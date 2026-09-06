"""Export the Earnings-22 semantic scan's CONTENT-IMPACT model as the taxonomy
file ``semantic-high-impact-error-rate-v1`` waits for.

``reproduction/semantic_impact.py`` implements the metric and fails closed until
``docs/taxonomies/semantic-high-impact/ACTIVE.json`` exists. That file is the
scan's deliverable, and this module is the **derivation**: it imports the scan's
own committed lexicons and re-expresses its committed impact function on the one
shape the file contract can carry -- a single ``(reference word, hypothesis
word)`` key. Nothing here is a new judgement. Every level this module emits comes
from :func:`analysis.e22_error_taxonomy.semantic_impact`, and a unit test proves
the two agree instance by instance on the inputs where the projection is defined.

WHAT IS PROJECTED
-----------------
E22 tags every error span twice (``analysis.e22_error_taxonomy.ScoredSpan``):

* ``content_impact`` -- :func:`~analysis.e22_error_taxonomy.semantic_impact`,
  computed from the span's OWN tokens;
* ``impact`` -- that reading after the category ruling of
  :data:`~analysis.e22_error_taxonomy.IMPACT_NEUTRAL_CATEGORIES`.

This export projects **``content_impact``**, because it is the half that is a
function of tokens alone. The category ruling is a function of the 32-rule
cascade, which reads the utterance's neighbours, the segment table, the clip
boundary and the call's entity inventory; a ``(ref, hyp)`` key cannot see any of
them, so the ruling is NOT projected and must never be claimed to be. Both
readings are published side by side in the scan's own verdict, so projecting the
named one is a selection, not an invention.

E22's content-impact function, on a span whose changed tokens are ``ref_tokens +
hyp_tokens`` (a deletion has no hypothesis tokens):

1. a token containing a digit                       -> ``HIGH``
2. a token in :data:`~analysis.e22_error_taxonomy.NEGATIONS`  -> ``HIGH``
3. a token in the call's own entity inventory       -> ``HIGH``
4. a token outside :data:`~analysis.e22_error_taxonomy.STOPWORDS` -> ``LOW``
5. otherwise                                        -> ``NONE``

WHAT THE FILE CONTRACT CANNOT CARRY, AND WHAT THAT COSTS
--------------------------------------------------------
``reproduction.semantic_impact`` looks up an exact key in one fixed order --
``(ref, hyp)``, ``(ref, "*")``, ``("*", hyp)``, ``("*", "*")`` -- so a rule can
only name an exact normalized word or "any word". Two of E22's three HIGH
triggers are not exact-word predicates:

* **trigger 1, digits.** "the token contains a digit" is an open class: the
  Whisper normalizer turns spoken numbers into ``2022``, ``$1500000``, ``14.9%``,
  ``1st``. Enumerating them is unbounded, and a partial enumeration would
  silently score an unlisted number as ordinary wording. It is therefore left
  out entirely rather than approximated.
* **trigger 3, named entities.** E22 builds a fresh entity inventory per call
  from that call's own reference sentences (64-192 forms). A single static file
  cannot be per-call, and a union across calls would tag a name from one call as
  HIGH in another. Left out entirely.

So **this taxonomy's HIGH tier is E22's NEGATION trigger alone**, and its rate is
a strict lower bound on E22's own content-impact HIGH rate. That is stated in the
emitted file (``derivation.unrepresentable_triggers``) and must be restated
wherever the number is quoted. On Earnings-21 the two missing triggers are not
lost: they are carried, with gold annotations rather than heuristics, by
``numeric-value-accuracy-v1`` (digit-bearing reference words, by kind) and by
``conec-entity-wer-official`` (ConEC's own entity tags, by published class). The
three metrics together cover what E22's single span-level tag covered on
Earnings-22, and each of the three is better anchored than the tag was.

One further deviation, in the LOW/NONE split only. ``NONE`` requires a
conjunction over both sides (E22: *every* changed token is a stopword), so it is
emitted as the full explicit product of
:data:`~analysis.e22_error_taxonomy.STOPWORDS` against itself plus the deletion
sentinel -- exact for substitutions and deletions, which are the operations that
carry reference-word mass. INSERTIONS are looked up as ``("*", hypothesis word)``
and therefore reach the ``("*", "*")`` default: an inserted function word, which
E22 calls ``NONE``, is reported ``LOW`` here. Insertions carry zero reference
mass by construction and are reported in their own ``insertions_by_level`` map,
so no rate moves; the mis-levelling is named in the file and in the receipt.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from ..reproduction.asr_wer_whisper import WHISPER_NORMALIZER_NAME
from ..reproduction.semantic_impact import DELETED, TAXONOMY_SCHEMA, WILDCARD
from .e22_error_taxonomy import (
    EXPOSURE_ROW_ID,
    IMPACTS,
    NEGATIONS,
    STOPWORDS,
    TAXONOMY_VERSION,
)

TAXONOMY_ID = "e22-semantic-scan-2026-09-06-content-impact-word-pair-v1"
"""Names the scan, its date, the half of its impact model that is projected, and
the shape it is projected onto. A reader who sees this id in a result summary can
tell without another file open that the HIGH tier is not the scan's full HIGH."""

