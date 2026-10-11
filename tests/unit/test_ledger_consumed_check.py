"""The ledger-consumed gate and its closing helper, on a synthetic ledger and run tree.

Zero model, GPU, network and dataset contact; everything lives in ``tmp_path``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
for sub in ("scripts/checks", "scripts/flights/batch"):
    if str(_REPO / sub) not in sys.path:
        sys.path.insert(0, str(_REPO / sub))

import ledger_consumed_check as gate  # noqa: E402
import ledger_mark_consumed as mark  # noqa: E402

HEADER = (
    "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | "
    "split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | "
    "inherited exposure | artifacts | notes |\n" + "|---" * 15 + "|\n"
)


def _row(date: str, run_id: str, consumed: str = "no", notes: str = "countersigned") -> str:
    cells = [date, run_id, "bounded-discovery-probe", "s", "m", "c", "dev", "h", consumed, "10", "20", "1.0", "i", "a", notes]
    return "| " + " | ".join(cells) + " |\n"


def _seal(data_root: Path, run_id: str, status: str = "COMPLETED", state: str = "FINALIZED") -> None:
    attempt = "attempt-x"
    run_dir = data_root / "runs" / run_id / attempt
    run_dir.mkdir(parents=True)
    manifest = {
        "run_id": run_id,
        "status": status,
        "attempt": {"attempt_id": attempt},
        "created_at": "2026-10-10T06:36:45.9+00:00",
        "study_commit": "abcdef012345",
        "cost": {"calls_used": 7, "audio_seconds_used": 12.5, "latency_seconds_total": 7200},
    }
    (run_dir / f"{run_id}.run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    record = data_root / "attempts" / run_id
    record.mkdir(parents=True)
    (record / f"{attempt}.json").write_text(json.dumps({"state": state}), encoding="utf-8")


def _repo(tmp_path: Path, rows: list[str]) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    (repo / "docs" / "results").mkdir(parents=True)
    (repo / "docs" / "exposure-ledger.md").write_text("# Ledger\n\n" + HEADER + "".join(rows), encoding="utf-8")
    data_root = tmp_path / "data"
    (data_root / "runs").mkdir(parents=True)
    return repo, data_root


def test_sealed_run_open_row_is_a_finding_and_helper_repairs_it(tmp_path):
    rows = [
        _row("2026-10-05", "RUN-A-V1"),
        _row("2026-10-05", "RUN-A-FIT-V1"),
        _row("2026-10-05", "RUN-B-V1"),  # never flown
        _row("2026-10-05", "RUN-C-V1"),  # manifest not COMPLETED
        _row("2026-09-20", "RUN-OLD-V1"),  # before --since
        _row("2026-10-05", "RUN-D-V1", consumed="yes"),
    ]
    repo, data_root = _repo(tmp_path, rows)
    _seal(data_root, "RUN-A-V1")
    (data_root / "prepared" / "RUN-A-FIT-V1" / "attempt-f").mkdir(parents=True)
    ((data_root / "prepared" / "RUN-A-FIT-V1" / "attempt-f") / "r.json").write_text("{}", encoding="utf-8")
    _seal(data_root, "RUN-C-V1", status="FAILED")
    _seal(data_root, "RUN-OLD-V1")

    data = gate.evaluate(repo, data_root)
    assert not data["passed"]
    assert {f["run_id"] for f in data["findings"]} == {"RUN-A-V1", "RUN-A-FIT-V1"}
    assert gate.main(["--repo-root", str(repo), "--data-root", str(data_root)]) == 1

    assert mark.main(["--repo-root", str(repo), "--data-root", str(data_root), "--apply"]) == 0
    text = (repo / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    lines = [line for line in text.split("\n") if line.startswith("| 2026")]
    assert len(lines) == len(rows)
    assert "| yes |" in lines[0] and "7 contacts" in lines[0] and "countersigned" in lines[0]
    assert "| yes |" in lines[1]
    assert "| no |" in lines[2] and "| no |" in lines[3] and "| no |" in lines[4]
    assert gate.main(["--repo-root", str(repo), "--data-root", str(data_root)]) == 0
    # idempotent
    assert mark.main(["--repo-root", str(repo), "--data-root", str(data_root), "--apply"]) == 0
    assert (repo / "docs" / "exposure-ledger.md").read_text(encoding="utf-8") == text


def test_smoke_attempt_left_opened_counts_as_sealed(tmp_path):
    repo, data_root = _repo(tmp_path, [_row("2026-10-06", "RUN-S-SMOKE-4-V1")])
    _seal(data_root, "RUN-S-SMOKE-4-V1", state="OPENED")
    assert not gate.evaluate(repo, data_root)["passed"]


def test_fit_row_needs_a_sealed_pair(tmp_path):
    repo, data_root = _repo(tmp_path, [_row("2026-10-06", "RUN-E-FIT-V1")])
    (data_root / "prepared" / "RUN-E-FIT-V1" / "a").mkdir(parents=True)
    ((data_root / "prepared" / "RUN-E-FIT-V1" / "a") / "r.json").write_text("{}", encoding="utf-8")
    assert gate.evaluate(repo, data_root)["passed"]


def test_fallback_to_results_notes_without_a_data_root(tmp_path):
    repo, _ = _repo(tmp_path, [_row("2026-10-07", "RUN-F-V1"), _row("2026-10-07", "RUN-G-V1")])
    (repo / "docs" / "results" / "n.md").write_text(
        "# Note\n\nRUN-F-V1 sealed on 2026-10-07.\n\nRUN-G-V1 is planned.\n", encoding="utf-8"
    )
    data = gate.evaluate(repo, None)
    assert data["mode"] == "results-notes"
    assert [f["run_id"] for f in data["findings"]] == ["RUN-F-V1"]
