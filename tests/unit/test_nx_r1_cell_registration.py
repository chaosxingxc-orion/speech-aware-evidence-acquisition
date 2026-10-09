"""NX round R1: the registered cell is exactly what its package says it is (model-free).

Reads the committed fragments, candidate templates and package files. Proves: the declared module block compiles to the
fragments' policy blocks (the loader's own check), the program is the compiled review-off c8, the Solver template group has the
seven arms in order with the delivering lock last, every pinned template hashes to its file, the plan budgets are the ceiling
arithmetic, and the stage3_measurement block is a node column with a twin and the nominated ceiling.
"""

from __future__ import annotations

import hashlib
import json
import math
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
        assert fam["fit_endpoint_calls_cap"] == nf.fit_contact_cap(rows) == rows * nf.CEILING * 4  # structural, never x mult
        assert document["cells"][0]["readiness"]["state"] in ("held", "ready")
        assert document["stage3_algorithm"]["id"] == "none"
    assert nf.SMOKE_ATTEMPTS_BUDGETED == 2
    assert (smoke["execution_plan"]["planned_model_calls"], smoke["execution_plan"]["planned_speech_audio_seconds"],
            smoke["family_budget"]["fit_endpoint_calls_cap"]) == (64, 164, 128)
    assert smoke["family_budget"]["repeated_speech_audio_seconds_cap"] == 164
    assert smoke["family_budget"]["gpu_hours_fit_inclusive"] == 1.0
    assert (arm["execution_plan"]["planned_model_calls"], arm["execution_plan"]["planned_speech_audio_seconds"],
            arm["family_budget"]["fit_endpoint_calls_cap"]) == (8640, 25239, 34560)
    assert nf.SMOKE["attempt_id"].endswith("-generation-rec3-v1") and nf.SMOKE["fit_attempt_id"].endswith("-fit-rec3-v1")
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


# --- Pre-contact preflight: every model-free gate the worker applies before its first contact -------------------------
#
# Three consecutive smoke stops (failed seal, run-cumulative budget refusal, FIT cap refusal) were registration defects that a
# model-free test could have caught. These tests re-derive each refusal the worker raises BEFORE the first model contact, from
# committed config + roster only (no server), for BOTH registered cells:
#   * core/preparation_fit.py build_native_contact_fit_gate: distinct FIT run AND attempt identities; a unique registered
#     roster; contact_cap == rows x program.max_contacts x (max_speech_packets + 3) EXACTLY; validate_native_contact_fit_config
#     (the real validator, called with the real phase program).
#   * contracts.plan.ExecutionPlan.validate on the registered generation and FIT plans (profile, role, hashes, positive budget).
#   * contracts.gate_exposure._require_exposure_preregistration / runtime._require_exposure_row_unconsumed: exactly one ledger
#     row per run id, consumed = no, and profile / split role / split identity hash / calls / audio / gpu equal the plan.
#   * core/model/adapter.py run-cumulative budget: planned_model_calls and planned_speech_audio_seconds cover what earlier
#     attempts of the run id spent PLUS this attempt's worst case.
#   * one-time key: the attempt ids are fresh (not any recorded predecessor) and agree across the experiment fragment, the
#     baseline FIT block, the registered plans, the protocol document and the chain script.


def _load(relpath: str) -> dict:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _roster(kind: str) -> dict:
    return _load(nf.ROSTER[kind])


