"""M11 operating-point sweep on already-exposed E108/C108 discovery trajectories.

ITERATION TIER, MODEL-FREE, ZERO SERVICE CONTACTS.

Authority: ``docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md``
section 7.2 -- before any conclusion, sweep a design's operating-point curves
on ALREADY-EXPOSED discovery data; model-free re-analysis is legal and cheap
(the P-EMB-4R mean-centering precedent). Exposure row
``SAEA-SN-MF-M11-OPERATING-POINT-SWEEP``.

What this module is NOT: it is not a reader, not a verdict, not a promotion
evaluator, and not a one-shot confirmatory read. Section 7.2 reserves one-shot
reads for confirmatory readings. Every number produced here is a DESIGN INPUT
for the DEV-100 campaign's starting knobs. No verdict clause attaches; no
admission, promotion, or superiority claim may be derived from this output.

Honesty constraints hard-wired into the design:

* Counterfactual firing conditions yield COUNTS ONLY. A query that would have
  fired the pair-boundary acquisition under a relaxed condition but never
  actually flew it has no recorded outcome; that outcome is reachable only by
  new model contacts and is never imputed here.
* The alpha-blend replay can only ever move a decision to a key that is already
  inside the logged retrieval list or is the logged primary. Its ceiling is the
  union-reachability count, which this module reports explicitly.
* The logged retrieval channel is a RANK, not a score. The frozen core emits an
  ordered key-id list; no cosine, logit, or embedding similarity was ever
  recorded on this surface. Every "rank weight" here is therefore a synthetic
  decay over rank position, not a recovered continuous retrieval score.

The module edits nothing. It imports the frozen reader's own parsing helpers so
that trajectory reconstruction, hash verification, and the deterministic
key-id-to-label mapping are the reader's, not a reimplementation.
"""

from __future__ import annotations

import os
import argparse
import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..core.driver.speech_native import (
    _load_binding_document,
    _load_decision_graph,
    _load_key_cards,
    _parse_m11_adaptive_evidence_gap_trajectory,
    _sha256_file,
)
from ..e0.artifacts import REPO_ROOT

SCHEMA = "saea-m11-operating-point-sweep-v1"
TIER = "iteration"
AUTHORITY = "docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md#7.2"
EXPOSURE_ROW = "SAEA-SN-MF-M11-OPERATING-POINT-SWEEP"
FRAME = (
    "iteration-tier, model-free, zero service contacts; outputs are DESIGN "
    "INPUTS for the DEV-100 campaign's starting knobs; NO verdict clause "
    "attaches; no promotion claim; FINAL60/DEV ladder/devel/test untouched"
)

# --- pinned, already-exposed inputs -----------------------------------------

E108_RUN_DIR = Path(
    "/home/chao/runs/SAEA-SN-EVIDENCE-E108-K1M11-INFORMATION-COMPLETE-ACTION"
    "-SUPPORT-ZCOPY/attempt-20260823T175901Z-e108zc"
)
E108_DECISIONS_SHA256 = (
    "4e9ebefceb07f11df858f6ccc71290beb243a2aef5198cf832fc16ce2d606f99"
)
E108_BINDING_RELPATH = (
    "configs/probes/g0-binding/"
    "speech-native-train-binding-evidence-e108-information-complete-knowledge.json"
)
E108_BINDING_SHA256 = (
    "a2ccd4b004ce2e31329bf7b69ce0ebb9cff642eec2d25cde8087ffc679203dfe"
)
E108_SPLIT_NAME = "EVIDENCE-E108"
E108_TOP_K = 3
E108_GRAPH_RELPATH = "configs/knowledge/slurp-signature-complete-decision-graph-v5.json"
E108_GRAPH_SHA256 = (
    "58c9457312d71a7c7a13e92e53e2a4f9fff5c45a9722eb5680d0fd465fe8a2fc"
)

C108_RUN_DIR = Path(
    "/home/chao/runs/SAEA-SN-EFFECT-C108-K1M6-GROUNDED-SCHEMA-V3"
    "/attempt-20260822T141000Z-12i001"
)
C108_DECISIONS_SHA256 = (
    "ce4d58221b35c3ab1ec15c6fff79b5d480b06f857364bb6c6be1879c8cb4cc78"
)
C108_BINDING_RELPATH = (
    "configs/probes/g0-binding/speech-native-train-binding-effect-c108.json"
)
C108_BINDING_SHA256 = (
    "41b74dd54292199ac6fdb55905edcbe965708ef7578a7b786625077269f48dc5"
)
C108_SPLIT_NAME = "EFFECT-C108"

KB_RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-kb-size-full.json"
KB_SNAPSHOT_RELPATH = "knowledge/slurp/saea-kb-distmodel-v1/size-full/snapshot.json"
KB_SNAPSHOT_SHA256 = (
    "e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57"
)
_SCENARIO_COUNT_RE = re.compile(r"\((\d+) TRAIN utterances in this snapshot\)")

# --- sweep grid --------------------------------------------------------------

ALPHAS: tuple[float, ...] = tuple(round(index / 10.0, 1) for index in range(11))
RANK_WEIGHTS: Mapping[str, Callable[[int, int], float]] = {
    # RRF-style reciprocal decay; the default listwise-fusion weight.
    "rrf": lambda rank, depth: 1.0 / (1.0 + float(rank)),
    # Linear decay to zero at the end of the logged list.
    "linear": lambda rank, depth: float(depth - rank) / float(depth),
    # Exponential decay; the sharpest of the three.
    "exp": lambda rank, depth: math.exp(-float(rank)),
}
EVIDENCE_VARIANTS: tuple[str, ...] = (
    "rank-only",
    "rank+prior",
    "rank+agreement",
    "rank+prior+agreement",
)
TAUS: tuple[float | None, ...] = (None, 0.5)
AGREEMENT_GAIN = 1.0
# Supplementary robustness scan: the coarse 0.1 alpha grid cannot tell a broad
# operating plateau from a one-grid-point knife edge, and a DEV-100 starting
# knob is worthless if it is the latter. Same model-free replay, finer alpha.
FINE_ALPHAS: tuple[float, ...] = tuple(
    round(0.50 + index / 100.0, 2) for index in range(41)
)


