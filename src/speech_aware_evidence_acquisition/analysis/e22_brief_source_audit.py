"""KC-E2's model-free source audit: what the Earnings-22 metadata brief COULD
move, measured before the cell is allowed to fly.

Exposure row ``SAEA-E22-MF-BRIEF-SOURCE-AUDIT-V1`` (``model-free-check``). Zero
contacts of every kind: no model, tokenizer, embedder, retriever, network, GPU or
audio-decode touch, and no media byte is opened.

WHAT IT ANSWERS, AND WHY EACH QUESTION IS WORTH A ROW
-----------------------------------------------------
1. **The pairing arithmetic.** How many distinct CALLS the 1,500 dev clips come
   from -- that number is the bootstrap cluster count, and a cell whose interval
   rests on ten clusters must say so before it flies, not after.
2. **What the brief can even say.** The five metadata fields of each of those
   calls, from the corpus's own table and nothing else (owner ruling 2026-09-07:
   Earnings-22 collects no external information, so there is no company-name
   variant and no external lookup table).
3. **The reference-side potential.** How many DEV reference words are brief-term
   words at all, per field and per call, under the same Whisper normalizer the
   paper-facing scorer uses -- the metric's denominator, measured before the
   metric is used.
4. **The ceiling.** The sealed comparator's own error mass ON those words: a
   brief that fixed every one of them would move corpus WER by exactly that
   many points and no more. This is the number that decides whether KC-E2 is
   worth a GPU hour, and it is computed from the comparator's sealed outputs,
   never from a new contact.
5. **The homograph diagnostic**, which is what stops 4 from being read wrong. A
   ticker like ``COST`` normalizes to ``cost``; a country like ``India`` is a
   real call fact. The audit separates them WITHOUT a judgement call, by
   counting how many OTHER calls' references also contain the term: a term that
   appears in calls whose metadata does not carry it is ordinary vocabulary,
   and its mass is dilution rather than headroom.

THE READ IS SEALED-ONLY AND DEV-ONLY
------------------------------------
References come from the hash-pinned DEV10 ESB layer through
``reproduction.esb_reference.load_esb_references``, restricted to that one
receipt so the six calibration-exposed ESB TEST calls are unreachable from here.
Hypotheses come from the sealed ``SAEA-E22-DEV-ESB-TAIL2S-V1`` outputs the
2026-09-07 encoding verdict already published, and an IDENTITY ANCHOR on that
arm's corpus WER refuses to compute a single further number unless the sealed
rows reproduce it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from ..core.metadata_brief import BRIEF_FIELDS, brief_terms, call_source_slice
from ..reproduction.asr_wer_whisper import WHISPER_NORMALIZER_NAME
from ..reproduction.brief_term_recall import (
    BRIEF_TERM_RECALL_SCORER_VERSION,
    FIELD_LABELS,
    cover_reference,
    term_tuples,
    whisper_words,
)
from ..reproduction.conec_entity_scoring import OP_DELETION, OP_SUBSTITUTION
from ..reproduction.esb_reference import published_segment_key
from ..scoring.wer import align

ANALYSIS_VERSION = "saea-e22-brief-source-audit-v1"
EXPOSURE_ROW_ID = "SAEA-E22-MF-BRIEF-SOURCE-AUDIT-V1"
PREREGISTRATION = "docs/readiness/2026-09-07-e22-kc-e2-pre-meeting-brief-v1-preregistration.md"

#: The sealed comparator this cell pairs against: the admitted tail-silence-2s
#: arm of the 2026-09-07 encoding verdict, on the same 1,500 published segments.
COMPARATOR = {
    "run_id": "SAEA-E22-DEV-ESB-TAIL2S-V1",
    "attempt": "attempt-20260907T090708Z-df36cc",
    "scorer": "asr-wer-esb-whisper",
    "corpus_wer_percent": 9.4054,
    "source": "docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-verdict.md section 1.2",
}

ROSTER_RELPATH = "docs/receipts/rosters/e22-dev-esb-1500-tail2s-v1.json"
CLIP_CALL_MAP_RELPATH = "docs/receipts/artifacts/e22-dev1500-clip-call-map.json"
METADATA_RELPATH = "datasets/earnings21-22/earnings22/metadata.csv"

#: The identity anchor's tolerance, in WER points. The verdict published 9.4054
#: to four decimals, so anything inside half a unit of the last digit is the same
#: number and anything outside it is a different read.
ANCHOR_TOLERANCE_POINTS = 5e-5


class BriefSourceAuditError(RuntimeError):
    """An input drifted, or the comparator's identity anchor failed."""


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _load(path: Path) -> tuple[Mapping[str, object], str]:
    blob = Path(path).read_bytes()
    return json.loads(blob.decode("utf-8")), sha256_bytes(blob)


