"""VER-1c (owner decision 257, decision 258 option A): the registered Fold A c3 column cell is exactly what its package says (model-free, HELD).

Reads the committed fragments and package files only (no data root, no model, no server). Proves: the fragment is the COMP-1b Fold A
composition declared as a consumption-module block on lock v2.2 (review loop off) with ONE Solver template column -- the R1 ``r1-c3``
template, byte for byte the file the NX R1 iteration-1 cell flew --, the ``aa`` twin and the delivering ``lock`` arm, compiled by the
module compiler (the loader verifies the declared block against its own compilation); the E1 arithmetic gives the registered program
``phase-native-module-v1-c4`` (ceiling base 2 + (K - 1), K = 3); the plan budgets are the contact arithmetic (1,080 x 4 = 4,320), the FIT
cap is structural; the identities agree; the roster is TRAIN Fold A; the measurement block is a same-flight node column with a
single-candidate ``template_variants`` summary, ``claims_benefit`` false and expected effect 0.0; the finite-completion and
ReAct-exhaustion policies are declared; and the cell is HELD with DRAFT ledger rows.
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

import ver1b_family as vf  # noqa: E402
import ver1c_derive_cells as derive  # noqa: E402
import ver1c_family as cf  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import MODULE_PROGRAM_FAMILY_IDS, default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402


def _load(relpath: str) -> dict:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _baseline(kind: str) -> dict:
    return _load(f"configs/baseline/{cf.names(kind)['baseline']}.json")


def _experiment(kind: str) -> dict:
    return _load(f"configs/experiment/{cf.names(kind)['experiment']}.json")


def _ledger_rows() -> list:
    from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables

    return _parse_ledger_tables((REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8"))


def _all_draft() -> bool:
    rows = {r.get("run/experiment id"): r for r in _ledger_rows()}
    ids = [cf.ARM["run_id"], cf.ARM["fit_run_id"], cf.SMOKE["run_id"], cf.SMOKE["fit_run_id"]]
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
    assert (cf.ARM["experiment"], cf.ARM["run_id"], cf.DECISION_ID, cf.DECISION_RELPATH, cf.READ_RUN_ID) == (
        "slurp-native-stage3-ver1c-c3-column-fold-a-v1", "SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-V1",
        "slurp-ver1c-c3-column-fold-a-admission-v1", "coordination/slurp-ver1c-c3-column-fold-a-v1/root-admission-v1.json",
        "SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-COLUMN-READ-V1")
    assert cf.ARM["fit_run_id"] == "SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-FIT-V1"
    assert cf.SMOKE["run_id"] == "SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-SMOKE-4-V1"
    assert cf.SMOKE["fit_run_id"] == "SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-SMOKE-4-FIT-V1"
    assert cf.SMOKE["experiment"] == "slurp-native-stage3-ver1c-c3-column-fold-a-smoke-4-v1"
    assert cf.ARM["attempt_id"] == "attempt-slurp-native-stage3-ver1c-c3-column-fold-a-generation-v1"
    assert cf.SMOKE["attempt_id"] == "attempt-slurp-native-stage3-ver1c-c3-column-fold-a-smoke-4-generation-v1"
    assert cf.PACKAGE == "docs/readiness/2026-10-10-slurp-ver1c-c3-column-fold-a-v1"
    assert cf.ARMS == ("r1-c3",) and cf.ARM_ORDER == ("r1-c3", "aa", "lock") and cf.K == 3
    assert cf.CEILING == cf.BASE_CONTACTS + (cf.K - 1) == 4 and cf.PROGRAM == "phase-native-module-v1-c4"
    assert cf.PROGRAM in MODULE_PROGRAM_FAMILY_IDS
    assert (cf.TUNING_ROSTER, cf.READ_ROSTER) == ("SLURP-EVO-FOLD-B-V2", "SLURP-EVO-FOLD-A-V2") == (vf.TUNING_ROSTER, vf.READ_ROSTER)
    assert cf.EXPECTED_EFFECT_PP == 0.0 and cf.ROWS == vf.ROWS == 1080
    assert cf.ARM["run_id"] != vf.ARM["run_id"] and cf.PACKAGE != vf.PACKAGE and cf.LEDGER_MARK != vf.LEDGER_MARK


def test_the_candidate_is_the_r1_c3_template_byte_for_byte():
    pins = cf.candidate_pins()                                # raises when the bytes differ from the R1 candidates README
    assert pins["r1-c3"] == {"relpath": "configs/probes/nx/solver/r1/r1-c3.txt",
                             "sha256": "89b81e97c0c8d5377eff2892fac548ac83fd6a24f61ceb25396a57196bb262dc"}
    readme = (REPO / cf.R1_CANDIDATES_README).read_text(encoding="utf-8")
    assert pins["r1-c3"]["sha256"] in readme and "r1-c3 -- explicit empty-entity decision" in readme
    r1 = _load("configs/baseline/slurp-native-stage3-nx-r1-solver-fold-b-baseline-v1.json")
    flown = next(c for c in r1["native_episode"]["consumption_module"]["columns"] if c["column_id"] == "r1-c3")
    assert flown["template"] == pins["r1-c3"]                  # the exact pin the R1 iteration-1 cell carries
    assert hashlib.sha256((REPO / cf.LOCKED_TEMPLATE).read_bytes()).hexdigest() == cf.LOCKED_TEMPLATE_SHA


# --- the compiled cell ---------------------------------------------------------------------------------------------------


def test_the_declared_module_block_compiles_to_the_fragment_and_names_one_candidate_the_twin_and_the_lock():
    for kind in ("arm", "smoke"):
        document = _baseline(kind)
        block = document["native_episode"]["consumption_module"]
        assert (block["lock"], block["review_loop"], block["profile"]) == ("v2.2", "off", "slurp")
        assert [(c["column_id"], c["kind"], c["node"]) for c in block["columns"]] == [("r1-c3", "template", "solver")]
        assert block["columns"][0]["template_tokens"] == cf.fit_measure()["template_tokens"]["r1-c3"] == 434
        assert block["template_frame"] == cf.fit_measure()["template_frame"] and block["template_frame"]["twin"] is True
        on = sorted(c["component_id"] for c in block["components"] if c["state"] == "on")
        assert on == sorted([cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY])
        cm.verify_declared_module(block, document, repo_root=REPO)          # the loader's own check
        composed = cm.compile_module(block, carrier_module_hooks(repo_root=REPO), repo_root=REPO)
        assert (composed.program_id, composed.program_ceiling) == (cf.PROGRAM, cf.CEILING)
        assert document["policy"] == cf.PROGRAM
        variants = document["native_episode"]["roles"]["solver"]["template_variants"]
        assert [arm["arm_id"] for arm in variants["arms"]] == list(cf.ARM_ORDER)
        assert variants["arms"][0]["instruction_template"] == cf.candidate_pins()["r1-c3"]
        assert variants["arms"][1] == {"arm_id": "aa", "replicate_of": "lock"} and variants["arms"][2]["deliver"] is True
        assert document["native_episode"]["deliver_normaliser"] == {"normaliser": "saea-deliver-normalise-v4g"}
        assert document["phase_tools"] == {} and document["native_episode"]["review_loop"] == "off"
        assert document["native_episode"]["max_revisions"] == 0
        text = json.dumps(document["knowledge_stores"])
        assert "FOLD-A" in text and "FOLD-B" not in text and "DEV2000" not in text and "fold-b" not in text


def test_the_loader_resolves_the_cell_to_a_ceiling_four_three_arm_review_off_graph():
    for kind in ("arm", "smoke"):
        document = _baseline(kind)
        program = default_phase_program(document["policy"])
        parsed = load_native_episode_config(dict(document, carrier_lock_key=document.get("carrier_lock_key", "slurp")), program)
        assert program.max_contacts == parsed.max_contacts == cf.CEILING == 4
        assert not parsed.review_loop_enabled and parsed.max_revisions == 0
        assert {r.role_kind: r.max_iterations for r in parsed.roles} == {"perception": 1, "solver": 1, "reviewer": 0, "planner": 0}


def test_the_fold_a_column_equals_the_committed_r1_fold_b_column_except_pins_columns_and_lock():
    """Structural twin: the committed NX R1 iteration-1 fragment (Fold B, five candidates, lock v2.1) vs this cell."""

    a = _leaves(_load("configs/baseline/slurp-native-stage3-nx-r1-solver-fold-b-baseline-v1.json"))
    b = _leaves(_baseline("arm"))
    moved = sorted(k for k in set(a) | set(b) if a.get(k, object()) != b.get(k, object()))
    allowed = ("knowledge_stores.intent-boundaries.phase_supply.perception.agreement_source",
               "knowledge_stores.intent-boundaries.phase_supply.perception.query_source",
               "knowledge_stores.train-exemplars.phase_supply.solver.query_source",
               "native_contact_fit", "native_episode.consumption_module.columns", "native_episode.consumption_module.lock",
               "native_episode.consumption_module.components",            # only the agreement-table pin inside the armed component moves
               "native_episode.roles.solver.template_variants.arms", "native_episode.deliver_normaliser",
               "policy", "preparation_source_receipts", "prepared_phase_supply", "what_the_train_exemplars_store_is", "what_this_is")
    assert moved and all(any(k == p or k.startswith(p + ".") for p in allowed) for k in moved), moved
    r1_block = _load("configs/baseline/slurp-native-stage3-nx-r1-solver-fold-b-baseline-v1.json")["native_episode"]["consumption_module"]
    here = _baseline("arm")["native_episode"]["consumption_module"]
    assert [(c["component_id"], c["state"]) for c in r1_block["components"]] == [(c["component_id"], c["state"]) for c in here["components"]]
    # untouched: the frame, the twin flag, the supply bound, the role graph
    for key in ("native_episode.consumption_module.template_frame.max_supplied_items",
                "native_episode.consumption_module.template_frame.fit_estimate.tokens_per_supplied_item",
                "native_episode.roles.solver.template_variants.max_supplied_items", "native_episode.review_loop"):
        assert a[key] == b[key], key


def test_finite_completion_and_react_exhaustion_policies_are_declared():
    for kind in ("arm", "smoke"):
        ne = _baseline(kind)["native_episode"]
        assert ne["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert ne["react_exhaustion_policy"] == "continue-without-answer"


def test_stage3_algorithm_label_is_none_as_the_r1_cells_carried_it():
    from speech_aware_evidence_acquisition.core.base import STAGE3_ALGORITHMS

    for kind in ("arm", "smoke"):
        label = _experiment(kind)["stage3_algorithm"]
        assert label["id"] == "none" and label["operators_used"] == [] and label["id"] in STAGE3_ALGORITHMS.names()
    r1 = _load("configs/experiment/slurp-native-stage3-nx-r1-solver-fold-b-v1.json")["stage3_algorithm"]
    assert r1["id"] == "none"


# --- roster, budgets and the FIT cap -------------------------------------------------------------------------------------


def test_the_roster_is_train_fold_a_and_the_smoke_is_its_prefix():
    arm, smoke = _experiment("arm"), _experiment("smoke")
    roster = _load(cf.ROSTER["arm"])
    assert roster["roster_id"] == cf.READ_ROSTER == arm["split_id"] == smoke["split_id"]
    assert arm["population"]["split_identity_hash"] == roster["split_identity_hash"]
    assert arm["population"]["count"] == cf.ROWS == len(roster["items"]) and arm["population"]["roster_receipt"] == cf.ROSTER["arm"]
    ids = [item["sample_id"] for item in roster["items"]]
    assert ids[:4] == smoke["populations"][0]["ids"] == cf.smoke_ids() == vf.smoke_ids() and smoke["population"]["count"] == 4
    assert arm["populations"][0]["ids"] == ids                 # the SAME rows as the VER-1b pool: paired row for row
    assert ids == [i["sample_id"] for i in vf.roster_items("arm")]


def test_budgets_are_the_contact_arithmetic_and_the_fit_cap_is_structural():
    arm, smoke = _experiment("arm"), _experiment("smoke")
    for document, kind, rows in ((arm, "arm", 1080), (smoke, "smoke", 4)):
        fam = document["family_budget"]
        audio = sum(float(i["audio_seconds"]) for i in cf.roster_items(kind))
        assert fam["generation_calls_cap"] == rows * cf.CEILING == document["execution_plan"]["planned_model_calls"]
        assert fam["native_task_contract_calls_cap"] == rows * cf.CEILING
        assert fam["fit_endpoint_calls_cap"] == cf.fit_contact_cap(rows) == rows * cf.CEILING * 4
        assert fam["repeated_speech_audio_seconds_cap"] == math.ceil(audio * cf.CEILING - 1e-9) == cf.audio_cap(kind)
        assert document["execution_plan"]["planned_speech_audio_seconds"] == fam["repeated_speech_audio_seconds_cap"]
        assert document["execution_plan"]["execution_profile"] == "bounded-discovery-probe"
        assert document["execution_plan"]["split_role"] == "discovery"
        assert document["cells"][0]["readiness"]["state"] in ("held", "ready")
    assert (arm["execution_plan"]["planned_model_calls"], arm["family_budget"]["fit_endpoint_calls_cap"]) == (4320, 17280)
    assert (smoke["execution_plan"]["planned_model_calls"], smoke["family_budget"]["fit_endpoint_calls_cap"]) == (16, 64)
    assert arm["family_budget"]["gpu_hours_fit_inclusive"] == arm["execution_plan"]["planned_gpu_hours"] == 1.8
    assert arm["generation_budget"]["cap"] == 4320 and arm["family_budget"]["repeated_speech_audio_seconds_cap"] == vf.audio_cap("arm")


def test_registered_measurement_block_is_a_same_flight_node_column_with_one_candidate_and_no_benefit_claim():
    import stage3_effect_floor_check as floor

    facts = _load(f"{cf.PACKAGE}/registered-facts-v1.json")
    block = facts["stage3_measurement"][cf.ARM["run_id"]]
    assert block["measurement_design"] == "same-flight-node-column" and block["measurement_design"] in floor.DESIGNS
    assert block["claims_benefit"] is False and block["expected_effect_pp"] == 0.0
    assert block["template_variants"] == {"node": "solver", "candidate_arms": 1, "twin": True}
    assert block["aa_arm_id"] == "aa" and block["primary_metric_key"] == "slu"
    assert (block["tuning_roster"], block["read_roster"], block["rows"]) == ("SLURP-EVO-FOLD-B-V2", "SLURP-EVO-FOLD-A-V2", 1080)
    assert "TRAIN Fold A (the R1 tuning roster" in block["note"]                 # the exposure disclosure (R6-P1 precedent)
    assert block["provisional_floor_pp"]["slu_f1"] == 1.49 and block["variant_cost"]["extra_contacts_per_row"] == 2
    smoke = facts["stage3_measurement"][cf.SMOKE["run_id"]]
    assert smoke["measurement_design"] == "form-proof" and smoke["claims_benefit"] is False and smoke["rows"] == 4
    assert facts["accounting"]["contacts_per_row"] == {"perception": 1, "solver": 3, "reviewer": 0, "planner": 0, "total": 4}
    assert "base 2 + (K - 1) with K = 3" in facts["accounting"]["derivation"]
    recipe = _load(f"{cf.PACKAGE}/analysis-recipe-v1.json")
    assert recipe["read_run_id"] == cf.READ_RUN_ID and recipe["recipe_id"] == cf.RECIPE_ID
    assert recipe["fixed_rule_consumer"]["flag"] == "--verdict-run"
    assert recipe["fixed_rule_consumer"]["value"] == f"{cf.ARM['run_id']}:{cf.ARM['attempt_id']}:r1-c3"
    assert recipe["official_columns"]["scoring_jobs"] == 3 and set(recipe["arms"]["columns"]) == {"r1-c3", "aa", "lock"}
    assert recipe["arms"]["columns"]["r1-c3"]["sha256"] == cf.candidate_pins()["r1-c3"]["sha256"]
    assert all(p["gating"] is not True for p in recipe["official_columns"]["passes"].values())      # nothing is nominated


# --- pre-contact preflight -----------------------------------------------------------------------------------------------


def test_pre_contact_preflight_fit_gate_and_native_config():
    from speech_aware_evidence_acquisition.core.flight.runtime import arm_uses_speech_feature_packets
    from speech_aware_evidence_acquisition.core.preparation_fit import validate_native_contact_fit_config

    for kind in ("arm", "smoke"):
        names = cf.names(kind)
        baseline = _baseline(kind)
        program = default_phase_program(baseline["policy"])
        spec = validate_native_contact_fit_config(baseline, program)
        assert spec is not None
        ids = [item["sample_id"] for item in cf.roster_items(kind)]
        assert ids and len(set(ids)) == len(ids) and len(ids) == (4 if kind == "smoke" else cf.ROWS)
        assert arm_uses_speech_feature_packets(baseline["arm"]), kind
        required_cap = len(ids) * program.max_contacts * (spec["max_speech_packets"] + 3)
        assert spec["contact_cap"] == required_cap == cf.fit_contact_cap(len(ids))
        gen_plan = _load(f"{cf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")["execution_plan"]
        assert spec["run_id"] != gen_plan["run_id"] and spec["attempt_id"] != gen_plan["attempt_id"]
        assert spec["run_id"] == names["fit_run_id"] and spec["attempt_id"] == names["fit_attempt_id"]


def test_pre_contact_preflight_plans_budgets_and_ledger_rows():
    from dataclasses import fields

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan

    ledger = _ledger_rows()
    allowed = {f.name for f in fields(ExecutionPlan)}
    for kind in ("arm", "smoke"):
        names = cf.names(kind)
        items = cf.roster_items(kind)
        rows = len(items)
        max_contacts = default_phase_program(_baseline(kind)["policy"]).max_contacts
        audio = sum(float(i["audio_seconds"]) for i in items)
        declared = _experiment(kind)["execution_plan"]
        assert declared["planned_model_calls"] >= rows * max_contacts
        assert declared["planned_speech_audio_seconds"] >= math.ceil(audio * max_contacts - 1e-9)
        for plan_kind in ("generation", "fit"):
            registered = _load(f"{cf.PACKAGE}/{names['prefix']}{plan_kind}-plan-registered-v1.json")["execution_plan"]
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
            assert int(row["calls"]) == plan.planned_model_calls
            assert int(row["speech audio seconds"]) == plan.planned_speech_audio_seconds
            assert float(row["gpu hours"]) == float(plan.planned_gpu_hours)


def test_pre_contact_preflight_identities_agree_and_are_fresh():
    for kind in ("arm", "smoke"):
        names = cf.names(kind)
        experiment, baseline = _experiment(kind), _baseline(kind)
        protocol = _load(f"{cf.PACKAGE}/protocol-registered-v1.json")["cells"][kind]
        gen = _load(f"{cf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")["execution_plan"]
        fit = _load(f"{cf.PACKAGE}/{names['prefix']}fit-plan-registered-v1.json")["execution_plan"]
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
        assert "-rec" not in json.dumps(experiment["cells"]) and "-rec" not in json.dumps(baseline["native_contact_fit"])
        for text in (json.dumps(experiment), json.dumps(baseline["native_contact_fit"])):
            assert not re.search(r"comp1b-fold-a|COMP1B-FOLD-A|nx-r1|NX-R1", text)


def test_registered_plans_pin_the_hashes_the_fragments_compose_to():
    from speech_aware_evidence_acquisition.core.config import compose, protocol_hash

    for kind in ("arm", "smoke"):
        names = cf.names(kind)
        document = _experiment(kind)
        cell = document["cells"][0]
        composed = compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], names["experiment"])
        split = document["population"]["split_identity_hash"]
        plan = _load(f"{cf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")
        if _all_draft():
            assert plan["composed_config_hash"] == composed.config_hash
            assert plan["execution_plan"]["protocol_hash"] == protocol_hash(composed.config_hash, composed.values["arm"], split)
        assert plan["protocol_document"]["sha256"] == hashlib.sha256(
            (REPO / cf.PACKAGE / "protocol-registered-v1.json").read_bytes()).hexdigest()


# --- scripts, held state, ledger -----------------------------------------------------------------------------------------


def test_chain_flip_repin_mint_and_dry_run_scripts_agree_with_the_family():
    scripts = REPO / "scripts" / "flights" / "ver"
    chain = (scripts / "ver1c_batch_chain.sh").read_text(encoding="utf-8")
    flip = (scripts / "ver1c_flip.sh").read_text(encoding="utf-8")
    repin = (scripts / "ver1c_repin_cell.sh").read_text(encoding="utf-8")
    for text in (chain, flip, repin):
        assert f"SLUG={cf.SLUG}" in text and f"SHORT={cf.SHORT}" in text
        assert "\r" not in text and "ver1a" not in text.lower().replace("ver-1a", "") and "ver1b_" not in text.lower()
    assert f"ROWS={cf.ROWS} " in chain and f"CEILING={cf.CEILING} " in chain
    assert '"expected_rows": rows, "contacts_per_row": ceiling, "ceiling_per_row": ceiling, "notool": True' in chain
    assert '"gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1"' in chain
    assert "SMOKE_REC=       #" in chain          # no recovery: the smoke is a first attempt
    assert f"RD=docs/readiness/{cf.DATE}-slurp-$SLUG-v1" in flip and f"RD=docs/readiness/{cf.DATE}-slurp-$SLUG-v1" in repin
    assert "ver1c_repin_cell.sh" in flip and "unset ALLOW_OUTPUT_CHANGE" in repin and "--allow-output-change must never" in flip
    assert f"SAEA-SLURP-STAGE3-{cf.SLUG.upper()}-COLUMN-READ-V1" in flip
    mint = (scripts / "ver1c_mint_receipt.py").read_text(encoding="utf-8")
    assert "ver1c_family as nf" in mint and "eligible_run_ids" in mint
    for name in ("ver1c_dry_run.py", "ver1c_mint_receipt.py", "ver1c_derive_cells.py", "ver1c_write_registration.py", "ver1c_family.py"):
        ast.parse((scripts / name).read_text(encoding="utf-8"))
    dry = (scripts / "ver1c_dry_run.py").read_text(encoding="utf-8")
    assert "ver1c_family" in dry and "nx_r1" not in dry and "NX-R1" not in dry


def test_the_cell_is_held_and_the_package_is_complete():
    for kind in ("arm", "smoke"):
        experiment = _experiment(kind)
        cell = experiment["cells"][0]
        requirements = cell["readiness"]["requirements"]
        decision = [r for r in requirements if r["kind"] == "decision"]
        own_supply = [r for r in requirements if re.search(r"/phase-supply-v\d+\.json$", r["relpath"])]
        agreement = [r for r in requirements if r["relpath"].endswith("FOLD-A-V1/agreement.jsonl")]
        assert len(decision) == len(own_supply) == len(agreement) == 1 and len(requirements) == 3
        assert decision[0]["relpath"] == cf.DECISION_RELPATH and decision[0]["expected_decision_id"] == cf.DECISION_ID
        assert own_supply[0]["relpath"].startswith(f"prepared/{cf.names(kind)['run_id']}/phase-supply-v")   # E16: its own
        if _all_draft():
            assert cell["readiness"]["state"] == "held" and "HELD" in cell["readiness"]["reason"]
            assert decision[0]["sha256"] == "0" * 64 and own_supply[0]["sha256"] == "0" * 64
            assert agreement[0]["sha256"] != "0" * 64
            assert "prepared_phase_supply" not in _baseline(kind)
        assert ("campaign" in cell["allowed_execution_stages"]) == (kind == "arm")
        assert "paper-scale" not in json.dumps(experiment["execution_plan"])
    package = REPO / cf.PACKAGE
    for name in ("README.md", "registered-facts-v1.json", "protocol-registered-v1.json", "analysis-recipe-v1.json",
                 "root-admission-draft-v1.json", "generation-plan-registered-v1.json", "fit-plan-registered-v1.json",
                 "smoke-generation-plan-registered-v1.json", "smoke-fit-plan-registered-v1.json"):
        assert (package / name).is_file(), name
    assert (REPO / cf.PREREG).is_file() and (REPO / cf.CAMPAIGN).is_file()
    assert _load(cf.CAMPAIGN)["cells"] == [{"cell": cf.ARM["experiment"], "experiment": cf.ARM["experiment"]}]
    draft = _load(f"{cf.PACKAGE}/root-admission-draft-v1.json")
    assert draft["status"] == "DRAFT-NOT-MINTED" and draft["decision_id"] == cf.DECISION_ID
    assert draft["eligible_run_ids"] == [cf.ARM["run_id"], cf.ARM["fit_run_id"], cf.SMOKE["run_id"], cf.SMOKE["fit_run_id"]]
    assert draft["population"]["test_contact_authorized"] is False and draft["population"]["fold_b_contact_authorized"] is False
    assert draft["budget"]["paid_api_calls"] == 0 and draft["budget"]["generation_calls_cap"] == 4320
    assert draft["recorded_at_utc"] is None


def test_the_ledger_rows_are_present_unconsumed_and_draft_or_countersigned():
    import flight_registration_check as frc
    from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables

    text = (REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    assert text.count(cf.LEDGER_MARK) == 1
    rows = _parse_ledger_tables(text)
    ids = [cf.ARM["run_id"], cf.ARM["fit_run_id"], cf.SMOKE["run_id"], cf.SMOKE["fit_run_id"], cf.READ_RUN_ID]
    for run_id in ids:
        matched = [r for r in rows if r.get("run/experiment id") == run_id]
        assert len(matched) == 1, run_id
        row = matched[0]
        assert "DRAFT" in row.get("notes", "") or frc.is_countersigned(row), run_id
        if run_id == cf.READ_RUN_ID:
            assert row["execution profile"] == "model-free-check"
    if _all_draft():
        for run_id in ids:
            row = next(r for r in rows if r.get("run/experiment id") == run_id)
            assert not frc.is_countersigned(row) and row["consumed"].strip().lower() == "no", run_id
        arm_row = next(r for r in rows if r.get("run/experiment id") == cf.ARM["run_id"])
        assert "claims_benefit false" in arm_row["notes"] and "same-flight-node-column" in arm_row["notes"]
        assert "expected_effect_pp 0.0" in arm_row["notes"] and "tuning roster SLURP-EVO-FOLD-B-V2" in arm_row["notes"]
    start = text.index(cf.LEDGER_MARK)
    following = text.find("\n## ", start + len(cf.LEDGER_MARK))
    section = text[start:] if following == -1 else text[start:following]
    assert len(re.findall(r"\| SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A", section)) == 5
    # the two heading blocks are adjacent sections of the ledger, in this order, and do not interleave. They
    # were the last two sections when written; later sections (e.g. the earnings22 all-off block, 291100d56,
    # 2026-10-11) are appended after them, so adjacency, not "last two", is the invariant.
    headings = [m.group(0) for m in re.finditer(r"^## .*$", text, flags=re.M)]
    vf_at = next(i for i, h in enumerate(headings) if h.startswith(vf.LEDGER_MARK))
    cf_at = next(i for i, h in enumerate(headings) if h.startswith(cf.LEDGER_MARK))
    assert cf_at == vf_at + 1
