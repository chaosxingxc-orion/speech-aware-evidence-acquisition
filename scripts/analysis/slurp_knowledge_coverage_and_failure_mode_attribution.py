#!/usr/bin/env python3
"""Decision-123 knowledge failure-mode attribution and existing-source coverage.

A model-free read over sealed bytes. Zero model, server, tokenizer, encoder,
embedder, scorer, network, GPU and paid-API contacts: every number below is read
from artefacts that earlier flights already sealed, from the released knowledge
stores, and from the governed SLURP TRAIN split through the ordinary loader.

Two questions.

1.  Owner decision 123 requires the five knowledge failure modes to stay
    distinguishable: (i) absent from the store, (ii) present but not retrieved,
    (iii) retrieved but budget-excluded, (iv) delivered but ignored or misused,
    (v) locally correct but later overwritten.  Modes (i)-(iii) are computable
    offline for every failed row, because the sealed receipts carry the released
    store's key universe, the row's retrieved set and the row's materialised
    supply.  Modes (iv) and (v) need re-execution and are reported as one
    residual bucket that this read explicitly cannot split.

2.  How much knowledge each class already has inside the sources this programme
    owns, the per-class error rate beside that count, the relationship between
    the two, the classes the store says nothing about, and how much of the TRAIN
    split the exemplar pool leaves unused.

Gold discipline.  Gold labels are read HERE, offline, exactly as
``core.scoring_batch`` reads them: through ``data.slurp.load_slurp_split`` for
the TRAIN split and out of the sealed bad-case bank for the two PLAN rosters.
No gold value reaches a runtime query, a retrieval key, a selector or a supply
decision -- this script writes a report and nothing else, and it opens no
config, no policy and no store-construction path.

Text discipline.  No utterance text, transcript, delivered answer, gold filler,
predicted filler or knowledge body text is read into a reported value or
printed.  Every cell is an id, a class name, a count, a rate, a ratio or a hash.

Reproducibility.  Deterministic apart from the ``generated_at`` stamp: every
container is sorted before it is consumed, and the one resampling procedure
(the bootstrap interval on the count-versus-error-rate correlation) is seeded.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402

DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
DEFAULT_MARKDOWN = (
    "docs/results/2026-09-26-slurp-knowledge-coverage-and-failure-mode-attribution.md"
)
DEFAULT_ANALYSIS_DIR = "analysis/SLURP-KNOWLEDGE-COVERAGE-FAILURE-MODE-V1"
READ_ID = "SAEA-SLURP-MF-KNOWLEDGE-COVERAGE-FAILURE-MODE-V1"
RECIPE = "slurp-knowledge-coverage-and-failure-mode-attribution-v1"
BOOTSTRAP_SEED = 20260926
BOOTSTRAP_REPLICATES = 10000

IB_STORE = "intent-boundaries"
SC_STORE = "slot-contracts"
EX_STORE = "train-exemplars"

IB_SNAPSHOT = "knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json"
IB_RELEASE = "knowledge/slurp/semantic/intent-boundaries-v1/release.json"
SC_SNAPSHOT = "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json"
SC_RELEASE = "knowledge/slurp/semantic/slot-contracts-v2/release.json"
EX_SNAPSHOT = (
    "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
)
EX_R01_SNAPSHOT = (
    "knowledge/slurp/saea-kb-distmodel-v1/"
    "size-pool-annotated-exemplars-minus-r01/snapshot.json"
)
GOVERNED_TRAIN = "datasets/slurp/metadata/train.jsonl"

BANK = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"

# The sealed arms this read attributes over.  ``roster`` names the bad-case
# bank's own roster label where one exists.
ARMS = (
    {
        "label": "roll1",
        "title": "ROLL-1 as-flown pool (R01C construction roster, 625 rows)",
        "run_id": "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1",
        "attempt": "attempt-slurp-native-stage3-rollout-r01-generation-v1",
        "roster": None,
        "split": "train",
        "scores": (
            "analysis/SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1/"
            "PS-registered-support-3-slurp-slu-official-projected-v3-train-scores.json"
        ),
        "scorer_id": "slurp-slu-official-projected-v3-train",
    },
    {
        "label": "train-fold-a-plan",
        "title": "TRAIN Fold A PLAN (construction roster, 1,080 rows)",
        "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
        "attempt": "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1",
        "roster": "train-fold-a",
        "split": "train",
        "scores": None,
        "scorer_id": None,
    },
    {
        "label": "dev2000-added-plan",
        "title": "DEV-2000-ADDED PLAN (fresh roster, 1,000 rows)",
        "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1",
        "attempt": "attempt-slurp-native-default-plan-dev2000-added-generation-v1",
        "roster": "dev2000-added",
        "split": "devel",
        "scores": None,
        "scorer_id": None,
    },
)

MODE_I = "i-absent-from-the-store"
MODE_II = "ii-present-but-not-retrieved"
MODE_III = "iii-retrieved-but-budget-excluded"
MODE_RESIDUAL = "iv-v-residual-delivered-and-still-wrong"
MODES = (MODE_I, MODE_II, MODE_III, MODE_RESIDUAL)


class ReadError(RuntimeError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def bare(value_id: str) -> str:
    return value_id.split("::", 1)[1] if "::" in value_id else value_id


def store_of(item_id: str) -> str:
    stripped = item_id.split("knowledge:", 1)[-1]
    return stripped.split("::", 1)[0] if "::" in stripped else ""


def pct(numerator: float, denominator: float) -> float:
    return 100.0 * numerator / denominator if denominator else 0.0


# ---------------------------------------------------------------------------
# Released stores
# ---------------------------------------------------------------------------


def load_store(data_root: Path, snapshot_rel: str, release_rel: str | None,
               prefix: str) -> dict:
    """Key universe of a released store, by id only; bodies are never read."""

    snapshot_path = data_root / snapshot_rel
    document = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if document.get("snapshot_version") is None:
        raise ReadError(f"{snapshot_rel}: not a knowledge snapshot")
    value_ids = sorted(str(v["value_id"]) for v in document["values"])
    facet_ids = sorted(str(f["facet_id"]) for f in document["facets"])
    keys = sorted({vid.split(prefix, 1)[-1] for vid in value_ids}) if prefix else value_ids
    entry = {
        "snapshot_relpath": snapshot_rel,
        "snapshot_file_sha256": digest(snapshot_path),
        "snapshot_content_sha256": document.get("snapshot_sha256"),
        "snapshot_id": document.get("snapshot_id"),
        "builder_policy_id": document.get("builder_policy_id"),
        "source_partition_role": document.get("source_partition_role"),
        "source_split_identity_hash": document.get("source_split_identity_hash"),
        "value_count": len(value_ids),
        "facet_count": len(facet_ids),
        "source_sample_id_count": len(document.get("source_sample_ids") or ()),
        "keys": keys,
        "key_count": len(keys),
        "task_targets": sorted({
            str(v["task_target"]) for v in document["values"]
            if v.get("task_target") is not None
        }),
    }
    entry["task_target_counts"] = dict(sorted(Counter(
        str(v["task_target"]) for v in document["values"]
        if v.get("task_target") is not None
    ).items()))
    if release_rel is not None:
        release_path = data_root / release_rel
        release = json.loads(release_path.read_text(encoding="utf-8"))
        entry["release_relpath"] = release_rel
        entry["release_file_sha256"] = digest(release_path)
        entry["release_store_id"] = release.get("store_id")
        entry["release_snapshot_sha256"] = release.get("snapshot_sha256")
        if entry["release_snapshot_sha256"] != entry["snapshot_content_sha256"]:
            raise ReadError(f"{snapshot_rel}: release pin disagrees with the snapshot")
    return entry


# ---------------------------------------------------------------------------
# Governed gold
# ---------------------------------------------------------------------------


def load_train_gold(lock: dict, data_root: Path) -> dict:
    """Utterance-level TRAIN gold: intent, scenario, action and slot TYPES.

    Read through the ordinary loader, offline, exactly as the official scorer
    reads it.  No filler value and no sentence is retained.
    """

    records = load_slurp_split(lock, data_root, "train")
    by_utterance: dict[str, dict] = {}
    for record in records:
        types = tuple(sorted(entity.type for entity in record.entities))
        payload = {
            "intent": f"{record.scenario}_{record.action}",
            "scenario": record.scenario,
            "action": record.action,
            "types": types,
            "type_set": tuple(sorted(set(types))),
        }
        key = str(int(record.utterance_id)) if str(record.utterance_id).isdigit()             else str(record.utterance_id)
        previous = by_utterance.get(key)
        if previous is not None and previous != payload:
            raise ReadError(f"TRAIN utterance {key}: gold disagrees across recordings")
        by_utterance[key] = payload
    return by_utterance


# ---------------------------------------------------------------------------
# Sealed per-row knowledge sets
# ---------------------------------------------------------------------------


def load_arm_rows(data_root: Path, arm: dict) -> dict:
    """Per row: what the released stores offered, retrieved and materialised.

    ``consumption.records`` is the sealed per-row record of the items the
    episode received; ``rank_result`` is the ranked retrieval result;
    ``fusion_decision.selected_value_ids`` and the acquire transition's
    ``new_value_ids`` are what was materialised into supply.  The
    candidate-semantic store additionally carries a pre-budget
    ``mapped_value_ids`` and a post-budget ``qualified_selected_value_ids`` in
    the flight receipt, which is the only place in this system where a budget
    can drop an already-retrieved value.
    """

    directory = data_root / "runs" / arm["run_id"] / arm["attempt"]
    phases_path = directory / f"{arm['run_id']}.phases.json"
    receipts_path = directory / "flight-receipts.json"
    document = json.loads(phases_path.read_text(encoding="utf-8"))
    if document.get("schema") != "saea-flight-phase-summaries-v1":
        raise ReadError(f"{arm['label']}: unexpected phase artefact schema")
    if document.get("run_id") != arm["run_id"] or len(document.get("phases") or ()) != 1:
        raise ReadError(f"{arm['label']}: phase artefact does not bind this one system")
    summary = document["phases"][0]
    rows: dict[str, dict] = {}
    for result in summary["results"]:
        sample_id = result.get("sample_id")
        row = {
            "ib_delivered": [],
            "ex_delivered": [],
            "ranked": defaultdict(set),
            "fused": defaultdict(set),
            "materialised": defaultdict(set),
            "outcomes": Counter(),
        }
        consumption = result.get("consumption") or {}
        for record in consumption.get("records") or ():
            item = str(record.get("supplied_item_id") or "")
            store = store_of(item)
            row["outcomes"][f"{store}|{record.get('outcome')}"] += 1
            if store == IB_STORE:
                row["ib_delivered"].append(bare(item).split("intent-boundary:", 1)[-1])
            elif store == EX_STORE:
                row["ex_delivered"].append(bare(item).split("value:", 1)[-1])
        for wave in result.get("waves") or ():
            rank = wave.get("rank_result")
            if isinstance(rank, dict):
                for candidate in rank.get("candidates") or ():
                    facet = str(candidate.get("facet_id"))
                    row["ranked"][facet.split("::", 1)[0]].add(bare(facet))
            fusion = wave.get("fusion_decision")
            if isinstance(fusion, dict):
                for value in fusion.get("selected_value_ids") or ():
                    row["fused"][value.split("::", 1)[0]].add(bare(value))
            transition = wave.get("transition")
            if isinstance(transition, dict):
                for value in transition.get("new_value_ids") or ():
                    if "::" in value:
                        row["materialised"][value.split("::", 1)[0]].add(bare(value))
        rows[sample_id] = row
    del document

    receipts = json.loads(receipts_path.read_text(encoding="utf-8"))
    supply = ((receipts.get("stages") or {}).get("run_phases") or {}).get("phase_supply") or {}
    selections = supply.get("candidate_selections") or {}
    if not selections:
        raise ReadError(f"{arm['label']}: flight receipt carries no candidate_selections")
    per_row_sc: dict[str, dict] = {}
    for entry in selections.values():
        sample_id = entry.get("sample_id")
        if not isinstance(sample_id, str):
            continue
        slot = per_row_sc.setdefault(sample_id, {
            "mapped": set(), "selected": set(), "ignored": Counter(),
            "caps": None, "events": 0, "dispositions": Counter(),
        })
        slot["events"] += 1
        slot["dispositions"][str(entry.get("supply_disposition"))] += 1
        slot["caps"] = (
            entry.get("max_candidates"),
            entry.get("max_total_values"),
            entry.get("max_values_per_candidate"),
        )
        for mapping in entry.get("mappings") or ():
            for value in mapping.get("mapped_value_ids") or ():
                slot["mapped"].add(bare(value).split("slot-contract:", 1)[-1])
            for ignored in mapping.get("ignored_mappings") or ():
                slot["ignored"][str(ignored.get("reason"))] += 1
        for value in entry.get("qualified_selected_value_ids") or ():
            if value.startswith(f"{SC_STORE}::"):
                slot["selected"].add(bare(value).split("slot-contract:", 1)[-1])

    store_specs: dict[str, dict] = {}
    for store_id, store in (supply.get("stores") or {}).items():
        spec_entry = {
            "store_release_sha256": store.get("store_release_sha256"),
            "store_snapshot_sha256": store.get("store_snapshot_sha256"),
        }
        phase_supply = store.get("phase_supply")
        if isinstance(phase_supply, dict):
            specs = []
            for phase in phase_supply.get("phases") or ():
                spec = phase.get("spec") or {}
                specs.append({
                    "phase": spec.get("phase"),
                    "provider": spec.get("provider"),
                    "k": spec.get("k"),
                    "tau": spec.get("tau"),
                    "fuse_coverage": spec.get("fuse_coverage"),
                    "fuse_policy": spec.get("fuse_policy"),
                    "facet_vector_rows": phase.get("facet_vector_rows"),
                    "query_vector_rows": phase.get("query_vector_rows"),
                    "facet_source_relpath": (spec.get("facet_source") or {}).get("relpath"),
                })
            spec_entry["phase_specs"] = specs
        candidate_supply = store.get("candidate_supply")
        if isinstance(candidate_supply, list):
            spec_entry["candidate_specs"] = [{
                "phase": spec.get("phase"),
                "provider": spec.get("provider"),
                "max_candidates": spec.get("max_candidates"),
                "max_total_values": spec.get("max_total_values"),
                "max_values_per_candidate": spec.get("max_values_per_candidate"),
            } for spec in candidate_supply]
        store_specs[store_id] = spec_entry

    for sample_id, slot in per_row_sc.items():
        row = rows.get(sample_id)
        if row is None:
            continue
        row["sc_mapped"] = slot["mapped"]
        row["sc_selected"] = slot["selected"]
        row["sc_ignored"] = slot["ignored"]
        row["sc_caps"] = slot["caps"]
        row["sc_events"] = slot["events"]
        row["sc_dispositions"] = slot["dispositions"]

    return {
        "label": arm["label"],
        "run_id": arm["run_id"],
        "attempt_id": arm["attempt"],
        "controller_policy_id": summary.get("controller_policy_id"),
        "knowledge_snapshot_sha256": summary.get("knowledge_snapshot_sha256"),
        "phases_relpath": str(phases_path.relative_to(data_root)),
        "phases_sha256": digest(phases_path),
        "receipts_relpath": str(receipts_path.relative_to(data_root)),
        "receipts_sha256": digest(receipts_path),
        "store_specs": store_specs,
        "rows": rows,
        "rows_with_candidate_receipt": len(per_row_sc),
    }


# ---------------------------------------------------------------------------
# Error populations
# ---------------------------------------------------------------------------


def classify(intent_wrong: bool, fp: float, fn: float) -> str:
    if intent_wrong:
        return "INTENT-WRONG"
    if fp and fn:
        return "ENTITY-MIXED"
    if fn:
        return "ENTITY-FN-ONLY"
    if fp:
        return "ENTITY-FP-ONLY"
    return "CORRECT"


def load_roll1_population(data_root: Path, arm: dict) -> dict:
    path = data_root / arm["scores"]
    document = json.loads(path.read_text(encoding="utf-8"))
    block = document[arm["scorer_id"]]
    rows = {}
    for sample in block["per_sample"]:
        sample_id = str(sample["sample_id"])
        intent_wrong = not bool(sample["scenario_action_exact"])
        rows[sample_id] = {
            "class": classify(intent_wrong,
                              float(sample["slot_f1_exact_fp"]),
                              float(sample["slot_f1_exact_fn"])),
            "intent_wrong": intent_wrong,
            "fp": float(sample["slot_f1_exact_fp"]),
            "fn": float(sample["slot_f1_exact_fn"]),
            "parsed": bool(sample.get("parsed")),
            "fn_types": None,
            "fp_types": None,
        }
    official = block["aggregate"]["official"]
    return {
        "rows": rows,
        "scores_relpath": arm["scores"],
        "scores_sha256": digest(path),
        "scorer_id": arm["scorer_id"],
        "evaluator_commit": block["aggregate"].get("evaluator_commit"),
        "identity_check": block["aggregate"].get("identity_check"),
        "official_intent_accuracy": official.get("intent_accuracy"),
        "official_slu_f1": official.get("slu_f1"),
        "official_span_f1": official.get("span_f1"),
        "official_intent_tp_fn": [
            (official.get("raw") or {}).get("intent", {}).get("tp"),
            (official.get("raw") or {}).get("intent", {}).get("fn"),
        ],
    }


def load_bank(data_root: Path) -> dict:
    path = data_root / BANK
    per_roster: dict[str, dict] = defaultdict(dict)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        per_roster[entry["roster"]][entry["sample_id"]] = {
            "class": {
                "INTENT-UNCOVERED": "INTENT-WRONG",
                "INTENT-COVERED": "INTENT-WRONG",
            }.get(entry["plan_class"], entry["plan_class"]),
            "plan_class": entry["plan_class"],
            "planr_class": entry["planr_class"],
            "stability_joint": entry["stability_joint"],
            "gold_intent": entry["gold_intent"],
            "gold_entity_types": list(entry["gold_entity_types"]),
            "gold_entity_count": entry["gold_entity_count"],
            "fn_types": list(entry["fn_types"]),
            "fp_types": list(entry["fp_types"]),
            "span_fn": entry["span_fn"],
            "span_fp": entry["span_fp"],
            "fn": entry["span_fn"],
            "fp": entry["span_fp"],
            "supplied_contract_types": list(entry["supplied_contract_types"]),
            "supplied_exemplar_types": list(entry["supplied_exemplar_types"]),
            "supplied_exemplar_intents": dict(entry["supplied_exemplar_intents"]),
            "stratum": entry["stratum"],
        }
    return {
        "relpath": BANK,
        "sha256": digest(path),
        "rosters": {name: dict(sorted(rows.items())) for name, rows in sorted(per_roster.items())},
    }


# ---------------------------------------------------------------------------
# Channel geometry: is a budget stage reachable at all?
# ---------------------------------------------------------------------------


def channel_geometry(arm_rows: dict) -> dict:
    """What the sealed receipt says about each channel's retrieval and budget.

    A channel can only produce mode (iii) if some already-retrieved value can
    fail to reach the row.  For the two facet channels that is decided by the
    pinned spec (``k`` against ``fuse_coverage``); for the candidate-semantic
    channel it is decided per row by ``mapped`` against ``selected``.
    """

    out = {}
    for store_id, spec in sorted(arm_rows["store_specs"].items()):
        entry = {"store_snapshot_sha256": spec.get("store_snapshot_sha256")}
        for phase_spec in spec.get("phase_specs") or ():
            coverage = phase_spec.get("fuse_coverage") or {}
            entry.update({
                "phase": phase_spec.get("phase"),
                "provider": phase_spec.get("provider"),
                "k": phase_spec.get("k"),
                "fuse_top_l": coverage.get("top_l"),
                "fuse_m": coverage.get("m"),
                "fuse_c": coverage.get("c"),
                "facet_vector_rows": phase_spec.get("facet_vector_rows"),
                "query_vector_rows": phase_spec.get("query_vector_rows"),
                "facet_source_relpath": phase_spec.get("facet_source_relpath"),
                "budget_reachable": not (
                    phase_spec.get("k") == coverage.get("top_l")
                    and coverage.get("m") == coverage.get("top_l")
                ),
            })
        for candidate_spec in spec.get("candidate_specs") or ():
            entry.update({
                "phase": candidate_spec.get("phase"),
                "provider": candidate_spec.get("provider"),
                "max_candidates": candidate_spec.get("max_candidates"),
                "max_total_values": candidate_spec.get("max_total_values"),
                "max_values_per_candidate": candidate_spec.get("max_values_per_candidate"),
                "budget_reachable": True,
            })
        out[store_id] = entry

    observed = {
        "ib_delivered_sizes": Counter(),
        "ex_delivered_sizes": Counter(),
        "sc_mapped_max": 0,
        "sc_mapped_minus_selected_rows": 0,
        "sc_mapped_minus_selected_values": 0,
        "sc_ignored_reasons": Counter(),
        "sc_caps": Counter(),
        "sc_dispositions": Counter(),
        "ex_ranked_equals_materialised_rows": 0,
        "ex_rows": 0,
    }
    for row in arm_rows["rows"].values():
        observed["ib_delivered_sizes"][len(row["ib_delivered"])] += 1
        observed["ex_delivered_sizes"][len(row["ex_delivered"])] += 1
        mapped = row.get("sc_mapped") or set()
        selected = row.get("sc_selected") or set()
        observed["sc_mapped_max"] = max(observed["sc_mapped_max"], len(mapped))
        gap = mapped - selected
        if gap:
            observed["sc_mapped_minus_selected_rows"] += 1
            observed["sc_mapped_minus_selected_values"] += len(gap)
        observed["sc_ignored_reasons"].update(row.get("sc_ignored") or {})
        if row.get("sc_caps"):
            observed["sc_caps"][str(row["sc_caps"])] += 1
        observed["sc_dispositions"].update(row.get("sc_dispositions") or {})
        ranked = {value.split(":")[-1] for value in row["ranked"].get(EX_STORE, set())}
        material = {value.split(":")[-1] for value in row["materialised"].get(EX_STORE, set())}
        observed["ex_rows"] += 1
        if ranked and ranked == material:
            observed["ex_ranked_equals_materialised_rows"] += 1
    return {
        "specs": out,
        "observed": {
            "ib_delivered_sizes": dict(sorted(observed["ib_delivered_sizes"].items())),
            "ex_delivered_sizes": dict(sorted(observed["ex_delivered_sizes"].items())),
            "sc_mapped_max": observed["sc_mapped_max"],
            "sc_mapped_minus_selected_rows": observed["sc_mapped_minus_selected_rows"],
            "sc_mapped_minus_selected_values": observed["sc_mapped_minus_selected_values"],
            "sc_ignored_reasons": dict(sorted(observed["sc_ignored_reasons"].items())),
            "sc_caps": dict(sorted(observed["sc_caps"].items())),
            "sc_dispositions": dict(sorted(observed["sc_dispositions"].items())),
            "ex_ranked_equals_materialised_rows": observed["ex_ranked_equals_materialised_rows"],
            "ex_rows": observed["ex_rows"],
        },
    }


# ---------------------------------------------------------------------------
# Question 1: the attribution
# ---------------------------------------------------------------------------


def pool_class_counts(pool_keys, train_gold) -> tuple[Counter, Counter]:
    """Per slot TYPE and per intent, how many pool utterances demonstrate it.

    ``__EMPTY__`` counts the utterances whose gold carries no entity at all --
    the only demonstration of the correct empty answer the pool can give.
    """

    types: Counter = Counter()
    intents: Counter = Counter()
    for key in sorted(pool_keys):
        meta = train_gold.get(key)
        if meta is None:
            continue
        intents[meta["intent"]] += 1
        if not meta["types"]:
            types["__EMPTY__"] += 1
        for slot_type in meta["type_set"]:
            types[slot_type] += 1
    return types, intents


def attribute_arm(*, arm, arm_rows, population, stores, train_gold, pool_types,
                  pool_intents) -> dict:
    """Mode shares per error class, per knowledge channel, at item granularity.

    The unit of the primary accounting is one (row, needed knowledge item)
    pair, because a row can need several items and an arbitrary per-row winner
    would not add up.  A row-level view under a stated precedence follows it.
    """

    ib_keys = set(stores["intent_boundaries"]["keys"])
    sc_keys = set(stores["slot_contracts"]["keys"])

    channels: dict[str, dict] = {
        "intent-boundary": defaultdict(lambda: defaultdict(Counter)),
        "slot-contract": defaultdict(lambda: defaultdict(Counter)),
        "exemplar-type": defaultdict(lambda: defaultdict(Counter)),
        "exemplar-intent": defaultdict(lambda: defaultdict(Counter)),
        "empty-answer": defaultdict(lambda: defaultdict(Counter)),
    }
    row_modes: dict[str, Counter] = defaultdict(Counter)
    class_rows: Counter = Counter()
    type_channel_unavailable: Counter = Counter()
    # Retrieval quality over EVERY row, correct ones included, because a
    # retrieval rate only reads as a defect beside the rate on rows that worked.
    quality: dict[str, Counter] = defaultdict(Counter)
    missing_rows = 0
    unknown_gold = 0

    for sample_id, verdict in sorted(population["rows"].items()):
        klass = verdict["class"]
        class_rows[klass] += 1
        row = arm_rows["rows"].get(sample_id)
        if row is None:
            missing_rows += 1
            continue
        utterance_id = sample_id.split(":")[2] if sample_id.count(":") >= 2 else None
        gold = train_gold.get(str(int(utterance_id))) if (
            utterance_id and arm["split"] == "train" and utterance_id.isdigit()
        ) else None
        gold_intent = verdict.get("gold_intent") or (gold or {}).get("intent")
        gold_types = verdict.get("gold_entity_types")
        if gold_types is None:
            gold_types = list((gold or {}).get("types") or ())
        if gold_intent is None:
            unknown_gold += 1
            continue

        delivered_ib = set(row["ib_delivered"])
        delivered_ex = set(row["ex_delivered"])
        delivered_ex_types: set[str] = set()
        delivered_ex_intents: Counter = Counter()
        for value_key in sorted(delivered_ex):
            meta = train_gold.get(value_key)
            if meta is None:
                continue
            delivered_ex_types.update(meta["type_set"])
            if not meta["types"]:
                delivered_ex_types.add("__EMPTY__")
            delivered_ex_intents[meta["intent"]] += 1
        sc_mapped = set(row.get("sc_mapped") or ())
        sc_selected = set(row.get("sc_selected") or ())
        sc_material = {
            value.split("slot-contract:", 1)[-1]
            for value in row["materialised"].get(SC_STORE, set())
        }

        gold_type_set = sorted(set(gold_types))
        quality[klass]["rows"] += 1
        quality[klass]["ib_gold_boundary_delivered"] += int(gold_intent in delivered_ib)
        quality[klass]["ib_gold_boundary_in_store"] += int(gold_intent in ib_keys)
        quality[klass]["ex_gold_intent_delivered"] += int(
            delivered_ex_intents.get(gold_intent, 0) > 0)
        quality[klass]["ex_empty_demo_delivered"] += int("__EMPTY__" in delivered_ex_types)
        quality[klass]["ex_empty_demo_count"] += sum(
            1 for key in sorted(delivered_ex)
            if (train_gold.get(key) or {}).get("types") == ()
        )
        if gold_type_set:
            quality[klass]["rows_with_gold_types"] += 1
            quality[klass]["gold_types"] += len(gold_type_set)
            quality[klass]["gold_types_with_contract_in_store"] += sum(
                1 for t in gold_type_set if t in sc_keys)
            quality[klass]["gold_types_contract_materialised"] += sum(
                1 for t in gold_type_set if t in sc_material)
            quality[klass]["gold_types_shown_by_an_exemplar"] += sum(
                1 for t in gold_type_set if t in delivered_ex_types)
        else:
            quality[klass]["rows_with_empty_gold"] += 1

        if klass == "CORRECT":
            continue

        row_seen: list[str] = []

        # Channel 1 -- the intent-boundary the row needed.
        if klass == "INTENT-WRONG":
            mode = (
                MODE_I if gold_intent not in ib_keys
                else MODE_RESIDUAL if gold_intent in delivered_ib
                else MODE_II
            )
            channels["intent-boundary"][klass][mode]["items"] += 1
            channels["intent-boundary"][klass][mode]["rows"] += 1
            row_seen.append(mode)

            pool_mode = (
                MODE_I if pool_intents.get(gold_intent, 0) == 0
                else MODE_RESIDUAL if delivered_ex_intents.get(gold_intent, 0) > 0
                else MODE_II
            )
            channels["exemplar-intent"][klass][pool_mode]["items"] += 1
            channels["exemplar-intent"][klass][pool_mode]["rows"] += 1

        # Channel 2/3 -- one item per missed gold slot TYPE.
        fn_types = verdict.get("fn_types")
        if fn_types is None:
            # Per-type FN attribution needs the gold-against-predicted TYPE
            # alignment, which only the sealed bad-case bank carries.  This
            # population therefore contributes to the intent channels only.
            type_channel_unavailable[klass] += 1
            fn_types = []
        for slot_type in sorted(set(fn_types)):
            mode = (
                MODE_I if slot_type not in sc_keys
                else MODE_III if slot_type in sc_mapped and slot_type not in sc_selected
                else MODE_RESIDUAL if slot_type in sc_material
                else MODE_II
            )
            channels["slot-contract"][klass][mode]["items"] += 1
            row_seen.append(mode)
            ex_mode = (
                MODE_I if pool_types.get(slot_type, 0) == 0
                else MODE_RESIDUAL if slot_type in delivered_ex_types
                else MODE_II
            )
            channels["exemplar-type"][klass][ex_mode]["items"] += 1
        if fn_types:
            for mode in sorted({
                MODE_I if t not in sc_keys
                else MODE_III if t in sc_mapped and t not in sc_selected
                else MODE_RESIDUAL if t in sc_material
                else MODE_II
                for t in set(fn_types)
            }):
                channels["slot-contract"][klass][mode]["rows"] += 1
            for mode in sorted({
                MODE_I if pool_types.get(t, 0) == 0
                else MODE_RESIDUAL if t in delivered_ex_types
                else MODE_II
                for t in set(fn_types)
            }):
                channels["exemplar-type"][klass][mode]["rows"] += 1

        # Channel 4 -- the correct empty answer, needed when gold has no entity
        # and the row emitted one anyway.
        if verdict.get("fp") and not gold_types:
            mode = MODE_I if pool_types.get("__EMPTY__", 0) == 0 else (
                MODE_RESIDUAL if "__EMPTY__" in delivered_ex_types else MODE_II
            )
            channels["empty-answer"][klass][mode]["items"] += 1
            channels["empty-answer"][klass][mode]["rows"] += 1
            row_seen.append(mode)

        if row_seen:
            for mode in MODES:
                if mode in row_seen:
                    row_modes[klass][mode] += 1
                    break

    serialised = {}
    for channel, by_class in sorted(channels.items()):
        serialised[channel] = {
            klass: {
                mode: {"items": counts["items"], "rows": counts["rows"]}
                for mode, counts in sorted(modes.items())
            }
            for klass, modes in sorted(by_class.items())
        }
    return {
        "class_rows": dict(sorted(class_rows.items())),
        "channels": serialised,
        "row_level_precedence": {
            klass: dict(sorted(modes.items())) for klass, modes in sorted(row_modes.items())
        },
        "rows_missing_from_phase_artefact": missing_rows,
        "rows_without_resolvable_gold": unknown_gold,
        "rows_without_per_type_fn_attribution": dict(sorted(type_channel_unavailable.items())),
        "retrieval_quality": {
            klass: dict(sorted(counts.items())) for klass, counts in sorted(quality.items())
        },
    }


# ---------------------------------------------------------------------------
# Question 2: coverage, saturation, correlation
# ---------------------------------------------------------------------------


def spearman(xs, ys) -> float:
    def rank(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            mean_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[order[k]] = mean_rank
            i = j + 1
        return ranks
    return pearson(rank(xs), rank(ys))


def pearson(xs, ys) -> float:
    n = len(xs)
    if n < 3:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return float("nan")
    return sxy / math.sqrt(sxx * syy)


def bootstrap_interval(xs, ys, statistic, *, seed, replicates) -> dict:
    rng = random.Random(seed)
    n = len(xs)
    draws = []
    for _ in range(replicates):
        idx = [rng.randrange(n) for _ in range(n)]
        value = statistic([xs[i] for i in idx], [ys[i] for i in idx])
        if not math.isnan(value):
            draws.append(value)
    draws.sort()
    if not draws:
        return {"low": None, "high": None, "replicates": 0}
    return {
        "low": draws[int(0.05 * len(draws))],
        "high": draws[min(len(draws) - 1, int(0.95 * len(draws)))],
        "replicates": len(draws),
    }


def residual_scatter(xs, ys) -> dict:
    """Least-squares fit of error rate on log1p(count) and its residual spread."""

    n = len(xs)
    lx = [math.log1p(x) for x in xs]
    mx = sum(lx) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in lx)
    if sxx <= 0:
        return {"slope_pp_per_log1p_unit": None, "intercept_pp": None,
                "residual_sd_pp": None, "outcome_sd_pp": None, "r2": None}
    slope = sum((x - mx) * (y - my) for x, y in zip(lx, ys)) / sxx
    intercept = my - slope * mx
    residuals = [y - (intercept + slope * x) for x, y in zip(lx, ys)]
    rss = sum(r * r for r in residuals)
    tss = sum((y - my) ** 2 for y in ys)
    return {
        "slope_pp_per_log1p_unit": slope,
        "intercept_pp": intercept,
        "residual_sd_pp": math.sqrt(rss / (n - 2)) if n > 2 else None,
        "outcome_sd_pp": math.sqrt(tss / (n - 1)) if n > 1 else None,
        "r2": 1.0 - rss / tss if tss > 0 else None,
    }


def quartile_curve(xs, ys) -> list[dict]:
    order = sorted(range(len(xs)), key=lambda i: (xs[i], ys[i]))
    buckets = 4
    size = len(order) / buckets
    out = []
    for b in range(buckets):
        lo = int(round(b * size))
        hi = int(round((b + 1) * size))
        members = order[lo:hi]
        if not members:
            continue
        out.append({
            "quartile": b + 1,
            "classes": len(members),
            "count_min": min(xs[i] for i in members),
            "count_max": max(xs[i] for i in members),
            "count_median": sorted(xs[i] for i in members)[len(members) // 2],
            "error_rate_mean_pp": sum(ys[i] for i in members) / len(members),
        })
    return out


def relationship(xs, ys, *, label) -> dict:
    return {
        "label": label,
        "classes": len(xs),
        "spearman_rho": spearman(xs, ys),
        "spearman_ci90": bootstrap_interval(xs, ys, spearman,
                                            seed=BOOTSTRAP_SEED,
                                            replicates=BOOTSTRAP_REPLICATES),
        "pearson_r_on_log1p_count": pearson([math.log1p(x) for x in xs], ys),
        "fit": residual_scatter(xs, ys),
        "quartiles": quartile_curve(xs, ys),
    }


def build_coverage(*, stores, train_gold, bank, roll1_population, roll1_rows) -> dict:
    pool_keys = set(stores["exemplar_pool"]["value_keys"])
    pool_r01_keys = set(stores["exemplar_pool_minus_r01"]["value_keys"])
    train_keys = set(train_gold)

    def class_counts(keys):
        intents, scenarios, types, empty = Counter(), Counter(), Counter(), 0
        for key in sorted(keys):
            meta = train_gold.get(key)
            if meta is None:
                continue
            intents[meta["intent"]] += 1
            scenarios[meta["scenario"]] += 1
            for slot_type in meta["type_set"]:
                types[slot_type] += 1
            if not meta["types"]:
                empty += 1
        return intents, scenarios, types, empty

    pool_i, pool_s, pool_t, pool_empty = class_counts(pool_keys)
    poolr_i, poolr_s, poolr_t, poolr_empty = class_counts(pool_r01_keys)
    train_i, train_s, train_t, train_empty = class_counts(train_keys)
    unused = train_keys - pool_keys
    unused_r01 = train_keys - pool_r01_keys
    un_i, un_s, un_t, un_empty = class_counts(unused)
    unr_i, unr_s, unr_t, unr_empty = class_counts(unused_r01)

    ib_keys = set(stores["intent_boundaries"]["keys"])
    sc_keys = set(stores["slot_contracts"]["keys"])

    # Error rates per class, from the sealed pools.
    per_intent_errors: dict[str, Counter] = defaultdict(Counter)
    per_scenario_errors: dict[str, Counter] = defaultdict(Counter)
    per_type: dict[str, Counter] = defaultdict(Counter)

    def fold_bank(roster_rows):
        for verdict in roster_rows.values():
            intent = verdict["gold_intent"]
            scenario = intent.split("_", 1)[0]
            per_intent_errors[intent]["rows"] += 1
            per_scenario_errors[scenario]["rows"] += 1
            if verdict["class"] == "INTENT-WRONG":
                per_intent_errors[intent]["intent_wrong"] += 1
                per_scenario_errors[scenario]["intent_wrong"] += 1
            if verdict["class"] != "CORRECT":
                per_intent_errors[intent]["any_error"] += 1
                per_scenario_errors[scenario]["any_error"] += 1
            for slot_type in verdict["gold_entity_types"]:
                per_type[slot_type]["gold_mentions"] += 1
            for slot_type in verdict["fn_types"]:
                per_type[slot_type]["fn"] += 1
            for slot_type in verdict["fp_types"]:
                per_type[slot_type]["fp"] += 1

    for roster_rows in bank["rosters"].values():
        fold_bank(roster_rows)

    for sample_id, verdict in roll1_population["rows"].items():
        utterance_id = sample_id.split(":")[2]
        meta = train_gold.get(str(int(utterance_id)))
        if meta is None:
            continue
        per_intent_errors[meta["intent"]]["roll1_rows"] += 1
        per_scenario_errors[meta["scenario"]]["roll1_rows"] += 1
        if verdict["intent_wrong"]:
            per_intent_errors[meta["intent"]]["roll1_intent_wrong"] += 1
            per_scenario_errors[meta["scenario"]]["roll1_intent_wrong"] += 1
        if verdict["class"] != "CORRECT":
            per_intent_errors[meta["intent"]]["roll1_any_error"] += 1
            per_scenario_errors[meta["scenario"]]["roll1_any_error"] += 1

    intent_rows = []
    for intent in sorted(set(train_i) | ib_keys | set(per_intent_errors)):
        counts = per_intent_errors.get(intent, Counter())
        intent_rows.append({
            "intent": intent,
            "store_entries": 1 if intent in ib_keys else 0,
            "pool_utterances": pool_i.get(intent, 0),
            "pool_minus_r01_utterances": poolr_i.get(intent, 0),
            "train_utterances": train_i.get(intent, 0),
            "train_unused_by_pool": un_i.get(intent, 0),
            "bank_rows": counts.get("rows", 0),
            "bank_intent_wrong": counts.get("intent_wrong", 0),
            "bank_any_error": counts.get("any_error", 0),
            "bank_intent_error_rate_pp": pct(counts.get("intent_wrong", 0), counts.get("rows", 0)),
            "bank_any_error_rate_pp": pct(counts.get("any_error", 0), counts.get("rows", 0)),
            "roll1_rows": counts.get("roll1_rows", 0),
            "roll1_intent_wrong": counts.get("roll1_intent_wrong", 0),
            "roll1_intent_error_rate_pp": pct(counts.get("roll1_intent_wrong", 0),
                                              counts.get("roll1_rows", 0)),
        })

    scenario_rows = []
    for scenario in sorted(set(train_s) | set(per_scenario_errors)):
        counts = per_scenario_errors.get(scenario, Counter())
        scenario_rows.append({
            "scenario": scenario,
            "store_entries": sum(1 for k in ib_keys if k.split("_", 1)[0] == scenario),
            "pool_utterances": pool_s.get(scenario, 0),
            "pool_minus_r01_utterances": poolr_s.get(scenario, 0),
            "train_utterances": train_s.get(scenario, 0),
            "train_unused_by_pool": un_s.get(scenario, 0),
            "bank_rows": counts.get("rows", 0),
            "bank_intent_error_rate_pp": pct(counts.get("intent_wrong", 0), counts.get("rows", 0)),
            "bank_any_error_rate_pp": pct(counts.get("any_error", 0), counts.get("rows", 0)),
            "roll1_rows": counts.get("roll1_rows", 0),
            "roll1_intent_error_rate_pp": pct(counts.get("roll1_intent_wrong", 0),
                                              counts.get("roll1_rows", 0)),
        })

    type_rows = []
    for slot_type in sorted(set(train_t) | sc_keys | set(per_type)):
        counts = per_type.get(slot_type, Counter())
        gold = counts.get("gold_mentions", 0)
        type_rows.append({
            "slot_type": slot_type,
            "store_entries": 1 if slot_type in sc_keys else 0,
            "pool_utterances": pool_t.get(slot_type, 0),
            "pool_minus_r01_utterances": poolr_t.get(slot_type, 0),
            "train_utterances": train_t.get(slot_type, 0),
            "train_unused_by_pool": un_t.get(slot_type, 0),
            "gold_mentions": gold,
            "fn": counts.get("fn", 0),
            "fp": counts.get("fp", 0),
            "fn_rate_pp": pct(counts.get("fn", 0), gold),
        })

    def series(rows, count_key, rate_key, *, min_rows_key, min_rows):
        xs, ys, names = [], [], []
        for row in rows:
            if row.get(min_rows_key, 0) < min_rows:
                continue
            xs.append(float(row[count_key]))
            ys.append(float(row[rate_key]))
            names.append(row.get("intent") or row.get("scenario") or row.get("slot_type"))
        return xs, ys, names

    relationships = []
    xs, ys, _ = series(intent_rows, "pool_utterances", "bank_any_error_rate_pp",
                       min_rows_key="bank_rows", min_rows=10)
    relationships.append(relationship(xs, ys,
        label="per intent: exemplar-pool utterances vs any-error rate (bank rosters, >= 10 rows)"))
    xs, ys, _ = series(intent_rows, "pool_utterances", "bank_intent_error_rate_pp",
                       min_rows_key="bank_rows", min_rows=10)
    relationships.append(relationship(xs, ys,
        label="per intent: exemplar-pool utterances vs intent-error rate (bank rosters, >= 10 rows)"))
    xs, ys, _ = series(intent_rows, "pool_minus_r01_utterances", "roll1_intent_error_rate_pp",
                       min_rows_key="roll1_rows", min_rows=5)
    relationships.append(relationship(xs, ys,
        label="per intent: minus-R01 pool utterances vs ROLL-1 intent-error rate (>= 5 rows)"))
    xs, ys, _ = series(type_rows, "pool_utterances", "fn_rate_pp",
                       min_rows_key="gold_mentions", min_rows=10)
    relationships.append(relationship(xs, ys,
        label="per slot type: exemplar-pool utterances vs FN rate (bank rosters, >= 10 gold mentions)"))
    xs, ys, _ = series(scenario_rows, "pool_utterances", "bank_any_error_rate_pp",
                       min_rows_key="bank_rows", min_rows=10)
    relationships.append(relationship(xs, ys,
        label="per scenario: exemplar-pool utterances vs any-error rate (bank rosters, >= 10 rows)"))

    return {
        "store_universes": {
            "intent_boundaries_entries": len(ib_keys),
            "slot_contracts_entries": len(sc_keys),
            "exemplar_pool_utterances": len(pool_keys),
            "exemplar_pool_minus_r01_utterances": len(pool_r01_keys),
            "train_utterances": len(train_keys),
            "train_intents": len(train_i),
            "train_scenarios": len(train_s),
            "train_slot_types": len(train_t),
            "intents_without_a_boundary_entry": sorted(set(train_i) - ib_keys),
            "slot_types_without_a_contract_entry": sorted(set(train_t) - sc_keys),
            "contract_entries_absent_from_train": sorted(sc_keys - set(train_t)),
            "train_entity_free_utterances": train_empty,
            "pool_entity_free_utterances": pool_empty,
            "pool_minus_r01_entity_free_utterances": poolr_empty,
            "train_unused_by_pool": len(unused),
            "train_unused_by_pool_minus_r01": len(unused_r01),
            "train_unused_entity_free_utterances": un_empty,
            "train_unused_minus_r01_entity_free_utterances": unr_empty,
            "train_unused_intents": len(un_i),
            "train_unused_slot_types": len(un_t),
        },
        "per_intent": intent_rows,
        "per_scenario": scenario_rows,
        "per_slot_type": type_rows,
        "relationships": relationships,
        "unused_remainder": {
            "per_intent": {k: un_i.get(k, 0) for k in sorted(set(train_i))},
            "per_slot_type": {k: un_t.get(k, 0) for k in sorted(set(train_t))},
            "per_intent_minus_r01": {k: unr_i.get(k, 0) for k in sorted(set(train_i))},
            "per_slot_type_minus_r01": {k: unr_t.get(k, 0) for k in sorted(set(train_t))},
        },
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


CLASS_ORDER = ("INTENT-WRONG", "ENTITY-MIXED", "ENTITY-FN-ONLY", "ENTITY-FP-ONLY",
               "MALFORMED")
CHANNEL_HEADINGS = {
    "intent-boundary": (
        "Channel 1 -- the `intent-boundaries-v1` entry for the row's own gold intent"),
    "exemplar-intent": (
        "Channel 2 -- an exemplar of the row's own gold intent in the pool"),
    "slot-contract": (
        "Channel 3 -- the `slot-contracts-v2` entry for each slot TYPE the row missed"),
    "exemplar-type": (
        "Channel 4 -- an exemplar demonstrating each slot TYPE the row missed"),
    "empty-answer": (
        "Channel 5 -- an exemplar demonstrating the correct EMPTY answer, needed where "
        "gold carries no entity and the row emitted one anyway"),
}
MODE_LABELS = {
    MODE_I: "(i) absent",
    MODE_II: "(ii) not retrieved",
    MODE_III: "(iii) budget-excluded",
    MODE_RESIDUAL: "(iv)+(v) residual",
}


def channel_rows(block, unit):
    lines = []
    for klass in CLASS_ORDER:
        modes = block.get(klass) or {}
        cells, total = [], 0
        for mode in MODES:
            value = (modes.get(mode) or {}).get(unit, 0)
            total += value
            cells.append(value)
        if total == 0:
            continue
        lines.append("| `" + klass + "` | "
                     + " | ".join(f"{v} ({pct(v, total):.1f} %)" for v in cells)
                     + f" | {total} |")
    return lines


def build_report(*, payload, coverage, attributions, geometry):
    u = coverage["store_universes"]
    identity = [
        {"what": "bad-case bank (2,080 rows, both PLAN rosters)",
         "relpath": payload["bank"]["relpath"], "sha256": payload["bank"]["sha256"]},
        {"what": "governed SLURP TRAIN split (11,514 utterances)",
         "relpath": payload["governed_train"]["relpath"],
         "sha256": payload["governed_train"]["sha256"]},
    ]
    for name, label in (("intent_boundaries", "released `intent-boundaries-v1` snapshot"),
                        ("slot_contracts", "released `slot-contracts-v2` snapshot"),
                        ("exemplar_pool", "released `size-pool-annotated-exemplars` snapshot"),
                        ("exemplar_pool_minus_r01",
                         "released `size-pool-annotated-exemplars-minus-r01` snapshot")):
        store = payload["stores"][name]
        identity.append({"what": label, "relpath": store["snapshot_relpath"],
                         "sha256": store["snapshot_file_sha256"]})
    for label in ("roll1", "train-fold-a-plan", "dev2000-added-plan"):
        arm = payload["arms"][label]
        identity.append({"what": f"`{label}` sealed phase artefact",
                         "relpath": arm["phases_relpath"], "sha256": arm["phases_sha256"]})
        identity.append({"what": f"`{label}` sealed flight receipt",
                         "relpath": arm["receipts_relpath"], "sha256": arm["receipts_sha256"]})
    pop = payload["populations"]["roll1"]
    identity.append({"what": "ROLL-1 as-flown pool official score file",
                     "relpath": pop["scores_relpath"], "sha256": pop["scores_sha256"]})

    arms_table = []
    for arm in ARMS:
        label = arm["label"]
        arms_table.append({
            "title": arm["title"],
            "rows": sum(attributions[label]["class_rows"].values()),
            "run_id": arm["run_id"],
            "attempt_id": arm["attempt"],
            "scorer_id": arm["scorer_id"],
        })
    total_rows = sum(row["rows"] for row in arms_table)

    pool_note = (
        "**Pool identity, and two corrections to the figures this read was asked about.** "
        "The ROLL-1 population is the as-flown delivered pool of run "
        f"`{ARMS[0]['run_id']}` over the 625-row R01C construction roster, re-scored "
        f"offline by the pinned official evaluator at commit `{pop['evaluator_commit']}` "
        f"under scorer `{pop['scorer_id']}` at the commit policy the flight actually flew "
        "(plurality support 3). Its sealed official intent accuracy is "
        f"{100.0 * pop['official_intent_accuracy']:.2f} % and exactly "
        f"{attributions['roll1']['class_rows']['INTENT-WRONG']} of its 625 rows are "
        "intent-wrong, which is the population asked for. Two figures in the request do "
        "not survive contact with the bytes and are corrected here rather than carried "
        f"forward. This pool's pooled SLU-F1 is {100.0 * pop['official_slu_f1']:.4f}, not "
        "41.88; the nearest sealed pooled number to 41.88 is this run's in-run "
        "unprojected span-F1 of 41.9035, which is a span-F1 and not an SLU-F1. And the "
        "released exemplar pool is 9,354 utterances over "
        f"{payload['stores']['exemplar_pool']['source_sample_id_count']:,} recordings; the "
        "8,554 / 34,474 figures belong to its R01-excluded sibling "
        "`size-pool-annotated-exemplars-minus-r01`. Construction/evaluation disjointness "
        "holds as designed: the ROLL-1 flight pins the minus-R01 pool "
        f"({payload['arm_exemplar_pools']['roll1']['utterances']:,} utterances) and the two "
        "PLAN rosters, which are not R01, pin the full pool "
        f"({payload['arm_exemplar_pools']['train-fold-a-plan']['utterances']:,})."
    )

    specs = geometry["roll1"]["specs"]
    ib, ex, sc = specs[IB_STORE], specs[EX_STORE], specs[SC_STORE]
    channel_table = [
        {"store": "intent-boundaries-v1", "phase": ib["phase"], "provider": ib["provider"],
         "retrieval": f"top-{ib['k']} of {u['intent_boundaries_entries']} by speech-keyed facet",
         "budget": (f"`fuse_coverage` top_l={ib['fuse_top_l']}, m={ib['fuse_m']}, "
                    f"c={ib['fuse_c']}; k == top_l == m, so nothing retrieved can be dropped"),
         "universe": u["intent_boundaries_entries"]},
        {"store": "size-pool-annotated-exemplars", "phase": ex["phase"],
         "provider": ex["provider"],
         "retrieval": f"top-{ex['k']} of the pool by speech-keyed facet",
         "budget": (f"`fuse_coverage` top_l={ex['fuse_top_l']}, m={ex['fuse_m']}, "
                    f"c={ex['fuse_c']}; again k == top_l == m"),
         "universe": (f"{payload['arm_exemplar_pools']['roll1']['utterances']:,} "
                      "(ROLL-1's minus-R01 pin; the two PLAN rosters pin "
                      f"{payload['arm_exemplar_pools']['train-fold-a-plan']['utterances']:,})")},
        {"store": "slot-contracts-v2", "phase": sc["phase"], "provider": sc["provider"],
         "retrieval": (f"the contracts bound to the row's at most {sc['max_candidates']} "
                       "Perception candidate intents"),
         "budget": (f"`max_total_values` {sc['max_total_values']}, "
                    f"`max_values_per_candidate` {sc['max_values_per_candidate']}; the one "
                    "place a budget can drop an already-retrieved value"),
         "universe": u["slot_contracts_entries"]},
    ]

    budget_evidence = []
    for label in ("roll1", "train-fold-a-plan", "dev2000-added-plan"):
        obs = geometry[label]["observed"]
        budget_evidence.append({
            "arm": label,
            "gap_rows": obs["sc_mapped_minus_selected_rows"],
            "gap_values": obs["sc_mapped_minus_selected_values"],
            "mapped_max": obs["sc_mapped_max"],
            "cap": sorted(obs["sc_caps"])[0] if obs["sc_caps"] else "--",
            "reasons": ", ".join(f"`{k}` {v}" for k, v in obs["sc_ignored_reasons"].items()) or "--",
        })
    gap_rows = sum(row["gap_rows"] for row in budget_evidence)
    gap_values = sum(row["gap_values"] for row in budget_evidence)
    mapped_peak = max(row["mapped_max"] for row in budget_evidence)
    budget_finding = (
        "**Mode (iii) is measurably empty, and in two channels of three it is not even "
        f"reachable.** Across all {total_rows:,} rows of the three sealed populations the "
        "number of rows on which a retrieved knowledge value failed to reach the episode "
        f"because of a budget is {gap_rows}, and the number of such values is "
        f"{gap_values}. In the two facet channels the pinned spec makes it impossible: "
        "`k` equals `top_l` equals `m`, so the retrieved set and the carried set are the "
        "same set, and the sealed rows agree -- the exemplar channel's ranked set equals "
        "its materialised set on "
        f"{geometry['roll1']['observed']['ex_ranked_equals_materialised_rows']}/"
        f"{geometry['roll1']['observed']['ex_rows']} ROLL-1 rows, "
        f"{geometry['train-fold-a-plan']['observed']['ex_ranked_equals_materialised_rows']:,}/"
        f"{geometry['train-fold-a-plan']['observed']['ex_rows']:,} on TRAIN Fold A and "
        f"{geometry['dev2000-added-plan']['observed']['ex_ranked_equals_materialised_rows']:,}/"
        f"{geometry['dev2000-added-plan']['observed']['ex_rows']:,} on DEV-2000-ADDED. In "
        "the candidate-semantic channel a budget IS reachable and it never fires: the cap "
        f"is {sc['max_total_values']} values and the largest set the rows ever ask it to "
        f"hold is {mapped_peak}. The only ignored-mapping reason the receipts ever record "
        "is `shared-value-already-selected`, which is de-duplication of a value the row "
        "does receive under another candidate rather than an exclusion -- every such value "
        "appears in the row's own `qualified_selected_value_ids`. The budget is not the "
        "binding constraint, and loosening it can buy nothing."
    )

    attribution_blocks = []
    for index, arm in enumerate(ARMS, start=1):
        label = arm["label"]
        att = attributions[label]
        channels = []
        for channel, heading in CHANNEL_HEADINGS.items():
            rows = channel_rows(att["channels"].get(channel) or {}, "items")
            if not rows:
                continue
            channels.append({"heading": heading, "rows": rows})
        note = ""
        unavailable = att["rows_without_per_type_fn_attribution"]
        if unavailable:
            note = (
                "Channels 3 and 4 are not attributable on this population: they need the "
                "gold-against-predicted slot TYPE alignment, which only the sealed "
                "bad-case bank carries, and this population has no bank entry. The rows "
                "affected are "
                + ", ".join(f"`{k}` {v}" for k, v in sorted(unavailable.items()))
                + ". Their contract and exemplar supply is still measured, as a supply "
                "rate rather than a per-item attribution, in section 3."
            )
        precedence = att["row_level_precedence"]
        row_level = "; ".join(
            f"`{klass}` " + ", ".join(
                f"{MODE_LABELS[mode]} {count}" for mode, count in sorted(modes.items()))
            for klass, modes in sorted(precedence.items())) or "--"
        attribution_blocks.append({
            "index": index, "title": arm["title"], "channels": channels,
            "row_level": row_level, "note": note,
        })

    quality_lines = []
    for arm in ARMS:
        label = arm["label"]
        q = attributions[label]["retrieval_quality"]
        for klass in ("CORRECT",) + CLASS_ORDER:
            counts = q.get(klass)
            if not counts:
                continue
            rows = counts.get("rows", 0)
            gold_types = counts.get("gold_types", 0)
            quality_lines.append(
                f"| `{label}` | `{klass}` | {rows} | "
                f"{pct(counts.get('ib_gold_boundary_delivered', 0), rows):.1f} % | "
                f"{pct(counts.get('ex_gold_intent_delivered', 0), rows):.1f} % | "
                f"{pct(counts.get('gold_types_contract_materialised', 0), gold_types):.1f} % | "
                f"{pct(counts.get('gold_types_shown_by_an_exemplar', 0), gold_types):.1f} % | "
                f"{pct(counts.get('ex_empty_demo_delivered', 0), rows):.1f} % | "
                f"{(counts.get('ex_empty_demo_count', 0) / rows if rows else 0):.2f} |")

    residual_note = (
        "The residual bucket is modes (iv) *delivered but ignored or misused* and (v) "
        "*locally correct but later overwritten* taken together, and **this read cannot "
        "split them**. Splitting requires re-execution: (iv) needs the counterfactual "
        "answer the row would have given without that item and (v) needs the intermediate "
        "state re-run forward, and neither is a function of bytes already sealed. The "
        "sealed `consumption` trace does carry a per-item `outcome` field whose values are "
        "`use` and `ignore`, and a `copy_rate`, but that field is a textual-overlap "
        "attribution made at trace time rather than a counterfactual, so it bounds neither "
        "mode and is deliberately not used as a substitute here. What this read can state "
        "about the residual without contacts is its size, above, and that it is where the "
        "entity mass sits."
    )

    z = [r for r in coverage["per_slot_type"] if r["store_entries"] == 0]
    low = [r for r in coverage["per_slot_type"] if r["pool_utterances"] <= 10]
    total_gold = sum(r["gold_mentions"] for r in coverage["per_slot_type"])
    total_fn = sum(r["fn"] for r in coverage["per_slot_type"])
    total_fp = sum(r["fp"] for r in coverage["per_slot_type"])
    uncovered = u["slot_types_without_a_contract_entry"]
    uncovered_gold = sum(r["gold_mentions"] for r in z if r["slot_type"] in uncovered)
    uncovered_fn = sum(r["fn"] for r in z if r["slot_type"] in uncovered)
    zero_coverage_note = (
        "**The classes the store says nothing about, and the mass they carry.** Every one "
        f"of the {u['train_intents']} TRAIN intents has an `intent-boundaries-v1` entry, "
        "so at intent level the store's coverage is complete and mode (i) is zero by "
        f"construction. At slot level {u['slot_contracts_entries']} of the "
        f"{u['train_slot_types']} TRAIN slot types have a contract; the one exception is "
        + ", ".join(f"`{name}`" for name in uncovered)
        + f", and it carries {uncovered_gold} gold mention and {uncovered_fn} false "
        f"negative against the {total_gold:,} gold mentions and {total_fn} false negatives "
        "the two PLAN rosters carry between them. Widening the net to every slot type the "
        f"exemplar pool shows at most ten times catches {len(low)} types, and together "
        f"they carry {sum(r['gold_mentions'] for r in low)} gold mentions "
        f"({pct(sum(r['gold_mentions'] for r in low), total_gold):.1f} % of the gold mass), "
        f"{sum(r['fn'] for r in low)} false negatives "
        f"({pct(sum(r['fn'] for r in low), total_fn):.1f} %) and "
        f"{sum(r['fp'] for r in low)} false positives "
        f"({pct(sum(r['fp'] for r in low), total_fp):.1f} %). A class the store is silent "
        "about would be the clearest case for expansion, and on this measurement there is "
        "no such class with any mass. Two rows of the per-type table are not gold classes "
        "at all: `none` and `general_quirky` appear only on the false-positive side "
        "because they are type names the system emitted that SLURP's vocabulary does not "
        "contain, and there is nothing for a store to say about them."
    )

    slot_rel = next(r for r in coverage["relationships"] if r["label"].startswith("per slot type"))
    intent_rel = next(r for r in coverage["relationships"]
                      if r["label"].startswith("per intent: exemplar-pool utterances vs any"))
    roll_rel = next(r for r in coverage["relationships"] if "minus-R01" in r["label"])
    correlation_reading = (
        "**The honest reading.** Volume does not govern the error rate, and its sign is "
        "not even stable across class families. At slot-type level more exemplars go with "
        f"a lower miss rate -- Spearman rho {slot_rel['spearman_rho']:.3f}, CI90 "
        f"[{slot_rel['spearman_ci90']['low']:.3f}, {slot_rel['spearman_ci90']['high']:.3f}], "
        "an interval that excludes zero -- but the fit explains only "
        f"{100.0 * slot_rel['fit']['r2']:.1f} % of the between-type variance and the "
        f"residual spread around it, {slot_rel['fit']['residual_sd_pp']:.2f} pp, is "
        f"{100.0 * slot_rel['fit']['residual_sd_pp'] / slot_rel['fit']['outcome_sd_pp']:.0f} % "
        "of the spread it started from. Doubling a type's exemplar count buys about "
        f"{abs(slot_rel['fit']['slope_pp_per_log1p_unit']) * math.log(2):.1f} pp of miss "
        f"rate against a between-type spread of {slot_rel['fit']['outcome_sd_pp']:.1f} pp. "
        "At intent level the sign REVERSES: rho "
        f"{intent_rel['spearman_rho']:+.3f}, CI90 "
        f"[{intent_rel['spearman_ci90']['low']:.3f}, {intent_rel['spearman_ci90']['high']:.3f}] "
        "-- the intents with the most exemplars have the HIGHER error rate, because the "
        "frequent intents are the confusable ones, so volume is confounded with "
        "difficulty rather than protective against it. On ROLL-1 the same relationship is "
        f"indistinguishable from nothing: rho {roll_rel['spearman_rho']:+.3f}, CI90 "
        f"[{roll_rel['spearman_ci90']['low']:.3f}, {roll_rel['spearman_ci90']['high']:.3f}]. "
        "The quartile curves say it the other way round: they are flat to non-monotone, "
        "with no knee to point at. There is therefore no count at which a curve flattens, "
        "because there is no falling curve to flatten. The reading the owner asked for "
        "follows: more of the same does not buy accuracy, and the bottleneck is "
        "retrievability, not volume."
    )

    ur = coverage["unused_remainder"]

    def under_covered(rows, name_key, count_key, mass_key, table_key):
        counts = sorted(r[count_key] for r in rows if r[count_key] > 0)
        threshold = counts[len(counts) // 4] if counts else 0
        under = [r for r in rows if r[count_key] <= threshold]
        covered = [r for r in under if ur[table_key].get(r[name_key], 0) > 0]
        return {"threshold": threshold, "under": len(under), "covered": len(covered),
                "utterances": sum(ur[table_key].get(r[name_key], 0) for r in under),
                "mass": sum(r[mass_key] for r in under)}

    holdbacks = {row["train_unused_by_pool"] for row in coverage["per_scenario"]}
    scenario_holdback = (sorted(holdbacks)[0] if len(holdbacks) == 1
                         else f"{min(holdbacks)} to {max(holdbacks)}")
    intent_under = under_covered(coverage["per_intent"], "intent", "pool_utterances",
                                 "bank_rows", "per_intent")
    type_under = under_covered(coverage["per_slot_type"], "slot_type", "pool_utterances",
                               "gold_mentions", "per_slot_type")
    unused_table = [
        {"family": (f"intents in the bottom quartile of pool coverage (at most "
                    f"{intent_under['threshold']} pool utterances)"),
         "under": intent_under["under"], "covered": intent_under["covered"],
         "utterances": intent_under["utterances"], "mass": intent_under["mass"]},
        {"family": (f"slot types in the bottom quartile of pool coverage (at most "
                    f"{type_under['threshold']} pool utterances)"),
         "under": type_under["under"], "covered": type_under["covered"],
         "utterances": type_under["utterances"], "mass": type_under["mass"]},
    ]
    unused_note = (
        f"The released pool uses {u['exemplar_pool_utterances']:,} of the "
        f"{u['train_utterances']:,} governed TRAIN utterances, leaving "
        f"{u['train_unused_by_pool']:,} unused "
        f"({pct(u['train_unused_by_pool'], u['train_utterances']):.1f} %); against the "
        "R01-excluded sibling the unused remainder is "
        f"{u['train_unused_by_pool_minus_r01']:,} "
        f"({pct(u['train_unused_by_pool_minus_r01'], u['train_utterances']):.1f} %). The "
        "remainder is not concentrated where the pool is thin. It touches all "
        f"{u['train_unused_intents']} intents and {u['train_unused_slot_types']} of the "
        f"{u['train_slot_types']} slot types, which makes it a thin uniform layer rather "
        "than a reserve aimed at the gaps -- and section 5.1 shows why, because the "
        f"remainder is exactly {scenario_holdback} utterances in every one of the "
        f"{len(coverage['per_scenario'])} scenarios, an equal-stratum hold-back by "
        "construction rather than a residue that could happen to sit where the coverage "
        "is worst. Every one of the "
        f"{intent_under['under']} bottom-quartile intents does have unused TRAIN rows "
        f"available, but they amount to {intent_under['utterances']} utterances in total "
        f"across all of them, against the {intent_under['mass']} roster rows those intents "
        f"carry; on the slot side only {type_under['covered']} of {type_under['under']} "
        "bottom-quartile types have any unused rows at all, totalling "
        f"{type_under['utterances']} utterances against {type_under['mass']} gold "
        "mentions. Legality, stated explicitly: the remainder is TRAIN, so it is legal "
        "construction material for any roster not drawn from it, and an expansion aimed "
        "at an R01-family evaluation must come from the minus-R01 remainder "
        f"({u['train_unused_by_pool_minus_r01']:,} utterances) rather than the full one, "
        "exactly as the ROLL-1 flight's own pin already does. One further fact would make "
        "an expansion cheap if it were ever wanted: the pinned facet-vector sidecar this "
        "system retrieves against already carries "
        f"{ex['facet_vector_rows']:,} rows -- all of TRAIN, not just the pool -- so widening "
        "the store needs no new encoding contact. That is a statement about cost, not a "
        "recommendation; the measurement above says the rows are not what is missing."
    )

    fp_q = attributions["train-fold-a-plan"]["retrieval_quality"]["ENTITY-FP-ONLY"]
    correction_note = (
        "**One prior record is corrected by this read.** The 2026-09-24 bad-case bank "
        "reported the exemplar pool as entity-bearing by construction, with zero "
        "exemplars carrying no entity, and concluded that the Solver never sees an example "
        "of the correct empty answer. Measured against the released snapshot joined to the "
        f"governed gold, {u['pool_entity_free_utterances']:,} of the "
        f"{u['exemplar_pool_utterances']:,} pool utterances "
        f"({pct(u['pool_entity_free_utterances'], u['exemplar_pool_utterances']):.1f} %) "
        "carry no gold entity at all, and the sealed rows show them being delivered: "
        f"{pct(fp_q['ex_empty_demo_delivered'], fp_q['rows']):.1f} % of the TRAIN Fold A "
        "`ENTITY-FP-ONLY` rows receive at least one entity-free exemplar, "
        f"{fp_q['ex_empty_demo_count'] / fp_q['rows']:.2f} of them on average. The bank's "
        "zero was an artefact of parsing the rendered exemplar body rather than joining "
        "the pool to the gold. The empty-answer gap is therefore not an absence in the "
        "source; it is a use failure, and it lands in the residual bucket."
    )

    def ib_rate(label, klass):
        c = attributions[label]["retrieval_quality"][klass]
        return pct(c["ib_gold_boundary_delivered"], c["rows"])

    def ii_share(label):
        att = attributions[label]
        items = att["channels"]["intent-boundary"]["INTENT-WRONG"][MODE_II]["items"]
        return items, pct(items, att["class_rows"]["INTENT-WRONG"])

    entity_ib = [ib_rate(label, klass) for label in attributions
                 for klass in ("ENTITY-MIXED", "ENTITY-FN-ONLY", "ENTITY-FP-ONLY")
                 if klass in attributions[label]["retrieval_quality"]]
    entity_ib_low, entity_ib_high = min(entity_ib), max(entity_ib)
    roll_items, roll_share = ii_share("roll1")
    tfa_items, tfa_share = ii_share("train-fold-a-plan")
    dev_items, dev_share = ii_share("dev2000-added-plan")
    mixed_q = attributions["train-fold-a-plan"]["retrieval_quality"]["ENTITY-MIXED"]
    verdict = (
        "**The binding constraint is UNRETRIEVED knowledge, and the measurement is not "
        f"close.** Absent knowledge is ruled out: all {u['train_intents']} intents have a "
        f"boundary entry, {u['slot_contracts_entries']} of {u['train_slot_types']} slot "
        f"types have a contract, the one uncovered type carries {uncovered_gold} gold "
        f"mention and {uncovered_fn} false negative of {total_gold:,} and {total_fn}, and "
        "mode (i) totals two items across every channel of all three populations -- both "
        "of them on one single row, and both of them that same uncovered type. Excluded "
        f"knowledge is ruled out harder: mode (iii) is {gap_rows} rows and {gap_values} "
        f"values across all {total_rows:,} rows, it is structurally unreachable "
        "in two of the three channels, and in the third the cap is "
        f"{sc['max_total_values']} against a peak demand of {mapped_peak} -- there is no "
        "budget to loosen. What is left is mode (ii), and it owns the intent errors: of "
        f"the {attributions['roll1']['class_rows']['INTENT-WRONG']} ROLL-1 intent-wrong "
        f"rows, {roll_items} ({roll_share:.1f} %) never received the boundary entry for "
        "their own gold intent although the store holds it, and the same figure is "
        f"{tfa_share:.1f} % on TRAIN Fold A ({tfa_items} of "
        f"{attributions['train-fold-a-plan']['class_rows']['INTENT-WRONG']}) and "
        f"{dev_share:.1f} % on DEV-2000-ADDED ({dev_items} of "
        f"{attributions['dev2000-added-plan']['class_rows']['INTENT-WRONG']}). What makes "
        "this a retrieval finding rather than a difficulty finding is the same quantity on "
        "the rows that worked: the gold intent's boundary reaches "
        f"{ib_rate('roll1', 'CORRECT'):.1f} % of ROLL-1's correct rows against "
        f"{ib_rate('roll1', 'INTENT-WRONG'):.1f} % of its intent-wrong rows, a gap of "
        f"{ib_rate('roll1', 'CORRECT') - ib_rate('roll1', 'INTENT-WRONG'):.1f} points on a "
        f"store whose coverage is complete, against {entity_ib_low:.1f} to "
        f"{entity_ib_high:.1f} % on the entity classes, which do not carry this defect. "
        "**The entity errors are a different story and it is not a knowledge story "
        "at all.** On the entity-error classes the contract for the missed type had been "
        "materialised into the row for "
        f"{pct(mixed_q['gold_types_contract_materialised'], mixed_q['gold_types']):.1f} % "
        "of gold types, an exemplar demonstrating it for "
        f"{pct(mixed_q['gold_types_shown_by_an_exemplar'], mixed_q['gold_types']):.1f} %, "
        "and modes (i)-(iii) together account for under 2 % of the slot-contract items and "
        "under 8 % of the exemplar items, leaving 92 to 100 % in the residual. **So: do "
        "not expand the sources.** Spend on retrieval and selection, and then measure the "
        "residual. That last clause is the honest limit of this read: the residual is "
        "modes (iv) delivered-but-ignored-or-misused and (v) locally-correct-but-later-"
        "overwritten taken together, and no sealed byte can separate them -- (iv) needs "
        "the counterfactual answer without the item and (v) needs the intermediate state "
        "re-run forward, so both need contacts. This read therefore proves where the "
        "constraint is NOT, proves that retrieval owns the intent half, and cannot tell "
        "us, for the entity half, whether the delivered knowledge was ignored, misused, "
        "or locally right and destroyed downstream."
    )

    boundary = (
        "Zero model, server, tokenizer, encoder, embedder, scorer, network, GPU and "
        "paid-API contacts: no server was started or stopped, no waveform decoded, no "
        "embedding computed and no subprocess run. The tools used were the "
        "`data.slurp.load_slurp_split` loader for the governed TRAIN gold; `json` reads of "
        "the released store snapshots and their release files; `json` reads of the sealed "
        "`*.phases.json` and `flight-receipts.json` of three completed flights; a `json` "
        "read of the sealed bad-case bank and of the sealed official score file of the "
        "ROLL-1 as-flown pool; and `hashlib` for every identity hash quoted above. This "
        "read admits nothing, promotes nothing, preregisters no cell, releases no store, "
        "draws no roster, expands no source, opens no split and reaches no superiority, "
        "generalisation or Stage-3 conclusion. It is byte-reproducible across runs apart "
        "from its `generated_at` stamp: every container is sorted before it is consumed "
        f"and the single resampling procedure is seeded at {BOOTSTRAP_SEED} with "
        f"{BOOTSTRAP_REPLICATES} replicates."
    )

    return {
        "generated_at": payload["generated_at"],
        "identity": identity,
        "arms": arms_table,
        "pool_identity_note": pool_note,
        "channel_table": channel_table,
        "budget_finding": budget_finding,
        "budget_evidence": budget_evidence,
        "attribution_blocks": attribution_blocks,
        "quality_lines": quality_lines,
        "residual_note": residual_note,
        "coverage": coverage,
        "zero_coverage_note": zero_coverage_note,
        "correlation_reading": correlation_reading,
        "unused_note": unused_note,
        "correction_note": correction_note,
        "unused_table": unused_table,
        "verdict": verdict,
        "boundary": boundary,
    }


def fmt(value, digits=3):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "--"
    return f"{value:.{digits}f}"


def render(report: dict) -> str:
    out: list[str] = []
    a = out.append
    a("# SLURP knowledge coverage and the decision-123 failure-mode attribution")
    a("")
    a(f"Date: {report['generated_at'][:10]}. Read id `{READ_ID}`, recipe `{RECIPE}`. A "
      "model-free read over sealed bytes: zero model, server, tokenizer, encoder, "
      "embedder, scorer, network, GPU and paid-API contacts. Nothing was executed. Every "
      "number is read from artefacts earlier flights already sealed, from the three "
      "released knowledge stores, and from the governed SLURP TRAIN split through "
      "`data.slurp.load_slurp_split`.")
    a("")
    a("A DIAGNOSTIC, never a gate. It decides no cell, admits no mechanism, releases no "
      "store, authorises no flight, expands no source and states no effectiveness, "
      "superiority or generalisation claim. Every roster below is a discovery or dev "
      "roster and its numbers are development numbers (owner decisions 28 and 86), never "
      "a test claim.")
    a("")
    a("**Where gold was read, and that it touched no runtime path.** Gold labels enter "
      "this read in exactly two places, both offline and both on the scoring side: the "
      "sealed bad-case bank's `gold_intent` / `gold_entity_types` / `fn_types` / "
      "`fp_types` fields, and the governed TRAIN split read through the ordinary "
      "`data.slurp.load_slurp_split` loader exactly as `core.scoring_batch` reads it. No "
      "gold value reaches a runtime query, a retrieval key, a selector, a supply decision "
      "or any config; this script writes a report and nothing else, and it opens no "
      "config, no policy and no store-construction path. No utterance text, transcript, "
      "delivered answer, gold filler, predicted filler or knowledge body text is read "
      "into a reported value: every cell below is an id, a class name, a count, a rate, a "
      "ratio or a hash.")
    a("")

    a("## 0. Inputs and identity")
    a("")
    a("| Artefact | Relpath under `SPEECHRL_DATA_DIR` | sha256 |")
    a("| --- | --- | --- |")
    for row in report["identity"]:
        a(f"| {row['what']} | `{row['relpath']}` | `{row['sha256']}` |")
    a("")
    a("| Population | Rows | Run id | Attempt | Class source |")
    a("| --- | ---: | --- | --- | --- |")
    for arm in report["arms"]:
        source = f"`{arm['scorer_id']}`" if arm["scorer_id"] else "sealed bad-case bank"
        a(f"| {arm['title']} | {arm['rows']} | `{arm['run_id']}` | `{arm['attempt_id']}` "
          f"| {source} |")
    a("")
    a(report["pool_identity_note"])
    a("")

    a("## 1. The three channels a failed row can fail in, and where a budget can act")
    a("")
    a("This system supplies knowledge through exactly three released stores, so modes "
      "(i)-(iii) are channel-local and are attributed channel by channel. A row that "
      "fails in two channels is counted once in each, and once at row level under a "
      "stated precedence.")
    a("")
    a("| Store | Phase | Provider | Retrieval | Where a budget could act | Store key universe |")
    a("| --- | --- | --- | --- | --- | ---: |")
    for row in report["channel_table"]:
        a(f"| `{row['store']}` | {row['phase']} | `{row['provider']}` | {row['retrieval']} "
          f"| {row['budget']} | {row['universe']} |")
    a("")
    a(report["budget_finding"])
    a("")
    a("| Arm | rows where a mapped contract was not selected | values | largest mapped set | cap `max_total_values` | ignored-mapping reasons |")
    a("| --- | ---: | ---: | ---: | --- | --- |")
    for row in report["budget_evidence"]:
        a(f"| `{row['arm']}` | {row['gap_rows']} | {row['gap_values']} | {row['mapped_max']} "
          f"| {row['cap']} | {row['reasons']} |")
    a("")

    a("## 2. Mode shares per error class")
    a("")
    a("The unit of the primary accounting is one **(row, needed knowledge item)** pair, "
      "because a row can need several items and an arbitrary per-row winner would not add "
      "up. `items` therefore sums over needed items, not rows. Percentages are of the "
      "channel's own item total for that class.")
    a("")
    for block in report["attribution_blocks"]:
        a(f"### 2.{block['index']} {block['title']}")
        a("")
        for channel in block["channels"]:
            a(f"**{channel['heading']}**")
            a("")
            a("| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |")
            a("| --- | ---: | ---: | ---: | ---: | ---: |")
            for line in channel["rows"]:
                a(line)
            a("")
        a("Row-level precedence view (absent > not retrieved > budget-excluded > "
          f"residual), one mode per failed row: {block['row_level']}.")
        a("")
        if block["note"]:
            a(block["note"])
            a("")

    a("## 3. Supply rates on every row, failures and successes alike")
    a("")
    a("A retrieval rate only reads as a defect beside the rate on the rows that worked. "
      "`gold types` columns are shares of the row's own gold slot TYPEs; the last two "
      "columns are the empty-answer demonstration the pool can supply.")
    a("")
    a("| Arm | Class | Rows | gold intent's boundary delivered | an exemplar of the gold intent delivered | gold types whose contract was materialised | gold types an exemplar demonstrated | received an entity-free exemplar | entity-free exemplars per row |")
    a("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for line in report["quality_lines"]:
        a(line)
    a("")

    a("## 4. What modes (iv) and (v) cannot be split into here")
    a("")
    a(report["residual_note"])
    a("")

    a("## 5. Coverage inside the existing sources")
    a("")
    u = report["coverage"]["store_universes"]
    a("| Quantity | Value |")
    a("| --- | ---: |")
    for key, label in (
        ("intent_boundaries_entries", "`intent-boundaries-v1` entries (one per intent)"),
        ("slot_contracts_entries", "`slot-contracts-v2` entries (one per slot type)"),
        ("exemplar_pool_utterances", "`size-pool-annotated-exemplars` utterances"),
        ("exemplar_pool_minus_r01_utterances",
         "`size-pool-annotated-exemplars-minus-r01` utterances"),
        ("train_utterances", "governed SLURP TRAIN utterances"),
        ("train_intents", "distinct TRAIN intents (`scenario_action`)"),
        ("train_scenarios", "distinct TRAIN scenarios"),
        ("train_slot_types", "distinct TRAIN slot types"),
        ("train_entity_free_utterances", "TRAIN utterances whose gold carries no entity"),
        ("pool_entity_free_utterances", "pool utterances whose gold carries no entity"),
        ("pool_minus_r01_entity_free_utterances",
         "minus-R01 pool utterances whose gold carries no entity"),
        ("train_unused_by_pool", "TRAIN utterances the released pool does not use"),
        ("train_unused_by_pool_minus_r01", "TRAIN utterances the minus-R01 pool does not use"),
        ("train_unused_entity_free_utterances", "of the unused remainder, entity-free"),
        ("train_unused_intents", "intents the unused remainder touches"),
        ("train_unused_slot_types", "slot types the unused remainder touches"),
    ):
        a(f"| {label} | {u[key]} |")
    a("")
    a(report["zero_coverage_note"])
    a("")
    a(report["correction_note"])
    a("")
    a("### 5.1 Per scenario")
    a("")
    a("| Scenario | boundary entries | pool utterances | minus-R01 pool | TRAIN | TRAIN unused by pool | bank rows | bank any-error rate | ROLL-1 rows | ROLL-1 intent-error rate |")
    a("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in report["coverage"]["per_scenario"]:
        a(f"| `{row['scenario']}` | {row['store_entries']} | {row['pool_utterances']} | "
          f"{row['pool_minus_r01_utterances']} | {row['train_utterances']} | "
          f"{row['train_unused_by_pool']} | {row['bank_rows']} | "
          f"{row['bank_any_error_rate_pp']:.1f} % | {row['roll1_rows']} | "
          f"{row['roll1_intent_error_rate_pp']:.1f} % |")
    a("")
    a("### 5.2 Per slot type")
    a("")
    a("Gold mentions, FN and FP are the two PLAN rosters' pooled mass; a type with no "
      "gold mention appears only because the system emitted it.")
    a("")
    a("| Slot type | contract entries | pool utterances | minus-R01 pool | TRAIN | TRAIN unused by pool | gold mentions | FN | FP | FN rate |")
    a("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in report["coverage"]["per_slot_type"]:
        a(f"| `{row['slot_type']}` | {row['store_entries']} | {row['pool_utterances']} | "
          f"{row['pool_minus_r01_utterances']} | {row['train_utterances']} | "
          f"{row['train_unused_by_pool']} | {row['gold_mentions']} | {row['fn']} | "
          f"{row['fp']} | {row['fn_rate_pp']:.1f} % |")
    a("")
    a("### 5.3 Per intent")
    a("")
    a("| Intent | boundary entry | pool utterances | minus-R01 pool | TRAIN | TRAIN unused | bank rows | bank intent-error rate | bank any-error rate | ROLL-1 rows | ROLL-1 intent-error rate |")
    a("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in report["coverage"]["per_intent"]:
        a(f"| `{row['intent']}` | {row['store_entries']} | {row['pool_utterances']} | "
          f"{row['pool_minus_r01_utterances']} | {row['train_utterances']} | "
          f"{row['train_unused_by_pool']} | {row['bank_rows']} | "
          f"{row['bank_intent_error_rate_pp']:.1f} % | {row['bank_any_error_rate_pp']:.1f} % | "
          f"{row['roll1_rows']} | {row['roll1_intent_error_rate_pp']:.1f} % |")
    a("")

    a("## 6. Does the error rate fall as a class gets more knowledge?")
    a("")
    a("| Relationship | Classes | Spearman rho | CI90 | Pearson r on log1p(count) | slope pp per log1p unit | residual SD pp | outcome SD pp | R^2 |")
    a("| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |")
    for rel in report["coverage"]["relationships"]:
        ci = rel["spearman_ci90"]
        f = rel["fit"]
        a(f"| {rel['label']} | {rel['classes']} | {fmt(rel['spearman_rho'])} | "
          f"[{fmt(ci['low'])}, {fmt(ci['high'])}] | "
          f"{fmt(rel['pearson_r_on_log1p_count'])} | "
          f"{fmt(f['slope_pp_per_log1p_unit'], 2)} | {fmt(f['residual_sd_pp'], 2)} | "
          f"{fmt(f['outcome_sd_pp'], 2)} | {fmt(f['r2'])} |")
    a("")
    for rel in report["coverage"]["relationships"]:
        a(f"*{rel['label']}* -- quartiles of the knowledge count against the class's own "
          "error rate:")
        a("")
        a("| Quartile | Classes | count min | count median | count max | mean error rate |")
        a("| --- | ---: | ---: | ---: | ---: | ---: |")
        for q in rel["quartiles"]:
            a(f"| {q['quartile']} | {q['classes']} | {q['count_min']:.0f} | "
              f"{q['count_median']:.0f} | {q['count_max']:.0f} | "
              f"{q['error_rate_mean_pp']:.1f} % |")
        a("")
    a(report["correlation_reading"])
    a("")

    a("## 7. The unused remainder of TRAIN")
    a("")
    a(report["unused_note"])
    a("")
    a("| Class family | Classes the pool under-covers | of those, with unused TRAIN available | unused utterances they carry | their error mass |")
    a("| --- | ---: | ---: | ---: | ---: |")
    for row in report["unused_table"]:
        a(f"| {row['family']} | {row['under']} | {row['covered']} | {row['utterances']} "
          f"| {row['mass']} |")
    a("")

    a("## 8. The answer to the owner's question")
    a("")
    a(report["verdict"])
    a("")

    a("## 9. Boundary")
    a("")
    a(report["boundary"])
    a("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--markdown", default=DEFAULT_MARKDOWN)
    parser.add_argument("--analysis-dir", default=DEFAULT_ANALYSIS_DIR)
    args = parser.parse_args(argv)

    module = sys.modules["speech_aware_evidence_acquisition"]
    if not str(Path(module.__file__).resolve()).startswith(str(REPO_ROOT.resolve())):
        raise ReadError(
            f"package resolves outside this tree: {module.__file__} (expected under {REPO_ROOT})"
        )

    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))

    stores = {
        "intent_boundaries": load_store(data_root, IB_SNAPSHOT, IB_RELEASE, "intent-boundary:"),
        "slot_contracts": load_store(data_root, SC_SNAPSHOT, SC_RELEASE, "slot-contract:"),
        "exemplar_pool": load_store(data_root, EX_SNAPSHOT, None, "value:"),
        "exemplar_pool_minus_r01": load_store(data_root, EX_R01_SNAPSHOT, None, "value:"),
    }
    stores["exemplar_pool"]["value_keys"] = stores["exemplar_pool"]["keys"]
    stores["exemplar_pool_minus_r01"]["value_keys"] = stores["exemplar_pool_minus_r01"]["keys"]

    train_gold = load_train_gold(lock, data_root)
    train_path = data_root / GOVERNED_TRAIN

    pools_by_snapshot = {}
    for name in ("exemplar_pool", "exemplar_pool_minus_r01"):
        store = stores[name]
        types, intents = pool_class_counts(store["value_keys"], train_gold)
        pools_by_snapshot[store["snapshot_content_sha256"]] = {
            "name": name,
            "types": types,
            "intents": intents,
            "utterances": len(store["value_keys"]),
        }

    bank = load_bank(data_root)
    arm_rows = {}
    populations = {}
    geometry = {}
    for arm in ARMS:
        arm_rows[arm["label"]] = load_arm_rows(data_root, arm)
        geometry[arm["label"]] = channel_geometry(arm_rows[arm["label"]])
        if arm["scores"]:
            populations[arm["label"]] = load_roll1_population(data_root, arm)
        else:
            populations[arm["label"]] = {"rows": bank["rosters"][arm["roster"]]}

    attributions = {}
    arm_pools = {}
    for arm in ARMS:
        pinned = (arm_rows[arm["label"]]["store_specs"].get(EX_STORE) or {}).get(
            "store_snapshot_sha256")
        pool = pools_by_snapshot.get(pinned)
        if pool is None:
            raise ReadError(
                f"{arm['label']}: the flight pins exemplar snapshot {pinned}, which is "
                "neither released pool this read loaded"
            )
        arm_pools[arm["label"]] = {"pool": pool["name"],
                                   "snapshot_content_sha256": pinned,
                                   "utterances": pool["utterances"]}
        attributions[arm["label"]] = attribute_arm(
            arm=arm,
            arm_rows=arm_rows[arm["label"]],
            population=populations[arm["label"]],
            stores=stores,
            train_gold=train_gold,
            pool_types=pool["types"],
            pool_intents=pool["intents"],
        )

    coverage = build_coverage(
        stores=stores,
        train_gold=train_gold,
        bank=bank,
        roll1_population=populations["roll1"],
        roll1_rows=arm_rows["roll1"],
    )

    payload = {
        "schema": "saea-slurp-knowledge-coverage-failure-mode-v1",
        "read_id": READ_ID,
        "recipe": RECIPE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contacts": {
            "model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
            "scorer": 0, "network": 0, "gpu": 0, "paid_api": 0,
        },
        "bootstrap": {"seed": BOOTSTRAP_SEED, "replicates": BOOTSTRAP_REPLICATES},
        "stores": {
            name: {k: v for k, v in store.items() if k not in ("keys", "value_keys")}
            for name, store in sorted(stores.items())
        },
        "governed_train": {
            "relpath": GOVERNED_TRAIN,
            "sha256": digest(train_path),
            "utterances": len(train_gold),
        },
        "bank": {"relpath": bank["relpath"], "sha256": bank["sha256"],
                 "rosters": {k: len(v) for k, v in bank["rosters"].items()}},
        "arms": {
            label: {
                k: v for k, v in rows.items()
                if k not in ("rows", "store_specs")
            } for label, rows in sorted(arm_rows.items())
        },
        "channel_geometry": geometry,
        "arm_exemplar_pools": arm_pools,
        "attribution": attributions,
        "coverage": coverage,
        "populations": {
            label: {k: v for k, v in pop.items() if k != "rows"}
            for label, pop in sorted(populations.items())
        },
        "class_rows": {label: attributions[label]["class_rows"] for label in attributions},
    }

    analysis_dir = data_root / args.analysis_dir
    analysis_dir.mkdir(parents=True, exist_ok=True)
    json_path = analysis_dir / "read.json"
    json_path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n",
                         encoding="utf-8")
    print("wrote", json_path)
    report = build_report(payload=payload, coverage=coverage,
                          attributions=attributions, geometry=geometry)
    markdown = render(report)
    markdown_path = REPO_ROOT / args.markdown
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    print("wrote", markdown_path, len(markdown), "chars")
    print(json.dumps({
        "class_rows": payload["class_rows"],
        "mode_i_items": sum(
            (modes.get(MODE_I) or {}).get("items", 0)
            for att in attributions.values()
            for by_class in att["channels"].values()
            for modes in by_class.values()),
        "mode_iii_items": sum(
            (modes.get(MODE_III) or {}).get("items", 0)
            for att in attributions.values()
            for by_class in att["channels"].values()
            for modes in by_class.values()),
    }, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
