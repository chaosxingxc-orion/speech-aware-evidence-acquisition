"""NX round R6-P1: the registered cell is exactly what its package says it is (model-free, HELD).

Reads the committed fragments, candidate templates and package files only (no data root, no model, no server). Proves: the declared
module block compiles to the fragments' policy blocks (the loader's own check), the program is the compiled review-off c10 on lock
v2.2 (the R5 arm's base), the Perception template group has the five arms in order with the delivering lock last and the twin
declared, every pinned template hashes to its file and matches its tag set, the plan budgets are the ceiling arithmetic
(rows x 10 = 10,800), the FIT cap is structural (rows x ceiling x 4), the identities (run, attempt, chain, flip, repin, recipe, ledger,
driver defaults) agree, the stage3_measurement block is a node column with a twin, no benefit claim and the nominated ceiling, the
finite-completion and ReAct-exhaustion policies are declared, and the cell is HELD with DRAFT ledger rows.

TEMPLATE TOKENS ARE AN ESTIMATE (word counts). When the registered tokenizer pass lands (package README, "Template tokens: ESTIMATE"),
regenerate the package with the writer and adjust ``test_template_tokens_are_the_labelled_word_count_estimate``.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "flights" / "nx"))
sys.path.insert(0, str(REPO / "scripts" / "checks"))
sys.path.insert(0, str(REPO / "scripts" / "analysis"))

import nx_r6_family as nf  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402

R5_BASELINE = "slurp-native-stage3-nx-r5-composed-dev2000-added-baseline-v1"


def _load(relpath: str) -> dict:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _baseline(kind: str) -> dict:
    return _load(f"configs/baseline/{nf.names(kind)['baseline']}.json")


def _experiment(kind: str) -> dict:
    return _load(f"configs/experiment/{nf.names(kind)['experiment']}.json")


def _roster(kind: str) -> dict:
    return _load(nf.ROSTER[kind])


def _ledger_rows() -> list:
    from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables

    return _parse_ledger_tables((REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8"))


def _all_draft() -> bool:
    """True while every flight row of the cell is still a DRAFT (nothing countersigned, nothing flipped)."""

    rows = {r.get("run/experiment id"): r for r in _ledger_rows()}
    ids = [nf.ARM["run_id"], nf.ARM["fit_run_id"], nf.SMOKE["run_id"], nf.SMOKE["fit_run_id"]]
    # the DRAFT marker of an unsigned row is "REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending)"; a countersigned row
    # still says "root countersigns the five DRAFT rows" in its READINESS HELD sentence, so a bare "DRAFT" test is not enough
    return all("(DRAFT, root countersignature pending)" in rows[i].get("notes", "") for i in ids)


# --- identity ------------------------------------------------------------------------------------------------------------


def test_family_identities_are_frozen():
    assert (nf.ARM["experiment"], nf.ARM["run_id"], nf.DECISION_ID, nf.DECISION_RELPATH, nf.READ_RUN_ID, nf.ARMS) == (
        "slurp-native-stage3-nx-r6-perception-fold-b-v1", "SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-V1",
        "slurp-nx-r6-perception-fold-b-admission-v1", "coordination/slurp-nx-r6-perception-fold-b-v1/root-admission-v1.json",
        "SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-COLUMN-READ-V1", ("p1", "p2", "p3"))
    assert nf.ARM["attempt_id"] == "attempt-slurp-native-stage3-nx-r6-perception-fold-b-generation-v1"
    assert nf.ARM["fit_run_id"] == nf.ARM["run_id"].replace("-V1", "-FIT-V1")
    assert nf.SMOKE["run_id"] == nf.ARM["run_id"].replace("-V1", "-SMOKE-4-V1")
    assert nf.SMOKE["fit_run_id"] == nf.ARM["run_id"].replace("-V1", "-SMOKE-4-FIT-V1")
    assert nf.SMOKE["experiment"] == nf.ARM["experiment"].replace("-v1", "-smoke-4-v1")
    # the smoke is the single recovery re-registration (rec1); the arm keeps its first-attempt ids
    assert nf.SMOKE["attempt_id"].endswith("-smoke-4-generation-rec1-v1") and nf.SMOKE["fit_attempt_id"].endswith("-smoke-4-fit-rec1-v1")
    assert nf.ARM["fit_attempt_id"] == "attempt-slurp-native-stage3-nx-r6-perception-fold-b-fit-v1"
    assert nf.ARM_ORDER == ("p1", "p2", "p3", "aa", "lock") and nf.ARM_ORDER[-2:] == (nf.TWIN, nf.DELIVERING)
    assert nf.CEILING == 10 == nf.BASE_CONTACTS + 2 * (len(nf.ARM_ORDER) - 1) and nf.PROGRAM == "phase-native-module-v1-c10"
    assert nf.PACKAGE == "docs/readiness/2026-10-10-slurp-nx-r6-perception-fold-b-v1"
    assert (nf.TUNING_ROSTER, nf.READ_ROSTER) == ("SLURP-EVO-FOLD-A-V2", "SLURP-EVO-FOLD-B-V2")   # the R1 cells' roster ids
    assert nf.ROSTER["arm"].endswith("slurp-evo-fold-b-v2.json")
    assert (nf.FLOOR_SLU_PP, nf.FLOOR_INTENT_PP, nf.EXPECTED_EFFECT_PP) == (1.49, 0.65, 0.75)


def test_the_driver_defaults_name_this_run():
    import slurp_nx_r6_upstream_empty as driver

    assert (driver.R6_RUN_ID, driver.R6_ATTEMPT_ID, driver.R6_ROWS) == (nf.ARM["run_id"], nf.ARM["attempt_id"], nf.ROWS)
    assert driver.GAIN_READ_ID == "SAEA-SLURP-NX-R6-PERCEPTION-GAIN-V1"


# --- the compiled cell ---------------------------------------------------------------------------------------------------


def test_declared_module_block_verifies_and_the_program_is_the_review_off_c10_on_lock_v2_2():
    for kind in ("arm", "smoke"):
        document = _baseline(kind)
        block = document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
        cm.verify_declared_module(block, document, repo_root=REPO)
        assert block["lock"] == nf.LOCK == "v2.2" and block["review_loop"] == "off"
        assert document["policy"] == nf.PROGRAM == "phase-native-module-v1-c10"
        ne = document["native_episode"]
        assert (ne["review_loop"], ne["max_revisions"]) == ("off", 0)
        assert document["phase_tools"] == {}
        assert ne["deliver_normaliser"]["normaliser"] == "saea-deliver-normalise-v4g"
        values = dict(document)
        values["carrier_lock_key"] = document.get("carrier_lock_key", "slurp")
        parsed = load_native_episode_config(values, default_phase_program(document["policy"]))
        assert parsed.max_contacts == nf.CEILING == 10 and not parsed.review_loop_enabled
        group = parsed.perception_branch_group
        assert group.is_template and group.level == 2 and parsed.supply_variant_group is None
        assert tuple(b.branch_id for b in group.branches) == nf.ARM_ORDER


def test_the_base_is_the_r5_arms_base_rederived_for_fold_b():
    """Lock v2.2, review-off, the same two armed components, the v4g normaliser and the locked Solver template as the R5 arm."""

    r5 = _load(f"configs/baseline/{R5_BASELINE}.json")
    r5_block = r5["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
    for kind in ("arm", "smoke"):
        document = _baseline(kind)
        block = document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
        assert (block["lock"], block["review_loop"], block["profile"], block["module_id"]) == (
            r5_block["lock"], r5_block["review_loop"], r5_block["profile"], r5_block["module_id"])
        armed = sorted(c["component_id"] for c in block["components"] if c["state"] != "off")
        assert armed == sorted(c["component_id"] for c in r5_block["components"] if c["state"] != "off")
        assert armed == sorted([cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY])
        for key in ("deliver_normaliser", "review_loop", "max_revisions", "finite_completion_policy", "react_exhaustion_policy"):
            assert document["native_episode"][key] == r5["native_episode"][key], key
        assert document["phase_tools"] == r5["phase_tools"] == {}
        assert document["phase_material"]["solver"] == r5["phase_material"]["solver"]
        # the Fold B pins, not DEV-2000-ADDED's
        assert "FOLD-B" in json.dumps(block["components"]) and "DEV2000" not in json.dumps(block["components"])
    assert r5["native_episode"]["deliver_normaliser"]["normaliser"] == "saea-deliver-normalise-v4g"


def test_finite_completion_and_react_exhaustion_policies_are_declared():
    for kind in ("arm", "smoke"):
        ne = _baseline(kind)["native_episode"]
        assert ne["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert ne["react_exhaustion_policy"] == "continue-without-answer"


def test_perception_template_arms_are_pinned_to_the_committed_candidate_files():
    document = _baseline("arm")
    role = document["native_episode"]["roles"][nf.NODE]
    assert "branches" not in role and "supply_variants" not in document["native_episode"]["roles"]["solver"]
    group = role["template_variants"]
    assert group["node"] == "perception"
    arms = group["arms"]
    assert [a["arm_id"] for a in arms] == list(nf.ARM_ORDER)
    assert arms[-1].get("deliver") is True and "instruction_template" not in arms[-1]
    assert arms[-2] == {"arm_id": "aa", "replicate_of": "lock"}
    for arm in arms[: len(nf.ARMS)]:
        pin = arm["instruction_template"]
        assert pin["relpath"] == nf.CANDIDATE_PATHS[arm["arm_id"]]
        assert hashlib.sha256((REPO / pin["relpath"]).read_bytes()).hexdigest() == pin["sha256"]
    assert hashlib.sha256((REPO / nf.LOCKED_TEMPLATE).read_bytes()).hexdigest() == nf.LOCKED_TEMPLATE_SHA
    assert document["phase_material"]["perception"]["instruction_template"] == "probes/slurp_native_role_perception_v3.txt"
    assert group["fit_estimate"] == nf.FIT_ESTIMATE and group["max_supplied_items"] == nf.MAX_SUPPLIED_ITEMS
    # the candidates README prints the digests the cell pins
    readme = (REPO / nf.CANDIDATES_README).read_text(encoding="utf-8")
    for arm, pin in nf.candidate_pins().items():
        assert pin["sha256"] in readme, arm
    assert nf.LOCKED_TEMPLATE_SHA in readme


def test_each_candidates_tag_instruction_matches_the_tag_set_the_read_will_use():
    grammar = (REPO / nf.TAG_GRAMMAR).read_text(encoding="utf-8")
    assert "E=" in grammar and "unsure" in grammar
    for arm, path in nf.CANDIDATE_PATHS.items():
        text = (REPO / path).read_text(encoding="utf-8")
        shape = "E=<none|some|unsure>" if "unsure" in nf.TAG_SETS[arm] else "E=<none|some>"
        assert shape in text, arm
        assert ("E=unsure when" in text) == ("unsure" in nf.TAG_SETS[arm]), arm
        assert text.isascii() and text.endswith("\n") and "\r" not in text
        assert "<" not in text.replace("<none|some", "").replace("<scenario>_<action>", "").replace(
            "<heard words>", "").replace("<at most 8 English words describing the speech-grounded distinction>", "").replace(
            "unsure>", "").replace("|unsure>", "")
    assert nf.TAG_SETS == {"p1": ("none", "some"), "p2": ("none", "some"), "p3": ("none", "some", "unsure")}


def test_stage3_algorithm_label_resolves_in_the_registry():
    from speech_aware_evidence_acquisition.core.base import STAGE3_ALGORITHMS

    for kind in ("arm", "smoke"):
        label = _experiment(kind)["stage3_algorithm"]
        assert label["id"] == "none" and label["id"] in STAGE3_ALGORITHMS.names() and label["operators_used"] == []


# --- budgets and the FIT cap ---------------------------------------------------------------------------------------------


def test_budgets_are_the_ceiling_arithmetic_and_the_fit_estimate_holds():
    arm, smoke = _experiment("arm"), _experiment("smoke")
    for document, kind, rows in ((arm, "arm", 1080), (smoke, "smoke", 4)):
        fam = document["family_budget"]
        audio = sum(float(i["audio_seconds"]) for i in _roster(kind)["items"])
        # The adapter enforces the plan run-cumulatively across the attempts of a run id: the smoke (rec1) carries the original plan
        # plus the failed attempt's realised spend; the arm is a first attempt.
        spent_calls, spent_audio, _ = _recovery_spend(kind)
        assert fam["generation_calls_cap"] == rows * nf.CEILING + spent_calls == document["execution_plan"]["planned_model_calls"]
        assert fam["native_task_contract_calls_cap"] == rows * nf.CEILING + spent_calls
        assert fam["fit_endpoint_calls_cap"] == nf.fit_contact_cap(rows) == rows * nf.CEILING * 4   # structural, never run-cumulative
        assert fam["repeated_speech_audio_seconds_cap"] == math.ceil(math.ceil(audio * nf.CEILING - 1e-9) + spent_audio - 1e-9)
        assert document["execution_plan"]["planned_speech_audio_seconds"] == fam["repeated_speech_audio_seconds_cap"]
        assert document["cells"][0]["readiness"]["state"] in ("held", "ready")
        assert document["execution_plan"]["execution_profile"] == "bounded-discovery-probe"
        assert document["execution_plan"]["split_role"] == "discovery"
    assert (arm["execution_plan"]["planned_model_calls"], arm["family_budget"]["fit_endpoint_calls_cap"]) == (10800, 43200)
    # smoke after the rec1 recovery: 40 + 20 spent = 60 calls, ceil(102 + 50.908) = 153 speech seconds, FIT cap still the structural 160
    assert (smoke["execution_plan"]["planned_model_calls"], smoke["family_budget"]["fit_endpoint_calls_cap"]) == (60, 160)
    assert smoke["execution_plan"]["planned_speech_audio_seconds"] == 153
    assert (arm["execution_plan"]["planned_speech_audio_seconds"], arm["family_budget"]["generation_calls_cap"]) == (31548, 10800)
    assert arm["family_budget"]["gpu_hours_fit_inclusive"] == arm["execution_plan"]["planned_gpu_hours"] == 4.1
    assert smoke["family_budget"]["gpu_hours_fit_inclusive"] == 1.0
    estimates = nf.arm_prompt_estimates()
    assert max(estimates.values()) <= nf.PROMPT_LIMIT_TOKENS and set(estimates) == {"lock", *nf.ARMS}


def test_template_tokens_are_the_labelled_word_count_estimate():
    """ESTIMATE, not a tokenizer pass. Adjust this test (and regenerate the package) when the registered pass lands."""

    tokens = nf.template_tokens()
    assert tokens == {"lock": 256, "p1": 374, "p2": 486, "p3": 528}
    for arm, path in nf.CANDIDATE_PATHS.items():
        assert tokens[arm] == math.ceil(2.0 * len((REPO / path).read_bytes().split()))
    declared = {a["arm_id"]: a["template_tokens"] for a in _baseline("arm")["native_episode"]["roles"][nf.NODE]["template_variants"]["arms"]
                if "template_tokens" in a}
    assert declared == tokens
    measure = _load(f"{nf.PACKAGE}/fit-measure-v1.json")
    assert measure == nf.fit_measure() and measure["status"].startswith("ESTIMATE")
    assert measure["contacts"] == {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0}
    facts = _load(f"{nf.PACKAGE}/registered-facts-v1.json")
    assert facts["fit_measure"]["status"].startswith("ESTIMATE")
    assert all(k.endswith("ESTIMATE") for c in facts["candidates"].values() for k in c if k.startswith("template_tokens"))
    readme = (REPO / nf.PACKAGE / "README.md").read_text(encoding="utf-8")
    assert "Template tokens: ESTIMATE" in readme and "TODO" in readme


def test_registered_measurement_block_is_a_node_column_measurement_cell_with_a_twin():
    facts = _load(f"{nf.PACKAGE}/registered-facts-v1.json")
    block = facts["stage3_measurement"][nf.ARM["run_id"]]
    assert block["measurement_design"] == "same-flight-node-column"
    assert block["aa_arm_id"] == "aa" and block["claim"] == "nominated"
    assert block["primary_metric_key"] == "slu" and block["claims_benefit"] is False
    assert block["expected_effect_pp"] == nf.EXPECTED_EFFECT_PP == 0.75
    assert "MEASUREMENT cell" in block["note"] and "245/247" in block["note"]
    assert block["template_variants"] == {"node": "perception", "candidate_arms": 3, "twin": True}
    assert (block["tuning_roster"], block["read_roster"], block["rows"]) == (nf.TUNING_ROSTER, nf.READ_ROSTER, 1080)
    cost = block["variant_cost"]
    assert cost["extra_contacts_per_row"] == len(nf.ARM_ORDER) - 1 and cost["extra_perception_contacts_per_row"] == 4
    assert cost["extra_solver_contacts_per_row"] == 4 and cost["extra_audio_seconds"] > 0
    assert "DISCLOSURE" in block["note"] and facts["tuning_disclosure"] == nf.TUNING_DISCLOSURE
    smoke = facts["stage3_measurement"][nf.SMOKE["run_id"]]
    assert smoke["measurement_design"] == "form-proof" and smoke["claims_benefit"] is False
    recipe = _load(f"{nf.PACKAGE}/analysis-recipe-v1.json")
    assert recipe["read_run_id"] == nf.READ_RUN_ID and recipe["recipe_id"] == nf.RECIPE_ID
    assert recipe["arms"]["arm"]["run_id"] == nf.ARM["run_id"] and recipe["arms"]["arm"]["attempt_id"] == nf.ARM["attempt_id"]
    columns = recipe["arms"]["columns"]
    assert [k for k in columns if k not in ("aa", "lock")] == list(nf.ARMS)   # the read driver derives candidates this way
    assert all("relpath" in columns[a] for a in nf.ARMS) and "relpath" in columns["lock"]
    assert set(recipe["official_columns"]["passes"]) == {f"{a}-vs-lock" for a in nf.ARMS} | {"aa-vs-lock"}
    assert recipe["tag_sets"] == {a: list(v) for a, v in nf.TAG_SETS.items()}
    assert recipe["acceptance"]["node_local"]["none_recall_min"] == 0.80
    assert recipe["acceptance"]["node_local"]["none_precision_min"] == 0.75
    assert recipe["acceptance"]["information_gain"]["bootstrap"] == {"unit": "whole utterance", "draws": 2000, "seed": 20261010}
    assert recipe["acceptance"]["delivered_estimate"]["bootstrap"]["draws"] == 10000
    assert recipe["information_gain"]["baselines"] == ["n1", "n1+prior", "n1+prior+lock"]
    assert recipe["node_local"]["tag_grammar"]["sha256"] == hashlib.sha256((REPO / nf.TAG_GRAMMAR).read_bytes()).hexdigest()


def test_the_effect_floor_gate_accepts_the_declaration():
    import stage3_effect_floor_check as floor

    assert floor.NODE_COLUMN_DESIGN == "same-flight-node-column" and "perception" in floor.TEMPLATE_VARIANT_NODES
    block = _load(f"{nf.PACKAGE}/registered-facts-v1.json")["stage3_measurement"][nf.ARM["run_id"]]
    # a claim-free declaration sits under the 1.49 pp floor without an effect-below-floor finding (the rule only looks at
    # cells that claim a benefit); the same numbers WITH a claim would be one.
    assert block["claims_benefit"] is False and block["expected_effect_pp"] < nf.FLOOR_SLU_PP


# --- pre-contact preflight -----------------------------------------------------------------------------------------------


def _recovery_spend(kind: str) -> tuple:
    """(contacts, speech seconds, predecessor attempt ids) already spent by earlier attempts of this kind's run id."""

    if kind != "smoke" or not nf.SMOKE_RECOVERY:
        return 0, 0.0, set()
    ids = {p["attempt_id"] for p in nf.SMOKE_RECOVERY["predecessors"]}
    return nf.SMOKE_PREDECESSOR_CONTACTS_SPENT, nf.SMOKE_PREDECESSOR_SPEECH_SECONDS_SPENT, ids


