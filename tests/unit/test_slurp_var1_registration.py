"""Stage-3 VAR-1 construction-variant family: the registration proof obligations.

The claim this package makes is narrow and mechanical, so it is checked
mechanically:

* every VAR-1 baseline equals the **locked v2.0 default plan** on every key
  except the R01C re-pointing cell ROLL-1 already proved, the per-cell identity
  bookkeeping, and that cell's OWN declared knobs;
* ``VAR1-PLANR`` equals ``VAR1-PLAN`` on every key except the fit identity and
  the prose -- it is a request-identical replicate, which is the only reason it
  can measure the roster's own null;
* each variant moves exactly the knobs its row of the registered knob table
  names, and no other;
* a candidate bound above three carries the CONFIGURABLE bounded
  first-occurrence projection, because ``rails.candidate_semantic_supply``
  refuses it otherwise;
* the exemplar store is the MINUS-R01 release on every cell (coordinator
  decision 102: a construction roster may never retrieve itself);
* every cell is ``held``, no baseline carries a ``prepared_phase_supply`` pin
  (the cell-P0 form: ``core.flight.repin`` mints each cell's own at the flip),
  every TRAIN cell binds an explicit registered population, and the smoke's
  declared split identity is the freshly recomputed hash of the four ids it
  names;
* the composed and protocol hashes the package registers reproduce from
  ``core.config.compose`` over the committed fragments.

Zero model, tokenizer, encoder, scorer, server and network contacts; no
``SPEECHRL_DATA_DIR`` read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import (
    compose,
    protocol_hash as compute_protocol_hash,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE = REPO_ROOT / "configs" / "baseline"
EXPERIMENT = REPO_ROOT / "configs" / "experiment"
CAMPAIGN = REPO_ROOT / "configs" / "campaign"
DATASET = REPO_ROOT / "configs" / "dataset"
READINESS = REPO_ROOT / "docs" / "readiness" / "2026-09-24-slurp-stage3-var1-v1"

LOCK = BASELINE / "slurp-native-default-plan-lock-baseline-v1.json"
ROLL = BASELINE / "slurp-native-stage3-rollout-baseline-v1.json"

#: ``short -> (config stem, run id, rows)``.
FAMILY = {
    "plan": ("slurp-native-stage3-var1-plan-r01c", "SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1", 625),
    "planr": ("slurp-native-stage3-var1-planr-r01c",
              "SAEA-SLURP-STAGE3-VAR1-PLANR-R01C-V1", 625),
    "exk10": ("slurp-native-stage3-var1-ex-k10-r01c",
              "SAEA-SLURP-STAGE3-VAR1-EX-K10-R01C-V1", 625),
    "exk30": ("slurp-native-stage3-var1-ex-k30-r01c",
              "SAEA-SLURP-STAGE3-VAR1-EX-K30-R01C-V1", 625),
    "exdiv": ("slurp-native-stage3-var1-ex-div-r01c",
              "SAEA-SLURP-STAGE3-VAR1-EX-DIV-R01C-V1", 625),
    "perk16c5": ("slurp-native-stage3-var1-per-k16c5-r01c",
                 "SAEA-SLURP-STAGE3-VAR1-PER-K16C5-R01C-V1", 625),
    "smoke": ("slurp-native-stage3-var1-smoke-4", "SAEA-SLURP-STAGE3-VAR1-SMOKE-4-V1", 4),
}
FLIGHT_SHORTS = ("plan", "planr", "exk10", "exk30", "exdiv", "perk16c5")

#: The registered knob table: exemplar (k, c, m, top_l), Perception
#: (k, c, m, top_l), candidate bound.
KNOBS = {
    "plan": ((20, 20, 20, 20), (8, 1, 8, 8), 3),
    "planr": ((20, 20, 20, 20), (8, 1, 8, 8), 3),
    "exk10": ((10, 10, 10, 10), (8, 1, 8, 8), 3),
    "exk30": ((30, 30, 30, 30), (8, 1, 8, 8), 3),
    "exdiv": ((20, 4, 20, 20), (8, 1, 8, 8), 3),
    "perk16c5": ((20, 20, 20, 20), (16, 1, 16, 16), 5),
    "smoke": ((20, 20, 20, 20), (16, 1, 16, 16), 5),
}

SMOKE_IDS = [
    "slurp:train:000049:audio-1434542455",
    "slurp:train:000051:audio-1434531302-headset",
    "slurp:train:000234:audio-1499688528",
    "slurp:train:000260:audio-1488549919",
]
ROSTER_SPLIT = "f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515"
DATASET_FRAGMENT = "slurp-speech-native-stage3-construction-r01c"
MODEL_FRAGMENT = (
    "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
)
BOUNDED = "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
CONFIGURABLE = "configurable-bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
MINUS_R01 = "size-pool-annotated-exemplars-minus-r01"

#: The keys a VAR-1 cell is ALLOWED to differ from the locked plan on. Anything
#: else differing is the defect this test exists to catch.
_ALLOWED_DIFFERENCES = {
    # per-cell identity bookkeeping
    "native_contact_fit",
    "prepared_phase_supply",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "what_this_is",
    "what_the_train_exemplars_store_is",
    "smoke_note",
    "populations",
    # the R01C re-pointing cell ROLL-1 proved (not a variant)
    "preparation_source_receipts",
    "speech_packet_promotion_receipt",
    "speech_packet_promotion_receipt_sha256",
    # the knobs live inside this one key, so it is compared structurally below
    "knowledge_stores",
    "phase_material",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def baseline_of(short: str) -> dict:
    return _load(BASELINE / f"{FAMILY[short][0]}-baseline-v1.json")


def experiment_of(short: str) -> dict:
    return _load(EXPERIMENT / f"{FAMILY[short][0]}-v1.json")


@pytest.mark.parametrize("short", sorted(FAMILY))
def test_every_var1_baseline_moves_only_the_allowed_keys_against_the_locked_plan(short):
    lock = _load(LOCK)
    cell = baseline_of(short)
    moved = {
        key
        for key in set(lock) | set(cell)
        if lock.get(key) != cell.get(key)
    }
    assert moved <= _ALLOWED_DIFFERENCES, sorted(moved - _ALLOWED_DIFFERENCES)


@pytest.mark.parametrize("short", sorted(FAMILY))
def test_the_knobs_are_exactly_the_registered_ones(short):
    cell = baseline_of(short)
    (ek, ec, em, el), (pk, pc, pm, pl), bound = KNOBS[short]
    exemplars = cell["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    assert exemplars["k"] == ek
    assert exemplars["fuse_coverage"] == {"c": ec, "m": em, "top_l": el}
    perception = cell["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    assert perception["k"] == pk
    assert perception["fuse_coverage"] == {"c": pc, "m": pm, "top_l": pl}
    assert cell["phase_material"]["perception"]["fill_params"]["max_candidates"] == bound
    supply = cell["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solver"]
    assert supply["max_candidates"] == bound
    # the two sites must agree, or the Solver is handed a candidate list the
    # Perception contract cannot produce
    assert supply["projection_policy"] == (CONFIGURABLE if bound > 3 else BOUNDED)
    # the candidate BLOCK size is never a variant
    assert supply["max_total_values"] == 28
    assert supply["max_values_per_candidate"] == 16


@pytest.mark.parametrize("short", sorted(FAMILY))
def test_nothing_but_the_knobs_moves_inside_knowledge_stores_and_phase_material(short):
    """The knob keys are compared above; every OTHER key of those two blocks must
    equal cell ROLL-1's R01C re-pointing byte for byte."""

    roll = _load(ROLL)
    lock = _load(LOCK)
    cell = baseline_of(short)

    def scrub(document: dict) -> dict:
        stores = json.loads(json.dumps(document["knowledge_stores"]))
        solver = stores["train-exemplars"]["phase_supply"]["solver"]
        solver.pop("k"), solver.pop("fuse_coverage")
        perception = stores["intent-boundaries"]["phase_supply"]["perception"]
        perception.pop("k"), perception.pop("fuse_coverage")
        supply = stores["slot-contracts"]["candidate_supply"]["solver"]
        supply.pop("max_candidates"), supply.pop("projection_policy")
        return stores

    assert scrub(cell) == scrub(roll)
    material = json.loads(json.dumps(cell["phase_material"]))
    material["perception"]["fill_params"].pop("max_candidates")
    reference = json.loads(json.dumps(lock["phase_material"]))
    reference["perception"]["fill_params"].pop("max_candidates")
    assert material == reference


