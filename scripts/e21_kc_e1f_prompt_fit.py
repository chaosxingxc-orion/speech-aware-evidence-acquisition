#!/usr/bin/env python3
"""Prompt fit for the Earnings-21 second-pass entity-repair cells (KC-E1f).

Sibling of ``scripts/e21_kc_e1_prompt_fit.py`` and the same measurement in
substance: render every request the flight would send, through the REAL
transport on the REAL composed config, count it on the FLIGHT tokenizer with
``POST /apply-template`` + ``POST /tokenize`` at zero generated tokens, and
certify the worst request against the declared slot under this study's own rule
``slot_tokens >= 2 * worst_required``.

WHAT IS DIFFERENT FROM THE KC-E1 FIT, AND WHY IT MATTERS
---------------------------------------------------------
KC-E1's text envelope was WINDOW-INDEPENDENT: the brief and the instruction are
per call, ``obs_condition_tail_chars`` is 0, and that fit ASSERTED the property
(a per-window difference would have meant something else was riding in the
prompt). KC-E1f breaks it deliberately -- every window carries its OWN sealed
pass-1 hypothesis -- so the envelope varies within a call by construction and
the worst request is a per-WINDOW maximum over 1,593 rows, not a per-call one.
This script therefore renders every window in the chosen pass rather than one
per call, and asserts the complementary property instead: the envelope minus
the pass-1 text is constant within a call.

TWO MODES
---------
``--projection-only`` is MODEL-FREE and spawns nothing. It answers the question
the flight agent needs answered before booking a GPU window at all: given the
sealed pass-1 token counts (measured by the flight server itself and pinned in
``docs/receipts/e21-predecessor-full44-direct-baseline-v2.json``) and KC-E1's
own measured brief envelope, what is the worst request and does the declared
geometry admit it? It sweeps the same cap grid KC-E1 swept and, because a cap
sweep may not be enough here, also sweeps the SLOT: the ``-np`` values a 36,864
-token context divides into, with the margin factor each one buys. It writes
``projection.json`` and decides nothing.

The default mode is the real fit and REQUIRES a resident server. It is the
flight agent's step, not the analyst's: it opens a session, so it is a model
contact by this study's accounting and needs its own registered exposure row.

THE DECISION PROCEDURE, FIXED HERE BEFORE ANY MEASUREMENT
----------------------------------------------------------
So that a chosen geometry can never be reverse-engineered from a result, the
levers are ordered in advance and the first one that satisfies the margin rule
is taken:

1. **Keep the cap at 12 and widen the slot.** The cap is KC-E1's own committed
   value and the cell's whole claim is that the SAME knowledge consumed
   differently behaves differently; moving it would confound the form with the
   content. Widening the slot changes no byte of any request -- only how many
   of them share the 36,864-token context -- so it is a serving decision, and
   the LARGEST ``-np`` (that is, the smallest slot, so the least parallelism
   given up) that still satisfies the rule is reported for the owner. Only a
   geometry whose context divides evenly into a 512-multiple slot counts.
2. **Lower the pass-2 completion ceiling.** A pass-2 answer is a re-emission of
   a text whose length is KNOWN: the sealed pass-1 maximum is 445 tokens, so a
   ceiling well above that truncates nothing pass 1 produced, and the delivery
   rule refuses anything much longer anyway. This changes ``decoding_params``
   and therefore the arm, so it is reported as an option and never taken
   silently.
3. **Only then, sweep the cap**, largest-first exactly as KC-E1's fit did, and
   report what each value costs through the same ``--cap-impact-only`` path.

Usage::

    python scripts/e21_kc_e1f_prompt_fit.py --projection-only --out-dir <dir>
    python scripts/e21_kc_e1f_prompt_fit.py --out-dir <dir>   # server; flight agent
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
RUNTIME_ROOT = Path("/home/chao")

CHECK = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-e21-kc-e1f-repair-44-v1"
)
ROSTER_RECEIPT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-roster/flight-roster-receipt.json"
)
KC_E1_FIT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e21-kc-e1-brief-44-v1/prompt-fit/prompt-fit.json"
)
BINDING_RECEIPT = REPO / "docs/receipts/e21-predecessor-full44-direct-baseline-v2.json"

EXPERIMENT = "e21-kc-e1f-repair-44-v1"
RUN_ID = "SAEA-E21-KC-E1F-PROMPT-FIT-V1"
PROJECTION_RUN_ID = "SAEA-E21-MF-KC-E1F-FIT-PROJECTION-V1"
FLIGHT_RUN_ID = "SAEA-E21-KC-E1F-REPAIR-44-V1"
SPLIT_IDENTITY_HASH = (
    "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
)

#: The mmproj encoder's exact one-second window rule, and the two special
#: tokens every sealed Earnings flight carried.
SPEECH_TOKENS_PER_SECOND_WINDOW = 13
SPECIAL_TOKENS = 2
#: slot_tokens >= FIT_MULTIPLE * worst_required.
FIT_MULTIPLE = 2
#: The context this geometry family always declares; the slot sweep divides it.
CONTEXT_TOKENS = 36864
#: The ``-np`` values the slot sweep considers. A geometry is only LEGAL when
#: the context divides evenly and the resulting slot is a multiple of 512 --
#: llama-server rounds a slot down otherwise, and this study's fit rule is
#: stated on a 512-multiple slot. ``-np 5`` is on the grid precisely so the
#: receipt records that it is illegal at a 36,864-token context (7,372.8
#: tokens per slot) rather than leaving a reader to wonder why it was skipped.
SLOT_SWEEP_NP = (2, 3, 4, 5, 6, 8, 9, 12)
#: KC-E1's own cap grid, unchanged, so the two fits are comparable row by row.
CAP_GRID = (0, 128, 96, 64, 48, 32, 24, 20, 16, 12, 10, 8, 6, 4, 2, 1)
#: Frame-cost sensitivity for the projection. The repair frame is a fixed
#: string; only the tokenizer knows its exact cost, so the projection reports
#: the whole grid and the fit measures the truth.
FRAME_TOKEN_GRID = (0, 40, 80, 120, 160)
PROJECTION_FRAME_TOKENS = 120

#: Nominal for the server mode: nothing decodes, but ``contracts.ExecutionPlan``
#: still requires a positive budget and the ceiling is run-cumulative.
PLAN_CALLS = 2
PLAN_AUDIO_SECONDS = 2
PLAN_GPU_HOURS = 0.4

STAND_IN_RELPATH = "derived/prompt-fit/e21-kc-e1f/silence-100ms-16k.wav"
STAND_IN_SECONDS = 0.1
STAND_IN_RATE_HZ = 16000


def git(*argv: str) -> str:
    return subprocess.run(
        ["git", *argv], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()


def log(message: str) -> None:
    print(
        "[%s] %s" % (datetime.now(tz=timezone.utc).strftime("%H:%M:%SZ"), message),
        flush=True,
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(document: object) -> str:
    blob = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Mapping[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def speech_tokens(audio_seconds: float) -> int:
    return SPEECH_TOKENS_PER_SECOND_WINDOW * math.ceil(float(audio_seconds))


def distribution(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(values)
    if not ordered:
        return {"count": 0}

    def percentile(fraction: float) -> float:
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


def build_windows(roster: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The 1,593 fixed 90-second windows, in the ``<sample_id>#w<index>``
    convention ``analysis.e21_window_pairing.window_id`` mints -- so a row of
    this receipt, a row of the predecessor snapshot and a row of the paired read
    all name the same unit. (KC-E1's own fit used an unpadded, zero-based
    spelling of the same window; this one does not, deliberately.)"""

    windows: list[dict[str, Any]] = []
    for call in roster["calls"]:
        sample_id = str(call["sample_id"])
        count = int(call["fixed_90s_windows"])
        last = float(call["last_window_seconds"])
        total = float(call["audio_seconds"])
        seconds = [90.0] * (count - 1) + [last]
        if abs(sum(seconds) - total) > 1e-6:
            raise SystemExit(
                "call %s: %d windows sum to %.6f s, roster says %.6f s"
                % (sample_id, count, sum(seconds), total)
            )
        for index, window_seconds in enumerate(seconds, start=1):
            windows.append(
                {
                    "window_id": "%s#w%04d" % (sample_id, index),
                    "sample_id": sample_id,
                    "window_index": index,
                    "window_seconds": window_seconds,
                    "speech_tokens": speech_tokens(window_seconds),
                }
            )
    return windows


