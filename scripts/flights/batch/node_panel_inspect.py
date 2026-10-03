"""Inspect every declared panel member through the existing structural inspector.

This reads completed evidence only and never scores, retries or emits task quality.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from speech_aware_evidence_acquisition.core.flight.cli import load_node_panel_plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo-root", "data-root", "campaign-plan", "flight-commit"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--ceiling-per-row", type=int, required=True)
    parser.add_argument("--notool", choices=("0", "1"), default="0")
    parser.add_argument(
        "--result-kind", choices=("task-answer", "artifact"), default="task-answer"
    )
    parser.add_argument(
        "--mode", choices=("node-panel", "node-panel-worker"), default="node-panel"
    )
    args = parser.parse_args(argv)
    repo, plan = Path(args.repo_root).resolve(), Path(args.campaign_plan).resolve()
    if not plan.is_relative_to(repo) or args.ceiling_per_row < 1:
        parser.error(
            "panel plan must be inside repo-root and its contact ceiling must be positive"
        )
    _cells, panel_id, members = load_node_panel_plan(repo, plan, mode=args.mode)
    reports = []
    for member in members:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(__file__).with_name("batch_inspect.py")),
                args.data_root,
                member.run_id,
                member.attempt_id,
                "worker" if args.mode == "node-panel-worker" else "arm",
                str(len(member.job_keys)),
                str(args.ceiling_per_row),
                args.notool,
                args.flight_commit,
                "--result-kind",
                args.result_kind,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            detail = json.loads(completed.stdout)
        except ValueError:
            detail = {
                "inspection_output": completed.stdout,
                "inspection_error": completed.stderr,
            }
        reports.append(
            {
                "run_id": member.run_id,
                "attempt_id": member.attempt_id,
                "exit_code": completed.returncode,
                "inspection": detail,
            }
        )
    passed = all(report["exit_code"] == 0 for report in reports)
    print(
        json.dumps(
            {
                "schema": "saea-node-panel-inspection-v1",
                "panel_id": panel_id,
                "pass": passed,
                "members": reports,
            },
            sort_keys=True,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
