"""The paired verdict of the two Earnings-22 model-usage cells (model-free).

Exposure row ``SAEA-E22-MF-USAGE-CELLS-VERDICT-V1`` (``model-free-check``).

Section 4 of ``docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md``
fixed a decision rule before either cell existed, and section 7.5 assigns its
application to a later document. Both flight rows published raw numbers only and
said in writing that "the paired contrast, its call-stratified CI90 and the
preregistered decision rule are a LATER document's". This module is that
document's measurement layer, and it does nothing else: it re-flies nothing,
re-scores nothing, post-processes no hypothesis and opens no test byte.

**The estimand is a POOLED RATIO, so the bootstrap is ``resampled_statistic``.**
Section 4 names ``analysis.paired`` and its stratified draws. Corpus WER and the
agentic error rate are both ``sum(numerator) / sum(denominator)`` over the
resampled rows, not the mean of a per-row difference, and ``analysis.paired``'s
own docstring says so: ``resampled_statistic`` "gets the identical draws" as
``paired_contrast`` for a caller-supplied ratio. ``paired_contrast`` is still
used, on the per-utterance WER, for saves / harms / ties and the exact sign
test -- those are per-unit statistics and it is the right tool for them.

**Nothing is computed until six hard-coded raw pairs reproduce.** The caller
passes them in (:func:`build_receipts` takes ``anchors``), and a single digit of
drift in any arm's corpus WER or agentic error rate refuses the whole read
rather than yielding a contrast over a table that is not the one the flights
sealed.

The six ESB TEST calls are unreachable from here: the reference loader is pinned
to the dev10 receipt alone and the segment-table loader to the dev10 extracted
table, exactly as ``analysis.e22_error_taxonomy`` pins them.

**This module is also the BASE for the 2026-09-07 encoding-probe verdict.**
``analysis.e22_encoding_probes`` is a thin derivation over it: it reuses the
loaders, the identity gate, :func:`pooled_delta`, :func:`decide`, the tables and
:func:`category_mass` unchanged, and adds only what its own preregistration
adds -- three cells instead of two, a per-row BOUNDARY charge
(:func:`boundary_charge`) so clause 3 can be bootstrapped like the other two
estimands, and the ``@``-suffixed variant ids of deviation ``D-ENC-1``, which
the loaders here fold back onto the published segment key. No pooled ratio, no
resampling rule, no table and no decision clause is implemented twice.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Callable, Mapping, Sequence

from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (
    IMPACT_NEUTRAL_CATEGORIES,
    IMPACT_NEUTRAL_RULES,
    ScoredSpan,
    UtteranceContext,
    agentic_error_rate,
    boundary_diagnostics,
    build_contexts,
    build_entity_inventory,
    category_table,
    load_hypotheses,
    rule_table,
    scan_arm,
)
from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (
    _mass as _span_mass,  # the taxonomy's one span-mass rule, never re-implemented here
)
from speech_aware_evidence_acquisition.analysis.paired import (
    paired_contrast,
    per_sample_scores_from_score_file,
)
from speech_aware_evidence_acquisition.analysis.paired import (
    resampled_statistic as _resampled_statistic,
)
from speech_aware_evidence_acquisition.reproduction.esb_reference import (
    published_segment_key,
)

ANALYSIS_VERSION = "saea-e22-usage-cells-verdict-v1"
EXPOSURE_ROW_ID = "SAEA-E22-MF-USAGE-CELLS-VERDICT-V1"
PREREGISTRATION = "docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md"

#: Section 4, verbatim: 10,000 replicates, stratified by source call, seed
#: 20260903, CI90. None of these three may be chosen after a number exists.
SEED = 20260903
N_REPLICATES = 10_000
CI_LEVEL = 0.90

#: Section 4 clause 2's non-inferiority margin, inherited verbatim from section
#: 1.6 of the boundary-exact preregistration and fixed before any number existed.
AGENTIC_MARGIN_POINTS = 0.05

WHISPER_SCORER = "asr-wer-esb-whisper"
FROZEN_SCORER = "asr-wer-esb"

COMPARATOR = {
    "arm": "A",
    "run_id": "SAEA-E22-DEV-ESB-PROMPT-A-V1",
    "attempt": "attempt-20260905T073641Z-f977d1",
    "label": "the sealed dev arm A, restricted to the 1,500 roster ids; NO new arm A is flown",
}
CELLS: Mapping[str, Mapping[str, str]] = {
    "Q8": {
        "run_id": "SAEA-E22-DEV-ESB-Q8-V1",
        "attempt": "attempt-20260907T030402Z-60e8e1",
        "cell": "(a)",
        "factor": "the decoder quantization: Q8_0 instead of the Q4_K_M requant",
    },
    "STOPCAP": {
        "run_id": "SAEA-E22-DEV-ESB-STOPCAP-V1",
        "attempt": "attempt-20260907T042641Z-2a48e8",
        "cell": "(b)",
        "factor": "a duration-proportional generation cap at alpha 1.5",
    },
}

ROSTER_RELPATH = "docs/receipts/rosters/e22-dev-esb-1500-v1.json"
CAPS_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-06-e22-dev-esb-stopcap-v1/flight-1500/caps-1500.json"
)

#: Section 2.2, fixed before any capped request existed so it could be wrong.
STOPCAP_PREDICTION = {
    "rows_the_cap_bites": 50,
    "benefit_rows": 35,
    "harm_rows": 15,
    "tail_bleed_rows_cut": 5,
    "corpus_wer_percent": 17.1765,
    "agentic_error_rate_percent": 1.9428,
}

DURATION_BUCKETS = ((0.0, 1.0), (1.0, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 16.0), (16.0, 1e9))

BOUNDARY_RULES = ("model-behaviour/runaway-tail", "model-behaviour/runaway-head")
BOUNDARY_CATEGORY = "segmentation-artifact"


class UsageCellsError(RuntimeError):
    """An input drifted, an identity anchor failed, or a roster id is missing."""


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def load_roster(repo_root: Path) -> dict[str, object]:
    """The frozen 1,500-row roster: ids, call strata, durations, identity hash."""

    path = Path(repo_root) / ROSTER_RELPATH
    payload = path.read_bytes()
    receipt = json.loads(payload.decode("utf-8"))
    items = receipt["items"]
    ids = tuple(sorted(str(item["sample_id"]) for item in items))
    if len(ids) != len(set(ids)) or not ids:
        raise UsageCellsError(f"{path} does not carry a unique non-empty id set")
    return {
        "sample_ids": ids,
        "call_of": {str(i["sample_id"]): str(i["stratum"]) for i in items},
        "seconds_of": {str(i["sample_id"]): float(i["audio_seconds"]) for i in items},
        "split_identity_hash": str(receipt["split_identity_hash"]),
        "roster_id": str(receipt["roster_id"]),
        "receipt_sha256": hashlib.sha256(payload).hexdigest(),
    }


def _run_dir(root: Path, source: Mapping[str, str]) -> Path:
    return Path(root) / "runs" / source["run_id"] / source["attempt"]


def load_score_rows(
    root: Path, source: Mapping[str, str], sample_ids: Sequence[str]
) -> dict[str, dict[str, dict[str, float]]]:
    """``{scorer -> {sample_id -> row}}`` from one arm's finalize score file.

    The finalize ``<run_id>.scores.json`` is the one per-sample table all three
    arms carry (the sealed comparator was never re-scored with
    ``--include-per-sample`` through ``core.scoring_batch``), so it is the single
    reading path for every arm. Where a cell also has a verified
    ``score-batch-per-sample`` file, :func:`verified_cross_check` proves the two
    agree row for row rather than assuming it.

    **Rows are keyed by the PUBLISHED segment.** A media-variant cell carries
    deviation ``D-ENC-1``: its sample ids are ``<call>-<segment>@<variant>``, so
    the score side is folded back onto the published key with
    ``reproduction.esb_reference.published_segment_key`` -- the same split on
    ``@`` the reference side already applies -- and the paired join is per
    published segment. An unsuffixed population is returned unchanged.
    """

    source_dir = _run_dir(root, source)
    path = source_dir / f"{source['run_id']}.scores.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    wanted = set(sample_ids)
    table: dict[str, dict[str, dict[str, float]]] = {}
    for scorer in (WHISPER_SCORER, FROZEN_SCORER):
        rows: dict[str, dict[str, float]] = {}
        for row in document[scorer]["per_sample"]:
            sample_id = published_segment_key(str(row["sample_id"]))
            if sample_id not in wanted:
                continue
            if sample_id in rows:
                raise UsageCellsError(
                    f"{path} scorer {scorer} carries two rows for published segment "
                    f"{sample_id!r}; a variant suffix must not collapse two rows into one"
                )
            rows[sample_id] = {
                key: float(row[key])
                for key in ("wer", "hits", "substitutions", "deletions", "insertions")
            }
        missing = wanted - set(rows)
        if missing:
            raise UsageCellsError(
                f"{path} scorer {scorer} is missing {len(missing)} roster rows, "
                f"first {sorted(missing)[0]!r}"
            )
        table[scorer] = rows
    return table


def verified_cross_check(
    root: Path,
    source: Mapping[str, str],
    rows: Mapping[str, Mapping[str, Mapping[str, float]]],
    *,
    directories: Sequence[str] = ("score-batch-per-sample",),
) -> dict[str, object]:
    """Prove the finalize per-sample rows equal the VERIFIED batch ones.

    ``core.scoring_batch``'s ``--include-per-sample`` result is the audit record
    (``"verified": true``); the finalize table is a convenience copy. Where both
    exist they must be the same numbers, and this says so with a count rather
    than with a sentence.

    ``directories`` names the sub-directories to search, in order, because
    ``run_score_batch`` has written its result under more than one name across
    this study's flights; the first that yields a ``*.score.json`` is read.
    Verified ids carry the same possible variant suffix the finalize table does,
    so they are folded onto the published segment key before the comparison.
    """

    matches: list[Path] = []
    for name in directories:
        directory = _run_dir(root, source) / name
        # ``run_score_batch`` writes the result beside its summary on one path
        # and under ``results/`` on another; both are the same verified
        # document, so the search is recursive rather than pinned to whichever
        # layout ran first.
        matches = sorted(directory.rglob("*.score.json")) if directory.is_dir() else []
        if matches:
            break
    if not matches:
        return {
            "available": False,
            "rows_compared": 0,
            "disagreements": [],
            "reason": "no core.scoring_batch result file under " + " or ".join(directories),
        }
    # Without ``--include-per-sample`` the driver emits each scorer's aggregate
    # block only, and the sealed comparator was scored that way. That is an
    # ABSENT cross-check, not a failed one -- the reading path is the finalize
    # table and the identity gate is what protects it -- so it is reported as
    # absent with its reason rather than swallowed or raised. Every other
    # malformation still fails closed inside the reader below.
    document = json.loads(matches[0].read_text(encoding="utf-8"))
    scorer_block = document.get("scores", {}).get(WHISPER_SCORER, {})
    if not isinstance(scorer_block, dict) or not scorer_block.get("per_sample"):
        return {
            "available": False,
            "rows_compared": 0,
            "disagreements": [],
            "score_file": matches[0].name,
            "score_file_sha256": hashlib.sha256(matches[0].read_bytes()).hexdigest(),
            "reason": (
                f"{matches[0].name} carries no per_sample block for {WHISPER_SCORER}; it was "
                "scored without --include-per-sample"
            ),
        }
    verified = {
        published_segment_key(sample_id): row
        for sample_id, row in per_sample_scores_from_score_file(
            matches[0], WHISPER_SCORER, ("wer", "substitutions", "deletions", "insertions")
        ).items()
    }
    disagreements = [
        sample_id
        for sample_id, row in rows[WHISPER_SCORER].items()
        if sample_id not in verified
        or any(abs(verified[sample_id][k] - row[k]) > 1e-12 for k in verified[sample_id])
    ]
    return {
        "available": True,
        "score_file": matches[0].name,
        "score_file_sha256": hashlib.sha256(matches[0].read_bytes()).hexdigest(),
        "rows_compared": len(rows[WHISPER_SCORER]),
        "disagreements": disagreements,
    }


def scan(
    root: Path,
    source: Mapping[str, str],
    *,
    references: Mapping[str, str],
    segments: Mapping[str, Mapping[str, object]],
    inventory: Mapping[str, frozenset[str]],
    sample_ids: Sequence[str],
) -> tuple[object, list[ScoredSpan], dict[str, UtteranceContext]]:
    """One arm's sealed outputs through the committed taxonomy, on the roster.

    The hypotheses are re-keyed by published segment for the same ``D-ENC-1``
    reason :func:`load_score_rows` gives, so ``build_contexts`` resolves the
    reference, the neighbours and the entity inventory of the segment the clip
    was cut from, whatever the media variant was called.
    """

    path = _run_dir(root, source) / f"{source['run_id']}.outputs.jsonl"
    sealed = load_hypotheses(path)
    hypotheses = {published_segment_key(sample_id): text for sample_id, text in sealed.items()}
    if len(hypotheses) != len(sealed):
        raise UsageCellsError(
            f"{path} collapses {len(sealed)} sealed ids onto {len(hypotheses)} published "
            "segments; a variant suffix must not merge two rows"
        )
    wanted = set(sample_ids)
    missing = wanted - set(hypotheses)
    if missing:
        raise UsageCellsError(
            f"{path} is missing {len(missing)} roster rows, first {sorted(missing)[0]!r}"
        )
    contexts = build_contexts(
        references, segments, {k: v for k, v in hypotheses.items() if k in wanted}, inventory
    )
    totals, scored = scan_arm(contexts, order=tuple(sample_ids))
    return totals, scored, contexts


def high_impact_charge(scored: Sequence[ScoredSpan]) -> dict[str, int]:
    """Per-row HIGH-impact reference-word mass -- the agentic rate's numerator.

    The neutrality ruling is read off the same two constants
    :func:`~...e22_error_taxonomy.agentic_error_rate` reads, so the per-row
    numerators sum to exactly the corpus figure that function returns.
    """

    charge: Counter[str] = Counter()
    for item in scored:
        neutral = item.category in IMPACT_NEUTRAL_CATEGORIES or item.rule in IMPACT_NEUTRAL_RULES
        if ("NONE" if neutral else item.content_impact) == "HIGH":
            charge[item.sample_id] += item.span.reference_word_charge
    return dict(charge)


def boundary_charge(scored: Sequence[ScoredSpan]) -> dict[str, int]:
    """Per-row BOUNDARY-block error mass -- the numerator of the boundary contrast.

    The block is the one :func:`category_mass` reports and clause 3 of the
    encoding-probe preregistration decides on: every span in the
    ``segmentation-artifact`` category plus the ``model-behaviour/runaway-tail``
    and ``model-behaviour/runaway-head`` rules. The mass is the same
    :func:`~...e22_error_taxonomy._mass` a span owns in ``category_table``, so
    these per-row numerators sum to exactly the corpus block that table reports
    and the pooled bootstrap is over the same quantity the rule names.
    """

    charge: Counter[str] = Counter()
    for item in scored:
        if item.category == BOUNDARY_CATEGORY or item.rule in BOUNDARY_RULES:
            charge[item.sample_id] += _span_mass(item.span)
    return dict(charge)


# ---------------------------------------------------------------------------
# The identity gate. Nothing below it runs until it passes.
# ---------------------------------------------------------------------------


def identity_gate(
    measured: Mapping[str, Mapping[str, float]], anchors: Mapping[str, Mapping[str, float]]
) -> dict[str, object]:
    """Refuse the whole read unless every hard-coded raw pair reproduces."""

    rows = []
    for arm in sorted(anchors):
        for metric, expected in sorted(anchors[arm].items()):
            got = round(float(measured[arm][metric]), 4)
            rows.append(
                {"arm": arm, "metric": metric, "sealed": expected, "measured": got,
                 "reproduced": got == round(float(expected), 4)}
            )
    failed = [row for row in rows if not row["reproduced"]]
    if failed:
        raise UsageCellsError(
            "identity gate FAILED, no contrast computed: "
            + "; ".join(
                f"{r['arm']} {r['metric']} sealed {r['sealed']} measured {r['measured']}"
                for r in failed
            )
        )
    return {"pairs": rows, "reproduced": True}


# ---------------------------------------------------------------------------
# Pooled contrasts
# ---------------------------------------------------------------------------


def pooled_delta(
    sample_ids: Sequence[str],
    numerator: Callable[[str, str], float],
    denominator: Callable[[str, str], float],
    *,
    left: str,
    right: str,
    call_of: Mapping[str, str],
) -> dict[str, object]:
    """``100 * (right_ratio - left_ratio)`` with both preregistered intervals.

    ``stratified`` is section 4's own draw -- rows resampled inside each of the
    ten call strata, calls held fixed. ``clustered`` resamples whole calls and
    is reported beside it because a per-call effect that ten calls happen to
    agree on is not the same evidence as one they do not; the decision rule
    reads the stratified interval, as written.
    """

    def statistic(sequence: Sequence[str]) -> float:
        rn = rd = ln = ld = 0.0
        for sample_id in sequence:
            rn += numerator(right, sample_id)
            rd += denominator(right, sample_id)
            ln += numerator(left, sample_id)
            ld += denominator(left, sample_id)
        return 100.0 * (rn / rd - ln / ld)

    out: dict[str, object] = {}
    for label, keyword in (("stratified", "strata_of"), ("clustered", "cluster_of")):
        result = _resampled_statistic(
            sample_ids=sample_ids,
            statistic=statistic,
            seed=SEED,
            n_replicates=N_REPLICATES,
            ci_level=CI_LEVEL,
            **{keyword: lambda sample_id: call_of[sample_id]},
        )
        out[label] = {
            "point_estimate": round(result.point_estimate, 4),
            "ci_low": round(result.ci_low, 4),
            "ci_high": round(result.ci_high, 4),
            "sigma_hat": round(result.sigma_hat, 4),
            "ci_level": CI_LEVEL,
            "n_replicates": N_REPLICATES,
            "seed": SEED,
        }
    return out


def decide(
    wer: Mapping[str, object],
    agentic: Mapping[str, object],
    *,
    wer_ci_upper_max: float = 0.0,
    boundary: Mapping[str, object] | None = None,
    boundary_drop_points: float = 0.0,
) -> dict[str, object]:
    """The preregistered rule, applied unmodified, on the STRATIFIED interval.

    Two clauses are the 2026-09-06 usage-cells rule and are the defaults:
    corpus WER improves with a CI90 upper bound below ``wer_ci_upper_max``
    (0 there), and the agentic CI90 upper bound is below the fixed
    non-inferiority margin.

    The 2026-09-07 encoding-probe rule is the SAME two clauses with a stricter
    ``wer_ci_upper_max`` -- -0.2356, the lower edge of the measured same-request
    null, so a cell must be disjoint from this runtime's own cross-run noise --
    plus a third: the boundary block must FALL by at least
    ``boundary_drop_points``. Passing ``boundary`` turns clause 3 on; omitting
    it leaves the two-clause rule byte-for-byte as it was.
    """

    wer_block = wer["stratified"]
    agentic_block = agentic["stratified"]
    clause_1 = bool(wer_block["point_estimate"] < 0.0 and wer_block["ci_high"] < wer_ci_upper_max)
    # Clause 2 has TWO halves in the preregistered text -- "its point estimate is
    # <= arm A's AND the CI90 upper bound on its delta is below +0.05 points" --
    # and both are tested. On every cell this study has decided the two halves
    # agree, so this is fidelity to the written rule rather than a change of
    # outcome.
    clause_2 = bool(
        agentic_block["point_estimate"] <= 0.0
        and agentic_block["ci_high"] < AGENTIC_MARGIN_POINTS
    )
    rule = (
        "ADMITTED iff corpus WER improves AND its call-stratified CI90 upper bound is "
        f"< {wer_ci_upper_max:g}, AND the agentic error rate does not worsen (point estimate "
        f"<= the comparator's) with a CI90 upper bound < +{AGENTIC_MARGIN_POINTS} points"
    )
    decision: dict[str, object] = {
        "clause_1_corpus_wer_improves_with_ci90_upper_below_zero": clause_1,
        "clause_1_ci90_upper": wer_block["ci_high"],
        "clause_1_ci90_upper_threshold": wer_ci_upper_max,
        "clause_2_agentic_ci90_upper_below_margin": clause_2,
        "clause_2_ci90_upper": agentic_block["ci_high"],
        "clause_2_point_estimate": agentic_block["point_estimate"],
        "clause_2_margin_points": AGENTIC_MARGIN_POINTS,
    }
    if boundary is None:
        decision["admitted"] = bool(clause_1 and clause_2)
        decision["rule"] = rule + " (preregistration section 4, applied unmodified)"
        return decision
    boundary_block = boundary["stratified"]
    clause_3 = bool(float(boundary_block["point_estimate"]) <= -boundary_drop_points)
    decision["clause_3_boundary_block_falls_by_at_least_points"] = clause_3
    decision["clause_3_boundary_delta_points"] = boundary_block["point_estimate"]
    decision["clause_3_required_drop_points"] = boundary_drop_points
    decision["clause_3_ci90"] = [boundary_block["ci_low"], boundary_block["ci_high"]]
    decision["admitted"] = bool(clause_1 and clause_2 and clause_3)
    decision["rule"] = (
        rule + f", AND the boundary block falls by at least {boundary_drop_points:g} WER "
        "points (preregistration section 4, applied unmodified)"
    )
    return decision


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def _corpus(rows: Mapping[str, Mapping[str, float]], subset: Sequence[str]) -> dict[str, float]:
    substitutions = sum(rows[s]["substitutions"] for s in subset)
    deletions = sum(rows[s]["deletions"] for s in subset)
    insertions = sum(rows[s]["insertions"] for s in subset)
    hits = sum(rows[s]["hits"] for s in subset)
    reference_words = hits + substitutions + deletions
    hypothesis_words = hits + substitutions + insertions
    errors = substitutions + deletions + insertions
    return {
        "rows": len(subset),
        "substitutions": int(substitutions),
        "deletions": int(deletions),
        "insertions": int(insertions),
        "reference_words": int(reference_words),
        "hypothesis_words": int(hypothesis_words),
        "errors": int(errors),
        "corpus_wer_percent": round(100.0 * errors / reference_words, 4),
        "hypothesis_over_reference_ratio": round(hypothesis_words / reference_words, 4),
        "insertion_share_of_errors_percent": round(100.0 * insertions / errors, 2),
        "mean_per_utterance_wer_percent": round(
            100.0 * sum(rows[s]["wer"] for s in subset) / len(subset), 4
        ),
    }


def pooled_charge_points(
    charge: Mapping[str, int], reference_words: Mapping[str, int], subset: Sequence[str]
) -> float:
    """``100 * sum(charge) / sum(reference words)`` over ``subset``, in WER points.

    One pooled-ratio arithmetic for every per-row charge this study reports on a
    reference-word denominator: the agentic HIGH-impact mass
    (:func:`high_impact_charge`) and the boundary block
    (:func:`boundary_charge`). Rows absent from ``charge`` carry zero.
    """

    mass = sum(charge.get(s, 0) for s in subset)
    words = sum(reference_words[s] for s in subset)
    return round(100.0 * mass / words, 4) if words else 0.0


def per_call_table(
    arms: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    call_of: Mapping[str, str],
) -> list[dict[str, object]]:
    """All ten calls, both normalizers, every arm, with each cell's delta."""

    table = []
    for call in sorted(set(call_of.values())):
        subset = [s for s in sample_ids if call_of[s] == call]
        row: dict[str, object] = {"call": call, "rows": len(subset)}
        for arm, block in arms.items():
            whisper = _corpus(block["scores"][WHISPER_SCORER], subset)
            frozen = _corpus(block["scores"][FROZEN_SCORER], subset)
            row[f"{arm}_reference_words"] = whisper["reference_words"]
            row[f"{arm}_corpus_wer_whisper"] = whisper["corpus_wer_percent"]
            row[f"{arm}_corpus_wer_saea_v1"] = frozen["corpus_wer_percent"]
            row[f"{arm}_agentic_percent"] = pooled_charge_points(
                block["charge"], block["reference_words_of"], subset
            )
        for arm in arms:
            if arm == "A":
                continue
            row[f"{arm}_delta_whisper"] = round(
                row[f"{arm}_corpus_wer_whisper"] - row["A_corpus_wer_whisper"], 4
            )
            row[f"{arm}_delta_agentic"] = round(
                row[f"{arm}_agentic_percent"] - row["A_agentic_percent"], 4
            )
        table.append(row)
    return table


