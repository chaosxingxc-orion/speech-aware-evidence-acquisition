"""ConEC per-entity-type WER: a definition mirror of the paper's own scorer.

WHAT THE PAPER SPECIFIES (primary source, quoted)
-------------------------------------------------
ConEC ("ConEC: Earnings Call Dataset with Real-world Contexts for
Benchmarking Contextual Speech Recognition", Huang et al., LREC-COLING 2024,
https://aclanthology.org/2024.lrec-main.328/, pp. 3700-3706) states its whole
metric protocol in section 4.1:

    "We use the fstalign tool to evaluate overall WER, WER for common/rare
    words, and WER for each entity types. [...] Hypothesis and reference texts
    are normalized with Whisper normalizer before being fed into fstalign."

Its footnote 8 pins the tool to https://github.com/revdotcom/fstalign and its
footnote 9 pins the normalizer to https://github.com/kurianbenoy/
whisper_normalizer -- a repackaging of OpenAI Whisper's own
``EnglishTextNormalizer``, which is exactly what
``reproduction/whisper_normalizer/`` already vendors byte-for-byte (tag
``v20240930``; that package's ``PROVENANCE.md`` carries the per-file
SHA-256s). Its footnote 6 points the entity taxonomy at the Earnings-21
release's own definitions. The paper defines NO entity F1 and no entity
precision/recall: Table 2's only per-entity quantity is a WER, so no
``-f1`` companion scorer is registered here (there is nothing to mirror).

WHY THIS IS A MIRROR AND NOT THE OFFICIAL BINARY
------------------------------------------------
fstalign is a C++/OpenFST program. This repository's standing rule -- carried
in every Earnings verdict since 2026-09-04 -- is that **fstalign is not
installed and is not run**, so the official metric code cannot be vendored
and executed the way ``reproduction/audio2tool_official/`` vendors Audio2Tool's
Python ``metrics.py`` or the way ``reproduction/slurp_official_eval.py``
subprocesses SLURP's real ``evaluate.py``. What is mirrored here is the
DEFINITION, read out of fstalign's own source at commit
``69df0b2b357f994101d630cb3f56e22b57ebcf04`` (branch ``develop``, Apache-2.0):

* ``src/wer.cpp::RecordTagWer`` -- the per-``wer_tags``-entity-ID accounting::

      for (const auto &stitch : stitches) {
        if (!stitch.nlpRow.wer_tags.empty()) {
          for (auto wer_tag : stitch.nlpRow.wer_tags) {
            ...
            wer_results[wer_tag.tag_id].insertions   += ins;
            wer_results[wer_tag.tag_id].deletions    += del;
            wer_results[wer_tag.tag_id].substitutions += sub;
            if (!ins) { wer_results[wer_tag.tag_id].numWordsInReference += 1; }

  An INSERTION stitch carries no NLP row, so its ``wer_tags`` list is empty and
  the loop body never runs for it: **fstalign attributes no insertion to any
  entity ID**. Its own committed side-by-side fixture (``test/data/
  short.sbs.txt``) shows exactly that -- every ``<ins>`` row has an empty
  ``Wer_Tag_Entities`` column. This mirror does the same.
* ``src/wer.h::WerResult`` -- ``NumErrors() = insertions + substitutions +
  deletions`` and ``WER() = NumErrors() / numWordsInReference``.
* ``src/Nlp.cpp::NlpFstLoader`` -- ``tag.entity_type`` comes from the
  ``wer_tag.json`` sidecar, keyed by tag id. This repository already reads that
  layer through ``data.references.reference_entity_mentions``.

WHY THE ``wer_tags`` PATH AND NOT THE ``tags`` PATH. fstalign also reports a
``classWER`` block built from the ``.nlp`` ``tags`` column (``src/wer.cpp::
RecordWer``). On the reference layer this study actually scores against --
``earnings21-original``, the Rev release, D1-hash-pinned -- that column carries
NO named-entity classes at all. Measured over call ``4330115``: 285 of 6,602
tokens carry a ``tags`` label and every one of them is a normalization class
(CONTRACTION 155, CARDINAL 49, FALLBACK 24, PERCENT 19, YEAR 13, ABBREVIATION
10, MONEY 6, ALPHANUMERIC 6, ORDINAL 2, WEBSITE 1), while 886 tokens carry
``wer_tags`` IDs whose sidecar types include PERSON, ORG, GPE, LOC, PRODUCT,
EVENT, NORP and FAC -- ConEC Table 2's eight columns. The ``tags`` path cannot
express the paper's table on these files; the ``wer_tags`` path can, and it is
the same layer ConEC's own corrected release ships.

THE TWO NAMED DIFFERENCES FROM fstalign, STATED NOT HIDDEN
----------------------------------------------------------
1. **Aligner.** fstalign aligns through an OpenFST composition and a shortest-
   path walk; this mirror uses the study's frozen unit-cost Levenshtein
   (``scoring.wer.align``'s own algorithm, re-expressed here as an operation
   trace -- see :func:`aligned_operations`, whose counts are asserted equal to
   ``align()``'s in ``tests/unit/test_conec_entity_scoring.py``). Both minimize
   the same unit-cost edit distance, so the TOTAL error count agrees; where
   several minimal alignments exist the two may place a given error on a
   different reference token, which can move an individual class by a token or
   two. It cannot move the corpus total.
2. **Normalization granularity.** fstalign consumes per-token rows (an NLP
   reference and a CTM hypothesis), so ConEC's "normalized with Whisper
   normalizer" was necessarily applied cell-wise. Applying it cell-wise here
   would change the reference word count by +0.55 % (361,740 against 359,765 on
   the 44 discovery calls) and would break comparability with this study's own
   ``asr-wer-whisper`` corpus number. So the ALIGNMENT here runs on the
   whole-string normalization -- byte-identical to ``asr-wer-whisper``'s, hence
   the ``__ALL__`` bucket reproduces the sealed corpus WER exactly, which is
   this scorer's own built-in identity anchor -- and the entity labels are
   carried onto that sequence from a run-chunked normalization by
   :func:`transfer_owners`. Positions the transfer cannot resolve are counted
   and reported as ``unlabelled_reference_words``, never silently assigned.

This module is deliberately free of any ``data.references`` import (that
module may be imported only by ``core/scorers.py``; ``tests/contract/
test_reference_import_isolation.py`` AST-enforces it). The registered scorer
``conec-entity-wer-official`` lives in ``core/scorers.py`` and calls into here.
"""

