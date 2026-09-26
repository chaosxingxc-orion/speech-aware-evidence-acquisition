#!/usr/bin/env python3
"""Does the PRODUCTION path reproduce the 2026-09-26 diagnostic's own delivery
numbers for the exemplar-intent agreement term?

WHY THIS EXISTS. ``docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md``
measured the agreement term OFFLINE, in a simulation: it read each row's
exemplar votes out of the SEALED consumption trace and blended them into a
re-implemented ordering rule. The registration flies something different -- a
pre-computed agreement table produced by
``scripts/build_slurp_intent_exemplar_agreement.py``, merged into the recall by
``rails.knowledge_provider.KbFacetProvider`` and read by the registered ranker's
own ``w_agree``. If those two disagree, one of them is wrong and flying the
change would be premature. This read compares them, cell by cell, on all three
rosters, BEFORE any flight.

WHAT IS PRODUCTION HERE. Not a re-implementation: the exemplar vote is formed by
``rails.phase_supply.build_supply_for_phase`` plus ``build_bootstrap_selection``
-- the same recall, the same registered ranker and the same registered fuser the
flight runs at the Solver -- over each roster's own committed exemplar channel
spec, read out of that roster's own committed baseline fragment. The boundary
channel is built by ``rails.phase_supply._provider_factory``, the production
constructor, and decided by ``provider.candidates`` plus ``provider.fuse`` under
the flown knobs. The packet bindings and the split identity come from a real
``core.flight.FlightRuntime`` for each roster's own registered cell.

ONE DELIBERATE DEPARTURE, stated so it cannot be mistaken for the flown shape:
the agreement table is INJECTED into ``_provider_factory`` rather than pinned by
an ``agreement_source`` in the spec, because two of the three rosters have no
such artifact and this read must not mint one for them. The injected table is
produced by exactly the builder's own arithmetic (its ``utterance_identity`` is
imported from it, not copied), so the values are the values the pinned file
carries; only the transport differs.

TWO DEFINITIONS OF DELIVERY, both reported. The diagnostic's is RANK-based: the
gold intent's rank in the ranked order is <= 8. The flight's is FUSION-based:
the gold intent's boundary value id is among the fused ``selected_value_ids``.
On this store they should coincide -- the fuser walks the top-8 ranked facets
taking one value each, and facet id and value id are 1:1 -- and any row where
they do not is counted and reported rather than reconciled.

ZERO model, server, encoder, embedder, scorer, network, GPU and paid-API
contacts: arithmetic over receipt-pinned vector files and frozen snapshots, each
verified against its configured sha256 by this repository's own loaders before a
number is taken from it. No server is started, stopped or probed.

TEXT DISCIPLINE. No utterance text, transcript, gold label, intent name,
knowledge body or delivered answer is printed or persisted. Gold intents are
read offline on the scoring side and only ever COUNTED; a boundary facet id
carries an intent name, so no facet id is emitted -- only counts, rates and
hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.flight.campaign import (  # noqa: E402
    load_campaign_cells,
)
from speech_aware_evidence_acquisition.core.flight.factory import (  # noqa: E402
    build_flight_runtime,
)
from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import (  # noqa: E402
    default_phase_program,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
    QueryState,
)
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    _provider_factory,
    build_bootstrap_selection,
    build_supply_for_phase,
    load_phase_supply_specs,
    load_sealed_segment_vectors,
    load_sealed_vectors,
)

READ_ID = "SAEA-SLURP-INTENT-AGREEMENT-PRODUCTION-REPLICATION-V1"
RECIPE = "slurp-intent-agreement-production-replication-v1"
BOUNDARY_STORE = "intent-boundaries"
VOTE_STORE = "train-exemplars"
BOUNDARY_PHASE = "perception"
VOTE_PHASE = "solver"
BOUNDARY_DIM = "intent-boundary"
FLOWN_K = 8
BANK = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"

#: The diagnostic's own published cells (section 3 row ``agree-1`` and section
#: 2's ``1-8 (delivered)`` column), as percentages, for the side-by-side.
DIAGNOSTIC = {
    "train-fold-a-plan": {
        "wrong_rows": 191, "correct_rows": 480,
        "wrong_base_pct": 45.0, "wrong_treat_pct": 81.7,
        "wrong_base_n": 86, "wrong_treat_n": 156,
        "correct_base_pct": 97.3, "correct_treat_pct": 99.6,
    },
    "roll1": {
        "wrong_rows": 184, "correct_rows": 163,
        "wrong_base_pct": 44.6, "wrong_treat_pct": 75.0,
        "wrong_base_n": 82, "wrong_treat_n": None,
        "correct_base_pct": 95.1, "correct_treat_pct": 98.8,
    },
    "dev2000-added-plan": {
        "wrong_rows": 232, "correct_rows": 398,
        "wrong_base_pct": 35.8, "wrong_treat_pct": 78.0,
        "wrong_base_n": 83, "wrong_treat_n": None,
        "correct_base_pct": 94.5, "correct_treat_pct": 99.5,
    },
}

#: Per roster: the registered cell whose committed fragments this read uses,
#: and the class source. Nothing is hard-coded about the vector files -- every
#: pin is read out of that cell's own committed baseline fragment.
ARMS = (
    {
        "label": "train-fold-a-plan",
        "experiment": "slurp-native-default-plan-lock-v1",
        "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
        "bank_roster": "train-fold-a",
        "scores": None,
        "scorer_id": None,
        "expected_bank_classes": {"INTENT-UNCOVERED": 130, "INTENT-COVERED": 61},
    },
    {
        "label": "roll1",
        "experiment": "slurp-native-stage3-rollout-r01-v1",
        "run_id": "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1",
        "bank_roster": None,
        "scores": (
            "analysis/SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1/"
            "PS-registered-support-3-slurp-slu-official-projected-v3-train-scores.json"
        ),
        "scorer_id": "slurp-slu-official-projected-v3-train",
        "expected_bank_classes": None,
    },
    {
        "label": "dev2000-added-plan",
        "experiment": "slurp-native-default-plan-dev2000-added-v1",
        "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1",
        "bank_roster": "dev2000-added",
        "scores": None,
        "scorer_id": None,
        "expected_bank_classes": {"INTENT-UNCOVERED": 169, "INTENT-COVERED": 63},
    },
)

#: The bank's two intent-error classes collapse to the diagnostic's one class,
#: exactly as its ``load_bank`` does. The split is kept beside it, because the
#: expected-effect arithmetic needs it: only the UNCOVERED rows are the ones a
#: coverage repair can act on.
_BANK_COLLAPSE = {"INTENT-UNCOVERED": "INTENT-WRONG", "INTENT-COVERED": "INTENT-WRONG"}


class ReadError(RuntimeError):
    """Refuse a roster, a pin or a population this read cannot verify."""


def _import_builder():
    """The AGREEMENT BUILDER's own module, imported from its path.

    ``scripts/`` is not a package, so this is the only way to reuse the
    builder's ``utterance_identity`` rather than copy it -- and reuse is the
    point: a second definition of the self-exclusion key would be a second
    thing to keep true.
    """

    path = REPO_ROOT / "scripts" / "build_slurp_intent_exemplar_agreement.py"
    spec = importlib.util.spec_from_file_location(
        "_saea_agreement_builder", path
    )
    if spec is None or spec.loader is None:
        raise ReadError("cannot import the agreement builder module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, hashlib.sha256(path.read_bytes()).hexdigest()


BUILDER, BUILDER_SHA = _import_builder()


def digest_file(path: Path) -> str:
    measured = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            measured.update(chunk)
    return measured.hexdigest()


def pct(num: float, den: float) -> float:
    return 100.0 * num / den if den else 0.0


def bare(value_id: str) -> str:
    return value_id.split("::", 1)[1] if "::" in value_id else value_id


def classify(intent_wrong: bool, fp: float, fn: float) -> str:
    """The diagnostic's own seven-class convention, verbatim in behaviour."""

    if intent_wrong:
        return "INTENT-WRONG"
    if fp and fn:
        return "ENTITY-MIXED"
    if fn:
        return "ENTITY-FN-ONLY"
    if fp:
        return "ENTITY-FP-ONLY"
    return "CORRECT"