def test_pre_contact_preflight_fit_gate_and_native_config():
    from speech_aware_evidence_acquisition.core.flight.runtime import arm_uses_speech_feature_packets
    from speech_aware_evidence_acquisition.core.preparation_fit import validate_native_contact_fit_config

    for kind in ("arm", "smoke"):
        names = nf.names(kind)
        baseline = _baseline(kind)
        program = default_phase_program(baseline["policy"])
        spec = validate_native_contact_fit_config(baseline, program)
        assert spec is not None
        ids = [item["sample_id"] for item in _roster(kind)["items"]]
        assert ids and all(isinstance(i, str) and i for i in ids) and len(set(ids)) == len(ids)
        rows = len(ids)
        assert rows == (4 if kind == "smoke" else nf.ROWS)
        assert arm_uses_speech_feature_packets(baseline["arm"]), kind
        assert program.max_contacts == nf.CEILING
        required_cap = rows * program.max_contacts * (spec["max_speech_packets"] + 3)
        assert spec["contact_cap"] == required_cap == nf.fit_contact_cap(rows), (kind, spec["contact_cap"], required_cap)
        gen_plan = _load(f"{nf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")["execution_plan"]
        assert spec["run_id"] != gen_plan["run_id"] and spec["attempt_id"] != gen_plan["attempt_id"]
        assert spec["run_id"] == names["fit_run_id"] and spec["attempt_id"] == names["fit_attempt_id"]


