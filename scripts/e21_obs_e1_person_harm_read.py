#!/usr/bin/env python3
"""The model-free decomposition of OBS-E1's PERSON harm, one reference word at a time.

Exposure row `SAEA-E21-MF-OBS-E1-HARM-DECOMPOSITION-V1` (`model-free-check`),
registered and committed before the first sealed artifact was opened. Zero
frozen-core, GPU, server, tokenizer, tool, embedder, network, audio-decode and
paid-API contacts; no Earnings-22 surface is named, loaded or scored.

What it reads
-------------
* the two sealed `outputs.jsonl` / `trace.jsonl` pairs already written by
  `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1` (attempt `attempt-20260908T150858Z-c597a8`,
  whose artifacts sit at the RUN ROOT) and its comparator
  `SAEA-E21-FULL44-DIRECT-BASELINE-V2`;
* the committed OBS-E1 unit plan v2, `docs/receipts/obs/e21-speaker-turn-units-v2.json`;
* the Earnings-21 reference and `wer_tags` layers, reached ONLY through
  `data.references` and `reproduction.conec_entity_scoring`, never opened by hand.

Two stages, so no question is paid for twice
---------------------------------------------
`--stage rows` re-runs both arms' alignments once and writes one row per
(PERSON reference word, entity ID) pair to `$SPEECHRL_DATA_DIR/runs/
SAEA-E21-MF-OBS-E1-HARM-DECOMPOSITION-V1/person-rows.json` -- a per-request
derivative of sealed model outputs, so it lives where those live and never
enters Git. `--stage tables` reads that file back and renders the receipt.
The rows stage proves itself first: pooling its own rows must reproduce the
sealed PERSON entity WER of BOTH arms to five decimals, and it refuses to write
if it does not.

usage:
  e21_obs_e1_person_harm_read.py --stage rows
  e21_obs_e1_person_harm_read.py --stage tables --out-dir <receipt dir>
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

REPO_ROOT = Path(
    os.environ.get("SAEA_REPO_ROOT", "")
    or "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
for _candidate in (Path(__file__).resolve().parent, REPO_ROOT / "scripts"):
    if (_candidate / "build_e21_tail2s_verdict.py").is_file():
        sys.path.insert(0, str(_candidate))
        break

import build_e21_tail2s_verdict as t2  # noqa: E402

from speech_aware_evidence_acquisition.analysis import e21_person_harm as ph  # noqa: E402
from speech_aware_evidence_acquisition.analysis import e21_window_pairing as wp  # noqa: E402
from speech_aware_evidence_acquisition.reproduction import (  # noqa: E402
    conec_entity_scoring as conec,
)
from speech_aware_evidence_acquisition.reproduction.asr_wer_whisper import (  # noqa: E402
    normalize_whisper_english,
)

DATA_ROOT = Path(
    os.environ.get(
        "SPEECHRL_DATA_DIR",
        (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"),
    )
)

CELL_RUN = "SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1"
CELL_ATTEMPT = "attempt-20260908T150858Z-c597a8"
CELL_DIR = DATA_ROOT / "runs" / CELL_RUN  # this flight wrote at the run ROOT
COMPARATOR_DIR = DATA_ROOT / "runs" / t2.COMPARATOR_RUN / t2.COMPARATOR_ATTEMPT
PLAN = REPO_ROOT / "docs/receipts/obs/e21-speaker-turn-units-v2.json"
ROWS_PATH = DATA_ROOT / "runs" / ph.EXPOSURE_ROW / "person-rows.json"

ENTITY_CLASS = ph.DEFAULT_ENTITY_CLASS

#: The two arms' sealed PERSON buckets, quoted from the OBS-E1 verdict's own
#: section 3 table. The rows stage refuses to write unless it re-derives both.
SEALED_PERSON_WER = {
    "comparator": 22.48886,
    "cell": 24.58005,
}
SEALED_PERSON_REFERENCE_WORDS = 2917

#: `SAEA-E21-FULL44-TAIL2S-V1`, section 3.1 of its verdict: the SAME comparator,
#: the SAME 1,593 fixed 90-second windows, ONE 2.0-second silence tail per
#: window and nothing else moved. This is the only measured point in the family
#: where the tail count changes and the boundary set does NOT.
TAIL_CELL = {
    "run_id": "SAEA-E21-FULL44-TAIL2S-V1",
    "tails": 1593,
    "transport_boundaries_added": 0,
    "person_improvement_points": -0.6856,
    "person_ci90": [-1.3467, -0.1314],
    "person_wer_percent": 23.1745,
}


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def outputs_text(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            out[str(entry["sample_id"])] = str(entry["text"])
    return out


def arm_spans(trace_path: Path, outputs_path: Path):
    """Every call's transport spans, proven byte for byte against the sealed
    hypothesis before anything is measured."""

    text = outputs_text(outputs_path)
    spans = wp.stitched_windows_from_trace(trace_path)
    spans, _hit = t2._quarantine_saturated(spans, trace_path)
    wp.assert_stitch_reproduces_outputs(spans, text)
    return spans, text


def plan_units() -> dict[str, list[dict]]:
    return {
        str(block["sample_id"]): list(block["units"])
        for block in load_json(PLAN)["calls"]
    }


def arm_decomposition(spans, hypothesis_text: str, whole_words, operations):
    """One arm, one call: the span reference blocks and the per-word span index."""

    boundaries = wp.hypothesis_window_boundaries(spans, normalize_whisper_english)
    hypothesis_words = conec.hypothesis_whisper_words(hypothesis_text)
    charged = wp.charge_operations_to_windows(operations, boundaries, len(hypothesis_words))
    ranges = ph.span_reference_ranges(charged, len(whole_words))
    index_of = ph.span_index_of_reference(ranges, len(whole_words))
    return ranges, index_of


def build_rows() -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path
    from speech_aware_evidence_acquisition.data.references import (
        reference_entity_mentions,
        reference_tokens,
    )

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    comparator_spans, comparator_text = arm_spans(
        COMPARATOR_DIR / f"{t2.COMPARATOR_RUN}.trace.jsonl",
        COMPARATOR_DIR / f"{t2.COMPARATOR_RUN}.outputs.jsonl",
    )
    cell_spans, cell_text = arm_spans(
        CELL_DIR / f"{CELL_RUN}.trace.jsonl",
        CELL_DIR / f"{CELL_RUN}.outputs.jsonl",
    )
    if set(comparator_spans) != set(cell_spans):
        raise SystemExit("the two arms do not cover the same calls")

    units_by_call = plan_units()
    rows: list[dict] = []
    mentions_out: list[dict] = []
    per_call: list[dict] = []

    for sample_id in sorted(comparator_spans):
        raw_tokens = reference_tokens(lock, DATA_ROOT, t2.CARRIER, sample_id)
        mentions = reference_entity_mentions(lock, DATA_ROOT, t2.CARRIER, sample_id)
        owners_by_index: list[list[str]] = [[] for _ in raw_tokens]
        entity_types: dict[str, str] = {}
        for mention in mentions:
            entity_types[mention.entity_id] = mention.entity_type
            for index in mention.token_indices:
                owners_by_index[index].append(mention.entity_id)
        owners = [tuple(sorted(ids)) for ids in owners_by_index]

        whole_words = conec.whole_string_whisper_words(raw_tokens)
        chunked_words, chunked_owners = conec.run_chunked_whisper_words(raw_tokens, owners)
        transferred = conec.transfer_owners(chunked_words, chunked_owners, whole_words)
        multiplicity = ph.class_multiplicity(transferred, entity_types, ENTITY_CLASS)

        arms: dict[str, dict] = {}
        for name, spans, text in (
            ("comparator", comparator_spans[sample_id], comparator_text[sample_id]),
            ("cell", cell_spans[sample_id], cell_text[sample_id]),
        ):
            hypothesis_words = conec.hypothesis_whisper_words(text)
            operations = conec.aligned_operations(whole_words, hypothesis_words)
            conec.operation_counts(operations, len(whole_words), len(hypothesis_words))
            ranges, index_of = arm_decomposition(spans, text, whole_words, operations)
            arms[name] = {
                "spans": spans,
                "ranges": ranges,
                "index_of": index_of,
                "kinds": ph.operation_kinds_by_reference(operations, len(whole_words)),
            }

        units = units_by_call[sample_id]
        if len(units) != len(cell_spans[sample_id]):
            raise SystemExit(
                f"{sample_id}: plan has {len(units)} units but the trace carries "
                f"{len(cell_spans[sample_id])} spans"
            )
        for unit, span in zip(units, cell_spans[sample_id]):
            for key, value in (
                ("start_seconds", span.start_seconds),
                ("end_seconds", span.end_seconds),
            ):
                if abs(float(unit[key]) - float(value)) > 1e-6:
                    raise SystemExit(
                        f"{sample_id}: plan unit {unit['unit_id']} {key} {unit[key]} != "
                        f"flown span {value}"
                    )
        previous_speaker = [None] + [unit.get("speaker") for unit in units[:-1]]

        # --- per (PERSON word, entity id) rows -------------------------------
        for index, weight in enumerate(multiplicity):
            if weight <= 0:
                continue
            row: dict[str, object] = {
                "sample_id": sample_id,
                "reference_index": index,
                "multiplicity": weight,
            }
            for name in ("comparator", "cell"):
                block = arms[name]
                position = block["index_of"][index]
                span = block["spans"][position]
                reference_range = block["ranges"][position]
                span_words = reference_range[1] - reference_range[0]
                span_seconds = span.end_seconds - span.start_seconds
                rate = ph.seconds_per_reference_word(span_seconds, span_words)
                from_start, from_end, nearest = ph.boundary_distance_words(
                    reference_range, index
                )
                row[f"{name}_kind"] = block["kinds"][index]
                row[f"{name}_span_position"] = position
                row[f"{name}_span_id"] = span.identifier
                row[f"{name}_span_seconds"] = round(span_seconds, 6)
                row[f"{name}_span_reference_words"] = span_words
                row[f"{name}_seconds_per_word"] = round(rate, 6)
                row[f"{name}_from_start_words"] = from_start
                row[f"{name}_from_end_words"] = from_end
                row[f"{name}_nearest_words"] = nearest
                for field, distance in (
                    ("from_start", from_start),
                    ("from_end", from_end),
                    ("nearest", nearest),
                ):
                    seconds = ph.boundary_distance_seconds(distance, rate)
                    row[f"{name}_{field}_seconds"] = round(seconds, 6)
                row[f"{name}_nearest_bin"] = ph.bin_label(
                    ph.boundary_distance_seconds(nearest, rate)
                )
            unit = units[row["cell_span_position"]]
            row.update(
                {
                    "unit_id": str(unit["unit_id"]),
                    "unit_index": int(unit["unit_index"]),
                    "unit_duration_seconds": float(unit["duration_seconds"]),
                    "unit_speaker": unit.get("speaker"),
                    "unit_speaker_share": float(unit["speaker_share"]),
                    "unit_speaker_count": int(unit["speaker_count"]),
                    "unit_start_cut": str(unit["start_cut"]),
                    "unit_end_cut": str(unit["end_cut"]),
                    "unit_ends_on_active_frame": bool(unit["ends_on_active_frame"]),
                    "unit_absorbed_units": len(unit.get("absorbed_units") or []),
                    "unit_flags": list(unit.get("flags") or []),
                    "unit_speaker_changed_from_previous": (
                        previous_speaker[row["cell_span_position"]] is not None
                        and previous_speaker[row["cell_span_position"]] != unit.get("speaker")
                    ),
                    "units_in_call": len(units),
                }
            )
            rows.append(row)

        # --- per PERSON mention, for the "cut through a name" test ------------
        by_entity: dict[str, list[int]] = {}
        for index, owner in enumerate(transferred):
            if not owner:
                continue
            for entity_id in owner:
                if entity_types.get(entity_id) == ENTITY_CLASS:
                    by_entity.setdefault(entity_id, []).append(index)
        for entity_id, positions in sorted(by_entity.items()):
            entry: dict[str, object] = {
                "sample_id": sample_id,
                "entity_id": entity_id,
                "words": len(positions),
            }
            for name in ("comparator", "cell"):
                block = arms[name]
                spans_hit = sorted({block["index_of"][p] for p in positions})
                kinds = [block["kinds"][p] for p in positions]
                entry[f"{name}_spans"] = len(spans_hit)
                entry[f"{name}_split"] = len(spans_hit) > 1
                entry[f"{name}_errors"] = sum(1 for kind in kinds if ph.is_error(kind))
                entry[f"{name}_substitutions"] = sum(
                    1 for kind in kinds if kind == conec.OP_SUBSTITUTION
                )
                entry[f"{name}_deletions"] = sum(
                    1 for kind in kinds if kind == conec.OP_DELETION
                )
            mentions_out.append(entry)

        call_rows = [row for row in rows if row["sample_id"] == sample_id]
        per_call.append(
            {
                "sample_id": sample_id,
                "person_reference_words": sum(int(r["multiplicity"]) for r in call_rows),
                "units": len(units),
                "windows": len(comparator_spans[sample_id]),
                **{
                    f"{name}_{field}": value
                    for name in ("comparator", "cell")
                    for field, value in ph.bucket_counts(call_rows, name).items()
                },
            }
        )

    # --- the identity anchor, before anything is written --------------------
    anchors: list[dict] = []
    for name, expected in SEALED_PERSON_WER.items():
        counts = ph.bucket_counts(rows, name)
        measured = ph.wer_percent(counts)
        anchors.append(
            {
                "arm": name,
                "measured_wer_percent": round(measured, 5),
                "sealed_wer_percent": expected,
                "measured_reference_words": counts["reference_words"],
                "sealed_reference_words": SEALED_PERSON_REFERENCE_WORDS,
                "substitutions": counts["substitutions"],
                "deletions": counts["deletions"],
                "verdict": (
                    "PASS"
                    if abs(measured - expected) <= 5e-5
                    and counts["reference_words"] == SEALED_PERSON_REFERENCE_WORDS
                    else "FAIL"
                ),
            }
        )
    if any(anchor["verdict"] == "FAIL" for anchor in anchors):
        raise SystemExit(
            "the per-word rows do not reproduce the sealed PERSON buckets:\n"
            + json.dumps(anchors, indent=1)
        )

    return {
        "schema": ph.RESULT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": ph.EXPOSURE_ROW,
        "entity_class": ENTITY_CLASS,
        "cell": {"run_id": CELL_RUN, "attempt_id": CELL_ATTEMPT},
        "comparator": {"run_id": t2.COMPARATOR_RUN, "attempt_id": t2.COMPARATOR_ATTEMPT},
        "carrier_lock_key": t2.CARRIER,
        "split_identity_hash": (
            "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
        ),
        "identity_anchor": anchors,
        "position_provenance": (
            "distances in reference WORDS are exact, from each arm's own charged "
            "alignment; distances in SECONDS are DERIVED by the containing span's own "
            "local rate (span seconds / span reference words) because the Earnings-21 "
            "reference layer ships no word timestamps -- an attribution, never a "
            "timestamped alignment"
        ),
        "zero_contact": (
            "no model, GPU, tool, embedding, tokenizer, network, audio-decode or "
            "paid-API contact; references and wer_tags reached only through the "
            "registered scoring path's own loaders"
        ),
        "per_call": per_call,
        "mentions": mentions_out,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Stage 2: the tables. Reads the rows back; opens no sealed artifact.
# ---------------------------------------------------------------------------


def call_rows_for_bootstrap(rows, arm: str) -> dict[str, dict]:
    """`{sample_id: counts}` in the shape `build_e21_tail2s_verdict.bootstrap_delta`
    expects, so every interval in this receipt comes out of the same instrument
    the OBS-E1 verdict itself used (seed 20260903, 10,000 replicates, CI90,
    clustered by call)."""

    out: dict[str, dict] = {}
    for row in rows:
        entry = out.setdefault(
            str(row["sample_id"]),
            {"substitutions": 0, "deletions": 0, "errors": 0, "reference_words": 0},
        )
        weight = int(row["multiplicity"])
        entry["reference_words"] += weight
        kind = str(row[f"{arm}_kind"])
        if kind == conec.OP_SUBSTITUTION:
            entry["substitutions"] += weight
            entry["errors"] += weight
        elif kind == conec.OP_DELETION:
            entry["deletions"] += weight
            entry["errors"] += weight
    return out


def paired_interval(rows, numerator: str) -> dict:
    """CI90 on `comparator - cell` for one numerator, clustered by call, so a
    POSITIVE point estimate means the cell is better."""

    cell = call_rows_for_bootstrap(rows, "cell")
    comparator = call_rows_for_bootstrap(rows, "comparator")
    ids = sorted(set(cell) & set(comparator))
    block = t2.bootstrap_delta(
        cell, comparator, ids, numerator, "reference_words", 100.0, cluster_of=lambda i: i
    )
    return {
        "improvement_point": block["point"],
        "improvement_ci90": [block["ci_low"], block["ci_high"]],
        "clusters": block["n"],
        "comparator_percent": t2.pooled(comparator, ids, numerator, "reference_words", 100.0),
        "cell_percent": t2.pooled(cell, ids, numerator, "reference_words", 100.0),
    }


def excess(rows, arm_left: str = "cell", arm_right: str = "comparator") -> int:
    """How many more entity errors the cell makes than the comparator over the
    SAME reference words -- the quantity every "addressable share" divides."""

    return int(ph.bucket_counts(rows, arm_left)["errors"]) - int(
        ph.bucket_counts(rows, arm_right)["errors"]
    )


def with_excess(table: list[dict], total_excess: int) -> list[dict]:
    for entry in table:
        entry["excess_errors"] = int(entry["cell"]["errors"]) - int(
            entry["comparator"]["errors"]
        )
        entry["excess_share_percent"] = (
            100.0 * entry["excess_errors"] / total_excess if total_excess else 0.0
        )
    return table


def duration_bucket(seconds: float) -> str:
    if seconds < 10.0:
        return "unit < 10 s"
    if seconds < 60.0:
        return "unit 10-60 s"
    return "unit >= 60 s"


def fine_duration_bucket(seconds: float) -> str:
    """The duration ladder the (c) candidate is priced on: each rung is a
    minimum-duration threshold a successor plan could be built at."""

    for edge, label in ((3.0, "unit < 3 s"), (5.0, "unit 3-5 s"), (10.0, "unit 5-10 s"),
                        (30.0, "unit 10-30 s"), (60.0, "unit 30-60 s")):
        if seconds < edge:
            return label
    return "unit >= 60 s"


def purity_bucket(row) -> str:
    count = int(row["unit_speaker_count"])
    if count == 0:
        return "speakers = 0 (silent)"
    if count == 1:
        return "speakers = 1 (pure)"
    if count == 2:
        return "speakers = 2"
    return "speakers >= 3"


def share_bucket(share: float) -> str:
    if share >= 0.999:
        return "share = 1.00"
    if share >= 0.80:
        return "share 0.80-1.00"
    if share >= 0.60:
        return "share 0.60-0.80"
    return "share < 0.60"


def words_bucket(distance: int) -> str:
    if distance <= 0:
        return "0 words (on the boundary)"
    if distance == 1:
        return "1 word"
    if distance <= 3:
        return "2-3 words"
    if distance <= 9:
        return "4-9 words"
    return ">= 10 words"


def build_tables(document: dict) -> dict:
    rows = document["rows"]
    mentions = document["mentions"]
    total_excess = excess(rows)

    for row in rows:
        row["unit_duration_bucket"] = duration_bucket(float(row["unit_duration_seconds"]))
        row["unit_fine_duration_bucket"] = fine_duration_bucket(
            float(row["unit_duration_seconds"])
        )
        row["unit_ends_active_bucket"] = (
            "unit ends mid-speech (keeps its tail under candidate b)"
            if bool(row["unit_ends_on_active_frame"])
            else "unit ends in a pause (loses its tail under candidate b)"
        )
        row["unit_purity_bucket"] = purity_bucket(row)
        row["unit_share_bucket"] = share_bucket(float(row["unit_speaker_share"]))
        row["unit_absorbed_bucket"] = (
            "absorbed >= 1 sliver"
            if int(row["unit_absorbed_units"]) > 0
            else "absorbed none"
        )
        row["unit_speaker_change_bucket"] = (
            "speaker changed from previous unit"
            if bool(row["unit_speaker_changed_from_previous"])
            else "same speaker as previous unit (or first)"
        )
        row["cell_nearest_words_bucket"] = words_bucket(int(row["cell_nearest_words"]))
        row["comparator_nearest_words_bucket"] = words_bucket(
            int(row["comparator_nearest_words"])
        )
        row["cell_tail_reach"] = (
            f"within {TAIL_CELL_TAIL_SECONDS:g} s of the unit end"
            if float(row["cell_from_end_seconds"]) <= TAIL_CELL_TAIL_SECONDS
            else "elsewhere in the unit"
        )
        row["cell_head_reach"] = (
            f"within {TAIL_CELL_TAIL_SECONDS:g} s of the unit start"
            if float(row["cell_from_start_seconds"]) <= TAIL_CELL_TAIL_SECONDS
            else "elsewhere in the unit"
        )
        row["comparator_tail_reach"] = (
            f"within {TAIL_CELL_TAIL_SECONDS:g} s of the window end"
            if float(row["comparator_from_end_seconds"]) <= TAIL_CELL_TAIL_SECONDS
            else "elsewhere in the window"
        )

    corpus = {
        arm: ph.bucket_counts(rows, arm) | {"wer_percent": ph.wer_percent(ph.bucket_counts(rows, arm))}
        for arm in ("comparator", "cell")
    }

    # --- Q1: the S/D split ------------------------------------------------
    per_call = []
    cell_calls = call_rows_for_bootstrap(rows, "cell")
    comparator_calls = call_rows_for_bootstrap(rows, "comparator")
    for sample_id in sorted(cell_calls):
        left, right = comparator_calls[sample_id], cell_calls[sample_id]
        per_call.append(
            {
                "sample_id": sample_id,
                "person_reference_words": right["reference_words"],
                "comparator_substitutions": left["substitutions"],
                "comparator_deletions": left["deletions"],
                "comparator_errors": left["errors"],
                "cell_substitutions": right["substitutions"],
                "cell_deletions": right["deletions"],
                "cell_errors": right["errors"],
                "delta_substitutions": right["substitutions"] - left["substitutions"],
                "delta_deletions": right["deletions"] - left["deletions"],
                "delta_errors": right["errors"] - left["errors"],
            }
        )
    split = {
        "corpus": corpus,
        "excess_errors": total_excess,
        "excess_substitutions": corpus["cell"]["substitutions"]
        - corpus["comparator"]["substitutions"],
        "excess_deletions": corpus["cell"]["deletions"] - corpus["comparator"]["deletions"],
        "substitution_rate": paired_interval(rows, "substitutions"),
        "deletion_rate": paired_interval(rows, "deletions"),
        "error_rate": paired_interval(rows, "errors"),
        "per_call": per_call,
        "calls_where_deletions_rose": sum(1 for r in per_call if r["delta_deletions"] > 0),
        "calls_where_deletions_fell": sum(1 for r in per_call if r["delta_deletions"] < 0),
        "calls_where_substitutions_rose": sum(
            1 for r in per_call if r["delta_substitutions"] > 0
        ),
        "calls_where_substitutions_fell": sum(
            1 for r in per_call if r["delta_substitutions"] < 0
        ),
    }

    # --- Q2: position ------------------------------------------------------
    position = {
        "cell_boundary_bins_seconds": with_excess(
            ph.group_table(rows, "cell_nearest_bin"), total_excess
        ),
        "comparator_boundary_bins_seconds": with_excess(
            ph.group_table(rows, "comparator_nearest_bin"), total_excess
        ),
        "cell_boundary_bins_words": with_excess(
            ph.group_table(rows, "cell_nearest_words_bucket"), total_excess
        ),
        "comparator_boundary_bins_words": with_excess(
            ph.group_table(rows, "comparator_nearest_words_bucket"), total_excess
        ),
        "mention_split": mention_split_table(mentions),
        # A short unit puts every one of its words near a boundary, so the
        # pooled gradient above cannot by itself tell a BOUNDARY effect from a
        # SHORT-UNIT effect. This cross-tab does: inside one duration class the
        # unit length is held roughly fixed and only the distance moves.
        "boundary_bins_within_duration_class": {
            label: with_excess(
                ph.group_table(
                    [row for row in rows if row["unit_duration_bucket"] == label],
                    "cell_nearest_bin",
                ),
                total_excess,
            )
            for label in ("unit < 10 s", "unit 10-60 s", "unit >= 60 s")
        },
    }

    # --- Q3: unit properties ----------------------------------------------
    unit_properties = {
        key: with_excess(ph.group_table(rows, key), total_excess)
        for key in (
            "unit_duration_bucket",
            "unit_fine_duration_bucket",
            "unit_ends_active_bucket",
            "unit_purity_bucket",
            "unit_share_bucket",
            "unit_end_cut",
            "unit_absorbed_bucket",
            "unit_speaker_change_bucket",
        )
    }

    # --- Q4: tail versus unit ---------------------------------------------
    tails = {
        "cell_tail_reach": with_excess(ph.group_table(rows, "cell_tail_reach"), total_excess),
        "cell_head_reach": with_excess(ph.group_table(rows, "cell_head_reach"), total_excess),
        "comparator_tail_reach": with_excess(
            ph.group_table(rows, "comparator_tail_reach"), total_excess
        ),
        "proportionality": proportionality_block(corpus),
        "per_tail_by_duration_class": per_tail_by_duration_class(rows),
        "deletion_position": deletion_position_block(rows),
    }

    return {
        "schema": "saea-e21-obs-e1-person-harm-decomposition-v1",
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": ph.EXPOSURE_ROW,
        "entity_class": ENTITY_CLASS,
        "cell": document["cell"],
        "comparator": document["comparator"],
        "identity_anchor": document["identity_anchor"],
        "position_provenance": document["position_provenance"],
        "zero_contact": document["zero_contact"],
        "q1_substitutions_versus_deletions": split,
        "q2_position": position,
        "q3_unit_properties": unit_properties,
        "q4_tail_versus_unit": tails,
        "q5_successor_pricing": successor_pricing(),
        "claim_surface": (
            "Discovery data at n = 44 clusters, below the program's n >= 400 rule. "
            "Nothing here is a decision, a preregistration or a GO; OBS-E1 stays "
            "REJECTED and no successor cell is registered by this read."
        ),
    }


TAIL_CELL_TAIL_SECONDS = ph.TAIL_SECONDS


def mention_split_table(mentions) -> dict:
    """Does a transport boundary cut THROUGH a name? Exact, no timing involved:
    a mention is SPLIT in an arm when its reference words fall in more than one
    of that arm's spans."""

    out: dict[str, object] = {}
    for arm in ("comparator", "cell"):
        multiword = [m for m in mentions if int(m["words"]) > 1]
        split = [m for m in multiword if bool(m[f"{arm}_split"])]
        whole = [m for m in multiword if not bool(m[f"{arm}_split"])]

        def rate(group):
            words = sum(int(m["words"]) for m in group)
            errors = sum(int(m[f"{arm}_errors"]) for m in group)
            return {
                "mentions": len(group),
                "words": words,
                "errors": errors,
                "wer_percent": (100.0 * errors / words) if words else 0.0,
            }

        out[arm] = {
            "mentions_total": len(mentions),
            "multiword_mentions": len(multiword),
            "split_across_spans": rate(split),
            "within_one_span": rate(whole),
        }
    return out


