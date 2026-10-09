#!/usr/bin/env python3
"""Measure the NX R1 Solver template-column fit numbers from a SEALED COMP-1b arm.

``rails.supply_variants.parse_template_variants`` refuses, before any contact, an arm whose
``base_prompt_tokens + template_tokens + max_supplied_items * tokens_per_supplied_item`` exceeds the live
slot minus its reserve, the completion ceiling and the special-token reserve. The R1 cell's delivering arm
renders the COMP-1b module request (same supply, same templates), so its first Solver visit already flew in
the sealed COMP-1b Fold A arm (TRAIN Fold A, the sibling roster of Fold B). Measured per row, on the ONE first
Solver visit (contact index 0) of the sealed trace: the number of supplied evidence items, the characters of
each item, and the realised ``usage.prompt_tokens`` of its ``MODEL_RESPONSE``.

Derived: ``base_prompt_tokens`` = a DECLARED structural floor of 2,000 tokens (the shared task context, the
control turn and the Perception note; the parser requires a positive base, and the least-squares intercept of
this arm is negative because a few very wide slot cards drive long prompts); ``tokens_per_supplied_item`` = the
maximum over rows of ``(prompt_tokens - locked template tokens - base) / items`` (ceiling), so ``base +
template + items * tokens_per_supplied_item`` bounds EVERY realised first Solver prompt of the sealed arm;
``max_supplied_items`` = measured maximum + a registered headroom of 2. This is a linear envelope of the sealed
arm, not a worst case over all possible item mixes; the realised fit of every arm request is the dispatch gate.
Template tokens are ESTIMATED from characters at a conservative 3.5 characters per token (no tokenizer
contact).

MODEL-FREE: zero model, server, tokenizer, encoder or scorer contacts; the sealed trace is opened read-only.
Only counts, token numbers and hashes are printed and written -- never supplied text, utterance text, gold or
model output.

    python scripts/flights/nx/nx_r1_fit_measure.py --data-root "$SPEECHRL_DATA_DIR" [--output PATH]

ITERATION 2 (``--iteration 2``) does NOT reopen the sealed trace: the measured quantities (items, prompt tokens, the linear
envelope, the base floor) belong to the delivering arm's COMP-1b request, which iteration 2 shares byte for byte with iteration 1
(same supply, same locked template). Only the five candidate template token estimates change, so the iteration-2 measure is the
iteration-1 measure re-derived with the iteration-2 templates (template_tokens, arm_prompt_estimates, ``reused_from``). It needs
no data root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nx_r1_family as nf  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
SOURCE_RUN = "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1"
SOURCE_ATTEMPT = "attempt-slurp-native-stage3-comp1b-fold-a-generation-v1"
SLOT_TOKENS = 24576
COMPLETION_CEILING = 512
HEADROOM_ITEMS = 2
TEMPLATE_CHARS_PER_TOKEN = 3.5
BASE_FLOOR_TOKENS = 2000
LOCKED_TEMPLATE = "configs/probes/slurp_native_role_solver_v2.txt"
ITER1_CANDIDATES = [f"configs/probes/nx/solver/r1/r1-c{i}.txt" for i in range(1, 6)]


def template_tokens(relpath: str) -> int:
    return math.ceil(len((REPO / relpath).read_bytes()) / TEMPLATE_CHARS_PER_TOKEN)


def rederive(previous: dict) -> dict:
    """Iteration >= 2: the previous measure with this iteration's template token estimates (no trace is opened)."""

    result = json.loads(json.dumps(previous))
    frame = result["template_frame"]
    locked_tokens = template_tokens(LOCKED_TEMPLATE)
    if locked_tokens != frame["delivering_template_tokens"]:
        raise SystemExit("the locked template's token estimate moved; re-measure from the sealed trace")
    fit = frame["fit_estimate"]
    arms = {"lock": locked_tokens, **{a: template_tokens(p) for a, p in nf.CANDIDATE_PATHS.items()}}
    bound = frame["max_supplied_items"]
    result["template_tokens"] = arms
    result["arm_prompt_estimates"] = {
        k: fit["base_prompt_tokens"] + v + bound * fit["tokens_per_supplied_item"] for k, v in arms.items()}
    result["reused_from"] = {
        "relpath": nf.ITER1_FIT_MEASURE,
        "sha256": hashlib.sha256((REPO / nf.ITER1_FIT_MEASURE).read_bytes()).hexdigest(),
        "reason": ("the delivering arm's COMP-1b request (supply, locked template, items, prompt tokens) is iteration 1's, so "
                   "the measured envelope is reused; only the candidate templates differ"),
    }
    result["schema"] = "saea-slurp-nx-r1-solver-fit-measure-v1"
    if max(result["arm_prompt_estimates"].values()) > result["prompt_limit_tokens"]:
        raise SystemExit("an iteration-2 arm estimate exceeds the prompt limit")
    return result