def weightings(
    arms: Mapping[str, Mapping[str, object]],
    per_call: Sequence[Mapping[str, object]],
    sample_ids: Sequence[str],
) -> dict[str, object]:
    """Natural-mixture beside equal-call, as section 4's reporting rule requires."""

    out: dict[str, object] = {}
    for arm, block in arms.items():
        natural = _corpus(block["scores"][WHISPER_SCORER], sample_ids)
        out[arm] = {
            "natural_mixture_corpus_wer": natural["corpus_wer_percent"],
            "equal_call_corpus_wer": round(
                sum(float(r[f"{arm}_corpus_wer_whisper"]) for r in per_call) / len(per_call), 4
            ),
            "natural_mixture_agentic": pooled_charge_points(
                block["charge"], block["reference_words_of"], sample_ids
            ),
            "equal_call_agentic": round(
                sum(float(r[f"{arm}_agentic_percent"]) for r in per_call) / len(per_call), 4
            ),
        }
    return out


def duration_table(
    arms: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    seconds_of: Mapping[str, float],
) -> list[dict[str, object]]:
    """The utterance-duration decomposition, on the taxonomy's own buckets."""

    table = []
    for low, high in DURATION_BUCKETS:
        subset = [s for s in sample_ids if low <= seconds_of[s] < high]
        if not subset:
            continue
        row: dict[str, object] = {
            "bucket": f"[{low:g}, {high:g})" if high < 1e8 else f"[{low:g}, inf)",
            "rows": len(subset),
        }
        for arm, block in arms.items():
            measured = _corpus(block["scores"][WHISPER_SCORER], subset)
            row[f"{arm}_corpus_wer_whisper"] = measured["corpus_wer_percent"]
            row["reference_words"] = measured["reference_words"]
        for arm in arms:
            if arm != "A":
                row[f"{arm}_delta"] = round(
                    row[f"{arm}_corpus_wer_whisper"] - row["A_corpus_wer_whisper"], 4
                )
        table.append(row)
    return table