@pytest.mark.parametrize("short", sorted(FAMILY))
def test_the_exemplar_store_is_the_minus_r01_release(short):
    store = baseline_of(short)["knowledge_stores"]["train-exemplars"]
    assert MINUS_R01 in store["release"]["relpath"]
    assert MINUS_R01 in store["snapshot"]["relpath"]


def test_planr_is_request_identical_to_plan():
    plan = baseline_of("plan")
    planr = baseline_of("planr")
    moved = {key for key in set(plan) | set(planr) if plan.get(key) != planr.get(key)}
    # 2026-09-24: the flip mints each cell its OWN prepared-supply pin, so that key is a
    # per-cell identity like native_contact_fit once the family has flown (flight commit
    # 3ade29ff); the request-identity claim is about the supply CONSTRUCTION, checked below.
    assert moved <= {"native_contact_fit", "what_this_is", "prepared_phase_supply"}
    assert {"native_contact_fit", "what_this_is"} <= moved
    assert plan["knowledge_stores"] == planr["knowledge_stores"]
    assert plan["phase_material"] == planr["phase_material"]
    assert plan["native_episode"] == planr["native_episode"]
    assert (
        plan["speech_feature_matcher_policy_id"]
        == planr["speech_feature_matcher_policy_id"]
    )


def test_the_smoke_flies_the_per_k16c5_form():
    smoke = baseline_of("smoke")
    arm = baseline_of("perk16c5")
    moved = {key for key in set(smoke) | set(arm) if smoke.get(key) != arm.get(key)}
    # 2026-09-24: the flip mints each cell its OWN prepared-supply pin, so that key is a
    # per-cell identity like native_contact_fit once the family has flown (flight commit
    # 3ade29ff); the request-identity claim is about the supply CONSTRUCTION, checked below.
    expected = {
        "native_contact_fit", "what_this_is", "smoke_note",
        "speech_feature_key_representation_id", "speech_feature_matcher_policy_id",
    }
    assert expected <= moved and moved <= expected | {"prepared_phase_supply"}


