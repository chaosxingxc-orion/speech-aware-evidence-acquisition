#!/usr/bin/env python3
"""CLI: Stage-3 S3-6, the delta-store RETENTION rule (owner decision 83;
``docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md``
section S3-6).

MODEL-FREE. Zero frozen-core, tool, embedding, encoder, tokenizer, scorer,
GPU and network contacts: every byte read is an already-sealed local file
(the released store's curated authored document and the CELL-1 paired
analysis root), and everything written is pure arithmetic over ids and
numbers. No statement text, utterance text, gold label or model output is
read into a printed or persisted field -- only value ids, node names, intent
and scenario ids, counts and percentages.

What decision 83 preregistered
------------------------------
"The per-scenario effect x prefilled-token frontier decides which deltas
survive -- a delta whose target scenario shows a net harm beyond the null
band is retired in version t+1, one whose scenario gains is kept, and the
cost weight is the frontier slope."

This CLI is that sentence, and nothing else:

1. **Scenario mapping.** Every authored row's ``associated_facet_ids`` are
   SLURP intent ids ``<scenario>_<action>`` (the S3-5 revision v1r
   ``source-intent`` facet rule), so the scenarios a delta targets are the
   distinct prefixes of its facet ids. A facet whose prefix is not one of
   the read's scenarios is recorded as unmapped and targets nothing.
2. **The null band.** Each scenario's band half-width is derived from the
   PLAN-vs-PLANr per-scenario pooled SLU-F1 deltas of the plan's OWN NULL
   read -- the movement the same locked plan produced on that scenario on a
   request-identical second pass -- floored at the registered pooled own-null
   half-width (``registered-facts-v1.json`` ``own_null_table.pooled_micro.
   slu_f1_micro.ci95_half_width``). The registered own-null table carries NO
   per-scenario band, which is why it is derived here; the floor exists
   because a 60-row scenario cannot be more stable than the 1,080-row pool
   the registered half-width was measured on, and without it a scenario
   whose replicate happened to move 0.01 pp would be treated as noiseless.
3. **The scenario rule.** RETIRE when EVERY targeted scenario is harmed
   beyond its own band (per-scenario pooled SLU delta < -half-width); KEEP
   when ANY targeted scenario gains beyond its band (> +half-width). The two
   are mutually exclusive by construction, so their order is immaterial.
4. **The tie rule = the frontier-slope weighting.** Everything else -- a
   delta all of whose targeted scenarios sit inside the band, a delta whose
   scenarios are mixed harm/in-band with no gain, and a delta that resolved
   no scenario at all -- is decided by cost. The CELL-1 arm sits OFF the
   prefilled-token frontier (+912 prefilled tokens per row, +2.5 % GPU-h
   against the same plan, for a pooled SLU delta of -0.48 pp), so the
   frontier slope through the arm is negative: an extra prefilled token buys
   nothing. A row carried into version t+1 therefore has to pay for itself
   out of its own paired evidence, and is kept only if its per-delta paired
   SLU mean over the rows it actually reached is strictly greater than
   ``--tie-threshold-pp`` (default 0.0 pp, i.e. "did not, on its own rows,
   move the score down").
5. **Rows the flight never supplied** have no paired evidence AND no
   prefilled-token cost, so the frontier slope is silent on them.
   ``--unreached-policy`` states what happens: ``keep`` (the default, the
   append-only carry-forward: an unsupplied row cost nothing and the cost
   weight cannot speak against it) or ``retire`` (the strict reading of
   "per-delta paired SLU mean over the rows it reached is > 0", which no
   unreached row can satisfy).

The output ``retention-v2.json`` is the input of
``scripts/build_slurp_stage3_delta_store.py --retire-value-ids``, which
drops the retired predecessor rows from version t+1 and records their ids.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

RETENTION_SCHEMA = "saea-stage3-delta-retention-v1"
#: The paired metric decision 83's "net harm" is read on. Named, not
#: implicit: the per-scenario table carries several and the verdict document
#: reports pooled official SLU-F1, so this is the one the rule keys on.
RETENTION_METRIC = "slu_f1"
#: Where the per-scenario pooled deltas live in a paired-analysis
#: ``per-scenario-tables.json`` (both the CELL-1 root and the plan's own-null
#: replicate root are written by the same recipe, so one accessor serves
#: both).
_PER_SCENARIO_PATH = (
    "natural_mixture_and_equal_scenario", "arm_vs_comparator",
    "pooled_slu_f1_per_scenario",
)
#: Where the registered pooled own-null half-width lives.
_OWN_NULL_PATH = (
    "own_null_table", "pooled_micro", "slu_f1_micro", "ci95_half_width",
)
DECISION_KEEP = "KEEP"
DECISION_RETIRE = "RETIRE"
RULE_SCENARIO = "scenario"
RULE_TIE = "frontier-slope-tie"
SIGNAL_GAIN = "gain-beyond-band"
SIGNAL_HARM = "harm-beyond-band"
SIGNAL_BAND = "inside-band"
UNREACHED_KEEP = "keep"
UNREACHED_RETIRE = "retire"
UNREACHED_POLICIES = (UNREACHED_KEEP, UNREACHED_RETIRE)


class Stage3DeltaRetentionError(RuntimeError):
    """A retention input is missing or does not have the shape this CLI needs."""


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Stage3DeltaRetentionError(f"{path} is unreadable: {error}") from error


def _dig(document: object, keys: Sequence[str], *, where: str) -> object:
    node = document
    for index, key in enumerate(keys):
        if not isinstance(node, Mapping) or key not in node:
            trail = ".".join(keys[: index + 1])
            raise Stage3DeltaRetentionError(f"{where} carries no {trail}")
        node = node[key]
    return node


def scenario_of(facet_id: str) -> str:
    """The SLURP scenario a facet id names.

    A v1r facet id is an intent id ``<scenario>_<action>`` (``alarm_set``,
    ``qa_factoid``), so the scenario is everything before the first
    underscore. PURE and total: a facet with no underscore returns itself,
    which the caller then fails to match against the read's scenario set and
    records as unmapped rather than guessing.
    """

    return facet_id.split("_", 1)[0]


def load_per_scenario_slu_deltas(
    path: Path,
) -> tuple[dict[str, float], dict[str, int]]:
    """The per-scenario pooled SLU-F1 deltas (pp) and row counts of one
    paired-analysis root's ``per-scenario-tables.json``.

    ``delta_pp`` is ``arm - comparator`` on that scenario's pooled SLU-F1;
    for the CELL-1 root the arm is CELL-1 and the comparator is the sealed
    PLAN, for the own-null root the arm is PLANr and the comparator is the
    same sealed PLAN -- which is exactly why the second one is a null.
    """

    table = _dig(_read_json(path), _PER_SCENARIO_PATH, where=str(path))
    if not isinstance(table, Mapping) or not table:
        raise Stage3DeltaRetentionError(f"{path} carries an empty per-scenario table")
    deltas: dict[str, float] = {}
    counts: dict[str, int] = {}
    for scenario, row in table.items():
        if not isinstance(row, Mapping) or not isinstance(
            row.get("delta_pp"), (int, float)
        ):
            raise Stage3DeltaRetentionError(
                f"{path} scenario {scenario!r} carries no numeric delta_pp"
            )
        deltas[str(scenario)] = float(row["delta_pp"])
        counts[str(scenario)] = int(row.get("n", 0))
    return deltas, counts


def load_registered_band_floor(path: Path) -> float:
    """The registered pooled own-null half-width (pp) the derived
    per-scenario band is floored at."""

    value = _dig(_read_json(path), _OWN_NULL_PATH, where=str(path))
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise Stage3DeltaRetentionError(
            f"{path} own_null_table half-width is not a positive number"
        )
    return float(value)


def derive_null_band(
    own_null_deltas: Mapping[str, float], *, floor_pp: float
) -> dict[str, float]:
    """The per-scenario null half-width: the magnitude of that scenario's
    own PLANr-vs-PLAN movement, floored at ``floor_pp``.

    PURE. One replicate pass is one observation, so the magnitude is a
    single-sample estimate of per-scenario replicate noise and the floor is
    what keeps a scenario that happened to move almost nothing from being
    declared noiseless. Both halves are recorded per scenario in the output
    document, so a reader can see which of the two bound each band.
    """

    if floor_pp <= 0:
        raise Stage3DeltaRetentionError("the band floor must be positive")
    return {
        scenario: max(abs(float(delta)), floor_pp)
        for scenario, delta in own_null_deltas.items()
    }


def scenario_signal(delta_pp: float, half_width_pp: float) -> str:
    """Where one scenario's CELL-1 delta sits against its own null band."""

    if delta_pp < -half_width_pp:
        return SIGNAL_HARM
    if delta_pp > half_width_pp:
        return SIGNAL_GAIN
    return SIGNAL_BAND


