#!/usr/bin/env python3
"""EVO-S1 prompt fit: the worst admissible slot envelope, and the F3 token counter.

Preregistration section 13 item 6; exposure row ``SAEA-SLURP-EVO-S1-PROMPT-FIT-V1``.
Sibling of ``scripts/slurp_kc_s1_prompt_fit.py`` and measured the same way: ``GET
/props`` for the media marker, ``POST /apply-template`` for the exact wire messages,
``POST /tokenize`` around the single opaque marker. ZERO generated tokens; the server
is spawned under a gate-checked ``ExecutionPlan`` and stopped with its own receipt.

What differs from KC-S1's fit. KC-S1b's widest row was ``A_0``'s 26,720-character
full-schema fallback; EVO-S1 flies CANDIDATE schemas whose every per-intent block is
admissible up to ``+20 %`` of the incumbent's tokens, so the widest prompt a round-1
cell can send is that fallback with all sixty blocks at their own budget. This script
BUILDS that string -- pad word measured to cost one token, each block padded to its
budget -- and renders it through the production instruction path
(``rails.phase_material.build_material_for_phase``), so the envelope is a real
rendering rather than an arithmetic sum.

The speech term is bounded, not sampled: the fold packets do not exist yet (that is
``SAEA-SLURP-EVO-FOLD-PACKETS-V2``, which this fit precedes so a geometry surprise
costs no packet contacts). ``13 * ceil(seconds / 0.96)`` is checked fail-closed
against all 1,000 committed DEV-1000 packets before use and re-verified exactly
against the fold packets afterwards.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/slurp_evo_s1_prompt_fit.py <output.json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if Path(_pkg.__file__ or "") != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose, d1_media_supplement_relpath, d1_media_supplement_sha256, model_materialization_root)
from speech_aware_evidence_acquisition.core.driver.speech_native import (  # noqa: E402
    _LoopbackPromptAuditClient)
from speech_aware_evidence_acquisition.core.flight.runtime import (  # noqa: E402
    merge_server_args, packet_id_for_sample)
from speech_aware_evidence_acquisition.core.instructions import (  # noqa: E402
    resolve_active_task_instruction)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt, start_session, stop_session)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root, load_lock, umbrella_lock_path)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    SLURP_LOCK_KEY, load_slurp_intent_slot_schema, render_slurp_intent_slot_schema)
from speech_aware_evidence_acquisition.rails.adapters.slurp import (  # noqa: E402
    SlurpAdapter, SlurpSample)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact  # noqa: E402
from speech_aware_evidence_acquisition.rails.obs import AudioRef, default_obs_packet  # noqa: E402
from speech_aware_evidence_acquisition.rails.phase_material import (  # noqa: E402
    build_material_for_phase, load_phase_material_specs, render_phase_envelope,
    render_static_instruction, resolve_response_formats)
from speech_aware_evidence_acquisition.rails.proposer import (  # noqa: E402
    SERVING_TOKENIZER_ID, SLURP_RELATIVE_TOKEN_BUDGET, slurp_block_texts)

RUNTIME_ROOT = Path("/home/chao")
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64"
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"
BASELINE_FRAGMENT = "slurp-phase-slots-given-intent-schema-projected-v2-fold-a"
EXPERIMENT_FRAGMENT = "slurp-evo-s1-slot-schema-v1"
FOLDS = ("slurp-speech-native-evo-fold-a-1080", "slurp-speech-native-evo-fold-b-1080")
DEFAULT_RUN_ID = "SAEA-SLURP-EVO-S1-PROMPT-FIT-V1"
PLAN_CALLS, PLAN_GPU_HOURS, PLAN_AUDIO = 8, 0.4, 60
PAD_WORD, CHUNK_TOKENS, CHUNK_SECONDS, SERVER_CONTEXT = " item", 13, 0.96, 65536


def log(message: str) -> None:
    print("[%s] %s" % (datetime.now(timezone.utc).strftime("%H:%M:%SZ"), message), flush=True)


def speech_bound(seconds: float) -> int:
    """The encoder's own token function, bounded above; zero violations and a
    max shortfall of 0 over all 1,000 committed DEV-1000 packets."""

    return CHUNK_TOKENS * math.ceil(float(seconds) / CHUNK_SECONDS)


def fold_facts() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name in FOLDS:
        view = json.loads((REPO / "configs" / "dataset" / f"{name}.json").read_text(encoding="utf-8"))
        seconds = [float(item["audio_seconds"]) for item in view["items"]]
        out[name] = {"rows": len(seconds), "max_audio_seconds": max(seconds),
                     "total_audio_seconds": sum(seconds),
                     "max_speech_feature_tokens_bound": speech_bound(max(seconds))}
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--model-fragment", default=MODEL_FRAGMENT)
    args = parser.parse_args(argv)

    lock, root = load_lock(umbrella_lock_path()), data_root()
    composed = compose(REPO, args.model_fragment, DATASET_FRAGMENT, BASELINE_FRAGMENT, EXPERIMENT_FRAGMENT)
    values = composed.values
    adapter = SlurpAdapter(lock, root, repo_root=REPO)
    slots = int(values.get("serving_slots", adapter.SERVING_SLOTS))
    slot_tokens = int(values.get("serving_slot_tokens", adapter.SERVING_SLOT_TOKENS))
    max_tokens = int(values["decoding_params"]["max_tokens"])
    folds = fold_facts()
    speech = max(int(fact["max_speech_feature_tokens_bound"]) for fact in folds.values())
    log("geometry -np %d slot %d; speech bound %d tokens" % (slots, slot_tokens, speech))

    item = sorted(values["items"], key=lambda entry: str(entry["sample_id"]))[0]
    sample_id = str(item["sample_id"])
    if not sample_id.startswith("slurp:train:"):
        raise SystemExit("the fold runtime view must carry TRAIN rows only")
    sample = SlurpSample(
        sample_id=sample_id,
        audio_ref=AudioRef(path=str(item["media_relpath"]), sha256=str(item["audio_sha256"])).validate(),
        audio_seconds=float(item["audio_seconds"]), utterance_id=sample_id.split(":")[2],
        media_relpath=str(item["media_relpath"]), scenario="", action="", intent="", entities=())
    system_text = resolve_active_task_instruction(values, REPO, lock, root)
    if system_text is None:
        raise SystemExit("the fold incumbent fragment declares no ACTIVE task instruction")
    contract = adapter.build_task_contract(sample, default_obs_packet(sample))
    if contract not in system_text:
        system_text = f"{system_text}\n\nTask contract:\n{contract}"
    program = default_phase_program(str(values["policy"]))
    specs = load_phase_material_specs(values, program)
    (phase,) = program.phase_names()
    static_text = {name: render_static_instruction(spec, REPO, lock, root) for name, spec in specs.items()}
    formats = resolve_response_formats(specs, lock, root)
    schema = load_slurp_intent_slot_schema(lock, root)
    blocks, full_text = slurp_block_texts(schema), render_slurp_intent_slot_schema(schema)

    plan = ExecutionPlan(
        run_id=args.run_id, execution_profile="bounded-discovery-probe",
        carrier_lock_key=SLURP_LOCK_KEY, split_role="discovery",
        split_identity_hash=str(values["split_identity_hash"]),
        planned_model_calls=PLAN_CALLS, planned_gpu_hours=PLAN_GPU_HOURS,
        planned_speech_audio_seconds=PLAN_AUDIO, protocol_hash=composed.config_hash,
        attempt_id="attempt-%s-evos1promptfit" % datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    ).validate()
    model_root = model_materialization_root(values)
    gate = FrozenCoreGate.for_study_repo(
        REPO, root, RUNTIME_ROOT, runtime_receipt_relpath=str(values["runtime_receipt"]),
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=(Path(model_root) if model_root else None),
        d1_media_supplement_relpath=d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values))
    log("frozen-core gate PASS (lock %s)" % gate.assert_model_touch_allowed(plan)[:12])

    runtime_receipt = load_runtime_receipt(REPO / "docs" / str(values["runtime_receipt"]))
    run_dir = root / "runs" / args.run_id / str(plan.attempt_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    port = int(str(values["base_url"]).rsplit(":", 1)[-1])
    started = time.time()
    session = start_session(
        runtime_root=RUNTIME_ROOT, data_root=root, runtime_receipt=runtime_receipt,
        host="127.0.0.1", port=port, session_id="%s-%s" % (args.run_id, plan.attempt_id),
        extra_argv=merge_server_args(values["server_args"], slots=slots, context_tokens=slots * slot_tokens),
        extra_env=dict(values.get("server_env", {})),
        receipt_path=run_dir / "session.receipt.json",
        server_log_path=run_dir / "session.server.log",
        role=str(runtime_receipt.get("role", "legacy")),
        model_root=(Path(model_root) if model_root else None), ready_timeout_seconds=1800.0)
    load_seconds = time.time() - started
    log("server up in %.1fs: pid=%s port=%s" % (load_seconds, session.pid, session.port))

    counts = {"GET /props": 0, "POST /apply-template": 0, "POST /tokenize": 0, "generations": 0}
    envelopes: dict[str, object] = {}
    try:
        client = _LoopbackPromptAuditClient(host="127.0.0.1", port=port, timeout_seconds=180.0)

        def tokens_of(text: str) -> int:
            counts["POST /tokenize"] += 1
            reply = client.request_json(
                "POST", "/tokenize", {"content": text, "add_special": False, "parse_special": True})
            if not isinstance(reply.get("tokens"), list):
                raise SystemExit("tokenize returned no token list")
            return len(reply["tokens"])

        props = client.request_json("GET", "/props", None)
        counts["GET /props"] += 1
        marker, live_ctx = props.get("media_marker"), (props.get("default_generation_settings") or {}).get("n_ctx")
        if not isinstance(marker, str) or not marker:
            raise SystemExit("resident props lack a media marker")
        if int(live_ctx) < slot_tokens:
            raise SystemExit("resident slot n_ctx %s is under the declared %d" % (live_ctx, slot_tokens))
        template_sha256 = hashlib.sha256(str(props.get("chat_template")).encode("utf-8")).hexdigest()

        if tokens_of(PAD_WORD) != 1:
            raise SystemExit("the pad word does not cost exactly one token on this tokenizer")
        padded, per_intent = full_text, []
        for intent in sorted(blocks):
            block = blocks[intent]
            incumbent = tokens_of(block)
            budget = int(incumbent * (1.0 + SLURP_RELATIVE_TOKEN_BUDGET))
            if padded.count(block) != 1:
                raise SystemExit("block for %s does not occur exactly once in the schema" % intent)
            padded = padded.replace(block, block + PAD_WORD * (budget - incumbent), 1)
            per_intent.append({"intent": intent, "incumbent_tokens": incumbent,
                               "budget_tokens": budget, "characters": len(block)})
        state_content = " ".join(["response"] * max_tokens)
        pad_tokens = tokens_of(state_content)
        if pad_tokens < max_tokens:
            raise SystemExit("the predecessor pad is narrower than the completion ceiling")
        state = AgentStateArtifact(
            state_id="prompt-fit-pad", state_kind=f"phase:{phase}", content=state_content,
            source_query_state_sha256="0" * 64, source_response_sha256="0" * 64,
            producer_policy_id=str(specs[phase].predecessor_source["producer_policy_id"]),
            cited_value_ids=()).validate()

        class _Ctx:
            sample_id = sample.sample_id

        packet = {"packet_id": packet_id_for_sample(sample.sample_id), "sha256": "0" * 64}
        for label, rendered in (("worst_admissible_candidate", padded), ("incumbent_a0", full_text)):
            material = build_material_for_phase(
                specs, program_id=program.program_id, static_text_by_phase=static_text,
                response_format_by_phase=formats,
                per_sample_states={phase: {sample.sample_id: state}},
                state_fill_by_phase={phase: (lambda text: lambda _content: text)(rendered)})
            instruction = material(phase, _Ctx(), {}).instruction
            messages = render_phase_envelope(
                system_text, instruction, prompt_order=str(values["prompt_order"]),
                packet_descriptor=packet,
                contact_id="%s:%s:%s" % (values["policy"], phase, sample.sample_id))
            counts["POST /apply-template"] += 1
            wire = client.request_json("POST", "/apply-template", {"messages": list(messages)})
            prompt = wire.get("prompt")
            if not isinstance(prompt, str) or prompt.count(marker) != 1:
                raise SystemExit("apply-template did not return a prompt with one media marker")
            text_tokens = sum(tokens_of(part) for part in prompt.split(marker) if part)
            upper = text_tokens + speech + 2
            envelopes[label] = {
                "schema_characters": len(rendered), "schema_tokens": tokens_of(rendered),
                "instruction_characters": len(instruction), "text_prompt_tokens": text_tokens,
                "speech_feature_tokens_bound": speech, "prompt_tokens_upper_bound": upper,
                "context_margin_tokens": slot_tokens - upper - max_tokens}
            log("%s: %d text tokens, margin %d"
                % (label, text_tokens, envelopes[label]["context_margin_tokens"]))
    finally:
        stop = stop_session(session, runtime_receipt=runtime_receipt, runtime_root=RUNTIME_ROOT,
                            receipt_path=run_dir / "session.stop-receipt.json", force_after_timeout=True)
        log("server stopped")

    worst = envelopes["worst_admissible_candidate"]
    upper = int(worst["prompt_tokens_upper_bound"])
    admissible = [n for n in (16, 8, 4, 2, 1) if SERVER_CONTEXT // n - upper - max_tokens >= 0]
    report = {
        "schema": "saea-slurp-evo-s1-prompt-fit-v1", "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "scope": "worst admissible slot envelope and the F3 token-counter binding; zero generated tokens",
        "exposure_run_id": args.run_id, "attempt_id": plan.attempt_id,
        "model_contacts": 0, "generated_tokens": 0,
        "config_fragments": {"model": args.model_fragment, "dataset": DATASET_FRAGMENT,
                             "baseline": BASELINE_FRAGMENT, "experiment": EXPERIMENT_FRAGMENT},
        "config_hash": composed.config_hash, "prompt_order": str(values["prompt_order"]),
        "serving_geometry": {"slots": slots, "slot_tokens": slot_tokens, "max_tokens": max_tokens},
        "server_context_tokens": SERVER_CONTEXT, "relative_token_budget": SLURP_RELATIVE_TOKEN_BUDGET,
        "system_text_sha256": hashlib.sha256(system_text.encode("utf-8")).hexdigest(),
        "system_text_characters": len(system_text), "schema_content_hash": schema.content_hash(),
        "intents": len(blocks), "per_intent": per_intent, "predecessor_pad_tokens": pad_tokens,
        "folds": folds,
        "speech_token_bound": {"formula": "13 * ceil(audio_seconds / 0.96)", "value_used": speech,
                               "authority": "fail-closed against all 1,000 committed DEV-1000 packets"},
        "envelopes": envelopes, "np_admissible": admissible,
        "np_recommended": max(admissible) if admissible else None,
        "np_unchanged": bool(admissible) and max(admissible) >= slots,
        "verdict": "ALLOW" if int(worst["context_margin_tokens"]) >= 0 else "REFUSE",
        "token_counter": {
            "token_counter_id": SERVING_TOKENIZER_ID, "endpoint": "POST /tokenize",
            "geometry": {"slots": slots, "context_tokens": slots * slot_tokens},
            "host": "127.0.0.1", "port": port,
            "handed_to": "rails.evolution.run_candidates_step(..., token_counter=...) for round 1's F3",
            "estimator_refused_by": "rails.proposer.validate_slurp_candidate_artifact (allow_estimator=False)",
            "request_counts": counts, "decoder_evaluations": 0,
            "chat_template_sha256": template_sha256},
        "session": {"session_id": session.session_id, "pid": session.pid,
                    "load_seconds": round(load_seconds, 2), "stop": stop},
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    log("wrote %s verdict=%s np=%s margin=%s"
        % (output, report["verdict"], report["np_recommended"], worst["context_margin_tokens"]))
    return 0 if report["verdict"] == "ALLOW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
