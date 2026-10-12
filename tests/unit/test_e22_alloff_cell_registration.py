"""Preflight for the HELD Earnings-22 consumption-module all-off cells (2026-10-11), model-free.

The cells ``earnings22-native-stage3-module-alloff-v1`` (whole 10-call dev split, 451 native windows) and
``-smoke-4-v1`` (the first four windows of call 4453225) are the carrier admission gate (design 2b.3) of the
Earnings-22 profile. This suite holds the registration to its own claims: the ``e220`` byte proof, the HELD
form-proof shape, the declared scorer variant, the window-inventory pins (re-derived from the data root when
it is present), the pending packet pin, the draft ledger block, the e220 wrappers and the mint tool. It
contacts no model, encoder, tokenizer or server and writes nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails import consumption_module as cm

_REPO = Path(__file__).resolve().parents[2]
_DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
_PACKAGE = _REPO / "docs/readiness/2026-10-11-earnings22-module-alloff-v1"
_CELLS = {"arm": "earnings22-native-stage3-module-alloff-v1", "smoke": "earnings22-native-stage3-module-alloff-smoke-4-v1"}
_BASELINES = {"arm": "e22-native-window-direct-dev10-v1", "smoke": "e22-native-window-direct-four-row-v1"}
_PENDING = "0" * 64


@pytest.fixture(autouse=True)
def _proof_path():
    extra = str(_REPO / "scripts" / "analysis")
    if extra not in sys.path:
        sys.path.insert(0, extra)


def _json(relpath: str) -> dict:
    return json.loads((_REPO / relpath).read_text(encoding="utf-8"))


def _experiment(key: str) -> dict:
    return _json(f"configs/experiment/{_CELLS[key]}.json")


def _baseline(key: str) -> dict:
    return _json(f"configs/baseline/{_BASELINES[key]}.json")


def _receipt() -> dict:
    return json.loads((_PACKAGE / "window-inventory-receipt-v1.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The byte proof and the HELD form-proof shape.
# ---------------------------------------------------------------------------


def test_the_e220_byte_proof_holds_and_compares_with_the_base_fragment():
    import module_equivalence_proof as proof  # noqa: PLC0415

    report = proof.run_case("e220")
    assert report["ok"], report
    layer = next(r for r in report["results"] if r.get("target") == "direct-layer")
    assert layer["fragment"] == "e22-native-window-direct-base-v1" and layer["differing_policy_paths"] == []
    cells = [r for r in report["results"] if "cell" in r]
    assert {r["cell"] for r in cells} == {"arm", "smoke"}
    for row in cells:
        assert row["composed_identical"] and row["differing_policy_paths"] == []
        assert row["canonical_alloff_policy_differences"] == [] and row["off_arm"]
        assert row["direct_parent"] == "e22-native-window-direct-base-v1"
        assert row["composed_config_diff_vs_parent"] == {
            "policy": [], "bookkeeping": [], "experiment_fragment": [], "anything_else": []}


@pytest.mark.parametrize("key", ["arm", "smoke"])
def test_the_cells_are_held_form_proofs_declaring_the_all_off_block(key):
    import module_equivalence_proof as proof  # noqa: PLC0415

    document = _experiment(key)
    cell = document["cells"][0]
    assert cell["readiness"]["state"] == "held" and cell["cell_id"] == _CELLS[key]
    assert cell["allowed_execution_stages"] == ["check", "worker", "campaign"]
    assert document["execution_plan"]["split_role"] == "dev"
    assert document["execution_plan"]["execution_profile"] == "bounded-discovery-probe"
    assert document["stage3_measurement"]["measurement_design"] == "form-proof"
    assert document["stage3_measurement"]["claims_benefit"] is False
    assert document["stage3_algorithm"]["id"] == "none"
    block = document[proof.DECLARATION_KEY]["block"]
    assert block["profile"] == "earnings22" and cm.is_module_off_block(block)
    plan = _json(f"configs/campaign/{_CELLS[key]}.json")
    assert plan == {"cells": [{"cell": _CELLS[key], "experiment": _CELLS[key]}], "schema": "saea-campaign-plan-v1"}


@pytest.mark.parametrize("key, rows, units", [("arm", 10, 451), ("smoke", 1, 4)])
def test_populations_budgets_and_the_failure_policy(key, rows, units):
    document = _experiment(key)
    population = document["population"]
    assert (population["carrier"], population["count"], population["execution_units"]) == ("earnings22-original", rows, units)
    assert population["historically_exposed"] is True
    budget = document["family_budget"]
    assert budget["generation_calls_cap"] == units == document["execution_plan"]["planned_model_calls"]
    assert budget["fit_endpoint_calls_cap"] == 0 and budget["encoder_calls"] == 0 and budget["asr_calls"] == 0
    assert budget["ceilings_are_not_targets"] is True
    assert "AT MOST ONE root-diagnosed recovery" in document["failure_policy"]


# ---------------------------------------------------------------------------
# The baseline fragments: direct base + E21-shaped geometry, one scorer, no knowledge supply, pending packet pin.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["arm", "smoke"])
def test_the_baseline_is_the_shared_base_plus_the_window_pins(key):
    base = _json("configs/baseline/e22-native-window-direct-base-v1.json")
    own = _baseline(key)
    assert cm.differing_paths(cm.policy_owned_values(own), cm.policy_owned_values(base)) == []
    assert own["scorers"] == ["asr-wer-whisper"]
    assert own["arm"] == "speech-feature-query" and own["evidence_source"] == "none" and own["evidence_mismatch"] is False
    assert own["knowledge_snapshot_relpath"] == "knowledge/e22/inert/all-off-placeholder-v1/snapshot.json"
    assert len(own["knowledge_snapshot_sha256"]) == 64
    for forbidden in ("knowledge_stores", "native_episode",
                      "live_phase_fit", "d1_evidence_supplement", "agent_tools", "tools"):
        assert forbidden not in own, forbidden
    e21 = _json("configs/baseline/e21-native-window-direct-full44-v1.json")
    for shared in ("task_instruction", "prompt_fit_multiple", "serving_slots", "serving_slot_tokens", "task_contract_source",
                   "ojw_workflow_timeout_seconds"):
        assert own[shared] == e21[shared], shared
    assert own["speech_feature_key_representation_id"].startswith("saea-e22-native-window-v1")
    assert own["speech_feature_matcher_policy_id"] == "saea-e22-native-window-v1"


def test_the_scorer_variant_decision_is_declared_in_what_this_is():
    for key in ("arm", "smoke"):
        text = _baseline(key)["what_this_is"]
        for needle in ("asr-wer-whisper only", "NOT the ESB short-form tail-2 s variant", "D-TS2-3", "15.937", "9.2377",
                       "appends no silence", "no alignment band is claimed", "PENDING"):
            assert needle in text, (key, needle)
    registered = _json("docs/readiness/2026-10-11-earnings22-module-alloff-v1/registered-facts-v1.json")
    measurement = registered["stage3_measurement"]["SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-V1"]
    assert measurement["claims_benefit"] is False
    assert "NOT the ESB short-form tail-2 s variant" in measurement["primary_metric"] and "D-TS2-3" in measurement["primary_metric"]


def test_the_packet_pin_is_the_named_pending_pin_and_the_units_pin_matches_the_receipt():
    receipt = _receipt()
    arm, smoke = _baseline("arm"), _baseline("smoke")
    assert arm["prepared_window_feature_packets"]["sha256"] == _PENDING == smoke["prepared_window_feature_packets"]["sha256"]
    assert arm["prepared_window_feature_packets"]["path"].endswith("/analysis/SAEA-E22-DEV-WINDOW-GPU-ENCODING-V1/window-feature-packets.json")
    assert smoke["prepared_window_feature_packets"]["path"].endswith("/analysis/SAEA-E22-NATIVE-WINDOW-FOUR-ROW-V1/window-feature-packets.json")
    inventory, four = receipt["inventory"], receipt["four_row"]
    assert arm["prepared_execution_units"] == {
        "batch": inventory["batch"], "registry_run_id": inventory["run_id"], "relpath": inventory["relpath"],
        "sha256": inventory["file_sha256"], "split_identity_hash": receipt["split_identity_hash"],
        "unit_count": 451}
    assert inventory["request_count"] == 451
    assert smoke["prepared_execution_units"]["batch"] == four["batch"] == "SAEA-E22-NATIVE-WINDOW-FOUR-ROW-V1"
    assert smoke["prepared_execution_units"]["registry_run_id"] == inventory["run_id"]
    assert smoke["prepared_execution_units"]["sha256"] == four["file_sha256"]
    assert smoke["prepared_execution_units"]["unit_count"] == four["unit_count"] == 4
    facts = _json("docs/readiness/2026-10-11-earnings22-module-alloff-v1/registered-facts-v1.json")
    assert "encoder pass" in facts["pending_pins"]["prepared_window_feature_packets"]


def test_the_model_fragment_is_the_e21_geometry_with_only_the_feature_roots_changed():
    e21 = _json("configs/model/q4km-e21-native-window-packets-cddb000c-np4-max1024-v1.json")
    e22 = _json("configs/model/q4km-e22-native-window-packets-cddb000c-np4-max1024-v1.json")
    differing = sorted(k for k in set(e21) | set(e22) if e21.get(k) != e22.get(k))
    assert differing == ["preparation_basis", "server_env", "speech_feature_root"]
    assert e22["speech_feature_root"].endswith("/e22-cddb000c-dev-gpu-v1")
    assert e22["server_env"]["LLAMA_SPEECH_FEATURE_ROOT"] == e22["speech_feature_root"]
    assert {k: v for k, v in e22["server_env"].items() if k != "LLAMA_SPEECH_FEATURE_ROOT"} == {
        k: v for k, v in e21["server_env"].items() if k != "LLAMA_SPEECH_FEATURE_ROOT"}
    assert e22["serving_geometry"] == {"max_tokens": 1024, "slot_tokens": 24576, "slots": 4}
    assert "-np" in e22["server_args"] and e22["server_args"][e22["server_args"].index("-np") + 1] == "4"
    # The np1 preprocess twin differs from E21's only in the cache root and its basis text.
    p21 = _json("configs/model/q4km-e21-feature-preprocess-gpu-cddb000c-np1.json")
    p22 = _json("configs/model/q4km-e22-feature-preprocess-gpu-cddb000c-np1.json")
    assert sorted(k for k in set(p21) | set(p22) if p21.get(k) != p22.get(k)) == ["preparation_basis", "server_env"]


@pytest.mark.parametrize("key", ["arm", "smoke"])
def test_each_cell_composes_and_its_hash_is_the_registered_one(key):
    document = _experiment(key)
    cell = document["cells"][0]
    composed = compose(_REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], _CELLS[key])
    facts = _json("docs/readiness/2026-10-11-earnings22-module-alloff-v1/registered-facts-v1.json")
    assert composed.config_hash == facts["cells"][key]["composed_config_hash"]
    assert composed.values["carrier_lock_key"] == "earnings22-original"
    assert composed.values["split_name"] == ("dev" if key == "arm" else "e22-native-window-four-row-v1")
    assert composed.values["policy"] == "phase-direct-only-v1"


def test_the_smoke_subset_is_one_dev_call_by_receipt():
    from speech_aware_evidence_acquisition.reproduction.probe_split import load_verified_probe_split

    split = load_verified_probe_split(_REPO, "e22-native-window-four-row-v1")
    assert (split.carrier_lock_key, split.split_role, split.ids) == ("earnings22-original", "dev", ("4453225",))
    dataset = _json("configs/dataset/e22-native-window-four-row-v1.json")
    assert dataset["e21_runtime_subset"] == {
        "receipt_split_name": "e22-native-window-four-row-v1", "parent_split": "dev", "subset_role": "construction"}
    assert _baseline("smoke")["prepared_execution_units"]["split_identity_hash"] == split.identity_hash
    full = _json("configs/dataset/earnings22-native-window-dev10-v1.json")
    assert (full["split_id"], full["split_name"]) == ("dev", "dev")


# ---------------------------------------------------------------------------
# The window inventory: receipt arithmetic always; the data root's bytes when present.
# ---------------------------------------------------------------------------


def test_the_receipt_is_internally_consistent_and_contactless():
    receipt = _receipt()
    inventory = receipt["inventory"]
    assert receipt["contact_class"] == "model-free" and set(receipt["contacts"].values()) == {0, 0.0}
    assert inventory["calls"] == 10 and inventory["request_count"] == inventory["unique_audio_count"] == 451
    assert sum(inventory["windows_per_call"].values()) == 451 and len(inventory["windows_per_call"]) == 10
    assert inventory["state"] == "inputs-verified-features-not-materialized"
    assert receipt["four_row"]["unit_count"] == 4 and receipt["four_row"]["sample_id"] == "4453225"
    assert "Counts, hashes and ids only" in receipt["_note"]


@pytest.mark.skipif(not (_DATA / "analysis/SAEA-E22-DEV-WINDOW-INVENTORY-V1/window-inventory.json").is_file(),
                    reason="the data root (and its Earnings-22 window inventory) is not mounted")
def test_the_inventory_bytes_on_the_data_root_match_every_pin():
    receipt = _receipt()
    path = _DATA / receipt["inventory"]["relpath"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt["inventory"]["file_sha256"] == _baseline("arm")["prepared_execution_units"]["sha256"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    output = artifact["output"]
    assert artifact["output_sha256"] == receipt["inventory"]["output_sha256"]
    assert artifact["contact_class"] == "model-free" and output["request_count"] == 451
    requests = output["batches"][0]["requests"]
    assert output["batches"][0]["name"] == "SAEA-E22-DEV-WINDOW-INVENTORY-V1"
    per_call: dict[str, int] = {}
    for row in requests:
        per_call[row["source_provenance"]["sample_id"]] = per_call.get(row["source_provenance"]["sample_id"], 0) + 1
    assert per_call == receipt["inventory"]["windows_per_call"]
    # The four-row batch is exactly the first four windows of call 4453225, byte-identical rows.
    four_path = _DATA / receipt["four_row"]["relpath"]
    assert hashlib.sha256(four_path.read_bytes()).hexdigest() == receipt["four_row"]["file_sha256"]
    four = json.loads(four_path.read_text(encoding="utf-8"))["output"]["batches"][0]
    first = [r for r in requests if r["source_provenance"]["sample_id"] == "4453225"][:4]
    assert four["name"] == "SAEA-E22-NATIVE-WINDOW-FOUR-ROW-V1" and four["requests"] == first
    assert [r["request_key"] for r in first] == [f"4453225#w{i:04d}" for i in range(1, 5)]


# ---------------------------------------------------------------------------
# The draft ledger block, the wrappers and the mint tool.
# ---------------------------------------------------------------------------


def _ledger_rows(*needles: str) -> list[str]:
    text = (_REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line.startswith("| 2026-10-11") and any(n in line for n in needles)]


def test_the_ledger_block_is_a_draft_with_one_executed_model_free_row():
    runs = ("SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-V1", "SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1",
            "SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-FORM-READ-V1")
    for run in runs:
        rows = _ledger_rows(f"| {run} |")
        assert len(rows) == 1, run
        assert "root countersigned" not in rows[0] and "DRAFT" in rows[0] and "| no |" in rows[0]
    inventory = _ledger_rows("| SAEA-E22-DEV-WINDOW-INVENTORY-V1 |")
    assert len(inventory) == 1 and "model-free-check" in inventory[0] and "| yes |" in inventory[0]
    assert "root countersigned" not in inventory[0] and "root countersignature pending" in inventory[0]
    # The generation rows carry the split role dev and the run-identity hashes of their own populations.
    arm = _ledger_rows("| SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-V1 |")[0]
    assert "| dev |" in arm and _receipt()["split_identity_hash"] in arm


def test_the_e220_wrappers_name_only_earnings22_and_the_package_exists():
    module_dir = _REPO / "scripts/flights/module"
    names = ["module_alloff_e220_flip.sh", "module_alloff_e220_read.sh", "module_alloff_e220_repin_arm.sh",
             "module_alloff_e220_repin_smoke.sh", "batch_chain_module_alloff_e220.sh"]
    for name in names:
        text = (module_dir / name).read_text(encoding="utf-8")
        assert "\r" not in text and text.startswith("#!/bin/bash"), name
        for stale in ("earnings21", "EARNINGS21", "e210", "serving-e21", "Earnings-21", "--carrier e21", "2026-09-30"):
            assert stale not in text, (name, stale)
    assert (_PACKAGE / "README.md").is_file() and (_REPO / "docs/readiness/2026-10-11-earnings22-module-alloff-v1-preregistration.md").is_file()
    chain = (module_dir / "batch_chain_module_alloff_e220.sh").read_text(encoding="utf-8")
    assert "serving-e22-native-window-flightruntime-np4-max1024-v1" in chain and '10, 45)' in chain
    for cell in _CELLS.values():
        assert (_REPO / f"configs/campaign/{cell}.json").is_file()


def test_the_mint_tool_drafts_the_e22_receipt_and_refuses_nothing_it_should_accept(tmp_path):
    env = dict(os.environ, SAEA_STUDY_ROOT=str(_REPO), SPEECHRL_DATA_DIR=str(tmp_path), PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run(
        [sys.executable, "-B", str(_REPO / "scripts/flights/module/module_alloff_mint_receipt.py"), "--carrier", "e22", "--dry"],
        capture_output=True, text=True, env=env, check=False)
    assert done.returncode == 0, done.stderr
    assert "(dry) would write" in done.stdout and "root-admission-v1.json" in done.stdout
    assert not (tmp_path / "coordination").exists()
    body = done.stdout.split("(dry)")[0]
    receipt = json.loads(body)
    assert receipt["status"] == "decided" and receipt["decision_id"] == "earnings22-native-stage3-module-alloff-v1-admission-v1"
    assert sorted(receipt["eligible_run_ids"]) == sorted([
        "SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-V1", "SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1"])


def test_the_derived_fragments_are_canonical_json():
    """The register script writes sorted-key, two-space, LF JSON; a hand edit of a derived fragment is visible here."""

    committed = (
        f"configs/baseline/{_BASELINES['arm']}.json", f"configs/baseline/{_BASELINES['smoke']}.json",
        f"configs/experiment/{_CELLS['arm']}.json", f"configs/experiment/{_CELLS['smoke']}.json",
        "configs/dataset/e22-native-window-four-row-v1.json", "configs/dataset/earnings22-native-window-dev10-v1.json")
    for rel in committed:
        text = (_REPO / rel).read_text(encoding="utf-8")
        assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False, sort_keys=True) + "\n", rel


# ---------------------------------------------------------------------------
# The inert knowledge snapshot: the runner needs a validated non-empty snapshot; Earnings-22 has no governed knowledge.
# ---------------------------------------------------------------------------


def _inert_builder():
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_e22_inert_knowledge_snapshot", _REPO / "scripts/build_e22_inert_knowledge_snapshot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("key", ["arm", "smoke"])
def test_both_baselines_pin_the_deterministic_inert_snapshot(key):
    builder = _inert_builder()
    snapshot = builder.build_snapshot()
    own = _baseline(key)
    assert own["knowledge_snapshot_relpath"] == builder.RELPATH
    assert own["knowledge_snapshot_sha256"] == snapshot.content_hash()
    assert (len(snapshot.facets), len(snapshot.values)) == (1, 1)
    assert snapshot.source_partition_role == "external-governed"


def test_the_inert_snapshot_round_trips_through_the_frozen_loader_and_is_deterministic():
    import json
    from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
    builder = _inert_builder()
    payload = builder.frozen_bytes()
    assert payload == builder.frozen_bytes()
    loaded = KnowledgeSnapshot.from_frozen_json(json.loads(payload.decode("utf-8")))
    assert loaded.content_hash() == builder.build_snapshot().content_hash()
    assert loaded.historical_prior_score_range_violations == ()


def test_the_runtime_loader_accepts_the_inert_pin_and_still_refuses_an_undeclared_one(tmp_path):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError
    builder = _inert_builder()
    target = tmp_path / builder.RELPATH
    target.parent.mkdir(parents=True)
    target.write_bytes(builder.frozen_bytes())

    def stub(values):
        runtime = FlightRuntime.__new__(FlightRuntime)
        runtime._composed = type("C", (), {"values": values})()
        runtime._data_root = tmp_path
        return runtime

    snapshot = stub({"knowledge_snapshot_relpath": builder.RELPATH,
                     "knowledge_snapshot_sha256": builder.build_snapshot().content_hash()})._load_knowledge_snapshot()
    assert snapshot.content_hash() == builder.build_snapshot().content_hash()
    with pytest.raises(FlightRuntimeError, match="must declare 'knowledge_snapshot_relpath'"):
        stub({})._load_knowledge_snapshot()
    with pytest.raises(FlightRuntimeError, match="hashes to"):
        stub({"knowledge_snapshot_relpath": builder.RELPATH, "knowledge_snapshot_sha256": "0" * 64})._load_knowledge_snapshot()