def test_pre_contact_preflight_plans_budgets_and_ledger_rows():
    from dataclasses import fields

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan

    ledger = _ledger_rows()
    allowed = {f.name for f in fields(ExecutionPlan)}
    for kind in ("arm", "smoke"):
        names = nf.names(kind)
        roster = _roster(kind)
        rows = len(roster["items"])
        max_contacts = default_phase_program(_baseline(kind)["policy"]).max_contacts
        audio = sum(float(i["audio_seconds"]) for i in roster["items"])
        worst_calls = rows * max_contacts
        worst_audio = math.ceil(audio * max_contacts - 1e-9)
        spent_calls, spent_audio, _ = _recovery_spend(kind)
        declared = _experiment(kind)["execution_plan"]
        # the run-cumulative adapter budget covers what earlier attempts of the run id spent PLUS this attempt's worst case
        assert declared["planned_model_calls"] >= spent_calls + worst_calls, kind
        assert declared["planned_speech_audio_seconds"] >= spent_audio + worst_audio, kind
        worst_audio = math.ceil(worst_audio + spent_audio - 1e-9)
        for plan_kind in ("generation", "fit"):
            registered = _load(f"{nf.PACKAGE}/{names['prefix']}{plan_kind}-plan-registered-v1.json")["execution_plan"]
            plan = ExecutionPlan(**{k: v for k, v in registered.items() if k in allowed}).validate(source_root=REPO)
            if plan_kind == "generation":
                assert plan.planned_model_calls == declared["planned_model_calls"]
                assert plan.run_id == names["run_id"] and plan.attempt_id == names["attempt_id"]
            else:
                assert plan.planned_model_calls == _baseline(kind)["native_contact_fit"]["contact_cap"]
                assert plan.run_id == names["fit_run_id"] and plan.attempt_id == names["fit_attempt_id"]
            assert plan.planned_speech_audio_seconds >= worst_audio
            matched = [r for r in ledger if r.get("run/experiment id") == plan.run_id]
            assert len(matched) == 1, (plan.run_id, len(matched))
            row = matched[0]
            assert row["consumed"].strip().lower() == "yes" and "CONSUMED (" in row["notes"]  # flown and sealed; closed by scripts/flights/batch/ledger_mark_consumed.py (SEALED prefix)
            assert row["execution profile"] == plan.execution_profile and row["split role"] == plan.split_role
            assert row["split identity hash"] == plan.split_identity_hash == roster["split_identity_hash"]
            assert int(row["calls"]) == plan.planned_model_calls
            assert int(row["speech audio seconds"]) == plan.planned_speech_audio_seconds
            assert float(row["gpu hours"]) == float(plan.planned_gpu_hours)


