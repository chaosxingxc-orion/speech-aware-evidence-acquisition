"""The judges that already existed, registered behind the ``Judge`` protocol.

Owner Decision 11-B change #2 (2026-09-08): this repository already carried
every deterministic check the design's judge table names -- but scattered
across ``SCORERS`` (post-hoc, explicitly forbidden inside the loop),
``RESPONSE_POSTPROCESSORS`` (one entry, plain-policy only) and plain functions
in ``core.flag_sources`` / ``core.replay_signals`` reachable only from
``reproduction.replay_loop``. There was no judge registry, so no cell could
declare one, and no receipt could quote one's version.

**No logic is added or changed here.** Every entry below is a thin adapter
over a FROZEN function that already ships, and the adapter does exactly three
things: call the frozen function, turn what it returns into a
``core.base.JudgeVerdict``, and carry a receipt-able ``version``. That is what
makes each judge's precision and recall measurable model-free on already
sealed outputs (design note section 4: "deterministic and tool judges first,
because their precision and recall can be measured model-free on sealed
outputs"), and it is why the wrapped functions are cited rather than copied.

Owner Decision 11-C, applied twice over
----------------------------------------

A judge SCORES and FLAGS; it never proposes a revision. Structurally that is
the verdict type's problem (``core.base.assert_criticism_only``), but two of
these adapters had to make a judgement call the type alone cannot make, and
both are recorded here rather than left to a reader:

* :class:`SlurpLegalLabelJudge` flags an illegal ``(scenario, action)`` pair
  and does **not** name the nearest legal pair, even though the frozen
  projection it sits beside computes exactly that. Naming it would be handing
  over the replacement.
* :class:`RosterBandJudge` flags a span that band-matches a roster candidate
  and does **not** name the candidate. The Solver gets the roster through its
  own traced knowledge supply; a judge that whispered the answer would be a
  second answering path wearing a reviewer's name.

Both are the conservative reading, and both keep the Reviewer's contribution
to "here, and why it looks wrong" -- which is precisely what the design's
selective re-listen and constrained revise consume.

What a judge is given
---------------------

``judge(draft, material, state)`` -- see ``rails.phase_review``. ``material``
is per-phase and per-judge (config ``params`` merged over injected carrier
material); ``state`` is per-row. Each judge below documents which keys it
reads and from which of the two, and fails closed with
``core.base.JudgeError`` when a key it cannot work without is missing -- a
judge that silently reported "nothing to criticise" because nobody wired its
signal would be worse than a loud stop on the first row.

Every judge is stateless, deterministic and model-free: no model call, no
network, no clock, no I/O. The heavy modules they wrap are imported inside
the call rather than at module scope, so importing ``core.policies`` (which
registers these) stays as light as it already was.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from .base import (
    MAX_JUDGE_TEXT_CHARS,
    JudgeError,
    JudgeFlag,
    JudgeVerdict,
)

#: Registered ids, as literals, so
#: ``scripts/checks/engineering_base_check.py`` can read the registered name
#: set out of ``core/policies.py`` without importing the package.
SLURP_LEGAL_LABEL_JUDGE_V1 = "slurp-legal-label-flag-v1"
SLURP_SLOT_SCHEMA_JUDGE_V1 = "slurp-slot-schema-conformance-v1"
EARNINGS_NUMERIC_FORMAT_JUDGE_V1 = "earnings-numeric-format-flag-v1"
E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1 = "e21-substitution-alignment-flag-v1"
REPLAY_LOGPROB_JUDGE_V1 = "replay-logprob-flag-v1"
ROSTER_BAND_JUDGE_V1 = "roster-band-flag-v1"
#: WAVE R7 (2026-09-08): the deterministic Audio2Tool hard-validity check,
#: which was a controller's private branch until the fold.
A2T_HARD_VALIDITY_JUDGE_V1 = "a2t-hard-validity-flag-v1"
E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1 = "e21-brief-name-near-miss-v1"
#: LP-2 (2026-09-09): the LABEL-TOKEN successor of the failed whole-answer
#: logprob flag. See :class:`SlurpIntentTokenLogprobJudge`.
SLURP_INTENT_TOKEN_LOGPROB_JUDGE_V1 = "slurp-intent-token-logprob-flag-v1"


def _lookup(
    key: str,
    material: Mapping[str, object],
    state: Mapping[str, object],
    *,
    judge_id: str,
    required: bool = True,
    default: object = None,
) -> object:
    """``state`` first, then ``material`` -- a per-row signal overrides a
    per-phase one, never the other way round."""

    if key in state:
        return state[key]
    if key in material:
        return material[key]
    if required:
        raise JudgeError(
            f"judge {judge_id!r} needs {key!r} in its per-row state or its per-phase "
            "material and was given neither; a judge that reported 'nothing to "
            "criticise' because its signal was never wired would be worse than this "
            "stop"
        )
    return default


def _clamped(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True)
class SlurpLegalLabelJudge:
    """FLAGS a SLURP intent label outside the closed legal space.

    Wraps, unchanged: ``reproduction.slurp_scoring.parse_slu_response`` (the
    fail-closed parser the official prediction file is built from) and
    ``reproduction.slurp_scoring.LegalIntentInventory`` (the 60 ``(scenario,
    action)`` pairs TRAIN carries).

    This is the JUDGE half of the legal-label rule and is deliberately
    distinct from ``slurp-legal-label-projection-v1``, the scoring-side
    POST-PROCESSOR that repairs the same defect: the projection maps an
    illegal pair onto the nearest legal one; this one says only that the pair
    is illegal, and never which pair is nearest (module docstring, Decision
    11-C).

    Reads ``inventory`` (a built ``LegalIntentInventory``) or
    ``actions_by_scenario`` (a ``{scenario: [action, ...]}`` mapping) from
    material or state. Flags: ``unparsed_response``, ``missing_label``,
    ``illegal_scenario``, ``illegal_action_for_scenario``. Score is 1.0 for a
    legal label and 0.0 otherwise.
    """

    id: str = SLURP_LEGAL_LABEL_JUDGE_V1
    version: str = "1.0.0"
    criticism_only: bool = True

    def __call__(
        self,
        draft: str,
        material: Mapping[str, object],
        state: Mapping[str, object],
    ) -> JudgeVerdict:
        from ..reproduction.slurp_scoring import (  # noqa: PLC0415 (import cost)
            legal_intent_inventory,
            parse_slu_response,
        )

        inventory = _lookup("inventory", material, state, judge_id=self.id, required=False)
        if inventory is None:
            pairing = _lookup("actions_by_scenario", material, state, judge_id=self.id)
            inventory = legal_intent_inventory(pairing)

        scenario, action, _entities, parsed = parse_slu_response(draft)
        if not parsed:
            return JudgeVerdict(
                judge_id=self.id,
                version=self.version,
                score=0.0,
                flags=(
                    JudgeFlag(
                        code="unparsed_response",
                        severity="block",
                        reason="the response is not a parseable SLU prediction object",
                        field_ref="$",
                    ),
                ),
            ).validate()
        if not scenario or not action:
            return JudgeVerdict(
                judge_id=self.id,
                version=self.version,
                score=0.0,
                flags=(
                    JudgeFlag(
                        code="missing_label",
                        severity="block",
                        reason="the parsed prediction names no scenario, no action, or neither",
                        field_ref="intent",
                    ),
                ),
            ).validate()
        if scenario not in inventory.scenarios:
            return JudgeVerdict(
                judge_id=self.id,
                version=self.version,
                score=0.0,
                flags=(
                    JudgeFlag(
                        code="illegal_scenario",
                        severity="block",
                        reason="the predicted scenario is outside the closed legal space",
                        field_ref="intent.scenario",
                    ),
                ),
            ).validate()
        if (scenario, action) not in inventory.pairs:
            return JudgeVerdict(
                judge_id=self.id,
                version=self.version,
                score=0.0,
                flags=(
                    JudgeFlag(
                        code="illegal_action_for_scenario",
                        severity="block",
                        reason=(
                            "the predicted action is not one this scenario carries in "
                            "the closed legal space"
                        ),
                        field_ref="intent.action",
                    ),
                ),
            ).validate()
        return JudgeVerdict(judge_id=self.id, version=self.version, score=1.0).validate()


@dataclass(frozen=True)
class SlurpSlotSchemaJudge:
    """FLAGS a SLURP slot frame that breaks its own schema block.

    The MF-9 schema judge, verbatim in definition (``docs/readiness/
    2026-09-08-mf9-slurp-slot-gap-audit-v1.md`` section 5.1): it fires on a
    row that is **unparsed**, that names **a type the row's own block did not
    list**, or that **repeats a type**. Measured there at 72.09 % precision
    over 86 of 1,000 rows -- the sharpest of the three judges that audit
    priced, and free.

    Wraps ``reproduction.slurp_scoring.parse_slu_response`` unchanged and adds
    no rule of its own. ``allowed_types`` is per ROW (the block is chosen by
    the row's own intent), so it is read from ``state`` first; a per-phase
    ``material`` fallback covers a cell whose whole roster shares one block.
    Score is the share of conforming mentions, 0.0 for an unparsed row.
    """

    id: str = SLURP_SLOT_SCHEMA_JUDGE_V1
    version: str = "1.0.0"
    criticism_only: bool = True

    def __call__(
        self,
        draft: str,
        material: Mapping[str, object],
        state: Mapping[str, object],
    ) -> JudgeVerdict:
        from ..reproduction.slurp_scoring import (  # noqa: PLC0415 (import cost)
            parse_slu_response,
        )

        allowed_raw = _lookup("allowed_types", material, state, judge_id=self.id)
        if isinstance(allowed_raw, (str, bytes)) or not isinstance(
            allowed_raw, (list, tuple, set, frozenset)
        ):
            raise JudgeError(
                f"judge {self.id!r}: 'allowed_types' must be a collection of entity "
                f"type names, got {type(allowed_raw).__name__}"
            )
        allowed = {str(entry) for entry in allowed_raw}

        _scenario, _action, entities, parsed = parse_slu_response(draft)
        if not parsed:
            return JudgeVerdict(
                judge_id=self.id,
                version=self.version,
                score=0.0,
                flags=(
                    JudgeFlag(
                        code="unparsed_response",
                        severity="block",
                        reason="the response is not a parseable SLU prediction object",
                        field_ref="$",
                    ),
                ),
            ).validate()

        flags: list[JudgeFlag] = []
        seen: set[str] = set()
        for index, entity in enumerate(entities):
            entity_type = str(entity.type)
            if entity_type not in allowed:
                flags.append(
                    JudgeFlag(
                        code="block_illegal_slot_type",
                        severity="block",
                        reason="this entity type is not listed in the row's own schema block",
                        field_ref=f"entities[{index}].type",
                    )
                )
            if entity_type in seen:
                flags.append(
                    JudgeFlag(
                        code="duplicate_slot_type",
                        severity="warn",
                        reason="this entity type already appears earlier in the frame",
                        field_ref=f"entities[{index}].type",
                    )
                )
            seen.add(entity_type)
        flagged = len({flag.field_ref for flag in flags})
        score = 1.0 if not entities else _clamped(1.0 - flagged / len(entities))
        return JudgeVerdict(
            judge_id=self.id,
            version=self.version,
            score=score,
            flags=tuple(flags),
        ).validate()


@dataclass(frozen=True)
class EarningsNumericFormatJudge:
    """FLAGS a malformed numeric surface in an Earnings transcript draft.

    The numeric-format check the Earnings agentic metrics already use,
    wrapped unchanged: ``reproduction.numeric_value_accuracy``'s
    ``whisper_words`` (the vendored Whisper ``EnglishTextNormalizer`` split),
    ``is_numeric_value`` ("a normalized word carrying at least one ASCII
    digit") and ``numeric_kind`` (the fixed-order currency / percent /
    ordinal / decimal / year / integer / other classification).

    The SCORER ``numeric-value-accuracy-v1`` compares the draft's numeric bag
    against a reference and is therefore post-hoc and gold-bound; a judge
    cannot see a reference, so this one asks the gold-free half of the same
    question: **is every digit-bearing token in the draft a well-formed
    figure at all.** A token classified ``other`` carries digits and fits no
    numeric shape the normalizer produces -- a "2q23", a "10k", a fused
    "1234.5.6" -- which is the numeric-format mismatch the design note names
    as an Earnings flag source. Score is the share of well-formed numeric
    tokens, 1.0 when the draft carries none.

    Reads nothing from material or state.
    """

    id: str = EARNINGS_NUMERIC_FORMAT_JUDGE_V1
    version: str = "1.0.0"
    criticism_only: bool = True

    def __call__(
        self,
        draft: str,
        material: Mapping[str, object],
        state: Mapping[str, object],
    ) -> JudgeVerdict:
        from ..reproduction.numeric_value_accuracy import (  # noqa: PLC0415 (import cost)
            is_numeric_value,
            numeric_kind,
            whisper_words,
        )

        words = whisper_words(draft)
        flags: list[JudgeFlag] = []
        numeric = 0
        for index, word in enumerate(words):
            if not is_numeric_value(word):
                continue
            numeric += 1
            if numeric_kind(word) == "other":
                flags.append(
                    JudgeFlag(
                        code="numeric_format_mismatch",
                        severity="warn",
                        reason=(
                            "this token carries digits but matches no well-formed "
                            "numeric shape after Whisper normalization"
                        ),
                        field_ref="transcript",
                        span=(index, index + 1),
                    )
                )
        score = 1.0 if not numeric else _clamped(1.0 - len(flags) / numeric)
        return JudgeVerdict(
            judge_id=self.id,
            version=self.version,
            score=score,
            flags=tuple(flags),
        ).validate()


@dataclass(frozen=True)
class SubstitutionAlignmentJudge:
    """FLAGS why a second-pass response could not be delivered as
    substitutions only.

    Wraps ``core.repair_alignment.accept_entity_repair`` unchanged and throws
    the delivered TEXT away. That is the whole point of the split: the
    registered POST-PROCESSOR ``e21-entity-repair-substitutions-v1`` exists to
    produce the delivery; this judge exists to say what the alignment refused
    and why, as flags a Planner and a receipt can count. Its refusal table
    (``core.repair_alignment.REFUSAL_REASONS``) and its rejected-opcode
    classes (``REJECTION_CLASSES``) become the flag codes verbatim, so a flag
    is traceable to the exact rule that raised it.

    Reads ``predecessor_text`` (the sealed pass-1 hypothesis) from state or
    material; ``max_span_tokens`` / ``min_anchor_ratio`` /
    ``max_substituted_fraction`` are optional config params that default to
    the module's own frozen defaults. Score is the alignment's anchor ratio.
    """

    id: str = E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1
    version: str = "1.0.0"
    criticism_only: bool = True

    def __call__(
        self,
        draft: str,
        material: Mapping[str, object],
        state: Mapping[str, object],
    ) -> JudgeVerdict:
        from .repair_alignment import (  # noqa: PLC0415 (import cost)
            DEFAULT_MAX_SPAN_TOKENS,
            DEFAULT_MAX_SUBSTITUTED_FRACTION,
            DEFAULT_MIN_ANCHOR_RATIO,
            accept_entity_repair,
        )

        predecessor = _lookup("predecessor_text", material, state, judge_id=self.id)
        if not isinstance(predecessor, str):
            raise JudgeError(
                f"judge {self.id!r}: 'predecessor_text' must be the sealed pass-1 "
                f"hypothesis text, got {type(predecessor).__name__}"
            )
        outcome = accept_entity_repair(
            predecessor,
            draft,
            max_span_tokens=int(material.get("max_span_tokens", DEFAULT_MAX_SPAN_TOKENS)),
            min_anchor_ratio=float(
                material.get("min_anchor_ratio", DEFAULT_MIN_ANCHOR_RATIO)
            ),
            max_substituted_fraction=float(
                material.get("max_substituted_fraction", DEFAULT_MAX_SUBSTITUTED_FRACTION)
            ),
        )
        flags: list[JudgeFlag] = []
        if outcome.refused:
            flags.append(
                JudgeFlag(
                    code=f"refused:{outcome.refusal_reason}",
                    severity="block",
                    reason=(
                        "the substitution-only alignment refused this response; the "
                        "predecessor stands unchanged"
                    ),
                    field_ref="transcript",
                )
            )
        for name, count in sorted(outcome.rejected.items()):
            if not count:
                continue
            flags.append(
                JudgeFlag(
                    code=f"rejected_{name}",
                    severity="warn",
                    reason=(
                        f"{int(count)} aligned edit(s) of class {name!r} could not be "
                        "delivered as a token-count-preserving substitution"
                    ),
                    field_ref="transcript",
                )
            )
        return JudgeVerdict(
            judge_id=self.id,
            version=self.version,
            score=_clamped(outcome.anchor_ratio),
            flags=tuple(flags),
        ).validate()


@dataclass(frozen=True)
class ReplayLogprobJudge:
    """FLAGS low-confidence decode spans from the sealed trace.

    Wraps ``core.replay_signals.flag_spans`` unchanged -- the same
    contiguous-run rule, the same half-open ascending-start span contract
    ``reproduction.replay_loop``'s SCORE stage already consumes. This is the
    "decode-confidence signals from the sealed trace" row of the design's
    judge table, moved from a policy-private function to a registered judge
    without touching the function.

    Reads ``word_scores`` (this row's per-word decode scores) from state or
    material, ``words`` optionally (defaulting to the draft's own whitespace
    split -- ``flag_spans`` requires the two to be the same length and refuses
    a mismatch), ``low_threshold`` (required) and ``min_run`` (default 1).
    Score is the share of words outside a flagged span.
    """

    id: str = REPLAY_LOGPROB_JUDGE_V1
    version: str = "1.0.0"
    criticism_only: bool = True

    def __call__(
        self,
        draft: str,
        material: Mapping[str, object],
        state: Mapping[str, object],
    ) -> JudgeVerdict:
        from .replay_signals import flag_spans  # noqa: PLC0415 (import cost)

        scores = _lookup("word_scores", material, state, judge_id=self.id)
        words = _lookup(
            "words", material, state, judge_id=self.id, required=False, default=None
        )
        if words is None:
            words = draft.split()
        if isinstance(scores, (str, bytes)) or not isinstance(scores, Sequence):
            raise JudgeError(
                f"judge {self.id!r}: 'word_scores' must be a sequence of per-word "
                f"decode scores, got {type(scores).__name__}"
            )
        threshold = _lookup("low_threshold", material, state, judge_id=self.id)
        min_run = int(
            _lookup(
                "min_run", material, state, judge_id=self.id, required=False, default=1
            )
        )
        spans = flag_spans(list(words), list(scores), float(threshold), min_run)
        flags = tuple(
            JudgeFlag(
                code="low_confidence_span",
                severity="warn",
                reason="every word in this span decoded below the configured floor",
                field_ref="transcript",
                span=(start, end),
            )
            for start, end in spans
        )
        flagged_words = sum(end - start for start, end in spans)
        total = len(list(words))
        score = 1.0 if not total else _clamped(1.0 - flagged_words / total)
        return JudgeVerdict(
            judge_id=self.id,
            version=self.version,
            score=score,
            flags=flags,
        ).validate()


@dataclass(frozen=True)
class RosterBandJudge:
    """FLAGS a draft span that band-matches a known roster/candidate name.

    Wraps ``core.flag_sources.roster_band_flags`` unchanged -- the same frozen
    weighted grapheme distance, the same ``[0.05, 0.45]`` band, the same
    df-rarity times name-likeness prior, the same greedy non-overlapping
    selection. This is the "brief-name near-miss detector" of the design's
    judge table, offline-validated at proper-name P@1 = 0.252 (``docs/
    readiness/2026-08-14-p1-ceiling-verdict.md``).

    **The flag names the span, never the candidate** (module docstring,
    Decision 11-C): the matched roster term is what a repair would substitute,
    and handing it over is proposing the revision. The Solver reads the roster
    through its own traced knowledge supply; the Observer re-listens to the
    span. What this judge contributes is where to look.

    Reads ``candidate_terms`` (required) from material or state, plus optional
    ``max_spans`` (default 4), ``min_score`` (default 0.0) and ``df`` (the
    whole-sample draft word-count table). Score is the share of words outside
    a flagged span.
    """

    id: str = ROSTER_BAND_JUDGE_V1
    version: str = "1.0.0"
    criticism_only: bool = True

    def __call__(
        self,
        draft: str,
        material: Mapping[str, object],
        state: Mapping[str, object],
    ) -> JudgeVerdict:
        from .flag_sources import roster_band_flags  # noqa: PLC0415 (import cost)

        terms = _lookup("candidate_terms", material, state, judge_id=self.id)
        if isinstance(terms, (str, bytes)) or not isinstance(terms, Sequence):
            raise JudgeError(
                f"judge {self.id!r}: 'candidate_terms' must be a sequence of candidate "
                f"terms, got {type(terms).__name__}"
            )
        words = _lookup(
            "words", material, state, judge_id=self.id, required=False, default=None
        )
        if words is None:
            words = draft.split()
        df = _lookup("df", material, state, judge_id=self.id, required=False, default=None)
        band = roster_band_flags(
            list(words),
            list(terms),
            int(material.get("max_spans", 4)),
            df=df,
            min_score=float(material.get("min_score", 0.0)),
        )
        flags = tuple(
            JudgeFlag(
                code="roster_band_near_miss",
                severity="warn",
                reason=(
                    "this span is a near-miss of a known candidate term at weighted "
                    f"grapheme distance {entry.distance:.3f}"
                ),
                field_ref="transcript",
                span=entry.span,
            )
            for entry in band
        )
        flagged_words = sum(end - start for (start, end) in (flag.span for flag in flags))
        total = len(list(words))
        score = 1.0 if not total else _clamped(1.0 - flagged_words / total)
        return JudgeVerdict(
            judge_id=self.id,
            version=self.version,
            score=score,
            flags=flags,
        ).validate()


@dataclass(frozen=True)
class A2tHardValidityJudge:
    """FLAGS the deterministic, deployment-visible invalidity of a tool-call
    draft.

    Wraps ``rails.a2t_hard_validity.validate_hard_validity`` unchanged. That
    function used to be reachable only from inside
    ``HardValidityRepairController``'s own ``advance`` -- it decided, in
    private, whether a second contact was spent -- and WAVE R7 folded that
    controller onto ``rails.controllers.EvidenceAgentController``. The
    sequencing became a phase program and the report became a registered
    knowledge view; this judge is the third piece: the same findings, declared,
    versioned and counted, on any cell that wants to SEE them without acting on
    them.

    Its own docstring already described a Reviewer: "only deterministic,
    deployment-visible validity checks ... deliberately excludes semantic
    confidence, reward, tier identity". Every
    ``HardValidityViolation.code`` becomes a flag code verbatim, at severity
    ``block`` -- a hard-invalid call cannot be dispatched at all, which is a
    different class of finding from a merely suspicious one. Score is 1.0 for a
    valid draft and 0.0 for a hard-invalid one; there is no middle, because the
    underlying rule has no middle.

    Reads ``registry_rows`` (the pinned public Audio2Tool tool registry) from
    material or state, and NOTHING else -- no gold, no expected call count, no
    tier. Decision 11-C holds by construction: a violation names the offending
    call index, tool name and argument key, and never the value that would fix
    them.
    """

    id: str = A2T_HARD_VALIDITY_JUDGE_V1
    version: str = "1.0.0"
    criticism_only: bool = True

    def __call__(
        self,
        draft: str,
        material: Mapping[str, object],
        state: Mapping[str, object],
    ) -> JudgeVerdict:
        from ..rails.a2t_hard_validity import (  # noqa: PLC0415 (import cost)
            validate_hard_validity,
        )

        rows = _lookup("registry_rows", material, state, judge_id=self.id)
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
            raise JudgeError(
                f"{self.id}: registry_rows must be a sequence of registry row "
                f"mappings, got {type(rows).__name__}"
            )
        report = validate_hard_validity(draft, tuple(rows))
        flags = tuple(
            JudgeFlag(
                code=violation.code,
                severity="block",
                reason=violation.message[:MAX_JUDGE_TEXT_CHARS],
                field_ref=_violation_field_ref(violation),
            )
            for violation in report.violations
        )
        return JudgeVerdict(
            judge_id=self.id,
            version=self.version,
            score=1.0 if report.status == "valid" else 0.0,
            flags=flags,
        ).validate()


def _violation_field_ref(violation: object) -> str | None:
    """``calls[i].arguments.key`` -- a LOCATION in the draft, never a value."""

    index = getattr(violation, "call_index", None)
    if index is None:
        return None
    ref = f"calls[{index}]"
    key = getattr(violation, "argument_key", None)
    if key:
        ref = f"{ref}.arguments.{key}"
    return ref[:MAX_JUDGE_TEXT_CHARS]


#: The near-miss judge's frozen band (:class:`BriefNameNearMissJudge`). A
#: distance of exactly 0 is the draft already carrying the brief's own form
#: -- correct, never a criticism -- and anything above the ceiling is a
#: different word rather than a corrupted one. The ceiling is a quarter of
#: the longer form under ``core.flag_sources``' own weighted cost table, so
#: "culp"/"calp" (0.125) is in and "culp"/"altec" is not.
BRIEF_NEAR_MISS_MAX_DISTANCE = 0.25

#: Draft words shorter than this never anchor a near-miss query -- the same
#: floor ``core.flag_sources.MIN_CANDIDATE_WORD_LENGTH`` puts on the
#: CANDIDATE side: at three characters a single substitution is already a
#: third of the form, so short words band-match everything.
BRIEF_NEAR_MISS_MIN_WORD_LENGTH = 3


@dataclass(frozen=True)
class BriefNameNearMissJudge:
    """FLAGS a draft span that is a NEAR MISS of a PERSON/ORG brief entry.

    The design note's "brief-name near-miss detector"
    (``docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md``
    section 2, judges table, "named, not built"), built for E21-LOOP-1 and
    deliberately NOT the same object as :class:`RosterBandJudge`:

    * its candidate set is the ConEC **pre-meeting brief's PERSON and ORG
      classes** -- the participant roster's own names and the organizations
      that roster labels -- not an arm's whole evidence candidate list;
    * it selects by DISTANCE alone inside a tight band ``(0,
      BRIEF_NEAR_MISS_MAX_DISTANCE]``, with no df-rarity weighting, no
      name-likeness prior and no ``max_spans`` truncation, so its flag count
      is a property of the draft and the brief rather than of a budget;
    * an EXACT match is never flagged. "Within a small edit distance of a
      brief entry **but not equal**" is the whole rule: a draft that already
      carries the brief's form is right, and criticising it would flag every
      correctly transcribed name in the call.

    The distance itself is not new logic: it is
    ``core.flag_sources.weighted_grapheme_distance``, the frozen weighted
    grapheme cost table (vowel/vowel 0.5, voiced-unvoiced pair 0.6, other
    substitution and indel 1.0, normalized by the longer form), and the
    candidate decomposition is that module's own
    :func:`~core.flag_sources.candidate_word_forms` /
    :func:`~core.flag_sources.candidate_bigram_forms`. One distance
    authority, two judges.

    **The flag names the span and the CLASS, never the entry** (Decision
    11-C, and the same reading :class:`RosterBandJudge` records): the brief
    entry a span nearly matches is exactly what a repair would substitute.
    The Solver reads the brief through its own traced knowledge supply and
    the Observer re-listens to the span; what this judge contributes is
    where to look and which kind of name to expect.

    Reads from material or state: ``person_terms`` and ``org_terms``
    (required sequences -- an absent one is a wiring defect, and a judge
    that silently reported "nothing to criticise" would be worse than a
    stop), plus optional ``words`` (defaulting to the draft's own whitespace
    split), ``max_distance`` (default
    :data:`BRIEF_NEAR_MISS_MAX_DISTANCE`) and ``min_word_length`` (default
    :data:`BRIEF_NEAR_MISS_MIN_WORD_LENGTH`). Score is the share of words
    outside a flagged span.
    """

    id: str = E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1
    version: str = "1.0.0"
    criticism_only: bool = True

    def __call__(
        self,
        draft: str,
        material: Mapping[str, object],
        state: Mapping[str, object],
    ) -> JudgeVerdict:
        from .flag_sources import (  # noqa: PLC0415 (import cost)
            STOPWORDS,
            candidate_bigram_forms,
            candidate_word_forms,
            weighted_grapheme_distance,
        )
        from .retrieval import normalize_term  # noqa: PLC0415 (import cost)

        classes: list[tuple[str, Sequence[object]]] = []
        for key, code in (("person_terms", "PERSON"), ("org_terms", "ORG")):
            terms = _lookup(key, material, state, judge_id=self.id)
            if isinstance(terms, (str, bytes)) or not isinstance(terms, Sequence):
                raise JudgeError(
                    f"judge {self.id!r}: {key!r} must be a sequence of brief entries, "
                    f"got {type(terms).__name__}"
                )
            classes.append((code, terms))

        words = _lookup(
            "words", material, state, judge_id=self.id, required=False, default=None
        )
        if words is None:
            words = draft.split()
        words = list(words)
        max_distance = float(
            _lookup(
                "max_distance",
                material,
                state,
                judge_id=self.id,
                required=False,
                default=BRIEF_NEAR_MISS_MAX_DISTANCE,
            )
        )
        min_word_length = int(
            _lookup(
                "min_word_length",
                material,
                state,
                judge_id=self.id,
                required=False,
                default=BRIEF_NEAR_MISS_MIN_WORD_LENGTH,
            )
        )
        if not 0.0 < max_distance <= 1.0:
            raise JudgeError(
                f"judge {self.id!r}: 'max_distance' must lie in (0, 1], got "
                f"{max_distance!r}"
            )
        if min_word_length < 1:
            raise JudgeError(
                f"judge {self.id!r}: 'min_word_length' must be >= 1, got "
                f"{min_word_length!r}"
            )

        unigram_targets: dict[str, str] = {}
        bigram_targets: dict[str, str] = {}
        for code, terms in classes:
            for term in terms:
                forms = candidate_word_forms(str(term))
                for form in forms:
                    unigram_targets.setdefault(form, code)
                for form in candidate_bigram_forms(forms):
                    bigram_targets.setdefault(form, code)

        normalized = [normalize_term(word) for word in words]

        def eligible(index: int) -> bool:
            form = normalized[index]
            return bool(form) and form not in STOPWORDS and len(form) >= min_word_length

        cache: dict[tuple[str, bool], tuple[str, float] | None] = {}

        def nearest(
            text: str, targets: Mapping[str, str]
        ) -> tuple[str, float] | None:
            best: tuple[str, float] | None = None
            length = len(text)
            for target, code in targets.items():
                if abs(len(target) - length) > max_distance * max(len(target), length):
                    continue
                distance = weighted_grapheme_distance(text, target)
                if distance <= 0.0 or distance > max_distance:
                    continue
                if (
                    best is None
                    or distance < best[1]
                    or (distance == best[1] and code < best[0])
                ):
                    best = (code, distance)
            return best

        def lookup(text: str, *, allow_bigram: bool) -> tuple[str, float] | None:
            key = (text, allow_bigram)
            if key not in cache:
                found = nearest(text, unigram_targets)
                if allow_bigram:
                    second = nearest(text, bigram_targets)
                    if second is not None and (found is None or second[1] < found[1]):
                        found = second
                cache[key] = found
            return cache[key]

        def exact(text: str, *, allow_bigram: bool) -> bool:
            """The draft span already IS a brief form -- correct, never a
            criticism, whatever else happens to sit near it."""

            if text in unigram_targets:
                return True
            return allow_bigram and text in bigram_targets

        found: list[tuple[float, int, int, str]] = []
        for index in range(len(words)):
            if not eligible(index):
                continue
            form = normalized[index]
            if not exact(form, allow_bigram=False):
                match = lookup(form, allow_bigram=False)
                if match is not None:
                    found.append((match[1], index, index + 1, match[0]))
            if index + 1 < len(words) and eligible(index + 1):
                window = f"{form} {normalized[index + 1]}"
                if not exact(window, allow_bigram=True):
                    match = lookup(window, allow_bigram=True)
                    if match is not None:
                        found.append((match[1], index, index + 2, match[0]))

        selected: list[tuple[float, int, int, str]] = []
        for entry in sorted(found, key=lambda item: (item[0], item[1], item[2])):
            if any(entry[1] < chosen[2] and chosen[1] < entry[2] for chosen in selected):
                continue
            selected.append(entry)
        selected.sort(key=lambda item: (item[1], item[2]))

        flags = tuple(
            JudgeFlag(
                code=f"brief_{code.lower()}_name_near_miss",
                severity="warn",
                reason=(
                    f"this span is within {distance:.3f} weighted grapheme distance "
                    f"of a {code} entry of this call's pre-meeting brief and is not "
                    "equal to it"
                ),
                field_ref="transcript",
                span=(start, end),
            )
            for distance, start, end, code in selected
        )
        flagged_words = sum(end - start for _d, start, end, _c in selected)
        total = len(words)
        score = 1.0 if not total else _clamped(1.0 - flagged_words / total)
        return JudgeVerdict(
            judge_id=self.id,
            version=self.version,
            score=score,
            flags=flags,
        ).validate()


#: The two label-token statistics this judge can turn on, each oriented so
#: that a LOWER value means LESS confident. Both are means/minima over the
#: tokens of the SCENARIO and ACTION values only -- the label the row is
#: scored on -- and neither can see a brace, a quote or an entity list.
SLURP_INTENT_LABEL_FIELDS = ("scenario", "action")
SLURP_INTENT_LOGPROB_STATISTICS = (
    "intent_mean_token_logprob",
    "intent_min_token_logprob",
)

#: The FROZEN thresholds, fixed from the sealed outputs of
#: ``SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1`` before this judge could be
#: read on anything, and quoted from the committed verdict receipt
#: ``docs/checks/speech-aware-evidence-acquisition/
#: 2026-09-09-slurp-logprob-judge-probe-v1/verdict/result-summary.json``
#: (field ``successor_diagnostic_NOT_PREREGISTERED.operating_points``). Each
#: is the value that flags exactly **86** of that arm's 1,000 rows -- the same
#: flag budget the failed probe's rule used, so the successor is read at the
#: predecessor's operating point rather than at a budget chosen to flatter it.
#:
#: These numbers were chosen AFTER the probe's data existed. That is why they
#: are frozen here as constants rather than recomputed per read, and why the
#: preregistration ``docs/readiness/
#: 2026-09-09-slurp-label-token-logprob-judge-lp2-v1-preregistration.md``
#: sends the DECISION to a fresh replicate read under this frozen rule.
SLURP_INTENT_MEAN_TOKEN_LOGPROB_FLOOR = -0.2675283079346116
SLURP_INTENT_MIN_TOKEN_LOGPROB_FLOOR = -0.5693119168281555

SLURP_INTENT_LOGPROB_FLOORS = {
    "intent_mean_token_logprob": SLURP_INTENT_MEAN_TOKEN_LOGPROB_FLOOR,
    "intent_min_token_logprob": SLURP_INTENT_MIN_TOKEN_LOGPROB_FLOOR,
}

#: The chosen statistic, named here rather than in a caller: the mean over the
#: label tokens. On the design read it reaches 75.58 % precision at 86 flags
#: against ``intent_min_token_logprob``'s 72.09 %, and AUROC 0.8497 against
#: 0.8446 -- and, unlike the minimum, it does not sit on the predecessor bar's
#: own value to three decimals.
SLURP_INTENT_LOGPROB_DEFAULT_STATISTIC = "intent_mean_token_logprob"


def _logprobs_object(value: object, *, judge_id: str) -> Mapping[str, object]:
    """The ``{"content": [...]}`` object, from any of the three shapes a
    caller can honestly be holding.

    A ``MODEL_LOGPROBS`` trace record is
    ``{"channel": ..., "payload": {"logprobs": {"content": [...]}, ...}}``,
    its payload is ``{"logprobs": {...}, "logprobs_sha256": ...}``, and the
    response envelope's own field is the innermost object. All three are
    accepted and unwrapped in that order; anything else is refused, because
    guessing at a fourth shape is how a judge ends up scoring the wrong row.
    """

    if not isinstance(value, Mapping):
        raise JudgeError(
            f"judge {judge_id!r}: 'logprobs' must be the row's MODEL_LOGPROBS record, "
            f"its payload, or the logprobs object itself, got {type(value).__name__}"
        )
    payload = value.get("payload")
    if isinstance(payload, Mapping) and "logprobs" in payload:
        value = payload
    inner = value.get("logprobs")
    if isinstance(inner, Mapping):
        value = inner
    if "content" not in value:
        raise JudgeError(
            f"judge {judge_id!r}: the logprobs object carries no 'content' list; the "
            "server returned no per-token distribution for this row"
        )
    return value


def _generated_tokens(
    logprobs: Mapping[str, object], *, judge_id: str
) -> list[tuple[str, float]]:
    """``[(token_text, logprob), ...]`` in generation order.

    llama-server's chat endpoint shape on the pinned build 04ccc72a
    (``tools/server/server-task.cpp:456-460``). Only GENERATED tokens appear;
    the prompt's tokens never carry probabilities on this build, which is why
    every statistic below is a statistic of the ANSWER.
    """

    content = logprobs.get("content")
    if not isinstance(content, list) or not content:
        raise JudgeError(
            f"judge {judge_id!r}: the logprobs object carries no non-empty 'content' "
            "list"
        )
    tokens: list[tuple[str, float]] = []
    for index, item in enumerate(content):
        if not isinstance(item, Mapping):
            raise JudgeError(
                f"judge {judge_id!r}: logprobs content[{index}] is not an object"
            )
        value = item.get("logprob")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise JudgeError(
                f"judge {judge_id!r}: logprobs content[{index}] carries no numeric "
                "logprob"
            )
        tokens.append((str(item.get("token", "")), float(value)))
    return tokens


def _json_string_value_span(text: str, key: str) -> tuple[int, int] | None:
    """Character span of the JSON string VALUE of ``key`` inside ``text``.

    A literal scan, not a JSON walk, and deliberately so: the statistic has to
    point at a region of the GENERATED TOKEN STREAM, and only the raw text
    preserves the offsets the stream is aligned to. Returns ``None`` when the
    key is absent or did not receive a quoted string value -- an answer this
    judge cannot locate a label in, which it says out loud rather than
    scoring.

    This is the same rule ``scripts/slurp_logprob_judge_read.py::_value_span``
    applied to the probe's sealed trace; the LP-2 design read asserts the two
    agree on all 1,000 sealed rows rather than trusting the restatement.
    """

    needle = f'"{key}"'
    at = text.find(needle)
    if at < 0:
        return None
    cursor = at + len(needle)
    while cursor < len(text) and text[cursor] in " \t\r\n":
        cursor += 1
    if cursor >= len(text) or text[cursor] != ":":
        return None
    cursor += 1
    while cursor < len(text) and text[cursor] in " \t\r\n":
        cursor += 1
    if cursor >= len(text) or text[cursor] != '"':
        return None
    start = cursor + 1
    end = start
    while end < len(text):
        if text[end] == "\\":
            end += 2
            continue
        if text[end] == '"':
            return (start, end)
        end += 1
    return None


@dataclass(frozen=True)
class SlurpIntentTokenLogprobJudge:
    """FLAGS a SLURP row whose own LABEL TOKENS decoded with low confidence.

    The preregistered successor of :class:`ReplayLogprobJudge`'s whole-answer
    reading, which was flown as ``SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1``
    and came back **NOT ADMITTED** (``docs/readiness/
    2026-09-09-slurp-logprob-judge-probe-v1-verdict.md``): the primary
    ``min_token_logprob`` reached AUROC 0.6935 and 51.16 % precision at 86
    flags, because **491 of that arm's 1,000 rows put their least-confident
    token on JSON punctuation** -- ``" []"`` alone on 208 -- so the statistic
    spent its ranking budget on the model's hesitation about how many entities
    to emit, which is a formatting decision.

    This judge asks the same question of a different region. It reconstructs
    the answer from the token stream itself, locates the ``scenario`` and
    ``action`` JSON string VALUES **in that reconstruction, by span, never by
    gold**, and takes a mean (or a minimum) over exactly the tokens that
    overlap them. A brace, a quote and an empty entity list cannot enter the
    statistic at all.

    **Criticism only** (owner Decision 11-C), and one degree stricter than the
    type requires: the flag names the ROW and the FIELD whose label token is
    least confident -- ``intent.scenario`` or ``intent.action`` -- and never a
    replacement label, never a nearest legal pair, and never one of the
    alternatives the ``top_logprobs`` list happens to carry. The alternatives
    are exactly what a repair would substitute; this judge reads their PARENT
    token's confidence and discards them.

    **The threshold is frozen, and it was chosen after the data existed.**
    :data:`SLURP_INTENT_LOGPROB_FLOORS` carries the value that flags 86 of the
    probe arm's 1,000 rows for each statistic, quoted from that flight's
    committed receipt. That provenance is the reason the LP-2 preregistration
    sends the DECISION to a fresh replicate of the same cell, read under this
    frozen rule, rather than to the sealed rows the threshold was read off.

    Reads from ``state`` first, then ``material``:

    * ``logprobs`` (required) -- the row's ``MODEL_LOGPROBS`` record, its
      payload, or the logprobs object itself (:func:`_logprobs_object`);
    * ``statistic`` (optional) -- one of
      :data:`SLURP_INTENT_LOGPROB_STATISTICS`, default
      :data:`SLURP_INTENT_LOGPROB_DEFAULT_STATISTIC`;
    * ``threshold`` (optional) -- default the frozen floor of the chosen
      statistic. A row is flagged when the statistic is **at or below** it:
      boundary ties are INCLUDED, because a threshold cannot split identical
      evidence, which is the same rule the probe's own flag budget used.

    Score is ``exp(statistic)`` -- the geometric-mean probability of the label
    tokens for the mean, the least confident label token's probability for the
    minimum. It is a real quantity in ``[0, 1]``, not a calibration this study
    has not earned, and 1.0 means "nothing to criticise" as the protocol says.
    """

    id: str = SLURP_INTENT_TOKEN_LOGPROB_JUDGE_V1
    version: str = "1.0.0"
    criticism_only: bool = True

    def statistics(
        self, draft: str, logprobs: Mapping[str, object]
    ) -> dict[str, object]:
        """Both label-token statistics for one row, and where they come from.

        Public because the model-free design read and the confirmation read
        measure precision and recall from exactly these numbers, and a second
        implementation of the alignment is exactly the drift the engineering
        base rule exists to forbid.
        """

        obj = _logprobs_object(logprobs, judge_id=self.id)
        tokens = _generated_tokens(obj, judge_id=self.id)
        text = "".join(token for token, _logprob in tokens)
        if not draft.startswith(text):
            raise JudgeError(
                f"judge {self.id!r}: the token stream rebuilds "
                f"{len(text)} characters that are not a prefix of the {len(draft)}-"
                "character draft, so every span statistic would be aligned to a "
                "different string than the one being judged"
            )

        offsets: list[tuple[int, int]] = []
        cursor = 0
        for token, _logprob in tokens:
            offsets.append((cursor, cursor + len(token)))
            cursor += len(token)

        located: dict[str, tuple[int, int]] = {}
        values: list[tuple[str, float]] = []
        for field in SLURP_INTENT_LABEL_FIELDS:
            span = _json_string_value_span(text, field)
            if span is None:
                continue
            located[field] = span
            low, high = span
            for (token, logprob), (start, end) in zip(tokens, offsets):
                if start < high and end > low:
                    values.append((field, logprob))

        if not values:
            return {
                "located_fields": tuple(sorted(located)),
                "label_token_count": 0,
                "intent_mean_token_logprob": None,
                "intent_min_token_logprob": None,
                "least_confident_field": None,
                "reconstructed_prefix_only": text != draft,
            }
        logprobs_only = [logprob for _field, logprob in values]
        least = min(values, key=lambda entry: (entry[1], entry[0]))
        return {
            "located_fields": tuple(sorted(located)),
            "label_token_count": len(values),
            "intent_mean_token_logprob": sum(logprobs_only) / len(logprobs_only),
            "intent_min_token_logprob": min(logprobs_only),
            "least_confident_field": least[0],
            "reconstructed_prefix_only": text != draft,
        }

    def __call__(
        self,
        draft: str,
        material: Mapping[str, object],
        state: Mapping[str, object],
    ) -> JudgeVerdict:
        statistic = str(
            _lookup(
                "statistic",
                material,
                state,
                judge_id=self.id,
                required=False,
                default=SLURP_INTENT_LOGPROB_DEFAULT_STATISTIC,
            )
        )
        if statistic not in SLURP_INTENT_LOGPROB_STATISTICS:
            raise JudgeError(
                f"judge {self.id!r}: 'statistic' must be one of "
                f"{list(SLURP_INTENT_LOGPROB_STATISTICS)}, got {statistic!r}"
            )
        threshold = float(
            _lookup(
                "threshold",
                material,
                state,
                judge_id=self.id,
                required=False,
                default=SLURP_INTENT_LOGPROB_FLOORS[statistic],
            )
        )
        if not math.isfinite(threshold) or threshold > 0.0:
            raise JudgeError(
                f"judge {self.id!r}: 'threshold' must be a finite logprob floor at or "
                f"below zero, got {threshold!r}"
            )

        measured = self.statistics(
            draft, _lookup("logprobs", material, state, judge_id=self.id)
        )
        value = measured[statistic]
        if value is None:
            # NOT "nothing to criticise": the token stream carries no locatable
            # scenario or action value at all, so the one thing this judge
            # measures is missing from the row it was pointed at. Saying so is
            # the module docstring's rule (a silent pass is worse than a loud
            # finding), and the code is distinct so a receipt can count the two
            # kinds of flag apart.
            return JudgeVerdict(
                judge_id=self.id,
                version=self.version,
                score=None,
                flags=(
                    JudgeFlag(
                        code="intent_label_tokens_not_located",
                        severity="warn",
                        reason=(
                            "the generated token stream carries no locatable scenario "
                            "or action string value, so its label confidence cannot be "
                            "measured"
                        ),
                        field_ref="intent",
                    ),
                ),
            ).validate()

        value = float(value)
        score = _clamped(math.exp(value))
        if value > threshold:
            return JudgeVerdict(
                judge_id=self.id, version=self.version, score=score
            ).validate()
        field = str(measured["least_confident_field"])
        return JudgeVerdict(
            judge_id=self.id,
            version=self.version,
            score=score,
            flags=(
                JudgeFlag(
                    code="low_intent_label_confidence",
                    severity="warn",
                    reason=(
                        f"the {int(measured['label_token_count'])} scenario/action "
                        f"label token(s) decoded at {statistic} {value:.4f}, at or "
                        f"below the frozen floor {threshold:.4f}"
                    ),
                    field_ref=f"intent.{field}",
                ),
            ),
        ).validate()


__all__ = [
    "A2T_HARD_VALIDITY_JUDGE_V1",
    "BRIEF_NEAR_MISS_MAX_DISTANCE",
    "BRIEF_NEAR_MISS_MIN_WORD_LENGTH",
    "EARNINGS_NUMERIC_FORMAT_JUDGE_V1",
    "E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1",
    "E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1",
    "REPLAY_LOGPROB_JUDGE_V1",
    "ROSTER_BAND_JUDGE_V1",
    "SLURP_LEGAL_LABEL_JUDGE_V1",
    "SLURP_SLOT_SCHEMA_JUDGE_V1",
    "A2tHardValidityJudge",
    "BriefNameNearMissJudge",
    "EarningsNumericFormatJudge",
    "ReplayLogprobJudge",
    "RosterBandJudge",
    "SlurpLegalLabelJudge",
    "SlurpSlotSchemaJudge",
    "SubstitutionAlignmentJudge",
]
