"""P-A2T selection-loss decomposition -- registered model-free re-read
(pinned, pre-registered) -- SAEA-CHECK-a2t-loss-decomp.

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory. It is a NARROWER instrument layered ON TOP OF
three ALREADY-CONSUMED read suites (``analysis.a2t_s2_read``,
``analysis.a2t_s2b_read``, ``analysis.a2t_s2c_read``), re-reading their SAME
archived ``outputs.jsonl`` files to answer one question those suites'
pooled/branch metrics could not: when a supply arm loses an already-correct
tool selection, where does the selection GO -- dragged to the arm's own
highlighted/supplied WRONG tool, drifted to some OTHER wrong tool, collapsed
to an EMPTY call, or lost to a PARSE-FAIL row.

Purpose (``docs/readiness/2026-08-18-a2t-loss-decomp-preregistration-
REGISTERED.md``): classify every lost selection (A0-correct -> arm-incorrect)
for eight arms across three already-flown, already-consumed attempts --

- **B2** (Stage-2b, 21 losses) -- the verdict carrier: DRAG-CONFIRMED (>=
  11/21 DRAGGED-TO-SUPPLIED) / DRIFT-CONFIRMED (<= 5/21, N0r shape reported
  side-by-side) / MIXED.
- **N0r** (Stage-2, 5 losses) -- the zero-supply DRIFT REFERENCE shape.
- **C3** (Stage-2c, 7 losses) -- descriptive (augment-form drift picture).
- **S1'/S2/B1/C1/C2** -- descriptive completeness; DRAGGED-TO-SUPPLIED is
  structurally impossible for these arms (their supplied tool IS the
  correct tool) and is asserted, not merely omitted.

A fifth class, **MULTIPLICITY** (correct tool SET, wrong call COUNT --
2026-08-18 amendment, note 1 below), applies to every one of the eight arms
and is never structurally impossible for any of them.

REUSE, NOT RE-DERIVATION. Every parsing/scoring/loading primitive below is
imported directly from the three consumed suites, never reimplemented a
second way:

- ``analysis.a2t_s2_read.load_attempt_rows``/``load_arm_plan``/``ArmPlan``/
  ``OutputRow``/``ClauseResult``/``A2tS2ReadError`` for the SAME row shape,
  arm-plan shape, and clause-record shape every sibling suite already uses
  (``load_flight_receipt``/``load_headroom_identity`` are reused
  INDIRECTLY, inside the three ``build_a2t_s2*_report`` calls below, which
  already fully validate ``flight-receipt.json``/``headroom.json`` before
  this module's own row walk runs -- no second, redundant direct call).
- ``analysis.a2t_s2_read.build_a2t_s2_report`` / ``analysis.a2t_s2b_read.
  build_a2t_s2b_report`` / ``analysis.a2t_s2c_read.build_a2t_s2c_report`` --
  called here UNCHANGED as this module's own harness-defect/integrity GATE
  (every check those suites already perform -- row completeness, duplicate
  pairs, receipt status, split-identity-hash, arm-plan/headroom consistency,
  S4-derangement no-fixed-point -- fires before this module's own per-row
  walk ever runs) AND as a second, independently-scored source of each arm's
  own retention (module docstring "three-way reconciliation" below).
- ``reproduction.toolcall_scoring.parse_tool_calls_text`` (the tool-selection
  extraction primitive) and ``analysis.a2t_read.is_empty_tool_call`` (the
  empty-call classifier) -- the SAME two calls ``analysis.a2t_s2_read.
  score_row`` itself makes internally. ``reproduction.toolcall_scoring.
  score_item`` -- the SAME name-MULTISET ``tool_accuracy`` comparator every
  consumed suite's own ``Audio2ToolAdapter.score`` calls internally -- is
  ALSO now this module's own loss-detection comparator (note 1, 2026-08-18
  amendment).
- ``data.audio2tool.load_expected_calls`` -- the A0-comparator's own gold
  source, reused for the sanity re-check note 1 below describes.

ENGINEERING-INTERPRETATION NOTES (flagged here, mirroring the three consumed
suites' own discipline -- each is a documented, reviewable choice, not a
silent guess):

1. **AMENDED 2026-08-18 (preregistration section 5): a loss is exactly what
   the PARENTS' OWN multiset ``tool_accuracy`` comparison scores != 1.0,
   never a deduplicated distinct-tool-IDENTITY comparison.** The first
   execution attempt refused at this module's own three-way reconciliation
   gate (note 4) before writing any output row: one headroom sample
   (``tier3_multi_intent:003994``) carries a duplicated GOLD tool name
   (``{setZoneTemperature: 2, setCabinOverheatProtection: 1}``), and the
   PRE-amendment identity/SET comparison below silently treated "same
   distinct tool SET, wrong call COUNT" as a retained correct selection --
   undercounting every full-headroom arm's own loss total by exactly one.
   The repair: a row is a loss iff ``reproduction.toolcall_scoring.
   score_item(gold, predicted).tool_accuracy != 1.0`` -- ``score_item`` (a
   ``collections.Counter`` comparison of tool NAMES, never arguments) is
   IMPORTED and called UNCHANGED, never reimplemented a second way, against
   ``gold`` = this sample's own fresh ``data.audio2tool.load_expected_calls``
   entry (already loaded once, for the sanity re-check this note's tail
   describes, and reused here rather than re-loaded a second time). A loss
   whose predicted call's own distinct-tool SET nonetheless equals the
   correct SET (right tool(s), wrong call COUNT) classifies as the fifth
   class, **MULTIPLICITY** (:func:`classify_loss`) -- structurally neither
   dragged nor drifted, and legal for every arm (note 3).

   The PRE-amendment design, kept here for the record since one piece of it
   still applies (below): ``rails.probes.a2t_s2_flight.
   derive_a0_selected_tools`` already computed, ONCE, "the tool(s) the core
   ITSELF named in its own A0 response" for every headroom sample, straight
   from the CONSUMED A0 attempt's own rows (reusing ``analysis.a2t_read.
   load_attempt_rows`` + ``reproduction.toolcall_scoring.
   parse_tool_calls_text``), and froze the result into ``{RUN_ID}.
   arm-plan.json``'s own ``selected_tools`` field -- a SORTED, DEDUPLICATED
   tool-name tuple, never the raw multiset A0 itself predicted. Combined
   with the headroom set's own DEFINING criterion (``tool_accuracy == 1.0``,
   i.e. A0's predicted tool-name multiset equals gold's), that deduplicated
   tuple's DISTINCT-TOOL SET is still exactly gold's own distinct-tool set
   for every headroom sample (dedup of two equal multisets is the same set)
   -- so ``arm_plan.selected_tools[sample_id]`` remains exactly right as the
   ``correct_tool_names`` argument :func:`classify_loss` uses for its
   MULTIPLICITY SET-equality check, even though it is NO LONGER trusted as
   the LOSS-DETECTION comparator itself (that role moved to fresh gold +
   ``score_item``, above -- the SAME distinct-tool-IDENTITY convention
   ``rails.probes.a2t_s2_flight.build_s4_derangement`` uses for deriving the
   derangement is preserved for THIS narrower SET-equality role, just no
   longer for loss detection). The A0-comparator sanity check inside
   :func:`build_loss_decomp_report` still independently re-verifies
   ``arm_plan.selected_tools``'s own distinct-SET agreement with fresh gold
   for every headroom sample before trusting the frozen file for that
   narrower role -- an orthogonal, cheap integrity check, not a
   re-derivation.
2. **DRIFT-CONFIRMED's "compatible with N0r's reference shape" clause is a
   REPORTING obligation, not a second boolean gate; "11/21"/"5/21" are
   RATIOS of B2's OWN total loss count, never a raw count fixed to the
   literal 21.** The preregistration's own text is explicit that no
   statistical test applies at n=21 vs n=5 ("stated as a shape comparison,
   not inference"). Mirrors ``analysis.a2t_s2_read``'s own note 10 precedent
   for its "PER-TIER REPORTING MANDATORY" language: read as an obligation on
   the RENDERED REPORT (the full N0r and B2 class-distribution tables are
   ALWAYS printed side-by-side whenever DRIFT-CONFIRMED's own numeric clause
   is met), never as an undefined second mechanical condition invented by
   this suite on its own authority. The 11/21 and 5/21 fractions themselves
   are read as RATIOS of B2's own ``n_losses`` (:data:`DRAG_CONFIRMED_MIN_RATIO`
   / :data:`DRIFT_CONFIRMED_MAX_RATIO`, both compared against ``dragged /
   total``) rather than raw counts hardcoded to the literal "21" -- the SAME
   testability-preserving choice ``analysis.a2t_s2b_read``'s own module
   docstring note 1 documents ("RATIOS, not raw counts fixed to n=120 ...
   keeps the evaluator well-defined for a small synthetic fixture"),
   numerically identical to the literal fraction at the real flight's own 21
   losses. :func:`evaluate_b2_verdict` evaluates DRAG-CONFIRMED and
   DRIFT-CONFIRMED from ONE ratio threshold each (numerically disjoint --
   11/21 > 5/21 -- so checked in the registered order purely for
   defense-in-depth, mirroring ``analysis.a2t_s2c_read.
   evaluate_form_robustness``'s own ROBUST/FORM-FRAGILE pattern), with MIXED
   as the fallback for the gap between them (and for the degenerate
   zero-loss case, guarded explicitly rather than left to divide-by-zero).
3. **Structural impossibility is asserted at TWO levels.** Level one (the
   PREMISE): for every non-drag arm (S1', S2, B1, C1, C2 -- C3 too, though
   the preregistration calls its own drag concept merely "undefined" rather
   than "impossible" since C3's supply MECHANISM is augmentation, not
   narrowing; the structural fact is identical either way), this module
   asserts ``arm_plan.s1p_tool_names[sample_id] == arm_plan.selected_tools
   [sample_id]`` (set-equality) BEFORE scoring a single row -- proving the
   premise "this arm's supplied tool IS the correct tool" holds for real,
   never assumed. Level two (the CONSEQUENCE, defense-in-depth):
   :func:`_supplied_wrong_tool` returns ``None`` for every arm other than B2,
   so :func:`classify_loss` can never structurally PRODUCE
   ``DRAGGED-TO-SUPPLIED`` for them; :func:`_build_arm_loss_table` still
   re-asserts this post hoc over every emitted row (unreachable in practice,
   `# pragma: no cover`, mirroring ``rails.probes.a2t_s2_flight.
   build_s4_derangement``'s own "Sattolo's algorithm precludes this; defense
   in depth" precedent) rather than relying on the level-one premise alone.
   MULTIPLICITY is deliberately EXEMPT from this guard (2026-08-18
   amendment): a MULTIPLICITY loss never implies the arm selected a WRONG
   tool identity, only a wrong call COUNT among the correct tool(s), so it
   is legal for every arm, correct-tool arms included -- only
   DRAGGED-TO-SUPPLIED remains structurally impossible for non-B2 arms.
4. **Three-way reconciliation, fail-closed on any disagreement.** For every
   one of the eight arms this module reconciles its OWN per-row loss count
   against (a) that SAME arm's fresh ``ArmAggregate.tool_accuracy`` from
   this module's own call into the appropriate consumed suite's
   ``build_a2t_s2*_report`` (an independently-scored number, since that
   pipeline scores against FRESH gold via ``reproduction.toolcall_scoring.
   score_item``, never against ``arm_plan.selected_tools``) and (b) the
   SAME arm's ``tool_selection_retention`` as PUBLISHED in the already-
   consumed, git-committed ``verdict.json`` under the matching
   ``2026-08-18-a2t-s2{,b,c}-read/`` archive (MANIFEST-verified before
   trusting its bytes -- :func:`verify_archive_manifest`). This three-way
   match is scale-invariant (works identically at the real 120/40-sample
   flight and at a hand-authored 20-sample test fixture) and is, at the
   real flight's own known scale, MECHANICALLY EQUIVALENT to "B2 must yield
   exactly 21 losses, N0r 5, C3 7" (the archived retention for those three
   arms genuinely retention-implies exactly those counts). The mission's own
   literal numbers are ADDITIONALLY pinned as :data:`EXACT_LOSS_COUNT_GATES`
   -- ``(count, real_arm_size)`` pairs -- and :func:`reconcile_arm` enforces
   each one ONLY when the arm being reconciled genuinely carries that real
   size (``n_samples == 120`` for B2/C3, ``== 40`` for N0r); at any OTHER
   scale (every hand-authored fixture in this module's own test suite) the
   gate is reported as "not applicable" rather than spuriously enforced --
   the literal "21" is a property of the one real, pinned flight, not a
   ratio this suite's own tests must be contorted to reproduce.
5. **MANIFEST coverage is honest about what is and is not pinned.**
   ``flight-receipt.json`` (cross-checked against each flight archive's own
   git-committed, MANIFEST-verified copy), ``headroom.json`` (verified
   in-place against the frozen A0-read archive's own manifest) and each
   consumed suite's ``verdict.json`` (verified in-place against its own read
   archive's manifest) all carry a real, git-committed sha256 pin this
   module checks BEFORE trusting their bytes. ``outputs.jsonl`` and
   ``{RUN_ID}.arm-plan.json`` carry NO such pin anywhere in this repository
   -- by design, never committed (umbrella first principle: never commit
   data/weights/speech files/raw traces) -- so their integrity rests
   entirely on the reused harness-defect gate (note above) plus the
   three-way reconciliation (note 4): a tampered ``outputs.jsonl`` that
   still passes both would have to reproduce the SAME retention number three
   independent ways, which this module treats as adequate fail-closed
   coverage for an unpinnable file, not as a gap silently ignored --
   :data:`UNPINNED_INPUTS` names them explicitly in every report.
6. **N0r's own row domain is ``arm_plan.n0r_sample_ids`` (40 ids), never
   ``headroom_ids`` (120)** -- N0r is Stage-2's own 40-sample tier-
   proportional re-fly subset, not a full-headroom arm; every other
   configured arm (S1', S2, B1, B2, C1, C2, C3) iterates the full
   ``headroom_ids``. :func:`_sample_domain` makes this dispatch explicit
   rather than leaving it implicit in a loop.

DEVELOPED AND TESTED EXCLUSIVELY AGAINST HAND-AUTHORED SYNTHETIC FIXTURES
(``tests/unit/test_a2t_loss_decomp.py``, reusing ``test_a2t_s2_read``'s own
``A2tS2World``/response builders and ``test_a2t_s2b_read``/
``test_a2t_s2c_read``'s own B/C-arm attempt builders directly). This module
is NEVER run against the real, already-consumed attempt directories
(``$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2{,b,c}-120/``) by the task that
wrote it -- that is a separately gated, one-shot execution mission.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from ..reproduction.toolcall_scoring import ToolCall, parse_tool_calls_text, score_item
from ..rails.probes.a2t_s2_flight import N0R_ARM, S1P_ARM, S2_ARM
from ..rails.probes.a2t_s2b_flight import B1_ARM, B2_ARM
from ..rails.probes.a2t_s2c_flight import C1_ARM, C2_ARM, C3_ARM
from .a2t_read import is_empty_tool_call
from .a2t_s2_read import (
    ArmPlan,
    A2tS2ReadError,
    ClauseResult,
    OutputRow,
    build_a2t_s2_report,
    load_arm_plan,
    load_attempt_rows,
)
from .a2t_s2b_read import A2tS2bReadError, build_a2t_s2b_report, _default_stage2_arm_plan_path
from .a2t_s2c_read import A2tS2cReadError, build_a2t_s2c_report

REPORT_SCHEMA = "saea-a2t-loss-decomp-read-v1"
DEFAULT_SPLIT_ROLE = "discovery"

CHECK_DIR = "speech-aware-evidence-acquisition"
HEADROOM_ARCHIVE_DIRNAME = "2026-08-18-pa2t-a0-read"
S2_FLIGHT_ARCHIVE_DIRNAME = "2026-08-18-a2t-s2-flight"
S2B_FLIGHT_ARCHIVE_DIRNAME = "2026-08-18-a2t-s2b-flight"
S2C_FLIGHT_ARCHIVE_DIRNAME = "2026-08-18-a2t-s2c-flight"
S2_READ_ARCHIVE_DIRNAME = "2026-08-18-a2t-s2-read"
S2B_READ_ARCHIVE_DIRNAME = "2026-08-18-a2t-s2b-read"
S2C_READ_ARCHIVE_DIRNAME = "2026-08-18-a2t-s2c-read"

# Loss classes (preregistration section 2, quoted verbatim, PLUS the
# 2026-08-18 amendment's fifth class MULTIPLICITY -- module docstring note 1).
DRAGGED_TO_SUPPLIED = "DRAGGED-TO-SUPPLIED"
DRIFTED_OTHER = "DRIFTED-OTHER"
MULTIPLICITY = "MULTIPLICITY"
EMPTY = "EMPTY"
PARSE_FAIL = "PARSE-FAIL"
LOSS_CLASSES: tuple[str, ...] = (DRAGGED_TO_SUPPLIED, DRIFTED_OTHER, MULTIPLICITY, EMPTY, PARSE_FAIL)
LossClass = Literal["DRAGGED-TO-SUPPLIED", "DRIFTED-OTHER", "MULTIPLICITY", "EMPTY", "PARSE-FAIL"]

# The eight configured arms (preregistration section 2 -- S4 is NOT in scope).
CORRECT_TOOL_ARMS: tuple[str, ...] = (S1P_ARM, S2_ARM, B1_ARM, C1_ARM, C2_ARM, C3_ARM)
DRAG_POSSIBLE_ARMS: tuple[str, ...] = (B2_ARM,)
ALL_ARMS: tuple[str, ...] = (N0R_ARM, S1P_ARM, S2_ARM, B1_ARM, B2_ARM, C1_ARM, C2_ARM, C3_ARM)

# arm -> which attempt dir role ("s2" / "s2b" / "s2c") carries its rows, and
# which read archive published its retention (identical role for all eight).
ARM_DIR_ROLE: Mapping[str, str] = {
    N0R_ARM: "s2",
    S1P_ARM: "s2",
    S2_ARM: "s2",
    B1_ARM: "s2b",
    B2_ARM: "s2b",
    C1_ARM: "s2c",
    C2_ARM: "s2c",
    C3_ARM: "s2c",
}

# Preregistration section 3 verbatim + note 4: the mission's own literal
# reconciliation targets (count, the real arm size that count is OVER) --
# ``reconcile_arm`` applies each gate ONLY when the arm being reconciled
# genuinely carries that real-world size (40 for N0r, 120 for B2/C3), never
# spuriously against a smaller synthetic fixture's own, differently-sized
# arm (note 4 explains why: the literal "21" is a property of the REAL
# 120-sample flight, not a scale-invariant ratio this suite's own tests
# should be forced to reproduce at a hand-authored world's own smaller n).
EXACT_LOSS_COUNT_GATES: Mapping[str, tuple[int, int]] = {
    N0R_ARM: (5, 40),
    B2_ARM: (21, 120),
    C3_ARM: (7, 120),
}

# Preregistration section 3 verbatim thresholds, read as RATIOS of B2's own
# TOTAL loss count (note 2) -- "11/21"/"5/21" is "11 (5) out of however many
# B2's own losses actually number", not a raw count fixed to literal 21;
# mirrors ``analysis.a2t_s2b_read``'s own module docstring note 1 precedent
# ("RATIOS, not raw counts fixed to n=120 ... keeps the evaluator
# well-defined for a small synthetic fixture"). At the real flight's own 21
# losses this is numerically identical to the literal fraction.
DRAG_CONFIRMED_MIN_RATIO = 11 / 21
DRIFT_CONFIRMED_MAX_RATIO = 5 / 21

# Note 5: files this module never expects a committed sha256 pin for.
UNPINNED_INPUTS: tuple[str, ...] = ("outputs.jsonl", "{RUN_ID}.arm-plan.json")


class A2tLossDecompError(RuntimeError):
    """A harness defect the reused consumed-suite gate refuses on, a
    MANIFEST.sha256 integrity failure, an A0-comparator sanity mismatch, or
    a reconciliation disagreement -- never raised for an ordinary,
    structurally clean read. Mirrors the two-exception-class convention
    ``analysis.a2t_s2b_read``/``analysis.a2t_s2c_read`` already establish:
    a RAW failure inside a directly reused consumed-suite loader surfaces as
    that loader's OWN error type unchanged (never re-wrapped)."""