def test_pre_contact_preflight_identities_agree_and_are_fresh():
    for kind in ("arm", "smoke"):
        names = nf.names(kind)
        experiment, baseline = _experiment(kind), _baseline(kind)
        protocol = _load(f"{nf.PACKAGE}/protocol-registered-v1.json")["cells"][kind]
        gen = _load(f"{nf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")["execution_plan"]
        fit = _load(f"{nf.PACKAGE}/{names['prefix']}fit-plan-registered-v1.json")["execution_plan"]
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
    # one-time key: a recovery attempt id is never any recorded predecessor's (generation or FIT)
    _, _, predecessors = _recovery_spend("smoke")
    assert nf.SMOKE["attempt_id"] not in predecessors
    assert nf.SMOKE["fit_attempt_id"] not in {p.replace("-generation-", "-fit-") for p in predecessors}
    # the recovery is recorded on the smoke only: the protocol, the smoke generation plan; the arm's plan carries none
    protocol = _load(f"{nf.PACKAGE}/protocol-registered-v1.json")
    assert protocol["recovery"] == {"smoke": nf.SMOKE_RECOVERY}
    assert _load(f"{nf.PACKAGE}/smoke-generation-plan-registered-v1.json")["execution_plan"]["recovery"] == nf.SMOKE_RECOVERY
    assert "recovery" not in _load(f"{nf.PACKAGE}/generation-plan-registered-v1.json")["execution_plan"]


