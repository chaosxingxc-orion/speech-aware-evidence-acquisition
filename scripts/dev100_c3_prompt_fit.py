"""Tokenizer-only prompt-fit bound for the DEV-100 C3 (alpha-blend) prompts.

Why not the existing machinery: `core.driver.speech_native._enumerate_m11_
prompt_envelopes` drives `run_speech_native_match_tasks` over KeyCardV1 +
DecisionGraphV1 and hard-requires `top_k in [2, min(3, key count)]`. The C3
controller does not use key cards, a decision graph, or that constructor at
all -- its prompt shapes come from `rails.runner._agent_messages`. Forcing the
M11 enumerator would certify the wrong prompt, so this script renders the C3
shapes through the REAL runner/transport functions instead and bounds them
conservatively.

What is rendered (worst case, not typical):

* system = SlurpAdapter's fixed instruction + "\n\nTask contract:\n" + the
  FULL TRAIN ontology roster (`_agent_messages` appends the contract when the
  system text does not already contain it).
* user   = the wire content `core.model.transport._ordered_speech_feature_
  content` builds under the resident service's `speech-query-prefix-v2`
  layout, with each text part wrapped exactly as the transport wraps it
  (`[evidence <id>] <text>` / `[agent control <contact_id>] <content>`).
* the evidence-decode contact's control instruction REFERENCES the task
  contract already present in the system message (post-fix rendering,
  amendment 5b remedy 1, commit 72096bad) -- the roster is counted ONCE,
  and this script asserts the real kb_policy source still renders that way.
* the m = 5 longest fused values and the 5 longest key facets in the pinned
  snapshot are used as the visible knowledge, which upper-bounds any real
  fusion decision at these knobs (fusion_m 5, fusion_c 2, fusion_top_l 3
  admits at most 5 facets and at most 6 values; the 5 longest values plus 1
  more longest value is taken to cover the c*l ceiling).
* speech-feature tokens are the maximum over the 5 longest DEV-100 packets,
  read from the promoted packets themselves.

Contacts: 1 GET /props + 1 POST /apply-template and <= 2 POST /tokenize per
envelope, against the RESIDENT session on port 8080. Zero decode, zero
generated tokens.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python scripts/dev100_c3_prompt_fit.py <output.json>
"""

from __future__ import annotations
import os

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
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
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter  # noqa: E402

MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np8-zcopy-speech-query-prefix-max64"
DATASET_FRAGMENT = "slurp-speech-native-dev100"
BASELINE_FRAGMENT = "slurp-dev100-kb-alpha-blend"
EXPERIMENT_FRAGMENT = "slurp-dev100-kb-alpha-blend-campaign-v1"
PROMPT_ORDER = "speech-query-prefix-v2"
FEATURE_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
SNAPSHOT_PATH = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET") + "/knowledge/slurp/"
    "saea-kb-distmodel-v1/size-full/snapshot.json"
)
SNAPSHOT_SHA256 = "e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57"
CONTROL_CONTACT_ID = "evidence-decode"
LONGEST_SAMPLE_COUNT = 5
FUSION_M = 5
FUSION_VALUE_CEILING = 6  # fusion_c 2 * fusion_top_l 3


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def evidence_id(index: int, knowledge_role: str, identifier: str) -> str:
    return f"{index:03d}:{knowledge_role}:{identifier}"


