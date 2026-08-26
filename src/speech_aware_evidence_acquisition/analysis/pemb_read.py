"""P-EMB pinned offline read suite (pre-registered, SAEA-PROBE-pemb1-78 /
SAEA-PROBE-pemb2-552): ``docs/readiness/2026-08-19-pemb-preregistration-
REGISTERED.md``.

Model-free, read-only: this module never opens a model session and never
mutates a manifest -- it loads an already-written embedding-vector manifest
(``rails.probes.pemb_flight.write_embedding_manifest``'s own shape, via
:func:`~rails.probes.pemb_flight.load_embedding_manifest`, reused directly)
and scores it with a pure argmax-cosine matcher against SCORING-SIDE-ONLY
gold, exactly as pre-registered (prereg section 5: "pinned suite ...
cosine matcher + verdict evaluators + confusion tables ... built ...
BEFORE the reads").

Gold sourcing, EACH reused from the exact consuming suite (never a second,
independently-authored gold path):

- Run A gold scenarios: :func:`gold_scenarios_for_run_a` reuses
  ``rails.adapters.slurp.SlurpAdapter.load_split('devel')`` filtered to the
  frozen 60-id manifest via ``rails.probes.pslu_flight.
  load_pslu_sample_manifest``/``select_pslu_samples`` (the SAME reuse the
  consumed P-KEY/P-SLU suites already established), reading each sample's
  own ``.scenario`` field -- loader-legal gold, never rendered into any
  prompt (``rails.adapters.slurp`` module docstring).
- Run A canonical labels: :func:`canonical_scenario_labels` reuses
  ``rails.probes.pslu_flight.load_pslu_rosters``'s own scenario-roster keys
  -- never the ceiling-tier ontology miner.
- Run B gold tools: :func:`gold_tools_for_run_b` reuses
  ``data.audio2tool.load_expected_calls`` (scorer-side-only, D2-legal).
  ENGINEERING-INTERPRETATION NOTE: ``reproduction.toolcall_scoring``'s own
  Tool Accuracy predicate is a MULTISET match (predicted tool-name multiset
  == expected tool-name multiset); an embedding argmax router can only ever
  name ONE tool per contact, so this suite's own top-1-correct predicate is
  "the argmax tool name is a MEMBER of that sample's own expected tool-name
  SET" -- the natural single-choice analog of the multiset predicate, never
  a re-derivation of a different metric.
- Run B's 183/217 tool-wrong/tool-correct partition: :func:`resolve_a0_attempt_dir`
  reuses ``rails.probes.a2t_pop_flight.load_headroom_source``/
  ``assert_split_identity_hash_pinned`` to locate and pin the SAME consumed
  A0 attempt ``rails.probes.a2t_pop_flight`` itself sourced its own 97-id
  EM-correct roster from; :func:`derive_tool_correct_partition` then reuses
  ``analysis.a2t_read.load_attempt_rows``/``score_row`` (the SAME frozen
  scorer, never a second implementation) over that SAME attempt, partitioned
  on ``tool_accuracy`` alone (this suite's own axis).

Cosine matcher (prereg: "cosine = dot" under L2-normalization; this module
computes the FULL cosine ratio rather than assuming normalization, so a
drifted/unnormalized stored vector still scores correctly rather than
silently under/over-weighting): :func:`cosine_similarity` /
:func:`rank_cosine`. Verdict evaluators (:func:`evaluate_run_a_verdict` /
:func:`evaluate_run_b_verdict`) implement the registered thresholds
VERBATIM (prereg sections 2-3) and are pure functions over already-computed
aggregates -- independently unit-testable against fixtures for every branch.

Idempotence: :func:`build_run_a_report`/:func:`build_run_b_report` are pure
functions of their inputs (no I/O, no mutation, no randomness) -- calling
either twice against the SAME manifest/gold produces byte-identical
(dataclass-equal) reports; the CLI (:func:`main`) additionally refuses to
run twice against the same ``--output-dir`` (one-shot read discipline,
mirrors ``analysis.pkey_read.main``'s own ``verdict.json``-exists guard).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ..rails.probes.pemb_flight import (
    RUN_A_AUDIO_N,
    RUN_A_ID,
    RUN_A_LABEL_N,
    RUN_B_AUDIO_N,
    RUN_B_ID,
    RUN_B_ROW_N,
    LoadedEmbeddingManifest,
    PembFlightError,
    load_embedding_manifest,
)

REPORT_SCHEMA_RUN_A = "saea-pemb1-read-v1"
REPORT_SCHEMA_RUN_B = "saea-pemb2-read-v1"

# Registered thresholds (prereg sections 2-3, quoted verbatim in each
# clause's own detail text below).
EMB_ROUTES_MIN_ACCURACY = 0.65
EMB_WEAK_MAX_ACCURACY = 0.30

EMB_OPENS_183_MIN_TOP1 = 0.30
EMB_OPENS_183_MIN_RECOVERIES = 55
EMB_CLOSED_MAX_TOP1 = 0.10

TOOL_CORRECT_N = 217  # the 217/400 non-degradation population
TOOL_WRONG_N = 183  # the 183/400 headline recovery population
DEFAULT_TOP_K = 5
DEFAULT_CONFUSION_LIMIT = 25


class PembReadError(RuntimeError):
    """A manifest/gold input is malformed, an id-set mismatch is detected,
    or a harness-defect fail-closed check tripped -- never raised for an
    ordinary, structurally clean read."""


# ---------------------------------------------------------------------------
# Cosine matcher.
# ---------------------------------------------------------------------------


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """The full cosine ratio (dot / (||a|| * ||b||)), not a bare dot
    product: correct regardless of whether a stored vector is exactly
    L2-normalized (the prereg's "cosine = dot" is a CONSEQUENCE of
    normalization at write time, never trusted blindly here)."""

    import numpy as np

    va = np.asarray(a, dtype=np.float64)
    vb = np.asarray(b, dtype=np.float64)
    norm_a = float(np.linalg.norm(va))
    norm_b = float(np.linalg.norm(vb))
    if norm_a == 0.0 or norm_b == 0.0:
        raise PembReadError("cosine_similarity: zero-norm vector cannot be compared")
    return float(np.dot(va, vb) / (norm_a * norm_b))


def rank_cosine(
    query: Sequence[float], candidates: Mapping[str, Sequence[float]]
) -> tuple[tuple[str, float], ...]:
    """Every ``(candidate_id, cosine)`` pair against ``query``, sorted by
    similarity DESCENDING then ``candidate_id`` ASCENDING (a deterministic
    tie-break -- this matcher never depends on dict iteration order).
    ``ranking[0]`` is the argmax top-1 prediction; ``ranking[:k]`` is the
    top-k set Run B's non-clause axis reports."""

    if not candidates:
        raise PembReadError("rank_cosine: candidates must be non-empty")
    scored = [(candidate_id, cosine_similarity(query, vector)) for candidate_id, vector in candidates.items()]
    scored.sort(key=lambda pair: (-pair[1], pair[0]))
    return tuple(scored)