def test_smoke_recovery_rec1_is_run_cumulative_fit_structural_and_leaves_the_arm_untouched():
    """The cell's single recovery re-registration: spend read from the failed attempt, cumulative arithmetic, structural FIT cap."""

    rec = nf.SMOKE_RECOVERY
    assert rec["recovery_index"] == 1 and nf.SMOKE_REC == "-rec1"
    assert rec["predecessor_attempt_id"] == "attempt-slurp-native-stage3-nx-r6-perception-fold-b-smoke-4-generation-v1"
    assert rec["predecessor_fit_attempt_id"] == "attempt-slurp-native-stage3-nx-r6-perception-fold-b-smoke-4-fit-v1"
    assert [p["attempt_id"] for p in rec["predecessors"]] == [rec["predecessor_attempt_id"]]
    # the failed attempt's realised spend (its attempt record: actual calls 20, audio_seconds 50.908125): 4 rows x 5 Perception arms
    assert nf.SMOKE_PREDECESSOR_CONTACTS_SPENT == 20 == nf.SMOKE_ROWS * len(nf.ARM_ORDER)
    assert nf.SMOKE_PREDECESSOR_SPEECH_SECONDS_SPENT == pytest.approx(50.908, abs=1e-9)
    assert rec["fit_cap_rule"].endswith("rows x max_contacts x (max_speech_packets + 3).")
    assert "second failure closes the cell" in rec["rule"] and "source-hash binding fix" in rec["reason"]
    smoke_audio = sum(float(i["audio_seconds"]) for i in _roster("smoke")["items"])
    original_calls, original_audio = nf.SMOKE_ROWS * nf.CEILING, math.ceil(smoke_audio * nf.CEILING - 1e-9)
    assert (original_calls, original_audio) == (40, 102)      # the failed attempt's own plan (its attempt record's reservation)
    # the recovery plan = the original plan + the failed attempt's realised spend; audio rounded up
    assert nf.smoke_cumulative_budget(original_calls, original_audio) == (60, 153)
    experiment = _experiment("smoke")
    assert (experiment["execution_plan"]["planned_model_calls"], experiment["execution_plan"]["planned_speech_audio_seconds"]) == (60, 153)
    assert experiment["execution_plan"]["planned_gpu_hours"] == 1.0
    # the FIT cap is structural and NOT scaled by the recovery: rows x max_contacts x (max_speech_packets + 3)
    baseline = _baseline("smoke")
    assert baseline["native_contact_fit"]["contact_cap"] == nf.fit_contact_cap(nf.SMOKE_ROWS) == 4 * 10 * 4 == 160
    assert experiment["family_budget"]["fit_endpoint_calls_cap"] == 160
    assert baseline["native_contact_fit"]["attempt_id"] == nf.SMOKE["fit_attempt_id"]
    assert experiment["cells"][0]["attempt_id"] == nf.SMOKE["attempt_id"]
    # the arm is untouched: first-attempt ids, first-attempt budget, no recovery suffix anywhere
    arm_experiment, arm_baseline = _experiment("arm"), _baseline("arm")
    assert arm_experiment["cells"][0]["attempt_id"] == "attempt-slurp-native-stage3-nx-r6-perception-fold-b-generation-v1"
    assert arm_baseline["native_contact_fit"]["attempt_id"] == "attempt-slurp-native-stage3-nx-r6-perception-fold-b-fit-v1"
    assert "rec" not in nf.ARM["attempt_id"].split("generation")[1] and "rec" not in nf.ARM["fit_attempt_id"].split("fit")[1]
    assert arm_experiment["execution_plan"]["planned_model_calls"] == 10800 == arm_experiment["family_budget"]["generation_calls_cap"]
    assert arm_baseline["native_contact_fit"]["contact_cap"] == 43200 == arm_experiment["family_budget"]["fit_endpoint_calls_cap"]
    assert "-rec1" not in json.dumps(arm_experiment) and "-rec1" not in json.dumps(arm_baseline)
    # the smoke's failure policy records that the single recovery is used
    assert "single root-diagnosed recovery re-registration" in experiment["failure_policy"]


