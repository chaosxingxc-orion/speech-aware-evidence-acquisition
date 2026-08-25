"""The prior-score semantics repair module's own fail-closed paths.

Row ``SAEA-SN-MF-PRIOR-SCORE-SEMANTICS-REPAIR``. The landed receipt is the
record of what the module measured on the real corpora; these tests exercise
the paths that must REFUSE, on synthetic inputs, so a future edit cannot turn
a fail-closed check into a reported one. Model-free, network-free, and no
dataset bytes are opened.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import (
    prior_score_semantics_repair as psr,
)
from speech_aware_evidence_acquisition.analysis import (
    stage2a_synthesis_verification as sv,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class _SlurpRow:
    utterance_id: str
    scenario: str
    action: str
    intent: str


@dataclass(frozen=True)
class _A2tRow:
    unit_id: str
    domain: str
    category: str
    tool_name: str


def _nesting_rows() -> tuple[_SlurpRow, ...]:
    return tuple(
        _SlurpRow(f"{scenario}-{action}-{index}", scenario, action, f"{scenario}_{action}")
        for scenario, actions in (("alarm", ("set", "query")), ("news", ("query",)))
        for action in actions
        for index in range(3)
    )


def test_the_slurp_identity_holds_under_the_production_label_scheme() -> None:
    block = psr.slurp_nesting_identity(_nesting_rows())
    assert block["identity_holds"] is True
    assert block["rows_violating_the_label_scheme"] == 0
    assert block["intents_whose_restricted_row_set_differs_from_the_unrestricted_one"] == 0
    assert block["rows_whose_prior_changed"] == 0
    assert block["post_repair_prior_supremum"] <= 1.0


def test_the_slurp_identity_reports_a_non_nesting_intent_as_a_finding() -> None:
    """A single intent under two scenarios would mean the SLURP prior was
    wrong in flight too. It must surface, not be swallowed."""

    rows = _nesting_rows() + (
        _SlurpRow("leak-0", "news", "set", "alarm_set"),
    )
    block = psr.slurp_nesting_identity(rows)
    assert block["identity_holds"] is False
    assert block["rows_violating_the_label_scheme"] == 1
    assert block["intents_whose_restricted_row_set_differs_from_the_unrestricted_one"] > 0
    assert block["rows_whose_prior_changed"] > 0


def _a2t_rows() -> tuple[_A2tRow, ...]:
    wide = tuple(
        _A2tRow(f"tier1_direct:{100 + index:06d}", "home", "wide", "sharedTool")
        for index in range(3)
    )
    narrow = (_A2tRow("tier2_parametric:000900", "car", "narrow", "sharedTool"),)
    return wide + narrow


def test_the_a2t_before_after_refuses_a_reconstruction_that_misses_the_pinned_values() -> None:
    rows = _a2t_rows()
    # Deliberately wrong: the pinned prior for the narrow row was 4/1 = 4.0.
    with pytest.raises(psr.RepairError, match="fidelity gate FAILED"):
        psr.a2t_prior_before_after(
            construction_rows=rows,
            selected_rows=rows,
            pinned_priors={"value:tier2_parametric:000900": 0.5},
        )


def test_the_a2t_before_after_passes_its_gate_and_conditions_the_prior() -> None:
    rows = _a2t_rows()
    pinned = {
        "value:tier1_direct:000100": 4 / 3,
        "value:tier1_direct:000101": 4 / 3,
        "value:tier1_direct:000102": 4 / 3,
        "value:tier2_parametric:000900": 4 / 1,
    }
    block = psr.a2t_prior_before_after(
        construction_rows=rows, selected_rows=rows, pinned_priors=pinned
    )
    assert block["fidelity_gate"]["recomputed_pre_repair_reproduces_the_pinned_snapshot"]
    assert block["pre_repair"]["max"] == pytest.approx(4.0)
    assert block["post_repair"]["max"] == pytest.approx(1.0)
    assert block["post_repair"]["values_above_1"] == 0
    assert block["values_moved"] == 4
    assert block["conditional_distribution_property"]["holds"] is True


def test_the_rebuild_diff_refuses_when_any_text_moved() -> None:
    """If text moved, a rebuild would need an embedding pass this row may not
    take. The module must STOP rather than report."""

    pinned = {
        "facets": [
            {"facet_id": "facet:label:t0", "representation": "tool_0"},
        ],
        "values": [
            {"value_id": "value:v0", "content": "before", "prior_score": 4.1},
        ],
        "builder_policy_id": "p1",
    }
    rebuilt = {
        "facets": [
            {"facet_id": "facet:label:t0", "representation": "tool_0"},
        ],
        "values": [
            {"value_id": "value:v0", "content": "AFTER", "prior_score": 0.5},
        ],
        "builder_policy_id": "p1",
    }
    with pytest.raises(psr.RepairError, match="moved something other than prior_score"):
        psr.rebuild_differs_only_in_prior_score(
            pinned_document=pinned, rebuilt_document=rebuilt
        )


def test_the_rebuild_diff_accepts_a_prior_score_only_change() -> None:
    pinned = {
        "facets": [{"facet_id": "facet:label:t0", "representation": "tool_0"}],
        "values": [{"value_id": "value:v0", "content": "same", "prior_score": 4.1}],
        "builder_policy_id": "p1",
    }
    rebuilt = {
        "facets": [{"facet_id": "facet:label:t0", "representation": "tool_0"}],
        "values": [{"value_id": "value:v0", "content": "same", "prior_score": 0.5}],
        "builder_policy_id": "p1",
    }
    block = psr.rebuild_differs_only_in_prior_score(
        pinned_document=pinned, rebuilt_document=rebuilt
    )
    assert block["only_prior_score_moved"] is True
    assert block["values_changed_in_prior_score_only"] == 1
    assert "NO EMBEDDING PASS IS IMPLIED" in str(block["embedding_implication"])


def test_the_pre_repair_evidence_is_read_from_the_landed_receipt() -> None:
    """The pre-repair lines are no longer in the tree; the evidence that they
    were there is the landed synthesis receipt, re-hashed before it is read."""

    block = psr.source_verification(REPO_ROOT)
    assert block["pre_repair_commit"] == psr.PRE_REPAIR_COMMIT
    evidence = block["pre_repair_evidence"]
    assert len(evidence["claims"]) == len(sv.SOURCE_CLAIMS_AT_3F131AFD)
    assert all(
        row["machine_checked_present_at_pre_repair_commit"]
        for row in evidence["claims"]
    )
    assert len(evidence["receipt_sha256"]) == 64
    live = block["live_tree_after_repair"]
    assert all(row["present"] for row in live["source_claims"])
    assert all(row["absent"] for row in live["forbidden_source_claims"])