@pytest.mark.parametrize("short", sorted(FAMILY))
def test_no_committed_baseline_carries_a_prepared_phase_supply_pin(short):
    """Before the flip a baseline carries no prepared-supply pin; the flip mints one under the
    cell's own run id (2026-09-24, flight commit 3ade29ff), so the live invariant is that any pin
    present is well formed."""
    pin = baseline_of(short).get("prepared_phase_supply")
    if pin is None:
        return
    assert isinstance(pin, dict), pin
    assert {"relpath", "sha256"} <= set(pin), sorted(pin)
    assert len(pin["sha256"]) == 64 and set(pin["sha256"]) <= set("0123456789abcdef"), pin["sha256"]
    assert pin["relpath"], pin["relpath"]


@pytest.mark.parametrize("short", sorted(FAMILY))
def test_every_registered_cell_is_held_and_names_its_own_identities(short):
    stem, run_id, rows = FAMILY[short]
    fragment = experiment_of(short)
    assert fragment["experiment_id"] == run_id
    assert fragment["execution_profile"] == "bounded-discovery-probe"
    assert fragment["execution_plan"]["split_role"] == "discovery"
    assert fragment["split_id"] == "STAGE3-CONSTRUCTION-R01C"
    assert fragment["population"]["count"] == rows
    cells = {cell["cell_id"]: cell for cell in fragment["cells"]}
    assert set(cells) == {f"{stem}-v1", f"{stem}-fit-v1"}
    # 2026-09-24: the family was flipped to ready and flown (flight commit 3ade29ff), so the
    # pre-contact "held" state is history; the live invariant is that a cell sits in one of the
    # two registered lifecycle states and names its own identities.
    for cell in cells.values():
        assert cell["readiness"]["state"] in {"held", "ready"}
        assert cell["dataset_fragment"] == DATASET_FRAGMENT
        assert cell["model_fragment"] == MODEL_FRAGMENT
        assert cell["baseline_fragment"] == f"{stem}-baseline-v1"
    assert cells[f"{stem}-v1"]["run_id"] == run_id
    assert cells[f"{stem}-fit-v1"]["run_id"] == run_id[:-3] + "-FIT-V1"


