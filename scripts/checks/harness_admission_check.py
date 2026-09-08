#!/usr/bin/env python3
"""Model-free gate over the living harness-admission receipt (WAVE W4).

The design note's admission gate (``docs/readiness/
2026-09-08-agent-system-episode-and-core-pressure-v1.md`` section 8) says three
things a machine can check, and until this script existed none of them was
checked:

1. **The contrast is one config key, never a second code path.** So every
   entry in ``docs/receipts/harness-admission.json`` must name the table and
   the key that switch its module, that key must resolve in one of the four
   config tables (``rails.config_tables``), and its OFF arm must be that
   table's null arm -- the arm that composes to the same config hash as the
   table being absent, which is what makes OFF a twin of the pre-table
   baseline rather than a third cell identity. A ``proof`` field names the
   test that composes both arms and asserts the one-key property, and that
   test has to exist.

2. **The default plan contains only admitted or neutral modules.** Every
   ADMITTED or NEUTRAL entry must appear in at least one default plan for its
   own carrier -- an admission that never reaches a plan is a receipt nobody
   acted on.

3. **Harmful modules never enter a plan.** Nor does a module whose admission
   is provisional with its obligation UNMET: the KC-E1f verdict note fixed
   that consequence before the verdict was known ("until then ... NO entry
   into the default plan"), and a rule that lives only in prose is not a rule.

A "default plan" is a committed config fragment the receipt itself names in
``default_plans`` -- declared, never inferred, because an experimental ON arm
is a config fragment carrying a table too and reading those as default plans
would admit every module the moment it was first tried.

Zero model contacts, zero GPU, no network, no ``SPEECHRL_DATA_DIR`` read.

Flags: ``--repo-root``, ``--receipt``, ``--json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT_DEFAULT / "src"))

from speech_aware_evidence_acquisition.rails.config_tables import (  # noqa: E402
    CONFIG_TABLE_NAMES,
    NULL_ARMS,
    ConfigTableError,
    resolve_switch_key,
)

RECEIPT_RELPATH = "docs/receipts/harness-admission.json"
EXPECTED_SCHEMA = "saea-harness-admission-v2"

#: The statuses whose modules belong in a default plan, and the one that
#: never does. ``PENDING`` is neither: a registered, undecided module has
#: nothing to enforce yet.
PLAN_STATUSES = ("ADMITTED", "NEUTRAL")
FORBIDDEN_STATUS = "HARMFUL"

REQUIRED_TOP_LEVEL = (
    "default_plans",
    "entries",
    "gate",
    "schema",
    "status_values",
    "switch_rule",
)
REQUIRED_ENTRY_KEYS = ("carrier", "evidence", "module", "row", "status", "switch")
REQUIRED_SWITCH_KEYS = ("key", "off", "on", "proof", "table")


class HarnessAdmissionCheckError(RuntimeError):
    """The receipt could not be read at all."""


def _read_receipt(path: Path) -> Mapping[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise HarnessAdmissionCheckError(f"cannot read {path}: {error}") from error
    if not isinstance(document, dict):
        raise HarnessAdmissionCheckError(f"{path} must be a JSON object")
    return document


def _is_blocked(entry: Mapping[str, Any]) -> tuple[bool, str]:
    """Whether this entry's module is barred from every default plan, and why."""

    if entry.get("status") == FORBIDDEN_STATUS:
        return True, "status HARMFUL"
    provisional = entry.get("provisional")
    if isinstance(provisional, Mapping) and provisional.get("state") == "UNMET":
        return True, "provisional obligation UNMET"
    return False, ""


def _switch_present(fragment: Mapping[str, Any], table: str, entry_key: str) -> bool:
    """Whether ``fragment`` arms ``entry_key`` of ``table`` with a non-null arm.

    The table's own null arm is not "present": that is the OFF arm, and a
    plan declaring it is a plan the module is switched off in.
    """

    block = fragment.get(table)
    if any(block == arm for arm in NULL_ARMS) or not isinstance(block, Mapping):
        return False
    return _names_key(block, entry_key)


def _names_key(value: object, entry_key: str) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == entry_key and not any(child == arm for arm in NULL_ARMS):
                return True
            if _names_key(child, entry_key):
                return True
    return False


def _check_switch(entry: Mapping[str, Any], repo_root: Path, where: str) -> list[str]:
    failures: list[str] = []
    switch = entry.get("switch")
    if not isinstance(switch, Mapping):
        return [f"{where}: 'switch' must be an object naming the module's one key"]
    missing = sorted(set(REQUIRED_SWITCH_KEYS) - set(switch))
    if missing:
        failures.append(f"{where}.switch is missing {missing}")
        return failures
    table = switch["table"]
    if table not in CONFIG_TABLE_NAMES:
        failures.append(
            f"{where}.switch.table is {table!r}; the config tables are "
            f"{list(CONFIG_TABLE_NAMES)}"
        )
        return failures
    try:
        resolve_switch_key(table, switch["key"])
    except ConfigTableError as error:
        failures.append(f"{where}.switch.key: {error}")
    if not any(switch["off"] == arm for arm in NULL_ARMS):
        failures.append(
            f"{where}.switch.off is {switch['off']!r}; the OFF arm of a module must "
            f"be its table's null arm ({list(NULL_ARMS)}), which composes to the "
            "same config hash as the table being absent -- anything else makes the "
            "OFF arm a third cell identity rather than a twin"
        )
    if switch["on"] is None or any(switch["on"] == arm for arm in NULL_ARMS):
        failures.append(f"{where}.switch.on is the null arm; an ON arm must arm something")
    failures.extend(_check_proof(switch["proof"], repo_root, where))
    return failures