# ---------------------------------------------------------------------------
# Confusion table (shared shape, both runs).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfusionCell:
    gold: str
    predicted: str
    count: int


def build_confusion_table(pairs: Iterable[tuple[str, str]], *, limit: int | None = None) -> tuple[ConfusionCell, ...]:
    """``(gold, predicted)`` pair counts, sorted by count DESCENDING then
    ``(gold, predicted)`` ASCENDING -- deterministic regardless of input
    order. ``limit`` (default ``None`` = every cell) caps the returned
    table for a compact report; the caller always has the ``pairs`` input
    available for a fuller reconstruction."""

    counts: dict[tuple[str, str], int] = {}
    for gold, predicted in pairs:
        key = (gold, predicted)
        counts[key] = counts.get(key, 0) + 1
    cells = tuple(
        ConfusionCell(gold=gold, predicted=predicted, count=count)
        for (gold, predicted), count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    )
    return cells if limit is None else cells[:limit]


def _assert_key_sets_equal(actual: Iterable[str], expected: Iterable[str], *, context: str) -> None:
    actual_set = set(actual)
    expected_set = set(expected)
    if actual_set != expected_set:
        missing = sorted(expected_set - actual_set)
        extra = sorted(actual_set - expected_set)
        raise PembReadError(
            f"{context}: id sets disagree (missing={missing[:5]}{'...' if len(missing) > 5 else ''}, "
            f"extra={extra[:5]}{'...' if len(extra) > 5 else ''})"
        )