def load_snapshot(data_root: Path, pin: dict, label: str) -> KnowledgeSnapshot:
    path = data_root / str(pin["relpath"])
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(path.read_text(encoding="utf-8"))
    )
    if snapshot.content_hash() != str(pin["sha256"]):
        raise ReadError(f"{label} snapshot does not hash to its configured pin")
    return snapshot


def load_bank(data_root: Path) -> dict:
    path = data_root / BANK
    rosters: dict[str, dict] = defaultdict(dict)
    raw_classes: dict[str, Counter] = defaultdict(Counter)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        raw_classes[entry["roster"]][entry["plan_class"]] += 1
        rosters[entry["roster"]][entry["sample_id"]] = {
            "class": _BANK_COLLAPSE.get(entry["plan_class"], entry["plan_class"]),
            "plan_class": entry["plan_class"],
            "gold_intent": entry["gold_intent"],
        }
    return {
        "sha256": digest_file(path),
        "rosters": {k: dict(sorted(v.items())) for k, v in sorted(rosters.items())},
        "raw_classes": {
            k: dict(sorted(v.items())) for k, v in sorted(raw_classes.items())
        },
    }


def load_train_gold(lock: dict, data_root: Path) -> dict:
    """TRAIN utterance -> intent, read OFFLINE on the scoring side only. It
    reaches no query, no key, no weight and no selector, and no value of it is
    printed."""

    by_utterance: dict[str, str] = {}
    for record in load_slurp_split(lock, data_root, "train"):
        key = str(record.utterance_id)
        by_utterance[str(int(key)) if key.isdigit() else key] = (
            f"{record.scenario}_{record.action}"
        )
    return by_utterance