def proportionality_block(corpus: dict) -> dict:
    """Is the PERSON loss proportional to the number of TAILS or to the number of
    transport BOUNDARIES? The tail cell is the discriminating point: it added
    1,593 tails and ZERO boundaries."""

    observed = corpus["comparator"]["wer_percent"] - corpus["cell"]["wer_percent"]
    per_tail = TAIL_CELL["person_improvement_points"] / TAIL_CELL["tails"]
    predicted = per_tail * 5122
    return {
        "tail_cell": dict(TAIL_CELL),
        "cell_tails": 5122,
        "cell_transport_boundaries_added": 5122 - 1593,
        "observed_person_improvement_points": observed,
        "tail_proportional_prediction_points": predicted,
        "residual_points": observed - predicted,
        "tail_model_explains_percent": (
            100.0 * predicted / observed if observed else 0.0
        ),
        "points_per_tail_tail_cell": per_tail,
        "points_per_tail_obs_e1": observed / 5122,
        "reading": (
            "The tail cell holds the transport unit fixed and adds one tail per "
            "window, so it prices a tail with zero new boundaries. Scaling its "
            "per-tail cost to OBS-E1's 5,122 tails predicts the observed PERSON "
            "movement; what the 3,529 extra transport boundaries add on top is the "
            "residual."
        ),
    }


