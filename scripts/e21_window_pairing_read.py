#!/usr/bin/env python3
"""Decompose the sealed Earnings-21 full-44 baseline into its 1,593 windows and
PROVE the per-window rows re-aggregate to the sealed corpus numbers exactly.

Exposure row `SAEA-E21-MF-WINDOW-PAIRING-V1` (`model-free-check`), registered and
committed before the first file was opened. Zero model, GPU, tool, embedder,
tokenizer, network, audio-decode and paid-API contacts; no Earnings-22 read.
References and `wer_tags` are reached only through the registered scoring path's
own loaders (`data.references`, `reproduction.conec_entity_scoring`), never opened
by hand.

What it writes
--------------
* ``<rows-out>/window-rows.json`` -- one row per window: identity, audio bounds,
  the operation counts, the ConEC entity buckets, the semantic-impact levels and
  the numeric-value counts. Written under ``SPEECHRL_DATA_DIR`` by default, never
  into Git: it is a per-request derivative of sealed model outputs and belongs
  where those live.
* ``<out-dir>/reaggregation.json`` -- the committed proof: per-window sums beside
  the sealed values with a PASS/FAIL per check, the per-call numeric shortfall,
  and the rows file's own path and SHA-256.
* ``<out-dir>/README.md`` is written by hand beside it.

Nothing here decides anything. It builds the instrument the KC-E1 verdict will use
and proves it lossless.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis import e21_window_pairing as wp  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.references import (  # noqa: E402
    reference_entity_mentions,
    reference_tokens,
)
from speech_aware_evidence_acquisition.reproduction import (  # noqa: E402
    conec_entity_scoring as conec,
)
from speech_aware_evidence_acquisition.reproduction import (  # noqa: E402
    numeric_value_accuracy as numeric,
)
from speech_aware_evidence_acquisition.reproduction import semantic_impact  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.asr_wer_whisper import (  # noqa: E402
    normalize_whisper_english,
)

CARRIER = "earnings21-original"
SEALED_RUN = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"

#: One committed sealed profile per run this instrument has been asked to
#: reproduce -- the check is always a comparison against a committed claim,
#: never against whatever this run happens to compute (module docstring
#: above). ``--run-id`` selects a profile; ``--attempt-id`` overrides its
#: pinned attempt only if given.
#:
#: The comparator's numbers are quoted from
#: docs/readiness/2026-09-06-earnings-agentic-metric-baseline-v1.md sections
#: 1-3 and the sealed verdict. KC-E1's are quoted from its own sealed
#: docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-kc-e1-brief-44-v1/flight/score-read.json
#: aggregates (``asr-wer-whisper``, ``conec-entity-wer-official``,
#: ``numeric-value-accuracy-v1``, ``semantic-high-impact-error-rate-v1``),
#: rounded exactly as this script's own checks round its live computation
#: (2 decimal places for entity WER, 3 for everything else), so the two
#: rounded quotations are directly comparable.
SEALED_PROFILES: dict[str, dict[str, object]] = {
    "SAEA-E21-FULL44-DIRECT-BASELINE-V2": {
        "attempt_id": "attempt-20260904T233816Z-bcd338",
        "sealed": {
            "corpus_wer_percent": 8.200,
            "substitutions": 13098,
            "deletions": 5701,
            "insertions": 10700,
            "reference_words": 359765,
            "windows": 1593,
            "calls": 44,
            "entity_wer_percent": {
                "PERSON": 22.5,
                "ORG": 17.2,
                "GPE": 18.7,
                "LOC": 2.5,
                "PRODUCT": 19.2,
                "EVENT": 2.4,
                "NORP": 9.7,
                "FAC": 21.3,
            },
            "entity_reference_words": {
                "PERSON": 2917,
                "ORG": 4363,
                "GPE": 1537,
                "LOC": 485,
                "PRODUCT": 390,
                "EVENT": 494,
                "NORP": 236,
                "FAC": 122,
            },
            "non_entity_wer_percent": 4.730,
            "unlabelled_reference_words": 1479,
            "numeric_expected": 9734,
            "numeric_matched": 8832,
            "negation_critical_high_reference_words": 100,
            "negation_critical_high_insertions": 56,
        },
    },
    # KC-E1 (docs/checks/.../2026-09-06-e21-kc-e1-brief-44-v1/), sealed with
    # two of its 1,593 windows saturated at the 1,024-token decode cap --
    # the case docs/checks/speech-aware-evidence-acquisition/
    # 2026-09-07-e21-window-pairing-fix/ exists to prove the fixed pairing
    # instrument still reproduces exactly.
    "SAEA-E21-KC-E1-BRIEF-44-V1": {
        "attempt_id": "attempt-20260907T171238Z-f02eef",
        "sealed": {
            "corpus_wer_percent": 8.736,
            "substitutions": 13022,
            "deletions": 8393,
            "insertions": 10014,
            "reference_words": 359765,
            "windows": 1593,
            "calls": 44,
            "entity_wer_percent": {
                "PERSON": 18.34,
                "ORG": 17.99,
                "GPE": 19.52,
                "LOC": 2.68,
                "PRODUCT": 16.67,
                "EVENT": 2.43,
                "NORP": 11.86,
                "FAC": 21.31,
            },
            "entity_reference_words": {
                "PERSON": 2917,
                "ORG": 4363,
                "GPE": 1537,
                "LOC": 485,
                "PRODUCT": 390,
                "EVENT": 494,
                "NORP": 236,
                "FAC": 122,
            },
            "non_entity_wer_percent": 5.507,
            "unlabelled_reference_words": 1479,
            "numeric_expected": 9734,
            "numeric_matched": 8779,
            "negation_critical_high_reference_words": 120,
            "negation_critical_high_insertions": 43,
        },
    },
}

DEFAULT_DATA_ROOT = Path(
    os.environ.get(
        "SPEECHRL_DATA_DIR", "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data"
    )
)


def _outputs_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _close(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--run-id", default=SEALED_RUN)
    parser.add_argument(
        "--attempt-id",
        default=None,
        help="overrides the selected run's pinned sealed attempt id",
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--rows-out",
        type=Path,
        default=None,
        help=(
            "where the per-window rows go (default: "
            "$SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/window-rows.json); "
            "never inside the repository"
        ),
    )
    args = parser.parse_args(argv)
    if args.run_id not in SEALED_PROFILES:
        raise SystemExit(
            f"no committed sealed profile for run {args.run_id!r}; add one to "
            "SEALED_PROFILES in this script before checking it"
        )
    profile = SEALED_PROFILES[args.run_id]
    attempt_id = args.attempt_id or profile["attempt_id"]
    sealed = profile["sealed"]
    rows_path = args.rows_out or (
        args.data_root / "runs" / "SAEA-E21-MF-WINDOW-PAIRING-V1" / "window-rows.json"
    )

    started = time.time()
    attempt_dir = args.data_root / "runs" / args.run_id / attempt_id
    outputs_path = attempt_dir / f"{args.run_id}.outputs.jsonl"
    trace_path = attempt_dir / f"{args.run_id}.trace.jsonl"

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    taxonomy = semantic_impact.load_taxonomy(
        REPO_ROOT / semantic_impact.ACTIVE_TAXONOMY_RELPATH
    )

    outputs = _outputs_rows(outputs_path)
    outputs_text = {str(row["sample_id"]): str(row["text"]) for row in outputs}
    windows = wp.stitched_windows_from_trace(trace_path)
    wp.assert_stitch_reproduces_outputs(windows, outputs_text)

    rows: list[dict] = []
    entity_bucket_rows: list[dict] = []
    semantic_rows: list[dict] = []
    numeric_rows: list[dict] = []
    call_numeric_rows: list[dict] = []
    per_call: list[dict] = []

    for sample_id in sorted(windows):
        spans = windows[sample_id]
        raw_tokens = reference_tokens(lock, args.data_root, CARRIER, sample_id)
        mentions = reference_entity_mentions(lock, args.data_root, CARRIER, sample_id)

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
        conec.operation_counts(operations, len(whole_words), len(hypothesis_words))

        boundaries = wp.hypothesis_window_boundaries(spans, normalize_whisper_english)
        if boundaries[-1] != len(hypothesis_words):
            raise SystemExit(
                f"sample {sample_id}: prefix boundaries end at {boundaries[-1]} but the "
                f"scorer aligned {len(hypothesis_words)} hypothesis words"
            )
        charged = wp.charge_operations_to_windows(
            operations, boundaries, len(hypothesis_words)
        )

        call_numeric = numeric.numeric_value_counts(whole_words, hypothesis_words)
        call_numeric["sample_id"] = sample_id
        call_numeric_rows.append(call_numeric)

        window_matched = 0
        for span, window_operations in zip(spans, charged):
            buckets = conec.entity_wer_buckets(window_operations, transferred, entity_types)
            impact = semantic_impact.semantic_impact_counts(
                window_operations, whole_words, hypothesis_words, taxonomy
            )
            ref_words = [whole_words[i] for i in wp.reference_indices(window_operations)]
            hyp_words = [hypothesis_words[i] for i in wp.hypothesis_indices(window_operations)]
            numeric_counts = numeric.numeric_value_counts(ref_words, hyp_words)
            window_matched += int(numeric_counts["matched_numeric_words"])

            overall = buckets[conec.OVERALL_BUCKET]
            row = span.as_dict()
            row.update(
                {
                    "substitutions": overall["substitutions"],
                    "deletions": overall["deletions"],
                    "insertions": overall["insertions"],
                    "errors": overall["errors"],
                    "reference_words": overall["reference_words"],
                    "hypothesis_words": len(hyp_words),
                    "wer": overall["wer"],
                    "person_entity_wer": buckets.get("PERSON", {}).get("wer", 0.0),
                    "person_reference_words": buckets.get("PERSON", {}).get(
                        "reference_words", 0
                    ),
                    "person_errors": buckets.get("PERSON", {}).get("errors", 0),
                    "org_entity_wer": buckets.get("ORG", {}).get("wer", 0.0),
                    "org_reference_words": buckets.get("ORG", {}).get("reference_words", 0),
                    "org_errors": buckets.get("ORG", {}).get("errors", 0),
                    "numeric_expected": numeric_counts["expected_numeric_words"],
                    "numeric_matched": numeric_counts["matched_numeric_words"],
                    "numeric_hypothesis": numeric_counts["hypothesis_numeric_words"],
                    "numeric_accuracy": numeric_counts["accuracy"],
                    "negation_critical_reference_words": impact[
                        "high_impact_reference_words"
                    ],
                    "negation_critical_error_rate": impact["high_impact_error_rate"],
                    "negation_critical_insertions": impact["high_impact_insertions"],
                }
            )
            rows.append(row)
            entity_bucket_rows.append(buckets)
            semantic_rows.append(impact)
            numeric_rows.append(numeric_counts)

        per_call.append(
            {
                "sample_id": sample_id,
                "windows": len(spans),
                "call_numeric_matched": call_numeric["matched_numeric_words"],
                "window_numeric_matched": window_matched,
                "numeric_matched_shortfall": int(call_numeric["matched_numeric_words"])
                - window_matched,
            }
        )

    aggregate = wp.aggregate_window_rows(rows)
    entity_totals = wp.aggregate_entity_buckets(entity_bucket_rows)
    semantic_totals = semantic_impact.merge_semantic_counts(semantic_rows, taxonomy)
    numeric_totals = numeric.merge_numeric_counts(numeric_rows)
    call_numeric_totals = numeric.merge_numeric_counts(call_numeric_rows)

    checks: list[dict] = []

    def check(name: str, actual, expected, ok: bool, note: str = "") -> None:
        checks.append(
            {
                "check": name,
                "actual": actual,
                "expected": expected,
                "verdict": "PASS" if ok else "FAIL",
                **({"note": note} if note else {}),
            }
        )

    check("windows", aggregate["windows"], sealed["windows"],
          aggregate["windows"] == sealed["windows"])
    check("calls", len(windows), sealed["calls"], len(windows) == sealed["calls"])
    for key in ("substitutions", "deletions", "insertions", "reference_words"):
        check(key, aggregate[key], sealed[key], aggregate[key] == sealed[key])
    corpus = aggregate["corpus_wer"] * 100.0
    check("corpus_wer_percent", round(corpus, 3), sealed["corpus_wer_percent"],
          _close(corpus, sealed["corpus_wer_percent"], 0.0005))
    overall_bucket = entity_totals[conec.OVERALL_BUCKET]
    check("conec_all_bucket_wer_percent", round(overall_bucket["wer"] * 100.0, 3),
          sealed["corpus_wer_percent"],
          _close(overall_bucket["wer"] * 100.0, sealed["corpus_wer_percent"], 0.0005),
          "the ConEC mirror's own __ALL__ anchor, re-derived from window rows")
    for entity, expected in sealed["entity_wer_percent"].items():
        bucket = entity_totals.get(entity, {"wer": 0.0, "reference_words": 0})
        check(f"entity_wer_percent[{entity}]", round(bucket["wer"] * 100.0, 2), expected,
              _close(bucket["wer"] * 100.0, expected, 0.05))
        check(f"entity_reference_words[{entity}]", bucket["reference_words"],
              sealed["entity_reference_words"][entity],
              bucket["reference_words"] == sealed["entity_reference_words"][entity])
    non_entity = entity_totals[conec.NON_ENTITY_BUCKET]
    check("non_entity_wer_percent", round(non_entity["wer"] * 100.0, 3),
          sealed["non_entity_wer_percent"],
          _close(non_entity["wer"] * 100.0, sealed["non_entity_wer_percent"], 0.0005))
    unlabelled = entity_totals[conec.UNLABELLED_BUCKET]
    check("unlabelled_reference_words", unlabelled["reference_words"],
          sealed["unlabelled_reference_words"],
          unlabelled["reference_words"] == sealed["unlabelled_reference_words"])
    check("negation_critical_high_reference_words",
          semantic_totals["high_impact_reference_words"],
          sealed["negation_critical_high_reference_words"],
          semantic_totals["high_impact_reference_words"]
          == sealed["negation_critical_high_reference_words"])
    check("negation_critical_high_insertions", semantic_totals["high_impact_insertions"],
          sealed["negation_critical_high_insertions"],
          semantic_totals["high_impact_insertions"]
          == sealed["negation_critical_high_insertions"])
    check("numeric_expected", numeric_totals["expected_numeric_words"],
          sealed["numeric_expected"],
          numeric_totals["expected_numeric_words"] == sealed["numeric_expected"],
          "expected numeric values partition exactly; only `matched` can fall short")

    shortfall = sum(row["numeric_matched_shortfall"] for row in per_call)
    checks.append(
        {
            "check": "numeric_matched_window_vs_call",
            "actual": numeric_totals["matched_numeric_words"],
            "expected": call_numeric_totals["matched_numeric_words"],
            "verdict": "REPORTED",
            "note": (
                "NOT an exactness claim. A bag match inside one window is strictly "
                "stricter than one across the whole call, so a value spoken in one "
                "window and transcribed into the next matches at call level and not at "
                f"window level. Shortfall: {shortfall} of "
                f"{call_numeric_totals['matched_numeric_words']} matched values "
                f"({100.0 * shortfall / max(call_numeric_totals['matched_numeric_words'], 1):.3f} %)."
            ),
        }
    )

    failures = [row for row in checks if row["verdict"] == "FAIL"]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows_path.parent.mkdir(parents=True, exist_ok=True)
    rows_path.write_text(
        json.dumps(
            {
                "schema": wp.RESULT_SCHEMA,
                "study": "speech-aware-evidence-acquisition",
                "exposure_row": "SAEA-E21-MF-WINDOW-PAIRING-V1",
                "source_run_id": args.run_id,
                "source_attempt_id": attempt_id,
                "carrier_lock_key": CARRIER,
                "split_identity_hash": (
                    "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
                ),
                "pairing_unit": "fixed 90-second window",
                "cluster": "call",
                "seed": wp.E21_WINDOW_SEED,
                "n_replicates": wp.E21_WINDOW_REPLICATES,
                "ci_level": wp.E21_WINDOW_CI_LEVEL,
                "taxonomy_id": taxonomy.taxonomy_id,
                "rows": rows,
            },
            indent=1,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    rows_sha256 = hashlib.sha256(rows_path.read_bytes()).hexdigest()
    (args.out_dir / "reaggregation.json").write_text(
        json.dumps(
            {
                "schema": "saea-e21-window-reaggregation-v1",
                "study": "speech-aware-evidence-acquisition",
                "exposure_row": "SAEA-E21-MF-WINDOW-PAIRING-V1",
                "source_run_id": args.run_id,
                "source_attempt_id": attempt_id,
                "verdict": "FAIL" if failures else "PASS",
                "rows_path": str(rows_path),
                "rows_sha256": rows_sha256,
                "rows": len(rows),
                "checks": checks,
                "aggregate": aggregate,
                "entity_buckets": entity_totals,
                "semantic_impact": semantic_totals,
                "numeric_window_pooled": numeric_totals,
                "numeric_call_pooled": call_numeric_totals,
                "per_call_numeric": per_call,
                "elapsed_seconds": round(time.time() - started, 1),
                "zero_contact": (
                    "no model, GPU, tool, embedding, tokenizer, network, audio-decode or "
                    "paid-API contact; references and wer_tags reached only through the "
                    "registered scoring path's own loaders"
                ),
            },
            indent=1,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    for row in checks:
        print(f"{row['verdict']:8} {row['check']}: {row['actual']} vs {row['expected']}")
    print(f"rows -> {rows_path} ({rows_sha256[:12]}...)")
    print(f"elapsed {time.time() - started:.1f}s")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
