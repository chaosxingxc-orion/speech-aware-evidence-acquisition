#!/usr/bin/env python3
"""Model-free gate: every unflown native cell declares its failure-mode policies.

Two keys, one rule, one script: ``native_episode.finite_completion_policy``
(item E13) and ``native_episode.react_exhaustion_policy`` (item E22 -- the
ReAct-exhaustion disposition, not the Earnings-22 carrier). Both are
FAILURE MODES of the same native episode, both default to ``"raise"``, both
lost a campaign to that default, and both must be armed before a cell flies,
so they are enforced together rather than by two scripts that would drift.

Item E13 (2026-09-19). On 2026-09-18 the B7a recovery arm
(``SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1``, attempt
``attempt-slurp-native-ncp-l1-anchor-train-fold-a-generation-recovery-v1``,
study commit ``2f039fa6``) died after 1,451 charged contacts with

    NativeEpisodeError: native episode node failed: [100054] component
    'reviewer_1_role' execute 'invoke' error, reason='metered completion is
    non-authoritative because finish_reason is 'length''

because ONE Reviewer completion reached the serving geometry's 512-token
output cap. Nothing was broken: ``rails.native_episode_config`` reads
``native_episode.finite_completion_policy`` with the default ``"raise"``, and
``"raise"`` means "abort the flight". The harness has implemented the other
arm, ``"deliver-latest-or-abstain"``, since the Audio2Tool cells -- the row is
retained, the latest delivery-eligible Solver draft (or an abstention) is
delivered, and the receipt records a ``finite_completion`` terminal
disposition naming the interrupted role. The A2T and Earnings native
baselines declare the key. The SLURP ones never did, so a 1,451-contact flight
was spent proving that a default nobody chose was still the default.

Item E22 (2026-09-19). On 2026-09-19 the B8b-anchor arm
(``SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1``, attempt
``attempt-slurp-native-reviewer-audit-anchor-train-fold-a-generation-v1``,
study commit ``c905ddf0``) died after 2,016 charged contacts with

    NativeEpisodeError: review node did not return an answer

raised at component ``reviewer_1_state``. Nothing was broken there either:
the Reviewer's ReAct loop (``max_iterations`` 3) called
``saea-tool-task-contract-v1`` with ``{}`` on iterations 1/3, 2/3 and 3/3,
the pinned framework returned its own ``"Max iterations reached without
completion"`` under ``result_type`` ``"error"``, and
``reproduction.ojw.native_episode._ApplyRole`` refused the non-answer. Two
Reviewer visits of 410 reached 3/3; both took the whole flight with them.
``native_episode.react_exhaustion_policy`` ``"continue-without-answer"``
ends such a visit with NO finding and lets the row deliver, recording a
``react_exhaustion`` visit disposition. The key defaults to ``"raise"``.

A rule that lives only in a verdict note is not a rule. This script is the
rule.

**Enforced (a failure exits 1).**

1. **Every LIVE, UNFLOWN native cell arms BOTH keys.** For each generation plan
   under ``docs/readiness/<package>/`` (``*generation-plan*.json``) this reads
   the plan's run id, looks that run id up in ``docs/exposure-ledger.md`` --
   with the repository's own table parser,
   ``contracts._parse_ledger_tables``, so a row hidden in a comment or a fence
   is exactly as invisible here as it is to the frozen-core gate -- and
   resolves the plan to its experiment fragment's cell(s). A cell is IN SCOPE
   when BOTH hold:

   * its run id has a ledger row whose ``consumed`` cell says ``no`` -- the
     cell has not flown, or has not been closed; and
   * its ``readiness.state`` is one of :data:`LIVE_READINESS_STATES`
     (``ready``, ``held``) -- the cell is still on the queue.

   Each in-scope cell's baseline config, if it carries a ``native_episode``
   block, must declare ``finite_completion_policy`` as
   ``"deliver-latest-or-abstain"`` AND ``react_exhaustion_policy`` as
   ``"continue-without-answer"``. Each missing or wrong key is its own
   finding, named by key, so a cell that arms one and not the other is told
   which one is missing.

   Everything else is OUT OF SCOPE and counted in the summary. A plan with no
   ledger row has no registration to enforce against. A consumed row names
   bytes that already flew, which this repository never rewrites. And a cell
   whose readiness state is anything but live -- ``superseded`` for a package
   rebased onto a newer comparator, ``preparation-pending``, or no readiness
   block at all on the pre-readiness fragments -- will never fly in that form,
   so demanding an edit to it would be demanding an edit to a dead cell. The
   summary names every such state and its count, so a state word this gate has
   not seen before is visible rather than silent.

2. **No baseline anywhere declares a third value.** Independently of scope,
   every ``configs/baseline/*.json`` whose ``native_episode`` block carries
   ``finite_completion_policy`` must carry it as
   ``"deliver-latest-or-abstain"``, and one that carries
   ``react_exhaustion_policy`` must carry it as
   ``"continue-without-answer"``. The parser also accepts the literal
   ``"raise"`` for either; writing the abort default out loud is legal to the
   loader and refused here, because a cell that means to abort on one of
   these failure modes should say so in its preregistration, not in a config
   leaf that reads like an oversight.

**Reported, never enforced (item E39, 2026-09-22).** Beside the two policies,
each in-scope cell's ``native_episode.finite_completion_scope`` (item E39 --
``"episode"``, the default and every pre-E39 cell's behaviour, or
``"answering-node"``, which keeps a truncated auxiliary node's text and lets
the Solver still answer) and any per-role
``native_episode.roles.<role>.max_completion_tokens`` are printed as a report
line, so the queue's truncation posture is visible without opening a config.
No value of either is required: the E35 sub10 read (docs/results/
2026-09-22-e21-native-window-e35-sub10-diagnosis.md) found the whole-episode
scope cost 95.6 % of that arm's extra error mass, but which scope a cell wants
is the coordinator's registration, not this gate's. The ONE refusal item E39
adds is a scope value outside the enum, under exactly rule 2's reasoning: a
third value reads like an oversight and the loader would refuse it at the
flight, later and more expensively.

This gate never edits a config. A violation is repaired by the coordinator
re-pinning the cell (``scripts/flights/repin_cell.py``), which is the only
path that recomputes the package's dependent hashes in the same cycle.

Zero model contacts, zero GPU, no network, no ``SPEECHRL_DATA_DIR`` read.

Flags: ``--repo-root``, ``--ledger``, ``--json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]

EXPOSURE_LEDGER = Path("docs/exposure-ledger.md")
READINESS = Path("docs/readiness")
EXPERIMENT_DIR = Path("configs/experiment")
BASELINE_DIR = Path("configs/baseline")

#: The plan files this gate reads: one directory below ``docs/readiness``,
#: because a readiness PACKAGE is a directory and a loose note is not a plan.
PLAN_GLOB = "*/*generation-plan*.json"

#: The leaves, and the one value a cell that has not yet flown must give each.
EPISODE_BLOCK = "native_episode"
POLICY_KEY = "finite_completion_policy"
REQUIRED_POLICY = "deliver-latest-or-abstain"

#: Item E22 (the ReAct-exhaustion disposition, not the Earnings-22 carrier):
#: the second leaf, enforced under exactly the same scope rule.
REACT_POLICY_KEY = "react_exhaustion_policy"
REQUIRED_REACT_POLICY = "continue-without-answer"

#: The two, in the order the findings report them: ``(key, required value,
#: what the parser's default does when the key is absent)``.
REQUIRED_POLICIES = (
    (
        POLICY_KEY,
        REQUIRED_POLICY,
        "the parser default 'raise', which aborts the flight on a finite "
        "completion",
    ),
    (
        REACT_POLICY_KEY,
        REQUIRED_REACT_POLICY,
        "the parser default 'raise', which aborts the flight when a tool "
        "role's ReAct loop ends without an answer",
    ),
)

#: Item E39 (2026-09-22): the episode-level scope leaf and the two values it
#: may take, and the per-role leaf whose declared caps are reported beside it.
#: Neither is REQUIRED of any cell; a scope outside the enum is refused.
SCOPE_KEY = "finite_completion_scope"
SCOPE_VALUES = ("episode", "answering-node")
ROLE_CAP_KEY = "max_completion_tokens"

#: The readiness states of a cell that is still on the queue. The vocabulary
#: seen in ``configs/experiment/*.json`` at 2026-09-19 is ``ready`` (141
#: cells), ``held`` (103), ``preparation-pending`` (1) and no readiness block
#: at all (208, the pre-readiness fragments); ``superseded`` is the word the
#: coordinator marks a package rebased onto a newer comparator with. Only the
#: two live words are enforced, and every other state is reported by name.
LIVE_READINESS_STATES = ("ready", "held")

#: What the summary calls a cell that declares no ``readiness`` block.
NO_READINESS_STATE = "<no readiness block>"

#: The exposure ledger's own column names, as the repository's parser lowers
#: them.
RUN_COLUMN = "run/experiment id"
CONSUMED_COLUMN = "consumed"


class FiniteCompletionPolicyCheckError(RuntimeError):
    """The gate could not read something it must read."""


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FiniteCompletionPolicyCheckError(f"cannot read {label}: {error}") from error


def _parse_exposure_ledger(repo_root: Path, ledger: Path) -> dict[str, dict[str, str]]:
    """``{run id: row}`` for every contract row of the exposure ledger.

    The table parser is the repository's own
    (``contracts._parse_ledger_tables``), which is what the frozen-core gate
    reads, so this check and that gate agree on what a registration is.
    """

    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    try:
        from speech_aware_evidence_acquisition.contracts import (  # noqa: PLC0415
            _parse_ledger_tables,
        )
    except Exception as error:  # pragma: no cover - import environment problem
        raise FiniteCompletionPolicyCheckError(
            f"cannot import the repository's exposure-ledger parser from {src}: {error}"
        ) from error

    path = repo_root / ledger
    if not path.is_file():
        raise FiniteCompletionPolicyCheckError(f"missing {ledger}")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        parsed = _parse_ledger_tables(text)
    except Exception as error:
        raise FiniteCompletionPolicyCheckError(
            f"cannot parse {ledger}: {error}"
        ) from error
    rows: dict[str, dict[str, str]] = {}
    for row in parsed:
        run_id = str(row.get(RUN_COLUMN, "")).strip()
        if run_id:
            rows.setdefault(run_id, dict(row))
    return rows


def _consumed(row: dict[str, str]) -> str:
    """The ``consumed`` cell reduced to its leading verdict word.

    Rows are prose as often as they are tokens: ``no; registered before read``
    and ``**yes** (2 transcripts read)`` are both in the ledger today. The
    leading word before any ``;`` or ``(``, stripped of markdown emphasis, is
    what the column means; anything this cannot reduce to ``no`` is treated as
    NOT unflown, which is the fail-safe direction (it puts the plan out of
    scope rather than demanding an edit to bytes that may already have flown).
    """

    cell = str(row.get(CONSUMED_COLUMN, "")).replace("*", "").strip().lower()
    return cell.split(";")[0].split("(")[0].strip()


def _readiness_state(cell: dict[str, Any]) -> str:
    readiness = cell.get("readiness")
    if not isinstance(readiness, dict):
        return NO_READINESS_STATE
    state = readiness.get("state")
    return state if isinstance(state, str) and state.strip() else NO_READINESS_STATE


def _plan_run_id(plan: dict[str, Any]) -> str | None:
    """The run id a generation plan names, across the three plan shapes.

    ``saea-registered-generation-plan-v1`` carries ``execution_plan``,
    ``saea-generation-execution-plan-preparation-v1`` carries
    ``prospective_execution_plan``, and a bare ``saea-execution-plan-v1``
    file IS the execution plan.
    """

    for holder in ("execution_plan", "prospective_execution_plan"):
        block = plan.get(holder)
        if isinstance(block, dict) and isinstance(block.get("run_id"), str):
            return block["run_id"]
    run_id = plan.get("run_id")
    return run_id if isinstance(run_id, str) else None


def _experiment_index(repo_root: Path) -> dict[str, list[str]]:
    """``{run id: [experiment fragment stem, ...]}`` over ``configs/experiment``.

    The fallback for a plan shape that names no ``experiment``: a fragment
    that declares a cell for this run id IS that plan's experiment.
    """

    index: dict[str, list[str]] = {}
    directory = repo_root / EXPERIMENT_DIR
    if not directory.is_dir():
        return index
    for path in sorted(directory.glob("*.json")):
        try:
            fragment = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(fragment, dict):
            continue
        for cell in fragment.get("cells") or []:
            if isinstance(cell, dict) and isinstance(cell.get("run_id"), str):
                index.setdefault(cell["run_id"], []).append(path.stem)
    return index


def _fragments_for(
    plan: dict[str, Any], run_id: str, repo_root: Path, index: dict[str, list[str]]
) -> list[str]:
    experiment = plan.get("experiment")
    if isinstance(experiment, str) and (
        repo_root / EXPERIMENT_DIR / f"{experiment}.json"
    ).is_file():
        return [experiment]
    return list(index.get(run_id, ()))


def _cells_of(fragment: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
    """The cell(s) of ``fragment`` this plan's run id composes.

    A fragment usually declares exactly the cell the plan registers, but some
    carry a whole family. When one of the cells names THIS run id, only that
    cell is read: a sibling cell's baseline is a different plan's problem.
    """

    cells = [cell for cell in (fragment.get("cells") or []) if isinstance(cell, dict)]
    return [cell for cell in cells if cell.get("run_id") == run_id] or cells


def _policy_of(baseline: dict[str, Any], key: str = POLICY_KEY) -> tuple[bool, Any]:
    """``(carries a native_episode block, the declared policy or None)``."""

    episode = baseline.get(EPISODE_BLOCK)
    if not isinstance(episode, dict):
        return False, None
    return True, episode.get(key)


def _scope_of(baseline: dict[str, Any]) -> tuple[bool, Any]:
    """Item E39: ``(carries a native_episode block, the declared scope)``.

    An absent key reads as the loader's own default, ``"episode"``, because
    that is what the flight would compose -- the report tells the reader what
    the cell DOES, not which bytes it spells.
    """

    episode = baseline.get(EPISODE_BLOCK)
    if not isinstance(episode, dict):
        return False, None
    return True, episode.get(SCOPE_KEY, SCOPE_VALUES[0])


def _role_caps_of(baseline: dict[str, Any]) -> dict[str, Any]:
    """Item E39: ``{role: max_completion_tokens}`` for the roles declaring one."""

    episode = baseline.get(EPISODE_BLOCK)
    if not isinstance(episode, dict):
        return {}
    roles = episode.get("roles")
    if not isinstance(roles, dict):
        return {}
    caps: dict[str, Any] = {}
    for role, row in sorted(roles.items()):
        if isinstance(row, dict) and row.get(ROLE_CAP_KEY) is not None:
            caps[role] = row[ROLE_CAP_KEY]
    return caps


def evaluate(repo_root: Path, ledger: Path = EXPOSURE_LEDGER) -> dict[str, Any]:
    rows = _parse_exposure_ledger(repo_root, ledger)
    index = _experiment_index(repo_root)

    violations: list[dict[str, Any]] = []
    in_scope: list[dict[str, Any]] = []
    unregistered: list[str] = []
    consumed_plans: list[str] = []
    unreadable: list[str] = []
    no_run_id: list[str] = []
    not_live: list[dict[str, str]] = []
    checked_baselines: set[str] = set()
    # Item E39 (2026-09-22): the truncation posture of every in-scope cell,
    # reported and never enforced.
    scope_report: dict[str, dict[str, Any]] = {}

    for path in sorted((repo_root / READINESS).glob(PLAN_GLOB)):
        relpath = path.relative_to(repo_root).as_posix()
        try:
            plan = _read_json(path, relpath)
        except FiniteCompletionPolicyCheckError as error:
            unreadable.append(f"{relpath}: {error}")
            continue
        if not isinstance(plan, dict):
            unreadable.append(f"{relpath}: a generation plan must be a JSON object")
            continue
        run_id = _plan_run_id(plan)
        if run_id is None:
            no_run_id.append(relpath)
            continue
        row = rows.get(run_id)
        if row is None:
            unregistered.append(f"{relpath} ({run_id})")
            continue
        if _consumed(row) != "no":
            consumed_plans.append(f"{relpath} ({run_id})")
            continue

        fragments = _fragments_for(plan, run_id, repo_root, index)
        if not fragments:
            violations.append(
                {
                    "kind": "unresolved-experiment",
                    "plan": relpath,
                    "run_id": run_id,
                    "message": (
                        f"{relpath}: run id {run_id} is registered and unconsumed, but "
                        f"no fragment under {EXPERIMENT_DIR.as_posix()} declares it and "
                        "the plan names no resolvable 'experiment'"
                    ),
                }
            )
            continue
        for stem in fragments:
            fragment_path = repo_root / EXPERIMENT_DIR / f"{stem}.json"
            fragment = _read_json(fragment_path, fragment_path.name)
            if not isinstance(fragment, dict):
                violations.append(
                    {
                        "kind": "unreadable-experiment",
                        "plan": relpath,
                        "run_id": run_id,
                        "experiment": stem,
                        "message": f"{relpath}: {stem}.json must be a JSON object",
                    }
                )
                continue
            cells = _cells_of(fragment, run_id)
            if not cells:
                violations.append(
                    {
                        "kind": "no-cell",
                        "plan": relpath,
                        "run_id": run_id,
                        "experiment": stem,
                        "message": (
                            f"{relpath}: experiment {stem} declares no cell at all"
                        ),
                    }
                )
                continue
            for cell in cells:
                state = _readiness_state(cell)
                if state not in LIVE_READINESS_STATES:
                    not_live.append(
                        {"plan": relpath, "run_id": run_id, "state": state}
                    )
                    continue
                name = cell.get("baseline_fragment")
                if not isinstance(name, str) or not name:
                    violations.append(
                        {
                            "kind": "no-baseline",
                            "plan": relpath,
                            "run_id": run_id,
                            "experiment": stem,
                            "readiness_state": state,
                            "message": (
                                f"{relpath}: experiment {stem} declares no "
                                "'baseline_fragment' for this run id"
                            ),
                        }
                    )
                    continue
                in_scope.append(
                    {
                        "plan": relpath,
                        "run_id": run_id,
                        "experiment": stem,
                        "baseline": name,
                        "readiness_state": state,
                    }
                )
                baseline_path = repo_root / BASELINE_DIR / f"{name}.json"
                if not baseline_path.is_file():
                    violations.append(
                        {
                            "kind": "missing-baseline",
                            "plan": relpath,
                            "run_id": run_id,
                            "baseline": name,
                            "readiness_state": state,
                            "message": (
                                f"{relpath}: baseline fragment {name} names "
                                f"{BASELINE_DIR.as_posix()}/{name}.json, which does "
                                "not exist"
                            ),
                        }
                    )
                    continue
                baseline = _read_json(baseline_path, baseline_path.name)
                if not isinstance(baseline, dict):
                    violations.append(
                        {
                            "kind": "unreadable-baseline",
                            "plan": relpath,
                            "run_id": run_id,
                            "baseline": name,
                            "readiness_state": state,
                            "message": f"{relpath}: {name}.json must be a JSON object",
                        }
                    )
                    continue
                checked_baselines.add(name)
                native_block, scope = _scope_of(baseline)
                if native_block:
                    scope_report[name] = {
                        "baseline": name,
                        "run_id": run_id,
                        SCOPE_KEY: scope,
                        "role_completion_caps": _role_caps_of(baseline),
                    }
                for key, required, absent_means in REQUIRED_POLICIES:
                    native, policy = _policy_of(baseline, key)
                    if not native or policy == required:
                        continue
                    violations.append(
                        {
                            "kind": "missing-policy" if policy is None else "wrong-policy",
                            "key": key,
                            "plan": relpath,
                            "run_id": run_id,
                            "experiment": stem,
                            "baseline": name,
                            "readiness_state": state,
                            "declared": policy,
                            "message": (
                                f"{relpath}: run id {run_id} is registered, unconsumed and "
                                f"{state}, and its baseline {name} declares native_episode."
                                f"{key} as "
                                + (
                                    f"ABSENT ({absent_means})"
                                    if policy is None
                                    else f"{policy!r}"
                                )
                                + f"; a live unflown native cell must declare "
                                f"{required!r}"
                            ),
                        }
                    )

    # Rule 2: repository-wide, a declared policy is never a third value.
    for path in sorted((repo_root / BASELINE_DIR).glob("*.json")):
        baseline = _read_json(path, path.name)
        if not isinstance(baseline, dict):
            continue
        for key, required, _absent_means in REQUIRED_POLICIES:
            native, policy = _policy_of(baseline, key)
            if not native or policy is None or policy == required:
                continue
            violations.append(
                {
                    "kind": "declared-third-value",
                    "key": key,
                    "plan": None,
                    "run_id": None,
                    "baseline": path.stem,
                    "declared": policy,
                    "message": (
                        f"{BASELINE_DIR.as_posix()}/{path.name}: native_episode."
                        f"{key} is {policy!r}; the only value a committed baseline "
                        f"may declare is {required!r}"
                    ),
                }
            )

    # Item E39 rule 3: repository-wide, a DECLARED scope is one of the two.
    # An absent key is the loader's default and is never a finding.
    for path in sorted((repo_root / BASELINE_DIR).glob("*.json")):
        baseline = _read_json(path, path.name)
        if not isinstance(baseline, dict):
            continue
        episode = baseline.get(EPISODE_BLOCK)
        if not isinstance(episode, dict) or SCOPE_KEY not in episode:
            continue
        declared = episode[SCOPE_KEY]
        if declared in SCOPE_VALUES:
            continue
        violations.append(
            {
                "kind": "invalid-scope",
                "key": SCOPE_KEY,
                "plan": None,
                "run_id": None,
                "baseline": path.stem,
                "declared": declared,
                "message": (
                    f"{BASELINE_DIR.as_posix()}/{path.name}: native_episode."
                    f"{SCOPE_KEY} is {declared!r}; the only values are "
                    f"{SCOPE_VALUES[0]!r} and {SCOPE_VALUES[1]!r}"
                ),
            }
        )

    state_counts = Counter(row["state"] for row in not_live)
    return {
        # E22 widened the gate from one key to two. The schema name is the
        # contract a reader binds to, so it moves with the shape.
        "schema": "saea-finite-completion-policy-check-v2",
        "repo_root": str(repo_root),
        "ledger": ledger.as_posix(),
        "required_policy": REQUIRED_POLICY,
        "required_react_exhaustion_policy": REQUIRED_REACT_POLICY,
        "required_policies": {key: value for key, value, _ in REQUIRED_POLICIES},
        # Item E39: reported, not required.
        "finite_completion_scopes": list(SCOPE_VALUES),
        "scope_report": [scope_report[name] for name in sorted(scope_report)],
        "live_readiness_states": list(LIVE_READINESS_STATES),
        "in_scope_plan_cells": in_scope,
        "in_scope_plans": sorted({row["plan"] for row in in_scope}),
        "checked_baselines": sorted(checked_baselines),
        "out_of_scope": {
            "no_ledger_row": sorted(unregistered),
            "consumed": sorted(consumed_plans),
            "no_run_id": sorted(no_run_id),
            "not_live_cells": sorted(
                not_live, key=lambda row: (row["state"], row["plan"])
            ),
            "not_live_state_counts": dict(sorted(state_counts.items())),
        },
        "unreadable_plans": sorted(unreadable),
        "violations": violations,
        "passed": not violations and not unreadable,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--ledger", type=Path, default=EXPOSURE_LEDGER)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        data = evaluate(args.repo_root.resolve(), args.ledger)
    except FiniteCompletionPolicyCheckError as error:
        print(f"native episode failure-mode policy check: FAIL: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0 if data["passed"] else 1

    for problem in data["unreadable_plans"]:
        print(f"native episode failure-mode policy check: FAIL: {problem}")
    for violation in data["violations"]:
        print(f"native episode failure-mode policy check: FAIL: {violation['message']}")

    for row in data["scope_report"]:
        caps = row["role_completion_caps"]
        rendered = (
            ", ".join(f"{role}={cap}" for role, cap in caps.items())
            if caps else "none"
        )
        print(
            f"native episode failure-mode policy check: scope: {row['baseline']} "
            f"({row['run_id']}): {SCOPE_KEY}={row[SCOPE_KEY]!r}; per-role "
            f"completion caps: {rendered}"
        )

    out_of_scope = data["out_of_scope"]
    states = ", ".join(
        f"{state} {count}"
        for state, count in out_of_scope["not_live_state_counts"].items()
    )
    summary = (
        f"native_episode.{POLICY_KEY}={REQUIRED_POLICY!r} and "
        f"native_episode.{REACT_POLICY_KEY}={REQUIRED_REACT_POLICY!r}; "
        f"{len(data['in_scope_plans'])} in-scope plan(s), "
        f"{len(data['checked_baselines'])} baseline(s) read; out of scope: "
        f"{len(out_of_scope['no_ledger_row'])} with no ledger row, "
        f"{len(out_of_scope['consumed'])} consumed, "
        f"{len(out_of_scope['no_run_id'])} naming no run id, "
        f"{len(out_of_scope['not_live_cells'])} not-live cell(s)"
        + (f" [{states}]" if states else "")
    )
    if data["passed"]:
        print(f"native episode failure-mode policy check: PASS ({summary})")
        return 0
    print(
        "native episode failure-mode policy check: FAIL "
        f"({len(data['violations']) + len(data['unreadable_plans'])} finding(s); "
        f"{summary})"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
