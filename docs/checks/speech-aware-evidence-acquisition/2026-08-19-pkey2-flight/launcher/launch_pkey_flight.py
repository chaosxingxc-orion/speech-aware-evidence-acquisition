"""P-KEY flight launcher (REGISTERED probe, exposure row SAEA-PROBE-pkey2-338).

Structurally the P-SLU Stage-2 flight launcher (archived at
``docs/checks/speech-aware-evidence-acquisition/2026-08-18-pslu-s2-flight/launcher/
launch_pslu_s2_flight.py``, flown as ``attempt-20260818T200339Z-80119a``),
adapted only where the P-KEY machinery differs:

    contracts.FrozenCoreGate.for_study_repo
      -> core.session.start_session                 (spawns the receipt-pinned binary)
      -> core.base.TRANSPORTS.resolve("llama-server")
      -> rails.core_client.FrozenCoreClient(plan, gate, transport, run_dir,
             binding=build_payload_binding(...), slice_registry=build_slice_registry(...))
      -> 3 x rails.silence_swap.build_silence_swap_slice + client.register_slice
      -> rails.probes.pkey_flight.run_pkey_flight   (T0 x60 -> AUD-NOSUP x60 ->
             AUD-SUP x60 (+3 silence-swap) -> TXT-NOSUP x60 -> TXT-SUP x60 ->
             TXT-NOSUP-DUP x35 = 338, ONE session)
      -> client.close()

Successor run (preregistration section 8): identical to the predecessor
``pkeyfly/`` launcher except ``flight_identity.RUN_ID``, which now names the
fresh exposure row ``SAEA-PROBE-pkey2-338`` (zero prior durable spend) instead
of the CLOSED NOT-CONSUMED ``SAEA-PROBE-pkey-303``. See ``flight_identity.py``'s
own SUCCESSOR-RUN NOTE for why the committed flight config needs no change.

THIS LAUNCHER NEVER READS A RESULT. It writes every scored row to
``outputs.jsonl`` (plus the per-sample T0 ``transcript-registry.json`` the
machinery docstring prescribes) for the separately-registered one-shot read
mission and prints ONLY operational health (request index, sample id, latency,
ok/fail, response LENGTH) -- never response text, never a metric value, never
a transcript.

Resumability under one registration (``--attempt-id``): every response is
appended to ``responses.jsonl`` as it arrives, keyed by request index and the
sha256 of that request's own canonical messages. A resumed attempt replays
those cached responses instead of re-contacting the core, and fails closed the
moment a replayed request's message hash disagrees with the cached one.
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
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import (  # noqa: E402
    SLURP_LOCK_KEY,
    SlurpAdapter,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    FrozenCoreClient,
    build_payload_binding,
    build_slice_registry,
    probe_sample_rate_hz,
)
from speech_aware_evidence_acquisition.rails.probes.pkey_flight import (  # noqa: E402
    assert_pinned_text_matches_config,
    run_pkey_flight,
    transcript_registry_as_json,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    load_pslu_rosters,
    load_pslu_sample_manifest,
    select_pslu_samples,
)
from speech_aware_evidence_acquisition.rails.silence_swap import (  # noqa: E402
    build_silence_swap_slice,
)

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/pkey-flight.json").read_text(encoding="utf-8")
)


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


class HealthProxy:
    """Counts requests, logs OPERATIONAL health only, and persists every
    response for resume. Never inspects response content beyond its length."""

    def __init__(self, inner, response_log: Path, cached: list[dict]) -> None:
        self._inner = inner
        self._response_log = response_log
        self._cached = cached
        self._index = 0
        self.replayed = 0
        self.flown = 0
        self.failures: list[dict] = []

    def complete(self, messages, *, decoding_params=None, text_only_sample_id=None):  # noqa: A002
        # ``text_only_sample_id`` is the real-client text-mode opt-in that
        # landed at fd9398e (the attempt-1 abort's own repair): passes 3, 4
        # and the 2026-08-19 amendment's duplicate sub-block all send it, so
        # this proxy MUST forward it verbatim -- swallowing it here would
        # re-create the exact transport-invariant refusal attempt-1 died on.
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
            if index % 25 == 0 or index == len(self._cached):
                log(f"replay {index}/{len(self._cached)} from cache")
            return entry["response_text"]

        started = time.time()
        try:
            if text_only_sample_id is None:
                text = self._inner.complete(messages, decoding_params=decoding_params)
            else:
                text = self._inner.complete(
                    messages,
                    decoding_params=decoding_params,
                    text_only_sample_id=text_only_sample_id,
                )
        except Exception as error:  # noqa: BLE001 -- health accounting, then re-raise
            elapsed = time.time() - started
            self.failures.append(
                {"index": index, "media_relpath": media, "error": f"{type(error).__name__}: {error}"}
            )
            log(f"req {index:04d} FAILED after {elapsed:.1f}s media={media} :: {type(error).__name__}")
            raise
        elapsed = time.time() - started
        self.flown += 1
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
        log(f"req {index:04d} ok {elapsed:6.2f}s media={media} chars={len(text)}")
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

    # Fail-closed config/code parity before anything else (machinery guard).
    assert_pinned_text_matches_config(FLIGHT_CFG)
    log("config/code parity guard: PASS (t0_instruction + txt_template + sha256 companions)")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    values = build_values(REPO)
    cfg_hash = config_hash_of(values)

    manifest = load_pslu_sample_manifest(REPO / FLIGHT_CFG["sample_manifest"])
    rosters = load_pslu_rosters(REPO / FLIGHT_CFG["roster_table"])
    adapter = SlurpAdapter(lock, root, repo_root=REPO)
    log("loading devel split (sha256 of every devel media file -- slow, model-free)")
    samples = select_pslu_samples(adapter.load_split("devel"), manifest)
    by_id = {sample.sample_id: sample for sample in samples}
    log(f"frozen sample set: {len(samples)} samples, {sum(s.audio_seconds for s in samples):.2f}s audio")

    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), manifest.split_identity_hash)
    attempt_id = args.attempt_id or fresh_attempt_id()
    plan = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile=FLIGHT_CFG["execution_plan"]["execution_profile"],
        carrier_lock_key=FLIGHT_CFG["execution_plan"]["carrier_lock_key"],
        split_role=FLIGHT_CFG["execution_plan"]["split_role"],
        split_identity_hash=manifest.split_identity_hash,
        planned_model_calls=int(FLIGHT_CFG["execution_plan"]["planned_model_calls"]),
        planned_gpu_hours=float(FLIGHT_CFG["execution_plan"]["planned_gpu_hours"]),
        planned_speech_audio_seconds=int(FLIGHT_CFG["execution_plan"]["planned_speech_audio_seconds"]),
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
        json.dumps({"config_hash": cfg_hash, "protocol_hash": phash, "values": values}, indent=2, sort_keys=True),
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
        carrier_lock_key=SLURP_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=asset_dir(lock, SLURP_LOCK_KEY, root),
    )
    slice_registry = build_slice_registry(data_root=root, run_id=RUN_ID, samples=samples)
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,
        run_dir=run_dir,
        binding=binding,
        slice_registry=slice_registry,
        request_id_prefix="pkey",
    )
    log(f"FrozenCoreClient constructed (D2 arm {client.arm}); flight lock {client.flight_lock}")

    swap_map: dict[str, str] = {}
    for sample_id in FLIGHT_CFG["silence_swap"]["sample_ids"]:
        sample = by_id[sample_id]
        record = build_silence_swap_slice(
            registry=slice_registry,
            data_root=root,
            sample_id=sample_id,
            parent_media_relpath=sample.media_relpath,
            duration_seconds=sample.audio_seconds,
            sample_rate_hz=probe_sample_rate_hz(root / sample.media_relpath),
        )
        client.register_slice(record)
        swap_map[sample_id] = record.media_relpath
        log(f"silence-swap registered: {sample_id} -> {record.media_relpath} ({record.audio_seconds:.2f}s)")

    proxy = HealthProxy(client, response_log, cached)
    started_at = time.time()
    txt_duplicate_ids = list(FLIGHT_CFG["txt_duplicate"]["sample_ids"])
    log(
        "FLIGHT START: 60 x T0 -> 60 x AUD-NOSUP -> 60 x AUD-SUP (+3 silence-swap) -> "
        f"60 x TXT-NOSUP -> 60 x TXT-SUP -> {len(txt_duplicate_ids)} x TXT-NOSUP-DUP "
        f"(303 + {len(txt_duplicate_ids)} = {303 + len(txt_duplicate_ids)} total)"
    )
    error: BaseException | None = None
    summary = None
    try:
        summary = run_pkey_flight(
            adapter=adapter,
            core_client=proxy,
            samples=samples,
            rosters=rosters,
            split_identity_hash=manifest.split_identity_hash,
            decoding_params=decoding_params(values),
            silence_swap_media_relpaths=swap_map,
            txt_duplicate_sample_ids=txt_duplicate_ids,
        )
    except BaseException as exc:  # noqa: BLE001 -- always close the sink and report
        error = exc
        log(f"FLIGHT ABORTED: {type(exc).__name__}: {exc}")
    wall = time.time() - started_at

    if summary is not None:
        # Persisted for the separately-registered one-shot read mission.
        # WRITTEN, NEVER READ by this launcher. Row shape is exactly what
        # analysis.pkey_read.PKeyOutputRow.from_json expects, including the
        # per-row transcript_sha256_used on TXT-* rows.
        with (run_dir / "outputs.jsonl").open("w", encoding="utf-8") as handle:
            for result in summary.results:
                record = {
                    "arm": result.arm,
                    "sample_id": result.sample_id,
                    "silence_swapped": result.silence_swapped,
                    "txt_duplicate": result.txt_duplicate,
                    "transcript_sha256_used": result.transcript_sha256_used,
                    "messages": list(result.messages),
                    "response_text": result.response_text,
                    "metrics": dict(result.metrics),
                    "consumption": result.consumption.as_json(),
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        log(f"outputs.jsonl written: {len(summary.results)} rows (NOT read by this launcher)")
        # The per-sample T0 transcript registry the machinery docstring
        # prescribes a real launcher writes into its own attempt dir
        # (transcript_registry_as_json). Structural count logged only.
        (run_dir / "transcript-registry.json").write_text(
            json.dumps(transcript_registry_as_json(summary.transcript_registry), indent=2, sort_keys=True),
            encoding="utf-8",
            newline="\n",
        )
        log(f"transcript-registry.json written: {len(summary.transcript_registry)} entries (hashes recorded at pass 0)")

    receipt = client.close()
    log(f"client.close(): trace_manifest_hash={receipt['trace_manifest_hash']}")
    log(f"requests: flown={proxy.flown} replayed={proxy.replayed} failures={len(proxy.failures)}")
    log(f"cost: {json.dumps(receipt['cost'], sort_keys=True)}")
    log(f"wall: {wall/60:.1f} min")

    flight_receipt = {
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "status": "COMPLETED" if error is None else "ABORTED",
        "error": None if error is None else f"{type(error).__name__}: {error}",
        "config_hash": cfg_hash,
        "protocol_hash": phash,
        "split_identity_hash": manifest.split_identity_hash,
        "wall_seconds": wall,
        "requests_flown_this_attempt": proxy.flown,
        "requests_replayed_from_cache": proxy.replayed,
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
        "silence_swap": swap_map,
    }
    (run_dir / "flight-receipt.json").write_text(
        json.dumps(flight_receipt, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    log(f"flight receipt: {run_dir / 'flight-receipt.json'}")
    return 0 if error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
