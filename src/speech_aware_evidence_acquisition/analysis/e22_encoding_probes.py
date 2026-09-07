"""The paired verdict of the three Earnings-22 encoding probe cells (model-free).

Exposure row ``SAEA-E22-MF-ENCODING-PROBES-VERDICT-V1`` (``model-free-check``).

Section 4 of ``docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md``
fixed a three-clause decision rule before any of the three cells was flown, and
each flight receipt says in writing that "the paired contrast against the sealed
comparator, its CI90 and the three-clause decision rule of section 4 are a later
document's". This module is that document's measurement layer, and it does
nothing else: it re-flies nothing, re-scores nothing, post-processes no
hypothesis and opens no test byte.

**A THIN DERIVATION, NOT A SECOND BASE.** ``analysis.e22_usage_cells`` is the
base and every shared measurement is reused from it unmodified -- the roster and
score loaders, the taxonomy scan, the identity gate, the pooled bootstrap
:func:`~...e22_usage_cells.pooled_delta`, the decision rule
:func:`~...e22_usage_cells.decide`, the per-call / weighting / duration tables
and :func:`~...e22_usage_cells.category_mass`. Four things are added here, three
of them because this preregistration asks for them and the fourth because
reproducing the receipts found it:

1. **three cells instead of two**, with the ``@bx1`` / ``@ts2`` / ``@p30``
   variant ids of deviation ``D-ENC-1`` -- which the base's loaders fold back
   onto the published segment key, so the pairing against sealed arm A is per
   published segment;
2. **the boundary-mass contrast**, clause 3's estimand, bootstrapped through the
   same ``resampled_statistic`` draws as the other two because
   :func:`~...e22_usage_cells.boundary_charge` gives it a per-row numerator;
3. **the two pairwise contrasts** the cost question needs -- ``pad-30s`` against
   ``tail-silence-2s`` (is 30 s of silence worth its 4.34x audio tokens?) and
   ``boundary-exact`` against ``tail-silence-2s``;
4. **the entity-inventory basis reconciliation** of
   :data:`FLIGHT_READ_INVENTORY_BASIS`. The three flight receipts do not share
   one basis: arm A and cell 1 reproduce on ``dev10``, cells 2 and 3 on
   ``subset1500``. Every arm is therefore scanned on BOTH, the gate checks each
   receipt against the basis it used, and every contrast is computed on the
   comparator's basis for all four arms.

**The rule is stricter than the usage cells' by one clause and one threshold.**
Clause 1 demands a CI90 upper bound below **-0.2356**, the lower edge of the
same-request null the 2026-09-06 verdict measured on 1,432 cap-inert rows, so an
admitted cell must be disjoint from this runtime's own cross-run noise. Clause 3
demands the boundary block fall by at least 2.0 WER points from arm A's 8.2778.
Both were fixed before any of these numbers existed.

The six ESB TEST calls are unreachable from here for the same reason they are
unreachable from the base: the reference loader is pinned to the dev10 receipt
alone and the segment-table loader to the dev10 extracted table.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (
    agentic_error_rate,
    build_entity_inventory,
)
from speech_aware_evidence_acquisition.analysis.e22_usage_cells import (
    CI_LEVEL,
    DURATION_BUCKETS,
    FROZEN_SCORER,
    N_REPLICATES,
    SEED,
    WHISPER_SCORER,
    UsageCellsError,
    boundary_charge,
    category_mass,
    decide,
    duration_table,
    high_impact_charge,
    identity_gate,
    load_roster,
    load_score_rows,
    per_call_csv,
    per_call_table,
    pooled_charge_points,
    pooled_delta,
    scan,
    verified_cross_check,
    weightings,
)
from speech_aware_evidence_acquisition.analysis.e22_usage_cells import (
    _corpus as _error_shape,
)
from speech_aware_evidence_acquisition.analysis.e22_usage_cells import (
    _run_dir as _attempt_dir,
)
from speech_aware_evidence_acquisition.analysis.paired import paired_contrast

ANALYSIS_VERSION = "saea-e22-encoding-probes-verdict-v1"
EXPOSURE_ROW_ID = "SAEA-E22-MF-ENCODING-PROBES-VERDICT-V1"
PREREGISTRATION = "docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md"

#: Section 4 clause 1. Not "below zero": below the LOWER edge of the same-request
#: null, so an admitted cell's interval is disjoint from this runtime's measured
#: cross-run noise. Fixed on 2026-09-07, before any of these numbers existed.
WER_CI90_UPPER_MAX_POINTS = -0.2356

#: Section 4 clause 3, fixed for a stated reason: no model-usage knob has moved
#: more than 2.2 % of the boundary block, so a mechanism claim on the encoding
#: needs a visible fraction of the block and not a corpus-WER wobble.
BOUNDARY_DROP_POINTS = 2.0

#: The 2026-09-06 verdict's measured null on 1,432 cap-inert rows -- rows whose
#: request differed from arm A's only by an inert integer. It is the reference
#: spread every contrast below sits on top of.
SAME_REQUEST_NULL = {
    "rows": 1432,
    "point_estimate": -0.0844,
    "ci_low": -0.2356,
    "ci_high": 0.0692,
    "rows_emitting_different_bytes": 302,
    "source": "docs/readiness/2026-09-06-e22-dev-usage-cells-v1-verdict.md section 3.2",
}

COMPARATOR = {
    "arm": "A",
    "run_id": "SAEA-E22-DEV-ESB-PROMPT-A-V1",
    "attempt": "attempt-20260905T073641Z-f977d1",
    "label": "the sealed dev arm A, restricted to the 1,500 roster ids; NO new arm A is flown",
}

_CHECKS = "docs/checks/speech-aware-evidence-acquisition"

CELLS: Mapping[str, Mapping[str, str]] = {
    "BX": {
        "run_id": "SAEA-E22-DEV-ESB-BX-V1",
        "attempt": "attempt-20260907T083612Z-20c7c4",
        "cell": "1",
        "variant": "boundary-exact",
        "id_suffix": "@bx1",
        "factor": "the clip boundary: the midpoint-of-overlap re-cut, strictly subtractive",
        "falsifier_relpath": f"{_CHECKS}/2026-09-07-e22-dev-esb-bx-v1/flight-1500/falsifier.json",
        "media_roster_relpath": (
            f"{_CHECKS}/2026-09-07-e22-dev1500-encoding-variants/boundary-exact/"
            "roster/flight-roster-receipt.json"
        ),
    },
    "TAIL2S": {
        "run_id": "SAEA-E22-DEV-ESB-TAIL2S-V1",
        "attempt": "attempt-20260907T090708Z-df36cc",
        "cell": "2",
        "variant": "tail-silence-2s",
        "id_suffix": "@ts2",
        "factor": "the acoustic tail: +2.0 s of digital silence after the last word",
        "falsifier_relpath": (
            f"{_CHECKS}/2026-09-07-e22-dev-esb-tail2s-v1/flight-1500/falsifier.json"
        ),
        "media_roster_relpath": (
            f"{_CHECKS}/2026-09-07-e22-dev1500-encoding-variants/tail-silence-2s/"
            "roster/flight-roster-receipt.json"
        ),
    },
    "PAD30S": {
        "run_id": "SAEA-E22-DEV-ESB-PAD30S-V1",
        "attempt": "attempt-20260907T093441Z-3a2278",
        "cell": "3",
        "variant": "pad-30s",
        "id_suffix": "@p30",
        "factor": "the input length: digital silence appended up to exactly 30.0 s",
        "falsifier_relpath": (
            f"{_CHECKS}/2026-09-07-e22-dev-esb-pad30s-v1/flight-1500/falsifier.json"
        ),
        "media_roster_relpath": (
            f"{_CHECKS}/2026-09-07-e22-dev1500-encoding-variants/pad-30s/"
            "roster/flight-roster-receipt.json"
        ),
    },
}

#: The frozen population's own receipt, hashed on load by
#: :func:`~...e22_usage_cells.load_roster`.
ROSTER_RELPATH = "docs/receipts/rosters/e22-dev-esb-1500-v1.json"

#: Sealed arm A's media cost. Its flight roster predates the audit and carries
#: no token column, so the comparator's audio-token and zero-pad totals come
#: from the committed audit that derived them.
ENCODING_AUDIT_RELPATH = f"{_CHECKS}/2026-09-07-e22-short-clip-encoding-audit/summary.json"
AUDIT_DEV1500_POPULATION = "E22-ESB-DEV1500-UTTERANCES"

#: ``hop_len 160`` at 16 kHz: one mel frame is 10 ms. The audit's own front-end
#: constants, not a number chosen here.
MEL_FRAME_SECONDS = 0.01

#: The pairwise cost questions, signed so the named cell is the RIGHT arm and a
#: negative delta means the named cell is the better one.
PAIRWISE = (
    ("PAD30S", "TAIL2S", "is 30.0 s of appended silence worth its 4.34x audio tokens?"),
    ("BX", "TAIL2S", "does removing the delivered overlap beat moving the encoder's pad away?"),
)

#: Section 4.2's named reporting obligation for cell 1: every re-cut clip under
#: 0.15 s, by name, beside the population that loses audio at all.
SHORT_RECUT_SECONDS = 0.15

BOUNDARY_METRIC = "boundary_block_wer_points"

#: The entity inventory ``analysis.e22_error_taxonomy.classify_span`` reads is
#: built per call from that call's reference sentences, and WHICH sentences are
#: offered changes the classification of a span that contains a call entity --
#: and therefore the agentic rate and, through ``runaway-head``, the boundary
#: block. Two bases exist in this study's sealed receipts and they are NOT the
#: same number, so both are computed for every arm and both are written into
#: the receipt.
INVENTORY_BASES = ("dev10", "subset1500")

#: The basis every contrast is computed on: all 6,038 dev10 reference sentences
#: per call. It is the comparator's own basis -- ``analysis.e22_usage_cells
#: .build_receipts`` has always built the inventory this way, so arm A's sealed
#: 1.9161 % agentic and 8.2778 boundary points are dev10 numbers -- and it is the
#: richer inventory, since the 1,500-row subset offers a quarter of each call's
#: sentences. A paired contrast must put both arms on one basis and this is it.
VERDICT_INVENTORY_BASIS = "dev10"

#: Which basis each arm's OWN published raw numbers were computed on. This is a
#: property of the sealed receipts, discovered by reproducing them: arm A (the
#: 2026-09-06 usage-cells verdict) and cell 1 reproduce to the digit on
#: ``dev10``, cells 2 and 3 reproduce to the digit on ``subset1500`` and on
#: nothing else. The identity gate checks each triple against the basis its own
#: receipt used -- which is what proves this read is over the same sealed
#: tables -- while the contrast uses :data:`VERDICT_INVENTORY_BASIS` for all
#: four arms. Corpus WER is unaffected: it comes from the scorer, not the
#: taxonomy.
FLIGHT_READ_INVENTORY_BASIS = {
    "A": "dev10",
    "BX": "dev10",
    "TAIL2S": "subset1500",
    "PAD30S": "subset1500",
}


class EncodingProbesError(UsageCellsError):
    """An input drifted, an identity anchor failed, or a receipt is missing."""


# ---------------------------------------------------------------------------
# Committed receipts carried forward
# ---------------------------------------------------------------------------


def _committed(repo_root: Path, relpath: str) -> tuple[dict[str, object], str]:
    path = Path(repo_root) / relpath
    payload = path.read_bytes()
    return json.loads(payload.decode("utf-8")), hashlib.sha256(payload).hexdigest()


def falsifier_check(repo_root: Path, cell: Mapping[str, str]) -> dict[str, object]:
    """Section 4.1's ``prompt_tokens`` falsifier, carried forward from the flight.

    The check itself ran on the sealed trace at flight time and is committed;
    this re-reads that committed receipt, re-hashes it, and REFUSES the verdict
    if it does not say ``HOLDS`` on all 1,500 rows. Section 6.2 item 7 puts the
    falsifier before any score is read, so a cell whose front-end model was
    wrong is never interpreted.
    """

    receipt, digest = _committed(repo_root, cell["falsifier_relpath"])
    holds = (
        str(receipt.get("verdict")) == "HOLDS"
        and int(receipt["rows_where_the_falsifier_holds"]) == int(receipt["rows_checked"])
        == int(receipt["rows_expected"])
        and not receipt["disagreements"]
        and int(receipt["measured_prompt_tokens_total"])
        == int(receipt["predicted_prompt_tokens_total"])
    )
    if not holds:
        raise EncodingProbesError(
            f"{cell['falsifier_relpath']} does not report the section 4.1 falsifier holding "
            "on every row; the cell stops and reports rather than being interpreted"
        )
    return {
        "receipt": cell["falsifier_relpath"],
        "receipt_sha256": digest,
        "verdict": receipt["verdict"],
        "rows_checked": receipt["rows_checked"],
        "rows_where_the_falsifier_holds": receipt["rows_where_the_falsifier_holds"],
        "measured_prompt_tokens_total": receipt["measured_prompt_tokens_total"],
        "predicted_prompt_tokens_total": receipt["predicted_prompt_tokens_total"],
        "text_envelope_tokens": receipt["text_envelope_tokens"],
    }


def media_cost(repo_root: Path, relpath: str) -> dict[str, object]:
    """What one CELL's media cost the encoder, from its committed roster receipt.

    Identifiers, durations, sample counts and token counts only: no WAV byte is
    opened, no decoder runs and no sentence is read. Every field is a column the
    variant builder already wrote and hashed.
    """

    receipt, digest = _committed(repo_root, relpath)
    items = receipt["items"]
    pad_frames = [int(item["zero_pad_frames"]) for item in items]
    return {
        "receipt": relpath,
        "receipt_sha256": digest,
        "rows": len(items),
        "audio_seconds_total": round(sum(float(i["audio_seconds"]) for i in items), 3),
        "audio_tokens_total": sum(int(i["audio_tokens"]) for i in items),
        "audio_seconds_longest_item": receipt.get("audio_seconds_longest_item"),
        "audio_seconds_shortest_item": receipt.get("audio_seconds_shortest_item"),
        "zero_pad_frames_total": sum(pad_frames),
        "zero_pad_seconds_total": round(sum(pad_frames) * MEL_FRAME_SECONDS, 3),
        "rows_carrying_a_zero_pad_block": sum(1 for frames in pad_frames if frames),
    }


def comparator_media_cost(repo_root: Path) -> dict[str, object]:
    """The same cost block for sealed arm A, from the committed encoding audit.

    Arm A's own flight roster predates the audit and carries no token column, so
    the numbers come from the audit receipt that derived them -- the same
    receipt the preregistration quotes -- rather than from a rule re-implemented
    here. The audit's ``extra_audio_tokens_total`` is carried through as well,
    because it is the quantity the three cells exist to move and it has no
    counterpart on a variant roster.
    """

    receipt, digest = _committed(repo_root, ENCODING_AUDIT_RELPATH)
    block = receipt["populations"][AUDIT_DEV1500_POPULATION]
    return {
        "receipt": ENCODING_AUDIT_RELPATH,
        "receipt_sha256": digest,
        "rows": block["clips"],
        "audio_seconds_total": round(float(block["audio_seconds_total"]), 3),
        "audio_tokens_total": int(block["llamacpp_audio_tokens_total"]),
        "published_path_audio_tokens_total": int(block["hf_audio_tokens_total"]),
        "padding_derived_audio_tokens_total": int(block["extra_audio_tokens_total"]),
        "zero_pad_frames_total": int(block["zero_pad_frames_total"]),
        "zero_pad_seconds_total": round(float(block["zero_pad_seconds_total"]), 3),
        "rows_carrying_a_zero_pad_block": int(block["clips_with_zero_pad"]),
    }


def short_recut_clips(repo_root: Path, relpath: str) -> dict[str, object]:
    """Section 4.2's cell-1 obligation: the shortest re-cut clips, by name.

    Every clip under :data:`SHORT_RECUT_SECONDS` is named, beside the count,
    mean and maximum of the clips that lose any audio at all -- so the re-cut's
    worst case is on the record whatever the pooled number says.
    """

    receipt, digest = _committed(repo_root, relpath)
    items = receipt["items"]
    shortest = sorted(
        (
            {
                "sample_id": str(item["sample_id"]),
                "audio_seconds": float(item["audio_seconds"]),
                "source_audio_seconds": float(item["source_audio_seconds"]),
            }
            for item in items
            if float(item["audio_seconds"]) < SHORT_RECUT_SECONDS
        ),
        key=lambda row: (row["audio_seconds"], row["sample_id"]),
    )
    removed = [
        float(item["source_audio_seconds"]) - float(item["audio_seconds"])
        for item in items
        if int(item["samples_removed"]) > 0
    ]
    return {
        "receipt": relpath,
        "receipt_sha256": digest,
        "threshold_seconds": SHORT_RECUT_SECONDS,
        "clips_under_threshold": shortest,
        "clips_that_lose_audio": len(removed),
        "mean_seconds_removed": round(sum(removed) / len(removed), 6) if removed else 0.0,
        "max_seconds_removed": round(max(removed), 6) if removed else 0.0,
    }


def entity_inventories(
    references: Mapping[str, str],
    segments: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
) -> dict[str, Mapping[str, frozenset[str]]]:
    """Both entity inventories named in :data:`INVENTORY_BASES`, per call.

    ``dev10`` offers every dev10 reference sentence of a call;
    ``subset1500`` offers only the sentences of the drawn 1,500. Both go
    through ``analysis.e22_error_taxonomy.build_entity_inventory`` unchanged --
    the difference is the corpus handed to it, not the rule.
    """

    dev10: dict[str, list[str]] = {}
    for sample_id, sentence in references.items():
        dev10.setdefault(str(segments[sample_id]["source_id"]), []).append(sentence)
    subset: dict[str, list[str]] = {}
    for sample_id in sample_ids:
        subset.setdefault(str(segments[sample_id]["source_id"]), []).append(
            references[sample_id]
        )
    return {
        "dev10": build_entity_inventory(dev10),
        "subset1500": build_entity_inventory(subset),
    }


# ---------------------------------------------------------------------------
# The boundary block: the estimand clause 3 decides on
# ---------------------------------------------------------------------------


def boundary_asymmetry(arms: Mapping[str, Mapping[str, object]]) -> list[dict[str, object]]:
    """Head against tail, per arm -- the one table the mechanism reading turns on.

    Every number is read out of the arm's own :func:`category_mass` block, which
    ``analysis.e22_error_taxonomy`` produced at its committed version. The two
    ends are reported separately because a variant that acts on the acoustic
    tail can only move the tail, and a variant that acts on the delivered
    overlap should move both.
    """

    table = []
    for arm, block in arms.items():
        boundary = block["category_mass"]["boundary"]
        containment = boundary["containment"]
        table.append(
            {
                "arm": arm,
                "runaway_head_mass": boundary["runaway_head_mass"],
                "runaway_tail_mass": boundary["runaway_tail_mass"],
                "segmentation_artifact_mass": boundary["segmentation_artifact_mass"],
                "boundary_total_error_mass": boundary["total_error_mass"],
                "boundary_wer_points": boundary["wer_points"],
                "head_insertion_spans": containment["head"]["insertion_spans"],
                "head_inserted_words": containment["head"]["inserted_words"],
                "head_spans_contained_at_0.6": containment["head"]["spans_by_containment"][
                    "contains_0.6_or_more"
                ],
                "tail_insertion_spans": containment["tail"]["insertion_spans"],
                "tail_inserted_words": containment["tail"]["inserted_words"],
                "tail_spans_contained_at_0.6": containment["tail"]["spans_by_containment"][
                    "contains_0.6_or_more"
                ],
            }
        )
    return table


def _charge_by_group(
    arms: Mapping[str, Mapping[str, object]],
    groups: Sequence[tuple[str, Sequence[str]]],
    charge_key: str,
) -> list[dict[str, object]]:
    """One per-row charge, pooled over each group, per arm, with each cell's delta."""

    table = []
    for label, subset in groups:
        row: dict[str, object] = {"group": label, "rows": len(subset)}
        for arm, block in arms.items():
            row[f"{arm}_wer_points"] = pooled_charge_points(
                block[charge_key], block["reference_words_of"], subset
            )
        for arm in arms:
            if arm != "A":
                row[f"{arm}_delta"] = round(
                    float(row[f"{arm}_wer_points"]) - float(row["A_wer_points"]), 4
                )
        table.append(row)
    return table