def load_authored_rows(path: Path) -> list[dict[str, object]]:
    """The predecessor store's rows, reduced to what the rule reads.

    ``content`` is deliberately NOT carried: this CLI never holds statement
    text in a value it could print or persist.
    """

    document = _read_json(path)
    if not isinstance(document, Mapping) or not isinstance(document.get("rows"), list):
        raise Stage3DeltaRetentionError(f"{path} is not an authored-deltas document")
    rows: list[dict[str, object]] = []
    for index, row in enumerate(document["rows"]):
        if not isinstance(row, Mapping):
            raise Stage3DeltaRetentionError(f"{path} rows[{index}] is not an object")
        value_id = row.get("value_id")
        facets = row.get("associated_facet_ids")
        if not isinstance(value_id, str) or not value_id:
            raise Stage3DeltaRetentionError(f"{path} rows[{index}] has no value_id")
        if not isinstance(facets, list) or not facets:
            raise Stage3DeltaRetentionError(
                f"{path} rows[{index}] has no associated_facet_ids"
            )
        rows.append(
            {
                "value_id": value_id,
                "facet_ids": [str(facet) for facet in facets],
                "node": str(row.get("node_target", "")) or None,
            }
        )
    if not rows:
        raise Stage3DeltaRetentionError(f"{path} carries no rows")
    return rows


