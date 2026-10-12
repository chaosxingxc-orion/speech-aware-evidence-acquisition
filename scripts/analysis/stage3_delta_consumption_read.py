"""Per-node delta-consumption read for a sealed CELL-1-shaped run (item S3-4s).

    python scripts/analysis/stage3_delta_consumption_read.py \
        --run SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1 \
        --attempt attempt-slurp-native-stage3-delta-cell-r01-v1-generation-recovery \
        --comparator-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1 \
        --comparator-attempt attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1 \
        --analysis-root "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-R01-PAIRED-ANALYSIS-V1"

MODEL-FREE. Zero model / tokenizer / encoder / scorer / server / network contacts: every number
below is read out of bytes the flight itself sealed, plus the two sealed score files. The read
answers the preregistration's ``DELTA_CONSUMPTION`` clause (owner decision 99, item S3-4s):

* per node (perception / solver / reviewer / planner) -- the rows that received at least one delta,
  the items supplied per row against that node's cap, the distinct ``value_id``s supplied, and the
  rows the route skipped with the reason it receipted;
* per supplied ``value_id`` -- the rows it reached and, joined to the sealed per-sample official
  scores of this run and of the sealed comparator on the SAME rows, the saves / harms / neutral
  counts and the mean paired per-row SLU-F1 and intent deltas on exactly those rows;
* per scenario -- the same, aggregated;
* the first-occurrence projection events (duplicate Perception candidates) this route recorded.

IDENTITIES AND COUNTS ONLY. No utterance, gold, delivered or delta STATEMENT text is read,
printed or persisted: the read opens ``value_id``s, node targets, sample ids, content hashes and
numbers, exactly as the recipe's ``prints_only_aggregates`` clause requires.

The receipt fields this read binds, and nothing else:

``<run>.phases.json`` -> ``phases[0].results[]``
    ``sample_id``; ``initial_query_state.retrieved_value_ids`` (the UNCONDITIONAL Perception
    seed -- ``rails.knowledge_stores`` serves the S3-4s first-phase route through
    ``bootstrap_first_phase`` / ``unconditional_first_phase``, so it never appears as a
    transition); ``waves[].batch_id`` (``<policy>:<role>:<visit>:<sample_id>`` -- the role
    ordering); ``waves[].transition`` with ``action_kind``, ``action_target_refs`` and
    ``new_value_ids`` (the per-node supply: the second target ref is
    ``knowledge-store:<store_id>:stage3-delta-candidate-bound-v1:node=<node>:cap=<cap>`` when the
    store served that node alone, and the composite ref when the phase composed several supplies,
    in which case the receiving node is the NEXT wave's role).

``flight-receipts.json`` -> ``stages.run_phases.phase_supply``
    ``stores[<store_id>]`` -- ``store_role``, ``store_release_sha256``, ``store_snapshot_sha256``,
    ``composite_snapshot_sha256``, ``context_supply`` (the phases routed) and
    ``unconditional_context_supply`` {``provider``, ``node_target``, ``phase``, ``cap``,
    ``selected_value_ids``}: the flight-wide Perception seed, a pure function of the store;
    ``delta_supply`` -- the per-row SKIP receipts
    ``rails.knowledge_stores._record_delta_supply_skip`` writes, keyed
    ``<phase>:<sample_id>:<query_state_sha256>`` with {``node``, ``phase``, ``sample_id``,
    ``store_id``, ``selected``, ``already_acquired``, ``reason``};
    ``delta_candidate_projection`` -- the per-row first-occurrence projection audits
    ``_record_delta_candidate_projection`` writes under the same key shape with
    {``node``, ``phase``, ``sample_id``, ``store_id``, ``raw_positions``,
    ``retained_positions``, ``projection_policy_id``, ``projection_policy_sha256``,
    ``original_text_sha256``, ``projected_content_sha256``}. Both keys are published only when a
    stage3-deltas context route exists, so a run sealed before the projection fix carries
    ``delta_supply`` alone and this read reports the absence rather than failing.

``<run>.scores.json`` and the comparator's
    per-sample rows through ``analysis.null_calibration_cli.rows_for`` -- the same loader and the
    same scorer id the paired read uses, so the join is the paired read's own join.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.null_calibration_cli import rows_for  # noqa: E402
from speech_aware_evidence_acquisition.rails.stage3_delta_supply import (  # noqa: E402
    STAGE3_DELTA_SCENARIO_GATE_SKIP_REASON,
)

DATA = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
)

#: The native role graph's node order (``analysis.native_episode_dry_run.
#: NATIVE_ROLE_GRAPH_ORDER``). Perception is served by the unconditional first-phase route; the
#: other three by the candidate-bound per-node routes.
NODES = ("perception", "solver", "reviewer", "planner")

#: The per-row official metrics this read joins: the per-row SLU-F1 and the intent
#: (joint scenario+action) exactness, i.e. the decision rule's two guards at row grain.
SLU_FIELD = "slu_f1_f1"
INTENT_FIELD = "scenario_action_exact"
SCORE_FIELDS = (SLU_FIELD, INTENT_FIELD)
SCORER = "slurp-slu-official-train"

#: ``knowledge-store:<store_id>:<provider>:node=<node>:cap=<cap>`` -- the action target ref
#: ``rails.knowledge_stores._stage3_delta_local_supply`` builds for a node-filtered route.
NODE_REF = re.compile(
    r"^knowledge-store:(?P<store>[^:]+):(?P<provider>[^:]+):node=(?P<node>[^:]+):cap=(?P<cap>\d+)$"
)
#: The same route without a ``node_target`` (the pre-S3-4s single-node shape), kept so this read
#: can also be pointed at a run sealed before the per-node widening.
PLAIN_REF = re.compile(
    r"^knowledge-store:(?P<store>[^:]+):(?P<provider>[^:]+):cap=(?P<cap>\d+)$"
)


class ConsumptionError(SystemExit):
    """Refuse rather than report a number this read cannot bind to sealed bytes."""


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def run_dir(run_id: str, attempt_id: str) -> Path:
    return DATA / "runs" / run_id / attempt_id


def load_manifest(directory: Path, run_id: str, *, require_completed: bool) -> dict:
    path = directory / f"{run_id}.run-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("run_id") != run_id:
        raise ConsumptionError(f"{run_id}: manifest names another run")
    if require_completed and manifest.get("status") != "COMPLETED":
        raise ConsumptionError(f"{run_id}: manifest is not COMPLETED")
    if manifest.get("study_repo_dirt"):
        raise ConsumptionError(f"{run_id}: sealed with a dirty study tree")
    split = manifest.get("split") or {}
    return {
        "path": str(path),
        "sha256": digest(path),
        "status": manifest.get("status"),
        "study_commit": manifest.get("study_commit"),
        "split_identity_hash": split.get("identity_hash"),
        "split_role": split.get("role"),
        "split_count": split.get("count"),
        "scores_pin": (manifest.get("scores") or {}).get("sha256")
        if isinstance(manifest.get("scores"), dict)
        else None,
    }


def load_router_receipt(directory: Path, store_id: str) -> dict:
    """``stages.run_phases.phase_supply`` -- the named-knowledge-store routing receipt."""
    path = directory / "flight-receipts.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    supply = (((document.get("stages") or {}).get("run_phases") or {}).get("phase_supply") or {})
    if supply.get("schema") != "saea-named-knowledge-store-routing-v1":
        raise ConsumptionError("flight receipt carries no knowledge-store routing receipt")
    stores = supply.get("stores") or {}
    if store_id not in stores:
        raise ConsumptionError(f"flight receipt has no store {store_id!r}")
    store = stores[store_id]
    unconditional = store.get("unconditional_context_supply") or {}
    return {
        "path": str(path),
        "sha256": digest(path),
        "binding_sha256": supply.get("binding_sha256"),
        "store": {
            "store_id": store.get("store_id"),
            "store_role": store.get("store_role"),
            "store_release_sha256": store.get("store_release_sha256"),
            "store_snapshot_sha256": store.get("store_snapshot_sha256"),
            "store_source_sha256": store.get("store_source_sha256"),
            "composite_snapshot_sha256": store.get("composite_snapshot_sha256"),
            "context_supply_phases": sorted(store.get("context_supply") or []),
        },
        "unconditional": {
            "provider": unconditional.get("provider"),
            "node_target": unconditional.get("node_target"),
            "phase": unconditional.get("phase"),
            "cap": unconditional.get("cap"),
            "selected_value_ids": list(unconditional.get("selected_value_ids") or ()),
        },
        "delta_supply": supply.get("delta_supply"),
        "delta_candidate_projection": supply.get("delta_candidate_projection"),
    }


def load_phase_results(directory: Path, run_id: str) -> dict:
    path = directory / f"{run_id}.phases.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        document.get("schema") != "saea-flight-phase-summaries-v1"
        or document.get("run_id") != run_id
        or len(document.get("phases") or []) != 1
    ):
        raise ConsumptionError(f"{run_id}: phase artefact does not bind this one system")
    summary = document["phases"][0]
    return {
        "path": str(path),
        "sha256": digest(path),
        "controller_policy_id": summary.get("controller_policy_id"),
        "knowledge_snapshot_sha256": summary.get("knowledge_snapshot_sha256"),
        "results": summary["results"],
    }


def load_score_rows(directory: Path, run_id: str, scorer: str) -> dict | None:
    path = directory / f"{run_id}.scores.json"
    if not path.exists():
        return None
    document = {"verified": True, "scores": json.loads(path.read_text(encoding="utf-8"))}
    return {
        "path": str(path),
        "sha256": digest(path),
        "rows": rows_for(document, scorer, SCORE_FIELDS),
    }


def load_declared_routes(config_path, store_id: str) -> dict:
    """The REGISTERED per-node routes, read from the committed baseline fragment.

    The flight receipt names a node's cap only where the store served that node alone (the
    composite ref a multi-supply phase emits carries no ``cap=`` token), so the caps this read
    reports against come from the cell's own ``configs/baseline/...`` fragment --
    ``knowledge_stores[<store_id>].context_supply[<phase>]`` -- with the file's sha256 recorded
    and its release / snapshot pins checked against the flight receipt's.
    """
    path = Path(config_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    store = ((document.get("knowledge_stores") or {}).get(store_id)) or {}
    if not store:
        raise ConsumptionError(f"{path}: declares no knowledge store {store_id!r}")
    routes = {}
    caps = {}
    for phase, spec in sorted((store.get("context_supply") or {}).items()):
        if not isinstance(spec, dict):
            continue
        node = str(spec.get("node_target") or phase)
        routes[node] = {
            "phase": phase,
            "provider": spec.get("provider"),
            "cap": spec.get("cap"),
            "rank_by": spec.get("rank_by"),
            "candidate_state_phase": spec.get("candidate_state_phase"),
        }
        if spec.get("cap") is not None:
            caps[node] = int(spec["cap"])
    def _pin(block):
        return block.get("sha256") if isinstance(block, dict) else block

    return {
        "path": str(path),
        "sha256": digest(path),
        "store_role": store.get("store_role"),
        "release_relpath": (store.get("release") or {}).get("relpath")
        if isinstance(store.get("release"), dict)
        else None,
        "release_sha256": _pin(store.get("release")),
        "snapshot_relpath": (store.get("snapshot") or {}).get("relpath")
        if isinstance(store.get("snapshot"), dict)
        else None,
        "snapshot_sha256": _pin(store.get("snapshot")),
        "routes": routes,
        "caps": caps,
    }


def load_scenarios(relpath: str | None) -> dict:
    if not relpath:
        return {}
    path = DATA / relpath
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
    return {sid: entry.get("scenario") for sid, entry in rows.items()}


# --------------------------------------------------------------------------
# Per-row supply extraction
# --------------------------------------------------------------------------

def _role_of(batch_id, policy_id):
    """``<policy>:<role>:<visit>:<sample_id>`` -> ``<role>``."""
    if not isinstance(batch_id, str):
        return None
    rest = batch_id
    if policy_id and batch_id.startswith(policy_id + ":"):
        rest = batch_id[len(policy_id) + 1:]
    parts = rest.split(":")
    return parts[0] if parts and parts[0] else None


def _node_from_refs(refs, store_id: str):
    """The node target and cap a transition's own target refs name, when they name one."""
    for ref in refs or ():
        if not isinstance(ref, str):
            continue
        match = NODE_REF.match(ref)
        if match and match.group("store") == store_id:
            return match.group("node"), int(match.group("cap"))
        plain = PLAIN_REF.match(ref)
        if plain and plain.group("store") == store_id:
            return None, int(plain.group("cap"))
    return None, None


