"""Cell CONV -- the conversion probe -- is the AGREE treatment on a proven roster.

Config only: no data root, no lock, no adapter, no contact. Every assertion here
is a property a reader of the registration should be able to take for granted,
and each one is a defect this registration could plausibly have shipped.
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

CELL = "slurp-native-stage3-conv-fold-a-70-v1"
RUN = "SAEA-SLURP-STAGE3-CONV-FOLD-A-70-V1"
FIT_RUN = "SAEA-SLURP-STAGE3-CONV-FOLD-A-70-FIT-V1"
PARENT_EXPERIMENT = "slurp-native-stage3-agree-w1-fold-a-v1"
PACKAGE = REPO / "docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1"
DERIVATION = PACKAGE / "roster-derivation-v1.json"
ROSTER_ROWS = 70
CONTACTS_PER_ROW = 11
#: The committed production-replication receipt the roster is proven against.
RECEIPT_SHA256 = "7cd1f6d338731ea7b6eef34408e5d37453c852670900319445968ddc2a1dc624"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def experiment() -> dict:
    return _read(REPO / "configs/experiment" / f"{CELL}.json")


@pytest.fixture(scope="module")
def derivation() -> dict:
    return _read(DERIVATION)


@pytest.fixture(scope="module")
def composed(experiment: dict):
    cell = experiment["cells"][0]
    return compose(
        REPO,
        cell["model_fragment"],
        cell["dataset_fragment"],
        cell["baseline_fragment"],
        CELL,
    )


def test_roster_derivation_reproduced_the_committed_receipt(derivation: dict) -> None:
    proof = derivation["proof"]
    assert proof["differences"] == []
    assert proof["receipt_sha256"] == RECEIPT_SHA256
    assert proof["recipe_imported_unchanged"] is True
    committed = proof["committed_plan_class_split"]
    rebuilt = proof["reconstructed_plan_class_split"]
    assert committed["newly_delivered"] == ROSTER_ROWS
    assert committed["newly_lost"] == 0
    for key, value in rebuilt.items():
        assert committed[key] == value, key


def test_the_committed_receipt_still_hashes_to_what_the_derivation_proved() -> None:
    receipt = REPO / _read(DERIVATION)["proof"]["receipt_relpath"]
    assert hashlib.sha256(receipt.read_bytes()).hexdigest() == RECEIPT_SHA256


def test_roster_ids_are_seventy_distinct_fold_a_rows(derivation: dict) -> None:
    ids = derivation["roster"]["ids"]
    assert len(ids) == ROSTER_ROWS
    assert len(set(ids)) == ROSTER_ROWS
    assert ids == sorted(ids)
    manifest = _read(
        REPO / "configs/dataset" / (derivation["roster"]["dataset_fragment"] + ".json")
    )
    available = {str(item["sample_id"]) for item in manifest["items"]}
    assert set(ids) <= available


def test_id_list_digest_and_split_identity_are_hashes_of_those_ids(
    derivation: dict,
) -> None:
    ids = derivation["roster"]["ids"]
    assert (
        hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
        == derivation["roster"]["id_list_sha256"]
    )
    assert derivation["roster"]["split_identity_hash"] == split_identity_hash(
        prefixed(derivation["roster"]["carrier_lock_key"], ids)
    )


def test_the_fragment_flies_exactly_the_derived_ids(
    experiment: dict, derivation: dict
) -> None:
    population = experiment["population"]
    assert population["count"] == ROSTER_ROWS
    assert population["split_identity_hash"] == derivation["roster"][
        "split_identity_hash"
    ]
    assert len(experiment["populations"]) == 1
    inline = experiment["populations"][0]
    assert inline["dataset_fragment"] == derivation["roster"]["dataset_fragment"]
    assert inline["ids"] == derivation["roster"]["ids"]


def test_split_identity_matches_a_fresh_hash_over_the_inline_ids(
    experiment: dict, composed
) -> None:
    ids = experiment["populations"][0]["ids"]
    recomputed = split_identity_hash(prefixed(composed.values["carrier_lock_key"], ids))
    assert recomputed == experiment["population"]["split_identity_hash"]


def test_every_treatment_knob_is_the_agree_arm_s(composed) -> None:
    parent = compose(
        REPO,
        *(
            _read(REPO / "configs/experiment" / f"{PARENT_EXPERIMENT}.json")["cells"][0][
                key
            ]
            for key in ("model_fragment", "dataset_fragment", "baseline_fragment")
        ),
        PARENT_EXPERIMENT,
    )
    for values in (composed.values, parent.values):
        assert values["policy"] == "phase-native-candidates-review-revise-v1"
    mine = composed.values["knowledge_stores"]["intent-boundaries"]["phase_supply"][
        "perception"
    ]
    theirs = parent.values["knowledge_stores"]["intent-boundaries"]["phase_supply"][
        "perception"
    ]
    assert mine == theirs
    assert mine["rank_weights"] == {"w_agree": 1.0, "w_cos": 1.0, "w_prior": 0.0}
    assert mine["k"] == 60
    assert mine["tau"] == 0.0
    assert mine["fuse_coverage"] == {"m": 8, "c": 1, "top_l": 8}
    assert mine["agreement_source"]["kind"] == "sealed-agreement"
    assert composed.values["scorers"] == parent.values["scorers"]
    assert composed.values["arm"] == parent.values["arm"]
    assert (
        composed.values["knowledge_stores"].keys()
        == parent.values["knowledge_stores"].keys()
    )


def test_prepared_phase_supply_is_absent_or_the_cells_own(
    composed, experiment: dict
) -> None:
    """The agreement merge invalidated every prepared_phase_supply pin; this
    cell carried none as registered (baa97b1b) and the flip (9255ac71) minted
    its own (item E16). Either state is recorded truth; a foreign supply never is."""

    baseline = _read(
        REPO / "configs/baseline" / (experiment["cells"][0]["baseline_fragment"] + ".json")
    )
    for doc in (composed.values, baseline):
        supply = doc.get("prepared_phase_supply")
        if supply is None:
            continue
        assert supply["relpath"].startswith(f"prepared/{RUN}/"), supply


def test_readiness_is_held_with_an_empty_requirements_list(experiment: dict) -> None:
    """Empty on purpose: core.flight.repin._set_preparation_requirement rewrites
    EVERY 'preparation' entry to the freshly minted supply pin, so a second one
    would be silently clobbered."""

    readiness = experiment["cells"][0]["readiness"]
    # `held` with the empty list as registered (baa97b1b); `ready` after the flip (9255ac71), whose re-pin appends
    # exactly the decision receipt and this cell's OWN prepared supply.
    assert readiness["state"] in ("held", "ready")
    if readiness["state"] == "held":
        assert readiness["requirements"] == []
        assert "--allow-output-change must never be passed" in readiness["reason"]
    else:
        kinds = sorted(req["kind"] for req in readiness["requirements"])
        assert kinds == ["decision", "preparation"], kinds
        for req in readiness["requirements"]:
            if req["kind"] == "preparation":
                assert req["relpath"].startswith(f"prepared/{RUN}/"), req


def test_caps_are_the_declared_arithmetic(experiment: dict, derivation: dict) -> None:
    caps = experiment["family_budget"]
    generation = ROSTER_ROWS * CONTACTS_PER_ROW
    assert caps["generation_calls_cap"] == generation == 770
    assert caps["fit_endpoint_calls_cap"] == 4 * generation == 3080
    assert caps["native_task_contract_calls_cap"] == 6 * ROSTER_ROWS == 420
    audio = derivation["roster"]["audio_seconds_total"]
    assert caps["repeated_speech_audio_seconds_cap"] == -(-int(audio * CONTACTS_PER_ROW * 1000) // 1000)
    assert caps["asr_calls"] == 0
    assert caps["encoder_calls"] == 0
    assert caps["official_complete_scoring_jobs"] == 1
    assert experiment["generation_budget"]["cap"] == generation
    plan = experiment["execution_plan"]
    assert plan["planned_model_calls"] == generation
    assert plan["planned_speech_audio_seconds"] == caps[
        "repeated_speech_audio_seconds_cap"
    ]
    assert plan["planned_gpu_hours"] == caps["gpu_hours_fit_inclusive"]
    assert plan["split_role"] == "discovery"
    assert experiment["execution_profile"] == "bounded-discovery-probe"


def test_the_fit_identity_is_this_cell_s_own(composed) -> None:
    fit = composed.values["native_contact_fit"]
    assert fit["run_id"] == FIT_RUN
    assert fit["attempt_id"] == "attempt-slurp-native-stage3-conv-fold-a-70-fit-v1"
    assert fit["contact_cap"] == 4 * ROSTER_ROWS * CONTACTS_PER_ROW


def test_the_failure_mode_policies_are_the_two_the_gate_requires(composed) -> None:
    episode = composed.values["native_episode"]
    assert episode["finite_completion_policy"] == "deliver-latest-or-abstain"
    assert episode["react_exhaustion_policy"] == "continue-without-answer"


def test_the_measurement_declaration_is_a_form_proof_that_claims_nothing() -> None:
    facts = _read(PACKAGE / "registered-facts-v1.json")
    block = facts["stage3_measurement"][RUN]
    assert block["measurement_design"] == "form-proof"
    assert block["claims_benefit"] is False
    assert block["expected_effect_pp"] == 0.0
    assert block["rows"] == ROSTER_ROWS
    # Not an admission request: 'no-harm' is for a base item being admitted.
    assert "admission" not in block
    assert "harm_margin_pp" not in block
    assert "conditional rate" in block["note"].lower()
    assert "no effectiveness claim" in block["note"].lower()


def test_the_preregistration_fence_repeats_the_canonical_block() -> None:
    text = (
        REPO / "docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1-preregistration.md"
    ).read_text(encoding="utf-8")
    start = text.index("```json")
    fenced = json.loads(text[text.index("\n", start) + 1 : text.index("```", start + 7)])
    canonical = _read(PACKAGE / "registered-facts-v1.json")["stage3_measurement"]
    assert fenced["stage3_measurement"] == canonical


def test_the_stage3_algorithm_label_is_none_with_its_reason(experiment: dict) -> None:
    label = experiment["stage3_algorithm"]
    assert label["id"] == "none"
    assert label["operators_used"] == []
    assert "NO training-free RL operator" in label["note"]


def test_the_package_forbids_a_pooled_claim_in_so_many_words() -> None:
    for name in ("registered-facts-v1.json", "protocol-registered-v1.json"):
        text = (PACKAGE / name).read_text(encoding="utf-8")
        assert "SELECTED USING GOLD" in text
        assert "NO POOLED OR ROSTER-LEVEL CLAIM MAY EVER BE MADE" in text
    derived = _read(DERIVATION)
    assert "NO POOLED OR ROSTER-LEVEL CLAIM MAY EVER BE MADE" in derived["gold_use"]


def test_the_campaign_plan_is_this_single_cell(experiment: dict) -> None:
    plan = _read(REPO / "configs/campaign" / f"{CELL}.json")
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [{"cell": CELL, "experiment": CELL}]
    assert "campaign" in experiment["cells"][0]["allowed_execution_stages"]


def test_the_plan_documents_carry_the_recomposed_hashes(
    composed, experiment: dict
) -> None:
    split = experiment["population"]["split_identity_hash"]
    expected = protocol_hash(composed.config_hash, composed.values["arm"], split)
    for name, run in (
        ("generation-plan-registered-v1.json", RUN),
        ("fit-plan-registered-v1.json", FIT_RUN),
    ):
        plan = _read(PACKAGE / name)
        assert plan["composed_config_hash"] == composed.config_hash
        assert plan["execution_plan"]["protocol_hash"] == expected
        assert plan["execution_plan"]["run_id"] == run
        assert plan["execution_plan"]["split_identity_hash"] == split
        assert plan["prepared_phase_supply"]["sha256"] == "MINTED_AT_THE_FLIP"


def test_both_exposure_rows_exist_and_no_cell_contains_a_pipe() -> None:
    """A literal '|' inside a cell silently splits the row, and
    contracts.ledger._parse_ledger_tables then refuses the whole ledger."""

    lines = io.open(
        REPO / "docs/exposure-ledger.md", encoding="utf-8", newline=""
    ).read().split("\n")
    rows = [
        line
        for line in lines
        if line.startswith("|") and ("| " + RUN + " |" in line or "| " + FIT_RUN + " |" in line)
    ]
    assert len(rows) == 2
    for line in rows:
        parts = line.split("|")
        assert len(parts) == 17, parts[:3]
        cells = [part.strip() for part in parts[1:-1]]
        assert cells[6] == "discovery"
        # "no" as registered; "yes" once the flight sealed (SEALED AND READ 2026-09-27, flight commit 9255ac71).
        assert cells[8] in ("no", "yes")
        assert "P(correct given newly delivered)" in line or cells[1] == FIT_RUN