def category_mass(
    scored: Sequence[ScoredSpan],
    contexts: Mapping[str, UtteranceContext],
    reference_words: int,
) -> dict[str, object]:
    """One arm's category masses plus the boundary block and its containment buckets."""

    rules = {row["rule"]: row for row in rule_table(scored, reference_words)}
    categories = {row["category"]: row for row in category_table(scored, reference_words)}
    boundary_mass = int(categories.get(BOUNDARY_CATEGORY, {}).get("error_mass", 0)) + sum(
        int(rules.get(rule, {}).get("error_mass", 0)) for rule in BOUNDARY_RULES
    )
    return {
        "categories": category_table(scored, reference_words),
        "boundary": {
            "segmentation_artifact_mass": int(
                categories.get(BOUNDARY_CATEGORY, {}).get("error_mass", 0)
            ),
            "runaway_tail_mass": int(rules.get(BOUNDARY_RULES[0], {}).get("error_mass", 0)),
            "runaway_head_mass": int(rules.get(BOUNDARY_RULES[1], {}).get("error_mass", 0)),
            "total_error_mass": boundary_mass,
            "wer_points": round(100.0 * boundary_mass / reference_words, 4),
            "containment": boundary_diagnostics(scored, contexts),
        },
    }


# ---------------------------------------------------------------------------
# The cell (b) prediction check
# ---------------------------------------------------------------------------