# ---------------------------------------------------------------------------
# MANIFEST.sha256 verification (note 5): a general, fail-closed primitive.
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_manifest_sha256(path: Path) -> dict[str, str]:
    """``{relpath (leading './' stripped): lowercase hex digest}`` --
    accepts both the ``sha256sum -b`` binary-mode format this repo's own
    ``archive.sh`` scripts emit (``<hex> *./name``) and plain ``sha256sum``
    text-mode format (``<hex>  ./name``, no asterisk) -- both are observed
    in this repository's own committed archives."""

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
            raise A2tLossDecompError(f"{path}: malformed MANIFEST.sha256 line: {line!r}")
        entries[rel] = digest.lower()
    if not entries:
        raise A2tLossDecompError(f"{path}: MANIFEST.sha256 carries zero entries")
    return entries


def verify_archive_manifest(
    archive_dir: Path, *, cross_check: Mapping[str, Path] = {}
) -> tuple[str, ...]:
    """Fail-closed integrity gate (note 5): every file the archive's own
    ``MANIFEST.sha256`` lists must exist under ``archive_dir`` and hash-match
    (self-consistency of the committed, git-tracked archive). Any relname
    named in ``cross_check`` (archive-relative name -> a LIVE, uncommitted
    path this module actually reads for scoring) must ALSO hash-match the
    archive's own pinned digest for that relname -- tamper/drift evidence
    between archival time and read time. Returns the sorted tuple of
    relnames the archive's own manifest lists."""

    archive_dir = Path(archive_dir)
    manifest_path = archive_dir / "MANIFEST.sha256"
    if not manifest_path.is_file():
        raise A2tLossDecompError(f"{manifest_path}: missing -- refusing to trust this archive")
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
        raise A2tLossDecompError(
            f"MANIFEST.sha256 integrity failure(s) under {archive_dir}:\n  " + "\n  ".join(problems)
        )
    return tuple(sorted(pinned))