# ---------------------------------------------------------------------------
# Run A -- SLURP scenario routing gold + report.
# ---------------------------------------------------------------------------


def gold_scenarios_for_run_a(
    lock: Mapping[str, object], root: Path, *, repo_root: Path, sample_manifest_path: Path
) -> dict[str, str]:
    """Scoring-side gold scenario per sample id, sourced the SAME way the
    consumed P-SLU/P-KEY suites do (module docstring)."""

    from ..rails.adapters.slurp import SlurpAdapter
    from ..rails.probes.pslu_flight import load_pslu_sample_manifest, select_pslu_samples

    adapter = SlurpAdapter(lock, root, repo_root=repo_root)
    manifest = load_pslu_sample_manifest(Path(sample_manifest_path))
    samples = select_pslu_samples(adapter.load_split("devel"), manifest)
    return {sample.sample_id: sample.scenario for sample in samples}


def canonical_scenario_labels(roster_table_path: Path) -> tuple[str, ...]:
    """The 18 bare canonical scenario labels -- the roster table's own
    scenario-roster keys, sorted (module docstring: never the ontology
    miner)."""

    from ..rails.probes.pslu_flight import load_pslu_rosters

    rosters = load_pslu_rosters(Path(roster_table_path))
    return tuple(sorted(rosters.scenario_rosters.keys()))


def evaluate_run_a_verdict(accuracy: float) -> tuple[str, str]:
    """EMB-ROUTES / EMB-WEAK / INCONCLUSIVE-EMB1, prereg section 2 verbatim."""

    if accuracy >= EMB_ROUTES_MIN_ACCURACY:
        return "EMB-ROUTES", (
            f"accuracy {accuracy:.4f} >= {EMB_ROUTES_MIN_ACCURACY} (within ~0.13 of the closed-set "
            "decode router, A1'r 47/60=0.7833) -- the embedding tier is a viable router at a "
            "fraction of the decode cost"
        )
    if accuracy <= EMB_WEAK_MAX_ACCURACY:
        return "EMB-WEAK", (
            f"accuracy {accuracy:.4f} <= {EMB_WEAK_MAX_ACCURACY} -- bare cross-modal matching does "
            "not form a usable shared space on this core; the routing tier stays decode-based"
        )
    return "INCONCLUSIVE-EMB1", (
        f"accuracy {accuracy:.4f} falls strictly between {EMB_WEAK_MAX_ACCURACY} and "
        f"{EMB_ROUTES_MIN_ACCURACY} -- neither threshold met; report the confusion structure"
    )


@dataclass(frozen=True)
class PembRunAPrediction:
    sample_id: str
    gold_scenario: str
    predicted_scenario: str
    top1_cosine: float
    top1_correct: bool


@dataclass(frozen=True)
class PembRunAReport:
    manifest_run_id: str
    n_samples: int
    n_labels: int
    n_correct: int
    accuracy: float
    predictions: tuple[PembRunAPrediction, ...]
    confusion: tuple[ConfusionCell, ...]
    verdict: str
    verdict_detail: str