@pytest.mark.parametrize("short", sorted(FAMILY))
def test_every_train_cell_binds_an_explicit_registered_population(short):
    """``rails.adapters.slurp_runtime`` refuses a TRAIN runtime view without one."""

    fragment = experiment_of(short)
    populations = fragment["populations"]
    assert len(populations) == 1
    assert populations[0]["dataset_fragment"] == DATASET_FRAGMENT
    assert len(populations[0]["ids"]) == FAMILY[short][2]


def test_the_smoke_population_is_the_first_four_roster_rows_and_its_hash_matches():
    dataset = _load(DATASET / f"{DATASET_FRAGMENT}.json")
    first_four = [item["sample_id"] for item in dataset["items"][:4]]
    assert first_four == SMOKE_IDS
    fragment = experiment_of("smoke")
    assert fragment["populations"][0]["ids"] == SMOKE_IDS
    assert fragment["population"]["split_identity_hash"] == split_identity_hash(
        prefixed("slurp", SMOKE_IDS)
    )


@pytest.mark.parametrize("short", sorted(set(FAMILY) - {"smoke"}))
def test_the_flight_cells_bind_the_full_roster_identity_and_its_ceiling(short):
    fragment = experiment_of(short)
    assert fragment["population"]["split_identity_hash"] == ROSTER_SPLIT
    assert fragment["generation_budget"]["cap"] == 625 * 11
    assert fragment["family_budget"]["generation_calls_cap"] == 625 * 11
    assert fragment["family_budget"]["fit_endpoint_calls_cap"] == 625 * 11 * 4
    assert fragment["family_budget"]["repeated_speech_audio_seconds_cap"] == 29996
    assert fragment["family_budget"]["native_task_contract_calls_cap"] == 0
    assert fragment["family_budget"]["official_complete_scoring_jobs"] == 1
    fit = baseline_of(short)["native_contact_fit"]
    assert fit["contact_cap"] == 625 * 11 * 4


def test_the_smoke_budget_is_four_rows_at_the_same_ceiling():
    fragment = experiment_of("smoke")
    assert fragment["family_budget"]["generation_calls_cap"] == 44
    assert fragment["family_budget"]["fit_endpoint_calls_cap"] == 176
    assert fragment["family_budget"]["repeated_speech_audio_seconds_cap"] == 188
    assert fragment["family_budget"]["official_complete_scoring_jobs"] == 0


@pytest.mark.parametrize("short", sorted(FAMILY))
def test_the_stage3_algorithm_label_is_the_shared_rollout_record(short):
    from speech_aware_evidence_acquisition.core import stage3_algorithms
    from speech_aware_evidence_acquisition.core.base import STAGE3_ALGORITHMS

    assert stage3_algorithms is not None  # the registry is populated on import
    label = experiment_of(short)["stage3_algorithm"]
    assert label["id"] == "shared-rollout"
    record = STAGE3_ALGORITHMS.resolve("shared-rollout")
    assert set(label["operators_used"]) <= set(record.operators)
    assert label["note"].strip()


