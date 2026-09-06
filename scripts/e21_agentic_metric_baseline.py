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


def bundles_dir() -> Path:
    """Deliberately OUTSIDE the study checkout: ``core.scorers`` refuses to
    score a dirty tree, so nothing this pipeline writes before the score may
    land in ``docs/``. The receipt copies arrive at read time."""

    return build_side.rescore_root() / "bundles"


def scratch_scoring() -> Path:
    return build_side.rescore_root() / "scoring"


def stage_build() -> int:
    bundles = build_side.build_all_bundles()
    read_side.write_json(bundles_dir() / "rescore-bundles.json", {"bundles": bundles})
    jobs = "".join(
        json.dumps({"job_id": bundle["job_id"], "manifest": bundle["manifest"]}) + "\n"
        for bundle in bundles
    )
    (bundles_dir() / "jobs.jsonl").write_text(jobs, encoding="utf-8", newline="\n")
    for bundle in bundles:
        print(f"{bundle['job_id']:24s} {bundle['scorer']:34s} {bundle['manifest']}")
    return 0


def stage_score() -> int:
    table = json.loads((bundles_dir() / "rescore-bundles.json").read_text(encoding="utf-8"))
    output_dir = scratch_scoring()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"{output_dir} is not empty; core.scoring_batch refuses to overwrite")
    summary = build_side.run_scoring(table["bundles"], output_dir)
    read_side.write_json(output_dir / "batch-summary.json", summary)
    print(json.dumps({key: summary[key] for key in ("succeeded", "failed", "job_count")}))
    return 0 if summary["failed"] == 0 else 1


def stage_read() -> int:
    scores = {
        scorer: read_side.load_scores(scratch_scoring() / f"{slug}.score.json", scorer)
        for slug, scorer in build_side.JOBS
    }
    summary = read_side.write_receipts(scores, scratch_scoring(), bundles_dir())
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
