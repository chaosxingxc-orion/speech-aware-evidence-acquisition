"""P-TRAP flight PRE-FLIGHT check -- ZERO model contact.

Structurally the archived P-KEY pre-flight
(``docs/checks/speech-aware-evidence-acquisition/2026-08-19-pkey2-flight/
launcher/preflight.py``), with the P-KEY-specific text-parity/silence-swap
items replaced by this probe's own trap-binding items. Verifies, before any
core contact:

  1. the machinery's own import-time ontology-miner guards pass and the
     frozen 60-sample manifest's ``split_identity_hash`` equals
     ``rails.probes.ptrap_flight.EXPECTED_SPLIT_IDENTITY_HASH`` VERBATIM (the
     module's own fail-closed pin), and the committed flight config's
     ``execution_plan.split_identity_hash`` agrees;
  2. the roster table loads under its own legality checks and the A3-form
     100-entry packet builds via the SAME frozen ``pslu_supply_packet``;
  3. the frozen 60 resolve against the devel split and every flac is present;
  4. the reviewed trap binding re-derives to the SAME canonical hash, every
     V1 K is <= TRAP_K_CAP, every V2 K is <= its own sample's V1 K, every V2
     entry is fixed-point-free, and NO appended entry equals (post-
     normalization) any gold slot value of its own target sample -- the
     binding-time fail-closed check preregistration section 2 mandates,
     re-run here independently of ``run_ptrap_flight``'s own end-of-flight
     copy;
  5. the exposure row ``SAEA-PROBE-ptrap-120`` exists exactly once,
     consumed=no, its split-identity-hash cell agrees VERBATIM with the
     manifest, and its budget cells cover the plan;
  6. the ExecutionPlan validates and the registered call arithmetic
     (60 x 2 = 120 <= 140) plus the metered audio arithmetic hold;
  7. the RUN-TOTAL budget is feasible for a fresh attempt (sibling attempts'
     durable spend on this run_id is charged against the SAME plan ceiling).

Nothing here opens a socket, spawns a server, or reads a model. The trap
binding it re-derives is the registered supply-content sourcing step, not a
result read: no response is scored, ranked or displayed.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speech_aware_evidence_acquisition.contracts import ExecutionPlan  # noqa: E402
from speech_aware_evidence_acquisition.contracts.ledger import (  # noqa: E402
    _EXPOSURE_RUN_COLUMN,
    _parse_ledger_tables,
)
from speech_aware_evidence_acquisition.core.config import protocol_hash as compute_protocol_hash  # noqa: E402
from speech_aware_evidence_acquisition.core.retrieval import normalize_term  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import SLURP_LOCK_KEY, SlurpAdapter  # noqa: E402
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    load_pslu_rosters,
    load_pslu_sample_manifest,
    pslu_supply_packet,
    select_pslu_samples,
)
from speech_aware_evidence_acquisition.rails.probes.ptrap_flight import (  # noqa: E402
    EXPECTED_SPLIT_IDENTITY_HASH,
    PTRAP_ARMS,
    TRAP_K_CAP,
    _gold_filler_values,
    assert_split_identity_hash,
)

from binding import build_binding, canonical_hash, consumed_attempt_dir, stats_document  # noqa: E402
from flight_identity import RUN_ID, build_values, config_hash_of  # noqa: E402

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/ptrap-flight.json").read_text(encoding="utf-8")
)


def main() -> int:
    problems: list[str] = []
    print(f"repo module root: {Path(__import__('speech_aware_evidence_acquisition').__file__).parent}")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    print(f"data_root: {root}")
    print(f"carrier_root (asset_dir slurp): {asset_dir(lock, SLURP_LOCK_KEY, root)}")

    # ---- 1. split identity ------------------------------------------------
    manifest = load_pslu_sample_manifest(REPO / FLIGHT_CFG["sample_manifest"])
    print(f"manifest: n={len(manifest.sample_ids)} seed={manifest.seed}")
    print(f"split_identity_hash (full, from binding JSON): {manifest.split_identity_hash}")
    try:
        assert_split_identity_hash(manifest.split_identity_hash)
    except Exception as error:  # noqa: BLE001 -- fail-closed
        problems.append(f"SPLIT IDENTITY PIN FAILED: {type(error).__name__}: {error}")
    else:
        print("split identity: manifest == machinery EXPECTED_SPLIT_IDENTITY_HASH verbatim -- PASS")
    print(f"  machinery pin: {EXPECTED_SPLIT_IDENTITY_HASH}")
    if FLIGHT_CFG["execution_plan"]["split_identity_hash"] != manifest.split_identity_hash:
        problems.append("flight config execution_plan.split_identity_hash != manifest hash")
    if list(FLIGHT_CFG["arms"]) != list(PTRAP_ARMS):
        problems.append(f"config arms {FLIGHT_CFG['arms']!r} != machinery PTRAP_ARMS {list(PTRAP_ARMS)!r}")
    else:
        print(f"arms: config == machinery PTRAP_ARMS == {list(PTRAP_ARMS)}")

    # ---- 2. roster table + A3 packet ---------------------------------------
    rosters = load_pslu_rosters(REPO / FLIGHT_CFG["roster_table"])
    print(
        f"rosters: {len(rosters.scenario_rosters)} scenarios, {len(rosters.global_types)} global types, "
        f"{len(rosters.full_roster)} full-roster entries, {len(rosters.derangement)} derangement keys"
    )
    a3 = pslu_supply_packet("A3", scenario=None, rosters=rosters)
    print(f"A3 packet: {len(a3.items)} items, dose n_items={a3.dose.n_items} (prereg: 100-entry roster)")
    if a3.dose.n_items != 100:
        problems.append(f"A3 packet dose n_items {a3.dose.n_items} != 100")
    if len(rosters.full_roster) != 100:
        problems.append(f"full_roster carries {len(rosters.full_roster)} entries, expected 100")

    # ---- 3. devel split resolution -----------------------------------------
    adapter = SlurpAdapter(lock, root, repo_root=REPO)
    all_devel = adapter.load_split("devel")
    print(f"devel split resolved: {len(all_devel)} samples")
    samples = select_pslu_samples(all_devel, manifest)
    print(f"frozen sample set selected: {len(samples)}")
    missing = [s.sample_id for s in samples if not (root / s.media_relpath).is_file()]
    if missing:
        problems.append(f"{len(missing)} sample media missing: {missing[:5]}")
    total_audio = sum(s.audio_seconds for s in samples)
    print(f"media resolved: {len(samples) - len(missing)}/{len(samples)} flac present")
    print(f"total audio seconds: {total_audio:.2f} (config: 182.26), mean {total_audio/len(samples):.2f}")

    # ---- 4. trap binding: re-derive, hash-check, invariants -----------------
    print()
    print("=== trap binding (REGISTERED supply-content sourcing; zero model calls) ===")
    print(f"consumed A0 attempt dir: {consumed_attempt_dir()}")
    binding_path = Path(__file__).resolve().parent / "trap-binding.json"
    if not binding_path.is_file():
        problems.append(f"reviewed trap binding missing: {binding_path} (run run_binding.sh first)")
        reviewed_hash = None
    else:
        reviewed_hash = canonical_hash(json.loads(binding_path.read_text(encoding="utf-8")))
    trap_sets, document = build_binding()
    rebuilt_hash = canonical_hash(document)
    print(f"re-derived binding hash: {rebuilt_hash}")
    print(f"reviewed  binding hash: {reviewed_hash}")
    if reviewed_hash is not None and reviewed_hash != rebuilt_hash:
        problems.append("trap binding is not reproducible: reviewed hash != re-derived hash")
    else:
        print("trap binding reproducibility: PASS (deterministic from seed + consumed attempt)")

    stats = stats_document(document, rebuilt_hash)
    print(f"V1 K distribution (K -> n samples): {json.dumps(stats['v1_k_distribution'], sort_keys=True)}")
    print(f"V2 K distribution (K -> n samples): {json.dumps(stats['v2_k_distribution'], sort_keys=True)}")
    print(f"V1 K=0 samples (EXCLUDED from the capture denominator): {len(stats['v1_k_zero_sample_ids'])}")
    print(f"common denominator (V1 K>=1): {stats['common_denominator_n']}")
    print(f"V1 appended entries total: {stats['v1_k_total']}; V2 total: {stats['v2_k_total']}")
    print(
        f"V2 shorter than V1 (donor pool dry) on {len(stats['v2_shorter_than_v1_sample_ids'])} sample(s)"
    )
    print(
        f"gold zero-overlap exclusions dropped: V1 {stats['v1_gold_overlap_exclusions_total']}, "
        f"V2 {stats['v2_gold_overlap_exclusions_total']}"
    )

    gold_entities_by_sample_id = {s.sample_id: s.entities for s in samples}
    k_cap_violations: list[str] = []
    length_violations: list[str] = []
    fixed_point_violations: list[str] = []
    gold_overlap_violations: list[str] = []
    for sample_id, trap_set in trap_sets.items():
        if trap_set.v1_k > TRAP_K_CAP:
            k_cap_violations.append(sample_id)
        if trap_set.v2_k > trap_set.v1_k:
            length_violations.append(sample_id)
        for entry in trap_set.v2_entries:
            if entry.origin_sample_id == sample_id:
                fixed_point_violations.append(sample_id)
        gold_values = _gold_filler_values(gold_entities_by_sample_id.get(sample_id, ()))
        for entry in tuple(trap_set.v1_entries) + tuple(trap_set.v2_entries):
            if normalize_term(entry.filler) in gold_values:
                gold_overlap_violations.append(sample_id)
    for label, offenders in (
        (f"V1 K > TRAP_K_CAP({TRAP_K_CAP})", k_cap_violations),
        ("V2 K > that sample's own V1 K (length-matched invariant)", length_violations),
        ("V2 fixed-point (origin_sample_id == target)", fixed_point_violations),
        ("appended entry equals a gold slot value of its own target sample", gold_overlap_violations),
    ):
        if offenders:
            problems.append(f"TRAP BINDING VIOLATION -- {label}: {sorted(set(offenders))[:5]}")
        else:
            print(f"binding invariant OK: no sample violates [{label}]")
    v1_origin_ok = all(
        entry.origin_sample_id == sample_id
        for sample_id, ts in trap_sets.items()
        for entry in ts.v1_entries
    )
    print(f"V1 self-percept origin invariant (every entry's origin == its own target): {v1_origin_ok}")
    if not v1_origin_ok:
        problems.append("a V1 trap entry's origin_sample_id is not its own target sample")
    donor_ids = Counter(
        entry.origin_sample_id for ts in trap_sets.values() for entry in ts.v2_entries
    )
    print(f"V2 donor breadth: {len(donor_ids)} distinct origin samples across {sum(donor_ids.values())} entries")

    # ---- 5. exposure ledger row --------------------------------------------
    print()
    rows = _parse_ledger_tables((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8"))
    matched = [r for r in rows if r.get(_EXPOSURE_RUN_COLUMN) == RUN_ID]
    ledger_calls_cell = matched[0].get("calls") if len(matched) == 1 else "<unresolved>"
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
        if row.get("split identity hash") != manifest.split_identity_hash:
            problems.append(
                "LEDGER CELL MISMATCH: 'split identity hash' cell is "
                f"{row.get('split identity hash')!r} but the plan will carry "
                f"{manifest.split_identity_hash!r}; FrozenCoreGate compares these verbatim"
            )
        if str(row.get("consumed", "")).lower() != "no":
            problems.append(f"exposure row consumed={row.get('consumed')!r}, must be 'no'")
        for cell_name, planned_value, caster in (
            ("calls", FLIGHT_CFG["execution_plan"]["planned_model_calls"], int),
            ("speech audio seconds", FLIGHT_CFG["execution_plan"]["planned_speech_audio_seconds"], int),
            ("gpu hours", FLIGHT_CFG["execution_plan"]["planned_gpu_hours"], float),
        ):
            try:
                registered_value = caster(str(row.get(cell_name, "")).strip())
            except ValueError:
                problems.append(f"ledger cell {cell_name!r} is not numeric: {row.get(cell_name)!r}")
                continue
            if registered_value < caster(planned_value):
                problems.append(
                    f"ledger {cell_name!r} cell registers {registered_value} but the plan declares "
                    f"{planned_value}; FrozenCoreGate refuses when registered < planned"
                )
            else:
                print(f"  budget cell {cell_name!r}: registered {registered_value} >= planned {planned_value} -- OK")

    # ---- 6. plan + registered arithmetic ------------------------------------
    print()
    values = build_values(REPO)
    cfg_hash = config_hash_of(values)
    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), manifest.split_identity_hash)
    print(f"config_hash: {cfg_hash}")
    print(f"protocol_hash: {phash}")
    print(f"server_env: {values['server_env']}")
    print(f"server_args: {values['server_args']}")
    print(f"decoding_params: {values['decoding_params']}")
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
        attempt_id="attempt-preflight-000000",
    ).validate()
    print(f"ExecutionPlan validates: profile={plan.execution_profile} role={plan.split_role}")
    registered_calls = len(PTRAP_ARMS) * len(samples)
    print(
        f"registered call arithmetic: 60 (V1) + 60 (V2) = {registered_calls} <= plan ceiling "
        f"{plan.planned_model_calls} <= registered ceiling {FLIGHT_CFG['cost_budget']['call_ceiling']}"
    )
    if registered_calls > plan.planned_model_calls:
        problems.append("registered call arithmetic exceeds the plan ceiling")
    metered_audio = total_audio * len(PTRAP_ARMS)
    print(
        f"audio-seconds arithmetic (METERED): {total_audio:.2f} x {len(PTRAP_ARMS)} arms = "
        f"{metered_audio:.2f} <= plan ceiling {plan.planned_speech_audio_seconds}"
    )
    if metered_audio > plan.planned_speech_audio_seconds:
        problems.append("metered audio-seconds estimate exceeds the plan ceiling")

    # ---- 7. RUN-TOTAL budget feasibility ------------------------------------
    from speech_aware_evidence_acquisition.core.attempts import AttemptStore  # noqa: PLC0415

    store = AttemptStore(attempts_root=root / "attempts")
    prior_calls, prior_audio = store.prior_actual_usage(RUN_ID, exclude_attempt_id=None)
    print()
    print("=== run-total budget feasibility (sibling attempts count) ===")
    print(f"prior durable spend on {RUN_ID}: calls={prior_calls}, audio_seconds={prior_audio:.2f}")
    headroom_calls = plan.planned_model_calls - prior_calls
    headroom_audio = plan.planned_speech_audio_seconds - prior_audio
    print(f"headroom for a FRESH attempt: calls={headroom_calls}, audio_seconds={headroom_audio:.2f}")
    print(f"this flight needs: calls={registered_calls}, metered audio_seconds={metered_audio:.2f}")
    if registered_calls > headroom_calls:
        problems.append(
            f"RUN-TOTAL CALL BUDGET INFEASIBLE: needs {registered_calls}, {headroom_calls} remain "
            f"({prior_calls} already durably spent). Registered ledger ceiling {ledger_calls_cell}. "
            "Resolution is a REGISTRATION act, not an implementer edit."
        )
    else:
        print("call headroom: sufficient for a full fresh attempt -- OK")
    if metered_audio > headroom_audio:
        problems.append(
            f"RUN-TOTAL AUDIO BUDGET INFEASIBLE: needs {metered_audio:.2f}s, {headroom_audio:.2f}s remain"
        )
    else:
        print("audio headroom: sufficient for a full fresh attempt -- OK")

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