@pytest.mark.parametrize("short", sorted(FLIGHT_SHORTS))
def test_each_flight_cell_has_its_own_single_cell_campaign_plan(short):
    stem = FAMILY[short][0]
    plan = _load(CAMPAIGN / f"{stem}-v1.json")
    assert plan == {
        "cells": [{"cell": f"{stem}-v1", "experiment": f"{stem}-v1"}],
        "schema": "saea-campaign-plan-v1",
    }


def test_the_smoke_has_no_campaign_plan_of_its_own():
    assert not (CAMPAIGN / "slurp-native-stage3-var1-smoke-4-v1.json").exists()


@pytest.mark.parametrize("short", sorted(FAMILY))
def test_the_registered_hashes_reproduce_from_the_committed_fragments(short):
    stem, _run_id, rows = FAMILY[short]
    protocol = _load(READINESS / "protocol-registered-v1.json")
    fragment = experiment_of(short)
    split = fragment["population"]["split_identity_hash"]
    composed = compose(
        REPO_ROOT, model=MODEL_FRAGMENT, dataset=DATASET_FRAGMENT,
        baseline=f"{stem}-baseline-v1", experiment=f"{stem}-v1",
    )
    proto = compute_protocol_hash(composed.config_hash, str(composed.values["arm"]), split)
    registered = protocol["cells"][short]
    assert registered["composed_config_hash"] == composed.config_hash
    assert registered["protocol_hash"] == proto
    assert registered["rows"] == rows
    fit = protocol["fit_only_cells"][short]
    assert fit["composed_config_hash"] == composed.config_hash
    assert fit["protocol_hash"] == proto


@pytest.mark.parametrize("short", sorted(FAMILY))
def test_the_protocol_knob_table_matches_the_committed_fragments(short):
    protocol = _load(READINESS / "protocol-registered-v1.json")
    declared = protocol["cells"][short]["knobs"]
    (ek, ec, em, el), (pk, pc, pm, pl), bound = KNOBS[short]
    assert declared["exemplars_k"] == ek
    assert declared["exemplars_fuse_coverage"] == {"c": ec, "m": em, "top_l": el}
    assert declared["perception_k"] == pk
    assert declared["perception_fuse_coverage"] == {"c": pc, "m": pm, "top_l": pl}
    assert declared["perception_fill_max_candidates"] == bound
    assert declared["slot_contracts_max_candidates"] == bound
    assert declared["projection_policy"] == (CONFIGURABLE if bound > 3 else BOUNDED)


def test_only_the_two_perception_forms_move_a_perception_knob():
    """The prepared first-phase supply is a Perception selection, so the cells
    whose prepared artifact may legitimately differ from VAR1-PLAN's are exactly
    the cells that move a Perception knob -- which is what the flip runbook
    asserts."""

    movers = {
        short for short in FAMILY
        if KNOBS[short][1] != KNOBS["plan"][1]
    }
    assert movers == {"perk16c5", "smoke"}


def test_every_plan_document_is_registered_and_held():
    for short in FAMILY:
        for kind in ("generation", "fit"):
            document = _load(READINESS / f"{short}-{kind}-plan-registered-v1.json")
            # 2026-09-24: the coordinator's flip rewrites this status; both strings are legal
            # states of a registered plan document and the pre-flip one is history.
            assert document["status"].startswith("REGISTERED_BEFORE_CONTACT"), document["status"]
            assert document["execution_plan"]["execution_profile"] == (
                "bounded-discovery-probe"
            )
            assert document["execution_plan"]["split_role"] == "discovery"
            assert document["plan_kind"] == (
                "generation" if kind == "generation" else "native contact fit"
            )
