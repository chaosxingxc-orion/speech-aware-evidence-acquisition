#!/usr/bin/env python3
"""Model-free re-score of the sealed Earnings-21 full-44 baseline under the
2026-09-06 agentic metrics. Thin CLI; every decision lives in
``analysis.e21_agentic_metric_baseline`` / ``analysis.e21_agentic_metric_read``.

    python scripts/e21_agentic_metric_baseline.py build
    python scripts/e21_agentic_metric_baseline.py score
    python scripts/e21_agentic_metric_baseline.py read
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    e21_agentic_metric_baseline as build_side,
)
from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    e21_agentic_metric_read as read_side,
)

RECEIPT_SCORING = build_side.CHECK_DIR / "scoring"
VERDICT = build_side.CHECK_DIR / "verdict"


def bundles_dir() -> Path:
    """Deliberately OUTSIDE the study checkout: ``core.scorers`` refuses to
    score a dirty tree, so nothing this pipeline writes before the score may
    land in ``docs/``. The receipt copies arrive at read time."""

    return build_side.rescore_root() / "bundles"


def scratch_scoring() -> Path:
    return build_side.rescore_root() / "scoring"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def stage_build() -> int:
    bundles = build_side.build_all_bundles()
    _write_json(bundles_dir() / "rescore-bundles.json", {"bundles": bundles})
    jobs = "".join(
        json.dumps({"job_id": bundle["job_id"], "manifest": bundle["manifest"]}) + "\n"
        for bundle in bundles
    )
    (bundles_dir() / "jobs.jsonl").write_text(jobs, encoding="utf-8", newline="\n")
    for bundle in bundles:
        print(f"{bundle['job_id']:24s} {bundle['scorer']:34s} {bundle['manifest']}")
    return 0


def stage_score() -> int:
    bundles = json.loads((bundles_dir() / "rescore-bundles.json").read_text(encoding="utf-8"))["bundles"]
    output_dir = scratch_scoring()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"{output_dir} is not empty; core.scoring_batch refuses to overwrite")
    summary = build_side.run_scoring(bundles, output_dir)
    _write_json(scratch_scoring() / "batch-summary.json", summary)
    print(json.dumps({key: summary[key] for key in ("succeeded", "failed", "job_count")}))
    return 0 if summary["failed"] == 0 else 1


def _reduce(rows: list[dict], drop: tuple[str, ...]) -> list[dict]:
    return [{key: value for key, value in row.items() if key not in drop} for row in rows]


def stage_read() -> int:
    scores = {}
    for slug, scorer in build_side.JOBS:
        path = scratch_scoring() / f"{slug}.score.json"
        scores[scorer] = read_side.load_scores(path, scorer)
    whisper = scores["asr-wer-whisper"]
    conec = scores["conec-entity-wer-official"]
    numeric = scores["numeric-value-accuracy-v1"]

    summary = read_side.build_summary(
        whisper["per_sample"], conec["per_sample"], numeric["per_sample"], conec["aggregate"]
    )
    summary["jobs"] = [
        {
            "job_id": slug,
            "scorer": scorer,
            "result_file": f"{slug}.score.json",
            "result_sha256": build_side.sha256_file(scratch_scoring() / f"{slug}.score.json"),
        }
        for slug, scorer in build_side.JOBS
    ]
    RECEIPT_SCORING.mkdir(parents=True, exist_ok=True)
    for name in ("batch-summary.json", "jobs.jsonl", "rescore-bundles.json"):
        source = scratch_scoring() / name
        if not source.is_file():
            source = bundles_dir() / name
        shutil.copyfile(source, RECEIPT_SCORING / name)
    _write_json(VERDICT / "result-summary.json", summary)
    (VERDICT / "per-call-table.md").write_text(
        read_side.per_call_table(
            whisper["per_sample"], conec["per_sample"], numeric["per_sample"]
        ),
        encoding="utf-8",
        newline="\n",
    )
    _write_json(
        RECEIPT_SCORING / "verified-score-read.json",
        {
            "_receipt_note": (
                "core.scoring_batch --include-per-sample verified reads of the three "
                "re-scoring manifests. Per-sample ref_hit_mask arrays are dropped for size "
                "(the same reduction the 2026-09-04 receipt made); every count is verbatim. "
                "The unreduced files' sha256s are in verdict/result-summary.json's jobs block."
            ),
            "scores": {
                "asr-wer-whisper": {
                    "aggregate": whisper["aggregate"],
                    "per_sample": _reduce(whisper["per_sample"], ("ref_hit_mask",)),
                },
                "conec-entity-wer-official": conec,
                "numeric-value-accuracy-v1": numeric,
            },
        },
    )
    anchor = summary["identity_anchor"]
    print(
        json.dumps(
            {
                "identity_holds": anchor["identity_holds"],
                "corpus_wer_percent": round(anchor["rescored_corpus_wer_percent"], 4),
                "conec_overall_percent": round(
                    summary["conec_entity_wer"]["all_44"]["overall_wer_percent"], 4
                ),
                "numeric_accuracy_percent": round(
                    summary["numeric_value_accuracy"]["all_44"]["accuracy_percent"], 4
                ),
            }
        )
    )
    return 0 if anchor["identity_holds"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("build", "score", "read"))
    stage = parser.parse_args().stage
    return {"build": stage_build, "score": stage_score, "read": stage_read}[stage]()


if __name__ == "__main__":
    raise SystemExit(main())
