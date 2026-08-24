"""Model-free damage-channel dissection of the SEALED DEV-100 rounds.

Exposure row ``SAEA-SN-MF-DEV100-DAMAGE-CHANNEL-ANALYSIS`` (registered
before any computation): zero frozen-core contacts, zero embedding-tool
contacts, zero HTTP requests of any kind. Everything this module reads is
already landed on disk -- the three sealed round reports, their per-sample
score files, the round-2 durable trace / outputs / query vectors, the pinned
TRAIN knowledge snapshot, and its landed content-facet vector NPZ. Nothing
is embedded, encoded, decoded, generated, or requested; the resident decoder
service is never contacted.

Why this exists
---------------
Three sealed DEV-100 rounds left a stable, byte-identical 11-sample
``correct -> wrong`` (C->W) damage list that neither ``tau`` (round 1, inert
on [0.5, 0.65]) nor ``alpha`` (round 2, 0.60 -> 0.55, gained 2 samples and
healed none of the 11) moved. The remaining registered dev-legal knobs are
``prior_source``, ``top_k_per_dimension``, and the rank weights
(``w_cos``/``w_prior``/``w_agree``). Rather than spend a round guessing, this
module replays the recall/rank/fuse/blend arithmetic offline, from the
already-logged inputs, using :mod:`..rails.kb_policy`'s OWN pure functions --
so a round-3 knob can be chosen by evidence.

Replay fidelity
---------------
The flown controller's supply decision is a deterministic function of
(query vector, facet vectors, snapshot, knobs). All four are landed, so the
supply stage is replayed EXACTLY, not approximated: :func:`replay_supply`
calls :func:`..rails.kb_policy.multidim_recall`, the registered ranker
factory, and the registered fuser factory, and :func:`fidelity_report`
asserts the recomputed ``selected_value_ids`` equal the value ids the
round-2 SUPPLY trace channel recorded, sample for sample.

Honesty about what a counterfactual can and cannot say
------------------------------------------------------
Changing a knob changes what is SUPPLIED; the frozen core's answer to a
changed evidence block is NOT knowable without a model contact. Every
counterfactual outcome is therefore reported in exactly one of three
buckets, and no counterfactual accuracy is ever asserted as a measured
flight result:

``revert_to_direct``
    the pre-evidence blend's unique winner is the direct-decode label, so
    the controller's retain-primary path fires and the DIRECT-decode
    response -- which is logged -- becomes final. Outcome KNOWN offline.
``dispatch_same_supply``
    an evidence contact still dispatches and the selected value ids are
    byte-identical to the flown ones, so the evidence prompt is
    byte-identical and the logged evidence response stands. Outcome KNOWN
    offline.
``dispatch_changed_supply``
    an evidence contact dispatches with a DIFFERENT evidence block. Outcome
    UNKNOWN offline; counted, never scored.

Diagnostics that use numpy
--------------------------
:func:`correct_label_reachability` needs the cosine of the query against ALL
11,514 content facets (to report where the gold-bearing facet sits in the
full recall ordering, which decides whether a wider ``top_k`` could ever
reach it). That is the same arithmetic as
:func:`..rails.kb_policy._cosine`, evaluated with numpy for tractability;
:func:`_assert_cosine_agreement` cross-checks the vectorised values against
``kb_policy``'s own scalar implementation on every facet the policy actually
recalled, so the diagnostic is pinned to the policy, not to numpy.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..rails import kb_policy as kb
from ..rails.knowledge import KnowledgeSnapshot, QueryState, RankResult
from ..reproduction.slurp_scoring import parse_slu_response, score_slu

SCHEMA = "saea-dev100-damage-channel-analysis-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-DEV100-DAMAGE-CHANNEL-ANALYSIS"

SNAPSHOT_RELPATH = "knowledge/slurp/saea-kb-distmodel-v1/size-full/snapshot.json"
SNAPSHOT_SHA256 = "e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57"
EMBEDDING_RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-kb-size-full-embeddings.json"
RUN_ID = "SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN"

ROUND2_ATTEMPT_ID = "attempt-20260824T153842Z-dev100r2"
ROUND2_ARM = "BLEND_ROUND2"
TRACE_BASENAME = f"{RUN_ID}.trace.jsonl"
RUNTIME_USE_SUFFIX = "/agent-loop/runtime-use"
SUPPLY_SUFFIX = "/agent-loop/supply"

# The three sealed round reports, relative to the study repo root.
ROUND_REPORT_RELPATHS = {
    0: "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round0/round0-report.json",
    1: "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round1/round1-report.json",
    2: "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round2/round2-report.json",
}

# Round-2 flown knobs (round2-report.json ``round2_knobs``).
ROUND2_WEIGHTS = kb.RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2)
ROUND2_FUSE = kb.FuseKnobs(tau=0.65, m=5, c=2, top_l=3)
ROUND2_ALPHA = 0.55
ROUND2_TOP_K = 5


class AnalysisError(RuntimeError):
    """Raised when a landed input does not match its pinned identity."""


# ---------------------------------------------------------------------------
# Landed inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LandedInputs:
    """Every byte this analysis consumes, already on disk."""

    snapshot: KnowledgeSnapshot
    snapshot_sha256: str
    facet_vector_ids: tuple[str, ...]
    facet_vector_matrix: object  # numpy.ndarray (n_facets, dim)
    facet_vectors: Callable[[str], Mapping[str, Sequence[float]]]
    facet_npz_sha256: str
    query_vectors: Mapping[str, tuple[float, ...]]
    direct_texts: Mapping[str, str]
    evidence_texts: Mapping[str, str]
    logged_supply: Mapping[str, tuple[str, ...]]
    logged_winner_labels: Mapping[str, str | None]
    gold_by_sample: Mapping[str, object]
    round_scores: Mapping[str, Mapping[str, Mapping[str, object]]]
    round_reports: Mapping[int, Mapping[str, object]]
    label_targets: Mapping[str, str]
    label_texts: Mapping[str, str]
    values_by_id: Mapping[str, object]
    content_facet_target: Mapping[str, str]

    @property
    def sample_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.query_vectors))


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_landed_inputs(*, data_root: Path, repo_root: Path) -> LandedInputs:
    """Load and identity-check every landed input (module docstring)."""

    import numpy as np

    snapshot_path = Path(data_root) / SNAPSHOT_RELPATH
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    snapshot_sha256 = snapshot.content_hash()
    if snapshot_sha256 != SNAPSHOT_SHA256:
        raise AnalysisError(
            f"knowledge snapshot hashes to {snapshot_sha256}, not the pinned {SNAPSHOT_SHA256}"
        )

    receipt = json.loads((Path(repo_root) / EMBEDDING_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    facet_block = receipt["vectors"]["content_facets"]
    npz_path = snapshot_path.parent / facet_block["file"]
    measured_npz = _sha256_file(npz_path)
    if measured_npz != facet_block["sha256"]:
        raise AnalysisError("content-facet NPZ hash mismatch vs the landed embedding receipt")
    npz = np.load(npz_path)
    facet_ids = tuple(str(value) for value in npz["ids"])
    matrix = npz["vectors"]
    if matrix.shape[0] != len(facet_ids):
        raise AnalysisError(f"unexpected facet vector shape {matrix.shape}")
    # VALUE VECTORS STAY SEALED: receipt["vectors"]["values"] is never opened.
    table = {facet_id: {"content": tuple(matrix[i].tolist())} for i, facet_id in enumerate(facet_ids)}

    def facet_vectors(facet_id: str) -> Mapping[str, Sequence[float]]:
        return table.get(facet_id, {})

    run_dir = Path(data_root) / "runs" / RUN_ID / ROUND2_ATTEMPT_ID
    query_vectors = _load_query_vectors(run_dir)
    direct_texts, evidence_texts, logged_supply = _load_trace(run_dir)
    logged_winner_labels = _load_winner_labels(run_dir)

    round_scores = json.loads((run_dir / "round2-scores.json").read_text(encoding="utf-8"))
    round_reports = {
        index: json.loads((Path(repo_root) / relpath).read_text(encoding="utf-8"))
        for index, relpath in ROUND_REPORT_RELPATHS.items()
    }

    label_targets = kb._label_identities(snapshot)
    label_texts = {
        facet.facet_id: facet.representation
        for facet in snapshot.facets
        if facet.facet_id in label_targets
    }
    values_by_id = {value.value_id: value for value in snapshot.values}
    content_facet_target: dict[str, str] = {}
    for value in snapshot.values:
        if value.task_target is None:
            continue
        for facet_id in value.associated_facet_ids:
            content_facet_target.setdefault(facet_id, value.task_target)

    gold_by_sample = _load_gold(data_root=data_root, repo_root=repo_root, sample_ids=set(query_vectors))

    return LandedInputs(
        snapshot=snapshot,
        snapshot_sha256=snapshot_sha256,
        facet_vector_ids=facet_ids,
        facet_vector_matrix=matrix,
        facet_vectors=facet_vectors,
        facet_npz_sha256=measured_npz,
        query_vectors=query_vectors,
        direct_texts=direct_texts,
        evidence_texts=evidence_texts,
        logged_supply=logged_supply,
        logged_winner_labels=logged_winner_labels,
        gold_by_sample=gold_by_sample,
        round_scores=round_scores,
        round_reports=round_reports,
        label_targets=label_targets,
        label_texts=label_texts,
        values_by_id=values_by_id,
        content_facet_target=content_facet_target,
    )


def _load_query_vectors(run_dir: Path) -> dict[str, tuple[float, ...]]:
    vectors: dict[str, tuple[float, ...]] = {}
    with (run_dir / "query-vectors.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            contact_id = record["contact_id"]
            if not contact_id.startswith("query:"):
                continue
            vectors[contact_id.split("query:", 1)[1]] = tuple(float(v) for v in record["values"])
    return vectors


def _load_trace(run_dir: Path) -> tuple[dict[str, str], dict[str, str], dict[str, tuple[str, ...]]]:
    """Direct/evidence response TEXTS and the flown supply, from the durable trace."""

    texts_by_sha: dict[str, str] = {}
    contacts_by_sample: dict[str, list[Mapping[str, object]]] = {}
    supply_by_sample: dict[str, tuple[str, ...]] = {}
    with (run_dir / TRACE_BASENAME).open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            channel = record["channel"]
            payload = record["payload"]
            record_id = record["record_id"]
            if channel == "MODEL_RESPONSE":
                # The USE channel's per-contact ``response_sha256`` is the hash
                # of the response TEXT, which MODEL_RESPONSE records under
                # ``response_text_sha256`` (its own ``response_sha256`` covers
                # the whole response object, envelope included).
                texts_by_sha[payload["response_text_sha256"]] = payload["text"]
            elif channel == "USE" and record_id.endswith(RUNTIME_USE_SUFFIX):
                sample_id = record_id[: -len(RUNTIME_USE_SUFFIX)]
                contacts_by_sample[sample_id] = list(payload["use_contacts"])
            elif channel == "SUPPLY" and record_id.endswith(SUPPLY_SUFFIX):
                sample_id = record_id[: -len(SUPPLY_SUFFIX)]
                supply_by_sample[sample_id] = tuple(payload["supply_final_visible_value_ids"])

    direct: dict[str, str] = {}
    evidence: dict[str, str] = {}
    for sample_id, contacts in contacts_by_sample.items():
        for contact in contacts:
            contact_id = contact["plan"]["contact_id"]
            text = texts_by_sha.get(contact["response_sha256"])
            if text is None:
                raise AnalysisError(f"no logged response text for {sample_id} {contact_id}")
            if contact_id == "direct-decode":
                direct[sample_id] = text
            elif contact_id == "evidence-decode":
                evidence[sample_id] = text
    return direct, evidence, supply_by_sample


def _load_winner_labels(run_dir: Path) -> dict[str, str | None]:
    winners: dict[str, str | None] = {}
    with (run_dir / "round2-outputs.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            winners[record["sample_id"]] = record.get("winner_label")
    return winners


def _load_gold(*, data_root: Path, repo_root: Path, sample_ids: set[str]):
    """Gold for the 100 already-scored DEV-100 samples.

    Gold was lawfully opened at each of the three round seals; this analysis
    is strictly scoring-side over the SAME samples and discloses nothing the
    sealed reports do not already carry.
    """

    from ..data.lock import load_lock, umbrella_lock_path
    from ..data.slurp import load_slurp_split

    lock = load_lock(umbrella_lock_path(Path(repo_root)))
    records = load_slurp_split(lock, Path(data_root), "devel")
    gold = {record.sample_id: record for record in records if record.sample_id in sample_ids}
    missing = sample_ids - set(gold)
    if missing:
        raise AnalysisError(f"{len(missing)} DEV-100 sample ids absent from the devel split")
    return gold


# ---------------------------------------------------------------------------
# Scoring helpers (post-hoc only)
# ---------------------------------------------------------------------------


def score_response(gold_record, response_text: str) -> dict[str, object]:
    """``scenario_action_exact`` for one logged response, via the repository's
    own scorer -- the same call the round launchers make post-seal."""

    scenario, action, entities, parsed = parse_slu_response(response_text)
    result = score_slu(
        gold_scenario=gold_record.scenario,
        gold_action=gold_record.action,
        gold_entities=gold_record.entities,
        predicted_scenario=scenario,
        predicted_action=action,
        predicted_entities=tuple(entities),
    )
    return {
        "correct": result.scenario_action_exact == 1.0,
        "parsed": parsed,
        "predicted_scenario": scenario,
        "predicted_action": action,
    }


def gold_label_facet(gold_record, label_targets: Mapping[str, str]) -> str | None:
    """The label facet whose ``task_target`` is the sample's gold intent."""

    target = f"{gold_record.scenario}_{gold_record.action}"
    for facet_id, facet_target in label_targets.items():
        if facet_target == target:
            return facet_id
    return None