def load_population(data_root: Path, arm: dict, bank: dict, train_gold: dict) -> dict:
    if arm["bank_roster"] is not None:
        roster = arm["bank_roster"]
        if roster not in bank["rosters"]:
            raise ReadError("the bad-case bank carries no such roster")
        observed = bank["raw_classes"][roster]
        expected = arm["expected_bank_classes"] or {}
        for name, count in sorted(expected.items()):
            if observed.get(name) != count:
                raise ReadError(
                    f"bank roster {roster!r} carries {observed.get(name)} {name} rows, "
                    f"not the expected {count}"
                )
        return {
            "rows": dict(bank["rosters"][roster]),
            "source": "bad-case bank roster " + roster,
            "source_sha256": bank["sha256"],
            "raw_classes": dict(observed),
        }
    path = data_root / str(arm["scores"])
    block = json.loads(path.read_text(encoding="utf-8"))[arm["scorer_id"]]
    rows = {}
    for sample in block["per_sample"]:
        sample_id = str(sample["sample_id"])
        utterance = sample_id.split(":")[2] if sample_id.count(":") >= 2 else ""
        rows[sample_id] = {
            "class": classify(
                not bool(sample["scenario_action_exact"]),
                float(sample["slot_f1_exact_fp"]),
                float(sample["slot_f1_exact_fn"]),
            ),
            "plan_class": None,
            "gold_intent": (
                train_gold.get(str(int(utterance))) if utterance.isdigit() else None
            ),
        }
    return {
        "rows": dict(sorted(rows.items())),
        "source": arm["scorer_id"],
        "source_sha256": digest_file(path),
        "raw_classes": dict(sorted(Counter(r["class"] for r in rows.values()).items())),
    }


def load_sealed(data_root: Path, run_id: str, attempt: str) -> dict:
    """The sealed BOUNDARY delivery and the sealed EXEMPLAR delivery, per row,
    out of the flight's own phase artefact -- the bytes the recomputation is
    validated against before any of it is believed."""

    path = (
        data_root / "runs" / run_id / attempt / (run_id + ".phases.json")
    )
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != "saea-flight-phase-summaries-v1":
        raise ReadError(f"{run_id}: unexpected phase artefact schema")
    rows: dict[str, dict] = {}
    for summary in document["phases"]:
        for result in summary["results"]:
            sample_id = result["sample_id"]
            row = rows.setdefault(sample_id, {"boundary": set(), "exemplars": set()})
            for record in (result.get("consumption") or {}).get("records") or ():
                item = bare(str(record.get("supplied_item_id") or ""))
                if item.startswith("intent-boundary:"):
                    row["boundary"].add(item)
                elif item.startswith("value:"):
                    row["exemplars"].add(item)
    del document
    return {"rows": rows, "sha256": digest_file(path), "relpath": str(path.relative_to(data_root))}


