"""``semantic-high-impact-error-rate-v1``: the taxonomy file contract, the
lookup order, the HIGH-mass metric on a synthetic taxonomy, and the
fail-closed hook that waits for the Earnings-22 semantic scan."""

import json

import pytest

from speech_aware_evidence_acquisition.core import scorers  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.core.scorers import (
    ScoringPhaseError,
    score_semantic_high_impact_outputs,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.reproduction.asr_wer_whisper import (
    WHISPER_NORMALIZER_NAME,
)
from speech_aware_evidence_acquisition.reproduction.conec_entity_scoring import (
    aligned_operations,
)
from speech_aware_evidence_acquisition.reproduction.semantic_impact import (
    ACTIVE_TAXONOMY_RELPATH,
    DELETED,
    TAXONOMY_SCHEMA,
    UNCLASSIFIED,
    TaxonomyError,
    load_taxonomy,
    merge_semantic_counts,
    semantic_impact_counts,
)

_RULES = [
    {"id": "billion-million", "level": "HIGH", "ref": "billion", "hyp": "million"},
    {"id": "guidance-any", "level": "HIGH", "ref": "guidance", "hyp": "*"},
    {"id": "any-dropped", "level": "LOW", "ref": "*", "hyp": DELETED},
    {"id": "catch-all", "level": "MEDIUM", "ref": "*", "hyp": "*"},
]


def _taxonomy_document(**overrides):
    document = {
        "schema": TAXONOMY_SCHEMA,
        "taxonomy_id": "synthetic-v1",
        "normalizer": WHISPER_NORMALIZER_NAME,
        "levels": ["HIGH", "MEDIUM", "LOW"],
        "high_level": "HIGH",
        "rules": [dict(rule) for rule in _RULES],
    }
    document.update(overrides)
    return document


def _write_taxonomy(path, **overrides):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_taxonomy_document(**overrides)), encoding="utf-8")
    return path


def _write_nlp(path, tokens):
    lines = ["token|speaker|tags|wer_tags"]
    for token in tokens:
        lines.append(f"{token}|0||[]")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_outputs(tmp_path, rows):
    path = tmp_path / "y.outputs.jsonl"
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    return path


def test_semantic_high_impact_is_registered():
    assert "semantic-high-impact-error-rate-v1" in SCORERS.names()
    assert SCORERS.resolve("semantic-high-impact-error-rate-v1") is (
        score_semantic_high_impact_outputs
    )


# ---------------------------------------------------------------------------
# Taxonomy loading, fail-closed.
# ---------------------------------------------------------------------------


def test_loads_a_well_formed_taxonomy(tmp_path):
    taxonomy = load_taxonomy(_write_taxonomy(tmp_path / "t.json"))
    assert taxonomy.taxonomy_id == "synthetic-v1"
    assert taxonomy.high_level == "HIGH"
    assert taxonomy.levels == ("HIGH", "MEDIUM", "LOW")


def test_refuses_a_missing_file(tmp_path):
    with pytest.raises(TaxonomyError, match="cannot read"):
        load_taxonomy(tmp_path / "absent.json")


def test_refuses_a_wrong_schema(tmp_path):
    with pytest.raises(TaxonomyError, match="schema"):
        load_taxonomy(_write_taxonomy(tmp_path / "t.json", schema="something-else"))


def test_refuses_a_taxonomy_built_under_another_normalizer(tmp_path):
    with pytest.raises(TaxonomyError, match="normalizer"):
        load_taxonomy(_write_taxonomy(tmp_path / "t.json", normalizer="saea-scoring-v1"))


def test_refuses_a_level_outside_the_declared_set(tmp_path):
    rules = [dict(rule) for rule in _RULES]
    rules[0]["level"] = "CRITICAL"
    with pytest.raises(TaxonomyError, match="outside"):
        load_taxonomy(_write_taxonomy(tmp_path / "t.json", rules=rules))


def test_refuses_two_rules_on_the_same_key(tmp_path):
    rules = [dict(rule) for rule in _RULES]
    rules.append({"id": "dup", "level": "LOW", "ref": "billion", "hyp": "million"})
    with pytest.raises(TaxonomyError, match="two rules on key"):
        load_taxonomy(_write_taxonomy(tmp_path / "t.json", rules=rules))


