#!/usr/bin/env python3
"""Section 4's preregistered SECONDARY read for OBS-E1: the 1,593-row common refinement.

The comparator's 1,593 fixed 90-second windows and the cell's 5,122 speaker-turn
units do not align one to one, so the CALL is the paired unit and the 44-cluster
interval is the honest one.  Section 4 nevertheless preregisters one secondary
read, and this is it: **both arms' alignment operations are charged to the SEALED
90-second window grid by REFERENCE index rather than by hypothesis index.**  The
reference is the same string in both arms, the sealed window rows partition it
into 1,593 consecutive index ranges, and every substitution, deletion and hit
carries a reference index that falls in exactly one of them; an insertion carries
none and goes to the window its reference cursor stands in -- the symmetric
convention ``charge_operations_to_windows`` already uses for the hypothesis
cursor.

**What this buys and what it does not.**  It buys a saves / harms / ties count
and the per-window strata.  It does NOT buy power: clustering by call, the
interval it produces is arithmetically the same as the primary's, and a verdict
that quotes it as if it were the honest one is misreading section 4.

The sealed window grid's own reference partition is derived from the COMPARATOR's
arm through the registered instrument (``analysis.e21_window_pairing``), never
from a transcript read out of band.

usage: e21_obs_e1_common_refinement.py <cell_attempt_dir> <cell_run_id> <out.json>
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from bisect import bisect_right
from pathlib import Path

REPO_ROOT = Path(
    os.environ.get("SAEA_REPO_ROOT", "")
    or "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
for candidate in (Path(__file__).resolve().parent, REPO_ROOT / "scripts"):
    if (candidate / "build_e21_tail2s_verdict.py").is_file():
        sys.path.insert(0, str(candidate))
        break

import build_e21_tail2s_verdict as t2  # noqa: E402
from speech_aware_evidence_acquisition.analysis import e21_window_pairing as wp  # noqa: E402

DATA_ROOT = Path(
    os.environ.get(
        "SPEECHRL_DATA_DIR",
        (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"),
    )
)
COMPARATOR_DIR = DATA_ROOT / "runs" / t2.COMPARATOR_RUN / t2.COMPARATOR_ATTEMPT
PLAN = REPO_ROOT / "docs/receipts/obs/e21-speaker-turn-units-v2.json"


def arm_pieces(trace_path: Path, outputs_path: Path, lock, taxonomy):
    """Per call: the whole-string reference words, the arm's hypothesis words, its
    alignment operations, its own spans, and the entity-owner transfer -- exactly
    what ``build_e21_tail2s_verdict.window_rows`` computes before it charges."""

    from speech_aware_evidence_acquisition.data.references import (
        reference_entity_mentions,
        reference_tokens,
    )
    from speech_aware_evidence_acquisition.reproduction import conec_entity_scoring as conec

    outputs_text = {}
    for line in outputs_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            outputs_text[str(entry["sample_id"])] = str(entry["text"])

    windows = wp.stitched_windows_from_trace(trace_path)
    windows, _hit = t2._quarantine_saturated(windows, trace_path)
    wp.assert_stitch_reproduces_outputs(windows, outputs_text)

    per_call = {}
    for sample_id in sorted(windows):
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
        hypothesis_words = conec.hypothesis_whisper_words(outputs_text[sample_id])
        operations = conec.aligned_operations(whole_words, hypothesis_words)
        per_call[sample_id] = {
            "spans": windows[sample_id],
            "whole_words": whole_words,
            "hypothesis_words": hypothesis_words,
            "operations": operations,
            "transferred": transferred,
            "entity_types": entity_types,
        }
    return per_call


def sealed_reference_boundaries(comparator_call: dict) -> tuple[int, ...]:
    """The sealed window grid's own reference partition: ``boundaries[k]`` is the
    number of reference words the first ``k + 1`` sealed windows account for."""

    from speech_aware_evidence_acquisition.reproduction.asr_wer_whisper import (
        normalize_whisper_english,
    )

    spans = comparator_call["spans"]
    hypothesis_words = comparator_call["hypothesis_words"]
    boundaries = wp.hypothesis_window_boundaries(spans, normalize_whisper_english)
    charged = wp.charge_operations_to_windows(
        comparator_call["operations"], boundaries, len(hypothesis_words)
    )
    cumulative = 0
    out: list[int] = []
    for window_operations in charged:
        cumulative += len(wp.reference_indices(window_operations))
        out.append(cumulative)
    return tuple(out)


def charge_by_reference(operations, boundaries):
    """Charge every operation of ONE arm to the sealed window whose reference
    range contains its reference index; an insertion goes to the window its
    reference cursor stands in.  A partition, so the per-window counts sum to the
    call's own."""

    buckets: list[list] = [[] for _ in boundaries]
    total = boundaries[-1] if boundaries else 0
    cursor = 0
    for operation in operations:
        _kind, ref_index, _hyp = operation
        index = cursor if ref_index is None else ref_index
        index = min(index, max(total - 1, 0))
        buckets[min(bisect_right(list(boundaries), index), len(boundaries) - 1)].append(
            operation
        )
        if ref_index is not None:
            cursor = ref_index + 1
    charged_total = sum(len(bucket) for bucket in buckets)
    if charged_total != len(operations):
        raise SystemExit(
            f"reference charging lost operations: {charged_total} of {len(operations)}"
        )
    return [tuple(bucket) for bucket in buckets]


