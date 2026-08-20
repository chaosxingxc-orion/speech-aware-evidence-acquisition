"""P-EMB-3M pinned offline read suite (pre-registered, SAEA-PROBE-pemb3m-388):
``docs/readiness/2026-08-20-pemb3m-preregistration-REGISTERED.md`` section 4.

Model-free, read-only, sibling of ``analysis.pemb_read``/``analysis.
pemb3l_read`` (built and coordinator-reviewed BEFORE the read, prereg
section 6: "pinned suite extension ... built and coordinator-reviewed
BEFORE the read"): loads the already-written per-arm embedding-vector
manifests (``rails.probes.pemb3m_flight.load_pemb3m_arm_manifest``, dim-
generic across the four arms' 2048/1024/512/1024 dims) and scores each with
the SAME pure argmax-cosine matcher every sibling P-EMB read uses
(:func:`~analysis.pemb_read.rank_cosine` /
:func:`~analysis.pemb_read.cosine_similarity` /
:func:`~analysis.pemb_read.build_confusion_table`, reused verbatim -- never
a second cosine implementation) against SCORING-SIDE-ONLY gold
(:func:`~analysis.pemb_read.gold_scenarios_for_run_a`, reused directly: the
P-EMB-3M surface is the SAME frozen 60-sample/18-label P-EMB-1 surface).

A DROPPED-DEPS control arm (registration section 3 item 2) has no
manifest -- :func:`build_arm_report` accepts ``manifest=None`` for exactly
that case and returns a ``dropped=True`` report with ``accuracy=None``;
every downstream aggregate (:func:`compute_cross_arm_agreement`,
:func:`evaluate_control_anomaly`, :func:`evaluate_pemb3m_verdict`) treats
a dropped arm's accuracy as absent rather than zero, so a dropped control
never silently drags a comparison down.

Verdict (:func:`evaluate_pemb3m_verdict`) implements the registered
thresholds per prereg section 4. UNLIKE ``analysis.pemb3l_read``'s single
collapsed verdict string (three arms reduced by "any"/"every"), P-EMB-3M's
own registered clauses name M1 and M4 INDEPENDENTLY ("M1 EMB-ROUTES", "M4
CASCADE-ROUTES/CASCADE-WEAK") plus a separately-fireable named finding
(CONTROL-ANOMALY, "any verdict") -- so this module reports a
:class:`Pemb3mVerdict` carrying M1's own label, M4's own label, and the
control-anomaly finding side by side, joined into one ``overall`` string
only for a single-line summary. This is a considered reading of an
under-specified registration clause (recorded here for audit, per the
build mission's own instruction to resolve spec ambiguity with judgment):
the alternative (a single collapsed verdict, pemb3l-style) cannot represent
"M1 EMB-ROUTES AND CONTROL-ANOMALY fired simultaneously", which the
registration's own "(named finding, any verdict)" parenthetical explicitly
allows.

Attractor structure reuses ``analysis.pemb3l_read.compute_attractor_structure``
verbatim (never a second implementation). Cross-arm agreement
(:func:`compute_cross_arm_agreement`) and cosine-sign profiles
(:func:`compute_cosine_sign_profile`) generalize the by-hand analyses
``docs/readiness/2026-08-20-pemb3l-verdict.md`` sections 2-3 performed
("L1 vs L2 predicted-label agreement 0/60", "pairs with a positive
cosine ... 59/60, 33/60, 1/60") into reusable, per-pair/per-arm
computations.

qwen3-emb repeat-call jitter tolerance (:func:`evaluate_m4_jitter_tolerance`,
prereg section 6 / ``docs/readiness/2026-08-20-e1-local-embedder-identity.md``
Mission C): the declared >= 0.9999 cosine tolerance PLUS an argmax-stability
check (does the SAME text, embedded twice, ever change which label wins
the argmax against the SAME 18-label set) -- argmax verdicts are
"unaffected at that magnitude" is the registered CLAIM; this function is
what actually checks it against the flight's own repeat-call sample rather
than assuming it.

Idempotence: :func:`build_arm_report`/:func:`build_pemb3m_sweep_report` are
pure functions of their inputs (no I/O, no mutation, no randomness).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..rails.probes.pemb3m_flight import (
    ARM_IDS,
    ARM_LABEL_N,
    ARM_M1_ID,
    ARM_M2_ID,
    ARM_M3_ID,
    ARM_M4_ID,
    ARM_QUERY_N,
    ARMS_BY_ID,
    LoadedPemb3mManifest,
    Pemb3mFlightError,
    arm_run_id,
)
from .pemb3l_read import AttractorStructure, Pemb3lReadError, compute_attractor_structure
from .pemb_read import ConfusionCell, PembReadError, _assert_key_sets_equal, build_confusion_table, cosine_similarity, rank_cosine

REPORT_SCHEMA = "saea-pemb3m-read-v1"

# Registered thresholds (prereg section 4, quoted verbatim in each clause's
# own detail text below). M1 and CASCADE(M4) share the SAME 0.65/0.30 bands.
EMB_ROUTES_MIN_ACCURACY = 0.65
EMB_WEAK_MAX_ACCURACY = 0.30
CASCADE_ROUTES_MIN_ACCURACY = 0.65
CASCADE_WEAK_MAX_ACCURACY = 0.30
CONTROL_ANOMALY_MIN_ACCURACY = 0.30

# E-1 Mission C (module docstring): "cosine >= 0.9999 on repeat" declared
# read-suite tolerance for qwen3-emb's own CUDA batched-inference jitter.
JITTER_COSINE_TOLERANCE = 0.9999


class Pemb3mReadError(RuntimeError):
    """A manifest/gold input is malformed, an id-set mismatch is detected,
    or a harness-defect fail-closed check tripped -- never raised for an
    ordinary, structurally clean read."""


# ---------------------------------------------------------------------------
# Cosine-sign profile (generalizes the pemb3l verdict's own by-hand
# "pairs with a positive cosine" table).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CosineSignProfile:
    n: int
    n_positive: int
    n_negative: int
    n_zero: int
    positive_share: float
    mean_cosine: float
    max_cosine: float
    min_cosine: float


def compute_cosine_sign_profile(top1_cosines: Sequence[float]) -> CosineSignProfile:
    if not top1_cosines:
        raise Pemb3mReadError("compute_cosine_sign_profile: top1_cosines must be non-empty")
    n = len(top1_cosines)
    n_positive = sum(1 for value in top1_cosines if value > 0.0)
    n_negative = sum(1 for value in top1_cosines if value < 0.0)
    n_zero = n - n_positive - n_negative
    return CosineSignProfile(
        n=n,
        n_positive=n_positive,
        n_negative=n_negative,
        n_zero=n_zero,
        positive_share=n_positive / n,
        mean_cosine=sum(top1_cosines) / n,
        max_cosine=max(top1_cosines),
        min_cosine=min(top1_cosines),
    )


# ---------------------------------------------------------------------------
# Cross-arm agreement (generalizes the pemb3l verdict's own by-hand
# per-sample predicted-label agreement counts).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CrossArmAgreement:
    arm_a: str
    arm_b: str
    n_common_samples: int
    n_agree: int
    agreement_rate: float


def compute_cross_arm_agreement(predictions_by_arm: Mapping[str, Mapping[str, str]]) -> tuple[CrossArmAgreement, ...]:
    """Every unordered pair of arms present in ``predictions_by_arm``
    (typically the non-dropped subset of :data:`~rails.probes.
    pemb3m_flight.ARM_IDS`): the count of samples both arms predicted a
    label for, and how often that predicted label was IDENTICAL --
    'agreement', never 'correctness' (gold never enters this
    computation)."""

    arm_ids = sorted(predictions_by_arm)
    results: list[CrossArmAgreement] = []
    for index, arm_a in enumerate(arm_ids):
        for arm_b in arm_ids[index + 1 :]:
            common = sorted(set(predictions_by_arm[arm_a]) & set(predictions_by_arm[arm_b]))
            n_agree = sum(
                1 for sample_id in common if predictions_by_arm[arm_a][sample_id] == predictions_by_arm[arm_b][sample_id]
            )
            results.append(
                CrossArmAgreement(
                    arm_a=arm_a,
                    arm_b=arm_b,
                    n_common_samples=len(common),
                    n_agree=n_agree,
                    agreement_rate=(n_agree / len(common)) if common else 0.0,
                )
            )
    return tuple(results)


# ---------------------------------------------------------------------------
# M4 repeat-call jitter tolerance (E-1 Mission C).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JitterToleranceResult:
    cosine: float
    within_tolerance: bool
    argmax_a: str
    argmax_b: str
    argmax_stable: bool


def evaluate_m4_jitter_tolerance(
    jitter_a: Sequence[float],
    jitter_b: Sequence[float],
    label_vectors: Mapping[str, Sequence[float]],
    *,
    tolerance: float = JITTER_COSINE_TOLERANCE,
) -> JitterToleranceResult:
    """The declared cosine >= 0.9999 tolerance PLUS an argmax-stability
    check: embeds the SAME text twice (``jitter_a``/``jitter_b``, the
    flight's own :func:`~rails.probes.pemb3m_flight.run_m4_repeat_call_gate`
    pair) and confirms BOTH that the two vectors' own cosine clears
    ``tolerance`` AND that ranking either one against ``label_vectors``
    (the SAME 18-label set every arm uses) picks the SAME top-1 label."""

    cosine = cosine_similarity(jitter_a, jitter_b)
    argmax_a, _cosine_a = rank_cosine(jitter_a, label_vectors)[0]
    argmax_b, _cosine_b = rank_cosine(jitter_b, label_vectors)[0]
    return JitterToleranceResult(
        cosine=cosine,
        within_tolerance=cosine >= tolerance,
        argmax_a=argmax_a,
        argmax_b=argmax_b,
        argmax_stable=(argmax_a == argmax_b),
    )


# ---------------------------------------------------------------------------
# Verdict evaluators (prereg section 4).
# ---------------------------------------------------------------------------


def evaluate_m1_verdict(accuracy: float | None, *, pooling_override_present: bool) -> tuple[str, str]:
    """EMB-ROUTES / EMB-WEAK(-SCOPED) / INCONCLUSIVE-3M-M1, prereg section 4
    verbatim. ``EMB-WEAK-SCOPED`` substitutes for ``EMB-WEAK`` exactly when
    :data:`~rails.probes.pemb3m_flight.PoolingDifferGateResult.
    pooling_override_present` fired on the M1 pre-flight gate."""

    if accuracy is None:
        return "INCONCLUSIVE-3M-M1", "M1 carries no measured accuracy (missing manifest)"
    if accuracy >= EMB_ROUTES_MIN_ACCURACY:
        return "EMB-ROUTES", (
            f"M1 (LCO) accuracy {accuracy:.4f} >= {EMB_ROUTES_MIN_ACCURACY} -- a dedicated embedder "
            "is a viable routing tier at a fraction of decode cost"
        )
    if accuracy <= EMB_WEAK_MAX_ACCURACY:
        if pooling_override_present:
            return "EMB-WEAK-SCOPED", (
                f"M1 (LCO) accuracy {accuracy:.4f} <= {EMB_WEAK_MAX_ACCURACY} -- POOLING-OVERRIDE-PRESENT "
                "fired on the pre-flight gate, so this refutation is SCOPED to the llama.cpp construction, "
                "never a model-level refutation"
            )
        return "EMB-WEAK", (
            f"M1 (LCO) accuracy {accuracy:.4f} <= {EMB_WEAK_MAX_ACCURACY} -- the dedicated-embedder "
            "hypothesis fails on this stack (clean pooling gate: model-level refutation)"
        )
    return "INCONCLUSIVE-3M-M1", (
        f"M1 (LCO) accuracy {accuracy:.4f} falls strictly between {EMB_WEAK_MAX_ACCURACY} and "
        f"{EMB_ROUTES_MIN_ACCURACY}"
    )


def evaluate_m4_verdict(accuracy: float | None) -> tuple[str, str]:
    """CASCADE-ROUTES / CASCADE-WEAK / INCONCLUSIVE-3M-M4, prereg section 4
    verbatim (SAME 0.65/0.30 bands as M1)."""

    if accuracy is None:
        return "INCONCLUSIVE-3M-M4", "M4 carries no measured accuracy (missing manifest)"
    if accuracy >= CASCADE_ROUTES_MIN_ACCURACY:
        return "CASCADE-ROUTES", (
            f"M4 (CASCADE) accuracy {accuracy:.4f} >= {CASCADE_ROUTES_MIN_ACCURACY} -- the routing tier "
            "does not need audio embeddings at all; the ~89%-text-side pattern (P-KEY) extends to "
            "representation matching"
        )
    if accuracy <= CASCADE_WEAK_MAX_ACCURACY:
        return "CASCADE-WEAK", f"M4 (CASCADE) accuracy {accuracy:.4f} <= {CASCADE_WEAK_MAX_ACCURACY}"
    return "INCONCLUSIVE-3M-M4", (
        f"M4 (CASCADE) accuracy {accuracy:.4f} falls strictly between {CASCADE_WEAK_MAX_ACCURACY} and "
        f"{CASCADE_ROUTES_MIN_ACCURACY}"
    )


def evaluate_control_anomaly(
    *, m1_accuracy: float | None, m2_accuracy: float | None, m3_accuracy: float | None, m4_accuracy: float | None
) -> tuple[bool, str]:
    """CONTROL-ANOMALY (prereg section 4: "named finding, any verdict"):
    ``max(M2, M3) >= max(M1, M4) AND >= 0.30``. A dropped control
    (``accuracy=None``) is excluded from ``max(M2, M3)``, never treated as
    0.0 (module docstring: "a dropped control never silently drags a
    comparison down"); if BOTH controls are dropped, the finding cannot
    fire and is reported as such."""

    control_values = [value for value in (m2_accuracy, m3_accuracy) if value is not None]
    if not control_values:
        return False, "CONTROL-ANOMALY cannot be evaluated: both M2 and M3 carry no measured accuracy (dropped)"
    max_control = max(control_values)
    primary_values = [value for value in (m1_accuracy, m4_accuracy) if value is not None]
    max_primary = max(primary_values) if primary_values else 0.0
    fired = max_control >= max_primary and max_control >= CONTROL_ANOMALY_MIN_ACCURACY
    detail = (
        f"max(M2,M3)={max_control:.4f} vs max(M1,M4)={max_primary:.4f}, floor {CONTROL_ANOMALY_MIN_ACCURACY} -- "
    )
    if fired:
        detail += (
            "FIRED: a content-agnostic control (audio-TYPE or speaking-STYLE) matches or beats a "
            "content-aligned model on content routing -- the 'content semantics' claim is confounded"
        )
    else:
        detail += "not met"
    return fired, detail


@dataclass(frozen=True)
class Pemb3mVerdict:
    """Module docstring: M1 and M4 each carry their OWN independent label
    (never collapsed into a single any/every reduction, unlike ``analysis.
    pemb3l_read.evaluate_pemb3l_verdict``), plus the separately-fireable
    CONTROL-ANOMALY finding. ``overall`` is a single-line join of whichever
    of the three actually fired, or ``"INCONCLUSIVE-3M"`` if none did."""

    m1_label: str
    m1_detail: str
    m4_label: str
    m4_detail: str
    control_anomaly: bool
    control_anomaly_detail: str
    overall: str


def evaluate_pemb3m_verdict(
    *,
    m1_accuracy: float | None,
    m2_accuracy: float | None,
    m3_accuracy: float | None,
    m4_accuracy: float | None,
    pooling_override_present: bool,
) -> Pemb3mVerdict:
    m1_label, m1_detail = evaluate_m1_verdict(m1_accuracy, pooling_override_present=pooling_override_present)
    m4_label, m4_detail = evaluate_m4_verdict(m4_accuracy)
    control_anomaly, control_detail = evaluate_control_anomaly(
        m1_accuracy=m1_accuracy, m2_accuracy=m2_accuracy, m3_accuracy=m3_accuracy, m4_accuracy=m4_accuracy
    )
    fired = [label for label in (m1_label, m4_label) if not label.startswith("INCONCLUSIVE-3M")]
    if control_anomaly:
        fired.append("CONTROL-ANOMALY")
    overall = " + ".join(fired) if fired else "INCONCLUSIVE-3M"
    return Pemb3mVerdict(
        m1_label=m1_label,
        m1_detail=m1_detail,
        m4_label=m4_label,
        m4_detail=m4_detail,
        control_anomaly=control_anomaly,
        control_anomaly_detail=control_detail,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Per-arm report.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pemb3mArmPrediction:
    sample_id: str
    gold_scenario: str
    predicted_scenario: str
    top1_cosine: float
    top1_correct: bool


@dataclass(frozen=True)
class Pemb3mArmReport:
    arm_id: str
    manifest_run_id: str | None
    dropped: bool
    n_samples: int
    n_labels: int
    n_correct: int
    accuracy: float | None
    predictions: tuple[Pemb3mArmPrediction, ...]
    confusion: tuple[ConfusionCell, ...]
    attractor: AttractorStructure | None
    cosine_sign_profile: CosineSignProfile | None


def build_arm_report(
    arm_id: str,
    manifest: LoadedPemb3mManifest | None,
    gold_scenarios: Mapping[str, str],
    expected_labels: Sequence[str],
    *,
    expected_query_n: int = ARM_QUERY_N,
    expected_label_n: int = ARM_LABEL_N,
) -> Pemb3mArmReport:
    """Pure function of its inputs (module docstring: idempotent).
    ``manifest=None`` -- a DROPPED-DEPS control arm -- returns a
    ``dropped=True`` report with ``accuracy=None`` rather than raising."""

    if arm_id not in ARMS_BY_ID:
        raise Pemb3mReadError(f"build_arm_report: unknown arm_id {arm_id!r}, expected one of {ARM_IDS}")

    if manifest is None:
        return Pemb3mArmReport(
            arm_id=arm_id,
            manifest_run_id=None,
            dropped=True,
            n_samples=0,
            n_labels=0,
            n_correct=0,
            accuracy=None,
            predictions=(),
            confusion=(),
            attractor=None,
            cosine_sign_profile=None,
        )

    expected_run_id = arm_run_id(arm_id)
    if manifest.run_id != expected_run_id:
        raise Pemb3mReadError(f"manifest run_id {manifest.run_id!r} does not match arm {arm_id!r}'s expected {expected_run_id!r}")
    if len(manifest.query) != expected_query_n:
        raise Pemb3mReadError(f"manifest carries {len(manifest.query)} query vector(s), expected {expected_query_n}")
    if len(manifest.label) != expected_label_n:
        raise Pemb3mReadError(f"manifest carries {len(manifest.label)} label vector(s), expected {expected_label_n}")
    _assert_key_sets_equal(manifest.query.keys(), gold_scenarios.keys(), context=f"{arm_id} query ids vs gold scenarios")
    _assert_key_sets_equal(manifest.label.keys(), expected_labels, context=f"{arm_id} label ids vs canonical labels")

    predictions: list[Pemb3mArmPrediction] = []
    pairs: list[tuple[str, str]] = []
    predicted_labels: list[str] = []
    top1_cosines: list[float] = []
    n_correct = 0
    for sample_id in sorted(manifest.query):
        ranking = rank_cosine(manifest.query[sample_id], manifest.label)
        predicted_scenario, top1_cosine = ranking[0]
        gold_scenario = gold_scenarios[sample_id]
        correct = predicted_scenario == gold_scenario
        n_correct += int(correct)
        pairs.append((gold_scenario, predicted_scenario))
        predicted_labels.append(predicted_scenario)
        top1_cosines.append(top1_cosine)
        predictions.append(
            Pemb3mArmPrediction(
                sample_id=sample_id,
                gold_scenario=gold_scenario,
                predicted_scenario=predicted_scenario,
                top1_cosine=top1_cosine,
                top1_correct=correct,
            )
        )
    accuracy = n_correct / len(predictions)
    attractor = compute_attractor_structure(predicted_labels, n_labels_available=len(expected_labels))
    cosine_profile = compute_cosine_sign_profile(top1_cosines)
    return Pemb3mArmReport(
        arm_id=arm_id,
        manifest_run_id=manifest.run_id,
        dropped=False,
        n_samples=len(predictions),
        n_labels=len(manifest.label),
        n_correct=n_correct,
        accuracy=accuracy,
        predictions=tuple(predictions),
        confusion=build_confusion_table(pairs),
        attractor=attractor,
        cosine_sign_profile=cosine_profile,
    )


# ---------------------------------------------------------------------------
# Sweep-level report.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pemb3mSweepReport:
    arm_reports: Mapping[str, Pemb3mArmReport]
    cross_arm_agreement: tuple[CrossArmAgreement, ...]
    pooling_override_present: bool
    control_import_status: Mapping[str, str]
    cascade_source_status: str
    jitter: JitterToleranceResult | None
    verdict: Pemb3mVerdict


def build_pemb3m_sweep_report(
    arm_manifests: Mapping[str, LoadedPemb3mManifest | None],
    gold_scenarios: Mapping[str, str],
    expected_labels: Sequence[str],
    *,
    pooling_override_present: bool,
    control_import_status: Mapping[str, str],
    cascade_source_status: str,
    jitter_vectors: tuple[Sequence[float], Sequence[float]] | None = None,
    expected_query_n: int = ARM_QUERY_N,
    expected_label_n: int = ARM_LABEL_N,
) -> Pemb3mSweepReport:
    """Pure function of its inputs (module docstring: idempotent). Builds
    all four :func:`build_arm_report` reports (a missing key in
    ``arm_manifests`` is treated as ``None``, i.e. dropped), the cross-arm
    agreement structure over the non-dropped arms, the verdict, and --
    when ``jitter_vectors`` is supplied -- the M4 repeat-call jitter-
    tolerance evaluation against M4's own label vectors."""

    arm_reports = {
        arm_id: build_arm_report(
            arm_id,
            arm_manifests.get(arm_id),
            gold_scenarios,
            expected_labels,
            expected_query_n=expected_query_n,
            expected_label_n=expected_label_n,
        )
        for arm_id in ARM_IDS
    }
    predictions_by_arm = {
        arm_id: {prediction.sample_id: prediction.predicted_scenario for prediction in report.predictions}
        for arm_id, report in arm_reports.items()
        if not report.dropped
    }
    cross_arm = compute_cross_arm_agreement(predictions_by_arm)
    accuracies = {arm_id: report.accuracy for arm_id, report in arm_reports.items()}
    verdict = evaluate_pemb3m_verdict(
        m1_accuracy=accuracies[ARM_M1_ID],
        m2_accuracy=accuracies[ARM_M2_ID],
        m3_accuracy=accuracies[ARM_M3_ID],
        m4_accuracy=accuracies[ARM_M4_ID],
        pooling_override_present=pooling_override_present,
    )
    jitter_result: JitterToleranceResult | None = None
    if jitter_vectors is not None:
        m4_manifest = arm_manifests.get(ARM_M4_ID)
        if m4_manifest is None:
            raise Pemb3mReadError("build_pemb3m_sweep_report: jitter_vectors supplied but M4 manifest is missing")
        jitter_a, jitter_b = jitter_vectors
        jitter_result = evaluate_m4_jitter_tolerance(jitter_a, jitter_b, m4_manifest.label)

    return Pemb3mSweepReport(
        arm_reports=arm_reports,
        cross_arm_agreement=cross_arm,
        pooling_override_present=pooling_override_present,
        control_import_status=dict(control_import_status),
        cascade_source_status=cascade_source_status,
        jitter=jitter_result,
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# JSON / text rendering.
# ---------------------------------------------------------------------------


def _attractor_to_json(attractor: AttractorStructure | None) -> dict[str, object] | None:
    if attractor is None:
        return None
    return {
        "n_predictions": attractor.n_predictions,
        "n_labels_available": attractor.n_labels_available,
        "n_labels_predicted": attractor.n_labels_predicted,
        "top1_share": attractor.top1_share,
        "top2_share": attractor.top2_share,
        "shares": [{"label": share.label, "count": share.count, "share": share.share} for share in attractor.shares],
    }


def _cosine_profile_to_json(profile: CosineSignProfile | None) -> dict[str, object] | None:
    if profile is None:
        return None
    return {
        "n": profile.n,
        "n_positive": profile.n_positive,
        "n_negative": profile.n_negative,
        "n_zero": profile.n_zero,
        "positive_share": profile.positive_share,
        "mean_cosine": profile.mean_cosine,
        "max_cosine": profile.max_cosine,
        "min_cosine": profile.min_cosine,
    }


def _arm_report_to_json(report: Pemb3mArmReport) -> dict[str, object]:
    return {
        "arm_id": report.arm_id,
        "manifest_run_id": report.manifest_run_id,
        "dropped": report.dropped,
        "n_samples": report.n_samples,
        "n_labels": report.n_labels,
        "n_correct": report.n_correct,
        "accuracy": report.accuracy,
        "predictions": [
            {
                "sample_id": p.sample_id,
                "gold_scenario": p.gold_scenario,
                "predicted_scenario": p.predicted_scenario,
                "top1_cosine": p.top1_cosine,
                "top1_correct": p.top1_correct,
            }
            for p in report.predictions
        ],
        "confusion": [{"gold": c.gold, "predicted": c.predicted, "count": c.count} for c in report.confusion],
        "attractor": _attractor_to_json(report.attractor),
        "cosine_sign_profile": _cosine_profile_to_json(report.cosine_sign_profile),
    }


def sweep_report_to_json(report: Pemb3mSweepReport) -> dict[str, object]:
    return {
        "schema": REPORT_SCHEMA,
        "probe_id": "SAEA-PROBE-pemb3m-388",
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
        "pooling_override_present": report.pooling_override_present,
        "control_import_status": dict(report.control_import_status),
        "cascade_source_status": report.cascade_source_status,
        "jitter": (
            None
            if report.jitter is None
            else {
                "cosine": report.jitter.cosine,
                "within_tolerance": report.jitter.within_tolerance,
                "argmax_a": report.jitter.argmax_a,
                "argmax_b": report.jitter.argmax_b,
                "argmax_stable": report.jitter.argmax_stable,
            }
        ),
        "verdict": {
            "m1_label": report.verdict.m1_label,
            "m1_detail": report.verdict.m1_detail,
            "m4_label": report.verdict.m4_label,
            "m4_detail": report.verdict.m4_detail,
            "control_anomaly": report.verdict.control_anomaly,
            "control_anomaly_detail": report.verdict.control_anomaly_detail,
            "overall": report.verdict.overall,
        },
    }


def render_sweep_report(report: Pemb3mSweepReport) -> str:
    lines = [
        "P-EMB-3M pinned offline read (docs/readiness/2026-08-20-pemb3m-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
    ]
    for arm_id in ARM_IDS:
        arm_report = report.arm_reports[arm_id]
        if arm_report.dropped:
            lines.append(f"[{arm_id}] DROPPED-DEPS (status={report.control_import_status.get(arm_id, '?')})")
            continue
        lines.append(
            f"[{arm_id}] accuracy={arm_report.accuracy:.4f} ({arm_report.n_correct}/{arm_report.n_samples}) "
            f"top1_share={arm_report.attractor.top1_share:.4f} "
            f"positive_cosine_share={arm_report.cosine_sign_profile.positive_share:.4f}"
        )
    lines += [
        "",
        f"pooling_override_present={report.pooling_override_present}",
        f"cascade_source_status={report.cascade_source_status}",
    ]
    if report.jitter is not None:
        lines.append(
            f"M4 jitter: cosine={report.jitter.cosine:.6f} within_tolerance={report.jitter.within_tolerance} "
            f"argmax_stable={report.jitter.argmax_stable}"
        )
    lines += [
        "",
        f"[M1] {report.verdict.m1_label}",
        f"  {report.verdict.m1_detail}",
        f"[M4] {report.verdict.m4_label}",
        f"  {report.verdict.m4_detail}",
        f"[CONTROL-ANOMALY] {report.verdict.control_anomaly}",
        f"  {report.verdict.control_anomaly_detail}",
        "",
        f"[OVERALL] {report.verdict.overall}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pemb3m-read",
        description=(
            "P-EMB-3M pinned offline read suite: four-arm argmax-cosine sweep vs scoring-side gold, "
            "verdict evaluators exactly as registered, confusion/attractor tables, cross-arm "
            "agreement, cosine-sign profiles, M4 jitter tolerance. Model-free, read-only."
        ),
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--embeddings-root", type=Path, default=None)
    parser.add_argument("--sample-manifest", type=Path, default=None)
    parser.add_argument("--roster-table", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import REPO_ROOT, data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import write_json_artifact
    from ..rails.probes.pemb3m_flight import load_pemb3m_arm_manifest
    from .pemb_read import _refuse_if_already_run, canonical_scenario_labels, gold_scenarios_for_run_a

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    root = Path(args.embeddings_root) if args.embeddings_root else data_root()
    lock = load_lock(umbrella_lock_path(repo_root))

    output_dir = Path(args.output_dir)
    verdict_path = _refuse_if_already_run(output_dir)
    if verdict_path is None:
        return 1

    try:
        sample_manifest_path = args.sample_manifest or (repo_root / "configs/probes/g0-binding/pslu-sample-devel-n60.json")
        roster_table_path = args.roster_table or (repo_root / "configs/probes/g0-binding/pslu-rosters-train-only.json")
        gold = gold_scenarios_for_run_a(lock, root, repo_root=repo_root, sample_manifest_path=sample_manifest_path)
        labels = canonical_scenario_labels(roster_table_path)
        arm_manifests: dict[str, LoadedPemb3mManifest | None] = {}
        control_import_status: dict[str, str] = {}
        for arm_id in ARM_IDS:
            try:
                arm_manifests[arm_id] = load_pemb3m_arm_manifest(root, arm_id)
                control_import_status[arm_id] = "OK"
            except Pemb3mFlightError:
                arm_manifests[arm_id] = None
                control_import_status[arm_id] = "DROPPED-DEPS"
        report = build_pemb3m_sweep_report(
            arm_manifests,
            gold,
            labels,
            pooling_override_present=False,
            control_import_status=control_import_status,
            cascade_source_status="COMPLETE",
        )
        document = sweep_report_to_json(report)
        rendered = render_sweep_report(report)
    except (Pemb3mReadError, Pemb3lReadError, Pemb3mFlightError, PembReadError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    write_json_artifact(verdict_path, document)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    return 0


__all__ = [
    "CASCADE_ROUTES_MIN_ACCURACY",
    "CASCADE_WEAK_MAX_ACCURACY",
    "CONTROL_ANOMALY_MIN_ACCURACY",
    "EMB_ROUTES_MIN_ACCURACY",
    "EMB_WEAK_MAX_ACCURACY",
    "JITTER_COSINE_TOLERANCE",
    "REPORT_SCHEMA",
    "CosineSignProfile",
    "CrossArmAgreement",
    "JitterToleranceResult",
    "Pemb3mArmPrediction",
    "Pemb3mArmReport",
    "Pemb3mReadError",
    "Pemb3mSweepReport",
    "Pemb3mVerdict",
    "build_arm_report",
    "build_pemb3m_sweep_report",
    "compute_cosine_sign_profile",
    "compute_cross_arm_agreement",
    "evaluate_control_anomaly",
    "evaluate_m1_verdict",
    "evaluate_m4_jitter_tolerance",
    "evaluate_m4_verdict",
    "evaluate_pemb3m_verdict",
    "main",
    "render_sweep_report",
    "sweep_report_to_json",
]
