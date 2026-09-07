"""KC-E2's brief-source audit: the pairing arithmetic, the identity anchor, the
ceiling and the homograph diagnostic, on a synthetic corpus.

Every number here is arithmetic over text this file writes. The audit's real
run is a receipt, not a test fixture, and it is checked by its own identity
anchor rather than by an assertion here.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from speech_aware_evidence_acquisition.analysis import e22_brief_source_audit as audit

HEADER = (
    "File ID,Ticker Symbol,Country by Ticker,UN Defined,Major Dialect Family,"
    "Language Family + Area Based,File Length (seconds),Sampling Rate (Hz)"
)
TABLE = (
    HEADER
    + "\n"
    + "4453225,APNHF,South Africa,Sub-Saharan Africa,Other,English,4307,16000\n"
    + "4474506,COST,United States,Europe and Northern America,North American,English,3975,24000\n"
)
CLIP_CALL = {
    "4453225-1": "4453225",
    "4453225-2": "4453225",
    "4474506-1": "4474506",
    "4474506-2": "4474506",
}
REFERENCES = {
    "4453225-1": "our South Africa business grew",
    "4453225-2": "other regions were flat",
    "4474506-1": "the cost in the United States rose",
    # "other" here belongs to a call whose dialect family is North American, so
    # it is the diagnostic's evidence that the term is ordinary vocabulary.
    "4474506-2": "other markets improved",
}
HYPOTHESES = {
    "4453225-1": "our South Africa business grew",
    "4453225-2": "other regions were flat",
    # "United States" is substituted at its second word and "cost" survives.
    "4474506-1": "the cost in the United Kingdom rose",
    "4474506-2": "other markets improved",
}


def _measure():
    return audit.measure(
        metadata_text=TABLE,
        references=REFERENCES,
        hypotheses=HYPOTHESES,
        clip_call=CLIP_CALL,
        clips=sorted(CLIP_CALL),
    )


def test_the_ceiling_is_the_error_mass_on_brief_term_words_over_all_reference_words():
    measurement = _measure()
    # "south africa" (2) + "other" (1) + "cost" (1) + "united states" (2) = 6.
    assert measurement["brief_term_reference_words"] == 6
    assert measurement["brief_term_hits"] == 5
    assert measurement["brief_term_substitutions"] == 1
    assert measurement["brief_term_deletions"] == 0
    total = measurement["reference_words"]
    assert measurement["ceiling_corpus_wer_points"] == pytest.approx(
        100.0 * 1 / total, abs=1e-6
    )


def test_the_per_field_rows_partition_the_covered_words():
    measurement = _measure()
    by_field = {row["field"]: row for row in measurement["per_field"]}
    assert sum(row["reference_words"] for row in measurement["per_field"]) == 6
    assert by_field["Country"]["reference_words"] == 4
    assert by_field["Major dialect family"]["reference_words"] == 1
    assert by_field["Ticker symbol"]["reference_words"] == 1
    assert by_field["UN region"]["reference_words"] == 0


def test_a_term_that_occurs_in_another_call_is_marked_shared_vocabulary():
    """``other`` is the literal value of one call's dialect family AND an
    ordinary English word. The diagnostic separates the two by counting
    occurrences in calls whose metadata does not carry the term, so no judgement
    call is needed and none is made."""

    measurement = _measure()
    terms = {(row["field"], row["normalized"]): row for row in measurement["terms"]}
    other = terms[("Major dialect family", "other")]
    assert other["own_call_reference_words"] == 1
    assert other["other_call_reference_words"] == 1
    assert other["call_specific"] is False
    south_africa = terms[("Country", "south africa")]
    assert south_africa["call_specific"] is True


def test_the_distinctive_summary_splits_the_term_mass():
    measurement = _measure()
    distinctive = audit.distinctive_summary(measurement)
    assert (
        distinctive["call_specific_reference_words"]
        + distinctive["shared_vocabulary_reference_words"]
        == distinctive["covered_reference_words"]
    )


def test_the_per_call_rows_cover_every_cluster():
    measurement = _measure()
    per_call = {row["call_id"]: row for row in measurement["per_call"]}
    assert set(per_call) == {"4453225", "4474506"}
    assert per_call["4453225"]["clips"] == 2
    assert per_call["4474506"]["clips"] == 2


def test_the_identity_anchor_refuses_a_number_it_cannot_reproduce():
    references = {"a-1": "alpha bravo charlie delta"}
    rows = {"a-1": {"wer": 0.0, "hits": 4, "substitutions": 0, "deletions": 0, "insertions": 0}}
    anchor = audit.identity_anchor(rows, references, ["a-1"])
    assert anchor["reference_words"] == 4
    assert anchor["reproduced"] is False
    assert anchor["measured_corpus_wer_percent"] == 0.0


def test_the_identity_anchor_reproduces_the_published_number():
    reference_words = 100
    references = {"a-1": " ".join("alpha" for _ in range(reference_words))}
    errors = round(audit.COMPARATOR["corpus_wer_percent"] * reference_words / 100)
    rows = {
        "a-1": {
            "wer": 0.0,
            "hits": reference_words - errors,
            "substitutions": errors,
            "deletions": 0,
            "insertions": 0,
        }
    }
    anchor = audit.identity_anchor(rows, references, ["a-1"])
    assert anchor["measured_corpus_wer_percent"] == pytest.approx(errors, abs=1e-9)


def test_the_clip_call_map_must_reproduce_its_own_digests(tmp_path):
    document = {
        "clip_call_map": dict(CLIP_CALL),
        "calls": sorted(set(CLIP_CALL.values())),
        "clips_per_call": {"4453225": 2, "4474506": 1},
        "count": len(CLIP_CALL),
        "ids_sha256": hashlib.sha256("\n".join(sorted(CLIP_CALL)).encode("utf-8")).hexdigest(),
        "map_sha256": hashlib.sha256(
            "\n".join(f"{k},{CLIP_CALL[k]}" for k in sorted(CLIP_CALL)).encode("utf-8")
        ).hexdigest(),
        "split_identity_hash": "0" * 64,
        "metadata_sha256": "1" * 64,
    }
    path = tmp_path / audit.CLIP_CALL_MAP_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8", newline="\n")
    loaded = audit.load_clip_calls(tmp_path)
    assert loaded["clip_call"] == CLIP_CALL

    document["map_sha256"] = "2" * 64
    path.write_text(json.dumps(document), encoding="utf-8", newline="\n")
    with pytest.raises(audit.BriefSourceAuditError, match="own ids/map digests"):
        audit.load_clip_calls(tmp_path)


def test_the_audit_reads_only_the_corpus_table_and_sealed_bytes():
    """The 2026-09-07 owner ruling, asserted rather than only written down: the
    audit's only corpus input is the benchmark's own metadata table, and its
    module names no URL, no lookup file and no second corpus path."""

    body = pathlib.Path(audit.__file__).read_text(encoding="utf-8")
    assert "http://" not in body and "https://" not in body
    assert audit.METADATA_RELPATH == "datasets/earnings21-22/earnings22/metadata.csv"
    corpus_paths = [
        value
        for name, value in vars(audit).items()
        if isinstance(value, str) and value.startswith("datasets/")
    ]
    assert corpus_paths == [audit.METADATA_RELPATH]
