"""Task-independent contracts for knowledge BUILD, USE, and optimization.

This module is the strict seam between two processes that earlier probes
accidentally mixed together:

* BUILD consumes only a TRAIN partition and freezes a content-addressed
  :class:`KnowledgeSnapshot`.
* USE consumes that frozen snapshot from a disjoint DEV query partition.
  Every :class:`QueryState` keeps the original speech-feature packet bound;
  agent state and previously retrieved values are auxiliary references, never
  a replacement text-only query. Since 2026-09-08 the packet may ADVANCE
  within a trajectory, but only to a :class:`SpeechPacketDerivation` of the
  packet the trajectory started from -- a re-cut span, an enhanced copy, or a
  re-encoded unit of the SAME media. The rule that motivated the freeze is
  untouched: the query is still this sample's own speech, never agent text,
  and never audio the original media does not contain.

The contracts deliberately do not prescribe one task, one label vocabulary,
or one retrieval implementation.  A key is a collection of independently
rankable facets (content, speaker, entity, domain, operation, or a task-defined
dimension); a value carries sample-associated evidence and optional prior/task
metadata; ranking and fusion remain separately hash-bound decisions.

No model or filesystem access occurs here.  Existing drivers can adopt these
contracts incrementally while their historical receipts remain readable.
"""

from __future__ import annotations

import math
import re
import warnings
from dataclasses import dataclass
from typing import Mapping, Sequence

from .errors import RailsError
from .hashing import content_hash

KNOWLEDGE_SNAPSHOT_VERSION = "knowledge-snapshot-v1"
QUERY_STATE_VERSION = "knowledge-query-state-v1"
RANK_RESULT_VERSION = "knowledge-rank-result-v1"
FUSION_DECISION_VERSION = "knowledge-fusion-decision-v1"
AGENT_STEP_TRANSITION_VERSION = "knowledge-agent-step-transition-v1"
AGENT_STATE_ARTIFACT_VERSION = "knowledge-agent-state-artifact-v1"
SPEECH_PACKET_DERIVATION_VERSION = "knowledge-speech-packet-derivation-v1"

AGENT_ACTION_KINDS = frozenset(
    {
        "stop",
        "organize",
        "acquire",
        "expand",
        "contrast",
        "verify",
        "backtrack",
        # OBS, not SUPPLY: the trajectory keeps listening to the SAME parent
        # media through a registered derivation of its original speech packet
        # (see :class:`SpeechPacketDerivation`). A relisten carries no
        # knowledge delta at all -- it moves the observation and nothing else.
        "relisten",
    }
)
_SUPPLY_ACTION_KINDS = frozenset({"acquire", "expand", "contrast"})

# The closed list of ways a successor speech packet may differ from the
# trajectory's original one. Every entry names a transform of the SAME parent
# media that adds no new content: a narrower span of it, a pinned enhancement
# of it, or the same span re-encoded. Anything that would introduce audio the
# original media does not contain has no entry here and can therefore never be
# spelled on a transition.
SPEECH_PACKET_DERIVATION_KINDS = frozenset(
    {
        "recut-span",  # a re-cut span of the same media (selective re-listen)
        "enhanced-copy",  # a pinned frozen enhancer applied to the same media
        "reencoded-unit",  # the same audio re-encoded (rate, unit boundaries)
    }
)

TRAIN_PARTITION_ROLE = "train"
EXTERNAL_GOVERNED_PARTITION_ROLE = "external-governed"
DEV_PARTITION_ROLE = "dev"

# BUILD-eligible source roles: task TRAIN samples, or governed external
# documents (e.g. ConEC context docs) that are not task train samples but are
# still frozen, provenance-tracked, and disjoint from DEV/TEST query rosters.
_SOURCE_PARTITION_ROLES = frozenset(
    {TRAIN_PARTITION_ROLE, EXTERNAL_GOVERNED_PARTITION_ROLE}
)

_SHA256_HEX = re.compile(r"[0-9a-f]{64}")

# ---------------------------------------------------------------------------
# The ``prior_score`` range contract
# ---------------------------------------------------------------------------
#
# ``ValueBundle.prior_score`` models a train-derived PRIOR: the probability of
# the value's own label given the conditioning event its builder chose. A
# probability lives in [0, 1]. Until 2026-08-25 that range was nowhere
# declared, and the omission had a measured cost: two independent builders
# wrote the SAME wrong ratio -- a numerator counted over the whole
# construction pool divided by a denominator counted over one conditioning
# cell -- and nothing refused it. On Audio2Tool the supremum reached 4.1, with
# 193 of 12,601 values above 1, which then monopolised the ranker's admission
# window. See ``docs/readiness/2026-08-25-prior-score-semantics-repair.md``.
#
# THE RANGE IS A CONTRACT, NEVER A KNOB. It is not configurable, not widened
# per carrier, and not softened by a tolerance: a number outside [0, 1] is not
# a probability, and calling it one is the defect.
PRIOR_SCORE_MIN = 0.0
PRIOR_SCORE_MAX = 1.0


def prior_score_range_violation(prior_score: object) -> float | None:
    """The out-of-range ``prior_score``, or ``None`` when it respects the range.

    Pure and total: it classifies, it never raises and it never mutates. The
    two sides of the contract -- fail-closed refusal at construction,
    explicit recording at historical load -- are both expressed in terms of
    this one predicate, so they can never drift apart. ``None`` and
    non-numeric inputs are not this function's business (``ValueBundle.validate``
    already refuses a non-finite ``prior_score``); they classify as no
    violation."""

    if prior_score is None or isinstance(prior_score, bool):
        return None
    if not isinstance(prior_score, (int, float)):
        return None
    value = float(prior_score)
    if not math.isfinite(value):
        return None
    if PRIOR_SCORE_MIN <= value <= PRIOR_SCORE_MAX:
        return None
    return value


def assert_prior_scores_are_probabilities(
    values: "Sequence[ValueBundle]", *, builder: str
) -> None:
    """FAIL-CLOSED, CONSTRUCTION SIDE. Refuse a value set carrying a
    non-probability ``prior_score``.

    This is the gate every NEW snapshot passes: both knowledge builders call
    it on the values they just assembled, and
    :meth:`KnowledgeSnapshot.frozen_json` calls it again at the exact moment a
    snapshot becomes durable bytes. It raises rather than reporting, because a
    builder that emits a non-probability has computed the wrong quantity and
    every downstream ranking statement made from it is unsound.

    It is deliberately NOT called from :meth:`ValueBundle.validate`. See
    :meth:`KnowledgeSnapshot.from_frozen_json` for the other side of the
    boundary and why it has to be somewhere else."""

    offenders = [
        (value.value_id, violation)
        for value in values
        if (violation := prior_score_range_violation(value.prior_score)) is not None
    ]
    if not offenders:
        return
    preview = ", ".join(
        f"{value_id}={score!r}" for value_id, score in sorted(offenders)[:5]
    )
    raise RailsError(
        f"{builder}: prior_score must be a probability in "
        f"[{PRIOR_SCORE_MIN}, {PRIOR_SCORE_MAX}] -- {len(offenders)} of "
        f"{len(values)} values are outside it ({preview}"
        + (f", +{len(offenders) - 5} more" if len(offenders) > 5 else "")
        + "). A ratio whose numerator is not restricted to its denominator's "
        "conditioning event is not a conditional probability; restrict the "
        "numerator rather than rescaling the result."
    )


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RailsError(f"{field} must be a non-empty string")
    return value


def _require_sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _SHA256_HEX.fullmatch(value) is None:
        raise RailsError(f"{field} must be a 64-hex SHA-256")
    return value


