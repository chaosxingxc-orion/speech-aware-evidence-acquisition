"""The 268-B read: the locked SLURP system on the Thinking core (owner decision 268 B, coordinator update of 2026-10-12).

Model-free and synthetic: the registered package, the derived fragments, the family constants and the reader are checked against each other and
against the loop's Instruct lock arm. No contact, no ledger write, no flip.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "direct", REPO / "scripts" / "flights" / "tfrl", REPO / "scripts" / "analysis", REPO / "scripts" / "checks", REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import slurp_system_thinking_core_read as reader  # noqa: E402
import thinking_system_derive_cells as dc  # noqa: E402
import thinking_system_family as fam  # noqa: E402
import tfrl_family as tf  # noqa: E402
import derive_tfrl_iteration_cells as dv  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.stage3_algorithms import validate_stage3_algorithm_label  # noqa: E402

PKG = REPO / fam.PACKAGE


def js(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def baseline(key: str) -> dict:
    return js(f"configs/baseline/{fam.CELLS[key]['baseline']}.json")


def experiment(key: str) -> dict:
    return js(f"configs/experiment/{fam.CELLS[key]['cell']}.json")


# ---- ids and shape ----------------------------------------------------------------------------------------------------------------


def test_ids_are_unique_and_follow_the_registered_pattern():
    runs = [fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")]
    assert len(set(runs)) == 6 and len(set(fam.eligible_run_ids())) == 6 and fam.eligible_run_ids() == runs
    assert fam.CELLS["lock"]["run"] == "SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-LOCK-V1"
    assert fam.CELLS["aa"]["fit_attempt"] == "attempt-slurp-native-stage3-thinking-system-fold-b-aa-fit-v1"
    assert fam.CELLS["smoke"]["cell"] == "slurp-native-stage3-thinking-system-fold-b-smoke-4-v1"
    assert fam.PACKAGE == "docs/readiness/2026-10-12-slurp-system-thinking-core-fold-b-v1"
    for key in fam.ALL_KEYS:
        assert experiment(key)["cells"][0]["run_id"] == fam.CELLS[key]["run"]
        assert experiment(key)["cells"][0]["attempt_id"] == fam.CELLS[key]["attempt"]
        assert baseline(key)["native_contact_fit"]["run_id"] == fam.CELLS[key]["fit_run"]


def test_program_is_the_plain_lock_c2_and_the_twin_is_a_separate_cell():
    assert fam.PROGRAM == "phase-native-module-v1-c2" == tf.CONST_PROGRAM and fam.CONTACTS_PER_ROW == 2 and fam.LOCK == "v2.2"
    assert fam.TWIN_SHAPE == "separate-cell" and fam.ARM_KEYS == ("lock", "aa")
    for key in fam.ALL_KEYS:
        doc = baseline(key)
        assert doc["policy"] == fam.PROGRAM
        block = doc["native_episode"]["consumption_module"]
        assert block["lock"] == "v2.2" and block["columns"] == [] and "supply_frame" not in block
        assert "supply_variants" not in json.dumps(doc["native_episode"]["roles"])
        assert "ace-playbook" not in doc["knowledge_stores"]
        assert doc["native_episode"]["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert doc["native_episode"]["react_exhaustion_policy"] == "continue-without-answer"
        assert doc["native_episode"]["deliver_normaliser"]["normaliser"] == "saea-deliver-normalise-v4g"


# ---- budgets ----------------------------------------------------------------------------------------------------------------------


def test_budgets_follow_the_formula_in_one_place():
    arm = fam.CELLS["lock"]
    assert arm["rows"] == 1080 and fam.generation_calls("lock") == 4320 and fam.generation_calls("smoke") == 16 and fam.program_calls("lock") == 2160
    assert fam.fit_contact_cap(1080) == 8640 == 1080 * 2 * tf.FIT_ENDPOINTS_PER_CONTACT and fam.fit_contact_cap(4) == 32
    assert fam.audio_cap("arm") == 12620 and fam.audio_cap("smoke") == 41
    assert abs(fam.modelled_row_seconds(1) - 51.90) < 0.05            # the pre-smoke model (design record)
    assert abs(fam.row_seconds(1) - 85.63) < 0.05                     # the smoke-measured seconds (sign-off amendment, 2026-10-12)
    assert round(fam.expected_gpu_hours(1080, 1), 2) == 6.42 and fam.planned_gpu_hours(1080, 1) == 8.4 == arm["gpu_hours"] == fam.CELLS["aa"]["gpu_hours"]
    # the design's c3 reference under the pre-smoke model: 5.91 GPU-h expected, 6.6-8.5 h wall
    assert round(fam.C3_EXPECTED_GPU_H, 2) == 5.91 and fam.wall_hours(1080, 2, modelled=True) == (6.6, 8.5)
    for key in fam.ALL_KEYS:
        spec = fam.CELLS[key]
        family, plan = dc.budgets(key)
        assert family["generation_calls_cap"] == plan["planned_model_calls"] == fam.generation_calls(key)
        assert family["fit_endpoint_calls_cap"] == fam.fit_contact_cap(spec["rows"]) == baseline(key)["native_contact_fit"]["contact_cap"]
        assert family["gpu_hours_fit_inclusive"] == plan["planned_gpu_hours"] == spec["gpu_hours"]
        assert experiment(key)["execution_plan"] == plan and experiment(key)["family_budget"] == family


def test_thinking_knobs_are_one_place_and_consistent():
    assert fam.THINK_MAX_TOKENS == fam.THINK_BUDGET_TOKENS + fam.THINK_ANSWER_RESERVE_TOKENS == 4096 and fam.THINK_BUDGET_TOKENS == 3072
    assert fam.REASONING_CONTEXT_POLICY == "drop-reasoning-v1" and set(fam.NODE_MODES.values()) == {"think"}
    assert fam.THINK_MODEL == "q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max4096-v1"
    assert fam.THINK_SESSION == "serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1"
    assert "8192" not in fam.THINK_MODEL and fam.SUPERSEDED_THINK_MODEL.endswith("max8192-v1")
    fragment = js(f"configs/model/{fam.THINK_MODEL}.json")
    assert fragment["decoding_params"]["max_tokens"] == fam.THINK_MAX_TOKENS and "thinking_budget_tokens" not in fragment["decoding_params"]
    for key, value in fam.FRAGMENT_KNOBS.items():
        assert fragment[key] == value
    assert fragment["forced_close_message_sha256"] == __import__("hashlib").sha256(fam.THINK_BUDGET_MESSAGE.encode()).hexdigest()
    assert fragment["decoding_params"]["temperature"] == 0
    args = fragment["server_args"]
    assert args[args.index("--reasoning-budget-message") + 1] == fam.THINK_BUDGET_MESSAGE and args[args.index("--reasoning-format") + 1] == "deepseek"
    assert fragment["reasoning_content_guard"] == "refuse-think-marker-in-content" and fragment["speech_feature_root"] == fam.THINK_PACKET_ROOT
    # the live prompt limit at the registered cap clears the measured Solver prompt maximum; the superseded 8,192 cap would not
    assert fam.PROMPT_LIMIT_THINKING == 17406 > fam.SOLVER_PROMPT_TOKENS_MAX > fam.PROMPT_LIMIT_SUPERSEDED_8192 == 13310
    for key in fam.ALL_KEYS:
        assert "thinking_policy" not in baseline(key)  # the all-nodes-think arm declares no per-node policy
        composed = compose(REPO, fam.THINK_MODEL, fam.DATASET, fam.CELLS[key]["baseline"], fam.CELLS[key]["cell"])
        assert composed.values["decoding_params"]["thinking_budget_tokens"] == 3072 and composed.values["decoding_params"]["chat_template_kwargs"] == {"enable_thinking": True}


def test_the_budget_session_is_registered_as_a_swap_target():
    lib = (REPO / "scripts/flights/batch/serving_lib.sh").read_text(encoding="utf-8")
    assert fam.THINK_SWAP_TARGET in lib and fam.THINK_SESSION in lib and fam.THINK_MODEL in lib
    for script in ("serving_task_entry_think_budget.sh", "serving_monitor_start_think_budget.sh"):
        text = (REPO / "scripts/flights/direct" / script).read_text(encoding="utf-8")
        assert "max8192" not in text.replace("amended", "") or "budget3072" in text
        assert fam.THINK_SESSION in text
        assert subprocess.run(["bash", "-n", str(REPO / "scripts/flights/direct" / script)], capture_output=True).returncode == 0


# ---- pins -------------------------------------------------------------------------------------------------------------------------


def test_the_core_is_the_only_factor_against_the_loops_instruct_lock_arm():
    loop = js("configs/baseline/slurp-native-stage3-tfrl-loop-i3-fold-b-baseline-v1.json")
    mine = baseline("lock")
    left, right = dv._leaves(loop), dv._leaves(mine)
    missing = object()
    moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
    allowed = ("knowledge_stores.ace-playbook", "native_contact_fit", "native_episode.consumption_module", "native_episode.roles.solver.supply_variants",
               "preflight_budget_mode",  # preflight deferral to the exact native gate (coordinator, 2026-10-12)
               "policy", "prepared_phase_supply", "speech_packet_promotion_receipt", "speech_packet_promotion_receipt_sha256", "what_this_is")
    assert not [k for k in moved if not any(k == p or k.startswith(p + ".") for p in allowed)]
    for store in ("intent-boundaries", "slot-contracts", "train-exemplars"):
        assert mine["knowledge_stores"][store] == loop["knowledge_stores"][store]
    assert mine["phase_material"] == loop["phase_material"] and mine["native_episode"]["roles"]["perception"] == loop["native_episode"]["roles"]["perception"]
    assert mine["native_episode"]["deliver_normaliser"] == loop["native_episode"]["deliver_normaliser"]


def test_packets_and_knowledge_pins():
    thinking = js("configs/baseline/slurp-direct-only-fold-b-thinking-baseline-v1.json")
    assert fam.thinking_promotion_sha256() == thinking["speech_packet_promotion_receipt_sha256"]
    for key in fam.ALL_KEYS:
        doc = baseline(key)
        assert doc["speech_packet_promotion_receipt"] == fam.THINK_PROMOTION_RECEIPT
        assert doc["speech_packet_promotion_receipt_sha256"] == thinking["speech_packet_promotion_receipt_sha256"]
        assert fam.THINK_PROMOTION_RECEIPT.startswith(fam.THINK_PACKET_ROOT) and "04ccc72a" not in doc["speech_packet_promotion_receipt"]
        assert fam.FULL_TRAIN_KNOWLEDGE_SNAPSHOT_SHA256 not in json.dumps(doc)
    # the loop's Fold B pools exclude Fold A and Fold B (the exemplar pool is the pool-annotated-exemplars release the loop flies)
    assert "size-pool-annotated-exemplars" in baseline("lock")["knowledge_stores"]["train-exemplars"]["release"]["relpath"]
    assert fam.KNOWLEDGE_SNAPSHOT_SHA256 == "9c64e8ec48a0fce4f172bd190932f99c98c7efa18bbfb14526d54c62fdf7032b"


def test_experiments_swap_only_the_core_and_keep_native_wire_metadata():
    for key in fam.ALL_KEYS:
        doc = experiment(key)
        cell = doc["cells"][0]
        assert cell["model_fragment"] == fam.THINK_MODEL and doc["service_session"] == fam.THINK_SESSION and doc["split_id"] == fam.SPLIT_ID
        assert doc["preserve_wire_responses"] is True        # native role contacts require preserved wire metadata
        assert cell["readiness"]["state"] in ("held", "ready")  # held before the flip, ready after it
        assert validate_stage3_algorithm_label(doc["stage3_algorithm"], cell=fam.CELLS[key]["cell"])[0].id == "shared-rollout"
        assert doc["stage3_algorithm"]["id"] == "shared-rollout"
        roster = json.loads((REPO / fam.ROSTER["smoke" if key == "smoke" else "arm"]).read_text(encoding="utf-8"))
        assert doc["populations"][0]["ids"] == [i["sample_id"] for i in roster["items"]]
        assert doc["population"]["split_identity_hash"] == roster["split_identity_hash"]
        composed = compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], fam.CELLS[key]["cell"])
        assert composed.values["policy"] == fam.PROGRAM and composed.values["decoding_params"]["max_tokens"] == 4096
    assert fam.ROSTER["arm"] == "docs/receipts/rosters/slurp-evo-fold-b-v2.json" and len(experiment("lock")["populations"][0]["ids"]) == 1080
    assert len(experiment("smoke")["populations"][0]["ids"]) == 4


def test_derivation_is_reproducible_in_memory():
    derived = dc.derive(write=False)
    assert derived["program"] == fam.PROGRAM
    for key in fam.ALL_KEYS:
        assert derived["cells"][key]["loader_verification"]["ok"] is True
        on_disk = baseline(key)
        in_memory = derived["_documents"][key]["baseline"]
        on_disk.pop("prepared_phase_supply", None)
        in_memory.pop("prepared_phase_supply", None)
        assert on_disk == in_memory


# ---- the package ------------------------------------------------------------------------------------------------------------------


def test_stage3_measurement_blocks():
    facts = json.loads((PKG / "registered-facts-v1.json").read_text(encoding="utf-8"))
    blocks = facts["stage3_measurement"]
    lock, aa, smoke = (fam.CELLS[k]["run"] for k in ("lock", "aa", "smoke"))
    assert set(blocks) == {lock, aa, smoke}
    for run in (lock, aa):
        assert blocks[run]["measurement_design"] == "cross-flight-with-in-chain-replicate" and blocks[run]["claims_benefit"] is False
        assert blocks[run]["tuning_roster"] == "none" and blocks[run]["read_roster"] == fam.READ_ROSTER and blocks[run]["rows"] == 1080
    assert blocks[lock]["replicate_run_id"] == aa and blocks[aa]["replicate_run_id"] == lock
    assert blocks[lock]["expected_effect_pp"] == fam.BARE_DELTA_SLU_PP == 11.90 and blocks[aa]["expected_effect_pp"] == 0.0
    assert blocks[smoke]["measurement_design"] == "form-proof" and blocks[smoke]["claims_benefit"] is False
    assert facts["accounting"]["twin_shape"] == "separate-cell" and facts["blockers"] == []
    assert {f["id"] for f in facts["findings"]} >= {"twin-is-a-separate-cell", "native-roles-require-preserved-wire", "harness-pass-through-merged"}


def test_plans_protocol_receipt_and_ledger_agree():
    protocol_sha = __import__("hashlib").sha256((PKG / "protocol-registered-v1.json").read_bytes()).hexdigest()
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    for key in fam.ALL_KEYS:
        for kind in ("generation", "fit"):
            plan = json.loads((PKG / fam.plan_file_name(key, kind)).read_text(encoding="utf-8"))
            assert plan["expected_session_id"] == fam.THINK_SESSION and plan["protocol_document"]["sha256"] == protocol_sha
            assert plan["thinking_knobs"]["thinking_budget_tokens"] == 3072 and plan["execution_plan"]["split_role"] == "discovery"
            run = fam.CELLS[key]["run" if kind == "generation" else "fit_run"]
            assert plan["execution_plan"]["run_id"] == run
            assert plan["execution_plan"]["planned_gpu_hours"] == fam.CELLS[key]["gpu_hours"]
            assert ledger.count(f"| {run} |") == 1
    draft = json.loads((PKG / "root-admission-draft-v1.json").read_text(encoding="utf-8"))
    assert draft["eligible_run_ids"] == fam.eligible_run_ids() and draft["eligible_attempt_ids"] == fam.eligible_attempt_ids()
    assert draft["decision_id"] == fam.DECISION_ID and draft["status"] == "DRAFT-NOT-MINTED" and draft["service"]["expected_session_id"] == fam.THINK_SESSION
    texts = json.loads((PKG / "countersign-row-texts-v1.json").read_text(encoding="utf-8"))
    assert set(texts["rows"]) == set(fam.eligible_run_ids()) | {fam.READ_RUN_ID} and ledger.count(f"| {fam.READ_RUN_ID} |") == 1
    recipe = json.loads((PKG / "analysis-recipe-v1.json").read_text(encoding="utf-8"))
    assert recipe["read_run_id"] == fam.READ_RUN_ID and recipe["run_ids"]["read"] == fam.READ_RUN_ID
    # Each row is in exactly one of two states: DRAFT (scope marker "DRAFT -- REGISTERED", no countersignature) or root-countersigned
    # (marker removed, the package text with a real UTC stamp at the front of the notes cell). The six flight rows were countersigned on
    # 2026-10-12 15:27Z; the READ row stays a draft until both arms are sealed (its text says so).
    for line in ledger.splitlines():
        if f"| {fam.READ_RUN_ID} |" in line or any(f"| {r} |" in line for r in fam.eligible_run_ids()):
            cells = [c.strip() for c in line.split("|")]
            notes = cells[15]
            if notes.startswith("DRAFT"):
                assert "root countersigned" not in notes
            else:
                # countersigned (REGISTERED BEFORE ...) or, after the seal, closed by ledger_mark_consumed.py (CONSUMED (...) in front)
                assert notes.startswith(("REGISTERED BEFORE ", "CONSUMED (")) and "root countersigned 2026-" in notes and "<UTC" not in notes
                assert "DRAFT -- REGISTERED" not in line
    assert (REPO / (fam.PREREG)).is_file()


def test_gpu_and_read_texts_name_the_formula_and_the_shapes():
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    for needle in ("268 B", "think-budget-np4", "drop-reasoning-v1", "3072", "4096", "separate cell", "TRANSFERS-ABOVE-BAR", "PARTIAL", "NO-TRANSFER", "HARM",
                   "flip_package_ext4.sh", "5.91", "6.42"):
        assert needle in readme, needle
    for script in ("thinking_system_flip.sh", "thinking_system_read.sh", "thinking_system_repin_cell.sh", "batch_chain_thinking_system.sh"):
        assert subprocess.run(["bash", "-n", str(REPO / "scripts/flights/direct" / script)], capture_output=True).returncode == 0
    assert not re.search(r"[^\x00-\x7f]", readme)


# ---- the reader -------------------------------------------------------------------------------------------------------------------


def _rows(ids, tp, fp, fn, intent):
    return {i: {"slu_f1_word_tp": tp[n], "slu_f1_char_tp": tp[n], "slu_f1_word_fp": fp[n], "slu_f1_char_fp": fp[n], "slu_f1_word_fn": fn[n],
                "slu_f1_char_fn": fn[n], reader.INTENT_FIELD: intent[n]} for n, i in enumerate(ids)}


def test_reader_verdict_words():
    ids = [f"r{n}" for n in range(40)]
    tp = [3.0] * 40
    good = _rows(ids, tp, [1.0] * 40, [1.0] * 40, [1.0] * 40)
    bad = _rows(ids, [1.0] * 40, [3.0] * 40, [3.0] * 40, [0.0] * 40)
    arms = {"lock": good, "aa": good, "inst": bad, "bare": bad}
    contrast = reader.paired_contrasts(arms, ids, lambda sid: sid, seed=1, draws=200)
    assert contrast["slu_f1"]["d_system_lock_vs_inst"]["point_pp"] > 2.5 and contrast["slu_f1"]["o_twin_aa_vs_lock"]["point_pp"] == 0.0
    assert reader.verdict(contrast, 0) == "TRANSFERS-ABOVE-BAR"
    assert reader.verdict(contrast, 1) == "PARTIAL"                  # a delivered reasoning marker withholds the top word
    flat = reader.paired_contrasts({"lock": good, "aa": good, "inst": good, "bare": good}, ids, lambda sid: sid, seed=1, draws=200)
    assert reader.verdict(flat, 0) == "NO-TRANSFER"
    harm = reader.paired_contrasts({"lock": bad, "aa": bad, "inst": good, "bare": good}, ids, lambda sid: sid, seed=1, draws=200)
    assert reader.verdict(harm, 0) == "HARM"
    table = reader.per_scenario_table(arms, ids, lambda sid: "alarm" if int(sid[1:]) % 2 else "music")
    assert set(table["scenarios"]) == {"alarm", "music"} and table["natural_mixture"]["slu_d_system_pp"] > 0


def test_reader_node_table_counts_without_text():
    contacts = [
        {"node": "perception", "prompt_tokens": 3500, "completion_tokens": 4096, "latency_seconds": 90.0, "finish_reason": "length", "empty_content": True,
         "no_json_object": True, "marker_in_content": False, "reasoning_chars": 9000, "forced_close": False},
        {"node": "perception", "prompt_tokens": 3500, "completion_tokens": 700, "latency_seconds": 20.0, "finish_reason": "stop", "empty_content": False,
         "no_json_object": False, "marker_in_content": False, "reasoning_chars": 2000, "forced_close": True},
        {"node": "solver", "prompt_tokens": 10000, "completion_tokens": 300, "latency_seconds": 12.0, "finish_reason": "stop", "empty_content": False,
         "no_json_object": True, "marker_in_content": False, "reasoning_chars": 800, "forced_close": False},
    ]
    table = reader.node_table(contacts)
    assert table["perception"]["contacts"] == 2 and table["perception"]["cap_hits"] == 1 and table["perception"]["empty_content"] == 1
    assert table["perception"]["forced_closes"] == 1 and table["perception"]["finish_reason_length"] == 1 and table["solver"]["no_json_object"] == 1
    flags = reader.wire_flags({"choices": [{"finish_reason": "stop", "message": {"content": "{}", "reasoning_content": "x " + fam.THINK_BUDGET_MESSAGE}}]},
                              fam.THINK_BUDGET_MESSAGE)
    assert flags["forced_close"] is True and flags["empty_content"] is False and "x" not in json.dumps(flags)
    projected = reader.wire_flags({"choices": [{"finish_reason": "length", "message": {"content": "", "reasoning": {
        "reasoning_chars": 321, "forced_close": True, "reasoning_content_sha256": "0" * 64}}}]}, fam.THINK_BUDGET_MESSAGE)
    assert projected["reasoning_chars"] == 321 and projected["forced_close"] is True and projected["empty_content"] is True  # decision 286 form
    assert set(reader.VERDICT_WORDS) == {"TRANSFERS-ABOVE-BAR", "PARTIAL", "NO-TRANSFER", "HARM"}


def test_the_ledger_text_is_english():
    for path in [PKG / n for n in ("README.md", "draft-ledger-rows.md", "countersign-row-texts-v1.json")]:
        assert not re.search(r"[^\x00-\x7f]", path.read_text(encoding="utf-8")), path
    assert io.open(REPO / "scripts/analysis/slurp_system_thinking_core_read.py", encoding="utf-8").read().isascii()
