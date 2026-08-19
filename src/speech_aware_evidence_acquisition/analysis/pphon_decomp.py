"""P-PHON failure-class decomposition -- registered model-free re-read
(pinned, pre-registered) -- SAEA-CHECK-pphon-decomp.

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory. It is a NARROWER instrument layered ON TOP OF
five ALREADY-CONSUMED read suites (``analysis.pslu_read``,
``analysis.pslu_s2_read``, ``analysis.a2t_read``, ``analysis.a2t_s2b_read``,
``analysis.a2t_s2c_read``), re-reading their SAME archived ``outputs.jsonl``
files to answer the study's identity question this suite exists for
(``docs/readiness/2026-08-18-pphon-preregistration-REGISTERED.md``): does
speech knowledge participate in the supply loop, or is the audio only a
retrieval key -- by asking WHICH KIND of failure the supply arms convert.

Four pinned classes (prereg section 1, quoted verbatim), computed on
gold-vs-predicted VALUE strings, scoring-side only, per failed slot/argument
of the zero-supply baseline:

- **MISSING** -- no value emitted for the gold slot.
- **EQUIV-FORMAT** -- equal after the pinned normalization (casefold, strip
  punctuation/whitespace, digit<->word map, article strip).
- **NEAR-MISS** -- normalized Levenshtein <= 0.5 after normalization.
- **FAR-WRONG** -- everything else.

Scope (prereg section 2): **SLURP** (primary) -- the consumed A3 attempt
(``analysis.pslu_read``'s own attempt dir) is the primary supply arm;
**A1'r** (``analysis.pslu_s2_read``'s own attempt dir) is reported
concordant/discordant against A3, never a second independent verdict.
**A2T** (secondary, orthographic proxy only) -- B1/C1/C2 (the clean-form,
correct-tool-and-schema arms) as the "clean-form conversion set", descriptive
only (no verdict clauses).

REUSE, NOT RE-DERIVATION (mirrors ``analysis.a2t_loss_decomp``'s own
explicit discipline for the SAME reason -- this suite reuses its parents'
already-approved primitives, never a second, drifting implementation):

- ``analysis.pslu_read.build_pslu_report`` / ``analysis.pslu_s2_read.
  build_pslu_s2_report`` / ``analysis.a2t_read.build_a2t_report`` /
  ``analysis.a2t_s2b_read.build_a2t_s2b_report`` / ``analysis.a2t_s2c_read.
  build_a2t_s2c_report`` -- called here UNCHANGED as this module's own
  harness-defect/integrity GATE (every check those five suites already
  perform fires before this module's own per-slot/per-argument walk ever
  runs) AND as a second, independently-scored source of each arm's own
  TP/em-flip numbers (module docstring "three-way reconciliation" below).
- ``analysis.pslu_read.load_attempt_rows``/``load_gold_by_sample_id`` and
  ``analysis.pslu_s2_read.load_attempt_rows`` -- the SAME row/gold loaders
  those suites' own row walks use, called a second time here for the raw
  ``response_text`` this module's own per-slot classification needs (the
  parent reports only expose per-arm AGGREGATES, never per-slot detail).
- ``analysis.a2t_read.load_attempt_rows`` / ``analysis.a2t_s2_read.
  load_attempt_rows``/``load_arm_plan`` -- ditto, for A0/B1/C1/C2's own raw
  ``response`` text.
- ``reproduction.slurp_scoring.parse_slu_response`` / ``SlotEntity`` /
  ``_lowest_distance`` / ``_word_distance`` -- the per-slot gold/predicted
  VALUE-ALIGNMENT primitive ``analysis.pslu_read.
  count_induced_substitutions`` already reuses this exact way (private
  cross-module reuse, precedented in this repository:
  ``rails.consumption.classify_outcome`` imports ``analysis.p2_reads.
  _count_subsequence`` the same way) -- reused VERBATIM here, inverted to a
  per-GOLD-SLOT view (note 2 below).
- ``reproduction.toolcall_scoring.ToolCall``/``parse_tool_calls_text``/
  ``score_item``/``_canonical_value`` -- the SAME bare-key argument
  alignment ``analysis.a2t_s2_read.count_induced_substitutions`` already
  establishes for A2T (note 5 below), reused verbatim.
- ``data.audio2tool.load_expected_calls`` -- the A2T gold source, reused
  directly (never re-derived).

ENGINEERING-INTERPRETATION NOTES (flagged here, not buried -- each is a
documented, reviewable choice, not a silent guess):

1. **"Conversion" is defined at the SLOT level (SLURP) / ARGUMENT level
   (A2T): "gold slot failed in A0 AND correct under the supply arm".**
   Reconciling this total naively against the supply arm's raw
   ``slot_f1_exact_tp_sum`` would be WRONG whenever the supply arm also
   REGRESSES an already-correct A0 slot (rare, but not structurally
   impossible). The correct identity, derived once and used throughout:
   ``conversions - regressions == entity_tp_gain`` where
   ``entity_tp_gain = ArmX_tp_sum - A0_tp_sum`` is EXACTLY the same
   quantity ``analysis.pslu_read.evaluate_branch_rules``'s own COPY-TRAP
   clause already publishes under that name (verified against the real,
   already-consumed ``2026-08-18-pslu-read/verdict.json``: A0 tp_sum=4.0,
   A3 tp_sum=48.0, and that archive's own copy-trap detail text literally
   reads "A3: induced=3, entity_tp_gain=+44.00" = 48-4). This module
   computes ``regressions`` itself (a scalar, class-independent: a gold
   slot exact-matched by A0 but NOT by the supply arm) via the SAME
   per-slot exact-match walk (:func:`_exact_match_indices`) run twice (once
   against A0's predicted entities, once against the supply arm's), so the
   identity above is EXACT, not approximate, and is asserted as a
   fail-closed reconciliation gate (:func:`reconcile`) three ways: this
   module's own computation, a PARENT recomputation (a fresh call into
   ``build_pslu_report``/``build_pslu_s2_report``), and the ALREADY-
   CONSUMED, MANIFEST-verified archived ``verdict.json``.
2. **Two DIFFERENT distance-based primitives serve two DIFFERENT roles, and
   only one is reused.** :func:`_align_failed_slots` reuses
   ``reproduction.slurp_scoring._lowest_distance``/``_word_distance``
   VERBATIM -- the exact greedy same-type nearest-word-distance algorithm
   ``analysis.pslu_read.count_induced_substitutions`` already reuses for
   its own per-predicted-entity gold alignment (module docstring item 2),
   just inverted here to answer "what value (if any) did A0 actually emit
   for THIS gold slot" rather than "what gold entity does THIS predicted
   entity align to". The four-class CLASSIFIER's own "normalized
   Levenshtein <= 0.5" metric (prereg section 1) is a SEPARATE, freshly
   written stdlib-only implementation (:func:`normalized_levenshtein`) --
   deliberately NOT a reuse of ``reproduction.slurp_scoring._char_distance``
   (a same-shaped [0,1] edit-distance ratio, but scoped to the OFFICIAL
   SLURP char-distance metric on RAW, non-pinned-normalized filler text, a
   different purpose and out of this module's own reuse list). This module
   ships its own pinned normalization (:func:`normalize_value`,
   :data:`DIGIT_WORD_MAP`) and its own pinned distance metric, exactly as
   the mission brief's own item 1 asks it to.
3. :func:`_exact_match_indices` replicates ``reproduction.slurp_scoring.
   _exact_counts``'s own greedy list-membership removal algorithm EXACTLY
   (same predicted-order walk, same first-structural-equal-item removal),
   additionally tracking WHICH original gold index each match consumed
   (``_exact_counts`` itself only returns an aggregate TP count). By
   construction, ``len(matched) == _exact_counts(gold, predicted)[0]``
   always -- this identity is what makes note 1's reconciliation exact
   rather than approximate. Predicted entities never claimed by any exact
   match are the ONLY pool :func:`_align_failed_slots` draws from for a
   failed slot's classification value -- an entity already spoken for by a
   DIFFERENT gold slot's exact match is never reused to explain a failed
   slot's near-miss value.
4. **A1'r concordance reuses the SAME A0 baseline classification** computed
   once from the live ``analysis.pslu_read`` attempt's own A0 rows (both
   attempts share the identical frozen ``pslu-sample-devel-n60.json``
   sample set and gold) -- never a second, independently-classified
   baseline. A1'r's own conversion pass (:func:`build_slurp_conversion`)
   is layered on top of that ONE shared baseline, exactly the way A3's own
   pass is, so the two verdicts are genuinely comparable
   (:func:`evaluate_concordance`).
5. **A2T's per-argument classification is bare-key, string-valued gold
   arguments only.** Mirrors ``analysis.a2t_s2_read.
   count_induced_substitutions``'s own "aligned by argument KEY only, not
   also scoped by tool name" convention (that module's own note 7) -- every
   headroom sample carries A0's own CORRECT tool selection by construction
   (the headroom set's own defining criterion), so key-only alignment
   within one sample's own single gold call is unambiguous. A gold argument
   value that is not itself a Python ``str`` (int/float/bool/mapping/list)
   has no orthographic-proxy meaning under this suite's pinned normalization
   (digit<->word/article-strip are string-token operations) and is excluded
   from the per-class table entirely -- mirrors ``analysis.pslu_read.
   _roster_values_for_packet``'s own "VALUE half only" exclusion precedent.
6. **The A2T EM-flip reconciliation (B1=8/C1=10/C2=9, prereg-external
   mission instruction) is a SEPARATE, ITEM-level gate from the
   ARGUMENT-level descriptive class table.** ``reproduction.toolcall_scoring
   .score_item`` is reused verbatim (the SAME comparator
   ``analysis.a2t_s2_read.score_row`` calls internally) to recompute, per
   headroom row, whether A0 was NOT exact-match and the supply arm IS --
   summed to an EM-flip count reconciled three ways (computed / parent-
   recomputed via a fresh ``build_a2t_s2b_report``/``build_a2t_s2c_report``
   call / archived) PLUS the literal exact-count gate at the real n=120
   scale (:data:`EXACT_EM_CONVERSION_GATES`, mirrors ``analysis.
   a2t_loss_decomp.EXACT_LOSS_COUNT_GATES``'s own "applies only at real
   scale" pattern -- verified against the real, already-consumed
   ``2026-08-18-a2t-s2b-read``/``2026-08-18-a2t-s2c-read`` archives: B1's
   own ``per_arm.B1.overall.em_flip_count`` is 8 at ``n_samples=120``, C1's
   is 10, C2's is 9). The ARGUMENT-level class table itself carries no
   separate reconciliation requirement (prereg: "descriptive").
7. **``analysis.pslu_read``/``analysis.pslu_s2_read`` report harness defects
   and recheck mismatches as SOFT clauses (their own VOID branch), never a
   hard raise** -- unlike ``analysis.a2t_read``/``analysis.a2t_s2_read``'s
   own fail-closed-raise convention (that family's own note 1 explicitly
   contrasts itself with "``analysis.pslu_read``'s own soft VOID-clause
   convention"). This module promotes ``harness_defect_reasons``/
   ``recheck_mismatches`` non-empty on EITHER pslu attempt to a hard
   :class:`PphonDecompError` refusal here (never silently tolerated) --
   deliberately narrower than that parent's own full VOID bucket, which
   also folds in the silence-swap-persistence clause (a qualitative claim
   about MODEL BEHAVIOR content this module's own per-slot walk does not
   depend on at all, so it is not promoted to a refusal).
8. **MANIFEST coverage is scoped to the five READ archives this module
   reads NUMBERS from** (``2026-08-18-pslu-read``, ``2026-08-18-pslu-s2-
   read``, ``2026-08-18-pa2t-a0-read`` [``headroom.json`` cross-check
   only], ``2026-08-18-a2t-s2b-read``, ``2026-08-18-a2t-s2c-read``) --
   never a second, redundant re-verification of the underlying FLIGHT
   archives, whose own ``flight-receipt.json``/``split_identity_hash``
   integrity is already fully re-validated by the five reused parent
   ``build_*_report`` gates themselves (step 1 of
   :func:`build_pphon_decomp_report`).
9. **Verdicts may co-fire; the evaluator never forces mutual exclusion.**
   SPEECH-SNAP-PRESENT and FORMAT-DOMINANT (prereg section 3) are two
   INDEPENDENT booleans; :func:`evaluate_pphon_verdict` computes both and
   sets ``boundary_co_fire`` when both are true simultaneously (the
   prereg's own arithmetic note: only reachable when conversions split
   >=85% exactly between the two classes) -- reported, never collapsed to
   one winner.

DEVELOPED AND TESTED EXCLUSIVELY AGAINST HAND-AUTHORED SYNTHETIC FIXTURES
(``tests/unit/test_pphon_decomp.py``). This module is NEVER run against the
real, already-consumed attempt directories by the task that wrote it -- that
is a separately gated, one-shot execution mission
(``docs/readiness/2026-08-18-pphon-preregistration-REGISTERED.md`` section 4:
"suite built and coordinator-reviewed BEFORE execution").
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Literal, Mapping, Sequence

from ..reproduction.slurp_scoring import SlotEntity, _lowest_distance, _word_distance, parse_slu_response
from ..reproduction.toolcall_scoring import ToolCall, _canonical_value, parse_tool_calls_text, score_item
from ..rails.probes.a2t_s2b_flight import B1_ARM
from ..rails.probes.a2t_s2c_flight import C1_ARM, C2_ARM
from ..rails.probes.pslu_flight import PSLU_PHASE1_ARM, load_pslu_sample_manifest
from ..rails.probes.pslu_s2_flight import A1R_ARM
from .a2t_read import A2tReadError, build_a2t_report
from .a2t_read import load_attempt_rows as load_a2t_a0_rows
from .a2t_s2_read import A2tS2ReadError, ArmPlan, load_arm_plan
from .a2t_s2_read import load_attempt_rows as load_a2t_s2_rows
from .a2t_s2b_read import A2tS2bReadError, _default_stage2_arm_plan_path, build_a2t_s2b_report
from .a2t_s2c_read import A2tS2cReadError, build_a2t_s2c_report
from .pslu_read import ClauseResult, PsluReadError, build_pslu_report, load_gold_by_sample_id
from .pslu_read import load_attempt_rows as load_pslu_rows
from .pslu_s2_read import PsluS2ReadError, build_pslu_s2_report
from .pslu_s2_read import load_attempt_rows as load_pslu_s2_rows

REPORT_SCHEMA = "saea-pphon-decomp-read-v1"
DEFAULT_SPLIT_ROLE = "discovery"

CHECK_DIR = "speech-aware-evidence-acquisition"
PSLU_READ_ARCHIVE_DIRNAME = "2026-08-18-pslu-read"
PSLU_S2_READ_ARCHIVE_DIRNAME = "2026-08-18-pslu-s2-read"
A2T_A0_READ_ARCHIVE_DIRNAME = "2026-08-18-pa2t-a0-read"
A2T_S2B_READ_ARCHIVE_DIRNAME = "2026-08-18-a2t-s2b-read"
A2T_S2C_READ_ARCHIVE_DIRNAME = "2026-08-18-a2t-s2c-read"

A3_ARM = "A3"

SLURP_CARRIER = "slurp"
A2T_CARRIER = "a2t"


class PphonDecompError(RuntimeError):
    """A harness defect the reused consumed-suite gates refuse on, a
    MANIFEST.sha256 integrity failure, or a reconciliation disagreement --
    never raised for an ordinary, structurally clean read."""


# ---------------------------------------------------------------------------
# Pinned normalization (prereg section 1) + a fresh, stdlib-only normalized
# Levenshtein (module docstring note 2).
# ---------------------------------------------------------------------------

#: The digit<->word map (mission brief: "ship the digit<->word map as a
#: frozen constant"). Digit tokens map to their spelled-out word form; word
#: tokens already equal to a value here are left untouched -- one direction
#: is sufficient for "10" and "ten" to both normalize to "ten".
DIGIT_WORD_MAP: Mapping[str, str] = MappingProxyType(
    {
        "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
        "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
        "10": "ten", "11": "eleven", "12": "twelve", "13": "thirteen",
        "14": "fourteen", "15": "fifteen", "16": "sixteen", "17": "seventeen",
        "18": "eighteen", "19": "nineteen", "20": "twenty", "30": "thirty",
        "40": "forty", "50": "fifty", "60": "sixty", "70": "seventy",
        "80": "eighty", "90": "ninety", "100": "hundred",
    }
)

_ARTICLES: frozenset[str] = frozenset({"a", "an", "the"})
_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_value(text: str) -> str:
    """Pinned normalization (prereg section 1, quoted verbatim): casefold,
    strip punctuation/whitespace, digit<->word map, article strip -- applied
    in that registered order, token-level (whitespace-split after
    punctuation is replaced with a space, so "well-known" normalizes to two
    tokens rather than a spuriously joined one). Returns a single
    space-joined string (possibly empty)."""

    folded = text.casefold()
    despunctuated = _PUNCTUATION_RE.sub(" ", folded)
    tokens = [tok for tok in _WHITESPACE_RE.split(despunctuated.strip()) if tok]
    tokens = [DIGIT_WORD_MAP.get(tok, tok) for tok in tokens]
    tokens = [tok for tok in tokens if tok not in _ARTICLES]
    return " ".join(tokens)


def _levenshtein_distance(a: str, b: str) -> int:
    """Classic O(len(a)*len(b)) dynamic-programming edit distance -- stdlib
    only (module docstring note 2: a fresh implementation, deliberately not
    a reuse of ``reproduction.slurp_scoring._levenshtein``, which exists for
    a differently-scoped metric)."""

    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i] + [0] * len(b)
        for j, char_b in enumerate(b, start=1):
            cost = 0 if char_a == char_b else 1
            current_row[j] = min(
                previous_row[j] + 1,  # deletion
                current_row[j - 1] + 1,  # insertion
                previous_row[j - 1] + cost,  # substitution
            )
        previous_row = current_row
    return previous_row[-1]


def normalized_levenshtein(a: str, b: str) -> float:
    """Edit distance normalized to [0, 1] by the longer string's length --
    0.0 when both strings are empty."""

    if not a and not b:
        return 0.0
    return _levenshtein_distance(a, b) / max(len(a), len(b))


# ---------------------------------------------------------------------------
# The four-class classifier (prereg section 1).
# ---------------------------------------------------------------------------

MISSING = "MISSING"
EQUIV_FORMAT = "EQUIV-FORMAT"
NEAR_MISS = "NEAR-MISS"
FAR_WRONG = "FAR-WRONG"
FAILURE_CLASSES: tuple[str, ...] = (MISSING, EQUIV_FORMAT, NEAR_MISS, FAR_WRONG)
FailureClass = Literal["MISSING", "EQUIV-FORMAT", "NEAR-MISS", "FAR-WRONG"]

NEAR_MISS_MAX_DISTANCE = 0.5  # prereg section 1: normalized Levenshtein <= 0.5


def classify_failure(gold_value: str, predicted_value: str | None) -> FailureClass:
    """The four pinned classes (prereg section 1), computed on the GOLD
    value string vs whatever value (if any) was actually emitted for that
    gold slot. Precondition (enforced by every caller in this module, never
    by this function itself): only called for a slot/argument already
    determined to have FAILED under the baseline arm -- ``predicted_value``
    is ``None`` exactly when no value was emitted at all (MISSING), never an
    empty string (a genuinely-emitted-but-blank value, which classifies
    through the normal normalize/Levenshtein path instead)."""

    if predicted_value is None:
        return MISSING
    normalized_gold = normalize_value(gold_value)
    normalized_predicted = normalize_value(predicted_value)
    if normalized_gold == normalized_predicted:
        return EQUIV_FORMAT
    if normalized_levenshtein(normalized_gold, normalized_predicted) <= NEAR_MISS_MAX_DISTANCE:
        return NEAR_MISS
    return FAR_WRONG


# ---------------------------------------------------------------------------
# Per-class / per-arm tables + CR(c).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClassCounts:
    baseline_failures: int
    converted: int

    @property
    def conversion_rate(self) -> float:
        return (self.converted / self.baseline_failures) if self.baseline_failures else 0.0


@dataclass(frozen=True)
class ArmClassTable:
    carrier: str
    arm: str
    classes: Mapping[FailureClass, ClassCounts]
    total_baseline_failures: int
    total_converted: int

    @property
    def conversion_rate_overall(self) -> float:
        return (self.total_converted / self.total_baseline_failures) if self.total_baseline_failures else 0.0


def build_class_table(carrier: str, arm: str, outcomes: Iterable[tuple[FailureClass, bool]]) -> ArmClassTable:
    counts: dict[str, list[int]] = {klass: [0, 0] for klass in FAILURE_CLASSES}
    for klass, converted in outcomes:
        counts[klass][0] += 1
        if converted:
            counts[klass][1] += 1
    classes = {klass: ClassCounts(baseline_failures=b, converted=c) for klass, (b, c) in counts.items()}
    return ArmClassTable(
        carrier=carrier,
        arm=arm,
        classes=classes,
        total_baseline_failures=sum(b for b, _c in counts.values()),
        total_converted=sum(c for _b, c in counts.values()),
    )


# ---------------------------------------------------------------------------
# Verdict evaluator (prereg section 3).
# ---------------------------------------------------------------------------

SPEECH_SNAP_NEAR_MISS_SHARE_MIN = 0.25
SPEECH_SNAP_CR_MARGIN_MIN = 0.15
FORMAT_DOMINANT_EQUIV_SHARE_MIN = 0.60

SPEECH_SNAP_PRESENT = "SPEECH-SNAP-PRESENT"
FORMAT_DOMINANT = "FORMAT-DOMINANT"
MIXED = "MIXED"


@dataclass(frozen=True)
class PphonVerdict:
    carrier: str
    arm: str
    total_converted: int
    near_miss_share: float
    equiv_format_share: float
    cr_near_miss: float
    cr_far_wrong: float
    near_miss_share_clause: ClauseResult
    near_miss_margin_clause: ClauseResult
    speech_snap_present: bool
    format_dominant_clause: ClauseResult
    format_dominant: bool
    boundary_co_fire: bool
    overall: str


def evaluate_pphon_verdict(
    table: ArmClassTable,
    *,
    near_miss_share_min: float = SPEECH_SNAP_NEAR_MISS_SHARE_MIN,
    cr_margin_min: float = SPEECH_SNAP_CR_MARGIN_MIN,
    format_dominant_share_min: float = FORMAT_DOMINANT_EQUIV_SHARE_MIN,
) -> PphonVerdict:
    """Prereg section 3, quoted verbatim in each clause's own detail text
    (overrides exist ONLY for this module's own test suite -- never used by
    :func:`build_pphon_decomp_report`). Module docstring note 9: the two
    branches are independent booleans, never forced mutually exclusive."""

    total = table.total_converted
    near_miss = table.classes[NEAR_MISS]
    equiv_format = table.classes[EQUIV_FORMAT]
    far_wrong = table.classes[FAR_WRONG]

    near_miss_share = (near_miss.converted / total) if total else 0.0
    equiv_format_share = (equiv_format.converted / total) if total else 0.0
    cr_near_miss = near_miss.conversion_rate
    cr_far_wrong = far_wrong.conversion_rate

    near_miss_share_clause = ClauseResult(
        f"NEAR-MISS conversions >= {near_miss_share_min:.0%} of all conversions",
        "met" if total and near_miss_share >= near_miss_share_min else "not_met",
        f"near_miss_share={near_miss_share:.4f} ({near_miss.converted}/{total}), floor={near_miss_share_min:.2f}",
    )
    near_miss_margin_clause = ClauseResult(
        f"CR(NEAR-MISS) >= CR(FAR-WRONG) + {cr_margin_min:.2f}",
        "met" if cr_near_miss >= cr_far_wrong + cr_margin_min else "not_met",
        f"CR(NEAR-MISS)={cr_near_miss:.4f}, CR(FAR-WRONG)={cr_far_wrong:.4f}, "
        f"margin={cr_near_miss - cr_far_wrong:+.4f}, floor={cr_margin_min:.2f}",
    )
    speech_snap_present = (
        total > 0 and near_miss_share_clause.verdict == "met" and near_miss_margin_clause.verdict == "met"
    )

    format_dominant_clause = ClauseResult(
        f"EQUIV-FORMAT conversions >= {format_dominant_share_min:.0%} of all conversions",
        "met" if total and equiv_format_share >= format_dominant_share_min else "not_met",
        f"equiv_format_share={equiv_format_share:.4f} ({equiv_format.converted}/{total}), "
        f"floor={format_dominant_share_min:.2f}",
    )
    format_dominant = total > 0 and format_dominant_clause.verdict == "met"

    boundary_co_fire = speech_snap_present and format_dominant
    if boundary_co_fire:
        overall = f"{SPEECH_SNAP_PRESENT} + {FORMAT_DOMINANT} (boundary co-fire)"
    elif speech_snap_present:
        overall = SPEECH_SNAP_PRESENT
    elif format_dominant:
        overall = FORMAT_DOMINANT
    else:
        overall = MIXED

    return PphonVerdict(
        carrier=table.carrier,
        arm=table.arm,
        total_converted=total,
        near_miss_share=near_miss_share,
        equiv_format_share=equiv_format_share,
        cr_near_miss=cr_near_miss,
        cr_far_wrong=cr_far_wrong,
        near_miss_share_clause=near_miss_share_clause,
        near_miss_margin_clause=near_miss_margin_clause,
        speech_snap_present=speech_snap_present,
        format_dominant_clause=format_dominant_clause,
        format_dominant=format_dominant,
        boundary_co_fire=boundary_co_fire,
        overall=overall,
    )


@dataclass(frozen=True)
class ConcordanceResult:
    concordant: bool
    detail: str


def evaluate_concordance(primary: PphonVerdict, secondary: PphonVerdict) -> ConcordanceResult:
    """A1'r concordance (prereg section 2: "A1'r must be reported as
    concordant/discordant") against the SLURP-A3 primary verdict --
    concordant iff BOTH independent booleans agree; never a string
    comparison of the composed ``overall`` label (a boundary co-fire on one
    side and a clean single verdict on the other is correctly read as
    discordant on whichever boolean actually differs)."""

    concordant = (
        primary.speech_snap_present == secondary.speech_snap_present
        and primary.format_dominant == secondary.format_dominant
    )
    detail = (
        f"A3 (primary): overall={primary.overall!r}, speech_snap_present={primary.speech_snap_present}, "
        f"format_dominant={primary.format_dominant}; A1'r (secondary): overall={secondary.overall!r}, "
        f"speech_snap_present={secondary.speech_snap_present}, format_dominant={secondary.format_dominant}"
    )
    return ConcordanceResult(concordant=concordant, detail=detail)


# ---------------------------------------------------------------------------
# SLURP per-slot walk (notes 2-4).
# ---------------------------------------------------------------------------


def _exact_match_indices(
    gold: Sequence[SlotEntity], predicted: Sequence[SlotEntity]
) -> tuple[frozenset[int], tuple[SlotEntity, ...]]:
    """Note 3: replicates ``reproduction.slurp_scoring._exact_counts``'s own
    greedy list-membership removal EXACTLY, additionally tracking WHICH
    original gold index each match consumed, and returning the predicted
    entities never claimed by any exact match."""

    remaining = list(enumerate(gold))
    matched: set[int] = set()
    leftover: list[SlotEntity] = []
    for entity in predicted:
        for pos, (gold_index, gold_entity) in enumerate(remaining):
            if gold_entity == entity:
                matched.add(gold_index)
                del remaining[pos]
                break
        else:
            leftover.append(entity)
    return frozenset(matched), tuple(leftover)


def _align_failed_slots(
    failed_gold_indices: Sequence[int],
    gold: Sequence[SlotEntity],
    leftover_predicted: Sequence[SlotEntity],
) -> dict[int, SlotEntity | None]:
    """Note 2: the per-slot value-alignment primitive reused VERBATIM from
    ``reproduction.slurp_scoring`` (``_lowest_distance``/``_word_distance``),
    inverted to a per-GOLD-SLOT view. ``None`` for a gold index with no
    same-type leftover candidate at all -- MISSING (prereg section 1)."""

    remaining_indices = list(failed_gold_indices)
    remaining_types = [gold[i].type for i in remaining_indices]
    remaining_fillers = [gold[i].filler for i in remaining_indices]
    aligned: dict[int, SlotEntity | None] = {i: None for i in failed_gold_indices}
    for entity in leftover_predicted:
        if entity.type not in remaining_types:
            continue
        pos, _distance = _lowest_distance(entity, remaining_types, remaining_fillers, _word_distance)
        gold_index = remaining_indices[pos]
        aligned[gold_index] = entity
        del remaining_indices[pos]
        del remaining_types[pos]
        del remaining_fillers[pos]
    return aligned


@dataclass(frozen=True)
class SlurpBaselineSlot:
    sample_id: str
    gold_index: int
    entity_type: str
    gold_filler: str
    aligned_a0_filler: str | None
    failure_class: FailureClass


@dataclass(frozen=True)
class SlurpBaseline:
    n_gold_entities_total: int
    total_failures: int
    failed_slots: tuple[SlurpBaselineSlot, ...]
    matched_a0_by_sample: Mapping[str, frozenset[int]]
    gold_entities_by_sample: Mapping[str, tuple[SlotEntity, ...]]


def build_slurp_baseline(
    sample_ids: Sequence[str],
    gold_by_id: Mapping[str, object],
    a0_response_by_id: Mapping[str, str],
) -> SlurpBaseline:
    """Per gold slot of the zero-supply (A0) baseline: classify every FAILED
    slot into one of the four pinned classes (module docstring notes 2-3)."""

    failed_slots: list[SlurpBaselineSlot] = []
    matched_by_sample: dict[str, frozenset[int]] = {}
    gold_by_sample: dict[str, tuple[SlotEntity, ...]] = {}
    n_gold_total = 0

    for sample_id in sample_ids:
        gold_entities = tuple(gold_by_id[sample_id].entities)
        gold_by_sample[sample_id] = gold_entities
        n_gold_total += len(gold_entities)

        _scenario, _action, predicted, _parsed = parse_slu_response(a0_response_by_id[sample_id])
        matched, leftover = _exact_match_indices(gold_entities, tuple(predicted))
        matched_by_sample[sample_id] = matched

        failed_indices = [i for i in range(len(gold_entities)) if i not in matched]
        aligned = _align_failed_slots(failed_indices, gold_entities, leftover)
        for i in failed_indices:
            gold_entity = gold_entities[i]
            aligned_entity = aligned[i]
            aligned_filler = aligned_entity.filler if aligned_entity is not None else None
            klass = classify_failure(gold_entity.filler, aligned_filler)
            failed_slots.append(
                SlurpBaselineSlot(
                    sample_id=sample_id,
                    gold_index=i,
                    entity_type=gold_entity.type,
                    gold_filler=gold_entity.filler,
                    aligned_a0_filler=aligned_filler,
                    failure_class=klass,
                )
            )

    return SlurpBaseline(
        n_gold_entities_total=n_gold_total,
        total_failures=len(failed_slots),
        failed_slots=tuple(failed_slots),
        matched_a0_by_sample=matched_by_sample,
        gold_entities_by_sample=gold_by_sample,
    )


@dataclass(frozen=True)
class SlurpConversionResult:
    arm: str
    table: ArmClassTable
    regressions: int


def build_slurp_conversion(
    arm: str, baseline: SlurpBaseline, arm_response_by_id: Mapping[str, str]
) -> SlurpConversionResult:
    """Note 1: for every FAILED baseline slot, is it exact-matched under
    ``arm``'s own predicted entities (bare conversion, class-scoped)? Also
    computes ``regressions`` -- gold slots A0 exact-matched that ``arm``
    does NOT -- the scalar note 1's reconciliation identity needs."""

    matched_arm_by_sample: dict[str, frozenset[int]] = {}
    regressions = 0
    for sample_id, gold_entities in baseline.gold_entities_by_sample.items():
        _scenario, _action, predicted, _parsed = parse_slu_response(arm_response_by_id[sample_id])
        matched_arm, _leftover = _exact_match_indices(gold_entities, tuple(predicted))
        matched_arm_by_sample[sample_id] = matched_arm
        regressions += len(baseline.matched_a0_by_sample[sample_id] - matched_arm)

    outcomes = [
        (slot.failure_class, slot.gold_index in matched_arm_by_sample[slot.sample_id])
        for slot in baseline.failed_slots
    ]
    table = build_class_table(SLURP_CARRIER, arm, outcomes)
    return SlurpConversionResult(arm=arm, table=table, regressions=regressions)


