"""P-A2T Stage-1 A0 baseline flight launcher (exposure row SAEA-BASE-a2t-a0-400).

Operator sequence, the same bridge sequence the archived P-SLU launcher used,
with ``rails.runner.run_rails_experiment`` in place of a probe-specific
orchestrator -- ``zero-supply`` IS one of ``rails.runner.RAILS_ARMS``, so this
flight needs no orchestration module of its own (the flight config's own
``runner_call`` note says exactly that):

    contracts.FrozenCoreGate.for_study_repo
      -> core.session.start_session                 (spawns the receipt-pinned binary)
      -> core.base.TRANSPORTS.resolve("llama-server")
      -> rails.core_client.FrozenCoreClient(plan, gate, transport, run_dir,
             binding=build_payload_binding(...))
      -> rails.runner.run_rails_experiment(arms=("zero-supply",))
      -> client.close()

No slice registry: A0 is zero-supply with no silence-swap control, so no
runtime-derived media variant is ever named.

THIS LAUNCHER NEVER READS A RESULT. It writes every scored row to
``outputs.jsonl`` for the separately-registered read mission and prints ONLY
operational health (request index, sample id, latency, ok/fail, response
LENGTH) -- never response text, never a metric value.

Resumability under one registration (``--attempt-id``): every response is
appended to ``responses.jsonl`` as it arrives, keyed by request index and the
sha256 of that request's own canonical messages. A resumed attempt replays
those cached responses instead of re-contacting the core, and fails closed the
moment a replayed request's message hash disagrees with the cached one.

Two hard operational ceilings are enforced here, before the request that would
cross them (they are the mission's, not the contract's -- the contract's own
call/audio budgets are enforced independently inside
``core.model.adapter.request``): 450 requests and 1.5 h of wall clock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flight_identity import (  # noqa: E402
    RUN_ID,
    build_values,
    config_hash_of,
    decoding_params,
    server_args,
    server_env,
)
from flight_plan import (  # noqa: E402
    CALLS_CEILING,
    GPU_HOURS_CEILING,
    PLANNED_GPU_HOURS,
    PLANNED_MODEL_CALLS,
    PLANNED_SPEECH_AUDIO_SECONDS,
)

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.core.base import TRANSPORTS  # noqa: E402
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    model_lock_key,
    protocol_hash as compute_protocol_hash,
    resolve_runtime_receipt_path,
    runtime_receipt_relpath,
)
from speech_aware_evidence_acquisition.core.driver.smoke import fresh_attempt_id  # noqa: E402
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
)
from speech_aware_evidence_acquisition.data.audio2tool import AUDIO2TOOL_LOCK_KEY  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    FrozenCoreClient,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.runner import run_rails_experiment  # noqa: E402

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/pa2t-a0-flight.json").read_text(encoding="utf-8")
)

WALL_CEILING_SECONDS = GPU_HOURS_CEILING * 3600.0


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{stamp}] {message}", flush=True)


def _messages_hash(messages: Sequence[Mapping[str, object]]) -> str:
    blob = json.dumps(list(messages), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _media_relpath(messages: Sequence[Mapping[str, object]]) -> str:
    for part in messages[1]["content"]:  # type: ignore[index]
        if isinstance(part, Mapping) and part.get("type") == "input_audio":
            return str(part.get("media_relpath"))
    return "<none>"


class CeilingExceeded(RuntimeError):
    """A mission ceiling (requests or wall clock) would be crossed by the next
    request. Raised BEFORE that request is issued, so nothing is spent."""


class HealthProxy:
    """Counts requests, logs OPERATIONAL health only, persists every response
    for resume, and enforces the mission's two hard ceilings. Never inspects
    response content beyond its length."""

    def __init__(self, inner, response_log: Path, cached: list[dict], started_at: float) -> None:
        self._inner = inner
        self._response_log = response_log
        self._cached = cached
        self._started_at = started_at
        self._index = 0
        self.replayed = 0
        self.flown = 0
        self.failures: list[dict] = []
        self.latency_total = 0.0

    def complete(self, messages, *, decoding_params=None):  # noqa: A002
        self._index += 1
        index = self._index
        mhash = _messages_hash(messages)
        media = _media_relpath(messages)

        if index <= len(self._cached):
            entry = self._cached[index - 1]
            if entry["index"] != index or entry["messages_sha256"] != mhash:
                raise RuntimeError(
                    f"resume divergence at request {index}: cached messages_sha256 "
                    f"{entry['messages_sha256']!r} != rebuilt {mhash!r}; refusing to replay a "
                    "response that does not belong to this request (fail-closed)"
                )
            self.replayed += 1
            if index % 50 == 0 or index == len(self._cached):
                log(f"replay {index}/{len(self._cached)} from cache")
            return entry["response_text"]

        if index > CALLS_CEILING:
            raise CeilingExceeded(
                f"request {index} would cross the mission request ceiling {CALLS_CEILING}"
            )
        elapsed_wall = time.time() - self._started_at
        if elapsed_wall > WALL_CEILING_SECONDS:
            raise CeilingExceeded(
                f"wall clock {elapsed_wall/3600:.3f} h has crossed the mission ceiling "
                f"{GPU_HOURS_CEILING} h at request {index}; stopping before it is issued "
                "(resume with --attempt-id after reporting)"
            )

        started = time.time()
        try:
            text = self._inner.complete(messages, decoding_params=decoding_params)
        except Exception as error:  # noqa: BLE001 -- health accounting, then re-raise
            elapsed = time.time() - started
            self.failures.append(
                {"index": index, "media_relpath": media, "error": f"{type(error).__name__}: {error}"}
            )
            log(f"req {index:04d} FAILED after {elapsed:.1f}s media={media} :: {type(error).__name__}")
            raise
        elapsed = time.time() - started
        self.flown += 1
        self.latency_total += elapsed
        with self._response_log.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "index": index,
                        "messages_sha256": mhash,
                        "media_relpath": media,
                        "latency_seconds": elapsed,
                        "response_text": text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        rate = self.flown / max(time.time() - self._started_at, 1e-9)
        log(
            f"req {index:04d} ok {elapsed:6.2f}s media={media} chars={len(text)} "
            f"| flown={self.flown} {rate*60:.1f} req/min eta={(400-index)/max(rate,1e-9)/60:.1f} min"
        )
        return text


def load_cached(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    entries.sort(key=lambda entry: entry["index"])
    for position, entry in enumerate(entries, start=1):
        if entry["index"] != position:
            raise RuntimeError(f"response cache {path} is not a contiguous 1..N sequence at {position}")
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--attempt-id", default=None, help="resume an existing attempt directory")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--runtime-root", default="/home/chao")
    args = parser.parse_args()

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    values = build_values(REPO)
    cfg_hash = config_hash_of(values)

    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    log("resolving the frozen discovery split (sha256 of every media file -- slow, model-free)")
    samples = adapter.load_split("discovery")
    total_audio = sum(s.audio_seconds for s in samples)
    log(f"frozen sample set: {len(samples)} samples, {total_audio:.2f}s audio")

    split_hash = str(FLIGHT_CFG["split_identity"]["split_identity_hash"])
    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), split_hash)
    attempt_id = args.attempt_id or fresh_attempt_id()
    plan = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile=FLIGHT_CFG["execution_plan"]["execution_profile"],
        carrier_lock_key=FLIGHT_CFG["execution_plan"]["carrier_lock_key"],
        split_role=FLIGHT_CFG["execution_plan"]["split_role"],
        split_identity_hash=split_hash,
        planned_model_calls=PLANNED_MODEL_CALLS,
        planned_gpu_hours=PLANNED_GPU_HOURS,
        planned_speech_audio_seconds=PLANNED_SPEECH_AUDIO_SECONDS,
        protocol_hash=phash,
        attempt_id=attempt_id,
    ).validate()

    run_dir = Path(args.run_dir) / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log(f"attempt {attempt_id} -> {run_dir}")
    (run_dir / f"{RUN_ID}.plan.json").write_text(
        json.dumps(asdict(plan), indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    (run_dir / f"{RUN_ID}.config-values.json").write_text(
        json.dumps(
            {"config_hash": cfg_hash, "protocol_hash": phash, "values": values},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
        newline="\n",
    )

    response_log = run_dir / "responses.jsonl"
    cached = load_cached(response_log)
    if cached:
        log(f"resume: {len(cached)} cached responses will be replayed without core contact")

    session_receipt_path = run_dir / f"{RUN_ID}.session-receipt.json"
    server_log_path = run_dir / f"{RUN_ID}.server.log"

    runtime_receipt = load_runtime_receipt(resolve_runtime_receipt_path(REPO, values))
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        Path(args.runtime_root),
        runtime_receipt_relpath=runtime_receipt_relpath(values),
        expected_model_lock_key=model_lock_key(values),
    )
    log(f"gate constructed (receipt {runtime_receipt_relpath(values)}, model {model_lock_key(values)})")

    log("spawning llama-server (receipt-pinned binary)")
    session = start_session(
        runtime_root=Path(args.runtime_root),
        data_root=root,
        runtime_receipt=runtime_receipt,
        host=args.host,
        port=args.port,
        session_id=f"{RUN_ID}-{attempt_id}",
        extra_argv=server_args(values),
        extra_env=server_env(values),
        receipt_path=session_receipt_path,
        server_log_path=server_log_path,
    )
    log(f"session up: pid={session.pid} port={session.port}")
    log(f"session argv: {' '.join(session.argv)}")
    for entry in session.model_files:
        log(f"  model file: {entry.path} sha256={entry.sha256}")

    transport = TRANSPORTS.resolve(str(values["transport"]))(
        values,
        root,
        session=session,
        runtime_receipt=runtime_receipt,
        runtime_root=Path(args.runtime_root),
    )

    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root),
    )
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,
        run_dir=run_dir,
        binding=binding,
        request_id_prefix="pa2t",
    )
    log(f"FrozenCoreClient constructed (D2 arm {client.arm}); flight lock {client.flight_lock}")

    started_at = time.time()
    proxy = HealthProxy(client, response_log, cached, started_at)
    log(
        f"FLIGHT START: {len(samples)} x zero-supply, ceilings {CALLS_CEILING} requests / "
        f"{GPU_HOURS_CEILING} h wall"
    )
    error: BaseException | None = None
    summary = None
    try:
        summary = run_rails_experiment(
            data_root=root,
            plan=plan,
            adapter=adapter,
            core_client=proxy,
            split_id=str(FLIGHT_CFG["runner_call"]["split_id"]),
            arms=tuple(FLIGHT_CFG["arms"]),
            decoding_params=decoding_params(values),
        )
    except BaseException as exc:  # noqa: BLE001 -- always close the sink and report
        error = exc
        log(f"FLIGHT ABORTED: {type(exc).__name__}: {exc}")
    wall = time.time() - started_at

    if summary is not None:
        # Persisted for the separately-registered one-shot read mission.
        # WRITTEN, NEVER READ by this launcher.
        with (run_dir / "outputs.jsonl").open("w", encoding="utf-8") as handle:
            for result in summary.results:
                handle.write(
                    json.dumps(
                        {
                            "arm": result.arm,
                            "sample_id": result.sample_id,
                            "messages": list(result.messages),
                            "response_text": result.response_text,
                            "metrics": dict(result.metrics),
                            "consumption": result.consumption.as_json(),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        log(f"outputs.jsonl written: {len(summary.results)} rows (NOT read by this launcher)")

    receipt = client.close()
    log(f"client.close(): trace_manifest_hash={receipt['trace_manifest_hash']}")
    log(f"requests: flown={proxy.flown} replayed={proxy.replayed} failures={len(proxy.failures)}")
    log(f"cost: {json.dumps(receipt['cost'], sort_keys=True)}")
    log(f"wall: {wall/60:.1f} min ({wall/3600:.3f} h of the {GPU_HOURS_CEILING} h ceiling)")

    flight_receipt = {
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "status": "COMPLETED" if error is None else "ABORTED",
        "error": None if error is None else f"{type(error).__name__}: {error}",
        "config_hash": cfg_hash,
        "protocol_hash": phash,
        "split_identity_hash": split_hash,
        "arms": list(FLIGHT_CFG["arms"]),
        "n_samples": len(samples),
        "split_audio_seconds": round(total_audio, 3),
        "planned_budgets": {
            "model_calls": PLANNED_MODEL_CALLS,
            "speech_audio_seconds": PLANNED_SPEECH_AUDIO_SECONDS,
            "gpu_hours": PLANNED_GPU_HOURS,
        },
        "wall_seconds": wall,
        "requests_flown_this_attempt": proxy.flown,
        "requests_replayed_from_cache": proxy.replayed,
        "request_latency_seconds_this_attempt": proxy.latency_total,
        "request_failures": proxy.failures,
        "result_rows": 0 if summary is None else len(summary.results),
        "session": {
            "session_id": session.session_id,
            "pid": session.pid,
            "host": session.host,
            "port": session.port,
            "binary_path": session.binary_path,
            "binary_sha256": session.binary_sha256,
            "argv": list(session.argv),
            "model_files": [{"path": m.path, "sha256": m.sha256} for m in session.model_files],
            "started_at": session.started_at,
        },
        "close_receipt": receipt,
    }
    (run_dir / "flight-receipt.json").write_text(
        json.dumps(flight_receipt, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    log(f"flight receipt: {run_dir / 'flight-receipt.json'}")
    return 0 if error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
