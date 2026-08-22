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
from collections import deque
from copy import deepcopy
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from threading import BoundedSemaphore
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

from ...data.loader import LoaderError
from ...data.slurp import (
    SlurpTrainMaterial,
    _probe_engineering_media,
    load_slurp_engineering_gate,
)
from ...reproduction.slurp_scoring import parse_slu_response
from ...core.tracing import TraceBuffer, set_current_trace_buffer
from ..adapters.slurp import SlurpAdapter, SlurpSample
from ..consumption import ConsumptionTrace
from ..obs import AudioRef
from ..supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket

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
)
SPEECH_NATIVE_PROMPT_POLICIES = (
    "speech-native-json-copy-v2",
    "speech-native-json-copy-v3",
    "speech-native-json-copy-v4",
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
)
SPEECH_NATIVE_AGENT_POLICIES = (
    "m1-m3-disagreement-escalation-v1",
    "m1-m3-full-branch-explorer-v1",
    "knowledge-grounded-semantic-refinement-full-action-v1",
    "knowledge-grounded-semantic-refinement-schema-v2",
    "knowledge-grounded-semantic-refinement-schema-v3",
    "knowledge-grounded-multistate-action-support-v1",
    "speech-conditioned-pairwise-boundary-support-v1",
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
        if not self.positive_examples or any(not item.strip() for item in self.positive_examples):
            raise PsluFlightError(
                f"key {self.key_id}: positive_examples must be non-empty strings"
            )
        if self.contrastive_boundary is not None and not self.contrastive_boundary.strip():
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
    verifier_policy_id: str = "speech-native-compatibility-v1"
    decoding_params: Mapping[str, object] = field(default_factory=dict)
    top_k: int = 3
    audio_key_bindings: Mapping[str, Mapping[str, str]] | None = None
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
        raise PsluFlightError("speech-native key cards contain duplicate value_label values")
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
                else ""
            ,)
        if not any(quote in source for source in sources):
            return None
        evidence.append(
            GroundedEvidenceV1(
                key_id=str(key_id), field=str(field_name), quote=quote
            )
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
) -> tuple[Mapping[str, object], ...]:
    required = {"packet_id", "sha256", "role"}
    if set(query_descriptor) != required or query_descriptor.get("role") != "query":
        raise PsluFlightError("query_descriptor must carry exact packet_id/sha256/role=query")
    content: list[Mapping[str, object]] = []
    if key_text:
        content.append({"type": "text", "text": key_text})
    content.append(
        {"type": "input_speech_features", "speech_features": dict(query_descriptor)}
    )
    if key_representation_id in {"K3", "K4"}:
        if audio_key_bindings is None or set(audio_key_bindings) != {
            card.key_id for card in key_cards
        }:
            raise PsluFlightError(
                f"{key_representation_id} requires one audio key binding per key card"
            )
        for card in key_cards:
            binding = audio_key_bindings[card.key_id]
            if not isinstance(binding, Mapping) or set(binding) != {"packet_id", "sha256"}:
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
    return (
        {"role": "system", "content": system_text},
        {"role": "user", "content": content},
    )


