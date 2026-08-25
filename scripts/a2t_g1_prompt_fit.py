"""Tokenizer-only prompt-fit bound for the Audio2Tool G1 (M0 / BLEND) prompts.

This is the Audio2Tool sibling of ``scripts/dev100_c3_prompt_fit.py`` and it
renders the SAME two envelope shapes through the SAME real runner/transport
functions -- only the ``TaskAdapter`` and the knowledge snapshot change:

* system = ``Audio2ToolAdapter``'s instruction, which embeds the FULL frozen
  152-row tool registry (``data.audio2tool.render_tool_schemas``), plus the
  ``"\n\nTask contract:\n" + contract`` suffix ``rails.runner._agent_messages``
  appends when the system text does not already contain the contract.  For
  this carrier ``build_task_contract`` returns the registry itself, so the
  suffix is NOT appended and the registry is counted exactly ONCE -- the
  same "counted once" discipline the SLURP script asserts.
* user = the wire content ``core.model.transport._ordered_speech_feature_
  content`` builds under the resident service's ``speech-query-prefix-v2``
  layout, with each text part wrapped exactly as the transport wraps it.
* the evidence-decode contact's control instruction REFERENCES the task
  contract already present in the system message (post-fix rendering,
  amendment 5b remedy 1, commit 72096bad); the real ``rails.kb_policy``
  source is asserted to still render that way.
* visible knowledge is the m = 5 longest A2T key facets and the 6 longest
  A2T values in the pinned A2T snapshot, which upper-bounds any real fusion
  decision at the LOCKED knobs (fusion_m 5, fusion_c 2, fusion_top_l 3
  admits at most 5 facets and at most 6 values).

SPEECH-FEATURE TOKENS ARE DELIBERATELY COUNTED AS ZERO in the primary bound.
Audio2Tool has no promoted speech-feature packet root (the prior A2T flights
encoded audio live through the mtmd feature cache, not through packets), so
no packet can be measured without first flying a preprocessing pass.  Zero is
the STRICTLY MOST GENEROUS assumption available -- it can only make the
prompt fit more easily -- so a NEGATIVE margin computed at zero speech tokens
is a lower bound on the deficit and cannot be an artefact of the assumption.
A clearly-labelled SECONDARY figure re-states the same envelopes with a
realistic speech allowance derived from the SLURP packets that WERE measured
(the landed np8 receipt records 8.126875 s -> 117 tokens and 5.312 s -> 78
tokens, i.e. about 14.5 feature tokens per audio second) applied to this
carrier's own longest item.  The secondary is a reference, never the gate.

Contacts: 1 GET /props + 1 POST /apply-template and <= 2 POST /tokenize per
envelope, against the RESIDENT session on port 8080.  Zero decode, zero
generated tokens, zero audio decoded, zero gold opened.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python scripts/a2t_g1_prompt_fit.py <output.json>
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
    raise SystemExit(f"package resolved outside this checkout: {_pkg.__file__}")

from speech_aware_evidence_acquisition.core.driver.speech_native import (  # noqa: E402
    _LoopbackPromptAuditClient,
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

# The LOCKED serving profile carried unchanged from the baseline lock verdict
# section 4: the BASE featcache binary at the np8 profile.
MODEL_FRAGMENT_RELPATH = (
    "configs/model/q4km-mmproj-free-speech-native-np8-zcopy-speech-query-prefix-max64.json"
)
PROMPT_ORDER = "speech-query-prefix-v2"
SNAPSHOT_RELPATH = (
    "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/snapshot.json"
)
SNAPSHOT_SHA256 = "ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2"
KB_RECEIPT_RELPATH = "docs/receipts/knowledge/a2t-kb-size-full.json"
CONTROL_CONTACT_ID = "evidence-decode"
FUSION_M = 5
FUSION_VALUE_CEILING = 6  # fusion_c 2 * fusion_top_l 3
SPLIT_ROLE = "discovery"

# A2T emits a JSON CALL LIST, not a single short label.  The locked SLURP
# serving fragment caps completion at 64 tokens, which cannot hold a call
# list; the registered A0 baseline on THIS carrier used 1024
# (configs/model/q4km-featcache.json).  Both are reported.
LOCKED_SLURP_COMPLETION_TOKENS = 64
A2T_A0_COMPLETION_TOKENS = 1024

# Measured on the landed np8 SLURP prompt-fit receipt
# (docs/checks/.../2026-08-24-dev100-c3-prompt-fit-np8/prompt-fit.json):
# 117 tokens / 8.126875 s and 78 tokens / 5.312 s.
SPEECH_FEATURE_TOKENS_PER_SECOND = 117.0 / 8.126875


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def evidence_id(index: int, knowledge_role: str, identifier: str) -> str:
    return f"{index:03d}:{knowledge_role}:{identifier}"


def build_messages(*, system_text, key_texts, value_texts, state_texts):
    """Exactly the transport's own wire assembly for one contact.

    The speech-feature part is a placeholder whose TOKEN cost is added
    separately (see the module docstring): ``_ordered_speech_feature_content``
    emits one opaque media marker for it regardless of the packet behind it,
    so the rendered TEXT is independent of which packet is named.
    """

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
        evidence_texts.append(f"[evidence {evidence_id(index, 'key', 'facet')}] {text}")
        knowledge_roles.append("key")
    for offset, text in enumerate(value_texts):
        index = len(key_texts) + offset
        evidence_texts.append(f"[evidence {evidence_id(index, 'value', 'value')}] {text}")
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
            f"rendered prompt carries {prompt.count(media_marker)} media markers, expected 1"
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

    # --- serving geometry: the LOCKED np8 fragment, cross-checked live -----
    fragment = json.loads(
        (REPO_ROOT / MODEL_FRAGMENT_RELPATH).read_text(encoding="utf-8")
    )
    server_args = [str(token) for token in fragment["server_args"]]
    context_tokens = int(server_args[server_args.index("-c") + 1])
    slot_count = int(server_args[server_args.index("-np") + 1])
    context_per_slot = context_tokens // slot_count
    if fragment["prompt_order"] != PROMPT_ORDER:
        raise SystemExit(f"fragment prompt_order is {fragment['prompt_order']!r}")
    locked_completion_tokens = int(fragment["decoding_params"]["max_tokens"])
    if locked_completion_tokens != LOCKED_SLURP_COMPLETION_TOKENS:
        raise SystemExit(
            "locked fragment max_tokens changed; re-derive the completion budget"
        )

    # --- worst-case text material -----------------------------------------
    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO_ROOT)
    samples = list(adapter.load_split(SPLIT_ROLE))
    if not samples:
        raise SystemExit(f"split_role={SPLIT_ROLE!r} resolved zero samples")
    longest = max(samples, key=lambda s: (float(s.audio_seconds), s.sample_id))

    task_contract = adapter.build_task_contract(longest, None)
    base = tuple(adapter.assemble_prompt(longest, None))
    if len(base) != 2:
        raise SystemExit("assemble_prompt must return exactly system and user messages")
    system_text = base[0]["content"]
    contract_counted_once = task_contract in system_text
    if not contract_counted_once:
        # Same rule as rails.runner._agent_messages.
        system_text = f"{system_text}\n\nTask contract:\n{task_contract}"

    # --- pinned A2T knowledge snapshot -------------------------------------
    receipt = json.loads(
        (REPO_ROOT / KB_RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    if receipt.get("snapshot_sha256") != SNAPSHOT_SHA256:
        raise SystemExit("A2T KB receipt snapshot sha256 does not match the pin")
    snapshot_path = root / SNAPSHOT_RELPATH
    snapshot_bytes = snapshot_path.read_bytes()
    snapshot_file_sha256 = hashlib.sha256(snapshot_bytes).hexdigest()
    snapshot = json.loads(snapshot_bytes.decode("utf-8"))
    # Same pin discipline as scripts/dev100_c3_prompt_fit.py: the receipt and
    # the snapshot must BOTH self-declare the pinned content hash (a file
    # cannot hash to a value it contains, so the self-declared field is the
    # pin and the file-bytes digest is recorded alongside it).
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
            "rails.kb_policy no longer renders the post-fix evidence "
            "instruction this script emulates; re-derive the worst case"
        )
    if task_contract in control_instruction:
        raise SystemExit("post-fix instruction must not re-render the task contract")
    history = [
        {
            "turn": 1,
            "role": "control",
            "contact_id": CONTROL_CONTACT_ID,
            "content": control_instruction,
            "content_sha256": hashlib.sha256(
                control_instruction.encode("utf-8")
            ).hexdigest(),
        }
    ]
    state_texts = _speech_history_texts(history)

    # --- envelopes ---------------------------------------------------------
    envelopes = [
        {
            "envelope_id": "m0-direct-decode",
            "stage_kind": "direct",
            "messages": build_messages(
                system_text=system_text,
                key_texts=[],
                value_texts=[],
                state_texts=[],
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

    client = _LoopbackPromptAuditClient(host="127.0.0.1", port=8080, timeout_seconds=120.0)
    props = client.get_json("/props")
    request_counts = {"GET /props": 1, "POST /apply-template": 0, "POST /tokenize": 0}
    media_marker = props.get("media_marker")
    chat_template = props.get("chat_template")
    if not isinstance(media_marker, str) or not media_marker:
        raise SystemExit("resident props lack a media marker")
    live_slot_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
    if int(live_slot_ctx) != context_per_slot:
        raise SystemExit(
            f"resident slot n_ctx {live_slot_ctx} does not match the locked "
            f"fragment's {context_per_slot}; refusing to certify a geometry "
            "the service does not serve"
        )

    realistic_speech_tokens = int(
        round(float(longest.audio_seconds) * SPEECH_FEATURE_TOKENS_PER_SECOND)
    )

    rows = []
    for envelope in envelopes:
        tokens = text_token_count(
            client, envelope["messages"], media_marker, request_counts
        )
        rows.append(
            {
                "envelope_id": envelope["envelope_id"],
                "stage_kind": envelope["stage_kind"],
                "messages_sha256": canonical_sha256(envelope["messages"]),
                "text_prompt_tokens": tokens,
                # PRIMARY: zero speech tokens, the most generous assumption.
                "prompt_tokens_lower_bound_zero_speech": tokens + 2,
                # SECONDARY reference only.
                "prompt_tokens_with_reference_speech": (
                    tokens + realistic_speech_tokens + 2
                ),
            }
        )

    worst = max(
        rows,
        key=lambda row: (row["prompt_tokens_lower_bound_zero_speech"], row["envelope_id"]),
    )
    maximum_prompt = worst["prompt_tokens_lower_bound_zero_speech"]

    def margin_for(completion_tokens: int, prompt_tokens: int) -> int:
        return context_per_slot - prompt_tokens - completion_tokens

    margin_locked = margin_for(locked_completion_tokens, maximum_prompt)
    margin_a2t = margin_for(A2T_A0_COMPLETION_TOKENS, maximum_prompt)
    margin_a2t_reference = margin_for(
        A2T_A0_COMPLETION_TOKENS, worst["prompt_tokens_with_reference_speech"]
    )
    required_per_slot = (
        worst["prompt_tokens_with_reference_speech"] + A2T_A0_COMPLETION_TOKENS
    )

    report = {
        "schema": "saea-a2t-g1-prompt-fit-v1",
        "study": "speech-aware-evidence-acquisition",
        "scope": "model-free-check",
        "model_contact": False,
        "exposure_run_id": "SAEA-SN-MF-A2T-G1-PROMPT-FIT-NP8",
        "carrier_lock_key": AUDIO2TOOL_LOCK_KEY,
        "split_role": SPLIT_ROLE,
        "split_sample_count": len(samples),
        "longest_sample_id": longest.sample_id,
        "longest_sample_audio_seconds": float(longest.audio_seconds),
        "rendering_source": (
            "rails.runner._agent_messages shapes rendered through "
            "core.model.transport._ordered_speech_feature_content and "
            "_speech_history_texts, with rails.adapters.audio2tool."
            "Audio2ToolAdapter supplying build_task_contract/assemble_prompt. "
            "POST-fix evidence instruction (amendment 5b remedy 1, commit "
            "72096bad) asserted against rails.kb_policy source"
        ),
        "model_fragment": MODEL_FRAGMENT_RELPATH,
        "prompt_order": PROMPT_ORDER,
        "knowledge_snapshot_sha256": SNAPSHOT_SHA256,
        "knowledge_snapshot_id": receipt.get("snapshot_id"),
        "knowledge_snapshot_file_sha256": snapshot_file_sha256,
        "task_contract_characters": len(task_contract),
        "task_contract_sha256": hashlib.sha256(
            task_contract.encode("utf-8")
        ).hexdigest(),
        "task_contract_counted_once": contract_counted_once,
        "visible_key_facets": len(key_texts),
        "visible_values": len(value_texts),
        "agent_state_texts": len(state_texts),
        "speech_feature_tokens_primary_assumption": 0,
        "speech_feature_tokens_reference": realistic_speech_tokens,
        "speech_feature_tokens_per_second_basis": SPEECH_FEATURE_TOKENS_PER_SECOND,
        "speech_packets_measured": [],
        "speech_packets_note": (
            "Audio2Tool has NO promoted speech-feature packet root; the prior "
            "A2T flights encoded audio live through the mtmd feature cache "
            "/home/chao/feat-cache/audio2tool-q4km. The primary bound counts "
            "ZERO speech tokens, which is the most generous assumption "
            "available and therefore makes a negative margin a LOWER BOUND on "
            "the deficit."
        ),
        "special_token_reserve": 2,
        "maximum_text_prompt_tokens": max(row["text_prompt_tokens"] for row in rows),
        "maximum_prompt_tokens_lower_bound_zero_speech": maximum_prompt,
        "maximum_prompt_tokens_with_reference_speech": worst[
            "prompt_tokens_with_reference_speech"
        ],
        "locked_slurp_completion_tokens": locked_completion_tokens,
        "a2t_a0_completion_tokens": A2T_A0_COMPLETION_TOKENS,
        "context_tokens": context_tokens,
        "slot_count": slot_count,
        "context_tokens_per_slot": context_per_slot,
        "context_margin_tokens_locked_completion": margin_locked,
        "context_margin_tokens_a2t_completion": margin_a2t,
        "context_margin_tokens_a2t_completion_reference_speech": margin_a2t_reference,
        "maximum_prompt_fits_one_slot": margin_a2t >= 0,
        "required_context_per_slot": required_per_slot,
        "worst_envelope_id": worst["envelope_id"],
        "envelopes": rows,
        "tokenizer": {
            "request_counts": request_counts,
            "decoder_evaluations": 0,
            "generated_tokens": 0,
            "media_marker": media_marker,
            "chat_template_sha256": hashlib.sha256(
                chat_template.encode("utf-8")
            ).hexdigest(),
            "host": "127.0.0.1",
            "port": 8080,
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
                    "speech_feature_tokens_primary_assumption",
                    "speech_feature_tokens_reference",
                    "maximum_prompt_tokens_lower_bound_zero_speech",
                    "maximum_prompt_tokens_with_reference_speech",
                    "context_tokens_per_slot",
                    "locked_slurp_completion_tokens",
                    "a2t_a0_completion_tokens",
                    "context_margin_tokens_locked_completion",
                    "context_margin_tokens_a2t_completion",
                    "context_margin_tokens_a2t_completion_reference_speech",
                    "required_context_per_slot",
                    "maximum_prompt_fits_one_slot",
                    "worst_envelope_id",
                )
            },
            indent=2,
        )
    )
    for row in report["envelopes"]:
        print(
            f"  {row['envelope_id']:<28} text={row['text_prompt_tokens']:>6} "
            f"lower_bound={row['prompt_tokens_lower_bound_zero_speech']:>6}"
        )
    print("receipt:", output)
    print("receipt_sha256:", hashlib.sha256(output.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
