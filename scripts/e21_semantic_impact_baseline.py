#!/usr/bin/env python3
"""Model-free re-score of the sealed Earnings-21 full-44 baseline under
``semantic-high-impact-error-rate-v1``, now that E5 landed its taxonomy. Thin
CLI; every decision lives in ``analysis.e21_semantic_impact_baseline``.

    python scripts/e21_semantic_impact_baseline.py build
    python scripts/e21_semantic_impact_baseline.py score
    python scripts/e21_semantic_impact_baseline.py read
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
    e21_semantic_impact_baseline as side,
)


def bundles_dir() -> Path:
    """Outside the study checkout, for the reason the 2026-09-06 agentic-metric
    pipeline states: ``core.scorers`` refuses to score a dirty tree, so nothing
    written before the score may land in ``docs/``."""

    return side.scratch_root() / "bundles"


def scratch_scoring() -> Path:
    return side.scratch_root() / "scoring"


def stage_build() -> int:
    bundle = side.build()
    side.write_json(bundles_dir() / "rescore-bundles.json", {"bundles": [bundle]})
    (bundles_dir() / "jobs.jsonl").write_text(
        json.dumps({"job_id": bundle["job_id"], "manifest": bundle["manifest"]}) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{bundle['job_id']:24s} {bundle['scorer']:34s} {bundle['manifest']}")
    return 0


def stage_score() -> int:
    table = json.loads((bundles_dir() / "rescore-bundles.json").read_text(encoding="utf-8"))
    output_dir = scratch_scoring()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"{output_dir} is not empty; core.scoring_batch refuses to overwrite")
    summary = side.score(table["bundles"], output_dir)
    side.write_json(output_dir / "batch-summary.json", summary)
    print(json.dumps({key: summary[key] for key in ("succeeded", "failed", "job_count")}))
    return 0 if summary["failed"] == 0 else 1


def stage_read() -> int:
    result_path = scratch_scoring() / f"{side.JOB_SLUG}.score.json"
    scores = side.load_scores(result_path)
    summary = side.build_summary(scores, result_path)
    side.CHECK_DIR.mkdir(parents=True, exist_ok=True)
    (side.CHECK_DIR / "scoring").mkdir(parents=True, exist_ok=True)
    (side.CHECK_DIR / "verdict").mkdir(parents=True, exist_ok=True)
    for name in ("batch-summary.json",):
        shutil.copyfile(scratch_scoring() / name, side.CHECK_DIR / "scoring" / name)
    for name in ("rescore-bundles.json", "jobs.jsonl"):
        shutil.copyfile(bundles_dir() / name, side.CHECK_DIR / "scoring" / name)
    side.write_json(side.CHECK_DIR / "verdict" / "result-summary.json", summary)
    (side.CHECK_DIR / "verdict" / "per-call-table.md").write_text(
        side.per_call_table(summary), encoding="utf-8", newline="\n"
    )
    pooled = summary["semantic_high_impact_error_rate"]
    print(
        json.dumps(
            {
                roster: {
                    "calls": pooled[roster]["calls"],
                    "reference_words": pooled[roster]["reference_words"],
                    "high_impact_percent": round(
                        pooled[roster]["high_impact_error_rate_percent"], 4
                    ),
                    "by_level_percent": {
                        level: round(value, 3)
                        for level, value in pooled[roster][
                            "reference_words_by_level_percent"
                        ].items()
                    },
                }
                for roster in ("all_44", "construction_34", "evaluation_10")
            }
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("build", "score", "read"))
    stage = parser.parse_args().stage
    return {"build": stage_build, "score": stage_score, "read": stage_read}[stage]()


if __name__ == "__main__":
    raise SystemExit(main())
