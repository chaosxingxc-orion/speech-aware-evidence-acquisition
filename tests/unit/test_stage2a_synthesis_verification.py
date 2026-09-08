"""Gates for the Stage-2A matured synthesis verification row.

Two kinds of test live here.

**Pure-function gates** pin the comparison semantics, so a later refactor
cannot quietly make the checker permissive: a boolean must not satisfy an
integer expectation, a float must match to the declared tolerance and not one
decimal looser, and a missing JSON path must raise rather than resolve to
``None``.

**Whole-corpus gates** run the receipt and claim verification over the
committed receipts themselves. Nothing outside the repository is read and no
sealed run directory is opened, so these are as offline as the module is. They
deliberately do NOT call :func:`~...stage2a_synthesis_verification.run`,
because that arms the process-wide offline guard by replacing
``socket.socket.connect`` and never restores it -- which would leak into every
later test in the same session.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import (
    stage2a_synthesis_verification as sv,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestWalk:
    def test_walks_nested_mappings(self) -> None:
        doc = {"a": {"b": {"c": 7}}}
        assert sv._walk(doc, "a/b/c", receipt_key="fixture") == 7

    def test_indexes_a_sequence(self) -> None:
        doc = {"rows": [{"v": 1}, {"v": 2}]}
        assert sv._walk(doc, "rows/1/v", receipt_key="fixture") == 2

    def test_a_missing_key_raises_rather_than_returning_none(self) -> None:
        with pytest.raises(sv.SynthesisVerificationError, match="no key at"):
            sv._walk({"a": {"x": 1}}, "a/b", receipt_key="fixture")

    def test_an_out_of_range_index_raises(self) -> None:
        with pytest.raises(sv.SynthesisVerificationError, match="index out of range"):
            sv._walk({"rows": [1]}, "rows/4", receipt_key="fixture")

    def test_descending_into_a_scalar_raises(self) -> None:
        with pytest.raises(sv.SynthesisVerificationError, match="cannot descend"):
            sv._walk({"a": 1}, "a/b", receipt_key="fixture")


class TestMatches:
    def test_integers_must_match_exactly(self) -> None:
        assert sv._matches(101, 101)
        assert not sv._matches(102, 101)

    def test_a_boolean_never_satisfies_an_integer_expectation(self) -> None:
        """The confusion this module exists to catch: a boolean field read as
        an integer would let ``True`` pass for ``1``."""

        assert not sv._matches(True, 1)
        assert not sv._matches(1, True)
        assert sv._matches(True, True)
        assert not sv._matches(False, True)

    def test_floats_match_inside_the_declared_tolerance(self) -> None:
        assert sv._matches(20.2, 20.2 + sv.FLOAT_TOLERANCE / 2)

    def test_floats_outside_the_tolerance_fail(self) -> None:
        assert not sv._matches(20.2, 20.2 + sv.FLOAT_TOLERANCE * 10)

    def test_the_tolerance_is_tight_enough_to_catch_a_fourth_decimal_slip(self) -> None:
        assert not sv._matches(6.7797, 6.7798)

    def test_strings_match_exactly(self) -> None:
        assert sv._matches("RANKING", "RANKING")
        assert not sv._matches("ranking", "RANKING")


class TestDeclarations:
    def test_every_claim_names_a_declared_receipt(self) -> None:
        keys = {r.key for r in sv.RECEIPTS}
        unknown = sorted({c.receipt for c in sv.CLAIMS} - keys)
        assert unknown == []

    def test_claim_ids_are_unique(self) -> None:
        ids = [c.claim_id for c in sv.CLAIMS]
        assert len(ids) == len(set(ids))

    def test_receipt_keys_are_unique(self) -> None:
        keys = [r.key for r in sv.RECEIPTS]
        assert len(keys) == len(set(keys))

    def test_every_declared_receipt_is_actually_cited_by_a_claim(self) -> None:
        """A receipt hashed but never read would be decoration."""

        cited = {c.receipt for c in sv.CLAIMS} | {c.receipt for c in sv.DERIVED_CLAIMS}
        assert sorted({r.key for r in sv.RECEIPTS} - cited) == []

    def test_derived_claim_ids_are_unique_and_disjoint_from_the_field_claims(self) -> None:
        derived = [c.claim_id for c in sv.DERIVED_CLAIMS]
        assert len(derived) == len(set(derived))
        assert set(derived).isdisjoint({c.claim_id for c in sv.CLAIMS})

    def test_every_derived_claim_names_a_declared_receipt(self) -> None:
        keys = {r.key for r in sv.RECEIPTS}
        assert sorted({c.receipt for c in sv.DERIVED_CLAIMS} - keys) == []


class TestAgainstTheCommittedReceipts:
    def test_every_receipt_digest_matches(self) -> None:
        block = sv.verify_receipts(REPO_ROOT)
        assert block["all_digests_match"] is True
        assert block["receipts_verified"] == len(sv.RECEIPTS)

    def test_every_carried_number_matches_its_receipt(self) -> None:
        documents = sv.load_receipts(REPO_ROOT)
        block = sv.verify_claims(documents)
        assert block["all_claims_match"] is True
        assert block["claims_verified"] == len(sv.CLAIMS)

    def test_a_tampered_expectation_is_rejected(self) -> None:
        """The checker must fail on a wrong number, not merely pass on right
        ones -- otherwise the whole row proves nothing."""

        documents = sv.load_receipts(REPO_ROOT)
        original = sv.CLAIMS
        bad = sv.Claim("tampered", "lock_read", "primary/delta_pp", 20.3)
        try:
            sv.CLAIMS = original + (bad,)  # type: ignore[misc]
            with pytest.raises(sv.SynthesisVerificationError, match="tampered"):
                sv.verify_claims(documents)
        finally:
            sv.CLAIMS = original  # type: ignore[misc]

    def test_every_carried_reduction_matches_its_receipt(self) -> None:
        documents = sv.load_receipts(REPO_ROOT)
        block = sv.verify_derived_claims(documents)
        assert block["all_derived_claims_match"] is True
        assert block["derived_claims_verified"] == len(sv.DERIVED_CLAIMS)

    def test_a_tampered_reduction_is_rejected(self) -> None:
        documents = sv.load_receipts(REPO_ROOT)
        original = sv.DERIVED_CLAIMS
        bad = sv.DerivedClaim(
            "tampered_reduction",
            "oracle_bound",
            "lower_constructions/per_sample",
            "N1_tier_prototype/tau_passing_targets_total",
            "min",
            1,
        )
        try:
            sv.DERIVED_CLAIMS = original + (bad,)  # type: ignore[misc]
            with pytest.raises(sv.SynthesisVerificationError, match="tampered_reduction"):
                sv.verify_derived_claims(documents)
        finally:
            sv.DERIVED_CLAIMS = original  # type: ignore[misc]

    def test_the_live_locked_artifacts_hash_to_the_carried_values(self) -> None:
        block = sv.verify_file_digests(REPO_ROOT)
        assert block["file_digests_verified"] == len(sv.FILE_DIGESTS)
        assert all(row["matches"] for row in block["file_digests"])

    def test_the_synthesis_time_digest_matches_the_five_receipts_that_recorded_it(
        self,
    ) -> None:
        """2026-09-08 re-pin (WAVE R7 folded kb_policy.py, module docstring's
        dated paragraph): FILE_DIGESTS_AT_SYNTHESIS is no longer asserted
        against the live tree -- verify_file_digests above now carries the
        live pin -- but it must still match what the five sealed 2026-08-25
        receipts that independently recorded kb_policy.py's digest actually
        carry, so the historical record cannot itself quietly drift."""

        documents = sv.load_receipts(REPO_ROOT)
        block = sv.verify_file_digests_at_synthesis(documents)
        assert block["file_digests_at_synthesis_verified"] == len(
            sv._KB_POLICY_DIGEST_AT_SYNTHESIS_PATHS
        )
        assert all(row["matches"] for row in block["file_digests_at_synthesis"])
        historical_kb_policy_digest = dict(sv.FILE_DIGESTS_AT_SYNTHESIS)[
            "src/speech_aware_evidence_acquisition/rails/kb_policy.py"
        ]
        assert all(
            row["measured_sha256"] == historical_kb_policy_digest
            for row in block["file_digests_at_synthesis"]
        )

    def test_the_live_pin_and_the_synthesis_time_pin_have_diverged_on_kb_policy(
        self,
    ) -> None:
        """Pins the fact the 2026-09-08 re-pin exists to record: the live
        kb_policy.py digest and the digest the synthesis actually locked are
        now two different values, on purpose, because the file's bytes moved
        under a proven-equivalent refactor (WAVE R7) after the synthesis ran.
        The config fragment beside it did not move."""

        live = dict(sv.FILE_DIGESTS)
        historical = dict(sv.FILE_DIGESTS_AT_SYNTHESIS)
        assert set(live) == set(historical)
        kb_policy_path = "src/speech_aware_evidence_acquisition/rails/kb_policy.py"
        config_path = "configs/policy/kb-policy-v1-dev100.json"
        assert live[kb_policy_path] != historical[kb_policy_path]
        assert live[config_path] == historical[config_path]

    def test_both_builders_now_condition_their_prior_on_the_conditioning_event(
        self,
    ) -> None:
        """The English successor to the landed claim that both builders shared
        one unconditioned expression shape. That was true at ``3f131afd``; row
        ``SAEA-SN-MF-PRIOR-SCORE-SEMANTICS-REPAIR`` repaired it. The live tree
        must carry the repaired expressions and must NOT carry the defective
        ones; the pre-repair lines stay published as the historical record."""

        block = sv.verify_source_claims(REPO_ROOT)
        assert block["source_claims_verified"] == len(sv.SOURCE_CLAIMS)
        assert all(row["present"] for row in block["source_claims"])
        assert block["forbidden_source_claims_verified"] == len(
            sv.SOURCE_CLAIMS_MUST_BE_ABSENT
        )
        assert all(row["absent"] for row in block["forbidden_source_claims"])
        assert len(block["source_claims_at_3f131afd"]) == len(
            sv.SOURCE_CLAIMS_AT_3F131AFD
        )