# ---------------------------------------------------------------------------
# A2T per-argument walk (bare-key; note 5).
# ---------------------------------------------------------------------------


def _predicted_value_for_key(calls: Sequence[ToolCall], key: str) -> object | None:
    """Bare-key lookup (note 5): the first predicted value under ``key``
    across every call this row's own response carries, or ``None`` when no
    predicted call supplies that key at all."""

    for call in calls:
        if key in call.arguments:
            return call.arguments[key]
    return None


@dataclass(frozen=True)
class A2tBaselineArgument:
    sample_id: str
    call_index: int
    key: str
    gold_value: str
    aligned_a0_value: str | None
    failure_class: FailureClass


@dataclass(frozen=True)
class A2tBaseline:
    total_failures: int
    failed_arguments: tuple[A2tBaselineArgument, ...]


def build_a2t_baseline(
    sample_ids: Sequence[str],
    gold_calls_by_id: Mapping[str, Sequence[ToolCall]],
    a0_predicted_by_id: Mapping[str, Sequence[ToolCall]],
) -> A2tBaseline:
    """Per gold (call, key) argument of the zero-supply (A0) baseline,
    STRING-valued gold arguments only (note 5): classify every FAILED
    argument into one of the four pinned classes."""

    failed: list[A2tBaselineArgument] = []
    for sample_id in sample_ids:
        gold_calls = gold_calls_by_id[sample_id]
        a0_calls = a0_predicted_by_id[sample_id]
        for call_index, call in enumerate(gold_calls):
            for key, gold_value in call.arguments.items():
                if not isinstance(gold_value, str):
                    continue  # note 5: orthographic classes apply to strings only
                predicted_value = _predicted_value_for_key(a0_calls, key)
                if predicted_value is not None and _canonical_value(predicted_value) == _canonical_value(gold_value):
                    continue  # already correct under A0 -- not a baseline failure
                predicted_str = (
                    predicted_value
                    if isinstance(predicted_value, str)
                    else (None if predicted_value is None else str(predicted_value))
                )
                klass = classify_failure(gold_value, predicted_str)
                failed.append(
                    A2tBaselineArgument(
                        sample_id=sample_id,
                        call_index=call_index,
                        key=key,
                        gold_value=gold_value,
                        aligned_a0_value=predicted_str,
                        failure_class=klass,
                    )
                )
    return A2tBaseline(total_failures=len(failed), failed_arguments=tuple(failed))