def boundary_by_call(
    arms: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    call_of: Mapping[str, str],
) -> list[dict[str, object]]:
    """Clause 3's block, per call, so ten strata can disagree visibly."""

    groups = [
        (call, [s for s in sample_ids if call_of[s] == call])
        for call in sorted(set(call_of.values()))
    ]
    return _charge_by_group(arms, groups, "boundary")


def boundary_by_duration(
    arms: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    seconds_of: Mapping[str, float],
) -> list[dict[str, object]]:
    """Clause 3's block by utterance duration -- the audit's own predicted slice."""

    groups = []
    for low, high in DURATION_BUCKETS:
        subset = [s for s in sample_ids if low <= seconds_of[s] < high]
        if subset:
            label = f"[{low:g}, {high:g})" if high < 1e8 else f"[{low:g}, inf)"
            groups.append((label, subset))
    return _charge_by_group(arms, groups, "boundary")


# ---------------------------------------------------------------------------
# Contrasts
# ---------------------------------------------------------------------------


def _errors(arms: Mapping[str, Mapping[str, object]]) -> dict[str, dict[str, float]]:
    return {
        arm: {
            sample_id: row["substitutions"] + row["deletions"] + row["insertions"]
            for sample_id, row in block["scores"][WHISPER_SCORER].items()
        }
        for arm, block in arms.items()
    }