def predicted_label_facet(
    response_text: str, label_targets: Mapping[str, str]
) -> str | None:
    """The label facet a response's OWN parsed scenario/action names.

    This is the label identity the controller's ``default_label_normalizer``
    is meant to recover but structurally cannot (see
    :func:`normalizer_liveness`): gold is never consulted here -- only the
    model's own answer text.
    """

    scenario, action, _entities, parsed = parse_slu_response(response_text)
    if not parsed or scenario is None or action is None:
        return None
    target = f"{scenario}_{action}"
    for facet_id, facet_target in label_targets.items():
        if facet_target == target:
            return facet_id
    return None


# ---------------------------------------------------------------------------
# Supply replay (exact) and blend replay
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SupplyReplay:
    """One sample's recall/rank/fuse replay at one knob setting."""

    sample_id: str
    recall_scores: Mapping[str, Mapping[str, float]]
    rank_result: RankResult
    selected_value_ids: tuple[str, ...]
    supporting_facet_ids: tuple[str, ...]
    admitted_facet_ids: tuple[str, ...]
    top_m_facet_ids: tuple[str, ...]
    dims_total: int


def _query_state(sample_id: str, snapshot_sha256: str) -> QueryState:
    """A minimal, contract-valid QueryState for the pure stages.

    The ranker and fuser consult ``query_state`` only for its content hash
    (binding) and its ``retrieved_value_ids`` (the already-visible set,
    empty at the acquire step of a fresh trajectory), so a locally
    constructed state replays the acquire step faithfully. The flown state's
    own hash is NOT reproduced here and no hash-bound claim is made from it.
    """

    return QueryState(
        query_id=f"{RUN_ID}:{sample_id}:step0",
        query_sample_id=sample_id,
        speech_packet_id=sample_id,
        speech_packet_sha256="0" * 64,
        use_split_identity_hash="0" * 64,
        loop_step=0,
        visible_facet_ids=(),
        agent_state_ids=(),
        retrieved_value_ids=(),
    ).validate()