def run_speech_native_matcher(
    *,
    core_client,
    sample,
    query_descriptor: Mapping[str, str],
    key_cards: Sequence[KeyCardV1],
    key_representation_id: str,
    matcher_policy_id: str,
    prompt_policy_id: str = "speech-native-json-copy-v2",
    verifier_policy_id: str = "speech-native-compatibility-v1",
    decoding_params: Mapping[str, object] | None = None,
    top_k: int = 3,
    audio_key_bindings: Mapping[str, Mapping[str, str]] | None = None,
    ensemble_base_policy_id: str = "M1",
    agent_policy_id: str = "m1-m3-disagreement-escalation-v1",
    agent_aggregator_id: str = "m3-majority-canonical-tie-v1",
    _trace_matcher_policy_id: str | None = None,
    _trace_buffer: TraceBuffer | None = None,
) -> SpeechNativeDecision:
    """Run one frozen-core speech-query decision under M0--M8.

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
        agent_policy_id not in m5_policies
        or agent_aggregator_id not in m5_aggregators
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
        raise PsluFlightError("M7 requires the multistate action-support policy and control")
    if matcher_policy_id == "M7" and key_representation_id not in {"K1", "K2"}:
        raise PsluFlightError("M7 supports maintainable text keys K1/K2 only")
    if matcher_policy_id == "M7" and prompt_policy_id != "speech-native-json-copy-v3":
        raise PsluFlightError("M7 requires the strict JSON-copy v3 prompt policy")
    if matcher_policy_id == "M8" and (
        agent_policy_id != "speech-conditioned-pairwise-boundary-support-v1"
        or agent_aggregator_id != "pairwise-boundary-primary-control-v1"
    ):
        raise PsluFlightError("M8 requires the pairwise-boundary support policy and control")
    if matcher_policy_id == "M8" and key_representation_id != "K1":
        raise PsluFlightError("M8 requires maintainable K1 text keys at the profile boundary")
    if matcher_policy_id == "M8" and prompt_policy_id != "speech-native-json-copy-v4":
        raise PsluFlightError("M8 requires the schema-constrained JSON-copy v4 prompt policy")
    top_k_is_active = matcher_policy_id in {"M3", "M5", "M6", "M7", "M8"} or (
        matcher_policy_id == "M4" and ensemble_base_policy_id == "M3"
    )
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
        specifications: Sequence[
            tuple[str, str, Sequence[KeyCardV1], str | None]
        ],
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
            verifier_policy_id=verifier_policy_id,
            decoding_params=decoding_params,
            top_k=top_k,
            audio_key_bindings=audio_key_bindings,
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
        votes = [decision.key_id for decision in decisions if decision.key_id is not None]
        if not votes:
            return finish(None)
        counts = {key_id: votes.count(key_id) for key_id in set(votes)}
        majority = next((key_id for key_id, count in counts.items() if count >= 2), None)
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
        majority = next((key_id for key_id, count in counts.items() if count >= 2), None)
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
                (
                    "explore:full-branch"
                    if full_branch
                    else "escalate:disagreement"
                ),
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
                                "label": {
                                    "enum": [card.value_label for card in cards]
                                }
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
        key_id = next((card.key_id for card in cards if card.value_label == label), None)
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
                            render_speech_native_keys(
                                ordered_cards, representation_id
                            ),
                            {"response_format": response_format},
                        )
                    )
                    pairwise_owners.append((rank, representation_id, order_id))
        pairwise_responses = contact_many_with_overrides(tuple(pairwise_requests))
        parsed_votes: dict[tuple[int, str, str], str | None] = {}
        for owner, response in zip(
            pairwise_owners, pairwise_responses, strict=True
        ):
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
            refined_top_ids = _selected_top_keys(
                retrieval_response, allowed, top_k
            )
            record["top_key_ids"] = refined_top_ids
            if len(refined_top_ids) != top_k:
                record["parse_failure"] = True

        verifier_requests: list[
            tuple[str, str, Sequence[KeyCardV1], str | None]
        ] = []
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
            compatible = [
                key_id for key_id in refined_top_ids if scores[key_id][0]
            ]
            pool = compatible or list(refined_top_ids)
            best_score = max(scores[key_id][1] for key_id in pool)
            tied = tuple(
                key_id for key_id in pool if scores[key_id][1] == best_score
            )
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
            + render_speech_native_keys(
                initial_cards, state_key_representation_id
            ),
            decoding_overrides=state_decoding_overrides,
        )
        state = parse_grounded_query_state(
            state_response,
            candidate_key_ids=initial_top_ids,
            cards_by_key=by_key,
            key_representation_id=state_key_representation_id,
        )
        if state is None:
            return backtrack(
                "backtrack:invalid-grounding", state_contacted=True
            )
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
        for key_id, response in zip(
            refined_top_ids, verifier_responses, strict=True
        ):
            parsed = _compatibility(response)
            verifier_scores[key_id] = parsed if parsed is not None else (False, -1.0)
        compatible = [
            key_id for key_id in refined_top_ids if verifier_scores[key_id][0]
        ]
        pool = compatible or list(refined_top_ids)
        best_score = max(verifier_scores[key_id][1] for key_id in pool)
        tied = [
            key_id for key_id in pool if verifier_scores[key_id][1] == best_score
        ]
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
    if (
        prompt_policy_id == "speech-native-json-copy-v3"
        and len(top_ids) != top_k
    ):
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

    if isinstance(slot_count, bool) or not isinstance(slot_count, int) or slot_count <= 0:
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
                or task.agent_aggregator_id
                != "pairwise-boundary-primary-control-v1"
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
                key_text=render_speech_native_keys(
                    stage_cards, key_representation_id
                ),
                key_cards=stage_cards,
                key_representation_id=key_representation_id,
                audio_key_bindings=None,
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
                for rank, challenger_key_id in enumerate(
                    state.challengers, start=1
                ):
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
                            "action_id": (
                                f"compare:pairwise-boundary-rank-{rank}"
                            ),
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
                                vote is None
                                for vote in (k1_ab, k1_ba, k2_ab, k2_ba)
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
                    raise PsluFlightError(
                        f"unknown M8 DAG stage {node.stage_kind!r}"
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
            result.outcome
            for result in buffered_outcomes
            if result.outcome is not None
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
            verifier_scores: dict[str, tuple[bool, float]] = field(
                default_factory=dict
            )
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
                key_text=render_speech_native_keys(
                    (card,), task.key_representation_id
                ),
                key_id=key_id,
            )

        def tie_node(state: DagBranchState) -> DagContact:
            task = ordered_tasks[state.task_index]
            cards = tuple(
                card for card in state.cards if card.key_id in state.tied_ids
            )
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
                key_text=render_speech_native_keys(
                    cards, task.key_representation_id
                ),
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
                (error for _decision, _buffer, error in task_results if error is not None),
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
            counts = {
                key_id: valid_votes.count(key_id) for key_id in set(valid_votes)
            }
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
            label_by_key = {
                card.key_id: card.value_label for card in task.key_cards
            }

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
                    response
                    for item in decisions
                    for response in item.raw_responses
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
            result.outcome
            for result in buffered_outcomes
            if result.outcome is not None
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
                verifier_policy_id=task.verifier_policy_id,
                decoding_params=decoding_params,
                top_k=task.top_k,
                audio_key_bindings=task.audio_key_bindings,
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
                next_index < len(ordered_tasks)
                and len(futures) < query_admission_depth
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


def _binding_rank(seed: int, purpose: str, *parts: str) -> str:
    text = "|".join((str(seed), purpose, *parts))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalized_sentence(sentence: str) -> str:
    return " ".join(sentence.casefold().split())


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
    if any(isinstance(count, bool) or not isinstance(count, int) or count <= 0 for count in counts):
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
    by_scenario: dict[str, list[SlurpTrainMaterial]] = {scenario: [] for scenario in scenarios}
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
        ordered = sorted(items, key=lambda item: (item["value_label"], item["sample_id"]))
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
        or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for character in split_name)
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
        raise PsluFlightError("speech-native parent binding cannot accept the extension")
    scenarios = tuple(expected_scenarios)
    card_labels = tuple(
        card.get("value_label") if isinstance(card, Mapping) else None
        for card in raw_cards
    )
    if not scenarios or len(set(scenarios)) != len(scenarios) or card_labels != scenarios:
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
                raise PsluFlightError(
                    f"speech-native {context} lacks {field_name}"
                )
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
                "parent_query_speaker_overlap_count": len(
                    parent_query_speaker_overlap
                ),
            },
            "isolation_audit": {
                "query_sample_count": len(forbidden_samples - key_samples) + len(ordered),
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
        raise PsluFlightError(f"{path}: probe must be {_PROBE_ID!r}, got {document.get('probe')!r}")
    if document.get("legality_tier") != _LEGAL_TIER:
        raise PsluFlightError(
            f"{path}: legality_tier must be {_LEGAL_TIER!r}, got {document.get('legality_tier')!r}"
        )
    refused = document.get("train_synthetic_refused")
    if not isinstance(refused, Mapping) or refused.get("train_jsonl_overlap_with_devel") != 0:
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
        derangement = {str(k): str(v) for k, v in arms["A4_deranged"]["mapping"].items()}
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
        raise PsluFlightError(f"{path}: probe must be {_PROBE_ID!r}, got {document.get('probe')!r}")
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
    return PsluSampleManifest(sample_ids=sample_ids, split_identity_hash=split_identity_hash, seed=seed)


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
    items = tuple(SupplyItem(item_id=f"{arm}-{index:03d}", text=t) for index, t in enumerate(types))
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
        entries = rosters.scenario_rosters.get(scenario) if scenario is not None else None
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
            raise PsluFlightError("A4 requires the sample's own gold scenario for its derangement key")
        deranged_scenario = rosters.derangement.get(scenario)
        if deranged_scenario is None:
            raise PsluFlightError(f"no A4 derangement mapping for scenario {scenario!r}")
        entries = rosters.scenario_rosters.get(deranged_scenario)
        if entries is None:
            raise PsluFlightError(f"no A1 roster for deranged scenario {deranged_scenario!r}")
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
        predicted_scenario, _predicted_action, _predicted_entities, parsed = parse_slu_response(
            response_text
        )
        predicted_scenario_by_sample_id[sample.sample_id] = predicted_scenario if parsed else None
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
            response_text = core_client.complete(messages, decoding_params=decoding_params)
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
                silence_media_relpath = silence_swap_media_relpaths.get(sample.sample_id)
                if silence_media_relpath is not None:
                    silence_messages = _swap_audio_media_relpath(messages, silence_media_relpath)
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
        results=tuple(results), predicted_scenario_by_sample_id=predicted_scenario_by_sample_id
    )


__all__ = [
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
    "SPEECH_NATIVE_SCENARIO_CONTRASTS",
    "SPEECH_NATIVE_SCENARIO_DEFINITIONS",
    "SpeechNativeEngineeringGate",
    "SpeechNativeEngineeringSample",
    "SpeechNativeDecision",
    "SpeechNativeMatchOutcome",
    "SpeechNativeMatchTask",
    "assert_never_calls_ontology_miner",
    "build_speech_native_binding",
    "extend_speech_native_binding",
    "load_pslu_rosters",
    "load_pslu_sample_manifest",
    "load_speech_native_engineering_gate",
    "pslu_supply_packet",
    "parse_grounded_query_state",
    "render_roster_entries",
    "render_speech_native_keys",
    "render_type_vocabulary",
    "run_pslu_flight",
    "run_speech_native_matcher",
    "run_speech_native_match_tasks",
    "select_pslu_samples",
]


# Executed at import time (module docstring / assert_never_calls_ontology_miner's
# own docstring): fails LOUD the moment this module is loaded if a future
# edit adds a live reference to the forbidden ontology miner.
assert_never_calls_ontology_miner()
