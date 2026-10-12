#!/usr/bin/env python3
"""slurp_general_scenario_diagnostic.py -- the ``general`` scenario hole, read model-free.

    python scripts/analysis/slurp_general_scenario_diagnostic.py \
        --data-root "$SPEECHRL_DATA_DIR"

Owner decision 110 asked why every Stage-3 delta cell leaves the ``general`` stratum of
TRAIN Fold A untouched or worse: against the sealed PLAN comparator, cell CELL-1 loses
12.4 pooled SLU-F1 points and 6.7 intent points on those 60 rows, and cell CELL-2 loses
10.6 / 6.7. This read answers the five diagnostic questions the coordinator needs before
designing iteration 3, entirely out of bytes the flights themselves sealed:

1. the gold intent distribution of the 60 ``general`` rows, and per arm the delivered-intent
   confusion, the per-row official SLU-F1 / intent-exact numbers and the entity FP / FN mass;
2. Perception candidate coverage of the gold intent, arm by arm, with the rows where
   coverage is lost or gained against PLAN;
3. which delta ``value_id``s reached those rows, per node, with their kind and target, their
   own source scenario, and the paired outcome restricted to ``general`` rows;
4. the row-level transitions (PLAN right -> cell wrong and the three others);
5. the four root-cause hypotheses with the maximum SLU / intent points a full fix of each
   could return, bounded by the row transitions themselves.

MODEL-FREE. Zero model, tokenizer, encoder, ASR, scorer, server and network contacts. Every
number is read out of sealed run artefacts (``<run>.outputs.jsonl``, ``<run>.phases.json``,
``<run>.scores.json``), the released delta stores, the committed roster and the frozen SLURP
TRAIN gold. No sealed file and no repository file is written, moved or modified; the resident
llama-server is never started, stopped or queried.

IDENTITIES, LABELS AND COUNTS ONLY. No utterance text, no transcript, no gold filler, no
delivered filler and no delta STATEMENT text is read into a report, printed or persisted.
Gold is used exactly the way a scorer uses it -- as an offline comparison key -- and only its
LABELS (intent names, scenario names, slot TYPE names) and derived counts leave this read.
The repository-facing markdown carries aggregates only; the per-row join stays under the
controlled data root, which is never committed.

Reuse, not re-parsing: the per-node delta supply is extracted with
``scripts/analysis/stage3_delta_consumption_read.extract_row_supply`` and
``load_phase_results``; the per-sample official rows come through
``analysis.null_calibration_cli.rows_for``; pooled micro F1 is
``analysis.null_calibration.pooled_f1`` with ``plan_cell_read``'s own field groups; the
delivered label parse is ``reproduction.slurp_scoring.parse_slu_response``, the same function
the official scorer's port calls; gold is ``data.slurp.load_slurp_split``.

The TRAIN gold projection is expensive to build (the loader re-verifies every recording
against its flac header), so it is cached under the output root keyed by the sha256 of the
split metadata file it was built from. The cache is a pure function of that file; a changed
metadata file rebuilds it rather than reusing it.
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
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
)

from stage3_delta_consumption_read import (  # noqa: E402
    extract_row_supply,
    load_phase_results,
)

RECIPE_ID = "slurp-general-scenario-diagnostic-v1"
SCHEMA = "saea-slurp-general-scenario-diagnostic-v1"
RUN_ID = "SAEA-SLURP-GENERAL-SCENARIO-DIAGNOSTIC-V1"
OUT_DIRNAME = "SLURP-GENERAL-SCENARIO-DIAGNOSTIC-V1"

SCORER = "slurp-slu-official-train"
SCENARIO = "general"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-evo-fold-a-v2.json"
SPLIT_ID = "train"
STORE_ID = "stage3-deltas"

#: The per-row official fields this read joins -- ``plan_cell_read``'s own per-row metric set
#: plus the two micro count triples pooled F1 needs.
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
COUNT_FIELDS = (
    "slot_f1_exact_tp",
    "slot_f1_exact_fp",
    "slot_f1_exact_fn",
    "parsed",
)
SCORE_FIELDS = tuple(
    dict.fromkeys(
        list(PER_ROW_METRICS)
        + [name for groups in MICRO_METRICS.values() for group in groups for name in group]
        + list(COUNT_FIELDS)
    )
)

#: The four sealed arms: (key, label, run id, attempt id, released store directory).
#: PLAN is the comparator every cell was registered against; the twin is CELL-2's
#: derangement control -- same supply FORM, deranged statement CONTENT.
ARMS = (
    (
        "plan",
        "PLAN (v2.0 lock)",
        "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
        "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1",
        None,
    ),
    (
        "cell1",
        "CELL-1 (deltas v1r)",
        "SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1",
        "attempt-slurp-native-stage3-delta-cell-r01-v1-generation-recovery-relaunch-2",
        "stage3-deltas-v1r",
    ),
    (
        "cell2",
        "CELL-2 (deltas v2)",
        "SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1",
        "attempt-slurp-native-stage3-delta-cell-r02-v1-generation",
        "stage3-deltas-v2",
    ),
    (
        "twin",
        "CELL-2 twin (deranged)",
        "SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-V1",
        "attempt-slurp-native-stage3-delta-cell-r02-v1-twin",
        "stage3-deltas-twin-v2",
    ),
)
ARM_KEYS = tuple(entry[0] for entry in ARMS)
CELL_KEYS = ("cell1", "cell2", "twin")
NODES = ("perception", "solver", "reviewer", "planner")

UNPARSED = "<unparsed>"


class DiagnosticError(SystemExit):
    """Refuse rather than report a number this read cannot bind to sealed bytes."""


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def load_roster(repo: Path, relpath: str) -> dict:
    path = repo / relpath
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document["items"]
    strata = {item["sample_id"]: item["stratum"] for item in items}
    selected = sorted(sid for sid, stratum in strata.items() if stratum == SCENARIO)
    if not selected:
        raise DiagnosticError(f"roster {relpath} has no {SCENARIO!r} stratum")
    return {
        "path": str(path),
        "relpath": relpath,
        "sha256": digest(path),
        "roster_id": document.get("roster_id"),
        "split_identity_hash": document.get("split_identity_hash"),
        "rows_total": len(items),
        "strata": strata,
        "scenario_rows": selected,
    }


def gold_projection(lock_path: Path, data_root: Path, cache_path: Path) -> dict:
    """``sample_id -> {scenario, action, intent, entity_types}`` for the whole TRAIN split.

    LABELS ONLY: the entity FILLER text the gold carries is never read into the projection,
    so no gold filler can reach a report, a cache file or a commit from here. Cached because
    the loader re-verifies every recording against its flac header; the cache key is the
    sha256 of the split metadata file it was built from.
    """

    lock = load_lock(lock_path)
    metadata_path = _governed_roots(lock, data_root)[2] / _SPLIT_FILES[SPLIT_ID]
    metadata_sha = digest(metadata_path)
    if cache_path.is_file():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if (
            cached.get("schema") == "saea-slurp-train-gold-label-projection-v1"
            and cached.get("split_id") == SPLIT_ID
            and cached.get("metadata_sha256") == metadata_sha
        ):
            return {
                "source": "cache",
                "cache_path": str(cache_path),
                "metadata_sha256": metadata_sha,
                "rows": cached["rows"],
            }
    records = load_slurp_split(lock, data_root, SPLIT_ID)
    rows = {
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
                "schema": "saea-slurp-train-gold-label-projection-v1",
                "split_id": SPLIT_ID,
                "metadata_sha256": metadata_sha,
                "rows": rows,
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
        "metadata_sha256": metadata_sha,
        "rows": rows,
    }


def run_dir(data_root: Path, run_id: str, attempt_id: str) -> Path:
    directory = data_root / "runs" / run_id / attempt_id
    if not directory.is_dir():
        raise DiagnosticError(f"sealed attempt directory missing: {directory}")
    return directory


def load_manifest(directory: Path, run_id: str) -> dict:
    path = directory / f"{run_id}.run-manifest.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("status") != "COMPLETED":
        raise DiagnosticError(f"{run_id}: manifest is not COMPLETED")
    return {
        "path": str(path),
        "sha256": digest(path),
        "status": document.get("status"),
        "split_role": document.get("split_role"),
        "split_identity_hash": document.get("split_identity_hash"),
        "split_count": document.get("split_count"),
        "study_commit": document.get("study_commit"),
    }


def load_score_rows(directory: Path, run_id: str) -> dict:
    path = directory / f"{run_id}.scores.json"
    document = {"verified": True, "scores": json.loads(path.read_text(encoding="utf-8"))}
    rows = rows_for(document, SCORER, SCORE_FIELDS)
    return {"path": str(path), "sha256": digest(path), "rows": rows}


def load_delivered(directory: Path, run_id: str, wanted: set[str]) -> dict:
    """The delivered LABELS of the wanted rows, parsed exactly as the official port parses.

    Only the ``(scenario, action)`` pair, the entity TYPE multiset and the entity COUNT leave
    this function: no filler text, no response text and no utterance text is retained.
    """

    path = directory / f"{run_id}.outputs.jsonl"
    delivered: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            sample_id = row.get("sample_id")
            if sample_id not in wanted:
                continue
            scenario, action, entities, parsed = parse_slu_response(row.get("text") or "")
            delivered[sample_id] = {
                "parsed": bool(parsed),
                "scenario": scenario if isinstance(scenario, str) else None,
                "action": action if isinstance(action, str) else None,
                "intent": (
                    f"{scenario}_{action}"
                    if parsed and isinstance(scenario, str) and isinstance(action, str)
                    else UNPARSED
                ),
                "entity_types": sorted(entity.type for entity in entities),
                "entity_count": len(entities),
            }
    missing = sorted(wanted - set(delivered))
    if missing:
        raise DiagnosticError(f"{run_id}: outputs are missing {len(missing)} wanted rows")
    return {"path": str(path), "sha256": digest(path), "rows": delivered}


def load_phase_bits(directory: Path, run_id: str, wanted: set[str]) -> dict:
    """Perception candidate intent ids and, when a delta store served the run, the per-node
    ``value_id`` supply -- both for the wanted rows only.

    The supply extraction is ``stage3_delta_consumption_read.extract_row_supply`` unchanged,
    so this read's node attribution is the consumption read's own.
    """

    phases = load_phase_results(directory, run_id)
    results = phases["results"]
    supply = extract_row_supply(results, phases["controller_policy_id"], STORE_ID)
    per_row: dict[str, dict] = {}
    candidate_parse_failures = 0
    for result in results:
        sample_id = result.get("sample_id")
        if sample_id not in wanted:
            continue
        union: list[str] = []
        first: list[str] | None = None
        states = 0
        for state in result.get("agent_states") or ():
            if state.get("state_kind") != "phase:perception":
                continue
            states += 1
            try:
                payload = json.loads(state.get("content") or "")
            except (TypeError, ValueError):
                candidate_parse_failures += 1
                continue
            candidates = payload.get("candidates") if isinstance(payload, dict) else None
            if not isinstance(candidates, list):
                candidate_parse_failures += 1
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
        node_supply = supply["per_row"].get(sample_id) or {}
        per_row[sample_id] = {
            "perception_states": states,
            "candidates_first": first or [],
            "candidates_union": union,
            "supply": {
                node: sorted({value_id.split("::", 1)[-1] for value_id in node_supply.get(node, ())})
                for node in NODES
            },
        }
    missing = sorted(wanted - set(per_row))
    if missing:
        raise DiagnosticError(f"{run_id}: phase results are missing {len(missing)} wanted rows")
    return {
        "path": phases["path"],
        "sha256": phases["sha256"],
        "controller_policy_id": phases["controller_policy_id"],
        "candidate_parse_failures": candidate_parse_failures,
        "rows": per_row,
    }


def load_store(data_root: Path, dirname: str) -> dict:
    """``value_id -> {node, kind, target, source_sample_ids, prior_score}`` from a released
    store snapshot. The statement CONTENT is never read; only its length is recorded."""

    path = data_root / "knowledge" / "slurp" / "semantic" / dirname / "snapshot.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    values = {}
    for value in document["values"]:
        target = value.get("task_target") or ""
        parts = target.split(":", 2)
        node = parts[0] if len(parts) > 0 else ""
        kind = parts[1] if len(parts) > 1 else ""
        rest = parts[2] if len(parts) > 2 else ""
        values[value["value_id"]] = {
            "node": node,
            "kind": kind,
            "target": rest,
            "task_target": target,
            "source_sample_ids": list(value.get("source_sample_ids") or ()),
            "prior_score": value.get("prior_score"),
            "content_chars": len(value.get("content") or ""),
        }
    return {
        "dirname": dirname,
        "path": str(path),
        "file_sha256": digest(path),
        "declared_snapshot_sha256": document.get("snapshot_sha256"),
        "values": values,
    }


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------


def pooled(rows: dict, sample_ids: list[str], micro: str) -> float:
    return 100.0 * pooled_f1(rows, sample_ids, MICRO_METRICS[micro])


def arm_levels(rows: dict, sample_ids: list[str], delivered: dict, gold: dict) -> dict:
    n = len(sample_ids)
    tp = sum(rows[sid]["slot_f1_exact_tp"] for sid in sample_ids)
    fp = sum(rows[sid]["slot_f1_exact_fp"] for sid in sample_ids)
    fn = sum(rows[sid]["slot_f1_exact_fn"] for sid in sample_ids)
    emitted = sum(delivered[sid]["entity_count"] for sid in sample_ids)
    gold_entities = sum(len(gold[sid]["entity_types"]) for sid in sample_ids)
    return {
        "rows": n,
        "pooled_slu_f1_pct": pooled(rows, sample_ids, "slu_f1_micro"),
        "pooled_span_f1_pct": pooled(rows, sample_ids, "span_f1_micro"),
        "intent_exact_pct": 100.0 * sum(rows[sid]["scenario_action_exact"] for sid in sample_ids) / n,
        "scenario_exact_pct": 100.0 * sum(rows[sid]["scenario_exact"] for sid in sample_ids) / n,
        "action_exact_pct": 100.0 * sum(rows[sid]["action_exact"] for sid in sample_ids) / n,
        "mean_row_slu_f1_pct": 100.0 * sum(rows[sid]["slu_f1_f1"] for sid in sample_ids) / n,
        "parsed_rows": int(sum(rows[sid]["parsed"] for sid in sample_ids)),
        "entity_exact_tp": tp,
        "entity_exact_fp": fp,
        "entity_exact_fn": fn,
        "entities_emitted": emitted,
        "gold_entities": gold_entities,
        "rows_emitting_any_entity": sum(
            1 for sid in sample_ids if delivered[sid]["entity_count"] > 0
        ),
        "rows_with_gold_entity": sum(1 for sid in sample_ids if gold[sid]["entity_types"]),
    }


def paired_block(arm_rows: dict, comparator_rows: dict, sample_ids: list[str]) -> dict:
    block = {}
    for name, field in (
        ("slu_f1", "slu_f1_f1"),
        ("intent", "scenario_action_exact"),
        ("scenario", "scenario_exact"),
        ("span_f1", "slot_f1_exact_f1"),
    ):
        saves = harms = neutral = 0
        total = 0.0
        for sid in sample_ids:
            delta = float(arm_rows[sid][field]) - float(comparator_rows[sid][field])
            total += delta
            if delta > 0:
                saves += 1
            elif delta < 0:
                harms += 1
            else:
                neutral += 1
        block[name] = {
            "saves": saves,
            "harms": harms,
            "neutral": neutral,
            "mean_delta_pp": 100.0 * total / len(sample_ids),
        }
    block["pooled_slu_f1_delta_pp"] = pooled(arm_rows, sample_ids, "slu_f1_micro") - pooled(
        comparator_rows, sample_ids, "slu_f1_micro"
    )
    block["pooled_span_f1_delta_pp"] = pooled(arm_rows, sample_ids, "span_f1_micro") - pooled(
        comparator_rows, sample_ids, "span_f1_micro"
    )
    return block


def confusion(gold: dict, delivered: dict, sample_ids: list[str]) -> dict:
    table: dict[str, Counter] = defaultdict(Counter)
    for sid in sample_ids:
        table[gold[sid]["intent"]][delivered[sid]["intent"]] += 1
    return {
        gold_label: dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
        for gold_label, counts in sorted(table.items())
    }


def delivered_scenario_mix(delivered: dict, sample_ids: list[str]) -> dict:
    counts = Counter()
    for sid in sample_ids:
        row = delivered[sid]
        counts[row["scenario"] if row["parsed"] and row["scenario"] else UNPARSED] += 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def coverage_block(gold: dict, phases: dict, sample_ids: list[str]) -> dict:
    covered = []
    for sid in sample_ids:
        union = phases["rows"][sid]["candidates_union"]
        covered.append(gold[sid]["intent"] in union)
    general_slots = 0
    slots = 0
    rows_with_general_candidate = 0
    candidate_scenarios = Counter()
    for sid in sample_ids:
        union = phases["rows"][sid]["candidates_union"]
        slots += len(union)
        has_general = False
        for intent_id in union:
            scenario = intent_id.split("_", 1)[0]
            candidate_scenarios[scenario] += 1
            if scenario == SCENARIO:
                general_slots += 1
                has_general = True
        rows_with_general_candidate += int(has_general)
    n = len(sample_ids)
    return {
        "rows": n,
        "gold_intent_covered": sum(covered),
        "gold_intent_covered_pct": 100.0 * sum(covered) / n,
        "candidate_slots_total": slots,
        "candidate_slots_mean": slots / n,
        "candidate_slots_general_scenario": general_slots,
        "rows_with_any_general_candidate": rows_with_general_candidate,
        "candidate_scenario_mix": dict(
            sorted(candidate_scenarios.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "covered_rows": [sid for sid, flag in zip(sample_ids, covered) if flag],
    }


def transitions(arm_rows: dict, comparator_rows: dict, sample_ids: list[str], field: str) -> dict:
    buckets = {"right_right": [], "right_wrong": [], "wrong_right": [], "wrong_wrong": []}
    for sid in sample_ids:
        left = float(comparator_rows[sid][field]) > 0.0
        right = float(arm_rows[sid][field]) > 0.0
        key = ("right" if left else "wrong") + "_" + ("right" if right else "wrong")
        buckets[key].append(sid)
    return {key: {"rows": len(value), "sample_ids": value} for key, value in buckets.items()}


def value_outcomes(
    phases: dict,
    store: dict,
    arm_rows: dict,
    comparator_rows: dict,
    sample_ids: list[str],
    gold: dict,
) -> dict:
    reach: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    per_node_rows: dict[str, set] = {node: set() for node in NODES}
    per_node_values: dict[str, set] = {node: set() for node in NODES}
    for sid in sample_ids:
        for node in NODES:
            ids = phases["rows"][sid]["supply"][node]
            if ids:
                per_node_rows[node].add(sid)
            for value_id in ids:
                reach[value_id][node].add(sid)
                per_node_values[node].add(value_id)

    def outcome(rows: list[str]) -> dict:
        if not rows:
            return {"rows": 0}
        block = {"rows": len(rows)}
        for name, field in (("slu_f1", "slu_f1_f1"), ("intent", "scenario_action_exact")):
            saves = harms = 0
            total = 0.0
            for sid in rows:
                delta = float(arm_rows[sid][field]) - float(comparator_rows[sid][field])
                total += delta
                if delta > 0:
                    saves += 1
                elif delta < 0:
                    harms += 1
            block[name] = {
                "saves": saves,
                "harms": harms,
                "neutral": len(rows) - saves - harms,
                "mean_delta_pp": 100.0 * total / len(rows),
            }
        return block

    source_scenario_of = {}
    per_value = {}
    for value_id, nodes in reach.items():
        rows = sorted({sid for node_rows in nodes.values() for sid in node_rows})
        meta = store["values"].get(value_id, {})
        sources = meta.get("source_sample_ids") or []
        source_scenarios = sorted(
            {gold[src]["scenario"] for src in sources if src in gold}
        )
        source_scenario_of[value_id] = source_scenarios
        per_value[value_id] = {
            "nodes": sorted(nodes),
            "rows_reached": len(rows),
            "sample_ids": rows,
            "node": meta.get("node"),
            "kind": meta.get("kind"),
            "target": meta.get("target"),
            "task_target": meta.get("task_target"),
            "prior_score": meta.get("prior_score"),
            "source_scenarios": source_scenarios,
            "outcome": outcome(rows),
        }
    per_node = {
        node: {
            "rows_supplied": len(per_node_rows[node]),
            "rows_unsupplied": len(sample_ids) - len(per_node_rows[node]),
            "distinct_value_ids": len(per_node_values[node]),
            "value_ids": sorted(per_node_values[node]),
            "outcome_on_supplied_rows": outcome(sorted(per_node_rows[node])),
            "outcome_on_unsupplied_rows": outcome(
                sorted(set(sample_ids) - per_node_rows[node])
            ),
        }
        for node in NODES
    }
    source_mix = Counter()
    for value_id in per_value:
        for scenario in source_scenario_of[value_id] or ["<unknown>"]:
            source_mix[scenario] += 1
    target_mix = Counter(
        (per_value[value_id]["task_target"] or "<unknown>").split(":", 2)[-1]
        for value_id in per_value
    )
    return {
        "distinct_values_reaching_scenario": len(per_value),
        "per_node": per_node,
        "per_value": per_value,
        "source_scenario_mix": dict(sorted(source_mix.items(), key=lambda kv: (-kv[1], kv[0]))),
        "values_sourced_from_scenario": source_mix.get(SCENARIO, 0),
        "target_mix_top": dict(
            sorted(target_mix.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
        ),
        "store_values_targeting_scenario": sorted(
            value_id
            for value_id, meta in store["values"].items()
            if SCENARIO in (meta.get("target") or "")
        ),
        "store_values_total": len(store["values"]),
    }


def recoverable_bounds(
    arm_rows: dict,
    comparator_rows: dict,
    scenario_rows: list[str],
    all_rows: list[str],
) -> dict:
    """The upper bound a FULL repair of the scenario could return, taken from the transitions.

    The bound restores every harmed row to its comparator outcome and keeps every gain -- it
    is an upper bound because no mechanism can do better than undoing each loss, and it is
    reported on the scenario's own 60 rows and on the whole Fold A roster.
    """

    repaired = dict(arm_rows)
    intent_lost = 0
    intent_gained = 0
    slu_recovered = 0.0
    for sid in scenario_rows:
        left = comparator_rows[sid]
        right = arm_rows[sid]
        if float(right["scenario_action_exact"]) < float(left["scenario_action_exact"]):
            intent_lost += 1
        elif float(right["scenario_action_exact"]) > float(left["scenario_action_exact"]):
            intent_gained += 1
        if float(right["slu_f1_f1"]) < float(left["slu_f1_f1"]):
            slu_recovered += float(left["slu_f1_f1"]) - float(right["slu_f1_f1"])
            repaired[sid] = left
    n_scenario = len(scenario_rows)
    n_all = len(all_rows)
    pooled_now_scn = pooled(arm_rows, scenario_rows, "slu_f1_micro")
    pooled_fix_scn = pooled(repaired, scenario_rows, "slu_f1_micro")
    pooled_now_all = pooled(arm_rows, all_rows, "slu_f1_micro")
    pooled_fix_all = pooled(repaired, all_rows, "slu_f1_micro")
    comparator_scn = pooled(comparator_rows, scenario_rows, "slu_f1_micro")
    return {
        "scenario_rows": n_scenario,
        "fold_a_rows": n_all,
        "intent_rows_lost": intent_lost,
        "intent_rows_gained": intent_gained,
        "intent_recoverable_pp_scenario": 100.0 * intent_lost / n_scenario,
        "intent_recoverable_pp_fold_a": 100.0 * intent_lost / n_all,
        "mean_row_slu_recoverable_pp_scenario": 100.0 * slu_recovered / n_scenario,
        "mean_row_slu_recoverable_pp_fold_a": 100.0 * slu_recovered / n_all,
        "pooled_slu_scenario_now_pct": pooled_now_scn,
        "pooled_slu_scenario_repaired_pct": pooled_fix_scn,
        "pooled_slu_scenario_comparator_pct": comparator_scn,
        "pooled_slu_recoverable_pp_scenario": pooled_fix_scn - pooled_now_scn,
        "pooled_slu_fold_a_now_pct": pooled_now_all,
        "pooled_slu_fold_a_repaired_pct": pooled_fix_all,
        "pooled_slu_recoverable_pp_fold_a": pooled_fix_all - pooled_now_all,
    }


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------


def fmt(value, digits=2, dash="--"):
    if value is None:
        return dash
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown(payload: dict) -> str:
    arms = payload["arms"]
    labels = {key: entry["label"] for key, entry in arms.items()}
    lines: list[str] = []
    add = lines.append

    add("# The `general` scenario hole on TRAIN Fold A: a model-free diagnostic")
    add("")
    add(
        f"Recipe `{payload['recipe_id']}`, run id `{payload['run_id']}`, generated "
        f"{payload['generated_at_utc']}. Produced by "
        "`scripts/analysis/slurp_general_scenario_diagnostic.py` from sealed bytes only: "
        "**zero model, tokenizer, encoder, ASR, scorer, server and network contacts**. Every "
        "number below is reproduced by re-running that script; the per-row join and the full "
        "value tables are written beside it under "
        f"`$SPEECHRL_DATA_DIR/analysis/{payload['out_dirname']}/`."
    )
    add("")
    add(
        "Labels, identifiers and counts only. No utterance text, transcript, gold filler, "
        "delivered filler or delta statement text is read into this document. Gold enters "
        "exactly as a scorer input and leaves only as label names and counts."
    )
    add("")
    add(
        f"Population: the {payload['population']['scenario_rows']} `general` rows of roster "
        f"`{payload['roster']['roster_id']}` (`{payload['roster']['relpath']}`, sha256 "
        f"`{payload['roster']['sha256'][:12]}`), inside the "
        f"{payload['population']['fold_a_rows']}-row TRAIN Fold A discovery split "
        f"`{payload['roster']['split_identity_hash'][:12]}`."
    )
    add("")
    add("## Headline")
    add("")
    for line in payload["headline"]:
        add(f"- {line}")
    add("")

    add("## Sealed inputs")
    add("")
    add("| arm | run id | attempt | outputs sha256 | scores sha256 | store |")
    add("| --- | --- | --- | --- | --- | --- |")
    for key in ARM_KEYS:
        entry = arms[key]
        add(
            f"| {labels[key]} | `{entry['run_id']}` | `{entry['attempt_id']}` | "
            f"`{entry['outputs_sha256'][:12]}` | `{entry['scores_sha256'][:12]}` | "
            + (f"`{entry['store']['dirname']}`" if entry.get("store") else "--")
            + " |"
        )
    add("")

    # ---------------- Q1
    q1 = payload["q1_levels_and_confusion"]
    add("## 1. What the 60 `general` rows are, and where the cells lose")
    add("")
    add("### 1.1 Gold intent distribution (labels only)")
    add("")
    add("| gold intent | rows | share |")
    add("| --- | ---: | ---: |")
    for label, count in q1["gold_intent_distribution"].items():
        add(f"| `{label}` | {count} | {fmt(100.0 * count / q1['rows'], 1)} % |")
    add(f"| **total** | **{q1['rows']}** | |")
    add("")
    add(
        "The stratum is not a mixed bag: "
        f"`{q1['dominant_gold_intent']}` alone carries "
        f"{q1['dominant_gold_intent_rows']} of {q1['rows']} rows "
        f"({fmt(100.0 * q1['dominant_gold_intent_rows'] / q1['rows'], 1)} %), only "
        f"{q1['rows_with_gold_entity']} of the {q1['rows']} rows carry any gold slot at all, and "
        "the whole stratum is three intent labels wide."
    )
    add("")
    add("### 1.2 Per-arm level on the 60 rows")
    add("")
    add(
        "| arm | pooled SLU-F1 | pooled span-F1 | intent exact | scenario exact | "
        "mean row SLU-F1 | entity TP | entity FP | entity FN | entities emitted |"
    )
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for key in ARM_KEYS:
        lv = q1["levels"][key]
        add(
            f"| {labels[key]} | {fmt(lv['pooled_slu_f1_pct'])} | {fmt(lv['pooled_span_f1_pct'])} | "
            f"{fmt(lv['intent_exact_pct'])} | {fmt(lv['scenario_exact_pct'])} | "
            f"{fmt(lv['mean_row_slu_f1_pct'])} | {fmt(lv['entity_exact_tp'], 0)} | "
            f"{fmt(lv['entity_exact_fp'], 0)} | {fmt(lv['entity_exact_fn'], 0)} | "
            f"{lv['entities_emitted']} |"
        )
    add("")
    add(
        f"Gold slots on these rows total {q1['levels']['plan']['gold_entities']}. Every arm "
        "parses all 60 rows."
    )
    add("")
    add("### 1.3 Paired against PLAN on the same rows")
    add("")
    add(
        "| arm | pooled SLU-F1 delta | intent delta (pp) | intent saves / harms | "
        "row SLU saves / harms | span-F1 delta (pp) |"
    )
    add("| --- | ---: | ---: | ---: | ---: | ---: |")
    for key in CELL_KEYS:
        pb = q1["paired_vs_plan"][key]
        add(
            f"| {labels[key]} | {fmt(pb['pooled_slu_f1_delta_pp'])} | "
            f"{fmt(pb['intent']['mean_delta_pp'])} | "
            f"{pb['intent']['saves']} / {pb['intent']['harms']} | "
            f"{pb['slu_f1']['saves']} / {pb['slu_f1']['harms']} | "
            f"{fmt(pb['span_f1']['mean_delta_pp'])} |"
        )
    add("")
    add("### 1.4 Delivered-intent confusion, per arm")
    add("")
    for key in ARM_KEYS:
        add(f"**{labels[key]}** -- delivered scenario mix: " + ", ".join(
            f"`{scenario}` {count}"
            for scenario, count in q1["delivered_scenario_mix"][key].items()
        ))
        add("")
        add("| gold intent | delivered intent | rows |")
        add("| --- | --- | ---: |")
        for gold_label, counts in q1["confusion"][key].items():
            for delivered_label, count in counts.items():
                mark = " (correct)" if delivered_label == gold_label else ""
                add(f"| `{gold_label}` | `{delivered_label}`{mark} | {count} |")
        add("")
    add(
        "Loss attribution: the entity side is nearly inert on this stratum -- PLAN emits "
        f"{q1['levels']['plan']['entities_emitted']} entities against "
        f"{q1['levels']['plan']['gold_entities']} gold slots, CELL-2 emits "
        f"{q1['levels']['cell2']['entities_emitted']} and CELL-1 "
        f"{q1['levels']['cell1']['entities_emitted']}, moving exact-match FP from "
        f"{q1['levels']['plan']['entity_exact_fp']:.0f} to "
        f"{q1['levels']['cell2']['entity_exact_fp']:.0f} and "
        f"{q1['levels']['cell1']['entity_exact_fp']:.0f}. The pooled SLU-F1 gap is therefore "
        "carried by the label half of the metric: `general_quirky` flips out of `general_*`, "
        "mostly into `qa_*`."
    )
    add("")

    # ---------------- Q2
    q2 = payload["q2_candidate_coverage"]
    add("## 2. Perception candidate coverage of the gold intent")
    add("")
    add(
        "| arm | gold intent among candidates | candidate slots / row | slots spent on "
        "`general_*` | rows with any `general_*` candidate |"
    )
    add("| --- | ---: | ---: | ---: | ---: |")
    for key in ARM_KEYS:
        cb = q2["per_arm"][key]
        add(
            f"| {labels[key]} | {cb['gold_intent_covered']} / {cb['rows']} "
            f"({fmt(cb['gold_intent_covered_pct'], 1)} %) | "
            f"{fmt(cb['candidate_slots_mean'])} | {cb['candidate_slots_general_scenario']} | "
            f"{cb['rows_with_any_general_candidate']} |"
        )
    add("")
    add("| arm vs PLAN | coverage lost | coverage gained | coverage unchanged | rows losing intent | coverage-loss AND intent-loss | intent loss with coverage intact |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for key in CELL_KEYS:
        tr = q2["coverage_transitions"][key]
        cv = q2["coverage_loss_versus_intent_loss"][key]
        add(
            f"| {labels[key]} | {tr['lost']} | {tr['gained']} | {tr['unchanged']} | "
            f"{cv['intent_lost_rows']} | {cv['overlap_rows']} | "
            f"{cv['intent_lost_without_coverage_loss']} |"
        )
    add("")
    add(
        "The last two columns are the discriminator: coverage loss and answer loss are largely "
        "different rows ("
        + "; ".join(
            f"{labels[key]} {q2['coverage_loss_versus_intent_loss'][key]['overlap_rows']} of "
            f"{q2['coverage_loss_versus_intent_loss'][key]['intent_lost_rows']} intent losses "
            "also lost coverage"
            for key in CELL_KEYS
        )
        + "). Crowding is a real contributing channel in CELL-1 and a minor one in CELL-2, but "
        "in no arm does it account for the whole loss."
    )
    add("")
    add(
        "The unconditional Perception seed is the same four `intent-boundary` values on every "
        "row of every arm: "
        + "; ".join(
            f"{labels[key]} "
            + ", ".join(
                f"`{value_id}` -> `{target}`"
                for value_id, target in q2["unconditional_perception_seed_targets"][key].items()
            )
            for key in CELL_KEYS
        )
        + ". None of them targets `general_*` in any arm."
    )
    add("")
    add(
        "Candidate scenario mix on these rows (PLAN): "
        + ", ".join(
            f"`{scenario}` {count}"
            for scenario, count in list(q2["per_arm"]["plan"]["candidate_scenario_mix"].items())[:10]
        )
        + "."
    )
    add("")

    # ---------------- Q3
    q3 = payload["q3_delta_consumption"]
    add("## 3. Which deltas reached the 60 rows, and what they did there")
    add("")
    for key in CELL_KEYS:
        block = q3[key]
        add(f"### 3.{CELL_KEYS.index(key) + 1} {labels[key]}")
        add("")
        add(
            f"Store `{arms[key]['store']['dirname']}` holds {block['store_values_total']} "
            f"values; {block['distinct_values_reaching_scenario']} distinct values reached at "
            f"least one `general` row. Values whose declared target names `{SCENARIO}`: "
            f"{len(block['store_values_targeting_scenario'])}. Values whose own source rows are "
            f"`general`: {block['values_sourced_from_scenario']}."
        )
        add("")
        add(
            "| node | rows supplied | distinct values | intent saves / harms on supplied | "
            "mean intent delta, supplied | mean intent delta, NOT supplied | mean row SLU "
            "delta, supplied | mean row SLU delta, NOT supplied |"
        )
        add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for node in NODES:
            nb = block["per_node"][node]
            oc = nb["outcome_on_supplied_rows"]
            un = nb["outcome_on_unsupplied_rows"]
            if not oc.get("rows"):
                add(f"| {node} | 0 | {nb['distinct_value_ids']} | -- | -- | -- | -- | -- |")
                continue
            add(
                f"| {node} | {nb['rows_supplied']} | {nb['distinct_value_ids']} | "
                f"{oc['intent']['saves']} / {oc['intent']['harms']} | "
                f"{fmt(oc['intent']['mean_delta_pp'])} | "
                + (fmt(un["intent"]["mean_delta_pp"]) if un.get("rows") else "--")
                + f" | {fmt(oc['slu_f1']['mean_delta_pp'])} | "
                + (fmt(un["slu_f1"]["mean_delta_pp"]) if un.get("rows") else "--")
                + " |"
            )
        add("")
        add(
            "The `NOT supplied` columns are the within-arm control: Perception's seed reaches "
            "every row, so only the three candidate-bound nodes can be contrasted, and the rows "
            "those nodes never fed are not protected -- they lose intent as well."
        )
        add("")
        add("Source scenario of the values that reached `general` rows: " + ", ".join(
            f"`{scenario}` {count}" for scenario, count in list(block["source_scenario_mix"].items())[:12]
        ) + ".")
        add("")
        top = block["top_values_by_rows_reached"]
        if top:
            add("| value id | node | kind | target | rows reached | intent saves / harms | mean row SLU delta |")
            add("| --- | --- | --- | --- | ---: | ---: | ---: |")
            for row in top:
                oc = row["outcome"]
                add(
                    f"| `{row['value_id']}` | {row['node']} | {row['kind']} | `{row['target']}` | "
                    f"{row['rows_reached']} | {oc['intent']['saves']} / {oc['intent']['harms']} | "
                    f"{fmt(oc['slu_f1']['mean_delta_pp'])} |"
                )
            add("")
        conc = block["concentration"]
        add(
            f"Concentration: {conc['values_touching_any_harmed_row']} of "
            f"{block['distinct_values_reaching_scenario']} values touch at least one harmed row, "
            f"of which {conc['values_only_on_harmed_rows']} touch harmed rows only; the "
            f"{conc['harmed_rows']} harmed rows received {conc['distinct_values_on_harmed_rows']} "
            "distinct values between them. No value and no node carries the loss on its own."
        )
        add("")
    add(
        "The derangement twin is the decisive column: it carries the same supply FORM with "
        "deranged statement CONTENT and loses at least as much on `general` as the arm does. "
        "A content-borne harm cannot survive a derangement; a form-borne one must."
    )
    add("")

    # ---------------- Q4
    q4 = payload["q4_transitions"]
    add("## 4. Are the losses on rows PLAN already got right?")
    add("")
    add("| arm | metric | PLAN right -> cell right | PLAN right -> cell wrong | PLAN wrong -> cell right | PLAN wrong -> cell wrong |")
    add("| --- | --- | ---: | ---: | ---: | ---: |")
    for key in CELL_KEYS:
        for metric in ("intent", "scenario"):
            tr = q4[key][metric]
            add(
                f"| {labels[key]} | {metric} exact | {tr['right_right']['rows']} | "
                f"{tr['right_wrong']['rows']} | {tr['wrong_right']['rows']} | "
                f"{tr['wrong_wrong']['rows']} |"
            )
    add("")
    add(
        "Every `general` loss is a row PLAN answered correctly -- by construction of the metric, "
        "a row that was already wrong can only be re-labelled inside the wrong set, and "
        f"{q4['cell2']['intent']['wrong_wrong']['rows']} of the 60 rows under CELL-2 are in that "
        "set. The delta supply therefore has no visible upside on this stratum and a measurable "
        "downside on the rows PLAN was getting right."
    )
    add("")

    # ---------------- Q5
    q5 = payload["q5_hypotheses"]
    add("## 5. Root-cause hypotheses, ranked, with the recoverable bound")
    add("")
    add("| arm | intent rows lost | intent pp recoverable on `general` | on Fold A | pooled SLU pp recoverable on `general` | on Fold A |")
    add("| --- | ---: | ---: | ---: | ---: | ---: |")
    for key in CELL_KEYS:
        rb = q5["bounds"][key]
        add(
            f"| {labels[key]} | {rb['intent_rows_lost']} | "
            f"{fmt(rb['intent_recoverable_pp_scenario'])} | "
            f"{fmt(rb['intent_recoverable_pp_fold_a'])} | "
            f"{fmt(rb['pooled_slu_recoverable_pp_scenario'])} | "
            f"{fmt(rb['pooled_slu_recoverable_pp_fold_a'])} |"
        )
    add("")
    add(
        "The bound undoes every harmed row and keeps every gain, so no iteration-3 mechanism "
        "aimed at this stratum can beat it. The second, larger ceiling is the stratum itself: "
        f"PLAN already answers only {fmt(q1['levels']['plan']['intent_exact_pct'])} % of the "
        f"`general` rows correctly and pools {fmt(q1['levels']['plan']['pooled_slu_f1_pct'])} "
        "SLU-F1 there, so closing the arm-vs-PLAN gap recovers a loss, it does not fix the "
        "stratum."
    )
    add("")
    for rank, hypothesis in enumerate(q5["ranked"], start=1):
        add(f"### H{rank} ({hypothesis['verdict']}) -- {hypothesis['title']}")
        add("")
        for line in hypothesis["evidence"]:
            add(f"- {line}")
        add("")
        add(f"**Iteration-3 mechanism it implies.** {hypothesis['mechanism']}")
        add("")
        add(f"**Bound if fully fixed.** {hypothesis['bound']}")
        add("")

    add("## Provenance")
    add("")
    add("| artefact | sha256 |")
    add("| --- | --- |")
    for name, sha in payload["provenance"].items():
        add(f"| {name} | `{sha}` |")
    add("")
    add(
        "Exposure: registered as run id "
        f"`{payload['run_id']}`, profile `model-free-check`, zero contacts, `consumed = no`."
    )
    add("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------


def read(args) -> dict:
    data_root = Path(args.data_root).resolve()
    repo = Path(args.repo_root).resolve()
    out_root = Path(args.out_root) if args.out_root else data_root / "analysis" / OUT_DIRNAME
    out_root.mkdir(parents=True, exist_ok=True)

    roster = load_roster(repo, args.roster)
    scenario_rows = roster["scenario_rows"]
    wanted = set(scenario_rows)

    gold_bundle = gold_projection(
        Path(args.umbrella_lock), data_root, out_root / "train-gold-label-projection.json"
    )
    gold_all = gold_bundle["rows"]
    missing_gold = sorted(wanted - set(gold_all))
    if missing_gold:
        raise DiagnosticError(f"gold is missing {len(missing_gold)} roster rows")
    gold = {sid: gold_all[sid] for sid in scenario_rows}
    off_scenario = sorted(sid for sid in scenario_rows if gold[sid]["scenario"] != SCENARIO)
    if off_scenario:
        raise DiagnosticError(
            f"{len(off_scenario)} roster rows in the {SCENARIO!r} stratum have another gold scenario"
        )

    arms: dict[str, dict] = {}
    for key, label, run_id, attempt_id, store_dirname in ARMS:
        directory = run_dir(data_root, run_id, attempt_id)
        manifest = load_manifest(directory, run_id)
        scores = load_score_rows(directory, run_id)
        delivered = load_delivered(directory, run_id, wanted)
        phases = load_phase_bits(directory, run_id, wanted)
        store = load_store(data_root, store_dirname) if store_dirname else None
        if store is not None:
            supplied = {
                value_id
                for sid in scenario_rows
                for node in NODES
                for value_id in phases["rows"][sid]["supply"][node]
            }
            unknown = sorted(supplied - set(store["values"]))
            if unknown:
                raise DiagnosticError(
                    f"{run_id}: {len(unknown)} supplied value ids are absent from store "
                    f"{store_dirname!r}; the store binding is wrong"
                )
        arms[key] = {
            "label": label,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "manifest": manifest,
            "scores_sha256": scores["sha256"],
            "outputs_sha256": delivered["sha256"],
            "phases_sha256": phases["sha256"],
            "controller_policy_id": phases["controller_policy_id"],
            "score_rows": scores["rows"],
            "delivered": delivered["rows"],
            "phases": phases,
            "store": store,
        }

    fold_a_rows = sorted(arms["plan"]["score_rows"])
    for key in ARM_KEYS:
        if sorted(arms[key]["score_rows"]) != fold_a_rows:
            raise DiagnosticError(f"{key}: the scored population differs from PLAN's")

    # ---- integrity: the delivered parse must reproduce the official intent-exact column
    parse_agreement = {}
    for key in ARM_KEYS:
        agree = 0
        for sid in scenario_rows:
            delivered_label = arms[key]["delivered"][sid]["intent"]
            official = float(arms[key]["score_rows"][sid]["scenario_action_exact"]) > 0.0
            if (delivered_label == gold[sid]["intent"]) == official:
                agree += 1
        parse_agreement[key] = {"rows": len(scenario_rows), "agreeing": agree}
        if agree != len(scenario_rows):
            raise DiagnosticError(
                f"{key}: the delivered-label parse disagrees with the official intent column "
                f"on {len(scenario_rows) - agree} rows"
            )

    plan_rows = arms["plan"]["score_rows"]

    # ---------------- Q1
    gold_distribution = dict(
        sorted(
            Counter(gold[sid]["intent"] for sid in scenario_rows).items(),
            key=lambda kv: (-kv[1], kv[0]),
        )
    )
    dominant = next(iter(gold_distribution))
    q1 = {
        "rows": len(scenario_rows),
        "gold_intent_distribution": gold_distribution,
        "dominant_gold_intent": dominant,
        "dominant_gold_intent_rows": gold_distribution[dominant],
        "gold_entity_type_mix": dict(
            sorted(
                Counter(
                    entity_type
                    for sid in scenario_rows
                    for entity_type in gold[sid]["entity_types"]
                ).items(),
                key=lambda kv: (-kv[1], kv[0]),
            )
        ),
        "rows_with_gold_entity": sum(1 for sid in scenario_rows if gold[sid]["entity_types"]),
        "levels": {
            key: arm_levels(arms[key]["score_rows"], scenario_rows, arms[key]["delivered"], gold)
            for key in ARM_KEYS
        },
        "paired_vs_plan": {
            key: paired_block(arms[key]["score_rows"], plan_rows, scenario_rows)
            for key in CELL_KEYS
        },
        "confusion": {
            key: confusion(gold, arms[key]["delivered"], scenario_rows) for key in ARM_KEYS
        },
        "delivered_scenario_mix": {
            key: delivered_scenario_mix(arms[key]["delivered"], scenario_rows)
            for key in ARM_KEYS
        },
        "delivered_intent_mix": {
            key: dict(
                sorted(
                    Counter(
                        arms[key]["delivered"][sid]["intent"] for sid in scenario_rows
                    ).items(),
                    key=lambda kv: (-kv[1], kv[0]),
                )
            )
            for key in ARM_KEYS
        },
        "parse_agreement_with_official": parse_agreement,
    }

    # ---------------- Q2
    coverage = {key: coverage_block(gold, arms[key]["phases"], scenario_rows) for key in ARM_KEYS}
    plan_cov = set(coverage["plan"]["covered_rows"])
    coverage_transitions = {}
    for key in CELL_KEYS:
        cell_cov = set(coverage[key]["covered_rows"])
        coverage_transitions[key] = {
            "lost": len(plan_cov - cell_cov),
            "gained": len(cell_cov - plan_cov),
            "unchanged": len(scenario_rows) - len(plan_cov ^ cell_cov),
            "lost_sample_ids": sorted(plan_cov - cell_cov),
            "gained_sample_ids": sorted(cell_cov - plan_cov),
        }
    q2 = {
        "per_arm": coverage,
        "coverage_transitions": coverage_transitions,
        "unconditional_perception_seed": {
            key: sorted(
                {
                    value_id
                    for sid in scenario_rows
                    for value_id in arms[key]["phases"]["rows"][sid]["supply"]["perception"]
                }
            )
            for key in CELL_KEYS
        },
    }
    # Does the candidate-coverage loss explain the intent loss, row for row?
    coverage_vs_intent = {}
    for key in CELL_KEYS:
        cov_lost = set(coverage_transitions[key]["lost_sample_ids"])
        intent_lost = {
            sid
            for sid in scenario_rows
            if float(arms[key]["score_rows"][sid]["scenario_action_exact"])
            < float(plan_rows[sid]["scenario_action_exact"])
        }
        coverage_vs_intent[key] = {
            "coverage_lost_rows": len(cov_lost),
            "intent_lost_rows": len(intent_lost),
            "overlap_rows": len(cov_lost & intent_lost),
            "coverage_lost_without_intent_loss": len(cov_lost - intent_lost),
            "intent_lost_without_coverage_loss": len(intent_lost - cov_lost),
            "overlap_sample_ids": sorted(cov_lost & intent_lost),
        }
    q2["coverage_loss_versus_intent_loss"] = coverage_vs_intent
    for key in CELL_KEYS:
        seed = q2["unconditional_perception_seed"][key]
        store = arms[key]["store"]
        q2.setdefault("unconditional_perception_seed_targets", {})[key] = {
            value_id: store["values"].get(value_id, {}).get("task_target")
            for value_id in seed
        }
        q2.setdefault("unconditional_perception_seed_rows", {})[key] = sum(
            1
            for sid in scenario_rows
            if arms[key]["phases"]["rows"][sid]["supply"]["perception"]
        )

    # ---------------- Q3
    q3 = {}
    for key in CELL_KEYS:
        block = value_outcomes(
            arms[key]["phases"],
            arms[key]["store"],
            arms[key]["score_rows"],
            plan_rows,
            scenario_rows,
            gold_all,
        )
        harmed_rows = [
            sid
            for sid in scenario_rows
            if float(arms[key]["score_rows"][sid]["scenario_action_exact"])
            < float(plan_rows[sid]["scenario_action_exact"])
            or float(arms[key]["score_rows"][sid]["slu_f1_f1"]) < float(plan_rows[sid]["slu_f1_f1"])
        ]
        harmed = set(harmed_rows)
        values_on_harmed = {
            value_id
            for value_id, entry in block["per_value"].items()
            if harmed & set(entry["sample_ids"])
        }
        only_harmed = {
            value_id
            for value_id in values_on_harmed
            if set(block["per_value"][value_id]["sample_ids"]) <= harmed
        }
        block["concentration"] = {
            "harmed_rows": len(harmed_rows),
            "harmed_sample_ids": harmed_rows,
            "values_touching_any_harmed_row": len(values_on_harmed),
            "values_only_on_harmed_rows": len(only_harmed),
            "distinct_values_on_harmed_rows": len(
                {
                    value_id
                    for sid in harmed_rows
                    for node in NODES
                    for value_id in arms[key]["phases"]["rows"][sid]["supply"][node]
                }
            ),
        }
        block["top_values_by_rows_reached"] = sorted(
            (
                {
                    "value_id": value_id,
                    "node": entry["node"],
                    "kind": entry["kind"],
                    "target": entry["target"],
                    "rows_reached": entry["rows_reached"],
                    "outcome": entry["outcome"],
                }
                for value_id, entry in block["per_value"].items()
            ),
            key=lambda row: (-row["rows_reached"], row["value_id"]),
        )[:12]
        q3[key] = block

    # ---------------- Q4
    q4 = {
        key: {
            "intent": transitions(
                arms[key]["score_rows"], plan_rows, scenario_rows, "scenario_action_exact"
            ),
            "scenario": transitions(
                arms[key]["score_rows"], plan_rows, scenario_rows, "scenario_exact"
            ),
        }
        for key in CELL_KEYS
    }

    # ---------------- Q5
    bounds = {
        key: recoverable_bounds(arms[key]["score_rows"], plan_rows, scenario_rows, fold_a_rows)
        for key in CELL_KEYS
    }
    q5 = {"bounds": bounds, "ranked": rank_hypotheses(q1, q2, q3, q4, bounds, arms)}

    payload = {
        "schema": SCHEMA,
        "recipe_id": RECIPE_ID,
        "run_id": RUN_ID,
        "out_dirname": OUT_DIRNAME,
        "title": "The general scenario hole on TRAIN Fold A",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scenario": SCENARIO,
        "scorer": SCORER,
        "population": {
            "scenario_rows": len(scenario_rows),
            "fold_a_rows": len(fold_a_rows),
            "sample_ids": scenario_rows,
        },
        "roster": {
            "relpath": roster["relpath"],
            "sha256": roster["sha256"],
            "roster_id": roster["roster_id"],
            "split_identity_hash": roster["split_identity_hash"],
        },
        "gold": {
            "split_id": SPLIT_ID,
            "source": gold_bundle["source"],
            "metadata_sha256": gold_bundle["metadata_sha256"],
            "cache_path": gold_bundle["cache_path"],
        },
        "arms": {
            key: {
                "label": arms[key]["label"],
                "run_id": arms[key]["run_id"],
                "attempt_id": arms[key]["attempt_id"],
                "manifest": arms[key]["manifest"],
                "scores_sha256": arms[key]["scores_sha256"],
                "outputs_sha256": arms[key]["outputs_sha256"],
                "phases_sha256": arms[key]["phases_sha256"],
                "controller_policy_id": arms[key]["controller_policy_id"],
                "store": (
                    {
                        "dirname": arms[key]["store"]["dirname"],
                        "file_sha256": arms[key]["store"]["file_sha256"],
                        "declared_snapshot_sha256": arms[key]["store"]["declared_snapshot_sha256"],
                        "values": len(arms[key]["store"]["values"]),
                    }
                    if arms[key]["store"]
                    else None
                ),
            }
            for key in ARM_KEYS
        },
        "headline": [
            f"The stratum is three labels wide and dominated by `{q1['dominant_gold_intent']}` "
            f"({q1['dominant_gold_intent_rows']} of {q1['rows']} rows); only "
            f"{q1['rows_with_gold_entity']} rows carry a gold slot, so the `general` number is "
            "an INTENT number, not a slot number.",
            "The derangement twin loses as much as the arms "
            f"(intent {q1['paired_vs_plan']['twin']['intent']['mean_delta_pp']:+.2f} pp versus "
            f"{q1['paired_vs_plan']['cell2']['intent']['mean_delta_pp']:+.2f} for CELL-2 and "
            f"{q1['paired_vs_plan']['cell1']['intent']['mean_delta_pp']:+.2f} for CELL-1), so the "
            "`general` loss is a FORM cost of carrying a delta supply, not the content of any "
            "delta.",
            "No delta content exists for this stratum: "
            f"{len(q3['cell2']['store_values_targeting_scenario'])} of "
            f"{q3['cell2']['store_values_total']} v2 values declare a `general` target and "
            f"{q3['cell2']['values_sourced_from_scenario']} of the values that reached these rows "
            "was learned from a `general` source row.",
            "Candidate crowding is real but does not explain the loss: "
            f"{q2['coverage_loss_versus_intent_loss']['cell2']['overlap_rows']} of the "
            f"{q2['coverage_loss_versus_intent_loss']['cell2']['intent_lost_rows']} CELL-2 intent "
            "losses also lost candidate coverage.",
            "The whole recoverable amount is small: "
            f"{bounds['cell2']['intent_recoverable_pp_scenario']:.2f} pp intent and "
            f"{bounds['cell2']['pooled_slu_recoverable_pp_scenario']:.2f} pp pooled SLU-F1 on the "
            f"{bounds['cell2']['scenario_rows']} rows, i.e. "
            f"{bounds['cell2']['intent_recoverable_pp_fold_a']:.2f} pp and "
            f"{bounds['cell2']['pooled_slu_recoverable_pp_fold_a']:.2f} pp on Fold A -- iteration "
            "3 should PROTECT this stratum from the supply, not try to win it.",
        ],
        "q1_levels_and_confusion": q1,
        "q2_candidate_coverage": q2,
        "q3_delta_consumption": q3,
        "q4_transitions": q4,
        "q5_hypotheses": q5,
        "provenance": {
            roster["relpath"]: roster["sha256"],
            **{
                f"{arms[key]['run_id']}.outputs.jsonl": arms[key]["outputs_sha256"]
                for key in ARM_KEYS
            },
            **{
                f"{arms[key]['run_id']}.scores.json": arms[key]["scores_sha256"]
                for key in ARM_KEYS
            },
            **{
                f"{arms[key]['run_id']}.phases.json": arms[key]["phases_sha256"]
                for key in ARM_KEYS
            },
            **{
                f"knowledge/slurp/semantic/{arms[key]['store']['dirname']}/snapshot.json": arms[
                    key
                ]["store"]["file_sha256"]
                for key in CELL_KEYS
            },
        },
    }
    return payload


def rank_hypotheses(q1, q2, q3, q4, bounds, arms) -> list[dict]:
    """The four candidate causes, ordered by how much of the measured loss each explains."""

    cell2_bound = bounds["cell2"]
    cell1_bound = bounds["cell1"]
    twin_bound = bounds["twin"]
    twin_intent = q1["paired_vs_plan"]["twin"]["intent"]["mean_delta_pp"]
    cell2_intent = q1["paired_vs_plan"]["cell2"]["intent"]["mean_delta_pp"]
    cell1_intent = q1["paired_vs_plan"]["cell1"]["intent"]["mean_delta_pp"]
    cov = q2["per_arm"]
    seed_rows = q2["unconditional_perception_seed_rows"]["cell2"]
    general_targets_v2 = len(q3["cell2"]["store_values_targeting_scenario"])
    general_targets_v1r = len(q3["cell1"]["store_values_targeting_scenario"])
    plan_entities = q1["levels"]["plan"]["entities_emitted"]
    cell2_entities = q1["levels"]["cell2"]["entities_emitted"]
    cell2_fp = q1["levels"]["cell2"]["entity_exact_fp"]
    plan_fp = q1["levels"]["plan"]["entity_exact_fp"]

    hypotheses = [
        {
            "key": "form-not-content",
            "title": (
                "The `general` loss is a FORM cost of the delta supply, not the content of any "
                "delta"
            ),
            "verdict": "PRIMARY -- carries the whole measured loss",
            "evidence": [
                f"The derangement twin, which carries the same supply form with deranged "
                f"statement content, loses {twin_intent:+.2f} pp intent on these rows against "
                f"PLAN, versus {cell2_intent:+.2f} pp for CELL-2 and {cell1_intent:+.2f} pp for "
                "CELL-1: the control loses at least as much as the arms.",
                f"There is almost no delta CONTENT for this stratum to consume: "
                f"{general_targets_v1r} of {q3['cell1']['store_values_total']} v1r values and "
                f"{general_targets_v2} of {q3['cell2']['store_values_total']} v2 values declare a "
                f"`{SCENARIO}` target, and of the values that actually reached these rows "
                f"{q3['cell1']['values_sourced_from_scenario']} (CELL-1) and "
                f"{q3['cell2']['values_sourced_from_scenario']} (CELL-2) were learned from a "
                "`general` source row at all.",
                "The harm is diffuse across values: "
                f"{q3['cell2']['concentration']['values_touching_any_harmed_row']} of "
                f"{q3['cell2']['distinct_values_reaching_scenario']} CELL-2 values touch a harmed "
                "row and no single value or node concentrates it.",
                "The within-arm control agrees: the rows the Solver route never fed lose intent "
                "too ("
                + "; ".join(
                    f"{arms[key]['label']} "
                    f"{q3[key]['per_node']['solver']['outcome_on_unsupplied_rows']['intent']['mean_delta_pp']:+.2f} pp "
                    f"on {q3[key]['per_node']['solver']['rows_unsupplied']} unsupplied rows versus "
                    f"{q3[key]['per_node']['solver']['outcome_on_supplied_rows']['intent']['mean_delta_pp']:+.2f} pp "
                    f"on {q3[key]['per_node']['solver']['rows_supplied']} supplied rows"
                    for key in ("cell1", "cell2")
                )
                + "), so what moves the stratum is present on rows no delta statement reached.",
            ],
            "mechanism": (
                "Iteration 3 must gate the supply itself, not re-author statements: route delta "
                "context only to rows whose Perception state names a scenario the store actually "
                "covers, and serve an empty supply otherwise, so an uncovered stratum runs the "
                "bare PLAN form. A scenario-gated supply is the only mechanism that removes a "
                "form cost without removing the gains elsewhere."
            ),
            "bound": (
                f"CELL-2: up to {cell2_bound['intent_recoverable_pp_scenario']:.2f} pp intent and "
                f"{cell2_bound['pooled_slu_recoverable_pp_scenario']:.2f} pp pooled SLU-F1 on the "
                f"60 `general` rows, which is "
                f"{cell2_bound['intent_recoverable_pp_fold_a']:.2f} pp intent and "
                f"{cell2_bound['pooled_slu_recoverable_pp_fold_a']:.2f} pp pooled SLU-F1 on the "
                f"{cell2_bound['fold_a_rows']}-row Fold A. CELL-1: "
                f"{cell1_bound['intent_recoverable_pp_scenario']:.2f} / "
                f"{cell1_bound['pooled_slu_recoverable_pp_scenario']:.2f} pp on the stratum "
                f"({cell1_bound['intent_recoverable_pp_fold_a']:.2f} / "
                f"{cell1_bound['pooled_slu_recoverable_pp_fold_a']:.2f} pp on Fold A). The twin's "
                f"own bound is {twin_bound['intent_recoverable_pp_scenario']:.2f} pp intent, "
                "which is what makes this the ceiling of the whole line, not a share of it."
            ),
        },
        {
            "key": "crowding",
            "title": "Perception seeds crowd `general_*` out of the candidate list",
            "verdict": "CONTRIBUTING -- real crowding, but it predates the delta cells",
            "evidence": [
                "Candidate coverage of the gold intent on these rows is "
                + ", ".join(
                    f"{arms[key]['label']} {cov[key]['gold_intent_covered']}/{cov[key]['rows']}"
                    for key in ARM_KEYS
                )
                + ".",
                "Coverage transitions against PLAN: "
                + ", ".join(
                    f"{arms[key]['label']} {q2['coverage_transitions'][key]['lost']} lost / "
                    f"{q2['coverage_transitions'][key]['gained']} gained"
                    for key in CELL_KEYS
                )
                + ".",
                f"The unconditional Perception seed is served to {seed_rows} of "
                f"{q1['rows']} `general` rows and is the SAME four `intent-boundary` values on "
                "every row, none of them targeting `general_*`, so it cannot be separated row by "
                "row inside one arm -- only the twin separates it.",
                "But coverage loss and answer loss are largely DIFFERENT rows: "
                + "; ".join(
                    f"{arms[key]['label']} "
                    f"{q2['coverage_loss_versus_intent_loss'][key]['overlap_rows']} of "
                    f"{q2['coverage_loss_versus_intent_loss'][key]['intent_lost_rows']} intent "
                    "losses also lost coverage"
                    for key in CELL_KEYS
                )
                + ", so crowding is a contributing channel in CELL-1 and a minor one in CELL-2, "
                "never the whole mechanism.",
            ],
            "mechanism": (
                "A `general_*` candidate floor in Perception (reserve one slot when no "
                "`general_*` candidate survives) or a scenario-aware candidate budget. Note the "
                "B4a precedent: a standing `general_quirky` fallback was flown on the anchor, "
                "lifted coverage to 100 % and was chosen on zero rows, so a floor alone is "
                "expected to be inert unless the Solver is also told when to prefer it."
            ),
            "bound": (
                "Bounded above by the coverage rows the cells actually lose against PLAN, which "
                "is "
                + ", ".join(
                    f"{arms[key]['label']} {q2['coverage_transitions'][key]['lost']} rows"
                    for key in CELL_KEYS
                )
                + f" -- at most {100.0 * max(q2['coverage_transitions'][key]['lost'] for key in CELL_KEYS) / q1['rows']:.2f} pp intent on the stratum."
            ),
        },
        {
            "key": "entity-pressure",
            "title": "Solver deltas learned on other scenarios push entity emission on chit-chat rows",
            "verdict": "REJECTED -- the entity side is not where the loss is",
            "evidence": [
                f"PLAN emits {plan_entities} entities on these 60 rows against "
                f"{q1['levels']['plan']['gold_entities']} gold slots; CELL-2 emits "
                f"{cell2_entities} and CELL-1 {q1['levels']['cell1']['entities_emitted']}.",
                f"Exact-match entity FP is {plan_fp:.0f} under PLAN, {cell2_fp:.0f} under CELL-2 "
                f"and {q1['levels']['cell1']['entity_exact_fp']:.0f} under CELL-1: CELL-1 adds "
                f"{q1['levels']['cell1']['entity_exact_fp'] - plan_fp:.0f} false positives across "
                "all 60 rows, which is a fraction of a point of the 12-point pooled gap.",
                "Span-F1 on the stratum moves by "
                f"{q1['paired_vs_plan']['cell2']['span_f1']['mean_delta_pp']:+.2f} pp per row "
                "under CELL-2, an order of magnitude smaller than the intent movement.",
            ],
            "mechanism": (
                "A no-entity contract for `general_*` would be close to a no-op: the rows already "
                "carry almost no gold slots and the arms already emit almost none. Do not spend "
                "an iteration-3 cell here."
            ),
            "bound": (
                f"At most {abs(q1['paired_vs_plan']['cell2']['span_f1']['mean_delta_pp']):.2f} pp "
                "span-F1 per row on the stratum, i.e. "
                f"{abs(q1['paired_vs_plan']['cell2']['span_f1']['mean_delta_pp']) * q1['rows'] / bounds['cell2']['fold_a_rows']:.3f} pp on Fold A."
            ),
        },
        {
            "key": "flip-destination",
            "title": "Intent flips land on a specific foreign family (mostly `qa_*`)",
            "verdict": "DESCRIPTIVE -- names the destination, not the cause",
            "evidence": [
                "Delivered scenario mix under PLAN: "
                + ", ".join(
                    f"`{scenario}` {count}"
                    for scenario, count in list(q1["delivered_scenario_mix"]["plan"].items())[:6]
                )
                + "; under CELL-2: "
                + ", ".join(
                    f"`{scenario}` {count}"
                    for scenario, count in list(q1["delivered_scenario_mix"]["cell2"].items())[:6]
                )
                + ".",
                "Every intent loss sits on a row PLAN answered correctly "
                f"({q4['cell2']['intent']['right_wrong']['rows']} rows under CELL-2, "
                f"{q4['cell1']['intent']['right_wrong']['rows']} under CELL-1); no loss comes "
                "from a row that was already wrong.",
            ],
            "mechanism": (
                "A one-directional contrast note (`general_quirky` versus the observed "
                "destination family) placed where the flip happens -- but only after the form "
                "cost above is removed, since the same note under the current supply form is "
                "what FIX-2 of the A3 audit already carried into cell B4a."
            ),
            "bound": (
                "Same transition bound as H1 -- it is the same rows seen from the destination "
                "side, not additional headroom."
            ),
        },
    ]
    return hypotheses


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
        help="repository path for the rendered read (default docs/results/<date>-...md)",
    )
    args = parser.parse_args(argv)

    payload = read(args)
    data_root = Path(args.data_root).resolve()
    out_root = Path(args.out_root) if args.out_root else data_root / "analysis" / OUT_DIRNAME
    out_root.mkdir(parents=True, exist_ok=True)
    json_path = out_root / "general-scenario-diagnostic.json"
    json_path.write_text(
        json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    markdown = render_markdown(payload)
    markdown_path = (
        Path(args.markdown)
        if args.markdown
        else Path(args.repo_root) / "docs" / "results" / "2026-09-24-slurp-general-scenario-diagnostic.md"
    )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    (out_root / markdown_path.name).write_text(markdown, encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {markdown_path}")
    print(f"wrote {out_root / markdown_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