def extract_row_supply(results, policy_id, store_id: str) -> dict:
    """Per row, the delta ``value_id``s each node actually received.

    Perception's are the unconditional first-phase seed carried on
    ``initial_query_state.retrieved_value_ids``; every other node's are the ``new_value_ids`` of
    the transition that fed it, filtered to this store's qualified prefix.
    """
    prefix = f"{store_id}::"
    per_row: dict = {}
    caps: dict = {}
    node_label_disagreements: list = []
    unattributed = 0
    for result in results:
        sample_id = result["sample_id"]
        initial = result.get("initial_query_state") or {}
        seed = [
            value_id
            for value_id in (initial.get("retrieved_value_ids") or ())
            if isinstance(value_id, str) and value_id.startswith(prefix)
        ]
        supplied = {node: [] for node in NODES}
        supplied["perception"] = list(seed)
        waves = result.get("waves") or []
        roles = [_role_of(wave.get("batch_id"), policy_id) for wave in waves]
        for index, wave in enumerate(waves):
            transition = wave.get("transition")
            if not isinstance(transition, dict):
                continue
            new_ids = [
                value_id
                for value_id in (transition.get("new_value_ids") or ())
                if isinstance(value_id, str) and value_id.startswith(prefix)
            ]
            if not new_ids:
                continue
            ref_node, cap = _node_from_refs(transition.get("action_target_refs"), store_id)
            next_role = roles[index + 1] if index + 1 < len(roles) else None
            node = ref_node or next_role
            if ref_node and next_role and ref_node != next_role:
                node_label_disagreements.append(
                    {"sample_id": sample_id, "ref_node": ref_node, "next_role": next_role}
                )
            if cap is not None and node:
                caps[node] = cap
            if node is None:
                unattributed += len(new_ids)
                continue
            supplied.setdefault(node, []).extend(new_ids)
        per_row[sample_id] = supplied
    return {
        "per_row": per_row,
        "caps_from_refs": caps,
        "node_label_disagreements": node_label_disagreements,
        "unattributed_supplied_items": unattributed,
    }


