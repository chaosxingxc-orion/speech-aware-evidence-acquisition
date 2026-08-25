"""Session-bound prompt-fit bound for the Audio2Tool G1 arms under the
SECTION 8.1 DERIVED serving geometry (`-c 65536 -np 2`, 32,768 tokens/slot).

Successor to ``scripts/a2t_g1_prompt_fit.py``, which measured the same two
envelope shapes against the SLURP np8 profile's 8,192-token slot and returned
a negative margin for BOTH arms, stopping the first G1 attempt at zero spend
(receipt ``docs/checks/.../2026-08-25-a2t-g1-prompt-fit/``). This script
re-measures against the geometry the campaign plan's section 8.1 rule DERIVES
for this carrier, and it improves on its predecessor in one material way:

**speech-feature tokens are now MEASURED, not assumed.** The predecessor had
to count them as zero because Audio2Tool had no promoted packet root; row
``SAEA-SN-A2T-G1-PREPROCESS`` has since materialized one, so this script reads
every promoted packet for the flown 104-item subset and takes the true
per-item maximum. The bound is therefore exact rather than a lower bound, and
the zero-speech figure is still reported alongside so the two receipts compare
directly.

Everything else is carried verbatim from the predecessor: the same real
``rails.runner._agent_messages`` shapes through
``core.model.transport._ordered_speech_feature_content`` /
``_speech_history_texts``, the same ``Audio2ToolAdapter`` supplying
``build_task_contract`` / ``assemble_prompt``, the same post-fix evidence
instruction asserted against the live ``rails.kb_policy`` source, and the same
worst-case visible knowledge (the m=5 longest key facets and the
fusion_c 2 * fusion_top_l 3 = 6 longest values in the pinned A2T snapshot).

Contacts: 1 GET /props + 1 POST /apply-template and <= 2 POST /tokenize per
envelope, against the RESIDENT np2 session on port 8090. Zero decode, zero
generated tokens, zero audio decoded, zero gold opened.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python scripts/a2t_g1_prompt_fit_np2.py <output.json>
"""

from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if not Path(_pkg.__file__).resolve().is_relative_to(REPO_ROOT / "src"):
    raise SystemExit("package resolved outside this checkout: %s" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.core.driver.speech_native import (  # noqa: E402
    _LoopbackPromptAuditClient,
)
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    load_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.model.transport import (  # noqa: E402
    _ordered_speech_feature_content,
    _speech_history_texts,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
)

MODEL_FRAGMENT_RELPATH = (
    "configs/model/q4km-mmproj-free-speech-native-np2-a2t-max1024.json"
)
PROMPT_ORDER = "speech-query-prefix-v2"
SNAPSHOT_RELPATH = (
    "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/snapshot.json"
)
SNAPSHOT_SHA256 = "ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2"
KB_RECEIPT_RELPATH = "docs/receipts/knowledge/a2t-kb-size-full.json"
SUBSET_RECEIPT_RELPATH = "docs/receipts/a2t/A2T-G1-104.json"
SUBSET_RECEIPT_SHA256 = (
    "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
)
FEATURE_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
CONTROL_CONTACT_ID = "evidence-decode"
FUSION_M = 5
FUSION_VALUE_CEILING = 6  # fusion_c 2 * fusion_top_l 3
SPLIT_ROLE = "discovery"
DECODER_PORT = 8090
PREDECESSOR_RECEIPT = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1-prompt-fit/prompt-fit.json"
)
PREDECESSOR_M0_TEXT_TOKENS = 13236
PREDECESSOR_BLEND_TEXT_TOKENS = 19047
PREDECESSOR_CONTEXT_PER_SLOT = 8192


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def evidence_id(index: int, knowledge_role: str, identifier: str) -> str:
    return "%03d:%s:%s" % (index, knowledge_role, identifier)


