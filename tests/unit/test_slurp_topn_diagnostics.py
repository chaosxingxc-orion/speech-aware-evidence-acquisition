from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics import (
    BranchOutcomeRow,
    ReferenceIntentRow,
    SourceCandidateRow,
    TopNDiagnosticError,
    aggregate_topn_diagnostics,
)


def _fixture():
    source = (
        SourceCandidateRow("s1", ("a", "b", "c")),
        SourceCandidateRow("s2", ("b", "a", "c")),
        SourceCandidateRow("s3", ("b", "c", "d")),
        SourceCandidateRow("s4", ("a", "b", "c")),
        SourceCandidateRow("s5", ("a", "b", "c")),
    )
    references = (
        ReferenceIntentRow("s1", "a"),
        ReferenceIntentRow("s2", "a"),
        ReferenceIntentRow("s3", "z"),
        ReferenceIntentRow("s4", "z"),
        ReferenceIntentRow("s5", "a"),
    )
    branches = {
        "hard_first": (
            BranchOutcomeRow("s1", "a", False, True),
            BranchOutcomeRow("s2", "b", False, False),
            BranchOutcomeRow("s3", None, True, None),
            BranchOutcomeRow("s4", "z", False, True),
            BranchOutcomeRow("s5", None, True, None),
        ),
        "closed_joint": (
            BranchOutcomeRow("s1", "a", False, True),
            BranchOutcomeRow("s2", "a", False, False),
            BranchOutcomeRow("s3", None, True, None),
            BranchOutcomeRow("s4", None, True, None),
            BranchOutcomeRow("s5", "b", False, False),
        ),
    }
    return source, references, branches


def test_aggregate_reports_source_candidates_and_branch_transitions():
    source, references, branches = _fixture()

    report = aggregate_topn_diagnostics(
        source, references, branches, candidate_width=3
    )

    assert report.candidate_width == 3
    assert report.source.sample_count == 5
    assert report.source.top1_correct == 2
    assert report.source.top1_accuracy == pytest.approx(0.4)
    assert report.source.topn_included == 3
    assert report.source.topn_inclusion == pytest.approx(0.6)
    assert report.source.missing_true_candidate == 2
    assert report.source.present_not_selected == 1

    hard = report.branches["hard_first"]
    assert hard.final_intent_correct == 2
    assert hard.rescues == 1
    assert hard.harms == 1
    assert hard.refusals == 2
    assert hard.out_of_shortlist_attempts == 1
    assert hard.candidate_present == 3
    assert hard.candidate_present_final_correct == 1
    assert hard.candidate_present_final_correct_rate == pytest.approx(1 / 3)
    assert hard.candidate_present_final_not_selected == 2
    assert hard.candidate_present_final_not_selected_rate == pytest.approx(2 / 3)
    assert hard.refusal_attempts_with_intent == 0
    assert hard.unchanged_correct == 1
    assert hard.unchanged_wrong == 2
    assert hard.entity_available == 3
    assert hard.intent_correct_entity_correct == 2
    assert hard.intent_correct_entity_incorrect == 0
    assert hard.intent_incorrect_entity_correct == 0
    assert hard.intent_incorrect_entity_incorrect == 1
    assert hard.entity_unavailable == 2

    joint = report.branches["closed_joint"]
    assert joint.final_intent_correct == 2
    assert joint.rescues == 1
    assert joint.harms == 1
    assert joint.refusals == 2
    assert joint.out_of_shortlist_attempts == 0
    assert joint.candidate_present == 3
    assert joint.candidate_present_final_correct == 2
    assert joint.candidate_present_final_correct_rate == pytest.approx(2 / 3)
    assert joint.candidate_present_final_not_selected == 1
    assert joint.candidate_present_final_not_selected_rate == pytest.approx(1 / 3)
    assert joint.refusal_attempts_with_intent == 0
    assert joint.entity_available == 3
    assert joint.intent_correct_entity_correct == 1
    assert joint.intent_correct_entity_incorrect == 1
    assert joint.intent_incorrect_entity_correct == 0
    assert joint.intent_incorrect_entity_incorrect == 1
    assert joint.entity_unavailable == 2

    sample = {row.sample_id: row for row in report.per_sample}
    assert sample["s2"].present_not_selected is True
    assert sample["s2"].branches["closed_joint"].rescue is True
    assert sample["s4"].branches["hard_first"].out_of_shortlist is True
    assert sample["s4"].branches["hard_first"].rescue is True
    assert sample["s2"].branches["closed_joint"].candidate_present is True
    assert sample["s2"].branches["closed_joint"].candidate_present_final_correct is True
    assert sample["s2"].branches["hard_first"].candidate_present_final_not_selected is True
    assert sample["s3"].missing_true_candidate is True

    encoded = report.as_json()
    assert encoded["schema"] == "saea-slurp-topn-diagnostics-v1"
    assert encoded["source"]["topn_included"] == 3
    assert encoded["source"]["true_candidate_present_but_source_rank1_not_selected"] == 1
    assert encoded["branches"]["closed_joint"]["refusals"] == 2
    assert encoded["branches"]["closed_joint"]["candidate_present_final_correct"] == 2


