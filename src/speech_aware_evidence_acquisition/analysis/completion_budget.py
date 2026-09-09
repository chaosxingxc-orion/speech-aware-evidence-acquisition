"""Read sealed completion metadata without scoring or changing model outputs."""
from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from ..reproduction.slurp_scoring import parse_slu_response


class CompletionBudgetError(ValueError):
    """A trace or source binding cannot support a trustworthy readout."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _text_metadata(text: object) -> dict[str, Any]:
    if not isinstance(text, str):
        return {"available": False}
    try:
        value = json.loads(text)
        json_valid = True
    except json.JSONDecodeError:
        value, json_valid = None, False
    entity_list = value.get("entities") if isinstance(value, dict) else None
    valid_entities = isinstance(entity_list, list) and all(
        isinstance(entity, dict) and set(entity) == {"type", "filler"}
        and all(isinstance(item, str) for item in entity.values())
        for entity in entity_list
    )
    return {
        "available": True, "sha256": _sha(text),
        "bytes": len(text.encode("utf-8")), "json_syntax_valid": json_valid,
        "json_object": isinstance(value, dict),
        "entities_schema_valid": valid_entities,
        "entities_only_phase_contract": valid_entities and set(value) == {"entities"},
        "slurp_parser_valid": parse_slu_response(text)[-1],
    }


def _index(records: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Mapping]]:
    suffixes = {"MODEL_REQUEST": "/request", "MODEL_RESPONSE": "/response",
                "MODEL_WIRE_RESPONSE": "/wire-response"}
    indexed: dict[str, dict[str, Mapping]] = {name: {} for name in suffixes}
    for record in records:
        channel = record.get("channel")
        if channel not in suffixes:
            continue
        payload, record_id = record.get("payload"), record.get("record_id")
        suffix = suffixes[channel]
        if not isinstance(payload, Mapping) or not isinstance(record_id, str) or not record_id.endswith(suffix):
            raise CompletionBudgetError("invalid trace envelope")
        request_id = record_id[:-len(suffix)]
        if not request_id or request_id in indexed[channel]:
            raise CompletionBudgetError("duplicate or empty request ID")
        if channel == "MODEL_REQUEST":
            payload = payload.get("payload")
            if not isinstance(payload, Mapping) or payload.get("request_id") != request_id:
                raise CompletionBudgetError("nested request ID mismatch")
        if channel == "MODEL_WIRE_RESPONSE" and payload.get("request_id") != request_id:
            raise CompletionBudgetError("wire request ID mismatch")
        indexed[channel][request_id] = payload
    requests = indexed["MODEL_REQUEST"]
    if not requests or any(set(indexed[name]) - set(requests) for name in suffixes if name != "MODEL_REQUEST"):
        raise CompletionBudgetError("missing request or orphan response")
    sample_ids = [value.get("sample_id") for value in requests.values()]
    if any(not isinstance(sid, str) or not sid for sid in sample_ids) or len(set(sample_ids)) != len(sample_ids):
        raise CompletionBudgetError("duplicate or invalid sample ID")
    return indexed


def _wire(payload: Mapping | None) -> tuple[dict[str, Any], str | None]:
    if payload is None:
        return {"available": False, "finish_reason": None}, None
    try:
        raw = base64.b64decode(payload["response_b64"], validate=True)
    except (KeyError, ValueError, TypeError, binascii.Error) as error:
        raise CompletionBudgetError("invalid raw response base64") from error
    digest = hashlib.sha256(raw).hexdigest()
    if digest != payload.get("response_sha256"):
        raise CompletionBudgetError("raw response hash mismatch")
    result: dict[str, Any] = {"available": True, "sha256": digest, "bytes": len(raw),
                              "finish_reason": None, "response_json_valid": False}
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return result, None
    result["response_json_valid"] = True
    choices = document.get("choices") if isinstance(document, dict) else None
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        result["response_envelope_valid"] = False
        return result, None
    choice = choices[0]
    message = choice.get("message")
    text = message.get("content") if isinstance(message, dict) else None
    finish = choice.get("finish_reason")
    if "finish_reason" in payload and payload["finish_reason"] != finish:
        raise CompletionBudgetError("wire finish metadata mismatch")
    usage = document.get("usage")
    if not isinstance(usage, dict):
        usage = {}
    details = usage.get("prompt_tokens_details")
    result.update({
        "response_envelope_valid": isinstance(text, str), "finish_reason": finish,
        "text": _text_metadata(text), "usage": usage,
        "cached_tokens": details.get("cached_tokens") if isinstance(details, dict) else None,
        "timings": document.get("timings"),
    })
    return result, text if isinstance(text, str) else None


def analyze_completion_metadata(records: Sequence[Mapping[str, Any]],
                                outputs: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Keep wire, normalized response and delivered output as separate views."""
    indexed = _index(records)
    requests, responses, wires = (indexed[name] for name in
        ("MODEL_REQUEST", "MODEL_RESPONSE", "MODEL_WIRE_RESPONSE"))
    delivered = {}
    for output in outputs:
        rid = output.get("request_id")
        if rid not in requests or rid in delivered or output.get("sample_id") != requests[rid]["sample_id"]:
            raise CompletionBudgetError("delivered output identity mismatch")
        text = output.get("text")
        if not isinstance(text, str) or output.get("response_text_sha256") != _sha(text):
            raise CompletionBudgetError("delivered output hash mismatch")
        delivered[rid] = output
    if outputs and set(delivered) != set(requests):
        raise CompletionBudgetError("incomplete delivered output roster")
    rows = []
    for rid, request in sorted(requests.items(), key=lambda item: item[1]["sample_id"]):
        decoding = request.get("decoding_params")
        limit = decoding.get("max_tokens") if isinstance(decoding, Mapping) else None
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise CompletionBudgetError("request lacks a positive completion ceiling")
        if rid in wires and wires[rid].get("sample_id") != request["sample_id"]:
            raise CompletionBudgetError("wire sample ID mismatch")
        wire, raw_text = _wire(wires.get(rid))
        response = responses.get(rid)
        text, usage = None, {}
        if response is not None:
            text = response.get("text")
            if not isinstance(text, str) or response.get("response_text_sha256") != _sha(text):
                raise CompletionBudgetError("normalized text hash mismatch")
            usage = response.get("usage", {})
            if not isinstance(usage, Mapping):
                raise CompletionBudgetError("normalized usage must be a mapping")
        raw_usage = wire.get("usage", {})
        for field in ("completion_tokens", "prompt_tokens"):
            if field in raw_usage and field in usage and raw_usage[field] != usage[field]:
                raise CompletionBudgetError("wire and normalized usage disagree")
        completion = raw_usage.get("completion_tokens", usage.get("completion_tokens"))
        if completion is not None and (isinstance(completion, bool) or not isinstance(completion, int) or completion < 0):
            raise CompletionBudgetError("invalid completion token count")
        finish = wire.get("finish_reason")
        output_text = delivered[rid]["text"] if rid in delivered else None
        rows.append({
            "request_id": rid, "sample_id": request["sample_id"], "max_tokens": limit,
            "completion_tokens": completion,
            "prompt_tokens": raw_usage.get("prompt_tokens", usage.get("prompt_tokens")),
            "at_cap": completion == limit if completion is not None else None,
            "actual_length_stop": finish == "length" if finish is not None else None,
            "stop_reason": finish, "wire": wire, "normalized": _text_metadata(text),
            "delivered": _text_metadata(output_text),
            "raw_matches_normalized": raw_text == text if raw_text is not None and text is not None else None,
            "normalized_matches_delivered": text == output_text if text is not None and output_text is not None else None,
        })
    return {"schema": "saea-completion-budget-metadata-v1", "rows": rows,
            "row_count": len(rows), "output_rows": len(outputs)}


def compare_request_payload_sets(left: Sequence[Mapping[str, Any]],
                                 right: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Reject any comparison change except request ID, slot ID and token ceiling."""
    def by_sample(records):
        return {value["sample_id"]: value for value in _index(records)["MODEL_REQUEST"].values()}
    a, b = by_sample(left), by_sample(right)
    if set(a) != set(b):
        raise CompletionBudgetError("paired sample sets differ")
    for sid in a:
        def cleaned(payload):
            value = copy.deepcopy(dict(payload))
            value.pop("request_id")
            decoding = value.get("decoding_params")
            if not isinstance(decoding, dict):
                raise CompletionBudgetError("missing decoding parameters")
            decoding.pop("id_slot", None)
            decoding.pop("max_tokens", None)
            return value
        if cleaned(a[sid]) != cleaned(b[sid]):
            raise CompletionBudgetError(f"unregistered paired request difference for {sid}")
    return {"sample_count": len(a), "payloads_equal_except_allowed": True}
