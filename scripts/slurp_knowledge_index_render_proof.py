#!/usr/bin/env python3
"""CLI: the model-free RENDER PROOF of item E21 (the knowledge index; NOT the
Earnings-21 carrier). Design section 7.0, the E17 Probe A form.

MODEL-FREE, and the refusal is structural: this script imports no transport
client, opens no socket, loads no tokenizer and reads the sealed run
directory READ-ONLY. Profile ``model-free-check``. Zero model, tool,
tokenizer, encoder, scorer, server and network contacts.

WHAT IT PROVES. Re-render the 100 contacts of the first 20 sealed rows of the
B1 arm ``SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2``
with ``native_episode.knowledge_index`` armed at the recommended defaults, and
emit a receipt per contact carrying the rendered system-message sha256, the
rendered prompt sha256, the pointer and expansion ids, and the predicted
prefilled-token count. Three properties, each of which stops the cell if it
does not reproduce (design section 7.0):

P1. the rendered system message is ONE value over all five contacts of a row
    and over all 20 rows;
P2. the Solver's predicted prefilled tokens fall sharply -- the whole
    economic claim of replacing 24,057 characters of candidate slot-contract
    cards with a pointer block;
P3. reducing ``expansion_budget.slot_card`` to 0 moves NO byte before the
    expansion block.

It also carries the key's own falsifier: with the key ABSENT this script
re-composes each sealed payload and re-hashes it, and the digest must equal
the sealed ``payload_sha256`` -- byte identity against the sealed B1 request
bytes, hashes only, nothing copied out.

THE ESTIMATOR, and why it is not a tokenizer. E17's own proof
(``docs/superpowers/specs/2026-09-19-e17-constant-tool-rendering-design.md``
section 5, and the Probe A of ``docs/results/2026-09-19-slurp-throughput-
root-cause-v1.md`` section 8) derives its prefill numbers from
"character-level longest-common-prefix proxies over sealed requests plus
llama.cpp's common-prefix rule", and states in as many words that
"re-tokenising here would have been a tokenizer contact". This script uses
exactly that estimator:

    rendered stream  = the system message (tools array included, because the
                       Qwen3-Omni chat template renders `tools` INSIDE the
                       system message) followed by every user content part in
                       wire order
    prompt tokens    = len(stream) / CHARS_PER_TOKEN
    cached tokens    = len(longest common prefix with the previous request on
                       the SAME pinned slot) / CHARS_PER_TOKEN
    prefilled tokens = prompt - cached

``CHARS_PER_TOKEN`` is ``rails.knowledge_index.CHARS_PER_TOKEN`` (4.60, the
measured median over this arm's own four roles). Every number this script
prints is therefore DERIVED and is labelled as such; token-level realisation
can only be confirmed on a live cell, exactly as E17 says of its own 50.1 %.

WHICH PRODUCTION CODE IS USED, and which rails are bypassed. The rendering
path is the transport's own: ``core.model.transport._speech_history_texts``,
``_ordered_speech_feature_content``, ``_assert_agent_history_suffix``, the
``[evidence <id>] <content>`` item format and the two-message
``[system, user]`` composition, plus ``project_native_framework_history`` /
``project_native_history``. The rails NOT run are the live-session validity
check, the speech-packet loader and the media-confinement check -- none of
which moves a byte of the rendered body, and all three of which would need a
resident server or the packet store. The same offline reuse of these
functions is already the repository's form in ``rails.phase_material`` and
``rails.a2t_executable_ground_prompt_fit``.

NOTHING IS PERSISTED BUT DIGESTS AND COUNTS. No utterance text, no reference
transcript, no gold and no rendered prompt body is written anywhere.

Usage::

    python scripts/slurp_knowledge_index_render_proof.py \\
        --snapshot <dir>/knowledge/slurp/semantic/slurp-knowledge-index-v1/snapshot.json \\
        --out <scratch>/render-proof.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.model.transport import (  # noqa: E402
    _assert_agent_history_suffix,
    _ordered_speech_feature_content,
    _speech_history_texts,
)
from speech_aware_evidence_acquisition.core.model.native_framework_history import (  # noqa: E402
    project_native_framework_history,
)
from speech_aware_evidence_acquisition.core.model.native_history import (  # noqa: E402
    project_native_history,
)
from speech_aware_evidence_acquisition.rails.knowledge_index import (  # noqa: E402
    CHARS_PER_TOKEN,
    POINTER_BLOCK_EVIDENCE_ID,
    RowSelection,
    apply_to_payload,
    assemble,
    canonical_json,
    contact_receipt,
    estimated_tokens,
    index_suffix,
    knowledge_index_receipt,
    parse_knowledge_index_config,
    render_constant_index,
    sha256_text,
    table_from_snapshot,
)

DEFAULT_RUN_ID = "SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2"
DEFAULT_ATTEMPT = (
    "attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-recovery-v2"
)
PROMPT_ORDER = "speech-query-prefix-v2"
ROLE_POSITIONS = ("perception", "solver", "reviewer-1", "reviewer-2", "planner")
ROLE_IDS = ("perception", "solver", "reviewer", "reviewer", "planner")
#: The tool-free base (repair form 0-B, cell B1-notool): the Reviewer answers on its
#: first contact, so a row is four contacts. Selected by ``--contacts-per-row 4``.
ROLE_POSITIONS_4 = ("perception", "solver", "reviewer", "planner")
ROLE_IDS_4 = ("perception", "solver", "reviewer", "planner")
CONTACTS_PER_ROW = 5
#: On the four-contact base the single Reviewer contact is compared with E17's first Reviewer position.
E17_REFERENCE_POSITION = {"reviewer": "reviewer-1"}


def set_contacts_per_row(count: int) -> None:
    """Select the five-contact (tool-bearing) or four-contact (tool-free) row shape."""
    global CONTACTS_PER_ROW, ROLE_POSITIONS, ROLE_IDS
    if count == 4:
        ROLE_POSITIONS, ROLE_IDS = ROLE_POSITIONS_4, ROLE_IDS_4
    elif count != 5:
        raise ProofError(f"unsupported contacts per row: {count}")
    CONTACTS_PER_ROW = count

#: E17's own measured per-position numbers, quoted here so the proof's table
#: can stand beside them (design section 2.5 / E17 design section 1).
E17_MEASURED = {
    "perception": {"prompt": 3597, "prefilled": 1373},
    "solver": {"prompt": 9960, "prefilled": 6591},
    "reviewer-1": {"prompt": 10062, "prefilled": 7843},
    "reviewer-2": {"prompt": 11813, "prefilled": 1757},
    "planner": {"prompt": 11805, "prefilled": 9586},
}

INTENT_PREFIX = "intent-boundaries::intent-boundary:"
SLOT_PREFIX = "slot-contracts::slot-contract:"
EXEMPLAR_PREFIX = "train-exemplars::value:"


class ProofError(SystemExit):
    pass


# ---------------------------------------------------------------------------
# Reading the sealed arm, read-only.
# ---------------------------------------------------------------------------


def read_rows(trace_path: Path, *, rows: int) -> "OrderedDict[str, list[dict]]":
    """The first ``rows`` distinct sample ids in flight order, 5 contacts each."""

    by_sample: OrderedDict[str, list[dict]] = OrderedDict()
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
            contacts = by_sample.setdefault(sample_id, [])
            contacts.append(
                {
                    "record_id": record["record_id"],
                    "payload": payload,
                    "payload_sha256": envelope["payload_sha256"],
                }
            )
            if sum(1 for items in by_sample.values() if len(items) == CONTACTS_PER_ROW) >= rows and len(by_sample) >= 4 * rows:
                break
    complete = OrderedDict(
        (sample_id, contacts)
        for sample_id, contacts in by_sample.items()
        if len(contacts) == CONTACTS_PER_ROW
    )
    if len(complete) < rows:
        raise ProofError(
            f"REFUSED: only {len(complete)} complete {CONTACTS_PER_ROW}-contact rows were found in the "
            f"sealed trace; the proof form needs {rows}"
        )
    return OrderedDict(list(complete.items())[:rows])


def derive_selection(payload: dict) -> RowSelection:
    """This row's own pointers, from its own sealed request. No gold is read.

    * candidates -- the Perception node's OWN hypothesis list, in its own
      order, taken from the ``phase:perception`` agent state. On the
      Perception contact itself there is no such state yet, so the
      intent-boundary evidence order stands in: that is the retrieval order
      the node is choosing between, which is exactly what the pointer block
      names at that position.
    * exemplar votes -- the construction intent of each retrieved exemplar,
      read from the exemplar's own rendered content
      (``<utterance> | <scenario>_<action> | <slots>``). Construction text,
      already in the prompt today.
    * slot types -- the types the candidate projection bound, in supply order.
    """

    candidates: list[str] = []
    for state in payload.get("history", ()):
        if state.get("state_kind") != "phase:perception":
            continue
        document = json.loads(state["content"])
        candidates = [
            row["intent_id"] for row in document.get("candidates", ())
            if isinstance(row.get("intent_id"), str)
        ]
    retrieved_intents: list[str] = []
    slot_types: list[str] = []
    exemplars: list[tuple[str, str]] = []
    votes: Counter[str] = Counter()
    for item in payload.get("supplied_evidence", ()):
        evidence_id = item.get("evidence_id", "")
        if evidence_id.startswith(INTENT_PREFIX):
            retrieved_intents.append(evidence_id[len(INTENT_PREFIX):])
        elif evidence_id.startswith(SLOT_PREFIX):
            slot_types.append(evidence_id[len(SLOT_PREFIX):])
        elif evidence_id.startswith(EXEMPLAR_PREFIX):
            key = evidence_id[len(EXEMPLAR_PREFIX):]
            content = item.get("content", "")
            exemplars.append((key, content))
            fields = [part.strip() for part in content.split("|")]
            if len(fields) >= 2 and fields[1]:
                votes[fields[1]] += 1
    return RowSelection(
        candidates=tuple(candidates or retrieved_intents),
        exemplar_votes=tuple(sorted(votes.items(), key=lambda row: (-row[1], row[0]))),
        slot_types=tuple(slot_types),
        exemplars=tuple(exemplars),
    )


# ---------------------------------------------------------------------------
# The production render path, offline.
# ---------------------------------------------------------------------------


def render_body(payload: dict, *, tool_schemas: list | None) -> dict:
    """The exact send body the transport composes for a speech-feature arm."""

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
    """The token stream, as the chat template lays it out.

    The Qwen3-Omni template renders the ``tools`` array INSIDE the system
    message, which is the whole reason E17 exists, so the proxy stream puts
    it there too: system content, then the tools block, then every message's
    parts in order.
    """

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
    """What the template folds into ONE system message (E17's own definition)."""

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


# ---------------------------------------------------------------------------
# The proof itself.
# ---------------------------------------------------------------------------


def run_arm(rows, table, plan, *, label: str) -> dict:
    index_text = render_constant_index(table, plan)
    suffix = index_suffix(table, plan)
    if not index_text or suffix != f"\n\n{index_text}":
        raise ProofError("REFUSED: the index suffix is not the index")
    per_position: dict[str, list[dict]] = {name: [] for name in ROLE_POSITIONS}
    receipts: list[dict] = []
    system_digests: set[str] = set()
    slot_last: dict[object, str] = {}
    streams: dict[tuple[str, int], str] = {}
    contents: dict[tuple[str, int], list] = {}
    expanded: dict[tuple[str, int], tuple] = {}
    for sample_id, contacts in rows.items():
        # E17 is a precondition of this key (refusal 7), so the rendered
        # tools array is CONSTANT across the row: the union of what any role
        # of this episode may call, which on this episode is the Reviewer's
        # own single schema.
        constant_tools: list = []
        for contact in contacts:
            schemas = contact["payload"].get("tool_schemas") or []
            if schemas:
                constant_tools = schemas
                break
        selection = derive_selection(contacts[1]["payload"])
        for position, contact in enumerate(contacts):
            payload = contact["payload"]
            role_id = ROLE_IDS[position]
            block = assemble(table, plan, selection, role_id=role_id)
            armed = apply_to_payload(payload, index_text=index_text, assembly=block)
            body = render_body(armed, tool_schemas=constant_tools)
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
                contact_id=contact["record_id"],
                role_id=role_id,
                assembly=block,
                system_message=prefix,
                index_text=index_text,
                cited_ids=(),
                table=table,
            )
            row.update(
                position=ROLE_POSITIONS[position],
                rendered_prompt_sha256=sha256_text(stream),
                rendered_prompt_chars=len(stream),
                predicted_prompt_tokens=prompt_tokens,
                predicted_cached_tokens=cached_tokens,
                predicted_prefilled_tokens=max(prompt_tokens - cached_tokens, 0),
                sealed_payload_sha256=contact["payload_sha256"],
            )
            receipts.append(row)
            per_position[ROLE_POSITIONS[position]].append(row)
            streams[(sample_id, position)] = stream
            contents[(sample_id, position)] = body["messages"][1]["content"]
            expanded[(sample_id, position)] = block.expanded_ids
    table_rows = []
    for name in ROLE_POSITIONS:
        entries = per_position[name]
        table_rows.append(
            {
                "position": name,
                "contacts": len(entries),
                "predicted_prompt_tokens_median": _median(
                    [row["predicted_prompt_tokens"] for row in entries]
                ),
                "predicted_prefilled_tokens_median": _median(
                    [row["predicted_prefilled_tokens"] for row in entries]
                ),
                "e17_measured_prompt_tokens": E17_MEASURED[E17_REFERENCE_POSITION.get(name, name)]["prompt"],
                "e17_measured_prefilled_tokens": E17_MEASURED[E17_REFERENCE_POSITION.get(name, name)]["prefilled"],
            }
        )
    receipt = knowledge_index_receipt(
        plan=plan, table=table, index_text=index_text, contacts=receipts,
    )
    return {
        "label": label,
        "index_chars": len(index_text),
        "index_tokens_at_4_60": estimated_tokens(len(index_text)),
        "index_sha256": sha256_text(index_text),
        "distinct_system_message_sha256": len(system_digests),
        "per_position": table_rows,
        "predicted_prefilled_tokens_per_row": sum(
            row["predicted_prefilled_tokens_median"] for row in table_rows
        ),
        "receipt": receipt,
        "_streams": streams,
        "_contents": contents,
        "_expanded": expanded,
    }


