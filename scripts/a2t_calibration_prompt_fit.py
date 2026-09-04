#!/usr/bin/env python3
"""Exact prompt fit for the four Audio2Tool direct-baseline calibration cells.

Preregistration prerequisite 3 (``docs/readiness/
2026-09-03-a2t-direct-baseline-calibration-v1-preregistration.md`` section 4):
"the exact request is rendered through the pinned template and measured
before any contact; every one of the 400 requests must fit its slot".

Phase-1 flagged why this is load-bearing for the NATIVE cells specifically:
their tool registry does not travel in the system message at all, it travels
in the request's ``tools`` field and the pinned GGUF chat template renders it
itself, so ``FlightRuntime``'s own pre-flight estimator counts 119 text
tokens for a request whose real envelope is ~12k. Only the live template can
say what that envelope actually is.

Method, and why it is exact rather than a bound:

* TEXT is measured through the resident server's own routes -- ``POST
  /apply-template`` renders the exact wire messages (``tools`` included) and
  ``POST /tokenize`` counts the rendered prompt around the single opaque
  media marker ``GET /props`` reports. This is the same technique
  ``scripts/a2t_g1_prompt_fit_np2.py`` already established.
* TEXT is identical for all 400 requests of a cell: the instruction is
  sample-independent and the audio is one opaque marker, so two distinct
  envelopes (legacy, native) cover all four cells. Raw-audio and packet cells
  of the same output contract share their text envelope exactly; only what
  the single marker stands for differs.
* SPEECH is measured per sample, from the promotion receipt's own per-packet
  ``n_tokens``. Those counts are the mmproj encoder's output for these exact
  audio bytes, so they are the true speech-token cost on BOTH audio paths
  (same encoder, same audio) -- not the 14.4 tokens/second approximation the
  registered geometry was sized with.

Zero generated tokens: only ``/props``, ``/apply-template`` and ``/tokenize``
are called, none of which decodes. The server is spawned under a gate-checked
:class:`~contracts.ExecutionPlan` bound to its own exposure row and stopped
with its own stop receipt.

2026-09-04 generalization (Audio2Tool official-protocol replication). The
four calibration cells were hard-coded here; the same measurement is now
driven by flags so a second experiment fragment reuses it rather than
forking a second script. Defaults reproduce the calibration run exactly.
Three capabilities were added for the official-protocol cell:

* the system text may come from a baseline fragment's frozen
  ``task_instruction_template`` + registered ``task_instruction_fill``
  (``core.instructions.resolve_task_instruction``), not only from a literal
  or from the adapter's legacy template;
* the user turn may carry a fragment-declared text part after the media
  (``user_turn_text`` / ``user_turn_audio_first``), which is what the
  published Audio2Tool protocol sends;
* the media stand-in follows the SERVER's prompt order: a speech-feature
  packet reference for the packet orders (as before), and a REAL
  ``input_audio`` part built from the roster's shortest wav for the
  raw-audio orders, so the rendered prompt is the one the flight sends.

``--expect-official-system-message`` additionally cross-checks the rendered
system text against the pinned Audio2Tool clone's own
``format_tools_compact`` over the same registry CSV, and records both
hashes in the receipt.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/a2t_calibration_prompt_fit.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
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
    resolve_task_instruction,
)
from speech_aware_evidence_acquisition.core.model.transport import (  # noqa: E402
    _SPEECH_FEATURE_PROMPT_ORDERS,
    _load_audio_part,
    _ordered_speech_feature_content,
)
from speech_aware_evidence_acquisition.core.policies import TOOL_SCHEMA_FILLS  # noqa: E402
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    render_audio2tool_instruction,
)

RUN_ID = "SAEA-A2T-DIRECT-CALIBRATION-PROMPT-FIT-V1"
EXPERIMENT = "a2t-direct-calibration-400-v1"
DATASET = "audio2tool-calibration-400"
PACKET_CELL = "P0-legacy-packets"
FLIGHT_SPLIT_IDENTITY_HASH = (
    "11091b38ae9d53530952af632636d7e79a614350213e10c6c26583c37f85846b"
)
RUNTIME_ROOT = Path("/home/chao")
PLAN_CALLS = 1
PLAN_AUDIO = 1
PLAN_GPU_HOURS = 0.3
SPECIAL_TOKEN_RESERVE = 2
RAW_NP2_RULE_THRESHOLD = 14800
OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-direct-calibration-400-v1"
    / "prompt-fit"
)


def log(message: str) -> None:
    print("[%s] %s" % (datetime.now(timezone.utc).strftime("%H:%M:%SZ"), message), flush=True)


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cells(experiment: str) -> list[Mapping[str, object]]:
    document = json.loads(
        (REPO / "configs" / "experiment" / f"{experiment}.json").read_text(encoding="utf-8")
    )
    return list(document["cells"])


def envelope_for(
    cell: Mapping[str, object], lock, root, *, experiment: str, dataset: str
) -> dict[str, object]:
    """The exact system text, ``tools`` list and user-turn text this cell's
    requests carry.

    The three instruction sources are exactly the three
    ``scripts/flights/run_calibration_cell.py::resolve_cell_instruction``
    honours, in the same precedence order, so what is measured here is what
    the flight sends -- a literal ``task_instruction``, an ACTIVE frozen
    template plus registered fill, or the adapter's legacy registry
    template.
    """

    composed = compose(
        REPO,
        str(cell["model_fragment"]),
        dataset,
        str(cell["baseline_fragment"]),
        experiment,
    )
    values = composed.values
    literal = values.get("task_instruction")
    if isinstance(literal, str) and literal:
        system_text = literal
        instruction_source = "baseline fragment literal task_instruction"
    elif values.get("task_instruction_template_active"):
        system_text = resolve_task_instruction(values, REPO, lock, root)
        instruction_source = "baseline fragment task_instruction_template + fill (%s + %s)" % (
            values.get("task_instruction_template"),
            values.get("task_instruction_fill"),
        )
    else:
        system_text = render_audio2tool_instruction(render_tool_schemas(lock, root))
        instruction_source = "rails.adapters.audio2tool.render_audio2tool_instruction"
    fill_name = values.get("tool_schema_fill")
    tools = None
    if isinstance(fill_name, str) and fill_name:
        tools = list(TOOL_SCHEMA_FILLS.resolve(fill_name)(lock, root))
    user_turn_text = values.get("user_turn_text")
    user_turn_audio_first = bool(values.get("user_turn_audio_first", True))
    geometry = values["serving_geometry"]
    return {
        "cell_id": str(cell["cell_id"]),
        "arm": str(values["arm"]),
        "model_fragment": str(cell["model_fragment"]),
        "system_text": system_text,
        "instruction_source": instruction_source,
        "tool_schema_fill": fill_name,
        "tools": tools,
        "user_turn_text": user_turn_text,
        "user_turn_audio_first": user_turn_audio_first,
        "slot_tokens": int(geometry["slot_tokens"]),
        "slots": int(geometry["slots"]),
        "completion_token_ceiling": int(geometry["max_tokens"]),
        "envelope_key": (
            sha256_text(system_text),
            canonical_sha256(tools or []),
            sha256_text(str(user_turn_text)) if user_turn_text else "",
            "audio-first" if user_turn_audio_first else "text-first",
        ),
    }


def wire_messages(
    system_text: str,
    prompt_order: str,
    *,
    data_root: Path | None = None,
    media_relpath: str | None = None,
    user_turn_text: object = None,
    user_turn_audio_first: bool = True,
) -> list[dict[str, object]]:
    """The exact two-message shape the transport puts on the wire for a
    one-contact direct request: the system instruction plus a user content
    sequence carrying exactly one opaque media part, plus the fragment's own
    user-turn text part when it declares one.

    The media stand-in follows the SERVER's prompt order. A speech-feature
    order builds the packet reference the transport itself would build (and
    asserts the transport orders it alone, unchanged from the calibration
    run). Any other order builds the REAL ``input_audio`` part through the
    transport's own ``_load_audio_part``, so the rendered prompt is exactly
    what a raw-audio flight sends rather than a packet-shaped proxy for it.
    """

    if prompt_order in _SPEECH_FEATURE_PROMPT_ORDERS:
        feature_parts = [
            {
                "type": "input_speech_features",
                "speech_features": {
                    "packet_id": "audit/a2t-calibration-prompt-fit/query",
                    "sha256": "0" * 64,
                    "role": "query",
                },
            }
        ]
        content = _ordered_speech_feature_content(
            prompt_order=prompt_order,
            evidence_texts=[],
            feature_parts=feature_parts,
            state_texts=(),
            knowledge_roles=(),
        )
        if content != feature_parts:
            raise SystemExit(
                "a zero-evidence direct contact must put exactly the one media part on "
                "the wire; the transport ordered it as %r" % (content,)
            )
    else:
        if data_root is None or not media_relpath:
            raise SystemExit(
                "a non-speech-feature prompt order needs a real media_relpath to render "
                "its input_audio part"
            )
        _, audio_part = _load_audio_part(
            Path(data_root), media_relpath, "prompt-fit media_relpath"
        )
        content = [audio_part]
    if user_turn_text:
        part = {"type": "text", "text": str(user_turn_text)}
        content = [*content, part] if user_turn_audio_first else [part, *content]
    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": content},
    ]


def text_token_count(client, messages, tools, media_marker, counts) -> tuple[int, str]:
    body: dict[str, object] = {"messages": list(messages)}
    if tools is not None:
        body["tools"] = list(tools)
    rendered = client.request_json("POST", "/apply-template", body)
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


def distribution(values: Sequence[int]) -> dict[str, object]:
    ordered = sorted(values)
    def percentile(fraction: float) -> int:
        index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
        return ordered[index]
    return {
        "count": len(ordered),
        "min": ordered[0],
        "median": float(statistics.median(ordered)),
        "p90": percentile(0.90),
        "p95": percentile(0.95),
        "max": ordered[-1],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", default=EXPERIMENT)
    parser.add_argument("--dataset", default=DATASET)
    parser.add_argument(
        "--server-cell",
        default=PACKET_CELL,
        help=(
            "which cell's model fragment supplies the RESIDENT server the rendering is "
            "measured on; its serving geometry is also the one the fit is certified "
            "against"
        ),
    )
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--flight-run-id", default="SAEA-A2T-DIRECT-CALIBRATION-V1")
    parser.add_argument(
        "--split-identity-hash", default=FLIGHT_SPLIT_IDENTITY_HASH
    )
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument(
        "--speech-token-receipt",
        type=Path,
        default=None,
        help=(
            "packet promotion receipt supplying per-sample speech token counts; "
            "defaults to the server cell's own speech_packet_promotion_receipt. A "
            "raw-audio cell has no promotion receipt of its own, but the counts are "
            "the SAME mmproj encoder output for the same audio bytes, so the packet "
            "campaign's receipt is the exact figure for it too"
        ),
    )
    parser.add_argument(
        "--slot-reserve-tokens",
        type=int,
        default=8192,
        help=(
            "the preregistered per-slot reserve every request must fit inside "
            "(2026-09-03 calibration preregistration section 4 item 3)"
        ),
    )
    parser.add_argument(
        "--expect-official-system-message",
        action="store_true",
        help=(
            "cross-check every cell's rendered system text against the pinned "
            "Audio2Tool clone's own system prompt + format_tools_compact over the "
            "same registry CSV, and record both hashes in the receipt"
        ),
    )
    return parser.parse_args()


def official_system_message(lock, root) -> str | None:
    """The pinned Audio2Tool release's own system message, built by ITS code.

    Imported from the local clone (``utils/tools_schema.py`` is stdlib-only:
    csv, pathlib, typing -- no torch, nothing installed), so this is a
    genuinely independent rendering of the same CSV, not a re-run of this
    repository's fill. ``None`` when the clone is absent.
    """

    clone = Path(str(root)) / "repos" / "audio2tool"
    schema_module = clone / "audio_benchmark" / "utils" / "tools_schema.py"
    if not schema_module.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_a2t_official_tools_schema", schema_module
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    csv_path = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root) / "tools_registry.csv"
    tool_lines = module.format_tools_compact(module.load_tools_from_csv(str(csv_path)))
    system_prompt = (
        "You are an AI assistant that converts voice commands into tool calls. "
        "Listen to the audio and determine which tool should be called. "
        "Output ONLY the tool call in the format: tool_name(param1=value1, param2=value2). "
        "If no parameters are mentioned, output: tool_name()."
    )
    return f"{system_prompt}\n\n## Available Tools:\n{tool_lines}"


def main() -> int:
    args = parse_args()
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    cell_rows = cells(args.experiment)
    envelopes = [
        envelope_for(cell, lock, root, experiment=args.experiment, dataset=args.dataset)
        for cell in cell_rows
    ]

    packet_cell = next(row for row in cell_rows if row["cell_id"] == args.server_cell)
    composed = compose(
        REPO,
        str(packet_cell["model_fragment"]),
        args.dataset,
        str(packet_cell["baseline_fragment"]),
        args.experiment,
    )
    values = composed.values
    geometry = values["serving_geometry"]
    prompt_order = str(values["prompt_order"])
    context_per_slot = int(geometry["slot_tokens"])

    # ---- exact speech tokens, from the registered promotion receipt ------
    promotion_path = Path(
        str(args.speech_token_receipt)
        if args.speech_token_receipt is not None
        else str(values["speech_packet_promotion_receipt"])
    )
    promotion = load_promotion_receipt(promotion_path)
    speech_by_packet: dict[str, int] = {}
    for entry in promotion["packets"]:
        n_tokens = entry.get("n_tokens")
        if not isinstance(n_tokens, int) or n_tokens <= 0:
            raise SystemExit("promotion receipt packet lacks a positive n_tokens")
        speech_by_packet[str(entry["packet_id"])] = n_tokens
    roster = json.loads(
        (REPO / str(values["a2t_calibration_subset_receipt"])).read_text(encoding="utf-8")
    )
    speech_by_sample: dict[str, int] = {}
    for item in roster["items"]:
        sample_id = str(item["sample_id"])
        packet_id = packet_id_for_sample(sample_id)
        if packet_id not in speech_by_packet:
            raise SystemExit("promotion receipt does not cover %s" % sample_id)
        speech_by_sample[sample_id] = speech_by_packet[packet_id]
    if len(speech_by_sample) != int(values["a2t_calibration_count"]):
        raise SystemExit("speech token coverage is incomplete")
    # The one real wav a non-speech-feature order needs to render its
    # input_audio part: the roster's SHORTEST, because the media is a single
    # opaque marker in the rendered prompt and the text count around it is
    # what is being measured -- picking the shortest keeps the /apply-template
    # request small while leaving the measured text identical. Deterministic
    # (sorted by (seconds, sample_id)) so the receipt is reproducible.
    shortest = min(
        roster["items"],
        key=lambda item: (float(item["audio_seconds"]), str(item["sample_id"])),
    )
    probe_media_relpath = str(shortest["media_relpath"])
    probe_media_sample_id = str(shortest["sample_id"])
    log(
        "media stand-in for non-packet orders: %s (%s s)"
        % (probe_media_sample_id, shortest["audio_seconds"])
    )

    official_message = (
        official_system_message(lock, root)
        if args.expect_official_system_message
        else None
    )
    if args.expect_official_system_message and official_message is None:
        raise SystemExit(
            "--expect-official-system-message needs the pinned Audio2Tool clone at "
            "$SPEECHRL_DATA_DIR/repos/audio2tool (see "
            "docs/receipts/environments/audio2tool-official-code.json)"
        )
    if official_message is not None:
        for envelope in envelopes:
            if envelope["system_text"] != official_message:
                raise SystemExit(
                    "cell %s renders a system message that is NOT the pinned release's "
                    "own (%s vs %s); refusing to certify a replication prompt that "
                    "differs from the published one"
                    % (
                        envelope["cell_id"],
                        sha256_text(envelope["system_text"])[:16],
                        sha256_text(official_message)[:16],
                    )
                )
        log(
            "official system message cross-check PASS: %d chars, sha256 %s"
            % (len(official_message), sha256_text(official_message)[:16])
        )
    log(
        "speech tokens from promotion receipt: %d samples, min=%d max=%d"
        % (
            len(speech_by_sample),
            min(speech_by_sample.values()),
            max(speech_by_sample.values()),
        )
    )

    # ---- gate, then spawn the packet server ------------------------------
    plan = ExecutionPlan(
        run_id=args.run_id,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=args.split_identity_hash,
        planned_model_calls=PLAN_CALLS,
        planned_gpu_hours=PLAN_GPU_HOURS,
        planned_speech_audio_seconds=PLAN_AUDIO,
        protocol_hash=composed.config_hash,
        attempt_id="attempt-%s-a2tcalpromptfit"
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
        slots=int(geometry["slots"]),
        context_tokens=int(geometry["slots"]) * context_per_slot,
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
    measured: dict[tuple[str, str], dict[str, object]] = {}
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
        # llama-server rounds each slot's n_ctx UP to a multiple of 512, so
        # the live figure can exceed the fragment's declared slot_tokens. A
        # LARGER live slot is safe (every margin below is computed against
        # the smaller declared figure); a SMALLER one would certify a fit
        # the server cannot honour, and is refused.
        if int(live_slot_ctx) < context_per_slot:
            raise SystemExit(
                "resident slot n_ctx %s is smaller than the fragment's declared %d; "
                "refusing to certify a fit the server cannot honour"
                % (live_slot_ctx, context_per_slot)
            )
        chat_template = props.get("chat_template")
        log("props OK: slot n_ctx=%s, media marker %r" % (live_slot_ctx, media_marker))

        for envelope in envelopes:
            key = envelope["envelope_key"]
            if key in measured:
                continue
            messages = wire_messages(
                envelope["system_text"],
                prompt_order,
                data_root=root,
                media_relpath=probe_media_relpath,
                user_turn_text=envelope["user_turn_text"],
                user_turn_audio_first=bool(envelope["user_turn_audio_first"]),
            )
            tokens, prompt = text_token_count(
                client, messages, envelope["tools"], media_marker, counts
            )
            if envelope["user_turn_text"] and str(envelope["user_turn_text"]) not in prompt:
                raise SystemExit(
                    "the pinned template did not render the declared user_turn_text; "
                    "refusing to certify a fit for a prompt the server would not build"
                )
            if envelope["tools"]:
                first_tool = envelope["tools"][0]["function"]["name"]
                if first_tool not in prompt:
                    raise SystemExit(
                        "the pinned template did not render the tools list "
                        "(tool %r absent from the rendered prompt); this build cannot "
                        "certify a native-tools prompt fit through /apply-template"
                        % first_tool
                    )
            measured[key] = {
                "text_prompt_tokens": tokens,
                "messages_sha256": canonical_sha256(messages),
                "tools_sha256": canonical_sha256(envelope["tools"] or []),
                "tools_count": len(envelope["tools"] or []),
                "rendered_prompt_sha256": sha256_text(prompt),
                "rendered_prompt_chars": len(prompt),
                "system_text_sha256": sha256_text(envelope["system_text"]),
                "system_text_chars": len(envelope["system_text"]),
                "system_text_verbatim_in_rendered_prompt": (
                    envelope["system_text"] in prompt
                ),
                "user_turn_text": envelope["user_turn_text"],
                "user_turn_audio_first": bool(envelope["user_turn_audio_first"]),
            }
            log(
                "envelope measured: %s tools=%d -> %d text tokens"
                % (
                    envelope["cell_id"],
                    len(envelope["tools"] or []),
                    tokens,
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
        log(
            "server stopped: %s forced=%s"
            % (stop_out.get("termination_signal"), stop_out.get("forced"))
        )

    # ---- per-cell required windows over all 400 requests -----------------
    cell_rows_out = []
    raw_worst = 0
    raw_slot_tokens = 0
    raw_slots = 0
    for envelope in envelopes:
        text_tokens = int(measured[envelope["envelope_key"]]["text_prompt_tokens"])
        completion = int(envelope["completion_token_ceiling"])
        required = {
            sample_id: text_tokens + speech + SPECIAL_TOKEN_RESERVE + completion
            for sample_id, speech in speech_by_sample.items()
        }
        worst_sample = max(required, key=lambda name: required[name])
        slot_tokens = int(envelope["slot_tokens"])
        margins = {name: slot_tokens - value for name, value in required.items()}
        fits = all(value > 0 for value in margins.values())
        row = {
            "cell_id": envelope["cell_id"],
            "arm": envelope["arm"],
            "model_fragment": envelope["model_fragment"],
            "instruction_source": envelope["instruction_source"],
            "tool_schema_fill": envelope["tool_schema_fill"],
            "tools_count": len(envelope["tools"] or []),
            "text_prompt_tokens": text_tokens,
            "completion_token_ceiling": completion,
            "special_token_reserve": SPECIAL_TOKEN_RESERVE,
            "slots": envelope["slots"],
            "slot_tokens": slot_tokens,
            "required_window_tokens": distribution(list(required.values())),
            "served_slot_margin_tokens": distribution(list(margins.values())),
            "worst_sample_id": worst_sample,
            "worst_required_window_tokens": required[worst_sample],
            "worst_served_slot_margin_tokens": margins[worst_sample],
            "every_request_fits": fits,
            **measured[envelope["envelope_key"]],
        }
        cell_rows_out.append(row)
        if "raw" in envelope["cell_id"].lower() or envelope["arm"].startswith("bare-core"):
            raw_worst = max(raw_worst, required[worst_sample])
            raw_slot_tokens = slot_tokens
            raw_slots = int(envelope["slots"])

    decision = {
        "rule": (
            "if the raw cells' worst request exceeds %d tokens, change the raw model "
            "fragment to -np 2 (24,576 tokens per slot); otherwise keep -np 3"
            % RAW_NP2_RULE_THRESHOLD
        ),
        "raw_worst_required_window_tokens": raw_worst,
        "threshold_tokens": RAW_NP2_RULE_THRESHOLD,
        "exceeds_threshold": raw_worst > RAW_NP2_RULE_THRESHOLD,
        "raw_slot_tokens_in_force": raw_slot_tokens,
        "raw_slots_in_force": raw_slots,
        "applied": (
            (
                "rule fired (raw worst %d > %d) and the raw model fragment is already "
                "at -np %d, %d tokens per slot; every raw request fits with at least "
                "%d tokens of margin"
                % (
                    raw_worst,
                    RAW_NP2_RULE_THRESHOLD,
                    raw_slots,
                    raw_slot_tokens,
                    raw_slot_tokens - raw_worst,
                )
            )
            if raw_worst > RAW_NP2_RULE_THRESHOLD
            else (
                "rule did not fire (raw worst %d <= %d); the raw model fragment stays "
                "at -np %d, %d tokens per slot"
                % (raw_worst, RAW_NP2_RULE_THRESHOLD, raw_slots, raw_slot_tokens)
            )
        ),
        "rule_satisfied_by_the_fragment_in_force": raw_slot_tokens > raw_worst,
    }

    # Generic per-slot reserve decision (2026-09-04). The block above is the
    # calibration's own -np 3 / -np 2 threshold rule and is kept verbatim so a
    # default re-run reproduces that receipt. THIS block is the rule any cell
    # can be read against: the 2026-09-03 preregistration's own requirement
    # that "every one of the 400 requests must fit its slot with the
    # 8,192-token reserve", applied per cell.
    reserve = int(args.slot_reserve_tokens)
    reserve_decision = {
        "rule": (
            "every request of a cell must fit its slot with at least %d tokens of "
            "reserve; slots x slot_tokens must equal the fragment's -c, and "
            "slot_tokens must be a multiple of 512 so llama-server's own rounding "
            "cannot make the live slot disagree with the declared one" % reserve
        ),
        "slot_reserve_tokens": reserve,
        "cells": {
            row["cell_id"]: {
                "slots": row["slots"],
                "slot_tokens": row["slot_tokens"],
                "context_tokens": int(row["slots"]) * int(row["slot_tokens"]),
                "slot_tokens_is_multiple_of_512": int(row["slot_tokens"]) % 512 == 0,
                "worst_required_window_tokens": row["worst_required_window_tokens"],
                "worst_served_slot_margin_tokens": row["worst_served_slot_margin_tokens"],
                "meets_reserve": int(row["worst_served_slot_margin_tokens"]) >= reserve,
                "largest_slot_count_meeting_reserve_at_this_context": (
                    int(row["slots"]) * int(row["slot_tokens"])
                )
                // max(1, int(row["worst_required_window_tokens"]) + reserve),
            }
            for row in cell_rows_out
        },
    }
    reserve_decision["all_cells_meet_reserve"] = all(
        entry["meets_reserve"] for entry in reserve_decision["cells"].values()
    )

    receipt = {
        "schema": "saea-a2t-calibration-prompt-fit-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "attempt_id": plan.attempt_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "flight_run_id": args.flight_run_id,
        "experiment_fragment": args.experiment,
        "dataset_fragment": args.dataset,
        "split_identity_hash": args.split_identity_hash,
        "sample_count": len(speech_by_sample),
        "server": {
            "port": port,
            "extra_argv": extra_argv,
            "slot_tokens_declared": context_per_slot,
            "slot_tokens_live": int(live_slot_ctx),
            "role": str(runtime_receipt.get("role", "legacy")),
            "llama_cpp_build_commit": runtime_receipt["llama_cpp"]["build_commit"],
            "chat_template_sha256": sha256_text(chat_template) if isinstance(chat_template, str) else None,
            "media_marker": media_marker,
            "load_seconds": round(load_seconds, 3),
            "stop_signal": stop_out.get("termination_signal") if stop_out else None,
            "stop_forced": bool(stop_out.get("forced")) if stop_out else None,
        },
        "contacts": counts,
        "speech_tokens": {
            "source": str(promotion_path),
            "source_sha256": sha256_file(promotion_path),
            "basis": (
                "the promotion receipt's own per-packet n_tokens -- the mmproj "
                "encoder's exact output for these audio bytes, therefore the true "
                "speech-token cost on both the raw-audio and the packet path"
            ),
            "distribution": distribution(list(speech_by_sample.values())),
            "registered_geometry_assumption": "35.714 s x 14.4 tokens/s = 514",
        },
        "cells": cell_rows_out,
        "media_stand_in": {
            "sample_id": probe_media_sample_id,
            "media_relpath": probe_media_relpath,
            "basis": (
                "used only for prompt orders that build a real input_audio part; the "
                "media is ONE opaque marker in the rendered prompt, so the text token "
                "count around it is identical for every sample of the roster"
            ),
        },
        "official_system_message_cross_check": (
            {
                "status": "PASS",
                "source": (
                    "the pinned Audio2Tool clone's own utils/tools_schema.py "
                    "(format_tools_compact + load_tools_from_csv) over the same "
                    "tools_registry.csv, executed from "
                    "$SPEECHRL_DATA_DIR/repos/audio2tool"
                ),
                "official_sha256": sha256_text(official_message),
                "official_chars": len(official_message),
                "rendered_sha256": sha256_text(envelopes[0]["system_text"]),
            }
            if official_message is not None
            else {"status": "NOT REQUESTED"}
        ),
        "decision": decision,
        "reserve_decision": reserve_decision,
        "boundary": (
            "zero generated tokens: only GET /props, POST /apply-template and POST "
            "/tokenize were called, none of which decodes. No gold, expected tool "
            "call, reference transcript, annotation, output, score, test datum or "
            "future turn was opened."
        ),
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "prompt-fit.json"
    out_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    log("prompt-fit receipt written: %s (sha256 %s)" % (out_path, sha256_file(out_path)[:12]))
    for row in cell_rows_out:
        log(
            "%-22s text=%-6d speech[min..max]=%d..%d required[min..max]=%d..%d "
            "slot=%d worst margin=%d fits=%s"
            % (
                row["cell_id"],
                row["text_prompt_tokens"],
                receipt["speech_tokens"]["distribution"]["min"],
                receipt["speech_tokens"]["distribution"]["max"],
                row["required_window_tokens"]["min"],
                row["required_window_tokens"]["max"],
                row["slot_tokens"],
                row["worst_served_slot_margin_tokens"],
                row["every_request_fits"],
            )
        )
    log("DECISION: %s" % decision["applied"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