def test_candidate_width_can_project_a_wider_ordered_source_without_reordering():
    source = (SourceCandidateRow("s1", ("a", "b", "c", "d")),)
    references = (ReferenceIntentRow("s1", "c"),)
    branches = {
        "joint": (BranchOutcomeRow("s1", "c", False, None),)
    }

    report = aggregate_topn_diagnostics(
        source, references, branches, candidate_width=2
    )

    assert report.candidate_width == 2
    assert report.source.top1_correct == 0
    assert report.source.topn_included == 0
    assert report.per_sample[0].candidate_ids == ("a", "b")


@pytest.mark.parametrize(
    "bad_source",
    [
        (
            SourceCandidateRow("s1", ("a", "a")),
        ),
        (
            SourceCandidateRow("s1", ("a",)),
            SourceCandidateRow("s1", ("b",)),
        ),
    ],
)
def test_refuses_duplicate_candidate_or_sample_id(bad_source):
    references = (ReferenceIntentRow("s1", "a"),)
    branches = {"joint": (BranchOutcomeRow("s1", "a", False, None),)}

    with pytest.raises(TopNDiagnosticError, match="duplicate"):
        aggregate_topn_diagnostics(bad_source, references, branches)


def test_refuses_roster_mismatch_and_nonrefused_missing_final():
    source = (SourceCandidateRow("s1", ("a", "b")),)
    references = (ReferenceIntentRow("s1", "a"),)

    with pytest.raises(TopNDiagnosticError, match="roster mismatch"):
        aggregate_topn_diagnostics(
            source, references,
            {"joint": (BranchOutcomeRow("s2", "a", False, None),)},
        )

    with pytest.raises(TopNDiagnosticError, match="final_intent_id"):
        aggregate_topn_diagnostics(
            source, references,
            {"joint": (BranchOutcomeRow("s1", None, False, None),)},
        )


def test_reference_outside_candidates_is_allowed_and_is_missing():
    source = (SourceCandidateRow("s1", ("a", "b", "c")),)
    references = (ReferenceIntentRow("s1", "outside"),)
    branches = {"joint": (BranchOutcomeRow("s1", "outside", False, True),)}

    report = aggregate_topn_diagnostics(source, references, branches)

    assert report.source.missing_true_candidate == 1
    assert report.branches["joint"].rescues == 1
    assert report.branches["joint"].out_of_shortlist_attempts == 1
    assert report.branches["joint"].intent_correct_entity_correct == 1


def test_references_are_never_derived_from_branch_predictions():
    source = (SourceCandidateRow("s1", ("a", "b", "c")),)
    references = (ReferenceIntentRow("s1", "gold"),)
    branches = {"joint": (BranchOutcomeRow("s1", "a", False, None),)}

    report = aggregate_topn_diagnostics(source, references, branches)

    assert report.source.top1_correct == 0
    assert report.branches["joint"].final_intent_correct == 0
    assert report.per_sample[0].reference_intent_id == "gold"


@pytest.mark.parametrize("candidate_ids", ["abc", b"abc", 3])
def test_refuses_string_or_nonsequence_candidate_ids(candidate_ids):
    source = (SourceCandidateRow("s1", candidate_ids),)
    references = (ReferenceIntentRow("s1", "a"),)
    branches = {"joint": (BranchOutcomeRow("s1", "a", False, None),)}

    with pytest.raises(TopNDiagnosticError, match="non-string sequence"):
        aggregate_topn_diagnostics(source, references, branches)


def test_refused_attempt_intent_is_diagnostic_only_and_never_final_quality():
    source = (SourceCandidateRow("s1", ("a", "b")),)
    references = (ReferenceIntentRow("s1", "a"),)
    branches = {
        "closed_joint": (BranchOutcomeRow("s1", "outside", True, None),)
    }

    result = aggregate_topn_diagnostics(source, references, branches)
    branch = result.branches["closed_joint"]
    sample = result.per_sample[0].branches["closed_joint"]

    assert branch.refusals == 1
    assert branch.refusal_attempts_with_intent == 1
    assert branch.out_of_shortlist_attempts == 1
    assert branch.final_intent_correct == 0
    assert sample.final_intent_attempt_only is True
    assert sample.final_intent_correct is False
    assert sample.out_of_shortlist is True
    assert result.as_json()["per_sample"][0]["branches"]["closed_joint"][
        "final_intent_attempt_only"
    ] is True


def test_explicit_missing_final_intent_is_retained_without_refusal():
    report = aggregate_topn_diagnostics(
        [SourceCandidateRow("s1", ("a",))],
        [ReferenceIntentRow("s1", "a")],
        {"system": [BranchOutcomeRow("s1", None, False, False, missing_final_intent=True)]},
    ).as_json()
    branch = report["branches"]["system"]
    assert branch["sample_count"] == 1
    assert branch["final_intent_correct"] == 0
    assert branch["refusals"] == 0
    assert branch["missing_final_intents"] == 1
    assert branch["harms"] == 1
    assert branch["candidate_present_final_not_selected"] == 1


@pytest.mark.parametrize("intent,refused,missing", [
    ("a", False, True), (None, True, True), (None, False, "yes"),
])
def test_missing_final_intent_flag_must_match_delivery(intent, refused, missing):
    with pytest.raises(TopNDiagnosticError, match="missing_final_intent"):
        aggregate_topn_diagnostics(
            [SourceCandidateRow("s1", ("a",))],
            [ReferenceIntentRow("s1", "a")],
            {"system": [BranchOutcomeRow("s1", intent, refused, missing_final_intent=missing)]},
        )