def _require_unique_texts(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise RailsError(f"{field} must be a tuple")
    if len(set(values)) != len(values):
        raise RailsError(f"{field} must contain unique values")
    for value in values:
        _require_text(value, field=f"{field} entry")
    return values


@dataclass(frozen=True)
class KeyFacet:
    """One independently matchable dimension of a knowledge key.

    ``representation_kind`` is open rather than enum-closed so text remains
    the maintainable default while bounded speech/hybrid controls stay
    representable without changing this task-independent contract.
    ``representation`` is either the English key material itself or a stable
    content-addressed reference, as declared by ``representation_kind``.
    """

    facet_id: str
    dimension: str
    representation_kind: str
    representation: str
    source_sample_ids: tuple[str, ...]
    parent_facet_ids: tuple[str, ...] = ()

    def validate(self) -> "KeyFacet":
        _require_text(self.facet_id, field="KeyFacet.facet_id")
        _require_text(self.dimension, field="KeyFacet.dimension")
        _require_text(self.representation_kind, field="KeyFacet.representation_kind")
        _require_text(self.representation, field="KeyFacet.representation")
        _require_unique_texts(
            self.source_sample_ids, field="KeyFacet.source_sample_ids"
        )
        if not self.source_sample_ids:
            raise RailsError(
                "KeyFacet.source_sample_ids must bind the facet to TRAIN samples"
            )
        _require_unique_texts(self.parent_facet_ids, field="KeyFacet.parent_facet_ids")
        if self.facet_id in self.parent_facet_ids:
            raise RailsError("KeyFacet cannot name itself as a parent")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "facet_id": self.facet_id,
            "dimension": self.dimension,
            "representation_kind": self.representation_kind,
            "representation": self.representation,
            "source_sample_ids": list(self.source_sample_ids),
            "parent_facet_ids": list(self.parent_facet_ids),
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "KeyFacet":
        return cls(
            facet_id=document["facet_id"],
            dimension=document["dimension"],
            representation_kind=document["representation_kind"],
            representation=document["representation"],
            source_sample_ids=tuple(document.get("source_sample_ids", [])),
            parent_facet_ids=tuple(document.get("parent_facet_ids", [])),
        ).validate()


@dataclass(frozen=True)
class ValueBundle:
    """Sample-associated evidence returned by knowledge retrieval.

    ``content`` is the task-helpful payload that can later become an
    ``EvidenceItem``/``SupplyItem``.  ``task_target`` and ``prior_score`` are
    metadata: they model train-derived associations and priors but are not key
    text.  This keeps key matching separate from the result/evidence carried by
    the value.

    ``prior_score`` is a PROBABILITY and its declared range is
    ``[PRIOR_SCORE_MIN, PRIOR_SCORE_MAX]``. :meth:`validate` deliberately does
    NOT enforce that range -- see
    :meth:`KnowledgeSnapshot.from_frozen_json` for why a historical snapshot
    must stay loadable, and :func:`assert_prior_scores_are_probabilities` for
    the construction-side gate that refuses a new one fail-closed.
    """

    value_id: str
    content: str
    associated_facet_ids: tuple[str, ...]
    source_sample_ids: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    task_target: str | None = None
    prior_score: float | None = None

    def validate(self) -> "ValueBundle":
        _require_text(self.value_id, field="ValueBundle.value_id")
        _require_text(self.content, field="ValueBundle.content")
        _require_unique_texts(
            self.associated_facet_ids,
            field="ValueBundle.associated_facet_ids",
        )
        if not self.associated_facet_ids:
            raise RailsError(
                "ValueBundle must be associated with at least one key facet"
            )
        _require_unique_texts(
            self.source_sample_ids, field="ValueBundle.source_sample_ids"
        )
        if not self.source_sample_ids:
            raise RailsError(
                "ValueBundle.source_sample_ids must bind the value to TRAIN samples"
            )
        _require_unique_texts(self.provenance_refs, field="ValueBundle.provenance_refs")
        if not self.provenance_refs:
            raise RailsError("ValueBundle.provenance_refs must be non-empty")
        if self.task_target is not None:
            _require_text(self.task_target, field="ValueBundle.task_target")
        if self.prior_score is not None and (
            isinstance(self.prior_score, bool)
            or not isinstance(self.prior_score, (int, float))
            or not math.isfinite(float(self.prior_score))
        ):
            raise RailsError("ValueBundle.prior_score must be finite or None")
        return self

    def prior_score_range_violation(self) -> float | None:
        """This value's out-of-range ``prior_score``, or ``None``.

        Pure; the classifier both sides of the contract are written in terms
        of."""

        return prior_score_range_violation(self.prior_score)

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "value_id": self.value_id,
            "content": self.content,
            "associated_facet_ids": list(self.associated_facet_ids),
            "source_sample_ids": list(self.source_sample_ids),
            "provenance_refs": list(self.provenance_refs),
            "task_target": self.task_target,
            "prior_score": self.prior_score,
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "ValueBundle":
        return cls(
            value_id=document["value_id"],
            content=document["content"],
            associated_facet_ids=tuple(document.get("associated_facet_ids", [])),
            source_sample_ids=tuple(document.get("source_sample_ids", [])),
            provenance_refs=tuple(document.get("provenance_refs", [])),
            task_target=document.get("task_target"),
            prior_score=document.get("prior_score"),
        ).validate()


@dataclass(frozen=True)
class KnowledgeSnapshot:
    """A content-addressed, immutable-by-contract TRAIN knowledge build."""

    snapshot_id: str
    source_split_identity_hash: str
    source_sample_ids: tuple[str, ...]
    builder_policy_id: str
    facets: tuple[KeyFacet, ...]
    values: tuple[ValueBundle, ...]
    source_partition_role: str = TRAIN_PARTITION_ROLE
    snapshot_version: str = KNOWLEDGE_SNAPSHOT_VERSION

    def validate(self) -> "KnowledgeSnapshot":
        # Idempotence guard: this dataclass is frozen (content-addressed and
        # never mutated after construction), so a prior successful full
        # validation stays valid for the instance's whole lifetime. Repeat
        # AgentLoop waves at train scale otherwise re-walk every facet/value
        # and the acyclicity graph on every step. The flag is a plain
        # instance attribute (set via object.__setattr__ because the
        # dataclass is frozen) -- it is not a declared dataclass field, so it
        # never enters __eq__/__hash__/as_json/content_hash.
        if getattr(self, "_validated", False):
            return self
        _require_text(self.snapshot_id, field="KnowledgeSnapshot.snapshot_id")
        _require_sha256(
            self.source_split_identity_hash,
            field="KnowledgeSnapshot.source_split_identity_hash",
        )
        if self.source_partition_role not in _SOURCE_PARTITION_ROLES:
            raise RailsError(
                "KnowledgeSnapshot.source_partition_role must be 'train' or "
                "'external-governed'; DEV/TEST samples cannot construct "
                "runtime knowledge"
            )
        if self.snapshot_version != KNOWLEDGE_SNAPSHOT_VERSION:
            raise RailsError(
                f"KnowledgeSnapshot.snapshot_version must be "
                f"{KNOWLEDGE_SNAPSHOT_VERSION!r}"
            )
        _require_text(
            self.builder_policy_id, field="KnowledgeSnapshot.builder_policy_id"
        )
        _require_unique_texts(
            self.source_sample_ids, field="KnowledgeSnapshot.source_sample_ids"
        )
        if not self.source_sample_ids:
            raise RailsError("KnowledgeSnapshot.source_sample_ids must be non-empty")
        if not isinstance(self.facets, tuple) or not self.facets:
            raise RailsError("KnowledgeSnapshot.facets must be a non-empty tuple")
        if not isinstance(self.values, tuple) or not self.values:
            raise RailsError("KnowledgeSnapshot.values must be a non-empty tuple")

        facet_ids: set[str] = set()
        used_source_ids: set[str] = set()
        for facet in self.facets:
            if not isinstance(facet, KeyFacet):
                raise RailsError(
                    "KnowledgeSnapshot.facets entries must be KeyFacet instances"
                )
            facet.validate()
            if facet.facet_id in facet_ids:
                raise RailsError(
                    f"KnowledgeSnapshot has duplicate facet_id {facet.facet_id!r}"
                )
            facet_ids.add(facet.facet_id)
            used_source_ids.update(facet.source_sample_ids)
        for facet in self.facets:
            unknown_parents = set(facet.parent_facet_ids) - facet_ids
            if unknown_parents:
                raise RailsError(
                    f"KeyFacet {facet.facet_id!r} references unknown parent facets "
                    f"{sorted(unknown_parents)}"
                )
        self._assert_acyclic_facets()

        value_ids: set[str] = set()
        for value in self.values:
            if not isinstance(value, ValueBundle):
                raise RailsError(
                    "KnowledgeSnapshot.values entries must be ValueBundle instances"
                )
            value.validate()
            if value.value_id in value_ids:
                raise RailsError(
                    f"KnowledgeSnapshot has duplicate value_id {value.value_id!r}"
                )
            value_ids.add(value.value_id)
            unknown_facets = set(value.associated_facet_ids) - facet_ids
            if unknown_facets:
                raise RailsError(
                    f"ValueBundle {value.value_id!r} references unknown facets "
                    f"{sorted(unknown_facets)}"
                )
            used_source_ids.update(value.source_sample_ids)

        declared_source_ids = set(self.source_sample_ids)
        unknown_source_ids = used_source_ids - declared_source_ids
        if unknown_source_ids:
            raise RailsError(
                "KnowledgeSnapshot records reference source samples outside the frozen "
                f"TRAIN roster: {sorted(unknown_source_ids)}"
            )
        unused_source_ids = declared_source_ids - used_source_ids
        if unused_source_ids:
            raise RailsError(
                "KnowledgeSnapshot source roster contains samples with no facet or value "
                f"provenance: {sorted(unused_source_ids)}"
            )
        object.__setattr__(self, "_validated", True)
        return self

    def _assert_acyclic_facets(self) -> None:
        parents = {facet.facet_id: facet.parent_facet_ids for facet in self.facets}
        active: set[str] = set()
        complete: set[str] = set()

        def visit(facet_id: str) -> None:
            if facet_id in complete:
                return
            if facet_id in active:
                raise RailsError("KnowledgeSnapshot facet hierarchy contains a cycle")
            active.add(facet_id)
            for parent_id in parents[facet_id]:
                visit(parent_id)
            active.remove(facet_id)
            complete.add(facet_id)

        for facet_id in parents:
            visit(facet_id)

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "snapshot_version": self.snapshot_version,
            "snapshot_id": self.snapshot_id,
            "source_partition_role": self.source_partition_role,
            "source_split_identity_hash": self.source_split_identity_hash,
            "source_sample_ids": list(self.source_sample_ids),
            "builder_policy_id": self.builder_policy_id,
            "facets": [facet.as_json() for facet in self.facets],
            "values": [value.as_json() for value in self.values],
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    def prior_score_range_violations(self) -> tuple[tuple[str, float], ...]:
        """Every ``(value_id, prior_score)`` outside the declared range.

        Pure: it reports, it never raises. Sorted by ``value_id`` so the tuple
        is stable enough to put in a receipt."""

        return tuple(
            sorted(
                (value.value_id, violation)
                for value in self.values
                if (violation := value.prior_score_range_violation()) is not None
            )
        )

    @property
    def historical_prior_score_range_violations(self) -> tuple[tuple[str, float], ...]:
        """What :meth:`from_frozen_json` RECORDED when it loaded this snapshot.

        Empty for a snapshot that was constructed rather than loaded, and
        empty for a loaded snapshot that respects the range. A non-empty tuple
        means: these bytes are historical evidence produced before the range
        contract existed, they are readable on purpose, and every ranking
        statement derived from them inherits the defect. Non-empty is never a
        licence to write such a snapshot -- :meth:`frozen_json` refuses that
        outright."""

        return getattr(self, "_historical_prior_score_range_violations", ())

    def frozen_json(self) -> dict[str, object]:
        """THE CONSTRUCTION SIDE OF THE RANGE CONTRACT, FAIL-CLOSED.

        This method is the ONLY point at which a snapshot becomes durable,
        content-addressed bytes: both build scripts write what it returns and
        nothing on the load path calls it. So this is where a non-probability
        ``prior_score`` is refused, and refused hard -- a snapshot carrying one
        never reaches disk, never acquires a hash, and never becomes something
        a later round has to keep readable."""

        assert_prior_scores_are_probabilities(
            self.values, builder=f"KnowledgeSnapshot.frozen_json[{self.snapshot_id}]"
        )
        document = self.as_json()
        return {**document, "snapshot_sha256": content_hash(document)}

    @classmethod
    def from_frozen_json(cls, document: Mapping[str, object]) -> "KnowledgeSnapshot":
        """THE LOAD SIDE OF THE RANGE CONTRACT: ACCEPT, AND RECORD.

        Snapshots frozen before the range contract existed carry
        ``prior_score`` values above 1 -- the pinned Audio2Tool snapshot
        ``ec2f9ec4...9fb2`` reaches 4.1 on 193 of its 12,601 values. Those
        bytes are the record of what actually flew. Refusing to load them
        would break every landed replay and make the flights unauditable,
        which is a worse failure than the defect being audited. So loading
        never raises on range; instead the violations are RECORDED on the
        loaded instance, reachable through
        :attr:`historical_prior_score_range_violations`, and a
        :class:`RuntimeWarning` is emitted so the acceptance is never silent.

        The boundary is therefore explicit and one-directional: bytes may come
        IN carrying a violation and be labelled; no violation may go OUT
        through :meth:`frozen_json`."""

        claimed_hash = _require_sha256(
            document.get("snapshot_sha256"), field="KnowledgeSnapshot.snapshot_sha256"
        )
        body = dict(document)
        body.pop("snapshot_sha256", None)
        if content_hash(body) != claimed_hash:
            raise RailsError("KnowledgeSnapshot frozen document hash mismatch")
        snapshot = cls(
            snapshot_id=body["snapshot_id"],
            source_partition_role=body["source_partition_role"],
            source_split_identity_hash=body["source_split_identity_hash"],
            source_sample_ids=tuple(body.get("source_sample_ids", [])),
            builder_policy_id=body["builder_policy_id"],
            facets=tuple(KeyFacet.from_json(item) for item in body.get("facets", [])),
            values=tuple(
                ValueBundle.from_json(item) for item in body.get("values", [])
            ),
            snapshot_version=body["snapshot_version"],
        ).validate()
        if snapshot.content_hash() != claimed_hash:
            raise RailsError(
                "KnowledgeSnapshot contains unsupported or non-canonical fields"
            )
        violations = snapshot.prior_score_range_violations()
        # Frozen dataclass; recorded exactly the way ``_validated`` is, as a
        # plain instance attribute that is not a declared field, so it never
        # enters __eq__/__hash__/as_json/content_hash and cannot perturb the
        # snapshot's identity.
        object.__setattr__(
            snapshot, "_historical_prior_score_range_violations", violations
        )
        if violations:
            worst = max(score for _value_id, score in violations)
            warnings.warn(
                f"KnowledgeSnapshot {snapshot.snapshot_id!r} (sha256 "
                f"{claimed_hash}) carries {len(violations)} of "
                f"{len(snapshot.values)} prior_score values outside "
                f"[{PRIOR_SCORE_MIN}, {PRIOR_SCORE_MAX}] (supremum {worst}). "
                "It is HISTORICAL evidence and is loaded on purpose; it may "
                "not be re-frozen, and every ranking statement derived from "
                "it inherits the defect. See "
                "docs/readiness/2026-08-25-prior-score-semantics-repair.md",
                RuntimeWarning,
                stacklevel=2,
            )
        return snapshot


@dataclass(frozen=True)
class QueryState:
    """A DEV use-time query bound to encoded speech features or raw speech audio.

    ``speech_audio`` names hash-bound audio bytes used by a single-phase
    window controller. It does not authorize feature-only runners to accept
    raw-audio history; each transport still enforces its own typed boundary.
    """

    query_id: str
    query_sample_id: str
    speech_packet_id: str
    speech_packet_sha256: str
    use_split_identity_hash: str
    loop_step: int = 0
    visible_facet_ids: tuple[str, ...] = ()
    agent_state_ids: tuple[str, ...] = ()
    retrieved_value_ids: tuple[str, ...] = ()
    use_partition_role: str = DEV_PARTITION_ROLE
    query_source: str = "speech_features"
    query_state_version: str = QUERY_STATE_VERSION

    def validate(self) -> "QueryState":
        _require_text(self.query_id, field="QueryState.query_id")
        _require_text(self.query_sample_id, field="QueryState.query_sample_id")
        _require_text(self.speech_packet_id, field="QueryState.speech_packet_id")
        _require_sha256(
            self.speech_packet_sha256, field="QueryState.speech_packet_sha256"
        )
        _require_sha256(
            self.use_split_identity_hash,
            field="QueryState.use_split_identity_hash",
        )
        if self.use_partition_role != DEV_PARTITION_ROLE:
            raise RailsError(
                "QueryState.use_partition_role must be 'dev' for Stage-2 USE/OPTIMIZE"
            )
        if self.query_source not in ("speech_features", "speech_audio"):
            raise RailsError(
                "QueryState.query_source must bind 'speech_features' or 'speech_audio'; agent state or "
                "generated text cannot replace the original speech query"
            )
        if self.query_state_version != QUERY_STATE_VERSION:
            raise RailsError(
                f"QueryState.query_state_version must be {QUERY_STATE_VERSION!r}"
            )
        if (
            isinstance(self.loop_step, bool)
            or not isinstance(self.loop_step, int)
            or self.loop_step < 0
        ):
            raise RailsError("QueryState.loop_step must be a non-negative integer")
        _require_unique_texts(self.agent_state_ids, field="QueryState.agent_state_ids")
        _require_unique_texts(
            self.visible_facet_ids, field="QueryState.visible_facet_ids"
        )
        _require_unique_texts(
            self.retrieved_value_ids, field="QueryState.retrieved_value_ids"
        )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "query_state_version": self.query_state_version,
            "query_id": self.query_id,
            "query_sample_id": self.query_sample_id,
            "speech_packet_id": self.speech_packet_id,
            "speech_packet_sha256": self.speech_packet_sha256,
            "query_source": self.query_source,
            "use_partition_role": self.use_partition_role,
            "use_split_identity_hash": self.use_split_identity_hash,
            "loop_step": self.loop_step,
            "visible_facet_ids": list(self.visible_facet_ids),
            "agent_state_ids": list(self.agent_state_ids),
            "retrieved_value_ids": list(self.retrieved_value_ids),
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "QueryState":
        return cls(
            query_id=document["query_id"],
            query_sample_id=document["query_sample_id"],
            speech_packet_id=document["speech_packet_id"],
            speech_packet_sha256=document["speech_packet_sha256"],
            query_source=document.get("query_source", "speech_features"),
            use_partition_role=document.get("use_partition_role", DEV_PARTITION_ROLE),
            use_split_identity_hash=document["use_split_identity_hash"],
            loop_step=document.get("loop_step", 0),
            visible_facet_ids=tuple(document.get("visible_facet_ids", [])),
            agent_state_ids=tuple(document.get("agent_state_ids", [])),
            retrieved_value_ids=tuple(document.get("retrieved_value_ids", [])),
            query_state_version=document.get(
                "query_state_version", QUERY_STATE_VERSION
            ),
        ).validate()


@dataclass(frozen=True)
class RankedFacet:
    facet_id: str
    score: float

    def validate(self) -> "RankedFacet":
        _require_text(self.facet_id, field="RankedFacet.facet_id")
        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, (int, float))
            or not math.isfinite(float(self.score))
        ):
            raise RailsError("RankedFacet.score must be finite")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {"facet_id": self.facet_id, "score": self.score}

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "RankedFacet":
        return cls(facet_id=document["facet_id"], score=document["score"]).validate()


