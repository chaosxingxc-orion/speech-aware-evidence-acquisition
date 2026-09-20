#!/usr/bin/env python3
"""CLI: the model-free WIRE CHECK of item E21w -- the LIVE runner wiring of
the knowledge INDEX (item E21, the knowledge index, NOT the Earnings-21
carrier). The E17 Probe A form, one level deeper than
``scripts/slurp_knowledge_index_render_proof.py``: the render proof drove the
RAIL over sealed payloads, this drives the PRODUCTION RUNNER SEAM --
``rails.runner._agent_messages`` and its ``_index_content`` -- over the same
sealed rows, with a fake transport that is never called.

MODEL-FREE, and the refusal is structural: this script opens no socket, loads
no tokenizer, builds no encoder, imports no serving client and reads the
sealed run directories READ-ONLY. Profile ``model-free-check``. Zero model,
tool, tokenizer, encoder, scorer, server and network contacts.

WHAT IT PROVES, per arm, ON and OFF:

W1. OFF is the sealed request. With the key absent the production seam,
    fed one sealed row's own inputs, re-composes that row's messages BYTE
    FOR BYTE, and the rail re-composes the payload to the sealed
    ``payload_sha256``.
W2. ONE rendered system message over every contact of a row and over every
    row of the arm (ON) -- the constancy claim, E17's own
    ``distinct_tool_schemas_sha256 == 1`` restated for the prefix.
W3. ON differs from OFF in EXACTLY the system suffix and the evidence
    parts. Every other differing payload key is a FINDING and is named.
W4. The seam and the rail agree: the content parts the live runner composes
    are exactly the ``supplied_evidence`` items
    ``rails.knowledge_index.apply_to_payload`` composes, in the same order.
W5. Provenance: one ``evidence_provenance`` row per pointer/expansion part,
    through the production ``rails.core_client._supply_provenance``, naming
    the released view rather than the rails message.
W6. The truncation property: at ``expansion_budget.slot_card = 0`` no byte
    before the expansion block moves.
W7. Every contact's receipt row is populated, and the framework contact
    envelope the seam rewrote still passes
    ``core.model.native_framework_history.validate_native_framework_contact``.
W8. The E20 ladder: one caller drives both ladders -- the index's own
    expansions-from-the-tail-then-the-pointer-block order is what
    ``rails.context_fit.droppable_items`` returns for an index-armed
    request, and ``apply_drops`` executes it.

THE ESTIMATOR is E17's and the render proof's, unchanged: the rendered
stream is the system message (the ``tools`` array included, because the
Qwen3-Omni template renders it inside the system message) followed by every
user content part in wire order; prompt tokens are ``chars / 4.60``; cached
tokens are the longest common character prefix with the previous request on
the same pinned ``id_slot``, over 4.60. EVERY number in the per-position
table is DERIVED, exactly as E17's own 50.1 % is. No tokenizer is contacted.

NOTHING IS PERSISTED BUT DIGESTS AND COUNTS. No utterance text, no reference
transcript, no gold and no rendered prompt body is written anywhere.

Usage::

    python scripts/knowledge_index_wire_check.py \\
        --snapshot <scratch>/knowledge/slurp/semantic/slurp-knowledge-index-v1/snapshot.json \\
        --release  <scratch>/knowledge/slurp/semantic/slurp-knowledge-index-v1/release.json \\
        --view-root <scratch> --out <scratch>/wire-check.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.model.native_framework_history import (  # noqa: E402
    project_native_framework_history,
    validate_native_framework_contact,
)
from speech_aware_evidence_acquisition.core.model.native_history import (  # noqa: E402
    project_native_history,
)
from speech_aware_evidence_acquisition.core.model.transport import (  # noqa: E402
    _assert_agent_history_suffix,
    _ordered_speech_feature_content,
    _speech_history_texts,
)
from speech_aware_evidence_acquisition.rails import runner as rails_runner  # noqa: E402
from speech_aware_evidence_acquisition.rails.context_fit import (  # noqa: E402
    CompactableRequest, apply_drops, droppable_items,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    _supply_provenance,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KeyFacet, KnowledgeSnapshot, QueryState, ValueBundle,
)
from speech_aware_evidence_acquisition.rails.knowledge_index import (  # noqa: E402
    CHARS_PER_TOKEN,
    INDEX_EXPANSION_BLOCK,
    INDEX_POINTER_BLOCK,
    POINTER_BLOCK_EVIDENCE_ID,
    apply_to_payload,
    build_knowledge_index_binding,
    canonical_json,
    contact_receipt,
    estimated_tokens,
    parse_knowledge_index_config,
    sha256_text,
)

PROMPT_ORDER = "speech-query-prefix-v2"
ROLE_POSITIONS = ("perception", "solver", "reviewer-1", "reviewer-2", "planner")
ROLE_KINDS = ("perception", "solver", "reviewer", "reviewer", "planner")
ROLE_POSITIONS_4 = ("perception", "solver", "reviewer", "planner")
ROLE_KINDS_4 = ("perception", "solver", "reviewer", "planner")
CONTACTS_PER_ROW = 5


def set_contacts_per_row(count: int) -> None:
    """Select the five-contact (tool-bearing) or four-contact (tool-free, repair form 0-B) row shape."""
    global CONTACTS_PER_ROW, ROLE_POSITIONS, ROLE_KINDS
    if count == 4:
        ROLE_POSITIONS, ROLE_KINDS = ROLE_POSITIONS_4, ROLE_KINDS_4
    elif count != 5:
        raise WireCheckError(f"unsupported contacts per row: {count}")
    CONTACTS_PER_ROW = count

#: The two sealed arms this check reads, both READ-ONLY and hashes only.
B1_RUN = "SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2"
B1_ATTEMPT = (
    "attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-recovery-v2"
)
SMOKE_RUN = "SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-V2"
SMOKE_ATTEMPT = "attempt-slurp-native-exemplars-k20-anchor-smoke-4-generation-v2"

#: The payload keys an armed contact is ALLOWED to move. Anything else that
#: differs between the ON and OFF arms is a finding, named in the receipt.
EXPECTED_ARMED_KEYS = frozenset(
    {"task_instruction", "history", "supplied_evidence", "evidence_provenance"}
)

KEY_PREFIX = "key:"
SNAPSHOT_SCHEME = "knowledge-snapshot://"


class WireCheckError(SystemExit):
    pass


# ---------------------------------------------------------------------------
# Reading the sealed arms, read-only.
# ---------------------------------------------------------------------------


def read_rows(trace_path: Path, *, rows: int) -> "OrderedDict[str, list[dict]]":
    """The first ``rows`` distinct sample ids in flight order, 5 contacts each."""

    by_sample: "OrderedDict[str, list[dict]]" = OrderedDict()
    with trace_path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("channel") != "MODEL_REQUEST":
                continue
            envelope = record["payload"]
            payload = envelope["payload"]
            sample_id = payload["sample_id"]
            if sample_id not in by_sample and len(by_sample) >= 4 * rows:
                continue  # scan past incomplete rows (finite completions, revisions) up to 4x rows
            by_sample.setdefault(sample_id, []).append(
                {
                    "record_id": record["record_id"],
                    "payload": payload,
                    "payload_sha256": envelope["payload_sha256"],
                }
            )
            if sum(1 for items in by_sample.values() if len(items) >= CONTACTS_PER_ROW) >= rows and len(by_sample) >= 4 * rows:
                break
    complete = OrderedDict(
        (sample_id, contacts[:CONTACTS_PER_ROW])
        for sample_id, contacts in by_sample.items()
        if len(contacts) >= CONTACTS_PER_ROW
    )
    if len(complete) < rows:
        raise WireCheckError(
            f"REFUSED: only {len(complete)} complete {CONTACTS_PER_ROW}-contact rows were found in "
            f"{trace_path}; this check needs {rows}"
        )
    return OrderedDict(list(complete.items())[:rows])


# ---------------------------------------------------------------------------
# Rebuilding ONE sealed contact's own inputs to the production seam.
# ---------------------------------------------------------------------------


class _SealedAdapter:
    """The TaskAdapter seam, bound to this contact's own sealed prompt.

    ``rails.runner._agent_messages`` calls ``assemble_prompt`` and nothing
    else on the adapter; handing it the sealed system message is what makes
    the OFF arm a byte-identity claim rather than a re-derivation.
    """

    def __init__(self, system_text: str) -> None:
        self._system_text = system_text

    def assemble_prompt(self, _sample, _selection):
        return (
            {"role": "system", "content": self._system_text},
            {"role": "user", "content": []},
        )


def rebuild_inputs(payload: dict) -> dict:
    """The snapshot, query state, states and value renderer of ONE contact.

    Every field is reconstructed from the contact's OWN sealed request: the
    key facets from its ``key:`` evidence items (and their sealed
    ``knowledge-snapshot://<sha>/<facet>`` uris, so the re-rendered uri is
    the sealed one), the values from its ``value`` items in sealed order,
    and the agent states from its own history. No gold, no transcript and no
    other row is read.
    """

    supplied = list(payload.get("supplied_evidence") or ())
    keys = [item for item in supplied if item.get("knowledge_role") == "key"]
    values = [item for item in supplied if item.get("knowledge_role") == "value"]
    if len(keys) + len(values) != len(supplied):
        raise WireCheckError(
            "REFUSED: a sealed contact carries an evidence item with no "
            "knowledge_role; this check only reads the typed native arm"
        )
    snapshot_sha256 = ""
    facets = []
    facet_ids = []
    for item in keys:
        evidence_id = str(item["evidence_id"])
        if not evidence_id.startswith(KEY_PREFIX):
            raise WireCheckError("REFUSED: a sealed key item is not key-prefixed")
        facet_id = evidence_id[len(KEY_PREFIX):]
        source = str(item.get("source_uri") or "")
        if source.startswith(SNAPSHOT_SCHEME):
            snapshot_sha256 = source[len(SNAPSHOT_SCHEME):].split("/", 1)[0]
        facet_ids.append(facet_id)
        facets.append(
            KeyFacet(
                facet_id=facet_id, dimension="content",
                representation_kind="text",
                representation=str(item["content"]),
                source_sample_ids=("train-0",),
            )
        )
    value_ids = [str(item["evidence_id"]) for item in values]
    bundles = [
        ValueBundle(
            value_id=str(item["evidence_id"]), content=str(item["content"]),
            associated_facet_ids=(facet_ids[0],) if facet_ids else ("facet:0",),
            source_sample_ids=("train-0",), provenance_refs=("sealed",),
        )
        for item in values
    ]
    if not facet_ids:
        facets.append(
            KeyFacet(
                facet_id="facet:0", dimension="content",
                representation_kind="text", representation="unused",
                source_sample_ids=("train-0",),
            )
        )
    snapshot = KnowledgeSnapshot(
        snapshot_id="sealed-wire-check",
        source_split_identity_hash="0" * 64,
        source_sample_ids=("train-0",),
        builder_policy_id="sealed-wire-check",
        facets=tuple(facets), values=tuple(bundles),
    )
    query_descriptor = next(
        part for part in payload["speech_feature_parts"] if part["role"] == "query"
    )
    query_state = QueryState(
        query_id=f"wire:{payload['sample_id']}",
        query_sample_id=str(payload["sample_id"]),
        speech_packet_id=str(query_descriptor["packet_id"]),
        speech_packet_sha256=str(query_descriptor["sha256"]),
        use_split_identity_hash="0" * 64,
        visible_facet_ids=tuple(facet_ids),
        retrieved_value_ids=tuple(value_ids),
    )
    states = [
        dict(entry) for entry in payload.get("history") or ()
        if isinstance(entry, dict) and entry.get("role") != "control"
    ]
    value_parts = [
        {
            "type": "text", "text": str(item["content"]),
            "evidence_id": str(item["evidence_id"]),
            "source_uri": str(item.get("source_uri") or ""),
            "knowledge_role": "value",
        }
        for item in values
    ]
    return {
        "adapter": _SealedAdapter(str(payload["task_instruction"])),
        "task_contract": str(payload["task_instruction"]),
        "snapshot": snapshot,
        "snapshot_sha256": snapshot_sha256,
        "query_state": query_state,
        "agent_states": states,
        "value_renderer": lambda _s, _q, _a, parts=value_parts: [
            dict(part) for part in parts
        ],
        "sealed_value_ids": value_ids,
    }


class _State:
    """The sealed history entry shape ``_agent_messages`` forwards verbatim."""

    def __init__(self, document: dict) -> None:
        self._document = document
        self.state_kind = document.get("state_kind")
        self.content = document.get("content")

    def as_json(self) -> dict:
        return dict(self._document)


def run_seam(inputs: dict, *, index, role_kind: str | None):
    """ONE contact through the PRODUCTION seam. Returns (messages, record)."""

    record: dict = {}

    def sink(assembly, selection, provenance):
        record.update(
            assembly=assembly, selection=selection, provenance=provenance,
        )

    messages = rails_runner._agent_messages(
        adapter=inputs["adapter"],
        sample=None,
        task_contract=inputs["task_contract"],
        snapshot=inputs["snapshot"],
        snapshot_sha256=inputs["snapshot_sha256"],
        query_state=inputs["query_state"],
        agent_states=tuple(_State(row) for row in inputs["agent_states"]),
        knowledge_value_renderer=inputs["value_renderer"],
        knowledge_index=index,
        index_role_kind=role_kind,
        index_sink=None if index is None else sink,
    )
    return messages, record


# ---------------------------------------------------------------------------
# The production render path, offline (the render proof's own form).
# ---------------------------------------------------------------------------


def render_body(payload: dict, *, tool_schemas: list | None) -> dict:
    evidence_texts: list[str] = []
    knowledge_roles: list[str | None] = []
    for field in ("supplied_evidence", "retrieved_evidence"):
        for item in payload.get(field, ()):
            evidence_texts.append(f"[evidence {item['evidence_id']}] {item['content']}")
            knowledge_roles.append(item.get("knowledge_role"))
    feature_parts = [
        {"type": "input_speech_features", "speech_features": dict(descriptor)}
        for descriptor in payload["speech_feature_parts"]
    ]
    state_texts = _speech_history_texts(payload.get("history", []))
    content = _ordered_speech_feature_content(
        prompt_order=PROMPT_ORDER,
        evidence_texts=evidence_texts,
        feature_parts=feature_parts,
        state_texts=state_texts,
        knowledge_roles=(knowledge_roles if any(knowledge_roles) else ()),
    )
    _assert_agent_history_suffix(
        prompt_order=PROMPT_ORDER, content=content, state_texts=state_texts
    )
    messages = [
        {"role": "system", "content": payload["task_instruction"]},
        {"role": "user", "content": content},
    ]
    projection = project_native_framework_history(
        payload=payload, messages=messages, state_texts=state_texts,
        evidence_projection=None, projection_context=None,
        receipt_sink=lambda _receipt: None,
    )
    if projection is None:
        messages, _descriptors = project_native_history(
            payload=payload, messages=messages, state_texts=state_texts
        )
    else:
        messages, _descriptors = projection
    body: dict[str, object] = {"messages": messages}
    if tool_schemas:
        body["tools"] = tool_schemas
    return body


def rendered_stream(body: dict) -> str:
    pieces: list[str] = []
    for index, message in enumerate(body["messages"]):
        content = message["content"]
        if isinstance(content, str):
            pieces.append(content)
        else:
            for part in content:
                if part.get("type") == "text":
                    pieces.append(part["text"])
                else:
                    pieces.append(canonical_json(part))
        if index == 0 and body.get("tools"):
            pieces.append("\n\n# Tools\n" + canonical_json(body["tools"]))
    return "\n".join(pieces)


def system_prefix(body: dict) -> str:
    head = body["messages"][0]["content"]
    if body.get("tools"):
        return head + "\n\n# Tools\n" + canonical_json(body["tools"])
    return head


def common_prefix_chars(left: str, right: str) -> int:
    limit = min(len(left), len(right))
    index = 0
    while index < limit and left[index] == right[index]:
        index += 1
    return index


def payload_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _median(values: list[int]) -> int:
    ordered = sorted(values)
    if not ordered:
        return 0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


# ---------------------------------------------------------------------------
# The check itself.
# ---------------------------------------------------------------------------


def check_arm(rows, binding, reduced_binding, *, label: str) -> dict:
    findings: list[dict] = []
    off_identical = 0
    off_seam_identical = 0
    contacts_checked = 0
    system_digests: set[str] = set()
    armed_key_sets: set[frozenset] = set()
    receipt_rows: list[dict] = []
    per_position: dict[str, list[dict]] = {name: [] for name in ROLE_POSITIONS}
    slot_last: dict[object, str] = {}
    provenance_rows = 0
    provenance_index_rows = 0
    envelope_ok = 0
    truncation_violations: list[dict] = []
    ladder_samples: list[dict] = []

    for sample_id, contacts in rows.items():
        constant_tools: list = []
        for contact in contacts:
            schemas = contact["payload"].get("tool_schemas") or []
            if schemas:
                constant_tools = schemas
                break
        for position, contact in enumerate(contacts):
            payload = contact["payload"]
            role_kind = ROLE_KINDS[position]
            contacts_checked += 1
            inputs = rebuild_inputs(payload)

            # --- W1: the OFF arm is the sealed request, byte for byte. ---
            off_messages, _ = run_seam(inputs, index=None, role_kind=None)
            sealed_parts = [
                {
                    "type": "text", "text": str(item["content"]),
                    "evidence_id": str(item["evidence_id"]),
                    "source_uri": str(item.get("source_uri") or ""),
                    "knowledge_role": item.get("knowledge_role"),
                }
                for item in payload.get("supplied_evidence") or ()
            ]
            seam_parts = [
                part for part in off_messages[1]["content"]
                if part.get("type") == "text"
            ]
            if (
                off_messages[0]["content"] == payload["task_instruction"]
                and seam_parts == sealed_parts
            ):
                off_seam_identical += 1
            else:
                findings.append(
                    {
                        "kind": "off-seam-differs",
                        "contact": contact["record_id"],
                        "system_equal": (
                            off_messages[0]["content"] == payload["task_instruction"]
                        ),
                        "parts_equal": seam_parts == sealed_parts,
                    }
                )
            off_payload = apply_to_payload(payload, index_text=None, assembly=None)
            if payload_digest(off_payload) == contact["payload_sha256"]:
                off_identical += 1
            else:
                findings.append(
                    {"kind": "off-payload-differs", "contact": contact["record_id"]}
                )

            # --- The ON arm, through the same production seam. ---
            on_messages, record = run_seam(
                inputs, index=binding, role_kind=role_kind
            )
            assembly = record["assembly"]
            on_payload = apply_to_payload(
                payload, index_text=binding.index_text, assembly=assembly
            )

            # --- W4: the seam and the rail compose the same items. ---
            seam_on = [
                part for part in on_messages[1]["content"]
                if part.get("type") == "text"
            ]
            rail_on = [
                {
                    "type": "text", "text": str(item["content"]),
                    "evidence_id": str(item["evidence_id"]),
                    "source_uri": str(item.get("source_uri") or ""),
                    "knowledge_role": item.get("knowledge_role"),
                }
                for item in on_payload["supplied_evidence"]
            ]
            seam_on_compare = [
                {**part, "source_uri": part.get("source_uri") or ""}
                for part in seam_on
            ]
            if seam_on_compare != rail_on:
                findings.append(
                    {
                        "kind": "seam-and-rail-differ",
                        "contact": contact["record_id"],
                        "seam_ids": [part["evidence_id"] for part in seam_on],
                        "rail_ids": [item["evidence_id"] for item in rail_on],
                    }
                )

            # --- W3: ON differs from OFF in exactly the declared keys. ---
            differing = frozenset(
                key for key in set(on_payload) | set(off_payload)
                if on_payload.get(key) != off_payload.get(key)
            )
            armed_key_sets.add(differing)
            for key in sorted(differing - EXPECTED_ARMED_KEYS):
                findings.append(
                    {
                        "kind": "unexpected-armed-key",
                        "contact": contact["record_id"], "key": key,
                    }
                )

            # --- W5: provenance, through the production composer. ---
            for index, part in enumerate(seam_on):
                row = _supply_provenance(
                    part, part["text"], request_id="wire-0001", index=index,
                )
                provenance_rows += 1
                if row["lock_key"] == "knowledge-index":
                    provenance_index_rows += 1
                    expected = (
                        f"{binding.table.view_id}/{part['evidence_id']}"
                    )
                    if row["relpath"] != expected:
                        findings.append(
                            {
                                "kind": "provenance-relpath",
                                "contact": contact["record_id"],
                                "relpath": row["relpath"],
                            }
                        )
            expected_index_rows = len(assembly.expansions) + 1
            actual_index_rows = sum(
                1 for part in seam_on
                if str(part.get("source_uri") or "").startswith("knowledge-index://")
            )
            if actual_index_rows != expected_index_rows:
                findings.append(
                    {
                        "kind": "provenance-count",
                        "contact": contact["record_id"],
                        "expected": expected_index_rows,
                        "actual": actual_index_rows,
                    }
                )

            # --- W7: the rewritten framework envelope still validates. ---
            try:
                validate_native_framework_contact(on_payload)
                envelope_ok += 1
            except Exception as error:  # noqa: BLE001 - reported, not raised
                findings.append(
                    {
                        "kind": "framework-envelope",
                        "contact": contact["record_id"], "error": str(error),
                    }
                )

            # --- W2 and the per-position table. ---
            body = render_body(on_payload, tool_schemas=constant_tools)
            stream = rendered_stream(body)
            prefix = system_prefix(body)
            system_digests.add(sha256_text(prefix))
            slot = payload.get("decoding_params", {}).get("id_slot")
            previous = slot_last.get(slot)
            cached_chars = (
                common_prefix_chars(previous, stream) if previous is not None else 0
            )
            slot_last[slot] = stream
            prompt_tokens = estimated_tokens(len(stream))
            cached_tokens = estimated_tokens(cached_chars)
            row = contact_receipt(
                contact_id=contact["record_id"], role_id=role_kind,
                assembly=assembly, system_message=prefix,
                index_text=binding.index_text, cited_ids=(), table=binding.table,
            )
            row.update(
                position=ROLE_POSITIONS[position],
                selection=dict(record["provenance"]),
                budget=binding.plan.budget_for(role_kind).as_json(),
                predicted_prompt_tokens=prompt_tokens,
                predicted_cached_tokens=cached_tokens,
                predicted_prefilled_tokens=max(prompt_tokens - cached_tokens, 0),
            )
            receipt_rows.append(row)
            per_position[ROLE_POSITIONS[position]].append(row)

            # --- W6: the truncation property. ---
            reduced_messages, reduced_record = run_seam(
                inputs, index=reduced_binding, role_kind=role_kind
            )
            reduced_parts = [
                part for part in reduced_messages[1]["content"]
                if part.get("type") == "text"
            ]
            kept = len(reduced_parts)
            if reduced_messages[0]["content"] != on_messages[0]["content"]:
                truncation_violations.append(
                    {"contact": contact["record_id"], "reason": "the prefix moved"}
                )
            elif reduced_parts != seam_on[:kept]:
                truncation_violations.append(
                    {
                        "contact": contact["record_id"],
                        "reason": "a part before the truncation moved",
                    }
                )

            # --- W8: the E20 ladder, driven by one caller. ---
            if position == 1 and not ladder_samples:
                view = CompactableRequest(
                    content=tuple(on_messages[1]["content"]),
                    agent_states=(),
                    index_assembly=assembly,
                )
                ordered = droppable_items(view)
                index_items = [
                    item for item in ordered
                    if item.block in (INDEX_EXPANSION_BLOCK, INDEX_POINTER_BLOCK)
                ]
                narrowed = apply_drops(view, index_items[:1])
                ladder_samples.append(
                    {
                        "contact": contact["record_id"],
                        "droppable_items": len(ordered),
                        "index_items": [
                            {"block": item.block, "identifier": item.identifier,
                             "tranche": item.tranche}
                            for item in index_items
                        ],
                        "expansions_before_pointer": (
                            [item.block for item in index_items]
                            == [INDEX_EXPANSION_BLOCK] * len(assembly.expansions)
                            + [INDEX_POINTER_BLOCK]
                        ),
                        "tail_first": [
                            item.identifier for item in index_items
                            if item.block == INDEX_EXPANSION_BLOCK
                        ] == [
                            f"value:{item.entry_id}"
                            for item in reversed(assembly.expansions)
                        ],
                        "parts_after_one_drop": len(narrowed.content),
                        "parts_before_one_drop": len(view.content),
                    }
                )

    table_rows = [
        {
            "position": name,
            "contacts": len(per_position[name]),
            "predicted_prompt_tokens_median": _median(
                [row["predicted_prompt_tokens"] for row in per_position[name]]
            ),
            "predicted_prefilled_tokens_median": _median(
                [row["predicted_prefilled_tokens"] for row in per_position[name]]
            ),
        }
        for name in ROLE_POSITIONS
    ]
    receipt = binding.receipt(receipt_rows)
    populated = sum(
        1 for row in receipt_rows
        if row["system_message_sha256"] and row["index_sha256"]
        and row["pointer_block_chars"] > 0
    )
    return {
        "label": label,
        "rows": len(rows),
        "contacts": contacts_checked,
        "W1_off_seam_byte_identical": off_seam_identical,
        "W1_off_payload_sha256_identical": off_identical,
        "W2_distinct_system_message_sha256": len(system_digests),
        "W3_armed_key_sets": [sorted(item) for item in sorted(map(sorted, armed_key_sets))],
        "W3_expected_armed_keys": sorted(EXPECTED_ARMED_KEYS),
        "W5_provenance_rows": provenance_rows,
        "W5_provenance_index_rows": provenance_index_rows,
        "W6_truncation_violations": truncation_violations,
        "W7_framework_envelope_ok": envelope_ok,
        "W7_receipt_rows_populated": populated,
        "W8_ladder": ladder_samples,
        "per_position": table_rows,
        "predicted_prefilled_tokens_per_row": sum(
            row["predicted_prefilled_tokens_median"] for row in table_rows
        ),
        "index_chars": len(binding.index_text),
        "index_tokens_at_4_60": estimated_tokens(len(binding.index_text)),
        "index_sha256": sha256_text(binding.index_text),
        "receipt": {
            key: value for key, value in receipt.items() if key != "contacts"
        },
        "findings": findings,
        "passes": (
            not findings
            and not truncation_violations
            and off_identical == contacts_checked
            and off_seam_identical == contacts_checked
            and len(system_digests) == 1
            and envelope_ok == contacts_checked
            and populated == contacts_checked
        ),
    }


def _pins(view_id: str, release_sha: str, snapshot_sha: str) -> dict:
    base = f"knowledge/slurp/semantic/{view_id}"
    return {
        "view": view_id,
        "release": {
            "relpath": f"{base}/release.json", "root": "data",
            "sha256": release_sha,
        },
        "snapshot": {
            "relpath": f"{base}/snapshot.json", "root": "data",
            "sha256": snapshot_sha,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=20)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--run-id", default=None, help="a sealed arm to check instead of the B1 arm")
    parser.add_argument("--attempt", default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--contacts-per-row", type=int, default=5)
    parser.add_argument("--no-smoke", action="store_true", help="skip the engineering-smoke arm")
    args = parser.parse_args()

    if args.data_root is not None:
        root = Path(args.data_root)
    else:
        from speech_aware_evidence_acquisition.data.lock import data_root

        root = data_root()

    view_id = "slurp-knowledge-index-v1"
    view_dir = args.view_root / "knowledge/slurp/semantic" / view_id
    release_sha = hashlib.sha256(
        (view_dir / "release.json").read_bytes()
    ).hexdigest()
    snapshot_sha = hashlib.sha256(
        (view_dir / "snapshot.json").read_bytes()
    ).hexdigest()
    pins = _pins(view_id, release_sha, snapshot_sha)
    binding = build_knowledge_index_binding(
        knowledge_index_json=canonical_json(
            parse_knowledge_index_config(pins).as_json()
        ),
        data_root=args.view_root,
    )
    reduced_binding = build_knowledge_index_binding(
        knowledge_index_json=canonical_json(
            parse_knowledge_index_config(
                {**pins, "expansion_budget": {"slot_card": 0}}
            ).as_json()
        ),
        data_root=args.view_root,
    )

    set_contacts_per_row(args.contacts_per_row)
    targets = [(args.label or f"{args.run_id}-{args.rows}-rows", args.run_id, args.attempt, args.rows)] if args.run_id else [("b1-sealed-20-rows", B1_RUN, B1_ATTEMPT, args.rows)]
    if not args.no_smoke:
        targets.append(("engineering-smoke-4-rows", SMOKE_RUN, SMOKE_ATTEMPT, 4))
    arms = []
    for label, run_id, attempt, count in targets:
        trace = root / "runs" / run_id / attempt / f"{run_id}.trace.jsonl"
        if not trace.is_file():
            raise WireCheckError(f"REFUSED: the sealed trace {trace} is not readable")
        rows = read_rows(trace, rows=count)
        arm = check_arm(rows, binding, reduced_binding, label=label)
        arm.update(run_id=run_id, attempt_id=attempt, read="read-only")
        arms.append(arm)

    document = {
        "schema": "saea-knowledge-index-wire-check-v1",
        "generator": "scripts/knowledge_index_wire_check.py",
        "execution_profile": "model-free-check",
        "item": "E21w (the knowledge index's live runner wiring)",
        "contacts": {
            "model": 0, "tool": 0, "scorer": 0, "encoder": 0, "tokenizer": 0,
            "server": 0, "network": 0,
        },
        "estimator": {
            "rule": "llama.cpp common-prefix rule over character-level longest "
                    "common prefixes on the pinned per-slot stream",
            "chars_per_token": CHARS_PER_TOKEN,
            "source": "E17 design section 5 / throughput report section 8 Probe A; "
                      "no tokenizer was contacted",
            "derived": True,
        },
        "view": {
            "view_id": binding.table.view_id,
            "release_sha256": release_sha,
            "snapshot_sha256": snapshot_sha,
            "content_hash": binding.table.content_hash(),
            "entry_counts": binding.table.counts(),
        },
        "arms": arms,
        "passes": all(arm["passes"] for arm in arms),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=1, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    print(f"wrote {args.out}")
    for arm in arms:
        print(f"  [{arm['label']}] rows={arm['rows']} contacts={arm['contacts']}")
        print(
            f"    W1 OFF seam byte-identical: "
            f"{arm['W1_off_seam_byte_identical']}/{arm['contacts']}; "
            f"OFF payload sha256 identical: "
            f"{arm['W1_off_payload_sha256_identical']}/{arm['contacts']}"
        )
        print(
            f"    W2 distinct system-message sha256 (ON): "
            f"{arm['W2_distinct_system_message_sha256']}"
        )
        print(f"    W3 ON-vs-OFF differing keys: {arm['W3_armed_key_sets']}")
        print(
            f"    W5 provenance rows: {arm['W5_provenance_rows']} "
            f"(index rows {arm['W5_provenance_index_rows']})"
        )
        print(
            f"    W6 truncation violations: {len(arm['W6_truncation_violations'])}"
        )
        print(
            f"    W7 envelope ok {arm['W7_framework_envelope_ok']}/{arm['contacts']}; "
            f"receipts populated {arm['W7_receipt_rows_populated']}/{arm['contacts']}"
        )
        print("    per position (predicted, derived):")
        print("       position      prompt  prefilled")
        for row in arm["per_position"]:
            print(
                f"       {row['position']:<12}"
                f"{row['predicted_prompt_tokens_median']:>8}"
                f"{row['predicted_prefilled_tokens_median']:>11}"
            )
        print(
            "       row total prefilled (predicted): "
            f"{arm['predicted_prefilled_tokens_per_row']}"
        )
        print(f"    findings: {len(arm['findings'])}  passes: {arm['passes']}")
    return 0 if document["passes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