def arm_channels(repo: Path, data_root: Path, lock_path: Path, arm: dict) -> dict:
    """One roster's two channels, built exactly the way a flight builds them."""

    cells = [
        cell
        for cell in load_campaign_cells(repo, arm["experiment"])
        if cell.run_id == arm["run_id"]
    ]
    if len(cells) != 1:
        raise ReadError(f"{arm['label']}: the experiment declares no such single cell")
    cell = cells[0]
    runtime = build_flight_runtime(
        repo,
        data_root,
        model=cell.document["model_fragment"],
        dataset=cell.document["dataset_fragment"],
        baseline=cell.document["baseline_fragment"],
        experiment=arm["experiment"],
        run_id=cell.run_id,
        attempt_id=cell.attempt_id,
        runtime_root=Path("/home/chao"),
        lock_path=lock_path,
    )
    _program, binding, _specs, first, identity, _inputs = (
        runtime.phase_supply_artifact_identity()
    )
    if first != BOUNDARY_PHASE:
        raise ReadError(f"{arm['label']}: first phase is not {BOUNDARY_PHASE!r}")
    values = runtime._composed.values  # noqa: SLF001 -- the composed config, read-only
    stores = values.get("knowledge_stores") or {}
    program = default_phase_program(str(values["policy"]))
    out = {
        "cell_id": cell.document["cell_id"],
        "attempt_id": cell.attempt_id,
        "baseline_fragment": cell.document["baseline_fragment"],
        "dataset_fragment": cell.document["dataset_fragment"],
        "split_identity_hash": identity,
        "packets": dict(binding["speech_packet_bindings"]),
        "specs": {},
        "snapshots": {},
    }
    for store_id, phase in ((BOUNDARY_STORE, BOUNDARY_PHASE), (VOTE_STORE, VOTE_PHASE)):
        if store_id not in stores:
            raise ReadError(f"{arm['label']}: the cell declares no store {store_id!r}")
        specs = load_phase_supply_specs(
            {"phase_supply": stores[store_id].get("phase_supply") or {}}, program
        )
        spec = specs.get(phase)
        if spec is None:
            raise ReadError(f"{arm['label']}: {store_id!r} supplies no {phase!r}")
        if spec.agreement_source is not None:
            raise ReadError(
                f"{arm['label']}: {store_id!r} already declares an agreement_source; "
                "this read compares against the FLOWN default and refuses a cell that "
                "has already been changed"
            )
        out["specs"][store_id] = spec
        out["snapshots"][store_id] = load_snapshot(
            data_root, stores[store_id]["snapshot"], f"{arm['label']} {store_id}"
        )
    return out


def exemplar_selections(
    data_root: Path, arm: dict, channels: dict, workers: int
) -> tuple[dict, dict]:
    """The row's own top-``k`` exemplar recall, through the production seam."""

    spec = channels["specs"][VOTE_STORE]
    snapshot = channels["snapshots"][VOTE_STORE]
    callback = build_supply_for_phase(
        {VOTE_PHASE: spec},
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=data_root,
        seed_phases=(VOTE_PHASE,),
    )
    if callback is None:
        raise ReadError(f"{arm['label']}: the vote channel built no supply callable")
    provider = callback.provider_factories[VOTE_PHASE]()
    query_table = callback.query_tables.get(VOTE_PHASE) or {}
    packets = channels["packets"]
    missing = sorted(set(packets) - set(query_table))
    if missing:
        raise ReadError(
            f"{arm['label']}: {len(missing)} of {len(packets)} rows have no exemplar "
            "query vector; a missing vector is refused rather than scored 0.0"
        )
    _facets, selections = build_bootstrap_selection(
        spec,
        provider=provider,
        query_vectors_by_sample=query_table,
        speech_packet_bindings=packets,
        split_identity_hash=channels["split_identity_hash"],
        source_audio_bindings=getattr(callback, "source_audio_bindings", None),
        workers=workers,
    )
    pins = {
        "query_source": dict(spec.query_source),
        "facet_source": dict(spec.facet_source or {}),
        "snapshot_sha256": snapshot.content_hash(),
        "k": spec.k,
        "fuse_policy": spec.fuse_policy,
        "fuse_coverage": dict(spec.fuse_coverage or {}),
        "rank_weights": dict(spec.rank_weights or {}),
    }
    return selections, pins