def measure(data_root: Path) -> dict:
    run_dir = data_root / "runs" / SOURCE_RUN / SOURCE_ATTEMPT
    trace = run_dir / f"{SOURCE_RUN}.trace.jsonl"
    pending: dict[str, dict] = {}
    rows: list[dict] = []
    with trace.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            channel = record["channel"]
            key = str(record["record_id"]).split("/")[0]
            if channel == "MODEL_REQUEST":
                payload = record["payload"]["payload"]
                phase = str(payload.get("key_representation_id") or "").rsplit(":", 1)[-1]
                if phase != "solver":
                    continue
                contact_id = payload["history"][-1]["contact_id"]
                if int(contact_id.split(":")[2]) != 0:
                    continue
                evidence = payload.get("supplied_evidence") or []
                pending[key] = {"sample_id": payload["sample_id"], "items": len(evidence),
                                "chars": [len(e["content"]) for e in evidence]}
            elif channel == "MODEL_RESPONSE" and key in pending:
                row = pending.pop(key)
                row["prompt_tokens"] = int(record["payload"]["usage"]["prompt_tokens"])
                rows.append(row)
    if pending:
        raise SystemExit(f"{len(pending)} request(s) carry no response in the sealed trace")
    n = len(rows)
    if n != len({r["sample_id"] for r in rows}):
        raise SystemExit("more than one first Solver visit on a row")
    for r in rows:
        r["evidence_chars"] = sum(r["chars"])
    mx = sum(r["evidence_chars"] for r in rows) / n
    my = sum(r["prompt_tokens"] for r in rows) / n
    slope = (sum((r["evidence_chars"] - mx) * (r["prompt_tokens"] - my) for r in rows)
             / sum((r["evidence_chars"] - mx) ** 2 for r in rows))
    chars_per_token = 1.0 / slope
    widest = max(c for r in rows for c in r["chars"])
    locked_tokens = template_tokens(LOCKED_TEMPLATE)
    base = BASE_FLOOR_TOKENS
    tokens_per_item = math.ceil(max((r["prompt_tokens"] - locked_tokens - base) / r["items"] for r in rows))
    items_max = max(r["items"] for r in rows)
    bound = items_max + HEADROOM_ITEMS
    reserve = SLOT_TOKENS // 8
    limit = SLOT_TOKENS - reserve - COMPLETION_CEILING - 2
    arms = {"lock": locked_tokens, **{Path(p).stem: template_tokens(p) for p in ITER1_CANDIDATES}}
    return {
        "schema": "saea-slurp-nx-r1-solver-fit-measure-v1",
        "source": {"run_id": SOURCE_RUN, "attempt_id": SOURCE_ATTEMPT, "roster": "TRAIN Fold A (the Fold B sibling)",
                   "trace_sha256": hashlib.sha256(trace.read_bytes()).hexdigest()},
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
        "first_solver_visits": n,
        "chars_per_token_least_squares": round(chars_per_token, 4),
        "items": {"min": min(r["items"] for r in rows), "max": items_max,
                  "mean": round(sum(r["items"] for r in rows) / n, 3)},
        "item_chars": {"max": widest},
        "prompt_tokens": {"min": min(r["prompt_tokens"] for r in rows),
                          "max": max(r["prompt_tokens"] for r in rows), "mean": round(my, 1)},
        "template_tokens_estimated_at_chars_per_token": TEMPLATE_CHARS_PER_TOKEN,
        "template_tokens": arms,
        "template_frame": {
            "max_supplied_items": bound, "delivering_template_tokens": locked_tokens, "twin": True,
            "fit_estimate": {"slot_tokens": SLOT_TOKENS, "completion_ceiling": COMPLETION_CEILING,
                             "base_prompt_tokens": base, "tokens_per_supplied_item": tokens_per_item},
        },
        "prompt_limit_tokens": limit,
        "arm_prompt_estimates": {k: base + v + bound * tokens_per_item for k, v in arms.items()},
        "headroom_items": HEADROOM_ITEMS,
        "method": __doc__.split("\n\n")[1].strip(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", type=Path, help="required for iteration 1 (opens the sealed COMP-1b trace read-only)")
    parser.add_argument("--iteration", type=int, default=nf.ITERATION, choices=(1, 2))
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    nf.configure(args.iteration)
    if args.output is None:
        args.output = str(REPO / nf.FIT_MEASURE)
    if args.iteration == 1:
        if args.data_root is None:
            parser.error("--data-root is required for iteration 1")
        result = measure(args.data_root)
    else:
        result = rederive(json.loads((REPO / nf.ITER1_FIT_MEASURE).read_text(encoding="utf-8")))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    print("sha256", hashlib.sha256(text.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
