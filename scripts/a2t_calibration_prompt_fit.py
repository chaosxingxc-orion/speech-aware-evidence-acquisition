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

2026-09-05 phase programs (E1.3). A multi-contact cell's request is not the
adapter's one-contact prompt: each phase carries its own instruction on the
payload's Agent-history CONTROL turn, so a program whose select phase pastes
the 152-tool registry and whose fill phase does not has two envelopes that
differ by thousands of tokens, and ``FlightRuntime._assess_prompt_budget``
only ESTIMATES them (a 4-bytes-per-token heuristic over one representative
sample). ``--phase-program`` measures them: for every cell whose ``policy``
is a ``phase-*`` program it renders each phase's envelope for EVERY roster
sample through ``rails.phase_material.render_phase_envelope`` (reached
through ``core.flight.runtime.render_phase_prompt_envelopes``, the same
function the flight's own pre-flight verification re-renders with), groups
them by envelope sha256, measures each distinct envelope once on the
resident server, and writes a ``saea-phase-prompt-fit-v1`` receipt recording
per phase the maximum text-token count, the sample that attains it, the
whole distribution, and that maximum envelope's sha256. A phase envelope
carries the contact id and the sample's own packet descriptor, so it is
per-sample by construction: the measurement spends exactly one
``/apply-template`` render per contact the flight itself will make, and
every row is measured rather than extrapolated from a representative.

A fragment then pins that receipt with ``prompt_fit_receipt`` +
``prompt_fit_receipt_sha256`` and ``FlightRuntime.preflight`` refuses before
any contact unless every recorded ``envelope_sha256`` still reproduces --
i.e. unless the measured envelope is the one the flight would send.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/a2t_calibration_prompt_fit.py

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/a2t_calibration_prompt_fit.py --phase-program \\
        --experiment <experiment> --dataset <dataset> --out-dir <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

# The checkout this file belongs to. Derived from ``__file__`` rather than
# written as a literal so the script measures the tree it was invoked from --
# a git worktree included -- while the two guards below still refuse to run
# against a package resolved from anywhere else.
REPO = Path(__file__).resolve().parents[1]

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if (
    Path(_pkg.__file__ or "").resolve()
    != (REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py").resolve()
):
    raise SystemExit(
        "package resolves to %s, not this checkout (%s)" % (_pkg.__file__, REPO)
    )

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
from speech_aware_evidence_acquisition.data.carriers import (  # noqa: E402
    carrier_task_layout,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
    render_audio2tool_instruction,
)
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
        "--cells",
        default=None,
        help=(
            "comma-separated cell ids to measure; omit to measure every cell the "
            "experiment fragment declares. An experiment whose cells fly DIFFERENT "
            "rosters must be measured one cell at a time, because --dataset supplies "
            "the roster whose per-sample speech cost the fit is computed over"
        ),
    )
    parser.add_argument(
        "--speech-token-source",
        choices=("promotion", "window-rule"),
        default="promotion",
        help=(
            "where per-sample speech token counts come from. 'promotion' reads a packet "
            "promotion receipt's own per-packet n_tokens (exact, but only exists for a "
            "roster that has been preprocessed). 'window-rule' applies the mmproj "
            "encoder's one-second window rule n_tokens = window_tokens * ceil(seconds) "
            "to the roster's measured durations, after PROVING that rule reproduces "
            "every per-packet n_tokens of a reference promotion receipt"
        ),
    )
    parser.add_argument(
        "--speech-window-tokens",
        type=int,
        default=13,
        help="tokens the mmproj encoder emits per one-second audio window",
    )
    parser.add_argument(
        "--speech-token-rule-reference-receipt",
        type=Path,
        default=Path(
            "/home/chao/feat-cache/a2t-calibration-400-packets-04ccc72a/"
            "A2T-CALIBRATION-400-promotion.json"
        ),
        help=(
            "promotion receipt the window rule is proved against before it is applied "
            "to an unpreprocessed roster (--speech-token-source window-rule)"
        ),
    )
    parser.add_argument(
        "--speech-token-rule-reference-roster",
        type=Path,
        default=(
            REPO
            / "docs/checks/speech-aware-evidence-acquisition"
            / "2026-09-04-a2t-calibration-400-roster"
            / "flight-roster-receipt.json"
        ),
        help="roster supplying the reference receipt's own per-sample durations",
    )
    parser.add_argument(
        "--no-legacy-np-decision",
        dest="emit_legacy_np_decision",
        action="store_false",
        help=(
            "omit the calibration's own -np 3/-np 2 threshold block from the receipt; "
            "the generic per-slot reserve decision is the rule that applies to any cell, "
            "and the threshold block is meaningful only for the calibration cells it was "
            "written for"
        ),
    )
    parser.set_defaults(emit_legacy_np_decision=True)
    parser.add_argument(
        "--reference-media-marker",
        default=None,
        help=(
            "a PRIOR receipt's server.media_marker. llama-server mints a fresh random "
            "media marker per session, so two renderings of the same prompt on the same "
            "template never share a rendered_prompt_sha256 even when every other byte is "
            "identical. When this is given, the receipt additionally records the rendered "
            "prompt hashed with this server's marker REPLACED by the reference one: if "
            "that equals the prior receipt's rendered_prompt_sha256, the two prompts are "
            "byte-identical apart from the nonce, which is a proof rather than an "
            "inference. Omitted by default, so every existing receipt reproduces exactly"
        ),
    )
    parser.add_argument(
        "--official-registry-renderer",
        choices=("compact", "grouped"),
        default="compact",
        help=(
            "which of the pinned release's TWO registry renderers "
            "--expect-official-system-message builds its reference message with: "
            "'compact' is format_tools_compact (the sealed official-protocol cells) "
            "and 'grouped' is format_tools_for_prompt(tools, "
            "include_constraints=False) (the A2T-ORG-1 cell). Default 'compact', so "
            "every existing receipt reproduces exactly"
        ),
    )
    parser.add_argument(
        "--phase-program",
        action="store_true",
        help=(
            "measure a PHASE PROGRAM's per-phase envelopes instead of a one-contact "
            "direct request. Every selected cell's baseline fragment must declare a "
            "phase-* policy and its phase_material; each phase's envelope is rendered "
            "for every roster sample through rails.phase_material.render_phase_envelope "
            "and measured on the resident server. Writes a "
            "saea-phase-prompt-fit-v1 receipt"
        ),
    )
    parser.add_argument(
        "--expect-official-system-message",
        action="store_true",
        help=(
            "cross-check every cell's rendered system text against the pinned "
            "Audio2Tool clone's own system prompt + the renderer named by "
            "--official-registry-renderer over the same registry CSV, and record "
            "both hashes in the receipt"
        ),
    )
    return parser.parse_args()


# The pinned release spells the same four-sentence system prompt two ways.
# ``in-code-default`` is the HF adapter's hard-coded default (single spaces);
# ``example-config-yaml`` is the YAML block scalar in
# ``configs/example_config.yaml``, which ``run_benchmark.py`` passes to the
# adapter whenever a config file is used (newline-separated, trailing
# newline). They differ ONLY in whitespace.
OFFICIAL_SYSTEM_PROMPT_VARIANTS = {
    "in-code-default": (
        "You are an AI assistant that converts voice commands into tool calls. "
        "Listen to the audio and determine which tool should be called. "
        "Output ONLY the tool call in the format: tool_name(param1=value1, param2=value2). "
        "If no parameters are mentioned, output: tool_name()."
    ),
    "example-config-yaml": (
        "You are an AI assistant that converts voice commands into tool calls.\n"
        "Listen to the audio and determine which tool should be called.\n"
        "Output ONLY the tool call in the format: tool_name(param1=value1, param2=value2).\n"
        "If no parameters are mentioned, output: tool_name().\n"
    ),
}


def official_system_messages(lock, root, *, renderer: str = "compact") -> dict[str, str] | None:
    """The pinned Audio2Tool release's own system messages, built by ITS code.

    Imported from the local clone (``utils/tools_schema.py`` is stdlib-only:
    csv, pathlib, typing -- no torch, nothing installed), so this is a
    genuinely independent rendering of the same CSV, not a re-run of this
    repository's fill. ``None`` when the clone is absent. One entry per
    system-prompt variant the release itself carries; the composed message
    shape ``f"{system_prompt}\n\n## Available Tools:\n{tool_lines}"`` is the
    adapter's own and is identical for both.

    ``renderer`` names which of the release's TWO registry renderers builds
    ``tool_lines``: ``compact`` is ``format_tools_compact`` (what the sealed
    official-protocol cells flew) and ``grouped`` is
    ``format_tools_for_prompt(tools, include_constraints=False)`` (the
    A2T-ORG-1 cell's single factor). The default reproduces every existing
    receipt.
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
    tools = module.load_tools_from_csv(str(csv_path))
    if renderer == "grouped":
        tool_lines = module.format_tools_for_prompt(tools, include_constraints=False)
    elif renderer == "compact":
        tool_lines = module.format_tools_compact(tools)
    else:
        raise SystemExit("unknown official registry renderer %r" % (renderer,))
    return {
        name: f"{system_prompt}\n\n## Available Tools:\n{tool_lines}"
        for name, system_prompt in OFFICIAL_SYSTEM_PROMPT_VARIANTS.items()
    }


def speech_tokens_by_window_rule(roster_items, *, window_tokens: int) -> dict[str, int]:
    """``n_tokens = window_tokens * ceil(audio_seconds)`` per roster sample."""

    return {
        str(item["sample_id"]): window_tokens * int(math.ceil(float(item["audio_seconds"])))
        for item in roster_items
    }


def verify_window_rule(
    *, promotion_path: Path, roster_path: Path, window_tokens: int
) -> dict[str, object]:
    """Prove the one-second window rule against a promotion receipt whose
    per-packet ``n_tokens`` the mmproj encoder actually produced.

    Refuses on the first disagreement: a rule that is only usually right is
    not a basis for certifying that every request fits its slot.
    """

    promotion = load_promotion_receipt(promotion_path)
    measured_tokens = {
        str(entry["packet_id"]).replace("/", ":"): int(entry["n_tokens"])
        for entry in promotion["packets"]
    }
    roster = json.loads(Path(roster_path).read_text(encoding="utf-8"))
    checked = 0
    for item in roster["items"]:
        sample_id = str(item["sample_id"])
        actual = measured_tokens.get(sample_id)
        if actual is None:
            raise SystemExit(
                "window-rule reference roster sample %s is absent from the reference "
                "promotion receipt" % sample_id
            )
        predicted = window_tokens * int(math.ceil(float(item["audio_seconds"])))
        if predicted != actual:
            raise SystemExit(
                "window rule (%d tokens per one-second window) predicts %d speech tokens "
                "for %s but the mmproj encoder produced %d; refusing to certify a fit on "
                "an unproved rule" % (window_tokens, predicted, sample_id, actual)
            )
        checked += 1
    if checked != len(measured_tokens):
        raise SystemExit(
            "window-rule verification covered %d of the reference receipt's %d packets"
            % (checked, len(measured_tokens))
        )
    return {
        "window_tokens": window_tokens,
        "rule": "n_tokens = window_tokens * ceil(audio_seconds)",
        "reference_promotion_receipt": str(promotion_path),
        "reference_promotion_receipt_sha256": sha256_file(promotion_path),
        "reference_roster": str(roster_path),
        "reference_roster_sha256": sha256_file(roster_path),
        "packets_checked": checked,
        "disagreements": 0,
    }


# ---------------------------------------------------------------------------
# --phase-program: exact prompt fit for a multi-contact phase program.
#
# A phase program's request is NOT the adapter's one-contact prompt: each
# phase carries its own instruction on the payload's Agent-history CONTROL
# turn (rails.core_client._agent_history), so a cell whose select phase
# pastes the 152-tool registry and whose fill phase does not have two
# envelopes that differ by thousands of tokens. FlightRuntime's own
# _assess_prompt_budget estimates them from a 4-bytes-per-token heuristic
# over one representative sample; this measures them, on the resident
# server's own template and tokenizer, for every sample of the roster.
#
# The envelope bytes come from core.flight.runtime.render_phase_prompt_
# envelopes -- the SAME function FlightRuntime._verify_phase_prompt_fit
# re-renders with at pre-flight time -- so the receipt this writes is
# verifiable against the flight rather than merely adjacent to it.
# ---------------------------------------------------------------------------

#: task_kind -> flight adapter, the same mapping core.driver.cli._cli_flight
#: resolves a FlightRuntime adapter with. Named here rather than re-derived
#: so a cell measured by this script and the same cell flown through
#: FlightRuntime build their system message from one adapter, never two.
PHASE_ADAPTERS = {
    "speech-tool-use": Audio2ToolAdapter,
    "slot-slu": SlurpAdapter,
}


def phase_adapter_for(values: Mapping[str, object], lock, root):
    """The flight adapter this cell's carrier resolves to."""

    carrier_lock_key = values.get("carrier_lock_key")
    if not isinstance(carrier_lock_key, str) or not carrier_lock_key:
        raise SystemExit("dataset fragment must declare a non-empty carrier_lock_key")
    task_kind = carrier_task_layout(carrier_lock_key).task_kind
    adapter_class = PHASE_ADAPTERS.get(task_kind)
    if adapter_class is None:
        raise SystemExit(
            "no flight adapter for task_kind %r (carrier %r); known: %s"
            % (task_kind, carrier_lock_key, sorted(PHASE_ADAPTERS))
        )
    return adapter_class(lock, root, repo_root=REPO)


def phase_packet_bindings(promotion, sample_ids: Sequence[str]) -> dict[str, dict[str, str]]:
    """``{sample_id: {"packet_id", "sha256"}}`` -- exactly the descriptor
    ``FlightRuntime.speech_packet_bindings`` hands the transport, rebuilt
    from the same promotion receipt. Fail-closed on any uncovered sample:
    a phase envelope carries the packet reference verbatim, so a wrong or
    missing descriptor is a wrong envelope hash, not a smaller one."""

    registered = {
        str(entry["packet_id"]): str(entry["packet_sha256"])
        for entry in promotion["packets"]
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


def phase_cell_plan(cell, lock, root, *, experiment: str, dataset: str) -> dict[str, object]:
    """Everything a phase-program cell needs measured, rendered locally.

    No server is touched here: the envelopes are built for every sample and
    grouped by their own sha256, so the number of DISTINCT envelopes -- which
    is what the measurement spends apply-template calls on -- is known before
    the first request.
    """

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
            "cell %s declares policy %r, which is not a phase program; --phase-program "
            "measures per-phase envelopes only" % (cell["cell_id"], policy)
        )
    program = default_phase_program(policy)
    specs = load_phase_material_specs(values, program)
    static_text = {
        phase: render_static_instruction(spec, REPO, lock, root)
        for phase, spec in specs.items()
    }

    adapter = phase_adapter_for(values, lock, root)
    samples = tuple(adapter.load_split(str(values["split_id"])))
    if not samples:
        raise SystemExit("cell %s resolved zero samples" % cell["cell_id"])
    sample_ids = tuple(sample.sample_id for sample in samples)

    promotion_path = Path(str(values["speech_packet_promotion_receipt"]))
    promotion = load_promotion_receipt(promotion_path)
    bindings = phase_packet_bindings(promotion, sample_ids)

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

    geometry = values["serving_geometry"]
    prompt_order = str(values.get("prompt_order") or "speech-query-prefix-v2")
    ceiling = int(geometry["max_tokens"])
    fill_name = values.get("tool_schema_fill")
    tools = (
        list(TOOL_SCHEMA_FILLS.resolve(fill_name)(lock, root))
        if isinstance(fill_name, str) and fill_name
        else None
    )

    # phase -> sample_id -> envelope sha256, plus the envelope bytes once per
    # distinct hash.
    by_phase: dict[str, dict[str, str]] = {phase: {} for phase in program.phase_names()}
    envelopes_by_sha: dict[str, list] = {}
    for sample in samples:
        rendered = render_phase_prompt_envelopes(
            program_id=program.program_id,
            phase_names=program.phase_names(),
            specs=specs,
            static_text_by_phase=static_text,
            system_text=phase_program_system_text(adapter, sample),
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
        "samples": samples,
        "sample_ids": sample_ids,
        "promotion_path": promotion_path,
        "promotion": promotion,
        "tool_schema_fill": fill_name,
        "tools": tools,
        "slots": int(geometry["slots"]),
        "slot_tokens": int(geometry["slot_tokens"]),
        "completion_token_ceiling": ceiling,
        "phase_sha256_by_sample": by_phase,
        "envelopes_by_sha256": envelopes_by_sha,
    }


def phase_speech_tokens(plan, args) -> tuple[dict[str, int], dict[str, object]]:
    """Per-sample speech token counts for a phase-program cell, from the same
    two grounded sources the direct mode uses."""

    if args.speech_token_source == "window-rule":
        proof = verify_window_rule(
            promotion_path=Path(args.speech_token_rule_reference_receipt),
            roster_path=Path(args.speech_token_rule_reference_roster),
            window_tokens=int(args.speech_window_tokens),
        )
        window = int(args.speech_window_tokens)
        by_sample = {
            sample.sample_id: window * int(math.ceil(float(sample.audio_seconds)))
            for sample in plan["samples"]
        }
        return by_sample, {
            "source": "window rule over the roster's measured wav durations",
            "basis": (
                "n_tokens = %d * ceil(audio_seconds), the mmproj encoder's own "
                "one-second window; PROVED before use against every per-packet "
                "n_tokens of the reference promotion receipt named in "
                "window_rule_proof, with zero disagreements" % window
            ),
            "distribution": distribution(list(by_sample.values())),
            "window_rule_proof": proof,
        }
    by_packet: dict[str, int] = {}
    for entry in plan["promotion"]["packets"]:
        n_tokens = entry.get("n_tokens")
        if not isinstance(n_tokens, int) or n_tokens <= 0:
            raise SystemExit("promotion receipt packet lacks a positive n_tokens")
        by_packet[str(entry["packet_id"])] = n_tokens
    by_sample = {}
    for sample_id in plan["sample_ids"]:
        packet_id = packet_id_for_sample(sample_id)
        if packet_id not in by_packet:
            raise SystemExit("promotion receipt does not cover %s" % sample_id)
        by_sample[sample_id] = by_packet[packet_id]
    return by_sample, {
        "source": str(plan["promotion_path"]),
        "source_sha256": sha256_file(plan["promotion_path"]),
        "basis": (
            "the promotion receipt's own per-packet n_tokens -- the mmproj encoder's "
            "exact output for these audio bytes"
        ),
        "distribution": distribution(list(by_sample.values())),
    }


def phase_cell_rows(plan, measured, speech_by_sample, *, reserve: int) -> dict[str, object]:
    """One receipt cell: per phase, the measured text-token distribution over
    the whole roster, the required window per sample, and the identity of the
    envelope that attains the maximum."""

    specs = plan["specs"]
    slot_tokens = int(plan["slot_tokens"])
    ceiling = int(plan["completion_token_ceiling"])
    phases: list[dict[str, object]] = []
    worst_phase = None
    worst_required = 0
    fits = True
    for phase, sha_by_sample in plan["phase_sha256_by_sample"].items():
        spec = specs[phase]
        tokens_by_sample = {
            sample_id: int(measured[digest]["text_prompt_tokens"])
            for sample_id, digest in sha_by_sample.items()
        }
        max_sample = max(
            tokens_by_sample, key=lambda name: (tokens_by_sample[name], name)
        )
        required = {
            sample_id: tokens + speech_by_sample[sample_id] + SPECIAL_TOKEN_RESERVE + ceiling
            for sample_id, tokens in tokens_by_sample.items()
        }
        margins = {name: slot_tokens - value for name, value in required.items()}
        worst_sample = max(required, key=lambda name: (required[name], name))
        phase_fits = all(value > 0 for value in margins.values())
        fits = fits and phase_fits
        if required[worst_sample] > worst_required:
            worst_required = required[worst_sample]
            worst_phase = phase
        max_digest = sha_by_sample[max_sample]
        phases.append(
            {
                "phase": phase,
                "purpose": spec.purpose,
                "instruction_template": spec.instruction_template,
                "instruction_fill": spec.instruction_fill,
                "response_format_id": spec.response_format_id,
                "predecessor_binding": spec.predecessor_binding,
                "exact_envelope": spec.predecessor_binding != "append-sealed-state",
                "static_instruction_chars": len(plan["static_text"][phase]),
                "static_instruction_sha256": sha256_text(plan["static_text"][phase]),
                "distinct_envelopes": len(set(sha_by_sample.values())),
                "max_sample_id": max_sample,
                "max_text_prompt_tokens": tokens_by_sample[max_sample],
                "envelope_sha256": max_digest,
                "text_prompt_tokens": distribution(list(tokens_by_sample.values())),
                "required_window_tokens": distribution(list(required.values())),
                "served_slot_margin_tokens": distribution(list(margins.values())),
                "worst_sample_id": worst_sample,
                "worst_required_window_tokens": required[worst_sample],
                "worst_served_slot_margin_tokens": margins[worst_sample],
                "every_request_fits": phase_fits,
                "meets_reserve": margins[worst_sample] >= reserve,
                **{
                    key: value
                    for key, value in measured[max_digest].items()
                    if key != "text_prompt_tokens"
                },
            }
        )
    return {
        "cell_id": plan["cell_id"],
        "arm": plan["arm"],
        "policy": plan["policy"],
        "program_id": plan["program_id"],
        "model_fragment": plan["model_fragment"],
        "dataset_fragment": plan["dataset_fragment"],
        "baseline_fragment": plan["baseline_fragment"],
        "experiment_fragment": plan["experiment_fragment"],
        # Provenance, never a match key: FlightRuntime._verify_phase_prompt_fit
        # selects this cell by its four FRAGMENT NAMES, because a receipt is
        # measured from a fragment that does not yet pin it and pinning it
        # changes exactly this hash.
        "config_hash": plan["config_hash"],
        "carrier_lock_key": plan["carrier_lock_key"],
        "split_id": plan["split_id"],
        "prompt_order": plan["prompt_order"],
        "tool_schema_fill": plan["tool_schema_fill"],
        "tools_count": len(plan["tools"] or []),
        "sample_count": len(plan["sample_ids"]),
        "slots": plan["slots"],
        "slot_tokens": slot_tokens,
        "completion_token_ceiling": ceiling,
        "special_token_reserve": SPECIAL_TOKEN_RESERVE,
        "phases": phases,
        "worst_phase": worst_phase,
        "worst_required_window_tokens": worst_required,
        "worst_served_slot_margin_tokens": slot_tokens - worst_required,
        "every_request_fits": fits,
        "meets_reserve": (slot_tokens - worst_required) >= reserve,
    }


def phase_contact_allowance(plans) -> dict[str, object]:
    """The registered contact allowance for a phase-program measurement.

    A phase envelope is per-sample BY CONSTRUCTION: the Agent-history CONTROL
    turn carries the contact id (``[agent control <program>:<phase>:<sample>]``)
    and the user turn carries that sample's own speech-feature packet
    descriptor. There is no roster-wide envelope one call could measure, and
    a token count extrapolated from a representative would not be exact --
    which is the one property this script exists to provide.

    The allowance is therefore ``n_phases`` apply-template renders per SAMPLE:
    exactly one per contact the flight itself will make, and not one more. A
    program that rendered more distinct envelopes than it has contacts would
    mean the material depends on something outside (phase, sample), and is
    refused rather than measured.

    Raises ``SystemExit`` when the rendered envelopes exceed the allowance.
    """

    phase_total = sum(len(plan["phase_sha256_by_sample"]) for plan in plans)
    sample_total = sum(len(plan["sample_ids"]) for plan in plans)
    program_contacts = sum(
        len(plan["phase_sha256_by_sample"]) * len(plan["sample_ids"]) for plan in plans
    )
    distinct_total = len(
        {digest for plan in plans for digest in plan["envelopes_by_sha256"]}
    )
    if distinct_total > program_contacts:
        raise SystemExit(
            "the selected cells render %d distinct phase envelopes but the programs "
            "make only %d contact(s) (%d phase(s) x their samples); a phase whose "
            "material depends on something other than (phase, sample) cannot be "
            "certified" % (distinct_total, program_contacts, phase_total)
        )
    return {
        "rule": (
            "one apply-template render per CONTACT the flight makes: n_phases per "
            "sample. A phase envelope carries the contact id and the sample's own "
            "packet descriptor, so it is per-sample by construction and every row is "
            "measured rather than extrapolated"
        ),
        "phases": phase_total,
        "samples": sample_total,
        "program_contacts": program_contacts,
        "apply_template_calls_allowed": program_contacts,
        "distinct_envelopes": distinct_total,
        "within_allowance": True,
    }


def measure_phase_envelopes(client, plans, *, media_marker, counts, args) -> dict:
    """Measure every DISTINCT envelope once through /apply-template +
    /tokenize -- the same two routes and the same media-marker split the
    direct mode uses, so the counts are comparable across modes."""

    measured: dict[str, dict[str, object]] = {}
    for plan in plans:
        for digest, envelope in plan["envelopes_by_sha256"].items():
            if digest in measured:
                continue
            tokens, prompt = text_token_count(
                client, envelope, plan["tools"], media_marker, counts
            )
            measured[digest] = {
                "text_prompt_tokens": tokens,
                "rendered_prompt_sha256": sha256_text(prompt),
                "rendered_prompt_chars": len(prompt),
                "messages_sha256": canonical_sha256(list(envelope)),
                "tools_sha256": canonical_sha256(plan["tools"] or []),
                **(
                    {
                        "reference_media_marker": str(args.reference_media_marker),
                        "rendered_prompt_sha256_with_reference_marker": sha256_text(
                            prompt.replace(media_marker, str(args.reference_media_marker))
                        ),
                    }
                    if args.reference_media_marker
                    else {}
                ),
            }
    return measured


def main_phase_program(args) -> int:
    """``--phase-program``: measure every phase's envelope, write a
    ``saea-phase-prompt-fit-v1`` receipt."""

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    cell_rows = cells(args.experiment)
    if args.cells:
        wanted = [part.strip() for part in str(args.cells).split(",") if part.strip()]
        known = {str(cell["cell_id"]) for cell in cell_rows}
        unknown = [name for name in wanted if name not in known]
        if unknown:
            raise SystemExit(
                "unknown cell(s) %r; this experiment declares %s" % (unknown, sorted(known))
            )
        cell_rows = [cell for cell in cell_rows if str(cell["cell_id"]) in wanted]
    if not cell_rows:
        raise SystemExit("no cells selected")

    plans = [
        phase_cell_plan(cell, lock, root, experiment=args.experiment, dataset=args.dataset)
        for cell in cell_rows
    ]

    allowance = phase_contact_allowance(plans)
    distinct_total = int(allowance["distinct_envelopes"])
    log(
        "%d cell(s), %d phase(s), %d sample(s): %d contact envelope(s) to measure"
        % (
            len(plans),
            allowance["phases"],
            allowance["samples"],
            distinct_total,
        )
    )

    server_plan = next(
        (plan for plan in plans if plan["cell_id"] == args.server_cell), None
    )
    if server_plan is None:
        if args.server_cell != PACKET_CELL:
            raise SystemExit(
                "--server-cell %r is not among the selected cells %s"
                % (args.server_cell, [plan["cell_id"] for plan in plans])
            )
        server_plan = plans[0]
    values = server_plan["values"]
    geometry = values["serving_geometry"]
    context_per_slot = int(geometry["slot_tokens"])

    speech_by_cell: dict[str, dict[str, int]] = {}
    speech_record: dict[str, object] = {}
    for plan in plans:
        by_sample, record = phase_speech_tokens(plan, args)
        speech_by_cell[plan["cell_id"]] = by_sample
        speech_record[plan["cell_id"]] = record
        log(
            "%s: %d samples, speech tokens min=%d max=%d, %d phase(s), %d distinct "
            "envelope(s)"
            % (
                plan["cell_id"],
                len(by_sample),
                min(by_sample.values()),
                max(by_sample.values()),
                len(plan["phase_sha256_by_sample"]),
                len(plan["envelopes_by_sha256"]),
            )
        )

    identity_hash = args.split_identity_hash
    if identity_hash == FLIGHT_SPLIT_IDENTITY_HASH:
        identity_hash = split_identity_hash(
            prefixed(server_plan["carrier_lock_key"], server_plan["sample_ids"])
        )
        log("split identity hash computed from the roster: %s" % identity_hash[:16])

    plan_record = ExecutionPlan(
        run_id=args.run_id,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=server_plan["carrier_lock_key"],
        split_role="discovery",
        split_identity_hash=identity_hash,
        planned_model_calls=PLAN_CALLS,
        planned_gpu_hours=PLAN_GPU_HOURS,
        planned_speech_audio_seconds=PLAN_AUDIO,
        protocol_hash=server_plan["config_hash"],
        attempt_id="attempt-%s-a2tphasepromptfit"
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
        slots=int(geometry["slots"]),
        context_tokens=int(geometry["slots"]) * context_per_slot,
    )
    port = int(str(values["base_url"]).rsplit(":", 1)[-1])
    log("spawning the server on %d: %s" % (port, " ".join(extra_argv)))
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

    counts = {"GET /props": 0, "POST /apply-template": 0, "POST /tokenize": 0, "generations": 0}
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
                "resident slot n_ctx %s is smaller than the fragment's declared %d; "
                "refusing to certify a fit the server cannot honour"
                % (live_slot_ctx, context_per_slot)
            )
        chat_template = props.get("chat_template")
        log("props OK: slot n_ctx=%s, media marker %r" % (live_slot_ctx, media_marker))
        measured = measure_phase_envelopes(
            client, plans, media_marker=media_marker, counts=counts, args=args
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
    if counts["POST /apply-template"] > int(allowance["apply_template_calls_allowed"]):
        raise SystemExit(
            "spent %d apply-template call(s) against an allowance of %d"
            % (counts["POST /apply-template"], allowance["apply_template_calls_allowed"])
        )
    if counts["generations"] != 0:
        raise SystemExit("a prompt-fit measurement must never generate a token")

    reserve = int(args.slot_reserve_tokens)
    cell_rows_out = [
        phase_cell_rows(plan, measured, speech_by_cell[plan["cell_id"]], reserve=reserve)
        for plan in plans
    ]
    receipt = {
        "schema": PHASE_PROMPT_FIT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "attempt_id": plan_record.attempt_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "flight_run_id": args.flight_run_id,
        "experiment_fragment": args.experiment,
        "dataset_fragment": args.dataset,
        "split_identity_hash": identity_hash,
        "server": {
            "port": port,
            "cell_id": server_plan["cell_id"],
            "extra_argv": extra_argv,
            "slot_tokens_declared": context_per_slot,
            "slot_tokens_live": int(live_slot_ctx),
            "role": str(runtime_receipt.get("role", "legacy")),
            "llama_cpp_build_commit": runtime_receipt["llama_cpp"]["build_commit"],
            "chat_template_sha256": (
                sha256_text(chat_template) if isinstance(chat_template, str) else None
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
        "speech_tokens": speech_record,
        "cells": cell_rows_out,
        "reserve_decision": {
            "rule": (
                "every phase contact of a cell must fit its slot with at least %d "
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
                for row in cell_rows_out
            },
            "all_cells_meet_reserve": all(row["meets_reserve"] for row in cell_rows_out),
        },
        "boundary": (
            "zero generated tokens: only GET /props, POST /apply-template and POST "
            "/tokenize were called, none of which decodes. No gold, expected tool "
            "call, reference transcript, annotation, output, score, test datum or "
            "future turn was opened."
        ),
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "phase-prompt-fit.json"
    out_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    log("phase prompt-fit receipt written: %s (sha256 %s)" % (out_path, sha256_file(out_path)))
    for row in cell_rows_out:
        for phase in row["phases"]:
            log(
                "%-22s %-10s text[min..max]=%d..%d max_sample=%s required max=%d "
                "slot=%d margin=%d fits=%s"
                % (
                    row["cell_id"],
                    phase["phase"],
                    phase["text_prompt_tokens"]["min"],
                    phase["text_prompt_tokens"]["max"],
                    phase["max_sample_id"],
                    phase["worst_required_window_tokens"],
                    row["slot_tokens"],
                    phase["worst_served_slot_margin_tokens"],
                    phase["every_request_fits"],
                )
            )
    log(
        "RESERVE DECISION: reserve=%d all_cells_meet_reserve=%s"
        % (reserve, receipt["reserve_decision"]["all_cells_meet_reserve"])
    )
    return 0


def main() -> int:
    args = parse_args()
    if args.phase_program:
        return main_phase_program(args)
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    cell_rows = cells(args.experiment)
    if args.cells:
        wanted = [part.strip() for part in str(args.cells).split(",") if part.strip()]
        known = {str(cell["cell_id"]) for cell in cell_rows}
        unknown = [name for name in wanted if name not in known]
        if unknown:
            raise SystemExit(
                "unknown cell(s) %r; this experiment declares %s"
                % (unknown, sorted(known))
            )
        cell_rows = [cell for cell in cell_rows if str(cell["cell_id"]) in wanted]
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

    # ---- per-sample speech tokens ---------------------------------------
    # Two sources, both grounded in the mmproj encoder's own output. A roster
    # that has been packet-preprocessed has EXACT per-packet n_tokens; a
    # roster that has not (a raw-audio cell needs no packets) is costed by the
    # encoder's one-second window rule, which is first proved to reproduce
    # every per-packet n_tokens of a reference promotion receipt.
    roster_path = REPO / str(values["a2t_calibration_subset_receipt"])
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    promotion_path: Path | None = None
    window_rule_proof: dict[str, object] | None = None
    speech_by_sample: dict[str, int] = {}
    if args.speech_token_source == "window-rule":
        window_rule_proof = verify_window_rule(
            promotion_path=Path(args.speech_token_rule_reference_receipt),
            roster_path=Path(args.speech_token_rule_reference_roster),
            window_tokens=int(args.speech_window_tokens),
        )
        log(
            "window rule PROVED on %d reference packets: %d tokens per one-second window"
            % (window_rule_proof["packets_checked"], int(args.speech_window_tokens))
        )
        speech_by_sample = speech_tokens_by_window_rule(
            roster["items"], window_tokens=int(args.speech_window_tokens)
        )
    else:
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

    official_messages = (
        official_system_messages(lock, root, renderer=args.official_registry_renderer)
        if args.expect_official_system_message
        else None
    )
    if args.expect_official_system_message and official_messages is None:
        raise SystemExit(
            "--expect-official-system-message needs the pinned Audio2Tool clone at "
            "$SPEECHRL_DATA_DIR/repos/audio2tool (see "
            "docs/receipts/environments/audio2tool-official-code.json)"
        )
    official_variant_by_cell: dict[str, str] = {}
    if official_messages is not None:
        # A cell must render ONE of the release's own spellings of its system
        # message; which one is recorded per cell, because the whitespace
        # variant is itself a factor this flight varies.
        by_text = {text: name for name, text in official_messages.items()}
        for envelope in envelopes:
            variant = by_text.get(envelope["system_text"])
            if variant is None:
                raise SystemExit(
                    "cell %s renders a system message that is NOT one of the pinned "
                    "release's own spellings (%s; known: %s); refusing to certify a "
                    "replication prompt that differs from the published one"
                    % (
                        envelope["cell_id"],
                        sha256_text(envelope["system_text"])[:16],
                        ", ".join(
                            "%s=%s" % (name, sha256_text(text)[:16])
                            for name, text in sorted(official_messages.items())
                        ),
                    )
                )
            official_variant_by_cell[str(envelope["cell_id"])] = variant
            log(
                "official system message cross-check PASS for %s: variant %s, %d chars, "
                "sha256 %s"
                % (
                    envelope["cell_id"],
                    variant,
                    len(envelope["system_text"]),
                    sha256_text(envelope["system_text"])[:16],
                )
            )
    log(
        "speech tokens (%s): %d samples, min=%d max=%d"
        % (
            args.speech_token_source,
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
                **(
                    {
                        "reference_media_marker": str(args.reference_media_marker),
                        "rendered_prompt_sha256_with_reference_marker": sha256_text(
                            prompt.replace(
                                media_marker, str(args.reference_media_marker)
                            )
                        ),
                    }
                    if args.reference_media_marker
                    else {}
                ),
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
        "speech_tokens": (
            {
                "source": str(promotion_path),
                "source_sha256": sha256_file(promotion_path),
                "basis": (
                    "the promotion receipt's own per-packet n_tokens -- the mmproj "
                    "encoder's exact output for these audio bytes, therefore the true "
                    "speech-token cost on both the raw-audio and the packet path"
                ),
                "distribution": distribution(list(speech_by_sample.values())),
                "registered_geometry_assumption": "35.714 s x 14.4 tokens/s = 514",
            }
            if promotion_path is not None
            else {
                "source": "window rule over the roster's measured wav durations",
                "source_sha256": sha256_file(roster_path),
                "basis": (
                    "n_tokens = %d * ceil(audio_seconds), the mmproj encoder's own "
                    "one-second window; PROVED before use against every per-packet "
                    "n_tokens of the reference promotion receipt named in "
                    "window_rule_proof, with zero disagreements. This roster has no "
                    "promotion receipt of its own because a raw-audio cell needs no "
                    "packets" % int(args.speech_window_tokens)
                ),
                "distribution": distribution(list(speech_by_sample.values())),
                "window_rule_proof": window_rule_proof,
            }
        ),
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
                "registry_renderer": args.official_registry_renderer,
                "source": (
                    "the pinned Audio2Tool clone's own utils/tools_schema.py "
                    "(%s + load_tools_from_csv) over the same tools_registry.csv, "
                    "executed from $SPEECHRL_DATA_DIR/repos/audio2tool"
                    % (
                        "format_tools_for_prompt(..., include_constraints=False)"
                        if args.official_registry_renderer == "grouped"
                        else "format_tools_compact"
                    )
                ),
                "variants": {
                    name: {
                        "sha256": sha256_text(text),
                        "chars": len(text),
                        "system_prompt_sha256": sha256_text(
                            OFFICIAL_SYSTEM_PROMPT_VARIANTS[name]
                        ),
                    }
                    for name, text in sorted(official_messages.items())
                },
                "variant_by_cell": official_variant_by_cell,
                "rendered_sha256_by_cell": {
                    str(envelope["cell_id"]): sha256_text(envelope["system_text"])
                    for envelope in envelopes
                },
            }
            if official_messages is not None
            else {"status": "NOT REQUESTED"}
        ),
        "decision": (
            decision
            if args.emit_legacy_np_decision
            else {
                "status": "NOT APPLICABLE",
                "reason": (
                    "the -np 3 / -np 2 threshold block is the 2026-09-04 calibration's "
                    "own rule for its own two raw cells; this run is read against the "
                    "generic per-slot reserve decision below"
                ),
            }
        ),
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
    if args.emit_legacy_np_decision:
        log("DECISION: %s" % decision["applied"])
    log(
        "RESERVE DECISION: reserve=%d all_cells_meet_reserve=%s"
        % (reserve, reserve_decision["all_cells_meet_reserve"])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
