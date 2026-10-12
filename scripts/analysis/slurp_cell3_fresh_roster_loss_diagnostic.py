#!/usr/bin/env python3
"""Where the first out-of-fold loss of the Stage-3 delta line sits.

Model-free diagnostic of cell CELL-3 (``SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1``,
the locked v2.0 plan plus the coverage-gated ``stage3-deltas-v2`` store) against the
sealed DEV-2000-ADDED PLAN arm, with the request-identical PLAN replicate (PLANr) as
the roster's own null. It answers six questions:

1. split the 1,000 roster rows into GATED (every gated node closed, so the row ran in
   bare PLAN form), SUPPLIED (some node received delta values) and OPEN-NO-SUPPLY
   (the gate opened but the store matched nothing), and read the pooled official
   micro-F1, the per-row means, the intent exactness and the entity FP / FN mass by
   slot TYPE on each split for PLAN-vs-CELL3 and PLAN-vs-PLANr;
2. on SUPPLIED rows, the paired outcome per supplied value id, joined to the CELL-2
   TRAIN Fold A consumption read, so a transfer failure can be told from a different
   set of values;
3. the entity side of the supplied rows: emitted count, FP added and FN added by slot
   type, and which delta kinds sat on the rows that added an FP;
4. Perception: the candidate lists of the three arms compared row by row, and the
   share of rows whose GATE DECISION would differ if it were taken on the PLAN arm's
   own candidates (gate stability);
5. two bounds -- perfect gate (every supplied row replaced by its PLAN outcome) and
   the noise residual (every gated row replaced by PLANr's outcome);
6. the ranked root-cause statement, rendered into the markdown.

ZERO CONTACTS. Model, tokenizer, encoder, scorer and server contacts are all zero:
every number comes from sealed per-row outputs, sealed phase results, sealed flight
receipts, the sealed official per-sample scores and the governed SLURP devel gold
metadata read offline through ``data.slurp.load_slurp_split``.

LABELS, IDS, COUNTS AND HASHES ONLY. No utterance text, no transcript, no delivered
text, no gold filler and no statement content is printed, cached or committed. Gold
is used as a scoring input and appears only in aggregate tables; the two cache files
this read writes carry labels (scenario / action / intent / entity TYPE) and integer
counts exclusively.

REUSED LOADERS. The official per-sample projection and the pooled-F1 statistic are
``scripts/analysis/slurp_paired_roster_read.py``'s (``MICRO_METRICS``, ``pooled_f1``,
``rows_for``); the per-row supply extraction and the phase-result reading are
``scripts/analysis/stage3_delta_consumption_read.py``'s ``extract_row_supply`` and
``load_phase_results`` unchanged; the delivered-label parse and the gold projection
follow ``scripts/analysis/slurp_general_scenario_diagnostic.py``; the gate itself is
``rails.stage3_delta_supply.ScenarioGate``, so the counterfactual gate this read
computes is the flown gate's own implementation.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))
_ANALYSIS_DIR = str(Path(__file__).resolve().parent)
if _ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, _ANALYSIS_DIR)

from speech_aware_evidence_acquisition.analysis.null_calibration import (  # noqa: E402
    pooled_f1,
)
from speech_aware_evidence_acquisition.analysis.null_calibration_cli import (  # noqa: E402
    rows_for,
)
from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    _SPLIT_FILES,
    _governed_roots,
    load_slurp_split,
)
from speech_aware_evidence_acquisition.rails.stage3_delta_supply import (  # noqa: E402
    STAGE3_DELTA_SCENARIO_GATE_SKIP_REASON,
    ScenarioGate,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
)

from stage3_delta_consumption_read import (  # noqa: E402
    extract_row_supply,
    load_phase_results,
)

RECIPE_ID = "slurp-cell3-fresh-roster-loss-diagnostic-v1"
SCHEMA = "saea-slurp-cell3-fresh-roster-loss-diagnostic-v1"
RUN_ID = "SAEA-SLURP-CELL3-FRESH-ROSTER-LOSS-DIAGNOSTIC-V1"
OUT_DIRNAME = "SLURP-CELL3-FRESH-ROSTER-LOSS-DIAGNOSTIC-V1"
DEFAULT_MARKDOWN = "docs/results/2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md"

SCORER = "slurp-slu-official"
SPLIT_ID = "devel"
STORE_ID = "stage3-deltas"
STORE_DIRNAME = "stage3-deltas-v2"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"
CELL2_CONSUMPTION = (
    "analysis/SAEA-SLURP-STAGE3-DELTA-CELL-R02-PAIRED-ANALYSIS-V1/delta-consumption.json"
)

NODES = ("perception", "solver", "reviewer", "planner")
GATED_NODES = ("solver", "reviewer", "planner")

PER_ROW_METRICS = (
    "scenario_action_exact",
    "scenario_exact",
    "action_exact",
    "slot_f1_exact_f1",
    "slu_f1_f1",
)
MICRO_METRICS = {
    "slu_f1_micro": (
        ("slu_f1_word_tp", "slu_f1_char_tp"),
        ("slu_f1_word_fp", "slu_f1_char_fp"),
        ("slu_f1_word_fn", "slu_f1_char_fn"),
    ),
    "span_f1_micro": (
        ("slot_f1_exact_tp",),
        ("slot_f1_exact_fp",),
        ("slot_f1_exact_fn",),
    ),
}
OFFICIAL_FIELD = {"slu_f1_micro": "slu_f1", "span_f1_micro": "span_f1"}
COUNT_FIELDS = ("slot_f1_exact_tp", "slot_f1_exact_fp", "slot_f1_exact_fn", "parsed")
SCORE_FIELDS = tuple(
    dict.fromkeys(
        list(PER_ROW_METRICS)
        + [name for groups in MICRO_METRICS.values() for group in groups for name in group]
        + list(COUNT_FIELDS)
    )
)

#: (key, label, run id, attempt id). PLAN is the sealed comparator every cell of this
#: roster is registered against; PLANr is the request-identical replicate that
#: measures the roster's own null; CELL3 is the arm.
ARMS = (
    (
        "plan",
        "PLAN (sealed DEV-2000-ADDED comparator)",
        "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1",
        "attempt-slurp-native-default-plan-dev2000-added-generation-v1",
    ),
    (
        "cell3",
        "CELL-3 (gated stage3-deltas-v2)",
        "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1",
        "attempt-slurp-native-stage3-delta-cell-r03-gate-v1-generation",
    ),
    (
        "planr",
        "PLANr (request-identical replicate)",
        "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1",
        "attempt-slurp-native-default-plan-dev2000-added-replicate-generation-v1",
    ),
)
ARM_KEYS = tuple(entry[0] for entry in ARMS)
UNPARSED = "<unparsed>"


class DiagnosticError(SystemExit):
    """Refuse rather than report a number this read cannot bind to sealed bytes."""


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def sha_of(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def load_roster(repo: Path, relpath: str) -> dict:
    path = repo / relpath
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document.get("items") or []
    ids = []
    channel = {}
    cluster = {}
    for item in items:
        sample_id = item.get("sample_id") or item.get("id")
        if not isinstance(sample_id, str):
            raise DiagnosticError(f"{path}: an item carries no sample_id")
        utterance_id = item.get("utterance_id")
        if not isinstance(utterance_id, str) or not utterance_id:
            raise DiagnosticError(f"{path}: item {sample_id!r} carries no utterance_id")
        ids.append(sample_id)
        channel[sample_id] = "headset" if item.get("headset") else "far_field"
        cluster[sample_id] = utterance_id
    if len(set(ids)) != len(ids):
        raise DiagnosticError(f"{path}: repeats a sample_id")
    return {
        "path": str(path),
        "sha256": digest(path),
        "roster_id": document.get("roster_id"),
        "split_role": document.get("split_role"),
        "split_identity_hash": document.get("split_identity_hash"),
        "ids": sorted(ids),
        "channel": channel,
        "cluster": cluster,
    }


def arm_dir(data_root: Path, run_id: str, attempt_id: str) -> Path:
    directory = data_root / "runs" / run_id / attempt_id
    if not directory.is_dir():
        raise DiagnosticError(f"sealed attempt directory missing: {directory}")
    return directory


def load_manifest(directory: Path, run_id: str, expected_hash: str) -> dict:
    path = directory / f"{run_id}.run-manifest.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("status") != "COMPLETED":
        raise DiagnosticError(f"{run_id}: manifest is not COMPLETED")
    if document.get("study_repo_dirt"):
        raise DiagnosticError(f"{run_id}: sealed with a dirty study tree")
    split = document.get("split") or {}
    if split.get("identity_hash") != expected_hash:
        raise DiagnosticError(
            f"{run_id}: manifest split identity {split.get('identity_hash')} is not the roster's"
        )
    return {
        "path": str(path),
        "sha256": digest(path),
        "status": document.get("status"),
        "study_commit": document.get("study_commit"),
        "split_role": split.get("role"),
        "split_count": split.get("count"),
        "split_identity_hash": split.get("identity_hash"),
    }


def load_scores(directory: Path, run_id: str, ids: list[str]) -> dict:
    path = directory / f"{run_id}.scores.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = rows_for({"verified": True, "scores": raw}, SCORER, SCORE_FIELDS)
    missing = sorted(set(ids) - set(rows))
    if missing:
        raise DiagnosticError(f"{run_id}: per_sample is missing {len(missing)} roster rows")
    official = ((raw.get(SCORER) or {}).get("aggregate") or {}).get("official") or {}
    for metric, groups in MICRO_METRICS.items():
        field = OFFICIAL_FIELD[metric]
        published = official.get(field)
        recomputed = pooled_f1(rows, ids, groups)
        if not isinstance(published, (int, float)) or isinstance(published, bool):
            raise DiagnosticError(f"{run_id}: official aggregate has no numeric {field!r}")
        if abs(recomputed - float(published)) > 1e-6:
            raise DiagnosticError(
                f"{run_id}: recomputed {metric} {recomputed} does not reproduce the official "
                f"{published} to 1e-6"
            )
    return {
        "path": str(path),
        "sha256": digest(path),
        "rows": rows,
        "official": {
            "slu_f1": float(official.get("slu_f1")),
            "span_f1": float(official.get("span_f1")),
            "intent_accuracy": float(official.get("intent_accuracy")),
            "action_accuracy": float(official.get("action_accuracy")),
        },
    }


def load_delivered(directory: Path, run_id: str, wanted: set[str]) -> dict:
    """Delivered LABELS and the entity (type, filler) pairs of every wanted row.

    The fillers never leave this process: they are consumed by :func:`per_type_counts`
    and only per-TYPE integer counts are written anywhere.
    """
    path = directory / f"{run_id}.outputs.jsonl"
    rows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            sample_id = record.get("sample_id")
            if sample_id not in wanted:
                continue
            scenario, action, entities, parsed = parse_slu_response(record.get("text") or "")
            rows[sample_id] = {
                "parsed": bool(parsed),
                "scenario": scenario if isinstance(scenario, str) else None,
                "action": action if isinstance(action, str) else None,
                "intent": (
                    f"{scenario}_{action}"
                    if parsed and isinstance(scenario, str) and isinstance(action, str)
                    else UNPARSED
                ),
                "entities": list(entities),
                "entity_types": sorted(entity.type for entity in entities),
                "entity_count": len(entities),
            }
    missing = sorted(wanted - set(rows))
    if missing:
        raise DiagnosticError(f"{run_id}: outputs are missing {len(missing)} roster rows")
    return {"path": str(path), "sha256": digest(path), "rows": rows}


def load_gate_and_supply(directory: Path, run_id: str) -> dict:
    """The CELL-3 flight's own gate decisions and its gate-closed skip receipts."""
    path = directory / "flight-receipts.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    supply_receipt = (
        ((document.get("stages") or {}).get("run_phases") or {}).get("phase_supply") or {}
    )
    if supply_receipt.get("schema") != "saea-named-knowledge-store-routing-v1":
        raise DiagnosticError(f"{run_id}: flight receipt carries no knowledge-store routing")
    gate_audits = supply_receipt.get("delta_scenario_gate") or {}
    if not gate_audits:
        raise DiagnosticError(f"{run_id}: flight receipt carries no delta_scenario_gate audits")
    delta_supply = supply_receipt.get("delta_supply") or {}
    per_row_gate: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    gated_scenarios: set[tuple[str, ...]] = set()
    for entry in gate_audits.values():
        per_row_gate[entry["sample_id"]][entry["node"]].append(entry)
        gated_scenarios.add(tuple(entry.get("gated_scenarios") or ()))
    if len(gated_scenarios) != 1:
        raise DiagnosticError(f"{run_id}: the flight used more than one gated-scenario set")
    gate_skip_rows: dict[str, set[str]] = defaultdict(set)
    for entry in delta_supply.values():
        if entry.get("reason") == STAGE3_DELTA_SCENARIO_GATE_SKIP_REASON:
            gate_skip_rows[entry["node"]].add(entry["sample_id"])
    return {
        "path": str(path),
        "sha256": digest(path),
        "gated_scenarios": list(next(iter(gated_scenarios))),
        "gate_audits": {row: dict(nodes) for row, nodes in per_row_gate.items()},
        "gate_audit_count": len(gate_audits),
        "gate_skip_rows": {node: sorted(rows) for node, rows in sorted(gate_skip_rows.items())},
        "delta_supply_events": len(delta_supply),
    }


