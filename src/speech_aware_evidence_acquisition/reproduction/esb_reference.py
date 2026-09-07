"""ESB Earnings-22 utterance references, and the two scorers that read them.

Why this module exists at all
-----------------------------

The only same-model published number this study can align against on any of
its three carriers is Qwen3-Omni-30B-A3B-Instruct's **9.79** zero-shot WER on
the ESB "Earnings22" test subset. That column is not the 125-file corpus and
not a per-call number: it is **2,735 short utterances** cut from six calls at
the boundaries published in ``sanchit-gandhi/earnings22_split``, each scored
against that table's own ``sentence`` field.

This study's carrier reference layer cannot express that. ``data.references``
resolves exactly one ``.nlp`` file per CALL id under the locked carrier tree
(``<asset root>/transcripts/nlp_references/<sample_id>.nlp``), and
``contracts.FrozenCoreGate.verify_reference_identity`` fails closed for any
sample id D1 does not record in that carrier's ``nlp_references`` manifest.
An utterance is neither: it has no ``.nlp`` file, and inventing one would
mean writing 2,735 derived files into a locked dataset tree that D1 hashed.

So the utterance references travel their own rail, the SAME way the two other
carriers' gold already does. ``a2t-toolcall``/``slurp-slu`` never touch
``data.references`` either -- their gold comes from ``data.audio2tool`` /
``data.slurp`` -- and this module is the third instance of that pattern, not
a new one. It is deliberately OUTSIDE the E0 D3 frozen ``scoring/`` package
(same as ``reproduction.a2t_scorer`` / ``reproduction.slurp_official_eval``)
and it never imports ``data.references``.

What replaces the D1 reference-identity gate
--------------------------------------------

Nothing is skipped silently. ``verify_reference_identity`` would refuse these
ids because they are genuinely outside D1's reference closure, so the identity
guarantee is supplied here instead, fail-closed and in this process:

* the derived reference layer is written ONCE by
  ``scripts/build_e22_esb_utterance_roster.py`` from the hash-pinned segment
  table, under the controlled data root -- never in Git, never inside the
  locked carrier tree;
* its SHA-256, row count and word count are committed in
  ``docs/checks/.../reference-layer/reference-layer-receipt.json``;
* :func:`load_esb_references` re-hashes the file on every call and refuses on
  any drift, exactly as the media rail re-hashes media at model-touch time.

Every formal WER is ``f(frozen scoring code, hypothesis text, reference
bytes)``. The frozen scoring code is unchanged (``scoring.wer.align``,
``scoring.normalize.tokens_v1``, the vendored Whisper normalizer); the
hypothesis is bound by the bundle contract's ``response_text_sha256``; and
the reference bytes are bound by the receipt this module verifies.

The two scorers
---------------

``asr-wer-esb-whisper`` and ``asr-wer-esb`` are the utterance-scoped twins of
the registered ``asr-wer-whisper`` and ``asr-wer``. Same alignment, same
normalizers, same aggregation conventions, same per-sample dict shape -- the
ONLY difference is where a row's reference comes from. That is what makes the
Earnings-22 number comparable, metric for metric, with the Earnings-21 number
this repository already published from the carrier reference layer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from ..data.variant_ids import published_sample_key
from ..e0.artifacts import REPO_ROOT
from ..scoring import align, tokens_v1
from .asr_wer_whisper import (
    WHISPER_NORMALIZER_NAME,
    WHISPER_WER_SCORER_VERSION,
    normalize_whisper_english,
)

ESB_REFERENCE_RECEIPT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-04-e22-esb-shortform-alignment-400-v1/reference-layer/"
    "reference-layer-receipt.json"
)
#: The 2026-09-05 prompt A/B population: the ESB train-split utterances of this
#: study's own Earnings-22 ``dev`` subset10. A second layer rather than an
#: edit of the first, because the sealed 2026-09-04 manifests pin that layer's
#: SHA-256 and its bytes must never move.
ESB_DEV10_REFERENCE_RECEIPT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-05-e22-dev-esb-prompt-ab-v1/reference-layer/"
    "reference-layer-receipt.json"
)
#: Every layer the two ESB scorers may resolve a reference from, in a fixed
#: order. Each is verified independently; ids may not repeat across layers.
ESB_REFERENCE_RECEIPT_RELPATHS = (
    ESB_REFERENCE_RECEIPT_RELPATH,
    ESB_DEV10_REFERENCE_RECEIPT_RELPATH,
)
ESB_REFERENCE_RECEIPT_SCHEMA = "saea-e22-esb-reference-layer-receipt-v1"
ESB_CARRIER_LOCK_KEY = "earnings22-original"
ESB_WER_SCORER_VERSION = "asr-wer-esb-v1"


class EsbReferenceError(RuntimeError):
    """The derived ESB reference layer is missing, malformed, or has drifted
    from the SHA-256 its committed receipt pins."""


def _read_json(path: Path, label: str) -> Mapping[str, object]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EsbReferenceError(f"cannot read {label}: {error}") from error
    if not isinstance(document, Mapping):
        raise EsbReferenceError(f"{label} must be a JSON object")
    return document


def load_esb_references(
    root: Path,
    *,
    repo_root: Path = REPO_ROOT,
    receipt_relpaths: tuple[str, ...] = ESB_REFERENCE_RECEIPT_RELPATHS,
) -> dict[str, str]:
    """``{utterance id -> reference sentence}``, hash-verified, over every layer.

    ``root`` is the controlled DATA root (the same argument every registered
    scorer already takes); ``repo_root`` is the checkout the committed receipts
    are read from, with the same test-overridable default convention
    ``core.scorers.score_bundle`` uses.

    Fails closed -- never silently empty -- on a missing receipt, a schema or
    carrier mismatch, a missing reference file, a SHA-256 that has drifted
    from the receipt, a row count that disagrees with it, a duplicate id, an
    id that two layers both claim, or an empty sentence. A layer whose receipt
    file is absent from this checkout is skipped, but at least one layer must
    load or the call is refused.
    """

    merged: dict[str, str] = {}
    loaded = 0
    for relpath in receipt_relpaths:
        if not (Path(repo_root) / relpath).is_file():
            continue
        layer = _load_one_esb_layer(root, repo_root=repo_root, receipt_relpath=relpath)
        overlap = sorted(set(layer) & set(merged))
        if overlap:
            raise EsbReferenceError(
                f"ESB reference layers disagree: {len(overlap)} sample id(s) appear in "
                f"more than one hash-pinned layer (first: {overlap[0]!r}); a sample must "
                "have exactly one reference"
            )
        merged.update(layer)
        loaded += 1
    if not loaded:
        # No layer's receipt exists in this checkout. Load the first configured
        # one anyway so its own fail-closed message ("cannot read ...") is what
        # the caller sees, exactly as it did when this rail had one layer.
        _load_one_esb_layer(
            root, repo_root=repo_root, receipt_relpath=receipt_relpaths[0]
        )
        raise EsbReferenceError(
            "no ESB reference-layer receipt was found in this checkout "
            f"({list(receipt_relpaths)}); scoring without a hash-pinned reference layer "
            "is refused"
        )
    return merged


def _load_one_esb_layer(
    root: Path, *, repo_root: Path, receipt_relpath: str
) -> dict[str, str]:
    """One hash-pinned layer, verified end to end (see :func:`load_esb_references`)."""

    receipt_path = Path(repo_root) / receipt_relpath
    receipt = _read_json(receipt_path, "ESB reference-layer receipt")
    if receipt.get("schema") != ESB_REFERENCE_RECEIPT_SCHEMA:
        raise EsbReferenceError(
            f"ESB reference-layer receipt schema must be {ESB_REFERENCE_RECEIPT_SCHEMA!r}, "
            f"got {receipt.get('schema')!r}"
        )
    if receipt.get("carrier") != ESB_CARRIER_LOCK_KEY:
        raise EsbReferenceError(
            f"ESB reference-layer receipt names carrier {receipt.get('carrier')!r}, not "
            f"{ESB_CARRIER_LOCK_KEY!r}"
        )
    relpath = receipt.get("relpath")
    expected_sha256 = receipt.get("sha256")
    expected_rows = receipt.get("rows")
    if (
        not isinstance(relpath, str)
        or not relpath
        or "\\" in relpath
        or relpath.startswith("/")
        or ".." in relpath.split("/")
        or not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or not isinstance(expected_rows, int)
        or isinstance(expected_rows, bool)
        or expected_rows <= 0
    ):
        raise EsbReferenceError("ESB reference-layer receipt is malformed")
    data_root = Path(root).resolve()
    resolved = (data_root / relpath).resolve()
    try:
        resolved.relative_to(data_root)
    except ValueError as error:
        raise EsbReferenceError(
            f"ESB reference layer {relpath!r} escapes the controlled data root"
        ) from error
    try:
        payload = resolved.read_bytes()
    except OSError as error:
        raise EsbReferenceError(f"cannot read ESB reference layer {resolved}: {error}") from error
    measured = hashlib.sha256(payload).hexdigest()
    if measured != expected_sha256:
        raise EsbReferenceError(
            f"ESB reference layer identity drift: the receipt pins {expected_sha256[:12]}..., "
            f"{resolved} now hashes to {measured[:12]}...; scoring against unverified "
            "reference bytes is refused"
        )
    references: dict[str, str] = {}
    for number, line in enumerate(payload.decode("utf-8").split("\n"), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise EsbReferenceError(
                f"ESB reference layer line {number} malformed: {error}"
            ) from error
        if not isinstance(row, Mapping) or set(row) != {"sample_id", "sentence"}:
            raise EsbReferenceError(
                f"ESB reference layer line {number} must carry exactly sample_id/sentence"
            )
        sample_id = row["sample_id"]
        sentence = row["sentence"]
        if not isinstance(sample_id, str) or not sample_id or sample_id in references:
            raise EsbReferenceError(
                f"ESB reference layer sample ids must be non-empty and unique "
                f"(line {number})"
            )
        if not isinstance(sentence, str) or not sentence.strip():
            raise EsbReferenceError(f"ESB reference {sample_id!r} is empty")
        references[sample_id] = sentence
    if len(references) != expected_rows:
        raise EsbReferenceError(
            f"ESB reference layer holds {len(references)} rows, the receipt pins {expected_rows}"
        )
    return references


def _outputs_rows(outputs_path: Path) -> list[Mapping[str, object]]:
    try:
        text = Path(outputs_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise EsbReferenceError(f"cannot read outputs {outputs_path}: {error}") from error
    # Split on the record separator only, exactly as ``core.scorers`` does:
    # ``json.dumps(ensure_ascii=False)`` leaves U+2028/U+2029 raw inside string
    # values and ``str.splitlines()`` would cut a valid row in two.
    lines = [line for line in text.split("\n") if line != ""]
    if not lines:
        raise EsbReferenceError(f"outputs file {outputs_path} is empty")
    rows: list[Mapping[str, object]] = []
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise EsbReferenceError(f"outputs line {number} malformed: {error}") from error
        if not isinstance(row, Mapping):
            raise EsbReferenceError(f"outputs line {number} is not an object")
        rows.append(row)
    return rows


def published_segment_key(sample_id: str) -> str:
    """The published ``<call>-<segment>`` key a derived-media id scores against.

    A probe MEDIA variant re-encodes the SAME published segment and must never
    share an identifier with its source population -- section 1.4 of
    ``docs/readiness/2026-09-06-e22-dev-boundary-exact-v1-preregistration.md``
    fixes the convention as ``<call>-<segment>@<variant>``. The published key is
    recovered by splitting on ``@``, which is what keeps the reference lookup,
    the neighbour lookup and the paired join against a sealed arm exact.

    An id without a suffix is returned unchanged, so every population that
    existed before the convention is byte-for-byte unaffected.

    This is the Earnings-22 NAME for the rule; the rule itself lives once, in
    ``data.variant_ids.published_sample_key``, so the Audio2Tool and SLURP
    gold rails (2026-09-07) share this exact behaviour rather than a second
    spelling of it.
    """

    return published_sample_key(sample_id)


def _reference_for(
    row: Mapping[str, object], references: Mapping[str, str], number: int
) -> str:
    carrier = row.get("carrier_lock_key")
    if carrier != ESB_CARRIER_LOCK_KEY:
        raise EsbReferenceError(
            f"outputs line {number} names carrier {carrier!r}; the ESB scorers only ever "
            f"score {ESB_CARRIER_LOCK_KEY!r}"
        )
    raw_id = row.get("sample_id")
    sample_id = published_segment_key(raw_id) if isinstance(raw_id, str) else raw_id
    if not isinstance(sample_id, str) or sample_id not in references:
        raise EsbReferenceError(
            f"outputs line {number} names sample {raw_id!r}, which the hash-pinned ESB "
            "reference layer does not contain; a sample outside the pinned reference "
            "closure can never be scored against"
        )
    hypothesis = row.get("text")
    if not isinstance(hypothesis, str):
        raise EsbReferenceError(f"outputs line {number} carries no hypothesis text")
    return references[sample_id]


def score_esb_outputs(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, object]:
    """``saea-scoring-v1`` WER over the ESB utterances.

    The exact twin of ``core.scorers.score_asr_outputs``: the frozen
    ``scoring.normalize.tokens_v1`` on both sides, then ``scoring.wer.align``.
    ``lock`` is accepted for the uniform ``scorer(outputs_path, lock, root)``
    signature and is unused -- this reference layer is resolved from its own
    hash-pinned receipt, never through the umbrella lock.

    Reports BOTH aggregations: ``mean_wer`` (the macro average
    ``score_asr_outputs`` reports) and ``corpus_wer`` (total errors over total
    reference words), because the published Earnings22 row is a corpus number
    while this study's own frozen convention is the macro one.
    """

    references = load_esb_references(root, repo_root=repo_root)
    rows = _outputs_rows(outputs_path)
    per_sample: list[dict[str, object]] = []
    total_substitutions = total_deletions = total_insertions = total_ref_words = 0
    for number, row in enumerate(rows, start=1):
        reference = _reference_for(row, references, number)
        result = align(tokens_v1(reference), tokens_v1(str(row["text"])))
        total_substitutions += result.substitutions
        total_deletions += result.deletions
        total_insertions += result.insertions
        total_ref_words += result.reference_length
        per_sample.append(
            {
                "sample_id": row["sample_id"],
                "wer": result.wer,
                "hits": result.hits,
                "substitutions": result.substitutions,
                "deletions": result.deletions,
                "insertions": result.insertions,
                "ref_hit_mask": list(result.ref_hit_mask),
                "normalizer": "saea-scoring-v1",
            }
        )
    total_errors = total_substitutions + total_deletions + total_insertions
    return {
        "per_sample": per_sample,
        "aggregate": {
            "mean_wer": sum(entry["wer"] for entry in per_sample) / len(per_sample),
            "corpus_wer": (total_errors / total_ref_words) if total_ref_words else 0.0,
            "substitutions": total_substitutions,
            "deletions": total_deletions,
            "insertions": total_insertions,
            "reference_words": total_ref_words,
            "samples": len(per_sample),
            "scorer_version": ESB_WER_SCORER_VERSION,
            "normalizer": "saea-scoring-v1",
            "reference_layer": "e22-esb hash-pinned derived layers (test + dev10)",
        },
    }


def score_esb_outputs_whisper(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, object]:
    """Whisper-normalized WER over the ESB utterances -- the PAPER-FACING
    number for this carrier.

    The exact twin of ``core.scorers.score_asr_outputs_whisper``: both sides
    through the vendored Whisper ``EnglishTextNormalizer``
    (``reproduction.asr_wer_whisper.normalize_whisper_english``), whitespace
    tokenization (``str.split()``, NOT ``tokens_v1``), then
    ``scoring.wer.align``; the headline aggregate is CORPUS WER, total S+D+I
    over total reference words, which is the aggregation the published
    Earnings22 rows use. ``merge_compounds`` is NOT applied -- the Open ASR
    Leaderboard applies it and we do not, which works against us.
    """

    references = load_esb_references(root, repo_root=repo_root)
    rows = _outputs_rows(outputs_path)
    per_sample: list[dict[str, object]] = []
    total_substitutions = total_deletions = total_insertions = total_ref_words = 0
    empty_after_normalization = 0
    for number, row in enumerate(rows, start=1):
        reference = _reference_for(row, references, number)
        ref = normalize_whisper_english(reference).split()
        hyp = normalize_whisper_english(str(row["text"])).split()
        if not ref:
            empty_after_normalization += 1
        result = align(ref, hyp)
        total_substitutions += result.substitutions
        total_deletions += result.deletions
        total_insertions += result.insertions
        total_ref_words += result.reference_length
        per_sample.append(
            {
                "sample_id": row["sample_id"],
                "wer": result.wer,
                "hits": result.hits,
                "substitutions": result.substitutions,
                "deletions": result.deletions,
                "insertions": result.insertions,
                "ref_hit_mask": list(result.ref_hit_mask),
                "normalizer": WHISPER_NORMALIZER_NAME,
            }
        )
    total_errors = total_substitutions + total_deletions + total_insertions
    return {
        "per_sample": per_sample,
        "aggregate": {
            "corpus_wer": (total_errors / total_ref_words) if total_ref_words else 0.0,
            "mean_wer": sum(entry["wer"] for entry in per_sample) / len(per_sample),
            "substitutions": total_substitutions,
            "deletions": total_deletions,
            "insertions": total_insertions,
            "reference_words": total_ref_words,
            "samples": len(per_sample),
            "references_empty_after_normalization": empty_after_normalization,
            "scorer_version": WHISPER_WER_SCORER_VERSION,
            "normalizer": WHISPER_NORMALIZER_NAME,
            "merge_compounds": False,
            "reference_layer": "e22-esb hash-pinned derived layers (test + dev10)",
        },
    }


__all__ = [
    "ESB_CARRIER_LOCK_KEY",
    "ESB_DEV10_REFERENCE_RECEIPT_RELPATH",
    "ESB_REFERENCE_RECEIPT_RELPATH",
    "ESB_REFERENCE_RECEIPT_RELPATHS",
    "ESB_REFERENCE_RECEIPT_SCHEMA",
    "ESB_WER_SCORER_VERSION",
    "EsbReferenceError",
    "load_esb_references",
    "score_esb_outputs",
    "score_esb_outputs_whisper",
]
