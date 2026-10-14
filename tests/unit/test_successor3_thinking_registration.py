"""SUCCESSOR 3: the Thinking system (SLURP lock candidate v3.0) on the signed test sample (owner ruling 301 A).

Model-free and synthetic: the registered package, the derived fragments, the family constants, the sample Thinking packets roster of the packet driver, the packets fragments,
the DRAFT v2 allowance, the composed-diff proof and the reader's verdict rule are checked against each other and against the sealed successor-2 / P3.1 cells. No contact, no
ledger write, no flip, no gold.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "nx", REPO / "scripts" / "flights" / "direct", REPO / "scripts" / "flights" / "tfrl", REPO / "scripts" / "analysis",
               REPO / "scripts" / "flights" / "comp1", REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import slurp_successor3_thinking_read as reader  # noqa: E402
import successor3_thinking_derive_cells as dc  # noqa: E402
import successor3_thinking_family as fam  # noqa: E402
import successor3_thinking_packets_fragments as pk  # noqa: E402
import successor3_thinking_preflip_check as pf  # noqa: E402

from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402

PKG = REPO / fam.PACKAGE
NX = REPO / "scripts" / "flights" / "nx"


def js(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def _driver():
    path = REPO / "scripts" / "slurp_fold_preprocess_thinking.py"
    spec = importlib.util.spec_from_file_location("slurp_fold_preprocess_thinking_s3_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---- package shape and identities -------------------------------------------------------------------------------------------------------------------
def test_package_files_exist_and_say_draft():
    names = {"README.md", "registered-facts-v1.json", "protocol-registered-v1.json", "generation-plan-registered-v1.json", "fit-plan-registered-v1.json",
             "analysis-recipe-v1.json", "population-counts-v1.json", "read-qualification-v1.md", "successor-identity-map.json", "root-admission-draft-v1.json",
             "countersign-row-texts-v1.json", "draft-ledger-rows.md"}
    assert names <= {p.name for p in PKG.iterdir()}
    assert (REPO / fam.PREREG).is_file()
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    assert "DRAFT / HELD" in readme and "No smoke cell" in readme and "packets-need-the-v2-allowance" in readme
    # prerequisite 1 is the v2 allowance / decision 308
    assert "1. **packets-need-the-v2-allowance.**" in readme and "decision 308" in readme
    assert json.loads((PKG / "root-admission-draft-v1.json").read_text(encoding="utf-8"))["status"] == "DRAFT-NOT-MINTED"


def test_ids_match_the_signed_allowance_and_the_identity_map():
    allowance = js(fam.ALLOWANCE)
    assert allowance["status"] == "authorised"
    assert allowance["read_run_ids"] == [fam.RUN] and allowance["preparation_run_ids"] == [fam.FIT_RUN]
    assert allowance["analysis_read_run_id_not_a_permission"]["run_id"] == fam.READ_RUN
    exp = js(f"configs/experiment/{fam.CELL}.json")
    cell = exp["cells"][0]
    assert (cell["cell_id"], cell["run_id"], cell["attempt_id"], cell["baseline_fragment"]) == (fam.CELL, fam.RUN, fam.ATTEMPT, fam.BASELINE)
    assert exp["experiment_id"] == fam.RUN and exp["split_id"] == fam.SPLIT_ID and exp["execution_plan"]["split_role"] == "final-report"
    base = js(f"configs/baseline/{fam.BASELINE}.json")
    assert base["native_contact_fit"]["run_id"] == fam.FIT_RUN and base["native_contact_fit"]["attempt_id"] == fam.FIT_ATTEMPT
    assert base["scorers"] == [fam.SCORER, "cost"]
    imap = js(f"{fam.PACKAGE}/successor-identity-map.json")
    assert imap["p31_dev_to_successor3_replacements"]["run_id"] == [fam.SRC["run"], fam.RUN]
    assert imap["contacts_per_row"] == 2 and imap["generation_rows"] == 3010
    assert fam.READ_RUN.endswith("SUCCESSOR3-PAIRED-ANALYSIS-V1") and fam.DECISION_RELPATH.startswith("coordination/")


def test_no_smoke_and_no_twin_cell():
    stray = [p.name for p in (REPO / "configs").rglob("*successor3*") if p.name not in (f"{fam.CELL}.json", f"{fam.BASELINE}.json")]
    assert stray == []
    assert [c["cell"] for c in js(fam.CAMPAIGN_PLAN)["cells"]] == [fam.CELL]
    exp = js(f"configs/experiment/{fam.CELL}.json")
    assert "populations" not in exp and exp["cells"][0]["allowed_execution_stages"] == ["check", "prepare-supply", "worker", "campaign"]
    assert "no smoke" in (PKG / "README.md").read_text(encoding="utf-8").lower()


def test_allowance_pin_is_the_signed_receipt():
    exp = js(f"configs/experiment/{fam.CELL}.json")
    assert exp["owner_allowance"] == {"path": fam.ALLOWANCE, "sha256": hashlib.sha256((REPO / fam.ALLOWANCE).read_bytes()).hexdigest()}
    assert fam.ALLOWANCE == "docs/receipts/owner/2026-10-13-slurp-test-sample-allowance-successor-3.json"
    assert exp["failure_policy"].startswith("ONE ATTEMPT, EVER") and "NO recovery re-registration" in exp["failure_policy"]


# ---- the composed-diff proof ---------------------------------------------------------------------------------------------------------------------
def test_composed_diff_proof_holds_and_matches_the_committed_facts():
    proof = dc.prove()
    assert proof["s3_vs_p31_lock_dev"]["anything_else"] == [] and proof["s3_vs_p31_lock_dev"]["composition_factor"] == []
    assert proof["composition_delta_commutes"]["commutes"] is True
    assert proof["composition_delta_commutes"]["graph_leaves_moved_by_the_core_swap_on_dev"] == proof["composition_delta_commutes"]["successor2_to_successor3_moves_exactly_these"]
    assert proof["mapping_square"]["leaves_only_in_the_p31_to_s3_mapping"] == [] and proof["mapping_square"]["leaves_only_in_the_r5_to_s2_mapping"] == []
    committed = js(f"{fam.PACKAGE}/registered-facts-v1.json")["composed_config_diffs"]
    assert committed["s3_vs_p31_lock_dev"] == proof["s3_vs_p31_lock_dev"]
    assert committed["composition_delta_commutes"] == proof["composition_delta_commutes"]


def test_roster_leaves_equal_successor2_and_core_leaves_equal_p31():
    s2, s3, p31 = (compose(REPO, *_parts(n)).values for n in (fam.S2_CELL, fam.CELL, fam.SRC["cell"]))
    for key in ("split_identity_hash", "items", "count", "runtime_view_sha256", "scorers", "split_role", "d1_media_supplement_sha256"):
        assert s3[key] == s2[key], key
    for key in ("model_lock_key", "server_args", "decoding_params", "reasoning_budget_tokens", "service_session", "preflight_budget_mode"):
        assert s3[key] == p31[key], key
    assert s3["native_episode"]["consumption_module"]["lock"] == fam.LOCK and s3["policy"] == fam.PROGRAM
    assert s3["speech_packet_promotion_receipt"] == fam.THINK_PROMOTION_RECEIPT


def _parts(experiment: str):
    cell = js(f"configs/experiment/{experiment}.json")["cells"][0]
    return cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment


# ---- ceilings -------------------------------------------------------------------------------------------------------------------------------------------
def test_ceilings_from_the_measured_throughput():
    assert fam.planned_gpu_hours(1000) == 11.8 == fam.dev.planned_gpu_hours(1000)
    assert fam.planned_gpu_hours(3010) == 35.5
    assert fam.generation_calls() == 12040 and fam.program_calls() == 6020 and fam.fit_contact_cap() == 24080 and fam.audio_cap() == 32826
    fb = js(f"configs/experiment/{fam.CELL}.json")["family_budget"]
    assert (fb["generation_calls_cap"], fb["fit_endpoint_calls_cap"], fb["gpu_hours_fit_inclusive"], fb["repeated_speech_audio_seconds_cap"]) == (12040, 24080, 35.5, 32826)
    assert js(f"configs/experiment/{fam.CELL}.json")["execution_plan"]["planned_gpu_hours"] == 35.5
    assert js(f"configs/baseline/{fam.BASELINE}.json")["native_contact_fit"]["contact_cap"] == 24080
    v2 = js(pk.V2)["budgets"]
    assert (v2["gpu_hour_cap_per_arm_fit_inclusive"], v2["generation_cap_total"], v2["fit_endpoint_cap_total"], v2["repeated_speech_audio_seconds_cap"], v2["program_contacts_total"]) == (35.5, 12040, 24080, 32826, 6020)


# ---- measurement ---------------------------------------------------------------------------------------------------------------------------------------
def test_measurement_block_is_the_successor2_form_with_the_declared_dev_offset():
    facts = js(f"{fam.PACKAGE}/registered-facts-v1.json")
    block = facts["stage3_measurement"][fam.RUN]
    assert block["measurement_design"] == "cross-flight-no-replicate" and block["claims_benefit"] is False and block["claim"] == "no-harm"
    assert block["comparator_run_id"] == fam.S2_RUN and block["harm_margin_pp"] == 2.5 and block["primary_metric_key"] == "slu"
    off = block["declared_flight_offset"]
    assert (off["slu_pp"], off["intent_pp"]) == (0.6144, 1.6) and (off["signed"]["slu_pp"], off["signed"]["intent_pp"]) == (-0.6144, 1.6)
    assert "LIMITATION" in off["scope"] and "NO in-chain" in off["scope"] or "no in-chain" in off["scope"].lower()
    assert isinstance(block["expected_effect_pp"], float) and block["expected_effect_pp"] > 0
    recipe = js(f"{fam.PACKAGE}/analysis-recipe-v1.json")
    assert recipe["resampling"] == {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20261014, "unit": "prompt cluster (paired)"}
    assert recipe["arms"]["comparator"]["run_id"] == fam.S2_RUN and recipe["read_driver"]["scorer"] == "slurp-slu-official-test"
    assert recipe["verdict_rule"]["words"] == ["NEUTRAL", "HARM", "UNRESOLVED"] and "in_chain" not in json.dumps(recipe["arms"])


def test_reader_verdict_words():
    off = {"slu_pp": 0.6144, "intent_pp": 1.6}
    ok = {"delta_pp": 7.0, "ci95_pp": [5.0, 9.0]}
    assert reader.verdict_word(ok, ok, off) == "NEUTRAL"
    assert reader.verdict_word({"delta_pp": -3.0, "ci95_pp": [-4.0, -1.0]}, ok, off) == "HARM"
    assert reader.verdict_word(ok, {"delta_pp": -2.0, "ci95_pp": [-3.0, -1.7]}, off) == "HARM"
    assert reader.verdict_word({"delta_pp": -1.0, "ci95_pp": [-3.0, 0.5]}, ok, off) == "UNRESOLVED"
    assert reader.verdict_word({"delta_pp": 0.0, "ci95_pp": [-2.0, 2.0]}, ok, off) == "NEUTRAL"
    eq = {"slu_f1": ok, "intent": ok}
    assert reader.beside(ok, ok, eq, off)["gain_reported_not_claimed"] is True
    assert reader.beside({"delta_pp": 0.2, "ci95_pp": [-0.3, 0.7]}, ok, eq, off)["gain_reported_not_claimed"] is False
    assert "NO IN-CHAIN REPLICATE" in reader.LIMITATION


# ---- draft ledger rows and countersign texts --------------------------------------------------------------------------------------------------------
def test_draft_rows_parse_and_agree_with_the_budgets():
    rows = _parse_ledger_tables((PKG / "draft-ledger-rows.md").read_text(encoding="utf-8"))
    by_id = {r["run/experiment id"]: r for r in rows}
    assert set(by_id) == {fam.PACKETS_RUN, fam.RUN, fam.FIT_RUN, fam.READ_RUN}
    for row in by_id.values():
        assert row["consumed"] == "no" and row["split role"] == "final-report"
        assert row["split identity hash"] == "0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9" and ("DRAFT" in row["notes"] or row["scope"].startswith("DRAFT -- REGISTERED"))
    assert (by_id[fam.PACKETS_RUN]["calls"], by_id[fam.PACKETS_RUN]["speech audio seconds"], by_id[fam.PACKETS_RUN]["gpu hours"]) == ("3010", "8207", "1.0")
    assert (by_id[fam.RUN]["calls"], by_id[fam.RUN]["gpu hours"], by_id[fam.RUN]["speech audio seconds"]) == ("12040", "35.5", "32826")
    assert by_id[fam.FIT_RUN]["calls"] == "24080" and by_id[fam.READ_RUN]["execution profile"] == "model-free-check"
    texts = js(f"{fam.PACKAGE}/countersign-row-texts-v1.json")
    assert set(texts["rows"]) == set(by_id) and texts["decision_receipt"] == fam.DECISION_RELPATH


# ---- the packets stage ---------------------------------------------------------------------------------------------------------------------------
def test_packets_roster_definition_matches_the_family():
    drv = _driver()
    spec = drv.SAMPLE_SPEC
    assert drv.ROSTERS[drv.SAMPLE_ROSTER_KEY].dev is spec and drv.SAMPLE_ROSTER_KEY == fam.PACKETS_ROSTER_KIND
    assert (spec.run_id, spec.sidecar_fragment, spec.experiment_fragment, spec.dataset_fragment) == (fam.PACKETS_RUN, fam.PACKETS_SIDECAR_FRAGMENT, fam.PACKETS_EXPERIMENT_FRAGMENT, fam.DATASET)
    assert (spec.sample_id_prefix, spec.split_role, spec.expected_rows, spec.row_calls, spec.row_speech_seconds) == ("slurp:test:", "final-report", 3010, 3010, 8207)
    assert str(spec.promotion_receipt) == fam.THINK_PROMOTION_RECEIPT and str(spec.legacy_cache) == fam.PACKETS_LEGACY_CACHE and str(spec.packet_root) == fam.THINK_PACKET_ROOT
    assert drv.ROSTERS[drv.SAMPLE_ROSTER_KEY].default_attempt_id == fam.PACKETS_ATTEMPT
    # the Fold B and DEV rosters and receipts are unchanged and distinct
    assert drv.DEV_SPEC.promotion_receipt != spec.promotion_receipt and drv.DEV_SPEC.legacy_cache != spec.legacy_cache
    assert str(drv.DEV_SPEC.promotion_receipt).endswith("DEV-2000-ADDED-promotion.json")
    assert drv.ROSTERS["thinking-fold-b"].dev is None and drv.ROSTERS["thinking-smoke-4"].dev is None


def test_packets_fragments_compose_and_pass_the_config_identity_check():
    drv = _driver()
    drv.apply_geometry("gpu")
    drv.apply_roster(drv.SAMPLE_ROSTER_KEY)
    _, values = drv.compose_values(REPO)
    drv.check_config_identity(values, REPO)
    assert values["split_role"] == "final-report" and values["owner_allowance"]["path"] == pk.V2
    assert values["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"] == fam.PACKETS_LEGACY_CACHE and len(values["items"]) == 3010
    assert all(str(item["sample_id"]).startswith("slurp:test:") for item in values["items"])
    assert drv.smoke_ids(REPO) == []


def test_packets_guard_refuses_while_the_v2_pin_is_zero_and_is_never_bypassed():
    drv = _driver()
    drv.apply_geometry("gpu")
    drv.apply_roster(drv.SAMPLE_ROSTER_KEY)
    _, values = drv.compose_values(REPO)
    problems = drv.allowance_problems(values, repo=REPO)
    v2 = js(pk.V2)
    if v2["status"] == "authorised":
        # owner decision 308 A (2026-10-14): the v2 receipt is signed and pinned; the contract accepts the packets pass
        assert problems == [], problems
        assert values["owner_allowance"]["sha256"] == hashlib.sha256((REPO / pk.V2).read_bytes()).hexdigest() != fam.ZERO
        assert v2["signature"]["status"] == "authorised" and v2["signature"].get("signed_by")
    else:
        assert len(problems) == 1 and "require_owner_split_allowance" in problems[0]
        assert values["owner_allowance"]["sha256"] == fam.ZERO
        assert v2["signature"]["status"] == "DRAFT: awaiting owner decision 308"
    # every other roster is not owner-allowance gated
    drv.apply_roster("thinking-dev2000-added")
    assert drv.allowance_problems({}, repo=REPO) == []


def test_packets_guard_accepts_when_the_contract_accepts(monkeypatch):
    drv = _driver()
    drv.apply_geometry("gpu")
    drv.apply_roster(drv.SAMPLE_ROSTER_KEY)
    _, values = drv.compose_values(REPO)
    seen = {}
    monkeypatch.setattr(drv.evo, "require_owner_split_allowance", lambda **kw: seen.update(kw) or {})
    assert drv.allowance_problems(values, repo=REPO) == []
    assert seen["run_id"] == fam.PACKETS_RUN and seen["split_identity_hash"] == values["split_identity_hash"] and seen["carrier_lock_key"] == "slurp"


def test_v2_allowance_draft_supersedes_by_sha_and_adds_only_the_packets_id():
    v2, signed = js(pk.V2), js(fam.ALLOWANCE)
    assert v2["supersedes"]["path"] == fam.ALLOWANCE and v2["supersedes"]["sha256"] == hashlib.sha256((REPO / fam.ALLOWANCE).read_bytes()).hexdigest()
    assert v2["permitted_run_ids"] == [fam.RUN, fam.FIT_RUN, fam.PACKETS_RUN]
    assert v2["read_run_ids"] == [fam.RUN] and v2["preparation_run_ids"] == [fam.FIT_RUN, fam.PACKETS_RUN]
    assert v2["split"] == signed["split"]
    if v2["status"] == "authorised":
        assert v2["signature"]["status"] == "authorised" and v2["signature"]["recorded_by"] == "coordinator Fable 5.1" and v2["signature"].get("signed_by")
    else:
        assert v2["signature"] == {"status": "DRAFT: awaiting owner decision 308", "recorded_by": "coordinator Fable 5.1"}
    assert signed["permitted_run_ids"] == [fam.RUN, fam.FIT_RUN]       # the signed bytes are not edited
    assert v2["status"] != "authorised" or v2["signature"].get("signed_by")


def test_packets_stage_in_the_swap_script():
    text = (REPO / "scripts/flights/direct/direct_fb_packets_gpu.sh").read_text(encoding="utf-8")
    for needle in ("test-sample-3010", "thinking-test-sample-3010", "slurp-test-sample-3010-thinking-packets-gpu-v1", 'run_attempt "$SAMPLE_ROSTER" 27',
                   "direct_fb_packets_gpu_sample_task_entry.sh", "direct-fb-packets-gpu-test-sample-3010.recovery"):
        assert needle in text, needle
    entry = (REPO / "scripts/flights/direct/direct_fb_packets_gpu_sample_task_entry.sh").read_text(encoding="utf-8")
    assert "--run --stage test-sample-3010" in entry
    assert subprocess.run(["bash", "-n", str(REPO / "scripts/flights/direct/direct_fb_packets_gpu.sh")]).returncode == 0


# ---- preflip, scripts ------------------------------------------------------------------------------------------------------------------------------
def test_preflip_refuses_only_the_packet_receipt_sentinel_today():
    found = pf.refusals(REPO, None)
    baseline = js(f"configs/baseline/{fam.BASELINE}.json")
    if baseline["speech_packet_promotion_receipt_sha256"] == fam.ZERO:
        assert len(found) == 1 and "speech_packet_promotion_receipt_sha256" in found[0]
    else:
        assert found == []


def test_scripts_parse_and_refuse_without_their_gates():
    for name in ("successor3_thinking_flip.sh", "successor3_thinking_repin_cell.sh", "batch_chain_successor3_thinking.sh", "successor3_thinking_read.sh"):
        assert subprocess.run(["bash", "-n", str(NX / name)]).returncode == 0, name
    chain = (NX / "batch_chain_successor3_thinking.sh").read_text(encoding="utf-8")
    for needle in ('"smoke_experiment": None', "think-budget-np4", "TEST-SAMPLE-3010-promotion.json", "packets exposure row", "ONE attempt, ever", "session-stop.json"):
        assert needle in chain, needle
    read = (NX / "successor3_thinking_read.sh").read_text(encoding="utf-8")
    for needle in ("read_require_countersigned", "--strata-source scorer", "--expected-split-role final-report", "slurp_successor3_thinking_read.py", "slurp-slu-official-test"):
        assert needle in read, needle
    flip = (NX / "successor3_thinking_flip.sh").read_text(encoding="utf-8")
    assert "successor3_thinking_preflip_check.py" in flip and "repin_loop_generic.sh" in flip and "--allow-output-change must never be passed" in flip


def test_derive_is_idempotent_on_the_committed_cell():
    result = dc.derive(write=False)
    on_disk = js(f"configs/experiment/{fam.CELL}.json")
    assert result["experiment"]["owner_allowance"] == on_disk["owner_allowance"]
    assert result["experiment"]["family_budget"] == on_disk["family_budget"]
    assert result["baseline"]["scorers"] == js(f"configs/baseline/{fam.BASELINE}.json")["scorers"]