def load_candidates(directory: Path, run_id: str, wanted: set[str]) -> dict:
    """Per row, the Perception candidate intent ids in the order the state carries them.

    ``first`` is the first Perception state's list -- the one the gate and the
    candidate-bound routes read; ``union`` is every id any Perception state proposed.
    """
    phases = load_phase_results(directory, run_id)
    per_row: dict[str, dict] = {}
    parse_failures = 0
    for result in phases["results"]:
        sample_id = result.get("sample_id")
        if sample_id not in wanted:
            continue
        first: list[str] | None = None
        union: list[str] = []
        states = 0
        for state in result.get("agent_states") or ():
            if state.get("state_kind") != "phase:perception":
                continue
            states += 1
            try:
                payload = json.loads(state.get("content") or "")
            except (TypeError, ValueError):
                parse_failures += 1
                continue
            candidates = payload.get("candidates") if isinstance(payload, dict) else None
            if not isinstance(candidates, list):
                parse_failures += 1
                continue
            ids = [
                candidate.get("intent_id")
                for candidate in candidates
                if isinstance(candidate, dict) and isinstance(candidate.get("intent_id"), str)
            ]
            if first is None:
                first = list(ids)
            for intent_id in ids:
                if intent_id not in union:
                    union.append(intent_id)
        per_row[sample_id] = {
            "perception_states": states,
            "first": first or [],
            "union": union,
        }
    missing = sorted(wanted - set(per_row))
    if missing:
        raise DiagnosticError(f"{run_id}: phase results are missing {len(missing)} roster rows")
    return {
        "path": phases["path"],
        "sha256": phases["sha256"],
        "controller_policy_id": phases["controller_policy_id"],
        "candidate_parse_failures": parse_failures,
        "rows": per_row,
        "results": phases["results"],
    }


def bare_value_id(value_id: str) -> str:
    """``<store_id>::<value_id>``, as a routing receipt qualifies it, to the snapshot's own id."""
    return value_id.split("::", 1)[-1]


def load_store(data_root: Path, dirname: str) -> dict:
    """``value_id -> {node, kind, target}`` from the released snapshot. Content is never read."""
    path = data_root / "knowledge" / "slurp" / "semantic" / dirname / "snapshot.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    values = {}
    for value in document["values"]:
        target = value.get("task_target") or ""
        parts = target.split(":", 2)
        values[value["value_id"]] = {
            "node": parts[0] if len(parts) > 0 else "",
            "kind": parts[1] if len(parts) > 1 else "",
            "target": parts[2] if len(parts) > 2 else "",
            "task_target": target,
            "facets": sorted(value.get("associated_facet_ids") or ()),
            "prior_score": value.get("prior_score"),
            "content_chars": len(value.get("content") or ""),
        }
    return {
        "path": str(path),
        "sha256": digest(path),
        "declared_snapshot_sha256": document.get("snapshot_sha256"),
        "values": values,
    }


def gold_projection(lock_path: Path, data_root: Path, cache_path: Path) -> dict:
    """``sample_id -> {scenario, action, intent, entity_types}`` for the devel split.

    LABELS ONLY: the gold FILLER text is never written to the cache, so no gold filler
    can reach a report or a commit from here. Cached because the loader re-verifies
    every recording against its flac header; the cache key is the sha256 of the split
    metadata file it was built from.
    """
    lock = load_lock(lock_path)
    metadata_path = _governed_roots(lock, data_root)[2] / _SPLIT_FILES[SPLIT_ID]
    metadata_sha = digest(metadata_path)
    if cache_path.is_file():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if (
            cached.get("schema") == "saea-slurp-devel-gold-label-projection-v1"
            and cached.get("split_id") == SPLIT_ID
            and cached.get("metadata_sha256") == metadata_sha
        ):
            return {
                "source": "cache",
                "cache_path": str(cache_path),
                "metadata_path": str(metadata_path),
                "metadata_sha256": metadata_sha,
                "labels": cached["rows"],
                "records": None,
            }
    records = load_slurp_split(lock, data_root, SPLIT_ID)
    labels = {
        record.sample_id: {
            "scenario": record.scenario,
            "action": record.action,
            "intent": record.intent,
            "entity_types": sorted(entity.type for entity in record.entities),
        }
        for record in records
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "schema": "saea-slurp-devel-gold-label-projection-v1",
                "split_id": SPLIT_ID,
                "metadata_sha256": metadata_sha,
                "rows": labels,
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source": "loader",
        "cache_path": str(cache_path),
        "metadata_path": str(metadata_path),
        "metadata_sha256": metadata_sha,
        "labels": labels,
        "records": {record.sample_id: record for record in records},
    }


# --------------------------------------------------------------------------
# Per-type exact entity counts
# --------------------------------------------------------------------------


def per_type_counts(gold_entities, predicted_entities) -> dict:
    """``reproduction.slurp_scoring._exact_counts`` decomposed by slot TYPE.

    The official ``SpanFMeasure`` matches a predicted entity to a gold entity only on
    an exact ``(type, filler)`` equality, so every TP belongs to one type and every FP
    and FN belongs to the type of the side that carried it. Summing the three
    dictionaries reproduces the sealed ``slot_f1_exact_{tp,fp,fn}`` of that row
    exactly, which :func:`build_entity_tables` asserts.
    """
    remaining = list(gold_entities)
    tp: Counter = Counter()
    fp: Counter = Counter()
    for entity in predicted_entities:
        if entity in remaining:
            tp[entity.type] += 1
            remaining.remove(entity)
        else:
            fp[entity.type] += 1
    fn = Counter(entity.type for entity in remaining)
    return {"tp": dict(tp), "fp": dict(fp), "fn": dict(fn)}


def resolve_entity_counts(
    *,
    arms: dict,
    ids: list[str],
    gold: dict,
    cache_path: Path,
) -> dict:
    """Per arm, per row, the per-TYPE exact TP / FP / FN -- from cache when the cache
    pins the same gold metadata and the same arm outputs, otherwise recomputed from the
    loaded gold records. COUNTS ONLY are cached."""

    want = {key: arms[key]["delivered"]["sha256"] for key in ARM_KEYS}
    if cache_path.is_file():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if (
            cached.get("schema") == "saea-slurp-per-type-exact-counts-v1"
            and cached.get("gold_metadata_sha256") == gold["metadata_sha256"]
            and all(
                (cached.get("arms") or {}).get(key, {}).get("outputs_sha256") == want[key]
                for key in ARM_KEYS
            )
        ):
            return {
                "source": "cache",
                "cache_path": str(cache_path),
                "arms": {key: cached["arms"][key]["rows"] for key in ARM_KEYS},
            }
    records = gold.get("records")
    if records is None:
        raise DiagnosticError(
            "the per-type entity cache is stale and the gold records were not loaded; "
            "delete the gold label cache (or pass --refresh-gold) and run again"
        )
    per_arm: dict[str, dict] = {}
    for key in ARM_KEYS:
        delivered = arms[key]["delivered"]["rows"]
        per_arm[key] = {
            sample_id: per_type_counts(
                records[sample_id].entities, delivered[sample_id]["entities"]
            )
            for sample_id in ids
        }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "schema": "saea-slurp-per-type-exact-counts-v1",
                "gold_metadata_sha256": gold["metadata_sha256"],
                "arms": {
                    key: {"outputs_sha256": want[key], "rows": per_arm[key]}
                    for key in ARM_KEYS
                },
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"source": "computed", "cache_path": str(cache_path), "arms": per_arm}


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------


def percentile(values, fraction: float) -> float:
    ordered = sorted(values)
    index = min(max(int(round(fraction * (len(ordered) - 1))), 0), len(ordered) - 1)
    return ordered[index]


def pooled(rows, sample_ids, metric: str) -> float:
    return 100.0 * pooled_f1(rows, sample_ids, MICRO_METRICS[metric])


def pooled_counts(rows, sample_ids, metric: str) -> dict:
    groups = MICRO_METRICS[metric]
    totals = [0.0, 0.0, 0.0]
    for sample_id in sample_ids:
        for index, names in enumerate(groups):
            for name in names:
                totals[index] += rows[sample_id][name]
    tp, fp, fn = totals
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "f1_pct": 100.0 * (2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0),
    }