def load_per_delta_outcomes(
    path: Path, *, metric: str = RETENTION_METRIC
) -> dict[str, dict[str, object]]:
    """The per-value paired outcome of the CELL-1 read, keyed by BARE value
    id.

    ``delta-consumption.json`` keys ``consumption.per_value_id`` by the
    store-qualified id ``<store_id>::<value_id>``; the authored document
    carries the bare one, so the store prefix is stripped here rather than
    re-derived at every call site.
    """

    per_value = _dig(
        _read_json(path), ("consumption", "per_value_id"), where=str(path)
    )
    if not isinstance(per_value, Mapping):
        raise Stage3DeltaRetentionError(f"{path} consumption.per_value_id is not an object")
    outcomes: dict[str, dict[str, object]] = {}
    for qualified, entry in per_value.items():
        if not isinstance(entry, Mapping):
            raise Stage3DeltaRetentionError(f"{path} {qualified} is not an object")
        bare = str(qualified).split("::", 1)[-1]
        outcome = entry.get("outcome")
        metric_block = (
            outcome.get(metric) if isinstance(outcome, Mapping) else None
        )
        if not isinstance(metric_block, Mapping):
            raise Stage3DeltaRetentionError(
                f"{path} {qualified} carries no outcome.{metric}"
            )
        outcomes[bare] = {
            "rows_reached": int(entry.get("rows_reached", 0)),
            "rows_joined": int(outcome.get("rows_joined", 0)) if isinstance(outcome, Mapping) else 0,
            "nodes": [str(node) for node in entry.get("nodes", ())],
            "mean_delta_pp": float(metric_block.get("mean_delta_pp", 0.0)),
            "saves": int(metric_block.get("saves", 0)),
            "harms": int(metric_block.get("harms", 0)),
            "neutral": int(metric_block.get("neutral", 0)),
        }
    return outcomes