def test_refuses_a_high_level_not_in_levels(tmp_path):
    with pytest.raises(TaxonomyError, match="high_level"):
        load_taxonomy(_write_taxonomy(tmp_path / "t.json", high_level="SEVERE"))


# ---------------------------------------------------------------------------
# Lookup order: exact pair, then exact ref, then exact hyp, then catch-all.
# ---------------------------------------------------------------------------


def test_lookup_prefers_the_exact_pair(tmp_path):
    taxonomy = load_taxonomy(_write_taxonomy(tmp_path / "t.json"))
    assert taxonomy.classify("billion", "million") == ("HIGH", "billion-million")


def test_lookup_falls_back_to_the_exact_reference_word(tmp_path):
    taxonomy = load_taxonomy(_write_taxonomy(tmp_path / "t.json"))
    assert taxonomy.classify("guidance", "anything") == ("HIGH", "guidance-any")


def test_lookup_falls_back_to_the_exact_hypothesis_word(tmp_path):
    taxonomy = load_taxonomy(_write_taxonomy(tmp_path / "t.json"))
    assert taxonomy.classify("revenue", DELETED) == ("LOW", "any-dropped")


def test_lookup_falls_back_to_the_catch_all(tmp_path):
    taxonomy = load_taxonomy(_write_taxonomy(tmp_path / "t.json"))
    assert taxonomy.classify("revenue", "revenues") == ("MEDIUM", "catch-all")


def test_an_unmatched_instance_is_unclassified_not_low(tmp_path):
    rules = [{"id": "only", "level": "HIGH", "ref": "billion", "hyp": "million"}]
    taxonomy = load_taxonomy(_write_taxonomy(tmp_path / "t.json", rules=rules))
    assert taxonomy.classify("revenue", "revenues") == (UNCLASSIFIED, "")


# ---------------------------------------------------------------------------
# The metric, hand-computed.
# ---------------------------------------------------------------------------


def test_high_impact_mass_over_reference_words(tmp_path):
    taxonomy = load_taxonomy(_write_taxonomy(tmp_path / "t.json"))
    reference = ["we", "held", "a", "billion", "on", "guidance"]
    hypothesis = ["we", "held", "a", "million", "on", "guidelines", "today"]
    operations = aligned_operations(reference, hypothesis)
    counts = semantic_impact_counts(operations, reference, hypothesis, taxonomy)
    assert counts["reference_words"] == 6
    # billion -> million (HIGH) and guidance -> guidelines (HIGH); "today" is an
    # insertion and carries no reference mass.
    assert counts["high_impact_reference_words"] == 2
    assert counts["high_impact_error_rate"] == pytest.approx(2 / 6)
    assert counts["reference_words_by_rule"]["billion-million"] == 1
    assert counts["reference_words_by_rule"]["guidance-any"] == 1


def test_an_insertion_carries_no_reference_mass_but_is_still_reported(tmp_path):
    rules = [{"id": "any", "level": "HIGH", "ref": "*", "hyp": "*"}]
    taxonomy = load_taxonomy(_write_taxonomy(tmp_path / "t.json", rules=rules))
    reference = ["a"]
    hypothesis = ["a", "b", "c"]
    operations = aligned_operations(reference, hypothesis)
    counts = semantic_impact_counts(operations, reference, hypothesis, taxonomy)
    assert counts["reference_words"] == 1
    assert counts["high_impact_reference_words"] == 0
    assert counts["high_impact_error_rate"] == 0.0
    assert counts["high_impact_insertions"] == 2


def test_a_deletion_is_classified_through_the_deleted_sentinel(tmp_path):
    taxonomy = load_taxonomy(_write_taxonomy(tmp_path / "t.json"))
    reference = ["we", "earned", "money"]
    hypothesis = ["we", "earned"]
    operations = aligned_operations(reference, hypothesis)
    counts = semantic_impact_counts(operations, reference, hypothesis, taxonomy)
    assert counts["reference_words_by_level"]["LOW"] == 1
    assert counts["high_impact_reference_words"] == 0


