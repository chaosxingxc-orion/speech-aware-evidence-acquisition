"""The Solver's cited-answer contract: WHICH supplied entries an answer used.

Gap G1 of ``docs/results/2026-09-26-slurp-reviewer-planner-global-state-audit.md``:
``cited_value_ids`` is a field on every sealed role state and was empty in all
4,209 rendered states of all 2,590 contacts of the locked plan, because the
native episode seals with ``seal_phase_response_state(...)`` and never passes
it. Every supplied body already reaches the model labelled with its own id
(``[evidence <evidence_id>] ``, ``core.model.transport``), so the ids are in
front of the model; nothing asked it to say which ones it used. Without that
edge the finest action a terminal reward can credit is "the whole supply
block", and entry-level construction is un-creditable.

This module is that edge, built the way every other structured output
contract in this repository is built (``rails.review_findings`` is the closest
precedent, ``rails.controllers.native_planner_action_response_format`` the
other one):

* :data:`CITED_ANSWER_RESPONSE_FORMAT_ID` is a ``response_format_id`` a phase
  program binds to its ANSWERING phase. The registered
  :func:`cited_answer_response_format` renders the static schema; the runner
  specialises it PER CONTACT through :func:`cited_answer_response_format_for`
  so the citation arrays may only spell ids that contact actually rendered.
* :func:`parse_cited_answer` is the strict parser (no text repair): the
  envelope is ``{"schema", "answer", "citations": {"intent", "entities"}}``
  and the ANSWER is an ordinary JSON object the model writes exactly as it
  writes today's answer. A citation list is a SET of ids: an id the model
  repeats inside one list is collapsed to its first occurrence and COUNTED
  (``duplicate_ids_dropped``), never refused -- the per-contact grammar
  cannot express ``uniqueItems`` (the rendered format deliberately carries
  none, and llama.cpp's schema-to-grammar has no such constraint), so a
  repeat is a legal output of the constrained decoder; refusing it aborted
  the COMP-1 arm at one row
  (``docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md``).
  The delivered text is the answer's OWN BYTES, cut
  from the raw response by :func:`answer_span` -- never a re-serialisation --
  so the citation is metadata beside the answer and never part of it.
* :func:`bind_cited_completion` is what the runner seals: the state content
  becomes the answer bytes, ``cited_value_ids`` becomes the ordered union of
  every cited id, and an id the contact did not supply is a REFUSAL, not a
  silent drop.

Un-armed -- every phase program written before this module, the v2.0 lock
included -- no function here is reachable and every rendered byte, sealed
state and delivered text is exactly its prior self.

Delivery custody: the envelope is the model response, so the delivered answer
must be re-derived from it by a registered delivery normaliser (invariant
I7n, ``rails.delivery_normalisers``): :data:`DELIVER_CITED_ANSWER_V1` unwraps,
:data:`DELIVER_CITED_ANSWER_NORMALISE_V3_V1` unwraps and then applies the
locked plan's ``saea-deliver-normalise-v3``. ``rails.native_episode_config``
refuses a fragment that arms the contract without one of them, or one of them
without the contract.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

#: The phase ``response_format_id`` (and the envelope's own ``schema`` const).
CITED_ANSWER_RESPONSE_FORMAT_ID = "saea-solver-cited-answer-v1"
CITED_ANSWER_SCHEMA = CITED_ANSWER_RESPONSE_FORMAT_ID
#: The per-row receipt block the runner seals beside E17's
#: ``tool_schema_rendering`` block. Absent on every un-armed row.
SOLVER_CITATIONS_RECEIPT_SCHEMA = "saea-solver-citations-v1"
#: The delivery normalisers that can re-derive the delivered answer from a
#: cited-answer envelope (registered in ``rails.delivery_normalisers``); the
#: third is the second composed with the do-not-tag scope stage.
DELIVER_CITED_ANSWER_V1 = "saea-deliver-cited-answer-v1"
DELIVER_CITED_ANSWER_NORMALISE_V3_V1 = "saea-deliver-cited-answer-normalise-v3-v1"
DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1 = (
    "saea-deliver-cited-answer-normalise-v3-scope-rule-v1"
)
CITED_ANSWER_NORMALISER_IDS = frozenset(
    {
        DELIVER_CITED_ANSWER_V1,
        DELIVER_CITED_ANSWER_NORMALISE_V3_V1,
        DELIVER_CITED_ANSWER_NORMALISE_V3_SCOPE_RULE_V1,
    }
)

#: Contract bounds. They cap the OUTPUT side of the citation (the ids the
#: model emits, about 11.6 tokens each on the pinned vocab), so a citing
#: answer stays far inside the 512-token completion cap of the serving
#: geometry: at most 3 + 6 x 3 = 21 ids.
MAX_INTENT_CITATIONS = 3
MAX_ENTITY_CITATIONS = 6
MAX_EVIDENCE_IDS_PER_ENTITY = 3
MAX_EVIDENCE_ID_CHARS = 160
MAX_ENTITY_TYPE_CHARS = 64
MAX_RESPONSE_CHARS = 16384

_JSON_SCHEMA_NAME = "saea_solver_cited_answer_v1"


class SolverCitationError(ValueError):
    """A response has no unambiguous cited answer under the registered contract."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _id_items(supplied_value_ids: Sequence[str] | None) -> Mapping[str, object]:
    if supplied_value_ids is None:
        return {"type": "string", "minLength": 1, "maxLength": MAX_EVIDENCE_ID_CHARS}
    return {"type": "string", "enum": list(supplied_value_ids)}


