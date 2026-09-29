#!/usr/bin/env python3
"""Measure cell W4-SV's ``supply_variants.fit_estimate`` from SEALED bytes (model-free).

Owner decision 172 / the svinst design section 2 ("Fit gate"): the four ``fit_estimate`` numbers are
MEASURED, never round placeholders (the VAR-2 lesson). Before the cell's own ``native_contact_fit`` pass
exists, the only measured Solver requests of this exact form are two sealed flights of TRAIN Fold A:

* ``SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`` -- the AGREE arm's own bytes (arm A's and the twin's Solver
  request is this flight's first Solver request by construction; ``w4sv_arm_a_proof.py`` proves it);
* ``SAEA-SLURP-STAGE3-W4-FOLD-A-V1`` -- the AGREE arm with the slot-contracts store re-pinned to
  ``slot-contracts-w4-v1``: its FIRST Solver request carries the cards arm B's request carries.

For every Solver contact of both flights this reads the request's ``supplied_evidence`` item count and the
paired response's realised ``usage.prompt_tokens`` (speech feature tokens included), and derives:

* ``tokens_per_supplied_item`` = ceil of max over every Solver contact of both flights of
  ``prompt_tokens / items`` -- the per-item envelope through the origin. The realised requests grow
  steeply with the item count (a row with more candidate intents receives more slot-contract cards;
  the least-squares slope is about 480 tokens per item on the W4 flight), so a line with the slope as
  its per-item cost has no positive envelope intercept; the ratio envelope does;
* ``base_prompt_tokens`` = max(1, ceil of max over every Solver contact of
  ``prompt_tokens - tokens_per_supplied_item * items``) -- 1 whenever the ratio envelope already covers
  every contact, so the estimate at any item count is at least every realised request with that many
  items;
* ``slot_tokens`` 24,576 and ``completion_ceiling`` 512 -- the serving geometry's live slot and the
  model fragment's completion ceiling (``max512``).

It also reports the structural item bound (the sum of the supply caps that can reach the Solver) against
the realised maximum, so ``max_supplied_items`` is a bound the runtime can never exceed.

Counts and token numbers only: no request text, supplied content, transcript, label or model output is
printed or persisted. Zero model, server, tokenizer, encoder, scorer, network and GPU contacts.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/flights/w4sv/measure_w4sv_fit.py --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

SCHEMA = "saea-w4sv-fit-measure-v1"
OUT = "analysis/SAEA-SLURP-STAGE3-W4SV-FIT-MEASURE-V1/fit-measure-v1.json"
FLIGHTS = {
    "agree_bytes": ("SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1", "attempt-slurp-native-stage3-wave1-aa-fold-a-generation-v1"),
    "w4": ("SAEA-SLURP-STAGE3-W4-FOLD-A-V1", "attempt-slurp-native-stage3-w4-fold-a-generation-v1"),
}
SLOT_TOKENS = 24576
COMPLETION_CEILING = 512


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def solver_contacts(trace: Path) -> list[dict]:
    """(sample, visit index, items, prompt tokens) per Solver contact, pairing each MODEL_REQUEST with
    the MODEL_RESPONSE that follows it in the sealed trace."""

    out, pending = [], None
    with trace.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            channel = record.get("channel")
            if channel == "MODEL_REQUEST":
                payload = record["payload"]["payload"]
                contact = payload["history"][-1]["contact_id"]
                parts = contact.split(":")
                pending = {"role": parts[1], "visit": int(parts[2]), "sample_id": payload["sample_id"],
                           "items": len(payload.get("supplied_evidence") or ())}
            elif channel == "MODEL_RESPONSE":
                if pending is None:
                    raise SystemExit(f"{trace.name}: a MODEL_RESPONSE with no preceding MODEL_REQUEST")
                if pending["role"] == "solver":
                    pending["prompt_tokens"] = int(record["payload"]["usage"]["prompt_tokens"])
                    out.append(pending)
                pending = None
    return out


def summary(rows: list[dict]) -> dict:
    items = [r["items"] for r in rows]
    tokens = [r["prompt_tokens"] for r in rows]
    first = [r for r in rows if r["visit"] == 0]
    return {"solver_contacts": len(rows), "first_visit_contacts": len(first),
            "items_min": min(items), "items_max": max(items), "items_mean": round(sum(items) / len(items), 3),
            "first_visit_items_max": max(r["items"] for r in first),
            "prompt_tokens_min": min(tokens), "prompt_tokens_max": max(tokens),
            "prompt_tokens_mean": round(sum(tokens) / len(tokens), 1),
            "first_visit_prompt_tokens_max": max(r["prompt_tokens"] for r in first)}


def slope(rows: list[dict]) -> float:
    n = len(rows)
    mx = sum(r["items"] for r in rows) / n
    my = sum(r["prompt_tokens"] for r in rows) / n
    sxx = sum((r["items"] - mx) ** 2 for r in rows)
    sxy = sum((r["items"] - mx) * (r["prompt_tokens"] - my) for r in rows)
    return sxy / sxx if sxx else 0.0


def structural_bound(baseline: dict) -> dict:
    """The largest item count that can reach the Solver: every Perception/Solver phase supply's
    ``fuse_coverage.top_l`` plus every Solver candidate supply's ``max_total_values``."""

    parts = {}
    for store_id, store in baseline["knowledge_stores"].items():
        for phase, block in (store.get("phase_supply") or {}).items():
            if phase in ("perception", "solver"):
                parts[f"{store_id}.phase_supply.{phase}.fuse_coverage.top_l"] = int(block["fuse_coverage"]["top_l"])
        for phase, block in (store.get("candidate_supply") or {}).items():
            if phase == "solver":
                parts[f"{store_id}.candidate_supply.{phase}.max_total_values"] = int(block["max_total_values"])
    return {"parts": parts, "sum": sum(parts.values())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR"))
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    args = parser.parse_args(argv)
    data, repo = Path(args.data_root), Path(args.repo_root)
    measured, rows_by = {}, {}
    for key, (run_id, attempt_id) in FLIGHTS.items():
        trace = data / "runs" / run_id / attempt_id / f"{run_id}.trace.jsonl"
        rows = solver_contacts(trace)
        rows_by[key] = rows
        measured[key] = {"run_id": run_id, "attempt_id": attempt_id,
                         "trace_sha256": sha_file(trace), **summary(rows)}
    every = rows_by["agree_bytes"] + rows_by["w4"]
    per_item = max(1, math.ceil(max(r["prompt_tokens"] / r["items"] for r in every)))
    base = max(1, math.ceil(max(r["prompt_tokens"] - per_item * r["items"] for r in every)))
    if any(base + per_item * r["items"] < r["prompt_tokens"] for r in every):
        raise SystemExit("the envelope does not cover every realised Solver request")
    baseline = json.loads((repo / "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json")
                          .read_text(encoding="utf-8"))
    bound = structural_bound(baseline)
    realised_max = max(r["items"] for r in every)
    if realised_max > bound["sum"]:
        raise SystemExit(f"realised {realised_max} items exceed the structural bound {bound['sum']}")
    fit = {"slot_tokens": SLOT_TOKENS, "completion_ceiling": COMPLETION_CEILING,
           "base_prompt_tokens": base, "tokens_per_supplied_item": per_item}
    from speech_aware_evidence_acquisition.rails.supply_variants import (  # noqa: PLC0415
        parse_supply_variant_fit_estimate,
    )
    estimate = parse_supply_variant_fit_estimate(fit)
    at_bound = base + per_item * bound["sum"]
    document = {
        "schema": SCHEMA, "fit_estimate": fit,
        "prompt_limit_tokens": estimate.prompt_limit_tokens, "reserve_tokens": estimate.reserve_tokens,
        "max_supplied_items": bound["sum"], "structural_bound": bound, "realised_items_max": realised_max,
        "estimated_prompt_tokens_at_max_supplied_items": at_bound,
        "estimate_headroom_tokens": estimate.prompt_limit_tokens - at_bound,
        "w4_solver_slope_tokens_per_item": round(slope(rows_by["w4"]), 3),
        "flights": measured,
        "method": ("tokens_per_supplied_item = ceil(max over every Solver contact of both sealed flights of "
                   "realised prompt_tokens / supplied items) -- the per-item envelope through the origin (the OLS "
                   "slope, reported beside it, has no positive envelope intercept); base_prompt_tokens = max(1, "
                   "ceil(max of prompt_tokens - tokens_per_supplied_item * items)); max_supplied_items = the "
                   "structural sum of the supply caps that can reach the Solver (never exceeded by construction)"),
        "agree_bytes_solver_slope_tokens_per_item": round(slope(rows_by["agree_bytes"]), 3),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "gpu": 0},
        "boundary": "counts and token numbers only; no request text, supplied content, transcript, label or output",
    }
    path = data / OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise SystemExit(f"{path} exists with different bytes; never overwritten")
    path.write_text(text, encoding="utf-8")
    print(json.dumps({"output": str(path), "sha256": hashlib.sha256(text.encode()).hexdigest(),
                      "fit_estimate": fit, "max_supplied_items": bound["sum"], "realised_items_max": realised_max,
                      "headroom": document["estimate_headroom_tokens"],
                      "flights": {k: {x: v[x] for x in ("solver_contacts", "items_max", "prompt_tokens_max",
                                                         "first_visit_prompt_tokens_max")} for k, v in measured.items()}},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