def build_run_a_report(
    manifest: LoadedEmbeddingManifest,
    gold_scenarios: Mapping[str, str],
    expected_labels: Sequence[str],
    *,
    expected_audio_n: int = RUN_A_AUDIO_N,
    expected_label_n: int = RUN_A_LABEL_N,
) -> PembRunAReport:
    """Pure function of its three inputs (module docstring: idempotent)."""

    if manifest.run_id != RUN_A_ID:
        raise PembReadError(f"manifest run_id {manifest.run_id!r} does not match Run A's {RUN_A_ID!r}")
    if len(manifest.audio) != expected_audio_n:
        raise PembReadError(f"manifest carries {len(manifest.audio)} audio vector(s), expected {expected_audio_n}")
    if len(manifest.text) != expected_label_n:
        raise PembReadError(f"manifest carries {len(manifest.text)} text vector(s), expected {expected_label_n}")
    _assert_key_sets_equal(manifest.audio.keys(), gold_scenarios.keys(), context="Run A audio ids vs gold scenarios")
    _assert_key_sets_equal(manifest.text.keys(), expected_labels, context="Run A text ids vs canonical labels")

    predictions: list[PembRunAPrediction] = []
    pairs: list[tuple[str, str]] = []
    n_correct = 0
    for sample_id in sorted(manifest.audio):
        ranking = rank_cosine(manifest.audio[sample_id], manifest.text)
        predicted_scenario, top1_cosine = ranking[0]
        gold_scenario = gold_scenarios[sample_id]
        correct = predicted_scenario == gold_scenario
        n_correct += int(correct)
        pairs.append((gold_scenario, predicted_scenario))
        predictions.append(
            PembRunAPrediction(
                sample_id=sample_id,
                gold_scenario=gold_scenario,
                predicted_scenario=predicted_scenario,
                top1_cosine=top1_cosine,
                top1_correct=correct,
            )
        )
    accuracy = n_correct / len(predictions)
    verdict, detail = evaluate_run_a_verdict(accuracy)
    return PembRunAReport(
        manifest_run_id=manifest.run_id,
        n_samples=len(predictions),
        n_labels=len(manifest.text),
        n_correct=n_correct,
        accuracy=accuracy,
        predictions=tuple(predictions),
        confusion=build_confusion_table(pairs),
        verdict=verdict,
        verdict_detail=detail,
    )


# ---------------------------------------------------------------------------
# Run B -- Audio2Tool tool routing gold + 183/217 partition + report.
# ---------------------------------------------------------------------------


def gold_tools_for_run_b(
    lock: Mapping[str, object], root: Path, *, repo_root: Path
) -> dict[str, frozenset[str]]:
    """Scoring-side gold tool-name SET per sample id (module docstring
    ENGINEERING-INTERPRETATION NOTE: a set, not the raw ``ToolCall`` tuple,
    since this suite's own predicate is set-membership)."""

    from ..data.audio2tool import load_expected_calls

    expected = load_expected_calls(lock, root, repo_root=repo_root)
    return {sample_id: frozenset(call.name for call in calls) for sample_id, calls in expected.items()}


def resolve_a0_attempt_dir(headroom_json_path: Path) -> Path:
    """The consumed A0 attempt directory Run B's 183/217 partition must be
    derived from -- reuses ``rails.probes.a2t_pop_flight.
    load_headroom_source``/``assert_split_identity_hash_pinned`` VERBATIM
    (module docstring: the SAME attempt ``a2t_pop_flight`` itself sourced
    its own 97-id EM-correct roster from), never a second path to the same
    fact."""

    from ..rails.probes.a2t_pop_flight import assert_split_identity_hash_pinned, load_headroom_source

    source = load_headroom_source(Path(headroom_json_path))
    assert_split_identity_hash_pinned(source.split_identity_hash)
    return Path(source.attempt_dir)