def test_registered_plans_pin_the_hashes_the_fragments_compose_to():
    from speech_aware_evidence_acquisition.core.config import compose, protocol_hash

    for kind in ("arm", "smoke"):
        names = nf.names(kind)
        document = _experiment(kind)
        cell = document["cells"][0]
        composed = compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], names["experiment"])
        split = document["population"]["split_identity_hash"]
        plan = _load(f"{nf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")
        # While the cell is HELD and unflipped the registered hashes are the composed ones; the flip loop re-pins them together.
        if _all_draft():
            assert plan["composed_config_hash"] == composed.config_hash
            assert plan["execution_plan"]["protocol_hash"] == protocol_hash(composed.config_hash, composed.values["arm"], split)
        assert plan["protocol_document"]["sha256"] == hashlib.sha256(
            (REPO / nf.PACKAGE / "protocol-registered-v1.json").read_bytes()).hexdigest()


# --- scripts, held state, ledger -----------------------------------------------------------------------------------------


def test_chain_flip_repin_mint_and_read_scripts_agree_with_the_family():
    scripts = REPO / "scripts" / "flights" / "nx"
    chain = (scripts / "batch_chain_nx_r6.sh").read_text(encoding="utf-8")
    flip = (scripts / "nx_r6_flip.sh").read_text(encoding="utf-8")
    repin = (scripts / "nx_r6_repin_cell.sh").read_text(encoding="utf-8")
    for text in (chain, flip, repin):
        assert f"SLUG={nf.SLUG}" in text and f"SHORT={nf.SHORT}" in text
        assert "\r" not in text
    assert f"SMOKE_REC={nf.SMOKE_REC}" in chain and 'rec = os.environ["NX_SMOKE_REC"]' in chain
    assert '"smoke_attempt_id": f"attempt-slurp-native-stage3-{slug}-smoke-4-generation{rec}-v1"' in chain
    assert '"gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1"' in chain
    assert nf.SMOKE["attempt_id"] == f"attempt-slurp-native-stage3-{nf.SLUG}-smoke-4-generation{nf.SMOKE_REC}-v1"
    assert nf.ARM["attempt_id"] == f"attempt-slurp-native-stage3-{nf.SLUG}-generation-v1"
    assert '"expected_rows": 1080, "contacts_per_row": 10, "ceiling_per_row": 10, "notool": True' in chain
    assert '"owner": f"root-slurp-native-stage3-{slug}-v1"' in chain
    assert "LOG=/home/chao/batch-chain-$SHORT.out" in chain and "$SHORT-flight-commit.txt" in chain
    assert f"RD=docs/readiness/{nf.DATE}-slurp-$SLUG-v1" in flip and f"RD=docs/readiness/{nf.DATE}-slurp-$SLUG-v1" in repin
    assert "nx_r6_repin_cell.sh" in flip and "unset ALLOW_OUTPUT_CHANGE" in repin and "--allow-output-change must never" in flip
    assert "export EXP=$CELL ARM=0" in repin
    read = (REPO / "scripts" / "analysis" / "nx_r6_read.sh").read_text(encoding="utf-8")
    assert f"{nf.PACKAGE}/analysis-recipe-v1.json" in read
    assert '--recipe-id "$RECIPE_ID"' in read and "--verdict-source" in read and "--tag-set" in read
    assert "read_require_countersigned" in read and 'BASELINES="n1 n1+prior n1+prior+lock"' in read
    mint = (scripts / "nx_r6_mint_receipt.py").read_text(encoding="utf-8")
    assert "nx_r6_family as nf" in mint and "eligible_run_ids" in mint
    for name in ("nx_r6_dry_run.py", "nx_r6_mint_receipt.py", "derive_slurp_nx_r6_cells.py", "write_slurp_nx_r6_registration.py",
                 "nx_r6_family.py"):
        ast.parse((scripts / name).read_text(encoding="utf-8"))
    # every script that names a run id uses the family's
    assert "nx_r6_family" in (scripts / "nx_r6_dry_run.py").read_text(encoding="utf-8")


