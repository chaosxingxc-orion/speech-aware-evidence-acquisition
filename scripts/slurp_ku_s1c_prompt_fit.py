#!/usr/bin/env python3
"""Exact per-phase prompt fit for the SLURP consumption cell KU-S1c.

A thin SLURP entry point over the SAME measurement
``scripts/a2t_calibration_prompt_fit.py --phase-program`` performs: the
envelope bytes come from ``core.flight.runtime.render_phase_prompt_envelopes``
(the one authority ``FlightRuntime._verify_phase_prompt_fit`` re-renders with),
the receipt rows come from that script's own ``phase_cell_rows`` /
``phase_contact_allowance`` / ``measure_phase_envelopes``, and the output is
the same ``saea-phase-prompt-fit-v1`` document a fragment pins with
``prompt_fit_receipt`` + ``prompt_fit_receipt_sha256``. Nothing about the
measurement is re-implemented here.

Why a SLURP entry point exists at all -- two things the Audio2Tool entry point
cannot supply for this carrier, both of which would silently certify the wrong
prompt:

* **the adapter.** ``--phase-program`` resolves ``slot-slu`` to the stock
  ``rails.adapters.slurp.SlurpAdapter``, whose ``load_split`` wants one of
  ``data.slurp``'s four governed split names (not ``DEV-1000``) and whose
  ``instruction`` is the module-level ``_INSTRUCTION``, not the config-resolved
  closed-list instruction the flight sends. ``FlightRuntime._verify_phase_
  prompt_fit`` re-renders with the FLIGHT's adapter, so a receipt measured
  against the stock system message would never verify. This entry point uses
  the flight entry point's own roster-bound, label-free
  ``ClosedListSlurpAdapter``, imported from
  ``scripts/flights/run_slurp_closed_list_cell.py`` -- literally the same
  class object the flight constructs.
* **the speech tokens.** The SLURP promotion receipt records packet identity
  but not token counts, so the promoted packets themselves are opened and
  ``sum(chunk.n_tokens)`` is read (the KC-S1 prompt-fit script's own method).
  The Audio2Tool entry point's two sources (a promotion receipt carrying
  ``n_tokens``, or the window rule) do not exist for this carrier.

Zero generated tokens: only ``GET /props``, ``POST /apply-template`` and
``POST /tokenize`` are called, none of which decodes. The server is spawned
under a gate-checked ``contracts.ExecutionPlan`` bound to this script's own
exposure row and stopped with its own stop receipt. No gold, reference
transcript, annotation, score, test datum or future turn is opened.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/slurp_ku_s1c_prompt_fit.py <output.json>

Both the smoke cell and the flight cell are measured in ONE pass and land in
ONE receipt, because ``FlightRuntime._verify_phase_prompt_fit`` selects its
cell by the four FRAGMENT NAMES: the two differ in the experiment fragment,
so a receipt carrying only one of them would refuse the other's pre-flight.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]

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
    PHASE_PROMPT_FIT_SCHEMA,
    load_promotion_receipt,
    merge_server_args,
    packet_id_for_sample,
    phase_envelope_sha256,
    phase_program_system_text,
    render_phase_prompt_envelopes,
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
from speech_aware_evidence_acquisition.data.slurp import SLURP_LOCK_KEY  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp import (  # noqa: E402
    SlurpAdapter,
)
from speech_aware_evidence_acquisition.rails.controllers import (  # noqa: E402
    default_phase_program,
)
from speech_aware_evidence_acquisition.rails.phase_material import (  # noqa: E402
    load_phase_material_specs,
    render_static_instruction,
    sealed_states_from_manifest,
)

RUNTIME_ROOT = Path("/home/chao")
#: ``experiment:cell`` pairs measured in ONE pass, so ONE pinned receipt
#: verifies at BOTH pre-flights: the smoke's and the flight's.
#: ``FlightRuntime._verify_phase_prompt_fit`` selects its cell by the four
#: FRAGMENT NAMES, and the smoke and the flight differ in the experiment
#: fragment, so a receipt carrying only one of them would refuse the other.
DEFAULT_CELL_SPECS = (
    "slurp-consumption-ku-s1c-smoke-4-v1:ku-s1c-smoke",
    "slurp-consumption-ku-s1c-v1:ku-s1c-draft-revise",
)
DEFAULT_RUN_ID = "SAEA-SLURP-KU-S1C-PROMPT-FIT-V1"
DEFAULT_FLIGHT_RUN_ID = "SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1"
PLAN_CALLS = 4
PLAN_GPU_HOURS = 0.3
PLAN_AUDIO = 60
#: Every phase contact must clear its slot by at least this many tokens.
DEFAULT_SLOT_RESERVE_TOKENS = 1024


def _load_module(relpath: str, name: str):
    """Import a ``scripts/`` entry point by path.

    By path rather than by ``import scripts.<name>``: the shared venv already
    installs a top-level ``scripts`` package (verl), so the dotted import
    resolves to the wrong tree unless the repository root happens to be first
    on ``sys.path``.
    """

    path = REPO / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


#: The Audio2Tool entry point owns the measurement; this file owns only the
#: SLURP-specific plan. Importing the functions rather than copying them is
#: what keeps the two receipts the same document.
_A2T = _load_module("scripts/a2t_calibration_prompt_fit.py", "saea_a2t_prompt_fit")
_FLIGHT = _load_module(
    "scripts/flights/run_slurp_closed_list_cell.py", "saea_slurp_flight_cell"
)


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print("[%s] %s" % (stamp, message), flush=True)


def load_cell(experiment: str, cell_id: str) -> Mapping[str, object]:
    cells = _FLIGHT.load_cells(experiment)
    if cell_id not in cells:
        raise SystemExit("unknown cell %r; known: %s" % (cell_id, sorted(cells)))
    return cells[cell_id]


def parse_cell_specs(raw: str) -> list[tuple[str, str]]:
    """``"experiment:cell,experiment:cell"`` -> pairs, in order."""

    specs: list[tuple[str, str]] = []
    for part in str(raw).split(","):
        part = part.strip()
        if not part:
            continue
        if part.count(":") != 1:
            raise SystemExit("cell spec %r is not experiment:cell" % part)
        experiment, cell_id = part.split(":")
        specs.append((experiment.strip(), cell_id.strip()))
    if not specs:
        raise SystemExit("no cell specs given")
    return specs


def speech_tokens_by_sample(
    values: Mapping[str, object], sample_ids: Sequence[str]
) -> dict[str, int]:
    """Exact speech-feature tokens per roster row, read from the promoted
    packets themselves (``sum(chunk.n_tokens)``).

    The receipt is loaded first, so the feature root and the promoted set are
    the registered ones; the packets are then opened because the SLURP
    promotion receipt records identity but not token counts.
    """

    receipt = load_promotion_receipt(
        Path(str(values["speech_packet_promotion_receipt"]))
    )
    promoted = {str(entry["packet_id"]) for entry in receipt["packets"]}
    feature_root = Path(str(receipt["feature_root"]))
    tokens: dict[str, int] = {}
    for sample_id in sample_ids:
        packet_id = packet_id_for_sample(sample_id)
        if packet_id not in promoted:
            raise SystemExit("promotion receipt has no packet for %s" % sample_id)
        packet = load_speech_feature_packet(feature_root, packet_id)
        tokens[sample_id] = sum(chunk.n_tokens for chunk in packet.chunks)
    return tokens


def packet_bindings(
    values: Mapping[str, object], sample_ids: Sequence[str]
) -> dict[str, dict[str, str]]:
    """``{sample_id: {"packet_id", "sha256"}}`` -- exactly what
    ``FlightRuntime.speech_packet_bindings`` hands the transport, rebuilt from
    the same promotion receipt. A phase envelope carries this descriptor
    verbatim, so a wrong one is a wrong envelope hash."""

    receipt = load_promotion_receipt(
        Path(str(values["speech_packet_promotion_receipt"]))
    )
    registered = {
        str(entry["packet_id"]): str(entry["packet_sha256"])
        for entry in receipt["packets"]
    }
    bindings: dict[str, dict[str, str]] = {}
    missing: list[str] = []
    for sample_id in sample_ids:
        packet_id = packet_id_for_sample(sample_id)
        sha256 = registered.get(packet_id)
        if sha256 is None:
            missing.append(sample_id)
            continue
        bindings[sample_id] = {"packet_id": packet_id, "sha256": sha256}
    if missing:
        raise SystemExit(
            "%d roster sample(s) have no promoted packet, e.g. %s"
            % (len(missing), sorted(missing)[:5])
        )
    return bindings


def build_plan(
    cell: Mapping[str, object], lock, root: Path, *, experiment: str, dataset: str
) -> dict[str, object]:
    """The one SLURP-specific piece: the same ``phase_cell_plan`` shape the
    Audio2Tool entry point builds, but with the FLIGHT's adapter and the
    packet-derived speech tokens."""

    composed = compose(
        REPO,
        str(cell["model_fragment"]),
        dataset,
        str(cell["baseline_fragment"]),
        experiment,
    )
    values = composed.values
    policy = values.get("policy")
    if not isinstance(policy, str) or policy == "fixed" or not policy.startswith("phase-"):
        raise SystemExit(
            "cell %s declares policy %r, which is not a phase program"
            % (cell["cell_id"], policy)
        )
    program = default_phase_program(policy)
    specs = load_phase_material_specs(values, program)
    static_text = {
        phase: render_static_instruction(spec, REPO, lock, root)
        for phase, spec in specs.items()
    }

    instruction = resolve_active_task_instruction(values, REPO, lock, root)
    if instruction is None:
        raise SystemExit("baseline fragment declares no ACTIVE task instruction")
    _FLIGHT.assert_instruction_extends_sealed_m0(instruction, None)
    # The registered fragment's own population, exactly as the flight entry
    # point resolves it -- never a command line, so a smoke can never be
    # measured on four rows other than the ones its exposure row names.
    limit_sample_ids = _FLIGHT.population_ids(
        _FLIGHT.load_experiment(experiment), dataset
    )
    samples = _FLIGHT.roster_samples(values, root, limit_sample_ids=limit_sample_ids)
    if not samples:
        raise SystemExit("cell %s resolved zero samples" % cell["cell_id"])
    sample_ids = tuple(sample.sample_id for sample in samples)
    slots, slot_tokens = _FLIGHT.resolved_geometry(values)
    adapter = _FLIGHT.ClosedListSlurpAdapter(
        lock,
        root,
        repo_root=REPO,
        split_id=str(values["split_id"]),
        samples=samples,
        instruction_text=instruction,
        serving_slots=slots,
        serving_slot_tokens=slot_tokens,
    )
    ceiling = int(SlurpAdapter.SERVING_MAX_TOKENS)

    bindings = packet_bindings(values, sample_ids)
    sealed_states: dict[str, Mapping[str, object]] = {}
    for phase, spec in specs.items():
        if spec.predecessor_binding != "sealed-manifest":
            continue
        source = spec.predecessor_source
        sealed_states[phase] = sealed_states_from_manifest(
            root / str(source["manifest_relpath"]),
            expected_sha256=str(source["manifest_sha256"]),
            phase_name=phase,
            producer_policy_id=str(source["producer_policy_id"]),
            sample_ids=sample_ids,
        )

    prompt_order = str(values.get("prompt_order") or "speech-query-prefix-v2")
    by_phase: dict[str, dict[str, str]] = {phase: {} for phase in program.phase_names()}
    envelopes_by_sha: dict[str, list] = {}
    system_texts: set[str] = set()
    for sample in samples:
        system_text = phase_program_system_text(adapter, sample)
        system_texts.add(system_text)
        rendered = render_phase_prompt_envelopes(
            program_id=program.program_id,
            phase_names=program.phase_names(),
            specs=specs,
            static_text_by_phase=static_text,
            system_text=system_text,
            prompt_order=prompt_order,
            packet_descriptor=bindings[sample.sample_id],
            sample_id=sample.sample_id,
            sealed_states_by_phase=sealed_states,
            completion_token_ceiling=ceiling,
        )
        for phase, envelope in rendered.items():
            digest = phase_envelope_sha256(envelope)
            by_phase[phase][sample.sample_id] = digest
            envelopes_by_sha.setdefault(digest, list(envelope))
    if len(system_texts) != 1:
        raise SystemExit(
            "the roster renders %d distinct system messages; this cell's system "
            "message is sample-independent by construction" % len(system_texts)
        )

    return {
        "cell_id": str(cell["cell_id"]),
        "arm": str(values["arm"]),
        "policy": policy,
        "program_id": program.program_id,
        "model_fragment": str(cell["model_fragment"]),
        "dataset_fragment": dataset,
        "baseline_fragment": str(cell["baseline_fragment"]),
        "experiment_fragment": experiment,
        "config_hash": composed.config_hash,
        "carrier_lock_key": str(values["carrier_lock_key"]),
        "split_id": str(values["split_id"]),
        "prompt_order": prompt_order,
        "values": values,
        "specs": specs,
        "static_text": static_text,
        "system_text": next(iter(system_texts)),
        "samples": samples,
        "sample_ids": sample_ids,
        "tool_schema_fill": values.get("tool_schema_fill"),
        "tools": None,
        "slots": slots,
        "slot_tokens": slot_tokens,
        "completion_token_ceiling": ceiling,
        "phase_sha256_by_sample": by_phase,
        "envelopes_by_sha256": envelopes_by_sha,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cells", default=",".join(DEFAULT_CELL_SPECS))
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--flight-run-id", default=DEFAULT_FLIGHT_RUN_ID)
    parser.add_argument(
        "--slot-reserve-tokens", type=int, default=DEFAULT_SLOT_RESERVE_TOKENS
    )
    args = parser.parse_args(argv)

    lock = load_lock(umbrella_lock_path())
    root = data_root()

    plans = []
    for experiment, cell_id in parse_cell_specs(args.cells):
        cell = load_cell(experiment, cell_id)
        plans.append(
            build_plan(
                cell,
                lock,
                root,
                experiment=experiment,
                dataset=args.dataset or str(cell["dataset_fragment"]),
            )
        )
    # The LAST plan hosts the server and supplies the geometry: the flight cell
    # comes last in DEFAULT_CELL_SPECS, so the resident slot context is sized
    # for the roster that actually needs it.
    host = plans[-1]
    values = host["values"]
    dataset = str(host["dataset_fragment"])
    context_per_slot = int(host["slot_tokens"])
    for plan in plans:
        log(
            "%s (%s): %d samples, %d phases, config hash %s"
            % (
                plan["cell_id"],
                plan["experiment_fragment"],
                len(plan["sample_ids"]),
                len(plan["phase_sha256_by_sample"]),
                plan["config_hash"],
            )
        )
        if int(plan["slot_tokens"]) != context_per_slot:
            raise SystemExit(
                "cell %s declares slot_tokens %s but the resident server is sized "
                "for %d" % (plan["cell_id"], plan["slot_tokens"], context_per_slot)
            )
    for phase, static in sorted(host["static_text"].items()):
        log("  phase %-8s static instruction %d chars" % (phase, len(static)))
    log("  system message %d chars" % len(host["system_text"]))
    if len({plan["system_text"] for plan in plans}) != 1:
        raise SystemExit("the measured cells do not share one system message")

    allowance = _A2T.phase_contact_allowance(plans)
    distinct_total = int(allowance["distinct_envelopes"])
    log(
        "%d contact envelope(s), %d distinct"
        % (allowance["program_contacts"], distinct_total)
    )

    speech_by_cell = {
        plan["cell_id"]: speech_tokens_by_sample(plan["values"], plan["sample_ids"])
        for plan in plans
    }
    for cell_id, by_sample in speech_by_cell.items():
        log(
            "%s speech tokens from the promoted packets: min %d max %d"
            % (cell_id, min(by_sample.values()), max(by_sample.values()))
        )

    plan_record = ExecutionPlan(
        run_id=args.run_id,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=SLURP_LOCK_KEY,
        split_role="dev",
        split_identity_hash=str(values["split_identity_hash"]),
        planned_model_calls=PLAN_CALLS,
        planned_gpu_hours=PLAN_GPU_HOURS,
        planned_speech_audio_seconds=PLAN_AUDIO,
        protocol_hash=str(host["config_hash"]),
        attempt_id="attempt-%s-slurpkus1cpromptfit"
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
    lock_sha256 = gate.assert_model_touch_allowed(plan_record)
    log("frozen-core gate PASS (lock %s)" % lock_sha256[:12])

    runtime_receipt = load_runtime_receipt(REPO / "docs" / str(values["runtime_receipt"]))
    run_dir = root / "runs" / args.run_id / str(plan_record.attempt_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    extra_argv = merge_server_args(
        values["server_args"],
        slots=int(host["slots"]),
        context_tokens=int(host["slots"]) * context_per_slot,
    )
    port = int(str(values["base_url"]).rsplit(":", 1)[-1])
    log("spawning the packet server on %d: %s" % (port, " ".join(extra_argv)))
    started_at = time.time()
    session = start_session(
        runtime_root=RUNTIME_ROOT,
        data_root=root,
        runtime_receipt=runtime_receipt,
        host="127.0.0.1",
        port=port,
        session_id="%s-%s" % (args.run_id, plan_record.attempt_id),
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

    counts = {
        "GET /props": 0,
        "POST /apply-template": 0,
        "POST /tokenize": 0,
        "generations": 0,
    }
    stop_out = None
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
        if int(live_slot_ctx) < context_per_slot:
            raise SystemExit(
                "resident slot n_ctx %s is smaller than the declared %d; refusing to "
                "certify a fit the server cannot honour"
                % (live_slot_ctx, context_per_slot)
            )
        chat_template = props.get("chat_template")
        log("props OK: slot n_ctx=%s, media marker %r" % (live_slot_ctx, media_marker))
        measured = _A2T.measure_phase_envelopes(
            client,
            plans,
            media_marker=media_marker,
            counts=counts,
            args=SimpleNamespace(reference_media_marker=None),
        )
    finally:
        stop_out = stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
            receipt_path=run_dir / "session.stop-receipt.json",
            force_after_timeout=True,
        )
        log(
            "server stopped: %s forced=%s"
            % (stop_out.get("termination_signal"), stop_out.get("forced"))
        )

    if counts["POST /apply-template"] != distinct_total:
        raise SystemExit(
            "measured %d distinct envelope(s) with %d apply-template call(s); the two "
            "must agree" % (distinct_total, counts["POST /apply-template"])
        )
    if counts["generations"] != 0:
        raise SystemExit("a prompt-fit measurement must never generate a token")

    reserve = int(args.slot_reserve_tokens)
    cell_rows = [
        _A2T.phase_cell_rows(
            plan, measured, speech_by_cell[plan["cell_id"]], reserve=reserve
        )
        for plan in plans
    ]
    receipt = {
        "schema": PHASE_PROMPT_FIT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "attempt_id": plan_record.attempt_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "flight_run_id": args.flight_run_id,
        "experiment_fragments": [plan["experiment_fragment"] for plan in plans],
        "dataset_fragment": dataset,
        "split_identity_hash": str(values["split_identity_hash"]),
        "system_message": {
            "chars": len(host["system_text"]),
            "sha256": _A2T.sha256_text(host["system_text"]),
            "basis": (
                "the config-resolved closed-list instruction plus the adapter's task "
                "contract when absent (rails.runner._agent_messages' own rule, through "
                "core.flight.runtime.phase_program_system_text), asserted to be the "
                "sealed DEV-1000 M0 instruction plus a pure suffix and identical on "
                "every roster row"
            ),
        },
        "server": {
            "port": port,
            "extra_argv": extra_argv,
            "slot_tokens_declared": context_per_slot,
            "slot_tokens_live": int(live_slot_ctx),
            "role": str(runtime_receipt.get("role", "legacy")),
            "llama_cpp_build_commit": runtime_receipt["llama_cpp"]["build_commit"],
            "chat_template_sha256": (
                _A2T.sha256_text(chat_template)
                if isinstance(chat_template, str)
                else None
            ),
            "media_marker": media_marker,
            "load_seconds": round(load_seconds, 3),
            "stop_signal": stop_out.get("termination_signal") if stop_out else None,
            "stop_forced": bool(stop_out.get("forced")) if stop_out else None,
        },
        "contacts": counts,
        "contact_allowance": {
            **allowance,
            "apply_template_calls": counts["POST /apply-template"],
        },
        "speech_tokens": {
            plan["cell_id"]: {
                "source": (
                    "the promoted packets themselves, sum(chunk.n_tokens); the SLURP "
                    "promotion receipt records packet identity but not token counts"
                ),
                "promotion_receipt": str(
                    plan["values"]["speech_packet_promotion_receipt"]
                ),
                "promotion_receipt_sha256": str(
                    plan["values"]["speech_packet_promotion_receipt_sha256"]
                ),
                **_A2T.distribution(list(speech_by_cell[plan["cell_id"]].values())),
            }
            for plan in plans
        },
        "cells": cell_rows,
        "reserve_decision": {
            "rule": (
                "every phase contact of every cell must fit its slot with at least %d "
                "tokens of reserve" % reserve
            ),
            "slot_reserve_tokens": reserve,
            "cells": {
                row["cell_id"]: {
                    "worst_phase": row["worst_phase"],
                    "worst_required_window_tokens": row["worst_required_window_tokens"],
                    "worst_served_slot_margin_tokens": row[
                        "worst_served_slot_margin_tokens"
                    ],
                    "meets_reserve": row["meets_reserve"],
                }
                for row in cell_rows
            },
            "all_cells_meet_reserve": all(row["meets_reserve"] for row in cell_rows),
        },
        "append_sealed_state_note": (
            "phase 'revise' binds append-sealed-state: its predecessor is this run's "
            "own draft response, which does not exist before the flight, so "
            "render_phase_prompt_envelopes pads the instruction with "
            "completion_token_ceiling tokens' worth of ASCII. That pad is an exact "
            "UPPER BOUND on the predecessor -- the draft is capped at "
            "decoding_params.max_tokens -- so the measured revise envelope is never "
            "an under-count, and it is the same pad "
            "FlightRuntime._verify_phase_prompt_fit re-renders with."
        ),
        "boundary": (
            "zero generated tokens: only GET /props, POST /apply-template and POST "
            "/tokenize were called, none of which decodes. No gold, reference "
            "transcript, annotation, output, score, test datum or future turn was "
            "opened; the roster is built label-free from the frozen runtime view."
        ),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    log(
        "phase prompt-fit receipt written: %s (sha256 %s)"
        % (out_path, _A2T.sha256_file(out_path))
    )
    for row in cell_rows:
        for phase in row["phases"]:
            log(
                "%-20s %-8s text[min..median..p95..max]=%d..%g..%d..%d max_sample=%s "
                "required max=%d slot=%d margin=%d fits=%s"
                % (
                    row["cell_id"],
                    phase["phase"],
                    phase["text_prompt_tokens"]["min"],
                    phase["text_prompt_tokens"]["median"],
                    phase["text_prompt_tokens"]["p95"],
                    phase["text_prompt_tokens"]["max"],
                    phase["max_sample_id"],
                    phase["worst_required_window_tokens"],
                    row["slot_tokens"],
                    phase["worst_served_slot_margin_tokens"],
                    phase["every_request_fits"],
                )
            )
    ok = all(row["every_request_fits"] and row["meets_reserve"] for row in cell_rows)
    log(
        "RESERVE DECISION: reserve=%d all_cells_meet_reserve=%s"
        % (reserve, receipt["reserve_decision"]["all_cells_meet_reserve"])
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
