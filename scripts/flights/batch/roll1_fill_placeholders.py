"""Fill cell ROLL-1's PENDING_ placeholders in both baseline fragments from a JSON map {placeholder_token: value}.

Each token (e.g. PENDING_STAGE3_CONSTRUCTION_R01_INTENT_BOUNDARY_QUERY_VECTORS_SHA256) is replaced wherever it appears as a
whole JSON string value; every `stage3_pending_placeholders` entry whose `path` is fully resolved afterwards moves to
`stage3_placeholders_filled` with the provenance note given by --by. Refuses a token that does not occur exactly once per
fragment and a value that still contains PENDING_. Windows Python from the study root; commit and re-pin afterwards.

    python scripts/flights/batch/roll1_fill_placeholders.py --values fill.json --by "preparation 2 encode-v1 receipt ..."
"""
import argparse
import io
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
FRAGMENTS = (
    "configs/baseline/slurp-native-stage3-rollout-baseline-v1.json",
    "configs/baseline/slurp-native-stage3-rollout-smoke-4-baseline-v1.json",
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--values", required=True, help="JSON file {PENDING_TOKEN: value}")
    ap.add_argument("--by", required=True, help="provenance note recorded for every filled placeholder")
    ap.add_argument("--date", default="2026-09-22")
    a = ap.parse_args()
    values = json.load(io.open(a.values, encoding="utf-8"))
    for tok, val in values.items():
        if not tok.startswith("PENDING_") or "PENDING_" in str(val):
            raise SystemExit(f"bad fill: {tok} -> {str(val)[:60]}")
    for p in FRAGMENTS:
        raw = io.open(p, encoding="utf-8", newline="").read()
        for tok, val in values.items():
            n = raw.count(json.dumps(tok))
            if n != 1:
                raise SystemExit(f"{p}: token {tok} occurs {n} times (expected 1)")
            raw = raw.replace(json.dumps(tok), json.dumps(val))
        d = json.loads(raw)
        text = json.dumps(d)
        keep, moved = [], []
        for e in d.get("stage3_pending_placeholders", []):
            still = "PENDING_" in json.dumps(_get(d, e.get("path", "")))
            (keep if still else moved).append(e)
        d["stage3_pending_placeholders"] = keep
        d["stage3_placeholders_filled"] = (d.get("stage3_placeholders_filled") or []) + [
            {"path": e.get("path"), "filled": a.date, "by": a.by} for e in moved]
        m = re.search(r"\n( +)\"", raw); ind = len(m.group(1)) if m else 2
        io.open(p, "w", encoding="utf-8", newline="").write(json.dumps(d, indent=ind, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
        print(p, "filled", len(values), "| placeholders moved", len(moved), "| left", len(keep), "| PENDING_ strings left", text.count("PENDING_") - sum(1 for _ in keep) * 0)


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