def _reference_words(arms: Mapping[str, Mapping[str, object]]) -> dict[str, dict[str, float]]:
    return {
        arm: {
            sample_id: row["hits"] + row["substitutions"] + row["deletions"]
            for sample_id, row in block["scores"][WHISPER_SCORER].items()
        }
        for arm, block in arms.items()
    }


def contrast(
    arms: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    call_of: Mapping[str, str],
    *,
    left: str,
    right: str,
    estimands: Sequence[str] = ("wer", "agentic", "boundary"),
) -> dict[str, object]:
    """``right - arm`` on each named estimand, plus per-row saves / harms / ties.

    Every estimand is a pooled ratio and every one goes through the base's
    :func:`~...e22_usage_cells.pooled_delta`, so all three get the identical
    stratified draws (seed 20260903, 10,000 replicates) and the call-clustered
    interval beside them. Values are precomputed per row before the bootstrap
    because the statistic is evaluated 10,000 times per interval.
    """

    errors = _errors(arms)
    reference = _reference_words(arms)
    block: dict[str, object] = {}
    if "wer" in estimands:
        block["corpus_wer_delta_points"] = pooled_delta(
            sample_ids,
            lambda arm, s: errors[arm][s],
            lambda arm, s: reference[arm][s],
            left=left,
            right=right,
            call_of=call_of,
        )
    words = {arm: arms[arm]["reference_words_of"] for arm in arms}
    for name, key, charge_key in (
        ("agentic", "agentic_delta_points", "charge"),
        ("boundary", "boundary_delta_points", "boundary"),
    ):
        if name not in estimands:
            continue
        charge = {arm: arms[arm][charge_key] for arm in arms}
        block[key] = pooled_delta(
            sample_ids,
            lambda arm, s, charge=charge: float(charge[arm].get(s, 0)),
            lambda arm, s: float(words[arm][s]),
            left=left,
            right=right,
            call_of=call_of,
        )
    per_row = paired_contrast(
        {s: {"neg_wer": -arms[left]["scores"][WHISPER_SCORER][s]["wer"]} for s in sample_ids},
        {s: {"neg_wer": -arms[right]["scores"][WHISPER_SCORER][s]["wer"]} for s in sample_ids},
        metrics=["neg_wer"],
        sample_ids=sample_ids,
        strata_of=lambda s: call_of[s],
        seed=SEED,
        n_replicates=N_REPLICATES,
        ci_level=CI_LEVEL,
    )["neg_wer"]
    block["per_row_wer"] = {
        "saves": per_row.saves,
        "harms": per_row.harms,
        "ties": per_row.ties,
        "sign_test_p": round(per_row.sign_test_p, 6),
        "mean_per_utterance_wer_delta_points": round(-100.0 * per_row.delta, 4),
    }
    block["signed_as"] = f"{right} minus {left}; negative means {right} is the better arm"
    return block