HIGH_LEVEL = "HIGH"

SOURCE_MODULE = "src/speech_aware_evidence_acquisition/analysis/e22_error_taxonomy.py"

#: The E22 content-impact triggers this key shape cannot express, with the reason.
#: Reproduced into the emitted file so the loss travels with the number.
UNREPRESENTABLE_TRIGGERS: tuple[tuple[str, str], ...] = (
    (
        "digit-bearing token (e22_error_taxonomy.semantic_impact rule 1)",
        "an open class after Whisper normalization (2022, $1500000, 14.9%, 1st); a "
        "taxonomy key is an exact word, and a partial enumeration would silently "
        "score an unlisted number as ordinary wording. On Earnings-21 this trigger "
        "is carried by numeric-value-accuracy-v1.",
    ),
    (
        "call-inventory named entity (e22_error_taxonomy.semantic_impact rule 3)",
        "E22's inventory is rebuilt per call from that call's own reference "
        "sentences; one static file cannot be per-call, and a union across calls "
        "would tag another call's names. On Earnings-21 this trigger is carried by "
        "conec-entity-wer-official, over ConEC's own gold entity tags.",
    ),
    (
        "the category ruling (e22_error_taxonomy.IMPACT_NEUTRAL_CATEGORIES)",
        "format-convention, reference-convention and segmentation-artifact are NONE "
        "by ruling, and all three are decided by the 32-rule cascade from the "
        "utterance's neighbours, the segment table and the clip boundary. This "
        "export projects content_impact, the reading E22 publishes beside it.",
    ),
)


def word_pair_content_impact(reference_word: str, hypothesis_word: str) -> str:
    """E22's :func:`~analysis.e22_error_taxonomy.semantic_impact`, restricted to
    one error instance and to the triggers an exact-word key can express.

    ``hypothesis_word`` is the normalized hypothesis word, or
    :data:`~reproduction.semantic_impact.DELETED` for a dropped reference word --
    in which case, exactly as in E22 (a deletion span carries no hypothesis
    tokens), only the reference word is examined.

    The digit and entity triggers are absent by construction, so this function
    equals E22's on any pair of words that carries no digit and belongs to no
    call's entity inventory. ``tests/unit/test_semantic_impact_taxonomy.py``
    asserts exactly that against the E22 function itself.
    """

    changed: tuple[str, ...] = (
        (reference_word,)
        if hypothesis_word == DELETED
        else (reference_word, hypothesis_word)
    )
    if any(token in NEGATIONS for token in changed):
        return "HIGH"
    if any(token not in STOPWORDS for token in changed):
        return "LOW"
    return "NONE"


def _rule(rule_id: str, level: str, reference: str, hypothesis: str) -> dict[str, str]:
    return {"id": rule_id, "level": level, "ref": reference, "hyp": hypothesis}


