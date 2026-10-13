"""NX-T R1: the per-node thinking-policy column on the Thinking core, TRAIN Fold B (owner ruling 304, coordinator approval 2026-10-13).

Model-free and synthetic: the registered package, the derived fragments, the family constants and the reader are checked against each other and against the
268-B Thinking lock cell the column is derived from. No contact, no ledger write, no flip.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "nx", REPO / "scripts" / "flights" / "direct", REPO / "scripts" / "flights" / "tfrl", REPO / "scripts" / "analysis",
               REPO / "scripts" / "checks", REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import derive_tfrl_iteration_cells as dv  # noqa: E402
import nxt_r1_derive_cells as dc  # noqa: E402
import nxt_r1_family as fam  # noqa: E402
import slurp_nxt_thinking_policy_column_read as reader  # noqa: E402
import thinking_system_family as tsf  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.stage3_algorithms import validate_stage3_algorithm_label  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402

PKG = REPO / fam.PACKAGE


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


# ---- ids and shape ----------------------------------------------------------------------------------------------------------------


def test_ids_are_unique_and_follow_the_registered_pattern():
    runs = [fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")]
    assert len(set(runs)) == 4 and fam.eligible_run_ids() == runs
    assert fam.CELLS["arm"]["run"] == "SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1"
    assert fam.CELLS["arm"]["cell"] == "slurp-native-stage3-nxt-r1-thinking-policy-fold-b-v1"
    assert fam.CELLS["smoke"]["cell"] == "slurp-native-stage3-nxt-r1-thinking-policy-fold-b-smoke-4-v1"
    assert fam.CELLS["arm"]["attempt"] == "attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-v1"
    assert fam.PACKAGE == "docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1" and fam.SHORT == "nxt1"
    for key in fam.ALL_KEYS:
        assert experiment(key)["cells"][0]["run_id"] == fam.CELLS[key]["run"]
        assert experiment(key)["cells"][0]["attempt_id"] == fam.CELLS[key]["attempt"]
        assert baseline(key)["native_contact_fit"]["run_id"] == fam.CELLS[key]["fit_run"]
        assert experiment(key)["cells"][0]["baseline_fragment"] == fam.CELLS[key]["baseline"]


def test_the_column_is_five_arms_with_the_delivering_arm_last_and_a_request_identical_twin():
    assert fam.ARM_ORDER == ("perception-off", "solver-off", "both-off", "both-on-twin", "both-on")
    assert fam.DELIVERING == "both-on" == fam.ARM_ORDER[-1] and fam.TWIN == "both-on-twin"
    assert fam.POLICIES == {
        "perception-off": {"perception": {"enable_thinking": False}},
        "solver-off": {"solver": {"enable_thinking": False}},
        "both-off": {"perception": {"enable_thinking": False}, "solver": {"enable_thinking": False}},
    }
    assert fam.K == 5 and fam.CONTACTS_PER_ROW == 10 == 2 + 2 * (fam.K - 1) and fam.PROGRAM == "phase-native-module-v1-c10"
    for key in fam.ALL_KEYS:
        doc = baseline(key)
        assert doc["policy"] == fam.PROGRAM
        block = doc["native_episode"]["consumption_module"]
        assert block["lock"] == "v2.2" and block["review_loop"] == "off"
        assert [c["column_id"] for c in block["columns"]] == list(fam.CANDIDATE_ARMS) and all(c["kind"] == "thinking" for c in block["columns"])
        assert block["thinking_frame"]["twin"] is True and block["thinking_frame"]["max_supplied_items"] == 55
        arms = doc["native_episode"]["roles"]["perception"]["thinking_variants"]["arms"]
        assert [a["arm_id"] for a in arms] == list(fam.ARM_ORDER)
        assert arms[-1] == {"arm_id": "both-on", "deliver": True} and arms[-2] == {"arm_id": "both-on-twin", "replicate_of": "both-on"}
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
        assert config.max_contacts == 10 and group.is_thinking and group.level == 2 and group.branch_ids == fam.ARM_ORDER
        assert values["decoding_params"]["max_tokens"] == 4096 and values["decoding_params"]["thinking_budget_tokens"] == 3072
        assert values["decoding_params"]["chat_template_kwargs"] == {"enable_thinking": True}
        assert values["reasoning_context_policy"] == "drop-reasoning-v1" and values["reasoning_content_guard"] == "refuse-think-marker-in-content"


# ---- the delivering arm is the 268-B lock -------------------------------------------------------------------------------------------


def test_the_cell_is_the_268b_lock_plus_the_column_and_nothing_else():
    parent = js(f"configs/baseline/{tsf.CELLS['lock']['baseline']}.json")
    mine = baseline("arm")
    left, right = dv._leaves(parent), dv._leaves(mine)
    missing = object()
    moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
    assert not [k for k in moved if not any(k == p or k.startswith(p + ".") for p in dc.ALLOWED_DIFFS)]
    # The request-determining content of the delivering arm is the lock's: stores, material, the other roles, normaliser, packets, fit identity of the model.
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
        assert "thinking-system" not in json.dumps(doc).lower().replace("nxt-r1-thinking-policy", "")
    assert len(experiment("arm")["populations"][0]["ids"]) == 1080 and len(experiment("smoke")["populations"][0]["ids"]) == 4


def test_derivation_is_reproducible_in_memory():
    derived = dc.derive(write=False)
    assert derived["program"] == fam.PROGRAM and derived["ceiling"] == fam.CONTACTS_PER_ROW
    for key in fam.ALL_KEYS:
        assert derived["cells"][key]["loader_verification"]["ok"] is True
        on_disk, in_memory = baseline(key), derived["_documents"][key]["baseline"]
        on_disk.pop("prepared_phase_supply", None)
        in_memory.pop("prepared_phase_supply", None)
        assert on_disk == in_memory


# ---- budgets ----------------------------------------------------------------------------------------------------------------------


def test_budgets_follow_the_formula_in_one_place():
    arm = fam.CELLS["arm"]
    assert fam.ARM_MIX_ROWS == 3.25 == 1.0 + 1.0 + 0.6 + 0.6 + 0.05 and fam.ROWS_PER_MINUTE_FULL == 1.84
    assert round(fam.expected_gpu_hours(1080), 2) == 31.79 and fam.planned_gpu_hours(1080) == 41.4 == arm["gpu_hours"]
    assert fam.planned_gpu_hours(1080) == round(__import__("math").ceil(round(1080 * 3.25 / 1.84 / 60 * 1.3 / 0.1, 9)) * 0.1, 1)
    assert fam.CELLS["smoke"]["gpu_hours"] == 0.5
    assert fam.generation_calls("arm") == 1080 * 16 == 17280 and fam.program_calls("arm") == 10800 and fam.generation_calls("smoke") == 64
    assert fam.FALLBACK_CONTACTS_PER_ROW_CEILING == 6 == 2 + 2 + 1 + 1 + 0
    assert fam.fit_contact_cap(1080) == 43200 == 1080 * 10 * tsf.tf.FIT_ENDPOINTS_PER_CONTACT and fam.fit_contact_cap(4) == 160
    assert fam.audio_cap("smoke") == fam.tsf.math.ceil(fam.roster_audio("smoke") * 16 - 1e-9) and fam.audio_cap("arm") == fam.tsf.math.ceil(fam.roster_audio("arm") * 16 - 1e-9)
    # the runner's own plan check: rows x (program contacts + the family fallback of 2) must fit the plan
    assert 1080 * (10 + 2) <= fam.generation_calls("arm")
    for key in fam.ALL_KEYS:
        spec = fam.CELLS[key]
        family, plan = dc.budgets(key)
        assert family["generation_calls_cap"] == plan["planned_model_calls"] == fam.generation_calls(key)
        assert family["fit_endpoint_calls_cap"] == fam.fit_contact_cap(spec["rows"]) == baseline(key)["native_contact_fit"]["contact_cap"]
        assert family["gpu_hours_fit_inclusive"] == plan["planned_gpu_hours"] == spec["gpu_hours"]
        assert experiment(key)["execution_plan"] == plan and experiment(key)["family_budget"] == family


def test_rows_per_minute_equivalents_follow_from_the_cost_mix():
    assert abs(fam.arm_row_equivalent_rows_per_minute("both-on") - 1.84) < 1e-9
    assert abs(fam.arm_row_equivalent_rows_per_minute("perception-off") - 1.84 / 0.6) < 1e-9
    assert abs(fam.PERCEPTION_SHARE_OF_ROW - 50.32 / (50.32 + 35.31)) < 1e-9


# ---- the package ------------------------------------------------------------------------------------------------------------------


def test_stage3_measurement_blocks():
    facts = json.loads((PKG / "registered-facts-v1.json").read_text(encoding="utf-8"))
    blocks = facts["stage3_measurement"]
    arm, smoke = fam.CELLS["arm"]["run"], fam.CELLS["smoke"]["run"]
    assert set(blocks) == {arm, smoke}
    b = blocks[arm]
    assert b["measurement_design"] == "same-flight-node-column" and b["claims_benefit"] is False and b["claim"] == "nominated"
    assert b["primary_metric_key"] == "slu" and b["rows"] == 1080 and b["tuning_roster"] == "none" and b["read_roster"] == fam.READ_ROSTER
    assert b["expected_effect_pp"] == 7.15 >= fam.FLOOR_SLU_PP and b["aa_arm_id"] == "both-on-twin"
    assert b["template_variants"] == {"node": "perception", "candidate_arms": 3, "twin": True} and b["variant_kind"] == "thinking-policy"
    assert b["variant_cost"]["extra_contacts_per_row"] == 8 and b["variant_cost"]["extra_audio_seconds"] > 0
    assert blocks[smoke]["measurement_design"] == "form-proof" and blocks[smoke]["claims_benefit"] is False
    assert facts["blockers"] == [] and {f["id"] for f in facts["findings"]} >= {"no-think-on-a-thinking-only-checkpoint-is-unmeasured",
                                                                               "solver-prompt-differs-by-the-arms-own-note"}
    assert facts["accounting"]["cost_estimate"]["column_flight"]["planned_ceiling_gpu_hours"] == 41.4
    assert facts["thinking_arms"]["both-on"] is None and facts["thinking_arms"]["both-on-twin"] is None


def test_the_effect_floor_gate_resolves_the_declaration(tmp_path):
    """The gate keys on the exposure ledger; the package's DRAFT rows are overlaid on a COPY (this repository's ledger is not touched)."""

    ledger = tmp_path / "ledger.md"
    ledger.write_text((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8") + "\n" + (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8"),
                      encoding="utf-8")
    out = subprocess.run([sys.executable, "-B", str(REPO / "scripts/checks/stage3_effect_floor_check.py"), "--ledger", str(ledger), "--json"],
                         capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0, out.stderr[-500:]
    report = json.loads(out.stdout[out.stdout.find("{"):])
    mine = [c for c in report["in_scope_cells"] if "nxt-r1-thinking-policy" in c["cell_id"]]
    assert {c["cell_id"] for c in mine} == {fam.CELLS[k]["cell"] for k in fam.ALL_KEYS}
    assert not [f for f in report["findings"] if "nxt-r1-thinking-policy" in json.dumps(f)]
    declared = {c["cell_id"]: c["declaration"] for c in mine}
    assert declared[fam.CELLS["arm"]["cell"]]["problems"] == [] and declared[fam.CELLS["arm"]["cell"]]["measurement_design"] == "same-flight-node-column"


def test_plans_protocol_receipt_and_ledger_agree():
    protocol_sha = hashlib.sha256((PKG / "protocol-registered-v1.json").read_bytes()).hexdigest()
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    draft_rows = (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8")
    for key in fam.ALL_KEYS:
        for kind in ("generation", "fit"):
            plan = json.loads((PKG / fam.plan_file_name(key, kind)).read_text(encoding="utf-8"))
            assert plan["expected_session_id"] == fam.THINK_SESSION and plan["protocol_document"]["sha256"] == protocol_sha
            assert plan["thinking_knobs"]["thinking_budget_tokens"] == 3072 and plan["execution_plan"]["split_role"] == "discovery"
            assert plan["no_think_node"]["max_tokens"] == 1024 and plan["arm_order"] == list(fam.ARM_ORDER)
            assert plan["thinking_arms"]["both-off"]["thinking_policy"] == fam.POLICIES["both-off"]
            run = fam.CELLS[key]["run" if kind == "generation" else "fit_run"]
            assert plan["execution_plan"]["run_id"] == run and plan["execution_plan"]["planned_gpu_hours"] == fam.CELLS[key]["gpu_hours"]
            assert draft_rows.count(f"| {run} |") == 1
            assert ledger.count(f"| {run} |") in (0, 1)          # DRAFT rows are appended (and later countersigned) by the coordinator, not by this package
    draft = json.loads((PKG / "root-admission-draft-v1.json").read_text(encoding="utf-8"))
    assert draft["eligible_run_ids"] == fam.eligible_run_ids() and draft["eligible_attempt_ids"] == fam.eligible_attempt_ids()
    assert draft["decision_id"] == fam.DECISION_ID and draft["status"] == "DRAFT-NOT-MINTED" and draft["service"]["expected_session_id"] == fam.THINK_SESSION
    texts = json.loads((PKG / "countersign-row-texts-v1.json").read_text(encoding="utf-8"))
    assert set(texts["rows"]) == set(fam.eligible_run_ids()) | {fam.READ_RUN_ID} and draft_rows.count(f"| {fam.READ_RUN_ID} |") == 1
    recipe = json.loads((PKG / "analysis-recipe-v1.json").read_text(encoding="utf-8"))
    assert recipe["read_run_id"] == fam.READ_RUN_ID and recipe["arms"] == list(fam.ARM_ORDER) and recipe["twin"] == "both-on-twin"
    assert (REPO / fam.PREREG).is_file()
    for line in draft_rows.splitlines():
        if line.startswith("| 2026"):
            assert "DRAFT" in line and "root countersigned" not in line


def test_the_readme_names_the_rulings_the_formula_and_the_shapes():
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    for needle in ("ruling 304", "think-budget-np4", "drop-reasoning-v1", "3072", "4096", "perception-off", "solver-off", "both-off", "both-on-twin", "both-on",
                   "independent chains", "no note sharing", "own Perception note", "3.25", "31.79", "41.4", "ceil_0.1", "NEEDS-THINKING", "NO-RESOLVED-LOSS",
                   "NOT-NEEDED-AT-THE-FLOOR", "flip_package_ext4.sh", "unmeasured", "saea-perception-branch-arms-v5", "byte for byte", "THROUGHPUT"):
        assert needle in readme, needle
    for script in ("nxt_r1_flip.sh", "nxt_r1_read.sh", "nxt_r1_repin_cell.sh", "batch_chain_nxt_r1.sh"):
        assert subprocess.run(["bash", "-n", str(REPO / "scripts/flights/nx" / script)], capture_output=True).returncode == 0
    assert not re.search(r"[^\x00-\x7f]", readme)


def test_the_text_of_the_package_is_english():
    for path in [PKG / n for n in ("README.md", "draft-ledger-rows.md", "countersign-row-texts-v1.json", "registered-facts-v1.json", "protocol-registered-v1.json")]:
        assert not re.search(r"[^\x00-\x7f]", path.read_text(encoding="utf-8")), path
    assert (REPO / fam.READER).read_text(encoding="utf-8").isascii() and (REPO / "scripts/flights/nx/nxt_r1_family.py").read_text(encoding="utf-8").isascii()


# ---- the reader -------------------------------------------------------------------------------------------------------------------


def _rows(ids, tp, fp, fn, intent):
    return {i: {"slu_f1_word_tp": tp[n], "slu_f1_char_tp": tp[n], "slu_f1_word_fp": fp[n], "slu_f1_char_fp": fp[n], "slu_f1_word_fn": fn[n],
                "slu_f1_char_fn": fn[n], reader.INTENT_FIELD: intent[n]} for n, i in enumerate(ids)}


def _arms(ids, loss_both_off=True):
    good = _rows(ids, [3.0] * len(ids), [1.0] * len(ids), [1.0] * len(ids), [1.0] * len(ids))
    bad = _rows(ids, [1.0] * len(ids), [3.0] * len(ids), [3.0] * len(ids), [0.0] * len(ids))
    return {"both-on": good, "both-on-twin": good, "perception-off": good, "solver-off": bad if loss_both_off else good, "both-off": bad if loss_both_off else good}


def test_reader_node_words_against_the_in_flight_twin():
    ids = [f"r{n}" for n in range(40)]
    contrast = reader.paired_contrasts(_arms(ids), ids, lambda sid: sid, seed=1, draws=200)
    assert set(contrast["levels"]) == set(fam.ARM_ORDER) and contrast["versus_delivering"]["both-on-twin"]["slu_f1"]["point_pp"] == 0.0
    words = reader.node_words(contrast)
    assert words["twin_offset_abs_pp"] == 0.0 and words["external_reference_268b"]["twin_offset_slu_pp"] == 1.15
    assert words["words"]["solver-off"]["word"] == "NEEDS-THINKING" and words["words"]["both-off"]["word"] == "NEEDS-THINKING"
    assert words["words"]["perception-off"]["word"] == "NO-RESOLVED-LOSS"
    assert words["words"]["perception-off"]["node"] == "perception" and words["words"]["solver-off"]["node"] == "solver"
    flat = reader.node_words(reader.paired_contrasts(_arms(ids, loss_both_off=False), ids, lambda sid: sid, seed=1, draws=200))
    assert all(v["word"] == "NO-RESOLVED-LOSS" for v in flat["words"].values())
    assert all(v["extra_word"] == reader.EXTRA_WORD for v in flat["words"].values())     # CI of an all-zero delta sits inside the floors
    table = reader.per_scenario_table(_arms(ids), ids, lambda sid: "alarm" if int(sid[1:]) % 2 else "music")
    assert set(table["scenarios"]) == {"alarm", "music"} and table["natural_mixture"]["slu_d_solver-off_pp"] < 0


def _contact(agent, node, tokens, seconds, finish="stop", *, empty=False, reasoning=0, forced=False, marker=False):
    return {"agent_contact_id": agent, "role": node, "prompt_tokens": 3000, "completion_tokens": tokens, "latency_seconds": seconds, "finish_reason": finish,
            "empty_content": empty, "no_json_object": False, "marker_in_content": marker, "reasoning_chars": reasoning, "forced_close": forced}


def _receipt_rows():
    rows = []
    for sid in ("s1", "s2"):
        rows.append({"sample_id": sid, "native_episode_receipt": {"perception_branches": {"branches": [
            {"branch_id": arm, "contact_id": f"{sid}:{arm}:p", "solver_contact_id": f"{sid}:{arm}:s"} for arm in fam.ARM_ORDER]}}})
    return rows


def test_reader_attributes_contacts_to_arms_and_tabulates_the_nodes_and_the_throughput():
    mapping = reader.arm_contact_map(_receipt_rows())
    assert mapping["s1:both-off:p"] == ("both-off", "perception") and mapping["s2:solver-off:s"] == ("solver-off", "solver") and len(mapping) == 20
    contacts = []
    for sid in ("s1", "s2"):
        for arm in fam.ARM_ORDER:
            p_off, s_off = reader.NO_THINK[arm]["perception"], reader.NO_THINK[arm]["solver"]
            contacts.append(_contact(f"{sid}:{arm}:p", "perception", 40 if p_off else 2000, 2.0 if p_off else 50.0, reasoning=0 if p_off else 6000, forced=not p_off and sid == "s1"))
            contacts.append(_contact(f"{sid}:{arm}:s", "solver", 30 if s_off else 1500, 1.5 if s_off else 35.0, reasoning=0 if s_off else 4000))
    contacts.append(_contact("stray", "perception", 10, 1.0))
    by_arm = reader.attribute(contacts, mapping)
    assert set(by_arm) == set(fam.ARM_ORDER) | {"unattributed"} and len(by_arm["both-on"]) == 4
    tables = reader.tables_by_arm(by_arm)
    assert tables["both-off"]["perception"]["mode"] == "no-think" and tables["both-off"]["perception"]["cap"] == 1024
    assert tables["both-on"]["perception"]["mode"] == "think" and tables["both-on"]["perception"]["cap"] == 4096
    assert tables["perception-off"]["perception"]["contacts_with_reasoning_chars"] == 0 and tables["both-on"]["perception"]["forced_closes"] == 1
    assert tables["both-on"]["solver"]["finish_reasons"] == {"stop": 2}
    throughput = reader.throughput_table(tables, 1080)
    assert abs(throughput["arms"]["both-on"]["seconds_per_row"] - 85.0) < 1e-9 and abs(throughput["arms"]["both-on"]["rows_per_minute"] - 4 * 60 / 85.0) < 1e-9
    assert throughput["arms"]["both-on"]["cost_in_both_on_rows"] == 1.0 and throughput["arms"]["both-off"]["cost_in_both_on_rows"] < 0.06
    assert "unattributed" not in throughput["arms"] and throughput["arm_mix_registered_rows"] == 3.25
    smoke = reader.smoke_stage(by_arm)
    assert set(smoke["no_think_nodes"]) == {"perception-off", "solver-off", "both-off"} and smoke["unattributed_contacts"] == 1


def test_a_no_think_arm_that_still_reasons_or_leaks_a_marker_is_visible():
    mapping = reader.arm_contact_map(_receipt_rows())
    leaky = [_contact("s1:both-off:p", "perception", 900, 20.0, finish="length", empty=True, reasoning=3000, marker=True)]
    table = reader.arm_node_table(reader.attribute(leaky, mapping)["both-off"], "both-off")["perception"]
    assert table["mode"] == "no-think" and table["cap_hits"] == 0 and table["finish_reason_length"] == 1 and table["empty_content"] == 1
    assert table["contacts_with_reasoning_chars"] == 1 and table["marker_in_content"] == 1
    flags = reader.sysread.wire_flags({"choices": [{"finish_reason": "stop", "message": {"content": "{}", "reasoning": {
        "reasoning_chars": 12, "forced_close": False, "reasoning_content_sha256": "0" * 64}}}]}, tsf.THINK_BUDGET_MESSAGE)
    assert flags["reasoning_chars"] == 12 and flags["empty_content"] is False


def test_the_reader_loads_only_ids_from_the_sealed_outputs(tmp_path):
    path = tmp_path / "outputs.jsonl"
    rows = [{"sample_id": "s1", "text": "SECRET ANSWER TEXT", "native_episode_receipt": {"perception_branches": {"branches": [
        {"branch_id": "both-on", "contact_id": "c1", "solver_contact_id": "c2", "thinking_policy": None, "note_sha256": "x" * 64}]}}}]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    loaded = reader.load_outputs_rows(path)
    assert "SECRET" not in json.dumps(loaded) and loaded[0]["native_episode_receipt"]["perception_branches"]["branches"][0]["contact_id"] == "c1"


def test_the_structural_dry_run_script_compiles_and_states_the_registered_node_decoding():
    import py_compile

    py_compile.compile(str(REPO / "scripts/flights/nx/nxt_r1_dry_run.py"), cfile=str(Path("/tmp") / "nxt_r1_dry_run.pyc"), doraise=True)
    import nxt_r1_dry_run as dry

    assert dry.expected_node_decoding("both-on") == dry.expected_node_decoding("both-on-twin") == {"perception": dry.ON, "solver": dry.ON}
    assert dry.expected_node_decoding("perception-off") == {"perception": dry.OFF, "solver": dry.ON}
    assert dry.expected_node_decoding("solver-off") == {"perception": dry.ON, "solver": dry.OFF}
    assert dry.expected_node_decoding("both-off") == {"perception": dry.OFF, "solver": dry.OFF}
    assert dry.ON["max_tokens"] == 4096 and dry.OFF["max_tokens"] == 1024 and dry.OFF["thinking_budget_tokens"] is None
