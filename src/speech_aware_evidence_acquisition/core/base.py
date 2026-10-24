"""Foundation seams: ONE registry mechanism + shared value types (R0).

Anti-fragmentation contract (owner direction 2026-08-05): every pluggable
dimension of a Stage-2 experiment — carrier, evidence source, transport,
policy, scorer, knowledge builder/ranker/fuser, and external Agent
controller — registers here through the same Registry class. A new
experiment is config plus at most one newly registered component, never new
wiring.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, fields as dataclass_fields
from pathlib import Path
from typing import Mapping, Protocol, Sequence, runtime_checkable

from ..contracts import assert_information_boundary


class CoreError(RuntimeError):
    """A foundation seam refuses: unknown/duplicate registration or wiring misuse."""


class Registry:
    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._entries: dict[str, object] = {}

    def register(self, name: str, entry: object) -> object:
        if not isinstance(name, str) or not name.strip():
            raise CoreError(f"{self._kind} registry: blank name")
        if name in self._entries:
            raise CoreError(f"{self._kind} registry: duplicate name {name!r}")
        self._entries[name] = entry
        return entry

    def resolve(self, name: str) -> object:
        try:
            return self._entries[name]
        except KeyError:
            raise CoreError(
                f"unknown {self._kind} {name!r}; registered: {self.names()}"
            ) from None

    def names(self) -> list[str]:
        return sorted(self._entries)


CARRIERS = Registry("carrier")
TASK_ADAPTERS = Registry("task adapter")
EVIDENCE_SOURCES = Registry("evidence source")
TRANSPORTS = Registry("transport")
POLICIES = Registry("policy")
SCORERS = Registry("scorer")
# E22 cell (b), 2026-09-06: named PER-SAMPLE resolution rules for
# ``decoding_params.max_tokens``. A config fragment normally declares that key
# as a plain integer and every request of a cell carries the same one; a
# fragment may instead declare an OBJECT naming a policy registered here plus
# that policy's parameters, and ``core.flight.FlightRuntime`` resolves it to an
# integer per sample from the sample's own ``audio_seconds`` -- exactly where it
# already resolves the ``id_slot`` slot-affinity sentinel. Same one-Registry
# discipline as every other seam above, so the id resolves in a ``core.base``
# registry like every other config-declared component id and
# ``scripts/checks/engineering_base_check.py`` can read that resolution from
# source. The entries are populated from ``core/policies.py``.
MAX_TOKENS_POLICIES = Registry("max-tokens policy")
# P1 scaffold: named fills for the ONE supported task-instruction template
# placeholder ("{tool_schemas}" -- see core.instructions). A fill is a
# callable (lock, root) -> str rendering pinned carrier data (e.g. the
# Audio2Tool tools_registry.csv) into the frozen prompt template at run time,
# so registry-sized prompt material is never committed into a config
# fragment. Same one-Registry discipline as every other seam above.
INSTRUCTION_FILLS = Registry("instruction fill")
KNOWLEDGE_BUILDERS = Registry("knowledge builder")
KNOWLEDGE_RANKERS = Registry("knowledge ranker")
KNOWLEDGE_FUSERS = Registry("knowledge fuser")
AGENT_CONTROLLERS = Registry("Agent controller")
# E6 (2026-09-06): the one knowledge-provider registry. It used to live in
# ``rails.knowledge_provider`` as an admitted stopgap ("core.base should
# eventually host it alongside KNOWLEDGE_BUILDERS/RANKERS/FUSERS", that
# module's own docstring). It moves here because a baseline fragment's
# ``phase_supply.provider`` must RESOLVE IN A core.base REGISTRY like every
# other config-declared component id, and
# ``scripts/checks/engineering_base_check.py`` reads that resolution from
# source. ``rails.knowledge_provider.KNOWLEDGE_PROVIDERS`` is now a
# re-export of this object, so every existing caller is unaffected.
KNOWLEDGE_PROVIDERS = Registry("knowledge provider")
# Stage-3 iteration 3 (2026-09-24): named, config-pinned APPLICATION policies
# for a stage3-deltas context route -- the rule that decides, per ROW, whether
# a node takes the store's supply at all. ``KNOWLEDGE_PROVIDERS`` above answers
# "which values", this answers "on which rows", and the two are different
# questions, so a config must say which it declared. Same one-Registry
# discipline as every other seam here: a ``context_supply.<node>.scenario_gate
# .policy`` value must RESOLVE IN A core.base REGISTRY like every other
# config-declared component id, and ``scripts/checks/engineering_base_check.py``
# reads that resolution from source. An entry is a factory
# ``(**params) -> gate``; populated from ``rails/knowledge_provider.py``, the
# canonical registration site the delta providers themselves register from.
STAGE3_SUPPLY_GATE_POLICIES = Registry("stage3 supply gate policy")
# E1 (2026-09-05): named structured-response formats a phase program's
# config may bind to one phase. ``rails.controllers.PhaseSpec`` already
# declares a ``response_format_id`` per phase but nothing resolved it, so
# every phase schema had to be handed in by a launcher. An entry is a
# callable ``(lock, root, **params) -> Mapping`` that renders a
# response-format document from pinned carrier data at run time -- the same
# shape and the same reason as INSTRUCTION_FILLS above (a real schema over
# the 152-tool registry is far too large for a config fragment).
RESPONSE_FORMATS = Registry("response format")
ARTIFACT_CONTENT_VALIDATORS = Registry("artifact content validator")
# KC-E1f (2026-09-07): named, config-pinned rules that turn a RESPONSE into
# the text a run actually delivers. RESPONSE_FORMATS above renders a
# structured-decoding SCHEMA and constrains what the core may emit; this is
# the other side of the same seam -- what the harness does with what the core
# emitted -- and it exists because the KC-E1 verdict's named next step needs a
# delivery that can differ from a sealed predecessor by SUBSTITUTIONS ONLY,
# which is a property of an alignment rule and not of any JSON schema. An
# entry is a factory ``(**params) -> (predecessor_text, response_text) ->
# outcome``, the same shape ``rails.phase_material.PHASE_STATE_FILLS`` uses,
# so the parameters ride in the composed config hash and no launcher owns the
# rule. Populated from ``core/policies.py``, one of the canonical
# registration sites ``scripts/checks/engineering_base_check.py`` reads.
RESPONSE_POSTPROCESSORS = Registry("response postprocessor")
# WAVE R7 (owner Decision 12-F, 2026-09-08): named KNOWLEDGE VIEWS a phase
# program may apply to its own sealed answer. An entry is a pure
# ``(response_text) -> state_content`` function: what the phase SEALS as its
# ``rails.knowledge.AgentStateArtifact`` content, and therefore what the next
# phase reads. Absent -- every cell written before R7 -- the phase seals the
# raw response, byte-identically to before this registry existed.
#
# It exists because folding ``rails.a2t_hard_validity``'s retired repair
# controller onto ``rails.controllers.EvidenceAgentController`` had to keep the
# bytes the repair contact reads: that controller sealed a DERIVED state (a
# bounded, deterministic validity report over its own draft), not the draft. A
# view is the registered, hashable name for that derivation -- the same
# one-Registry discipline every other pluggable dimension above uses, and the
# reason the derivation is no longer a hard-coded branch inside a controller.
# Entries are populated from ``rails/controllers.py``.
PHASE_STATE_VIEWS = Registry("phase state view")
# A planner consumes typed criticism and returns a bounded continuation decision.
PHASE_PLANNERS = Registry("phase planner")
# Consumer-specific source-bound state views; no controller or knowledge acquisition.
ROLE_CONTEXT_COMPILERS = Registry("role context compiler")
# Native request projections are bounded, pure wire transformations applied
# only after the framework history has been validated. Config names the
# projection explicitly; absent means the historical request bytes.
NATIVE_EVIDENCE_PROJECTIONS = Registry("native evidence projection")
# E2 (2026-09-16, SLURP v2 base program M2, ``docs/superpowers/specs/
# 2026-09-16-slurp-v2-base-program-design.md`` section 4): named deterministic
# policies that aggregate the N raw structured answers of one grouped Solver
# visit (temperature > 0, distinct pinned seeds, every raw response kept in
# custody) into the ONE delivered answer. An entry is a pure callable
# ``(votes: Sequence[rails.commit_policies.SolverSampleVote], *, min_support,
# similarity_threshold) -> rails.commit_policies.CommitOutcome`` -- same
# one-Registry discipline as every other seam above, so
# ``native_episode.roles.solver.commit.policy`` resolves here exactly like
# every other config-declared component id. Populated from
# ``rails/commit_policies.py``, the canonical registration site.
COMMIT_POLICIES = Registry("commit policy")

# Decision 338 (2026-10-19, lever column L2): the Perception candidate-list MERGE
# policies. A ``native_episode.roles.perception.sampling_variants`` branch that
# declares ``perception_samples`` merges its k notes' candidate lists into the ONE
# shortlist its branch Solver contact reads. An entry is a pure callable
# ``(note_lists: Sequence[Sequence[str] | None], *, cap: int) ->
# rails.perception_merge_policies.MergeOutcome`` (``None`` marks a sample whose
# note carried no usable list). Same one-Registry discipline as
# :data:`COMMIT_POLICIES`; populated from ``rails/perception_merge_policies.py``.
PERCEPTION_MERGE_POLICIES = Registry("perception merge policy")


# ---------------------------------------------------------------------------
# Acquisition policies: the SIXTH node of the agent base (E18, 2026-09-19,
# owner decisions 43 and 44).
#
# The ``acquire`` primitive of the base-lock draft --
# ``(acquire_action, trajectory state) -> typed evidence bound into the
# successor state`` -- is the only primitive of that document MISSING on every
# carrier, and the one the research object names first (SUPPLY: "selection,
# amount, order and timing"). Owner decision 43 makes all six nodes mandatory
# per carrier and decision 44 rules that Acquisition is a component of
# everyday inference, not a research extra, so it is built now.
#
# An entry is one ``rails.acquisition.AcquisitionPolicy``: a frozen record
# carrying its own ``kind`` (one of ``rails.acquisition.ACQUISITION_KINDS``),
# its ``contacts_per_acquisition`` (0 for a model-free kind, 1 for a kind that
# spends a model contact) and its ``cost_unit``, callable as
# ``await policy(request) -> rails.acquisition.AcquiredEvidence``. Same
# one-Registry discipline as every other seam above, so
# ``native_episode.acquisition.policy`` resolves here exactly like every other
# config-declared component id. Populated from ``rails/acquisition.py``, the
# canonical registration site.
ACQUISITION_POLICIES = Registry("acquisition policy")


# ---------------------------------------------------------------------------
# E4, the core-native targeted re-listen (2026-09-28, owner decision 185).
#
# A post-accept, model-free-to-declare stage: one registered policy record
# carrying its own ``policy_id`` and the contact cost of ONE triggered slot
# (``rails.relisten.CONTACTS_PER_ENTITY``, both the blind and the forced-
# choice contact). Distinct from ``ACQUISITION_POLICIES`` above -- E4 is not
# one of E18's three acquisition kinds, it never routes through a Planner
# ACQUIRE, and it runs exactly once per row, after the answer is already
# accepted -- so its own registry is the one seam ``native_episode.relisten.
# policy`` resolves against, the same one-Registry discipline as every other
# seam here. Populated from ``rails/relisten.py``, the canonical
# registration site, exactly as the acquisition policies above are.
RELISTEN_POLICIES = Registry("relisten policy")


# ---------------------------------------------------------------------------
# The knowledge INDEX (item E21 -- the knowledge index, not the Earnings-21
# carrier -- 2026-09-19, owner decisions 48 and 50).
#
# An index is a stable, addressable, ordered catalogue of the task's knowledge
# space, rendered into the CONSTANT prefix of every request at a declared
# granularity, with short ids the model can cite. Three ids of it are
# component identities a config fragment names, so all three register here,
# beside every other config-declared component id:
#
# * ``KNOWLEDGE_INDEX_ORDERINGS`` -- an ORDERING is a pure, total
#   ``Sequence[IndexEntry] -> tuple[IndexEntry, ...]``. The order is declared,
#   never emergent, and it IS the degradation order, so a fragment naming an
#   unregistered ordering is refused before any contact (refusal 6 of the
#   design's section 6.4). Ordering is a mechanism with its own sign: the one
#   time this program re-rendered an unchanged registry under new headers
#   (Audio2Tool ORG-1) the official number fell 3.23 points, which is why the
#   rule is a registered object rather than a rendering convention.
# * ``KNOWLEDGE_INDEX_VIEWS`` -- a released, hash-pinned construction VIEW id
#   and the builder policy that produced it.
# * ``KNOWLEDGE_INDEX_RECEIPTS`` -- the per-row receipt schema id and the view
#   it belongs to, so a receipt reader resolves a block's schema the same way
#   every other component id resolves.
#
# Populated from ``rails/knowledge_index.py``, the canonical registration
# site, exactly as the acquisition and commit policies above are.
KNOWLEDGE_INDEX_ORDERINGS = Registry("knowledge index ordering")
KNOWLEDGE_INDEX_VIEWS = Registry("knowledge index view")
KNOWLEDGE_INDEX_RECEIPTS = Registry("knowledge index receipt")


# ---------------------------------------------------------------------------
# Stage-3 training-free RL algorithms (owner decision 101, 2026-09-22).
#
# "In the Stage-3 experiment set-up, different experiments must explicitly mark
# which training-free RL they use; you may explore several groups of
# training-free RL algorithms." An entry is one
# ``core.stage3_algorithms.Stage3Algorithm`` -- a frozen record carrying the
# algorithm's family, display name, citation, the loop OPERATORS it defines
# (rollout / scoring / credit assignment / update / selection / context
# application), its status and one sentence of what it changes. Same
# one-Registry discipline as every other seam above, so a Stage-3 experiment
# fragment's ``stage3_algorithm.id`` resolves here exactly like every other
# config-declared component id, and
# ``scripts/checks/stage3_algorithm_label_check.py`` refuses a Stage-3 cell
# whose label is absent, unregistered, or claims an operator its algorithm
# does not define. Populated from ``core/stage3_algorithms.py``, the canonical
# registration site.
STAGE3_ALGORITHMS = Registry("Stage-3 training-free RL algorithm")


# ---------------------------------------------------------------------------
# Judges: the Reviewer seat of the four-agent loop (owner Decision 11-B/11-C,
# 2026-09-08; ``docs/readiness/2026-09-08-openjiuwen-implementation-assessment
# -v1.md`` change #1, and the design note's section 2 Reviewer row).
#
# OWNER DECISION 11-C, stated once and enforced below rather than asked for:
# **the Reviewer is CRITICISM ONLY.** A judge SCORES and FLAGS; it never
# proposes a revision. Its whole output is a typed verdict -- a score, flags
# carrying span/field references, and reasons -- consumed by the Planner's
# loop decision and by the Solver's constrained revise. No judge may emit
# replacement text, and that is a property of the TYPE, not of a convention:
# :func:`assert_criticism_only` refuses a verdict type carrying any field that
# could hold text longer than one reason, and :meth:`JudgeVerdict.validate`
# caps every text field at :data:`MAX_JUDGE_TEXT_CHARS`. Answer authority
# stays with the frozen core (study CLAUDE.md research boundary); a judge that
# could hand back a rewritten answer would be a second answering LLM wearing a
# reviewer's name.
# ---------------------------------------------------------------------------


class JudgeError(CoreError):
    """A judge, a judge registration, or a judge verdict is malformed."""


#: Every severity a flag may declare, weakest first. ``block`` says the draft
#: violates a hard rule the harness itself can check; ``warn`` says the judge
#: suspects an error; ``info`` is bookkeeping a receipt may count. Severity
#: NEVER decides anything on its own -- the Planner's ``on_flag`` rule does
#: (``rails.phase_review``).
JUDGE_FLAG_SEVERITIES = ("info", "warn", "block")

#: The one length every piece of judge-authored text is capped at. A reason
#: is a sentence, not a rewrite: 240 characters cannot carry a replacement
#: transcript, a repaired tool call or a re-answered slot frame, which is
#: exactly the structural half of Decision 11-C.
MAX_JUDGE_TEXT_CHARS = 240

_JUDGE_SCALAR_ATOMS = frozenset({"str", "int", "float", "bool"})
_JUDGE_CONTAINER_ATOMS = frozenset({"tuple"})


def _split_top_level(text: str, separator: str) -> list[str]:
    """Split ``text`` on ``separator`` at bracket depth 0."""

    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for char in text:
        if char in "[(":
            depth += 1
        elif char in "])":
            depth -= 1
        if char == separator and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    parts.append("".join(current))
    return parts


def _annotation_atoms(annotation: str) -> set[str]:
    """Every type name mentioned by a dataclass field's SOURCE annotation.

    ``from __future__ import annotations`` is in force everywhere in this
    package, so ``dataclasses.fields(...)[i].type`` is the annotation's text.
    Reading the text rather than resolving the object is deliberate: the
    structural proof below must hold without importing anything a judge
    module might drag in, and it must refuse an annotation it cannot
    understand instead of silently passing it.
    """

    text = annotation.strip()
    if not text:
        return set()
    atoms: set[str] = set()
    for alternative in _split_top_level(text, "|"):
        alternative = alternative.strip()
        if not alternative or alternative == "None":
            continue
        if alternative.endswith("]") and "[" in alternative:
            outer = alternative[: alternative.index("[")].strip()
            inner = alternative[alternative.index("[") + 1 : -1]
            atoms.add(outer)
            for part in _split_top_level(inner, ","):
                part = part.strip()
                if part in ("", "..."):
                    continue
                atoms |= _annotation_atoms(part)
        else:
            atoms.add(alternative)
    return atoms


def assert_criticism_only(verdict_type: type, *, proven: Sequence[type] = ()) -> type:
    """Refuse a verdict type that could carry a proposed revision.

    The check is structural, over the type's own declared fields:

    * every field's annotation may mention only a scalar
      (:data:`_JUDGE_SCALAR_ATOMS`), ``tuple`` and its element types, or a
      type already PROVEN criticism-only by an earlier call (``proven``).
      An ``object``/``Mapping``/``Any`` field is refused outright, because a
      mapping can carry a whole rewritten answer under any key at all.
    * every field that can hold a ``str`` must be named in the type's own
      ``BOUNDED_TEXT_FIELDS``, and :meth:`JudgeVerdict.validate` caps each of
      those at :data:`MAX_JUDGE_TEXT_CHARS`.

    So a judge cannot return replacement text through ANY field, and adding
    such a field later fails this assertion at import time rather than
    reopening Decision 11-C by accident.
    """

    bounded = frozenset(getattr(verdict_type, "BOUNDED_TEXT_FIELDS", ()))
    proven_names = {kind.__name__ for kind in proven}
    for entry in dataclass_fields(verdict_type):
        atoms = _annotation_atoms(str(entry.type))
        unknown = sorted(
            atom
            for atom in atoms
            if atom not in _JUDGE_SCALAR_ATOMS
            and atom not in _JUDGE_CONTAINER_ATOMS
            and atom not in proven_names
        )
        if unknown:
            raise JudgeError(
                f"{verdict_type.__name__}.{entry.name} is annotated {entry.type!r}, "
                f"which names {unknown} -- a criticism-only verdict may carry only "
                f"{sorted(_JUDGE_SCALAR_ATOMS)}, tuples of those, and types already "
                "proven criticism-only; anything else could carry a proposed revision "
                "(owner Decision 11-C)"
            )
        if "str" in atoms and entry.name not in bounded:
            raise JudgeError(
                f"{verdict_type.__name__}.{entry.name} can carry text but is not "
                f"declared in {verdict_type.__name__}.BOUNDED_TEXT_FIELDS, so nothing "
                f"caps it at {MAX_JUDGE_TEXT_CHARS} characters; a judge scores and "
                "flags and never proposes a revision (owner Decision 11-C)"
            )
    return verdict_type


def _require_bounded_text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JudgeError(f"{field_name} must be non-empty text, got {value!r}")
    if len(value) > MAX_JUDGE_TEXT_CHARS:
        raise JudgeError(
            f"{field_name} is {len(value)} characters, over the "
            f"{MAX_JUDGE_TEXT_CHARS}-character cap; a judge writes a reason, never a "
            "replacement (owner Decision 11-C)"
        )
    return value


@dataclass(frozen=True)
class JudgeFlag:
    """One criticism, pointing at where in the draft it applies.

    ``code`` is the machine-readable flag name a Planner rule and a receipt
    both key on; ``reason`` is the human sentence. ``field_ref`` names a
    structured location inside the draft (``"entities[2].type"``,
    ``"intent.scenario"``) and ``span`` a half-open ``(start, end)`` WORD
    index pair over the draft's own whitespace tokens -- the same convention
    ``core.replay_signals.flag_spans`` and ``core.flag_sources`` already use.
    Both are references INTO the draft, never content: a flag says where to
    look, and the Solver decides what to do under the system's constraints.
    """

    BOUNDED_TEXT_FIELDS = ("code", "severity", "reason", "field_ref")

    code: str
    severity: str
    reason: str
    field_ref: str | None = None
    span: tuple[int, int] | None = None

    def validate(self) -> "JudgeFlag":
        _require_bounded_text(self.code, field_name="JudgeFlag.code")
        if self.severity not in JUDGE_FLAG_SEVERITIES:
            raise JudgeError(
                f"JudgeFlag.severity must be one of {list(JUDGE_FLAG_SEVERITIES)}, "
                f"got {self.severity!r}"
            )
        _require_bounded_text(self.reason, field_name="JudgeFlag.reason")
        if self.field_ref is not None:
            _require_bounded_text(self.field_ref, field_name="JudgeFlag.field_ref")
        if self.span is not None:
            if (
                not isinstance(self.span, tuple)
                or len(self.span) != 2
                or any(
                    isinstance(bound, bool) or not isinstance(bound, int)
                    for bound in self.span
                )
            ):
                raise JudgeError(
                    f"JudgeFlag.span must be a (start, end) int pair, got {self.span!r}"
                )
            start, end = self.span
            if start < 0 or end <= start:
                raise JudgeError(
                    f"JudgeFlag.span must be a non-empty half-open range, got {self.span!r}"
                )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "code": self.code,
            "severity": self.severity,
            "reason": self.reason,
            "field_ref": self.field_ref,
            "span": list(self.span) if self.span is not None else None,
        }


assert_criticism_only(JudgeFlag)


@dataclass(frozen=True)
class JudgeVerdict:
    """What one judge returns for one draft: a score, flags and reasons.

    ``score`` is optional and, when given, lies in ``[0.0, 1.0]`` with 1.0
    meaning "nothing to criticise" -- a judge that only flags returns
    ``None`` rather than inventing a number. ``flags`` is the payload the
    Planner's ``on_flag`` rule and the Solver's constrained revise both read.
    ``reasons`` carries whole-draft remarks that belong to no single span.

    Nothing here can hold a rewritten draft: see
    :func:`assert_criticism_only`, asserted on this type at import.
    """

    BOUNDED_TEXT_FIELDS = ("judge_id", "version", "reasons")

    judge_id: str
    version: str
    score: float | None = None
    flags: tuple[JudgeFlag, ...] = ()
    reasons: tuple[str, ...] = ()

    def validate(self) -> "JudgeVerdict":
        _require_bounded_text(self.judge_id, field_name="JudgeVerdict.judge_id")
        _require_bounded_text(self.version, field_name="JudgeVerdict.version")
        if self.score is not None:
            if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
                raise JudgeError(
                    f"JudgeVerdict.score must be a number or None, got {self.score!r}"
                )
            if not math.isfinite(float(self.score)) or not 0.0 <= float(self.score) <= 1.0:
                raise JudgeError(
                    f"JudgeVerdict.score must be a finite value in [0, 1], got "
                    f"{self.score!r}"
                )
        if not isinstance(self.flags, tuple):
            raise JudgeError("JudgeVerdict.flags must be a tuple of JudgeFlag")
        for flag in self.flags:
            if not isinstance(flag, JudgeFlag):
                raise JudgeError("JudgeVerdict.flags entries must be JudgeFlag")
            flag.validate()
        if not isinstance(self.reasons, tuple):
            raise JudgeError("JudgeVerdict.reasons must be a tuple of strings")
        for index, reason in enumerate(self.reasons):
            _require_bounded_text(reason, field_name=f"JudgeVerdict.reasons[{index}]")
        return self

    @property
    def flagged(self) -> bool:
        return bool(self.flags)

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "judge_id": self.judge_id,
            "version": self.version,
            "score": None if self.score is None else float(self.score),
            "flags": [flag.as_json() for flag in self.flags],
            "reasons": list(self.reasons),
        }


assert_criticism_only(JudgeVerdict, proven=(JudgeFlag,))


@runtime_checkable
class Judge(Protocol):
    """The Reviewer seat's one shape.

    ``id`` and ``version`` are receipt-able identity (the version is what a
    preregistration and an admission receipt quote). The call takes the
    DRAFT the Solver just produced, the phase MATERIAL the judge was given
    by config, and the row STATE, and returns one :class:`JudgeVerdict`.
    ``criticism_only`` is ``True`` for every registered judge and is checked
    at registration; the structural half of that promise lives in
    :func:`assert_criticism_only`.

    A judge is stateless and deterministic: the same three inputs must give
    the same verdict, in this process and in the next one.
    """

    id: str
    version: str
    criticism_only: bool

    def __call__(
        self,
        draft: str,
        material: Mapping[str, object],
        state: Mapping[str, object],
    ) -> JudgeVerdict: ...


def assert_judge(entry: object, *, name: str) -> object:
    """Refuse anything that is not a criticism-only, callable, identified judge."""

    if not callable(entry):
        raise JudgeError(f"judge {name!r} must be callable")
    for attribute in ("id", "version"):
        value = getattr(entry, attribute, None)
        _require_bounded_text(value, field_name=f"judge {name!r}.{attribute}")
    if getattr(entry, "id") != name:
        raise JudgeError(
            f"judge registered as {name!r} declares id {getattr(entry, 'id')!r}; the "
            "registry name and the judge's own id are one identity"
        )
    if getattr(entry, "criticism_only", None) is not True:
        raise JudgeError(
            f"judge {name!r} must declare criticism_only=True; a judge scores and "
            "flags and never proposes a revision (owner Decision 11-C)"
        )
    return entry


class JudgeRegistry(Registry):
    """The one registry whose entries are checked at registration time.

    Every other seam in this module registers whatever it is handed; a judge
    is different because Decision 11-C is a rule about what a registered
    entry may DO, and the cheapest place to hold that rule is the door.
    """

    def register(self, name: str, entry: object) -> object:
        assert_judge(entry, name=name)
        return super().register(name, entry)


#: The Reviewer's registry (owner Decision 11-B change #1). A ``judges`` list
#: in ``configs/`` -- today under a baseline fragment's ``phase_review``
#: block, parsed by ``rails.phase_review`` -- names ids that must resolve
#: here, exactly as ``policy`` / ``evidence_source`` / ``scorers`` resolve in
#: their own registries, and ``scripts/checks/engineering_base_check.py``
#: reads that resolution from source. Populated from ``core/policies.py``,
#: one of the canonical registration sites that check knows about.
JUDGES = JudgeRegistry("judge")


# ---------------------------------------------------------------------------
# Delivery normalisers: the DELIVERY-TIME node of the native episode (E11,
# 2026-09-18, owner directive 26 "analyses into nodes"; SLURP v2 base program
# module M3's runtime form).
#
# WHY THIS IS NOT A JUDGE. Owner Decision 11-C, enforced a few lines above,
# makes every ``core.base.JUDGES`` entry CRITICISM ONLY: a judge returns a
# :class:`JudgeVerdict` and may not emit replacement text, and
# :func:`assert_criticism_only` refuses a verdict type that could carry one.
# A delivery normaliser REWRITES the delivered answer, so registering it in
# JUDGES would either be refused at the door or would reopen 11-C by
# accident. It is instead the same seam :data:`COMMIT_POLICIES` is: a
# registered, deterministic, pure function whose output IS delivered bytes,
# resolved by id from one config key and re-derivable offline from custody.
#
# WHAT AN ENTRY IS. A callable ``(text: str) -> DeliveryNormalisation`` that
# is pure and deterministic (same text, same result, in this process and the
# next), makes no model, tool, network or corpus-gold lookup of the row it is
# rewriting, and declares three attributes: ``id`` (equal to its registry
# name), ``version`` (what a preregistration and an admission receipt quote)
# and ``carrier_lock_key`` (the ONE carrier whose answers it is defined for,
# checked fail-closed by ``rails.native_episode_config`` against the composed
# config, so a fragment can never arm a SLURP rule on an Earnings run).
# Populated from ``rails/delivery_normalisers.py``, the canonical
# registration site, exactly as COMMIT_POLICIES is populated from
# ``rails/commit_policies.py``.
# ---------------------------------------------------------------------------


class DeliveryNormaliserError(CoreError):
    """A delivery normaliser, its registration or its result is malformed."""


@dataclass(frozen=True)
class DeliveryNormalisation:
    """What one delivery normaliser returns for one delivered answer.

    ``text`` is always a value the caller may deliver: the rewritten answer
    when ``changed`` is true, and BYTE-IDENTICAL to the input otherwise.
    ``receipt`` is the custody record the episode seals beside the row
    (``native_episode_receipt.deliver_normaliser``); it carries the rule's
    identity and the input/output digests that let the bundle verifier
    re-derive the delivered bytes from the recorded model response, and it
    never carries the answer text itself -- a delivered SLURP answer holds
    slot fillers taken from speech, and a receipt is not a place to copy
    them.
    """

    text: str
    changed: bool
    receipt: Mapping[str, object]

    def validate(self) -> "DeliveryNormalisation":
        if not isinstance(self.text, str):
            raise DeliveryNormaliserError(
                "DeliveryNormalisation.text must be a string"
            )
        if not isinstance(self.changed, bool):
            raise DeliveryNormaliserError(
                "DeliveryNormalisation.changed must be a bool"
            )
        if not isinstance(self.receipt, Mapping) or not self.receipt:
            raise DeliveryNormaliserError(
                "DeliveryNormalisation.receipt must be a non-empty mapping"
            )
        return self


@runtime_checkable
class DeliveryNormaliser(Protocol):
    """The delivery node's one shape (module comment above)."""

    id: str
    version: str
    carrier_lock_key: str

    def __call__(self, text: str) -> DeliveryNormalisation: ...