def rows_for_arm(per_call: dict, boundaries_by_call: dict, taxonomy) -> dict[str, dict]:
    from speech_aware_evidence_acquisition.reproduction import conec_entity_scoring as conec
    from speech_aware_evidence_acquisition.reproduction import semantic_impact

    rows: dict[str, dict] = {}
    for sample_id, block in per_call.items():
        boundaries = boundaries_by_call[sample_id]
        charged = charge_by_reference(block["operations"], boundaries)
        for index, window_operations in enumerate(charged, start=1):
            buckets = conec.entity_wer_buckets(
                window_operations, block["transferred"], block["entity_types"]
            )
            impact = semantic_impact.semantic_impact_counts(
                window_operations,
                block["whole_words"],
                block["hypothesis_words"],
                taxonomy,
            )
            overall = buckets[conec.OVERALL_BUCKET]
            person = buckets.get("PERSON") or {"errors": 0, "reference_words": 0}
            organisation = buckets.get("ORG") or {"errors": 0, "reference_words": 0}
            row = {
                "window_id": f"{sample_id}#w{index:04d}",
                "sample_id": sample_id,
                "window_index": index,
                "substitutions": overall["substitutions"],
                "deletions": overall["deletions"],
                "insertions": overall["insertions"],
                "reference_words": overall["reference_words"],
                "conec_errors": overall["errors"],
                "conec_reference_words": overall["reference_words"],
                "conec_person_errors": person["errors"],
                "conec_person_reference_words": person["reference_words"],
                "conec_org_errors": organisation["errors"],
                "conec_org_reference_words": organisation["reference_words"],
                "semantic_high_reference_words": impact["high_impact_reference_words"],
                "semantic_reference_words": impact["reference_words"],
            }
            row["__wer_errors"] = (
                row["substitutions"] + row["deletions"] + row["insertions"]
            )
            rows[row["window_id"]] = row
    return rows