from __future__ import annotations

import difflib
from typing import Iterable, Mapping, Sequence

from .asr_wer_whisper import WHISPER_NORMALIZER_NAME, normalize_whisper_english

CONEC_ENTITY_SCORER_VERSION = "conec-entity-wer-fstalign-mirror-v1"
"""Version of THIS mirror, not of fstalign."""

FSTALIGN_DEFINITION_SOURCE = (
    "github.com/revdotcom/fstalign@69df0b2b357f994101d630cb3f56e22b57ebcf04"
    " (Apache-2.0): src/wer.cpp RecordTagWer, src/wer.h WerResult, src/Nlp.cpp NlpFstLoader"
)

CONEC_PAPER_SOURCE = "aclanthology.org/2024.lrec-main.328 (LREC-COLING 2024), section 4.1"

NON_ENTITY_BUCKET = "__NON_ENTITY__"
"""ConEC Table 2's "None" column: reference words carrying no ``wer_tags`` ID."""

OVERALL_BUCKET = "__ALL__"
"""Every reference word, insertions included -- ConEC Table 2's "WER" column,
and the identity anchor against ``asr-wer-whisper``'s corpus number."""

UNLABELLED_BUCKET = "__UNLABELLED__"
"""Reference words :func:`transfer_owners` could not carry a label onto."""

#: Operation kinds in an :func:`aligned_operations` trace.
OP_HIT = "hit"
OP_SUBSTITUTION = "sub"
OP_DELETION = "del"
OP_INSERTION = "ins"

_REFERENCE_CONSUMING = frozenset({OP_HIT, OP_SUBSTITUTION, OP_DELETION})


