"""Gates for the scoreboard-v5 verification row.

These run the digest and claim verification over the committed artifacts
themselves. Nothing outside the repository is read and no sealed run directory
is opened, so they are as offline as the module is.

They deliberately do NOT call
:func:`~...scoreboard_v5_verification.run`, because that arms the process-wide
offline guard by replacing ``socket.socket.connect`` and never restores it,
which would leak into every later test in the same session.

The mutation gates are the point: a verification module that cannot be made to
fail is not a check. Each one mutates exactly one declared expectation and
asserts that the corresponding verifier raises.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import (
    scoreboard_v5_verification as sv,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Byte constants for the pin/line-ending gates below. Named rather than
#: inlined so no escape in this file can be misread as a real newline.
LF = bytes([0x0A])
CRLF = bytes([0x0D, 0x0A])


class TestRegister:
    def test_every_cited_artifact_exists_and_hashes_to_its_pin(self) -> None:
        block = sv.verify_artifacts(REPO_ROOT)
        assert block["receipts_verified"] == len(sv.RECEIPTS)
        assert block["documents_verified"] == len(sv.DOCUMENTS)
        assert all(row["matches_pin"] for row in block["artifacts"])

    def test_register_keys_are_unique_across_both_tiers(self) -> None:
        keys = [a.key for a in (*sv.RECEIPTS, *sv.DOCUMENTS)]
        assert len(keys) == len(set(keys))

    def test_every_claim_names_a_registered_receipt(self) -> None:
        receipt_keys = {r.key for r in sv.RECEIPTS}
        for claim in sv.CLAIMS:
            assert claim.receipt in receipt_keys, claim.claim_id
        for claim in sv.SUBSTRING_CLAIMS:
            assert claim.receipt in receipt_keys, claim.claim_id

    def test_every_document_claim_names_a_registered_document(self) -> None:
        document_keys = {d.key for d in sv.DOCUMENTS}
        for claim in sv.DOCUMENT_CLAIMS:
            assert claim.document in document_keys, claim.claim_id

    def test_claim_ids_are_unique(self) -> None:
        ids = [c.claim_id for c in (*sv.CLAIMS, *sv.SUBSTRING_CLAIMS, *sv.DOCUMENT_CLAIMS)]
        assert len(ids) == len(set(ids))

    def test_every_registered_receipt_carries_at_least_one_claim(self) -> None:
        """A receipt cited but never read from is a digest with no number
        behind it. R-FACET is the one deliberate exception: the scoreboard
        carries its conclusion, not its counts, and says so in section 5."""

        cited = {c.receipt for c in (*sv.CLAIMS, *sv.SUBSTRING_CLAIMS)}
        unread = {r.key for r in sv.RECEIPTS} - cited
        assert unread == {"R-FACET"}


class TestCarriedNumbers:
    def test_every_carried_number_matches_its_receipt(self) -> None:
        receipts = sv.load_receipts(REPO_ROOT)
        block = sv.verify_claims(receipts)
        assert block["claims_verified"] == len(sv.CLAIMS)

    def test_every_carried_substring_is_present_in_its_receipt(self) -> None:
        receipts = sv.load_receipts(REPO_ROOT)
        block = sv.verify_substring_claims(receipts)
        assert block["substring_claims_verified"] == len(sv.SUBSTRING_CLAIMS)

    def test_every_tier_d_sentence_is_present_verbatim(self) -> None:
        texts = sv.load_documents(REPO_ROOT)
        block = sv.verify_document_claims(texts)
        assert block["document_claims_verified"] == len(sv.DOCUMENT_CLAIMS)


class TestItCanFail:
    def test_a_wrong_number_raises(self) -> None:
        receipts = sv.load_receipts(REPO_ROOT)
        mutated = (*sv.CLAIMS, sv.Claim("mutant", "R-LOCK", "primary/M0_correct", 279))
        original = sv.CLAIMS
        try:
            sv.CLAIMS = mutated  # type: ignore[misc]
            with pytest.raises(sv.ScoreboardVerificationError, match="do not match"):
                sv.verify_claims(receipts)
        finally:
            sv.CLAIMS = original  # type: ignore[misc]

    def test_a_missing_json_path_raises(self) -> None:
        receipts = sv.load_receipts(REPO_ROOT)
        mutated = (sv.Claim("mutant", "R-LOCK", "primary/no_such_field", 1),)
        original = sv.CLAIMS
        try:
            sv.CLAIMS = mutated  # type: ignore[misc]
            with pytest.raises(sv.ScoreboardVerificationError):
                sv.verify_claims(receipts)
        finally:
            sv.CLAIMS = original  # type: ignore[misc]

    def test_an_absent_tier_d_sentence_raises(self) -> None:
        texts = sv.load_documents(REPO_ROOT)
        mutated = (sv.DocumentClaim("mutant", "D-SN", "Direct K0-M0 scores 78/108."),)
        original = sv.DOCUMENT_CLAIMS
        try:
            sv.DOCUMENT_CLAIMS = mutated  # type: ignore[misc]
            with pytest.raises(sv.ScoreboardVerificationError, match="absent"):
                sv.verify_document_claims(texts)
        finally:
            sv.DOCUMENT_CLAIMS = original  # type: ignore[misc]

    def test_a_wrong_digest_raises(self) -> None:
        original = sv.RECEIPTS
        pinned = sv.ARTIFACTS_BY_KEY["R-LOCK"]
        broken = sv.Receipt("R-LOCK", pinned.relpath, "0" * 64, pinned.produced_by)
        try:
            sv.RECEIPTS = tuple(  # type: ignore[misc]
                broken if r.key == "R-LOCK" else r for r in original
            )
            with pytest.raises(sv.ScoreboardVerificationError, match="digest"):
                sv.verify_artifacts(REPO_ROOT)
        finally:
            sv.RECEIPTS = original  # type: ignore[misc]


class TestPinsAreOverGitBlobBytes:
    """The 2026-08-25 D-GATES defect, made impossible to repeat silently.

    The D-GATES pin was taken from that file's CRLF WORKING-TREE bytes on the
    Windows checkout. `.gitattributes` here declares `* text=auto eol=lf`, so the
    blob is LF and hashes to something else entirely -- the pin passed on the one
    machine that authored it and failed on every clean checkout, which is how it
    reached `master` and broke CI. Umbrella `CLAUDE.md` settles the authority:
    "Git blob bytes are the evidence hash authority ... not CRLF working-tree
    bytes."

    `crlf_defect` turns that sentence into a refusal, and these two gates prove it
    fires. The first is a standing invariant over the live register: a pin can
    only ever be taken from bytes that are already LF, so the CRLF-derived pin
    could not be authored again without this failing first. The second is a
    mutation gate -- a guard that cannot be made to fire is not a guard.
    """

    def test_no_pinned_artifact_carries_crlf_in_the_working_tree(self) -> None:
        offenders = [
            artifact.relpath
            for artifact in (*sv.RECEIPTS, *sv.DOCUMENTS)
            if CRLF in (REPO_ROOT / artifact.relpath).read_bytes()
        ]
        assert offenders == [], (
            "these pinned artifacts hold CRLF on disk, so their on-disk digest is not "
            "the Git blob digest every clean checkout measures: " + repr(offenders)
        )

    def test_a_crlf_working_tree_copy_is_refused_by_name(self, tmp_path: Path) -> None:
        artifact = sv.ARTIFACTS_BY_KEY["D-GATES"]
        blob = (REPO_ROOT / artifact.relpath).read_bytes()
        assert CRLF not in blob
        staged = tmp_path / artifact.relpath
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(blob.replace(LF, CRLF))

        kept_documents, kept_receipts = sv.DOCUMENTS, sv.RECEIPTS
        try:
            # Verify exactly the one staged artifact: the rest of the register
            # does not exist under tmp_path and would drown the signal in
            # MISSING rows.
            sv.DOCUMENTS = (artifact,)  # type: ignore[misc]
            sv.RECEIPTS = ()  # type: ignore[misc]
            with pytest.raises(sv.ScoreboardVerificationError, match="CRLF line endings"):
                sv.verify_artifacts(tmp_path)
        finally:
            sv.DOCUMENTS = kept_documents  # type: ignore[misc]
            sv.RECEIPTS = kept_receipts  # type: ignore[misc]


class TestReadingRules:
    def test_the_two_delivery_rates_are_receipt_fields_not_prose(self) -> None:
        """Rule 2 of the scoreboard header stands on these two numbers, so they
        are pinned here as well as in the claim table."""

        ids = {c.claim_id for c in sv.CLAIMS}
        for claim_id in (
            "field.slurp_delivered",
            "field.slurp_rate",
            "field.a2t_delivered",
            "field.a2t_rate",
        ):
            assert claim_id in ids

    def test_the_supersession_is_pinned_by_its_own_measurement(self) -> None:
        """The scoreboard shows the matching-versus-extraction conditioned
        verdict as SUPERSEDED. What supersedes it is a dispatch count, and it
        must be verified rather than asserted."""

        by_id = {c.claim_id: c for c in sv.CLAIMS}
        assert by_id["ecd.superseded_cell_dispatched_unexposed"].expected == 3
        assert by_id["ecd.superseded_cell_dispatched_exposed"].expected == 2
        assert by_id["ecd.superseded_cell_dispatched_a2t"].expected == 0

    def test_the_scoreboard_document_is_present(self) -> None:
        assert (REPO_ROOT / sv.SCOREBOARD_RELPATH).is_file()