def prediction_check(
    repo_root: Path,
    arms: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    call_of: Mapping[str, str],
    texts: Mapping[str, Mapping[str, str]],
) -> dict[str, object]:
    """Section 2.2's prediction against what the cap actually did.

    A row is BOUND when its completion tokens equal its own resolved cap -- what
    a greedy decode stopped by ``n_predict`` looks like -- and that flag is read
    out of the committed ``caps-1500.json``, which the flight built from the
    sealed trace. The cap-inert rows are then read as a NULL: their request
    differed from arm A's only in a ``max_tokens`` integer larger than the
    generation, so anything that moved there is run-to-run non-determinism and
    not the cap.
    """

    caps = json.loads((Path(repo_root) / CAPS_RELPATH).read_text(encoding="utf-8"))["rows"]
    bound = [s for s in sample_ids if bool(caps[s]["cap_bound"])]
    inert = [s for s in sample_ids if not bool(caps[s]["cap_bound"])]
    cell = arms["STOPCAP"]["scores"][WHISPER_SCORER]
    base = arms["A"]["scores"][WHISPER_SCORER]

    benefit = harm = 0
    lost_reference_words = []
    for sample_id in bound:
        row = cell[sample_id]
        hypothesis_words = row["hits"] + row["substitutions"] + row["insertions"]
        reference_words = row["hits"] + row["substitutions"] + row["deletions"]
        if hypothesis_words < reference_words:
            harm += 1
        else:
            benefit += 1
        extra = row["deletions"] - base[sample_id]["deletions"]
        if extra > 0:
            lost_reference_words.append(
                {
                    "sample_id": sample_id,
                    "arm_a_deletions": int(base[sample_id]["deletions"]),
                    "cell_deletions": int(row["deletions"]),
                    "extra_deletions": int(extra),
                    "resolved_max_tokens": int(caps[sample_id]["resolved_max_tokens"]),
                    "audio_seconds": float(caps[sample_id]["audio_seconds"]),
                }
            )

    def errors(rows: Mapping[str, Mapping[str, float]], subset: Sequence[str]) -> int:
        return int(
            sum(rows[s]["substitutions"] + rows[s]["deletions"] + rows[s]["insertions"]
                for s in subset)
        )

    def split(subset: Sequence[str]) -> dict[str, object]:
        block = pooled_delta(
            sorted(subset),
            lambda arm, s: (
                arms[arm]["scores"][WHISPER_SCORER][s]["substitutions"]
                + arms[arm]["scores"][WHISPER_SCORER][s]["deletions"]
                + arms[arm]["scores"][WHISPER_SCORER][s]["insertions"]
            ),
            lambda arm, s: (
                arms[arm]["scores"][WHISPER_SCORER][s]["hits"]
                + arms[arm]["scores"][WHISPER_SCORER][s]["substitutions"]
                + arms[arm]["scores"][WHISPER_SCORER][s]["deletions"]
            ),
            left="A",
            right="STOPCAP",
            call_of=call_of,
        )
        return {
            "rows": len(subset),
            "arm_a_error_operations": errors(base, subset),
            "cell_error_operations": errors(cell, subset),
            "error_operation_delta": errors(cell, subset) - errors(base, subset),
            "pooled_delta_on_own_denominator": block["stratified"],
        }

    prefixes = sum(1 for s in bound if texts["A"][s].startswith(texts["STOPCAP"][s]))
    identical_bound = sum(1 for s in bound if texts["A"][s] == texts["STOPCAP"][s])
    return {
        "predicted": dict(STOPCAP_PREDICTION),
        "measured": {
            "rows_the_cap_bit": len(bound),
            "benefit_rows": benefit,
            "harm_rows": harm,
            "corpus_wer_percent": _corpus(cell, sample_ids)["corpus_wer_percent"],
            "agentic_error_rate_percent": pooled_charge_points(
                arms["STOPCAP"]["charge"], arms["STOPCAP"]["reference_words_of"], sample_ids
            ),
        },
        "benefit_harm_definition": (
            "mirrors section 2.2's simulator: a bound row is HARM when its emitted "
            "normalized hypothesis is shorter than its own reference, and BENEFIT otherwise"
        ),
        "bound_rows_that_lost_reference_words": lost_reference_words,
        "bound": split(bound),
        "cap_inert_null": split(inert),
        "greedy_prefix_assumption": {
            "bound_rows": len(bound),
            "cell_text_is_a_prefix_of_arm_a_text": prefixes,
            "byte_identical_to_arm_a": identical_bound,
            "not_a_prefix": len(bound) - prefixes,
            "reading": (
                "section 2.2 assumption 1 says a capped greedy decode returns the uncapped "
                "decode's token PREFIX; arm A's own text is not bitwise reproducible on this "
                "runtime, so a non-prefix row is jointly the assumption and that jitter"
            ),
        },
        "text_identity": {
            "cap_inert_rows": len(inert),
            "cap_inert_byte_identical_to_arm_a": sum(
                1 for s in inert if texts["A"][s] == texts["STOPCAP"][s]
            ),
            "cap_inert_score_row_identical": sum(
                1
                for s in inert
                if cell[s]["substitutions"] == base[s]["substitutions"]
                and cell[s]["deletions"] == base[s]["deletions"]
                and cell[s]["insertions"] == base[s]["insertions"]
            ),
        },
    }