class ConecScoringError(RuntimeError):
    """The mirror's own invariants do not hold on the inputs it was given."""


def aligned_operations(
    ref: Sequence[str], hyp: Sequence[str]
) -> tuple[tuple[str, int | None, int | None], ...]:
    """The operation trace of the SAME alignment ``scoring.wer.align`` computes.

    Returns forward-order ``(kind, ref_index, hyp_index)`` triples, where
    ``kind`` is one of :data:`OP_HIT` / :data:`OP_SUBSTITUTION` /
    :data:`OP_DELETION` / :data:`OP_INSERTION`, ``ref_index`` is ``None`` for
    an insertion and ``hyp_index`` is ``None`` for a deletion.

    The cost matrix and the backtrace preference (match/substitution, then
    deletion, then insertion) are transcribed from the frozen
    ``scoring/wer.py`` (E0 D3 freeze) so the two agree operation for
    operation. This is a re-expression rather than a call because the frozen
    aligner returns only a per-reference-token hit mask and never a trace, and
    the frozen scoring package is hash-pinned and must not grow one. The
    equality is not assumed: ``tests/unit/test_conec_entity_scoring.py``
    asserts it against ``align()`` on fixed and randomized inputs, and
    :func:`operation_counts` re-derives the counts this trace implies.
    """

    for label, seq in (("ref", ref), ("hyp", hyp)):
        if not all(isinstance(token, str) for token in seq):
            raise TypeError(f"{label} tokens must all be str")
    rows, cols = len(ref) + 1, len(hyp) + 1
    cost = [[0] * cols for _ in range(rows)]
    for i in range(1, rows):
        cost[i][0] = i
    for j in range(1, cols):
        cost[0][j] = j
    for i in range(1, rows):
        row, previous = cost[i], cost[i - 1]
        ref_token = ref[i - 1]
        for j in range(1, cols):
            diagonal = previous[j - 1] + (0 if ref_token == hyp[j - 1] else 1)
            deletion = previous[j] + 1
            insertion = row[j - 1] + 1
            row[j] = min(diagonal, deletion, insertion)

    reversed_ops: list[tuple[str, int | None, int | None]] = []
    i, j = len(ref), len(hyp)
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            diagonal = cost[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1)
            if cost[i][j] == diagonal:
                kind = OP_HIT if ref[i - 1] == hyp[j - 1] else OP_SUBSTITUTION
                reversed_ops.append((kind, i - 1, j - 1))
                i, j = i - 1, j - 1
                continue
        if i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            reversed_ops.append((OP_DELETION, i - 1, None))
            i -= 1
            continue
        reversed_ops.append((OP_INSERTION, None, j - 1))
        j -= 1
    reversed_ops.reverse()
    return tuple(reversed_ops)


def operation_counts(
    operations: Sequence[tuple[str, int | None, int | None]],
    reference_length: int,
    hypothesis_length: int,
) -> dict[str, int]:
    """Counts implied by a trace, with the trace's own structural invariants
    checked (fail-closed). Every reference index appears exactly once across
    the reference-consuming operations, every hypothesis index exactly once
    across the hypothesis-consuming ones, and both in increasing order."""

    counts = {OP_HIT: 0, OP_SUBSTITUTION: 0, OP_DELETION: 0, OP_INSERTION: 0}
    next_ref = 0
    next_hyp = 0
    for kind, ref_index, hyp_index in operations:
        if kind not in counts:
            raise ConecScoringError(f"unknown alignment operation {kind!r}")
        counts[kind] += 1
        if kind in _REFERENCE_CONSUMING:
            if ref_index != next_ref:
                raise ConecScoringError(
                    f"alignment trace consumed reference index {ref_index!r} where "
                    f"{next_ref} was due"
                )
            next_ref += 1
        elif ref_index is not None:
            raise ConecScoringError("an insertion may not carry a reference index")
        if kind in (OP_HIT, OP_SUBSTITUTION, OP_INSERTION):
            if hyp_index != next_hyp:
                raise ConecScoringError(
                    f"alignment trace consumed hypothesis index {hyp_index!r} where "
                    f"{next_hyp} was due"
                )
            next_hyp += 1
        elif hyp_index is not None:
            raise ConecScoringError("a deletion may not carry a hypothesis index")
    if next_ref != reference_length:
        raise ConecScoringError(
            f"alignment trace consumed {next_ref} reference words, expected {reference_length}"
        )
    if next_hyp != hypothesis_length:
        raise ConecScoringError(
            f"alignment trace consumed {next_hyp} hypothesis words, expected {hypothesis_length}"
        )
    counts["errors"] = counts[OP_SUBSTITUTION] + counts[OP_DELETION] + counts[OP_INSERTION]
    counts["reference_words"] = reference_length
    return counts


