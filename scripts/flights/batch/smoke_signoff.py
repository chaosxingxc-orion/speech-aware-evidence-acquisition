#!/usr/bin/env python3
"""Machine sign-off between a smoke and its column flight (owner ruling 314 A). Model-free.

Given a package's registered sign-off conditions (``saea-smoke-signoff-conditions-v1``) and the smoke
decode-cost table a reader wrote, decide PASS or FAIL. PASS writes the marker file (first line: the
signer, the verdict and a UTC stamp; then the evidence as JSON) and removes a stale ``<marker>.refused``.
FAIL writes ``<marker>.refused`` with the failing conditions and never writes the marker.

    python -B scripts/flights/batch/smoke_signoff.py --conditions C.json --data-root DIR --marker M [--veto-minutes N]

Exit codes: 0 PASS (or a marker already present: never overwritten), 3 FAIL (refused file written), 2 usage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import operator
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

CONDITIONS_SCHEMA = "saea-smoke-signoff-conditions-v1"
MARKER_SCHEMA = "saea-smoke-signoff-marker-v1"
REFUSED_SCHEMA = "saea-smoke-signoff-refused-v1"
SIGNER = "machine sign-off under owner ruling 314 A"
OPS = {"<=": operator.le, "<": operator.lt, ">=": operator.ge, ">": operator.gt, "==": operator.eq, "!=": operator.ne}


class ConditionsError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_conditions(c: Any) -> None:
    if not isinstance(c, dict) or c.get("schema") != CONDITIONS_SCHEMA:
        raise ConditionsError(f"conditions schema must be {CONDITIONS_SCHEMA}")
    for key in ("package", "table_schema", "expected_arms", "no_think_nodes", "no_think_max", "every_node_max", "arm_mix"):
        if key not in c:
            raise ConditionsError(f"conditions lack {key!r}")
    if not isinstance(c["expected_arms"], list) or not c["expected_arms"]:
        raise ConditionsError("expected_arms must be a nonempty list")
    if not isinstance(c["no_think_nodes"], dict):
        raise ConditionsError("no_think_nodes must map arm -> [nodes]")
    mix = c["arm_mix"]
    if not isinstance(mix, dict) or not isinstance(mix.get("max_ratio"), (int, float)) or mix["max_ratio"] <= 0:
        raise ConditionsError("arm_mix.max_ratio must be a positive number")
    for extra in c.get("extras", []):
        if extra.get("op") not in OPS or "path" not in extra or "value" not in extra or "id" not in extra:
            raise ConditionsError(f"bad extra condition {extra!r}")


def lookup(doc: Any, dotted: str) -> list[tuple[str, Any]]:
    """Resolve a dotted path; ``*`` expands over dict keys. Raises KeyError when a segment is missing."""
    found: list[tuple[str, Any]] = [("", doc)]
    for seg in dotted.split("."):
        nxt: list[tuple[str, Any]] = []
        for prefix, node in found:
            if not isinstance(node, Mapping):
                raise KeyError(prefix + "." + seg)
            keys = list(node) if seg == "*" else [seg]
            for k in keys:
                if k not in node:
                    raise KeyError((prefix + "." + k).lstrip("."))
                nxt.append(((prefix + "." + k).lstrip("."), node[k]))
        found = nxt
    return found


def _check(cid: str, observed: Any, op: str, limit: Any) -> dict:
    ok = isinstance(observed, (int, float)) and not isinstance(observed, bool) and OPS[op](observed, limit)
    if op in ("==", "!="):
        ok = OPS[op](observed, limit)
    return {"id": cid, "observed": observed, "op": op, "limit": limit, "ok": bool(ok)}


def evaluate(c: Mapping, table: Mapping) -> list[dict]:
    checks: list[dict] = []
    checks.append(_check("table.schema", table.get("schema"), "==", c["table_schema"]))
    arms = table.get("arms") if isinstance(table.get("arms"), Mapping) else {}
    for arm in c["expected_arms"]:
        checks.append(_check(f"arm-present/{arm}", arm in arms, "==", True))
    registered_nt = {(a, n) for a, nodes in c["no_think_nodes"].items() for n in nodes}
    min_contacts = c.get("min_contacts_per_node", 1)
    for arm, nodes in arms.items():
        for node, row in (nodes.items() if isinstance(nodes, Mapping) else ()):
            base = f"{arm}/{node}"
            checks.append(_check(f"{base}/contacts", row.get("contacts"), ">=", min_contacts))
            for field, limit in c["every_node_max"].items():
                checks.append(_check(f"{base}/{field}", row.get(field), "<=", limit))
            is_nt = (arm, node) in registered_nt
            checks.append(_check(f"{base}/mode-matches-registration", row.get("mode") == "no-think", "==", is_nt))
            if is_nt:
                for field, limit in c["no_think_max"].items():
                    checks.append(_check(f"{base}/{field}", row.get(field), "<=", limit))
    for arm, node in sorted(registered_nt):
        checks.append(_check(f"no-think-node-present/{arm}/{node}", isinstance(arms.get(arm), Mapping) and node in arms[arm], "==", True))
    mix = c["arm_mix"]
    tp = table.get("throughput") if isinstance(table.get("throughput"), Mapping) else {}
    measured = tp.get(mix.get("measured_key", "arm_mix_measured_rows"))
    registered = tp.get(mix.get("registered_key", "arm_mix_registered_rows"))
    if isinstance(measured, (int, float)) and isinstance(registered, (int, float)) and registered > 0:
        checks.append(_check("arm-mix/measured<=ratio*registered", measured, "<=", mix["max_ratio"] * registered))
    else:
        checks.append(_check("arm-mix/measured<=ratio*registered", None, "<=", None))
    for extra in c.get("extras", []):
        try:
            for path, value in lookup(table, extra["path"]):
                checks.append(_check(f"extra/{extra['id']}/{path}", value, extra["op"], extra["value"]))
        except KeyError as error:
            checks.append(_check(f"extra/{extra['id']}", f"missing {error}", extra["op"], extra["value"]))
    return checks


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def run(args: argparse.Namespace) -> int:
    marker = Path(args.marker)
    refused = marker.with_name(marker.name + ".refused")
    if marker.is_file() and marker.stat().st_size > 0:
        print(f"smoke sign-off: marker already present, not overwritten: {marker}")
        return 0
    now = args.utc or utc_now()
    cond_path = Path(args.conditions)
    table_path = None
    checks: list[dict] = []
    try:
        conditions = json.loads(cond_path.read_text(encoding="utf-8"))
        validate_conditions(conditions)
        table_path = Path(args.table) if args.table else Path(args.data_root or ".") / conditions["table_relpath"]
        table = json.loads(table_path.read_text(encoding="utf-8"))
        checks = evaluate(conditions, table)
    except (OSError, ValueError, KeyError) as error:
        checks = [{"id": "inputs", "observed": f"{type(error).__name__}: {error}", "op": "==", "limit": "readable", "ok": False}]
        conditions = {"package": "unknown"}
    failing = [x for x in checks if not x["ok"]]
    evidence = {
        "schema": MARKER_SCHEMA if not failing else REFUSED_SCHEMA, "signer": SIGNER, "verdict": "PASS" if not failing else "FAIL",
        "utc": now, "package": conditions.get("package"), "conditions_path": str(cond_path),
        "conditions_sha256": sha256_file(cond_path) if cond_path.is_file() else None,
        "table_path": str(table_path) if table_path else None,
        "table_sha256": sha256_file(table_path) if table_path and table_path.is_file() else None,
        "veto_minutes": args.veto_minutes, "checks_total": len(checks), "checks_failed": len(failing),
        "checks": checks if not failing else failing,
    }
    body = json.dumps(evidence, indent=1, sort_keys=True)
    if failing:
        first = f"{SIGNER}: REFUSED {now} package={evidence['package']} failing={len(failing)}/{len(checks)}"
        _atomic_write(refused, first + "\n" + body + "\n")
        print(first)
        for x in failing[:12]:
            print(f"  FAIL {x['id']}: observed {x['observed']!r} needs {x['op']} {x['limit']!r}")
        return 3
    first = (f"{SIGNER}: PASS {now} package={evidence['package']} conditions={str(evidence['conditions_sha256'])[:12]} "
             f"table={str(evidence['table_sha256'])[:12]} checks={len(checks)}/{len(checks)}")
    _atomic_write(marker, first + "\n" + body + "\n")
    if refused.exists():
        refused.unlink()
    print(first)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("--conditions", required=True)
    p.add_argument("--table", default=None, help="the smoke decode-cost json (default: <data-root>/<conditions.table_relpath>)")
    p.add_argument("--data-root", default=os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR"))
    p.add_argument("--marker", required=True)
    p.add_argument("--veto-minutes", type=float, default=None)
    p.add_argument("--utc", default=None, help="test hook: the stamp to record")
    return run(p.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
