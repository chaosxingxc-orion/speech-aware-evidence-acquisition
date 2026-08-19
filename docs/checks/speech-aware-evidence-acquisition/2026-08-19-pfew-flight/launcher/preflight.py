"""P-FEW flight PRE-FLIGHT check -- ZERO model contact.

Structurally the archived P-TRAP pre-flight
(``docs/checks/speech-aware-evidence-acquisition/2026-08-19-ptrap-flight/
launcher/preflight.py``), with the P-TRAP-specific trap-binding items replaced
by this probe's own demo-binding items. Verifies, before any core contact:

  1. the machinery's own import-time ontology-miner guards pass and the frozen
     60-sample manifest's ``split_identity_hash`` equals
     ``rails.probes.pfew_flight.EXPECTED_SPLIT_IDENTITY_HASH`` VERBATIM (the
     module's own fail-closed pin);
  2. the roster table loads under its own legality checks and yields exactly
     the 18 canonical scenario labels, and the reused A1'r closed-set phase-1
     packet builds from them;
  3. the frozen 60 resolve against the devel split and every flac is present;
  4. the reviewed demo binding re-derives to the SAME ``DemoBinding.sha256``,
     FS-BAL carries K=4 all-distinct canonical labels on every sample, FS-SKEW
     carries K=4 demos all under the ONE global seeded skew label, every demo
     id is TRAIN-namespaced, and NO demo's slurp_id collides with a target
     devel utterance id -- the binding-time fail-closed devel-exclusion check
     preregistration section 5 mandates, re-run here independently of
     ``build_demo_binding``'s own internal copy;
  5. all three arms' supply packets compose (FS-NONE byte-identical to the
     reused closed-set packet; FS-BAL/FS-SKEW prepend the demo block ahead of
     that SAME text);
  6. the exposure row ``SAEA-PROBE-pfew-180`` exists exactly once, consumed=no,
     its split-identity-hash cell agrees VERBATIM with the manifest, and its
     budget cells cover the plan AND match the launcher's transcribed
     ``REGISTERED_CEILINGS``;
  7. the ExecutionPlan validates and the registered call arithmetic
     (3 x 60 = 180 <= 200) plus the metered audio arithmetic hold;
  8. the RUN-TOTAL budget is feasible for a fresh attempt (sibling attempts'
     durable spend on this run_id is charged against the SAME plan ceiling).

Nothing here opens a socket, spawns a server, or reads a model. The demo
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
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import SLURP_LOCK_KEY, SlurpAdapter  # noqa: E402
from speech_aware_evidence_acquisition.rails.probes.pfew_flight import (  # noqa: E402
    EXPECTED_SPLIT_IDENTITY_HASH,
    FS_BAL_ARM,
    FS_BAL_K,
    FS_NONE_ARM,
    FS_SKEW_ARM,
    FS_SKEW_K,
    PFEW_ARMS,
    TRAIN_SAMPLE_ID_PREFIX,
    assert_split_identity_hash,
    pfew_supply_packet,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    load_pslu_rosters,
    load_pslu_sample_manifest,
    select_pslu_samples,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import (  # noqa: E402
    canonical_scenario_labels,
    closed_set_phase1_supply_packet,
)

from binding import build_binding, stats_document  # noqa: E402
from flight_identity import (  # noqa: E402
    CARRIER_LOCK_KEY,
    EXECUTION_PROFILE,
    PLANNED_BUDGETS,
    PREREGISTRATION_RELPATH,
    REGISTERED_CEILINGS,
    ROSTER_TABLE_RELPATH,
    RUN_ID,
    SAMPLE_MANIFEST_RELPATH,
    SPLIT_ROLE,
    build_values,
    config_hash_of,
)


def main() -> int:
    problems: list[str] = []
    print(f"repo module root: {Path(__import__('speech_aware_evidence_acquisition').__file__).parent}")
    print(f"preregistration: {PREREGISTRATION_RELPATH}")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    print(f"data_root: {root}")
    print(f"carrier_root (asset_dir slurp): {asset_dir(lock, SLURP_LOCK_KEY, root)}")

    # ---- 1. split identity ------------------------------------------------
    manifest = load_pslu_sample_manifest(REPO / SAMPLE_MANIFEST_RELPATH)
    print(f"manifest: n={len(manifest.sample_ids)} seed={manifest.seed}")
    print(f"split_identity_hash (full, from binding JSON): {manifest.split_identity_hash}")
    try:
        assert_split_identity_hash(manifest.split_identity_hash)
    except Exception as error:  # noqa: BLE001 -- fail-closed
        problems.append(f"SPLIT IDENTITY PIN FAILED: {type(error).__name__}: {error}")
    else:
        print("split identity: manifest == machinery EXPECTED_SPLIT_IDENTITY_HASH verbatim -- PASS")
    print(f"  machinery pin: {EXPECTED_SPLIT_IDENTITY_HASH}")
    print(f"arms: machinery PFEW_ARMS == {list(PFEW_ARMS)}")

    # ---- 2. roster table + canonical labels + reused closed-set packet ------
    rosters = load_pslu_rosters(REPO / ROSTER_TABLE_RELPATH)
    canonical = canonical_scenario_labels(rosters)
    print(
        f"rosters: {len(rosters.scenario_rosters)} scenarios, {len(rosters.global_types)} global types, "
        f"{len(rosters.full_roster)} full-roster entries"
    )
    print(f"canonical scenario labels: {len(canonical)} -> {list(canonical)}")
    if len(canonical) != 18:
        problems.append(f"canonical label count {len(canonical)} != the registered 18")
    closed_set = closed_set_phase1_supply_packet(canonical)
    print(
        f"A1'r closed-set phase-1 packet: template={closed_set.assembly_template_id!r} "
        f"dose n_items={closed_set.dose.n_items} tokens~{closed_set.dose.token_count}"
    )

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
    print(f"total audio seconds (one pass): {total_audio:.2f}, mean {total_audio/len(samples):.2f}")

    # ---- 4. demo binding: re-derive, hash-check, invariants -----------------
    print()
    print("=== demo binding (REGISTERED supply-content sourcing; zero model calls) ===")
    binding_path = Path(__file__).resolve().parent / "demo-binding.json"
    if not binding_path.is_file():
        problems.append(f"reviewed demo binding missing: {binding_path} (run run_binding.sh first)")
        reviewed_sha = None
    else:
        reviewed_sha = json.loads(binding_path.read_text(encoding="utf-8"))["demo_binding_sha256"]
    binding, document = build_binding(adapter=adapter)
    print(f"re-derived demo_binding_sha256: {binding.sha256}")
    print(f"reviewed  demo_binding_sha256: {reviewed_sha}")
    if reviewed_sha is not None and reviewed_sha != binding.sha256:
        problems.append("demo binding is not reproducible: reviewed sha256 != re-derived sha256")
    else:
        print("demo binding reproducibility: PASS (deterministic from seed + frozen inputs)")

    stats = stats_document(binding, document)
    print(f"seeded GLOBAL skew label (chosen with zero gold input): {binding.skew_label!r}")
    print(f"FS-BAL K distribution: {json.dumps(stats['fs_bal_k_distribution'], sort_keys=True)}")
    print(f"FS-SKEW K distribution: {json.dumps(stats['fs_skew_k_distribution'], sort_keys=True)}")
    print(
        "FS-BAL distinct-label-per-sample distribution: "
        f"{json.dumps(stats['fs_bal_distinct_label_count_distribution'], sort_keys=True)}"
    )
    print(f"FS-BAL label usage: {json.dumps(stats['fs_bal_label_usage'], sort_keys=True)}")
    print(
        f"distinct TRAIN donors: FS-BAL {stats['fs_bal_distinct_train_donors']}, "
        f"FS-SKEW {stats['fs_skew_distinct_train_donors']}"
    )
    print(
        "TRAIN pool coverage (label -> candidates): "
        f"{json.dumps(stats['train_demo_pool_label_coverage'], sort_keys=True)}"
    )

    devel_utterance_ids = {s.utterance_id for s in samples}
    bal_k_violations: list[str] = []
    bal_distinct_violations: list[str] = []
    skew_k_violations: list[str] = []
    skew_label_violations: list[str] = []
    namespace_violations: list[str] = []
    devel_overlap_violations: list[str] = []
    label_legality_violations: list[str] = []
    canonical_set = set(canonical)
    for sample_id, demo_set in binding.per_sample.items():
        if len(demo_set.fs_bal_demos) != FS_BAL_K:
            bal_k_violations.append(sample_id)
        if len({d.scenario_label for d in demo_set.fs_bal_demos}) != len(demo_set.fs_bal_demos):
            bal_distinct_violations.append(sample_id)
        if len(demo_set.fs_skew_demos) != FS_SKEW_K:
            skew_k_violations.append(sample_id)
        if {d.scenario_label for d in demo_set.fs_skew_demos} != {binding.skew_label}:
            skew_label_violations.append(sample_id)
        for demo in tuple(demo_set.fs_bal_demos) + tuple(demo_set.fs_skew_demos):
            if not demo.train_sample_id.startswith(TRAIN_SAMPLE_ID_PREFIX):
                namespace_violations.append(sample_id)
                continue
            if demo.scenario_label not in canonical_set:
                label_legality_violations.append(sample_id)
            slurp_id = str(int(demo.train_sample_id[len(TRAIN_SAMPLE_ID_PREFIX) :]))
            if slurp_id in devel_utterance_ids:
                devel_overlap_violations.append(sample_id)
    for label, offenders in (
        (f"FS-BAL demo count != {FS_BAL_K}", bal_k_violations),
        ("FS-BAL demo labels not all distinct", bal_distinct_violations),
        (f"FS-SKEW demo count != {FS_SKEW_K}", skew_k_violations),
        ("FS-SKEW demo labels != {the one global skew label}", skew_label_violations),
        ("a demo id is not TRAIN-namespaced", namespace_violations),
        ("a demo label is outside the canonical 18", label_legality_violations),
        ("a demo slurp_id collides with a TARGET devel utterance id", devel_overlap_violations),
    ):
        if offenders:
            problems.append(f"DEMO BINDING VIOLATION -- {label}: {sorted(set(offenders))[:5]}")
        else:
            print(f"binding invariant OK: no sample violates [{label}]")

    donor_counts = Counter(
        demo.train_sample_id
        for demo_set in binding.per_sample.values()
        for demo in demo_set.fs_bal_demos
    )
    print(
        f"FS-BAL donor breadth: {len(donor_counts)} distinct TRAIN ids across "
        f"{sum(donor_counts.values())} demo slots"
    )

    # ---- 5. supply packet composition per arm -------------------------------
    print()
    print("=== per-arm supply packet composition (offline, no model) ===")
    first_id = sorted(binding.per_sample)[0]
    first_set = binding.per_sample[first_id]
    none_packet = pfew_supply_packet(FS_NONE_ARM, (), canonical)
    bal_packet = pfew_supply_packet(FS_BAL_ARM, first_set.fs_bal_demos, canonical)
    skew_packet = pfew_supply_packet(FS_SKEW_ARM, first_set.fs_skew_demos, canonical)
    print(
        f"  {FS_NONE_ARM}: template={none_packet.assembly_template_id!r} items={len(none_packet.items)} "
        f"prompt_chars={len(none_packet.prompt_block)}"
    )
    print(
        f"  {FS_BAL_ARM}: template={bal_packet.assembly_template_id!r} items={len(bal_packet.items)} "
        f"prompt_chars={len(bal_packet.prompt_block)}"
    )
    print(
        f"  {FS_SKEW_ARM}: template={skew_packet.assembly_template_id!r} items={len(skew_packet.items)} "
        f"prompt_chars={len(skew_packet.prompt_block)}"
    )
    if none_packet.prompt_block != closed_set.prompt_block:
        problems.append("FS-NONE packet is not byte-identical to the reused closed-set phase-1 packet")
    else:
        print("  FS-NONE == the reused A1'r closed-set phase-1 packet, byte-identical -- PASS")
    for arm, packet in ((FS_BAL_ARM, bal_packet), (FS_SKEW_ARM, skew_packet)):
        if not packet.prompt_block.endswith(closed_set.prompt_block):
            problems.append(f"{arm} packet does not end with the reused closed-set instruction text")
        else:
            print(f"  {arm} prepends the demo block ahead of the SAME reused instruction -- PASS")

    # ---- 6. exposure ledger row --------------------------------------------
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
        if str(row.get("execution profile", "")).strip() != EXECUTION_PROFILE:
            problems.append(f"exposure row execution profile != {EXECUTION_PROFILE!r}")
        if str(row.get("split role", "")).strip() != SPLIT_ROLE:
            problems.append(f"exposure row split role != {SPLIT_ROLE!r}")
        for cell_name, planned_key, registered_key, caster in (
            ("calls", "model_calls", "model_calls", int),
            ("speech audio seconds", "speech_audio_seconds", "speech_audio_seconds", int),
            ("gpu hours", "gpu_hours", "gpu_hours", float),
        ):
            try:
                registered_value = caster(str(row.get(cell_name, "")).strip())
            except ValueError:
                problems.append(f"ledger cell {cell_name!r} is not numeric: {row.get(cell_name)!r}")
                continue
            planned_value = caster(PLANNED_BUDGETS[planned_key])
            if registered_value != caster(REGISTERED_CEILINGS[registered_key]):
                problems.append(
                    f"launcher REGISTERED_CEILINGS[{registered_key!r}]="
                    f"{REGISTERED_CEILINGS[registered_key]} disagrees with the LIVE ledger cell "
                    f"{cell_name!r}={registered_value}"
                )
            if registered_value < planned_value:
                problems.append(
                    f"ledger {cell_name!r} cell registers {registered_value} but the plan declares "
                    f"{planned_value}; FrozenCoreGate refuses when registered < planned"
                )
            else:
                print(
                    f"  budget cell {cell_name!r}: registered {registered_value} >= planned "
                    f"{planned_value} -- OK"
                )

    # ---- 7. plan + registered arithmetic ------------------------------------
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
        execution_profile=EXECUTION_PROFILE,
        carrier_lock_key=CARRIER_LOCK_KEY,
        split_role=SPLIT_ROLE,
        split_identity_hash=manifest.split_identity_hash,
        planned_model_calls=int(PLANNED_BUDGETS["model_calls"]),
        planned_gpu_hours=float(PLANNED_BUDGETS["gpu_hours"]),
        planned_speech_audio_seconds=int(PLANNED_BUDGETS["speech_audio_seconds"]),
        protocol_hash=phash,
        attempt_id="attempt-preflight-000000",
    ).validate()
    print(f"ExecutionPlan validates: profile={plan.execution_profile} role={plan.split_role}")
    registered_calls = len(PFEW_ARMS) * len(samples)
    print(
        f"registered call arithmetic: 60 x {len(PFEW_ARMS)} arms = {registered_calls} <= plan ceiling "
        f"{plan.planned_model_calls} <= registered ceiling {REGISTERED_CEILINGS['model_calls']}"
    )
    if registered_calls > plan.planned_model_calls:
        problems.append("registered call arithmetic exceeds the plan ceiling")
    if registered_calls > int(REGISTERED_CEILINGS["model_calls"]):
        problems.append("registered call arithmetic exceeds the REGISTERED ceiling")
    metered_audio = total_audio * len(PFEW_ARMS)
    print(
        f"audio-seconds arithmetic (METERED): {total_audio:.2f} x {len(PFEW_ARMS)} arms = "
        f"{metered_audio:.2f} <= plan ceiling {plan.planned_speech_audio_seconds}"
    )
    if metered_audio > plan.planned_speech_audio_seconds:
        problems.append("metered audio-seconds estimate exceeds the plan ceiling")

    # ---- 8. RUN-TOTAL budget feasibility ------------------------------------
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