def per_tail_by_duration_class(rows) -> dict:
    """Is a tail's cost the SAME on every unit? Every unit carries exactly one
    tail, so dividing each duration class's excess PERSON errors by that class's
    unit count prices a tail where it actually sits. A flat column would support
    "the loss is proportional to the number of tails"; a steep one refuses it."""

    units = [unit for block in load_json(PLAN)["calls"] for unit in block["units"]]
    counts: dict[str, int] = {}
    for unit in units:
        counts[duration_bucket(float(unit["duration_seconds"]))] = (
            counts.get(duration_bucket(float(unit["duration_seconds"])), 0) + 1
        )
    table = []
    for label in ("unit < 10 s", "unit 10-60 s", "unit >= 60 s"):
        members = [row for row in rows if row["unit_duration_bucket"] == label]
        left = ph.bucket_counts(members, "comparator")
        right = ph.bucket_counts(members, "cell")
        tails = counts.get(label, 0)
        table.append(
            {
                "stratum": label,
                "units_and_tails": tails,
                "units_share_percent": 100.0 * tails / len(units),
                "person_reference_words": right["reference_words"],
                "person_words_share_percent": 100.0
                * right["reference_words"]
                / sum(int(row["multiplicity"]) for row in rows),
                "excess_errors": right["errors"] - left["errors"],
                "excess_errors_per_tail": (
                    (right["errors"] - left["errors"]) / tails if tails else 0.0
                ),
                "excess_errors_per_person_word": (
                    (right["errors"] - left["errors"]) / right["reference_words"]
                    if right["reference_words"]
                    else 0.0
                ),
            }
        )
    return {
        "units_total": len(units),
        "table": table,
        "reading": (
            "Every unit carries exactly one tail, so 'per tail' and 'per unit' are "
            "the same column here. A steep column means the tail count is a proxy "
            "rather than a cause."
        ),
    }


