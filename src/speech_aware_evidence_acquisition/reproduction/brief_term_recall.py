"""``brief-term-recall-v1``: how much of what the brief NAMES the transcript
actually keeps.

Corpus WER is the alignment anchor for Earnings-22 and it is not the thing a
pre-meeting brief is supposed to move: five metadata facts cannot shift 26,251
reference words, and a cell that only reported WER would either see nothing or
see runtime noise. This scorer is the cell's own targeted measurement, defined
BEFORE any KC-E2 number exists (``docs/readiness/2026-09-07-e22-kc-e2-pre-meeting-
brief-v1-preregistration.md`` section 5), and it is model-free, deterministic and
computable on the sealed comparator's own outputs.

THE DEFINITION, IN ONE SENTENCE
-------------------------------
Among a clip's reference words that lie inside a BRIEF TERM of that clip's own
call, the share the hypothesis reproduces -- pooled as ``sum(hits) /
sum(brief-term reference words)`` over the roster, exactly the corpus-style
aggregation ``asr-wer-esb-whisper`` uses for WER.

Spelled out, so nothing is left to reading:

* **Normalization.** The vendored Whisper ``EnglishTextNormalizer`` on BOTH
  sides and whitespace tokenization -- the same two lines
  ``reproduction.esb_reference.score_esb_outputs_whisper`` uses, so a brief-term
  word is the same object a WER word is.
* **Terms.** The five fields ``core.metadata_brief.BRIEF_FIELDS`` renders for
  the clip's OWN call: ticker, country, UN region, dialect family, language
  family. Never the twin's call -- the metric asks whether THIS call's facts
  survive, and it must therefore read the same terms for every arm.
* **Coverage.** Each term is normalized to a word tuple and matched against the
  reference word sequence as a contiguous n-gram, longest-first at each
  position, non-overlapping. A reference index inside any match is a brief-term
  word, attributed to the field of the term that covered it.
* **Recall.** The alignment is ``scoring.wer.align``'s own -- the frozen aligner,
  not a second one -- and a brief-term reference word counts as recalled exactly
  when that alignment marks it a HIT (``WerResult.ref_hit_mask``). A substituted
  or deleted brief-term word does not.

WHAT THE METRIC DOES NOT DO, STATED RATHER THAN DISCOVERED LATER
-----------------------------------------------------------------
It does not know a homograph from a name. A ticker like ``COST`` normalizes to
``cost``, which is ordinary earnings vocabulary, so its "term" mass is mostly
the common noun and both arms will recall nearly all of it. That inflates the
denominator and DILUTES an effect; it does not bias one arm against the other,
because both arms are scored on the same reference words with the same terms.
The per-field table below is what makes the dilution visible: a verdict reads the
field rows, not only the pooled number. The model-free audit
(``analysis.e22_brief_source_audit``) measures the dilution on the comparator
before the cell flies.

It is also not an entity metric. ``conec-entity-wer-official`` needs a
``wer_tags`` sidecar and ``data.carriers`` registers no entity layer for
earnings22-original; this scorer needs no annotation at all, only the corpus's
own metadata table, which is why it exists for this carrier.

SOURCES
-------
References come from the hash-pinned ESB reference layer through
``reproduction.esb_reference.load_esb_references``, which re-hashes the layer
against its committed receipt before a reference word is read. Terms come from
the carrier's own metadata table, resolved through the carrier descriptor the
same way the evidence source resolves it, and the table's measured sha256 is
written into the aggregate so a verdict can compare it against the fragment's own
pin rather than assume they agree.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping, Sequence

from ..core.metadata_brief import BRIEF_FIELDS, brief_terms, call_source_slice
from ..e0.artifacts import REPO_ROOT
from ..scoring.wer import align
from .asr_wer_whisper import WHISPER_NORMALIZER_NAME, normalize_whisper_english
from .esb_reference import (
    EsbReferenceError,
    _outputs_rows,
    load_esb_references,
    published_segment_key,
)

BRIEF_TERM_RECALL_SCORER_VERSION = "brief-term-recall-v1"

#: Field labels, in :data:`~speech_aware_evidence_acquisition.core.metadata_brief.
#: BRIEF_FIELDS` order -- the per-field table's fixed row order, so two runs'
#: receipts line up without sorting.
FIELD_LABELS: tuple[str, ...] = tuple(label for _, label in BRIEF_FIELDS)


class BriefTermRecallError(RuntimeError):
    """The brief-term recall metric could not be computed."""


def whisper_words(text: str) -> list[str]:
    """The metric's tokenization: the vendored Whisper normalizer, then
    ``str.split()`` -- byte-identical to ``score_esb_outputs_whisper``'s."""

    return normalize_whisper_english(text).split()


