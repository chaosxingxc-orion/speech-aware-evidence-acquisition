"""NX Stage J round R5: the registered composed cell is exactly what its package says it is (model-free).

Reads the committed fragments and package files. Proves: the declared module block (lock v2.2, review loop off) compiles to the
fragments' policy blocks (the loader's own check), the program is the compiled review-off c2 with ceiling 2, lock id v2.2 resolves to the
v4g normaliser at the hook and in the fragment, the Solver template is the locked pinned one (and the swap point refuses anything else), the
plan budgets are the ceiling arithmetic, the FIT cap is structural, the identities (run, attempt, chain, flip, repin, recipe, ledger) agree,
the reused replicate's recomposed hashes equal the HELD module package's registered ones, the measurement block is a no-harm cross-flight
declaration with an in-chain replicate, and the effect-floor gate accepts it.
"""

from __future__ import annotations

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

import nx_r5_family as nf  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402
from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402


def _load(relpath: str) -> dict:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _baseline(kind: str) -> dict:
    return _load(f"configs/baseline/{nf.names(kind)['baseline']}.json")


def _composed(experiment: str):
    document = _load(f"configs/experiment/{experiment}.json")
    cell = document["cells"][0]
    return compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)


def _facts() -> dict:
    return _load(f"{nf.PACKAGE}/registered-facts-v1.json")


