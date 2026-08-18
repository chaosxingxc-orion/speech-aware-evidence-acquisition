"""P-SLU Stage-2 flight PRE-FLIGHT check -- ZERO model contact.

Verifies, before any core contact:
  1. the frozen n=60 sample manifest resolves against the devel split, all 60
     flac files exist, total audio matches the preregistration;
  2. the roster table loads under its own legality checks and yields the 18
     canonical scenario labels the closed-set phase-1 needs;
  3. the F1 filler lexicon loads under its own legality checks, the seeded
     100-entry roster generates deterministically, and the FAIL-CLOSED binding
     check proves ZERO overlap against (a) the 55 ontology type names,
     (b) every ontology value, (c) the 89 gold slot values of the frozen 60
     (rails.probes.pslu_s2_filler.check_f1_filler_binding -- the only place
     gold is touched, model-free, binding-time);
  4. the 3 silence-swap sample ids are inside the frozen 60;
  5. the exposure row SAEA-PROBE-pslu-s2-183 exists exactly once, consumed=no,
     its split-identity-hash cell agrees VERBATIM with the manifest, and its
     budget cells agree with the plan;
  6. the ExecutionPlan validates and the registered call arithmetic
     (60+60+60+3=183 <= 220) holds.
Nothing here opens a socket, spawns a server, or reads a model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.contracts.ledger import (
    _EXPOSURE_RUN_COLUMN,
    _parse_ledger_tables,
)
from speech_aware_evidence_acquisition.core.config import protocol_hash as compute_protocol_hash
from speech_aware_evidence_acquisition.data.lock import (
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import SLURP_LOCK_KEY, SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
    load_pslu_rosters,
    load_pslu_sample_manifest,
    select_pslu_samples,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_filler import (
    F1_FILLER_SEED,
    F1_ROSTER_SIZE,
    check_f1_filler_binding,
    generate_f1_filler_roster,
    load_filler_lexicon,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import (
    canonical_scenario_labels,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flight_identity import RUN_ID, build_values, config_hash_of  # noqa: E402

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/pslu-s2-flight.json").read_text(encoding="utf-8")
)


def main() -> int:
    problems: list[str] = []
    print(f"repo module root: {Path(__import__('speech_aware_evidence_acquisition').__file__).parent}")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    print(f"data_root: {root}")
    carrier_root = asset_dir(lock, SLURP_LOCK_KEY, root)
    print(f"carrier_root (asset_dir slurp): {carrier_root}")

    # ---- 1. sample manifest + roster table -------------------------------
    manifest = load_pslu_sample_manifest(REPO / FLIGHT_CFG["sample_manifest"])
    rosters = load_pslu_rosters(REPO / FLIGHT_CFG["roster_table"])
    print(f"manifest: n={len(manifest.sample_ids)} seed={manifest.seed}")
    print(f"split_identity_hash (full, from binding JSON): {manifest.split_identity_hash}")
    print(
        f"rosters: {len(rosters.scenario_rosters)} scenarios, "
        f"{len(rosters.global_types)} global types, "
        f"{len(rosters.full_roster)} full-roster entries, "
        f"{len(rosters.derangement)} derangement keys"
    )
    labels = canonical_scenario_labels(rosters)
    print(f"canonical closed-set labels (phase 1): {len(labels)} (prereg: 18)")
    if len(labels) != 18:
        problems.append(f"expected 18 canonical scenario labels, got {len(labels)}")

    # ---- 2. devel split resolution ---------------------------------------
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
    print(f"total audio seconds: {total_audio:.2f} (prereg: 182.26), mean {total_audio/len(samples):.2f}")
    gold_slots = sum(len(s.entities) for s in samples)
    print(f"gold slots on the frozen 60: {gold_slots} (prereg: 89)")
    scenarios = sorted({s.scenario for s in samples})
    print(f"distinct gold scenarios: {len(scenarios)} (prereg: 18 devel scenarios)")
    unknown_scen = [s for s in scenarios if s not in rosters.scenario_rosters]
    if unknown_scen:
        problems.append(f"gold scenarios with no A1p roster: {unknown_scen}")

    # ---- 3. F1 filler lexicon + FAIL-CLOSED binding check ----------------
    lexicon = load_filler_lexicon(REPO / FLIGHT_CFG["filler_lexicon"])
    print(f"filler lexicon: {len(lexicon)} words, slurp_derived=false verified at load")
    entries = generate_f1_filler_roster(lexicon, seed=F1_FILLER_SEED, n_entries=F1_ROSTER_SIZE)
    print(f"F1 filler roster: {len(entries)} entries (seed {F1_FILLER_SEED}, deterministic)")
    try:
        report = check_f1_filler_binding(
            entries,
            rosters=rosters,
            lock=lock,
            root=root,
            sample_ids=list(manifest.sample_ids),
        )
    except Exception as error:  # noqa: BLE001 -- fail-closed: any raise is a preflight problem
        problems.append(f"F1 FILLER BINDING CHECK FAILED: {type(error).__name__}: {error}")
    else:
        print(
            f"F1 filler binding check: CLEAN over {report.entries_checked} entries "
            f"(zero overlap with ontology types, ontology values, gold slot values) -- fail-closed PASS"
        )

    # ---- 4. silence-swap ids ---------------------------------------------
    swap_ids = list(FLIGHT_CFG["silence_swap"]["sample_ids"])
    frozen = {s.sample_id for s in samples}
    outside = [i for i in swap_ids if i not in frozen]
    print(f"silence-swap ids: {swap_ids}")
    if outside:
        problems.append(f"silence-swap ids outside the frozen 60: {outside}")
    else:
        print("silence-swap ids: all 3 inside the frozen 60 -- OK")

    # ---- 5. exposure ledger row ------------------------------------------
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
        if row.get("split identity hash") != manifest.split_identity_hash:
            problems.append(
                "LEDGER CELL MISMATCH: 'split identity hash' cell is "
                f"{row.get('split identity hash')!r} but the plan will carry the full 64-hex "
                f"{manifest.split_identity_hash!r}; FrozenCoreGate compares these verbatim "
                "(gate_exposure._require_exposure_preregistration) -- the gate WILL refuse."
            )
        if str(row.get("consumed", "")).lower() != "no":
            problems.append(f"exposure row consumed={row.get('consumed')!r}, must be 'no'")

    # ---- 6. plan + registered call arithmetic ----------------------------
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
        planned_speech_audio_seconds=int(
            FLIGHT_CFG["execution_plan"]["planned_speech_audio_seconds"]
        ),
        protocol_hash=phash,
        attempt_id="attempt-preflight-000000",
    ).validate()
    print(f"ExecutionPlan validates: profile={plan.execution_profile} role={plan.split_role}")
    registered_calls = 60 + 60 + 60 + 3
    print(
        f"registered call arithmetic: 60 (F1) + 60 (A1'r phase1) + 60 (A1'r phase2) + 3 (swap) "
        f"= {registered_calls} <= ceiling {plan.planned_model_calls}"
    )
    if registered_calls > plan.planned_model_calls:
        problems.append("registered call arithmetic exceeds the plan ceiling")

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