def derive_tool_correct_partition(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path,
    expected_correct_n: int = TOOL_CORRECT_N,
    expected_wrong_n: int = TOOL_WRONG_N,
) -> tuple[frozenset[str], frozenset[str]]:
    """``(tool_correct_ids, tool_wrong_ids)`` -- the 217/183 partition of the
    SAME consumed A0 attempt ``rails.probes.a2t_pop_flight.
    derive_em_correct_ids`` reads (module docstring), reusing
    ``analysis.a2t_read.load_attempt_rows``/``score_row`` directly and
    partitioning on ``tool_accuracy`` alone (never re-deriving a second
    scorer, never re-flying). Fail-closed harness checks mirror
    ``a2t_pop_flight.derive_em_correct_ids``'s own: malformed rows, a row on
    an arm other than zero-supply, duplicate sample_id rows, an impossible
    overlap between the two partitions, an incomplete partition (a row that
    is neither correct nor wrong), and a derived count other than the
    expected 217/183 all raise :class:`PembReadError`."""

    from ..rails.adapters.audio2tool import Audio2ToolAdapter
    from ..rails.runner import ZERO_SUPPLY_ARM
    from .a2t_read import load_attempt_rows, score_row

    rows, malformed = load_attempt_rows(Path(attempt_dir))
    if malformed:
        raise PembReadError(
            f"{attempt_dir}: {len(malformed)} malformed outputs.jsonl row(s), e.g. {malformed[0]!r}"
        )
    wrong_arm = [row.sample_id for row in rows if row.arm != ZERO_SUPPLY_ARM]
    if wrong_arm:
        raise PembReadError(
            f"{attempt_dir}: {len(wrong_arm)} row(s) on an arm other than {ZERO_SUPPLY_ARM!r}, "
            f"e.g. {wrong_arm[:5]} -- this attempt is expected to carry only A0's own zero-supply arm"
        )
    seen: set[str] = set()
    duplicates: list[str] = []
    for row in rows:
        if row.sample_id in seen:
            duplicates.append(row.sample_id)
        seen.add(row.sample_id)
    if duplicates:
        raise PembReadError(f"{attempt_dir}: duplicate sample_id row(s): {sorted(set(duplicates))[:5]}")

    adapter = Audio2ToolAdapter(lock, root, repo_root=repo_root)
    scores = [score_row(adapter, row) for row in rows]
    correct = frozenset(score.row.sample_id for score in scores if float(score.metrics["tool_accuracy"]) == 1.0)
    wrong = frozenset(score.row.sample_id for score in scores if float(score.metrics["tool_accuracy"]) == 0.0)
    overlap = correct & wrong
    if overlap:  # pragma: no cover -- tool_accuracy is binary, precluded structurally
        raise PembReadError(f"{attempt_dir}: {len(overlap)} sample id(s) scored both correct and wrong")
    all_ids = frozenset(row.sample_id for row in rows)
    union = correct | wrong
    if union != all_ids:  # pragma: no cover -- tool_accuracy in {0.0, 1.0} covers every row structurally
        missing = sorted(all_ids - union)
        raise PembReadError(f"{attempt_dir}: partition does not cover every row (missing {missing[:5]})")
    if len(correct) != expected_correct_n:
        raise PembReadError(
            f"{attempt_dir}: derived {len(correct)} tool-correct id(s), expected exactly "
            f"{expected_correct_n} ({expected_correct_n}/{expected_correct_n + expected_wrong_n} "
            "fail-closed check)"
        )
    if len(wrong) != expected_wrong_n:
        raise PembReadError(
            f"{attempt_dir}: derived {len(wrong)} tool-wrong id(s), expected exactly {expected_wrong_n}"
        )
    return correct, wrong


def evaluate_run_b_verdict(*, top1_accuracy_183: float, recoveries_183: int) -> tuple[str, str]:
    """EMB-OPENS-183 / EMB-CLOSED / INCONCLUSIVE-EMB2, prereg section 3
    verbatim (BOTH clauses of EMB-OPENS-183 are required: top-1 >= 0.30 AND
    >= 55 recoveries)."""

    if top1_accuracy_183 >= EMB_OPENS_183_MIN_TOP1 and recoveries_183 >= EMB_OPENS_183_MIN_RECOVERIES:
        return "EMB-OPENS-183", (
            f"top-1 accuracy on the {TOOL_WRONG_N} tool-wrong ids = {top1_accuracy_183:.4f} >= "
            f"{EMB_OPENS_183_MIN_TOP1} AND recoveries = {recoveries_183} >= "
            f"{EMB_OPENS_183_MIN_RECOVERIES} (both clauses met -- a deployment-meaningful dent)"
        )
    if top1_accuracy_183 <= EMB_CLOSED_MAX_TOP1:
        return "EMB-CLOSED", (
            f"top-1 accuracy on the {TOOL_WRONG_N} tool-wrong ids = {top1_accuracy_183:.4f} <= "
            f"{EMB_CLOSED_MAX_TOP1}"
        )
    return "INCONCLUSIVE-EMB2", (
        f"top-1 accuracy on the {TOOL_WRONG_N} tool-wrong ids = {top1_accuracy_183:.4f} "
        f"(recoveries={recoveries_183}) meets neither the EMB-OPENS-183 nor EMB-CLOSED threshold"
    )


@dataclass(frozen=True)
class PembRunBPrediction:
    sample_id: str
    partition: str  # "correct" | "wrong" -- the 217/183 A0 partition this sample belongs to
    gold_tool_names: tuple[str, ...]
    top1_predicted_tool: str
    top1_cosine: float
    top1_correct: bool
    top5_predicted_tools: tuple[str, ...]
    top5_correct: bool