#: The per-node skip block a node with NO skip receipt reports. Named once so the
#: fallback and the real block can never drift apart.
EMPTY_SKIP_BLOCK = {
    "skip_events": 0,
    "rows_skipped": 0,
    "reasons": {},
    "already_acquired_total": 0,
    "already_acquired_events": 0,
    "gated_events": 0,
    "gated_rows": 0,
    "gated_majority_scenarios": {},
}


def summarise_skips(delta_supply) -> dict:
    """The skip receipts, by node: events, distinct rows and the reason each route gave.

    Iteration 3 (2026-09-24) adds the GATE counts. A row-level scenario gate
    declines a node by taking no supply step at all, receipted through the very
    same ``delta_supply`` map with ``reason ==
    STAGE3_DELTA_SCENARIO_GATE_SKIP_REASON`` plus the majority scenario LABEL
    that closed it -- so the reason counter below already names it, and
    ``gated_rows`` separates "this node was WITHHELD on n rows" from "this node
    found nothing to give on n rows", which are different facts about a cell.
    """
    if not isinstance(delta_supply, dict):
        return {"published": False, "by_node": {}, "events": 0, "gated_events": 0}
    by_node: dict = {}
    for entry in delta_supply.values():
        if not isinstance(entry, dict):
            continue
        node = entry.get("node") or entry.get("phase") or "unknown"
        block = by_node.setdefault(
            node,
            {
                "skip_events": 0,
                "rows_skipped": set(),
                "reasons": Counter(),
                "already_acquired_total": 0,
                "already_acquired_events": 0,
                "gated_events": 0,
                "gated_rows": set(),
                "gated_majority_scenarios": Counter(),
            },
        )
        block["skip_events"] += 1
        block["rows_skipped"].add(entry.get("sample_id"))
        block["reasons"][str(entry.get("reason"))] += 1
        already = entry.get("already_acquired") or 0
        if already:
            block["already_acquired_total"] += int(already)
            block["already_acquired_events"] += 1
        if entry.get("reason") == STAGE3_DELTA_SCENARIO_GATE_SKIP_REASON:
            block["gated_events"] += 1
            block["gated_rows"].add(entry.get("sample_id"))
            block["gated_majority_scenarios"][str(entry.get("majority_scenario"))] += 1
    rendered = {
        node: {
            "skip_events": block["skip_events"],
            "rows_skipped": len(block["rows_skipped"]),
            "reasons": dict(sorted(block["reasons"].items())),
            "already_acquired_total": block["already_acquired_total"],
            "already_acquired_events": block["already_acquired_events"],
            "gated_events": block["gated_events"],
            "gated_rows": len(block["gated_rows"]),
            "gated_majority_scenarios": dict(
                sorted(block["gated_majority_scenarios"].items())
            ),
        }
        for node, block in sorted(by_node.items())
    }
    return {
        "published": True,
        "by_node": rendered,
        "events": sum(block["skip_events"] for block in rendered.values()),
        "gated_events": sum(block["gated_events"] for block in rendered.values()),
    }


