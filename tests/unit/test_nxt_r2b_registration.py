"""NX-T R2b: the Solver reasoning-budget raise on the Thinking core, TRAIN Fold B (owner rulings 323 and 325 A of 2026-10-17; one candidate arm).

Model-free and synthetic: the registered package, the derived fragments, the family constants, the cost arithmetic, the fit proof, the serving wiring, the chain /
queue-hook / launch-spec scripts and the reader are checked against each other and against the 268-B Thinking lock cell the column is derived from. No contact, no
ledger write, no flip. The arm table is DATA (``nxt_r2b_arms.json``): the tests that name a number of the registered table are guarded so that an edited table fails
nothing but the guard. NX-T R2's own files are untouched (``test_nxt_r2_registration.py`` keeps passing).
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "nx", REPO / "scripts" / "flights" / "direct", REPO / "scripts" / "flights" / "tfrl", REPO / "scripts" / "flights" / "lib",
               REPO / "scripts" / "flights" / "batch", REPO / "scripts" / "analysis", REPO / "scripts" / "checks", REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import derive_tfrl_iteration_cells as dv  # noqa: E402
import nxt_r2b_derive_cells as dc  # noqa: E402
import nxt_r2b_family as fam  # noqa: E402
import slurp_nxt_r2b_solver_budget_column_read as reader_entry  # noqa: E402
import smoke_signoff  # noqa: E402
import thinking_system_family as tsf  # noqa: E402

from speech_aware_evidence_acquisition.core import reasoning_knobs as rk  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.stage3_algorithms import validate_stage3_algorithm_label  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402

reader = reader_entry.load()                       # the NX-T R2 reader module, loaded with the R2b family selected
NX = REPO / "scripts" / "flights" / "nx"
PKG = REPO / fam.PACKAGE
REGISTERED_TABLE = [{"arm_id": "solver-6144", "perception": {"budget_tokens": 3072, "completion_cap": 4096}, "solver": {"budget_tokens": 6144, "completion_cap": 7168}}]
IS_REGISTERED = fam.ARM_SPECS == REGISTERED_TABLE and fam.FRAGMENT_CAP == 7168
registered_only = pytest.mark.skipif(not IS_REGISTERED, reason="the arm table was edited: the number-of-the-registered-table guards do not apply")
LOCK = fam.DELIVERING_SETTING


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


def table(*arms: dict, **over) -> dict:
    doc = {"_note": "x", "answer_reserve_floor_tokens": 1024, "arms": list(arms), "delivering": {"budget_tokens": 3072, "completion_cap": 4096},
           "fragment_completion_cap": 7168, "schema": "saea-nxt-r2b-arm-table-v1"}
    doc.update(over)
    return doc


def node(budget: int, cap: int) -> dict:
    return {"budget_tokens": budget, "completion_cap": cap}


def arm(arm_id: str = "solver-6144", perception=None, solver=None) -> dict:
    return {"arm_id": arm_id, "perception": perception or node(3072, 4096), "solver": solver or node(6144, 7168)}


def family_variant(tmp_path: Path, doc: dict):
    """A second copy of the family module evaluated against a different arm table (the file under test is unchanged)."""

    path = tmp_path / "arms.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    source = (NX / "nxt_r2b_family.py").read_text(encoding="utf-8")
    needle = 'ARMS_PATH = HERE / "nxt_r2b_arms.json"'
    assert needle in source
    module = types.ModuleType("nxt_r2b_family_variant")
    module.__file__ = str(NX / "nxt_r2b_family.py")
    exec(compile(source.replace(needle, f"ARMS_PATH = Path({str(path)!r})"), module.__file__, "exec"), module.__dict__)  # noqa: S102
    return module


# ---- ids and shape ----------------------------------------------------------------------------------------------------------------


def test_ids_are_unique_and_follow_the_registered_pattern():
    runs = [fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")]
    assert len(set(runs)) == 4
    assert fam.RECOVERIES == {} and fam.recovery("arm") is None and fam.rec_suffix("arm") == ""
    assert fam.eligible_run_ids() == [fam.CELLS["smoke"]["run"], fam.CELLS["smoke"]["fit_run"], fam.CELLS["arm"]["run"], fam.CELLS["arm"]["fit_run"]]
    assert fam.CELLS["smoke"]["run"] == "SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-SMOKE-4-V1"
    assert fam.CELLS["smoke"]["fit_run"] == "SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-SMOKE-4-FIT-V1"
    assert fam.CELLS["arm"]["run"] == "SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1"
    assert fam.CELLS["arm"]["fit_run"] == "SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-FIT-V1"
    assert fam.CELLS["arm"]["cell"] == "slurp-native-stage3-nxt-r2b-solver-budget-fold-b-v1"
    assert fam.CELLS["smoke"]["cell"] == "slurp-native-stage3-nxt-r2b-solver-budget-fold-b-smoke-4-v1"
    assert fam.CELLS["arm"]["attempt"] == "attempt-slurp-native-stage3-nxt-r2b-solver-budget-fold-b-generation-v1"
    assert fam.CELLS["arm"]["fit_attempt"] == "attempt-slurp-native-stage3-nxt-r2b-solver-budget-fold-b-fit-v1"
    assert fam.PACKAGE == "docs/readiness/2026-10-17-slurp-nxt-r2b-solver-budget-fold-b-v1" and fam.SHORT == "nxt2b" and fam.PKG_NAME == "slurp-nxt-r2b-solver-budget-fold-b-v1"
    assert fam.READ_RUN_ID == "SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1"
    assert fam.SIGNOFF_CONDITIONS == f"{fam.PACKAGE}/signoff-conditions-v1.json"
    for key in fam.ALL_KEYS:
        assert experiment(key)["cells"][0]["run_id"] == fam.CELLS[key]["run"]
        assert experiment(key)["cells"][0]["attempt_id"] == fam.CELLS[key]["attempt"]
        assert baseline(key)["native_contact_fit"]["run_id"] == fam.CELLS[key]["fit_run"]
        assert experiment(key)["cells"][0]["baseline_fragment"] == fam.CELLS[key]["baseline"]


def test_the_r2_package_is_not_the_r2b_package():
    import nxt_r2_family as r2

    assert r2.PACKAGE != fam.PACKAGE and r2.SHORT == "nxt2" and r2.CELLS["arm"]["run"] != fam.CELLS["arm"]["run"] and r2.THINK_SESSION != fam.THINK_SESSION
    assert r2.ARMS_PATH.name == "nxt_r2_arms.json" and fam.ARMS_PATH.name == "nxt_r2b_arms.json"


def test_the_arm_table_is_data_and_the_registered_table_is_one_candidate_arm():
    assert fam.ARM_SPECS == fam.load_arm_table()[0] and fam.FRAGMENT_CAP == fam.load_arm_table()[1]
    assert fam.DELIVERING == "budget-3072" == fam.ARM_ORDER[-1] and fam.TWIN is None
    assert len(fam.CANDIDATE_ARMS) == 1 == fam.MAX_CANDIDATE_ARMS
    assert fam.K == len(fam.CANDIDATE_ARMS) + 1 and fam.CONTACTS_PER_ROW == 2 + 2 * (fam.K - 1) and fam.PROGRAM == f"phase-native-module-v1-c{fam.CONTACTS_PER_ROW}"
    assert fam.COMPLETION_CAP == 4096 == tsf.THINK_MAX_TOKENS and fam.DELIVERING_BUDGET == 3072 == tsf.THINK_BUDGET_TOKENS and fam.ANSWER_RESERVE_FLOOR == 1024
    roles = json.dumps(baseline("arm")["native_episode"]["roles"])
    assert "both-on-twin" not in roles and "replicate_of" not in roles


@registered_only
def test_the_registered_table_is_solver_6144_c4_and_the_wire_form_is_solver_only():
    assert fam.ARM_ORDER == ("solver-6144", "budget-3072") and fam.CANDIDATE_ARMS == ("solver-6144",)
    assert fam.POLICIES == {"solver-6144": {"solver": {"reasoning_budget_tokens": 6144, "answer_reserve_tokens": 1024}}}
    assert fam.K == 2 and fam.CONTACTS_PER_ROW == 4 and fam.PROGRAM == "phase-native-module-v1-c4"
    assert fam.THINKING_CONTACTS_PER_ROW == 4 == fam.FALLBACK_CONTACTS_PER_ROW_CEILING
    assert fam.NODE_BUDGETS == {"solver-6144": {"perception": 3072, "solver": 6144}, "budget-3072": {"perception": 3072, "solver": 3072}}
    assert fam.NODE_CAPS == {"solver-6144": {"perception": 4096, "solver": 7168}, "budget-3072": {"perception": 4096, "solver": 4096}}
    assert fam.FRAGMENT_CAP == 7168 == 6144 + 1024


@pytest.mark.parametrize("bad, message", [
    (lambda t: t.update(extra=1), "must be exactly"),
    (lambda t: t.update(schema="x"), "schema must be"),
    (lambda t: t.update(delivering={"budget_tokens": 3072, "completion_cap": 8192}), "never move"),
    (lambda t: t.update(delivering={"budget_tokens": 2048, "completion_cap": 4096}), "never move"),
    (lambda t: t.update(answer_reserve_floor_tokens=512), "answer_reserve_floor_tokens must be"),
    (lambda t: t.update(fragment_completion_cap=2048), "fragment_completion_cap must be an integer"),
    (lambda t: t.update(fragment_completion_cap=True), "fragment_completion_cap must be an integer"),
    (lambda t: t.update(fragment_completion_cap=8192), "must equal the largest node cap"),
    (lambda t: t.update(arms=[]), "between 1 and 1"),
    (lambda t: t.update(arms=[arm("a"), arm("b", solver=node(5000, 7168))]), "between 1 and 1"),
    (lambda t: t["arms"][0].update(extra=1), "must be exactly"),
    (lambda t: t["arms"][0].update(arm_id="budget-3072"), "distinct lower-case id"),
    (lambda t: t["arms"][0].update(arm_id="Bad Id"), "distinct lower-case id"),
    (lambda t: t["arms"][0].update(solver=node(6144, 7167)), "must be >= budget_tokens \\+ 1024"),
    (lambda t: t["arms"][0].update(solver=node(6145, 7168)), "must be >= budget_tokens \\+ 1024"),
    (lambda t: t["arms"][0].update(solver=node(7000, 7168)), "must be >= budget_tokens \\+ 1024"),
    (lambda t: t["arms"][0].update(solver=node(6144, 8192)), "exceeds the serving fragment's geometry cap"),
    (lambda t: t["arms"][0].update(solver=node(3072, 7168)), "keeps the delivering completion cap"),
    (lambda t: t["arms"][0].update(perception=node(2048, 5000)), "keeps the delivering completion cap"),
    (lambda t: t["arms"][0].update(solver=node(64, 4096)), "is below 128"),
    (lambda t: t["arms"][0].update(solver={"budget_tokens": 6144}), "must be exactly"),
    (lambda t: t["arms"][0].update(solver={"budget_tokens": "6144", "completion_cap": 7168}), "must be integers"),
    (lambda t: t["arms"][0].update(solver={"budget_tokens": True, "completion_cap": 7168}), "must be integers"),
    (lambda t: t["arms"][0].update(solver="off"), "must be exactly"),
    (lambda t: t["arms"][0].update(perception=node(3072, 4096), solver=node(3072, 4096)), "duplicate the delivering arm"),
])
def test_the_arm_table_is_refused_by_name(bad, message):
    doc = table(arm())
    bad(doc)
    with pytest.raises(fam.ArmTableError, match=message):
        fam.validate_arm_table(doc)


def test_a_budget_above_the_delivering_one_is_accepted_only_with_a_cap_that_leaves_the_answer_reserve():
    # exactly budget + 1024 is accepted; one token less is refused (the Solver and the Perception node alike)
    arms, cap = fam.validate_arm_table(table(arm(solver=node(6144, 7168))))
    assert cap == 7168 and arms[0]["solver"] == node(6144, 7168) and arms[0]["perception"] == LOCK
    with pytest.raises(fam.ArmTableError, match="must be >="):
        fam.validate_arm_table(table(arm(solver=node(6144, 7167))))
    arms, cap = fam.validate_arm_table(table(arm("p-up", perception=node(4096, 5120), solver=node(3072, 4096)), fragment_completion_cap=5120))
    assert cap == 5120 and arms[0]["perception"] == node(4096, 5120)
    with pytest.raises(fam.ArmTableError, match="must be >="):
        fam.validate_arm_table(table(arm("p-up", perception=node(4096, 5119), solver=node(3072, 4096)), fragment_completion_cap=5120))
    # a node below the delivering budget keeps the delivering cap, a lowered budget is a legal node setting of the validator (the cost model refuses it later)
    arms, _ = fam.validate_arm_table(table(arm("low", perception=node(2048, 4096), solver=node(3072, 4096)), fragment_completion_cap=4096))
    assert arms[0]["perception"] == node(2048, 4096)


def test_the_delivering_arm_is_unchanged_by_the_table():
    assert fam.DELIVERING_SETTING == node(3072, 4096) and fam.SETTINGS[fam.DELIVERING] == (LOCK, LOCK)
    assert fam.node_policy(LOCK) is None and fam.POLICIES.get(fam.DELIVERING) is None and fam.policy_of({"perception": LOCK, "solver": LOCK}) == {}
    assert fam.DELIVERING_NODE_POLICY == {"perception": {"reasoning_budget_tokens": 3072, "answer_reserve_tokens": 1024},
                                          "solver": {"reasoning_budget_tokens": 3072, "answer_reserve_tokens": 1024}}
    assert fam.NODE_BUDGETS[fam.DELIVERING] == {"perception": 3072, "solver": 3072} and fam.NODE_CAPS[fam.DELIVERING] == {"perception": 4096, "solver": 4096}


def test_node_policies_state_the_reserve_and_resolve_to_the_node_own_cap():
    assert fam.node_policy(node(6144, 7168)) == {"reasoning_budget_tokens": 6144, "answer_reserve_tokens": 1024}
    assert fam.node_policy(node(4096, 5120)) == {"reasoning_budget_tokens": 4096, "answer_reserve_tokens": 1024}
    assert fam.node_policy(node(2048, 4096)) == {"reasoning_budget_tokens": 2048, "answer_reserve_tokens": 2048}
    base = {"temperature": 0, "seed": 20260913, "max_tokens": 7168, "thinking_budget_tokens": 3072, "chat_template_kwargs": {"enable_thinking": True}}
    out = rk.resolve_node_decoding(base, {"solver": fam.node_policy(node(6144, 7168))}, "solver", cap=7168)
    assert out["thinking_budget_tokens"] == 6144 and out["max_tokens"] == 7168
    with pytest.raises(rk.ReasoningKnobError, match="exceeds the geometry cap"):
        rk.resolve_node_decoding(base, {"solver": fam.node_policy(node(6144, 7168))}, "solver", cap=4096)


# ---- the cells --------------------------------------------------------------------------------------------------------------------


def test_the_cells_carry_the_arm_table_the_cell_level_policy_and_the_delivering_arm_last():
    for key in fam.ALL_KEYS:
        doc = baseline(key)
        assert doc["policy"] == fam.PROGRAM
        block = doc["native_episode"]["consumption_module"]
        assert block["lock"] == "v2.2" and block["review_loop"] == "off"
        assert [c["column_id"] for c in block["columns"]] == list(fam.CANDIDATE_ARMS) and all(c["kind"] == "thinking" for c in block["columns"])
        assert [c["thinking_policy"] for c in block["columns"]] == [fam.POLICIES[a] for a in fam.CANDIDATE_ARMS]
        frame = block["thinking_frame"]
        assert frame["twin"] is False and frame["max_supplied_items"] == fam.MAX_SUPPLIED_ITEMS and frame["delivering_arm_id"] == "budget-3072"
        assert frame["fit_estimate"] == fam.FIT_ESTIMATE and frame["fit_estimate"]["completion_ceiling"] == fam.FRAGMENT_CAP
        arms = doc["native_episode"]["roles"]["perception"]["thinking_variants"]["arms"]
        assert [a["arm_id"] for a in arms] == list(fam.ARM_ORDER)
        assert arms[-1] == {"arm_id": "budget-3072", "deliver": True} and all("replicate_of" not in a for a in arms)
        assert [a["thinking_policy"] for a in arms[:-1]] == [fam.POLICIES[a] for a in fam.CANDIDATE_ARMS]
        assert doc["thinking_policy"] == fam.DELIVERING_NODE_POLICY              # the lock form on BOTH nodes, stated at the cell level
        assert "supply_variants" not in json.dumps(doc["native_episode"]["roles"]) and "template_variants" not in json.dumps(doc["native_episode"]["roles"])
        assert doc["native_episode"]["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert doc["native_episode"]["react_exhaustion_policy"] == "continue-without-answer"
        assert doc["native_episode"]["deliver_normaliser"]["normaliser"] == "saea-deliver-normalise-v4g"
        assert doc["preflight_budget_mode"] == "defer-to-native-contact-fit"
        assert doc["native_episode"]["context_fit_policy"] == "compact-or-abstain"


def test_the_composed_cell_loads_through_the_runtime_loader_on_the_raised_fragment():
    for key in fam.ALL_KEYS:
        values = composed(key).values
        config = load_native_episode_config(values, default_phase_program(values["policy"]))
        group = config.perception_branch_group
        assert config.max_contacts == fam.CONTACTS_PER_ROW and group.is_thinking and group.level == 2 and group.branch_ids == fam.ARM_ORDER
        assert not group.has_twin and group.delivering_branch.branch_id == "budget-3072" and group.delivering_branch.thinking_policy is None
        assert group.fit_estimate.completion_ceiling == fam.FRAGMENT_CAP and group.delivering_branch.max_supplied_items == fam.MAX_SUPPLIED_ITEMS
        assert values["decoding_params"]["max_tokens"] == fam.FRAGMENT_CAP and values["decoding_params"]["thinking_budget_tokens"] == 3072
        assert values["reasoning_budget_tokens"] == 3072 and values["answer_reserve_tokens"] == fam.FRAGMENT_CAP - 3072
        assert values["thinking_policy"] == fam.DELIVERING_NODE_POLICY
        assert values["decoding_params"]["chat_template_kwargs"] == {"enable_thinking": True}
        assert values["reasoning_context_policy"] == "drop-reasoning-v1" and values["reasoning_content_guard"] == "refuse-think-marker-in-content"
        assert values["server_args"][values["server_args"].index("-c") + 1] == "98304" and values["server_args"][values["server_args"].index("-np") + 1] == "4"


def test_the_derive_proves_that_only_the_column_the_cell_policy_and_the_program_leaves_moved():
    parent = js(f"configs/baseline/{tsf.CELLS['lock']['baseline']}.json")
    mine = baseline("arm")
    left, right = dv._leaves(parent), dv._leaves(mine)
    missing = object()
    moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
    grouped, stray = dc.classify_moved(moved)
    assert stray == [] and set(grouped) == {name for name, _ in dc.MOVED_LEAF_RULES}
    assert grouped["the program id and ceiling"] == ["policy"] and grouped["the cell text"] == ["what_this_is"]
    assert all(leaf.startswith("native_episode.roles.perception.thinking_variants") for leaf in grouped["the thinking_variants block"])
    assert set(grouped["the cell-level thinking policy (the lock form on both nodes)"]) == {
        f"thinking_policy.{n}.{k}" for n in fam.NODES for k in ("reasoning_budget_tokens", "answer_reserve_tokens")}
    assert set(grouped["the live-fit ids and cap"]) == {"native_contact_fit.run_id", "native_contact_fit.attempt_id", "native_contact_fit.contact_cap"}
    assert dc.classify_moved(["native_episode.roles.solver.instruction"])[1] == ["native_episode.roles.solver.instruction"]
    assert dc.classify_moved(["decoding_params.max_tokens"])[1] == ["decoding_params.max_tokens"]
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


def test_experiments_swap_nothing_but_the_ids_and_name_only_the_raised_session():
    for key in fam.ALL_KEYS:
        doc = experiment(key)
        cell = doc["cells"][0]
        assert cell["model_fragment"] == fam.THINK_MODEL and doc["service_session"] == fam.THINK_SESSION and doc["split_id"] == fam.SPLIT_ID
        assert fam.CONTROL_FRAGMENT not in json.dumps(doc) and tsf.THINK_SESSION not in json.dumps(doc)
        assert doc["preserve_wire_responses"] is True and cell["readiness"]["state"] in ("held", "ready")
        assert validate_stage3_algorithm_label(doc["stage3_algorithm"], cell=fam.CELLS[key]["cell"])[0].id == "none"
        roster = json.loads((REPO / fam.ROSTER["smoke" if key == "smoke" else "arm"]).read_text(encoding="utf-8"))
        assert doc["populations"][0]["ids"] == [i["sample_id"] for i in roster["items"]]
        assert doc["population"]["split_identity_hash"] == roster["split_identity_hash"]
        assert "thinking-system" not in json.dumps(doc).lower().replace("nxt-r2b-solver-budget", "")
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
    assert derived["fit"]["ok"] is True and derived["fragment"]["ok"] is True and derived["signoff_conditions"] == fam.SIGNOFF_CONDITIONS


# ---- the wire form: the delivering arm is the lock's request, the candidate moves the Solver only -----------------------------------------


def _resolve(values: dict, policy: dict | None, arm_policy: dict | None, role: str) -> dict:
    """Compose a node's decoding the way the request composer does: the fragment's folded defaults, the CELL-level policy, then the arm's own policy."""

    folded = rk.fold_into_decoding(values) or values
    out = dict(folded["decoding_params"])
    out = rk.resolve_node_decoding(out, policy or {}, role)
    return rk.resolve_node_decoding(out, arm_policy or {}, role)


