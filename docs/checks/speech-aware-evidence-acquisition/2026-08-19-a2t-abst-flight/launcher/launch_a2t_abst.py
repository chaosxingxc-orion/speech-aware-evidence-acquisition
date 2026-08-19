"""P-A2T abstention-asymmetry 2x2 flight launcher (exposure row
``SAEA-PROBE-a2t-abst-44``).

Operator sequence, the same chain the archived Stage-2c launcher used
(``docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2c-flight/
launcher/launch_pa2t_s2c.py``), with the abstention-asymmetry orchestrator
swapped in and the silence-swap wiring the P-SLU/P-KEY SLURP launchers already
established re-used verbatim:

    contracts.FrozenCoreGate.for_study_repo
      -> core.session.start_session                 (spawns the receipt-pinned binary)
      -> core.base.TRANSPORTS.resolve("llama-server")
      -> rails.core_client.FrozenCoreClient(plan, gate, transport, run_dir,
             binding=build_payload_binding(...), slice_registry=build_slice_registry(...))
      -> 11 x rails.silence_swap.build_silence_swap_slice + client.register_slice
      -> rails.probes.a2t_abst_flight.run_a2t_abst_flight  (TP-A -> TP-S -> TW-A
             -> TW-S per sample over the seeded 11 = 44, ONE session)
      -> rails.probes.a2t_abst_flight.write_outputs_jsonl
      -> client.close()

SILENCE SWAPS. The preregistration requires all four cells for all 11 ids, so
every drawn sample needs its own matched-duration silent counterpart (unlike
P-SLU's optional 3-sample subset). ``rails.probes.a2t_abst_flight`` deliberately
does NOT generate or register them (only a real ``FrozenCoreClient`` has a slice
registry); that is this launcher's job, via the established
``rails.silence_swap.build_silence_swap_slice`` +
``FrozenCoreClient.register_slice`` path, exactly as the archived P-KEY launcher
did for its own 3 swaps. Each record chains to its REAL parent media's sha256 on
disk, so a swap is a registered derived slice, never anonymous audio.

THE TOOL-REMOVAL PLAN IS BUILT BEFORE THE SESSION SPAWNS. Every sample's own
correct tool comes from ``rails.probes.a2t_s2_flight.derive_a0_selected_tools``
over the CONSUMED A0 attempt (self-supplied, deployment-legal, gold-free -- on
headroom ids the core's own A0 selection IS the correct tool by that set's
defining criterion). That derivation is a read of an already-flown, already-
consumed attempt's recorded output, not a new model contact, and this launcher
records only COUNTS about it.

THIS LAUNCHER NEVER READS A RESULT. It writes every per-request row to
``outputs.jsonl`` for the separately-registered one-shot read mission
(``analysis.a2t_abst_read``) and prints ONLY operational health (request index,
cell, sample id, latency, ok/fail, response LENGTH) -- never response text,
never an abstention flag, never a metric value.

Resumability under one registration (``--attempt-id``): every response is
appended to ``responses.jsonl`` as it arrives, keyed by request index and the
sha256 of that request's own canonical messages. A resumed attempt replays those
cached responses instead of re-contacting the core, and fails closed the moment
a replayed request's message hash disagrees with the cached one.

Two hard operational ceilings are enforced here, before the request that would
cross them (they are the mission's, not the contract's -- the contract's own
call/audio budgets are enforced independently inside
``core.model.adapter.request``): 60 requests (counted on the TOTAL index,
replays included) and 0.15 h of CUMULATIVE wall clock measured from
llama-server spawn (``--prior-wall-seconds`` carries an earlier attempt's spend
into a resume, so the registered ceiling stays honest across attempts).
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
    build_slice_registry,
    probe_sample_rate_hz,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_abst_flight import (  # noqa: E402
    A2T_ABST_CELLS,
    ABST_N,
    DEFAULT_SEED,
    build_flight_plan_from_attempt,
    run_a2t_abst_flight,
    seeded_abst_draw,
    write_outputs_jsonl,
)
from speech_aware_evidence_acquisition.rails.silence_swap import (  # noqa: E402
    build_silence_swap_slice,
)

WALL_CEILING_SECONDS = GPU_HOURS_CEILING * 3600.0

# The flight loop's own fixed order (a2t_abst_flight.run_a2t_abst_flight):
# TP-A, TP-S, TW-A, TW-S per sample, over the sorted drawn ids. Derived from the
# plan, never from response content -- it only labels the operational health line.
_CELL_CYCLE = A2T_ABST_CELLS


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


def _cell_of_index(index: int) -> str:
    return _CELL_CYCLE[(index - 1) % len(_CELL_CYCLE)]


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
        self.latency_by_cell: dict[str, float] = {}
        self.flown_by_cell: Counter = Counter()

    def complete(self, messages, *, decoding_params=None):  # noqa: A002
        self._index += 1
        index = self._index
        cell = _cell_of_index(index)
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
                    "cell": cell,
                    "media_relpath": media,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            log(
                f"req {index:04d} [{cell:4s}] FAILED after {elapsed:.1f}s media={media} "
                f":: {type(error).__name__}"
            )
            raise
        elapsed = time.time() - started
        self.flown += 1
        self.flown_by_cell[cell] += 1
        self.latency_total += elapsed
        self.latency_by_cell[cell] = self.latency_by_cell.get(cell, 0.0) + elapsed
        with self._response_log.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "index": index,
                        "cell": cell,
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
            f"req {index:04d} [{cell:4s}] ok {elapsed:6.2f}s media={media} chars={len(text)} "
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

    # ---- the deterministic 2x2 flight plan (model-free) --------------------
    split = resolve_split(REPO)
    log(
        f"headroom artifact: {len(split.headroom_ids)} ids; consumed A0 attempt "
        f"{split.consumed_a0_attempt_dir}"
    )
    drawn = seeded_abst_draw(split.headroom_ids, seed=DEFAULT_SEED, n=ABST_N)
    log(f"seeded draw (seed {DEFAULT_SEED}, n={ABST_N}): {len(drawn)} ids")

    registry_rows = load_tool_registry(lock, root)
    full_registry_text = render_tool_schemas(lock, root)
    fplan = build_flight_plan_from_attempt(drawn, Path(split.consumed_a0_attempt_dir), registry_rows)
    distinct_withheld = {n for names in fplan.correct_tool_names_by_sample.values() for n in names}
    log(
        f"tool-removal plan: {len(fplan.sample_ids)} samples, registry {len(registry_rows)} rows "
        f"(full render {len(full_registry_text)} chars), {len(distinct_withheld)} distinct withheld tools"
    )
    total_requests = len(A2T_ABST_CELLS) * len(fplan.sample_ids)
    log(
        f"flight plan: {len(fplan.sample_ids)} samples x {len(A2T_ABST_CELLS)} cells "
        f"{A2T_ABST_CELLS} = {total_requests} requests"
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
        raise RuntimeError(f"{len(missing)} drawn ids absent from the frozen split: {missing[:5]}")
    samples = [by_id[sid] for sid in fplan.sample_ids]
    one_pass = sum(s.audio_seconds for s in samples)
    metered_audio = float(len(A2T_ABST_CELLS)) * one_pass
    log(
        f"drawn sample set: {len(samples)} samples, one pass {one_pass:.2f}s audio; "
        f"metered total for this flight {metered_audio:.2f}s (plan ceiling "
        f"{PLANNED_SPEECH_AUDIO_SECONDS})"
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
    # The resolved cell construction, written for the read mission's own audit
    # (fully reconstructible from the headroom artifact + seed + registry +
    # consumed attempt; recorded anyway). Mirrors Stage-2b/2c's own write shape.
    (run_dir / f"{RUN_ID}.cell-plan.json").write_text(
        json.dumps(
            {
                "seed": DEFAULT_SEED,
                "n_draw": ABST_N,
                "cells": list(A2T_ABST_CELLS),
                "consumed_a0_attempt_dir": split.consumed_a0_attempt_dir,
                "split_identity_hash": split_hash,
                "sample_ids": list(fplan.sample_ids),
                "correct_tool_names": {
                    k: list(v) for k, v in sorted(fplan.correct_tool_names_by_sample.items())
                },
                "tw_registry_render_chars": {
                    k: len(v) for k, v in sorted(fplan.tw_registry_text_by_sample.items())
                },
                "full_registry_render_chars": len(full_registry_text),
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
    slice_registry = build_slice_registry(data_root=root, run_id=RUN_ID, samples=samples)
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,
        run_dir=run_dir,
        binding=payload_binding,
        slice_registry=slice_registry,
        request_id_prefix="a2tabst",
    )
    log(f"FrozenCoreClient constructed (D2 arm {client.arm}); flight lock {client.flight_lock}")

    swap_map: dict[str, str] = {}
    for sample in samples:
        record = build_silence_swap_slice(
            registry=slice_registry,
            data_root=root,
            sample_id=sample.sample_id,
            parent_media_relpath=sample.media_relpath,
            duration_seconds=sample.audio_seconds,
            sample_rate_hz=probe_sample_rate_hz(root / sample.media_relpath),
        )
        client.register_slice(record)
        swap_map[sample.sample_id] = record.media_relpath
        log(
            f"silence-swap registered: {sample.sample_id} -> {record.media_relpath} "
            f"({record.audio_seconds:.2f}s)"
        )
    if set(swap_map) != set(fplan.sample_ids):
        raise RuntimeError("silence-swap registration did not cover exactly the planned sample ids")
    log(f"silence swaps: {len(swap_map)}/{len(fplan.sample_ids)} registered derived slices")

    proxy = HealthProxy(
        client, response_log, cached, gpu_started_at, args.prior_wall_seconds, total_requests
    )
    flight_started_at = time.time()
    log(
        f"FLIGHT START: {total_requests} requests over cells {A2T_ABST_CELLS}; ceilings "
        f"{CALLS_CEILING} requests / {GPU_HOURS_CEILING} h cumulative wall "
        f"(prior {args.prior_wall_seconds:.0f}s)"
    )
    error: BaseException | None = None
    summary = None
    try:
        summary = run_a2t_abst_flight(
            adapter=adapter,
            core_client=proxy,
            samples=samples,
            plan=fplan,
            silence_swap_media_relpaths=swap_map,
            decoding_params=decoding_params(values),
        )
    except BaseException as exc:  # noqa: BLE001 -- always close the sink and report
        error = exc
        log(f"FLIGHT ABORTED: {type(exc).__name__}: {exc}")
    wall = time.time() - flight_started_at
    gpu_wall = time.time() - gpu_started_at

    cell_counts: dict[str, int] = {}
    if summary is not None:
        # Persisted for the separately-registered one-shot read mission
        # (analysis.a2t_abst_read). WRITTEN, NEVER READ by this launcher.
        write_outputs_jsonl(run_dir / "outputs.jsonl", summary.results)
        cell_counts = dict(Counter(result.arm for result in summary.results))
        distinct_pairs = {(result.arm, result.sample_id) for result in summary.results}
        log(f"outputs.jsonl written: {len(summary.results)} rows (NOT read by this launcher)")
        log(f"per-cell row counts: {json.dumps(cell_counts, sort_keys=True)}")
        if len(distinct_pairs) != len(summary.results):
            log(
                f"COMPLETENESS WARNING: {len(summary.results)} rows but only "
                f"{len(distinct_pairs)} distinct (cell, sample_id) pairs"
            )
        expected_counts = {cell: len(fplan.sample_ids) for cell in A2T_ABST_CELLS}
        if cell_counts != expected_counts:
            log(f"COMPLETENESS WARNING: expected {expected_counts}, got {cell_counts}")

    receipt = client.close()
    log(f"client.close(): trace_manifest_hash={receipt['trace_manifest_hash']}")
    log(f"requests: flown={proxy.flown} replayed={proxy.replayed} failures={len(proxy.failures)}")
    log(f"flown by cell: {json.dumps(dict(proxy.flown_by_cell), sort_keys=True)}")
    log(
        "mean latency by cell: "
        + json.dumps(
            {
                cell: round(total / max(proxy.flown_by_cell[cell], 1), 3)
                for cell, total in sorted(proxy.latency_by_cell.items())
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
        "cells": list(A2T_ABST_CELLS),
        "consumed_a0_attempt_dir": split.consumed_a0_attempt_dir,
        "n_samples": len(samples),
        "n_requests_planned": total_requests,
        "n_silence_swap_slices": len(swap_map),
        "distinct_withheld_tool_count": len(distinct_withheld),
        "metered_audio_seconds_expected": round(metered_audio, 3),
        "planned_budgets": {
            "model_calls": PLANNED_MODEL_CALLS,
            "speech_audio_seconds": PLANNED_SPEECH_AUDIO_SECONDS,
            "gpu_hours": PLANNED_GPU_HOURS,
        },
        "registered_ceilings": {
            "model_calls": CALLS_CEILING,
            "speech_audio_seconds": 500,
            "gpu_hours": GPU_HOURS_CEILING,
        },
        "wall_seconds": wall,
        "gpu_occupied_seconds_this_attempt": gpu_wall,
        "prior_wall_seconds": args.prior_wall_seconds,
        "cumulative_gpu_hours": (args.prior_wall_seconds + gpu_wall) / 3600.0,
        "requests_flown_this_attempt": proxy.flown,
        "requests_replayed_from_cache": proxy.replayed,
        "request_latency_seconds_this_attempt": proxy.latency_total,
        "requests_flown_by_cell": dict(proxy.flown_by_cell),
        "latency_seconds_by_cell": dict(proxy.latency_by_cell),
        "request_failures": proxy.failures,
        "result_rows": 0 if summary is None else len(summary.results),
        "result_rows_by_cell": cell_counts,
        "silence_swap": swap_map,
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