def deletion_position_block(rows) -> dict:
    """Of the PERSON words the CELL deletes, how many sit at a unit edge? Counted
    in reference words, which is exact; the seconds column is derived."""

    deleted = [row for row in rows if str(row["cell_kind"]) == conec.OP_DELETION]
    comparator_deleted = [
        row for row in rows if str(row["comparator_kind"]) == conec.OP_DELETION
    ]
    all_words = rows

    def share(group, predicate) -> dict:
        weight = sum(int(row["multiplicity"]) for row in group)
        hit = sum(int(row["multiplicity"]) for row in group if predicate(row))
        return {
            "words": weight,
            "at_edge": hit,
            "share_percent": (100.0 * hit / weight) if weight else 0.0,
        }

    predicates = {
        "last or first reference word of its unit": lambda r: int(r["cell_nearest_words"]) == 0,
        "within 2 reference words of a unit edge": lambda r: int(r["cell_nearest_words"]) <= 1,
        "within 2.0 derived seconds of the unit end": lambda r: float(
            r["cell_from_end_seconds"]
        )
        <= ph.TAIL_SECONDS,
    }
    return {
        "cell_deletions": {
            name: share(deleted, predicate) for name, predicate in predicates.items()
        },
        "comparator_deletions_at_window_edges": {
            "last or first reference word of its window": share(
                comparator_deleted, lambda r: int(r["comparator_nearest_words"]) == 0
            ),
            "within 2.0 derived seconds of the window end": share(
                comparator_deleted,
                lambda r: float(r["comparator_from_end_seconds"]) <= ph.TAIL_SECONDS,
            ),
        },
        "base_rate_all_person_words": {
            "cell: on a unit edge": share(
                all_words, lambda r: int(r["cell_nearest_words"]) == 0
            ),
            "cell: within 2.0 derived seconds of the unit end": share(
                all_words, lambda r: float(r["cell_from_end_seconds"]) <= ph.TAIL_SECONDS
            ),
            "comparator: on a window edge": share(
                all_words, lambda r: int(r["comparator_nearest_words"]) == 0
            ),
        },
    }