def assert_delivery_normaliser(entry: object, *, name: str) -> object:
    """Refuse anything that is not a callable, identified, carrier-scoped
    delivery normaliser. Checked at REGISTRATION, for the same reason
    :class:`JudgeRegistry` checks its own door: the rule is about what a
    registered entry may do, and the door is the cheapest place to hold it.
    """

    if not callable(entry):
        raise DeliveryNormaliserError(f"delivery normaliser {name!r} must be callable")
    for attribute in ("id", "version", "carrier_lock_key"):
        value = getattr(entry, attribute, None)
        if not isinstance(value, str) or not value.strip():
            raise DeliveryNormaliserError(
                f"delivery normaliser {name!r}.{attribute} must be non-empty text, "
                f"got {value!r}"
            )
    if getattr(entry, "id") != name:
        raise DeliveryNormaliserError(
            f"delivery normaliser registered as {name!r} declares id "
            f"{getattr(entry, 'id')!r}; the registry name and the entry's own id "
            "are one identity"
        )
    return entry


class DeliveryNormaliserRegistry(Registry):
    """Checks its entries at registration (see :func:`assert_delivery_normaliser`)."""

    def register(self, name: str, entry: object) -> object:
        assert_delivery_normaliser(entry, name=name)
        return super().register(name, entry)


