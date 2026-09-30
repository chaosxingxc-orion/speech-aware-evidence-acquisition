#!/usr/bin/env python3
"""Measure the Perception-branch ``fit_estimate`` and per-branch item bounds of P-SV-1 / P-SV-2 from the SEALED
AGREE arm (owner decisions 184 and 188).

``rails.supply_variants.parse_perception_branches`` refuses, before any contact, a branch whose
``base_prompt_tokens + max_supplied_items * tokens_per_supplied_item`` exceeds the live slot minus its reserve,
the completion ceiling and the special-token reserve. Both numbers must be MEASURED (the VAR-2 lesson). The
delivering branch A renders AGREE's Perception request (the same boundary supply, the same templates), so its
bytes already flew in the sealed AGREE arm on TRAIN Fold A -- the TUNING roster -- and are measured there:

* per row, the ONE Perception contact of the sealed trace (``MODEL_REQUEST`` whose ``key_representation_id``
  phase is ``perception``): the number of supplied boundary items, the characters of each item, and the realised
  ``usage.prompt_tokens`` of its ``MODEL_RESPONSE``;
* characters per token, by least squares of realised prompt tokens on supplied-evidence characters over every
  Perception contact;
* ``tokens_per_supplied_item`` = the WIDEST boundary item in tokens (ceiling);
* ``base_prompt_tokens`` = the maximum over Perception contacts of ``prompt_tokens - items *
  tokens_per_supplied_item`` (ceiling), so ``base + items * tokens_per_supplied_item`` bounds every realised
  Perception prompt.

Branch bounds: A and T = the measured maximum item count plus a registered headroom of 2; the top2-contrast
branch = A's bound plus 2 item-widths for the contrast block's two sentences (activation + exclusion,
``rails.perception_presentations``), a DECLARED allowance until the contrast-pair table exists; the
min_candidates branch = A's bound (the response contract changes one bound in the instruction, not the supply);
the boundary_depth branch (P-SV-3) = the DECLARED new fuse_coverage.top_l (``psv_family.
BOUNDARY_DEPTH_NEW_TOP_L``, 12) plus the same registered headroom of 2 -- the boundary supply itself is raised, so
the bound is built from the new declared depth the same way A's bound is built from the measured one, never
measured (P-SV-3 has never flown); the key_source branch (P-SV-4) = A's bound (a key swap changes which items are
recalled, never how many). The first Solver visit's realised prompt is reported beside (the level-2
branch Solver contact carries a branch note of the same shape in place of A's).

MODEL-FREE: zero model, server, tokenizer, encoder or scorer contacts; the sealed trace is opened read-only.
Only counts, token numbers and hashes are printed and written -- never supplied text, utterance text, gold or
model output.

    python scripts/flights/psv/psv_fit_measure.py --data-root "$SPEECHRL_DATA_DIR" [--output PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import psv_family as ff  # noqa: E402

BOUNDARY_STORE = "intent-boundaries"
HEADROOM_ITEMS = 2
CONTRAST_ALLOWANCE_ITEMS = 2
SLOT_TOKENS = 24576
COMPLETION_CEILING = 512


def _phase(payload: dict) -> str:
    return str(payload.get("key_representation_id") or "").rsplit(":", 1)[-1]


def measure(data_root: Path) -> dict:
    run_dir = data_root / "runs" / ff.AGREE_RUN / ff.AGREE_ATTEMPT
    trace = run_dir / f"{ff.AGREE_RUN}.trace.jsonl"
    pending: dict[str, dict] = {}
    perception: list[dict] = []
    solver_first: list[int] = []
    with trace.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            channel = record["channel"]
            key = str(record["record_id"]).split("/")[0]
            if channel == "MODEL_REQUEST":
                payload = record["payload"]["payload"]
                phase = _phase(payload)
                if phase not in ("perception", "solver"):
                    continue
                contact_id = payload["history"][-1]["contact_id"]
                if phase == "solver" and int(contact_id.split(":")[2]) != 0:
                    continue
                evidence = payload.get("supplied_evidence") or []
                boundary = [len(e["content"]) for e in evidence
                            if str(e["evidence_id"]).split("::", 1)[0] == BOUNDARY_STORE]
                pending[key] = {"phase": phase, "sample_id": payload["sample_id"], "items": len(evidence),
                                "boundary_items": len(boundary), "boundary_chars": boundary,
                                "evidence_chars": sum(len(e["content"]) for e in evidence)}
            elif channel == "MODEL_RESPONSE" and key in pending:
                row = pending.pop(key)
                row["prompt_tokens"] = int(record["payload"]["usage"]["prompt_tokens"])
                if row["phase"] == "perception":
                    perception.append(row)
                else:
                    solver_first.append(row["prompt_tokens"])
    if pending:
        raise SystemExit(f"{len(pending)} request(s) carry no response in the sealed trace")
    if len({r["sample_id"] for r in perception}) != ff.LEDGER_ROWS or len(perception) != ff.LEDGER_ROWS:
        raise SystemExit(f"{len(perception)} Perception contacts; expected exactly one on each of {ff.LEDGER_ROWS} rows")

    n = len(perception)
    mx = sum(r["evidence_chars"] for r in perception) / n
    my = sum(r["prompt_tokens"] for r in perception) / n
    sxx = sum((r["evidence_chars"] - mx) ** 2 for r in perception)
    sxy = sum((r["evidence_chars"] - mx) * (r["prompt_tokens"] - my) for r in perception)
    slope = sxy / sxx
    chars_per_token = 1.0 / slope
    item_chars = [c for r in perception for c in r["boundary_chars"]]
    tokens_per_item = math.ceil(max(item_chars) / chars_per_token)
    base = math.ceil(max(r["prompt_tokens"] - r["items"] * tokens_per_item for r in perception))
    items_max = max(r["items"] for r in perception)
    a_bound = items_max + HEADROOM_ITEMS
    bounds = {
        "a_and_twin": a_bound, "top2_contrast": a_bound + CONTRAST_ALLOWANCE_ITEMS, "min_candidates": a_bound,
        # P-SV-3: the branch's own fuse_coverage.m/top_l are raised to ff.BOUNDARY_DEPTH_NEW_TOP_L (a DECLARED
        # target, not a measured one -- this axis has never flown), plus the same registered headroom A/T use.
        "boundary_depth": ff.BOUNDARY_DEPTH_NEW_TOP_L + HEADROOM_ITEMS,
        # P-SV-4: a key_source branch re-keys WHICH boundary items are recalled, never how many (k, m, c and top_l
        # are unchanged, so the fuser still stops at top_l 8): A's measured bound applies unchanged.
        "key_source": a_bound,
    }
    reserve = SLOT_TOKENS // 8
    limit = SLOT_TOKENS - reserve - COMPLETION_CEILING - 2
    fit_estimate = {"slot_tokens": SLOT_TOKENS, "completion_ceiling": COMPLETION_CEILING,
                    "base_prompt_tokens": base, "tokens_per_supplied_item": tokens_per_item}
    return {
        "schema": "saea-slurp-psv-perception-fit-measure-v1",
        "source": {"run_id": ff.AGREE_RUN, "attempt_id": ff.AGREE_ATTEMPT, "roster": ff.TUNING_ROSTER,
                   "trace_sha256": hashlib.sha256(trace.read_bytes()).hexdigest()},
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
        "perception_contacts": n,
        "chars_per_token_least_squares": round(chars_per_token, 4),
        "intercept_tokens": round(my - slope * mx, 2),
        "perception": {
            "items": {"min": min(r["items"] for r in perception), "max": items_max,
                      "mean": round(sum(r["items"] for r in perception) / n, 3)},
            "items_histogram": {str(k): v for k, v in sorted(Counter(r["items"] for r in perception).items())},
            "boundary_item_chars": {"min": min(item_chars), "max": max(item_chars),
                                    "mean": round(sum(item_chars) / len(item_chars), 1)},
            "prompt_tokens": {"min": min(r["prompt_tokens"] for r in perception),
                              "max": max(r["prompt_tokens"] for r in perception),
                              "mean": round(my, 1)},
        },
        "first_solver_visit_prompt_tokens": {"contacts": len(solver_first), "min": min(solver_first),
                                             "max": max(solver_first),
                                             "mean": round(sum(solver_first) / len(solver_first), 1)},
        "fit_estimate": fit_estimate,
        "prompt_limit_tokens": limit,
        "headroom_items": HEADROOM_ITEMS,
        "contrast_allowance_items": CONTRAST_ALLOWANCE_ITEMS,
        "max_supplied_items": bounds,
        "estimates": {k: base + v * tokens_per_item for k, v in bounds.items()},
        "method": __doc__.split("\n\n")[1].strip(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    result = measure(args.data_root)
    # Default: the v2 file (P-SV-4 on). The v1 file the P-SV-1..3 packages pin is never overwritten by default.
    output = Path(args.output) if args.output else args.data_root / ff.FIT_MEASURE_V2
    output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    output.write_text(text, encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      **{k: result[k] for k in ("chars_per_token_least_squares", "perception", "fit_estimate",
                                                 "prompt_limit_tokens", "max_supplied_items", "estimates",
                                                 "first_solver_visit_prompt_tokens")}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
