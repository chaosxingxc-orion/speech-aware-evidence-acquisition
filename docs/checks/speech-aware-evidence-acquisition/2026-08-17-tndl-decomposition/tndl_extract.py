"""T-NDL stage 1: wrong-entity mention inventory WITH the hypothesis substitution.

Archival replay (owner ruling D5) of an already-consumed discovery trace. Reads
outputs.jsonl + the gold reference layer offline. ZERO model contact.

Emits one JSONL row per GOLD entity mention that the frozen entity-wer scorer
counts as not-recognised, carrying the reference mention text, the hypothesis text
actually aligned to it, and the three format-tier verdicts.

Correctness is not asserted, it is reconciled: the per-sample and per-class
correct/expected counts derived here are compared against the COMMITTED
``r0bias.entity-wer.json`` produced by the frozen scorer. Any disagreement is a
hard failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tndl_lib import (  # noqa: E402
    align_trace, chunk_offsets, chunks_covering, format_match,
)
from speech_aware_evidence_acquisition.core.scorers import (  # noqa: E402
    _normalized_span_offsets,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root, load_lock, umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.references import (  # noqa: E402
    reference_entity_mentions, reference_tokens,
)
from speech_aware_evidence_acquisition.scoring.normalize import tokens_v1  # noqa: E402

WIDE = 6  # normalized tokens of slack on each side of the aligned region


def mention_windows(positions, ref_to_hyp, hyp_len):
    """Tight and wide hypothesis index ranges for one mention.

    Tight: the span of hypothesis positions the aligner actually paired with this
    mention's reference positions. When EVERY position was deleted the mention has
    no hypothesis partner at all, so the range collapses to the gap between the
    nearest aligned neighbours on either side -- which is where an insertion, if
    any, would sit.
    """
    aligned = [ref_to_hyp[p] for p in positions if ref_to_hyp[p] is not None]
    if aligned:
        lo, hi = min(aligned), max(aligned)
    else:
        left = min(positions) - 1
        while left >= 0 and ref_to_hyp[left] is None:
            left -= 1
        right = max(positions) + 1
        while right < len(ref_to_hyp) and ref_to_hyp[right] is None:
            right += 1
        lo = (ref_to_hyp[left] + 1) if left >= 0 else 0
        hi = (ref_to_hyp[right] - 1) if right < len(ref_to_hyp) else hyp_len - 1
        if hi < lo:
            lo, hi = lo, lo - 1  # empty: a pure deletion
    return (lo, hi), (max(0, lo - WIDE), min(hyp_len - 1, hi + WIDE))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", required=True, type=Path)
    parser.add_argument("--reconcile", type=Path, default=None,
                        help="committed entity-wer JSON to reconcile against")
    parser.add_argument("--reconcile-rladder", type=Path, default=None,
                        help="committed p2-rladder report.json to reconcile against")
    parser.add_argument("--arm", default=None, help="arm name inside --reconcile-rladder")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    root = data_root()
    lock = load_lock(umbrella_lock_path())
    rows = [json.loads(line) for line in
            args.outputs.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"samples: {len(rows)}")

    wrong_rows = []
    per_sample = {}
    per_class = defaultdict(lambda: Counter())

    for row in rows:
        sample_id = row["sample_id"]
        carrier = row["carrier_lock_key"]
        raw_ref = reference_tokens(lock, root, carrier, sample_id)
        mentions = reference_entity_mentions(lock, root, carrier, sample_id)
        ref = tokens_v1(" ".join(raw_ref))
        hyp = tokens_v1(row["text"])
        ref_to_hyp, _ops, _hyp_aligned, mask = align_trace(ref, hyp)
        ref_spans = _normalized_span_offsets(raw_ref)
        hyp_chunks = row["text"].split()
        hyp_spans = chunk_offsets(hyp_chunks, tokens_v1)

        expected = correct = 0
        for mention in mentions:
            positions = []
            for raw_index in mention.token_indices:
                start, end = ref_spans[raw_index]
                positions.extend(range(start, end))
            expected += 1
            per_class[mention.entity_type]["expected"] += 1
            is_correct = bool(positions) and all(mask[p] for p in positions)
            if is_correct:
                correct += 1
                per_class[mention.entity_type]["correct"] += 1
                continue
            if not positions:
                wrong_rows.append({
                    "sample_id": sample_id, "entity_id": mention.entity_id,
                    "entity_type": mention.entity_type,
                    "token_indices": list(mention.token_indices),
                    "ref_text": " ".join(mention.tokens),
                    "hyp_tight": "", "hyp_wide": "", "degenerate": True,
                    "fmt_strict": False, "fmt_window": False, "fmt_value": False,
                })
                continue

            (tlo, thi), (wlo, whi) = mention_windows(positions, ref_to_hyp, len(hyp))
            tight = " ".join(hyp_chunks[k] for k in chunks_covering(hyp_spans, tlo, thi)) \
                if thi >= tlo else ""
            wide = " ".join(hyp_chunks[k] for k in chunks_covering(hyp_spans, wlo, whi))
            ref_text = " ".join(mention.tokens)

            strict = bool(tight) and format_match(ref_text, tight, "strict")
            window = strict or (bool(wide) and format_match(ref_text, wide, "window"))
            value = window or (bool(wide) and format_match(ref_text, wide, "value"))
            wrong_rows.append({
                "sample_id": sample_id, "entity_id": mention.entity_id,
                "entity_type": mention.entity_type, "ref_text": ref_text,
                "token_indices": list(mention.token_indices),
                "hyp_tight": tight, "hyp_wide": wide, "degenerate": False,
                "fmt_strict": strict, "fmt_window": window, "fmt_value": value,
            })
        per_sample[sample_id] = {"expected": expected, "correct": correct}
        print(f"  {sample_id}: ref={len(ref):6d} hyp={len(hyp):6d} "
              f"expected={expected:4d} correct={correct:4d} wrong={expected - correct:4d}")

    args.out.write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in wrong_rows) + "\n",
        encoding="utf-8")
    total_expected = sum(v["expected"] for v in per_sample.values())
    total_correct = sum(v["correct"] for v in per_sample.values())
    print(f"\nTOTAL expected={total_expected} correct={total_correct} "
          f"wrong={total_expected - total_correct}  -> {args.out}")

    if args.reconcile:
        gold = json.loads(args.reconcile.read_text(encoding="utf-8"))
        problems = []
        for entry in gold["per_sample"]:
            mine = per_sample.get(entry["sample_id"])
            if mine is None:
                problems.append(f"{entry['sample_id']}: absent here")
                continue
            if (mine["expected"] != entry["expected_total"]
                    or mine["correct"] != entry["correct"]):
                problems.append(
                    f"{entry['sample_id']}: mine={mine} frozen="
                    f"{{'expected': {entry['expected_total']}, 'correct': {entry['correct']}}}")
        for entity_type, summary in gold["aggregate"]["by_entity_type"].items():
            mine = per_class[entity_type]
            if (mine["expected"] != summary["expected_total"]
                    or mine["correct"] != summary["correct"]):
                problems.append(
                    f"class {entity_type}: mine={dict(mine)} frozen="
                    f"{{'expected': {summary['expected_total']}, "
                    f"'correct': {summary['correct']}}}")
        if problems:
            print("\nRECONCILIATION FAILED against the frozen scorer:")
            for problem in problems:
                print("  " + problem)
            return 1
        print(f"\nRECONCILIATION OK: {len(gold['per_sample'])} samples and "
              f"{len(gold['aggregate']['by_entity_type'])} entity classes match the "
              f"frozen entity-wer scorer exactly ({args.reconcile.name}).")

    if args.reconcile_rladder:
        report = json.loads(args.reconcile_rladder.read_text(encoding="utf-8"))
        by_type = report["arms"][args.arm]["entity_by_type"]
        problems = []
        for entity_type, summary in by_type.items():
            mine = per_class[entity_type]
            if (mine["expected"] != summary["expected_total"]
                    or mine["correct"] != summary["correct"]):
                problems.append(
                    f"class {entity_type}: mine={dict(mine)} frozen="
                    f"{{'expected': {summary['expected_total']}, "
                    f"'correct': {summary['correct']}}}")
        extra = set(per_class) - set(by_type)
        if extra:
            problems.append(f"classes present here but not in the report: {sorted(extra)}")
        if problems:
            print(f"\nRECONCILIATION FAILED against arm {args.arm!r}:")
            for problem in problems:
                print("  " + problem)
            return 1
        print(f"\nRECONCILIATION OK: all {len(by_type)} entity classes match arm "
              f"{args.arm!r} of {args.reconcile_rladder.name} exactly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
