#!/usr/bin/env python3
"""Exact prompt fit and per-sample material audit for cells KC-S1a / KC-S1b.

The KC-S1 preregistration's takeoff prerequisite: "the per-sample slot block
varies, so measure the longest rendered envelope and record the
distribution". ``core.flight.FlightRuntime``'s own pre-flight estimator
cannot do it -- ``_phase_prompt_payloads`` renders ONE representative
request per phase with a fixed-length pad in place of the predecessor state
and does not apply a ``state_fill`` at all, so for KC-S1b it counts a
prompt that is roughly 7,500 tokens shorter than the widest real one.

Method, and why it is exact rather than a bound:

* TEXT is measured through the resident server's own routes -- ``POST
  /apply-template`` renders the exact wire messages and ``POST /tokenize``
  counts the rendered prompt around the single opaque media marker ``GET
  /props`` reports. Same technique as ``scripts/a2t_calibration_prompt_fit.
  py`` and ``scripts/dev500_confirmatory_prompt_fit.py``.
* Every one of the 1,000 rows is measured for BOTH cells, because the
  per-sample material differs per row: KC-S1a appends that row's sealed
  closed-list response, and KC-S1b appends that response's per-intent TRAIN
  slot schema block on top (or, for a row whose sealed response does not
  parse or names a pair TRAIN never carries, the full 60-intent schema).
* SPEECH is the promotion receipt's own per-packet ``n_tokens`` -- the
  mmproj encoder's real output for these exact audio bytes -- maximised
  over the roster.

Zero generated tokens: only ``/props``, ``/apply-template`` and
``/tokenize`` are called, none of which decodes. The server is spawned under
a gate-checked ``contracts.ExecutionPlan`` bound to this script's own
exposure row and stopped with its own stop receipt.

The receipt doubles as the cells' MATERIAL AUDIT, because the same rendering
pass produces it for free:

* that KC-S1b's contact instruction is KC-S1a's contact instruction plus a
  pure per-sample suffix, asserted on every row (the cells' single-factor
  claim, as bytes);
* which intent block each row got, how many rows fell back to the full
  schema and which ones;
* the character and token distribution of both cells' envelopes.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/slurp_kc_s1_prompt_fit.py <output.json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if (
    Path(_pkg.__file__ or "")
    != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"
):
    raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    model_materialization_root,
)
from speech_aware_evidence_acquisition.core.driver.speech_native import (  # noqa: E402
    _LoopbackPromptAuditClient,
)
from speech_aware_evidence_acquisition.core.flight.runtime import (  # noqa: E402
    load_promotion_receipt,
    merge_server_args,
    packet_id_for_sample,
)
from speech_aware_evidence_acquisition.core.instructions import (  # noqa: E402
    resolve_active_task_instruction,
)
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    load_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    SLURP_LOCK_KEY,
    load_slurp_intent_slot_schema,
    render_slurp_slot_schema_for_state_detail,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import (  # noqa: E402
    SlurpAdapter,
    SlurpSample,
)
from speech_aware_evidence_acquisition.rails.controllers import (  # noqa: E402
    default_phase_program,
)
from speech_aware_evidence_acquisition.rails.obs import (  # noqa: E402
    AudioRef,
    default_obs_packet,
)
from speech_aware_evidence_acquisition.rails.phase_material import (  # noqa: E402
    build_material_for_phase,
    load_phase_material_specs,
    render_phase_envelope,
    render_static_instruction,
    resolve_response_formats,
    sealed_states_from_manifest,
)

RUNTIME_ROOT = Path("/home/chao")
DATASET_FRAGMENT = "slurp-speech-native-dev1000"
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64"
CELLS = (
    ("kc-s1a", "slurp-phase-slots-given-intent-v1", "slurp-slot-stage-kc-s1a-v1"),
    (
        "kc-s1b",
        "slurp-phase-slots-given-intent-schema-v1",
        "slurp-slot-stage-kc-s1b-v1",
    ),
)
DEFAULT_RUN_ID = "SAEA-SLURP-KC-S1-PROMPT-FIT-V1"
PLAN_CALLS = 4
PLAN_GPU_HOURS = 0.3
PLAN_AUDIO = 60


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print("[%s] %s" % (stamp, message), flush=True)


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def roster(values: Mapping[str, object]) -> tuple[SlurpSample, ...]:
    """LABEL-FREE samples straight from the frozen runtime view, which
    carries media identity only. The gold SLU fields are left empty exactly
    as the flight entry point leaves them; nothing here opens audio bytes
    (this pass renders text and asks the tokenizer to count it)."""

    items = values.get("items")
    if values.get("schema") != "saea-speech-native-runtime-view-v1" or not isinstance(
        items, list
    ):
        raise SystemExit("dataset fragment is not a speech-native runtime view")
    samples = []
    for item in items:
        sample_id = str(item["sample_id"])
        if sample_id.startswith("slurp:test:"):
            raise SystemExit("runtime view names a held-out test sample; refusing")
        samples.append(
            SlurpSample(
                sample_id=sample_id,
                audio_ref=AudioRef(
                    path=str(item["media_relpath"]), sha256=str(item["audio_sha256"])
                ).validate(),
                audio_seconds=float(item["audio_seconds"]),
                utterance_id=sample_id.split(":")[2],
                media_relpath=str(item["media_relpath"]),
                scenario="",
                action="",
                intent="",
                entities=(),
            )
        )
    return tuple(sorted(samples, key=lambda sample: sample.sample_id))


def speech_tokens_by_sample(
    values: Mapping[str, object], samples: Sequence[SlurpSample]
) -> dict[str, int]:
    """Exact speech-feature tokens per roster row, read from the promoted
    packets themselves (``sum(chunk.n_tokens)``) rather than from the
    14.4 tokens/second approximation the registered geometry was sized with.

    The SLURP promotion receipt records packet identity but not token
    counts, so the packets are opened; the receipt is still loaded first so
    the feature root and the promoted set are the registered ones.
    """

    receipt = load_promotion_receipt(Path(str(values["speech_packet_promotion_receipt"])))
    promoted = {str(entry["packet_id"]) for entry in receipt["packets"]}
    feature_root = Path(str(receipt["feature_root"]))
    tokens: dict[str, int] = {}
    for sample in samples:
        packet_id = packet_id_for_sample(sample.sample_id)
        if packet_id not in promoted:
            raise SystemExit("promotion receipt has no packet for %s" % sample.sample_id)
        packet = load_speech_feature_packet(feature_root, packet_id)
        tokens[sample.sample_id] = sum(chunk.n_tokens for chunk in packet.chunks)
    return tokens


def system_text_for(values: Mapping[str, object], lock, root, adapter, sample) -> str:
    """The system message ``rails.runner._agent_messages`` assembles: the
    config-resolved instruction, plus the adapter's task contract when the
    instruction does not already carry it (the closed-list fill does)."""

    instruction = resolve_active_task_instruction(values, REPO, lock, root)
    if instruction is None:
        raise SystemExit("baseline fragment declares no ACTIVE task instruction")
    contract = adapter.build_task_contract(sample, default_obs_packet(sample))
    if contract not in instruction:
        instruction = f"{instruction}\n\nTask contract:\n{contract}"
    return instruction


def phase_instructions(
    values: Mapping[str, object],
    lock,
    root: Path,
    sample_ids: Sequence[str],
) -> tuple[str, dict[str, str], Mapping[str, object]]:
    """``(phase_name, {sample_id: contact instruction}, specs)`` for one cell,
    built exactly the way ``FlightRuntime._default_phase_program_binding``
    builds it -- same module, same functions, same config keys."""

    program = default_phase_program(str(values["policy"]))
    specs = load_phase_material_specs(values, program)
    static_text = {
        phase: render_static_instruction(spec, REPO, lock, root)
        for phase, spec in specs.items()
    }
    formats = resolve_response_formats(specs, lock, root)
    per_sample_states: dict[str, Mapping[str, object]] = {}
    for phase, spec in specs.items():
        if spec.predecessor_binding != "sealed-manifest":
            continue
        source = spec.predecessor_source
        per_sample_states[phase] = sealed_states_from_manifest(
            root / str(source["manifest_relpath"]),
            expected_sha256=str(source["manifest_sha256"]),
            phase_name=phase,
            producer_policy_id=str(source["producer_policy_id"]),
            sample_ids=tuple(sample_ids),
        )
    material = build_material_for_phase(
        specs,
        program_id=program.program_id,
        static_text_by_phase=static_text,
        response_format_by_phase=formats,
        per_sample_states=per_sample_states,
    )
    (phase_name,) = program.phase_names()

    class _Ctx:
        __slots__ = ("sample_id",)

        def __init__(self, sample_id: str) -> None:
            self.sample_id = sample_id

    instructions = {
        sample_id: material(phase_name, _Ctx(sample_id), {}).instruction
        for sample_id in sample_ids
    }
    return phase_name, instructions, specs


def text_token_count(client, messages, media_marker, counts) -> int:
    rendered = client.request_json(
        "POST", "/apply-template", {"messages": list(messages)}
    )
    counts["POST /apply-template"] += 1
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
    return total


def distribution(values: Sequence[int]) -> dict[str, object]:
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "min": ordered[0],
        "p50": ordered[len(ordered) // 2],
        "p95": ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))],
        "max": ordered[-1],
        "mean": round(statistics.fmean(ordered), 2),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--model-fragment", default=MODEL_FRAGMENT)
    args = parser.parse_args(argv)

    lock = load_lock(umbrella_lock_path())
    root = data_root()

    composed_by_cell = {}
    for cell_id, baseline, experiment in CELLS:
        composed_by_cell[cell_id] = compose(
            REPO, args.model_fragment, DATASET_FRAGMENT, baseline, experiment
        )
    reference = composed_by_cell["kc-s1b"]
    values = reference.values
    samples = roster(values)
    sample_ids = tuple(sample.sample_id for sample in samples)
    log("roster: %d samples" % len(samples))

    adapter = SlurpAdapter(lock, root, repo_root=REPO)
    geometry = {
        "slots": int(values.get("serving_slots", adapter.SERVING_SLOTS)),
        "slot_tokens": int(values.get("serving_slot_tokens", adapter.SERVING_SLOT_TOKENS)),
        "max_tokens": int(adapter.SERVING_MAX_TOKENS),
    }
    context_per_slot = geometry["slot_tokens"]
    maximum_completion_tokens = int(values["decoding_params"]["max_tokens"])

    speech_by_sample = speech_tokens_by_sample(values, samples)
    maximum_speech_feature_tokens = max(speech_by_sample.values())
    log(
        "speech tokens from the promotion receipt: min %d max %d"
        % (min(speech_by_sample.values()), maximum_speech_feature_tokens)
    )

    # ---- material, model-free --------------------------------------------
    schema = load_slurp_intent_slot_schema(lock, root)
    per_cell: dict[str, dict] = {}
    for cell_id, _baseline, _experiment in CELLS:
        cell_values = composed_by_cell[cell_id].values
        phase_name, instructions, specs = phase_instructions(
            cell_values, lock, root, sample_ids
        )
        per_cell[cell_id] = {
            "phase": phase_name,
            "instructions": instructions,
            "specs": {name: spec.as_json() for name, spec in specs.items()},
            "config_hash": composed_by_cell[cell_id].config_hash,
            "system_text": system_text_for(
                cell_values, lock, root, adapter, samples[0]
            ),
        }
        log(
            "%s: %d instructions rendered, chars %s"
            % (
                cell_id,
                len(instructions),
                distribution([len(text) for text in instructions.values()]),
            )
        )

    if per_cell["kc-s1a"]["system_text"] != per_cell["kc-s1b"]["system_text"]:
        raise SystemExit("the two cells' system messages differ; they must be identical")

    # The single-factor claim, as bytes.
    suffix_chars: list[int] = []
    for sample_id in sample_ids:
        a = per_cell["kc-s1a"]["instructions"][sample_id]
        b = per_cell["kc-s1b"]["instructions"][sample_id]
        if not b.startswith(a):
            raise SystemExit(
                "KC-S1b instruction for %s is not KC-S1a's plus a suffix" % sample_id
            )
        suffix_chars.append(len(b) - len(a))

    # Which schema block each row got, and which rows fell back.
    used_intent: dict[str, str | None] = {}
    fallback_ids: list[str] = []
    states = sealed_states_from_manifest(
        root
        / str(
            per_cell["kc-s1b"]["specs"]["slots"]["predecessor_source"]["manifest_relpath"]
        ),
        expected_sha256=str(
            per_cell["kc-s1b"]["specs"]["slots"]["predecessor_source"]["manifest_sha256"]
        ),
        phase_name="slots",
        producer_policy_id=str(
            per_cell["kc-s1b"]["specs"]["slots"]["predecessor_source"][
                "producer_policy_id"
            ]
        ),
        sample_ids=sample_ids,
    )
    for sample_id in sample_ids:
        _text, intent, fallback = render_slurp_slot_schema_for_state_detail(
            lock, root, states[sample_id].content, schema=schema
        )
        used_intent[sample_id] = intent
        if fallback:
            fallback_ids.append(sample_id)
    log(
        "schema blocks: %d rows on a per-intent block, %d rows on the full-schema fallback"
        % (len(sample_ids) - len(fallback_ids), len(fallback_ids))
    )

    # ---- gate, then spawn the server -------------------------------------
    plan = ExecutionPlan(
        run_id=args.run_id,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=SLURP_LOCK_KEY,
        split_role="dev",
        split_identity_hash=str(values["split_identity_hash"]),
        planned_model_calls=PLAN_CALLS,
        planned_gpu_hours=PLAN_GPU_HOURS,
        planned_speech_audio_seconds=PLAN_AUDIO,
        protocol_hash=reference.config_hash,
        attempt_id="attempt-%s-slurpkcs1promptfit"
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
    log("frozen-core gate PASS (lock %s)" % lock_sha256[:12])

    runtime_receipt = load_runtime_receipt(REPO / "docs" / str(values["runtime_receipt"]))
    run_dir = root / "runs" / args.run_id / str(plan.attempt_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    extra_argv = merge_server_args(
        values["server_args"],
        slots=geometry["slots"],
        context_tokens=geometry["slots"] * context_per_slot,
    )
    port = int(str(values["base_url"]).rsplit(":", 1)[-1])
    log("spawning the packet server on %d" % port)
    started_at = time.time()
    session = start_session(
        runtime_root=RUNTIME_ROOT,
        data_root=root,
        runtime_receipt=runtime_receipt,
        host="127.0.0.1",
        port=port,
        session_id="%s-%s" % (args.run_id, plan.attempt_id),
        extra_argv=extra_argv,
        extra_env=dict(values.get("server_env", {})),
        receipt_path=run_dir / "session.receipt.json",
        server_log_path=run_dir / "session.server.log",
        role=str(runtime_receipt.get("role", "legacy")),
        model_root=(Path(configured_model_root) if configured_model_root else None),
        ready_timeout_seconds=1800.0,
    )
    load_seconds = time.time() - started_at
    log("server up in %.1fs: pid=%s port=%s" % (load_seconds, session.pid, session.port))

    counts = {"GET /props": 0, "POST /apply-template": 0, "POST /tokenize": 0, "generations": 0}
    rows: list[dict[str, object]] = []
    stop_out = None
    try:
        client = _LoopbackPromptAuditClient(host="127.0.0.1", port=port, timeout_seconds=180.0)
        props = client.request_json("GET", "/props", None)
        counts["GET /props"] += 1
        media_marker = props.get("media_marker")
        if not isinstance(media_marker, str) or not media_marker:
            raise SystemExit("resident props lack a media marker")
        live_slot_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
        if int(live_slot_ctx) < context_per_slot:
            raise SystemExit(
                "resident slot n_ctx %s is smaller than the declared %d; refusing to "
                "certify a fit the server cannot honour" % (live_slot_ctx, context_per_slot)
            )
        chat_template = props.get("chat_template")
        log("props OK: slot n_ctx=%s" % live_slot_ctx)

        packet_descriptor = {
            "packet_id": packet_id_for_sample(sample_ids[0]),
            "sha256": "0" * 64,
        }
        for cell_id, _baseline, _experiment in CELLS:
            cell = per_cell[cell_id]
            measured = 0
            for sample in samples:
                instruction = cell["instructions"][sample.sample_id]
                envelope = render_phase_envelope(
                    cell["system_text"],
                    instruction,
                    prompt_order=str(values["prompt_order"]),
                    packet_descriptor=packet_descriptor,
                    contact_id="%s:%s:%s"
                    % (values["policy"], cell["phase"], sample.sample_id),
                )
                tokens = text_token_count(client, envelope, media_marker, counts)
                speech = speech_by_sample[sample.sample_id]
                upper = tokens + speech + 2
                rows.append(
                    {
                        "cell_id": cell_id,
                        "sample_id": sample.sample_id,
                        "instruction_characters": len(instruction),
                        "text_prompt_tokens": tokens,
                        "speech_feature_tokens": speech,
                        "prompt_tokens_upper_bound": upper,
                        "context_margin_tokens": (
                            context_per_slot - upper - maximum_completion_tokens
                        ),
                        "schema_block_intent": used_intent[sample.sample_id],
                        "schema_full_fallback": sample.sample_id in set(fallback_ids),
                    }
                )
                measured += 1
                if measured % 200 == 0:
                    log("  %s: %d/%d measured" % (cell_id, measured, len(samples)))
            log("%s: %d envelopes measured" % (cell_id, measured))
    finally:
        stop_out = stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
            receipt_path=run_dir / "session.stop-receipt.json",
            force_after_timeout=True,
        )
        log("server stopped")

    by_cell: dict[str, object] = {}
    worst_margin = None
    for cell_id, _baseline, _experiment in CELLS:
        cell_rows = [row for row in rows if row["cell_id"] == cell_id]
        worst = max(
            cell_rows,
            key=lambda row: (row["prompt_tokens_upper_bound"], row["sample_id"]),
        )
        margin = int(worst["context_margin_tokens"])
        worst_margin = margin if worst_margin is None else min(worst_margin, margin)
        by_cell[cell_id] = {
            "config_hash": per_cell[cell_id]["config_hash"],
            "phase_material_spec": per_cell[cell_id]["specs"],
            "system_text_sha256": hashlib.sha256(
                per_cell[cell_id]["system_text"].encode("utf-8")
            ).hexdigest(),
            "system_text_characters": len(per_cell[cell_id]["system_text"]),
            "instruction_characters": distribution(
                [int(row["instruction_characters"]) for row in cell_rows]
            ),
            "text_prompt_tokens": distribution(
                [int(row["text_prompt_tokens"]) for row in cell_rows]
            ),
            "prompt_tokens_upper_bound": distribution(
                [int(row["prompt_tokens_upper_bound"]) for row in cell_rows]
            ),
            "worst_sample_id": worst["sample_id"],
            "worst_prompt_tokens_upper_bound": int(worst["prompt_tokens_upper_bound"]),
            "worst_context_margin_tokens": margin,
            "maximum_prompt_fits_one_slot": margin >= 0,
        }

    report = {
        "schema": "saea-slurp-kc-s1-prompt-fit-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "scope": "prompt fit and per-sample material audit, zero generated tokens",
        "exposure_run_id": args.run_id,
        "attempt_id": plan.attempt_id,
        "model_contacts": 0,
        "generated_tokens": 0,
        "config_fragments": {
            "model": args.model_fragment,
            "dataset": DATASET_FRAGMENT,
            "cells": {cell_id: baseline for cell_id, baseline, _ in CELLS},
        },
        "prompt_order": str(values["prompt_order"]),
        "serving_geometry": geometry,
        "context_tokens_per_slot": context_per_slot,
        "maximum_completion_tokens": maximum_completion_tokens,
        "maximum_speech_feature_tokens": maximum_speech_feature_tokens,
        "special_token_reserve": 2,
        "sample_count": len(samples),
        "split_identity_hash": str(values["split_identity_hash"]),
        "single_factor_check": {
            "every_kc_s1b_instruction_is_kc_s1a_plus_a_suffix": True,
            "system_messages_identical": True,
            "suffix_characters": distribution(suffix_chars),
        },
        "schema_blocks": {
            "per_intent_rows": len(sample_ids) - len(fallback_ids),
            "full_schema_fallback_rows": len(fallback_ids),
            "full_schema_fallback_sample_ids": sorted(fallback_ids),
            "distinct_intents_used": len(
                {intent for intent in used_intent.values() if intent is not None}
            ),
            "schema_content_hash": schema.content_hash(),
            "schema_source_split": schema.source_split,
        },
        "cells": by_cell,
        "worst_context_margin_tokens_over_both_cells": worst_margin,
        "verdict": "ALLOW" if (worst_margin or 0) >= 0 else "REFUSE",
        "rows": rows,
        "rows_sha256": canonical_sha256(rows),
        "tokenizer": {
            "request_counts": counts,
            "decoder_evaluations": 0,
            "generated_tokens": 0,
            "media_marker": media_marker,
            "chat_template_sha256": hashlib.sha256(
                str(chat_template).encode("utf-8")
            ).hexdigest(),
            "host": "127.0.0.1",
            "port": port,
        },
        "session": {
            "session_id": session.session_id,
            "pid": session.pid,
            "load_seconds": round(load_seconds, 2),
            "stop": stop_out,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    log(
        "wrote %s  verdict=%s worst margin=%s"
        % (output, report["verdict"], worst_margin)
    )
    return 0 if report["verdict"] == "ALLOW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