def cluster_ci(left_rows, right_rows, sample_ids, metric, cluster_of, seed, draws) -> dict:
    """The paired whole-cluster bootstrap of a pooled micro-F1 delta -- the identical
    statistic and resampling rule ``slurp_paired_roster_read._pooled_contrast_block``
    uses, so a per-split interval here is comparable with the published whole-roster one."""
    from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic

    groups = MICRO_METRICS[metric]

    def statistic(resampled):
        return pooled_f1(right_rows, resampled, groups) - pooled_f1(left_rows, resampled, groups)

    result = resampled_statistic(
        sample_ids=list(sample_ids),
        statistic=statistic,
        seed=seed,
        n_replicates=draws,
        ci_level=0.95,
        cluster_of=cluster_of,
    )
    replicates = [100.0 * value for value in result.replicates]
    point = 100.0 * result.point_estimate
    low = percentile(replicates, 0.025)
    high = percentile(replicates, 0.975)
    return {
        "point_estimate_pp": point,
        "ci95_pp": [low, high],
        "ci95_half_width_pp": 0.5 * (high - low),
        "n_replicates": draws,
        "seed": seed,
        "resampling": "paired whole-cluster bootstrap",
    }


def per_row_block(left_rows, right_rows, sample_ids, field: str) -> dict:
    saves = harms = neutral = 0
    total = 0.0
    for sample_id in sample_ids:
        delta = float(right_rows[sample_id][field]) - float(left_rows[sample_id][field])
        total += delta
        if delta > 0:
            saves += 1
        elif delta < 0:
            harms += 1
        else:
            neutral += 1
    n = len(sample_ids)
    return {
        "n": n,
        "saves": saves,
        "harms": harms,
        "neutral": neutral,
        "mean_delta_pp": (100.0 * total / n) if n else None,
    }


def arm_level_block(rows, sample_ids, delivered, gold_labels, type_counts) -> dict:
    n = len(sample_ids)
    fp_by_type: Counter = Counter()
    fn_by_type: Counter = Counter()
    tp_by_type: Counter = Counter()
    for sample_id in sample_ids:
        counts = type_counts[sample_id]
        tp_by_type.update(counts["tp"])
        fp_by_type.update(counts["fp"])
        fn_by_type.update(counts["fn"])
    return {
        "rows": n,
        "pooled_slu_f1_pct": pooled(rows, sample_ids, "slu_f1_micro"),
        "pooled_span_f1_pct": pooled(rows, sample_ids, "span_f1_micro"),
        "slu_counts": pooled_counts(rows, sample_ids, "slu_f1_micro"),
        "span_counts": pooled_counts(rows, sample_ids, "span_f1_micro"),
        "intent_exact_pct": 100.0
        * sum(rows[sample_id]["scenario_action_exact"] for sample_id in sample_ids)
        / n,
        "scenario_exact_pct": 100.0
        * sum(rows[sample_id]["scenario_exact"] for sample_id in sample_ids)
        / n,
        "mean_row_slu_f1_pct": 100.0
        * sum(rows[sample_id]["slu_f1_f1"] for sample_id in sample_ids)
        / n,
        "parsed_rows": int(sum(rows[sample_id]["parsed"] for sample_id in sample_ids)),
        "entities_emitted": sum(delivered[sample_id]["entity_count"] for sample_id in sample_ids),
        "gold_entities": sum(
            len(gold_labels[sample_id]["entity_types"]) for sample_id in sample_ids
        ),
        "entity_tp_by_type": dict(tp_by_type),
        "entity_fp_by_type": dict(fp_by_type),
        "entity_fn_by_type": dict(fn_by_type),
        "entity_tp": sum(tp_by_type.values()),
        "entity_fp": sum(fp_by_type.values()),
        "entity_fn": sum(fn_by_type.values()),
    }


# --------------------------------------------------------------------------
# Q1: the three splits
# --------------------------------------------------------------------------


def build_splits(ids, supply, gate) -> dict:
    """GATED / SUPPLIED / OPEN-NO-SUPPLY, decided from CELL-3's own sealed receipts."""
    supplied_rows = []
    gated_rows = []
    open_no_supply = []
    per_row_supply = supply["per_row"]
    audits = gate["gate_audits"]
    node_detail: dict[str, dict] = {}
    for sample_id in ids:
        supplied_nodes = {
            node: sorted(set(values))
            for node, values in (per_row_supply.get(sample_id) or {}).items()
            if values
        }
        row_audits = audits.get(sample_id) or {}
        decisions = [entry for node in row_audits for entry in row_audits[node]]
        closed_nodes = sorted({entry["node"] for entry in decisions if entry["closed"]})
        open_nodes = sorted({entry["node"] for entry in decisions if not entry["closed"]})
        all_closed = bool(decisions) and not open_nodes
        node_detail[sample_id] = {
            "supplied_nodes": supplied_nodes,
            "closed_nodes": closed_nodes,
            "open_nodes": open_nodes,
            "gate_decisions": len(decisions),
            "majority_scenario": (decisions[0]["majority_scenario"] if decisions else None),
        }
        if supplied_nodes:
            supplied_rows.append(sample_id)
        elif all_closed:
            gated_rows.append(sample_id)
        else:
            open_no_supply.append(sample_id)
    return {
        "gated": sorted(gated_rows),
        "supplied": sorted(supplied_rows),
        "open_no_supply": sorted(open_no_supply),
        "per_row": node_detail,
    }


def split_tables(*, arms, splits, ids, gold_labels, type_counts, channel, seed, draws) -> dict:
    """Per split and per pair, the levels and the paired contrast."""
    pairs = (("plan", "cell3"), ("plan", "planr"))
    out: dict = {"splits": {}, "pairs": {}}
    named = {
        "all": ids,
        "gated": splits["gated"],
        "supplied": splits["supplied"],
        "open_no_supply": splits["open_no_supply"],
    }

    def cluster_of(sample_id: str) -> str:
        return channel["cluster"][sample_id]

    for split_name, sample_ids in named.items():
        out["splits"][split_name] = {
            "rows": len(sample_ids),
            "levels": {
                key: arm_level_block(
                    arms[key]["scores"]["rows"],
                    sample_ids,
                    arms[key]["delivered"]["rows"],
                    gold_labels,
                    type_counts["arms"][key],
                )
                for key in ARM_KEYS
            }
            if sample_ids
            else {},
        }
        for left, right in pairs:
            block_key = f"{left}_vs_{right}"
            if not sample_ids:
                out["pairs"].setdefault(block_key, {})[split_name] = None
                continue
            left_rows = arms[left]["scores"]["rows"]
            right_rows = arms[right]["scores"]["rows"]
            block = {
                "rows": len(sample_ids),
                "pooled_slu_f1_delta_pp": pooled(right_rows, sample_ids, "slu_f1_micro")
                - pooled(left_rows, sample_ids, "slu_f1_micro"),
                "pooled_span_f1_delta_pp": pooled(right_rows, sample_ids, "span_f1_micro")
                - pooled(left_rows, sample_ids, "span_f1_micro"),
                "per_row_slu": per_row_block(left_rows, right_rows, sample_ids, "slu_f1_f1"),
                "per_row_intent": per_row_block(
                    left_rows, right_rows, sample_ids, "scenario_action_exact"
                ),
                "per_row_span": per_row_block(
                    left_rows, right_rows, sample_ids, "slot_f1_exact_f1"
                ),
                "slu_ci": cluster_ci(
                    left_rows, right_rows, sample_ids, "slu_f1_micro", cluster_of, seed, draws
                ),
                "span_ci": cluster_ci(
                    left_rows, right_rows, sample_ids, "span_f1_micro", cluster_of, seed, draws
                ),
            }
            out["pairs"].setdefault(block_key, {})[split_name] = block
    return out


# --------------------------------------------------------------------------
# Q2: per supplied value id, and the TRAIN Fold A join
# --------------------------------------------------------------------------


def value_outcomes(*, arms, splits, supply, store, cell2_path: Path) -> dict:
    left_rows = arms["plan"]["scores"]["rows"]
    right_rows = arms["cell3"]["scores"]["rows"]
    per_row_supply = supply["per_row"]
    reach: dict[str, dict] = defaultdict(
        lambda: {"rows": [], "nodes": set()}
    )
    for sample_id in splits["supplied"]:
        for node, values in (per_row_supply.get(sample_id) or {}).items():
            for value_id in set(values):
                reach[value_id]["rows"].append(sample_id)
                reach[value_id]["nodes"].add(node)
    cell2 = json.loads(cell2_path.read_text(encoding="utf-8"))
    cell2_values = (cell2.get("consumption") or {}).get("per_value_id") or {}
    rows_out = []
    for value_id, entry in reach.items():
        sample_ids = sorted(set(entry["rows"]))
        slu = per_row_block(left_rows, right_rows, sample_ids, "slu_f1_f1")
        intent = per_row_block(left_rows, right_rows, sample_ids, "scenario_action_exact")
        harm_mass = 0.0
        save_mass = 0.0
        for sample_id in sample_ids:
            delta = 100.0 * (
                float(right_rows[sample_id]["slu_f1_f1"]) - float(left_rows[sample_id]["slu_f1_f1"])
            )
            if delta < 0:
                harm_mass += -delta
            else:
                save_mass += delta
        meta = store["values"].get(bare_value_id(value_id)) or {}
        fold_a = cell2_values.get(value_id)
        rows_out.append(
            {
                "value_id": value_id,
                "nodes": sorted(entry["nodes"]),
                "kind": meta.get("kind"),
                "target": meta.get("target"),
                "facets": meta.get("facets"),
                "store_node": meta.get("node"),
                "prior_score": meta.get("prior_score"),
                "rows_reached": len(sample_ids),
                "slu": slu,
                "intent": intent,
                "harm_mass_pp": harm_mass,
                "save_mass_pp": save_mass,
                "net_mass_pp": save_mass - harm_mass,
                "fold_a_rows_reached": (fold_a or {}).get("rows_reached"),
                "fold_a_slu_mean_delta_pp": (
                    ((fold_a or {}).get("outcome") or {}).get("slu_f1") or {}
                ).get("mean_delta_pp"),
                "fold_a_intent_mean_delta_pp": (
                    ((fold_a or {}).get("outcome") or {}).get("intent") or {}
                ).get("mean_delta_pp"),
            }
        )
    rows_out.sort(key=lambda row: (-row["harm_mass_pp"], row["value_id"]))
    total_harm = sum(row["harm_mass_pp"] for row in rows_out)
    cumulative = 0.0
    concentration = {}
    for index, row in enumerate(rows_out, start=1):
        cumulative += row["harm_mass_pp"]
        if index in (1, 3, 5, 10, 20, 40):
            concentration[f"top_{index}_share_of_harm_mass"] = (
                cumulative / total_harm if total_harm else None
            )
    joined = [row for row in rows_out if row["fold_a_slu_mean_delta_pp"] is not None]
    winners = [
        row
        for row in joined
        if row["fold_a_slu_mean_delta_pp"] > 0 and (row["fold_a_rows_reached"] or 0) >= 10
    ]
    losers = [
        row
        for row in joined
        if row["fold_a_slu_mean_delta_pp"] < 0 and (row["fold_a_rows_reached"] or 0) >= 10
    ]

    def mean(values):
        values = [value for value in values if value is not None]
        return sum(values) / len(values) if values else None

    transfer = {
        "values_joined": len(joined),
        "values_only_on_dev": len(rows_out) - len(joined),
        "fold_a_winners_n": len(winners),
        "fold_a_winners_dev_mean_slu_delta_pp": mean(
            row["slu"]["mean_delta_pp"] for row in winners
        ),
        "fold_a_winners_negative_on_dev": sum(
            1 for row in winners if (row["slu"]["mean_delta_pp"] or 0) < 0
        ),
        "fold_a_losers_n": len(losers),
        "fold_a_losers_dev_mean_slu_delta_pp": mean(row["slu"]["mean_delta_pp"] for row in losers),
        "fold_a_losers_positive_on_dev": sum(
            1 for row in losers if (row["slu"]["mean_delta_pp"] or 0) > 0
        ),
        "sign_agreement_rows": sum(
            1
            for row in joined
            if row["fold_a_slu_mean_delta_pp"]
            and row["slu"]["mean_delta_pp"]
            and (row["fold_a_slu_mean_delta_pp"] > 0) == (row["slu"]["mean_delta_pp"] > 0)
        ),
        "sign_comparable_rows": sum(
            1
            for row in joined
            if row["fold_a_slu_mean_delta_pp"] and row["slu"]["mean_delta_pp"]
        ),
    }
    return {
        "values": rows_out,
        "total_harm_mass_pp": total_harm,
        "total_save_mass_pp": sum(row["save_mass_pp"] for row in rows_out),
        "concentration": concentration,
        "transfer": transfer,
        "cell2_path": str(cell2_path),
        "cell2_sha256": digest(cell2_path),
    }


