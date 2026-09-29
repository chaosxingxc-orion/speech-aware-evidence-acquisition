"""``scripts/flights/*/*_read.sh`` drivers: the shared countersign gate and the idempotent
column-scoring step, both factored into ``scripts/flights/batch/read_lib.sh``.

Context (2026-09-29 read-agent follow-up): the W-SV-1 read agent found that
``scripts/flights/wsv1/wsv1_read.sh``'s step-0 countersign check loaded
``scripts/checks/flight_registration_check.py`` by file path with ``importlib.util`` and called
``spec.loader.exec_module(gate)`` WITHOUT first registering the module in ``sys.modules`` -- the
gate's ``@dataclass`` rows (``Finding``, ``CellReport``) resolve their own module through
``sys.modules`` while their class bodies are evaluated, so the missing entry raised
``AttributeError`` ("'NoneType' object has no attribute '__dict__'") before the gate read a single
row: the driver crashed before anything was opened, not a documented REFUSED refusal (commit
e3799ad3). The identical one-line bug was independently present, unfixed, in
``scripts/flights/psv/psv_read.sh``, ``scripts/flights/e4/e4_read.sh`` and
``scripts/flights/w4sv/w4sv_read.sh`` -- the only other ``*_read.sh`` drivers that loaded this gate
the same way (``grep -rl flight_registration_check scripts/flights/`` finds no fifth). All four now
share one fix, ``read_lib.sh``'s ``read_require_countersigned``, so a future ``*_read.sh`` cannot
reintroduce the missing-``sys.modules`` line by copying an inlined heredoc that never had it.

The read agent separately noted that a paired-read failure AFTER the column-scoring step (an
official-scorer subprocess, not free) made a retry re-score every column from scratch. The same
library's ``read_scoring_done`` gates that step: skip when a scoring receipt already carries the
expected schema, ``--rescore`` forces it regardless.

Zero model, tokenizer, encoder, scorer, network and GPU contacts: every check here runs `bash -n`
or drives the two pure-Python library functions over a synthetic ledger / synthetic JSON receipt
under ``tmp_path``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FLIGHTS = REPO_ROOT / "scripts" / "flights"
LIB_PATH = FLIGHTS / "batch" / "read_lib.sh"

#: The four drivers that loaded scripts/checks/flight_registration_check.py by file path and
#: carried the missing-sys.modules bug (wsv1_read.sh was fixed first, by commit e3799ad3; the
#: other three carried it until this change). Every one of them must now call the shared library
#: function instead of inlining the loader.
SHARED_GATE_SCRIPTS = (
    FLIGHTS / "wsv1" / "wsv1_read.sh",
    FLIGHTS / "psv" / "psv_read.sh",
    FLIGHTS / "e4" / "e4_read.sh",
    FLIGHTS / "w4sv" / "w4sv_read.sh",
)

#: Every *_read.sh under scripts/flights (any depth), for the broad bash -n sweep. Computed at
#: collection time so a future new *_read.sh is covered automatically.
ALL_READ_SCRIPTS = sorted(FLIGHTS.rglob("*_read.sh"))

LEDGER_COLUMNS = (
    "date", "run/experiment id", "execution profile", "scope", "model/tool",
    "speech carrier + split", "split role", "split identity hash", "consumed", "calls",
    "speech audio seconds", "gpu hours", "inherited exposure", "artifacts", "notes",
)
SIGNED = "REGISTERED BEFORE CONTACT (root countersigned 2026-09-29 by the coordinator)"
DRAFT = "REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending)"


def _row(run_id: str, notes: str) -> dict[str, str]:
    return {
        "date": "2026-09-29",
        "run/experiment id": run_id,
        "execution profile": "model-free-check",
        "scope": "test",
        "model/tool": "none",
        "speech carrier + split": "n/a",
        "split role": "discovery",
        "split identity hash": "a" * 8,
        "consumed": "no",
        "calls": "0",
        "speech audio seconds": "0",
        "gpu hours": "0",
        "inherited exposure": "none",
        "artifacts": "docs/readiness/test/plan.json",
        "notes": notes,
    }


def _ledger_text(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Exposure ledger", "",
        "| " + " | ".join(LEDGER_COLUMNS) + " |",
        "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(name, "-")) for name in LEDGER_COLUMNS) + " |")
    return "\n".join(lines) + "\n"


def _bash(script: str) -> subprocess.CompletedProcess[str]:
    """Run a small bash program that sources read_lib.sh with PY/MAIN already set, the same way
    every *_read.sh driver does before it calls a library function."""

    preamble = f'PY="{sys.executable}"\nMAIN="{REPO_ROOT}"\nsource "{LIB_PATH}"\n'
    return subprocess.run(
        ["bash", "-c", preamble + script], capture_output=True, text=True, check=False,
    )


# ---------------------------------------------------------------------------
# bash -n: every *_read.sh (not just the four fixed here) and the library itself must parse.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("script", ALL_READ_SCRIPTS, ids=lambda p: p.relative_to(FLIGHTS).as_posix())
def test_read_script_bash_syntax_ok(script: Path) -> None:
    result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_read_lib_bash_syntax_ok() -> None:
    result = subprocess.run(["bash", "-n", str(LIB_PATH)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# regression: no *_read.sh may reintroduce an inlined copy of the gate loader.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("script", SHARED_GATE_SCRIPTS, ids=lambda p: p.name)
def test_shared_gate_script_calls_the_library(script: Path) -> None:
    text = script.read_text(encoding="utf-8")
    assert "read_require_countersigned" in text
    assert f'source "$MAIN/{LIB_PATH.relative_to(REPO_ROOT).as_posix()}"' in text
    # The bug this file guards against: loading the gate by file path without registering it in
    # sys.modules first. No *_read.sh may inline that loader again -- it must go through the
    # library, which fixed it once.
    assert "spec_from_file_location" not in text
    assert "module_from_spec" not in text


@pytest.mark.parametrize("script", ALL_READ_SCRIPTS, ids=lambda p: p.relative_to(FLIGHTS).as_posix())
def test_no_read_script_inlines_the_flight_registration_gate(script: Path) -> None:
    """Broader sweep than ``SHARED_GATE_SCRIPTS``: a *_read.sh written after this change that
    still wants the countersign gate must call ``read_require_countersigned``, never load
    ``flight_registration_check.py`` by file path itself -- that is exactly how the missing-
    sys.modules bug was copied into three separate drivers the first time."""

    text = script.read_text(encoding="utf-8")
    assert "flight_registration_check.py" not in text or "read_require_countersigned" in text, (
        f"{script} references flight_registration_check.py directly instead of the shared library"
    )


# ---------------------------------------------------------------------------
# read_require_countersigned: present+countersigned / present+DRAFT / absent, over a synthetic
# ledger -- the exact three cases the missing-sys.modules bug made unreachable (every case used to
# crash with AttributeError before the ledger was even opened).
# ---------------------------------------------------------------------------


def test_require_countersigned_present_and_signed(tmp_path: Path) -> None:
    ledger = tmp_path / "exposure-ledger.md"
    ledger.write_text(_ledger_text([_row("SAEA-TEST-SIGNED-V1", SIGNED)]), encoding="utf-8")
    result = _bash(f'read_require_countersigned "{ledger}" SAEA-TEST-SIGNED-V1')
    assert result.returncode == 0, result.stderr
    assert "countersigned" in result.stdout


def test_require_countersigned_present_draft_refuses(tmp_path: Path) -> None:
    ledger = tmp_path / "exposure-ledger.md"
    ledger.write_text(_ledger_text([_row("SAEA-TEST-DRAFT-V1", DRAFT)]), encoding="utf-8")
    result = _bash(f'read_require_countersigned "{ledger}" SAEA-TEST-DRAFT-V1')
    assert result.returncode != 0
    assert "not root countersigned" in result.stderr


def test_require_countersigned_absent_row_refuses(tmp_path: Path) -> None:
    ledger = tmp_path / "exposure-ledger.md"
    ledger.write_text(_ledger_text([_row("SAEA-TEST-SIGNED-V1", SIGNED)]), encoding="utf-8")
    result = _bash(f'read_require_countersigned "{ledger}" SAEA-TEST-ABSENT-V1')
    assert result.returncode != 0
    assert "not in the exposure ledger" in result.stderr


def test_require_countersigned_mixed_rows_any_signed_row_is_enough(tmp_path: Path) -> None:
    """One row is enough: ``is_countersigned`` is checked with ``any(...)`` over every row sharing
    the run id, so a DRAFT row alongside a signed one for the SAME id must still pass."""

    ledger = tmp_path / "exposure-ledger.md"
    ledger.write_text(
        _ledger_text([_row("SAEA-TEST-MIXED-V1", DRAFT), _row("SAEA-TEST-MIXED-V1", SIGNED)]),
        encoding="utf-8",
    )
    result = _bash(f'read_require_countersigned "{ledger}" SAEA-TEST-MIXED-V1')
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# read_scoring_done: the idempotent column-scoring gate.
# ---------------------------------------------------------------------------


def test_scoring_done_missing_file_is_false(tmp_path: Path) -> None:
    receipt = tmp_path / "score-summary.json"
    result = _bash(f'read_scoring_done "{receipt}" some-schema-v1')
    assert result.returncode != 0


def test_scoring_done_malformed_json_is_false(tmp_path: Path) -> None:
    receipt = tmp_path / "score-summary.json"
    receipt.write_text("not json", encoding="utf-8")
    result = _bash(f'read_scoring_done "{receipt}" some-schema-v1')
    assert result.returncode != 0


def test_scoring_done_wrong_schema_is_false(tmp_path: Path) -> None:
    receipt = tmp_path / "score-summary.json"
    receipt.write_text(json.dumps({"schema": "other-schema-v1"}), encoding="utf-8")
    result = _bash(f'read_scoring_done "{receipt}" some-schema-v1')
    assert result.returncode != 0


def test_scoring_done_matching_schema_is_true(tmp_path: Path) -> None:
    receipt = tmp_path / "score-summary.json"
    receipt.write_text(json.dumps({"schema": "some-schema-v1", "arms": {}}), encoding="utf-8")
    result = _bash(f'read_scoring_done "{receipt}" some-schema-v1')
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "rescore,receipt_exists,expect",
    [
        ("0", False, "RUN"),  # nothing scored yet -> run
        ("0", True, "SKIP"),  # already scored, no --rescore -> skip
        ("1", False, "RUN"),  # --rescore always runs
        ("1", True, "RUN"),  # --rescore forces even when already scored
    ],
)
def test_rescore_guard_matches_every_driver(
    tmp_path: Path, rescore: str, receipt_exists: bool, expect: str,
) -> None:
    """Exercises the exact guard expression every fixed driver uses:

        if [ "$RESCORE" = 1 ] || ! read_scoring_done "$RECEIPT" "$SCHEMA"; then RUN else SKIP
    """

    receipt = tmp_path / "score-summary.json"
    if receipt_exists:
        receipt.write_text(json.dumps({"schema": "some-schema-v1"}), encoding="utf-8")
    script = (
        f'RESCORE={rescore}\n'
        f'if [ "$RESCORE" = 1 ] || ! read_scoring_done "{receipt}" some-schema-v1; then '
        f'echo RUN; else echo SKIP; fi'
    )
    result = _bash(script)
    assert result.stdout.strip() == expect, result.stderr
