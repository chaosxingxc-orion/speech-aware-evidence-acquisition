"""SUPPLY dose knob (``evidence_budget_bytes``): resolution/validation is
fail-closed, and truncation is deterministic, UTF-8-safe, cut at a
whitespace boundary, and a no-op when absent/0 (core.evidence_budget)."""

import pytest

from speech_aware_evidence_acquisition.core.base import EvidenceError, EvidenceItem
from speech_aware_evidence_acquisition.core.evidence_budget import (
    apply_evidence_budget,
    resolve_evidence_budget_bytes,
)


def _item(content: str, evidence_id: str = "conec/1") -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        source_uri=f"conec://{evidence_id}",
        content=content,
        provenance={"lock_key": "conec", "relpath": "x", "sha256": "0" * 64},
    )


class TestResolveEvidenceBudgetBytes:
    def test_absent_is_unlimited(self):
        assert resolve_evidence_budget_bytes({}) == 0

    def test_explicit_zero_is_unlimited(self):
        assert resolve_evidence_budget_bytes({"evidence_budget_bytes": 0}) == 0

    def test_positive_int_resolves_verbatim(self):
        assert resolve_evidence_budget_bytes({"evidence_budget_bytes": 512}) == 512

    @pytest.mark.parametrize("bad", [-1, -100, 1.5, "512", True, False, None, [512]])
    def test_bad_values_refuse(self, bad):
        with pytest.raises(EvidenceError, match="evidence_budget_bytes"):
            resolve_evidence_budget_bytes({"evidence_budget_bytes": bad})


class TestApplyEvidenceBudget:
    def test_zero_budget_leaves_content_byte_identical(self):
        by_sample = {"s1": [_item("some evidence text here")]}
        result = apply_evidence_budget(by_sample, 0)
        assert result["s1"][0].content == "some evidence text here"

    def test_budget_larger_than_content_is_unchanged(self):
        content = "short context"
        by_sample = {"s1": [_item(content)]}
        result = apply_evidence_budget(by_sample, 10_000)
        assert result["s1"][0].content == content

    def test_positive_budget_truncates_at_the_last_whitespace_boundary(self):
        content = "Alpha beta gamma delta epsilon zeta"
        budget = 15  # inside "Alpha beta gamm" -- must back off to "Alpha beta"
        result = apply_evidence_budget({"s1": [_item(content)]}, budget)
        truncated = result["s1"][0].content
        assert truncated == "Alpha beta"
        assert len(truncated.encode("utf-8")) <= budget
        assert not truncated.endswith(" ")

    def test_truncation_is_deterministic(self):
        content = "one two three four five six seven eight"
        by_sample = {"s1": [_item(content)]}
        first = apply_evidence_budget(by_sample, 17)["s1"][0].content
        second = apply_evidence_budget(by_sample, 17)["s1"][0].content
        assert first == second

    def test_never_splits_a_multibyte_codepoint(self):
        # "café" is 5 UTF-8 bytes ('é' is 2); a budget of 4 lands exactly on
        # the lead byte of 'é' with no whitespace anywhere -- the codepoint
        # -safe backoff must still decode cleanly and stay within budget.
        content = "café"
        budget = 4
        result = apply_evidence_budget({"s1": [_item(content)]}, budget)
        truncated = result["s1"][0].content
        truncated.encode("utf-8")  # must not raise
        assert truncated == "caf"
        assert len(truncated.encode("utf-8")) <= budget

    def test_single_token_longer_than_budget_falls_back_to_the_byte_safe_prefix(self):
        content = "supercalifragilisticexpialidocious"
        budget = 6
        result = apply_evidence_budget({"s1": [_item(content)]}, budget)
        truncated = result["s1"][0].content
        assert truncated == content[:budget]
        assert len(truncated.encode("utf-8")) <= budget

    def test_multiple_items_in_one_sample_share_a_single_running_budget(self):
        items = [_item("aaaa", "e1"), _item("bbbb", "e2")]
        result = apply_evidence_budget({"s1": items}, 4)
        # the first item exactly exhausts the budget -- the second is
        # dropped entirely, never independently (re-)truncated
        assert [item.evidence_id for item in result["s1"]] == ["e1"]

    def test_multiple_samples_are_truncated_independently(self):
        by_sample = {
            "s1": [_item("aaaa aaaa aaaa")],
            "s2": [_item("bbbb bbbb bbbb")],
        }
        result = apply_evidence_budget(by_sample, 10)
        assert result["s1"][0].content == "aaaa aaaa"
        assert result["s2"][0].content == "bbbb bbbb"

    def test_provenance_and_derivation_survive_truncation_unchanged(self):
        item = _item("Alpha beta gamma")
        result = apply_evidence_budget({"s1": [item]}, 8)
        truncated = result["s1"][0]
        assert truncated.evidence_id == item.evidence_id
        assert truncated.source_uri == item.source_uri
        assert truncated.provenance == item.provenance
        assert truncated.content != item.content