def term_tuples(terms: Mapping[str, str]) -> dict[str, tuple[tuple[str, ...], ...]]:
    """``{field label -> the normalized word tuples that field contributes}``.

    A field whose value normalizes to nothing contributes no tuple rather than an
    empty one; a duplicate tuple inside one field is dropped, keeping first
    order, so a table that repeated a value could not double-count it.
    """

    out: dict[str, tuple[tuple[str, ...], ...]] = {}
    for label in FIELD_LABELS:
        value = terms.get(label)
        if not isinstance(value, str):
            raise BriefTermRecallError(f"brief field {label!r} carries no text value")
        words = tuple(whisper_words(value))
        out[label] = (words,) if words else ()
    return out


def cover_reference(
    reference_words: Sequence[str], tuples_by_field: Mapping[str, Sequence[tuple[str, ...]]]
) -> list[str | None]:
    """One field label per reference index, ``None`` where no term covers it.

    Longest match first at each position, then earliest field in
    :data:`FIELD_LABELS` order, then left to right without overlap -- a fixed,
    stated tie-break, so the cover is a pure function of the two inputs.
    """

    candidates: list[tuple[int, int, str, tuple[str, ...]]] = []
    for field_index, label in enumerate(FIELD_LABELS):
        for words in tuples_by_field.get(label, ()):
            if words:
                candidates.append((-len(words), field_index, label, words))
    candidates.sort()
    cover: list[str | None] = [None] * len(reference_words)
    index = 0
    while index < len(reference_words):
        matched = 0
        for _, _, label, words in candidates:
            end = index + len(words)
            if end > len(reference_words):
                continue
            if tuple(reference_words[index:end]) == words:
                for position in range(index, end):
                    cover[position] = label
                matched = len(words)
                break
        index += matched if matched else 1
    return cover


def clip_counts(
    reference: str, hypothesis: str, terms: Mapping[str, str]
) -> dict[str, object]:
    """One clip's brief-term counts: covered reference words and hits, pooled and
    per field."""

    reference_words = whisper_words(reference)
    hypothesis_words = whisper_words(hypothesis)
    result = align(reference_words, hypothesis_words)
    cover = cover_reference(reference_words, term_tuples(terms))
    per_field = {label: {"reference_words": 0, "hits": 0} for label in FIELD_LABELS}
    covered = hits = 0
    for index, label in enumerate(cover):
        if label is None:
            continue
        covered += 1
        per_field[label]["reference_words"] += 1
        if result.ref_hit_mask[index]:
            hits += 1
            per_field[label]["hits"] += 1
    return {
        "brief_term_reference_words": covered,
        "brief_term_hits": hits,
        "recall": (hits / covered) if covered else 0.0,
        "reference_words": len(reference_words),
        "per_field": per_field,
    }