def build_messages(*, system_text, key_texts, value_texts, state_texts):
    """Exactly the transport's own wire assembly for one contact.

    The speech-feature part is a placeholder whose TOKEN cost is added
    separately: ``_ordered_speech_feature_content`` emits one opaque media
    marker for it regardless of the packet behind it, so the rendered TEXT is
    independent of which packet is named."""

    feature_parts = [
        {
            "type": "input_speech_features",
            "speech_features": {
                "packet_id": "audit/a2t-g1-prompt-fit/query",
                "sha256": "0" * 64,
                "role": "query",
            },
        }
    ]
    evidence_texts = []
    knowledge_roles = []
    for index, text in enumerate(key_texts):
        evidence_texts.append("[evidence %s] %s" % (evidence_id(index, "key", "facet"), text))
        knowledge_roles.append("key")
    for offset, text in enumerate(value_texts):
        index = len(key_texts) + offset
        evidence_texts.append(
            "[evidence %s] %s" % (evidence_id(index, "value", "value"), text)
        )
        knowledge_roles.append("value")
    content = _ordered_speech_feature_content(
        prompt_order=PROMPT_ORDER,
        evidence_texts=evidence_texts,
        feature_parts=feature_parts,
        state_texts=state_texts,
        knowledge_roles=knowledge_roles if any(knowledge_roles) else (),
    )
    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": content},
    ]


def text_token_count(client, messages, media_marker, request_counts):
    body = {"messages": list(messages)}
    rendered = client.post_json("/apply-template", body)
    request_counts["POST /apply-template"] += 1
    prompt = rendered.get("prompt")
    if not isinstance(prompt, str):
        raise SystemExit("apply-template returned no prompt")
    if prompt.count(media_marker) != 1:
        raise SystemExit(
            "rendered prompt carries %d media markers, expected 1"
            % prompt.count(media_marker)
        )
    total = 0
    for segment in prompt.split(media_marker):
        if not segment:
            continue
        response = client.post_json(
            "/tokenize",
            {"content": segment, "add_special": False, "parse_special": True},
        )
        request_counts["POST /tokenize"] += 1
        tokens = response.get("tokens")
        if not isinstance(tokens, list):
            raise SystemExit("tokenize returned no token list")
        total += len(tokens)
    return total