def _check_proof(proof: object, repo_root: Path, where: str) -> list[str]:
    if not isinstance(proof, str) or "::" not in proof:
        return [f"{where}.switch.proof must be a '<test file>::<test name>' node id"]
    relpath, _, test_name = proof.partition("::")
    path = repo_root / relpath
    if not path.is_file():
        return [f"{where}.switch.proof names {relpath}, which does not exist"]
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [f"{where}.switch.proof: cannot read {relpath}: {error}"]
    if f"def {test_name}(" not in source:
        return [f"{where}.switch.proof names {test_name}, which {relpath} does not define"]
    return []


def _load_plans(document: Mapping[str, Any], repo_root: Path) -> tuple[list[str], list[dict]]:
    failures: list[str] = []
    plans: list[dict] = []
    declared = document.get("default_plans")
    if not isinstance(declared, list):
        return ["'default_plans' must be a list (empty is legal and is a statement)"], []
    for index, plan in enumerate(declared):
        where = f"default_plans[{index}]"
        if not isinstance(plan, Mapping):
            failures.append(f"{where} must be an object with 'carrier' and 'config'")
            continue
        missing = sorted({"carrier", "config"} - set(plan))
        if missing:
            failures.append(f"{where} is missing {missing}")
            continue
        path = repo_root / str(plan["config"])
        if not path.is_file():
            failures.append(f"{where} names {plan['config']}, which does not exist")
            continue
        try:
            fragment = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            failures.append(f"{where}: cannot read {plan['config']}: {error}")
            continue
        if not isinstance(fragment, dict):
            failures.append(f"{where}: {plan['config']} must be a JSON object")
            continue
        plans.append(
            {"carrier": plan["carrier"], "config": str(plan["config"]), "fragment": fragment}
        )
    return failures, plans


def evaluate(repo_root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    path = receipt_path or (repo_root / RECEIPT_RELPATH)
    document = _read_receipt(path)
    failures: list[str] = []

    missing = sorted(set(REQUIRED_TOP_LEVEL) - set(document))
    if missing:
        failures.append(f"the receipt is missing top-level key(s) {missing}")
    if document.get("schema") != EXPECTED_SCHEMA:
        failures.append(
            f"schema is {document.get('schema')!r}, expected {EXPECTED_SCHEMA!r}"
        )
    statuses = document.get("status_values")
    known_statuses = set(statuses) if isinstance(statuses, Mapping) else set()

    plan_failures, plans = _load_plans(document, repo_root)
    failures.extend(plan_failures)

    entries = document.get("entries")
    if not isinstance(entries, list):
        failures.append("'entries' must be a list")
        entries = []

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, entry in enumerate(entries):
        where = f"entries[{index}]"
        if not isinstance(entry, Mapping):
            failures.append(f"{where} must be an object")
            continue
        entry_missing = sorted(set(REQUIRED_ENTRY_KEYS) - set(entry))
        if entry_missing:
            failures.append(f"{where} is missing {entry_missing}")
            continue
        module = str(entry["module"])
        carrier = str(entry["carrier"])
        where = f"entries[{index}] ({module!r} on {carrier!r})"
        if (module, carrier) in seen:
            failures.append(f"{where}: a second entry decides the same module and carrier")
        seen.add((module, carrier))
        status = entry["status"]
        if known_statuses and status not in known_statuses:
            failures.append(
                f"{where}: status {status!r} is not one of {sorted(known_statuses)}"
            )
        switch_failures = _check_switch(entry, repo_root, where)
        failures.extend(switch_failures)

        blocked, reason = _is_blocked(entry)
        table = entry["switch"].get("table") if isinstance(entry["switch"], Mapping) else None
        entry_key = None
        if not switch_failures and table in CONFIG_TABLE_NAMES:
            entry_key = resolve_switch_key(table, entry["switch"]["key"])

        carrying = (
            [
                plan["config"]
                for plan in plans
                if plan["carrier"] == carrier
                and _switch_present(plan["fragment"], table, entry_key)
            ]
            if entry_key is not None
            else []
        )
        if blocked and carrying:
            failures.append(
                f"{where}: {reason}, but it is armed in default plan(s) {carrying}; a "
                "module in this state never enters a plan"
            )
        if not blocked and status in PLAN_STATUSES and not carrying:
            failures.append(
                f"{where}: status {status} with no blocking obligation, but no default "
                f"plan for {carrier!r} arms {entry['switch']['key']!r}; an admitted "
                "module that reaches no plan is a receipt nobody acted on"
            )
        rows.append(
            {
                "blocked": blocked,
                "blocked_reason": reason,
                "carrier": carrier,
                "in_default_plans": carrying,
                "module": module,
                "status": status,
                "switch_key": entry["switch"].get("key"),
                "table": table,
            }
        )

    return {
        "schema": "saea-harness-admission-check-v1",
        "receipt": str(path),
        "repo_root": str(repo_root),
        "default_plans": [
            {"carrier": plan["carrier"], "config": plan["config"]} for plan in plans
        ],
        "entries": rows,
        "failures": failures,
        "passed": not failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--receipt", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        data = evaluate(args.repo_root.resolve(), args.receipt)
    except HarnessAdmissionCheckError as exc:
        print(f"harness admission check: FAIL: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0 if data["passed"] else 1

    for failure in data["failures"]:
        print(f"harness admission check: FAIL: {failure}")
    if data["failures"]:
        print(f"harness admission check: FAIL ({len(data['failures'])} finding(s))")
        return 1

    blocked = sum(1 for row in data["entries"] if row["blocked"])
    print(
        "harness admission check: PASS "
        f"({len(data['entries'])} module(s), {blocked} barred from every default "
        f"plan, {len(data['default_plans'])} default plan(s))"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
