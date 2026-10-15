"""The decode-cost model of NX-T R2 (the per-node reasoning-budget column). Model-free; stdlib only.

WHAT IT PREDICTS. The seconds one contact costs at a node whose reasoning budget is ``b`` (or whose thinking is off), as a fraction of the delivering
arm's contact (budget 3,072), so the registration can cost an arm table it has not flown. The fit inputs are the 40 per-contact records of the sealed NX-T
R1 four-row smoke (``nxt_r2_cost_inputs.json``: token counts, latencies and a forced-close flag; no text), 12 thinking contacts per node.

THE MODEL (per node; ``R`` = the natural reasoning length a contact would produce with no budget, ``A`` = its answer tokens)::

    completion tokens at budget b   T(b) = min(R, b) + A + m * [R > b]          m = the forced-close message tokens
    seconds of one contact          s(b) = a_node + c * T(b)                    one slope c (decode seconds per token at np4), one intercept per node
    a no-think contact              s    = the node's measured no-think mean seconds

* ``A`` is the mean completion of the node's no-think contacts (they emit the answer and nothing else).
* An unforced thinking contact has R = completion - A. A forced-close contact has R > 3,072 (right-censored at the R1 budget), so for every b <= 3,072 it
  contributes min(R, b) = b exactly: no extrapolation beyond the R1 budget is needed, and that is why a candidate budget must stay below 3,072.
* ``m`` = mean(forced completion) - 3,072 - A (the forced-close message the server appends).
* ``c`` and the node intercepts are the ordinary least-squares line of seconds on completion tokens over the thinking contacts, intercept per node.
* E[T(b)] is the plain mean over the node's thinking contacts, so ``s(3072)`` reproduces the delivering arm's measured seconds by construction.

LIMITS, stated on every use: four smoke rows; 12 contacts per node; np4 batching jitter is inside the residual. The linear-in-budget guess
(b + fixed) / (3,072 + fixed) UNDER-states the cost of a lower budget (most contacts finish before 3,072 anyway, so a lower budget clips only the long tail);
the clipped model above is the registered one and the linear form is reported beside it as the lower reference.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Mapping, Sequence

HERE = Path(__file__).resolve().parent
INPUTS_PATH = HERE / "nxt_r2_cost_inputs.json"
NODES = ("perception", "solver")
OFF = "off"


def load_inputs(path: Path = INPUTS_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def fit(inputs: Mapping) -> dict:
    """Fit the model on the committed contact records; returns plain numbers (all that the registration and the tests need)."""

    contacts = inputs["contacts"]
    r1_budget = int(inputs["source"]["r1_budget_tokens"])
    model: dict = {"r1_budget_tokens": r1_budget, "nodes": {}}
    sxx = sxy = 0.0
    centres: dict[str, tuple[float, float]] = {}
    for node in NODES:
        think = [c for c in contacts if c["node"] == node and c["mode"] == "think"]
        plain = [c for c in contacts if c["node"] == node and c["mode"] == "no-think"]
        if not think or not plain:
            raise ValueError(f"cost inputs carry no thinking or no no-think contact for node {node!r}")
        answer = _mean([c["completion_tokens"] for c in plain])
        forced = [c for c in think if c["forced_close"]]
        message = max(0.0, _mean([c["completion_tokens"] for c in forced]) - r1_budget - answer) if forced else 0.0
        natural = sorted(c["completion_tokens"] - answer for c in think if not c["forced_close"])
        mean_tokens, mean_seconds = _mean([c["completion_tokens"] for c in think]), _mean([c["seconds"] for c in think])
        centres[node] = (mean_tokens, mean_seconds)
        sxx += sum((c["completion_tokens"] - mean_tokens) ** 2 for c in think)
        sxy += sum((c["completion_tokens"] - mean_tokens) * (c["seconds"] - mean_seconds) for c in think)
        model["nodes"][node] = {
            "think_contacts": len(think), "forced_contacts": len(forced), "answer_tokens": answer, "forced_close_message_tokens": message,
            "natural_reasoning_tokens": [round(v, 3) for v in natural], "no_think_seconds": _mean([c["seconds"] for c in plain]),
            "think_mean_tokens": mean_tokens, "think_mean_seconds": mean_seconds,
        }
    slope = sxy / sxx
    model["seconds_per_token"] = slope
    for node in NODES:
        model["nodes"][node]["intercept_seconds"] = centres[node][1] - slope * centres[node][0]
    return model


def tokens_at(model: Mapping, node: str, budget: int) -> float:
    """E[T(b)]: the mean completion tokens of a thinking contact at ``node`` with reasoning budget ``budget`` (b <= the R1 budget)."""

    if budget > model["r1_budget_tokens"]:
        raise ValueError(f"budget {budget} is above the R1 budget {model['r1_budget_tokens']}: the fit data are right-censored there")
    info = model["nodes"][node]
    total = 0.0
    for r in info["natural_reasoning_tokens"]:
        total += min(r, budget) + info["answer_tokens"] + (info["forced_close_message_tokens"] if r > budget else 0.0)
    total += info["forced_contacts"] * (budget + info["answer_tokens"] + info["forced_close_message_tokens"])
    return total / info["think_contacts"]


def seconds_at(model: Mapping, node: str, setting: int | str) -> float:
    """Seconds one contact at ``node`` costs: ``"off"`` = the measured no-think mean, an int = a thinking budget."""

    info = model["nodes"][node]
    if setting == OFF:
        return info["no_think_seconds"]
    return info["intercept_seconds"] + model["seconds_per_token"] * tokens_at(model, node, int(setting))


def row_seconds(model: Mapping, perception: int | str, solver: int | str) -> float:
    """Seconds of one arm's Perception contact plus its Solver contact (the arm's cost per row)."""

    return seconds_at(model, "perception", perception) + seconds_at(model, "solver", solver)


def relative_cost(model: Mapping, perception: int | str, solver: int | str, delivering: int = 3072) -> float:
    """The arm's row cost as a fraction of the delivering arm's (both nodes at ``delivering``)."""

    return row_seconds(model, perception, solver) / row_seconds(model, delivering, delivering)


def linear_reference(model: Mapping, perception: int | str, solver: int | str, delivering: int = 3072) -> float:
    """The lower reference: cost proportional to (b + fixed) / (delivering + fixed) per node, fixed = intercept / slope, weighted by the delivering seconds."""

    slope = model["seconds_per_token"]
    num = den = 0.0
    for node, setting in (("perception", perception), ("solver", solver)):
        info = model["nodes"][node]
        fixed = info["intercept_seconds"] / slope
        full = seconds_at(model, node, delivering)
        den += full
        num += seconds_at(model, node, OFF) if setting == OFF else full * (int(setting) + fixed) / (delivering + fixed)
    return num / den


def ceil_hundredth(value: float) -> float:
    """Registered costs round UP to 0.01: a ceiling must not be tightened by rounding."""

    return round(math.ceil(round(value * 100.0, 9)) / 100.0, 2)
