"""The native-episode failure-mode policy gate, on a synthetic repository.

Item E13 (2026-09-19). ``scripts/checks/finite_completion_policy_check.py``
demands ``native_episode.finite_completion_policy ==
"deliver-latest-or-abstain"`` of every LIVE, UNFLOWN native cell -- the rule
the B7a recovery arm's 1,451-contact abort bought. Item E22 (2026-09-19, the
ReAct-exhaustion disposition, not the Earnings-22 carrier) added the second
key ``native_episode.react_exhaustion_policy ==
"continue-without-answer"`` under exactly the same scope rule, after the
B8b-anchor arm's 2,016-contact abort. These fixtures therefore arm BOTH keys
by default and vary one at a time. These tests build a whole
miniature repository (exposure ledger, experiment fragment, baseline fragment,
readiness package) per case, so the scope rule is exercised on both sides of
each of its three conditions rather than on whatever the real tree happens to
hold today.

Zero model, tokenizer, encoder, network and GPU contacts; no
``SPEECHRL_DATA_DIR`` read.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_CHECKS = Path(__file__).resolve().parents[2] / "scripts" / "checks"
if str(_CHECKS) not in sys.path:
    sys.path.insert(0, str(_CHECKS))

import finite_completion_policy_check as gate  # noqa: E402

RUN_ID = "SAEA-SLURP-NATIVE-E13-PROOF-V1"
EXPERIMENT = "slurp-native-e13-proof-v1"
BASELINE = "slurp-native-e13-proof-baseline-v1"

LEDGER_COLUMNS = (
    "date",
    "run/experiment id",
    "execution profile",
    "scope",
    "model/tool",
    "speech carrier + split",
    "split role",
    "split identity hash",
    "consumed",
    "calls",
    "speech audio seconds",
    "gpu hours",
    "inherited exposure",
    "artifacts",
    "notes",
)


def _ledger(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Exposure ledger",
        "",
        "| " + " | ".join(LEDGER_COLUMNS) + " |",
        "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |",
    ]
    for row in rows:
        lines.append(
            "| " + " | ".join(str(row.get(name, "-")) for name in LEDGER_COLUMNS) + " |"
        )
    return "\n".join(lines) + "\n"


def _episode(policy: str | None, react_policy: str | None) -> dict:
    block = {
        "schema": "saea-native-episode-config-v1",
        "episode_id": "e13-proof-v1",
        "max_revisions": 1,
        "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
        "roles": {
            kind: {"phase_id": kind, "max_iterations": 3 if kind == "reviewer" else 1}
            for kind in ("perception", "solver", "reviewer", "planner")
        },
    }
    if policy is not None:
        block["finite_completion_policy"] = policy
    if react_policy is not None:
        block["react_exhaustion_policy"] = react_policy
    return block


def _build(
    root: Path,
    *,
    policy: str | None,
    react_policy: str | None = gate.REQUIRED_REACT_POLICY,
    consumed: str = "no",
    readiness_state: str | None = "ready",
    with_ledger_row: bool = True,
    native: bool = True,
) -> None:
    """One synthetic repository: one plan, one fragment, one baseline, one row."""

    (root / "docs" / "readiness" / "2026-09-19-e13-proof-v1").mkdir(parents=True)
    (root / "configs" / "experiment").mkdir(parents=True)
    (root / "configs" / "baseline").mkdir(parents=True)

    baseline: dict = {"arm": "e13-proof", "policy": "phase-native-e13-proof-v1"}
    if native:
        baseline["native_episode"] = _episode(policy, react_policy)
    (root / "configs" / "baseline" / f"{BASELINE}.json").write_text(
        json.dumps(baseline, indent=2, sort_keys=True), encoding="utf-8"
    )

    cell: dict = {"cell_id": EXPERIMENT, "baseline_fragment": BASELINE, "run_id": RUN_ID}
    if readiness_state is not None:
        cell["readiness"] = {"state": readiness_state, "reason": "synthetic"}
    (root / "configs" / "experiment" / f"{EXPERIMENT}.json").write_text(
        json.dumps({"experiment_id": RUN_ID, "cells": [cell]}, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    (
        root / "docs" / "readiness" / "2026-09-19-e13-proof-v1" / "generation-plan-v1.json"
    ).write_text(
        json.dumps(
            {
                "schema": "saea-registered-generation-plan-v1",
                "cell": EXPERIMENT,
                "experiment": EXPERIMENT,
                "execution_plan": {
                    "schema": "saea-execution-plan-v1",
                    "run_id": RUN_ID,
                    "attempt_id": "attempt-e13-proof-generation-v1",
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    rows = []
    if with_ledger_row:
        rows.append(
            {
                "date": "2026-09-19",
                "run/experiment id": RUN_ID,
                "execution profile": "bounded-discovery-probe",
                "consumed": consumed,
                "calls": "44",
            }
        )
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "exposure-ledger.md").write_text(_ledger(rows), encoding="utf-8")


def _kinds(result: dict) -> list[str]:
    return [violation["kind"] for violation in result["violations"]]


def test_an_armed_live_unflown_cell_passes(tmp_path):
    _build(tmp_path, policy="deliver-latest-or-abstain")
    result = gate.evaluate(tmp_path)
    assert result["passed"] is True
    assert result["violations"] == []
    assert result["in_scope_plans"] == [
        "docs/readiness/2026-09-19-e13-proof-v1/generation-plan-v1.json"
    ]
    assert result["checked_baselines"] == [BASELINE]
    assert gate.main(["--repo-root", str(tmp_path)]) == 0


def test_a_live_unflown_cell_with_the_key_absent_is_a_violation(tmp_path):
    _build(tmp_path, policy=None)
    result = gate.evaluate(tmp_path)
    assert result["passed"] is False
    assert _kinds(result) == ["missing-policy"]
    violation = result["violations"][0]
    assert violation["run_id"] == RUN_ID
    assert violation["baseline"] == BASELINE
    assert violation["readiness_state"] == "ready"
    assert violation["declared"] is None
    assert "ABSENT" in violation["message"]
    assert "deliver-latest-or-abstain" in violation["message"]
    assert gate.main(["--repo-root", str(tmp_path)]) == 1


def test_any_other_declared_value_is_refused_twice_over(tmp_path):
    """A wrong value fails the scope rule AND the repository-wide rule.

    ``"raise"`` is legal to ``load_native_episode_config`` -- it is the
    parser's own default -- which is exactly why the gate has a second,
    scope-free rule: a committed baseline that writes the abort default out
    loud reads like an oversight, and an oversight is what this item exists to
    stop being silent.
    """

    _build(tmp_path, policy="raise")
    result = gate.evaluate(tmp_path)
    assert result["passed"] is False
    assert sorted(_kinds(result)) == ["declared-third-value", "wrong-policy"]
    assert all(
        violation["declared"] == "raise" for violation in result["violations"]
    )


def test_a_consumed_row_is_out_of_scope(tmp_path):
    _build(tmp_path, policy=None, consumed="yes")
    result = gate.evaluate(tmp_path)
    assert result["passed"] is True
    assert result["in_scope_plans"] == []
    assert result["out_of_scope"]["consumed"] == [
        f"docs/readiness/2026-09-19-e13-proof-v1/generation-plan-v1.json ({RUN_ID})"
    ]
    assert gate.main(["--repo-root", str(tmp_path)]) == 0


def test_a_plan_with_no_ledger_row_is_out_of_scope(tmp_path):
    _build(tmp_path, policy=None, with_ledger_row=False)
    result = gate.evaluate(tmp_path)
    assert result["passed"] is True
    assert result["in_scope_plans"] == []
    assert result["out_of_scope"]["no_ledger_row"] == [
        f"docs/readiness/2026-09-19-e13-proof-v1/generation-plan-v1.json ({RUN_ID})"
    ]


@pytest.mark.parametrize("state", ["superseded", "preparation-pending", None])
def test_a_cell_that_is_not_live_is_out_of_scope_and_named(tmp_path, state):
    """A rebased or unprepared cell never flies in that form (coordinator,
    2026-09-19), so the gate reports its state instead of demanding an edit."""

    _build(tmp_path, policy=None, readiness_state=state)
    result = gate.evaluate(tmp_path)
    assert result["passed"] is True
    assert result["in_scope_plans"] == []
    expected = state if state is not None else gate.NO_READINESS_STATE
    assert result["out_of_scope"]["not_live_state_counts"] == {expected: 1}
    assert [row["state"] for row in result["out_of_scope"]["not_live_cells"]] == [
        expected
    ]


@pytest.mark.parametrize("state", list(gate.LIVE_READINESS_STATES))
def test_both_live_states_are_in_scope(tmp_path, state):
    _build(tmp_path, policy=None, readiness_state=state)
    result = gate.evaluate(tmp_path)
    assert _kinds(result) == ["missing-policy"]
    assert result["violations"][0]["readiness_state"] == state


def test_a_baseline_without_a_native_episode_block_is_never_asked(tmp_path):
    """The key belongs to the native role graph; a direct arm has no graph."""

    _build(tmp_path, policy=None, native=False)
    result = gate.evaluate(tmp_path)
    assert result["passed"] is True
    assert result["checked_baselines"] == [BASELINE]


def test_a_prose_consumed_cell_reduces_to_its_leading_word(tmp_path):
    _build(tmp_path, policy=None, consumed="no; registered before read")
    assert _kinds(gate.evaluate(tmp_path)) == ["missing-policy"]
    _build(tmp_path / "second", policy=None, consumed="**yes** (2 transcripts read)")
    assert gate.evaluate(tmp_path / "second")["passed"] is True


def test_a_missing_ledger_is_fail_closed(tmp_path):
    _build(tmp_path, policy="deliver-latest-or-abstain")
    (tmp_path / "docs" / "exposure-ledger.md").unlink()
    with pytest.raises(gate.FiniteCompletionPolicyCheckError, match="exposure-ledger"):
        gate.evaluate(tmp_path)
    assert gate.main(["--repo-root", str(tmp_path)]) == 1
