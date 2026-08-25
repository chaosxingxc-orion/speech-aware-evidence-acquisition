"""Model-free pre-analysis of the CONTRAST-FEWSHOT (E-A) design.

Exposure row ``SAEA-SN-MF-CONTRAST-FEWSHOT-PREANALYSIS`` (registered before
any computation): zero frozen-core contacts, zero embedding-tool contacts,
zero HTTP or socket requests of any kind. Every byte this module reads is
already landed and already scored -- the sealed DEV-100 round-4/round-5
frozen-cell attempt stores, the sealed DEV-500 confirmatory BLEND arm, the
committed round and arm reports, the committed split receipts, the pinned
TRAIN knowledge snapshot, and its landed content-facet vector NPZ. Nothing
is embedded, encoded, decoded, generated, or requested.

Non-contact is proven BY CONSTRUCTION, not by a service log
-----------------------------------------------------------
:func:`.dev100_reviewer_audit.arm_offline_guard` is called before a single
input is opened: it replaces ``socket.socket.connect``,
``socket.socket.connect_ex`` and ``socket.create_connection`` with counting
refusers, and the attempt counter is emitted in the report. A concurrent
flight may hold the resident decoder unit, so -- unlike the damage-channel
row -- this module makes NO server-log byte-identity claim and reads or
writes no file belonging to another campaign.

What CONTRAST-FEWSHOT (E-A) proposes
------------------------------------
The frozen cell's supply stage already fuses recall into at most
``top_l = 3`` task targets, each carrying at most ``c = 2`` TRAIN exemplar
values, and hands them to the frozen core as a FLAT list ordered by
``value_id`` (``_fuse_supply_filter`` returns ``tuple(sorted(set(...)))``).
E-A proposes that when the fused label distribution's top two targets are
CLOSE -- a margin signal computed entirely from runtime-legal quantities --
the supply is narrowed to that confusable pair and rendered CONTRASTIVELY:
``n`` balanced nearest exemplars per side, grouped by side, with the
discrimination stated explicitly, so the evidence contact is asked to
separate two candidates rather than to absorb an unordered mixture.

The standing negative control this must be distinguished from is the sealed
DEV-500 ``ABL-RANDICL`` arm: RANDOM exemplars cost -5.5 pp. E-A changes
neither the retrieval nor the exemplar source -- it changes only which
retrieved targets are supplied and how they are ORGANIZED, so it is an
ORG/SUPPLY move over the same retrieved content, which is exactly the axis
``ABL-RANDICL`` did not test.

What this module can and cannot say
-----------------------------------
Identical honesty discipline to
:mod:`.dev100_damage_channel_analysis`: any change to the supplied evidence
block changes the evidence prompt, and the frozen core's answer to a CHANGED
prompt is NOT knowable offline. So this module computes, exactly:

* the trigger's coverage -- which samples a margin threshold selects, split
  by the sealed BLEND outcome;
* the ceiling -- whether GOLD is inside the fused top-2 (the two-way
  contrast) or the fused top-3 (a three-way variant), which is the
  NECESSARY condition for a contrastive supply to be able to help at all;
* the exemplar supply available per side of each triggered pair;
* the offline-knowable part of the risk to already-correct samples.

It never asserts a counterfactual accuracy as a measured result. The
registered prediction it emits is a PREDICTION, to be scored against a
flight if and only if the coordinator and owner authorize one.
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as ra
from . import dev500_confirmatory_read as d5
from ..rails import kb_policy as kb
from ..rails.knowledge import KnowledgeSnapshot

SCHEMA = "saea-contrast-fewshot-preanalysis-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-CONTRAST-FEWSHOT-PREANALYSIS"

# The FROZEN cell (configs/policy/kb-policy-v1-dev100.json, and the committed
# round-4/round-5 ``round*_knobs`` blocks, which agree byte-for-byte).
FROZEN_ALPHA = 0.45
FROZEN_TOP_K = 5
FROZEN_WEIGHTS = kb.RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2)
FROZEN_FUSE = kb.FuseKnobs(tau=0.65, m=5, c=2, top_l=3)
FROZEN_POLICY_CONFIG_RELPATH = "configs/policy/kb-policy-v1-dev100.json"

# Threshold grid for the trigger trade-off curve.
MARGIN_GRID = (
    0.0,
    0.02,
    0.05,
    0.08,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
    0.50,
    0.60,
    0.75,
    0.90,
    1.00,
)

# Candidate ``n`` values for the per-side exemplar budget.
EXEMPLAR_N_GRID = (2, 3, 4)

# How many samples per population are cross-checked against a real
# ``kb.multidim_recall`` call before the vectorised recall is trusted.
RECALL_FIDELITY_PROBES = 8

# The operating point this pre-analysis recommends, and which its registered
# prediction is computed at (docs/readiness/2026-08-24-contrast-fewshot-preanalysis.md
# section 7). The trigger is the COSINE margin because the briefed fused-score
# margin is degenerate; the scope overrides retain-primary because the
# dispatch-only ceiling is 2 errors on DEV-100 and 4 on NEW400.
RECOMMENDED_COS_MARGIN = 0.02
RECOMMENDED_EXEMPLARS_PER_SIDE = 3
RECOMMENDED_SCOPE = "all"
RECOMMENDED_DISAGREEMENT_GATE = False


class PreanalysisError(RuntimeError):
    """Raised when a landed input does not match its pinned identity."""


# ---------------------------------------------------------------------------
# Population pins
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CellPin:
    """One sealed flight of the FROZEN cell, and the id set to read from it."""

    population_id: str
    run_id: str
    attempt_id: str
    outputs_basename: str
    arm_key: str
    report_relpath: str | None
    report_arm_key: str | None
    restrict_to: str | None  # a d5.Populations field name, or None for "all"


CELL_PINS = (
    CellPin(
        population_id="DEV-100-ROUND4",
        run_id="SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN",
        attempt_id="attempt-20260824T181942Z-dev100r4",
        outputs_basename="round4-outputs.jsonl",
        arm_key="BLEND_ROUND4",
        report_relpath=(
            "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round4/"
            "round4-report.json"
        ),
        report_arm_key="BLEND_ROUND4",
        restrict_to=None,
    ),
    CellPin(
        population_id="DEV-100-ROUND5",
        run_id="SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN",
        attempt_id="attempt-20260824T190029Z-dev100r5",
        outputs_basename="round5-outputs.jsonl",
        arm_key="BLEND_ROUND5",
        report_relpath=(
            "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round5/"
            "round5-report.json"
        ),
        report_arm_key="BLEND_ROUND5",
        restrict_to=None,
    ),
    CellPin(
        population_id="DEV-500-NEW400",
        run_id="SAEA-DEV500-CONFIRMATORY",
        attempt_id="attempt-20260824T205527Z-dev500blend",
        outputs_basename="arm2-blend-outputs.jsonl",
        arm_key="BLEND",
        report_relpath=None,  # hash-pinned instead, through d5.ARM_PINS
        report_arm_key=None,
        restrict_to="new400",
    ),
)


# ---------------------------------------------------------------------------
# Landed inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SnapshotBundle:
    """The pinned TRAIN snapshot plus its landed content-facet vectors."""

    snapshot: KnowledgeSnapshot
    snapshot_sha256: str
    facet_ids: tuple[str, ...]
    matrix: object  # numpy.ndarray (n_content_facets, dim)
    facet_index: Mapping[str, int]
    npz_sha256: str
    label_targets: Mapping[str, str]
    label_texts: Mapping[str, str]
    values_by_id: Mapping[str, object]
    content_facet_target: Mapping[str, str]
    facet_indices_by_target: Mapping[str, object]  # target -> numpy int array
    values_by_target: Mapping[str, tuple[str, ...]]
    facet_id_rank: object  # numpy int array: lexicographic rank of each facet id
    prior_dimension_recall: Mapping[str, Mapping[str, float]]


def load_snapshot_bundle(*, data_root: Path, repo_root: Path) -> SnapshotBundle:
    """Load and identity-check the snapshot and its content-facet NPZ.

    Same pins and same refusals as
    :func:`.dev100_damage_channel_analysis.load_landed_inputs`; the TRAIN
    VALUE vectors (``receipt["vectors"]["values"]``) are never opened."""

    import numpy as np

    snapshot_path = Path(data_root) / dc.SNAPSHOT_RELPATH
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    snapshot_sha256 = snapshot.content_hash()
    if snapshot_sha256 != dc.SNAPSHOT_SHA256:
        raise PreanalysisError(
            f"knowledge snapshot hashes to {snapshot_sha256}, not the pinned "
            f"{dc.SNAPSHOT_SHA256}"
        )

    receipt = json.loads(
        (Path(repo_root) / dc.EMBEDDING_RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    facet_block = receipt["vectors"]["content_facets"]
    npz_path = snapshot_path.parent / facet_block["file"]
    measured_npz = dc._sha256_file(npz_path)
    if measured_npz != facet_block["sha256"]:
        raise PreanalysisError("content-facet NPZ hash mismatch vs the landed embedding receipt")
    npz = np.load(npz_path)
    facet_ids = tuple(str(value) for value in npz["ids"])
    matrix = np.asarray(npz["vectors"], dtype=np.float64)
    if matrix.shape[0] != len(facet_ids):
        raise PreanalysisError(f"unexpected facet vector shape {matrix.shape}")
    facet_index = {facet_id: index for index, facet_id in enumerate(facet_ids)}

    label_targets = kb._label_identities(snapshot)
    label_texts = {
        facet.facet_id: facet.representation
        for facet in snapshot.facets
        if facet.facet_id in label_targets
    }
    values_by_id = {value.value_id: value for value in snapshot.values}
    content_facet_target: dict[str, str] = {}
    values_by_target: dict[str, list[str]] = {}
    for value in snapshot.values:
        if value.task_target is None:
            continue
        values_by_target.setdefault(value.task_target, []).append(value.value_id)
        for facet_id in value.associated_facet_ids:
            content_facet_target.setdefault(facet_id, value.task_target)

    by_target: dict[str, list[int]] = {}
    for facet_id, target in content_facet_target.items():
        index = facet_index.get(facet_id)
        if index is not None:
            by_target.setdefault(target, []).append(index)
    facet_indices_by_target = {
        target: np.asarray(sorted(indices), dtype=np.int64)
        for target, indices in by_target.items()
    }

    # Lexicographic rank of each content facet id, so the vectorised recall
    # can reproduce ``multidim_recall``'s exact tie-break (score descending,
    # then facet_id ascending).
    lexicographic = sorted(range(len(facet_ids)), key=lambda index: facet_ids[index])
    facet_id_rank = np.empty(len(facet_ids), dtype=np.int64)
    for position, index in enumerate(lexicographic):
        facet_id_rank[index] = position

    # The label/prior half of ``multidim_recall`` is recalled by prior MASS,
    # not by any vector, so it is identical for every sample. Computing it
    # once through kb's OWN function -- with an empty query-vector mapping,
    # which makes every cosine dimension a no-op -- keeps it exact while
    # taking it out of the per-sample loop.
    prior_dimension_recall = kb.multidim_recall(snapshot, {}, lambda _facet_id: {}, FROZEN_TOP_K)

    return SnapshotBundle(
        snapshot=snapshot,
        snapshot_sha256=snapshot_sha256,
        facet_ids=facet_ids,
        matrix=matrix,
        facet_index=facet_index,
        npz_sha256=measured_npz,
        label_targets=label_targets,
        label_texts=label_texts,
        values_by_id=values_by_id,
        content_facet_target=content_facet_target,
        facet_indices_by_target=facet_indices_by_target,
        values_by_target={
            target: tuple(sorted(ids)) for target, ids in values_by_target.items()
        },
        facet_id_rank=facet_id_rank,
        prior_dimension_recall=prior_dimension_recall,
    )


def vectorised_recall(
    bundle: SnapshotBundle, cosines, *, top_k: int = FROZEN_TOP_K
) -> dict[str, dict[str, float]]:
    """``kb.multidim_recall`` for one sample, with the content dimension's
    11,514-facet cosine sweep vectorised.

    Reproduces the function's exact contract: each dimension truncates to its
    OWN top ``k`` (score descending, ``facet_id`` ascending tie-break) before
    the union, only strictly-positive scores are recalled, and the
    label/prior dimensions recall by prior mass. Fidelity is not assumed --
    :func:`replay_population` cross-checks a bounded probe of samples against
    a real ``kb.multidim_recall`` call, and the whole supply replay is then
    gated against the flown SUPPLY channel."""

    import numpy as np

    order = np.lexsort((bundle.facet_id_rank, -np.asarray(cosines)))
    recalled: dict[str, dict[str, float]] = {}
    for index in order[:top_k]:
        score = float(cosines[int(index)])
        if score <= 0.0:
            break
        recalled[bundle.facet_ids[int(index)]] = {"content": score}
    for facet_id, dim_scores in bundle.prior_dimension_recall.items():
        recalled.setdefault(facet_id, {}).update(dim_scores)
    return recalled


def _load_trace_texts(
    trace_path: Path,
) -> tuple[dict[str, str], dict[str, str], dict[str, tuple[str, ...]]]:
    """``dev100_damage_channel_analysis._load_trace`` generalized over the
    trace basename, so the same record semantics read the DEV-500 run whose
    ``run_id`` -- and therefore whose trace filename -- differs. The channel,
    record-id, and payload-key contract is unchanged."""

    texts_by_sha: dict[str, str] = {}
    contacts_by_sample: dict[str, list[Mapping[str, object]]] = {}
    supply_by_sample: dict[str, tuple[str, ...]] = {}
    with trace_path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            channel = record["channel"]
            payload = record["payload"]
            record_id = record["record_id"]
            if channel == "MODEL_RESPONSE":
                texts_by_sha[payload["response_text_sha256"]] = payload["text"]
            elif channel == "USE" and record_id.endswith(dc.RUNTIME_USE_SUFFIX):
                sample_id = record_id[: -len(dc.RUNTIME_USE_SUFFIX)]
                contacts_by_sample[sample_id] = list(payload["use_contacts"])
            elif channel == "SUPPLY" and record_id.endswith(dc.SUPPLY_SUFFIX):
                sample_id = record_id[: -len(dc.SUPPLY_SUFFIX)]
                supply_by_sample[sample_id] = tuple(
                    payload["supply_final_visible_value_ids"]
                )

    direct: dict[str, str] = {}
    evidence: dict[str, str] = {}
    for sample_id, contacts in contacts_by_sample.items():
        for contact in contacts:
            contact_id = contact["plan"]["contact_id"]
            text = texts_by_sha.get(contact["response_sha256"])
            if text is None:
                raise PreanalysisError(f"no logged response text for {sample_id} {contact_id}")
            if contact_id == "direct-decode":
                direct[sample_id] = text
            elif contact_id == "evidence-decode":
                evidence[sample_id] = text
    return direct, evidence, supply_by_sample


@dataclass(frozen=True)
class CellPopulation:
    """One frozen-cell flight, restricted to one scored population."""

    pin: CellPin
    sample_ids: tuple[str, ...]
    inputs: dc.LandedInputs
    logged_contacts: Mapping[str, int]
    final_texts: Mapping[str, str]
    run_dir: Path
    artifact_hashes: Mapping[str, str]
    committed_report: Mapping[str, object] | None
    committed_report_sha256: str | None


def load_cell_population(
    *,
    pin: CellPin,
    bundle: SnapshotBundle,
    populations: d5.Populations,
    data_root: Path,
    repo_root: Path,
) -> CellPopulation:
    """Load one sealed frozen-cell flight into a ``dc.LandedInputs`` holder.

    Reusing the damage-channel holder means :func:`dc.replay_supply` and
    :func:`dc.replay_blend` -- the very functions whose fidelity was proved
    100/100 against the round-2 flight -- are the replay path here too,
    rather than a second implementation that could drift."""

    run_dir = Path(data_root) / "runs" / pin.run_id / pin.attempt_id
    outputs_path = run_dir / pin.outputs_basename
    trace_path = run_dir / f"{pin.run_id}.trace.jsonl"

    committed_report: Mapping[str, object] | None = None
    committed_report_sha256: str | None = None
    if pin.report_relpath is not None:
        report_path = Path(repo_root) / pin.report_relpath
        committed_report_sha256 = dc._sha256_file(report_path)
        committed_report = json.loads(report_path.read_text(encoding="utf-8"))
        if str(committed_report["attempt_id"]) != pin.attempt_id:
            raise PreanalysisError(f"{pin.population_id}: committed report names another attempt")
    else:
        # The DEV-500 BLEND arm carries committed byte-level pins; verify them.
        arm_pin = next(item for item in d5.ARM_PINS if item.arm_id == pin.arm_key)
        if arm_pin.attempt_id != pin.attempt_id:
            raise PreanalysisError(f"{pin.population_id}: arm pin names another attempt")
        d5._require_hash(
            Path(repo_root) / d5.CHECK_DIR_RELPATH / arm_pin.report_basename,
            arm_pin.report_sha256,
            f"{pin.population_id} committed mechanical report",
        )
        d5._require_hash(
            outputs_path, arm_pin.outputs_sha256, f"{pin.population_id} sealed outputs"
        )

    logged_contacts: dict[str, int] = {}
    final_texts: dict[str, str] = {}
    logged_winner_labels: dict[str, str | None] = {}
    with outputs_path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if str(record["arm"]) != pin.arm_key:
                raise PreanalysisError(
                    f"{pin.population_id}: outputs carry a foreign arm {record['arm']!r}"
                )
            sample_id = str(record["sample_id"])
            logged_contacts[sample_id] = int(record["contacts"])
            final_texts[sample_id] = str(record["final_response_text"])
            winner = record.get("winner_label")
            logged_winner_labels[sample_id] = None if winner is None else str(winner)

    if pin.restrict_to is None:
        sample_ids = tuple(sorted(logged_contacts))
    else:
        wanted = set(getattr(populations, pin.restrict_to))
        missing = wanted - set(logged_contacts)
        if missing:
            raise PreanalysisError(
                f"{pin.population_id}: {len(missing)} population ids absent from the sealed arm"
            )
        sample_ids = tuple(sorted(wanted))

    query_vectors = dc._load_query_vectors(run_dir)
    direct_texts, evidence_texts, logged_supply = _load_trace_texts(trace_path)
    gold_by_sample = dc._load_gold(
        data_root=data_root, repo_root=repo_root, sample_ids=set(sample_ids)
    )

    inputs = dc.LandedInputs(
        snapshot=bundle.snapshot,
        snapshot_sha256=bundle.snapshot_sha256,
        facet_vector_ids=bundle.facet_ids,
        facet_vector_matrix=bundle.matrix,
        facet_vectors=_facet_vector_lookup(bundle),
        facet_npz_sha256=bundle.npz_sha256,
        query_vectors={
            sample_id: query_vectors[sample_id]
            for sample_id in sample_ids
            if sample_id in query_vectors
        },
        direct_texts=direct_texts,
        evidence_texts=evidence_texts,
        logged_supply=logged_supply,
        logged_winner_labels=logged_winner_labels,
        gold_by_sample=gold_by_sample,
        round_scores={},
        round_reports={},
        label_targets=bundle.label_targets,
        label_texts=bundle.label_texts,
        values_by_id=bundle.values_by_id,
        content_facet_target=bundle.content_facet_target,
    )
    missing_vectors = set(sample_ids) - set(inputs.query_vectors)
    if missing_vectors:
        raise PreanalysisError(
            f"{pin.population_id}: {len(missing_vectors)} samples have no landed query vector"
        )

    artifact_hashes = {
        pin.outputs_basename: dc._sha256_file(outputs_path),
        trace_path.name: dc._sha256_file(trace_path),
        "query-vectors.jsonl": dc._sha256_file(run_dir / "query-vectors.jsonl"),
    }

    return CellPopulation(
        pin=pin,
        sample_ids=sample_ids,
        inputs=inputs,
        logged_contacts=logged_contacts,
        final_texts=final_texts,
        run_dir=run_dir,
        artifact_hashes=artifact_hashes,
        committed_report=committed_report,
        committed_report_sha256=committed_report_sha256,
    )


def _facet_vector_lookup(bundle: SnapshotBundle):
    """A ``facet_id -> {"content": vector}`` callable over the landed NPZ,
    built lazily so the 11,514-row matrix is not copied into a dict of
    tuples three times (once per population)."""

    matrix = bundle.matrix
    index = bundle.facet_index

    def facet_vectors(facet_id: str) -> Mapping[str, Sequence[float]]:
        position = index.get(facet_id)
        if position is None:
            return {}
        return {"content": tuple(matrix[position].tolist())}

    return facet_vectors


# ---------------------------------------------------------------------------
# Per-sample replay at the frozen cell
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SampleReplay:
    """Everything the trigger, the ceiling, and the risk account need."""

    sample_id: str
    gold_target: str
    correct: bool
    parsed: bool
    logged_contacts: int
    retain_primary: bool
    supply_empty: bool
    dispatched: bool
    direct_label: str | None
    direct_target: str | None
    selected_value_ids: tuple[str, ...]
    fused_ranked: tuple[tuple[str, float], ...]  # (task_target, score) desc
    margin_top2: float
    cos_top1: float | None
    cos_top2: float | None
    cos_margin: float
    direct_agrees_with_fused_top1: bool
    gold_fused_rank: int | None
    gold_facet_position: int | None
    gold_facet_cosine: float | None
    supplied_per_target: Mapping[str, int]
    admitted_count: int


def _fused_ranked_targets(
    fused: Mapping[str, float], label_targets: Mapping[str, str]
) -> tuple[tuple[str, float], ...]:
    """Collapse the label-facet-keyed fused scores onto task targets.

    ``_fused_label_scores`` is keyed by label FACET id; several facet ids can
    resolve to the same intent identity, and the E-A pair is a pair of
    INTENTS, so the scores are folded onto ``task_target`` (taking the max,
    which is what ``_argmax_labels`` would see) before ranking."""

    by_target: dict[str, float] = {}
    for facet_id, score in fused.items():
        if score <= 0.0:
            continue
        target = label_targets[facet_id]
        by_target[target] = max(by_target.get(target, 0.0), score)
    return tuple(sorted(by_target.items(), key=lambda item: (-item[1], item[0])))


def replay_population(
    population: CellPopulation, bundle: SnapshotBundle
) -> tuple[dict[str, SampleReplay], dict[str, object]]:
    """Replay the frozen cell over one population and gate it on the flight.

    The gate is stronger than the damage-channel row's: it checks the
    replayed RETAIN-PRIMARY / DISPATCH decision against the flown per-sample
    contact count on EVERY sample (1 contact means retain-primary fired,
    2 means the evidence contact dispatched), and, on the dispatched
    samples, checks the replayed ``selected_value_ids`` against the flown
    SUPPLY channel exactly."""

    import numpy as np

    inputs = population.inputs
    matrix = np.asarray(bundle.matrix, dtype=np.float64)
    facet_norms = np.linalg.norm(matrix, axis=1)

    replays: dict[str, SampleReplay] = {}
    decision_matches = 0
    decision_mismatches: list[dict[str, object]] = []
    supply_matches = 0
    supply_mismatches: list[dict[str, object]] = []
    dispatched_seen = 0
    cosine_probes = 0
    recall_probes = 0

    for probe_position, sample_id in enumerate(population.sample_ids):
        query = np.asarray(inputs.query_vectors[sample_id], dtype=np.float64)
        denominator = facet_norms * float(np.linalg.norm(query))
        with np.errstate(divide="ignore", invalid="ignore"):
            cosines = np.where(denominator > 0.0, matrix @ query / denominator, 0.0)
        recall_scores = vectorised_recall(bundle, cosines, top_k=FROZEN_TOP_K)
        if probe_position < RECALL_FIDELITY_PROBES:
            reference = kb.multidim_recall(
                bundle.snapshot,
                {"content": inputs.query_vectors[sample_id]},
                inputs.facet_vectors,
                FROZEN_TOP_K,
            )
            if set(reference) != set(recall_scores):
                raise PreanalysisError(
                    f"{sample_id}: vectorised recall admitted a different facet set than "
                    "kb.multidim_recall"
                )
            for facet_id, dim_scores in reference.items():
                for dimension, score in dim_scores.items():
                    if abs(score - recall_scores[facet_id][dimension]) > 1e-9:
                        raise PreanalysisError(
                            f"{sample_id}/{facet_id}/{dimension}: vectorised recall score "
                            "disagrees with kb.multidim_recall"
                        )
            recall_probes += 1

        supply = dc.replay_supply(
            inputs,
            sample_id,
            weights=FROZEN_WEIGHTS,
            knobs=FROZEN_FUSE,
            top_k=FROZEN_TOP_K,
            recall_scores=recall_scores,
        )
        direct_label = kb.default_label_normalizer(
            inputs.direct_texts[sample_id], inputs.label_targets
        )
        blend = dc.replay_blend(
            inputs, supply, direct_label=direct_label, alpha=FROZEN_ALPHA
        )
        # The controller stops at ONE contact in three cases: nothing was
        # recalled, nothing was selected for supply, or the direct label is
        # the pre-evidence blend's unique winner (retain-primary). Only the
        # third is retain-primary proper; the first two are "no evidence to
        # dispatch", which the sealed outputs also record as one contact.
        supply_empty = not supply.selected_value_ids
        retain = blend.retain_primary and not supply_empty

        logged_contacts = population.logged_contacts[sample_id]
        replayed_contacts = 1 if (retain or supply_empty) else 2
        if replayed_contacts == logged_contacts:
            decision_matches += 1
        else:
            decision_mismatches.append(
                {
                    "sample_id": sample_id,
                    "logged_contacts": logged_contacts,
                    "replayed_contacts": replayed_contacts,
                }
            )
        if logged_contacts == 2:
            dispatched_seen += 1
            logged = tuple(sorted(inputs.logged_supply.get(sample_id, ())))
            recomputed = tuple(sorted(supply.selected_value_ids))
            if logged == recomputed:
                supply_matches += 1
            else:
                supply_mismatches.append(
                    {"sample_id": sample_id, "logged": logged, "recomputed": recomputed}
                )

        gold = inputs.gold_by_sample[sample_id]
        gold_target = f"{gold.scenario}_{gold.action}"
        scored = dc.score_response(gold, population.final_texts[sample_id])

        fused_ranked = _fused_ranked_targets(blend.fused_label_scores, inputs.label_targets)
        # Fewer than two fused targets means there is no second side and so
        # no confusable pair at all: the margin is defined as the maximally
        # UNambiguous 1.0 so that no threshold below 1.0 ever triggers on it.
        if len(fused_ranked) < 2:
            margin = 1.0
        else:
            margin = fused_ranked[0][1] - fused_ranked[1][1]
        gold_fused_rank = next(
            (
                position
                for position, (target, _score) in enumerate(fused_ranked, start=1)
                if target == gold_target
            ),
            None,
        )

        # The SECOND, non-degenerate margin signal: the raw cosine of each
        # side's best admitted supporting facet. The fused score is
        # ``w_cos * cos + w_agree / dims_total`` with ``w_prior`` mass zero on
        # every content facet, then normalized across the supplied targets --
        # an affine squash followed by a normalization, which compresses a
        # real cosine spread into a near-uniform distribution. The underlying
        # cosine is not squashed and is equally runtime-legal.
        best_cos_by_target: dict[str, float] = {}
        for facet_id in supply.admitted_facet_ids:
            target = bundle.content_facet_target.get(facet_id)
            if target is None:
                continue
            score = recall_scores.get(facet_id, {}).get("content")
            if score is None:
                continue
            best_cos_by_target[target] = max(best_cos_by_target.get(target, 0.0), score)
        cos_top1 = (
            best_cos_by_target.get(fused_ranked[0][0]) if fused_ranked else None
        )
        cos_top2 = (
            best_cos_by_target.get(fused_ranked[1][0]) if len(fused_ranked) > 1 else None
        )
        cos_margin = (
            cos_top1 - cos_top2
            if (cos_top1 is not None and cos_top2 is not None)
            else 1.0
        )

        # Full-KB cosine ordering, for the recall-limited partition and for
        # per-side exemplar availability. Pinned to kb_policy's own scalar
        # cosine on this sample's top-8 facets plus the gold-bearing one.
        order = np.argsort(-cosines, kind="stable")
        gold_position: int | None = None
        for rank_position, index in enumerate(order, start=1):
            if bundle.content_facet_target.get(bundle.facet_ids[int(index)]) == gold_target:
                gold_position = rank_position
                break
        gold_cosine = (
            float(cosines[int(order[gold_position - 1])]) if gold_position is not None else None
        )
        probes = [int(index) for index in order[:8]]
        if gold_position is not None:
            probes.append(int(order[gold_position - 1]))
        for index in probes:
            policy_value = kb._cosine(
                tuple(query.tolist()), tuple(matrix[index].tolist())
            )
            if abs(policy_value - float(cosines[index])) > 1e-9:
                raise PreanalysisError(
                    f"{sample_id}/{bundle.facet_ids[index]}: vectorised cosine disagrees "
                    "with kb_policy._cosine"
                )
            cosine_probes += 1

        supplied_per_target: dict[str, int] = {}
        for value_id in supply.selected_value_ids:
            target = inputs.values_by_id[value_id].task_target
            if target is not None:
                supplied_per_target[target] = supplied_per_target.get(target, 0) + 1

        replays[sample_id] = SampleReplay(
            sample_id=sample_id,
            gold_target=gold_target,
            correct=bool(scored["correct"]),
            parsed=bool(scored["parsed"]),
            logged_contacts=logged_contacts,
            retain_primary=retain,
            supply_empty=supply_empty,
            dispatched=replayed_contacts == 2,
            direct_label=direct_label,
            direct_target=(
                inputs.label_targets[direct_label] if direct_label is not None else None
            ),
            selected_value_ids=tuple(supply.selected_value_ids),
            fused_ranked=fused_ranked,
            margin_top2=margin,
            cos_top1=cos_top1,
            cos_top2=cos_top2,
            cos_margin=cos_margin,
            direct_agrees_with_fused_top1=bool(
                fused_ranked
                and direct_label is not None
                and inputs.label_targets[direct_label] == fused_ranked[0][0]
            ),
            gold_fused_rank=gold_fused_rank,
            gold_facet_position=gold_position,
            gold_facet_cosine=gold_cosine,
            supplied_per_target=supplied_per_target,
            admitted_count=len(supply.admitted_facet_ids),
        )
        # Keep the per-sample cosine vector for the exemplar-availability
        # pass rather than recomputing it: stash it on the replay map.
        _COSINE_CACHE[(population.pin.population_id, sample_id)] = cosines

    gate = {
        "population": population.pin.population_id,
        "samples": len(population.sample_ids),
        "retain_dispatch_decision_matches": decision_matches,
        "retain_dispatch_decision_mismatches": decision_mismatches[:10],
        "retain_dispatch_gate_passed": decision_matches == len(population.sample_ids),
        "dispatched_samples": dispatched_seen,
        "supply_exact_matches": supply_matches,
        "supply_mismatches": supply_mismatches[:10],
        "supply_gate_passed": supply_matches == dispatched_seen,
        "cosine_agreement_probes_vs_kb_policy": cosine_probes,
        "vectorised_recall_probes_vs_kb_multidim_recall": recall_probes,
    }
    if population.committed_report is not None and population.pin.report_arm_key:
        arm = population.committed_report["arms"][population.pin.report_arm_key]
        replayed_retained = sum(1 for r in replays.values() if r.retain_primary)
        gate["committed_report_sha256"] = population.committed_report_sha256
        gate["committed_retain_primary_samples"] = int(arm["retain_primary_samples"])
        gate["replayed_retain_primary_samples"] = replayed_retained
        gate["committed_correct_count"] = int(arm["correct_count"])
        gate["rescored_correct_count"] = sum(1 for r in replays.values() if r.correct)
        gate["committed_anchor_gate_passed"] = (
            replayed_retained == int(arm["retain_primary_samples"])
            and gate["rescored_correct_count"] == int(arm["correct_count"])
        )
    return replays, gate


# Per-population, per-sample full-KB cosine vectors, kept between the replay
# pass and the exemplar-availability pass so the 11,514-facet matmul runs
# exactly once per sample.
_COSINE_CACHE: dict[tuple[str, str], object] = {}


# ---------------------------------------------------------------------------
# Question 1 -- the trigger
# ---------------------------------------------------------------------------


def _descriptives(values: Sequence[float]) -> dict[str, object]:
    if not values:
        return {"n": 0}
    ordered = sorted(values)

    def percentile(fraction: float) -> float:
        index = min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))
        return round(ordered[index], 4)

    return {
        "n": len(ordered),
        "min": round(ordered[0], 4),
        "p10": percentile(0.10),
        "p25": percentile(0.25),
        "median": round(statistics.median(ordered), 4),
        "p75": percentile(0.75),
        "p90": percentile(0.90),
        "max": round(ordered[-1], 4),
        "mean": round(statistics.fmean(ordered), 4),
        "at_or_below_0_10": sum(1 for value in ordered if value <= 0.10),
        "at_or_below_0_25": sum(1 for value in ordered if value <= 0.25),
        "exactly_1_0_single_supplied_target": sum(
            1 for value in ordered if abs(value - 1.0) <= 1e-9
        ),
    }


def trigger_analysis(
    replays: Mapping[str, SampleReplay], *, scope: str
) -> dict[str, object]:
    """Margin distribution and threshold trade-off curve, in one scope.

    ``scope`` is ``"all"`` (the trigger may also override retain-primary and
    force a dispatch) or ``"dispatched"`` (the trigger only re-organizes an
    evidence contact that the frozen cell was going to make anyway, so it
    costs no extra frozen-core contact and cannot touch a retained
    trajectory)."""

    if scope == "dispatched":
        members = [r for r in replays.values() if r.dispatched]
    elif scope == "all":
        members = list(replays.values())
    else:  # pragma: no cover - guarded by the caller
        raise PreanalysisError(f"unknown trigger scope {scope!r}")

    wrong = [r for r in members if not r.correct]
    right = [r for r in members if r.correct]
    curve = []
    for threshold in MARGIN_GRID:
        triggered = [r for r in members if r.margin_top2 <= threshold + 1e-9]
        captured = [r for r in triggered if not r.correct]
        disturbed = [r for r in triggered if r.correct]
        reachable = [
            r for r in captured if r.gold_fused_rank is not None and r.gold_fused_rank <= 2
        ]
        curve.append(
            {
                "margin_threshold": threshold,
                "triggered": len(triggered),
                "trigger_rate": round(len(triggered) / len(members), 4) if members else 0.0,
                "errors_captured": len(captured),
                "errors_captured_share_of_all_errors": (
                    round(len(captured) / len(wrong), 4) if wrong else None
                ),
                "correct_samples_disturbed": len(disturbed),
                "correct_disturbed_share_of_all_correct": (
                    round(len(disturbed) / len(right), 4) if right else None
                ),
                "trigger_precision_errors_over_triggered": (
                    round(len(captured) / len(triggered), 4) if triggered else None
                ),
                "errors_captured_with_gold_in_fused_top2": len(reachable),
            }
        )
    return {
        "scope": scope,
        "population_size": len(members),
        "correct": len(right),
        "wrong": len(wrong),
        "margin_descriptives_blend_correct": _descriptives([r.margin_top2 for r in right]),
        "margin_descriptives_blend_wrong": _descriptives([r.margin_top2 for r in wrong]),
        "tradeoff_curve": curve,
    }


# ---------------------------------------------------------------------------
# Question 2 -- the ceiling, per error class
# ---------------------------------------------------------------------------


def error_class(replay: SampleReplay) -> str:
    """Mutually exclusive residual-error channel, in priority order.

    * ``absent-from-kb`` -- no content facet in the snapshot carries the gold
      intent, so no retrieval-side change can reach it.
    * ``retain-override-loss`` -- gold IS the fused TOP-1 label, but
      retain-primary fired and the evidence contact was never dispatched, so
      the frozen core never saw the gold-bearing exemplars. The retrieval was
      RIGHT and the ``(1 - alpha) = 0.55`` protect-direct constant discarded
      it. Reachable by a trigger that is allowed to override retain-primary;
      NOT reachable by a dispatch-scoped trigger.
    * ``intrinsic`` -- gold is the fused TOP-1 label AND the evidence contact
      dispatched: the core saw gold-first evidence and still answered wrong.
      Retrieval did everything available to it.
    * ``confusable-sibling`` -- gold IS in the fused label set at position 2
      or 3: a sibling intent out-scored it. THIS is the class a contrastive
      supply is designed for.
    * ``recall-limited`` -- the nearest gold-bearing facet sits outside the
      frozen ``top_k = 5`` recall window; retrieval never sees gold.
    * ``admission-limited`` -- gold IS inside the recall window but never
      reaches the fused label set (percept admission at ``tau``, the
      ``top_m`` truncation, or the ``top_l = 3`` target budget dropped it).

    ``retain-override-loss`` is split out from ``intrinsic`` deliberately:
    calling a sample "intrinsic" when the core was never shown the evidence
    would attribute a control-plane loss to the frozen model.
    """

    if replay.gold_facet_position is None:
        return "absent-from-kb"
    if replay.gold_fused_rank == 1:
        return "intrinsic" if replay.dispatched else "retain-override-loss"
    if replay.gold_fused_rank in (2, 3):
        return "confusable-sibling"
    if replay.gold_facet_position > FROZEN_TOP_K:
        return "recall-limited"
    return "admission-limited"


def composite_trigger_analysis(
    replays: Mapping[str, SampleReplay],
    *,
    cos_margin_grid: Sequence[float] = (0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 1.0),
) -> dict[str, object]:
    """The trigger family that the degenerate fused-score margin forces.

    Because the fused-score margin is effectively binary (see
    :func:`trigger_analysis`: any threshold in ``[0.02, 0.90]`` selects the
    same set, namely "more than one task target was supplied"), a usable E-A
    trigger needs a graded signal and a disagreement gate. Both are
    runtime-legal -- they read only the sample's own query vector, the frozen
    snapshot, and the direct answer's own parsed label:

    * the COSINE margin ``cos1 - cos2`` between the two sides' best admitted
      supporting facets, which the fused normalization squashes away;
    * the DISAGREEMENT gate: fire only when the direct answer's own label is
      NOT the retrieval's top-1 target. When they agree there is no
      confusion to resolve, and firing would put a correct, cheap,
      one-contact trajectory at risk for nothing.
    """

    members = list(replays.values())
    rows = []
    for gate in (False, True):
        for threshold in cos_margin_grid:
            triggered = [
                r
                for r in members
                if len(r.fused_ranked) >= 2
                and r.cos_margin <= threshold + 1e-9
                and (not gate or not r.direct_agrees_with_fused_top1)
            ]
            captured = [r for r in triggered if not r.correct]
            disturbed = [r for r in triggered if r.correct]
            reachable = [
                r
                for r in captured
                if r.gold_fused_rank is not None and r.gold_fused_rank <= 2
            ]
            disturbed_gold_outside = [
                r
                for r in disturbed
                if r.gold_fused_rank is None or r.gold_fused_rank > 2
            ]
            extra_contacts = sum(1 for r in triggered if not r.dispatched)
            rows.append(
                {
                    "disagreement_gate": gate,
                    "cos_margin_threshold": threshold,
                    "triggered": len(triggered),
                    "trigger_rate": round(len(triggered) / len(members), 4),
                    "errors_captured": len(captured),
                    "theoretically_reachable_gold_in_pair": len(reachable),
                    "correct_samples_disturbed": len(disturbed),
                    "disturbed_with_gold_outside_the_pair": len(disturbed_gold_outside),
                    "extra_frozen_core_contacts": extra_contacts,
                }
            )
    return {
        "signal": (
            "cos_margin = cos1 - cos2 over the two sides' best PERCEPT-ADMITTED supporting "
            "facets, optionally gated on the direct answer's own label disagreeing with the "
            "retrieval top-1. Both quantities are already computed by the frozen controller "
            "before the retain/dispatch decision; no gold, no future turn, no second model"
        ),
        "rows": rows,
    }


def ceiling_table(replays: Mapping[str, SampleReplay]) -> dict[str, object]:
    """Where gold sits in the fused label list, per error class and per
    dispatch state -- the NECESSARY condition for a contrastive supply."""

    errors = [r for r in replays.values() if not r.correct]
    rows: dict[str, dict[str, object]] = {}
    for replay in errors:
        name = error_class(replay)
        row = rows.setdefault(
            name,
            {
                "errors": 0,
                "retained": 0,
                "dispatched": 0,
                "gold_in_fused_top1": 0,
                "gold_in_fused_top2": 0,
                "gold_in_fused_top3": 0,
                "gold_not_in_fused_set": 0,
                "gold_facet_positions": [],
            },
        )
        row["errors"] += 1
        row["dispatched" if replay.dispatched else "retained"] += 1
        rank = replay.gold_fused_rank
        if rank is None:
            row["gold_not_in_fused_set"] += 1
        else:
            if rank <= 1:
                row["gold_in_fused_top1"] += 1
            if rank <= 2:
                row["gold_in_fused_top2"] += 1
            if rank <= 3:
                row["gold_in_fused_top3"] += 1
        if replay.gold_facet_position is not None:
            row["gold_facet_positions"].append(replay.gold_facet_position)

    for row in rows.values():
        positions = sorted(row.pop("gold_facet_positions"))
        row["gold_facet_position_median"] = (
            statistics.median(positions) if positions else None
        )
        row["gold_facet_position_max"] = positions[-1] if positions else None

    totals = {
        "errors": len(errors),
        "retained": sum(1 for r in errors if not r.dispatched),
        "dispatched": sum(1 for r in errors if r.dispatched),
        "gold_in_fused_top1": sum(
            1 for r in errors if r.gold_fused_rank is not None and r.gold_fused_rank <= 1
        ),
        "gold_in_fused_top2": sum(
            1 for r in errors if r.gold_fused_rank is not None and r.gold_fused_rank <= 2
        ),
        "gold_in_fused_top3": sum(
            1 for r in errors if r.gold_fused_rank is not None and r.gold_fused_rank <= 3
        ),
        "gold_not_in_fused_set": sum(1 for r in errors if r.gold_fused_rank is None),
    }
    return {
        "what_this_is": (
            "the NECESSARY (never sufficient) condition for CONTRAST-FEWSHOT: gold must be "
            "inside the contrast pair for a two-way contrastive supply to be able to select "
            "it. It is silent on what the frozen core would answer given that supply"
        ),
        "per_class": rows,
        "totals": totals,
    }


# ---------------------------------------------------------------------------
# Question 3 -- exemplar availability per side
# ---------------------------------------------------------------------------


def exemplar_availability(
    *,
    population: CellPopulation,
    replays: Mapping[str, SampleReplay],
    bundle: SnapshotBundle,
    margin_threshold: float,
) -> dict[str, object]:
    """For every sample the trigger selects, how many NEAR exemplars exist on
    each side of the fused top-2 pair?

    Three availability tiers are reported, weakest condition last:

    * ``supplied_now`` -- how many values of that side the FROZEN fuser
      actually put in front of the core (bounded by ``c = 2`` and by the
      ``top_m = 5`` admitted window);
    * ``near_at_tau`` -- how many of that side's content facets clear the
      frozen percept-admission threshold ``tau = 0.65`` against this
      sample's own flown query vector, ignoring the ``top_m`` truncation;
    * ``in_kb`` -- how many values that side has in the snapshot at all.
    """

    import numpy as np

    triggered = [
        r
        for r in replays.values()
        if r.margin_top2 <= margin_threshold + 1e-9 and len(r.fused_ranked) >= 2
    ]
    per_side_supplied: list[int] = []
    per_side_near: list[int] = []
    per_side_in_kb: list[int] = []
    top3_cosines: list[float] = []
    pairs_with_n_available = {n: 0 for n in EXEMPLAR_N_GRID}
    for replay in triggered:
        cosines = _COSINE_CACHE[(population.pin.population_id, replay.sample_id)]
        side_counts_near = []
        for target, _score in replay.fused_ranked[:2]:
            indices = bundle.facet_indices_by_target.get(target)
            if indices is None or len(indices) == 0:
                side_near = 0
                side_top3: list[float] = []
            else:
                side_cos = np.sort(np.asarray(cosines)[indices])[::-1]
                side_near = int((side_cos >= FROZEN_FUSE.tau).sum())
                side_top3 = [float(value) for value in side_cos[:3]]
            per_side_supplied.append(replay.supplied_per_target.get(target, 0))
            per_side_near.append(side_near)
            per_side_in_kb.append(len(bundle.values_by_target.get(target, ())))
            top3_cosines.extend(round(value, 4) for value in side_top3)
            side_counts_near.append(side_near)
        for n in EXEMPLAR_N_GRID:
            if side_counts_near and min(side_counts_near) >= n:
                pairs_with_n_available[n] += 1

    def summarize(values: Sequence[int]) -> dict[str, object]:
        if not values:
            return {"n": 0}
        ordered = sorted(values)
        return {
            "n": len(ordered),
            "min": ordered[0],
            "p10": ordered[min(len(ordered) - 1, len(ordered) // 10)],
            "median": statistics.median(ordered),
            "max": ordered[-1],
            "sides_with_at_least_2": sum(1 for value in ordered if value >= 2),
            "sides_with_at_least_3": sum(1 for value in ordered if value >= 3),
        }

    return {
        "margin_threshold": margin_threshold,
        "triggered_pairs": len(triggered),
        "per_side_supplied_now_by_the_frozen_fuser": summarize(per_side_supplied),
        "per_side_near_exemplars_at_tau_0_65": summarize(per_side_near),
        "per_side_values_in_kb": summarize(per_side_in_kb),
        "pairs_where_BOTH_sides_have_n_near_exemplars": {
            f"n_{n}": pairs_with_n_available[n] for n in EXEMPLAR_N_GRID
        },
        "note": (
            "``in_kb`` is a property of the snapshot, not of the query: the smallest TRAIN "
            "intent in this snapshot carries 4 values and the median carries 128, so an "
            "n = 2..4 per-side budget is never blocked by the KB itself. The binding "
            "constraint is NEARNESS at tau, and the frozen fuser's own c = 2 / top_m = 5 "
            "window, not availability"
        ),
    }


# ---------------------------------------------------------------------------
# Question 4 -- risk accounting for already-correct samples
# ---------------------------------------------------------------------------


def risk_accounting(
    replays: Mapping[str, SampleReplay], *, margin_threshold: float
) -> dict[str, object]:
    """What the offline record CAN and CANNOT say about disturbing a
    correct sample that the trigger would select."""

    triggered_correct = [
        r
        for r in replays.values()
        if r.correct and r.margin_top2 <= margin_threshold + 1e-9
    ]
    retained = [r for r in triggered_correct if not r.dispatched]
    dispatched = [r for r in triggered_correct if r.dispatched]
    gold_top1 = [r for r in triggered_correct if r.gold_fused_rank == 1]
    gold_top2 = [
        r
        for r in triggered_correct
        if r.gold_fused_rank is not None and r.gold_fused_rank <= 2
    ]
    gold_outside = [
        r
        for r in triggered_correct
        if r.gold_fused_rank is None or r.gold_fused_rank > 2
    ]
    worst_case = [r for r in gold_outside if not r.dispatched]
    survives_gate = [
        r for r in triggered_correct if not r.direct_agrees_with_fused_top1
    ]
    worst_case_after_gate = [
        r for r in worst_case if not r.direct_agrees_with_fused_top1
    ]
    return {
        "margin_threshold": margin_threshold,
        "triggered_correct_samples": len(triggered_correct),
        "of_which_retained_primary": len(retained),
        "of_which_dispatched": len(dispatched),
        "gold_is_the_fused_top1": len(gold_top1),
        "gold_inside_the_contrast_pair": len(gold_top2),
        "gold_OUTSIDE_the_contrast_pair": len(gold_outside),
        "WORST_CASE_retained_correct_with_gold_outside_the_pair": len(worst_case),
        "still_triggered_after_the_disagreement_gate": len(survives_gate),
        "WORST_CASE_after_the_disagreement_gate": len(worst_case_after_gate),
        "gold_outside_sample_ids": sorted(r.sample_id for r in gold_outside)[:20],
        "known_offline": (
            "on a RETAINED correct sample the final answer today is the logged direct-decode "
            "response, which is correct by construction; forcing a contrastive evidence "
            "dispatch replaces a KNOWN-correct answer with an evidence-conditioned answer "
            "that is NOT knowable offline. That is the whole of the retained-side risk and it "
            "is why the dispatch-only trigger scope carries zero retained-side risk by "
            "construction"
        ),
        "cannot_be_known_offline": (
            "on a DISPATCHED correct sample the contrast render changes the evidence prompt, "
            "so the frozen core's answer to it is unknowable without a model contact. The "
            "offline record can only report the structural protection: a contrast render "
            "keeps BOTH sides of the pair visible, so whenever gold is inside the pair the "
            "correct exemplars remain in front of the core, and the direct answer remains in "
            "the trajectory as the blend anchor. Where gold is OUTSIDE the pair the render "
            "removes gold-bearing exemplars that the flat top-3 supply carried, and that is a "
            "REAL, counted, unquantifiable-offline risk"
        ),
    }


# ---------------------------------------------------------------------------
# Question 5 -- the registered prediction
# ---------------------------------------------------------------------------


def registered_prediction(
    *,
    primary: Mapping[str, SampleReplay],
    replication: Mapping[str, SampleReplay],
    cos_margin_threshold: float,
    exemplar_n: int,
    scope: str,
    disagreement_gate: bool,
) -> dict[str, object]:
    """A projected ledger for a possible E-A round 1 on DEV-100.

    The trigger is the COSINE margin, not the briefed fused-score margin:
    :func:`trigger_analysis` proves the latter bimodal, so a prediction
    computed on it would be a prediction about "how many targets were
    supplied" rather than about confusability.

    The conversion band's OPTIMISTIC anchor is the sealed DEV-500 dispatched
    subgroup, where the evidence contact converted direct-decode failures at
    62.31% (W->C 78 / C->W 0 over n = 130). The band is discounted because
    the E-A population is strictly harder than that subgroup: every triggered
    error is a case the frozen core ALREADY saw the gold-bearing exemplars
    for (gold is inside the fused set) and still answered wrong -- the
    exemplars were present but unorganized. So the pessimistic edge assumes
    the render buys nothing beyond noise and the central estimate assumes it
    recovers about a third of the reachable set.
    """

    def scoped(replays: Mapping[str, SampleReplay]) -> list[SampleReplay]:
        if scope == "dispatched":
            return [r for r in replays.values() if r.dispatched]
        return list(replays.values())

    def ledger(replays: Mapping[str, SampleReplay], population_size: int) -> dict[str, object]:
        members = scoped(replays)
        triggered = [
            r
            for r in members
            if len(r.fused_ranked) >= 2
            and r.cos_margin <= cos_margin_threshold + 1e-9
            and (not disagreement_gate or not r.direct_agrees_with_fused_top1)
        ]
        captured = [r for r in triggered if not r.correct]
        reachable = [
            r for r in captured if r.gold_fused_rank is not None and r.gold_fused_rank <= 2
        ]
        disturbed = [r for r in triggered if r.correct]
        disturbed_gold_outside = [
            r
            for r in disturbed
            if r.gold_fused_rank is None or r.gold_fused_rank > 2
        ]
        baseline_correct = sum(1 for r in replays.values() if r.correct)
        bands = {}
        for name, conversion, loss in (
            ("pessimistic", 0.00, 0.10),
            ("central", 0.33, 0.05),
            ("optimistic", 0.62, 0.00),
        ):
            gained = round(len(reachable) * conversion)
            lost = round(len(disturbed_gold_outside) * loss)
            bands[name] = {
                "assumed_conversion_on_the_reachable_set": conversion,
                "assumed_loss_rate_on_disturbed_gold_outside_pair": loss,
                "projected_wrong_to_correct": gained,
                "projected_correct_to_wrong": lost,
                "projected_correct_count": baseline_correct + gained - lost,
                "projected_accuracy": round(
                    (baseline_correct + gained - lost) / population_size, 4
                ),
            }
        return {
            "population_size": population_size,
            "sealed_baseline_correct": baseline_correct,
            "sealed_baseline_accuracy": round(baseline_correct / population_size, 4),
            "triggered": len(triggered),
            "extra_frozen_core_contacts": sum(1 for r in triggered if not r.dispatched),
            "errors_captured": len(captured),
            "theoretically_reachable_errors_gold_in_pair": len(reachable),
            "correct_samples_disturbed": len(disturbed),
            "disturbed_with_gold_outside_the_pair": len(disturbed_gold_outside),
            "conversion_bands": bands,
            "absolute_bounds": {
                "note": (
                    "not a band: the arithmetic extremes, where every reachable error "
                    "converts or every disturbed correct sample breaks"
                ),
                "best_case_correct_count": baseline_correct + len(reachable),
                "worst_case_correct_count": baseline_correct - len(disturbed),
            },
        }

    return {
        "status": "REGISTERED PREDICTION -- design input only; no round is authorized by it",
        "recommended_knobs": {
            "trigger_signal": "cosine margin cos1 - cos2 over the pair's best admitted facets",
            "cos_margin_threshold": cos_margin_threshold,
            "exemplars_per_side_n": exemplar_n,
            "trigger_scope": scope,
            "disagreement_gate": disagreement_gate,
            "pair_size": 2,
            "everything_else": "byte-equal to the frozen cell",
        },
        "why_not_the_briefed_signal": (
            "the briefed fused-score top-2 margin is bimodal -- every threshold in "
            "[0.10, 0.90] selects the identical set -- so it encodes how many targets were "
            "supplied, not how confusable they are; see trigger_analysis and the "
            "degeneracy_finding note"
        ),
        "evaluability_caveat": (
            "the whole DEV-100 credible band sits inside or barely outside the documented "
            "+/- 2 per 100 direct-decode byte-variance channel, so an E-A round cannot be "
            "evaluated on DEV-100; a read would have to be at the 400-sample tier or larger"
        ),
        "optimistic_anchor": (
            "the sealed DEV-500 dispatched subgroup: BLEND 62.31% vs M0 2.31%, W->C 78 / "
            "C->W 0 over n = 130 (docs/readiness/2026-08-24-dev500-confirmatory-verdict.md)"
        ),
        "confusable_difficulty_discount": (
            "every triggered error already had the gold-bearing exemplars in its supply and "
            "was answered wrong anyway, so E-A's population is strictly harder than the "
            "dispatched subgroup that anchors 62%; the central band therefore assumes ~1/3 "
            "conversion and the pessimistic band assumes zero"
        ),
        "standing_negative_control": (
            "DEV-500 ABL-RANDICL: random exemplars cost -5.5 pp [-9.5, -1.5]. E-A must be "
            "distinguished from it BY CONSTRUCTION -- same retrieved content, different "
            "organization -- and a flown E-A arm that changes the exemplar SOURCE would be "
            "testing ABL-RANDICL again, not E-A"
        ),
        "dev100_projection": ledger(primary, len(primary)),
        "dev500_new400_replication_projection": ledger(replication, len(replication)),
        "what_would_falsify_it": (
            "a flown E-A arm whose W->C on the triggered reachable set is 0 while its C->W on "
            "the disturbed set is positive falsifies the central band; a flown arm at or "
            "below the sealed baseline falsifies the design"
        ),
    }


# ---------------------------------------------------------------------------
# The analysis
# ---------------------------------------------------------------------------


def analyse(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """Run the whole pre-analysis. Contacts nothing."""

    attempts = ra.arm_offline_guard()

    bundle = load_snapshot_bundle(data_root=data_root, repo_root=repo_root)
    populations = d5.load_populations(repo_root)

    cells: dict[str, CellPopulation] = {}
    replays: dict[str, dict[str, SampleReplay]] = {}
    gates: dict[str, object] = {}
    for pin in CELL_PINS:
        cell = load_cell_population(
            pin=pin,
            bundle=bundle,
            populations=populations,
            data_root=data_root,
            repo_root=repo_root,
        )
        cells[pin.population_id] = cell
        cell_replays, gate = replay_population(cell, bundle)
        replays[pin.population_id] = cell_replays
        gates[pin.population_id] = gate

    primary = replays["DEV-100-ROUND4"]
    replicate = replays["DEV-100-ROUND5"]
    new400 = replays["DEV-500-NEW400"]

    # The fused-margin threshold used ONLY for the exemplar-availability and
    # risk passes, where the widest (all multi-target) trigger set is wanted.
    recommended_threshold = 0.25

    report: dict[str, object] = {
        "schema": SCHEMA,
        "exposure_row_id": EXPOSURE_ROW_ID,
        "tier": "ITERATION-TIER DESIGN INPUT -- selects no knob, authorizes no flight",
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
            "proof_shape": (
                "socket.socket.connect / connect_ex / socket.create_connection were replaced "
                "with counting refusers BEFORE the first input was opened; a nonzero counter "
                "would have raised. No server-log byte-identity claim is made because a "
                "concurrent flight may hold the resident decoder unit"
            ),
        },
        "frozen_cell": {
            "config": FROZEN_POLICY_CONFIG_RELPATH,
            "alpha": FROZEN_ALPHA,
            "tau": FROZEN_FUSE.tau,
            "top_k_per_dimension": FROZEN_TOP_K,
            "fusion": {"m": FROZEN_FUSE.m, "c": FROZEN_FUSE.c, "l": FROZEN_FUSE.top_l},
            "rank_weights": {
                "w_cos": FROZEN_WEIGHTS.w_cos,
                "w_prior": FROZEN_WEIGHTS.w_prior,
                "w_agree": FROZEN_WEIGHTS.w_agree,
            },
        },
        "sources": {
            pin.population_id: {
                "run_dir": str(cells[pin.population_id].run_dir),
                "samples": len(cells[pin.population_id].sample_ids),
                "artifact_sha256_measured_at_read_time": dict(
                    cells[pin.population_id].artifact_hashes
                ),
                "committed_report": pin.report_relpath,
            }
            for pin in CELL_PINS
        },
        "snapshot": {
            "snapshot_sha256": bundle.snapshot_sha256,
            "content_facet_npz_sha256": bundle.npz_sha256,
            "content_facets": len(bundle.facet_ids),
            "label_identities": len(bundle.label_targets),
            "distinct_task_targets": len(bundle.values_by_target),
            "value_vectors": "SEALED (never loaded)",
        },
        "fidelity_gates": gates,
        "q1_trigger": {
            "signal": (
                "margin = p1 - p2 over the fused label distribution folded onto task "
                "targets, where p is _fused_label_scores normalized across the supplied "
                "targets. Computed by the controller BEFORE the retain/dispatch decision on "
                "every sample, from the sample's own query vector and the frozen snapshot -- "
                "no gold, no future turn, no second answering model. Runtime-legal"
            ),
            "boundary_case": (
                "a sample whose supply carries only ONE task target has no second label; its "
                "margin is defined as p1 - 0 = 1.0, the maximally UNambiguous value, so it is "
                "never triggered by a threshold below 1.0"
            ),
            "DEV-100-ROUND4": {
                scope: trigger_analysis(primary, scope=scope)
                for scope in ("all", "dispatched")
            },
            "DEV-100-ROUND5-replicate": {
                scope: trigger_analysis(replicate, scope=scope)
                for scope in ("all", "dispatched")
            },
            "DEV-500-NEW400": {
                scope: trigger_analysis(new400, scope=scope)
                for scope in ("all", "dispatched")
            },
            "degeneracy_finding": (
                "the fused-score margin is BIMODAL, not graded: a sample whose supply "
                "carries one target scores exactly 1.0 and a sample whose supply carries two "
                "or three scores near 0, because the ranker's score is an affine map of the "
                "cosine (w_prior mass is zero on every content facet and the agreement term "
                "is a constant 1/dims_total) which the fused normalization then squashes "
                "toward uniform. Every threshold in [0.02, 0.90] therefore selects the SAME "
                "set. The graded, non-degenerate replacement is the cosine margin -- see "
                "composite_trigger"
            ),
            "composite_trigger": {
                "DEV-100-ROUND4": composite_trigger_analysis(primary),
                "DEV-100-ROUND5-replicate": composite_trigger_analysis(replicate),
                "DEV-500-NEW400": composite_trigger_analysis(new400),
            },
        },
        "q2_ceiling": {
            "DEV-100-ROUND4": ceiling_table(primary),
            "DEV-100-ROUND5-replicate": ceiling_table(replicate),
            "DEV-500-NEW400": ceiling_table(new400),
        },
        "q3_exemplar_availability": {
            "DEV-100-ROUND4": exemplar_availability(
                population=cells["DEV-100-ROUND4"],
                replays=primary,
                bundle=bundle,
                margin_threshold=recommended_threshold,
            ),
            "DEV-500-NEW400": exemplar_availability(
                population=cells["DEV-500-NEW400"],
                replays=new400,
                bundle=bundle,
                margin_threshold=recommended_threshold,
            ),
        },
        "q4_risk_accounting": {
            "DEV-100-ROUND4": risk_accounting(
                primary, margin_threshold=recommended_threshold
            ),
            "DEV-500-NEW400": risk_accounting(
                new400, margin_threshold=recommended_threshold
            ),
        },
        "q5_registered_prediction": registered_prediction(
            primary=primary,
            replication=new400,
            cos_margin_threshold=RECOMMENDED_COS_MARGIN,
            exemplar_n=RECOMMENDED_EXEMPLARS_PER_SIDE,
            scope=RECOMMENDED_SCOPE,
            disagreement_gate=RECOMMENDED_DISAGREEMENT_GATE,
        ),
    }
    report["per_sample"] = {
        population_id: [
            {
                "sample_id": replay.sample_id,
                "correct": replay.correct,
                "contacts": replay.logged_contacts,
                "retain_primary": replay.retain_primary,
                "supply_empty": replay.supply_empty,
                "dispatched": replay.dispatched,
                "direct_target": replay.direct_target,
                "gold_target": replay.gold_target,
                "margin_top2": round(replay.margin_top2, 4),
                "cos_top1": (
                    None if replay.cos_top1 is None else round(replay.cos_top1, 4)
                ),
                "cos_top2": (
                    None if replay.cos_top2 is None else round(replay.cos_top2, 4)
                ),
                "cos_margin": round(replay.cos_margin, 4),
                "direct_agrees_with_fused_top1": replay.direct_agrees_with_fused_top1,
                "fused_ranked": [
                    [target, round(score, 4)] for target, score in replay.fused_ranked
                ],
                "gold_fused_rank": replay.gold_fused_rank,
                "gold_facet_position": replay.gold_facet_position,
                "error_class": None if replay.correct else error_class(replay),
            }
            for replay in sorted(
                replays[population_id].values(), key=lambda item: item.sample_id
            )
        ]
        for population_id in ("DEV-100-ROUND4",)
    }
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    report = analyse(repo_root=args.repo_root, data_root=args.data_root)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


__all__ = [
    "CELL_PINS",
    "EXPOSURE_ROW_ID",
    "FROZEN_ALPHA",
    "FROZEN_FUSE",
    "FROZEN_TOP_K",
    "FROZEN_WEIGHTS",
    "RECALL_FIDELITY_PROBES",
    "RECOMMENDED_COS_MARGIN",
    "RECOMMENDED_DISAGREEMENT_GATE",
    "RECOMMENDED_EXEMPLARS_PER_SIDE",
    "RECOMMENDED_SCOPE",
    "SCHEMA",
    "SampleReplay",
    "analyse",
    "ceiling_table",
    "composite_trigger_analysis",
    "error_class",
    "exemplar_availability",
    "load_cell_population",
    "load_snapshot_bundle",
    "main",
    "registered_prediction",
    "replay_population",
    "risk_accounting",
    "trigger_analysis",
    "vectorised_recall",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