def test_the_delivering_arm_resolves_to_the_lock_decoding_and_the_candidate_moves_the_solver_only():
    values = composed("arm").values
    lock_values = compose(REPO, tsf.THINK_MODEL, tsf.DATASET, tsf.CELLS["lock"]["baseline"], tsf.CELLS["lock"]["cell"]).values
    lock_base = dict((rk.fold_into_decoding(lock_values) or lock_values)["decoding_params"])
    assert lock_base["max_tokens"] == 4096 and values["decoding_params"]["max_tokens"] == 7168
    for node_name in fam.NODES:
        # the delivering arm: the fragment default (cap 7168) is overridden to the lock form by the cell-level policy; field for field the 268-B request decoding
        assert _resolve(values, values["thinking_policy"], None, node_name) == lock_base, node_name
        for arm_id in fam.CANDIDATE_ARMS:
            out = _resolve(values, values["thinking_policy"], fam.POLICIES[arm_id], node_name)
            setting = fam.SETTINGS[arm_id][fam.NODES.index(node_name)]
            if setting == LOCK:
                assert out == lock_base, (arm_id, node_name)                       # the candidate's Perception is the lock's request
            else:
                assert out["thinking_budget_tokens"] == setting["budget_tokens"] and out["max_tokens"] == setting["completion_cap"]
                assert {k: v for k, v in out.items() if k not in ("thinking_budget_tokens", "max_tokens")} == {
                    k: v for k, v in lock_base.items() if k not in ("thinking_budget_tokens", "max_tokens")}