# ---------------------------------------------------------------------------
# The receipt
# ---------------------------------------------------------------------------


def build_receipts(
    *,
    repo_root: Path,
    root: Path,
    references: Mapping[str, str],
    segments: Mapping[str, Mapping[str, object]],
    anchors: Mapping[str, Mapping[str, float]],
    outbound_attempts: int,
    outbound_targets: Sequence[str],
) -> tuple[dict[str, object], str]:
    """``(summary, per-call CSV)``. Nothing is contrasted until the gate passes."""

    roster = load_roster(repo_root)
    sample_ids: tuple[str, ...] = roster["sample_ids"]  # type: ignore[assignment]
    call_of: Mapping[str, str] = roster["call_of"]  # type: ignore[assignment]
    raw_by_call: dict[str, list[str]] = {}
    for sample_id, sentence in references.items():
        raw_by_call.setdefault(str(segments[sample_id]["source_id"]), []).append(sentence)
    inventory = build_entity_inventory(raw_by_call)

    arms: dict[str, dict[str, object]] = {}
    texts: dict[str, dict[str, str]] = {}
    measured: dict[str, dict[str, float]] = {}
    for arm, source in [("A", COMPARATOR)] + [(k, v) for k, v in CELLS.items()]:
        scores = load_score_rows(root, source, sample_ids)
        totals, scored, contexts = scan(
            root,
            source,
            references=references,
            segments=segments,
            inventory=inventory,
            sample_ids=sample_ids,
        )
        rate = agentic_error_rate(scored, totals.reference_length)
        arms[arm] = {
            "run_id": source["run_id"],
            "attempt": source["attempt"],
            "outputs_sha256": hashlib.sha256(
                (_run_dir(root, source) / f"{source['run_id']}.outputs.jsonl").read_bytes()
            ).hexdigest(),
            "scores": scores,
            "charge": high_impact_charge(scored),
            "reference_words_of": {s: len(contexts[s].ref_tokens) for s in sample_ids},
            "agentic": rate,
            "taxonomy_totals": {
                "substitutions": totals.substitutions,
                "deletions": totals.deletions,
                "insertions": totals.insertions,
                "reference_words": totals.reference_length,
                "corpus_wer_percent": round(
                    100.0 * totals.errors / totals.reference_length, 4
                ),
            },
            "category_mass": category_mass(scored, contexts, totals.reference_length),
            "verified_cross_check": verified_cross_check(root, source, scores),
            "error_shape_whisper": _corpus(scores[WHISPER_SCORER], sample_ids),
            "error_shape_saea_v1": _corpus(scores[FROZEN_SCORER], sample_ids),
        }
        texts[arm] = {
            sample_id: contexts[sample_id].raw_hypothesis for sample_id in sample_ids
        }
        measured[arm] = {
            "corpus_wer_percent": _corpus(scores[WHISPER_SCORER], sample_ids)[
                "corpus_wer_percent"
            ],
            "agentic_error_rate_percent": float(rate["agentic_error_rate_percent"]),
        }

    gate = identity_gate(measured, anchors)

    contrasts: dict[str, object] = {}
    for arm in CELLS:
        wer = pooled_delta(
            sample_ids,
            lambda a, s: (
                arms[a]["scores"][WHISPER_SCORER][s]["substitutions"]
                + arms[a]["scores"][WHISPER_SCORER][s]["deletions"]
                + arms[a]["scores"][WHISPER_SCORER][s]["insertions"]
            ),
            lambda a, s: (
                arms[a]["scores"][WHISPER_SCORER][s]["hits"]
                + arms[a]["scores"][WHISPER_SCORER][s]["substitutions"]
                + arms[a]["scores"][WHISPER_SCORER][s]["deletions"]
            ),
            left="A",
            right=arm,
            call_of=call_of,
        )
        agentic = pooled_delta(
            sample_ids,
            lambda a, s: float(arms[a]["charge"].get(s, 0)),
            lambda a, s: float(arms[a]["reference_words_of"][s]),
            left="A",
            right=arm,
            call_of=call_of,
        )
        left = {s: {"neg_wer": -arms["A"]["scores"][WHISPER_SCORER][s]["wer"]} for s in sample_ids}
        right = {s: {"neg_wer": -arms[arm]["scores"][WHISPER_SCORER][s]["wer"]} for s in sample_ids}
        per_row = paired_contrast(
            left,
            right,
            metrics=["neg_wer"],
            sample_ids=sample_ids,
            strata_of=lambda s: call_of[s],
            seed=SEED,
            n_replicates=N_REPLICATES,
            ci_level=CI_LEVEL,
        )["neg_wer"]
        contrasts[arm] = {
            "cell": CELLS[arm]["cell"],
            "factor": CELLS[arm]["factor"],
            "corpus_wer_delta_points": wer,
            "agentic_delta_points": agentic,
            "per_row_wer": {
                "saves": per_row.saves,
                "harms": per_row.harms,
                "ties": per_row.ties,
                "sign_test_p": round(per_row.sign_test_p, 6),
                "mean_per_utterance_wer_delta_points": round(-100.0 * per_row.delta, 4),
            },
            "decision": decide(wer, agentic),
        }

    per_call = per_call_table(arms, sample_ids, call_of)
    summary = {
        "schema": ANALYSIS_VERSION,
        "exposure_row": EXPOSURE_ROW_ID,
        "preregistration": PREREGISTRATION,
        "population": {
            "roster_id": roster["roster_id"],
            "split_identity_hash": roster["split_identity_hash"],
            "roster_receipt": ROSTER_RELPATH,
            "roster_receipt_sha256": roster["receipt_sha256"],
            "rows": len(sample_ids),
            "strata": len(set(call_of.values())),
        },
        "comparator": dict(COMPARATOR),
        "identity_gate": gate,
        "contrasts": contrasts,
        "per_call_table": per_call,
        "weightings": weightings(arms, per_call, sample_ids),
        "duration_decomposition": duration_table(arms, sample_ids, roster["seconds_of"]),
        "arms": {
            arm: {
                key: block[key]
                for key in (
                    "run_id",
                    "attempt",
                    "outputs_sha256",
                    "agentic",
                    "taxonomy_totals",
                    "category_mass",
                    "verified_cross_check",
                    "error_shape_whisper",
                    "error_shape_saea_v1",
                )
            }
            for arm, block in arms.items()
        },
        "prediction_check_cell_b": prediction_check(
            repo_root, arms, sample_ids, call_of, texts
        ),
        "boundary": {
            "test_split_read": False,
            "model_contacts": 0,
            "gpu_hours": 0,
            "outbound_connection_attempts": outbound_attempts,
            "outbound_targets": list(outbound_targets),
            "statement": (
                "sealed score files, sealed outputs, the hash-pinned dev10 reference layer "
                "and segment table, the committed roster receipt and the committed cell (b) "
                "caps receipt. Nothing is re-flown, re-scored or post-processed."
            ),
        },
    }
    return summary, per_call_csv(per_call)