#: The delivery node's registry (E11). A
#: ``native_episode.deliver_normaliser.normaliser`` value in ``configs/``
#: resolves here exactly as ``native_episode.roles.solver.commit.policy``
#: resolves in :data:`COMMIT_POLICIES`. Populated from
#: ``rails/delivery_normalisers.py``.
DELIVERY_NORMALISERS = DeliveryNormaliserRegistry("delivery normaliser")


# ---------------------------------------------------------------------------
# Perception-branch PRESENTATIONS (same-flight instrument phase 2, merge set
# C, design docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-
# perception-variants-design.md section 3, "presentation"). A closed
# registry, mirroring :data:`DELIVERY_NORMALISERS`'s own door: an entry is
# checked at REGISTRATION, not at every resolve, and a
# ``native_episode.roles.perception.branches.branches[].presentation_id``
# value resolves here exactly as ``deliver_normaliser.normaliser`` resolves
# in :data:`DELIVERY_NORMALISERS`. Populated from
# ``rails/perception_presentations.py``.


@runtime_checkable
class PerceptionPresentation(Protocol):
    """One registered Perception-branch presentation renderer's shape."""

    id: str
    version: str

    def __call__(self, *args: object, **kwargs: object) -> object: ...


class PerceptionPresentationError(CoreError):
    """A registered Perception presentation renderer is invalid or misused."""


