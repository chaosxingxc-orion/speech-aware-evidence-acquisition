#!/usr/bin/env python3
"""Read the carrier base on the Thinking core (A2T, E21, E22). Model-free: reads sealed run bytes and score files only (no model, server, tokenizer or GPU contact).

    carrier_think_read.py --stage smoke   --carrier a2t [--data-root DIR]   # decode-cost table of the sealed smoke (the machine sign-off input); no countersignature
    carrier_think_read.py --stage columns --carrier a2t                      # verify both arms are sealed and scored by the standard scorer (prints no number)
    carrier_think_read.py --stage read    --carrier a2t                      # the full read (the shell driver refuses unless the carrier's READ row is countersigned)

``smoke`` writes ``<analysis root>/smoke-decode-cost.json`` (schema ``saea-carrier-think-base-smoke-v1``) from the smoke's trace: per contact the COST channel
(completion tokens, finish reason, forced close, latency, prompt tokens, reasoning characters), the delivered content of MODEL_RESPONSE (emptiness and reasoning markers only;
no text is printed or persisted) and the request's decoding parameters (the node's own cap). ``read`` loads the two arms' ``<run>.scores.json`` (the flight's own complete
official scoring; this reader never re-scores), reports each arm's levels, the all-off minus direct difference (the in-chain A/A offset of this core on this carrier) with a
paired percentile bootstrap, the per-stratum table (A2T: per tier, with the PAPER column of arXiv:2604.22821 Table 3 beside the repo column; Earnings: per call) and the
decode-cost table of each arm. claims_benefit is false; development numbers only.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "scripts" / "flights" / "carriers"))
sys.path.insert(0, str(HERE))

import carrier_think_family as fam  # noqa: E402

BOOTSTRAP_DRAWS, BOOTSTRAP_SEED = 10000, 20261018
THINK_MARKERS = ("<think>", "</think>")


def data_root(arg: str | None) -> Path:
    value = arg or os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR")
    if not value:
        raise SystemExit("no data root: pass --data-root or set SAEA_DATA_ROOT")
    return Path(value)


def run_dir(root: Path, key: str) -> Path:
    s = fam.CELLS[key]
    return root / "runs" / s["run"] / s["attempt"]


def sealed(root: Path, key: str) -> bool:
    s = fam.CELLS[key]
    try:
        return json.loads((run_dir(root, key) / f"{s['run']}.run-manifest.json").read_text(encoding="utf-8")).get("status") == "COMPLETED"
    except (OSError, ValueError):
        return False


def quantile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return float(ordered[min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))])


def stats(values: Sequence[float]) -> dict:
    if not values:
        return {"n": 0}
    return {"n": len(values), "mean": float(sum(values) / len(values)), "p50": quantile(values, 0.5), "p90": quantile(values, 0.9), "p99": quantile(values, 0.99), "max": float(max(values))}


# ---- smoke / decode cost -----------------------------------------------------------------------------------------------------------
def contacts_of(trace_path: Path) -> tuple[list[dict], int]:
    """Group the trace by contact (``flight-NNNN/<channel>``). Returns (complete contacts, unattributed contacts: requests without a COST record)."""

    groups: dict[str, dict[str, Any]] = collections.OrderedDict()
    with trace_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rid = row.get("record_id", "")
            prefix, _, tail = rid.partition("/")
            if not prefix.startswith("flight-"):
                continue
            groups.setdefault(prefix, {})[row["channel"]] = row["payload"]
    out, unattributed = [], 0
    for prefix, g in groups.items():
        req = (g.get("MODEL_REQUEST") or {}).get("payload", {}) if isinstance(g.get("MODEL_REQUEST"), dict) else {}
        if "COST" not in g or "MODEL_REQUEST" not in g:
            unattributed += 1
            continue
        decoding = req.get("decoding_params") or {}
        out.append({"contact": prefix, "decoding": decoding, "cost": g["COST"], "response": g.get("MODEL_RESPONSE") or {}, "wire": g.get("MODEL_WIRE_RESPONSE") or {}})
    return out, unattributed


def contact_row(c: Mapping[str, Any]) -> dict:
    cost, decoding = c["cost"], c["decoding"]
    cap = decoding.get("max_tokens")
    completion = cost.get("completion_tokens")
    text = c["response"].get("text") or ""
    finish = cost.get("finish_reason") or (c["wire"].get("finish_reason"))
    thinking = decoding.get("thinking_budget_tokens") is not None
    return {
        "think": thinking, "cap": cap, "completion_tokens": completion, "prompt_tokens": cost.get("prompt_tokens"), "latency": cost.get("latency_seconds"),
        "forced_close": bool(cost.get("forced_close")), "reasoning_chars": cost.get("reasoning_chars") or 0, "finish_reason": finish,
        "cap_hit": isinstance(cap, int) and isinstance(completion, int) and completion >= cap, "empty": not str(text).strip(),
        "marker": any(m in str(text) for m in THINK_MARKERS), "length_finish": finish == "length",
    }


def decode_table(contacts: Sequence[Mapping[str, Any]], unattributed: int) -> dict:
    rows = [contact_row(c) for c in contacts]
    think = [r for r in rows if r["think"]]
    fallbacks = [r for r in rows if not r["think"]]
    lat = [r["latency"] for r in rows if isinstance(r["latency"], (int, float))]
    return {
        "contacts": len(rows), "mode": "think", "think_contacts": len(think), "fallback_contacts": len(fallbacks),
        "cap_hits": sum(r["cap_hit"] for r in rows), "empty_content": sum(r["empty"] for r in rows), "finish_reason_length": sum(r["length_finish"] for r in rows),
        "marker_in_content": sum(r["marker"] for r in rows), "forced_closes": sum(r["forced_close"] for r in rows),
        "finish_reasons": dict(collections.Counter(str(r["finish_reason"]) for r in rows)),
        "completion_tokens": stats([r["completion_tokens"] for r in rows if isinstance(r["completion_tokens"], int)]),
        "prompt_tokens": stats([r["prompt_tokens"] for r in rows if isinstance(r["prompt_tokens"], int)]),
        "latency_seconds": stats(lat), "reasoning_chars_mean": (sum(r["reasoning_chars"] for r in rows) / len(rows)) if rows else 0.0,
        "unattributed_contacts": unattributed,
    }


def smoke_stage(carrier: str, root: Path) -> dict:
    key = fam.cell_key(carrier, "smoke")
    s = fam.CELLS[key]
    if not sealed(root, key):
        raise SystemExit(f"the {carrier} smoke is not sealed (no COMPLETED run manifest under {run_dir(root, key)})")
    trace = run_dir(root, key) / f"{s['run']}.trace.jsonl"
    contacts, unattributed = contacts_of(trace)
    row = decode_table(contacts, unattributed)
    registered = fam.seconds_per_contact(carrier)
    measured = row["latency_seconds"].get("mean")
    table = {
        "schema": fam.SMOKE_TABLE_SCHEMA, "carrier": carrier, "run_id": s["run"], "attempt_id": s["attempt"],
        "arms": {"smoke": {"core": row}},
        "throughput": {"seconds_per_contact_measured": measured, "seconds_per_contact_registered": registered,
                       "ratio": (measured / registered) if isinstance(measured, float) else None,
                       "units": s["units"], "projected_arm_gpu_hours_at_measured": (None if not isinstance(measured, float) else
                                                                                    round(fam.CELLS[fam.cell_key(carrier, 'alloff')]['units'] * measured / fam.SLOTS / 3600.0, 2)),
                       "registered_arm_ceiling_gpu_hours": fam.CELLS[fam.cell_key(carrier, "alloff")]["gpu_hours"]},
        "unattributed_contacts": unattributed,
        "note": "numbers only; no text, transcript, gold or reasoning byte is printed or persisted",
    }
    out = root / fam.analysis_root(carrier) / "smoke-decode-cost.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(table, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return table


# ---- scores / read -----------------------------------------------------------------------------------------------------------------
def scores_of(root: Path, key: str) -> dict:
    s = fam.CELLS[key]
    path = run_dir(root, key) / f"{s['run']}.scores.json"
    if not sealed(root, key):
        raise SystemExit(f"{key} is not sealed")
    if not path.is_file():
        raise SystemExit(f"{key}: the flight's official score file {path} is absent")
    return json.loads(path.read_text(encoding="utf-8"))


def numeric_leaves(node: Any, prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(node, Mapping):
        for k, v in node.items():
            if k in ("per_tier", "by_entity_type", "request_gpu_samples", "per_sample"):
                continue
            out.update(numeric_leaves(v, f"{prefix}{k}."))
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        out[prefix[:-1]] = float(node)
    return out


def bootstrap_diff(a: Sequence[float], b: Sequence[float]) -> dict:
    import numpy as np

    if len(a) != len(b) or not a:
        return {"n": min(len(a), len(b)), "refused": "unpaired or empty"}
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    idx = rng.integers(0, len(d), size=(BOOTSTRAP_DRAWS, len(d)))
    means = d[idx].mean(axis=1)
    return {"n": int(len(d)), "mean_diff": float(d.mean()), "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
            "draws": BOOTSTRAP_DRAWS, "seed": BOOTSTRAP_SEED}


def per_sample_metric(carrier: str, scores: Mapping[str, Any]) -> tuple[str, dict[str, float]]:
    if carrier == "a2t":
        rows = scores["a2t-toolcall-official"]["per_sample"]
        return "a2t-toolcall-official.tool_correct", {r["sample_id"]: 1.0 if r.get("tool_correct") else 0.0 for r in rows}
    rows = scores["asr-wer-whisper"]["per_sample"]
    return "asr-wer-whisper.wer (per call)", {r["sample_id"]: float(r["wer"]) for r in rows}


def strata_table(carrier: str, alloff: Mapping[str, Any], direct: Mapping[str, Any]) -> list[dict]:
    if carrier == "a2t":
        import a2t_gap_diagnosis as gap  # noqa: E402

        pa = alloff["a2t-toolcall-official"]["aggregate"]["per_tier"]
        pd = direct["a2t-toolcall-official"]["aggregate"]["per_tier"]
        repo_a = alloff["a2t-toolcall"]["aggregate"]["per_tier"]
        rows = []
        for tier in gap.TIERS:
            paper_tool, paper_exact = gap.PAPER_QWEN3[tier]
            rows.append({"stratum": tier, "n": pa[tier].get("samples"), "official_alloff": {k: pa[tier].get(k) for k in ("tool_accuracy", "exact_match", "param_f1")},
                         "official_direct": {k: pd[tier].get(k) for k in ("tool_accuracy", "exact_match", "param_f1")},
                         "repo_alloff": {k: repo_a.get(tier, {}).get(k) for k in ("tool_accuracy", "exact_match")},
                         "paper_qwen3_omni_30b": {"tool_accuracy": paper_tool, "exact_match": paper_exact}})
        return rows
    ra = {r["sample_id"]: r for r in alloff["asr-wer-whisper"]["per_sample"]}
    rd = {r["sample_id"]: r for r in direct["asr-wer-whisper"]["per_sample"]}
    return [{"stratum": f"call {sid}", "alloff_wer": ra[sid]["wer"], "direct_wer": rd[sid]["wer"], "alloff_minus_direct": ra[sid]["wer"] - rd[sid]["wer"]} for sid in sorted(ra) if sid in rd]


def read_stage(carrier: str, root: Path, *, write: bool = True) -> dict:
    keys = {k: fam.cell_key(carrier, k) for k in fam.KINDS}
    sc = {k: scores_of(root, keys[k]) for k in fam.ARM_KINDS}
    levels = {k: {scorer: numeric_leaves(sc[k][scorer].get("aggregate", {})) for scorer in sc[k]} for k in fam.ARM_KINDS}
    diff = {scorer: {leaf: levels["alloff"][scorer][leaf] - levels["direct"][scorer].get(leaf, float("nan")) for leaf in levels["alloff"][scorer]}
            for scorer in levels["alloff"] if scorer in levels["direct"]}
    metric, pa = per_sample_metric(carrier, sc["alloff"])
    _m, pd = per_sample_metric(carrier, sc["direct"])
    common = sorted(set(pa) & set(pd))
    decode = {}
    for kind in fam.ARM_KINDS:
        s = fam.CELLS[keys[kind]]
        contacts, unattributed = contacts_of(run_dir(root, keys[kind]) / f"{s['run']}.trace.jsonl")
        decode[kind] = decode_table(contacts, unattributed)
    result = {
        "schema": fam.READ_SCHEMA, "carrier": carrier, "read_run_id": fam.read_run_id(carrier), "claims_benefit": False,
        "arms": {k: {"run_id": fam.CELLS[keys[k]]["run"], "attempt_id": fam.CELLS[keys[k]]["attempt"]} for k in fam.ARM_KINDS},
        "levels": levels, "alloff_minus_direct_aggregate": diff,
        "paired_aa": {"metric": metric, **bootstrap_diff([pa[s] for s in common], [pd[s] for s in common])},
        "per_stratum": strata_table(carrier, sc["alloff"], sc["direct"]), "decode_cost": decode,
        "instruct_comparator": fam.CARRIER_SPEC[carrier]["instruct_comparator"],
        "note": "development numbers only (owner decisions 28 and 86); the all-off and direct arms are request-identical, so their difference is this carrier's A/A on the Thinking core",
    }
    if write:
        out = root / fam.analysis_root(carrier) / "read.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


def columns_stage(carrier: str, root: Path) -> dict:
    out = {}
    for kind in fam.ARM_KINDS:
        key = fam.cell_key(carrier, kind)
        scores_of(root, key)                    # raises when unsealed or unscored
        out[kind] = "sealed and scored"
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("--stage", required=True, choices=("smoke", "columns", "read"))
    p.add_argument("--carrier", required=True, choices=fam.CARRIERS)
    p.add_argument("--data-root", default=None)
    p.add_argument("--repo-root", default=None, help="accepted for symmetry with the other readers")
    a = p.parse_args(argv)
    root = data_root(a.data_root)
    if a.stage == "smoke":
        table = smoke_stage(a.carrier, root)
        print(f"CARRIER-THINK smoke {a.carrier}: {table['arms']['smoke']['core']['contacts']} contacts, measured {table['throughput']['seconds_per_contact_measured']} s per contact "
              f"against {table['throughput']['seconds_per_contact_registered']} registered")
    elif a.stage == "columns":
        print(json.dumps(columns_stage(a.carrier, root), sort_keys=True))
    else:
        result = read_stage(a.carrier, root)
        print(f"CARRIER-THINK read {a.carrier}: written {fam.analysis_root(a.carrier)}/read.json; paired A/A n={result['paired_aa'].get('n')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