def replay_supply(
    inputs: LandedInputs,
    sample_id: str,
    *,
    weights: kb.RankWeights = ROUND2_WEIGHTS,
    knobs: kb.FuseKnobs = ROUND2_FUSE,
    top_k: int = ROUND2_TOP_K,
    recall_scores: Mapping[str, Mapping[str, float]] | None = None,
) -> SupplyReplay:
    """Replay recall -> rank -> fuse through ``kb_policy``'s own functions."""

    if recall_scores is None:
        recall_scores = kb.multidim_recall(
            inputs.snapshot,
            {"content": inputs.query_vectors[sample_id]},
            inputs.facet_vectors,
            top_k,
        )
    ranker = kb.rank_wcos_prior_agree_factory(weights)
    fuser = kb.fuse_supplyfilter_factory(knobs)
    state = _query_state(sample_id, inputs.snapshot_sha256)
    rank_result = ranker(
        snapshot_sha256=inputs.snapshot_sha256,
        query_state=state,
        recall_scores=recall_scores,
    )
    decision = fuser(
        snapshot=inputs.snapshot,
        snapshot_sha256=inputs.snapshot_sha256,
        query_state=state,
        rank_result=rank_result,
        recall_scores=recall_scores,
    )
    top_m = tuple(candidate.facet_id for candidate in rank_result.candidates[: knobs.m])
    admitted = tuple(
        facet_id
        for facet_id in top_m
        if _max_cosine(recall_scores.get(facet_id, {})) >= knobs.tau
    )
    dims_total = len({dim for scores in recall_scores.values() for dim in scores})
    return SupplyReplay(
        sample_id=sample_id,
        recall_scores=recall_scores,
        rank_result=rank_result,
        selected_value_ids=tuple(decision.selected_value_ids),
        supporting_facet_ids=tuple(decision.supporting_facet_ids),
        admitted_facet_ids=admitted,
        top_m_facet_ids=top_m,
        dims_total=dims_total,
    )


def _max_cosine(dim_scores: Mapping[str, float]) -> float:
    values = [
        score for dim, score in dim_scores.items() if dim not in kb.PRIOR_MASS_DIMENSIONS
    ]
    return max(values) if values else 0.0


def _max_prior(dim_scores: Mapping[str, float]) -> float:
    values = [score for dim, score in dim_scores.items() if dim in kb.PRIOR_MASS_DIMENSIONS]
    return max(values) if values else 0.0


@dataclass(frozen=True)
class BlendReplay:
    """The alpha-blend head's own arithmetic at one (supply, direct, alpha)."""

    fused_label_scores: Mapping[str, float]
    blended: Mapping[str, float]
    best_labels: tuple[str, ...]
    direct_label: str | None
    retain_primary: bool
    winner_margin: float


def replay_blend(
    inputs: LandedInputs,
    supply: SupplyReplay,
    *,
    direct_label: str | None,
    alpha: float,
) -> BlendReplay:
    """Replay the blend head through ``kb_policy``'s own functions."""

    fused = kb._fused_label_scores(
        inputs.label_targets,
        inputs.values_by_id,
        supply.selected_value_ids,
        supply.rank_result,
    )
    blended = kb._blend_scores(inputs.label_targets, fused, direct_label, alpha)
    best = kb._argmax_labels(blended)
    retain = best == (direct_label,) and direct_label is not None
    ordered = sorted(blended.values(), reverse=True)
    margin = (ordered[0] - ordered[1]) if len(ordered) > 1 else ordered[0]
    return BlendReplay(
        fused_label_scores=fused,
        blended=blended,
        best_labels=best,
        direct_label=direct_label,
        retain_primary=retain,
        winner_margin=margin,
    )


