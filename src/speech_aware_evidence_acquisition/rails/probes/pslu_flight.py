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
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from ...data.slurp import SlurpTrainMaterial
from ...reproduction.slurp_scoring import parse_slu_response
from ..adapters.slurp import SlurpAdapter, SlurpSample
from ..consumption import ConsumptionTrace
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


SPEECH_NATIVE_KEY_REPRESENTATIONS = ("K0", "K1", "K2", "K3", "K4")
SPEECH_NATIVE_MATCHER_POLICIES = ("M0", "M1", "M2", "M3", "M4")
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
    try:
        document = json.loads(text.strip())
    except (json.JSONDecodeError, UnicodeError):
        return None
    return document if isinstance(document, Mapping) else None


def _selected_key_id(text: str, allowed: set[str]) -> str | None:
    document = _response_object(text)
    key_id = document.get("key_id") if document is not None else None
    return key_id if isinstance(key_id, str) and key_id in allowed else None


def _selected_top_keys(text: str, allowed: set[str], top_k: int) -> tuple[str, ...]:
    document = _response_object(text)
    raw = document.get("key_ids") if document is not None else None
    if not isinstance(raw, list):
        return ()
    selected: list[str] = []
    for key_id in raw:
        if isinstance(key_id, str) and key_id in allowed and key_id not in selected:
            selected.append(key_id)
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
    decoding_params: Mapping[str, object] | None = None,
    top_k: int = 3,
    audio_key_bindings: Mapping[str, Mapping[str, str]] | None = None,
    ensemble_base_policy_id: str = "M1",
    _trace_matcher_policy_id: str | None = None,
) -> SpeechNativeDecision:
    """Run one frozen-core speech-query decision under M0--M4.

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
    top_k_is_active = matcher_policy_id == "M3" or (
        matcher_policy_id == "M4" and ensemble_base_policy_id == "M3"
    )
    if top_k_is_active and (top_k <= 0 or top_k > len(cards)):
        raise PsluFlightError(f"top_k must be in [1, {len(cards)}], got {top_k}")
    by_key = {card.key_id: card for card in cards}
    allowed = set(by_key)
    raw_responses: list[str] = []

    def contact(
        stage: str,
        system_text: str,
        stage_cards: Sequence[KeyCardV1],
        key_text: str | None,
    ) -> str:
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
        response = core_client.complete(
            messages,
            decoding_params=decoding_params,
            speech_feature_sample_id=sample.sample_id,
            key_representation_id=key_representation_id,
            matcher_policy_id=f"{_trace_matcher_policy_id or matcher_policy_id}:{stage}",
        )
        raw_responses.append(response)
        return response

    def finish(
        key_id: str | None,
        *,
        top_ids: tuple[str, ...] = (),
        scores: Mapping[str, tuple[bool, float]] = MappingProxyType({}),
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
        )

    if matcher_policy_id == "M4":
        orderings = (
            cards,
            tuple(reversed(cards)),
            cards[1:] + cards[:1],
        )
        decisions = []
        for order_index, ordering in enumerate(orderings):
            decisions.append(
                run_speech_native_matcher(
                core_client=core_client,
                sample=sample,
                query_descriptor=query_descriptor,
                key_cards=ordering,
                key_representation_id=key_representation_id,
                matcher_policy_id=ensemble_base_policy_id,
                decoding_params=decoding_params,
                top_k=top_k,
                audio_key_bindings=audio_key_bindings,
                _trace_matcher_policy_id=(
                    f"M4:{ensemble_base_policy_id}:order-{order_index}"
                ),
            )
            )
        for decision in decisions:
            raw_responses.extend(decision.raw_responses)
        votes = [decision.key_id for decision in decisions if decision.key_id is not None]
        if not votes:
            return finish(None)
        counts = {key_id: votes.count(key_id) for key_id in set(votes)}
        winner = min(counts, key=lambda key_id: (-counts[key_id], key_id))
        return finish(winner)

    if matcher_policy_id == "M0":
        response = contact(
            "direct-label",
            "Classify the spoken command into exactly one listed label. Respond only as "
            '{"label":"..."}.',
            cards,
            render_speech_native_keys(cards, "K0"),
        )
        document = _response_object(response)
        label = document.get("label") if document is not None else None
        key_id = next((card.key_id for card in cards if card.value_label == label), None)
        return finish(key_id)

    if matcher_policy_id == "M1":
        response = contact(
            "listwise",
            "Match the spoken command to exactly one opaque key. Use the speech signal and "
            "the supplied key representations jointly. Respond only as "
            '{"key_id":"K000"}.',
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
            "request. Respond only as {\"key_id\":\"K000\"}.",
            cards,
            (
                "Prior semantic analysis:\n"
                + factors
                + "\n\nKeys:\n"
                + render_speech_native_keys(cards, key_representation_id)
            ),
        )
        return finish(_selected_key_id(response, allowed))

    retrieval = contact(
        f"retrieve-top-{top_k}",
        f"Retrieve the {top_k} most compatible opaque keys for the spoken command, best first. "
        f"Respond only as {{\"key_ids\":[\"K000\"]}} with at most {top_k} ids.",
        cards,
        render_speech_native_keys(cards, key_representation_id),
    )
    top_ids = _selected_top_keys(retrieval, allowed, top_k)
    if not top_ids:
        return finish(None)
    verifier_scores: dict[str, tuple[bool, float]] = {}
    for key_id in top_ids:
        card = by_key[key_id]
        response = contact(
            f"verify-{key_id}",
            "Judge whether the spoken command is compatible with this one candidate key. "
            "Respond only as {\"compatible\":true,\"confidence\":0}, with confidence from "
            "0 to 100.",
            (card,),
            render_speech_native_keys((card,), key_representation_id),
        )
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
        "tied opaque keys. Respond only as {\"key_id\":\"K000\"}.",
        tied_cards,
        render_speech_native_keys(tied_cards, key_representation_id),
    )
    key_id = _selected_key_id(response, set(tied))
    return finish(key_id, top_ids=top_ids, scores=verifier_scores)


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
    unsigned: dict[str, object] = {
        "schema": "saea-speech-native-binding-v1",
        "status": "MODEL-FREE BINDING; NOT AN EXPOSURE REGISTRATION",
        "seed": seed,
        "source_split": "SLURP train real speech only",
        "splits": split_documents,
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
    "SPEECH_NATIVE_SCENARIO_CONTRASTS",
    "SPEECH_NATIVE_SCENARIO_DEFINITIONS",
    "SpeechNativeDecision",
    "assert_never_calls_ontology_miner",
    "build_speech_native_binding",
    "load_pslu_rosters",
    "load_pslu_sample_manifest",
    "pslu_supply_packet",
    "render_roster_entries",
    "render_speech_native_keys",
    "render_type_vocabulary",
    "run_pslu_flight",
    "run_speech_native_matcher",
    "select_pslu_samples",
]


# Executed at import time (module docstring / assert_never_calls_ontology_miner's
# own docstring): fails LOUD the moment this module is loaded if a future
# edit adds a live reference to the forbidden ontology miner.
assert_never_calls_ontology_miner()