def build_messages(*, system_text, key_texts, value_texts, state_texts, packet):
    """Exactly the transport's own wire assembly for one C3 contact."""

    feature_parts = [
        {
            "type": "input_speech_features",
            "speech_features": {
                "packet_id": packet["packet_id"],
                "sha256": packet["packet_sha256"],
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


def text_token_count(client, messages, media_marker, response_format):
    body = {"messages": list(messages)}
    if response_format is not None:
        body["response_format"] = response_format
    rendered = client.post_json("/apply-template", body)
    prompt = rendered.get("prompt")
    if not isinstance(prompt, str):
        raise SystemExit("apply-template returned no prompt")
    if prompt.count(media_marker) != 1:
        raise SystemExit(
            f"rendered prompt carries {prompt.count(media_marker)} media markers, expected 1"
        )
    total = 0
    segments = 0
    for segment in prompt.split(media_marker):
        if not segment:
            continue
        response = client.post_json(
            "/tokenize",
            {"content": segment, "add_special": False, "parse_special": True},
        )
        tokens = response.get("tokens")
        if not isinstance(tokens, list):
            raise SystemExit("tokenize returned no token list")
        total += len(tokens)
        segments += 1
    return total, segments


def main() -> int:
    # Optional argv[2] selects the model fragment (attempt-6 base-build
    # serving variant); the default remains the registered np8 zcopy
    # fragment. The receipt's config_hash/config_fragments self-describe
    # whichever composition was measured.
    model_fragment = sys.argv[2] if len(sys.argv) > 2 else MODEL_FRAGMENT
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    composed = compose(
        REPO_ROOT, model_fragment, DATASET_FRAGMENT, BASELINE_FRAGMENT, EXPERIMENT_FRAGMENT
    )
    values = composed.values
    if values["prompt_order"] != PROMPT_ORDER:
        raise SystemExit(f"composed prompt_order is {values['prompt_order']!r}")
    server_args = values["server_args"]
    context_tokens = int(server_args[server_args.index("-c") + 1])
    slot_count = int(server_args[server_args.index("-np") + 1])
    context_per_slot = context_tokens // slot_count
    maximum_completion_tokens = int(values["decoding_params"]["max_tokens"])

    # --- worst-case text material ------------------------------------------
    adapter = SlurpAdapter(lock, root, repo_root=REPO_ROOT)
    view = json.loads(
        (REPO_ROOT / "configs" / "dataset" / f"{DATASET_FRAGMENT}.json").read_text(
            encoding="utf-8"
        )
    )
    items = sorted(view["items"], key=lambda item: -float(item["audio_seconds"]))
    longest = items[:LONGEST_SAMPLE_COUNT]

    class _Sample:
        def __init__(self, item):
            self.sample_id = item["sample_id"]
            self.media_relpath = item["media_relpath"]

    sample = _Sample(longest[0])
    task_contract = adapter.build_task_contract(sample, None)
    base = tuple(adapter.assemble_prompt(sample, None))
    system_text = base[0]["content"]
    if task_contract not in system_text:
        system_text = f"{system_text}\n\nTask contract:\n{task_contract}"

    # Same pin discipline as analysis.m11_operating_point_sweep: the receipt
    # and the snapshot must both self-declare the pinned content hash.
    receipt = json.loads(
        (REPO_ROOT / "docs" / "receipts" / "knowledge" / "slurp-kb-size-full.json").read_text(
            encoding="utf-8"
        )
    )
    if receipt.get("snapshot_sha256") != SNAPSHOT_SHA256:
        raise SystemExit("KB receipt snapshot sha256 does not match the pin")
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if snapshot.get("snapshot_sha256") != SNAPSHOT_SHA256:
        raise SystemExit("KB snapshot self-declared sha256 does not match the pin")
    if snapshot.get("source_partition_role") != "train":
        raise SystemExit("KB snapshot is not TRAIN-sourced")
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

    # POST-fix rendering (amendment 5b remedy 1, commit 72096bad): the
    # evidence contact's instruction REFERENCES the contract already present
    # in the system message instead of re-rendering it. This emulation is
    # bound to the real controller source below so a later kb_policy wording
    # change breaks this script loudly instead of silently certifying a
    # prompt the campaign no longer sends.
    control_instruction = (
        "Decide under the task contract already given above, now "
        "considering the retrieved evidence. Answer using the speech "
        "query together with the supplied knowledge evidence."
    )
    import inspect

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

    # --- speech feature tokens over the longest DEV-100 packets ------------
    packet_rows = []
    for item in longest:
        packet = load_speech_feature_packet(FEATURE_ROOT, item["packet_id"])
        tokens = sum(chunk.n_tokens for chunk in packet.chunks)
        packet_rows.append(
            {
                "packet_id": packet.packet_id,
                "packet_sha256": packet.packet_sha256,
                "audio_seconds": item["audio_seconds"],
                "feature_tokens": tokens,
            }
        )
    packet_rows.sort(key=lambda row: (-row["feature_tokens"], row["packet_id"]))
    maximum_speech_feature_tokens = packet_rows[0]["feature_tokens"]

    # --- envelopes ---------------------------------------------------------
    envelopes = [
        {
            "envelope_id": "direct-decode",
            "stage_kind": "direct",
            "messages": build_messages(
                system_text=system_text,
                key_texts=[],
                value_texts=[],
                state_texts=[],
                packet=packet_rows[0],
            ),
        },
        {
            "envelope_id": "evidence-decode-worst",
            "stage_kind": "evidence",
            "messages": build_messages(
                system_text=system_text,
                key_texts=key_texts,
                value_texts=value_texts,
                state_texts=state_texts,
                packet=packet_rows[0],
            ),
        },
    ]

    client = _LoopbackPromptAuditClient(host="127.0.0.1", port=8080, timeout_seconds=120.0)
    props = client.get_json("/props")
    media_marker = props.get("media_marker")
    chat_template = props.get("chat_template")
    if not isinstance(media_marker, str) or not media_marker:
        raise SystemExit("resident props lack a media marker")
    request_counts = {"GET /props": 1, "POST /apply-template": 0, "POST /tokenize": 0}

    rows = []
    for envelope in envelopes:
        tokens, segments = text_token_count(
            client, envelope["messages"], media_marker, None
        )
        request_counts["POST /apply-template"] += 1
        request_counts["POST /tokenize"] += segments
        upper = tokens + maximum_speech_feature_tokens + 2
        rows.append(
            {
                "envelope_id": envelope["envelope_id"],
                "stage_kind": envelope["stage_kind"],
                "messages_sha256": canonical_sha256(envelope["messages"]),
                "text_prompt_tokens": tokens,
                "prompt_tokens_upper_bound": upper,
            }
        )

    worst = max(rows, key=lambda row: (row["prompt_tokens_upper_bound"], row["envelope_id"]))
    maximum_prompt = worst["prompt_tokens_upper_bound"]
    margin = context_per_slot - maximum_prompt - maximum_completion_tokens

    report = {
        "schema": "saea-dev100-c3-prompt-fit-v1",
        "study": "speech-aware-evidence-acquisition",
        "scope": "model-free-check",
        "model_contact": False,
        "exposure_run_id": "SAEA-SN-MF-DEV100-C3-PROMPT-FIT-NP8",
        "rendering_source": (
            "rails.runner._agent_messages shapes rendered through "
            "core.model.transport._ordered_speech_feature_content and "
            "_speech_history_texts; the M11 enumerator is constructor-specific "
            "and does not describe the C3 chain. POST-fix evidence instruction "
            "(amendment 5b remedy 1, commit 72096bad): references the contract "
            "in the system message, asserted against rails.kb_policy source"
        ),
        "config_hash": composed.config_hash,
        "config_fragments": composed.fragments,
        "prompt_order": PROMPT_ORDER,
        "knowledge_snapshot_sha256": SNAPSHOT_SHA256,
        "task_contract_characters": len(task_contract),
        "task_contract_sha256": hashlib.sha256(
            task_contract.encode("utf-8")
        ).hexdigest(),
        "visible_key_facets": len(key_texts),
        "visible_values": len(value_texts),
        "agent_state_texts": len(state_texts),
        "speech_packets_measured": packet_rows,
        "maximum_speech_feature_tokens": maximum_speech_feature_tokens,
        "special_token_reserve": 2,
        "maximum_text_prompt_tokens": max(row["text_prompt_tokens"] for row in rows),
        "maximum_prompt_tokens_upper_bound": maximum_prompt,
        "maximum_completion_tokens": maximum_completion_tokens,
        "context_tokens": context_tokens,
        "slot_count": slot_count,
        "context_tokens_per_slot": context_per_slot,
        "context_margin_tokens": margin,
        "maximum_prompt_fits_one_slot": margin >= 0,
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
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in (
        "maximum_text_prompt_tokens",
        "maximum_speech_feature_tokens",
        "maximum_prompt_tokens_upper_bound",
        "context_tokens_per_slot",
        "maximum_completion_tokens",
        "context_margin_tokens",
        "maximum_prompt_fits_one_slot",
        "worst_envelope_id",
    )}, indent=2))
    print("receipt:", output)
    print("receipt_sha256:", hashlib.sha256(output.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