@dataclass(frozen=True)
class PembRunBReport:
    manifest_run_id: str
    n_samples: int
    n_registry_rows: int
    n_tool_correct: int
    n_tool_wrong: int
    recoveries_183: int
    top1_accuracy_183: float
    top5_accuracy_183: float
    top1_accuracy_217: float
    predictions: tuple[PembRunBPrediction, ...]
    confusion_183: tuple[ConfusionCell, ...]
    verdict: str
    verdict_detail: str


def build_run_b_report(
    manifest: LoadedEmbeddingManifest,
    gold_tools: Mapping[str, frozenset[str]],
    tool_correct_ids: frozenset[str],
    tool_wrong_ids: frozenset[str],
    *,
    expected_audio_n: int = RUN_B_AUDIO_N,
    expected_row_n: int = RUN_B_ROW_N,
    top_k: int = DEFAULT_TOP_K,
    confusion_limit: int | None = DEFAULT_CONFUSION_LIMIT,
) -> PembRunBReport:
    """Pure function of its inputs (module docstring: idempotent)."""

    if manifest.run_id != RUN_B_ID:
        raise PembReadError(f"manifest run_id {manifest.run_id!r} does not match Run B's {RUN_B_ID!r}")
    if len(manifest.audio) != expected_audio_n:
        raise PembReadError(f"manifest carries {len(manifest.audio)} audio vector(s), expected {expected_audio_n}")
    if len(manifest.text) != expected_row_n:
        raise PembReadError(f"manifest carries {len(manifest.text)} text vector(s), expected {expected_row_n}")
    _assert_key_sets_equal(manifest.audio.keys(), gold_tools.keys(), context="Run B audio ids vs gold tools")
    overlap = tool_correct_ids & tool_wrong_ids
    if overlap:
        raise PembReadError(f"tool_correct_ids and tool_wrong_ids overlap: {sorted(overlap)[:5]}")
    _assert_key_sets_equal(
        manifest.audio.keys(), tool_correct_ids | tool_wrong_ids, context="Run B audio ids vs 217+183 partition"
    )

    predictions: list[PembRunBPrediction] = []
    wrong_pairs: list[tuple[str, str]] = []
    for sample_id in sorted(manifest.audio):
        ranking = rank_cosine(manifest.audio[sample_id], manifest.text)
        top1_tool, top1_cosine = ranking[0]
        top5_tools = tuple(candidate_id for candidate_id, _cosine in ranking[:top_k])
        gold_names = gold_tools[sample_id]
        top1_correct = top1_tool in gold_names
        top5_correct = any(name in gold_names for name in top5_tools)
        partition = "wrong" if sample_id in tool_wrong_ids else "correct"
        if partition == "wrong":
            gold_label = ",".join(sorted(gold_names)) if gold_names else "(no gold tool)"
            wrong_pairs.append((gold_label, top1_tool))
        predictions.append(
            PembRunBPrediction(
                sample_id=sample_id,
                partition=partition,
                gold_tool_names=tuple(sorted(gold_names)),
                top1_predicted_tool=top1_tool,
                top1_cosine=top1_cosine,
                top1_correct=top1_correct,
                top5_predicted_tools=top5_tools,
                top5_correct=top5_correct,
            )
        )

    wrong_predictions = [p for p in predictions if p.partition == "wrong"]
    correct_predictions = [p for p in predictions if p.partition == "correct"]
    n_wrong = len(wrong_predictions)
    n_correct = len(correct_predictions)
    recoveries_183 = sum(1 for p in wrong_predictions if p.top1_correct)
    top1_accuracy_183 = recoveries_183 / n_wrong
    top5_hits_183 = sum(1 for p in wrong_predictions if p.top5_correct)
    top5_accuracy_183 = top5_hits_183 / n_wrong
    top1_hits_217 = sum(1 for p in correct_predictions if p.top1_correct)
    top1_accuracy_217 = top1_hits_217 / n_correct

    verdict, detail = evaluate_run_b_verdict(top1_accuracy_183=top1_accuracy_183, recoveries_183=recoveries_183)
    return PembRunBReport(
        manifest_run_id=manifest.run_id,
        n_samples=len(predictions),
        n_registry_rows=len(manifest.text),
        n_tool_correct=n_correct,
        n_tool_wrong=n_wrong,
        recoveries_183=recoveries_183,
        top1_accuracy_183=top1_accuracy_183,
        top5_accuracy_183=top5_accuracy_183,
        top1_accuracy_217=top1_accuracy_217,
        predictions=tuple(predictions),
        confusion_183=build_confusion_table(wrong_pairs, limit=confusion_limit),
        verdict=verdict,
        verdict_detail=detail,
    )