def test_unclassified_mass_is_reported_rather_than_absorbed(tmp_path):
    rules = [{"id": "only", "level": "HIGH", "ref": "billion", "hyp": "million"}]
    taxonomy = load_taxonomy(_write_taxonomy(tmp_path / "t.json", rules=rules))
    reference = ["revenue", "rose"]
    hypothesis = ["revenues", "rose"]
    operations = aligned_operations(reference, hypothesis)
    counts = semantic_impact_counts(operations, reference, hypothesis, taxonomy)
    assert counts["unclassified_reference_words"] == 1
    assert counts["high_impact_reference_words"] == 0


def test_merge_pools_counts_and_divides_once(tmp_path):
    taxonomy = load_taxonomy(_write_taxonomy(tmp_path / "t.json"))
    rows = [
        {
            "reference_words": 2,
            "high_impact_reference_words": 2,
            "unclassified_reference_words": 0,
            "high_impact_insertions": 0,
            "reference_words_by_level": {"HIGH": 2},
            "insertions_by_level": {},
            "reference_words_by_rule": {"guidance-any": 2},
        },
        {
            "reference_words": 6,
            "high_impact_reference_words": 0,
            "unclassified_reference_words": 1,
            "high_impact_insertions": 3,
            "reference_words_by_level": {"MEDIUM": 1},
            "insertions_by_level": {"HIGH": 3},
            "reference_words_by_rule": {},
        },
    ]
    merged = merge_semantic_counts(rows, taxonomy)
    assert merged["reference_words"] == 8
    # Pooled 2/8, not the mean of 1.0 and 0.0.
    assert merged["high_impact_error_rate"] == pytest.approx(0.25)
    assert merged["high_impact_insertions"] == 3
    assert merged["taxonomy_id"] == "synthetic-v1"


# ---------------------------------------------------------------------------
# The registered hook waits, by name, for the Earnings-22 semantic scan.
# ---------------------------------------------------------------------------


def test_registered_scorer_fails_closed_until_the_scan_lands(synthetic_world, tmp_path):
    _write_nlp(synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp", ["hi"])
    outputs = _write_outputs(
        tmp_path,
        [{"sample_id": "4000001", "carrier_lock_key": "earnings21-original", "text": "hi"}],
    )
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="Earnings-22 semantic scan"):
        score_semantic_high_impact_outputs(
            outputs, lock, synthetic_world.data_root, repo_root=synthetic_world.repo_root
        )


def test_registered_scorer_runs_once_a_taxonomy_is_present(synthetic_world, tmp_path):
    _write_nlp(
        synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp",
        ["revenue", "guidance", "was", "raised"],
    )
    _write_taxonomy(synthetic_world.repo_root / ACTIVE_TAXONOMY_RELPATH)
    outputs = _write_outputs(
        tmp_path,
        [
            {
                "sample_id": "4000001",
                "carrier_lock_key": "earnings21-original",
                "text": "revenue guidelines was raised",
            }
        ],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = score_semantic_high_impact_outputs(
        outputs, lock, synthetic_world.data_root, repo_root=synthetic_world.repo_root
    )
    assert scores["aggregate"]["high_impact_reference_words"] == 1
    assert scores["aggregate"]["reference_words"] == 4
    assert scores["aggregate"]["high_impact_error_rate"] == pytest.approx(0.25)


def test_the_active_taxonomy_path_now_carries_the_e22_projection():
    """Superseded 2026-09-06 (E5). This assertion used to demand the path be
    ABSENT, so the wait for the Earnings-22 scan stayed visible. The scan landed
    and its content-impact model was projected onto this file contract
    (``analysis.semantic_impact_taxonomy``), so what stays visible now is that
    the committed file loads through this module's own reader -- the scorer no
    longer fails closed, and a taxonomy that would break it breaks here.
    ``tests/unit/test_semantic_impact_taxonomy.py`` asserts the bytes are the
    projection."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    path = REPO_ROOT / ACTIVE_TAXONOMY_RELPATH
    assert path.is_file()
    assert load_taxonomy(path).normalizer == "whisper-english-v20240930"