# ---------------------------------------------------------------------------
# Fidelity gate
# ---------------------------------------------------------------------------


def fidelity_report(
    inputs: LandedInputs, replays: Mapping[str, SupplyReplay]
) -> dict[str, object]:
    """Assert the offline supply replay equals the flown SUPPLY trace."""

    matches = 0
    mismatches: list[dict[str, object]] = []
    winner_matches = 0
    winner_mismatches: list[dict[str, object]] = []
    for sample_id in inputs.sample_ids:
        replay = replays[sample_id]
        logged = tuple(sorted(inputs.logged_supply[sample_id]))
        recomputed = tuple(sorted(replay.selected_value_ids))
        if logged == recomputed:
            matches += 1
        else:
            mismatches.append(
                {"sample_id": sample_id, "logged": logged, "recomputed": recomputed}
            )
        blend = replay_blend(
            inputs,
            replay,
            direct_label=kb.default_label_normalizer(
                inputs.direct_texts[sample_id], inputs.label_texts
            ),
            alpha=ROUND2_ALPHA,
        )
        logged_winner = inputs.logged_winner_labels.get(sample_id)
        # The flown winner is the evidence answer when it lands inside
        # best_labels, else best_labels[0] (KbAlphaBlendController).
        evidence_label = kb.default_label_normalizer(
            inputs.evidence_texts[sample_id], inputs.label_texts
        )
        expected = (
            evidence_label
            if evidence_label in blend.best_labels
            else (blend.best_labels[0] if blend.best_labels else None)
        )
        if expected == logged_winner:
            winner_matches += 1
        else:
            winner_mismatches.append(
                {"sample_id": sample_id, "logged": logged_winner, "recomputed": expected}
            )
    return {
        "samples": len(inputs.sample_ids),
        "supply_exact_matches": matches,
        "supply_mismatches": mismatches[:10],
        "supply_gate_passed": matches == len(inputs.sample_ids),
        "winner_label_matches": winner_matches,
        "winner_label_mismatches": winner_mismatches[:10],
        "winner_gate_passed": winner_matches == len(inputs.sample_ids),
    }


# ---------------------------------------------------------------------------
# Structural diagnostics
# ---------------------------------------------------------------------------


def normalizer_liveness(inputs: LandedInputs) -> dict[str, object]:
    """Is the controller's direct-label term ever live?

    ``KbAlphaBlendController`` blends ``(1 - alpha)`` onto the label facet
    ``default_label_normalizer`` recovers from the direct-decode text. The
    normalizer matches a label facet's REPRESENTATION as a substring of the
    response. The snapshot's representations are prose sentences ("Intent
    'alarm_query' (scenario='alarm', action='query'); 130 TRAIN utterances
    ...") while the task contract's answers are compact JSON, so the match
    can never fire. This measures that directly, and measures how often the
    answer's OWN parsed scenario/action DOES name a snapshot label facet.
    """

    direct_matched = 0
    evidence_matched = 0
    direct_parsed_identity = 0
    evidence_parsed_identity = 0
    direct_swapped_identity = 0
    direct_unparsed = 0
    targets = set(inputs.label_targets.values())
    for sample_id in inputs.sample_ids:
        if kb.default_label_normalizer(inputs.direct_texts[sample_id], inputs.label_texts):
            direct_matched += 1
        if kb.default_label_normalizer(inputs.evidence_texts[sample_id], inputs.label_texts):
            evidence_matched += 1
        if predicted_label_facet(inputs.direct_texts[sample_id], inputs.label_targets):
            direct_parsed_identity += 1
        else:
            scenario, action, _entities, parsed = parse_slu_response(
                inputs.direct_texts[sample_id]
            )
            if not parsed or scenario is None or action is None:
                direct_unparsed += 1
            elif f"{action}_{scenario}" in targets:
                direct_swapped_identity += 1
        if predicted_label_facet(inputs.evidence_texts[sample_id], inputs.label_targets):
            evidence_parsed_identity += 1
    total = len(inputs.sample_ids)
    return {
        "samples": total,
        "direct_label_recovered_by_flown_normalizer": direct_matched,
        "evidence_label_recovered_by_flown_normalizer": evidence_matched,
        "direct_label_recoverable_from_own_parsed_answer": direct_parsed_identity,
        "evidence_label_recoverable_from_own_parsed_answer": evidence_parsed_identity,
        # Of the direct answers a scenario_action lookup does NOT resolve, how
        # many would resolve with the two fields exchanged (the answer names a
        # real TRAIN intent but in action_scenario order) -- a separate,
        # answer-format finding, not part of the repair measured here.
        "direct_label_recoverable_only_if_scenario_action_swapped": direct_swapped_identity,
        "direct_answers_unparsed_or_incomplete": direct_unparsed,
        "direct_term_ever_live": direct_matched > 0,
        "consequence": (
            "with the direct-label term dead on every sample the blend reduces to "
            "argmax(alpha * fused_label_scores), whose argmax is invariant in alpha; "
            "retain-primary can never fire, which is exactly what all three sealed "
            "rounds recorded (retain_primary_samples = 0)"
        ),
    }


def _assert_cosine_agreement(
    inputs: LandedInputs, sample_id: str, cosines, recall_scores
) -> None:
    """Pin the vectorised cosine to ``kb_policy._cosine`` on recalled facets."""

    index = {facet_id: i for i, facet_id in enumerate(inputs.facet_vector_ids)}
    query = inputs.query_vectors[sample_id]
    for facet_id, dim_scores in recall_scores.items():
        if "content" not in dim_scores:
            continue
        policy_value = kb._cosine(query, inputs.facet_vectors(facet_id)["content"])
        vector_value = float(cosines[index[facet_id]])
        if not math.isclose(policy_value, vector_value, rel_tol=1e-9, abs_tol=1e-9):
            raise AnalysisError(
                f"{sample_id}/{facet_id}: vectorised cosine {vector_value} disagrees with "
                f"kb_policy._cosine {policy_value}"
            )