def taxonomy_rules() -> list[dict[str, str]]:
    """Every rule of the projection, in a deterministic order.

    The lookup is by exact key and the loader refuses a duplicate key, so file
    order changes nothing; it is fixed anyway so the emitted bytes are stable.

    Four families, and they are the whole projection:

    ``negation-ref/<w>``  ``(w, "*")`` HIGH -- a negation on the reference side
    dominates whatever replaced it.

    ``negation-hyp/<w>``  ``("*", w)`` HIGH -- a negation on the hypothesis side,
    reached only when the reference word is not itself a negation, since the
    ``(ref, "*")`` tier is tried first.

    ``inert-deletion/<s>`` ``(s, "<deleted>")`` NONE -- a dropped function word.
    Listed on the exact tier so it is not shadowed by the wildcard families.

    ``inert-substitution/<s1>__<s2>`` ``(s1, s2)`` NONE -- function word for
    function word. The explicit product, because NONE is a conjunction over both
    sides and no wildcard tier can express one. Identity pairs are omitted: an
    aligner never emits a substitution whose two words are equal.

    Everything else falls to ``residual-wording`` ``("*", "*")`` LOW, which is
    E22's rule 4 -- ordinary wording moved.
    """

    negations = sorted(NEGATIONS)
    stopwords = sorted(STOPWORDS)
    rules: list[dict[str, str]] = []
    for word in negations:
        rules.append(_rule(f"negation-ref/{word}", "HIGH", word, WILDCARD))
    for word in negations:
        rules.append(_rule(f"negation-hyp/{word}", "HIGH", WILDCARD, word))
    for stopword in stopwords:
        rules.append(_rule(f"inert-deletion/{stopword}", "NONE", stopword, DELETED))
    for reference in stopwords:
        for hypothesis in stopwords:
            if reference == hypothesis:
                continue
            rules.append(
                _rule(
                    f"inert-substitution/{reference}__{hypothesis}",
                    "NONE",
                    reference,
                    hypothesis,
                )
            )
    rules.append(_rule("residual-wording", "LOW", WILDCARD, WILDCARD))
    return rules


def build_taxonomy(
    *,
    source_commit: str,
    source_sha256: str,
    generator_relpath: str = "scripts/build_semantic_impact_taxonomy.py",
) -> dict[str, object]:
    """The complete ``ACTIVE.json`` document.

    ``source_commit`` / ``source_sha256`` pin the E22 scan module this derivation
    imports -- the commit that landed it and the sha256 of ITS blob bytes at that
    commit (``git show <commit>:<path>``, the repository's stated hash authority),
    so a reader can re-derive the file from the same inputs.
    """

    if not source_commit or not source_sha256:
        raise ValueError("the taxonomy must pin the E22 scan module's commit and sha256")
    rules = taxonomy_rules()
    return {
        "schema": TAXONOMY_SCHEMA,
        "taxonomy_id": TAXONOMY_ID,
        "normalizer": WHISPER_NORMALIZER_NAME,
        "levels": list(IMPACTS),
        "high_level": HIGH_LEVEL,
        "derivation": {
            "kind": "mechanical projection of committed code; no new judgement",
            "source_module": SOURCE_MODULE,
            "source_module_commit": source_commit,
            "source_module_sha256": source_sha256,
            "source_taxonomy_version": TAXONOMY_VERSION,
            "source_exposure_row": EXPOSURE_ROW_ID,
            "projected_quantity": (
                "analysis.e22_error_taxonomy.semantic_impact, the span's own "
                "content_impact, restricted to one (reference word, hypothesis word) "
                "error instance"
            ),
            "generator": generator_relpath,
            "lexicons": {
                "NEGATIONS": sorted(NEGATIONS),
                "STOPWORDS": sorted(STOPWORDS),
            },
            "unrepresentable_triggers": [
                {"trigger": trigger, "why": why} for trigger, why in UNREPRESENTABLE_TRIGGERS
            ],
            "consequence": (
                "The HIGH tier of this taxonomy is E22's NEGATION trigger alone, so "
                "semantic-high-impact-error-rate-v1 under it is a strict LOWER BOUND on "
                "E22's own content-impact HIGH rate and must be quoted as the "
                "negation-critical rate, never as E22's 1.92 % agentic error rate. On "
                "Earnings-21 the digit trigger is carried by numeric-value-accuracy-v1 "
                "and the entity trigger by conec-entity-wer-official."
            ),
            "known_deviation": (
                "An INSERTED function word is LOW here and NONE in E22: an insertion is "
                "looked up as (\"*\", hypothesis word) and reaches the residual rule. "
                "Insertions carry zero reference-word mass, so no rate moves; they are "
                "reported separately in insertions_by_level."
            ),
        },
        "rules": rules,
    }


def rule_keys(rules: Iterable[Mapping[str, str]]) -> list[tuple[str, str]]:
    """The ``(ref, hyp)`` keys of a rule list, for a duplicate check outside the
    loader's own (the loader raises; a generator wants to count)."""

    return [(rule["ref"], rule["hyp"]) for rule in rules]
