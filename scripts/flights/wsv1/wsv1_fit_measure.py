#!/usr/bin/env python3
"""Measure W-SV-1's supply-variant ``fit_estimate`` and per-arm item bounds from the SEALED AGREE arm.

Cell W-SV-1 (owner decision 172; docs/superpowers/specs/2026-09-27-same-flight-supply-variant-
instrument-design.md) is the AGREE arm with a Solver ``supply_variants`` group under
``arm_visits: "first"``: A (the delivering arm, override-free) renders the AGREE arm's first
Solver request up to two program-identity fields of a few characters (wsv1_arm_a_proof.py), B re-caps the train-exemplar Solver supply from k 20 to k 30, T is A's twin.
``rails.supply_variants`` refuses, before any contact, an arm whose
``base_prompt_tokens + max_supplied_items * tokens_per_supplied_item`` exceeds the live slot with
its reserve, and the runner refuses an arm that supplies more than ``max_supplied_items`` at the
fanned-out (first) visit. Both numbers must be MEASURED, never round placeholders (VAR-2's closed
failure). The delivering arm's bytes already flew in the sealed AGREE arm, so they are measured
there:

* per row, the FIRST Solver contact of the sealed trace (``MODEL_REQUEST`` whose
  ``key_representation_id`` phase is ``solver``): the number of supplied items in all, the number
  from the ``train-exemplars`` store (the only store an arm re-caps), the characters of each
  exemplar item, and the realised ``usage.prompt_tokens`` of its ``MODEL_RESPONSE``;
* characters per token, by least squares of realised prompt tokens on supplied-evidence
  characters over every Solver contact (the W4 package's own method,
  ``scripts/analysis/slurp_w4_fold_a_offline_estimate.py::contact_cost``);
* ``tokens_per_supplied_item`` = the WIDEST exemplar item in tokens (ceiling), so every exemplar
  the k-30 arm adds is covered;
* ``base_prompt_tokens`` = the maximum over first Solver contacts of
  ``prompt_tokens - items * tokens_per_supplied_item`` (ceiling), so
  ``base + items * tokens_per_supplied_item`` bounds every realised first Solver prompt.

Arm bounds: A and T = the measured maximum first-visit item count plus a registered headroom (the
Perception candidates, hence the candidate-keyed boundary and slot-contract items, are a model
output and may differ from the sealed flight); B = the maximum first-visit NON-exemplar count plus
the headroom plus 30 (k 30 caps the exemplar store at 30 items).

MODEL-FREE: zero model, server, tokenizer, encoder or scorer contacts; the sealed trace is opened
read-only. Only counts, token numbers and hashes are printed and written -- never supplied text,
utterance text, gold or model output.

    python scripts/flights/wsv1/wsv1_fit_measure.py --data-root "$SPEECHRL_DATA_DIR" [--output PATH]
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

AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
AGREE_ATTEMPT = "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"
EXEMPLAR_STORE = "train-exemplars"
K_BASE, K_VARIANT = 20, 30
ROWS = 1080
#: Items of headroom on every arm bound: the candidate-keyed stores follow Perception's output.
HEADROOM_ITEMS = 6
SLOT_TOKENS = 24576
COMPLETION_CEILING = 512
DEFAULT_OUTPUT = "analysis/SAEA-SLURP-STAGE3-WSV1-FOLD-A-FIT-MEASURE-V1/fit-measure-v1.json"


def _phase(payload: dict) -> str:
    return str(payload.get("key_representation_id") or "").rsplit(":", 1)[-1]


def measure(data_root: Path) -> dict:
    run_dir = data_root / "runs" / AGREE_RUN / AGREE_ATTEMPT
    trace = run_dir / f"{AGREE_RUN}.trace.jsonl"
    requests: dict[str, dict] = {}
    solver_contacts: list[dict] = []
    with trace.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            channel = record["channel"]
            key = str(record["record_id"]).split("/")[0]
            if channel == "MODEL_REQUEST":
                payload = record["payload"]["payload"]
                if _phase(payload) != "solver":
                    continue
                evidence = payload.get("supplied_evidence") or []
                exemplar_chars = [len(e["content"]) for e in evidence
                                  if str(e["evidence_id"]).split("::", 1)[0] == EXEMPLAR_STORE]
                requests[key] = {
                    "sample_id": payload["sample_id"],
                    "contact_id": payload["history"][-1]["contact_id"],
                    "items": len(evidence),
                    "exemplar_items": len(exemplar_chars),
                    "exemplar_chars": exemplar_chars,
                    "evidence_chars": sum(len(e["content"]) for e in evidence),
                }
            elif channel == "MODEL_RESPONSE" and key in requests:
                row = requests.pop(key)
                row["prompt_tokens"] = int(record["payload"]["usage"]["prompt_tokens"])
                solver_contacts.append(row)
    if requests:
        raise SystemExit(f"{len(requests)} Solver request(s) carry no response in the sealed trace")
    first: dict[str, dict] = {}
    for row in solver_contacts:
        visit = int(row["contact_id"].split(":")[2])
        if visit == 0:
            if row["sample_id"] in first:
                raise SystemExit("two visit-0 Solver contacts on one row")
            first[row["sample_id"]] = row
    if len(first) != ROWS:
        raise SystemExit(f"{len(first)} rows carry a first Solver contact; expected {ROWS}")

    # characters per token over every Solver contact (the W4 method): prompt = a + b * chars
    n = len(solver_contacts)
    mx = sum(r["evidence_chars"] for r in solver_contacts) / n
    my = sum(r["prompt_tokens"] for r in solver_contacts) / n
    sxx = sum((r["evidence_chars"] - mx) ** 2 for r in solver_contacts)
    sxy = sum((r["evidence_chars"] - mx) * (r["prompt_tokens"] - my) for r in solver_contacts)
    slope = sxy / sxx
    chars_per_token = 1.0 / slope

    exemplar_chars = [c for r in first.values() for c in r["exemplar_chars"]]
    tokens_per_item = math.ceil(max(exemplar_chars) / chars_per_token)
    base = math.ceil(max(r["prompt_tokens"] - r["items"] * tokens_per_item for r in first.values()))
    items_max = max(r["items"] for r in first.values())
    nonexemplar_max = max(r["items"] - r["exemplar_items"] for r in first.values())
    exemplar_counts = Counter(r["exemplar_items"] for r in first.values())
    bounds = {
        "a_and_twin": items_max + HEADROOM_ITEMS,
        "b_exk30": nonexemplar_max + HEADROOM_ITEMS + K_VARIANT,
    }
    fit_estimate = {"slot_tokens": SLOT_TOKENS, "completion_ceiling": COMPLETION_CEILING,
                    "base_prompt_tokens": base, "tokens_per_supplied_item": tokens_per_item}
    return {
        "schema": "saea-slurp-wsv1-fit-measure-v1",
        "source": {"run_id": AGREE_RUN, "attempt_id": AGREE_ATTEMPT,
                   "trace_sha256": hashlib.sha256(trace.read_bytes()).hexdigest()},
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
        "solver_contacts": n,
        "first_visit_rows": len(first),
        "chars_per_token_least_squares": round(chars_per_token, 4),
        "intercept_tokens": round(my - slope * mx, 2),
        "first_visit": {
            "items": {"min": min(r["items"] for r in first.values()), "max": items_max,
                      "mean": round(sum(r["items"] for r in first.values()) / ROWS, 3)},
            "exemplar_items_histogram": {str(k): v for k, v in sorted(exemplar_counts.items())},
            "nonexemplar_items_max": nonexemplar_max,
            "exemplar_item_chars": {"min": min(exemplar_chars), "max": max(exemplar_chars),
                                    "mean": round(sum(exemplar_chars) / len(exemplar_chars), 1)},
            "exemplar_item_tokens_mean": round(sum(exemplar_chars) / len(exemplar_chars) / chars_per_token, 1),
            "prompt_tokens": {"min": min(r["prompt_tokens"] for r in first.values()),
                              "max": max(r["prompt_tokens"] for r in first.values()),
                              "mean": round(sum(r["prompt_tokens"] for r in first.values()) / ROWS, 1)},
        },
        "fit_estimate": fit_estimate,
        "headroom_items": HEADROOM_ITEMS,
        "max_supplied_items": bounds,
        "estimates": {
            "a_and_twin": base + bounds["a_and_twin"] * tokens_per_item,
            "b_exk30": base + bounds["b_exk30"] * tokens_per_item,
        },
        "b_realistic_projection_max_prompt_tokens": max(
            r["prompt_tokens"] for r in first.values()
        ) + math.ceil((K_VARIANT - K_BASE) * (sum(exemplar_chars) / len(exemplar_chars)) / chars_per_token),
        "method": __doc__.split("\n\n")[2].strip(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    result = measure(args.data_root)
    output = Path(args.output) if args.output else args.data_root / DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    output.write_text(text, encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      **{k: result[k] for k in ("chars_per_token_least_squares", "first_visit", "fit_estimate",
                                                 "max_supplied_items", "estimates",
                                                 "b_realistic_projection_max_prompt_tokens")}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