def correct_label_reachability(
    inputs: LandedInputs, sample_id: str, replay: SupplyReplay
) -> dict[str, object]:
    """Where does the GOLD-bearing content facet sit in the recall ordering?

    Partitions a damaged sample into *reweight-addressable* (a gold-bearing
    facet is already inside the logged top-5, so a different weighting or
    fusion could promote it) versus *recall-limited* (no gold-bearing facet
    is in reach, so only wider recall or better keys could help). The full
    cosine ordering is reported too, which answers the ``top_k 5 -> 8``
    question exactly rather than by proxy.
    """

    import numpy as np

    gold = inputs.gold_by_sample[sample_id]
    gold_target = f"{gold.scenario}_{gold.action}"
    query = np.asarray(inputs.query_vectors[sample_id], dtype=np.float64)
    matrix = np.asarray(inputs.facet_vector_matrix, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1) * float(np.linalg.norm(query))
    with np.errstate(divide="ignore", invalid="ignore"):
        cosines = np.where(norms > 0.0, matrix @ query / norms, 0.0)
    _assert_cosine_agreement(inputs, sample_id, cosines, replay.recall_scores)

    order = np.argsort(-cosines, kind="stable")
    gold_positions: list[int] = []
    for rank_position, index in enumerate(order, start=1):
        facet_id = inputs.facet_vector_ids[int(index)]
        if inputs.content_facet_target.get(facet_id) == gold_target:
            gold_positions.append(rank_position)
            if len(gold_positions) >= 3:
                break
    best_position = gold_positions[0] if gold_positions else None
    best_cosine = (
        float(cosines[int(order[best_position - 1])]) if best_position is not None else None
    )

    recalled_content = {
        facet_id: scores["content"]
        for facet_id, scores in replay.recall_scores.items()
        if "content" in scores
    }
    in_top5 = any(
        inputs.content_facet_target.get(facet_id) == gold_target for facet_id in recalled_content
    )
    admitted_gold = any(
        inputs.content_facet_target.get(facet_id) == gold_target
        for facet_id in replay.admitted_facet_ids
    )
    supplied_gold = any(
        inputs.values_by_id[value_id].task_target == gold_target
        for value_id in replay.selected_value_ids
    )
    return {
        "gold_target": gold_target,
        "gold_facet_best_full_recall_position": best_position,
        "gold_facet_best_cosine": best_cosine,
        "gold_facet_next_positions": gold_positions[1:3],
        "gold_bearing_facet_in_logged_top5": in_top5,
        "gold_bearing_facet_admitted": admitted_gold,
        "gold_bearing_value_supplied": supplied_gold,
        "reachable_at_top_k": (
            best_position if best_position is not None and best_position <= 64 else None
        ),
        "partition": (
            "reweight_addressable"
            if in_top5
            else ("recall_limited" if best_position is not None else "absent_from_kb")
        ),
    }


# ---------------------------------------------------------------------------
# Counterfactual bucketing
# ---------------------------------------------------------------------------


@dataclass
class CounterfactualOutcome:
    sample_id: str
    bucket: str
    known_correct: bool | None
    detail: dict[str, object] = field(default_factory=dict)


def counterfactual(
    inputs: LandedInputs,
    sample_id: str,
    *,
    baseline: SupplyReplay,
    weights: kb.RankWeights,
    knobs: kb.FuseKnobs,
    alpha: float,
    top_k: int,
    use_repaired_normalizer: bool,
) -> CounterfactualOutcome:
    """One sample under one counterfactual knob setting, bucketed honestly."""

    recall = None
    if top_k == ROUND2_TOP_K:
        recall = baseline.recall_scores
    replay = replay_supply(
        inputs, sample_id, weights=weights, knobs=knobs, top_k=top_k, recall_scores=recall
    )
    if use_repaired_normalizer:
        direct_label = predicted_label_facet(inputs.direct_texts[sample_id], inputs.label_targets)
    else:
        direct_label = kb.default_label_normalizer(
            inputs.direct_texts[sample_id], inputs.label_texts
        )
    gold = inputs.gold_by_sample[sample_id]
    gold_target = f"{gold.scenario}_{gold.action}"
    gold_supplied = any(
        inputs.values_by_id[value_id].task_target == gold_target
        for value_id in replay.selected_value_ids
    )

    if not replay.selected_value_ids:
        # kb_policy stops before dispatching when fusion selects nothing.
        outcome = score_response(gold, inputs.direct_texts[sample_id])
        return CounterfactualOutcome(
            sample_id=sample_id,
            bucket="revert_to_direct",
            known_correct=bool(outcome["correct"]),
            detail={"reason": "fusion selected nothing", "gold_target_supplied": False},
        )

    blend = replay_blend(inputs, replay, direct_label=direct_label, alpha=alpha)
    if blend.retain_primary:
        outcome = score_response(gold, inputs.direct_texts[sample_id])
        return CounterfactualOutcome(
            sample_id=sample_id,
            bucket="revert_to_direct",
            known_correct=bool(outcome["correct"]),
            detail={
                "reason": "retain-primary: direct label uniquely wins the pre-evidence blend",
                "winner_margin": blend.winner_margin,
                "gold_target_supplied": gold_supplied,
            },
        )

    same_supply = tuple(sorted(replay.selected_value_ids)) == tuple(
        sorted(baseline.selected_value_ids)
    )
    if same_supply:
        outcome = score_response(gold, inputs.evidence_texts[sample_id])
        return CounterfactualOutcome(
            sample_id=sample_id,
            bucket="dispatch_same_supply",
            known_correct=bool(outcome["correct"]),
            detail={
                "best_labels": list(blend.best_labels),
                "gold_target_supplied": gold_supplied,
            },
        )
    return CounterfactualOutcome(
        sample_id=sample_id,
        bucket="dispatch_changed_supply",
        known_correct=None,
        detail={
            "baseline_supply": list(baseline.selected_value_ids),
            "counterfactual_supply": list(replay.selected_value_ids),
            "gold_target_supplied": gold_supplied,
        },
    )


