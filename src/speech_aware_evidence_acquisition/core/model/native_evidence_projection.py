"""Pure, opt-in references to exact knowledge bodies visible in the same request."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping

from ..base import NATIVE_EVIDENCE_PROJECTIONS
from . import FrozenCoreError
from .native_framework_history import native_tool_result_message

POLICY_ID = "native-knowledge-reference-v1"
RECEIPT_SCHEMA = "saea-native-knowledge-reference-projection-v1"


def _refuse(message):
    raise FrozenCoreError("native knowledge projection: " + message)


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _hash(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _identity(block):
    if not isinstance(block, Mapping):
        _refuse("evidence is not a mapping")
    values = tuple(block.get(key) for key in ("evidence_id", "source_uri", "content"))
    if not all(isinstance(value, str) and value for value in values):
        _refuse("evidence requires nonempty ID, source URI and full content")
    return (*values[:2], hashlib.sha256(values[2].encode("utf-8")).hexdigest())


def _tool_content(message):
    try:
        content = json.loads(message["content"])
    except (KeyError, TypeError, ValueError) as exc:
        raise FrozenCoreError("native knowledge projection: invalid tool JSON") from exc
    if (not isinstance(content, Mapping)
            or not isinstance(content.get("result"), Mapping)
            or not isinstance(content.get("evidence"), list)):
        _refuse("tool content lacks canonical result and evidence")
    return content


def _local_result_documents(messages, local_results):
    documents = {}
    previous_index = -1
    for index, document in local_results:
        if (not isinstance(index, int) or isinstance(index, bool)
                or index <= previous_index or index >= len(messages)
                or not isinstance(document, Mapping)):
            _refuse("local result indices must be unique, ordered and in bounds")
        if messages[index] != native_tool_result_message(document):
            _refuse("local tool message differs from its source document")
        documents[index] = document
        previous_index = index

    return documents


def project_native_knowledge_references(*, payload, messages, local_results):
    """Reference only prior visible full bodies; leave canonical observations intact.

    The framework caller validates source authority and complete tool groups first.
    Local results bind message positions to full dispatcher documents, independently
    of whether a tool call ID has been reused in another round.
    """
    rendered = copy.deepcopy(messages)
    documents = _local_result_documents(messages, local_results)

    # Exact native text parts are required. A substring, an observation, or an
    # ambiguous source binding cannot establish visible knowledge.
    base_parts = {}
    for field in ("supplied_evidence", "retrieved_evidence"):
        for block in payload.get(field, []):
            identity = _identity(block)
            tag = f"[evidence {block['evidence_id']}] {block['content']}"
            base_parts.setdefault(tag, set()).add(identity)

    visible = {}
    source_hashes = {}
    placements = []

    def remember(identity, location):
        previous_hash = source_hashes.setdefault(identity[:2], identity[2])
        if previous_hash != identity[2]:
            _refuse("conflicting content for one evidence source identity")
        visible.setdefault(identity, location)

    for message_index, message in enumerate(rendered):
        if message.get("role") == "user" and isinstance(message.get("content"), list):
            for part_index, part in enumerate(message["content"]):
                if not isinstance(part, Mapping) or part.get("type") != "text":
                    continue
                identities = base_parts.get(part.get("text"), set())
                if len(identities) == 1:
                    identity = next(iter(identities))
                    remember(identity, {
                        "message_index": message_index,
                        "content_part_index": part_index,
                        "content_sha256": identity[2],
                        "visible_in": "Earlier user evidence text part "
                                      f"[evidence {identity[0]}]",
                    })
            continue
        if message.get("role") != "tool":
            continue
        content = _tool_content(message)
        if content["result"].get("knowledge_view") not in {"text", "paired"}:
            continue
        document = documents.get(message_index)
        changed = False
        for evidence_index, block in enumerate(content["evidence"]):
            # References never become reference targets.
            if isinstance(block, Mapping) and "content" not in block:
                continue
            identity = _identity(block)
            previous_hash = source_hashes.get(identity[:2])
            if previous_hash is not None and previous_hash != identity[2]:
                _refuse("conflicting content for one evidence source identity")
            location = visible.get(identity)
            if document is not None:
                placement = {
                    "message_index": message_index,
                    "evidence_index": evidence_index,
                    "evidence_id": identity[0],
                    "source_uri": identity[1],
                    "content_sha256": identity[2],
                    "source_document_sha256": _hash(document),
                    "disposition": "reference" if location is not None else "retained",
                }
                if location is not None:
                    block.pop("content")
                    block["reference"] = copy.deepcopy(location)
                    placement["target"] = copy.deepcopy(location)
                    changed = True
                placements.append(placement)
            if location is None:
                remember(identity, {
                    "message_index": message_index,
                    "evidence_index": evidence_index,
                    "content_sha256": identity[2],
                    "visible_in": "Earlier tool result "
                                  + str(message.get("tool_call_id", "")),
                })
        if changed:
            content["evidence_projection"] = {
                "policy_id": POLICY_ID,
                "instruction": (
                    "Referenced evidence retains the full content at the indicated "
                    "earlier message in this request. Use that content with this "
                    "tool's selected IDs and result. Re-selection is not an "
                    "independent observation."
                ),
            }
            message["content"] = json.dumps(content, ensure_ascii=False, sort_keys=True)

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "policy_id": POLICY_ID,
        "source_payload_sha256": _hash(payload),
        "source_messages_sha256": _hash(messages),
        "projected_messages_sha256": _hash(rendered),
        "referenced_blocks": sum(p["disposition"] == "reference" for p in placements),
        "retained_blocks": sum(p["disposition"] == "retained" for p in placements),
        "placements": placements,
        "local_tool_messages": [{
            "message_index": index,
            "source_document_sha256": _hash(document),
            "source_message_sha256": _hash(messages[index]),
            "projected_message_sha256": _hash(rendered[index]),
        } for index, document in documents.items()],
    }
    return rendered, receipt


NATIVE_EVIDENCE_PROJECTIONS.register(
    "native-knowledge-reference-v1", project_native_knowledge_references,
)