def agreement_table(
    arm: dict, channels: dict, selections: dict
) -> tuple[dict, dict]:
    """``{sample_id: {boundary facet id: share}}`` -- the builder's arithmetic,
    with the builder's own self-exclusion key."""

    vote_snapshot = channels["snapshots"][VOTE_STORE]
    boundary_facets = {
        facet.facet_id for facet in channels["snapshots"][BOUNDARY_STORE].facets
    }
    target_of_value = {v.value_id: v.task_target for v in vote_snapshot.values}
    utterances_of_value = {
        v.value_id: {
            BUILDER.utterance_identity(sample_id) for sample_id in v.source_sample_ids
        }
        for v in vote_snapshot.values
    }
    table: dict[str, dict[str, float]] = {}
    totals: Counter[int] = Counter()
    self_rows = self_total = untargeted = zero_rows = 0
    for sample_id in sorted(channels["packets"]):
        # THE BUILDER'S OWN PURE FUNCTION, not a copy of it. This is the whole
        # point of the comparison: the shares this read ranks with are formed by
        # exactly the code that writes the pinned artifact, so a difference
        # between this read and the flight cannot come from two spellings of the
        # same arithmetic.
        shares, total, dropped, no_target = BUILDER.form_vote(
            selections.get(sample_id, ()),
            own_utterance=BUILDER.utterance_identity(sample_id),
            target_of_value=target_of_value,
            utterances_of_value=utterances_of_value,
            target_facet_template=f"{BOUNDARY_DIM}:{{key}}",
            target_facets=boundary_facets,
        )
        totals[total] += 1
        self_total += dropped
        self_rows += int(dropped > 0)
        untargeted += no_target
        zero_rows += int(total == 0)
        table[sample_id] = shares
    measured = {
        "vote_total_histogram": {str(k): v for k, v in sorted(totals.items())},
        "rows_with_a_self_excluded_exemplar": self_rows,
        "self_excluded_exemplars": self_total,
        "rows_with_no_vote": zero_rows,
        "pool_values_without_a_build_time_target": untargeted,
        "distinct_facets_ever_voted_for": len({f for r in table.values() for f in r}),
    }
    return table, measured


def boundary_decisions(
    data_root: Path,
    arm: dict,
    channels: dict,
    table: dict | None,
    w_agree: float,
    recall_width: int,
) -> dict:
    """One boundary decision per row, through the production constructor.

    ``recall_width`` is ``PhaseSupplySpec.k``, which
    ``rails.phase_supply._provider_factory`` passes as
    ``top_k_per_dimension`` -- the number of candidates the RECALL admits.
    THE DELIVERED width is ``fuse_coverage`` (``m`` / ``c`` / ``top_l``) and is
    left exactly as the cell committed it, so widening the recall costs no
    rendered entry.

    WHY THIS IS A PARAMETER AND NOT THE FLOWN CONSTANT. The flown cell sets
    ``k`` 8 and ``fuse_coverage`` m=8/c=1/top_l=8, so the recall truncates to
    eight candidates BY COSINE before the ranker ever runs: a reweighting can
    then only permute the delivered eight and can never reach a candidate at
    rank 9-60. The 2026-09-26 diagnostic's simulation recalled at full width 60
    and delivered eight. Both widths are therefore measured here, and the
    receipt reports both, because the difference between them IS the finding.
    """

    spec = channels["specs"][BOUNDARY_STORE]
    snapshot = channels["snapshots"][BOUNDARY_STORE]
    flown = dict(spec.rank_weights or {})
    used = replace(
        spec, rank_weights={**flown, "w_agree": w_agree}, k=int(recall_width)
    )
    facets = load_sealed_vectors(
        data_root / str(spec.facet_source["relpath"]),
        expected_sha256=str(spec.facet_source["sha256"]),
        dimensions=spec.dimensions,
    )
    recalled_widths: Counter[int] = Counter()
    queries = load_sealed_segment_vectors(
        data_root / str(spec.query_source["relpath"]),
        expected_sha256=str(spec.query_source["sha256"]),
        dimensions=spec.dimensions,
    )
    factory = _provider_factory(
        used,
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        facet_vectors=facets,
        provider_for_phase=None,
        agreement_scores=table,
    )
    out: dict[str, dict] = {}
    for sample_id, descriptor in sorted(channels["packets"].items()):
        record = queries.get(sample_id)
        if record is None:
            raise ReadError(f"{arm['label']}: a roster row has no boundary query vector")
        state = QueryState(
            query_id=f"agreement-replication:{BOUNDARY_PHASE}:{sample_id}",
            query_sample_id=sample_id,
            speech_packet_id=str(descriptor["packet_id"]),
            speech_packet_sha256=str(descriptor["sha256"]),
            use_split_identity_hash=channels["split_identity_hash"],
        ).validate()
        provider = factory()
        ranking = provider.candidates(
            {"query_state": state, "query_segments": record.segments}, k=spec.k
        )
        decision = provider.fuse([ranking], k=used.k, policy_id=spec.fuse_policy)
        recalled_widths[len(provider._last_recall_scores or {})] += 1  # noqa: SLF001
        out[sample_id] = {
            "ranked": tuple(entry.entry_id for entry in ranking.entries),
            "fused": frozenset(decision.selected_value_ids),
        }
    pins = {
        "query_source": dict(spec.query_source),
        "facet_source": dict(spec.facet_source or {}),
        "snapshot_sha256": snapshot.content_hash(),
        "k_committed": spec.k,
        "k_used_as_recall_width": used.k,
        "tau": spec.tau,
        "fuse_policy": spec.fuse_policy,
        "fuse_coverage": dict(spec.fuse_coverage or {}),
        "rank_weights_flown": flown,
        "rank_weights_used": dict(used.rank_weights or {}),
        "candidates_recalled_histogram": {
            str(k): v for k, v in sorted(recalled_widths.items())
        },
        "delivered_width_histogram": {
            str(k): v
            for k, v in sorted(Counter(len(r["fused"]) for r in out.values()).items())
        },
        "segments_per_row": {
            str(k): v
            for k, v in sorted(
                Counter(len(queries[s].segments) for s in channels["packets"]).items()
            )
        },
    }
    return {"rows": out, "pins": pins}


