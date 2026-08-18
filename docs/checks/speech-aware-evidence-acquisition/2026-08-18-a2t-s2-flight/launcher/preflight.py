"""P-A2T Stage-2 supply-probe PRE-FLIGHT check -- ZERO model contact.

Verifies, before any core contact:
  1. the frozen 400-item discovery split resolves through the shipped adapter,
     the 120 headroom media are all present, and the receipt's split identity
     hash is the one the flight config, the headroom manifest and the ledger
     row all name;
  2. exactly ONE audio2tool probe receipt declares split_role=discovery (a
     second one would silently widen the split ``load_split`` returns);
  3. the exposure row SAEA-PROBE-a2t-s2-120 exists exactly once, reads
     consumed=no, carries the FULL 64-hex split identity hash verbatim, and
     registers budgets >= the plan's;
  4. the ExecutionPlan validates as bounded-discovery-probe / discovery;
  5. the payload binding builds over the 120 headroom samples (media
     confinement, sample-rate probe);
  6. the ``-np 1`` context delta is present and the WORST arm (N0r's full
     152-row registry) fits the single slot;
  7. the full FrozenCoreGate dry-run authorizes the model touch.
Nothing here opens a socket, spawns a server, or reads a model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.contracts.ledger import (  # noqa: E402
    _EXPOSURE_CARRIER_COLUMN,
    _EXPOSURE_RUN_COLUMN,
    _parse_ledger_tables,
)
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    model_lock_key,
    protocol_hash as compute_protocol_hash,
    runtime_receipt_relpath,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    audio2tool_receipts,
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
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import (  # noqa: E402
    A2T_S2_ARMS,
    build_flight_plan,
    derive_a0_selected_tools,
    load_headroom_manifest,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flight_identity import RUN_ID, build_values, config_hash_of  # noqa: E402
from flight_plan import (  # noqa: E402
    EXPECTED_REQUESTS,
    PLANNED_GPU_HOURS,
    PLANNED_MODEL_CALLS,
    PLANNED_SPEECH_AUDIO_SECONDS,
)

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/a2t-s2-flight.json").read_text(encoding="utf-8")
)


def main() -> int:
    problems: list[str] = []
    module_root = Path(__import__("speech_aware_evidence_acquisition").__file__).parent
    print(f"repo module root: {module_root}")
    if module_root != REPO / "src" / "speech_aware_evidence_acquisition":
        problems.append(f"module resolved outside this checkout: {module_root}")

    pyc = sorted((REPO / "src").rglob("*.pyc"))
    print(f"__pycache__ .pyc files under src/: {len(pyc)}")
    if pyc:
        problems.append(f"{len(pyc)} .pyc under src/ -- the D3 gate refuses bytecode; first {pyc[:3]}")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    print(f"data_root: {root}")
    carrier_root = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    print(f"carrier_root (asset_dir audio2tool): {carrier_root}")

    # ---- 1/2. split identity ------------------------------------------------
    receipts = audio2tool_receipts(REPO)
    discovery_receipts = {
        name: payload
        for name, payload in receipts.items()
        if payload.get("split_role") == "discovery"
    }
    print(f"audio2tool receipts declaring split_role=discovery: {sorted(discovery_receipts)}")
    if len(discovery_receipts) != 1:
        problems.append(
            f"expected exactly 1 discovery receipt, found {sorted(discovery_receipts)}"
        )
    receipt_payload = next(iter(discovery_receipts.values()))
    split_hash = str(receipt_payload["split_identity_hash"])
    print(f"split_identity_hash (from the receipt): {split_hash}")

    headroom_path = REPO / str(FLIGHT_CFG["headroom_manifest"])
    headroom = load_headroom_manifest(headroom_path)
    print(f"headroom manifest: {len(headroom.sample_ids)} ids, attempt_dir {headroom.attempt_dir}")
    for source, expected in (
        ("a2t-s2-flight.json execution_plan", FLIGHT_CFG["execution_plan"]["split_identity_hash"]),
        ("headroom.json", headroom.split_identity_hash),
    ):
        if expected != split_hash:
            problems.append(f"{source} split hash {expected!r} != receipt {split_hash!r}")
    if len(split_hash) != 64:
        problems.append(f"split identity hash is not 64-hex: {split_hash!r}")

    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    print("resolving discovery split (sha256 of every media file -- slow, model-free)")
    all_samples = adapter.load_split("discovery")
    print(f"discovery split resolved: {len(all_samples)} samples")
    by_id = {s.sample_id: s for s in all_samples}
    absent = [sid for sid in headroom.sample_ids if sid not in by_id]
    if absent:
        problems.append(f"{len(absent)} headroom ids absent from the split: {absent[:5]}")
    samples = [by_id[sid] for sid in headroom.sample_ids if sid in by_id]
    missing = [s.sample_id for s in samples if not (root / s.media_relpath).is_file()]
    if missing:
        problems.append(f"{len(missing)} headroom media missing: {missing[:5]}")
    print(f"headroom media resolved: {len(samples) - len(missing)}/{len(headroom.sample_ids)}")

    # ---- the deterministic plan + its metered audio load --------------------
    selected = derive_a0_selected_tools(Path(headroom.attempt_dir), headroom.sample_ids)
    registry_rows = load_tool_registry(lock, root)
    fplan = build_flight_plan(headroom, selected, registry_rows, seed=int(FLIGHT_CFG["seed"]))
    total_requests = 3 * len(fplan.headroom_ids) + len(fplan.n0r_sample_ids)
    print(f"flight plan: {total_requests} requests over arms {A2T_S2_ARMS}")
    if total_requests != EXPECTED_REQUESTS:
        problems.append(f"plan yields {total_requests} requests, registration declares {EXPECTED_REQUESTS}")
    if tuple(FLIGHT_CFG["arms"]) != A2T_S2_ARMS:
        problems.append(f"config arms {FLIGHT_CFG['arms']} != module arms {A2T_S2_ARMS}")
    one_pass = sum(s.audio_seconds for s in samples)
    n0r_audio = sum(by_id[sid].audio_seconds for sid in fplan.n0r_sample_ids)
    metered_audio = 3.0 * one_pass + n0r_audio
    max_item = max(s.audio_seconds for s in samples)
    print(f"metered audio seconds for one full flight: {metered_audio:.2f} (longest item {max_item:.2f})")
    if metered_audio > PLANNED_SPEECH_AUDIO_SECONDS:
        problems.append(
            f"one full flight meters {metered_audio:.2f} audio seconds but the plan claims only "
            f"{PLANNED_SPEECH_AUDIO_SECONDS}"
        )
    worst_case_audio = metered_audio + (PLANNED_MODEL_CALLS - total_requests) * max_item
    print(f"worst case within the {PLANNED_MODEL_CALLS}-call budget: {worst_case_audio:.2f} audio seconds")
    if worst_case_audio > PLANNED_SPEECH_AUDIO_SECONDS:
        print(
            "  NOTE: the audio ceiling would bite before the call ceiling in a pathological "
            "all-retries-on-the-longest-item scenario (fail-closed, acceptable)"
        )

    # ---- 6. context sizing --------------------------------------------------
    values = build_values(REPO)
    argv = [str(t) for t in values["server_args"]]
    print(f"server_args (after the -np delta): {argv}")
    ctx = int(argv[argv.index("-c") + 1])
    npar = int(argv[argv.index("-np") + 1])
    per_slot = ctx // npar
    schemas = render_tool_schemas(lock, root)
    instruction_chars = len(
        "You control tools. Available tools:\n" + schemas + "\n\n"
        'Respond with ONLY a JSON array of tool calls, e.g. [{"name": "x", "arguments": {}}].'
    )
    est_tokens = instruction_chars // 4
    print(f"per-slot context: {ctx}/{npar} = {per_slot} tokens")
    print(f"worst arm (N0r, full registry): {instruction_chars} chars, est {est_tokens} tokens")
    if npar != 1:
        problems.append(f"-np is {npar}, delta 4 did not apply")
    max_out = int(values["decoding_params"].get("max_tokens", 0))
    worst_sequence = est_tokens + 500 + max_out
    print(f"max_tokens: {max_out}; worst-case sequence ~{worst_sequence} tokens")
    if per_slot < worst_sequence:
        problems.append(f"per-slot context {per_slot} cannot hold the worst-case ~{worst_sequence}")

    # ---- 3. exposure ledger row ---------------------------------------------
    rows = _parse_ledger_tables((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8"))
    matched = [r for r in rows if r.get(_EXPOSURE_RUN_COLUMN) == RUN_ID]
    print(f"exposure rows matching run id {RUN_ID!r}: {len(matched)}")
    if len(matched) != 1:
        problems.append(f"expected exactly 1 exposure row, found {len(matched)}")
    else:
        row = matched[0]
        for col in (
            "execution profile",
            "split role",
            "split identity hash",
            "consumed",
            "calls",
            "speech audio seconds",
            "gpu hours",
        ):
            print(f"  ledger[{col!r}] = {row.get(col)!r}")
        print(f"  ledger[{_EXPOSURE_CARRIER_COLUMN!r}] = {str(row.get(_EXPOSURE_CARRIER_COLUMN))[:80]!r}...")
        if row.get("split identity hash") != split_hash:
            problems.append(
                "LEDGER CELL MISMATCH: 'split identity hash' cell is "
                f"{row.get('split identity hash')!r} but the plan carries {split_hash!r}; "
                "FrozenCoreGate compares these verbatim -- the gate WILL refuse."
            )
        if str(row.get("consumed", "")).lower() != "no":
            problems.append(f"exposure row consumed={row.get('consumed')!r}, must be 'no'")
        if row.get("execution profile") != FLIGHT_CFG["execution_plan"]["execution_profile"]:
            problems.append("exposure row execution profile disagrees with the plan")
        if row.get("split role") != FLIGHT_CFG["execution_plan"]["split_role"]:
            problems.append("exposure row split role disagrees with the plan")
        for col, planned, parse in (
            ("calls", PLANNED_MODEL_CALLS, int),
            ("speech audio seconds", PLANNED_SPEECH_AUDIO_SECONDS, int),
            ("gpu hours", PLANNED_GPU_HOURS, float),
        ):
            try:
                registered = parse(str(row.get(col)))
            except ValueError:
                problems.append(f"ledger column {col!r} is not a number: {row.get(col)!r}")
                continue
            if registered < planned:
                problems.append(f"ledger {col}={registered} < planned {planned}")

    # ---- 4. plan ------------------------------------------------------------
    cfg_hash = config_hash_of(values)
    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), split_hash)
    print(f"config_hash: {cfg_hash}")
    print(f"protocol_hash: {phash}")
    print(f"server_env: {values['server_env']}")
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
        attempt_id="attempt-preflight-000000",
    ).validate()
    print(
        f"ExecutionPlan validates: profile={plan.execution_profile} role={plan.split_role} "
        f"calls={plan.planned_model_calls} audio_s={plan.planned_speech_audio_seconds} "
        f"gpu_h={plan.planned_gpu_hours}"
    )

    # ---- 5. payload binding -------------------------------------------------
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=carrier_root,
    )
    rates = {binding.sample_facts[s.sample_id][1] for s in samples}
    print(f"payload binding built: {len(binding.allowed_sample_ids)} ids, sample rates {sorted(rates)}")

    # ---- 7. FULL GATE DRY-RUN ----------------------------------------------
    # assert_model_touch_allowed is pure authorization: it validates the plan,
    # cross-checks the exposure row, resolves the carrier against the umbrella
    # lock and verifies both receipts. It contacts no model and opens no socket.
    # full_hash=False fast-paths the 30 GB GGUF verification; the real flight
    # pays for one genuine full SHA-256 pass per session.
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        Path("/home/chao"),
        runtime_receipt_relpath=runtime_receipt_relpath(values),
        expected_model_lock_key=model_lock_key(values),
    )
    try:
        lock_sha = gate.assert_model_touch_allowed(plan, full_hash=False)
        print(f"GATE DRY-RUN: model touch AUTHORIZED (umbrella lock sha256 {lock_sha})")
    except Exception as error:  # noqa: BLE001
        problems.append(f"GATE DRY-RUN REFUSED -> {type(error).__name__}: {error}")

    print()
    if problems:
        print(f"PRE-FLIGHT PROBLEMS ({len(problems)}):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("PRE-FLIGHT CLEAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
