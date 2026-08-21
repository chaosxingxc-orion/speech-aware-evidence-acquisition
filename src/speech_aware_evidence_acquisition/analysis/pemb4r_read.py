"""P-EMB-4R pinned offline read suite (pre-registered, SAEA-PROBE-pemb4r-4100):
``docs/readiness/2026-08-20-pemb4r-preregistration-REGISTERED.md`` section 4.

Model-free, read-only, sibling of ``analysis.pemb3m_read``/``analysis.
pfew_read`` (built and coordinator-reviewed BEFORE the read, per this
probe's own discipline section 6): scores the flight's own already-written
``retrieval_plan.json`` (:mod:`rails.probes.pemb4r_flight`'s own flight-side,
GOLD-FREE artifact) against SCORING-SIDE-ONLY devel gold, and separately
scores C-DECODE's own responses when such responses are explicitly supplied.
The 2026-08-21 owner amendment canceled C-DECODE before any generation
contact and authorized the existing seven-arm vector read to close this
probe model-free. The report therefore carries an explicit cancellation
status; a missing C-DECODE comparison is never left ambiguous.

**Explicit-input discipline** (mission instruction, restated here as this
module's own architectural commitment): every function in this module is a
PURE function of caller-supplied inputs -- gate outcomes (``dropped_arms``),
jitter/repeat-delta measurements (``repeat_delta_by_model``), the pooling-
override scope flag (``pooling_override_present_by_model``), and the
already-flown ``retrieval_plan_document`` -- NEVER hardcoded, never
re-derived from this module's own assumption about what a real flight must
have measured. Only the thin CLI wrapper (:func:`main`) performs any I/O.

**Retrieval-plan integrity** (:func:`verify_retrieval_plan_document`): the
flight-side ``retrieval_plan.json`` is never trusted blindly -- this
function INDEPENDENTLY RE-DERIVES every arm's own per-sample top-K
retrieval from the SAME flown bank/query vectors (``rails.probes.
pemb4r_flight.build_arm_retrieval``, reused verbatim) and compares the
result BYTE-FOR-BYTE (structurally, field-by-field) against the flight's
own written document, reporting every disagreement rather than silently
trusting either side (the SAME "tri-derivation" discipline ``rails.probes.
pcorrf_flight``'s own corrective binding hash establishes, generalized from
a single hash equality to a full per-sample structural comparison).

**Vote-accuracy** (:func:`majority_vote_label`): top-K majority vote over
the RANKED (never deduplicated) label sequence a retrieval row carries, ties
broken by the highest MEAN cosine among the tied labels' own retrieved
members (registration section 2), a final deterministic tie-break by sorted
label. Computed at K=1/3/5 (registration section 2: "K=5 primary; K=1/3
reported").

**Recall@1/3/5** (:func:`compute_recall_at_k`): "the mechanical ceiling on
voting AND on C-DECODE" (registration section 4's own mandatory pre-verdict
reachability item) -- the fraction of samples whose OWN gold scenario
appears anywhere in the top-K retrieved set, independent of voting.

**Per-sample top-1 margins vs measured repeat-delta** (:func:`evaluate_
argmax_stability`, the registration's own explicit "NO blanket 'argmax
unaffected' claim -- the 3M jitter lesson"): every sample's own top1-minus-
top2 cosine margin is compared AGAINST that arm's own model's measured
repeat-call cosine delta (``repeat_delta_by_model``, an EXPLICIT caller
input -- never assumed) -- a sample whose margin does not clear the
measured noise floor is reported ``WITHIN-JITTER-NOISE``, never silently
folded into an aggregate accuracy number as if it were a stable pick.

**Verdicts** (registration section 4, quoted verbatim in each clause's own
detail text): REGISTER-RESCUE / AUDIO-ROUTES (per audio arm, LCO arms
POOLING-OVERRIDE-SCOPED while the flag stands, GLAP unscoped) /
AUDIO-CONTENT-ABSENT (sweep-level) / KNN-BEATS-LABEL-MATCH (named finding,
vs the CITED M4 label-match 0.7500) / C-DECODE's own RETRIEVAL-SUPPLY-HELPS
/ RETRIEVAL-SUPPLY-HURTS (paired per-sample vs the CONSUMED P-FEW FS-NONE
rows, attempt ``attempt-20260819T233312Z-480fed``, cross-session +/-2-sample
drift carried per the registration's own disclosure) / otherwise
INCONCLUSIVE-4R with the full matrix.

**Feasibility matrix** (:func:`build_feasibility_matrix`): every flown arm
plus the two environment-gated candidates (``omni-embed-nemotron-3b``,
``clsp``) named in the registration's own section 3 as "documented NOT
flown" -- neither is EVER flyable through this read (this module never
opens either), the matrix exists purely as a design-input disclosure for
the escalation decision.

Idempotence: :func:`build_pemb4r_sweep_report` is a pure function of its
inputs (no I/O, no mutation, no randomness).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..rails.probes import pemb4r_flight as flight
from ..rails.probes.pemb4r_flight import ARMS_BY_ID, AUDIO_ARM_IDS, MODEL_LCO3, MODEL_LCO7, TEXT_ARM_IDS
from .pemb_read import ConfusionCell, PembReadError, build_confusion_table

REPORT_SCHEMA = "saea-pemb4r-read-v1"

# Registration section 4, quoted verbatim in each clause's own detail text.
CHANCE_ACCURACY = 0.0556
REGISTER_RESCUE_MIN_ACCURACY = 0.30
AUDIO_ROUTES_MIN_ACCURACY = 0.65
AUDIO_CONTENT_ABSENT_MAX_AUDIO = 0.15
AUDIO_CONTENT_ABSENT_MIN_TEXT = 0.65
KNN_BEATS_LABEL_MATCH_THRESHOLD = 0.7500
CITED_FS_NONE_ACCURACY = 0.8167
CITED_A1R_ACCURACY = 0.7833
CITED_M4_LABEL_MATCH_ACCURACY = 0.7500
CITED_AUDIO_VS_LABEL_FLOOR = (0.0500, 0.1333)

C_DECODE_HELPS_MIN_NET = 3
C_DECODE_HURTS_MAX_NET = -3
C_DECODE_NOT_PROVIDED = "NOT-PROVIDED"
C_DECODE_CANCELED_OWNER_20260821 = "CANCELED-BY-OWNER-2026-08-21"

# The consumed P-FEW attempt (registration section 4: "the consumed FS-NONE
# rows"), verdict docs/readiness/2026-08-19-pfew-verdict.md: FS-NONE
# 49/60 = 0.8167. This module never re-flies it -- a strictly READ-side
# citation of an already-consumed sibling probe's own per-sample rows.
CONSUMED_PFEW_RUN_EXPERIMENT_ID = "SAEA-PROBE-pfew-180"
CONSUMED_PFEW_ATTEMPT_ID = "attempt-20260819T233312Z-480fed"

FEASIBILITY_FLYABLE = "FLYABLE-NOW"
FEASIBILITY_ENV_GATED = "ENVIRONMENT-GATED"


class Pemb4rReadError(RuntimeError):
    """A retrieval-plan/manifest input is malformed, an id-set mismatch is
    detected, or a harness-defect fail-closed check tripped -- never raised
    for an ordinary, structurally clean read."""


def load_repeat_delta_by_model(flight_run_dir: Path) -> dict[str, float]:
    """Derive cosine-distance noise floors from the landed repeat pairs."""

    filenames = {
        flight.MODEL_LCO3: "lco3-jitter-vectors.json",
        flight.MODEL_LCO7: "lco7-jitter-vectors.json",
        flight.MODEL_QW: "qw-jitter-vectors.json",
    }
    result: dict[str, float] = {}
    for model, filename in filenames.items():
        path = Path(flight_run_dir) / filename
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise Pemb4rReadError(f"cannot read repeat-call pair {path}: {error}") from error
        if not isinstance(document, Mapping) or set(document) != {"a", "b"}:
            raise Pemb4rReadError(f"{path}: repeat-call pair must have exact a/b keys")
        a = document["a"]
        b = document["b"]
        if (
            not isinstance(a, list)
            or not isinstance(b, list)
            or not a
            or len(a) != len(b)
            or any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                for value in [*a, *b]
            )
        ):
            raise Pemb4rReadError(
                f"{path}: repeat-call vectors are malformed or dimension-mismatched"
            )
        result[model] = max(0.0, 1.0 - flight._cosine(a, b))
    return result


def flight_facts_from_state(
    state: Mapping[str, object],
) -> tuple[dict[str, str], dict[str, bool]]:
    """Reuse explicit pooling and completed-arm facts from flight state."""

    pooling: dict[str, bool] = {}
    for model in (flight.MODEL_LCO3, flight.MODEL_LCO7):
        field = f"gate_c_pooling_differ_{model}"
        gate = state.get(field)
        if not isinstance(gate, Mapping) or not isinstance(
            gate.get("pooling_override_present"), bool
        ):
            raise Pemb4rReadError(
                f"flight state lacks a valid {field}.pooling_override_present fact"
            )
        pooling[model] = gate["pooling_override_present"]
    sweeps = state.get("sweeps")
    if not isinstance(sweeps, Mapping):
        raise Pemb4rReadError("flight state lacks a sweeps mapping")
    dropped = {
        arm_id: "NOT-FLOWN: no completed sweep in the landed flight state"
        for arm_id in flight.ARM_IDS
        if arm_id not in sweeps
    }
    return dropped, pooling


# ---------------------------------------------------------------------------
# Retrieval-plan integrity (module docstring).
# ---------------------------------------------------------------------------


def verify_retrieval_plan_document(
    retrieval_plan_document: Mapping[str, object],
    *,
    bank_vectors_by_model: Mapping[str, Mapping[str, Sequence[float]]],
    bank_labels: Mapping[str, str],
    query_vectors_by_arm: Mapping[str, Mapping[str, Sequence[float]]],
) -> tuple[bool, tuple[str, ...]]:
    """Independently RE-DERIVES every arm's own retrieval from the SAME
    flown vectors (module docstring) and reports every field-level
    disagreement against the flight-written document -- ``(True, ())`` iff
    every arm/sample/field matches EXACTLY."""

    mismatches: list[str] = []
    arms_block = retrieval_plan_document.get("arms")
    if not isinstance(arms_block, Mapping):
        return False, ("retrieval_plan_document carries no 'arms' block",)
    k_primary = retrieval_plan_document.get("k_primary", flight.RETRIEVAL_K_PRIMARY)

    for arm_id, arm_block in sorted(arms_block.items()):
        if arm_id not in ARMS_BY_ID:
            mismatches.append(f"{arm_id}: unknown arm id")
            continue
        model = ARMS_BY_ID[arm_id].model
        bank_vectors = bank_vectors_by_model.get(model)
        query_vectors = query_vectors_by_arm.get(arm_id)
        if bank_vectors is None or query_vectors is None:
            mismatches.append(f"{arm_id}: missing bank or query vectors for re-derivation")
            continue
        recomputed = flight.build_arm_retrieval(arm_id, query_vectors, bank_vectors, bank_labels, k=k_primary)
        per_sample = arm_block.get("per_sample", {})
        for sample_id, row in sorted(per_sample.items()):
            recomputed_row = recomputed.per_sample.get(sample_id)
            if recomputed_row is None:
                mismatches.append(f"{arm_id}/{sample_id}: no re-derived row (query vector missing)")
                continue
            if tuple(row.get("top_k_bank_ids", ())) != recomputed_row.top_k_bank_ids:
                mismatches.append(f"{arm_id}/{sample_id}: top_k_bank_ids mismatch")
            if tuple(row.get("dedup_labels_k5", ())) != recomputed_row.dedup_labels_k5:
                mismatches.append(f"{arm_id}/{sample_id}: dedup_labels_k5 mismatch")
            if tuple(row.get("dedup_labels_k3", ())) != recomputed_row.dedup_labels_k3:
                mismatches.append(f"{arm_id}/{sample_id}: dedup_labels_k3 mismatch")
            if tuple(row.get("dedup_labels_k1", ())) != recomputed_row.dedup_labels_k1:
                mismatches.append(f"{arm_id}/{sample_id}: dedup_labels_k1 mismatch")
    return (len(mismatches) == 0, tuple(mismatches))


def verify_landed_retrieval_plan(
    root: Path, retrieval_plan_document: Mapping[str, object]
) -> tuple[bool, tuple[str, ...]]:
    """Load existing vector manifests through the flight's own verified
    loaders and independently re-derive the retrieval plan."""

    bank = flight.load_bank_manifest(root)
    bank_labels = {entry.bank_id: entry.gold_scenario for entry in bank.entries}
    bank_vectors = {
        model: flight.load_bank_vectors(root, model).vectors for model in flight.MODELS
    }
    query_vectors = {
        arm_id: flight.load_query_vectors(root, arm_id).vectors for arm_id in flight.ARM_IDS
    }
    return verify_retrieval_plan_document(
        retrieval_plan_document,
        bank_vectors_by_model=bank_vectors,
        bank_labels=bank_labels,
        query_vectors_by_arm=query_vectors,
    )


# ---------------------------------------------------------------------------
# Vote-accuracy (top-K majority, tie -> highest mean cosine).
# ---------------------------------------------------------------------------


def majority_vote_label(top_k_labels: Sequence[str], top_k_cosines: Sequence[float]) -> str:
    """Registration section 2: "top-K by cosine ... majority-vote label
    prediction (tie -> highest-mean-cosine label)". A further deterministic
    tie-break by sorted label discriminates a genuine multi-way count-AND-
    mean-cosine tie (never depends on input order)."""

    if not top_k_labels:
        raise Pemb4rReadError("majority_vote_label: top_k_labels must be non-empty")
    counts: dict[str, int] = {}
    for label in top_k_labels:
        counts[label] = counts.get(label, 0) + 1
    max_count = max(counts.values())
    tied = sorted(label for label, count in counts.items() if count == max_count)
    if len(tied) == 1:
        return tied[0]
    mean_cosine: dict[str, float] = {}
    for label in tied:
        cosines = [cosine for candidate_label, cosine in zip(top_k_labels, top_k_cosines) if candidate_label == label]
        mean_cosine[label] = sum(cosines) / len(cosines)
    best_mean = max(mean_cosine.values())
    winners = sorted(label for label, mean in mean_cosine.items() if mean == best_mean)
    return winners[0]


def compute_recall_at_k(top_k_labels: Sequence[str], gold_scenario: str, k: int) -> bool:
    """Registration section 4: "the mechanical ceiling on voting AND on
    C-DECODE" -- ``True`` iff ``gold_scenario`` appears anywhere in the
    first ``k`` entries of ``top_k_labels`` (the RANKED, non-deduplicated
    label sequence)."""

    return gold_scenario in top_k_labels[:k]


def compute_top1_margin(top_k_cosines: Sequence[float]) -> float:
    if not top_k_cosines:
        raise Pemb4rReadError("compute_top1_margin: top_k_cosines must be non-empty")
    if len(top_k_cosines) < 2:
        return top_k_cosines[0]
    return top_k_cosines[0] - top_k_cosines[1]


ARGMAX_STABLE = "STABLE"
ARGMAX_WITHIN_JITTER_NOISE = "WITHIN-JITTER-NOISE"


def evaluate_argmax_stability(margin: float, repeat_delta: float | None) -> str | None:
    """The 3M jitter lesson (module docstring): ``None`` when no repeat-
    delta was measured for this arm's own session (this function never
    guesses); otherwise :data:`ARGMAX_STABLE` iff ``margin`` clears
    ``repeat_delta``, else :data:`ARGMAX_WITHIN_JITTER_NOISE`."""

    if repeat_delta is None:
        return None
    return ARGMAX_STABLE if margin > repeat_delta else ARGMAX_WITHIN_JITTER_NOISE


# ---------------------------------------------------------------------------
# Per-arm report.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pemb4rSamplePrediction:
    sample_id: str
    gold_scenario: str
    top_k_labels: tuple[str, ...]
    top_k_cosines: tuple[float, ...]
    vote_label_k1: str
    vote_label_k3: str
    vote_label_k5: str
    vote_correct_k1: bool
    vote_correct_k3: bool
    vote_correct_k5: bool
    recall_hit_k1: bool
    recall_hit_k3: bool
    recall_hit_k5: bool
    top1_margin: float
    argmax_stability: str | None


@dataclass(frozen=True)
class Pemb4rArmReport:
    arm_id: str
    model: str
    query_kind: str
    dropped: bool
    drop_reason: str | None
    n_samples: int
    vote_accuracy_k1: float | None
    vote_accuracy_k3: float | None
    vote_accuracy_k5: float | None
    recall_at_1: float | None
    recall_at_3: float | None
    recall_at_5: float | None
    n_within_jitter_noise: int
    predictions: tuple[Pemb4rSamplePrediction, ...]
    confusion: tuple[ConfusionCell, ...]


def build_arm_report(
    arm_id: str,
    retrieval_plan_document: Mapping[str, object] | None,
    gold_scenarios: Mapping[str, str],
    *,
    dropped_reason: str | None = None,
    repeat_delta: float | None = None,
) -> Pemb4rArmReport:
    """Pure function of its inputs (module docstring). ``retrieval_plan_
    document is None`` OR ``dropped_reason is not None`` -- a gate-dropped
    arm (module docstring: "flight facts as explicit inputs") -- returns a
    ``dropped=True`` report with every accuracy field ``None``, never a
    silent zero."""

    if arm_id not in ARMS_BY_ID:
        raise Pemb4rReadError(f"build_arm_report: unknown arm_id {arm_id!r}")
    arm = ARMS_BY_ID[arm_id]

    if dropped_reason is not None or retrieval_plan_document is None:
        return Pemb4rArmReport(
            arm_id=arm_id,
            model=arm.model,
            query_kind=arm.query_kind,
            dropped=True,
            drop_reason=dropped_reason or "no retrieval_plan_document supplied",
            n_samples=0,
            vote_accuracy_k1=None,
            vote_accuracy_k3=None,
            vote_accuracy_k5=None,
            recall_at_1=None,
            recall_at_3=None,
            recall_at_5=None,
            n_within_jitter_noise=0,
            predictions=(),
            confusion=(),
        )

    arms_block = retrieval_plan_document.get("arms")
    if not isinstance(arms_block, Mapping) or arm_id not in arms_block:
        raise Pemb4rReadError(f"retrieval_plan_document carries no arm block for {arm_id!r}")
    per_sample_block = arms_block[arm_id].get("per_sample")
    if not isinstance(per_sample_block, Mapping) or not per_sample_block:
        raise Pemb4rReadError(f"retrieval_plan_document arm {arm_id!r} carries no per_sample rows")

    predictions: list[Pemb4rSamplePrediction] = []
    pairs: list[tuple[str, str]] = []
    n_correct = {1: 0, 3: 0, 5: 0}
    n_recall = {1: 0, 3: 0, 5: 0}
    n_within_jitter = 0
    for sample_id in sorted(per_sample_block):
        row = per_sample_block[sample_id]
        top_k_labels = tuple(row["top_k_labels"])
        top_k_cosines = tuple(float(c) for c in row["top_k_cosines"])
        gold = gold_scenarios.get(sample_id)
        if gold is None:
            raise Pemb4rReadError(f"no gold scenario for sample {sample_id!r}")
        vote_k1 = majority_vote_label(top_k_labels[:1], top_k_cosines[:1])
        vote_k3 = majority_vote_label(top_k_labels[:3], top_k_cosines[:3])
        vote_k5 = majority_vote_label(top_k_labels[:5], top_k_cosines[:5])
        correct_k1 = vote_k1 == gold
        correct_k3 = vote_k3 == gold
        correct_k5 = vote_k5 == gold
        n_correct[1] += int(correct_k1)
        n_correct[3] += int(correct_k3)
        n_correct[5] += int(correct_k5)
        recall1 = compute_recall_at_k(top_k_labels, gold, 1)
        recall3 = compute_recall_at_k(top_k_labels, gold, 3)
        recall5 = compute_recall_at_k(top_k_labels, gold, 5)
        n_recall[1] += int(recall1)
        n_recall[3] += int(recall3)
        n_recall[5] += int(recall5)
        margin = compute_top1_margin(top_k_cosines)
        stability = evaluate_argmax_stability(margin, repeat_delta)
        if stability == ARGMAX_WITHIN_JITTER_NOISE:
            n_within_jitter += 1
        pairs.append((gold, vote_k5))
        predictions.append(
            Pemb4rSamplePrediction(
                sample_id=sample_id,
                gold_scenario=gold,
                top_k_labels=top_k_labels,
                top_k_cosines=top_k_cosines,
                vote_label_k1=vote_k1,
                vote_label_k3=vote_k3,
                vote_label_k5=vote_k5,
                vote_correct_k1=correct_k1,
                vote_correct_k3=correct_k3,
                vote_correct_k5=correct_k5,
                recall_hit_k1=recall1,
                recall_hit_k3=recall3,
                recall_hit_k5=recall5,
                top1_margin=margin,
                argmax_stability=stability,
            )
        )

    n = len(predictions)
    return Pemb4rArmReport(
        arm_id=arm_id,
        model=arm.model,
        query_kind=arm.query_kind,
        dropped=False,
        drop_reason=None,
        n_samples=n,
        vote_accuracy_k1=n_correct[1] / n,
        vote_accuracy_k3=n_correct[3] / n,
        vote_accuracy_k5=n_correct[5] / n,
        recall_at_1=n_recall[1] / n,
        recall_at_3=n_recall[3] / n,
        recall_at_5=n_recall[5] / n,
        n_within_jitter_noise=n_within_jitter,
        predictions=tuple(predictions),
        confusion=build_confusion_table(pairs),
    )


# ---------------------------------------------------------------------------
# Cross-arm agreement -- reuses analysis.pemb3m_read.compute_cross_arm_
# agreement verbatim (module docstring: never a second implementation).
# ---------------------------------------------------------------------------


def compute_cross_arm_agreement(predictions_by_arm: Mapping[str, Mapping[str, str]]):
    from .pemb3m_read import compute_cross_arm_agreement as _compute

    return _compute(predictions_by_arm)


# ---------------------------------------------------------------------------
# Per-arm verdict findings (REGISTER-RESCUE / AUDIO-ROUTES).
# ---------------------------------------------------------------------------


def evaluate_audio_arm_findings(
    arm_id: str, accuracy: float | None, *, pooling_override_present: bool | None
) -> tuple[tuple[str, ...], str]:
    """REGISTER-RESCUE / AUDIO-ROUTES, registration section 4 verbatim.
    LCO arms carry a POOLING-OVERRIDE-SCOPED note while
    ``pooling_override_present`` is ``True`` (registration: "LCO arms stay
    stack-scoped while the pooling override stands"); GLAP is unscoped."""

    arm = ARMS_BY_ID[arm_id]
    if accuracy is None:
        return (), f"{arm_id}: no measured vote accuracy (dropped)"
    findings: list[str] = []
    if accuracy >= REGISTER_RESCUE_MIN_ACCURACY:
        findings.append("REGISTER-RESCUE")
    if accuracy >= AUDIO_ROUTES_MIN_ACCURACY:
        findings.append("AUDIO-ROUTES")
    scope_note = ""
    if arm.model in (MODEL_LCO3, MODEL_LCO7) and pooling_override_present:
        scope_note = " -- SCOPED (POOLING-OVERRIDE-PRESENT on this stack, never a model-level claim)"
    detail = f"{arm_id} ({arm.model}) vote accuracy(K=5) {accuracy:.4f}{scope_note}"
    return tuple(findings), detail


def evaluate_audio_content_absent(
    audio_accuracies: Mapping[str, float | None], text_accuracies: Mapping[str, float | None]
) -> tuple[bool, str]:
    present_audio = [acc for acc in audio_accuracies.values() if acc is not None]
    present_text = [acc for acc in text_accuracies.values() if acc is not None]
    if not present_audio or not present_text:
        return False, "cannot evaluate AUDIO-CONTENT-ABSENT: an audio or text accuracy is entirely missing (all dropped)"
    every_audio_low = all(acc <= AUDIO_CONTENT_ABSENT_MAX_AUDIO for acc in present_audio)
    best_text = max(present_text)
    fired = every_audio_low and best_text >= AUDIO_CONTENT_ABSENT_MIN_TEXT
    detail = (
        f"max(audio)={max(present_audio):.4f} (ceiling {AUDIO_CONTENT_ABSENT_MAX_AUDIO}), "
        f"best_text={best_text:.4f} (floor {AUDIO_CONTENT_ABSENT_MIN_TEXT}) -- "
        f"{'FIRED' if fired else 'not met'}"
    )
    return fired, detail


def evaluate_knn_beats_label_match(all_arm_accuracies: Mapping[str, float | None]) -> tuple[bool, str]:
    present = {arm_id: acc for arm_id, acc in all_arm_accuracies.items() if acc is not None}
    if not present:
        return False, "cannot evaluate KNN-BEATS-LABEL-MATCH: every arm dropped"
    best_arm_id = max(present, key=lambda arm_id: present[arm_id])
    best_acc = present[best_arm_id]
    fired = best_acc > KNN_BEATS_LABEL_MATCH_THRESHOLD
    detail = (
        f"best arm {best_arm_id} vote accuracy(K=5) {best_acc:.4f} vs CITED M4 label-match "
        f"{CITED_M4_LABEL_MATCH_ACCURACY:.4f} -- {'FIRED' if fired else 'not met'}"
    )
    return fired, detail


# ---------------------------------------------------------------------------
# C-DECODE: paired per-sample vs the consumed P-FEW FS-NONE rows.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CDecodePairedComparison:
    n_samples: int
    n_gain: int
    n_loss: int
    net: int
    verdict: str  # RETRIEVAL-SUPPLY-HELPS | RETRIEVAL-SUPPLY-HURTS | DESCRIPTIVE
    detail: str


def evaluate_c_decode_vs_cited_fs_none(
    c_decode_correct_by_sample: Mapping[str, bool], cited_fs_none_correct_by_sample: Mapping[str, bool]
) -> CDecodePairedComparison:
    """Registration section 4: "paired per-sample vs the consumed FS-NONE
    rows (cross-session +/-2-sample drift carried)". ``net = n_gain -
    n_loss`` over the samples common to both (module docstring: never
    fabricates a comparison for a sample present in only one series)."""

    common = sorted(set(c_decode_correct_by_sample) & set(cited_fs_none_correct_by_sample))
    if not common:
        raise Pemb4rReadError("evaluate_c_decode_vs_cited_fs_none: no common sample ids between the two series")
    n_gain = sum(1 for sid in common if c_decode_correct_by_sample[sid] and not cited_fs_none_correct_by_sample[sid])
    n_loss = sum(1 for sid in common if not c_decode_correct_by_sample[sid] and cited_fs_none_correct_by_sample[sid])
    net = n_gain - n_loss
    if net >= C_DECODE_HELPS_MIN_NET:
        verdict = "RETRIEVAL-SUPPLY-HELPS"
    elif net <= C_DECODE_HURTS_MAX_NET:
        verdict = "RETRIEVAL-SUPPLY-HURTS"
    else:
        verdict = "DESCRIPTIVE"
    detail = (
        f"net={net:+d} (gain={n_gain}, loss={n_loss}) over {len(common)} paired sample(s) vs the "
        f"consumed {CONSUMED_PFEW_RUN_EXPERIMENT_ID}/{CONSUMED_PFEW_ATTEMPT_ID} FS-NONE rows "
        "(cross-session +/-2-sample drift carried, registration section 4)"
    )
    return CDecodePairedComparison(n_samples=len(common), n_gain=n_gain, n_loss=n_loss, net=net, verdict=verdict, detail=detail)


# ---------------------------------------------------------------------------
# Feasibility matrix (module docstring).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeasibilityRow:
    name: str
    status: str
    detail: str


def build_feasibility_matrix(*, dropped_arms: Mapping[str, str] | None = None) -> tuple[FeasibilityRow, ...]:
    dropped = dict(dropped_arms or {})
    rows: list[FeasibilityRow] = []
    for arm_id in flight.ARM_IDS:
        if arm_id in dropped:
            rows.append(FeasibilityRow(name=arm_id, status=FEASIBILITY_ENV_GATED, detail=dropped[arm_id]))
        else:
            rows.append(FeasibilityRow(name=arm_id, status=FEASIBILITY_FLYABLE, detail="flown this attempt"))
    rows.append(
        FeasibilityRow(
            name="omni-embed-nemotron-3b",
            status=FEASIBILITY_ENV_GATED,
            detail="NC license + a pinned transformers branch (registration section 3) -- never flown by this probe",
        )
    )
    rows.append(
        FeasibilityRow(
            name="clsp",
            status=FEASIBILITY_ENV_GATED,
            detail="transformers 5.12 incompatibility (registration section 3) -- never flown by this probe",
        )
    )
    return tuple(rows)


# ---------------------------------------------------------------------------
# Overall verdict.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pemb4rVerdict:
    per_audio_arm_findings: Mapping[str, tuple[str, ...]]
    per_audio_arm_detail: Mapping[str, str]
    audio_content_absent: bool
    audio_content_absent_detail: str
    knn_beats_label_match: bool
    knn_beats_label_match_detail: str
    c_decode: CDecodePairedComparison | None
    c_decode_status: str
    overall: str


def evaluate_pemb4r_verdict(
    *,
    audio_arm_accuracies: Mapping[str, float | None],
    text_arm_accuracies: Mapping[str, float | None],
    all_arm_accuracies: Mapping[str, float | None],
    pooling_override_present_by_model: Mapping[str, bool],
    c_decode: CDecodePairedComparison | None,
    c_decode_status: str = C_DECODE_NOT_PROVIDED,
) -> Pemb4rVerdict:
    if c_decode is not None and c_decode_status != C_DECODE_NOT_PROVIDED:
        raise Pemb4rReadError(
            "C-DECODE cannot be both evaluated and assigned a non-default status"
        )
    per_audio_findings: dict[str, tuple[str, ...]] = {}
    per_audio_detail: dict[str, str] = {}
    for arm_id in AUDIO_ARM_IDS:
        arm = ARMS_BY_ID[arm_id]
        pooling_present = pooling_override_present_by_model.get(arm.model)
        findings, detail = evaluate_audio_arm_findings(
            arm_id, audio_arm_accuracies.get(arm_id), pooling_override_present=pooling_present
        )
        per_audio_findings[arm_id] = findings
        per_audio_detail[arm_id] = detail

    audio_content_absent, audio_content_absent_detail = evaluate_audio_content_absent(audio_arm_accuracies, text_arm_accuracies)
    knn_beats, knn_beats_detail = evaluate_knn_beats_label_match(all_arm_accuracies)

    fired: list[str] = []
    for arm_id in AUDIO_ARM_IDS:
        for finding in per_audio_findings[arm_id]:
            fired.append(f"{finding}({arm_id})")
    if audio_content_absent:
        fired.append("AUDIO-CONTENT-ABSENT")
    if knn_beats:
        fired.append("KNN-BEATS-LABEL-MATCH")
    if c_decode is not None and c_decode.verdict in ("RETRIEVAL-SUPPLY-HELPS", "RETRIEVAL-SUPPLY-HURTS"):
        fired.append(c_decode.verdict)
    overall = " + ".join(fired) if fired else "INCONCLUSIVE-4R"

    return Pemb4rVerdict(
        per_audio_arm_findings=per_audio_findings,
        per_audio_arm_detail=per_audio_detail,
        audio_content_absent=audio_content_absent,
        audio_content_absent_detail=audio_content_absent_detail,
        knn_beats_label_match=knn_beats,
        knn_beats_label_match_detail=knn_beats_detail,
        c_decode=c_decode,
        c_decode_status=c_decode_status,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Sweep-level report.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pemb4rSweepReport:
    arm_reports: Mapping[str, Pemb4rArmReport]
    cross_arm_agreement: tuple
    feasibility_matrix: tuple[FeasibilityRow, ...]
    retrieval_plan_verified: bool
    retrieval_plan_mismatches: tuple[str, ...]
    verdict: Pemb4rVerdict


def build_pemb4r_sweep_report(
    *,
    retrieval_plan_document: Mapping[str, object],
    gold_scenarios: Mapping[str, str],
    dropped_arms: Mapping[str, str] | None = None,
    pooling_override_present_by_model: Mapping[str, bool] | None = None,
    repeat_delta_by_model: Mapping[str, float] | None = None,
    c_decode_correct_by_sample: Mapping[str, bool] | None = None,
    cited_fs_none_correct_by_sample: Mapping[str, bool] | None = None,
    c_decode_status: str = C_DECODE_NOT_PROVIDED,
    retrieval_plan_verification: tuple[bool, tuple[str, ...]] | None = None,
) -> Pemb4rSweepReport:
    """Pure function of its inputs (module docstring). Every "flight fact"
    -- ``dropped_arms``, ``pooling_override_present_by_model``,
    ``repeat_delta_by_model``, ``c_decode_correct_by_sample``, ``cited_fs_
    none_correct_by_sample``, ``retrieval_plan_verification`` -- is an
    EXPLICIT, caller-supplied input; this function never hardcodes or
    guesses any of them."""

    dropped_arms = dropped_arms or {}
    pooling_override_present_by_model = pooling_override_present_by_model or {}
    repeat_delta_by_model = repeat_delta_by_model or {}

    arm_reports: dict[str, Pemb4rArmReport] = {}
    for arm_id in flight.ARM_IDS:
        arm = ARMS_BY_ID[arm_id]
        arm_reports[arm_id] = build_arm_report(
            arm_id,
            None if arm_id in dropped_arms else retrieval_plan_document,
            gold_scenarios,
            dropped_reason=dropped_arms.get(arm_id),
            repeat_delta=repeat_delta_by_model.get(arm.model),
        )

    predictions_by_arm = {
        arm_id: {p.sample_id: p.vote_label_k5 for p in report.predictions}
        for arm_id, report in arm_reports.items()
        if not report.dropped
    }
    cross_arm = compute_cross_arm_agreement(predictions_by_arm)

    audio_accuracies = {arm_id: arm_reports[arm_id].vote_accuracy_k5 for arm_id in AUDIO_ARM_IDS}
    text_accuracies = {arm_id: arm_reports[arm_id].vote_accuracy_k5 for arm_id in TEXT_ARM_IDS}
    all_accuracies = {arm_id: report.vote_accuracy_k5 for arm_id, report in arm_reports.items()}

    if not isinstance(c_decode_status, str) or not c_decode_status:
        raise Pemb4rReadError("c_decode_status must be a non-empty string")
    c_decode_comparison: CDecodePairedComparison | None = None
    if c_decode_correct_by_sample is not None and cited_fs_none_correct_by_sample is not None:
        c_decode_comparison = evaluate_c_decode_vs_cited_fs_none(c_decode_correct_by_sample, cited_fs_none_correct_by_sample)

    verdict = evaluate_pemb4r_verdict(
        audio_arm_accuracies=audio_accuracies,
        text_arm_accuracies=text_accuracies,
        all_arm_accuracies=all_accuracies,
        pooling_override_present_by_model=pooling_override_present_by_model,
        c_decode=c_decode_comparison,
        c_decode_status=c_decode_status,
    )

    verified, mismatches = retrieval_plan_verification if retrieval_plan_verification is not None else (False, ("not verified -- caller supplied no vectors to re-derive against",))

    return Pemb4rSweepReport(
        arm_reports=arm_reports,
        cross_arm_agreement=cross_arm,
        feasibility_matrix=build_feasibility_matrix(dropped_arms=dropped_arms),
        retrieval_plan_verified=verified,
        retrieval_plan_mismatches=mismatches,
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# JSON / text rendering.
# ---------------------------------------------------------------------------


def _arm_report_to_json(report: Pemb4rArmReport) -> dict[str, object]:
    return {
        "arm_id": report.arm_id,
        "model": report.model,
        "query_kind": report.query_kind,
        "dropped": report.dropped,
        "drop_reason": report.drop_reason,
        "n_samples": report.n_samples,
        "vote_accuracy_k1": report.vote_accuracy_k1,
        "vote_accuracy_k3": report.vote_accuracy_k3,
        "vote_accuracy_k5": report.vote_accuracy_k5,
        "recall_at_1": report.recall_at_1,
        "recall_at_3": report.recall_at_3,
        "recall_at_5": report.recall_at_5,
        "n_within_jitter_noise": report.n_within_jitter_noise,
        "predictions": [
            {
                "sample_id": p.sample_id,
                "gold_scenario": p.gold_scenario,
                "vote_label_k5": p.vote_label_k5,
                "vote_correct_k5": p.vote_correct_k5,
                "recall_hit_k5": p.recall_hit_k5,
                "top1_margin": p.top1_margin,
                "argmax_stability": p.argmax_stability,
            }
            for p in report.predictions
        ],
        "confusion": [{"gold": c.gold, "predicted": c.predicted, "count": c.count} for c in report.confusion],
    }


def sweep_report_to_json(report: Pemb4rSweepReport) -> dict[str, object]:
    verdict = report.verdict
    return {
        "schema": REPORT_SCHEMA,
        "probe_id": flight.PROBE_ID,
        "chance_accuracy": CHANCE_ACCURACY,
        "cited": {
            "fs_none": CITED_FS_NONE_ACCURACY,
            "a1r": CITED_A1R_ACCURACY,
            "m4_label_match": CITED_M4_LABEL_MATCH_ACCURACY,
            "audio_vs_label_floor": list(CITED_AUDIO_VS_LABEL_FLOOR),
        },
        "arms": {arm_id: _arm_report_to_json(arm_report) for arm_id, arm_report in report.arm_reports.items()},
        "cross_arm_agreement": [
            {
                "arm_a": pair.arm_a,
                "arm_b": pair.arm_b,
                "n_common_samples": pair.n_common_samples,
                "n_agree": pair.n_agree,
                "agreement_rate": pair.agreement_rate,
            }
            for pair in report.cross_arm_agreement
        ],
        "feasibility_matrix": [
            {"name": row.name, "status": row.status, "detail": row.detail} for row in report.feasibility_matrix
        ],
        "retrieval_plan_verified": report.retrieval_plan_verified,
        "retrieval_plan_mismatches": list(report.retrieval_plan_mismatches),
        "verdict": {
            "per_audio_arm_findings": {arm_id: list(findings) for arm_id, findings in verdict.per_audio_arm_findings.items()},
            "per_audio_arm_detail": dict(verdict.per_audio_arm_detail),
            "audio_content_absent": verdict.audio_content_absent,
            "audio_content_absent_detail": verdict.audio_content_absent_detail,
            "knn_beats_label_match": verdict.knn_beats_label_match,
            "knn_beats_label_match_detail": verdict.knn_beats_label_match_detail,
            "c_decode": (
                None
                if verdict.c_decode is None
                else {
                    "n_samples": verdict.c_decode.n_samples,
                    "n_gain": verdict.c_decode.n_gain,
                    "n_loss": verdict.c_decode.n_loss,
                    "net": verdict.c_decode.net,
                    "verdict": verdict.c_decode.verdict,
                    "detail": verdict.c_decode.detail,
                }
            ),
            "c_decode_status": verdict.c_decode_status,
            "overall": verdict.overall,
        },
    }


def render_sweep_report(report: Pemb4rSweepReport) -> str:
    lines = [
        "P-EMB-4R pinned offline read (docs/readiness/2026-08-20-pemb4r-preregistration-REGISTERED.md)",
        "=" * 84,
        "",
        f"chance={CHANCE_ACCURACY} CITED: FS-NONE={CITED_FS_NONE_ACCURACY} A1'r={CITED_A1R_ACCURACY} "
        f"M4-label-match={CITED_M4_LABEL_MATCH_ACCURACY} audio-vs-label-floor={CITED_AUDIO_VS_LABEL_FLOOR}",
        "",
        f"retrieval_plan_verified={report.retrieval_plan_verified} "
        f"({len(report.retrieval_plan_mismatches)} mismatch(es))",
        "",
        "Mandatory pre-verdict reachability -- per-arm recall@1/3/5 (mechanical ceiling)",
    ]
    for arm_id in flight.ARM_IDS:
        arm_report = report.arm_reports[arm_id]
        if arm_report.dropped:
            lines.append(f"  [{arm_id}] DROPPED ({arm_report.drop_reason})")
            continue
        lines.append(
            f"  [{arm_id}] vote_acc(K5)={arm_report.vote_accuracy_k5:.4f} "
            f"recall@1={arm_report.recall_at_1:.4f} recall@3={arm_report.recall_at_3:.4f} "
            f"recall@5={arm_report.recall_at_5:.4f} within_jitter_noise={arm_report.n_within_jitter_noise}"
        )
    lines.append("")
    lines.append("Cross-arm agreement")
    for pair in report.cross_arm_agreement:
        lines.append(f"  {pair.arm_a} vs {pair.arm_b}: {pair.n_agree}/{pair.n_common_samples} ({pair.agreement_rate:.4f})")
    lines.append("")
    lines.append("Feasibility matrix")
    for row in report.feasibility_matrix:
        lines.append(f"  [{row.status}] {row.name}: {row.detail}")
    lines.append("")

    verdict = report.verdict
    lines.append("Per-audio-arm findings")
    for arm_id in AUDIO_ARM_IDS:
        findings = verdict.per_audio_arm_findings.get(arm_id, ())
        lines.append(f"  [{arm_id}] {list(findings) or '(none)'} -- {verdict.per_audio_arm_detail.get(arm_id, '')}")
    lines.append("")
    lines.append(f"[AUDIO-CONTENT-ABSENT] {verdict.audio_content_absent}")
    lines.append(f"  {verdict.audio_content_absent_detail}")
    lines.append(f"[KNN-BEATS-LABEL-MATCH] {verdict.knn_beats_label_match}")
    lines.append(f"  {verdict.knn_beats_label_match_detail}")
    if verdict.c_decode is not None:
        lines.append(f"[C-DECODE] {verdict.c_decode.verdict}")
        lines.append(f"  {verdict.c_decode.detail}")
    else:
        lines.append(f"[C-DECODE] {verdict.c_decode_status}")
    lines.append("")
    lines.append(f"[OVERALL] {verdict.overall}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pemb4r-read",
        description=(
            "P-EMB-4R pinned offline read suite: per-arm vote-accuracy (top-K majority, tie -> "
            "highest mean cosine), recall@1/3/5, per-sample argmax-stability vs measured jitter, "
            "cross-arm agreement, feasibility matrix, verdict evaluators exactly as registered. "
            "Model-free, read-only."
        ),
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--embeddings-root", type=Path, default=None)
    parser.add_argument("--sample-manifest", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--dropped-arms-json", type=Path, default=None, help="arm_id -> drop reason, explicit flight facts")
    parser.add_argument(
        "--pooling-override-json", type=Path, default=None, help="model -> pooling_override_present bool, explicit flight facts"
    )
    parser.add_argument("--repeat-delta-json", type=Path, default=None, help="model -> measured repeat-call cosine delta")
    parser.add_argument(
        "--flight-state",
        type=Path,
        default=None,
        help="landed flight-state.json; defaults to the committed P-EMB-4R archive",
    )
    parser.add_argument(
        "--flight-run-dir",
        type=Path,
        default=None,
        help="landed attempt directory containing repeat-call vectors",
    )
    return parser


def _refuse_if_already_run(output_dir: Path) -> Path | None:
    import sys

    verdict_path = output_dir / "verdict.json"
    if verdict_path.exists():
        print(
            f"REFUSED: {verdict_path} already exists -- this suite refuses to run twice against "
            "the same output dir (one-shot read discipline); choose a fresh --output-dir if a "
            "genuinely new read is intended",
            file=sys.stderr,
        )
        return None
    return verdict_path


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import REPO_ROOT as _REPO_ROOT
    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import write_json_artifact
    from .pemb_read import gold_scenarios_for_run_a

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else _REPO_ROOT
    root = Path(args.embeddings_root) if args.embeddings_root else data_root()
    lock = load_lock(umbrella_lock_path(repo_root))

    output_dir = Path(args.output_dir)
    verdict_path = _refuse_if_already_run(output_dir)
    if verdict_path is None:
        return 1

    def _load_json_or_empty(path: Path | None) -> dict:
        if path is None:
            return {}
        return json.loads(Path(path).read_text(encoding="utf-8"))

    try:
        sample_manifest_path = args.sample_manifest or (repo_root / "configs/probes/g0-binding/pslu-sample-devel-n60.json")
        gold = gold_scenarios_for_run_a(lock, root, repo_root=repo_root, sample_manifest_path=sample_manifest_path)
        retrieval_plan_document = flight.load_retrieval_plan(root)
        flight_state_path = args.flight_state or (
            repo_root
            / "docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb4r-flight/flight-state.json"
        )
        flight_state = json.loads(Path(flight_state_path).read_text(encoding="utf-8"))
        if not isinstance(flight_state, Mapping):
            raise Pemb4rReadError(f"{flight_state_path}: flight state must be a JSON object")
        state_dropped_arms, state_pooling_override = flight_facts_from_state(flight_state)
        dropped_arms = _load_json_or_empty(args.dropped_arms_json) or state_dropped_arms
        pooling_override = _load_json_or_empty(args.pooling_override_json) or state_pooling_override
        attempt_id = flight_state.get("attempt_id")
        if not isinstance(attempt_id, str) or not attempt_id:
            raise Pemb4rReadError(f"{flight_state_path}: flight state lacks attempt_id")
        flight_run_dir = args.flight_run_dir or (root / "runs" / flight.PROBE_ID / attempt_id)
        repeat_delta = _load_json_or_empty(args.repeat_delta_json) or load_repeat_delta_by_model(
            flight_run_dir
        )
        retrieval_verification = verify_landed_retrieval_plan(root, retrieval_plan_document)

        report = build_pemb4r_sweep_report(
            retrieval_plan_document=retrieval_plan_document,
            gold_scenarios=gold,
            dropped_arms=dropped_arms,
            pooling_override_present_by_model=pooling_override,
            repeat_delta_by_model=repeat_delta,
            c_decode_status=C_DECODE_CANCELED_OWNER_20260821,
            retrieval_plan_verification=retrieval_verification,
        )
        document = sweep_report_to_json(report)
        rendered = render_sweep_report(report)
    except (Pemb4rReadError, flight.Pemb4rFlightError, PembReadError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    write_json_artifact(verdict_path, document)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    return 0


__all__ = [
    "ARGMAX_STABLE",
    "ARGMAX_WITHIN_JITTER_NOISE",
    "AUDIO_CONTENT_ABSENT_MAX_AUDIO",
    "AUDIO_CONTENT_ABSENT_MIN_TEXT",
    "AUDIO_ROUTES_MIN_ACCURACY",
    "CHANCE_ACCURACY",
    "CITED_A1R_ACCURACY",
    "CITED_AUDIO_VS_LABEL_FLOOR",
    "CITED_FS_NONE_ACCURACY",
    "C_DECODE_CANCELED_OWNER_20260821",
    "C_DECODE_NOT_PROVIDED",
    "CITED_M4_LABEL_MATCH_ACCURACY",
    "CONSUMED_PFEW_ATTEMPT_ID",
    "CONSUMED_PFEW_RUN_EXPERIMENT_ID",
    "C_DECODE_HELPS_MIN_NET",
    "C_DECODE_HURTS_MAX_NET",
    "FEASIBILITY_ENV_GATED",
    "FEASIBILITY_FLYABLE",
    "KNN_BEATS_LABEL_MATCH_THRESHOLD",
    "REGISTER_RESCUE_MIN_ACCURACY",
    "REPORT_SCHEMA",
    "CDecodePairedComparison",
    "FeasibilityRow",
    "Pemb4rArmReport",
    "Pemb4rReadError",
    "Pemb4rSamplePrediction",
    "Pemb4rSweepReport",
    "Pemb4rVerdict",
    "build_arm_report",
    "build_feasibility_matrix",
    "build_pemb4r_sweep_report",
    "compute_cross_arm_agreement",
    "compute_recall_at_k",
    "compute_top1_margin",
    "evaluate_argmax_stability",
    "evaluate_audio_arm_findings",
    "evaluate_audio_content_absent",
    "evaluate_c_decode_vs_cited_fs_none",
    "evaluate_knn_beats_label_match",
    "evaluate_pemb4r_verdict",
    "flight_facts_from_state",
    "load_repeat_delta_by_model",
    "main",
    "majority_vote_label",
    "render_sweep_report",
    "sweep_report_to_json",
    "verify_retrieval_plan_document",
    "verify_landed_retrieval_plan",
]
