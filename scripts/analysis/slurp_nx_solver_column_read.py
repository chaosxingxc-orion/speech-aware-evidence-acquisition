#!/usr/bin/env python3
"""NX programme E2: the node-local reader for a sealed Solver template column (and, E-S2, supply column).

Programme ``docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`` C0.1 / C1 item E2.
A sealed run whose Solver node carries a ``template_variants`` group (item E1, receipt
``saea-supply-variant-arms-v4``) holds K RAW first-visit Solver answers per row, one per
instruction-template arm, all composed over the SAME QueryState and the SAME evidence. This reader
scores each arm against the DELIVERING (locked-template) arm, PAIRED per row, on the node-local
metrics the programme names for the Solver, in TWO views of the same answers (schema v2):

* the NORMALISED view (PRIMARY, ``exact_set_normalised``): the answer after the delivered row's OWN
  sealed delivery normaliser, derived through the SAME function the official column scorer calls
  (``stage3_rollout_score.normalise_arm_answer``: normaliser id -> v3 cited-answer unwrap -> SLURP
  deliver projection; fallback ``parse_slu_response`` + ``render_answer``). This is what the cell
  would deliver, so a gain here is not formatting the normaliser already repairs (R1 iteration 1:
  r1-c5 read +2.50 raw yet -0.15 on the official column);
* the RAW view (diagnostic): the sealed first-visit text exactly as the core wrote it.

The four metrics, each computed on both views:

* ``parse_valid``           -- the answer parses through the governed SLURP parser
                               (``reproduction.slurp_scoring.parse_slu_response``);
* ``exact_set``             -- the answer's entity set equals the gold set EXACTLY
                               (the official exact matcher's ``{type, filler}`` equality, via
                               ``analysis.sealed_credit.entity_states.entity_items``: no error
                               item at all); an unparsed answer is not exact;
* ``empty_gold_false_fill`` -- on rows whose gold entity list is empty: the answer parses and emits
                               at least one entity (lower is better);
* ``nonempty_exact``        -- on rows whose gold entity list is non-empty: ``exact_set``.

Per arm it also tabulates per-slot-type counts (gold items, exactly matched, missing, otherwise
wrong; predicted items and spurious predictions). Value-in-supply conversion needs the supplied
value text, which a sealed receipt does not carry, and is NOT computed here.

Statistics. Every difference is a per-row paired difference (arm minus delivering arm). Reported
with it, per arm and metric: the two rates; the mean difference in pp with a WHOLE-UTTERANCE
CLUSTER bootstrap CI95 (``analysis.paired.resampled_statistic``, 10,000 draws, seed 20260915, a
cluster being one SLURP utterance id -- the first three colon-separated segments of a sample id);
and the paired Wilson read: of the b + c discordant rows (arm right / delivering wrong = b, the
reverse = c), the share b / (b + c) with its Wilson score CI95 -- a share whose interval lies
above 1/2 is the arm winning the rows where the two disagree.

SUPPLY COLUMNS (loop engineering E-S2, 2026-10-11). A run whose Solver node carries a ``supply_variants``
group (receipt ``saea-supply-variant-arms-v3``; flown under the full graph or the review-off module graph, built
by the consumption module's ``supply`` column kind) is read the same way: the arms differ in the SUPPLIED
EVIDENCE (knob re-caps and/or one release swap) instead of the instruction template, every arm still answering
over the same QueryState. The report then also carries ``arm_group_kind: "supply"`` and ``supply_stats``: per
arm, the supplied-item count and the id-set difference against the delivering arm (rows identical, items added,
items removed), read from the arm's sealed ``supplied_value_ids`` -- counts only. The per-error-item value-in-supply
class (E1/E2/E3) needs the supplied value TEXT, which a sealed receipt does not carry, and is NOT computed here.

Gold discipline: gold enters only offline, through the governed SLURP loaders exactly as
``scripts/analysis/slurp_s1_slu_error_taxonomy.py`` loads it (``train`` through the error-source
driver's ``load_gold``; ``devel`` through ``data.slurp.load_slurp_split``); the test split is
refused. Text discipline: no utterance text, transcript, gold value, filler or model output is
printed or persisted -- only ids, counts, rates, pp, slot TYPE names, arm ids and hashes. Zero
model, server, tokenizer, scorer-subprocess, network and GPU contact.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_solver_column_read.py \\
        --data-root "$SPEECHRL_DATA_DIR" --lock docs/datasets.lock.json \\
        --run-id <RUN_ID> --attempt-id <ATTEMPT_ID> --split train
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

READ_ID = "SAEA-NX-SOLVER-TEMPLATE-COLUMN-READ-V1"
RECIPE = "slurp-nx-solver-column-read-v2"
#: The ``report.json`` schema. v1 (single raw view) is superseded: v2 carries both views, the
#: normalised one primary, and the per-arm raw-vs-normalised flip table.
SCHEMA_VERSION = "saea-nx-solver-column-read-v2"
SEED = 20260915
DRAWS = 10_000
CI_LEVEL = 0.95
Z95 = 1.959963984540054
DEFAULT_LOCK = "docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")

#: ``(metric, subset of rows, higher_is_better)``. The primary is ``exact_set``.
METRICS = (
    ("parse_valid", "all", True),
    ("exact_set", "all", True),
    ("empty_gold_false_fill", "empty_gold", False),
    ("nonempty_exact", "nonempty_gold", True),
)
#: The registered primary is the exact-set of the NORMALISED (delivered-equivalent) answer.
PRIMARY = "exact_set_normalised"
VIEW_PRIMARY_METRIC = "exact_set"
SECONDARIES = ("parse_valid", "empty_gold_false_fill", "nonempty_exact")
V4_SCHEMA = "saea-supply-variant-arms-v4"
V3_SCHEMA = "saea-supply-variant-arms-v3"
V5_SCHEMA = "saea-supply-variant-arms-v5"  # loop item E-T6: multi-store release_swaps
#: receipt schema -> the arm group kind it seals.
KIND_BY_SCHEMA = {V4_SCHEMA: "template", V3_SCHEMA: "supply", V5_SCHEMA: "supply"}


class ColumnReadError(RuntimeError):
    """The sealed run, its gold or its arm group is not what this reader reads."""


# ---------------------------------------------------------------------------
# pure parts (unit-tested on synthetic sealed records)


def utterance_id(sample_id: str) -> str:
    """The cluster a row is resampled under: its SLURP utterance (the first three
    colon-separated segments of the sample id, W3a's convention)."""

    return ":".join(str(sample_id).split(":")[:3])


def wilson(successes: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for a binomial share; ``(0, 1)`` for an empty denominator."""

    if n <= 0:
        return 0.0, 1.0
    p = successes / n
    denominator = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def score_answer(raw_text: str, gold_entities: Sequence) -> dict:
    """One raw first answer against one row's gold entities. Returns booleans and
    per-type counts only -- never a filler."""

    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        SlotEntity, parse_slu_response,
    )

    gold = tuple(SlotEntity(str(g.type), str(g.filler)) for g in gold_entities)
    _scenario, _action, predicted, parsed = parse_slu_response(raw_text)
    pred = tuple(predicted) if parsed else ()
    items = entity_items(gold, pred)
    exact = parsed and not items
    gold_side = [i for i in items if i["gold_index"] is not None]
    by_type: dict[str, Counter] = {}

    def bucket(entity_type: str) -> Counter:
        return by_type.setdefault(entity_type, Counter())

    for entity in gold:
        bucket(entity.type)["gold_items"] += 1
    for item in gold_side:
        bucket(item["type"])["gold_missing" if item["kind"] == "MISSING" else "gold_wrong"] += 1
    for entity in pred:
        bucket(entity.type)["pred_items"] += 1
    for item in items:
        if item["kind"] == "SPURIOUS":
            bucket(item["type"])["spurious"] += 1
    for entity_type, counts in by_type.items():
        counts["gold_exact"] = counts["gold_items"] - counts["gold_missing"] - counts["gold_wrong"]
    return {
        "parsed": bool(parsed),
        "n_gold": len(gold),
        "n_pred": len(pred),
        "exact_set": bool(exact),
        "false_fill": (bool(parsed and pred) if not gold else None),
        "nonempty_exact": (bool(exact) if gold else None),
        "by_type": {t: dict(c) for t, c in by_type.items()},
    }


def metric_value(row: Mapping, metric: str) -> int | None:
    if metric == "parse_valid":
        return int(row["parsed"])
    if metric == "exact_set":
        return int(row["exact_set"])
    if metric == "empty_gold_false_fill":
        return None if row["false_fill"] is None else int(row["false_fill"])
    if metric == "nonempty_exact":
        return None if row["nonempty_exact"] is None else int(row["nonempty_exact"])
    raise ColumnReadError(f"unknown metric {metric!r}")


def paired_metric(
    scored_arm: Mapping[str, Mapping], scored_ref: Mapping[str, Mapping], ids: Sequence[str],
    metric: str, *, seed: int = SEED, draws: int = DRAWS,
) -> dict:
    """One arm vs the delivering arm on one metric, PAIRED per row."""

    from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic

    subset = [s for s in ids
              if metric_value(scored_arm[s], metric) is not None]
    arm_v = {s: metric_value(scored_arm[s], metric) for s in subset}
    ref_v = {s: metric_value(scored_ref[s], metric) for s in subset}
    n = len(subset)
    if n == 0:
        return {"n": 0, "rate_arm": None, "rate_delivering": None, "diff_pp": None, "ci95_pp": None,
                "b_arm_only": 0, "c_delivering_only": 0, "discordant_share": None, "wilson95": None}
    diff = {s: arm_v[s] - ref_v[s] for s in subset}
    b = sum(1 for s in subset if arm_v[s] == 1 and ref_v[s] == 0)
    c = sum(1 for s in subset if arm_v[s] == 0 and ref_v[s] == 1)
    result = resampled_statistic(
        sample_ids=subset,
        statistic=lambda chosen: sum(diff[s] for s in chosen) / len(chosen),
        seed=seed, n_replicates=draws, ci_level=CI_LEVEL, cluster_of=utterance_id,
    )
    lo, hi = wilson(b, b + c)
    return {
        "n": n,
        "rate_arm": sum(arm_v.values()) / n,
        "rate_delivering": sum(ref_v.values()) / n,
        "diff_pp": 100.0 * result.point_estimate,
        "ci95_pp": [100.0 * result.ci_low, 100.0 * result.ci_high],
        "b_arm_only": b, "c_delivering_only": c,
        "discordant_share": (b / (b + c)) if b + c else None,
        "wilson95": [lo, hi] if b + c else None,
    }


def type_table(scored_arm: Mapping[str, Mapping], ids: Sequence[str]) -> dict:
    """Per-slot-type counts summed over the roster (names and counts only)."""

    total: dict[str, Counter] = {}
    for sid in ids:
        for entity_type, counts in scored_arm[sid]["by_type"].items():
            total.setdefault(entity_type, Counter()).update(counts)
    keys = ("gold_items", "gold_exact", "gold_missing", "gold_wrong", "pred_items", "spurious")
    return {t: {k: int(total[t].get(k, 0)) for k in keys} for t in sorted(total)}


def _view(
    texts: Mapping[str, Mapping[str, str]], gold: Mapping[str, Mapping], *, arm_ids: Sequence[str],
    delivering: str, twin: str | None, ids: Sequence[str], subsets: Mapping[str, Sequence[str]],
    seed: int, draws: int,
) -> tuple[dict, dict]:
    """One view (raw or normalised) of the whole column: per-arm tables and the scored rows."""

    scored = {
        arm: {sid: score_answer(texts[arm][sid], gold[sid]["entities"]) for sid in ids}
        for arm in arm_ids
    }
    arms_out = {}
    for arm in arm_ids:
        row_stats = scored[arm]
        paired = {}
        if arm != delivering:
            for metric, subset_name, _higher in METRICS:
                paired[metric] = paired_metric(
                    row_stats, scored[delivering], subsets[subset_name], metric,
                    seed=seed, draws=draws,
                )
        marginal = {}
        for metric, subset_name, _higher in METRICS:
            values = [metric_value(row_stats[s], metric) for s in subsets[subset_name]]
            values = [v for v in values if v is not None]
            lo, hi = wilson(sum(values), len(values))
            marginal[metric] = {
                "n": len(values), "count": sum(values),
                "rate": (sum(values) / len(values)) if values else None, "wilson95": [lo, hi],
            }
        arms_out[arm] = {
            "role": ("delivering" if arm == delivering else "twin" if arm == twin else "candidate"),
            "marginal": marginal, "paired_vs_delivering": paired,
            "by_slot_type": type_table(row_stats, ids),
            "predicted_items": sum(row_stats[s]["n_pred"] for s in ids),
        }
    return arms_out, scored


def _screen(arms_out: Mapping[str, Mapping], arm_ids: Sequence[str], delivering: str,
            twin: str | None) -> dict:
    screen = {}
    for arm in arm_ids:
        if arm == delivering or arm == twin:
            continue
        paired = arms_out[arm]["paired_vs_delivering"]
        against = []
        for metric, _subset, higher in METRICS:
            if metric == VIEW_PRIMARY_METRIC:
                continue
            ci = paired[metric]["ci95_pp"]
            if ci is None:
                continue
            if (higher and ci[1] < 0) or (not higher and ci[0] > 0):
                against.append(metric)
        primary_ci = paired[VIEW_PRIMARY_METRIC]["ci95_pp"]
        screen[arm] = {
            "primary_ci_lb_gt_0": bool(primary_ci is not None and primary_ci[0] > 0),
            "secondaries_with_ci_against": against,
            "passes_mechanical_screen": bool(
                primary_ci is not None and primary_ci[0] > 0 and not against
            ),
        }
    return screen


def read_columns(
    texts: Mapping[str, Mapping[str, str]], gold: Mapping[str, Mapping], *,
    arm_ids: Sequence[str], delivering: str, twin: str | None = None,
    normalised_texts: Mapping[str, Mapping[str, str]] | None = None,
    seed: int = SEED, draws: int = DRAWS,
    group_kind: str = "template", supplied_ids: Mapping[str, Mapping[str, Sequence[str]]] | None = None,
) -> dict:
    """The whole column read over ``texts[arm_id][sample_id] -> raw answer``.

    ``normalised_texts`` is the same grid after the delivered row's normaliser
    (:func:`normalise_texts`); left ``None`` it is the raw grid (an identity normalisation, for a
    caller whose cell delivers raw answers).
    """

    arm_ids = list(arm_ids)
    if delivering not in arm_ids:
        raise ColumnReadError("the delivering arm is not among the arms")
    ids = sorted(texts[delivering])
    normalised = texts if normalised_texts is None else normalised_texts
    for grid_name, grid in (("raw", texts), ("normalised", normalised)):
        for arm in arm_ids:
            if sorted(grid[arm]) != ids:
                raise ColumnReadError(
                    f"arm {arm!r} does not cover the delivering arm's rows ({grid_name} grid)"
                )
    missing = [s for s in ids if s not in gold]
    if missing:
        raise ColumnReadError(f"{len(missing)} roster ids are absent from the gold")
    subsets = {
        "all": ids,
        "empty_gold": [s for s in ids if not gold[s]["entities"]],
        "nonempty_gold": [s for s in ids if gold[s]["entities"]],
    }
    raw_arms, raw_scored = _view(texts, gold, arm_ids=arm_ids, delivering=delivering, twin=twin,
                                 ids=ids, subsets=subsets, seed=seed, draws=draws)
    norm_arms, norm_scored = _view(normalised, gold, arm_ids=arm_ids, delivering=delivering,
                                   twin=twin, ids=ids, subsets=subsets, seed=seed, draws=draws)
    flips = {}
    for arm in arm_ids:
        raw_s, norm_s = raw_scored[arm], norm_scored[arm]
        flips[arm] = {
            "rows": len(ids),
            "text_changed": sum(1 for s in ids if texts[arm][s] != normalised[arm][s]),
            "exact_raw_false_to_normalised_true": sum(
                1 for s in ids if not raw_s[s]["exact_set"] and norm_s[s]["exact_set"]),
            "exact_raw_true_to_normalised_false": sum(
                1 for s in ids if raw_s[s]["exact_set"] and not norm_s[s]["exact_set"]),
            "parse_raw_false_to_normalised_true": sum(
                1 for s in ids if not raw_s[s]["parsed"] and norm_s[s]["parsed"]),
            "parse_raw_true_to_normalised_false": sum(
                1 for s in ids if raw_s[s]["parsed"] and not norm_s[s]["parsed"]),
        }
    report = {
        "read_id": READ_ID, "recipe": RECIPE, "schema_version": SCHEMA_VERSION,
        "status": "DESCRIPTIVE",
        "rows": len(ids),
        "rows_empty_gold": len(subsets["empty_gold"]),
        "rows_nonempty_gold": len(subsets["nonempty_gold"]),
        "bootstrap": {"draws": draws, "seed": seed, "ci_level": CI_LEVEL,
                      "cluster": "whole utterance (first three colon segments of the sample id)"},
        "arm_order": arm_ids, "delivering_arm": delivering, "twin_arm": twin,
        "primary_metric": PRIMARY, "primary_view": "normalised",
        "secondary_metrics": list(SECONDARIES),
        "mechanical_screen": _screen(norm_arms, arm_ids, delivering, twin),
        "arms": norm_arms,
        "raw_diagnostic": {
            "view": "raw (the sealed first-visit text, before the delivery normaliser)",
            "diagnostic_primary": "exact_set",
            "mechanical_screen": _screen(raw_arms, arm_ids, delivering, twin),
            "arms": raw_arms,
        },
        "raw_vs_normalised": flips,
    }
    if group_kind == "supply":
        report["arm_group_kind"] = "supply"
        report["supply_stats"] = supply_stats(supplied_ids or {}, arm_ids, delivering, ids)
    elif group_kind != "template":
        raise ColumnReadError(f"unknown arm group kind {group_kind!r}")
    return report


def supply_stats(
    supplied_ids: Mapping[str, Mapping[str, Sequence[str]]], arm_ids: Sequence[str], delivering: str,
    ids: Sequence[str],
) -> dict:
    """Per arm, from the sealed ``supplied_value_ids`` (ids only): the supplied-item count and the
    id-set difference against the delivering arm. Counts and shares; never a value text."""

    for arm in arm_ids:
        if sorted(supplied_ids.get(arm, {})) != sorted(ids):
            raise ColumnReadError(f"arm {arm!r} carries no sealed supplied ids for every roster row")
    out = {}
    n = len(ids)
    for arm in arm_ids:
        items = [len(supplied_ids[arm][s]) for s in ids]
        entry = {
            "rows": n, "items_total": sum(items), "items_mean": (sum(items) / n) if n else None,
            "rows_with_no_items": sum(1 for v in items if v == 0),
        }
        if arm != delivering:
            added = removed = identical = reordered = 0
            for s in ids:
                mine, ref = list(supplied_ids[arm][s]), list(supplied_ids[delivering][s])
                added += len(set(mine) - set(ref))
                removed += len(set(ref) - set(mine))
                identical += int(set(mine) == set(ref))
                reordered += int(set(mine) == set(ref) and mine != ref)
            entry.update({
                "rows_same_id_set": identical, "rows_same_set_other_order": reordered,
                "items_added_vs_delivering": added, "items_removed_vs_delivering": removed,
                "items_added_mean": (added / n) if n else None,
                "items_removed_mean": (removed / n) if n else None,
            })
        out[arm] = entry
    return out


# ---------------------------------------------------------------------------
# the sealed-run side


def load_sealed_arm_texts(outputs_rows: Sequence[Mapping], trace_records: Mapping[str, Mapping]) -> dict:
    """The raw first-visit answer of every arm of every row of a sealed template or supply column.

    ``outputs_rows`` and ``trace_records`` are a verified bundle's own (``core.bundle.
    verify_bundle(...).outputs_rows`` / ``.trace_records``). Refuses a row whose receipt is not the
    node-template (v4) or supply (v3) shape, whose arm group differs from the first row's, whose first Solver visit
    is not the full arm group, or whose trace pair disagrees with the arm's sealed contact.
    """

    from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
        validate_supply_variant_receipt,
    )

    arm_ids: tuple[str, ...] | None = None
    templates: list | None = None
    declarations: list | None = None
    kind: str | None = None
    supplied: dict[str, dict[str, list[str]]] = {}
    delivering: str | None = None
    twin: str | None = None
    texts: dict[str, dict[str, str]] = {}
    normaliser_ids: dict[str, str | None] = {}
    skipped: list[str] = []
    for row in outputs_rows:
        sid = row.get("sample_id")
        if not isinstance(sid, str) or not sid:
            raise ColumnReadError("an outputs row has no sample id")
        receipt = row.get("supply_variants")
        episode = row.get("native_episode_receipt")
        visits = episode.get("role_visits") if isinstance(episode, Mapping) else None
        solver = [v for v in (visits or []) if isinstance(v, Mapping) and v.get("stage") == "solver"]
        if receipt is None:
            if solver:
                raise ColumnReadError(f"{sid}: a Solver visit sealed no template-variant custody")
            skipped.append(sid)
            continue
        if not isinstance(receipt, Mapping) or receipt.get("schema") not in KIND_BY_SCHEMA:
            raise ColumnReadError(
                f"{sid}: supply_variants is not a {V4_SCHEMA} node-template or {V3_SCHEMA} supply "
                "receipt; this reader reads template and supply columns only"
            )
        row_kind = KIND_BY_SCHEMA[receipt["schema"]]
        if kind is not None and row_kind != kind:
            raise ColumnReadError(f"{sid}: the arm group kind ({row_kind}) differs from the first row's ({kind})")
        row_arm_ids = tuple(arm["arm_id"] for arm in receipt["arms"])
        validate_supply_variant_receipt(
            receipt, arm_ids=row_arm_ids, delivered_arm_id=row_arm_ids[-1],
            phase_id=receipt["phase_id"], error_type=ColumnReadError,
        )
        if row_kind == "template":
            row_templates = [arm["instruction_template"] for arm in receipt["arms"]]
        else:  # a supply column: the declared supply of each arm (knobs, release swap, bound)
            if receipt["schema"] == V5_SCHEMA:  # every swapped store, in store order
                row_templates = [
                    {"resolved_knobs": arm.get("resolved_knobs"), "release_swaps": arm.get("release_swaps"),
                     "max_supplied_items": arm.get("max_supplied_items")}
                    for arm in receipt["arms"]
                ]
            else:
                row_templates = [
                    {"resolved_knobs": arm.get("resolved_knobs"), "release_swap": arm.get("release_swap"),
                     "max_supplied_items": arm.get("max_supplied_items")}
                    for arm in receipt["arms"]
                ]
        row_twin = next((a["arm_id"] for a in receipt["arms"] if a.get("replicate_of")), None)
        if arm_ids is None:
            arm_ids, templates, delivering, twin = row_arm_ids, row_templates, row_arm_ids[-1], row_twin
            kind = row_kind
            texts = {arm: {} for arm in arm_ids}
            supplied = {arm: {} for arm in arm_ids}
        elif (row_arm_ids, row_templates, row_twin) != (arm_ids, templates, twin):
            raise ColumnReadError(f"{sid}: the arm group or its templates differ from the first row's")
        if row_kind == "supply":
            for arm_row in receipt["arms"]:
                supplied[arm_row["arm_id"]][sid] = list(arm_row.get("supplied_value_ids") or [])
        if not solver:
            raise ColumnReadError(f"{sid}: template custody without a Solver visit")
        # the delivered row's OWN sealed normaliser, exactly where the column scorer reads it
        deliver_receipt = episode.get("deliver_normaliser")
        normaliser_ids[sid] = (
            deliver_receipt.get("normaliser_id") if isinstance(deliver_receipt, Mapping) else None
        )
        first = solver[0].get("execution_receipt")
        contacts = first.get("contacts") if isinstance(first, Mapping) else None
        if not isinstance(contacts, list) or len(contacts) != len(arm_ids):
            raise ColumnReadError(f"{sid}: the first Solver visit is not the full arm group")
        for arm_id, arm_row, contact in zip(arm_ids, receipt["arms"], contacts, strict=True):
            if arm_row["contact_id"] != contact.get("agent_contact_id"):
                raise ColumnReadError(f"{sid}: arm {arm_id!r} custody names another contact")
            request_id = contact.get("request_id")
            response = trace_records.get(f"{request_id}/response")
            request = trace_records.get(f"{request_id}/request")
            if not isinstance(response, Mapping) or not isinstance(request, Mapping):
                raise ColumnReadError(f"{sid}: arm {arm_id!r} has no trace pair")
            raw = response.get("text")
            if (
                not isinstance(raw, str)
                or request.get("payload_sha256") != contact.get("request_sha256")
                or hashlib.sha256(raw.encode("utf-8")).hexdigest() != contact.get("response_text_sha256")
            ):
                raise ColumnReadError(f"{sid}: arm {arm_id!r} trace differs from its sealed contact")
            texts[arm_id][sid] = raw
    if arm_ids is None:
        raise ColumnReadError("no row of the run carries template-variant custody")
    return {"arm_ids": arm_ids, "templates": templates, "delivering": delivering, "twin": twin,
            "texts": texts, "normaliser_ids": normaliser_ids,
            "rows_without_solver_visit": sorted(skipped), "kind": kind,
            "supplied_ids": supplied if kind == "supply" else None}


def normalise_texts(
    texts: Mapping[str, Mapping[str, str]], normaliser_ids: Mapping[str, str | None],
) -> dict[str, dict[str, str]]:
    """Every raw answer through the delivered row's own normaliser, by the column scorer's function
    (``stage3_rollout_score.normalise_arm_answer``) -- reused, not re-implemented."""

    from stage3_rollout_score import normalise_arm_answer

    return {
        arm: {sid: normalise_arm_answer(raw, normaliser_ids.get(sid))[0] for sid, raw in rows.items()}
        for arm, rows in texts.items()
    }


# ---------------------------------------------------------------------------
# rendering


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{100.0 * value:.2f}"


def _render_view(report: Mapping, arms: Mapping, screen: Mapping, heading: str) -> list[str]:
    lines = [
        f"## {heading}: marginal rates (%)", "",
        "| arm | role | parse valid | exact set | empty-gold false fill | non-empty exact | predicted items |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm in report["arm_order"]:
        m = arms[arm]["marginal"]
        lines.append(
            f"| {arm} | {arms[arm]['role']} | {_pct(m['parse_valid']['rate'])} | "
            f"{_pct(m['exact_set']['rate'])} | {_pct(m['empty_gold_false_fill']['rate'])} | "
            f"{_pct(m['nonempty_exact']['rate'])} | {arms[arm]['predicted_items']} |"
        )
    lines += ["", f"## {heading}: paired difference vs the delivering arm (pp, CI95) and discordant rows", "",
              "| arm | metric | n | diff pp | CI95 pp | b (arm only) | c (delivering only) | share b/(b+c) | Wilson95 |",
              "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |"]
    for arm in report["arm_order"]:
        for metric, _subset, _higher in METRICS:
            p = arms[arm]["paired_vs_delivering"].get(metric)
            if p is None:
                continue
            ci = "-" if p["ci95_pp"] is None else f"[{p['ci95_pp'][0]:+.2f}, {p['ci95_pp'][1]:+.2f}]"
            wil = "-" if p["wilson95"] is None else f"[{p['wilson95'][0]:.3f}, {p['wilson95'][1]:.3f}]"
            diff = "-" if p["diff_pp"] is None else f"{p['diff_pp']:+.2f}"
            share = "-" if p["discordant_share"] is None else f"{p['discordant_share']:.3f}"
            lines.append(
                f"| {arm} | {metric} | {p['n']} | {diff} | {ci} | {p['b_arm_only']} | "
                f"{p['c_delivering_only']} | {share} | {wil} |"
            )
    lines += ["", f"## {heading}: mechanical screen (exact-set CI lower bound above 0, no secondary CI against)", "",
              "| arm | exact-set CI-LB > 0 | secondaries against | passes |", "| --- | --- | --- | --- |"]
    for arm, s in screen.items():
        lines.append(
            f"| {arm} | {s['primary_ci_lb_gt_0']} | {', '.join(s['secondaries_with_ci_against']) or '-'} | "
            f"{s['passes_mechanical_screen']} |"
        )
    return lines


def render(report: Mapping) -> str:
    arms = report["arms"]
    raw = report["raw_diagnostic"]
    lines = [
        f"# {report['read_id']} tables ({report['schema_version']})", "",
        f"{report['rows']} rows ({report['rows_empty_gold']} empty-gold, {report['rows_nonempty_gold']} "
        f"non-empty-gold). Delivering arm `{report['delivering_arm']}`"
        + (f", twin `{report['twin_arm']}`" if report["twin_arm"] else "")
        + f". Bootstrap: {report['bootstrap']['draws']} draws, seed {report['bootstrap']['seed']}, "
        "whole-utterance clusters, CI95. DESCRIPTIVE; development numbers.", "",
        f"PRIMARY: `{report['primary_metric']}` -- the exact-set of the answer AFTER the delivered row's own "
        "delivery normaliser. The raw view below it is a diagnostic only.", "",
    ]
    lines += _render_view(report, arms, report["mechanical_screen"], "NORMALISED (primary)")
    lines += ["", "## Raw vs normalised: rows changed by the delivery normaliser (per arm)", "",
              "| arm | rows | text changed | exact raw false -> normalised true | exact raw true -> normalised false "
              "| parse false -> true | parse true -> false |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for arm in report["arm_order"]:
        f = report["raw_vs_normalised"][arm]
        lines.append(
            f"| {arm} | {f['rows']} | {f['text_changed']} | {f['exact_raw_false_to_normalised_true']} | "
            f"{f['exact_raw_true_to_normalised_false']} | {f['parse_raw_false_to_normalised_true']} | "
            f"{f['parse_raw_true_to_normalised_false']} |"
        )
    lines += [""]
    lines += _render_view(report, raw["arms"], raw["mechanical_screen"], "RAW (diagnostic)")
    if report.get("arm_group_kind") == "supply":
        lines += ["", "## Supply columns: supplied items and id-set difference vs the delivering arm (ids only)", "",
                  "| arm | items total | items mean | rows no items | rows same id set | rows same set other order "
                  "| items added | items removed |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for arm in report["arm_order"]:
            st = report["supply_stats"][arm]
            lines.append(
                f"| {arm} | {st['items_total']} | {st['items_mean']:.2f} | {st['rows_with_no_items']} | "
                f"{st.get('rows_same_id_set', '-')} | {st.get('rows_same_set_other_order', '-')} | "
                f"{st.get('items_added_vs_delivering', '-')} | {st.get('items_removed_vs_delivering', '-')} |"
            )
    for arm in report["arm_order"]:
        lines += ["", f"## Per slot type, normalised ({arm})", "",
                  "| type | gold | gold exact | gold missing | gold wrong | predicted | spurious |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for entity_type, c in arms[arm]["by_slot_type"].items():
            lines.append(
                f"| {entity_type} | {c['gold_items']} | {c['gold_exact']} | {c['gold_missing']} | "
                f"{c['gold_wrong']} | {c['pred_items']} | {c['spurious']} |"
            )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI


def _import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_gold(lock, data_root: Path, split: str) -> dict:
    """Gold per sample id through the governed SLURP loaders, exactly as the S1 taxonomy loads it."""

    if split == "train":
        ES = _import_path(REPO_ROOT / "scripts/analysis/slurp_agree_arm_error_sources.py",
                          "slurp_agree_arm_error_sources")
        return ES.load_gold(lock, data_root)
    if split != "devel":
        raise ColumnReadError(f"split {split!r} is not read here (the test split is closed)")
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

    records = load_slurp_split(lock, data_root, "devel", workers=4)
    return {r.sample_id: {"entities": tuple(SlotEntity(e.type, e.filler) for e in r.entities)}
            for r in records}


def build(args) -> dict:
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle
    from speech_aware_evidence_acquisition.data.lock import load_lock

    data_root = Path(args.data_root)
    directory = data_root / "runs" / args.run_id / args.attempt_id
    if not directory.is_dir():
        raise ColumnReadError(f"no sealed attempt directory at {directory}")
    bundle = verify_bundle(directory / f"{args.run_id}.run-manifest.json")
    sealed = load_sealed_arm_texts(bundle.outputs_rows, bundle.trace_records)
    gold = load_gold(load_lock(Path(args.lock)), data_root, args.split)
    normalised = normalise_texts(sealed["texts"], sealed["normaliser_ids"])
    report = read_columns(
        sealed["texts"], gold, arm_ids=sealed["arm_ids"], delivering=sealed["delivering"],
        twin=sealed["twin"], normalised_texts=normalised, seed=args.seed, draws=args.draws,
        group_kind=sealed["kind"], supplied_ids=sealed["supplied_ids"],
    )
    report["inputs"] = {
        "run_id": args.run_id, "attempt_id": args.attempt_id, "split": args.split,
        "manifest_sha256": hashlib.sha256(
            (directory / f"{args.run_id}.run-manifest.json").read_bytes()
        ).hexdigest(),
        ("templates" if sealed["kind"] == "template" else "declarations"):
            dict(zip(sealed["arm_ids"], sealed["templates"], strict=True)),
        "rows_without_solver_visit": len(sealed["rows_without_solver_visit"]),
        "deliver_normaliser_ids": dict(sorted(Counter(
            str(v) for v in sealed["normaliser_ids"].values()).items())),
    }
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=str(REPO_ROOT / DEFAULT_LOCK))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--split", choices=("train", "devel"), required=True)
    parser.add_argument("--draws", type=int, default=DRAWS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)
    report = build(args)
    out_dir = Path(args.out_dir) if args.out_dir else Path(args.data_root) / "analysis" / READ_ID / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    texts = {"report.json": json.dumps(report, indent=2, sort_keys=True) + "\n", "tables.md": render(report)}
    for name, text in texts.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    print("wrote", out_dir)
    print(json.dumps({n: hashlib.sha256(t.encode("utf-8")).hexdigest() for n, t in sorted(texts.items())},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