@dataclass(frozen=True)
class RankResult:
    snapshot_sha256: str
    query_state_sha256: str
    ranking_policy_id: str
    candidates: tuple[RankedFacet, ...]
    rank_result_version: str = RANK_RESULT_VERSION

    def validate(self) -> "RankResult":
        _require_sha256(self.snapshot_sha256, field="RankResult.snapshot_sha256")
        _require_sha256(self.query_state_sha256, field="RankResult.query_state_sha256")
        _require_text(self.ranking_policy_id, field="RankResult.ranking_policy_id")
        if self.rank_result_version != RANK_RESULT_VERSION:
            raise RailsError(
                f"RankResult.rank_result_version must be {RANK_RESULT_VERSION!r}"
            )
        if not isinstance(self.candidates, tuple):
            raise RailsError("RankResult.candidates must be a tuple")
        ids: set[str] = set()
        previous_score: float | None = None
        previous_id: str | None = None
        for candidate in self.candidates:
            if not isinstance(candidate, RankedFacet):
                raise RailsError(
                    "RankResult.candidates entries must be RankedFacet instances"
                )
            candidate.validate()
            if candidate.facet_id in ids:
                raise RailsError(
                    f"RankResult has duplicate facet_id {candidate.facet_id!r}"
                )
            ids.add(candidate.facet_id)
            score = float(candidate.score)
            if previous_score is not None and (
                score > previous_score
                or (score == previous_score and candidate.facet_id < previous_id)
            ):
                raise RailsError(
                    "RankResult.candidates must be sorted by score descending, then "
                    "facet_id ascending"
                )
            previous_score = score
            previous_id = candidate.facet_id
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "rank_result_version": self.rank_result_version,
            "snapshot_sha256": self.snapshot_sha256,
            "query_state_sha256": self.query_state_sha256,
            "ranking_policy_id": self.ranking_policy_id,
            "candidates": [candidate.as_json() for candidate in self.candidates],
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "RankResult":
        return cls(
            snapshot_sha256=document["snapshot_sha256"],
            query_state_sha256=document["query_state_sha256"],
            ranking_policy_id=document["ranking_policy_id"],
            candidates=tuple(
                RankedFacet.from_json(item) for item in document.get("candidates", [])
            ),
            rank_result_version=document.get(
                "rank_result_version", RANK_RESULT_VERSION
            ),
        ).validate()


