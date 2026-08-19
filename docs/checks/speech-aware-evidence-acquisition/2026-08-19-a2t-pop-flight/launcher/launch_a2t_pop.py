"""P-A2T whole-population regression-arm flight launcher (exposure row
``SAEA-PROBE-a2t-pop-194``).

Operator sequence, the same chain the archived Stage-2c launcher used
(``docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2c-flight/
launcher/launch_pa2t_s2c.py``), with the whole-population orchestrator swapped
in:

    contracts.FrozenCoreGate.for_study_repo
      -> core.session.start_session                 (spawns the receipt-pinned binary)
      -> core.base.TRANSPORTS.resolve("llama-server")
      -> rails.core_client.FrozenCoreClient(plan, gate, transport, run_dir,
             binding=build_payload_binding(...))
      -> rails.probes.a2t_pop_flight.run_a2t_pop_flight  (R0 -> R1 per sample
             over the EM-correct 97 = 194, ONE session)
      -> rails.probes.a2t_pop_flight.write_outputs_jsonl
      -> client.close()

ROSTER SOURCING. The 97-id EM-correct population is derived HERE, before the
session spawns, by ``rails.probes.a2t_pop_flight.derive_em_correct_ids`` --
the preregistration's own section-2 rule made executable (reuse
``analysis.a2t_read.load_attempt_rows``/``score_row``, the EXACT frozen scorer
the headroom list itself was built on, over the SAME consumed A0 attempt; never
a second scorer implementation, never a hand-curated list). That derivation is
fail-closed at exactly 97. It is a read of an already-flown, already-consumed
attempt's recorded output, not a new model contact, and this launcher records
only COUNTS about it plus the resolved id list (a plan artifact, not a result).

No slice registry: neither arm derives a runtime media variant (R0 is A0's own
zero-supply request byte-identically; R1's manipulation is entirely prompt-level
inside the SYSTEM message), so no runtime-derived media is ever named.

THIS LAUNCHER NEVER READS A RESULT. It writes every per-request row to
``outputs.jsonl`` for the separately-registered one-shot read mission
(``analysis.a2t_pop_read``) and prints ONLY operational health (request index,
arm, sample id, latency, ok/fail, response LENGTH) -- never response text, never
an EM value, never a regression count.

Resumability under one registration (``--attempt-id``): every response is
appended to ``responses.jsonl`` as it arrives, keyed by request index and the
sha256 of that request's own canonical messages. A resumed attempt replays those
cached responses instead of re-contacting the core, and fails closed the moment
a replayed request's message hash disagrees with the cached one.

Two hard operational ceilings are enforced here, before the request that would
cross them (they are the mission's, not the contract's -- the contract's own
call/audio budgets are enforced independently inside
``core.model.adapter.request``): 220 requests (counted on the TOTAL index,
replays included) and 0.5 h of CUMULATIVE wall clock measured from llama-server
spawn (``--prior-wall-seconds`` carries an earlier attempt's spend into a
resume, so the registered ceiling stays honest across attempts).
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

from flight_identity import (  # noqa: E402
    D2_ARM,
    PREREGISTRATION_RELPATH,
    RUN_ID,
    build_values,
    config_hash_of,
    decoding_params,
    resolve_split,
    server_args,
    server_env,
)
from flight_plan import (  # noqa: E402
    CALLS_CEILING,
    EXPECTED_REQUESTS,
    GPU_HOURS_CEILING,
    PLANNED_GPU_HOURS,
    PLANNED_MODEL_CALLS,
    PLANNED_SPEECH_AUDIO_SECONDS,
    REGISTERED_SPEECH_AUDIO_SECONDS,
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
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    load_tool_registry,
    render_tool_schemas,
)
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
from speech_aware_evidence_acquisition.rails.probes.a2t_pop_flight import (  # noqa: E402
    A2T_POP_ARMS,
    DEFAULT_SEED,
    EM_CORRECT_N,
    build_flight_plan_from_attempt,
    derive_em_correct_ids,
    run_a2t_pop_flight,
    write_outputs_jsonl,
)

WALL_CEILING_SECONDS = GPU_HOURS_CEILING * 3600.0

# The flight loop's own fixed order (a2t_pop_flight.run_a2t_pop_flight): R0 then
# R1 per sample, over the sorted EM-correct ids. Derived from the plan, never
# from response content -- it only labels the operational health line.
_ARM_CYCLE = A2T_POP_ARMS


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
    return _ARM_CYCLE[(index - 1) % len(_ARM_CYCLE)]


class CeilingExceeded(RuntimeError):
    """A mission ceiling (requests or cumulative wall clock) would be crossed by
    the next request. Raised BEFORE that request is issued, so nothing is spent."""


class HealthProxy:
    """Counts requests, logs OPERATIONAL health only, persists every response
    for resume, and enforces the mission's two hard ceilings. Never inspects
    response content beyond its length."""

    def __init__(
        self,
        inner,
        response_log: Path,
        cached: list[dict],
        gpu_started_at: float,
        prior_wall_seconds: float,
        total_requests: int,
    ) -> None:
        self._inner = inner
        self._response_log = response_log
        self._cached = cached
        self._gpu_started_at = gpu_started_at
        self._prior_wall = prior_wall_seconds
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
            if index % 50 == 0 or index == len(self._cached):
                log(f"replay {index}/{len(self._cached)} from cache")
            return entry["response_text"]

        if index > CALLS_CEILING:
            raise CeilingExceeded(
                f"request {index} would cross the mission request ceiling {CALLS_CEILING}"
            )
        cumulative_wall = self._prior_wall + (time.time() - self._gpu_started_at)
        if cumulative_wall > WALL_CEILING_SECONDS:
            raise CeilingExceeded(
                f"cumulative wall clock {cumulative_wall/3600:.3f} h has crossed the mission "
                f"ceiling {GPU_HOURS_CEILING} h at request {index}; stopping before it is issued "
                "(resume with --attempt-id and --prior-wall-seconds after reporting)"
            )

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
            log(
                f"req {index:04d} [{arm}] FAILED after {elapsed:.1f}s media={media} "
                f":: {type(error).__name__}"
            )
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
    parser.add_argument("--attempt-id", default=None, help="resume an existing attempt directory")
    parser.add_argument(
        "--prior-wall-seconds",
        type=float,
        default=0.0,
        help="wall seconds already spent by earlier attempts of this registration",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--runtime-root", default="/home/chao")
    args = parser.parse_args()

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    values = build_values(REPO)
    cfg_hash = config_hash_of(values)

    # ---- the deterministic two-arm flight plan (model-free) ----------------
    split = resolve_split(REPO)
    log(
        f"headroom artifact: {len(split.headroom_ids)} consumed headroom ids; consumed A0 attempt "
        f"{split.consumed_a0_attempt_dir}"
    )
    log("deriving the EM-correct roster (frozen scorer over the consumed A0 attempt, fail-closed at 97)")
    em_ids = derive_em_correct_ids(
        Path(split.consumed_a0_attempt_dir), lock, root, repo_root=REPO, expected_n=EM_CORRECT_N
    )
    log(f"EM-correct roster: {len(em_ids)} ids (registered {EM_CORRECT_N}) -- fail-closed check PASSED")
    overlap = sorted(set(em_ids) & set(split.headroom_ids))
    if overlap:
        raise RuntimeError(f"EM-correct roster overlaps the consumed headroom set: {overlap[:5]}")
    log("disjointness from the consumed 120-id headroom set: 0 overlapping ids -- OK")

    registry_rows = load_tool_registry(lock, root)
    full_registry_text = render_tool_schemas(lock, root)
    fplan = build_flight_plan_from_attempt(em_ids, Path(split.consumed_a0_attempt_dir), registry_rows)
    distinct_supplied = {n for names in fplan.r1_tool_names_by_sample.values() for n in names}
    log(
        f"R1 self-supplied plan: {len(fplan.sample_ids)} samples, registry {len(registry_rows)} rows "
        f"(full render {len(full_registry_text)} chars), {len(distinct_supplied)} distinct supplied tools"
    )
    total_requests = len(A2T_POP_ARMS) * len(fplan.sample_ids)
    log(
        f"flight plan: {len(fplan.sample_ids)} samples x {len(A2T_POP_ARMS)} arms "
        f"{A2T_POP_ARMS} = {total_requests} requests"
    )
    if total_requests != EXPECTED_REQUESTS:
        raise RuntimeError(
            f"plan yields {total_requests} requests, the registration declares {EXPECTED_REQUESTS}"
        )

    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    log("resolving the frozen discovery split (sha256 of every media file -- slow, model-free)")
    all_samples = adapter.load_split("discovery")
    by_id = {s.sample_id: s for s in all_samples}
    missing = [sid for sid in fplan.sample_ids if sid not in by_id]
    if missing:
        raise RuntimeError(f"{len(missing)} EM-correct ids absent from the frozen split: {missing[:5]}")
    samples = [by_id[sid] for sid in fplan.sample_ids]
    one_pass = sum(s.audio_seconds for s in samples)
    metered_audio = float(len(A2T_POP_ARMS)) * one_pass
    log(
        f"EM-correct sample set: {len(samples)} samples, one pass {one_pass:.2f}s audio; "
        f"metered total for this flight {metered_audio:.2f}s (plan ceiling "
        f"{PLANNED_SPEECH_AUDIO_SECONDS}, registered {REGISTERED_SPEECH_AUDIO_SECONDS})"
    )
    if metered_audio > PLANNED_SPEECH_AUDIO_SECONDS:
        raise RuntimeError(
            f"one full flight meters {metered_audio:.2f} audio seconds but the plan allows only "
            f"{PLANNED_SPEECH_AUDIO_SECONDS}"
        )

    split_hash = split.split_identity_hash
    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), split_hash)
    attempt_id = args.attempt_id or fresh_attempt_id()
    plan = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
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
        json.dumps({"config_hash": cfg_hash, "protocol_hash": phash, "values": values}, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )
    # The resolved arm construction, written for the read mission's own audit
    # (fully reconstructible from the consumed attempt + registry; recorded
    # anyway). Mirrors Stage-2b/2c's own write shape.
    (run_dir / f"{RUN_ID}.arm-plan.json").write_text(
        json.dumps(
            {
                "seed": DEFAULT_SEED,
                "arms": list(A2T_POP_ARMS),
                "population": "EM-correct (tool_accuracy==1 AND exact_match==1) ids of the frozen A2T 400",
                "population_n": len(fplan.sample_ids),
                "consumed_a0_attempt_dir": split.consumed_a0_attempt_dir,
                "split_identity_hash": split_hash,
                "sample_ids": list(fplan.sample_ids),
                "r1_tool_names": {
                    k: list(v) for k, v in sorted(fplan.r1_tool_names_by_sample.items())
                },
                "full_registry_render_chars": len(full_registry_text),
                "excluded_population_note": (
                    "the 183 tool-selection-failure ids are excluded (EM cannot regress there and no "
                    "gold-free supply-row rule exists for them) -- recorded limitation, prereg section 1"
                ),
            },
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
        binding=payload_binding,
        request_id_prefix="a2tpop",
    )
    log(f"FrozenCoreClient constructed (D2 arm {client.arm}); flight lock {client.flight_lock}")

    proxy = HealthProxy(
        client, response_log, cached, gpu_started_at, args.prior_wall_seconds, total_requests
    )
    flight_started_at = time.time()
    log(
        f"FLIGHT START: {total_requests} requests over arms {A2T_POP_ARMS}; ceilings "
        f"{CALLS_CEILING} requests / {GPU_HOURS_CEILING} h cumulative wall "
        f"(prior {args.prior_wall_seconds:.0f}s)"
    )
    error: BaseException | None = None
    summary = None
    try:
        summary = run_a2t_pop_flight(
            adapter=adapter,
            core_client=proxy,
            samples=samples,
            plan=fplan,
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
        # (analysis.a2t_pop_read). WRITTEN, NEVER READ by this launcher.
        write_outputs_jsonl(run_dir / "outputs.jsonl", summary.results)
        arm_counts = dict(Counter(result.arm for result in summary.results))
        distinct_pairs = {(result.arm, result.sample_id) for result in summary.results}
        log(f"outputs.jsonl written: {len(summary.results)} rows (NOT read by this launcher)")
        log(f"per-arm row counts: {json.dumps(arm_counts, sort_keys=True)}")
        if len(distinct_pairs) != len(summary.results):
            log(
                f"COMPLETENESS WARNING: {len(summary.results)} rows but only "
                f"{len(distinct_pairs)} distinct (arm, sample_id) pairs"
            )
        expected_counts = {arm: len(fplan.sample_ids) for arm in A2T_POP_ARMS}
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
    log(
        f"wall: flight {wall/60:.1f} min; GPU-occupied {gpu_wall/60:.1f} min "
        f"({(args.prior_wall_seconds + gpu_wall)/3600:.3f} h cumulative of the "
        f"{GPU_HOURS_CEILING} h ceiling)"
    )

    flight_receipt = {
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "status": "COMPLETED" if error is None else "ABORTED",
        "error": None if error is None else f"{type(error).__name__}: {error}",
        "config_hash": cfg_hash,
        "protocol_hash": phash,
        "split_identity_hash": split_hash,
        "preregistration": PREREGISTRATION_RELPATH,
        "d2_arm": D2_ARM,
        "seed": DEFAULT_SEED,
        "arms": list(A2T_POP_ARMS),
        "consumed_a0_attempt_dir": split.consumed_a0_attempt_dir,
        "population_n": len(samples),
        "population_headroom_overlap": len(overlap),
        "distinct_supplied_tool_count": len(distinct_supplied),
        "n_requests_planned": total_requests,
        "metered_audio_seconds_expected": round(metered_audio, 3),
        "planned_budgets": {
            "model_calls": PLANNED_MODEL_CALLS,
            "speech_audio_seconds": PLANNED_SPEECH_AUDIO_SECONDS,
            "gpu_hours": PLANNED_GPU_HOURS,
        },
        "registered_ceilings": {
            "model_calls": CALLS_CEILING,
            "speech_audio_seconds": REGISTERED_SPEECH_AUDIO_SECONDS,
            "gpu_hours": GPU_HOURS_CEILING,
        },
        "wall_seconds": wall,
        "gpu_occupied_seconds_this_attempt": gpu_wall,
        "prior_wall_seconds": args.prior_wall_seconds,
        "cumulative_gpu_hours": (args.prior_wall_seconds + gpu_wall) / 3600.0,
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
