#!/usr/bin/env python3
"""Verdict reader for SAEA-E21-FULL44-DIRECT-BASELINE-V1.

Zero contact: reads only the flight's own sealed artifacts (its run manifest,
the ``core.scoring_batch`` verified score read beside it) plus the committed
roster receipt, and emits ``result-summary.json`` and the markdown tables the
preregistration's section 8 makes mandatory.

Everything the preregistration promised is computed here and nowhere else:

* the per-call table for all 44 calls, including ``4346923``;
* corpus WER under the Whisper ``EnglishTextNormalizer`` (the paper-facing
  number) and the mean of per-call WER beside it, plus the same pair under the
  frozen ``saea-scoring-v1`` metric;
* the ``4346923`` effect, as an explicit delta;
* the ten sealed calls re-measured on this build against their sealed 7.137;
* sector and sample-rate strata in natural-mixture and equal-stratum weightings;
* entity WER by class with each class's gold mention count;
* throughput, and the preregistered alignment verdict.

Usage:
    python scripts/e21_full44_analysis.py \
        --manifest <flight run-manifest.json> \
        --score-read <score-batch score-read json> \
        --roster docs/checks/.../flight-roster-receipt.json \
        --output-dir docs/checks/.../verdict/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

WHISPER_TARGET = 9.71
BAND = 3.0
STRICT_FLOOR = 10.2
LOOSE_FLOOR = 12.5
FLOORS = {
    "Whisper medium.en": 10.2,
    "Whisper small.en": 10.8,
    "Whisper base.en": 12.5,
    "Whisper tiny.en": 17.0,
    "FastConformer FT+LCA+GT": 13.84,
    "Qwen2-Audio-7B": 26.06,
}
PATHOLOGICAL = "4346923"
SEALED_TEN_CORPUS_WHISPER = 7.137
SEALED_TEN = {
    "4330115",
    "4365024",
    "4365948",
    "4366429",
    "4366522",
    "4384964",
    "4385072",
    "4387383",
    "4389907",
    "4397829",
}


def _corpus(rows: list[dict[str, object]]) -> dict[str, float]:
    subs = sum(int(row["substitutions"]) for row in rows)
    dele = sum(int(row["deletions"]) for row in rows)
    ins = sum(int(row["insertions"]) for row in rows)
    hits = sum(int(row["hits"]) for row in rows)
    ref = hits + subs + dele
    return {
        "substitutions": subs,
        "deletions": dele,
        "insertions": ins,
        "hits": hits,
        "reference_words": ref,
        "corpus_wer_pct": round(100.0 * (subs + dele + ins) / ref, 4) if ref else 0.0,
        # unrounded, for the identity check against the scorer's own aggregate
        "corpus_wer_exact": ((subs + dele + ins) / ref) if ref else 0.0,
        "mean_of_per_call_wer_pct": (
            round(100.0 * sum(float(row["wer"]) for row in rows) / len(rows), 4)
            if rows
            else 0.0
        ),
        "calls": len(rows),
    }


def _scorer_rows(score_read: dict, scorer: str) -> dict[str, dict]:
    block = score_read[scorer]
    return {str(row["sample_id"]): row for row in block["per_sample"]}


def _load_score_read(path: Path) -> dict:
    """Read the ``<job_id>.score.json`` a ``core.scoring_batch
    --include-per-sample`` job writes: the driver's own verified
    ``score --manifest`` payload, shaped
    ``{"manifest": ..., "verified": true, "scores": {<scorer>: {...}}}``.

    An unverified payload is refused outright. ``core.driver._cli_score`` tags
    the ad-hoc ``--outputs`` path ``"verified": false`` precisely so nothing
    downstream can mistake it for an audit record, and a paper-facing number may
    only ever come off the verified path."""

    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("verified") is not True:
        raise SystemExit(f"{path} is not a verified score read; refusing to report it")
    scores = document.get("scores")
    if not isinstance(scores, dict):
        raise SystemExit(f"{path} carries no scores block")
    return scores


def build(args: argparse.Namespace) -> dict:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    score_read = _load_score_read(Path(args.score_read))
    roster = json.loads(Path(args.roster).read_text(encoding="utf-8"))
    meta = {str(call["sample_id"]): call for call in roster["calls"]}

    whisper = _scorer_rows(score_read, "asr-wer-whisper")
    saea = _scorer_rows(score_read, "asr-wer")
    entity = _scorer_rows(score_read, "entity-wer")
    ids = sorted(whisper)
    if len(ids) != 44:
        raise SystemExit(f"expected 44 scored calls, got {len(ids)}")

    per_call = []
    for sample_id in ids:
        w = whisper[sample_id]
        s = saea[sample_id]
        e = entity[sample_id]
        m = meta[sample_id]
        per_call.append(
            {
                "sample_id": sample_id,
                "company": m["company_name"],
                "sector": m["sector"],
                "sample_rate_hz": m["sample_rate_hz"],
                "minutes": m["audio_minutes"],
                "windows": m["fixed_90s_windows"],
                "in_sealed_ten": sample_id in SEALED_TEN,
                "whisper_wer_pct": round(100.0 * float(w["wer"]), 3),
                "whisper_substitutions": int(w["substitutions"]),
                "whisper_deletions": int(w["deletions"]),
                "whisper_insertions": int(w["insertions"]),
                "whisper_reference_words": int(w["hits"])
                + int(w["substitutions"])
                + int(w["deletions"]),
                "saea_wer_pct": round(100.0 * float(s["wer"]), 3),
                "entity_wer_pct": round(100.0 * float(e["entity_wer"]), 3),
                "entity_expected_total": int(e["expected_total"]),
            }
        )

    all_rows = [whisper[i] for i in ids]
    no_path = [whisper[i] for i in ids if i != PATHOLOGICAL]
    ten_rows = [whisper[i] for i in ids if i in SEALED_TEN]
    other_rows = [whisper[i] for i in ids if i not in SEALED_TEN]

    corpus_all = _corpus(all_rows)
    corpus_no_path = _corpus(no_path)
    corpus_ten = _corpus(ten_rows)
    corpus_other = _corpus(other_rows)

    saea_all = _corpus([saea[i] for i in ids])

    aggregate_reported = score_read["asr-wer-whisper"]["aggregate"]
    recomputed = corpus_all["corpus_wer_exact"]
    if abs(recomputed - float(aggregate_reported["corpus_wer"])) > 1e-9:
        raise SystemExit(
            "recomputed corpus WER disagrees with the scorer's own aggregate: "
            f"{recomputed} vs {aggregate_reported['corpus_wer']}"
        )

    def _stratum(key: str) -> dict:
        buckets: dict[str, list[dict]] = {}
        for sample_id in ids:
            buckets.setdefault(str(meta[sample_id][key]), []).append(whisper[sample_id])
        table = {name: _corpus(rows) for name, rows in sorted(buckets.items())}
        equal = round(
            sum(value["corpus_wer_pct"] for value in table.values()) / len(table), 4
        )
        return {
            "per_stratum": table,
            "natural_mixture_corpus_wer_pct": corpus_all["corpus_wer_pct"],
            "equal_stratum_mean_of_stratum_corpus_wer_pct": equal,
        }

    entity_aggregate = score_read["entity-wer"]["aggregate"]
    entity_by_class = {
        name: {
            "entity_wer_pct": round(100.0 * float(value["entity_wer"]), 3),
            "gold_mentions": int(value["expected_total"]),
        }
        for name, value in sorted(entity_aggregate["by_entity_type"].items())
    }

    corpus_wer_pct = corpus_all["corpus_wer_pct"]
    band_pass = corpus_wer_pct <= WHISPER_TARGET + BAND
    floor_pass = corpus_wer_pct <= STRICT_FLOOR
    if corpus_wer_pct < WHISPER_TARGET - BAND:
        verdict = "ALIGNED-BETTER"
    elif band_pass and floor_pass:
        verdict = "ALIGNED"
    else:
        verdict = "NOT ALIGNED"

    cost = manifest["cost"]
    gpu_seconds = cost.get("gpu_seconds")
    summary = {
        "schema": "saea-e21-full44-result-summary-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": manifest["run_id"],
        "attempt_id": manifest["attempt"]["attempt_id"],
        "study_commit": manifest["study_commit"],
        "status": manifest["status"],
        "config_hash": manifest["config"]["config_hash"],
        "protocol_hash": manifest["protocol_hash"],
        "config_fragments": manifest["config"]["fragments"],
        "manifest_scorers": manifest["scorers"],
        "split": {
            key: manifest["split"][key]
            for key in ("carrier_lock_key", "count", "identity_hash", "name", "role")
        },
        "build_commit": "04ccc72a2207347ca76161b93fd9d846dd0a8675",
        "paper_facing": {
            "metric": (
                "corpus WER, Whisper EnglishTextNormalizer on both sides, whitespace "
                "tokenization, total S+D+I over total reference words"
            ),
            "scorer": "asr-wer-whisper",
            "corpus_wer_pct": corpus_wer_pct,
            "mean_of_per_call_wer_pct": corpus_all["mean_of_per_call_wer_pct"],
            "reference_words": corpus_all["reference_words"],
            "substitutions": corpus_all["substitutions"],
            "deletions": corpus_all["deletions"],
            "insertions": corpus_all["insertions"],
        },
        "saea_scoring_v1": {
            "metric": "frozen saea-scoring-v1 normalize_text_v1 / tokens_v1",
            "corpus_wer_pct": saea_all["corpus_wer_pct"],
            "mean_of_per_call_wer_pct": saea_all["mean_of_per_call_wer_pct"],
            "reference_words": saea_all["reference_words"],
            "comparability": (
                "NOT comparable to any published Earnings-21 row: a different metric "
                "family. Reported for continuity with this repository's own history"
            ),
        },
        "pathological_call_effect": {
            "sample_id": PATHOLOGICAL,
            "company": meta[PATHOLOGICAL]["company_name"],
            "sector": meta[PATHOLOGICAL]["sector"],
            "sample_rate_hz": meta[PATHOLOGICAL]["sample_rate_hz"],
            "minutes": meta[PATHOLOGICAL]["audio_minutes"],
            "its_own_whisper_wer_pct": round(
                100.0 * float(whisper[PATHOLOGICAL]["wer"]), 3
            ),
            "corpus_with_it_pct": corpus_wer_pct,
            "corpus_without_it_pct": corpus_no_path["corpus_wer_pct"],
            "delta_pct_points": round(
                corpus_wer_pct - corpus_no_path["corpus_wer_pct"], 4
            ),
        },
        "sealed_ten_contrast": {
            "these_ten_on_this_build_corpus_wer_pct": corpus_ten["corpus_wer_pct"],
            "sealed_2026_08_14_corpus_wer_pct": SEALED_TEN_CORPUS_WHISPER,
            "delta_pct_points": round(
                corpus_ten["corpus_wer_pct"] - SEALED_TEN_CORPUS_WHISPER, 4
            ),
            "what_the_delta_confounds": (
                "build 5d9dfcb58 -> 04ccc72a and mmproj CPU -> GPU, together; the two "
                "were changed in the same step and this flight does not separate them"
            ),
            "the_other_34_corpus_wer_pct": corpus_other["corpus_wer_pct"],
        },
        "strata": {
            "by_sector": _stratum("sector"),
            "by_sample_rate_hz": _stratum("sample_rate_hz"),
        },
        "entity_wer": {
            "definition": (
                "mention-level 1 - recall over the .nlp wer_tags sidecar under the "
                "frozen normalize_text_v1 (NOT the Whisper normalizer); precision is "
                "1.0 by construction, so only the recall-derived error rate carries "
                "information"
            ),
            "corpus_entity_wer_pct": round(
                100.0 * float(entity_aggregate["entity_wer"]), 3
            ),
            "gold_mentions": int(entity_aggregate["expected_total"]),
            "macro_entity_wer_pct": round(
                100.0 * float(entity_aggregate["macro_entity_wer"]), 3
            ),
            "by_class": entity_by_class,
        },
        "targets": {
            "primary": {"system": "openai/whisper-large-v3", "wer": WHISPER_TARGET},
            "delta_vs_primary_pct_points": round(corpus_wer_pct - WHISPER_TARGET, 4),
            "others": {
                "Whisper large-v2": 9.7,
                "TRADE speech-LLM": 9.75,
                "FastConformer FT+LCA+GT": 13.84,
                "Qwen2-Audio-7B (normalizer unnamed; floor only)": 26.06,
            },
        },
        "floors": {
            name: {
                "published_wer": value,
                "cleared": corpus_wer_pct <= value,
            }
            for name, value in FLOORS.items()
        },
        "decision": {
            "rule": (
                "ALIGNED = corpus Whisper-normalized WER <= 12.71 AND <= the strict "
                "medium.en floor 10.2; ALIGNED-BETTER = < 6.71; otherwise NOT ALIGNED"
            ),
            "band_test_threshold": WHISPER_TARGET + BAND,
            "band_test_pass": band_pass,
            "strict_floor_threshold": STRICT_FLOOR,
            "strict_floor_pass": floor_pass,
            "loose_floor_threshold": LOOSE_FLOOR,
            "loose_floor_pass": corpus_wer_pct <= LOOSE_FLOOR,
            "verdict": verdict,
        },
        "caveats": [
            "Whisper's own long-form decoding heuristics move Earnings-21 by 1.1 points "
            "(10.7 greedy to 9.63 with previous-text conditioning, Whisper Table 7), so "
            "a 3-point band around 9.71 is about three times the reference literature's "
            "own protocol spread.",
            "The Open ASR Leaderboard applies merge_compounds=True; this repository does "
            "not. That works against us.",
            "fstalign was not installed and not run; no number here is comparable to "
            "ConEC's fstalign-based table.",
            "Cross-system comparison against third-party published rows, never a "
            "reproduction: no Qwen-published Earnings-21 number exists.",
            "saea-scoring-v1 corpus figures landing near 9.71 would be a coincidence "
            "between two unrelated normalizers and must never be read as an alignment.",
        ],
        "cost": {
            "calls_used": cost["calls_used"],
            "audio_seconds_used": cost["audio_seconds_used"],
            "audio_hours_used": round(float(cost["audio_seconds_used"]) / 3600.0, 4),
            "prompt_tokens_total": cost["prompt_tokens_total"],
            "completion_tokens_total": cost["completion_tokens_total"],
            "gpu_seconds": gpu_seconds,
            "gpu_hours": (
                round(float(gpu_seconds) / 3600.0, 4)
                if isinstance(gpu_seconds, (int, float))
                else gpu_seconds
            ),
            "cpu_seconds": cost["cpu_seconds"],
            "peak_vram_mib": cost["peak_vram_mib"],
            "latency_seconds_total": cost["latency_seconds_total"],
            "skipped_slice_count": cost["skipped_slice_count"],
            "saturated_slice_count": cost["saturated_slice_count"],
        },
        "per_call": per_call,
    }
    return summary


def _markdown(summary: dict) -> str:
    lines: list[str] = []
    lines.append("| call | company | sector | kHz | min | win | Whisper WER % | S | D | I | ref words | saea-v1 WER % | entity WER % | mentions |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in summary["per_call"]:
        mark = "*" if row["in_sealed_ten"] else ""
        lines.append(
            f"| {row['sample_id']}{mark} | {row['company']} | {row['sector']} | "
            f"{row['sample_rate_hz']} | {row['minutes']:.1f} | {row['windows']} | "
            f"{row['whisper_wer_pct']:.2f} | {row['whisper_substitutions']} | "
            f"{row['whisper_deletions']} | {row['whisper_insertions']} | "
            f"{row['whisper_reference_words']} | {row['saea_wer_pct']:.2f} | "
            f"{row['entity_wer_pct']:.2f} | {row['entity_expected_total']} |"
        )
    paper = summary["paper_facing"]
    lines.append("")
    lines.append(
        f"**All 44: corpus Whisper-normalized WER {paper['corpus_wer_pct']:.3f} %** "
        f"(S {paper['substitutions']} / D {paper['deletions']} / I {paper['insertions']} "
        f"over {paper['reference_words']} reference words); mean of per-call "
        f"{paper['mean_of_per_call_wer_pct']:.3f} %."
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--score-read", required=True)
    parser.add_argument("--roster", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary = build(args)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (out / "per-call-table.md").write_text(
        _markdown(summary), encoding="utf-8", newline="\n"
    )
    print(
        f"corpus Whisper-normalized WER {summary['paper_facing']['corpus_wer_pct']} % "
        f"-> {summary['decision']['verdict']}"
    )
    print(
        "without 4346923: "
        f"{summary['pathological_call_effect']['corpus_without_it_pct']} % "
        f"(delta {summary['pathological_call_effect']['delta_pct_points']})"
    )
    print(
        "sealed ten on this build: "
        f"{summary['sealed_ten_contrast']['these_ten_on_this_build_corpus_wer_pct']} % "
        f"vs sealed {SEALED_TEN_CORPUS_WHISPER} "
        f"(delta {summary['sealed_ten_contrast']['delta_pct_points']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
