"""Derived candidate-specific knowledge bodies at the validated wire boundary."""

from __future__ import annotations

import copy
import hashlib
import json

from ..base import NATIVE_EVIDENCE_PROJECTIONS
from . import FrozenCoreError
from .native_evidence_projection import (
    _hash, _identity, _local_result_documents, _tool_content,
)

POLICY_ID = "native-candidate-slot-view-v1"


def _bind_config(values, data_root):
    from ...rails.slot_binding_view import bind_slot_view_context

    return bind_slot_view_context(values, data_root)


def _validate_context(context):
    from ...rails.slot_binding_view import validate_slot_view_context

    validate_slot_view_context(context)


def _scope_for_payload(payload, context):
    from ...rails.slot_binding_view import scope_for_payload

    return scope_for_payload(payload, context)


def _project_slot_value(context, **kwargs):
    from ...rails.slot_binding_view import project_slot_value

    return project_slot_value(context, **kwargs)


def project_native_slot_binding_view(
    *, payload, messages, local_results, projection_context,
):
    """Keep full observations immutable and expose clearly labeled derived views.

    No selection, retrieval, answer generation, or tokenization occurs here.
    The framework caller has validated native source authority and complete groups.
    """
    try:
        _validate_context(projection_context)
        scope = _scope_for_payload(payload, projection_context)
    except ValueError as error:
        raise FrozenCoreError("native slot view context: " + str(error)) from error
    documents = _local_result_documents(messages, local_results)
    rendered = copy.deepcopy(messages)
    values = set(projection_context.value_ids)
    parts_by_text = {}
    for field in ("supplied_evidence", "retrieved_evidence"):
        for block in payload.get(field, []):
            if block.get("evidence_id") not in values:
                continue
            identity = _identity(block)
            text = f"[evidence {block['evidence_id']}] {block['content']}"
            parts_by_text.setdefault(text, {})[identity] = block
    placements = []

    def derive(block, location):
        try:
            text, audit = _project_slot_value(
                projection_context, evidence_id=block["evidence_id"],
                source_uri=block["source_uri"], content=block["content"], scope=scope,
            )
        except ValueError as error:
            raise FrozenCoreError("native slot view source: " + str(error)) from error
        if audit is None:
            return None
        changed = text != block["content"]
        original_hash = hashlib.sha256(block["content"].encode("utf-8")).hexdigest()
        receipt = {
            **location, "evidence_id": block["evidence_id"],
            "source_uri": block["source_uri"], "source_content_sha256": original_hash,
            "disposition": "projected" if changed else "retained", "view_audit": audit,
        }
        if not changed:
            placements.append(receipt)
            return None
        view = {
            "policy_id": POLICY_ID,
            "source_content_sha256": original_hash,
            "scope_candidate_ids": list(scope["candidate_ids"]),
            "content": text,
        }
        view_hash = _hash(view)
        view["view_sha256"] = view_hash
        receipt["view_sha256"] = view_hash
        placements.append(receipt)
        return view

    for message_index, message in enumerate(rendered):
        if message.get("role") == "user" and isinstance(message.get("content"), list):
            for part_index, part in enumerate(message["content"]):
                if not isinstance(part, dict) or part.get("type") != "text":
                    continue
                sources = parts_by_text.get(part.get("text"))
                if not sources:
                    continue
                if len(sources) != 1:
                    raise FrozenCoreError("native slot view has ambiguous base source")
                block = next(iter(sources.values()))
                view = derive(block, {
                    "surface": "base-evidence", "message_index": message_index,
                    "content_part_index": part_index,
                })
                if view is not None:
                    part["text"] = (
                        f"[evidence {block['evidence_id']}] "
                        "[derived knowledge view; original evidence ID identifies the source. "
                        "Only unrelated intent bindings were omitted; all global guidance "
                        "is retained. Omission does not restrict legal intents or slots.] "
                        + json.dumps(view, ensure_ascii=False, sort_keys=True)
                    )
            continue
        if message.get("role") != "tool":
            continue
        content = _tool_content(message)
        if content["result"].get("knowledge_view") not in {"text", "paired"}:
            continue
        changed = False
        for evidence_index, block in enumerate(content["evidence"]):
            if (block.get("evidence_id") not in values or "content" not in block):
                continue
            view = derive(block, {
                "surface": "tool-result", "message_index": message_index,
                "evidence_index": evidence_index,
                **({"source_document_sha256": _hash(documents[message_index])}
                   if message_index in documents else {}),
            })
            if view is not None:
                block.pop("content")
                block["derived_view"] = view
                changed = True
        if changed:
            content["evidence_projection"] = {
                "policy_id": POLICY_ID,
                "instruction": (
                    "Derived views preserve all global guidance and retain the semantic "
                    "roles for the stated intent scope. Original IDs and URIs identify "
                    "sources, not full visible copies. Omission is not a legality rule."
                ),
            }
            message["content"] = json.dumps(content, ensure_ascii=False, sort_keys=True)

    return rendered, {
        "schema": "saea-native-candidate-slot-view-receipt-v1",
        "policy_id": POLICY_ID, "context_sha256": projection_context.context_sha256,
        "source_payload_sha256": _hash(payload),
        "source_messages_sha256": _hash(messages),
        "projected_messages_sha256": _hash(rendered),
        "scope": scope, "placements": placements,
        "projected_occurrences": sum(p["disposition"] == "projected" for p in placements),
        "retained_target_occurrences": sum(p["disposition"] == "retained" for p in placements),
        "local_tool_messages": [{
            "message_index": index, "source_document_sha256": _hash(document),
            "source_message_sha256": _hash(messages[index]),
            "projected_message_sha256": _hash(rendered[index]),
        } for index, document in documents.items()],
    }


project_native_slot_binding_view.bind_config = _bind_config
project_native_slot_binding_view.validate_context = _validate_context
NATIVE_EVIDENCE_PROJECTIONS.register(
    "native-candidate-slot-view-v1", project_native_slot_binding_view,
)