# ---------------------------------------------------------------------------
# Per-row classification (notes 1, 3, 6).
# ---------------------------------------------------------------------------


def _sample_domain(arm: str, arm_plan: ArmPlan) -> tuple[str, ...]:
    """Note 6: N0r iterates its own 40-sample re-fly subset; every other
    configured arm iterates the full 120-sample headroom set."""

    return arm_plan.n0r_sample_ids if arm == N0R_ARM else arm_plan.headroom_ids


def _supplied_wrong_tool(arm: str, arm_plan: ArmPlan, sample_id: str) -> str | None:
    """The arm's own highlighted/supplied WRONG tool for DRAGGED-TO-SUPPLIED
    -- ``None`` for every arm other than B2 (note 3, level two): B2's wrong
    row comes from Stage-2's OWN derangement mapping (``arm_plan.
    s4_tool_name``), reused verbatim, never re-derived."""

    if arm == B2_ARM:
        return arm_plan.s4_tool_name.get(sample_id)
    return None


def _correct_tool_roster(arm_plan: ArmPlan, sample_id: str) -> tuple[str, ...]:
    """The correct-tool roster ``s1p_tool_names`` supplies -- identical for
    EVERY non-drag arm (note 3, level one): S1'/S2/B1/C1/C2/C3 all reuse
    this SAME field (``configs/probes/g0-binding/a2t-s2{b,c}-flight.json``'s
    own ``arm_semantics``: B1/C1/C2/C3 render S1p's exact reused roster;
    S2's OWN ``supplied_tool`` label also names it, dilution
    notwithstanding), so this helper takes no ``arm`` parameter at all."""

    return arm_plan.s1p_tool_names.get(sample_id, ())