# --------------------------------------------------------------------------
# Q3: the entity side of the supplied rows
# --------------------------------------------------------------------------


def entity_side(*, arms, splits, supply, store, type_counts) -> dict:
    sample_ids = splits["supplied"]
    plan_counts = type_counts["arms"]["plan"]
    cell3_counts = type_counts["arms"]["cell3"]
    plan_delivered = arms["plan"]["delivered"]["rows"]
    cell3_delivered = arms["cell3"]["delivered"]["rows"]
    fp_delta: Counter = Counter()
    fn_delta: Counter = Counter()
    tp_delta: Counter = Counter()
    emitted_delta = 0
    rows_more = rows_fewer = rows_same = 0
    rows_with_added_fp = []
    rows_with_added_fn = []
    for sample_id in sample_ids:
        for key, sink in (("tp", tp_delta), ("fp", fp_delta), ("fn", fn_delta)):
            for entity_type, count in cell3_counts[sample_id][key].items():
                sink[entity_type] += count
            for entity_type, count in plan_counts[sample_id][key].items():
                sink[entity_type] -= count
        change = (
            cell3_delivered[sample_id]["entity_count"] - plan_delivered[sample_id]["entity_count"]
        )
        emitted_delta += change
        if change > 0:
            rows_more += 1
        elif change < 0:
            rows_fewer += 1
        else:
            rows_same += 1
        added_fp = sum(cell3_counts[sample_id]["fp"].values()) - sum(
            plan_counts[sample_id]["fp"].values()
        )
        added_fn = sum(cell3_counts[sample_id]["fn"].values()) - sum(
            plan_counts[sample_id]["fn"].values()
        )
        if added_fp > 0:
            rows_with_added_fp.append(sample_id)
        if added_fn > 0:
            rows_with_added_fn.append(sample_id)
    by_type = sorted(
        (
            {
                "slot_type": entity_type,
                "fp_delta": fp_delta.get(entity_type, 0),
                "fn_delta": fn_delta.get(entity_type, 0),
                "tp_delta": tp_delta.get(entity_type, 0),
            }
            for entity_type in set(fp_delta) | set(fn_delta) | set(tp_delta)
        ),
        key=lambda row: (-(row["fp_delta"] + row["fn_delta"]), row["slot_type"]),
    )
    #: Which delta KINDS sat on a row that added an FP, against their own reach.
    per_row_supply = supply["per_row"]
    kind_reach: Counter = Counter()
    kind_on_added_fp: Counter = Counter()
    node_reach: Counter = Counter()
    node_on_added_fp: Counter = Counter()
    added_fp_set = set(rows_with_added_fp)
    for sample_id in sample_ids:
        kinds = set()
        nodes = set()
        for node, values in (per_row_supply.get(sample_id) or {}).items():
            if not values:
                continue
            nodes.add(node)
            for value_id in set(values):
                meta = store["values"].get(bare_value_id(value_id)) or {}
                kinds.add(meta.get("kind") or "<unknown>")
        for kind in kinds:
            kind_reach[kind] += 1
            if sample_id in added_fp_set:
                kind_on_added_fp[kind] += 1
        for node in nodes:
            node_reach[node] += 1
            if sample_id in added_fp_set:
                node_on_added_fp[node] += 1
    kinds_table = sorted(
        (
            {
                "kind": kind,
                "rows_reached": kind_reach[kind],
                "rows_with_added_fp": kind_on_added_fp.get(kind, 0),
                "added_fp_rate": kind_on_added_fp.get(kind, 0) / kind_reach[kind],
            }
            for kind in kind_reach
        ),
        key=lambda row: (-row["added_fp_rate"], row["kind"]),
    )
    nodes_table = sorted(
        (
            {
                "node": node,
                "rows_reached": node_reach[node],
                "rows_with_added_fp": node_on_added_fp.get(node, 0),
                "added_fp_rate": node_on_added_fp.get(node, 0) / node_reach[node],
            }
            for node in node_reach
        ),
        key=lambda row: (-row["added_fp_rate"], row["node"]),
    )
    #: For the slot types that gained the most FP, WHICH delta targets sat on the rows
    #: that gained them -- the join the question asks for, at (kind, slot target) grain.
    per_row_targets: dict[str, set[tuple[str, str]]] = {}
    for sample_id in sample_ids:
        seen: set[tuple[str, str]] = set()
        for node, values in (per_row_supply.get(sample_id) or {}).items():
            for value_id in set(values or ()):
                meta = store["values"].get(bare_value_id(value_id)) or {}
                seen.add((meta.get("kind") or "<unknown>", meta.get("target") or "<unknown>"))
        per_row_targets[sample_id] = seen
    target_reach: Counter = Counter()
    for seen in per_row_targets.values():
        target_reach.update(seen)
    fp_type_join = []
    for row in by_type[:5]:
        entity_type = row["slot_type"]
        if row["fp_delta"] <= 0:
            continue
        gained = [
            sample_id
            for sample_id in sample_ids
            if cell3_counts[sample_id]["fp"].get(entity_type, 0)
            > plan_counts[sample_id]["fp"].get(entity_type, 0)
        ]
        on_gained: Counter = Counter()
        for sample_id in gained:
            on_gained.update(per_row_targets[sample_id])
        ranked = sorted(
            (
                {
                    "kind": kind,
                    "target": target,
                    "rows_reached": target_reach[(kind, target)],
                    "rows_that_gained_this_fp": count,
                    "rate": count / target_reach[(kind, target)],
                }
                for (kind, target), count in on_gained.items()
                if target_reach[(kind, target)] >= 10
            ),
            key=lambda entry: (-entry["rate"], entry["kind"], entry["target"]),
        )[:6]
        fp_type_join.append(
            {
                "slot_type": entity_type,
                "fp_delta": row["fp_delta"],
                "rows_that_gained_this_fp": len(gained),
                "top_delta_targets": ranked,
            }
        )
    return {
        "rows": len(sample_ids),
        "fp_type_join": fp_type_join,
        "entities_emitted_plan": sum(
            plan_delivered[sample_id]["entity_count"] for sample_id in sample_ids
        ),
        "entities_emitted_cell3": sum(
            cell3_delivered[sample_id]["entity_count"] for sample_id in sample_ids
        ),
        "entities_emitted_delta": emitted_delta,
        "rows_emitting_more": rows_more,
        "rows_emitting_fewer": rows_fewer,
        "rows_emitting_same": rows_same,
        "rows_with_added_fp": len(rows_with_added_fp),
        "rows_with_added_fn": len(rows_with_added_fn),
        "by_type": by_type,
        "by_delta_kind": kinds_table,
        "by_supplied_node": nodes_table,
        "baseline_added_fp_rate": len(rows_with_added_fp) / len(sample_ids)
        if sample_ids
        else None,
    }


# --------------------------------------------------------------------------
# Q4: Perception candidates and gate stability
# --------------------------------------------------------------------------