def _median(values: list[int]) -> int:
    ordered = sorted(values)
    if not ordered:
        return 0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def off_arm_identity(rows) -> dict:
    """The key's own falsifier: absent, the payload is byte-identical.

    Digests only. The sealed payload is re-composed through
    :func:`rails.knowledge_index.apply_to_payload` with no index and no
    assembly, canonicalised the way the trace sealed it, and its sha256 must
    equal the sealed ``payload_sha256``.
    """

    import hashlib

    checked = 0
    mismatched = []
    for _sample_id, contacts in rows.items():
        for contact in contacts:
            composed = apply_to_payload(
                contact["payload"], index_text=None, assembly=None
            )
            digest = hashlib.sha256(
                json.dumps(
                    composed, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()
            checked += 1
            if digest != contact["payload_sha256"]:
                mismatched.append(contact["record_id"])
    return {
        "contacts_checked": checked,
        "mismatched_contacts": mismatched,
        "identical": not mismatched,
    }


def _expansion_span(parts: list, expanded_ids: tuple) -> tuple[int, int]:
    """``(start, end)`` of the expansion block inside one content list.

    The block starts immediately after the pointer part and runs for exactly
    as many parts as the contact expanded, which is what makes "the tail" a
    position rather than a guess.
    """

    # The wire content parts carry only ``{"type": "text", "text": ...}``:
    # the evidence id lives INSIDE the text, as the transport's own
    # ``[evidence <id>] `` prefix. That prefix is therefore what addresses a
    # block here, exactly as it is what the model reads.
    start = None
    for index, part in enumerate(parts):
        if part.get("type") == "text" and part.get("text", "").startswith(
            f"[evidence {POINTER_BLOCK_EVIDENCE_ID}] "
        ):
            start = index + 1
            break
    if start is None:
        raise ProofError("REFUSED: a rendered contact carries no pointer block")
    return start, start + len(expanded_ids)


def _is_expansion_part(part: dict) -> bool:
    text = part.get("text", "") if part.get("type") == "text" else ""
    return any(
        text.startswith(f"[evidence {sigil}/") for sigil in ("X", "S", "I")
    )


def no_byte_moves(full: dict, reduced: dict) -> dict:
    """P3: truncating the expansion block from its tail moves no byte before it.

    The claim is positional, so the check is positional. Let ``k`` be the
    number of expansions the NARROWED arm kept. The narrowed content must be
    the full content with a CONTIGUOUS run removed from the END of the
    expansion block:

    * every part before the truncation point is equal object-for-object --
      the speech packet, the key parts, the pointer block and the retained
      expansions;
    * what follows the truncation point in the narrowed arm is exactly what
      followed the whole expansion block in the full arm (the agent states
      and the role query), shifted but unchanged byte for byte;
    * only ``value:`` expansion parts were removed -- never a state, never
      the speech packet, never the pointer block.

    It is also checked TEXTUALLY: the two rendered streams must share a
    character prefix at least as long as everything up to the truncation
    point, which is the statement the KV cache actually cares about.
    """

    violations: list[dict] = []
    checked = 0
    for key, reduced_parts in reduced["_contents"].items():
        full_parts = full["_contents"][key]
        checked += 1
        full_start, full_end = _expansion_span(
            full_parts, full["_expanded"][key]
        )
        reduced_start, reduced_end = _expansion_span(
            reduced_parts, reduced["_expanded"][key]
        )
        kept = reduced_end - reduced_start
        if reduced_start != full_start or kept > full_end - full_start:
            violations.append({"contact": list(key), "reason": "the block moved or grew"})
            continue
        head = full_start + kept
        if reduced_parts[:head] != full_parts[:head]:
            violations.append(
                {"contact": list(key), "reason": "a part before the truncation moved"}
            )
            continue
        if reduced_parts[head:] != full_parts[full_end:]:
            violations.append(
                {"contact": list(key), "reason": "the suffix after the block changed"}
            )
            continue
        for part in full_parts[head:full_end]:
            if not _is_expansion_part(part):
                violations.append(
                    {"contact": list(key), "reason": "a non-expansion part was dropped"}
                )
        head_chars = sum(
            len(part.get("text", "")) for part in full_parts[:head]
            if part.get("type") == "text"
        )
        shared = common_prefix_chars(
            full["_streams"][key], reduced["_streams"][key]
        )
        if shared < head_chars:
            violations.append(
                {
                    "contact": list(key),
                    "reason": "the rendered streams diverge before the truncation",
                    "shared_chars": shared,
                    "head_chars": head_chars,
                }
            )
    return {
        "contacts_checked": checked,
        "violations": violations,
        "no_byte_before_the_expansion_block_moved": not violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=20)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--attempt", default=DEFAULT_ATTEMPT)
    parser.add_argument("--contacts-per-row", type=int, default=5, help="5 (tool-bearing base) or 4 (tool-free base, repair form 0-B)")
    args = parser.parse_args()

    if args.data_root is not None:
        root = Path(args.data_root)
    else:
        from speech_aware_evidence_acquisition.data.lock import data_root

        root = data_root()
    trace = (
        root / "runs" / args.run_id / args.attempt / f"{args.run_id}.trace.jsonl"
    )
    if not trace.is_file():
        raise ProofError(f"REFUSED: the sealed trace {trace} is not readable")

    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    table = table_from_snapshot(snapshot)
    pins = {
        "view": table.view_id,
        "release": {
            "relpath": f"knowledge/slurp/semantic/{table.view_id}/release.json",
            "root": "data", "sha256": "0" * 64,
        },
        "snapshot": {
            "relpath": f"knowledge/slurp/semantic/{table.view_id}/snapshot.json",
            "root": "data", "sha256": "0" * 64,
        },
    }
    plan = parse_knowledge_index_config(pins)
    reduced_plan = parse_knowledge_index_config(
        {**pins, "expansion_budget": {"slot_card": 0}}
    )

    set_contacts_per_row(args.contacts_per_row)
    rows = read_rows(trace, rows=args.rows)
    full = run_arm(rows, table, plan, label="armed-defaults")
    reduced = run_arm(rows, table, reduced_plan, label="armed-slot-card-0")
    identity = off_arm_identity(rows)
    property3 = no_byte_moves(full, reduced)

    document = {
        "schema": "saea-knowledge-index-render-proof-v1",
        "generator": "scripts/slurp_knowledge_index_render_proof.py",
        "execution_profile": "model-free-check",
        "contacts": {
            "model": 0, "tool": 0, "scorer": 0, "encoder": 0, "tokenizer": 0,
            "server": 0, "network": 0,
        },
        "estimator": {
            "rule": "llama.cpp common-prefix rule over character-level longest "
                    "common prefixes on the pinned per-slot stream",
            "chars_per_token": CHARS_PER_TOKEN,
            "source": "E17 design section 5 / throughput report section 8 Probe A; "
                      "no tokenizer was contacted, exactly as E17's proof did not",
            "derived": True,
        },
        "sealed_arm": {
            "run_id": args.run_id,
            "attempt_id": args.attempt,
            "rows": len(rows),
            "contacts": sum(len(items) for items in rows.values()),
            "read": "read-only",
        },
        "view": {
            "view_id": table.view_id,
            "content_hash": table.content_hash(),
            "entry_counts": table.counts(),
        },
        "P1_one_system_message_sha256": {
            "armed_defaults": full["distinct_system_message_sha256"],
            "armed_slot_card_0": reduced["distinct_system_message_sha256"],
            "passes": full["distinct_system_message_sha256"] == 1
            and reduced["distinct_system_message_sha256"] == 1,
        },
        "P2_per_position": full["per_position"],
        "P2_predicted_prefilled_tokens_per_row": full[
            "predicted_prefilled_tokens_per_row"
        ],
        "P3_no_byte_before_the_expansion_block_moves": property3,
        "off_arm_byte_identity": identity,
        "arms": {
            name: {
                key: value for key, value in arm.items()
                if not key.startswith("_")
            }
            for name, arm in (("armed-defaults", full), ("armed-slot-card-0", reduced))
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=1, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    print(f"wrote {args.out}")
    print(f"  index chars={full['index_chars']} tokens@4.60={full['index_tokens_at_4_60']}")
    print(f"  P1 distinct system-message sha256 = "
          f"{full['distinct_system_message_sha256']} (armed defaults)")
    print("  P2 per position (predicted, derived):")
    print("     position      prompt  prefilled | E17 measured prompt  prefilled")
    for row in full["per_position"]:
        print(
            f"     {row['position']:<12}{row['predicted_prompt_tokens_median']:>8}"
            f"{row['predicted_prefilled_tokens_median']:>11} |"
            f"{row['e17_measured_prompt_tokens']:>16}{row['e17_measured_prefilled_tokens']:>11}"
        )
    print(
        "     row total prefilled (predicted): "
        f"{document['P2_predicted_prefilled_tokens_per_row']}"
    )
    print(f"  P3 no byte before the expansion block moved: "
          f"{property3['no_byte_before_the_expansion_block_moved']} "
          f"({property3['contacts_checked']} contacts)")
    print(f"  OFF arm byte identity: {identity['identical']} "
          f"({identity['contacts_checked']} contacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
