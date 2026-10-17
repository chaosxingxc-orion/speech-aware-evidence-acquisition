"""NX-T R2: the per-node reasoning-budget column on the Thinking core, TRAIN Fold B (owner rulings 304/307, 313 A, 318 A; coordinator approval 2026-10-15).

Model-free and synthetic: the registered package, the derived fragments, the family constants, the cost model and the reader are checked against each other and
against the 268-B Thinking lock cell the column is derived from. No contact, no ledger write, no flip. The arm table is DATA (``nxt_r2_arms.json``): tests that
name a number of the DEFAULT table are guarded so that an edited table fails nothing but the guard.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "nx", REPO / "scripts" / "flights" / "direct", REPO / "scripts" / "flights" / "tfrl", REPO / "scripts" / "flights" / "lib",
               REPO / "scripts" / "analysis", REPO / "scripts" / "checks", REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import derive_tfrl_iteration_cells as dv  # noqa: E402
import nxt_r2_cost as cost  # noqa: E402
import nxt_r2_derive_cells as dc  # noqa: E402
import nxt_r2_family as fam  # noqa: E402
import slurp_nxt_thinking_budget_column_read as reader  # noqa: E402
import thinking_system_family as tsf  # noqa: E402

from speech_aware_evidence_acquisition.core import reasoning_knobs as rk  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.stage3_algorithms import validate_stage3_algorithm_label  # noqa: E402
from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402

PKG = REPO / fam.PACKAGE
DEFAULT_TABLE = [{"arm_id": "budget-1536", "perception": 1536, "solver": 1536}, {"arm_id": "budget-2048", "perception": 2048, "solver": 2048}]
IS_DEFAULT = fam.ARM_SPECS == DEFAULT_TABLE
default_only = pytest.mark.skipif(not IS_DEFAULT, reason="the arm table was edited: the number-of-the-default-table guards do not apply")


def js(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def baseline(key: str) -> dict:
    return js(f"configs/baseline/{fam.CELLS[key]['baseline']}.json")


def experiment(key: str) -> dict:
    return js(f"configs/experiment/{fam.CELLS[key]['cell']}.json")


def composed(key: str):
    spec = fam.CELLS[key]
    cell = experiment(key)["cells"][0]
    return compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], spec["cell"])


def table(*arms: dict) -> dict:
    return {"_note": "x", "arms": list(arms), "completion_cap": 4096, "delivering_budget_tokens": 3072, "schema": "saea-nxt-r2-arm-table-v1"}


# ---- ids and shape ----------------------------------------------------------------------------------------------------------------


def test_ids_are_unique_and_follow_the_registered_pattern():
    runs = [fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")]
    assert len(set(runs)) == 4
    # the arm cell is on its rec2 (owner ruling 328): the first-registration list, then the rec1 FIT run id, then the rec2 FIT run id
    assert set(fam.RECOVERIES) == {"arm"} and fam.recovery_index("arm") == 2 and fam.rec_suffix("arm") == "-rec2" and fam.recovery("smoke") is None
    assert fam.eligible_run_ids() == [fam.CELLS["smoke"]["run"], fam.CELLS["smoke"]["fit_run"], fam.CELLS["arm"]["run"],
                                      "SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-FIT-V1", "SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-FIT-REC1-V1",
                                      fam.CELLS["arm"]["fit_run"]]
    assert fam.CELLS["arm"]["run"] == "SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1"
    assert fam.CELLS["arm"]["fit_run"] == "SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-FIT-REC2-V1"
    assert fam.CELLS["arm"]["cell"] == "slurp-native-stage3-nxt-r2-thinking-budget-fold-b-v1"
    assert fam.CELLS["smoke"]["cell"] == "slurp-native-stage3-nxt-r2-thinking-budget-fold-b-smoke-4-v1"
    assert fam.CELLS["arm"]["attempt"] == "attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-rec2-v1"
    assert fam.CELLS["arm"]["fit_attempt"] == "attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-fit-rec2-v1"
    assert fam.PACKAGE == "docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1" and fam.SHORT == "nxt2"
    assert fam.READ_RUN_ID == "SAEA-SLURP-NXT-R2-THINKING-BUDGET-FOLD-B-READ-V1"
    for key in fam.ALL_KEYS:
        assert experiment(key)["cells"][0]["run_id"] == fam.CELLS[key]["run"]
        assert experiment(key)["cells"][0]["attempt_id"] == fam.CELLS[key]["attempt"]
        assert baseline(key)["native_contact_fit"]["run_id"] == fam.CELLS[key]["fit_run"]
        assert experiment(key)["cells"][0]["baseline_fragment"] == fam.CELLS[key]["baseline"]


def test_the_arm_table_is_data_and_the_default_matches_the_coordinators_brief():
    assert fam.ARM_SPECS == fam.load_arm_table() and fam.ARMS_PATH.name == "nxt_r2_arms.json"
    assert fam.DELIVERING == "budget-3072" == fam.ARM_ORDER[-1] and fam.TWIN is None
    assert len(fam.CANDIDATE_ARMS) <= fam.MAX_CANDIDATE_ARMS == 2
    assert fam.K == len(fam.CANDIDATE_ARMS) + 1 and fam.CONTACTS_PER_ROW == 2 + 2 * (fam.K - 1) and fam.PROGRAM == f"phase-native-module-v1-c{fam.CONTACTS_PER_ROW}"
    assert fam.COMPLETION_CAP == 4096 == tsf.THINK_MAX_TOKENS and fam.DELIVERING_BUDGET == 3072 == tsf.THINK_BUDGET_TOKENS
    assert "both-on-twin" not in json.dumps(baseline("arm")["native_episode"]["roles"]) and "replicate_of" not in json.dumps(baseline("arm")["native_episode"]["roles"])


@default_only
def test_the_default_table_is_two_budget_arms_and_c6():
    assert fam.ARM_ORDER == ("budget-1536", "budget-2048", "budget-3072")
    assert fam.POLICIES == {
        "budget-1536": {"perception": {"reasoning_budget_tokens": 1536, "answer_reserve_tokens": 2560}, "solver": {"reasoning_budget_tokens": 1536, "answer_reserve_tokens": 2560}},
        "budget-2048": {"perception": {"reasoning_budget_tokens": 2048, "answer_reserve_tokens": 2048}, "solver": {"reasoning_budget_tokens": 2048, "answer_reserve_tokens": 2048}},
    }
    assert fam.K == 3 and fam.CONTACTS_PER_ROW == 6 and fam.PROGRAM == "phase-native-module-v1-c6"
    assert fam.THINKING_CONTACTS_PER_ROW == 6 == fam.FALLBACK_CONTACTS_PER_ROW_CEILING


@pytest.mark.parametrize("bad, message", [
    (lambda t: t.update(extra=1), "must be exactly"),
    (lambda t: t.update(schema="x"), "schema must be"),
    (lambda t: t.update(completion_cap=8192), "never move"),
    (lambda t: t.update(delivering_budget_tokens=2048), "never move"),
    (lambda t: t.update(arms=[]), "between 1 and 2"),
    (lambda t: t.update(arms=[{"arm_id": f"a{i}", "perception": 1000 + i, "solver": 1000} for i in range(3)]), "between 1 and 2"),
    (lambda t: t["arms"][0].update(extra=1), "must be exactly"),
    (lambda t: t["arms"][0].update(arm_id="budget-3072"), "distinct lower-case id"),
    (lambda t: t["arms"][1].update(arm_id=t["arms"][0]["arm_id"]), "distinct lower-case id"),
    (lambda t: t["arms"][0].update(arm_id="Bad Id"), "distinct lower-case id"),
    (lambda t: t["arms"][0].update(perception=64), "reasoning budget in"),
    (lambda t: t["arms"][0].update(solver=3500), "reasoning budget in"),
    (lambda t: t["arms"][0].update(solver="on"), "reasoning budget in"),
    (lambda t: t["arms"][0].update(perception=True), "reasoning budget in"),
    (lambda t: t["arms"][0].update(perception=3072, solver=3072), "duplicate the delivering arm"),
    (lambda t: t["arms"][1].update(perception=1536, solver=1536), "repeats the setting"),
])
def test_the_arm_table_is_refused_by_name(bad, message):
    doc = table(*copy.deepcopy(DEFAULT_TABLE))
    bad(doc)
    with pytest.raises(fam.ArmTableError, match=message):
        fam.validate_arm_table(doc)


def test_node_policies_state_the_reserve_that_keeps_the_cap_and_off_is_the_r1_form():
    assert fam.node_policy(1536) == {"reasoning_budget_tokens": 1536, "answer_reserve_tokens": 2560}
    assert fam.node_policy(2048) == {"reasoning_budget_tokens": 2048, "answer_reserve_tokens": 2048}
    assert fam.node_policy(3072) is None and fam.node_policy("off") == {"enable_thinking": False}
    assert fam.policy_of({"arm_id": "x", "perception": 1536, "solver": 3072}) == {"perception": {"reasoning_budget_tokens": 1536, "answer_reserve_tokens": 2560}}
    assert fam.policy_of({"arm_id": "x", "perception": 3072, "solver": "off"}) == {"solver": {"enable_thinking": False}}
    base = {"temperature": 0, "seed": 20260913, "max_tokens": 4096, "thinking_budget_tokens": 3072, "chat_template_kwargs": {"enable_thinking": True}}
    for budget in (128, 1536, 2048, 3071, 3072):
        out = rk.resolve_node_decoding(base, {"solver": fam.node_policy(budget)}, "solver", cap=4096) if budget != 3072 else base
        assert out["max_tokens"] == 4096 and out["thinking_budget_tokens"] == budget
    off = rk.resolve_node_decoding(base, {"solver": fam.node_policy("off")}, "solver", cap=4096)
    assert "thinking_budget_tokens" not in off and off["max_tokens"] == 1024 and off["chat_template_kwargs"] == {"enable_thinking": False}


def test_one_node_scans_and_a_node_off_compile_and_the_ceiling_follows_the_table():
    hooks = carrier_module_hooks()
    from test_consumption_module_review_off import review_off_block

    def compile_table(*arms):
        block = review_off_block()
        block["columns"] = [{"column_id": a["arm_id"], "kind": "thinking", "node": "perception", "thinking_policy": fam.policy_of(a)} for a in arms]
        block["thinking_frame"] = {"max_supplied_items": 55, "twin": False, "fit_estimate": dict(fam.FIT_ESTIMATE), "delivering_arm_id": fam.DELIVERING}
        composed_ = cm.compile_module(block, hooks)
        arms_out = composed_.values()["native_episode"]["roles"]["perception"]["thinking_variants"]["arms"]
        return composed_, arms_out

    scan = [{"arm_id": "perception-1536", "perception": 1536, "solver": 3072}, {"arm_id": "solver-off", "perception": 3072, "solver": "off"}]
    composed_, arms = compile_table(*scan)
    assert (composed_.program_id, composed_.program_ceiling) == ("phase-native-module-v1-c6", 6)
    assert [a["arm_id"] for a in arms] == ["perception-1536", "solver-off", "budget-3072"]
    assert arms[0]["thinking_policy"] == {"perception": {"answer_reserve_tokens": 2560, "reasoning_budget_tokens": 1536}}
    assert arms[1]["thinking_policy"] == {"solver": {"enable_thinking": False}}
    composed_, arms = compile_table(scan[0])
    assert (composed_.program_id, composed_.program_ceiling) == ("phase-native-module-v1-c4", 4) and len(arms) == 2


# ---- the cells --------------------------------------------------------------------------------------------------------------------


def test_the_cells_carry_the_arm_table_with_the_delivering_arm_last_and_no_twin():
    for key in fam.ALL_KEYS:
        doc = baseline(key)
        assert doc["policy"] == fam.PROGRAM
        block = doc["native_episode"]["consumption_module"]
        assert block["lock"] == "v2.2" and block["review_loop"] == "off"
        assert [c["column_id"] for c in block["columns"]] == list(fam.CANDIDATE_ARMS) and all(c["kind"] == "thinking" for c in block["columns"])
        assert [c["thinking_policy"] for c in block["columns"]] == [fam.POLICIES[a] for a in fam.CANDIDATE_ARMS]
        assert block["thinking_frame"]["twin"] is False and block["thinking_frame"]["max_supplied_items"] == 55
        assert block["thinking_frame"]["delivering_arm_id"] == "budget-3072"
        arms = doc["native_episode"]["roles"]["perception"]["thinking_variants"]["arms"]
        assert [a["arm_id"] for a in arms] == list(fam.ARM_ORDER)
        assert arms[-1] == {"arm_id": "budget-3072", "deliver": True} and all("replicate_of" not in a for a in arms)
        assert [a["thinking_policy"] for a in arms[:-1]] == [fam.POLICIES[a] for a in fam.CANDIDATE_ARMS]
        assert "thinking_policy" not in doc                                     # the column is the ONLY per-node thinking mechanism
        assert "supply_variants" not in json.dumps(doc["native_episode"]["roles"]) and "template_variants" not in json.dumps(doc["native_episode"]["roles"])
        assert doc["native_episode"]["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert doc["native_episode"]["react_exhaustion_policy"] == "continue-without-answer"
        assert doc["native_episode"]["deliver_normaliser"]["normaliser"] == "saea-deliver-normalise-v4g"
        assert doc["preflight_budget_mode"] == "defer-to-native-contact-fit"


def test_the_composed_cell_loads_through_the_runtime_loader():
    for key in fam.ALL_KEYS:
        values = composed(key).values
        config = load_native_episode_config(values, default_phase_program(values["policy"]))
        group = config.perception_branch_group
        assert config.max_contacts == fam.CONTACTS_PER_ROW and group.is_thinking and group.level == 2 and group.branch_ids == fam.ARM_ORDER
        assert not group.has_twin and group.delivering_branch.branch_id == "budget-3072" and group.delivering_branch.thinking_policy is None
        assert values["decoding_params"]["max_tokens"] == 4096 and values["decoding_params"]["thinking_budget_tokens"] == 3072
        assert values["decoding_params"]["chat_template_kwargs"] == {"enable_thinking": True}
        assert values["reasoning_context_policy"] == "drop-reasoning-v1" and values["reasoning_content_guard"] == "refuse-think-marker-in-content"


def test_the_derive_proves_that_only_the_column_and_the_program_leaves_moved():
    parent = js(f"configs/baseline/{tsf.CELLS['lock']['baseline']}.json")
    mine = baseline("arm")
    left, right = dv._leaves(parent), dv._leaves(mine)
    missing = object()
    moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
    grouped, stray = dc.classify_moved(moved)
    assert stray == [] and set(grouped) == {name for name, _ in dc.MOVED_LEAF_RULES}
    assert grouped["the program id and ceiling"] == ["policy"] and grouped["the cell text"] == ["what_this_is"]
    assert all(leaf.startswith("native_episode.roles.perception.thinking_variants") for leaf in grouped["the thinking_variants block"])
    assert set(grouped["the live-fit ids and cap"]) == {"native_contact_fit.run_id", "native_contact_fit.attempt_id", "native_contact_fit.contact_cap"}
    # the strict rules refuse a leaf outside them
    assert dc.classify_moved(["native_episode.roles.solver.instruction"])[1] == ["native_episode.roles.solver.instruction"]
    assert dc.classify_moved(["native_episode.roles.perception.instruction"])[1] == ["native_episode.roles.perception.instruction"]
    for store in parent["knowledge_stores"]:
        assert mine["knowledge_stores"][store] == parent["knowledge_stores"][store]
    assert mine["phase_material"] == parent["phase_material"]
    assert mine["native_episode"]["deliver_normaliser"] == parent["native_episode"]["deliver_normaliser"]
    for role in ("solver", "reviewer", "planner"):
        assert mine["native_episode"]["roles"][role] == parent["native_episode"]["roles"][role]
    perception_mine = {k: v for k, v in mine["native_episode"]["roles"]["perception"].items() if k != "thinking_variants"}
    assert perception_mine == parent["native_episode"]["roles"]["perception"]
    assert mine["speech_packet_promotion_receipt"] == parent["speech_packet_promotion_receipt"] == fam.THINK_PROMOTION_RECEIPT
    assert mine["speech_packet_promotion_receipt_sha256"] == parent["speech_packet_promotion_receipt_sha256"] == fam.thinking_promotion_sha256()
    lock_values = compose(REPO, tsf.THINK_MODEL, tsf.DATASET, tsf.CELLS["lock"]["baseline"], tsf.CELLS["lock"]["cell"]).values
    mine_values = composed("arm").values
    assert mine_values["decoding_params"] == lock_values["decoding_params"] and mine_values["server_args"] == lock_values["server_args"]
    assert mine_values["reasoning_budget_tokens"] == lock_values["reasoning_budget_tokens"] == 3072


def test_experiments_swap_nothing_but_the_ids_and_keep_native_wire_metadata():
    for key in fam.ALL_KEYS:
        doc = experiment(key)
        cell = doc["cells"][0]
        assert cell["model_fragment"] == fam.THINK_MODEL and doc["service_session"] == fam.THINK_SESSION and doc["split_id"] == fam.SPLIT_ID
        assert doc["preserve_wire_responses"] is True and cell["readiness"]["state"] in ("held", "ready")
        assert validate_stage3_algorithm_label(doc["stage3_algorithm"], cell=fam.CELLS[key]["cell"])[0].id == "none"
        roster = json.loads((REPO / fam.ROSTER["smoke" if key == "smoke" else "arm"]).read_text(encoding="utf-8"))
        assert doc["populations"][0]["ids"] == [i["sample_id"] for i in roster["items"]]
        assert doc["population"]["split_identity_hash"] == roster["split_identity_hash"]
        assert "thinking-system" not in json.dumps(doc).lower().replace("nxt-r2-thinking-budget", "")
    assert len(experiment("arm")["populations"][0]["ids"]) == 1080 and len(experiment("smoke")["populations"][0]["ids"]) == 4


def test_derivation_is_reproducible_in_memory():
    derived = dc.derive(write=False)
    assert derived["program"] == fam.PROGRAM and derived["ceiling"] == fam.CONTACTS_PER_ROW
    for key in fam.ALL_KEYS:
        assert derived["cells"][key]["loader_verification"]["ok"] is True
        assert derived["cells"][key]["moved_by_rule"] and derived["cells"][key]["moved_leaves"]
        on_disk, in_memory = baseline(key), derived["_documents"][key]["baseline"]
        on_disk.pop("prepared_phase_supply", None)
        in_memory.pop("prepared_phase_supply", None)
        assert on_disk == in_memory


# ---- the delivering arm is the lock's request, byte for byte -----------------------------------------------------------------------------


def test_the_delivering_arm_resolves_to_the_lock_decoding_and_a_budget_arm_moves_only_the_budget():
    values = composed("arm").values
    base = dict(rk.fold_into_decoding(values)["decoding_params"]) if rk.fold_into_decoding(values) else dict(values["decoding_params"])
    for node in fam.NODES:
        assert rk.resolve_node_decoding(base, None, node, cap=4096) == base
        assert rk.resolve_node_decoding(base, {}, node, cap=4096) == base                       # the delivering arm declares no policy
        for arm in fam.CANDIDATE_ARMS:
            out = rk.resolve_node_decoding(base, fam.POLICIES[arm], node, cap=4096)
            budget = fam.SETTINGS[arm][fam.NODES.index(node)]
            if budget == fam.OFF:
                assert "thinking_budget_tokens" not in out and out["max_tokens"] == 1024
            elif budget == fam.DELIVERING_BUDGET:
                assert out == base
            else:
                assert out["thinking_budget_tokens"] == budget and out["max_tokens"] == 4096
                assert {k: v for k, v in out.items() if k != "thinking_budget_tokens"} == {k: v for k, v in base.items() if k != "thinking_budget_tokens"}


def test_the_delivering_arm_request_is_the_locked_plan_request_byte_for_byte(tmp_path):
    """Compose the 268-B lock request (no arm policy at all) and the delivering arm's request (an adapter that DOES carry the column's real policies) and compare
    bodies, payloads and prepared bytes minus the arm id; a candidate budget arm differs in the budget field only."""

    openjiuwen = pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")  # noqa: F841
    from test_thinking_policy_column import _adapter, _decoding, _request  # noqa: PLC0415

    policy = {arm: json.loads(json.dumps(fam.POLICIES[arm])) for arm in fam.CANDIDATE_ARMS}
    lock = _adapter(tmp_path / "lock", branch_policy=None)
    column = _adapter(tmp_path / "col", branch_policy=policy)
    for role in fam.NODES:
        reference = lock.prepare(_request(role, branch=None))
        armed = column.prepare(_request(role, branch=fam.DELIVERING))
        assert armed.rendered_body() == reference.rendered_body(), role
        assert armed.request.payload_bytes == reference.request.payload_bytes, role
        expected, actual = json.loads(reference.role_request_bytes), json.loads(armed.role_request_bytes)
        assert actual["context"].pop("perception_branch_id") == fam.DELIVERING
        assert actual == expected, role
        locked = _decoding(lock, role, branch=None)
        for arm in fam.CANDIDATE_ARMS:
            decoding = _decoding(column, role, branch=arm)
            setting = fam.SETTINGS[arm][fam.NODES.index(role)]
            if setting in (fam.OFF, fam.DELIVERING_BUDGET):
                continue
            assert decoding["thinking_budget_tokens"] == setting and decoding["max_tokens"] == 4096
            assert {k: v for k, v in decoding.items() if k != "thinking_budget_tokens"} == {k: v for k, v in locked.items() if k != "thinking_budget_tokens"}


# ---- budgets and the cost model ---------------------------------------------------------------------------------------------------


def test_the_cost_model_reproduces_the_delivering_arm_and_is_monotone_in_the_budget():
    model = fam.COST_MODEL
    assert model["r1_budget_tokens"] == 3072 and model["seconds_per_token"] > 0
    inputs = cost.load_inputs()
    assert inputs["source"]["sealed_trace_sha256"] and len(inputs["contacts"]) == 40 and all("text" not in c for c in inputs["contacts"])
    for node in fam.NODES:
        info = model["nodes"][node]
        think = [c for c in inputs["contacts"] if c["node"] == node and c["mode"] == "think"]
        assert info["think_contacts"] == len(think) == 12
        mean_tokens = sum(c["completion_tokens"] for c in think) / len(think)
        mean_seconds = sum(c["seconds"] for c in think) / len(think)
        assert abs(cost.tokens_at(model, node, 3072) - mean_tokens) < 1e-9                  # the delivering arm is reproduced exactly (clipping at 3,072 changes nothing)
        assert abs(cost.seconds_at(model, node, 3072) - mean_seconds) < 1e-9
        values = [cost.seconds_at(model, node, b) for b in (256, 1024, 1536, 2048, 3072)]
        assert values == sorted(values) and len(set(values)) == len(values)
        assert cost.seconds_at(model, node, "off") < cost.seconds_at(model, node, 256)
    with pytest.raises(ValueError, match="right-censored"):
        cost.tokens_at(model, "solver", 3073)
    # the clipped model is never below the linear-in-budget guess it replaces (the guess under-states a lower budget)
    for b in (1024, 1536, 2048):
        assert cost.relative_cost(model, b, b) >= cost.linear_reference(model, b, b) - 1e-9
    assert cost.relative_cost(model, 3072, 3072) == 1.0
    assert cost.ceil_hundredth(0.6545) == 0.66 and cost.ceil_hundredth(0.66) == 0.66 and cost.ceil_hundredth(0.7999) == 0.8


def test_registered_costs_ceiling_and_plans_follow_from_the_cost_model():
    model = fam.COST_MODEL
    for arm in fam.CANDIDATE_ARMS:
        assert fam.ROW_COST[arm] == cost.ceil_hundredth(cost.relative_cost(model, *fam.SETTINGS[arm]))
        assert fam.ROW_COST[arm] >= cost.relative_cost(model, *fam.SETTINGS[arm]) - 1e-12 and fam.ROW_COST[arm] < 1.0
    assert fam.ROW_COST[fam.DELIVERING] == 1.0 and fam.ARM_MIX_ROWS == round(sum(fam.ROW_COST.values()), 2)
    arm = fam.CELLS["arm"]
    expected = 1080 * fam.ARM_MIX_ROWS / 1.84 / 60
    assert abs(fam.expected_gpu_hours(1080) - expected) < 1e-9
    assert arm["gpu_hours"] == fam.planned_gpu_hours(1080) == round(math.ceil(round(expected * 1.3 / 0.1, 9)) * 0.1, 1)
    assert fam.CELLS["smoke"]["gpu_hours"] == 0.5
    rows, c, f = 1080, fam.CONTACTS_PER_ROW, fam.FALLBACK_CONTACTS_PER_ROW_CEILING
    spent_calls, spent_audio = fam.predecessor_spend("arm")                       # rec2: both earlier attempts' realised spend (run-cumulative)
    assert fam.original_generation_calls("arm") == rows * (c + f) and fam.generation_calls("arm") == rows * (c + f) + spent_calls and fam.program_calls("arm") == rows * c
    assert fam.fit_contact_cap(1080) == rows * c * tsf.tf.FIT_ENDPOINTS_PER_CONTACT and fam.fit_contact_cap(4) == 4 * c * tsf.tf.FIT_ENDPOINTS_PER_CONTACT
    assert fam.audio_cap("arm") == math.ceil(fam.roster_audio("arm") * (c + f) - 1e-9) and fam.cell_audio_cap("arm") == math.ceil(fam.audio_cap("arm") + spent_audio - 1e-9)
    assert rows * (c + 2) <= fam.generation_calls("arm")          # the runner's own plan check
    for key in fam.ALL_KEYS:
        spec = fam.CELLS[key]
        family, plan = dc.budgets(key)
        assert family["generation_calls_cap"] == plan["planned_model_calls"] == fam.generation_calls(key)
        assert family["fit_endpoint_calls_cap"] == fam.fit_contact_cap(spec["rows"]) == baseline(key)["native_contact_fit"]["contact_cap"]
        assert family["gpu_hours_fit_inclusive"] == plan["planned_gpu_hours"] == spec["gpu_hours"]
        assert experiment(key)["execution_plan"] == plan and experiment(key)["family_budget"] == family


@default_only
def test_the_default_table_ceiling_is_the_registered_one():
    assert fam.ROW_COST == {"budget-1536": 0.66, "budget-2048": 0.8, "budget-3072": 1.0} and fam.ARM_MIX_ROWS == 2.46
    assert round(fam.expected_gpu_hours(1080), 2) == 24.07 and fam.CELLS["arm"]["gpu_hours"] == 31.3
    assert fam.program_calls("arm") == 6480 and fam.original_generation_calls("arm") == 12960 and fam.generation_calls("smoke") == 48
    assert round(fam.lock_flight_gpu_hours("budget-1536"), 2) == 6.46 and round(fam.lock_flight_gpu_hours("budget-3072"), 2) == 9.78


def test_projected_lock_flight_follows_the_cost():
    assert abs(fam.arm_row_equivalent_rows_per_minute(fam.DELIVERING) - 1.84) < 1e-9
    for arm in fam.CANDIDATE_ARMS:
        assert abs(fam.arm_row_equivalent_rows_per_minute(arm) - 1.84 / fam.ROW_COST[arm]) < 1e-9
        assert fam.lock_flight_gpu_hours(arm) < fam.lock_flight_gpu_hours(fam.DELIVERING)


# ---- the package ------------------------------------------------------------------------------------------------------------------


def test_stage3_measurement_blocks():
    facts = json.loads((PKG / "registered-facts-v1.json").read_text(encoding="utf-8"))
    blocks = facts["stage3_measurement"]
    arm, smoke = fam.CELLS["arm"]["run"], fam.CELLS["smoke"]["run"]
    assert set(blocks) == {arm, smoke}
    b = blocks[arm]
    assert b["measurement_design"] == "same-flight-node-column" and b["claims_benefit"] is False and b["claim"] == "nominated"
    assert b["primary_metric_key"] == "slu" and b["rows"] == 1080 and b["tuning_roster"] == "none" and b["read_roster"] == fam.READ_ROSTER
    assert "aa_arm_id" not in b                                       # no twin (owner decision 313 A)
    assert b["template_variants"] == {"node": "perception", "candidate_arms": len(fam.CANDIDATE_ARMS), "twin": False} and b["variant_kind"] == "thinking-budget"
    assert b["variant_cost"]["extra_contacts_per_row"] == fam.CONTACTS_PER_ROW - 2 and b["variant_cost"]["extra_audio_seconds"] > 0
    assert str(fam.DECLARED_OFFSET_SLU_PP) in b["note"] and str(fam.PAIRED_FLOOR_PP) in b["note"]
    assert blocks[smoke]["measurement_design"] == "form-proof" and blocks[smoke]["claims_benefit"] is False
    assert facts["blockers"] == [] and {f["id"] for f in facts["findings"]} >= {"r1-answer-decides-the-arm-table", "no-twin-the-declared-offset-is-the-null",
                                                                              "cost-model-is-fitted-on-four-smoke-rows", "harness-addition-is-one-optional-frame-key"}
    ce = facts["accounting"]["cost_estimate"]
    assert ce["column_flight"]["planned_ceiling_gpu_hours"] == fam.CELLS["arm"]["gpu_hours"] and ce["arm_mix_rows"] == fam.ARM_MIX_ROWS
    assert [r["arm"] for r in ce["arm_table"]] == list(fam.ARM_ORDER) and ce["cost_model"]["seconds_per_token"] > 0
    assert facts["thinking_arms"]["budget-3072"] is None and facts["read_rule"]["declared_offset_slu_pp"] == 1.15 == fam.DECLARED_OFFSET_SLU_PP
    assert facts["read_rule"]["twin"] is None and facts["read_rule"]["word_order"] == list(reader.NODE_WORDS)


def test_the_effect_floor_gate_resolves_a_twinless_node_column(tmp_path):
    """The gate keys on the exposure ledger; the package's DRAFT rows are overlaid on a COPY (this repository's ledger is not touched). ``same-flight-node-column``
    with ``twin: false`` passes with no findings: the gate asks a twin only of the cross-flight designs."""

    ledger = tmp_path / "ledger.md"
    ledger.write_text((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8") + "\n" + (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8"),
                      encoding="utf-8")
    out = subprocess.run([sys.executable, "-B", str(REPO / "scripts/checks/stage3_effect_floor_check.py"), "--ledger", str(ledger), "--json"],
                         capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0, out.stderr[-500:]
    report = json.loads(out.stdout[out.stdout.find("{"):])
    mine = [c for c in report["in_scope_cells"] if "nxt-r2-thinking-budget" in c["cell_id"]]
    assert {c["cell_id"] for c in mine} == {fam.CELLS[k]["cell"] for k in fam.ALL_KEYS}
    assert not [f for f in report["findings"] if "nxt-r2-thinking-budget" in json.dumps(f)]
    declared = {c["cell_id"]: c["declaration"] for c in mine}
    column = declared[fam.CELLS["arm"]["cell"]]
    assert column["problems"] == [] and column["measurement_design"] == "same-flight-node-column" and column["claims_benefit"] is False


def test_plans_protocol_receipt_and_ledger_agree():
    protocol_sha = hashlib.sha256((PKG / "protocol-registered-v1.json").read_bytes()).hexdigest()
    draft_rows = (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8")
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    for key in fam.ALL_KEYS:
        for kind in ("generation", "fit"):
            assert fam.plan_file_name(key, kind) == (f"{fam.CELLS[key]['prefix']}{kind}-plan-registered{'-rec2' if key == 'arm' else ''}-v1.json")
            plan = json.loads((PKG / fam.plan_file_name(key, kind)).read_text(encoding="utf-8"))
            assert plan["expected_session_id"] == fam.THINK_SESSION and plan["protocol_document"]["sha256"] == protocol_sha
            assert plan["thinking_knobs"]["thinking_budget_tokens"] == 3072 and plan["execution_plan"]["split_role"] == "discovery"
            assert plan["arm_order"] == list(fam.ARM_ORDER) and plan["no_twin"] is True and ("recovery" in plan) == (key == "arm")
            assert plan["thinking_arms"][fam.CANDIDATE_ARMS[0]]["thinking_policy"] == fam.POLICIES[fam.CANDIDATE_ARMS[0]]
            assert plan["thinking_arms"][fam.DELIVERING]["thinking_policy"] is None
            run = fam.CELLS[key]["run" if kind == "generation" else "fit_run"]
            assert plan["execution_plan"]["run_id"] == run and plan["execution_plan"]["planned_gpu_hours"] == fam.CELLS[key]["gpu_hours"]
            assert plan["execution_plan"]["planned_model_calls"] == (fam.generation_calls(key) if kind == "generation" else fam.fit_contact_cap(fam.CELLS[key]["rows"]))
            assert draft_rows.count(f"| {run} |") == 1
            assert ledger.count(f"| {run} |") in (0, 1)          # DRAFT rows are appended (and later countersigned) by the coordinator, not by this package
    draft = json.loads((PKG / "root-admission-draft-v1.json").read_text(encoding="utf-8"))
    assert draft["eligible_run_ids"] == fam.eligible_run_ids() and draft["eligible_attempt_ids"] == fam.eligible_attempt_ids()
    assert draft["decision_id"] == fam.DECISION_ID and draft["status"] == "DRAFT-NOT-MINTED" and draft["service"]["expected_session_id"] == fam.THINK_SESSION
    assert "recovery" in draft and draft["budget"]["generation_calls_cap"] == fam.generation_calls("arm")
    texts = json.loads((PKG / "countersign-row-texts-v1.json").read_text(encoding="utf-8"))
    current = {fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")}
    assert set(texts["rows"]) == current | {fam.READ_RUN_ID} and draft_rows.count(f"| {fam.READ_RUN_ID} |") == 1
    assert len([ln for ln in draft_rows.splitlines() if ln.startswith("| 2026")]) == 5
    recipe = json.loads((PKG / "analysis-recipe-v1.json").read_text(encoding="utf-8"))
    assert recipe["read_run_id"] == fam.READ_RUN_ID and recipe["arms"] == list(fam.ARM_ORDER) and recipe["twin"] is None and recipe["delivering"] == fam.DELIVERING
    assert recipe["declared_offset"]["slu_pp"] == 1.15 and recipe["verdict_words"] == list(reader.NODE_WORDS)
    assert (REPO / fam.PREREG).is_file()
    for line in draft_rows.splitlines():
        if line.startswith("| 2026"):
            assert "DRAFT" in line and "root countersigned" not in line


def test_the_readme_names_the_rulings_the_cost_model_the_words_and_the_prerequisite():
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    for needle in ("313 A", "318 A", "think-budget-np4", "drop-reasoning-v1", "3072", "4096", "budget-3072", "independent chains", "no note sharing", "own Perception note",
                   "ceil_0.1", "GAIN", "NEEDS-FULL-BUDGET", "CHEAPER-AT-NO-RESOLVED-LOSS", "UNRESOLVED", "flip_package_ext4.sh", "saea-perception-branch-arms-v5",
                   "byte for byte", "THROUGHPUT", "R1's answer decides the arm table", "nxt_r2_arms.json", "|o| = 1.15", "0.7 pp", "nxt2-decode-signoff.marker",
                   "NXT2_KINDS", "no twin", "clipped-reasoning"):
        assert needle in readme, needle
    for script in ("nxt_r2_flip.sh", "nxt_r2_read.sh", "nxt_r2_repin_cell.sh", "batch_chain_nxt_r2.sh"):
        assert subprocess.run(["bash", "-n", str(REPO / "scripts/flights/nx" / script)], capture_output=True).returncode == 0
    assert str(fam.CELLS["arm"]["gpu_hours"]) in readme and str(fam.ARM_MIX_ROWS) in readme
    assert not re.search(r"[^\x00-\x7f]", readme)


def test_the_text_of_the_package_is_english():
    for path in [PKG / n for n in ("README.md", "draft-ledger-rows.md", "countersign-row-texts-v1.json", "registered-facts-v1.json", "protocol-registered-v1.json")]:
        assert not re.search(r"[^\x00-\x7f]", path.read_text(encoding="utf-8")), path
    nx = REPO / "scripts" / "flights" / "nx"
    for name in ("nxt_r2_family.py", "nxt_r2_cost.py", "nxt_r2_derive_cells.py", "nxt_r2_write_registration.py", "nxt_r2_mint_receipt.py", "nxt_r2_dry_run.py",
                 "nxt_r2_flip.sh", "nxt_r2_repin_cell.sh", "nxt_r2_read.sh", "batch_chain_nxt_r2.sh", "nxt_r2_arms.json", "nxt_r2_cost_inputs.json"):
        assert (nx / name).read_text(encoding="utf-8").isascii(), name
    assert (REPO / fam.READER).read_text(encoding="utf-8").isascii()
    assert (REPO / fam.PREREG).read_text(encoding="utf-8").isascii()


# ---- the reader -------------------------------------------------------------------------------------------------------------------


def _rows(ids, tp, fp, fn, intent):
    return {i: {"slu_f1_word_tp": tp[n], "slu_f1_char_tp": tp[n], "slu_f1_word_fp": fp[n], "slu_f1_char_fp": fp[n], "slu_f1_word_fn": fn[n],
                "slu_f1_char_fn": fn[n], reader.INTENT_FIELD: intent[n]} for n, i in enumerate(ids)}


def _arms(ids, loss_last_candidate=True):
    good = _rows(ids, [3.0] * len(ids), [1.0] * len(ids), [1.0] * len(ids), [1.0] * len(ids))
    bad = _rows(ids, [1.0] * len(ids), [3.0] * len(ids), [3.0] * len(ids), [0.0] * len(ids))
    arms = {arm: good for arm in fam.ARM_ORDER}
    if loss_last_candidate:
        arms[fam.CANDIDATE_ARMS[-1]] = bad
    return arms


def test_the_words_and_their_order_on_synthetic_contrasts():
    ci = lambda lo, hi: {"point_pp": (lo + hi) / 2, "ci95_lo_pp": lo, "ci95_hi_pp": hi}  # noqa: E731
    o = fam.DECLARED_OFFSET_SLU_PP
    assert (o, fam.FLOOR_SLU_PP, fam.FLOOR_INTENT_PP, fam.PAIRED_FLOOR_PP) == (1.15, 1.49, 0.65, 0.7)
    cases = [
        (ci(o + 0.01, 3.0), ci(-3, 3), "GAIN"),                                   # lower bound above +|o|, whatever the intent
        (ci(-3.0, -o - 0.01), ci(-0.1, 1.0), "NEEDS-FULL-BUDGET"),                 # upper bound below -|o|
        (ci(-1.49, 0.8), ci(-0.65, 1.0), "CHEAPER-AT-NO-RESOLVED-LOSS"),            # both floors met exactly
        (ci(-0.5, 0.5), ci(-0.3, 0.3), "CHEAPER-AT-NO-RESOLVED-LOSS"),
        (ci(-1.5, 0.8), ci(-0.1, 1.0), "UNRESOLVED"),                              # SLU lower bound under the floor, upper bound not under -|o|
        (ci(-0.5, 0.5), ci(-0.7, 0.3), "UNRESOLVED"),                              # intent lower bound under its floor
        (ci(-2.0, -0.5), ci(-0.1, 0.5), "UNRESOLVED"),
        (ci(-1.0, 1.15), ci(-0.1, 0.5), "CHEAPER-AT-NO-RESOLVED-LOSS"),            # +|o| exactly is not above it
        (ci(-3.0, -1.15), ci(-0.1, 0.5), "UNRESOLVED"),                            # -|o| exactly is not below it
    ]
    for slu, intent, word in cases:
        assert reader.classify(slu, intent) == word, (slu, intent, word)
    assert reader.NODE_WORDS == ("GAIN", "NEEDS-FULL-BUDGET", "CHEAPER-AT-NO-RESOLVED-LOSS", "UNRESOLVED")
    contrast = {"versus_delivering": {arm: {"slu_f1": ci(-0.5, 0.5), "intent": ci(-0.3, 0.3)} for arm in fam.CANDIDATE_ARMS}}
    words = reader.node_words(contrast)
    assert words["declared_offset_abs_pp"] == 1.15 and words["paired_floor_pp"] == 0.7 and words["external_reference_twin_offsets"]["268b_slu_pp"] == 1.15
    assert words["external_reference_twin_offsets"]["p31_slu_pp"] == -0.61 and set(words["words"]) == set(fam.CANDIDATE_ARMS)
    assert all(v["word"] == "CHEAPER-AT-NO-RESOLVED-LOSS" for v in words["words"].values())


def test_reader_paired_contrast_end_to_end_without_a_twin():
    ids = [f"r{n}" for n in range(40)]
    contrast = reader.paired_contrasts(_arms(ids), ids, lambda sid: sid, seed=1, draws=200)
    assert set(contrast["levels"]) == set(fam.ARM_ORDER) and fam.DELIVERING not in contrast["versus_delivering"]
    first, last = fam.CANDIDATE_ARMS[0], fam.CANDIDATE_ARMS[-1]
    assert contrast["versus_delivering"][first]["slu_f1"]["point_pp"] == 0.0
    words = reader.node_words(contrast)
    assert words["words"][last]["word"] == "NEEDS-FULL-BUDGET"
    if first != last:
        assert words["words"][first]["word"] == "CHEAPER-AT-NO-RESOLVED-LOSS"
    flat = reader.node_words(reader.paired_contrasts(_arms(ids, loss_last_candidate=False), ids, lambda sid: sid, seed=1, draws=200))
    assert all(v["word"] == "CHEAPER-AT-NO-RESOLVED-LOSS" for v in flat["words"].values())
    assert reader.SEED == 20261015 and reader.node_label(first).split("@")[0] in fam.NODES
    table_ = reader.per_scenario_table(_arms(ids), ids, lambda sid: "alarm" if int(sid[1:]) % 2 else "music")
    assert set(table_["scenarios"]) == {"alarm", "music"} and table_["natural_mixture"][f"slu_d_{last}_pp"] < 0


def _contact(agent, node, tokens, seconds, finish="stop", *, empty=False, reasoning=0, forced=False, marker=False):
    return {"agent_contact_id": agent, "role": node, "prompt_tokens": 3000, "completion_tokens": tokens, "latency_seconds": seconds, "finish_reason": finish,
            "empty_content": empty, "no_json_object": False, "marker_in_content": marker, "reasoning_chars": reasoning, "forced_close": forced}


def _receipt_rows():
    rows = []
    for sid in ("s1", "s2"):
        rows.append({"sample_id": sid, "native_episode_receipt": {"perception_branches": {"branches": [
            {"branch_id": arm, "contact_id": f"{sid}:{arm}:p", "solver_contact_id": f"{sid}:{arm}:s"} for arm in fam.ARM_ORDER]}}})
    return rows


def _synthetic_contacts(scale: float = 1.0, *, cap_hit: bool = False):
    """Two rows: a contact costs seconds proportional to its (budget-clipped) tokens; a forced close on the first row of every arm that has a budget below 3072."""

    contacts = []
    for sid in ("s1", "s2"):
        for arm in fam.ARM_ORDER:
            for node, suffix in (("perception", "p"), ("solver", "s")):
                budget = reader.BUDGET[arm][node]
                if budget is None:
                    contacts.append(_contact(f"{sid}:{arm}:{suffix}", node, 40, 2.0))
                    continue
                tokens = min(2600, budget) + 60
                contacts.append(_contact(f"{sid}:{arm}:{suffix}", node, 4096 if cap_hit else tokens, scale * tokens * 0.025, reasoning=5000,
                                         forced=sid == "s1" and budget < 2600, finish="length" if cap_hit else "stop"))
    return contacts


def test_reader_attributes_contacts_and_tabulates_nodes_forced_closes_and_the_throughput():
    mapping = reader.arm_contact_map(_receipt_rows())
    first = fam.CANDIDATE_ARMS[0]
    assert mapping[f"s1:{first}:p"] == (first, "perception") and mapping[f"s2:{fam.DELIVERING}:s"] == (fam.DELIVERING, "solver") and len(mapping) == 4 * fam.K
    contacts = _synthetic_contacts() + [_contact("stray", "perception", 10, 1.0)]
    by_arm = reader.attribute(contacts, mapping)
    assert set(by_arm) == set(fam.ARM_ORDER) | {"unattributed"} and len(by_arm[fam.DELIVERING]) == 4
    tables = reader.tables_by_arm(by_arm)
    t = tables[fam.DELIVERING]["perception"]
    assert t["mode"] == "think" and t["cap"] == 4096 and t["budget"] == 3072 and t["forced_closes"] == 0 and t["contacts"] == 2
    low = fam.CANDIDATE_ARMS[0]
    if reader.BUDGET[low]["perception"] not in (None, 3072):
        assert tables[low]["perception"]["forced_closes"] == 1 and tables[low]["perception"]["forced_close_share"] == 0.5
        assert tables[low]["perception"]["cap"] == 4096 and tables[low]["perception"]["budget"] == reader.BUDGET[low]["perception"]
    throughput = reader.throughput_table(tables, 1080)
    assert "unattributed" not in throughput["arms"] and throughput["arm_mix_registered_rows"] == fam.ARM_MIX_ROWS
    d = throughput["arms"][fam.DELIVERING]
    assert d["cost_in_delivering_rows"] == 1.0 and d["saving_vs_delivering"] == 0.0 and abs(d["gpu_hours_per_lock_flight"] - 1080 * d["seconds_per_row"] / 4 / 3600) < 1e-9
    assert abs(d["gpu_hours_per_lock_flight_at_reference_throughput"] - 1080 / 1.84 / 60) < 1e-9
    for arm in fam.CANDIDATE_ARMS:
        v = throughput["arms"][arm]
        assert v["gpu_hours_per_lock_flight"] < d["gpu_hours_per_lock_flight"] and 0 < v["saving_vs_delivering"] < 1
        assert abs(v["gpu_hours_per_lock_flight_at_reference_throughput"] - 1080 / (1.84 / v["cost_in_delivering_rows"]) / 60) < 1e-9
        assert v["registered_cost_in_rows"] == fam.ROW_COST[arm]
    assert abs(throughput["measured_gpu_hours_one_flight"] - sum(v["gpu_hours_per_lock_flight"] for v in throughput["arms"].values())) < 1e-9
    md = reader.render_markdown({"arms_nodes": tables, "throughput": throughput})
    assert "LOCK flight" in md and "GPU-h per lock flight" in md and "forced closes" in md


def test_smoke_signoff_conditions_are_booleans_the_coordinator_can_veto():
    mapping = reader.arm_contact_map(_receipt_rows())
    good = reader.smoke_stage(reader.attribute(_synthetic_contacts(), mapping))
    assert good["signoff"]["all_ok"] is True and set(good["signoff"]["conditions"]) == {
        "no_cap_hits_empty_or_malformed", "no_think_markers_in_content", "no_reasoning_bytes_on_a_no_think_node", "every_contact_attributed", "no_absent_columns", "mix_within_tolerance"}
    assert good["unattributed_contacts"] == 0 and good["contacts"] == reader.CONTACTS_ZERO and good["signoff"]["mix_tolerance"] == 1.3
    capped = reader.smoke_stage(reader.attribute(_synthetic_contacts(cap_hit=True), mapping))
    assert capped["signoff"]["conditions"]["no_cap_hits_empty_or_malformed"] is False and capped["signoff"]["all_ok"] is False
    marker = _synthetic_contacts()
    marker[0] = {**marker[0], "marker_in_content": True}
    assert reader.smoke_stage(reader.attribute(marker, mapping))["signoff"]["conditions"]["no_think_markers_in_content"] is False
    stray = reader.smoke_stage(reader.attribute(_synthetic_contacts() + [_contact("stray", "perception", 10, 1.0)], mapping))
    assert stray["unattributed_contacts"] == 1 and stray["signoff"]["conditions"]["every_contact_attributed"] is False
    tables = reader.tables_by_arm(reader.attribute(_synthetic_contacts(), mapping))
    over = {"mix_ratio_measured_over_registered": 1.31}
    assert reader.signoff_conditions(tables, over, 0)["conditions"]["mix_within_tolerance"] is False
    assert reader.signoff_conditions(tables, {"mix_ratio_measured_over_registered": 1.3}, 0)["conditions"]["mix_within_tolerance"] is True


def test_a_no_think_node_that_still_reasons_or_leaks_a_marker_is_visible():
    mapping = reader.arm_contact_map(_receipt_rows())
    arm = fam.CANDIDATE_ARMS[0]
    leaky = [_contact(f"s1:{arm}:p", "perception", 900, 20.0, finish="length", empty=True, reasoning=3000, marker=True)]
    saved = dict(reader.NO_THINK[arm])
    reader.NO_THINK[arm]["perception"] = True
    try:
        table_ = reader.arm_node_table(reader.attribute(leaky, mapping)[arm], arm)["perception"]
    finally:
        reader.NO_THINK[arm].update(saved)
    assert table_["mode"] == "no-think" and table_["cap_hits"] == 0 and table_["finish_reason_length"] == 1 and table_["empty_content"] == 1
    assert table_["contacts_with_reasoning_chars"] == 1 and table_["marker_in_content"] == 1


def test_the_reader_loads_only_ids_from_the_sealed_outputs(tmp_path):
    path = tmp_path / "outputs.jsonl"
    rows = [{"sample_id": "s1", "text": "SECRET ANSWER TEXT", "native_episode_receipt": {"perception_branches": {"branches": [
        {"branch_id": "budget-3072", "contact_id": "c1", "solver_contact_id": "c2", "thinking_policy": None, "note_sha256": "x" * 64}]}}}]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    loaded = reader.load_outputs_rows(path)
    assert "SECRET" not in json.dumps(loaded) and loaded[0]["native_episode_receipt"]["perception_branches"]["branches"][0]["contact_id"] == "c1"


def test_the_structural_dry_run_script_compiles_and_states_the_registered_node_decoding(tmp_path):
    import py_compile

    py_compile.compile(str(REPO / "scripts/flights/nx/nxt_r2_dry_run.py"), cfile=str(tmp_path / "nxt_r2_dry_run.pyc"), doraise=True)
    import nxt_r2_dry_run as dry

    on = lambda b: {"thinking_budget_tokens": b, "chat_template_kwargs": {"enable_thinking": True}, "max_tokens": 4096}  # noqa: E731
    assert dry.expected_node_decoding(fam.DELIVERING) == {"perception": on(3072), "solver": on(3072)}
    for arm in fam.CANDIDATE_ARMS:
        for node, setting in zip(fam.NODES, fam.SETTINGS[arm]):
            expected = dry.OFF if setting == fam.OFF else on(int(setting))
            assert dry.expected_node_decoding(arm)[node] == expected
    assert dry.OFF["max_tokens"] == 1024 and dry.OFF["thinking_budget_tokens"] is None
    # the expectation equals what the harness resolves for the composed cell (the dry run's own seam)
    values = composed("smoke").values
    folded = rk.fold_into_decoding(values) or values
    base = dict(folded["decoding_params"])
    for arm in fam.ARM_ORDER:
        for node in fam.NODES:
            resolved = rk.resolve_node_decoding(base, fam.POLICIES.get(arm) or {}, node)
            assert {k: resolved.get(k) for k in ("thinking_budget_tokens", "chat_template_kwargs", "max_tokens")} == dry.expected_node_decoding(arm)[node], (arm, node)


# ---- recovery: the generic lib is wired, EMPTY now, and the rec1 path is data-driven -----------------------------------------------------


def _snapshot() -> dict:
    first = lambda text: text.replace("-rec2-v1", "-v1").replace("-REC2-V1", "-V1")  # noqa: E731  (the snapshot of the FIRST attempt; the committed tree is on rec2)
    return {"schema": "saea-recovery-predecessor-snapshot-v1", "run_id": fam.CELLS["arm"]["run"], "attempt_id": first(fam.CELLS["arm"]["attempt"]), "state": "OPENED",
            "actual_calls": 700, "actual_audio_seconds": 1900.5, "reserved_calls": fam.generation_calls("arm"), "reserved_audio_seconds": float(fam.audio_cap("arm")),
            "fit": {"run_id": first(fam.CELLS["arm"]["fit_run"]), "attempt_id": first(fam.CELLS["arm"]["fit_attempt"]), "attempt_record_present": False, "prepared_dir_present": True,
                    "prepared_request_fit_envelopes": 700}}


def _recovery_input() -> dict:
    return {"recovered_at": "2026-10-20", "ledger_title": "the column flight re-registration", "agent": "the NX-T R2 recovery agent", "reason": "host restart",
            "root_cause": "infrastructure, not the cell", "fix": "none in the cell", "decision": "owner decision 309 A"}


def test_the_first_attempt_state_and_the_rec1_path_are_data_driven(monkeypatch, tmp_path):
    # the committed tree is on rec2 (tests/unit/test_nxt_r2_rec2.py); here the family is put back on its FIRST attempt, then rec1 is rebuilt from the two files' shape
    monkeypatch.setattr(fam, "RECOVERIES", {})
    monkeypatch.setattr(fam, "RECOVERY_HISTORY", {})
    assert fam.RECOVERIES == {} and fam.rcv.REC == "-rec1" and fam.recovery_index("arm") == 0
    assert fam.plan_file_name("arm", "generation") == "generation-plan-registered-v1.json" and fam.superseded_plan_file_names("arm") == []
    assert fam.predecessor_spend("arm") == (0, 0.0) and fam.cumulative_budget("arm", 100, 50.0) == (100, 50)
    first = {"smoke": fam._spec("smoke", "x", 4, "smoke", 0, 0.5, ids_stem=f"{fam.SLUG}-smoke-4", parent_key="smoke"),
             "arm": fam._spec("arm", "x", 1080, "arm", 1, 1.0, ids_stem=fam.SLUG, parent_key="lock")}
    assert first["arm"]["attempt"].endswith("generation-v1") and first["arm"]["fit_run"].endswith("-FIT-V1") and first["arm"]["fit_attempt"].endswith("-fit-v1")
    # build the record from the two committed files' shape and wire it through the family (no file in the real package is touched)
    root = tmp_path / "repo"
    (root / fam.PACKAGE).mkdir(parents=True)
    (root / fam.PREDECESSOR_SNAPSHOT["arm"]).write_text(json.dumps(_snapshot()), encoding="utf-8")
    (root / fam.RECOVERY_INPUT["arm"]).write_text(json.dumps(_recovery_input()), encoding="utf-8")
    loaded = fam._load_recoveries(root)
    assert set(loaded) == {"arm"} and loaded["arm"]["predecessors"][0]["contacts_spent"] == 700 and loaded["arm"]["recovery_index"] == 1
    fam.rcv.validate_recovery(loaded["arm"])
    assert set(fam._load_history(root)["arm"][0]) == set(loaded["arm"]) and len(fam._load_history(root)["arm"]) == 1
    assert fam._load_recoveries(tmp_path) == {}
    monkeypatch.setitem(fam.RECOVERIES, "arm", loaded["arm"])
    monkeypatch.setitem(fam.RECOVERY_HISTORY, "arm", [loaded["arm"]])
    assert fam.rec_suffix("arm") == "-rec1" and fam.rec_suffix("smoke") == "" and fam.recovery_index("arm") == 1
    assert fam.plan_file_name("arm", "generation") == "generation-plan-registered-rec1-v1.json" and fam.plan_file_name("smoke", "fit") == "smoke-fit-plan-registered-v1.json"
    assert fam.superseded_plan_file_names("arm") == ["generation-plan-registered-v1.json", "fit-plan-registered-v1.json"]
    assert fam.predecessor_spend("arm") == (700, 1900.5)
    assert fam.generation_calls("arm") == fam.original_generation_calls("arm") + 700 and fam.cell_audio_cap("arm") == fam.audio_cap("arm") + 1901
    rebuilt = {"smoke": fam._spec("smoke", "x", 4, "smoke", 0, 0.5, ids_stem=f"{fam.SLUG}-smoke-4", parent_key="smoke"),
               "arm": fam._spec("arm", "x", 1080, "arm", 1, 1.0, ids_stem=fam.SLUG, parent_key="lock")}
    spec = rebuilt["arm"]
    assert spec["attempt"].endswith("generation-rec1-v1") and spec["fit_run"].endswith("FIT-REC1-V1") and spec["run"] == first["arm"]["run"]
    assert spec["fit_attempt"].endswith("fit-rec1-v1")
    monkeypatch.setattr(fam, "CELLS", rebuilt)
    assert fam.eligible_run_ids() == [first["smoke"]["run"], first["smoke"]["fit_run"], first["arm"]["run"], first["arm"]["fit_run"], spec["fit_run"]]
    assert fam.eligible_attempt_ids() == [first["smoke"]["attempt"], first["smoke"]["fit_attempt"], first["arm"]["attempt"], first["arm"]["fit_attempt"], spec["attempt"],
                                          spec["fit_attempt"]]
    budget = fam.rcv.recovery_budget(fam.RECOVERIES, "arm", {"generation_calls_cap": fam.generation_calls("arm"),
                                                             "repeated_speech_audio_seconds_cap": fam.cell_audio_cap("arm")})
    assert budget["failed_attempt_spend"]["model_calls"] == 700 and budget["original_plan"]["planned_model_calls"] == fam.original_generation_calls("arm")


def test_a_recovery_input_missing_a_key_is_refused():
    bad = _recovery_input()
    bad.pop("root_cause")
    with pytest.raises(ValueError, match="root_cause"):
        fam.build_arm_recovery(bad, _snapshot())


def test_the_writer_recovery_text_and_ledger_are_wired(tmp_path):
    import nxt_r2_write_registration as writer

    ids = writer.identities(REPO)
    blocks = writer.recovery_blocks(REPO, ids, "x", "2026-10-20T00:00:00+00:00", "abc", "/wt", "br")
    assert set(blocks) == {"arm"} and blocks["arm"].lstrip().startswith("## Cell NXT-R2 recovery rec2: ")
    text = writer.recovery_sequence_text(ids)
    assert "Recovery rec2 sequence" in text and "NXT2_KINDS=arm" in text and "arm-only" in text and "--supersede" in text
    out = subprocess.run([sys.executable, "-B", str(REPO / "scripts/flights/nx/nxt_r2_write_registration.py"), "--help"], capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0
    for flag in ("--append-recovery-ledger", "--recovery-registered-at", "--recovery-base-commit", "--study-commit", "--append-ledger", "--registered-at", "--geometry"):
        assert flag in out.stdout


def test_the_mint_supersedes_only_the_first_registration_receipt(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    import nxt_r2_mint_receipt as mint

    first = fam.eligible_run_ids()
    longer = first + ["SAEA-X-FIT-NEXT-V1"]
    path = tmp_path / "root-admission-v1.json"
    path.write_text(json.dumps({"decision_id": fam.DECISION_ID, "eligible_run_ids": first}), encoding="utf-8")
    monkeypatch.setattr(fam, "eligible_run_ids", lambda: longer)
    assert mint.check_supersedable(str(path)) == first
    for bad in ({"decision_id": "other", "eligible_run_ids": first}, {"decision_id": fam.DECISION_ID, "eligible_run_ids": longer},
                {"decision_id": fam.DECISION_ID, "eligible_run_ids": list(reversed(first))}, {"decision_id": fam.DECISION_ID, "eligible_run_ids": []}):
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(SystemExit):
            mint.check_supersedable(str(path))
    stamp = datetime(2026, 10, 20, 17, 0, 5, tzinfo=timezone.utc)
    assert mint.backup_name("/d/root-admission-v1.json", stamp) == "/d/root-admission-v1.json.superseded-20261020T170005Z-by-rec2.bak"


def test_the_chain_flip_and_read_scripts_consume_the_family_record():
    nx = REPO / "scripts" / "flights" / "nx"
    chain, flip, read, repin = [(nx / n).read_text(encoding="utf-8") for n in ("batch_chain_nxt_r2.sh", "nxt_r2_flip.sh", "nxt_r2_read.sh", "nxt_r2_repin_cell.sh")]
    for script in ("batch_chain_nxt_r2.sh", "nxt_r2_flip.sh", "nxt_r2_read.sh", "nxt_r2_repin_cell.sh"):
        assert subprocess.run(["bash", "-n", str(nx / script)], capture_output=True).returncode == 0
    # smoke|arm|all|arm-only; the smoke must be sealed and the marker present for arm-only; all refuses to re-fly the smoke attempt; ids come from the family
    for needle in ("smoke) export BATCH_SESSION", "arm|arm-only)", "arm-only) run_driver arm", "use arm-only", "exit 9", '"$SMOKE_STATE" = sealed', "COMPLETED",
                   "no sign-off marker", "/home/chao/nxt2-decode-signoff.marker", "NXT2_SIGNOFF_WAIT_SECONDS", "nxt2-flight-commit.txt", "nxt_r2_family"):
        assert needle in chain, needle
    assert 'spec["attempt"]' in chain and "gen_attempt_id" in chain and "generation-v1" not in chain and "nxt_r1" not in chain and "nxt1" not in chain.replace("nxt2", "")
    assert "PLAN_REC=" in flip and "rec_suffix" in flip and 'NXT2_KINDS:-"smoke arm"' in flip and "nxt_r2_family" in flip and "nxt_r1" not in flip
    assert "generation-v1" not in read and "nxt_r2_family" in read and "SAEA-SLURP-NXT-R2-THINKING-BUDGET-FOLD-B-READ-V1" in read and "POLICY" not in read
    assert "NXT2_KIND" in repin and "nxt-r2-thinking-budget-fold-b" in repin and "2026-10-15" in repin
    assert "slurp_nxt_thinking_budget_column_read.py" in read and "perception-branches" in read
    assert subprocess.run([sys.executable, "-B", "-c", "import ast,sys; ast.parse(open(sys.argv[1]).read())", str(nx / "nxt_r2_dry_run.py")]).returncode == 0