@registered_only
def test_the_candidate_arm_wire_form_is_budget_6144_max_7168_on_the_solver_only():
    values = composed("arm").values
    solver = _resolve(values, values["thinking_policy"], fam.POLICIES["solver-6144"], "solver")
    perception = _resolve(values, values["thinking_policy"], fam.POLICIES["solver-6144"], "perception")
    assert (solver["thinking_budget_tokens"], solver["max_tokens"]) == (6144, 7168) and solver["chat_template_kwargs"] == {"enable_thinking": True}
    assert (perception["thinking_budget_tokens"], perception["max_tokens"]) == (3072, 4096)
    delivering = {n: _resolve(values, values["thinking_policy"], None, n) for n in fam.NODES}
    assert all((d["thinking_budget_tokens"], d["max_tokens"]) == (3072, 4096) for d in delivering.values())
    # the fallback re-ask reserve of every working request is the lock's 1,024 tokens
    assert rk.fallback_reserve(solver) == 1024 == rk.fallback_reserve(perception)


def test_the_delivering_arm_request_is_the_locked_plan_request_byte_for_byte_through_the_real_composer(tmp_path):
    """The R2 byte-for-byte test, extended with a CELL-LEVEL policy: the lock adapter has no policy at all; the column adapter carries the lock form as its role-level
    policy and the candidate arm's Solver override as its branch policy. The delivering arm's prepared bytes equal the lock's; the candidate differs in its Solver only."""

    pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")
    import test_thinking_policy_column as tpc  # noqa: PLC0415

    def adapter(path, *, role_policy, branch_policy):
        world = tpc._World(path)
        feature_root, packet, bindings = tpc._speech_feature_world(world, path)
        client, _gate, _t = tpc._client(world, path, transport=tpc._ScriptedTransport([("a", "stop", 3)] * 8), arm="speech-feature-query-native-tools",
                                        tool_schemas=tpc._TOOLS, speech_feature_root=feature_root, speech_packet_bindings=bindings, plan=tpc._native_plan(planned_model_calls=50))
        return tpc.MeteredNativeSpeechRequest(
            client=client, binding_provider=lambda r: tpc._native_binding(r.role_id, packet), render_request=lambda b: json.loads(b),
            completion_sink=lambda request, completion: None, role_thinking_policy=role_policy, branch_thinking_policy=branch_policy)

    lock = adapter(tmp_path / "lock", role_policy=None, branch_policy=None)
    column = adapter(tmp_path / "col", role_policy=json.loads(json.dumps(fam.DELIVERING_NODE_POLICY)),
                     branch_policy={arm_id: json.loads(json.dumps(fam.POLICIES[arm_id])) for arm_id in fam.CANDIDATE_ARMS})
    for role in fam.NODES:
        reference = lock.prepare(tpc._request(role, branch=None))
        armed = column.prepare(tpc._request(role, branch=fam.DELIVERING))
        assert armed.rendered_body() == reference.rendered_body(), role
        assert armed.request.payload_bytes == reference.request.payload_bytes, role
        expected, actual = json.loads(reference.role_request_bytes), json.loads(armed.role_request_bytes)
        assert actual["context"].pop("perception_branch_id") == fam.DELIVERING
        assert actual == expected, role
        locked = tpc._decoding(lock, role, branch=None)
        for arm_id in fam.CANDIDATE_ARMS:
            decoding = tpc._decoding(column, role, branch=arm_id)
            setting = fam.SETTINGS[arm_id][fam.NODES.index(role)]
            if setting == LOCK:
                assert decoding == locked, (arm_id, role)
                continue
            assert decoding["thinking_budget_tokens"] == setting["budget_tokens"] and decoding["max_tokens"] == setting["completion_cap"]
            assert {k: v for k, v in decoding.items() if k not in ("thinking_budget_tokens", "max_tokens")} == {
                k: v for k, v in locked.items() if k not in ("thinking_budget_tokens", "max_tokens")}


# ---- the context fit of the raised cap --------------------------------------------------------------------------------------------------


def test_the_live_slot_holds_the_solver_prompt_plus_the_raised_cap():
    proof = fam.fit_proof()
    assert proof["ok"] is True and all(proof["checks"].values())
    assert proof["slot_tokens"] == 24576 and proof["completion_cap"] == fam.FRAGMENT_CAP
    assert proof["prompt_limit_tokens"] == 24576 - 3072 - fam.FRAGMENT_CAP - 2 == fam.PROMPT_LIMIT
    assert proof["observed_solver_prompt_tokens_max"] + fam.FRAGMENT_CAP <= 24576 and proof["observed_headroom_tokens"] > 0
    assert proof["estimate_at_bound_tokens"] <= proof["prompt_limit_tokens"] and proof["estimate_headroom_tokens"] >= 0
    # the lock's 55-item bound does NOT fit the registered estimate at this ceiling; the bound is the largest count that does
    if fam.FRAGMENT_CAP == 7168:
        assert proof["lock_bound_fits_at_cap"] is False and proof["lock_bound_estimate_tokens"] == 14925 and proof["max_supplied_items"] == 52 == fam.MAX_SUPPLIED_ITEMS
    assert fam.estimated_prompt_tokens(fam.MAX_SUPPLIED_ITEMS + 1) > fam.PROMPT_LIMIT or fam.MAX_SUPPLIED_ITEMS == fam.LOCK_MAX_SUPPLIED_ITEMS
    assert fam.OBSERVED_SUPPLIED_COUNT_MAX <= fam.MAX_SUPPLIED_ITEMS
    # the same arithmetic is the rails' own parser: the thinking_variants block of the cell was accepted at this bound and ceiling
    est = baseline("arm")["native_episode"]["consumption_module"]["thinking_frame"]["fit_estimate"]
    assert est["completion_ceiling"] == fam.FRAGMENT_CAP and est["slot_tokens"] == 24576


def test_the_derive_refuses_when_the_slot_cannot_hold_the_prompt_plus_the_cap(monkeypatch):
    monkeypatch.setattr(fam, "OBSERVED_SOLVER_PROMPT_MAX", fam.PROMPT_LIMIT + 1)
    assert fam.fit_proof()["ok"] is False
    with pytest.raises(SystemExit, match="does not hold the Solver prompt plus"):
        dc.derive(write=False)
    monkeypatch.undo()
    monkeypatch.setattr(fam, "OBSERVED_SUPPLIED_COUNT_MAX", fam.MAX_SUPPLIED_ITEMS + 1)
    with pytest.raises(SystemExit, match="observed_supplied_count_within_bound"):
        dc.derive(write=False)
    monkeypatch.undo()
    monkeypatch.setattr(fam, "SLOT_TOKENS", 20000)
    assert fam.fit_proof()["checks"]["slot_holds_prompt_plus_cap"] is False


# ---- the serving fragment and the swap target ------------------------------------------------------------------------------------------


def test_the_raised_fragment_differs_from_the_resident_one_only_in_the_cap_leaves():
    proof = dc.fragment_proof()
    assert proof["ok"] and proof["stray_leaves"] == [] and set(proof["moved_leaves"]) == {"answer_reserve_tokens", "decoding_params.max_tokens", "geometry_basis"}
    assert proof["server_args_equal"] and proof["runtime_receipt_equal"] and proof["server_env_equal"] and (proof["slots"], proof["slot_tokens"]) == (4, 24576)
    new, old = js(f"configs/model/{fam.THINK_MODEL}.json"), js(f"configs/model/{fam.CONTROL_FRAGMENT}.json")
    assert new["server_args"] == old["server_args"] and new["runtime_receipt"] == old["runtime_receipt"] == "receipts/runtime-q4km-thinking-mmproj-free.json"
    assert new["decoding_params"]["max_tokens"] == fam.FRAGMENT_CAP and new["answer_reserve_tokens"] == fam.FRAGMENT_CAP - new["reasoning_budget_tokens"]
    assert new["profile_slot_count"] == 4 and new["speech_feature_root"] == old["speech_feature_root"]
    rk.validate_fragment_knobs(new)                                                         # the fragment invariant max_tokens = budget + reserve holds
    assert fam.THINK_MODEL == f"q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max{fam.FRAGMENT_CAP}-v1"
    assert fam.THINK_SESSION == f"serving-slurp-thinking-module-fold-b-np4-budget3072-max{fam.FRAGMENT_CAP}-v1"
    assert fam.THINK_SWAP_TARGET == f"think-budget{fam.FRAGMENT_CAP}-np4"
    assert fam.THINK_SESSION != tsf.THINK_SESSION and fam.THINK_MODEL != tsf.THINK_MODEL                    # a NEW session id: the resident one encodes max4096