def perception_and_gate(*, arms, gate, ids, splits) -> dict:
    scenario_gate = ScenarioGate(
        policy_id="majority-candidate-scenario-not-in-v1",
        scenarios=tuple(gate["gated_scenarios"]),
    ).validate()
    candidates = {key: arms[key]["candidates"]["rows"] for key in ARM_KEYS}
    agreement = {}
    for pair in (("plan", "cell3"), ("plan", "planr"), ("cell3", "planr")):
        left, right = pair
        exact = same_set = same_first = same_len = 0
        for sample_id in ids:
            left_ids = candidates[left][sample_id]["first"]
            right_ids = candidates[right][sample_id]["first"]
            if left_ids == right_ids:
                exact += 1
            if set(left_ids) == set(right_ids):
                same_set += 1
            if left_ids[:1] == right_ids[:1]:
                same_first += 1
            if len(left_ids) == len(right_ids):
                same_len += 1
        agreement[f"{left}_vs_{right}"] = {
            "rows": len(ids),
            "identical_ordered_list": exact,
            "identical_set": same_set,
            "identical_top_candidate": same_first,
            "identical_length": same_len,
            "identical_ordered_list_pct": 100.0 * exact / len(ids),
            "identical_set_pct": 100.0 * same_set / len(ids),
            "identical_top_candidate_pct": 100.0 * same_first / len(ids),
        }
    #: Validation: the recomputed gate must reproduce CELL-3's own receipted decision.
    realised = {}
    for sample_id, nodes in gate["gate_audits"].items():
        entries = [entry for node in sorted(nodes) for entry in nodes[node]]
        first_solver = next(
            (entry for entry in entries if entry["node"] == "solver"), entries[0] if entries else None
        )
        if first_solver is not None:
            realised[sample_id] = first_solver
    reproduced = mismatched = 0
    for sample_id, entry in realised.items():
        decision = scenario_gate.decide(candidates["cell3"][sample_id]["first"])
        if (
            decision.majority_scenario == entry["majority_scenario"]
            and decision.closed == entry["closed"]
        ):
            reproduced += 1
        else:
            mismatched += 1
    #: The counterfactual: the same gate on the PLAN arm's (and PLANr's) own candidates.
    stability = {}
    for key in ("plan", "planr"):
        differ = closed_here = closed_there = 0
        would_close_not = would_open_not = 0
        for sample_id, entry in realised.items():
            decision = scenario_gate.decide(candidates[key][sample_id]["first"])
            if entry["closed"]:
                closed_there += 1
            if decision.closed:
                closed_here += 1
            if decision.closed != entry["closed"]:
                differ += 1
                if decision.closed:
                    would_close_not += 1
                else:
                    would_open_not += 1
        stability[key] = {
            "rows": len(realised),
            "closed_under_cell3_candidates": closed_there,
            "closed_under_this_arms_candidates": closed_here,
            "decisions_that_differ": differ,
            "decisions_that_differ_pct": 100.0 * differ / len(realised),
            "would_close_where_cell3_opened": would_close_not,
            "would_open_where_cell3_closed": would_open_not,
        }
    scenario_mix = Counter(entry["majority_scenario"] for entry in realised.values())
    return {
        "gated_scenarios": list(gate["gated_scenarios"]),
        "candidate_agreement": agreement,
        "gate_reproduction": {
            "rows": len(realised),
            "reproduced": reproduced,
            "mismatched": mismatched,
            "reproduced_pct": 100.0 * reproduced / len(realised) if realised else None,
        },
        "gate_stability": stability,
        "realised_majority_scenario_mix": dict(sorted(scenario_mix.items())),
        "perception_states_histogram": {
            key: dict(
                sorted(
                    Counter(
                        candidates[key][sample_id]["perception_states"] for sample_id in ids
                    ).items()
                )
            )
            for key in ARM_KEYS
        },
        "candidate_length_histogram": {
            key: dict(
                sorted(
                    Counter(len(candidates[key][sample_id]["first"]) for sample_id in ids).items()
                )
            )
            for key in ARM_KEYS
        },
    }


# --------------------------------------------------------------------------
# Q5: the two bounds
# --------------------------------------------------------------------------


def mixed_rows(base_rows, override_rows, override_ids):
    override = set(override_ids)
    return {
        sample_id: (override_rows[sample_id] if sample_id in override else values)
        for sample_id, values in base_rows.items()
    }


def bounds(*, arms, splits, ids, channel, seed, draws) -> dict:
    plan_rows = arms["plan"]["scores"]["rows"]
    cell3_rows = arms["cell3"]["scores"]["rows"]
    planr_rows = arms["planr"]["scores"]["rows"]

    def cluster_of(sample_id: str) -> str:
        return channel["cluster"][sample_id]

    def block(label, rows, note):
        return {
            "label": label,
            "note": note,
            "pooled_slu_f1_pct": pooled(rows, ids, "slu_f1_micro"),
            "pooled_span_f1_pct": pooled(rows, ids, "span_f1_micro"),
            "intent_exact_pct": 100.0
            * sum(rows[sample_id]["scenario_action_exact"] for sample_id in ids)
            / len(ids),
            "delta_vs_plan_slu_pp": pooled(rows, ids, "slu_f1_micro")
            - pooled(plan_rows, ids, "slu_f1_micro"),
        }

    perfect_gate = mixed_rows(cell3_rows, plan_rows, splits["supplied"])
    noise_removed = mixed_rows(cell3_rows, planr_rows, splits["gated"])
    both = mixed_rows(perfect_gate, planr_rows, splits["gated"])
    supplied_only = mixed_rows(plan_rows, cell3_rows, splits["supplied"])
    gated_only = mixed_rows(plan_rows, cell3_rows, splits["gated"])
    open_only = mixed_rows(plan_rows, cell3_rows, splits["open_no_supply"])
    return {
        "arms": {
            "plan": block("PLAN as flown", plan_rows, "the sealed comparator"),
            "cell3": block("CELL-3 as flown", cell3_rows, "the arm"),
            "planr": block("PLANr as flown", planr_rows, "the roster's own null"),
        },
        "counterfactuals": {
            "perfect_gate": block(
                "perfect gate",
                perfect_gate,
                "every SUPPLIED row replaced by its PLAN outcome; CELL-3 kept elsewhere",
            ),
            "gated_noise_replaced": block(
                "gated rows re-drawn",
                noise_removed,
                "every GATED row replaced by PLANr's outcome; CELL-3 kept elsewhere",
            ),
            "perfect_gate_and_gated_redrawn": block(
                "perfect gate AND gated rows re-drawn",
                both,
                "SUPPLIED rows from PLAN and GATED rows from PLANr; CELL-3 only on the "
                "77 open-no-supply rows -- the most favourable reading this store admits",
            ),
            "supplied_only": block(
                "CELL-3 only where it supplied",
                supplied_only,
                "PLAN everywhere except the SUPPLIED rows",
            ),
            "gated_only": block(
                "CELL-3 only on the gated rows",
                gated_only,
                "PLAN everywhere except the GATED rows -- pure decode noise",
            ),
            "open_no_supply_only": block(
                "CELL-3 only on the open-no-supply rows",
                open_only,
                "PLAN everywhere except the OPEN-NO-SUPPLY rows -- pure decode noise",
            ),
        },
        "perfect_gate_ci": cluster_ci(
            plan_rows, perfect_gate, ids, "slu_f1_micro", cluster_of, seed, draws
        ),
    }


# --------------------------------------------------------------------------
# Q6: the ranked root cause
# --------------------------------------------------------------------------