def assert_perception_presentation(entry: object, *, name: str) -> object:
    """Refuse anything that is not a callable, identified presentation.

    Checked at REGISTRATION, for the same reason
    :func:`assert_delivery_normaliser` checks its own door.
    """

    if not callable(entry):
        raise PerceptionPresentationError(
            f"perception presentation {name!r} must be callable"
        )
    for attribute in ("id", "version"):
        value = getattr(entry, attribute, None)
        if not isinstance(value, str) or not value.strip():
            raise PerceptionPresentationError(
                f"perception presentation {name!r}.{attribute} must be "
                f"non-empty text, got {value!r}"
            )
    if getattr(entry, "id") != name:
        raise PerceptionPresentationError(
            f"perception presentation registered as {name!r} declares id "
            f"{getattr(entry, 'id')!r}; the registry name and the entry's own "
            "id are one identity"
        )
    return entry


class PerceptionPresentationRegistry(Registry):
    """Checks its entries at registration (see :func:`assert_perception_presentation`)."""

    def register(self, name: str, entry: object) -> object:
        assert_perception_presentation(entry, name=name)
        return super().register(name, entry)


#: The Perception-branch presentation registry (phase 2, merge set C). A
#: ``presentation_id`` value declared on a Perception branch resolves here.
#: Populated from ``rails/perception_presentations.py``.
PERCEPTION_PRESENTATIONS = PerceptionPresentationRegistry("Perception branch presentation")