def window_unit_strata() -> dict[str, dict]:
    """For each sealed 90-second window, the composition of the plan units that
    overlap it -- the per-window stratum the secondary read buys."""

    plan = {
        str(block["sample_id"]): block["units"]
        for block in json.loads(PLAN.read_text(encoding="utf-8"))["calls"]
    }
    out: dict[str, dict] = {}
    for path in sorted(COMPARATOR_DIR.glob(f"{t2.COMPARATOR_RUN}.obs-derivation.*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        sample_id = str(doc["sample_id"])
        units = plan.get(sample_id) or []
        for position, record in enumerate(doc["slices"], start=1):
            start = float(record["start_seconds"])
            end = float(record["end_seconds"])
            overlapping = [
                unit
                for unit in units
                if float(unit["end_seconds"]) > start and float(unit["start_seconds"]) < end
            ]
            if not overlapping:
                continue
            shares = [float(unit["speaker_share"]) for unit in overlapping]
            counts = [int(unit["speaker_count"]) for unit in overlapping]
            lengths = [float(unit["duration_seconds"]) for unit in overlapping]
            cuts = {str(unit["end_cut"]) for unit in overlapping}
            dominated = all(
                (count == 0) or (share >= 0.60) for share, count in zip(shares, counts)
            )
            longest = max(lengths)
            if longest < 10.0:
                length_bucket = "all units < 10 s"
            elif longest < 60.0:
                length_bucket = "longest unit 10-60 s"
            else:
                length_bucket = "longest unit >= 60 s"
            out[f"{sample_id}#w{position:04d}"] = {
                "units_overlapping": len(overlapping),
                "dominance": "all-dominated" if dominated else "any-shared",
                "max_speaker_count": max(counts),
                "unit_length": length_bucket,
                "mean_unit_seconds": round(statistics.fmean(lengths), 4),
                "cut_kinds": sorted(cuts),
                "any_turn_boundary_cut": "turn-boundary" in cuts,
                "units_bucket": (
                    "1 unit"
                    if len(overlapping) == 1
                    else ("2-4 units" if len(overlapping) <= 4 else ">=5 units")
                ),
            }
    return out


def main() -> int:
    from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path
    from speech_aware_evidence_acquisition.reproduction import semantic_impact

    cell_attempt = Path(sys.argv[1])
    cell_run_id = sys.argv[2]
    out = Path(sys.argv[3])

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    taxonomy = semantic_impact.load_taxonomy(
        REPO_ROOT / semantic_impact.ACTIVE_TAXONOMY_RELPATH
    )

    comparator = arm_pieces(
        COMPARATOR_DIR / f"{t2.COMPARATOR_RUN}.trace.jsonl",
        COMPARATOR_DIR / f"{t2.COMPARATOR_RUN}.outputs.jsonl",
        lock,
        taxonomy,
    )
    cell = arm_pieces(
        cell_attempt / f"{cell_run_id}.trace.jsonl",
        cell_attempt / f"{cell_run_id}.outputs.jsonl",
        lock,
        taxonomy,
    )
    boundaries = {
        sample_id: sealed_reference_boundaries(block)
        for sample_id, block in comparator.items()
    }
    comparator_rows = rows_for_arm(comparator, boundaries, taxonomy)
    cell_rows = rows_for_arm(cell, boundaries, taxonomy)

    shared = sorted(set(comparator_rows) & set(cell_rows))
    scored = [w for w in shared if comparator_rows[w]["reference_words"]]

    def contrast(ids, numerator: str, denominator: str) -> dict:
        left = t2.pooled(cell_rows, ids, numerator, denominator, 100.0)
        right = t2.pooled(comparator_rows, ids, numerator, denominator, 100.0)
        block = t2.bootstrap_delta(
            cell_rows, comparator_rows, ids, numerator, denominator, 100.0,
            cluster_of=wp.call_of,
        )
        return {
            "windows": len(ids),
            "comparator": right,
            "cell": left,
            "improvement_point": block["point"],
            "improvement_ci90": [block["ci_low"], block["ci_high"]],
            "clusters": block["n"],
        }

    saves = harms = ties = 0
    for window_id in scored:
        delta = (
            comparator_rows[window_id]["__wer_errors"]
            - cell_rows[window_id]["__wer_errors"]
        )
        if delta > 0:
            saves += 1
        elif delta < 0:
            harms += 1
        else:
            ties += 1

    strata_of = window_unit_strata()
    strata: dict[str, list] = {}
    for key in ("dominance", "unit_length", "units_bucket"):
        table = []
        labels = {w: strata_of[w][key] for w in scored if w in strata_of}
        for label in sorted(set(labels.values())):
            subset = [w for w in scored if labels.get(w) == label]
            row = {"stratum": label, "windows": len(subset)}
            row["corpus_wer"] = contrast(subset, "__wer_errors", "reference_words")
            row["person"] = contrast(
                subset, "conec_person_errors", "conec_person_reference_words"
            )
            per_window_saves = sum(
                1
                for w in subset
                if comparator_rows[w]["__wer_errors"] > cell_rows[w]["__wer_errors"]
            )
            per_window_harms = sum(
                1
                for w in subset
                if comparator_rows[w]["__wer_errors"] < cell_rows[w]["__wer_errors"]
            )
            row["saves"] = per_window_saves
            row["harms"] = per_window_harms
            row["ties"] = len(subset) - per_window_saves - per_window_harms
            row["equal_stratum_comparator_wer"] = t2.equal_stratum(
                comparator_rows, subset, "__wer_errors", "reference_words", 100.0
            )
            row["equal_stratum_cell_wer"] = t2.equal_stratum(
                cell_rows, subset, "__wer_errors", "reference_words", 100.0
            )
            table.append(row)
        strata[key] = table

    document = {
        "schema": "saea-e21-obs-e1-common-refinement-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": cell_run_id,
        "comparator": {"run_id": t2.COMPARATOR_RUN, "attempt_id": t2.COMPARATOR_ATTEMPT},
        "what_this_is": (
            "section 4's preregistered SECONDARY read: BOTH arms' alignment operations "
            "charged to the SEALED 90-second window grid by REFERENCE index. It buys a "
            "saves / harms / ties count and the per-window strata, NOT power; the honest "
            "interval is the primary's 44-cluster one."
        ),
        "windows_total": len(shared),
        "windows_with_reference_words": len(scored),
        "conservation": {
            "comparator_errors": sum(
                comparator_rows[w]["__wer_errors"] for w in shared
            ),
            "cell_errors": sum(cell_rows[w]["__wer_errors"] for w in shared),
            "comparator_reference_words": sum(
                comparator_rows[w]["reference_words"] for w in shared
            ),
            "cell_reference_words": sum(cell_rows[w]["reference_words"] for w in shared),
        },
        "corpus_wer": contrast(shared, "__wer_errors", "reference_words"),
        "person": contrast(
            shared, "conec_person_errors", "conec_person_reference_words"
        ),
        "org": contrast(shared, "conec_org_errors", "conec_org_reference_words"),
        "saves_harms_ties": {
            "saves": saves,
            "harms": harms,
            "ties": ties,
            "n": len(scored),
            "convention": (
                "a window is a SAVE when the cell makes strictly fewer whole-string "
                "alignment errors than the comparator on that window's own reference range"
            ),
        },
        "per_window_strata": strata,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(document, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "windows": document["windows_total"],
                "scored": document["windows_with_reference_words"],
                "corpus_wer": document["corpus_wer"],
                "saves_harms_ties": document["saves_harms_ties"],
                "out": str(out),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
