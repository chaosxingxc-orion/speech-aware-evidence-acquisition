#!/usr/bin/env python3
"""Verdict reader for the Earnings-22 ESB short-form alignment flight.

Zero model contact, strictly post-hoc. Reads only artifacts the flight already
sealed: the finalize ``<run_id>.scores.json`` (per-sample rows for both ESB
scorers), the ``score-batch/*.score.json`` that ``core.scoring_batch`` wrote as
one whole-manifest verified job, the run manifest, the sealed
``<run_id>.outputs.jsonl``, the flight receipt, the committed roster receipt,
and -- for the gap decomposition only -- the hash-pinned derived reference
layer. Emits ``result-summary.json``, ``per-call-table.md`` and
``gap-decomposition.json``.

**The decomposition transforms are diagnostics, never a second number.** The
verdict is computed from the sealed ``asr-wer-esb-whisper`` corpus figure and
nothing else. Two of the transforms below are ORACLE transforms -- they use the
reference's own length -- so they bound a component of the gap from above and
are not achievable results. They are labelled as such in the output and must be
reported that way.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Mapping

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
CHECK = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e22-esb-shortform-alignment-400-v1"
)
ROSTER = CHECK / "roster" / "flight-roster-receipt.json"

PAPER_WER = 9.79
CROSS_READ_WER = 12.3
BAND = 3.0
STRICT_FLOOR = 11.59  # whisper-large-v3, same column
LOOSE_FLOOR = 15.09  # whisper-base.en, 2026-06-13 vintage
FLOORS = {
    "whisper-large-v3": 11.59,
    "whisper-large-v3-turbo": 11.07,
    "distil-large-v3.5": 10.83,
    "qwen3-asr-0.6b": 10.78,
    "qwen3-asr-1.7b": 9.73,
    "whisper-medium.en": 12.63,
    "whisper-small.en": 12.97,
    "whisper-base.en": 15.09,
    "whisper-tiny.en": 19.12,
}
E21_FULL44_CORPUS = 8.200


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _corpus(rows: list[Mapping[str, Any]]) -> dict[str, float | int]:
    substitutions = sum(int(row["substitutions"]) for row in rows)
    deletions = sum(int(row["deletions"]) for row in rows)
    insertions = sum(int(row["insertions"]) for row in rows)
    reference_words = sum(len(row["ref_hit_mask"]) for row in rows)
    errors = substitutions + deletions + insertions
    return {
        "utterances": len(rows),
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "reference_words": reference_words,
        "errors": errors,
        "corpus_wer_pct": round(100.0 * errors / reference_words, 4) if reference_words else 0.0,
        "mean_wer_pct": round(100.0 * statistics.fmean(float(row["wer"]) for row in rows), 4),
    }


def _decompose(
    references: Mapping[str, str],
    outputs: Mapping[str, str],
    items: Mapping[str, Any],
    baseline_pct: float,
) -> dict[str, Any]:
    """Where the gap lives. Diagnostics only -- see the module docstring."""

    import sys

    sys.path.insert(0, str(REPO / "src"))
    from speech_aware_evidence_acquisition.reproduction.asr_wer_whisper import (  # noqa: PLC0415
        normalize_whisper_english,
    )
    from speech_aware_evidence_acquisition.scoring import align  # noqa: PLC0415

    pairs = {
        sid: (
            normalize_whisper_english(references[sid]).split(),
            normalize_whisper_english(outputs[sid]).split(),
        )
        for sid in references
    }

    def corpus(rows) -> dict[str, Any]:
        s = d = i = n = 0
        for reference, hypothesis in rows:
            result = align(reference, hypothesis)
            s += result.substitutions
            d += result.deletions
            i += result.insertions
            n += result.reference_length
        return {
            "substitutions": s,
            "deletions": d,
            "insertions": i,
            "reference_words": n,
            "corpus_wer_pct": round(100.0 * (s + d + i) / n, 4) if n else 0.0,
        }

    def dedup(tokens):
        out = []
        for token in tokens:
            if out and out[-1] == token:
                continue
            out.append(token)
        return out

    reference_words = sum(len(r) for r, _ in pairs.values())
    hypothesis_words = sum(len(h) for _, h in pairs.values())
    longer = sum(1 for r, h in pairs.values() if len(h) > len(r))
    shorter = sum(1 for r, h in pairs.values() if len(h) < len(r))

    buckets = []
    for lo, hi in ((0, 1), (1, 2), (2, 4), (4, 8), (8, 16), (16, 40)):
        ids = [sid for sid in pairs if lo <= float(items[sid]["audio_seconds"]) < hi]
        if not ids:
            continue
        block = corpus(pairs[sid] for sid in ids)
        errors = block["substitutions"] + block["deletions"] + block["insertions"]
        buckets.append(
            {
                "seconds_from": lo,
                "seconds_to": hi,
                "utterances": len(ids),
                "hypothesis_words": sum(len(pairs[sid][1]) for sid in ids),
                "length_ratio": round(
                    sum(len(pairs[sid][1]) for sid in ids)
                    / max(1, sum(len(pairs[sid][0]) for sid in ids)),
                    4,
                ),
                "insertion_share_of_errors_pct": round(
                    100.0 * block["insertions"] / max(1, errors), 2
                ),
                **block,
            }
        )

    transforms = {
        "hypothesis_immediate_repeats_collapsed": {
            "oracle": False,
            "what": "collapse runs of an identical word in the HYPOTHESIS only",
            **corpus((r, dedup(h)) for r, h in pairs.values()),
        },
        "both_sides_immediate_repeats_collapsed": {
            "oracle": False,
            "what": "collapse runs of an identical word on BOTH sides",
            **corpus((dedup(r), dedup(h)) for r, h in pairs.values()),
        },
        "hypothesis_truncated_to_reference_length": {
            "oracle": True,
            "what": (
                "cut each hypothesis to its own reference word count -- an ORACLE "
                "transform that bounds the over-generation component from above and is "
                "not an achievable result"
            ),
            **corpus((r, h[: len(r)]) for r, h in pairs.values()),
        },
        "dedup_then_truncate": {
            "oracle": True,
            "what": "both of the above, composed; also an ORACLE bound",
            **corpus((r, dedup(h)[: len(r)]) for r, h in pairs.values()),
        },
    }
    for block in transforms.values():
        block["delta_vs_sealed_pct"] = round(block["corpus_wer_pct"] - baseline_pct, 4)

    minimum_duration = {}
    for cut in (1.0, 2.0, 3.0):
        ids = [sid for sid in pairs if float(items[sid]["audio_seconds"]) >= cut]
        block = corpus(pairs[sid] for sid in ids)
        block["utterances"] = len(ids)
        block["delta_vs_sealed_pct"] = round(block["corpus_wer_pct"] - baseline_pct, 4)
        minimum_duration[f"at_least_{cut:.0f}s"] = block

    empty_reference = [sid for sid in pairs if not pairs[sid][0]]
    cjk = [
        sid
        for sid in outputs
        if any("\u2e80" <= ch <= "\u9fff" for ch in outputs[sid])
    ]
    return {
        "sealed_corpus_wer_pct": baseline_pct,
        "boundary": (
            "Every figure in this file is a DIAGNOSTIC computed after the fact on sealed "
            "outputs. None of it is the verdict, none of it was fitted, and the two "
            "transforms marked oracle = true use the reference's own length and are upper "
            "bounds on a component rather than achievable numbers."
        ),
        "length": {
            "reference_words": reference_words,
            "hypothesis_words": hypothesis_words,
            "ratio": round(hypothesis_words / reference_words, 4),
            "utterances_with_a_longer_hypothesis": longer,
            "utterances_with_a_shorter_hypothesis": shorter,
            "excess_hypothesis_tokens": sum(
                max(0, len(h) - len(r)) for r, h in pairs.values()
            ),
        },
        "by_duration_bucket": buckets,
        "transforms": transforms,
        "minimum_duration": minimum_duration,
        "empty_reference_after_normalization": {
            "ids": sorted(empty_reference),
            "count": len(empty_reference),
            "hypothesis_words_counted_as_insertions": sum(
                len(pairs[sid][1]) for sid in empty_reference
            ),
            "note": (
                "a reference that normalizes to nothing (an isolated 'Um.', "
                "'mm-hmm <affirmative>.' or '<inaudible>.') contributes zero reference "
                "words to the denominator while any hypothesis words it draws are counted "
                "as insertions in the numerator. Four rows of 2,735; the effect on the "
                "corpus figure is a few hundredths of a point and is recorded rather than "
                "removed."
            ),
        },
        "non_english_hypotheses": {
            "ids": sorted(cjk),
            "count": len(cjk),
            "note": (
                "hypotheses containing CJK-range characters, all on sub-second clips. A "
                "real defect of the frozen core on near-empty audio, three rows of 2,735."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1")
    parser.add_argument("--flight-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=CHECK / "verdict")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")),
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    scores = json.loads((run_dir / f"{args.run_id}.scores.json").read_text(encoding="utf-8"))
    manifest_path = run_dir / f"{args.run_id}.run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    receipt = json.loads(Path(args.flight_receipt).read_text(encoding="utf-8"))
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    items = {item["sample_id"]: item for item in roster["items"]}

    outputs = {
        json.loads(line)["sample_id"]: json.loads(line)["text"]
        for line in (run_dir / f"{args.run_id}.outputs.jsonl")
        .read_text(encoding="utf-8")
        .split("\n")
        if line.strip()
    }

    batch_files = sorted((run_dir / "score-batch").glob("*.score.json"))
    batch = json.loads(batch_files[0].read_text(encoding="utf-8")) if batch_files else {}
    batch_scores = batch.get("scores", batch.get("results", {}))
    batch_verified = batch.get("verified")

    whisper = scores["asr-wer-esb-whisper"]
    frozen = scores["asr-wer-esb"]
    whisper_rows = list(whisper["per_sample"])
    frozen_rows = list(frozen["per_sample"])
    assert len(whisper_rows) == len(items), (len(whisper_rows), len(items))

    overall_whisper = _corpus(whisper_rows)
    overall_frozen = _corpus(frozen_rows)
    W = overall_whisper["corpus_wer_pct"]

    calls = sorted({item["parent_sample_id"] for item in items.values()})
    per_call: dict[str, Any] = {}
    for call in calls:
        ids = {sid for sid, item in items.items() if item["parent_sample_id"] == call}
        wr = [row for row in whisper_rows if row["sample_id"] in ids]
        fr = [row for row in frozen_rows if row["sample_id"] in ids]
        per_call[call] = {
            "whisper": _corpus(wr),
            "frozen": _corpus(fr),
            "audio_seconds": round(
                sum(float(items[sid]["audio_seconds"]) for sid in ids), 3
            ),
        }
    equal_call = round(
        statistics.fmean(per_call[call]["whisper"]["corpus_wer_pct"] for call in calls), 4
    )

    ordered = sorted(items.values(), key=lambda item: float(item["audio_seconds"]))
    by_id = {row["sample_id"]: row for row in whisper_rows}
    deciles = []
    size = len(ordered)
    for index in range(10):
        lo = index * size // 10
        hi = (index + 1) * size // 10
        chunk = ordered[lo:hi]
        if not chunk:
            continue
        rows = [by_id[item["sample_id"]] for item in chunk]
        deciles.append(
            {
                "decile": index + 1,
                "seconds_from": round(float(chunk[0]["audio_seconds"]), 3),
                "seconds_to": round(float(chunk[-1]["audio_seconds"]), 3),
                **_corpus(rows),
            }
        )

    long_ids = [sid for sid, item in items.items() if float(item["audio_seconds"]) > 20.0]
    short_ids = [sid for sid in items if sid not in set(long_ids)]
    long_block = _corpus([by_id[sid] for sid in long_ids])
    short_block = _corpus([by_id[sid] for sid in short_ids])

    clamped = sorted(
        sid for sid in roster.get("clamped_to_decoded_parent", []) if sid in by_id
    )
    clamped_rows = [
        {
            "sample_id": sid,
            "audio_seconds": float(items[sid]["audio_seconds"]),
            "segment_end_seconds": float(items[sid]["segment_end_seconds"]),
            "parent_decoded_seconds": float(items[sid]["parent_decoded_seconds"]),
            "whisper_wer_pct": round(100.0 * float(by_id[sid]["wer"]), 4),
            "reference_words": len(by_id[sid]["ref_hit_mask"]),
        }
        for sid in clamped
    ]

    band_pass = W <= PAPER_WER + BAND
    strict_pass = W <= STRICT_FLOOR
    better = W < PAPER_WER - BAND
    verdict = "ALIGNED-BETTER" if better else ("ALIGNED" if (band_pass and strict_pass) else "NOT ALIGNED")

    stages = receipt["stages"]
    summary = {
        "schema": "saea-e22-esb-result-summary-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "attempt_id": receipt["attempt_id"],
        "cell_id": receipt["cell_id"],
        "study_commit": stages["preflight"]["study_commit"],
        "config_hash": stages["preflight"]["config_hash"],
        "protocol_hash": stages["preflight"]["protocol_hash"],
        "split_identity_hash": stages["preflight"]["split_identity_hash"],
        "manifest_sha256": stages["seal"]["manifest_sha256"],
        "manifest_path_sha256_recomputed": sha256_file(manifest_path),
        "attempt_state": stages["seal"]["finalize"]["attempt_state"],
        "build_commit": "04ccc72a2207347ca76161b93fd9d846dd0a8675",
        "config_fragments": {
            "model": "q4km-e22-esb-mmproj-gpu-04ccc72a-np8",
            "dataset": "earnings22-esb-utterances-2735",
            "baseline": "e22-esb-direct-zero",
            "experiment": "e22-esb-shortform-alignment-v1",
        },
        "scoring_path": {
            "scorers_declared": manifest.get("scorers"),
            "paper_facing_scorer": "asr-wer-esb-whisper",
            "aggregation": "corpus: total S+D+I over total reference words",
            "scoring_batch_verified": batch_verified,
            "scoring_batch_aggregates": {
                name: value.get("aggregate")
                for name, value in (batch_scores.items() if isinstance(batch_scores, dict) else [])
                if isinstance(value, dict) and "aggregate" in value
            },
            "whole_manifest_jobs_only": True,
            "dataset_sharding": False,
            "merge_compounds": False,
        },
        "headline": {
            "corpus_wer_whisper_pct": W,
            "mean_of_per_utterance_wer_whisper_pct": overall_whisper["mean_wer_pct"],
            "corpus_wer_saea_scoring_v1_pct": overall_frozen["corpus_wer_pct"],
            "mean_of_per_utterance_wer_saea_scoring_v1_pct": overall_frozen["mean_wer_pct"],
            "equal_call_weighted_whisper_pct": equal_call,
        },
        "counts_whisper": overall_whisper,
        "counts_saea_scoring_v1": overall_frozen,
        "decision": {
            "rule": (
                "ALIGNED = corpus Whisper-normalized WER <= 12.79 (9.79 + 3) AND <= the strict "
                "whisper-large-v3 floor 11.59; ALIGNED-BETTER = < 6.79; otherwise NOT ALIGNED"
            ),
            "band_test_threshold": PAPER_WER + BAND,
            "band_test_pass": band_pass,
            "strict_floor_threshold": STRICT_FLOOR,
            "strict_floor_pass": strict_pass,
            "loose_floor_threshold": LOOSE_FLOOR,
            "loose_floor_pass": W <= LOOSE_FLOOR,
            "aligned_better_threshold": PAPER_WER - BAND,
            "verdict": verdict,
            "delta_vs_published": round(W - PAPER_WER, 4),
            "delta_vs_cross_read": round(W - CROSS_READ_WER, 4),
            "floors": {
                name: {"published": value, "cleared": W <= value} for name, value in FLOORS.items()
            },
        },
        "targets": {
            "published_same_model": PAPER_WER,
            "published_source": "NVIDIA NeMo AutoModel, 'Fine-Tune Qwen3-Omni for ASR', N = 2741",
            "cross_read_same_model": CROSS_READ_WER,
            "cross_read_source": "Nemotron 3 Nano Omni, arXiv:2604.24954v2 Table 8",
            "vendor_disagreement_points": round(CROSS_READ_WER - PAPER_WER, 2),
        },
        "per_call": per_call,
        "duration_deciles_whisper": deciles,
        "duration_split_whisper": {
            "longer_than_20s": {"count": len(long_ids), **long_block},
            "at_most_20s": {"count": len(short_ids), **short_block},
        },
        "clamped_utterances": clamped_rows,
        "earnings21_full44_for_contrast": {
            "corpus_wer_whisper_pct": E21_FULL44_CORPUS,
            "run_id": "SAEA-E21-FULL44-DIRECT-BASELINE-V2",
            "why_not_a_comparison": (
                "different corpus (Earnings-21 discovery, 44 calls), different segmentation "
                "(fixed 90-second long-form windows, transcripts stitched per call) and a "
                "different reference layer (the carrier's own .nlp tokens). The two numbers are "
                "printed side by side as context, never as a difference."
            ),
        },
        "cost": stages["seal"]["cost"],
        "throughput": {
            key: stages["run_phases"][key]
            for key in (
                "contact_count",
                "wall_seconds",
                "average_latency_seconds",
                "contacts_per_second",
                "slot_occupancy",
                "serving_slots",
            )
        },
        "serve": {
            "extra_argv": stages["serve"]["extra_argv"],
            "startup_seconds": stages["serve"]["startup_seconds"],
        },
        "caveats": [
            "Two vendor reports of this same frozen model differ by 2.5 points (9.79 vs 12.3), "
            "most of the owner's 3-point tolerance; 'consistent with both' is the strongest "
            "honest reading of any number inside that spread.",
            "The Open ASR Leaderboard applies merge_compounds=True; this repository does not. "
            "That works against us.",
            "The published row's precision and prompt are not published. Q4_K_M and this study's "
            "own three-sentence ASR instruction are named deviations, not controls.",
            "2,735 rows against the published N = 2,741. The six-row gap is unexplained and is "
            "recorded, never reconciled by guesswork.",
            "Utterances were cut locally from the locked MP3s at the published float32 "
            "boundaries, not from the release's own audio chunks; three end boundaries fall past "
            "the decoded parent and were clamped to it.",
            "fstalign was not installed and not run.",
            "saea-scoring-v1 figures are a different metric family and must never be reported as "
            "an alignment however close they land.",
        ],
    }

    references = {
        json.loads(line)["sample_id"]: json.loads(line)["sentence"]
        for line in (
            Path(args.data_root)
            / "derived/e22-esb-segment-table/e22-esb-test-references.jsonl"
        )
        .read_text(encoding="utf-8")
        .split("\n")
        if line.strip()
    }
    decomposition = _decompose(references, outputs, items, W)
    truncated = decomposition["transforms"]["hypothesis_truncated_to_reference_length"]
    summary["gap_decomposition_headline"] = {
        "over_generation_is_the_gap": (
            "cutting each hypothesis to its own reference word count -- an ORACLE "
            "transform, not an achievable result -- moves the corpus figure by "
            f"{truncated['delta_vs_sealed_pct']} points. Over-generation therefore "
            "accounts for most of the distance to the published number; immediate word "
            "repetition and the shortest utterances account for well under a point each."
        ),
        "hypothesis_to_reference_word_ratio": decomposition["length"]["ratio"],
        "insertions_share_of_all_errors_pct": round(
            100.0 * overall_whisper["insertions"] / overall_whisper["errors"], 2
        ),
        "oracle_truncation_corpus_wer_pct": truncated["corpus_wer_pct"],
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "gap-decomposition.json").write_text(
        json.dumps(decomposition, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output_dir / "result-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    lines = [
        "# Earnings-22 ESB short-form: per-call table",
        "",
        f"Run `{args.run_id}`, attempt `{receipt['attempt_id']}`, study commit "
        f"`{stages['preflight']['study_commit'][:8]}`. Paper-facing scorer `asr-wer-esb-whisper`, "
        "corpus aggregation (total S+D+I over total reference words).",
        "",
        "| call | utterances | audio s | ref words | S | D | I | corpus WER % (Whisper) | mean per-utt % | corpus WER % (saea-scoring-v1) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for call in calls:
        w = per_call[call]["whisper"]
        f = per_call[call]["frozen"]
        lines.append(
            f"| {call} | {w['utterances']} | {per_call[call]['audio_seconds']:.1f} | "
            f"{w['reference_words']} | {w['substitutions']} | {w['deletions']} | "
            f"{w['insertions']} | **{w['corpus_wer_pct']:.3f}** | {w['mean_wer_pct']:.3f} | "
            f"{f['corpus_wer_pct']:.3f} |"
        )
    lines.append(
        f"| **all six** | **{overall_whisper['utterances']}** | "
        f"**{roster['audio_seconds_total']:.1f}** | **{overall_whisper['reference_words']}** | "
        f"**{overall_whisper['substitutions']}** | **{overall_whisper['deletions']}** | "
        f"**{overall_whisper['insertions']}** | **{W:.3f}** | "
        f"**{overall_whisper['mean_wer_pct']:.3f}** | "
        f"**{overall_frozen['corpus_wer_pct']:.3f}** |"
    )
    lines += [
        "",
        f"Equal-call weighting (mean of the six per-call corpus figures): **{equal_call:.3f} %**. "
        f"Natural mixture (the corpus figure above): **{W:.3f} %**.",
        "",
        "## By utterance duration (Whisper normalizer, corpus)",
        "",
        "| decile | seconds | utterances | ref words | corpus WER % |",
        "|---:|---|---:|---:|---:|",
    ]
    for row in deciles:
        lines.append(
            f"| {row['decile']} | {row['seconds_from']:.2f}-{row['seconds_to']:.2f} | "
            f"{row['utterances']} | {row['reference_words']} | {row['corpus_wer_pct']:.3f} |"
        )
    lines += [
        "",
        f"Longer than 20 s: {long_block['utterances']} utterances, "
        f"{long_block['reference_words']} reference words, corpus WER "
        f"{long_block['corpus_wer_pct']:.3f} %. At most 20 s: {short_block['utterances']} "
        f"utterances, {short_block['reference_words']} reference words, corpus WER "
        f"{short_block['corpus_wer_pct']:.3f} %.",
        "",
        "## The three clamped utterances",
        "",
        "| id | cut seconds | published end | decoded parent | ref words | WER % |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in clamped_rows:
        lines.append(
            f"| {row['sample_id']} | {row['audio_seconds']:.3f} | "
            f"{row['segment_end_seconds']:.3f} | {row['parent_decoded_seconds']:.3f} | "
            f"{row['reference_words']} | {row['whisper_wer_pct']:.3f} |"
        )
    lines.append("")
    (output_dir / "per-call-table.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps(summary["headline"], indent=2))
    print(json.dumps(summary["decision"], indent=2)[:900])
    print("wrote", output_dir / "result-summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