def tally(population: dict, sealed: dict, base: dict, treat: dict) -> dict:
    """Delivery counts per class, both definitions, plus the per-plan_class gain
    split the expected-effect arithmetic needs."""

    counts: dict[str, Counter] = defaultdict(Counter)
    plan_split: dict[str, Counter] = defaultdict(Counter)
    skipped: Counter = Counter()
    disagreements = 0
    sealed_agree = Counter()
    for sample_id, verdict in sorted(population["rows"].items()):
        gold = verdict.get("gold_intent")
        if gold is None:
            skipped["no-gold-intent"] += 1
            continue
        if sample_id not in base["rows"] or sample_id not in treat["rows"]:
            skipped["no-boundary-decision"] += 1
            continue
        sealed_row = sealed["rows"].get(sample_id)
        if sealed_row is None:
            skipped["no-sealed-row"] += 1
            continue
        gold_id = f"{BOUNDARY_DIM}:{gold}"
        klass = verdict["class"]
        counts[klass]["rows"] += 1
        # The sealed check: the baseline fusion must equal what the flight sealed.
        sealed_agree["rows"] += 1
        sealed_agree["baseline_fusion_equals_sealed"] += int(
            base["rows"][sample_id]["fused"] == frozenset(sealed_row["boundary"])
        )
        for name, decision in (("base", base), ("treat", treat)):
            row = decision["rows"][sample_id]
            fused = gold_id in row["fused"]
            ranked = gold_id in row["ranked"][:FLOWN_K]
            counts[klass][f"{name}_fused"] += int(fused)
            counts[klass][f"{name}_ranked"] += int(ranked)
            disagreements += int(fused != ranked)
        if verdict.get("plan_class"):
            before = gold_id in base["rows"][sample_id]["fused"]
            after = gold_id in treat["rows"][sample_id]["fused"]
            bucket = plan_split[verdict["plan_class"]]
            bucket["rows"] += 1
            bucket["delivered_before"] += int(before)
            bucket["delivered_after"] += int(after)
            bucket["newly_delivered"] += int(after and not before)
            bucket["newly_lost"] += int(before and not after)
    return {
        "classes": {
            klass: {
                **dict(sorted(counter.items())),
                "base_fused_pct": round(pct(counter["base_fused"], counter["rows"]), 4),
                "treat_fused_pct": round(pct(counter["treat_fused"], counter["rows"]), 4),
                "base_ranked_pct": round(pct(counter["base_ranked"], counter["rows"]), 4),
                "treat_ranked_pct": round(pct(counter["treat_ranked"], counter["rows"]), 4),
            }
            for klass, counter in sorted(counts.items())
        },
        "plan_class_split": {
            name: dict(sorted(counter.items()))
            for name, counter in sorted(plan_split.items())
        },
        "skipped": dict(sorted(skipped.items())),
        "fusion_vs_rank_disagreements": disagreements,
        "sealed_boundary_agreement": dict(sorted(sealed_agree.items())),
    }


def sealed_exemplar_agreement(sealed: dict, selections: dict, packets: dict) -> dict:
    counter = Counter()
    for sample_id in sorted(packets):
        row = sealed["rows"].get(sample_id)
        if row is None:
            counter["no_sealed_row"] += 1
            continue
        counter["rows"] += 1
        recomputed = frozenset(selections.get(sample_id, ()))
        counter["sealed_nonempty"] += int(bool(row["exemplars"]))
        counter["exact"] += int(recomputed == frozenset(row["exemplars"]))
        counter["recomputed_width_20"] += int(len(recomputed) == 20)
    return dict(sorted(counter.items()))