# ---------------------------------------------------------------------------
# JSON / text rendering (shared shape across both runs' CLI output).
# ---------------------------------------------------------------------------


def run_a_report_to_json(report: PembRunAReport) -> dict[str, object]:
    return {
        "schema": REPORT_SCHEMA_RUN_A,
        "run_id": RUN_A_ID,
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
        "verdict": report.verdict,
        "verdict_detail": report.verdict_detail,
    }


def run_b_report_to_json(report: PembRunBReport) -> dict[str, object]:
    return {
        "schema": REPORT_SCHEMA_RUN_B,
        "run_id": RUN_B_ID,
        "manifest_run_id": report.manifest_run_id,
        "n_samples": report.n_samples,
        "n_registry_rows": report.n_registry_rows,
        "n_tool_correct": report.n_tool_correct,
        "n_tool_wrong": report.n_tool_wrong,
        "recoveries_183": report.recoveries_183,
        "top1_accuracy_183": report.top1_accuracy_183,
        "top5_accuracy_183": report.top5_accuracy_183,
        "top1_accuracy_217": report.top1_accuracy_217,
        "predictions": [
            {
                "sample_id": p.sample_id,
                "partition": p.partition,
                "gold_tool_names": list(p.gold_tool_names),
                "top1_predicted_tool": p.top1_predicted_tool,
                "top1_cosine": p.top1_cosine,
                "top1_correct": p.top1_correct,
                "top5_predicted_tools": list(p.top5_predicted_tools),
                "top5_correct": p.top5_correct,
            }
            for p in report.predictions
        ],
        "confusion_183": [{"gold": c.gold, "predicted": c.predicted, "count": c.count} for c in report.confusion_183],
        "verdict": report.verdict,
        "verdict_detail": report.verdict_detail,
    }


def render_run_a_report(report: PembRunAReport) -> str:
    lines = [
        "P-EMB-1 pinned offline read (docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
        f"manifest run_id: {report.manifest_run_id}",
        f"n_samples={report.n_samples} n_labels={report.n_labels}",
        f"accuracy={report.accuracy:.4f} ({report.n_correct}/{report.n_samples})",
        "",
        f"[{report.verdict}]",
        f"  {report.verdict_detail}",
        "",
        "Confusion table (gold -> predicted : count)",
    ]
    for cell in report.confusion:
        lines.append(f"  {cell.gold} -> {cell.predicted} : {cell.count}")
    return "\n".join(lines)


