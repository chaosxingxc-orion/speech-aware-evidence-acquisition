#!/usr/bin/env python3
"""Window fit for the Earnings-22 DEV ESB prompt A/B cells, before any contact.

Sibling of ``scripts/a2t_calibration_prompt_fit.py`` for the Earnings carrier,
and the executable form of section 5.1 of
``docs/readiness/2026-09-05-e22-dev-esb-prompt-ab-v1-preregistration.md``.

**Zero contacts of every kind**: no model, no server, no tokenizer, no socket.
The arithmetic below is the whole method, and it is the same one the sealed
2026-09-04 ESB test flight used and then confirmed live to the token:

* SPEECH cost is the mmproj encoder's exact one-second window rule
  ``n_tokens = 13 * ceil(audio_seconds)``. That rule reproduces all 342 sealed
  ``COST`` records of ``SAEA-E-005B-N10-zero``, all 400 per-packet counts of the
  Audio2Tool calibration promotion receipt, and the ESB test flight's measured
  530-token worst prompt (``13 * ceil(36.360125) = 481`` plus a 49-token text
  envelope) without exception.
* TEXT is the envelope the ESB test smoke MEASURED: exactly 49 tokens on all
  four of its requests, for arm A's three-sentence instruction plus a bare
  audio user turn. Arm A here sends that identical instruction, so 49 is its
  measured envelope rather than a guess; arm B's instruction is one short
  sentence, so 49 is a strict upper bound for it. The smoke re-measures both.
* The FIT RULE is this repository's own, unchanged: a request may occupy at
  most half its slot, ``slot_tokens >= 2 * worst_required``, and the slot must
  be a multiple of 512 so llama-server's own rounding cannot move it.

Why this matters for THIS roster and not merely as a formality: the dev
subset10's longest ESB utterance is 78.36 s against the test subset's 36.36 s,
which is exactly why the sealed flight's ``-c 32768 -np 8`` geometry is refused
here and a 5,120-token slot is registered instead.

2026-09-05 addition, for the shape-C arm: a second, OPTIONAL mode (``--render``)
that proves the RENDERED chat template instead of the arithmetic. It is needed
because arm C asserts something arithmetic cannot see -- that the pinned GGUF
chat template really emits NO system block when the request carries no system
message, and that the audio placeholder really precedes the instruction text. A
template that quietly injected a default system prompt would make the whole
experiment measure something other than what it claims. The mode spawns the
gated server and calls only ``GET /props``, ``POST /apply-template`` and ``POST
/tokenize``; **nothing decodes and zero tokens are generated**. Arms A and B are
rendered beside arm C as the control that the check can see a system block when
there is one.

Usage::

    python scripts/e22_dev_esb_prompt_fit.py --write
    python scripts/e22_dev_esb_prompt_fit.py --render --write --output <path>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[1]
CHECK = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-e22-dev-esb-prompt-ab-v1"
)
DEFAULT_OUTPUT = CHECK / "prompt-fit" / "prompt-fit.json"

#: The mmproj encoder's exact one-second window rule.
SPEECH_TOKENS_PER_SECOND_WINDOW = 13
#: Measured, not assumed: the ESB test smoke's text envelope for arm A's
#: instruction plus a bare audio user turn, identical on all four requests.
MEASURED_TEXT_ENVELOPE_TOKENS = 49
MEASURED_TEXT_ENVELOPE_SOURCE = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-04-e22-esb-shortform-alignment-400-v1/smoke/smoke.json"
)
#: Two special tokens, the same allowance the sealed flights carried.
SPECIAL_TOKENS = 2
#: slot_tokens >= FIT_MULTIPLE * worst_required.
FIT_MULTIPLE = 2


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path: Path) -> Mapping[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def speech_tokens(audio_seconds: float) -> int:
    return SPEECH_TOKENS_PER_SECOND_WINDOW * math.ceil(float(audio_seconds))


def build(*, dataset: str, model: str, baselines: tuple[str, ...]) -> dict[str, Any]:
    dataset_doc = _load(REPO / "configs" / "dataset" / f"{dataset}.json")
    model_doc = _load(REPO / "configs" / "model" / f"{model}.json")
    roster_relpath = str(dataset_doc["e22_esb_roster_receipt"])
    roster_path = REPO / roster_relpath
    measured_roster_sha256 = sha256_file(roster_path)
    if measured_roster_sha256 != str(dataset_doc["e22_esb_roster_receipt_sha256"]):
        raise SystemExit(
            "roster receipt hashes to %s, not the dataset fragment's %s"
            % (measured_roster_sha256, dataset_doc["e22_esb_roster_receipt_sha256"])
        )
    roster = _load(roster_path)
    items = list(roster["items"])
    if len(items) != int(roster["count"]):
        raise SystemExit("roster count disagrees with its items")

    geometry = model_doc["serving_geometry"]
    slot_tokens = int(geometry["slot_tokens"])
    slots = int(geometry["slots"])
    max_tokens = int(geometry["max_tokens"])
    server_args = [str(value) for value in model_doc["server_args"]]
    declared_c = int(server_args[server_args.index("-c") + 1])
    declared_np = int(server_args[server_args.index("-np") + 1])
    if declared_np != slots or declared_c != slots * slot_tokens:
        raise SystemExit("model fragment server_args disagree with its serving_geometry")

    longest = max(items, key=lambda item: float(item["audio_seconds"]))
    longest_seconds = float(longest["audio_seconds"])
    worst_speech = speech_tokens(longest_seconds)
    worst_required = worst_speech + MEASURED_TEXT_ENVELOPE_TOKENS + max_tokens + SPECIAL_TOKENS

    per_arm = {}
    for baseline in baselines:
        baseline_doc = _load(REPO / "configs" / "baseline" / f"{baseline}.json")
        instruction = str(baseline_doc["task_instruction"])
        per_arm[baseline] = {
            "task_instruction": instruction,
            "task_instruction_sha256": hashlib.sha256(
                instruction.encode("utf-8")
            ).hexdigest(),
            "task_instruction_chars": len(instruction),
            "task_instruction_whitespace_words": len(instruction.split()),
            "text_envelope_tokens_bound": MEASURED_TEXT_ENVELOPE_TOKENS,
            "text_envelope_basis": (
                "measured exactly for this instruction by the 2026-09-04 ESB test smoke"
                if instruction.startswith("Transcribe the speech verbatim")
                else (
                    "strict upper bound: this arm's instruction is shorter than the "
                    "one the 2026-09-04 ESB test smoke measured at 49 tokens, and "
                    "dropping the system message (omit_system_message) can only "
                    "REMOVE template scaffolding, never add any. The exact figure is "
                    "measured by --render through /apply-template + /tokenize and "
                    "again by this arm's own smoke."
                )
            ),
            "worst_required_tokens": worst_required,
            "slot_tokens": slot_tokens,
            "margin_tokens": slot_tokens - worst_required,
            "ratio": round(slot_tokens / worst_required, 4),
            "fits": slot_tokens >= FIT_MULTIPLE * worst_required,
        }

    prior_geometry_slot_tokens = 4096
    total_speech = sum(speech_tokens(item["audio_seconds"]) for item in items)
    return {
        "schema": "saea-e22-esb-prompt-fit-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "contacts": {
            "model": 0,
            "server": 0,
            "tokenizer": 0,
            "socket": 0,
            "generated_tokens": 0,
            "basis": (
                "arithmetic only: the encoder's exact one-second window rule plus a text "
                "envelope the 2026-09-04 ESB test smoke already measured. Nothing is "
                "started, opened or asked."
            ),
        },
        "fragments": {
            "dataset": dataset,
            "model": model,
            "baselines": list(baselines),
        },
        "roster": {
            "relpath": roster_relpath,
            "sha256": measured_roster_sha256,
            "count": len(items),
            "audio_seconds_total": round(
                sum(float(item["audio_seconds"]) for item in items), 6
            ),
        },
        "rule": {
            "speech": "n_tokens = 13 * ceil(audio_seconds)",
            "speech_basis": (
                "reproduces all 342 sealed COST records of SAEA-E-005B-N10-zero, all 400 "
                "per-packet counts of the A2T calibration promotion receipt, and the ESB "
                "test flight's measured 530-token worst prompt without exception"
            ),
            "text_envelope_tokens": MEASURED_TEXT_ENVELOPE_TOKENS,
            "text_envelope_source": MEASURED_TEXT_ENVELOPE_SOURCE,
            "special_tokens": SPECIAL_TOKENS,
            "fit": f"slot_tokens >= {FIT_MULTIPLE} * worst_required, slot a multiple of 512",
        },
        "geometry": {
            "server_args_c": declared_c,
            "server_args_np": declared_np,
            "slots": slots,
            "slot_tokens": slot_tokens,
            "slot_tokens_is_multiple_of_512": slot_tokens % 512 == 0,
            "max_tokens": max_tokens,
        },
        "worst_case": {
            "sample_id": str(longest["sample_id"]),
            "audio_seconds": longest_seconds,
            "speech_tokens": worst_speech,
            "text_envelope_tokens": MEASURED_TEXT_ENVELOPE_TOKENS,
            "completion_ceiling_tokens": max_tokens,
            "special_tokens": SPECIAL_TOKENS,
            "worst_required_tokens": worst_required,
        },
        "per_arm": per_arm,
        "why_the_sealed_geometry_is_refused": {
            "sealed_flight": "SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1, -c 32768 -np 8",
            "sealed_slot_tokens": prior_geometry_slot_tokens,
            "required_at_fit_rule": FIT_MULTIPLE * worst_required,
            "fits": prior_geometry_slot_tokens >= FIT_MULTIPLE * worst_required,
            "note": (
                "the sealed flight's 4096-token slot cannot hold this roster's longest "
                "request at the fit rule, which is what forces deviation G1"
            ),
        },
        "aggregate_projection": {
            "speech_tokens_total_one_arm": total_speech,
            "prompt_tokens_projection_one_arm": total_speech
            + MEASURED_TEXT_ENVELOPE_TOKENS * len(items),
            "note": (
                "a projection for the flight to be checked against, not a measurement. The "
                "ESB test flight's own aggregate came within 0.11 % of the same arithmetic."
            ),
        },
    }


RENDER_RUN_ID = "SAEA-E22-DEV-ESB-SHAPE-C-PROMPT-FIT-V1"
RENDER_EXPERIMENT = "e22-dev-esb-shape-c-v1"
RENDER_BASELINES = (
    "e22-esb-dev-prompt-a",
    "e22-esb-dev-prompt-b",
    "e22-esb-dev-shape-c",
)
RENDER_SPLIT_IDENTITY_HASH = (
    "fc14c98bae814f1c70314393078c9aa360e3638f82bd2e77d1ddb962f8bdebb3"
)
RUNTIME_ROOT = Path("/home/chao")
#: Nominal: this route decodes nothing. It still opens a gated session, so it
#: carries a plan and an exposure row of its own, exactly as
#: ``scripts/a2t_calibration_prompt_fit.py`` does.
RENDER_PLAN_CALLS = 1
RENDER_PLAN_AUDIO = 1
RENDER_PLAN_GPU_HOURS = 0.3
#: The literal a Qwen chat template writes when it opens a system block. Its
#: ABSENCE from the rendered prompt is the shape-C proof; its PRESENCE in arms
#: A and B is the control that proves the check can see one.
SYSTEM_BLOCK_MARKER = "<|im_start|>system"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_sha256(document: Any) -> str:
    blob = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _log(message: str) -> None:
    print(
        "[%s] %s" % (datetime.now(tz=timezone.utc).strftime("%H:%M:%SZ"), message),
        flush=True,
    )


def _text_token_count(client, counts, messages, media_marker) -> tuple[int, str]:
    """``(text tokens, rendered prompt)`` for one message list.

    The same technique ``scripts/a2t_calibration_prompt_fit.py`` established:
    ``POST /apply-template`` renders the EXACT wire messages through the pinned
    GGUF chat template, and ``POST /tokenize`` counts the rendered text around
    the single opaque media marker ``GET /props`` reports. Nothing decodes.
    """

    rendered = client.request_json("POST", "/apply-template", {"messages": list(messages)})
    counts["POST /apply-template"] += 1
    prompt = rendered.get("prompt")
    if not isinstance(prompt, str) or not prompt:
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
        response = client.request_json(
            "POST",
            "/tokenize",
            {"content": segment, "add_special": False, "parse_special": True},
        )
        counts["POST /tokenize"] += 1
        tokens = response.get("tokens")
        if not isinstance(tokens, list):
            raise SystemExit("tokenize returned no token list")
        total += len(tokens)
    return total, prompt


def render(
    *,
    dataset: str,
    model: str,
    experiment: str,
    baselines: tuple[str, ...],
    run_id: str,
    split_identity_hash: str,
    gate_baseline: str,
) -> dict[str, Any]:
    """Prove the RENDERED chat template for each arm, at zero generated tokens.

    Why this exists and why it is not an arithmetic exercise: the shape-C arm
    asserts something arithmetic cannot see -- that the pinned GGUF chat
    template really emits NO system block when the request carries no system
    message, and that the audio placeholder really precedes the instruction
    text. A template that silently injects a default system prompt would make
    the whole experiment measure something other than what it claims, and only
    the live template can say. Arms A and B are rendered beside it as the
    control: the same check must SEE their system block.

    The wire messages are not rebuilt here. They are taken from the REAL
    ``core.model.transport.LlamaServerTransport``, resolved through the same
    ``TRANSPORTS`` registry entry and the same composed config the flight
    uses, driven with a real ``core.policies.build_arm_payload`` payload, with
    only its ``_post`` replaced by a capture -- so what is rendered is what the
    flight sends, byte for byte, rather than a second spelling of it.
    """

    import os
    import time

    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
        raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

    import speech_aware_evidence_acquisition as _pkg

    if (
        Path(_pkg.__file__ or "")
        != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"
    ):
        raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate
    from speech_aware_evidence_acquisition.core.base import TRANSPORTS
    from speech_aware_evidence_acquisition.core.config import (
        compose,
        d1_media_supplement_relpath,
        d1_media_supplement_sha256,
        model_materialization_root,
    )
    from speech_aware_evidence_acquisition.core.driver.speech_native import (
        _LoopbackPromptAuditClient,
    )
    from speech_aware_evidence_acquisition.core.flight.runtime import merge_server_args
    from speech_aware_evidence_acquisition.core.policies import build_arm_payload
    from speech_aware_evidence_acquisition.core.session import (
        load_runtime_receipt,
        start_session,
        stop_session,
    )
    from speech_aware_evidence_acquisition.data.lock import data_root
    from speech_aware_evidence_acquisition.data.loader import SampleRef

    composed_by_baseline = {
        baseline: compose(REPO, model, dataset, baseline, experiment)
        for baseline in baselines
    }
    if gate_baseline not in composed_by_baseline:
        raise SystemExit("gate baseline %r is not among the rendered arms" % gate_baseline)
    gate_composed = composed_by_baseline[gate_baseline]
    values = gate_composed.values
    root = data_root()

    dataset_doc = _load(REPO / "configs" / "dataset" / f"{dataset}.json")
    roster_relpath = str(dataset_doc["e22_esb_roster_receipt"])
    roster_path = REPO / roster_relpath
    measured_roster_sha256 = sha256_file(roster_path)
    if measured_roster_sha256 != str(dataset_doc["e22_esb_roster_receipt_sha256"]):
        raise SystemExit("roster receipt hash drift; refusing to render")
    roster = _load(roster_path)
    # The media stand-in: the roster's SHORTEST utterance, deterministic
    # (sorted by (seconds, sample_id)). The audio is a single opaque marker in
    # the rendered prompt, so which wav it is cannot change a text count; the
    # shortest keeps the /apply-template request small.
    shortest = min(
        roster["items"],
        key=lambda item: (float(item["audio_seconds"]), str(item["sample_id"])),
    )
    ref = SampleRef(
        carrier_lock_key=str(roster["carrier"]),
        sample_id=str(shortest["sample_id"]),
        media_relpath=str(shortest["media_relpath"]),
        audio_seconds=float(shortest["audio_seconds"]),
        sample_rate_hz=int(shortest["sample_rate_hz"]),
    )
    _log(
        "media stand-in %s (%.6f s) -> %s"
        % (ref.sample_id, ref.audio_seconds, ref.media_relpath)
    )

    geometry = values["serving_geometry"]
    slots = int(geometry["slots"])
    slot_tokens = int(geometry["slot_tokens"])
    max_tokens = int(geometry["max_tokens"])

    plan = ExecutionPlan(
        run_id=run_id,
        execution_profile=str(values["execution_profile"])
        if "execution_profile" in values
        else "baseline-reproduction",
        carrier_lock_key=str(values["carrier_lock_key"]),
        split_role=str(dataset_doc["e22_esb_split_role"]),
        split_identity_hash=split_identity_hash,
        planned_model_calls=RENDER_PLAN_CALLS,
        planned_gpu_hours=RENDER_PLAN_GPU_HOURS,
        planned_speech_audio_seconds=RENDER_PLAN_AUDIO,
        protocol_hash=gate_composed.config_hash,
        attempt_id="attempt-%s-e22shapecfit"
        % datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    ).validate()
    configured_model_root = model_materialization_root(values)
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath=str(values["runtime_receipt"]),
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=(Path(configured_model_root) if configured_model_root else None),
        d1_media_supplement_relpath=d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values),
    )
    lock_sha256 = gate.assert_model_touch_allowed(plan)
    _log("frozen-core gate PASS (lock %s)" % lock_sha256[:12])

    runtime_receipt = load_runtime_receipt(REPO / "docs" / str(values["runtime_receipt"]))
    run_dir = root / "runs" / run_id / str(plan.attempt_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    extra_argv = merge_server_args(
        values["server_args"], slots=slots, context_tokens=slots * slot_tokens
    )
    port = int(str(values["base_url"]).rsplit(":", 1)[-1])
    _log("spawning llama-server on %d: %s" % (port, " ".join(extra_argv)))
    started_at = time.time()
    session = start_session(
        runtime_root=RUNTIME_ROOT,
        data_root=root,
        runtime_receipt=runtime_receipt,
        host="127.0.0.1",
        port=port,
        session_id="%s-%s" % (run_id, plan.attempt_id),
        extra_argv=extra_argv,
        extra_env=dict(values.get("server_env", {})),
        receipt_path=run_dir / "session.receipt.json",
        server_log_path=run_dir / "session.server.log",
        role=str(runtime_receipt.get("role", "legacy")),
        model_root=(Path(configured_model_root) if configured_model_root else None),
        ready_timeout_seconds=1800.0,
    )
    load_seconds = time.time() - started_at
    _log("server up in %.1fs: pid=%s port=%s" % (load_seconds, session.pid, session.port))

    counts = {
        "GET /props": 0,
        "POST /apply-template": 0,
        "POST /tokenize": 0,
        "generations": 0,
    }
    per_arm: dict[str, Any] = {}
    live_slot_ctx: object = None
    chat_template_sha256 = ""
    media_marker = ""
    try:
        client = _LoopbackPromptAuditClient(
            host="127.0.0.1", port=port, timeout_seconds=180.0
        )
        props = client.request_json("GET", "/props", None)
        counts["GET /props"] += 1
        media_marker = props.get("media_marker")
        if not isinstance(media_marker, str) or not media_marker:
            raise SystemExit("resident props lack a media marker")
        live_slot_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
        if int(live_slot_ctx) < slot_tokens:
            raise SystemExit(
                "resident slot n_ctx %s is smaller than the fragment's declared %d"
                % (live_slot_ctx, slot_tokens)
            )
        chat_template = props.get("chat_template")
        chat_template_sha256 = (
            sha256_text(chat_template) if isinstance(chat_template, str) else ""
        )
        _log("props OK: slot n_ctx=%s, media marker %r" % (live_slot_ctx, media_marker))

        for baseline in baselines:
            composed = composed_by_baseline[baseline]
            arm_values = composed.values
            instruction = str(arm_values["task_instruction"])
            payload = build_arm_payload(
                arm=str(arm_values["arm"]),
                ref=ref,
                request_id="e22esb-promptfit-%s" % baseline,
                task_instruction=instruction,
                decoding_params=dict(arm_values["decoding_params"]),
            )
            # The REAL transport, resolved through the REAL registry entry from
            # the REAL composed config -- only its HTTP sender is replaced, so
            # the messages captured below are the flight's own wire bytes.
            captured: dict[str, Any] = {}

            def _capture(url, body, _captured=captured):
                _captured["body"] = json.loads(body.decode("utf-8"))
                return json.dumps(
                    {
                        "choices": [{"message": {"content": ""}}],
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                    }
                ).encode("utf-8")

            transport = TRANSPORTS.resolve(str(arm_values["transport"]))(
                arm_values,
                root,
                session=session,
                runtime_receipt=runtime_receipt,
                runtime_root=RUNTIME_ROOT,
            )
            transport._post = _capture
            transport(json.dumps(payload).encode("utf-8"))
            messages = captured["body"]["messages"]
            roles = [str(message["role"]) for message in messages]

            tokens, prompt = _text_token_count(client, counts, messages, media_marker)
            system_block_rendered = SYSTEM_BLOCK_MARKER in prompt
            marker_index = prompt.index(media_marker)
            instruction_indexes = [
                index
                for index in range(len(prompt))
                if prompt.startswith(instruction, index)
            ]
            audio_precedes_instruction = bool(instruction_indexes) and all(
                index > marker_index for index in instruction_indexes
            )
            speech_tokens_shortest = speech_tokens(ref.audio_seconds)
            per_arm[baseline] = {
                "config_hash": composed.config_hash,
                "arm": str(arm_values["arm"]),
                "task_instruction": instruction,
                "task_instruction_sha256": sha256_text(instruction),
                "omit_system_message": bool(arm_values.get("omit_system_message", False)),
                "user_turn_text": arm_values.get("user_turn_text"),
                "user_turn_audio_first": bool(
                    arm_values.get("user_turn_audio_first", True)
                ),
                "wire_message_roles": roles,
                "wire_messages_sha256": canonical_sha256(messages),
                "wire_user_content_types": [
                    str(part.get("type"))
                    for message in messages
                    if message["role"] == "user"
                    for part in message["content"]
                ],
                "rendered_prompt": prompt,
                "rendered_prompt_sha256": sha256_text(prompt),
                "rendered_prompt_chars": len(prompt),
                "rendered_text_tokens": tokens,
                "system_block_rendered": system_block_rendered,
                "instruction_verbatim_in_rendered_prompt": bool(instruction_indexes),
                "audio_placeholder_precedes_instruction": audio_precedes_instruction,
                "media_marker_char_index": marker_index,
                "instruction_char_indexes": instruction_indexes,
                "worst_required_tokens": (
                    speech_tokens(float(roster["audio_seconds_longest_item"]))
                    + tokens
                    + max_tokens
                    + SPECIAL_TOKENS
                ),
                "media_stand_in_speech_tokens": speech_tokens_shortest,
            }
            _log(
                "rendered %s: roles=%s system_block=%s text_tokens=%d audio_first=%s"
                % (
                    baseline,
                    roles,
                    system_block_rendered,
                    tokens,
                    audio_precedes_instruction,
                )
            )
    finally:
        stop_out = stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
            receipt_path=run_dir / "session.stop-receipt.json",
            force_after_timeout=True,
        )
        _log(
            "server stopped: %s forced=%s"
            % (stop_out.get("termination_signal"), stop_out.get("forced"))
        )

    shape_c = per_arm.get("e22-esb-dev-shape-c", {})
    controls = {
        name: entry for name, entry in per_arm.items() if name != "e22-esb-dev-shape-c"
    }
    proof = {
        "shape_c_sends_no_system_message": (
            shape_c.get("wire_message_roles") == ["user"]
            and shape_c.get("system_block_rendered") is False
        ),
        "shape_c_audio_precedes_the_instruction": bool(
            shape_c.get("audio_placeholder_precedes_instruction")
        ),
        "shape_c_instruction_is_on_the_wire": bool(
            shape_c.get("instruction_verbatim_in_rendered_prompt")
        ),
        "controls_still_render_a_system_block": all(
            entry.get("system_block_rendered") is True
            and entry.get("wire_message_roles") == ["system", "user"]
            for entry in controls.values()
        ),
        "control_arms": sorted(controls),
        "why_the_controls_matter": (
            "an absent system block only proves anything if the same check can SEE "
            "one; arms A and B are rendered through the identical route and must "
            "still show theirs. It also proves the pinned template does not inject a "
            "default system prompt of its own when the request carries none -- which, "
            "if it did, would make this whole experiment measure something else."
        ),
    }
    proof["all_assertions_hold"] = all(
        value is True
        for key, value in proof.items()
        if key.startswith(("shape_c_", "controls_"))
    )
    return {
        "schema": "saea-e22-esb-prompt-fit-render-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "run_id": run_id,
        "attempt_id": str(plan.attempt_id),
        "contacts": {
            **counts,
            "generated_tokens": 0,
            "basis": (
                "only GET /props, POST /apply-template and POST /tokenize are called, "
                "none of which decodes. The server is spawned under a gate-checked "
                "contracts.ExecutionPlan bound to this run id's own exposure row and "
                "stopped with its own stop receipt."
            ),
        },
        "fragments": {
            "dataset": dataset,
            "model": model,
            "experiment": experiment,
            "baselines": list(baselines),
            "gate_baseline": gate_baseline,
        },
        "server": {
            "build_commit": str(
                (runtime_receipt.get("llama_cpp") or {}).get("build_commit", "")
            ),
            "server_args": list(extra_argv),
            "declared_slots": slots,
            "declared_slot_tokens": slot_tokens,
            "live_slot_n_ctx": live_slot_ctx,
            "model_load_seconds": round(load_seconds, 1),
            "chat_template_sha256": chat_template_sha256,
            "media_marker": media_marker,
        },
        "media_stand_in": {
            "sample_id": ref.sample_id,
            "media_relpath": ref.media_relpath,
            "audio_seconds": ref.audio_seconds,
            "selection": "the roster's shortest utterance, deterministic",
        },
        "method": (
            "the wire messages are captured from the REAL LlamaServerTransport -- "
            "resolved through the same TRANSPORTS registry entry, from the same "
            "composed config, driven with a real core.policies.build_arm_payload "
            "payload, with only its HTTP sender replaced -- and then rendered through "
            "the pinned GGUF chat template by POST /apply-template. Nothing about the "
            "request shape is re-spelled here."
        ),
        "per_arm": per_arm,
        "proof": proof,
    }


def _render_main(args) -> int:
    baselines = tuple(args.baseline or RENDER_BASELINES)
    document = render(
        dataset=args.dataset,
        model=args.model,
        experiment=args.experiment,
        baselines=baselines,
        run_id=args.run_id,
        split_identity_hash=args.split_identity_hash,
        gate_baseline=args.gate_baseline,
    )
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "proof": document["proof"],
                "per_arm": {
                    name: {
                        "wire_message_roles": entry["wire_message_roles"],
                        "system_block_rendered": entry["system_block_rendered"],
                        "rendered_text_tokens": entry["rendered_text_tokens"],
                        "audio_placeholder_precedes_instruction": entry[
                            "audio_placeholder_precedes_instruction"
                        ],
                        "worst_required_tokens": entry["worst_required_tokens"],
                    }
                    for name, entry in document["per_arm"].items()
                },
                "contacts": document["contacts"],
                "output": str(args.output),
                "output_sha256": (
                    sha256_file(args.output)
                    if args.write
                    else hashlib.sha256(text.encode("utf-8")).hexdigest()
                ),
                "written": args.write,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if document["proof"]["all_assertions_hold"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="earnings22-esb-dev-utterances-6038")
    parser.add_argument("--model", default="q4km-e22-dev-esb-mmproj-gpu-04ccc72a-np8-c40960")
    parser.add_argument(
        "--baseline",
        action="append",
        default=None,
        help="repeatable; defaults to the two prompt A/B arms",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--render",
        action="store_true",
        help=(
            "prove the RENDERED chat template through /apply-template + /tokenize "
            "instead of the arithmetic fit; spawns the gated server, decodes nothing"
        ),
    )
    parser.add_argument("--experiment", default=RENDER_EXPERIMENT)
    parser.add_argument("--run-id", default=RENDER_RUN_ID)
    parser.add_argument("--split-identity-hash", default=RENDER_SPLIT_IDENTITY_HASH)
    parser.add_argument("--gate-baseline", default="e22-esb-dev-shape-c")
    args = parser.parse_args()
    if args.render:
        return _render_main(args)
    baselines = tuple(args.baseline or ("e22-esb-dev-prompt-a", "e22-esb-dev-prompt-b"))
    document = build(dataset=args.dataset, model=args.model, baselines=baselines)
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    fits = all(entry["fits"] for entry in document["per_arm"].values())
    print(
        json.dumps(
            {
                "fits": fits,
                "worst_case": document["worst_case"],
                "slot_tokens": document["geometry"]["slot_tokens"],
                "ratio_per_arm": {
                    name: entry["ratio"] for name, entry in document["per_arm"].items()
                },
                "sealed_geometry_would_fit": document[
                    "why_the_sealed_geometry_is_refused"
                ]["fits"],
                "output": str(args.output),
                "output_sha256": (
                    sha256_file(args.output)
                    if args.write
                    else hashlib.sha256(text.encode("utf-8")).hexdigest()
                ),
                "written": args.write,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if fits else 1


if __name__ == "__main__":
    raise SystemExit(main())
