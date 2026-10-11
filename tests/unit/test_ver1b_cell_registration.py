"""VER-1b (owner decision 257, decision 258 option A): the registered cell is exactly what its package says it is (model-free, HELD).

Reads the committed fragments and package files only (no data root, no model, no server). Proves: the fragment is the R5 composed arm
(the COMP-1b Fold A module block, compiled) plus EXACTLY the registered diff (policy id, module declaration dropped, v4g
deliver_normaliser dropped, Solver samples 3 / greedy_first / plurality-support commit at min_support 2), and that it equals the
committed VER-1a Fold B fragment except for the Fold A pins and the sample parameters; the program is the registered review-off family
member ``phase-native-module-v1-c4`` and the loader's graph ceiling is 4; the plan budgets are the contact arithmetic (1,080 x 4 =
4,320), the FIT cap is structural (rows x ceiling x 4); the identities (run, attempt, chain, flip, repin, ledger) agree; the roster is
TRAIN Fold A, the rule is the one FIXED on Fold B and named in the facts and the preregistration; the stage3_measurement block is an
offline sealed pool with no benefit claim; the stage-3 label resolves; the finite-completion and ReAct-exhaustion policies are declared;
and the cell is HELD with DRAFT ledger rows.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "flights" / "ver"))
sys.path.insert(0, str(REPO / "scripts" / "checks"))

import ver1b_derive_cells as derive  # noqa: E402
import ver1b_family as vf  # noqa: E402
import ver1c_family as cf  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import MODULE_PROGRAM_FAMILY_IDS, default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402


def _load(relpath: str) -> dict:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _baseline(kind: str, names=vf.names) -> dict:
    return _load(f"configs/baseline/{names(kind)['baseline']}.json")


def _experiment(kind: str) -> dict:
    return _load(f"configs/experiment/{vf.names(kind)['experiment']}.json")


def _roster(kind: str) -> list:
    return vf.roster_items(kind)


def _ledger_rows() -> list:
    from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables

    return _parse_ledger_tables((REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8"))


def _all_draft() -> bool:
    rows = {r.get("run/experiment id"): r for r in _ledger_rows()}
    ids = [vf.ARM["run_id"], vf.ARM["fit_run_id"], vf.SMOKE["run_id"], vf.SMOKE["fit_run_id"]]
    return all("(DRAFT, root countersignature pending)" in rows[i].get("notes", "") for i in ids)


def _leaves(node, prefix=""):
    if isinstance(node, dict) and node:
        out = {}
        for key, value in node.items():
            out.update(_leaves(value, f"{prefix}.{key}" if prefix else str(key)))
        return out
    return {prefix: node}


# --- identity ------------------------------------------------------------------------------------------------------------


def test_family_identities_are_frozen():
    assert (vf.ARM["experiment"], vf.ARM["run_id"], vf.DECISION_ID, vf.DECISION_RELPATH, vf.READ_RUN_ID) == (
        "slurp-native-stage3-ver1b-samples-fold-a-v1", "SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-V1",
        "slurp-ver1b-samples-fold-a-admission-v1", "coordination/slurp-ver1b-samples-fold-a-v1/root-admission-v1.json",
        "SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-POOL-READ-V1")
    assert vf.ARM["fit_run_id"] == "SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-FIT-V1"
    assert vf.SMOKE["run_id"] == "SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-SMOKE-4-V1"
    assert vf.SMOKE["fit_run_id"] == "SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-SMOKE-4-FIT-V1"
    assert vf.SMOKE["experiment"] == "slurp-native-stage3-ver1b-samples-fold-a-smoke-4-v1"
    assert vf.ARM["attempt_id"] == "attempt-slurp-native-stage3-ver1b-samples-fold-a-generation-v1"
    assert vf.SMOKE["attempt_id"] == "attempt-slurp-native-stage3-ver1b-samples-fold-a-smoke-4-generation-v1"
    assert vf.PACKAGE == "docs/readiness/2026-10-10-slurp-ver1b-samples-fold-a-v1"
    assert vf.SAMPLES == 3 and vf.CEILING == 4 == 1 + vf.SAMPLES and vf.PROGRAM == "phase-native-module-v1-c4"
    assert vf.SOLVER_COMMIT["min_support"] == 2 and vf.SOLVER_OVERRIDES == {"temperature": 0.7, "seed_offset": 0, "greedy_first": True}
    assert vf.PROGRAM in MODULE_PROGRAM_FAMILY_IDS            # registered already: no new program id
    assert (vf.TUNING_ROSTER, vf.READ_ROSTER) == ("SLURP-EVO-FOLD-B-V2", "SLURP-EVO-FOLD-A-V2")
    assert (vf.RULE_N, vf.RULE_S, vf.RULE_THETA) == (3, 2, 0.2) and vf.MIN_SUPPORT == vf.RULE_S
    assert vf.ROWS == 1080 and vf.SMOKE_ROWS == 4


def test_the_family_is_parameterised_not_hard_coded():
    """The sample count and the support threshold are parameters: every derived piece follows them (no re-edit of prose)."""

    assert vf.SAMPLES_WORD == "three" and vf.LAST_SAMPLE == 2 and vf.DRAWN_TEXT == "samples 1-2"
    assert vf.TEMPERATURES_TEXT == "0, 0.7, 0.7"
    assert vf.CEILING == 1 + vf.SAMPLES and vf.fit_contact_cap(vf.ROWS) == vf.ROWS * vf.CEILING * 4 == 17280
    assert vf.SOLVER_COMMIT["min_support"] == vf.MIN_SUPPORT
    assert vf.SAMPLES_WORD in vf.LEDGER_MARK and "TRAIN Fold A" in vf.LEDGER_MARK and "TRAIN Fold B" in vf.LEDGER_MARK
    text = (REPO / "scripts" / "flights" / "ver" / "ver1b_write_registration.py").read_text(encoding="utf-8")
    assert not re.search(r"\b(?:four|five|six)[- ]sample|samples 5\b|best-of-5", text)      # no sample count frozen into prose


# --- the compiled cell ---------------------------------------------------------------------------------------------------


def test_the_fragment_is_the_r5_composed_arm_plus_exactly_the_registered_diff():
    for kind in ("arm", "smoke"):
        document = _baseline(kind)
        parent = _load(f"configs/baseline/{vf.parent_names(kind)['baseline']}.json")
        composed = cm.compile_module(derive.module_block(parent), carrier_module_hooks(repo_root=REPO), repo_root=REPO)
        assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c2", 2)   # the R5 arm's program
        r5 = composed.apply_to(parent)
        moved = sorted(k for k in set(_leaves(r5)) | set(_leaves(document))
                       if _leaves(r5).get(k, object()) != _leaves(document).get(k, object()))
        allowed = ("policy", "native_episode.deliver_normaliser", "native_episode.roles.solver.samples",
                   "native_episode.roles.solver.decoding_overrides", "native_episode.roles.solver.commit",
                   "native_episode.consumption_module", "native_contact_fit", "prepared_phase_supply", "what_this_is")
        assert moved and all(any(k == p or k.startswith(p + ".") for p in allowed) for k in moved), moved
        assert document["policy"] == vf.PROGRAM and "consumption_module" not in document["native_episode"]
        assert "deliver_normaliser" not in document["native_episode"]
        # the flip (1a4e78749 arm, 79d8afaad smoke; 2026-10-10) mints the cell's own prepared_phase_supply; the held
        # registration carried none. It is an allowed moved key above and must name this cell's own supply.
        assert document["prepared_phase_supply"]["relpath"].startswith("prepared/") and len(document["prepared_phase_supply"]["sha256"]) == 64
        assert document["native_episode"]["roles"]["solver"]["samples"] == vf.SAMPLES
        assert document["native_episode"]["roles"]["solver"]["decoding_overrides"] == vf.SOLVER_OVERRIDES
        assert document["native_episode"]["roles"]["solver"]["commit"] == vf.SOLVER_COMMIT
        assert "template_variants" not in document["native_episode"]["roles"]["perception"]
        assert document["phase_tools"] == {} and document["scorers"] == parent["scorers"]
        # the Fold A pins, not another roster's
        text = json.dumps(document["knowledge_stores"])
        assert "FOLD-A" in text and "FOLD-B" not in text and "DEV2000" not in text and "fold-b" not in text


def test_the_fold_a_fragment_equals_the_committed_fold_b_sibling_except_pins_and_sample_parameters():
    """Structural twin: the same derive on Fold A and Fold B produces the same fragment up to the roster pins and the parameters."""

    sibling_ok = (REPO / "configs" / "baseline" / f"{vf.sibling_names('arm')['baseline']}.json").exists()
    assert sibling_ok
    for kind in ("arm", "smoke"):
        a = _leaves(_load(f"configs/baseline/{vf.sibling_names(kind)['baseline']}.json"))
        b = _leaves(_baseline(kind))
        moved = sorted(k for k in set(a) | set(b) if a.get(k, object()) != b.get(k, object()))
        allowed = ("knowledge_stores.intent-boundaries.phase_supply.perception.agreement_source",
                   "knowledge_stores.intent-boundaries.phase_supply.perception.query_source",
                   "knowledge_stores.train-exemplars.phase_supply.solver.query_source",
                   "native_contact_fit", "native_episode.roles.solver.commit.min_support", "native_episode.roles.solver.samples",
                   "policy", "preparation_source_receipts", "prepared_phase_supply", "what_the_train_exemplars_store_is", "what_this_is")
        assert moved and all(any(k == p or k.startswith(p + ".") for p in allowed) for k in moved), moved
        # everything that did not move is the VER-1a base: same roles, same decoding overrides, same phase material, same tools
        for key in ("native_episode.roles.solver.decoding_overrides.temperature", "native_episode.roles.solver.decoding_overrides.greedy_first",
                    "native_episode.review_loop", "native_episode.max_revisions", "native_episode.finite_completion_policy"):
            assert a[key] == b[key], key
        assert a["native_episode.roles.solver.commit.policy"] == b["native_episode.roles.solver.commit.policy"]


def test_the_loader_resolves_the_cell_to_a_ceiling_four_greedy_first_grouped_review_off_graph():
    for kind in ("arm", "smoke"):
        document = _baseline(kind)
        program = default_phase_program(document["policy"])
        parsed = load_native_episode_config(dict(document, carrier_lock_key=document.get("carrier_lock_key", "slurp")), program)
        assert program.max_contacts == parsed.max_contacts == vf.CEILING == 4
        assert not parsed.review_loop_enabled and parsed.max_revisions == 0
        solver = next(r for r in parsed.roles if r.role_kind == "solver")
        assert (solver.samples, solver.twin) == (vf.SAMPLES, None)
        assert dict(solver.decoding_overrides) == vf.SOLVER_OVERRIDES
        assert dict(solver.commit) == vf.SOLVER_COMMIT
        assert {r.role_kind: r.max_iterations for r in parsed.roles} == {"perception": 1, "solver": 1, "reviewer": 0, "planner": 0}


def test_finite_completion_and_react_exhaustion_policies_are_declared():
    for kind in ("arm", "smoke"):
        ne = _baseline(kind)["native_episode"]
        assert ne["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert ne["react_exhaustion_policy"] == "continue-without-answer"


def test_stage3_algorithm_label_resolves_in_the_registry():
    from speech_aware_evidence_acquisition.core.base import STAGE3_ALGORITHMS

    for kind in ("arm", "smoke"):
        label = _experiment(kind)["stage3_algorithm"]
        assert label["id"] == "inference-time-verification-v1" and label["id"] in STAGE3_ALGORITHMS.names()
        assert label["operators_used"] == ["scoring", "selection"]
        record = STAGE3_ALGORITHMS.resolve(label["id"])
        assert set(label["operators_used"]) <= set(record.operators)


# --- roster, budgets and the FIT cap -------------------------------------------------------------------------------------


def test_the_roster_is_train_fold_a_and_the_smoke_is_its_prefix():
    arm, smoke = _experiment("arm"), _experiment("smoke")
    roster = _load(vf.ROSTER["arm"])
    assert roster["roster_id"] == vf.READ_ROSTER == arm["split_id"] == smoke["split_id"] == "SLURP-EVO-FOLD-A-V2"
    assert arm["population"]["split_identity_hash"] == roster["split_identity_hash"]
    assert arm["population"]["count"] == vf.ROWS == len(roster["items"]) and arm["population"]["roster_receipt"] == vf.ROSTER["arm"]
    assert arm["population"]["dataset_fragment"] == smoke["population"]["dataset_fragment"] == "slurp-speech-native-evo-fold-a-1080"
    ids = [item["sample_id"] for item in roster["items"]]
    assert ids[:4] == smoke["populations"][0]["ids"] == vf.smoke_ids() and smoke["population"]["count"] == 4
    assert arm["populations"][0]["ids"] == ids
    structural = json.dumps({"cells": arm["cells"], "population_fragment": arm["population"]["dataset_fragment"], "split": arm["split_id"]})
    assert "FOLD-B" not in structural and "fold-b" not in structural      # no Fold B pin in the cell's identity or requirements


def test_budgets_are_the_contact_arithmetic_and_the_fit_cap_is_structural():
    arm, smoke = _experiment("arm"), _experiment("smoke")
    for document, kind, rows in ((arm, "arm", 1080), (smoke, "smoke", 4)):
        fam = document["family_budget"]
        audio = sum(float(i["audio_seconds"]) for i in _roster(kind))
        assert fam["generation_calls_cap"] == rows * vf.CEILING == document["execution_plan"]["planned_model_calls"]
        assert fam["native_task_contract_calls_cap"] == rows * vf.CEILING
        assert fam["fit_endpoint_calls_cap"] == vf.fit_contact_cap(rows) == rows * vf.CEILING * 4
        assert fam["repeated_speech_audio_seconds_cap"] == math.ceil(audio * vf.CEILING - 1e-9) == vf.audio_cap(kind)
        assert document["execution_plan"]["planned_speech_audio_seconds"] == fam["repeated_speech_audio_seconds_cap"]
        assert document["execution_plan"]["execution_profile"] == "bounded-discovery-probe"
        assert document["execution_plan"]["split_role"] == "discovery"
        assert document["cells"][0]["readiness"]["state"] in ("held", "ready")
    assert (arm["execution_plan"]["planned_model_calls"], arm["family_budget"]["fit_endpoint_calls_cap"]) == (4320, 17280)
    assert (smoke["execution_plan"]["planned_model_calls"], smoke["family_budget"]["fit_endpoint_calls_cap"]) == (16, 64)
    assert arm["family_budget"]["gpu_hours_fit_inclusive"] == arm["execution_plan"]["planned_gpu_hours"] == 1.7
    assert arm["generation_budget"]["cap"] == 4320 and arm["family_budget"]["repeated_speech_audio_seconds_cap"] == 12339


def test_registered_measurement_block_is_an_offline_sealed_pool_with_no_benefit_claim():
    facts = _load(f"{vf.PACKAGE}/registered-facts-v1.json")
    block = facts["stage3_measurement"][vf.ARM["run_id"]]
    assert block["measurement_design"] == "offline-sealed-pool" and block["claims_benefit"] is False
    assert block["expected_effect_pp"] == 0.0 and block["primary_metric"] == "slu_f1"
    assert (block["tuning_roster"], block["read_roster"], block["rows"]) == ("SLURP-EVO-FOLD-B-V2", "SLURP-EVO-FOLD-A-V2", 1080)
    smoke = facts["stage3_measurement"][vf.SMOKE["run_id"]]
    assert smoke["measurement_design"] == "form-proof" and smoke["claims_benefit"] is False and smoke["rows"] == 4
    assert facts["accounting"]["contacts_per_row"] == {"perception": 1, "solver": 3, "reviewer": 0, "planner": 0, "total": 4}
    recipe = _load(f"{vf.PACKAGE}/analysis-recipe-v1.json")
    assert recipe["read_run_id"] == vf.READ_RUN_ID and recipe["recipe_id"] == vf.RECIPE_ID
    assert recipe["run_ids"]["arm"] == vf.ARM["run_id"] and recipe["measurement_design"] == "offline-sealed-pool"
    assert recipe["run_ids"]["verdict_column"] == cf.ARM["run_id"]
    assert "min_support 2" in recipe["row_accounting_required"] and "temperatures 0, 0.7, 0.7" in recipe["row_accounting_required"]
    assert "exactly 3 samples" in recipe["row_accounting_required"] and "seeds fragment_seed + 0 + index" in recipe["row_accounting_required"]
    assert vf.V4G_LOCK_RECORD in recipe["stages"]["3_v4g"]


def test_the_fixed_rule_is_named_in_the_facts_the_protocol_the_recipe_and_the_preregistration():
    facts = _load(f"{vf.PACKAGE}/registered-facts-v1.json")
    protocol = _load(f"{vf.PACKAGE}/protocol-registered-v1.json")
    recipe = _load(f"{vf.PACKAGE}/analysis-recipe-v1.json")
    expect = {"n": 3, "s": 2, "theta": 0.2, "tuning_roster": "SLURP-EVO-FOLD-B-V2", "read_roster": "SLURP-EVO-FOLD-A-V2"}
    for document in (facts, protocol, recipe):
        rule = document["fixed_rule"]
        assert {k: rule[k] for k in expect} == expect
    prereg = (REPO / vf.PREREG).read_text(encoding="utf-8")
    assert "the fixed rule" in prereg and "n = 3, s = 2, theta 0.2" in prereg and "FIXED on `SLURP-EVO-FOLD-B-V2`" in prereg
    assert "THE FIXED RULE" in protocol["decision_rule_fixed_here"] and "NOT re-tuned on this roster" in protocol["decision_rule_fixed_here"]
    assert "CRITERION" in protocol["decision_rule_fixed_here"] and "NOT CONFIRMED" in protocol["decision_rule_fixed_here"]
    # the combined read is one composer invocation with the generic verdict option and only the fixed rule's grid
    command = recipe["composer_command"]
    assert "--verdict-run " + cf.ARM["run_id"] + ":" + cf.ARM["attempt_id"] + ":r1-c3" in command
    assert "--n 3 --s 2 --thetas 0.2" in command and "--run-id " + vf.ARM["run_id"] in command and "--rows 1080" in command


def test_the_effect_floor_and_algorithm_label_gates_accept_the_declaration():
    import stage3_effect_floor_check as floor

    block = _load(f"{vf.PACKAGE}/registered-facts-v1.json")["stage3_measurement"][vf.ARM["run_id"]]
    assert block["measurement_design"] in floor.DESIGNS and block["claims_benefit"] is False


# --- pre-contact preflight -----------------------------------------------------------------------------------------------


def test_pre_contact_preflight_fit_gate_and_native_config():
    from speech_aware_evidence_acquisition.core.flight.runtime import arm_uses_speech_feature_packets
    from speech_aware_evidence_acquisition.core.preparation_fit import validate_native_contact_fit_config

    for kind in ("arm", "smoke"):
        names = vf.names(kind)
        baseline = _baseline(kind)
        program = default_phase_program(baseline["policy"])
        spec = validate_native_contact_fit_config(baseline, program)
        assert spec is not None
        ids = [item["sample_id"] for item in _roster(kind)]
        assert ids and len(set(ids)) == len(ids) and len(ids) == (4 if kind == "smoke" else vf.ROWS)
        assert arm_uses_speech_feature_packets(baseline["arm"]), kind
        required_cap = len(ids) * program.max_contacts * (spec["max_speech_packets"] + 3)
        assert spec["contact_cap"] == required_cap == vf.fit_contact_cap(len(ids))
        gen_plan = _load(f"{vf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")["execution_plan"]
        assert spec["run_id"] != gen_plan["run_id"] and spec["attempt_id"] != gen_plan["attempt_id"]
        assert spec["run_id"] == names["fit_run_id"] and spec["attempt_id"] == names["fit_attempt_id"]


def test_pre_contact_preflight_plans_budgets_and_ledger_rows():
    from dataclasses import fields

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan

    ledger = _ledger_rows()
    allowed = {f.name for f in fields(ExecutionPlan)}
    split_hash = _load(vf.ROSTER["arm"])["split_identity_hash"]
    for kind in ("arm", "smoke"):
        names = vf.names(kind)
        items = _roster(kind)
        rows = len(items)
        max_contacts = default_phase_program(_baseline(kind)["policy"]).max_contacts
        audio = sum(float(i["audio_seconds"]) for i in items)
        declared = _experiment(kind)["execution_plan"]
        assert declared["planned_model_calls"] >= rows * max_contacts
        assert declared["planned_speech_audio_seconds"] >= math.ceil(audio * max_contacts - 1e-9)
        for plan_kind in ("generation", "fit"):
            registered = _load(f"{vf.PACKAGE}/{names['prefix']}{plan_kind}-plan-registered-v1.json")["execution_plan"]
            plan = ExecutionPlan(**{k: v for k, v in registered.items() if k in allowed}).validate(source_root=REPO)
            if plan_kind == "generation":
                assert plan.planned_model_calls == declared["planned_model_calls"]
                assert plan.run_id == names["run_id"] and plan.attempt_id == names["attempt_id"]
            else:
                assert plan.planned_model_calls == _baseline(kind)["native_contact_fit"]["contact_cap"]
                assert plan.run_id == names["fit_run_id"] and plan.attempt_id == names["fit_attempt_id"]
            matched = [r for r in ledger if r.get("run/experiment id") == plan.run_id]
            assert len(matched) == 1, (plan.run_id, len(matched))
            row = matched[0]
            assert row["consumed"].strip().lower() == "yes" and "CONSUMED (" in row["notes"]  # flown and sealed; closed by scripts/flights/batch/ledger_mark_consumed.py (SEALED prefix)
            assert row["execution profile"] == plan.execution_profile and row["split role"] == plan.split_role
            assert row["split identity hash"] == plan.split_identity_hash
            assert (kind == "smoke") or row["split identity hash"] == split_hash
            assert int(row["calls"]) == plan.planned_model_calls
            assert int(row["speech audio seconds"]) == plan.planned_speech_audio_seconds
            assert float(row["gpu hours"]) == float(plan.planned_gpu_hours)


def test_pre_contact_preflight_identities_agree_and_are_fresh():
    for kind in ("arm", "smoke"):
        names = vf.names(kind)
        experiment, baseline = _experiment(kind), _baseline(kind)
        protocol = _load(f"{vf.PACKAGE}/protocol-registered-v1.json")["cells"][kind]
        gen = _load(f"{vf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")["execution_plan"]
        fit = _load(f"{vf.PACKAGE}/{names['prefix']}fit-plan-registered-v1.json")["execution_plan"]
        cell = experiment["cells"][0]
        assert cell["attempt_id"] == names["attempt_id"] == gen["attempt_id"] == protocol["attempt_id"]
        fit_block = baseline["native_contact_fit"]
        assert fit_block["attempt_id"] == names["fit_attempt_id"] == fit["attempt_id"] == protocol["fit_attempt_id"]
        assert cell["run_id"] == names["run_id"] == gen["run_id"] == protocol["run_id"]
        assert fit_block["run_id"] == names["fit_run_id"] == fit["run_id"] == protocol["fit_run_id"]
        assert names["run_id"] != names["fit_run_id"] and names["attempt_id"] != names["fit_attempt_id"]
        fam = experiment["family_budget"]
        assert fam["fit_endpoint_calls_cap"] == fit_block["contact_cap"] == fit["planned_model_calls"]
        assert fam["generation_calls_cap"] == gen["planned_model_calls"]
        assert "-rec1" not in json.dumps(experiment) and "-rec1" not in json.dumps(baseline)
        for text in (json.dumps(experiment), json.dumps(baseline["native_contact_fit"]), json.dumps(cell)):
            assert not re.search(r"comp1b-fold-a|COMP1B-FOLD-A|nx-r6|NX-R6", text)    # no inherited identity survived the derive


def test_registered_plans_pin_the_hashes_the_fragments_compose_to():
    from speech_aware_evidence_acquisition.core.config import compose, protocol_hash

    for kind in ("arm", "smoke"):
        names = vf.names(kind)
        document = _experiment(kind)
        cell = document["cells"][0]
        composed = compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], names["experiment"])
        split = document["population"]["split_identity_hash"]
        plan = _load(f"{vf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")
        if _all_draft():
            assert plan["composed_config_hash"] == composed.config_hash
            assert plan["execution_plan"]["protocol_hash"] == protocol_hash(composed.config_hash, composed.values["arm"], split)
        assert plan["protocol_document"]["sha256"] == hashlib.sha256(
            (REPO / vf.PACKAGE / "protocol-registered-v1.json").read_bytes()).hexdigest()


# --- scripts, held state, ledger -----------------------------------------------------------------------------------------


def test_chain_flip_repin_mint_and_dry_run_scripts_agree_with_the_family():
    scripts = REPO / "scripts" / "flights" / "ver"
    chain = (scripts / "ver1b_batch_chain.sh").read_text(encoding="utf-8")
    flip = (scripts / "ver1b_flip.sh").read_text(encoding="utf-8")
    repin = (scripts / "ver1b_repin_cell.sh").read_text(encoding="utf-8")
    for text in (chain, flip, repin):
        assert f"SLUG={vf.SLUG}" in text and f"SHORT={vf.SHORT}" in text
        assert "\r" not in text and "ver1a" not in text.lower().replace("ver-1a", "")
    assert f"ROWS={vf.ROWS} " in chain and f"CEILING={vf.CEILING} " in chain
    assert '"expected_rows": rows, "contacts_per_row": ceiling, "ceiling_per_row": ceiling, "notool": True' in chain
    assert '"gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1"' in chain
    assert '"smoke_attempt_id": f"attempt-slurp-native-stage3-{slug}-smoke-4-generation{rec}-v1"' in chain
    assert "SMOKE_REC=       #" in chain          # no recovery: the smoke is a first attempt
    assert f"RD=docs/readiness/{vf.DATE}-slurp-$SLUG-v1" in flip and f"RD=docs/readiness/{vf.DATE}-slurp-$SLUG-v1" in repin
    assert "ver1b_repin_cell.sh" in flip and "unset ALLOW_OUTPUT_CHANGE" in repin and "--allow-output-change must never" in flip
    assert "export EXP=$CELL ARM=0" in repin
    assert f"SAEA-SLURP-STAGE3-{vf.SLUG.upper()}-POOL-READ-V1" in flip
    mint = (scripts / "ver1b_mint_receipt.py").read_text(encoding="utf-8")
    assert "ver1b_family as nf" in mint and "eligible_run_ids" in mint
    for name in ("ver1b_dry_run.py", "ver1b_mint_receipt.py", "ver1b_derive_cells.py", "ver1b_write_registration.py", "ver1b_family.py"):
        ast.parse((scripts / name).read_text(encoding="utf-8"))
    dry = (scripts / "ver1b_dry_run.py").read_text(encoding="utf-8")
    assert "ver1b_family" in dry and "ver1a" not in dry


def test_the_cell_is_held_and_the_package_is_complete():
    for kind in ("arm", "smoke"):
        experiment = _experiment(kind)
        cell = experiment["cells"][0]
        requirements = cell["readiness"]["requirements"]
        decision = [r for r in requirements if r["kind"] == "decision"]
        own_supply = [r for r in requirements if re.search(r"/phase-supply-v\d+\.json$", r["relpath"])]
        agreement = [r for r in requirements if r["relpath"].endswith("FOLD-A-V1/agreement.jsonl")]
        assert len(decision) == len(own_supply) == len(agreement) == 1 and len(requirements) == 3
        assert decision[0]["relpath"] == vf.DECISION_RELPATH and decision[0]["expected_decision_id"] == vf.DECISION_ID
        assert own_supply[0]["relpath"].startswith(f"prepared/{vf.names(kind)['run_id']}/phase-supply-v")   # E16: its own
        if _all_draft():
            assert cell["readiness"]["state"] == "held" and "HELD" in cell["readiness"]["reason"]
            assert decision[0]["sha256"] == "0" * 64 and own_supply[0]["sha256"] == "0" * 64
            assert agreement[0]["sha256"] != "0" * 64
            assert "prepared_phase_supply" not in _baseline(kind)
        assert ("campaign" in cell["allowed_execution_stages"]) == (kind == "arm")
        assert "paper-scale" not in json.dumps(experiment["execution_plan"])
    package = REPO / vf.PACKAGE
    for name in ("README.md", "registered-facts-v1.json", "protocol-registered-v1.json", "analysis-recipe-v1.json",
                 "root-admission-draft-v1.json", "generation-plan-registered-v1.json", "fit-plan-registered-v1.json",
                 "smoke-generation-plan-registered-v1.json", "smoke-fit-plan-registered-v1.json"):
        assert (package / name).is_file(), name
    assert (REPO / vf.PREREG).is_file() and (REPO / vf.CAMPAIGN).is_file()
    assert _load(vf.CAMPAIGN)["cells"] == [{"cell": vf.ARM["experiment"], "experiment": vf.ARM["experiment"]}]
    draft = _load(f"{vf.PACKAGE}/root-admission-draft-v1.json")
    assert draft["status"] == "DRAFT-NOT-MINTED" and draft["decision_id"] == vf.DECISION_ID
    assert draft["eligible_run_ids"] == [vf.ARM["run_id"], vf.ARM["fit_run_id"], vf.SMOKE["run_id"], vf.SMOKE["fit_run_id"]]
    assert draft["population"]["test_contact_authorized"] is False and draft["population"]["fold_b_contact_authorized"] is False
    assert draft["budget"]["paid_api_calls"] == 0 and draft["budget"]["generation_calls_cap"] == 4320
    assert draft["recorded_at_utc"] is None


def test_the_ledger_rows_are_present_unconsumed_and_draft_or_countersigned():
    import flight_registration_check as frc
    from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables

    text = (REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    assert text.count(vf.LEDGER_MARK) == 1
    rows = _parse_ledger_tables(text)
    ids = [vf.ARM["run_id"], vf.ARM["fit_run_id"], vf.SMOKE["run_id"], vf.SMOKE["fit_run_id"], vf.READ_RUN_ID]
    for run_id in ids:
        matched = [r for r in rows if r.get("run/experiment id") == run_id]
        assert len(matched) == 1, run_id
        row = matched[0]
        assert "DRAFT" in row.get("notes", "") or frc.is_countersigned(row), run_id
        if run_id == vf.READ_RUN_ID:
            assert row["execution profile"] == "model-free-check"
    if _all_draft():
        for run_id in ids:
            row = next(r for r in rows if r.get("run/experiment id") == run_id)
            assert not frc.is_countersigned(row) and row["consumed"].strip().lower() == "no", run_id
        arm_row = next(r for r in rows if r.get("run/experiment id") == vf.ARM["run_id"])
        assert "claims_benefit false" in arm_row["notes"] and "offline-sealed-pool" in arm_row["notes"]
        assert "n = 3, s = 2, theta 0.2" in arm_row["notes"] and "tuning roster SLURP-EVO-FOLD-B-V2" in arm_row["notes"]
        assert "samples 3" in arm_row["model/tool"] and "min_support 2" in arm_row["model/tool"]
    # the section holds nothing but this cell's five rows, in its own heading block
    start = text.index(vf.LEDGER_MARK)
    following = text.find("\n## ", start + len(vf.LEDGER_MARK))
    section = text[start:] if following == -1 else text[start:following]
    assert len(re.findall(r"\| SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A", section)) == 5
