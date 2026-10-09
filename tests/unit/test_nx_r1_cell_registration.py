"""NX round R1: the registered cell is exactly what its package says it is (model-free).

Reads the committed fragments, candidate templates and package files. Proves: the declared module block compiles to the
fragments' policy blocks (the loader's own check), the program is the compiled review-off c8, the Solver template group has the
seven arms in order with the delivering lock last, every pinned template hashes to its file, the plan budgets are the ceiling
arithmetic, and the stage3_measurement block is a node column with a twin and the nominated ceiling.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "flights" / "nx"))
sys.path.insert(0, str(REPO / "scripts" / "checks"))

import nx_r1_family as nf  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402


def _baseline(kind: str) -> dict:
    return json.loads((REPO / "configs" / "baseline" / f"{nf.names(kind)['baseline']}.json").read_text(encoding="utf-8"))


def test_declared_module_block_verifies_and_the_program_is_the_review_off_c8():
    for kind in ("arm", "smoke"):
        document = _baseline(kind)
        block = document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
        cm.verify_declared_module(block, document, repo_root=REPO)
        assert document["policy"] == nf.PROGRAM == "phase-native-module-v1-c8"
        assert document["native_episode"]["review_loop"] == "off"
        assert document["native_episode"]["max_revisions"] == 0
        assert document["phase_tools"] == {}
        assert document["native_episode"]["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert document["native_episode"]["react_exhaustion_policy"] == "continue-without-answer"
        values = dict(document)
        values["carrier_lock_key"] = document.get("carrier_lock_key", "slurp")
        parsed = load_native_episode_config(values, default_phase_program(document["policy"]))
        assert parsed.max_contacts == nf.CEILING == 8
        assert not parsed.review_loop_enabled
        group = parsed.supply_variant_group
        assert group.is_template and group.arm_ids == nf.ARM_ORDER


def test_solver_template_arms_are_pinned_to_the_committed_candidate_files():
    document = _baseline("arm")
    arms = document["native_episode"]["roles"]["solver"]["template_variants"]["arms"]
    assert [a["arm_id"] for a in arms] == list(nf.ARM_ORDER)
    assert arms[-1].get("deliver") is True and "instruction_template" not in arms[-1]
    assert arms[-2] == {"arm_id": "aa", "replicate_of": "lock"}
    for arm in arms[: len(nf.ARMS)]:
        pin = arm["instruction_template"]
        assert hashlib.sha256((REPO / pin["relpath"]).read_bytes()).hexdigest() == pin["sha256"]
    assert hashlib.sha256((REPO / nf.LOCKED_TEMPLATE).read_bytes()).hexdigest() == nf.LOCKED_TEMPLATE_SHA
    assert document["phase_material"]["solver"]["instruction_template"] == "probes/slurp_native_role_solver_v2.txt"


def test_budgets_are_the_ceiling_arithmetic_and_the_fit_estimate_holds():
    arm = json.loads((REPO / "configs" / "experiment" / f"{nf.ARM['experiment']}.json").read_text(encoding="utf-8"))
    smoke = json.loads((REPO / "configs" / "experiment" / f"{nf.SMOKE['experiment']}.json").read_text(encoding="utf-8"))
    # The model adapter enforces planned_model_calls / planned_speech_audio_seconds run-cumulatively across the attempts
    # of a run id, so the smoke budget covers the failed first attempt plus the recovery (SMOKE_ATTEMPTS_BUDGETED = 2).
    for document, rows, mult in ((arm, 1080, 1), (smoke, 4, nf.SMOKE_ATTEMPTS_BUDGETED)):
        fam = document["family_budget"]
        assert fam["generation_calls_cap"] == rows * nf.CEILING * mult == document["execution_plan"]["planned_model_calls"]
        assert fam["native_task_contract_calls_cap"] == rows * nf.CEILING * mult
        assert fam["fit_endpoint_calls_cap"] == rows * nf.CEILING * 4 * mult
        assert document["cells"][0]["readiness"]["state"] in ("held", "ready")
        assert document["stage3_algorithm"]["id"] == "none"
    assert nf.SMOKE_ATTEMPTS_BUDGETED == 2
    assert (smoke["execution_plan"]["planned_model_calls"], smoke["execution_plan"]["planned_speech_audio_seconds"],
            smoke["family_budget"]["fit_endpoint_calls_cap"]) == (64, 164, 256)
    assert smoke["family_budget"]["repeated_speech_audio_seconds_cap"] == 164
    assert smoke["family_budget"]["gpu_hours_fit_inclusive"] == 1.0
    assert (arm["execution_plan"]["planned_model_calls"], arm["execution_plan"]["planned_speech_audio_seconds"],
            arm["family_budget"]["fit_endpoint_calls_cap"]) == (8640, 25239, 34560)
    assert nf.SMOKE["attempt_id"].endswith("-generation-rec2-v1") and nf.SMOKE["fit_attempt_id"].endswith("-fit-rec2-v1")
    assert nf.ARM["attempt_id"].endswith("-generation-v1") and nf.ARM["fit_attempt_id"].endswith("-fit-v1")
    measure = nf.fit_measure()
    limit = measure["prompt_limit_tokens"]
    assert max(measure["arm_prompt_estimates"].values()) <= limit


def test_registered_measurement_block_is_a_node_column_with_a_twin_and_the_nominated_ceiling():
    facts = json.loads((REPO / nf.PACKAGE / "registered-facts-v1.json").read_text(encoding="utf-8"))
    block = facts["stage3_measurement"][nf.ARM["run_id"]]
    assert block["measurement_design"] == "same-flight-node-column"
    assert block["aa_arm_id"] == "aa" and block["claim"] == "nominated"
    assert block["primary_metric_key"] == "slu" and block["claims_benefit"] is True
    assert block["expected_effect_pp"] == nf.EXPECTED_EFFECT_PP >= nf.FLOOR_SLU_PP
    assert block["template_variants"] == {"node": "solver", "candidate_arms": 5, "twin": True}
    assert block["variant_cost"]["extra_contacts_per_row"] == nf.CEILING - 2
    smoke = facts["stage3_measurement"][nf.SMOKE["run_id"]]
    assert smoke["measurement_design"] == "form-proof" and smoke["claims_benefit"] is False
    recipe = json.loads((REPO / nf.PACKAGE / "analysis-recipe-v1.json").read_text(encoding="utf-8"))
    assert recipe["read_run_id"] == nf.READ_RUN_ID
    assert recipe["offline_columns"]["columns"]["v4g"]["guards"] == nf.V4G_GUARDS
    assert recipe["offline_columns"]["statistics"]["sha256"] == nf.V4_STATS_SHA256