KNOB_GRID: tuple[dict[str, object], ...] = (
    {
        "id": "baseline-round2",
        "note": "the flown round-2 setting, replayed (control)",
        "weights": ROUND2_WEIGHTS,
        "knobs": ROUND2_FUSE,
        "alpha": ROUND2_ALPHA,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": False,
    },
    {
        "id": "w_prior-zero",
        "note": "drop the TRAIN prior from the ranker (w_cos .5 / w_prior 0 / w_agree .2)",
        "weights": kb.RankWeights(w_cos=0.5, w_prior=0.0, w_agree=0.2),
        "knobs": ROUND2_FUSE,
        "alpha": ROUND2_ALPHA,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": False,
    },
    {
        "id": "w_agree-up-a",
        "note": "raise cross-dimension agreement (w_cos .5 / w_prior .1 / w_agree .4)",
        "weights": kb.RankWeights(w_cos=0.5, w_prior=0.1, w_agree=0.4),
        "knobs": ROUND2_FUSE,
        "alpha": ROUND2_ALPHA,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": False,
    },
    {
        "id": "w_agree-up-b",
        "note": "raise cross-dimension agreement (w_cos .4 / w_prior .2 / w_agree .4)",
        "weights": kb.RankWeights(w_cos=0.4, w_prior=0.2, w_agree=0.4),
        "knobs": ROUND2_FUSE,
        "alpha": ROUND2_ALPHA,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": False,
    },
    {
        "id": "alpha-050",
        "note": "shift the blend further toward the direct label (alpha .50)",
        "weights": ROUND2_WEIGHTS,
        "knobs": ROUND2_FUSE,
        "alpha": 0.50,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": False,
    },
    {
        "id": "alpha-045",
        "note": "shift the blend further toward the direct label (alpha .45)",
        "weights": ROUND2_WEIGHTS,
        "knobs": ROUND2_FUSE,
        "alpha": 0.45,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": False,
    },
    {
        "id": "top_k-8",
        "note": "widen per-dimension recall 5 -> 8 (supply side replayed exactly)",
        "weights": ROUND2_WEIGHTS,
        "knobs": ROUND2_FUSE,
        "alpha": ROUND2_ALPHA,
        "top_k": 8,
        "repaired_normalizer": False,
    },
    {
        "id": "top_k-8-and-m-8",
        "note": (
            "widen recall AND the fuser's top-m together (top_k 8, m 8) -- not a single "
            "registered knob; measured only to show what recall widening would need"
        ),
        "weights": ROUND2_WEIGHTS,
        "knobs": kb.FuseKnobs(tau=0.65, m=8, c=2, top_l=3),
        "alpha": ROUND2_ALPHA,
        "top_k": 8,
        "repaired_normalizer": False,
    },
    {
        "id": "top_l-4",
        "note": "raise the fuser's coverage floor l 3 -> 4 (a fusion knob, not a rank knob)",
        "weights": ROUND2_WEIGHTS,
        "knobs": kb.FuseKnobs(tau=0.65, m=5, c=2, top_l=4),
        "alpha": ROUND2_ALPHA,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": False,
    },
    {
        "id": "top_k-8-m-8-top_l-4",
        "note": "widen recall, top-m and the coverage floor together (three knobs at once)",
        "weights": ROUND2_WEIGHTS,
        "knobs": kb.FuseKnobs(tau=0.65, m=8, c=2, top_l=4),
        "alpha": ROUND2_ALPHA,
        "top_k": 8,
        "repaired_normalizer": False,
    },
    {
        "id": "label-identity-repair-alpha-055",
        "note": (
            "repair the dead direct-label term (recover the label facet from the answer's "
            "OWN parsed scenario/action instead of a prose-representation substring match), "
            "keeping every flown knob at its round-2 value"
        ),
        "weights": ROUND2_WEIGHTS,
        "knobs": ROUND2_FUSE,
        "alpha": ROUND2_ALPHA,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": True,
    },
    {
        "id": "label-identity-repair-alpha-060",
        "note": "the same repair at the round-0/1 alpha .60",
        "weights": ROUND2_WEIGHTS,
        "knobs": ROUND2_FUSE,
        "alpha": 0.60,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": True,
    },
    {
        "id": "label-identity-repair-alpha-050",
        "note": "the same repair at alpha .50",
        "weights": ROUND2_WEIGHTS,
        "knobs": ROUND2_FUSE,
        "alpha": 0.50,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": True,
    },
    # Below alpha .50 a fully-concentrated fused distribution (mass 1.0 on one
    # wrong label) stops out-scoring the direct term, so these positions expose
    # the repair's own damage/repair tradeoff curve.
    {
        "id": "label-identity-repair-alpha-045",
        "note": "the same repair at alpha .45",
        "weights": ROUND2_WEIGHTS,
        "knobs": ROUND2_FUSE,
        "alpha": 0.45,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": True,
    },
    {
        "id": "label-identity-repair-alpha-040",
        "note": "the same repair at alpha .40",
        "weights": ROUND2_WEIGHTS,
        "knobs": ROUND2_FUSE,
        "alpha": 0.40,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": True,
    },
    {
        "id": "label-identity-repair-alpha-030",
        "note": "the same repair at alpha .30",
        "weights": ROUND2_WEIGHTS,
        "knobs": ROUND2_FUSE,
        "alpha": 0.30,
        "top_k": ROUND2_TOP_K,
        "repaired_normalizer": True,
    },
)


# ---------------------------------------------------------------------------
# Top-level analysis
# ---------------------------------------------------------------------------


def analyse(*, data_root: Path, repo_root: Path) -> dict[str, object]:
    """The whole model-free dissection, as a JSON-ready mapping."""

    inputs = load_landed_inputs(data_root=data_root, repo_root=repo_root)
    sample_ids = inputs.sample_ids

    baseline: dict[str, SupplyReplay] = {
        sample_id: replay_supply(inputs, sample_id) for sample_id in sample_ids
    }
    fidelity = fidelity_report(inputs, baseline)
    if not fidelity["supply_gate_passed"]:
        raise AnalysisError(
            "supply replay does not reproduce the flown SUPPLY trace; the analysis is void"
        )

    report2 = inputs.round_reports[2]
    damaged = tuple(report2["correct_to_wrong_sample_ids"])
    repairs = tuple(report2["wrong_to_correct_sample_ids"])

    m0_rows = inputs.round_scores["M0_SEALED_ROUND0"]
    r2_rows = inputs.round_scores[ROUND2_ARM]

    dissection: dict[str, dict[str, object]] = {}
    for sample_id in tuple(damaged) + tuple(repairs):
        dissection[sample_id] = _dissect(inputs, sample_id, baseline[sample_id], m0_rows, r2_rows)

    grid: dict[str, object] = {}
    for setting in KNOB_GRID:
        grid[str(setting["id"])] = _run_setting(
            inputs, baseline, setting, damaged=damaged, repairs=repairs
        )

    partition = {
        "reweight_addressable": [
            sample_id
            for sample_id in damaged
            if dissection[sample_id]["reachability"]["partition"] == "reweight_addressable"
        ],
        "recall_limited": [
            sample_id
            for sample_id in damaged
            if dissection[sample_id]["reachability"]["partition"] == "recall_limited"
        ],
        "absent_from_kb": [
            sample_id
            for sample_id in damaged
            if dissection[sample_id]["reachability"]["partition"] == "absent_from_kb"
        ],
    }

    return {
        "schema": SCHEMA,
        "exposure_row_id": EXPOSURE_ROW_ID,
        "model_contacts": 0,
        "embedding_tool_contacts": 0,
        "provenance": {
            "snapshot_sha256": inputs.snapshot_sha256,
            "facet_vectors_npz_sha256": inputs.facet_npz_sha256,
            "value_vectors_loaded": False,
            "round2_attempt_id": ROUND2_ATTEMPT_ID,
            "samples": len(sample_ids),
            "round2_knobs": {
                "alpha": ROUND2_ALPHA,
                "tau": ROUND2_FUSE.tau,
                "m": ROUND2_FUSE.m,
                "c": ROUND2_FUSE.c,
                "l": ROUND2_FUSE.top_l,
                "top_k_per_dimension": ROUND2_TOP_K,
                "w_cos": ROUND2_WEIGHTS.w_cos,
                "w_prior": ROUND2_WEIGHTS.w_prior,
                "w_agree": ROUND2_WEIGHTS.w_agree,
            },
        },
        "fidelity": fidelity,
        "normalizer_liveness": normalizer_liveness(inputs),
        "geometry": _geometry(inputs, baseline),
        "damage_list": list(damaged),
        "repair_list": list(repairs),
        "dissection": dissection,
        "counterfactuals": grid,
        "partition_of_the_11": partition,
    }


