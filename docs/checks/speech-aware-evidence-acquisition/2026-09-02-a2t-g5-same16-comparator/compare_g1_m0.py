"""Compare completed G5 outputs with frozen G1 M0 on the identical 16 rows.

This postflight analysis reads only sealed output JSONL files and scorer-side
gold. It never opens audio, contacts a model, or uses the network. Frozen M0
rows are copied unchanged into the result so the comparison cannot silently
rewrite landed predictions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[4]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    load_expected_calls,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (  # noqa: E402
    ToolCall,
    parse_tool_calls_text,
    score_item,
)


G5_IDS = tuple(
    sorted(
        (
            "tier1_direct:002609",
            "tier1_direct:002728",
            "tier2_parametric:003923",
            "tier2_parametric:006317",
            "tier3_multi_intent:002995",
            "tier3_multi_intent:003153",
            "tier4_implicit:001074",
            "tier4_implicit:001148",
            "tier5_needle:000241",
            "tier5_needle:002215",
            "tier6_correction:002179",
            "tier6_correction:003197",
            "tier7_multiturn:000545",
            "tier7_multiturn:002120",
            "tier8_intent_blending:000581",
            "tier8_intent_blending:000720",
        )
    )
)
M0_RELPATH = Path(
    "runs/SAEA-A2T-G1/attempt-20260825T100735Z-a2tg1m0/"
    "arm1-m0-outputs.jsonl"
)
M0_SHA256 = "dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get("sample_id"), str):
            raise RuntimeError(f"malformed output row {line_number} in {path}")
        sample_id = str(row["sample_id"])
        if sample_id in result:
            raise RuntimeError(f"duplicate sample {sample_id!r} in {path}")
        result[sample_id] = row
    return result


def score_row(
    row: Mapping[str, object], expected: Sequence[ToolCall]
) -> dict[str, object]:
    text = row.get("text", row.get("final_response_text"))
    if not isinstance(text, str):
        raise RuntimeError("output row lacks a scoreable response text field")
    predicted, parsed = parse_tool_calls_text(text)
    score = score_item(expected, predicted)
    return {
        "exact": int(score.exact_match),
        "tool": int(score.tool_accuracy),
        "slot_f1": score.slot_f1,
        "slot_true_positives": score.slot_true_positives,
        "slot_expected_total": score.slot_expected_total,
        "slot_predicted_total": score.slot_predicted_total,
        "parsed": int(parsed),
        "predicted_calls": len(predicted),
    }


def aggregate_view(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    count = len(rows)
    exact_count = sum(int(row["exact"]) for row in rows)
    tool_count = sum(int(row["tool"]) for row in rows)
    parse_count = sum(int(row["parsed"]) for row in rows)
    true_positives = sum(int(row["slot_true_positives"]) for row in rows)
    expected_total = sum(int(row["slot_expected_total"]) for row in rows)
    predicted_total = sum(int(row["slot_predicted_total"]) for row in rows)
    precision = true_positives / predicted_total if predicted_total else 0.0
    recall = true_positives / expected_total if expected_total else 0.0
    slot_f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "samples": count,
        "exact_count": exact_count,
        "exact_match": exact_count / count if count else 0.0,
        "tool_count": tool_count,
        "tool_accuracy": tool_count / count if count else 0.0,
        "parse_count": parse_count,
        "parse_failures": count - parse_count,
        "slot_true_positives": true_positives,
        "slot_expected_total": expected_total,
        "slot_predicted_total": predicted_total,
        "slot_precision": precision,
        "slot_recall": recall,
        "slot_f1": slot_f1,
    }


def paired_view(rows: Sequence[Mapping[str, object]], metric: str) -> dict[str, int]:
    values = [str(row["paired"][metric]) for row in rows]  # type: ignore[index]
    return {name: values.count(name) for name in ("win", "loss", "tie")}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g5", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    root = data_root()
    m0_path = Path(root) / M0_RELPATH
    if sha256_file(m0_path) != M0_SHA256:
        raise RuntimeError("frozen G1 M0 output identity drift")
    m0 = read_rows(m0_path)
    g5 = read_rows(args.g5)
    if not set(G5_IDS).issubset(m0):
        raise RuntimeError("frozen G1 M0 does not cover G5 fixed16")
    if set(g5) != set(G5_IDS):
        raise RuntimeError("G5 outputs do not cover exactly fixed16")

    lock = load_lock(umbrella_lock_path(REPO))
    expected = load_expected_calls(lock, root, repo_root=REPO)
    comparison_rows: list[dict[str, object]] = []
    for sample_id in G5_IDS:
        m0_score = score_row(m0[sample_id], expected[sample_id])
        g5_score = score_row(g5[sample_id], expected[sample_id])

        def outcome(metric: str) -> str:
            left, right = int(m0_score[metric]), int(g5_score[metric])
            return "win" if right > left else "loss" if right < left else "tie"

        comparison_rows.append(
            {
                "sample_id": sample_id,
                "tier": sample_id.split(":", 1)[0],
                "m0": m0_score,
                "g5": g5_score,
                "paired": {"exact": outcome("exact"), "tool": outcome("tool")},
            }
        )
    result = {
        "schema": "saea-a2t-g5-same16-comparator-v1",
        "sources": {
            "m0_outputs": str(m0_path),
            "m0_outputs_sha256": M0_SHA256,
            "g5_outputs": str(args.g5.resolve()),
            "g5_outputs_sha256": sha256_file(args.g5),
        },
        "contacts": {"model": 0, "network": 0, "scorer_processes": 0},
        "selected_ids": list(G5_IDS),
        "m0_rows": [m0[sample_id] for sample_id in G5_IDS],
        "rows": comparison_rows,
        "aggregate": {
            "m0": aggregate_view([row["m0"] for row in comparison_rows]),
            "g5": aggregate_view([row["g5"] for row in comparison_rows]),
            "paired_exact": paired_view(comparison_rows, "exact"),
            "paired_tool": paired_view(comparison_rows, "tool"),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=False)
    args.out.write_text(
        json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result["aggregate"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