# ---------------------------------------------------------------------------
# Evidence-CONSUMPTION MODULES (owner decisions 195 and 196, design
# docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md
# section 2.1). A closed registry with the same door as
# :data:`PERCEPTION_PRESENTATIONS`: an entry is checked at REGISTRATION, and
# a ``native_episode.consumption_module.module_id`` value resolves here
# exactly as a ``presentation_id`` resolves in
# :data:`PERCEPTION_PRESENTATIONS`. Populated from
# ``rails/consumption_module.py``. An entry is a policy COMPILER, never a
# controller and never a model client: it turns a declared component list
# into the config blocks the one harness already reads.


@runtime_checkable
class ConsumptionModule(Protocol):
    """One registered evidence-consumption module's shape."""

    id: str
    version: str

    def __call__(self, *args: object, **kwargs: object) -> object: ...


class ConsumptionModuleError(CoreError):
    """A registered consumption module is invalid or misused."""


def assert_consumption_module(entry: object, *, name: str) -> object:
    """Refuse anything that is not a callable, identified module.

    Checked at REGISTRATION, for the same reason
    :func:`assert_perception_presentation` checks its own door.
    """

    if not callable(entry):
        raise ConsumptionModuleError(f"consumption module {name!r} must be callable")
    for attribute in ("id", "version"):
        value = getattr(entry, attribute, None)
        if not isinstance(value, str) or not value.strip():
            raise ConsumptionModuleError(
                f"consumption module {name!r}.{attribute} must be non-empty "
                f"text, got {value!r}"
            )
    if getattr(entry, "id") != name:
        raise ConsumptionModuleError(
            f"consumption module registered as {name!r} declares id "
            f"{getattr(entry, 'id')!r}; the registry name and the entry's own "
            "id are one identity"
        )
    return entry


class ConsumptionModuleRegistry(Registry):
    """Checks its entries at registration (see :func:`assert_consumption_module`)."""

    def register(self, name: str, entry: object) -> object:
        assert_consumption_module(entry, name=name)
        return super().register(name, entry)


#: The evidence-consumption module registry (owner decisions 195/196). A
#: ``native_episode.consumption_module.module_id`` value resolves here.
#: Populated from ``rails/consumption_module.py``.
CONSUMPTION_MODULES = ConsumptionModuleRegistry("evidence consumption module")

#: The module's carrier PROFILES (owner decision 196; design section 2b.1):
#: ``{profile: the carrier lock keys whose configs reach that profile's
#: hooks}``. A block's ``profile`` resolves to
#: ``rails/adapters/<profile>_module_hooks.py`` only when it is listed here,
#: and ``rails.consumption_module.carrier_hooks_for_lock_key`` maps a config's
#: ``carrier_lock_key`` to its profile through this table -- the module file
#: itself names no carrier. Earnings-22 exposes only a model-free direct layer.
#: A profile is library plumbing, not a measured own null, component admission
#: or experiment authorization (design section 2b.2).
CONSUMPTION_MODULE_PROFILES: Mapping[str, tuple[str, ...]] = {
    "slurp": ("slurp",),
    "audio2tool": ("audio2tool",),
    "earnings": ("earnings21-original",),
    "earnings22": ("earnings22-original",),
}


class RepairAlignmentError(CoreError):
    """A substitution-only delivery rule refuses.

    Raised for a caller's bad parameters and for a violated token-count
    invariant -- never for model output, which is always a named REFUSAL that
    delivers the predecessor verbatim (``core.repair_alignment``).
    """


_REQUIRED_PROVENANCE = ("lock_key", "relpath", "sha256")


class EvidenceError(RuntimeError):
    """An evidence item is malformed or an evidence source is unavailable."""


@dataclass(frozen=True)
class DerivedEvidenceRecord:
    """One evidence item's derivation chain (2026-08-09, ``docs/readiness/
    2026-08-09-conec-evidence-shape.md`` "Blocking gap"): the evidence-layer
    counterpart to ``core.model.slices.SliceRecord`` for runtime audio
    slices. ``core.driver.run_experiment`` used to bind evidence identity by
    hashing the carrier's RAW per-sample file and checking that hash against
    whatever content an evidence source actually returned -- correct for a
    verbatim passthrough (``conec-contexts``), but it fails closed on every
    source that TRANSFORMS that content (a capped bias list, reconstructed
    phrases, a carrier-independent distractor list, ...), because the
    transformed bytes never equal the raw file's D1-frozen hash.

    The fix extends the chain rather than weakening the rail (exactly the
    audio precedent): a transforming evidence source builds one of these
    records alongside its :class:`EvidenceItem`, naming the untransformed
    SOURCE it read, the PINNED transform (name+version) it applied, a hash of
    the params that governed the transform, and the resulting derived
    content's own hash. ``core.evidence_derivation.DerivedEvidenceRegistry``
    re-derives every one of those links independently before the content is
    trusted to reach a prompt -- see that module's docstring for the exact
    four conditions and which refusal names which broken link.

    ``carrier_bound`` (default ``True``): ``source_relpath``/``source_sha256``
    name a SINGLE per-sample carrier file (the SAME relative-path convention
    ``core.evidence.evidence_file_relpath`` already uses), whose identity the
    EXISTING, UNCHANGED D1 evidence rail
    (``contracts.gate_evidence_identity``) independently re-verifies via
    ``core.driver.run_experiment``'s ``binding.evidence_relpaths``/
    ``evidence_contents`` -- now scoped to the SOURCE bytes, never the
    derived ones. ``carrier_bound=False`` is the HONEST alternative for
    evidence built from files that carry no D1-recorded per-sample identity
    at all (e.g. the shared ``bias_lists/`` corpus): ``source_relpath``/
    ``source_sha256`` then name a COMBINED, canonically-ordered manifest of
    those files, identity rests SOLELY on this record's own re-derived chain
    (weaker than the D1-anchored case), and the record says so plainly
    instead of fabricating a per-sample carrier binding it cannot back up.
    """

    sample_id: str
    source_relpath: str
    source_sha256: str
    transform_name: str
    transform_version: str
    params_hash: str
    derived_sha256: str
    carrier_bound: bool = True

    def trace_view(self) -> dict[str, object]:
        """The record as a JSON-safe mapping for trace/derivation artifacts."""

        return {
            "sample_id": self.sample_id,
            "source_relpath": self.source_relpath,
            "source_sha256": self.source_sha256,
            "transform_name": self.transform_name,
            "transform_version": self.transform_version,
            "params_hash": self.params_hash,
            "derived_sha256": self.derived_sha256,
            "carrier_bound": self.carrier_bound,
        }


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source_uri: str
    content: str
    provenance: Mapping[str, str]
    # Derivation-chain rail (2026-08-09): optional, defaulted so every
    # pre-existing direct construction (this module's own "none" source, unit
    # tests building a bare EvidenceItem) is unaffected. A transforming
    # evidence source (core.evidence's conec-bias-list/distractor-only-
    # bias-list) sets both: `derivation` is the claim, `derivation_source_
    # bytes` is the untransformed source bytes the source function actually
    # read (kept OFF the runtime/provenance views below -- never crosses the
    # information boundary, it exists purely for
    # core.evidence_derivation.DerivedEvidenceRegistry to re-verify against,
    # zero extra I/O, mirroring verify_evidence_content_identity's own
    # "check the bytes already read" discipline).
    derivation: DerivedEvidenceRecord | None = None
    derivation_source_bytes: bytes | None = None

    def validate(self) -> "EvidenceItem":
        for label, value in (
            ("evidence_id", self.evidence_id),
            ("source_uri", self.source_uri),
            ("content", self.content),
        ):
            if not isinstance(value, str) or not value:
                raise EvidenceError(f"evidence {label} must be a non-empty string")
        if not isinstance(self.provenance, Mapping):
            raise EvidenceError("evidence provenance must be a mapping")
        missing = [key for key in _REQUIRED_PROVENANCE if key not in self.provenance]
        if missing:
            raise EvidenceError(f"evidence provenance lacks required keys {missing}")
        assert_information_boundary(self.runtime_view())
        assert_information_boundary(dict(self.provenance))
        return self

    def runtime_view(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "source_uri": self.source_uri,
            "content": self.content,
        }

    def provenance_view(self) -> dict[str, object]:
        return dict(self.provenance)


