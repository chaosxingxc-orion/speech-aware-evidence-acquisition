"""P-SLU flight orchestration -- REGISTERED probe (Stage-2, bounded-discovery-
probe): ``docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md``.

Six arms over the SAME n=60 devel sample set (A0/A1/A1'/A2/A3/A4), NOT run
through ``rails.runner.run_rails_experiment`` -- that runner's ``arms=``
vocabulary is frozen to exactly ``("zero-supply", "supplied")``
(``rails.runner.RAILS_ARMS``); six independently-named, differently-rostered
arms need their own orchestration loop, built from the SAME primitives
that runner composes on top of (``SlurpAdapter.assemble_prompt`` /
``CoreClient.complete`` / ``SlurpAdapter.score`` /
``SlurpAdapter.extract_consumption``), never a reimplementation of them.

Two-phase plan (bridge mission instruction): PHASE 1 sends one zero-supply
(A0) request per sample and parses its predicted scenario
(``reproduction.slurp_scoring.parse_slu_response``) -- this IS the A0 arm's
own scored response, spent once, never a second throwaway call (the
preregistration's own cost line, "6 arms x 60 + headroom", counts phase 1 as
arm A0, not as an extra pass). PHASE 2 sends the remaining five arms (A1,
A1', A2, A3, A4) per sample, where A1' selects its roster by EACH sample's
own phase-1 PREDICTED scenario (self-supplied, deployment-legal) rather than
A1's gold scenario (ceiling-tier, gold-scoped selection -- the
preregistration's own "ceiling companion" label). If phase 1 failed to parse
a scenario, or predicted one outside the 18-scenario roster table, A1' falls
back to the scenario-agnostic A2 roster -- NEVER to the gold scenario: a
gold fallback would silently promote the "self-supplied" arm to ceiling
tier on exactly the samples where the core's own first pass was weakest,
which is precisely backwards.

Rosters come ONLY from ``configs/probes/g0-binding/pslu-rosters-train-only
.json`` (:func:`load_pslu_rosters` checks that file's own
``legality_tier``/``train_synthetic_refused`` fields at load time) --
``data.slurp.load_slurp_ontology`` (the shipped ontology miner, ceiling-tier
for a devel-split probe: 64.8% verbatim ``train_synthetic`` overlap with
``devel``, that function's own docstring) is asserted NOT referenced
anywhere in this module's own source, both at import time and again at the
top of :func:`run_pslu_flight` (:func:`assert_never_calls_ontology_miner`).

Silence-swap (module docstring continued): the 3 seeded A1' samples'
silent-audio variant is NOT generated or registered here -- that is
``rails.silence_swap``'s job (a ``core.model.SliceRecord``, registered via
``FrozenCoreClient.register_slice`` before any flight request runs, since
only a REAL ``FrozenCoreClient`` has a slice registry at all; ``MockCoreClient``
does not). This module's own job is narrower and generic over ANY
``CoreClient``: given a caller-supplied ``sample_id -> already-registered
media_relpath`` mapping, issue one EXTRA A1' request per silence-swap sample
with the audio content part's ``media_relpath`` swapped for the silent one,
same roster text, same instruction.
"""

from __future__ import annotations

import ast
import contextvars
import hashlib
import json
import math
import re
from collections import Counter, defaultdict, deque
from copy import deepcopy
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field, replace
from pathlib import Path
from queue import Queue
from threading import BoundedSemaphore
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

from ...contracts import ExecutionPlan
from ...core.base import Registry
from ...data.loader import LoaderError
from ...data.slurp import (
    SlurpTrainMaterial,
    SlurpTrainRecording,
    _probe_engineering_media,
    load_slurp_engineering_gate,
)
from ...reproduction.slurp_scoring import parse_slu_response
from ...core.tracing import TraceBuffer, set_current_trace_buffer
from ..adapters.slurp import SlurpAdapter, SlurpSample
from ..consumption import ConsumptionTrace, build_consumption_trace
from ..knowledge import (
    AgentStateArtifact,
    AgentStepTransition,
    FusionDecision,
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    RankedFacet,
    RankResult,
    ValueBundle,
)
from ..obs import AudioRef, ObsPacket
from ..runner import (
    AgentContactPlan,
    AgentLoopAdvance,
    AgentRuntimeContext,
    ContactDAGAdvance,
    run_bounded_contact_dag,
    run_speech_native_agent_loop,
)
from ..supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket
from ..task_adapter import TaskAdapter

PSLU_PHASE1_ARM = "A0"
PSLU_PHASE2_ARMS: tuple[str, ...] = ("A1", "A1p", "A2", "A3", "A4")
PSLU_ARMS: tuple[str, ...] = (PSLU_PHASE1_ARM, *PSLU_PHASE2_ARMS)

_PROBE_ID = "P-SLU"
_LEGAL_TIER = "legal"
_FORBIDDEN_ONTOLOGY_SYMBOL = "load_slurp_ontology"


class PsluFlightError(RuntimeError):
    """A P-SLU flight input is malformed, a roster table fails its own
    load-time legality checks, or the ontology-miner import guard tripped."""


@dataclass(frozen=True)
class SpeechNativeEngineeringSample:
    """Label-free runtime sample for preprocessing and packet equivalence."""

    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float
    media_relpath: str
    sample_rate_hz: int
    packet_id: str


@dataclass(frozen=True)
class SpeechNativeEngineeringGate:
    split_identity_hash: str
    runtime_view_sha256: str
    d1_media_supplement: str
    d1_media_supplement_sha256: str
    samples: tuple[SpeechNativeEngineeringSample, ...]


def load_speech_native_engineering_gate(
    path: Path,
    *,
    data_root: Path,
    expected_count: int = 8,
    expected_split_name: str = "ENG-GATE8",
    workers: int = 8,
    media_probe: Callable[[Path], tuple[str, float, int]] = _probe_engineering_media,
) -> SpeechNativeEngineeringGate:
    """Load the shared label-free ENG-GATE8 view for the P-SLU rail."""

    try:
        gate = load_slurp_engineering_gate(
            path,
            data_root=data_root,
            expected_count=expected_count,
            expected_split_name=expected_split_name,
            workers=workers,
            media_probe=media_probe,
        )
    except LoaderError as error:
        raise PsluFlightError(str(error)) from error
    return SpeechNativeEngineeringGate(
        split_identity_hash=gate.split_identity_hash,
        runtime_view_sha256=gate.runtime_view_sha256,
        d1_media_supplement=gate.d1_media_supplement,
        d1_media_supplement_sha256=gate.d1_media_supplement_sha256,
        samples=tuple(
            SpeechNativeEngineeringSample(
                sample_id=sample.sample_id,
                audio_ref=AudioRef(
                    path=sample.media_relpath,
                    sha256=sample.audio_sha256,
                ).validate(),
                audio_seconds=sample.audio_seconds,
                media_relpath=sample.media_relpath,
                sample_rate_hz=sample.sample_rate_hz,
                packet_id=sample.packet_id,
            )
            for sample in gate.samples
        ),
    )


SPEECH_NATIVE_KEY_REPRESENTATIONS = ("K0", "K1", "K2", "K3", "K4")
SPEECH_NATIVE_MATCHER_POLICIES = (
    "M0",
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "M7",
    "M8",
    "M9",
    "M10",
    "M11",
)
SPEECH_NATIVE_PROMPT_POLICIES = (
    "speech-native-json-copy-v2",
    "speech-native-json-copy-v3",
    "speech-native-json-copy-v4",
)
SPEECH_NATIVE_REQUEST_LAYOUTS = (
    "legacy-key-speech-v1",
    "slot-affine-speech-prefix-v1",
    "slot-affine-knowledge-speech-state-v1",
)
SPEECH_NATIVE_STABLE_SYSTEM_TEXT = (
    "Use the frozen speech observation and supplied knowledge to execute the final task "
    "instruction. Treat the speech observation as the primary query, keep opaque key ids "
    "exact, and return only the requested response shape."
)
SPEECH_NATIVE_VERIFIER_POLICIES = (
    "speech-native-compatibility-v1",
    "speech-native-contrastive-verifier-v2",
)
SPEECH_NATIVE_AGENT_AGGREGATORS = (
    "m3-majority-canonical-tie-v1",
    "m3-majority-primary-tie-v2",
    "m3-unanimous-primary-fallback-v3",
    "grounded-refined-primary-fallback-v1",
    "action-support-primary-control-v1",
    "pairwise-boundary-primary-control-v1",
    "factor-graph-primary-control-v1",
    "candidate-evidence-primary-control-v1",
    "adaptive-evidence-gap-primary-control-v1",
)
SPEECH_NATIVE_AGENT_POLICIES = (
    "m1-m3-disagreement-escalation-v1",
    "m1-m3-full-branch-explorer-v1",
    "knowledge-grounded-semantic-refinement-full-action-v1",
    "knowledge-grounded-semantic-refinement-schema-v2",
    "knowledge-grounded-semantic-refinement-schema-v3",
    "knowledge-grounded-multistate-action-support-v1",
    "speech-conditioned-pairwise-boundary-support-v1",
    "speech-conditioned-factor-graph-action-support-v1",
    "speech-conditioned-candidate-evidence-action-support-v1",
    "speech-conditioned-adaptive-evidence-gap-v1",
    "speech-conditioned-adaptive-evidence-gap-v2",
)
SPEECH_NATIVE_SCENARIO_DEFINITIONS: Mapping[str, str] = MappingProxyType(
    {
        "alarm": "Commands that create, change, inspect, or remove alarms and wake-up reminders.",
        "audio": "Commands that control audio volume, muting, or the active audio device.",
        "calendar": "Commands that create, change, inspect, or remove calendar events.",
        "cooking": "Commands asking for recipes, ingredients, cooking steps, or cooking timers.",
        "datetime": "Commands asking for the current date, time, day, or time in another place.",
        "email": "Commands that read, search, compose, send, or manage email messages.",
        "general": "General assistant-control commands and requests that do not fit a specialist domain.",
        "iot": "Commands that inspect or control connected home devices, lights, heating, or appliances.",
        "lists": "Commands that create, inspect, change, or remove shopping and task list entries.",
        "music": "Commands about songs, artists, albums, playlists, and music playback choices.",
        "news": "Commands asking for news reports, headlines, or updates on current events.",
        "play": "Commands that start, pause, resume, stop, or navigate playable media.",
        "qa": "Open factual questions seeking an answer rather than a device or service action.",
        "recommendation": "Commands asking the assistant to recommend an option, place, or activity.",
        "social": "Commands that read, compose, send, or manage social and instant messages.",
        "takeaway": "Commands for finding, ordering, or tracking prepared food for delivery or pickup.",
        "transport": "Commands about routes, traffic, travel duration, public transit, or vehicle travel.",
        "weather": "Commands asking for weather conditions, forecasts, temperature, rain, or wind.",
    }
)
SPEECH_NATIVE_SCENARIO_CONTRASTS: Mapping[str, str] = MappingProxyType(
    {
        "alarm": "Exclude calendar appointments and generic time questions.",
        "audio": "Exclude choosing music content and generic play or pause operations.",
        "calendar": "Exclude wake-up alarms and task-list entries.",
        "cooking": "Exclude restaurant delivery and general factual questions.",
        "datetime": "Exclude alarms, calendar events, and weather forecasts.",
        "email": "Exclude social or instant messages.",
        "general": "Use a specialist key whenever a specific domain is expressed.",
        "iot": "Exclude media playback and non-device factual questions.",
        "lists": "Exclude calendar events and reminders implemented as alarms.",
        "music": "Exclude pure volume control and generic media transport controls.",
        "news": "Exclude weather forecasts and open-domain factual questions.",
        "play": "Exclude selecting music content and changing audio volume.",
        "qa": "Exclude recommendations and commands that operate a service or device.",
        "recommendation": "Exclude direct factual questions and explicit takeaway orders.",
        "social": "Exclude email messages.",
        "takeaway": "Exclude cooking instructions and general place recommendations.",
        "transport": "Exclude weather and generic time questions.",
        "weather": "Exclude news, transport status, and generic date or time questions.",
    }
)

SPEECH_NATIVE_KNOWLEDGE_POLICY_ID = "slurp-action-stratified-specificity-v1"
SPEECH_NATIVE_INFORMATION_COMPLETE_KNOWLEDGE_POLICY_ID = (
    "slurp-action-complete-specificity-v2"
)
SPEECH_NATIVE_KNOWLEDGE_POLICY_IDS = (
    SPEECH_NATIVE_KNOWLEDGE_POLICY_ID,
    SPEECH_NATIVE_INFORMATION_COMPLETE_KNOWLEDGE_POLICY_ID,
)
SPEECH_NATIVE_BOUNDARY_POLICY_IDS = (
    "ranked-pair-signal-v1",
    "shared-action-entity-boundaries-v2",
    "shared-signature-lexical-boundaries-v3",
    "shared-signature-complete-boundaries-v4",
)
_STABLE_SHARED_ACTION_MIN_SUPPORT = 5
_DISCRIMINATIVE_ENTITY_MIN_SUPPORT = 2
_DISCRIMINATIVE_ENTITY_MIN_PREVALENCE = 0.01
_DISCRIMINATIVE_ENTITY_MIN_RATE_RATIO = 5.0
_DISCRIMINATIVE_ENTITY_MAX_PER_SIDE = 3
_SIGNATURE_LEXICAL_CUE_COUNT = 8
SPEECH_NATIVE_ACTION_FACET_DESCRIPTIONS: Mapping[tuple[str, str], str] = (
    MappingProxyType(
        {
            ("alarm", "set"): "create or change an alarm",
            ("alarm", "query"): "inspect existing alarms",
            ("alarm", "remove"): "cancel or remove an alarm",
            ("audio", "volume_up"): "increase audio volume",
            ("audio", "volume_mute"): "mute or unmute audio",
            ("audio", "volume_down"): "decrease audio volume",
            ("audio", "volume_other"): "set or inspect another volume state",
            ("calendar", "set"): "create or change a calendar event",
            ("calendar", "query"): "inspect calendar events or schedules",
            ("calendar", "remove"): "cancel or remove a calendar event",
            ("cooking", "recipe"): "request a recipe or cooking procedure",
            ("cooking", "query"): "ask another cooking-related question",
            ("datetime", "query"): "ask for a date, day, time, or timezone",
            ("datetime", "convert"): "convert between times or timezones",
            ("email", "query"): "read or search email",
            ("email", "sendemail"): "compose, reply to, or send email",
            ("email", "querycontact"): "look up an email contact",
            ("email", "addcontact"): "add an email contact",
            ("general", "quirky"): (
                "handle an open-ended assistant request without a stable "
                "specialist target"
            ),
            ("general", "joke"): "tell or discuss a joke",
            ("general", "greet"): "handle a greeting",
            ("iot", "hue_lightoff"): "turn a connected light off",
            ("iot", "hue_lightchange"): "change a connected light's color or state",
            ("iot", "coffee"): "operate a connected coffee appliance",
            ("iot", "cleaning"): "operate a connected cleaning appliance",
            ("iot", "hue_lightdim"): "dim a connected light",
            ("iot", "hue_lightup"): "brighten a connected light",
            ("iot", "wemo_off"): "turn a connected Wemo device off",
            ("iot", "wemo_on"): "turn a connected Wemo device on",
            ("iot", "hue_lighton"): "turn a connected light on",
            ("lists", "query"): "inspect a shopping or task list",
            ("lists", "createoradd"): "create a list or add a list item",
            ("lists", "remove"): "remove a list or list item",
            ("music", "query"): "identify or inspect music content",
            ("music", "likeness"): "like, save, or favorite music content",
            ("music", "settings"): "change a music preference or setting",
            ("music", "dislikeness"): "dislike music content",
            ("news", "query"): "request news or a current-event update",
            ("play", "music"): "play selected music",
            ("play", "radio"): "play a radio station or channel",
            ("play", "podcasts"): "play or navigate a podcast",
            ("play", "audiobook"): "play or navigate an audiobook",
            ("play", "game"): "start or play a game",
            ("qa", "factoid"): "ask an open factual question",
            ("qa", "definition"): "ask for a definition",
            ("qa", "stock"): "ask for stock information",
            ("qa", "currency"): "ask for currency or exchange-rate information",
            ("qa", "maths"): "ask for a mathematical result",
            ("recommendation", "events"): "request an event recommendation",
            ("recommendation", "locations"): "request a place recommendation",
            ("recommendation", "movies"): "request a movie recommendation",
            ("social", "post"): "compose or publish a social post",
            ("social", "query"): "read or inspect social messages or activity",
            ("takeaway", "order"): "place or track a prepared-food order",
            ("takeaway", "query"): "find prepared-food delivery or pickup options",
            ("transport", "query"): "inspect routes, transit, or travel status",
            ("transport", "ticket"): "find or book a transport ticket",
            ("transport", "traffic"): "inspect road traffic",
            ("transport", "taxi"): "request or book a taxi",
            ("weather", "query"): "request weather conditions or a forecast",
        }
    )
)


@dataclass(frozen=True)
class KeyCardV1:
    """One opaque routing key and its train-only maintainable text card.

    ``value_label`` is deterministic post-model metadata. Renderers never
    expose it for K1/K2/K3/K4; the frozen core selects ``key_id`` and the
    caller performs the final mapping after the response.
    """

    key_id: str
    definition: str
    positive_examples: tuple[str, ...]
    contrastive_boundary: str | None
    value_label: str

    def validate(self) -> "KeyCardV1":
        if not self.key_id.startswith("K") or not self.key_id[1:].isdigit():
            raise PsluFlightError(f"invalid opaque key_id {self.key_id!r}")
        if not self.definition.strip():
            raise PsluFlightError(f"key {self.key_id}: definition must be non-empty")
        if not self.positive_examples or any(
            not item.strip() for item in self.positive_examples
        ):
            raise PsluFlightError(
                f"key {self.key_id}: positive_examples must be non-empty strings"
            )
        if (
            self.contrastive_boundary is not None
            and not self.contrastive_boundary.strip()
        ):
            raise PsluFlightError(
                f"key {self.key_id}: contrastive_boundary must be non-empty or None"
            )
        if not self.value_label.strip():
            raise PsluFlightError(f"key {self.key_id}: value_label must be non-empty")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "key_id": self.key_id,
            "definition": self.definition,
            "positive_examples": list(self.positive_examples),
            "contrastive_boundary": self.contrastive_boundary,
            "value_label": self.value_label,
        }


_DECISION_FACTOR_KINDS = ("domain", "operation", "target", "constraint")


def _is_numbered_id(value: object, prefix: str) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(prefix)
        and len(value) > len(prefix)
        and value[len(prefix) :].isdigit()
    )


def _validate_provenance_ids(provenance_ids: tuple[str, ...], *, context: str) -> None:
    if (
        not provenance_ids
        or len(set(provenance_ids)) != len(provenance_ids)
        or any(not isinstance(item, str) or not item.strip() for item in provenance_ids)
    ):
        raise PsluFlightError(
            f"{context} provenance_ids must be unique non-empty strings"
        )


@dataclass(frozen=True)
class DecisionFactorV1:
    """One maintainable, query-selectable knowledge factor."""

    factor_id: str
    kind: str
    statement: str
    key_ids: tuple[str, ...]
    provenance_ids: tuple[str, ...]

    def validate(self, allowed_key_ids: set[str]) -> "DecisionFactorV1":
        if not _is_numbered_id(self.factor_id, "F"):
            raise PsluFlightError(f"invalid decision factor_id {self.factor_id!r}")
        if self.kind not in _DECISION_FACTOR_KINDS:
            raise PsluFlightError(
                f"factor {self.factor_id}: kind must be one of {_DECISION_FACTOR_KINDS}"
            )
        if not isinstance(self.statement, str) or not self.statement.strip():
            raise PsluFlightError(
                f"factor {self.factor_id}: statement must be non-empty"
            )
        if (
            not self.key_ids
            or len(set(self.key_ids)) != len(self.key_ids)
            or any(not isinstance(key_id, str) or not key_id for key_id in self.key_ids)
        ):
            raise PsluFlightError(
                f"factor {self.factor_id}: key_ids must be unique non-empty strings"
            )
        unknown = set(self.key_ids) - allowed_key_ids
        if unknown:
            raise PsluFlightError(
                f"factor {self.factor_id} references unknown key ids {sorted(unknown)}"
            )
        _validate_provenance_ids(
            self.provenance_ids, context=f"factor {self.factor_id}"
        )
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "factor_id": self.factor_id,
            "kind": self.kind,
            "statement": self.statement,
            "key_ids": list(self.key_ids),
            "provenance_ids": list(self.provenance_ids),
        }


@dataclass(frozen=True)
class DecisionBoundaryV1:
    """One directed rendering of an unordered hard-negative key boundary."""

    boundary_id: str
    left_key_id: str
    right_key_id: str
    left_factor_ids: tuple[str, ...]
    right_factor_ids: tuple[str, ...]
    left_exclusion: str
    right_exclusion: str
    provenance_ids: tuple[str, ...]

    def validate(
        self,
        *,
        allowed_key_ids: set[str],
        factors_by_id: Mapping[str, DecisionFactorV1],
    ) -> "DecisionBoundaryV1":
        if not _is_numbered_id(self.boundary_id, "B"):
            raise PsluFlightError(f"invalid decision boundary_id {self.boundary_id!r}")
        if (
            self.left_key_id == self.right_key_id
            or self.left_key_id not in allowed_key_ids
            or self.right_key_id not in allowed_key_ids
        ):
            raise PsluFlightError(
                f"boundary {self.boundary_id}: endpoints must be two distinct known keys"
            )
        for side, key_id, factor_ids in (
            ("left", self.left_key_id, self.left_factor_ids),
            ("right", self.right_key_id, self.right_factor_ids),
        ):
            if not factor_ids or len(set(factor_ids)) != len(factor_ids):
                raise PsluFlightError(
                    f"boundary {self.boundary_id}: {side} factor ids must be non-empty and unique"
                )
            for factor_id in factor_ids:
                factor = factors_by_id.get(factor_id)
                if factor is None or key_id not in factor.key_ids:
                    raise PsluFlightError(
                        f"boundary {self.boundary_id}: {side} factor {factor_id!r} "
                        f"does not support endpoint {key_id}"
                    )
        if (
            not isinstance(self.left_exclusion, str)
            or not self.left_exclusion.strip()
            or not isinstance(self.right_exclusion, str)
            or not self.right_exclusion.strip()
        ):
            raise PsluFlightError(
                f"boundary {self.boundary_id}: exclusions must be non-empty strings"
            )
        _validate_provenance_ids(
            self.provenance_ids, context=f"boundary {self.boundary_id}"
        )
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "boundary_id": self.boundary_id,
            "left_key_id": self.left_key_id,
            "right_key_id": self.right_key_id,
            "left_factor_ids": list(self.left_factor_ids),
            "right_factor_ids": list(self.right_factor_ids),
            "left_exclusion": self.left_exclusion,
            "right_exclusion": self.right_exclusion,
            "provenance_ids": list(self.provenance_ids),
        }


@dataclass(frozen=True)
class DecisionGraphNeighborhoodV1:
    key_ids: tuple[str, ...]
    factor_ids: tuple[str, ...]
    boundary_ids: tuple[str, ...]


@dataclass(frozen=True)
class DecisionGraphV1:
    """A small, hashable factor graph over opaque routing keys."""

    graph_id: str
    factors: tuple[DecisionFactorV1, ...]
    boundaries: tuple[DecisionBoundaryV1, ...]

    def validate(self, key_cards: Sequence[KeyCardV1]) -> "DecisionGraphV1":
        cards = _validated_key_cards(key_cards)
        allowed_key_ids = {card.key_id for card in cards}
        if (
            not isinstance(self.graph_id, str)
            or not self.graph_id
            or any(
                character not in "abcdefghijklmnopqrstuvwxyz0123456789-"
                for character in self.graph_id
            )
        ):
            raise PsluFlightError(
                "decision graph_id must use lowercase letters, digits, and dashes"
            )
        if not self.factors:
            raise PsluFlightError("decision graph must contain factor nodes")
        factor_ids = [factor.factor_id for factor in self.factors]
        if len(set(factor_ids)) != len(factor_ids):
            raise PsluFlightError("decision graph contains duplicate factor ids")
        factors_by_id = {
            factor.factor_id: factor.validate(allowed_key_ids)
            for factor in self.factors
        }
        covered_keys = {key_id for factor in self.factors for key_id in factor.key_ids}
        missing_keys = allowed_key_ids - covered_keys
        if missing_keys:
            raise PsluFlightError(
                f"decision graph lacks factor coverage for keys {sorted(missing_keys)}"
            )
        boundary_ids = [boundary.boundary_id for boundary in self.boundaries]
        if len(set(boundary_ids)) != len(boundary_ids):
            raise PsluFlightError("decision graph contains duplicate boundary ids")
        boundary_pairs: set[frozenset[str]] = set()
        for boundary in self.boundaries:
            boundary.validate(
                allowed_key_ids=allowed_key_ids,
                factors_by_id=factors_by_id,
            )
            pair = frozenset((boundary.left_key_id, boundary.right_key_id))
            if pair in boundary_pairs:
                raise PsluFlightError(
                    "decision graph contains a duplicate unordered boundary pair"
                )
            boundary_pairs.add(pair)
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "schema": "saea-decision-graph-v1",
            "graph_id": self.graph_id,
            "factors": [factor.as_json() for factor in self.factors],
            "boundaries": [boundary.as_json() for boundary in self.boundaries],
        }

    def neighborhood(
        self, candidate_key_ids: Sequence[str]
    ) -> DecisionGraphNeighborhoodV1:
        candidates = tuple(candidate_key_ids)
        if not candidates or len(set(candidates)) != len(candidates):
            raise PsluFlightError(
                "decision graph candidates must be non-empty and unique"
            )
        known_keys = {key_id for factor in self.factors for key_id in factor.key_ids}
        unknown = set(candidates) - known_keys
        if unknown:
            raise PsluFlightError(
                f"decision graph neighborhood references unknown keys {sorted(unknown)}"
            )
        incident = tuple(
            boundary
            for boundary in self.boundaries
            if boundary.left_key_id in candidates or boundary.right_key_id in candidates
        )
        expanded_keys = list(candidates)
        for boundary in incident:
            for key_id in (boundary.left_key_id, boundary.right_key_id):
                if key_id not in expanded_keys:
                    expanded_keys.append(key_id)
        required_factor_ids = {
            factor.factor_id
            for factor in self.factors
            if any(key_id in candidates for key_id in factor.key_ids)
        }
        for boundary in incident:
            required_factor_ids.update(boundary.left_factor_ids)
            required_factor_ids.update(boundary.right_factor_ids)
        return DecisionGraphNeighborhoodV1(
            key_ids=tuple(expanded_keys),
            factor_ids=tuple(
                factor.factor_id
                for factor in self.factors
                if factor.factor_id in required_factor_ids
            ),
            boundary_ids=tuple(boundary.boundary_id for boundary in incident),
        )


@dataclass(frozen=True)
class FactorLinkStateV1:
    factor_ids: tuple[str, ...]
    boundary_id: str | None

    def as_json(self) -> dict[str, object]:
        return {
            "factor_ids": list(self.factor_ids),
            "boundary_id": self.boundary_id or "NONE",
        }


@dataclass(frozen=True)
class CandidateActionStateV1:
    key_id: str
    factor_ids: tuple[str, ...]


@dataclass(frozen=True)
class DecisionGraphExpansionV1:
    key_ids: tuple[str, ...]
    distance_by_key: Mapping[str, int]


@dataclass(frozen=True)
class CandidateSupportStateV1:
    compatible: bool
    confidence: int
    factor_ids: tuple[str, ...]


@dataclass(frozen=True)
class CandidateCounterevidenceStateV1:
    contradicted: bool
    confidence: int
    boundary_ids: tuple[str, ...]


def _candidate_factor_ids(
    graph: DecisionGraphV1, candidate_key_id: str
) -> tuple[str, ...]:
    factor_ids = tuple(
        factor.factor_id
        for factor in graph.factors
        if candidate_key_id in factor.key_ids
    )
    if not factor_ids:
        raise PsluFlightError(
            f"candidate evidence has no factors for key {candidate_key_id!r}"
        )
    return factor_ids


def _candidate_boundary_ids(
    graph: DecisionGraphV1, candidate_key_id: str
) -> tuple[str, ...]:
    known_keys = {key_id for factor in graph.factors for key_id in factor.key_ids}
    if candidate_key_id not in known_keys:
        raise PsluFlightError(
            f"candidate evidence references unknown key {candidate_key_id!r}"
        )
    return tuple(
        boundary.boundary_id
        for boundary in graph.boundaries
        if candidate_key_id in {boundary.left_key_id, boundary.right_key_id}
    )


def expand_decision_graph_neighborhood(
    *,
    graph: DecisionGraphV1,
    initial_key_ids: Sequence[str],
    cap: int,
) -> DecisionGraphExpansionV1:
    """Expand all one-hop factor and boundary neighbors deterministically."""

    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise PsluFlightError("candidate evidence expansion cap must be positive")
    initial = tuple(initial_key_ids)
    if not initial or len(set(initial)) != len(initial) or len(initial) > cap:
        raise PsluFlightError(
            "candidate evidence expansion requires unique initial keys within the cap"
        )
    known_keys = {key_id for factor in graph.factors for key_id in factor.key_ids}
    unknown = set(initial) - known_keys
    if unknown:
        raise PsluFlightError(
            f"candidate evidence expansion references unknown keys {sorted(unknown)}"
        )
    neighbors: set[str] = set()
    initial_set = set(initial)
    for factor in graph.factors:
        if initial_set.intersection(factor.key_ids):
            neighbors.update(factor.key_ids)
    for boundary in graph.boundaries:
        if boundary.left_key_id in initial_set or boundary.right_key_id in initial_set:
            neighbors.update((boundary.left_key_id, boundary.right_key_id))
    ordered = (*initial, *sorted(neighbors - initial_set))[:cap]
    return DecisionGraphExpansionV1(
        key_ids=tuple(ordered),
        distance_by_key={
            key_id: 0 if key_id in initial_set else 1 for key_id in ordered
        },
    )


def expand_decision_graph_candidates(
    *,
    graph: DecisionGraphV1,
    initial_key_ids: Sequence[str],
    state: FactorLinkStateV1,
    cap: int,
) -> DecisionGraphExpansionV1:
    """Expand selected graph evidence with deterministic distance/rank ties."""

    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise PsluFlightError("decision graph expansion cap must be positive")
    initial = tuple(initial_key_ids)
    if not initial or len(set(initial)) != len(initial) or len(initial) > cap:
        raise PsluFlightError(
            "decision graph expansion requires unique initial keys within the cap"
        )
    factors_by_id = {factor.factor_id: factor for factor in graph.factors}
    boundaries_by_id = {boundary.boundary_id: boundary for boundary in graph.boundaries}
    known_keys = {key_id for factor in graph.factors for key_id in factor.key_ids}
    unknown_initial = set(initial) - known_keys
    if unknown_initial:
        raise PsluFlightError(
            f"decision graph expansion references unknown initial keys {sorted(unknown_initial)}"
        )
    if (
        not state.factor_ids
        or len(set(state.factor_ids)) != len(state.factor_ids)
        or any(factor_id not in factors_by_id for factor_id in state.factor_ids)
    ):
        raise PsluFlightError("decision graph expansion received invalid factor ids")
    if state.boundary_id is not None and state.boundary_id not in boundaries_by_id:
        raise PsluFlightError(
            "decision graph expansion received an invalid boundary id"
        )
    ordered = list(initial)
    distance_by_key: dict[str, int] = {key_id: 0 for key_id in initial}
    for factor_id in state.factor_ids:
        for key_id in factors_by_id[factor_id].key_ids:
            if key_id not in distance_by_key:
                distance_by_key[key_id] = 1
                ordered.append(key_id)
    if state.boundary_id is not None:
        boundary = boundaries_by_id[state.boundary_id]
        for key_id in (boundary.left_key_id, boundary.right_key_id):
            if key_id not in distance_by_key:
                distance_by_key[key_id] = 1
                ordered.append(key_id)
    selected = tuple(ordered[:cap])
    return DecisionGraphExpansionV1(
        key_ids=selected,
        distance_by_key={key_id: distance_by_key[key_id] for key_id in selected},
    )


def decision_boundary_path(
    *,
    graph: DecisionGraphV1,
    source_key_id: str,
    target_key_id: str,
    max_edges: int,
) -> tuple[str, ...]:
    """Return the first graph-order boundary path within a small hop cap."""

    if isinstance(max_edges, bool) or not isinstance(max_edges, int) or max_edges <= 0:
        raise PsluFlightError("decision boundary path max_edges must be positive")
    known_keys = {key_id for factor in graph.factors for key_id in factor.key_ids}
    if source_key_id not in known_keys or target_key_id not in known_keys:
        raise PsluFlightError("decision boundary path endpoints must be known keys")
    if source_key_id == target_key_id:
        return ()
    frontier: deque[tuple[str, tuple[str, ...], frozenset[str]]] = deque(
        ((source_key_id, (), frozenset((source_key_id,))),)
    )
    while frontier:
        key_id, path, visited = frontier.popleft()
        if len(path) >= max_edges:
            continue
        for boundary in graph.boundaries:
            if boundary.left_key_id == key_id:
                neighbor = boundary.right_key_id
            elif boundary.right_key_id == key_id:
                neighbor = boundary.left_key_id
            else:
                continue
            if neighbor in visited:
                continue
            next_path = (*path, boundary.boundary_id)
            if neighbor == target_key_id:
                return next_path
            frontier.append((neighbor, next_path, visited | {neighbor}))
    return ()


def render_factor_link_state(
    *, graph: DecisionGraphV1, state: FactorLinkStateV1
) -> str:
    """Render only ids selected by the factor-link action."""

    factors_by_id = {factor.factor_id: factor for factor in graph.factors}
    boundaries_by_id = {boundary.boundary_id: boundary for boundary in graph.boundaries}
    if (
        not state.factor_ids
        or any(factor_id not in factors_by_id for factor_id in state.factor_ids)
        or len(set(state.factor_ids)) != len(state.factor_ids)
    ):
        raise PsluFlightError("factor-link state contains invalid factor ids")
    if state.boundary_id is not None and state.boundary_id not in boundaries_by_id:
        raise PsluFlightError("factor-link state contains an invalid boundary id")
    lines = ["Selected factor nodes:"]
    for factor_id in state.factor_ids:
        factor = factors_by_id[factor_id]
        lines.extend(
            (
                f"[{factor.factor_id}] kind={factor.kind}",
                f"Statement: {factor.statement}",
                f"Linked keys: {','.join(factor.key_ids)}",
            )
        )
    lines.append("Selected boundary edge:")
    if state.boundary_id is None:
        lines.append("NONE")
    else:
        boundary = boundaries_by_id[state.boundary_id]
        lines.extend(
            (
                f"[{boundary.boundary_id}] endpoints="
                f"{boundary.left_key_id},{boundary.right_key_id}",
                f"{boundary.left_key_id} exclusion: {boundary.left_exclusion}",
                f"{boundary.right_key_id} exclusion: {boundary.right_exclusion}",
            )
        )
    return "\n".join(lines)


def render_decision_graph_neighborhood(
    *,
    graph: DecisionGraphV1,
    key_cards: Sequence[KeyCardV1],
    candidate_key_ids: Sequence[str],
) -> str:
    """Render one auditable graph neighborhood without label metadata."""

    graph.validate(key_cards)
    neighborhood = graph.neighborhood(candidate_key_ids)
    factors_by_id = {factor.factor_id: factor for factor in graph.factors}
    boundaries_by_id = {boundary.boundary_id: boundary for boundary in graph.boundaries}
    lines = [f"Decision graph: {graph.graph_id}", "Factor nodes:"]
    for factor_id in neighborhood.factor_ids:
        factor = factors_by_id[factor_id]
        lines.extend(
            (
                f"[{factor.factor_id}] kind={factor.kind}",
                f"Statement: {factor.statement}",
                f"Linked keys: {','.join(factor.key_ids)}",
            )
        )
    lines.append("Boundary edges:")
    if not neighborhood.boundary_ids:
        lines.append("NONE")
    for boundary_id in neighborhood.boundary_ids:
        boundary = boundaries_by_id[boundary_id]
        lines.extend(
            (
                f"[{boundary.boundary_id}] endpoints="
                f"{boundary.left_key_id},{boundary.right_key_id}",
                f"{boundary.left_key_id} factors: {','.join(boundary.left_factor_ids)}",
                f"{boundary.left_key_id} exclusion: {boundary.left_exclusion}",
                f"{boundary.right_key_id} factors: "
                f"{','.join(boundary.right_factor_ids)}",
                f"{boundary.right_key_id} exclusion: {boundary.right_exclusion}",
            )
        )
    return "\n".join(lines)


def factor_link_response_format(
    *,
    graph: DecisionGraphV1,
    key_cards: Sequence[KeyCardV1],
    candidate_key_ids: Sequence[str],
) -> dict[str, object]:
    graph.validate(key_cards)
    neighborhood = graph.neighborhood(candidate_key_ids)
    if len(neighborhood.factor_ids) < 2:
        raise PsluFlightError(
            "factor-link neighborhood must expose at least two factor ids"
        )
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "speech_native_factor_link_state",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "factor_ids": {
                        "type": "array",
                        "items": {"enum": list(neighborhood.factor_ids)},
                        "minItems": 2,
                        "maxItems": min(5, len(neighborhood.factor_ids)),
                        "uniqueItems": True,
                    },
                    "boundary_id": {"enum": ["NONE", *neighborhood.boundary_ids]},
                },
                "required": ["factor_ids", "boundary_id"],
                "additionalProperties": False,
            },
        },
    }


def parse_factor_link_state(
    text: str,
    *,
    graph: DecisionGraphV1,
    key_cards: Sequence[KeyCardV1],
    candidate_key_ids: Sequence[str],
) -> FactorLinkStateV1 | None:
    graph.validate(key_cards)
    neighborhood = graph.neighborhood(candidate_key_ids)
    document = _response_object(text)
    if document is None or set(document) != {"factor_ids", "boundary_id"}:
        return None
    factor_ids = document.get("factor_ids")
    boundary_id = document.get("boundary_id")
    if (
        not isinstance(factor_ids, list)
        or not 2 <= len(factor_ids) <= min(5, len(neighborhood.factor_ids))
        or any(not isinstance(factor_id, str) for factor_id in factor_ids)
        or len(set(factor_ids)) != len(factor_ids)
        or not set(factor_ids).issubset(neighborhood.factor_ids)
        or not isinstance(boundary_id, str)
        or boundary_id not in {"NONE", *neighborhood.boundary_ids}
    ):
        return None
    return FactorLinkStateV1(
        factor_ids=tuple(factor_ids),
        boundary_id=None if boundary_id == "NONE" else boundary_id,
    )


def candidate_action_state_response_format(
    *,
    graph: DecisionGraphV1,
    candidate_key_ids: Sequence[str],
    key_conditioned: bool = False,
) -> dict[str, object]:
    candidates = tuple(candidate_key_ids)
    if not candidates or len(set(candidates)) != len(candidates):
        raise PsluFlightError(
            "candidate action state requires unique candidate key ids"
        )
    known = {key_id for factor in graph.factors for key_id in factor.key_ids}
    if set(candidates) - known:
        raise PsluFlightError("candidate action state references unknown keys")
    factor_ids = tuple(
        factor.factor_id
        for factor in graph.factors
        if any(key_id in candidates for key_id in factor.key_ids)
    )
    if not factor_ids:
        raise PsluFlightError("candidate action state lacks factor knowledge")
    if key_conditioned:
        factors_by_key = {
            key_id: tuple(
                factor.factor_id for factor in graph.factors if key_id in factor.key_ids
            )
            for key_id in candidates
        }
        operations_by_key = {
            key_id: tuple(
                factor.factor_id
                for factor in graph.factors
                if key_id in factor.key_ids and factor.kind == "operation"
            )
            for key_id in candidates
        }
        missing_operations = tuple(
            key_id for key_id in candidates if not operations_by_key[key_id]
        )
        if missing_operations:
            raise PsluFlightError(
                "key-conditioned candidate action state lacks operation factors for "
                + ",".join(missing_operations)
            )
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "speech_native_candidate_action_state_v2",
                "strict": True,
                "schema": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "key_id": {"const": key_id},
                                "factor_ids": {
                                    "type": "array",
                                    "prefixItems": [
                                        {"enum": list(operations_by_key[key_id])}
                                    ],
                                    "items": {"enum": list(factors_by_key[key_id])},
                                    "minItems": 1,
                                    "maxItems": min(3, len(factors_by_key[key_id])),
                                    "uniqueItems": True,
                                },
                            },
                            "required": ["key_id", "factor_ids"],
                            "additionalProperties": False,
                        }
                        for key_id in candidates
                    ]
                },
            },
        }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "speech_native_candidate_action_state",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "key_id": {"enum": list(candidates)},
                    "factor_ids": {
                        "type": "array",
                        "items": {"enum": list(factor_ids)},
                        "minItems": 1,
                        "maxItems": min(3, len(factor_ids)),
                        "uniqueItems": True,
                    },
                },
                "required": ["key_id", "factor_ids"],
                "additionalProperties": False,
            },
        },
    }


def parse_candidate_action_state(
    text: str,
    *,
    graph: DecisionGraphV1,
    candidate_key_ids: Sequence[str],
) -> CandidateActionStateV1 | None:
    candidates = tuple(candidate_key_ids)
    document = _response_object(text)
    if document is None or set(document) != {"key_id", "factor_ids"}:
        return None
    key_id = document.get("key_id")
    factor_ids = document.get("factor_ids")
    factors_by_id = {factor.factor_id: factor for factor in graph.factors}
    if (
        not isinstance(key_id, str)
        or key_id not in candidates
        or not isinstance(factor_ids, list)
        or not 1 <= len(factor_ids) <= 3
        or len(set(factor_ids)) != len(factor_ids)
        or not all(
            isinstance(factor_id, str)
            and factor_id in factors_by_id
            and key_id in factors_by_id[factor_id].key_ids
            for factor_id in factor_ids
        )
        or not any(
            factors_by_id[factor_id].kind == "operation" for factor_id in factor_ids
        )
    ):
        return None
    return CandidateActionStateV1(key_id=key_id, factor_ids=tuple(factor_ids))


def _render_candidate_action_context(
    *, graph: DecisionGraphV1, candidate_key_ids: Sequence[str]
) -> str:
    candidates = set(candidate_key_ids)
    lines = ["Candidate-local task factors:"]
    for factor in graph.factors:
        linked = tuple(key_id for key_id in factor.key_ids if key_id in candidates)
        if not linked:
            continue
        lines.extend(
            (
                f"[{factor.factor_id}] kind={factor.kind}",
                f"Statement: {factor.statement}",
                f"Linked keys: {','.join(linked)}",
            )
        )
    return "\n".join(lines)


def _decision_boundary_for_pair(
    *, graph: DecisionGraphV1, left_key_id: str, right_key_id: str
) -> DecisionBoundaryV1 | None:
    pair = {left_key_id, right_key_id}
    return next(
        (
            boundary
            for boundary in graph.boundaries
            if {boundary.left_key_id, boundary.right_key_id} == pair
        ),
        None,
    )


def _render_adaptive_boundary_context(
    *,
    boundary: DecisionBoundaryV1,
    action_state: CandidateActionStateV1,
) -> str:
    return "\n".join(
        (
            "Agent state from the preceding speech-conditioned action-factor step:",
            f"candidate_key_id={action_state.key_id}",
            f"supported_factor_ids={','.join(action_state.factor_ids)}",
            "New pair-specific boundary knowledge:",
            f"[{boundary.boundary_id}] endpoints="
            f"{boundary.left_key_id},{boundary.right_key_id}",
            f"{boundary.left_key_id} exclusion: {boundary.left_exclusion}",
            f"{boundary.right_key_id} exclusion: {boundary.right_exclusion}",
        )
    )


def candidate_support_response_format(
    *, graph: DecisionGraphV1, candidate_key_id: str
) -> dict[str, object]:
    factor_ids = _candidate_factor_ids(graph, candidate_key_id)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "speech_native_candidate_support",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "compatible": {"type": "boolean"},
                    "confidence": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "factor_ids": {
                        "type": "array",
                        "items": {"enum": list(factor_ids)},
                        "minItems": 1,
                        "maxItems": min(3, len(factor_ids)),
                        "uniqueItems": True,
                    },
                },
                "required": ["compatible", "confidence", "factor_ids"],
                "additionalProperties": False,
            },
        },
    }


def parse_candidate_support_state(
    text: str,
    *,
    graph: DecisionGraphV1,
    candidate_key_id: str,
) -> CandidateSupportStateV1 | None:
    allowed_factor_ids = set(_candidate_factor_ids(graph, candidate_key_id))
    document = _response_object(text)
    if document is None or set(document) != {
        "compatible",
        "confidence",
        "factor_ids",
    }:
        return None
    compatible = document.get("compatible")
    confidence = document.get("confidence")
    factor_ids = document.get("factor_ids")
    if (
        not isinstance(compatible, bool)
        or isinstance(confidence, bool)
        or not isinstance(confidence, int)
        or not 0 <= confidence <= 100
        or not isinstance(factor_ids, list)
        or not 1 <= len(factor_ids) <= min(3, len(allowed_factor_ids))
        or len(set(factor_ids)) != len(factor_ids)
        or not all(
            isinstance(factor_id, str) and factor_id in allowed_factor_ids
            for factor_id in factor_ids
        )
    ):
        return None
    return CandidateSupportStateV1(
        compatible=compatible,
        confidence=confidence,
        factor_ids=tuple(factor_ids),
    )


def candidate_counterevidence_response_format(
    *, graph: DecisionGraphV1, candidate_key_id: str
) -> dict[str, object]:
    boundary_ids = _candidate_boundary_ids(graph, candidate_key_id)
    boundary_items: dict[str, object] = (
        {"enum": list(boundary_ids)} if boundary_ids else {"type": "string"}
    )
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "speech_native_candidate_counterevidence",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "contradicted": {"type": "boolean"},
                    "confidence": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "boundary_ids": {
                        "type": "array",
                        "items": boundary_items,
                        "minItems": 0,
                        "maxItems": min(2, len(boundary_ids)),
                        "uniqueItems": True,
                    },
                },
                "required": ["contradicted", "confidence", "boundary_ids"],
                "additionalProperties": False,
            },
        },
    }


def parse_candidate_counterevidence_state(
    text: str,
    *,
    graph: DecisionGraphV1,
    candidate_key_id: str,
) -> CandidateCounterevidenceStateV1 | None:
    allowed_boundary_ids = set(_candidate_boundary_ids(graph, candidate_key_id))
    document = _response_object(text)
    if document is None or set(document) != {
        "contradicted",
        "confidence",
        "boundary_ids",
    }:
        return None
    contradicted = document.get("contradicted")
    confidence = document.get("confidence")
    boundary_ids = document.get("boundary_ids")
    if (
        not isinstance(contradicted, bool)
        or isinstance(confidence, bool)
        or not isinstance(confidence, int)
        or not 0 <= confidence <= 100
        or not isinstance(boundary_ids, list)
        or len(boundary_ids) > min(2, len(allowed_boundary_ids))
        or len(set(boundary_ids)) != len(boundary_ids)
        or not all(
            isinstance(boundary_id, str) and boundary_id in allowed_boundary_ids
            for boundary_id in boundary_ids
        )
    ):
        return None
    return CandidateCounterevidenceStateV1(
        contradicted=contradicted,
        confidence=confidence,
        boundary_ids=tuple(boundary_ids),
    )


def _render_candidate_factor_context(
    *, graph: DecisionGraphV1, candidate_key_id: str
) -> str:
    allowed = set(_candidate_factor_ids(graph, candidate_key_id))
    lines = [f"Candidate {candidate_key_id} factor nodes:"]
    for factor in graph.factors:
        if factor.factor_id in allowed:
            lines.extend(
                (
                    f"[{factor.factor_id}] kind={factor.kind}",
                    f"Statement: {factor.statement}",
                )
            )
    return "\n".join(lines)


def _render_candidate_boundary_context(
    *, graph: DecisionGraphV1, candidate_key_id: str
) -> str:
    allowed = set(_candidate_boundary_ids(graph, candidate_key_id))
    lines = [f"Candidate {candidate_key_id} hard-negative boundaries:"]
    if not allowed:
        lines.append("NONE")
    for boundary in graph.boundaries:
        if boundary.boundary_id not in allowed:
            continue
        lines.extend(
            (
                f"[{boundary.boundary_id}] endpoints="
                f"{boundary.left_key_id},{boundary.right_key_id}",
                f"{boundary.left_key_id} exclusion: {boundary.left_exclusion}",
                f"{boundary.right_key_id} exclusion: {boundary.right_exclusion}",
            )
        )
    return "\n".join(lines)


def _render_candidate_reconciliation_state(
    *,
    graph: DecisionGraphV1,
    candidate_key_id: str,
    support: CandidateSupportStateV1,
    counterevidence: CandidateCounterevidenceStateV1,
) -> str:
    factors_by_id = {factor.factor_id: factor for factor in graph.factors}
    boundaries_by_id = {boundary.boundary_id: boundary for boundary in graph.boundaries}
    lines = [
        f"Candidate: {candidate_key_id}",
        f"Support compatible: {str(support.compatible).lower()}",
        f"Support confidence: {support.confidence}",
        "Selected support factors:",
    ]
    for factor_id in support.factor_ids:
        factor = factors_by_id[factor_id]
        lines.extend((f"[{factor_id}] kind={factor.kind}", factor.statement))
    lines.extend(
        (
            f"Counterevidence contradicted: "
            f"{str(counterevidence.contradicted).lower()}",
            f"Counterevidence confidence: {counterevidence.confidence}",
            "Selected counterevidence boundaries:",
        )
    )
    if not counterevidence.boundary_ids:
        lines.append("NONE")
    for boundary_id in counterevidence.boundary_ids:
        boundary = boundaries_by_id[boundary_id]
        lines.extend(
            (
                f"[{boundary_id}] endpoints="
                f"{boundary.left_key_id},{boundary.right_key_id}",
                f"{boundary.left_key_id} exclusion: {boundary.left_exclusion}",
                f"{boundary.right_key_id} exclusion: {boundary.right_exclusion}",
            )
        )
    return "\n".join(lines)


def _candidate_reconciliation_response_format() -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "speech_native_candidate_reconciliation",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "action": {"enum": ["retain_primary", "accept_candidate"]}
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
    }


def _parse_candidate_reconciliation(text: str) -> str | None:
    document = _response_object(text)
    if document is None or set(document) != {"action"}:
        return None
    action = document.get("action")
    return action if action in {"retain_primary", "accept_candidate"} else None


@dataclass(frozen=True)
class GroundedEvidenceV1:
    """One mechanically verifiable citation into a retrieved text key."""

    key_id: str
    field: str
    quote: str

    def as_json(self) -> dict[str, str]:
        return {"key_id": self.key_id, "field": self.field, "quote": self.quote}


@dataclass(frozen=True)
class GroundedQueryStateV1:
    """A bounded semantic query state whose evidence is copied from text keys."""

    candidate_key_ids: tuple[str, ...]
    domain: str
    operation: str
    target: str
    constraints: tuple[str, ...]
    exclusions: tuple[str, ...]
    unresolved_ambiguity: str
    evidence: tuple[GroundedEvidenceV1, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "candidate_key_ids": list(self.candidate_key_ids),
            "domain": self.domain,
            "operation": self.operation,
            "target": self.target,
            "constraints": list(self.constraints),
            "exclusions": list(self.exclusions),
            "unresolved_ambiguity": self.unresolved_ambiguity,
            "evidence": [item.as_json() for item in self.evidence],
        }


@dataclass(frozen=True)
class SpeechNativeDecision:
    matcher_policy_id: str
    key_representation_id: str
    key_id: str | None
    value_label: str | None
    top_key_ids: tuple[str, ...]
    calls: int
    raw_responses: tuple[str, ...]
    verifier_scores: Mapping[str, tuple[bool, float]]
    parse_failure: bool = False
    agent_policy_id: str | None = None
    agent_actions: tuple[str, ...] = ()
    agent_escalated: bool = False
    agent_vote_key_ids: tuple[str | None, ...] = ()
    agent_steps: tuple[Mapping[str, object], ...] = ()
    agent_aggregator_id: str | None = None


@dataclass(frozen=True)
class SpeechNativeMatchTask:
    """One independently schedulable speech-native matcher decision.

    Task dispatch preserves historical whole-decision slot affinity. Contact
    dispatch assigns each model contact independently, so a multi-contact
    decision may migrate between llama-server slots while every contact keeps
    the same speech packet and trace attribution.
    """

    task_id: str
    sample: object
    query_descriptor: Mapping[str, str]
    key_cards: tuple[KeyCardV1, ...]
    key_representation_id: str
    matcher_policy_id: str
    scoring_sample_id: str | None = None
    mechanism_control_id: str = "matched"
    prompt_policy_id: str = "speech-native-json-copy-v2"
    request_layout_id: str = "legacy-key-speech-v1"
    verifier_policy_id: str = "speech-native-compatibility-v1"
    decoding_params: Mapping[str, object] = field(default_factory=dict)
    top_k: int = 3
    audio_key_bindings: Mapping[str, Mapping[str, str]] | None = None
    decision_graph: DecisionGraphV1 | None = None
    ensemble_base_policy_id: str = "M1"
    agent_policy_id: str = "m1-m3-disagreement-escalation-v1"
    agent_aggregator_id: str = "m3-majority-canonical-tie-v1"


@dataclass(frozen=True)
class SpeechNativeMatchOutcome:
    task_id: str
    slot_id: int
    decision: SpeechNativeDecision


@dataclass(frozen=True)
class _BufferedSpeechNativeOutcome:
    outcome: SpeechNativeMatchOutcome | None
    buffer: TraceBuffer | None
    error: BaseException | None


def _validated_key_cards(key_cards: Sequence[KeyCardV1]) -> tuple[KeyCardV1, ...]:
    cards = tuple(card.validate() for card in key_cards)
    if not cards:
        raise PsluFlightError("speech-native matching requires at least one key card")
    key_ids = [card.key_id for card in cards]
    labels = [card.value_label for card in cards]
    if len(set(key_ids)) != len(key_ids):
        raise PsluFlightError("speech-native key cards contain duplicate key_id values")
    if len(set(labels)) != len(labels):
        raise PsluFlightError(
            "speech-native key cards contain duplicate value_label values"
        )
    return cards


def _rotate_key_cards(
    key_cards: tuple[KeyCardV1, ...], offset: int
) -> tuple[KeyCardV1, ...]:
    normalized = offset % len(key_cards)
    return key_cards[normalized:] + key_cards[:normalized]


def render_speech_native_keys(
    key_cards: Sequence[KeyCardV1], key_representation_id: str
) -> str:
    """Render only the matcher-visible portion of K0/K1/K2/K3/K4.

    K3 carries no semantic key body: the short order declaration is needed
    solely to associate each following audio packet with its opaque id.
    """

    cards = _validated_key_cards(key_cards)
    if key_representation_id not in SPEECH_NATIVE_KEY_REPRESENTATIONS:
        raise PsluFlightError(
            f"unknown key representation {key_representation_id!r}; expected "
            f"{SPEECH_NATIVE_KEY_REPRESENTATIONS}"
        )
    if key_representation_id == "K0":
        return "Candidate labels: " + ", ".join(card.value_label for card in cards)
    if key_representation_id == "K3":
        return "Audio key packet order: " + ", ".join(card.key_id for card in cards)
    blocks: list[str] = []
    for card in cards:
        block = (
            f"{card.key_id}\nDefinition: {card.definition}\n"
            f"Positive examples: {' | '.join(card.positive_examples)}"
        )
        if key_representation_id in {"K2", "K4"} and card.contrastive_boundary:
            block += f"\nContrastive boundary: {card.contrastive_boundary}"
        blocks.append(block)
    return "\n\n".join(blocks)


def _response_object(text: str) -> Mapping[str, object] | None:
    candidate = text.strip()
    lines = candidate.splitlines()
    if (
        len(lines) >= 3
        and lines[0].strip().lower() == "```json"
        and lines[-1].strip() == "```"
    ):
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        document = json.loads(candidate)
    except (json.JSONDecodeError, UnicodeError):
        return None
    return document if isinstance(document, Mapping) else None


def _canonical_key_id(key_id: object, allowed: set[str]) -> str | None:
    if not isinstance(key_id, str):
        return None
    if key_id in allowed:
        return key_id
    if key_id.startswith("K") and key_id[1:].isdigit() and 1 <= len(key_id[1:]) <= 3:
        canonical = f"K{int(key_id[1:]):03d}"
        return canonical if canonical in allowed else None
    return None


def _selected_key_id(text: str, allowed: set[str]) -> str | None:
    document = _response_object(text)
    key_id = document.get("key_id") if document is not None else None
    return _canonical_key_id(key_id, allowed)


def _selected_top_keys(text: str, allowed: set[str], top_k: int) -> tuple[str, ...]:
    document = _response_object(text)
    raw = document.get("key_ids") if document is not None else None
    if not isinstance(raw, list):
        return ()
    selected: list[str] = []
    for key_id in raw:
        canonical = _canonical_key_id(key_id, allowed)
        if canonical is not None and canonical not in selected:
            selected.append(canonical)
        if len(selected) == top_k:
            break
    return tuple(selected)


def _compatibility(text: str) -> tuple[bool, float] | None:
    document = _response_object(text)
    if document is None or not isinstance(document.get("compatible"), bool):
        return None
    confidence = document.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return None
    score = float(confidence)
    if score < 0.0 or score > 100.0:
        return None
    return bool(document["compatible"]), score


def parse_grounded_query_state(
    text: str,
    *,
    candidate_key_ids: tuple[str, ...],
    cards_by_key: Mapping[str, KeyCardV1],
    key_representation_id: str,
) -> GroundedQueryStateV1 | None:
    """Parse a bounded state and verify every cited quote against visible key text."""

    document = _response_object(text)
    required = {
        "candidate_key_ids",
        "domain",
        "operation",
        "target",
        "constraints",
        "exclusions",
        "unresolved_ambiguity",
        "evidence",
    }
    if document is None or set(document) != required:
        return None
    raw_candidates = document.get("candidate_key_ids")
    if raw_candidates != list(candidate_key_ids):
        return None

    def bounded_text(value: object, *, maximum: int = 160) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = " ".join(value.split())
        return normalized if normalized and len(normalized) <= maximum else None

    scalar_values = tuple(
        bounded_text(document.get(field))
        for field in ("domain", "operation", "target", "unresolved_ambiguity")
    )
    if any(value is None for value in scalar_values):
        return None

    def bounded_list(value: object) -> tuple[str, ...] | None:
        if not isinstance(value, list) or len(value) > 5:
            return None
        parsed = tuple(bounded_text(item) for item in value)
        if any(item is None for item in parsed):
            return None
        return tuple(item for item in parsed if item is not None)

    constraints = bounded_list(document.get("constraints"))
    exclusions = bounded_list(document.get("exclusions"))
    if constraints is None or exclusions is None:
        return None
    raw_evidence = document.get("evidence")
    if (
        not isinstance(raw_evidence, list)
        or not candidate_key_ids
        or not len(candidate_key_ids) <= len(raw_evidence) <= 2 * len(candidate_key_ids)
    ):
        return None
    visible_fields = {"definition", "positive_examples"}
    if key_representation_id == "K2":
        visible_fields.add("contrastive_boundary")
    evidence: list[GroundedEvidenceV1] = []
    for item in raw_evidence:
        if not isinstance(item, Mapping) or set(item) != {"key_id", "field", "quote"}:
            return None
        key_id = item.get("key_id")
        field_name = item.get("field")
        quote = bounded_text(item.get("quote"), maximum=240)
        if (
            key_id not in candidate_key_ids
            or field_name not in visible_fields
            or quote is None
        ):
            return None
        card = cards_by_key[str(key_id)]
        if field_name == "definition":
            sources = (card.definition,)
        elif field_name == "positive_examples":
            sources = card.positive_examples
        else:
            sources = (
                (card.contrastive_boundary or "")
                if field_name == "contrastive_boundary"
                else "",
            )
        if not any(quote in source for source in sources):
            return None
        evidence.append(
            GroundedEvidenceV1(key_id=str(key_id), field=str(field_name), quote=quote)
        )
    if {item.key_id for item in evidence} != set(candidate_key_ids):
        return None
    domain, operation, target, ambiguity = scalar_values
    assert domain is not None and operation is not None and target is not None
    assert ambiguity is not None
    return GroundedQueryStateV1(
        candidate_key_ids=candidate_key_ids,
        domain=domain,
        operation=operation,
        target=target,
        constraints=constraints,
        exclusions=exclusions,
        unresolved_ambiguity=ambiguity,
        evidence=tuple(evidence),
    )


def _grounded_query_state_response_format(
    *,
    candidate_key_ids: tuple[str, ...],
    cards_by_key: Mapping[str, KeyCardV1],
    key_representation_id: str,
) -> dict[str, object]:
    """Build a llama-server JSON schema that can only emit parser-valid citations."""

    def evidence_alternatives(key_id: str) -> list[dict[str, object]]:
        card = cards_by_key[key_id]
        sources: list[tuple[str, tuple[str, ...]]] = [
            ("definition", (card.definition,)),
            ("positive_examples", card.positive_examples),
        ]
        if key_representation_id == "K2" and card.contrastive_boundary:
            sources.append(("contrastive_boundary", (card.contrastive_boundary,)))
        return [
            {
                "type": "object",
                "properties": {
                    "key_id": {"const": key_id},
                    "field": {"const": field_name},
                    "quote": {"enum": list(quotes)},
                },
                "required": ["key_id", "field", "quote"],
                "additionalProperties": False,
            }
            for field_name, quotes in sources
        ]

    scalar = {"type": "string", "minLength": 1, "maxLength": 160}
    bounded_list = {
        "type": "array",
        "items": {"type": "string", "minLength": 1, "maxLength": 160},
        "maxItems": 5,
    }
    count = len(candidate_key_ids)
    schema = {
        "type": "object",
        "properties": {
            "candidate_key_ids": {
                "type": "array",
                "prefixItems": [{"const": key_id} for key_id in candidate_key_ids],
                "minItems": count,
                "maxItems": count,
            },
            "domain": scalar,
            "operation": scalar,
            "target": scalar,
            "constraints": bounded_list,
            "exclusions": bounded_list,
            "unresolved_ambiguity": scalar,
            "evidence": {
                "type": "array",
                "prefixItems": [
                    {"anyOf": evidence_alternatives(key_id)}
                    for key_id in candidate_key_ids
                ],
                "minItems": count,
                "maxItems": count,
            },
        },
        "required": [
            "candidate_key_ids",
            "domain",
            "operation",
            "target",
            "constraints",
            "exclusions",
            "unresolved_ambiguity",
            "evidence",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "grounded_query_state",
            "strict": True,
            "schema": schema,
        },
    }


def _key_choice_response_format(
    *, name: str, key_ids: Sequence[str]
) -> dict[str, object]:
    """Constrain one frozen-core response to one supplied opaque key id."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"key_id": {"enum": list(key_ids)}},
                "required": ["key_id"],
                "additionalProperties": False,
            },
        },
    }


def _top_key_choice_response_format(
    *, key_ids: Sequence[str], top_k: int
) -> dict[str, object]:
    """Constrain one retrieval response to an exact-size opaque-key array."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "speech_native_top_key_choice",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "key_ids": {
                        "type": "array",
                        "items": {"enum": list(key_ids)},
                        "minItems": top_k,
                        "maxItems": top_k,
                    }
                },
                "required": ["key_ids"],
                "additionalProperties": False,
            },
        },
    }


def _speech_feature_messages(
    *,
    system_text: str,
    query_descriptor: Mapping[str, str],
    key_text: str | None,
    key_cards: Sequence[KeyCardV1],
    key_representation_id: str,
    audio_key_bindings: Mapping[str, Mapping[str, str]] | None,
    request_layout_id: str,
    stable_knowledge_text: str | None = None,
) -> tuple[Mapping[str, object], ...]:
    if request_layout_id not in SPEECH_NATIVE_REQUEST_LAYOUTS:
        raise PsluFlightError(
            f"unknown request layout {request_layout_id!r}; expected "
            f"{SPEECH_NATIVE_REQUEST_LAYOUTS}"
        )
    required = {"packet_id", "sha256", "role"}
    if set(query_descriptor) != required or query_descriptor.get("role") != "query":
        raise PsluFlightError(
            "query_descriptor must carry exact packet_id/sha256/role=query"
        )
    query_part = {
        "type": "input_speech_features",
        "speech_features": dict(query_descriptor),
    }
    content: list[Mapping[str, object]] = []
    if request_layout_id == "slot-affine-knowledge-speech-state-v1":
        if not isinstance(stable_knowledge_text, str) or not stable_knowledge_text:
            raise PsluFlightError(
                "knowledge-speech-state layout requires stable knowledge text"
            )
        content.append(
            {
                "type": "text",
                "text": f"Opaque key catalog:\n{stable_knowledge_text}",
            }
        )
    if request_layout_id == "legacy-key-speech-v1" and key_text:
        content.append({"type": "text", "text": key_text})
    content.append(query_part)
    if request_layout_id == "slot-affine-speech-prefix-v1" and key_text:
        content.append({"type": "text", "text": key_text})
    if (
        request_layout_id == "slot-affine-knowledge-speech-state-v1"
        and key_text
        and key_text != stable_knowledge_text
    ):
        content.append({"type": "text", "text": key_text})
    if key_representation_id in {"K3", "K4"}:
        if audio_key_bindings is None or set(audio_key_bindings) != {
            card.key_id for card in key_cards
        }:
            raise PsluFlightError(
                f"{key_representation_id} requires one audio key binding per key card"
            )
        for card in key_cards:
            binding = audio_key_bindings[card.key_id]
            if not isinstance(binding, Mapping) or set(binding) != {
                "packet_id",
                "sha256",
            }:
                raise PsluFlightError(
                    f"audio key binding {card.key_id!r} must carry exact packet_id/sha256"
                )
            content.append(
                {
                    "type": "input_speech_features",
                    "speech_features": {
                        "packet_id": binding["packet_id"],
                        "sha256": binding["sha256"],
                        "role": "key",
                    },
                }
            )
    if request_layout_id in {
        "slot-affine-speech-prefix-v1",
        "slot-affine-knowledge-speech-state-v1",
    }:
        content.append({"type": "text", "text": f"Task instruction:\n{system_text}"})
    return (
        {
            "role": "system",
            "content": (
                SPEECH_NATIVE_STABLE_SYSTEM_TEXT
                if request_layout_id
                in {
                    "slot-affine-speech-prefix-v1",
                    "slot-affine-knowledge-speech-state-v1",
                }
                else system_text
            ),
        },
        {"role": "user", "content": content},
    )


def _stable_knowledge_text_for_layout(
    *,
    request_layout_id: str,
    key_cards: Sequence[KeyCardV1],
    key_representation_id: str,
) -> str | None:
    if request_layout_id != "slot-affine-knowledge-speech-state-v1":
        return None
    return render_speech_native_keys(key_cards, key_representation_id)


def run_speech_native_matcher(
    *,
    core_client,
    sample,
    query_descriptor: Mapping[str, str],
    key_cards: Sequence[KeyCardV1],
    key_representation_id: str,
    matcher_policy_id: str,
    prompt_policy_id: str = "speech-native-json-copy-v2",
    request_layout_id: str = "legacy-key-speech-v1",
    verifier_policy_id: str = "speech-native-compatibility-v1",
    decoding_params: Mapping[str, object] | None = None,
    top_k: int = 3,
    audio_key_bindings: Mapping[str, Mapping[str, str]] | None = None,
    decision_graph: DecisionGraphV1 | None = None,
    ensemble_base_policy_id: str = "M1",
    agent_policy_id: str = "m1-m3-disagreement-escalation-v1",
    agent_aggregator_id: str = "m3-majority-canonical-tie-v1",
    _trace_matcher_policy_id: str | None = None,
    _trace_buffer: TraceBuffer | None = None,
) -> SpeechNativeDecision:
    """Run one frozen-core speech-query decision under M0--M11.

    Every local ``contact`` call reconstructs a two-message request carrying
    the original query packet. Generated factor text and verifier outputs may
    condition later calls, but never replace the speech query.
    """

    cards = _validated_key_cards(key_cards)
    if matcher_policy_id not in SPEECH_NATIVE_MATCHER_POLICIES:
        raise PsluFlightError(
            f"unknown matcher policy {matcher_policy_id!r}; expected "
            f"{SPEECH_NATIVE_MATCHER_POLICIES}"
        )
    if prompt_policy_id not in SPEECH_NATIVE_PROMPT_POLICIES:
        raise PsluFlightError(
            f"unknown prompt policy {prompt_policy_id!r}; expected "
            f"{SPEECH_NATIVE_PROMPT_POLICIES}"
        )
    if request_layout_id not in SPEECH_NATIVE_REQUEST_LAYOUTS:
        raise PsluFlightError(
            f"unknown request layout {request_layout_id!r}; expected "
            f"{SPEECH_NATIVE_REQUEST_LAYOUTS}"
        )
    if verifier_policy_id not in SPEECH_NATIVE_VERIFIER_POLICIES:
        raise PsluFlightError(
            f"unknown verifier policy {verifier_policy_id!r}; expected "
            f"{SPEECH_NATIVE_VERIFIER_POLICIES}"
        )
    if agent_aggregator_id not in SPEECH_NATIVE_AGENT_AGGREGATORS:
        raise PsluFlightError(
            f"unknown agent aggregator {agent_aggregator_id!r}; expected "
            f"{SPEECH_NATIVE_AGENT_AGGREGATORS}"
        )
    if agent_policy_id not in SPEECH_NATIVE_AGENT_POLICIES:
        raise PsluFlightError(
            f"unknown agent policy {agent_policy_id!r}; expected "
            f"{SPEECH_NATIVE_AGENT_POLICIES}"
        )
    m5_policies = {
        "m1-m3-disagreement-escalation-v1",
        "m1-m3-full-branch-explorer-v1",
    }
    m5_aggregators = {
        "m3-majority-canonical-tie-v1",
        "m3-majority-primary-tie-v2",
        "m3-unanimous-primary-fallback-v3",
    }
    if matcher_policy_id == "M5" and (
        agent_policy_id not in m5_policies or agent_aggregator_id not in m5_aggregators
    ):
        raise PsluFlightError("M5 requires an M1/M3 agent policy and aggregator")
    m6_policies = {
        "knowledge-grounded-semantic-refinement-full-action-v1",
        "knowledge-grounded-semantic-refinement-schema-v2",
        "knowledge-grounded-semantic-refinement-schema-v3",
    }
    if matcher_policy_id == "M6" and (
        agent_policy_id not in m6_policies
        or agent_aggregator_id != "grounded-refined-primary-fallback-v1"
    ):
        raise PsluFlightError("M6 requires the grounded semantic policy and aggregator")
    if matcher_policy_id == "M6" and key_representation_id not in {"K1", "K2"}:
        raise PsluFlightError("M6 supports maintainable text keys K1/K2 only")
    if matcher_policy_id == "M6" and prompt_policy_id != "speech-native-json-copy-v3":
        raise PsluFlightError("M6 requires the strict JSON-copy v3 prompt policy")
    if matcher_policy_id == "M7" and (
        agent_policy_id != "knowledge-grounded-multistate-action-support-v1"
        or agent_aggregator_id != "action-support-primary-control-v1"
    ):
        raise PsluFlightError(
            "M7 requires the multistate action-support policy and control"
        )
    if matcher_policy_id == "M7" and key_representation_id not in {"K1", "K2"}:
        raise PsluFlightError("M7 supports maintainable text keys K1/K2 only")
    if matcher_policy_id == "M7" and prompt_policy_id != "speech-native-json-copy-v3":
        raise PsluFlightError("M7 requires the strict JSON-copy v3 prompt policy")
    if matcher_policy_id == "M8" and (
        agent_policy_id != "speech-conditioned-pairwise-boundary-support-v1"
        or agent_aggregator_id != "pairwise-boundary-primary-control-v1"
    ):
        raise PsluFlightError(
            "M8 requires the pairwise-boundary support policy and control"
        )
    if matcher_policy_id == "M8" and key_representation_id != "K1":
        raise PsluFlightError(
            "M8 requires maintainable K1 text keys at the profile boundary"
        )
    if matcher_policy_id == "M8" and prompt_policy_id != "speech-native-json-copy-v4":
        raise PsluFlightError(
            "M8 requires the schema-constrained JSON-copy v4 prompt policy"
        )
    if matcher_policy_id == "M9" and (
        agent_policy_id != "speech-conditioned-factor-graph-action-support-v1"
        or agent_aggregator_id != "factor-graph-primary-control-v1"
    ):
        raise PsluFlightError("M9 requires the factor-graph support policy and control")
    if matcher_policy_id == "M9" and key_representation_id != "K1":
        raise PsluFlightError("M9 requires maintainable K1 text keys")
    if matcher_policy_id == "M9" and prompt_policy_id != "speech-native-json-copy-v4":
        raise PsluFlightError(
            "M9 requires the schema-constrained JSON-copy v4 prompt policy"
        )
    if matcher_policy_id == "M9" and decision_graph is None:
        raise PsluFlightError("M9 requires one DecisionGraphV1")
    if matcher_policy_id == "M9":
        assert decision_graph is not None
        decision_graph.validate(cards)
    if matcher_policy_id == "M10" and (
        agent_policy_id != "speech-conditioned-candidate-evidence-action-support-v1"
        or agent_aggregator_id != "candidate-evidence-primary-control-v1"
    ):
        raise PsluFlightError(
            "M10 requires the candidate-evidence support policy and control"
        )
    if matcher_policy_id == "M10" and key_representation_id != "K1":
        raise PsluFlightError("M10 requires maintainable K1 text keys")
    if matcher_policy_id == "M10" and prompt_policy_id != "speech-native-json-copy-v4":
        raise PsluFlightError(
            "M10 requires the schema-constrained JSON-copy v4 prompt policy"
        )
    if matcher_policy_id == "M10" and decision_graph is None:
        raise PsluFlightError("M10 requires one DecisionGraphV1")
    if matcher_policy_id == "M10":
        assert decision_graph is not None
        decision_graph.validate(cards)
    if matcher_policy_id == "M11" and (
        agent_policy_id
        not in {
            "speech-conditioned-adaptive-evidence-gap-v1",
            "speech-conditioned-adaptive-evidence-gap-v2",
        }
        or agent_aggregator_id != "adaptive-evidence-gap-primary-control-v1"
    ):
        raise PsluFlightError(
            "M11 requires the adaptive evidence-gap policy and primary control"
        )
    if matcher_policy_id == "M11" and key_representation_id != "K1":
        raise PsluFlightError("M11 requires maintainable K1 text keys")
    if matcher_policy_id == "M11" and prompt_policy_id != "speech-native-json-copy-v4":
        raise PsluFlightError(
            "M11 requires the schema-constrained JSON-copy v4 prompt policy"
        )
    if matcher_policy_id == "M11" and decision_graph is None:
        raise PsluFlightError("M11 requires one data-derived DecisionGraphV1")
    if matcher_policy_id == "M11":
        assert decision_graph is not None
        decision_graph.validate(cards)
    top_k_is_active = matcher_policy_id in {
        "M3",
        "M5",
        "M6",
        "M7",
        "M8",
        "M9",
        "M10",
        "M11",
    } or (matcher_policy_id == "M4" and ensemble_base_policy_id == "M3")
    if top_k_is_active and (top_k <= 0 or top_k > len(cards)):
        raise PsluFlightError(f"top_k must be in [1, {len(cards)}], got {top_k}")
    by_key = {card.key_id: card for card in cards}
    allowed = set(by_key)
    raw_responses: list[str] = []

    def contact_request(
        stage: str,
        system_text: str,
        stage_cards: Sequence[KeyCardV1],
        key_text: str | None,
        *,
        decoding_overrides: Mapping[str, object] | None = None,
    ) -> tuple[tuple[Mapping[str, object], ...], dict[str, object]]:
        messages = _speech_feature_messages(
            system_text=system_text,
            query_descriptor=query_descriptor,
            key_text=key_text,
            key_cards=stage_cards,
            key_representation_id=key_representation_id,
            audio_key_bindings=(
                {card.key_id: audio_key_bindings[card.key_id] for card in stage_cards}
                if audio_key_bindings is not None
                else None
            ),
            request_layout_id=request_layout_id,
            stable_knowledge_text=_stable_knowledge_text_for_layout(
                request_layout_id=request_layout_id,
                key_cards=cards,
                key_representation_id=key_representation_id,
            ),
        )
        request_decoding_params = dict(decoding_params or {})
        if decoding_overrides is not None:
            request_decoding_params.update(decoding_overrides)
        return messages, {
            "decoding_params": request_decoding_params,
            "speech_feature_sample_id": sample.sample_id,
            "key_representation_id": key_representation_id,
            "matcher_policy_id": (
                f"{_trace_matcher_policy_id or matcher_policy_id}:{stage}"
            ),
        }

    def contact(
        stage: str,
        system_text: str,
        stage_cards: Sequence[KeyCardV1],
        key_text: str | None,
        *,
        decoding_overrides: Mapping[str, object] | None = None,
    ) -> str:
        messages, kwargs = contact_request(
            stage,
            system_text,
            stage_cards,
            key_text,
            decoding_overrides=decoding_overrides,
        )
        response = core_client.complete(messages, **kwargs)
        raw_responses.append(response)
        return response

    def contact_many_with_overrides(
        specifications: Sequence[
            tuple[
                str,
                str,
                Sequence[KeyCardV1],
                str | None,
                Mapping[str, object] | None,
            ]
        ],
    ) -> tuple[str, ...]:
        if not specifications:
            return ()
        requests = tuple(
            contact_request(
                stage,
                system_text,
                stage_cards,
                key_text,
                decoding_overrides=decoding_overrides,
            )
            for (
                stage,
                system_text,
                stage_cards,
                key_text,
                decoding_overrides,
            ) in specifications
        )
        batch_complete = getattr(core_client, "complete_many", None)
        if callable(batch_complete):
            responses = tuple(batch_complete(requests, trace_parent=_trace_buffer))
        else:
            responses = tuple(
                core_client.complete(messages, **kwargs)
                for messages, kwargs in requests
            )
        raw_responses.extend(responses)
        return responses

    def contact_many(
        specifications: Sequence[tuple[str, str, Sequence[KeyCardV1], str | None]],
    ) -> tuple[str, ...]:
        return contact_many_with_overrides(
            tuple((*specification, None) for specification in specifications)
        )

    def finish(
        key_id: str | None,
        *,
        top_ids: tuple[str, ...] = (),
        scores: Mapping[str, tuple[bool, float]] = MappingProxyType({}),
        agent_policy_id: str | None = None,
        agent_actions: tuple[str, ...] = (),
        agent_escalated: bool = False,
        agent_vote_key_ids: tuple[str | None, ...] = (),
        agent_steps: tuple[Mapping[str, object], ...] = (),
        decision_agent_aggregator_id: str | None = None,
    ) -> SpeechNativeDecision:
        return SpeechNativeDecision(
            matcher_policy_id=matcher_policy_id,
            key_representation_id=key_representation_id,
            key_id=key_id,
            value_label=by_key[key_id].value_label if key_id in by_key else None,
            top_key_ids=top_ids,
            calls=len(raw_responses),
            raw_responses=tuple(raw_responses),
            verifier_scores=dict(scores),
            parse_failure=key_id is None,
            agent_policy_id=agent_policy_id,
            agent_actions=agent_actions,
            agent_escalated=agent_escalated,
            agent_vote_key_ids=agent_vote_key_ids,
            agent_steps=agent_steps,
            agent_aggregator_id=decision_agent_aggregator_id,
        )

    def run_nested_decision(
        policy_id: str,
        ordering: tuple[KeyCardV1, ...],
        trace_policy_id: str,
        trace_buffer: TraceBuffer | None,
    ) -> SpeechNativeDecision:
        return run_speech_native_matcher(
            core_client=core_client,
            sample=sample,
            query_descriptor=query_descriptor,
            key_cards=ordering,
            key_representation_id=key_representation_id,
            matcher_policy_id=policy_id,
            prompt_policy_id=prompt_policy_id,
            request_layout_id=request_layout_id,
            verifier_policy_id=verifier_policy_id,
            decoding_params=decoding_params,
            top_k=top_k,
            audio_key_bindings=audio_key_bindings,
            decision_graph=decision_graph,
            agent_policy_id=agent_policy_id,
            _trace_matcher_policy_id=trace_policy_id,
            _trace_buffer=trace_buffer,
        )

    def nested_decision(
        policy_id: str,
        ordering: tuple[KeyCardV1, ...],
        trace_policy_id: str,
    ) -> SpeechNativeDecision:
        decision = run_nested_decision(
            policy_id, ordering, trace_policy_id, _trace_buffer
        )
        raw_responses.extend(decision.raw_responses)
        return decision

    def parallel_nested_decisions(
        specifications: Sequence[tuple[str, tuple[KeyCardV1, ...], str]],
    ) -> tuple[SpeechNativeDecision, ...]:
        if not getattr(core_client, "supports_parallel_branches", False):
            return tuple(
                nested_decision(policy_id, ordering, trace_policy_id)
                for policy_id, ordering, trace_policy_id in specifications
            )
        child_buffers = (
            tuple(TraceBuffer(_trace_buffer.run_id) for _ in specifications)
            if _trace_buffer is not None
            else (None,) * len(specifications)
        )

        def invoke(
            specification: tuple[str, tuple[KeyCardV1, ...], str],
            child_buffer: TraceBuffer | None,
        ) -> SpeechNativeDecision:
            if child_buffer is not None:
                set_current_trace_buffer(child_buffer)
            try:
                return run_nested_decision(*specification, child_buffer)
            finally:
                if child_buffer is not None:
                    set_current_trace_buffer(None)

        with ThreadPoolExecutor(
            max_workers=len(specifications),
            thread_name_prefix="saea-speech-native-branch",
        ) as branch_pool:
            futures = tuple(
                branch_pool.submit(invoke, specification, child_buffer)
                for specification, child_buffer in zip(
                    specifications, child_buffers, strict=True
                )
            )
            decisions = tuple(future.result() for future in futures)
        if _trace_buffer is not None:
            for child_buffer in child_buffers:
                assert child_buffer is not None
                _trace_buffer.extend_from(child_buffer)
        for decision in decisions:
            raw_responses.extend(decision.raw_responses)
        return decisions

    def agent_step(
        action_id: str, decision: SpeechNativeDecision
    ) -> Mapping[str, object]:
        return {
            "action_id": action_id,
            "key_id": decision.key_id,
            "top_key_ids": list(decision.top_key_ids),
            "calls": decision.calls,
            "parse_failure": decision.parse_failure,
        }

    if matcher_policy_id == "M4":
        orderings = (
            cards,
            tuple(reversed(cards)),
            _rotate_key_cards(cards, 7),
        )
        decisions = parallel_nested_decisions(
            tuple(
                (
                    ensemble_base_policy_id,
                    ordering,
                    f"M4:{ensemble_base_policy_id}:order-{order_index}",
                )
                for order_index, ordering in enumerate(orderings)
            )
        )
        votes = [
            decision.key_id for decision in decisions if decision.key_id is not None
        ]
        if not votes:
            return finish(None)
        counts = {key_id: votes.count(key_id) for key_id in set(votes)}
        majority = next(
            (key_id for key_id, count in counts.items() if count >= 2), None
        )
        winner = majority if majority is not None else decisions[0].key_id
        return finish(winner)

    if matcher_policy_id == "M5":
        primary, canonical = parallel_nested_decisions(
            (
                ("M1", cards, "M5:M1:canonical"),
                ("M3", cards, "M5:M3:canonical"),
            )
        )
        initial_votes = (primary.key_id, canonical.key_id)
        initial_steps = (
            agent_step("match:listwise-canonical", primary),
            agent_step("retrieve-verify:canonical", canonical),
        )
        initial_agreement = (
            primary.key_id is not None and primary.key_id == canonical.key_id
        )
        full_branch = agent_policy_id == "m1-m3-full-branch-explorer-v1"
        if initial_agreement and not full_branch:
            return finish(
                primary.key_id,
                top_ids=canonical.top_key_ids,
                scores=canonical.verifier_scores,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    "match:listwise-canonical",
                    "retrieve-verify:canonical",
                    "stop:agree",
                ),
                agent_vote_key_ids=initial_votes,
                agent_steps=initial_steps,
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        reverse, rotate = parallel_nested_decisions(
            (
                ("M3", tuple(reversed(cards)), "M5:M3:reverse"),
                ("M3", _rotate_key_cards(cards, 7), "M5:M3:rotate-7"),
            )
        )
        m3_votes = (canonical.key_id, reverse.key_id, rotate.key_id)
        valid_m3_votes = [key_id for key_id in m3_votes if key_id is not None]
        counts = {
            key_id: valid_m3_votes.count(key_id) for key_id in set(valid_m3_votes)
        }
        majority = next(
            (key_id for key_id, count in counts.items() if count >= 2), None
        )
        if agent_aggregator_id == "m3-unanimous-primary-fallback-v3":
            unanimous = (
                valid_m3_votes[0]
                if len(valid_m3_votes) == 3 and len(set(valid_m3_votes)) == 1
                else None
            )
            winner = unanimous if unanimous is not None else primary.key_id
            aggregate_action = "aggregate:m3-unanimous-primary-fallback"
        else:
            fallback = (
                primary.key_id
                if agent_aggregator_id == "m3-majority-primary-tie-v2"
                else canonical.key_id
            )
            winner = majority if majority is not None else fallback
            aggregate_action = (
                "aggregate:m3-majority-primary-tie"
                if agent_aggregator_id == "m3-majority-primary-tie-v2"
                else "aggregate:m3-majority-canonical-tie"
            )
        return finish(
            winner,
            top_ids=canonical.top_key_ids,
            scores=canonical.verifier_scores,
            agent_policy_id=agent_policy_id,
            agent_actions=(
                "match:listwise-canonical",
                "retrieve-verify:canonical",
                ("explore:full-branch" if full_branch else "escalate:disagreement"),
                "retrieve-verify:reverse",
                "retrieve-verify:rotate-7",
                aggregate_action,
            ),
            agent_escalated=not initial_agreement,
            agent_vote_key_ids=(*initial_votes, reverse.key_id, rotate.key_id),
            agent_steps=(
                *initial_steps,
                agent_step("retrieve-verify:reverse", reverse),
                agent_step("retrieve-verify:rotate-7", rotate),
            ),
            decision_agent_aggregator_id=agent_aggregator_id,
        )

    if matcher_policy_id == "M0":
        direct_label_overrides = None
        if prompt_policy_id == "speech-native-json-copy-v4":
            direct_label_overrides = {
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "direct_label_choice",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "label": {"enum": [card.value_label for card in cards]}
                            },
                            "required": ["label"],
                            "additionalProperties": False,
                        },
                    },
                }
            }
        response = contact(
            "direct-label",
            "Classify the spoken command into exactly one listed label. Respond only as "
            '{"label":"..."}.',
            cards,
            render_speech_native_keys(cards, "K0"),
            decoding_overrides=direct_label_overrides,
        )
        document = _response_object(response)
        label = document.get("label") if document is not None else None
        key_id = next(
            (card.key_id for card in cards if card.value_label == label), None
        )
        return finish(key_id)

    if matcher_policy_id == "M1":
        if key_representation_id == "K0":
            response = contact(
                "listwise-label",
                "Match the spoken command to exactly one listed label. Return one JSON "
                "object with exactly one field named label. Its string value must be "
                "copied verbatim from the supplied label list.",
                cards,
                render_speech_native_keys(cards, key_representation_id),
            )
            document = _response_object(response)
            label = document.get("label") if document is not None else None
            key_id = next(
                (card.key_id for card in cards if card.value_label == label), None
            )
            return finish(key_id)
        response = contact(
            "listwise",
            "Match the spoken command to exactly one opaque key. Use the speech signal and "
            "the supplied key representations jointly. Return one JSON object with exactly "
            "one field named key_id. Its string value must be copied verbatim from a supplied "
            "key heading; do not invent or shorten an id.",
            cards,
            render_speech_native_keys(cards, key_representation_id),
        )
        return finish(_selected_key_id(response, allowed))

    if matcher_policy_id == "M2":
        factors = contact(
            "intent-factors",
            "Analyze the speech directly without transcribing it. Identify intent factors such "
            "as domain, requested operation, target, and contrastive cues. Respond only as "
            '{"factors":["..."],"summary":"..."}.',
            (),
            None,
        )
        response = contact(
            "factor-conditioned-selection",
            "Match the spoken command to exactly one opaque key. The prior semantic analysis "
            "below is advisory; re-evaluate it against the speech signal carried again in this "
            "request. Return one JSON object with exactly one field named key_id. Its string "
            "value must be copied verbatim from a supplied key heading.",
            cards,
            (
                "Prior semantic analysis:\n"
                + factors
                + "\n\nKeys:\n"
                + render_speech_native_keys(cards, key_representation_id)
            ),
        )
        return finish(_selected_key_id(response, allowed))

    if matcher_policy_id == "M8":
        primary_instruction = (
            "Match the spoken command to exactly one opaque key. Use the speech signal and "
            "the supplied K1 text cards jointly. Return only the selected key_id."
        )
        retrieval_instruction = (
            f"Retrieve exactly {top_k} distinct opaque keys for the spoken command, ranked "
            "from most to least compatible. Use the speech signal and supplied K1 text "
            "cards jointly. Return only the ordered key_ids."
        )
        initial_responses = contact_many_with_overrides(
            (
                (
                    "primary-listwise",
                    primary_instruction,
                    cards,
                    render_speech_native_keys(cards, "K1"),
                    {
                        "response_format": _key_choice_response_format(
                            name="speech_native_primary_key_choice",
                            key_ids=tuple(card.key_id for card in cards),
                        )
                    },
                ),
                (
                    f"speech-retrieve-top-{top_k}",
                    retrieval_instruction,
                    cards,
                    render_speech_native_keys(cards, "K1"),
                    {
                        "response_format": _top_key_choice_response_format(
                            key_ids=tuple(card.key_id for card in cards),
                            top_k=top_k,
                        )
                    },
                ),
            )
        )
        primary_key_id = _selected_key_id(initial_responses[0], allowed)
        initial_top_ids = _selected_top_keys(initial_responses[1], allowed, top_k)
        initial_steps: tuple[Mapping[str, object], ...] = (
            {
                "action_id": "match:speech-only-primary",
                "key_id": primary_key_id,
                "top_key_ids": [],
                "calls": 1,
                "parse_failure": primary_key_id is None,
            },
            {
                "action_id": "retrieve:speech-only",
                "key_id": initial_top_ids[0] if initial_top_ids else None,
                "top_key_ids": list(initial_top_ids),
                "calls": 1,
                "parse_failure": len(initial_top_ids) != top_k,
            },
        )
        if primary_key_id is None or len(initial_top_ids) != top_k:
            return finish(
                primary_key_id,
                top_ids=initial_top_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "backtrack:invalid-initial-pairwise-support",
                ),
                agent_escalated=True,
                agent_vote_key_ids=(primary_key_id,),
                agent_steps=initial_steps,
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        challengers = tuple(
            key_id for key_id in initial_top_ids if key_id != primary_key_id
        )
        pairwise_requests: list[
            tuple[
                str,
                str,
                Sequence[KeyCardV1],
                str | None,
                Mapping[str, object] | None,
            ]
        ] = []
        pairwise_owners: list[tuple[int, str, str]] = []
        for rank, challenger_key_id in enumerate(challengers, start=1):
            pair_ids = (primary_key_id, challenger_key_id)
            response_format = _key_choice_response_format(
                name="speech_native_pairwise_key_choice",
                key_ids=pair_ids,
            )
            for representation_id in ("K1", "K2"):
                for order_id, ordered_ids in (
                    ("ab", pair_ids),
                    ("ba", tuple(reversed(pair_ids))),
                ):
                    ordered_cards = tuple(by_key[key_id] for key_id in ordered_ids)
                    pairwise_requests.append(
                        (
                            f"pairwise-{representation_id}-rank-{rank}-{order_id}",
                            "Choose which of exactly two opaque keys better matches the "
                            "spoken command. Compare the speech signal directly against both "
                            "cards. Treat card order as irrelevant and return only key_id.",
                            ordered_cards,
                            render_speech_native_keys(ordered_cards, representation_id),
                            {"response_format": response_format},
                        )
                    )
                    pairwise_owners.append((rank, representation_id, order_id))
        pairwise_responses = contact_many_with_overrides(tuple(pairwise_requests))
        parsed_votes: dict[tuple[int, str, str], str | None] = {}
        for owner, response in zip(pairwise_owners, pairwise_responses, strict=True):
            challenger_key_id = challengers[owner[0] - 1]
            parsed_votes[owner] = _selected_key_id(
                response, {primary_key_id, challenger_key_id}
            )

        comparison_steps: list[Mapping[str, object]] = []
        support_votes: list[str | None] = []
        for rank, challenger_key_id in enumerate(challengers, start=1):
            k1_ab = parsed_votes[(rank, "K1", "ab")]
            k1_ba = parsed_votes[(rank, "K1", "ba")]
            k2_ab = parsed_votes[(rank, "K2", "ab")]
            k2_ba = parsed_votes[(rank, "K2", "ba")]
            k1_stable = (
                challenger_key_id if k1_ab == k1_ba == challenger_key_id else None
            )
            k2_stable = (
                challenger_key_id if k2_ab == k2_ba == challenger_key_id else None
            )
            support_votes.extend((k1_stable, k2_stable))
            comparison_steps.append(
                {
                    "action_id": f"compare:pairwise-boundary-rank-{rank}",
                    "rank": rank,
                    "primary_key_id": primary_key_id,
                    "challenger_key_id": challenger_key_id,
                    "k1_ab_key_id": k1_ab,
                    "k1_ba_key_id": k1_ba,
                    "k1_stable_key_id": k1_stable,
                    "k2_ab_key_id": k2_ab,
                    "k2_ba_key_id": k2_ba,
                    "k2_stable_key_id": k2_stable,
                    "calls": 4,
                    "parse_failure": any(
                        vote is None for vote in (k1_ab, k1_ba, k2_ab, k2_ba)
                    ),
                    "causal_parent_ids": [
                        "match:speech-only-primary",
                        "retrieve:speech-only",
                    ],
                }
            )
        return finish(
            primary_key_id,
            top_ids=initial_top_ids,
            agent_policy_id=agent_policy_id,
            agent_actions=(
                "match:speech-only-primary",
                "retrieve:speech-only",
                *(
                    f"compare:pairwise-boundary-rank-{rank}"
                    for rank in range(1, len(challengers) + 1)
                ),
                "select:retain-primary-for-support",
            ),
            agent_escalated=True,
            agent_vote_key_ids=(primary_key_id, *support_votes),
            agent_steps=initial_steps + tuple(comparison_steps),
            decision_agent_aggregator_id=agent_aggregator_id,
        )

    if matcher_policy_id == "M9":
        assert decision_graph is not None
        primary_instruction = (
            "Match the spoken command to exactly one opaque key. Use the speech signal and "
            "the supplied K1 text cards jointly. Return only the selected key_id."
        )
        retrieval_instruction = (
            f"Retrieve exactly {top_k} distinct opaque keys for the spoken command, ranked "
            "from most to least compatible. Use the speech signal and supplied K1 text "
            "cards jointly. Return only the ordered key_ids."
        )
        initial_responses = contact_many_with_overrides(
            (
                (
                    "primary-listwise",
                    primary_instruction,
                    cards,
                    render_speech_native_keys(cards, "K1"),
                    {
                        "response_format": _key_choice_response_format(
                            name="speech_native_primary_key_choice",
                            key_ids=tuple(card.key_id for card in cards),
                        )
                    },
                ),
                (
                    f"speech-retrieve-top-{top_k}",
                    retrieval_instruction,
                    cards,
                    render_speech_native_keys(cards, "K1"),
                    {
                        "response_format": _top_key_choice_response_format(
                            key_ids=tuple(card.key_id for card in cards),
                            top_k=top_k,
                        )
                    },
                ),
            )
        )
        primary_key_id = _selected_key_id(initial_responses[0], allowed)
        initial_top_ids = _selected_top_keys(initial_responses[1], allowed, top_k)
        initial_steps: tuple[Mapping[str, object], ...] = (
            {
                "action_id": "match:speech-only-primary",
                "key_id": primary_key_id,
                "top_key_ids": [],
                "calls": 1,
                "parse_failure": primary_key_id is None,
            },
            {
                "action_id": "retrieve:speech-only",
                "key_id": initial_top_ids[0] if initial_top_ids else None,
                "top_key_ids": list(initial_top_ids),
                "calls": 1,
                "parse_failure": len(initial_top_ids) != top_k,
            },
        )
        if primary_key_id is None or len(initial_top_ids) != top_k:
            return finish(
                primary_key_id,
                top_ids=initial_top_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "backtrack:invalid-initial-factor-support",
                ),
                agent_escalated=True,
                agent_vote_key_ids=(primary_key_id,),
                agent_steps=initial_steps,
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        initial_cards = tuple(by_key[key_id] for key_id in initial_top_ids)
        graph_text = render_decision_graph_neighborhood(
            graph=decision_graph,
            key_cards=cards,
            candidate_key_ids=initial_top_ids,
        )
        factor_response = contact(
            "link-factors",
            "Select two through five existing factor ids that are directly supported by "
            "the spoken command, plus at most one existing boundary id when it captures "
            "the unresolved distinction. Return only the registered ids. Do not generate "
            "a paraphrase, rationale, or free-form semantic field.",
            initial_cards,
            "Initial key cards:\n"
            + render_speech_native_keys(initial_cards, "K1")
            + "\n\nReachable decision graph:\n"
            + graph_text,
            decoding_overrides={
                "response_format": factor_link_response_format(
                    graph=decision_graph,
                    key_cards=cards,
                    candidate_key_ids=initial_top_ids,
                )
            },
        )
        factor_state = parse_factor_link_state(
            factor_response,
            graph=decision_graph,
            key_cards=cards,
            candidate_key_ids=initial_top_ids,
        )
        if factor_state is None:
            return finish(
                primary_key_id,
                top_ids=initial_top_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "link:knowledge-factors",
                    "backtrack:invalid-factor-link-state",
                ),
                agent_escalated=True,
                agent_vote_key_ids=(primary_key_id,),
                agent_steps=(
                    *initial_steps,
                    {
                        "action_id": "link:knowledge-factors",
                        "key_id": None,
                        "top_key_ids": list(initial_top_ids),
                        "calls": 1,
                        "parse_failure": True,
                    },
                ),
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        expanded = expand_decision_graph_candidates(
            graph=decision_graph,
            initial_key_ids=initial_top_ids,
            state=factor_state,
            cap=min(6, len(cards)),
        )
        expanded_cards = tuple(by_key[key_id] for key_id in expanded.key_ids)
        rerank_top_k = min(3, len(expanded_cards))
        factor_state_text = render_factor_link_state(
            graph=decision_graph, state=factor_state
        )
        rerank_response = contact(
            f"factor-rerank-top-{rerank_top_k}",
            f"Rank exactly {rerank_top_k} opaque keys for the spoken command. The selected "
            "knowledge factors are advisory evidence; re-evaluate them against the speech "
            "signal carried in this request. Return only the ordered key_ids.",
            expanded_cards,
            factor_state_text
            + "\n\nExpanded key cards:\n"
            + render_speech_native_keys(expanded_cards, "K1"),
            decoding_overrides={
                "response_format": _top_key_choice_response_format(
                    key_ids=expanded.key_ids,
                    top_k=rerank_top_k,
                )
            },
        )
        reranked_ids = _selected_top_keys(
            rerank_response, set(expanded.key_ids), rerank_top_k
        )
        factor_step: Mapping[str, object] = {
            "action_id": "link:knowledge-factors",
            "key_id": None,
            "top_key_ids": list(initial_top_ids),
            "calls": 1,
            "parse_failure": False,
            "factor_link_state": {
                "factor_ids": list(factor_state.factor_ids),
                "boundary_id": factor_state.boundary_id,
            },
        }
        expansion_step: Mapping[str, object] = {
            "action_id": "tool:expand-factor-graph",
            "key_id": None,
            "top_key_ids": list(initial_top_ids),
            "calls": 0,
            "parse_failure": False,
            "expanded_key_ids": list(expanded.key_ids),
            "distance_by_key": dict(expanded.distance_by_key),
        }
        rerank_step: Mapping[str, object] = {
            "action_id": "rerank:speech-plus-factor-state",
            "key_id": reranked_ids[0] if reranked_ids else None,
            "top_key_ids": list(reranked_ids),
            "calls": 1,
            "parse_failure": len(reranked_ids) != rerank_top_k,
        }
        common_steps = (*initial_steps, factor_step, expansion_step, rerank_step)
        if len(reranked_ids) != rerank_top_k:
            return finish(
                primary_key_id,
                top_ids=reranked_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "link:knowledge-factors",
                    "tool:expand-factor-graph",
                    "rerank:speech-plus-factor-state",
                    "backtrack:invalid-factor-rerank",
                ),
                agent_escalated=True,
                agent_vote_key_ids=(primary_key_id,),
                agent_steps=common_steps,
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        rerank_key_id = reranked_ids[0]
        if rerank_key_id == primary_key_id:
            return finish(
                primary_key_id,
                top_ids=reranked_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "link:knowledge-factors",
                    "tool:expand-factor-graph",
                    "rerank:speech-plus-factor-state",
                    "stop:primary-rerank-agree",
                    "select:retain-primary-for-support",
                ),
                agent_escalated=True,
                agent_vote_key_ids=(primary_key_id, rerank_key_id),
                agent_steps=common_steps,
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        boundary_path = decision_boundary_path(
            graph=decision_graph,
            source_key_id=primary_key_id,
            target_key_id=rerank_key_id,
            max_edges=2,
        )
        if not boundary_path:
            return finish(
                primary_key_id,
                top_ids=reranked_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "link:knowledge-factors",
                    "tool:expand-factor-graph",
                    "rerank:speech-plus-factor-state",
                    "backtrack:no-boundary-path",
                    "select:retain-primary-for-support",
                ),
                agent_escalated=True,
                agent_vote_key_ids=(primary_key_id, rerank_key_id),
                agent_steps=common_steps,
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        boundaries_by_id = {
            boundary.boundary_id: boundary for boundary in decision_graph.boundaries
        }
        path_lines = ["Boundary path:"]
        for boundary_id in boundary_path:
            boundary = boundaries_by_id[boundary_id]
            path_lines.extend(
                (
                    f"[{boundary.boundary_id}] endpoints="
                    f"{boundary.left_key_id},{boundary.right_key_id}",
                    f"{boundary.left_key_id} factors: "
                    f"{','.join(boundary.left_factor_ids)}",
                    f"{boundary.left_key_id} exclusion: {boundary.left_exclusion}",
                    f"{boundary.right_key_id} factors: "
                    f"{','.join(boundary.right_factor_ids)}",
                    f"{boundary.right_key_id} exclusion: {boundary.right_exclusion}",
                )
            )
        boundary_text = factor_state_text + "\n\n" + "\n".join(path_lines)
        pair_ids = (primary_key_id, rerank_key_id)
        response_format = _key_choice_response_format(
            name="speech_native_factor_boundary_choice",
            key_ids=pair_ids,
        )
        boundary_requests = []
        for order_id, ordered_ids in (
            ("ab", pair_ids),
            ("ba", tuple(reversed(pair_ids))),
        ):
            ordered_cards = tuple(by_key[key_id] for key_id in ordered_ids)
            boundary_requests.append(
                (
                    f"boundary-rank-1-{order_id}",
                    "Choose which of exactly two opaque keys better matches the spoken "
                    "command. Use the selected factor nodes and registered boundary path as "
                    "advisory evidence, but resolve conflicts from the speech signal. Treat "
                    "card order as irrelevant and return only key_id.",
                    ordered_cards,
                    boundary_text
                    + "\n\nCandidate key cards:\n"
                    + render_speech_native_keys(ordered_cards, "K1"),
                    {"response_format": response_format},
                )
            )
        boundary_responses = contact_many_with_overrides(tuple(boundary_requests))
        boundary_votes = tuple(
            _selected_key_id(response, set(pair_ids)) for response in boundary_responses
        )
        return finish(
            primary_key_id,
            top_ids=reranked_ids,
            agent_policy_id=agent_policy_id,
            agent_actions=(
                "match:speech-only-primary",
                "retrieve:speech-only",
                "link:knowledge-factors",
                "tool:expand-factor-graph",
                "rerank:speech-plus-factor-state",
                "compare:boundary-ab",
                "compare:boundary-ba",
                "select:retain-primary-for-support",
            ),
            agent_escalated=True,
            agent_vote_key_ids=(
                primary_key_id,
                rerank_key_id,
                *boundary_votes,
            ),
            agent_steps=(
                *common_steps,
                {
                    "action_id": "compare:factor-boundary",
                    "key_id": None,
                    "top_key_ids": [primary_key_id, rerank_key_id],
                    "calls": 2,
                    "parse_failure": any(vote is None for vote in boundary_votes),
                    "boundary_path_ids": list(boundary_path),
                    "ab_key_id": boundary_votes[0],
                    "ba_key_id": boundary_votes[1],
                    "causal_parent_ids": [
                        "link:knowledge-factors",
                        "tool:expand-factor-graph",
                        "rerank:speech-plus-factor-state",
                    ],
                },
            ),
            decision_agent_aggregator_id=agent_aggregator_id,
        )

    if matcher_policy_id == "M11":
        assert decision_graph is not None
        key_ids = tuple(card.key_id for card in cards)
        rendered_keys = render_speech_native_keys(cards, "K1")
        initial_responses = contact_many_with_overrides(
            (
                (
                    "primary-listwise",
                    "Match the spoken command to exactly one opaque key. Use the original "
                    "speech signal and all action-complete K1 text cards jointly. Return "
                    "only key_id.",
                    cards,
                    rendered_keys,
                    {
                        "response_format": _key_choice_response_format(
                            name="speech_native_adaptive_primary_key_choice",
                            key_ids=key_ids,
                        )
                    },
                ),
                (
                    f"speech-retrieve-top-{top_k}",
                    f"Retrieve exactly {top_k} distinct opaque keys for the spoken "
                    "command, ranked from most to least compatible. Use the original "
                    "speech signal and all action-complete K1 cards jointly.",
                    cards,
                    rendered_keys,
                    {
                        "response_format": _top_key_choice_response_format(
                            key_ids=key_ids,
                            top_k=top_k,
                        )
                    },
                ),
            )
        )
        primary_key_id = _selected_key_id(initial_responses[0], allowed)
        initial_top_ids = _selected_top_keys(initial_responses[1], allowed, top_k)
        initial_steps: tuple[Mapping[str, object], ...] = (
            {
                "action_id": "match:speech-only-primary",
                "key_id": primary_key_id,
                "top_key_ids": [],
                "calls": 1,
                "parse_failure": primary_key_id is None,
                "new_knowledge_ids": [],
            },
            {
                "action_id": "retrieve:speech-only",
                "key_id": initial_top_ids[0] if initial_top_ids else None,
                "top_key_ids": list(initial_top_ids),
                "calls": 1,
                "parse_failure": len(initial_top_ids) != top_k,
                "new_knowledge_ids": [],
            },
        )
        if primary_key_id is None or len(initial_top_ids) != top_k:
            return finish(
                primary_key_id,
                top_ids=initial_top_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "backtrack:invalid-initial-adaptive-state",
                ),
                agent_escalated=True,
                agent_vote_key_ids=(primary_key_id,),
                agent_steps=initial_steps,
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        candidate_cards = tuple(by_key[key_id] for key_id in initial_top_ids)
        action_response = contact(
            "candidate-action-state",
            "Re-observe the original speech while using only the retrieved candidate "
            "cards and their registered task factors. Select the best candidate and one "
            "to three factor ids supported by the speech. "
            + (
                "The first factor id must be an operation factor registered to the "
                "selected key. "
                if agent_policy_id == "speech-conditioned-adaptive-evidence-gap-v2"
                else ""
            )
            + "Return no rationale, summary, or free-form text.",
            candidate_cards,
            render_speech_native_keys(candidate_cards, "K1")
            + "\n\n"
            + _render_candidate_action_context(
                graph=decision_graph,
                candidate_key_ids=initial_top_ids,
            ),
            decoding_overrides={
                "response_format": candidate_action_state_response_format(
                    graph=decision_graph,
                    candidate_key_ids=initial_top_ids,
                    key_conditioned=(
                        agent_policy_id == "speech-conditioned-adaptive-evidence-gap-v2"
                    ),
                )
            },
        )
        action_state = parse_candidate_action_state(
            action_response,
            graph=decision_graph,
            candidate_key_ids=initial_top_ids,
        )
        action_step: Mapping[str, object] = {
            "action_id": "link:candidate-action-state",
            "key_id": action_state.key_id if action_state is not None else None,
            "top_key_ids": list(initial_top_ids),
            "factor_ids": (
                list(action_state.factor_ids) if action_state is not None else []
            ),
            "calls": 1,
            "parse_failure": action_state is None,
            "new_knowledge_ids": (
                list(action_state.factor_ids) if action_state is not None else []
            ),
            "causal_parent_ids": ["retrieve:speech-only"],
        }
        if action_state is None:
            return finish(
                primary_key_id,
                top_ids=initial_top_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "link:candidate-action-state",
                    "backtrack:invalid-candidate-action-state",
                ),
                agent_escalated=True,
                agent_vote_key_ids=(primary_key_id, initial_top_ids[0]),
                agent_steps=(*initial_steps, action_step),
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        base_actions = (
            "match:speech-only-primary",
            "retrieve:speech-only",
            "link:candidate-action-state",
        )
        base_votes = (primary_key_id, initial_top_ids[0], action_state.key_id)
        if len(set(base_votes)) == 1:
            return finish(
                primary_key_id,
                top_ids=initial_top_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(*base_actions, "stop:complete-consistent-state"),
                agent_escalated=False,
                agent_vote_key_ids=base_votes,
                agent_steps=(*initial_steps, action_step),
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        challenger_key_id = (
            action_state.key_id
            if action_state.key_id != primary_key_id
            else initial_top_ids[0]
        )
        boundary = _decision_boundary_for_pair(
            graph=decision_graph,
            left_key_id=primary_key_id,
            right_key_id=challenger_key_id,
        )
        if boundary is None:
            return finish(
                primary_key_id,
                top_ids=initial_top_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(*base_actions, "stop:no-registered-pair-boundary"),
                agent_escalated=False,
                agent_vote_key_ids=base_votes,
                agent_steps=(*initial_steps, action_step),
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        pair_cards = (by_key[primary_key_id], by_key[challenger_key_id])
        boundary_context = _render_adaptive_boundary_context(
            boundary=boundary,
            action_state=action_state,
        )
        boundary_responses = contact_many_with_overrides(
            (
                (
                    "boundary-ab",
                    "Compare only these two candidates against the original speech and "
                    "the newly retrieved pair boundary. Return only key_id.",
                    pair_cards,
                    boundary_context
                    + "\n\nCandidate cards:\n"
                    + render_speech_native_keys(pair_cards, "K1"),
                    {
                        "response_format": _key_choice_response_format(
                            name="speech_native_adaptive_boundary_ab",
                            key_ids=tuple(card.key_id for card in pair_cards),
                        )
                    },
                ),
                (
                    "boundary-ba",
                    "Compare only these two candidates against the original speech and "
                    "the newly retrieved pair boundary. Return only key_id.",
                    tuple(reversed(pair_cards)),
                    boundary_context
                    + "\n\nCandidate cards in reverse order:\n"
                    + render_speech_native_keys(tuple(reversed(pair_cards)), "K1"),
                    {
                        "response_format": _key_choice_response_format(
                            name="speech_native_adaptive_boundary_ba",
                            key_ids=tuple(card.key_id for card in reversed(pair_cards)),
                        )
                    },
                ),
            )
        )
        pair_allowed = {primary_key_id, challenger_key_id}
        ab_key_id = _selected_key_id(boundary_responses[0], pair_allowed)
        ba_key_id = _selected_key_id(boundary_responses[1], pair_allowed)
        boundary_step: Mapping[str, object] = {
            "action_id": f"retrieve:pair-boundary:{boundary.boundary_id}",
            "boundary_id": boundary.boundary_id,
            "primary_key_id": primary_key_id,
            "challenger_key_id": challenger_key_id,
            "information_gap": "candidate-disagreement",
            "ab_key_id": ab_key_id,
            "ba_key_id": ba_key_id,
            "calls": 2,
            "parse_failure": ab_key_id is None or ba_key_id is None,
            "new_knowledge_ids": [boundary.boundary_id],
            "causal_parent_ids": ["link:candidate-action-state"],
        }
        return finish(
            primary_key_id,
            top_ids=initial_top_ids,
            agent_policy_id=agent_policy_id,
            agent_actions=(
                *base_actions,
                f"retrieve:pair-boundary:{boundary.boundary_id}",
                "compare:boundary-ab",
                "compare:boundary-ba",
                (
                    "backtrack:invalid-pair-boundary-comparison"
                    if ab_key_id is None or ba_key_id is None
                    else "select:retain-primary-for-support"
                ),
            ),
            agent_escalated=True,
            agent_vote_key_ids=(*base_votes, ab_key_id, ba_key_id),
            agent_steps=(*initial_steps, action_step, boundary_step),
            decision_agent_aggregator_id=agent_aggregator_id,
        )

    if matcher_policy_id == "M10":
        assert decision_graph is not None
        key_ids = tuple(card.key_id for card in cards)
        rendered_keys = render_speech_native_keys(cards, "K1")
        initial_responses = contact_many_with_overrides(
            (
                (
                    "primary-listwise",
                    "Match the spoken command to exactly one opaque key. Use the speech "
                    "signal and supplied K1 text cards jointly. Return only key_id.",
                    cards,
                    rendered_keys,
                    {
                        "response_format": _key_choice_response_format(
                            name="speech_native_primary_key_choice",
                            key_ids=key_ids,
                        )
                    },
                ),
                (
                    f"speech-retrieve-top-{top_k}",
                    f"Retrieve exactly {top_k} distinct opaque keys for the spoken "
                    "command, ranked from most to least compatible. Use the speech signal "
                    "and supplied K1 text cards jointly. Return only the ordered key_ids.",
                    cards,
                    rendered_keys,
                    {
                        "response_format": _top_key_choice_response_format(
                            key_ids=key_ids,
                            top_k=top_k,
                        )
                    },
                ),
            )
        )
        primary_key_id = _selected_key_id(initial_responses[0], allowed)
        initial_top_ids = _selected_top_keys(initial_responses[1], allowed, top_k)
        initial_steps: tuple[Mapping[str, object], ...] = (
            {
                "action_id": "match:speech-only-primary",
                "key_id": primary_key_id,
                "top_key_ids": [],
                "calls": 1,
                "parse_failure": primary_key_id is None,
            },
            {
                "action_id": "retrieve:speech-only",
                "key_id": initial_top_ids[0] if initial_top_ids else None,
                "top_key_ids": list(initial_top_ids),
                "calls": 1,
                "parse_failure": len(initial_top_ids) != top_k,
            },
        )
        if primary_key_id is None or len(initial_top_ids) != top_k:
            return finish(
                primary_key_id,
                top_ids=initial_top_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "backtrack:invalid-initial-candidate-evidence",
                ),
                agent_escalated=True,
                agent_vote_key_ids=(primary_key_id,),
                agent_steps=initial_steps,
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        expansion = expand_decision_graph_neighborhood(
            graph=decision_graph,
            initial_key_ids=initial_top_ids,
            cap=min(6, len(cards)),
        )
        expansion_step: Mapping[str, object] = {
            "action_id": "tool:expand-candidate-neighborhood",
            "key_id": None,
            "top_key_ids": list(initial_top_ids),
            "calls": 0,
            "parse_failure": False,
            "expanded_key_ids": list(expansion.key_ids),
            "distance_by_key": dict(expansion.distance_by_key),
        }
        evidence_requests: list[
            tuple[
                str,
                str,
                Sequence[KeyCardV1],
                str,
                Mapping[str, object],
            ]
        ] = []
        for candidate_key_id in expansion.key_ids:
            candidate_card = by_key[candidate_key_id]
            evidence_requests.extend(
                (
                    (
                        f"support-{candidate_key_id}",
                        "Judge whether this candidate's domain and operation are supported "
                        "by the spoken command. Select only registered factor ids that the "
                        "speech supports. Return no rationale or transcript.",
                        (candidate_card,),
                        "Candidate key card:\n"
                        + render_speech_native_keys((candidate_card,), "K2")
                        + "\n\n"
                        + _render_candidate_factor_context(
                            graph=decision_graph,
                            candidate_key_id=candidate_key_id,
                        ),
                        {
                            "response_format": candidate_support_response_format(
                                graph=decision_graph,
                                candidate_key_id=candidate_key_id,
                            )
                        },
                    ),
                    (
                        f"counterevidence-{candidate_key_id}",
                        "Search for speech evidence that contradicts this candidate by "
                        "using only the registered hard-negative boundaries. Select only "
                        "request-local boundary ids. Return no rationale or transcript.",
                        (candidate_card,),
                        "Candidate key card:\n"
                        + render_speech_native_keys((candidate_card,), "K2")
                        + "\n\n"
                        + _render_candidate_boundary_context(
                            graph=decision_graph,
                            candidate_key_id=candidate_key_id,
                        ),
                        {
                            "response_format": (
                                candidate_counterevidence_response_format(
                                    graph=decision_graph,
                                    candidate_key_id=candidate_key_id,
                                )
                            )
                        },
                    ),
                )
            )
        evidence_responses = contact_many_with_overrides(tuple(evidence_requests))
        support_by_key: dict[str, CandidateSupportStateV1 | None] = {}
        counterevidence_by_key: dict[str, CandidateCounterevidenceStateV1 | None] = {}
        evidence_steps: list[Mapping[str, object]] = []
        evidence_actions: list[str] = []
        for index, candidate_key_id in enumerate(expansion.key_ids):
            support = parse_candidate_support_state(
                evidence_responses[index * 2],
                graph=decision_graph,
                candidate_key_id=candidate_key_id,
            )
            counterevidence = parse_candidate_counterevidence_state(
                evidence_responses[index * 2 + 1],
                graph=decision_graph,
                candidate_key_id=candidate_key_id,
            )
            support_by_key[candidate_key_id] = support
            counterevidence_by_key[candidate_key_id] = counterevidence
            evidence_actions.extend(
                (
                    f"acquire:support:{candidate_key_id}",
                    f"seek:counterevidence:{candidate_key_id}",
                )
            )
            evidence_steps.append(
                {
                    "action_id": f"acquire:candidate-evidence:{candidate_key_id}",
                    "candidate_key_id": candidate_key_id,
                    "support_compatible": (
                        support.compatible if support is not None else None
                    ),
                    "support_confidence": (
                        support.confidence if support is not None else None
                    ),
                    "support_factor_ids": (
                        list(support.factor_ids) if support is not None else []
                    ),
                    "counterevidence_contradicted": (
                        counterevidence.contradicted
                        if counterevidence is not None
                        else None
                    ),
                    "counterevidence_confidence": (
                        counterevidence.confidence
                        if counterevidence is not None
                        else None
                    ),
                    "counterevidence_boundary_ids": (
                        list(counterevidence.boundary_ids)
                        if counterevidence is not None
                        else []
                    ),
                    "calls": 2,
                    "parse_failure": support is None or counterevidence is None,
                    "causal_parent_ids": [
                        "retrieve:speech-only",
                        "tool:expand-candidate-neighborhood",
                    ],
                }
            )
        common_actions = (
            "match:speech-only-primary",
            "retrieve:speech-only",
            "tool:expand-candidate-neighborhood",
            *evidence_actions,
        )
        common_steps = (*initial_steps, expansion_step, *evidence_steps)
        if any(step["parse_failure"] for step in evidence_steps):
            return finish(
                primary_key_id,
                top_ids=expansion.key_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    *common_actions,
                    "backtrack:invalid-candidate-evidence",
                ),
                agent_escalated=True,
                agent_vote_key_ids=(primary_key_id,),
                agent_steps=common_steps,
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        challenger_ids = tuple(
            key_id for key_id in expansion.key_ids if key_id != primary_key_id
        )
        reconciliation_requests = []
        for candidate_key_id in challenger_ids:
            support = support_by_key[candidate_key_id]
            counterevidence = counterevidence_by_key[candidate_key_id]
            assert support is not None and counterevidence is not None
            pair_cards = (by_key[primary_key_id], by_key[candidate_key_id])
            reconciliation_requests.append(
                (
                    f"reconcile-{candidate_key_id}",
                    "Choose whether the candidate evidence justifies replacing the "
                    "speech-only primary. Re-evaluate the enum-bound semantic state against "
                    "the original speech carried in this request. Return only action.",
                    pair_cards,
                    _render_candidate_reconciliation_state(
                        graph=decision_graph,
                        candidate_key_id=candidate_key_id,
                        support=support,
                        counterevidence=counterevidence,
                    )
                    + "\n\nPrimary and candidate key cards:\n"
                    + render_speech_native_keys(pair_cards, "K2"),
                    {"response_format": (_candidate_reconciliation_response_format())},
                )
            )
        reconciliation_responses = contact_many_with_overrides(
            tuple(reconciliation_requests)
        )
        reconciliation_steps: list[Mapping[str, object]] = []
        reconciliation_actions: list[str] = []
        votes: list[str | None] = [primary_key_id]
        for candidate_key_id, response in zip(
            challenger_ids, reconciliation_responses, strict=True
        ):
            selected_action = _parse_candidate_reconciliation(response)
            support = support_by_key[candidate_key_id]
            counterevidence = counterevidence_by_key[candidate_key_id]
            assert support is not None and counterevidence is not None
            reconciliation_actions.append(f"reconcile:{candidate_key_id}")
            selected_key_id = (
                candidate_key_id
                if selected_action == "accept_candidate"
                else primary_key_id
                if selected_action == "retain_primary"
                else None
            )
            votes.append(selected_key_id)
            reconciliation_steps.append(
                {
                    "action_id": f"reconcile:candidate:{candidate_key_id}",
                    "candidate_key_id": candidate_key_id,
                    "selected_action": selected_action,
                    "key_id": selected_key_id,
                    "selected_factor_ids": list(support.factor_ids),
                    "selected_boundary_ids": list(counterevidence.boundary_ids),
                    "calls": 1,
                    "parse_failure": selected_action is None,
                    "causal_parent_ids": [
                        f"acquire:candidate-evidence:{candidate_key_id}"
                    ],
                }
            )
        return finish(
            primary_key_id,
            top_ids=expansion.key_ids,
            agent_policy_id=agent_policy_id,
            agent_actions=(
                *common_actions,
                *reconciliation_actions,
                (
                    "backtrack:invalid-candidate-reconciliation"
                    if any(step["parse_failure"] for step in reconciliation_steps)
                    else "select:retain-primary-for-support"
                ),
            ),
            agent_escalated=True,
            agent_vote_key_ids=tuple(votes),
            agent_steps=(*common_steps, *reconciliation_steps),
            decision_agent_aggregator_id=agent_aggregator_id,
        )

    if matcher_policy_id == "M7":
        state_policy_ids = (
            "balanced-evidence-v1",
            "primary-challenge-v1",
            "retrieval-gap-v1",
        )
        primary_instruction = (
            "Match the spoken command to exactly one opaque key. Use the speech signal and "
            "the supplied key representations jointly. Return one JSON object with exactly "
            "one field named key_id. Its string value must be copied verbatim from a supplied "
            "key heading; do not invent or shorten an id."
        )
        retrieval_instruction = (
            f"Retrieve exactly {top_k} distinct opaque keys for the spoken command, "
            "ranked from most to least compatible. Return a single-line JSON object with "
            f"exactly one field named key_ids whose value is an array of exactly {top_k} "
            "ids copied verbatim from supplied key headings. Do not use Markdown or code "
            "fences and do not add any other text."
        )
        initial_responses = contact_many(
            (
                (
                    "primary-listwise",
                    primary_instruction,
                    cards,
                    render_speech_native_keys(cards, key_representation_id),
                ),
                (
                    f"speech-retrieve-top-{top_k}",
                    retrieval_instruction,
                    cards,
                    render_speech_native_keys(cards, key_representation_id),
                ),
            )
        )
        primary_key_id = _selected_key_id(initial_responses[0], allowed)
        initial_top_ids = _selected_top_keys(initial_responses[1], allowed, top_k)
        initial_steps: tuple[Mapping[str, object], ...] = (
            {
                "action_id": "match:speech-only-primary",
                "key_id": primary_key_id,
                "top_key_ids": [],
                "calls": 1,
                "parse_failure": primary_key_id is None,
            },
            {
                "action_id": "retrieve:speech-only",
                "key_id": initial_top_ids[0] if initial_top_ids else None,
                "top_key_ids": list(initial_top_ids),
                "calls": 1,
                "parse_failure": len(initial_top_ids) != top_k,
            },
        )
        if primary_key_id is None or len(initial_top_ids) != top_k:
            return finish(
                primary_key_id,
                top_ids=initial_top_ids,
                agent_policy_id=agent_policy_id,
                agent_actions=(
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "backtrack:invalid-initial-action-support",
                ),
                agent_escalated=True,
                agent_vote_key_ids=(primary_key_id, None, None, None),
                agent_steps=initial_steps,
                decision_agent_aggregator_id=agent_aggregator_id,
            )

        initial_cards = tuple(by_key[key_id] for key_id in initial_top_ids)
        candidate_json = json.dumps(
            list(initial_top_ids), ensure_ascii=False, separators=(",", ":")
        )
        state_schema_instruction = (
            "Return one bare JSON object without Markdown or code fences and with exactly "
            "these fields: candidate_key_ids, domain, operation, target, constraints, "
            "exclusions, unresolved_ambiguity, and evidence. candidate_key_ids must be "
            f"exactly {candidate_json}. domain, operation, target, and unresolved_ambiguity "
            "must each be a non-empty JSON string; use the string unspecified or none "
            "instead of null, true, or false. constraints and exclusions must be arrays "
            "of at most five non-empty JSON strings. evidence must contain exactly one "
            "evidence object for each candidate, in the same candidate order. Every "
            "evidence object must have exactly key_id, field, and quote. field must be "
            "exactly definition, positive_examples, or contrastive_boundary. quote must "
            "be copied exactly from the named field of that same key. When field is "
            "positive_examples, copy from exactly one example and never include the | "
            "separator or combine examples."
        )
        state_objectives = {
            "balanced-evidence-v1": (
                "Extract the most direct domain, operation, target, constraints, exclusions, "
                "and unresolved candidate boundary supported jointly by the speech signal "
                "and retrieved cards. Do not force a change from the speech-only primary."
            ),
            "primary-challenge-v1": (
                f"Try to falsify the opaque speech-only primary {primary_key_id} without "
                "forcing a change. Record operation cues that support or contradict it, use "
                "exclusions for conflicting cues, and name the exact candidate boundary in "
                "unresolved_ambiguity."
            ),
            "retrieval-gap-v1": (
                "Assume the initial top-k may have omitted the correct key. Extract the "
                "speech-grounded domain, operation, target, and requirements that a missing "
                "key would need while citing only the visible candidates as boundaries. Do "
                "not invent a missing key id and do not transcribe the utterance."
            ),
        }
        state_responses = contact_many_with_overrides(
            tuple(
                (
                    f"state-{state_policy_id}",
                    "Build a knowledge-grounded semantic query state for the spoken command. "
                    "Use only the retrieved key cards and the speech signal carried in this "
                    "request. Do not transcribe or paraphrase the utterance. "
                    + state_objectives[state_policy_id]
                    + " "
                    + state_schema_instruction,
                    initial_cards,
                    "Retrieved key cards:\n"
                    + render_speech_native_keys(initial_cards, "K2"),
                    {
                        "max_tokens": 512,
                        "response_format": _grounded_query_state_response_format(
                            candidate_key_ids=initial_top_ids,
                            cards_by_key=by_key,
                            key_representation_id="K2",
                        ),
                    },
                )
                for state_policy_id in state_policy_ids
            )
        )
        branch_records: list[dict[str, object]] = []
        for state_policy_id, state_response in zip(
            state_policy_ids, state_responses, strict=True
        ):
            state = parse_grounded_query_state(
                state_response,
                candidate_key_ids=initial_top_ids,
                cards_by_key=by_key,
                key_representation_id="K2",
            )
            branch_records.append(
                {
                    "state_policy_id": state_policy_id,
                    "state": state,
                    "top_key_ids": (),
                    "verifier_scores": {},
                    "key_id": None,
                    "calls": 1,
                    "parse_failure": state is None,
                }
            )

        retrievable = [
            record for record in branch_records if record["state"] is not None
        ]
        retrieval_responses = contact_many(
            tuple(
                (
                    f"grounded-retrieve-{record['state_policy_id']}-top-{top_k}",
                    retrieval_instruction
                    + " The validated grounded query state is advisory. Re-evaluate it "
                    "against the speech signal and search the complete key collection, "
                    "including keys outside the first retrieval.",
                    cards,
                    "Validated grounded query state:\n"
                    + json.dumps(
                        record["state"].as_json(),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n\nKeys:\n"
                    + render_speech_native_keys(cards, key_representation_id),
                )
                for record in retrievable
            )
        )
        for record, retrieval_response in zip(
            retrievable, retrieval_responses, strict=True
        ):
            record["calls"] = int(record["calls"]) + 1
            refined_top_ids = _selected_top_keys(retrieval_response, allowed, top_k)
            record["top_key_ids"] = refined_top_ids
            if len(refined_top_ids) != top_k:
                record["parse_failure"] = True

        verifier_requests: list[tuple[str, str, Sequence[KeyCardV1], str | None]] = []
        verifier_owners: list[tuple[dict[str, object], str]] = []
        for record in branch_records:
            refined_top_ids = record["top_key_ids"]
            if record["parse_failure"] or not isinstance(refined_top_ids, tuple):
                continue
            state = record["state"]
            assert isinstance(state, GroundedQueryStateV1)
            state_json = json.dumps(
                state.as_json(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for key_id in refined_top_ids:
                verifier_requests.append(
                    (
                        f"grounded-verify-{record['state_policy_id']}-{key_id}",
                        "Judge whether the spoken command matches both the domain and "
                        "requested operation of this one candidate key. The grounded query "
                        "state is advisory; reject it when it conflicts with the speech "
                        "signal. Reject a merely related topic when the requested operation "
                        "differs. Respond only as "
                        '{"compatible":true,"confidence":0}, with confidence from 0 to 100.',
                        (by_key[key_id],),
                        "Validated grounded query state:\n"
                        + state_json
                        + "\n\nCandidate key:\n"
                        + render_speech_native_keys(
                            (by_key[key_id],), key_representation_id
                        ),
                    )
                )
                verifier_owners.append((record, key_id))
        verifier_responses = contact_many(tuple(verifier_requests))
        for (record, key_id), verifier_response in zip(
            verifier_owners, verifier_responses, strict=True
        ):
            record["calls"] = int(record["calls"]) + 1
            parsed = _compatibility(verifier_response)
            if parsed is None:
                record["parse_failure"] = True
            else:
                scores = record["verifier_scores"]
                assert isinstance(scores, dict)
                scores[key_id] = parsed

        tied_records: list[tuple[dict[str, object], tuple[str, ...]]] = []
        for record in branch_records:
            refined_top_ids = record["top_key_ids"]
            scores = record["verifier_scores"]
            if (
                record["parse_failure"]
                or not isinstance(refined_top_ids, tuple)
                or not isinstance(scores, dict)
                or len(scores) != top_k
            ):
                continue
            compatible = [key_id for key_id in refined_top_ids if scores[key_id][0]]
            pool = compatible or list(refined_top_ids)
            best_score = max(scores[key_id][1] for key_id in pool)
            tied = tuple(key_id for key_id in pool if scores[key_id][1] == best_score)
            if len(tied) == 1:
                record["key_id"] = tied[0]
            else:
                tied_records.append((record, tied))

        tie_responses = contact_many(
            tuple(
                (
                    f"grounded-tie-{record['state_policy_id']}",
                    "Resolve the verifier tie by comparing the speech signal directly against "
                    "only these tied opaque keys. The grounded state is advisory. Return one "
                    "JSON object with exactly one field named key_id whose value is copied "
                    "verbatim from a supplied key heading.",
                    tuple(by_key[key_id] for key_id in tied),
                    "Tied keys:\n"
                    + render_speech_native_keys(
                        tuple(by_key[key_id] for key_id in tied),
                        key_representation_id,
                    ),
                )
                for record, tied in tied_records
            )
        )
        for (record, tied), tie_response in zip(
            tied_records, tie_responses, strict=True
        ):
            record["calls"] = int(record["calls"]) + 1
            record["key_id"] = _selected_key_id(tie_response, set(tied))
            if record["key_id"] is None:
                record["parse_failure"] = True

        branch_steps = tuple(
            {
                "action_id": f"explore:{record['state_policy_id']}",
                "state_policy_id": record["state_policy_id"],
                "key_id": record["key_id"],
                "top_key_ids": list(record["top_key_ids"]),
                "calls": record["calls"],
                "parse_failure": record["parse_failure"],
                "grounded_query_state": (
                    record["state"].as_json()
                    if isinstance(record["state"], GroundedQueryStateV1)
                    else None
                ),
                "verifier_scores": {
                    key_id: {
                        "compatible": score[0],
                        "confidence": score[1],
                    }
                    for key_id, score in record["verifier_scores"].items()
                },
                "causal_parent_ids": [
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                ],
            }
            for record in branch_records
        )
        return finish(
            primary_key_id,
            top_ids=initial_top_ids,
            agent_policy_id=agent_policy_id,
            agent_actions=(
                "match:speech-only-primary",
                "retrieve:speech-only",
                *(f"explore:{state_policy_id}" for state_policy_id in state_policy_ids),
                "select:retain-primary-for-support",
            ),
            agent_escalated=True,
            agent_vote_key_ids=(
                primary_key_id,
                *(record["key_id"] for record in branch_records),
            ),
            agent_steps=initial_steps + branch_steps,
            decision_agent_aggregator_id=agent_aggregator_id,
        )

    if matcher_policy_id == "M6":
        policy_id = agent_policy_id
        aggregator_id = "grounded-refined-primary-fallback-v1"
        state_key_representation_id = "K2"
        primary = nested_decision("M1", cards, "M6:M1:primary")
        retrieval_instruction = (
            f"Retrieve exactly {top_k} distinct opaque keys for the spoken command, "
            "ranked from most to least compatible. Return a single-line JSON object with "
            f"exactly one field named key_ids whose value is an array of exactly {top_k} "
            "ids copied verbatim from supplied key headings. Do not use Markdown or code "
            "fences and do not add any other text."
        )
        initial_response = contact(
            f"speech-retrieve-top-{top_k}",
            retrieval_instruction,
            cards,
            render_speech_native_keys(cards, key_representation_id),
        )
        initial_top_ids = _selected_top_keys(initial_response, allowed, top_k)

        def backtrack(
            action_id: str,
            *,
            state: GroundedQueryStateV1 | None = None,
            state_contacted: bool = False,
        ) -> SpeechNativeDecision:
            actions = (
                "match:speech-only-primary",
                "retrieve:speech-only",
                *(("build:grounded-query-state",) if state_contacted else ()),
                action_id,
            )
            steps: tuple[Mapping[str, object], ...] = (
                agent_step("match:speech-only-primary", primary),
                {
                    "action_id": "retrieve:speech-only",
                    "key_id": initial_top_ids[0] if initial_top_ids else None,
                    "top_key_ids": list(initial_top_ids),
                    "calls": 1,
                    "parse_failure": len(initial_top_ids) != top_k,
                },
            )
            if state_contacted:
                steps += (
                    {
                        "action_id": "build:grounded-query-state",
                        "key_id": None,
                        "top_key_ids": list(initial_top_ids),
                        "calls": 1,
                        "parse_failure": state is None,
                    },
                )
            return finish(
                primary.key_id,
                top_ids=initial_top_ids,
                agent_policy_id=policy_id,
                agent_actions=actions,
                agent_escalated=True,
                agent_vote_key_ids=(primary.key_id, None),
                agent_steps=steps,
                decision_agent_aggregator_id=aggregator_id,
            )

        if len(initial_top_ids) != top_k:
            return backtrack("backtrack:invalid-initial-retrieval")
        initial_cards = tuple(by_key[key_id] for key_id in initial_top_ids)
        candidate_json = json.dumps(
            list(initial_top_ids),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        if agent_policy_id in {
            "knowledge-grounded-semantic-refinement-schema-v2",
            "knowledge-grounded-semantic-refinement-schema-v3",
        }:
            state_instruction = (
                "Build a knowledge-grounded semantic query state for the spoken command. "
                "Use only the retrieved key cards and the speech signal carried in this "
                "request. Do not transcribe or paraphrase the utterance. Return one bare "
                "JSON object without Markdown or code fences and with exactly these fields: "
                "candidate_key_ids, domain, operation, target, constraints, exclusions, "
                "unresolved_ambiguity, and evidence. candidate_key_ids must be exactly "
                f"{candidate_json}. domain, operation, target, and unresolved_ambiguity "
                "must each be a non-empty JSON string; use the string unspecified or none "
                "instead of null, true, or false. constraints and exclusions must be arrays "
                "of at most five non-empty JSON strings. evidence must contain exactly one "
                "evidence object for each candidate, in the same candidate order. Every "
                "evidence object must have exactly key_id, field, and quote. field must be "
                "exactly definition, positive_examples, or contrastive_boundary. quote must "
                "be copied exactly from the named field of that same key. When field is "
                "positive_examples, copy from exactly one example and never include the | "
                "separator or combine examples."
            )
        else:
            state_instruction = (
                "Build a knowledge-grounded semantic query state for the spoken command. "
                "Use only the retrieved key cards and the speech signal carried in this "
                "request. Do not transcribe or paraphrase the utterance. Return one bare JSON "
                "object with exactly these fields: candidate_key_ids, domain, operation, "
                "target, constraints, exclusions, unresolved_ambiguity, and evidence. Copy "
                "candidate_key_ids in the supplied order. constraints and exclusions are arrays "
                "of at most five short strings. evidence is an array of objects with exactly "
                "key_id, field, and quote; cite every candidate at least once, use only visible "
                "fields, and copy each quote exactly from that key card."
            )
        state_decoding_overrides: dict[str, object] = {"max_tokens": 512}
        if agent_policy_id == "knowledge-grounded-semantic-refinement-schema-v3":
            state_decoding_overrides["response_format"] = (
                _grounded_query_state_response_format(
                    candidate_key_ids=initial_top_ids,
                    cards_by_key=by_key,
                    key_representation_id=state_key_representation_id,
                )
            )
        state_response = contact(
            "build-grounded-query-state",
            state_instruction,
            initial_cards,
            "Retrieved key cards:\n"
            + render_speech_native_keys(initial_cards, state_key_representation_id),
            decoding_overrides=state_decoding_overrides,
        )
        state = parse_grounded_query_state(
            state_response,
            candidate_key_ids=initial_top_ids,
            cards_by_key=by_key,
            key_representation_id=state_key_representation_id,
        )
        if state is None:
            return backtrack("backtrack:invalid-grounding", state_contacted=True)
        state_json = json.dumps(
            state.as_json(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        refined_response = contact(
            f"grounded-retrieve-top-{top_k}",
            retrieval_instruction
            + " The validated grounded query state is advisory. Re-evaluate it against the "
            "speech signal and search the complete key collection, including keys outside "
            "the first retrieval.",
            cards,
            "Validated grounded query state:\n"
            + state_json
            + "\n\nKeys:\n"
            + render_speech_native_keys(cards, key_representation_id),
        )
        refined_top_ids = _selected_top_keys(refined_response, allowed, top_k)
        if len(refined_top_ids) != top_k:
            return backtrack(
                "backtrack:invalid-refined-retrieval",
                state=state,
                state_contacted=True,
            )
        verifier_specifications = []
        for key_id in refined_top_ids:
            card = by_key[key_id]
            verifier_instruction = (
                "Judge whether the spoken command matches both the domain and requested "
                "operation of this one candidate key. The grounded query state is advisory; "
                "reject it when it conflicts with the speech signal. Reject a merely related "
                "topic when the requested operation differs. Respond only as "
                '{"compatible":true,"confidence":0}, with confidence from 0 to 100.'
            )
            verifier_specifications.append(
                (
                    f"grounded-verify-{key_id}",
                    verifier_instruction,
                    (card,),
                    "Validated grounded query state:\n"
                    + state_json
                    + "\n\nCandidate key:\n"
                    + render_speech_native_keys((card,), key_representation_id),
                )
            )
        verifier_responses = contact_many(verifier_specifications)
        verifier_scores: dict[str, tuple[bool, float]] = {}
        for key_id, response in zip(refined_top_ids, verifier_responses, strict=True):
            parsed = _compatibility(response)
            verifier_scores[key_id] = parsed if parsed is not None else (False, -1.0)
        compatible = [
            key_id for key_id in refined_top_ids if verifier_scores[key_id][0]
        ]
        pool = compatible or list(refined_top_ids)
        best_score = max(verifier_scores[key_id][1] for key_id in pool)
        tied = [key_id for key_id in pool if verifier_scores[key_id][1] == best_score]
        refined_key_id: str | None
        if len(tied) == 1:
            refined_key_id = tied[0]
        else:
            tied_cards = tuple(by_key[key_id] for key_id in tied)
            tie_response = contact(
                "grounded-tie-arbitration",
                "Resolve the verifier tie by comparing the speech signal directly against "
                "only these tied opaque keys. The grounded state is advisory. Return one "
                "JSON object with exactly one field named key_id whose value is copied "
                "verbatim from a supplied key heading.",
                tied_cards,
                "Validated grounded query state:\n"
                + state_json
                + "\n\nTied keys:\n"
                + render_speech_native_keys(tied_cards, key_representation_id),
            )
            refined_key_id = _selected_key_id(tie_response, set(tied))
        winner = refined_key_id or primary.key_id
        return finish(
            winner,
            top_ids=refined_top_ids,
            scores=verifier_scores,
            agent_policy_id=policy_id,
            agent_actions=(
                "match:speech-only-primary",
                "retrieve:speech-only",
                "build:grounded-query-state",
                "retrieve:speech-plus-grounded-state",
                "verify:speech-plus-grounded-state",
                "select:refined-primary-fallback",
            ),
            agent_escalated=True,
            agent_vote_key_ids=(primary.key_id, refined_key_id),
            agent_steps=(
                agent_step("match:speech-only-primary", primary),
                {
                    "action_id": "retrieve:speech-only",
                    "key_id": initial_top_ids[0],
                    "top_key_ids": list(initial_top_ids),
                    "calls": 1,
                    "parse_failure": False,
                },
                {
                    "action_id": "build:grounded-query-state",
                    "key_id": None,
                    "top_key_ids": list(initial_top_ids),
                    "calls": 1,
                    "parse_failure": False,
                    "grounded_query_state": state.as_json(),
                },
                {
                    "action_id": "retrieve-and-verify:speech-plus-grounded-state",
                    "key_id": refined_key_id,
                    "top_key_ids": list(refined_top_ids),
                    "calls": 1 + len(verifier_responses),
                    "parse_failure": refined_key_id is None,
                    "verifier_scores": {
                        key_id: {
                            "compatible": score[0],
                            "confidence": score[1],
                        }
                        for key_id, score in verifier_scores.items()
                    },
                },
            ),
            decision_agent_aggregator_id=aggregator_id,
        )

    retrieval_instruction = (
        f"Retrieve exactly {top_k} distinct opaque keys for the spoken command, ranked "
        "from most to least compatible. Return a single-line JSON object with exactly "
        f"one field named key_ids whose value is an array of exactly {top_k} ids copied "
        "verbatim from supplied key headings. Do not use Markdown or code fences and do "
        "not add any other text."
        if prompt_policy_id == "speech-native-json-copy-v3"
        else (
            f"Retrieve the {top_k} most compatible opaque keys for the spoken command, "
            f"best first. Return one JSON object with exactly one field named key_ids "
            f"whose value is an array of at most {top_k} ids copied verbatim from supplied "
            "key headings."
        )
    )
    retrieval = contact(
        f"retrieve-top-{top_k}",
        retrieval_instruction,
        cards,
        render_speech_native_keys(cards, key_representation_id),
    )
    top_ids = _selected_top_keys(retrieval, allowed, top_k)
    if not top_ids:
        return finish(None)
    if prompt_policy_id == "speech-native-json-copy-v3" and len(top_ids) != top_k:
        return finish(None, top_ids=top_ids)
    verifier_scores: dict[str, tuple[bool, float]] = {}
    verifier_specifications = []
    for key_id in top_ids:
        card = by_key[key_id]
        verifier_instruction = (
            "Judge whether the spoken command matches both the domain and requested "
            "operation of this one candidate key. Reject a merely related topic when "
            "the requested operation differs. Respond only as "
            '{"compatible":true,"confidence":0}, with confidence from 0 to 100.'
            if verifier_policy_id == "speech-native-contrastive-verifier-v2"
            else (
                "Judge whether the spoken command is compatible with this one candidate "
                'key. Respond only as {"compatible":true,"confidence":0}, with confidence '
                "from 0 to 100."
            )
        )
        verifier_specifications.append(
            (
                f"verify-{key_id}",
                verifier_instruction,
                (card,),
                render_speech_native_keys((card,), key_representation_id),
            )
        )
    verifier_responses = contact_many(verifier_specifications)
    for key_id, response in zip(top_ids, verifier_responses, strict=True):
        parsed = _compatibility(response)
        verifier_scores[key_id] = parsed if parsed is not None else (False, -1.0)
    compatible = [key_id for key_id in top_ids if verifier_scores[key_id][0]]
    pool = compatible or list(top_ids)
    best_score = max(verifier_scores[key_id][1] for key_id in pool)
    tied = [key_id for key_id in pool if verifier_scores[key_id][1] == best_score]
    if len(tied) == 1:
        return finish(tied[0], top_ids=top_ids, scores=verifier_scores)
    tied_cards = tuple(by_key[key_id] for key_id in tied)
    response = contact(
        "tie-arbitration",
        "Resolve the verifier tie by comparing the speech signal directly against only these "
        "tied opaque keys. Return one JSON object with exactly one field named key_id whose "
        "value is copied verbatim from a supplied key heading.",
        tied_cards,
        render_speech_native_keys(tied_cards, key_representation_id),
    )
    key_id = _selected_key_id(response, set(tied))
    return finish(key_id, top_ids=top_ids, scores=verifier_scores)


def run_speech_native_match_tasks(
    *,
    core_client,
    tasks: Sequence[SpeechNativeMatchTask],
    slot_count: int,
    queue_depth: int,
    dispatch_granularity: str = "task",
    trace_run_id: str | None = None,
    trace_flusher: Callable[[TraceBuffer], None] | None = None,
) -> tuple[SpeechNativeMatchOutcome, ...]:
    """Run matcher tasks with bounded rolling concurrency.

    ``dispatch_granularity='task'`` preserves historical whole-decision slot
    affinity. ``'contact'`` queues every matcher contact independently. The
    full-branch M5 path is a bounded dependency DAG: retrieval completion makes
    verifier contacts ready without blocking a branch worker. Results and trace
    buffers are recovered in registered task, branch, and stage order. No failed
    contact or task is retried.
    """

    if (
        isinstance(slot_count, bool)
        or not isinstance(slot_count, int)
        or slot_count <= 0
    ):
        raise PsluFlightError("slot_count must be a positive integer")
    if isinstance(queue_depth, bool) or not isinstance(queue_depth, int):
        raise PsluFlightError("queue_depth must be an integer")
    if queue_depth < slot_count:
        raise PsluFlightError("queue_depth must be at least slot_count")
    if dispatch_granularity not in {"task", "contact"}:
        raise PsluFlightError("dispatch_granularity must be 'task' or 'contact'")
    if (trace_run_id is None) != (trace_flusher is None):
        raise PsluFlightError(
            "trace_run_id and trace_flusher must be supplied together or both omitted"
        )
    ordered_tasks = tuple(tasks)
    task_ids = [task.task_id for task in ordered_tasks]
    if any(not isinstance(task_id, str) or not task_id for task_id in task_ids):
        raise PsluFlightError("speech-native task_id values must be non-empty strings")
    if len(set(task_ids)) != len(task_ids):
        raise PsluFlightError("speech-native task_id values must be unique")
    if not ordered_tasks:
        return ()

    slots: Queue[int] = Queue(maxsize=slot_count)
    for slot_id in range(slot_count):
        slots.put(slot_id)

    contact_pool = (
        ThreadPoolExecutor(
            max_workers=slot_count,
            thread_name_prefix="saea-speech-native-contact",
        )
        if dispatch_granularity == "contact"
        else None
    )
    contact_backlog = BoundedSemaphore(queue_depth)

    class ContactDispatchClient:
        supports_parallel_branches = True

        def _submit(self, messages, kwargs, trace_buffer=None):
            assert contact_pool is not None

            def invoke():
                if trace_buffer is not None:
                    set_current_trace_buffer(trace_buffer)
                slot_id = slots.get()
                try:
                    decoding_params = dict(kwargs.get("decoding_params") or {})
                    requested_slot = decoding_params.get("id_slot")
                    if requested_slot not in (None, "per-sample", "per-task"):
                        raise PsluFlightError(
                            "contact-dispatched decoding_params.id_slot must be absent, "
                            "'per-sample', or 'per-task'"
                        )
                    decoding_params["id_slot"] = slot_id
                    return core_client.complete(
                        messages, **{**kwargs, "decoding_params": decoding_params}
                    )
                finally:
                    slots.put(slot_id)
                    if trace_buffer is not None:
                        set_current_trace_buffer(None)

            context = contextvars.copy_context()
            contact_backlog.acquire()
            try:
                future = contact_pool.submit(context.run, invoke)
            except BaseException:
                contact_backlog.release()
                raise
            future.add_done_callback(lambda _future: contact_backlog.release())
            return future

        def complete(self, messages, **kwargs):
            return self._submit(messages, kwargs).result()

        def complete_many(self, requests, *, trace_parent=None):
            child_buffers = (
                tuple(TraceBuffer(trace_parent.run_id) for _ in requests)
                if trace_parent is not None
                else (None,) * len(requests)
            )
            futures = tuple(
                self._submit(messages, kwargs, child_buffer)
                for (messages, kwargs), child_buffer in zip(
                    requests, child_buffers, strict=True
                )
            )
            responses = tuple(future.result() for future in futures)
            if trace_parent is not None:
                for child_buffer in child_buffers:
                    assert child_buffer is not None
                    trace_parent.extend_from(child_buffer)
            return responses

    contact_client = ContactDispatchClient()

    m11_global = dispatch_granularity == "contact" and all(
        task.matcher_policy_id == "M11" for task in ordered_tasks
    )
    if m11_global:

        @dataclass
        class M11TaskState:
            task_index: int
            cards: tuple[KeyCardV1, ...]
            graph: DecisionGraphV1
            responses: dict[int, str] = field(default_factory=dict)
            trace_buffers: dict[int, TraceBuffer] = field(default_factory=dict)
            primary_key_id: str | None = None
            top_ids: tuple[str, ...] = ()
            action_state: CandidateActionStateV1 | None = None
            challenger_key_id: str | None = None
            boundary: DecisionBoundaryV1 | None = None
            boundary_votes: dict[str, str | None] = field(default_factory=dict)
            decision: SpeechNativeDecision | None = None
            error: BaseException | None = None

        @dataclass(frozen=True)
        class M11Contact:
            task_index: int
            stage_index: int
            stage_kind: str
            order_id: str | None
            messages: tuple[Mapping[str, object], ...]
            kwargs: Mapping[str, object]
            trace_buffer: TraceBuffer | None

            @property
            def sort_key(self) -> tuple[int, int]:
                return self.task_index, self.stage_index

        states_list: list[M11TaskState] = []
        for task_index, task in enumerate(ordered_tasks):
            cards = _validated_key_cards(task.key_cards)
            if task.key_representation_id != "K1":
                raise PsluFlightError("M11 requires maintainable K1 text keys")
            if task.prompt_policy_id != "speech-native-json-copy-v4":
                raise PsluFlightError(
                    "M11 requires the schema-constrained JSON-copy v4 prompt policy"
                )
            if (
                task.agent_policy_id
                not in {
                    "speech-conditioned-adaptive-evidence-gap-v1",
                    "speech-conditioned-adaptive-evidence-gap-v2",
                }
                or task.agent_aggregator_id
                != "adaptive-evidence-gap-primary-control-v1"
            ):
                raise PsluFlightError(
                    "M11 requires the adaptive evidence-gap policy and primary control"
                )
            if task.decision_graph is None:
                raise PsluFlightError("M11 requires one data-derived DecisionGraphV1")
            task.decision_graph.validate(cards)
            if task.top_k <= 0 or task.top_k > len(cards):
                raise PsluFlightError(
                    f"top_k must be in [1, {len(cards)}], got {task.top_k}"
                )
            states_list.append(
                M11TaskState(
                    task_index=task_index,
                    cards=cards,
                    graph=task.decision_graph,
                )
            )
        states = tuple(states_list)

        def m11_contact_node(
            state: M11TaskState,
            *,
            stage_index: int,
            stage_kind: str,
            stage: str,
            system_text: str,
            stage_cards: Sequence[KeyCardV1],
            key_text: str,
            response_format: Mapping[str, object],
            order_id: str | None = None,
        ) -> M11Contact:
            task = ordered_tasks[state.task_index]
            messages = _speech_feature_messages(
                system_text=system_text,
                query_descriptor=task.query_descriptor,
                key_text=key_text,
                key_cards=stage_cards,
                key_representation_id="K1",
                audio_key_bindings=None,
                request_layout_id=task.request_layout_id,
                stable_knowledge_text=_stable_knowledge_text_for_layout(
                    request_layout_id=task.request_layout_id,
                    key_cards=state.cards,
                    key_representation_id="K1",
                ),
            )
            trace_buffer = (
                TraceBuffer(trace_run_id) if trace_run_id is not None else None
            )
            if trace_buffer is not None:
                state.trace_buffers[stage_index] = trace_buffer
            decoding_params = dict(task.decoding_params)
            decoding_params["response_format"] = response_format
            return M11Contact(
                task_index=state.task_index,
                stage_index=stage_index,
                stage_kind=stage_kind,
                order_id=order_id,
                messages=messages,
                kwargs={
                    "decoding_params": decoding_params,
                    "speech_feature_sample_id": task.sample.sample_id,
                    "key_representation_id": "K1",
                    "matcher_policy_id": f"M11:{stage}",
                },
                trace_buffer=trace_buffer,
            )

        def m11_initial_nodes(
            state: M11TaskState,
        ) -> tuple[M11Contact, M11Contact]:
            task = ordered_tasks[state.task_index]
            key_ids = tuple(card.key_id for card in state.cards)
            rendered = render_speech_native_keys(state.cards, "K1")
            return (
                m11_contact_node(
                    state,
                    stage_index=0,
                    stage_kind="primary",
                    stage="primary-listwise",
                    system_text=(
                        "Match the spoken command to exactly one opaque key. Use the "
                        "original speech signal and all action-complete K1 text cards "
                        "jointly. Return only key_id."
                    ),
                    stage_cards=state.cards,
                    key_text=rendered,
                    response_format=_key_choice_response_format(
                        name="speech_native_adaptive_primary_key_choice",
                        key_ids=key_ids,
                    ),
                ),
                m11_contact_node(
                    state,
                    stage_index=1,
                    stage_kind="retrieval",
                    stage=f"speech-retrieve-top-{task.top_k}",
                    system_text=(
                        f"Retrieve exactly {task.top_k} distinct opaque keys for the "
                        "spoken command, ranked from most to least compatible. Use the "
                        "original speech signal and all action-complete K1 cards jointly."
                    ),
                    stage_cards=state.cards,
                    key_text=rendered,
                    response_format=_top_key_choice_response_format(
                        key_ids=key_ids,
                        top_k=task.top_k,
                    ),
                ),
            )

        def m11_initial_steps(
            state: M11TaskState,
        ) -> tuple[Mapping[str, object], ...]:
            task = ordered_tasks[state.task_index]
            return (
                {
                    "action_id": "match:speech-only-primary",
                    "key_id": state.primary_key_id,
                    "top_key_ids": [],
                    "calls": 1,
                    "parse_failure": state.primary_key_id is None,
                    "new_knowledge_ids": [],
                },
                {
                    "action_id": "retrieve:speech-only",
                    "key_id": state.top_ids[0] if state.top_ids else None,
                    "top_key_ids": list(state.top_ids),
                    "calls": 1,
                    "parse_failure": len(state.top_ids) != task.top_k,
                    "new_knowledge_ids": [],
                },
            )

        def m11_action_step(state: M11TaskState) -> Mapping[str, object]:
            return {
                "action_id": "link:candidate-action-state",
                "key_id": (
                    state.action_state.key_id
                    if state.action_state is not None
                    else None
                ),
                "top_key_ids": list(state.top_ids),
                "factor_ids": (
                    list(state.action_state.factor_ids)
                    if state.action_state is not None
                    else []
                ),
                "calls": 1,
                "parse_failure": state.action_state is None,
                "new_knowledge_ids": (
                    list(state.action_state.factor_ids)
                    if state.action_state is not None
                    else []
                ),
                "causal_parent_ids": ["retrieve:speech-only"],
            }

        def finish_m11(
            state: M11TaskState,
            *,
            actions: tuple[str, ...],
            votes: tuple[str | None, ...],
            steps: tuple[Mapping[str, object], ...],
            escalated: bool,
        ) -> None:
            task = ordered_tasks[state.task_index]
            labels = {card.key_id: card.value_label for card in state.cards}
            state.decision = SpeechNativeDecision(
                matcher_policy_id="M11",
                key_representation_id="K1",
                key_id=state.primary_key_id,
                value_label=labels.get(state.primary_key_id),
                top_key_ids=state.top_ids,
                calls=len(state.responses),
                raw_responses=tuple(
                    state.responses[index] for index in sorted(state.responses)
                ),
                verifier_scores={},
                parse_failure=state.primary_key_id is None,
                agent_policy_id=task.agent_policy_id,
                agent_actions=actions,
                agent_escalated=escalated,
                agent_vote_key_ids=votes,
                agent_steps=steps,
                agent_aggregator_id=task.agent_aggregator_id,
            )

        def m11_action_node(state: M11TaskState) -> M11Contact:
            task = ordered_tasks[state.task_index]
            by_key = {card.key_id: card for card in state.cards}
            candidate_cards = tuple(by_key[key_id] for key_id in state.top_ids)
            return m11_contact_node(
                state,
                stage_index=2,
                stage_kind="action",
                stage="candidate-action-state",
                system_text=(
                    "Re-observe the original speech while using only the retrieved "
                    "candidate cards and their registered task factors. Select the best "
                    "candidate and one to three factor ids supported by the speech. "
                    + (
                        "The first factor id must be an operation factor registered to "
                        "the selected key. "
                        if task.agent_policy_id
                        == "speech-conditioned-adaptive-evidence-gap-v2"
                        else ""
                    )
                    + "Return no rationale, summary, or free-form text."
                ),
                stage_cards=candidate_cards,
                key_text=(
                    render_speech_native_keys(candidate_cards, "K1")
                    + "\n\n"
                    + _render_candidate_action_context(
                        graph=state.graph,
                        candidate_key_ids=state.top_ids,
                    )
                ),
                response_format=candidate_action_state_response_format(
                    graph=state.graph,
                    candidate_key_ids=state.top_ids,
                    key_conditioned=(
                        task.agent_policy_id
                        == "speech-conditioned-adaptive-evidence-gap-v2"
                    ),
                ),
            )

        def m11_boundary_nodes(
            state: M11TaskState,
        ) -> tuple[M11Contact, M11Contact]:
            assert state.primary_key_id is not None
            assert state.challenger_key_id is not None
            assert state.boundary is not None
            assert state.action_state is not None
            by_key = {card.key_id: card for card in state.cards}
            pair_ids = (state.primary_key_id, state.challenger_key_id)
            pair_cards = tuple(by_key[key_id] for key_id in pair_ids)
            context = _render_adaptive_boundary_context(
                boundary=state.boundary,
                action_state=state.action_state,
            )
            nodes = []
            for stage_index, (order_id, ordered_cards, heading) in enumerate(
                (
                    ("ab", pair_cards, "Candidate cards:"),
                    (
                        "ba",
                        tuple(reversed(pair_cards)),
                        "Candidate cards in reverse order:",
                    ),
                ),
                start=3,
            ):
                nodes.append(
                    m11_contact_node(
                        state,
                        stage_index=stage_index,
                        stage_kind="boundary",
                        stage=f"boundary-{order_id}",
                        system_text=(
                            "Compare only these two candidates against the original speech "
                            "and the newly retrieved pair boundary. Return only key_id."
                        ),
                        stage_cards=ordered_cards,
                        key_text=(
                            context
                            + f"\n\n{heading}\n"
                            + render_speech_native_keys(ordered_cards, "K1")
                        ),
                        response_format=_key_choice_response_format(
                            name=(
                                "speech_native_adaptive_boundary_ab"
                                if order_id == "ab"
                                else "speech_native_adaptive_boundary_ba"
                            ),
                            key_ids=tuple(card.key_id for card in ordered_cards),
                        ),
                        order_id=order_id,
                    )
                )
            return tuple(nodes)  # type: ignore[return-value]

        def m11_is_runnable(node: M11Contact) -> bool:
            state = states[node.task_index]
            return state.error is None and state.decision is None

        def m11_submit(node: M11Contact) -> Future[str]:
            return contact_client._submit(
                node.messages, dict(node.kwargs), node.trace_buffer
            )

        def m11_error(node: M11Contact, error: BaseException) -> None:
            state = states[node.task_index]
            if state.error is None:
                state.error = error

        def m11_advance(
            node: M11Contact, response: str
        ) -> ContactDAGAdvance[M11Contact]:
            state = states[node.task_index]
            state.responses[node.stage_index] = response
            task = ordered_tasks[state.task_index]
            allowed = {card.key_id for card in state.cards}
            if node.stage_kind in {"primary", "retrieval"}:
                if not {0, 1}.issubset(state.responses):
                    return ContactDAGAdvance()
                state.primary_key_id = _selected_key_id(state.responses[0], allowed)
                state.top_ids = _selected_top_keys(
                    state.responses[1], allowed, task.top_k
                )
                if state.primary_key_id is None or len(state.top_ids) != task.top_k:
                    finish_m11(
                        state,
                        actions=(
                            "match:speech-only-primary",
                            "retrieve:speech-only",
                            "backtrack:invalid-initial-adaptive-state",
                        ),
                        votes=(state.primary_key_id,),
                        steps=m11_initial_steps(state),
                        escalated=True,
                    )
                    return ContactDAGAdvance()
                return ContactDAGAdvance(ready_front=(m11_action_node(state),))
            if node.stage_kind == "action":
                state.action_state = parse_candidate_action_state(
                    response,
                    graph=state.graph,
                    candidate_key_ids=state.top_ids,
                )
                action_step = m11_action_step(state)
                base_actions = (
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "link:candidate-action-state",
                )
                if state.action_state is None:
                    finish_m11(
                        state,
                        actions=(
                            *base_actions,
                            "backtrack:invalid-candidate-action-state",
                        ),
                        votes=(state.primary_key_id, state.top_ids[0]),
                        steps=(*m11_initial_steps(state), action_step),
                        escalated=True,
                    )
                    return ContactDAGAdvance()
                assert state.primary_key_id is not None
                base_votes = (
                    state.primary_key_id,
                    state.top_ids[0],
                    state.action_state.key_id,
                )
                if len(set(base_votes)) == 1:
                    finish_m11(
                        state,
                        actions=(*base_actions, "stop:complete-consistent-state"),
                        votes=base_votes,
                        steps=(*m11_initial_steps(state), action_step),
                        escalated=False,
                    )
                    return ContactDAGAdvance()
                state.challenger_key_id = (
                    state.action_state.key_id
                    if state.action_state.key_id != state.primary_key_id
                    else state.top_ids[0]
                )
                state.boundary = _decision_boundary_for_pair(
                    graph=state.graph,
                    left_key_id=state.primary_key_id,
                    right_key_id=state.challenger_key_id,
                )
                if state.boundary is None:
                    finish_m11(
                        state,
                        actions=(*base_actions, "stop:no-registered-pair-boundary"),
                        votes=base_votes,
                        steps=(*m11_initial_steps(state), action_step),
                        escalated=False,
                    )
                    return ContactDAGAdvance()
                return ContactDAGAdvance(ready_front=m11_boundary_nodes(state))
            if node.stage_kind == "boundary":
                assert node.order_id is not None
                assert state.primary_key_id is not None
                assert state.challenger_key_id is not None
                state.boundary_votes[node.order_id] = _selected_key_id(
                    response,
                    {state.primary_key_id, state.challenger_key_id},
                )
                if set(state.boundary_votes) != {"ab", "ba"}:
                    return ContactDAGAdvance()
                assert state.action_state is not None
                assert state.boundary is not None
                ab_key_id = state.boundary_votes["ab"]
                ba_key_id = state.boundary_votes["ba"]
                comparison_failed = ab_key_id is None or ba_key_id is None
                base_votes = (
                    state.primary_key_id,
                    state.top_ids[0],
                    state.action_state.key_id,
                )
                boundary_step: Mapping[str, object] = {
                    "action_id": (
                        f"retrieve:pair-boundary:{state.boundary.boundary_id}"
                    ),
                    "boundary_id": state.boundary.boundary_id,
                    "primary_key_id": state.primary_key_id,
                    "challenger_key_id": state.challenger_key_id,
                    "information_gap": "candidate-disagreement",
                    "ab_key_id": ab_key_id,
                    "ba_key_id": ba_key_id,
                    "calls": 2,
                    "parse_failure": comparison_failed,
                    "new_knowledge_ids": [state.boundary.boundary_id],
                    "causal_parent_ids": ["link:candidate-action-state"],
                }
                finish_m11(
                    state,
                    actions=(
                        "match:speech-only-primary",
                        "retrieve:speech-only",
                        "link:candidate-action-state",
                        f"retrieve:pair-boundary:{state.boundary.boundary_id}",
                        "compare:boundary-ab",
                        "compare:boundary-ba",
                        (
                            "backtrack:invalid-pair-boundary-comparison"
                            if comparison_failed
                            else "select:retain-primary-for-support"
                        ),
                    ),
                    votes=(*base_votes, ab_key_id, ba_key_id),
                    steps=(
                        *m11_initial_steps(state),
                        m11_action_step(state),
                        boundary_step,
                    ),
                    escalated=True,
                )
                return ContactDAGAdvance()
            raise PsluFlightError(f"unknown M11 DAG stage {node.stage_kind!r}")

        try:
            run_bounded_contact_dag(
                initial_nodes=tuple(
                    node for state in states for node in m11_initial_nodes(state)
                ),
                max_in_flight=slot_count,
                queue_depth=queue_depth,
                node_key=lambda node: (node.task_index, node.stage_index),
                sort_key=lambda node: node.sort_key,
                is_runnable=m11_is_runnable,
                submit=m11_submit,
                on_result=m11_advance,
                on_error=m11_error,
            )
        finally:
            assert contact_pool is not None
            contact_pool.shutdown(wait=True)

        buffered_outcomes: list[_BufferedSpeechNativeOutcome] = []
        for state in states:
            combined = TraceBuffer(trace_run_id) if trace_run_id is not None else None
            if combined is not None:
                for stage_index in sorted(state.trace_buffers):
                    combined.extend_from(state.trace_buffers[stage_index])
            if state.error is None and state.decision is None:
                state.error = PsluFlightError("global M11 DAG did not settle one task")
            buffered_outcomes.append(
                _BufferedSpeechNativeOutcome(
                    outcome=(
                        SpeechNativeMatchOutcome(
                            task_id=ordered_tasks[state.task_index].task_id,
                            slot_id=-1,
                            decision=state.decision,
                        )
                        if state.decision is not None
                        else None
                    ),
                    buffer=combined,
                    error=state.error,
                )
            )
        if trace_flusher is not None:
            for result in buffered_outcomes:
                assert result.buffer is not None
                trace_flusher(result.buffer)
        for result in buffered_outcomes:
            if result.error is not None:
                raise result.error
        return tuple(
            result.outcome for result in buffered_outcomes if result.outcome is not None
        )

    m8_global = dispatch_granularity == "contact" and all(
        task.matcher_policy_id == "M8" for task in ordered_tasks
    )
    if m8_global:

        @dataclass
        class M8TaskState:
            task_index: int
            cards: tuple[KeyCardV1, ...]
            responses: dict[int, str] = field(default_factory=dict)
            trace_buffers: dict[int, TraceBuffer] = field(default_factory=dict)
            primary_key_id: str | None = None
            top_ids: tuple[str, ...] = ()
            challengers: tuple[str, ...] = ()
            pairwise_owners: dict[int, tuple[int, str, str]] = field(
                default_factory=dict
            )
            parsed_votes: dict[tuple[int, str, str], str | None] = field(
                default_factory=dict
            )
            pairwise_scheduled: bool = False
            decision: SpeechNativeDecision | None = None
            error: BaseException | None = None

        @dataclass(frozen=True)
        class M8Contact:
            task_index: int
            stage_index: int
            stage_kind: str
            messages: tuple[Mapping[str, object], ...]
            kwargs: Mapping[str, object]
            trace_buffer: TraceBuffer | None

            @property
            def sort_key(self) -> tuple[int, int]:
                return self.task_index, self.stage_index

        states: tuple[M8TaskState, ...] = tuple(
            M8TaskState(
                task_index=task_index,
                cards=_validated_key_cards(task.key_cards),
            )
            for task_index, task in enumerate(ordered_tasks)
        )
        for state in states:
            task = ordered_tasks[state.task_index]
            if task.key_representation_id != "K1":
                raise PsluFlightError(
                    "M8 requires maintainable K1 text keys at the profile boundary"
                )
            if task.prompt_policy_id != "speech-native-json-copy-v4":
                raise PsluFlightError(
                    "M8 requires the schema-constrained JSON-copy v4 prompt policy"
                )
            if (
                task.agent_policy_id
                != "speech-conditioned-pairwise-boundary-support-v1"
                or task.agent_aggregator_id != "pairwise-boundary-primary-control-v1"
            ):
                raise PsluFlightError(
                    "M8 requires the pairwise-boundary support policy and control"
                )
            if task.top_k <= 0 or task.top_k > len(state.cards):
                raise PsluFlightError(
                    f"top_k must be in [1, {len(state.cards)}], got {task.top_k}"
                )

        def m8_contact_node(
            state: M8TaskState,
            *,
            stage_index: int,
            stage_kind: str,
            stage: str,
            system_text: str,
            stage_cards: Sequence[KeyCardV1],
            key_representation_id: str,
            response_format: Mapping[str, object],
        ) -> M8Contact:
            task = ordered_tasks[state.task_index]
            messages = _speech_feature_messages(
                system_text=system_text,
                query_descriptor=task.query_descriptor,
                key_text=render_speech_native_keys(stage_cards, key_representation_id),
                key_cards=stage_cards,
                key_representation_id=key_representation_id,
                audio_key_bindings=None,
                request_layout_id=task.request_layout_id,
                stable_knowledge_text=_stable_knowledge_text_for_layout(
                    request_layout_id=task.request_layout_id,
                    key_cards=state.cards,
                    key_representation_id=key_representation_id,
                ),
            )
            trace_buffer = (
                TraceBuffer(trace_run_id) if trace_run_id is not None else None
            )
            if trace_buffer is not None:
                state.trace_buffers[stage_index] = trace_buffer
            decoding_params = dict(task.decoding_params)
            decoding_params["response_format"] = response_format
            return M8Contact(
                task_index=state.task_index,
                stage_index=stage_index,
                stage_kind=stage_kind,
                messages=messages,
                kwargs={
                    "decoding_params": decoding_params,
                    "speech_feature_sample_id": task.sample.sample_id,
                    "key_representation_id": key_representation_id,
                    "matcher_policy_id": f"M8:{stage}",
                },
                trace_buffer=trace_buffer,
            )

        def m8_initial_nodes(state: M8TaskState) -> tuple[M8Contact, M8Contact]:
            task = ordered_tasks[state.task_index]
            key_ids = tuple(card.key_id for card in state.cards)
            return (
                m8_contact_node(
                    state,
                    stage_index=0,
                    stage_kind="primary",
                    stage="primary-listwise",
                    system_text=(
                        "Match the spoken command to exactly one opaque key. Use the speech "
                        "signal and the supplied K1 text cards jointly. Return only the "
                        "selected key_id."
                    ),
                    stage_cards=state.cards,
                    key_representation_id="K1",
                    response_format=_key_choice_response_format(
                        name="speech_native_primary_key_choice",
                        key_ids=key_ids,
                    ),
                ),
                m8_contact_node(
                    state,
                    stage_index=1,
                    stage_kind="retrieval",
                    stage=f"speech-retrieve-top-{task.top_k}",
                    system_text=(
                        f"Retrieve exactly {task.top_k} distinct opaque keys for the spoken "
                        "command, ranked from most to least compatible. Use the speech signal "
                        "and supplied K1 text cards jointly. Return only the ordered key_ids."
                    ),
                    stage_cards=state.cards,
                    key_representation_id="K1",
                    response_format=_top_key_choice_response_format(
                        key_ids=key_ids,
                        top_k=task.top_k,
                    ),
                ),
            )

        def m8_pairwise_nodes(state: M8TaskState) -> tuple[M8Contact, ...]:
            assert state.primary_key_id is not None
            by_key = {card.key_id: card for card in state.cards}
            nodes: list[M8Contact] = []
            stage_index = 2
            for rank, challenger_key_id in enumerate(state.challengers, start=1):
                pair_ids = (state.primary_key_id, challenger_key_id)
                response_format = _key_choice_response_format(
                    name="speech_native_pairwise_key_choice",
                    key_ids=pair_ids,
                )
                for representation_id in ("K1", "K2"):
                    for order_id, ordered_ids in (
                        ("ab", pair_ids),
                        ("ba", tuple(reversed(pair_ids))),
                    ):
                        state.pairwise_owners[stage_index] = (
                            rank,
                            representation_id,
                            order_id,
                        )
                        nodes.append(
                            m8_contact_node(
                                state,
                                stage_index=stage_index,
                                stage_kind="pairwise",
                                stage=(
                                    f"pairwise-{representation_id}-rank-{rank}-{order_id}"
                                ),
                                system_text=(
                                    "Choose which of exactly two opaque keys better matches "
                                    "the spoken command. Compare the speech signal directly "
                                    "against both cards. Treat card order as irrelevant and "
                                    "return only key_id."
                                ),
                                stage_cards=tuple(
                                    by_key[key_id] for key_id in ordered_ids
                                ),
                                key_representation_id=representation_id,
                                response_format=response_format,
                            )
                        )
                        stage_index += 1
            return tuple(nodes)

        def finish_m8(state: M8TaskState) -> None:
            task = ordered_tasks[state.task_index]
            labels = {card.key_id: card.value_label for card in state.cards}
            initial_steps: tuple[Mapping[str, object], ...] = (
                {
                    "action_id": "match:speech-only-primary",
                    "key_id": state.primary_key_id,
                    "top_key_ids": [],
                    "calls": 1,
                    "parse_failure": state.primary_key_id is None,
                },
                {
                    "action_id": "retrieve:speech-only",
                    "key_id": state.top_ids[0] if state.top_ids else None,
                    "top_key_ids": list(state.top_ids),
                    "calls": 1,
                    "parse_failure": len(state.top_ids) != task.top_k,
                },
            )
            if state.primary_key_id is None or len(state.top_ids) != task.top_k:
                actions = (
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "backtrack:invalid-initial-pairwise-support",
                )
                votes = (state.primary_key_id,)
                steps = initial_steps
            else:
                comparison_steps: list[Mapping[str, object]] = []
                support_votes: list[str | None] = []
                for rank, challenger_key_id in enumerate(state.challengers, start=1):
                    k1_ab = state.parsed_votes[(rank, "K1", "ab")]
                    k1_ba = state.parsed_votes[(rank, "K1", "ba")]
                    k2_ab = state.parsed_votes[(rank, "K2", "ab")]
                    k2_ba = state.parsed_votes[(rank, "K2", "ba")]
                    k1_stable = (
                        challenger_key_id
                        if k1_ab == k1_ba == challenger_key_id
                        else None
                    )
                    k2_stable = (
                        challenger_key_id
                        if k2_ab == k2_ba == challenger_key_id
                        else None
                    )
                    support_votes.extend((k1_stable, k2_stable))
                    comparison_steps.append(
                        {
                            "action_id": (f"compare:pairwise-boundary-rank-{rank}"),
                            "rank": rank,
                            "primary_key_id": state.primary_key_id,
                            "challenger_key_id": challenger_key_id,
                            "k1_ab_key_id": k1_ab,
                            "k1_ba_key_id": k1_ba,
                            "k1_stable_key_id": k1_stable,
                            "k2_ab_key_id": k2_ab,
                            "k2_ba_key_id": k2_ba,
                            "k2_stable_key_id": k2_stable,
                            "calls": 4,
                            "parse_failure": any(
                                vote is None for vote in (k1_ab, k1_ba, k2_ab, k2_ba)
                            ),
                            "causal_parent_ids": [
                                "match:speech-only-primary",
                                "retrieve:speech-only",
                            ],
                        }
                    )
                actions = (
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    *(
                        f"compare:pairwise-boundary-rank-{rank}"
                        for rank in range(1, len(state.challengers) + 1)
                    ),
                    "select:retain-primary-for-support",
                )
                votes = (state.primary_key_id, *support_votes)
                steps = initial_steps + tuple(comparison_steps)
            state.decision = SpeechNativeDecision(
                matcher_policy_id="M8",
                key_representation_id=task.key_representation_id,
                key_id=state.primary_key_id,
                value_label=labels.get(state.primary_key_id),
                top_key_ids=state.top_ids,
                calls=len(state.responses),
                raw_responses=tuple(
                    state.responses[index] for index in sorted(state.responses)
                ),
                verifier_scores={},
                parse_failure=state.primary_key_id is None,
                agent_policy_id=task.agent_policy_id,
                agent_actions=actions,
                agent_escalated=True,
                agent_vote_key_ids=votes,
                agent_steps=steps,
                agent_aggregator_id=task.agent_aggregator_id,
            )

        ready: deque[M8Contact] = deque(
            node for state in states for node in m8_initial_nodes(state)
        )
        pending: dict[Future, M8Contact] = {}
        try:
            while ready or pending:
                while ready and len(pending) < queue_depth:
                    node = ready.popleft()
                    state = states[node.task_index]
                    if state.error is not None or state.decision is not None:
                        continue
                    future = contact_client._submit(
                        node.messages, dict(node.kwargs), node.trace_buffer
                    )
                    pending[future] = node
                if not pending:
                    if ready:
                        continue
                    break
                done, _not_done = wait(tuple(pending), return_when=FIRST_COMPLETED)
                for future in sorted(done, key=lambda item: pending[item].sort_key):
                    node = pending.pop(future)
                    state = states[node.task_index]
                    try:
                        response = future.result()
                    except BaseException as error:
                        if state.error is None:
                            state.error = error
                        continue
                    if state.error is not None:
                        continue
                    state.responses[node.stage_index] = response
                    task = ordered_tasks[state.task_index]
                    allowed = {card.key_id for card in state.cards}
                    if node.stage_kind in {"primary", "retrieval"}:
                        if not {0, 1}.issubset(state.responses):
                            continue
                        state.primary_key_id = _selected_key_id(
                            state.responses[0], allowed
                        )
                        state.top_ids = _selected_top_keys(
                            state.responses[1], allowed, task.top_k
                        )
                        if (
                            state.primary_key_id is None
                            or len(state.top_ids) != task.top_k
                        ):
                            finish_m8(state)
                            continue
                        state.challengers = tuple(
                            key_id
                            for key_id in state.top_ids
                            if key_id != state.primary_key_id
                        )
                        if not state.pairwise_scheduled:
                            state.pairwise_scheduled = True
                            children = m8_pairwise_nodes(state)
                            if children:
                                ready.extend(children)
                            else:
                                finish_m8(state)
                        continue
                    if node.stage_kind == "pairwise":
                        owner = state.pairwise_owners[node.stage_index]
                        challenger_key_id = state.challengers[owner[0] - 1]
                        state.parsed_votes[owner] = _selected_key_id(
                            response,
                            {state.primary_key_id, challenger_key_id},
                        )
                        if len(state.parsed_votes) == len(state.pairwise_owners):
                            finish_m8(state)
                        continue
                    raise PsluFlightError(f"unknown M8 DAG stage {node.stage_kind!r}")
        finally:
            assert contact_pool is not None
            contact_pool.shutdown(wait=True)

        buffered_outcomes: list[_BufferedSpeechNativeOutcome] = []
        for state in states:
            combined = TraceBuffer(trace_run_id) if trace_run_id is not None else None
            if combined is not None:
                for stage_index in sorted(state.trace_buffers):
                    combined.extend_from(state.trace_buffers[stage_index])
            if state.error is None and state.decision is None:
                state.error = PsluFlightError("global M8 DAG did not settle one task")
            buffered_outcomes.append(
                _BufferedSpeechNativeOutcome(
                    outcome=(
                        SpeechNativeMatchOutcome(
                            task_id=ordered_tasks[state.task_index].task_id,
                            slot_id=-1,
                            decision=state.decision,
                        )
                        if state.decision is not None
                        else None
                    ),
                    buffer=combined,
                    error=state.error,
                )
            )
        if trace_flusher is not None:
            for result in buffered_outcomes:
                assert result.buffer is not None
                trace_flusher(result.buffer)
        for result in buffered_outcomes:
            if result.error is not None:
                raise result.error
        return tuple(
            result.outcome for result in buffered_outcomes if result.outcome is not None
        )

    m9_global = dispatch_granularity == "contact" and all(
        task.matcher_policy_id == "M9" for task in ordered_tasks
    )
    if m9_global:

        @dataclass
        class M9TaskState:
            task_index: int
            cards: tuple[KeyCardV1, ...]
            graph: DecisionGraphV1
            responses: dict[int, str] = field(default_factory=dict)
            trace_buffers: dict[int, TraceBuffer] = field(default_factory=dict)
            primary_key_id: str | None = None
            top_ids: tuple[str, ...] = ()
            factor_state: FactorLinkStateV1 | None = None
            expansion: DecisionGraphExpansionV1 | None = None
            reranked_ids: tuple[str, ...] = ()
            boundary_path: tuple[str, ...] = ()
            boundary_votes: dict[str, str | None] = field(default_factory=dict)
            child_scheduled: bool = False
            decision: SpeechNativeDecision | None = None
            error: BaseException | None = None

        @dataclass(frozen=True)
        class M9Contact:
            task_index: int
            stage_index: int
            stage_kind: str
            order_id: str | None
            messages: tuple[Mapping[str, object], ...]
            kwargs: Mapping[str, object]
            trace_buffer: TraceBuffer | None

            @property
            def sort_key(self) -> tuple[int, int]:
                return self.task_index, self.stage_index

        states_list: list[M9TaskState] = []
        for task_index, task in enumerate(ordered_tasks):
            cards = _validated_key_cards(task.key_cards)
            if task.key_representation_id != "K1":
                raise PsluFlightError("M9 requires maintainable K1 text keys")
            if task.prompt_policy_id != "speech-native-json-copy-v4":
                raise PsluFlightError(
                    "M9 requires the schema-constrained JSON-copy v4 prompt policy"
                )
            if (
                task.agent_policy_id
                != "speech-conditioned-factor-graph-action-support-v1"
                or task.agent_aggregator_id != "factor-graph-primary-control-v1"
            ):
                raise PsluFlightError(
                    "M9 requires the factor-graph support policy and control"
                )
            if task.decision_graph is None:
                raise PsluFlightError("M9 requires one DecisionGraphV1")
            task.decision_graph.validate(cards)
            if task.top_k <= 0 or task.top_k > len(cards):
                raise PsluFlightError(
                    f"top_k must be in [1, {len(cards)}], got {task.top_k}"
                )
            states_list.append(
                M9TaskState(
                    task_index=task_index,
                    cards=cards,
                    graph=task.decision_graph,
                )
            )
        states = tuple(states_list)

        def m9_contact_node(
            state: M9TaskState,
            *,
            stage_index: int,
            stage_kind: str,
            stage: str,
            system_text: str,
            stage_cards: Sequence[KeyCardV1],
            key_text: str,
            response_format: Mapping[str, object],
            order_id: str | None = None,
        ) -> M9Contact:
            task = ordered_tasks[state.task_index]
            messages = _speech_feature_messages(
                system_text=system_text,
                query_descriptor=task.query_descriptor,
                key_text=key_text,
                key_cards=stage_cards,
                key_representation_id="K1",
                audio_key_bindings=None,
                request_layout_id=task.request_layout_id,
                stable_knowledge_text=_stable_knowledge_text_for_layout(
                    request_layout_id=task.request_layout_id,
                    key_cards=state.cards,
                    key_representation_id="K1",
                ),
            )
            trace_buffer = (
                TraceBuffer(trace_run_id) if trace_run_id is not None else None
            )
            if trace_buffer is not None:
                state.trace_buffers[stage_index] = trace_buffer
            decoding_params = dict(task.decoding_params)
            decoding_params["response_format"] = response_format
            return M9Contact(
                task_index=state.task_index,
                stage_index=stage_index,
                stage_kind=stage_kind,
                order_id=order_id,
                messages=messages,
                kwargs={
                    "decoding_params": decoding_params,
                    "speech_feature_sample_id": task.sample.sample_id,
                    "key_representation_id": "K1",
                    "matcher_policy_id": f"M9:{stage}",
                },
                trace_buffer=trace_buffer,
            )

        def m9_initial_nodes(state: M9TaskState) -> tuple[M9Contact, M9Contact]:
            task = ordered_tasks[state.task_index]
            key_ids = tuple(card.key_id for card in state.cards)
            rendered = render_speech_native_keys(state.cards, "K1")
            return (
                m9_contact_node(
                    state,
                    stage_index=0,
                    stage_kind="primary",
                    stage="primary-listwise",
                    system_text=(
                        "Match the spoken command to exactly one opaque key. Use the speech "
                        "signal and the supplied K1 text cards jointly. Return only the "
                        "selected key_id."
                    ),
                    stage_cards=state.cards,
                    key_text=rendered,
                    response_format=_key_choice_response_format(
                        name="speech_native_primary_key_choice",
                        key_ids=key_ids,
                    ),
                ),
                m9_contact_node(
                    state,
                    stage_index=1,
                    stage_kind="retrieval",
                    stage=f"speech-retrieve-top-{task.top_k}",
                    system_text=(
                        f"Retrieve exactly {task.top_k} distinct opaque keys for the spoken "
                        "command, ranked from most to least compatible. Use the speech signal "
                        "and supplied K1 text cards jointly. Return only the ordered key_ids."
                    ),
                    stage_cards=state.cards,
                    key_text=rendered,
                    response_format=_top_key_choice_response_format(
                        key_ids=key_ids,
                        top_k=task.top_k,
                    ),
                ),
            )

        def m9_initial_steps(
            state: M9TaskState,
        ) -> tuple[Mapping[str, object], ...]:
            task = ordered_tasks[state.task_index]
            return (
                {
                    "action_id": "match:speech-only-primary",
                    "key_id": state.primary_key_id,
                    "top_key_ids": [],
                    "calls": 1,
                    "parse_failure": state.primary_key_id is None,
                },
                {
                    "action_id": "retrieve:speech-only",
                    "key_id": state.top_ids[0] if state.top_ids else None,
                    "top_key_ids": list(state.top_ids),
                    "calls": 1,
                    "parse_failure": len(state.top_ids) != task.top_k,
                },
            )

        def finish_m9(
            state: M9TaskState,
            *,
            top_ids: tuple[str, ...],
            actions: tuple[str, ...],
            votes: tuple[str | None, ...],
            steps: tuple[Mapping[str, object], ...],
        ) -> None:
            task = ordered_tasks[state.task_index]
            labels = {card.key_id: card.value_label for card in state.cards}
            state.decision = SpeechNativeDecision(
                matcher_policy_id="M9",
                key_representation_id="K1",
                key_id=state.primary_key_id,
                value_label=labels.get(state.primary_key_id),
                top_key_ids=top_ids,
                calls=len(state.responses),
                raw_responses=tuple(
                    state.responses[index] for index in sorted(state.responses)
                ),
                verifier_scores={},
                parse_failure=state.primary_key_id is None,
                agent_policy_id=task.agent_policy_id,
                agent_actions=actions,
                agent_escalated=True,
                agent_vote_key_ids=votes,
                agent_steps=steps,
                agent_aggregator_id=task.agent_aggregator_id,
            )

        def m9_link_node(state: M9TaskState) -> M9Contact:
            initial_cards = tuple(
                card
                for key_id in state.top_ids
                for card in state.cards
                if card.key_id == key_id
            )
            graph_text = render_decision_graph_neighborhood(
                graph=state.graph,
                key_cards=state.cards,
                candidate_key_ids=state.top_ids,
            )
            return m9_contact_node(
                state,
                stage_index=2,
                stage_kind="link",
                stage="link-factors",
                system_text=(
                    "Select two through five existing factor ids that are directly supported "
                    "by the spoken command, plus at most one existing boundary id when it "
                    "captures the unresolved distinction. Return only the registered ids. "
                    "Do not generate a paraphrase, rationale, or free-form semantic field."
                ),
                stage_cards=initial_cards,
                key_text=(
                    "Initial key cards:\n"
                    + render_speech_native_keys(initial_cards, "K1")
                    + "\n\nReachable decision graph:\n"
                    + graph_text
                ),
                response_format=factor_link_response_format(
                    graph=state.graph,
                    key_cards=state.cards,
                    candidate_key_ids=state.top_ids,
                ),
            )

        def m9_rerank_node(state: M9TaskState) -> M9Contact:
            assert state.factor_state is not None
            assert state.expansion is not None
            expanded_cards = tuple(
                card
                for key_id in state.expansion.key_ids
                for card in state.cards
                if card.key_id == key_id
            )
            rerank_top_k = min(3, len(expanded_cards))
            return m9_contact_node(
                state,
                stage_index=3,
                stage_kind="rerank",
                stage=f"factor-rerank-top-{rerank_top_k}",
                system_text=(
                    f"Rank exactly {rerank_top_k} opaque keys for the spoken command. The "
                    "selected knowledge factors are advisory evidence; re-evaluate them "
                    "against the speech signal carried in this request. Return only the "
                    "ordered key_ids."
                ),
                stage_cards=expanded_cards,
                key_text=(
                    render_factor_link_state(
                        graph=state.graph, state=state.factor_state
                    )
                    + "\n\nExpanded key cards:\n"
                    + render_speech_native_keys(expanded_cards, "K1")
                ),
                response_format=_top_key_choice_response_format(
                    key_ids=state.expansion.key_ids,
                    top_k=rerank_top_k,
                ),
            )

        def m9_factor_steps(
            state: M9TaskState,
        ) -> tuple[Mapping[str, object], ...]:
            assert state.factor_state is not None
            assert state.expansion is not None
            return (
                *m9_initial_steps(state),
                {
                    "action_id": "link:knowledge-factors",
                    "key_id": None,
                    "top_key_ids": list(state.top_ids),
                    "calls": 1,
                    "parse_failure": False,
                    "factor_link_state": {
                        "factor_ids": list(state.factor_state.factor_ids),
                        "boundary_id": state.factor_state.boundary_id,
                    },
                },
                {
                    "action_id": "tool:expand-factor-graph",
                    "key_id": None,
                    "top_key_ids": list(state.top_ids),
                    "calls": 0,
                    "parse_failure": False,
                    "expanded_key_ids": list(state.expansion.key_ids),
                    "distance_by_key": dict(state.expansion.distance_by_key),
                },
                {
                    "action_id": "rerank:speech-plus-factor-state",
                    "key_id": state.reranked_ids[0] if state.reranked_ids else None,
                    "top_key_ids": list(state.reranked_ids),
                    "calls": 1,
                    "parse_failure": len(state.reranked_ids)
                    != min(3, len(state.expansion.key_ids)),
                },
            )

        def m9_boundary_nodes(
            state: M9TaskState,
        ) -> tuple[M9Contact, M9Contact]:
            assert state.primary_key_id is not None
            assert state.reranked_ids
            assert state.factor_state is not None
            pair_ids = (state.primary_key_id, state.reranked_ids[0])
            by_key = {card.key_id: card for card in state.cards}
            boundaries_by_id = {
                boundary.boundary_id: boundary for boundary in state.graph.boundaries
            }
            path_lines = ["Boundary path:"]
            for boundary_id in state.boundary_path:
                boundary = boundaries_by_id[boundary_id]
                path_lines.extend(
                    (
                        f"[{boundary.boundary_id}] endpoints="
                        f"{boundary.left_key_id},{boundary.right_key_id}",
                        f"{boundary.left_key_id} factors: "
                        f"{','.join(boundary.left_factor_ids)}",
                        f"{boundary.left_key_id} exclusion: {boundary.left_exclusion}",
                        f"{boundary.right_key_id} factors: "
                        f"{','.join(boundary.right_factor_ids)}",
                        f"{boundary.right_key_id} exclusion: {boundary.right_exclusion}",
                    )
                )
            key_text_prefix = (
                render_factor_link_state(graph=state.graph, state=state.factor_state)
                + "\n\n"
                + "\n".join(path_lines)
                + "\n\nCandidate key cards:\n"
            )
            response_format = _key_choice_response_format(
                name="speech_native_factor_boundary_choice",
                key_ids=pair_ids,
            )
            nodes = []
            for stage_index, (order_id, ordered_ids) in enumerate(
                (("ab", pair_ids), ("ba", tuple(reversed(pair_ids)))), start=4
            ):
                ordered_cards = tuple(by_key[key_id] for key_id in ordered_ids)
                nodes.append(
                    m9_contact_node(
                        state,
                        stage_index=stage_index,
                        stage_kind="boundary",
                        stage=f"boundary-rank-1-{order_id}",
                        system_text=(
                            "Choose which of exactly two opaque keys better matches the "
                            "spoken command. Use the selected factor nodes and registered "
                            "boundary path as advisory evidence, but resolve conflicts from "
                            "the speech signal. Treat card order as irrelevant and return "
                            "only key_id."
                        ),
                        stage_cards=ordered_cards,
                        key_text=(
                            key_text_prefix
                            + render_speech_native_keys(ordered_cards, "K1")
                        ),
                        response_format=response_format,
                        order_id=order_id,
                    )
                )
            return tuple(nodes)  # type: ignore[return-value]

        ready: deque[M9Contact] = deque(
            node for state in states for node in m9_initial_nodes(state)
        )
        pending: dict[Future, M9Contact] = {}
        try:
            while ready or pending:
                while ready and len(pending) < queue_depth:
                    node = ready.popleft()
                    state = states[node.task_index]
                    if state.error is not None or state.decision is not None:
                        continue
                    future = contact_client._submit(
                        node.messages, dict(node.kwargs), node.trace_buffer
                    )
                    pending[future] = node
                if not pending:
                    if ready:
                        continue
                    break
                done, _not_done = wait(tuple(pending), return_when=FIRST_COMPLETED)
                for future in sorted(done, key=lambda item: pending[item].sort_key):
                    node = pending.pop(future)
                    state = states[node.task_index]
                    try:
                        response = future.result()
                    except BaseException as error:
                        if state.error is None:
                            state.error = error
                        continue
                    if state.error is not None or state.decision is not None:
                        continue
                    state.responses[node.stage_index] = response
                    task = ordered_tasks[state.task_index]
                    allowed = {card.key_id for card in state.cards}
                    if node.stage_kind in {"primary", "retrieval"}:
                        if not {0, 1}.issubset(state.responses):
                            continue
                        state.primary_key_id = _selected_key_id(
                            state.responses[0], allowed
                        )
                        state.top_ids = _selected_top_keys(
                            state.responses[1], allowed, task.top_k
                        )
                        if (
                            state.primary_key_id is None
                            or len(state.top_ids) != task.top_k
                        ):
                            finish_m9(
                                state,
                                top_ids=state.top_ids,
                                actions=(
                                    "match:speech-only-primary",
                                    "retrieve:speech-only",
                                    "backtrack:invalid-initial-factor-support",
                                ),
                                votes=(state.primary_key_id,),
                                steps=m9_initial_steps(state),
                            )
                        elif not state.child_scheduled:
                            state.child_scheduled = True
                            ready.append(m9_link_node(state))
                        continue
                    if node.stage_kind == "link":
                        state.factor_state = parse_factor_link_state(
                            response,
                            graph=state.graph,
                            key_cards=state.cards,
                            candidate_key_ids=state.top_ids,
                        )
                        if state.factor_state is None:
                            finish_m9(
                                state,
                                top_ids=state.top_ids,
                                actions=(
                                    "match:speech-only-primary",
                                    "retrieve:speech-only",
                                    "link:knowledge-factors",
                                    "backtrack:invalid-factor-link-state",
                                ),
                                votes=(state.primary_key_id,),
                                steps=(
                                    *m9_initial_steps(state),
                                    {
                                        "action_id": "link:knowledge-factors",
                                        "key_id": None,
                                        "top_key_ids": list(state.top_ids),
                                        "calls": 1,
                                        "parse_failure": True,
                                    },
                                ),
                            )
                            continue
                        state.expansion = expand_decision_graph_candidates(
                            graph=state.graph,
                            initial_key_ids=state.top_ids,
                            state=state.factor_state,
                            cap=min(6, len(state.cards)),
                        )
                        ready.append(m9_rerank_node(state))
                        continue
                    if node.stage_kind == "rerank":
                        assert state.expansion is not None
                        rerank_top_k = min(3, len(state.expansion.key_ids))
                        state.reranked_ids = _selected_top_keys(
                            response, set(state.expansion.key_ids), rerank_top_k
                        )
                        common_actions = (
                            "match:speech-only-primary",
                            "retrieve:speech-only",
                            "link:knowledge-factors",
                            "tool:expand-factor-graph",
                            "rerank:speech-plus-factor-state",
                        )
                        steps = m9_factor_steps(state)
                        if len(state.reranked_ids) != rerank_top_k:
                            finish_m9(
                                state,
                                top_ids=state.reranked_ids,
                                actions=(
                                    *common_actions,
                                    "backtrack:invalid-factor-rerank",
                                ),
                                votes=(state.primary_key_id,),
                                steps=steps,
                            )
                            continue
                        rerank_key_id = state.reranked_ids[0]
                        if rerank_key_id == state.primary_key_id:
                            finish_m9(
                                state,
                                top_ids=state.reranked_ids,
                                actions=(
                                    *common_actions,
                                    "stop:primary-rerank-agree",
                                    "select:retain-primary-for-support",
                                ),
                                votes=(state.primary_key_id, rerank_key_id),
                                steps=steps,
                            )
                            continue
                        assert state.primary_key_id is not None
                        state.boundary_path = decision_boundary_path(
                            graph=state.graph,
                            source_key_id=state.primary_key_id,
                            target_key_id=rerank_key_id,
                            max_edges=2,
                        )
                        if not state.boundary_path:
                            finish_m9(
                                state,
                                top_ids=state.reranked_ids,
                                actions=(
                                    *common_actions,
                                    "backtrack:no-boundary-path",
                                    "select:retain-primary-for-support",
                                ),
                                votes=(state.primary_key_id, rerank_key_id),
                                steps=steps,
                            )
                            continue
                        ready.extend(m9_boundary_nodes(state))
                        continue
                    if node.stage_kind == "boundary":
                        assert node.order_id is not None
                        assert state.primary_key_id is not None
                        state.boundary_votes[node.order_id] = _selected_key_id(
                            response,
                            {state.primary_key_id, state.reranked_ids[0]},
                        )
                        if set(state.boundary_votes) != {"ab", "ba"}:
                            continue
                        boundary_votes = (
                            state.boundary_votes["ab"],
                            state.boundary_votes["ba"],
                        )
                        finish_m9(
                            state,
                            top_ids=state.reranked_ids,
                            actions=(
                                "match:speech-only-primary",
                                "retrieve:speech-only",
                                "link:knowledge-factors",
                                "tool:expand-factor-graph",
                                "rerank:speech-plus-factor-state",
                                "compare:boundary-ab",
                                "compare:boundary-ba",
                                "select:retain-primary-for-support",
                            ),
                            votes=(
                                state.primary_key_id,
                                state.reranked_ids[0],
                                *boundary_votes,
                            ),
                            steps=(
                                *m9_factor_steps(state),
                                {
                                    "action_id": "compare:factor-boundary",
                                    "key_id": None,
                                    "top_key_ids": [
                                        state.primary_key_id,
                                        state.reranked_ids[0],
                                    ],
                                    "calls": 2,
                                    "parse_failure": any(
                                        vote is None for vote in boundary_votes
                                    ),
                                    "boundary_path_ids": list(state.boundary_path),
                                    "ab_key_id": boundary_votes[0],
                                    "ba_key_id": boundary_votes[1],
                                    "causal_parent_ids": [
                                        "link:knowledge-factors",
                                        "tool:expand-factor-graph",
                                        "rerank:speech-plus-factor-state",
                                    ],
                                },
                            ),
                        )
                        continue
                    raise PsluFlightError(f"unknown M9 DAG stage {node.stage_kind!r}")
        finally:
            assert contact_pool is not None
            contact_pool.shutdown(wait=True)

        buffered_outcomes: list[_BufferedSpeechNativeOutcome] = []
        for state in states:
            combined = TraceBuffer(trace_run_id) if trace_run_id is not None else None
            if combined is not None:
                for stage_index in sorted(state.trace_buffers):
                    combined.extend_from(state.trace_buffers[stage_index])
            if state.error is None and state.decision is None:
                state.error = PsluFlightError("global M9 DAG did not settle one task")
            buffered_outcomes.append(
                _BufferedSpeechNativeOutcome(
                    outcome=(
                        SpeechNativeMatchOutcome(
                            task_id=ordered_tasks[state.task_index].task_id,
                            slot_id=-1,
                            decision=state.decision,
                        )
                        if state.decision is not None
                        else None
                    ),
                    buffer=combined,
                    error=state.error,
                )
            )
        if trace_flusher is not None:
            for result in buffered_outcomes:
                assert result.buffer is not None
                trace_flusher(result.buffer)
        for result in buffered_outcomes:
            if result.error is not None:
                raise result.error
        return tuple(
            result.outcome for result in buffered_outcomes if result.outcome is not None
        )

    full_branch_global = dispatch_granularity == "contact" and all(
        task.matcher_policy_id == "M5"
        and task.agent_policy_id == "m1-m3-full-branch-explorer-v1"
        for task in ordered_tasks
    )
    if full_branch_global:
        branch_kinds = (
            ("M1", "canonical", "M5:M1:canonical"),
            ("M3", "canonical", "M5:M3:canonical"),
            ("M3", "reverse", "M5:M3:reverse"),
            ("M3", "rotate-7", "M5:M3:rotate-7"),
        )
        branch_specs = tuple(
            (task_index, branch_index, policy_id, order_id, trace_policy_id)
            for task_index in range(len(ordered_tasks))
            for branch_index, (policy_id, order_id, trace_policy_id) in enumerate(
                branch_kinds
            )
        )

        def branch_cards(
            task: SpeechNativeMatchTask, order_id: str
        ) -> tuple[KeyCardV1, ...]:
            if order_id == "canonical":
                return task.key_cards
            if order_id == "reverse":
                return tuple(reversed(task.key_cards))
            if order_id == "rotate-7":
                return _rotate_key_cards(task.key_cards, 7)
            raise PsluFlightError(f"unknown full-branch order {order_id!r}")

        @dataclass
        class DagBranchState:
            task_index: int
            branch_index: int
            policy_id: str
            order_id: str
            trace_policy_id: str
            cards: tuple[KeyCardV1, ...]
            responses: dict[int, str] = field(default_factory=dict)
            trace_buffers: dict[int, TraceBuffer] = field(default_factory=dict)
            top_ids: tuple[str, ...] = ()
            verifier_scores: dict[str, tuple[bool, float]] = field(default_factory=dict)
            tied_ids: tuple[str, ...] = ()
            decision: SpeechNativeDecision | None = None
            error: BaseException | None = None

        @dataclass(frozen=True)
        class DagContact:
            task_index: int
            branch_index: int
            stage_index: int
            stage_kind: str
            key_id: str | None
            messages: tuple[Mapping[str, object], ...]
            kwargs: Mapping[str, object]
            trace_buffer: TraceBuffer | None

            @property
            def sort_key(self) -> tuple[int, int, int]:
                return self.task_index, self.branch_index, self.stage_index

        states = tuple(
            DagBranchState(
                task_index=task_index,
                branch_index=branch_index,
                policy_id=policy_id,
                order_id=order_id,
                trace_policy_id=trace_policy_id,
                cards=branch_cards(ordered_tasks[task_index], order_id),
            )
            for task_index, branch_index, policy_id, order_id, trace_policy_id in branch_specs
        )
        state_by_pair = {
            (state.task_index, state.branch_index): state for state in states
        }

        def contact_node(
            state: DagBranchState,
            *,
            stage_index: int,
            stage_kind: str,
            stage: str,
            system_text: str,
            stage_cards: Sequence[KeyCardV1],
            key_text: str | None,
            key_id: str | None = None,
        ) -> DagContact:
            task = ordered_tasks[state.task_index]
            messages = _speech_feature_messages(
                system_text=system_text,
                query_descriptor=task.query_descriptor,
                key_text=key_text,
                key_cards=stage_cards,
                key_representation_id=task.key_representation_id,
                audio_key_bindings=(
                    {
                        card.key_id: task.audio_key_bindings[card.key_id]
                        for card in stage_cards
                    }
                    if task.audio_key_bindings is not None
                    else None
                ),
                request_layout_id=task.request_layout_id,
                stable_knowledge_text=_stable_knowledge_text_for_layout(
                    request_layout_id=task.request_layout_id,
                    key_cards=state.cards,
                    key_representation_id=task.key_representation_id,
                ),
            )
            trace_buffer = (
                TraceBuffer(trace_run_id) if trace_run_id is not None else None
            )
            if trace_buffer is not None:
                state.trace_buffers[stage_index] = trace_buffer
            return DagContact(
                task_index=state.task_index,
                branch_index=state.branch_index,
                stage_index=stage_index,
                stage_kind=stage_kind,
                key_id=key_id,
                messages=messages,
                kwargs={
                    "decoding_params": dict(task.decoding_params),
                    "speech_feature_sample_id": task.sample.sample_id,
                    "key_representation_id": task.key_representation_id,
                    "matcher_policy_id": f"{state.trace_policy_id}:{stage}",
                },
                trace_buffer=trace_buffer,
            )

        def finish_branch(
            state: DagBranchState,
            key_id: str | None,
            *,
            top_ids: tuple[str, ...] = (),
            scores: Mapping[str, tuple[bool, float]] = MappingProxyType({}),
        ) -> None:
            task = ordered_tasks[state.task_index]
            labels = {card.key_id: card.value_label for card in state.cards}
            state.decision = SpeechNativeDecision(
                matcher_policy_id=state.policy_id,
                key_representation_id=task.key_representation_id,
                key_id=key_id,
                value_label=labels.get(key_id),
                top_key_ids=top_ids,
                calls=len(state.responses),
                raw_responses=tuple(
                    state.responses[index] for index in sorted(state.responses)
                ),
                verifier_scores=dict(scores),
                parse_failure=key_id is None,
                agent_policy_id=task.agent_policy_id,
            )

        def m1_node(state: DagBranchState) -> DagContact:
            task = ordered_tasks[state.task_index]
            label_mode = task.key_representation_id == "K0"
            return contact_node(
                state,
                stage_index=0,
                stage_kind="m1",
                stage="listwise-label" if label_mode else "listwise",
                system_text=(
                    "Match the spoken command to exactly one listed label. Return one JSON "
                    "object with exactly one field named label. Its string value must be "
                    "copied verbatim from the supplied label list."
                    if label_mode
                    else (
                        "Match the spoken command to exactly one opaque key. Use the speech "
                        "signal and the supplied key representations jointly. Return one JSON "
                        "object with exactly one field named key_id. Its string value must be "
                        "copied verbatim from a supplied key heading; do not invent or shorten "
                        "an id."
                    )
                ),
                stage_cards=state.cards,
                key_text=render_speech_native_keys(
                    state.cards, task.key_representation_id
                ),
            )

        def retrieval_node(state: DagBranchState) -> DagContact:
            task = ordered_tasks[state.task_index]
            instruction = (
                f"Retrieve exactly {task.top_k} distinct opaque keys for the spoken command, "
                "ranked from most to least compatible. Return a single-line JSON object with "
                f"exactly one field named key_ids whose value is an array of exactly {task.top_k} "
                "ids copied verbatim from supplied key headings. Do not use Markdown or code "
                "fences and do not add any other text."
                if task.prompt_policy_id == "speech-native-json-copy-v3"
                else (
                    f"Retrieve the {task.top_k} most compatible opaque keys for the spoken "
                    f"command, best first. Return one JSON object with exactly one field named "
                    f"key_ids whose value is an array of at most {task.top_k} ids copied verbatim "
                    "from supplied key headings."
                )
            )
            return contact_node(
                state,
                stage_index=0,
                stage_kind="retrieval",
                stage=f"retrieve-top-{task.top_k}",
                system_text=instruction,
                stage_cards=state.cards,
                key_text=render_speech_native_keys(
                    state.cards, task.key_representation_id
                ),
            )

        def verifier_node(
            state: DagBranchState, key_id: str, stage_index: int
        ) -> DagContact:
            task = ordered_tasks[state.task_index]
            card = next(card for card in state.cards if card.key_id == key_id)
            instruction = (
                "Judge whether the spoken command matches both the domain and requested "
                "operation of this one candidate key. Reject a merely related topic when "
                "the requested operation differs. Respond only as "
                '{"compatible":true,"confidence":0}, with confidence from 0 to 100.'
                if task.verifier_policy_id == "speech-native-contrastive-verifier-v2"
                else (
                    "Judge whether the spoken command is compatible with this one candidate "
                    'key. Respond only as {"compatible":true,"confidence":0}, with confidence '
                    "from 0 to 100."
                )
            )
            return contact_node(
                state,
                stage_index=stage_index,
                stage_kind="verifier",
                stage=f"verify-{key_id}",
                system_text=instruction,
                stage_cards=(card,),
                key_text=render_speech_native_keys((card,), task.key_representation_id),
                key_id=key_id,
            )

        def tie_node(state: DagBranchState) -> DagContact:
            task = ordered_tasks[state.task_index]
            cards = tuple(card for card in state.cards if card.key_id in state.tied_ids)
            return contact_node(
                state,
                stage_index=1 + len(state.top_ids),
                stage_kind="tie",
                stage="tie-arbitration",
                system_text=(
                    "Resolve the verifier tie by comparing the speech signal directly against "
                    "only these tied opaque keys. Return one JSON object with exactly one field "
                    "named key_id whose value is copied verbatim from a supplied key heading."
                ),
                stage_cards=cards,
                key_text=render_speech_native_keys(cards, task.key_representation_id),
            )

        ready: deque[DagContact] = deque(
            m1_node(state) if state.policy_id == "M1" else retrieval_node(state)
            for state in states
        )
        pending: dict[Future, DagContact] = {}
        try:
            while ready or pending:
                while ready and len(pending) < queue_depth:
                    node = ready.popleft()
                    future = contact_client._submit(
                        node.messages, dict(node.kwargs), node.trace_buffer
                    )
                    pending[future] = node
                if not pending:
                    raise PsluFlightError(
                        "full-branch stage DAG has unfinished work but no pending contacts"
                    )
                done, _not_done = wait(tuple(pending), return_when=FIRST_COMPLETED)
                completed = sorted(done, key=lambda item: pending[item].sort_key)
                for future in completed:
                    node = pending.pop(future)
                    state = state_by_pair[(node.task_index, node.branch_index)]
                    try:
                        response = future.result()
                    except BaseException as error:
                        if state.error is None:
                            state.error = error
                        continue
                    state.responses[node.stage_index] = response
                    task = ordered_tasks[state.task_index]
                    allowed = {card.key_id for card in state.cards}
                    if node.stage_kind == "m1":
                        if task.key_representation_id == "K0":
                            document = _response_object(response)
                            label = (
                                document.get("label") if document is not None else None
                            )
                            selected = next(
                                (
                                    card.key_id
                                    for card in state.cards
                                    if card.value_label == label
                                ),
                                None,
                            )
                        else:
                            selected = _selected_key_id(response, allowed)
                        finish_branch(state, selected)
                        continue
                    if node.stage_kind == "retrieval":
                        state.top_ids = _selected_top_keys(
                            response, allowed, task.top_k
                        )
                        if not state.top_ids or (
                            task.prompt_policy_id == "speech-native-json-copy-v3"
                            and len(state.top_ids) != task.top_k
                        ):
                            finish_branch(state, None, top_ids=state.top_ids)
                            continue
                        ready.extend(
                            verifier_node(state, key_id, 1 + index)
                            for index, key_id in enumerate(state.top_ids)
                        )
                        continue
                    if node.stage_kind == "verifier":
                        assert node.key_id is not None
                        parsed = _compatibility(response)
                        state.verifier_scores[node.key_id] = (
                            parsed if parsed is not None else (False, -1.0)
                        )
                        if len(state.verifier_scores) != len(state.top_ids):
                            continue
                        compatible = [
                            key_id
                            for key_id in state.top_ids
                            if state.verifier_scores[key_id][0]
                        ]
                        pool = compatible or list(state.top_ids)
                        best_score = max(
                            state.verifier_scores[key_id][1] for key_id in pool
                        )
                        state.tied_ids = tuple(
                            key_id
                            for key_id in pool
                            if state.verifier_scores[key_id][1] == best_score
                        )
                        if len(state.tied_ids) == 1:
                            finish_branch(
                                state,
                                state.tied_ids[0],
                                top_ids=state.top_ids,
                                scores=state.verifier_scores,
                            )
                        else:
                            ready.append(tie_node(state))
                        continue
                    if node.stage_kind == "tie":
                        selected = _selected_key_id(response, set(state.tied_ids))
                        finish_branch(
                            state,
                            selected,
                            top_ids=state.top_ids,
                            scores=state.verifier_scores,
                        )
                        continue
                    raise PsluFlightError(
                        f"unknown full-branch DAG stage {node.stage_kind!r}"
                    )
        finally:
            assert contact_pool is not None
            contact_pool.shutdown(wait=True)

        branch_results: list[
            tuple[SpeechNativeDecision | None, TraceBuffer | None, BaseException | None]
        ] = []
        for state in states:
            combined = TraceBuffer(trace_run_id) if trace_run_id is not None else None
            if combined is not None:
                for stage_index in sorted(state.trace_buffers):
                    combined.extend_from(state.trace_buffers[stage_index])
            if state.error is None and state.decision is None:
                state.error = PsluFlightError(
                    "full-branch stage DAG did not settle one branch"
                )
            branch_results.append((state.decision, combined, state.error))
        settled_branches = tuple(branch_results)

        buffered_outcomes: list[_BufferedSpeechNativeOutcome] = []
        for task_index, task in enumerate(ordered_tasks):
            start = task_index * len(branch_kinds)
            task_results = settled_branches[start : start + len(branch_kinds)]
            combined_buffer = (
                TraceBuffer(trace_run_id) if trace_run_id is not None else None
            )
            if combined_buffer is not None:
                for _decision, branch_buffer, _error in task_results:
                    assert branch_buffer is not None
                    combined_buffer.extend_from(branch_buffer)
            first_error = next(
                (
                    error
                    for _decision, _buffer, error in task_results
                    if error is not None
                ),
                None,
            )
            decisions = tuple(
                decision
                for decision, _buffer, _error in task_results
                if decision is not None
            )
            if first_error is not None or len(decisions) != len(branch_kinds):
                buffered_outcomes.append(
                    _BufferedSpeechNativeOutcome(
                        outcome=None,
                        buffer=combined_buffer,
                        error=first_error
                        or PsluFlightError("full-branch task lacks a branch decision"),
                    )
                )
                continue
            primary, canonical, reverse, rotate = decisions
            votes = (canonical.key_id, reverse.key_id, rotate.key_id)
            valid_votes = [key_id for key_id in votes if key_id is not None]
            counts = {key_id: valid_votes.count(key_id) for key_id in set(valid_votes)}
            majority = next(
                (key_id for key_id, count in counts.items() if count >= 2),
                None,
            )
            if task.agent_aggregator_id == "m3-unanimous-primary-fallback-v3":
                unanimous = (
                    valid_votes[0]
                    if len(valid_votes) == 3 and len(set(valid_votes)) == 1
                    else None
                )
                winner = unanimous if unanimous is not None else primary.key_id
                aggregate_action = "aggregate:m3-unanimous-primary-fallback"
            else:
                fallback = (
                    primary.key_id
                    if task.agent_aggregator_id == "m3-majority-primary-tie-v2"
                    else canonical.key_id
                )
                winner = majority if majority is not None else fallback
                aggregate_action = (
                    "aggregate:m3-majority-primary-tie"
                    if task.agent_aggregator_id == "m3-majority-primary-tie-v2"
                    else "aggregate:m3-majority-canonical-tie"
                )
            label_by_key = {card.key_id: card.value_label for card in task.key_cards}

            def step(action_id: str, decision: SpeechNativeDecision):
                return {
                    "action_id": action_id,
                    "key_id": decision.key_id,
                    "top_key_ids": list(decision.top_key_ids),
                    "calls": decision.calls,
                    "parse_failure": decision.parse_failure,
                }

            decision = SpeechNativeDecision(
                matcher_policy_id="M5",
                key_representation_id=task.key_representation_id,
                key_id=winner,
                value_label=label_by_key.get(winner),
                top_key_ids=canonical.top_key_ids,
                calls=sum(item.calls for item in decisions),
                raw_responses=tuple(
                    response for item in decisions for response in item.raw_responses
                ),
                verifier_scores=canonical.verifier_scores,
                parse_failure=winner is None,
                agent_policy_id=task.agent_policy_id,
                agent_actions=(
                    "match:listwise-canonical",
                    "retrieve-verify:canonical",
                    "explore:full-branch",
                    "retrieve-verify:reverse",
                    "retrieve-verify:rotate-7",
                    aggregate_action,
                ),
                agent_escalated=(
                    primary.key_id is None or primary.key_id != canonical.key_id
                ),
                agent_vote_key_ids=(
                    primary.key_id,
                    canonical.key_id,
                    reverse.key_id,
                    rotate.key_id,
                ),
                agent_steps=(
                    step("match:listwise-canonical", primary),
                    step("retrieve-verify:canonical", canonical),
                    step("retrieve-verify:reverse", reverse),
                    step("retrieve-verify:rotate-7", rotate),
                ),
                agent_aggregator_id=task.agent_aggregator_id,
            )
            buffered_outcomes.append(
                _BufferedSpeechNativeOutcome(
                    outcome=SpeechNativeMatchOutcome(
                        task_id=task.task_id,
                        slot_id=-1,
                        decision=decision,
                    ),
                    buffer=combined_buffer,
                    error=None,
                )
            )

        if trace_flusher is not None:
            for result in buffered_outcomes:
                assert result.buffer is not None
                trace_flusher(result.buffer)
        for result in buffered_outcomes:
            if result.error is not None:
                raise result.error
        return tuple(
            result.outcome for result in buffered_outcomes if result.outcome is not None
        )

    def one(task: SpeechNativeMatchTask) -> _BufferedSpeechNativeOutcome:
        slot_id = slots.get() if dispatch_granularity == "task" else -1
        buffer = TraceBuffer(trace_run_id) if trace_run_id is not None else None
        if buffer is not None:
            set_current_trace_buffer(buffer)
        try:
            decoding_params = dict(task.decoding_params)
            if dispatch_granularity == "task":
                requested_slot = decoding_params.get("id_slot")
                if requested_slot not in (None, "per-sample", "per-task"):
                    raise PsluFlightError(
                        "parallel speech-native tasks require decoding_params.id_slot to be "
                        "absent, 'per-sample', or 'per-task' before dispatch"
                    )
                decoding_params["id_slot"] = slot_id
            decision = run_speech_native_matcher(
                core_client=(
                    core_client if dispatch_granularity == "task" else contact_client
                ),
                sample=task.sample,
                query_descriptor=task.query_descriptor,
                key_cards=task.key_cards,
                key_representation_id=task.key_representation_id,
                matcher_policy_id=task.matcher_policy_id,
                prompt_policy_id=task.prompt_policy_id,
                request_layout_id=task.request_layout_id,
                verifier_policy_id=task.verifier_policy_id,
                decoding_params=decoding_params,
                top_k=task.top_k,
                audio_key_bindings=task.audio_key_bindings,
                decision_graph=task.decision_graph,
                ensemble_base_policy_id=task.ensemble_base_policy_id,
                agent_policy_id=task.agent_policy_id,
                agent_aggregator_id=task.agent_aggregator_id,
                _trace_buffer=buffer,
            )
            return _BufferedSpeechNativeOutcome(
                outcome=SpeechNativeMatchOutcome(
                    task_id=task.task_id,
                    slot_id=slot_id,
                    decision=decision,
                ),
                buffer=buffer,
                error=None,
            )
        except BaseException as error:  # preserve one-shot traces before raising
            return _BufferedSpeechNativeOutcome(
                outcome=None,
                buffer=buffer,
                error=error,
            )
        finally:
            if buffer is not None:
                set_current_trace_buffer(None)
            if dispatch_granularity == "task":
                slots.put(slot_id)

    buffered: list[_BufferedSpeechNativeOutcome | None] = [None] * len(ordered_tasks)
    next_index = 0
    futures: dict[Future[_BufferedSpeechNativeOutcome], int] = {}
    query_admission_depth = min(
        slot_count if dispatch_granularity == "task" else slot_count * 4,
        queue_depth,
        len(ordered_tasks),
    )
    with ThreadPoolExecutor(
        max_workers=query_admission_depth,
        thread_name_prefix="saea-speech-native",
    ) as pool:
        while next_index < query_admission_depth:
            futures[pool.submit(one, ordered_tasks[next_index])] = next_index
            next_index += 1
        while futures:
            done, _ = wait(tuple(futures), return_when=FIRST_COMPLETED)
            for future in done:
                index = futures.pop(future)
                buffered[index] = future.result()
            while (
                next_index < len(ordered_tasks) and len(futures) < query_admission_depth
            ):
                futures[pool.submit(one, ordered_tasks[next_index])] = next_index
                next_index += 1
    if contact_pool is not None:
        contact_pool.shutdown(wait=True)

    settled = tuple(result for result in buffered if result is not None)
    if len(settled) != len(ordered_tasks):  # defensive: every future assigns once
        raise PsluFlightError("parallel speech-native dispatcher lost a task outcome")
    if trace_flusher is not None:
        for result in settled:
            assert result.buffer is not None
            trace_flusher(result.buffer)
    for result in settled:
        if result.error is not None:
            raise result.error
    outcomes = tuple(result.outcome for result in settled)
    if any(outcome is None for outcome in outcomes):  # defensive after error loop
        raise PsluFlightError("parallel speech-native task lacks a completed outcome")
    return tuple(outcome for outcome in outcomes if outcome is not None)


_OPENJIUWEN_M1_CONTROLLER_POLICY_ID = "speech-native-m1-openjiuwen-v1"
_OPENJIUWEN_M1_SPLIT_ID = "speech-native-profile-use"


@dataclass
class _SpeechNativeM1TaskAdapter(TaskAdapter):
    """Adapt the existing M1 profile task to the generic speech AgentLoop."""

    tasks: tuple[SpeechNativeMatchTask, ...]

    def __post_init__(self) -> None:
        self._task_by_sample_id = {task.sample.sample_id: task for task in self.tasks}

    def load_split(self, split_id: str) -> Sequence[object]:
        if split_id != _OPENJIUWEN_M1_SPLIT_ID:
            return ()
        return tuple(task.sample for task in self.tasks)

    def build_task_contract(self, sample: object, obs: ObsPacket) -> str:
        del obs
        if sample.sample_id not in self._task_by_sample_id:
            raise PsluFlightError(
                "speech-native Agent adapter received an unknown sample"
            )
        return (
            "Match the primary speech observation against the supplied TRAIN-built "
            "opaque scenario-key catalog and choose exactly one opaque key id. The "
            "catalog is task knowledge, never a replacement for the speech query."
        )

    def assemble_prompt(
        self, sample: object, supply: SupplyPacket | None
    ) -> Sequence[Mapping[str, object]]:
        if sample.sample_id not in self._task_by_sample_id:
            raise PsluFlightError(
                "speech-native Agent adapter received an unknown sample"
            )
        if supply is not None:
            raise PsluFlightError(
                "speech-native Agent prompt assembly receives knowledge through QueryState"
            )
        return (
            {"role": "system", "content": SPEECH_NATIVE_STABLE_SYSTEM_TEXT},
            {"role": "user", "content": ()},
        )

    def score(self, sample: object, response: str) -> Mapping[str, object]:
        task = self._task_by_sample_id[sample.sample_id]
        allowed = {card.key_id for card in task.key_cards}
        selected = _selected_key_id(response, allowed)
        return {
            "response_parsed": selected is not None,
            "selected_key_id": selected,
            "gold_observed": False,
        }

    def extract_consumption(
        self,
        sample: object,
        supply: SupplyPacket | None,
        response: str,
    ) -> ConsumptionTrace:
        return build_consumption_trace(
            span_id=f"{sample.sample_id}:openjiuwen-m1",
            supply=supply,
            response_text=response,
        )


@dataclass(frozen=True)
class _SpeechNativeM1AgentController:
    """M1 listwise and M2 semantic-first policies on the shared AgentLoop."""

    task: SpeechNativeMatchTask

    def _selection_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        decoding_params = dict(self.task.decoding_params)
        decoding_params.pop("id_slot", None)
        decoding_params["response_format"] = _key_choice_response_format(
            name="speech_native_openjiuwen_key_choice",
            key_ids=tuple(card.key_id for card in self.task.key_cards),
        )
        return AgentContactPlan(
            contact_id=f"{self.task.task_id}:listwise",
            query_state_sha256=context.query_state.content_hash(),
            purpose="speech-native-listwise-key-selection",
            instruction=(
                "Match the speech signal to exactly one supplied opaque key. Use the "
                "original speech observation and the TRAIN-built key representations "
                "jointly. Key headings contain an opaque K001 segment; return only that "
                "K001 id as one JSON object with exactly one field named key_id. "
                "Copy a supplied id exactly and do not invent or shorten it."
            ),
            key_representation_id=self.task.key_representation_id,
            matcher_policy_id=(f"{self.task.matcher_policy_id}:openjiuwen-listwise-v1"),
            decoding_params=decoding_params,
        ).validate()

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        if context.sample_id != self.task.sample.sample_id:
            raise PsluFlightError(
                "speech-native Agent controller is bound to a different query sample"
            )
        if self.task.matcher_policy_id == "M1":
            return self._selection_contact(context)
        decoding_params = dict(self.task.decoding_params)
        decoding_params.pop("id_slot", None)
        decoding_params["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "speech_native_semantic_state",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "intent_summary": {"type": "string"},
                        "discriminative_cues": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["intent_summary", "discriminative_cues"],
                    "additionalProperties": False,
                },
            },
        }
        return AgentContactPlan(
            contact_id=f"{self.task.task_id}:semantic-state",
            query_state_sha256=context.query_state.content_hash(),
            purpose="speech-native-semantic-state",
            instruction=(
                "Analyze the original speech without transcribing it. Produce a compact "
                "English intent summary and only the discriminative semantic cues that "
                "would help a later key match. Do not choose a key yet."
            ),
            key_representation_id=self.task.key_representation_id,
            matcher_policy_id="M2:openjiuwen-semantic-state-v1",
            decoding_params=decoding_params,
        ).validate()

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContactPlan,
        response_text: str,
    ) -> AgentLoopAdvance:
        if not isinstance(response_text, str):
            raise PsluFlightError("speech-native Agent contact must return one string")
        if self.task.matcher_policy_id == "M2" and context.query_state.loop_step == 0:
            state_id = f"state:{self.task.task_id}:semantic"
            state = AgentStateArtifact(
                state_id=state_id,
                state_kind="speech-semantic-cues",
                content=response_text,
                source_query_state_sha256=context.query_state.content_hash(),
                source_response_sha256=hashlib.sha256(
                    response_text.encode("utf-8")
                ).hexdigest(),
                producer_policy_id="M2:openjiuwen-semantic-state-v1",
                cited_value_ids=(),
            ).validate()
            ranked_facet_ids = tuple(sorted(context.catalog_facet_ids))
            rank_result = RankResult(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                query_state_sha256=context.query_state.content_hash(),
                ranking_policy_id="M2:complete-key-catalog-v1",
                candidates=tuple(
                    RankedFacet(facet_id=facet_id, score=0.0)
                    for facet_id in ranked_facet_ids
                ),
            ).validate()
            fusion_decision = FusionDecision(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                query_state_sha256=context.query_state.content_hash(),
                rank_result_sha256=rank_result.content_hash(),
                fusion_policy_id="M2:complete-key-catalog-v1",
                supporting_facet_ids=ranked_facet_ids,
                selected_value_ids=(),
            ).validate()
            next_state = QueryState(
                query_id=context.query_state.query_id,
                query_sample_id=context.query_state.query_sample_id,
                speech_packet_id=context.query_state.speech_packet_id,
                speech_packet_sha256=context.query_state.speech_packet_sha256,
                use_split_identity_hash=context.query_state.use_split_identity_hash,
                loop_step=1,
                visible_facet_ids=ranked_facet_ids,
                agent_state_ids=(state_id,),
            ).validate()
            return AgentLoopAdvance(
                transition=AgentStepTransition(
                    snapshot_sha256=context.knowledge_snapshot_sha256,
                    prior_query_state_sha256=context.query_state.content_hash(),
                    next_query_state_sha256=next_state.content_hash(),
                    action_kind="expand",
                    action_target_refs=(
                        f"rank-result:{rank_result.content_hash()}",
                        f"fusion-decision:{fusion_decision.content_hash()}",
                    ),
                    new_value_ids=(),
                    used_value_ids=(),
                    dropped_value_ids=(),
                    new_agent_state_ids=(state_id,),
                    dropped_agent_state_ids=(),
                    new_facet_ids=ranked_facet_ids,
                ).validate(),
                next_query_state=next_state,
                new_agent_states=(state,),
                next_contact=self._selection_contact(
                    replace(context, query_state=next_state, contact_index=1)
                ),
                rank_result=rank_result,
                fusion_decision=fusion_decision,
            )
        return AgentLoopAdvance(
            transition=AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                prior_query_state_sha256=context.query_state.content_hash(),
                next_query_state_sha256=None,
                action_kind="stop",
                action_target_refs=(),
                new_value_ids=(),
                used_value_ids=(),
                dropped_value_ids=(),
                new_agent_state_ids=(),
                dropped_agent_state_ids=(),
            ).validate(),
            next_query_state=None,
            new_agent_states=(),
            next_contact=None,
            final_response_contact_id=contact.contact_id,
        )


def validate_openjiuwen_speech_native_match_tasks(
    tasks: Sequence[SpeechNativeMatchTask],
    knowledge_snapshot: KnowledgeSnapshot,
) -> tuple[SpeechNativeMatchTask, ...]:
    ordered = tuple(tasks)
    if not ordered:
        raise PsluFlightError(
            "openJiuwen speech-native profile requires at least one task"
        )
    task_ids = tuple(task.task_id for task in ordered)
    sample_ids = tuple(task.sample.sample_id for task in ordered)
    if len(set(task_ids)) != len(task_ids):
        raise PsluFlightError("openJiuwen speech-native task ids must be unique")
    if len(set(sample_ids)) != len(sample_ids):
        raise PsluFlightError(
            "openJiuwen speech-native vertical slice requires one key order per query"
        )
    first_cards = _validated_key_cards(ordered[0].key_cards)
    first_matcher_policy_id = ordered[0].matcher_policy_id
    for task in ordered:
        if task.matcher_policy_id not in {"M1", "M2"} or (
            task.key_representation_id != "K2"
        ):
            raise PsluFlightError(
                "openJiuwen speech-native vertical slice only supports M1/M2 with "
                "K2 text keys"
            )
        if task.matcher_policy_id != first_matcher_policy_id:
            raise PsluFlightError(
                "openJiuwen speech-native tasks must share one matcher policy"
            )
        if task.mechanism_control_id == "key-text-shuffle-v1":
            raise PsluFlightError(
                "openJiuwen speech-native vertical slice does not support key-text shuffle"
            )
        if task.audio_key_bindings is not None or task.decision_graph is not None:
            raise PsluFlightError(
                "openJiuwen M1 text-key tasks cannot carry audio keys or decision graphs"
            )
        if _validated_key_cards(task.key_cards) != first_cards:
            raise PsluFlightError(
                "openJiuwen speech-native tasks must share one frozen key ordering"
            )
        if not hasattr(task.sample, "audio_ref") or not hasattr(
            task.sample, "audio_seconds"
        ):
            raise PsluFlightError(
                "openJiuwen speech-native samples must expose AudioRef and audio_seconds"
            )
        if set(task.query_descriptor) != {"packet_id", "sha256", "role"} or (
            task.query_descriptor.get("role") != "query"
        ):
            raise PsluFlightError(
                "openJiuwen speech-native query descriptor must bind one query packet"
            )

    knowledge_snapshot.validate()
    overlap = set(sample_ids) & set(knowledge_snapshot.source_sample_ids)
    if overlap:
        raise PsluFlightError(
            "openJiuwen speech-native USE samples overlap the TRAIN knowledge source: "
            f"{sorted(overlap)}"
        )
    value_by_id = {value.value_id: value for value in knowledge_snapshot.values}
    facet_by_id = {facet.facet_id: facet for facet in knowledge_snapshot.facets}
    for card in first_cards:
        value = value_by_id.get(f"value:{card.key_id}")
        if value is None or value.task_target != card.value_label:
            raise PsluFlightError(
                f"TRAIN knowledge snapshot does not bind {card.key_id!r} to its value"
            )
        key_material_text = "\n".join(
            facet_by_id[facet_id].representation
            for facet_id in value.associated_facet_ids
        )
        required_key_material = (
            card.definition,
            *card.positive_examples,
            card.contrastive_boundary,
        )
        if any(text not in key_material_text for text in required_key_material):
            raise PsluFlightError(
                f"TRAIN knowledge snapshot has incomplete K2 key facets for "
                f"{card.key_id!r}"
            )
    return ordered


def run_openjiuwen_speech_native_match_tasks(
    *,
    data_root: Path,
    plan: ExecutionPlan,
    core_client: object,
    tasks: Sequence[SpeechNativeMatchTask],
    knowledge_snapshot: KnowledgeSnapshot,
    slot_count: int,
    queue_depth: int,
    trace_flusher: Callable[[TraceBuffer], None] | None = None,
) -> tuple[SpeechNativeMatchOutcome, ...]:
    """Run the existing M1/K2 profile cell on the formal openJiuwen AgentLoop.

    This is deliberately a narrow, fail-closed vertical slice. It reuses the
    production task, decision, frozen-core, packet, and trace contracts while
    the generic AgentLoop grows key-order-specific retrieval and dynamic M2--M11
    evidence acquisition. No handwritten Agent runtime remains on this path.
    """

    ordered = validate_openjiuwen_speech_native_match_tasks(tasks, knowledge_snapshot)
    controller_by_sample_id = {
        task.sample.sample_id: _SpeechNativeM1AgentController(task) for task in ordered
    }
    registry = Registry("speech-native profile Agent controller")
    registry.register(
        _OPENJIUWEN_M1_CONTROLLER_POLICY_ID,
        lambda sample_id: controller_by_sample_id[sample_id],
    )
    trace_buffer = TraceBuffer(plan.run_id)
    matcher_policy_id = ordered[0].matcher_policy_id
    bootstrap_facet_ids = (
        tuple(facet.facet_id for facet in knowledge_snapshot.facets)
        if matcher_policy_id == "M1"
        else ()
    )
    max_contacts = 1 if matcher_policy_id == "M1" else 2
    try:
        summary = run_speech_native_agent_loop(
            data_root=data_root,
            plan=plan,
            adapter=_SpeechNativeM1TaskAdapter(ordered),
            core_client=core_client,
            split_id=_OPENJIUWEN_M1_SPLIT_ID,
            knowledge_snapshot=knowledge_snapshot,
            speech_packet_bindings={
                task.sample.sample_id: {
                    "packet_id": task.query_descriptor["packet_id"],
                    "sha256": task.query_descriptor["sha256"],
                }
                for task in ordered
            },
            controller_policy_id=_OPENJIUWEN_M1_CONTROLLER_POLICY_ID,
            bootstrap_facet_ids=bootstrap_facet_ids,
            max_contacts=max_contacts,
            slot_count=slot_count,
            queue_depth=queue_depth,
            trace_sink=trace_buffer,
            agent_executor_id="openjiuwen-workflow-v1",
            controller_registry=registry,
        )
    finally:
        if trace_flusher is not None:
            trace_flusher(trace_buffer)

    task_by_sample_id = {task.sample.sample_id: task for task in ordered}
    outcomes: list[SpeechNativeMatchOutcome] = []
    for result in summary.results:
        task = task_by_sample_id[result.sample_id]
        allowed = {card.key_id for card in task.key_cards}
        selected = _selected_key_id(result.final_response_text, allowed)
        card_by_id = {card.key_id: card for card in task.key_cards}
        if len(result.contacts) != max_contacts:
            raise PsluFlightError(
                f"openJiuwen {matcher_policy_id} trajectory must contain "
                f"{max_contacts} contacts"
            )
        raw_responses = (
            (result.final_response_text,)
            if matcher_policy_id == "M1"
            else (result.agent_states[0].content, result.final_response_text)
        )
        outcomes.append(
            SpeechNativeMatchOutcome(
                task_id=task.task_id,
                slot_id=result.contacts[0].slot_id,
                decision=SpeechNativeDecision(
                    matcher_policy_id=task.matcher_policy_id,
                    key_representation_id=task.key_representation_id,
                    key_id=selected,
                    value_label=(
                        card_by_id[selected].value_label
                        if selected in card_by_id
                        else None
                    ),
                    top_key_ids=(),
                    calls=max_contacts,
                    raw_responses=raw_responses,
                    verifier_scores={},
                    parse_failure=selected is None,
                ),
            )
        )
    return tuple(outcomes)


def _binding_rank(seed: int, purpose: str, *parts: str) -> str:
    text = "|".join((str(seed), purpose, *parts))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalized_sentence(sentence: str) -> str:
    return " ".join(sentence.casefold().split())


def partition_speech_native_train_knowledge(
    material: Sequence[SlurpTrainMaterial],
    *,
    use_sample_ids: Sequence[str],
) -> tuple[SlurpTrainMaterial, ...]:
    """Remove USE query identity groups from the TRAIN knowledge build.

    Speech-native optimization views are currently sampled from the governed
    natural TRAIN carrier. Treating those held-out views as DEV-role USE still
    requires construction to remove the exact recording, its utterance/text
    group, and its speaker group before a :class:`KnowledgeSnapshot` is built.
    """

    requested = tuple(use_sample_ids)
    if not requested or any(
        not isinstance(item, str) or not item for item in requested
    ):
        raise PsluFlightError(
            "knowledge partition USE sample ids must be non-empty strings"
        )
    if len(set(requested)) != len(requested):
        raise PsluFlightError("knowledge partition USE sample ids must be unique")
    requested_set = set(requested)
    found: set[str] = set()
    blocked_utterances: set[str] = set()
    blocked_sentences: set[str] = set()
    blocked_speakers: set[str] = set()
    for entry in material:
        matching = tuple(
            recording
            for recording in entry.recordings
            if recording.sample_id in requested_set
        )
        if not matching:
            continue
        found.update(recording.sample_id for recording in matching)
        blocked_utterances.add(entry.utterance_id)
        blocked_sentences.add(_normalized_sentence(entry.sentence))
        blocked_speakers.update(recording.speaker_id for recording in matching)
    missing = requested_set - found
    if missing:
        raise PsluFlightError(
            "knowledge partition cannot resolve USE samples in TRAIN material: "
            f"{sorted(missing)}"
        )

    construction: list[SlurpTrainMaterial] = []
    for entry in material:
        if (
            entry.utterance_id in blocked_utterances
            or _normalized_sentence(entry.sentence) in blocked_sentences
        ):
            continue
        recordings = tuple(
            recording
            for recording in entry.recordings
            if recording.sample_id not in requested_set
            and recording.speaker_id not in blocked_speakers
        )
        if recordings:
            construction.append(replace(entry, recordings=recordings))
    if not construction:
        raise PsluFlightError("knowledge partition removed the complete TRAIN corpus")
    return tuple(construction)


def _binding_sha256(document: Mapping[str, object]) -> str:
    raw = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_speech_native_binding(
    material: Sequence[SlurpTrainMaterial],
    *,
    seed: int,
    expected_scenarios: Sequence[str] = tuple(SPEECH_NATIVE_SCENARIO_DEFINITIONS),
    opt_a_per_scenario: int = 2,
    opt_b_per_scenario: int = 1,
    gate_per_scenario: int = 1,
    key_examples_per_scenario: int = 5,
) -> dict[str, object]:
    """Bind the small speech-native train partitions and their key cards.

    Selection is hash-ranked and therefore invariant to input iteration
    order. Query speakers are unique across all three optimization/gate
    splits. Key material excludes every query speaker, sample id, utterance
    and normalized sentence; the returned audit block rechecks all four
    disjointness claims before the document can be emitted.
    """

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise PsluFlightError("speech-native binding seed must be an integer")
    counts = (opt_a_per_scenario, opt_b_per_scenario, gate_per_scenario)
    if any(
        isinstance(count, bool) or not isinstance(count, int) or count <= 0
        for count in counts
    ):
        raise PsluFlightError("speech-native query counts must be positive integers")
    if (
        isinstance(key_examples_per_scenario, bool)
        or not isinstance(key_examples_per_scenario, int)
        or key_examples_per_scenario <= 0
    ):
        raise PsluFlightError("key_examples_per_scenario must be a positive integer")
    scenarios = tuple(expected_scenarios)
    if not scenarios or len(set(scenarios)) != len(scenarios):
        raise PsluFlightError("expected_scenarios must be non-empty and unique")
    unknown_definitions = set(scenarios) - set(SPEECH_NATIVE_SCENARIO_DEFINITIONS)
    if unknown_definitions:
        raise PsluFlightError(
            f"speech-native scenarios lack canonical definitions: {sorted(unknown_definitions)}"
        )
    by_scenario: dict[str, list[SlurpTrainMaterial]] = {
        scenario: [] for scenario in scenarios
    }
    for entry in material:
        if entry.scenario in by_scenario:
            by_scenario[entry.scenario].append(entry)
    missing = [scenario for scenario in scenarios if not by_scenario[scenario]]
    if missing:
        raise PsluFlightError(f"insufficient train material for scenarios {missing}")

    query_total = sum(counts)
    query_by_scenario: dict[str, list[dict[str, str]]] = {}
    query_speakers: set[str] = set()
    query_samples: set[str] = set()
    query_utterances: set[str] = set()
    query_sentences: set[str] = set()
    for scenario in scenarios:
        candidates = [
            (entry, recording)
            for entry in by_scenario[scenario]
            for recording in entry.recordings
        ]
        candidates.sort(
            key=lambda pair: _binding_rank(
                seed,
                "query",
                scenario,
                pair[0].utterance_id,
                pair[1].sample_id,
            )
        )
        selected: list[dict[str, str]] = []
        local_utterances: set[str] = set()
        local_sentences: set[str] = set()
        for entry, recording in candidates:
            normalized = _normalized_sentence(entry.sentence)
            if (
                entry.utterance_id in local_utterances
                or normalized in local_sentences
                or recording.speaker_id in query_speakers
            ):
                continue
            selected.append(
                {
                    "sample_id": recording.sample_id,
                    "utterance_id": entry.utterance_id,
                    "media_relpath": recording.media_relpath,
                    "speaker_id": recording.speaker_id,
                    "normalized_sentence": normalized,
                    "value_label": scenario,
                }
            )
            local_utterances.add(entry.utterance_id)
            local_sentences.add(normalized)
            query_speakers.add(recording.speaker_id)
            if len(selected) == query_total:
                break
        if len(selected) != query_total:
            raise PsluFlightError(
                f"insufficient speaker-isolated train queries for {scenario!r}: "
                f"needed {query_total}, found {len(selected)}"
            )
        query_by_scenario[scenario] = selected
        query_samples.update(item["sample_id"] for item in selected)
        query_utterances.update(item["utterance_id"] for item in selected)
        query_sentences.update(item["normalized_sentence"] for item in selected)

    split_items: dict[str, list[dict[str, str]]] = {
        "OPT-A36": [],
        "OPT-B18": [],
        "GATE18": [],
    }
    for scenario in scenarios:
        selected = query_by_scenario[scenario]
        a_end = opt_a_per_scenario
        b_end = a_end + opt_b_per_scenario
        split_items["OPT-A36"].extend(selected[:a_end])
        split_items["OPT-B18"].extend(selected[a_end:b_end])
        split_items["GATE18"].extend(selected[b_end:])

    key_cards: list[dict[str, object]] = []
    key_material: list[dict[str, object]] = []
    key_speakers: set[str] = set()
    key_samples: set[str] = set()
    key_utterances: set[str] = set()
    key_sentences: set[str] = set()
    for key_index, scenario in enumerate(scenarios, start=1):
        candidates = [
            (entry, recording)
            for entry in by_scenario[scenario]
            for recording in entry.recordings
        ]
        candidates.sort(
            key=lambda pair: _binding_rank(
                seed,
                "key",
                scenario,
                pair[0].utterance_id,
                pair[1].sample_id,
            )
        )
        sources: list[dict[str, str]] = []
        local_utterances: set[str] = set()
        for entry, recording in candidates:
            normalized = _normalized_sentence(entry.sentence)
            if (
                recording.speaker_id in query_speakers
                or recording.sample_id in query_samples
                or entry.utterance_id in query_utterances
                or normalized in query_sentences
                or entry.utterance_id in local_utterances
                or normalized in key_sentences
            ):
                continue
            sources.append(
                {
                    "sample_id": recording.sample_id,
                    "utterance_id": entry.utterance_id,
                    "media_relpath": recording.media_relpath,
                    "speaker_id": recording.speaker_id,
                    "sentence": entry.sentence,
                    "normalized_sentence": normalized,
                }
            )
            local_utterances.add(entry.utterance_id)
            key_speakers.add(recording.speaker_id)
            key_samples.add(recording.sample_id)
            key_utterances.add(entry.utterance_id)
            key_sentences.add(normalized)
            if len(sources) == key_examples_per_scenario:
                break
        if len(sources) != key_examples_per_scenario:
            raise PsluFlightError(
                f"insufficient query-isolated key examples for {scenario!r}: needed "
                f"{key_examples_per_scenario}, found {len(sources)}"
            )
        key_id = f"K{key_index:03d}"
        card = KeyCardV1(
            key_id=key_id,
            definition=SPEECH_NATIVE_SCENARIO_DEFINITIONS[scenario],
            positive_examples=tuple(source["sentence"] for source in sources),
            contrastive_boundary=SPEECH_NATIVE_SCENARIO_CONTRASTS[scenario],
            value_label=scenario,
        ).validate()
        key_cards.append(card.as_json())
        key_material.append(
            {
                "key_id": key_id,
                "sources": sources,
                "audio_key_source_sample_id": sources[0]["sample_id"],
            }
        )

    if not query_speakers.isdisjoint(key_speakers):
        raise PsluFlightError("query/key speaker isolation failed")
    if not query_samples.isdisjoint(key_samples):
        raise PsluFlightError("query/key audio isolation failed")
    if not query_utterances.isdisjoint(key_utterances):
        raise PsluFlightError("query/key utterance isolation failed")
    if not query_sentences.isdisjoint(key_sentences):
        raise PsluFlightError("query/key text isolation failed")

    split_documents: dict[str, object] = {}
    for split_name, items in split_items.items():
        ordered = sorted(
            items, key=lambda item: (item["value_label"], item["sample_id"])
        )
        identity = {
            "schema": "saea-speech-native-split-v1",
            "name": split_name,
            "seed": seed,
            "sample_ids": [item["sample_id"] for item in ordered],
        }
        split_documents[split_name] = {
            **identity,
            "split_identity_hash": _binding_sha256(identity),
            "items": ordered,
        }
    opt_a_document = split_documents["OPT-A36"]
    if not isinstance(opt_a_document, Mapping):  # defensive: locally constructed above
        raise PsluFlightError("OPT-A36 split document is malformed")
    opt_a_items = opt_a_document["items"]
    if not isinstance(opt_a_items, list):  # defensive: locally constructed above
        raise PsluFlightError("OPT-A36 items are malformed")
    engineering_items = [
        {
            "sample_id": item["sample_id"],
            "media_relpath": item["media_relpath"],
        }
        for item in opt_a_items[:8]
    ]
    engineering_identity = {
        "schema": "saea-speech-native-split-v1",
        "name": "ENG-GATE8",
        "seed": seed,
        "sample_ids": [item["sample_id"] for item in engineering_items],
    }
    engineering_gate = {
        **engineering_identity,
        "split_identity_hash": _binding_sha256(engineering_identity),
        "items": engineering_items,
    }
    unsigned: dict[str, object] = {
        "schema": "saea-speech-native-binding-v1",
        "status": "MODEL-FREE BINDING; NOT AN EXPOSURE REGISTRATION",
        "seed": seed,
        "source_split": "SLURP train real speech only",
        "splits": split_documents,
        # A derived engineering-only view of OPT-A. It is not an additional
        # scientific split and therefore does not change query/key isolation
        # accounting. Its exact identity lets preprocessing and inference
        # register only the eight packets they actually touch.
        "engineering_gate": engineering_gate,
        "key_cards": key_cards,
        "key_material": key_material,
        "isolation_audit": {
            "query_sample_count": len(query_samples),
            "query_speaker_count": len(query_speakers),
            "key_example_count": len(key_samples),
            "query_key_sample_overlap": 0,
            "query_key_utterance_overlap": 0,
            "query_key_normalized_sentence_overlap": 0,
            "query_key_speaker_overlap": 0,
        },
    }
    return {**unsigned, "binding_sha256": _binding_sha256(unsigned)}


_KNOWLEDGE_TOKEN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


def _knowledge_features(sentence: str) -> set[str]:
    tokens = _KNOWLEDGE_TOKEN.findall(sentence.casefold())
    return set(tokens).union(
        f"{tokens[index]} {tokens[index + 1]}" for index in range(len(tokens) - 1)
    )


def _validate_speech_native_knowledge_build(
    *,
    seed: int,
    policy_id: str,
    expected_scenarios: Sequence[str],
    key_examples_per_scenario: int,
) -> tuple[str, ...]:
    """Validate the shared inputs of the pure build and legacy wrapper."""

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise PsluFlightError("speech-native knowledge seed must be an integer")
    if policy_id not in SPEECH_NATIVE_KNOWLEDGE_POLICY_IDS:
        raise PsluFlightError(
            f"unsupported speech-native knowledge policy {policy_id!r}"
        )
    if (
        isinstance(key_examples_per_scenario, bool)
        or not isinstance(key_examples_per_scenario, int)
        or key_examples_per_scenario <= 0
    ):
        raise PsluFlightError(
            "knowledge key_examples_per_scenario must be a positive integer"
        )
    scenarios = tuple(expected_scenarios)
    if not scenarios or len(set(scenarios)) != len(scenarios):
        raise PsluFlightError("knowledge scenarios must be non-empty and unique")
    unknown_scenarios = set(scenarios) - set(SPEECH_NATIVE_SCENARIO_DEFINITIONS)
    if unknown_scenarios:
        raise PsluFlightError(
            f"knowledge scenarios lack canonical definitions: {sorted(unknown_scenarios)}"
        )
    return scenarios


def _select_speech_native_knowledge(
    material: Sequence[SlurpTrainMaterial],
    *,
    seed: int,
    policy_id: str,
    scenarios: tuple[str, ...],
    key_examples_per_scenario: int,
    key_id_by_scenario: Mapping[str, str],
    excluded_sample_ids: frozenset[str] = frozenset(),
    excluded_utterance_ids: frozenset[str] = frozenset(),
    excluded_normalized_sentences: frozenset[str] = frozenset(),
    excluded_speaker_ids: frozenset[str] = frozenset(),
) -> dict[str, object]:
    """Build train-derived key material under explicit identity exclusions.

    The public pure builder below passes empty exclusions because its input is
    already the TRAIN knowledge-construction partition.  The historical
    combined-binding wrapper passes its embedded query identities so its
    output remains byte-compatible with the earlier isolation behavior.
    """

    if set(key_id_by_scenario) != set(scenarios):
        raise PsluFlightError("knowledge key ids do not match scenarios")
    ordered_material = tuple(
        sorted(material, key=lambda entry: (entry.scenario, entry.utterance_id))
    )
    if not all(isinstance(entry, SlurpTrainMaterial) for entry in ordered_material):
        raise PsluFlightError(
            "speech-native knowledge material must contain SlurpTrainMaterial entries"
        )
    corpus = tuple(
        entry
        for entry in ordered_material
        if entry.scenario in key_id_by_scenario
        and entry.utterance_id not in excluded_utterance_ids
        and _normalized_sentence(entry.sentence) not in excluded_normalized_sentences
    )
    if not corpus:
        raise PsluFlightError(
            "speech-native knowledge corpus is empty after query isolation"
        )
    by_scenario: dict[str, list[SlurpTrainMaterial]] = {
        scenario: [] for scenario in scenarios
    }
    for entry in corpus:
        by_scenario[entry.scenario].append(entry)
    missing_material = [scenario for scenario in scenarios if not by_scenario[scenario]]
    if missing_material:
        raise PsluFlightError(
            f"speech-native knowledge corpus lacks scenarios {missing_material}"
        )

    feature_df: Counter[str] = Counter()
    scenario_feature_df: dict[str, Counter[str]] = defaultdict(Counter)
    scenario_counts: Counter[str] = Counter()
    action_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for entry in corpus:
        features = _knowledge_features(entry.sentence)
        feature_df.update(features)
        scenario_feature_df[entry.scenario].update(features)
        scenario_counts[entry.scenario] += 1
        action_counts[entry.scenario][entry.action] += 1
    corpus_count = len(corpus)

    missing_facets = sorted(
        (scenario, action)
        for scenario in scenarios
        for action in action_counts[scenario]
        if (scenario, action) not in SPEECH_NATIVE_ACTION_FACET_DESCRIPTIONS
    )
    if missing_facets:
        raise PsluFlightError(
            f"speech-native knowledge actions lack English facets: {missing_facets}"
        )

    def specificity(entry: SlurpTrainMaterial) -> float:
        label_count = scenario_counts[entry.scenario]
        other_count = corpus_count - label_count
        if other_count <= 0:
            raise PsluFlightError(
                "speech-native specificity needs at least two scenarios"
            )
        lifts: list[float] = []
        for feature in _knowledge_features(entry.sentence):
            total = feature_df[feature]
            if total < 5:
                continue
            within = scenario_feature_df[entry.scenario][feature]
            outside = total - within
            within_rate = (within + 0.5) / (label_count + 1.0)
            outside_rate = (outside + 0.5) / (other_count + 1.0)
            lift = math.log2(within_rate / outside_rate)
            if lift > 0:
                lifts.append(lift)
        lifts.sort(reverse=True)
        semantic_score = sum(lifts[:3]) / min(3, len(lifts)) if lifts else -20.0
        token_count = len(_KNOWLEDGE_TOKEN.findall(entry.sentence))
        length_penalty = 0.0
        if token_count < 3:
            length_penalty = float(3 - token_count)
        elif token_count > 16:
            length_penalty = 0.25 * float(token_count - 16)
        return semantic_score - length_penalty

    key_cards: list[dict[str, object]] = []
    key_material: list[dict[str, object]] = []
    revision_keys: list[dict[str, object]] = []
    key_samples: set[str] = set()
    key_utterances: set[str] = set()
    key_sentences: set[str] = set()
    key_speakers: set[str] = set()

    for scenario in scenarios:
        ranked_actions = tuple(
            action
            for action, _count in sorted(
                action_counts[scenario].items(), key=lambda item: (-item[1], item[0])
            )
        )
        ranked_candidates = sorted(
            (
                (entry, recording, specificity(entry))
                for entry in by_scenario[scenario]
                for recording in sorted(
                    entry.recordings, key=lambda item: item.sample_id
                )
                if recording.speaker_id not in excluded_speaker_ids
                and recording.sample_id not in excluded_sample_ids
            ),
            key=lambda item: (
                -item[2],
                _binding_rank(
                    seed,
                    "knowledge",
                    scenario,
                    item[0].action,
                    item[0].utterance_id,
                    item[1].sample_id,
                ),
            ),
        )
        selected: list[tuple[SlurpTrainMaterial, SlurpTrainRecording, float]] = []
        local_utterances: set[str] = set()

        def select_one(action: str | None) -> bool:
            for entry, recording, score in ranked_candidates:
                normalized = _normalized_sentence(entry.sentence)
                if action is not None and entry.action != action:
                    continue
                if (
                    entry.utterance_id in local_utterances
                    or entry.utterance_id in key_utterances
                    or normalized in key_sentences
                    or recording.sample_id in key_samples
                ):
                    continue
                selected.append((entry, recording, score))
                local_utterances.add(entry.utterance_id)
                key_samples.add(recording.sample_id)
                key_utterances.add(entry.utterance_id)
                key_sentences.add(normalized)
                key_speakers.add(recording.speaker_id)
                return True
            return False

        actions_requiring_examples = (
            ranked_actions
            if policy_id == SPEECH_NATIVE_INFORMATION_COMPLETE_KNOWLEDGE_POLICY_ID
            else ranked_actions[:key_examples_per_scenario]
        )
        for action in actions_requiring_examples:
            if not select_one(action):
                raise PsluFlightError(
                    f"no isolated knowledge prototype for {scenario!r}/{action!r}"
                )
        while len(selected) < key_examples_per_scenario:
            if not select_one(None):
                break
        if len(selected) < key_examples_per_scenario:
            raise PsluFlightError(
                f"insufficient isolated knowledge examples for {scenario!r}: needed "
                f"at least {key_examples_per_scenario}, found {len(selected)}"
            )

        selected_actions = {entry.action for entry, _recording, _score in selected}
        action_total = sum(action_counts[scenario].values())
        covered_action_mass = (
            sum(action_counts[scenario][action] for action in selected_actions)
            / action_total
        )
        cumulative = 0
        examples_for_95_percent = 0
        for action in ranked_actions:
            cumulative += action_counts[scenario][action]
            examples_for_95_percent += 1
            if cumulative / action_total >= 0.95:
                break
        facet_text = "; ".join(
            SPEECH_NATIVE_ACTION_FACET_DESCRIPTIONS[(scenario, action)]
            for action in ranked_actions
        )
        definition = (
            f"{SPEECH_NATIVE_SCENARIO_DEFINITIONS[scenario]} "
            f"Dataset-derived action facets: {facet_text}."
        )
        key_id = key_id_by_scenario[scenario]
        sources = [
            {
                "sample_id": recording.sample_id,
                "utterance_id": entry.utterance_id,
                "media_relpath": recording.media_relpath,
                "speaker_id": recording.speaker_id,
                "sentence": entry.sentence,
                "normalized_sentence": _normalized_sentence(entry.sentence),
            }
            for entry, recording, _score in selected
        ]
        card = KeyCardV1(
            key_id=key_id,
            definition=definition,
            positive_examples=tuple(source["sentence"] for source in sources),
            contrastive_boundary=SPEECH_NATIVE_SCENARIO_CONTRASTS[scenario],
            value_label=scenario,
        ).validate()
        key_cards.append(card.as_json())
        key_material.append(
            {
                "key_id": key_id,
                "sources": sources,
                "audio_key_source_sample_id": sources[0]["sample_id"],
            }
        )
        revision_keys.append(
            {
                "key_id": key_id,
                "value_label": scenario,
                "dataset_action_counts": dict(sorted(action_counts[scenario].items())),
                "selected_actions": sorted(selected_actions),
                "missing_example_actions": sorted(
                    set(ranked_actions) - selected_actions
                ),
                "covered_action_mass": round(covered_action_mass, 8),
                "examples_needed_for_95pct_action_mass": examples_for_95_percent,
                "selected_source_sample_ids": [
                    source["sample_id"] for source in sources
                ],
                "selected_specificity_scores": [
                    round(score, 8) for _entry, _recording, score in selected
                ],
            }
        )

    return {
        "corpus": corpus,
        "corpus_count": corpus_count,
        "key_cards": key_cards,
        "key_material": key_material,
        "revision_keys": revision_keys,
        "key_samples": frozenset(key_samples),
        "key_utterances": frozenset(key_utterances),
        "key_sentences": frozenset(key_sentences),
        "key_speakers": frozenset(key_speakers),
    }


def build_speech_native_knowledge_snapshot(
    material: Sequence[SlurpTrainMaterial],
    *,
    seed: int,
    policy_id: str = SPEECH_NATIVE_KNOWLEDGE_POLICY_ID,
    expected_scenarios: Sequence[str] = tuple(SPEECH_NATIVE_SCENARIO_DEFINITIONS),
    key_examples_per_scenario: int = 5,
) -> KnowledgeSnapshot:
    """Build one standalone, model-free TRAIN knowledge snapshot.

    Unlike :func:`refine_speech_native_binding_knowledge`, this function has
    no query binding argument and cannot observe OPT/DEV identities.  Its
    input is the already separated TRAIN knowledge-construction partition.
    The snapshot models the complete supplied train distribution: scenario
    and action facets reference every natural recording, while each value
    carries maintainable selected examples plus sample-, utterance-, and
    speaker-group provenance and a train-derived scenario prior.
    """

    scenarios = _validate_speech_native_knowledge_build(
        seed=seed,
        policy_id=policy_id,
        expected_scenarios=expected_scenarios,
        key_examples_per_scenario=key_examples_per_scenario,
    )
    key_id_by_scenario = {
        scenario: f"K{index:03d}" for index, scenario in enumerate(scenarios, start=1)
    }
    selection = _select_speech_native_knowledge(
        material,
        seed=seed,
        policy_id=policy_id,
        scenarios=scenarios,
        key_examples_per_scenario=key_examples_per_scenario,
        key_id_by_scenario=key_id_by_scenario,
    )
    corpus = selection["corpus"]
    key_cards = selection["key_cards"]
    key_material = selection["key_material"]
    if (
        not isinstance(corpus, tuple)
        or not isinstance(key_cards, list)
        or not isinstance(key_material, list)
    ):
        raise PsluFlightError("speech-native knowledge selection is malformed")

    card_by_key = {
        str(card["key_id"]): card for card in key_cards if isinstance(card, Mapping)
    }
    material_by_key = {
        str(item["key_id"]): item for item in key_material if isinstance(item, Mapping)
    }
    rows_by_scenario_action: dict[
        tuple[str, str], list[tuple[SlurpTrainMaterial, SlurpTrainRecording]]
    ] = defaultdict(list)
    sample_identity: dict[str, tuple[str, str, str]] = {}
    for entry in corpus:
        for recording in sorted(entry.recordings, key=lambda item: item.sample_id):
            identity = (
                entry.utterance_id,
                recording.speaker_id,
                recording.media_relpath,
            )
            previous = sample_identity.get(recording.sample_id)
            if previous is not None and previous != identity:
                raise PsluFlightError(
                    f"train sample {recording.sample_id!r} has conflicting group identity"
                )
            if previous is not None:
                raise PsluFlightError(
                    f"train sample {recording.sample_id!r} occurs more than once"
                )
            sample_identity[recording.sample_id] = identity
            rows_by_scenario_action[(entry.scenario, entry.action)].append(
                (entry, recording)
            )
    if not sample_identity:
        raise PsluFlightError(
            "speech-native TRAIN knowledge snapshot has zero recordings"
        )

    facets: list[KeyFacet] = []
    values: list[ValueBundle] = []
    total_recordings = len(sample_identity)
    for scenario in scenarios:
        key_id = key_id_by_scenario[scenario]
        scenario_rows = [
            row
            for (row_scenario, _action), rows in rows_by_scenario_action.items()
            if row_scenario == scenario
            for row in rows
        ]
        scenario_source_ids = tuple(
            sorted(recording.sample_id for _entry, recording in scenario_rows)
        )
        if not scenario_source_ids:
            raise PsluFlightError(
                f"speech-native TRAIN snapshot lacks recordings for {scenario!r}"
            )
        scenario_facet_id = f"facet:{key_id}:scenario"
        facets.append(
            KeyFacet(
                facet_id=scenario_facet_id,
                dimension="scenario",
                representation_kind="text",
                representation=SPEECH_NATIVE_SCENARIO_DEFINITIONS[scenario],
                source_sample_ids=scenario_source_ids,
            ).validate()
        )
        action_facet_ids: list[str] = []
        for action in sorted(
            action
            for row_scenario, action in rows_by_scenario_action
            if row_scenario == scenario
        ):
            action_rows = rows_by_scenario_action[(scenario, action)]
            action_facet_id = f"facet:{key_id}:action:{action}"
            action_facet_ids.append(action_facet_id)
            facets.append(
                KeyFacet(
                    facet_id=action_facet_id,
                    dimension="action",
                    representation_kind="text",
                    representation=SPEECH_NATIVE_ACTION_FACET_DESCRIPTIONS[
                        (scenario, action)
                    ],
                    source_sample_ids=tuple(
                        sorted(recording.sample_id for _entry, recording in action_rows)
                    ),
                    parent_facet_ids=(scenario_facet_id,),
                ).validate()
            )

        card = card_by_key.get(key_id)
        if card is None:
            raise PsluFlightError(f"TRAIN snapshot lacks selected card {key_id!r}")
        examples = card.get("positive_examples")
        boundary = card.get("contrastive_boundary")
        definition = card.get("definition")
        if (
            not isinstance(examples, list)
            or not all(isinstance(item, str) and item for item in examples)
            or not isinstance(boundary, str)
            or not boundary
            or not isinstance(definition, str)
            or not definition
        ):
            raise PsluFlightError(f"TRAIN snapshot card {key_id!r} is malformed")
        material_entry = material_by_key.get(key_id)
        raw_sources = (
            material_entry.get("sources")
            if isinstance(material_entry, Mapping)
            else None
        )
        if not isinstance(raw_sources, list):
            raise PsluFlightError(
                f"TRAIN snapshot key material {key_id!r} is malformed"
            )
        card_source_ids = tuple(
            str(source["sample_id"])
            for source in raw_sources
            if isinstance(source, Mapping) and isinstance(source.get("sample_id"), str)
        )
        if len(card_source_ids) != len(raw_sources) or not card_source_ids:
            raise PsluFlightError(
                f"TRAIN snapshot key material {key_id!r} lacks source identities"
            )
        card_facet_id = f"facet:{key_id}:contrastive-card"
        facets.append(
            KeyFacet(
                facet_id=card_facet_id,
                dimension="contrastive-card",
                representation_kind="text",
                representation=(
                    f"Definition: {definition}\n"
                    f"Positive examples: {' | '.join(examples)}\n"
                    f"Contrastive boundary: {boundary}"
                ),
                source_sample_ids=card_source_ids,
                parent_facet_ids=(scenario_facet_id,),
            ).validate()
        )
        provenance_refs = tuple(
            sorted(
                {
                    *(
                        f"sample:{recording.sample_id}"
                        for _entry, recording in scenario_rows
                    ),
                    *(
                        f"utterance:{entry.utterance_id}"
                        for entry, _recording in scenario_rows
                    ),
                    *(
                        f"speaker:{recording.speaker_id}"
                        for _entry, recording in scenario_rows
                    ),
                }
            )
        )
        values.append(
            ValueBundle(
                value_id=f"value:{key_id}",
                content=f"Deterministic task-target mapping for opaque key {key_id}.",
                associated_facet_ids=(
                    scenario_facet_id,
                    card_facet_id,
                    *action_facet_ids,
                ),
                source_sample_ids=scenario_source_ids,
                provenance_refs=provenance_refs,
                task_target=scenario,
                prior_score=len(scenario_source_ids) / total_recordings,
            ).validate()
        )

    source_sample_ids = tuple(sorted(sample_identity))
    source_split_identity_hash = hashlib.sha256(
        "\n".join(source_sample_ids).encode("utf-8")
    ).hexdigest()
    build_descriptor = {
        "schema": "saea-speech-native-knowledge-build-v1",
        "source_split_identity_hash": source_split_identity_hash,
        "seed": seed,
        "policy_id": policy_id,
        "scenarios": list(scenarios),
        "key_examples_per_scenario": key_examples_per_scenario,
    }
    build_sha256 = _binding_sha256(build_descriptor)
    return KnowledgeSnapshot(
        snapshot_id=f"slurp-train-knowledge-{build_sha256[:16]}",
        source_split_identity_hash=source_split_identity_hash,
        source_sample_ids=source_sample_ids,
        builder_policy_id=f"{policy_id}@{build_sha256}",
        facets=tuple(facets),
        values=tuple(values),
    ).validate()


def refine_speech_native_binding_knowledge(
    base_binding: Mapping[str, object],
    material: Sequence[SlurpTrainMaterial],
    *,
    seed: int,
    policy_id: str = SPEECH_NATIVE_KNOWLEDGE_POLICY_ID,
    expected_scenarios: Sequence[str] = tuple(SPEECH_NATIVE_SCENARIO_DEFINITIONS),
    key_examples_per_scenario: int = 5,
) -> dict[str, object]:
    """Compatibility wrapper for the historical combined binding artifact.

    The existing binding's split identities and engineering view remain byte
    identical while the shared pure selector replaces only key material.  New
    BUILD/USE work must call :func:`build_speech_native_knowledge_snapshot`;
    this wrapper remains for historical configs and receipts.  No fitted
    classifier, model contact, held-out split, or reference transcript enters
    either path.
    """

    scenarios = _validate_speech_native_knowledge_build(
        seed=seed,
        policy_id=policy_id,
        expected_scenarios=expected_scenarios,
        key_examples_per_scenario=key_examples_per_scenario,
    )
    claimed_sha256 = base_binding.get("binding_sha256")
    unsigned_base = dict(base_binding)
    unsigned_base.pop("binding_sha256", None)
    if claimed_sha256 != _binding_sha256(unsigned_base):
        raise PsluFlightError("speech-native parent binding self-hash mismatch")
    if "knowledge_revision" in base_binding:
        raise PsluFlightError(
            "speech-native binding already has a knowledge revision; use its parent"
        )

    raw_cards = base_binding.get("key_cards")
    if not isinstance(raw_cards, list):
        raise PsluFlightError("speech-native parent binding lacks key cards")
    key_id_by_scenario: dict[str, str] = {}
    for raw_card in raw_cards:
        if not isinstance(raw_card, Mapping):
            raise PsluFlightError("speech-native parent key cards must be objects")
        key_id = raw_card.get("key_id")
        value_label = raw_card.get("value_label")
        if (
            not isinstance(key_id, str)
            or not isinstance(value_label, str)
            or value_label in key_id_by_scenario
        ):
            raise PsluFlightError("speech-native parent key card ids are malformed")
        key_id_by_scenario[value_label] = key_id
    if set(key_id_by_scenario) != set(scenarios):
        raise PsluFlightError(
            "speech-native parent key cards do not match knowledge scenarios"
        )

    raw_splits = base_binding.get("splits")
    if not isinstance(raw_splits, Mapping) or not raw_splits:
        raise PsluFlightError("speech-native parent binding lacks query splits")
    query_samples: set[str] = set()
    query_utterances: set[str] = set()
    query_sentences: set[str] = set()
    query_speakers: set[str] = set()
    for raw_split in raw_splits.values():
        if not isinstance(raw_split, Mapping) or not isinstance(
            raw_split.get("items"), list
        ):
            raise PsluFlightError("speech-native parent split is malformed")
        for raw_item in raw_split["items"]:
            if not isinstance(raw_item, Mapping):
                raise PsluFlightError("speech-native parent query item is malformed")
            fields = {
                "sample": raw_item.get("sample_id"),
                "utterance": raw_item.get("utterance_id"),
                "sentence": raw_item.get("normalized_sentence"),
                "speaker": raw_item.get("speaker_id"),
            }
            if not all(isinstance(value, str) and value for value in fields.values()):
                raise PsluFlightError(
                    "speech-native parent query identity is malformed"
                )
            query_samples.add(fields["sample"])
            query_utterances.add(fields["utterance"])
            query_sentences.add(fields["sentence"])
            query_speakers.add(fields["speaker"])

    selection = _select_speech_native_knowledge(
        material,
        seed=seed,
        policy_id=policy_id,
        scenarios=scenarios,
        key_examples_per_scenario=key_examples_per_scenario,
        key_id_by_scenario=key_id_by_scenario,
        excluded_sample_ids=frozenset(query_samples),
        excluded_utterance_ids=frozenset(query_utterances),
        excluded_normalized_sentences=frozenset(query_sentences),
        excluded_speaker_ids=frozenset(query_speakers),
    )
    key_cards = selection["key_cards"]
    key_material = selection["key_material"]
    revision_keys = selection["revision_keys"]
    key_samples = selection["key_samples"]
    key_utterances = selection["key_utterances"]
    key_sentences = selection["key_sentences"]
    key_speakers = selection["key_speakers"]
    corpus_count = selection["corpus_count"]
    if (
        not isinstance(key_cards, list)
        or not isinstance(key_material, list)
        or not isinstance(revision_keys, list)
        or not isinstance(key_samples, frozenset)
        or not isinstance(key_utterances, frozenset)
        or not isinstance(key_sentences, frozenset)
        or not isinstance(key_speakers, frozenset)
        or not isinstance(corpus_count, int)
    ):
        raise PsluFlightError("speech-native knowledge selection is malformed")

    if not query_samples.isdisjoint(key_samples):
        raise PsluFlightError("refined query/key audio isolation failed")
    if not query_utterances.isdisjoint(key_utterances):
        raise PsluFlightError("refined query/key utterance isolation failed")
    if not query_sentences.isdisjoint(key_sentences):
        raise PsluFlightError("refined query/key text isolation failed")
    if not query_speakers.isdisjoint(key_speakers):
        raise PsluFlightError("refined query/key speaker isolation failed")

    successor = deepcopy(dict(base_binding))
    successor.pop("binding_sha256", None)
    successor["key_cards"] = key_cards
    successor["key_material"] = key_material
    successor["knowledge_parent_binding_sha256"] = claimed_sha256
    knowledge_revision: dict[str, object] = {
        "schema": "saea-speech-native-knowledge-revision-v1",
        "policy_id": policy_id,
        "seed": seed,
        "source_split": "SLURP train real speech only",
        "query_excluded_corpus_utterances": corpus_count,
        "key_count": len(key_cards),
        "selection_signal": (
            "smoothed scenario-vs-rest unigram/bigram lift with length penalty"
        ),
        "keys": revision_keys,
    }
    if policy_id == SPEECH_NATIVE_KNOWLEDGE_POLICY_ID:
        knowledge_revision["examples_per_key"] = key_examples_per_scenario
    else:
        example_count_by_key = {
            str(key["key_id"]): len(key["selected_source_sample_ids"])
            for key in revision_keys
        }
        knowledge_revision.update(
            {
                "minimum_examples_per_key": key_examples_per_scenario,
                "maximum_examples_per_key": max(example_count_by_key.values()),
                "example_count_by_key": example_count_by_key,
            }
        )
    successor["knowledge_revision"] = knowledge_revision
    successor["isolation_audit"] = {
        "query_sample_count": len(query_samples),
        "query_speaker_count": len(query_speakers),
        "key_example_count": len(key_samples),
        "query_key_sample_overlap": 0,
        "query_key_utterance_overlap": 0,
        "query_key_normalized_sentence_overlap": 0,
        "query_key_speaker_overlap": 0,
    }
    successor["binding_sha256"] = _binding_sha256(successor)
    return successor


_KNOWLEDGE_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "all",
        "an",
        "and",
        "are",
        "at",
        "be",
        "can",
        "could",
        "do",
        "for",
        "from",
        "get",
        "give",
        "have",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "please",
        "show",
        "tell",
        "that",
        "the",
        "this",
        "to",
        "what",
        "when",
        "with",
        "you",
    }
)

_DATASET_SEMANTIC_BOUNDARY_SPECS: Mapping[tuple[str, str], Mapping[str, object]] = (
    MappingProxyType(
        {
            ("calendar", "datetime"): {
                "left_source_terms": ("calendar", "meeting", "appointment"),
                "right_source_terms": (
                    "christmas",
                    "halloween",
                    "holiday",
                    "valentine",
                    "match",
                ),
                "left_exclusion": (
                    "use the other key for a general date, day, or time question about "
                    "a public or named event; use {left_key_id} only for the user's "
                    "stored or scheduled calendar item"
                ),
                "right_exclusion": (
                    "use the other key for the user's stored or scheduled calendar "
                    "item, meeting, or appointment; use {right_key_id} for a general "
                    "date, day, or time question about a public or named event"
                ),
                "supported_relations": (
                    ("query", ("event_name",)),
                    ("query", ("date", "event_name")),
                ),
            },
            ("lists", "social"): {
                "left_source_terms": ("list", "tasks", "jobs"),
                "right_source_terms": ("likes", "status", "social media"),
                "left_exclusion": (
                    "use the other key for social-network engagement, likes, status, "
                    "posts, or platform activity even when a date is mentioned"
                ),
                "right_exclusion": (
                    "use the other key for the user's tasks, jobs, or list contents; "
                    "a date mention alone is not social-network evidence"
                ),
                "supported_relations": (("query", ("date",)),),
            },
            ("news", "social"): {
                "left_source_terms": ("news", "headline", "current events"),
                "right_source_terms": ("likes", "status", "social media"),
                "left_exclusion": (
                    "use the other key for social-network engagement, likes, status, "
                    "posts, or platform activity even when a date is mentioned"
                ),
                "right_exclusion": (
                    "use the other key for general news reports, headlines, or current "
                    "events without social-account or platform engagement"
                ),
                "supported_relations": (("query", ("date",)),),
            },
        }
    )
)


@dataclass(frozen=True)
class _DatasetSemanticBoundarySupply:
    left_exclusion: str
    right_exclusion: str
    provenance_ids: tuple[str, ...]


def _dataset_semantic_boundary_supply(
    corpus: Sequence[SlurpTrainMaterial],
    *,
    left: str,
    right: str,
    left_key_id: str,
    right_key_id: str,
) -> _DatasetSemanticBoundarySupply:
    """Render a bounded human-readable abstraction backed by train examples."""

    spec = _DATASET_SEMANTIC_BOUNDARY_SPECS.get((left, right))
    if spec is None:
        return _DatasetSemanticBoundarySupply("", "", ())

    def source_ids(scenario: str, raw_terms: object) -> tuple[str, ...]:
        if not isinstance(raw_terms, tuple) or not all(
            isinstance(term, str) and term for term in raw_terms
        ):
            raise PsluFlightError("semantic boundary source terms are malformed")
        selected: list[str] = []
        seen_sentences: set[str] = set()
        for entry in sorted(corpus, key=lambda item: item.utterance_id):
            normalized = _normalized_sentence(entry.sentence)
            if (
                entry.scenario != scenario
                or entry.action != "query"
                or normalized in seen_sentences
                or not any(term in normalized for term in raw_terms)
            ):
                continue
            selected.append(entry.utterance_id)
            seen_sentences.add(normalized)
            if len(selected) == 3:
                break
        return tuple(selected)

    left_sources = source_ids(left, spec.get("left_source_terms"))
    right_sources = source_ids(right, spec.get("right_source_terms"))
    if len(left_sources) < 2 or len(right_sources) < 2:
        return _DatasetSemanticBoundarySupply("", "", ())
    left_rule = spec.get("left_exclusion")
    right_rule = spec.get("right_exclusion")
    if not isinstance(left_rule, str) or not isinstance(right_rule, str):
        raise PsluFlightError("semantic boundary rules are malformed")
    return _DatasetSemanticBoundarySupply(
        left_exclusion=(
            f" Dataset-grounded semantic boundary supporting {right_key_id}: "
            f"{left_rule.format(left_key_id=left_key_id, right_key_id=right_key_id)}."
        ),
        right_exclusion=(
            f" Dataset-grounded semantic boundary supporting {left_key_id}: "
            f"{right_rule.format(left_key_id=left_key_id, right_key_id=right_key_id)}."
        ),
        provenance_ids=(
            f"slurp-train-semantic-boundary-v1:{left}:{right}:{left}:sources-"
            + "+".join(left_sources),
            f"slurp-train-semantic-boundary-v1:{left}:{right}:{right}:sources-"
            + "+".join(right_sources),
        ),
    )


def _semantic_boundary_supported_relations(
    pair: tuple[str, str],
) -> frozenset[tuple[str, tuple[str, ...]]]:
    spec = _DATASET_SEMANTIC_BOUNDARY_SPECS.get(pair)
    if spec is None:
        return frozenset()
    raw = spec.get("supported_relations")
    if not isinstance(raw, tuple):
        raise PsluFlightError("semantic boundary supported relations are malformed")
    return frozenset(raw)


def _semantic_boundary_present(
    boundary: DecisionBoundaryV1,
    expected: _DatasetSemanticBoundarySupply,
) -> bool:
    return bool(
        expected.provenance_ids
        and set(expected.provenance_ids) <= set(boundary.provenance_ids)
        and expected.left_exclusion in boundary.left_exclusion
        and expected.right_exclusion in boundary.right_exclusion
    )


def _signature_lexical_cues(
    primary: Sequence[SlurpTrainMaterial],
    other: Sequence[SlurpTrainMaterial],
    *,
    maximum: int = _SIGNATURE_LEXICAL_CUE_COUNT,
) -> tuple[tuple[str, int, int, float], ...]:
    """Return compact corpus-derived cues that discriminate one residual side.

    Each utterance contributes a feature at most once. Cues require repeated
    support, exclude content-free features, and are ranked by prevalence times
    smoothed log rate ratio. The final float is the log-ratio weight used by the
    model-free cross-fit diagnostic.
    """

    if not primary or not other or maximum <= 0:
        return ()
    primary_counts: Counter[str] = Counter()
    other_counts: Counter[str] = Counter()
    for entry in primary:
        primary_counts.update(_knowledge_features(entry.sentence))
    for entry in other:
        other_counts.update(_knowledge_features(entry.sentence))

    ranked: list[tuple[float, int, str, int, float]] = []
    for feature, count in primary_counts.items():
        if count < 2:
            continue
        feature_tokens = feature.split()
        if not any(
            token not in _KNOWLEDGE_STOPWORDS and not token.isdigit()
            for token in feature_tokens
        ):
            continue
        other_count = other_counts[feature]
        log_ratio = math.log2(
            ((count + 0.5) / (len(primary) + 1.0))
            / ((other_count + 0.5) / (len(other) + 1.0))
        )
        if log_ratio <= 0.0:
            continue
        rank_score = (count / len(primary)) * log_ratio
        ranked.append((rank_score, count, feature, other_count, log_ratio))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return tuple(
        (feature, count, other_count, log_ratio)
        for _score, count, feature, other_count, log_ratio in ranked[:maximum]
    )


def _render_signature_lexical_cues(
    *,
    supporting_key_id: str,
    action: str,
    entity_signature_text: str,
    cues: Sequence[tuple[str, int, int, float]],
) -> str:
    if not cues:
        return ""
    cue_text = "; ".join(f'"{feature}"' for feature, *_rest in cues)
    return (
        f" Train-derived lexical cues supporting {supporting_key_id} for shared "
        f"action {action} and entity types {entity_signature_text}: {cue_text}."
    )


def build_data_derived_decision_graph(
    knowledge_binding: Mapping[str, object],
    material: Sequence[SlurpTrainMaterial],
    *,
    graph_id: str,
    expected_scenarios: Sequence[str] = tuple(SPEECH_NATIVE_SCENARIO_DEFINITIONS),
    maximum_boundaries: int = 30,
    boundary_policy_id: str = "ranked-pair-signal-v1",
) -> DecisionGraphV1:
    """Build action-complete factors and versioned boundaries from SLURP train.

    The graph consumes the same query-isolated corpus as the knowledge
    successor.  Target statements stay maintainable English, action factors
    are admitted only when observed in train, and the historical policy ranks
    pair boundaries by model-free lexical and action-distribution overlap. The
    shared-action policy instead covers every stably operation-ambiguous pair
    and supplies bounded train-derived entity-rate asymmetry without
    truncation. Neither policy uses model outputs, rewards, held-out labels,
    reference transcripts at runtime, or devel/test material.
    """

    if (
        isinstance(maximum_boundaries, bool)
        or not isinstance(maximum_boundaries, int)
        or maximum_boundaries <= 0
    ):
        raise PsluFlightError("maximum_boundaries must be a positive integer")
    if boundary_policy_id not in SPEECH_NATIVE_BOUNDARY_POLICY_IDS:
        raise PsluFlightError(
            "boundary_policy_id must name one registered decision-graph policy"
        )
    claimed_sha256 = knowledge_binding.get("binding_sha256")
    unsigned = dict(knowledge_binding)
    unsigned.pop("binding_sha256", None)
    if claimed_sha256 != _binding_sha256(unsigned):
        raise PsluFlightError("knowledge binding self-hash mismatch")
    revision = knowledge_binding.get("knowledge_revision")
    if (
        not isinstance(revision, Mapping)
        or revision.get("policy_id") not in SPEECH_NATIVE_KNOWLEDGE_POLICY_IDS
    ):
        raise PsluFlightError(
            "data-derived graph requires the action-stratified knowledge successor"
        )

    scenarios = tuple(expected_scenarios)
    if not scenarios or len(set(scenarios)) != len(scenarios):
        raise PsluFlightError("graph scenarios must be non-empty and unique")
    raw_cards = knowledge_binding.get("key_cards")
    if not isinstance(raw_cards, list):
        raise PsluFlightError("knowledge binding lacks key cards")
    cards_by_scenario: dict[str, KeyCardV1] = {}
    for raw in raw_cards:
        if not isinstance(raw, Mapping):
            raise PsluFlightError("knowledge key card must be an object")
        examples = raw.get("positive_examples")
        if not isinstance(examples, list) or not all(
            isinstance(example, str) for example in examples
        ):
            raise PsluFlightError("knowledge key card examples must be strings")
        card = KeyCardV1(
            key_id=str(raw.get("key_id")),
            definition=str(raw.get("definition")),
            positive_examples=tuple(examples),
            contrastive_boundary=(
                str(raw["contrastive_boundary"])
                if raw.get("contrastive_boundary") is not None
                else None
            ),
            value_label=str(raw.get("value_label")),
        ).validate()
        if card.value_label in cards_by_scenario:
            raise PsluFlightError("knowledge key cards contain duplicate labels")
        cards_by_scenario[card.value_label] = card
    if set(cards_by_scenario) != set(scenarios):
        raise PsluFlightError("knowledge key cards do not match graph scenarios")

    raw_splits = knowledge_binding.get("splits")
    if not isinstance(raw_splits, Mapping) or not raw_splits:
        raise PsluFlightError("knowledge binding lacks query splits")
    query_utterances: set[str] = set()
    query_sentences: set[str] = set()
    for raw_split in raw_splits.values():
        if not isinstance(raw_split, Mapping) or not isinstance(
            raw_split.get("items"), list
        ):
            raise PsluFlightError("knowledge query split is malformed")
        for raw_item in raw_split["items"]:
            if not isinstance(raw_item, Mapping):
                raise PsluFlightError("knowledge query item is malformed")
            utterance_id = raw_item.get("utterance_id")
            normalized_sentence = raw_item.get("normalized_sentence")
            if (
                not isinstance(utterance_id, str)
                or not utterance_id
                or not isinstance(normalized_sentence, str)
                or not normalized_sentence
            ):
                raise PsluFlightError("knowledge query identity is malformed")
            query_utterances.add(utterance_id)
            query_sentences.add(normalized_sentence)

    corpus = tuple(
        entry
        for entry in sorted(
            material, key=lambda item: (item.scenario, item.utterance_id)
        )
        if entry.scenario in cards_by_scenario
        and entry.utterance_id not in query_utterances
        and _normalized_sentence(entry.sentence) not in query_sentences
    )
    by_scenario: dict[str, list[SlurpTrainMaterial]] = {
        scenario: [] for scenario in scenarios
    }
    for entry in corpus:
        by_scenario[entry.scenario].append(entry)
    missing = [scenario for scenario in scenarios if not by_scenario[scenario]]
    if missing:
        raise PsluFlightError(f"data-derived graph corpus lacks scenarios {missing}")

    action_counts: dict[str, Counter[str]] = defaultdict(Counter)
    entity_types_by_scenario_action: dict[tuple[str, str], Counter[str]] = defaultdict(
        Counter
    )
    lexical_counts: dict[str, Counter[str]] = defaultdict(Counter)
    document_frequency: Counter[str] = Counter()
    for entry in corpus:
        action_counts[entry.scenario][entry.action] += 1
        if any(
            not isinstance(entity_type, str) or not entity_type
            for entity_type in entry.entity_types
        ):
            raise PsluFlightError(
                "data-derived graph corpus contains a malformed entity type"
            )
        entity_types_by_scenario_action[(entry.scenario, entry.action)].update(
            set(entry.entity_types)
        )
        tokens = {
            token
            for token in _KNOWLEDGE_TOKEN.findall(entry.sentence.casefold())
            if token not in _KNOWLEDGE_STOPWORDS and len(token) > 1
        }
        lexical_counts[entry.scenario].update(tokens)
        document_frequency.update(tokens)
    missing_facets = sorted(
        (scenario, action)
        for scenario in scenarios
        for action in action_counts[scenario]
        if (scenario, action) not in SPEECH_NATIVE_ACTION_FACET_DESCRIPTIONS
    )
    if missing_facets:
        raise PsluFlightError(
            f"data-derived graph actions lack English facets: {missing_facets}"
        )
    action_scenario_frequency = Counter(
        action for scenario in scenarios for action in action_counts[scenario]
    )
    maximum_action_information = math.log2(len(scenarios))

    document_count = len(corpus)
    weighted_lexical: dict[str, dict[str, float]] = {}
    for scenario in scenarios:
        weighted_lexical[scenario] = {
            token: count
            * (
                math.log((document_count + 1.0) / (document_frequency[token] + 1.0))
                + 1.0
            )
            for token, count in lexical_counts[scenario].items()
            if document_frequency[token] >= 5
        }

    def cosine(left: str, right: str) -> float:
        left_values = weighted_lexical[left]
        right_values = weighted_lexical[right]
        common = set(left_values) & set(right_values)
        numerator = sum(left_values[token] * right_values[token] for token in common)
        left_norm = math.sqrt(sum(value * value for value in left_values.values()))
        right_norm = math.sqrt(sum(value * value for value in right_values.values()))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return numerator / (left_norm * right_norm)

    def action_overlap(left: str, right: str) -> float:
        left_total = sum(action_counts[left].values())
        right_total = sum(action_counts[right].values())
        return sum(
            min(
                action_counts[left][action] / left_total,
                action_counts[right][action] / right_total,
            )
            * (
                math.log2(len(scenarios) / action_scenario_frequency[action])
                / maximum_action_information
                if maximum_action_information > 0.0
                else 0.0
            )
            for action in set(action_counts[left]) & set(action_counts[right])
        )

    factors: list[DecisionFactorV1] = []
    target_factor_by_scenario: dict[str, str] = {}
    operation_factors_by_scenario: dict[str, list[str]] = defaultdict(list)
    operation_factor_by_scenario_action: dict[tuple[str, str], str] = {}
    for scenario in scenarios:
        factor_id = f"F{len(factors) + 1:03d}"
        target_factor_by_scenario[scenario] = factor_id
        factors.append(
            DecisionFactorV1(
                factor_id=factor_id,
                kind="target",
                statement=SPEECH_NATIVE_SCENARIO_DEFINITIONS[scenario],
                key_ids=(cards_by_scenario[scenario].key_id,),
                provenance_ids=(
                    f"key-card:{cards_by_scenario[scenario].key_id}:definition",
                ),
            )
        )
    for scenario in scenarios:
        for action in sorted(action_counts[scenario]):
            factor_id = f"F{len(factors) + 1:03d}"
            operation_factors_by_scenario[scenario].append(factor_id)
            operation_factor_by_scenario_action[(scenario, action)] = factor_id
            factors.append(
                DecisionFactorV1(
                    factor_id=factor_id,
                    kind="operation",
                    statement=SPEECH_NATIVE_ACTION_FACET_DESCRIPTIONS[
                        (scenario, action)
                    ],
                    key_ids=(cards_by_scenario[scenario].key_id,),
                    provenance_ids=(f"slurp-train-action:{scenario}:{action}",),
                )
            )

    pair_signals: list[tuple[float, float, float, str, str]] = []
    for left_index, left in enumerate(scenarios):
        for right in scenarios[left_index + 1 :]:
            lexical = cosine(left, right)
            action = action_overlap(left, right)
            combined = 0.65 * lexical + 0.35 * action
            pair_signals.append((combined, lexical, action, left, right))
    boundaries: list[DecisionBoundaryV1] = []
    if boundary_policy_id == "ranked-pair-signal-v1":
        ranked_pairs = sorted(
            pair_signals,
            key=lambda item: (-item[0], -item[1], -item[2], item[3], item[4]),
        )[: min(maximum_boundaries, len(pair_signals))]
        for _combined, lexical, action, left, right in ranked_pairs:
            left_card = cards_by_scenario[left]
            right_card = cards_by_scenario[right]
            boundaries.append(
                DecisionBoundaryV1(
                    boundary_id=f"B{len(boundaries) + 1:03d}",
                    left_key_id=left_card.key_id,
                    right_key_id=right_card.key_id,
                    left_factor_ids=(
                        target_factor_by_scenario[left],
                        *operation_factors_by_scenario[left],
                    ),
                    right_factor_ids=(
                        target_factor_by_scenario[right],
                        *operation_factors_by_scenario[right],
                    ),
                    left_exclusion=(
                        "Do not choose this side when the speech instead expresses "
                        + SPEECH_NATIVE_SCENARIO_DEFINITIONS[right]
                        .rstrip(".")
                        .casefold()
                        + "."
                    ),
                    right_exclusion=(
                        "Do not choose this side when the speech instead expresses "
                        + SPEECH_NATIVE_SCENARIO_DEFINITIONS[left]
                        .rstrip(".")
                        .casefold()
                        + "."
                    ),
                    provenance_ids=(
                        f"slurp-train-pair-signal:{left}:{right}:"
                        f"lexical-{lexical:.8f}:action-{action:.8f}",
                        f"key-card:{left_card.key_id}:definition",
                        f"key-card:{right_card.key_id}:definition",
                    ),
                )
            )
    else:
        EntityRateEvidence = tuple[str, int, int, float, float]

        def discriminative_entity_types(
            primary_counts: Counter[str],
            other_counts: Counter[str],
            *,
            primary_total: int,
            other_total: int,
        ) -> tuple[EntityRateEvidence, ...]:
            ranked: list[tuple[float, EntityRateEvidence]] = []
            for entity_type, count in primary_counts.items():
                prevalence = count / primary_total
                other_count = other_counts[entity_type]
                rate_ratio = ((count + 1.0) / (primary_total + 2.0)) / (
                    (other_count + 1.0) / (other_total + 2.0)
                )
                if (
                    count < _DISCRIMINATIVE_ENTITY_MIN_SUPPORT
                    or prevalence < _DISCRIMINATIVE_ENTITY_MIN_PREVALENCE
                    or rate_ratio < _DISCRIMINATIVE_ENTITY_MIN_RATE_RATIO
                ):
                    continue
                evidence = (
                    entity_type,
                    count,
                    other_count,
                    prevalence,
                    rate_ratio,
                )
                information_score = prevalence * math.log2(rate_ratio)
                ranked.append((information_score, evidence))
            return tuple(
                evidence
                for _score, evidence in sorted(
                    ranked,
                    key=lambda item: (-item[0], -item[1][1], item[1][0]),
                )[:_DISCRIMINATIVE_ENTITY_MAX_PER_SIDE]
            )

        shared_pairs: list[
            tuple[
                str,
                str,
                tuple[str, ...],
                tuple[EntityRateEvidence, ...],
                tuple[EntityRateEvidence, ...],
            ]
        ] = []
        for left_index, left in enumerate(scenarios):
            for right in scenarios[left_index + 1 :]:
                shared_actions = tuple(
                    sorted(
                        action
                        for action in set(action_counts[left])
                        & set(action_counts[right])
                        if action_counts[left][action]
                        >= _STABLE_SHARED_ACTION_MIN_SUPPORT
                        and action_counts[right][action]
                        >= _STABLE_SHARED_ACTION_MIN_SUPPORT
                    )
                )
                if not shared_actions:
                    continue
                left_entity_counts = sum(
                    (
                        entity_types_by_scenario_action[(left, action)]
                        for action in shared_actions
                    ),
                    Counter(),
                )
                right_entity_counts = sum(
                    (
                        entity_types_by_scenario_action[(right, action)]
                        for action in shared_actions
                    ),
                    Counter(),
                )
                left_total = sum(
                    action_counts[left][action] for action in shared_actions
                )
                right_total = sum(
                    action_counts[right][action] for action in shared_actions
                )
                left_evidence = discriminative_entity_types(
                    left_entity_counts,
                    right_entity_counts,
                    primary_total=left_total,
                    other_total=right_total,
                )
                right_evidence = discriminative_entity_types(
                    right_entity_counts,
                    left_entity_counts,
                    primary_total=right_total,
                    other_total=left_total,
                )
                if not left_evidence or not right_evidence:
                    raise PsluFlightError(
                        "shared-action boundary lacks bilateral supported entity "
                        "asymmetry: "
                        f"{left}/{right} actions={list(shared_actions)}"
                    )
                shared_pairs.append(
                    (left, right, shared_actions, left_evidence, right_evidence)
                )
        if len(shared_pairs) > maximum_boundaries:
            raise PsluFlightError(
                "shared-action boundary policy refuses truncation: "
                f"requires {len(shared_pairs)} boundaries but maximum_boundaries="
                f"{maximum_boundaries}"
            )

        signature_material: dict[
            tuple[str, str, tuple[str, ...]], list[SlurpTrainMaterial]
        ] = defaultdict(list)
        for entry in corpus:
            signature_material[
                (
                    entry.scenario,
                    entry.action,
                    tuple(sorted(set(entry.entity_types))),
                )
            ].append(entry)
        visible_sentences = {
            scenario: {
                _normalized_sentence(example)
                for example in cards_by_scenario[scenario].positive_examples
            }
            for scenario in scenarios
        }

        def lexical_prototype(
            primary: Sequence[SlurpTrainMaterial],
            other: Sequence[SlurpTrainMaterial],
            *,
            scenario: str,
            leave_one_out: bool = False,
        ) -> SlurpTrainMaterial:
            primary_counts: Counter[str] = Counter()
            other_counts: Counter[str] = Counter()
            for entry in primary:
                primary_counts.update(_knowledge_features(entry.sentence))
            for entry in other:
                other_counts.update(_knowledge_features(entry.sentence))

            def score(entry: SlurpTrainMaterial) -> float:
                entry_features = _knowledge_features(entry.sentence)
                primary_size = len(primary) - int(leave_one_out)
                lifts = sorted(
                    (
                        math.log2(
                            (
                                (
                                    primary_counts[feature]
                                    - int(leave_one_out and feature in entry_features)
                                    + 0.5
                                )
                                / (primary_size + 1.0)
                            )
                            / ((other_counts[feature] + 0.5) / (len(other) + 1.0))
                        )
                        for feature in entry_features
                    ),
                    reverse=True,
                )
                return sum(value for value in lifts[:3] if value > 0.0)

            candidates = [
                entry
                for entry in primary
                if _normalized_sentence(entry.sentence)
                not in visible_sentences[scenario]
            ]
            if not candidates:
                raise PsluFlightError(
                    "signature lexical boundary lacks a prototype not already "
                    f"visible in key examples for {scenario!r}"
                )
            return sorted(
                candidates,
                key=lambda entry: (-score(entry), entry.utterance_id),
            )[0]

        def render_entity_types(
            evidence: tuple[EntityRateEvidence, ...],
        ) -> str:
            return ", ".join(
                entity_type.replace("_", " ")
                for entity_type, _count, _other_count, _prevalence, _ratio in evidence
            )

        for left, right, shared_actions, left_evidence, right_evidence in shared_pairs:
            left_card = cards_by_scenario[left]
            right_card = cards_by_scenario[right]
            action_text = ", ".join(shared_actions)
            lexical_provenance: list[str] = []
            left_lexical_exclusions: list[str] = []
            right_lexical_exclusions: list[str] = []
            if boundary_policy_id in {
                "shared-signature-lexical-boundaries-v3",
                "shared-signature-complete-boundaries-v4",
            }:
                residual_signatures: list[
                    tuple[
                        int,
                        int,
                        str,
                        tuple[str, ...],
                        tuple[SlurpTrainMaterial, ...],
                        tuple[SlurpTrainMaterial, ...],
                    ]
                ] = []
                for action in shared_actions:
                    entity_signatures = {
                        signature
                        for scenario, candidate_action, signature in signature_material
                        if scenario == left and candidate_action == action
                    } & {
                        signature
                        for scenario, candidate_action, signature in signature_material
                        if scenario == right and candidate_action == action
                    }
                    for entity_signature in entity_signatures:
                        left_entries = tuple(
                            signature_material[(left, action, entity_signature)]
                        )
                        right_entries = tuple(
                            signature_material[(right, action, entity_signature)]
                        )
                        if (
                            len(left_entries) < _STABLE_SHARED_ACTION_MIN_SUPPORT
                            or len(right_entries) < _STABLE_SHARED_ACTION_MIN_SUPPORT
                        ):
                            continue
                        residual_signatures.append(
                            (
                                min(len(left_entries), len(right_entries)),
                                len(left_entries) + len(right_entries),
                                action,
                                entity_signature,
                                left_entries,
                                right_entries,
                            )
                        )
                if not residual_signatures:
                    raise PsluFlightError(
                        "signature lexical boundary lacks a stable residual "
                        f"signature for {left}/{right}"
                    )
                ordered_residual_signatures = sorted(
                    residual_signatures,
                    key=lambda item: (-item[0], -item[1], item[2], item[3]),
                )
                selected_residual_signatures = (
                    ordered_residual_signatures[:1]
                    if boundary_policy_id == "shared-signature-lexical-boundaries-v3"
                    else ordered_residual_signatures
                )
                for (
                    _minimum_support,
                    _total_support,
                    lexical_action,
                    lexical_entities,
                    left_entries,
                    right_entries,
                ) in selected_residual_signatures:
                    left_prototype = lexical_prototype(
                        left_entries,
                        right_entries,
                        scenario=left,
                        leave_one_out=(
                            boundary_policy_id
                            == "shared-signature-complete-boundaries-v4"
                        ),
                    )
                    right_prototype = lexical_prototype(
                        right_entries,
                        left_entries,
                        scenario=right,
                        leave_one_out=(
                            boundary_policy_id
                            == "shared-signature-complete-boundaries-v4"
                        ),
                    )
                    entity_signature_text = (
                        ", ".join(item.replace("_", " ") for item in lexical_entities)
                        if lexical_entities
                        else "none"
                    )
                    entity_signature_id = (
                        "+".join(lexical_entities) if lexical_entities else "none"
                    )
                    left_lexical_exclusions.append(
                        f" Train-derived prototype supporting {right_card.key_id} for "
                        f"shared action {lexical_action} and entity types "
                        f'{entity_signature_text}: "{right_prototype.sentence}".'
                    )
                    right_lexical_exclusions.append(
                        f" Train-derived prototype supporting {left_card.key_id} for "
                        f"shared action {lexical_action} and entity types "
                        f'{entity_signature_text}: "{left_prototype.sentence}".'
                    )
                    if boundary_policy_id == "shared-signature-complete-boundaries-v4":
                        left_cues = _signature_lexical_cues(left_entries, right_entries)
                        right_cues = _signature_lexical_cues(
                            right_entries, left_entries
                        )
                        left_lexical_exclusions.append(
                            _render_signature_lexical_cues(
                                supporting_key_id=right_card.key_id,
                                action=lexical_action,
                                entity_signature_text=entity_signature_text,
                                cues=right_cues,
                            )
                        )
                        right_lexical_exclusions.append(
                            _render_signature_lexical_cues(
                                supporting_key_id=left_card.key_id,
                                action=lexical_action,
                                entity_signature_text=entity_signature_text,
                                cues=left_cues,
                            )
                        )
                    if boundary_policy_id == "shared-signature-lexical-boundaries-v3":
                        lexical_provenance.append(
                            f"slurp-train-signature-lexical:{left}:{right}:"
                            f"{lexical_action}:{entity_signature_id}:"
                            f"support-{len(left_entries)}-{len(right_entries)}:"
                            f"prototypes-{left_prototype.utterance_id}-"
                            f"{right_prototype.utterance_id}"
                        )
                    else:
                        relation_prefix = (
                            f"{left}:{right}:{lexical_action}:{entity_signature_id}"
                        )
                        lexical_provenance.extend(
                            (
                                "slurp-train-signature-lexical-v4:"
                                f"{relation_prefix}:support-{len(left_entries)}-"
                                f"{len(right_entries)}",
                                "slurp-train-signature-prototype-v4:"
                                f"{relation_prefix}:{left}:"
                                f"{left_prototype.utterance_id}",
                                "slurp-train-signature-prototype-v4:"
                                f"{relation_prefix}:{right}:"
                                f"{right_prototype.utterance_id}",
                            )
                        )
                if boundary_policy_id == "shared-signature-complete-boundaries-v4":
                    semantic_supply = _dataset_semantic_boundary_supply(
                        corpus,
                        left=left,
                        right=right,
                        left_key_id=left_card.key_id,
                        right_key_id=right_card.key_id,
                    )
                    if semantic_supply.provenance_ids:
                        left_lexical_exclusions.append(semantic_supply.left_exclusion)
                        right_lexical_exclusions.append(semantic_supply.right_exclusion)
                        lexical_provenance.extend(semantic_supply.provenance_ids)
            boundaries.append(
                DecisionBoundaryV1(
                    boundary_id=f"B{len(boundaries) + 1:03d}",
                    left_key_id=left_card.key_id,
                    right_key_id=right_card.key_id,
                    left_factor_ids=(
                        target_factor_by_scenario[left],
                        *(
                            operation_factor_by_scenario_action[(left, action)]
                            for action in shared_actions
                        ),
                    ),
                    right_factor_ids=(
                        target_factor_by_scenario[right],
                        *(
                            operation_factor_by_scenario_action[(right, action)]
                            for action in shared_actions
                        ),
                    ),
                    left_exclusion=(
                        "Do not choose this side for shared operation evidence "
                        f"({action_text}) when the speech instead refers to entity "
                        "categories at least 5x more prevalent for the other key: "
                        f"{render_entity_types(right_evidence)}."
                        + "".join(left_lexical_exclusions)
                    ),
                    right_exclusion=(
                        "Do not choose this side for shared operation evidence "
                        f"({action_text}) when the speech instead refers to entity "
                        "categories at least 5x more prevalent for the other key: "
                        f"{render_entity_types(left_evidence)}."
                        + "".join(right_lexical_exclusions)
                    ),
                    provenance_ids=(
                        f"slurp-train-stable-shared-actions:{left}:{right}:"
                        + ",".join(shared_actions),
                        *(
                            f"slurp-train-entity-rate:{left}:{right}:{left}:"
                            f"{entity_type}:count-{count}:other-{other_count}:"
                            f"prevalence-{prevalence:.8f}:ratio-{rate_ratio:.8f}"
                            for entity_type, count, other_count, prevalence, rate_ratio in left_evidence
                        ),
                        *(
                            f"slurp-train-entity-rate:{left}:{right}:{right}:"
                            f"{entity_type}:count-{count}:other-{other_count}:"
                            f"prevalence-{prevalence:.8f}:ratio-{rate_ratio:.8f}"
                            for entity_type, count, other_count, prevalence, rate_ratio in right_evidence
                        ),
                        *lexical_provenance,
                        f"key-card:{left_card.key_id}:definition",
                        f"key-card:{right_card.key_id}:definition",
                    ),
                )
            )

    graph = DecisionGraphV1(
        graph_id=graph_id,
        factors=tuple(factors),
        boundaries=tuple(boundaries),
    )
    return graph.validate(tuple(cards_by_scenario[scenario] for scenario in scenarios))


def build_speech_native_information_audit(
    knowledge_binding: Mapping[str, object],
    material: Sequence[SlurpTrainMaterial],
    graph: DecisionGraphV1,
    *,
    expected_scenarios: Sequence[str] = tuple(SPEECH_NATIVE_SCENARIO_DEFINITIONS),
    minimum_example_action_mass: float = 0.95,
) -> dict[str, object]:
    """Audit task information and knowledge supply without model contact.

    The audit measures empirical scenario information in train-only action and
    entity-type signatures. Generated semantic state is not counted as new
    information: it may reorganize speech evidence, but only retrieved,
    registered knowledge can add evidence that was absent from a prior call.
    """

    if (
        isinstance(minimum_example_action_mass, bool)
        or not isinstance(minimum_example_action_mass, (int, float))
        or not 0.0 < float(minimum_example_action_mass) <= 1.0
    ):
        raise PsluFlightError("minimum_example_action_mass must be a number in (0, 1]")
    claimed_sha256 = knowledge_binding.get("binding_sha256")
    unsigned = dict(knowledge_binding)
    unsigned.pop("binding_sha256", None)
    if claimed_sha256 != _binding_sha256(unsigned):
        raise PsluFlightError("knowledge binding self-hash mismatch")
    revision = knowledge_binding.get("knowledge_revision")
    if (
        not isinstance(revision, Mapping)
        or revision.get("policy_id") not in SPEECH_NATIVE_KNOWLEDGE_POLICY_IDS
    ):
        raise PsluFlightError(
            "information audit requires the action-stratified knowledge successor"
        )

    scenarios = tuple(expected_scenarios)
    if not scenarios or len(set(scenarios)) != len(scenarios):
        raise PsluFlightError(
            "information-audit scenarios must be non-empty and unique"
        )
    raw_cards = knowledge_binding.get("key_cards")
    if not isinstance(raw_cards, list):
        raise PsluFlightError("knowledge binding lacks key cards")
    cards_by_scenario: dict[str, KeyCardV1] = {}
    scenario_by_key_id: dict[str, str] = {}
    for raw in raw_cards:
        if not isinstance(raw, Mapping):
            raise PsluFlightError("knowledge key card must be an object")
        examples = raw.get("positive_examples")
        if not isinstance(examples, list) or not all(
            isinstance(example, str) for example in examples
        ):
            raise PsluFlightError("knowledge key card examples must be strings")
        card = KeyCardV1(
            key_id=str(raw.get("key_id")),
            definition=str(raw.get("definition")),
            positive_examples=tuple(examples),
            contrastive_boundary=(
                str(raw["contrastive_boundary"])
                if raw.get("contrastive_boundary") is not None
                else None
            ),
            value_label=str(raw.get("value_label")),
        ).validate()
        if card.value_label in cards_by_scenario or card.key_id in scenario_by_key_id:
            raise PsluFlightError("knowledge key cards contain duplicate labels or ids")
        cards_by_scenario[card.value_label] = card
        scenario_by_key_id[card.key_id] = card.value_label
    if set(cards_by_scenario) != set(scenarios):
        raise PsluFlightError("knowledge key cards do not match audit scenarios")
    graph.validate(tuple(cards_by_scenario[scenario] for scenario in scenarios))

    raw_splits = knowledge_binding.get("splits")
    if not isinstance(raw_splits, Mapping) or not raw_splits:
        raise PsluFlightError("knowledge binding lacks query splits")
    query_utterances: set[str] = set()
    query_sentences: set[str] = set()
    for raw_split in raw_splits.values():
        if not isinstance(raw_split, Mapping) or not isinstance(
            raw_split.get("items"), list
        ):
            raise PsluFlightError("knowledge query split is malformed")
        for raw_item in raw_split["items"]:
            if not isinstance(raw_item, Mapping):
                raise PsluFlightError("knowledge query item is malformed")
            utterance_id = raw_item.get("utterance_id")
            normalized_sentence = raw_item.get("normalized_sentence")
            if (
                not isinstance(utterance_id, str)
                or not utterance_id
                or not isinstance(normalized_sentence, str)
                or not normalized_sentence
            ):
                raise PsluFlightError("knowledge query identity is malformed")
            query_utterances.add(utterance_id)
            query_sentences.add(normalized_sentence)
    corpus = tuple(
        entry
        for entry in sorted(
            material, key=lambda item: (item.scenario, item.utterance_id)
        )
        if entry.scenario in cards_by_scenario
        and entry.utterance_id not in query_utterances
        and _normalized_sentence(entry.sentence) not in query_sentences
    )
    if not corpus or {entry.scenario for entry in corpus} != set(scenarios):
        raise PsluFlightError(
            "information-audit corpus lacks the complete query-isolated roster"
        )
    if any(
        any(
            not isinstance(entity_type, str) or not entity_type
            for entity_type in entry.entity_types
        )
        for entry in corpus
    ):
        raise PsluFlightError("information-audit corpus has malformed entity types")

    def entropy(counts: Counter[str]) -> float:
        total = sum(counts.values())
        return (
            -sum(
                (count / total) * math.log2(count / total) for count in counts.values()
            )
            if total
            else 0.0
        )

    scenario_counts = Counter(entry.scenario for entry in corpus)
    scenario_entropy = entropy(scenario_counts)

    def summarize(signatures: Sequence[object]):
        groups: dict[object, Counter[str]] = defaultdict(Counter)
        for entry, signature in zip(corpus, signatures, strict=True):
            groups[signature][entry.scenario] += 1
        conditional = sum(
            sum(counts.values()) / len(corpus) * entropy(counts)
            for counts in groups.values()
        )
        ambiguous = tuple(counts for counts in groups.values() if len(counts) > 1)
        ambiguous_count = sum(sum(counts.values()) for counts in ambiguous)
        return {
            "value_count": len(groups),
            "mutual_information_bits": round(scenario_entropy - conditional, 8),
            "conditional_scenario_entropy_bits": round(conditional, 8),
            "majority_oracle_accuracy": round(
                sum(max(counts.values()) for counts in groups.values()) / len(corpus),
                8,
            ),
            "ambiguous_value_count": len(ambiguous),
            "ambiguous_utterance_count": ambiguous_count,
            "ambiguous_utterance_rate": round(ambiguous_count / len(corpus), 8),
        }, groups

    actions = tuple(entry.action for entry in corpus)
    entities = tuple(tuple(sorted(set(entry.entity_types))) for entry in corpus)
    joint = tuple(zip(actions, entities, strict=True))
    action_layer, action_groups = summarize(actions)
    entity_layer, _ = summarize(entities)
    joint_layer, joint_groups = summarize(joint)

    stable_action_pairs: set[tuple[str, str]] = set()
    for counts in action_groups.values():
        stable = sorted(
            scenario
            for scenario, count in counts.items()
            if count >= _STABLE_SHARED_ACTION_MIN_SUPPORT
        )
        for left_index, left in enumerate(stable):
            stable_action_pairs.update(
                (left, right) for right in stable[left_index + 1 :]
            )

    LexicalRelation = tuple[str, str, str, tuple[str, ...]]
    residual_pairs: set[tuple[str, str]] = set()
    residual_relations: set[LexicalRelation] = set()
    ambiguous_signatures: list[dict[str, object]] = []
    for signature, counts in joint_groups.items():
        if len(counts) <= 1:
            continue
        action, entity_types = signature
        stable = sorted(
            scenario
            for scenario, count in counts.items()
            if count >= _STABLE_SHARED_ACTION_MIN_SUPPORT
        )
        for left_index, left in enumerate(stable):
            for right in stable[left_index + 1 :]:
                residual_pairs.add((left, right))
                residual_relations.add((left, right, action, entity_types))
        ambiguous_signatures.append(
            {
                "action": action,
                "entity_types": list(entity_types),
                "utterance_count": sum(counts.values()),
                "scenario_counts": dict(sorted(counts.items())),
            }
        )
    ambiguous_signatures.sort(
        key=lambda item: (
            -int(item["utterance_count"]),
            str(item["action"]),
            tuple(item["entity_types"]),
        )
    )

    entity_pairs: set[tuple[str, str]] = set()
    lexical_pairs: set[tuple[str, str]] = set()
    lexical_relations: set[LexicalRelation] = set()
    lexical_signal_relations: set[LexicalRelation] = set()
    lexical_cue_signal_relations: set[LexicalRelation] = set()
    semantic_boundary_pairs: set[tuple[str, str]] = set()
    lexical_validation_by_relation: dict[LexicalRelation, dict[str, object]] = {}
    corpus_by_utterance = {entry.utterance_id: entry for entry in corpus}
    if len(corpus_by_utterance) != len(corpus):
        raise PsluFlightError("information-audit corpus has duplicate utterance ids")

    def relation_parts(
        *, left: str, right: str, action: str, entity_id: str
    ) -> LexicalRelation | None:
        if (
            left not in cards_by_scenario
            or right not in cards_by_scenario
            or left == right
        ):
            return None
        pair = (left, right) if left < right else (right, left)
        entities = () if entity_id == "none" else tuple(entity_id.split("+"))
        if not action or any(not entity for entity in entities):
            return None
        return (*pair, action, entities)

    def support_matches(
        relation: LexicalRelation,
        *,
        provenance_left: str,
        provenance_right: str,
        support_text: str,
    ) -> bool:
        if not support_text.startswith("support-"):
            return False
        try:
            left_count, right_count = (
                int(value) for value in support_text.removeprefix("support-").split("-")
            )
        except (TypeError, ValueError):
            return False
        counts = joint_groups.get((relation[2], relation[3]))
        return (
            counts is not None
            and left_count == counts[provenance_left]
            and right_count == counts[provenance_right]
        )

    def entries_for(
        relation: LexicalRelation, scenario: str
    ) -> tuple[SlurpTrainMaterial, ...]:
        return tuple(
            entry
            for entry in corpus
            if entry.scenario == scenario
            and entry.action == relation[2]
            and tuple(sorted(set(entry.entity_types))) == relation[3]
        )

    def validate_lexical_signal(
        relation: LexicalRelation,
        *,
        left_source: SlurpTrainMaterial,
        right_source: SlurpTrainMaterial,
    ) -> dict[str, object]:
        left_entries = entries_for(relation, relation[0])
        right_entries = entries_for(relation, relation[1])

        def heldout_entries(
            entries: Sequence[SlurpTrainMaterial], prototype: SlurpTrainMaterial
        ) -> tuple[SlurpTrainMaterial, ...]:
            prototype_sentence = _normalized_sentence(prototype.sentence)
            return tuple(
                entry
                for entry in entries
                if entry.utterance_id != prototype.utterance_id
                and _normalized_sentence(entry.sentence) != prototype_sentence
            )

        left_heldout = heldout_entries(left_entries, left_source)
        right_heldout = heldout_entries(right_entries, right_source)

        def positive_lift(
            prototype: SlurpTrainMaterial,
            primary: Sequence[SlurpTrainMaterial],
            other: Sequence[SlurpTrainMaterial],
        ) -> float:
            primary_counts: Counter[str] = Counter()
            other_counts: Counter[str] = Counter()
            for entry in primary:
                primary_counts.update(_knowledge_features(entry.sentence))
            for entry in other:
                other_counts.update(_knowledge_features(entry.sentence))
            lifts = sorted(
                (
                    math.log2(
                        ((primary_counts[feature] + 0.5) / (len(primary) + 1.0))
                        / ((other_counts[feature] + 0.5) / (len(other) + 1.0))
                    )
                    for feature in _knowledge_features(prototype.sentence)
                ),
                reverse=True,
            )
            return sum(value for value in lifts[:3] if value > 0.0)

        def similarity(left_entry: SlurpTrainMaterial, right_entry: SlurpTrainMaterial):
            left_features = _knowledge_features(left_entry.sentence)
            right_features = _knowledge_features(right_entry.sentence)
            union = left_features | right_features
            return len(left_features & right_features) / len(union) if union else 0.0

        left_correct = sum(
            similarity(entry, left_source) > similarity(entry, right_source)
            for entry in left_heldout
        )
        right_correct = sum(
            similarity(entry, right_source) > similarity(entry, left_source)
            for entry in right_heldout
        )
        ties = sum(
            similarity(entry, left_source) == similarity(entry, right_source)
            for entry in (*left_heldout, *right_heldout)
        )
        left_lift = positive_lift(left_source, left_heldout, right_entries)
        right_lift = positive_lift(right_source, right_heldout, left_entries)
        left_accuracy = left_correct / len(left_heldout) if left_heldout else 0.0
        right_accuracy = right_correct / len(right_heldout) if right_heldout else 0.0
        bilateral_signal = (
            bool(left_heldout)
            and bool(right_heldout)
            and left_lift > 0.0
            and right_lift > 0.0
        )

        def crossfit_prediction_counts(
            evaluation: Sequence[SlurpTrainMaterial],
            *,
            own_entries: Sequence[SlurpTrainMaterial],
            other_entries: Sequence[SlurpTrainMaterial],
        ) -> tuple[int, int]:
            correct = 0
            ties = 0
            for entry in evaluation:
                heldout_sentence = _normalized_sentence(entry.sentence)
                own_train = tuple(
                    candidate
                    for candidate in own_entries
                    if _normalized_sentence(candidate.sentence) != heldout_sentence
                )
                other_train = tuple(
                    candidate
                    for candidate in other_entries
                    if _normalized_sentence(candidate.sentence) != heldout_sentence
                )
                own_cues = _signature_lexical_cues(own_train, other_train)
                other_cues = _signature_lexical_cues(other_train, own_train)
                features = _knowledge_features(entry.sentence)
                own_score = sum(
                    log_ratio
                    for feature, _count, _other_count, log_ratio in own_cues
                    if feature in features
                )
                other_score = sum(
                    log_ratio
                    for feature, _count, _other_count, log_ratio in other_cues
                    if feature in features
                )
                correct += own_score > other_score
                ties += own_score == other_score
            return correct, ties

        left_cue_correct, left_cue_ties = crossfit_prediction_counts(
            left_entries,
            own_entries=left_entries,
            other_entries=right_entries,
        )
        right_cue_correct, right_cue_ties = crossfit_prediction_counts(
            right_entries,
            own_entries=right_entries,
            other_entries=left_entries,
        )
        left_cue_accuracy = left_cue_correct / len(left_entries)
        right_cue_accuracy = right_cue_correct / len(right_entries)
        crossfit_cue_balanced_accuracy = (left_cue_accuracy + right_cue_accuracy) / 2.0
        return {
            "left_scenario": relation[0],
            "right_scenario": relation[1],
            "action": relation[2],
            "entity_types": list(relation[3]),
            "left_support_count": len(left_entries),
            "right_support_count": len(right_entries),
            "left_prototype_utterance_id": left_source.utterance_id,
            "right_prototype_utterance_id": right_source.utterance_id,
            "left_heldout_count": len(left_heldout),
            "right_heldout_count": len(right_heldout),
            "left_heldout_positive_lift": round(left_lift, 8),
            "right_heldout_positive_lift": round(right_lift, 8),
            "prototype_jaccard_balanced_accuracy": round(
                (left_accuracy + right_accuracy) / 2.0, 8
            ),
            "prototype_jaccard_tie_count": ties,
            "bilateral_heldout_signal": bilateral_signal,
            "crossfit_lexical_cue_balanced_accuracy": round(
                crossfit_cue_balanced_accuracy, 8
            ),
            "crossfit_lexical_cue_correct_count": (
                left_cue_correct + right_cue_correct
            ),
            "crossfit_lexical_cue_tie_count": left_cue_ties + right_cue_ties,
            "crossfit_lexical_cue_signal": crossfit_cue_balanced_accuracy >= 0.5,
        }

    for boundary in graph.boundaries:
        left = scenario_by_key_id[boundary.left_key_id]
        right = scenario_by_key_id[boundary.right_key_id]
        pair = (left, right) if left < right else (right, left)
        if any(
            item.startswith("slurp-train-stable-shared-actions:")
            for item in boundary.provenance_ids
        ):
            entity_pairs.add(pair)
        expected_semantic_supply = _dataset_semantic_boundary_supply(
            corpus,
            left=left,
            right=right,
            left_key_id=boundary.left_key_id,
            right_key_id=boundary.right_key_id,
        )
        if _semantic_boundary_present(boundary, expected_semantic_supply):
            semantic_boundary_pairs.add(pair)
        v4_prototypes: dict[LexicalRelation, dict[str, str]] = defaultdict(dict)
        for item in boundary.provenance_ids:
            if not item.startswith("slurp-train-signature-prototype-v4:"):
                continue
            fields = item.split(":")
            if len(fields) != 7:
                continue
            relation = relation_parts(
                left=fields[1],
                right=fields[2],
                action=fields[3],
                entity_id=fields[4],
            )
            side = fields[5]
            utterance_id = fields[6]
            if (
                relation is None
                or side not in relation[:2]
                or side in v4_prototypes[relation]
            ):
                continue
            v4_prototypes[relation][side] = utterance_id
        for item in boundary.provenance_ids:
            relation: LexicalRelation | None = None
            valid_supply = False
            left_source: SlurpTrainMaterial | None = None
            right_source: SlurpTrainMaterial | None = None
            if item.startswith("slurp-train-signature-lexical:"):
                fields = item.split(":")
                if len(fields) != 7 or not fields[6].startswith("prototypes-"):
                    continue
                relation = relation_parts(
                    left=fields[1],
                    right=fields[2],
                    action=fields[3],
                    entity_id=fields[4],
                )
                relation_left_entries = (
                    entries_for(relation, fields[1]) if relation else ()
                )
                relation_right_entries = (
                    entries_for(relation, fields[2]) if relation else ()
                )
                prototype_payload = fields[6].removeprefix("prototypes-")
                source_matches = [
                    (left_entry, right_entry)
                    for left_entry in relation_left_entries
                    for right_entry in relation_right_entries
                    if (
                        f"{left_entry.utterance_id}-{right_entry.utterance_id}"
                        == prototype_payload
                    )
                ]
                if len(source_matches) == 1:
                    left_source, right_source = source_matches[0]
                valid_supply = (
                    relation is not None
                    and relation[:2] == pair
                    and support_matches(
                        relation,
                        provenance_left=fields[1],
                        provenance_right=fields[2],
                        support_text=fields[5],
                    )
                    and left_source is not None
                    and right_source is not None
                    and right_source.sentence in boundary.left_exclusion
                    and left_source.sentence in boundary.right_exclusion
                )
            elif item.startswith("slurp-train-signature-lexical-v4:"):
                fields = item.split(":")
                if len(fields) != 6:
                    continue
                relation = relation_parts(
                    left=fields[1],
                    right=fields[2],
                    action=fields[3],
                    entity_id=fields[4],
                )
                prototypes = v4_prototypes.get(relation, {}) if relation else {}
                left_source = corpus_by_utterance.get(prototypes.get(fields[1], ""))
                right_source = corpus_by_utterance.get(prototypes.get(fields[2], ""))
                if relation is not None:
                    left_entries = entries_for(relation, fields[1])
                    right_entries = entries_for(relation, fields[2])
                    entity_signature_text = (
                        ", ".join(item.replace("_", " ") for item in relation[3])
                        if relation[3]
                        else "none"
                    )
                    expected_left_cue_supply = _render_signature_lexical_cues(
                        supporting_key_id=boundary.right_key_id,
                        action=relation[2],
                        entity_signature_text=entity_signature_text,
                        cues=_signature_lexical_cues(right_entries, left_entries),
                    )
                    expected_right_cue_supply = _render_signature_lexical_cues(
                        supporting_key_id=boundary.left_key_id,
                        action=relation[2],
                        entity_signature_text=entity_signature_text,
                        cues=_signature_lexical_cues(left_entries, right_entries),
                    )
                else:
                    expected_left_cue_supply = ""
                    expected_right_cue_supply = ""
                valid_supply = (
                    relation is not None
                    and relation[:2] == pair
                    and support_matches(
                        relation,
                        provenance_left=fields[1],
                        provenance_right=fields[2],
                        support_text=fields[5],
                    )
                    and left_source is not None
                    and right_source is not None
                    and (
                        left_source.scenario,
                        left_source.action,
                        tuple(sorted(set(left_source.entity_types))),
                    )
                    == (fields[1], fields[3], relation[3])
                    and (
                        right_source.scenario,
                        right_source.action,
                        tuple(sorted(set(right_source.entity_types))),
                    )
                    == (fields[2], fields[3], relation[3])
                    and right_source.sentence in boundary.left_exclusion
                    and left_source.sentence in boundary.right_exclusion
                    and (
                        not expected_left_cue_supply
                        or expected_left_cue_supply in boundary.left_exclusion
                    )
                    and (
                        not expected_right_cue_supply
                        or expected_right_cue_supply in boundary.right_exclusion
                    )
                )
            if relation is not None and valid_supply:
                lexical_relations.add(relation)
                lexical_pairs.add(pair)
                assert left_source is not None
                assert right_source is not None
                validation = validate_lexical_signal(
                    relation,
                    left_source=left_source,
                    right_source=right_source,
                )
                lexical_validation_by_relation[relation] = validation
                if validation["bilateral_heldout_signal"] is True:
                    lexical_signal_relations.add(relation)
                if validation["crossfit_lexical_cue_signal"] is True:
                    lexical_cue_signal_relations.add(relation)

    raw_revision_keys = revision.get("keys")
    if not isinstance(raw_revision_keys, list):
        raise PsluFlightError("knowledge revision lacks per-key coverage")
    example_coverage: list[dict[str, object]] = []
    incomplete_labels: list[str] = []
    revision_labels: set[str] = set()
    action_facets_complete = True
    for raw_key in raw_revision_keys:
        if not isinstance(raw_key, Mapping):
            raise PsluFlightError("knowledge revision key coverage is malformed")
        label = raw_key.get("value_label")
        key_id = raw_key.get("key_id")
        mass = raw_key.get("covered_action_mass")
        action_counts = raw_key.get("dataset_action_counts")
        missing_actions = raw_key.get("missing_example_actions")
        needed = raw_key.get("examples_needed_for_95pct_action_mass")
        if (
            not isinstance(label, str)
            or label not in cards_by_scenario
            or not isinstance(key_id, str)
            or key_id != cards_by_scenario[label].key_id
            or isinstance(mass, bool)
            or not isinstance(mass, (int, float))
            or not isinstance(action_counts, Mapping)
            or not isinstance(missing_actions, list)
            or not all(isinstance(action, str) for action in missing_actions)
            or isinstance(needed, bool)
            or not isinstance(needed, int)
        ):
            raise PsluFlightError("knowledge revision key coverage is malformed")
        revision_labels.add(label)
        action_facets_complete = action_facets_complete and all(
            isinstance(action, str)
            and (label, action) in SPEECH_NATIVE_ACTION_FACET_DESCRIPTIONS
            for action in action_counts
        )
        meets_minimum = float(mass) >= float(minimum_example_action_mass)
        if not meets_minimum:
            incomplete_labels.append(label)
        example_coverage.append(
            {
                "key_id": key_id,
                "value_label": label,
                "covered_action_mass": round(float(mass), 8),
                "missing_example_actions": sorted(missing_actions),
                "examples_needed_for_95pct_action_mass": needed,
                "meets_minimum": meets_minimum,
            }
        )
    if revision_labels != set(scenarios):
        raise PsluFlightError("knowledge revision does not cover the scenario roster")
    example_coverage.sort(key=lambda item: str(item["key_id"]))

    semantic_boundary_relations = {
        relation
        for relation in residual_relations
        if relation[:2] in semantic_boundary_pairs
        and (relation[2], relation[3])
        in _semantic_boundary_supported_relations(relation[:2])
    }
    discriminative_relations = (
        lexical_cue_signal_relations | semantic_boundary_relations
    )
    checks = {
        "intent_roster_complete": len(cards_by_scenario) == len(scenarios),
        "action_facets_complete": action_facets_complete,
        "positive_example_action_mass": not incomplete_labels,
        "stable_shared_action_entity_supply": stable_action_pairs <= entity_pairs,
        "residual_signature_lexical_supply": residual_relations <= lexical_relations,
        "residual_signature_lexical_heldout_signal": (
            residual_relations <= lexical_signal_relations
        ),
        "residual_signature_discriminative_supply": (
            residual_relations <= discriminative_relations
        ),
    }
    diagnostics = {
        "residual_signature_lexical_crossfit_cue_signal": (
            residual_relations <= lexical_cue_signal_relations
        ),
    }
    failed_checks = sorted(name for name, passed in checks.items() if not passed)
    admission = (
        {
            "status": "blocked",
            "failed_checks": failed_checks,
            "new_model_contact_authorized": False,
            "reason": (
                "The query-isolated train corpus identifies decision-relevant "
                "information that the current knowledge supply does not yet expose."
            ),
        }
        if failed_checks
        else {
            "status": "admitted",
            "failed_checks": [],
            "new_model_contact_authorized": False,
            "reason": (
                "The model-free information gate is complete; a separate execution "
                "plan and exposure registration are still required."
            ),
        }
    )
    without_entities = sum(not signature for signature in entities)
    return {
        "schema": "saea-speech-native-information-audit-v1",
        "source": {
            "binding_sha256": claimed_sha256,
            "knowledge_policy_id": revision.get("policy_id"),
            "decision_graph_id": graph.graph_id,
            "source_split": "SLURP train real speech only",
            "query_isolated": True,
            "query_utterance_count": len(query_utterances),
            "query_isolated_train_utterance_count": len(corpus),
        },
        "label_space": {
            "scenario_count": len(scenarios),
            "scenario_entropy_bits": round(scenario_entropy, 8),
            "scenarios": list(scenarios),
        },
        "information_layers": {
            "action": action_layer,
            "entity_signature": entity_layer,
            "action_plus_entity_signature": joint_layer,
        },
        "residual_ambiguity": {
            "utterances_without_entities": without_entities,
            "utterances_without_entities_rate": round(
                without_entities / len(corpus), 8
            ),
            "stable_shared_action_pair_count": len(stable_action_pairs),
            "residual_signature_pair_count": len(residual_pairs),
            "residual_signature_relation_count": len(residual_relations),
            "top_action_entity_signatures": ambiguous_signatures[:20],
        },
        "knowledge_supply": {
            "intent_roster_count": len(cards_by_scenario),
            "action_facets_complete": action_facets_complete,
            "minimum_positive_example_action_mass": float(minimum_example_action_mass),
            "positive_example_coverage": example_coverage,
            "incomplete_positive_example_labels": sorted(incomplete_labels),
            "entity_boundary_pair_coverage": {
                "covered": len(stable_action_pairs & entity_pairs),
                "required": len(stable_action_pairs),
            },
            "signature_lexical_pair_coverage": {
                "covered": len(residual_pairs & lexical_pairs),
                "required": len(residual_pairs),
            },
            "signature_lexical_relation_coverage": {
                "covered": len(residual_relations & lexical_relations),
                "required": len(residual_relations),
            },
            "signature_lexical_heldout_validation": {
                "validated_relation_count": len(lexical_validation_by_relation),
                "bilateral_signal_relation_count": len(lexical_signal_relations),
                "crossfit_cue_signal_relation_count": len(lexical_cue_signal_relations),
                "required_relation_count": len(residual_relations),
                "relations": [
                    lexical_validation_by_relation[relation]
                    for relation in sorted(lexical_validation_by_relation)
                ],
            },
            "semantic_boundary_relation_coverage": {
                "covered": len(residual_relations & semantic_boundary_relations),
                "registered_pair_count": len(semantic_boundary_pairs),
            },
            "discriminative_relation_coverage": {
                "covered": len(residual_relations & discriminative_relations),
                "required": len(residual_relations),
            },
        },
        "required_task_information": [
            "complete intent roster",
            "intent definition and contrastive boundary",
            "speech-derived operation",
            "speech-derived target or domain",
            "entity type signature when present",
            "pair-specific lexical evidence for residual shared signatures",
        ],
        "agent_loop_information_rule": (
            "A generated semantic state may denoise or reorganize the original "
            "speech observation but does not add label information by itself. A "
            "later retrieval is useful only when it supplies registered train-derived "
            "boundary evidence that was not visible in the preceding call."
        ),
        "checks": checks,
        "diagnostics": diagnostics,
        "admission": admission,
    }


def extend_speech_native_binding(
    base_binding: Mapping[str, object],
    material: Sequence[SlurpTrainMaterial],
    *,
    seed: int,
    split_name: str,
    per_scenario: int,
    expected_scenarios: Sequence[str] = tuple(SPEECH_NATIVE_SCENARIO_DEFINITIONS),
    isolate_parent_query_speakers: bool = True,
) -> dict[str, object]:
    """Add one isolated discovery split without changing frozen key material.

    The successor preserves every existing split and key byte. Candidate
    queries always exclude historical query and key-example speech,
    utterances, and normalized text, plus every key-example speaker. Parent
    query speakers are also excluded by default. A caller may explicitly
    retain only that final overlap after proving a fully speaker-isolated
    extension infeasible; the successor then records the exact overlap count
    and still preserves strict query/key speaker isolation.
    """

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise PsluFlightError("speech-native extension seed must be an integer")
    if (
        not isinstance(split_name, str)
        or not split_name
        or any(
            character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
            for character in split_name
        )
    ):
        raise PsluFlightError(
            "speech-native extension split_name must use uppercase letters, digits, and dashes"
        )
    if (
        isinstance(per_scenario, bool)
        or not isinstance(per_scenario, int)
        or per_scenario <= 0
    ):
        raise PsluFlightError("speech-native extension per_scenario must be positive")
    if not isinstance(isolate_parent_query_speakers, bool):
        raise PsluFlightError(
            "speech-native parent-query speaker isolation flag must be boolean"
        )
    if not isinstance(base_binding, Mapping):
        raise PsluFlightError("speech-native parent binding must be an object")
    parent_sha256 = base_binding.get("binding_sha256")
    parent_unsigned = {
        key: value for key, value in base_binding.items() if key != "binding_sha256"
    }
    if parent_sha256 != _binding_sha256(parent_unsigned):
        raise PsluFlightError("speech-native parent binding self-hash mismatch")
    raw_splits = base_binding.get("splits")
    raw_cards = base_binding.get("key_cards")
    raw_key_material = base_binding.get("key_material")
    if (
        not isinstance(raw_splits, Mapping)
        or split_name in raw_splits
        or not isinstance(raw_cards, list)
        or not isinstance(raw_key_material, list)
    ):
        raise PsluFlightError(
            "speech-native parent binding cannot accept the extension"
        )
    scenarios = tuple(expected_scenarios)
    card_labels = tuple(
        card.get("value_label") if isinstance(card, Mapping) else None
        for card in raw_cards
    )
    if (
        not scenarios
        or len(set(scenarios)) != len(scenarios)
        or card_labels != scenarios
    ):
        raise PsluFlightError(
            "speech-native extension scenarios must match the frozen key-card order"
        )

    forbidden_samples: set[str] = set()
    forbidden_utterances: set[str] = set()
    forbidden_speakers: set[str] = set()
    forbidden_sentences: set[str] = set()
    parent_query_speakers: set[str] = set()

    def exclude(
        item: Mapping[str, object],
        context: str,
        *,
        include_speaker: bool,
    ) -> str:
        fields = {
            "sample_id": forbidden_samples,
            "utterance_id": forbidden_utterances,
            "normalized_sentence": forbidden_sentences,
        }
        for field_name, destination in fields.items():
            value = item.get(field_name)
            if not isinstance(value, str) or not value:
                raise PsluFlightError(f"speech-native {context} lacks {field_name}")
            destination.add(value)
        speaker_id = item.get("speaker_id")
        if not isinstance(speaker_id, str) or not speaker_id:
            raise PsluFlightError(f"speech-native {context} lacks speaker_id")
        if include_speaker:
            forbidden_speakers.add(speaker_id)
        return speaker_id

    for existing_name, split in raw_splits.items():
        items = split.get("items") if isinstance(split, Mapping) else None
        if not isinstance(existing_name, str) or not isinstance(items, list):
            raise PsluFlightError("speech-native parent split is malformed")
        for item in items:
            if not isinstance(item, Mapping):
                raise PsluFlightError("speech-native parent query item is malformed")
            parent_query_speakers.add(
                exclude(
                    item,
                    f"parent split {existing_name!r}",
                    include_speaker=isolate_parent_query_speakers,
                )
            )
    key_samples: set[str] = set()
    key_utterances: set[str] = set()
    key_speakers: set[str] = set()
    key_sentences: set[str] = set()
    for key in raw_key_material:
        sources = key.get("sources") if isinstance(key, Mapping) else None
        if not isinstance(sources, list):
            raise PsluFlightError("speech-native parent key material is malformed")
        for source in sources:
            if not isinstance(source, Mapping):
                raise PsluFlightError("speech-native parent key source is malformed")
            exclude(source, "parent key source", include_speaker=True)
            key_samples.add(str(source["sample_id"]))
            key_utterances.add(str(source["utterance_id"]))
            key_speakers.add(str(source["speaker_id"]))
            key_sentences.add(str(source["normalized_sentence"]))

    by_scenario: dict[str, list[SlurpTrainMaterial]] = {
        scenario: [] for scenario in scenarios
    }
    for entry in material:
        if entry.scenario in by_scenario:
            by_scenario[entry.scenario].append(entry)
    selected_items: list[dict[str, str]] = []
    selected_speakers: set[str] = set()
    for scenario in scenarios:
        candidates = [
            (entry, recording)
            for entry in by_scenario[scenario]
            for recording in entry.recordings
        ]
        candidates.sort(
            key=lambda pair: _binding_rank(
                seed,
                split_name,
                scenario,
                pair[0].utterance_id,
                pair[1].sample_id,
            )
        )
        selected_for_scenario: list[dict[str, str]] = []
        local_utterances: set[str] = set()
        local_sentences: set[str] = set()
        for entry, recording in candidates:
            normalized = _normalized_sentence(entry.sentence)
            if (
                recording.sample_id in forbidden_samples
                or entry.utterance_id in forbidden_utterances
                or recording.speaker_id in forbidden_speakers
                or normalized in forbidden_sentences
                or entry.utterance_id in local_utterances
                or normalized in local_sentences
            ):
                continue
            selected_for_scenario.append(
                {
                    "sample_id": recording.sample_id,
                    "utterance_id": entry.utterance_id,
                    "media_relpath": recording.media_relpath,
                    "speaker_id": recording.speaker_id,
                    "normalized_sentence": normalized,
                    "value_label": scenario,
                }
            )
            selected_speakers.add(recording.speaker_id)
            local_utterances.add(entry.utterance_id)
            local_sentences.add(normalized)
            if len(selected_for_scenario) == per_scenario:
                break
        if len(selected_for_scenario) != per_scenario:
            raise PsluFlightError(
                f"insufficient isolated extension queries for {scenario!r}: needed "
                f"{per_scenario}, found {len(selected_for_scenario)}"
            )
        selected_items.extend(selected_for_scenario)

    ordered = sorted(
        selected_items, key=lambda item: (item["value_label"], item["sample_id"])
    )
    parent_query_speaker_overlap = selected_speakers & parent_query_speakers
    if isolate_parent_query_speakers and parent_query_speaker_overlap:
        raise PsluFlightError(
            "speech-native isolated extension overlaps a parent query speaker"
        )
    identity = {
        "schema": "saea-speech-native-split-v1",
        "name": split_name,
        "seed": seed,
        "sample_ids": [item["sample_id"] for item in ordered],
    }
    successor_unsigned = deepcopy(parent_unsigned)
    successor_splits = deepcopy(dict(raw_splits))
    successor_splits[split_name] = {
        **identity,
        "split_identity_hash": _binding_sha256(identity),
        "items": ordered,
    }
    successor_unsigned.update(
        {
            "status": "MODEL-FREE SUCCESSOR BINDING; NOT AN EXPOSURE REGISTRATION",
            "splits": successor_splits,
            "parent_binding_sha256": parent_sha256,
            "extension_audit": {
                "split_name": split_name,
                "seed": seed,
                "per_scenario": per_scenario,
                "query_count": len(ordered),
                "excluded_parent_query_count": len(forbidden_samples - key_samples),
                "excluded_key_example_count": len(key_samples),
                "parent_query_speaker_isolation": isolate_parent_query_speakers,
                "parent_query_speaker_overlap_count": len(parent_query_speaker_overlap),
            },
            "isolation_audit": {
                "query_sample_count": len(forbidden_samples - key_samples)
                + len(ordered),
                "query_speaker_count": len(parent_query_speakers | selected_speakers),
                "key_example_count": len(key_samples),
                "query_key_sample_overlap": 0,
                "query_key_utterance_overlap": 0,
                "query_key_normalized_sentence_overlap": 0,
                "query_key_speaker_overlap": 0,
                "parent_extension_query_speaker_overlap": len(
                    parent_query_speaker_overlap
                ),
            },
        }
    )
    return {
        **successor_unsigned,
        "binding_sha256": _binding_sha256(successor_unsigned),
    }


@dataclass(frozen=True)
class _SpeechNativeCapacityCandidate:
    scenario: str
    action: str
    entity_types: tuple[str, ...]
    sample: str
    utterance: str
    speaker: str
    normalized_text: str


def audit_speech_native_scale_capacity(
    base_binding: Mapping[str, object],
    material: Sequence[SlurpTrainMaterial],
    *,
    seed: int,
    existing_memory_split_name: str,
    cumulative_query_count: int,
    memory_query_count: int,
    holdout_query_count: int,
    expected_scenarios: Sequence[str] = tuple(SPEECH_NATIVE_SCENARIO_DEFINITIONS),
) -> dict[str, object]:
    """Audit a cumulative memory/holdout ladder without exposing new identities.

    The audit performs a deterministic hypothetical allocation, but emits only
    aggregate counts. It reserves the holdout before allocating new discovery
    memory and keeps every holdout speaker out of both the existing and new
    memory. Study-wide historical-query speaker isolation is evaluated as a
    stricter diagnostic because it can be infeasible after earlier bounded
    discovery flights; it is never silently conflated with the mandatory
    within-stage speaker-grouped holdout.
    """

    integer_values = {
        "seed": seed,
        "cumulative_query_count": cumulative_query_count,
        "memory_query_count": memory_query_count,
        "holdout_query_count": holdout_query_count,
    }
    for name, value in integer_values.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise PsluFlightError(f"speech-native scale {name} must be an integer")
    if seed < 0:
        raise PsluFlightError("speech-native scale seed must be non-negative")
    if any(value <= 0 for name, value in integer_values.items() if name != "seed"):
        raise PsluFlightError("speech-native scale query targets must be positive")
    if cumulative_query_count != memory_query_count + holdout_query_count:
        raise PsluFlightError(
            "speech-native cumulative query count must equal memory plus holdout"
        )
    if (
        not isinstance(existing_memory_split_name, str)
        or not existing_memory_split_name
    ):
        raise PsluFlightError(
            "speech-native existing memory split name must be non-empty"
        )
    if not isinstance(base_binding, Mapping):
        raise PsluFlightError("speech-native scale parent binding must be an object")
    claimed_sha256 = base_binding.get("binding_sha256")
    unsigned = {
        key: value for key, value in base_binding.items() if key != "binding_sha256"
    }
    if claimed_sha256 != _binding_sha256(unsigned):
        raise PsluFlightError("speech-native scale parent binding self-hash mismatch")

    scenarios = tuple(expected_scenarios)
    raw_cards = base_binding.get("key_cards")
    raw_splits = base_binding.get("splits")
    raw_keys = base_binding.get("key_material")
    if (
        not scenarios
        or len(set(scenarios)) != len(scenarios)
        or not isinstance(raw_cards, list)
        or not isinstance(raw_splits, Mapping)
        or not isinstance(raw_keys, list)
    ):
        raise PsluFlightError("speech-native scale binding roster is malformed")
    card_labels = tuple(
        card.get("value_label") if isinstance(card, Mapping) else None
        for card in raw_cards
    )
    if card_labels != scenarios:
        raise PsluFlightError(
            "speech-native scale scenarios must match the frozen key-card order"
        )
    memory_split = raw_splits.get(existing_memory_split_name)
    memory_items = (
        memory_split.get("items") if isinstance(memory_split, Mapping) else None
    )
    if not isinstance(memory_items, list) or not memory_items:
        raise PsluFlightError(
            "speech-native existing memory split is missing or malformed"
        )
    if len(memory_items) >= memory_query_count:
        raise PsluFlightError(
            "speech-native memory target must exceed the existing memory split"
        )

    def required_text(item: Mapping[str, object], field_name: str, context: str) -> str:
        value = item.get(field_name)
        if not isinstance(value, str) or not value:
            raise PsluFlightError(f"speech-native {context} lacks {field_name}")
        return value

    registered_samples: set[str] = set()
    registered_utterances: set[str] = set()
    registered_speakers: set[str] = set()
    registered_texts: set[str] = set()
    for split_name, split in raw_splits.items():
        items = split.get("items") if isinstance(split, Mapping) else None
        if not isinstance(split_name, str) or not isinstance(items, list):
            raise PsluFlightError("speech-native scale query split is malformed")
        for item in items:
            if not isinstance(item, Mapping):
                raise PsluFlightError("speech-native scale query item is malformed")
            registered_samples.add(required_text(item, "sample_id", "query item"))
            registered_utterances.add(required_text(item, "utterance_id", "query item"))
            registered_speakers.add(required_text(item, "speaker_id", "query item"))
            registered_texts.add(
                required_text(item, "normalized_sentence", "query item")
            )

    key_samples: set[str] = set()
    key_utterances: set[str] = set()
    key_speakers: set[str] = set()
    key_texts: set[str] = set()
    for key in raw_keys:
        sources = key.get("sources") if isinstance(key, Mapping) else None
        if not isinstance(sources, list):
            raise PsluFlightError("speech-native scale key material is malformed")
        for source in sources:
            if not isinstance(source, Mapping):
                raise PsluFlightError("speech-native scale key source is malformed")
            key_samples.add(required_text(source, "sample_id", "key source"))
            key_utterances.add(required_text(source, "utterance_id", "key source"))
            key_speakers.add(required_text(source, "speaker_id", "key source"))
            key_texts.add(required_text(source, "normalized_sentence", "key source"))

    material_by_utterance: dict[str, SlurpTrainMaterial] = {}
    for entry in material:
        if entry.utterance_id in material_by_utterance:
            raise PsluFlightError("speech-native scale material repeats an utterance")
        if (
            not entry.utterance_id
            or not entry.scenario
            or not entry.action
            or not entry.sentence
            or any(not entity_type for entity_type in entry.entity_types)
        ):
            raise PsluFlightError("speech-native scale material is malformed")
        material_by_utterance[entry.utterance_id] = entry

    def observation_from_item(item: object) -> dict[str, object]:
        if not isinstance(item, Mapping):
            raise PsluFlightError("speech-native scale memory item is malformed")
        utterance = required_text(item, "utterance_id", "memory item")
        scenario = required_text(item, "value_label", "memory item")
        speaker = required_text(item, "speaker_id", "memory item")
        sample = required_text(item, "sample_id", "memory item")
        normalized = required_text(item, "normalized_sentence", "memory item")
        entry = material_by_utterance.get(utterance)
        if (
            entry is None
            or entry.scenario != scenario
            or _normalized_sentence(entry.sentence) != normalized
            or not any(
                recording.sample_id == sample and recording.speaker_id == speaker
                for recording in entry.recordings
            )
        ):
            raise PsluFlightError(
                "speech-native existing memory item does not match train material"
            )
        return {
            "scenario": scenario,
            "action": entry.action,
            "entity_types": tuple(sorted(set(entry.entity_types))),
            "speaker": speaker,
        }

    existing_observations = tuple(observation_from_item(item) for item in memory_items)
    existing_memory_speakers = {
        str(observation["speaker"]) for observation in existing_observations
    }

    candidates: list[_SpeechNativeCapacityCandidate] = []
    for entry in material:
        normalized = _normalized_sentence(entry.sentence)
        if (
            entry.scenario not in scenarios
            or entry.utterance_id in registered_utterances
            or normalized in registered_texts
            or entry.utterance_id in key_utterances
            or normalized in key_texts
        ):
            continue
        entities = tuple(sorted(set(entry.entity_types)))
        for recording in entry.recordings:
            if (
                recording.sample_id in registered_samples
                or recording.sample_id in key_samples
                or recording.speaker_id in key_speakers
            ):
                continue
            candidates.append(
                _SpeechNativeCapacityCandidate(
                    scenario=entry.scenario,
                    action=entry.action,
                    entity_types=entities,
                    sample=recording.sample_id,
                    utterance=entry.utterance_id,
                    speaker=recording.speaker_id,
                    normalized_text=normalized,
                )
            )

    def balanced_quotas(total: int, purpose: str) -> dict[str, int]:
        base, remainder = divmod(total, len(scenarios))
        bonus = set(
            sorted(
                scenarios,
                key=lambda scenario: _binding_rank(seed, purpose, scenario),
            )[:remainder]
        )
        return {scenario: base + int(scenario in bonus) for scenario in scenarios}

    holdout_quotas = balanced_quotas(holdout_query_count, "scale-holdout-quota")
    new_memory_count = memory_query_count - len(memory_items)
    new_memory_quotas = balanced_quotas(new_memory_count, "scale-memory-quota")

    shared_signature_scenarios: dict[tuple[str, tuple[str, ...]], set[str]] = (
        defaultdict(set)
    )
    for candidate in candidates:
        shared_signature_scenarios[(candidate.action, candidate.entity_types)].add(
            candidate.scenario
        )
    shared_signatures = {
        signature
        for signature, labels in shared_signature_scenarios.items()
        if len(labels) > 1
    }
    unique_candidate_utterances = {
        (
            candidate.utterance,
            candidate.scenario,
            candidate.action,
            candidate.entity_types,
        )
        for candidate in candidates
    }
    action_scenario_counts: dict[str, Counter[str]] = defaultdict(Counter)
    signature_scenario_counts: dict[tuple[str, tuple[str, ...]], Counter[str]] = (
        defaultdict(Counter)
    )
    for _utterance, scenario, action, entity_types in unique_candidate_utterances:
        action_scenario_counts[action][scenario] += 1
        signature_scenario_counts[(action, entity_types)][scenario] += 1

    stable_action_pairs: set[tuple[str, str, str]] = set()
    for action, counts in action_scenario_counts.items():
        stable_scenarios = sorted(
            scenario
            for scenario, count in counts.items()
            if count >= _STABLE_SHARED_ACTION_MIN_SUPPORT
        )
        for left_index, left in enumerate(stable_scenarios):
            stable_action_pairs.update(
                (left, right, action) for right in stable_scenarios[left_index + 1 :]
            )
    residual_signature_pairs: set[tuple[str, str, str, tuple[str, ...]]] = set()
    for (action, entity_types), counts in signature_scenario_counts.items():
        stable_scenarios = sorted(
            scenario
            for scenario, count in counts.items()
            if count >= _STABLE_SHARED_ACTION_MIN_SUPPORT
        )
        for left_index, left in enumerate(stable_scenarios):
            residual_signature_pairs.update(
                (left, right, action, entity_types)
                for right in stable_scenarios[left_index + 1 :]
            )
    stable_action_sides = {
        (scenario, action)
        for left, right, action in stable_action_pairs
        for scenario in (left, right)
    }
    residual_signature_sides = {
        (scenario, action, entity_types)
        for left, right, action, entity_types in residual_signature_pairs
        for scenario in (left, right)
    }

    def select(
        pool: Sequence[_SpeechNativeCapacityCandidate],
        quotas: Mapping[str, int],
        purpose: str,
        *,
        forbidden_speakers: set[str],
        initial_observations: Sequence[Mapping[str, object]] = (),
        information_balanced: bool = False,
        speaker_balanced: bool = False,
        residual_pair_balanced: bool = False,
    ) -> tuple[_SpeechNativeCapacityCandidate, ...]:
        selected: list[_SpeechNativeCapacityCandidate] = []
        used_samples: set[str] = set()
        used_utterances: set[str] = set()
        used_texts: set[str] = set()
        used_speakers: set[str] = set()
        seen_scenario_signatures = {
            (
                str(item["scenario"]),
                str(item["action"]),
                tuple(item["entity_types"]),
            )
            for item in initial_observations
        }
        seen_scenario_signature_counts = Counter(
            (
                str(item["scenario"]),
                str(item["action"]),
                tuple(item["entity_types"]),
            )
            for item in initial_observations
        )

        def residual_completion_gain(
            candidate: _SpeechNativeCapacityCandidate,
        ) -> int:
            side = (
                candidate.scenario,
                candidate.action,
                candidate.entity_types,
            )
            if side in seen_scenario_signatures:
                return 0
            return sum(
                (
                    left == candidate.scenario
                    and action == candidate.action
                    and entity_types == candidate.entity_types
                    and (right, action, entity_types) in seen_scenario_signatures
                )
                or (
                    right == candidate.scenario
                    and action == candidate.action
                    and entity_types == candidate.entity_types
                    and (left, action, entity_types) in seen_scenario_signatures
                )
                for left, right, action, entity_types in residual_signature_pairs
            )

        def residual_minimum_support_gain(
            candidate: _SpeechNativeCapacityCandidate,
        ) -> int:
            gain = 0
            for left, right, action, entity_types in residual_signature_pairs:
                if (
                    action != candidate.action
                    or entity_types != candidate.entity_types
                    or candidate.scenario not in (left, right)
                ):
                    continue
                left_count = seen_scenario_signature_counts[
                    (left, action, entity_types)
                ]
                right_count = seen_scenario_signature_counts[
                    (right, action, entity_types)
                ]
                before = min(left_count, right_count)
                if candidate.scenario == left:
                    left_count += 1
                else:
                    right_count += 1
                after = min(left_count, right_count)
                gain += int(before < 5 and after > before)
            return gain

        for scenario in scenarios:
            available = [
                candidate
                for candidate in pool
                if candidate.scenario == scenario
                and candidate.speaker not in forbidden_speakers
            ]
            seen_actions = {
                str(item["action"])
                for item in initial_observations
                if item["scenario"] == scenario
            }
            seen_signatures = {
                (str(item["action"]), tuple(item["entity_types"]))
                for item in initial_observations
                if item["scenario"] == scenario
            }
            count = 0
            while count < quotas[scenario]:
                remaining = [
                    candidate
                    for candidate in available
                    if candidate.sample not in used_samples
                    and candidate.utterance not in used_utterances
                    and candidate.normalized_text not in used_texts
                ]
                if not remaining:
                    break
                candidate = min(
                    remaining,
                    key=lambda item: (
                        int(speaker_balanced and item.speaker in used_speakers),
                        int(information_balanced and item.action in seen_actions),
                        -(
                            residual_completion_gain(item)
                            if residual_pair_balanced
                            else 0
                        ),
                        int(
                            residual_pair_balanced
                            and (
                                item.scenario,
                                item.action,
                                item.entity_types,
                            )
                            not in residual_signature_sides
                        ),
                        int(
                            residual_pair_balanced
                            and (
                                item.scenario,
                                item.action,
                                item.entity_types,
                            )
                            in seen_scenario_signatures
                        ),
                        -(
                            residual_minimum_support_gain(item)
                            if residual_pair_balanced
                            else 0
                        ),
                        int(
                            information_balanced
                            and (item.action, item.entity_types) in seen_signatures
                        ),
                        _binding_rank(
                            seed,
                            purpose,
                            scenario,
                            item.action,
                            "+".join(item.entity_types),
                            item.utterance,
                            item.sample,
                        ),
                    ),
                )
                selected.append(candidate)
                used_samples.add(candidate.sample)
                used_utterances.add(candidate.utterance)
                used_texts.add(candidate.normalized_text)
                used_speakers.add(candidate.speaker)
                seen_actions.add(candidate.action)
                seen_signatures.add((candidate.action, candidate.entity_types))
                seen_scenario_signatures.add(
                    (candidate.scenario, candidate.action, candidate.entity_types)
                )
                seen_scenario_signature_counts[
                    (candidate.scenario, candidate.action, candidate.entity_types)
                ] += 1
                count += 1
        return tuple(selected)

    strict_holdout = select(
        candidates,
        holdout_quotas,
        "scale-strict-study-holdout",
        forbidden_speakers=registered_speakers,
        speaker_balanced=True,
    )
    stage_holdout = select(
        candidates,
        holdout_quotas,
        "scale-stage-holdout",
        forbidden_speakers=existing_memory_speakers,
        speaker_balanced=True,
    )
    holdout = (
        strict_holdout if len(strict_holdout) == holdout_query_count else stage_holdout
    )
    holdout_speakers = {candidate.speaker for candidate in holdout}
    holdout_samples = {candidate.sample for candidate in holdout}
    holdout_utterances = {candidate.utterance for candidate in holdout}
    holdout_texts = {candidate.normalized_text for candidate in holdout}
    memory_pool = tuple(
        candidate
        for candidate in candidates
        if candidate.sample not in holdout_samples
        and candidate.utterance not in holdout_utterances
        and candidate.normalized_text not in holdout_texts
    )
    new_memory = select(
        memory_pool,
        new_memory_quotas,
        "scale-new-memory",
        forbidden_speakers=holdout_speakers,
        initial_observations=existing_observations,
        information_balanced=True,
        residual_pair_balanced=True,
    )

    def candidate_observation(
        candidate: _SpeechNativeCapacityCandidate,
    ) -> dict[str, object]:
        return {
            "scenario": candidate.scenario,
            "action": candidate.action,
            "entity_types": candidate.entity_types,
            "speaker": candidate.speaker,
        }

    def summarize(observations: Sequence[Mapping[str, object]]) -> dict[str, object]:
        actions = {str(item["action"]) for item in observations}
        signatures = {
            (str(item["action"]), tuple(item["entity_types"])) for item in observations
        }
        per_scenario: dict[str, object] = {}
        for scenario in scenarios:
            subset = [item for item in observations if item["scenario"] == scenario]
            per_scenario[scenario] = {
                "query_count": len(subset),
                "action_count": len({str(item["action"]) for item in subset}),
                "action_entity_signature_count": len(
                    {
                        (str(item["action"]), tuple(item["entity_types"]))
                        for item in subset
                    }
                ),
            }
        no_entities = sum(not tuple(item["entity_types"]) for item in observations)
        observed_scenario_actions = {
            (str(item["scenario"]), str(item["action"])) for item in observations
        }
        observed_scenario_signatures = {
            (
                str(item["scenario"]),
                str(item["action"]),
                tuple(item["entity_types"]),
            )
            for item in observations
        }
        scenario_action_counts = Counter(
            (str(item["scenario"]), str(item["action"])) for item in observations
        )
        scenario_signature_counts = Counter(
            (
                str(item["scenario"]),
                str(item["action"]),
                tuple(item["entity_types"]),
            )
            for item in observations
        )
        stable_pair_support = tuple(
            min(
                scenario_action_counts[(left, action)],
                scenario_action_counts[(right, action)],
            )
            for left, right, action in stable_action_pairs
        )
        residual_pair_support = tuple(
            min(
                scenario_signature_counts[(left, action, entity_types)],
                scenario_signature_counts[(right, action, entity_types)],
            )
            for left, right, action, entity_types in residual_signature_pairs
        )

        def support_summary(values: Sequence[int]) -> dict[str, int]:
            return {
                "minimum": min(values) if values else 0,
                "pairs_at_least_2": sum(value >= 2 for value in values),
                "pairs_at_least_3": sum(value >= 3 for value in values),
                "pairs_at_least_5": sum(value >= 5 for value in values),
                "required": len(values),
            }

        stable_bilateral = sum(
            (left, action) in observed_scenario_actions
            and (right, action) in observed_scenario_actions
            for left, right, action in stable_action_pairs
        )
        residual_bilateral = sum(
            (left, action, entity_types) in observed_scenario_signatures
            and (right, action, entity_types) in observed_scenario_signatures
            for left, right, action, entity_types in residual_signature_pairs
        )
        return {
            "query_count": len(observations),
            "speaker_count": len({str(item["speaker"]) for item in observations}),
            "scenario_count": len({str(item["scenario"]) for item in observations}),
            "action_count": len(actions),
            "action_entity_signature_count": len(signatures),
            "shared_action_entity_query_count": sum(
                (str(item["action"]), tuple(item["entity_types"])) in shared_signatures
                for item in observations
            ),
            "stable_shared_action_query_count": sum(
                (str(item["scenario"]), str(item["action"])) in stable_action_sides
                for item in observations
            ),
            "residual_shared_signature_query_count": sum(
                (
                    str(item["scenario"]),
                    str(item["action"]),
                    tuple(item["entity_types"]),
                )
                in residual_signature_sides
                for item in observations
            ),
            "entity_free_stable_action_query_count": sum(
                not tuple(item["entity_types"])
                and (str(item["scenario"]), str(item["action"])) in stable_action_sides
                for item in observations
            ),
            "stable_action_pair_bilateral_coverage": {
                "covered": stable_bilateral,
                "required": len(stable_action_pairs),
            },
            "residual_signature_pair_bilateral_coverage": {
                "covered": residual_bilateral,
                "required": len(residual_signature_pairs),
            },
            "stable_action_pair_minimum_side_support": support_summary(
                stable_pair_support
            ),
            "residual_signature_pair_minimum_side_support": support_summary(
                residual_pair_support
            ),
            "without_entities_count": no_entities,
            "without_entities_rate": (
                round(no_entities / len(observations), 8) if observations else 0.0
            ),
            "per_scenario": per_scenario,
        }

    holdout_observations = tuple(candidate_observation(item) for item in holdout)
    new_memory_observations = tuple(candidate_observation(item) for item in new_memory)
    cumulative_memory_observations = existing_observations + new_memory_observations
    candidate_observations = tuple(candidate_observation(item) for item in candidates)
    available_actions = {candidate.action for candidate in candidates}
    cumulative_memory_actions = {
        str(item["action"]) for item in cumulative_memory_observations
    }
    available_scenario_actions = {
        (candidate.scenario, candidate.action) for candidate in candidates
    }
    cumulative_memory_scenario_actions = {
        (str(item["scenario"]), str(item["action"]))
        for item in cumulative_memory_observations
    }
    existing_memory_summary = summarize(existing_observations)
    new_memory_summary = summarize(new_memory_observations)
    cumulative_memory_summary = summarize(cumulative_memory_observations)
    holdout_summary = summarize(holdout_observations)
    available_pool_summary = summarize(candidate_observations)
    cumulative_stable_coverage = cumulative_memory_summary[
        "stable_action_pair_bilateral_coverage"
    ]
    cumulative_residual_coverage = cumulative_memory_summary[
        "residual_signature_pair_bilateral_coverage"
    ]

    new_memory_speakers = {candidate.speaker for candidate in new_memory}
    memory_speakers = existing_memory_speakers | new_memory_speakers
    query_key_speaker_overlap = (
        memory_speakers & key_speakers | holdout_speakers & key_speakers
    )
    stage_identity_overlap_count = len(
        (holdout_samples & {candidate.sample for candidate in new_memory})
        | (holdout_utterances & {candidate.utterance for candidate in new_memory})
        | (holdout_texts & {candidate.normalized_text for candidate in new_memory})
    )
    checks = {
        "holdout_capacity": len(holdout) == holdout_query_count,
        "new_memory_capacity": len(new_memory) == new_memory_count,
        "memory_holdout_speaker_disjoint": not (memory_speakers & holdout_speakers),
        "query_key_speaker_disjoint": not query_key_speaker_overlap,
        "stage_identity_disjoint": stage_identity_overlap_count == 0,
        "cumulative_memory_action_complete": (
            cumulative_memory_actions == available_actions
        ),
        "cumulative_memory_scenario_action_complete": (
            cumulative_memory_scenario_actions == available_scenario_actions
        ),
        "cumulative_memory_stable_action_pair_complete": (
            isinstance(cumulative_stable_coverage, Mapping)
            and cumulative_stable_coverage.get("covered")
            == cumulative_stable_coverage.get("required")
        ),
        "cumulative_memory_residual_signature_pair_complete": (
            isinstance(cumulative_residual_coverage, Mapping)
            and cumulative_residual_coverage.get("covered")
            == cumulative_residual_coverage.get("required")
        ),
        "complete_scenario_roster": (
            len(holdout) == holdout_query_count
            and len(new_memory) == new_memory_count
            and {item.scenario for item in holdout} == set(scenarios)
            and {item.scenario for item in new_memory} == set(scenarios)
        ),
    }
    failed_checks = sorted(name for name, passed in checks.items() if not passed)
    status = "feasible" if not failed_checks else "blocked"

    return {
        "schema": "saea-speech-native-scale-capacity-audit-v1",
        "status": "MODEL-FREE AGGREGATE AUDIT; NOT AN EXPOSURE REGISTRATION",
        "source": {
            "binding_sha256": claimed_sha256,
            "split": "SLURP train real speech only",
            "seed": seed,
            "existing_memory_split": existing_memory_split_name,
            "registered_query_count": len(registered_samples),
            "registered_query_speaker_count": len(registered_speakers),
            "key_example_count": len(key_samples),
            "key_speaker_count": len(key_speakers),
            "new_identity_fields_emitted": False,
        },
        "targets": {
            "cumulative_query_count": cumulative_query_count,
            "memory_query_count": memory_query_count,
            "existing_memory_query_count": len(memory_items),
            "new_memory_query_count": new_memory_count,
            "holdout_query_count": holdout_query_count,
        },
        "query_isolated_capacity": {
            "recording_count": len(candidates),
            "utterance_count": len({candidate.utterance for candidate in candidates}),
            "speaker_count": len({candidate.speaker for candidate in candidates}),
            "scenario_count": len({candidate.scenario for candidate in candidates}),
            "action_count": len({candidate.action for candidate in candidates}),
            "action_entity_signature_count": len(shared_signature_scenarios),
            "shared_action_entity_signature_count": len(shared_signatures),
        },
        "agentloop_actionability": {
            "minimum_bilateral_train_support": _STABLE_SHARED_ACTION_MIN_SUPPORT,
            "stable_action_pair_count": len(stable_action_pairs),
            "stable_boundary_scenario_pair_count": len(
                {(left, right) for left, right, _action in stable_action_pairs}
            ),
            "residual_signature_pair_count": len(residual_signature_pairs),
            "residual_boundary_scenario_pair_count": len(
                {
                    (left, right)
                    for left, right, _action, _entity_types in residual_signature_pairs
                }
            ),
            "interpretation": (
                "Stable shared actions expose a candidate boundary action. Exact "
                "shared action-plus-entity signatures mark residual cases where "
                "entity extraction alone cannot resolve the label."
            ),
        },
        "allocation_policy": {
            "id": "speaker-unseen-holdout-residual-support-memory-v4",
            "holdout_reserved_before_new_memory": True,
            "study_wide_speaker_unseen_holdout_preferred": True,
            "holdout_prioritizes_unseen_speakers": True,
            "new_memory_prioritizes_unseen_action_then_signature": True,
            "new_memory_prioritizes_residual_pair_completion": True,
            "new_memory_prioritizes_residual_pair_minimum_support": True,
            "holdout_quota_by_scenario": holdout_quotas,
            "new_memory_quota_by_scenario": new_memory_quotas,
        },
        "allocations": {
            "existing_memory": existing_memory_summary,
            "new_memory": new_memory_summary,
            "cumulative_memory": cumulative_memory_summary,
            "holdout": holdout_summary,
            "available_pool": available_pool_summary,
        },
        "isolation": {
            "memory_holdout_speaker_overlap_count": len(
                memory_speakers & holdout_speakers
            ),
            "query_key_speaker_overlap_count": len(query_key_speaker_overlap),
            "stage_identity_overlap_count": stage_identity_overlap_count,
            "holdout_historical_nonmemory_speaker_overlap_count": len(
                (holdout_speakers & registered_speakers) - existing_memory_speakers
            ),
        },
        "study_wide_speaker_unseen_holdout": {
            "feasible": len(strict_holdout) == holdout_query_count,
            "allocated_query_count": len(strict_holdout),
            "target_query_count": holdout_query_count,
            "interpretation": (
                "The holdout can be speaker-unseen relative to every registered query."
                if len(strict_holdout) == holdout_query_count
                else "The holdout cannot be claimed speaker-unseen relative to every "
                "historical query; only the within-stage grouped claim is admissible."
            ),
        },
        "information_interpretation": {
            "rule": (
                "The memory adds decision evidence only through train-derived key and "
                "boundary information. Generated loop state may denoise speech but is "
                "not counted as new label information."
            ),
            "cumulative_memory_action_coverage_rate": round(
                len(cumulative_memory_actions) / len(available_actions),
                8,
            )
            if candidates
            else 0.0,
            "cumulative_memory_scenario_action_coverage_rate": round(
                len(cumulative_memory_scenario_actions)
                / len(available_scenario_actions),
                8,
            )
            if candidates
            else 0.0,
            "cumulative_memory_shared_signature_query_count": (
                cumulative_memory_summary["shared_action_entity_query_count"]
            ),
            "holdout_shared_signature_query_count": holdout_summary[
                "shared_action_entity_query_count"
            ],
        },
        "checks": checks,
        "admission": {
            "status": status,
            "failed_checks": failed_checks,
            "new_model_contact_authorized": False,
            "reason": (
                "The aggregate train-only ladder is feasible; exact identities remain "
                "unfrozen and require a later owner-approved registration."
                if status == "feasible"
                else "The aggregate train-only ladder is infeasible under the "
                "mandatory within-stage isolation constraints."
            ),
        },
    }


# ---------------------------------------------------------------------------
# The ontology-miner call guard (module docstring).
# ---------------------------------------------------------------------------


def _source_references_ontology_miner(source: str) -> bool:
    """AST-based (never a plain substring search: this module's OWN
    docstrings legitimately name ``load_slurp_ontology`` in prose, which a
    substring search could not tell apart from a live import/call). True iff
    ``source`` contains an ``import ... load_slurp_ontology``, a bare
    ``load_slurp_ontology`` name reference (covers both a direct call and
    passing the function as a value), or a ``<module>.load_slurp_ontology``
    attribute access."""

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(
            alias.name == _FORBIDDEN_ONTOLOGY_SYMBOL for alias in node.names
        ):
            return True
        if isinstance(node, ast.Name) and node.id == _FORBIDDEN_ONTOLOGY_SYMBOL:
            return True
        if isinstance(node, ast.Attribute) and node.attr == _FORBIDDEN_ONTOLOGY_SYMBOL:
            return True
    return False


def assert_never_calls_ontology_miner(source: str | None = None) -> None:
    """Static, executed guard (bridge mission instruction: "assert at load
    time that load_slurp_ontology is NOT called on this path"). ``source``
    is this module's OWN source text by default (``Path(__file__)``); a
    caller (a test) may pass a synthetic snippet instead. Runs
    automatically at IMPORT time (module-level call at the bottom of this
    file) and again, explicitly, at the top of :func:`run_pslu_flight` --
    so a future edit that adds the forbidden import/call fails LOUD the
    moment this module is next imported, not silently at flight time."""

    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    if _source_references_ontology_miner(text):
        raise PsluFlightError(
            f"rails.probes.pslu_flight source references "
            f"{_FORBIDDEN_ONTOLOGY_SYMBOL!r}; this flight is REGISTERED to consume "
            "rosters ONLY from configs/probes/g0-binding/pslu-rosters-train-only.json "
            "(load_pslu_rosters) -- the shipped ontology miner is ceiling-tier for a "
            "devel-split probe (data.slurp.load_slurp_ontology's own docstring: 64.8% "
            "verbatim train_synthetic overlap with devel)"
        )


# ---------------------------------------------------------------------------
# Roster table (configs/probes/g0-binding/pslu-rosters-train-only.json)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PsluRosters:
    """The four roster shapes the binding table's ``arms`` block carries --
    one per non-A0 arm family. ``scenario_rosters`` backs BOTH A1 (gold
    scenario key) and A1' (predicted scenario key); A4 also reads it, keyed
    by its own derangement partner."""

    scenario_rosters: Mapping[str, tuple[tuple[str, str], ...]]
    global_types: tuple[str, ...]
    full_roster: tuple[tuple[str, str], ...]
    derangement: Mapping[str, str]


def load_pslu_rosters(path: Path) -> PsluRosters:
    """Load and validate ``pslu-rosters-train-only.json`` -- checks, at load
    time, that the table declares ``probe == "P-SLU"``,
    ``legality_tier == "legal"``, and
    ``train_synthetic_refused.train_jsonl_overlap_with_devel == 0`` (the
    table's own recorded proof that its rosters are train-split-only and
    zero-overlap with the devel evaluation surface) before trusting any
    roster it carries."""

    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("probe") != _PROBE_ID:
        raise PsluFlightError(
            f"{path}: probe must be {_PROBE_ID!r}, got {document.get('probe')!r}"
        )
    if document.get("legality_tier") != _LEGAL_TIER:
        raise PsluFlightError(
            f"{path}: legality_tier must be {_LEGAL_TIER!r}, got {document.get('legality_tier')!r}"
        )
    refused = document.get("train_synthetic_refused")
    if (
        not isinstance(refused, Mapping)
        or refused.get("train_jsonl_overlap_with_devel") != 0
    ):
        raise PsluFlightError(
            f"{path}: train_synthetic_refused.train_jsonl_overlap_with_devel must be 0"
        )
    try:
        arms = document["arms"]
        scenario_rosters = {
            scenario: tuple((str(t), str(v)) for t, v in entries)
            for scenario, entries in arms["A1_scenario_roster"]["rosters"].items()
        }
        global_types = tuple(str(t) for t in arms["A2_global_type_vocabulary"]["types"])
        full_roster = tuple(
            (str(t), str(v)) for t, v in arms["A3_full_ontology_dose_capped"]["roster"]
        )
        derangement = {
            str(k): str(v) for k, v in arms["A4_deranged"]["mapping"].items()
        }
    except (KeyError, TypeError, ValueError) as error:
        raise PsluFlightError(f"{path}: malformed roster table: {error}") from error
    if not scenario_rosters or not global_types or not full_roster or not derangement:
        raise PsluFlightError(f"{path}: one or more roster sections resolved empty")
    return PsluRosters(
        scenario_rosters=scenario_rosters,
        global_types=global_types,
        full_roster=full_roster,
        derangement=derangement,
    )


@dataclass(frozen=True)
class PsluSampleManifest:
    """The frozen n=60 sample set (``configs/probes/g0-binding/pslu-sample-
    devel-n60.json``) -- the ORDERED ``sample_id`` list a real flight must
    run, not "whatever ``SlurpAdapter.load_split('devel')`` happens to
    return" (that call resolves the FULL ~2000-item devel split; the
    preregistered probe scope is exactly this frozen 60)."""

    sample_ids: tuple[str, ...]
    split_identity_hash: str
    seed: int


def load_pslu_sample_manifest(path: Path) -> PsluSampleManifest:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("probe") != _PROBE_ID:
        raise PsluFlightError(
            f"{path}: probe must be {_PROBE_ID!r}, got {document.get('probe')!r}"
        )
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise PsluFlightError(f"{path}: no items")
    try:
        sample_ids = tuple(str(item["sample_id"]) for item in items)
    except (KeyError, TypeError) as error:
        raise PsluFlightError(f"{path}: malformed items: {error}") from error
    split_identity_hash = document.get("split_identity_hash")
    if not isinstance(split_identity_hash, str) or len(split_identity_hash) != 64:
        raise PsluFlightError(f"{path}: split_identity_hash must be a 64-hex sha256")
    seed = document.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise PsluFlightError(f"{path}: seed must be an integer")
    if len(set(sample_ids)) != len(sample_ids):
        raise PsluFlightError(f"{path}: duplicate sample_id in items")
    return PsluSampleManifest(
        sample_ids=sample_ids, split_identity_hash=split_identity_hash, seed=seed
    )


def select_pslu_samples(
    all_samples: Sequence[SlurpSample], manifest: PsluSampleManifest
) -> tuple[SlurpSample, ...]:
    """Filter+order ``all_samples`` (e.g. every ``SlurpAdapter.
    load_split("devel")`` result) down to EXACTLY ``manifest.sample_ids``,
    in that frozen order -- fail-closed if any id is missing: the probe's
    n=60 sample set is frozen pre-registration, so a run must never
    silently resolve to fewer samples than registered."""

    by_id = {sample.sample_id: sample for sample in all_samples}
    missing = [sample_id for sample_id in manifest.sample_ids if sample_id not in by_id]
    if missing:
        raise PsluFlightError(
            f"sample manifest names {len(missing)} sample id(s) not present in the loaded "
            f"split: {missing[:5]}{'...' if len(missing) > 5 else ''}"
        )
    return tuple(by_id[sample_id] for sample_id in manifest.sample_ids)


def render_roster_entries(entries: Sequence[tuple[str, str]]) -> str:
    return "; ".join(f"{entry_type}={value}" for entry_type, value in entries)


def render_type_vocabulary(types: Sequence[str]) -> str:
    return ", ".join(types)


def _roster_packet(arm: str, entries: Sequence[tuple[str, str]]) -> SupplyPacket:
    prompt_block = render_roster_entries(entries)
    items = tuple(
        SupplyItem(item_id=f"{arm}-{index:03d}", text=f"{entry_type}={value}")
        for index, (entry_type, value) in enumerate(entries)
    )
    return SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=len(entries), token_count=len(prompt_block.split())),
        prompt_block=prompt_block,
        assembly_template_id=f"pslu-{arm}-roster-v1",
        items=items,
    ).validate()


def _type_vocabulary_packet(arm: str, types: Sequence[str]) -> SupplyPacket:
    prompt_block = render_type_vocabulary(types)
    items = tuple(
        SupplyItem(item_id=f"{arm}-{index:03d}", text=t)
        for index, t in enumerate(types)
    )
    return SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=len(types), token_count=len(prompt_block.split())),
        prompt_block=prompt_block,
        assembly_template_id=f"pslu-{arm}-roster-v1",
        items=items,
    ).validate()


def pslu_supply_packet(
    arm: str, *, scenario: str | None, rosters: PsluRosters
) -> SupplyPacket | None:
    """One arm's ``SupplyPacket`` (or ``None`` for A0's zero-supply). Module
    docstring covers the roster-selection rule per arm; ``scenario`` is the
    GOLD scenario for A1/A4 (documented, gold-scoped-by-design arms) and the
    PHASE-1 PREDICTED scenario (``None`` if unparsed/unknown) for A1'."""

    if arm == PSLU_PHASE1_ARM:
        return None
    if arm == "A1":
        if scenario is None:
            raise PsluFlightError("A1 requires the sample's own gold scenario")
        entries = rosters.scenario_rosters.get(scenario)
        if entries is None:
            raise PsluFlightError(f"no A1 roster for scenario {scenario!r}")
        return _roster_packet(arm, entries)
    if arm == "A1p":
        entries = (
            rosters.scenario_rosters.get(scenario) if scenario is not None else None
        )
        if entries is None:
            # Module docstring: an unparsed/unknown phase-1 prediction falls
            # back to the scenario-agnostic A2 roster -- NEVER to gold.
            return _type_vocabulary_packet("A1p-fallback-A2", rosters.global_types)
        return _roster_packet(arm, entries)
    if arm == "A2":
        return _type_vocabulary_packet(arm, rosters.global_types)
    if arm == "A3":
        return _roster_packet(arm, rosters.full_roster)
    if arm == "A4":
        if scenario is None:
            raise PsluFlightError(
                "A4 requires the sample's own gold scenario for its derangement key"
            )
        deranged_scenario = rosters.derangement.get(scenario)
        if deranged_scenario is None:
            raise PsluFlightError(
                f"no A4 derangement mapping for scenario {scenario!r}"
            )
        entries = rosters.scenario_rosters.get(deranged_scenario)
        if entries is None:
            raise PsluFlightError(
                f"no A1 roster for deranged scenario {deranged_scenario!r}"
            )
        return _roster_packet(arm, entries)
    raise PsluFlightError(f"unknown P-SLU arm {arm!r}; known arms are {PSLU_ARMS}")


# ---------------------------------------------------------------------------
# Flight orchestration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PsluArmResult:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: ConsumptionTrace
    silence_swapped: bool = False
    # Only meaningful on an "A0" row: whether parse_slu_response actually
    # parsed a scenario out of that row's own response (phase 1's own
    # signal for A1''s roster selection). None for every other arm.
    phase1_scenario_parsed: bool | None = None


@dataclass(frozen=True)
class PsluFlightSummary:
    results: tuple[PsluArmResult, ...]
    # sample_id -> the phase-1 predicted scenario, or None when phase 1
    # failed to parse one (module docstring's A1' fallback trigger) -- kept
    # on the summary for audit even though A1p's own supply packet already
    # encodes the consequence.
    predicted_scenario_by_sample_id: Mapping[str, str | None]


def _swap_audio_media_relpath(
    messages: Sequence[Mapping[str, object]], media_relpath: str
) -> tuple[Mapping[str, object], ...]:
    """A silence-swap variant of ``messages``: same system+text content,
    audio content part's ``media_relpath`` replaced. Never mutates the
    input."""

    system_message, user_message = messages
    new_content = []
    for part in user_message["content"]:  # type: ignore[union-attr]
        if isinstance(part, Mapping) and part.get("type") == "input_audio":
            new_content.append({**part, "media_relpath": media_relpath})
        else:
            new_content.append(dict(part))
    return (dict(system_message), {"role": "user", "content": new_content})


def run_pslu_flight(
    *,
    adapter: SlurpAdapter,
    core_client,
    samples: Sequence[SlurpSample],
    rosters: PsluRosters,
    decoding_params: Mapping[str, object] | None = None,
    silence_swap_media_relpaths: Mapping[str, str] = MappingProxyType({}),
) -> PsluFlightSummary:
    """Execute the full six-arm P-SLU flight over ``samples`` (module
    docstring: phase 1 = A0, phase 2 = A1/A1'/A2/A3/A4) plus one extra A1'
    request per entry in ``silence_swap_media_relpaths`` (``sample_id ->
    already-registered silent media_relpath`` -- ``rails.silence_swap`` +
    ``FrozenCoreClient.register_slice`` build that registration; this
    function only consumes the resulting mapping, staying generic over any
    ``CoreClient`` implementation, ``MockCoreClient`` included).

    ``core_client`` is duck-typed against ``rails.core_client.CoreClient``
    (not imported/annotated directly, to keep this module's own signature
    free of importing FrozenCoreClient -- the SAME "no forced import"
    discipline ``rails.obs.default_obs_packet`` uses for ``TaskSample``).
    """

    assert_never_calls_ontology_miner()
    if not samples:
        raise PsluFlightError("run_pslu_flight requires at least one sample")
    sample_ids = {sample.sample_id for sample in samples}
    unknown_silence_ids = set(silence_swap_media_relpaths) - sample_ids
    if unknown_silence_ids:
        raise PsluFlightError(
            f"silence_swap_media_relpaths names sample ids outside this flight's own "
            f"samples: {sorted(unknown_silence_ids)}"
        )

    results: list[PsluArmResult] = []
    predicted_scenario_by_sample_id: dict[str, str | None] = {}

    # Phase 1: A0 -- one zero-supply request per sample, doubling as the
    # scenario-prediction source A1' phase 2 reads (module docstring).
    for sample in samples:
        messages = adapter.assemble_prompt(sample, None)
        response_text = core_client.complete(messages, decoding_params=decoding_params)
        predicted_scenario, _predicted_action, _predicted_entities, parsed = (
            parse_slu_response(response_text)
        )
        predicted_scenario_by_sample_id[sample.sample_id] = (
            predicted_scenario if parsed else None
        )
        metrics = adapter.score(sample, response_text)
        consumption = adapter.extract_consumption(sample, None, response_text)
        results.append(
            PsluArmResult(
                arm=PSLU_PHASE1_ARM,
                sample_id=sample.sample_id,
                messages=tuple(messages),
                response_text=response_text,
                metrics=metrics,
                consumption=consumption,
                phase1_scenario_parsed=parsed,
            )
        )

    # Phase 2: A1, A1', A2, A3, A4 -- plus silence-swap A1' variants.
    for sample in samples:
        for arm in PSLU_PHASE2_ARMS:
            scenario = (
                sample.scenario
                if arm in ("A1", "A4")
                else predicted_scenario_by_sample_id[sample.sample_id]
            )
            supply = pslu_supply_packet(arm, scenario=scenario, rosters=rosters)
            messages = adapter.assemble_prompt(sample, supply)
            response_text = core_client.complete(
                messages, decoding_params=decoding_params
            )
            metrics = adapter.score(sample, response_text)
            consumption = adapter.extract_consumption(sample, supply, response_text)
            results.append(
                PsluArmResult(
                    arm=arm,
                    sample_id=sample.sample_id,
                    messages=tuple(messages),
                    response_text=response_text,
                    metrics=metrics,
                    consumption=consumption,
                )
            )
            if arm == "A1p":
                silence_media_relpath = silence_swap_media_relpaths.get(
                    sample.sample_id
                )
                if silence_media_relpath is not None:
                    silence_messages = _swap_audio_media_relpath(
                        messages, silence_media_relpath
                    )
                    silence_response_text = core_client.complete(
                        silence_messages, decoding_params=decoding_params
                    )
                    silence_metrics = adapter.score(sample, silence_response_text)
                    silence_consumption = adapter.extract_consumption(
                        sample, supply, silence_response_text
                    )
                    results.append(
                        PsluArmResult(
                            arm=arm,
                            sample_id=sample.sample_id,
                            messages=silence_messages,
                            response_text=silence_response_text,
                            metrics=silence_metrics,
                            consumption=silence_consumption,
                            silence_swapped=True,
                        )
                    )

    return PsluFlightSummary(
        results=tuple(results),
        predicted_scenario_by_sample_id=predicted_scenario_by_sample_id,
    )


__all__ = [
    "CandidateActionStateV1",
    "CandidateCounterevidenceStateV1",
    "CandidateSupportStateV1",
    "DecisionBoundaryV1",
    "DecisionFactorV1",
    "DecisionGraphExpansionV1",
    "DecisionGraphNeighborhoodV1",
    "DecisionGraphV1",
    "FactorLinkStateV1",
    "KeyCardV1",
    "GroundedEvidenceV1",
    "GroundedQueryStateV1",
    "PSLU_ARMS",
    "PSLU_PHASE1_ARM",
    "PSLU_PHASE2_ARMS",
    "PsluArmResult",
    "PsluFlightError",
    "PsluFlightSummary",
    "PsluRosters",
    "PsluSampleManifest",
    "SPEECH_NATIVE_KEY_REPRESENTATIONS",
    "SPEECH_NATIVE_MATCHER_POLICIES",
    "SPEECH_NATIVE_AGENT_POLICIES",
    "SPEECH_NATIVE_ACTION_FACET_DESCRIPTIONS",
    "SPEECH_NATIVE_BOUNDARY_POLICY_IDS",
    "SPEECH_NATIVE_INFORMATION_COMPLETE_KNOWLEDGE_POLICY_ID",
    "SPEECH_NATIVE_KNOWLEDGE_POLICY_ID",
    "SPEECH_NATIVE_KNOWLEDGE_POLICY_IDS",
    "SPEECH_NATIVE_SCENARIO_CONTRASTS",
    "SPEECH_NATIVE_SCENARIO_DEFINITIONS",
    "SpeechNativeEngineeringGate",
    "SpeechNativeEngineeringSample",
    "SpeechNativeDecision",
    "SpeechNativeMatchOutcome",
    "SpeechNativeMatchTask",
    "assert_never_calls_ontology_miner",
    "audit_speech_native_scale_capacity",
    "build_data_derived_decision_graph",
    "build_speech_native_information_audit",
    "build_speech_native_binding",
    "candidate_counterevidence_response_format",
    "candidate_action_state_response_format",
    "candidate_support_response_format",
    "decision_boundary_path",
    "expand_decision_graph_candidates",
    "expand_decision_graph_neighborhood",
    "extend_speech_native_binding",
    "factor_link_response_format",
    "load_pslu_rosters",
    "load_pslu_sample_manifest",
    "load_speech_native_engineering_gate",
    "pslu_supply_packet",
    "parse_candidate_counterevidence_state",
    "parse_candidate_action_state",
    "parse_candidate_support_state",
    "parse_factor_link_state",
    "parse_grounded_query_state",
    "partition_speech_native_train_knowledge",
    "render_decision_graph_neighborhood",
    "render_factor_link_state",
    "render_roster_entries",
    "render_speech_native_keys",
    "render_type_vocabulary",
    "refine_speech_native_binding_knowledge",
    "run_pslu_flight",
    "run_openjiuwen_speech_native_match_tasks",
    "run_speech_native_matcher",
    "run_speech_native_match_tasks",
    "select_pslu_samples",
    "validate_openjiuwen_speech_native_match_tasks",
]


# Executed at import time (module docstring / assert_never_calls_ontology_miner's
# own docstring): fails LOUD the moment this module is loaded if a future
# edit adds a live reference to the forbidden ontology miner.
assert_never_calls_ontology_miner()