def _id_array(cap: int, supplied_value_ids: Sequence[str] | None) -> Mapping[str, object]:
    if supplied_value_ids is not None and not supplied_value_ids:
        # Nothing was supplied, so nothing can be cited: the grammar admits
        # exactly the empty array rather than an enum with no members.
        return {"type": "array", "maxItems": 0}
    return {"type": "array", "maxItems": cap, "items": _id_items(supplied_value_ids)}


def envelope_schema(supplied_value_ids: Sequence[str] | None = None) -> dict[str, Any]:
    """The JSON schema of the cited-answer envelope.

    ``None`` renders the static contract (ids are bounded free strings);
    a sequence renders the per-contact specialisation whose citation arrays
    may only spell those ids. ``answer`` is deliberately a bare object: the
    model writes its task answer exactly as an un-armed Solver writes it, and
    only the envelope around it is constrained.
    """

    if supplied_value_ids is not None:
        ids = tuple(supplied_value_ids)
        if len(set(ids)) != len(ids) or any(
            not isinstance(value, str) or not value for value in ids
        ):
            raise SolverCitationError("supplied evidence ids must be unique non-empty strings")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema", "answer", "citations"],
        "properties": {
            "schema": {"const": CITED_ANSWER_SCHEMA},
            "answer": {"type": "object"},
            "citations": {
                "type": "object",
                "additionalProperties": False,
                "required": ["intent", "entities"],
                "properties": {
                    "intent": _id_array(MAX_INTENT_CITATIONS, supplied_value_ids),
                    "entities": {
                        "type": "array",
                        "maxItems": MAX_ENTITY_CITATIONS,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["type", "evidence_ids"],
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "minLength": 1,
                                    "maxLength": MAX_ENTITY_TYPE_CHARS,
                                },
                                "evidence_ids": _id_array(
                                    MAX_EVIDENCE_IDS_PER_ENTITY, supplied_value_ids
                                ),
                            },
                        },
                    },
                },
            },
        },
    }


def _response_format(schema: Mapping[str, object]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {"name": _JSON_SCHEMA_NAME, "strict": True, "schema": schema},
    }


def cited_answer_response_format(
    _lock: Any = None, _root: Any = None, **params: Any
) -> dict[str, Any]:
    """The ``core.base.RESPONSE_FORMATS`` entry ``"saea-solver-cited-answer-v1"``.

    Static: this is what ``rails.phase_material.resolve_response_formats``
    renders for the phase at config time and what the runner checks the
    phase material against before specialising it per contact.
    """

    if params:
        raise SolverCitationError("the cited-answer response format takes no parameters")
    return _response_format(envelope_schema(None))