@dataclass(frozen=True)
class SampleOutcome:
    sample_id: str
    request_ids: tuple[str, ...]
    text: str
    admitted: bool
    request_sha256: str
    response_sha256: str
    # R0 repair T6 (I7): sha256 of ``text`` alone (UTF-8 bytes), independent of
    # ``response_sha256``'s raw-transport-bytes hash (whose exact bytes --
    # dict key order of a server-controlled ``usage`` mapping included -- are
    # not reproducible from ``text`` alone). This is the field
    # ``core.bundle.verify_bundle`` recomputes to catch an outputs row whose
    # ``text`` was mutated after the fact while ``response_sha256`` was left
    # untouched (see ``core.model.CoreResponse.response_text_sha256`` for
    # where it is first computed, at the one true model-request choke point).
    response_text_sha256: str
    # Per-slice decode-cap saturation (2026-08-09, continues the obs-loop
    # E-001 retry finding: ``reproduction.obs_loop.SLICE_RETRYABLE_EXCEPTIONS``
    # comment): the count of this sample's slice requests whose completion hit
    # the configured ``decoding_params.max_tokens`` cap (``reproduction.
    # obs_loop._slice_saturated`` / ``request_slice_with_retry``) -- a runaway
    # decode truncated by the cap, not a genuine transcript end. Default 0 for
    # the whole-file "fixed" policy, which sends one request per sample
    # through no slicing seam at all and therefore can never saturate a slice.
    saturated_slices: int = 0
    # Exhausted-slice skip count (Task 2, 2026-08-09, continues the obs-loop
    # E-001 retry finding: ``reproduction.obs_loop`` module comment above
    # ``SLICE_RETRYABLE_EXCEPTIONS``): the count of this sample's slice
    # requests that exhausted ``obs_slice_retry_max`` retries and were
    # skipped as an honest hole rather than aborting the whole run. Default
    # 0 for the same reason as ``saturated_slices`` above -- the whole-file
    # "fixed" policy has no slicing seam to skip a slice within.
    skipped_slices: int = 0


@dataclass(frozen=True)
class RunResult:
    run_id: str
    arm: str
    outputs_path: Path
    trace_manifest_hash: str
    cost: Mapping[str, object]


#: The one directory beneath ``SPEECHRL_DATA_DIR`` that derived media may live
#: in. Every media variant this study builds (silence-tail ``@ts2``, 16 kHz
#: input-rate, ESB utterance cuts) is written under ``<data_root>/derived/
#: <variant>/`` by its own build script, and its dataset fragment names that
#: same directory back. Nothing else is ever a legal derived media root.
DERIVED_MEDIA_PREFIX = "derived"

#: Dataset-fragment key -> the (path, sha256) key pair whose D1 media
#: supplement vouches for the media under that derived root. Each carrier
#: spells its own key (the SLURP runtime views, the Audio2Tool calibration
#: fragments and the Earnings-22 ESB fragments were each written before there
#: was a shared one), and each pairs with the supplement its media identity is
#: actually pinned by. A key not in this table is not a derived-root
#: declaration and contributes nothing.
DERIVED_MEDIA_SUBDIR_KEYS: Mapping[str, tuple[str, str]] = {
    "derived_media_subdir": ("d1_media_supplement", "d1_media_supplement_sha256"),
    "a2t_calibration_derived_subdir": (
        "a2t_calibration_d1_media_supplement",
        "a2t_calibration_d1_media_supplement_sha256",
    ),
    "e22_esb_derived_subdir": ("d1_media_supplement", "d1_media_supplement_sha256"),
}

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def _assert_d1_media_supplement(
    values: Mapping[str, object], subdir_key: str, path_key: str, digest_key: str
) -> None:
    """Refuse a declared derived media root whose fragment carries no
    hash-pinned D1 media supplement for it (fail-closed).

    A derived root widens what a payload may name. The ONLY thing that makes
    that widening safe is that every file under it is itself an identity the
    study froze: the fragment's D1 media supplement (schema
    ``saea-d1-media-supplement-v1``, verified byte-for-byte by
    ``contracts.gate_media_identity``) records the sample id, relpath, size and
    SHA-256 of each derived file. Without that pair there is nothing vouching
    for the root's contents, so the root is refused rather than trusted.
    Several fragments carry the supplement key as PROSE explaining why they
    need none (they declare no derived root either) -- requiring the paired
    lowercase 64-hex digest is what tells the two apart.
    """

    path_value = values.get(path_key)
    digest_value = values.get(digest_key)
    if path_value is None or digest_value is None:
        raise CoreError(
            f"dataset fragment declares {subdir_key!r} but no D1 media supplement "
            f"({path_key!r} + {digest_key!r}); a derived media root is legal only "
            "when a hash-pinned D1 supplement vouches for its contents"
        )
    if (
        not isinstance(path_value, str)
        or not path_value
        or any(character.isspace() for character in path_value)
        or "\\" in path_value
        or path_value.startswith("/")
        or any(part in ("", ".", "..") for part in path_value.split("/"))
    ):
        raise CoreError(
            f"dataset fragment {path_key!r} must be a relative POSIX path, got "
            f"{path_value!r}"
        )
    if not isinstance(digest_value, str) or _SHA256_HEX.fullmatch(digest_value) is None:
        raise CoreError(
            f"dataset fragment {digest_key!r} must be a lowercase 64-hex SHA-256, got "
            f"{digest_value!r}"
        )