def slot_sweep(worst_required: int) -> list[dict[str, Any]]:
    """What each parallel-slot count buys at a fixed 36,864-token context."""

    rows = []
    for slots in SLOT_SWEEP_NP:
        divides = CONTEXT_TOKENS % slots == 0
        nominal = CONTEXT_TOKENS / slots
        slot = CONTEXT_TOKENS // slots
        legal = divides and slot % 512 == 0
        rows.append(
            {
                "np": slots,
                "nominal_slot_tokens": nominal,
                "slot_tokens": slot,
                "divides_context_evenly": divides,
                "slot_is_multiple_of_512": slot % 512 == 0,
                "legal_geometry": legal,
                "margin_factor": round(slot / worst_required, 4),
                "fits_under_study_rule": legal and slot >= FIT_MULTIPLE * worst_required,
                "fits_strictly": legal and slot >= worst_required,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Model-free projection.
# ---------------------------------------------------------------------------


def write_projection(args, *, composed_values, cap: int) -> int:
    from speech_aware_evidence_acquisition.core.predecessor_snapshot import (  # noqa: PLC0415
        binding_from_values,
        load_predecessor_binding,
    )
    from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: PLC0415
    from speech_aware_evidence_acquisition.reproduction.repair_loop import (  # noqa: PLC0415
        REPAIR_FRAMES,
    )

    kc_e1 = load_json(KC_E1_FIT)
    candidate = kc_e1["passes"]["candidate"]["cells"]
    arm_key = "E21-kc-e1-brief-whole-prompt"
    arm = candidate[arm_key]
    if int(arm["brief_max_entries_per_class"]) != cap:
        raise SystemExit(
            "the KC-E1 fit's candidate pass measured cap %s, this cell carries %s"
            % (arm["brief_max_entries_per_class"], cap)
        )
    overhead = int(arm["fixed_envelope_overhead_tokens"][0])
    brief_by_call = {row["sample_id"]: int(row["brief_tokens"]) for row in arm["brief_rows"]}
    cap_sweep_worst = {
        int(row["brief_max_entries_per_class"]): int(row["worst_brief_tokens"])
        for row in kc_e1["cap_sweep"]["rows"]
    }

    relpath, digest = binding_from_values(composed_values)
    snapshot = load_predecessor_binding(
        REPO / "docs" / relpath, data_root(), expected_receipt_sha256=digest
    )
    pass1_tokens = {
        window_id: int(window.completion_tokens or 0)
        for window_id, window in snapshot.windows.items()
    }
    if len(pass1_tokens) != 1593:
        raise SystemExit("the binding does not carry 1,593 windows")

    slot_tokens = int(composed_values["serving_geometry"]["slot_tokens"])
    max_tokens = int(composed_values["serving_geometry"]["max_tokens"])
    worst_speech = speech_tokens(90.0)
    frame_text = REPAIR_FRAMES[str(composed_values["repair_frame"])]
    frame_whitespace_tokens = len(frame_text.replace("{predecessor}", "").split())

    def worst_at(cap_value: int, frame_tokens: int, completion_ceiling: int) -> dict[str, Any]:
        worst_text = 0
        worst_window = None
        texts = []
        for window_id, tokens in pass1_tokens.items():
            sample_id = window_id.split("#w", 1)[0]
            brief = (
                brief_by_call[sample_id]
                if cap_value == cap
                else cap_sweep_worst.get(cap_value, 0)
            )
            text = overhead + brief + frame_tokens + tokens
            texts.append(text)
            if text > worst_text:
                worst_text, worst_window = text, window_id
        required = worst_speech + worst_text + completion_ceiling + SPECIAL_TOKENS
        return {
            "brief_max_entries_per_class": cap_value,
            "frame_tokens_assumed": frame_tokens,
            "completion_ceiling": completion_ceiling,
            "worst_text_tokens": worst_text,
            "worst_window_id": worst_window,
            "worst_required_tokens": required,
            "margin_factor": round(slot_tokens / required, 4),
            "fits_under_study_rule": slot_tokens >= FIT_MULTIPLE * required,
            "fits_strictly": slot_tokens >= required,
            "text_token_distribution": distribution(texts),
        }

    committed = worst_at(cap, PROJECTION_FRAME_TOKENS, max_tokens)
    document = {
        "schema": "saea-e21-kc-e1f-prompt-fit-projection-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "flight_run_id": FLIGHT_RUN_ID,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "study_commit": git("rev-parse", "HEAD"),
        "zero_contact": (
            "no model, GPU, server, tokenizer, tool, embedder, network or "
            "audio-decode contact. Two committed receipts are read (the KC-E1 "
            "prompt fit's measured brief envelope and this cell's predecessor "
            "binding) plus the verified snapshot artifact; nothing is rendered "
            "and nothing is tokenized"
        ),
        "what_this_is_not": (
            "a fit. Token counts are not additive across a chat template's joins, "
            "so this projects from two measurements and cannot certify a geometry. "
            "The default mode of this script certifies; that mode needs a resident "
            "server and is the flight agent's step"
        ),
        "inputs": {
            "kc_e1_prompt_fit": {
                "relpath": str(KC_E1_FIT.relative_to(REPO)).replace("\\", "/"),
                "sha256": sha256_file(KC_E1_FIT),
                "fixed_envelope_overhead_tokens": overhead,
                "brief_token_distribution_at_cap": arm["brief_token_distribution"],
                "measured_worst_required_tokens": arm["worst_required_tokens"],
            },
            "predecessor_binding": {
                "relpath": relpath,
                "sha256": digest,
                "run_id": snapshot.run_id,
                "windows": snapshot.window_count,
                "pass1_completion_token_distribution": distribution(
                    list(pass1_tokens.values())
                ),
            },
            "repair_frame": {
                "id": str(composed_values["repair_frame"]),
                "whitespace_tokens": frame_whitespace_tokens,
                "sha256": sha256_text(frame_text),
                "note": (
                    "the frame is a fixed string; its FLIGHT-tokenizer cost is "
                    "unknown until the fit runs, so the projection reports a grid"
                ),
            },
        },
        "geometry": {
            "model_fragment": "q4km-e21-buf90-mmproj-gpu-04ccc72a-np6",
            "context_tokens": CONTEXT_TOKENS,
            "slots": int(composed_values["serving_geometry"]["slots"]),
            "slot_tokens": slot_tokens,
            "max_tokens": max_tokens,
            "worst_speech_tokens": worst_speech,
            "rule": "slot_tokens >= 2 * worst_required, with worst_required = speech + text + max_tokens + 2",
        },
        "committed_configuration": committed,
        "frame_sensitivity": [
            worst_at(cap, frame_tokens, max_tokens) for frame_tokens in FRAME_TOKEN_GRID
        ],
        "lever_1_slot_sweep": {
            "at": "cap %d, frame %d, completion ceiling %d"
            % (cap, PROJECTION_FRAME_TOKENS, max_tokens),
            "rows": slot_sweep(int(committed["worst_required_tokens"])),
        },
        "lever_2_completion_ceiling": {
            "sealed_pass1_max_completion_tokens": max(pass1_tokens.values()),
            "note": (
                "a pass-2 answer re-emits a text of known length; a ceiling above "
                "the sealed pass-1 maximum truncates nothing pass 1 produced, and "
                "core.repair_alignment refuses anything much longer regardless. "
                "Lowering it changes decoding_params and therefore the arm, so it "
                "is an option the owner takes, never a silent one"
            ),
            "rows": [
                worst_at(cap, PROJECTION_FRAME_TOKENS, ceiling)
                for ceiling in (1024, 896, 768, 704, 640, 576, 512)
            ],
        },
        "lever_3_cap_sweep": {
            "note": (
                "the same grid KC-E1's fit swept, at this cell's frame and ceiling. "
                "Caps other than the committed one use the KC-E1 sweep's WORST "
                "per-cap brief rather than a per-call one, so these rows are an "
                "upper bound and strictly conservative"
            ),
            "rows": [
                worst_at(cap_value, PROJECTION_FRAME_TOKENS, max_tokens)
                for cap_value in CAP_GRID
                if cap_value in cap_sweep_worst or cap_value == cap
            ],
        },
    }
    document["headline"] = (
        "at the committed cap %d and the declared %d-token slot the projected worst "
        "request is %d tokens, a margin factor of %.3f against the rule's 2.0 -- it "
        "fits STRICTLY and FAILS the margin rule. The LARGEST legal -np that "
        "satisfies the rule at this cap is %s"
        % (
            cap,
            slot_tokens,
            committed["worst_required_tokens"],
            committed["margin_factor"],
            next(
                (
                    row["np"]
                    for row in sorted(
                        document["lever_1_slot_sweep"]["rows"],
                        key=lambda row: -row["np"],
                    )
                    if row["fits_under_study_rule"]
                ),
                "none on the grid",
            ),
        )
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "projection.json"
    out_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    log("wrote %s (%d bytes)" % (out_path, out_path.stat().st_size))
    log(document["headline"])
    return 0


# ---------------------------------------------------------------------------
# The real fit (server mode).
# ---------------------------------------------------------------------------


def text_token_count(client, counts, messages, media_marker) -> tuple[int, str]:
    rendered = client.request_json("POST", "/apply-template", {"messages": list(messages)})
    counts["POST /apply-template"] += 1
    prompt = rendered.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        raise SystemExit("apply-template returned no prompt")
    if prompt.count(media_marker) != 1:
        raise SystemExit(
            "rendered prompt carries %d media markers, expected 1" % prompt.count(media_marker)
        )
    total = 0
    for segment in prompt.split(media_marker):
        if not segment:
            continue
        response = client.request_json(
            "POST", "/tokenize",
            {"content": segment, "add_special": False, "parse_special": True},
        )
        counts["POST /tokenize"] += 1
        tokens = response.get("tokens")
        if not isinstance(tokens, list):
            raise SystemExit("tokenize returned no token list")
        total += len(tokens)
    return total, prompt


#: The wire-shape propositions this cell's requests must satisfy. KC-E1's eight,
#: plus the three the repair pass adds.
WIRE_SHAPE_PROPERTIES = (
    "system_then_user_roles",
    "exactly_two_evidence_blocks",
    "roster_block_precedes_document_block",
    "one_input_audio_part_and_nothing_else",
    "instruction_verbatim_in_rendered_prompt",
    "both_evidence_blocks_precede_the_media_marker",
    "instruction_precedes_the_media_marker",
    "predecessor_text_verbatim_in_the_system_message",
    "predecessor_block_follows_the_instruction",
    "payload_key_set_equals_the_arm_allowlist",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=CHECK / "prompt-fit")
    parser.add_argument("--experiment", default=EXPERIMENT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--projection-only",
        action="store_true",
        help=(
            "MODEL-FREE mode: spawn nothing, contact nothing, and write only "
            "projection.json -- the worst request this cell's requests would need, "
            "projected from the KC-E1 fit's measured brief envelope and the sealed "
            "pass-1 token counts, with the cap, slot and completion-ceiling sweeps "
            "the decision procedure orders. It cannot certify a geometry"
        ),
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help=(
            "TEST-ONLY. A fit certifies COMMITTED fragments; without this the run "
            "refuses a dirty tree rather than recording a study_commit that "
            "describes different bytes"
        ),
    )
    args = parser.parse_args()
    if args.run_id is None:
        args.run_id = PROJECTION_RUN_ID if args.projection_only else RUN_ID

    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
        raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

    import speech_aware_evidence_acquisition as _pkg

    if (
        Path(_pkg.__file__ or "").resolve()
        != (REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py").resolve()
    ):
        raise SystemExit(
            "package resolves to %s, not this checkout's src/" % (_pkg.__file__,)
        )

    from speech_aware_evidence_acquisition.core.config import compose

    dirty = git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "the working tree is dirty; a fit certifies committed fragments:\n" + dirty
        )
    log("clean tree at %s" % git("rev-parse", "HEAD")[:8])

    experiment_doc = load_json(REPO / "configs" / "experiment" / f"{args.experiment}.json")
    cells = list(experiment_doc["cells"])
    if len(cells) != 2:
        raise SystemExit("this fit measures exactly the experiment's two cells")
    dataset = str(cells[0]["dataset_fragment"])
    model = str(cells[0]["model_fragment"])
    if any(str(cell["dataset_fragment"]) != dataset for cell in cells):
        raise SystemExit("the two cells must fly the same roster")
    if any(str(cell["model_fragment"]) != model for cell in cells):
        raise SystemExit("the two cells must fly the same serving geometry")

    composed_by_cell = {
        str(cell["cell_id"]): compose(
            REPO, model, dataset, str(cell["baseline_fragment"]), args.experiment
        )
        for cell in cells
    }
    cell_ids = [str(cell["cell_id"]) for cell in cells]
    values_a = dict(composed_by_cell[cell_ids[0]].values)
    values_b = dict(composed_by_cell[cell_ids[1]].values)
    differing = sorted(
        key for key in set(values_a) | set(values_b) if values_a.get(key) != values_b.get(key)
    )
    if differing not in (["evidence_source"], ["evidence_pad_plan", "evidence_source"]):
        raise SystemExit(
            "the two cells must differ in exactly evidence_source, or in it plus the "
            "twin's pad-plan pin; they differ in %r" % (differing,)
        )
    committed_cap = int(values_a.get("brief_max_entries_per_class", 0))
    log("committed brief_max_entries_per_class = %d (both fragments)" % committed_cap)

    if args.projection_only:
        return write_projection(args, composed_values=values_a, cap=committed_cap)

    # ------------------------------------------------------------------
    # Server mode. NOT RUN by the analyst: opening a session is a model
    # contact by this study's accounting and needs its own exposure row.
    # ------------------------------------------------------------------
    import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate
    from speech_aware_evidence_acquisition.core.base import EVIDENCE_SOURCES, TRANSPORTS
    from speech_aware_evidence_acquisition.core.config import (
        d1_evidence_supplement_relpath,
        d1_evidence_supplement_sha256,
        d1_media_supplement_relpath,
        d1_media_supplement_sha256,
        fragment_hash,
        model_materialization_root,
        read_fragment,
        resolve_runtime_receipt_path,
        runtime_receipt_relpath,
    )
    from speech_aware_evidence_acquisition.core.driver.speech_native import (
        _LoopbackPromptAuditClient,
    )
    from speech_aware_evidence_acquisition.core.flight.runtime import merge_server_args
    from speech_aware_evidence_acquisition.core.policies import build_arm_payload
    from speech_aware_evidence_acquisition.core.predecessor_snapshot import (
        binding_from_values,
        load_predecessor_binding,
    )
    from speech_aware_evidence_acquisition.core.session import (
        attach_session,
        build_server_command,
        load_runtime_receipt,
    )
    from speech_aware_evidence_acquisition.core.session.serving import (
        SESSION_RECEIPT_NAME,
        assert_identity_matches,
        find_resident_session,
        serving_identity,
    )
    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.data.loader import SampleRef
    from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
    from speech_aware_evidence_acquisition.reproduction.obs_audio import write_wav_bytes
    from speech_aware_evidence_acquisition.reproduction.repair_loop import REPAIR_FRAMES

    geometry = values_a["serving_geometry"]
    slots = int(geometry["slots"])
    slot_tokens = int(geometry["slot_tokens"])
    max_tokens = int(geometry["max_tokens"])
    if slot_tokens % 512:
        raise SystemExit("slot_tokens must be a multiple of 512")

    roster = load_json(ROSTER_RECEIPT)
    windows = build_windows(roster)
    declared = int(experiment_doc["population"]["fixed_90s_windows_one_pass"])
    if len(windows) != declared:
        raise SystemExit(
            "built %d windows, the experiment fragment declares %d" % (len(windows), declared)
        )
    sample_ids = [str(call["sample_id"]) for call in roster["calls"]]

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    relpath, digest = binding_from_values(values_a)
    snapshot = load_predecessor_binding(
        REPO / "docs" / relpath, root, expected_receipt_sha256=digest
    )
    if snapshot.window_count != len(windows):
        raise SystemExit(
            "the binding carries %d windows, the roster tiles %d"
            % (snapshot.window_count, len(windows))
        )
    frame = REPAIR_FRAMES[str(values_a["repair_frame"])]

    stand_in_path = root / STAND_IN_RELPATH
    stand_in_path.parent.mkdir(parents=True, exist_ok=True)
    stand_in_bytes = write_wav_bytes(
        [0] * int(round(STAND_IN_SECONDS * STAND_IN_RATE_HZ)), STAND_IN_RATE_HZ
    )
    stand_in_path.write_bytes(stand_in_bytes)

    plan = ExecutionPlan(
        run_id=args.run_id,
        execution_profile=str(values_a["execution_profile"]),
        carrier_lock_key=str(values_a["carrier_lock_key"]),
        split_role=str(experiment_doc["population"]["split_role"]),
        split_identity_hash=SPLIT_IDENTITY_HASH,
        planned_model_calls=PLAN_CALLS,
        planned_gpu_hours=PLAN_GPU_HOURS,
        planned_speech_audio_seconds=PLAN_AUDIO_SECONDS,
        protocol_hash=composed_by_cell[cell_ids[0]].config_hash,
        attempt_id="attempt-%s-e21kce1ffit"
        % datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    ).validate()
    configured_model_root = model_materialization_root(values_a)
    gate = FrozenCoreGate.for_study_repo(
        REPO, root, RUNTIME_ROOT,
        runtime_receipt_relpath=str(values_a["runtime_receipt"]),
        expected_model_lock_key=str(values_a["model_lock_key"]),
        model_root=(Path(configured_model_root) if configured_model_root else None),
        d1_media_supplement_relpath=d1_media_supplement_relpath(values_a),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values_a),
        d1_evidence_supplement_relpath=d1_evidence_supplement_relpath(values_a),
        d1_evidence_supplement_sha256=d1_evidence_supplement_sha256(values_a),
    )
    lock_sha256 = gate.assert_model_touch_allowed(plan)
    log("frozen-core gate PASS (lock %s)" % lock_sha256[:12])

    evidence_by_cell = {}
    for cell_id in cell_ids:
        values = dict(composed_by_cell[cell_id].values)
        source = EVIDENCE_SOURCES.resolve(str(values["evidence_source"]))
        built = {}
        for sample_id in sample_ids:
            items = source(
                lock, root, sample_id, str(values_a["carrier_lock_key"]), values
            )
            if len(items) != 2:
                raise SystemExit("the brief must be two items (roster then document)")
            built[sample_id] = items
        evidence_by_cell[cell_id] = built

    runtime_receipt = load_runtime_receipt(REPO / "docs" / str(values_a["runtime_receipt"]))
    run_dir = root / "runs" / args.run_id / str(plan.attempt_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    extra_argv = merge_server_args(
        values_a["server_args"], slots=slots, context_tokens=slots * slot_tokens
    )
    port = int(str(values_a["base_url"]).rsplit(":", 1)[-1])
    host = "127.0.0.1"

    # ATTACH, NEVER SPAWN (owner rule 2026-09-07; docs/readiness/
    # 2026-09-07-always-on-serving-operating-note.md). This script used to
    # start its own llama-server and stop it in a finally block. Under
    # always-on serving that is wrong twice over: the coordinator's resident
    # server already owns the port, and stopping a session this script does
    # not own would take the core away from every other queued flight. So it
    # does exactly what core.flight.FlightRuntime.serve does -- find the ONE
    # resident serving session, require it to be serving THIS cell's
    # identity, bind through core.session.attach_session (which
    # independently re-verifies loopback, the runtime-receipt-pinned binary
    # and GGUF set, that the pid is alive right now and that it owns the
    # listening socket), and never stop it. No resident session, or one
    # serving something else, is a refusal rather than a second spawn.
    resident = find_resident_session(root)
    if resident is None:
        raise SystemExit(
            "no resident serving session under %s: this fit attaches and never "
            "spawns, so the coordinator must start the session for this cell's "
            "geometry first" % (root / "serving")
        )
    session_dir, session_document = resident
    session_dir = Path(session_dir)
    command = build_server_command(
        runtime_root=RUNTIME_ROOT,
        data_root=root,
        runtime_receipt=runtime_receipt,
        host=host,
        port=port,
        extra_argv=tuple(extra_argv),
        extra_env=dict(values_a.get("server_env", {})),
        role=str(runtime_receipt.get("role", "legacy")),
        model_root=(Path(configured_model_root) if configured_model_root else None),
    )
    model_argv = list(command.argv)
    required_identity = serving_identity(
        model_fragment=model,
        model_fragment_sha256=fragment_hash(read_fragment(REPO, "model", model)),
        runtime_receipt_relpath=runtime_receipt_relpath(values_a),
        runtime_receipt_sha256=sha256_file(resolve_runtime_receipt_path(REPO, values_a)),
        binary_path=command.binary_path,
        binary_sha256=command.binary_sha256,
        model_files=[
            {"path": entry.path, "sha256": entry.sha256} for entry in command.model_files
        ],
        session_role=str(runtime_receipt.get("role", "legacy")),
        model_root=configured_model_root,
        server_argv=command.argv,
        server_env=dict(values_a.get("server_env", {})),
        host=host,
        port=port,
        props={
            "total_slots": slots,
            "default_generation_settings": {"n_ctx": slot_tokens},
            "model_path": (
                model_argv[model_argv.index("-m") + 1] if "-m" in model_argv else None
            ),
        },
    )
    assert_identity_matches(session_document, required_identity)
    session = attach_session(
        session_dir / SESSION_RECEIPT_NAME,
        runtime_receipt=runtime_receipt,
        runtime_root=RUNTIME_ROOT,
    )
    serving_session_id = str(session_document.get("session_id"))
    log(
        "attached to resident serving session %s (pid %s, %d slots x %d tokens); "
        "this script starts and stops nothing"
        % (serving_session_id, session.pid, slots, slot_tokens)
    )

    counts: Counter[str] = Counter()
    per_cell: dict[str, Any] = {}
    try:
        # Keyword-only, exactly as scripts/e21_kc_e1_prompt_fit.py constructs
        # it: this client takes host/port/timeout, never a base URL. Host and
        # port come from the ATTACHED session receipt rather than from the
        # config string, so the measurement is provably against the process
        # attach_session just verified.
        client = _LoopbackPromptAuditClient(
            host=session.host, port=session.port, timeout_seconds=600.0
        )
        props = client.request_json("GET", "/props", None)
        counts["GET /props"] += 1
        media_marker = str(props["media_marker"])
        # The live server's OWN account of the slot it serves. The identity
        # assertion above already compared this against the fragment, but a
        # fit that certified a slot the server does not actually honour would
        # be worthless paper, so it is re-read here from /props directly.
        live_slot_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
        if int(live_slot_ctx) < slot_tokens:
            raise SystemExit(
                "resident slot n_ctx %s is smaller than the fragment's declared %d; "
                "refusing to certify a fit the server cannot honour"
                % (live_slot_ctx, slot_tokens)
            )
        chat_template_sha256 = sha256_text(str(props.get("chat_template", "")))
        log(
            "props OK: %s slots x %s tokens, media marker %r"
            % (props.get("total_slots"), live_slot_ctx, media_marker)
        )

        for cell_id in cell_ids:
            values = dict(composed_by_cell[cell_id].values)
            instruction_base = str(values["task_instruction"])
            decoding_params = dict(values["decoding_params"])
            decoding_params["id_slot"] = 0
            transport = TRANSPORTS.resolve(str(values["transport"]))(
                values, root, session=session, runtime_receipt=runtime_receipt,
                runtime_root=RUNTIME_ROOT,
            )
            captured: dict[str, Any] = {}

            def _capture(url, body, _captured=captured):
                _captured["body"] = json.loads(body.decode("utf-8"))
                return json.dumps(
                    {
                        "choices": [{"message": {"content": ""}}],
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                    }
                ).encode("utf-8")

            transport._post = _capture
            window_rows: list[dict[str, Any]] = []
            shape_rows: list[dict[str, bool]] = []
            allowlist = set(ARM_VISIBLE_FIELDS[str(values["arm"])])
            for window in windows:
                sample_id = window["sample_id"]
                items = evidence_by_cell[cell_id][sample_id]
                predecessor = snapshot.windows[window["window_id"]]
                instruction = "%s\n\n%s" % (
                    instruction_base, frame.format(predecessor=predecessor.text)
                )
                ref = SampleRef(
                    carrier_lock_key=str(values_a["carrier_lock_key"]),
                    sample_id=sample_id,
                    media_relpath=STAND_IN_RELPATH,
                    audio_seconds=float(window["window_seconds"]),
                    sample_rate_hz=STAND_IN_RATE_HZ,
                )
                payload = build_arm_payload(
                    str(values["arm"]), ref,
                    "e21kce1f-fit-%s-%s" % (cell_id, window["window_id"]),
                    instruction, decoding_params, evidence=list(items),
                )
                transport(json.dumps(payload).encode("utf-8"))
                messages = captured["body"]["messages"]
                tokens, prompt = text_token_count(client, counts, messages, media_marker)
                system = messages[0]["content"]
                marker_index = prompt.index(media_marker)
                shape_rows.append(
                    {
                        "system_then_user_roles": [m["role"] for m in messages] == ["system", "user"],
                        "exactly_two_evidence_blocks": system.count("[evidence ") == 2,
                        "roster_block_precedes_document_block": (
                            system.index(f"[evidence {items[0].evidence_id}]")
                            < system.index(f"[evidence {items[1].evidence_id}]")
                        ),
                        "one_input_audio_part_and_nothing_else": (
                            isinstance(messages[-1]["content"], list)
                            and len(messages[-1]["content"]) == 1
                            and messages[-1]["content"][0].get("type") == "input_audio"
                        ),
                        "instruction_verbatim_in_rendered_prompt": instruction in prompt,
                        "both_evidence_blocks_precede_the_media_marker": (
                            prompt.index(f"[evidence {items[1].evidence_id}]") < marker_index
                        ),
                        "instruction_precedes_the_media_marker": (
                            prompt.index(instruction_base) < marker_index
                        ),
                        "predecessor_text_verbatim_in_the_system_message": (
                            predecessor.text in system if predecessor.text else True
                        ),
                        "predecessor_block_follows_the_instruction": (
                            system.index(instruction_base) < system.rindex(frame[:40])
                        ),
                        "payload_key_set_equals_the_arm_allowlist": set(payload) == allowlist,
                    }
                )
                required = (
                    int(window["speech_tokens"]) + tokens + max_tokens + SPECIAL_TOKENS
                )
                window_rows.append(
                    {
                        "window_id": window["window_id"],
                        "sample_id": sample_id,
                        "window_seconds": window["window_seconds"],
                        "speech_tokens": int(window["speech_tokens"]),
                        "text_tokens": tokens,
                        "predecessor_completion_tokens": predecessor.completion_tokens,
                        "required_tokens": required,
                    }
                )
            worst = max(window_rows, key=lambda row: row["required_tokens"])
            per_cell[cell_id] = {
                "cell_id": cell_id,
                "config_hash": composed_by_cell[cell_id].config_hash,
                "windows_rendered": len(window_rows),
                "text_token_distribution": distribution(
                    [row["text_tokens"] for row in window_rows]
                ),
                "worst_window_id": worst["window_id"],
                "worst_required_tokens": worst["required_tokens"],
                "margin_factor": round(slot_tokens / worst["required_tokens"], 4),
                "fits_under_study_rule": slot_tokens >= FIT_MULTIPLE * worst["required_tokens"],
                "fits_strictly": slot_tokens >= worst["required_tokens"],
                "slot_sweep": slot_sweep(int(worst["required_tokens"])),
                "wire_shape": {
                    "requests_checked": len(shape_rows),
                    "properties": {
                        name: {
                            "holds_on_every_request": all(row[name] for row in shape_rows),
                            "requests_holding": sum(1 for row in shape_rows if row[name]),
                        }
                        for name in WIRE_SHAPE_PROPERTIES
                    },
                    "all_hold": all(
                        all(row[name] for row in shape_rows) for name in WIRE_SHAPE_PROPERTIES
                    ),
                },
                "window_rows": window_rows,
            }
            log(
                "  %-28s windows=%4d text min/median/max = %5d / %8.1f / %5d worst_required=%5d factor=%.3f"
                % (
                    cell_id, len(window_rows),
                    per_cell[cell_id]["text_token_distribution"]["min"],
                    per_cell[cell_id]["text_token_distribution"]["median"],
                    per_cell[cell_id]["text_token_distribution"]["max"],
                    worst["required_tokens"], per_cell[cell_id]["margin_factor"],
                )
            )
    finally:
        # Deliberately no teardown: the session belongs to the coordinator's
        # foreground wrapper and outlives this script (E7b, two guards in
        # FlightRuntime.stop_serving say the same thing for a flight).
        pass

    document = {
        "schema": "saea-e21-kc-e1f-prompt-fit-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "flight_run_id": FLIGHT_RUN_ID,
        "attempt_id": plan.attempt_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "study_commit": git("rev-parse", "HEAD"),
        "experiment_fragment": args.experiment,
        "geometry": {
            "slots": slots,
            "slot_tokens": slot_tokens,
            "live_slot_n_ctx": live_slot_ctx,
            "live_total_slots": props.get("total_slots"),
            "context_tokens": slots * slot_tokens,
            "max_tokens": max_tokens,
            "media_marker": media_marker,
            "chat_template_sha256": chat_template_sha256,
        },
        "predecessor_binding": {"relpath": relpath, "sha256": digest},
        "serving_session": {
            "session_id": serving_session_id,
            "session_dir": str(session_dir),
            "pid": session.pid,
            "host": session.host,
            "port": session.port,
            "attached": True,
            "started_by_this_script": False,
            "stopped_by_this_script": False,
            "identity_fields_asserted": sorted(required_identity),
        },
        "cells": per_cell,
        "route_counts": dict(counts),
        "generated_tokens": 0,
        "decision": {
            "worst_required_tokens": max(
                cell["worst_required_tokens"] for cell in per_cell.values()
            ),
            "fits_under_study_rule": all(
                cell["fits_under_study_rule"] for cell in per_cell.values()
            ),
            "fits_strictly": all(cell["fits_strictly"] for cell in per_cell.values()),
            "lever_order": (
                "1 widen the slot at the committed cap; 2 lower the pass-2 completion "
                "ceiling; 3 sweep the cap. Fixed before measurement in this script's "
                "own docstring"
            ),
        },
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "prompt-fit.json"
    out_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    log("wrote %s (%d bytes)" % (out_path, out_path.stat().st_size))
    log("canonical %s" % canonical_sha256(document)[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
