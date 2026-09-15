"""Recover window statistics from one complete saved score, without gold access.

The official scorer owns normalization and alignment. This reader partitions its
saved operations using the existing whole-prefix convention, verifies every
pooled total, and leaves whole-call numeric bag matching explicitly separate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping

from . import e21_window_pairing as wp
from .delivery_windows import verified_delivery_windows, verified_execution_unit_windows
from ..core.bundle import verify_bundle
from ..core.scoring_receipt import SavedScoreReceiptRef, verify_complete_score_receipt
from ..reproduction import conec_entity_scoring as conec
from ..reproduction import numeric_value_accuracy as numeric


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pinned(binding: Mapping) -> dict:
    path = Path(binding["path"])
    if _digest(path) != binding["sha256"]:
        raise ValueError(f"saved analysis input hash mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _index(rows: list[dict]) -> dict[str, dict]:
    result = {row["sample_id"]: row for row in rows}
    if len(result) != len(rows) or not result:
        raise ValueError("score rows require a nonempty unique roster")
    return result


def _equal_buckets(actual: Mapping, expected: Mapping) -> None:
    fields = ("substitutions", "deletions", "insertions", "reference_words")
    for name in set(actual) | set(expected):
        for field in fields:
            if actual.get(name, {}).get(field, 0) != expected.get(name, {}).get(
                field, 0
            ):
                raise ValueError(f"window aggregation changed {name}/{field}")


def decompose_scored_windows(windows: Mapping, document: Mapping) -> dict:
    """Partition saved ConEC alignments, preserving the authoritative totals."""
    if document.get("verified") is not True:
        raise ValueError("window analysis requires a verified complete score")
    scores = document["scores"]
    conec_score = scores["conec-entity-wer-official"]
    calls = _index(conec_score["per_sample"])
    if set(calls) != set(windows):
        raise ValueError("window and score rosters differ")
    numeric_calls = (
        _index(scores["numeric-value-accuracy-v1"]["per_sample"])
        if "numeric-value-accuracy-v1" in scores
        else None
    )
    if numeric_calls is not None and set(numeric_calls) != set(calls):
        raise ValueError("numeric and ConEC score rosters differ")
    rows, bucket_rows, per_call = [], [], []
    for sample_id in sorted(calls):
        call = calls[sample_id]
        alignment = call.get("alignment", {})
        if alignment.get("schema") != "saea-conec-alignment-v1":
            raise ValueError(f"{sample_id}: first-score alignment artifact is missing")
        refs, hyps = alignment["reference_words"], alignment["hypothesis_words"]
        operations = [tuple(item) for item in alignment["operations"]]
        owners, entity_types = alignment["reference_owners"], alignment["entity_types"]
        if len(owners) != len(refs):
            raise ValueError("reference owner count differs from alignment")
        conec.operation_counts(operations, len(refs), len(hyps))
        reconstructed = conec.entity_wer_buckets(operations, owners, entity_types)
        _equal_buckets(reconstructed, call["by_entity_type"])
        spans = windows[sample_id]
        normalized = conec.hypothesis_whisper_words(wp.stitched_text(spans))
        if normalized != hyps:
            raise ValueError("delivered windows differ from the scored hypothesis")
        boundaries = wp.hypothesis_window_boundaries(
            spans, lambda text: " ".join(conec.hypothesis_whisper_words(text))
        )
        charged = wp.charge_operations_to_windows(operations, boundaries, len(hyps))
        call_numeric = numeric.numeric_value_counts(refs, hyps)
        if numeric_calls is not None:
            for field in (
                "expected_numeric_words",
                "matched_numeric_words",
                "hypothesis_numeric_words",
            ):
                if call_numeric[field] != numeric_calls[sample_id][field]:
                    raise ValueError(
                        "saved numeric score differs from saved alignment words"
                    )
        window_matched = 0
        for span, part in zip(spans, charged, strict=True):
            buckets = conec.entity_wer_buckets(part, owners, entity_types)
            overall = buckets[conec.OVERALL_BUCKET]
            part_refs = [refs[i] for i in wp.reference_indices(part)]
            part_hyps = [hyps[i] for i in wp.hypothesis_indices(part)]
            number_counts = numeric.numeric_value_counts(part_refs, part_hyps)
            window_matched += number_counts["matched_numeric_words"]
            row = span.as_dict()
            row.update(overall)
            row.update(
                {
                    "hypothesis_words": len(part_hyps),
                    "by_entity_type": buckets,
                    "person_entity_wer": buckets.get("PERSON", {}).get("wer", 0.0),
                    "person_reference_words": buckets.get("PERSON", {}).get(
                        "reference_words", 0
                    ),
                    "person_errors": buckets.get("PERSON", {}).get("errors", 0),
                    "org_entity_wer": buckets.get("ORG", {}).get("wer", 0.0),
                    "org_reference_words": buckets.get("ORG", {}).get(
                        "reference_words", 0
                    ),
                    "org_errors": buckets.get("ORG", {}).get("errors", 0),
                    "numeric_expected": number_counts["expected_numeric_words"],
                    "numeric_matched": number_counts["matched_numeric_words"],
                    "numeric_hypothesis": number_counts["hypothesis_numeric_words"],
                    "numeric_accuracy": number_counts["accuracy"],
                    "entity_class_counts": {
                        name: [
                            item["substitutions"],
                            item["deletions"],
                            item["reference_words"],
                        ]
                        for name, item in buckets.items()
                    },
                }
            )
            rows.append(row)
            bucket_rows.append(buckets)
        if window_matched > call_numeric["matched_numeric_words"]:
            raise ValueError("window numeric matches exceed whole-call bag matches")
        per_call.append(
            {
                "sample_id": sample_id,
                "windows": len(spans),
                "call_numeric_expected": call_numeric["expected_numeric_words"],
                "call_numeric_matched": call_numeric["matched_numeric_words"],
                "window_numeric_matched": window_matched,
                "numeric_matched_shortfall": call_numeric["matched_numeric_words"]
                - window_matched,
            }
        )
    totals = conec.merge_buckets(bucket_rows)
    _equal_buckets(totals, conec_score["aggregate"]["by_entity_type"])
    aggregate = wp.aggregate_window_rows(rows)
    return {
        "schema": "saea-scored-window-statistics-v1",
        "rows": rows,
        "per_call": per_call,
        "aggregate": aggregate,
        "entity_totals": totals,
        "call_scores": {
            name: (
                {
                    "aggregate": value["aggregate"],
                    "per_sample": [
                        {key: item for key, item in row.items() if key != "alignment"}
                        for row in value["per_sample"]
                    ],
                }
                if name == "conec-entity-wer-official"
                else value
            )
            for name, value in scores.items()
        },
        "numeric_note": (
            "Call numeric accuracy remains the official bag-matched metric. "
            "Window matching is stricter; its shortfall is descriptive."
        ),
        "pairing_note": (
            "Pair windows and resample whole calls. The pooled call-cluster interval "
            "equals the interval from resampling call totals; windows are not independent calls."
        ),
        "model_contacts": 0,
        "encoder_contacts": 0,
        "official_scorer_invocations": 0,
        "reference_loader_invocations": 0,
    }


def run(config_path: Path, output: Path) -> dict:
    """Use pinned configuration and the public complete-score verification seam."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("execution_profile") != "model-free-check":
        raise ValueError("saved-score analysis requires model-free-check")
    spec = config["analysis"]
    _pinned(spec["manifest"])
    bundle = verify_bundle(Path(spec["manifest"]["path"]))
    reference = SavedScoreReceiptRef(
        cell_id=spec["score_receipt"]["cell_id"],
        path=Path(spec["score_receipt"]["path"]),
        sha256=spec["score_receipt"]["sha256"],
    )
    receipt = verify_complete_score_receipt(reference, bundle)
    score_doc = _pinned(receipt["score_result"])
    if bundle.manifest["schema"] == "saea-derived-delivery-v1":
        windows = verified_delivery_windows(bundle)
    elif any("execution_unit_delivery" in row for row in bundle.outputs_rows):
        windows = verified_execution_unit_windows(bundle)
    elif any(
        record.get("obs_relisten") is True
        for key, record in bundle.trace_records.items() if key.endswith("/obs")
    ):
        from .e21_selective_loop_windows import verified_selective_loop_windows

        windows = verified_selective_loop_windows(
            bundle, repo_root=Path(spec["repo_root"]), data_root=Path(spec["data_root"]),
        )
    else:
        windows = wp.stitched_windows_from_trace(Path(bundle.manifest["raw_trace"]["path"]))
    wp.assert_stitch_reproduces_outputs(
        windows, {row["sample_id"]: row["text"] for row in bundle.outputs_rows}
    )
    result = decompose_scored_windows(windows, score_doc)
    if (
        len(windows) != spec["expected_calls"]
        or len(result["rows"]) != spec["expected_windows"]
    ):
        raise ValueError("saved-score window coverage differs from registered analysis")
    result.update(
        {
            "config": {
                "path": str(config_path.resolve()),
                "sha256": _digest(config_path),
            },
            "sources": {
                "manifest": spec["manifest"],
                "score_receipt": spec["score_receipt"],
            },
            "implementation": {
                "path": str(Path(__file__)),
                "sha256": _digest(Path(__file__)),
            },
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.config, args.output)
    print(json.dumps({"output": str(args.output), "aggregate": result["aggregate"]}))


if __name__ == "__main__":
    main()
