"""P-CORR-F flight launcher (REGISTERED probe, exposure row SAEA-PROBE-pcorrf-240).

Structurally the archived P-TRAP flight launcher
(``docs/checks/speech-aware-evidence-acquisition/2026-08-19-ptrap-flight/
launcher/launch_ptrap_flight.py``), adapted only where the P-CORR-F machinery
differs:

    binding.build_binding_full()                  (OFFLINE, zero model calls,
                                                   zero gold)
      -> tri-derivation hash cross-check against the reviewed
         corrective-binding.json
    contracts.FrozenCoreGate.for_study_repo
      -> core.session.start_session               (spawns the receipt-pinned
                                                   binary as a CHILD of this
                                                   process)
      -> core.base.TRANSPORTS.resolve("llama-server")
      -> rails.core_client.FrozenCoreClient(plan, gate, transport, run_dir,
             binding=build_payload_binding(...))
      -> rails.probes.pcorrf_flight.run_pcorrf_flight  (W1..W4 per sample over
             the frozen 60 = 240 requests, ONE session -- it is one model)
      -> client.close()

No slice registry and no silence swap: no arm derives a runtime media variant
(all four carry the sample's own real audio), so no runtime-derived media is
ever named.

THE CORRECTIVE TABLE IS NEVER RE-DERIVED BEHIND THE REVIEWED BINDING.
``binding.py`` runs first as its own model-free step and writes
``corrective-binding.json`` plus its structural stats; this launcher recomputes
the SAME deterministic table and refuses to fly unless BOTH its tri-derivation
``binding_hash`` and its canonical document hash equal the reviewed ones.
``run_pcorrf_flight`` then consumes the already-built table (it never re-derives
one itself) and re-runs the tri-derivation guard a third time, plus the
ontology-miner and forbidden-gold-symbol AST guards, before issuing any request.

THIS LAUNCHER NEVER READS A RESULT. It writes every row to ``outputs.jsonl``
for the separately-registered one-shot read mission (``analysis.pcorrf_read``)
and prints ONLY operational health (request index, arm, sample id, latency,
ok/fail, response LENGTH) -- never response text, never a metric value, never a
recovery or contamination flag.

Two independent resume mechanisms, both fail-closed:

* **Response replay within one attempt** (``--attempt-id``, the P-TRAP
  precedent): every response is appended to ``responses.jsonl`` as it arrives,
  keyed by request index and the sha256 of that request's own canonical
  messages. A resumed attempt replays those cached responses instead of
  re-contacting the core, and refuses the moment a replayed request's message
  hash disagrees with the cached one. ``outputs.jsonl`` is regenerated whole.
* **Arm-level carry across attempts** (``--carry-from <attempt-id>``, the
  mission's own arm-level idempotence requirement): any arm that is COMPLETE
  (all 60 cells present) in that attempt's ``outputs.jsonl`` is passed to
  ``run_pcorrf_flight`` through its ``already_completed`` map -- so those cells
  are never re-fired -- and its rows are copied forward VERBATIM into this
  attempt's ``outputs.jsonl``. Copying reads only the ``arm`` and ``sample_id``
  fields of each line; the row's response text and metrics pass through as
  opaque bytes and are never inspected.
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
from types import MappingProxyType
from typing import Mapping, Sequence

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from binding import (  # noqa: E402
    SAMPLE_MANIFEST_RELPATH,
    build_binding_full,
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
from speech_aware_evidence_acquisition.rails.probes.pcorrf_flight import (  # noqa: E402
    ARM_N,
    CEILING_AUDIO_SECONDS,
    CEILING_CALLS,
    CEILING_GPU_HOURS,
    DEFAULT_PLANNED_GPU_HOURS,
    DEFAULT_PLANNED_MODEL_CALLS,
    DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS,
    PCORRF_ARMS,
    binding_config_sha256,
    build_execution_plan,
    run_pcorrf_flight,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    load_pslu_rosters,
    load_pslu_sample_manifest,
    select_pslu_samples,
)

ROSTER_TABLE_RELPATH = "configs/probes/g0-binding/pslu-rosters-train-only.json"
PREREGISTRATION_RELPATH = "docs/readiness/2026-08-20-pcorrf-preregistration-REGISTERED.md"


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
    response for resume. Never inspects response content beyond its length.

    ``request_plan`` is the exact ``(arm, sample_id)`` sequence
    ``run_pcorrf_flight`` will issue given this attempt's own
    ``already_completed`` map -- derived from the PLAN, never from response
    content, and used only to label the health line and to catch a divergence
    between the plan and what the machinery actually asks for."""

    def __init__(
        self,
        inner,
        response_log: Path,
        cached: list[dict],
        request_plan: Sequence[tuple[str, str]],
    ) -> None:
        self._inner = inner
        self._response_log = response_log
        self._cached = cached
        self._plan = tuple(request_plan)
        self._total = len(self._plan)
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
        if index > self._total:
            raise RuntimeError(
                f"request {index} exceeds the planned {self._total}-request sequence; refusing to "
                "issue an unplanned core contact (fail-closed)"
            )
        arm, planned_sample_id = self._plan[index - 1]
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
                    "sample_id": planned_sample_id,
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
                        "sample_id": planned_sample_id,
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