def merge_counts(per_sample: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Pooled aggregate: ``sum(hits) / sum(brief-term reference words)``, plus the
    per-field table and the share of all reference words the brief's terms cover."""

    covered = sum(int(row["brief_term_reference_words"]) for row in per_sample)
    hits = sum(int(row["brief_term_hits"]) for row in per_sample)
    reference_words = sum(int(row["reference_words"]) for row in per_sample)
    per_field = []
    for label in FIELD_LABELS:
        field_words = sum(int(row["per_field"][label]["reference_words"]) for row in per_sample)
        field_hits = sum(int(row["per_field"][label]["hits"]) for row in per_sample)
        per_field.append(
            {
                "field": label,
                "reference_words": field_words,
                "hits": field_hits,
                "recall": (field_hits / field_words) if field_words else 0.0,
            }
        )
    return {
        "brief_term_recall": (hits / covered) if covered else 0.0,
        "brief_term_reference_words": covered,
        "brief_term_hits": hits,
        "reference_words": reference_words,
        "brief_term_share_of_reference_words": (
            (covered / reference_words) if reference_words else 0.0
        ),
        "samples": len(per_sample),
        "per_field": per_field,
        "scorer_version": BRIEF_TERM_RECALL_SCORER_VERSION,
        "normalizer": WHISPER_NORMALIZER_NAME,
    }


def load_metadata_text(lock: Mapping[str, object], root: Path, carrier_lock_key: str) -> tuple[str, str, str]:
    """``(relpath, sha256, text)`` of the carrier's own metadata table.

    Resolved through the SAME ``core.evidence.e22_metadata_file_relpath`` the
    evidence source resolves it with, so the scorer and the arm can never read
    two different tables. The import is local because ``core.evidence`` imports
    ``core.metadata_brief``, and a module-level import here would make the two
    packages circular at import time.
    """

    from ..core.evidence import e22_metadata_file_relpath

    relpath = e22_metadata_file_relpath(lock, carrier_lock_key)
    path = Path(root) / relpath
    if not path.is_file():
        raise BriefTermRecallError(f"metadata table missing: {path}")
    blob = path.read_bytes()
    return relpath, hashlib.sha256(blob).hexdigest(), blob.decode("utf-8")


def score_brief_term_recall_outputs(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, object]:
    """``brief-term-recall-v1``, over one arm's sealed outputs.

    Uniform ``scorer(outputs_path, lock, root)`` signature, like every other
    registration in ``core.scorers``. Fails closed on a foreign carrier, on a
    sample the pinned reference layer does not carry, and on a clip whose call
    the metadata table does not name.
    """

    from ..core.evidence import brief_call_id

    references = load_esb_references(root, repo_root=repo_root)
    rows = _outputs_rows(outputs_path)
    if not rows:
        raise BriefTermRecallError(f"outputs file {outputs_path} carries no rows")
    carriers = {row.get("carrier_lock_key") for row in rows}
    if len(carriers) != 1:
        raise BriefTermRecallError(
            f"brief-term recall scores one carrier at a time, got {sorted(map(str, carriers))}"
        )
    carrier_lock_key = str(next(iter(carriers)))
    relpath, sha256_hex, text = load_metadata_text(lock, root, carrier_lock_key)

    terms_cache: dict[str, Mapping[str, str]] = {}
    per_sample: list[dict[str, object]] = []
    for number, row in enumerate(rows, start=1):
        raw_id = row.get("sample_id")
        if not isinstance(raw_id, str) or not raw_id:
            raise BriefTermRecallError(f"outputs line {number} carries no sample id")
        published = published_segment_key(raw_id)
        reference = references.get(published)
        if reference is None:
            raise EsbReferenceError(
                f"outputs line {number} names sample {raw_id!r}, which the hash-pinned "
                "ESB reference layer does not contain"
            )
        hypothesis = row.get("text")
        if not isinstance(hypothesis, str):
            raise BriefTermRecallError(f"outputs line {number} carries no hypothesis text")
        call_id = brief_call_id(raw_id)
        terms = terms_cache.get(call_id)
        if terms is None:
            terms = brief_terms(call_source_slice(text, call_id))
            terms_cache[call_id] = terms
        counts = clip_counts(reference, hypothesis, terms)
        counts["sample_id"] = raw_id
        counts["call_id"] = call_id
        per_sample.append(counts)
    aggregate = merge_counts(per_sample)
    aggregate["metadata_relpath"] = relpath
    aggregate["metadata_sha256"] = sha256_hex
    aggregate["calls"] = len(terms_cache)
    return {"per_sample": per_sample, "aggregate": aggregate}


__all__ = [
    "BRIEF_TERM_RECALL_SCORER_VERSION",
    "BriefTermRecallError",
    "FIELD_LABELS",
    "clip_counts",
    "cover_reference",
    "load_metadata_text",
    "merge_counts",
    "score_brief_term_recall_outputs",
    "term_tuples",
    "whisper_words",
]