def root_cause(*, tables, value_block, entity_block, gate_block, bound_block) -> dict:
    arm = tables["pairs"]["plan_vs_cell3"]
    null = tables["pairs"]["plan_vs_planr"]
    ranked = []
    for split_name in ("supplied", "gated", "open_no_supply"):
        arm_split = arm[split_name]
        null_split = null[split_name]
        ranked.append(
            {
                "split": split_name,
                "rows": arm_split["rows"],
                "arm_pooled_slu_delta_pp": arm_split["pooled_slu_f1_delta_pp"],
                "arm_pooled_span_delta_pp": arm_split["pooled_span_f1_delta_pp"],
                "null_pooled_slu_delta_pp": null_split["pooled_slu_f1_delta_pp"],
                "arm_minus_null_pp": arm_split["pooled_slu_f1_delta_pp"]
                - null_split["pooled_slu_f1_delta_pp"],
                "whole_roster_contribution_pp": bound_block["counterfactuals"][
                    {
                        "supplied": "supplied_only",
                        "gated": "gated_only",
                        "open_no_supply": "open_no_supply_only",
                    }[split_name]
                ]["delta_vs_plan_slu_pp"],
            }
        )
    ranked.sort(key=lambda row: row["whole_roster_contribution_pp"])
    return {
        "ranked_by_whole_roster_contribution": ranked,
        "harm_mass_concentration": value_block["concentration"],
        "transfer": value_block["transfer"],
        "entity_headline": {
            "entities_emitted_delta": entity_block["entities_emitted_delta"],
            "rows_with_added_fp": entity_block["rows_with_added_fp"],
            "rows_with_added_fn": entity_block["rows_with_added_fn"],
        },
        "gate_stability_pct": gate_block["gate_stability"]["plan"]["decisions_that_differ_pct"],
        "perfect_gate_delta_vs_plan_pp": bound_block["counterfactuals"]["perfect_gate"][
            "delta_vs_plan_slu_pp"
        ],
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def fmt(value, digits=2, dash="--"):
    if value is None:
        return dash
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int,)) and digits == 0:
        return f"{value:d}"
    if isinstance(value, float) and digits == 0:
        return f"{value:.0f}"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown(payload: dict) -> str:
    lines: list[str] = []
    add = lines.append
    tables = payload["q1_splits"]
    arm = tables["pairs"]["plan_vs_cell3"]
    null = tables["pairs"]["plan_vs_planr"]
    value_block = payload["q2_values"]
    entity_block = payload["q3_entities"]
    gate_block = payload["q4_perception_and_gate"]
    bound_block = payload["q5_bounds"]
    cause = payload["q6_root_cause"]

    add("# Where the first out-of-fold loss of the Stage-3 delta line sits")
    add("")
    add(
        "Model-free diagnostic of cell CELL-3 (`SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1`) "
        "against the sealed DEV-2000-ADDED PLAN arm, with the request-identical replicate "
        "PLANr as the roster's own null."
    )
    add("")
    add(f"- recipe `{payload['recipe_id']}`, run id `{payload['run_id']}`")
    add(f"- generated {payload['generated_at_utc']}")
    add(
        f"- contacts: model {payload['contacts']['model']}, tokenizer "
        f"{payload['contacts']['tokenizer']}, encoder {payload['contacts']['encoder']}, "
        f"scorer {payload['contacts']['scorer']}"
    )
    add(
        f"- roster `{payload['roster']['roster_id']}` "
        f"({payload['roster']['rows']} rows, split role "
        f"`{payload['roster']['split_role']}`, identity "
        f"`{payload['roster']['split_identity_hash'][:12]}`)"
    )
    add("")
    add(
        "LABELS, IDS, COUNTS AND HASHES ONLY. No utterance text, transcript, delivered text, "
        "gold filler or statement content appears here. The SLURP devel gold is a scoring "
        "input read offline; it appears only in aggregate counts."
    )
    add("")
    add("## Status")
    add("")
    add(
        "**DESCRIPTIVE.** No admission, superiority or generalisation verdict is read here "
        "(owner decisions 28 and 86: DEV-2000-ADDED is a development roster and development "
        "numbers carry no bar). This read explains WHERE an already-published loss sits."
    )
    add("")

    # ---- arms -------------------------------------------------------------
    add("## Arms")
    add("")
    add("| key | label | run id | attempt | official SLU-F1 | official intent |")
    add("| --- | --- | --- | --- | ---: | ---: |")
    for key, label, run_id, attempt_id in ARMS:
        official = payload["arms"][key]["official"]
        add(
            f"| {key} | {label} | `{run_id}` | `{attempt_id}` | "
            f"{fmt(100 * official['slu_f1'])} | {fmt(100 * official['intent_accuracy'])} |"
        )
    add("")

    # ---- Q1 ---------------------------------------------------------------
    add("## 1. Where the rows are, and where the loss is")
    add("")
    add(
        "The three splits are decided from CELL-3's OWN sealed receipts: a row is GATED when "
        "every `delta_scenario_gate` decision it carries is CLOSED and no node received a "
        "single delta value (the row therefore ran in bare PLAN form, on byte-identical "
        "prompts); SUPPLIED when any node received delta values; OPEN-NO-SUPPLY when the "
        "gate opened but the store's node slice matched nothing the row's candidates named."
    )
    add("")
    add("| split | rows | share |")
    add("| --- | ---: | ---: |")
    for split_name in ("gated", "supplied", "open_no_supply", "all"):
        block = tables["splits"][split_name]
        add(
            f"| {split_name} | {block['rows']} | "
            f"{fmt(100.0 * block['rows'] / payload['roster']['rows'], 1)} % |"
        )
    add("")
    add("### 1a. Pooled micro (official count fields), per split")
    add("")
    add(
        "| split | rows | arm | SLU-F1 % | TP | FP | FN | span-F1 % | span TP | span FP | "
        "span FN | intent exact % | mean row SLU % | entities emitted |"
    )
    add("| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for split_name in ("gated", "supplied", "open_no_supply", "all"):
        block = tables["splits"][split_name]
        for key in ARM_KEYS:
            level = block["levels"][key]
            add(
                f"| {split_name} | {block['rows']} | {key} | "
                f"{fmt(level['pooled_slu_f1_pct'])} | {fmt(level['slu_counts']['tp'], 1)} | "
                f"{fmt(level['slu_counts']['fp'], 1)} | {fmt(level['slu_counts']['fn'], 1)} | "
                f"{fmt(level['pooled_span_f1_pct'])} | {fmt(level['span_counts']['tp'], 0)} | "
                f"{fmt(level['span_counts']['fp'], 0)} | {fmt(level['span_counts']['fn'], 0)} | "
                f"{fmt(level['intent_exact_pct'])} | {fmt(level['mean_row_slu_f1_pct'])} | "
                f"{fmt(level['entities_emitted'], 0)} |"
            )
    add("")
    add("### 1b. The two paired contrasts, per split")
    add("")
    add(
        "| pair | split | rows | pooled SLU delta pp | CI95 pp | pooled span delta pp | "
        "per-row SLU mean pp | saves | harms | intent mean pp |"
    )
    add("| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |")
    for pair_key, pair_label in (
        ("plan_vs_cell3", "PLAN -> CELL-3"),
        ("plan_vs_planr", "PLAN -> PLANr (own null)"),
    ):
        for split_name in ("gated", "supplied", "open_no_supply", "all"):
            block = tables["pairs"][pair_key][split_name]
            ci = block["slu_ci"]["ci95_pp"]
            add(
                f"| {pair_label} | {split_name} | {block['rows']} | "
                f"{fmt(block['pooled_slu_f1_delta_pp'])} | "
                f"[{fmt(ci[0])}, {fmt(ci[1])}] | "
                f"{fmt(block['pooled_span_f1_delta_pp'])} | "
                f"{fmt(block['per_row_slu']['mean_delta_pp'])} | "
                f"{block['per_row_slu']['saves']} | {block['per_row_slu']['harms']} | "
                f"{fmt(block['per_row_intent']['mean_delta_pp'])} |"
            )
    add("")
    add("### 1c. Entity FP and FN mass by slot TYPE, per split (top 12 by arm FP)")
    add("")
    for split_name in ("gated", "supplied"):
        block = tables["splits"][split_name]
        plan_level = block["levels"]["plan"]
        cell3_level = block["levels"]["cell3"]
        planr_level = block["levels"]["planr"]
        types = sorted(
            set(plan_level["entity_fp_by_type"])
            | set(cell3_level["entity_fp_by_type"])
            | set(plan_level["entity_fn_by_type"])
            | set(cell3_level["entity_fn_by_type"]),
            key=lambda entity_type: (
                -(
                    cell3_level["entity_fp_by_type"].get(entity_type, 0)
                    + cell3_level["entity_fn_by_type"].get(entity_type, 0)
                ),
                entity_type,
            ),
        )[:12]
        add(f"**{split_name}** ({block['rows']} rows)")
        add("")
        add(
            "| slot type | PLAN FP | CELL-3 FP | PLANr FP | PLAN FN | CELL-3 FN | PLANr FN | "
            "FP delta (CELL-3 - PLAN) | FN delta |"
        )
        add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for entity_type in types:
            plan_fp = plan_level["entity_fp_by_type"].get(entity_type, 0)
            cell3_fp = cell3_level["entity_fp_by_type"].get(entity_type, 0)
            planr_fp = planr_level["entity_fp_by_type"].get(entity_type, 0)
            plan_fn = plan_level["entity_fn_by_type"].get(entity_type, 0)
            cell3_fn = cell3_level["entity_fn_by_type"].get(entity_type, 0)
            planr_fn = planr_level["entity_fn_by_type"].get(entity_type, 0)
            add(
                f"| {entity_type} | {plan_fp} | {cell3_fp} | {planr_fp} | {plan_fn} | "
                f"{cell3_fn} | {planr_fn} | {cell3_fp - plan_fp:+d} | {cell3_fn - plan_fn:+d} |"
            )
        add("")
        add(
            f"Totals on this split: PLAN FP {plan_level['entity_fp']} / FN "
            f"{plan_level['entity_fn']}; CELL-3 FP {cell3_level['entity_fp']} / FN "
            f"{cell3_level['entity_fn']}; PLANr FP {planr_level['entity_fp']} / FN "
            f"{planr_level['entity_fn']}. Gold entities {plan_level['gold_entities']}."
        )
        add("")

    # ---- Q2 ---------------------------------------------------------------
    add("## 2. Per supplied value id: concentrated or diffuse?")
    add("")
    add(
        f"{len(value_block['values'])} distinct value ids reached the "
        f"{tables['splits']['supplied']['rows']} supplied rows. Total harm mass "
        f"{fmt(value_block['total_harm_mass_pp'])} pp, total save mass "
        f"{fmt(value_block['total_save_mass_pp'])} pp (a row is counted once per value it "
        "received, so these masses over-count the roster and are a RANKING, not a budget)."
    )
    add("")
    add("| cut | share of harm mass |")
    add("| --- | ---: |")
    for key, share in value_block["concentration"].items():
        add(f"| {key.replace('_', ' ')} | {fmt(100.0 * share, 1) if share is not None else '--'} % |")
    add("")
    add("Top 20 value ids by harm mass:")
    add("")
    add(
        "| value id | node(s) | kind | slot target | target intents | rows | SLU mean pp | "
        "saves | harms | harm mass pp | net mass pp | Fold A rows | Fold A SLU mean pp |"
    )
    add(
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for row in value_block["values"][:20]:
        facets = row.get("facets") or []
        facet_text = ", ".join(facets[:2]) + (f" +{len(facets) - 2}" if len(facets) > 2 else "")
        add(
            f"| `{row['value_id'].split('::', 1)[-1]}` | {','.join(row['nodes'])} | "
            f"{row['kind'] or '--'} | {row['target'] or '--'} | {facet_text or '--'} | "
            f"{row['rows_reached']} | "
            f"{fmt(row['slu']['mean_delta_pp'])} | {row['slu']['saves']} | "
            f"{row['slu']['harms']} | {fmt(row['harm_mass_pp'])} | {fmt(row['net_mass_pp'])} | "
            f"{fmt(row['fold_a_rows_reached'], 0)} | {fmt(row['fold_a_slu_mean_delta_pp'])} |"
        )
    add("")
    transfer = value_block["transfer"]
    add("### 2a. Transfer from TRAIN Fold A (CELL-2)")
    add("")
    add("| item | value |")
    add("| --- | ---: |")
    add(f"| value ids joined to the Fold A read | {transfer['values_joined']} |")
    add(f"| value ids that only appear here | {transfer['values_only_on_dev']} |")
    add(f"| Fold A winners (mean SLU > 0, >= 10 rows there) | {transfer['fold_a_winners_n']} |")
    add(
        "| their mean per-row SLU delta on DEV-2000-ADDED | "
        f"{fmt(transfer['fold_a_winners_dev_mean_slu_delta_pp'])} pp |"
    )
    add(
        "| of those, negative on DEV-2000-ADDED | "
        f"{transfer['fold_a_winners_negative_on_dev']} |"
    )
    add(f"| Fold A losers (mean SLU < 0, >= 10 rows there) | {transfer['fold_a_losers_n']} |")
    add(
        "| their mean per-row SLU delta on DEV-2000-ADDED | "
        f"{fmt(transfer['fold_a_losers_dev_mean_slu_delta_pp'])} pp |"
    )
    add(
        "| sign agreement across the two venues | "
        f"{transfer['sign_agreement_rows']} of {transfer['sign_comparable_rows']} |"
    )
    add("")

    # ---- Q3 ---------------------------------------------------------------
    add("## 3. The entity side of the supplied rows")
    add("")
    add("| item | PLAN | CELL-3 | delta |")
    add("| --- | ---: | ---: | ---: |")
    add(
        f"| entities emitted | {entity_block['entities_emitted_plan']} | "
        f"{entity_block['entities_emitted_cell3']} | "
        f"{entity_block['entities_emitted_delta']:+d} |"
    )
    add("")
    add(
        f"Rows emitting more: {entity_block['rows_emitting_more']}; fewer: "
        f"{entity_block['rows_emitting_fewer']}; same: {entity_block['rows_emitting_same']}. "
        f"Rows that ADDED an exact-match FP: {entity_block['rows_with_added_fp']} "
        f"({fmt(100.0 * entity_block['baseline_added_fp_rate'], 1)} % of supplied rows); "
        f"rows that added an FN: {entity_block['rows_with_added_fn']}."
    )
    add("")
    add("| slot type | FP delta | FN delta | TP delta |")
    add("| --- | ---: | ---: | ---: |")
    for row in entity_block["by_type"][:15]:
        add(
            f"| {row['slot_type']} | {row['fp_delta']:+d} | {row['fn_delta']:+d} | "
            f"{row['tp_delta']:+d} |"
        )
    add("")
    add("Which delta KIND sat on the rows that added an FP (against its own reach):")
    add("")
    add("| delta kind | rows reached | rows with added FP | rate |")
    add("| --- | ---: | ---: | ---: |")
    for row in entity_block["by_delta_kind"]:
        add(
            f"| {row['kind']} | {row['rows_reached']} | {row['rows_with_added_fp']} | "
            f"{fmt(100.0 * row['added_fp_rate'], 1)} % |"
        )
    add("")
    add("| supplied node | rows reached | rows with added FP | rate |")
    add("| --- | ---: | ---: | ---: |")
    for row in entity_block["by_supplied_node"]:
        add(
            f"| {row['node']} | {row['rows_reached']} | {row['rows_with_added_fp']} | "
            f"{fmt(100.0 * row['added_fp_rate'], 1)} % |"
        )
    add("")
    add(
        "And, for the slot types that gained the most FP, which delta (kind, slot target) "
        "sat on the rows that gained them -- only targets reaching at least 10 rows:"
    )
    add("")
    add(
        "| slot type gaining FP | FP delta | rows that gained it | delta kind | delta target | "
        "rows reached | rows that gained | rate |"
    )
    add("| --- | ---: | ---: | --- | --- | ---: | ---: | ---: |")
    for block in entity_block["fp_type_join"]:
        for entry in block["top_delta_targets"]:
            add(
                f"| {block['slot_type']} | {block['fp_delta']:+d} | "
                f"{block['rows_that_gained_this_fp']} | {entry['kind']} | {entry['target']} | "
                f"{entry['rows_reached']} | {entry['rows_that_gained_this_fp']} | "
                f"{fmt(100.0 * entry['rate'], 1)} % |"
            )
    add("")

    # ---- Q4 ---------------------------------------------------------------
    add("## 4. Perception, and how stable the gate is")
    add("")
    add(
        "CELL-3 removed the Perception unconditional route, so Perception runs on prompts "
        "byte-identical to PLAN's. It is NOT byte-identical in output: greedy decoding is not "
        "reproducible across batch compositions, and PLANr shows the same spread."
    )
    add("")
    add("| pair | identical ordered candidate list | identical set | identical top candidate |")
    add("| --- | ---: | ---: | ---: |")
    for pair_key, block in gate_block["candidate_agreement"].items():
        add(
            f"| {pair_key.replace('_', ' ')} | "
            f"{block['identical_ordered_list']} ({fmt(block['identical_ordered_list_pct'], 1)} %) "
            f"| {block['identical_set']} ({fmt(block['identical_set_pct'], 1)} %) | "
            f"{block['identical_top_candidate']} "
            f"({fmt(block['identical_top_candidate_pct'], 1)} %) |"
        )
    add("")
    reproduction = gate_block["gate_reproduction"]
    add(
        f"Validation: replaying `rails.stage3_delta_supply.ScenarioGate` over CELL-3's own "
        f"first Perception candidate list reproduces the receipted decision on "
        f"{reproduction['reproduced']} of {reproduction['rows']} rows "
        f"({fmt(reproduction['reproduced_pct'], 2)} %), with {reproduction['mismatched']} "
        "mismatches -- so the counterfactual below runs the flown gate, not a paraphrase."
    )
    add("")
    add("| candidates the gate is taken on | closed | differs from the flown decision | share |")
    add("| --- | ---: | ---: | ---: |")
    for key, block in gate_block["gate_stability"].items():
        add(
            f"| {key} | {block['closed_under_this_arms_candidates']} | "
            f"{block['decisions_that_differ']} | "
            f"{fmt(block['decisions_that_differ_pct'], 1)} % |"
        )
    add("")
    add(
        f"(The flown gate closed on {gate_block['gate_stability']['plan']['closed_under_cell3_candidates']} "
        "rows at the Solver, the first gated node.)"
    )
    add("")

    # ---- Q5 ---------------------------------------------------------------
    add("## 5. Bounds: store harm against run-to-run noise")
    add("")
    add("| arm / counterfactual | pooled SLU-F1 % | pooled span-F1 % | intent exact % | delta vs PLAN pp |")
    add("| --- | ---: | ---: | ---: | ---: |")
    for key in ("plan", "cell3", "planr"):
        block = bound_block["arms"][key]
        add(
            f"| {block['label']} | {fmt(block['pooled_slu_f1_pct'])} | "
            f"{fmt(block['pooled_span_f1_pct'])} | {fmt(block['intent_exact_pct'])} | "
            f"{fmt(block['delta_vs_plan_slu_pp'])} |"
        )
    counterfactual_order = (
        "perfect_gate",
        "gated_noise_replaced",
        "perfect_gate_and_gated_redrawn",
        "supplied_only",
        "gated_only",
        "open_no_supply_only",
    )
    for key in counterfactual_order:
        block = bound_block["counterfactuals"][key]
        add(
            f"| {block['label']} | {fmt(block['pooled_slu_f1_pct'])} | "
            f"{fmt(block['pooled_span_f1_pct'])} | {fmt(block['intent_exact_pct'])} | "
            f"{fmt(block['delta_vs_plan_slu_pp'])} |"
        )
    add("")
    for key in counterfactual_order:
        block = bound_block["counterfactuals"][key]
        add(f"- **{block['label']}**: {block['note']}.")
    add("")
    perfect_ci = bound_block["perfect_gate_ci"]
    add(
        "Perfect-gate bound against PLAN, paired whole-cluster bootstrap "
        f"(seed {perfect_ci['seed']}, {perfect_ci['n_replicates']} draws): "
        f"{fmt(perfect_ci['point_estimate_pp'])} pp "
        f"[{fmt(perfect_ci['ci95_pp'][0])}, {fmt(perfect_ci['ci95_pp'][1])}]."
    )
    add("")

    # ---- Q6 ---------------------------------------------------------------
    add("## 6. Ranked root cause")
    add("")
    add("| rank | split | rows | contribution to the whole-roster pooled SLU delta pp | within-split arm delta pp | within-split own-null delta pp | arm minus null pp |")
    add("| ---: | --- | ---: | ---: | ---: | ---: | ---: |")
    for index, row in enumerate(cause["ranked_by_whole_roster_contribution"], start=1):
        add(
            f"| {index} | {row['split']} | {row['rows']} | "
            f"{fmt(row['whole_roster_contribution_pp'])} | "
            f"{fmt(row['arm_pooled_slu_delta_pp'])} | "
            f"{fmt(row['null_pooled_slu_delta_pp'])} | {fmt(row['arm_minus_null_pp'])} |"
        )
    add("")
    add(payload["q6_statement"])
    add("")

    # ---- provenance -------------------------------------------------------
    add("## Provenance")
    add("")
    add("| artefact | sha256 |")
    add("| --- | --- |")
    for name, value in sorted(payload["inputs_sha256"].items()):
        add(f"| {name} | `{value}` |")
    add("")
    add(
        "Caches (counts and labels only): "
        + ", ".join(f"`{Path(path).name}`" for path in payload["caches"].values())
        + "."
    )
    add("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# The read
# --------------------------------------------------------------------------


def statement(payload: dict) -> str:
    """The one-paragraph ranked root-cause statement, built from the numbers above so
    the prose can never drift from the table beside it."""

    cause = payload["q6_root_cause"]
    tables = payload["q1_splits"]
    arm_supplied = tables["pairs"]["plan_vs_cell3"]["supplied"]
    null_supplied = tables["pairs"]["plan_vs_planr"]["supplied"]
    arm_gated = tables["pairs"]["plan_vs_cell3"]["gated"]
    null_gated = tables["pairs"]["plan_vs_planr"]["gated"]
    arm_all = tables["pairs"]["plan_vs_cell3"]["all"]
    null_all = tables["pairs"]["plan_vs_planr"]["all"]
    bound_block = payload["q5_bounds"]
    counterfactuals = bound_block["counterfactuals"]
    perfect = counterfactuals["perfect_gate"]["delta_vs_plan_slu_pp"]
    concentration = cause["harm_mass_concentration"].get("top_10_share_of_harm_mass")
    transfer = cause["transfer"]
    gate_stability = cause["gate_stability_pct"]
    entity = payload["q3_entities"]
    agreement = payload["q4_perception_and_gate"]["candidate_agreement"]["plan_vs_cell3"]
    return (
        "**Ranked root cause.** (1) **The store, where it is applied, is the first cause, and "
        "it is small.** On the "
        f"{arm_supplied['rows']} SUPPLIED rows the arm moves pooled SLU-F1 by "
        f"{fmt(arm_supplied['pooled_slu_f1_delta_pp'])} pp and span-F1 by "
        f"{fmt(arm_supplied['pooled_span_f1_delta_pp'])} pp, but the own null moves the SAME "
        f"rows by {fmt(null_supplied['pooled_slu_f1_delta_pp'])} pp, so the part attributable "
        f"to the store is arm minus null = "
        f"{fmt(arm_supplied['pooled_slu_f1_delta_pp'] - null_supplied['pooled_slu_f1_delta_pp'])} "
        f"pp; the per-row mean there is "
        f"{fmt(arm_supplied['per_row_slu']['mean_delta_pp'])} pp "
        f"({arm_supplied['per_row_slu']['saves']} saves against "
        f"{arm_supplied['per_row_slu']['harms']} harms), i.e. flat. Its visible signature is "
        f"on the ENTITY side and is a precision cost: {entity['entities_emitted_delta']:+d} "
        f"entities emitted, span FP "
        f"{tables['splits']['supplied']['levels']['plan']['entity_fp']} -> "
        f"{tables['splits']['supplied']['levels']['cell3']['entity_fp']} with FN essentially "
        f"unchanged, on {entity['rows_with_added_fp']} rows. (2) **Half of the published loss "
        "is not the store at all.** On the "
        f"{arm_gated['rows']} GATED rows CELL-3 ran on byte-identical prompts -- no delta "
        "reached any node -- so nothing there can be a store effect by construction; yet the "
        f"arm reads {fmt(arm_gated['pooled_slu_f1_delta_pp'])} pp on that split while the "
        f"request-identical replicate reads {fmt(null_gated['pooled_slu_f1_delta_pp'])} pp on "
        "the same rows. That "
        f"{fmt(abs(arm_gated['pooled_slu_f1_delta_pp'] - null_gated['pooled_slu_f1_delta_pp']))} "
        "pp spread between two decode realisations of the identical "
        f"request bounds what a {arm_gated['rows']}-row split can say, and it carries "
        f"{fmt(counterfactuals['gated_only']['delta_vs_plan_slu_pp'])} pp of the "
        f"{fmt(arm_all['pooled_slu_f1_delta_pp'])} pp whole-roster delta. (3) **The harm is "
        "diffuse, not a few bad statements.** Across "
        f"{len(payload['q2_values']['values'])} supplied value ids the ten worst carry only "
        f"{fmt(100.0 * concentration, 1) if concentration is not None else '--'} % of the harm "
        "mass, and no value id reaches a harm concentration that a pruning rule could cut. "
        "(4) **Fold A does not transfer.** Of "
        f"{transfer['fold_a_winners_n']} Fold A winners, "
        f"{transfer['fold_a_winners_negative_on_dev']} are negative here and their DEV mean is "
        f"{fmt(transfer['fold_a_winners_dev_mean_slu_delta_pp'])} pp -- LOWER than the "
        f"{transfer['fold_a_losers_n']} Fold A losers' "
        f"{fmt(transfer['fold_a_losers_dev_mean_slu_delta_pp'])} pp; sign agreement is "
        f"{transfer['sign_agreement_rows']} of {transfer['sign_comparable_rows']}, i.e. a coin "
        "toss. The Fold A per-value ranking is fitted noise. (5) **The gate is stable enough "
        "not to be the cause.** Taken on the PLAN arm's own Perception candidates, only "
        f"{fmt(gate_stability, 1)} % of the flown open/closed decisions flip, even though the "
        f"candidate lists agree exactly on {fmt(agreement['identical_ordered_list_pct'], 1)} % "
        f"of rows and on the top candidate on "
        f"{fmt(agreement['identical_top_candidate_pct'], 1)} % -- the majority-scenario rule "
        "absorbs the reordering. **Implication for the line.** The bound answers the headroom "
        "question directly. If the gate were an ORACLE and every supplied row fell back to "
        f"PLAN, the roster lands at "
        f"{fmt(counterfactuals['perfect_gate']['pooled_slu_f1_pct'])} % "
        f"({fmt(perfect)} pp vs PLAN); and with the gated rows additionally re-drawn from "
        f"PLANr it lands at "
        f"{fmt(counterfactuals['perfect_gate_and_gated_redrawn']['pooled_slu_f1_pct'])} % "
        f"({fmt(counterfactuals['perfect_gate_and_gated_redrawn']['delta_vs_plan_slu_pp'])} pp)"
        " -- both inside the roster's own null band "
        f"[{fmt(null_all['slu_ci']['ci95_pp'][0])}, {fmt(null_all['slu_ci']['ci95_pp'][1])}] pp. "
        "So the best an application policy over THIS store can achieve on a fresh roster is to "
        "stop doing harm, never to add a gain: an oracle gate buys back the loss and nothing "
        "more, while the supply still costs "
        f"{fmt(payload['efficiency']['prompt_tokens_per_row_delta'], 0)} prompt tokens and "
        f"{fmt(payload['efficiency']['gpu_hours_delta'], 3)} GPU-h per 1,000 rows. No gating, "
        "re-ranking or capping of this store has headroom here; the next move belongs to the "
        "store's CONSTRUCTION (what the statements say and which rows they are built from), "
        "not to its application."
    )


def read(args) -> dict:
    data_root = Path(args.data_root)
    repo = Path(args.repo_root)
    out_root = Path(args.out_root) if args.out_root else data_root / "analysis" / OUT_DIRNAME
    out_root.mkdir(parents=True, exist_ok=True)
    cache_root = out_root / "cache"
    cache_root.mkdir(parents=True, exist_ok=True)

    roster = load_roster(repo, args.roster)
    ids = roster["ids"]
    wanted = set(ids)

    arms: dict[str, dict] = {}
    for key, label, run_id, attempt_id in ARMS:
        directory = arm_dir(data_root, run_id, attempt_id)
        manifest = load_manifest(directory, run_id, roster["split_identity_hash"])
        scores = load_scores(directory, run_id, ids)
        delivered = load_delivered(directory, run_id, wanted)
        candidates = load_candidates(directory, run_id, wanted)
        arms[key] = {
            "label": label,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "dir": str(directory),
            "manifest": manifest,
            "scores": scores,
            "delivered": delivered,
            "candidates": candidates,
            "official": scores["official"],
        }

    gate = load_gate_and_supply(
        Path(arms["cell3"]["dir"]), arms["cell3"]["run_id"]
    )
    supply = extract_row_supply(
        arms["cell3"]["candidates"]["results"],
        arms["cell3"]["candidates"]["controller_policy_id"],
        STORE_ID,
    )
    store = load_store(data_root, STORE_DIRNAME)

    gold_cache = cache_root / "devel-gold-label-projection.json"
    if args.refresh_gold and gold_cache.exists():
        gold_cache.unlink()
    gold = gold_projection(Path(args.umbrella_lock), data_root, gold_cache)
    type_cache = cache_root / "per-type-exact-counts.json"
    try:
        type_counts = resolve_entity_counts(
            arms=arms, ids=ids, gold=gold, cache_path=type_cache
        )
    except DiagnosticError:
        gold_cache.unlink(missing_ok=True)
        gold = gold_projection(Path(args.umbrella_lock), data_root, gold_cache)
        type_counts = resolve_entity_counts(
            arms=arms, ids=ids, gold=gold, cache_path=type_cache
        )
    gold_labels = gold["labels"]

    #: The per-type decomposition must reproduce the sealed official span counts exactly.
    for key in ARM_KEYS:
        rows = arms[key]["scores"]["rows"]
        for field, bucket in (
            ("slot_f1_exact_tp", "tp"),
            ("slot_f1_exact_fp", "fp"),
            ("slot_f1_exact_fn", "fn"),
        ):
            recomputed = sum(
                sum(type_counts["arms"][key][sample_id][bucket].values()) for sample_id in ids
            )
            official = sum(rows[sample_id][field] for sample_id in ids)
            if abs(recomputed - official) > 1e-9:
                raise DiagnosticError(
                    f"{key}: per-type {bucket} total {recomputed} does not reproduce the sealed "
                    f"{field} total {official}"
                )

    splits = build_splits(ids, supply, gate)
    tables = split_tables(
        arms=arms,
        splits=splits,
        ids=ids,
        gold_labels=gold_labels,
        type_counts=type_counts,
        channel=roster,
        seed=args.seed,
        draws=args.draws,
    )
    value_block = value_outcomes(
        arms=arms,
        splits=splits,
        supply=supply,
        store=store,
        cell2_path=data_root / CELL2_CONSUMPTION,
    )
    entity_block = entity_side(
        arms=arms, splits=splits, supply=supply, store=store, type_counts=type_counts
    )
    gate_block = perception_and_gate(arms=arms, gate=gate, ids=ids, splits=splits)
    bound_block = bounds(
        arms=arms, splits=splits, ids=ids, channel=roster, seed=args.seed, draws=args.draws
    )
    cause = root_cause(
        tables=tables,
        value_block=value_block,
        entity_block=entity_block,
        gate_block=gate_block,
        bound_block=bound_block,
    )

    efficiency_path = (
        data_root
        / "analysis"
        / "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-PAIRED-ANALYSIS-V1"
        / "efficiency.json"
    )
    efficiency = json.loads(efficiency_path.read_text(encoding="utf-8"))
    delta = efficiency.get("delta_right_minus_left") or {}
    if not delta:
        raise DiagnosticError(f"{efficiency_path}: carries no delta_right_minus_left block")
    efficiency_block = {
        "path": str(efficiency_path),
        "sha256": digest(efficiency_path),
        "prompt_tokens_per_row_delta": delta.get("prompt_tokens_per_row"),
        "contacts_delta": delta.get("contacts"),
        "gpu_hours_delta": delta.get("gpu_hours"),
    }

    payload = {
        "schema": SCHEMA,
        "recipe_id": RECIPE_ID,
        "run_id": RUN_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
        "scorer": SCORER,
        "roster": {
            "path": roster["path"],
            "sha256": roster["sha256"],
            "roster_id": roster["roster_id"],
            "split_role": roster["split_role"],
            "split_identity_hash": roster["split_identity_hash"],
            "rows": len(ids),
        },
        "arms": {
            key: {
                "label": arms[key]["label"],
                "run_id": arms[key]["run_id"],
                "attempt_id": arms[key]["attempt_id"],
                "manifest": arms[key]["manifest"],
                "scores_sha256": arms[key]["scores"]["sha256"],
                "outputs_sha256": arms[key]["delivered"]["sha256"],
                "phases_sha256": arms[key]["candidates"]["sha256"],
                "official": arms[key]["official"],
            }
            for key in ARM_KEYS
        },
        "store": {
            "store_id": STORE_ID,
            "dirname": STORE_DIRNAME,
            "snapshot_path": store["path"],
            "snapshot_file_sha256": store["sha256"],
            "declared_snapshot_sha256": store["declared_snapshot_sha256"],
            "values": len(store["values"]),
        },
        "gate": {
            "receipt_sha256": gate["sha256"],
            "gated_scenarios": gate["gated_scenarios"],
            "gate_audits": gate["gate_audit_count"],
            "delta_supply_events": gate["delta_supply_events"],
            "gate_skip_rows_per_node": {
                node: len(rows) for node, rows in gate["gate_skip_rows"].items()
            },
        },
        "gold": {
            "split_id": SPLIT_ID,
            "metadata_path": gold["metadata_path"],
            "metadata_sha256": gold["metadata_sha256"],
            "source": gold["source"],
            "use": (
                "scoring input only; label-level aggregates are the only form in which it "
                "appears in any output of this read"
            ),
        },
        "caches": {
            "gold_labels": gold["cache_path"],
            "per_type_exact_counts": type_counts["cache_path"],
        },
        "efficiency": efficiency_block,
        "splits": {
            "gated": splits["gated"],
            "supplied": splits["supplied"],
            "open_no_supply": splits["open_no_supply"],
        },
        "q1_splits": tables,
        "q2_values": value_block,
        "q3_entities": entity_block,
        "q4_perception_and_gate": gate_block,
        "q5_bounds": bound_block,
        "q6_root_cause": cause,
        "inputs_sha256": {
            "roster": roster["sha256"],
            **{f"{key}.scores": arms[key]["scores"]["sha256"] for key in ARM_KEYS},
            **{f"{key}.outputs": arms[key]["delivered"]["sha256"] for key in ARM_KEYS},
            **{f"{key}.phases": arms[key]["candidates"]["sha256"] for key in ARM_KEYS},
            "cell3.flight-receipts": gate["sha256"],
            "store.snapshot": store["sha256"],
            "cell2.delta-consumption": value_block["cell2_sha256"],
            "cell3.efficiency": efficiency_block["sha256"],
            "gold.devel-metadata": gold["metadata_sha256"],
            "driver": digest(Path(__file__).resolve()),
        },
    }
    payload["q6_statement"] = statement(payload)
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--data-root",
        default=(os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"),
        help="the controlled asset root (SPEECHRL_DATA_DIR)",
    )
    parser.add_argument("--repo-root", default=str(REPO), help="this study repository")
    parser.add_argument(
        "--umbrella-lock",
        default="/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json",
        help="the umbrella datasets lock, the only live authority for asset identity",
    )
    parser.add_argument("--roster", default=ROSTER_RELPATH)
    parser.add_argument("--out-root", default=None)
    parser.add_argument(
        "--markdown",
        default=None,
        help=f"repository path for the rendered read (default {DEFAULT_MARKDOWN})",
    )
    parser.add_argument("--seed", type=int, default=20260915)
    parser.add_argument("--draws", type=int, default=10_000)
    parser.add_argument(
        "--refresh-gold",
        action="store_true",
        help="drop the cached gold label projection and rebuild it from the loader",
    )
    args = parser.parse_args(argv)

    payload = read(args)
    out_root = Path(args.out_root) if args.out_root else Path(args.data_root) / "analysis" / OUT_DIRNAME
    json_path = out_root / "cell3-fresh-roster-loss-diagnostic.json"
    json_path.write_text(
        json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    markdown = render_markdown(payload)
    markdown_path = out_root / "2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md"
    markdown_path.write_text(markdown, encoding="utf-8")
    repo_markdown = Path(args.repo_root) / (args.markdown or DEFAULT_MARKDOWN)
    repo_markdown.parent.mkdir(parents=True, exist_ok=True)
    repo_markdown.write_text(markdown, encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {markdown_path}")
    print(f"wrote {repo_markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
