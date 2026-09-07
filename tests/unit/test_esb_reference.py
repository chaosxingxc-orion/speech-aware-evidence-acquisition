"""The ESB Earnings-22 utterance reference rail and its two scorers.

These scorers carry the paper-facing Earnings-22 number, and they reach their
gold OUTSIDE ``data.references`` -- so the identity guarantee that
``contracts.FrozenCoreGate.verify_reference_identity`` supplies for the
carrier ``.nlp`` layer has to be supplied here instead. Every refusal below is
that guarantee: a drifted reference file, a row count that disagrees with the
committed receipt, a duplicate id, an empty sentence, a path escaping the data
root, a foreign carrier, and an outputs row the pinned layer does not contain.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.reproduction.esb_reference import (
    ESB_CARRIER_LOCK_KEY,
    ESB_REFERENCE_RECEIPT_RELPATH,
    ESB_REFERENCE_RECEIPT_SCHEMA,
    EsbReferenceError,
    load_esb_references,
    published_segment_key,
    score_esb_outputs,
    score_esb_outputs_whisper,
)

RELPATH = "derived/e22-esb-segment-table/e22-esb-test-references.jsonl"


def _reference_payload(rows: list[dict[str, str]]) -> str:
    return (
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n"
    )


def _materialize(
    tmp_path: Path,
    rows: list[dict[str, str]],
    *,
    receipt_overrides: dict[str, object] | None = None,
    payload: str | None = None,
) -> tuple[Path, Path]:
    """``(repo_root, data_root)`` with a committed receipt and a written layer."""

    data_root = tmp_path / "data"
    repo_root = tmp_path / "repo"
    text = _reference_payload(rows) if payload is None else payload
    target = data_root / RELPATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    receipt = {
        "schema": ESB_REFERENCE_RECEIPT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier": ESB_CARRIER_LOCK_KEY,
        "relpath": RELPATH,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "rows": len(rows),
    }
    receipt.update(receipt_overrides or {})
    receipt_path = repo_root / ESB_REFERENCE_RECEIPT_RELPATH
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return repo_root, data_root


def _outputs(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    path = tmp_path / "run.outputs.jsonl"
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


REFERENCE_ROWS = [
    {"sample_id": "4432298-0", "sentence": "Good evening, hello."},
    {"sample_id": "4432298-1", "sentence": "We sold twenty units."},
]


def test_load_returns_every_pinned_reference(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(tmp_path, REFERENCE_ROWS)
    references = load_esb_references(data_root, repo_root=repo_root)
    assert references == {row["sample_id"]: row["sentence"] for row in REFERENCE_ROWS}


def test_load_refuses_a_reference_layer_that_drifted(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(tmp_path, REFERENCE_ROWS)
    target = data_root / RELPATH
    target.write_text(
        _reference_payload(
            [
                {"sample_id": "4432298-0", "sentence": "Good evening, hello."},
                {"sample_id": "4432298-1", "sentence": "We sold TWO HUNDRED units."},
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(EsbReferenceError, match="identity drift"):
        load_esb_references(data_root, repo_root=repo_root)


def test_load_refuses_a_row_count_that_disagrees_with_the_receipt(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(tmp_path, REFERENCE_ROWS, receipt_overrides={"rows": 3})
    with pytest.raises(EsbReferenceError, match="the receipt pins 3"):
        load_esb_references(data_root, repo_root=repo_root)


def test_load_refuses_a_duplicate_sample_id(tmp_path: Path) -> None:
    duplicated = [REFERENCE_ROWS[0], dict(REFERENCE_ROWS[0])]
    repo_root, data_root = _materialize(tmp_path, duplicated)
    with pytest.raises(EsbReferenceError, match="non-empty and unique"):
        load_esb_references(data_root, repo_root=repo_root)


def test_load_refuses_an_empty_sentence(tmp_path: Path) -> None:
    rows = [{"sample_id": "4432298-0", "sentence": "   "}]
    repo_root, data_root = _materialize(tmp_path, rows)
    with pytest.raises(EsbReferenceError, match="is empty"):
        load_esb_references(data_root, repo_root=repo_root)


def test_load_refuses_a_path_escaping_the_data_root(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(
        tmp_path, REFERENCE_ROWS, receipt_overrides={"relpath": "../outside.jsonl"}
    )
    with pytest.raises(EsbReferenceError, match="malformed"):
        load_esb_references(data_root, repo_root=repo_root)


def test_load_refuses_a_foreign_carrier(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(
        tmp_path, REFERENCE_ROWS, receipt_overrides={"carrier": "earnings21-original"}
    )
    with pytest.raises(EsbReferenceError, match="names carrier"):
        load_esb_references(data_root, repo_root=repo_root)


def test_load_refuses_a_wrong_schema(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(
        tmp_path, REFERENCE_ROWS, receipt_overrides={"schema": "something-else-v1"}
    )
    with pytest.raises(EsbReferenceError, match="schema must be"):
        load_esb_references(data_root, repo_root=repo_root)


def test_load_refuses_a_missing_receipt(tmp_path: Path) -> None:
    _repo_root, data_root = _materialize(tmp_path, REFERENCE_ROWS)
    with pytest.raises(EsbReferenceError, match="cannot read"):
        load_esb_references(data_root, repo_root=tmp_path / "no-such-repo")


def test_whisper_scorer_reports_corpus_and_per_sample(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(tmp_path, REFERENCE_ROWS)
    outputs = _outputs(
        tmp_path,
        [
            {
                "sample_id": "4432298-0",
                "carrier_lock_key": ESB_CARRIER_LOCK_KEY,
                "text": "Good evening hello",
            },
            {
                "sample_id": "4432298-1",
                "carrier_lock_key": ESB_CARRIER_LOCK_KEY,
                "text": "We sold 20 units",
            },
        ],
    )
    result = score_esb_outputs_whisper(outputs, {}, data_root, repo_root=repo_root)
    aggregate = result["aggregate"]
    # "twenty" -> "20" is exactly what the Whisper normalizer unifies, and
    # punctuation is stripped on both sides, so both rows are perfect.
    assert aggregate["corpus_wer"] == pytest.approx(0.0)
    assert aggregate["substitutions"] == 0
    assert aggregate["deletions"] == 0
    assert aggregate["insertions"] == 0
    assert aggregate["reference_words"] == 7
    assert aggregate["samples"] == 2
    assert aggregate["merge_compounds"] is False
    assert [entry["sample_id"] for entry in result["per_sample"]] == [
        "4432298-0",
        "4432298-1",
    ]


def test_whisper_corpus_is_micro_not_macro(tmp_path: Path) -> None:
    """A long perfect row must not be averaged away by a short wrong one."""

    # Deliberately number-free: the Whisper normalizer collapses a run of
    # spelled-out numerals into ONE digit token, which would make the word
    # counts this test is about say something else entirely.
    rows = [
        {"sample_id": "a-1", "sentence": "alpha bravo charlie delta echo foxtrot golf hotel india juliet"},
        {"sample_id": "a-2", "sentence": "kilo"},
    ]
    repo_root, data_root = _materialize(tmp_path, rows)
    outputs = _outputs(
        tmp_path,
        [
            {
                "sample_id": "a-1",
                "carrier_lock_key": ESB_CARRIER_LOCK_KEY,
                "text": "alpha bravo charlie delta echo foxtrot golf hotel india juliet",
            },
            {"sample_id": "a-2", "carrier_lock_key": ESB_CARRIER_LOCK_KEY, "text": "lima"},
        ],
    )
    result = score_esb_outputs_whisper(outputs, {}, data_root, repo_root=repo_root)
    # corpus: 1 error over 11 reference words; mean: (0.0 + 1.0) / 2.
    assert result["aggregate"]["corpus_wer"] == pytest.approx(1 / 11)
    assert result["aggregate"]["mean_wer"] == pytest.approx(0.5)


def test_frozen_normalizer_scorer_disagrees_with_the_whisper_one(tmp_path: Path) -> None:
    """The two scorers are different metric families, and the test says so."""

    rows = [{"sample_id": "a-1", "sentence": "We sold twenty units."}]
    repo_root, data_root = _materialize(tmp_path, rows)
    outputs = _outputs(
        tmp_path,
        [{"sample_id": "a-1", "carrier_lock_key": ESB_CARRIER_LOCK_KEY, "text": "We sold 20 units"}],
    )
    whisper = score_esb_outputs_whisper(outputs, {}, data_root, repo_root=repo_root)
    frozen = score_esb_outputs(outputs, {}, data_root, repo_root=repo_root)
    assert whisper["aggregate"]["corpus_wer"] == pytest.approx(0.0)
    assert frozen["aggregate"]["corpus_wer"] > 0.0
    assert frozen["aggregate"]["normalizer"] == "saea-scoring-v1"


def test_scorers_refuse_a_sample_outside_the_pinned_reference_layer(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(tmp_path, REFERENCE_ROWS)
    outputs = _outputs(
        tmp_path,
        [{"sample_id": "9999999-0", "carrier_lock_key": ESB_CARRIER_LOCK_KEY, "text": "hello"}],
    )
    for scorer in (score_esb_outputs, score_esb_outputs_whisper):
        with pytest.raises(EsbReferenceError, match="pinned reference closure"):
            scorer(outputs, {}, data_root, repo_root=repo_root)


def test_scorers_refuse_a_foreign_carrier_row(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(tmp_path, REFERENCE_ROWS)
    outputs = _outputs(
        tmp_path,
        [{"sample_id": "4432298-0", "carrier_lock_key": "earnings21-original", "text": "hello"}],
    )
    for scorer in (score_esb_outputs, score_esb_outputs_whisper):
        with pytest.raises(EsbReferenceError, match="only ever score"):
            scorer(outputs, {}, data_root, repo_root=repo_root)


def test_scorers_refuse_an_empty_outputs_file(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(tmp_path, REFERENCE_ROWS)
    outputs = tmp_path / "empty.outputs.jsonl"
    outputs.write_text("", encoding="utf-8")
    with pytest.raises(EsbReferenceError, match="is empty"):
        score_esb_outputs_whisper(outputs, {}, data_root, repo_root=repo_root)


def test_both_scorers_are_registered_under_their_flight_names() -> None:
    from speech_aware_evidence_acquisition.core.base import SCORERS
    import speech_aware_evidence_acquisition.core.scorers  # noqa: F401 (registration)

    assert SCORERS.resolve("asr-wer-esb") is score_esb_outputs
    assert SCORERS.resolve("asr-wer-esb-whisper") is score_esb_outputs_whisper


# ---------------------------------------------------------------------------
# The probe MEDIA variant id convention (@<variant>)
# ---------------------------------------------------------------------------


def test_published_segment_key_strips_a_variant_suffix_and_nothing_else() -> None:
    assert published_segment_key("4453225-103") == "4453225-103"
    assert published_segment_key("4453225-103@ts2") == "4453225-103"
    assert published_segment_key("4453225-103@p30") == "4453225-103"
    assert published_segment_key("4453225-103@bx1") == "4453225-103"
    # Only the FIRST '@' splits, so a suffix that itself contains one cannot
    # smuggle a different published key in.
    assert published_segment_key("4453225-103@a@b") == "4453225-103"


def test_a_variant_row_scores_against_its_own_published_sentence(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(tmp_path, REFERENCE_ROWS)
    outputs = _outputs(
        tmp_path,
        [
            {
                "sample_id": "4432298-0@ts2",
                "carrier_lock_key": ESB_CARRIER_LOCK_KEY,
                "text": "Good evening hello",
            },
            {
                "sample_id": "4432298-1@ts2",
                "carrier_lock_key": ESB_CARRIER_LOCK_KEY,
                "text": "We sold 20 units",
            },
        ],
    )
    result = score_esb_outputs_whisper(outputs, {}, data_root, repo_root=repo_root)
    assert result["aggregate"]["corpus_wer"] == pytest.approx(0.0)
    assert result["aggregate"]["reference_words"] == 7
    # The per-sample rows keep the SUFFIXED id, which is what a paired join and
    # a receipt need; only the reference lookup uses the published key.
    assert [entry["sample_id"] for entry in result["per_sample"]] == [
        "4432298-0@ts2",
        "4432298-1@ts2",
    ]


def test_a_variant_row_outside_the_reference_layer_is_still_refused(tmp_path: Path) -> None:
    repo_root, data_root = _materialize(tmp_path, REFERENCE_ROWS)
    outputs = _outputs(
        tmp_path,
        [
            {
                "sample_id": "9999999-0@ts2",
                "carrier_lock_key": ESB_CARRIER_LOCK_KEY,
                "text": "hello",
            }
        ],
    )
    for scorer in (score_esb_outputs, score_esb_outputs_whisper):
        with pytest.raises(EsbReferenceError, match="pinned reference closure"):
            scorer(outputs, {}, data_root, repo_root=repo_root)