def assert_structural_premises(arm_plan: ArmPlan) -> None:
    """Note 3, level one: for every non-drag arm, the premise "supplied tool
    IS the correct tool" -- checked as SET equality against ``selected_tools``
    (A0's own recorded selection, note 1) -- must hold for EVERY headroom
    sample before this module scores a single row. For B2, the OPPOSITE
    premise (the highlighted tool is NOT the correct one) is checked with
    equal rigor. Fail-closed on any violation: a violated premise would
    silently invalidate every DRAGGED-TO-SUPPLIED/structural-impossibility
    conclusion this module draws."""

    problems: list[str] = []
    for sample_id in arm_plan.headroom_ids:
        correct = tuple(sorted(set(_correct_tool_roster(arm_plan, sample_id))))
        a0_selected = tuple(sorted(set(arm_plan.selected_tools.get(sample_id, ()))))
        if correct != a0_selected:
            problems.append(
                f"sample {sample_id!r}: s1p_tool_names {correct!r} != selected_tools {a0_selected!r} "
                "-- the 'supplied tool IS the correct tool' premise does not hold"
            )
        wrong = arm_plan.s4_tool_name.get(sample_id)
        if wrong is not None and wrong in set(a0_selected):
            problems.append(
                f"sample {sample_id!r}: B2's highlighted wrong tool {wrong!r} IS one of A0's own "
                f"correct selections {a0_selected!r} -- the derangement no-fixed-point premise does "
                "not hold"
            )
    if problems:
        raise A2tLossDecompError(
            "structural premise violation(s) -- refusing to classify:\n  " + "\n  ".join(problems)
        )


def classify_loss(
    *,
    parsed: bool,
    predicted_names: tuple[str, ...],
    supplied_wrong_tool: str | None,
    correct_tool_names: tuple[str, ...] = (),
) -> LossClass:
    """The five mechanical classes (preregistration section 2 + the
    2026-08-18 amendment, module docstring note 1), checked in this
    registered order: PARSE-FAIL (row unparseable), EMPTY (well-formed empty
    call), MULTIPLICITY (the predicted call's own distinct-tool SET equals
    ``correct_tool_names`` exactly -- right tool(s), wrong call COUNT;
    structurally neither dragged nor drifted, legal for every arm -- note
    3), DRAGGED-TO-SUPPLIED (selected tool == the arm's supplied/highlighted
    tool), DRIFTED-OTHER (any other wrong tool). Only called for rows this
    module has ALREADY determined are losses (the parents' own multiset
    ``tool_accuracy`` comparison scored != 1.0 against fresh gold, note 1)."""

    if not parsed:
        return PARSE_FAIL
    if not predicted_names:
        return EMPTY
    if set(predicted_names) == set(correct_tool_names):
        return MULTIPLICITY
    if supplied_wrong_tool is not None and predicted_names == (supplied_wrong_tool,):
        return DRAGGED_TO_SUPPLIED
    return DRIFTED_OTHER


@dataclass(frozen=True)
class LossRow:
    sample_id: str
    a0_tool: str
    arm_tool: str
    klass: LossClass


def _loss_row_for(
    arm: str,
    row: OutputRow,
    arm_plan: ArmPlan,
    expected_calls: Mapping[str, Sequence[ToolCall]],
) -> LossRow | None:
    """``None`` when this row is NOT a loss. 2026-08-18 amendment (note 1):
    a loss is exactly what the PARENTS' OWN ``tool_accuracy`` comparison
    (``reproduction.toolcall_scoring.score_item``, a name-MULTISET
    comparison, reused verbatim) scores != 1.0 against this sample's own
    fresh gold -- never a deduplicated distinct-tool-IDENTITY comparison."""

    predicted, parsed = parse_tool_calls_text(row.response)
    predicted_names = tuple(sorted({call.name for call in predicted}))
    a0_names = arm_plan.selected_tools.get(row.sample_id, ())

    gold = expected_calls.get(row.sample_id, ())
    if score_item(gold, predicted).tool_accuracy == 1.0:  # the parents' own primitive, verbatim
        return None  # arm retained A0's own correct multiset selection -- not a loss

    empty = is_empty_tool_call(row.response)  # reused verbatim (module docstring)
    if not parsed:
        if not empty:  # pragma: no cover -- parse_tool_calls_text fails closed to ([], False)
            raise A2tLossDecompError(
                f"sample {row.sample_id!r} arm {arm!r}: parsed=False but is_empty_tool_call=False -- "
                "parse_tool_calls_text's own fail-closed contract (empty predicted list on failure) "
                "does not hold; refusing to classify"
            )
        klass: LossClass = PARSE_FAIL
        arm_tool_label = "(parse-fail)"
    elif not predicted_names:
        klass = EMPTY
        arm_tool_label = "(empty)"
    else:
        supplied_wrong = _supplied_wrong_tool(arm, arm_plan, row.sample_id)
        klass = classify_loss(
            parsed=parsed,
            predicted_names=predicted_names,
            supplied_wrong_tool=supplied_wrong,
            correct_tool_names=a0_names,
        )
        if klass == DRAGGED_TO_SUPPLIED and arm not in DRAG_POSSIBLE_ARMS:  # pragma: no cover -- note 3
            raise A2tLossDecompError(
                f"sample {row.sample_id!r} arm {arm!r}: classified DRAGGED-TO-SUPPLIED, but this arm is "
                "not in DRAG_POSSIBLE_ARMS -- structural-impossibility invariant violated"
            )
        arm_tool_label = ",".join(predicted_names)

    return LossRow(sample_id=row.sample_id, a0_tool=",".join(a0_names), arm_tool=arm_tool_label, klass=klass)