def _dissect(
    inputs: LandedInputs,
    sample_id: str,
    replay: SupplyReplay,
    m0_rows: Mapping[str, Mapping[str, object]],
    r2_rows: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    gold = inputs.gold_by_sample[sample_id]
    direct_score = score_response(gold, inputs.direct_texts[sample_id])
    evidence_score = score_response(gold, inputs.evidence_texts[sample_id])
    blend = replay_blend(
        inputs,
        replay,
        direct_label=kb.default_label_normalizer(
            inputs.direct_texts[sample_id], inputs.label_texts
        ),
        alpha=ROUND2_ALPHA,
    )
    facet_score = {c.facet_id: c.score for c in replay.rank_result.candidates}
    ranked = [
        {
            "facet_id": candidate.facet_id,
            "rank_score": candidate.score,
            "max_cosine": _max_cosine(replay.recall_scores.get(candidate.facet_id, {})),
            "max_prior": _max_prior(replay.recall_scores.get(candidate.facet_id, {})),
            "agreement": len(replay.recall_scores.get(candidate.facet_id, {})) / replay.dims_total,
            "task_target": inputs.content_facet_target.get(candidate.facet_id),
            "in_top_m": candidate.facet_id in replay.top_m_facet_ids,
            "admitted": candidate.facet_id in replay.admitted_facet_ids,
            "supporting": candidate.facet_id in replay.supporting_facet_ids,
        }
        for candidate in replay.rank_result.candidates[:8]
    ]
    fused_nonzero = {
        label_id: value for label_id, value in blend.fused_label_scores.items() if value > 0.0
    }
    ordered_fused = sorted(fused_nonzero.items(), key=lambda kv: -kv[1])
    gold_facet = gold_label_facet(gold, inputs.label_targets)
    direct_facet = predicted_label_facet(inputs.direct_texts[sample_id], inputs.label_targets)
    winner = inputs.logged_winner_labels.get(sample_id)
    winner_blend = blend.blended.get(winner, 0.0) if winner else 0.0
    direct_blend = blend.blended.get(direct_facet, 0.0) if direct_facet else 0.0
    return {
        "m0_correct": bool(m0_rows[sample_id]["correct"]),
        "round2_correct": bool(r2_rows[sample_id]["correct"]),
        "gold_intent": f"{gold.scenario}_{gold.action}",
        "gold_label_facet": gold_facet,
        "direct_answer": {
            "scenario": direct_score["predicted_scenario"],
            "action": direct_score["predicted_action"],
            "correct": direct_score["correct"],
            "implied_label_facet": direct_facet,
        },
        "evidence_answer": {
            "scenario": evidence_score["predicted_scenario"],
            "action": evidence_score["predicted_action"],
            "correct": evidence_score["correct"],
        },
        "flown_winner_label": winner,
        "dims_total": replay.dims_total,
        "ranked_candidates": ranked,
        "admitted_facet_ids": list(replay.admitted_facet_ids),
        "selected_value_ids": list(replay.selected_value_ids),
        "supplied_targets": sorted(
            {
                str(inputs.values_by_id[value_id].task_target)
                for value_id in replay.selected_value_ids
            }
        ),
        "fused_label_scores": {label_id: value for label_id, value in ordered_fused},
        "direct_label_recovered_by_flown_normalizer": blend.direct_label,
        "blend_at_alpha_055": {
            "winner_label_score": winner_blend,
            "direct_implied_label_score": direct_blend,
            "margin_winner_over_direct": winner_blend - direct_blend,
            "retain_primary": blend.retain_primary,
        },
        "supply_carries_gold_target": any(
            inputs.values_by_id[value_id].task_target == f"{gold.scenario}_{gold.action}"
            for value_id in replay.selected_value_ids
        ),
        "reachability": correct_label_reachability(inputs, sample_id, replay),
        "top_facet_rank_score": facet_score.get(replay.rank_result.candidates[0].facet_id),
    }


def _geometry(inputs: LandedInputs, baseline: Mapping[str, SupplyReplay]) -> dict[str, object]:
    """Structural facts about the recall geometry that bound every knob."""

    multi_dim_facets = 0
    label_or_prior_in_top_m = 0
    dims_totals: dict[int, int] = {}
    min_admitted_cosine = 1.0
    max_prior_on_a_content_facet = 0.0
    rank_order_equals_cosine_order = True
    for sample_id, replay in baseline.items():
        content_by_rank = [
            candidate.facet_id
            for candidate in replay.rank_result.candidates
            if "content" in replay.recall_scores.get(candidate.facet_id, {})
        ]
        content_by_cosine = sorted(
            content_by_rank,
            key=lambda facet_id: (-replay.recall_scores[facet_id]["content"], facet_id),
        )
        if content_by_rank != content_by_cosine:
            rank_order_equals_cosine_order = False
        for facet_id in content_by_rank:
            max_prior_on_a_content_facet = max(
                max_prior_on_a_content_facet, _max_prior(replay.recall_scores[facet_id])
            )
        dims_totals[replay.dims_total] = dims_totals.get(replay.dims_total, 0) + 1
        for facet_id, scores in replay.recall_scores.items():
            if len(scores) > 1:
                multi_dim_facets += 1
        for facet_id in replay.top_m_facet_ids:
            scores = replay.recall_scores.get(facet_id, {})
            if not [dim for dim in scores if dim not in kb.PRIOR_MASS_DIMENSIONS]:
                label_or_prior_in_top_m += 1
        for facet_id in replay.admitted_facet_ids:
            min_admitted_cosine = min(
                min_admitted_cosine, _max_cosine(replay.recall_scores[facet_id])
            )
    return {
        "facets_recalled_under_more_than_one_dimension": multi_dim_facets,
        "agreement_is_constant_across_candidates": multi_dim_facets == 0,
        "dims_total_histogram": dims_totals,
        "label_or_prior_facets_inside_top_m": label_or_prior_in_top_m,
        "min_admitted_max_cosine": min_admitted_cosine,
        "max_prior_mass_on_a_content_facet": max_prior_on_a_content_facet,
        "content_facet_rank_order_equals_cosine_order": rank_order_equals_cosine_order,
        "consequence": (
            "every facet in this snapshot carries exactly one dimension, so the ranker's "
            "agreement term is the SAME constant 1/dims_total for every candidate -- w_agree "
            "cannot reorder candidates and therefore cannot change what is supplied; content "
            "facets carry zero prior mass, so w_prior cannot reorder them either; and the "
            "fuser's percept-admission test requires a cosine score, so label/prior facets can "
            "never be admitted, only crowd the top-m. The ranker's content ordering is therefore "
            "IDENTICALLY the cosine ordering for any weight vector with w_cos > 0: the rank-weight "
            "knob family cannot move a single supplied value on this split"
        ),
    }


def _run_setting(
    inputs: LandedInputs,
    baseline: Mapping[str, SupplyReplay],
    setting: Mapping[str, object],
    *,
    damaged: Sequence[str],
    repairs: Sequence[str],
) -> dict[str, object]:
    outcomes = {
        sample_id: counterfactual(
            inputs,
            sample_id,
            baseline=baseline[sample_id],
            weights=setting["weights"],  # type: ignore[arg-type]
            knobs=setting["knobs"],  # type: ignore[arg-type]
            alpha=float(setting["alpha"]),  # type: ignore[arg-type]
            top_k=int(setting["top_k"]),  # type: ignore[arg-type]
            use_repaired_normalizer=bool(setting["repaired_normalizer"]),
        )
        for sample_id in inputs.sample_ids
    }

    def summarise(ids: Sequence[str]) -> dict[str, object]:
        buckets: dict[str, int] = {}
        known_correct = 0
        known_wrong = 0
        unknown = 0
        flipped: list[str] = []
        gold_supplied = 0
        for sample_id in ids:
            outcome = outcomes[sample_id]
            buckets[outcome.bucket] = buckets.get(outcome.bucket, 0) + 1
            if outcome.detail.get("gold_target_supplied"):
                gold_supplied += 1
            if outcome.known_correct is None:
                unknown += 1
            elif outcome.known_correct:
                known_correct += 1
                flipped.append(sample_id)
            else:
                known_wrong += 1
        return {
            "n": len(ids),
            "buckets": buckets,
            "known_correct": known_correct,
            "known_wrong": known_wrong,
            "outcome_unknown_offline": unknown,
            "known_correct_ids": flipped,
            # A necessary (never sufficient) condition for evidence to repair a
            # sample: does the supplied evidence carry the gold task_target at all?
            "gold_target_supplied": gold_supplied,
        }

    r2_rows = inputs.round_scores[ROUND2_ARM]
    projected_correct = 0
    projected_unknown = 0
    for sample_id in inputs.sample_ids:
        outcome = outcomes[sample_id]
        if outcome.known_correct is None:
            projected_unknown += 1
            if bool(r2_rows[sample_id]["correct"]):
                projected_correct += 1  # carried forward, flagged by projected_unknown
        elif outcome.known_correct:
            projected_correct += 1
    changed = [
        sample_id
        for sample_id in inputs.sample_ids
        if outcomes[sample_id].bucket != "dispatch_same_supply"
    ]
    group_of = {sample_id: "damage" for sample_id in damaged}
    group_of.update({sample_id: "repair" for sample_id in repairs})
    ledger = {
        sample_id: {
            "group": group_of.get(sample_id, "neither"),
            "bucket": outcomes[sample_id].bucket,
            "round2_correct": bool(r2_rows[sample_id]["correct"]),
            "projected_correct": outcomes[sample_id].known_correct,
        }
        for sample_id in inputs.sample_ids
    }
    movers = {
        "wrong_to_correct": sorted(
            sample_id
            for sample_id, row in ledger.items()
            if row["projected_correct"] is True and not row["round2_correct"]
        ),
        "correct_to_wrong": sorted(
            sample_id
            for sample_id, row in ledger.items()
            if row["projected_correct"] is False and row["round2_correct"]
        ),
    }
    return {
        "note": setting["note"],
        "weights": {
            "w_cos": setting["weights"].w_cos,  # type: ignore[union-attr]
            "w_prior": setting["weights"].w_prior,  # type: ignore[union-attr]
            "w_agree": setting["weights"].w_agree,  # type: ignore[union-attr]
        },
        "alpha": setting["alpha"],
        "top_k_per_dimension": setting["top_k"],
        "repaired_normalizer": setting["repaired_normalizer"],
        "damage_group": summarise(damaged),
        "repair_group": summarise(repairs),
        "whole_split": {
            "samples_whose_trajectory_changed": len(changed),
            "changed_sample_ids": changed[:40],
            "projected_correct_with_unknowns_carried_at_round2": projected_correct,
            "samples_with_unknown_offline_outcome": projected_unknown,
            # Only an EXACT projection when nothing is unknown offline: every
            # trajectory then ends on a response this analysis has already read.
            "projected_correct_exact": (projected_correct if projected_unknown == 0 else None),
        },
        "per_sample_ledger": ledger,
        "projected_movement_vs_round2": movers,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = analyse(data_root=args.data_root, repo_root=args.repo_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {args.out}")
    print(json.dumps(report["fidelity"], indent=1))
    print(json.dumps(report["normalizer_liveness"], indent=1))
    print(json.dumps(report["geometry"], indent=1))
    return 0


__all__ = [
    "AnalysisError",
    "BlendReplay",
    "CounterfactualOutcome",
    "EXPOSURE_ROW_ID",
    "KNOB_GRID",
    "LandedInputs",
    "SCHEMA",
    "SupplyReplay",
    "analyse",
    "correct_label_reachability",
    "counterfactual",
    "fidelity_report",
    "gold_label_facet",
    "load_landed_inputs",
    "main",
    "normalizer_liveness",
    "predicted_label_facet",
    "replay_blend",
    "replay_supply",
    "score_response",
]


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