# ---------------------------------------------------------------------------
# The receipt
# ---------------------------------------------------------------------------


def build_receipts(
    *,
    repo_root: Path,
    root: Path,
    references: Mapping[str, str],
    segments: Mapping[str, Mapping[str, object]],
    anchors: Mapping[str, Mapping[str, float]],
    outbound_attempts: int,
    outbound_targets: Sequence[str],
) -> tuple[dict[str, object], str]:
    """``(summary, per-call CSV)``. Nothing is contrasted until the gate passes.

    Order is the preregistration's own: the section 4.1 falsifier for every
    cell FIRST (section 6.2 item 7 puts it before any score is read), then the
    identity gate on the four raw triples, and only then a single contrast.
    """

    repo_root = Path(repo_root)
    falsifiers = {arm: falsifier_check(repo_root, cell) for arm, cell in CELLS.items()}

    roster = load_roster(repo_root)
    sample_ids: tuple[str, ...] = roster["sample_ids"]  # type: ignore[assignment]
    call_of: Mapping[str, str] = roster["call_of"]  # type: ignore[assignment]
    inventories = entity_inventories(references, segments, sample_ids)

    arms: dict[str, dict[str, object]] = {}
    measured: dict[str, dict[str, float]] = {}
    bases: dict[str, dict[str, object]] = {}
    for arm, source in [("A", COMPARATOR)] + [(k, v) for k, v in CELLS.items()]:
        scores = load_score_rows(root, source, sample_ids)
        by_basis = {
            basis: scan(
                root,
                source,
                references=references,
                segments=segments,
                inventory=inventories[basis],
                sample_ids=sample_ids,
            )
            for basis in INVENTORY_BASES
        }
        bases[arm] = {
            basis: {
                "agentic_error_rate_percent": agentic_error_rate(
                    scored, totals.reference_length
                )["agentic_error_rate_percent"],
                BOUNDARY_METRIC: category_mass(scored, contexts, totals.reference_length)[
                    "boundary"
                ]["wer_points"],
            }
            for basis, (totals, scored, contexts) in by_basis.items()
        }
        totals, scored, contexts = by_basis[VERDICT_INVENTORY_BASIS]
        rate = agentic_error_rate(scored, totals.reference_length)
        mass = category_mass(scored, contexts, totals.reference_length)
        arms[arm] = {
            "run_id": source["run_id"],
            "attempt": source["attempt"],
            "outputs_sha256": hashlib.sha256(
                (_attempt_dir(root, source) / f"{source['run_id']}.outputs.jsonl").read_bytes()
            ).hexdigest(),
            "scores": scores,
            "charge": high_impact_charge(scored),
            "boundary": boundary_charge(scored),
            "reference_words_of": {s: len(contexts[s].ref_tokens) for s in sample_ids},
            "agentic": rate,
            "taxonomy_totals": {
                "substitutions": totals.substitutions,
                "deletions": totals.deletions,
                "insertions": totals.insertions,
                "reference_words": totals.reference_length,
                "corpus_wer_percent": round(100.0 * totals.errors / totals.reference_length, 4),
            },
            "category_mass": mass,
            "verified_cross_check": verified_cross_check(
                root, source, scores, directories=("score-batch-per-sample", "score-batch")
            ),
            "error_shape_whisper": _error_shape(scores[WHISPER_SCORER], sample_ids),
            "error_shape_saea_v1": _error_shape(scores[FROZEN_SCORER], sample_ids),
            "media": comparator_media_cost(repo_root)
            if arm == "A"
            else media_cost(repo_root, str(source["media_roster_relpath"])),
        }
        flight_basis = bases[arm][FLIGHT_READ_INVENTORY_BASIS[arm]]
        measured[arm] = {
            "corpus_wer_percent": _error_shape(scores[WHISPER_SCORER], sample_ids)[
                "corpus_wer_percent"
            ],
            "agentic_error_rate_percent": float(flight_basis["agentic_error_rate_percent"]),
            BOUNDARY_METRIC: float(flight_basis[BOUNDARY_METRIC]),
        }

    # The per-row boundary charge must sum to exactly the corpus block the
    # committed taxonomy reports, or clause 3 would be decided on a different
    # quantity from the one the flight receipts published.
    for arm, block in arms.items():
        pooled = pooled_charge_points(
            block["boundary"], block["reference_words_of"], sample_ids
        )
        published = float(block["category_mass"]["boundary"]["wer_points"])
        if abs(pooled - published) > 5e-4:
            raise EncodingProbesError(
                f"arm {arm}: the per-row boundary charge pools to {pooled} WER points but the "
                f"category table reports {published}; clause 3's estimand is not the block"
            )

    gate = identity_gate(measured, anchors)

    contrasts: dict[str, object] = {}
    for arm, cell in CELLS.items():
        block = contrast(arms, sample_ids, call_of, left="A", right=arm)
        block["cell"] = cell["cell"]
        block["variant"] = cell["variant"]
        block["factor"] = cell["factor"]
        block["falsifier"] = falsifiers[arm]
        block["decision"] = decide(
            block["corpus_wer_delta_points"],
            block["agentic_delta_points"],
            wer_ci_upper_max=WER_CI90_UPPER_MAX_POINTS,
            boundary=block["boundary_delta_points"],
            boundary_drop_points=BOUNDARY_DROP_POINTS,
        )
        block["audio_token_cost_ratio_vs_comparator"] = round(
            float(arms[arm]["media"]["audio_tokens_total"])
            / float(arms["A"]["media"]["audio_tokens_total"]),
            4,
        )
        contrasts[arm] = block

    pairwise: dict[str, object] = {}
    for right, left, question in PAIRWISE:
        block = contrast(
            arms,
            sample_ids,
            call_of,
            left=left,
            right=right,
            estimands=("wer", "boundary"),
        )
        block["question"] = question
        block["audio_token_ratio"] = round(
            float(arms[right]["media"]["audio_tokens_total"])
            / float(arms[left]["media"]["audio_tokens_total"]),
            4,
        )
        block["audio_seconds_ratio"] = round(
            float(arms[right]["media"]["audio_seconds_total"])
            / float(arms[left]["media"]["audio_seconds_total"]),
            4,
        )
        pairwise[f"{right}_minus_{left}"] = block

    per_call = per_call_table(arms, sample_ids, call_of)
    admitted = sorted(arm for arm, block in contrasts.items() if block["decision"]["admitted"])
    summary = {
        "schema": ANALYSIS_VERSION,
        "exposure_row": EXPOSURE_ROW_ID,
        "preregistration": PREREGISTRATION,
        "population": {
            "roster_id": roster["roster_id"],
            "split_identity_hash": roster["split_identity_hash"],
            "roster_receipt": ROSTER_RELPATH,
            "roster_receipt_sha256": roster["receipt_sha256"],
            "rows": len(sample_ids),
            "strata": len(set(call_of.values())),
            "pairing_key": (
                "the published ESB segment id, recovered from each cell's variant id by "
                "splitting on '@' (deviation D-ENC-1)"
            ),
        },
        "comparator": dict(COMPARATOR),
        "same_request_null": dict(SAME_REQUEST_NULL),
        "identity_gate": gate,
        "entity_inventory_basis": {
            "verdict_basis": VERDICT_INVENTORY_BASIS,
            "flight_read_basis_per_arm": dict(FLIGHT_READ_INVENTORY_BASIS),
            "per_arm_both_bases": bases,
            "what_it_changes": (
                "the per-call entity inventory feeds classify_span, so it moves the agentic "
                "error rate and, through the runaway-head rule, the boundary block. Corpus WER "
                "comes from the scorer and is identical on both bases"
            ),
            "finding": (
                "THE THREE FLIGHT RECEIPTS DO NOT SHARE ONE BASIS. Arm A (the 2026-09-06 "
                "usage-cells verdict) and cell 1 reproduce to the digit on dev10; cells 2 and 3 "
                "reproduce to the digit on subset1500 and on nothing else. This was found by "
                "reproducing each receipt, not chosen: each triple reproduces on exactly one "
                "basis. The identity gate therefore checks every arm against the basis its own "
                "receipt used -- which is what proves this read is over the same sealed tables "
                "-- and every contrast is then computed on the comparator's basis for all four "
                "arms, because a paired contrast whose arms use different inventories is not a "
                "paired contrast"
            ),
        },
        "contrasts": contrasts,
        "pairwise_contrasts": pairwise,
        "per_call_table": per_call,
        "weightings": weightings(arms, per_call, sample_ids),
        "duration_decomposition": duration_table(arms, sample_ids, roster["seconds_of"]),
        "boundary_asymmetry": boundary_asymmetry(arms),
        "boundary_by_call": boundary_by_call(arms, sample_ids, call_of),
        "boundary_by_duration": boundary_by_duration(arms, sample_ids, roster["seconds_of"]),
        "cell_1_short_recut_clips": short_recut_clips(
            repo_root, CELLS["BX"]["media_roster_relpath"]
        ),
        "arms": {
            arm: {
                key: block[key]
                for key in (
                    "run_id",
                    "attempt",
                    "outputs_sha256",
                    "agentic",
                    "taxonomy_totals",
                    "category_mass",
                    "verified_cross_check",
                    "error_shape_whisper",
                    "error_shape_saea_v1",
                    "media",
                )
            }
            for arm, block in arms.items()
        },
        "closing_rule": {
            "rule": (
                "section 8: if NO cell moves the boundary category mass by at least "
                f"{BOUNDARY_DROP_POINTS} WER points, Earnings-22 short-form is DROPPED from "
                "this work's scope"
            ),
            "cells_clearing_clause_3": sorted(
                arm
                for arm, block in contrasts.items()
                if block["decision"]["clause_3_boundary_block_falls_by_at_least_points"]
            ),
            "cells_admitted": admitted,
            "fires": not admitted
            and not any(
                block["decision"]["clause_3_boundary_block_falls_by_at_least_points"]
                for block in contrasts.values()
            ),
        },
        "boundary": {
            "test_split_read": False,
            "model_contacts": 0,
            "gpu_hours": 0,
            "outbound_connection_attempts": outbound_attempts,
            "outbound_targets": list(outbound_targets),
            "statement": (
                "sealed score files, sealed outputs, the hash-pinned dev10 reference layer and "
                "segment table, the committed roster receipts and the committed per-cell "
                "falsifier receipts. Nothing is re-flown, re-scored or post-processed, and no "
                "media byte is opened."
            ),
        },
    }
    return summary, per_call_csv(per_call)


__all__ = [
    "ANALYSIS_VERSION",
    "BOUNDARY_DROP_POINTS",
    "BOUNDARY_METRIC",
    "CELLS",
    "FLIGHT_READ_INVENTORY_BASIS",
    "INVENTORY_BASES",
    "VERDICT_INVENTORY_BASIS",
    "COMPARATOR",
    "EXPOSURE_ROW_ID",
    "PAIRWISE",
    "SAME_REQUEST_NULL",
    "SHORT_RECUT_SECONDS",
    "WER_CI90_UPPER_MAX_POINTS",
    "EncodingProbesError",
    "boundary_asymmetry",
    "boundary_by_call",
    "boundary_by_duration",
    "build_receipts",
    "comparator_media_cost",
    "contrast",
    "entity_inventories",
    "falsifier_check",
    "media_cost",
    "short_recut_clips",
]