# ---------------------------------------------------------------------------
# Stage 2b: what a successor transport plan would COST. Design only.
# ---------------------------------------------------------------------------

#: The OBS-E1 flight's own realized figures, quoted from its verdict's section 7.
CELL_CONTACTS = 5122
CELL_CUT_SECONDS = 141345.852687
CELL_DELIVERED_SECONDS = 151589.852687
CELL_GPU_HOURS = 1.0657
CELL_WALL_SECONDS = 5964
CELL_PROMPT_TOKENS = 2255812

#: The encoder's own rate, measured on the wire by the tail cell: 1,593 windows
#: x 2.0 s of appended silence cost exactly 41,418 prompt tokens = 26 per window.
ENCODER_TOKENS_PER_SECOND = 13.0

#: KC-E1f's realized second pass, from its verdict's section 11: 1,593 pass-2
#: contacts over the SAME audio cost 1.1093 GPU-h against the comparator's
#: 0.9734 for one pass, on +83.4 % prompt tokens.
REPAIR_PASS = {
    "run_id": "SAEA-E21-KC-E1F-REPAIR-44-V1",
    "contacts": 1593,
    "gpu_hours": 1.1093,
    "prompt_tokens": 3550695,
    "person_improvement_points": 3.737,
    "person_ci90": [2.653, 4.855],
    "person_wer_percent": 18.752,
    "reachable_floor_percent": 100.0 * 83 / 2917,
}