def summarise_projection(audits) -> dict:
    """The first-occurrence projection audits: events, rows and positions dropped."""
    if audits is None:
        return {
            "published": False,
            "note": (
                "the flight receipt carries no delta_candidate_projection key: this run was "
                "sealed by a router build that predates the ARM projection audit"
            ),
            "events": 0,
            "rows": 0,
            "positions_dropped": 0,
            "by_node": {},
        }
    if not isinstance(audits, dict):
        raise ConsumptionError("delta_candidate_projection is malformed")
    rows = set()
    dropped = 0
    by_node = Counter()
    policies = Counter()
    for entry in audits.values():
        if not isinstance(entry, dict):
            continue
        rows.add(entry.get("sample_id"))
        raw = int(entry.get("raw_positions") or 0)
        retained = int(entry.get("retained_positions") or 0)
        dropped += max(raw - retained, 0)
        by_node[str(entry.get("node"))] += 1
        policies[str(entry.get("projection_policy_id"))] += 1
    return {
        "published": True,
        "events": len(audits),
        "rows": len(rows),
        "positions_dropped": dropped,
        "by_node": dict(sorted(by_node.items())),
        "projection_policy_ids": dict(sorted(policies.items())),
    }


# --------------------------------------------------------------------------
# The paired join
# --------------------------------------------------------------------------

