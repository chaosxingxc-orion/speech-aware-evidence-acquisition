#!/usr/bin/env python3
"""Prompt fit for the Earnings-21 draft-then-refresh cells (DR-1).

Sibling of ``scripts/e21_kc_e1f_prompt_fit.py`` and the same measurement in
substance: render every request the flight would send, through the REAL
transport on the REAL composed config, count it on the FLIGHT tokenizer with
``POST /apply-template`` + ``POST /tokenize`` at zero generated tokens, and
certify the worst request against the declared slot under this study's own rule
``slot_tokens >= 2 * worst_required``.

WHAT IS DIFFERENT FROM THE KC-E1f FIT, AND WHY IT MATTERS
----------------------------------------------------------
Two things, and both make this cell CHEAPER on the wire than KC-E1f's.

1. **There is no brief.** DR-1 supplies no external knowledge at all: the arm
   is ``bare-core``, the payload carries the comparator's own D2-frozen field
   set, and the only text beyond the instruction is the draft. So KC-E1f's
   lever 3 -- sweep the brief cap -- does not exist here, and this script says
   so rather than leaving a reader to wonder why a lever is missing.
2. **THREE cells, and two different drafts.** DR-1c and DR-1f carry the
   stitched unit draft (``saea-e21-unit-draft-majority-overlap-v1``, max 596
   sealed flight tokens); DR-1s carries the comparator's own sealed
   hypothesis (max 445). Both bindings are read, both worst requests are
   projected, and the fit certifies the geometry against the LARGER.

The per-window envelope still varies within a call by construction -- each
window carries its own draft -- so the worst request is a per-WINDOW maximum
over 1,593 rows per cell, exactly as KC-E1f's was.

TWO MODES
---------
``--projection-only`` is MODEL-FREE and spawns nothing. It answers the question
the flight agent needs answered before booking a GPU window at all, and it
projects from TWO measurements rather than from a characters-per-token guess:

* the comparator's OWN per-window prompt-token counts, measured by the flight
  server on the flight tokenizer and pinned in
  ``docs/receipts/e21-predecessor-full44-direct-baseline-v2.json`` (min 75,
  median and max 1,232 for a full 90-second window). That figure IS
  ``speech + system template + the comparator's instruction``, so it needs no
  reconstruction;
* each binding's per-window draft token counts, likewise sealed.

What it cannot measure is the ADDED envelope: DR-1's instruction contains the
comparator's whole instruction verbatim as its last three sentences, plus one
leading sentence, plus the frame. Only the tokenizer knows what those cost, so
the projection sweeps a grid (:data:`ADDED_ENVELOPE_GRID`) and reports the
whole ladder including the point at which the np6 margin falls under 2.0.

The default mode is the real fit and REQUIRES a resident server. It is the
flight agent's step, not the analyst's: it opens a session, so it is a model
contact by this study's accounting and needs its own registered exposure row.

THE DECISION PROCEDURE, FIXED HERE BEFORE ANY MEASUREMENT
----------------------------------------------------------
So that a chosen geometry can never be reverse-engineered from a result, the
levers are ordered in advance and the first one that satisfies the margin rule
is taken:

1. **Widen the slot.** Widening the slot changes no byte of any request --
   only how many of them share the 36,864-token context -- so it is a serving
   decision, and the LARGEST ``-np`` (that is, the smallest slot, so the least
   parallelism given up) that still satisfies the rule is reported for the
   owner. Only a geometry whose context divides evenly into a 512-multiple slot
   counts.
2. **Lower the pass-2 completion ceiling.** A pass-2 answer here re-emits a
   text whose length is known: the largest sealed draft is 596 flight tokens
   and the comparator's own largest window completion was 445, so a ceiling
   well above either truncates nothing pass 1 produced. This changes
   ``decoding_params`` and therefore the arm, so it is reported as an option
   and never taken silently.
3. **There is no third lever.** KC-E1f's was the brief cap, and DR-1 has no
   brief. If levers 1 and 2 both fail, the cell does not fly at this geometry
   and the owner is told so.

Usage::

    python scripts/e21_dr1_prompt_fit.py --projection-only --out-dir <dir>
    python scripts/e21_dr1_prompt_fit.py --out-dir <dir>   # server; flight agent
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
    / "2026-09-09-e21-draft-then-refresh-dr1-v1"
)
ROSTER_RECEIPT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-roster/flight-roster-receipt.json"
)

EXPERIMENT = "e21-draft-then-refresh-dr1-v1"
RUN_ID = "SAEA-E21-DR1-PROMPT-FIT-V1"
PROJECTION_RUN_ID = "SAEA-E21-MF-DR1-PREP-V1"
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
#: the context divides evenly and the resulting slot is a multiple of 512.
#: ``-np 5`` is on the grid precisely so the receipt records that it is illegal
#: at a 36,864-token context (7,372.8 tokens per slot).
SLOT_SWEEP_NP = (2, 3, 4, 5, 6, 8, 9, 12)
#: The completion ceilings lever 2 would consider, largest (the committed one)
#: first.
COMPLETION_CEILING_GRID = (1024, 896, 768, 704, 640, 576, 512)

#: How many FLIGHT tokens DR-1's request adds to the comparator's own measured
#: per-window prompt: one leading instruction sentence (38 whitespace tokens)
#: plus the frame's fixed wording (38 whitespace tokens plus its quotes and
#: newlines). Only the tokenizer knows the truth, so the projection reports the
#: whole grid and the fit measures it.
ADDED_ENVELOPE_GRID = (60, 80, 100, 120, 160, 200, 240, 280)
PROJECTION_ADDED_ENVELOPE = 100

#: Nominal for the server mode: nothing decodes, but ``contracts.ExecutionPlan``
#: still requires a positive budget and the ceiling is run-cumulative.
PLAN_CALLS = 2
PLAN_AUDIO_SECONDS = 2
PLAN_GPU_HOURS = 0.4

STAND_IN_RELPATH = "derived/prompt-fit/e21-dr1/silence-100ms-16k.wav"
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
    this receipt, a row of either binding and a row of the paired read all name
    the same unit."""

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