def load_clip_calls(repo_root: Path) -> dict[str, object]:
    """The committed clip -> call map, re-hashed and re-checked against its own
    recorded digests before a single number is computed."""

    document, digest = _load(Path(repo_root) / CLIP_CALL_MAP_RELPATH)
    mapping = {str(k): str(v) for k, v in dict(document["clip_call_map"]).items()}
    ids_sha256 = sha256_bytes("\n".join(sorted(mapping)).encode("utf-8"))
    map_sha256 = sha256_bytes(
        "\n".join(f"{clip},{mapping[clip]}" for clip in sorted(mapping)).encode("utf-8")
    )
    if ids_sha256 != document["ids_sha256"] or map_sha256 != document["map_sha256"]:
        raise BriefSourceAuditError(
            f"{CLIP_CALL_MAP_RELPATH} does not reproduce its own ids/map digests"
        )
    if int(document["count"]) != len(mapping):
        raise BriefSourceAuditError(f"{CLIP_CALL_MAP_RELPATH} count disagrees with its map")
    return {
        "clip_call": mapping,
        "calls": [str(call) for call in document["calls"]],
        "clips_per_call": {str(k): int(v) for k, v in dict(document["clips_per_call"]).items()},
        "split_identity_hash": str(document["split_identity_hash"]),
        "receipt_sha256": digest,
        "metadata_sha256": str(document["metadata_sha256"]),
    }


def load_sealed_hypotheses(root: Path, source: Mapping[str, str]) -> dict[str, str]:
    """``{published segment -> hypothesis}`` from one sealed arm's outputs."""

    path = Path(root) / "runs" / source["run_id"] / source["attempt"] / f"{source['run_id']}.outputs.jsonl"
    text = path.read_text(encoding="utf-8")
    rows = [line for line in text.split("\n") if line != ""]
    hypotheses: dict[str, str] = {}
    for number, line in enumerate(rows, start=1):
        row = json.loads(line)
        sample_id = published_segment_key(str(row["sample_id"]))
        if sample_id in hypotheses:
            raise BriefSourceAuditError(
                f"{path} collapses two rows onto published segment {sample_id!r}"
            )
        hypotheses[sample_id] = str(row["text"])
    if not hypotheses:
        raise BriefSourceAuditError(f"{path} carries no sealed rows")
    return hypotheses


def load_sealed_score_rows(
    root: Path, source: Mapping[str, str]
) -> dict[str, dict[str, float]]:
    """The sealed finalize per-sample rows of the paper-facing scorer, keyed by
    published segment -- the identity anchor's own input."""

    path = Path(root) / "runs" / source["run_id"] / source["attempt"] / f"{source['run_id']}.scores.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, float]] = {}
    for row in document[source["scorer"]]["per_sample"]:
        sample_id = published_segment_key(str(row["sample_id"]))
        rows[sample_id] = {
            key: float(row[key])
            for key in ("wer", "hits", "substitutions", "deletions", "insertions")
        }
    return rows


def identity_anchor(
    score_rows: Mapping[str, Mapping[str, float]],
    references: Mapping[str, str],
    clips: Sequence[str],
) -> dict[str, object]:
    """Reproduce the comparator's published corpus WER from its own sealed rows.

    Nothing downstream runs unless this holds: an audit that cannot re-derive the
    number it is measuring headroom against is measuring something else.
    """

    substitutions = deletions = insertions = 0
    reference_words = 0
    for clip in clips:
        row = score_rows.get(clip)
        if row is None:
            raise BriefSourceAuditError(f"the sealed score file has no row for clip {clip!r}")
        substitutions += int(row["substitutions"])
        deletions += int(row["deletions"])
        insertions += int(row["insertions"])
        reference_words += len(whisper_words(references[clip]))
    errors = substitutions + deletions + insertions
    measured = 100.0 * errors / reference_words if reference_words else 0.0
    expected = float(COMPARATOR["corpus_wer_percent"])
    reproduced = abs(measured - expected) <= ANCHOR_TOLERANCE_POINTS
    return {
        "reproduced": reproduced,
        "measured_corpus_wer_percent": round(measured, 6),
        "published_corpus_wer_percent": expected,
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "reference_words": reference_words,
        "clips": len(clips),
        "scorer": COMPARATOR["scorer"],
        "normalizer": WHISPER_NORMALIZER_NAME,
    }