def _outcome(arm_rows, comparator_rows, sample_ids) -> dict:
    """Saves / harms / neutral and the mean paired delta in pp, over exactly these rows."""
    block = {"rows_joined": 0}
    for name, field in (("slu_f1", SLU_FIELD), ("intent", INTENT_FIELD)):
        saves = harms = neutral = 0
        total = 0.0
        joined = 0
        for sample_id in sample_ids:
            left = comparator_rows.get(sample_id)
            right = arm_rows.get(sample_id)
            if left is None or right is None:
                continue
            delta = float(right[field]) - float(left[field])
            joined += 1
            total += delta
            if delta > 0:
                saves += 1
            elif delta < 0:
                harms += 1
            else:
                neutral += 1
        block["rows_joined"] = joined
        block[name] = {
            "saves": saves,
            "harms": harms,
            "neutral": neutral,
            "mean_delta_pp": (100.0 * total / joined) if joined else None,
        }
    return block


def build_consumption(
    *,
    supply: dict,
    skips: dict,
    projection: dict,
    unconditional: dict,
    arm_rows,
    comparator_rows,
    scenarios: dict,
    caps_override: dict,
) -> dict:
    per_row = supply["per_row"]
    caps = dict(supply["caps_from_refs"])
    if unconditional.get("cap") is not None and unconditional.get("node_target"):
        caps[str(unconditional["node_target"])] = int(unconditional["cap"])
    caps.update({node: int(cap) for node, cap in (caps_override or {}).items()})
    joinable = arm_rows is not None and comparator_rows is not None

    nodes_seen = (
        {node for row in per_row.values() for node in row}
        | set(NODES)
        | set(skips.get("by_node") or {})
    )
    ordered_nodes = [node for node in NODES if node in nodes_seen] + sorted(
        node for node in nodes_seen if node not in NODES
    )

    per_node: dict = {}
    value_rows = defaultdict(set)
    value_nodes = defaultdict(set)
    rows_with_any = set()
    for node in ordered_nodes:
        counts = []
        supplied_rows = []
        distinct = set()
        for sample_id, row in per_row.items():
            items = row.get(node) or []
            counts.append(len(items))
            if items:
                supplied_rows.append(sample_id)
                rows_with_any.add(sample_id)
                distinct.update(items)
                for value_id in items:
                    value_rows[value_id].add(sample_id)
                    value_nodes[value_id].add(node)
        cap = caps.get(node)
        histogram = Counter(counts)
        per_node[node] = {
            "cap": cap,
            "rows_total": len(per_row),
            "rows_supplied": len(supplied_rows),
            "rows_supplied_share": (len(supplied_rows) / len(per_row)) if per_row else None,
            "items_supplied_total": sum(counts),
            "items_per_row_mean": (sum(counts) / len(per_row)) if per_row else None,
            "items_per_supplied_row_mean": (
                (sum(counts) / len(supplied_rows)) if supplied_rows else None
            ),
            "items_per_row_histogram": {str(k): v for k, v in sorted(histogram.items())},
            "rows_at_full_cap": (histogram.get(cap, 0) if cap is not None else None),
            "distinct_value_ids": len(distinct),
            "distinct_value_id_list": sorted(distinct),
            "skips": (skips.get("by_node") or {}).get(node, dict(EMPTY_SKIP_BLOCK)),
            "route_is_inert": len(supplied_rows) == 0,
        }
        if joinable and supplied_rows:
            per_node[node]["outcome_on_supplied_rows"] = _outcome(
                arm_rows, comparator_rows, supplied_rows
            )

    per_value: dict = {}
    for value_id in sorted(value_rows):
        members = sorted(value_rows[value_id])
        entry = {
            "nodes": sorted(value_nodes[value_id]),
            "rows_reached": len(members),
        }
        if joinable:
            entry["outcome"] = _outcome(arm_rows, comparator_rows, members)
        per_value[value_id] = entry

    per_scenario: dict = {}
    if scenarios:
        by_scenario = defaultdict(list)
        for sample_id in per_row:
            by_scenario[str(scenarios.get(sample_id))].append(sample_id)
        for scenario, members in sorted(by_scenario.items()):
            block = {"rows_total": len(members), "nodes": {}}
            supplied_here = set()
            for node in ordered_nodes:
                counts = [len(per_row[sid].get(node) or []) for sid in members]
                rows_supplied = [sid for sid in members if per_row[sid].get(node)]
                supplied_here.update(rows_supplied)
                distinct = {
                    value_id for sid in rows_supplied for value_id in per_row[sid][node]
                }
                block["nodes"][node] = {
                    "rows_supplied": len(rows_supplied),
                    "items_supplied_total": sum(counts),
                    "items_per_row_mean": (sum(counts) / len(members)) if members else None,
                    "distinct_value_ids": len(distinct),
                }
            block["rows_supplied_any_node"] = len(supplied_here)
            if joinable:
                block["outcome_all_rows"] = _outcome(arm_rows, comparator_rows, members)
                if supplied_here:
                    block["outcome_on_supplied_rows"] = _outcome(
                        arm_rows, comparator_rows, sorted(supplied_here)
                    )
            per_scenario[scenario] = block

    summary = {
        "rows_total": len(per_row),
        "rows_supplied_any_node": len(rows_with_any),
        "distinct_value_ids_supplied": len(value_rows),
        "items_supplied_total": sum(
            block["items_supplied_total"] for block in per_node.values()
        ),
        "unconditional_seed_value_ids": len(unconditional.get("selected_value_ids") or ()),
        "skip_events": skips.get("events", 0),
        "gated_skip_events": skips.get("gated_events", 0),
        "projection_events": projection.get("events", 0),
        "inert_routes": [node for node, block in per_node.items() if block["route_is_inert"]],
        "score_join": "joined" if joinable else "not available",
    }
    if joinable:
        summary["outcome_all_rows"] = _outcome(arm_rows, comparator_rows, sorted(per_row))
        summary["outcome_on_supplied_rows"] = _outcome(
            arm_rows, comparator_rows, sorted(rows_with_any)
        )
    return {
        "summary": summary,
        "per_node": per_node,
        "per_value_id": per_value,
        "per_scenario": per_scenario,
        "projection": projection,
        "node_order": ordered_nodes,
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def _fmt(value, digits=3, dash="--"):
    if value is None:
        return dash
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown(payload: dict, *, max_value_rows: int) -> str:
    block = payload["consumption"]
    summary = block["summary"]
    lines = []
    lines.append(f"# {payload['title']}")
    lines.append("")
    lines.append(
        f"Model-free delta-consumption read of `{payload['run']['run_id']}` "
        f"(attempt `{payload['run']['attempt_id']}`), store `{payload['store_id']}` "
        f"(release sha256 `{payload['store']['store_release_sha256']}`, snapshot "
        f"`{payload['store']['store_snapshot_sha256']}`). "
        f"Generated {payload['generated_at_utc']}. Counts, ids and hashes only."
    )
    lines.append("")
    lines.append("## 1. Summary")
    lines.append("")
    lines.append("| item | value |")
    lines.append("| --- | ---: |")
    for key in (
        "rows_total",
        "rows_supplied_any_node",
        "items_supplied_total",
        "distinct_value_ids_supplied",
        "unconditional_seed_value_ids",
        "skip_events",
        "gated_skip_events",
        "projection_events",
    ):
        lines.append(f"| {key} | {_fmt(summary.get(key))} |")
    lines.append(f"| inert routes | {', '.join(summary['inert_routes']) or 'none'} |")
    lines.append(f"| score join | {summary['score_join']} |")
    lines.append("")
    lines.append("## 2. Per node")
    lines.append("")
    lines.append(
        "| node | cap | rows supplied | share | items | items / supplied row | at full cap "
        "| distinct value ids | skip events | rows skipped | gated rows |"
    )
    lines.append(
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for node in block["node_order"]:
        entry = block["per_node"][node]
        skips = entry["skips"]
        lines.append(
            f"| {node} | {_fmt(entry['cap'], 0)} | {entry['rows_supplied']} "
            f"| {_fmt(entry['rows_supplied_share'])} | {entry['items_supplied_total']} "
            f"| {_fmt(entry['items_per_supplied_row_mean'])} "
            f"| {_fmt(entry['rows_at_full_cap'], 0)} | {entry['distinct_value_ids']} "
            f"| {skips.get('skip_events', 0)} | {skips.get('rows_skipped', 0)} "
            f"| {skips.get('gated_rows', 0)} |"
        )
    lines.append("")
    # Iteration 3: WHICH strata the gate actually withheld, per node. Labels and
    # counts only, and printed only where a gate closed at all -- a run of an
    # ungated cell renders exactly what it always did.
    gate_lines = []
    for node in block["node_order"]:
        scenarios = block["per_node"][node]["skips"].get("gated_majority_scenarios") or {}
        if scenarios:
            gate_lines.append(
                f"- {node} gate closed on majority scenario: "
                + "; ".join(
                    f"{scenario} = {count}" for scenario, count in sorted(scenarios.items())
                )
            )
    if gate_lines:
        lines.extend(gate_lines)
        lines.append("")
    reason_lines = []
    for node in block["node_order"]:
        reasons = block["per_node"][node]["skips"].get("reasons") or {}
        if reasons:
            reason_lines.append(
                f"- {node} skip reasons: "
                + "; ".join(f"{reason} = {count}" for reason, count in sorted(reasons.items()))
            )
    if reason_lines:
        lines.extend(reason_lines)
        lines.append("")
    outcome_rows = [
        (node, block["per_node"][node].get("outcome_on_supplied_rows"))
        for node in block["node_order"]
    ]
    if any(entry for _, entry in outcome_rows):
        lines.append("### 2a. Paired outcome on the rows each node supplied")
        lines.append("")
        lines.append(
            "| node | rows | SLU saves | SLU harms | SLU neutral | SLU mean delta pp "
            "| intent saves | intent harms | intent neutral | intent mean delta pp |"
        )
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for node, entry in outcome_rows:
            if not entry:
                continue
            slu = entry["slu_f1"]
            intent = entry["intent"]
            lines.append(
                f"| {node} | {entry['rows_joined']} | {slu['saves']} | {slu['harms']} "
                f"| {slu['neutral']} | {_fmt(slu['mean_delta_pp'])} | {intent['saves']} "
                f"| {intent['harms']} | {intent['neutral']} | {_fmt(intent['mean_delta_pp'])} |"
            )
        lines.append("")
    lines.append("## 3. Per supplied value id")
    lines.append("")
    per_value = block["per_value_id"]
    ordered = sorted(per_value.items(), key=lambda item: (-item[1]["rows_reached"], item[0]))
    shown = ordered[:max_value_rows]
    lines.append(
        "| value id | nodes | rows reached | SLU saves | SLU harms | SLU neutral "
        "| SLU mean delta pp | intent saves | intent harms | intent neutral "
        "| intent mean delta pp |"
    )
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for value_id, entry in shown:
        outcome = entry.get("outcome")
        if outcome:
            slu = outcome["slu_f1"]
            intent = outcome["intent"]
            tail = (
                f"{slu['saves']} | {slu['harms']} | {slu['neutral']} "
                f"| {_fmt(slu['mean_delta_pp'])} | {intent['saves']} | {intent['harms']} "
                f"| {intent['neutral']} | {_fmt(intent['mean_delta_pp'])}"
            )
        else:
            tail = "-- | -- | -- | -- | -- | -- | -- | --"
        lines.append(
            f"| {value_id} | {','.join(entry['nodes'])} | {entry['rows_reached']} | {tail} |"
        )
    if len(ordered) > len(shown):
        lines.append("")
        lines.append(
            f"({len(ordered) - len(shown)} further value ids omitted from this table; "
            "`delta-consumption.json` carries all of them.)"
        )
    lines.append("")
    if block["per_scenario"]:
        lines.append("## 4. Per scenario")
        lines.append("")
        header = "| scenario | rows | rows supplied |"
        rule = "| --- | ---: | ---: |"
        for node in block["node_order"]:
            header += f" {node} rows | {node} items |"
            rule += " ---: | ---: |"
        header += " SLU mean delta pp | intent mean delta pp |"
        rule += " ---: | ---: |"
        lines.append(header)
        lines.append(rule)
        for scenario, entry in block["per_scenario"].items():
            row = f"| {scenario} | {entry['rows_total']} | {entry['rows_supplied_any_node']} |"
            for node in block["node_order"]:
                node_entry = entry["nodes"][node]
                row += f" {node_entry['rows_supplied']} | {node_entry['items_supplied_total']} |"
            outcome = entry.get("outcome_on_supplied_rows")
            if outcome:
                row += (
                    f" {_fmt(outcome['slu_f1']['mean_delta_pp'])} "
                    f"| {_fmt(outcome['intent']['mean_delta_pp'])} |"
                )
            else:
                row += " -- | -- |"
            lines.append(row)
        lines.append("")
    projection = block["projection"]
    lines.append("## 5. Candidate projection events")
    lines.append("")
    if not projection.get("published"):
        lines.append(f"- {projection.get('note')}")
    else:
        lines.append(
            f"- events {projection['events']}, rows {projection['rows']}, "
            f"positions dropped {projection['positions_dropped']}, "
            f"by node {projection['by_node']}"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def read(args) -> dict:
    directory = run_dir(args.run, args.attempt)
    manifest = load_manifest(directory, args.run, require_completed=not args.allow_incomplete)
    receipt = load_router_receipt(directory, args.store_id)
    phases = load_phase_results(directory, args.run)
    supply = extract_row_supply(phases["results"], phases["controller_policy_id"], args.store_id)
    skips = summarise_skips(receipt["delta_supply"])
    projection = summarise_projection(receipt["delta_candidate_projection"])
    declared = (
        load_declared_routes(args.baseline_config, args.store_id)
        if args.baseline_config
        else None
    )
    caps_override = json.loads(args.caps) if args.caps else {}
    cap_disagreements = []
    if declared:
        for node, cap in supply["caps_from_refs"].items():
            if node in declared["caps"] and declared["caps"][node] != cap:
                cap_disagreements.append(
                    {"node": node, "flown_cap": cap, "declared_cap": declared["caps"][node]}
                )
        merged = dict(declared["caps"])
        merged.update(caps_override)
        caps_override = merged

    arm_scores = load_score_rows(directory, args.run, args.scorer)
    comparator_scores = None
    comparator_manifest = None
    if args.comparator_run and args.comparator_attempt:
        comparator_dir = run_dir(args.comparator_run, args.comparator_attempt)
        comparator_manifest = load_manifest(
            comparator_dir, args.comparator_run, require_completed=True
        )
        comparator_scores = load_score_rows(comparator_dir, args.comparator_run, args.scorer)
    if arm_scores and comparator_scores:
        missing = sorted(set(supply["per_row"]) - set(arm_scores["rows"]))
        if missing:
            raise ConsumptionError(
                f"{len(missing)} flown row(s) carry no per-sample score in this run"
            )
        absent = sorted(set(supply["per_row"]) - set(comparator_scores["rows"]))
        if absent:
            raise ConsumptionError(
                f"{len(absent)} flown row(s) are absent from the comparator's scores"
            )

    consumption = build_consumption(
        supply=supply,
        skips=skips,
        projection=projection,
        unconditional=receipt["unconditional"],
        arm_rows=arm_scores["rows"] if arm_scores else None,
        comparator_rows=comparator_scores["rows"] if comparator_scores else None,
        scenarios=load_scenarios(args.roster_metadata),
        caps_override=caps_override,
    )
    return {
        "schema": "saea-stage3-delta-consumption-v1",
        "recipe_id": args.recipe_id,
        "title": args.title or f"Stage-3 delta consumption: {args.run}",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "store_id": args.store_id,
        "scorer": args.scorer,
        "run": {
            "run_id": args.run,
            "attempt_id": args.attempt,
            "manifest": manifest,
            "phases_sha256": phases["sha256"],
            "flight_receipts_sha256": receipt["sha256"],
            "knowledge_snapshot_sha256": phases["knowledge_snapshot_sha256"],
            "controller_policy_id": phases["controller_policy_id"],
            "scores_sha256": arm_scores["sha256"] if arm_scores else None,
        },
        "comparator": (
            {
                "run_id": args.comparator_run,
                "attempt_id": args.comparator_attempt,
                "manifest": comparator_manifest,
                "scores_sha256": comparator_scores["sha256"] if comparator_scores else None,
            }
            if comparator_manifest
            else None
        ),
        "store": receipt["store"],
        "unconditional_context_supply": receipt["unconditional"],
        "binding_sha256": receipt["binding_sha256"],
        "declared_routes": declared,
        "attribution_audit": {
            "node_label_disagreements": supply["node_label_disagreements"],
            "unattributed_supplied_items": supply["unattributed_supplied_items"],
            "caps_from_refs": supply["caps_from_refs"],
            "cap_disagreements": cap_disagreements,
            "declared_release_matches_the_flight_receipt": (
                None
                if declared is None
                else declared["release_sha256"] == receipt["store"]["store_release_sha256"]
            ),
            "declared_snapshot_matches_the_flight_receipt": (
                None
                if declared is None
                else declared["snapshot_sha256"] == receipt["store"]["store_snapshot_sha256"]
            ),
        },
        "consumption": consumption,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Stage-3 per-node delta-consumption read")
    parser.add_argument("--run", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--comparator-run", default=None)
    parser.add_argument("--comparator-attempt", default=None)
    parser.add_argument("--store-id", default="stage3-deltas")
    parser.add_argument("--scorer", default=SCORER)
    parser.add_argument("--analysis-root", required=True)
    parser.add_argument(
        "--roster-metadata",
        default=(
            "analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/"
            "roster-metadata.json"
        ),
    )
    parser.add_argument("--recipe-id", default="slurp-stage3-delta-consumption-v1")
    parser.add_argument("--title", default=None)
    parser.add_argument(
        "--baseline-config",
        default=None,
        help=(
            "the cell's committed configs/baseline fragment; the registered per-node caps and "
            "route declarations are read from it and its sha256 is recorded"
        ),
    )
    parser.add_argument(
        "--caps", default=None, help="JSON {node: cap} override when a route served no row"
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="read a run whose manifest is not COMPLETED (smoke diagnostics)",
    )
    parser.add_argument("--max-value-rows", type=int, default=200)
    parser.add_argument(
        "--stdout", action="store_true", help="print the summary block instead of writing files"
    )
    args = parser.parse_args(argv)

    payload = read(args)
    if args.stdout:
        print(json.dumps(payload["consumption"]["summary"], indent=2, sort_keys=True))
        return 0
    root = Path(args.analysis_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "delta-consumption.json"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    md_path = root / "delta-consumption.md"
    md_path.write_text(
        render_markdown(payload, max_value_rows=args.max_value_rows),
        encoding="utf-8",
        newline="\n",
    )
    print("written ->", json_path)
    print("written ->", md_path)
    summary = payload["consumption"]["summary"]
    print(
        "rows", summary["rows_total"],
        "| supplied", summary["rows_supplied_any_node"],
        "| items", summary["items_supplied_total"],
        "| distinct value ids", summary["distinct_value_ids_supplied"],
        "| skips", summary["skip_events"],
        "| projections", summary["projection_events"],
        "| inert", summary["inert_routes"] or "none",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