@dataclass(frozen=True)
class FusionDecision:
    snapshot_sha256: str
    query_state_sha256: str
    rank_result_sha256: str
    fusion_policy_id: str
    supporting_facet_ids: tuple[str, ...]
    selected_value_ids: tuple[str, ...]
    fusion_decision_version: str = FUSION_DECISION_VERSION

    def validate(self) -> "FusionDecision":
        _require_sha256(self.snapshot_sha256, field="FusionDecision.snapshot_sha256")
        _require_sha256(
            self.query_state_sha256, field="FusionDecision.query_state_sha256"
        )
        _require_sha256(
            self.rank_result_sha256, field="FusionDecision.rank_result_sha256"
        )
        _require_text(self.fusion_policy_id, field="FusionDecision.fusion_policy_id")
        _require_unique_texts(
            self.supporting_facet_ids,
            field="FusionDecision.supporting_facet_ids",
        )
        _require_unique_texts(
            self.selected_value_ids,
            field="FusionDecision.selected_value_ids",
        )
        if self.selected_value_ids and not self.supporting_facet_ids:
            raise RailsError(
                "FusionDecision cannot select values without supporting ranked facets"
            )
        if self.fusion_decision_version != FUSION_DECISION_VERSION:
            raise RailsError(
                f"FusionDecision.fusion_decision_version must be "
                f"{FUSION_DECISION_VERSION!r}"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "fusion_decision_version": self.fusion_decision_version,
            "snapshot_sha256": self.snapshot_sha256,
            "query_state_sha256": self.query_state_sha256,
            "rank_result_sha256": self.rank_result_sha256,
            "fusion_policy_id": self.fusion_policy_id,
            "supporting_facet_ids": list(self.supporting_facet_ids),
            "selected_value_ids": list(self.selected_value_ids),
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "FusionDecision":
        return cls(
            snapshot_sha256=document["snapshot_sha256"],
            query_state_sha256=document["query_state_sha256"],
            rank_result_sha256=document["rank_result_sha256"],
            fusion_policy_id=document["fusion_policy_id"],
            supporting_facet_ids=tuple(document.get("supporting_facet_ids", [])),
            selected_value_ids=tuple(document.get("selected_value_ids", [])),
            fusion_decision_version=document.get(
                "fusion_decision_version", FUSION_DECISION_VERSION
            ),
        ).validate()


@dataclass(frozen=True)
class AgentStateArtifact:
    """One bounded ORG artifact produced from a speech-conditioned contact.

    Agent state is auxiliary organization, never knowledge SUPPLY. The two
    source hashes prove which speech-bound query state and model response
    produced it. ``cited_value_ids`` records any train-built values it
    summarizes without reclassifying those values as newly acquired.
    """

    state_id: str
    state_kind: str
    content: str
    source_query_state_sha256: str
    source_response_sha256: str
    producer_policy_id: str
    cited_value_ids: tuple[str, ...]
    state_artifact_version: str = AGENT_STATE_ARTIFACT_VERSION

    def validate(self) -> "AgentStateArtifact":
        _require_text(self.state_id, field="AgentStateArtifact.state_id")
        _require_text(self.state_kind, field="AgentStateArtifact.state_kind")
        _require_text(self.content, field="AgentStateArtifact.content")
        _require_sha256(
            self.source_query_state_sha256,
            field="AgentStateArtifact.source_query_state_sha256",
        )
        _require_sha256(
            self.source_response_sha256,
            field="AgentStateArtifact.source_response_sha256",
        )
        _require_text(
            self.producer_policy_id,
            field="AgentStateArtifact.producer_policy_id",
        )
        _require_unique_texts(
            self.cited_value_ids,
            field="AgentStateArtifact.cited_value_ids",
        )
        if self.state_artifact_version != AGENT_STATE_ARTIFACT_VERSION:
            raise RailsError(
                "AgentStateArtifact.state_artifact_version must be "
                f"{AGENT_STATE_ARTIFACT_VERSION!r}"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "state_artifact_version": self.state_artifact_version,
            "state_id": self.state_id,
            "state_kind": self.state_kind,
            "content": self.content,
            "source_query_state_sha256": self.source_query_state_sha256,
            "source_response_sha256": self.source_response_sha256,
            "producer_policy_id": self.producer_policy_id,
            "cited_value_ids": list(self.cited_value_ids),
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "AgentStateArtifact":
        return cls(
            state_id=document["state_id"],
            state_kind=document["state_kind"],
            content=document["content"],
            source_query_state_sha256=document["source_query_state_sha256"],
            source_response_sha256=document["source_response_sha256"],
            producer_policy_id=document["producer_policy_id"],
            cited_value_ids=tuple(document.get("cited_value_ids", [])),
            state_artifact_version=document.get(
                "state_artifact_version", AGENT_STATE_ARTIFACT_VERSION
            ),
        ).validate()


@dataclass(frozen=True)
class SpeechPacketDerivation:
    """One registered derivation of a trajectory's ORIGINAL speech packet.

    The standing rule is that a DEV query is this sample's own speech and can
    never become agent text (:meth:`QueryState.validate`). Until 2026-09-08
    that rule was enforced by freezing ``speech_packet_id``/
    ``speech_packet_sha256`` for the whole trajectory, which also made a
    SELECTIVE RE-LISTEN -- listening again, more closely, to a span of the
    same call -- unexpressible (assessment
    ``2026-09-08-openjiuwen-implementation-assessment-v1.md`` §2.3).

    This record is the narrow relaxation. It admits a successor packet only
    when the successor is a transform, drawn from
    :data:`SPEECH_PACKET_DERIVATION_KINDS`, of the packet the trajectory
    STARTED from -- never of an intermediate derived packet, so a trajectory
    can never drift away from its own media one derivation at a time, and
    never of anything else, so foreign audio has no path in. Identity only:
    this module reads no bytes and no filesystem (module docstring). The BYTE
    chain is the separate, unchanged rail --
    ``core.model.slices.SliceRegistry`` re-measures the parent media and the
    cut file, exactly as ``obs-replay-loop`` already does for its re-cut
    windows -- and ``rails.observe`` is what wires the two together.

    ``derivation_params_hash`` is the canonical hash of the parameters that
    governed the transform (the flagged span, the context margin, the kind),
    so two derivations that claim the same output from different parameters
    cannot both verify -- the same discipline
    ``core.evidence_derivation.canonical_params_hash`` applies to derived
    evidence text.
    """

    parent_packet_id: str
    parent_packet_sha256: str
    derived_packet_id: str
    derived_packet_sha256: str
    derivation_kind: str
    derivation_params_hash: str
    derivation_version: str = SPEECH_PACKET_DERIVATION_VERSION

    def validate(self) -> "SpeechPacketDerivation":
        _require_text(self.parent_packet_id, field="SpeechPacketDerivation.parent_packet_id")
        _require_text(
            self.derived_packet_id, field="SpeechPacketDerivation.derived_packet_id"
        )
        _require_sha256(
            self.parent_packet_sha256,
            field="SpeechPacketDerivation.parent_packet_sha256",
        )
        _require_sha256(
            self.derived_packet_sha256,
            field="SpeechPacketDerivation.derived_packet_sha256",
        )
        _require_sha256(
            self.derivation_params_hash,
            field="SpeechPacketDerivation.derivation_params_hash",
        )
        if self.derivation_version != SPEECH_PACKET_DERIVATION_VERSION:
            raise RailsError(
                "SpeechPacketDerivation.derivation_version must be "
                f"{SPEECH_PACKET_DERIVATION_VERSION!r}"
            )
        if self.derivation_kind not in SPEECH_PACKET_DERIVATION_KINDS:
            raise RailsError(
                "SpeechPacketDerivation.derivation_kind must be one of "
                f"{sorted(SPEECH_PACKET_DERIVATION_KINDS)}"
            )
        if self.derived_packet_id == self.parent_packet_id:
            raise RailsError(
                "a speech-packet derivation must produce a NEW packet id; reusing "
                "the parent's id would make the derivation unaddressable"
            )
        if self.derived_packet_sha256 == self.parent_packet_sha256:
            raise RailsError(
                "a speech-packet derivation whose output hashes to its parent "
                "derived nothing; refused"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "derivation_version": self.derivation_version,
            "parent_packet_id": self.parent_packet_id,
            "parent_packet_sha256": self.parent_packet_sha256,
            "derived_packet_id": self.derived_packet_id,
            "derived_packet_sha256": self.derived_packet_sha256,
            "derivation_kind": self.derivation_kind,
            "derivation_params_hash": self.derivation_params_hash,
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "SpeechPacketDerivation":
        return cls(
            parent_packet_id=document["parent_packet_id"],
            parent_packet_sha256=document["parent_packet_sha256"],
            derived_packet_id=document["derived_packet_id"],
            derived_packet_sha256=document["derived_packet_sha256"],
            derivation_kind=document["derivation_kind"],
            derivation_params_hash=document["derivation_params_hash"],
            derivation_version=document.get(
                "derivation_version", SPEECH_PACKET_DERIVATION_VERSION
            ),
        ).validate()


@dataclass(frozen=True)
class AgentStepTransition:
    """One speech-bound external AgentLoop decision and its information delta.

    The transition distinguishes new train-built values (SUPPLY), values
    merely revisited by verification (USE), generated state references (ORG),
    and information discarded by backtracking. It carries identities only;
    task predictions and post-hoc reward remain outside this runtime contract.
    """

    snapshot_sha256: str
    prior_query_state_sha256: str
    next_query_state_sha256: str | None
    action_kind: str
    action_target_refs: tuple[str, ...]
    new_value_ids: tuple[str, ...]
    used_value_ids: tuple[str, ...]
    dropped_value_ids: tuple[str, ...]
    new_agent_state_ids: tuple[str, ...]
    dropped_agent_state_ids: tuple[str, ...]
    new_facet_ids: tuple[str, ...] = ()
    used_facet_ids: tuple[str, ...] = ()
    dropped_facet_ids: tuple[str, ...] = ()
    # OBS delta, present ONLY on a ``relisten`` step: the registered
    # derivation that moves the observation from the trajectory's original
    # speech packet to a re-cut/enhanced/re-encoded packet of the same media.
    # ``None`` -- every step this repository has ever run -- keeps the
    # transition's JSON and hash byte-identical to before the field existed.
    speech_packet_derivation: "SpeechPacketDerivation | None" = None
    transition_version: str = AGENT_STEP_TRANSITION_VERSION

    def validate(self) -> "AgentStepTransition":
        _require_sha256(
            self.snapshot_sha256,
            field="AgentStepTransition.snapshot_sha256",
        )
        _require_sha256(
            self.prior_query_state_sha256,
            field="AgentStepTransition.prior_query_state_sha256",
        )
        if self.next_query_state_sha256 is not None:
            _require_sha256(
                self.next_query_state_sha256,
                field="AgentStepTransition.next_query_state_sha256",
            )
        if self.transition_version != AGENT_STEP_TRANSITION_VERSION:
            raise RailsError(
                "AgentStepTransition.transition_version must be "
                f"{AGENT_STEP_TRANSITION_VERSION!r}"
            )
        if self.action_kind not in AGENT_ACTION_KINDS:
            raise RailsError(
                "AgentStepTransition.action_kind must be one of "
                f"{sorted(AGENT_ACTION_KINDS)}"
            )
        for field_name in (
            "action_target_refs",
            "new_value_ids",
            "used_value_ids",
            "dropped_value_ids",
            "new_agent_state_ids",
            "dropped_agent_state_ids",
            "new_facet_ids",
            "used_facet_ids",
            "dropped_facet_ids",
        ):
            _require_unique_texts(
                getattr(self, field_name),
                field=f"AgentStepTransition.{field_name}",
            )
        if set(self.new_value_ids) & set(self.dropped_value_ids):
            raise RailsError("AgentStepTransition cannot add and drop the same value")
        if set(self.new_agent_state_ids) & set(self.dropped_agent_state_ids):
            raise RailsError(
                "AgentStepTransition cannot add and drop the same agent state"
            )
        if set(self.new_facet_ids) & set(self.dropped_facet_ids):
            raise RailsError("AgentStepTransition cannot add and drop the same facet")

        # The derivation record and the ``relisten`` kind are one object: a
        # step that moves the observation says so in its action_kind, and a
        # step that says ``relisten`` proves the move. Neither half is legal
        # alone -- which is what lets any reader of a trace decide, from
        # action_kind ALONE, whether the observation moved.
        if self.speech_packet_derivation is not None:
            if not isinstance(self.speech_packet_derivation, SpeechPacketDerivation):
                raise RailsError(
                    "AgentStepTransition.speech_packet_derivation must be a "
                    "SpeechPacketDerivation"
                )
            if self.action_kind != "relisten":
                raise RailsError(
                    "only a 'relisten' AgentStepTransition may carry a speech-packet "
                    f"derivation, got action_kind {self.action_kind!r}"
                )
            self.speech_packet_derivation.validate()
        elif self.action_kind == "relisten":
            raise RailsError(
                "a 'relisten' AgentStepTransition requires its speech-packet "
                "derivation record; an unregistered observation change is refused"
            )
        if self.action_kind == "relisten" and (
            self.new_agent_state_ids or self.used_value_ids or self.used_facet_ids
        ):
            raise RailsError(
                "relisten changes only the observation: it cannot create agent "
                "state or claim knowledge use"
            )

        if self.action_kind == "stop":
            if self.next_query_state_sha256 is not None or any(
                (
                    self.action_target_refs,
                    self.new_value_ids,
                    self.used_value_ids,
                    self.dropped_value_ids,
                    self.new_agent_state_ids,
                    self.dropped_agent_state_ids,
                    self.new_facet_ids,
                    self.used_facet_ids,
                    self.dropped_facet_ids,
                )
            ):
                raise RailsError(
                    "stop must have no successor, target, or information delta"
                )
            return self

        if self.next_query_state_sha256 is None:
            raise RailsError(
                "a non-stop AgentStepTransition requires a successor QueryState"
            )
        if not self.action_target_refs:
            raise RailsError(
                "a non-stop AgentStepTransition requires action_target_refs"
            )
        if self.action_kind in _SUPPLY_ACTION_KINDS and not (
            self.new_value_ids or self.new_facet_ids
        ):
            raise RailsError(
                f"{self.action_kind} must introduce at least one new value or facet"
            )
        if self.action_kind == "organize" and not self.new_agent_state_ids:
            raise RailsError("organize must introduce at least one new agent state")
        if self.action_kind == "verify" and not self.used_value_ids:
            raise RailsError("verify must use at least one previously supplied value")
        if self.action_kind == "backtrack" and not (
            self.dropped_value_ids
            or self.dropped_agent_state_ids
            or self.dropped_facet_ids
        ):
            raise RailsError("backtrack must drop at least one value, facet, or state")
        if self.action_kind != "backtrack" and (
            self.dropped_value_ids
            or self.dropped_agent_state_ids
            or self.dropped_facet_ids
        ):
            raise RailsError("only backtrack may drop values, facets, or agent states")
        if self.action_kind not in _SUPPLY_ACTION_KINDS and (
            self.new_value_ids or self.new_facet_ids
        ):
            raise RailsError(
                "only acquire, expand, or contrast may claim new supplied knowledge"
            )
        if self.action_kind == "backtrack" and (
            self.new_agent_state_ids
            or self.used_value_ids
            or self.new_facet_ids
            or self.used_facet_ids
        ):
            raise RailsError(
                "backtrack cannot create agent state or claim knowledge use"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        document: dict[str, object] = {
            "transition_version": self.transition_version,
            "snapshot_sha256": self.snapshot_sha256,
            "prior_query_state_sha256": self.prior_query_state_sha256,
            "next_query_state_sha256": self.next_query_state_sha256,
            "action_kind": self.action_kind,
            "action_target_refs": list(self.action_target_refs),
            "new_value_ids": list(self.new_value_ids),
            "used_value_ids": list(self.used_value_ids),
            "dropped_value_ids": list(self.dropped_value_ids),
            "new_agent_state_ids": list(self.new_agent_state_ids),
            "dropped_agent_state_ids": list(self.dropped_agent_state_ids),
            "new_facet_ids": list(self.new_facet_ids),
            "used_facet_ids": list(self.used_facet_ids),
            "dropped_facet_ids": list(self.dropped_facet_ids),
        }
        # Emitted only when a derivation exists, so every transition this
        # repository has already sealed keeps its exact JSON bytes and its
        # exact content hash (the "today's steps unchanged byte for byte"
        # requirement of the 2026-09-08 change list, item 3).
        if self.speech_packet_derivation is not None:
            document["speech_packet_derivation"] = (
                self.speech_packet_derivation.as_json()
            )
        return document

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "AgentStepTransition":
        derivation_document = document.get("speech_packet_derivation")
        return cls(
            snapshot_sha256=document["snapshot_sha256"],
            prior_query_state_sha256=document["prior_query_state_sha256"],
            next_query_state_sha256=document.get("next_query_state_sha256"),
            action_kind=document["action_kind"],
            action_target_refs=tuple(document.get("action_target_refs", [])),
            new_value_ids=tuple(document.get("new_value_ids", [])),
            used_value_ids=tuple(document.get("used_value_ids", [])),
            dropped_value_ids=tuple(document.get("dropped_value_ids", [])),
            new_agent_state_ids=tuple(document.get("new_agent_state_ids", [])),
            dropped_agent_state_ids=tuple(document.get("dropped_agent_state_ids", [])),
            new_facet_ids=tuple(document.get("new_facet_ids", [])),
            used_facet_ids=tuple(document.get("used_facet_ids", [])),
            dropped_facet_ids=tuple(document.get("dropped_facet_ids", [])),
            speech_packet_derivation=(
                None
                if derivation_document is None
                else SpeechPacketDerivation.from_json(derivation_document)
            ),
            transition_version=document.get(
                "transition_version", AGENT_STEP_TRANSITION_VERSION
            ),
        ).validate()


def _assert_speech_packet_binding(
    *,
    prior_query_state: QueryState,
    next_query_state: QueryState,
    transition: AgentStepTransition,
    origin_speech_packet: tuple[str, str] | None,
) -> None:
    """The observation half of :func:`assert_agent_step_binding`.

    Two outcomes, and only two. The successor either keeps the prior step's
    exact packet -- the historical rule, the case every sealed run took, and
    the case in which a derivation record would be a lie and is refused -- or
    it carries a :class:`SpeechPacketDerivation` whose parent is the
    trajectory's ORIGINAL packet and whose output is exactly the successor's
    packet. An unregistered swap falls through to the historical refusal,
    word for word, so a trace reader (and every existing test that matches on
    it) sees the same sentence it always did.
    """

    if origin_speech_packet is None:
        origin = (
            prior_query_state.speech_packet_id,
            prior_query_state.speech_packet_sha256,
        )
    else:
        if (
            not isinstance(origin_speech_packet, tuple)
            or len(origin_speech_packet) != 2
        ):
            raise RailsError(
                "origin_speech_packet must be a (packet_id, packet_sha256) pair"
            )
        origin = (
            _require_text(
                origin_speech_packet[0], field="origin_speech_packet.packet_id"
            ),
            _require_sha256(
                origin_speech_packet[1], field="origin_speech_packet.packet_sha256"
            ),
        )
    prior_packet = (
        prior_query_state.speech_packet_id,
        prior_query_state.speech_packet_sha256,
    )
    next_packet = (
        next_query_state.speech_packet_id,
        next_query_state.speech_packet_sha256,
    )
    derivation = transition.speech_packet_derivation
    if next_packet == prior_packet:
        if derivation is not None:
            raise RailsError(
                "a speech-packet derivation that derives nothing is refused: the "
                "successor QueryState carries the prior step's own packet"
            )
        return
    if derivation is None:
        raise RailsError(
            "AgentStepTransition must keep the same original speech packet and "
            "DEV query binding across every step"
        )
    derivation.validate()
    if (derivation.parent_packet_id, derivation.parent_packet_sha256) != origin:
        raise RailsError(
            "a speech-packet derivation must chain to this trajectory's ORIGINAL "
            f"speech packet {origin[0]!r}/{origin[1][:12]}..., but names parent "
            f"{derivation.parent_packet_id!r}/{derivation.parent_packet_sha256[:12]}..."
        )
    if (derivation.derived_packet_id, derivation.derived_packet_sha256) != next_packet:
        raise RailsError(
            "the speech-packet derivation does not produce the successor "
            f"QueryState's packet: derivation yields {derivation.derived_packet_id!r}"
            f"/{derivation.derived_packet_sha256[:12]}..., the successor binds "
            f"{next_packet[0]!r}/{next_packet[1][:12]}..."
        )


def assert_agent_step_binding(
    *,
    snapshot: KnowledgeSnapshot,
    prior_query_state: QueryState,
    next_query_state: QueryState | None,
    transition: AgentStepTransition,
    snapshot_sha256: str | None = None,
    origin_speech_packet: tuple[str, str] | None = None,
) -> None:
    """Prove one Agent step preserves speech and reports its exact delta.

    ``origin_speech_packet`` is the ``(packet_id, packet_sha256)`` this
    trajectory STARTED from -- the only packet a registered derivation may
    name as its parent. ``None``, the default and every caller written before
    2026-09-08, means "the prior step's own packet", which reproduces the
    historical rule exactly: with no derivation on the transition the packet
    is frozen for the whole trajectory, and the refusal message is unchanged.
    A driver that runs an Observer step (``rails.observe``) passes the
    trajectory's initial packet here, so a second re-listen still chains to
    the ORIGINAL media rather than to the first re-listen's own cut -- the
    successor ``QueryState`` itself carries no origin field, so no controller
    has to learn to propagate one.

    ``snapshot_sha256``, when given, must be the caller's own already-computed
    ``snapshot.content_hash()`` (only format-checked here, not recomputed
    against ``snapshot`` -- callers own the pairing, exactly as
    ``AgentStepTransition.snapshot_sha256`` already relies on caller-supplied
    hashes). This lets a driver that revalidates the same frozen snapshot
    across many waves skip re-hashing the whole snapshot every time; passing
    ``None`` keeps the original recompute-every-call behavior.
    """

    snapshot.validate()
    prior_query_state.validate()
    transition.validate()
    snapshot_sha256 = (
        snapshot.content_hash()
        if snapshot_sha256 is None
        else _require_sha256(
            snapshot_sha256, field="assert_agent_step_binding.snapshot_sha256"
        )
    )
    if transition.snapshot_sha256 != snapshot_sha256:
        raise RailsError("AgentStepTransition is bound to a different snapshot")
    if transition.prior_query_state_sha256 != prior_query_state.content_hash():
        raise RailsError("AgentStepTransition is bound to a different prior QueryState")
    if prior_query_state.query_sample_id in set(snapshot.source_sample_ids):
        raise RailsError(
            "AgentStepTransition query overlaps the TRAIN snapshot source roster"
        )

    if transition.action_kind == "stop":
        if next_query_state is not None:
            raise RailsError("stop cannot bind a successor QueryState")
        return
    if next_query_state is None:
        raise RailsError("non-stop AgentStepTransition requires next_query_state")
    next_query_state.validate()
    if transition.next_query_state_sha256 != next_query_state.content_hash():
        raise RailsError("AgentStepTransition is bound to a different next QueryState")
    if next_query_state.query_sample_id in set(snapshot.source_sample_ids):
        raise RailsError(
            "AgentStepTransition successor overlaps the TRAIN snapshot source roster"
        )

    stable_query_fields = (
        "query_sample_id",
        "use_split_identity_hash",
        "use_partition_role",
        "query_source",
    )
    if any(
        getattr(prior_query_state, field_name) != getattr(next_query_state, field_name)
        for field_name in stable_query_fields
    ):
        raise RailsError(
            "AgentStepTransition must keep the same original speech packet and "
            "DEV query binding across every step"
        )
    _assert_speech_packet_binding(
        prior_query_state=prior_query_state,
        next_query_state=next_query_state,
        transition=transition,
        origin_speech_packet=origin_speech_packet,
    )
    if next_query_state.loop_step != prior_query_state.loop_step + 1:
        raise RailsError(
            "AgentStepTransition successor loop_step must increment by exactly one"
        )

    known_value_ids = {value.value_id for value in snapshot.values}
    referenced_value_ids = set(
        (
            *transition.new_value_ids,
            *transition.used_value_ids,
            *transition.dropped_value_ids,
        )
    )
    unknown_value_ids = referenced_value_ids - known_value_ids
    if unknown_value_ids:
        raise RailsError(
            "AgentStepTransition references values outside the frozen snapshot: "
            f"{sorted(unknown_value_ids)}"
        )
    known_facet_ids = {facet.facet_id for facet in snapshot.facets}
    referenced_facet_ids = set(
        (
            *transition.new_facet_ids,
            *transition.used_facet_ids,
            *transition.dropped_facet_ids,
        )
    )
    unknown_facet_ids = referenced_facet_ids - known_facet_ids
    if unknown_facet_ids:
        raise RailsError(
            "AgentStepTransition references facets outside the frozen snapshot: "
            f"{sorted(unknown_facet_ids)}"
        )

    prior_values = set(prior_query_state.retrieved_value_ids)
    next_values = set(next_query_state.retrieved_value_ids)
    prior_facets = set(prior_query_state.visible_facet_ids)
    next_facets = set(next_query_state.visible_facet_ids)
    prior_states = set(prior_query_state.agent_state_ids)
    next_states = set(next_query_state.agent_state_ids)
    repeated_values = set(transition.new_value_ids) & prior_values
    if repeated_values:
        raise RailsError(
            "AgentStepTransition cannot claim already visible values as new SUPPLY: "
            f"{sorted(repeated_values)}"
        )
    repeated_states = set(transition.new_agent_state_ids) & prior_states
    if repeated_states:
        raise RailsError(
            "AgentStepTransition cannot claim already visible Agent states as new ORG: "
            f"{sorted(repeated_states)}"
        )
    repeated_facets = set(transition.new_facet_ids) & prior_facets
    if repeated_facets:
        raise RailsError(
            "AgentStepTransition cannot claim already visible facets as new SUPPLY: "
            f"{sorted(repeated_facets)}"
        )
    absent_dropped_values = set(transition.dropped_value_ids) - prior_values
    absent_dropped_states = set(transition.dropped_agent_state_ids) - prior_states
    absent_dropped_facets = set(transition.dropped_facet_ids) - prior_facets
    if absent_dropped_values or absent_dropped_states or absent_dropped_facets:
        raise RailsError(
            "AgentStepTransition cannot drop knowledge or states that were not visible: "
            f"values={sorted(absent_dropped_values)}, "
            f"facets={sorted(absent_dropped_facets)}, "
            f"states={sorted(absent_dropped_states)}"
        )
    if transition.action_kind == "backtrack":
        expected_values = prior_values - set(transition.dropped_value_ids)
        expected_facets = prior_facets - set(transition.dropped_facet_ids)
        expected_states = prior_states - set(transition.dropped_agent_state_ids)
    else:
        expected_values = prior_values | set(transition.new_value_ids)
        expected_facets = prior_facets | set(transition.new_facet_ids)
        expected_states = prior_states | set(transition.new_agent_state_ids)
    if next_values != expected_values:
        raise RailsError(
            "AgentStepTransition new/dropped value ids do not match the successor QueryState"
        )
    if next_states != expected_states:
        raise RailsError(
            "AgentStepTransition new/dropped state ids do not match the successor QueryState"
        )
    if next_facets != expected_facets:
        raise RailsError(
            "AgentStepTransition new/dropped facet ids do not match the successor QueryState"
        )
    if not set(transition.used_value_ids).issubset(next_values):
        raise RailsError(
            "AgentStepTransition used values must remain visible in the successor QueryState"
        )
    if not set(transition.used_facet_ids).issubset(next_facets):
        raise RailsError(
            "AgentStepTransition used facets must remain visible in the successor QueryState"
        )


def assert_knowledge_use_binding(
    *,
    snapshot: KnowledgeSnapshot,
    query_state: QueryState,
    rank_result: RankResult,
    fusion_decision: FusionDecision,
    snapshot_sha256: str | None = None,
) -> None:
    """Fail closed unless one DEV decision uses one disjoint TRAIN snapshot.

    This is the machine-enforced BUILD/USE boundary.  It verifies every hash
    edge, query/knowledge sample disjointness, prior-loop value references,
    ranked facet membership, and the final facet-to-value association.

    ``snapshot_sha256``, when given, must be the caller's own already-computed
    ``snapshot.content_hash()`` (only format-checked here, not recomputed
    against ``snapshot``); see :func:`assert_agent_step_binding` for the same
    passthrough contract. Passing ``None`` keeps the original
    recompute-every-call behavior.
    """

    snapshot.validate()
    query_state.validate()
    rank_result.validate()
    fusion_decision.validate()

    if query_state.query_sample_id in set(snapshot.source_sample_ids):
        raise RailsError(
            "knowledge USE query sample overlaps the TRAIN snapshot source roster"
        )
    snapshot_sha256 = (
        snapshot.content_hash()
        if snapshot_sha256 is None
        else _require_sha256(
            snapshot_sha256, field="assert_knowledge_use_binding.snapshot_sha256"
        )
    )
    query_state_sha256 = query_state.content_hash()
    if rank_result.snapshot_sha256 != snapshot_sha256:
        raise RailsError("RankResult is bound to a different KnowledgeSnapshot")
    if rank_result.query_state_sha256 != query_state_sha256:
        raise RailsError("RankResult is bound to a different QueryState")
    if fusion_decision.snapshot_sha256 != snapshot_sha256:
        raise RailsError("FusionDecision is bound to a different KnowledgeSnapshot")
    if fusion_decision.query_state_sha256 != query_state_sha256:
        raise RailsError("FusionDecision is bound to a different QueryState")
    if fusion_decision.rank_result_sha256 != rank_result.content_hash():
        raise RailsError("FusionDecision is bound to a different RankResult")

    values_by_id = {value.value_id: value for value in snapshot.values}
    unknown_previous_values = set(query_state.retrieved_value_ids) - set(values_by_id)
    if unknown_previous_values:
        raise RailsError(
            "QueryState references values outside the frozen snapshot: "
            f"{sorted(unknown_previous_values)}"
        )
    facet_ids = {facet.facet_id for facet in snapshot.facets}
    unknown_previous_facets = set(query_state.visible_facet_ids) - facet_ids
    if unknown_previous_facets:
        raise RailsError(
            "QueryState references facets outside the frozen snapshot: "
            f"{sorted(unknown_previous_facets)}"
        )
    ranked_facet_ids = {candidate.facet_id for candidate in rank_result.candidates}
    unknown_ranked_facets = ranked_facet_ids - facet_ids
    if unknown_ranked_facets:
        raise RailsError(
            f"RankResult references facets outside the snapshot: "
            f"{sorted(unknown_ranked_facets)}"
        )
    support_ids = set(fusion_decision.supporting_facet_ids)
    if not support_ids.issubset(ranked_facet_ids):
        raise RailsError(
            "FusionDecision supporting facets must be present in RankResult"
        )
    unknown_values = set(fusion_decision.selected_value_ids) - set(values_by_id)
    if unknown_values:
        raise RailsError(
            f"FusionDecision selects values outside the snapshot: {sorted(unknown_values)}"
        )
    for value_id in fusion_decision.selected_value_ids:
        value_facets = set(values_by_id[value_id].associated_facet_ids)
        if value_facets.isdisjoint(support_ids):
            raise RailsError(
                f"FusionDecision value {value_id!r} has no association with its "
                "supporting ranked facets"
            )


__all__ = [
    "AGENT_ACTION_KINDS",
    "AGENT_STATE_ARTIFACT_VERSION",
    "AGENT_STEP_TRANSITION_VERSION",
    "AgentStateArtifact",
    "AgentStepTransition",
    "DEV_PARTITION_ROLE",
    "EXTERNAL_GOVERNED_PARTITION_ROLE",
    "FUSION_DECISION_VERSION",
    "FusionDecision",
    "KNOWLEDGE_SNAPSHOT_VERSION",
    "KeyFacet",
    "KnowledgeSnapshot",
    "QUERY_STATE_VERSION",
    "QueryState",
    "RANK_RESULT_VERSION",
    "RankResult",
    "RankedFacet",
    "SPEECH_PACKET_DERIVATION_KINDS",
    "SPEECH_PACKET_DERIVATION_VERSION",
    "SpeechPacketDerivation",
    "TRAIN_PARTITION_ROLE",
    "ValueBundle",
    "assert_agent_step_binding",
    "assert_knowledge_use_binding",
]