def load_carry_rows(attempt_dir: Path) -> tuple[dict[str, frozenset[str]], list[str]]:
    """Arm-level idempotence (module docstring): returns the ``already_completed``
    map of COMPLETE arms plus the raw JSON LINES of those arms' rows, to be
    copied forward verbatim. Only ``arm``/``sample_id`` are ever inspected."""

    path = Path(attempt_dir) / "outputs.jsonl"
    if not path.is_file():
        raise RuntimeError(f"--carry-from names {attempt_dir} but it has no outputs.jsonl")
    by_arm: dict[str, set[str]] = {}
    lines_by_arm: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        document = json.loads(line)
        arm = str(document["arm"])
        sample_id = str(document["sample_id"])
        by_arm.setdefault(arm, set()).add(sample_id)
        lines_by_arm.setdefault(arm, []).append(line)
    complete = {arm: ids for arm, ids in by_arm.items() if len(ids) == ARM_N and arm in PCORRF_ARMS}
    carried_lines: list[str] = []
    for arm in sorted(complete):
        carried_lines.extend(lines_by_arm[arm])
    return {arm: frozenset(ids) for arm, ids in complete.items()}, carried_lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--binding-dir", required=True, help="directory holding the reviewed corrective-binding.json")
    parser.add_argument("--attempt-id", default=None, help="resume an existing attempt directory (response replay)")
    parser.add_argument("--carry-from", default=None, help="attempt id whose COMPLETE arms are carried, never re-flown")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--runtime-root", default="/home/chao")
    args = parser.parse_args()

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    values = build_values(REPO)
    cfg_hash = config_hash_of(values)

    # ---- the reviewed corrective binding, re-derived and hash-checked --------
    binding_dir = Path(args.binding_dir)
    reviewed = json.loads((binding_dir / "corrective-binding.json").read_text(encoding="utf-8"))
    reviewed_doc_hash = canonical_hash(reviewed)
    reviewed_binding_hash = str(reviewed["binding_hash"])
    binding_table, document, harvested = build_binding_full()
    rebuilt_doc_hash = canonical_hash(document)
    if binding_table.binding_hash != reviewed_binding_hash:
        raise RuntimeError(
            f"tri-derivation binding hash divergence: the launcher rebuilt "
            f"{binding_table.binding_hash!r} but the reviewed "
            f"{binding_dir / 'corrective-binding.json'} carries {reviewed_binding_hash!r}; refusing "
            "(fail-closed, preregistration section 4 item 1)"
        )
    if rebuilt_doc_hash != reviewed_doc_hash:
        raise RuntimeError(
            f"corrective binding document divergence: the launcher rebuilt {rebuilt_doc_hash!r} but "
            f"the reviewed {binding_dir / 'corrective-binding.json'} hashes to {reviewed_doc_hash!r}; "
            "refusing to fly a corrective table other than the reviewed one (fail-closed)"
        )
    binding_stats = stats_document(document, rebuilt_doc_hash)
    log(f"corrective binding: tri-derivation hash {binding_table.binding_hash} matches the reviewed manifest -- PASS")
    log(f"corrective binding: document hash {rebuilt_doc_hash} matches the reviewed manifest -- PASS")
    log(f"binding_config_sha256: {binding_config_sha256()}")
    for arm in PCORRF_ARMS:
        block = binding_stats["per_arm"][arm]
        log(
            f"corrective binding structure {arm}: K dist "
            f"{json.dumps(block['k_distribution'], sort_keys=True)} total {block['k_total']} "
            f"mean {block['k_mean']} max {block['k_max']} K=0 {block['k_zero_sample_count']}"
        )

    manifest = load_pslu_sample_manifest(REPO / SAMPLE_MANIFEST_RELPATH)
    rosters = load_pslu_rosters(REPO / ROSTER_TABLE_RELPATH)
    adapter = SlurpAdapter(lock, root, repo_root=REPO)
    log("loading devel split (sha256 of every devel media file -- slow, model-free)")
    samples = select_pslu_samples(adapter.load_split("devel"), manifest)
    one_pass = sum(s.audio_seconds for s in samples)
    log(f"frozen sample set: {len(samples)} samples, one pass {one_pass:.2f}s audio")

    # ---- arm-level idempotence ------------------------------------------------
    already_completed: dict[str, frozenset[str]] = {}
    carried_lines: list[str] = []
    if args.carry_from:
        already_completed, carried_lines = load_carry_rows(Path(args.run_dir) / args.carry_from)
        log(
            f"carry-from {args.carry_from}: COMPLETE arms {sorted(already_completed)} "
            f"({len(carried_lines)} rows carried forward, never re-flown)"
        )

    request_plan: list[tuple[str, str]] = [
        (arm, sample.sample_id)
        for sample in samples
        for arm in PCORRF_ARMS
        if sample.sample_id not in already_completed.get(arm, frozenset())
    ]
    total_requests = len(request_plan)
    log(
        f"flight plan: {len(samples)} samples x {len(PCORRF_ARMS)} arms {PCORRF_ARMS} = "
        f"{len(samples) * len(PCORRF_ARMS)} cells, {total_requests} to issue "
        f"({len(samples) * len(PCORRF_ARMS) - total_requests} carried); base roster "
        f"{len(rosters.full_roster)} entries"
    )
    if total_requests > DEFAULT_PLANNED_MODEL_CALLS:
        raise RuntimeError(
            f"plan yields {total_requests} requests, above the registered plan of "
            f"{DEFAULT_PLANNED_MODEL_CALLS}"
        )
    metered_audio = float(len(PCORRF_ARMS)) * one_pass
    log(f"metered audio for a full flight: {metered_audio:.2f}s (plan {DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS}, ceiling {CEILING_AUDIO_SECONDS})")
    if metered_audio > DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS:
        raise RuntimeError(
            f"one full flight meters {metered_audio:.2f} audio seconds but the plan allows only "
            f"{DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS}"
        )

    # The plan comes from the MACHINERY's own registered constructor
    # (rails.probes.pcorrf_flight.build_execution_plan): it is the
    # coordinator-reviewed path, it re-asserts the registered ceilings on the
    # way through (assert_within_registered_ceilings) and it re-resolves the
    # execution profile through contracts.assert_execution_scope. Its
    # protocol_hash is the pinned binding_config_sha256.
    #
    # The sibling P-SLU/P-KEY/P-TRAP flights instead hashed
    # core.config.protocol_hash(config_hash, arm, split_identity_hash), which
    # additionally binds this session's server argv, decode params and
    # feature-cache directory. That value is NOT discarded: it is recorded
    # alongside as `config_protocol_hash` in both config-values.json and the
    # flight receipt, so the cross-probe comparison the read may want stays
    # available. Documented divergence, recorded for audit.
    config_phash = compute_protocol_hash(cfg_hash, str(values["arm"]), manifest.split_identity_hash)
    attempt_id = args.attempt_id or fresh_attempt_id()
    plan = build_execution_plan(attempt_id=attempt_id)
    if plan.split_identity_hash != manifest.split_identity_hash:
        raise RuntimeError(
            f"machinery plan split_identity_hash {plan.split_identity_hash!r} != manifest "
            f"{manifest.split_identity_hash!r}; refusing (fail-closed)"
        )
    phash = plan.protocol_hash

    run_dir = Path(args.run_dir) / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log(f"attempt {attempt_id} -> {run_dir}")
    (run_dir / f"{RUN_ID}.plan.json").write_text(
        json.dumps(asdict(plan), indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    (run_dir / f"{RUN_ID}.config-values.json").write_text(
        json.dumps(
            {
                "config_hash": cfg_hash,
                "protocol_hash": phash,
                "config_protocol_hash": config_phash,
                "values": values,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
        newline="\n",
    )
    # The corrective binding manifest the exposure row names, written into the
    # attempt dir for the read mission's own audit. WRITTEN, NEVER READ here.
    (run_dir / "corrective-binding.json").write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8", newline="\n"
    )
    (run_dir / "corrective-binding-stats.json").write_text(
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

    log("spawning llama-server (receipt-pinned binary, CHILD of this process)")
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
        request_id_prefix="pcorrf",
    )
    log(f"FrozenCoreClient constructed (D2 arm {client.arm}); flight lock {client.flight_lock}")

    proxy = HealthProxy(client, response_log, cached, request_plan)
    flight_started_at = time.time()
    log(f"FLIGHT START: {total_requests} requests over arms {PCORRF_ARMS}, ONE session (one model)")
    error: BaseException | None = None
    summary = None
    try:
        summary = run_pcorrf_flight(
            adapter=adapter,
            core_client=proxy,
            samples=samples,
            base_roster_entries=rosters.full_roster,
            binding_table=binding_table,
            harvested=harvested,
            # The machinery's own convention (its unit suite passes
            # slurp_world.data_root here): `root` reaches
            # core.legality.resolve_legality_declaration, whose only
            # root-relative lookups are evidence-materialization records --
            # none of which this probe declares.
            root=root,
            split_identity_hash=manifest.split_identity_hash,
            decoding_params=decoding_params(values),
            already_completed=MappingProxyType(dict(already_completed)),
        )
    except BaseException as exc:  # noqa: BLE001 -- always close the sink and report
        error = exc
        log(f"FLIGHT ABORTED: {type(exc).__name__}: {exc}")
    wall = time.time() - flight_started_at
    gpu_wall = time.time() - gpu_started_at

    arm_counts: dict[str, int] = {}
    arm_k_totals: dict[str, int] = {}
    if summary is not None:
        # Persisted for the separately-registered one-shot read mission
        # (analysis.pcorrf_read). WRITTEN, NEVER READ by this launcher. Row
        # shape is exactly what analysis.pcorrf_read.PCorrFOutputRow.from_json
        # expects.
        with (run_dir / "outputs.jsonl").open("w", encoding="utf-8") as handle:
            for line in carried_lines:  # opaque pass-through, arm/sample_id only
                handle.write(line + "\n")
            for result in summary.results:
                record = {
                    "arm": result.arm,
                    "sample_id": result.sample_id,
                    "messages": list(result.messages),
                    "response_text": result.response_text,
                    "metrics": dict(result.metrics),
                    "consumption": result.consumption.as_json(),
                    "k": result.k,
                    "corrective_entries": [dict(entry) for entry in result.corrective_entries],
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        arm_counts = dict(Counter(result.arm for result in summary.results))
        for result in summary.results:
            arm_k_totals[result.arm] = arm_k_totals.get(result.arm, 0) + result.k
        distinct_pairs = {(result.arm, result.sample_id) for result in summary.results}
        n_written = len(summary.results) + len(carried_lines)
        log(f"outputs.jsonl written: {n_written} rows ({len(carried_lines)} carried) -- NOT read by this launcher")
        log(f"per-arm row counts (flown this attempt): {json.dumps(arm_counts, sort_keys=True)}")
        log(f"per-arm corrective-entry totals actually flown: {json.dumps(arm_k_totals, sort_keys=True)}")
        if len(distinct_pairs) != len(summary.results):
            log(
                f"COMPLETENESS WARNING: {len(summary.results)} rows but only "
                f"{len(distinct_pairs)} distinct (arm, sample_id) pairs"
            )
        expected_counts = {
            arm: len(samples) for arm in PCORRF_ARMS if arm not in already_completed
        }
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
        "config_protocol_hash": config_phash,
        "binding_config_sha256": binding_config_sha256(),
        "split_identity_hash": manifest.split_identity_hash,
        "preregistration": PREREGISTRATION_RELPATH,
        "arms": list(PCORRF_ARMS),
        "corrective_binding_hash": binding_table.binding_hash,
        "corrective_binding_document_hash": rebuilt_doc_hash,
        "corrective_binding_stats": binding_stats,
        "carried_from_attempt_id": args.carry_from,
        "carried_arms": sorted(already_completed),
        "carried_row_count": len(carried_lines),
        "n_samples": len(samples),
        "n_cells_total": len(samples) * len(PCORRF_ARMS),
        "n_requests_planned_this_attempt": total_requests,
        "metered_audio_seconds_expected": round(metered_audio, 3),
        "planned_budgets": {
            "model_calls": DEFAULT_PLANNED_MODEL_CALLS,
            "speech_audio_seconds": DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS,
            "gpu_hours": DEFAULT_PLANNED_GPU_HOURS,
        },
        "registered_ceilings": {
            "model_calls": CEILING_CALLS,
            "speech_audio_seconds": CEILING_AUDIO_SECONDS,
            "gpu_hours": CEILING_GPU_HOURS,
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
        "corrective_entries_flown_by_arm": arm_k_totals,
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
