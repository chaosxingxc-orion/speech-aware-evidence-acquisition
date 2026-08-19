"""P-TRAP flight launcher (REGISTERED probe, exposure row SAEA-PROBE-ptrap-120).

Structurally the archived P-KEY flight launcher
(``docs/checks/speech-aware-evidence-acquisition/2026-08-19-pkey2-flight/
launcher/launch_pkey_flight.py``, flown as ``attempt-20260819T...``), adapted
only where the P-TRAP machinery differs:

    binding.build_binding()                       (OFFLINE, zero model calls)
      -> hash cross-check against the reviewed trap-binding.json
    contracts.FrozenCoreGate.for_study_repo
      -> core.session.start_session               (spawns the receipt-pinned binary)
      -> core.base.TRANSPORTS.resolve("llama-server")
      -> rails.core_client.FrozenCoreClient(plan, gate, transport, run_dir,
             binding=build_payload_binding(...))
      -> rails.probes.ptrap_flight.run_ptrap_flight  (V1+V2 per sample over the
             frozen 60 = 120 requests, ONE session)
      -> client.close()

No slice registry and no silence swap: neither V1 nor V2 derives a runtime
media variant (both carry the sample's own real audio, the flight config's
``bridge.note``), so no runtime-derived media is ever named.

THE TRAP TABLE IS NEVER RE-DERIVED BEHIND THE REVIEWED BINDING. ``binding.py``
runs first as its own model-free step and writes ``trap-binding.json`` plus its
structural stats; this launcher recomputes the SAME deterministic table and
refuses to fly unless its canonical hash equals the hash recorded in that
file. ``run_ptrap_flight`` then consumes the already-built table (it never
re-derives one itself) and re-runs the binding-time fail-closed gold
zero-overlap check over every row it produced.

THIS LAUNCHER NEVER READS A RESULT. It writes every scored row to
``outputs.jsonl`` for the separately-registered one-shot read mission
(``analysis.ptrap_read``) and prints ONLY operational health (request index,
arm, sample id, latency, ok/fail, response LENGTH) -- never response text,
never a metric value, never a capture flag.

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
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from binding import (  # noqa: E402
    build_binding,
    canonical_hash,
    stats_document,
)
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
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    load_pslu_rosters,
    load_pslu_sample_manifest,
    select_pslu_samples,
)
from speech_aware_evidence_acquisition.rails.probes.ptrap_flight import (  # noqa: E402
    PTRAP_ARMS,
    V1_ARM,
    V2_ARM,
    run_ptrap_flight,
)

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/ptrap-flight.json").read_text(encoding="utf-8")
)

# The flight loop's own fixed order (ptrap_flight.run_ptrap_flight): V1 then V2
# per sample, over the 60 manifest ids. Derived from the plan, never from
# response content -- it only labels the operational health line.
_ARM_CYCLE = (V1_ARM, V2_ARM)


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


def _arm_of_index(index: int) -> str:
    return _ARM_CYCLE[(index - 1) % 2]


class HealthProxy:
    """Counts requests, logs OPERATIONAL health only, and persists every
    response for resume. Never inspects response content beyond its length."""

    def __init__(self, inner, response_log: Path, cached: list[dict], total_requests: int) -> None:
        self._inner = inner
        self._response_log = response_log
        self._cached = cached
        self._total = total_requests
        self._index = 0
        self._flight_started_at = time.time()
        self.replayed = 0
        self.flown = 0
        self.failures: list[dict] = []
        self.latency_total = 0.0
        self.latency_by_arm: dict[str, float] = {}
        self.flown_by_arm: Counter = Counter()

    def complete(self, messages, *, decoding_params=None):  # noqa: A002
        self._index += 1
        index = self._index
        arm = _arm_of_index(index)
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
            text = self._inner.complete(messages, decoding_params=decoding_params)
        except Exception as error:  # noqa: BLE001 -- health accounting, then re-raise
            elapsed = time.time() - started
            self.failures.append(
                {
                    "index": index,
                    "arm": arm,
                    "media_relpath": media,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            log(f"req {index:04d} [{arm}] FAILED after {elapsed:.1f}s media={media} :: {type(error).__name__}")
            raise
        elapsed = time.time() - started
        self.flown += 1
        self.flown_by_arm[arm] += 1
        self.latency_total += elapsed
        self.latency_by_arm[arm] = self.latency_by_arm.get(arm, 0.0) + elapsed
        with self._response_log.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "index": index,
                        "arm": arm,
                        "messages_sha256": mhash,
                        "media_relpath": media,
                        "latency_seconds": elapsed,
                        "response_text": text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        rate = self.flown / max(time.time() - self._flight_started_at, 1e-9)
        remaining = max(self._total - index, 0)
        log(
            f"req {index:04d} [{arm}] ok {elapsed:6.2f}s media={media} chars={len(text)} "
            f"| flown={self.flown} {rate*60:.1f} req/min eta={remaining/max(rate,1e-9)/60:.1f} min"
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
    parser.add_argument("--binding-dir", required=True, help="directory holding the reviewed trap-binding.json")
    parser.add_argument("--attempt-id", default=None, help="resume an existing attempt directory")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--runtime-root", default="/home/chao")
    args = parser.parse_args()

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    values = build_values(REPO)
    cfg_hash = config_hash_of(values)

    # ---- the reviewed trap binding, re-derived and hash-checked -------------
    binding_dir = Path(args.binding_dir)
    reviewed = json.loads((binding_dir / "trap-binding.json").read_text(encoding="utf-8"))
    reviewed_hash = canonical_hash(reviewed)
    trap_sets, document = build_binding()
    rebuilt_hash = canonical_hash(document)
    if rebuilt_hash != reviewed_hash:
        raise RuntimeError(
            f"trap binding divergence: the launcher rebuilt {rebuilt_hash!r} but the reviewed "
            f"{binding_dir / 'trap-binding.json'} hashes to {reviewed_hash!r}; refusing to fly a "
            "trap table other than the reviewed one (fail-closed)"
        )
    binding_stats = stats_document(document, rebuilt_hash)
    log(f"trap binding: hash {rebuilt_hash} matches the reviewed manifest -- PASS")
    log(
        f"trap binding structure: V1 K distribution "
        f"{json.dumps(binding_stats['v1_k_distribution'], sort_keys=True)}; "
        f"V2 K distribution {json.dumps(binding_stats['v2_k_distribution'], sort_keys=True)}; "
        f"V1 K=0 samples {len(binding_stats['v1_k_zero_sample_ids'])}; "
        f"common denominator {binding_stats['common_denominator_n']}"
    )

    manifest = load_pslu_sample_manifest(REPO / FLIGHT_CFG["sample_manifest"])
    rosters = load_pslu_rosters(REPO / FLIGHT_CFG["roster_table"])
    adapter = SlurpAdapter(lock, root, repo_root=REPO)
    log("loading devel split (sha256 of every devel media file -- slow, model-free)")
    samples = select_pslu_samples(adapter.load_split("devel"), manifest)
    total_requests = len(PTRAP_ARMS) * len(samples)
    one_pass = sum(s.audio_seconds for s in samples)
    log(f"frozen sample set: {len(samples)} samples, one pass {one_pass:.2f}s audio")
    log(
        f"flight plan: {len(samples)} samples x {len(PTRAP_ARMS)} arms {PTRAP_ARMS} = "
        f"{total_requests} requests; base roster {len(rosters.full_roster)} entries"
    )
    planned_calls = int(FLIGHT_CFG["execution_plan"]["planned_model_calls"])
    if total_requests != planned_calls:
        raise RuntimeError(
            f"plan yields {total_requests} requests, the committed flight config declares "
            f"{planned_calls}"
        )
    metered_audio = float(len(PTRAP_ARMS)) * one_pass
    planned_audio = int(FLIGHT_CFG["execution_plan"]["planned_speech_audio_seconds"])
    log(f"metered audio for this flight: {metered_audio:.2f}s (plan ceiling {planned_audio})")
    if metered_audio > planned_audio:
        raise RuntimeError(
            f"one full flight meters {metered_audio:.2f} audio seconds but the plan allows only "
            f"{planned_audio}"
        )

    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), manifest.split_identity_hash)
    attempt_id = args.attempt_id or fresh_attempt_id()
    plan = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile=FLIGHT_CFG["execution_plan"]["execution_profile"],
        carrier_lock_key=FLIGHT_CFG["execution_plan"]["carrier_lock_key"],
        split_role=FLIGHT_CFG["execution_plan"]["split_role"],
        split_identity_hash=manifest.split_identity_hash,
        planned_model_calls=planned_calls,
        planned_gpu_hours=float(FLIGHT_CFG["execution_plan"]["planned_gpu_hours"]),
        planned_speech_audio_seconds=planned_audio,
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
    # The trap binding manifest the exposure row names, written into the attempt
    # dir for the read mission's own audit. WRITTEN, NEVER READ back here.
    (run_dir / "trap-binding.json").write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8", newline="\n"
    )
    (run_dir / "trap-binding-stats.json").write_text(
        json.dumps(binding_stats, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
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
    gpu_started_at = time.time()
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
    log(f"session up: pid={session.pid} port={session.port} (spawn+load {time.time()-gpu_started_at:.1f}s)")
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

    payload_binding = build_payload_binding(
        carrier_lock_key=SLURP_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=asset_dir(lock, SLURP_LOCK_KEY, root),
    )
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,
        run_dir=run_dir,
        binding=payload_binding,
        request_id_prefix="ptrap",
    )
    log(f"FrozenCoreClient constructed (D2 arm {client.arm}); flight lock {client.flight_lock}")

    proxy = HealthProxy(client, response_log, cached, total_requests)
    flight_started_at = time.time()
    log(f"FLIGHT START: {len(samples)} samples x (V1 -> V2) = {total_requests} requests, ONE session")
    error: BaseException | None = None
    summary = None
    try:
        summary = run_ptrap_flight(
            adapter=adapter,
            core_client=proxy,
            samples=samples,
            base_roster_entries=rosters.full_roster,
            trap_sets=trap_sets,
            split_identity_hash=manifest.split_identity_hash,
            decoding_params=decoding_params(values),
        )
    except BaseException as exc:  # noqa: BLE001 -- always close the sink and report
        error = exc
        log(f"FLIGHT ABORTED: {type(exc).__name__}: {exc}")
    wall = time.time() - flight_started_at
    gpu_wall = time.time() - gpu_started_at

    arm_counts: dict[str, int] = {}
    if summary is not None:
        # Persisted for the separately-registered one-shot read mission
        # (analysis.ptrap_read). WRITTEN, NEVER READ by this launcher. Row shape
        # is exactly what analysis.ptrap_read.PTrapOutputRow.from_json expects.
        with (run_dir / "outputs.jsonl").open("w", encoding="utf-8") as handle:
            for result in summary.results:
                record = {
                    "arm": result.arm,
                    "sample_id": result.sample_id,
                    "messages": list(result.messages),
                    "response_text": result.response_text,
                    "metrics": dict(result.metrics),
                    "consumption": result.consumption.as_json(),
                    "k": result.k,
                    "trap_entries": [dict(entry) for entry in result.trap_entries],
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        arm_counts = dict(Counter(result.arm for result in summary.results))
        distinct_pairs = {(result.arm, result.sample_id) for result in summary.results}
        log(f"outputs.jsonl written: {len(summary.results)} rows (NOT read by this launcher)")
        log(f"per-arm row counts: {json.dumps(arm_counts, sort_keys=True)}")
        if len(distinct_pairs) != len(summary.results):
            log(
                f"COMPLETENESS WARNING: {len(summary.results)} rows but only "
                f"{len(distinct_pairs)} distinct (arm, sample_id) pairs"
            )
        expected_counts = {V1_ARM: len(samples), V2_ARM: len(samples)}
        if arm_counts != expected_counts:
            log(f"COMPLETENESS WARNING: expected {expected_counts}, got {arm_counts}")

    receipt = client.close()
    log(f"client.close(): trace_manifest_hash={receipt['trace_manifest_hash']}")
    log(f"requests: flown={proxy.flown} replayed={proxy.replayed} failures={len(proxy.failures)}")
    log(f"flown by arm: {json.dumps(dict(proxy.flown_by_arm), sort_keys=True)}")
    log(
        "mean latency by arm: "
        + json.dumps(
            {
                arm: round(total / max(proxy.flown_by_arm[arm], 1), 3)
                for arm, total in sorted(proxy.latency_by_arm.items())
            },
            sort_keys=True,
        )
    )
    log(f"cost: {json.dumps(receipt['cost'], sort_keys=True)}")
    log(f"wall: flight {wall/60:.1f} min; GPU-occupied {gpu_wall/60:.1f} min ({gpu_wall/3600:.3f} h)")

    flight_receipt = {
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "status": "COMPLETED" if error is None else "ABORTED",
        "error": None if error is None else f"{type(error).__name__}: {error}",
        "config_hash": cfg_hash,
        "protocol_hash": phash,
        "split_identity_hash": manifest.split_identity_hash,
        "preregistration": FLIGHT_CFG["preregistration"],
        "arms": list(PTRAP_ARMS),
        "trap_binding_hash": rebuilt_hash,
        "trap_binding_stats": binding_stats,
        "n_samples": len(samples),
        "n_requests_planned": total_requests,
        "metered_audio_seconds_expected": round(metered_audio, 3),
        "planned_budgets": {
            "model_calls": planned_calls,
            "speech_audio_seconds": planned_audio,
            "gpu_hours": float(FLIGHT_CFG["execution_plan"]["planned_gpu_hours"]),
        },
        "registered_ceilings": {
            "model_calls": int(FLIGHT_CFG["cost_budget"]["call_ceiling"]),
            "speech_audio_seconds": int(FLIGHT_CFG["cost_budget"]["audio_seconds_ceiling"]),
            "gpu_hours": float(FLIGHT_CFG["cost_budget"]["gpu_hours_ceiling"]),
        },
        "wall_seconds": wall,
        "gpu_occupied_seconds_this_attempt": gpu_wall,
        "gpu_hours_this_attempt": gpu_wall / 3600.0,
        "requests_flown_this_attempt": proxy.flown,
        "requests_replayed_from_cache": proxy.replayed,
        "request_latency_seconds_this_attempt": proxy.latency_total,
        "requests_flown_by_arm": dict(proxy.flown_by_arm),
        "latency_seconds_by_arm": dict(proxy.latency_by_arm),
        "request_failures": proxy.failures,
        "result_rows": 0 if summary is None else len(summary.results),
        "result_rows_by_arm": arm_counts,
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