def test_the_raised_session_is_wired_as_a_swap_target_exactly_like_think_budget_np4():
    lib = REPO / "scripts/flights/batch/serving_lib.sh"
    script = f"source {lib}; saea_geometry {fam.SWAP_TARGET} && echo \"$G_SID|$G_FRAGMENT|$G_SERVING_TASK|$G_MONITOR_TASK|$G_SERVING_ENTRY|$G_MONITOR_ENTRY|$G_LABEL\"; " \
             f"saea_geometry think-budget-np4 && echo \"$G_SID|$G_FRAGMENT|$G_SERVING_TASK|$G_MONITOR_TASK\"; echo \"$SAEA_TARGETS\""
    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    new_row, old_row, targets = done.stdout.strip().splitlines()[-3:]
    sid, fragment, serving, monitor, s_entry, m_entry, label = new_row.split("|")
    assert (sid, fragment) == (fam.THINK_SESSION, fam.THINK_MODEL) and (serving, monitor) == ("SAEA-Serving-THINKB7", "SAEA-Monitor-THINKB7") and label == "THINKB7"
    assert old_row.split("|")[:2] == [tsf.THINK_SESSION, tsf.THINK_MODEL] and old_row.split("|")[2:] == ["SAEA-Serving-THINKB", "SAEA-Monitor-THINKB"]
    assert fam.SWAP_TARGET in targets.split() and "think-budget-np4" in targets.split()
    for entry in (s_entry, m_entry):
        path = REPO / entry
        assert path.is_file() and subprocess.run(["bash", "-n", str(path)], capture_output=True).returncode == 0
        text = path.read_text(encoding="utf-8")
        assert fam.THINK_SESSION in text and "max4096" not in text and text.isascii()
    assert fam.THINK_MODEL in (REPO / s_entry).read_text(encoding="utf-8")
    assert fam.ACTIVE_GEOMETRY["target"] == fam.SWAP_TARGET and (fam.ACTIVE_GEOMETRY["slots"], fam.ACTIVE_GEOMETRY["slot_tokens"]) == (4, 24576)
    assert fam.THINK_SLOTS == 4 and fam.CONTROL_SESSION == fam.THINK_SESSION                # the smoke and the column flight share the one new session
    assert fam.SWAP_TARGET in (REPO / "scripts/flights/batch/serving_swap.sh").read_text(encoding="utf-8")


# ---- budgets and the cost arithmetic ---------------------------------------------------------------------------------------------------


def test_costs_are_the_r1_measured_seconds_scaled_by_the_budget_ratio_and_rounded_up():
    r1 = fam.R1
    assert abs(fam.NODE_SECONDS["perception"] + fam.NODE_SECONDS["solver"] - r1["seconds_per_row_both_on"]) < 1e-6
    assert abs(1080 * r1["seconds_per_row_both_on"] / r1["slots"] / 3600 - r1["gpu_hours_per_1080_row_pass"]) < 1e-9
    assert r1["source_sha256"] and re.fullmatch(r"[0-9a-f]{64}", r1["source_sha256"])
    for arm_id in fam.CANDIDATE_ARMS:
        seconds = sum(fam.NODE_SECONDS[n] * (fam.NODE_BUDGETS[arm_id][n] / 3072) for n in fam.NODES)
        exact = seconds / r1["seconds_per_row_both_on"]
        assert fam.ROW_COST[arm_id] == math.ceil(round(exact * 100, 9)) / 100 and fam.ROW_COST[arm_id] >= exact and fam.ROW_COST[arm_id] > 1.0   # a RAISE costs more
        assert abs(fam.LINEAR_REFERENCE[arm_id] - exact) < 1e-4
    assert fam.ROW_COST[fam.DELIVERING] == 1.0 and fam.ARM_MIX_ROWS == round(sum(fam.ROW_COST.values()), 2)
    assert fam.ROWS_PER_MINUTE_FULL == math.floor(round(r1["slots"] * 60 / r1["seconds_per_row_both_on"] * 100, 9)) / 100
    with pytest.raises(ValueError, match="only raised budgets"):
        fam.NODE_BUDGETS["tmp"] = {"perception": 2048, "solver": 3072}
        try:
            fam.relative_cost("tmp")
        finally:
            fam.NODE_BUDGETS.pop("tmp")


@registered_only
def test_the_registered_expected_hours_and_ceiling():
    assert fam.ROW_COST == {"solver-6144": 1.57, "budget-3072": 1.0} and fam.ARM_MIX_ROWS == 2.57 and fam.ROWS_PER_MINUTE_FULL == 2.18
    expected = 1080 * 2.57 / 2.18 / 60
    assert abs(fam.expected_gpu_hours(1080) - expected) < 1e-9 and 21.2 < expected < 21.3
    assert fam.planned_gpu_hours(1080) == fam.CELLS["arm"]["gpu_hours"] == 27.6
    assert fam.CELLS["smoke"]["gpu_hours"] == 0.5 == tsf.SMOKE_GPU_HOURS
    assert fam.planned_gpu_hours(1080) == round(math.ceil(round(fam.expected_gpu_hours(1080) * fam.GPU_MARGIN / fam.GPU_ROUND_H, 9)) * fam.GPU_ROUND_H, 1)
    assert abs(fam.lock_flight_gpu_hours(fam.DELIVERING) - 1080 / 2.18 / 60) < 1e-9 and fam.lock_flight_gpu_hours("solver-6144") > fam.lock_flight_gpu_hours(fam.DELIVERING)


def test_plan_ceilings_follow_the_program_and_the_fallback_contacts():
    assert fam.original_generation_calls("arm") == 1080 * (fam.CONTACTS_PER_ROW + fam.FALLBACK_CONTACTS_PER_ROW_CEILING)
    assert fam.program_calls("arm") == 1080 * fam.CONTACTS_PER_ROW and fam.fit_contact_cap(4) == 4 * fam.CONTACTS_PER_ROW * 4
    for key in fam.ALL_KEYS:
        plan = experiment(key)["execution_plan"]
        assert plan["planned_model_calls"] == fam.generation_calls(key) and plan["planned_gpu_hours"] == fam.CELLS[key]["gpu_hours"]
        assert plan["execution_profile"] == "bounded-discovery-probe" and plan["split_role"] == "discovery"
        assert experiment(key)["family_budget"]["fit_endpoint_calls_cap"] == fam.fit_contact_cap(fam.CELLS[key]["rows"])


# ---- the package ------------------------------------------------------------------------------------------------------------------


def test_stage3_measurement_blocks():
    facts = json.loads((PKG / "registered-facts-v1.json").read_text(encoding="utf-8"))
    blocks = facts["stage3_measurement"]
    arm_run, smoke = fam.CELLS["arm"]["run"], fam.CELLS["smoke"]["run"]
    assert set(blocks) == {arm_run, smoke}
    b = blocks[arm_run]
    assert b["measurement_design"] == "same-flight-node-column" and b["claims_benefit"] is False and b["claim"] == "nominated"
    assert b["primary_metric_key"] == "slu" and b["rows"] == 1080 and b["tuning_roster"] == "none" and b["read_roster"] == fam.READ_ROSTER
    assert "aa_arm_id" not in b
    assert b["template_variants"] == {"node": "perception", "candidate_arms": len(fam.CANDIDATE_ARMS), "twin": False} and b["variant_kind"] == "thinking-budget"
    assert b["variant_cost"]["extra_contacts_per_row"] == fam.CONTACTS_PER_ROW - 2 and b["variant_cost"]["extra_audio_seconds"] > 0
    assert str(fam.DECLARED_OFFSET_SLU_PP) in b["note"] and str(fam.PAIRED_FLOOR_PP) in b["note"]
    assert blocks[smoke]["measurement_design"] == "form-proof" and blocks[smoke]["claims_benefit"] is False
    assert facts["blockers"] == [] and {f["id"] for f in facts["findings"]} >= {
        "solver-reasoning-is-truncated-at-the-delivering-budget", "no-twin-the-declared-offset-is-the-null", "fit-bound-52-not-55-at-the-raised-cap",
        "cell-level-thinking-policy-states-the-lock-form", "new-session-same-geometry", "machine-signoff-with-a-veto-window"}
    ce = facts["accounting"]["cost_estimate"]
    assert ce["column_flight"]["planned_ceiling_gpu_hours"] == fam.CELLS["arm"]["gpu_hours"] and ce["arm_mix_rows"] == fam.ARM_MIX_ROWS
    assert [r["arm"] for r in ce["arm_table"]] == list(fam.ARM_ORDER) and ce["inputs"]["r1_measured"]["slots"] == 4
    assert facts["thinking_arms"]["budget-3072"] is None and facts["read_rule"]["declared_offset_slu_pp"] == 1.15 == fam.DECLARED_OFFSET_SLU_PP
    assert facts["read_rule"]["twin"] is None and facts["read_rule"]["word_order"] == list(reader.NODE_WORDS) and facts["read_rule"]["word_mode"] == "raise"
    assert facts["context_fit"]["ok"] is True and facts["context_fit"]["max_supplied_items"] == fam.MAX_SUPPLIED_ITEMS and facts["fragment"]["ok"] is True
    assert facts["pins"]["signoff_conditions"]["sha256"] == hashlib.sha256((PKG / "signoff-conditions-v1.json").read_bytes()).hexdigest()
    assert facts["cell_thinking_policy"] == fam.DELIVERING_NODE_POLICY