def build_a2t_conversion(
    arm: str, baseline: A2tBaseline, arm_predicted_by_id: Mapping[str, Sequence[ToolCall]]
) -> ArmClassTable:
    """For every FAILED baseline argument, does ``arm``'s own predicted call
    supply a canonically-equal value under the SAME key (note 5, bare-key)?"""

    outcomes: list[tuple[FailureClass, bool]] = []
    for arg in baseline.failed_arguments:
        arm_calls = arm_predicted_by_id[arg.sample_id]
        predicted_value = _predicted_value_for_key(arm_calls, arg.key)
        converted = predicted_value is not None and _canonical_value(predicted_value) == _canonical_value(
            arg.gold_value
        )
        outcomes.append((arg.failure_class, converted))
    return build_class_table(A2T_CARRIER, arm, outcomes)


def compute_em_flips(
    sample_ids: Sequence[str],
    expected_by_id: Mapping[str, Sequence[ToolCall]],
    a0_predicted_by_id: Mapping[str, Sequence[ToolCall]],
    arm_predicted_by_id: Mapping[str, Sequence[ToolCall]],
) -> int:
    """Note 6: item-level EM-flip count (A0 not exact-match, arm IS),
    recomputed via ``reproduction.toolcall_scoring.score_item`` reused
    verbatim -- the SAME comparator ``analysis.a2t_s2_read.score_row``
    itself calls internally."""

    count = 0
    for sample_id in sample_ids:
        gold = expected_by_id[sample_id]
        if score_item(gold, a0_predicted_by_id[sample_id]).exact_match == 1.0:
            continue
        if score_item(gold, arm_predicted_by_id[sample_id]).exact_match == 1.0:
            count += 1
    return count