@dataclass(frozen=True)
class ArmLossTable:
    arm: str
    n_samples: int
    n_losses: int
    class_counts: Mapping[LossClass, int]
    rows: tuple[LossRow, ...]


def build_arm_loss_table(
    arm: str,
    rows: Sequence[OutputRow],
    arm_plan: ArmPlan,
    expected_calls: Mapping[str, Sequence[ToolCall]],
) -> ArmLossTable:
    domain = _sample_domain(arm, arm_plan)
    by_id = {row.sample_id: row for row in rows}
    missing = [sid for sid in domain if sid not in by_id]
    if missing:
        raise A2tLossDecompError(f"arm {arm!r}: no row for {len(missing)} sample(s), e.g. {missing[:5]!r}")

    loss_rows: list[LossRow] = []
    for sample_id in domain:
        loss = _loss_row_for(arm, by_id[sample_id], arm_plan, expected_calls)
        if loss is not None:
            loss_rows.append(loss)
    loss_rows.sort(key=lambda r: r.sample_id)

    counts: dict[LossClass, int] = {klass: 0 for klass in LOSS_CLASSES}
    for loss in loss_rows:
        counts[loss.klass] += 1

    return ArmLossTable(
        arm=arm, n_samples=len(domain), n_losses=len(loss_rows), class_counts=counts, rows=tuple(loss_rows)
    )


# ---------------------------------------------------------------------------
# B2 verdict (preregistration section 3, quoted verbatim; note 2).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class B2Verdict:
    dragged_count: int
    total_losses: int
    drag_confirmed_clause: ClauseResult
    drag_confirmed: bool
    drift_confirmed_clause: ClauseResult
    drift_confirmed: bool
    overall: str
    b2_shape: Mapping[LossClass, int]
    n0r_reference_shape: Mapping[LossClass, int]


def evaluate_b2_verdict(b2_table: ArmLossTable, n0r_table: ArmLossTable) -> B2Verdict:
    dragged = b2_table.class_counts[DRAGGED_TO_SUPPLIED]
    total = b2_table.n_losses
    rate = (dragged / total) if total else 0.0

    drag_clause = ClauseResult(
        f"B2 DRAGGED-TO-SUPPLIED >= {DRAG_CONFIRMED_MIN_RATIO:.4f} (11/21) of B2's own losses",
        "met" if total and rate >= DRAG_CONFIRMED_MIN_RATIO else "not_met",
        f"dragged={dragged}/{total} (rate={rate:.4f}), floor={DRAG_CONFIRMED_MIN_RATIO:.4f}",
    )
    drag_confirmed = drag_clause.verdict == "met"

    drift_clause = ClauseResult(
        f"B2 DRAGGED-TO-SUPPLIED <= {DRIFT_CONFIRMED_MAX_RATIO:.4f} (5/21) of B2's own losses "
        "(N0r reference shape reported side-by-side, note 2: not statistically tested at n=21 vs "
        "n=5, prereg section 3)",
        "met" if total and rate <= DRIFT_CONFIRMED_MAX_RATIO else "not_met",
        f"dragged={dragged}/{total} (rate={rate:.4f}), ceiling={DRIFT_CONFIRMED_MAX_RATIO:.4f}",
    )
    drift_confirmed = (not drag_confirmed) and drift_clause.verdict == "met"

    if drag_confirmed:
        overall = "DRAG-CONFIRMED"
    elif drift_confirmed:
        overall = "DRIFT-CONFIRMED"
    else:
        overall = "MIXED"

    return B2Verdict(
        dragged_count=dragged,
        total_losses=total,
        drag_confirmed_clause=drag_clause,
        drag_confirmed=drag_confirmed,
        drift_confirmed_clause=drift_clause,
        drift_confirmed=drift_confirmed,
        overall=overall,
        b2_shape=dict(b2_table.class_counts),
        n0r_reference_shape=dict(n0r_table.class_counts),
    )


# ---------------------------------------------------------------------------
# Reconciliation (note 4).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReconciliationRow:
    arm: str
    computed_loss_count: int
    parent_recomputed_loss_count: int
    archived_loss_count: int
    matched: bool
    detail: str


def _retention_implied_loss_count(n_samples: int, retention: float) -> int:
    return n_samples - round(n_samples * retention)


def _load_archived_overall(read_archive_dir: Path, arm: str) -> Mapping[str, object]:
    verdict_path = Path(read_archive_dir) / "verdict.json"
    document = json.loads(verdict_path.read_text(encoding="utf-8"))
    try:
        return document["per_arm"][arm]["overall"]
    except (KeyError, TypeError) as error:
        raise A2tLossDecompError(f"{verdict_path}: no per_arm[{arm!r}].overall") from error


