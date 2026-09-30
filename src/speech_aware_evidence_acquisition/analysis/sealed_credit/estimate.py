"""The per-candidate predicted-effect estimator (design spec task 5).

Formula per conversion-source kind (design spec section 2c's own formula,
specialised per source):

* ``pool_pair_delta`` -- the candidate value's own deliberate-variant pool
  (e.g. VAR-1 EX-K30) minus its flown comparator pool (e.g. VAR-1 PLANR), a
  PAIRED whole-cluster-bootstrap contrast on their shared rows
  (``credit.pool_pair_delta``): ``predicted_pp = mean(b_hit) - mean(a_hit)``
  over the shared roster, both for intent (``d_ok``) and for the SLU side
  (mean per-row official ``slu_f1_f1``).
* ``cited`` -- a number read directly off an already-sealed JSON artefact this
  run does not re-derive (e.g. the W-SV-1 same-flight column read's own
  ``delta_pp`` fields), or, when no artefact is named, a literal number carried
  in the policy-space document itself (the RANKVIS/CONV/W4 probes' own
  published deltas, section 2c). Every cited number keeps the source path and,
  when read from a file, that file's own sha256.
* ``credit_table_perception_rank`` / ``credit_table_block_position`` -- the
  design spec's own class-reweighting formula: ``predicted_pp = moved_rows *
  (rate(to_bucket) - rate(from_bucket)) / n``, rates and ``n`` read from the
  named pool's own :func:`credit.perception_rank_conversion` /
  :func:`credit.block_position_conversion` table; ``moved_rows`` is either
  measured in this run's own pools or cited from the design spec's own text
  (e.g. the P-SV-2 ceiling, "about 6 rows") -- every cited ``moved_rows``
  carries that citation in the output.
* ``credit_table_reviewer_toggle`` / ``credit_table_normaliser_toggle`` --
  ``credit.reviewer_toggle_effect`` / ``credit.normaliser_toggle_effect``'s own
  exact-offline replay delta on the named pool.
* ``credit_table_relisten_reach`` / ``unobserved`` / ``excluded`` -- no
  conversion rate is sealed yet; ``predicted_intent_pp = predicted_slu_pp = 0.0``
  with ``unobserved: true`` (design spec section 2c: "Knob values with no
  sealed conversion source enter with an expected gain of 0.0 and a flag
  ``unobserved``").

Two-fold cross-fit (design spec task 5; the fold split is item D3's own,
reused verbatim from ``scripts/analysis/slurp_reviewer_credit_table.py``'s
``fold_of`` -- a sample id's UTTERANCE hashed mod 2): every ``pool_pair_delta``
and ``credit_table_*`` estimate additionally reports its value restricted to
fold 0 and to fold 1 of the pool(s) it reads, so a downstream reader can see
whether the pooled point estimate is carried by one half of the roster. A
``cited`` estimate cannot be cross-fit (it is an external, already-pooled
artefact) and says so.

Composition (design spec section 2c): a composed policy assigns each row to
at most one repairing node by FLIGHT_ORDER (Perception seed, then Solver
supply, then the review loop, then post-accept/relisten, then delivery);
:func:`compose` sums single-knob estimates only across knobs whose ``node``
values are pairwise distinct, refusing two knobs on the same node (double
counting one row's repair). Run 1's own search (owner ruling Q4) is restricted
to single-knob candidates -- one node changed per candidate -- so
:func:`compose` is exercised by the unit tests and available for a future run,
not used by run 1's own candidate list.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from speech_aware_evidence_acquisition.analysis.sealed_credit import credit

FLIGHT_ORDER = ("perception_seed", "solver_supply", "solver_supply_candidates", "review_loop", "post_accept", "delivery")


class EstimateError(RuntimeError):
    pass


def _import_reviewer_credit_table(repo_root: Path):
    analysis_dir = repo_root / "scripts" / "analysis"
    if str(analysis_dir) not in sys.path:
        sys.path.insert(0, str(analysis_dir))
    spec = importlib.util.spec_from_file_location(
        "slurp_reviewer_credit_table", analysis_dir / "slurp_reviewer_credit_table.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["slurp_reviewer_credit_table"] = module  # see pools._import_path's own comment
    spec.loader.exec_module(module)
    return module


def fold_of(sample_id: str, repo_root: Path) -> int:
    """Item D3's own two-fold utterance split, reused (not reimplemented) from
    ``slurp_reviewer_credit_table.fold_of``."""

    return _import_reviewer_credit_table(repo_root).fold_of(sample_id)


def _get_path(document: Mapping[str, Any], dotted: str) -> Any:
    node: Any = document
    for part in dotted.split("."):
        if not isinstance(node, Mapping) or part not in node:
            raise EstimateError(f"cited source: path {dotted!r} not found (stopped at {part!r})")
        node = node[part]
    return node


def _digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unobserved(knob: Mapping[str, Any], value: Any, reason: str) -> dict[str, Any]:
    return {
        "knob_id": knob["id"], "node": knob["node"], "value": value, "flown_value": knob["flown_value"],
        "predicted_intent_pp": 0.0, "predicted_slu_pp": 0.0,
        "fold_intent_pp": None, "fold_slu_pp": None,
        "unobserved": True, "evidence": {"reason": reason}, "caveats": [reason],
    }


def _from_cited(knob: Mapping[str, Any], value: Any, source: Mapping[str, Any], data_root: Path) -> dict[str, Any]:
    caveats = list(source.get("caveats", []))
    read_json = source.get("read_json")
    if read_json is not None:
        path = data_root / read_json["path"]
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise EstimateError(f"cited source {read_json['path']!r}: cannot read: {error}") from error
        # Per metric: a field read off the sealed JSON or, when the artefact carries no such
        # field (a deterministic entity edit changes no intent by construction; a composite whose
        # SLU side is a counterfactual stated elsewhere), the literal ``intent_delta_pp`` /
        # ``slu_delta_pp`` the source states. A literal half is recorded in ``evidence``
        # (``literal_metrics``); an all-field source keeps run 1's evidence shape byte for byte.
        literal_metrics = []
        if "intent_field" in read_json:
            intent_pp = float(_get_path(document, read_json["intent_field"]))
        elif source.get("intent_delta_pp") is not None:
            intent_pp = float(source["intent_delta_pp"])
            literal_metrics.append("intent")
        else:
            raise EstimateError(
                f"cited source {read_json['path']!r}: names neither read_json.intent_field nor intent_delta_pp"
            )
        intent_ci = _get_path(document, read_json["intent_ci_field"]) if "intent_ci_field" in read_json else None
        if "slu_field" in read_json:
            slu_pp = float(_get_path(document, read_json["slu_field"]))
        elif source.get("slu_delta_pp") is not None:
            slu_pp = float(source["slu_delta_pp"])
            literal_metrics.append("slu")
        else:
            slu_pp = None
        slu_ci = _get_path(document, read_json["slu_ci_field"]) if "slu_ci_field" in read_json else None
        evidence = {
            "type": "cited_json", "path": read_json["path"], "sha256": _digest_file(path),
            "intent_field": read_json.get("intent_field"), "slu_field": read_json.get("slu_field"),
            "intent_ci95": intent_ci, "slu_ci95": slu_ci,
        }
        if literal_metrics:
            evidence["literal_metrics"] = literal_metrics
            evidence["literal_source"] = source.get("source")
            if intent_ci is None and source.get("intent_ci95") is not None:
                evidence["intent_ci95"] = source["intent_ci95"]
            if slu_ci is None and source.get("slu_ci95") is not None:
                evidence["slu_ci95"] = source["slu_ci95"]
    else:
        intent_pp = float(source["intent_delta_pp"])
        slu_pp = float(source["slu_delta_pp"]) if source.get("slu_delta_pp") is not None else None
        evidence = {
            "type": "cited_literal", "source": source.get("source"),
            "intent_ci95": source.get("intent_ci95"), "slu_ci95": source.get("slu_ci95"),
        }
    return {
        "knob_id": knob["id"], "node": knob["node"], "value": value, "flown_value": knob["flown_value"],
        "predicted_intent_pp": round(intent_pp, 4),
        "predicted_slu_pp": round(slu_pp, 4) if slu_pp is not None else None,
        "fold_intent_pp": None, "fold_slu_pp": None,
        "unobserved": False, "evidence": evidence,
        "caveats": caveats + ["cited: an already-pooled external read, not cross-fit by this run"],
    }


def _from_pool_pair(
    knob: Mapping[str, Any], value: Any, source: Mapping[str, Any],
    pools_by_label: Mapping[str, Any], repo_root: Path,
) -> dict[str, Any]:
    right_label, left_label = source["pools"]
    if right_label not in pools_by_label or left_label not in pools_by_label:
        raise EstimateError(f"knob {knob['id']!r}: pool_pair_delta names an unloaded pool in {source['pools']!r}")
    pool_b, pool_a = pools_by_label[right_label], pools_by_label[left_label]
    pooled = credit.pool_pair_delta(pool_b, pool_a)
    shared = set(pool_a["rows"]) & set(pool_b["rows"])
    folds = {0: set(), 1: set()}
    for sid in shared:
        folds[fold_of(sid, repo_root)].add(sid)
    fold_intent, fold_slu = [], []
    for f in (0, 1):
        if folds[f]:
            per_fold = credit.pool_pair_delta(pool_b, pool_a, only_ids=folds[f])
            fold_intent.append(per_fold["intent_delta_pp"]["delta_pp"])
            fold_slu.append(per_fold["slu_f1_mean_delta_pp"]["delta_pp"])
        else:
            fold_intent.append(None)
            fold_slu.append(None)
    return {
        "knob_id": knob["id"], "node": knob["node"], "value": value, "flown_value": knob["flown_value"],
        "predicted_intent_pp": pooled["intent_delta_pp"]["delta_pp"],
        "predicted_slu_pp": pooled["slu_f1_mean_delta_pp"]["delta_pp"],
        "fold_intent_pp": fold_intent, "fold_slu_pp": fold_slu,
        "unobserved": False, "evidence": pooled, "caveats": [pooled["slu_caveat"]],
    }


def _bucket_reweight(
    knob: Mapping[str, Any], value: Any, source: Mapping[str, Any],
    pools_by_label: Mapping[str, Any], repo_root: Path, table_fn,
) -> dict[str, Any]:
    label = source["primary_pool"]
    if label not in pools_by_label:
        raise EstimateError(f"knob {knob['id']!r}: names unloaded pool {label!r}")
    pool = pools_by_label[label]
    moved_rows = source.get("moved_rows")
    caveats = []
    if moved_rows is None:
        moved_rows = source["moved_rows_cited"]
        caveats.append(f"moved_rows cited, not measured: {source.get('moved_rows_source', 'design spec')}")

    def point(table: Mapping[str, Any]) -> float:
        n = sum(cell["n"] for cell in table.values())
        rate_to = table[source["to_bucket"]]["rate_pct"]
        rate_from = table[source["from_bucket"]]["rate_pct"]
        return moved_rows * (rate_to - rate_from) / n if n else 0.0

    pooled_table = table_fn(pool)
    predicted = point(pooled_table)
    ids = set(pool["rows"])
    folds = {0: set(), 1: set()}
    for sid in ids:
        folds[fold_of(sid, repo_root)].add(sid)
    fold_values = []
    for f in (0, 1):
        if folds[f]:
            fold_values.append(point(table_fn(pool, only_ids=folds[f])))
        else:
            fold_values.append(None)
    return {
        "knob_id": knob["id"], "node": knob["node"], "value": value, "flown_value": knob["flown_value"],
        "predicted_intent_pp": round(predicted, 4),
        "predicted_slu_pp": None,
        "fold_intent_pp": [round(v, 4) if v is not None else None for v in fold_values],
        "fold_slu_pp": None,
        "unobserved": False,
        "evidence": {
            "primary_pool": label, "from_bucket": source["from_bucket"], "to_bucket": source["to_bucket"],
            "moved_rows": moved_rows, "table": pooled_table,
        },
        "caveats": caveats + ["predicted_slu_pp not modelled for a bucket-reweight source"],
    }


def _from_toggle(
    knob: Mapping[str, Any], value: Any, source: Mapping[str, Any],
    pools_by_label: Mapping[str, Any], repo_root: Path, toggle: str,
) -> dict[str, Any]:
    label = source["pool"]
    if label not in pools_by_label:
        raise EstimateError(f"knob {knob['id']!r}: names unloaded pool {label!r}")
    pool = pools_by_label[label]
    fn = credit.reviewer_toggle_effect if toggle == "reviewer" else credit.normaliser_toggle_effect
    pooled = fn(pool)
    if pooled is None:
        raise EstimateError(f"knob {knob['id']!r}: pool {label!r} is not a single-sample-arm pool")
    ids = set(pool["rows"])
    folds = {0: set(), 1: set()}
    for sid in ids:
        folds[fold_of(sid, repo_root)].add(sid)
    fold_intent = []
    for f in (0, 1):
        if folds[f]:
            fold_intent.append(fn(pool, only_ids=folds[f])["intent_delta_pp"]["delta_pp"])
        else:
            fold_intent.append(None)
    slu_key = "slu_proxy_delta_pp"
    slu_pp = pooled[slu_key]["delta_pp"] if pooled.get(slu_key) else None
    return {
        "knob_id": knob["id"], "node": knob["node"], "value": value, "flown_value": knob["flown_value"],
        "predicted_intent_pp": pooled["intent_delta_pp"]["delta_pp"],
        "predicted_slu_pp": slu_pp,
        "fold_intent_pp": fold_intent, "fold_slu_pp": None,
        "unobserved": False, "evidence": pooled, "caveats": [pooled.get("slu_proxy_caveat", "")],
    }


def estimate_knob_value(
    knob: Mapping[str, Any], value_entry: Mapping[str, Any],
    pools_by_label: Mapping[str, Any], repo_root: Path, data_root: Path | None = None,
) -> dict[str, Any]:
    """One knob value's predicted effect. Never contacts a model, server or GPU:
    every number here is read from already-extracted pools or already-sealed
    JSON artefacts on disk. ``data_root`` (defaults to ``repo_root`` when a
    ``cited`` source is not used) is where a ``cited`` source's ``read_json.path``
    resolves -- sealed analysis outputs live under ``$SPEECHRL_DATA_DIR``, not the
    repository."""

    value = value_entry["value"]
    source = value_entry["conversion_source"]
    stype = source["type"]
    if stype == "cited":
        result = _from_cited(knob, value, source, data_root if data_root is not None else repo_root)
    elif stype in ("unobserved", "excluded", "credit_table_relisten_reach"):
        result = _unobserved(knob, value, source.get("reason", f"{stype}: no sealed conversion rate"))
    elif stype == "pool_pair_delta":
        result = _from_pool_pair(knob, value, source, pools_by_label, repo_root)
    elif stype == "credit_table_perception_rank":
        result = _bucket_reweight(knob, value, source, pools_by_label, repo_root, credit.perception_rank_conversion)
    elif stype == "credit_table_block_position":
        result = _bucket_reweight(knob, value, source, pools_by_label, repo_root, credit.block_position_conversion)
    elif stype == "credit_table_reviewer_toggle":
        result = _from_toggle(knob, value, source, pools_by_label, repo_root, "reviewer")
    elif stype == "credit_table_normaliser_toggle":
        result = _from_toggle(knob, value, source, pools_by_label, repo_root, "normaliser")
    else:
        raise EstimateError(f"knob {knob['id']!r}: unknown conversion_source.type {stype!r}")
    # Run 3: a declared line status travels with the estimate (absent -> key absent, so a
    # policy space without statuses yields byte-identical estimates to run 2).
    if "status" in value_entry:
        result["status"] = value_entry["status"]
        if value_entry.get("status_note"):
            result["status_note"] = value_entry["status_note"]
    return result


def estimate_all(
    policy_space: Mapping[str, Any], pools_by_label: Mapping[str, Any], repo_root: Path,
    data_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Every non-excluded knob value's estimate, in a deterministic (knob id,
    value) order."""

    out = []
    for knob in sorted(policy_space["knobs"], key=lambda k: k["id"]):
        if knob["estimator"] == "excluded":
            continue
        for value_entry in sorted(knob["values"], key=lambda v: json.dumps(v["value"], sort_keys=True)):
            out.append(estimate_knob_value(knob, value_entry, pools_by_label, repo_root, data_root))
    return out


def compose(estimates: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum single-knob estimates whose ``node`` values are pairwise distinct
    (flight-order precedence: each row is repaired by at most one node). Refuses
    two estimates on the same node -- that would double-count a row's repair."""

    nodes = [e["node"] for e in estimates]
    if len(set(nodes)) != len(nodes):
        raise EstimateError(f"compose: two knob values target the same node in {nodes!r}")
    ordered = sorted(estimates, key=lambda e: FLIGHT_ORDER.index(e["node"]) if e["node"] in FLIGHT_ORDER else 99)
    intent = sum(e["predicted_intent_pp"] for e in ordered)
    slu_values = [e["predicted_slu_pp"] for e in ordered if e["predicted_slu_pp"] is not None]
    return {
        "knobs": [{"knob_id": e["knob_id"], "value": e["value"]} for e in ordered],
        "predicted_intent_pp": round(intent, 4),
        "predicted_slu_pp": round(sum(slu_values), 4) if slu_values else None,
        "unobserved": any(e["unobserved"] for e in ordered),
        "components": ordered,
    }


__all__ = [
    "EstimateError", "FLIGHT_ORDER", "fold_of",
    "estimate_knob_value", "estimate_all", "compose",
]
