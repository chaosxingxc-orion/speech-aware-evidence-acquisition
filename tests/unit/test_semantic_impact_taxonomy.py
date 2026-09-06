"""The E22 -> ``ACTIVE.json`` projection: does the file say what the scan says?

The projection is only worth anything if it agrees with the function it claims
to project. :func:`test_the_projection_equals_the_e22_impact_function` asserts
that directly -- it builds a real one-word E22 span, runs the scan's own
:func:`~analysis.e22_error_taxonomy.semantic_impact` on it, and demands the same
level from the emitted taxonomy's lookup, over the whole cross product of the
vocabularies that can disagree.
"""

from __future__ import annotations

import itertools
import json

import pytest

from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (
    IMPACTS,
    NEGATIONS,
    STOPWORDS,
    align_spans,
    semantic_impact,
)
from speech_aware_evidence_acquisition.analysis.semantic_impact_taxonomy import (
    TAXONOMY_ID,
    UNREPRESENTABLE_TRIGGERS,
    build_taxonomy,
    rule_keys,
    taxonomy_rules,
    word_pair_content_impact,
)
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT
from speech_aware_evidence_acquisition.reproduction.asr_wer_whisper import (
    WHISPER_NORMALIZER_NAME,
)
from speech_aware_evidence_acquisition.reproduction.semantic_impact import (
    ACTIVE_TAXONOMY_RELPATH,
    DELETED,
    TAXONOMY_SCHEMA,
    load_taxonomy,
)

from test_e22_error_taxonomy import make_context  # noqa: E402  (same-directory test helper)

_PIN = {"source_commit": "0" * 40, "source_sha256": "f" * 64}

#: One word from each behaviour class the projection distinguishes: a negation,
#: a function word, a content word. The cross product of these against
#: themselves and against the deletion sentinel is every distinct case the
#: word-pair lookup can see.
PROBE_WORDS = ("not", "never", "the", "a", "revenue", "guidance")


def _document():
    return build_taxonomy(**_PIN)


def _e22_level(reference: str, hypothesis: str) -> str:
    """E22's own content impact for one error instance, obtained by aligning a
    real one-word pair rather than by re-implementing the function here."""

    if hypothesis == DELETED:
        context = make_context(reference, "")
    else:
        context = make_context(reference, hypothesis)
    spans = align_spans(context.ref_tokens, context.hyp_tokens).spans
    assert len(spans) == 1, (reference, hypothesis, spans)
    return semantic_impact(spans[0], context)


# ---------------------------------------------------------------------------
# The projection agrees with the function it projects
# ---------------------------------------------------------------------------


def test_the_projection_equals_the_e22_impact_function():
    for reference, hypothesis in itertools.product(PROBE_WORDS, (*PROBE_WORDS, DELETED)):
        if reference == hypothesis:
            continue  # an aligner never emits a substitution of a word for itself
        assert word_pair_content_impact(reference, hypothesis) == _e22_level(
            reference, hypothesis
        ), (reference, hypothesis)


def test_the_emitted_rules_classify_exactly_as_the_projection_does():
    taxonomy = _loaded()
    for reference, hypothesis in itertools.product(PROBE_WORDS, (*PROBE_WORDS, DELETED)):
        if reference == hypothesis:
            continue
        level, rule_id = taxonomy.classify(reference, hypothesis)
        assert level == word_pair_content_impact(reference, hypothesis), (reference, hypothesis)
        assert rule_id


def _loaded(tmp_path=None):
    from speech_aware_evidence_acquisition.reproduction.semantic_impact import (
        ImpactTaxonomy,
        WILDCARD,
    )

    document = _document()
    rules: dict[tuple[str, str], tuple[str, str]] = {}
    for rule in document["rules"]:
        rules[(rule["ref"], rule["hyp"])] = (rule["level"], rule["id"])
    assert (WILDCARD, WILDCARD) in rules
    return ImpactTaxonomy(
        taxonomy_id=str(document["taxonomy_id"]),
        levels=tuple(document["levels"]),
        high_level=str(document["high_level"]),
        rules=rules,
        normalizer=str(document["normalizer"]),
    )


# ---------------------------------------------------------------------------
# The file contract
# ---------------------------------------------------------------------------


def test_the_document_satisfies_the_scorers_own_loader(tmp_path):
    path = tmp_path / "ACTIVE.json"
    path.write_text(json.dumps(_document(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    taxonomy = load_taxonomy(path)
    assert taxonomy.taxonomy_id == TAXONOMY_ID
    assert taxonomy.levels == IMPACTS
    assert taxonomy.high_level == "HIGH"
    assert taxonomy.normalizer == WHISPER_NORMALIZER_NAME


def test_the_rule_keys_are_unique():
    keys = rule_keys(taxonomy_rules())
    assert len(set(keys)) == len(keys)


def test_the_high_tier_is_exactly_the_negation_trigger():
    """The projection's stated limit, asserted rather than only documented: no
    rule reaches HIGH except through a negation, because the digit and entity
    triggers are not expressible as exact-word keys."""

    high = [rule for rule in taxonomy_rules() if rule["level"] == "HIGH"]
    assert len(high) == 2 * len(NEGATIONS)
    for rule in high:
        assert rule["ref"] in NEGATIONS or rule["hyp"] in NEGATIONS


def test_the_none_tier_is_the_stopword_product():
    none = [rule for rule in taxonomy_rules() if rule["level"] == "NONE"]
    assert len(none) == len(STOPWORDS) * len(STOPWORDS)  # |S|^2 - |S| pairs + |S| deletions
    for rule in none:
        assert rule["ref"] in STOPWORDS
        assert rule["hyp"] in STOPWORDS or rule["hyp"] == DELETED


def test_the_pin_is_required():
    with pytest.raises(ValueError, match="commit and sha256"):
        build_taxonomy(source_commit="", source_sha256="f" * 64)


def test_the_document_names_what_it_cannot_carry():
    derivation = _document()["derivation"]
    assert len(derivation["unrepresentable_triggers"]) == len(UNREPRESENTABLE_TRIGGERS)
    assert "LOWER BOUND" in derivation["consequence"]
    assert "numeric-value-accuracy-v1" in derivation["consequence"]
    assert "conec-entity-wer-official" in derivation["consequence"]


# ---------------------------------------------------------------------------
# The landed file
# ---------------------------------------------------------------------------


def test_the_active_taxonomy_in_this_checkout_is_the_projection():
    """Replaces the 2026-09-06 placeholder assertion that this path was ABSENT.
    The taxonomy has landed, so what is asserted now is that the committed bytes
    are the ones the generator produces -- schema, id, normalizer and the exact
    rule set."""

    path = REPO_ROOT / ACTIVE_TAXONOMY_RELPATH
    assert path.is_file(), "the E5 taxonomy export has not landed"
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["schema"] == TAXONOMY_SCHEMA
    assert document["taxonomy_id"] == TAXONOMY_ID
    assert document["normalizer"] == WHISPER_NORMALIZER_NAME
    assert document["rules"] == taxonomy_rules()
    load_taxonomy(path)