def whole_string_whisper_words(tokens: Sequence[str]) -> list[str]:
    """The reference word sequence ``asr-wer-whisper`` itself aligns against:
    the raw reference tokens space-joined, Whisper-normalized once as a whole
    string, split on whitespace."""

    return normalize_whisper_english(" ".join(tokens)).split()


def hypothesis_whisper_words(text: str) -> list[str]:
    """The hypothesis word sequence ``asr-wer-whisper`` aligns against: the
    transcript Whisper-normalized once as a whole string, split on whitespace."""

    return normalize_whisper_english(text).split()


def run_chunked_whisper_words(
    tokens: Sequence[str], owners: Sequence[tuple[str, ...]]
) -> tuple[list[str], list[tuple[str, ...]]]:
    """Whisper-normalize the reference in maximal runs of constant owner set.

    ``owners[k]`` is the tuple of ``wer_tags`` entity IDs carried by raw token
    ``tokens[k]`` (empty tuple for an untagged token). Consecutive tokens with
    an identical owner tuple are normalized together as one string, so a
    multi-word number inside a run still merges the way the whole-string
    normalizer merges it; only a merge that would straddle an entity boundary
    is lost, and that is exactly the boundary the label has to respect anyway.

    Returns the concatenated word sequence and, position for position, the
    owner tuple it came from.
    """

    if len(tokens) != len(owners):
        raise ConecScoringError(
            f"run chunking needs one owner tuple per token; got {len(owners)} for {len(tokens)}"
        )
    words: list[str] = []
    word_owners: list[tuple[str, ...]] = []
    index = 0
    while index < len(tokens):
        end = index
        while end < len(tokens) and owners[end] == owners[index]:
            end += 1
        piece = normalize_whisper_english(" ".join(tokens[index:end])).split()
        words.extend(piece)
        word_owners.extend([owners[index]] * len(piece))
        index = end
    return words, word_owners


def transfer_owners(
    chunked_words: Sequence[str],
    chunked_owners: Sequence[tuple[str, ...]],
    whole_words: Sequence[str],
) -> list[tuple[str, ...] | None]:
    """Carry per-word owner tuples from the run-chunked normalization onto the
    whole-string normalization.

    The two sequences are the same text normalized at two granularities and
    agree on about 99.5 % of positions (measured: 14,475 of 14,541 on the
    longest Earnings-21 call). ``difflib.SequenceMatcher`` -- stdlib,
    deterministic, ``autojunk=False`` so no popular-element heuristic can fire
    on a 300k-word corpus -- supplies the matching blocks; a whole-string
    position inside a matching block takes its counterpart's owner tuple, and
    every other position is left ``None``. ``None`` is never treated as "no
    entity": the caller counts those positions separately under
    :data:`UNLABELLED_BUCKET`, so an unresolved position can never quietly
    deflate an entity denominator.
    """

    transferred: list[tuple[str, ...] | None] = [None] * len(whole_words)
    matcher = difflib.SequenceMatcher(None, list(chunked_words), list(whole_words), autojunk=False)
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            transferred[block.b + offset] = chunked_owners[block.a + offset]
    return transferred


def _blank_counts() -> dict[str, int]:
    return {
        "substitutions": 0,
        "deletions": 0,
        "insertions": 0,
        "reference_words": 0,
    }