def call_field_table(metadata_text: str, calls: Sequence[str]) -> list[dict[str, object]]:
    """The five brief fields of every dev call, plus that call's source-slice
    digest -- the answer to "what can the brief even say"."""

    table: list[dict[str, object]] = []
    for call in calls:
        slice_text = call_source_slice(metadata_text, call)
        entry: dict[str, object] = {
            "call_id": call,
            "source_slice_sha256": sha256_bytes(slice_text.encode("utf-8")),
        }
        entry.update(brief_terms(slice_text))
        table.append(entry)
    return table


def measure(
    *,
    metadata_text: str,
    references: Mapping[str, str],
    hypotheses: Mapping[str, str],
    clip_call: Mapping[str, str],
    clips: Sequence[str],
) -> dict[str, object]:
    """The whole measurement: coverage, recall, error mass, ceiling, homographs.

    One pass over the roster. Every count is pooled ``sum/sum``, never a mean of
    per-clip rates, for the reason ``analysis.e21_window_pairing`` gives: a
    four-word clip must not weigh as much as a forty-word one.
    """

    terms_by_call = {
        call: brief_terms(call_source_slice(metadata_text, call))
        for call in sorted(set(clip_call.values()))
    }
    tuples_by_call = {call: term_tuples(terms) for call, terms in terms_by_call.items()}

    total_reference_words = 0
    covered = hits = substitutions = deletions = 0
    per_field = {
        label: {"reference_words": 0, "hits": 0, "substitutions": 0, "deletions": 0}
        for label in FIELD_LABELS
    }
    per_call: dict[str, dict[str, int]] = {
        call: {"reference_words": 0, "brief_term_reference_words": 0, "hits": 0, "clips": 0}
        for call in terms_by_call
    }
    # Homograph diagnostic: how many of each call's brief-term occurrences land
    # in references of calls whose OWN metadata does not carry that term.
    term_occurrences: dict[tuple[str, str], dict[str, int]] = {}

    for clip in clips:
        call = clip_call[clip]
        reference_words = whisper_words(references[clip])
        hypothesis_words = whisper_words(hypotheses[clip])
        result = align(reference_words, hypothesis_words)
        total_reference_words += len(reference_words)
        per_call[call]["reference_words"] += len(reference_words)
        per_call[call]["clips"] += 1

        own_cover = cover_reference(reference_words, tuples_by_call[call])
        for index, label in enumerate(own_cover):
            if label is None:
                continue
            covered += 1
            per_call[call]["brief_term_reference_words"] += 1
            per_field[label]["reference_words"] += 1
            if result.ref_hit_mask[index]:
                hits += 1
                per_call[call]["hits"] += 1
                per_field[label]["hits"] += 1
        # S vs D on the covered words, from the SAME alignment: a covered index
        # that is not a hit was either substituted or deleted, and which of the
        # two it was is what tells a reader whether the core heard a wrong word
        # or heard nothing.
        operations = _operations(reference_words, hypothesis_words)
        for kind, ref_index in operations:
            if ref_index is None or own_cover[ref_index] is None:
                continue
            if kind == OP_SUBSTITUTION:
                substitutions += 1
                per_field[own_cover[ref_index]]["substitutions"] += 1
            elif kind == OP_DELETION:
                deletions += 1
                per_field[own_cover[ref_index]]["deletions"] += 1

        # Cross-call occurrence: every call's term set scanned over THIS clip.
        for other_call, tuples in tuples_by_call.items():
            other_cover = cover_reference(reference_words, tuples)
            for label in FIELD_LABELS:
                value = terms_by_call[other_call][label]
                count = sum(1 for entry in other_cover if entry == label)
                if not count:
                    continue
                bucket = term_occurrences.setdefault(
                    (label, value), {"own_call_words": 0, "other_call_words": 0}
                )
                key = "own_call_words" if other_call == call else "other_call_words"
                bucket[key] += count

    error_mass = covered - hits
    ceiling_points = (
        100.0 * error_mass / total_reference_words if total_reference_words else 0.0
    )
    return {
        "reference_words": total_reference_words,
        "brief_term_reference_words": covered,
        "brief_term_share_of_reference_words": (
            covered / total_reference_words if total_reference_words else 0.0
        ),
        "brief_term_hits": hits,
        "brief_term_recall": (hits / covered) if covered else 0.0,
        "brief_term_error_mass_words": error_mass,
        "brief_term_substitutions": substitutions,
        "brief_term_deletions": deletions,
        "ceiling_corpus_wer_points": round(ceiling_points, 6),
        "per_field": [
            {
                "field": label,
                **per_field[label],
                "recall": (
                    per_field[label]["hits"] / per_field[label]["reference_words"]
                    if per_field[label]["reference_words"]
                    else 0.0
                ),
                "ceiling_corpus_wer_points": round(
                    100.0
                    * (per_field[label]["reference_words"] - per_field[label]["hits"])
                    / total_reference_words,
                    6,
                )
                if total_reference_words
                else 0.0,
            }
            for label in FIELD_LABELS
        ],
        "per_call": [
            {
                "call_id": call,
                **per_call[call],
                "recall": (
                    per_call[call]["hits"] / per_call[call]["brief_term_reference_words"]
                    if per_call[call]["brief_term_reference_words"]
                    else 0.0
                ),
            }
            for call in sorted(per_call)
        ],
        "terms": [
            {
                "field": label,
                "term": value,
                "normalized": " ".join(whisper_words(value)),
                "own_call_reference_words": bucket["own_call_words"],
                "other_call_reference_words": bucket["other_call_words"],
                "call_specific": bucket["other_call_words"] == 0,
            }
            for (label, value), bucket in sorted(term_occurrences.items())
        ],
        "scorer_version": BRIEF_TERM_RECALL_SCORER_VERSION,
        "normalizer": WHISPER_NORMALIZER_NAME,
    }