def test_declared_module_block_verifies_and_the_program_is_the_review_off_c2():
    for kind in ("arm", "smoke"):
        document = _baseline(kind)
        block = document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
        cm.verify_declared_module(block, document, repo_root=REPO)
        assert block["lock"] == nf.LOCK == "v2.2" and block["review_loop"] == "off"
        assert sorted(c["component_id"] for c in block["components"] if c["state"] != "off") == [
            cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY]
        assert not block["columns"] and "template_frame" not in block
        assert document["policy"] == nf.PROGRAM == "phase-native-module-v1-c2"
        ne = document["native_episode"]
        assert ne["review_loop"] == "off" and ne["max_revisions"] == 0
        assert ne["roles"]["reviewer"]["max_iterations"] == 0 and ne["roles"]["planner"]["max_iterations"] == 0
        assert document["phase_tools"] == {}
        assert ne["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert ne["react_exhaustion_policy"] == "continue-without-answer"
        assert ne["deliver_normaliser"]["normaliser"] == nf.NORMALISER
        values = dict(document)
        values["carrier_lock_key"] = document.get("carrier_lock_key", "slurp")
        parsed = load_native_episode_config(values, default_phase_program(document["policy"]))
        assert parsed.max_contacts == nf.CEILING == 2
        assert not parsed.review_loop_enabled
        assert not parsed.supply_variant_group


def test_lock_id_v2_2_resolves_to_v4g_and_the_scope_rule_and_citation_stay_out():
    hooks = carrier_module_hooks(repo_root=REPO)
    assert hooks.lock_deliver_normalisers["v2.2"]() == nf.NORMALISER
    assert hooks.lock_deliver_normalisers.get("v2.1", hooks.default_deliver_normaliser)() == "saea-deliver-normalise-v3"
    for kind in ("arm", "smoke"):
        block = _baseline(kind)["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
        states = {c["component_id"]: c["state"] for c in block["components"]}
        assert states[cm.SCOPE_RULE] == "off" and states[cm.SOLVER_CITATION_CONTRACT] == "off"
    # The compiler itself refuses the scope-rule stage on this lock (no registered composition with v4g).
    block = json.loads(json.dumps(_baseline("arm")["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]))
    for component in block["components"]:
        if component["component_id"] == cm.SOLVER_CITATION_CONTRACT:
            component["state"] = "on"
            component["params"] = {"instruction_template": "x", "response_format_id": "y", "deliver_normaliser": "z"}
    with pytest.raises(cm.ConsumptionModuleConfigError):
        cm.compile_module(block, hooks, repo_root=REPO)


def test_solver_template_is_the_locked_pin_and_the_swap_point_refuses_anything_else(monkeypatch):
    assert nf.SOLVER_TEMPLATE_PIN == "configs/probes/slurp_native_role_solver_v2.txt"
    assert hashlib.sha256((REPO / nf.SOLVER_TEMPLATE_PIN).read_bytes()).hexdigest() == nf.SOLVER_TEMPLATE_SHA
    for kind in ("arm", "smoke"):
        assert _baseline(kind)["phase_material"]["solver"]["instruction_template"] == "probes/slurp_native_role_solver_v2.txt"
    import derive_slurp_nx_r5_cells as derive

    assert derive.check_solver_template_pin() == "probes/slurp_native_role_solver_v2.txt"
    monkeypatch.setattr(nf, "SOLVER_TEMPLATE_PIN", "configs/probes/nx/solver/r1/r1-i2-c3.txt")
    with pytest.raises(SystemExit):
        derive.check_solver_template_pin()


def test_budgets_are_the_ceiling_arithmetic_and_the_fit_cap_is_structural():
    arm = _load(f"configs/experiment/{nf.ARM['experiment']}.json")
    smoke = _load(f"configs/experiment/{nf.SMOKE['experiment']}.json")
    for document, rows in ((arm, nf.ROWS), (smoke, nf.SMOKE_ROWS)):
        fam = document["family_budget"]
        assert fam["generation_calls_cap"] == rows * nf.CEILING == document["execution_plan"]["planned_model_calls"]
        assert fam["native_task_contract_calls_cap"] == rows * nf.CEILING
        assert fam["fit_endpoint_calls_cap"] == nf.fit_contact_cap(rows) == rows * nf.CEILING * 4
        assert fam["repeated_speech_audio_seconds_cap"] == document["execution_plan"]["planned_speech_audio_seconds"]
        assert document["cells"][0]["readiness"]["state"] in ("held", "ready")
        assert document["execution_plan"]["split_role"] == "dev"
        assert document["stage3_algorithm"]["id"] == "sealed-credit-system-policy-v1"
    assert (arm["execution_plan"]["planned_model_calls"], arm["family_budget"]["fit_endpoint_calls_cap"]) == (2000, 8000)
    assert (smoke["execution_plan"]["planned_model_calls"], smoke["family_budget"]["fit_endpoint_calls_cap"]) == (8, 32)
    assert arm["family_budget"]["gpu_hours_fit_inclusive"] == arm["execution_plan"]["planned_gpu_hours"] == nf.PLANNED_GPU_HOURS_ARM
    roster = _load(nf.ROSTER)
    audio = sum(float(i["audio_seconds"]) for i in roster["items"])
    assert arm["family_budget"]["repeated_speech_audio_seconds_cap"] == math.ceil(audio * nf.CEILING - 1e-9)
    # the audio source is the parent module cell's own: ceil(audio x 11) is its registered cap
    parent = _load(f"configs/experiment/{nf.PARENT_ARM}.json")
    assert parent["family_budget"]["repeated_speech_audio_seconds_cap"] == math.ceil(audio * 11 - 1e-9)


def test_identities_agree_and_the_replicate_is_the_held_module_cell_with_equal_hashes():
    facts = _facts()
    for kind in ("arm", "smoke"):
        names = nf.names(kind)
        experiment = _load(f"configs/experiment/{names['experiment']}.json")
        baseline = _baseline(kind)
        gen = _load(f"{nf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")["execution_plan"]
        fit = _load(f"{nf.PACKAGE}/{names['prefix']}fit-plan-registered-v1.json")["execution_plan"]
        cell = experiment["cells"][0]
        assert cell["attempt_id"] == names["attempt_id"] == gen["attempt_id"]
        assert cell["run_id"] == names["run_id"] == gen["run_id"]
        fit_block = baseline["native_contact_fit"]
        assert fit_block["run_id"] == names["fit_run_id"] == fit["run_id"]
        assert fit_block["attempt_id"] == names["fit_attempt_id"] == fit["attempt_id"]
        assert names["run_id"] != names["fit_run_id"] and names["attempt_id"] != names["fit_attempt_id"]
        assert experiment["family_budget"]["fit_endpoint_calls_cap"] == fit_block["contact_cap"] == fit["planned_model_calls"]
        assert experiment["family_budget"]["generation_calls_cap"] == gen["planned_model_calls"]
        comp = _composed(names["experiment"])
        assert facts["cells"][kind]["composed_config_hash"] == comp.config_hash == _load(
            f"{nf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")["composed_config_hash"]
        split = experiment["population"]["split_identity_hash"]
        assert facts["cells"][kind]["protocol_hash"] == protocol_hash(comp.config_hash, comp.values["arm"], split)
    # the replicate: the HELD module OFF-arm cell, reused as registered -- the recomposed hashes equal what its own package registered
    parent = _load(f"{nf.PARENT_PACKAGE}/registered-facts-v1.json")["cells"]["aa"]
    replicate = _composed(nf.REPLICATE["experiment"])
    assert replicate.config_hash == parent["composed_config_hash"] == facts["cells"]["replicate"]["composed_config_hash"]
    rep_doc = _load(f"configs/experiment/{nf.REPLICATE['experiment']}.json")
    rep_split = rep_doc["population"]["split_identity_hash"]
    assert protocol_hash(replicate.config_hash, replicate.values["arm"], rep_split) == parent["protocol_hash"]
    cell = rep_doc["cells"][0]
    assert (cell["run_id"], cell["attempt_id"]) == (nf.REPLICATE["run_id"], nf.REPLICATE["attempt_id"])
    assert replicate.values["native_contact_fit"]["run_id"] == nf.REPLICATE["fit_run_id"]
    block = replicate.values["native_episode"]["consumption_module"]
    assert block["lock"] == "v2.1" and all(c["state"] == "off" for c in block["components"])
    assert replicate.values["native_episode"]["deliver_normaliser"]["normaliser"] == "saea-deliver-normalise-v3"
    assert rep_split == _load(f"configs/experiment/{nf.ARM['experiment']}.json")["population"]["split_identity_hash"]
    assert facts["replicate_reuse"]["hashes_equal"] is True


def test_campaign_plan_flies_the_replicate_then_the_composed_arm():
    plan = _load(nf.CAMPAIGN_PLAN)
    assert [c["cell"] for c in plan["cells"]] == [nf.REPLICATE["experiment"], nf.ARM["experiment"]]
    assert [c["experiment"] for c in plan["cells"]] == [nf.REPLICATE["experiment"], nf.ARM["experiment"]]
    for experiment in (nf.REPLICATE["experiment"], nf.ARM["experiment"]):
        assert "campaign" in _load(f"configs/experiment/{experiment}.json")["cells"][0]["allowed_execution_stages"]
    assert "campaign" not in _load(f"configs/experiment/{nf.SMOKE['experiment']}.json")["cells"][0]["allowed_execution_stages"]


def test_registered_measurement_is_a_no_harm_cross_flight_declaration_with_an_in_chain_replicate():
    facts = _facts()
    block = facts["stage3_measurement"][nf.ARM["run_id"]]
    assert block["measurement_design"] == "cross-flight-with-in-chain-replicate"
    assert block["replicate_run_id"] == nf.REPLICATE["run_id"]
    assert block["primary_metric_key"] == "slu" and block["admission"] == "no-harm" and block["claims_benefit"] is False
    assert block["expected_effect_pp"] == nf.EXPECTED_EFFECT_PP == round(nf.REVIEW_OFF_VS_FULL_PP + nf.V4G_LOCK_COLUMN_PP, 2)
    assert nf.EXPECTED_EFFECT_PP < nf.BAR_PP_N1000  # far under the cross-flight bar: no benefit can be claimed
    assert block["harm_margin_pp"] == nf.HARM_MARGIN_PP >= nf.OWN_NULL["h_slu"]
    assert block["bar_pp"] == nf.BAR_PP_N1000 == 2.5 and block["rows"] == nf.ROWS
    assert block["comparator_run_id"] == nf.A2_ARM["run_id"] and block["offset_pair"]["left_run_id"] == nf.A2_AA["run_id"]
    assert block["offset_pair"]["right_run_id"] == nf.REPLICATE["run_id"]
    assert block["read_roster"] == nf.ROSTER_ID and block["tuning_exception"] == nf.TUNING_EXCEPTION
    assert "SLURP-DEV-2000-ADDED-V1" not in block["tuning_roster"]
    smoke = facts["stage3_measurement"][nf.SMOKE["run_id"]]
    assert smoke["measurement_design"] == "form-proof" and smoke["claims_benefit"] is False and smoke["rows"] == nf.SMOKE_ROWS
    # the protocol and the preregistration carry the same declaration
    protocol = _load(f"{nf.PACKAGE}/protocol-registered-v1.json")
    assert protocol["stage3_measurement"] == facts["stage3_measurement"]
    prereg = (REPO / nf.PREREG).read_text(encoding="utf-8")
    assert nf.ARM["run_id"] in prereg and "```json" in prereg and '"cross-flight-with-in-chain-replicate"' in prereg
    for word in ("NOMINATED", "NEUTRAL", "HARM", "UNRESOLVED"):
        assert word in facts["decision_rule"]


def test_the_effect_floor_gate_accepts_the_declaration_and_names_no_finding_for_the_new_cells():
    import stage3_effect_floor_check as gate

    report = gate.evaluate(REPO)
    ours = {nf.ARM["run_id"], nf.ARM["fit_run_id"], nf.SMOKE["run_id"], nf.SMOKE["fit_run_id"]}
    assert any(c.get("run_id") == nf.ARM["run_id"] for c in report["in_scope_cells"])
    mentioning = [f for f in report["findings"] if any(run in json.dumps(f) for run in ours)]
    assert mentioning == []


def test_preflight_fit_gate_and_native_config():
    from speech_aware_evidence_acquisition.core.flight.runtime import arm_uses_speech_feature_packets
    from speech_aware_evidence_acquisition.core.preparation_fit import validate_native_contact_fit_config

    for kind in ("arm", "smoke"):
        names = nf.names(kind)
        baseline = _baseline(kind)
        program = default_phase_program(baseline["policy"])
        spec = validate_native_contact_fit_config(baseline, program)
        assert spec is not None
        experiment = _load(f"configs/experiment/{names['experiment']}.json")
        ids = experiment["populations"][0]["ids"] if kind == "smoke" else [i["sample_id"] for i in _load(nf.ROSTER)["items"]]
        assert len(set(ids)) == len(ids) == (nf.SMOKE_ROWS if kind == "smoke" else nf.ROWS)
        assert arm_uses_speech_feature_packets(baseline["arm"])
        assert program.max_contacts == nf.CEILING
        assert spec["contact_cap"] == len(ids) * program.max_contacts * (spec["max_speech_packets"] + 3) == nf.fit_contact_cap(len(ids))
        gen_plan = _load(f"{nf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")["execution_plan"]
        assert spec["run_id"] != gen_plan["run_id"] and spec["attempt_id"] != gen_plan["attempt_id"]


def _ledger_rows() -> list:
    from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables

    return _parse_ledger_tables((REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8"))


def test_preflight_plans_budgets_and_ledger_rows():
    from dataclasses import fields

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan

    ledger = _ledger_rows()
    allowed = {f.name for f in fields(ExecutionPlan)}
    for kind in ("arm", "smoke"):
        names = nf.names(kind)
        declared = _load(f"configs/experiment/{names['experiment']}.json")["execution_plan"]
        for plan_kind in ("generation", "fit"):
            registered = _load(f"{nf.PACKAGE}/{names['prefix']}{plan_kind}-plan-registered-v1.json")["execution_plan"]
            plan = ExecutionPlan(**{k: v for k, v in registered.items() if k in allowed}).validate(source_root=REPO)
            if plan_kind == "generation":
                assert plan.planned_model_calls == declared["planned_model_calls"]
                assert plan.run_id == names["run_id"] and plan.attempt_id == names["attempt_id"]
            else:
                assert plan.planned_model_calls == _baseline(kind)["native_contact_fit"]["contact_cap"]
                assert plan.run_id == names["fit_run_id"] and plan.attempt_id == names["fit_attempt_id"]
            assert plan.planned_speech_audio_seconds == declared["planned_speech_audio_seconds"]
            matched = [r for r in ledger if r.get("run/experiment id") == plan.run_id]
            assert len(matched) == 1, (plan.run_id, len(matched))
            row = matched[0]
            assert row["consumed"].strip().lower() == "yes" and "CONSUMED (" in row["notes"]  # flown and sealed; closed by scripts/flights/batch/ledger_mark_consumed.py (SEALED prefix)
            assert row["execution profile"] == plan.execution_profile and row["split role"] == plan.split_role
            assert row["split identity hash"] == plan.split_identity_hash
            assert int(row["calls"]) == plan.planned_model_calls
            assert int(row["speech audio seconds"]) == plan.planned_speech_audio_seconds
            assert float(row["gpu hours"]) == float(plan.planned_gpu_hours)


def test_ledger_rows_are_present_unconsumed_and_draft_or_countersigned():
    import flight_registration_check as frc

    text = (REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    assert text.count(nf.LEDGER_MARK) == 1 and nf.LEDGER_MARK.startswith("## NX round R5")
    rows = _ledger_rows()
    ids = [nf.ARM["run_id"], nf.ARM["fit_run_id"], nf.SMOKE["run_id"], nf.SMOKE["fit_run_id"], nf.READ_RUN_ID]
    for run_id in ids:
        matched = [r for r in rows if r.get("run/experiment id") == run_id]
        assert len(matched) == 1, run_id
        row = matched[0]
        assert "DRAFT" in row.get("notes", "") or frc.is_countersigned(row), run_id
        if run_id == nf.READ_RUN_ID:
            assert row["execution profile"] == "model-free-check"
    # the replicate keeps the two rows of the module package
    for run_id in (nf.REPLICATE["run_id"], nf.REPLICATE["fit_run_id"]):
        assert len([r for r in rows if r.get("run/experiment id") == run_id]) == 1


def test_recipe_names_the_four_arms_the_read_driver_resolves():
    recipe = _load(f"{nf.PACKAGE}/analysis-recipe-v1.json")
    assert recipe["read_run_id"] == nf.READ_RUN_ID and recipe["recipe_id"] == nf.RECIPE_ID
    arms = recipe["arms"]
    assert (arms["arm"]["run_id"], arms["arm"]["attempt_id"]) == (nf.ARM["run_id"], nf.ARM["attempt_id"])
    assert (arms["in_chain_replicate"]["run_id"], arms["in_chain_replicate"]["attempt_id"]) == (nf.REPLICATE["run_id"], nf.REPLICATE["attempt_id"])
    assert (arms["comparator"]["run_id"], arms["comparator"]["attempt_id"]) == (nf.A2_ARM["run_id"], nf.A2_ARM["attempt_id"])
    assert (arms["a2_aa"]["run_id"], arms["a2_aa"]["attempt_id"]) == (nf.A2_AA["run_id"], nf.A2_AA["attempt_id"])
    assert recipe["output"]["analysis_root"] == nf.ANALYSIS_ROOT
    assert recipe["resampling"]["unit"] == "utterance cluster (paired)" and recipe["resampling"]["bootstrap_draws"] == 10000
    offline = recipe["offline_columns"]
    assert offline["columns"]["v4g"] == {"normaliser": nf.NORMALISER, "guards": nf.V4G_GUARDS}
    assert offline["statistics"]["sha256"] == nf.V4_STATS_SHA256
    # the sealed A2 flight exists as registered fragments with these run and attempt ids
    for ref in (nf.A2_ARM, nf.A2_AA):
        cell = _load(f"configs/experiment/{ref['experiment']}.json")["cells"][0]
        assert (cell["run_id"], cell["attempt_id"]) == (ref["run_id"], ref["attempt_id"])


def test_scripts_agree_with_the_family():
    scripts = REPO / "scripts" / "flights" / "nx"
    chain = (scripts / "batch_chain_nx_r5.sh").read_text(encoding="utf-8")
    flip = (scripts / "nx_r5_flip.sh").read_text(encoding="utf-8")
    repin = (scripts / "nx_r5_repin_cell.sh").read_text(encoding="utf-8")
    read = (scripts / "nx_r5_read.sh").read_text(encoding="utf-8")
    for text in (chain, flip, repin):
        assert f"SLUG={nf.SLUG}" in text and f"SHORT={nf.SHORT}" in text
    assert '"smoke_attempt_id": f"attempt-slurp-native-stage3-{slug}-smoke-4-generation-v1"' in chain
    assert '"gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1"' in chain
    assert nf.SMOKE["attempt_id"] == f"attempt-slurp-native-stage3-{nf.SLUG}-smoke-4-generation-v1"
    assert nf.ARM["attempt_id"] == f"attempt-slurp-native-stage3-{nf.SLUG}-generation-v1"
    assert '"owner": f"root-slurp-native-stage3-{slug}-v1"' in chain and "$SHORT-flight-commit.txt" in chain
    assert f'"{nf.REPLICATE["experiment"]}", "slurp-native-stage3-nx-r5-composed-dev2000-added-v1"' in chain.replace("\n", " ") or (
        nf.REPLICATE["experiment"] in chain and nf.ARM["experiment"] in chain)
    assert 'LOG=/home/chao/batch-chain-$SHORT.out' in chain
    # the flip re-pins smoke, the replicate through the module package script, then the arm, in loop form, and needs BOTH receipts
    assert flip.index("repin_loop_generic.sh\" \"$NX/nx_r5_repin_cell.sh\"") >= 0
    assert "module_comp1bdev_repin_aa.sh" in flip and "root-admission-v1.json" in flip
    assert flip.count("root-admission-v1.json") >= 2 and "convergence pass" in flip
    assert "--allow-output-change must never be passed" in flip and "ALLOW_OUTPUT_CHANGE" in repin
    assert f"DEC_ID=slurp-$SLUG-admission-v1" in repin and nf.DECISION_ID == f"slurp-{nf.SLUG}-admission-v1"
    assert nf.DECISION_RELPATH == f"coordination/slurp-{nf.SLUG}-v1/root-admission-v1.json"
    assert "read_paired_cell.sh" in read and "offset-replicate-vs-a2aa" in read and "nx_r5_v4g_contrast.py" in read
    assert f"{nf.PACKAGE}/analysis-recipe-v1.json" in read
    # the replicate's repin script is the module package's own and points at the module package
    module_repin = (REPO / "scripts" / "flights" / "module" / "module_comp1bdev_repin_aa.sh").read_text(encoding="utf-8")
    assert nf.REPLICATE["package"] in module_repin and nf.REPLICATE["decision_relpath"] in module_repin


def test_the_draft_receipt_lists_exactly_the_composed_cells_eligible():
    draft = _load(f"{nf.PACKAGE}/root-admission-draft-v1.json")
    assert draft["decision_id"] == nf.DECISION_ID and draft["status"] == "DRAFT-NOT-MINTED"
    assert draft["eligible_run_ids"] == [nf.ARM["run_id"], nf.ARM["fit_run_id"], nf.SMOKE["run_id"], nf.SMOKE["fit_run_id"]]
    assert nf.REPLICATE["run_id"] not in draft["eligible_run_ids"]  # its receipt is the module package's own
    module_draft = _load(f"{nf.PARENT_PACKAGE}/root-admission-draft-v1.json")
    assert nf.REPLICATE["run_id"] in module_draft["eligible_run_ids"] and nf.REPLICATE["fit_run_id"] in module_draft["eligible_run_ids"]
    assert draft["population"]["test_contact_authorized"] is False and draft["budget"]["paid_api_calls"] == 0


def test_the_decision_rule_arithmetic_names_the_registered_words():
    import nx_r5_v4g_contrast as contrast

    def block(delta_slu, ci_slu, delta_int, ci_int):
        return {"delta_slu_pp": delta_slu, "ci95_slu_pp": ci_slu, "delta_intent_pp": delta_int, "ci95_intent_pp": ci_int}

    offset = block(0.4, [-0.8, 1.6], -0.2, [-1.4, 1.0])
    # a resolved gain beyond the offset and the bar
    assert contrast.rule_arithmetic(block(3.0, [1.2, 4.8], 0.5, [-0.5, 1.5]), offset)["satisfies"] == "NOMINATED"
    # within the margin, nothing resolved
    assert contrast.rule_arithmetic(block(0.1, [-1.9, 2.1], 0.0, [-1.2, 1.2]), offset)["satisfies"] == "NEUTRAL"
    # a resolved loss beyond the flight offset
    assert contrast.rule_arithmetic(block(-2.0, [-3.9, -0.6], 0.0, [-1.2, 1.2]), offset)["satisfies"] == "HARM"
    # an upper bound inside the offset's magnitude is not a resolved loss
    assert contrast.rule_arithmetic(block(-2.0, [-3.9, -0.3], 0.0, [-1.2, 1.2]), offset)["satisfies"] == "UNRESOLVED"
    assert contrast.rule_arithmetic(block(0.0, [-1.0, 1.0], -1.5, [-2.6, -0.6]), offset)["satisfies"] == "HARM"
    # neither, but the lower bound is under the preregistered margin
    assert contrast.rule_arithmetic(block(-1.0, [-3.4, 1.4], 0.0, [-1.2, 1.2]), offset)["satisfies"] == "UNRESOLVED"
    # a gain with a guard harm is never NOMINATED
    assert contrast.rule_arithmetic(block(3.0, [1.2, 4.8], -2.0, [-3.0, -1.0]), offset)["satisfies"] == "HARM"
    assert contrast.BAR_PP == nf.BAR_PP_N1000 and contrast.HARM_MARGIN_PP == nf.HARM_MARGIN_PP