def per_call_csv(per_call: Sequence[Mapping[str, object]]) -> str:
    """The ten-call table as CSV. Identifiers and numbers only -- no dev sentence text."""

    columns = list(per_call[0])
    lines = [",".join(columns)]
    for row in per_call:
        lines.append(",".join(str(row[column]) for column in columns))
    return "\n".join(lines) + "\n"


def write_check_manifest(directory: Path) -> Path:
    """``MANIFEST.sha256`` over every file this verdict's receipt directory holds.

    The convention is this study's receipt convention -- ``<sha256> *<name>``,
    sorted by name, LF, no timestamp anywhere -- so two back-to-back writes of a
    deterministic read reproduce the same manifest. Both Earnings-22 verdict
    runners call this one function.
    """

    directory = Path(directory)
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    target = directory / "MANIFEST.sha256"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return target


__all__ = [
    "AGENTIC_MARGIN_POINTS",
    "ANALYSIS_VERSION",
    "CELLS",
    "COMPARATOR",
    "EXPOSURE_ROW_ID",
    "STOPCAP_PREDICTION",
    "UsageCellsError",
    "boundary_charge",
    "build_receipts",
    "category_mass",
    "decide",
    "duration_table",
    "high_impact_charge",
    "identity_gate",
    "load_roster",
    "load_score_rows",
    "per_call_csv",
    "per_call_table",
    "pooled_charge_points",
    "pooled_delta",
    "prediction_check",
    "scan",
    "verified_cross_check",
    "weightings",
    "write_check_manifest",
]