def _operations(
    reference_words: Sequence[str], hypothesis_words: Sequence[str]
) -> list[tuple[str, int | None]]:
    """``(kind, reference index)`` per operation, from the frozen aligner's own
    trace (``reproduction.conec_entity_scoring.aligned_operations``, which
    ``tests/unit/test_conec_entity_scoring.py`` proves equal to ``align()``)."""

    from ..reproduction.conec_entity_scoring import aligned_operations

    return [(kind, ref_index) for kind, ref_index, _ in aligned_operations(
        list(reference_words), list(hypothesis_words)
    )]


def distinctive_summary(measurement: Mapping[str, object]) -> dict[str, object]:
    """The headline reading of the homograph diagnostic: how much of the term
    mass belongs to terms that occur ONLY in the calls whose metadata carries
    them, and how much is ordinary vocabulary the brief happens to name."""

    call_specific_words = sum(
        int(entry["own_call_reference_words"])
        for entry in measurement["terms"]
        if entry["call_specific"]
    )
    shared_words = sum(
        int(entry["own_call_reference_words"])
        for entry in measurement["terms"]
        if not entry["call_specific"]
    )
    covered = int(measurement["brief_term_reference_words"])
    return {
        "call_specific_reference_words": call_specific_words,
        "shared_vocabulary_reference_words": shared_words,
        "covered_reference_words": covered,
        "call_specific_share": (call_specific_words / covered) if covered else 0.0,
        "reading": (
            "a term whose only occurrences are in the calls whose metadata names it is a "
            "call fact; a term that also occurs in other calls' references is ordinary "
            "earnings vocabulary the brief happens to name. Both are inside the metric's "
            "denominator by construction and both arms are scored on the same words, so "
            "the shared half dilutes an effect rather than biasing one -- but a verdict "
            "that quotes only the pooled recall without this split is quoting a diluted "
            "number."
        ),
    }


