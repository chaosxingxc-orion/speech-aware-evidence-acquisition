#!/usr/bin/env python3
"""CLI: Stage-3 layer A, the GEPA arm's per-(scenario, node) GROUP material.

MODEL-FREE. Zero frozen-core, tool, embedding, encoder, tokenizer, scorer, GPU
and network contacts: every byte read is an already-sealed local file (S3-3's
``pairs.json`` and ``per_row.json``, the released v1r authored-deltas document,
the committed R01C roster receipt and the construction gold-intent map), and
everything written is ids, counts and digests. No utterance text, transcript,
gold label, statement text or model output is read into a printed or persisted
field.

What a GROUP is (design note
``docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md``): one
SCENARIO x one NODE. The GEPA reflection contact for that group is shown

* that scenario's ``K`` WORST-outcome and ``K`` BEST-outcome rows, each with its
  whole sealed trajectory (Perception candidate list, the best and worst Solver
  samples, the delivered answer with the Reviewer verdict labels and the Planner
  route, and the row's own construction gold), and
* the node's CURRENT delta statements for that scenario -- the instruction text
  a reflective mutation is asked to revise.

**Which rows are eligible.** Exactly the rows ``pairs.json`` carries a sealed
``trajectory`` block for: the disagreeing rows of the rollout. A row whose five
rollout samples agreed has no best/worst contrast and no trajectory in the
sealed artifact, and this CLI never rebuilds one from the trace.

**How they are ranked** (``--rank-metric``, default ``group-mean``). By the
row's ROLLOUT GROUP MEAN official SLU-F1 (``per_row.json``
``group_mean_slu_f1_f1``), ascending, ties broken by ``sample_id``. The mean of
the five samples is the row's OUTCOME under the one scorer id every number in
this artifact comes from (``slurp-slu-official-projected-v3-train``), which is
what a reflector is being asked to separate. The two alternatives are
deliberately not the default and are selectable for an audit:
``disagreement`` (best minus worst) measures WITHIN-row variance, not outcome
quality, so its "worst" rows are the least stable rather than the least
correct; ``delivered`` is unusable in this seal at all, because the delivered
answer was scored under a DIFFERENT scorer id
(``slurp-slu-official-train``) -- the documented ``delivered_below_best``
vacuity of the ADV-1 registration -- and comparing across scorer ids is not a
measurement.

**The carrier row.** ``core.flight.FlightRuntime`` makes exactly one contact per
FLOWN ROW for a construction-visible arm, so a group needs one row id to be the
flight's row: its CARRIER. The carrier is an identity anchor and nothing else --
the contact is text-only (no packet is opened) and its material is the whole
group. Carrier ``i`` of a scenario (``i`` indexing the four nodes in program
order) is the ``i``-th row of that scenario's ordered group, so the four
carriers of a scenario are distinct and each is a row whose own gold the
contact already shows. A scenario with fewer than four eligible rows tops up
from its OWN remaining R01C rows in ascending ``sample_id``; those top-up
carriers are recorded with ``carrier_from: "roster-topup"`` and their gold is
NOT shown (they are not group rows).

**The current delta slice.** A v1r row belongs to (scenario, node) when its
``node_target`` is that node and at least one of its ``associated_facet_ids``
is an intent of that scenario (the facet ids are ``<scenario>_<action>`` under
the S3-5 revision v1r ``source-intent`` rule). The slice is ranked by
``prior_score`` descending, ``value_id`` ascending, and capped at
``--current-delta-cap``. The artifact pins the SELECTED value ids in order, so
the flight-time renderer renders exactly those rows in exactly that order and
never re-derives the slice.

Output: ``gepa-groups-v1.json`` (schema ``saea-stage3-gepa-groups-v1``) under
``prepared/SAEA-SLURP-STAGE3-DELTAS-GEPA-V1/``, plus a printed report. The
baseline fragment of the GEPA cell pins this file by relpath and sha256 and
``rails.stage3_gepa_material`` is the only reader.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

GROUPS_SCHEMA = "saea-stage3-gepa-groups-v1"

#: The four nodes of the locked plan's episode, in PROGRAM order. The carrier
#: index below is an index into this tuple, so the order is part of the
#: artifact's identity and is stated once.
NODES = ("perception", "solver", "reviewer", "planner")

RANK_METRICS = ("group-mean", "disagreement")
DEFAULT_K = 6
DEFAULT_CURRENT_DELTA_CAP = 12


class Stage3GepaGroupsError(RuntimeError):
    """An input is missing or does not have the shape this builder needs."""


def canonical_json_bytes(document: object) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Stage3GepaGroupsError(f"{path} is unreadable: {error}") from error


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scenario_of(facet_id: str) -> str:
    """``<scenario>_<action>`` -> ``<scenario>``; a bare id is its own scenario."""

    text = str(facet_id)
    return text.split("_", 1)[0] if "_" in text else text


# ---------------------------------------------------------------------------
# Reading the sealed inputs.
# ---------------------------------------------------------------------------


def load_eligible_rows(pairs_document: Mapping[str, object]) -> dict[str, dict]:
    """``{sample_id: {stratum, best_index, worst_index, disagreement}}`` for the
    rows ``pairs.json`` carries an AVAILABLE trajectory for."""

    rows = pairs_document.get("pairs")
    if not isinstance(rows, list) or not rows:
        raise Stage3GepaGroupsError("pairs.json carries no non-empty 'pairs' array")
    out: dict[str, dict] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise Stage3GepaGroupsError(f"pairs.json pairs[{index}] must be an object")
        sample_id = row.get("sample_id")
        stratum = row.get("stratum")
        trajectory = row.get("trajectory")
        if not isinstance(sample_id, str) or not sample_id:
            raise Stage3GepaGroupsError(f"pairs.json pairs[{index}] has no sample_id")
        if not isinstance(stratum, str) or not stratum:
            raise Stage3GepaGroupsError(f"pairs.json pairs[{index}] has no stratum")
        if sample_id in out:
            raise Stage3GepaGroupsError(f"pairs.json repeats sample_id {sample_id!r}")
        if not isinstance(trajectory, Mapping) or not trajectory.get("available"):
            continue
        disagreement = row.get("disagreement")
        out[sample_id] = {
            "stratum": stratum,
            "best_index": row.get("best_index"),
            "worst_index": row.get("worst_index"),
            "disagreement": (
                float(disagreement)
                if isinstance(disagreement, (int, float))
                and not isinstance(disagreement, bool)
                else None
            ),
        }
    if not out:
        raise Stage3GepaGroupsError("no pairs.json row carries an available trajectory")
    return out


def load_group_means(per_row_document: Mapping[str, object]) -> dict[str, float]:
    """``{sample_id: group_mean_slu_f1_f1}`` from ``per_row.json``."""

    rows = per_row_document.get("rows")
    if not isinstance(rows, list) or not rows:
        raise Stage3GepaGroupsError("per_row.json carries no non-empty 'rows' array")
    out: dict[str, float] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise Stage3GepaGroupsError(f"per_row.json rows[{index}] must be an object")
        sample_id = row.get("sample_id")
        value = row.get("group_mean_slu_f1_f1")
        if not isinstance(sample_id, str) or not sample_id:
            raise Stage3GepaGroupsError(f"per_row.json rows[{index}] has no sample_id")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise Stage3GepaGroupsError(
                f"per_row.json rows[{index}] has no numeric group_mean_slu_f1_f1"
            )
        out[sample_id] = float(value)
    return out


def load_roster_strata(roster_document: Mapping[str, object]) -> dict[str, dict]:
    """``{sample_id: {stratum, audio_seconds}}`` from a frozen roster receipt."""

    items = roster_document.get("items")
    if not isinstance(items, list) or not items:
        raise Stage3GepaGroupsError("the roster receipt carries no items")
    out: dict[str, dict] = {}
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise Stage3GepaGroupsError(f"roster items[{index}] must be an object")
        sample_id = item.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise Stage3GepaGroupsError(f"roster items[{index}] has no sample_id")
        out[sample_id] = {
            "stratum": str(item.get("stratum") or ""),
            "audio_seconds": float(item.get("audio_seconds") or 0.0),
        }
    return out


def load_authored_deltas(document: Mapping[str, object]) -> list[dict]:
    """The v1r authored rows, validated for the four fields this builder reads.

    ``content`` IS statement text: it is never returned, printed or persisted by
    this builder. Only ``value_id``, ``node_target``, ``associated_facet_ids``
    and ``prior_score`` leave this function.
    """

    rows = document.get("rows")
    if not isinstance(rows, list) or not rows:
        raise Stage3GepaGroupsError("the authored-deltas document carries no rows")
    out: list[dict] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise Stage3GepaGroupsError(f"authored rows[{index}] must be an object")
        value_id = row.get("value_id")
        node = row.get("node_target")
        facets = row.get("associated_facet_ids")
        if not isinstance(value_id, str) or not value_id:
            raise Stage3GepaGroupsError(f"authored rows[{index}] has no value_id")
        if node not in NODES:
            raise Stage3GepaGroupsError(
                f"authored rows[{index}] node_target {node!r} is not one of {list(NODES)}"
            )
        if not isinstance(facets, list) or not facets:
            raise Stage3GepaGroupsError(
                f"authored rows[{index}] has no associated_facet_ids"
            )
        try:
            prior = float(row.get("prior_score"))
        except (TypeError, ValueError):
            raise Stage3GepaGroupsError(
                f"authored rows[{index}] has no numeric prior_score"
            ) from None
        out.append(
            {
                "value_id": value_id,
                "node_target": str(node),
                "facet_ids": [str(facet) for facet in facets],
                "prior_score": prior,
            }
        )
    return out


def load_gold_intents(path: Path | None) -> dict[str, str]:
    """``{sample_id: <scenario>_<action>}``, ids only (owner decision 82)."""

    if path is None:
        return {}
    document = _read_json(path)
    if not isinstance(document, Mapping):
        raise Stage3GepaGroupsError(f"{path} must be a JSON object of sample id -> intent")
    rows = document.get("intents") if "intents" in document else document
    if not isinstance(rows, Mapping):
        raise Stage3GepaGroupsError(f"{path} carries no sample id -> intent mapping")
    out: dict[str, str] = {}
    for sample_id, intent in rows.items():
        if isinstance(sample_id, str) and isinstance(intent, str) and intent:
            out[sample_id] = intent
    if not out:
        raise Stage3GepaGroupsError(f"{path} resolved zero gold intents")
    return out


# ---------------------------------------------------------------------------
# Building the groups.
# ---------------------------------------------------------------------------


def rank_key(sample_id: str, row: Mapping[str, object], means: Mapping[str, float], metric: str):
    if metric == "group-mean":
        if sample_id not in means:
            raise Stage3GepaGroupsError(
                f"row {sample_id!r} has no per_row.json group mean to rank on"
            )
        return (means[sample_id], sample_id)
    value = row.get("disagreement")
    if value is None:
        raise Stage3GepaGroupsError(
            f"row {sample_id!r} carries no disagreement to rank on"
        )
    return (float(value), sample_id)


def scenario_rows(
    eligible: Mapping[str, Mapping[str, object]],
    means: Mapping[str, float],
    *,
    k: int,
    metric: str,
) -> dict[str, dict]:
    """Per scenario: ``{worst, best, ordered}`` sample ids, DISJOINT.

    ``worst`` is the lowest-ranked rows, lowest first; ``best`` is the
    highest-ranked rows, HIGHEST first -- both lists read outward from their own
    extreme, which is the order the instruction shows them in.

    The two halves never overlap. A scenario with fewer than ``2k`` eligible
    rows splits its ranked list at ``(n + 1) // 2`` instead of taking ``k`` from
    each end: showing one row as a WORSE-outcome example and again as a
    BETTER-outcome example in the same instruction would be contradictory
    material, which is worse than showing fewer rows. So ``|worst| = min(k, (n
    + 1) // 2)`` and ``|best| = min(k, n - |worst|)``; for ``n >= 2k`` both are
    ``k``, and for ``n == 1`` the single row is shown once, as the worst.

    ``ordered`` is ``worst`` then ``best``: the group's row set, worst-first,
    already distinct, and the carrier index runs over it.
    """

    by_scenario: dict[str, list[str]] = {}
    for sample_id, row in eligible.items():
        by_scenario.setdefault(str(row["stratum"]), []).append(sample_id)
    out: dict[str, dict] = {}
    for scenario, ids in sorted(by_scenario.items()):
        ranked = sorted(ids, key=lambda sid: rank_key(sid, eligible[sid], means, metric))
        total = len(ranked)
        worst_size = min(k, (total + 1) // 2)
        best_size = min(k, total - worst_size)
        worst = ranked[:worst_size]
        best = list(reversed(ranked[total - best_size :])) if best_size else []
        ordered = list(worst) + list(best)
        if len(set(ordered)) != len(ordered):
            raise Stage3GepaGroupsError(
                f"scenario {scenario!r}: the worst and best halves overlap"
            )
        out[scenario] = {"worst": worst, "best": best, "ordered": ordered}
    return out


def current_delta_slice(
    authored: Sequence[Mapping[str, object]], *, scenario: str, node: str, cap: int
) -> list[str]:
    """The node's current statements for this scenario: ordered value ids."""

    matched = [
        row
        for row in authored
        if row["node_target"] == node
        and any(scenario_of(facet) == scenario for facet in row["facet_ids"])
    ]
    matched.sort(key=lambda row: (-float(row["prior_score"]), str(row["value_id"])))
    return [str(row["value_id"]) for row in matched[:cap]]


def build_groups(
    *,
    eligible: Mapping[str, Mapping[str, object]],
    means: Mapping[str, float],
    roster: Mapping[str, Mapping[str, object]],
    authored: Sequence[Mapping[str, object]],
    gold_intents: Mapping[str, str],
    k: int,
    metric: str,
    current_delta_cap: int,
) -> tuple[list[dict], dict]:
    per_scenario = scenario_rows(eligible, means, k=k, metric=metric)
    roster_by_scenario: dict[str, list[str]] = {}
    for sample_id, item in roster.items():
        roster_by_scenario.setdefault(str(item["stratum"]), []).append(sample_id)
    for ids in roster_by_scenario.values():
        ids.sort()

    groups: list[dict] = []
    carriers: set[str] = set()
    topup_count = 0
    for scenario, slices in sorted(per_scenario.items()):
        ordered = slices["ordered"]
        topups = [
            sample_id
            for sample_id in roster_by_scenario.get(scenario, ())
            if sample_id not in set(ordered)
        ]
        for node_index, node in enumerate(NODES):
            if node_index < len(ordered):
                carrier = ordered[node_index]
                carrier_from = "group"
            else:
                offset = node_index - len(ordered)
                if offset >= len(topups):
                    raise Stage3GepaGroupsError(
                        f"scenario {scenario!r} cannot supply a distinct carrier row for "
                        f"node {node!r}: {len(ordered)} group row(s) and {len(topups)} "
                        "R01C top-up row(s)"
                    )
                carrier = topups[offset]
                carrier_from = "roster-topup"
                topup_count += 1
            if carrier in carriers:
                raise Stage3GepaGroupsError(f"carrier {carrier!r} is used twice")
            carriers.add(carrier)
            if carrier not in roster:
                raise Stage3GepaGroupsError(
                    f"carrier {carrier!r} is not an item of the construction roster"
                )
            intents = sorted(
                {
                    gold_intents[sample_id]
                    for sample_id in ordered
                    if sample_id in gold_intents
                }
            )
            # The curated rows' ``prior_score``: the DISAGREEMENT MASS of the
            # rows a proposal was reflected from, aggregated to the group's own
            # unit. ADV-1 gives each row's statement that row's own
            # best-minus-worst score; a GEPA statement is proposed from the
            # whole group, so it carries the group's mean. The per-node supply
            # route ranks by exactly this field, so it must be a number that
            # means the same thing across families.
            masses = [
                float(eligible[sample_id]["disagreement"])
                for sample_id in ordered
                if eligible[sample_id]["disagreement"] is not None
            ]
            groups.append(
                {
                    "group_id": f"gepa:{scenario}:{node}",
                    "scenario": scenario,
                    "node": node,
                    "node_index": node_index,
                    "carrier_sample_id": carrier,
                    "carrier_from": carrier_from,
                    "carrier_audio_seconds": float(roster[carrier]["audio_seconds"]),
                    "worst_sample_ids": list(slices["worst"]),
                    "best_sample_ids": list(slices["best"]),
                    "row_sample_ids": list(ordered),
                    "row_count": len(ordered),
                    "disagreement_sum": round(sum(masses), 12),
                    "disagreement_mean": (
                        round(sum(masses) / len(masses), 12) if masses else 0.0
                    ),
                    "gold_intent_ids": intents,
                    "current_delta_value_ids": current_delta_slice(
                        authored, scenario=scenario, node=node, cap=current_delta_cap
                    ),
                }
            )

    union_rows = sorted({sid for group in groups for sid in group["row_sample_ids"]})
    counts = {
        "scenarios": len(per_scenario),
        "nodes": len(NODES),
        "groups": len(groups),
        "carriers": len(carriers),
        "carriers_from_roster_topup": topup_count,
        "distinct_group_rows": len(union_rows),
        "eligible_rows": len(eligible),
        "rows_per_group_histogram": dict(
            sorted(Counter(group["row_count"] for group in groups).items())
        ),
        "current_deltas_per_group_histogram": dict(
            sorted(
                Counter(len(group["current_delta_value_ids"]) for group in groups).items()
            )
        ),
        "groups_with_no_current_delta": sum(
            1 for group in groups if not group["current_delta_value_ids"]
        ),
        "gold_intents_per_group_histogram": dict(
            sorted(Counter(len(group["gold_intent_ids"]) for group in groups).items())
        ),
    }
    return groups, counts


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--per-row", required=True, type=Path)
    parser.add_argument("--deltas", required=True, type=Path)
    parser.add_argument("--roster", required=True, type=Path)
    parser.add_argument("--gold-intents", default=None, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--k", default=DEFAULT_K, type=int)
    parser.add_argument("--rank-metric", default="group-mean", choices=RANK_METRICS)
    parser.add_argument(
        "--current-delta-cap", default=DEFAULT_CURRENT_DELTA_CAP, type=int
    )
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.k < 1:
        raise Stage3GepaGroupsError("--k must be >= 1")
    if args.current_delta_cap < 0:
        raise Stage3GepaGroupsError("--current-delta-cap must be >= 0")

    pairs_document = _read_json(args.pairs)
    per_row_document = _read_json(args.per_row)
    deltas_document = _read_json(args.deltas)
    roster_document = _read_json(args.roster)
    if not all(
        isinstance(document, Mapping)
        for document in (pairs_document, per_row_document, deltas_document, roster_document)
    ):
        raise Stage3GepaGroupsError("every input must be a JSON object")

    eligible = load_eligible_rows(pairs_document)
    means = load_group_means(per_row_document)
    roster = load_roster_strata(roster_document)
    authored = load_authored_deltas(deltas_document)
    gold_intents = load_gold_intents(args.gold_intents)

    missing_roster = sorted(set(eligible) - set(roster))
    if missing_roster:
        raise Stage3GepaGroupsError(
            f"{len(missing_roster)} eligible row(s) are not in the construction roster; "
            f"first: {missing_roster[0]}"
        )

    groups, counts = build_groups(
        eligible=eligible,
        means=means,
        roster=roster,
        authored=authored,
        gold_intents=gold_intents,
        k=args.k,
        metric=args.rank_metric,
        current_delta_cap=args.current_delta_cap,
    )

    scored_scenarios = sorted({str(row["stratum"]) for row in eligible.values()})
    roster_scenarios = sorted({str(item["stratum"]) for item in roster.values()})
    excluded = [
        {
            "scenario": scenario,
            "reason": (
                "no row of this scenario carries an available sealed trajectory in "
                "pairs.json (its rollout groups did not disagree), so there is nothing "
                "for a reflective proposer to read"
            ),
        }
        for scenario in roster_scenarios
        if scenario not in set(scored_scenarios)
    ]

    def _pin(path: Path, root: Path) -> dict:
        resolved = Path(path).resolve()
        try:
            relpath = resolved.relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            relpath = resolved.as_posix()
        return {"relpath": relpath, "sha256": sha256_file(resolved)}

    document = {
        "schema": GROUPS_SCHEMA,
        "generator": "scripts/build_slurp_stage3_gepa_groups.py",
        "design_note": (
            "docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md"
        ),
        "stage3_algorithm_id": "gepa-reflective-pareto-v1",
        "k": args.k,
        "rank_metric": args.rank_metric,
        "rank_metric_note": (
            "group-mean: the row's rollout GROUP MEAN official SLU-F1 under "
            "slurp-slu-official-projected-v3-train (per_row.json "
            "group_mean_slu_f1_f1), ascending, ties by sample_id. The row's own "
            "outcome under the one scorer id every number here comes from."
        ),
        "current_delta_cap": args.current_delta_cap,
        "nodes": list(NODES),
        "scenarios": scored_scenarios,
        "excluded_scenarios": excluded,
        "rollout_run_id": pairs_document.get("run_id"),
        "rollout_attempt_id": pairs_document.get("attempt_id"),
        "scorer_id": pairs_document.get("scorer_id"),
        "pairs": _pin(args.pairs, args.data_root),
        "per_row": _pin(args.per_row, args.data_root),
        "deltas": {
            **_pin(args.deltas, args.data_root),
            "iteration": deltas_document.get("iteration"),
            "facet_rule": deltas_document.get("facet_rule"),
            "row_count": len(authored),
        },
        "roster": {
            **_pin(args.roster, args.repo_root),
            "roster_id": roster_document.get("roster_id"),
            "roster_role": roster_document.get("roster_role"),
            "split_identity_hash": roster_document.get("split_identity_hash"),
        },
        "gold_intents": (
            None if args.gold_intents is None else _pin(args.gold_intents, args.data_root)
        ),
        "carrier_sample_ids": [group["carrier_sample_id"] for group in groups],
        "group_row_sample_ids": sorted(
            {sid for group in groups for sid in group["row_sample_ids"]}
        ),
        "groups": groups,
        "counts": counts,
        "contacts": {
            "asr": 0,
            "encoder": 0,
            "model": 0,
            "network": 0,
            "scorer": 0,
            "server": 0,
            "tokenizer": 0,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(document)
    args.out.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()

    report = {
        "schema": "saea-stage3-gepa-groups-report-v1",
        "out": {"relpath": str(args.out), "sha256": digest},
        "counts": counts,
        "scenarios": scored_scenarios,
        "excluded_scenarios": [row["scenario"] for row in excluded],
        "carrier_audio_seconds_total": round(
            sum(float(group["carrier_audio_seconds"]) for group in groups), 4
        ),
        "rank_metric": args.rank_metric,
        "k": args.k,
    }
    print(json.dumps(report, indent=2, sort_keys=True))  # noqa: T201 -- ids/counts only
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Stage3GepaGroupsError as error:  # pragma: no cover - CLI surface
        print(f"build_slurp_stage3_gepa_groups: FAIL: {error}", file=sys.stderr)
        raise SystemExit(2) from None
