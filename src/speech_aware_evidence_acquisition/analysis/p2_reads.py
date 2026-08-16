"""P2 R-ladder offline read suite (pinned, pre-registered).

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory -- it scores already-written
``<run_id>.outputs.jsonl`` / replay-derivation / trace files through the
SAME frozen scoring stack every other offline read in this study uses
(``core.scorers.score_asr_outputs`` / ``score_entity_wer_outputs``), plus
the same replay-loop guard predicates the copy-count salvage read used
(``reproduction.replay_loop._reference_echo_reject`` /
``_unsupported_reference_word``, ``core.retrieval.normalize_term``).

Sources of truth this module implements EXACTLY (never re-derives on its
own authority):

- ``docs/arms/p2-rladder.arms`` / ``docs/arms/p2-rladder-resume.arms``: the
  frozen ten, the PRE-REGISTERED READS, the BRANCH RULES, and the four
  zero-oracle-candidate calls (4365024/4365948/4366429/4384964) that fly
  legitimate-empty -> paired Wilcoxon effective n=6.
- ``docs/p2-metric-definitions-mirror.md``: the HER and RIR formulas
  verbatim, including the <10 denominator guard (below 10 -> descriptive
  only, falls back to raw counts; if those degenerate too -> UNRESOLVED,
  never silently passed/failed).

DEVELOPED AND TESTED EXCLUSIVELY AGAINST HAND-AUTHORED SYNTHETIC FIXTURES
(``tests/unit/test_p2_reads.py``). This module is never run against real
data by the task that wrote it; a later caller points ``read_arm``/
``build_p2_report`` at the real COMPLETED attempt directories.

ENGINEERING-INTERPRETATION NOTES (flagged here, not buried, because the
pre-registration text is genuinely underspecified on these exact points --
each is a documented, reviewable choice, not a silent guess):

1. HER's "score the affected span against the ALIGNED gold span" (mirror
   section 3) has no hypothesis-side backtrace anywhere in the frozen
   scoring stack (``scoring.wer.align`` exposes only a per-reference-
   position hit mask -- see ``core.scorers``'s own docstring on this exact
   limitation). This module resolves a span's gold alignment by calling the
   SAME frozen ``core.scorers.score_asr_outputs`` / ``score_entity_wer_
   outputs`` this whole suite already reuses, with the span's own text
   substituted as if it were the FULL hypothesis for that sample -- i.e.
   the span is scored against the full sample reference (and, for the
   entity ledger, the full reference's entity set) exactly the way a
   complete hypothesis would be. This is a real re-use of the frozen
   scorers, not a new alignment algorithm, and it is also what keeps this
   module outside the reference-import isolation contract (only
   ``core/scorers.py`` may import ``data.references`` --
   ``tests/contract/test_reference_import_isolation.py``): this module
   never reads a reference layer directly, only through those two already-
   sanctioned entry points. See ``_score_span_errors``.
2. RIR's "correct form appears in the candidate set delivered to that
   call" is read literally: the denominator/numerator units are the
   DELIVERED items themselves (``replay_candidates[].text`` and
   ``replay_exemplars_attached`` labels), not an independently-resolved
   gold entity identity -- RIR's own definition already names delivered
   content as the correct form, so no reference-layer lookup is needed
   (same import-isolation reasoning as note 1). "Wrong in the pass-1
   hypothesis" is evaluated against the SAME window's own
   ``replay_pass1_text`` (the span-local pre-replay text), which is also a
   faithful scoping rather than a mere convenience: content outside every
   flagged span was never a replay candidate at all, so RIR's substrate is
   naturally the flagged-span population. See ``extract_rir_records``.
3. The bare branch-rule clause "(R2-R1>0)" (arms file, BRANCH RULES) names
   no ledger and no explicit improvement polarity. This module resolves it
   on the entity-correct-token delta (the ledger the pre-registration
   itself treats as decisive under the n=6 restriction -- "entity ledger
   co-primary compensates") and prints the macro-WER delta alongside for
   transparency, but does NOT silently treat that resolution as itself
   pre-registered -- see ``evaluate_branch_rules``'s own docstring and the
   printed caveat in ``BranchVerdict.clause_a_note``.
4. "Wrong-reference copying in R1/R2 voids the audio-verification claim"
   (arms file) is evaluated against ``r1wrong`` (the only registered R1
   arm under an actually-wrong reference) AND ``r2draft`` (which has no
   wrongref sibling arm in this 5-arm block, but whose delivered
   "reference" IS the model's own unverified draft -- the same
   self-referential-copy hazard the D4 screen already confirmed as
   ANCHORING for this framing, ``docs/exposure-ledger.md`` SAEA-D4-r2draft
   row). The SAME generic copy-count machinery applies to both without
   special-casing, because for every arm "the delivered reference" is
   whatever ``replay_candidates``/``replay_exemplars_attached`` actually
   carried for that call, correct or not.
5. "Format-normalized secondary" has no formula anywhere in the repository
   (unlike HER/RIR, no amendment record exists for it). This module
   implements it as the SAME frozen ``align``/``tokens_v1`` pipeline with
   both reference and hypothesis additionally passed through
   ``core.retrieval.normalize_term`` first (no new WER logic; only the
   token-normalization INPUT changes) -- see ``format_normalized_wer``.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from ..core.scorers import (
    ScoringPhaseError,
    score_asr_outputs,
    score_entity_wer_outputs,
)
from ..scoring import WerResult, align, tokens_v1
from ..scoring.transitions import TransitionCounts, flag_transitions
from .context_dose import (
    ComparisonError,
    WilcoxonResult,
    find_completed_attempt,
    wilcoxon_signed_rank_exact,
)

REPORT_SCHEMA = "saea-p2-reads-v1"

ARM_NAMES: tuple[str, ...] = ("r0bias", "r1verify", "r2draft", "r0wrong", "r1wrong")
CORRECT_REFERENCE_ARMS: tuple[str, ...] = ("r0bias", "r1verify", "r2draft")
WRONGREF_ARMS: tuple[str, ...] = ("r0wrong", "r1wrong")

# The co-primary paired call-level contrasts the arms file's PRE-REGISTERED
# READS name: R1 vs R0-bias, R2 vs R1 (both ledgers), plus the wrongref
# pairs needed to evaluate the branch rule's wrongref clause and the
# framing x reference-correctness interaction the SAEA-P2-r1wrong row
# itself names ("the framing x reference-correctness interaction with arm
# 4/5 is the mechanistic signature").
CONTRASTS: tuple[tuple[str, str, str], ...] = (
    ("r1verify_vs_r0bias", "r1verify", "r0bias"),
    ("r2draft_vs_r1verify", "r2draft", "r1verify"),
    ("r0wrong_vs_r0bias", "r0wrong", "r0bias"),
    ("r1wrong_vs_r1verify", "r1wrong", "r1verify"),
    ("r1wrong_vs_r0wrong", "r1wrong", "r0wrong"),
)

LEDGERS: tuple[str, ...] = ("macro", "entity")

# HER / RIR degenerate-denominator guard (docs/p2-metric-definitions-mirror.md
# sections 3.1 / 4.1, IDENTICAL for both metrics): below this, the rate is
# descriptive only.
GUARD_DENOMINATOR_FLOOR = 10

GuardStatus = Literal["resolved", "descriptive_only"]


class P2ReadsError(RuntimeError):
    """Malformed input to a pure computation, or a fail-closed condition in
    the offline extraction layer (never raised for a real arm's legitimate
    data shape -- those are guard-bound results, not errors)."""


# ---------------------------------------------------------------------------
# Degenerate-denominator guard (HER section 3.1, RIR section 4.1 -- the SAME
# rule, applied twice).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GuardedRate:
    """A rate that MUST NOT be read bare: the raw numerator/denominator ride
    alongside always (mirror section 3: "A bare rate without its counts is
    not a reportable HER value"), and ``status`` names whether the rate
    itself is decision-grade (``"resolved"``, denominator >= floor) or
    descriptive-only (``"descriptive_only"``, denominator < floor -- a
    caller deciding a branch clause from this MUST fall back to comparing
    raw counts, never the rate)."""

    label: str
    numerator: int
    denominator: int
    rate: float | None
    status: GuardStatus
    note: str


def guarded_rate(numerator: int, denominator: int, *, label: str) -> GuardedRate:
    if numerator < 0 or denominator < 0:
        raise P2ReadsError(f"{label}: numerator/denominator must be non-negative, got {numerator}/{denominator}")
    if numerator > denominator:
        raise P2ReadsError(f"{label}: numerator {numerator} exceeds denominator {denominator}")
    if denominator == 0:
        return GuardedRate(
            label=label, numerator=numerator, denominator=denominator, rate=None,
            status="descriptive_only",
            note=f"{label}: denominator is 0 -- no units at all; the rate is undefined.",
        )
    if denominator < GUARD_DENOMINATOR_FLOOR:
        return GuardedRate(
            label=label, numerator=numerator, denominator=denominator,
            rate=numerator / denominator, status="descriptive_only",
            note=(
                f"{label}: denominator {denominator} < {GUARD_DENOMINATOR_FLOOR} -- rate is "
                "descriptive only per the mandatory guard; must not decide a branch rule on its "
                "own, fall back to raw counts."
            ),
        )
    return GuardedRate(
        label=label, numerator=numerator, denominator=denominator,
        rate=numerator / denominator, status="resolved",
        note=f"{label}: resolved ({numerator}/{denominator} = {numerator / denominator:.4f}).",
    )


RawCountVerdict = Literal["favors_a", "favors_b", "tie", "unresolved"]


def compare_via_raw_counts(a: GuardedRate, b: GuardedRate, *, lower_is_better: bool) -> RawCountVerdict:
    """The guard's own mandated fallback when a rate is ``descriptive_only``:
    compare the RAW numerator counts directly. ``unresolved`` iff EITHER
    side's denominator is 0 (mirror: "if those [counts] are also degenerate
    -> UNRESOLVED, never silently passed, never silently failed") -- a
    denominator-0 side has no units to count at all, so even a raw-count
    comparison carries no information. An exact tie in the raw counts is
    reported as ``"tie"`` (not unresolved -- the counts ARE informative,
    they just do not favor either side), consistent with this module's
    strict-inequality convention elsewhere ("equality is not harm")."""

    if a.denominator == 0 or b.denominator == 0:
        return "unresolved"
    if a.numerator == b.numerator:
        return "tie"
    a_better = a.numerator < b.numerator if lower_is_better else a.numerator > b.numerator
    return "favors_a" if a_better else "favors_b"


# ---------------------------------------------------------------------------
# HER -- Harmful Edit Rate (mirror section 3).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpliceScore:
    """One accepted replay splice's pass-1 vs post-splice span error, on
    both ledgers -- the unit of analysis for HER. Errors are raw counts
    (substitutions+deletions+insertions against the aligned gold span), not
    rates; see module docstring note 1 for how "the aligned gold span" is
    resolved."""

    sample_id: str
    window_iteration: int | None
    span_index: int | None
    macro_pass1_errors: int
    macro_post_errors: int
    entity_pass1_errors: int
    entity_post_errors: int


def splice_is_harmful(splice: SpliceScore, ledger: str) -> bool:
    """"Harmful on a ledger" iff post-splice span error is STRICTLY greater
    than pass-1 span error on that ledger. Equality is not harm (mirror
    section 3, verbatim)."""

    if ledger == "macro":
        return splice.macro_post_errors > splice.macro_pass1_errors
    if ledger == "entity":
        return splice.entity_post_errors > splice.entity_pass1_errors
    raise P2ReadsError(f"unknown ledger {ledger!r}; expected one of {LEDGERS}")


@dataclass(frozen=True)
class HERResult:
    ledger: str
    harmful_splices: int
    accepted_splices: int
    rate: GuardedRate
    harmful_sample_ids: tuple[str, ...]


def compute_her(splices: Sequence[SpliceScore], ledger: str) -> HERResult:
    """HER = (harmful accepted splices) / (accepted splices), per ledger,
    with the mandatory <10 guard (mirror section 3.1)."""

    harmful = [s for s in splices if splice_is_harmful(s, ledger)]
    rate = guarded_rate(len(harmful), len(splices), label=f"HER[{ledger}]")
    return HERResult(
        ledger=ledger,
        harmful_splices=len(harmful),
        accepted_splices=len(splices),
        rate=rate,
        harmful_sample_ids=tuple(s.sample_id for s in harmful),
    )


# ---------------------------------------------------------------------------
# RIR -- recoverable-information ratio (mirror section 4).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RIRTokenRecord:
    """One entity-mention observation against one replay window, the unit
    of analysis for RIR (mirror section 4). ``wrong_in_pass1`` and
    ``correct_form_delivered`` together gate membership in the
    denominator; ``correct_in_final`` gates membership in the numerator
    (denominator members only)."""

    sample_id: str
    entity_id: str
    wrong_in_pass1: bool
    correct_form_delivered: bool
    correct_in_final: bool


@dataclass(frozen=True)
class RIRResult:
    numerator: int
    denominator: int
    rate: GuardedRate
    # F1: an RIR read built from the r0bias salvage archive cannot derive
    # this metric at all (the preserved JSONs carry no per-window delivered-
    # candidate/final-hypothesis identity) -- rather than fabricate a 0/0
    # read indistinguishable from a genuinely-degenerate one, that path sets
    # ``available=False`` with ``unavailable_reason`` explaining why. RIR
    # feeds no branch-rule clause, so this never blocks a verdict.
    available: bool = True
    unavailable_reason: str | None = None


def compute_rir(records: Sequence[RIRTokenRecord]) -> RIRResult:
    denominator_records = [r for r in records if r.wrong_in_pass1 and r.correct_form_delivered]
    numerator_records = [r for r in denominator_records if r.correct_in_final]
    rate = guarded_rate(len(numerator_records), len(denominator_records), label="RIR")
    return RIRResult(numerator=len(numerator_records), denominator=len(denominator_records), rate=rate)


# ---------------------------------------------------------------------------
# format-normalized secondary (module docstring note 5).
# ---------------------------------------------------------------------------


def format_normalized_wer(reference_raw_tokens: Sequence[str], hypothesis_text: str) -> WerResult:
    """Secondary WER: the SAME frozen ``align``/``tokens_v1`` pipeline
    ``core.scorers.score_asr_outputs`` uses, with both sides additionally
    passed through ``core.retrieval.normalize_term`` before tokenization --
    no new alignment/scoring logic, only the normalization INPUT changes
    (module docstring note 5)."""

    from ..core.retrieval import normalize_term

    ref = tokens_v1(normalize_term(" ".join(reference_raw_tokens)))
    hyp = tokens_v1(normalize_term(hypothesis_text))
    return align(ref, hyp)


# ---------------------------------------------------------------------------
# Wrong-reference COPY COUNT, measured on PRE-LOCALIZE replay text (the D7E
# guard-2 aperture note) -- reuses reproduction.replay_loop's own guard
# predicates and core.retrieval.normalize_term, exactly as the r0bias
# salvage's copycount_r0bias.py did (docs/checks/.../2026-08-16-p2-r0bias-
# salvage/copycount_r0bias.py), with one correction: replay_exemplars_
# attached is a flat list of label strings/None in the authoritative
# runtime schema (reproduction/replay_loop.py, REPLAY window record
# construction), not a list of {"label": ...} mappings -- the salvage
# script's `.get('label')` on each entry only avoided crashing because
# R0-bias's own framing never attaches exemplars, so that code path went
# unexercised there.
# ---------------------------------------------------------------------------


def delivered_reference_text(window: Mapping[str, object]) -> str:
    parts = [str(c["text"]) for c in (window.get("replay_candidates") or [])]
    for label in (window.get("replay_exemplars_attached") or []):
        if isinstance(label, str) and label:
            parts.append(label)
    return " ".join(parts)


def _contains_subsequence(haystack: Sequence[str], needle: Sequence[str]) -> bool:
    n, m = len(haystack), len(needle)
    if m == 0 or m > n:
        return False
    return any(haystack[i : i + m] == needle for i in range(n - m + 1))


def _count_subsequence(haystack: Sequence[str], needle: Sequence[str]) -> int:
    n, m = len(haystack), len(needle)
    if m == 0 or m > n:
        return 0
    return sum(1 for i in range(n - m + 1) if haystack[i : i + m] == needle)


@dataclass(frozen=True)
class CopyCountResult:
    arm: str
    total_windows: int
    called_windows: int
    accepted_splices: int
    total_copy_occurrences: int
    windows_with_copy: int
    novel_copies: int
    guard3_unsupported: int
    copy_window_sample_ids: tuple[str, ...]

    @property
    def copy_rate(self) -> float:
        """windows-with->=1-copy / called-windows -- 0.0 when no window ever
        received a call (never a bare ZeroDivisionError; a report reads this
        alongside the raw counts above, never in isolation)."""

        return self.windows_with_copy / self.called_windows if self.called_windows else 0.0


def copy_count_for_arm(arm: str, windows: Sequence[Mapping[str, object]]) -> CopyCountResult:
    """F9 correction: verbatim-copy DETECTION below uses this module's OWN
    ``_count_subsequence`` (a plain occurrence counter), never
    ``reproduction.replay_loop._reference_echo_reject`` -- an earlier
    revision of this docstring claimed that reuse, but ``_reference_echo_
    reject`` is a boolean strict-echo REJECTION predicate (Guard 2), not a
    verbatim-occurrence counter, and this function never imports it.
    ``core.retrieval.normalize_term`` IS reused directly for both the copy
    count and the ``guard3_unsupported`` read below (Guard 3's own
    ``_unsupported_reference_word`` predicate, reused unchanged). Measured
    on ``replay_replay_text`` (the RAW, PRE-LOCALIZE replay transcript), per
    the D7E guard-2 aperture note the arms file's own PRE-REGISTERED READS
    cite; a window with no model call (``replay_replay_text is None``, the
    legitimate-empty "no-candidates" skip path) contributes zero to every
    count here but is still counted in ``total_windows``."""

    from ..core.retrieval import normalize_term

    called = [w for w in windows if w.get("replay_replay_text") is not None]
    total_occurrences = 0
    windows_with_copy = 0
    novel = 0
    with_copy_ids: list[str] = []
    for window in called:
        reference_text = delivered_reference_text(window)
        pre_text = str(window["replay_replay_text"])
        pass1_text = str(window.get("replay_pass1_text") or "")
        ref_tokens = normalize_term(reference_text).split()
        pre_tokens = normalize_term(pre_text).split()
        p1_tokens = normalize_term(pass1_text).split()
        if not ref_tokens:
            continue
        occurrences = _count_subsequence(pre_tokens, ref_tokens)
        if occurrences <= 0:
            continue
        total_occurrences += occurrences
        windows_with_copy += 1
        with_copy_ids.append(str(window.get("replay_sample_id", "")))
        if _count_subsequence(p1_tokens, ref_tokens) == 0:
            novel += 1

    guard3 = 0
    try:
        from ..reproduction.replay_loop import _unsupported_reference_word
    except ImportError as error:  # pragma: no cover - defensive only
        raise P2ReadsError(f"cannot import replay-loop guard predicates: {error}") from error
    # F9: unlike the copy-occurrence count above (measured on ``pre_tokens``,
    # i.e. PRE-localize), this guard-3 read is measured on POST-localize
    # words (``replay_localized_words``) -- a real inconsistency against the
    # D7E pre-localize aperture note this function's own docstring and the
    # module comment above cite. Left uncorrected here rather than silently
    # re-apertured: ``guard3_unsupported`` is purely descriptive and feeds
    # no branch-rule clause, so changing its substrate would be a silent
    # behavior change with no registered read depending on it. A future
    # revision that DOES want guard-3 measured pre-localize should pass
    # ``pre_tokens`` (from ``replay_replay_text``) here instead of
    # ``localized_words``.
    for window in called:
        reference_text = delivered_reference_text(window)
        localized_words = [str(w) for w in (window.get("replay_localized_words") or [])]
        pass1_text = str(window.get("replay_pass1_text") or "")
        if _unsupported_reference_word(localized_words, reference_text, pass1_text.split()):
            guard3 += 1

    accepted = sum(1 for w in windows if w.get("replay_accepted"))
    return CopyCountResult(
        arm=arm,
        total_windows=len(windows),
        called_windows=len(called),
        accepted_splices=accepted,
        total_copy_occurrences=total_occurrences,
        windows_with_copy=windows_with_copy,
        novel_copies=novel,
        guard3_unsupported=guard3,
        copy_window_sample_ids=tuple(with_copy_ids),
    )


# ---------------------------------------------------------------------------
# Per-call metrics + paired call-level Wilcoxon contrasts (co-primary,
# macro WER and entity-WER), with the four zero-oracle-candidate calls
# excluded per arm as "legitimate-empty" -> effective n=6.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerCallMetrics:
    sample_id: str
    macro_wer: float
    macro_ref_hit_mask: tuple[bool, ...]
    entity_wer: float
    entity_correct: int
    entity_expected_total: int
    legitimate_empty: bool


def _ledger_value(metrics: PerCallMetrics, ledger: str) -> float:
    if ledger == "macro":
        return metrics.macro_wer
    if ledger == "entity":
        return metrics.entity_wer
    raise P2ReadsError(f"unknown ledger {ledger!r}; expected one of {LEDGERS}")


@dataclass(frozen=True)
class PerCallRow:
    sample_id: str
    condition_value: float
    reference_value: float
    diff: float
    macro_transitions: TransitionCounts | None
    entity_correct_delta: int


@dataclass(frozen=True)
class ContrastResult:
    name: str
    condition_arm: str
    reference_arm: str
    ledger: str
    included_sample_ids: tuple[str, ...]
    excluded_legitimate_empty: tuple[str, ...]
    diffs: tuple[float, ...]
    wilcoxon: WilcoxonResult
    per_call: tuple[PerCallRow, ...]
    # F8 / Pin 1: "Any cross-arm contrast must state both sources." Defaults
    # preserve every pre-existing direct construction of this dataclass
    # (hand-built fixtures in tests/unit/test_p2_reads.py); build_p2_report
    # always threads the real per-arm ArmRead.source through explicitly.
    condition_source: str = "completed-attempt"
    reference_source: str = "completed-attempt"


def build_wilcoxon_contrast(
    name: str,
    condition_arm: str,
    reference_arm: str,
    ledger: str,
    condition_calls: Mapping[str, PerCallMetrics],
    reference_calls: Mapping[str, PerCallMetrics],
    *,
    condition_source: str = "completed-attempt",
    reference_source: str = "completed-attempt",
) -> ContrastResult:
    if set(condition_calls) != set(reference_calls):
        raise P2ReadsError(
            f"contrast {name!r} cannot pair {condition_arm!r} against {reference_arm!r}: "
            f"sample ids differ ({sorted(set(condition_calls) ^ set(reference_calls))})"
        )
    common = sorted(condition_calls)
    excluded = tuple(
        sample_id
        for sample_id in common
        if condition_calls[sample_id].legitimate_empty or reference_calls[sample_id].legitimate_empty
    )
    included = tuple(sample_id for sample_id in common if sample_id not in excluded)

    per_call: list[PerCallRow] = []
    diffs: list[float] = []
    for sample_id in included:
        condition = condition_calls[sample_id]
        reference = reference_calls[sample_id]
        condition_value = _ledger_value(condition, ledger)
        reference_value = _ledger_value(reference, ledger)
        diff = condition_value - reference_value
        diffs.append(diff)
        macro_transitions = (
            flag_transitions(reference.macro_ref_hit_mask, condition.macro_ref_hit_mask)
            if ledger == "macro"
            else None
        )
        per_call.append(
            PerCallRow(
                sample_id=sample_id,
                condition_value=condition_value,
                reference_value=reference_value,
                diff=diff,
                macro_transitions=macro_transitions,
                entity_correct_delta=condition.entity_correct - reference.entity_correct,
            )
        )
    wilcoxon = wilcoxon_signed_rank_exact(diffs)
    return ContrastResult(
        name=name,
        condition_arm=condition_arm,
        reference_arm=reference_arm,
        ledger=ledger,
        included_sample_ids=included,
        excluded_legitimate_empty=excluded,
        diffs=tuple(diffs),
        wilcoxon=wilcoxon,
        per_call=tuple(per_call),
        condition_source=condition_source,
        reference_source=reference_source,
    )


# ---------------------------------------------------------------------------
# per-term flip lists (PRE-REGISTERED READS).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TermFlipList:
    condition_arm: str
    reference_arm: str
    flipped_to_correct: tuple[str, ...]
    flipped_to_wrong: tuple[str, ...]


def per_term_flip_list(
    condition_arm: str,
    reference_arm: str,
    reference_correct_terms: set[str],
    condition_correct_terms: set[str],
) -> TermFlipList:
    """Terms (normalized via ``core.retrieval.normalize_term`` by the
    caller before this function sees them) whose correctness flips between
    ``reference_arm`` and ``condition_arm`` -- entity mentions correct in
    one arm's final hypothesis and not the other's, for ONE sample or
    aggregated across a whole arm pair, at the caller's choice."""

    return TermFlipList(
        condition_arm=condition_arm,
        reference_arm=reference_arm,
        flipped_to_correct=tuple(sorted(condition_correct_terms - reference_correct_terms)),
        flipped_to_wrong=tuple(sorted(reference_correct_terms - condition_correct_terms)),
    )


# ---------------------------------------------------------------------------
# Mechanical branch-rule evaluator (arms file BRANCH RULES, verbatim below).
# ---------------------------------------------------------------------------

BRANCH_RULES_TEXT = (
    "BRANCH RULES (registered before launch): operator AFFIRMED iff at "
    "least one of (R2-R1>0) / (R1 beats R0-bias at matched entity gain "
    "with lower HER) / (wrongref copy rate materially lower under verify "
    "than bias framing). Taxonomy COLLAPSE iff R1~R0-bias on both ledgers "
    "and HER AND R2~R1 - then the 2026-08-14/15 scope amendments are "
    "re-amended, the candidate keeps targeting/small-N wording, no "
    '"different operator" language. Wrong-reference copying in R1/R2 '
    "voids the audio-verification claim regardless of WER deltas."
)

ClauseVerdict = Literal["met", "not_met", "unresolved"]


@dataclass(frozen=True)
class ClauseResult:
    clause_text: str
    verdict: ClauseVerdict
    detail: str


@dataclass(frozen=True)
class BranchVerdict:
    voided: bool
    voiding_clause: ClauseResult
    # F3 / Pin 6: a raw wrong-reference copy count of exactly 1 (on r1wrong
    # or r2draft) does not void the claim but must be surfaced as a
    # material weakening; None when neither side sits at exactly 1.
    weakening_note: str | None
    affirm: ClauseVerdict
    affirm_clauses: tuple[ClauseResult, ClauseResult, ClauseResult]
    collapse: ClauseVerdict
    collapse_clauses: tuple[ClauseResult, ...]
    overall: str
    registered_text: str = BRANCH_RULES_TEXT


def _clause_a_r2_beats_r1(
    entity_contrast: ContrastResult, macro_contrast: ContrastResult
) -> ClauseResult:
    """"(R2-R1>0)". Pin 2: fires iff BOTH co-primary ledgers agree -- paired
    entity-correct total STRICTLY HIGHER under R2-draft AND paired macro
    WER STRICTLY LOWER under R2-draft, over the effective paired calls
    (conjunctive; F4, superseding the prior entity-only engineering
    interpretation). A mixed result (the ledgers disagree) does NOT fire
    the limb and is reported "not_met" along a "mixed" detail path (Pin 2:
    "A mixed result does not fire the limb and is reported as mixed")."""

    clause_text = "(R2-R1>0)"
    if not entity_contrast.per_call or not macro_contrast.diffs:
        return ClauseResult(clause_text, "unresolved", "no paired calls survive the legitimate-empty exclusion")
    entity_delta = sum(row.entity_correct_delta for row in entity_contrast.per_call)
    macro_delta = statistics.fmean(macro_contrast.diffs)
    entity_up = entity_delta > 0
    macro_down = macro_delta < 0
    if entity_up and macro_down:
        verdict: ClauseVerdict = "met"
        path = "both ledgers agree (entity strictly up, macro strictly down)"
    elif entity_up or macro_down:
        verdict = "not_met"
        path = "mixed (ledgers disagree)"
    else:
        verdict = "not_met"
        path = "neither ledger moved in R2's favor"
    detail = (
        f"PIN 2 (conjunctive, both ledgers required): entity-correct delta R2-R1 = {entity_delta:+d} "
        f"across {len(entity_contrast.per_call)} paired call(s) "
        f"({'strictly up' if entity_up else 'not up'}); mean macro-WER delta R2-R1 = "
        f"{macro_delta:+.4f} ({'strictly down' if macro_down else 'not down'}); path={path}"
    )
    return ClauseResult(clause_text, verdict, detail)


# Pin 3 / Pin 5: the tie margin in entity-correct TOKENS -- "not lower than
# R0-bias's by more than 25 tokens" (clause B's "matched entity gain") and
# the COLLAPSE entity-ledger equivalence (F6) both use this SAME margin.
MATCHED_GAIN_TOKEN_MARGIN = 25


def _clause_b_r1_beats_r0bias(
    entity_contrast: ContrastResult,
    her_r1: HERResult,
    her_r0bias: HERResult,
    *,
    token_margin: int = MATCHED_GAIN_TOKEN_MARGIN,
) -> ClauseResult:
    """"(R1 beats R0-bias at matched entity gain with lower HER)". Pin 3:
    "matched entity gain" means R1-verify's entity-correct total is NOT
    LOWER than R0-bias's by more than the tie margin (``token_margin``,
    Pin 5's 25 tokens) -- i.e. ``entity_delta >= -token_margin``, not a
    strict R1>R0bias requirement (F5). "Lower HER": strictly fewer harmful
    accepted splices, guard-aware (mirror 3.1 / Pin 3); when the guard-bound
    raw-count fallback is ITSELF degenerate -- ``compare_via_raw_counts``
    returns "tie" (equal raw harmful counts, including the literal 0-vs-0
    case) or "unresolved" (a zero-denominator side) -- this clause is
    UNRESOLVED, never silently resolved toward ``not_met`` (Pin 3: "if raw
    counts are degenerate ... the limb is UNRESOLVED"; F5)."""

    clause_text = "(R1 beats R0-bias at matched entity gain with lower HER)"
    if not entity_contrast.per_call:
        return ClauseResult(clause_text, "unresolved", "no paired calls survive the legitimate-empty exclusion")
    entity_delta = sum(row.entity_correct_delta for row in entity_contrast.per_call)
    entity_matched = entity_delta >= -token_margin
    if her_r1.rate.status == "resolved" and her_r0bias.rate.status == "resolved":
        assert her_r1.rate.rate is not None and her_r0bias.rate.rate is not None
        her_lower = her_r1.rate.rate < her_r0bias.rate.rate
        her_detail = f"HER[entity] r1verify={her_r1.rate.rate:.4f} vs r0bias={her_r0bias.rate.rate:.4f} (rate-decided)"
    else:
        raw = compare_via_raw_counts(her_r1.rate, her_r0bias.rate, lower_is_better=True)
        if raw in ("unresolved", "tie"):
            return ClauseResult(
                clause_text, "unresolved",
                f"HER guard-bound (mirror 3.1) and raw harmful-splice counts degenerate ({raw}) -- "
                f"Pin 3/F5: UNRESOLVED rather than silently passed/failed; r1verify "
                f"{her_r1.harmful_splices}/{her_r1.accepted_splices}, r0bias "
                f"{her_r0bias.harmful_splices}/{her_r0bias.accepted_splices}",
            )
        her_lower = raw == "favors_a"
        her_detail = (
            f"HER guard-bound (mirror 3.1, denominator < {GUARD_DENOMINATOR_FLOOR}): fell back to "
            f"raw harmful-splice counts r1verify={her_r1.harmful_splices}/{her_r1.accepted_splices} "
            f"vs r0bias={her_r0bias.harmful_splices}/{her_r0bias.accepted_splices} ({raw})"
        )
    verdict: ClauseVerdict = "met" if entity_matched and her_lower else "not_met"
    detail = (
        f"PIN 3 matched-entity-gain margin={token_margin}: entity delta R1-R0bias = "
        f"{entity_delta:+d} ({'matched' if entity_matched else 'not matched'}); {her_detail}"
    )
    return ClauseResult(clause_text, verdict, detail)


def _clause_c_wrongref_copy_rate(
    copy_r1wrong: CopyCountResult,
    copy_r0wrong: CopyCountResult,
    *,
    material_relative_drop: float = 0.50,
    c_bias_floor: int = 4,
) -> ClauseResult:
    """"(wrongref copy rate materially lower under verify than bias
    framing)". Pin 4: basis is the RAW ``total_copy_occurrences`` count
    (F2 -- NOT ``windows_with_copy``/``called_windows`` rate); the limb
    fires iff ``C_verify <= material_relative_drop * C_bias`` (Pin 4's
    registered 50% factor) AND ``C_bias >= c_bias_floor`` (Pin 4's
    registered floor of 4). Below the floor the copy-opportunity base is
    too thin to say anything and the clause is UNRESOLVED -- never
    met/not_met (F2, replacing the prior bare ``bias_rate==0.0 ->
    not_met``)."""

    clause_text = "(wrongref copy rate materially lower under verify than bias framing)"
    c_bias = copy_r0wrong.total_copy_occurrences
    c_verify = copy_r1wrong.total_copy_occurrences
    if c_bias < c_bias_floor:
        return ClauseResult(
            clause_text, "unresolved",
            f"PIN 4: C_bias (raw total_copy_occurrences, r0wrong) = {c_bias} < floor {c_bias_floor} "
            "-- the copy-opportunity base is too thin (insufficient opportunities); never passed "
            f"or failed. C_verify (r1wrong) = {c_verify}.",
        )
    verdict: ClauseVerdict = "met" if c_verify <= material_relative_drop * c_bias else "not_met"
    relative_drop = (c_bias - c_verify) / c_bias
    detail = (
        f"PIN 4 basis=raw total_copy_occurrences, material_relative_drop={material_relative_drop:.2f}, "
        f"c_bias_floor={c_bias_floor}: C_bias(r0wrong)={c_bias}, C_verify(r1wrong)={c_verify}, "
        f"threshold C_verify <= {material_relative_drop * c_bias:.2f}, relative_drop={relative_drop:+.4f}"
    )
    return ClauseResult(clause_text, verdict, detail)


def _voiding_clause(
    copy_r1wrong: CopyCountResult, copy_r2draft: CopyCountResult
) -> tuple[ClauseResult, str | None]:
    """"Wrong-reference copying in R1/R2 voids the audio-verification
    claim regardless of WER deltas." Pin 6 (F3): basis is the RAW copy
    count (``total_copy_occurrences``, NOT ``windows_with_copy``); void iff
    that count is >= 2 on EITHER side -- ``r1wrong`` (wrong-reference echo)
    or ``r2draft`` (own-draft anchoring, module docstring note 4). A count
    of EXACTLY 1 on a side does NOT void, but Pin 6 requires it be reported
    as a material weakening of the claim; that note is returned separately
    (never silently absorbed into the boolean verdict) so callers can
    surface it independently (F3).

    Note: because clause C's own "materially lower" test (Pin 4) requires
    ``C_verify > 0.5 * C_bias`` with ``C_bias >= 4`` whenever it resolves
    "not_met", ``C_verify`` in that branch is always >= 3 -- i.e. a
    cleanly-resolved-"not_met" clause C on the SAME r1wrong arm always
    co-occurs with voiding here. This is an intended interlock (copying
    the wrong reference often enough to not be "materially lower" than the
    bias framing IS, definitionally, copying it >= 2 times), not a bug."""

    clause_text = (
        "Wrong-reference copying in R1/R2 voids the audio-verification claim regardless of "
        "WER deltas."
    )
    c1 = copy_r1wrong.total_copy_occurrences
    c2 = copy_r2draft.total_copy_occurrences
    voided = c1 >= 2 or c2 >= 2
    verdict: ClauseVerdict = "met" if voided else "not_met"
    detail = (
        f"PIN 6 basis=raw total_copy_occurrences (void iff >= 2 on either side): r1wrong={c1} "
        f"(wrong-reference echo); r2draft={c2} (own-draft anchoring, module docstring note 4)"
    )
    weak_sides = []
    if c1 == 1:
        weak_sides.append(f"r1wrong={c1}")
    if c2 == 1:
        weak_sides.append(f"r2draft={c2}")
    weakening_note = None
    if not voided and weak_sides:
        weakening_note = (
            f"PIN 6 material weakening: exactly 1 raw wrong-reference copy on {', '.join(weak_sides)} "
            "-- does not void the audio-verification claim, but is reported as a material weakening "
            "per the registered rule's exact-1 carve-out."
        )
    return ClauseResult(clause_text, verdict, detail), weakening_note


# Pin 5 (F6): the macro-WER equivalence tie floor, in FRACTIONAL WER units
# -- 0.001 = 0.10 percentage points ("|paired macro WER difference| <= 0.10
# percentage points").
COLLAPSE_MACRO_TIE_FLOOR = 0.001


def _collapse_clause_macro_similarity(
    contrast: ContrastResult, *, tie_floor: float = COLLAPSE_MACRO_TIE_FLOOR
) -> ClauseResult:
    """"R1~R0-bias" / "R2~R1" on the MACRO-WER ledger (Pin 5): the paired
    mean WER difference sits within ``tie_floor`` (0.10pp, F6) of zero, or
    there are too few nonzero pairs to say anything (``n_effective == 0``)."""

    clause_text = f"{contrast.condition_arm}~{contrast.reference_arm} on {contrast.ledger}"
    if not contrast.diffs:
        return ClauseResult(clause_text, "unresolved", "no paired calls survive the legitimate-empty exclusion")
    mean_diff = statistics.fmean(contrast.diffs)
    similar = contrast.wilcoxon.n_effective == 0 or abs(mean_diff) <= tie_floor
    verdict: ClauseVerdict = "met" if similar else "not_met"
    detail = (
        f"PIN 5 tie_floor={tie_floor:.4f} fractional ({tie_floor * 100:.2f}pp): mean_diff={mean_diff:+.4f}, "
        f"wilcoxon n_effective={contrast.wilcoxon.n_effective}, p={contrast.wilcoxon.pvalue:.4g} "
        f"(floor {contrast.wilcoxon.min_two_sided_p:.4g})"
    )
    return ClauseResult(clause_text, verdict, detail)


def _collapse_clause_entity_similarity(
    contrast: ContrastResult, *, token_margin: int = MATCHED_GAIN_TOKEN_MARGIN
) -> ClauseResult:
    """"R1~R0-bias" / "R2~R1" on the ENTITY ledger (Pin 5, F6): compares the
    SUMMED ``entity_correct_delta`` against the 25-token margin -- NOT the
    ``entity_wer`` mean diff (F6's explicit correction). Entity-correct is
    the co-primary ledger's own unit, and Pin 5's 25-token scale is defined
    in that unit, not a WER fraction."""

    clause_text = f"{contrast.condition_arm}~{contrast.reference_arm} on {contrast.ledger} (entity-correct delta)"
    if not contrast.per_call:
        return ClauseResult(clause_text, "unresolved", "no paired calls survive the legitimate-empty exclusion")
    entity_delta = sum(row.entity_correct_delta for row in contrast.per_call)
    similar = abs(entity_delta) <= token_margin
    verdict: ClauseVerdict = "met" if similar else "not_met"
    detail = (
        f"PIN 5 token_margin={token_margin}: summed entity_correct_delta={entity_delta:+d} across "
        f"{len(contrast.per_call)} paired call(s) (F6: entity-correct delta, not entity_wer mean diff)"
    )
    return ClauseResult(clause_text, verdict, detail)


def _collapse_her_similarity(
    her_r1: HERResult, her_r0bias: HERResult, *, rate_tie_floor: float = COLLAPSE_MACRO_TIE_FLOOR
) -> ClauseResult:
    """"R1~R0-bias ... on HER" (Pin 5: "HER equivalence is raw-count-based
    and guard-aware per Pin 3"). F6: when EITHER side is guard-bound
    (denominator < 10, mirror 3.1), this conjunct falls back to comparing
    RAW harmful counts via :func:`compare_via_raw_counts` rather than
    auto-declaring "met" (the prior behavior). A degenerate raw comparison
    -- both sides tied, including the literal 0-vs-0 case, or a zero
    denominator -- resolves this conjunct as UNRESOLVED, never silently
    "met" (F6); per :func:`evaluate_branch_rules`, an unresolved conjunct
    means COLLAPSE cannot be declared."""

    clause_text = "HER[entity] r1verify~r0bias"
    if her_r1.rate.status == "resolved" and her_r0bias.rate.status == "resolved":
        assert her_r1.rate.rate is not None and her_r0bias.rate.rate is not None
        similar = abs(her_r1.rate.rate - her_r0bias.rate.rate) <= rate_tie_floor
        verdict: ClauseVerdict = "met" if similar else "not_met"
        detail = (
            f"HER[entity] rate-decided: r1verify={her_r1.rate.rate:.4f} vs r0bias="
            f"{her_r0bias.rate.rate:.4f}, tie_floor={rate_tie_floor:.4f}"
        )
        return ClauseResult(clause_text, verdict, detail)
    raw = compare_via_raw_counts(her_r1.rate, her_r0bias.rate, lower_is_better=True)
    if raw in ("unresolved", "tie"):
        return ClauseResult(
            clause_text, "unresolved",
            f"HER guard-bound (mirror 3.1) and raw harmful-splice counts degenerate ({raw}) -- F6: "
            f"UNRESOLVED rather than auto-met; r1verify {her_r1.harmful_splices}/"
            f"{her_r1.accepted_splices}, r0bias {her_r0bias.harmful_splices}/{her_r0bias.accepted_splices}",
        )
    detail = (
        f"HER guard-bound (mirror 3.1): raw harmful-splice counts r1verify="
        f"{her_r1.harmful_splices}/{her_r1.accepted_splices} vs r0bias={her_r0bias.harmful_splices}/"
        f"{her_r0bias.accepted_splices} ({raw}) -- NOT a tie, so not similar under the guard-aware "
        "raw-count comparison (F6)"
    )
    return ClauseResult(clause_text, "not_met", detail)


def evaluate_branch_rules(
    *,
    macro_r1_vs_r0bias: ContrastResult,
    entity_r1_vs_r0bias: ContrastResult,
    macro_r2_vs_r1: ContrastResult,
    entity_r2_vs_r1: ContrastResult,
    her_r1verify: HERResult,
    her_r0bias: HERResult,
    copy_r1wrong: CopyCountResult,
    copy_r0wrong: CopyCountResult,
    copy_r2draft: CopyCountResult,
    material_relative_drop: float = 0.50,
    c_bias_floor: int = 4,
    token_margin: int = MATCHED_GAIN_TOKEN_MARGIN,
    collapse_tie_floor: float = COLLAPSE_MACRO_TIE_FLOOR,
) -> BranchVerdict:
    """The mechanical evaluator: quotes the registered clauses verbatim
    next to each computed verdict, checks the VOIDING condition FIRST (it
    bars AFFIRM regardless of every WER-based clause), then AFFIRM, then
    COLLAPSE. Never silently resolves an UNRESOLVED clause either way."""

    voiding, weakening_note = _voiding_clause(copy_r1wrong, copy_r2draft)

    clause_a = _clause_a_r2_beats_r1(entity_r2_vs_r1, macro_r2_vs_r1)
    clause_b = _clause_b_r1_beats_r0bias(entity_r1_vs_r0bias, her_r1verify, her_r0bias, token_margin=token_margin)
    clause_c = _clause_c_wrongref_copy_rate(
        copy_r1wrong, copy_r0wrong, material_relative_drop=material_relative_drop, c_bias_floor=c_bias_floor
    )
    affirm_clauses = (clause_a, clause_b, clause_c)
    if voiding.verdict == "met":
        affirm = "not_met"
    elif any(c.verdict == "met" for c in affirm_clauses):
        affirm = "met"
    elif any(c.verdict == "unresolved" for c in affirm_clauses):
        affirm = "unresolved"
    else:
        affirm = "not_met"

    collapse_r1_macro = _collapse_clause_macro_similarity(macro_r1_vs_r0bias, tie_floor=collapse_tie_floor)
    collapse_r1_entity = _collapse_clause_entity_similarity(entity_r1_vs_r0bias, token_margin=token_margin)
    collapse_her = _collapse_her_similarity(her_r1verify, her_r0bias, rate_tie_floor=collapse_tie_floor)
    collapse_r2_macro = _collapse_clause_macro_similarity(macro_r2_vs_r1, tie_floor=collapse_tie_floor)
    collapse_r2_entity = _collapse_clause_entity_similarity(entity_r2_vs_r1, token_margin=token_margin)
    collapse_clauses = (
        collapse_r1_macro, collapse_r1_entity, collapse_her, collapse_r2_macro, collapse_r2_entity,
    )
    if any(c.verdict == "unresolved" for c in collapse_clauses):
        collapse: ClauseVerdict = "unresolved"
    elif all(c.verdict == "met" for c in collapse_clauses):
        collapse = "met"
    else:
        collapse = "not_met"

    if voiding.verdict == "met":
        overall = "VOIDED (audio-verification claim voided by wrong-reference copying; WER-based AFFIRM/COLLAPSE clauses are advisory only below)"
    elif affirm == "met":
        overall = "AFFIRMED"
    elif affirm == "unresolved":
        overall = "UNRESOLVED (at least one AFFIRM clause could not be resolved)"
    elif collapse == "met":
        overall = "COLLAPSE"
    elif collapse == "unresolved":
        overall = "UNRESOLVED (neither AFFIRM nor COLLAPSE could be fully resolved)"
    else:
        overall = "NEITHER AFFIRMED NOR COLLAPSED (no clause fired either way)"

    return BranchVerdict(
        voided=voiding.verdict == "met",
        voiding_clause=voiding,
        weakening_note=weakening_note,
        affirm=affirm,
        affirm_clauses=affirm_clauses,
        collapse=collapse,
        collapse_clauses=collapse_clauses,
        overall=overall,
    )


def render_branch_verdict(verdict: BranchVerdict) -> str:
    lines = ["Branch-rule evaluation (docs/arms/p2-rladder.arms, quoted verbatim):", "", BRANCH_RULES_TEXT, ""]
    lines.append(f"VOIDING (checked FIRST): {verdict.voiding_clause.verdict.upper()}")
    lines.append(f"  clause: {verdict.voiding_clause.clause_text}")
    lines.append(f"  detail: {verdict.voiding_clause.detail}")
    if verdict.weakening_note:
        lines.append(f"  WEAKENING NOTE: {verdict.weakening_note}")
    lines.append("")
    lines.append(f"AFFIRM: {verdict.affirm.upper()}")
    for clause in verdict.affirm_clauses:
        lines.append(f"  [{clause.verdict.upper():>10}] {clause.clause_text}")
        lines.append(f"             {clause.detail}")
    lines.append("")
    lines.append(f"COLLAPSE: {verdict.collapse.upper()}")
    for clause in verdict.collapse_clauses:
        lines.append(f"  [{clause.verdict.upper():>10}] {clause.clause_text}")
        lines.append(f"             {clause.detail}")
    lines.append("")
    lines.append(f"OVERALL: {verdict.overall}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Offline extraction layer: real arm run dirs -> the structured data the
# pure functions above consume. Reuses find_completed_attempt (context_dose)
# and the frozen scorers directly -- never a second, drifting
# implementation. Model-free, read-only; never mutates an attempt dir.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArmRead:
    arm: str
    run_dir: Path
    manifest_path: Path
    outputs_path: Path
    calls: tuple[PerCallMetrics, ...]
    macro_aggregate: Mapping[str, object]
    entity_aggregate: Mapping[str, object]
    her: dict[str, HERResult]
    rir: RIRResult
    copy_count: CopyCountResult
    legitimate_empty_sample_ids: tuple[str, ...]
    # F8 / Pin 1: which extraction path produced this read -- "completed-
    # attempt" (:func:`read_arm`, the COMPLETED-manifest run-dir path) or
    # "salvage-json" (:func:`read_arm_from_salvage`, F1's one-shot preserved
    # salvage-JSON path). Echoed into every cross-arm contrast this arm
    # participates in (Pin 1: "Any cross-arm contrast must state both
    # sources").
    source: str = "completed-attempt"


def _resolve_outputs_path(manifest: Mapping[str, object], manifest_path: Path) -> Path:
    outputs_meta = manifest.get("outputs")
    if not isinstance(outputs_meta, Mapping) or not outputs_meta.get("path"):
        raise P2ReadsError(f"manifest {manifest_path} carries no outputs artifact to score")
    outputs_path = Path(str(outputs_meta["path"]))
    if not outputs_path.is_file():
        raise P2ReadsError(f"outputs artifact recorded in {manifest_path} does not exist: {outputs_path}")
    return outputs_path


def _load_replay_windows(run_dir_of_attempt: Path, run_id: str) -> list[dict[str, object]]:
    """Loads every sample's replay windows from the attempt's own
    ``<run_id>.trace.jsonl`` REPLAY channel records -- the authoritative,
    already-durable source the salvage read used (``copycount_r0bias.py``'s
    own choice of ``wins_trace`` over the per-sample derivation files after
    an equality check). Missing trace file -> empty list (an arm with no
    replay windows at all, e.g. a bare-core baseline, is a legitimate
    shape, not an error)."""

    import json

    trace_path = run_dir_of_attempt / f"{run_id}.trace.jsonl"
    if not trace_path.is_file():
        return []
    windows: list[dict[str, object]] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("channel") == "REPLAY":
            windows.append(record["payload"])
    return windows


def _windows_by_sample(windows: Sequence[Mapping[str, object]]) -> dict[str, list[Mapping[str, object]]]:
    by_sample: dict[str, list[Mapping[str, object]]] = {}
    for window in windows:
        sample_id = str(window.get("replay_sample_id"))
        by_sample.setdefault(sample_id, []).append(window)
    return by_sample


def _score_span_errors(
    sample_id: str, carrier_lock_key: str, span_text: str, lock: Mapping[str, object], root: Path
) -> tuple[int, int]:
    """Module docstring note 1: ``(macro_error_count, entity_error_count)``
    for ``span_text`` scored as if it were the FULL hypothesis for
    ``sample_id``, via the SAME frozen ``core.scorers.score_asr_outputs`` /
    ``score_entity_wer_outputs`` this whole suite already reuses -- a real
    temp-file round trip through the actual registered scorers, never a
    parallel/reimplemented alignment call, and never a direct
    ``data.references`` import (the reference-import isolation contract:
    only ``core/scorers.py`` may do that)."""

    import json
    import tempfile

    row = {"sample_id": sample_id, "carrier_lock_key": carrier_lock_key, "text": span_text}
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".outputs.jsonl", delete=False, encoding="utf-8"
    )
    try:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.close()
        temp_path = Path(handle.name)
        try:
            asr = score_asr_outputs(temp_path, lock, root)
            entity = score_entity_wer_outputs(temp_path, lock, root)
        except ScoringPhaseError as error:
            raise P2ReadsError(f"span scoring failed for sample {sample_id!r}: {error}") from error
    finally:
        Path(handle.name).unlink(missing_ok=True)

    asr_entry = asr["per_sample"][0]
    entity_entry = entity["per_sample"][0]
    macro_errors = (
        int(asr_entry["substitutions"]) + int(asr_entry["deletions"]) + int(asr_entry["insertions"])
    )
    entity_errors = int(entity_entry["expected_total"]) - int(entity_entry["correct"])
    return macro_errors, entity_errors


def extract_her_splices(
    windows_by_sample: Mapping[str, Sequence[Mapping[str, object]]],
    carrier_lock_key_by_sample: Mapping[str, str],
    lock: Mapping[str, object],
    root: Path,
) -> list[SpliceScore]:
    """Builds one :class:`SpliceScore` per ACCEPTED replay splice (mirror
    section 3: "an accepted replay splice ... Rejected edits and untouched
    windows are not units")."""

    splices: list[SpliceScore] = []
    for sample_id, windows in windows_by_sample.items():
        carrier_lock_key = carrier_lock_key_by_sample.get(sample_id)
        if carrier_lock_key is None:
            continue
        for window in windows:
            if not window.get("replay_accepted"):
                continue
            pass1_text = str(window.get("replay_pass1_text") or "")
            localized_words = window.get("replay_localized_words") or []
            post_text = " ".join(str(w) for w in localized_words)
            macro_pass1, entity_pass1 = _score_span_errors(sample_id, carrier_lock_key, pass1_text, lock, root)
            macro_post, entity_post = _score_span_errors(sample_id, carrier_lock_key, post_text, lock, root)
            splices.append(
                SpliceScore(
                    sample_id=sample_id,
                    window_iteration=window.get("replay_window_iteration"),
                    span_index=window.get("replay_span_index"),
                    macro_pass1_errors=macro_pass1,
                    macro_post_errors=macro_post,
                    entity_pass1_errors=entity_pass1,
                    entity_post_errors=entity_post,
                )
            )
    return splices


def extract_rir_records(
    windows_by_sample: Mapping[str, Sequence[Mapping[str, object]]],
    final_hypothesis_by_sample: Mapping[str, str],
) -> list[RIRTokenRecord]:
    """Module docstring note 2: anchored on the DELIVERED units themselves
    (each ``replay_candidates[].text`` entry and each
    ``replay_exemplars_attached`` label) -- RIR's own denominator
    definition already names delivered content as "the correct form", so no
    independent reference-layer lookup is needed. One record per (sample,
    window, delivered unit); ``compute_rir`` counts records directly,
    matching the mirror's own "accepted splices" per-unit convention rather
    than a per-mention one."""

    from ..core.retrieval import normalize_term

    records: list[RIRTokenRecord] = []
    for sample_id, windows in windows_by_sample.items():
        final_tokens = normalize_term(final_hypothesis_by_sample.get(sample_id, "")).split()
        for window in windows:
            pass1_tokens = normalize_term(str(window.get("replay_pass1_text") or "")).split()
            units: list[str] = [str(c["text"]) for c in (window.get("replay_candidates") or [])]
            units.extend(
                label
                for label in (window.get("replay_exemplars_attached") or [])
                if isinstance(label, str) and label
            )
            for index, unit_text in enumerate(units):
                unit_tokens = normalize_term(unit_text).split()
                if not unit_tokens:
                    continue
                wrong_in_pass1 = not _contains_subsequence(pass1_tokens, unit_tokens)
                entity_id = (
                    f"{window.get('replay_window_iteration')}:{window.get('replay_span_index')}:"
                    f"{index}:{unit_text}"
                )
                records.append(
                    RIRTokenRecord(
                        sample_id=sample_id,
                        entity_id=entity_id,
                        wrong_in_pass1=wrong_in_pass1,
                        correct_form_delivered=True,
                        correct_in_final=_contains_subsequence(final_tokens, unit_tokens),
                    )
                )
    return records


# ---------------------------------------------------------------------------
# read_arm: real arm run dir -> ArmRead, wiring everything above together.
# ---------------------------------------------------------------------------


def _is_legitimate_empty(windows: Sequence[Mapping[str, object]]) -> bool:
    """A call is legitimate-empty (arms file: "fly as legitimate-empty
    (fix-3 exemption)") iff it has no replay windows at all, or every one
    of its windows delivered zero candidates -- a DATA fact read off the
    trace, never the four hardcoded sample IDs the pre-registration happens
    to name for THIS block (a different arm run could have a different set;
    this module never assumes which)."""

    if not windows:
        return True
    return all(not (window.get("replay_candidates") or []) for window in windows)


def read_arm(arm: str, run_dir: Path, lock: Mapping[str, object], root: Path) -> ArmRead:
    """Model-free, read-only: locates the arm's COMPLETED attempt
    (:func:`~speech_aware_evidence_acquisition.analysis.context_dose.find_completed_attempt`,
    reused unchanged -- carrier/metric-agnostic attempt selection, same
    precedent ``analysis.entity_wer_offline`` already follows), scores its
    outputs through the frozen ``asr-wer``/``entity-wer`` scorers, and
    extracts the HER/RIR/copy-count substrate from its trace. Never opens a
    model session; never mutates the attempt directory."""

    import json

    try:
        selection = find_completed_attempt(Path(run_dir))
    except ComparisonError as error:
        raise P2ReadsError(f"arm {arm!r}: {error}") from error
    manifest_path, manifest = selection.manifest_path, selection.manifest
    outputs_path = _resolve_outputs_path(manifest, manifest_path)

    try:
        asr_scores = score_asr_outputs(outputs_path, lock, root)
        entity_scores = score_entity_wer_outputs(outputs_path, lock, root)
    except ScoringPhaseError as error:
        raise P2ReadsError(f"arm {arm!r}: {error}") from error

    asr_by_sample = {str(entry["sample_id"]): entry for entry in asr_scores["per_sample"]}
    entity_by_sample = {str(entry["sample_id"]): entry for entry in entity_scores["per_sample"]}
    if set(asr_by_sample) != set(entity_by_sample):
        raise P2ReadsError(f"arm {arm!r}: asr-wer and entity-wer scored different sample sets")

    run_id = str(manifest.get("run_id") or "")
    windows = _load_replay_windows(manifest_path.parent, run_id)
    windows_by_sample = _windows_by_sample(windows)

    carrier_lock_key_by_sample: dict[str, str] = {}
    final_hypothesis_by_sample: dict[str, str] = {}
    for line in outputs_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        sample_id = str(row["sample_id"])
        carrier_lock_key_by_sample[sample_id] = str(row["carrier_lock_key"])
        final_hypothesis_by_sample[sample_id] = str(row["text"])

    calls: list[PerCallMetrics] = []
    legitimate_empty_ids: list[str] = []
    for sample_id in sorted(asr_by_sample):
        asr_entry = asr_by_sample[sample_id]
        entity_entry = entity_by_sample[sample_id]
        sample_windows = windows_by_sample.get(sample_id, ())
        empty = _is_legitimate_empty(sample_windows)
        if empty:
            legitimate_empty_ids.append(sample_id)
        calls.append(
            PerCallMetrics(
                sample_id=sample_id,
                macro_wer=float(asr_entry["wer"]),
                macro_ref_hit_mask=tuple(asr_entry["ref_hit_mask"]),
                entity_wer=float(entity_entry["entity_wer"]),
                entity_correct=int(entity_entry["correct"]),
                entity_expected_total=int(entity_entry["expected_total"]),
                legitimate_empty=empty,
            )
        )

    splices = extract_her_splices(windows_by_sample, carrier_lock_key_by_sample, lock, root)
    her = {ledger: compute_her(splices, ledger) for ledger in LEDGERS}

    rir_records = extract_rir_records(windows_by_sample, final_hypothesis_by_sample)
    rir = compute_rir(rir_records)

    copy_count = copy_count_for_arm(arm, windows)

    return ArmRead(
        arm=arm,
        run_dir=Path(run_dir),
        manifest_path=manifest_path,
        outputs_path=outputs_path,
        calls=tuple(calls),
        macro_aggregate=asr_scores["aggregate"],
        entity_aggregate=entity_scores["aggregate"],
        her=her,
        rir=rir,
        copy_count=copy_count,
        legitimate_empty_sample_ids=tuple(legitimate_empty_ids),
        source="completed-attempt",
    )


# ---------------------------------------------------------------------------
# F1: the salvage input path -- read_arm_from_salvage. Builds an ArmRead
# directly from a preserved one-shot salvage archive's three JSON outputs
# (docs/checks/speech-aware-evidence-acquisition/2026-08-16-p2-r0bias-
# salvage/ for r0bias) instead of a COMPLETED attempt run-dir. The sealed
# raw attempt trace is NEVER re-read here -- one-shot attempt semantics
# (Pin 1) are preserved by consuming only the already-spent read's
# preserved bytes.
# ---------------------------------------------------------------------------

# Provenance for this default: the P2 R-ladder frozen ten IS the
# r4-e21-sub10-sample split (configs/dataset/r4-e21-sub10.json,
# docs/receipts/probe-samples/r4-e21-sub10-sample.json) -- every one of the
# ten sample ids the salvage JSONs carry (4330115, 4365024, 4365948,
# 4366429, 4366522, 4384964, 4385072, 4387383, 4389907, 4397829) is listed
# there under carrier "earnings21-original". This module does not re-derive
# that fact from the sealed r0bias trace (never re-read); it is read off
# the already-committed split receipt instead.
SALVAGE_CARRIER_LOCK_KEY_DEFAULT = "earnings21-original"


def _load_salvage_json(path: Path) -> object:
    import json

    if not path.is_file():
        raise P2ReadsError(f"salvage input missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _copycount_rows_by_sample(
    rows: Sequence[Mapping[str, object]]
) -> dict[str, list[Mapping[str, object]]]:
    by_sample: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        by_sample.setdefault(str(row["sample"]), []).append(row)
    return by_sample


def copy_count_from_salvage_rows(arm: str, rows: Sequence[Mapping[str, object]]) -> CopyCountResult:
    """F1: builds a :class:`CopyCountResult` directly from the salvage
    ``{arm}.copycount.json`` flat-row shape (``copycount_r0bias.py``'s own
    output), reusing its ALREADY-COMPUTED ``copies_pre``/``novel_copy``/
    ``guard3_pre`` fields rather than re-deriving them from a trace this
    module never re-reads (one-shot semantics). Basis is ``copies_pre``
    (F2 Pin 4: raw ``total_copy_occurrences``), matching
    :func:`copy_count_for_arm`'s own ``total_copy_occurrences`` field
    exactly. A row's ``pre`` is ``None`` for the "no-candidates" skip path
    (mirrors ``replay_replay_text is None`` in the trace-based path)."""

    called = [row for row in rows if row.get("pre") is not None]
    total_occurrences = sum(int(row.get("copies_pre") or 0) for row in called)
    with_copy = [row for row in called if int(row.get("copies_pre") or 0) > 0]
    novel = sum(1 for row in called if row.get("novel_copy"))
    guard3 = sum(1 for row in called if row.get("guard3_pre") is True)
    accepted = sum(1 for row in rows if row.get("accepted"))
    return CopyCountResult(
        arm=arm,
        total_windows=len(rows),
        called_windows=len(called),
        accepted_splices=accepted,
        total_copy_occurrences=total_occurrences,
        windows_with_copy=len(with_copy),
        novel_copies=novel,
        guard3_unsupported=guard3,
        copy_window_sample_ids=tuple(str(row["sample"]) for row in with_copy),
    )


def extract_her_splices_from_salvage_rows(
    rows: Sequence[Mapping[str, object]],
    carrier_lock_key: str,
    lock: Mapping[str, object],
    root: Path,
) -> list[SpliceScore]:
    """F1: HER's ACCEPTED-splice substrate, built from the salvage
    copycount rows' own ``pass1``/``localized`` fields (each accepted row
    already carries the exact pass-1 span text and the exact post-splice
    localized-word text ``copycount_r0bias.py`` measured) through the SAME
    :func:`_score_span_errors` reuse every other HER extraction in this
    module uses -- no new alignment/scoring logic (module docstring
    note 1)."""

    splices: list[SpliceScore] = []
    for row in rows:
        if not row.get("accepted"):
            continue
        sample_id = str(row["sample"])
        pass1_text = str(row.get("pass1") or "")
        post_text = str(row.get("localized") or "")
        macro_pass1, entity_pass1 = _score_span_errors(sample_id, carrier_lock_key, pass1_text, lock, root)
        macro_post, entity_post = _score_span_errors(sample_id, carrier_lock_key, post_text, lock, root)
        splices.append(
            SpliceScore(
                sample_id=sample_id,
                window_iteration=row.get("win"),  # type: ignore[arg-type]
                span_index=row.get("span"),  # type: ignore[arg-type]
                macro_pass1_errors=macro_pass1,
                macro_post_errors=macro_post,
                entity_pass1_errors=entity_pass1,
                entity_post_errors=entity_post,
            )
        )
    return splices


def read_arm_from_salvage(
    arm: str,
    salvage_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    carrier_lock_key: str = SALVAGE_CARRIER_LOCK_KEY_DEFAULT,
) -> ArmRead:
    """F1: builds an :class:`ArmRead` directly from a preserved one-shot
    salvage archive's three JSON outputs, NEVER from a re-read of the
    sealed raw attempt trace (one-shot attempt semantics; Pin 1). Expects
    ``salvage_dir`` to carry exactly:

    - ``{arm}.asr-wer.json`` -- the EXACT, lossless return of
      ``core.scorers.score_asr_outputs``
      (``{"aggregate": {...}, "per_sample": [...]}}``);
    - ``{arm}.entity-wer.json`` -- the EXACT, lossless return of
      ``core.scorers.score_entity_wer_outputs``;
    - ``{arm}.copycount.json`` -- a flat list of per-window rows, the
      salvage's own ``copycount_r0bias.py`` output shape (keys: ``sample``,
      ``win``, ``span``, ``ref``, ``pre``, ``pass1``, ``localized``,
      ``accepted``, ``reason``, ``copies_pre``, ``copies_pass1``,
      ``novel_copy``, ``echo_pre``, ``echo_post``, ``guard3_pre``).

    Legitimate-empty: a sample_id is legitimate-empty iff it has ZERO rows
    in the copycount JSON -- literal, NOT "every row is a no-candidates
    skip" (a sample CAN carry a mix of skip rows and real windows, as
    SAEA-P2-r0bias's own sample 4387383 does; that sample is NOT
    legitimate-empty). This is the rule that reproduces the four registered
    zero-oracle-candidate ids exactly against the real archive.

    RIR is NOT derivable from the three preserved salvage JSONs (they never
    captured per-window delivered-candidate/final-hypothesis identity in a
    form this can read) and RIR feeds no branch-rule clause -- the returned
    :class:`RIRResult` carries ``available=False`` with an explanatory
    reason rather than a fabricated 0/0 read passed off as real."""

    asr_scores = _load_salvage_json(salvage_dir / f"{arm}.asr-wer.json")
    entity_scores = _load_salvage_json(salvage_dir / f"{arm}.entity-wer.json")
    copycount_rows = _load_salvage_json(salvage_dir / f"{arm}.copycount.json")
    if (
        not isinstance(asr_scores, Mapping)
        or not isinstance(entity_scores, Mapping)
        or not isinstance(copycount_rows, list)
    ):
        raise P2ReadsError(f"arm {arm!r}: malformed salvage JSON shape under {salvage_dir}")

    asr_by_sample = {str(entry["sample_id"]): entry for entry in asr_scores["per_sample"]}
    entity_by_sample = {str(entry["sample_id"]): entry for entry in entity_scores["per_sample"]}
    if set(asr_by_sample) != set(entity_by_sample):
        raise P2ReadsError(f"arm {arm!r}: asr-wer and entity-wer salvage JSONs scored different sample sets")

    rows_by_sample = _copycount_rows_by_sample(copycount_rows)

    calls: list[PerCallMetrics] = []
    legitimate_empty_ids: list[str] = []
    for sample_id in sorted(asr_by_sample):
        asr_entry = asr_by_sample[sample_id]
        entity_entry = entity_by_sample[sample_id]
        empty = sample_id not in rows_by_sample
        if empty:
            legitimate_empty_ids.append(sample_id)
        calls.append(
            PerCallMetrics(
                sample_id=sample_id,
                macro_wer=float(asr_entry["wer"]),
                macro_ref_hit_mask=tuple(asr_entry["ref_hit_mask"]),
                entity_wer=float(entity_entry["entity_wer"]),
                entity_correct=int(entity_entry["correct"]),
                entity_expected_total=int(entity_entry["expected_total"]),
                legitimate_empty=empty,
            )
        )

    splices = extract_her_splices_from_salvage_rows(copycount_rows, carrier_lock_key, lock, root)
    her = {ledger: compute_her(splices, ledger) for ledger in LEDGERS}

    rir = RIRResult(
        numerator=0,
        denominator=0,
        rate=guarded_rate(0, 0, label="RIR"),
        available=False,
        unavailable_reason=(
            "not derivable from preserved salvage outputs (the salvage JSONs carry no per-window "
            "delivered-candidate/final-hypothesis identity); RIR feeds no branch-rule clause (F1)."
        ),
    )

    copy_count = copy_count_from_salvage_rows(arm, copycount_rows)

    return ArmRead(
        arm=arm,
        run_dir=Path(salvage_dir),
        manifest_path=Path(salvage_dir) / "MANIFEST.sha256",
        outputs_path=Path(salvage_dir) / f"{arm}.asr-wer.json",
        calls=tuple(calls),
        macro_aggregate=asr_scores["aggregate"],
        entity_aggregate=entity_scores["aggregate"],
        her=her,
        rir=rir,
        copy_count=copy_count,
        legitimate_empty_sample_ids=tuple(legitimate_empty_ids),
        source="salvage-json",
    )


# F7: the two decisive co-primary contrasts evaluate_branch_rules actually
# consumes, and the exact registered zero-oracle-candidate exclusion set
# (arms file: "4365024/4365948/4366429/4384964", "paired Wilcoxon effective
# n=6").
DECISIVE_CONTRAST_NAMES: tuple[str, ...] = ("r1verify_vs_r0bias", "r2draft_vs_r1verify")
EXPECTED_LEGITIMATE_EMPTY_IDS: frozenset[str] = frozenset(
    {"4365024", "4365948", "4366429", "4384964"}
)


def _check_decisive_contrast_exclusions(
    contrasts: Mapping[str, Mapping[str, ContrastResult]]
) -> list[str]:
    """F7: loudly (never silently) verifies that the two decisive
    co-primary contrasts land at the pre-registered ``n_effective_paired
    == 6`` with EXACTLY the four registered zero-oracle-candidate ids
    excluded. Returns a (possibly empty) list of human-readable warning
    lines; NEVER raises -- a mismatch is reported prominently, not a
    hard-crash (F7)."""

    warnings: list[str] = []
    for name in DECISIVE_CONTRAST_NAMES:
        by_ledger = contrasts.get(name, {})
        for ledger, contrast in by_ledger.items():
            excluded = set(contrast.excluded_legitimate_empty)
            n_effective = len(contrast.included_sample_ids)
            if n_effective != 6 or excluded != EXPECTED_LEGITIMATE_EMPTY_IDS:
                warnings.append(
                    f"MISMATCH on decisive contrast {name!r} [{ledger}]: n_effective_paired="
                    f"{n_effective} (expected 6), excluded={sorted(excluded)} (expected "
                    f"{sorted(EXPECTED_LEGITIMATE_EMPTY_IDS)})"
                )
    return warnings


def build_p2_report(
    run_dirs: Mapping[str, Path],
    lock: Mapping[str, object],
    root: Path,
    *,
    r0bias_read: ArmRead | None = None,
) -> dict[str, object]:
    """Top-level orchestration: reads all five arms, builds the
    pre-registered paired contrasts, and runs the mechanical branch-rule
    evaluator. Raises :class:`P2ReadsError` (never returns a partial
    report) if any arm is unreadable or the arm set is incomplete.

    F1: pass ``r0bias_read`` (e.g. the output of :func:`read_arm_from_
    salvage`) to supply the r0bias arm directly instead of via
    ``run_dirs`` -- the two are mutually exclusive sources for that one
    arm, mirroring the CLI's ``--r0bias-run-dir`` / ``--r0bias-salvage-dir``
    split. ``run_dirs`` must then carry every OTHER arm name but must NOT
    carry ``"r0bias"``."""

    if r0bias_read is not None:
        expected = tuple(name for name in ARM_NAMES if name != "r0bias")
        missing = sorted(set(expected) - set(run_dirs))
        if missing:
            raise P2ReadsError(f"missing arm(s) {missing}; expected exactly {expected} plus r0bias_read")
        if "r0bias" in run_dirs:
            raise P2ReadsError(
                "both run_dirs['r0bias'] and r0bias_read were given; exactly one r0bias source is allowed"
            )
        reads = {arm: read_arm(arm, run_dirs[arm], lock, root) for arm in expected}
        reads["r0bias"] = r0bias_read
    else:
        missing = sorted(set(ARM_NAMES) - set(run_dirs))
        if missing:
            raise P2ReadsError(f"missing arm(s) {missing}; expected exactly {ARM_NAMES}")
        reads = {arm: read_arm(arm, run_dirs[arm], lock, root) for arm in ARM_NAMES}

    calls_by_arm = {arm: {c.sample_id: c for c in reads[arm].calls} for arm in ARM_NAMES}

    contrasts: dict[str, dict[str, ContrastResult]] = {}
    for name, condition_arm, reference_arm in CONTRASTS:
        contrasts[name] = {
            ledger: build_wilcoxon_contrast(
                name, condition_arm, reference_arm, ledger,
                calls_by_arm[condition_arm], calls_by_arm[reference_arm],
                condition_source=reads[condition_arm].source,
                reference_source=reads[reference_arm].source,
            )
            for ledger in LEDGERS
        }

    verdict = evaluate_branch_rules(
        macro_r1_vs_r0bias=contrasts["r1verify_vs_r0bias"]["macro"],
        entity_r1_vs_r0bias=contrasts["r1verify_vs_r0bias"]["entity"],
        macro_r2_vs_r1=contrasts["r2draft_vs_r1verify"]["macro"],
        entity_r2_vs_r1=contrasts["r2draft_vs_r1verify"]["entity"],
        her_r1verify=reads["r1verify"].her["entity"],
        her_r0bias=reads["r0bias"].her["entity"],
        copy_r1wrong=reads["r1wrong"].copy_count,
        copy_r0wrong=reads["r0wrong"].copy_count,
        copy_r2draft=reads["r2draft"].copy_count,
    )

    exclusion_warnings = _check_decisive_contrast_exclusions(contrasts)

    return {
        "schema": REPORT_SCHEMA,
        "reads": reads,
        "contrasts": contrasts,
        "branch_verdict": verdict,
        "exclusion_warnings": exclusion_warnings,
    }


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point
# (scripts/p2_reads.py is a thin wrapper, following scripts/compare_context_
# dose.py's / scripts/score_entity_wer.py's precedent).
# ---------------------------------------------------------------------------


def _guarded_rate_json(rate: GuardedRate) -> dict[str, object]:
    return {
        "label": rate.label, "numerator": rate.numerator, "denominator": rate.denominator,
        "rate": rate.rate, "status": rate.status, "note": rate.note,
    }


def _her_json(result: HERResult) -> dict[str, object]:
    return {
        "ledger": result.ledger, "harmful_splices": result.harmful_splices,
        "accepted_splices": result.accepted_splices, "rate": _guarded_rate_json(result.rate),
        "harmful_sample_ids": list(result.harmful_sample_ids),
    }


def _rir_json(result: RIRResult) -> dict[str, object]:
    return {
        "numerator": result.numerator, "denominator": result.denominator, "rate": _guarded_rate_json(result.rate),
        "available": result.available, "unavailable_reason": result.unavailable_reason,
    }


def _copy_count_json(result: CopyCountResult) -> dict[str, object]:
    return {
        "arm": result.arm, "total_windows": result.total_windows, "called_windows": result.called_windows,
        "accepted_splices": result.accepted_splices, "total_copy_occurrences": result.total_copy_occurrences,
        "windows_with_copy": result.windows_with_copy, "novel_copies": result.novel_copies,
        "guard3_unsupported": result.guard3_unsupported, "copy_rate": result.copy_rate,
        "copy_window_sample_ids": list(result.copy_window_sample_ids),
    }


def _transitions_json(transitions: TransitionCounts | None) -> dict[str, object] | None:
    if transitions is None:
        return None
    return {
        "correct_to_correct": transitions.correct_to_correct,
        "correct_to_wrong": transitions.correct_to_wrong,
        "wrong_to_correct": transitions.wrong_to_correct,
        "wrong_to_wrong": transitions.wrong_to_wrong,
    }


def _contrast_json(contrast: ContrastResult) -> dict[str, object]:
    return {
        "name": contrast.name, "condition_arm": contrast.condition_arm, "reference_arm": contrast.reference_arm,
        # F8 / Pin 1: "Any cross-arm contrast must state both sources."
        "condition_source": contrast.condition_source, "reference_source": contrast.reference_source,
        "ledger": contrast.ledger, "included_sample_ids": list(contrast.included_sample_ids),
        "excluded_legitimate_empty": list(contrast.excluded_legitimate_empty),
        "n_pairs_before_exclusion": len(contrast.included_sample_ids) + len(contrast.excluded_legitimate_empty),
        "n_effective_paired": len(contrast.included_sample_ids),
        "diffs": list(contrast.diffs),
        "wilcoxon": {
            "statistic_w_plus": contrast.wilcoxon.statistic, "n_pairs": contrast.wilcoxon.n_pairs,
            "n_effective_nonzero": contrast.wilcoxon.n_effective, "pvalue_two_sided_exact": contrast.wilcoxon.pvalue,
            "min_achievable_two_sided_p": contrast.wilcoxon.min_two_sided_p,
        },
        "per_call": [
            {
                "sample_id": row.sample_id, "condition_value": row.condition_value,
                "reference_value": row.reference_value, "diff": row.diff,
                "macro_transitions": _transitions_json(row.macro_transitions),
                "entity_correct_delta": row.entity_correct_delta,
            }
            for row in contrast.per_call
        ],
    }


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def _branch_verdict_json(verdict: BranchVerdict) -> dict[str, object]:
    return {
        "registered_text": verdict.registered_text,
        "voided": verdict.voided,
        "voiding_clause": _clause_json(verdict.voiding_clause),
        "weakening_note": verdict.weakening_note,
        "affirm": verdict.affirm,
        "affirm_clauses": [_clause_json(c) for c in verdict.affirm_clauses],
        "collapse": verdict.collapse,
        "collapse_clauses": [_clause_json(c) for c in verdict.collapse_clauses],
        "overall": verdict.overall,
    }


def _arm_read_json(read: ArmRead) -> dict[str, object]:
    return {
        "arm": read.arm,
        "source": read.source,  # F8: "completed-attempt" or "salvage-json"
        "run_dir": str(read.run_dir),
        "manifest_path": str(read.manifest_path),
        "outputs_path": str(read.outputs_path),
        "macro_aggregate": dict(read.macro_aggregate),
        "entity_aggregate": {k: v for k, v in read.entity_aggregate.items() if k != "by_entity_type"},
        "entity_by_type": read.entity_aggregate.get("by_entity_type", {}),
        "per_call": [
            {
                "sample_id": c.sample_id, "macro_wer": c.macro_wer, "entity_wer": c.entity_wer,
                "entity_correct": c.entity_correct, "entity_expected_total": c.entity_expected_total,
                "legitimate_empty": c.legitimate_empty,
            }
            for c in read.calls
        ],
        "legitimate_empty_sample_ids": list(read.legitimate_empty_sample_ids),
        "her": {ledger: _her_json(result) for ledger, result in read.her.items()},
        "rir": _rir_json(read.rir),
        "copy_count": _copy_count_json(read.copy_count),
    }


def report_to_json(report: Mapping[str, object]) -> dict[str, object]:
    """The full machine-readable JSON this suite's CLI writes. Per-term flip
    lists are NOT auto-populated here (see the note below) -- call
    :func:`per_term_flip_list` directly with sets of correct terms recovered
    another way if per-term detail is needed for a specific pair."""

    reads: Mapping[str, ArmRead] = report["reads"]  # type: ignore[assignment]
    contrasts: Mapping[str, Mapping[str, ContrastResult]] = report["contrasts"]  # type: ignore[assignment]
    verdict: BranchVerdict = report["branch_verdict"]  # type: ignore[assignment]
    exclusion_warnings: list[str] = list(report.get("exclusion_warnings") or [])  # type: ignore[arg-type]
    return {
        "schema": report["schema"],
        "arms": {arm: _arm_read_json(read) for arm, read in reads.items()},
        "contrasts": {
            name: {ledger: _contrast_json(contrast) for ledger, contrast in by_ledger.items()}
            for name, by_ledger in contrasts.items()
        },
        "branch_verdict": _branch_verdict_json(verdict),
        # F7: loud (never silent) exclusion-mismatch banner data -- empty
        # when the two decisive contrasts land exactly at the pre-
        # registered n_effective_paired==6 / four-id exclusion set.
        "exclusion_warnings": exclusion_warnings,
        "per_term_flip_lists": {
            "available": False,
            "note": (
                "per_term_flip_list(...) is provided as a reusable, independently-tested pure "
                "function (see tests/unit/test_p2_reads.py); it is not auto-populated in this "
                "report because per-sample predicted-entity-term IDENTITY is aggregated away by "
                "core.scorers.score_entity_wer_outputs's public return value, and re-deriving it "
                "here would require either violating the data.references import-isolation "
                "contract (tests/contract/test_reference_import_isolation.py) or extending "
                "core/scorers.py's public surface, both out of this task's scope. Call "
                "per_term_flip_list(...) directly with sets of correct terms recovered another way."
            ),
        },
        "format_normalized_secondary": {
            "available": False,
            "note": (
                "format_normalized_wer(reference_raw_tokens, hypothesis_text) is provided as a "
                "reusable, independently-tested function; no formula for this read exists "
                "anywhere in the repository (unlike HER/RIR, no definitions amendment covers it "
                "-- module docstring note 5), so this report does not silently invent an "
                "aggregate for it. Call format_normalized_wer(...) directly per sample/arm if "
                "this secondary read is wanted."
            ),
        },
    }


def render_report(report: Mapping[str, object]) -> str:
    reads: Mapping[str, ArmRead] = report["reads"]  # type: ignore[assignment]
    contrasts: Mapping[str, Mapping[str, ContrastResult]] = report["contrasts"]  # type: ignore[assignment]
    verdict: BranchVerdict = report["branch_verdict"]  # type: ignore[assignment]
    exclusion_warnings: list[str] = list(report.get("exclusion_warnings") or [])  # type: ignore[arg-type]

    lines = ["P2 R-ladder offline reads (docs/arms/p2-rladder.arms)", "=" * 60, ""]

    # F7: a LOUD banner, never a silent report, when the decisive
    # co-primary contrasts don't land at the pre-registered n_effective_
    # paired==6 / four-id exclusion set.
    if exclusion_warnings:
        lines.append("!" * 70)
        lines.append("PROMINENT WARNING (F7): decisive-contrast exclusion mismatch")
        for warning in exclusion_warnings:
            lines.append(f"  {warning}")
        lines.append("!" * 70)
        lines.append("")

    lines.append("Per-arm aggregates")
    lines.append(f"  {'arm':<10}{'macro_wer':>11}{'entity_wer':>12}{'ent_correct':>13}{'ent_expected':>13}")
    for arm in ARM_NAMES:
        read = reads[arm]
        macro_wer = read.macro_aggregate.get("mean_wer")
        entity_wer = read.entity_aggregate.get("entity_wer")
        correct = read.entity_aggregate.get("correct")
        expected = read.entity_aggregate.get("expected_total")
        lines.append(f"  {arm:<10}{macro_wer:>11.4f}{entity_wer:>12.4f}{correct:>13}{expected:>13}")
    lines.append("")

    lines.append("HER (mirror section 3) -- harmful/accepted, per ledger, per arm")
    for arm in ARM_NAMES:
        for ledger, result in reads[arm].her.items():
            lines.append(
                f"  {arm:<10}[{ledger:>6}] {result.harmful_splices}/{result.accepted_splices} "
                f"status={result.rate.status} rate={result.rate.rate}"
            )
    lines.append("")

    lines.append("RIR (mirror section 4) -- numerator/denominator, per arm")
    for arm in ARM_NAMES:
        rir = reads[arm].rir
        lines.append(f"  {arm:<10}{rir.numerator}/{rir.denominator} status={rir.rate.status} rate={rir.rate.rate}")
    lines.append("")

    lines.append("Wrong-reference copy count (PRE-LOCALIZE, D7E guard-2 aperture) -- per arm")
    for arm in ARM_NAMES:
        copy = reads[arm].copy_count
        lines.append(
            f"  {arm:<10}copies={copy.windows_with_copy}/{copy.called_windows} "
            f"(rate={copy.copy_rate:.4f}, novel={copy.novel_copies}, guard3={copy.guard3_unsupported})"
        )
    lines.append("")

    lines.append("Paired call-level contrasts (co-primary Wilcoxon, macro + entity)")
    for name, by_ledger in contrasts.items():
        for ledger, contrast in by_ledger.items():
            w = contrast.wilcoxon
            lines.append(
                f"  {name:<24}[{ledger:>6}] n_effective={w.n_effective} (of {w.n_pairs}, "
                f"{len(contrast.excluded_legitimate_empty)} legitimate-empty excluded) "
                f"p={w.pvalue:.4g} (floor {w.min_two_sided_p:.4g})"
            )
            for row in contrast.per_call:
                transitions = (
                    f" transitions={_transitions_json(row.macro_transitions)}"
                    if row.macro_transitions is not None
                    else ""
                )
                lines.append(
                    f"      {row.sample_id}: diff={row.diff:+.4f} "
                    f"entity_correct_delta={row.entity_correct_delta:+d}{transitions}"
                )
    lines.append("")

    lines.append(render_branch_verdict(verdict))
    return "\n".join(lines)


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="p2-reads",
        description=(
            "P2 R-ladder pinned offline read suite: macro/entity-WER, HER, RIR, wrong-reference "
            "copy count, paired Wilcoxon contrasts, and the mechanical branch-rule evaluator. "
            "Model-free, read-only; never opens a model session."
        ),
    )
    for arm in ARM_NAMES:
        if arm == "r0bias":
            # F1: r0bias's COMPLETED attempt was never re-flown after the
            # 2026-08-16 manifest-bind death (one-shot semantics) -- it has
            # exactly two mutually exclusive input paths: the ordinary
            # run-dir (if a COMPLETED attempt ever exists) or the preserved
            # one-shot salvage-JSON archive. Exactly one is required.
            r0bias_group = parser.add_mutually_exclusive_group(required=True)
            r0bias_group.add_argument(
                "--r0bias-run-dir", type=Path, default=None,
                help="stable run_dir for the r0bias arm (COMPLETED-attempt path; mutually "
                "exclusive with --r0bias-salvage-dir)",
            )
            r0bias_group.add_argument(
                "--r0bias-salvage-dir", type=Path, default=None,
                help="F1: preserved one-shot salvage archive directory for r0bias, carrying "
                "r0bias.asr-wer.json / r0bias.entity-wer.json / r0bias.copycount.json "
                "(mutually exclusive with --r0bias-run-dir)",
            )
            continue
        parser.add_argument(
            f"--{arm.replace('_', '-')}-run-dir", required=True, type=Path,
            help=f"stable run_dir for the {arm} arm (parent of attempt-*/ subdirectories)",
        )
    parser.add_argument("--output", required=True, type=Path, help="path to write the machine-readable JSON")
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="TEST-ONLY override of the study repo root used to resolve the umbrella lock",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import REPO_ROOT, write_json_artifact

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    lock = load_lock(umbrella_lock_path(repo_root))
    root = data_root()
    run_dirs = {arm: getattr(args, f"{arm}_run_dir") for arm in ARM_NAMES if arm != "r0bias"}

    r0bias_read = None
    if args.r0bias_salvage_dir is not None:
        try:
            r0bias_read = read_arm_from_salvage("r0bias", args.r0bias_salvage_dir, lock, root)
        except P2ReadsError as error:
            print(f"REFUSED: {error}", file=sys.stderr)
            return 1
    else:
        run_dirs["r0bias"] = args.r0bias_run_dir

    try:
        report = build_p2_report(run_dirs, lock, root, r0bias_read=r0bias_read)
    except P2ReadsError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    document = report_to_json(report)
    write_json_artifact(args.output, document)
    print(render_report(report))
    print(f"\nwrote machine-readable summary to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