def declared_derived_media_roots(
    values: Mapping[str, object], data_root: Path
) -> tuple[Path, ...]:
    """The additional legal media roots THIS composed dataset fragment declares.

    Reads only the keys in :data:`DERIVED_MEDIA_SUBDIR_KEYS`, in a fixed order,
    and returns them resolved beneath ``data_root``. A fragment that declares
    none returns ``()`` -- which is every fragment that existed before derived
    media did, so their bindings are byte-identical. Each declared value must
    be a relative POSIX path strictly beneath ``derived/`` and must come with
    the fragment's own hash-pinned D1 media supplement
    (:func:`_assert_d1_media_supplement`); anything else refuses here, before a
    binding is ever built, rather than widening confinement on trust.
    """

    roots: list[Path] = []
    seen: set[str] = set()
    for subdir_key, (path_key, digest_key) in DERIVED_MEDIA_SUBDIR_KEYS.items():
        declared = values.get(subdir_key)
        if declared is None:
            continue
        if not isinstance(declared, str) or not declared:
            raise CoreError(f"dataset fragment {subdir_key!r} must be a non-empty string")
        parts = declared.split("/")
        if (
            declared.startswith("/")
            or "\\" in declared
            or len(parts) < 2
            or parts[0] != DERIVED_MEDIA_PREFIX
            or any(part in ("", ".", "..") for part in parts)
        ):
            raise CoreError(
                f"dataset fragment {subdir_key!r} must be a relative POSIX path strictly "
                f"beneath {DERIVED_MEDIA_PREFIX!r}/, got {declared!r}"
            )
        _assert_d1_media_supplement(values, subdir_key, path_key, digest_key)
        if declared in seen:
            continue
        seen.add(declared)
        roots.append(Path(data_root) / declared)
    return tuple(roots)


@dataclass(frozen=True)
class PayloadBindingContext:
    """Immutable payload<->plan<->split binding facts (R0 repair T3, invariants I3/I4).

    Built by the driver from the T1 :class:`~.split_receipt.VerifiedSplit` (the
    frozen, live-recomputed sample id set actually authorized for this run) and
    the same carrier loader's per-sample facts, plus the controlled data root
    and the specific carrier's own subdirectory beneath it. This is the object
    a :class:`~.model.FrozenCoreAdapter` must be constructed with: a payload can
    name any sample id, carrier or path string it likes, but the adapter only
    ever trusts what this context says was actually loaded for this run.
    """

    carrier_lock_key: str
    allowed_sample_ids: frozenset[str]
    sample_facts: Mapping[str, tuple[float, int]]
    data_root: Path
    carrier_root: Path
    # I-4 (external-threat-model review): the same carrier loader's per-sample
    # media_relpath, keyed exactly like sample_facts. Optional/defaulted (not a
    # constructor-breaking addition) so every pre-existing caller in this
    # module's own test suite -- unit tests isolating I3 payload-binding or I4
    # path-confinement behavior, which never touch D1 identity at all -- keeps
    # working unchanged; the one true production call site
    # (core.driver.run_experiment) always supplies it, and
    # core.model.FrozenCoreAdapter only attempts the D1 media-identity check
    # (gate.verify_media_identity) when it is present and non-empty.
    media_relpaths: Mapping[str, str] = field(default_factory=dict)
    # IMPORTANT 1 (external-threat-model review round 4): the sample ids THIS
    # run's evidence source supplied non-empty evidence for, mapped to that
    # evidence file's path (core.evidence.evidence_file_relpath), so
    # core.model.FrozenCoreAdapter can ask the gate to re-verify it against
    # D1's frozen evidence-layer identity -- the evidence-layer counterpart to
    # media_relpaths above. Optional/defaulted (not every sample necessarily
    # carries evidence -- evidence_source "none" supplies an empty mapping)
    # and, unlike media_relpaths, deliberately NOT required to cover every
    # allowed_sample_id: only samples with actual evidence appear here.
    # 2026-09-06 (KC-E1): a sample may carry MORE THAN ONE evidence file. E5's
    # ``conec-class-lists`` returns two items per call -- the participant roster
    # (D1 layer ``e21_participant_names``) and the context document (D1 layer
    # ``e21_contexts``) -- and this field used to hold one relpath per sample, so
    # ``core.driver.run_experiment``'s per-item loop silently overwrote the first
    # with the second and only the LAST item's file was ever identity-checked.
    # The value is therefore ``str`` (one file, byte-identical to before) or an
    # ordered ``tuple[str, ...]`` (several, checked in order, each routed to its
    # own D1 layer).
    evidence_relpaths: Mapping[str, str | tuple[str, ...]] = field(default_factory=dict)
    # IMPROVEMENT (fifth external-threat-model review): the same sample ids as
    # evidence_relpaths, mapped instead to the exact UTF-8 bytes of the
    # evidence content this run's evidence source ALREADY READ into memory --
    # so core.model.FrozenCoreAdapter can ask the gate to bind the D1
    # evidence-identity check to the bytes actually consumed, never merely a
    # second read of the file at gate-check time (see
    # contracts.gate_evidence_identity's own module docstring for the
    # check<->send race this closes). Optional/defaulted like
    # evidence_relpaths, for the same reason: not every binding built in this
    # module's own test suite constructs a real evidence corpus.
    # Same one-or-many shape as ``evidence_relpaths`` above, and positionally
    # paired with it: ``evidence_contents[sid][i]`` is the content of
    # ``evidence_relpaths[sid][i]``.
    evidence_contents: Mapping[str, bytes | tuple[bytes, ...]] = field(default_factory=dict)
    # DERIVED-MEDIA CONFINEMENT (2026-09-07 defect: every cross-carrier
    # derived-media fragment was refused at payload time). A carrier whose
    # media lives under ``<data_root>/<carrier subdir>`` has exactly one legal
    # media root, and ``carrier_root`` is it. A DERIVED media variant of that
    # carrier -- the ``@ts2`` silence-tail populations, the 16 kHz input-rate
    # populations, the ESB utterance cuts -- lives instead under its own
    # hash-pinned ``<data_root>/derived/<variant>`` root, declared by the
    # dataset fragment itself (``derived_media_subdir`` /
    # ``a2t_calibration_derived_subdir`` / ``e22_esb_derived_subdir``, read by
    # :func:`declared_derived_media_roots`) and vouched for by that fragment's
    # own D1 media supplement. Those roots go HERE, and
    # ``core.model._enforce_payload_binding`` accepts a relpath confined under
    # the carrier root OR under one of them -- always AFTER the I4 exact
    # relpath check, never instead of it. A fragment that declares no such key
    # contributes nothing, so this tuple is empty for every binding that
    # existed before and their behaviour is byte-identical.
    derived_media_roots: tuple[Path, ...] = ()

    def validate(self) -> "PayloadBindingContext":
        """Structural self-check, no filesystem access: a malformed binding
        context (wrong shape, sample_facts that don't exactly cover
        allowed_sample_ids, a carrier_root outside data_root) refuses rather
        than silently under-checking payloads later."""

        if not isinstance(self.carrier_lock_key, str) or not self.carrier_lock_key.strip():
            raise CoreError("binding context carrier_lock_key must be a non-empty string")
        if not isinstance(self.allowed_sample_ids, frozenset) or not self.allowed_sample_ids:
            raise CoreError("binding context allowed_sample_ids must be a non-empty frozenset")
        if not all(
            isinstance(sample_id, str) and sample_id for sample_id in self.allowed_sample_ids
        ):
            raise CoreError("binding context allowed_sample_ids must contain non-empty strings")
        if not isinstance(self.sample_facts, Mapping) or set(self.sample_facts) != set(
            self.allowed_sample_ids
        ):
            raise CoreError(
                "binding context sample_facts keys must exactly match allowed_sample_ids"
            )
        for sample_id, fact in self.sample_facts.items():
            if not isinstance(fact, tuple) or len(fact) != 2:
                raise CoreError(
                    f"binding context sample_facts[{sample_id!r}] must be an "
                    "(audio_seconds, sample_rate_hz) tuple"
                )
            audio_seconds, sample_rate_hz = fact
            if (
                isinstance(audio_seconds, bool)
                or not isinstance(audio_seconds, (int, float))
                or not math.isfinite(audio_seconds)
                or audio_seconds <= 0
            ):
                raise CoreError(
                    f"binding context sample_facts[{sample_id!r}] audio_seconds must be "
                    "a finite positive number"
                )
            if (
                isinstance(sample_rate_hz, bool)
                or not isinstance(sample_rate_hz, int)
                or sample_rate_hz <= 0
            ):
                raise CoreError(
                    f"binding context sample_facts[{sample_id!r}] sample_rate_hz must be "
                    "a positive integer"
                )
        if not isinstance(self.data_root, Path) or not isinstance(self.carrier_root, Path):
            raise CoreError("binding context data_root/carrier_root must be Path objects")
        if not self.carrier_root.is_relative_to(self.data_root):
            raise CoreError("binding context carrier_root must be beneath data_root")
        # DERIVED-MEDIA CONFINEMENT (see the field's own docstring): the extra
        # legal roots are checked with exactly the discipline carrier_root gets
        # -- purely lexical, no filesystem access -- plus the two rules that
        # keep the widening narrow. A root outside data_root would let a
        # payload name bytes this run's controlled data tree does not even
        # contain; a root outside ``derived/`` (or ``derived/`` itself, which
        # would legalize EVERY variant at once rather than this fragment's own)
        # would re-open the confinement hole the whole check exists to close.
        if not isinstance(self.derived_media_roots, tuple):
            raise CoreError("binding context derived_media_roots must be a tuple")
        for derived_root in self.derived_media_roots:
            if not isinstance(derived_root, Path):
                raise CoreError(
                    "binding context derived_media_roots must contain Path objects, "
                    f"got {derived_root!r}"
                )
            if not derived_root.is_relative_to(self.data_root):
                raise CoreError(
                    f"binding context derived media root {str(derived_root)!r} must be "
                    "beneath data_root"
                )
            parts = derived_root.relative_to(self.data_root).parts
            if len(parts) < 2 or parts[0] != DERIVED_MEDIA_PREFIX:
                raise CoreError(
                    f"binding context derived media root {str(derived_root)!r} must be a "
                    f"named variant directory strictly beneath "
                    f"<data_root>/{DERIVED_MEDIA_PREFIX}/"
                )
        if not isinstance(self.media_relpaths, Mapping):
            raise CoreError("binding context media_relpaths must be a mapping")
        # I-4: optional (empty is allowed -- see the field's own docstring), but
        # if ANY entry is supplied it must exactly cover allowed_sample_ids: a
        # partial media_relpaths mapping would let some samples silently skip
        # the D1 media-identity check entirely.
        if self.media_relpaths and set(self.media_relpaths) != set(self.allowed_sample_ids):
            raise CoreError(
                "binding context media_relpaths keys must exactly match allowed_sample_ids "
                "when supplied"
            )
        for sample_id, relpath in self.media_relpaths.items():
            if not isinstance(relpath, str) or not relpath:
                raise CoreError(
                    f"binding context media_relpaths[{sample_id!r}] must be a non-empty string"
                )
        if not isinstance(self.evidence_relpaths, Mapping):
            raise CoreError("binding context evidence_relpaths must be a mapping")
        # IMPORTANT 1: unlike media_relpaths, evidence is legitimately sparse
        # (not every sample carries evidence -- evidence_source "none" yields
        # none at all), so only a SUBSET check applies: every key must still
        # name an actually-allowed sample id, never one outside this run's own
        # verified split.
        if not set(self.evidence_relpaths) <= set(self.allowed_sample_ids):
            raise CoreError(
                "binding context evidence_relpaths keys must be a subset of "
                "allowed_sample_ids"
            )
        for sample_id, relpath in self.evidence_relpaths.items():
            values = relpath if isinstance(relpath, tuple) else (relpath,)
            if not values or not all(
                isinstance(value, str) and value for value in values
            ):
                raise CoreError(
                    f"binding context evidence_relpaths[{sample_id!r}] must be a "
                    "non-empty string or a non-empty tuple of them"
                )
        if not isinstance(self.evidence_contents, Mapping):
            raise CoreError("binding context evidence_contents must be a mapping")
        # IMPROVEMENT: same sparse-subset discipline as evidence_relpaths above
        # -- not every allowed sample id necessarily carries evidence content.
        if not set(self.evidence_contents) <= set(self.allowed_sample_ids):
            raise CoreError(
                "binding context evidence_contents keys must be a subset of "
                "allowed_sample_ids"
            )
        for sample_id, content_bytes in self.evidence_contents.items():
            values = content_bytes if isinstance(content_bytes, tuple) else (content_bytes,)
            if not values or not all(
                isinstance(value, (bytes, bytearray)) and value for value in values
            ):
                raise CoreError(
                    f"binding context evidence_contents[{sample_id!r}] must be "
                    "non-empty bytes or a non-empty tuple of them"
                )
            paired = self.evidence_relpaths.get(sample_id)
            if paired is not None:
                relpaths = paired if isinstance(paired, tuple) else (paired,)
                if len(relpaths) != len(values):
                    raise CoreError(
                        f"binding context evidence_contents[{sample_id!r}] has "
                        f"{len(values)} entries but evidence_relpaths has "
                        f"{len(relpaths)}; the two are positionally paired"
                    )
        return self


