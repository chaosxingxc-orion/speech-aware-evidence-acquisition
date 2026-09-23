"""Fill a cell's PENDING_ placeholders in its fragments from a JSON map {placeholder_token: value}.

Each token (e.g. PENDING_STAGE3_CONSTRUCTION_R01_INTENT_BOUNDARY_QUERY_VECTORS_SHA256) is replaced wherever it appears as a
whole JSON string value; every `stage3_pending_placeholders` entry whose `path` is fully resolved afterwards moves to
`stage3_placeholders_filled` with the provenance note given by --by. Refuses a value that still contains PENDING_ and a
token that occurs nowhere in the whole fragment set. Windows Python from the study root; commit and re-pin afterwards.

    python scripts/flights/batch/roll1_fill_placeholders.py --values fill.json --by "preparation 2 encode-v1 receipt ..."

--fragments names the fragments to rewrite; the default is cell ROLL-1's two baselines, so the ROLL-1 invocation above is
unchanged. --occurrence-policy is the per-fragment multiplicity rule and defaults to ROLL-1's own `exactly-one`:

  exactly-one   every token occurs exactly once in every named fragment (the ROLL-1 rule, unchanged)
  at-least-one  every token occurs at least once in every named fragment
  any           a token may be absent from a given fragment, as long as it occurs somewhere in the set

The looser policies exist for the Stage-3 ADV-1 / CELL-1 packages, where one release hash is pinned by several held cells
of one experiment fragment and a twin token appears only in the twin's baselines
(docs/readiness/2026-09-22-slurp-stage3-advantage-r01-v1/fill-after-roll1-seal.json). Under every policy a token that
matches nothing anywhere is a typo and is refused, and a fragment that carries no `stage3_pending_placeholders` block
keeps none: the documentation keys are touched only where they already exist.
"""
import argparse
import io
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROLL1_FRAGMENTS = (
    "configs/baseline/slurp-native-stage3-rollout-baseline-v1.json",
    "configs/baseline/slurp-native-stage3-rollout-smoke-4-baseline-v1.json",
)
FRAGMENTS = ROLL1_FRAGMENTS  # backwards-compatible name for importers
OCCURRENCE_POLICIES = ("exactly-one", "at-least-one", "any")
PLACEHOLDER_KEY = "stage3_pending_placeholders"
FILLED_KEY = "stage3_placeholders_filled"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--values", required=True, help="JSON file {PENDING_TOKEN: value}")
    ap.add_argument("--by", required=True, help="provenance note recorded for every filled placeholder")
    ap.add_argument("--date", default="2026-09-22")
    ap.add_argument(
        "--fragments", nargs="+", default=list(ROLL1_FRAGMENTS),
        help="fragments to rewrite (default: cell ROLL-1's two baselines)",
    )
    ap.add_argument(
        "--occurrence-policy", choices=OCCURRENCE_POLICIES, default="exactly-one",
        help="per-fragment multiplicity rule (default: the ROLL-1 rule, exactly one per fragment)",
    )
    a = ap.parse_args()
    values = json.load(io.open(a.values, encoding="utf-8"))
    for tok, val in values.items():
        if not tok.startswith("PENDING_") or "PENDING_" in str(val):
            raise SystemExit(f"bad fill: {tok} -> {str(val)[:60]}")
    seen = {tok: 0 for tok in values}
    for p in a.fragments:
        raw = io.open(p, encoding="utf-8", newline="").read()
        for tok, val in values.items():
            n = raw.count(json.dumps(tok))
            _check_occurrences(p, tok, n, a.occurrence_policy)
            seen[tok] += n
            raw = raw.replace(json.dumps(tok), json.dumps(val))
        d = json.loads(raw)
        text = json.dumps(d)
        keep, moved = [], []
        for e in d.get(PLACEHOLDER_KEY, []):
            still = "PENDING_" in json.dumps(_get(d, e.get("path", "")))
            (keep if still else moved).append(e)
        if PLACEHOLDER_KEY in d:
            d[PLACEHOLDER_KEY] = keep
            d[FILLED_KEY] = (d.get(FILLED_KEY) or []) + [
                {"path": e.get("path"), "filled": a.date, "by": a.by} for e in moved]
        m = re.search(r"\n( +)\"", raw); ind = len(m.group(1)) if m else 2
        io.open(p, "w", encoding="utf-8", newline="").write(json.dumps(d, indent=ind, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
        print(p, "filled", len(values), "| placeholders moved", len(moved), "| left", len(keep), "| PENDING_ strings left", text.count("PENDING_") - sum(1 for _ in keep) * 0)
    missing = sorted(tok for tok, n in seen.items() if n == 0)
    if missing:
        raise SystemExit(f"tokens matched nothing in any fragment: {missing}")


def _check_occurrences(fragment, token, count, policy):
    """Fail closed when a fragment's occurrence count breaks the chosen policy."""

    if policy == "exactly-one" and count != 1:
        raise SystemExit(f"{fragment}: token {token} occurs {count} times (expected 1)")
    if policy == "at-least-one" and count < 1:
        raise SystemExit(f"{fragment}: token {token} occurs {count} times (expected at least 1)")


def _get(d, path):
    """Resolve a dotted path with [n] indexes; returns None when absent."""
    cur = d
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        if part.startswith("["):
            idx = int(part[1:-1])
            cur = cur[idx] if isinstance(cur, list) and idx < len(cur) else None
        else:
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


if __name__ == "__main__":
    main()