def gpu_hours_for(delivered_seconds: float) -> float:
    """The OBS-E1 verdict's own cost model, in its own words: on this carrier and
    geometry the cost tracks ENCODED SECONDS, not requests (its section 7, where
    the realized 1.0657 landed 2 % above the audio-proportional floor and the
    contact-proportional ceiling over-predicted by 2.9x)."""

    return CELL_GPU_HOURS * delivered_seconds / CELL_DELIVERED_SECONDS


def successor_pricing() -> dict:
    """The four OBS-E1b candidates, priced from the committed plan and the cell's
    own realized cost. DESIGN ONLY: no candidate is registered, preregistered or
    authorized by this read, and every figure is a projection under the stated
    model, never a measurement."""

    units = [unit for block in load_json(PLAN)["calls"] for unit in block["units"]]
    ends_active = sum(1 for unit in units if bool(unit["ends_on_active_frame"]))

    def block(label, contacts, delivered, note, extra=None):
        entry = {
            "candidate": label,
            "contacts": contacts,
            "delivered_audio_seconds": round(delivered, 6),
            "delivered_versus_cell_percent": 100.0 * delivered / CELL_DELIVERED_SECONDS,
            "projected_gpu_hours": round(gpu_hours_for(delivered), 4),
            "projected_wall_minutes": round(
                CELL_WALL_SECONDS / 60.0 * delivered / CELL_DELIVERED_SECONDS, 1
            ),
            "cost_model": note,
        }
        if extra:
            entry.update(extra)
        return entry

    margins = []
    for seconds in (3.0, 5.0, 10.0):
        delivered = CELL_CUT_SECONDS + CELL_CONTACTS * (seconds + ph.TAIL_SECONDS)
        margins.append(
            block(
                f"(a) context margin +{seconds:g} s of preceding audio, text discarded",
                CELL_CONTACTS,
                delivered,
                "audio-proportional; the margin is delivered, never metered as new speech",
                {
                    "extra_prompt_tokens": int(
                        CELL_CONTACTS * seconds * ENCODER_TOKENS_PER_SECOND
                    ),
                    "projected_prompt_tokens": int(
                        CELL_PROMPT_TOKENS
                        + CELL_CONTACTS * seconds * ENCODER_TOKENS_PER_SECOND
                    ),
                    "worst_request_tokens_projected": int(
                        1258 + seconds * ENCODER_TOKENS_PER_SECOND
                    ),
                    "slot_tokens": 6144,
                },
            )
        )

    minimum_duration = []
    for threshold in (3.0, 5.0, 10.0):
        merged = 0
        for call in load_json(PLAN)["calls"]:
            merged += len(ph.merge_units_below_threshold(call["units"], threshold))
        delivered = CELL_CUT_SECONDS + merged * ph.TAIL_SECONDS
        minimum_duration.append(
            block(
                f"(c) minimum unit duration raised to {threshold:g} s",
                merged,
                delivered,
                "audio-proportional; the cut total is invariant, only the tail count moves",
                {
                    "units_removed": CELL_CONTACTS - merged,
                    "mean_unit_seconds": round(CELL_CUT_SECONDS / merged, 3),
                },
            )
        )

    no_tail = block(
        "(b) tail only where the unit ends mid-speech",
        CELL_CONTACTS,
        CELL_CUT_SECONDS + ends_active * ph.TAIL_SECONDS,
        "audio-proportional; the cut total and the contact count are both invariant",
        {
            "units_ending_on_an_active_frame": ends_active,
            "units_total": len(units),
            "share_percent": 100.0 * ends_active / len(units),
            "tails_removed": len(units) - ends_active,
        },
    )

    repair = block(
        "(d) KC-E1f second-pass entity repair on top of the units",
        CELL_CONTACTS * 2,
        CELL_DELIVERED_SECONDS * 2,
        "two passes over the same media; pass 2 carries the audio, the brief and pass 1",
        {
            "second_pass_only_gpu_hours": round(
                gpu_hours_for(CELL_DELIVERED_SECONDS)
                * REPAIR_PASS["gpu_hours"]
                / 0.9734,
                4,
            ),
            "projected_prompt_tokens": int(
                CELL_PROMPT_TOKENS
                + CELL_CONTACTS
                * (REPAIR_PASS["prompt_tokens"] / 1593 - 1935965 / 1593)
                + CELL_PROMPT_TOKENS
            ),
            "measured_on_windows": dict(REPAIR_PASS),
        },
    )

    # The preregistration's OWN named follow-up, priced here beside the four
    # repair candidates so the table cannot be read as replacing it: a fixed
    # window at the cell's realized mean unit length, contact- and length-matched,
    # boundary- and purity-unmatched.
    buffer_seconds = CELL_CUT_SECONDS / CELL_CONTACTS
    control_windows = sum(
        math.ceil(float(block["decoded_duration_seconds"]) / buffer_seconds)
        for block in load_json(PLAN)["calls"]
    )
    control = block(
        f"(control) fixed {buffer_seconds:.2f}-second windows -- the preregistration's own OBS-E1b",
        control_windows,
        CELL_CUT_SECONDS + control_windows * ph.TAIL_SECONDS,
        "audio-proportional; the same media convention as the cell, the transport unit fixed",
        {
            "buffer_seconds": round(buffer_seconds, 4),
            "contacts_versus_cell": control_windows - CELL_CONTACTS,
            "separates": (
                "factor 3 (contact count and length) from factors 1 and 2 (boundary "
                "placement and speaker purity); it is a CONTROL, not a repair, and it "
                "answers a different question from candidates (a)-(d)"
            ),
        },
    )

    return {
        "what_this_is": (
            "DESIGN ONLY, priced under the OBS-E1 verdict's own audio-proportional cost "
            "model. No candidate is registered, preregistered or authorized here, and "
            "OBS-E1 stays REJECTED."
        ),
        "e_contact_matched_control": control,
        "cell_realized": {
            "contacts": CELL_CONTACTS,
            "cut_audio_seconds": CELL_CUT_SECONDS,
            "delivered_audio_seconds": CELL_DELIVERED_SECONDS,
            "gpu_hours": CELL_GPU_HOURS,
            "wall_minutes": round(CELL_WALL_SECONDS / 60.0, 1),
            "prompt_tokens": CELL_PROMPT_TOKENS,
        },
        "a_context_margin": margins,
        "b_tail_only_where_mid_speech": no_tail,
        "c_minimum_unit_duration": minimum_duration,
        "d_repair_pass_on_units": repair,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("rows", "tables"), default="rows")
    parser.add_argument("--rows-out", type=Path, default=ROWS_PATH)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.stage == "rows":
        document = build_rows()
        args.rows_out.parent.mkdir(parents=True, exist_ok=True)
        args.rows_out.write_text(
            json.dumps(document, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(json.dumps({"identity_anchor": document["identity_anchor"]}, indent=1))
        print(f"rows -> {args.rows_out} ({len(document['rows'])} rows)")
        return 0

    if args.out_dir is None:
        raise SystemExit("--stage tables needs --out-dir")
    tables = build_tables(load_json(args.rows_out))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    target = args.out_dir / "person-harm.json"
    target.write_text(
        json.dumps(tables, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("wrote", target)
    print(json.dumps(tables["q1_substitutions_versus_deletions"]["corpus"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
