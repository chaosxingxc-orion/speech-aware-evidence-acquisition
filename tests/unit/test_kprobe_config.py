"""Cell KPROBE -- the centroid-key conversion probe -- is the locked PLAN plan with ONE pin
moved, on a proven roster.

Config only: no data root, no lock, no adapter, no contact. Every assertion here is a property a
reader of the registration should be able to take for granted, and each one is a defect this
registration could plausibly have shipped.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

REPO = Path(__file__).resolve().parents[2]

ROSTER_ROWS = 55
CELL = f"slurp-native-stage3-kprobe-fold-a-{ROSTER_ROWS}-v1"
RUN = f"SAEA-SLURP-STAGE3-KPROBE-FOLD-A-{ROSTER_ROWS}-V1"
FIT_RUN = f"SAEA-SLURP-STAGE3-KPROBE-FOLD-A-{ROSTER_ROWS}-FIT-V1"
KEY_ROW = "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1"
PARENT_EXPERIMENT = "slurp-native-default-plan-lock-v1"
PACKAGE = REPO / f"docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-{ROSTER_ROWS}-v1"
PREREG = REPO / f"docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-{ROSTER_ROWS}-v1-preregistration.md"
DERIVATION = PACKAGE / "roster-derivation-v1.json"
CONTACTS_PER_ROW = 11
WRITTEN_KEY_SHA = "76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2"
CENTROID_FACETS = "prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl"
CENTROID_RECEIPT = "prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/receipt.json"
ONE_PIN = "knowledge_stores.intent-boundaries.phase_supply.perception.facet_source"
BOOKKEEPING = ("native_contact_fit.", "prepared_phase_supply", "preparation_source_receipts", "what_this_is")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(_flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


@pytest.fixture(scope="module")
def experiment() -> dict:
    return _read(REPO / "configs/experiment" / f"{CELL}.json")


@pytest.fixture(scope="module")
def derivation() -> dict:
    return _read(DERIVATION)


@pytest.fixture(scope="module")
def composed(experiment: dict):
    cell = experiment["cells"][0]
    return compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], CELL)


@pytest.fixture(scope="module")
def parent():
    cell = _read(REPO / "configs/experiment" / f"{PARENT_EXPERIMENT}.json")["cells"][0]
    return compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], PARENT_EXPERIMENT)


def test_the_three_proofs_recorded_no_differences(derivation: dict) -> None:
    assert derivation["schema"] == "saea-centroid-key-conversion-roster-v1"
    assert derivation["proof_a_diagnostic_reproduced"]["differences"] == []
    b = derivation["proof_b_treatment_file_through_production_recall"]
    assert b["differences"] == []
    assert b["fallback_equals_written_key_exactly"] is True
    assert b["max_abs_diff_to_diagnostic_r01_excluded_centroid"] <= 1e-12
    assert b["fallback_facet_ids"] == ["intent-boundary:cooking_query"]
    c = derivation["proof_c_population_through_production_constructor"]
    assert c["production_constructor_equals_production_recall_on_the_population"] is True
    agree = c["delivery"]["sealed_boundary_agreement"]
    assert agree["baseline_fusion_equals_sealed"] == agree["rows"] == 1080
    assert c["delivery"]["fusion_vs_rank_disagreements"] == 0


def test_the_diagnostic_note_and_recipe_still_hash_to_what_the_derivation_proved(derivation: dict) -> None:
    for key in ("diagnostic_note", "diagnostic_recipe", "replication_recipe"):
        pin = derivation["authority"][key]
        assert hashlib.sha256((REPO / pin["relpath"]).read_bytes()).hexdigest() == pin["sha256"], key


def test_proof_a_reproduces_the_notes_published_cells(derivation: dict) -> None:
    pa = derivation["proof_a_diagnostic_reproduced"]
    note = pa["note_cells_compared"]
    for label, arm in pa["arms"].items():
        for construction in ("written", "centroid"):
            assert arm["reads"][construction]["cells"] == note[label][construction], (label, construction)
        v = arm["validation"]
        assert v["repo_top_matches_sealed"] == v["numpy_top_matches_sealed"] == v["numpy_order_equals_repo"] == v["rows"]
    assert note["train-fold-a-plan"]["centroid"]["deliv_wrong"] == 71.2
    assert note["train-fold-a-plan"]["written"]["deliv_wrong"] == 45.0


def test_proof_b_roll1_equals_the_note_under_the_same_pool(derivation: dict) -> None:
    pa = derivation["proof_a_diagnostic_reproduced"]
    pb = derivation["proof_b_treatment_file_through_production_recall"]
    assert pb["arms"]["roll1"]["cells"] == pa["note_cells_compared"]["roll1"]["centroid"]
    for arm in pb["arms"].values():
        assert arm["production_recall_order_equals_vectorised_order"] == arm["rows"]
        assert arm["production_recall_width8_equals_order_head"] == arm["rows"]


def test_roster_ids_are_distinct_intent_wrong_fold_a_rows(derivation: dict) -> None:
    ids = derivation["roster"]["ids"]
    assert len(ids) == ROSTER_ROWS == derivation["roster"]["count"]
    assert len(set(ids)) == ROSTER_ROWS
    assert ids == sorted(ids)
    manifest = _read(REPO / "configs/dataset" / (derivation["roster"]["dataset_fragment"] + ".json"))
    assert set(ids) <= {str(item["sample_id"]) for item in manifest["items"]}
    wrong = derivation["proof_b_treatment_file_through_production_recall"]["arms"]["train-fold-a-plan"]["per_class"]["INTENT-WRONG"]
    assert wrong["newly_delivered"] == ROSTER_ROWS
    assert wrong["delivered_centroid"] - wrong["delivered_written"] == ROSTER_ROWS - wrong["newly_lost"]
    split = derivation["proof_c_population_through_production_constructor"]["delivery"]["plan_class_split"]
    assert sum(split[k]["newly_delivered"] for k in ("INTENT-UNCOVERED", "INTENT-COVERED")) == ROSTER_ROWS
    assert split["INTENT-UNCOVERED"]["rows"] == 130 and split["INTENT-COVERED"]["rows"] == 61
    by_class = derivation["proof_c_population_through_production_constructor"]["population_by_plan_class"]
    assert sum(v["newly_delivered"] for v in by_class.values()) == ROSTER_ROWS


def test_id_list_digest_and_split_identity_are_hashes_of_those_ids(derivation: dict) -> None:
    ids = derivation["roster"]["ids"]
    assert hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest() == derivation["roster"]["id_list_sha256"]
    assert derivation["roster"]["split_identity_hash"] == split_identity_hash(prefixed(derivation["roster"]["carrier_lock_key"], ids))


def test_the_fragment_flies_exactly_the_derived_ids(experiment: dict, derivation: dict) -> None:
    population = experiment["population"]
    assert population["count"] == ROSTER_ROWS
    assert population["split_identity_hash"] == derivation["roster"]["split_identity_hash"]
    assert len(experiment["populations"]) == 1
    inline = experiment["populations"][0]
    assert inline["dataset_fragment"] == derivation["roster"]["dataset_fragment"]
    assert inline["ids"] == derivation["roster"]["ids"]


def test_split_identity_matches_a_fresh_hash_over_the_inline_ids(experiment: dict, composed) -> None:
    ids = experiment["populations"][0]["ids"]
    assert split_identity_hash(prefixed(composed.values["carrier_lock_key"], ids)) == experiment["population"]["split_identity_hash"]


def test_the_composed_config_differs_from_the_locked_plan_by_one_pin_and_bookkeeping(composed, parent, experiment) -> None:
    parent_doc = _read(REPO / "configs/experiment" / f"{PARENT_EXPERIMENT}.json")
    baseline_keys = set(_read(REPO / "configs/baseline" / (parent_doc["cells"][0]["baseline_fragment"] + ".json")))
    experiment_keys = set(experiment) | set(parent_doc)
    assert not (experiment_keys & baseline_keys), "the experiment fragment overrides a baseline key"
    a, b = _flatten(parent.values), _flatten(composed.values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    one_pin = [k for k in changed if k.startswith(ONE_PIN + ".")]
    bookkeeping = [k for k in changed if k.startswith(BOOKKEEPING) and not k.startswith(ONE_PIN)]
    experiment_block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in one_pin and k not in bookkeeping]
    other = [k for k in changed if k not in one_pin and k not in bookkeeping and k not in experiment_block]
    assert other == [], other
    assert one_pin, "the facet_source pin did not move"
    mine = composed.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    theirs = parent.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    assert {k: v for k, v in mine.items() if k != "facet_source"} == {k: v for k, v in theirs.items() if k != "facet_source"}
    assert theirs["facet_source"]["sha256"] == WRITTEN_KEY_SHA
    assert mine["facet_source"]["relpath"] == CENTROID_FACETS
    assert mine["facet_source"]["kind"] == "sealed-vectors"
    assert mine["facet_source"]["tool_contact_ledger_row"] == KEY_ROW
    assert mine["k"] == 8 and mine["tau"] == 0.0
    assert mine["fuse_coverage"] == {"m": 8, "c": 1, "top_l": 8}
    assert mine["rank_weights"] == {"w_agree": 0.0, "w_cos": 1.0, "w_prior": 0.0}
    assert "agreement_source" not in mine
    for store in ("intent-boundaries", "train-exemplars", "slot-contracts"):
        for pin in ("snapshot", "release"):
            assert composed.values["knowledge_stores"][store][pin] == parent.values["knowledge_stores"][store][pin]
    assert composed.values["scorers"] == parent.values["scorers"]
    assert composed.values["arm"] == parent.values["arm"]
    assert composed.values["policy"] == parent.values["policy"] == "phase-native-candidates-review-revise-v1"
    receipts, parent_receipts = composed.values["preparation_source_receipts"], parent.values["preparation_source_receipts"]
    assert receipts[:-1] == parent_receipts
    assert receipts[-1]["relpath"] == CENTROID_RECEIPT and receipts[-1]["root"] == "data"


def test_the_pin_agrees_with_the_derivation_and_the_registered_facts(composed, derivation: dict) -> None:
    mine = composed.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["facet_source"]
    assert mine == derivation["treatment"]["facet_source_pin"]
    assert mine["sha256"] == derivation["treatment"]["sha256"]
    facts = _read(PACKAGE / "registered-facts-v1.json")
    assert facts["treatment_key_file"]["facets"]["sha256"] == mine["sha256"]
    assert facts["treatment_key_file"]["receipt"]["sha256"] == derivation["treatment"]["receipt_sha256"]
    receipt_copy = PACKAGE / "centroid-keys-receipt-v1.json"
    assert hashlib.sha256(receipt_copy.read_bytes()).hexdigest() == derivation["treatment"]["receipt_sha256"]
    receipt = _read(receipt_copy)
    assert receipt["schema"] == "saea-centroid-key-receipt-v1"
    assert receipt["artifact"]["sha256"] == mine["sha256"]
    assert receipt["measured"]["written_fallback_ids"] == ["intent-boundary:cooking_query"]
    assert receipt["measured"]["intents"] == 60 and receipt["measured"]["centroid_facets"] == 59
    assert receipt["contacts"]["encoder"] == 0 and receipt["contacts"]["model"] == 0
    assert composed.values["preparation_source_receipts"][-1]["sha256"] == derivation["treatment"]["receipt_sha256"]
    diff = facts["composed_config_diff_against_the_locked_plan_cell"]
    assert diff["anything_else"] == []
    assert diff["the_one_pin"] and all(k.startswith(ONE_PIN) for k in diff["the_one_pin"])


def test_prepared_phase_supply_is_absent_or_the_cells_own(composed, experiment: dict) -> None:
    # Before the flip nothing is committed; after the re-pin (flight commit baa5ff99) the pinned supply must be
    # KPROBE's own prepared artefact, never a foreign one (item E26 / the is_own_supply_requirement fix).
    baseline = _read(REPO / "configs/baseline" / (experiment["cells"][0]["baseline_fragment"] + ".json"))
    for doc in (composed.values, baseline):
        pps = doc.get("prepared_phase_supply")
        if pps is None:
            continue
        text = json.dumps(pps)
        assert "kprobe" in text.lower(), "a committed prepared supply must be this cell's own"


def test_readiness_is_held_with_an_empty_requirements_list(experiment: dict) -> None:
    readiness = experiment["cells"][0]["readiness"]
    # `held` with the empty requirements list before the flip; `ready` after the converging re-pin.
    assert readiness["state"] in ("held", "ready")
    if readiness["state"] == "held":
        assert readiness["requirements"] == []
        assert "--allow-output-change must never be passed" in readiness["reason"]
    else:
        # after the flip every requirement (decision receipt, own prepared supply) names this cell's package
        assert readiness["requirements"]
        for req in readiness["requirements"]:
            assert "kprobe" in json.dumps(req).lower(), req


def test_caps_are_the_conv_arithmetic(experiment: dict, derivation: dict) -> None:
    caps = experiment["family_budget"]
    generation = ROSTER_ROWS * CONTACTS_PER_ROW
    assert caps["generation_calls_cap"] == generation
    assert caps["fit_endpoint_calls_cap"] == 4 * generation
    assert caps["native_task_contract_calls_cap"] == 6 * ROSTER_ROWS
    audio = derivation["roster"]["audio_seconds_total"]
    assert caps["repeated_speech_audio_seconds_cap"] == -(-int(audio * CONTACTS_PER_ROW * 1000) // 1000)
    assert caps["asr_calls"] == 0 and caps["encoder_calls"] == 0
    assert caps["official_complete_scoring_jobs"] == 1
    assert caps["gpu_hours_fit_inclusive"] == 1.0
    assert experiment["generation_budget"]["cap"] == generation
    plan = experiment["execution_plan"]
    assert plan["planned_model_calls"] == generation
    assert plan["planned_speech_audio_seconds"] == caps["repeated_speech_audio_seconds_cap"]
    assert plan["planned_gpu_hours"] == caps["gpu_hours_fit_inclusive"]
    assert plan["split_role"] == "discovery"
    assert experiment["execution_profile"] == "bounded-discovery-probe"


def test_the_fit_identity_is_this_cell_s_own(composed) -> None:
    fit = composed.values["native_contact_fit"]
    assert fit["run_id"] == FIT_RUN
    assert fit["attempt_id"] == f"attempt-slurp-native-stage3-kprobe-fold-a-{ROSTER_ROWS}-fit-v1"
    assert fit["contact_cap"] == 4 * ROSTER_ROWS * CONTACTS_PER_ROW


def test_the_failure_mode_policies_are_the_two_the_gate_requires(composed) -> None:
    episode = composed.values["native_episode"]
    assert episode["finite_completion_policy"] == "deliver-latest-or-abstain"
    assert episode["react_exhaustion_policy"] == "continue-without-answer"


def test_the_measurement_declaration_is_a_form_proof_that_claims_nothing() -> None:
    block = _read(PACKAGE / "registered-facts-v1.json")["stage3_measurement"][RUN]
    assert block["measurement_design"] == "form-proof"
    assert block["claims_benefit"] is False
    assert block["expected_effect_pp"] == 0.0
    assert block["rows"] == ROSTER_ROWS
    assert "admission" not in block and "harm_margin_pp" not in block
    assert "conditional rate" in block["note"].lower()
    assert "no effectiveness claim" in block["note"].lower()
    assert "0.092615" in block["note"] and "decision 133" in block["note"]


def test_the_preregistration_fence_repeats_the_canonical_block() -> None:
    text = PREREG.read_text(encoding="utf-8")
    start = text.index("```json")
    fenced = json.loads(text[text.index("\n", start) + 1 : text.index("```", start + 7)])
    assert fenced["stage3_measurement"] == _read(PACKAGE / "registered-facts-v1.json")["stage3_measurement"]


def test_the_stage3_algorithm_label_is_none_with_its_reason(experiment: dict) -> None:
    label = experiment["stage3_algorithm"]
    assert label["id"] == "none"
    assert label["operators_used"] == []
    assert "NO training-free RL operator" in label["note"]


def test_the_package_forbids_a_pooled_claim_in_so_many_words(derivation: dict) -> None:
    for name in ("registered-facts-v1.json", "protocol-registered-v1.json"):
        text = (PACKAGE / name).read_text(encoding="utf-8")
        assert "SELECTED USING GOLD" in text
        assert "NO POOLED OR ROSTER-LEVEL CLAIM MAY EVER BE MADE" in text
    assert "NO POOLED OR ROSTER-LEVEL CLAIM MAY EVER BE MADE" in derivation["gold_use"]


def test_the_read_recipe_gates_on_delivery_and_reads_the_four_way_split() -> None:
    recipe = _read(PACKAGE / "analysis-recipe-v1.json")
    assert recipe["arms"]["probe"]["run_id"] == RUN and recipe["arms"]["probe"]["fit_run_id"] == FIT_RUN
    assert recipe["metrics"] == ["scenario_action_exact"]
    assert recipe["interval"]["primary"] == "Wilson score CI95"
    assert "Clopper-Pearson" in recipe["interval"]["reported_beside"]
    steps = "\n".join(recipe["steps"])
    assert "DELIVERY GATE" in steps and "FOUR-WAY" in steps
    assert (REPO / recipe["read_driver"]).is_file()
    assert recipe["roster"]["sha256"] == hashlib.sha256(DERIVATION.read_bytes()).hexdigest()


def test_the_campaign_plan_is_this_single_cell(experiment: dict) -> None:
    plan = _read(REPO / "configs/campaign" / f"{CELL}.json")
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [{"cell": CELL, "experiment": CELL}]
    assert "campaign" in experiment["cells"][0]["allowed_execution_stages"]


def test_the_plan_documents_carry_the_recomposed_hashes(composed, experiment: dict) -> None:
    split = experiment["population"]["split_identity_hash"]
    expected = protocol_hash(composed.config_hash, composed.values["arm"], split)
    for name, run in (("generation-plan-registered-v1.json", RUN), ("fit-plan-registered-v1.json", FIT_RUN)):
        plan = _read(PACKAGE / name)
        assert plan["composed_config_hash"] == composed.config_hash
        assert plan["execution_plan"]["protocol_hash"] == expected
        assert plan["execution_plan"]["run_id"] == run
        assert plan["execution_plan"]["split_identity_hash"] == split
        assert plan["prepared_phase_supply"]["sha256"] == "MINTED_AT_THE_FLIP"


def test_the_draft_decision_receipt_names_the_two_run_ids_and_is_not_decided() -> None:
    draft = _read(PACKAGE / "root-admission-draft-v1.json")
    assert draft["eligible_run_ids"] == [RUN, FIT_RUN]
    assert draft["status"] != "decided"
    assert draft["decision_id"] == f"slurp-stage3-kprobe-fold-a-{ROSTER_ROWS}-admission-v1"


def test_all_three_exposure_rows_exist_and_no_cell_contains_a_pipe() -> None:
    """A literal '|' inside a cell silently splits the row, and
    contracts.ledger._parse_ledger_tables then refuses the whole ledger."""

    lines = io.open(REPO / "docs/exposure-ledger.md", encoding="utf-8", newline="").read().split("\n")
    rows = {
        run: [line for line in lines if line.startswith("|") and ("| " + run + " |") in line]
        for run in (RUN, FIT_RUN, KEY_ROW)
    }
    for run, found in rows.items():
        assert len(found) == 1, run
        parts = found[0].split("|")
        assert len(parts) == 17, (run, parts[:3])
        cells = [part.strip() for part in parts[1:-1]]
        assert cells[6] == "discovery"
        assert cells[8] in ("no", "yes")  # flown and sealed; closed by scripts/flights/batch/ledger_mark_consumed.py
    assert rows[KEY_ROW][0].split("|")[3].strip() == "model-free-check"
    assert "P(correct given newly delivered)" in rows[RUN][0]