def render_run_b_report(report: PembRunBReport) -> str:
    lines = [
        "P-EMB-2 pinned offline read (docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
        f"manifest run_id: {report.manifest_run_id}",
        f"n_samples={report.n_samples} n_registry_rows={report.n_registry_rows}",
        f"tool-wrong (183): n={report.n_tool_wrong} recoveries={report.recoveries_183} "
        f"top1_accuracy={report.top1_accuracy_183:.4f} top5_accuracy={report.top5_accuracy_183:.4f}",
        f"tool-correct (217, non-degradation, informational): n={report.n_tool_correct} "
        f"top1_accuracy={report.top1_accuracy_217:.4f}",
        "",
        f"[{report.verdict}]",
        f"  {report.verdict_detail}",
        "",
        "Confusion table over the 183 tool-wrong ids (gold -> predicted : count, top rows)",
    ]
    for cell in report.confusion_183:
        lines.append(f"  {cell.gold} -> {cell.predicted} : {cell.count}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pemb-read",
        description=(
            "P-EMB pinned offline read suite: argmax-cosine routing predictions vs scoring-side "
            "gold, verdict evaluators exactly as registered, confusion tables. Model-free, "
            "read-only; never opens a model session."
        ),
    )
    subparsers = parser.add_subparsers(dest="run", required=True)

    run_a = subparsers.add_parser("run-a", help="Run A: SLURP scenario routing (SAEA-PROBE-pemb1-78)")
    run_a.add_argument("--output-dir", required=True, type=Path)
    run_a.add_argument("--embeddings-root", type=Path, default=None, help="override the data root (default: SPEECHRL_DATA_DIR)")
    run_a.add_argument("--sample-manifest", type=Path, default=None)
    run_a.add_argument("--roster-table", type=Path, default=None)
    run_a.add_argument("--repo-root", type=Path, default=None)

    run_b = subparsers.add_parser("run-b", help="Run B: Audio2Tool tool routing (SAEA-PROBE-pemb2-552)")
    run_b.add_argument("--output-dir", required=True, type=Path)
    run_b.add_argument("--embeddings-root", type=Path, default=None, help="override the data root (default: SPEECHRL_DATA_DIR)")
    run_b.add_argument("--headroom-json", type=Path, default=None)
    run_b.add_argument("--repo-root", type=Path, default=None)

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

    from ..data.lock import REPO_ROOT, data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import write_json_artifact

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    root = Path(args.embeddings_root) if args.embeddings_root else data_root()
    lock = load_lock(umbrella_lock_path(repo_root))

    output_dir = Path(args.output_dir)
    verdict_path = _refuse_if_already_run(output_dir)
    if verdict_path is None:
        return 1

    try:
        if args.run == "run-a":
            sample_manifest_path = args.sample_manifest or (
                repo_root / "configs/probes/g0-binding/pslu-sample-devel-n60.json"
            )
            roster_table_path = args.roster_table or (
                repo_root / "configs/probes/g0-binding/pslu-rosters-train-only.json"
            )
            manifest = load_embedding_manifest(root, RUN_A_ID)
            gold = gold_scenarios_for_run_a(lock, root, repo_root=repo_root, sample_manifest_path=sample_manifest_path)
            labels = canonical_scenario_labels(roster_table_path)
            report = build_run_a_report(manifest, gold, labels)
            document = run_a_report_to_json(report)
            rendered = render_run_a_report(report)
        else:
            headroom_json_path = args.headroom_json or (
                repo_root
                / "docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/headroom.json"
            )
            manifest = load_embedding_manifest(root, RUN_B_ID)
            gold = gold_tools_for_run_b(lock, root, repo_root=repo_root)
            attempt_dir = resolve_a0_attempt_dir(headroom_json_path)
            correct_ids, wrong_ids = derive_tool_correct_partition(attempt_dir, lock, root, repo_root=repo_root)
            report = build_run_b_report(manifest, gold, correct_ids, wrong_ids)
            document = run_b_report_to_json(report)
            rendered = render_run_b_report(report)
    except (PembReadError, PembFlightError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    write_json_artifact(verdict_path, document)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    return 0


__all__ = [
    "DEFAULT_CONFUSION_LIMIT",
    "DEFAULT_TOP_K",
    "EMB_CLOSED_MAX_TOP1",
    "EMB_OPENS_183_MIN_RECOVERIES",
    "EMB_OPENS_183_MIN_TOP1",
    "EMB_ROUTES_MIN_ACCURACY",
    "EMB_WEAK_MAX_ACCURACY",
    "REPORT_SCHEMA_RUN_A",
    "REPORT_SCHEMA_RUN_B",
    "TOOL_CORRECT_N",
    "TOOL_WRONG_N",
    "ConfusionCell",
    "PembReadError",
    "PembRunAPrediction",
    "PembRunAReport",
    "PembRunBPrediction",
    "PembRunBReport",
    "build_confusion_table",
    "build_run_a_report",
    "build_run_b_report",
    "canonical_scenario_labels",
    "cosine_similarity",
    "derive_tool_correct_partition",
    "evaluate_run_a_verdict",
    "evaluate_run_b_verdict",
    "gold_scenarios_for_run_a",
    "gold_tools_for_run_b",
    "main",
    "rank_cosine",
    "render_run_a_report",
    "render_run_b_report",
    "resolve_a0_attempt_dir",
    "run_a_report_to_json",
    "run_b_report_to_json",
]