def test_the_cell_is_held_and_the_package_is_complete():
    for kind in ("arm", "smoke"):
        experiment = _experiment(kind)
        cell = experiment["cells"][0]
        state = cell["readiness"]["state"]
        requirements = cell["readiness"]["requirements"]
        decision = [r for r in requirements if r["kind"] == "decision"]
        # the cell's own prepared supply: v1 at the first flip; a later flip at a changed implementation identity mints v2, v3, ...
        own_supply = [r for r in requirements if re.search(r"/phase-supply-v\d+\.json$", r["relpath"])]
        agreement = [r for r in requirements if r["relpath"].endswith("FOLD-B-V1/agreement.jsonl")]
        assert len(decision) == len(own_supply) == len(agreement) == 1 and len(requirements) == 3
        assert decision[0]["relpath"] == nf.DECISION_RELPATH and decision[0]["expected_decision_id"] == nf.DECISION_ID
        assert own_supply[0]["relpath"].startswith(f"prepared/{nf.names(kind)['run_id']}/phase-supply-v")   # E16: its own
        if _all_draft():
            # held at registration (2026-10-10); flipped to ready for the R6-P1 chain (flight commits 58c546b54, 1f04ce42d)
            assert state in ("held", "ready")
            # the receipt and the supply are minted at the flip: the registered pins are the zero placeholder until then
            assert decision[0]["sha256"] == "0" * 64 and own_supply[0]["sha256"] == "0" * 64
            assert agreement[0]["sha256"] != "0" * 64
            assert "HELD" in cell["readiness"]["reason"]
            assert "prepared_phase_supply" not in _baseline(kind)          # E16: the flip mints this cell's own
        else:
            assert state in ("held", "ready")
        assert ("campaign" in cell["allowed_execution_stages"]) == (kind == "arm")
        assert "paper-scale" not in json.dumps(experiment["execution_plan"])
    package = REPO / nf.PACKAGE
    for name in ("README.md", "registered-facts-v1.json", "protocol-registered-v1.json", "analysis-recipe-v1.json",
                 "root-admission-draft-v1.json", "fit-measure-v1.json", "generation-plan-registered-v1.json",
                 "fit-plan-registered-v1.json", "smoke-generation-plan-registered-v1.json", "smoke-fit-plan-registered-v1.json"):
        assert (package / name).is_file(), name
    assert (REPO / nf.PREREG).is_file() and (REPO / nf.CAMPAIGN).is_file()
    campaign = _load(nf.CAMPAIGN)
    assert campaign["cells"] == [{"cell": nf.ARM["experiment"], "experiment": nf.ARM["experiment"]}]   # arm alone, no A/A cell
    draft = _load(f"{nf.PACKAGE}/root-admission-draft-v1.json")
    assert draft["status"] == "DRAFT-NOT-MINTED" and draft["decision_id"] == nf.DECISION_ID
    assert draft["eligible_run_ids"] == [nf.ARM["run_id"], nf.ARM["fit_run_id"], nf.SMOKE["run_id"], nf.SMOKE["fit_run_id"]]
    assert draft["population"]["test_contact_authorized"] is False and draft["population"]["fold_a_contact_authorized"] is False
    assert draft["budget"]["paid_api_calls"] == 0 and draft["budget"]["generation_calls_cap"] == 10800
    assert draft["recorded_at_utc"] is None
    fence = (REPO / nf.PREREG).read_text(encoding="utf-8")
    assert "stage3_measurement" in fence and nf.ARM["run_id"] in fence and '"claims_benefit": false' in fence