@dataclass
class SampleContext:
    sample: object
    evidence: list[EvidenceItem]
    adapter: object
    sink: object
    arm: str
    task_instruction: str
    decoding_params: Mapping[str, object]
    request_id_base: str
    retrieval_query: str | None = None
    # Acoustic exemplar bank (core.exemplars module docstring, M-C-prime prep
    # infrastructure): None means the run never resolved an exemplar_manifest_id
    # at all (the pre-existing state, unaffected); a (possibly empty) sequence
    # means core.driver.run_experiment resolved this sample's own bank and a
    # policy MAY thread it into core.policies.build_arm_payload the same way
    # `evidence` already flows -- legal only for an arm whose D2-frozen field
    # set declares "exemplar_bank" ("exemplar-context" and
    # "fixed-legal-context-replay" do, e0.d2_leakage.ARM_VISIBLE_FIELDS).
    exemplar_bank: Sequence[Mapping[str, str]] | None = None
    extras: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Frozen-historical components (WAVE R7, owner Decision 12-F, 2026-09-08).
#
# The engineering-base ratchet's ``unregistered_config_values`` rule listed 36
# ``policy``/``evidence_source``/``controller_policy_id`` values that resolved
# in NO ``core.base`` registry. Every one of them belongs to an Audio2Tool
# AgentLoop cell that FLEW, sealed a receipt under ``docs/checks/`` and is
# cited by ``docs/exposure-ledger.md`` -- so the fragment carrying the name may
# not be rewritten or archived (study ``CLAUDE.md``: immutable records are
# superseded, never edited), and the name may not be pointed at some live
# function that never produced those bytes.
#
# A ``FrozenHistoricalComponent`` is the third answer. It RESOLVES, so the
# config value is a name the base knows and the gate can read from source; it
# carries the fragment and the sealed receipt that consumed it, so a reader of
# the registry is one hop from the bytes; and it REFUSES every use, so nothing
# can accidentally fly a retired probe launcher's id on the shared harness and
# claim it is the same cell. "Registered" here means "accounted for", never
# "runnable".
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrozenHistoricalComponent:
    """A config id that names a SEALED flight and no live implementation.

    Resolvable, never runnable. Any attempt to call it, or to read any
    attribute other than its own provenance fields, raises :class:`CoreError`
    naming the fragment and the sealed receipt instead.
    """

    component_id: str
    registry_kind: str
    fragment: str
    receipt: str
    note: str = ""

    def validate(self) -> "FrozenHistoricalComponent":
        for name in ("component_id", "registry_kind", "fragment", "receipt"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise CoreError(
                    f"FrozenHistoricalComponent.{name} must be non-empty text"
                )
        if not isinstance(self.note, str):
            raise CoreError("FrozenHistoricalComponent.note must be text")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "component_id": self.component_id,
            "registry_kind": self.registry_kind,
            "fragment": self.fragment,
            "receipt": self.receipt,
            "note": self.note,
            "runnable": False,
        }

    def _refuse(self, what: str) -> "CoreError":
        return CoreError(
            f"{self.registry_kind} {self.component_id!r} is FROZEN-HISTORICAL: it "
            f"names the sealed cell under {self.receipt} (declared by "
            f"{self.fragment}) and has no live implementation on today's "
            f"engineering base, so {what} is refused. Re-express the cell as a "
            "registered phase program if it must fly again; never resurrect the "
            "retired probe launcher."
        )

    def __call__(self, *args: object, **kwargs: object) -> object:
        raise self._refuse("calling it")

    def __getattr__(self, name: str) -> object:
        # Dunder/private lookups must keep raising AttributeError so copy,
        # pickle and dataclass machinery behave normally; a real component-like
        # attribute access is the misuse this type exists to catch.
        if name.startswith("_"):
            raise AttributeError(name)
        raise self._refuse(f"reading attribute {name!r}")
