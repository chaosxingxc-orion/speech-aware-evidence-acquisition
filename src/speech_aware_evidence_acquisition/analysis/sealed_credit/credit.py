"""The per-node credit table (design spec task 3).

Builds, from one or more extracted pools (``analysis.sealed_credit.row_states.
extract_pool``), the conversion rates the estimator (``analysis.sealed_credit.
estimate``) turns into a candidate's predicted effect: P(delivered correct | node
state) per node-state class, with a whole-utterance cluster-bootstrap interval
(``analysis.bootstrap.paired_cluster_bootstrap``, the same primitive
``slurp_reviewer_credit_table.py`` and the node-gain ledger already use), plus the
Reviewer/Planner and deliver-normaliser "exact offline" edges (single-sample-arm
pools only -- the toggle replays the ALREADY-SEALED first/last Solver state and the
already-sealed delivered answer, never a model contact).

Canonical JSON: every table is built from sorted ids and sorted dict keys, so
``json.dumps(document, indent=2, sort_keys=True)`` is deterministic given the same
input pools and seed; ``table_sha256`` is the sha256 of that exact text (with
``table_sha256`` itself absent, computed once and then embedded) -- the credit
table's own hash pin.

Counts and rates only: no filler text, no utterance text, ever leaves this module.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

from speech_aware_evidence_acquisition.analysis.bootstrap import paired_cluster_bootstrap

DEFAULT_SEED = 20260807
DEFAULT_N_REPLICATES = 2000
DEFAULT_CI_LEVEL = 0.95


class CreditError(RuntimeError):
    pass


def _rate_stat(hits: Mapping[str, float]) -> Callable[[list[str]], float]:
    def statistic(ids: list[str]) -> float:
        return 100.0 * sum(hits[s] for s in ids) / len(ids)
    return statistic


def bootstrap_rate(
    ids: list[str], hits: Mapping[str, float], *,
    seed: int = DEFAULT_SEED, n_replicates: int = DEFAULT_N_REPLICATES, ci_level: float = DEFAULT_CI_LEVEL,
) -> dict[str, Any]:
    """P(hit)*100 over ``ids`` with a whole-utterance cluster-bootstrap CI."""

    if not ids:
        raise CreditError("bootstrap_rate requires at least one sample id")
    result = paired_cluster_bootstrap(
        sample_ids=ids, statistic=_rate_stat(hits), seed=seed, n_replicates=n_replicates, ci_level=ci_level,
    )
    return {
        "n": len(ids), "hits": round(sum(hits[s] for s in ids), 3),
        "rate_pct": round(result.point_estimate, 4),
        "ci95": [round(result.ci_low, 4), round(result.ci_high, 4)],
        "sigma_hat": round(result.sigma_hat, 4),
    }


def bootstrap_delta_pct(
    ids: list[str], a_hits: Mapping[str, float], b_hits: Mapping[str, float], *,
    seed: int = DEFAULT_SEED, n_replicates: int = DEFAULT_N_REPLICATES, ci_level: float = DEFAULT_CI_LEVEL,
) -> dict[str, Any]:
    """(mean(b) - mean(a)) * 100 over ``ids``, paired at the sample-id cluster."""

    if not ids:
        raise CreditError("bootstrap_delta_pct requires at least one sample id")

    def statistic(sample: list[str]) -> float:
        return 100.0 * (sum(b_hits[s] for s in sample) - sum(a_hits[s] for s in sample)) / len(sample)

    result = paired_cluster_bootstrap(
        sample_ids=ids, statistic=statistic, seed=seed, n_replicates=n_replicates, ci_level=ci_level,
    )
    return {
        "n": len(ids),
        "a_pct": round(100.0 * sum(a_hits[s] for s in ids) / len(ids), 4),
        "b_pct": round(100.0 * sum(b_hits[s] for s in ids) / len(ids), 4),
        "delta_pp": round(result.point_estimate, 4),
        "ci95": [round(result.ci_low, 4), round(result.ci_high, 4)],
        "sigma_hat": round(result.sigma_hat, 4),
    }


def conversion_table(
    ids: list[str], bucket_of: Callable[[str], str], hit_of: Callable[[str], float], *,
    seed: int = DEFAULT_SEED, n_replicates: int = DEFAULT_N_REPLICATES, ci_level: float = DEFAULT_CI_LEVEL,
) -> dict[str, Any]:
    buckets: dict[str, list[str]] = {}
    for sid in ids:
        buckets.setdefault(bucket_of(sid), []).append(sid)
    hits = {sid: hit_of(sid) for sid in ids}
    return {
        bucket: bootstrap_rate(bucket_ids, hits, seed=seed, n_replicates=n_replicates, ci_level=ci_level)
        for bucket, bucket_ids in sorted(buckets.items())
    }


# ---------------------------------------------------------------------------
# node-specific bucketing


def block_position_bucket(pos: int | None) -> str:
    if pos is None:
        return "none"
    if pos == 1:
        return "1"
    if pos <= 3:
        return "2-3"
    if pos <= 8:
        return "4-8"
    return "9+"


def perception_rank_conversion(pool: Mapping[str, Any], only_ids: set[str] | None = None) -> dict[str, Any]:
    """P(Solver's FIRST answer correct | Perception rank bucket) -- the P->S1
    edge, matched exactly against the design spec's own published AGREE numbers
    (section 2b: rank 1 97.57 %, rank 2 26.98 % (63 rows), rank 3+ 12.0 %, absent
    2.35 %; verified byte-for-byte against this run's own AGREE pool). The hit is
    ``s1_ok``, not ``d_ok``: a Perception/boundary knob's causal effect is what
    the IMMEDIATE next node (the first Solver answer) does with a better-ranked
    or better-positioned gold entry -- crediting it with ``d_ok`` instead would
    double-count whatever the Reviewer and the deliver normaliser separately do
    downstream, which already have their own exact-offline toggles below, and
    would violate the design spec's own flight-order "at most one repairing
    node" composition rule. ``only_ids`` restricts to a subset (the two-fold
    cross-fit)."""

    ids = sorted(pool["rows"] if only_ids is None else (set(pool["rows"]) & only_ids))
    return conversion_table(
        ids, lambda s: pool["rows"][s]["perc_rank_bucket"], lambda s: 1.0 if pool["rows"][s]["s1_ok"] else 0.0,
    )


def block_position_conversion(pool: Mapping[str, Any], only_ids: set[str] | None = None) -> dict[str, Any]:
    """P(Solver's FIRST answer correct | boundary-block position bucket) -- the
    B->S1 edge (see :func:`perception_rank_conversion`'s docstring for why the
    hit is ``s1_ok``, not ``d_ok``): the conversion source for a knob that
    widens the Perception seed (``phase_supply.k`` / ``fuse_coverage`` on the
    boundary route, ``min_candidates``). ``only_ids`` restricts to a subset (the
    two-fold cross-fit)."""

    ids = sorted(pool["rows"] if only_ids is None else (set(pool["rows"]) & only_ids))
    return conversion_table(
        ids, lambda s: block_position_bucket(pool["rows"][s]["block_pos"]),
        lambda s: 1.0 if pool["rows"][s]["s1_ok"] else 0.0,
    )


def _item_exact_rate_by_sample(pool: Mapping[str, Any], node: str) -> dict[str, float]:
    """Per sample id, the fraction of its gold entity items that are ``EXACT`` at
    ``node`` (``"s1"`` or ``"d"``) -- an APPROXIMATE, item-count SLU proxy (never
    the official word/char-distance metric, which is defined only at the
    delivered node): used only to bound the Reviewer/normaliser toggle's SLU
    side, always reported with this caveat attached."""

    per_sample: dict[str, list[bool]] = {}
    for item in pool["items"]:
        per_sample.setdefault(item["sample_id"], []).append(item[node] == "EXACT")
    return {sid: (sum(flags) / len(flags) if flags else 1.0) for sid, flags in per_sample.items()}


def reviewer_toggle_effect(pool: Mapping[str, Any], only_ids: set[str] | None = None) -> dict[str, Any] | None:
    """"Reviewer/Planner: off" (exact offline -- deliver S1 instead of the sealed
    delivered answer) vs as-flown, on the same rows. Single-sample-arm pools
    only; ``None`` for a grouped pool (no Reviewer node). ``only_ids`` restricts
    to a subset (the two-fold cross-fit)."""

    if pool["kind"] != "single-sample-arm":
        return None
    ids = sorted(pool["rows"] if only_ids is None else (set(pool["rows"]) & only_ids))
    d_ok = {s: (1.0 if pool["rows"][s]["d_ok"] else 0.0) for s in ids}
    s1_ok = {s: (1.0 if pool["rows"][s]["s1_ok"] else 0.0) for s in ids}
    intent = bootstrap_delta_pct(ids, d_ok, s1_ok)
    s1_item = _item_exact_rate_by_sample(pool, "s1")
    d_item = _item_exact_rate_by_sample(pool, "d")
    common = sorted(set(s1_item) & set(d_item) & set(ids))
    # bootstrap_delta_pct itself multiplies by 100 -- these stay raw [0, 1] fractions.
    slu_proxy = bootstrap_delta_pct(
        common, {s: d_item[s] for s in common}, {s: s1_item[s] for s in common},
    ) if common else None
    return {
        "policy_value": "off", "definition": "deliver_s1 (exact offline replay of the sealed first Solver state)",
        "intent_delta_pp": intent, "slu_proxy_delta_pp": slu_proxy,
        "slu_proxy_caveat": "item-exact-match rate, not the official word/char-distance SLU-F1 metric",
    }


def pool_pair_delta(
    pool_b: Mapping[str, Any], pool_a: Mapping[str, Any], only_ids: set[str] | None = None,
) -> dict[str, Any]:
    """``pool_b`` (a deliberate variant, e.g. a VAR-1 supply arm) minus ``pool_a``
    (its own flown comparator, e.g. PLANR), on their SHARED sample ids -- a paired
    same-roster contrast. Intent uses ``d_ok``; the SLU side uses the mean PER-ROW
    official ``slu_f1_f1`` (module docstring caveat: mean-of-per-row, not the
    pooled/micro aggregate). ``only_ids``, when given, further restricts the shared
    ids (the two-fold cross-fit)."""

    ids = sorted(set(pool_a["rows"]) & set(pool_b["rows"]))
    if only_ids is not None:
        ids = [s for s in ids if s in only_ids]
    if not ids:
        raise CreditError(f"pool_pair_delta: {pool_a['label']!r} and {pool_b['label']!r} share no sample id")
    a_ok = {s: (1.0 if pool_a["rows"][s]["d_ok"] else 0.0) for s in ids}
    b_ok = {s: (1.0 if pool_b["rows"][s]["d_ok"] else 0.0) for s in ids}
    # bootstrap_delta_pct itself multiplies by 100 -- these stay raw [0, 1] fractions.
    a_slu = {s: pool_a["rows"][s]["d_slu_f1"] for s in ids}
    b_slu = {s: pool_b["rows"][s]["d_slu_f1"] for s in ids}
    return {
        "left_pool": pool_a["label"], "right_pool": pool_b["label"], "n": len(ids),
        "intent_delta_pp": bootstrap_delta_pct(ids, a_ok, b_ok),
        "slu_f1_mean_delta_pp": bootstrap_delta_pct(ids, a_slu, b_slu),
        "slu_caveat": "mean of the official per-row slu_f1_f1, not the pooled/micro aggregate",
    }


def relisten_reach_table(pool: Mapping[str, Any]) -> dict[str, Any]:
    """Count of delivered gold entity items whose class is one relisten could act
    on (``BOUNDARY``/``NEAR``/``FORMAT`` -- ``RELISTEN_KINDS`` in the node-gain
    ledger), by Perception-note state. Descriptive only: no sealed relisten read
    (E4-1) exists yet to convert this reach into a predicted effect, so a
    candidate sourced from this table is reported with ``estimated_effect_pp 0.0``
    and the flag ``unobserved`` (design spec section 2c, relisten acceptance row)."""

    relisten_kinds = ("BOUNDARY", "NEAR", "FORMAT")
    by_note: dict[str, int] = {}
    total = 0
    for item in pool["items"]:
        if item["d"] in relisten_kinds:
            total += 1
            by_note[item["note"]] = by_note.get(item["note"], 0) + 1
    return {"relisten_kinds": list(relisten_kinds), "items": total, "by_note_state": dict(sorted(by_note.items()))}


def normaliser_toggle_effect(pool: Mapping[str, Any], only_ids: set[str] | None = None) -> dict[str, Any] | None:
    """"deliver normaliser: off" (exact offline -- deliver the pre-normaliser last
    Solver state) vs as-flown. Single-sample-arm pools only. ``only_ids`` restricts
    to a subset (the two-fold cross-fit)."""

    if pool["kind"] != "single-sample-arm":
        return None
    ids = sorted(pool["rows"] if only_ids is None else (set(pool["rows"]) & only_ids))
    d_ok = {s: (1.0 if pool["rows"][s]["d_ok"] else 0.0) for s in ids}
    s_last_ok = {s: (1.0 if pool["rows"][s]["s_last_ok"] else 0.0) for s in ids}
    intent = bootstrap_delta_pct(ids, d_ok, s_last_ok)
    return {
        "policy_value": "off", "definition": "pre_normaliser_last_solver_state (exact offline replay)",
        "intent_delta_pp": intent,
        "slu_proxy_delta_pp": None,
        "slu_proxy_caveat": "not computed: the pre-normaliser entity set is not separately tracked",
    }


# ---------------------------------------------------------------------------
# catalog assembly


def pool_headline(pool: Mapping[str, Any]) -> dict[str, Any]:
    ids = sorted(pool["rows"])
    n = len(ids)
    return {
        "label": pool["label"], "run_id": pool["run_id"], "kind": pool["kind"], "use": pool["use"],
        "rows": n,
        "d_ok": sum(1 for s in ids if pool["rows"][s]["d_ok"]),
        "s1_ok": sum(1 for s in ids if pool["rows"][s]["s1_ok"]),
        "reviewer_visited": sum(1 for s in ids if pool["rows"][s]["reviewer_visited"]),
        "revised": sum(1 for s in ids if pool["rows"][s]["revised"]),
        "normaliser_changed": sum(1 for s in ids if pool["rows"][s]["normaliser_changed"]),
        "items": len(pool["items"]),
    }


def build_credit_table(
    pools: list[dict[str, Any]], pairs: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """The full credit table over every pool passed in (already filtered to the
    tuning role by the CLI), plus an explicit list of ``(right, left)`` pool-label
    pairs to contrast with :func:`pool_pair_delta` (``right`` minus ``left`` --
    e.g. ``("var1-ex-k30", "var1-planr")``). Deterministic given the same pools,
    pairs and default seed."""

    by_label = {pool["label"]: pool for pool in pools}
    per_pool = {}
    for pool in sorted(pools, key=lambda p: p["label"]):
        entry: dict[str, Any] = {
            "headline": pool_headline(pool),
            "perception_rank_conversion": perception_rank_conversion(pool),
            "block_position_conversion": block_position_conversion(pool),
            "provenance": pool["provenance"],
        }
        reviewer = reviewer_toggle_effect(pool)
        if reviewer is not None:
            entry["reviewer_toggle"] = reviewer
        normaliser = normaliser_toggle_effect(pool)
        if normaliser is not None:
            entry["normaliser_toggle"] = normaliser
        entry["relisten_reach"] = relisten_reach_table(pool)
        per_pool[pool["label"]] = entry
    pair_deltas = {}
    for right_label, left_label in sorted(pairs or []):
        if right_label not in by_label or left_label not in by_label:
            raise CreditError(f"pool_pair_delta: unknown pool label in pair {(right_label, left_label)!r}")
        pair_deltas[f"{right_label}_vs_{left_label}"] = pool_pair_delta(by_label[right_label], by_label[left_label])
    document = {
        "schema": "saea-sealed-credit-table-v1",
        "bootstrap": {
            "primitive": "analysis.bootstrap.paired_cluster_bootstrap",
            "seed": DEFAULT_SEED, "n_replicates": DEFAULT_N_REPLICATES, "ci_level": DEFAULT_CI_LEVEL,
        },
        "pools": per_pool,
        "pool_pairs": pair_deltas,
    }
    return finalize(document)


def finalize(document: dict[str, Any]) -> dict[str, Any]:
    """Attach ``table_sha256`` (the hash of the document without that field)."""

    text = json.dumps(document, indent=2, sort_keys=True)
    document = dict(document)
    document["table_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return document


__all__ = [
    "CreditError", "bootstrap_rate", "bootstrap_delta_pct", "conversion_table",
    "block_position_bucket", "perception_rank_conversion", "block_position_conversion",
    "reviewer_toggle_effect", "normaliser_toggle_effect", "pool_pair_delta", "relisten_reach_table",
    "pool_headline", "build_credit_table", "finalize",
]
