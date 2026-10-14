"""The P3.1 replicate: the locked SLURP system on the Thinking core, DEV-2000-ADDED (registry "P3 programme under decision 299 A").

Model-free and synthetic: the registered package, the derived fragments, the DEV family constants, the DEV packet-driver roster and the DEV reader are
checked against each other and against the sealed Instruct parent cell. No contact, no ledger write, no flip.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "direct", REPO / "scripts" / "flights" / "tfrl", REPO / "scripts" / "analysis", REPO / "scripts" / "checks", REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import derive_tfrl_iteration_cells as dv  # noqa: E402
import slurp_system_thinking_core_dev_read as reader  # noqa: E402
import thinking_system_dev_derive_cells as dc  # noqa: E402
import thinking_system_dev_family as fam  # noqa: E402
import thinking_system_dev_mint_receipt as dmint  # noqa: E402
import thinking_system_family as fold_b  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.stage3_algorithms import validate_stage3_algorithm_label  # noqa: E402

PKG = REPO / fam.PACKAGE
DIRECT = REPO / "scripts" / "flights" / "direct"
DATA = Path(os.environ.get("SPEECHRL_DATA_DIR", "/nonexistent"))


def js(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def baseline(key: str) -> dict:
    return js(f"configs/baseline/{fam.CELLS[key]['baseline']}.json")


def experiment(key: str) -> dict:
    return js(f"configs/experiment/{fam.CELLS[key]['cell']}.json")


def _driver():
    path = REPO / "scripts" / "slurp_fold_preprocess_thinking.py"
    spec = importlib.util.spec_from_file_location("slurp_fold_preprocess_thinking_dev_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---- ids and shape ----------------------------------------------------------------------------------------------------------------


def test_ids_follow_the_registered_pattern_and_the_fold_b_constants_are_untouched():
    runs = [fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")]
    assert len(set(runs)) == 6 and fam.eligible_run_ids() == runs
    assert fam.CELLS["lock"]["run"] == "SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-LOCK-V1"
    assert fam.CELLS["aa"]["fit_attempt"] == "attempt-slurp-native-stage3-thinking-system-dev2000-added-aa-fit-v1"
    assert fam.CELLS["smoke"]["cell"] == "slurp-native-stage3-thinking-system-dev2000-added-smoke-4-v1"
    assert fam.READ_RUN_ID == "SAEA-SLURP-SYSTEM-THINKING-CORE-DEV2000-ADDED-READ-V1" and fam.SHORT == "tsysd"
    assert fam.PACKAGE == "docs/readiness/2026-10-13-slurp-system-thinking-core-dev2000-added-v1"
    # the Fold B family is not edited by this package
    assert fold_b.PACKAGE.endswith("fold-b-v1") and fold_b.ROWS == 1080 and fold_b.CELLS["lock"]["gpu_hours"] == 8.4
    for key in fam.ALL_KEYS:
        assert experiment(key)["cells"][0]["run_id"] == fam.CELLS[key]["run"]
        assert experiment(key)["cells"][0]["attempt_id"] == fam.CELLS[key]["attempt"]
        assert baseline(key)["native_contact_fit"]["run_id"] == fam.CELLS[key]["fit_run"]


def test_program_is_the_plain_lock_c2_and_the_twin_is_a_separate_cell():
    assert fam.PROGRAM == "phase-native-module-v1-c2" and fam.CONTACTS_PER_ROW == 2 and fam.LOCK == "v2.2" and fam.TWIN_SHAPE == "separate-cell"
    for key in fam.ALL_KEYS:
        doc = baseline(key)
        assert doc["policy"] == fam.PROGRAM
        block = doc["native_episode"]["consumption_module"]
        assert block["lock"] == "v2.2" and block["columns"] == [] and "supply_frame" not in block and "template_frame" not in block
        assert "supply_variants" not in json.dumps(doc["native_episode"]["roles"])
        assert doc["native_episode"]["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert doc["native_episode"]["react_exhaustion_policy"] == "continue-without-answer"
        assert doc["native_episode"]["deliver_normaliser"]["normaliser"] == "saea-deliver-normalise-v4g"
        assert doc["preflight_budget_mode"] == "defer-to-native-contact-fit"


# ---- the parent: ledger and sealed manifests ------------------------------------------------------------------------------------------


def test_the_named_module_comp1b_cells_are_a_different_graph_and_the_nx_r5_composed_cell_is_the_parent():
    other = baseline_of("slurp-native-stage3-module-comp1b-aa-dev2000-added-baseline-v1")
    assert other["policy"] == "phase-native-candidates-review-revise-v1" and other["native_episode"]["consumption_module"]["lock"] == "v2.1"
    assert other["native_episode"]["review_loop"] == "on"
    parent = baseline_of(f"slurp-native-stage3-{fam.PARENT_SLUG}-baseline-v1")
    assert parent["policy"] == fam.PROGRAM and parent["native_episode"]["consumption_module"]["lock"] == fam.LOCK and parent["native_episode"]["review_loop"] == "off"
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    line = next(row for row in ledger.splitlines() if row.startswith("|") and f"| {fam.PARENT_RUN} |" in row)
    assert "CONSUMED (sealed)" in line and fam.PARENT_STUDY_COMMIT[:9] in line
    assert f"| {fam.BARE_RUN} |" in ledger
    for run in (fam.PARENT_RUN, fam.BARE_RUN):
        row = next(r for r in ledger.splitlines() if r.startswith("|") and f"| {run} |" in r)
        assert "ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67" in row     # the roster identity hash of this package


def baseline_of(name: str) -> dict:
    return js(f"configs/baseline/{name}.json")


@pytest.mark.skipif(not (DATA / "runs").is_dir(), reason="the data root is not mounted")
def test_the_comparator_runs_are_sealed_completed_on_the_same_split_identity():
    split = js(fam.ROSTER["arm"])["split_identity_hash"]
    for run, attempt, commit in ((fam.COMPARATOR_COLUMN, fam.COMPARATOR_ATTEMPT, fam.PARENT_STUDY_COMMIT), (fam.BARE_RUN, fam.BARE_ATTEMPT, None)):
        manifest = json.loads((DATA / "runs" / run / attempt / f"{run}.run-manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "COMPLETED" and manifest["plan"]["split_identity_hash"] == split
        if commit:
            assert manifest["study_commit"] == commit


# ---- budgets (one place) --------------------------------------------------------------------------------------------------------------


def test_budgets_follow_the_measured_throughput_formula_in_one_place():
    assert fam.MEASURED_ROWS_PER_MINUTE == 1.84 and fam.GPU_MARGIN == 1.3
    assert round(fam.expected_wall_hours(1000), 2) == 9.06 and fam.planned_gpu_hours(1000) == 11.8 == fam.CELLS["lock"]["gpu_hours"] == fam.CELLS["aa"]["gpu_hours"]
    assert fam.planned_gpu_hours(1080) == 12.8 and fam.CELLS["smoke"]["gpu_hours"] == 0.5
    assert fam.generation_calls("lock") == 4000 and fam.generation_calls("smoke") == 16 and fam.program_calls("lock") == 2000
    assert fam.fit_contact_cap(1000) == 8000 == baseline("lock")["native_contact_fit"]["contact_cap"] and fam.fit_contact_cap(4) == 32
    assert fam.audio_cap("arm") == 11935 and fam.audio_cap("smoke") == 33
    for key in fam.ALL_KEYS:
        spec = fam.CELLS[key]
        family, plan = dc.budgets(key)
        assert family["generation_calls_cap"] == plan["planned_model_calls"] == fam.generation_calls(key)
        assert family["fit_endpoint_calls_cap"] == fam.fit_contact_cap(spec["rows"]) == baseline(key)["native_contact_fit"]["contact_cap"]
        assert family["gpu_hours_fit_inclusive"] == plan["planned_gpu_hours"] == spec["gpu_hours"] and plan["split_role"] == "dev"
        assert experiment(key)["execution_plan"] == plan and experiment(key)["family_budget"] == family
    doc = fam.__doc__
    assert "rows / 1.84 / 60 x 1.3" in doc and "1.84 rows per minute" in doc


def test_thinking_knobs_and_model_fragment_are_the_fold_b_ones():
    assert (fam.THINK_BUDGET_TOKENS, fam.THINK_MAX_TOKENS, fam.REASONING_CONTEXT_POLICY) == (3072, 4096, "drop-reasoning-v1")
    assert fam.THINK_MODEL == fold_b.THINK_MODEL and fam.THINK_SESSION == fold_b.THINK_SESSION and fam.THINKING_KNOBS == fold_b.THINKING_KNOBS
    fragment = js(f"configs/model/{fam.THINK_MODEL}.json")
    assert fragment["speech_feature_root"] == fam.THINK_PACKET_ROOT and "promotion" not in json.dumps(fragment)      # the fragment pins the root only
    for key in fam.ALL_KEYS:
        composed = compose(REPO, fam.THINK_MODEL, fam.DATASET, fam.CELLS[key]["baseline"], fam.CELLS[key]["cell"])
        assert composed.values["policy"] == fam.PROGRAM and composed.values["decoding_params"]["max_tokens"] == 4096
        assert composed.values["decoding_params"]["thinking_budget_tokens"] == 3072


# ---- the one factor and the packets ---------------------------------------------------------------------------------------------------


def test_the_core_and_packets_are_the_only_factor_against_the_instruct_parent():
    for key in fam.ALL_KEYS:
        parent = baseline_of(fam.parent_names(fam.CELLS[key]["parent_kind"])["baseline"])
        mine = baseline(key)
        left, right = dv._leaves(parent), dv._leaves(mine)
        missing = object()
        moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
        assert not [k for k in moved if not any(k == p or k.startswith(p + ".") for p in dc.ALLOWED_DIFFS)]
        assert mine["knowledge_stores"] == parent["knowledge_stores"] and mine["phase_material"] == parent["phase_material"]
        assert mine["native_episode"]["roles"] == parent["native_episode"]["roles"]
        assert mine["speech_packet_promotion_receipt"].endswith("slurp-q4km-packets-thinking-gpu-afdaeff6/DEV-2000-ADDED-promotion.json")
        assert fold_b.THINK_PROMOTION_RECEIPT not in json.dumps(mine) and "04ccc72a" not in mine["speech_packet_promotion_receipt"]


def test_the_family_fails_closed_without_the_receipt_and_pins_it_when_present(tmp_path):
    absent = tmp_path / "DEV-2000-ADDED-promotion.json"
    with pytest.raises(SystemExit, match="absent"):
        fam.thinking_promotion_sha256(absent)
    with pytest.raises(SystemExit):
        fam.pinned_promotion_sha256(absent, require=True)
    assert fam.pinned_promotion_sha256(absent) == fam.UNPINNED_SHA
    absent.write_bytes(b"{}\n")
    assert fam.thinking_promotion_sha256(absent) == hashlib.sha256(b"{}\n").hexdigest() == fam.pinned_promotion_sha256(absent)
    state = fam.receipt_state()
    for key in fam.ALL_KEYS:
        pinned = baseline(key)["speech_packet_promotion_receipt_sha256"]
        assert pinned == (state["sha256"] if state["present"] else fam.UNPINNED_SHA)
    facts = json.loads((PKG / "registered-facts-v1.json").read_text(encoding="utf-8"))
    ids = [b["id"] for b in facts["blockers"]]
    assert ids == ([] if state["present"] else ["thinking-dev-promotion-receipt-absent"])


def test_the_mint_refuses_while_the_receipt_is_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(fam, "THINK_PROMOTION_RECEIPT", str(tmp_path / "missing.json"))
    with pytest.raises(SystemExit, match="absent"):
        dmint.require_packets(str(REPO))
    assert dmint.base.expected_eligible(fam) == fam.eligible_run_ids() and len(fam.eligible_run_ids()) == 6


def test_experiments_swap_only_the_core_and_use_the_dev_roster():
    roster = js(fam.ROSTER["arm"])
    for key in fam.ALL_KEYS:
        doc = experiment(key)
        cell = doc["cells"][0]
        assert cell["model_fragment"] == fam.THINK_MODEL and doc["service_session"] == fam.THINK_SESSION and doc["split_id"] == "DEV-2000-ADDED"
        assert doc["preserve_wire_responses"] is True and cell["readiness"]["state"] in ("held", "ready")
        assert validate_stage3_algorithm_label(doc["stage3_algorithm"], cell=fam.CELLS[key]["cell"])[0].id == "shared-rollout"
        ids = doc["populations"][0]["ids"]
        assert ids == [i["sample_id"] for i in roster["items"]][: len(ids)]
        assert len(ids) == fam.CELLS[key]["rows"] and doc["population"]["count"] == len(ids)
        assert all(i.startswith("slurp:devel:") for i in ids)
    assert experiment("lock")["population"]["split_identity_hash"] == roster["split_identity_hash"]
    assert experiment("smoke")["population"]["split_identity_hash"] == fam.PARENT_SMOKE_SPLIT_IDENTITY


def test_derivation_is_reproducible_in_memory():
    derived = dc.derive(write=False)
    assert derived["program"] == fam.PROGRAM
    for key in fam.ALL_KEYS:
        assert derived["cells"][key]["loader_verification"]["ok"] is True
        on_disk, in_memory = baseline(key), derived["_documents"][key]["baseline"]
        on_disk.pop("prepared_phase_supply", None)
        in_memory.pop("prepared_phase_supply", None)
        assert on_disk == in_memory


# ---- the package ------------------------------------------------------------------------------------------------------------------------


def test_stage3_measurement_blocks():
    facts = json.loads((PKG / "registered-facts-v1.json").read_text(encoding="utf-8"))
    blocks = facts["stage3_measurement"]
    lock, aa, smoke = (fam.CELLS[k]["run"] for k in ("lock", "aa", "smoke"))
    assert set(blocks) == {lock, aa, smoke}
    for run in (lock, aa):
        assert blocks[run]["measurement_design"] == "cross-flight-with-in-chain-replicate" and blocks[run]["claims_benefit"] is False
        assert blocks[run]["tuning_roster"] == "none" and blocks[run]["read_roster"] == "SLURP-DEV-2000-ADDED-V1" and blocks[run]["rows"] == 1000
    assert blocks[lock]["replicate_run_id"] == aa and blocks[aa]["replicate_run_id"] == lock
    assert blocks[lock]["expected_effect_pp"] == fam.EXPECTED_EFFECT_PP == 7.15 and blocks[aa]["expected_effect_pp"] == 0.0
    assert blocks[smoke]["measurement_design"] == "form-proof"
    assert facts["instruct_parent"]["run_id"] == fam.PARENT_RUN and {f["id"] for f in facts["findings"]} >= {"instruct-parent-is-nx-r5-composed", "dev-thinking-packets-required"}


def test_plans_protocol_receipt_and_draft_rows_agree():
    protocol_sha = hashlib.sha256((PKG / "protocol-registered-v1.json").read_bytes()).hexdigest()
    rows_text = (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8")
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    for key in fam.ALL_KEYS:
        for kind in ("generation", "fit"):
            plan = json.loads((PKG / fam.plan_file_name(key, kind)).read_text(encoding="utf-8"))
            assert plan["expected_session_id"] == fam.THINK_SESSION and plan["protocol_document"]["sha256"] == protocol_sha
            run = fam.CELLS[key]["run" if kind == "generation" else "fit_run"]
            assert plan["execution_plan"]["run_id"] == run and plan["execution_plan"]["planned_gpu_hours"] == fam.CELLS[key]["gpu_hours"]
            assert plan["execution_plan"]["split_role"] == "dev"
            assert rows_text.count(f"| {run} |") == 1
            assert ledger.count(f"| {run} |") in (0, 1)                 # DRAFT until --append-ledger flights; one row afterwards
    draft = json.loads((PKG / "root-admission-draft-v1.json").read_text(encoding="utf-8"))
    assert draft["eligible_run_ids"] == fam.eligible_run_ids() and draft["eligible_attempt_ids"] == fam.eligible_attempt_ids()
    assert draft["decision_id"] == fam.DECISION_ID and draft["status"] == "DRAFT-NOT-MINTED" and draft["service"]["expected_session_id"] == fam.THINK_SESSION
    texts = json.loads((PKG / "countersign-row-texts-v1.json").read_text(encoding="utf-8"))
    assert set(texts["rows"]) == set(fam.eligible_run_ids()) | {fam.READ_RUN_ID, fam.PACKETS_ROW_ID}
    for needle in (fam.READ_RUN_ID, fam.PACKETS_ROW_ID):
        assert rows_text.count(f"| {needle} |") == 1
    recipe = json.loads((PKG / "analysis-recipe-v1.json").read_text(encoding="utf-8"))
    assert recipe["read_run_id"] == fam.READ_RUN_ID and recipe["comparators"]["bare_thinking_core"].startswith("none")
    assert recipe["comparators"]["instruct_lock_column"]["run_id"] == fam.COMPARATOR_COLUMN and recipe["comparators"]["bare_instruct_core"]["run_id"] == fam.BARE_RUN
    assert (REPO / fam.PREREG).is_file()


def test_readme_names_the_formula_the_chain_and_the_shapes_and_scripts_parse():
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    for needle in ("P3.1", "think-budget-np4", "drop-reasoning-v1", "3072", "4096", "NOMINATED", "NOT-NOMINATED", "HARM", "flip_package_ext4.sh",
                   "--stage dev2000-added", "1.84", "11.8", "tsysd-decode-signoff.marker", "DEV-2000-ADDED-promotion.json", "NX R5 composed"):
        assert needle in readme, needle
    for script in ("thinking_system_dev_flip.sh", "thinking_system_dev_read.sh", "thinking_system_dev_repin_cell.sh", "batch_chain_thinking_system_dev.sh",
                   "direct_fb_packets_gpu.sh", "direct_fb_packets_gpu_dev_task_entry.sh", "direct_fb_packets_gpu_task_entry.sh"):
        assert subprocess.run(["bash", "-n", str(DIRECT / script)], capture_output=True).returncode == 0, script
    chain = (DIRECT / "batch_chain_thinking_system_dev.sh").read_text(encoding="utf-8")
    assert "SHORT=tsysd" in chain and "/home/chao/tsysd-decode-signoff.marker" in chain and "/home/chao/tsysd-flight-commit.txt" in chain
    assert "batch-chain-$SHORT.out" in chain and f"THINK_SESSION={fam.THINK_SESSION}" in chain and "thinking_system_dev_family as fam" in chain
    assert "tsys-" not in chain.replace("tsysd-", "")
    flip = (DIRECT / "thinking_system_dev_flip.sh").read_text(encoding="utf-8")
    assert "SHORT=tsysd" in flip and "SLUG=" + fam.SLUG in flip and "PKGN=" + fam.PKG_NAME in flip and "DEV-2000-ADDED-promotion.json" in flip
    read = (DIRECT / "thinking_system_dev_read.sh").read_text(encoding="utf-8")
    assert fam.READ_RUN_ID in read and "slurp_system_thinking_core_dev_read.py" in read
    repin = (DIRECT / "thinking_system_dev_repin_cell.sh").read_text(encoding="utf-8")
    assert fam.DECISION_ID in repin and "SHORT=tsysd" in repin
    assert not re.search(r"[^\x00-\x7f]", readme)


def test_the_package_text_is_english():
    for path in [PKG / n for n in ("README.md", "draft-ledger-rows.md", "countersign-row-texts-v1.json")]:
        assert not re.search(r"[^\x00-\x7f]", path.read_text(encoding="utf-8")), path
    assert (REPO / "scripts/analysis/slurp_system_thinking_core_dev_read.py").read_text(encoding="utf-8").isascii()


# ---- the packet driver: the DEV roster ------------------------------------------------------------------------------------------------


def test_the_driver_dev_roster_mirrors_the_family_and_leaves_fold_b_alone():
    drv = _driver()
    spec = drv.DEV_SPEC
    assert spec.run_id == fam.PACKETS_ROW_ID and drv.DEV_ROSTER_KEY == fam.PACKETS_ROSTER_KIND
    assert str(spec.promotion_receipt) == fam.THINK_PROMOTION_RECEIPT and str(spec.packet_root) == fam.THINK_PACKET_ROOT
    assert spec.expected_rows == fam.ROWS and spec.split_role == fam.SPLIT_ROLE and spec.dataset_fragment == fam.DATASET
    assert spec.roster_receipt == fam.ROSTER_RECEIPT and spec.row_speech_seconds == 2984 and spec.row_calls == 1000
    assert spec.legacy_cache != drv.GEOMETRIES["gpu"].legacy_cache                  # its own cache: no Fold B entry is foreign to it
    assert drv.ACTIVE_DEV is None and set(drv.ROSTERS) == {"thinking-smoke-4", "thinking-fold-b", fam.PACKETS_ROSTER_KIND, "thinking-test-sample-3010"}   # successor 3 adds the sample roster
    fold_receipt, fold_run = drv.PROMOTION_RECEIPT, drv.RUN_ID
    drv.apply_roster(fam.PACKETS_ROSTER_KIND)
    assert drv.ACTIVE_DEV is spec and drv.RUN_ID == fam.PACKETS_ROW_ID and drv.PROMOTION_RECEIPT == spec.promotion_receipt
    drv.apply_roster("thinking-fold-b")
    assert drv.ACTIVE_DEV is None and drv.PROMOTION_RECEIPT == fold_receipt and drv.RUN_ID == fold_run


def test_the_driver_dev_fragments_compose_and_pass_the_identity_check():
    drv = _driver()
    drv.apply_roster(fam.PACKETS_ROSTER_KIND)
    try:
        _, values = drv.compose_values(REPO)
        drv.check_config_identity(values, REPO)
        assert values["split_role"] == "dev" and values["feature_root"] == fam.THINK_PACKET_ROOT and values["promotion_receipt"] == fam.THINK_PROMOTION_RECEIPT
        assert values["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"] == str(drv.DEV_SPEC.legacy_cache)
        items = drv.select_items(values, drv.ROSTERS[fam.PACKETS_ROSTER_KIND], drv.smoke_ids(REPO))
        assert len(items) == 1000 and all(i["sample_id"].startswith("slurp:devel:") for i in items)
        totals = drv.expected_row_totals(values, drv.AttemptContext(0, 0.0, 0, 0.0, ()))
        assert totals == (1000, 2984)
        assert drv.root_problems(drv.ROSTERS[fam.PACKETS_ROSTER_KIND], packet_root=drv.PACKET_ROOT, legacy_cache=drv.LEGACY_CACHE,
                                 promotion_receipt=Path("/nonexistent/receipt.json"), allow_populated_root=True) == []
    finally:
        drv.apply_roster(None)


def test_the_driver_dev_ledger_gate_wants_the_dev_row(tmp_path):
    drv = _driver()
    drv.apply_roster(fam.PACKETS_ROSTER_KIND)
    try:
        header = ("| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed "
                  "| calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |")
        split = js(fam.ROSTER_RECEIPT)["split_identity_hash"]

        def table(role, notes):
            cells = ["2026-10-13", fam.PACKETS_ROW_ID, "bounded-discovery-probe", "s", "m", "slurp DEV-2000-ADDED 1000", role, split, "no", "1000", "2984", "1.0", "i", "a", notes]
            return header + "\n" + "| --- " * 15 + "|\n| " + " | ".join(cells) + " |\n"

        ledger = tmp_path / "ledger.md"
        ledger.write_text(table("dev", "DRAFT at study commit abc; nothing authorised."), encoding="utf-8")
        state = drv.ledger_state(ledger, split_identity_hash=split)
        assert state["present"] and not state["countersigned"] and not state["problems"]
        ledger.write_text(table("dev", "REGISTERED BEFORE CONTACT (root countersigned 2026-10-13T18:00:00Z by root flight operations)."), encoding="utf-8")
        assert drv.ledger_state(ledger, split_identity_hash=split)["countersigned"] is True
        ledger.write_text(table("discovery", "REGISTERED BEFORE CONTACT (root countersigned 2026-10-13T18:00:00Z)."), encoding="utf-8")
        assert any("split role" in p for p in drv.ledger_state(ledger, split_identity_hash=split)["problems"])
    finally:
        drv.apply_roster(None)


def test_the_gpu_chain_script_accepts_the_dev_stage_with_its_own_roster_output_and_target():
    text = (DIRECT / "direct_fb_packets_gpu.sh").read_text(encoding="utf-8")
    for needle in ("check:dev2000-added|run:dev2000-added|task:dev2000-added", "DEV_ROSTER=thinking-dev2000-added", "THINK_TARGET=think-budget-np4",
                   "slurp-dev2000-added-thinking-packets-gpu-v1", 'run_attempt "$DEV_ROSTER" 26', "direct_fb_packets_gpu_dev_task_entry.sh",
                   "direct-fb-packets-gpu-dev2000-added.recovery"):
        assert needle in text, needle
    entry = (DIRECT / "direct_fb_packets_gpu_dev_task_entry.sh").read_text(encoding="utf-8")
    assert "--run --stage dev2000-added" in entry
    assert "direct_fb_packets_gpu.sh\" --run --stage all" in (DIRECT / "direct_fb_packets_gpu_task_entry.sh").read_text(encoding="utf-8")


# ---- the reader -------------------------------------------------------------------------------------------------------------------------


def _rows(ids, tp, fp, fn, intent):
    return {i: {"slu_f1_word_tp": tp[n], "slu_f1_char_tp": tp[n], "slu_f1_word_fp": fp[n], "slu_f1_char_fp": fp[n], "slu_f1_word_fn": fn[n],
                "slu_f1_char_fn": fn[n], reader.INTENT_FIELD: intent[n]} for n, i in enumerate(ids)}


def test_reader_verdict_words_and_replication_share():
    ids = [f"r{n}" for n in range(40)]
    good = _rows(ids, [3.0] * 40, [1.0] * 40, [1.0] * 40, [1.0] * 40)
    bad = _rows(ids, [1.0] * 40, [3.0] * 40, [3.0] * 40, [0.0] * 40)
    arms = {"lock": good, "aa": good, "inst": bad, "bare": bad}
    contrast = reader.paired_contrasts(arms, ids, lambda sid: sid, seed=1, draws=200)
    assert contrast["slu_f1"]["d_system_lock_vs_inst"]["point_pp"] > 2.5 and "transfer_share_of_bare_delta" not in contrast["slu_f1"]
    assert contrast["slu_f1"]["replication_of_fold_b"]["fold_b_d_system_pp"] == 7.15
    assert reader.verdict(contrast, 0) == "NOMINATED" and reader.verdict(contrast, 1) == "NOT-NOMINATED"
    flat = reader.paired_contrasts({"lock": good, "aa": good, "inst": good, "bare": good}, ids, lambda sid: sid, seed=1, draws=200)
    assert reader.verdict(flat, 0) == "NOT-NOMINATED"
    harm = reader.paired_contrasts({"lock": bad, "aa": bad, "inst": good, "bare": good}, ids, lambda sid: sid, seed=1, draws=200)
    assert reader.verdict(harm, 0) == "HARM"
    assert set(reader.VERDICT_WORDS) == {"NOMINATED", "NOT-NOMINATED", "HARM"}


def test_reader_read_stage_and_render_without_text():
    ids = [f"r{n}" for n in range(40)]
    good = _rows(ids, [3.0] * 40, [1.0] * 40, [1.0] * 40, [1.0] * 40)
    bad = _rows(ids, [1.0] * 40, [3.0] * 40, [3.0] * 40, [0.0] * 40)
    contact = {"node": "perception", "prompt_tokens": 3000, "completion_tokens": 900, "latency_seconds": 30.0, "finish_reason": "stop", "empty_content": False,
               "no_json_object": False, "marker_in_content": False, "reasoning_chars": 100, "forced_close": False}
    flags = {k: {i: {"empty": False, "no_object": False, "leak": False} for i in ids} for k in ("lock", "aa", "inst", "bare")}
    result = reader.read_stage({"lock": good, "aa": good, "inst": bad, "bare": bad}, ids, lambda s: s, lambda s: "alarm" if int(s[1:]) % 2 else "music", flags,
                               {"lock": [contact] * 4, "aa": [contact] * 4}, draws=200)
    assert result["verdict"] == "NOMINATED" and result["comparators"]["bare_thinking_core"] == "none on this roster"
    assert result["reported_beside_the_word"]["decision_299_conditions_on_this_roster"]["lock_completion_rate"] == 1.0
    markdown = reader.render_markdown(result)
    assert "NOMINATED" in markdown and "bare Instruct core" in markdown and markdown.isascii()
    smoke = reader.smoke_stage([contact] * 4)
    assert smoke["projection"]["registered_plan_gpu_hours_per_arm"] == 11.8 and smoke["projection"]["measured_rows_per_minute"] == 1.84


def test_reader_refuses_a_foreign_split_identity():
    with pytest.raises(reader.ReadError):
        reader.assert_split_identity({"plan": {"split_identity_hash": "00"}}, "RUN", js(fam.ROSTER["arm"])["split_identity_hash"])
    reader.assert_split_identity({"plan": {"split_identity_hash": "x"}}, "RUN", "x")