def write_projection(args, *, composed_by_cell, cells) -> int:
    from speech_aware_evidence_acquisition.core.predecessor_snapshot import (  # noqa: PLC0415
        binding_from_values,
        load_predecessor_binding,
    )
    from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: PLC0415
    from speech_aware_evidence_acquisition.reproduction.repair_loop import (  # noqa: PLC0415
        REPAIR_FRAMES,
    )

    root = data_root()
    bindings: dict[str, Any] = {}
    projections: dict[str, Any] = {}
    for cell in cells:
        cell_id = str(cell["cell_id"])
        values = dict(composed_by_cell[cell_id].values)
        relpath, digest = binding_from_values(values)
        if relpath not in bindings:
            snapshot = load_predecessor_binding(
                REPO / "docs" / relpath, root, expected_receipt_sha256=digest
            )
            if snapshot.window_count != 1593:
                raise SystemExit(
                    "binding %s carries %d windows, not 1,593"
                    % (relpath, snapshot.window_count)
                )
            bindings[relpath] = {
                "relpath": relpath,
                "sha256": digest,
                "run_id": snapshot.run_id,
                "attempt_id": snapshot.attempt_id,
                "windows": snapshot.window_count,
                "draft_tokens": {
                    window_id: int(window.completion_tokens or 0)
                    for window_id, window in snapshot.windows.items()
                },
                "comparator_prompt_tokens": {
                    window_id: int(window.prompt_tokens or 0)
                    for window_id, window in snapshot.windows.items()
                },
                "window_seconds": {
                    window_id: float(window.audio_seconds)
                    for window_id, window in snapshot.windows.items()
                },
            }
        bound = bindings[relpath]

        slot_tokens = int(values["serving_geometry"]["slot_tokens"])
        committed_ceiling = int(values["serving_geometry"]["max_tokens"])
        frame_text = REPAIR_FRAMES[str(values["repair_frame"])]
        instruction = str(values["task_instruction"])

        def worst_at(added_envelope: int, ceiling: int) -> dict[str, Any]:
            worst_required = 0
            worst_window = None
            required_all = []
            for window_id, draft in bound["draft_tokens"].items():
                # The comparator's own measured prompt for this window already
                # IS speech + template + its instruction, so nothing is
                # reconstructed: the projection adds only what DR-1 adds.
                required = (
                    bound["comparator_prompt_tokens"][window_id]
                    + added_envelope
                    + draft
                    + ceiling
                    + SPECIAL_TOKENS
                )
                required_all.append(required)
                if required > worst_required:
                    worst_required, worst_window = required, window_id
            return {
                "added_envelope_tokens": added_envelope,
                "completion_ceiling": ceiling,
                "worst_required_tokens": worst_required,
                "worst_window_id": worst_window,
                "margin_factor": round(slot_tokens / worst_required, 4),
                "fits_under_study_rule": slot_tokens >= FIT_MULTIPLE * worst_required,
                "fits_strictly": slot_tokens >= worst_required,
                "required_token_distribution": distribution(required_all),
            }

        committed = worst_at(PROJECTION_ADDED_ENVELOPE, committed_ceiling)
        projections[cell_id] = {
            "cell_id": cell_id,
            "config_hash": composed_by_cell[cell_id].config_hash,
            "binding_relpath": relpath,
            "model_fragment": str(cell["model_fragment"]),
            "slot_tokens": slot_tokens,
            "committed_completion_ceiling": committed_ceiling,
            "draft_token_distribution": distribution(list(bound["draft_tokens"].values())),
            "instruction_whitespace_tokens": len(instruction.split()),
            "instruction_sha256": sha256_text(instruction),
            "frame_id": str(values["repair_frame"]),
            "frame_whitespace_tokens": len(
                frame_text.replace("{predecessor}", "").split()
            ),
            "frame_sha256": sha256_text(frame_text),
            "committed_configuration": committed,
            "added_envelope_sensitivity": [
                worst_at(added, committed_ceiling) for added in ADDED_ENVELOPE_GRID
            ],
            "lever_1_slot_sweep": slot_sweep(int(committed["worst_required_tokens"])),
            "lever_2_completion_ceiling": [
                worst_at(PROJECTION_ADDED_ENVELOPE, ceiling)
                for ceiling in COMPLETION_CEILING_GRID
            ],
        }

    worst_cell = max(
        projections.values(),
        key=lambda row: row["committed_configuration"]["worst_required_tokens"],
    )
    # The added-envelope point at which the DECLARED geometry stops satisfying
    # the rule -- reported so the fit's own measurement can be read against a
    # threshold that was written down first.
    breaks_at = next(
        (
            row["added_envelope_tokens"]
            for row in worst_cell["added_envelope_sensitivity"]
            if not row["fits_under_study_rule"]
        ),
        None,
    )
    document = {
        "schema": "saea-e21-dr1-prompt-fit-projection-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "experiment_fragment": args.experiment,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "study_commit": git("rev-parse", "HEAD"),
        "zero_contact": (
            "no model, GPU, server, socket, tokenizer, tool, embedder, network or "
            "audio-decode contact. Two committed binding receipts are read plus their "
            "hash-verified snapshot artifacts; nothing is rendered and nothing is "
            "tokenized"
        ),
        "what_this_is_not": (
            "a fit. Token counts are not additive across a chat template's joins, so "
            "this projects from two measurements and cannot certify a geometry. The "
            "default mode of this script certifies; that mode needs a resident server "
            "and is the flight agent's step"
        ),
        "geometry": {
            "context_tokens": CONTEXT_TOKENS,
            "rule": (
                "slot_tokens >= 2 * worst_required, with worst_required = the "
                "comparator's own measured per-window prompt tokens + the added DR-1 "
                "envelope + the draft + max_tokens + 2"
            ),
        },
        "bindings": {
            relpath: {
                key: value
                for key, value in bound.items()
                if key not in ("draft_tokens", "comparator_prompt_tokens", "window_seconds")
            }
            | {
                "draft_token_distribution": distribution(
                    list(bound["draft_tokens"].values())
                ),
                "comparator_prompt_token_distribution": distribution(
                    list(bound["comparator_prompt_tokens"].values())
                ),
            }
            for relpath, bound in bindings.items()
        },
        "cells": projections,
        "lever_order": (
            "1 widen the slot; 2 lower the pass-2 completion ceiling; 3 does not exist "
            "-- KC-E1f's third lever was the brief cap and DR-1 carries no brief. Fixed "
            "before measurement in this script's own docstring"
        ),
        "authorizes": "nothing. No contact, no geometry decision, no flight.",
    }
    document["headline"] = (
        "worst cell %s: at an assumed added envelope of %d tokens the projected worst "
        "request is %d tokens against the declared %d-token slot, a margin factor of "
        "%.3f against the rule's 2.0 (%s). The declared geometry stops satisfying the "
        "rule once the added envelope reaches %s tokens. The largest legal -np that "
        "satisfies the rule is %s. A SERVER fit decides."
        % (
            worst_cell["cell_id"],
            PROJECTION_ADDED_ENVELOPE,
            worst_cell["committed_configuration"]["worst_required_tokens"],
            worst_cell["slot_tokens"],
            worst_cell["committed_configuration"]["margin_factor"],
            "PASSES"
            if worst_cell["committed_configuration"]["fits_under_study_rule"]
            else "FAILS",
            breaks_at if breaks_at is not None else "beyond this grid",
            next(
                (
                    row["np"]
                    for row in sorted(
                        worst_cell["lever_1_slot_sweep"], key=lambda row: -row["np"]
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


#: The wire-shape propositions this cell's requests must satisfy. KC-E1f's
#: list minus the three evidence ones -- DR-1 is ``bare-core`` and carries no
#: evidence block at all, which is itself a property worth asserting rather
#: than assuming.
WIRE_SHAPE_PROPERTIES = (
    "system_then_user_roles",
    "no_evidence_block_anywhere",
    "one_input_audio_part_and_nothing_else",
    "instruction_verbatim_in_rendered_prompt",
    "instruction_precedes_the_media_marker",
    "draft_text_verbatim_in_the_system_message",
    "draft_block_follows_the_instruction",
    "payload_key_set_equals_the_bare_core_allowlist",
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
            "projection.json -- the worst request this family's requests would need, "
            "projected from the comparator's own sealed per-window prompt tokens and "
            "each binding's sealed draft tokens, with the added-envelope, slot and "
            "completion-ceiling sweeps the decision procedure orders. It cannot "
            "certify a geometry"
        ),
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help=(
            "TEST-ONLY. A fit certifies COMMITTED fragments; without this the run "
            "refuses a dirty tree rather than recording a study_commit that describes "
            "different bytes"
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
    if len(cells) != 3:
        raise SystemExit("this fit measures exactly the experiment's three cells")
    dataset = str(cells[0]["dataset_fragment"])
    model = str(cells[0]["model_fragment"])
    if any(str(cell["dataset_fragment"]) != dataset for cell in cells):
        raise SystemExit("the three cells must fly the same roster")
    if any(str(cell["model_fragment"]) != model for cell in cells):
        raise SystemExit("the three cells must fly the same serving geometry")

    composed_by_cell = {
        str(cell["cell_id"]): compose(
            REPO, model, dataset, str(cell["baseline_fragment"]), args.experiment
        )
        for cell in cells
    }
    cell_ids = [str(cell["cell_id"]) for cell in cells]

    # The one-factor claim, re-asserted on the COMPOSED documents rather than
    # on the fragments, because a fit renders composed values.
    def differing(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[str]:
        keys = set(left) | set(right)
        return sorted(
            key
            for key in keys
            if left.get(key) != right.get(key) and key != "what_this_is"
        )

    values_by_cell = {cell_id: dict(composed_by_cell[cell_id].values) for cell_id in cell_ids}
    c_vs_f = differing(values_by_cell[cell_ids[0]], values_by_cell[cell_ids[1]])
    c_vs_s = differing(values_by_cell[cell_ids[0]], values_by_cell[cell_ids[2]])
    if c_vs_f != ["response_postprocessor", "response_postprocessor_params"]:
        raise SystemExit(
            "DR-1c and DR-1f must differ in exactly the delivery rule and its "
            "parameters; they differ in %r" % (c_vs_f,)
        )
    if c_vs_s != ["predecessor_snapshot"]:
        raise SystemExit(
            "DR-1c and DR-1s must differ in exactly predecessor_snapshot; they differ "
            "in %r" % (c_vs_s,)
        )
    log("one factor holds on the composed documents: %r and %r" % (c_vs_f, c_vs_s))

    if args.projection_only:
        return write_projection(args, composed_by_cell=composed_by_cell, cells=cells)

    # ------------------------------------------------------------------
    # Server mode. NOT RUN by the analyst: opening a session is a model
    # contact by this study's accounting and needs its own exposure row.
    # ------------------------------------------------------------------
    import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate
    from speech_aware_evidence_acquisition.core.base import TRANSPORTS
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
    from speech_aware_evidence_acquisition.data.lock import data_root
    from speech_aware_evidence_acquisition.data.loader import SampleRef
    from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
    from speech_aware_evidence_acquisition.reproduction.obs_audio import write_wav_bytes
    from speech_aware_evidence_acquisition.reproduction.repair_loop import REPAIR_FRAMES

    values_a = values_by_cell[cell_ids[0]]
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
            "built %d windows, the experiment fragment declares %d"
            % (len(windows), declared)
        )

    root = data_root()
    snapshots: dict[str, Any] = {}
    for cell_id in cell_ids:
        relpath, digest = binding_from_values(values_by_cell[cell_id])
        if relpath not in snapshots:
            snapshots[relpath] = load_predecessor_binding(
                REPO / "docs" / relpath, root, expected_receipt_sha256=digest
            )
        if snapshots[relpath].window_count != len(windows):
            raise SystemExit(
                "binding %s carries %d windows, the roster tiles %d"
                % (relpath, snapshots[relpath].window_count, len(windows))
            )

    stand_in_path = root / STAND_IN_RELPATH
    stand_in_path.parent.mkdir(parents=True, exist_ok=True)
    stand_in_path.write_bytes(
        write_wav_bytes(
            [0] * int(round(STAND_IN_SECONDS * STAND_IN_RATE_HZ)), STAND_IN_RATE_HZ
        )
    )

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
        attempt_id="attempt-%s-e21dr1fit"
        % datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    ).validate()
    configured_model_root = model_materialization_root(values_a)
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        RUNTIME_ROOT,
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

    runtime_receipt = load_runtime_receipt(REPO / "docs" / str(values_a["runtime_receipt"]))
    extra_argv = merge_server_args(
        values_a["server_args"], slots=slots, context_tokens=slots * slot_tokens
    )
    port = int(str(values_a["base_url"]).rsplit(":", 1)[-1])
    host = "127.0.0.1"

    # ATTACH, NEVER SPAWN (owner rule 2026-09-07). The coordinator's resident
    # server already owns the port, and stopping a session this script does not
    # own would take the core away from every other queued flight.
    resident = find_resident_session(root)
    if resident is None:
        raise SystemExit(
            "no resident serving session under %s: this fit attaches and never spawns, "
            "so the coordinator must start the session for this cell's geometry first"
            % (root / "serving")
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
        "attached to resident serving session %s (pid %s, %d slots x %d tokens); this "
        "script starts and stops nothing"
        % (serving_session_id, session.pid, slots, slot_tokens)
    )

    counts: Counter[str] = Counter()
    per_cell: dict[str, Any] = {}
    client = _LoopbackPromptAuditClient(
        host=session.host, port=session.port, timeout_seconds=600.0
    )
    props = client.request_json("GET", "/props", None)
    counts["GET /props"] += 1
    media_marker = str(props["media_marker"])
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
        values = values_by_cell[cell_id]
        relpath, _digest = binding_from_values(values)
        snapshot = snapshots[relpath]
        frame = REPAIR_FRAMES[str(values["repair_frame"])]
        instruction_base = str(values["task_instruction"])
        decoding_params = dict(values["decoding_params"])
        decoding_params["id_slot"] = 0
        transport = TRANSPORTS.resolve(str(values["transport"]))(
            values,
            root,
            session=session,
            runtime_receipt=runtime_receipt,
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
            draft = snapshot.windows[window["window_id"]]
            instruction = "%s\n\n%s" % (
                instruction_base,
                frame.format(predecessor=draft.text),
            )
            ref = SampleRef(
                carrier_lock_key=str(values["carrier_lock_key"]),
                sample_id=window["sample_id"],
                media_relpath=STAND_IN_RELPATH,
                audio_seconds=float(window["window_seconds"]),
                sample_rate_hz=STAND_IN_RATE_HZ,
            )
            payload = build_arm_payload(
                str(values["arm"]),
                ref,
                "e21dr1-fit-%s-%s" % (cell_id, window["window_id"]),
                instruction,
                decoding_params,
            )
            transport(json.dumps(payload).encode("utf-8"))
            messages = captured["body"]["messages"]
            tokens, prompt = text_token_count(client, counts, messages, media_marker)
            system = messages[0]["content"]
            marker_index = prompt.index(media_marker)
            shape_rows.append(
                {
                    "system_then_user_roles": [m["role"] for m in messages]
                    == ["system", "user"],
                    "no_evidence_block_anywhere": "[evidence " not in prompt,
                    "one_input_audio_part_and_nothing_else": (
                        isinstance(messages[-1]["content"], list)
                        and len(messages[-1]["content"]) == 1
                        and messages[-1]["content"][0].get("type") == "input_audio"
                    ),
                    "instruction_verbatim_in_rendered_prompt": instruction in prompt,
                    "instruction_precedes_the_media_marker": (
                        prompt.index(instruction_base) < marker_index
                    ),
                    "draft_text_verbatim_in_the_system_message": (
                        draft.text in system if draft.text else True
                    ),
                    "draft_block_follows_the_instruction": (
                        system.index(instruction_base) < system.rindex(frame[:40])
                    ),
                    "payload_key_set_equals_the_bare_core_allowlist": set(payload)
                    == allowlist,
                }
            )
            required = int(window["speech_tokens"]) + tokens + max_tokens + SPECIAL_TOKENS
            window_rows.append(
                {
                    "window_id": window["window_id"],
                    "sample_id": window["sample_id"],
                    "window_seconds": window["window_seconds"],
                    "speech_tokens": int(window["speech_tokens"]),
                    "text_tokens": tokens,
                    "draft_completion_tokens": draft.completion_tokens,
                    "required_tokens": required,
                }
            )
        worst = max(window_rows, key=lambda row: row["required_tokens"])
        per_cell[cell_id] = {
            "cell_id": cell_id,
            "config_hash": composed_by_cell[cell_id].config_hash,
            "binding_relpath": relpath,
            "windows_rendered": len(window_rows),
            "text_token_distribution": distribution(
                [row["text_tokens"] for row in window_rows]
            ),
            "draft_token_distribution": distribution(
                [int(row["draft_completion_tokens"] or 0) for row in window_rows]
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
            "  %-36s windows=%4d text min/median/max = %5d / %8.1f / %5d "
            "worst_required=%5d factor=%.3f"
            % (
                cell_id,
                len(window_rows),
                per_cell[cell_id]["text_token_distribution"]["min"],
                per_cell[cell_id]["text_token_distribution"]["median"],
                per_cell[cell_id]["text_token_distribution"]["max"],
                worst["required_tokens"],
                per_cell[cell_id]["margin_factor"],
            )
        )

    document = {
        "schema": "saea-e21-dr1-prompt-fit-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "experiment_fragment": args.experiment,
        "attempt_id": plan.attempt_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "study_commit": git("rev-parse", "HEAD"),
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
        "bindings": {
            relpath: {"run_id": snapshot.run_id, "windows": snapshot.window_count}
            for relpath, snapshot in snapshots.items()
        },
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
        "one_factor": {
            "dr1c_vs_dr1f_composed_diff": c_vs_f,
            "dr1c_vs_dr1s_composed_diff": c_vs_s,
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
                "1 widen the slot; 2 lower the pass-2 completion ceiling; 3 does not "
                "exist -- KC-E1f's third lever was the brief cap and DR-1 carries no "
                "brief. Fixed before measurement in this script's own docstring"
            ),
        },
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "prompt-fit.json"
    out_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    log("wrote %s (%d bytes)" % (out_path, out_path.stat().st_size))
    log("canonical %s" % canonical_sha256(document)[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