def test_the_effect_floor_gate_resolves_a_twinless_node_column(tmp_path):
    """The gate keys on the exposure ledger; the package's DRAFT rows are overlaid on a COPY (this repository's ledger is not touched)."""

    ledger = tmp_path / "ledger.md"
    ledger.write_text((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8") + "\n" + (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8"),
                      encoding="utf-8")
    out = subprocess.run([sys.executable, "-B", str(REPO / "scripts/checks/stage3_effect_floor_check.py"), "--ledger", str(ledger), "--json"],
                         capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0, out.stderr[-500:]
    report = json.loads(out.stdout[out.stdout.find("{"):])
    mine = [c for c in report["in_scope_cells"] if "nxt-r2b-solver-budget" in c["cell_id"]]
    assert {c["cell_id"] for c in mine} == {fam.CELLS[k]["cell"] for k in fam.ALL_KEYS}
    assert not [f for f in report["findings"] if "nxt-r2b-solver-budget" in json.dumps(f)]
    column = {c["cell_id"]: c["declaration"] for c in mine}[fam.CELLS["arm"]["cell"]]
    assert column["problems"] == [] and column["measurement_design"] == "same-flight-node-column" and column["claims_benefit"] is False


def test_plans_protocol_receipt_and_ledger_agree():
    protocol_sha = hashlib.sha256((PKG / "protocol-registered-v1.json").read_bytes()).hexdigest()
    draft_rows = (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8")
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    for key in fam.ALL_KEYS:
        for kind in ("generation", "fit"):
            assert fam.plan_file_name(key, kind) == (f"{fam.CELLS[key]['prefix']}{kind}-plan-registered-v1.json")
            plan = json.loads((PKG / fam.plan_file_name(key, kind)).read_text(encoding="utf-8"))
            assert plan["expected_session_id"] == fam.THINK_SESSION and plan["protocol_document"]["sha256"] == protocol_sha
            assert plan["thinking_knobs"]["thinking_budget_tokens"] == 3072 and plan["execution_plan"]["split_role"] == "discovery"
            assert plan["arm_order"] == list(fam.ARM_ORDER) and plan["no_twin"] is True and "recovery" not in plan
            assert plan["cell_thinking_policy"] == fam.DELIVERING_NODE_POLICY and plan["serving"]["geometry_cap"] == fam.FRAGMENT_CAP
            assert plan["thinking_arms"][fam.CANDIDATE_ARMS[0]]["thinking_policy"] == fam.POLICIES[fam.CANDIDATE_ARMS[0]]
            assert plan["thinking_arms"][fam.DELIVERING]["thinking_policy"] is None
            run = fam.CELLS[key]["run" if kind == "generation" else "fit_run"]
            assert plan["execution_plan"]["run_id"] == run and plan["execution_plan"]["planned_gpu_hours"] == fam.CELLS[key]["gpu_hours"]
            assert plan["execution_plan"]["planned_model_calls"] == (fam.generation_calls(key) if kind == "generation" else fam.fit_contact_cap(fam.CELLS[key]["rows"]))
            if kind == "fit":
                assert plan["context_fit"]["ok"] is True and plan["context_fit"]["prompt_limit_tokens"] == fam.PROMPT_LIMIT       # the FIT plans show the slot holds prompt + cap
            assert draft_rows.count(f"| {run} |") == 1
            assert ledger.count(f"| {run} |") in (0, 1)
    draft = json.loads((PKG / "root-admission-draft-v1.json").read_text(encoding="utf-8"))
    assert draft["eligible_run_ids"] == fam.eligible_run_ids() and draft["eligible_attempt_ids"] == fam.eligible_attempt_ids()
    assert draft["decision_id"] == fam.DECISION_ID and draft["status"] == "DRAFT-NOT-MINTED" and draft["service"]["expected_session_id"] == fam.THINK_SESSION
    assert draft["service"]["model_fragment"] == fam.THINK_MODEL and "recovery" not in draft and draft["budget"]["generation_calls_cap"] == fam.generation_calls("arm")
    texts = json.loads((PKG / "countersign-row-texts-v1.json").read_text(encoding="utf-8"))
    current = {fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")}
    assert set(texts["rows"]) == current | {fam.READ_RUN_ID} and draft_rows.count(f"| {fam.READ_RUN_ID} |") == 1
    assert len([ln for ln in draft_rows.splitlines() if ln.startswith("| 2026")]) == 5
    recipe = json.loads((PKG / "analysis-recipe-v1.json").read_text(encoding="utf-8"))
    assert recipe["read_run_id"] == fam.READ_RUN_ID and recipe["arms"] == list(fam.ARM_ORDER) and recipe["twin"] is None and recipe["delivering"] == fam.DELIVERING
    assert recipe["declared_offset"]["slu_pp"] == 1.15 and recipe["verdict_words"] == list(reader.NODE_WORDS) and recipe["word_mode"] == "raise"
    assert (REPO / fam.PREREG).is_file()
    for line in draft_rows.splitlines():
        if line.startswith("| 2026"):
            assert "DRAFT" in line and "root countersigned" not in line


def test_the_readme_names_the_rulings_the_fit_the_cost_the_words_and_the_geometry():
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    for needle in ("323", "325 A", "313 A", "think-budget7168-np4", "drop-reasoning-v1", "6144", "7168", "4096", "budget-3072", "independent chains", "no note sharing", "own Perception note",
                   "ceil_0.1", "GAIN", "HARM", "NEEDS-NO-MORE-BUDGET", "UNRESOLVED", "flip_package_ext4.sh", "saea-perception-branch-arms-v5", "byte for byte", "THROUGHPUT",
                   "nxt_r2b_arms.json", "|o| = 1.15", "0.7 pp", "nxt2b-decode-signoff.marker", "NXT2B_KINDS", "no twin", "cell-level `thinking_policy`", "-c 98304 -np 4",
                   "runtime-q4km-thinking-mmproj-free.json", "14,334", "14,925", "does NOT fit", "wait_or_machine_signoff", "close_rows_after_seal", "SAEA-Chain-NXT2B",
                   "queue_nxt2b_after_nxt2.sh", "CHAIN_NXT2_EXIT", "signoff-conditions-v1.json", "arm-only", "flight_registration_check.py"):
        assert needle in readme, needle
    for script in ("nxt_r2b_flip.sh", "nxt_r2b_read.sh", "nxt_r2b_repin_cell.sh", "batch_chain_nxt_r2b.sh"):
        assert subprocess.run(["bash", "-n", str(NX / script)], capture_output=True).returncode == 0
    assert str(fam.CELLS["arm"]["gpu_hours"]) in readme and str(fam.ARM_MIX_ROWS) in readme
    assert not re.search(r"[^\x00-\x7f]", readme)


def test_the_text_of_the_package_is_english():
    for path in [PKG / n for n in ("README.md", "draft-ledger-rows.md", "countersign-row-texts-v1.json", "registered-facts-v1.json", "protocol-registered-v1.json",
                                     "signoff-conditions-v1.json")]:
        assert not re.search(r"[^\x00-\x7f]", path.read_text(encoding="utf-8")), path
    for name in ("nxt_r2b_family.py", "nxt_r2b_derive_cells.py", "nxt_r2b_write_registration.py", "nxt_r2b_mint_receipt.py", "nxt_r2b_dry_run.py", "nxt_r2b_flip.sh",
                 "nxt_r2b_repin_cell.sh", "nxt_r2b_read.sh", "batch_chain_nxt_r2b.sh", "nxt_r2b_arms.json", "nxt_r2b_cost_inputs.json", "nxt_r2b_launch_spec.json"):
        assert (NX / name).read_text(encoding="utf-8").isascii(), name
    for rel in (fam.READER, fam.READER_IMPL, fam.PREREG, "scripts/flights/batch/queue/queue_nxt2b_after_nxt2.sh", "scripts/flights/batch/queue/chain_nxt2b.sh",
                f"configs/model/{fam.THINK_MODEL}.json", "scripts/flights/direct/serving_task_entry_think_budget7168.sh", "scripts/flights/direct/serving_monitor_start_think_budget7168.sh"):
        assert (REPO / rel).read_text(encoding="utf-8").isascii(), rel


# ---- the sign-off conditions (emitted by the derive, inside the package) -------------------------------------------------------------


def test_signoff_conditions_are_emitted_inside_the_package_from_the_arm_table():
    committed = json.loads((PKG / "signoff-conditions-v1.json").read_text(encoding="utf-8"))
    assert committed == fam.signoff_conditions()
    assert (PKG / "signoff-conditions-v1.json").read_text(encoding="utf-8") == dc.signoff_conditions_text()
    smoke_signoff.validate_conditions(committed)
    assert committed["package"] == fam.PKG_NAME and committed["table_schema"] == fam.SMOKE_SCHEMA == reader.SCHEMA_SMOKE
    assert committed["table_relpath"] == f"{fam.ANALYSIS_ROOT}/smoke-decode-cost.json" and committed["expected_arms"] == sorted(fam.ARM_ORDER)
    assert committed["no_think_nodes"] == {} and committed["every_node_max"] == {"cap_hits": 0, "empty_content": 0, "no_json_object": 0, "finish_reason_length": 0}
    assert committed["arm_mix"] == {"max_ratio": 1.3, "measured_key": "arm_mix_measured_rows", "registered_key": "arm_mix_registered_rows"}
    assert {(e["id"], e["path"], e["op"], e["value"]) for e in committed["extras"]} == {("unattributed-contacts", "unattributed_contacts", "==", 0),
                                                                                         ("absent-columns", "absent_columns", "==", 0)}
    if IS_REGISTERED:
        assert committed["expected_arms"] == ["budget-3072", "solver-6144"]


def test_the_derive_regenerates_the_signoff_conditions_when_the_table_changes(tmp_path):
    first = dc.write_signoff_conditions(repo_root=tmp_path)
    before = (tmp_path / first).read_text(encoding="utf-8")
    assert json.loads(before) == fam.signoff_conditions() and dc.write_signoff_conditions(repo_root=tmp_path) == first                 # idempotent
    variant = family_variant(tmp_path, table(arm("solver-6000", solver=node(6000, 7168))))
    assert variant.ARM_ORDER == ("solver-6000", "budget-3072")
    original = dc.fam
    dc.fam = variant
    try:
        dc.write_signoff_conditions(repo_root=tmp_path)
    finally:
        dc.fam = original
    after = (tmp_path / first).read_text(encoding="utf-8")
    assert after != before and json.loads(after)["expected_arms"] == ["budget-3072", "solver-6000"] and json.loads(before)["expected_arms"] == sorted(fam.ARM_ORDER)
    # the registered table is unchanged in the repository
    assert (PKG / "signoff-conditions-v1.json").read_text(encoding="utf-8") == before


def test_a_table_edit_flows_through_the_family(tmp_path):
    variant = family_variant(tmp_path, table(arm("solver-6000", solver=node(6000, 7168))))
    assert variant.CANDIDATE_ARMS == ("solver-6000",) and variant.POLICIES["solver-6000"]["solver"]["reasoning_budget_tokens"] == 6000
    assert variant.ROW_COST["solver-6000"] < fam.ROW_COST["solver-6144"] or not IS_REGISTERED
    assert variant.NODE_CAPS["solver-6000"] == {"perception": 4096, "solver": 7168} and variant.SIGNOFF_CONDITIONS == fam.SIGNOFF_CONDITIONS
    assert variant.THINK_MODEL == fam.THINK_MODEL                                            # same fragment cap, same session
    with pytest.raises(Exception, match="must be >= budget_tokens"):
        family_variant(tmp_path, table(arm("x", solver=node(6144, 7000))))


def test_the_signoff_conditions_pass_a_good_smoke_and_refuse_a_cap_hit():
    mapping = reader.arm_contact_map(_receipt_rows())
    good = reader.smoke_stage(reader.attribute(_synthetic_contacts(), mapping))
    checks = smoke_signoff.evaluate(fam.signoff_conditions(), good)
    assert checks and all(c["ok"] for c in checks), [c for c in checks if not c["ok"]]
    capped = reader.smoke_stage(reader.attribute(_synthetic_contacts(cap_hit=True), mapping))
    assert any(not c["ok"] for c in smoke_signoff.evaluate(fam.signoff_conditions(), capped))
    stale = copy.deepcopy(fam.signoff_conditions())
    stale["expected_arms"] = ["budget-3072", "perception-off-solver-3072", "solver-2048"]                       # R2's stale table: refused by name
    assert any((not c["ok"]) and c["id"].startswith("arm-present/") for c in smoke_signoff.evaluate(stale, good))


# ---- the reader ------------------------------------------------------------------------------------------------------------------


def _rows(ids, tp, fp, fn, intent):
    return {i: {"slu_f1_word_tp": tp[n], "slu_f1_char_tp": tp[n], "slu_f1_word_fp": fp[n], "slu_f1_char_fp": fp[n], "slu_f1_word_fn": fn[n],
                "slu_f1_char_fn": fn[n], reader.INTENT_FIELD: intent[n]} for n, i in enumerate(ids)}


def _arms(ids, harm=False, gain=False):
    base = _rows(ids, [3.0] * len(ids), [1.0] * len(ids), [1.0] * len(ids), [1.0] * len(ids))
    worse = _rows(ids, [1.0] * len(ids), [3.0] * len(ids), [3.0] * len(ids), [0.0] * len(ids))
    better = _rows(ids, [5.0] * len(ids), [1.0] * len(ids), [1.0] * len(ids), [1.0] * len(ids))
    arms = {arm_id: base for arm_id in fam.ARM_ORDER}
    if harm:
        arms[fam.CANDIDATE_ARMS[-1]] = worse
    if gain:
        arms[fam.CANDIDATE_ARMS[-1]] = better
    return arms


def test_the_r2b_words_invert_the_cheaper_wording_for_a_raised_budget():
    ci = lambda lo, hi: {"point_pp": (lo + hi) / 2, "ci95_lo_pp": lo, "ci95_hi_pp": hi}  # noqa: E731
    o = fam.DECLARED_OFFSET_SLU_PP
    assert (o, fam.FLOOR_SLU_PP, fam.FLOOR_INTENT_PP, fam.PAIRED_FLOOR_PP) == (1.15, 1.49, 0.65, 0.7)
    assert reader.WORD_MODE == "raise" and reader.NODE_WORDS == ("GAIN", "HARM", "NEEDS-NO-MORE-BUDGET", "UNRESOLVED")
    cases = [
        (ci(o + 0.01, 3.0), ci(-3, 3), "GAIN"),                                    # lower bound above +|o|, whatever the intent
        (ci(-3.0, -o - 0.01), ci(-0.1, 1.0), "HARM"),                                # upper bound below -|o|
        (ci(-1.0, 1.49), ci(-1.0, 0.65), "NEEDS-NO-MORE-BUDGET"),                    # both upper bounds exactly at the floors
        (ci(-0.5, 0.5), ci(-0.3, 0.3), "NEEDS-NO-MORE-BUDGET"),
        (ci(-3.0, 1.15), ci(-0.1, 0.5), "NEEDS-NO-MORE-BUDGET"),                     # no resolved gain, whatever the lower bound
        (ci(-0.5, 1.5), ci(-0.1, 0.5), "UNRESOLVED"),                                # SLU upper bound above its floor
        (ci(-0.5, 0.5), ci(-0.3, 0.7), "UNRESOLVED"),                                # intent upper bound above its floor
        (ci(1.0, 1.6), ci(-0.1, 0.5), "UNRESOLVED"),
        (ci(1.15, 2.0), ci(-0.1, 0.5), "UNRESOLVED"),                                # +|o| exactly is not above it
        (ci(-3.0, -1.15), ci(-0.1, 0.5), "NEEDS-NO-MORE-BUDGET"),                    # -|o| exactly is not below it, and the upper bound is inside the floors
    ]
    for slu, intent, word in cases:
        assert reader.classify(slu, intent) == word, (slu, intent, word)
    contrast = {"versus_delivering": {arm_id: {"slu_f1": ci(-0.5, 0.5), "intent": ci(-0.3, 0.3)} for arm_id in fam.CANDIDATE_ARMS}}
    words = reader.node_words(contrast)
    assert words["declared_offset_abs_pp"] == 1.15 and words["paired_floor_pp"] == 0.7 and set(words["words"]) == set(fam.CANDIDATE_ARMS)
    assert all(v["word"] == "NEEDS-NO-MORE-BUDGET" for v in words["words"].values())
    assert words["words"][fam.CANDIDATE_ARMS[0]]["node"] == reader.node_label(fam.CANDIDATE_ARMS[0])


def test_the_writer_words_are_the_readers_words_in_order():
    import nxt_r2b_write_registration as writer

    assert list(writer.WORD_RULES) == list(reader.NODE_WORDS) == ["GAIN", "HARM", "NEEDS-NO-MORE-BUDGET", "UNRESOLVED"]


def test_the_r2_reader_is_unchanged_and_the_two_modules_do_not_share_state():
    import slurp_nxt_thinking_budget_column_read as r2_reader

    assert r2_reader.fam.__name__ == "nxt_r2_family" and r2_reader.WORD_MODE == "cheaper" and r2_reader is not reader
    assert r2_reader.NODE_WORDS == ("GAIN", "NEEDS-FULL-BUDGET", "CHEAPER-AT-NO-RESOLVED-LOSS", "UNRESOLVED")
    assert reader.fam.__name__ == "nxt_r2b_family" and reader_entry.load() is reader and reader.SCHEMA_SMOKE == fam.SMOKE_SCHEMA and reader.SCHEMA_READ == fam.READ_SCHEMA
    assert r2_reader.NODE_CAPS is None and reader.NODE_CAPS == fam.NODE_CAPS
    assert os.environ.get("NXT_COLUMN_READ_FAMILY") in (None, "")                              # the loader restores the environment


def test_reader_paired_contrast_end_to_end_without_a_twin():
    ids = [f"r{n}" for n in range(40)]
    for arms_kw, word in (({}, "NEEDS-NO-MORE-BUDGET"), ({"harm": True}, "HARM"), ({"gain": True}, "GAIN")):
        contrast = reader.paired_contrasts(_arms(ids, **arms_kw), ids, lambda sid: sid, seed=1, draws=200)
        assert set(contrast["levels"]) == set(fam.ARM_ORDER) and fam.DELIVERING not in contrast["versus_delivering"]
        assert reader.node_words(contrast)["words"][fam.CANDIDATE_ARMS[0]]["word"] == word
    assert reader.SEED == 20261015 and reader.node_label(fam.CANDIDATE_ARMS[0]).split("@")[0] in fam.NODES
    table_ = reader.per_scenario_table(_arms(ids, harm=True), ids, lambda sid: "alarm" if int(sid[1:]) % 2 else "music")
    assert set(table_["scenarios"]) == {"alarm", "music"} and table_["natural_mixture"][f"slu_d_{fam.CANDIDATE_ARMS[-1]}_pp"] < 0


def _contact(agent, node_name, tokens, seconds, finish="stop", *, empty=False, reasoning=0, forced=False, marker=False):
    return {"agent_contact_id": agent, "role": node_name, "prompt_tokens": 3000, "completion_tokens": tokens, "latency_seconds": seconds, "finish_reason": finish,
            "empty_content": empty, "no_json_object": False, "marker_in_content": marker, "reasoning_chars": reasoning, "forced_close": forced}


def _receipt_rows():
    rows = []
    for sid in ("s1", "s2"):
        rows.append({"sample_id": sid, "native_episode_receipt": {"perception_branches": {"branches": [
            {"branch_id": arm_id, "contact_id": f"{sid}:{arm_id}:p", "solver_contact_id": f"{sid}:{arm_id}:s"} for arm_id in fam.ARM_ORDER]}}})
    return rows


def _synthetic_contacts(*, cap_hit: bool = False):
    """Two rows: a contact costs seconds proportional to its tokens; the RAISED node (budget above the delivering one) reasons longer and costs more."""

    contacts = []
    for sid in ("s1", "s2"):
        for arm_id in fam.ARM_ORDER:
            for node_name, suffix in (("perception", "p"), ("solver", "s")):
                budget, cap = reader.BUDGET[arm_id][node_name], fam.NODE_CAPS[arm_id][node_name]
                tokens = (min(5000, budget) if budget > 3072 else 2600) + 60
                contacts.append(_contact(f"{sid}:{arm_id}:{suffix}", node_name, cap if cap_hit else tokens, 0.025 * tokens, reasoning=5000,
                                         forced=False, finish="length" if cap_hit else "stop"))
    return contacts


def test_reader_counts_cap_hits_against_each_nodes_own_cap_and_tabulates_the_throughput():
    mapping = reader.arm_contact_map(_receipt_rows())
    assert len(mapping) == 4 * fam.K
    contacts = _synthetic_contacts() + [_contact("stray", "perception", 10, 1.0)]
    by_arm = reader.attribute(contacts, mapping)
    assert set(by_arm) == set(fam.ARM_ORDER) | {"unattributed"} and len(by_arm[fam.DELIVERING]) == 4
    tables = reader.tables_by_arm(by_arm)
    cand = fam.CANDIDATE_ARMS[0]
    assert tables[fam.DELIVERING]["solver"]["cap"] == 4096 and tables[fam.DELIVERING]["solver"]["budget"] == 3072 and tables[fam.DELIVERING]["perception"]["cap"] == 4096
    assert tables[cand]["perception"]["cap"] == 4096 and tables[cand]["solver"]["cap"] == fam.NODE_CAPS[cand]["solver"]
    if IS_REGISTERED:
        assert tables[cand]["solver"]["cap"] == 7168 and tables[cand]["solver"]["budget"] == 6144
        # 5,060 completion tokens is a cap hit at the delivering Solver's 4,096 cap but NOT at the raised arm's 7,168 cap
        probe = [_contact("s1:solver-6144:s", "solver", 5060, 100.0), _contact("s1:budget-3072:s", "solver", 5060, 100.0)]
        probed = reader.attribute(probe, mapping)
        assert reader.arm_node_table(probed["solver-6144"], "solver-6144")["solver"]["cap_hits"] == 0
        assert reader.arm_node_table(probed["budget-3072"], "budget-3072")["solver"]["cap_hits"] == 1
        probe = [_contact("s1:solver-6144:s", "solver", 7168, 100.0, finish="length")]
        assert reader.arm_node_table(reader.attribute(probe, mapping)["solver-6144"], "solver-6144")["solver"]["cap_hits"] == 1
    throughput = reader.throughput_table(tables, 1080)
    assert "unattributed" not in throughput["arms"] and throughput["arm_mix_registered_rows"] == fam.ARM_MIX_ROWS
    d = throughput["arms"][fam.DELIVERING]
    assert d["cost_in_delivering_rows"] == 1.0 and abs(d["gpu_hours_per_lock_flight_at_reference_throughput"] - 1080 / fam.ROWS_PER_MINUTE_FULL / 60) < 1e-9
    v = throughput["arms"][cand]
    assert v["gpu_hours_per_lock_flight"] > d["gpu_hours_per_lock_flight"] and v["saving_vs_delivering"] < 0 and v["registered_cost_in_rows"] == fam.ROW_COST[cand]
    md = reader.render_markdown({"arms_nodes": tables, "throughput": throughput, "node_words": None})
    assert "LOCK flight" in md and md.startswith("# NX-T R2b read")


def test_smoke_signoff_conditions_are_booleans_the_coordinator_can_veto():
    mapping = reader.arm_contact_map(_receipt_rows())
    good = reader.smoke_stage(reader.attribute(_synthetic_contacts(), mapping))
    assert good["schema"] == fam.SMOKE_SCHEMA and good["signoff"]["all_ok"] is True and good["signoff"]["mix_tolerance"] == 1.3
    assert good["unattributed_contacts"] == 0 and good["contacts"] == reader.CONTACTS_ZERO
    capped = reader.smoke_stage(reader.attribute(_synthetic_contacts(cap_hit=True), mapping))
    assert capped["signoff"]["conditions"]["no_cap_hits_empty_or_malformed"] is False and capped["signoff"]["all_ok"] is False
    stray = reader.smoke_stage(reader.attribute(_synthetic_contacts() + [_contact("stray", "perception", 10, 1.0)], mapping))
    assert stray["unattributed_contacts"] == 1 and stray["signoff"]["conditions"]["every_contact_attributed"] is False


def test_the_reader_loads_only_ids_from_the_sealed_outputs(tmp_path):
    path = tmp_path / "outputs.jsonl"
    rows = [{"sample_id": "s1", "text": "SECRET ANSWER TEXT", "native_episode_receipt": {"perception_branches": {"branches": [
        {"branch_id": "budget-3072", "contact_id": "c1", "solver_contact_id": "c2", "thinking_policy": None, "note_sha256": "x" * 64}]}}}]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    loaded = reader.load_outputs_rows(path)
    assert "SECRET" not in json.dumps(loaded) and loaded[0]["native_episode_receipt"]["perception_branches"]["branches"][0]["contact_id"] == "c1"


def test_the_structural_dry_run_script_states_the_registered_node_decoding(tmp_path):
    import py_compile

    py_compile.compile(str(NX / "nxt_r2b_dry_run.py"), cfile=str(tmp_path / "nxt_r2b_dry_run.pyc"), doraise=True)
    import nxt_r2b_dry_run as dry

    on = lambda b, c: {"thinking_budget_tokens": b, "chat_template_kwargs": {"enable_thinking": True}, "max_tokens": c}  # noqa: E731
    assert dry.expected_node_decoding(fam.DELIVERING) == {"perception": on(3072, 4096), "solver": on(3072, 4096)}
    for arm_id in fam.CANDIDATE_ARMS:
        for node_name, setting in zip(fam.NODES, fam.SETTINGS[arm_id]):
            assert dry.expected_node_decoding(arm_id)[node_name] == on(setting["budget_tokens"], setting["completion_cap"])
    # the expectation equals what the harness resolves for the composed cell, INCLUDING the cell-level policy (the dry run's own seam)
    values = composed("smoke").values
    for arm_id in fam.ARM_ORDER:
        for node_name in fam.NODES:
            resolved = _resolve(values, values["thinking_policy"], fam.POLICIES.get(arm_id), node_name)
            assert {k: resolved.get(k) for k in ("thinking_budget_tokens", "chat_template_kwargs", "max_tokens")} == dry.expected_node_decoding(arm_id)[node_name], (arm_id, node_name)


# ---- recovery: the generic lib is wired, EMPTY now ---------------------------------------------------------------------------------------


def _snapshot() -> dict:
    return {"schema": "saea-recovery-predecessor-snapshot-v1", "run_id": fam.CELLS["arm"]["run"], "attempt_id": fam.CELLS["arm"]["attempt"], "state": "OPENED",
            "actual_calls": 700, "actual_audio_seconds": 1900.5, "reserved_calls": fam.generation_calls("arm"), "reserved_audio_seconds": float(fam.audio_cap("arm")),
            "fit": {"run_id": fam.CELLS["arm"]["fit_run"], "attempt_id": fam.CELLS["arm"]["fit_attempt"], "attempt_record_present": False, "prepared_dir_present": True,
                    "prepared_request_fit_envelopes": 700}}


def _recovery_input() -> dict:
    return {"recovered_at": "2026-10-25", "ledger_title": "the column flight re-registration", "agent": "the NX-T R2b recovery agent", "reason": "host restart",
            "root_cause": "infrastructure, not the cell", "fix": "none in the cell", "decision": "owner decision 309 A"}


def test_recovery_is_empty_now_and_the_rec1_path_is_data_driven(tmp_path):
    assert fam.RECOVERIES == {} and fam.rcv.REC == "-rec1"
    assert fam.plan_file_name("arm", "generation") == "generation-plan-registered-v1.json" and fam.superseded_plan_file_names("arm") == []
    assert fam.predecessor_spend("arm") == (0, 0.0) and fam.cumulative_budget("arm", 100, 50.0) == (100, 50)
    root = tmp_path / "repo"
    (root / fam.PACKAGE).mkdir(parents=True)
    (root / fam.PREDECESSOR_SNAPSHOT["arm"]).write_text(json.dumps(_snapshot()), encoding="utf-8")
    (root / fam.RECOVERY_INPUT["arm"]).write_text(json.dumps(_recovery_input()), encoding="utf-8")
    loaded = fam._load_recoveries(root)
    assert set(loaded) == {"arm"} and loaded["arm"]["predecessors"][0]["contacts_spent"] == 700 and loaded["arm"]["recovery_index"] == 1
    fam.rcv.validate_recovery(loaded["arm"])
    assert fam._load_recoveries(tmp_path) == {}
    bad = _recovery_input()
    bad.pop("root_cause")
    with pytest.raises(ValueError, match="root_cause"):
        fam.build_arm_recovery(bad, _snapshot())


def test_the_writer_recovery_text_and_flags_are_wired():
    import nxt_r2b_write_registration as writer

    ids = writer.identities(REPO)
    assert writer.recovery_blocks(REPO, ids, "x", "2026-10-25T00:00:00+00:00", "abc", "/wt", "br") == {}
    text = writer.recovery_sequence_text(ids)
    assert "recovery-input-arm-v1.json" in text and "predecessor-snapshot-arm-rec1-v1.json" in text and "NXT2B_KINDS=arm" in text and "arm-only" in text
    out = subprocess.run([sys.executable, "-B", str(NX / "nxt_r2b_write_registration.py"), "--help"], capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0
    for flag in ("--append-recovery-ledger", "--recovery-registered-at", "--recovery-base-commit", "--study-commit", "--append-ledger", "--registered-at"):
        assert flag in out.stdout
    assert "--geometry" not in out.stdout                                                  # R2b has one geometry


def test_the_mint_supersedes_only_the_first_registration_receipt(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    import nxt_r2b_mint_receipt as mint

    first = fam.eligible_run_ids()
    longer = first + [fam.CELLS["arm"]["fit_run"].replace("-FIT-", "-FIT-REC1-")]
    path = tmp_path / "root-admission-v1.json"
    path.write_text(json.dumps({"decision_id": fam.DECISION_ID, "eligible_run_ids": first}), encoding="utf-8")
    monkeypatch.setattr(fam, "eligible_run_ids", lambda: longer)
    assert mint.check_supersedable(str(path)) == first
    for bad in ({"decision_id": "other", "eligible_run_ids": first}, {"decision_id": fam.DECISION_ID, "eligible_run_ids": longer},
                {"decision_id": fam.DECISION_ID, "eligible_run_ids": list(reversed(first))}, {"decision_id": fam.DECISION_ID, "eligible_run_ids": []}):
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(SystemExit):
            mint.check_supersedable(str(path))
    assert mint.backup_name("/d/root-admission-v1.json", datetime(2026, 10, 25, 17, 0, 5, tzinfo=timezone.utc)) == "/d/root-admission-v1.json.superseded-20261025T170005Z-by-rec1.bak"


# ---- the chain, the flip, the read, the queue hook and the launch spec ---------------------------------------------------------------------


def test_the_chain_uses_the_machine_signoff_and_closes_the_rows():
    chain = (NX / "batch_chain_nxt_r2b.sh").read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(NX / "batch_chain_nxt_r2b.sh")], capture_output=True).returncode == 0
    # the sign-off is chain_lib's: reader, conditions (emitted inside the package), marker, 20-minute veto -- and R2's own hand-marker wait is NOT copied
    assert '. "$SP/chain_lib.sh"' in chain
    assert 'wait_or_machine_signoff "bash scripts/flights/nx/nxt_r2b_read.sh smoke" "$MAIN/$SIGNOFF_CONDITIONS" "$SIGNOFF_MARKER" 20' in chain
    assert "wait_signoff()" not in chain and "NXT2_SIGNOFF" not in chain and "sleep 60" not in chain
    assert "SIGNOFF_MARKER=/home/chao/nxt2b-decode-signoff.marker" in chain and "SIGNOFF_CONDITIONS=%s" in chain and "f.SIGNOFF_CONDITIONS" in chain
    assert "close_rows_after_seal" in chain and "close_rows $SMOKE_CLOSE_IDS" in chain and "close_rows $ALL_CLOSE_IDS" in chain
    for needle in ("smoke|arm|arm-only|all) export BATCH_SESSION=$THINK_SESSION", "arm-only) run_driver arm", "use arm-only", "exit 9", '"$SMOKE_STATE" = sealed', "COMPLETED",
                   "no sign-off marker",
                   "serving_swap.sh \"$SWAP_TARGET\"", "nxt_r2b_family", "NXT2B_SIGNOFF_WAIT_SECONDS"):
        assert needle in chain, needle
    assert "SHORT=nxt2b" in chain and "/home/chao/$SHORT-flight-commit.txt" in chain and 'spec["attempt"]' in chain and "gen_attempt_id" in chain
    assert "generation-v1" not in chain and "nxt_r1" not in chain and "nxt_r2_" not in chain.replace("nxt_r2b_", "")
    # unlike R2's `all`, every segment swaps to the raised-cap session itself when it is not resident
    assert chain.count("serving_swap.sh") >= 1 and "is not resident; swapping to" in chain and "arm-only: session" not in chain


def test_the_flip_read_and_repin_scripts_consume_the_family_record():
    flip, read, repin = [(NX / n).read_text(encoding="utf-8") for n in ("nxt_r2b_flip.sh", "nxt_r2b_read.sh", "nxt_r2b_repin_cell.sh")]
    for script in ("nxt_r2b_flip.sh", "nxt_r2b_read.sh", "nxt_r2b_repin_cell.sh", "batch_chain_nxt_r2b.sh"):
        assert subprocess.run(["bash", "-n", str(NX / script)], capture_output=True).returncode == 0
    assert "PLAN_REC=" in flip and "rec_suffix" in flip and 'NXT2B_KINDS:-"smoke arm"' in flip and "nxt_r2b_family" in flip and "nxt_r1" not in flip
    assert "SLUG=nxt-r2b-solver-budget-fold-b" in flip and "PKGN=slurp-nxt-r2b-solver-budget-fold-b-v1" in flip and "SHORT=nxt2b" in flip
    assert "generation-v1" not in read and "nxt_r2b_family" in read and "SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1" in read
    assert "slurp_nxt_r2b_solver_budget_column_read.py" in read and "perception-branches" in read and "slurp_nxt_thinking_budget_column_read.py" not in read
    assert "NXT2B_KIND" in repin and "nxt-r2b-solver-budget-fold-b" in repin and "2026-10-17" in repin and "2026-10-15" not in repin
    # the three read stages and the cell identities agree with the family
    assert re.search(r'STAGE=\$\{1:-read\}', read) and '"$STAGE" = "columns"' in read


def _hook(tmp_path, chain_lines, *, stamp="2026-10-17T12:40:00Z", wait="3", poll="0.2", launch=None):
    out, chain = tmp_path / "queue.out", tmp_path / "chain.out"
    chain.write_text("\n".join(chain_lines) + ("\n" if chain_lines else ""), encoding="utf-8")
    ran = tmp_path / "ran.txt"
    launch = launch or f"echo launched-from $(pwd) > {ran}"
    env = dict(os.environ, NXT2B_HOOK_CHAIN_OUT=str(chain), NXT2B_HOOK_OUT=str(out), NXT2B_HOOK_MAIN=str(tmp_path), NXT2B_HOOK_POLL_SECONDS=poll,
               NXT2B_HOOK_MAX_WAIT_SECONDS=wait, NXT2B_HOOK_LAUNCH_CMD=launch)
    done = subprocess.run(["bash", str(REPO / "scripts/flights/batch/queue/queue_nxt2b_after_nxt2.sh"), *([stamp] if stamp else [])], capture_output=True, text=True, env=env, timeout=60)
    return done, out.read_text(encoding="utf-8") if out.exists() else "", ran


def test_the_queue_hook_launches_only_after_a_clean_r2_exit_later_than_the_stamp(tmp_path):
    script = REPO / "scripts/flights/batch/queue/queue_nxt2b_after_nxt2.sh"
    assert subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode == 0
    text = script.read_text(encoding="utf-8")
    assert "CHAIN_NXT2_EXIT" in text and "/home/chao/nxt2-chain.out" in text and "/home/chao/nxt2b-queue.out" in text and "108000" in text and "POLL_SECONDS:-60" in text
    assert "package_launch.sh scripts/flights/nx/nxt_r2b_launch_spec.json --from flip --until chain" in text and "exit 9" in text
    # (a) an rc=0 exit stamped AFTER the start stamp launches (from the master checkout); an older rc=0 line alone does not
    (tmp_path / "a").mkdir()
    done, log, ran = _hook(tmp_path / "a", ["CHAIN_NXT2_EXIT rc=0 2026-10-17T12:50:00Z"])
    assert done.returncode == 0 and ran.is_file() and "launching NX-T R2b" in log and "launcher exit rc=0" in log
    (tmp_path / "b").mkdir()
    done, log, ran = _hook(tmp_path / "b", ["CHAIN_NXT2_EXIT rc=0 2026-10-17T09:00:00Z"])
    assert done.returncode == 8 and not ran.exists() and "TIMEOUT" in log                       # an older attempt's line is ignored: nothing after the stamp
    # (b) a non-zero R2 exit after the stamp: logged, exit 9, nothing launched
    (tmp_path / "c").mkdir()
    done, log, ran = _hook(tmp_path / "c", ["CHAIN_NXT2_EXIT rc=0 2026-10-17T09:00:00Z", "CHAIN_NXT2_EXIT rc=3 2026-10-17T13:00:00Z"])
    assert done.returncode == 9 and not ran.exists() and "rc=3" in log and "NOT launched" in log
    # (c) the launcher's failure code is the hook's
    (tmp_path / "d").mkdir()
    done, log, ran = _hook(tmp_path / "d", ["CHAIN_NXT2_EXIT rc=0 2026-10-17T13:00:00Z"], launch="exit 4")
    assert done.returncode == 4 and "launcher exit rc=4" in log
    # (d) the first exit line after the stamp decides; usage error without a stamp; a late line is seen while polling
    (tmp_path / "e").mkdir()
    done, _, _ = _hook(tmp_path / "e", [], stamp=None)
    assert done.returncode == 64


def test_the_queue_hook_sees_a_line_that_appears_while_it_polls(tmp_path):
    chain = tmp_path / "chain.out"
    chain.write_text("chain start 2026-10-17T12:40:00Z\n", encoding="utf-8")
    ran = tmp_path / "ran.txt"
    env = dict(os.environ, NXT2B_HOOK_CHAIN_OUT=str(chain), NXT2B_HOOK_OUT=str(tmp_path / "q.out"), NXT2B_HOOK_MAIN=str(tmp_path), NXT2B_HOOK_POLL_SECONDS="0.2",
               NXT2B_HOOK_MAX_WAIT_SECONDS="30", NXT2B_HOOK_LAUNCH_CMD=f"echo ok > {ran}")
    proc = subprocess.Popen(["bash", str(REPO / "scripts/flights/batch/queue/queue_nxt2b_after_nxt2.sh"), "2026-10-17T12:40:00Z"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    import time

    time.sleep(1.0)
    assert proc.poll() is None
    with chain.open("a", encoding="utf-8") as handle:
        handle.write("CHAIN_NXT2_EXIT rc=0 2026-10-17T14:00:00Z\n")
    assert proc.wait(timeout=30) == 0 and ran.is_file()


def test_the_launch_spec_is_the_r2_form_with_the_r2b_names():
    spec = js("scripts/flights/nx/nxt_r2b_launch_spec.json")
    r2 = js("scripts/flights/nx/nxt_r2_launch_spec.json")
    assert spec["schema"] == "saea-package-launch-spec-v1" == r2["schema"] and list(spec["steps"]) == list(r2["steps"]) == ["derive", "write", "countersign", "mint", "commit", "flip", "chain", "read"]
    assert (spec["short"], spec["package"], spec["readiness_dir"]) == ("nxt2b", fam.PKG_NAME, fam.PACKAGE) and spec["launch_id"] == "nxt2b-first-attempt"
    steps = spec["steps"]
    assert steps["derive"]["cmd"].endswith("nxt_r2b_derive_cells.py") and "nxt_r2b_write_registration.py --study-commit {head}" in steps["write"]["cmd"]
    assert "--registered-at {utc}" in steps["write"]["cmd"] and "--append-ledger" in steps["write"]["cmd"]
    assert steps["mint"]["cmd"].endswith("nxt_r2b_mint_receipt.py") and steps["mint"]["done_if"]["contains"] == [fam.CELLS["arm"]["fit_run"]]
    assert steps["mint"]["done_if"]["file"] == fam.DECISION_RELPATH
    assert steps["countersign"]["texts"] == "{readiness_dir}/countersign-row-texts-v1.json" and steps["countersign"]["skip_substrings"] == ["-READ-"]
    assert set(steps["commit"]["paths"]) == {"configs", "docs/exposure-ledger.md", "{readiness_dir}", "{readiness_dir}-preregistration.md"}
    flip = steps["flip"]
    assert flip["script"] == "scripts/flights/nx/nxt_r2b_flip.sh" and flip["package"] == fam.PACKAGE and flip["env"] == {"NXT2B_KINDS": "smoke arm"}
    assert flip["cells"] == [fam.CELLS["smoke"]["cell"], fam.CELLS["arm"]["cell"]] and flip["pins_commit_msg"] == "/home/chao/nxt2b-pins-commit.txt"
    assert flip["flight_commit_file"] == "/home/chao/nxt2b-flight-commit.txt" == steps["chain"]["flight_commit_file"]
    assert flip["pins_commit_text"].rstrip("\n").splitlines()[-1] == "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" and flip["pins_commit_text"].startswith("NX-T R2b")
    assert steps["chain"]["task"] == "SAEA-Chain-NXT2B" and steps["chain"]["wrapper"] == "/home/chao/saea-queue/chain_nxt2b.sh"
    assert steps["read"]["cmd"] == "bash scripts/flights/nx/nxt_r2b_read.sh smoke"
    wrapper = (REPO / "scripts/flights/batch/queue/chain_nxt2b.sh").read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(REPO / "scripts/flights/batch/queue/chain_nxt2b.sh")], capture_output=True).returncode == 0
    assert "batch_chain_nxt_r2b.sh all" in wrapper and "CHAIN_NXT2B_EXIT" in wrapper and "/home/chao/nxt2b-flight-commit.txt" in wrapper
    import package_launch  # noqa: PLC0415

    launch = package_launch.Launch(spec, REPO, dry=True, root_countersign=False, redo=set())
    assert launch.log_path == Path("/home/chao/nxt2b-launch.out") and launch.render("{readiness_dir}") == fam.PACKAGE


def test_every_script_the_spec_names_exists_and_parses():
    for rel in ("nxt_r2b_derive_cells.py", "nxt_r2b_write_registration.py", "nxt_r2b_mint_receipt.py", "nxt_r2b_dry_run.py", "nxt_r2b_family.py"):
        subprocess.run([sys.executable, "-B", "-c", "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())", str(NX / rel)], check=True)
    assert (REPO / fam.READER).is_file() and (REPO / fam.READER_IMPL).is_file()