def build_receipt(
    *,
    repo_root: Path,
    root: Path,
    references: Mapping[str, str],
    outbound_attempts: int,
    outbound_targets: Sequence[str],
) -> dict[str, object]:
    """The whole audit, as one receipt document. Deterministic: no timestamp, so
    two back-to-back writes reproduce the same sha256."""

    clip_calls = load_clip_calls(repo_root)
    # The map is keyed by the FLOWN id (``<call>-<segment>@ts2``); the reference
    # layer, the sealed score rows and the sealed outputs are all keyed by the
    # PUBLISHED segment. Fold once, here, exactly the way
    # ``analysis.e22_usage_cells`` folds its own -- deviation D-ENC-1 -- and
    # refuse if two flown ids ever collapsed onto one published segment.
    clip_call = {
        published_segment_key(clip): call
        for clip, call in clip_calls["clip_call"].items()
    }
    if len(clip_call) != len(clip_calls["clip_call"]):
        raise BriefSourceAuditError(
            "two flown clip ids collapse onto one published segment; the paired join "
            "would silently merge two rows"
        )
    clips = sorted(clip_call)

    metadata_path = Path(root) / METADATA_RELPATH
    metadata_blob = metadata_path.read_bytes()
    metadata_sha256 = sha256_bytes(metadata_blob)
    if metadata_sha256 != clip_calls["metadata_sha256"]:
        raise BriefSourceAuditError(
            f"the metadata table hashes to {metadata_sha256}, not the clip-call map's "
            f"{clip_calls['metadata_sha256']}"
        )
    metadata_text = metadata_blob.decode("utf-8")

    missing = [clip for clip in clips if clip not in references]
    if missing:
        raise BriefSourceAuditError(
            f"the pinned DEV10 reference layer is missing {len(missing)} roster clips, "
            f"first {missing[0]!r}"
        )

    score_rows = load_sealed_score_rows(root, COMPARATOR)
    anchor = identity_anchor(score_rows, references, clips)
    if not anchor["reproduced"]:
        raise BriefSourceAuditError(
            "identity anchor FAILED: the sealed rows give "
            f"{anchor['measured_corpus_wer_percent']} against the published "
            f"{anchor['published_corpus_wer_percent']}; refusing to measure headroom "
            "against a number this read cannot reproduce"
        )
    hypotheses = load_sealed_hypotheses(root, COMPARATOR)
    absent = [clip for clip in clips if clip not in hypotheses]
    if absent:
        raise BriefSourceAuditError(
            f"the sealed outputs are missing {len(absent)} roster clips, first {absent[0]!r}"
        )

    measurement = measure(
        metadata_text=metadata_text,
        references=references,
        hypotheses=hypotheses,
        clip_call=clip_call,
        clips=clips,
    )
    return {
        "schema": ANALYSIS_VERSION,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": EXPOSURE_ROW_ID,
        "preregistration": PREREGISTRATION,
        "contacts": {
            "model": 0,
            "tokenizer": 0,
            "embedder": 0,
            "retriever": 0,
            "network": 0,
            "gpu": 0,
            "audio_decode_seconds": 0,
            "media_bytes_opened": 0,
            "outbound_connection_attempts": int(outbound_attempts),
            "outbound_targets": list(outbound_targets),
        },
        "test_split_read": False,
        "inputs": {
            "clip_call_map": CLIP_CALL_MAP_RELPATH,
            "clip_call_map_sha256": clip_calls["receipt_sha256"],
            "roster_receipt": ROSTER_RELPATH,
            "metadata_relpath": METADATA_RELPATH,
            "metadata_sha256": metadata_sha256,
            "reference_layer": "the hash-pinned DEV10 ESB layer only (test layer unreachable)",
            "comparator": dict(COMPARATOR),
        },
        "pairing": {
            "clips": len(clips),
            "clusters": len(clip_calls["calls"]),
            "cluster_unit": "the source call",
            "clips_per_call": clip_calls["clips_per_call"],
            "split_identity_hash": clip_calls["split_identity_hash"],
        },
        "identity_anchor": anchor,
        "call_fields": call_field_table(metadata_text, clip_calls["calls"]),
        "brief_field_labels": [label for _, label in BRIEF_FIELDS],
        "measurement": measurement,
        "distinctive": distinctive_summary(measurement),
        "external_sources": {
            "used": False,
            "ruling": (
                "owner 2026-09-07: Earnings-22 must not collect any external information, "
                "or the result stops being comparable with the academic references. The "
                "company-name brief variant is dropped, no ticker -> legal-name lookup "
                "table is built or registered, and the brief's only source is the "
                "corpus's own metadata table."
            ),
        },
    }


__all__ = [
    "ANALYSIS_VERSION",
    "BriefSourceAuditError",
    "COMPARATOR",
    "EXPOSURE_ROW_ID",
    "build_receipt",
    "call_field_table",
    "distinctive_summary",
    "identity_anchor",
    "load_clip_calls",
    "load_sealed_hypotheses",
    "load_sealed_score_rows",
    "measure",
]