def reconcile_arm(
    arm: str,
    table: ArmLossTable,
    parent_overall: Mapping[str, object],
    archived_overall: Mapping[str, object],
) -> ReconciliationRow:
    parent_loss = _retention_implied_loss_count(
        int(parent_overall["n_samples"]), float(parent_overall["tool_selection_retention"])
    )
    archived_loss = _retention_implied_loss_count(
        int(archived_overall["n_samples"]), float(archived_overall["tool_selection_retention"])
    )
    matched = table.n_losses == parent_loss == archived_loss

    # Note 4 / EXACT_LOSS_COUNT_GATES: the mission's own literal targets
    # (21/5/7) apply ONLY when this arm genuinely carries its real-world
    # size (120 for B2/C3, 40 for N0r) -- never spuriously against a
    # smaller synthetic fixture's own, differently-sized arm.
    gate = EXACT_LOSS_COUNT_GATES.get(arm)
    gate_detail = ""
    if gate is not None:
        gate_count, gate_n = gate
        if table.n_samples == gate_n:
            matched = matched and table.n_losses == gate_count
            gate_detail = f", exact_gate={gate_count}/{gate_n} (applies, n_samples matches)"
        else:
            gate_detail = f", exact_gate={gate_count}/{gate_n} (not applicable at n_samples={table.n_samples})"

    detail = f"computed={table.n_losses}, parent_recomputed={parent_loss}, archived={archived_loss}{gate_detail}"
    return ReconciliationRow(
        arm=arm,
        computed_loss_count=table.n_losses,
        parent_recomputed_loss_count=parent_loss,
        archived_loss_count=archived_loss,
        matched=matched,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntegrityReport:
    headroom_archive_verified_files: tuple[str, ...]
    flight_archive_verified: Mapping[str, tuple[str, ...]]
    read_archive_verified: Mapping[str, tuple[str, ...]]
    unpinned_inputs: tuple[str, ...]
    reconciliation: tuple[ReconciliationRow, ...]


@dataclass(frozen=True)
class LossDecompReport:
    s2_attempt_dir: Path
    s2b_attempt_dir: Path
    s2c_attempt_dir: Path
    arm_plan_path: Path
    headroom_path: Path
    split_identity_hash: str
    tables: Mapping[str, ArmLossTable]
    b2_verdict: B2Verdict
    integrity: IntegrityReport


def _default_archive_dir(repo_root: Path, dirname: str) -> Path:
    return Path(repo_root) / "docs" / "checks" / CHECK_DIR / dirname


def _group_rows_by_arm(rows: Sequence[OutputRow], arms: Sequence[str]) -> dict[str, list[OutputRow]]:
    by_arm: dict[str, list[OutputRow]] = {arm: [] for arm in arms}
    for row in rows:
        if row.arm in by_arm:
            by_arm[row.arm].append(row)
    return by_arm


def build_loss_decomp_report(
    s2_attempt_dir: Path,
    s2b_attempt_dir: Path,
    s2c_attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path,
    headroom_path: Path,
    arm_plan_path: Path | None = None,
    headroom_archive_dir: Path | None = None,
    s2_flight_archive_dir: Path | None = None,
    s2b_flight_archive_dir: Path | None = None,
    s2c_flight_archive_dir: Path | None = None,
    s2_read_archive_dir: Path | None = None,
    s2b_read_archive_dir: Path | None = None,
    s2c_read_archive_dir: Path | None = None,
    split_role: str = DEFAULT_SPLIT_ROLE,
) -> LossDecompReport:
    s2_attempt_dir = Path(s2_attempt_dir)
    s2b_attempt_dir = Path(s2b_attempt_dir)
    s2c_attempt_dir = Path(s2c_attempt_dir)
    repo_root = Path(repo_root)
    headroom_path = Path(headroom_path)
    resolved_arm_plan_path = (
        Path(arm_plan_path) if arm_plan_path else _default_stage2_arm_plan_path(repo_root)
    )

    headroom_archive_dir = headroom_archive_dir or _default_archive_dir(repo_root, HEADROOM_ARCHIVE_DIRNAME)
    s2_flight_archive_dir = s2_flight_archive_dir or _default_archive_dir(repo_root, S2_FLIGHT_ARCHIVE_DIRNAME)
    s2b_flight_archive_dir = s2b_flight_archive_dir or _default_archive_dir(repo_root, S2B_FLIGHT_ARCHIVE_DIRNAME)
    s2c_flight_archive_dir = s2c_flight_archive_dir or _default_archive_dir(repo_root, S2C_FLIGHT_ARCHIVE_DIRNAME)
    s2_read_archive_dir = s2_read_archive_dir or _default_archive_dir(repo_root, S2_READ_ARCHIVE_DIRNAME)
    s2b_read_archive_dir = s2b_read_archive_dir or _default_archive_dir(repo_root, S2B_READ_ARCHIVE_DIRNAME)
    s2c_read_archive_dir = s2c_read_archive_dir or _default_archive_dir(repo_root, S2C_READ_ARCHIVE_DIRNAME)

    # 1. The reused consumed-suite gate: every harness-defect check those
    #    three suites already perform, unchanged. Raises directly (module
    #    docstring: two-exception-class convention) on any defect.
    s2_parent = build_a2t_s2_report(
        s2_attempt_dir, lock, root, repo_root=repo_root, headroom_path=headroom_path,
        arm_plan_path=resolved_arm_plan_path, split_role=split_role,
    )
    s2b_parent = build_a2t_s2b_report(
        s2b_attempt_dir, lock, root, repo_root=repo_root, headroom_path=headroom_path,
        stage2_arm_plan_path=resolved_arm_plan_path, split_role=split_role,
    )
    s2c_parent = build_a2t_s2c_report(
        s2c_attempt_dir, lock, root, repo_root=repo_root, headroom_path=headroom_path,
        stage2_arm_plan_path=resolved_arm_plan_path, split_role=split_role,
    )
    split_hashes = {s2_parent.split_identity_hash, s2b_parent.split_identity_hash, s2c_parent.split_identity_hash}
    if len(split_hashes) != 1:
        raise A2tLossDecompError(f"split_identity_hash disagreement across the three attempts: {split_hashes!r}")
    split_identity_hash = split_hashes.pop()

    # 2. Load arm_plan directly for the per-sample dispatch this module's own
    #    row walk needs (the parent reports above only expose per-arm
    #    AGGREGATES, never per-row detail). headroom.json itself is already
    #    fully validated by the gate above (step 1); no second load needed.
    arm_plan = load_arm_plan(resolved_arm_plan_path)

    # 3. Note 3 (level one): the structural premise, asserted before any row
    #    is classified.
    assert_structural_premises(arm_plan)

    # 4. Note 1: the A0-comparator sanity re-check against FRESH gold.
    from ..data.audio2tool import load_expected_calls

    expected_by_id = load_expected_calls(lock, root, repo_root=repo_root)
    comparator_problems: list[str] = []
    for sample_id in arm_plan.headroom_ids:
        gold_names = tuple(sorted({call.name for call in expected_by_id.get(sample_id, ())}))
        a0_names = tuple(sorted(set(arm_plan.selected_tools.get(sample_id, ()))))
        if gold_names != a0_names:
            comparator_problems.append(f"sample {sample_id!r}: gold={gold_names!r} != A0 selection={a0_names!r}")
    if comparator_problems:
        raise A2tLossDecompError(
            "A0-comparator sanity check failed -- refusing to classify:\n  " + "\n  ".join(comparator_problems)
        )

    # 5. Re-load raw rows for the per-sample tool-name extraction this
    #    module's own walk needs (reused loader, called a second time --
    #    step 1's parent reports already proved these rows are structurally
    #    clean).
    s2_rows, _ = load_attempt_rows(s2_attempt_dir)
    s2b_rows, _ = load_attempt_rows(s2b_attempt_dir)
    s2c_rows, _ = load_attempt_rows(s2c_attempt_dir)
    rows_by_arm: dict[str, list[OutputRow]] = {}
    rows_by_arm.update(_group_rows_by_arm(s2_rows, (N0R_ARM, S1P_ARM, S2_ARM)))
    rows_by_arm.update(_group_rows_by_arm(s2b_rows, (B1_ARM, B2_ARM)))
    rows_by_arm.update(_group_rows_by_arm(s2c_rows, (C1_ARM, C2_ARM, C3_ARM)))

    tables: dict[str, ArmLossTable] = {
        arm: build_arm_loss_table(arm, rows_by_arm[arm], arm_plan, expected_by_id) for arm in ALL_ARMS
    }

    # 6. MANIFEST integrity section (note 5).
    headroom_verified = verify_archive_manifest(
        headroom_archive_dir, cross_check={"headroom.json": headroom_path}
    )
    flight_verified = {
        "s2": verify_archive_manifest(
            s2_flight_archive_dir, cross_check={"flight-receipt.json": s2_attempt_dir / "flight-receipt.json"}
        ),
        "s2b": verify_archive_manifest(
            s2b_flight_archive_dir, cross_check={"flight-receipt.json": s2b_attempt_dir / "flight-receipt.json"}
        ),
        "s2c": verify_archive_manifest(
            s2c_flight_archive_dir, cross_check={"flight-receipt.json": s2c_attempt_dir / "flight-receipt.json"}
        ),
    }
    read_verified = {
        "s2": verify_archive_manifest(s2_read_archive_dir),
        "s2b": verify_archive_manifest(s2b_read_archive_dir),
        "s2c": verify_archive_manifest(s2c_read_archive_dir),
    }

    # 7. Reconciliation (note 4), fail-closed on any disagreement.
    parent_overall_by_arm: dict[str, Mapping[str, object]] = {}
    for arm in (N0R_ARM, S1P_ARM, S2_ARM):
        parent_overall_by_arm[arm] = _arm_aggregate_to_mapping(s2_parent.per_arm[arm].overall)
    for arm in (B1_ARM, B2_ARM):
        parent_overall_by_arm[arm] = _arm_aggregate_to_mapping(s2b_parent.per_arm[arm].overall)
    for arm in (C1_ARM, C2_ARM, C3_ARM):
        parent_overall_by_arm[arm] = _arm_aggregate_to_mapping(s2c_parent.per_arm[arm].overall)

    read_archive_by_role = {"s2": s2_read_archive_dir, "s2b": s2b_read_archive_dir, "s2c": s2c_read_archive_dir}
    reconciliation: list[ReconciliationRow] = []
    mismatches: list[str] = []
    for arm in ALL_ARMS:
        archived_overall = _load_archived_overall(read_archive_by_role[ARM_DIR_ROLE[arm]], arm)
        row = reconcile_arm(arm, tables[arm], parent_overall_by_arm[arm], archived_overall)
        reconciliation.append(row)
        if not row.matched:
            mismatches.append(f"arm {arm}: {row.detail}")
    if mismatches:
        raise A2tLossDecompError(
            "loss-count reconciliation failure(s) -- refusing to publish a verdict:\n  " + "\n  ".join(mismatches)
        )

    integrity = IntegrityReport(
        headroom_archive_verified_files=headroom_verified,
        flight_archive_verified=flight_verified,
        read_archive_verified=read_verified,
        unpinned_inputs=UNPINNED_INPUTS,
        reconciliation=tuple(reconciliation),
    )

    b2_verdict = evaluate_b2_verdict(tables[B2_ARM], tables[N0R_ARM])

    return LossDecompReport(
        s2_attempt_dir=s2_attempt_dir,
        s2b_attempt_dir=s2b_attempt_dir,
        s2c_attempt_dir=s2c_attempt_dir,
        arm_plan_path=resolved_arm_plan_path,
        headroom_path=headroom_path,
        split_identity_hash=split_identity_hash,
        tables=tables,
        b2_verdict=b2_verdict,
        integrity=integrity,
    )


def _arm_aggregate_to_mapping(agg: object) -> Mapping[str, object]:
    return {"n_samples": agg.n_samples, "tool_selection_retention": agg.tool_accuracy}  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _loss_row_json(row: LossRow) -> dict[str, object]:
    return {"sample_id": row.sample_id, "a0_tool": row.a0_tool, "arm_tool": row.arm_tool, "class": row.klass}


def _arm_table_json(table: ArmLossTable) -> dict[str, object]:
    return {
        "arm": table.arm,
        "n_samples": table.n_samples,
        "n_losses": table.n_losses,
        "class_counts": dict(table.class_counts),
        "rows": [_loss_row_json(r) for r in table.rows],
    }


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def _reconciliation_json(row: ReconciliationRow) -> dict[str, object]:
    return {
        "arm": row.arm,
        "computed_loss_count": row.computed_loss_count,
        "parent_recomputed_loss_count": row.parent_recomputed_loss_count,
        "archived_loss_count": row.archived_loss_count,
        "matched": row.matched,
        "detail": row.detail,
    }


def report_to_json(report: LossDecompReport) -> dict[str, object]:
    verdict = report.b2_verdict
    integrity = report.integrity
    return {
        "schema": REPORT_SCHEMA,
        "s2_attempt_dir": str(report.s2_attempt_dir),
        "s2b_attempt_dir": str(report.s2b_attempt_dir),
        "s2c_attempt_dir": str(report.s2c_attempt_dir),
        "arm_plan_path": str(report.arm_plan_path),
        "headroom_path": str(report.headroom_path),
        "split_identity_hash": report.split_identity_hash,
        "tables": {arm: _arm_table_json(table) for arm, table in report.tables.items()},
        "b2_verdict": {
            "dragged_count": verdict.dragged_count,
            "total_losses": verdict.total_losses,
            "drag_confirmed_clause": _clause_json(verdict.drag_confirmed_clause),
            "drag_confirmed": verdict.drag_confirmed,
            "drift_confirmed_clause": _clause_json(verdict.drift_confirmed_clause),
            "drift_confirmed": verdict.drift_confirmed,
            "overall": verdict.overall,
            "b2_shape": dict(verdict.b2_shape),
            "n0r_reference_shape": dict(verdict.n0r_reference_shape),
        },
        "integrity": {
            "headroom_archive_verified_files": list(integrity.headroom_archive_verified_files),
            "flight_archive_verified": {k: list(v) for k, v in integrity.flight_archive_verified.items()},
            "read_archive_verified": {k: list(v) for k, v in integrity.read_archive_verified.items()},
            "unpinned_inputs": list(integrity.unpinned_inputs),
            "reconciliation": [_reconciliation_json(r) for r in integrity.reconciliation],
        },
    }


def render_report(report: LossDecompReport) -> str:
    verdict = report.b2_verdict
    integrity = report.integrity
    lines = [
        "P-A2T selection-loss decomposition -- registered model-free re-read "
        "(docs/readiness/2026-08-18-a2t-loss-decomp-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
        f"S2  attempt dir: {report.s2_attempt_dir}",
        f"S2b attempt dir: {report.s2b_attempt_dir}",
        f"S2c attempt dir: {report.s2c_attempt_dir}",
        f"arm plan (reused verbatim): {report.arm_plan_path}",
        f"headroom manifest: {report.headroom_path}",
        f"split identity hash: {report.split_identity_hash}",
        "",
        "Per-arm loss-class tables",
    ]
    header = (
        f"  {'arm':<6}{'n':>4}{'losses':>8}{'DRAGGED':>9}{'DRIFTED':>9}"
        f"{'MULTIPL':>9}{'EMPTY':>7}{'PARSE-FAIL':>12}"
    )
    lines.append(header)
    for arm in ALL_ARMS:
        table = report.tables[arm]
        c = table.class_counts
        lines.append(
            f"  {arm:<6}{table.n_samples:>4}{table.n_losses:>8}{c[DRAGGED_TO_SUPPLIED]:>9}"
            f"{c[DRIFTED_OTHER]:>9}{c[MULTIPLICITY]:>9}{c[EMPTY]:>7}{c[PARSE_FAIL]:>12}"
        )
    lines.append("")

    for arm in ALL_ARMS:
        table = report.tables[arm]
        lines.append(f"arm {arm} -- {table.n_losses} loss row(s):")
        for row in table.rows:
            lines.append(f"  {row.sample_id:<24} a0={row.a0_tool:<20} arm={row.arm_tool:<24} class={row.klass}")
        lines.append("")

    lines.append("B2 verdict (the verdict carrier)")
    lines.append(f"DRAG-CONFIRMED: {'MET' if verdict.drag_confirmed else 'not met'}")
    lines.append(f"  [{verdict.drag_confirmed_clause.verdict.upper():>8}] {verdict.drag_confirmed_clause.clause_text}")
    lines.append(f"           {verdict.drag_confirmed_clause.detail}")
    lines.append(f"DRIFT-CONFIRMED: {'MET' if verdict.drift_confirmed else 'not met'}")
    lines.append(f"  [{verdict.drift_confirmed_clause.verdict.upper():>8}] {verdict.drift_confirmed_clause.clause_text}")
    lines.append(f"           {verdict.drift_confirmed_clause.detail}")
    lines.append(f"B2 OVERALL: {verdict.overall}")
    lines.append("")
    lines.append("N0r reference shape side-by-side (note 2: reporting obligation, not a statistical test)")
    lines.append(f"  {'class':<20}{'B2 (n=21)':>12}{'N0r (n=40)':>12}")
    for klass in LOSS_CLASSES:
        lines.append(f"  {klass:<20}{verdict.b2_shape[klass]:>12}{verdict.n0r_reference_shape[klass]:>12}")
    lines.append("")

    lines.append("Integrity section")
    lines.append(f"headroom archive verified files: {len(integrity.headroom_archive_verified_files)}")
    for role, files in integrity.flight_archive_verified.items():
        lines.append(f"flight archive [{role}] verified files: {len(files)} (flight-receipt.json cross-checked)")
    for role, files in integrity.read_archive_verified.items():
        lines.append(f"read archive [{role}] verified files: {len(files)} (verdict.json in-place verified)")
    lines.append(f"unpinned inputs (never committed, by design): {', '.join(integrity.unpinned_inputs)}")
    lines.append("")
    lines.append("Three-way reconciliation (computed / parent-recomputed / archived-published)")
    for row in integrity.reconciliation:
        status = "OK" if row.matched else "MISMATCH"
        lines.append(f"  [{status:>8}] {row.arm}: {row.detail}")

    return "\n".join(lines)


def _write_manifest_sha256(output_dir: Path) -> None:
    """Mirrors this repository's own ``archive.sh`` generation convention
    (``sha256sum -b`` binary-mode format) -- computed over every file this
    CLI itself just wrote, excluding MANIFEST.sha256 itself."""

    output_dir = Path(output_dir)
    entries: list[str] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.sha256":
            continue
        rel = path.relative_to(output_dir).as_posix()
        entries.append(f"{_sha256_file(path)} *./{rel}")
    (output_dir / "MANIFEST.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8", newline="\n")


def _render_readme(report: LossDecompReport) -> str:
    verdict = report.b2_verdict
    lines = [
        "# P-A2T selection-loss decomposition -- registered model-free re-read",
        "",
        f"Schema: `{REPORT_SCHEMA}`. Registered design: "
        "`docs/readiness/2026-08-18-a2t-loss-decomp-preregistration-REGISTERED.md`. "
        "Exposure row: `SAEA-CHECK-a2t-loss-decomp`.",
        "",
        "Re-reads three ALREADY-CONSUMED attempts (Stage-2, Stage-2b, Stage-2c) with a NEW, "
        "narrower instrument (`analysis.a2t_loss_decomp` + this CLI) over the SAME archived "
        "`outputs.jsonl` files, hash-verified against their MANIFESTs before reading. The "
        "original one-shot reads remain consumed and their own verdicts untouched.",
        "",
        "## Attempt dirs",
        "",
        f"- S2:  `{report.s2_attempt_dir}`",
        f"- S2b: `{report.s2b_attempt_dir}`",
        f"- S2c: `{report.s2c_attempt_dir}`",
        f"- arm plan (reused verbatim): `{report.arm_plan_path}`",
        f"- split identity hash: `{report.split_identity_hash}`",
        "",
        "## B2 verdict",
        "",
        f"**{verdict.overall}** -- {verdict.dragged_count}/{verdict.total_losses} of B2's losses "
        "are DRAGGED-TO-SUPPLIED.",
        "",
        "## Files",
        "",
        "- `verdict.json` -- machine-readable report",
        "- `report.txt` -- human-rendered report (per-arm class tables, per-sample detail rows, "
        "the B2 verdict, the N0r reference shape, the integrity section)",
        "- `MANIFEST.sha256` -- hashes of every file in this directory",
    ]
    return "\n".join(lines) + "\n"


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="a2t-loss-decomp",
        description=(
            "P-A2T selection-loss decomposition pinned offline read suite: classifies every "
            "A0-correct-to-arm-incorrect loss across eight arms (N0r/S1p/S2/B1/B2/C1/C2/C3) into "
            "DRAGGED-TO-SUPPLIED/DRIFTED-OTHER/EMPTY/PARSE-FAIL and mechanically evaluates the "
            "B2 DRAG-CONFIRMED/DRIFT-CONFIRMED/MIXED verdict. Model-free, read-only; never opens "
            "a model session."
        ),
    )
    parser.add_argument("s2_attempt_dir", type=Path, help="Stage-2 (S1p/S2/S4/N0r) attempt directory")
    parser.add_argument("s2b_attempt_dir", type=Path, help="Stage-2b (B1/B2) attempt directory")
    parser.add_argument("s2c_attempt_dir", type=Path, help="Stage-2c (C1/C2/C3) attempt directory")
    parser.add_argument("--output-dir", required=True, type=Path, help="directory to write the report bundle to")
    parser.add_argument("--headroom-manifest", type=Path, default=None, help="override headroom.json's path")
    parser.add_argument("--arm-plan", type=Path, default=None, help="override the reused {RUN_ID}.arm-plan.json path")
    parser.add_argument("--headroom-archive", type=Path, default=None, help="override the A0-read archive dir")
    parser.add_argument("--s2-flight-archive", type=Path, default=None, help="override the Stage-2 flight archive dir")
    parser.add_argument("--s2b-flight-archive", type=Path, default=None, help="override the Stage-2b flight archive dir")
    parser.add_argument("--s2c-flight-archive", type=Path, default=None, help="override the Stage-2c flight archive dir")
    parser.add_argument("--s2-read-archive", type=Path, default=None, help="override the Stage-2 read archive dir")
    parser.add_argument("--s2b-read-archive", type=Path, default=None, help="override the Stage-2b read archive dir")
    parser.add_argument("--s2c-read-archive", type=Path, default=None, help="override the Stage-2c read archive dir")
    parser.add_argument("--split-role", default=DEFAULT_SPLIT_ROLE, help=f"default: {DEFAULT_SPLIT_ROLE!r}")
    parser.add_argument("--repo-root", type=Path, default=None, help="TEST-ONLY override of the study repo root")
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import REPO_ROOT, write_json_artifact

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    headroom_path = args.headroom_manifest or _default_archive_dir(repo_root, HEADROOM_ARCHIVE_DIRNAME) / "headroom.json"

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
        report = build_loss_decomp_report(
            args.s2_attempt_dir,
            args.s2b_attempt_dir,
            args.s2c_attempt_dir,
            lock,
            root,
            repo_root=repo_root,
            headroom_path=headroom_path,
            arm_plan_path=args.arm_plan,
            headroom_archive_dir=args.headroom_archive,
            s2_flight_archive_dir=args.s2_flight_archive,
            s2b_flight_archive_dir=args.s2b_flight_archive,
            s2c_flight_archive_dir=args.s2c_flight_archive,
            s2_read_archive_dir=args.s2_read_archive,
            s2b_read_archive_dir=args.s2b_read_archive,
            s2c_read_archive_dir=args.s2c_read_archive,
            split_role=args.split_role,
        )
    except (A2tLossDecompError, A2tS2ReadError, A2tS2bReadError, A2tS2cReadError) as error:
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