def cited_answer_response_format_for(supplied_value_ids: Sequence[str]) -> dict[str, Any]:
    """The per-contact specialisation: citation arrays enumerate ``supplied_value_ids``."""

    return _response_format(envelope_schema(tuple(supplied_value_ids)))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SolverCitationError("cited answer repeats a JSON key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise SolverCitationError("cited answer contains a nonfinite JSON constant")


_VALIDATOR = None


def _validator():
    """The Draft 2020-12 validator over the static schema, built once and lazily
    so importing this module from config loading stays light."""

    global _VALIDATOR
    if _VALIDATOR is None:
        from jsonschema import Draft202012Validator

        _VALIDATOR = Draft202012Validator(envelope_schema(None))
    return _VALIDATOR


def answer_span(text: str) -> tuple[int, int]:
    """``(start, end)`` of the ``answer`` member's VALUE in ``text``.

    A token walk over the top-level object with the standard library's own
    decoder, so the span is exactly the bytes the model emitted for its
    answer -- its own spacing and key order included -- and never a
    re-serialisation. Call only on text :func:`parse_cited_answer` accepted.
    """

    from json.decoder import WHITESPACE

    decoder = json.JSONDecoder()

    def skip(index: int) -> int:
        return WHITESPACE.match(text, index).end()

    index = skip(0)
    if index >= len(text) or text[index] != "{":
        raise SolverCitationError("cited answer is not a JSON object")
    index += 1
    while True:
        index = skip(index)
        if index >= len(text) or text[index] == "}":
            raise SolverCitationError("cited answer has no answer member")
        try:
            key, index = decoder.raw_decode(text, index)
            index = skip(index)
            if text[index] != ":":
                raise SolverCitationError("cited answer member has no value")
            index = skip(index + 1)
            start = index
            _value, index = decoder.raw_decode(text, index)
        except (json.JSONDecodeError, IndexError) as error:
            raise SolverCitationError("cited answer is not well-formed JSON") from error
        if key == "answer":
            return start, index
        index = skip(index)
        if index < len(text) and text[index] == ",":
            index += 1
            continue
        raise SolverCitationError("cited answer has no answer member")


@dataclass(frozen=True)
class EntityCitation:
    type: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class CitedAnswer:
    """One parsed envelope: the answer's own bytes plus the ids it cites."""

    schema: str
    answer_text: str
    answer: Mapping[str, object]
    intent_evidence_ids: tuple[str, ...]
    entity_citations: tuple[EntityCitation, ...]
    #: How many repeated ids the parser collapsed across every citation list
    #: (intent and each entity). Zero on every envelope without a repeat.
    duplicate_ids_dropped: int = 0

    @property
    def cited_value_ids(self) -> tuple[str, ...]:
        """Every cited id once, in first-citation order (intent first)."""

        ordered = list(self.intent_evidence_ids)
        for entity in self.entity_citations:
            ordered.extend(entity.evidence_ids)
        return tuple(dict.fromkeys(ordered))

    def citations_json(self) -> dict[str, object]:
        return {
            "intent": list(self.intent_evidence_ids),
            "entities": [
                {"type": entity.type, "evidence_ids": list(entity.evidence_ids)}
                for entity in self.entity_citations
            ],
        }


def parse_cited_answer(text: str) -> CitedAnswer:
    """Return the exact structured declaration, or reject without text repair."""

    if not isinstance(text, str) or not text.strip() or len(text) > MAX_RESPONSE_CHARS:
        raise SolverCitationError("cited answer requires bounded nonempty text")
    try:
        document = json.loads(
            text, object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        from jsonschema import ValidationError

        try:
            _validator().validate(document)
        except ValidationError as error:
            raise SolverCitationError(
                "cited answer does not match its JSON contract"
            ) from error
    except json.JSONDecodeError as error:
        raise SolverCitationError("cited answer does not match its JSON contract") from error
    citations = document["citations"]
    # A citation list is a set of ids. The per-contact grammar admits a
    # repeated id (it cannot express ``uniqueItems``), so a repeat is
    # collapsed to its first occurrence and counted: the answer bytes, the
    # cited set and ``cited_value_ids`` are exactly what they would be
    # without the repeat. A BLANK id is still refused: the per-contact
    # grammar enumerates supplied non-empty ids, so a blank one means the
    # server did not honour the grammar.
    dropped = 0
    raw_intent = tuple(citations["intent"])
    if any(not value.strip() for value in raw_intent):
        raise SolverCitationError("intent citations must be non-blank ids")
    intent_ids = tuple(dict.fromkeys(raw_intent))
    dropped += len(raw_intent) - len(intent_ids)
    entities = []
    for entity in citations["entities"]:
        raw_ids = tuple(entity["evidence_ids"])
        if any(not value.strip() for value in raw_ids) or not entity["type"].strip():
            raise SolverCitationError("citation ids and entity types cannot be blank")
        ids = tuple(dict.fromkeys(raw_ids))
        dropped += len(raw_ids) - len(ids)
        entities.append(EntityCitation(type=entity["type"], evidence_ids=ids))
    start, end = answer_span(text)
    return CitedAnswer(
        schema=document["schema"],
        answer_text=text[start:end],
        answer=document["answer"],
        intent_evidence_ids=intent_ids,
        entity_citations=tuple(entities),
        duplicate_ids_dropped=dropped,
    )


def validate_citations_supplied(
    parsed: CitedAnswer, supplied_value_ids: Sequence[str]
) -> None:
    """Refuse a citation of anything the contact did not render."""

    supplied = set(supplied_value_ids)
    unknown = [value for value in parsed.cited_value_ids if value not in supplied]
    if unknown:
        shown = ", ".join(repr(value) for value in unknown[:3])
        raise SolverCitationError(
            f"cited answer names {len(unknown)} evidence id(s) this contact never "
            f"supplied ({shown}{', ...' if len(unknown) > 3 else ''}); a citation of "
            "unsupplied evidence is refused, never dropped"
        )


@dataclass(frozen=True)
class CitedCapture:
    """What the runner seals for one cited-answer contact."""

    state_content: str
    cited_value_ids: tuple[str, ...]
    record: Mapping[str, object]


def bind_cited_completion(
    text: str,
    *,
    finish_reason: object,
    supplied_value_ids: Sequence[str],
    contact_id: str,
    role_id: str,
    response_text_sha256: str,
) -> CitedCapture:
    """Bind one completion of a cited-answer contact to its sealed form.

    A completion that stopped on its own (``finish_reason == "stop"``) MUST
    satisfy the contract -- under constrained decoding it does by
    construction, and a server that did not honour the grammar is a refusal
    here rather than an envelope delivered as an answer -- and may cite only
    supplied ids. A repeated id is NOT a grammar violation (the grammar
    cannot forbid it): the parser collapses it and the record carries
    ``duplicate_citation_ids_dropped`` -- present only when nonzero, so every
    record without a repeat is byte-identical to its prior self. Any other finish (a ``length`` truncation, which the
    episode's own finite-completion policy disposes of after this seal) is
    sealed verbatim with no citation and the reason recorded, so the seal
    never invents a citation and never blocks the policy that owns the
    disposition.
    """

    supplied = tuple(supplied_value_ids)
    if finish_reason != "stop":
        return CitedCapture(
            state_content=text,
            cited_value_ids=(),
            record={
                "contact_id": contact_id,
                "role_id": role_id,
                "parse": "non-authoritative-finish",
                "finish_reason": finish_reason if isinstance(finish_reason, str) else None,
                "supplied_value_ids": list(supplied),
                "cited_value_ids": [],
                "intent_evidence_ids": [],
                "entity_citations": [],
                "answer_sha256": None,
                "response_text_sha256": response_text_sha256,
            },
        )
    parsed = parse_cited_answer(text)
    validate_citations_supplied(parsed, supplied)
    duplicates = (
        {"duplicate_citation_ids_dropped": parsed.duplicate_ids_dropped}
        if parsed.duplicate_ids_dropped
        else {}
    )
    return CitedCapture(
        state_content=parsed.answer_text,
        cited_value_ids=parsed.cited_value_ids,
        record={
            "contact_id": contact_id,
            "role_id": role_id,
            "parse": "ok",
            "finish_reason": "stop",
            "supplied_value_ids": list(supplied),
            "cited_value_ids": list(parsed.cited_value_ids),
            "intent_evidence_ids": list(parsed.intent_evidence_ids),
            "entity_citations": parsed.citations_json()["entities"],
            "answer_sha256": _sha256(parsed.answer_text),
            "response_text_sha256": response_text_sha256,
            **duplicates,
        },
    )


__all__ = [
    "CITED_ANSWER_NORMALISER_IDS",
    "CITED_ANSWER_RESPONSE_FORMAT_ID",
    "CITED_ANSWER_SCHEMA",
    "CitedAnswer",
    "CitedCapture",
    "DELIVER_CITED_ANSWER_NORMALISE_V3_V1",
    "DELIVER_CITED_ANSWER_V1",
    "EntityCitation",
    "MAX_ENTITY_CITATIONS",
    "MAX_EVIDENCE_IDS_PER_ENTITY",
    "MAX_INTENT_CITATIONS",
    "SOLVER_CITATIONS_RECEIPT_SCHEMA",
    "SolverCitationError",
    "answer_span",
    "bind_cited_completion",
    "cited_answer_response_format",
    "cited_answer_response_format_for",
    "envelope_schema",
    "parse_cited_answer",
    "validate_citations_supplied",
]