def decide_row(
    *,
    signals: Mapping[str, str],
    outcome: Mapping[str, object] | None,
    tie_threshold_pp: float,
    unreached_policy: str,
) -> tuple[str, str, str]:
    """One row's ``(decision, rule, reason)``. PURE and total.

    The three branches are decision 83's three clauses, in its own order.
    """

    values = list(signals.values())
    if values and all(signal == SIGNAL_HARM for signal in values):
        return (
            DECISION_RETIRE, RULE_SCENARIO,
            "every targeted scenario is harmed beyond its own null band",
        )
    if any(signal == SIGNAL_GAIN for signal in values):
        return (
            DECISION_KEEP, RULE_SCENARIO,
            "a targeted scenario gains beyond its own null band",
        )
    if outcome is None or int(outcome["rows_reached"]) <= 0:
        if unreached_policy == UNREACHED_KEEP:
            return (
                DECISION_KEEP, RULE_TIE,
                "the flight never supplied this value: no paired evidence and no "
                "prefilled-token cost, carried forward by --unreached-policy keep",
            )
        return (
            DECISION_RETIRE, RULE_TIE,
            "the flight never supplied this value, so it cannot show a positive "
            "per-delta mean (--unreached-policy retire)",
        )
    mean = float(outcome["mean_delta_pp"])
    if mean > tie_threshold_pp:
        return (
            DECISION_KEEP, RULE_TIE,
            "no targeted scenario is decided by the band; the per-delta paired "
            "SLU mean over the rows it reached clears the frontier-slope threshold",
        )
    return (
        DECISION_RETIRE, RULE_TIE,
        "no targeted scenario is decided by the band and the per-delta paired "
        "SLU mean over the rows it reached does not clear the frontier-slope "
        "threshold, so the row does not pay for its prefilled tokens",
    )