def run(args: argparse.Namespace) -> dict:
    repo = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve()
    lock_path = Path(args.lock_path).resolve()
    lock = load_lock(lock_path)
    bank = load_bank(data_root)
    train_gold = load_train_gold(lock, data_root)
    report: dict = {
        "schema": "saea-agreement-production-replication-v1",
        "read_id": READ_ID,
        "recipe": RECIPE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contact_class": "model-free",
        "contacts": {
            "model": 0, "server": 0, "encoder": 0, "embedder": 0,
            "scorer": 0, "network": 0, "gpu": 0, "paid_api": 0,
        },
        "workers": args.workers,
        "recall_width": args.recall_width,
        "the_finding": (
            "The delivered width and the RECALL width are the same knob in the flown "
            "cell: PhaseSupplySpec.k is passed to the provider as "
            "top_k_per_dimension AND the fuser's coverage is m=top_l=8, so at k=8 the "
            "recall truncates to eight candidates by cosine BEFORE the ranker runs and "
            "an agreement reweighting can only permute the eight it already delivers. "
            "The 2026-09-26 diagnostic simulated a full-width recall (60) followed by a "
            "delivery of eight. This read measures both widths: at the committed width "
            "the treatment is inert, and at width 60 with fuse_coverage unchanged it "
            "reproduces the diagnostic. The registered cell therefore has to widen k "
            "while leaving fuse_coverage at m=8/c=1/top_l=8 -- which costs no rendered "
            "entry, as the delivered-width histogram beside each block shows."
        ),
        "agreement_builder_sha256": BUILDER_SHA,
        "bad_case_bank_sha256": bank["sha256"],
        "lock_path": str(lock_path),
        "arms": {},
    }
    report["wiring_probe_max_rows"] = args.max_rows
    for arm in ARMS:
        channels = arm_channels(repo, data_root, lock_path, arm)
        if args.max_rows:
            # WIRING PROBE ONLY. Truncating the roster makes every rate below
            # incomparable with the diagnostic, so the receipt records the
            # truncation at its top level and a truncated run must never be
            # cited as the replication.
            keep = sorted(channels["packets"])[: args.max_rows]
            channels["packets"] = {k: channels["packets"][k] for k in keep}
        population = load_population(data_root, arm, bank, train_gold)
        sealed = load_sealed(data_root, arm["run_id"], channels["attempt_id"])
        selections, vote_pins = exemplar_selections(
            data_root, arm, channels, args.workers
        )
        ex_agree = sealed_exemplar_agreement(sealed, selections, channels["packets"])
        table, vote_measured = agreement_table(arm, channels, selections)
        flown_k = channels["specs"][BOUNDARY_STORE].k
        by_width = {}
        for width in sorted({flown_k, args.recall_width}):
            base = boundary_decisions(data_root, arm, channels, None, 0.0, width)
            treat = boundary_decisions(data_root, arm, channels, table, 1.0, width)
            by_width[width] = {
                "boundary_channel": base["pins"],
                "treatment_boundary_channel": treat["pins"],
                "delivery": tally(population, sealed, base, treat),
            }
        counted = by_width[args.recall_width]["delivery"]
        flown = by_width[flown_k]["delivery"]
        expected = DIAGNOSTIC[arm["label"]]
        wrong = counted["classes"].get("INTENT-WRONG", {})
        right = counted["classes"].get("CORRECT", {})
        wrong_flown = flown["classes"].get("INTENT-WRONG", {})
        report["arms"][arm["label"]] = {
            "cell_id": channels["cell_id"],
            "run_id": arm["run_id"],
            "attempt_id": channels["attempt_id"],
            "baseline_fragment": channels["baseline_fragment"],
            "dataset_fragment": channels["dataset_fragment"],
            "split_identity_hash": channels["split_identity_hash"],
            "roster_rows": len(channels["packets"]),
            "population": {
                "source": population["source"],
                "sha256": population["source_sha256"],
                "raw_classes": population["raw_classes"],
            },
            "sealed_phase_artefact": {
                "relpath": sealed["relpath"], "sha256": sealed["sha256"],
            },
            "vote_channel": {**vote_pins, "measured": vote_measured},
            "sealed_exemplar_agreement": ex_agree,
            "committed_recall_width": flown_k,
            "read_recall_width": args.recall_width,
            "by_recall_width": {str(k): v for k, v in sorted(by_width.items())},
            "delivery": counted,
            "at_the_committed_recall_width": {
                "note": (
                    "At the width the cell commits, the RECALL truncates to that many "
                    "candidates by cosine before the ranker runs, so the agreement term "
                    "can only permute the already-delivered set. These two numbers "
                    "being equal is the finding, not a defect of the signal."
                ),
                "wrong_base_pct": wrong_flown.get("base_fused_pct"),
                "wrong_treat_pct": wrong_flown.get("treat_fused_pct"),
                "treatment_is_inert": (
                    wrong_flown.get("base_fused") == wrong_flown.get("treat_fused")
                ),
            },
            "diagnostic": expected,
            "side_by_side": {
                "wrong_rows": {"diagnostic": expected["wrong_rows"], "read": wrong.get("rows")},
                "correct_rows": {"diagnostic": expected["correct_rows"], "read": right.get("rows")},
                "wrong_base_pct": {
                    "diagnostic": expected["wrong_base_pct"],
                    "read": wrong.get("base_fused_pct"),
                },
                "wrong_treat_pct": {
                    "diagnostic": expected["wrong_treat_pct"],
                    "read": wrong.get("treat_fused_pct"),
                },
                "correct_base_pct": {
                    "diagnostic": expected["correct_base_pct"],
                    "read": right.get("base_fused_pct"),
                },
                "correct_treat_pct": {
                    "diagnostic": expected["correct_treat_pct"],
                    "read": right.get("treat_fused_pct"),
                },
            },
        }
        print(
            "%-20s rows=%4d | recall%d wrong %3d/%3d %.1f%%->%.1f%% (diag %.1f->%.1f) "
            "correct %.1f%%->%.1f%% (diag %.1f->%.1f) | recall%d(flown) %.1f%%->%.1f%% "
            "| ex-exact=%d/%d"
            % (
                arm["label"], len(channels["packets"]), args.recall_width,
                wrong.get("treat_fused", 0), wrong.get("rows", 0),
                wrong.get("base_fused_pct", 0.0), wrong.get("treat_fused_pct", 0.0),
                expected["wrong_base_pct"], expected["wrong_treat_pct"],
                right.get("base_fused_pct", 0.0), right.get("treat_fused_pct", 0.0),
                expected["correct_base_pct"], expected["correct_treat_pct"],
                flown_k, wrong_flown.get("base_fused_pct", 0.0),
                wrong_flown.get("treat_fused_pct", 0.0),
                ex_agree.get("exact", 0), ex_agree.get("rows", 0),
            ),
            flush=True,
        )
    report["boundary"] = (
        "ZERO model, server, encoder, embedder, scorer, network, GPU and paid-API "
        "contacts: no server was started, stopped or probed, no waveform decoded and "
        "no embedding computed. Every number is arithmetic over receipt-pinned vector "
        "files and frozen snapshots, each verified against its configured sha256 by "
        "this repository's own loaders before a value was taken from it, through this "
        "repository's own rails.phase_supply / rails.knowledge_provider / "
        "rails.kb_policy seams. A DIAGNOSTIC COMPARISON, never a gate: it registers no "
        "cell, admits no mechanism, releases no store, authorises no flight and states "
        "no effectiveness, superiority or generalisation claim. Every roster is a "
        "discovery or dev roster and every number is a development number (owner "
        "decisions 28 and 86). No utterance text, transcript, gold label, intent name, "
        "knowledge body or delivered answer is printed or persisted: every cell is an "
        "id, a count, a rate or a hash."
    )
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--recall-width",
        type=int,
        default=60,
        help=(
            "PhaseSupplySpec.k -- the number of candidates the RECALL admits before the "
            "ranker runs. The DELIVERED width stays at the cell's own fuse_coverage. "
            "60 (the default) is the whole 60-way boundary store, which is the width "
            "the 2026-09-26 diagnostic's simulation used. The cell's committed width is "
            "always measured too."
        ),
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help=(
            "WIRING PROBE ONLY: truncate every roster to its first N rows by sample "
            "id. It makes every rate incomparable with the diagnostic and is recorded "
            "in the receipt; 0 (the default) is the real read."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        print(json.dumps({"error": "PYTHONDONTWRITEBYTECODE=1 is required"}), file=sys.stderr)
        return 1
    if not 1 <= args.workers <= 4:
        print(json.dumps({"error": "workers must be 1..4"}), file=sys.stderr)
        return 1
    report = run(args)
    out = Path(args.data_root).resolve() / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("receipt", out, digest_file(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
