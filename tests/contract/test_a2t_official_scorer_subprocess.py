"""Contract: the Audio2Tool official scorer still runs as ``core.scoring_batch``
runs it, and still reproduces the sealed comparator to the digit.

Every number this study reports for Audio2Tool comes out of ONE subprocess --
``core.scoring_batch.run_official_score_job``, i.e. ``python -m
speech_aware_evidence_acquisition.core.driver score --manifest <path>`` with
``cwd`` at the repo root. Nothing else may compute it, and nothing that is not
a score may stop it.

REGRESSION (2026-09-09). The four Audio2Tool wire-check cells ended at
``seal_and_score = SCORING_FAILED`` / "official scorer exited with status 1"
while ONE untracked readiness note sat in the worktree: the manifest sealed
COMPLETED (``core.bundle.git_commit._study_commit_for_completed_manifest``
tolerates and records dirt outside the load-bearing surface, since the
2026-08-16 flight-protection fix) and the scoring entry gate then refused the
same tree, because it still called ``require_clean_study_repo``, which refuses
ANY dirt. The scorer itself was never at fault: every one of its inputs is
byte-identical to merge wave 3. Receipt:
``docs/checks/speech-aware-evidence-acquisition/
2026-09-09-a2t-official-scorer-seal-and-score-diagnosis/``.

Preconditions, all skipped rather than faked:

* ``SPEECHRL_DATA_DIR`` is set and carries the sealed Audio2Tool bundles --
  large bytes never enter Git;
* this checkout's own LOAD-BEARING surface (``src/``, ``configs/``,
  ``docs/arms/``, ``scripts/``) is clean, because the subprocess resolves the
  study repo from where it is installed and cannot be pointed at a stand-in.
  That is the gate under test, so it is a precondition of the host here, never
  something to monkeypatch away.

Zero model contacts, zero servers, zero sockets, zero GPU: this reads sealed
outputs off disk and scores them.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.scoring_batch import (
    ScoreJob,
    run_official_score_job,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The sealed Audio2Tool official-protocol replication: cell ``R-official-raw``,
#: the comparator every ``@ts2``/``@16k`` variant cell is measured against, and
#: the 4-row smoke that preceded it.
COMPARATOR = (
    "runs/SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1/"
    "attempt-20260904T135250Z-rofficialraw/"
    "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1.run-manifest.json"
)
SMOKE = (
    "runs/SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-SMOKE-V1/"
    "attempt-20260904T134948Z-rofficialraw/"
    "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-SMOKE-V1.run-manifest.json"
)

#: Where the sealed comparator's own numbers are committed, so this test reads
#: the pin the cells read rather than a constant retyped here.
COMPARATOR_FRAGMENT = "configs/experiment/a2t-official-protocol-tail2s-400-v1.json"

LOAD_BEARING_PREFIXES = ("src/", "configs/", "docs/arms/", "scripts/")


def _data_root() -> Path | None:
    raw = os.environ.get("SPEECHRL_DATA_DIR", "").strip()
    if not raw:
        return None
    root = Path(raw)
    return root if root.is_dir() else None


def _porcelain() -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout if completed.returncode == 0 else ""


def _load_bearing_dirt() -> list[str]:
    paths = []
    for line in _porcelain().splitlines():
        entry = (line[3:] if len(line) > 3 else line[2:].lstrip()).strip()
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip('"').replace("\\", "/")
        if any(entry == prefix[:-1] or entry.startswith(prefix) for prefix in LOAD_BEARING_PREFIXES):
            paths.append(entry)
    return paths


DATA_ROOT = _data_root()

pytestmark = [
    pytest.mark.skipif(
        DATA_ROOT is None or not (DATA_ROOT / COMPARATOR).is_file(),
        reason="the sealed Audio2Tool bundles are not on this host's data root",
    ),
    pytest.mark.skipif(
        bool(_load_bearing_dirt()),
        reason=(
            "this checkout's load-bearing surface is dirty; the scoring gate under "
            "test resolves the study repo from where it is installed and correctly "
            "refuses, so the probe would measure the working tree, not the scorer"
        ),
    ),
]


def _score(relpath: str, job_id: str) -> dict:
    """Exactly what ``core.scoring_batch`` does for one whole manifest."""

    assert DATA_ROOT is not None
    manifest = DATA_ROOT / relpath
    outcome = run_official_score_job(ScoreJob(job_id=job_id, manifest=manifest))
    assert outcome.returncode == 0, outcome.stderr
    payload = json.loads(outcome.stdout)
    assert payload["verified"] is True
    assert Path(payload["manifest"]).resolve() == manifest.resolve()
    return payload["scores"]


def test_official_scorer_subprocess_scores_the_smallest_sealed_bundle():
    """The cheap leg: four rows, the whole subprocess path, every registered
    scorer of that cell run to completion."""

    scores = _score(SMOKE, "contract-a2t-smoke")
    official = scores["a2t-toolcall-official"]
    assert official["samples"] == 4
    assert official["scorer_version"].startswith("a2t-scorer-official-")
    # Every scorer the cell configured ran; a partial result is a failure.
    assert {"a2t-toolcall-official", "a2t-toolcall", "cost"} <= set(scores)


def test_official_scorer_subprocess_reproduces_the_sealed_comparator_to_the_digit():
    """The comparator is the ruler. If this drifts by a digit, every ``@ts2`` /
    ``@16k`` verdict measured against it is void, so the assertion is exact
    equality against the numbers the cell fragments themselves pin -- overall,
    exact match, parse rate, the multi-call diagnostic, and all eight tiers."""

    sealed = json.loads((REPO_ROOT / COMPARATOR_FRAGMENT).read_text(encoding="utf-8"))
    expected = sealed["comparator"]["sealed_official_tool_accuracy"]
    official = _score(COMPARATOR, "contract-a2t-comparator")["a2t-toolcall-official"]

    assert official["samples"] == expected["n"]
    assert round(official["tool_accuracy"] * 100, 2) == expected["overall"]
    assert round(official["exact_match"] * 100, 2) == expected["exact_match"]
    assert round(official["parse_rate"] * 100, 2) == expected["parse_rate"]
    assert official["rows_with_multiple_call_matches"] == (
        expected["rows_with_multiple_call_matches"]
    )
    tiers = {
        tier: round(values["tool_accuracy"] * 100, 2)
        for tier, values in official["per_tier"].items()
    }
    assert tiers == {
        tier: value for tier, value in expected.items() if tier.startswith("tier")
    }


def test_a_governance_document_does_not_stop_the_official_scorer():
    """THE regression, end to end through the real subprocess.

    A COMPLETED manifest binds its commit over dirt confined outside the
    load-bearing surface and records it; the scoring gate must agree, or a
    sealed run is unscoreable and unfinalizable on the tree that sealed it.
    The probe file is untracked, lives where the 2026-09-09 note lived, and is
    removed again whether or not the assertion holds."""

    note = REPO_ROOT / "docs" / "readiness" / f".scoring-gate-probe-{uuid.uuid4().hex}.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("an untracked readiness note, exactly the 2026-09-09 shape\n", encoding="utf-8")
    try:
        relpath = note.relative_to(REPO_ROOT).as_posix()
        if relpath not in _porcelain():
            pytest.skip(f"{relpath} is not reported dirty by git; the probe would be vacuous")
        scores = _score(SMOKE, "contract-a2t-governance-dirt")
        assert scores["a2t-toolcall-official"]["samples"] == 4
    finally:
        note.unlink(missing_ok=True)
