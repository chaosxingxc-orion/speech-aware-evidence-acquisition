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
    assert len(set(runs)) == 4
    # rec2: the first four ids (the first-registration receipt's list, in its order), then the rec1 FIT run id, then the rec2 FIT run id
    first_fit = fam.RECOVERY_HISTORY["arm"][0]["predecessor_fit_run_id"]
    assert fam.eligible_run_ids() == [fam.CELLS["smoke"]["run"], fam.CELLS["smoke"]["fit_run"], fam.CELLS["arm"]["run"], first_fit,
                                      fam.recovery("arm")["predecessor_fit_run_id"], fam.CELLS["arm"]["fit_run"]]
    assert first_fit == "SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-V1"
    assert fam.recovery("arm")["predecessor_fit_run_id"] == "SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-REC1-V1"
    assert fam.CELLS["arm"]["fit_run"] == "SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-REC2-V1"
    assert fam.CELLS["arm"]["run"] == "SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1"
    assert fam.CELLS["arm"]["cell"] == "slurp-native-stage3-nxt-r1-thinking-policy-fold-b-v1"
    assert fam.CELLS["smoke"]["cell"] == "slurp-native-stage3-nxt-r1-thinking-policy-fold-b-smoke-4-v1"
    assert fam.CELLS["arm"]["attempt"] == "attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec2-v1"
    assert fam.CELLS["arm"]["fit_attempt"] == "attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-fit-rec2-v1"
    # the smoke is NOT recovered: its ids are the first-registration ids
    assert fam.recovery("smoke") is None and fam.CELLS["smoke"]["attempt"] == "attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-smoke-4-generation-v1"
    assert fam.CELLS["smoke"]["fit_run"] == "SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-SMOKE-4-FIT-V1"
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
    assert fam.original_generation_calls("arm") == 1080 * 16 == 17280 and fam.program_calls("arm") == 10800 and fam.generation_calls("smoke") == 64
    # rec2: the registered caps are run-cumulative: the original plan plus BOTH earlier attempts' realised spend (the snapshot receipts': 1,204 + 10,298 calls)
    assert fam.generation_calls("arm") == 17280 + 1204 + 10298 == 28782 and fam.cell_audio_cap("arm") == 83877 == fam.audio_cap("arm") + 33400
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
    # the seal-only completion (package -sealonly-v1) is a third in-scope cell of the same family
    assert {c["cell_id"] for c in mine} == {fam.CELLS[k]["cell"] for k in fam.ALL_KEYS} | {fam.sealonly_spec()["cell"]}
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
    current = {fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")}          # the superseded first FIT run id has no countersign text
    assert set(texts["rows"]) == current | {fam.READ_RUN_ID} and draft_rows.count(f"| {fam.READ_RUN_ID} |") == 1
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


# ---- recoveries: rec1 (owner decision 309 A, a Windows restart) and rec2 (owner ruling 320 B, a mode-A resume under an explicit owner exception) ---------


def _plan(key: str, kind: str) -> dict:
    return json.loads((PKG / fam.plan_file_name(key, kind)).read_text(encoding="utf-8"))


def _snapshots() -> tuple[dict, dict]:
    first, stopped = (json.loads((REPO / rel).read_text(encoding="utf-8")) for rel in fam.PREDECESSOR_SNAPSHOTS["arm"])
    return first, stopped


def test_the_predecessor_spend_is_the_snapshot_receipts_and_it_is_cumulative_over_both_earlier_attempts():
    first, stopped = _snapshots()
    for snap in (first, stopped):
        assert snap["schema"] == "saea-recovery-predecessor-snapshot-v1" and snap["run_id"] == fam.CELLS["arm"]["run"]
    assert first["attempt_id"] == "attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-v1" and first["state"] == "OPENED"
    assert (first["actual_calls"], first["actual_audio_seconds"]) == (1204, 3298.2618750000015)
    assert stopped["attempt_id"] == "attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1"
    assert (stopped["actual_calls"], stopped["actual_audio_seconds"]) == (10298, 30101.20187499958) and stopped["state"] in ("ABORTED", "OPENED", "FAILED")
    assert stopped["fit"]["prepared_request_fit_envelopes"] == 10298
    rec = fam.recovery("arm")
    assert rec["recovery_index"] == 2 and [p["attempt_id"] for p in rec["predecessors"]] == [first["attempt_id"], stopped["attempt_id"]]
    assert [p["contacts_spent"] for p in rec["predecessors"]] == [1204, 10298]
    assert fam.predecessor_spend("arm") == (1204 + 10298, 3298.2618750000015 + 30101.20187499958) and fam.predecessor_spend("smoke") == (0, 0.0)
    assert fam.cumulative_budget("arm", 17280, 50477) == (28782, 83877)
    assert rec["predecessor_fit_run_id"] == stopped["fit"]["run_id"] and rec["predecessor_fit_attempt_id"] == stopped["fit"]["attempt_id"]
    # the rec1 record of the history keeps its own (first-attempt) accounting
    rec1 = fam.RECOVERY_HISTORY["arm"][0]
    assert rec1["recovery_index"] == 1 and [p["contacts_spent"] for p in rec1["predecessors"]] == [1204] and "owner_exception" not in rec1
    assert fam.history_caps("arm", 1, {})["generation_calls_cap"] == 18484 and fam.history_caps("arm", 1, {})["repeated_speech_audio_seconds_cap"] == 53776


def test_the_resume_pin_is_the_trace_sha_the_snapshot_read_and_the_counts_add_up():
    _first, stopped = _snapshots()
    rec = fam.recovery("arm")
    assert rec["owner_exception"] == "owner ruling 320 B of 2026-10-16" and rec["fix_commit"] == "60134738e"
    assert rec["resume_from"] == {"attempt_id": stopped["attempt_id"], "trace_sha256": stopped["trace"]["trace_sha256"]}
    assert re.fullmatch(r"[0-9a-f]{64}", rec["resume_from"]["trace_sha256"]) and rec["resume_from"]["trace_sha256"].startswith("3238cd8a")
    counts = rec["resume_counts"]
    assert counts == stopped["resume"]["counts"] == {"roster": 1080, "kept": 1029, "flown": 51, "partial": 0, "unstarted": 51}
    assert counts["kept"] + counts["flown"] == counts["roster"] == fam.ROWS and rec["resume_mode"] == "resume-mode-A-keep-1029-fly-51"
    assert set(rec["resume_from"]) == {"attempt_id", "trace_sha256"}                     # exactly the mode-A declaration shape core.flight.resume accepts


def test_a_second_recovery_record_is_refused_without_the_owner_exception():
    import copy

    rec = copy.deepcopy(fam.recovery("arm"))
    fam.rcv.validate_recovery(rec)
    for bad in (None, "", "   "):
        broken = {k: v for k, v in rec.items() if k != "owner_exception"}
        if bad is not None:
            broken["owner_exception"] = bad
        with pytest.raises(fam.rcv.RecoveryError, match="owner_exception"):
            fam.rcv.validate_recovery(broken)
    short = dict(rec, predecessors=rec["predecessors"][-1:])
    with pytest.raises(fam.rcv.RecoveryError, match="every earlier attempt"):
        fam.rcv.validate_recovery(short)
    fam.rcv.validate_recovery(copy.deepcopy(fam.RECOVERY_HISTORY["arm"][0]))             # rec1 needs no exception


def test_rec2_plans_carry_the_recovery_block_the_resume_blocks_and_the_run_cumulative_caps():
    gen, fit = _plan("arm", "generation"), _plan("arm", "fit")
    assert fam.plan_file_name("arm", "generation") == "generation-plan-registered-rec2-v1.json"
    assert fam.plan_file_name("arm", "fit") == "fit-plan-registered-rec2-v1.json"
    assert fam.plan_file_name("smoke", "generation") == "smoke-generation-plan-registered-v1.json"
    assert fam.superseded_plan_file_names("arm") == ["generation-plan-registered-v1.json", "fit-plan-registered-v1.json",
                                                      "generation-plan-registered-rec1-v1.json", "fit-plan-registered-rec1-v1.json"]
    for stale in fam.superseded_plan_file_names("arm"):
        assert not (PKG / stale).exists()                                                 # the first-attempt and rec1 plans are removed, consistently
    assert fam.superseded_plan_file_names("smoke") == []
    assert gen["execution_plan"]["attempt_id"] == fam.CELLS["arm"]["attempt"] and fit["execution_plan"]["attempt_id"] == fam.CELLS["arm"]["fit_attempt"]
    assert gen["execution_plan"]["run_id"] == fam.CELLS["arm"]["run"] and fit["execution_plan"]["run_id"] == fam.CELLS["arm"]["fit_run"]
    assert fam.CELLS["arm"]["fit_run"].endswith("-FIT-REC2-V1") and fam.CELLS["arm"]["fit_attempt"].endswith("-fit-rec2-v1")
    for plan in (gen, fit):
        ep = plan["execution_plan"]
        assert ep["planned_speech_audio_seconds"] == 83877 and ep["planned_gpu_hours"] == 41.4      # the GPU ceiling stands; the audio cap grows by the spend
        assert plan["recovery"]["recovery_index"] == 2 and plan["recovery"]["owner_exception"] == "owner ruling 320 B of 2026-10-16"
        assert plan["recovery"]["resume_from"] == fam.recovery("arm")["resume_from"]
        assert [p["contacts_spent"] for p in plan["recovery"]["predecessors"]] == [1204, 10298]
        assert plan["recovery_budget"]["original_plan"] == {"planned_model_calls": 17280, "planned_speech_audio_seconds": 50477}
        assert plan["recovery_budget"]["cumulative_plan"] == {"planned_model_calls": 28782, "planned_speech_audio_seconds": 83877}
        assert plan["recovery_budget"]["failed_attempt_spend"]["attempt_ids"] == [p["attempt_id"] for p in fam.recovery("arm")["predecessors"]]
    assert gen["execution_plan"]["planned_model_calls"] == 28782
    assert fit["execution_plan"]["planned_model_calls"] == 43200 == fam.fit_contact_cap(1080)
    assert gen["resume_from"] == fam.recovery("arm")["resume_from"] and "resume_from" not in fit
    budget = gen["resume_budget"]
    assert (budget["kept_rows"], budget["flown_rows"], budget["flown_worst_case_program_contacts"]) == (1029, 51, 510)
    assert budget["run_cumulative_worst_case_calls"] == 11502 + 510 and budget["cap_calls"] == 28782 and budget["gpu_hours_ceiling"] == 41.4
    assert budget["gpu_hours_expected"] == 1.5
    proof = gen["resume_replay_proof"]
    assert (proof["rows_checked"], proof["rows_failing"], proof["sealed_twice"], proof["model_contacts"]) == (1029, 0, 0, 0)
    assert proof["predecessor_attempts"][0]["trace_sha256"] == gen["resume_from"]["trace_sha256"]
    assert gen["prepared_phase_supply"] == baseline("arm")["prepared_phase_supply"] and gen["prepared_phase_supply"]["sha256"] != "MINTED_AT_THE_FLIP"
    exp = experiment("arm")
    cell = exp["cells"][0]
    assert cell["resume_from"] == fam.recovery("arm")["resume_from"] and "resume_from" not in experiment("smoke")["cells"][0]
    assert exp["execution_plan"]["planned_model_calls"] == 28782 == exp["family_budget"]["generation_calls_cap"] == exp["generation_budget"]["cap"]
    assert exp["family_budget"]["repeated_speech_audio_seconds_cap"] == 83877 and exp["family_budget"]["fit_endpoint_calls_cap"] == 43200
    assert baseline("arm")["native_contact_fit"]["attempt_id"] == fam.CELLS["arm"]["fit_attempt"]
    assert baseline("arm")["native_contact_fit"]["run_id"] == fam.CELLS["arm"]["fit_run"]
    definition = exp["generation_budget"]["definition"]
    assert "Recovery rec2" in baseline("arm")["what_this_is"] and "Recovery rec2" in definition
    assert "51 x 10 = 510 program contacts and nothing else" in definition and "owner ruling 320 B" in definition and "41.4 GPU-h" in definition
    assert "EXPLICIT OWNER EXCEPTION" in exp["failure_policy"]


def test_the_smoke_cell_is_untouched_by_the_recovery():
    for kind in ("generation", "fit"):
        plan = _plan("smoke", kind)
        assert "recovery" not in plan and "recovery_budget" not in plan and "resume_from" not in plan
        assert plan["execution_plan"]["attempt_id"] == fam.CELLS["smoke"]["attempt" if kind == "generation" else "fit_attempt"]
        assert "-rec" not in plan["execution_plan"]["attempt_id"] and "-REC" not in plan["execution_plan"]["run_id"]
    smoke_plan = _plan("smoke", "generation")
    assert smoke_plan["execution_plan"]["planned_model_calls"] == fam.generation_calls("smoke") == 64 and smoke_plan["preparation_base_commit"] == "8132badd8"
    assert "Recovery rec" not in baseline("smoke")["what_this_is"]
    assert baseline("smoke")["native_contact_fit"]["attempt_id"] == fam.CELLS["smoke"]["fit_attempt"]
    assert experiment("smoke")["cells"][0]["attempt_id"] == fam.CELLS["smoke"]["attempt"]


def test_protocol_facts_and_draft_receipt_carry_the_recovery_block_and_the_new_plan_shas():
    protocol = json.loads((PKG / "protocol-registered-v1.json").read_text(encoding="utf-8"))
    assert set(protocol["recovery"]) == {"arm"} and [p["contacts_spent"] for p in protocol["recovery"]["arm"]["predecessors"]] == [1204, 10298]
    assert protocol["cells"]["arm"]["attempt_id"] == fam.CELLS["arm"]["attempt"] and protocol["cells"]["arm"]["fit_run_id"] == fam.CELLS["arm"]["fit_run"]
    assert protocol["cells"]["smoke"]["attempt_id"] == fam.CELLS["smoke"]["attempt"]
    for rec in fam.RECOVERY_HISTORY["arm"]:
        assert rec["predecessor_attempt_id"] in protocol["superseded_attempt_ids"] and rec["predecessor_fit_attempt_id"] in protocol["superseded_attempt_ids"]
    assert "owner ruling 320 B" in protocol["failure_policy"]
    refs = protocol["predecessor_snapshots"]["arm"]
    assert [r["path"] for r in refs] == fam.PREDECESSOR_SNAPSHOTS["arm"]
    assert all(r["sha256"] == hashlib.sha256((REPO / r["path"]).read_bytes()).hexdigest() for r in refs)
    facts = json.loads((PKG / "registered-facts-v1.json").read_text(encoding="utf-8"))
    assert facts["recovery_budget"]["arm"]["cumulative_plan"]["planned_model_calls"] == 28782
    assert facts["accounting"]["arm_generation_calls"] == 28782
    assert facts["resume"]["arm"]["counts"]["kept"] == 1029 and facts["resume"]["arm"]["counts"]["flown"] == 51
    assert facts["resume"]["arm"]["resume_from"] == fam.recovery("arm")["resume_from"]
    assert facts["accounting"]["cost_estimate"]["column_flight"]["planned_ceiling_gpu_hours"] == 41.4
    draft = json.loads((PKG / "root-admission-draft-v1.json").read_text(encoding="utf-8"))
    assert draft["recovery"]["arm"]["recovery_index"] == 2 and draft["budget"]["generation_calls_cap"] == 28782
    for kind in ("generation", "fit"):
        entry = draft["antecedents"]["recovery_plans"]["arm"][kind]
        assert entry["path"] == f"{fam.PACKAGE}/{fam.plan_file_name('arm', kind)}"
        assert entry["sha256"] == hashlib.sha256((PKG / fam.plan_file_name("arm", kind)).read_bytes()).hexdigest()
    for entry in draft["antecedents"]["predecessor_snapshots"]["arm"]:
        assert entry["sha256"] == hashlib.sha256((REPO / entry["path"]).read_bytes()).hexdigest()
    assert draft["supersedes_receipt"]["path"] == fam.DECISION_RELPATH


def test_the_eligible_ids_extend_the_rec1_receipts_list_by_exactly_the_rec2_fit_run_and_attempts():
    ids = fam.eligible_run_ids()
    rec1_list = [fam.CELLS["smoke"]["run"], fam.CELLS["smoke"]["fit_run"], fam.CELLS["arm"]["run"], "SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-V1",
                 "SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-REC1-V1"]
    assert ids == rec1_list + ["SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-REC2-V1"]      # the minted rec1 receipt is a strict prefix: --supersede accepts it
    attempts = fam.eligible_attempt_ids()
    assert attempts[-2:] == [fam.CELLS["arm"]["attempt"], fam.CELLS["arm"]["fit_attempt"]] and len(attempts) == len(set(attempts)) == 8


def test_the_recovery_ledger_block_names_both_predecessors_and_the_countersign_texts_carry_the_exception():
    rows = (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8")
    assert "## Cell NXT-R1 recovery rec2: " in rows and "recovery rec1: " not in rows
    block = rows[rows.index("## Cell NXT-R1 recovery rec2: "):]
    data = [ln for ln in block.splitlines() if ln.startswith("| 2026")]
    assert len(data) == 2 and all(ln.count("|") == 16 for ln in data)
    assert f"| {fam.CELLS['arm']['run']} |" in data[0] and f"| {fam.CELLS['arm']['fit_run']} |" in data[1]
    assert "| no | 28782 | 83877 | 41.4 |" in data[0] and "| no | 43200 | 83877 | 41.4 |" in data[1]
    first, stopped = _snapshots()
    assert "17280 + 11502 = 28782 calls" in data[0] and fam.CELLS["arm"]["attempt"] in data[0]
    assert first["attempt_id"] in data[0] and stopped["attempt_id"] in data[0]                                  # BOTH predecessors are named
    assert "owner ruling 320 B" in data[0] and "SUPERSEDES the rec1 row" in data[0] and "mode A" in data[0]
    assert fam.recovery("arm")["predecessor_fit_run_id"] in data[1] and "SUPERSEDES" in data[1]
    assert "root countersigned" not in block
    texts = json.loads((PKG / "countersign-row-texts-v1.json").read_text(encoding="utf-8"))["rows"]
    for run in (fam.CELLS["arm"]["run"], fam.CELLS["arm"]["fit_run"]):
        assert "RECOVERY rec2" in texts[run] and "11502 calls" in texts[run] and "nxt_r1_mint_receipt.py --supersede" in texts[run]
        assert "owner ruling 320 B" in texts[run] and first["attempt_id"] in texts[run] and stopped["attempt_id"] in texts[run]
        assert fam.CELLS["arm"]["attempt"] in texts[run] and "Resumed in mode A" in texts[run]
    assert "RECOVERY" not in texts[fam.CELLS["smoke"]["run"]]
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    prereg = (REPO / fam.PREREG).read_text(encoding="utf-8")
    for text in (readme, prereg):
        assert "## Recovery rec1: the thinking-policy column flight" in text and "17280 + 1204 = 18484 calls" in text and "Windows Update" in text
        assert "## Recovery rec2: the thinking-policy column flight" in text and "17280 + 11502 = 28782 calls" in text
        assert "explicit owner exception" in text.lower() and "Owner exception: owner ruling 320 B of 2026-10-16" in text
        assert "3238cd8aedb50c8a142b15e321070ffc7cf2cd055088fdcb0aee83d8a0895835" in text and "51 x 10 = 510 program contacts" in text
        assert "kept 1,029 rows" in text and "solver_absent" in text and "60134738e" in text
    assert "Recovery rec2 sequence" in readme and "arm-only" in readme and "NXT1_KINDS=arm" in readme and not re.search(r"[^\x00-\x7f]", prereg)


def test_the_writer_is_idempotent_on_the_recovery_ledger(tmp_path):
    import nxt_r1_write_registration as writer

    ids = writer.identities(REPO)
    blocks = writer.recovery_blocks(REPO, ids, "x", "2026-10-17T04:45:39Z", "abc", "/wt", "br")
    assert set(blocks) == {"arm"} and blocks["arm"].lstrip().startswith("## Cell NXT-R1 recovery rec2: ")
    ledger = tmp_path / "ledger.md"
    ledger.write_text("# Ledger\n", encoding="utf-8")
    assert writer.rcv.append_recovery_ledger_block(ledger, blocks["arm"], ids["arm"]["attempt_id"]) is True
    assert writer.rcv.append_recovery_ledger_block(ledger, blocks["arm"], ids["arm"]["attempt_id"]) is False
    assert ledger.read_text(encoding="utf-8").count(f"| {ids['arm']['run_id']} |") == 1


def test_the_writer_verifies_both_snapshots_and_the_trace_pin_against_a_data_root(tmp_path):
    import nxt_r1_write_registration as writer

    first, stopped = _snapshots()
    run = fam.CELLS["arm"]["run"]
    for snap, trace in ((first, False), (stopped, True)):
        record = tmp_path / "attempts" / run / f"{snap['attempt_id']}.json"
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({"run_id": run, "attempt_id": snap["attempt_id"], "state": "ABORTED", "reserved": {}, "actual": {
            "calls": snap["actual_calls"], "audio_seconds": snap["actual_audio_seconds"]}}), encoding="utf-8")
    trace = tmp_path / "runs" / run / stopped["attempt_id"] / f"{run}.trace.jsonl"
    trace.parent.mkdir(parents=True)
    trace.write_bytes(b"not the registered trace\n")
    with pytest.raises(fam.rcv.RecoveryError, match="predecessor moved"):
        writer.verify_snapshots(REPO, str(tmp_path))
    assert writer.verify_snapshots(REPO, str(tmp_path / "absent"))["arm"][0]["verified"] is False


def test_the_mint_supersedes_only_a_receipt_whose_list_is_a_strict_prefix(tmp_path):
    from datetime import datetime, timezone

    import nxt_r1_mint_receipt as mint

    rec1_list = fam.eligible_run_ids()[:5]
    path = tmp_path / "root-admission-v1.json"
    path.write_text(json.dumps({"decision_id": fam.DECISION_ID, "eligible_run_ids": rec1_list}), encoding="utf-8")
    assert mint.check_supersedable(str(path)) == rec1_list
    path.write_text(json.dumps({"decision_id": fam.DECISION_ID, "eligible_run_ids": rec1_list[:4]}), encoding="utf-8")
    assert mint.check_supersedable(str(path)) == rec1_list[:4]                   # a receipt that was never superseded is a prefix too
    for bad in ({"decision_id": "other", "eligible_run_ids": rec1_list}, {"decision_id": fam.DECISION_ID, "eligible_run_ids": fam.eligible_run_ids()},
                {"decision_id": fam.DECISION_ID, "eligible_run_ids": list(reversed(rec1_list))}, {"decision_id": fam.DECISION_ID, "eligible_run_ids": []}):
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(SystemExit):
            mint.check_supersedable(str(path))
    stamp = datetime(2026, 10, 17, 17, 0, 5, tzinfo=timezone.utc)
    assert mint.backup_name("/d/root-admission-v1.json", stamp) == "/d/root-admission-v1.json.superseded-20261017T170005Z-by-rec2.bak"


def test_the_chain_flip_and_read_scripts_consume_the_family_record():
    nx = REPO / "scripts" / "flights" / "nx"
    chain, flip, read = [(nx / n).read_text(encoding="utf-8") for n in ("batch_chain_nxt_r1.sh", "nxt_r1_flip.sh", "nxt_r1_read.sh")]
    for script in ("batch_chain_nxt_r1.sh", "nxt_r1_flip.sh", "nxt_r1_read.sh", "nxt_r1_repin_cell.sh"):
        assert subprocess.run(["bash", "-n", str(nx / script)], capture_output=True).returncode == 0
    # arm-only: the smoke must be sealed and the marker present; all refuses to re-fly the smoke attempt; the chain flies the family's rec2 ids
    assert "arm|arm-only)" in chain and "arm-only) run_driver arm" in chain and "use arm-only" in chain and "exit 9" in chain
    assert '"$SMOKE_STATE" = sealed' in chain and "COMPLETED" in chain and "no sign-off marker" in chain
    assert 'spec["attempt"]' in chain and "gen_attempt_id" in chain and "generation-v1" not in chain
    # the rec2 resume precondition: the predecessor trace is re-hashed against the family's resume_from, and the rec2 attempt must not exist yet
    assert "resume_from" in chain and "RECOVERIES[\"arm\"][\"resume_from\"]" in chain and "the predecessor trace moved" in chain and "already exists" in chain
    assert "PLAN_REC=" in flip and "rec_suffix" in flip and "NXT1_KINDS" in flip and "generation-v1" not in read and "nxt_r1_family" in read


def test_the_reader_reports_the_kept_and_flown_split_of_a_resume_and_refuses_another_trace():
    resume_from = fam.recovery("arm")["resume_from"]
    manifest = {"predecessor_attempt": {"trace_sha256": resume_from["trace_sha256"], "kept_sample_ids": [f"s{i}" for i in range(1029)], "kept_sample_ids_sha256": "ab" * 32,
                                        "counts": {"kept": 1029}}}
    block = reader.resume_block(manifest, resume_from, 1080)
    assert (block["kept"], block["flown"], block["rows"]) == (1029, 51, 1080)
    with pytest.raises(reader.ReadError, match="registered trace"):
        reader.resume_block({"predecessor_attempt": dict(manifest["predecessor_attempt"], trace_sha256="0" * 64)}, resume_from, 1080)
    with pytest.raises(reader.ReadError, match="kept/flown split"):
        reader.resume_block({"predecessor_attempt": dict(manifest["predecessor_attempt"], kept_sample_ids=[])}, resume_from, 1080)
    text = reader.render_markdown({"resume": block, "arms_nodes": {}})
    assert "1,029 rows kept" in text and "51 rows flown" in text


def test_the_rec2_snapshot_and_replay_proof_tools_compile_and_are_read_only_on_the_data_root():
    for name in ("nxt_r1_rec2_snapshot.py", "nxt_r1_rec2_replay_proof.py"):
        source = (REPO / "scripts/flights/nx" / name).read_text(encoding="utf-8")
        compile(source, name, "exec")
        assert source.isascii() and "write_text" not in source.replace("Path(args.out).write_bytes", "")
    assert "--trace-pin" in (REPO / "scripts/flights/lib/recovery.py").read_text(encoding="utf-8")


def test_the_writer_cli_exposes_the_recovery_flags():
    out = subprocess.run([sys.executable, "-B", str(REPO / "scripts/flights/nx/nxt_r1_write_registration.py"), "--help"], capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0
    for flag in ("--append-recovery-ledger", "--recovery-registered-at", "--recovery-base-commit", "--study-commit"):
        assert flag in out.stdout


# ---- serving geometry of the re-flown arm (owner decision 315 A) --------------------------------------------------------------------------


def _fake_repo(tmp_path: Path, *, lib_row: bool, fragment: dict | None) -> Path:
    """A repo-shaped temp root: scripts/flights/batch/serving_lib.sh with an np6 row (or not) and configs/model with the np6 fragment (or not)."""

    root = tmp_path / "repo"
    (root / "scripts/flights/batch").mkdir(parents=True)
    (root / "configs/model").mkdir(parents=True)
    rows = "    think-budget-np6)\n      G_SID=serving-test-np6\n      G_FRAGMENT=frag-np6\n      G_LABEL=X ;;\n" if lib_row else ""
    (root / "scripts/flights/batch/serving_lib.sh").write_text("case \"$1\" in\n" + rows + "    *) return 1 ;;\nesac\n", encoding="utf-8")
    if fragment is not None:
        (root / "configs/model/frag-np6.json").write_text(json.dumps(fragment), encoding="utf-8")
    return root


def _np6_fragment(**overrides) -> dict:
    doc = json.loads((REPO / "configs/model" / f"{fam.CONTROL_MODEL}.json").read_text(encoding="utf-8"))
    args = list(doc["server_args"])
    args[args.index("-c") + 1], args[args.index("-np") + 1] = "122880", "6"
    doc.update(server_args=args, profile_slot_count=6, geometry_basis="np6 x 20480 test geometry basis")
    doc.update(overrides)
    return doc


def test_the_default_geometry_is_the_control_and_the_selection_file_is_absent():
    g = fam.ACTIVE_GEOMETRY
    assert g["target"] == fam.DEFAULT_GEOMETRY == "think-budget-np4" and not (REPO / fam.GEOMETRY_SELECTION).exists()
    assert (g["session"], g["model_fragment"]) == (fam.CONTROL_SESSION, fam.CONTROL_MODEL) == (fam.tsf.THINK_SESSION, fam.tsf.THINK_MODEL)
    assert (g["slots"], g["slot_tokens"], g["fragment_present"], g["provisional"]) == (4, 24576, True, False)
    assert fam.CELLS["arm"]["model"] == fam.CONTROL_MODEL and fam.CELLS["arm"]["session"] == fam.CONTROL_SESSION
    assert fam.CELLS["smoke"]["model"] == fam.CONTROL_MODEL and fam.THINK_SLOTS == 4
    assert "c98304 np4 x 24,576 max4096" in fam.think_model_text("arm") and fam.think_model_text("arm") == fam.think_model_text("smoke")
    facts = json.loads((PKG / "registered-facts-v1.json").read_text(encoding="utf-8"))
    proof = facts["geometry"]
    assert proof["is_control"] is True and proof["moved_leaves"] == [] and proof["stray_leaves"] == [] and proof["ok"] is True
    assert proof["allowed_leaves"] == ["server_args", "geometry_basis", "profile_slot_count"]
    assert proof["decoding_knobs_never_move"] == {"reasoning_budget_tokens": 3072, "completion_cap": 4096, "reasoning_context_policy": "drop-reasoning-v1"}
    assert facts["context_fit"]["slot_tokens"] == 24576 and facts["context_fit"]["prompt_limit_tokens"] == fam.PROMPT_LIMIT_THINKING == 17406
    assert facts["context_fit"]["solver_prompt_fits_measured_max"] is True


def test_the_geometry_table_agrees_with_the_serving_lib_row_for_every_target_the_lib_knows():
    table = json.loads(fam.GEOMETRY_TABLE_PATH.read_text(encoding="utf-8"))
    assert table["default"] == fam.DEFAULT_GEOMETRY and set(table["targets"]) == {"think-budget-np4", "think-budget-np6", "think-budget-np8"}
    for target, hint in table["targets"].items():
        row = fam._serving_lib_row(target, REPO)
        if target == "think-budget-np4":
            assert row == {"session": hint["session"], "model_fragment": hint["model_fragment"]} and hint["provisional"] is False
        elif row is not None:                                   # the other agent's rows, once they land, must agree with (or replace) the hints
            assert row["session"] == hint["session"] and row["model_fragment"] == hint["model_fragment"]
        else:
            assert hint["provisional"] is True
        assert hint["slots"] * hint["slot_tokens"] in (98304, 147456, 196608)   # 4, 6, 8 slots x 24,576 (the slot never shrinks: max Solver prompt 14,641)


def test_geometry_resolution_is_data_driven_and_refuses_what_is_not_there(tmp_path):
    root = _fake_repo(tmp_path, lib_row=True, fragment=_np6_fragment())
    g = fam.resolve_geometry("think-budget-np6", root)
    assert (g["session"], g["model_fragment"], g["slots"], g["slot_tokens"]) == ("serving-test-np6", "frag-np6", 6, 20480)
    assert g["fragment_present"] is True and g["provisional"] is False and "serving_lib.sh geometry row" in g["source"]
    root2 = _fake_repo(tmp_path / "b", lib_row=False, fragment=None)
    hinted = fam.resolve_geometry("think-budget-np8", root2)
    assert hinted["provisional"] is True and hinted["fragment_present"] is False and (hinted["slots"], hinted["slot_tokens"]) == (8, 24576)
    with pytest.raises(ValueError, match="unknown serving geometry"):
        fam.resolve_geometry("think-budget-np9", root2)
    with pytest.raises(ValueError, match="not present"):
        fam.select_geometry("think-budget-np8", root2, write=True)
    assert not (root2 / fam.GEOMETRY_SELECTION).exists() and fam.ACTIVE_GEOMETRY["target"] == "think-budget-np4"


def test_select_geometry_moves_only_the_arm_and_writes_or_removes_the_selection_file(tmp_path):
    root = _fake_repo(tmp_path, lib_row=True, fragment=_np6_fragment())
    (root / fam.PACKAGE).mkdir(parents=True)
    smoke_before = dict(fam.CELLS["smoke"])
    try:
        g = fam.select_geometry("think-budget-np6", root)
        selection = json.loads((root / fam.GEOMETRY_SELECTION).read_text(encoding="utf-8"))
        assert selection["target"] == "think-budget-np6" and selection["session"] == "serving-test-np6" and "315 A" in selection["decision"]
        assert (fam.THINK_SESSION, fam.THINK_MODEL, fam.THINK_SWAP_TARGET, fam.THINK_SLOTS) == ("serving-test-np6", "frag-np6", "think-budget-np6", 6)
        assert (fam.CELLS["arm"]["session"], fam.CELLS["arm"]["model"]) == ("serving-test-np6", "frag-np6") and fam.CELLS["smoke"] == smoke_before
        assert fam.geometry_of("smoke")["target"] == "think-budget-np4" and g["slot_tokens"] == 20480 and fam.THINK_SLOTS == 6
        assert "c122880 np6 x 20,480 max4096" in fam.think_model_text("arm") and "c98304 np4 x 24,576" in fam.think_model_text("smoke")
        fam.select_geometry("think-budget-np4", root)                        # the control removes the selection file
        assert not (root / fam.GEOMETRY_SELECTION).exists() and fam.CELLS["arm"]["session"] == fam.CONTROL_SESSION
    finally:
        fam.select_geometry("think-budget-np4", REPO, write=False)
    assert fam.ACTIVE_GEOMETRY["target"] == "think-budget-np4" and fam.CELLS["arm"]["model"] == fam.CONTROL_MODEL and fam.THINK_SLOTS == 4


def _overlay_root(tmp_path: Path, fragment: dict) -> Path:
    """A repo-shaped overlay: every entry of the real tree symlinked, except configs/model, which is the real fragments plus the np6 test fragment."""

    root = tmp_path / "overlay"
    root.mkdir(parents=True)
    for entry in REPO.iterdir():
        if entry.name not in ("configs", ".git"):
            (root / entry.name).symlink_to(entry)
    (root / "configs").mkdir()
    for entry in (REPO / "configs").iterdir():
        if entry.name != "model":
            (root / "configs" / entry.name).symlink_to(entry)
    (root / "configs/model").mkdir()
    for entry in (REPO / "configs/model").iterdir():
        (root / "configs/model" / entry.name).symlink_to(entry)
    name = fam.resolve_geometry("think-budget-np6", REPO)["model_fragment"]        # the lib row once it lands, else the provisional hint
    (root / "configs/model" / f"{name}.json").write_text(json.dumps(fragment), encoding="utf-8")
    return root


def test_the_geometry_proof_accepts_only_the_geometry_leaves(tmp_path):
    import nxt_r1_derive_cells as derive

    ok_root = _overlay_root(tmp_path / "ok", _np6_fragment())
    hint = {"model_fragment": fam.resolve_geometry("think-budget-np6", REPO)["model_fragment"]}     # the overlay holds a fragment under this name
    try:
        fam.select_geometry("think-budget-np6", ok_root, write=False)
        proof = derive.geometry_proof(ok_root)
        assert proof["ok"] is True and proof["is_control"] is False and proof["target"] == "think-budget-np6" and proof["stray_leaves"] == []
        assert proof["moved_leaves"] and all(any(k.startswith(p) for p in fam.GEOMETRY_LEAVES) for k in proof["moved_leaves"])
        assert {k.split("[")[0].split(".")[0] for k in proof["moved_leaves"]} <= set(fam.GEOMETRY_LEAVES)
        # a decoding knob riding along with the geometry refuses the derive
        bad = _np6_fragment(decoding_params={**_np6_fragment()["decoding_params"], "seed": 1})
        (ok_root / "configs/model" / f"{hint['model_fragment']}.json").unlink()
        (ok_root / "configs/model" / f"{hint['model_fragment']}.json").write_text(json.dumps(bad), encoding="utf-8")
        fam.select_geometry("think-budget-np6", ok_root, write=False)
        with pytest.raises(SystemExit, match="does not compose|beyond the geometry set"):
            derive.geometry_proof(ok_root)
        # so does a server flag other than the -c / -np values
        flag = _np6_fragment()
        flag["server_args"] = flag["server_args"] + ["--extra-flag"]
        (ok_root / "configs/model" / f"{hint['model_fragment']}.json").unlink()
        (ok_root / "configs/model" / f"{hint['model_fragment']}.json").write_text(json.dumps(flag), encoding="utf-8")
        fam.select_geometry("think-budget-np6", ok_root, write=False)
        with pytest.raises(SystemExit, match="beyond the geometry set"):
            derive.geometry_proof(ok_root)
    finally:
        fam.select_geometry("think-budget-np4", REPO, write=False)
    assert fam.ACTIVE_GEOMETRY["target"] == "think-budget-np4"


def test_the_server_arg_mask_ignores_only_the_slot_geometry_values():
    import nxt_r1_derive_cells as derive

    a = ["-c", "98304", "-np", "4", "-fa", "on"]
    b = ["-c", "122880", "-np", "6", "-fa", "on"]
    assert derive._server_args_without_geometry(a) == derive._server_args_without_geometry(b)
    assert derive._server_args_without_geometry(a) != derive._server_args_without_geometry(["-c", "98304", "-np", "4", "-fa", "off"])


def test_the_derive_and_writer_accept_geometry_and_the_chain_swaps_to_the_chosen_target():
    for script in ("nxt_r1_derive_cells.py", "nxt_r1_write_registration.py"):
        out = subprocess.run([sys.executable, "-B", str(REPO / "scripts/flights/nx" / script), "--help"], capture_output=True, text=True, cwd=REPO)
        assert out.returncode == 0 and "--geometry" in out.stdout and "think-budget-np4" in out.stdout
    chain = (REPO / "scripts/flights/nx/batch_chain_nxt_r1.sh").read_text(encoding="utf-8")
    assert "ARM_SWAP_TARGET" in chain and 'serving_swap.sh "$SWAP_TARGET"' in chain and "ACTIVE_GEOMETRY" in chain
    assert "THINK_SESSION=serving-slurp" not in chain and "f.THINK_SESSION" in chain and "f.CONTROL_SESSION" in chain
    assert "arm geometry" in chain and "exit 9" in chain