def _finish(counts: Mapping[str, int]) -> dict[str, object]:
    errors = counts["substitutions"] + counts["deletions"] + counts["insertions"]
    reference_words = counts["reference_words"]
    return {
        "substitutions": counts["substitutions"],
        "deletions": counts["deletions"],
        "insertions": counts["insertions"],
        "errors": errors,
        "reference_words": reference_words,
        "wer": (errors / reference_words) if reference_words else 0.0,
    }


def entity_wer_buckets(
    operations: Sequence[tuple[str, int | None, int | None]],
    owners: Sequence[tuple[str, ...] | None],
    entity_types: Mapping[str, str],
) -> dict[str, dict[str, object]]:
    """fstalign ``RecordTagWer`` accounting, aggregated by entity type.

    ``owners[p]`` is the tuple of entity IDs carried by whole-string reference
    word ``p`` (``None`` when :func:`transfer_owners` could not resolve it);
    ``entity_types`` maps an entity ID to its sidecar class. A reference word
    carrying two IDs of the same type is counted twice for that type -- exactly
    what fstalign's per-ID loop does, since it visits the stitch once per tag.

    Insertions reach only :data:`OVERALL_BUCKET`: fstalign cannot attribute an
    insertion to an entity ID (an insertion stitch has no NLP row), so no
    entity bucket and no :data:`NON_ENTITY_BUCKET` bucket carries one here
    either. :data:`OVERALL_BUCKET` therefore reports ``(S + D + I) / reference
    words`` -- ConEC Table 2's "WER" column -- while every other bucket reports
    ``(S + D) / tagged reference words``.
    """

    buckets: dict[str, dict[str, int]] = {
        OVERALL_BUCKET: _blank_counts(),
        NON_ENTITY_BUCKET: _blank_counts(),
        UNLABELLED_BUCKET: _blank_counts(),
    }
    field = {
        OP_SUBSTITUTION: "substitutions",
        OP_DELETION: "deletions",
        OP_INSERTION: "insertions",
    }
    for kind, ref_index, _ in operations:
        if kind == OP_INSERTION:
            buckets[OVERALL_BUCKET]["insertions"] += 1
            continue
        buckets[OVERALL_BUCKET]["reference_words"] += 1
        if kind in field:
            buckets[OVERALL_BUCKET][field[kind]] += 1
        owner = owners[ref_index] if ref_index is not None else None
        if owner is None:
            target_names: tuple[str, ...] = (UNLABELLED_BUCKET,)
        elif not owner:
            target_names = (NON_ENTITY_BUCKET,)
        else:
            target_names = tuple(entity_types.get(entity_id, "") for entity_id in owner)
        for name in target_names:
            if not name:
                raise ConecScoringError(
                    "an entity id reached the ConEC mirror with no entity type; the "
                    "caller must supply a type for every id it labels a word with"
                )
            bucket = buckets.setdefault(name, _blank_counts())
            bucket["reference_words"] += 1
            if kind in field:
                bucket[field[kind]] += 1
    return {name: _finish(counts) for name, counts in buckets.items()}


def merge_buckets(
    per_sample: Iterable[Mapping[str, Mapping[str, object]]],
) -> dict[str, dict[str, object]]:
    """Corpus-level buckets: sum the counts, then divide once. Never an average
    of per-call rates -- the same corpus-aggregation rule ``asr-wer-whisper``
    and fstalign both use."""

    totals: dict[str, dict[str, int]] = {}
    for sample in per_sample:
        for name, values in sample.items():
            bucket = totals.setdefault(name, _blank_counts())
            for key in ("substitutions", "deletions", "insertions", "reference_words"):
                bucket[key] += int(values[key])
    return {name: _finish(counts) for name, counts in sorted(totals.items())}


def scorer_provenance() -> dict[str, object]:
    """The machine-visible statement that this is a definition mirror."""

    return {
        "scorer_version": CONEC_ENTITY_SCORER_VERSION,
        "normalizer": WHISPER_NORMALIZER_NAME,
        "implementation": "definition-mirror",
        "official_tool_run": False,
        "official_tool": "revdotcom/fstalign",
        "definition_source": FSTALIGN_DEFINITION_SOURCE,
        "paper_source": CONEC_PAPER_SOURCE,
        "insertions_attributed_to_entities": False,
    }