def _ledger_rows() -> list:
    from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables

    return _parse_ledger_tables((REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8"))


def _recovery_spend(kind: str) -> tuple:
    if kind != "smoke":
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
        # The real validator the gate calls first (stop rule, positive max_contacts, no conflicting fit modes).
        spec = validate_native_contact_fit_config(baseline, program)
        assert spec is not None
        roster = _roster(kind)
        ids = [item["sample_id"] for item in roster["items"]]
        # Unique registered sample roster (gate: "requires a unique registered sample roster").
        assert ids and all(isinstance(i, str) and i for i in ids) and len(set(ids)) == len(ids)
        rows = len(ids)
        assert rows == (4 if kind == "smoke" else nf.ROWS)
        # The gate's endpoints_per_contact formula (max_speech_packets + 3) applies on the feature-packet path.
        assert arm_uses_speech_feature_packets(baseline["arm"]), kind
        max_contacts = program.max_contacts  # the gate's own program.max_contacts, never hard-coded
        assert max_contacts == nf.CEILING
        required_cap = rows * max_contacts * (spec["max_speech_packets"] + 3)
        assert spec["contact_cap"] == required_cap == nf.fit_contact_cap(rows), (kind, spec["contact_cap"], required_cap)
        # Distinct run AND attempt identities (the gate refuses if EITHER equals the generation plan's).
        gen_plan = _load(f"{nf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")["execution_plan"]
        assert spec["run_id"] != gen_plan["run_id"]
        assert spec["attempt_id"] != gen_plan["attempt_id"]
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
        spent_calls, spent_audio, _ = _recovery_spend(kind)
        audio = sum(float(i["audio_seconds"]) for i in roster["items"])
        worst_calls = rows * max_contacts
        worst_audio = math.ceil(audio * max_contacts - 1e-9)
        declared = _load(f"configs/experiment/{names['experiment']}.json")["execution_plan"]
        # The adapter's run-cumulative call/audio budget: earlier attempts' spend plus this attempt's worst case.
        assert declared["planned_model_calls"] >= spent_calls + worst_calls, kind
        assert declared["planned_speech_audio_seconds"] >= spent_audio + worst_audio, kind
        for plan_kind in ("generation", "fit"):
            registered = _load(f"{nf.PACKAGE}/{names['prefix']}{plan_kind}-plan-registered-v1.json")["execution_plan"]
            plan = ExecutionPlan(**{k: v for k, v in registered.items() if k in allowed}).validate(source_root=REPO)
            if plan_kind == "generation":
                assert plan.planned_model_calls == declared["planned_model_calls"]
                assert plan.run_id == names["run_id"] and plan.attempt_id == names["attempt_id"]
            else:
                # The gate rewrites the FIT plan's planned_model_calls to the contact cap.
                assert plan.planned_model_calls == _baseline(kind)["native_contact_fit"]["contact_cap"]
                assert plan.run_id == names["fit_run_id"] and plan.attempt_id == names["fit_attempt_id"]
            assert plan.planned_speech_audio_seconds >= spent_audio + worst_audio
            # Exposure ledger: exactly one unconsumed row per run id, equal to the plan field by field.
            matched = [r for r in ledger if r.get("run/experiment id") == plan.run_id]
            assert len(matched) == 1, (plan.run_id, len(matched))
            row = matched[0]
            assert row["consumed"].strip().lower() == "no"
            assert row["execution profile"] == plan.execution_profile
            assert row["split role"] == plan.split_role
            assert row["split identity hash"] == plan.split_identity_hash == roster["split_identity_hash"]
            assert int(row["calls"]) == plan.planned_model_calls, (plan.run_id, row["calls"], plan.planned_model_calls)
            assert int(row["speech audio seconds"]) == plan.planned_speech_audio_seconds
            assert float(row["gpu hours"]) == float(plan.planned_gpu_hours)


def test_pre_contact_preflight_identities_agree_and_are_fresh():
    chain = (REPO / "scripts" / "flights" / "nx" / "batch_chain_nx_r1.sh").read_text(encoding="utf-8")
    for kind in ("arm", "smoke"):
        names = nf.names(kind)
        experiment = _load(f"configs/experiment/{names['experiment']}.json")
        baseline = _baseline(kind)
        protocol = _load(f"{nf.PACKAGE}/protocol-registered-v1.json")["cells"][kind]
        gen = _load(f"{nf.PACKAGE}/{names['prefix']}generation-plan-registered-v1.json")["execution_plan"]
        fit = _load(f"{nf.PACKAGE}/{names['prefix']}fit-plan-registered-v1.json")["execution_plan"]
        cell = experiment["cells"][0]
        # Every carrier of the attempt and run ids agrees.
        assert cell["attempt_id"] == names["attempt_id"] == gen["attempt_id"] == protocol["attempt_id"]
        fit_block = baseline["native_contact_fit"]
        assert fit_block["attempt_id"] == names["fit_attempt_id"] == fit["attempt_id"] == protocol["fit_attempt_id"]
        assert cell["run_id"] == names["run_id"] == gen["run_id"] == protocol["run_id"]
        assert fit_block["run_id"] == names["fit_run_id"] == fit["run_id"] == protocol["fit_run_id"]
        # The chain script drives the same generation attempt id (it spells the slug as a variable).
        key = "smoke_attempt_id" if kind == "smoke" else "gen_attempt_id"
        spelled = names["attempt_id"].replace(nf.SLUG, "{slug}")
        assert f'"{key}": f"{spelled}"' in chain, (kind, spelled)
        # FIT and generation identities are distinct on BOTH axes.
        assert names["run_id"] != names["fit_run_id"] and names["attempt_id"] != names["fit_attempt_id"]
        # Family caps: FIT is structural (== block cap == FIT plan calls); generation is the run-cumulative plan budget.
        fam = experiment["family_budget"]
        assert fam["fit_endpoint_calls_cap"] == fit_block["contact_cap"] == fit["planned_model_calls"]
        assert fam["generation_calls_cap"] == gen["planned_model_calls"]
        # One-time key: a recovery attempt id is never any recorded predecessor's.
        _, _, predecessors = _recovery_spend(kind)
        assert names["attempt_id"] not in predecessors
        assert names["fit_attempt_id"] not in {p.replace("-generation-", "-fit-") for p in predecessors}
    assert len(nf.SMOKE_RECOVERY["predecessors"]) == 3 and nf.SMOKE_PREDECESSOR_CONTACTS_SPENT == 32
    assert nf.SMOKE_RECOVERY["fit_cap_rule"].endswith("rows x max_contacts x (max_speech_packets + 3).")