EXACT_EM_CONVERSION_GATES: Mapping[str, tuple[int, int]] = {
    B1_ARM: (8, 120),
    C1_ARM: (10, 120),
    C2_ARM: (9, 120),
}


# ---------------------------------------------------------------------------
# MANIFEST.sha256 verification (module docstring note 8): a general,
# fail-closed primitive, mirroring analysis.a2t_loss_decomp's own structure.
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_manifest_sha256(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, rel = line.partition(" ")
        rel = rel.lstrip("*").strip()
        if rel.startswith("./"):
            rel = rel[2:]
        if not rel:
            raise PphonDecompError(f"{path}: malformed MANIFEST.sha256 line: {line!r}")
        entries[rel] = digest.lower()
    if not entries:
        raise PphonDecompError(f"{path}: MANIFEST.sha256 carries zero entries")
    return entries


def verify_archive_manifest(
    archive_dir: Path, *, cross_check: Mapping[str, Path] = {}
) -> tuple[str, ...]:
    """Fail-closed integrity gate: every file the archive's own
    ``MANIFEST.sha256`` lists must exist under ``archive_dir`` and
    hash-match. Any relname named in ``cross_check`` must ALSO hash-match
    the archive's own pinned digest -- tamper/drift evidence between
    archival time and read time. Returns the sorted tuple of relnames the
    archive's own manifest lists."""

    archive_dir = Path(archive_dir)
    manifest_path = archive_dir / "MANIFEST.sha256"
    if not manifest_path.is_file():
        raise PphonDecompError(f"{manifest_path}: missing -- refusing to trust this archive")
    pinned = _parse_manifest_sha256(manifest_path)

    problems: list[str] = []
    for rel, digest in sorted(pinned.items()):
        file_path = archive_dir / rel
        if not file_path.is_file():
            problems.append(f"{file_path}: listed in {manifest_path} but missing")
            continue
        actual = _sha256_file(file_path)
        if actual != digest:
            problems.append(f"{file_path}: sha256 mismatch (manifest={digest}, actual={actual})")

    for rel, live_path in sorted(cross_check.items()):
        if rel not in pinned:
            problems.append(f"{manifest_path}: cross-check target {rel!r} is not listed")
            continue
        live_path = Path(live_path)
        if not live_path.is_file():
            problems.append(f"{live_path}: cross-check target missing")
            continue
        actual = _sha256_file(live_path)
        if actual != pinned[rel]:
            problems.append(
                f"{live_path}: sha256 does not match the archived, MANIFEST-pinned "
                f"{archive_dir / rel} (manifest={pinned[rel]}, actual={actual})"
            )

    if problems:
        raise PphonDecompError(
            f"MANIFEST.sha256 integrity failure(s) under {archive_dir}:\n  " + "\n  ".join(problems)
        )
    return tuple(sorted(pinned))


# ---------------------------------------------------------------------------
# Reconciliation (note 1, note 6).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReconciliationRow:
    label: str
    computed: float
    parent_recomputed: float
    archived: float
    matched: bool
    detail: str


def _numbers_match(a: float, b: float, *, tol: float = 1e-6) -> bool:
    return abs(a - b) < tol


def reconcile(
    label: str,
    computed: float,
    parent_recomputed: float,
    archived: float,
    *,
    exact_gate: tuple[float, int] | None = None,
    n_samples: int | None = None,
) -> ReconciliationRow:
    """Three-way reconciliation (``analysis.a2t_loss_decomp`` precedent):
    this module's own walk (``computed``) must agree with an INDEPENDENT
    recomputation via a parent suite's own reused primitives
    (``parent_recomputed``) and with the already-consumed, MANIFEST-
    verified, git-committed archive (``archived``). ``exact_gate`` (a
    literal ``(value, real_n_samples)`` pair, mirrors ``analysis.
    a2t_loss_decomp.EXACT_LOSS_COUNT_GATES``) applies an ADDITIONAL literal
    requirement only when ``n_samples`` genuinely equals the real flight's
    own size; otherwise reported as not applicable rather than spuriously
    enforced against a smaller synthetic fixture."""

    matched = _numbers_match(computed, parent_recomputed) and _numbers_match(computed, archived)
    detail = f"computed={computed:g}, parent_recomputed={parent_recomputed:g}, archived={archived:g}"
    if exact_gate is not None:
        gate_value, gate_n = exact_gate
        if n_samples == gate_n:
            matched = matched and _numbers_match(computed, gate_value)
            detail += f", exact_gate={gate_value:g}/{gate_n} (applies, n_samples matches)"
        else:
            detail += f", exact_gate={gate_value:g}/{gate_n} (not applicable at n_samples={n_samples})"
    return ReconciliationRow(
        label=label,
        computed=computed,
        parent_recomputed=parent_recomputed,
        archived=archived,
        matched=matched,
        detail=detail,
    )


def _load_json(path: Path) -> Mapping[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _archived_pslu_tp_sum(archive_dir: Path, arm: str) -> float:
    document = _load_json(Path(archive_dir) / "verdict.json")
    try:
        return float(document["aggregates"][arm]["slot_f1_exact"]["tp_sum"])
    except (KeyError, TypeError) as error:
        raise PphonDecompError(
            f"{archive_dir}/verdict.json: no aggregates[{arm!r}].slot_f1_exact.tp_sum"
        ) from error


def _archived_a2t_overall(archive_dir: Path, arm: str) -> Mapping[str, object]:
    document = _load_json(Path(archive_dir) / "verdict.json")
    try:
        return document["per_arm"][arm]["overall"]
    except (KeyError, TypeError) as error:
        raise PphonDecompError(f"{archive_dir}/verdict.json: no per_arm[{arm!r}].overall") from error


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SlurpSection:
    n_gold_entities_total: int
    baseline_total_failures: int
    a3: ArmClassTable
    a3_regressions: int
    a3_verdict: PphonVerdict
    a1r: ArmClassTable
    a1r_regressions: int
    a1r_verdict: PphonVerdict
    concordance: ConcordanceResult
    reconciliation: tuple[ReconciliationRow, ...]


@dataclass(frozen=True)
class A2tSection:
    baseline_total_failures: int
    tables: Mapping[str, ArmClassTable]
    em_flip_reconciliation: Mapping[str, ReconciliationRow]


@dataclass(frozen=True)
class PphonDecompReport:
    pslu_attempt_dir: Path
    pslu_s2_attempt_dir: Path
    a2t_attempt_dir: Path
    a2t_s2b_attempt_dir: Path
    a2t_s2c_attempt_dir: Path
    arm_plan_path: Path
    slurp: SlurpSection
    a2t: A2tSection
    manifest_verified: Mapping[str, tuple[str, ...]]


def _default_archive_dir(repo_root: Path, dirname: str) -> Path:
    return Path(repo_root) / "docs" / "checks" / CHECK_DIR / dirname


def _pslu_response_by_arm(rows: Sequence[object], arm: str) -> dict[str, str]:
    return {row.sample_id: row.response_text for row in rows if row.arm == arm and not row.silence_swapped}


def _a2t_response_by_id(rows: Sequence[object]) -> dict[str, str]:
    return {row.sample_id: row.response_text for row in rows}


def _a2t_s2_response_by_arm(rows: Sequence[object], arm: str) -> dict[str, str]:
    return {row.sample_id: row.response for row in rows if row.arm == arm}


def _parsed_calls_by_id(response_by_id: Mapping[str, str]) -> dict[str, tuple[ToolCall, ...]]:
    result: dict[str, tuple[ToolCall, ...]] = {}
    for sample_id, response_text in response_by_id.items():
        predicted, _parsed = parse_tool_calls_text(response_text)
        result[sample_id] = tuple(predicted)
    return result


def build_pphon_decomp_report(
    pslu_attempt_dir: Path,
    pslu_s2_attempt_dir: Path,
    a2t_attempt_dir: Path,
    a2t_s2b_attempt_dir: Path,
    a2t_s2c_attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path,
    pslu_sample_manifest_path: Path,
    pslu_roster_table_path: Path,
    pslu_filler_lexicon_path: Path,
    a2t_headroom_path: Path,
    a2t_arm_plan_path: Path | None = None,
    split_role: str = DEFAULT_SPLIT_ROLE,
    pslu_read_archive_dir: Path | None = None,
    pslu_s2_read_archive_dir: Path | None = None,
    a2t_a0_read_archive_dir: Path | None = None,
    a2t_s2b_read_archive_dir: Path | None = None,
    a2t_s2c_read_archive_dir: Path | None = None,
) -> PphonDecompReport:
    repo_root = Path(repo_root)
    pslu_attempt_dir = Path(pslu_attempt_dir)
    pslu_s2_attempt_dir = Path(pslu_s2_attempt_dir)
    a2t_attempt_dir = Path(a2t_attempt_dir)
    a2t_s2b_attempt_dir = Path(a2t_s2b_attempt_dir)
    a2t_s2c_attempt_dir = Path(a2t_s2c_attempt_dir)

    pslu_read_archive_dir = pslu_read_archive_dir or _default_archive_dir(repo_root, PSLU_READ_ARCHIVE_DIRNAME)
    pslu_s2_read_archive_dir = pslu_s2_read_archive_dir or _default_archive_dir(
        repo_root, PSLU_S2_READ_ARCHIVE_DIRNAME
    )
    a2t_a0_read_archive_dir = a2t_a0_read_archive_dir or _default_archive_dir(
        repo_root, A2T_A0_READ_ARCHIVE_DIRNAME
    )
    a2t_s2b_read_archive_dir = a2t_s2b_read_archive_dir or _default_archive_dir(
        repo_root, A2T_S2B_READ_ARCHIVE_DIRNAME
    )
    a2t_s2c_read_archive_dir = a2t_s2c_read_archive_dir or _default_archive_dir(
        repo_root, A2T_S2C_READ_ARCHIVE_DIRNAME
    )
    resolved_arm_plan_path = (
        Path(a2t_arm_plan_path) if a2t_arm_plan_path else _default_stage2_arm_plan_path(repo_root)
    )

    # 1. The reused consumed-suite gates (module docstring): every check
    #    those five suites already perform, unchanged.
    pslu_report = build_pslu_report(
        pslu_attempt_dir,
        lock,
        root,
        sample_manifest_path=pslu_sample_manifest_path,
        roster_table_path=pslu_roster_table_path,
    )
    if pslu_report.harness_defect_reasons or pslu_report.recheck_mismatches:
        raise PphonDecompError(
            "pslu attempt failed this module's own integrity gate (note 7: harness defects "
            f"or recheck mismatches promoted to a refusal): {list(pslu_report.harness_defect_reasons)!r}, "
            f"{len(pslu_report.recheck_mismatches)} recheck mismatch(es)"
        )

    pslu_s2_report = build_pslu_s2_report(
        pslu_s2_attempt_dir,
        lock,
        root,
        sample_manifest_path=pslu_sample_manifest_path,
        roster_table_path=pslu_roster_table_path,
        filler_lexicon_path=pslu_filler_lexicon_path,
    )
    if pslu_s2_report.harness_defect_reasons or pslu_s2_report.recheck_mismatches:
        raise PphonDecompError(
            "pslu-s2 attempt failed this module's own integrity gate (note 7): "
            f"{list(pslu_s2_report.harness_defect_reasons)!r}, "
            f"{len(pslu_s2_report.recheck_mismatches)} recheck mismatch(es)"
        )

    build_a2t_report(a2t_attempt_dir, lock, root, repo_root=repo_root, split_role=split_role)
    s2b_report = build_a2t_s2b_report(
        a2t_s2b_attempt_dir,
        lock,
        root,
        repo_root=repo_root,
        headroom_path=a2t_headroom_path,
        stage2_arm_plan_path=resolved_arm_plan_path,
        split_role=split_role,
    )
    s2c_report = build_a2t_s2c_report(
        a2t_s2c_attempt_dir,
        lock,
        root,
        repo_root=repo_root,
        headroom_path=a2t_headroom_path,
        stage2_arm_plan_path=resolved_arm_plan_path,
        split_role=split_role,
    )

    # 2. MANIFEST verification of every input archive this module reads
    #    NUMBERS from (module docstring note 8) -- BEFORE trusting their
    #    bytes.
    manifest_verified = {
        "pslu-read": verify_archive_manifest(pslu_read_archive_dir),
        "pslu-s2-read": verify_archive_manifest(pslu_s2_read_archive_dir),
        "a2t-a0-read": verify_archive_manifest(
            a2t_a0_read_archive_dir, cross_check={"headroom.json": a2t_headroom_path}
        ),
        "a2t-s2b-read": verify_archive_manifest(a2t_s2b_read_archive_dir),
        "a2t-s2c-read": verify_archive_manifest(a2t_s2c_read_archive_dir),
    }

    # 3. SLURP: reload raw rows for the per-slot walk (already structurally
    #    validated by step 1).
    pslu_manifest = load_pslu_sample_manifest(pslu_sample_manifest_path)
    gold_by_id = load_gold_by_sample_id(lock, root, pslu_manifest.sample_ids)  # RUNTIME_PROHIBITED, reused

    pslu_rows = load_pslu_rows(pslu_attempt_dir)
    a0_response_by_id = _pslu_response_by_arm(pslu_rows, PSLU_PHASE1_ARM)
    a3_response_by_id = _pslu_response_by_arm(pslu_rows, A3_ARM)
    pslu_s2_rows = load_pslu_s2_rows(pslu_s2_attempt_dir)
    a1r_response_by_id = _pslu_response_by_arm(pslu_s2_rows, A1R_ARM)

    for label, response_by_id in (("A0", a0_response_by_id), (A3_ARM, a3_response_by_id), (A1R_ARM, a1r_response_by_id)):
        missing = [sid for sid in pslu_manifest.sample_ids if sid not in response_by_id]
        if missing:
            raise PphonDecompError(f"arm {label}: no row for {len(missing)} sample(s), e.g. {missing[:5]!r}")

    baseline = build_slurp_baseline(pslu_manifest.sample_ids, gold_by_id, a0_response_by_id)
    a3_result = build_slurp_conversion(A3_ARM, baseline, a3_response_by_id)
    a1r_result = build_slurp_conversion(A1R_ARM, baseline, a1r_response_by_id)

    parent_a0_tp = pslu_report.aggregates[PSLU_PHASE1_ARM].slot_f1_exact_tp_sum
    parent_a3_tp = pslu_report.aggregates[A3_ARM].slot_f1_exact_tp_sum
    parent_a1r_tp = pslu_s2_report.aggregates[A1R_ARM].slot_f1_exact_tp_sum
    archived_a0_tp = _archived_pslu_tp_sum(pslu_read_archive_dir, PSLU_PHASE1_ARM)
    archived_a3_tp = _archived_pslu_tp_sum(pslu_read_archive_dir, A3_ARM)
    archived_a1r_tp = _archived_pslu_tp_sum(pslu_s2_read_archive_dir, A1R_ARM)

    slurp_reconciliation = (
        reconcile(
            "slurp-baseline-failures",
            baseline.total_failures,
            baseline.n_gold_entities_total - parent_a0_tp,
            baseline.n_gold_entities_total - archived_a0_tp,
        ),
        reconcile(
            "slurp-A3-conversions-net-of-regressions",
            a3_result.table.total_converted - a3_result.regressions,
            parent_a3_tp - parent_a0_tp,
            archived_a3_tp - archived_a0_tp,
        ),
        reconcile(
            "slurp-A1r-conversions-net-of-regressions",
            a1r_result.table.total_converted - a1r_result.regressions,
            parent_a1r_tp - parent_a0_tp,
            archived_a1r_tp - archived_a0_tp,
        ),
    )
    mismatches = [row for row in slurp_reconciliation if not row.matched]
    if mismatches:
        raise PphonDecompError(
            "SLURP reconciliation failure(s) -- refusing to publish a verdict:\n  "
            + "\n  ".join(f"{row.label}: {row.detail}" for row in mismatches)
        )

    a3_verdict = evaluate_pphon_verdict(a3_result.table)
    a1r_verdict = evaluate_pphon_verdict(a1r_result.table)
    concordance = evaluate_concordance(a3_verdict, a1r_verdict)

    slurp_section = SlurpSection(
        n_gold_entities_total=baseline.n_gold_entities_total,
        baseline_total_failures=baseline.total_failures,
        a3=a3_result.table,
        a3_regressions=a3_result.regressions,
        a3_verdict=a3_verdict,
        a1r=a1r_result.table,
        a1r_regressions=a1r_result.regressions,
        a1r_verdict=a1r_verdict,
        concordance=concordance,
        reconciliation=slurp_reconciliation,
    )

    # 4. A2T: reload raw rows for the per-argument walk.
    arm_plan: ArmPlan = load_arm_plan(resolved_arm_plan_path)
    from ..data.audio2tool import load_expected_calls

    expected_by_id = load_expected_calls(lock, root, repo_root=repo_root)

    a2t_rows, _malformed_a0 = load_a2t_a0_rows(a2t_attempt_dir)
    a0_a2t_response_by_id = _a2t_response_by_id(a2t_rows)
    s2b_rows, _malformed_s2b = load_a2t_s2_rows(a2t_s2b_attempt_dir)
    b1_response_by_id = _a2t_s2_response_by_arm(s2b_rows, B1_ARM)
    s2c_rows, _malformed_s2c = load_a2t_s2_rows(a2t_s2c_attempt_dir)
    c1_response_by_id = _a2t_s2_response_by_arm(s2c_rows, C1_ARM)
    c2_response_by_id = _a2t_s2_response_by_arm(s2c_rows, C2_ARM)

    headroom_ids = arm_plan.headroom_ids
    per_arm_rows = {"A0": a0_a2t_response_by_id, B1_ARM: b1_response_by_id, C1_ARM: c1_response_by_id, C2_ARM: c2_response_by_id}
    for label, response_by_id in per_arm_rows.items():
        missing = [sid for sid in headroom_ids if sid not in response_by_id]
        if missing:
            raise PphonDecompError(f"A2T arm {label}: no row for {len(missing)} headroom sample(s), e.g. {missing[:5]!r}")

    a0_calls_by_id = _parsed_calls_by_id(a0_a2t_response_by_id)
    b1_calls_by_id = _parsed_calls_by_id(b1_response_by_id)
    c1_calls_by_id = _parsed_calls_by_id(c1_response_by_id)
    c2_calls_by_id = _parsed_calls_by_id(c2_response_by_id)

    gold_calls_by_id = {sid: expected_by_id[sid] for sid in headroom_ids}
    a2t_baseline = build_a2t_baseline(headroom_ids, gold_calls_by_id, a0_calls_by_id)
    b1_table = build_a2t_conversion(B1_ARM, a2t_baseline, b1_calls_by_id)
    c1_table = build_a2t_conversion(C1_ARM, a2t_baseline, c1_calls_by_id)
    c2_table = build_a2t_conversion(C2_ARM, a2t_baseline, c2_calls_by_id)

    em_flip_reconciliation: dict[str, ReconciliationRow] = {}
    for arm, arm_calls_by_id, s2_report, archive_dir in (
        (B1_ARM, b1_calls_by_id, s2b_report, a2t_s2b_read_archive_dir),
        (C1_ARM, c1_calls_by_id, s2c_report, a2t_s2c_read_archive_dir),
        (C2_ARM, c2_calls_by_id, s2c_report, a2t_s2c_read_archive_dir),
    ):
        computed = compute_em_flips(headroom_ids, gold_calls_by_id, a0_calls_by_id, arm_calls_by_id)
        parent_overall = s2_report.per_arm[arm].overall
        archived_overall = _archived_a2t_overall(archive_dir, arm)
        row = reconcile(
            f"a2t-{arm}-em-flips",
            computed,
            parent_overall.em_flip_count,
            int(archived_overall["em_flip_count"]),
            exact_gate=EXACT_EM_CONVERSION_GATES.get(arm),
            n_samples=parent_overall.n_samples,
        )
        em_flip_reconciliation[arm] = row

    mismatches = [row for row in em_flip_reconciliation.values() if not row.matched]
    if mismatches:
        raise PphonDecompError(
            "A2T EM-flip reconciliation failure(s) -- refusing to publish a verdict:\n  "
            + "\n  ".join(f"{row.label}: {row.detail}" for row in mismatches)
        )

    a2t_section = A2tSection(
        baseline_total_failures=a2t_baseline.total_failures,
        tables={B1_ARM: b1_table, C1_ARM: c1_table, C2_ARM: c2_table},
        em_flip_reconciliation=em_flip_reconciliation,
    )

    return PphonDecompReport(
        pslu_attempt_dir=pslu_attempt_dir,
        pslu_s2_attempt_dir=pslu_s2_attempt_dir,
        a2t_attempt_dir=a2t_attempt_dir,
        a2t_s2b_attempt_dir=a2t_s2b_attempt_dir,
        a2t_s2c_attempt_dir=a2t_s2c_attempt_dir,
        arm_plan_path=resolved_arm_plan_path,
        slurp=slurp_section,
        a2t=a2t_section,
        manifest_verified=manifest_verified,
    )


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _class_counts_json(counts: ClassCounts) -> dict[str, object]:
    return {
        "baseline_failures": counts.baseline_failures,
        "converted": counts.converted,
        "conversion_rate": counts.conversion_rate,
    }


def _class_table_json(table: ArmClassTable) -> dict[str, object]:
    return {
        "carrier": table.carrier,
        "arm": table.arm,
        "classes": {klass: _class_counts_json(table.classes[klass]) for klass in FAILURE_CLASSES},
        "total_baseline_failures": table.total_baseline_failures,
        "total_converted": table.total_converted,
        "conversion_rate_overall": table.conversion_rate_overall,
    }


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def _verdict_json(verdict: PphonVerdict) -> dict[str, object]:
    return {
        "carrier": verdict.carrier,
        "arm": verdict.arm,
        "total_converted": verdict.total_converted,
        "near_miss_share": verdict.near_miss_share,
        "equiv_format_share": verdict.equiv_format_share,
        "cr_near_miss": verdict.cr_near_miss,
        "cr_far_wrong": verdict.cr_far_wrong,
        "near_miss_share_clause": _clause_json(verdict.near_miss_share_clause),
        "near_miss_margin_clause": _clause_json(verdict.near_miss_margin_clause),
        "speech_snap_present": verdict.speech_snap_present,
        "format_dominant_clause": _clause_json(verdict.format_dominant_clause),
        "format_dominant": verdict.format_dominant,
        "boundary_co_fire": verdict.boundary_co_fire,
        "overall": verdict.overall,
    }


def _reconciliation_json(row: ReconciliationRow) -> dict[str, object]:
    return {
        "label": row.label,
        "computed": row.computed,
        "parent_recomputed": row.parent_recomputed,
        "archived": row.archived,
        "matched": row.matched,
        "detail": row.detail,
    }


def report_to_json(report: PphonDecompReport) -> dict[str, object]:
    slurp = report.slurp
    a2t = report.a2t
    return {
        "schema": REPORT_SCHEMA,
        "pslu_attempt_dir": str(report.pslu_attempt_dir),
        "pslu_s2_attempt_dir": str(report.pslu_s2_attempt_dir),
        "a2t_attempt_dir": str(report.a2t_attempt_dir),
        "a2t_s2b_attempt_dir": str(report.a2t_s2b_attempt_dir),
        "a2t_s2c_attempt_dir": str(report.a2t_s2c_attempt_dir),
        "arm_plan_path": str(report.arm_plan_path),
        "slurp": {
            "n_gold_entities_total": slurp.n_gold_entities_total,
            "baseline_total_failures": slurp.baseline_total_failures,
            "a3": {
                "table": _class_table_json(slurp.a3),
                "regressions": slurp.a3_regressions,
                "verdict": _verdict_json(slurp.a3_verdict),
            },
            "a1r": {
                "table": _class_table_json(slurp.a1r),
                "regressions": slurp.a1r_regressions,
                "verdict": _verdict_json(slurp.a1r_verdict),
            },
            "concordance": {"concordant": slurp.concordance.concordant, "detail": slurp.concordance.detail},
            "reconciliation": [_reconciliation_json(row) for row in slurp.reconciliation],
        },
        "a2t": {
            "baseline_total_failures": a2t.baseline_total_failures,
            "tables": {arm: _class_table_json(table) for arm, table in a2t.tables.items()},
            "em_flip_reconciliation": {
                arm: _reconciliation_json(row) for arm, row in a2t.em_flip_reconciliation.items()
            },
        },
        "manifest_verified": {k: list(v) for k, v in report.manifest_verified.items()},
    }


def _render_class_table(lines: list[str], table: ArmClassTable) -> None:
    lines.append(
        f"  {'class':<14}{'baseline':>10}{'converted':>11}{'CR(c)':>9}"
    )
    for klass in FAILURE_CLASSES:
        counts = table.classes[klass]
        lines.append(f"  {klass:<14}{counts.baseline_failures:>10}{counts.converted:>11}{counts.conversion_rate:>9.4f}")
    lines.append(
        f"  {'TOTAL':<14}{table.total_baseline_failures:>10}{table.total_converted:>11}"
        f"{table.conversion_rate_overall:>9.4f}"
    )


def _render_verdict(lines: list[str], verdict: PphonVerdict) -> None:
    lines.append(f"  [{verdict.near_miss_share_clause.verdict.upper():>8}] {verdict.near_miss_share_clause.clause_text}")
    lines.append(f"           {verdict.near_miss_share_clause.detail}")
    lines.append(f"  [{verdict.near_miss_margin_clause.verdict.upper():>8}] {verdict.near_miss_margin_clause.clause_text}")
    lines.append(f"           {verdict.near_miss_margin_clause.detail}")
    lines.append(f"  SPEECH-SNAP-PRESENT: {'MET' if verdict.speech_snap_present else 'not met'}")
    lines.append(f"  [{verdict.format_dominant_clause.verdict.upper():>8}] {verdict.format_dominant_clause.clause_text}")
    lines.append(f"           {verdict.format_dominant_clause.detail}")
    lines.append(f"  FORMAT-DOMINANT: {'MET' if verdict.format_dominant else 'not met'}")
    if verdict.boundary_co_fire:
        lines.append("  BOUNDARY CO-FIRE: both verdicts fired simultaneously")
    lines.append(f"  OVERALL ({verdict.carrier}/{verdict.arm}): {verdict.overall}")


def render_report(report: PphonDecompReport) -> str:
    slurp = report.slurp
    a2t = report.a2t
    lines = [
        "P-PHON failure-class decomposition -- registered model-free re-read "
        "(docs/readiness/2026-08-18-pphon-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
        f"pslu attempt dir: {report.pslu_attempt_dir}",
        f"pslu-s2 attempt dir: {report.pslu_s2_attempt_dir}",
        f"a2t (A0) attempt dir: {report.a2t_attempt_dir}",
        f"a2t-s2b attempt dir: {report.a2t_s2b_attempt_dir}",
        f"a2t-s2c attempt dir: {report.a2t_s2c_attempt_dir}",
        f"arm plan (reused verbatim): {report.arm_plan_path}",
        "",
        "SLURP (primary)",
        "-" * 40,
        f"n_gold_entities_total={slurp.n_gold_entities_total}  baseline_total_failures={slurp.baseline_total_failures}",
        "",
        "A3 (primary supply arm) per-class table",
    ]
    _render_class_table(lines, slurp.a3)
    lines.append(f"  regressions (A0-correct, A3-incorrect): {slurp.a3_regressions}")
    lines.append("")
    lines.append("A3 verdict")
    _render_verdict(lines, slurp.a3_verdict)
    lines.append("")
    lines.append("A1'r (concordance) per-class table")
    _render_class_table(lines, slurp.a1r)
    lines.append(f"  regressions (A0-correct, A1'r-incorrect): {slurp.a1r_regressions}")
    lines.append("")
    lines.append("A1'r verdict")
    _render_verdict(lines, slurp.a1r_verdict)
    lines.append("")
    lines.append(f"CONCORDANCE (A1'r vs A3): {'CONCORDANT' if slurp.concordance.concordant else 'DISCORDANT'}")
    lines.append(f"  {slurp.concordance.detail}")
    lines.append("")
    lines.append("SLURP reconciliation (computed / parent-recomputed / archived)")
    for row in slurp.reconciliation:
        status = "OK" if row.matched else "MISMATCH"
        lines.append(f"  [{status:>8}] {row.label}: {row.detail}")
    lines.append("")

    lines.append("A2T (secondary, orthographic proxy only; B1/C1/C2 descriptive)")
    lines.append("-" * 40)
    lines.append(f"baseline_total_failures={a2t.baseline_total_failures}")
    lines.append("")
    for arm in (B1_ARM, C1_ARM, C2_ARM):
        lines.append(f"arm {arm} per-class table")
        _render_class_table(lines, a2t.tables[arm])
        lines.append("")
    lines.append("A2T EM-flip reconciliation (computed / parent-recomputed / archived, exact gate at n=120)")
    for arm, row in a2t.em_flip_reconciliation.items():
        status = "OK" if row.matched else "MISMATCH"
        lines.append(f"  [{status:>8}] {row.label}: {row.detail}")
    lines.append("")

    lines.append("MANIFEST verification (input archives)")
    for key, files in report.manifest_verified.items():
        lines.append(f"  {key}: {len(files)} file(s) verified")

    return "\n".join(lines)


def _write_manifest_sha256(output_dir: Path) -> None:
    output_dir = Path(output_dir)
    entries: list[str] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.sha256":
            continue
        rel = path.relative_to(output_dir).as_posix()
        entries.append(f"{_sha256_file(path)} *./{rel}")
    (output_dir / "MANIFEST.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8", newline="\n")


def _render_readme(report: PphonDecompReport) -> str:
    slurp = report.slurp
    lines = [
        "# P-PHON failure-class decomposition -- registered model-free re-read",
        "",
        f"Schema: `{REPORT_SCHEMA}`. Registered design: "
        "`docs/readiness/2026-08-18-pphon-preregistration-REGISTERED.md`. "
        "Exposure row: `SAEA-CHECK-pphon-decomp`.",
        "",
        "Re-reads five ALREADY-CONSUMED attempts (pslu_read, pslu_s2_read, a2t_read, "
        "a2t_s2b_read, a2t_s2c_read) with a NEW, narrower instrument "
        "(`analysis.pphon_decomp` + this CLI) over the SAME archived `outputs.jsonl` files, "
        "hash-verified against their MANIFESTs before reading. The original one-shot reads "
        "remain consumed and their own verdicts untouched.",
        "",
        "## Attempt dirs",
        "",
        f"- pslu (A0+A3): `{report.pslu_attempt_dir}`",
        f"- pslu-s2 (A1'r): `{report.pslu_s2_attempt_dir}`",
        f"- a2t (A0): `{report.a2t_attempt_dir}`",
        f"- a2t-s2b (B1): `{report.a2t_s2b_attempt_dir}`",
        f"- a2t-s2c (C1/C2): `{report.a2t_s2c_attempt_dir}`",
        f"- arm plan (reused verbatim): `{report.arm_plan_path}`",
        "",
        "## SLURP-A3 verdict (primary)",
        "",
        f"**{slurp.a3_verdict.overall}**",
        "",
        "## A1'r concordance",
        "",
        f"**{'CONCORDANT' if slurp.concordance.concordant else 'DISCORDANT'}** -- {slurp.concordance.detail}",
        "",
        "## Files",
        "",
        "- `verdict.json` -- machine-readable report",
        "- `report.txt` -- human-rendered report (per-class tables, verdicts, concordance, "
        "reconciliation, integrity section)",
        "- `MANIFEST.sha256` -- hashes of every file in this directory",
    ]
    return "\n".join(lines) + "\n"


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pphon-decomp",
        description=(
            "P-PHON failure-class decomposition pinned offline read suite: classifies every "
            "SLURP A0-failed slot (SPEECH-SNAP-PRESENT/FORMAT-DOMINANT/MIXED verdict on A3, "
            "A1'r concordance mandatory) and every A2T A0-failed argument (B1/C1/C2, "
            "descriptive) into MISSING/EQUIV-FORMAT/NEAR-MISS/FAR-WRONG. Model-free, "
            "read-only; never opens a model session."
        ),
    )
    parser.add_argument("pslu_attempt_dir", type=Path, help="the pslu_read flight's own attempt directory (A0+A3)")
    parser.add_argument(
        "pslu_s2_attempt_dir", type=Path, help="the pslu_s2_read flight's own attempt directory (A1'r)"
    )
    parser.add_argument(
        "a2t_attempt_dir", type=Path, help="the a2t_read (A0 discovery) flight's own attempt directory"
    )
    parser.add_argument(
        "a2t_s2b_attempt_dir", type=Path, help="the a2t_s2b_read flight's own attempt directory (B1/B2)"
    )
    parser.add_argument(
        "a2t_s2c_attempt_dir", type=Path, help="the a2t_s2c_read flight's own attempt directory (C1/C2/C3)"
    )
    parser.add_argument("--output-dir", required=True, type=Path, help="directory to write the report bundle to")
    parser.add_argument("--pslu-sample-manifest", type=Path, default=None)
    parser.add_argument("--pslu-roster-table", type=Path, default=None)
    parser.add_argument("--pslu-filler-lexicon", type=Path, default=None)
    parser.add_argument("--a2t-headroom-manifest", type=Path, default=None)
    parser.add_argument("--a2t-arm-plan", type=Path, default=None, help="override the reused stage-2 arm-plan.json path")
    parser.add_argument("--split-role", default=DEFAULT_SPLIT_ROLE, help=f"default: {DEFAULT_SPLIT_ROLE!r}")
    parser.add_argument("--pslu-read-archive", type=Path, default=None)
    parser.add_argument("--pslu-s2-read-archive", type=Path, default=None)
    parser.add_argument("--a2t-a0-read-archive", type=Path, default=None)
    parser.add_argument("--a2t-s2b-read-archive", type=Path, default=None)
    parser.add_argument("--a2t-s2c-read-archive", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None, help="TEST-ONLY override of the study repo root")
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import REPO_ROOT, write_json_artifact

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    pslu_sample_manifest_path = args.pslu_sample_manifest or (
        repo_root / "configs/probes/g0-binding/pslu-sample-devel-n60.json"
    )
    pslu_roster_table_path = args.pslu_roster_table or (
        repo_root / "configs/probes/g0-binding/pslu-rosters-train-only.json"
    )
    pslu_filler_lexicon_path = args.pslu_filler_lexicon or (
        repo_root / "configs/probes/g0-binding/pslu-s2-filler-lexicon.json"
    )
    a2t_headroom_path = args.a2t_headroom_manifest or (
        _default_archive_dir(repo_root, A2T_A0_READ_ARCHIVE_DIRNAME) / "headroom.json"
    )

    output_dir = Path(args.output_dir)
    verdict_path = output_dir / "verdict.json"
    if verdict_path.exists():
        print(
            f"REFUSED: {verdict_path} already exists -- this suite refuses to run twice against the same "
            "output dir (one-shot read discipline); choose a fresh --output-dir if a genuinely new read is "
            "intended",
            file=sys.stderr,
        )
        return 1

    lock = load_lock(umbrella_lock_path(repo_root))
    root = data_root()

    try:
        report = build_pphon_decomp_report(
            args.pslu_attempt_dir,
            args.pslu_s2_attempt_dir,
            args.a2t_attempt_dir,
            args.a2t_s2b_attempt_dir,
            args.a2t_s2c_attempt_dir,
            lock,
            root,
            repo_root=repo_root,
            pslu_sample_manifest_path=pslu_sample_manifest_path,
            pslu_roster_table_path=pslu_roster_table_path,
            pslu_filler_lexicon_path=pslu_filler_lexicon_path,
            a2t_headroom_path=a2t_headroom_path,
            a2t_arm_plan_path=args.a2t_arm_plan,
            split_role=args.split_role,
            pslu_read_archive_dir=args.pslu_read_archive,
            pslu_s2_read_archive_dir=args.pslu_s2_read_archive,
            a2t_a0_read_archive_dir=args.a2t_a0_read_archive,
            a2t_s2b_read_archive_dir=args.a2t_s2b_read_archive,
            a2t_s2c_read_archive_dir=args.a2t_s2c_read_archive,
        )
    except (
        PphonDecompError,
        PsluReadError,
        PsluS2ReadError,
        A2tReadError,
        A2tS2ReadError,
        A2tS2bReadError,
        A2tS2cReadError,
    ) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json_artifact(verdict_path, report_to_json(report))
    rendered = render_report(report)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    (output_dir / "README.md").write_text(_render_readme(report), encoding="utf-8", newline="\n")
    _write_manifest_sha256(output_dir)
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