def main() -> int:
    output = Path(sys.argv[1])
    lock = load_lock(umbrella_lock_path())
    root = data_root()

    # --- serving geometry: the DERIVED np2 fragment, cross-checked live ----
    fragment = json.loads((REPO_ROOT / MODEL_FRAGMENT_RELPATH).read_text(encoding="utf-8"))
    server_args = [str(token) for token in fragment["server_args"]]
    context_tokens = int(server_args[server_args.index("-c") + 1])
    slot_count = int(server_args[server_args.index("-np") + 1])
    context_per_slot = context_tokens // slot_count
    if fragment["prompt_order"] != PROMPT_ORDER:
        raise SystemExit("fragment prompt_order is %r" % (fragment["prompt_order"],))
    completion_tokens = int(fragment["decoding_params"]["max_tokens"])
    if (context_tokens, slot_count, completion_tokens) != (65536, 2, 1024):
        raise SystemExit(
            "fragment geometry is -c %d -np %d max_tokens %d, not the section 8.1 "
            "derived 65536 / 2 / 1024" % (context_tokens, slot_count, completion_tokens)
        )

    # --- MEASURED speech-feature tokens over the FLOWN subset --------------
    subset_path = REPO_ROOT / SUBSET_RECEIPT_RELPATH
    measured_subset = hashlib.sha256(subset_path.read_bytes()).hexdigest()
    if measured_subset != SUBSET_RECEIPT_SHA256:
        raise SystemExit("subset receipt hashes to %s, not the pin" % measured_subset)
    subset = json.loads(subset_path.read_text(encoding="utf-8"))
    packet_tokens: dict[str, int] = {}
    for item in subset["items"]:
        packet = load_speech_feature_packet(FEATURE_ROOT, item["packet_id"])
        if packet.audio_sha256 != item["audio_sha256"]:
            raise SystemExit("packet %s carries a different audio sha256" % item["packet_id"])
        packet_tokens[item["sample_id"]] = sum(chunk.n_tokens for chunk in packet.chunks)
    if len(packet_tokens) != int(subset["count"]):
        raise SystemExit("packet coverage is incomplete")
    worst_speech_sample = max(
        packet_tokens, key=lambda sid: (packet_tokens[sid], sid)
    )
    measured_speech_tokens = packet_tokens[worst_speech_sample]
    ordered_tokens = sorted(packet_tokens.values())

    # --- worst-case text material -----------------------------------------
    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO_ROOT)
    samples = list(adapter.load_split(SPLIT_ROLE))
    if not samples:
        raise SystemExit("split_role=%r resolved zero samples" % SPLIT_ROLE)
    longest = max(samples, key=lambda s: (float(s.audio_seconds), s.sample_id))

    task_contract = adapter.build_task_contract(longest, None)
    base = tuple(adapter.assemble_prompt(longest, None))
    if len(base) != 2:
        raise SystemExit("assemble_prompt must return exactly system and user messages")
    system_text = base[0]["content"]
    contract_counted_once = task_contract in system_text
    if not contract_counted_once:
        system_text = "%s\n\nTask contract:\n%s" % (system_text, task_contract)

    # --- pinned A2T knowledge snapshot -------------------------------------
    receipt = json.loads((REPO_ROOT / KB_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    if receipt.get("snapshot_sha256") != SNAPSHOT_SHA256:
        raise SystemExit("A2T KB receipt snapshot sha256 does not match the pin")
    snapshot_path = root / SNAPSHOT_RELPATH
    snapshot_bytes = snapshot_path.read_bytes()
    snapshot_file_sha256 = hashlib.sha256(snapshot_bytes).hexdigest()
    snapshot = json.loads(snapshot_bytes.decode("utf-8"))
    if snapshot.get("snapshot_sha256") != SNAPSHOT_SHA256:
        raise SystemExit("A2T KB snapshot self-declared sha256 does not match the pin")
    if snapshot.get("snapshot_id") != receipt.get("snapshot_id"):
        raise SystemExit("A2T KB snapshot id does not match its receipt")
    key_texts = [
        str(facet["representation"])
        for facet in sorted(
            snapshot["facets"], key=lambda f: -len(str(f.get("representation", "")))
        )[:FUSION_M]
    ]
    value_texts = [
        str(value["content"])
        for value in sorted(
            snapshot["values"], key=lambda v: -len(str(v.get("content", "")))
        )[:FUSION_VALUE_CEILING]
    ]

    # --- post-fix evidence instruction, bound to the real controller -------
    control_instruction = (
        "Decide under the task contract already given above, now "
        "considering the retrieved evidence. Answer using the speech "
        "query together with the supplied knowledge evidence."
    )
    from speech_aware_evidence_acquisition.rails import kb_policy as _kb_policy

    _kb_source = inspect.getsource(_kb_policy)
    if '"Decide under the task contract already given above, now "' not in _kb_source:
        raise SystemExit(
            "rails.kb_policy no longer renders the post-fix evidence instruction "
            "this script emulates; re-derive the worst case"
        )
    if task_contract in control_instruction:
        raise SystemExit("post-fix instruction must not re-render the task contract")
    history = [
        {
            "turn": 1,
            "role": "control",
            "contact_id": CONTROL_CONTACT_ID,
            "content": control_instruction,
            "content_sha256": hashlib.sha256(control_instruction.encode("utf-8")).hexdigest(),
        }
    ]
    state_texts = _speech_history_texts(history)

    envelopes = [
        {
            "envelope_id": "m0-direct-decode",
            "stage_kind": "direct",
            "messages": build_messages(
                system_text=system_text, key_texts=[], value_texts=[], state_texts=[]
            ),
        },
        {
            "envelope_id": "blend-evidence-decode-worst",
            "stage_kind": "evidence",
            "messages": build_messages(
                system_text=system_text,
                key_texts=key_texts,
                value_texts=value_texts,
                state_texts=state_texts,
            ),
        },
    ]

    client = _LoopbackPromptAuditClient(
        host="127.0.0.1", port=DECODER_PORT, timeout_seconds=120.0
    )
    props = client.get_json("/props")
    request_counts = {"GET /props": 1, "POST /apply-template": 0, "POST /tokenize": 0}
    media_marker = props.get("media_marker")
    chat_template = props.get("chat_template")
    if not isinstance(media_marker, str) or not media_marker:
        raise SystemExit("resident props lack a media marker")
    live_slot_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
    if int(live_slot_ctx) != context_per_slot:
        raise SystemExit(
            "resident slot n_ctx %s does not match the derived fragment's %d; refusing "
            "to certify a geometry the service does not serve"
            % (live_slot_ctx, context_per_slot)
        )

    rows = []
    for envelope in envelopes:
        tokens = text_token_count(client, envelope["messages"], media_marker, request_counts)
        rows.append(
            {
                "envelope_id": envelope["envelope_id"],
                "stage_kind": envelope["stage_kind"],
                "messages_sha256": canonical_sha256(envelope["messages"]),
                "text_prompt_tokens": tokens,
                "prompt_tokens_zero_speech": tokens + 2,
                # PRIMARY for this receipt: the MEASURED worst packet.
                "prompt_tokens_with_measured_speech": tokens + measured_speech_tokens + 2,
            }
        )

    worst = max(
        rows,
        key=lambda row: (row["prompt_tokens_with_measured_speech"], row["envelope_id"]),
    )
    maximum_prompt = worst["prompt_tokens_with_measured_speech"]
    margin = context_per_slot - maximum_prompt - completion_tokens
    required_per_slot = maximum_prompt + completion_tokens

    by_envelope = {row["envelope_id"]: row for row in rows}
    report = {
        "schema": "saea-a2t-g1-prompt-fit-np2-v1",
        "study": "speech-aware-evidence-acquisition",
        "scope": "model-free-check",
        "model_contact": False,
        "exposure_run_id": "SAEA-SN-MF-A2T-G1-PROMPT-FIT-NP2",
        "carrier_lock_key": AUDIO2TOOL_LOCK_KEY,
        "split_role": SPLIT_ROLE,
        "split_sample_count": len(samples),
        "flown_subset": subset["split_name"],
        "flown_subset_count": int(subset["count"]),
        "flown_subset_receipt_sha256": measured_subset,
        "longest_sample_id": longest.sample_id,
        "longest_sample_audio_seconds": float(longest.audio_seconds),
        "rendering_source": (
            "rails.runner._agent_messages shapes rendered through "
            "core.model.transport._ordered_speech_feature_content and "
            "_speech_history_texts, with rails.adapters.audio2tool.Audio2ToolAdapter "
            "supplying build_task_contract/assemble_prompt. POST-fix evidence "
            "instruction asserted against rails.kb_policy source"
        ),
        "model_fragment": MODEL_FRAGMENT_RELPATH,
        "prompt_order": PROMPT_ORDER,
        "serving_geometry_status": (
            "DERIVED per carrier by campaign plan section 8.1 from the measured task "
            "contract; applied identically to every arm and fixed before any result "
            "was seen"
        ),
        "knowledge_snapshot_sha256": SNAPSHOT_SHA256,
        "knowledge_snapshot_id": receipt.get("snapshot_id"),
        "knowledge_snapshot_file_sha256": snapshot_file_sha256,
        "task_contract_characters": len(task_contract),
        "task_contract_sha256": hashlib.sha256(task_contract.encode("utf-8")).hexdigest(),
        "task_contract_counted_once": contract_counted_once,
        "visible_key_facets": len(key_texts),
        "visible_values": len(value_texts),
        "agent_state_texts": len(state_texts),
        "speech_feature_tokens_measured_worst": measured_speech_tokens,
        "speech_feature_tokens_measured_worst_sample_id": worst_speech_sample,
        "speech_feature_tokens_distribution": {
            "count": len(ordered_tokens),
            "min": ordered_tokens[0],
            "median": ordered_tokens[len(ordered_tokens) // 2],
            "p90": ordered_tokens[min(len(ordered_tokens) - 1, int(0.9 * len(ordered_tokens)))],
            "max": ordered_tokens[-1],
            "sum": sum(ordered_tokens),
        },
        "speech_feature_tokens_source": (
            "MEASURED from the promoted packets under %s (row "
            "SAEA-SN-A2T-G1-PREPROCESS). The predecessor receipt had to assume ZERO "
            "because no packet root existed; this receipt is exact." % FEATURE_ROOT
        ),
        "special_token_reserve": 2,
        "completion_tokens": completion_tokens,
        "maximum_text_prompt_tokens": max(row["text_prompt_tokens"] for row in rows),
        "maximum_prompt_tokens_with_measured_speech": maximum_prompt,
        "maximum_prompt_tokens_zero_speech": max(
            row["prompt_tokens_zero_speech"] for row in rows
        ),
        "context_tokens": context_tokens,
        "slot_count": slot_count,
        "context_tokens_per_slot": context_per_slot,
        "context_margin_tokens": margin,
        "maximum_prompt_fits_one_slot": margin >= 0,
        "required_context_per_slot": required_per_slot,
        "worst_envelope_id": worst["envelope_id"],
        "envelopes": rows,
        "predecessor_comparison": {
            "receipt": PREDECESSOR_RECEIPT,
            "context_tokens_per_slot": PREDECESSOR_CONTEXT_PER_SLOT,
            "m0_text_tokens_then": PREDECESSOR_M0_TEXT_TOKENS,
            "m0_text_tokens_now": by_envelope["m0-direct-decode"]["text_prompt_tokens"],
            "blend_text_tokens_then": PREDECESSOR_BLEND_TEXT_TOKENS,
            "blend_text_tokens_now": by_envelope["blend-evidence-decode-worst"][
                "text_prompt_tokens"
            ],
            "text_rendering_unchanged": (
                by_envelope["m0-direct-decode"]["text_prompt_tokens"]
                == PREDECESSOR_M0_TEXT_TOKENS
                and by_envelope["blend-evidence-decode-worst"]["text_prompt_tokens"]
                == PREDECESSOR_BLEND_TEXT_TOKENS
            ),
            "note": (
                "the TEXT envelopes must be unchanged: the derivation changed the "
                "SERVING geometry, never the prompt. A difference here would mean the "
                "prompt shape moved and the comparison to the predecessor is void."
            ),
        },
        "tokenizer": {
            "request_counts": request_counts,
            "decoder_evaluations": 0,
            "generated_tokens": 0,
            "media_marker": media_marker,
            "chat_template_sha256": hashlib.sha256(chat_template.encode("utf-8")).hexdigest(),
            "host": "127.0.0.1",
            "port": DECODER_PORT,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "maximum_text_prompt_tokens",
                    "speech_feature_tokens_measured_worst",
                    "maximum_prompt_tokens_with_measured_speech",
                    "context_tokens_per_slot",
                    "completion_tokens",
                    "context_margin_tokens",
                    "required_context_per_slot",
                    "maximum_prompt_fits_one_slot",
                    "worst_envelope_id",
                )
            },
            indent=2,
        )
    )
    print(
        "text rendering unchanged vs the np8 receipt: %s"
        % report["predecessor_comparison"]["text_rendering_unchanged"]
    )
    for row in report["envelopes"]:
        print(
            "  %-28s text=%6d with_measured_speech=%6d"
            % (
                row["envelope_id"],
                row["text_prompt_tokens"],
                row["prompt_tokens_with_measured_speech"],
            )
        )
    print("receipt:", output)
    print("receipt_sha256:", hashlib.sha256(output.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