def test_the_ledger_rows_are_present_unconsumed_and_draft_or_countersigned():
    import flight_registration_check as frc
    from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables

    text = (REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    assert text.count(nf.LEDGER_MARK) == 1 and nf.LEDGER_MARK.startswith("## NX round R6-P1")
    rows = _parse_ledger_tables(text)
    ids = [nf.ARM["run_id"], nf.ARM["fit_run_id"], nf.SMOKE["run_id"], nf.SMOKE["fit_run_id"], nf.READ_RUN_ID]
    for run_id in ids:
        matched = [r for r in rows if r.get("run/experiment id") == run_id]
        assert len(matched) == 1, run_id
        row = matched[0]
        notes = row.get("notes", "")
        assert "DRAFT" in notes or frc.is_countersigned(row), run_id
        if run_id != nf.READ_RUN_ID:
            assert row["consumed"].strip().lower() in ("no", "yes"), run_id
        else:
            assert row["execution profile"] == "model-free-check"
    if _all_draft():
        for run_id in ids:
            row = next(r for r in rows if r.get("run/experiment id") == run_id)
            assert not frc.is_countersigned(row) and row["consumed"].strip().lower() == "no", run_id
        arm_row = next(r for r in rows if r.get("run/experiment id") == nf.ARM["run_id"])
        assert "ESTIMATE" in arm_row["notes"] and "claims_benefit false" in arm_row["notes"]
    # the smoke recovery (rec1): the two smoke rows were AMENDED in place (the originals stay; the amendment names the failed attempt
    # and the rec1 ids); the arm rows carry no recovery text and keep their first-attempt ids.
    by_id = {r.get("run/experiment id"): r for r in rows}
    for run_id, fit in ((nf.SMOKE["run_id"], False), (nf.SMOKE["fit_run_id"], True)):
        row = by_id[run_id]
        notes = row["notes"]
        attempt = nf.SMOKE["fit_attempt_id"] if fit else nf.SMOKE["attempt_id"]
        predecessor = nf.SMOKE_RECOVERY["predecessor_fit_attempt_id" if fit else "predecessor_attempt_id"]
        assert notes.count("RECOVERY RE-REGISTRATION") == 1 and f"attempt {attempt}. Protocol hash" in notes
        assert predecessor in notes
        if not fit:
            assert "20 contacts / 50.908 speech-seconds" in notes
        assert nf.SMOKE["attempt_id"] in notes and nf.SMOKE["fit_attempt_id"] in notes
        assert "40 + 20 = 60 calls" in notes and "ceil(102 + 50.908) = 153" in notes and "160 = 4 rows x 10 contacts x 4 endpoints" in notes
        assert int(row["calls"]) == (160 if fit else 60) and int(row["speech audio seconds"]) == 153
        assert row["consumed"].strip().lower() == "yes" and "CONSUMED (" in row["notes"]  # flown and sealed; closed by scripts/flights/batch/ledger_mark_consumed.py (SEALED prefix)
    for run_id in (nf.ARM["run_id"], nf.ARM["fit_run_id"]):
        assert "RECOVERY RE-REGISTRATION" not in by_id[run_id]["notes"], run_id
    assert f"attempt {nf.ARM['attempt_id']}. Protocol hash" in by_id[nf.ARM["run_id"]]["notes"]
    # the section holds nothing but this cell's five rows
    section = text[text.index(nf.LEDGER_MARK):]
    section = section[: section.find("\n## ", 5)] if "\n## " in section[5:] else section
    assert len(re.findall(r"\| SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B", section)) == 5
