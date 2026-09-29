"""Cell COMP-1b -- COMP-1 minus the citation contract -- is cell COMP-1's OWN
committed, already-flown arm and smoke with the citation contract's four leaf
paths reverted to the locked plan's own non-cited program, one arming, and
NOTHING else: the agreement term and the centroid boundary key are COMP-1's own
committed bytes, byte for byte. The comparator is the EXISTING SEALED in-chain
A/A cell COMP-1 already flew, reused cross-flight and never re-flown or
re-registered by this family (owner decision 160's shared-A/A pattern).

Config only: no data root, no lock, no adapter, no contact. Every assertion here
is a property a reader of the registration should be able to take for granted,
and each one is a defect this registration could plausibly have shipped.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.stage3_algorithms import validate_stage3_algorithm_label

REPO = Path(__file__).resolve().parents[2]

ARM = "slurp-native-stage3-comp1b-fold-a-v1"
SMOKE = "slurp-native-stage3-comp1b-fold-a-smoke-4-v1"
COMP1_ARM = "slurp-native-stage3-comp1-fold-a-v1"
COMP1_SMOKE = "slurp-native-stage3-comp1-fold-a-smoke-4-v1"
RUNS = {
    ARM: ("SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1", "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-FIT-V1"),
    SMOKE: ("SAEA-SLURP-STAGE3-COMP1B-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-SMOKE-4-FIT-V1"),
}
PACKAGE = REPO / "docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1"
PREREG = REPO / "docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1-preregistration.md"
COMPARATOR_RUN = "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"
COMP1_ARM_SUPPLY_OUTPUT_SHA = "ce68bebcf2bbf5502b081221a92c3fde1095da3979106bcdddb6eeeca9e9c41a"

# The citation-contract factor cell COMP-1b reverts: FOUR leaf JSON paths, one
# arming across three JSON locations (top-level ``policy``, the two
# ``phase_material.solver`` keys, and ``native_episode.deliver_normaliser``).
# The task that produced this cell described it as "the three citation-contract
# settings" -- policy, the Solver material (template + response format, one
# object), and the normaliser -- which is the same one arming counted by
# location rather than by leaf value.
CITATION_FACTOR_PATHS = (
    "policy",
    "phase_material.solver.instruction_template",
    "phase_material.solver.response_format_id",
    "native_episode.deliver_normaliser.normaliser",
)
BOOKKEEPING = ("native_contact_fit.", "prepared_phase_supply", "preparation_source_receipts", "what_this_is")

DECISION_ID = "slurp-stage3-comp1b-fold-a-admission-v1"


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


def _composed(experiment: str):
    document = _read(REPO / "configs/experiment" / f"{experiment}.json")
    cell = document["cells"][0]
    return document, cell, compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)


def _matches(key: str, path: str) -> bool:
    return key == path or (path.endswith(".") and key.startswith(path))


def _diff(parent_values, mine, experiment_keys, allowed):
    a, b = _flatten(parent_values), _flatten(mine)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    factor = [k for k in changed if any(_matches(k, p) for p in allowed)]
    bookkeeping = [k for k in changed if k not in factor and k.startswith(BOOKKEEPING)]
    experiment_block = [k for k in changed if k not in factor and k not in bookkeeping and k.split(".", 1)[0] in experiment_keys]
    other = [k for k in changed if k not in factor and k not in bookkeeping and k not in experiment_block]
    return factor, bookkeeping, experiment_block, other


@pytest.fixture(scope="module")
def cells():
    return {name: _composed(name) for name in (ARM, SMOKE)}


@pytest.fixture(scope="module")
def comp1_cells():
    return {name: _composed(name) for name in (COMP1_ARM, COMP1_SMOKE)}


@pytest.fixture(scope="module")
def facts():
    return _read(PACKAGE / "registered-facts-v1.json")


def test_the_arm_differs_from_comp1_by_exactly_the_citation_contract_and_bookkeeping(cells, comp1_cells):
    doc, _cell, composed = cells[ARM]
    pdoc, _pcell, parent = comp1_cells[COMP1_ARM]
    factor, _bk, _exp, other = _diff(parent.values, composed.values, set(doc) | set(pdoc), CITATION_FACTOR_PATHS)
    assert other == [], other
    assert sorted(factor) == sorted(CITATION_FACTOR_PATHS)


def test_the_smoke_differs_from_comp1s_smoke_by_exactly_the_citation_contract_and_bookkeeping(cells, comp1_cells):
    doc, _cell, composed = cells[SMOKE]
    pdoc, _pcell, parent = comp1_cells[COMP1_SMOKE]
    factor, _bk, _exp, other = _diff(parent.values, composed.values, set(doc) | set(pdoc), CITATION_FACTOR_PATHS)
    assert other == [], other
    assert sorted(factor) == sorted(CITATION_FACTOR_PATHS)


def test_the_four_keys_move_exactly_this_way(cells, comp1_cells):
    """Quotes the exact old/new value of each of the four leaf paths the family task named."""

    _doc, _cell, comp1b = cells[ARM]
    _pdoc, _pcell, comp1 = comp1_cells[COMP1_ARM]
    assert comp1.values["policy"] == "phase-native-candidates-review-revise-cited-v1"
    assert comp1b.values["policy"] == "phase-native-candidates-review-revise-v1"
    comp1_solver = comp1.values["phase_material"]["solver"]
    comp1b_solver = comp1b.values["phase_material"]["solver"]
    assert comp1_solver["instruction_template"] == "probes/slurp_native_role_solver_cited_v1.txt"
    assert comp1b_solver["instruction_template"] == "probes/slurp_native_role_solver_v2.txt"
    assert comp1_solver["response_format_id"] == "saea-solver-cited-answer-v1"
    assert comp1b_solver["response_format_id"] is None
    assert comp1.values["native_episode"]["deliver_normaliser"] == {"normaliser": "saea-deliver-cited-answer-normalise-v3-v1"}
    assert comp1b.values["native_episode"]["deliver_normaliser"] == {"normaliser": "saea-deliver-normalise-v3"}


def test_the_agreement_term_and_centroid_key_are_comp1s_own_byte_for_byte(cells, comp1_cells):
    for arm_name, comp1_name in ((ARM, COMP1_ARM), (SMOKE, COMP1_SMOKE)):
        _doc, _cell, composed = cells[arm_name]
        _pdoc, _pcell, parent = comp1_cells[comp1_name]
        mine = composed.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
        theirs = parent.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
        assert mine == theirs
        assert mine["rank_weights"] == {"w_agree": 1.0, "w_cos": 1.0, "w_prior": 0.0}
        assert mine["k"] == 60
        assert "agreement_source" in mine
        assert mine["facet_source"]["relpath"] == "prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl"


def test_the_receipts_and_every_other_store_pin_are_comp1s_own(cells, comp1_cells):
    for arm_name, comp1_name in ((ARM, COMP1_ARM), (SMOKE, COMP1_SMOKE)):
        _doc, _cell, composed = cells[arm_name]
        _pdoc, _pcell, parent = comp1_cells[comp1_name]
        assert composed.values["preparation_source_receipts"] == parent.values["preparation_source_receipts"]
        for store in ("intent-boundaries", "train-exemplars", "slot-contracts"):
            for pin in ("snapshot", "release"):
                assert composed.values["knowledge_stores"][store][pin] == parent.values["knowledge_stores"][store][pin]
        assert composed.values["scorers"] == parent.values["scorers"]
        assert composed.values["arm"] == parent.values["arm"]
        assert composed.values["serving_slot_tokens"] == parent.values["serving_slot_tokens"]
        assert composed.values["serving_slots"] == parent.values["serving_slots"]


def test_each_cell_pins_its_own_prepared_phase_supply_and_no_cell_pins_anothers(cells, comp1_cells):
    """Post-flip invariant (flip at c6e98e6b, re-pinned by scripts/flights/repin_cell.py).

    Before the flip no prepared phase supply was committed. The flip re-minted
    each cell's own first-phase supply, so the invariant is now: each COMP-1b
    cell pins exactly one prepared phase supply, under its OWN run id, declared
    once among its readiness requirements, and no cell pins another cell's
    supply (neither its sibling's nor COMP-1's).
    """

    pins = {}
    for name, (doc, cell, composed) in cells.items():
        run_id, fit_run = RUNS[name]
        assert cell["run_id"] == run_id
        assert composed.values["native_contact_fit"]["run_id"] == fit_run
        supply = composed.values.get("prepared_phase_supply")
        assert supply is not None
        assert supply["relpath"] == f"prepared/{run_id}/phase-supply-v1.json"
        sha = supply["sha256"]
        assert isinstance(sha, str) and len(sha) == 64 and all(ch in "0123456789abcdef" for ch in sha)
        pins[name] = (supply["relpath"], sha)
        assert cell["readiness"]["state"] == "ready"
        own = [r for r in cell["readiness"]["requirements"] if r["relpath"].endswith("phase-supply-v1.json")]
        assert len(own) == 1
        assert own[0]["kind"] == "preparation"
        assert own[0]["relpath"] == supply["relpath"]
        if "sha256" in own[0]:
            assert own[0]["sha256"] == sha
        decisions = [r for r in cell["readiness"]["requirements"] if r["kind"] == "decision"]
        assert len(decisions) == 1
        assert decisions[0]["relpath"] == "coordination/slurp-stage3-comp1b-fold-a-v1/root-admission-v1.json"
        agreement = [r for r in cell["readiness"]["requirements"] if r["relpath"].endswith("agreement.jsonl")]
        assert len(agreement) == 1
    # No cell pins another's supply: the two COMP-1b pins are distinct in path and bytes ...
    assert len({relpath for relpath, _sha in pins.values()}) == len(pins)
    assert len({sha for _relpath, sha in pins.values()}) == len(pins)
    # ... and neither is one of COMP-1's own pins.
    for _pdoc, _pcell, parent in comp1_cells.values():
        theirs = parent.values.get("prepared_phase_supply")
        if theirs is None:
            continue
        for relpath, sha in pins.values():
            assert relpath != theirs["relpath"]
            assert sha != theirs["sha256"]


def test_the_caps_are_comp1s_own(cells):
    for name, (doc, _cell, composed) in cells.items():
        caps = doc["family_budget"]
        rows = doc["population"]["count"]
        assert rows == (4 if name == SMOKE else 1080)
        assert caps["generation_calls_cap"] == rows * 11
        assert caps["fit_endpoint_calls_cap"] == 4 * rows * 11
        assert caps["native_task_contract_calls_cap"] == rows * 6
        assert composed.values["native_contact_fit"]["contact_cap"] == caps["fit_endpoint_calls_cap"]
        assert doc["execution_plan"]["planned_model_calls"] == caps["generation_calls_cap"]
        assert doc["execution_profile"] == "bounded-discovery-probe"
        assert doc["execution_plan"]["split_role"] == "discovery"


def test_the_roster_is_identical_to_comp1s(cells, comp1_cells):
    for arm_name, comp1_name in ((ARM, COMP1_ARM), (SMOKE, COMP1_SMOKE)):
        doc, _cell, _composed = cells[arm_name]
        pdoc, _pcell, _parent = comp1_cells[comp1_name]
        assert doc["population"]["split_identity_hash"] == pdoc["population"]["split_identity_hash"]
        assert doc["population"]["count"] == pdoc["population"]["count"]


def test_the_measurement_declaration_is_a_declared_number_not_a_placeholder(facts):
    block = facts["stage3_measurement"]
    arm, smoke = (block[RUNS[n][0]] for n in (ARM, SMOKE))
    assert arm["expected_effect_pp"] == 4.26
    assert arm["claims_benefit"] is True
    assert arm["measurement_design"] == "cross-flight-with-in-chain-replicate"
    assert arm["replicate_run_id"] == COMPARATOR_RUN
    assert arm["primary_metric_key"] == "intent"
    assert arm["rows"] == 1080 and "intent" in arm["primary_metric"]
    assert smoke["measurement_design"] == "form-proof" and smoke["claims_benefit"] is False and smoke["rows"] == 4
    assert smoke["tuning_roster"] == "none"


def test_the_preregistration_fence_repeats_the_canonical_block(facts):
    text = PREREG.read_text(encoding="utf-8")
    start = text.index("```json")
    fenced = json.loads(text[text.index("\n", start) + 1 : text.index("```", start + 7)])
    assert fenced["stage3_measurement"] == facts["stage3_measurement"]


def test_the_stage3_labels_resolve(cells):
    for name, (doc, _cell, _composed) in cells.items():
        record, used = validate_stage3_algorithm_label(doc["stage3_algorithm"], cell=name)
        assert record.id == "sealed-credit-system-policy-v1"
        assert used == ("context_application",)


def test_the_campaign_plan_flies_the_arm_alone(cells):
    plan = _read(REPO / "configs/campaign/slurp-native-stage3-comp1b-fold-a-v1.json")
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [{"cell": ARM, "experiment": ARM}]
    assert "campaign" in cells[ARM][1]["allowed_execution_stages"]
    assert "campaign" not in cells[SMOKE][1]["allowed_execution_stages"]


def test_the_plan_documents_carry_the_recomputed_hashes(cells):
    for name, prefix in ((ARM, ""), (SMOKE, "smoke-")):
        doc, cell, composed = cells[name]
        split = doc["population"]["split_identity_hash"]
        expected = protocol_hash(composed.config_hash, composed.values["arm"], split)
        for kind, run in (("generation", RUNS[name][0]), ("fit", RUNS[name][1])):
            plan = _read(PACKAGE / f"{prefix}{kind}-plan-registered-v1.json")
            assert plan["composed_config_hash"] == composed.config_hash
            assert plan["execution_plan"]["protocol_hash"] == expected
            assert plan["execution_plan"]["run_id"] == run
            assert plan["execution_plan"]["split_identity_hash"] == split


def test_the_recipe_names_the_existing_sealed_aa_as_the_gating_replicate(facts):
    recipe = _read(PACKAGE / "analysis-recipe-v1.json")
    assert recipe["arms"]["arm"]["run_id"] == RUNS[ARM][0]
    assert recipe["arms"]["in_chain_replicate"]["run_id"] == COMPARATOR_RUN
    assert recipe["arms"]["comparator"]["run_id"] == "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
    assert recipe["read_run_id"] == "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-PAIRED-ANALYSIS-V1"


def test_the_draft_decision_receipt_names_the_four_run_ids_and_is_not_decided():
    draft = _read(PACKAGE / "root-admission-draft-v1.json")
    assert draft["eligible_run_ids"] == [RUNS[ARM][0], RUNS[ARM][1], RUNS[SMOKE][0], RUNS[SMOKE][1]]
    assert draft["status"] != "decided"
    assert draft["decision_id"] == DECISION_ID


def test_all_five_exposure_rows_exist_and_no_cell_contains_a_pipe():
    """A literal '|' inside a cell silently splits the row, and
    contracts.ledger._parse_ledger_tables then refuses the whole ledger."""

    lines = io.open(REPO / "docs/exposure-ledger.md", encoding="utf-8", newline="").read().split("\n")
    wanted = [run for pair in RUNS.values() for run in pair] + ["SAEA-SLURP-STAGE3-COMP1B-FOLD-A-PAIRED-ANALYSIS-V1"]
    for run in wanted:
        found = [line for line in lines if line.startswith("|") and ("| " + run + " |") in line]
        assert len(found) == 1, run
        parts = found[0].split("|")
        assert len(parts) == 17, (run, len(parts))
        cells = [part.strip() for part in parts[1:-1]]
        assert cells[6] == "discovery"
        assert cells[8] in ("yes", "no")