def build_retention(
    *,
    rows: Sequence[Mapping[str, object]],
    cell_deltas: Mapping[str, float],
    band: Mapping[str, float],
    outcomes: Mapping[str, Mapping[str, object]],
    tie_threshold_pp: float,
    unreached_policy: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """The per-value decisions and their roll-up. PURE."""

    decisions: list[dict[str, object]] = []
    per_node: dict[str, dict[str, int]] = {}
    per_rule: dict[str, dict[str, int]] = {}
    per_scenario_values: dict[str, dict[str, int]] = {}
    unmapped_facets: dict[str, int] = {}
    for row in rows:
        facet_ids = [str(facet) for facet in row["facet_ids"]]
        scenarios: list[str] = []
        for facet in facet_ids:
            scenario = scenario_of(facet)
            if scenario in cell_deltas:
                if scenario not in scenarios:
                    scenarios.append(scenario)
            else:
                unmapped_facets[facet] = unmapped_facets.get(facet, 0) + 1
        scenarios.sort()
        signals = {
            scenario: scenario_signal(cell_deltas[scenario], band[scenario])
            for scenario in scenarios
        }
        value_id = str(row["value_id"])
        outcome = outcomes.get(value_id)
        decision, rule, reason = decide_row(
            signals=signals,
            outcome=outcome,
            tie_threshold_pp=tie_threshold_pp,
            unreached_policy=unreached_policy,
        )
        node = str(row.get("node") or "unknown")
        decisions.append(
            {
                "value_id": value_id,
                "node": node,
                "facet_ids": facet_ids,
                "scenarios": scenarios,
                "scenario_delta_pp": {s: cell_deltas[s] for s in scenarios},
                "null_band_half_width_pp": {s: band[s] for s in scenarios},
                "scenario_signal": signals,
                "per_delta": dict(outcome) if outcome is not None else None,
                "decision": decision,
                "rule": rule,
                "reason": reason,
            }
        )
        per_node.setdefault(node, {DECISION_KEEP: 0, DECISION_RETIRE: 0})[decision] += 1
        per_rule.setdefault(rule, {DECISION_KEEP: 0, DECISION_RETIRE: 0})[decision] += 1
        for scenario in scenarios:
            bucket = per_scenario_values.setdefault(
                scenario, {DECISION_KEEP: 0, DECISION_RETIRE: 0}
            )
            bucket[decision] += 1
    decisions.sort(key=lambda entry: str(entry["value_id"]))
    summary = {
        "values": len(decisions),
        "kept": sum(1 for entry in decisions if entry["decision"] == DECISION_KEEP),
        "retired": sum(1 for entry in decisions if entry["decision"] == DECISION_RETIRE),
        "per_node": {node: dict(counts) for node, counts in sorted(per_node.items())},
        "per_rule": {rule: dict(counts) for rule, counts in sorted(per_rule.items())},
        "per_scenario_values": {
            scenario: dict(counts)
            for scenario, counts in sorted(per_scenario_values.items())
        },
        "values_with_no_resolved_scenario": sum(
            1 for entry in decisions if not entry["scenarios"]
        ),
        "values_never_supplied": sum(
            1 for entry in decisions if entry["per_delta"] is None
        ),
        "unmapped_facet_ids": dict(sorted(unmapped_facets.items())),
    }
    return decisions, summary


def render_markdown(document: Mapping[str, object]) -> str:
    """The counts-only summary. No statement text, by construction: the
    document it renders carries none."""

    summary = document["summary"]
    inputs = document["inputs"]
    band = document["null_band"]
    lines: list[str] = []
    lines.append("# Stage-3 delta store: retention for version 2 (owner decision 83)")
    lines.append("")
    lines.append(
        "Model-free. Counts, ids and percentages only -- no statement text, "
        "utterance text, gold label or model output."
    )
    lines.append("")
    lines.append("## 1. What was decided")
    lines.append("")
    lines.append(
        f"- predecessor store: `{inputs['authored']['relpath']}` "
        f"({summary['values']} values, sha256 `{inputs['authored']['sha256'][:12]}`)"
    )
    lines.append(f"- kept: **{summary['kept']}**, retired: **{summary['retired']}**")
    lines.append(
        f"- tie threshold: {document['tie_threshold_pp']} pp; unreached policy: "
        f"`{document['unreached_policy']}`"
    )
    lines.append(
        f"- values the flight never supplied: {summary['values_never_supplied']}; "
        f"values resolving no scenario: {summary['values_with_no_resolved_scenario']}"
    )
    lines.append("")
    lines.append("## 2. Per node")
    lines.append("")
    lines.append("| node | kept | retired | total |")
    lines.append("| --- | ---: | ---: | ---: |")
    for node, counts in summary["per_node"].items():
        total = counts[DECISION_KEEP] + counts[DECISION_RETIRE]
        lines.append(
            f"| {node} | {counts[DECISION_KEEP]} | {counts[DECISION_RETIRE]} | {total} |"
        )
    lines.append("")
    lines.append("## 3. Per rule")
    lines.append("")
    lines.append("| rule | kept | retired | total |")
    lines.append("| --- | ---: | ---: | ---: |")
    for rule, counts in summary["per_rule"].items():
        total = counts[DECISION_KEEP] + counts[DECISION_RETIRE]
        lines.append(
            f"| {rule} | {counts[DECISION_KEEP]} | {counts[DECISION_RETIRE]} | {total} |"
        )
    lines.append("")
    lines.append("## 4. Per scenario")
    lines.append("")
    lines.append(
        f"Band = max(|PLANr - PLAN per-scenario pooled SLU delta|, "
        f"{band['floor_pp']} pp floor). Floor source: "
        f"`{band['floor_source']}`."
    )
    lines.append("")
    lines.append(
        "| scenario | n | CELL-1 delta pp | own-null delta pp | band pp | signal "
        "| values | kept | retired |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |")
    per_scenario = document["per_scenario"]
    values_by_scenario = summary["per_scenario_values"]
    for scenario in sorted(per_scenario):
        entry = per_scenario[scenario]
        counts = values_by_scenario.get(
            scenario, {DECISION_KEEP: 0, DECISION_RETIRE: 0}
        )
        total = counts[DECISION_KEEP] + counts[DECISION_RETIRE]
        lines.append(
            f"| {scenario} | {entry['n']} | {entry['cell_delta_pp']:+.4f} | "
            f"{entry['own_null_delta_pp']:+.4f} | {entry['band_half_width_pp']:.4f} | "
            f"{entry['signal']} | {total} | {counts[DECISION_KEEP]} | "
            f"{counts[DECISION_RETIRE]} |"
        )
    lines.append("")
    lines.append("## 5. The rule, in the preregistered words")
    lines.append("")
    lines.append(
        "Owner decision 83: \"the per-scenario effect x prefilled-token frontier "
        "decides which deltas survive -- a delta whose target scenario shows a net "
        "harm beyond the null band is retired in version t+1, one whose scenario "
        "gains is kept, and the cost weight is the frontier slope.\""
    )
    lines.append("")
    lines.append(
        "1. RETIRE when every targeted scenario is harmed beyond its own band."
    )
    lines.append("2. KEEP when any targeted scenario gains beyond its own band.")
    lines.append(
        "3. Otherwise the frontier-slope weighting decides: the CELL-1 arm sits off "
        "the prefilled-token frontier (+912 prefilled tokens per row, +2.5 % GPU-h, "
        "pooled SLU -0.48 pp), so a row is kept only if its own per-delta paired SLU "
        f"mean over the rows it reached exceeds {document['tie_threshold_pp']} pp."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--authored", required=True, type=Path,
        help="the predecessor store's curated authored-deltas document",
    )
    parser.add_argument(
        "--cell-per-scenario", required=True, type=Path,
        help="the CELL-1 paired analysis root's per-scenario-tables.json",
    )
    parser.add_argument(
        "--own-null-per-scenario", required=True, type=Path,
        help=(
            "the plan's own-null (PLAN vs PLANr) paired analysis root's "
            "per-scenario-tables.json, from which the per-scenario band is derived"
        ),
    )
    parser.add_argument(
        "--delta-consumption", required=True, type=Path,
        help="the CELL-1 paired analysis root's delta-consumption.json",
    )
    parser.add_argument(
        "--registered-facts", default=None, type=Path,
        help=(
            "the cell's registered-facts document, read ONLY for the pooled "
            "own-null half-width the derived per-scenario band is floored at. "
            "Required unless --band-floor-pp is given."
        ),
    )
    parser.add_argument(
        "--band-floor-pp", default=None, type=float,
        help=(
            "override the band floor (pp). Default: the registered pooled "
            "own-null SLU-F1 micro CI95 half-width from --registered-facts."
        ),
    )
    parser.add_argument(
        "--tie-threshold-pp", default=0.0, type=float,
        help=(
            "the frontier-slope weighting's threshold (pp): a within-band value is "
            "kept only if its per-delta paired SLU mean over the rows it reached is "
            "strictly greater than this. DEFAULT 0.0 -- the arm is off the "
            "prefilled-token frontier, so a carried row must at least not have "
            "moved its own rows down."
        ),
    )
    parser.add_argument(
        "--unreached-policy", default=UNREACHED_KEEP, choices=UNREACHED_POLICIES,
        help=(
            "what to do with a value the flight never supplied: 'keep' (the "
            "default: no paired evidence and no prefilled-token cost, so the cost "
            "weight is silent and the append-only carry-forward stands) or "
            "'retire' (the strict reading of the tie rule)."
        ),
    )
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-markdown", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.band_floor_pp is None:
        if args.registered_facts is None:
            raise Stage3DeltaRetentionError(
                "--band-floor-pp or --registered-facts is required"
            )
        floor_pp = load_registered_band_floor(args.registered_facts)
        floor_source = str(args.registered_facts)
    else:
        floor_pp = float(args.band_floor_pp)
        floor_source = "--band-floor-pp"

    cell_deltas, cell_counts = load_per_scenario_slu_deltas(args.cell_per_scenario)
    own_null_deltas, _ = load_per_scenario_slu_deltas(args.own_null_per_scenario)
    missing = sorted(set(cell_deltas) - set(own_null_deltas))
    if missing:
        raise Stage3DeltaRetentionError(
            "the own-null read has no per-scenario delta for "
            f"{missing}; refusing to invent a band"
        )
    band = derive_null_band(own_null_deltas, floor_pp=floor_pp)
    rows = load_authored_rows(args.authored)
    outcomes = load_per_delta_outcomes(args.delta_consumption)

    decisions, summary = build_retention(
        rows=rows,
        cell_deltas=cell_deltas,
        band=band,
        outcomes=outcomes,
        tie_threshold_pp=args.tie_threshold_pp,
        unreached_policy=args.unreached_policy,
    )
    per_scenario = {
        scenario: {
            "n": cell_counts.get(scenario, 0),
            "cell_delta_pp": cell_deltas[scenario],
            "own_null_delta_pp": own_null_deltas[scenario],
            "band_half_width_pp": band[scenario],
            "band_bound_by": (
                "floor" if abs(own_null_deltas[scenario]) <= floor_pp else "own-null"
            ),
            "signal": scenario_signal(cell_deltas[scenario], band[scenario]),
        }
        for scenario in sorted(cell_deltas)
    }
    document = {
        "schema": RETENTION_SCHEMA,
        "metric": RETENTION_METRIC,
        "decision_reference": (
            "owner decision 83 (docs/readiness/2026-09-16-slurp-next-stage-owner-"
            "decisions-v1.md); spec docs/superpowers/specs/2026-09-22-stage3-tfrl-"
            "base-loop-engineering.md section S3-6"
        ),
        "target_iteration": 2,
        "tie_threshold_pp": args.tie_threshold_pp,
        "unreached_policy": args.unreached_policy,
        "null_band": {
            "derivation": (
                "the registered own-null table carries no per-scenario band, so "
                "each scenario's half-width is the magnitude of that scenario's own "
                "PLANr-vs-PLAN pooled SLU-F1 delta (the same locked plan, "
                "request-identical second pass), floored at the registered pooled "
                "own-null half-width because a 60-row scenario cannot be more "
                "stable than the 1,080-row pool that half-width was measured on"
            ),
            "floor_pp": floor_pp,
            "floor_source": floor_source,
            "own_null_source": str(args.own_null_per_scenario),
        },
        "inputs": {
            "authored": {
                "relpath": str(args.authored),
                "sha256": _sha256_file(args.authored),
            },
            "cell_per_scenario": {
                "relpath": str(args.cell_per_scenario),
                "sha256": _sha256_file(args.cell_per_scenario),
            },
            "own_null_per_scenario": {
                "relpath": str(args.own_null_per_scenario),
                "sha256": _sha256_file(args.own_null_per_scenario),
            },
            "delta_consumption": {
                "relpath": str(args.delta_consumption),
                "sha256": _sha256_file(args.delta_consumption),
            },
        },
        "per_scenario": per_scenario,
        "summary": summary,
        "retired_value_ids": sorted(
            str(entry["value_id"])
            for entry in decisions
            if entry["decision"] == DECISION_RETIRE
        ),
        "decisions": decisions,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    args.out_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.out_markdown.write_text(
        render_markdown(document), encoding="utf-8", newline="\n"
    )
    print(json.dumps(  # noqa: T201 -- ids, counts and digests only
        {
            "schema": RETENTION_SCHEMA,
            "out_json": {
                "relpath": str(args.out_json),
                "sha256": _sha256_file(args.out_json),
            },
            "out_markdown": {
                "relpath": str(args.out_markdown),
                "sha256": _sha256_file(args.out_markdown),
            },
            "band_floor_pp": floor_pp,
            "tie_threshold_pp": args.tie_threshold_pp,
            "unreached_policy": args.unreached_policy,
            "summary": summary,
        },
        indent=2, sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Stage3DeltaRetentionError as error:  # pragma: no cover - CLI surface
        print(f"retention refused: {error}", file=sys.stderr)  # noqa: T201
        raise SystemExit(2) from error