class SweepError(RuntimeError):
    """A pinned input failed verification, or a logged row broke its contract."""


# --- trajectory records ------------------------------------------------------


@dataclass(frozen=True)
class QueryRecord:
    """One logged trajectory reduced to the dimensions both splits share."""

    split: str
    sample_id: str
    speaker_id: str
    gold_key_id: str
    primary_key_id: str
    top_key_ids: tuple[str, ...]
    agreement_key_ids: frozenset[str]
    # M11-only fields; empty on the M6 split.
    retrieval_key_id: str | None = None
    action_key_id: str | None = None
    boundary_stable_key_id: str | None = None
    termination: str | None = None
    new_boundary_id: str | None = None
    boundary_ab_key_id: str | None = None
    boundary_ba_key_id: str | None = None
    # M6-only: the refined list actually scored by the registered reader.
    refined_top_key_ids: tuple[str, ...] = ()
    refined_key_id: str | None = None


def _read_rows(path: Path, expected_sha256: str) -> list[Mapping[str, object]]:
    if _sha256_file(path) != expected_sha256:
        raise SweepError(f"decisions SHA-256 mismatch for {path}")
    rows: list[Mapping[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if not isinstance(row, Mapping):
                raise SweepError("decision row must be an object")
            rows.append(row)
    return rows


def _gold_and_speakers(
    binding: Mapping[str, object], split_name: str
) -> tuple[dict[str, str], dict[str, str]]:
    splits = binding.get("splits")
    split = splits.get(split_name) if isinstance(splits, Mapping) else None
    items = split.get("items") if isinstance(split, Mapping) else None
    if not isinstance(items, list) or not items:
        raise SweepError(f"binding lacks split {split_name!r}")
    gold: dict[str, str] = {}
    speakers: dict[str, str] = {}
    for item in items:
        gold[str(item["sample_id"])] = str(item["value_label"])
        speakers[str(item["sample_id"])] = str(item["speaker_id"])
    return gold, speakers


def load_e108_records() -> tuple[list[QueryRecord], dict[str, str]]:
    """Reconstruct E108 through the frozen reader's own M11 parser."""

    binding_path = REPO_ROOT / E108_BINDING_RELPATH
    binding = _load_binding_document(binding_path, E108_BINDING_SHA256)
    cards = _load_key_cards(binding_path, E108_BINDING_SHA256)
    card_by_key = {card.key_id: card for card in cards}
    label_by_key = {card.key_id: card.value_label for card in cards}
    key_by_label = {card.value_label: card.key_id for card in cards}
    gold, speakers = _gold_and_speakers(binding, E108_SPLIT_NAME)
    graph = _load_decision_graph(
        REPO_ROOT / E108_GRAPH_RELPATH,
        expected_sha256=E108_GRAPH_SHA256,
        key_cards=cards,
    )
    rows = _read_rows(E108_RUN_DIR / "decisions.jsonl", E108_DECISIONS_SHA256)
    if len(rows) != len(gold):
        raise SweepError("E108 decision count does not match the split")
    records: list[QueryRecord] = []
    for row in rows:
        sample_id = str(row["sample_id"])
        trajectory = _parse_m11_adaptive_evidence_gap_trajectory(
            row=row,
            sample_id=sample_id,
            speaker_id=speakers[sample_id],
            gold_key_id=key_by_label[gold[sample_id]],
            top_k=E108_TOP_K,
            visible_card_by_key=card_by_key,
            decision_graph=graph,
        )
        action_key_id = trajectory["action_key_id"]
        stable_key_id = trajectory["boundary_stable_key_id"]
        agreement = {
            key_id
            for key_id in (action_key_id, stable_key_id)
            if isinstance(key_id, str)
        }
        records.append(
            QueryRecord(
                split=E108_SPLIT_NAME,
                sample_id=sample_id,
                speaker_id=str(trajectory["speaker_id"]),
                gold_key_id=str(trajectory["gold_key_id"]),
                primary_key_id=str(trajectory["primary_key_id"]),
                top_key_ids=tuple(trajectory["initial_top_key_ids"]),  # type: ignore[arg-type]
                agreement_key_ids=frozenset(agreement),
                retrieval_key_id=str(trajectory["retrieval_key_id"]),
                action_key_id=action_key_id if isinstance(action_key_id, str) else None,
                boundary_stable_key_id=(
                    stable_key_id if isinstance(stable_key_id, str) else None
                ),
                termination=str(trajectory["termination"]),
                new_boundary_id=(
                    str(trajectory["new_boundary_id"])
                    if trajectory["new_boundary_id"] is not None
                    else None
                ),
                boundary_ab_key_id=(
                    str(trajectory["boundary_ab_key_id"])
                    if trajectory["boundary_ab_key_id"] is not None
                    else None
                ),
                boundary_ba_key_id=(
                    str(trajectory["boundary_ba_key_id"])
                    if trajectory["boundary_ba_key_id"] is not None
                    else None
                ),
            )
        )
    return records, label_by_key


def load_c108_records() -> tuple[list[QueryRecord], dict[str, str]]:
    """Reduce the C108 M6-grounded rows to the shared dimensions.

    The field contract mirrored here is the reader's own inline M6 contract
    (``read_speech_native_predictions``, the ``matcher_policy_id == "M6"``
    branch): ``agent_vote_key_ids[0]`` is the speech-only primary,
    ``agent_vote_key_ids[1]`` the refined vote, ``agent_steps[1].top_key_ids``
    the speech-only retrieval list, ``row["top_key_ids"]`` the refined list, and
    ``row["verifier_scores"]`` the per-candidate compatibility judgements. The
    gold comparison is the reader's deterministic ``key_id -> value_label``
    mapping over the hash-pinned binding, not a separate scorer.
    """

    binding_path = REPO_ROOT / C108_BINDING_RELPATH
    binding = _load_binding_document(binding_path, C108_BINDING_SHA256)
    cards = _load_key_cards(binding_path, C108_BINDING_SHA256)
    label_by_key = {card.key_id: card.value_label for card in cards}
    key_by_label = {card.value_label: card.key_id for card in cards}
    gold, speakers = _gold_and_speakers(binding, C108_SPLIT_NAME)
    rows = _read_rows(C108_RUN_DIR / "decisions.jsonl", C108_DECISIONS_SHA256)
    if len(rows) != len(gold):
        raise SweepError("C108 decision count does not match the split")
    records: list[QueryRecord] = []
    for row in rows:
        sample_id = str(row["sample_id"])
        if (
            row.get("schema") != "saea-speech-native-decision-v1"
            or row.get("matcher_policy_id") != "M6"
            or row.get("mechanism_control_id") != "matched"
        ):
            raise SweepError("C108 row identity is malformed")
        votes = row.get("agent_vote_key_ids")
        steps = row.get("agent_steps")
        if not isinstance(votes, list) or not isinstance(steps, list) or len(steps) < 2:
            raise SweepError("C108 row lacks its vote/step structure")
        primary_key_id = votes[0]
        if not isinstance(primary_key_id, str) or primary_key_id not in label_by_key:
            raise SweepError("C108 speech-only primary is malformed")
        if steps[1].get("action_id") != "retrieve:speech-only":
            raise SweepError("C108 speech-only retrieval stage is malformed")
        initial_top = steps[1].get("top_key_ids")
        refined_top = row.get("top_key_ids")
        if (
            not isinstance(initial_top, list)
            or not initial_top
            or not isinstance(refined_top, list)
            or not all(
                isinstance(key_id, str) and key_id in label_by_key
                for key_id in list(initial_top) + list(refined_top)
            )
        ):
            raise SweepError("C108 retrieval lists are malformed")
        scores = row.get("verifier_scores")
        agreement: set[str] = set()
        if isinstance(scores, Mapping):
            for key_id, document in scores.items():
                if (
                    isinstance(document, Mapping)
                    and document.get("compatible") is True
                    and key_id in label_by_key
                ):
                    agreement.add(str(key_id))
        refined_vote = votes[1] if len(votes) > 1 else None
        records.append(
            QueryRecord(
                split=C108_SPLIT_NAME,
                sample_id=sample_id,
                speaker_id=speakers[sample_id],
                gold_key_id=key_by_label[gold[sample_id]],
                primary_key_id=primary_key_id,
                top_key_ids=tuple(str(key_id) for key_id in initial_top),
                agreement_key_ids=frozenset(agreement),
                refined_top_key_ids=tuple(str(key_id) for key_id in refined_top),
                refined_key_id=(
                    refined_vote if isinstance(refined_vote, str) else None
                ),
            )
        )
    return records, label_by_key


# --- ValueBundle-style label prior ------------------------------------------


def load_scenario_prior(data_root: Path) -> dict[str, object]:
    """Read the TRAIN scenario distribution from the landed KB-BUILD snapshot.

    Prior source, stated exactly: the model-free KB-BUILD v1 size-full snapshot
    (receipt ``docs/receipts/knowledge/slurp-kb-size-full.json``, snapshot
    sha256 ``e27b2745...``), specifically its eighteen
    ``facet:label:scenario:<label>`` facets, whose representation text carries
    the TRAIN utterance count behind each scenario. This is the only landed
    ValueBundle-style prior that is (a) built on TRAIN, (b) hash-pinned, and
    (c) keyed by the exact eighteen value labels this task routes over. The
    per-intent ``facet:prior:*`` facets in the same snapshot are entity-type
    priors CONDITIONED ON an intent that is not observable at decision time on
    this surface, so they are not usable as a label prior here and are not used.
    """

    receipt_path = REPO_ROOT / KB_RECEIPT_RELPATH
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("snapshot_sha256") != KB_SNAPSHOT_SHA256:
        raise SweepError("KB receipt snapshot sha256 does not match the pin")
    snapshot_path = data_root / KB_SNAPSHOT_RELPATH
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("snapshot_sha256") != KB_SNAPSHOT_SHA256:
        raise SweepError("KB snapshot self-declared sha256 does not match the pin")
    if snapshot.get("source_partition_role") != "train":
        raise SweepError("KB snapshot is not TRAIN-sourced")
    counts: dict[str, int] = {}
    for facet in snapshot.get("facets", []):
        facet_id = str(facet.get("facet_id", ""))
        if not facet_id.startswith("facet:label:scenario:"):
            continue
        match = _SCENARIO_COUNT_RE.search(str(facet.get("representation", "")))
        if match is None:
            raise SweepError(f"scenario facet {facet_id} has no TRAIN count")
        counts[facet_id.split(":")[-1]] = int(match.group(1))
    total = sum(counts.values())
    if len(counts) != 18 or total != int(receipt["coverage_report"]["counts"]["train_utterances"]):
        raise SweepError("scenario counts do not reconcile with the KB receipt")
    return {
        "source": KB_RECEIPT_RELPATH,
        "snapshot_relpath": KB_SNAPSHOT_RELPATH,
        "snapshot_sha256": KB_SNAPSHOT_SHA256,
        "snapshot_file_sha256": _sha256_file(snapshot_path),
        "train_utterances": total,
        "counts": dict(sorted(counts.items())),
        "probability": {
            label: count / total for label, count in sorted(counts.items())
        },
    }


# --- part 1: boundary firing-rate curve -------------------------------------


def firing_rate_curve(records: Sequence[QueryRecord]) -> dict[str, object]:
    """Recompute which alternative firing conditions would have triggered.

    Every condition below is evaluated over the LOGGED pre-boundary state
    (primary vote, speech-only retrieval list, candidate-action state). Counts
    are counts of queries that WOULD have entered the pair-boundary acquisition.
    For any query that did not actually fly the acquisition, the outcome is
    unrecorded and is never imputed: the model was never asked.
    """

    fired = [record for record in records if record.termination == "pair-boundary-compared"]
    no_boundary = [
        record for record in records if record.termination == "no-registered-pair-boundary"
    ]
    consistent = [
        record for record in records if record.termination == "complete-consistent-state"
    ]

    def disagreement(record: QueryRecord) -> bool:
        votes = {record.primary_key_id, record.retrieval_key_id, record.action_key_id}
        return len(votes - {None}) > 1

    conditions: list[dict[str, object]] = []

    def add(
        condition_id: str,
        predicate: Callable[[QueryRecord], bool],
        legality: str,
        description: str,
    ) -> None:
        matched = [record for record in records if predicate(record)]
        actually_flown = [
            record for record in matched if record.termination == "pair-boundary-compared"
        ]
        conditions.append(
            {
                "condition_id": condition_id,
                "legality": legality,
                "description": description,
                "would_fire_count": len(matched),
                "would_fire_rate": len(matched) / len(records),
                "of_which_actually_flown": len(actually_flown),
                "reachable_only_by_new_contacts": len(matched) - len(actually_flown),
                "outcome_imputation": "refused-outcomes-are-unrecorded",
            }
        )

    add(
        "C0-registered-as-flown",
        lambda record: record.termination == "pair-boundary-compared",
        "runtime-legal (this is the registered condition)",
        "valid candidate-action state AND the three votes are not unanimous AND "
        "a pair boundary for {primary, challenger} is registered in the frozen "
        "decision graph (the stable-edge-support floor).",
    )
    add(
        "C1-drop-stable-edge-support-floor",
        lambda record: disagreement(record) and record.action_key_id is not None,
        "runtime-legal but requires new graph edges",
        "candidate disagreement, with the registered-pair-boundary requirement "
        "dropped: fire on every disagreeing pair whether or not the frozen "
        "graph carries a stable-edge-supported boundary for it.",
    )
    add(
        "C2-primary-vs-retrieval-top1",
        lambda record: record.primary_key_id != record.retrieval_key_id,
        "runtime-legal, no candidate-action state needed",
        "fire whenever the speech-only primary disagrees with the speech-only "
        "retrieval rank-1 key; needs only the first two contacts.",
    )
    add(
        "C3-primary-vs-candidate-action",
        lambda record: record.action_key_id is not None
        and record.primary_key_id != record.action_key_id,
        "runtime-legal, needs the candidate-action contact",
        "fire whenever the primary disagrees with the evidence-conditioned "
        "candidate-action state.",
    )
    add(
        "C4-retrieval-top1-vs-candidate-action",
        lambda record: record.action_key_id is not None
        and record.retrieval_key_id != record.action_key_id,
        "runtime-legal, needs the candidate-action contact",
        "fire whenever the retrieval rank-1 key disagrees with the "
        "candidate-action state.",
    )
    add(
        "C5-any-pairwise-disagreement",
        disagreement,
        "runtime-legal but requires new graph edges",
        "union of C2/C3/C4: any disagreement among the three logged votes, "
        "boundary registration ignored.",
    )
    add(
        "C6-always-fire",
        lambda record: True,
        "runtime-legal, maximal cost",
        "unconditional acquisition on every query (the cost ceiling).",
    )
    add(
        "D1-gold-not-at-rank-1",
        lambda record: record.gold_key_id != record.retrieval_key_id,
        "ORACLE-DIAGNOSTIC, NOT runtime-legal (reads gold)",
        "fire whenever the gold key is not the retrieval rank-1 key; reported "
        "only as the diagnostic upper reference for a perfect gap detector.",
    )
    add(
        "D2-gold-not-primary",
        lambda record: record.gold_key_id != record.primary_key_id,
        "ORACLE-DIAGNOSTIC, NOT runtime-legal (reads gold)",
        "fire whenever the primary is already wrong; the diagnostic set a "
        "perfect gap detector would target.",
    )

    fired_detail = [
        {
            "sample_id": record.sample_id,
            "primary_key_id": record.primary_key_id,
            "retrieval_top1_key_id": record.retrieval_key_id,
            "candidate_action_key_id": record.action_key_id,
            "boundary_id": record.new_boundary_id,
            "boundary_ab_key_id": record.boundary_ab_key_id,
            "boundary_ba_key_id": record.boundary_ba_key_id,
            "boundary_stable_key_id": record.boundary_stable_key_id,
            "gold_key_id": record.gold_key_id,
            "primary_was_correct": record.primary_key_id == record.gold_key_id,
            "gold_in_logged_top_k": record.gold_key_id in record.top_key_ids,
        }
        for record in fired
    ]
    return {
        "query_count": len(records),
        "registered_firing_count": len(fired),
        "registered_firing_rate": len(fired) / len(records),
        "termination_histogram": dict(
            sorted(Counter(str(record.termination) for record in records).items())
        ),
        "stable_edge_support_gap": {
            "disagreeing_queries_without_a_registered_boundary": len(no_boundary),
            "unanimous_queries": len(consistent),
            "note": (
                "these are queries where the loop DID detect a candidate "
                "disagreement but the frozen decision graph carried no "
                "stable-edge-supported boundary for that pair, so no "
                "acquisition was possible"
            ),
        },
        "conditions": conditions,
        "fired_queries": fired_detail,
        "fired_precision_recap": {
            "source": "docs/checks/speech-aware-evidence-acquisition/"
            "2026-08-23-e108-zcopy-read/read-verdict.json",
            "boundary_supply_transition": {
                "eligible_count": 4,
                "changed_prediction_count": 4,
                "helpful_transition_count": 4,
                "harmful_transition_count": 0,
                "unresolved_count": 3,
            },
            "reading": (
                "of the 7 acquisitions actually flown, 4 were attributable "
                "transitions and all 4 were helpful, 0 harmful; the other 3 "
                "were unresolved. Precision on the attributable subset is 4/4"
            ),
        },
    }


# --- part 2: within-logged-k retrieval curves --------------------------------


def recall_curve(records: Sequence[QueryRecord], label_by_key: Mapping[str, str]) -> dict[str, object]:
    """Gold-in-top-r from the logged retrieval lists, plus the union ceiling."""

    depth = max(len(record.top_key_ids) for record in records)
    curve: list[dict[str, object]] = []
    for rank in range(1, depth + 1):
        hits = sum(
            1
            for record in records
            if record.gold_key_id in record.top_key_ids[:rank]
        )
        curve.append(
            {
                "top_r": rank,
                "gold_reachable_count": hits,
                "gold_reachable_rate": hits / len(records),
            }
        )
    union_reachable = [
        record
        for record in records
        if record.gold_key_id in set(record.top_key_ids) | {record.primary_key_id}
    ]
    unreachable = [record for record in records if record not in union_reachable]
    primary_correct = sum(
        1 for record in records if record.primary_key_id == record.gold_key_id
    )
    result: dict[str, object] = {
        "query_count": len(records),
        "logged_depth": depth,
        "logged_retrieval_channel": "ordered key-id list only; no score was recorded",
        "curve": curve,
        "primary_correct": primary_correct,
        "blend_layer_ceiling": {
            "union_reachable_count": len(union_reachable),
            "note": (
                "a decision layer that only re-ranks the logged candidates can "
                "never exceed this; it is the count of queries whose gold key "
                "is inside (logged top-k UNION {primary})"
            ),
        },
        "unreachable_queries": {
            "count": len(unreachable),
            "gold_label_histogram": dict(
                sorted(
                    Counter(
                        label_by_key[record.gold_key_id] for record in unreachable
                    ).items()
                )
            ),
            "sample_ids": [record.sample_id for record in unreachable],
        },
    }
    if any(record.refined_top_key_ids for record in records):
        refined_hits = sum(
            1
            for record in records
            if record.gold_key_id in record.refined_top_key_ids
        )
        result["refined_list_top_k_reachable_count"] = refined_hits
        result["refined_list_note"] = (
            "the registered reader scores top-k reachability on the REFINED "
            "list; this sweep blends over the speech-only INITIAL list so the "
            "two splits stay schema-parallel"
        )
    return result


# --- part 3: C3 alpha-blend offline replay -----------------------------------


def _fused_scores(
    record: QueryRecord,
    *,
    rank_weight: Callable[[int, int], float],
    use_prior: bool,
    use_agreement: bool,
    prior_multiplier: Mapping[str, float],
    label_by_key: Mapping[str, str],
) -> dict[str, float]:
    depth = len(record.top_key_ids)
    scores: dict[str, float] = {record.primary_key_id: 0.0}
    for rank, key_id in enumerate(record.top_key_ids):
        scores[key_id] = rank_weight(rank, depth)
    for key_id in list(scores):
        value = scores[key_id]
        if use_prior:
            value *= prior_multiplier[label_by_key[key_id]]
        if use_agreement and key_id in record.agreement_key_ids:
            value *= 1.0 + AGREEMENT_GAIN
        scores[key_id] = value
    total = sum(scores.values())
    if total <= 0.0:
        return {key_id: 0.0 for key_id in scores}
    return {key_id: value / total for key_id, value in scores.items()}


def _blend_decision(
    record: QueryRecord,
    normalized: Mapping[str, float],
    alpha: float,
    tau: float | None,
) -> str:
    if tau is not None and (not normalized or max(normalized.values()) < tau):
        return record.primary_key_id
    rank_of = {key_id: rank for rank, key_id in enumerate(record.top_key_ids)}
    best_key = record.primary_key_id
    best_sort: tuple[float, int, int, str] | None = None
    for key_id, fused in normalized.items():
        score = alpha * fused + (1.0 - alpha) * (
            1.0 if key_id == record.primary_key_id else 0.0
        )
        # Deterministic tie-break: higher score, then prefer the primary, then
        # the shallower logged rank, then the lexicographically smaller key id.
        sort_key = (
            -score,
            0 if key_id == record.primary_key_id else 1,
            rank_of.get(key_id, len(record.top_key_ids)),
            key_id,
        )
        if best_sort is None or sort_key < best_sort:
            best_sort = sort_key
            best_key = key_id
    return best_key


def _prior_multiplier(prior: Mapping[str, object]) -> dict[str, float]:
    probability = prior["probability"]
    assert isinstance(probability, Mapping)
    mean_probability = sum(probability.values()) / len(probability)
    return {
        label: float(value) / mean_probability for label, value in probability.items()
    }


def _normalized_by_split(
    records_by_split: Mapping[str, Sequence[QueryRecord]],
    label_by_key_by_split: Mapping[str, Mapping[str, str]],
    *,
    rank_weight: Callable[[int, int], float],
    variant: str,
    prior_multiplier: Mapping[str, float],
) -> dict[str, list[dict[str, float]]]:
    return {
        split: [
            _fused_scores(
                record,
                rank_weight=rank_weight,
                use_prior="prior" in variant,
                use_agreement="agreement" in variant,
                prior_multiplier=prior_multiplier,
                label_by_key=label_by_key_by_split[split],
            )
            for record in records
        ]
        for split, records in records_by_split.items()
    }


def _score_cell(
    records_by_split: Mapping[str, Sequence[QueryRecord]],
    normalized_by_split: Mapping[str, Sequence[Mapping[str, float]]],
    alpha: float,
    tau: float | None,
) -> tuple[dict[str, object], float, int]:
    per_split: dict[str, object] = {}
    worst_accuracy = 1.0
    worst_delta = 10**9
    for split, records in records_by_split.items():
        correct = 0
        wrong_to_correct = 0
        correct_to_wrong = 0
        changed = 0
        primary_correct = 0
        for record, normalized in zip(records, normalized_by_split[split]):
            decision = _blend_decision(record, normalized, alpha, tau)
            was_right = record.primary_key_id == record.gold_key_id
            is_right = decision == record.gold_key_id
            correct += int(is_right)
            primary_correct += int(was_right)
            if decision != record.primary_key_id:
                changed += 1
                if is_right and not was_right:
                    wrong_to_correct += 1
                elif was_right and not is_right:
                    correct_to_wrong += 1
        per_split[split] = {
            "correct": correct,
            "count": len(records),
            "accuracy": correct / len(records),
            "primary_correct": primary_correct,
            "delta_vs_primary": correct - primary_correct,
            "changed_decisions": changed,
            "wrong_to_correct": wrong_to_correct,
            "correct_to_wrong": correct_to_wrong,
        }
        worst_accuracy = min(worst_accuracy, correct / len(records))
        worst_delta = min(worst_delta, correct - primary_correct)
    return per_split, worst_accuracy, worst_delta


def alpha_blend_grid(
    records_by_split: Mapping[str, Sequence[QueryRecord]],
    label_by_key_by_split: Mapping[str, Mapping[str, str]],
    prior: Mapping[str, object],
) -> dict[str, object]:
    """Replay the frozen baseline form's alpha-blend decision layer offline."""

    prior_multiplier = _prior_multiplier(prior)
    cells: list[dict[str, object]] = []
    for weight_id, rank_weight in RANK_WEIGHTS.items():
        for variant in EVIDENCE_VARIANTS:
            normalized_by_split = _normalized_by_split(
                records_by_split,
                label_by_key_by_split,
                rank_weight=rank_weight,
                variant=variant,
                prior_multiplier=prior_multiplier,
            )
            for tau in TAUS:
                for alpha in ALPHAS:
                    per_split, worst_accuracy, worst_delta = _score_cell(
                        records_by_split, normalized_by_split, alpha, tau
                    )
                    cells.append(
                        {
                            "cell_id": f"{weight_id}|{variant}|tau="
                            f"{'off' if tau is None else tau}|alpha={alpha}",
                            "rank_weight": weight_id,
                            "evidence_variant": variant,
                            "tau": tau,
                            "alpha": alpha,
                            "per_split": per_split,
                            "worst_split_accuracy": worst_accuracy,
                            "worst_split_delta_vs_primary": worst_delta,
                        }
                    )
    return {
        "grid_size": len(cells),
        "axes": {
            "alpha": list(ALPHAS),
            "rank_weight": list(RANK_WEIGHTS),
            "evidence_variant": list(EVIDENCE_VARIANTS),
            "tau": ["off" if tau is None else tau for tau in TAUS],
        },
        "agreement_gain": AGREEMENT_GAIN,
        "agreement_semantics": {
            E108_SPLIT_NAME: "the single evidence-conditioned candidate-action "
            "key (plus a stable boundary key when one was acquired)",
            C108_SPLIT_NAME: "every candidate the grounded verifier marked "
            "compatible (may endorse more than one key)",
            "caveat": "the two endorsement channels are different in kind; the "
            "agreement axis is therefore only loosely comparable across splits",
        },
        "cells": cells,
    }


def fine_alpha_scan(
    records_by_split: Mapping[str, Sequence[QueryRecord]],
    label_by_key_by_split: Mapping[str, Mapping[str, str]],
    prior: Mapping[str, object],
) -> dict[str, object]:
    """How WIDE is the alpha region that beats primary on both splits?

    The coarse grid reports accuracy at ten-percent alpha steps. A starting knob
    recommended off a single grid point is a knife edge, not an operating point,
    and would not survive a DEV-100 re-fit. This supplementary scan walks alpha
    in one-percent steps across the switching region and reports, per
    (rank weight, evidence variant, tau) combination, the exact alpha values at
    which the blend beats the primary on BOTH splits, plus the widest contiguous
    such interval. Same model-free replay, same logged trajectories, no contact.
    """

    prior_multiplier = _prior_multiplier(prior)
    combinations: list[dict[str, object]] = []
    for weight_id, rank_weight in RANK_WEIGHTS.items():
        for variant in EVIDENCE_VARIANTS:
            normalized_by_split = _normalized_by_split(
                records_by_split,
                label_by_key_by_split,
                rank_weight=rank_weight,
                variant=variant,
                prior_multiplier=prior_multiplier,
            )
            for tau in TAUS:
                deltas: list[dict[str, object]] = []
                positive: list[float] = []
                for alpha in FINE_ALPHAS:
                    per_split, _accuracy, worst_delta = _score_cell(
                        records_by_split, normalized_by_split, alpha, tau
                    )
                    deltas.append(
                        {
                            "alpha": alpha,
                            "worst_split_delta_vs_primary": worst_delta,
                            "per_split_delta": {
                                split: int(values["delta_vs_primary"])
                                for split, values in per_split.items()
                            },
                        }
                    )
                    if worst_delta > 0:
                        positive.append(alpha)
                widest: tuple[float, float] | None = None
                if positive:
                    start = previous = positive[0]
                    best_span = (start, previous)
                    for alpha in positive[1:]:
                        if round(alpha - previous, 2) <= 0.01:
                            previous = alpha
                        else:
                            if previous - start >= best_span[1] - best_span[0]:
                                best_span = (start, previous)
                            start = previous = alpha
                    if previous - start >= best_span[1] - best_span[0]:
                        best_span = (start, previous)
                    widest = best_span
                combinations.append(
                    {
                        "combination_id": f"{weight_id}|{variant}|tau="
                        f"{'off' if tau is None else tau}",
                        "rank_weight": weight_id,
                        "evidence_variant": variant,
                        "tau": tau,
                        "both_splits_positive_alpha_count": len(positive),
                        "both_splits_positive_alphas": positive,
                        "widest_contiguous_both_splits_interval": (
                            list(widest) if widest is not None else None
                        ),
                        "widest_interval_width": (
                            round(widest[1] - widest[0], 2)
                            if widest is not None
                            else 0.0
                        ),
                        "alpha_profile": deltas,
                    }
                )
    ranked = sorted(
        combinations,
        key=lambda item: (
            -float(item["widest_interval_width"]),
            -int(item["both_splits_positive_alpha_count"]),
            str(item["combination_id"]),
        ),
    )
    return {
        "alpha_step": 0.01,
        "alpha_range": [FINE_ALPHAS[0], FINE_ALPHAS[-1]],
        "combination_count": len(combinations),
        "combinations_with_any_both_splits_win": sum(
            1
            for item in combinations
            if int(item["both_splits_positive_alpha_count"]) > 0
        ),
        "widest_both_splits_interval": ranked[0]["widest_contiguous_both_splits_interval"],
        "widest_both_splits_combination_id": ranked[0]["combination_id"],
        "ranking": [
            {
                "combination_id": item["combination_id"],
                "widest_contiguous_both_splits_interval": item[
                    "widest_contiguous_both_splits_interval"
                ],
                "widest_interval_width": item["widest_interval_width"],
                "both_splits_positive_alpha_count": item[
                    "both_splits_positive_alpha_count"
                ],
            }
            for item in ranked
        ],
        "combinations": combinations,
    }


def cell_decision_detail(
    cell_id: str,
    records_by_split: Mapping[str, Sequence[QueryRecord]],
    label_by_key_by_split: Mapping[str, Mapping[str, str]],
    prior: Mapping[str, object],
) -> dict[str, object]:
    """Every decision one cell CHANGES, with its outcome, for audit."""

    weight_id, variant, tau_text, alpha_text = cell_id.split("|")
    tau = None if tau_text == "tau=off" else float(tau_text.split("=")[1])
    alpha = float(alpha_text.split("=")[1])
    normalized_by_split = _normalized_by_split(
        records_by_split,
        label_by_key_by_split,
        rank_weight=RANK_WEIGHTS[weight_id],
        variant=variant,
        prior_multiplier=_prior_multiplier(prior),
    )
    changes: dict[str, object] = {}
    for split, records in records_by_split.items():
        labels = label_by_key_by_split[split]
        rows: list[dict[str, object]] = []
        for record, normalized in zip(records, normalized_by_split[split]):
            decision = _blend_decision(record, normalized, alpha, tau)
            if decision == record.primary_key_id:
                continue
            was_right = record.primary_key_id == record.gold_key_id
            is_right = decision == record.gold_key_id
            rows.append(
                {
                    "sample_id": record.sample_id,
                    "primary_label": labels[record.primary_key_id],
                    "chosen_label": labels[decision],
                    "gold_label": labels[record.gold_key_id],
                    "logged_top_labels": [
                        labels[key_id] for key_id in record.top_key_ids
                    ],
                    "agreement_labels": sorted(
                        labels[key_id] for key_id in record.agreement_key_ids
                    ),
                    "outcome": (
                        "wrong-to-correct"
                        if is_right and not was_right
                        else "correct-to-wrong"
                        if was_right and not is_right
                        else "wrong-to-wrong"
                    ),
                }
            )
        changes[split] = rows
    return {"cell_id": cell_id, "alpha": alpha, "tau": tau, "changed_decisions": changes}


def _sensitivity(cells: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Which knob moves accuracy at all, marginalizing over the others."""

    report: dict[str, object] = {}
    for axis in ("alpha", "rank_weight", "evidence_variant", "tau"):
        by_value: dict[str, list[float]] = {}
        for cell in cells:
            key = str(cell[axis])
            by_value.setdefault(key, []).append(float(cell["worst_split_accuracy"]))
        summary = {
            value: {
                "best_worst_split_accuracy": max(values),
                "mean_worst_split_accuracy": sum(values) / len(values),
            }
            for value, values in sorted(by_value.items())
        }
        spread = max(
            item["best_worst_split_accuracy"] for item in summary.values()
        ) - min(item["best_worst_split_accuracy"] for item in summary.values())
        report[axis] = {
            "by_value": summary,
            "best_cell_spread": spread,
            "moves_accuracy": spread > 0.0,
        }
    return report


# --- driver ------------------------------------------------------------------


def run_sweep(data_root: Path) -> dict[str, object]:
    e108_records, e108_labels = load_e108_records()
    c108_records, c108_labels = load_c108_records()
    prior = load_scenario_prior(data_root)
    records_by_split = {
        E108_SPLIT_NAME: e108_records,
        C108_SPLIT_NAME: c108_records,
    }
    labels_by_split = {
        E108_SPLIT_NAME: e108_labels,
        C108_SPLIT_NAME: c108_labels,
    }
    grid = alpha_blend_grid(records_by_split, labels_by_split, prior)
    cells = grid["cells"]
    assert isinstance(cells, list)
    # Selection is BEST-CELL-BY-WORST-SPLIT and the ordering key is the worst
    # per-split DELTA against that split's own primary, not raw accuracy: the
    # two splits have different primaries (92 vs 90), so raw worst accuracy
    # silently rewards a cell that damages E108 while lifting C108.
    best_by_worst = sorted(
        cells,
        key=lambda cell: (
            -int(cell["worst_split_delta_vs_primary"]),
            -sum(
                int(split["delta_vs_primary"]) for split in cell["per_split"].values()
            ),
            sum(int(split["correct_to_wrong"]) for split in cell["per_split"].values()),
            float(cell["alpha"]),
            str(cell["cell_id"]),
        ),
    )
    best_per_split = {}
    best_per_split_detail = {}
    for split in records_by_split:
        winner = max(
            cells,
            key=lambda cell: (
                int(cell["per_split"][split]["correct"]),
                -float(cell["alpha"]),
            ),
        )
        best_per_split[split] = winner["cell_id"]
        best_per_split_detail[split] = {
            "cell_id": winner["cell_id"],
            "this_split": winner["per_split"][split],
            "other_splits": {
                other: values
                for other, values in winner["per_split"].items()
                if other != split
            },
        }
    beats_both = [
        cell
        for cell in cells
        if all(
            int(split["delta_vs_primary"]) > 0 for split in cell["per_split"].values()
        )
    ]
    no_harm_both = [
        cell
        for cell in cells
        if all(
            int(split["delta_vs_primary"]) >= 0 for split in cell["per_split"].values()
        )
        and any(
            int(split["delta_vs_primary"]) > 0
            for split in cell["per_split"].values()
        )
    ]
    e108_recall = recall_curve(e108_records, e108_labels)
    c108_recall = recall_curve(c108_records, c108_labels)
    fine_alpha = fine_alpha_scan(records_by_split, labels_by_split, prior)
    return {
        "schema": SCHEMA,
        "tier": TIER,
        "authority": AUTHORITY,
        "exposure_row": EXPOSURE_ROW,
        "frame": FRAME,
        "service_contact_count": 0,
        "inputs": {
            "e108": {
                "run_dir": str(E108_RUN_DIR),
                "decisions_sha256": E108_DECISIONS_SHA256,
                "binding_relpath": E108_BINDING_RELPATH,
                "binding_sha256": E108_BINDING_SHA256,
                "decision_graph_relpath": E108_GRAPH_RELPATH,
                "decision_graph_sha256": E108_GRAPH_SHA256,
                "parser": "core.driver.speech_native."
                "_parse_m11_adaptive_evidence_gap_trajectory",
            },
            "c108": {
                "run_dir": str(C108_RUN_DIR),
                "decisions_sha256": C108_DECISIONS_SHA256,
                "binding_relpath": C108_BINDING_RELPATH,
                "binding_sha256": C108_BINDING_SHA256,
                "parser": "reader M6 field contract mirrored in "
                "analysis.m11_operating_point_sweep.load_c108_records",
            },
            "prior": {
                key: value for key, value in prior.items() if key != "probability"
            },
        },
        "boundary_firing_curve": firing_rate_curve(e108_records),
        "retrieval_curves": {
            E108_SPLIT_NAME: e108_recall,
            C108_SPLIT_NAME: c108_recall,
        },
        "alpha_blend_grid": grid,
        "headline": {
            "selection_rule": "best-cell-by-worst-split on per-split DELTA vs "
            "that split's own primary; never best-by-single-split",
            "best_cell_per_split": best_per_split,
            "best_cell_per_split_detail": best_per_split_detail,
            "best_cell_by_worst_split": best_by_worst[0]["cell_id"],
            "best_cell_by_worst_split_detail": best_by_worst[0],
            "top_10_by_worst_split": [cell["cell_id"] for cell in best_by_worst[:10]],
            "cells_beating_primary_on_both_splits": len(beats_both),
            "cells_beating_primary_on_one_split_without_harming_the_other": len(
                no_harm_both
            ),
            "cell_ids_beating_primary_on_both_splits": [
                cell["cell_id"] for cell in beats_both
            ][:20],
            "honest_ceiling": {
                split: {
                    "primary_correct": curves["primary_correct"],
                    "blend_layer_ceiling": curves["blend_layer_ceiling"][
                        "union_reachable_count"
                    ],
                    "headroom_above_primary": int(
                        curves["blend_layer_ceiling"]["union_reachable_count"]
                    )
                    - int(curves["primary_correct"]),
                }
                for split, curves in (
                    (E108_SPLIT_NAME, e108_recall),
                    (C108_SPLIT_NAME, c108_recall),
                )
            },
            "registered_action_family_oracle_e108": {
                "value": 94,
                "source": "docs/checks/speech-aware-evidence-acquisition/"
                "2026-08-23-e108-zcopy-read/read-verdict.json",
                "status": "diagnostic-only-not-an-admissible-controller",
            },
        },
        "fine_alpha_robustness_scan": fine_alpha,
        "recommended_cell_decision_detail": cell_decision_detail(
            best_by_worst[0]["cell_id"],
            records_by_split,
            labels_by_split,
            prior,
        ),
        "sensitivity": _sensitivity(cells),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Model-free iteration-tier operating-point sweep over already-"
            "exposed E108/C108 trajectories. Produces DESIGN INPUTS only."
        )
    )
    parser.add_argument("--out", required=True, help="destination JSON path")
    parser.add_argument(
        "--data-root",
        default=os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET",
        help="data root (default: SAEA_DATA_ROOT / SPEECHRL_DATA_DIR; holds the KB snapshot)",
    )
    args = parser.parse_args(argv)
    import speech_aware_evidence_acquisition as package

    package_file = Path(package.__file__ or "").resolve()
    expected_root = (REPO_ROOT / "src" / "speech_aware_evidence_acquisition").resolve()
    if package_file.parent != expected_root:
        raise SweepError(
            f"package __file__ {package_file} is not the checkout under {expected_root}"
        )
    report = run_sweep(Path(args.data_root))
    report["package_file"] = str(package_file)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False)
    out_path.write_text(payload + "\n", encoding="utf-8")
    print(f"wrote {out_path} ({len(payload)} bytes)")
    print(f"sha256 {hashlib.sha256(payload.encode('utf-8')).hexdigest()}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
