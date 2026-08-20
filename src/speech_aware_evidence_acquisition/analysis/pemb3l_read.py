"""P-EMB-3L pinned offline read suite (pre-registered, SAEA-PROBE-pemb3l-234):
``docs/readiness/2026-08-20-pemb3l-preregistration-REGISTERED.md``.

Model-free, read-only, sibling of ``analysis.pemb_read`` (this suite must be
built and coordinator-reviewed BEFORE the read, prereg section 5): loads the
three already-written per-arm embedding-vector manifests
(``rails.probes.pemb3l_flight.write_pemb3l_arm_manifest``'s own shape, via
:func:`~rails.probes.pemb3l_flight.load_pemb3l_arm_manifest`, reused
directly) and scores each with the SAME pure argmax-cosine matcher
``analysis.pemb_read`` already established
(:func:`~analysis.pemb_read.rank_cosine` /
:func:`~analysis.pemb_read.cosine_similarity` /
:func:`~analysis.pemb_read.build_confusion_table`, all reused verbatim --
never a second cosine implementation) against SCORING-SIDE-ONLY gold.

Gold sourcing (never a second, independently-authored gold path): both
:func:`~analysis.pemb_read.gold_scenarios_for_run_a` and
:func:`~analysis.pemb_read.canonical_scenario_labels` are reused directly --
the P-EMB-3L surface is the SAME frozen 60-sample/18-label P-EMB-1 surface
(module docstring of ``rails.probes.pemb3l_flight``), so this suite never
re-derives gold or the canonical label roster a second way.

Attractor structure (:func:`compute_attractor_structure`): the per-arm
predicted-label distribution, generalizing the descriptive collapse analysis
``docs/readiness/2026-08-19-pemb1-verdict.md`` section 2 performed by hand
("the argmax collapses onto two attractor labels ... 29 + 26 = 55/60") into
a reusable, per-arm computation -- reported alongside each arm's accuracy,
never folded into any verdict clause.

Verdict (:func:`evaluate_pemb3l_verdict`) implements the registered
thresholds VERBATIM (prereg section 3): **LOCAL-SPACE-EXISTS** if ANY arm's
accuracy >= 0.30, **LOCAL-EXHAUSTED** if EVERY arm's accuracy <= 0.15,
otherwise **INCONCLUSIVE-EMB3L** -- a pure function over already-computed
per-arm accuracies, independently unit-testable against every branch
including both threshold boundaries.

L3-vs-cited-mean-bare common-mode delta (prereg section 3, "the prefix
common-mode effect"): :func:`build_pemb3l_sweep_report` subtracts
``rails.probes.pemb3l_flight.CITED_MEAN_BARE_ACCURACY`` (the CITED,
already-consumed P-EMB-1 mean-pooled/no-instruction accuracy, 0.0500) from
L3's OWN freshly-measured accuracy (mean pooling, WITH the instruct prefix)
-- holding pooling mode (mean) common between the two numbers so the delta
isolates the prefix's own effect, never a re-embedding of the bare
construction.

Idempotence: :func:`build_arm_report`/:func:`build_pemb3l_sweep_report` are
pure functions of their inputs (no I/O, no mutation, no randomness) --
calling either twice against the SAME manifest/gold produces byte-identical
(dataclass-equal) reports; the CLI (:func:`main`) reuses ``analysis.
pemb_read._refuse_if_already_run`` verbatim (one-shot read discipline, the
SAME ``verdict.json``-exists guard every sibling read CLI uses).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..rails.probes.pemb3l_flight import (
    ARM_AUDIO_N,
    ARM_IDS,
    ARM_L3_ID,
    ARM_LABEL_N,
    ARMS_BY_ID,
    CITED_MEAN_BARE_ACCURACY,
    Pemb3lFlightError,
    arm_run_id,
)
from ..rails.probes.pemb_flight import LoadedEmbeddingManifest, PembFlightError
from .pemb_read import (
    ConfusionCell,
    PembReadError,
    _assert_key_sets_equal,
    build_confusion_table,
    rank_cosine,
)

REPORT_SCHEMA = "saea-pemb3l-read-v1"

# Registered thresholds (prereg section 3, quoted verbatim in
# evaluate_pemb3l_verdict's own detail text below).
LOCAL_SPACE_EXISTS_MIN_ACCURACY = 0.30
LOCAL_EXHAUSTED_MAX_ACCURACY = 0.15


class Pemb3lReadError(RuntimeError):
    """A manifest/gold input is malformed, an id-set mismatch is detected,
    or a harness-defect fail-closed check tripped -- never raised for an
    ordinary, structurally clean read."""


# ---------------------------------------------------------------------------
# Attractor structure -- generalizes the P-EMB-1 verdict's own by-hand
# confusion-collapse read into a per-arm, reusable computation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LabelPredictionShare:
    label: str
    count: int
    share: float


@dataclass(frozen=True)
class AttractorStructure:
    n_predictions: int
    n_labels_available: int
    n_labels_predicted: int
    shares: tuple[LabelPredictionShare, ...]  # sorted count DESC, label ASC
    top1_share: float
    top2_share: float


def compute_attractor_structure(predicted_labels: Sequence[str], *, n_labels_available: int) -> AttractorStructure:
    """The predicted-label distribution over ``predicted_labels`` -- ``top1_
    share``/``top2_share`` are the fraction of ALL predictions absorbed by
    the single most- / two most-predicted labels respectively (the P-EMB-1
    verdict's own ``general``+``play`` = 91.7% figure, generalized). Refuses
    an empty ``predicted_labels`` (a report with zero samples is a harness
    defect, never a legitimate arm read)."""

    if not predicted_labels:
        raise Pemb3lReadError("compute_attractor_structure: predicted_labels must be non-empty")
    if n_labels_available <= 0:
        raise Pemb3lReadError("compute_attractor_structure: n_labels_available must be positive")

    counts: dict[str, int] = {}
    for label in predicted_labels:
        counts[label] = counts.get(label, 0) + 1
    n = len(predicted_labels)
    shares = tuple(
        LabelPredictionShare(label=label, count=count, share=count / n)
        for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    )
    top1_share = shares[0].share if shares else 0.0
    top2_share = sum(share.share for share in shares[:2])
    return AttractorStructure(
        n_predictions=n,
        n_labels_available=n_labels_available,
        n_labels_predicted=len(shares),
        shares=shares,
        top1_share=top1_share,
        top2_share=top2_share,
    )


# ---------------------------------------------------------------------------
# Verdict evaluator.
# ---------------------------------------------------------------------------


def evaluate_pemb3l_verdict(arm_accuracies: Mapping[str, float]) -> tuple[str, str]:
    """LOCAL-SPACE-EXISTS / LOCAL-EXHAUSTED / INCONCLUSIVE-EMB3L, prereg
    section 3 verbatim, with margins against whichever clause came closest
    to firing. Requires exactly the three registered arm ids as keys (fail-
    closed on a missing arm -- a partial sweep must never silently produce a
    verdict)."""

    missing = [arm_id for arm_id in ARM_IDS if arm_id not in arm_accuracies]
    if missing:
        raise Pemb3lReadError(f"evaluate_pemb3l_verdict: missing accuracy for arm(s) {missing}")
    extra = [arm_id for arm_id in arm_accuracies if arm_id not in ARMS_BY_ID]
    if extra:
        raise Pemb3lReadError(f"evaluate_pemb3l_verdict: unknown arm id(s) {extra}")

    best_arm_id, best_accuracy = max(arm_accuracies.items(), key=lambda item: (item[1], item[0]))

    if best_accuracy >= LOCAL_SPACE_EXISTS_MIN_ACCURACY:
        margin = best_accuracy - LOCAL_SPACE_EXISTS_MIN_ACCURACY
        return "LOCAL-SPACE-EXISTS", (
            f"{best_arm_id} accuracy {best_accuracy:.4f} >= {LOCAL_SPACE_EXISTS_MIN_ACCURACY} "
            f"(margin +{margin:.4f}) -- a usable training-free space exists on the local core; the "
            f"winning construction ({best_arm_id}) advances and external-embedder adoption is "
            "deferred"
        )
    if best_accuracy <= LOCAL_EXHAUSTED_MAX_ACCURACY:
        margin = LOCAL_EXHAUSTED_MAX_ACCURACY - best_accuracy
        detail_accuracies = ", ".join(f"{arm_id}={arm_accuracies[arm_id]:.4f}" for arm_id in ARM_IDS)
        return "LOCAL-EXHAUSTED", (
            f"every arm's accuracy <= {LOCAL_EXHAUSTED_MAX_ACCURACY} (best: {best_arm_id}="
            f"{best_accuracy:.4f}, margin {margin:.4f} below the ceiling; all: {detail_accuracies}) "
            "-- the local core's training-free constructions are exhausted; the external "
            "dedicated-embedder path becomes the routing-tier's representation instrument"
        )
    return "INCONCLUSIVE-EMB3L", (
        f"best arm {best_arm_id}={best_accuracy:.4f} falls strictly between "
        f"{LOCAL_EXHAUSTED_MAX_ACCURACY} and {LOCAL_SPACE_EXISTS_MIN_ACCURACY} -- neither threshold "
        "met; report the per-arm accuracies and attractor structure"
    )


# ---------------------------------------------------------------------------
# Per-arm report.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pemb3lArmPrediction:
    sample_id: str
    gold_scenario: str
    predicted_scenario: str
    top1_cosine: float
    top1_correct: bool


@dataclass(frozen=True)
class Pemb3lArmReport:
    arm_id: str
    manifest_run_id: str
    n_samples: int
    n_labels: int
    n_correct: int
    accuracy: float
    predictions: tuple[Pemb3lArmPrediction, ...]
    confusion: tuple[ConfusionCell, ...]
    attractor: AttractorStructure


def build_arm_report(
    arm_id: str,
    manifest: LoadedEmbeddingManifest,
    gold_scenarios: Mapping[str, str],
    expected_labels: Sequence[str],
    *,
    expected_audio_n: int = ARM_AUDIO_N,
    expected_label_n: int = ARM_LABEL_N,
) -> Pemb3lArmReport:
    """Pure function of its inputs (module docstring: idempotent). Argmax-
    cosine per sample, reusing ``analysis.pemb_read.rank_cosine`` verbatim --
    the SAME matcher every sibling P-EMB read uses."""

    if arm_id not in ARMS_BY_ID:
        raise Pemb3lReadError(f"build_arm_report: unknown arm_id {arm_id!r}, expected one of {ARM_IDS}")
    expected_run_id = arm_run_id(arm_id)
    if manifest.run_id != expected_run_id:
        raise Pemb3lReadError(
            f"manifest run_id {manifest.run_id!r} does not match arm {arm_id!r}'s expected "
            f"{expected_run_id!r}"
        )
    if len(manifest.audio) != expected_audio_n:
        raise Pemb3lReadError(f"manifest carries {len(manifest.audio)} audio vector(s), expected {expected_audio_n}")
    if len(manifest.text) != expected_label_n:
        raise Pemb3lReadError(f"manifest carries {len(manifest.text)} text vector(s), expected {expected_label_n}")
    _assert_key_sets_equal(manifest.audio.keys(), gold_scenarios.keys(), context=f"{arm_id} audio ids vs gold scenarios")
    _assert_key_sets_equal(manifest.text.keys(), expected_labels, context=f"{arm_id} text ids vs canonical labels")

    predictions: list[Pemb3lArmPrediction] = []
    pairs: list[tuple[str, str]] = []
    predicted_labels: list[str] = []
    n_correct = 0
    for sample_id in sorted(manifest.audio):
        ranking = rank_cosine(manifest.audio[sample_id], manifest.text)
        predicted_scenario, top1_cosine = ranking[0]
        gold_scenario = gold_scenarios[sample_id]
        correct = predicted_scenario == gold_scenario
        n_correct += int(correct)
        pairs.append((gold_scenario, predicted_scenario))
        predicted_labels.append(predicted_scenario)
        predictions.append(
            Pemb3lArmPrediction(
                sample_id=sample_id,
                gold_scenario=gold_scenario,
                predicted_scenario=predicted_scenario,
                top1_cosine=top1_cosine,
                top1_correct=correct,
            )
        )
    accuracy = n_correct / len(predictions)
    attractor = compute_attractor_structure(predicted_labels, n_labels_available=len(expected_labels))
    return Pemb3lArmReport(
        arm_id=arm_id,
        manifest_run_id=manifest.run_id,
        n_samples=len(predictions),
        n_labels=len(manifest.text),
        n_correct=n_correct,
        accuracy=accuracy,
        predictions=tuple(predictions),
        confusion=build_confusion_table(pairs),
        attractor=attractor,
    )


# ---------------------------------------------------------------------------
# Sweep-level report (all three arms + verdict + L3-vs-cited delta).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pemb3lSweepReport:
    arm_reports: Mapping[str, Pemb3lArmReport]  # arm_id -> report, one entry per ARM_IDS
    cited_mean_bare_accuracy: float
    l3_accuracy: float
    l3_vs_cited_mean_bare_delta: float
    verdict: str
    verdict_detail: str


def build_pemb3l_sweep_report(
    arm_manifests: Mapping[str, LoadedEmbeddingManifest],
    gold_scenarios: Mapping[str, str],
    expected_labels: Sequence[str],
    *,
    expected_audio_n: int = ARM_AUDIO_N,
    expected_label_n: int = ARM_LABEL_N,
) -> Pemb3lSweepReport:
    """Pure function of its inputs (module docstring: idempotent). Builds
    all three :func:`build_arm_report` reports, evaluates
    :func:`evaluate_pemb3l_verdict` over their accuracies, and computes the
    L3-vs-cited-mean-bare common-mode delta from
    ``rails.probes.pemb3l_flight.CITED_MEAN_BARE_ACCURACY`` (never a fourth
    embedding contact)."""

    missing = [arm_id for arm_id in ARM_IDS if arm_id not in arm_manifests]
    if missing:
        raise Pemb3lReadError(f"build_pemb3l_sweep_report: missing manifest for arm(s) {missing}")

    arm_reports = {
        arm_id: build_arm_report(
            arm_id,
            arm_manifests[arm_id],
            gold_scenarios,
            expected_labels,
            expected_audio_n=expected_audio_n,
            expected_label_n=expected_label_n,
        )
        for arm_id in ARM_IDS
    }
    accuracies = {arm_id: report.accuracy for arm_id, report in arm_reports.items()}
    verdict, detail = evaluate_pemb3l_verdict(accuracies)

    l3_accuracy = arm_reports[ARM_L3_ID].accuracy
    delta = l3_accuracy - CITED_MEAN_BARE_ACCURACY

    return Pemb3lSweepReport(
        arm_reports=dict(arm_reports),
        cited_mean_bare_accuracy=CITED_MEAN_BARE_ACCURACY,
        l3_accuracy=l3_accuracy,
        l3_vs_cited_mean_bare_delta=delta,
        verdict=verdict,
        verdict_detail=detail,
    )


# ---------------------------------------------------------------------------
# JSON / text rendering.
# ---------------------------------------------------------------------------


def _attractor_to_json(attractor: AttractorStructure) -> dict[str, object]:
    return {
        "n_predictions": attractor.n_predictions,
        "n_labels_available": attractor.n_labels_available,
        "n_labels_predicted": attractor.n_labels_predicted,
        "top1_share": attractor.top1_share,
        "top2_share": attractor.top2_share,
        "shares": [
            {"label": share.label, "count": share.count, "share": share.share} for share in attractor.shares
        ],
    }


def _arm_report_to_json(report: Pemb3lArmReport) -> dict[str, object]:
    return {
        "arm_id": report.arm_id,
        "manifest_run_id": report.manifest_run_id,
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
    }


def sweep_report_to_json(report: Pemb3lSweepReport) -> dict[str, object]:
    return {
        "schema": REPORT_SCHEMA,
        "probe_id": "SAEA-PROBE-pemb3l-234",
        "arms": {arm_id: _arm_report_to_json(arm_report) for arm_id, arm_report in report.arm_reports.items()},
        "cited_mean_bare_accuracy": report.cited_mean_bare_accuracy,
        "l3_accuracy": report.l3_accuracy,
        "l3_vs_cited_mean_bare_delta": report.l3_vs_cited_mean_bare_delta,
        "verdict": report.verdict,
        "verdict_detail": report.verdict_detail,
    }


def render_sweep_report(report: Pemb3lSweepReport) -> str:
    lines = [
        "P-EMB-3L pinned offline read (docs/readiness/2026-08-20-pemb3l-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
    ]
    for arm_id in ARM_IDS:
        arm_report = report.arm_reports[arm_id]
        lines.append(
            f"[{arm_id}] accuracy={arm_report.accuracy:.4f} ({arm_report.n_correct}/{arm_report.n_samples}) "
            f"top1_share={arm_report.attractor.top1_share:.4f} top2_share={arm_report.attractor.top2_share:.4f} "
            f"n_labels_predicted={arm_report.attractor.n_labels_predicted}/{arm_report.attractor.n_labels_available}"
        )
    lines += [
        "",
        f"cited mean-bare accuracy (P-EMB-1, consumed): {report.cited_mean_bare_accuracy:.4f}",
        f"L3 (mean-instruct) accuracy: {report.l3_accuracy:.4f}",
        f"L3 vs cited mean-bare delta: {report.l3_vs_cited_mean_bare_delta:+.4f}",
        "",
        f"[{report.verdict}]",
        f"  {report.verdict_detail}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pemb3l-read",
        description=(
            "P-EMB-3L pinned offline read suite: three-arm argmax-cosine sweep vs scoring-side "
            "gold, verdict evaluator exactly as registered, attractor structure, L3-vs-cited-"
            "mean-bare delta. Model-free, read-only; never opens a model session."
        ),
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--embeddings-root", type=Path, default=None, help="override the data root (default: SPEECHRL_DATA_DIR)")
    parser.add_argument("--sample-manifest", type=Path, default=None)
    parser.add_argument("--roster-table", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import REPO_ROOT, data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import write_json_artifact
    from ..rails.probes.pemb3l_flight import ARM_IDS as _ARM_IDS
    from ..rails.probes.pemb3l_flight import load_pemb3l_arm_manifest
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
        sample_manifest_path = args.sample_manifest or (
            repo_root / "configs/probes/g0-binding/pslu-sample-devel-n60.json"
        )
        roster_table_path = args.roster_table or (
            repo_root / "configs/probes/g0-binding/pslu-rosters-train-only.json"
        )
        gold = gold_scenarios_for_run_a(lock, root, repo_root=repo_root, sample_manifest_path=sample_manifest_path)
        labels = canonical_scenario_labels(roster_table_path)
        arm_manifests = {arm_id: load_pemb3l_arm_manifest(root, arm_id) for arm_id in _ARM_IDS}
        report = build_pemb3l_sweep_report(arm_manifests, gold, labels)
        document = sweep_report_to_json(report)
        rendered = render_sweep_report(report)
    except (Pemb3lReadError, Pemb3lFlightError, PembReadError, PembFlightError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    write_json_artifact(verdict_path, document)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    return 0


__all__ = [
    "LOCAL_EXHAUSTED_MAX_ACCURACY",
    "LOCAL_SPACE_EXISTS_MIN_ACCURACY",
    "REPORT_SCHEMA",
    "AttractorStructure",
    "LabelPredictionShare",
    "Pemb3lArmPrediction",
    "Pemb3lArmReport",
    "Pemb3lReadError",
    "Pemb3lSweepReport",
    "build_arm_report",
    "build_pemb3l_sweep_report",
    "compute_attractor_structure",
    "evaluate_pemb3l_verdict",
    "main",
    "render_sweep_report",
    "sweep_report_to_json",
]
