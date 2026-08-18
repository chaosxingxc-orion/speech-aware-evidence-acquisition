"""P-A2T Stage-2c form-robustness PRE-FLIGHT check -- ZERO model contact.

Mirrors the archived Stage-2b pre-flight (``docs/checks/
speech-aware-evidence-acquisition/2026-08-18-a2t-s2b-flight/launcher/
preflight.py``) with the Stage-2c three-arm plan swapped in. Verifies, before
any core contact:

  1. the frozen 400-item discovery split resolves through the shipped adapter,
     the 120 headroom media are all present, and the receipt's split identity
     hash is the one the flight config, the headroom manifest and the ledger
     row all name;
  2. exactly ONE audio2tool probe receipt declares split_role=discovery (a
     second one would silently widen the split ``load_split`` returns);
  3. the exposure row SAEA-PROBE-a2t-s2c-120 exists exactly once, reads
     consumed=no, carries the FULL 64-hex split identity hash verbatim, and
     registers budgets >= the plan's;
  4. the ExecutionPlan validates as bounded-discovery-probe / discovery;
  5. the payload binding builds over the 120 headroom samples (media
     confinement, sample-rate probe);
  6. the ``-np 1`` context delta is present and the WORST arm (C3's full
     152-row registry + pinned header + appended correct row(s), measured from
     the REAL rendered block, not estimated from A0) fits the single slot;
  7. the full FrozenCoreGate dry-run authorizes the model touch.

Stage-2c specifics, all model-free (same shape as Stage-2b's own additions):
  8. the Stage-2 arm-plan file the config names exists, loads through
     ``analysis.a2t_s2_read.load_arm_plan``, and ``build_flight_plan`` accepts
     it (fail-closed on any headroom sample missing from ``s1p_tool_names`` or
     naming a tool absent from the registry; no C-arm touches the S4
     derangement at all);
  9. the pinned C3 header (Stage-2b's own B2_HIGHLIGHT_HEADER, reused
     directly) still hashes to its committed constant;
 10. the feature cache is WARM (entry count recorded here so the post-flight
     delta can be shown to be zero).

Nothing here opens a socket, spawns a server, or reads a model. It also never
opens any ``outputs.jsonl``: the arm-plan file is the sanctioned mapping reuse.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

from speech_aware_evidence_acquisition.analysis.a2t_s2_read import (  # noqa: E402
    load_arm_plan,
)
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
from speech_aware_evidence_acquisition.rails.probes.a2t_s2c_flight import (  # noqa: E402
    A2T_S2C_ARMS,
    B2_HIGHLIGHT_HEADER,
    B2_HIGHLIGHT_HEADER_SHA256,
    build_flight_plan,
    load_headroom_manifest,
    render_c1_tool_schemas,
    render_c2_tool_schemas,
    render_c3_tool_schemas,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flight_identity import (  # noqa: E402
    RUN_ID,
    build_values,
    config_hash_of,
    stage2_arm_plan_path,
)
from flight_plan import (  # noqa: E402
    EXPECTED_REQUESTS,
    PLANNED_GPU_HOURS,
    PLANNED_MODEL_CALLS,
    PLANNED_SPEECH_AUDIO_SECONDS,
)

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/a2t-s2c-flight.json").read_text(encoding="utf-8")
)

# The frozen instruction template every arm fills, imported from the shipped
# adapter so the context sizing below measures the REAL prompt, not a paraphrase.
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    _INSTRUCTION_TEMPLATE,
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

    # ---- 9. pinned header (C3 reuses Stage-2b's own constant) ---------------
    computed_header = hashlib.sha256(B2_HIGHLIGHT_HEADER.encode("utf-8")).hexdigest()
    print(f"C3 header (B2_HIGHLIGHT_HEADER) sha256: {computed_header}")
    if computed_header != B2_HIGHLIGHT_HEADER_SHA256:
        problems.append(
            f"B2_HIGHLIGHT_HEADER drifted from its pinned hash {B2_HIGHLIGHT_HEADER_SHA256!r}"
        )

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    print(f"data_root: {root}")
    carrier_root = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    print(f"carrier_root (asset_dir audio2tool): {carrier_root}")

    # ---- 10. feature cache warmth ------------------------------------------
    feat_dir = Path(os.environ["SAEA_FEAT_CACHE_DIR"])
    feat_entries = sorted(p for p in feat_dir.iterdir()) if feat_dir.is_dir() else []
    print(f"feat cache {feat_dir}: {len(feat_entries)} entries")
    if len(feat_entries) == 0:
        problems.append(f"feature cache {feat_dir} is EMPTY -- this flight expects a warm cache")

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
        ("a2t-s2c-flight.json execution_plan", FLIGHT_CFG["execution_plan"]["split_identity_hash"]),
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

    # ---- 8. the reused Stage-2 arm plan + the deterministic Stage-2c plan ----
    arm_plan_path = stage2_arm_plan_path(FLIGHT_CFG)
    print(f"Stage-2 arm-plan (REUSED VERBATIM, never re-derived): {arm_plan_path}")
    if not arm_plan_path.is_file():
        problems.append(f"Stage-2 arm-plan missing: {arm_plan_path}")
        print("PRE-FLIGHT PROBLEMS (fatal, cannot continue without the arm plan)")
        for p in problems:
            print(f"  - {p}")
        return 1
    arm_plan = load_arm_plan(arm_plan_path)
    print(
        f"arm plan loaded: seed={arm_plan.seed} headroom={len(arm_plan.headroom_ids)} "
        f"s1p={len(arm_plan.s1p_tool_names)} (s4/derangement present but UNUSED by any C-arm)"
    )
    if arm_plan.seed != int(FLIGHT_CFG["seed"]):
        problems.append(
            f"arm-plan seed {arm_plan.seed} != flight config seed {FLIGHT_CFG['seed']}"
        )

    registry_rows = load_tool_registry(lock, root)
    full_registry_text = render_tool_schemas(lock, root)
    print(f"registry: {len(registry_rows)} rows, full text {len(full_registry_text)} chars")
    fplan = build_flight_plan(
        headroom, arm_plan, registry_rows, full_registry_text, seed=int(FLIGHT_CFG["seed"])
    )
    total_requests = 3 * len(fplan.headroom_ids)
    print(f"flight plan: {total_requests} requests over arms {A2T_S2C_ARMS}")
    if total_requests != EXPECTED_REQUESTS:
        problems.append(f"plan yields {total_requests} requests, registration declares {EXPECTED_REQUESTS}")
    if tuple(FLIGHT_CFG["arms"]) != A2T_S2C_ARMS:
        problems.append(f"config arms {FLIGHT_CFG['arms']} != module arms {A2T_S2C_ARMS}")

    roster_sizes = sorted(len(v) for v in fplan.correct_tool_names_by_sample.values())
    print(
        f"C-arm roster sizes (S1p's own shape verbatim): min={roster_sizes[0]} "
        f"max={roster_sizes[-1]} single={sum(1 for n in roster_sizes if n == 1)}/{len(roster_sizes)}"
    )

    one_pass = sum(s.audio_seconds for s in samples)
    metered_audio = 3.0 * one_pass
    max_item = max(s.audio_seconds for s in samples)
    print(
        f"metered audio seconds for one full flight: {metered_audio:.2f} "
        f"(one pass {one_pass:.2f}, longest item {max_item:.2f})"
    )
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

    # ---- 6. context sizing (measured on the REAL rendered blocks) -----------
    values = build_values(REPO)
    argv = [str(t) for t in values["server_args"]]
    print(f"server_args (after the -np delta): {argv}")
    ctx = int(argv[argv.index("-c") + 1])
    npar = int(argv[argv.index("-np") + 1])
    per_slot = ctx // npar
    print(f"per-slot context: {ctx}/{npar} = {per_slot} tokens")
    if npar != 1:
        problems.append(f"-np is {npar}, delta 4 did not apply")

    worst_c1_chars = 0
    worst_c2_chars = 0
    worst_c3_chars = 0
    seed = int(FLIGHT_CFG["seed"])
    for sample_id in fplan.headroom_ids:
        rows = [fplan.registry_index[n] for n in fplan.correct_tool_names_by_sample[sample_id]]
        c1_prompt = _INSTRUCTION_TEMPLATE.format(
            tool_schemas=render_c1_tool_schemas(rows, seed=seed, sample_id=sample_id)
        )
        worst_c1_chars = max(worst_c1_chars, len(c1_prompt))
        c2_prompt = _INSTRUCTION_TEMPLATE.format(tool_schemas=render_c2_tool_schemas(rows))
        worst_c2_chars = max(worst_c2_chars, len(c2_prompt))
        c3_prompt = _INSTRUCTION_TEMPLATE.format(
            tool_schemas=render_c3_tool_schemas(fplan.full_registry_text, rows)
        )
        worst_c3_chars = max(worst_c3_chars, len(c3_prompt))
    a0_prompt_chars = len(_INSTRUCTION_TEMPLATE.format(tool_schemas=full_registry_text))
    print(f"A0's own full-registry system prompt: {a0_prompt_chars} chars (~{a0_prompt_chars//4} tokens)")
    print(f"worst C1 system prompt: {worst_c1_chars} chars (~{worst_c1_chars//4} tokens)")
    print(f"worst C2 system prompt: {worst_c2_chars} chars (~{worst_c2_chars//4} tokens)")
    print(
        f"worst C3 system prompt: {worst_c3_chars} chars (~{worst_c3_chars//4} tokens); "
        f"delta over A0 = +{worst_c3_chars - a0_prompt_chars} chars"
    )
    if worst_c3_chars <= a0_prompt_chars:
        problems.append("C3 prompt is not larger than A0's -- the highlighted correct row did not append")

    max_out = int(values["decoding_params"].get("max_tokens", 0))
    worst_sequence = worst_c3_chars // 4 + 500 + max_out
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

    measurement = {
        "run_id": RUN_ID,
        "arms": list(A2T_S2C_ARMS),
        "n_headroom_samples": len(fplan.headroom_ids),
        "n_requests_planned": total_requests,
        "one_pass_audio_seconds": round(one_pass, 3),
        "metered_audio_seconds_expected": round(metered_audio, 3),
        "longest_item_audio_seconds": round(max_item, 3),
        "worst_case_audio_seconds_within_call_budget": round(worst_case_audio, 3),
        "a0_full_registry_prompt_chars": a0_prompt_chars,
        "worst_c1_prompt_chars": worst_c1_chars,
        "worst_c2_prompt_chars": worst_c2_chars,
        "worst_c3_prompt_chars": worst_c3_chars,
        "roster_size_min": roster_sizes[0],
        "roster_size_max": roster_sizes[-1],
        "single_tool_samples": sum(1 for n in roster_sizes if n == 1),
        "per_slot_context_tokens": per_slot,
        "config_hash": cfg_hash,
        "protocol_hash": phash,
        "split_identity_hash": split_hash,
        "stage2_arm_plan": str(arm_plan_path),
        "stage2_arm_plan_seed": arm_plan.seed,
        "feat_cache_dir": str(feat_dir),
        "feat_cache_entries_preflight": len(feat_entries),
        "planned_budgets": {
            "model_calls": PLANNED_MODEL_CALLS,
            "speech_audio_seconds": PLANNED_SPEECH_AUDIO_SECONDS,
            "gpu_hours": PLANNED_GPU_HOURS,
        },
    }
    out = Path(os.environ["SCRATCH"]) / "preflight-split-measurement.json"
    out.write_text(json.dumps(measurement, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"measurement written: {out}")

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
