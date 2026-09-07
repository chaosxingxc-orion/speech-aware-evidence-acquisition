#!/usr/bin/env python3
"""Prompt fit for the Earnings-21 pre-meeting-brief cells, before any flight.

Precondition 2 of ``docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-
preregistration.md``, and the last measurement standing between KC-E1 and a
takeoff decision. The E5 provenance receipt
(``docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-pre-meeting-
brief-provenance/``) priced the brief in WHITESPACE tokens -- 263 to 2,565 per
call, median 969 -- and said in writing that it would not guess the tokenizer's
count. This script measures it, on the flight tokenizer, for every request the
flight would send.

METHOD, and why it is exact rather than a bound
-----------------------------------------------
TEXT is measured through the resident server's own non-generative routes, the
technique ``scripts/a2t_calibration_prompt_fit.py`` established and
``scripts/e22_dev_esb_prompt_fit.py`` carried to the Earnings carrier: ``POST
/apply-template`` renders the EXACT wire messages through the pinned GGUF chat
template, and ``POST /tokenize`` counts the rendered prompt around the single
opaque media marker ``GET /props`` reports. Nothing decodes and zero tokens are
generated.

The wire messages are not rebuilt here. They come from the REAL
``core.model.transport.LlamaServerTransport``, resolved through the REAL
``TRANSPORTS`` registry entry from the REAL composed config, driven with a REAL
``core.policies.build_arm_payload`` payload carrying the REAL
``core.evidence.conec-class-lists`` items -- only the transport's HTTP sender is
replaced by a capture. What is measured is therefore the flight's own request
bytes rather than a second spelling of them.

SPEECH is the mmproj encoder's one-second window rule ``n_tokens = 13 *
ceil(audio_seconds)``, the rule the E21 window-fit receipt certified this exact
geometry with and which reproduced all 342 sealed ``COST`` records of
``SAEA-E-005B-N10-zero`` without an exception. No audio is encoded here: the
media in a rendered prompt is one opaque marker, so a deterministic 0.1-second
silent WAV stands in for every window's slice and no call audio reaches the core
at all.

THE MEDIA STAND-IN IS NOT A SHORTCUT AROUND THE MEASUREMENT. It is the only way
to make it: the flight's own slices are 90-second MP3-derived WAVs whose base64
would be ~2.5 MB per request, and every byte of them collapses to the same
single marker in the rendered prompt. The rule above supplies their token cost
separately, per window, from their durations.

THE FIT RULE is this repository's own, unchanged from the E21 window-fit and the
E22 sibling: a request may occupy at most half its slot,
``slot_tokens >= 2 * worst_required``, with
``worst_required = speech + text + max_tokens + 2`` and the slot a multiple of
512 so llama-server's own rounding cannot move it. The strict-fit reading
(``slot_tokens >= worst_required``) is recorded beside it as a second, clearly
labelled number, and the generic per-slot reserve some other cells of this study
are read against (8,192 tokens of margin) is recorded as UNREACHABLE at a
6,144-token slot -- it exceeds the whole slot, so no request of any size could
meet it and it is not the rule that certified this geometry.

THE CAP. If the whole brief does not fit, ``brief_max_entries_per_class`` is
swept over a fixed candidate grid and set to the LARGEST value whose worst
request still fits -- the least truncation the slot permits, not the smallest
integer, because the fit is monotone in the cap and every small value would
trivially "fit". The chosen value is then applied to BOTH cells: the twin stops
being a twin the moment the two fragments cap differently. Both the chosen cap
and the next larger candidate are re-rendered in full, so the boundary is proved
from both sides rather than interpolated.

A model-free companion mode, ``--cap-impact-only``, answers the question the
fit cannot: the fit says a cap is LEGAL, and this says what it COSTS -- how many
entries each of the six classes had before the cap and how many survive it, over
the real 44 calls. It returns before the plan, the gate, the media stand-in and
the server, so its zero-contact claim carries no asterisk.

Usage::

    python scripts/e21_kc_e1_prompt_fit.py --out-dir <dir>
    python scripts/e21_kc_e1_prompt_fit.py --cap-impact-only --out-dir <dir>
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
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
RUNTIME_ROOT = Path("/home/chao")

CHECK = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e21-kc-e1-brief-44-v1"
)
ROSTER_RECEIPT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-roster/flight-roster-receipt.json"
)
BRIEF_PROVENANCE = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e21-pre-meeting-brief-provenance/brief-provenance.json"
)
WINDOW_FIT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-direct-baseline-v1/window-fit/window-fit.json"
)

EXPERIMENT = "e21-kc-e1-brief-44-v1"
RUN_ID = "SAEA-E21-KC-E1-PROMPT-FIT-V1"
FLIGHT_RUN_ID = "SAEA-E21-KC-E1-BRIEF-44-V1"
SPLIT_IDENTITY_HASH = (
    "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
)

#: The mmproj encoder's exact one-second window rule.
SPEECH_TOKENS_PER_SECOND_WINDOW = 13
#: Two special tokens, the same allowance every sealed Earnings flight carried.
SPECIAL_TOKENS = 2
#: slot_tokens >= FIT_MULTIPLE * worst_required.
FIT_MULTIPLE = 2
#: The generic per-slot reserve other cells of this study are read against.
#: Recorded, never applied here: it exceeds this geometry's whole slot.
GENERIC_SLOT_RESERVE_TOKENS = 8192

#: The cap grid. 0 is "the whole brief" -- always measured first, whatever the
#: fragments currently carry, so the receipt can answer "does the whole brief
#: fit" from its own numbers; the rest are the candidates the sweep may choose
#: from. Fixed here, before any measurement, so the chosen value cannot be
#: reverse-engineered from a result.
CAP_GRID = (0, 128, 96, 64, 48, 32, 24, 20, 16, 12, 10, 8, 6, 4, 2, 1)

#: Nominal: nothing decodes. A positive budget is still required by
#: ``contracts.ExecutionPlan``, and the run's registered ceiling is cumulative
#: across every attempt of the run id.
PLAN_CALLS = 2
PLAN_AUDIO_SECONDS = 2
PLAN_GPU_HOURS = 0.4

#: The silent media stand-in. 0.1 s of 16 kHz mono silence, written by the
#: repository's OWN wav writer so the bytes are the same shape the OBS slicer
#: produces, under the controlled data root and never in Git.
STAND_IN_RELPATH = "derived/prompt-fit/e21-kc-e1/silence-100ms-16k.wav"
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
    blob = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Mapping[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def speech_tokens(audio_seconds: float) -> int:
    return SPEECH_TOKENS_PER_SECOND_WINDOW * math.ceil(float(audio_seconds))


def distribution(values: Sequence[int]) -> dict[str, Any]:
    ordered = sorted(values)

    def percentile(fraction: float) -> int:
        index = min(
            len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1))))
        )
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
    """The 1,593 fixed 90-second windows, from the roster receipt's own counts.

    The window ids are minted in the SAME ``<sample_id>#w<index>`` convention
    ``analysis.e21_window_pairing`` uses, so a row of this receipt names the
    same unit the paired read will. Every call is checked to sum back to its
    own recorded duration before a single window is emitted.
    """

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
        if not 0.0 < last <= 90.0:
            raise SystemExit(
                "call %s: last window %.6f s is not in (0, 90]" % (sample_id, last)
            )
        for index, window_seconds in enumerate(seconds):
            windows.append(
                {
                    "window_id": "%s#w%d" % (sample_id, index),
                    "sample_id": sample_id,
                    "window_index": index,
                    "window_seconds": window_seconds,
                    "speech_tokens": speech_tokens(window_seconds),
                }
            )
    return windows


def text_token_count(client, counts, messages, media_marker) -> tuple[int, str]:
    """``(text tokens, rendered prompt)`` for one message list."""

    rendered = client.request_json(
        "POST", "/apply-template", {"messages": list(messages)}
    )
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


#: The wire-shape properties every rendered request must satisfy. Named here,
#: before the measurement, so a receipt reader sees the claim rather than a
#: pass/fail with no proposition attached.
WIRE_SHAPE_PROPERTIES = (
    "system_then_user_roles",
    "system_text_is_evidence_blocks_then_instruction",
    "exactly_two_evidence_blocks",
    "roster_block_precedes_document_block",
    "one_input_audio_part_and_nothing_else",
    "instruction_verbatim_in_rendered_prompt",
    "both_evidence_blocks_precede_the_media_marker",
    "instruction_precedes_the_media_marker",
)


def wire_shape(
    *,
    messages: Sequence[Mapping[str, Any]],
    prompt: str,
    media_marker: str,
    items: Sequence[Any],
    instruction: str,
) -> dict[str, bool]:
    """The eight propositions the preregistration's wire check asks of a request.

    Checked HERE rather than in the contact-free wire check for one structural
    reason: ``core.model.transport.LlamaServerTransport`` re-runs the full I5
    session liveness, binary-identity and socket-ownership check on every send,
    so the only place the REAL transport can be driven is beside a REAL
    resident server -- which is exactly where this measurement already is. The
    wire check proves everything up to the payload, from the sealed trace; this
    proves what the transport then does with it.

    The second property is the load-bearing one: an EQUALITY against the two
    evidence items the source returned, which pins the block order, the
    ``[evidence <id>] `` prefix, the blank-line separator and the instruction's
    position after both blocks in a single assertion rather than four
    independent substring searches.
    """

    roles = [str(message["role"]) for message in messages]
    system = messages[0]["content"] if messages and roles[:1] == ["system"] else None
    expected_system = "\n\n".join(
        [f"[evidence {item.evidence_id}] {item.content}" for item in items]
        + [instruction]
    )
    user_content = messages[-1]["content"] if messages else None
    roster_marker = f"[evidence {items[0].evidence_id}]"
    document_marker = f"[evidence {items[1].evidence_id}]"
    marker_index = prompt.index(media_marker)
    system_is_text = isinstance(system, str)
    return {
        "system_then_user_roles": roles == ["system", "user"],
        "system_text_is_evidence_blocks_then_instruction": (
            system_is_text and system == expected_system
        ),
        "exactly_two_evidence_blocks": (
            system_is_text and system.count("[evidence ") == 2
        ),
        "roster_block_precedes_document_block": (
            system_is_text
            and roster_marker in system
            and document_marker in system
            and system.index(roster_marker) < system.index(document_marker)
        ),
        "one_input_audio_part_and_nothing_else": (
            isinstance(user_content, list)
            and len(user_content) == 1
            and isinstance(user_content[0], Mapping)
            and user_content[0].get("type") == "input_audio"
        ),
        "instruction_verbatim_in_rendered_prompt": instruction in prompt,
        "both_evidence_blocks_precede_the_media_marker": (
            roster_marker in prompt
            and document_marker in prompt
            and prompt.index(roster_marker) < marker_index
            and prompt.index(document_marker) < marker_index
        ),
        "instruction_precedes_the_media_marker": (
            instruction in prompt and prompt.index(instruction) < marker_index
        ),
    }


def tokenize_count(client, counts, text: str) -> int:
    """Flight-tokenizer token count of one standalone string."""

    response = client.request_json(
        "POST",
        "/tokenize",
        {"content": text, "add_special": False, "parse_special": True},
    )
    counts["POST /tokenize"] += 1
    tokens = response.get("tokens")
    if not isinstance(tokens, list):
        raise SystemExit("tokenize returned no token list")
    return len(tokens)


def write_cap_impact(
    args,
    *,
    lock,
    root: Path,
    sample_ids: Sequence[str],
    carrier_lock_key: str,
    cap: int,
    roster_by_call: Mapping[str, str],
) -> int:
    """What the committed cap discards, class by class, over the real 44 calls.

    The fit certifies the cap is LEGAL. This certifies what it COSTS, which is
    a different question and the one a reader of the verdict will ask first --
    the preregistration's own §7 item 2 warns that dropping the roster half
    would turn the cell into a different experiment, so how much of that half
    survives has to be a published number rather than an impression. Zero
    contacts of every kind: the six class extractors are pure functions over
    the same two ConEC files the evidence source reads.
    """

    from speech_aware_evidence_acquisition.core.class_lists import (
        affiliation_class,
        company_class,
        context_tokens,
        division_class,
        participant_class,
        roster_entries,
        segment_class,
        term_class,
    )
    from speech_aware_evidence_acquisition.core.evidence import (
        conec_names_file_relpath,
        evidence_file_relpath,
    )

    classes = (
        ("roster", "Participants and roles", participant_class),
        ("roster", "Organizations named in the roster", affiliation_class),
        ("roster", "Divisions and segments named in the roster", division_class),
        ("document", "Company and ticker candidates", company_class),
        ("document", "Product and segment candidates", segment_class),
        ("document", "Other terms from the call's documents", term_class),
    )
    per_class: dict[str, dict[str, Any]] = {
        label: {
            "brief_part": part,
            "calls_with_the_class": 0,
            "calls_truncated": 0,
            "entries_before": 0,
            "entries_after": 0,
            "max_entries_on_any_call": 0,
        }
        for part, label, _ in classes
    }
    call_rows: list[dict[str, Any]] = []
    for sample_id in sample_ids:
        roster_text = (
            root / conec_names_file_relpath(lock, carrier_lock_key, sample_id)
        ).read_text(encoding="utf-8")
        document_text = (
            root / evidence_file_relpath(lock, carrier_lock_key, sample_id)
        ).read_text(encoding="utf-8")
        entries = roster_entries(roster_text)
        tokens = context_tokens(document_text)
        row: dict[str, Any] = {"sample_id": sample_id, "classes": {}}
        for part, label, extractor in classes:
            values = extractor(entries if part == "roster" else tokens)
            before = len(values)
            after = min(before, cap) if cap else before
            entry = per_class[label]
            if before:
                entry["calls_with_the_class"] += 1
            entry["entries_before"] += before
            entry["entries_after"] += after
            entry["max_entries_on_any_call"] = max(
                entry["max_entries_on_any_call"], before
            )
            if after < before:
                entry["calls_truncated"] += 1
            row["classes"][label] = {"before": before, "after": after}
        row["roster_half_entries_before"] = sum(
            row["classes"][label]["before"] for part, label, _ in classes if part == "roster"
        )
        row["roster_half_entries_after"] = sum(
            row["classes"][label]["after"] for part, label, _ in classes if part == "roster"
        )
        row["in_sealed_ten"] = roster_by_call.get(sample_id)
        call_rows.append(row)

    for entry in per_class.values():
        entry["kept_fraction"] = (
            round(entry["entries_after"] / entry["entries_before"], 6)
            if entry["entries_before"]
            else None
        )

    participants = per_class["Participants and roles"]
    document_terms = per_class["Other terms from the call's documents"]
    document_total_before = sum(
        entry["entries_before"]
        for label, entry in per_class.items()
        if entry["brief_part"] == "document"
    )
    document_total_after = sum(
        entry["entries_after"]
        for label, entry in per_class.items()
        if entry["brief_part"] == "document"
    )
    roster_total_before = sum(
        entry["entries_before"]
        for label, entry in per_class.items()
        if entry["brief_part"] == "roster"
    )
    roster_total_after = sum(
        entry["entries_after"]
        for label, entry in per_class.items()
        if entry["brief_part"] == "roster"
    )

    document = {
        "schema": "saea-e21-kc-e1-cap-impact-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "brief_max_entries_per_class": cap,
        "study_commit": git("rev-parse", "HEAD"),
        "zero_contact": (
            "no model, server, tokenizer, GPU, tool, embedding, network or "
            "audio-decode contact; six pure class extractors over the same two "
            "ConEC context files the evidence source reads, and nothing else"
        ),
        "what_this_answers": (
            "the fit says the cap is legal at this geometry. This says what it "
            "costs: how many entries each class had before the cap and how many "
            "survive it, over the real 44 calls"
        ),
        "calls": len(sample_ids),
        "per_class": per_class,
        "halves": {
            "roster": {
                "entries_before": roster_total_before,
                "entries_after": roster_total_after,
                "kept_fraction": round(roster_total_after / roster_total_before, 6),
            },
            "document": {
                "entries_before": document_total_before,
                "entries_after": document_total_after,
                "kept_fraction": round(document_total_after / document_total_before, 6),
            },
        },
        "headline": (
            "the cap falls almost entirely on the DOCUMENT half's residual-term "
            "class (%d of %d entries kept, %d of 44 calls truncated); the ROSTER "
            "half keeps %d of %d entries, and the participant class -- the one the "
            "PERSON hypothesis rests on -- keeps %d of %d over %d truncated calls"
            % (
                document_terms["entries_after"],
                document_terms["entries_before"],
                document_terms["calls_truncated"],
                roster_total_after,
                roster_total_before,
                participants["entries_after"],
                participants["entries_before"],
                participants["calls_truncated"],
            )
        ),
        "call_rows": call_rows,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "cap-impact.json"
    out_path.write_text(
        json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    log("wrote %s (%d bytes)" % (out_path, out_path.stat().st_size))
    log(document["headline"])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=CHECK / "prompt-fit")
    parser.add_argument("--experiment", default=EXPERIMENT)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help=(
            "TEST-ONLY. A fit certifies COMMITTED fragments -- the cap it reports "
            "is only meaningful if the baseline fragments it read are the ones "
            "that will fly. Without this the run refuses a dirty tree rather than "
            "recording a study_commit that describes different bytes"
        ),
    )
    parser.add_argument(
        "--cap-impact-only",
        action="store_true",
        help=(
            "MODEL-FREE mode: spawn nothing, contact nothing, and write only "
            "cap-impact.json -- what the committed cap actually discards, class by "
            "class, over the real 44 calls. The fit says the cap is legal; this says "
            "what it costs, which is the number the flight's own reporting needs"
        ),
    )
    parser.add_argument(
        "--reference-media-marker",
        default=None,
        help=(
            "a PRIOR receipt's server media marker. llama-server mints a fresh "
            "random marker per session, so two renderings of the same prompt on "
            "the same template never share a rendered_prompt_sha256 even when "
            "every other byte is identical. When given, each envelope also "
            "records its hash with this session's marker REPLACED by the "
            "reference one, which makes cross-receipt comparison a proof rather "
            "than an inference"
        ),
    )
    args = parser.parse_args()

    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
        raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

    import speech_aware_evidence_acquisition as _pkg

    if (
        Path(_pkg.__file__ or "")
        != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"
    ):
        raise SystemExit(
            "package resolves to %s, not the main checkout" % (_pkg.__file__,)
        )

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate
    from speech_aware_evidence_acquisition.core.base import EVIDENCE_SOURCES, TRANSPORTS
    from speech_aware_evidence_acquisition.core.class_lists import (
        whitespace_token_count,
    )
    from speech_aware_evidence_acquisition.core.config import (
        compose,
        d1_evidence_supplement_relpath,
        d1_evidence_supplement_sha256,
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
    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.data.loader import SampleRef
    from speech_aware_evidence_acquisition.reproduction.obs_audio import write_wav_bytes

    dirty = git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "the working tree is dirty; a fit certifies committed fragments:\n" + dirty
        )
    study_commit = git("rev-parse", "HEAD")
    log("clean tree at %s" % study_commit[:8])

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
    baseline_by_cell = {
        str(cell["cell_id"]): str(cell["baseline_fragment"]) for cell in cells
    }

    # The one factor: the two fragments must differ in exactly evidence_source
    # -- or, since SAEA-E21-KU-E1C-TOKEN-MATCH-V1 (2026-09-07), in that plus
    # the twin's own pad-plan pin -- and must carry the SAME cap. Re-asserted
    # here, on the composed configs, because a fit that measured two
    # differently-capped cells would certify a twin that no longer exists.
    # ``evidence_pad_plan`` is admitted because it is the BYTE IDENTITY of the
    # twin's own token match: it names no call content, it changes nothing the
    # arm renders, and it exists so the two cells' briefs measure the same on
    # this very tokenizer. A third key would not be admitted.
    values_a = dict(composed_by_cell[cell_ids[0]].values)
    values_b = dict(composed_by_cell[cell_ids[1]].values)
    differing = sorted(
        key
        for key in set(values_a) | set(values_b)
        if values_a.get(key) != values_b.get(key)
    )
    if differing not in (["evidence_source"], ["evidence_pad_plan", "evidence_source"]):
        raise SystemExit(
            "the two cells must differ in exactly evidence_source, or in it plus the "
            "twin's pad-plan pin; they differ in %r" % (differing,)
        )
    committed_cap = int(values_a.get("brief_max_entries_per_class", 0))
    log("committed brief_max_entries_per_class = %d (both fragments)" % committed_cap)

    geometry = values_a["serving_geometry"]
    slots = int(geometry["slots"])
    slot_tokens = int(geometry["slot_tokens"])
    max_tokens = int(geometry["max_tokens"])
    server_args = [str(value) for value in values_a["server_args"]]
    declared_c = int(server_args[server_args.index("-c") + 1])
    declared_np = int(server_args[server_args.index("-np") + 1])
    if declared_np != slots or declared_c != slots * slot_tokens:
        raise SystemExit("model fragment server_args disagree with its serving_geometry")
    if slot_tokens % 512:
        raise SystemExit("slot_tokens must be a multiple of 512")

    roster = load_json(ROSTER_RECEIPT)
    windows = build_windows(roster)
    declared_windows = int(experiment_doc["population"]["fixed_90s_windows_one_pass"])
    if len(windows) != declared_windows:
        raise SystemExit(
            "built %d windows, the experiment fragment declares %d"
            % (len(windows), declared_windows)
        )
    sample_ids = [str(call["sample_id"]) for call in roster["calls"]]
    windows_by_sample: dict[str, list[dict[str, Any]]] = {sid: [] for sid in sample_ids}
    for window in windows:
        windows_by_sample[window["sample_id"]].append(window)
    worst_window_seconds = max(window["window_seconds"] for window in windows)
    worst_speech_tokens = speech_tokens(worst_window_seconds)
    log(
        "%d windows over %d calls; longest %.6f s -> %d speech tokens"
        % (len(windows), len(sample_ids), worst_window_seconds, worst_speech_tokens)
    )

    lock = load_lock(umbrella_lock_path())
    root = data_root()

    # The model-free branch returns BEFORE the plan, the gate, the media
    # stand-in and the server: --cap-impact-only must be able to say "zero
    # contacts of every kind" without an asterisk, so it never opens a gate
    # either.
    if args.cap_impact_only:
        return write_cap_impact(
            args,
            lock=lock,
            root=root,
            sample_ids=sample_ids,
            carrier_lock_key=str(values_a["carrier_lock_key"]),
            cap=committed_cap,
            roster_by_call={
                str(call["sample_id"]): bool(call.get("in_sealed_ten", False))
                for call in roster["calls"]
            },
        )

    # The media stand-in, written before the gate so its bytes are pinned in
    # the receipt whatever happens next.
    stand_in_path = root / STAND_IN_RELPATH
    stand_in_path.parent.mkdir(parents=True, exist_ok=True)
    stand_in_bytes = write_wav_bytes(
        [0] * int(round(STAND_IN_SECONDS * STAND_IN_RATE_HZ)), STAND_IN_RATE_HZ
    )
    stand_in_path.write_bytes(stand_in_bytes)
    log(
        "media stand-in %s (%d bytes, sha256 %s)"
        % (
            STAND_IN_RELPATH,
            len(stand_in_bytes),
            hashlib.sha256(stand_in_bytes).hexdigest()[:12],
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
        attempt_id="attempt-%s-e21kce1fit"
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

    # ------------------------------------------------------------------
    # Evidence, rendered offline once per (cell, cap). No model contact.
    # ------------------------------------------------------------------
    source_by_cell = {
        cell_id: EVIDENCE_SOURCES.resolve(
            str(composed_by_cell[cell_id].values["evidence_source"])
        )
        for cell_id in cell_ids
    }
    evidence_cache: dict[tuple[str, int], dict[str, list[Any]]] = {}

    def evidence_for(cell_id: str, cap: int) -> dict[str, list[Any]]:
        key = (cell_id, cap)
        if key not in evidence_cache:
            values = dict(composed_by_cell[cell_id].values)
            values["brief_max_entries_per_class"] = cap
            source = source_by_cell[cell_id]
            built: dict[str, list[Any]] = {}
            for sample_id in sample_ids:
                items = source(lock, root, sample_id, str(values_a["carrier_lock_key"]), values)
                if len(items) != 2:
                    raise SystemExit(
                        "the brief must be two items (roster then document), got %d"
                        % len(items)
                    )
                if items[0].provenance["brief_part"] != "roster":
                    raise SystemExit("the roster half must come first")
                if items[1].provenance["brief_part"] != "document":
                    raise SystemExit("the document half must come second")
                built[sample_id] = items
            evidence_cache[key] = built
        return evidence_cache[key]

    runtime_receipt = load_runtime_receipt(REPO / "docs" / str(values_a["runtime_receipt"]))
    run_dir = root / "runs" / args.run_id / str(plan.attempt_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    extra_argv = merge_server_args(
        values_a["server_args"], slots=slots, context_tokens=slots * slot_tokens
    )
    port = int(str(values_a["base_url"]).rsplit(":", 1)[-1])
    log("spawning llama-server on %d: %s" % (port, " ".join(extra_argv)))
    started_at = time.time()
    session = start_session(
        runtime_root=RUNTIME_ROOT,
        data_root=root,
        runtime_receipt=runtime_receipt,
        host="127.0.0.1",
        port=port,
        session_id="%s-%s" % (args.run_id, plan.attempt_id),
        extra_argv=extra_argv,
        extra_env=dict(values_a.get("server_env", {})),
        receipt_path=run_dir / "session.receipt.json",
        server_log_path=run_dir / "session.server.log",
        role=str(runtime_receipt.get("role", "legacy")),
        model_root=(Path(configured_model_root) if configured_model_root else None),
        ready_timeout_seconds=1800.0,
    )
    load_seconds = time.time() - started_at
    log("server up in %.1fs: pid=%s port=%s" % (load_seconds, session.pid, session.port))

    counts: Counter[str] = Counter()
    passes: dict[str, Any] = {}
    sweep: dict[str, Any] = {}
    media_marker = ""
    chat_template_sha256 = ""
    live_slot_ctx: object = None

    def render_pass(client, cap: int, *, label: str, full: bool) -> dict[str, Any]:
        """Render and measure one cap.

        ``full`` renders EVERY window of every call (the flight's own request
        count); otherwise one window per call, which is exact for the text
        because the envelope is window-independent -- a property the full
        passes prove rather than assume.
        """

        per_cell: dict[str, Any] = {}
        for cell_id in cell_ids:
            evidence = evidence_for(cell_id, cap)
            values = dict(composed_by_cell[cell_id].values)
            values["brief_max_entries_per_class"] = cap
            instruction = str(values["task_instruction"])
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

            brief_rows: list[dict[str, Any]] = []
            window_rows: list[dict[str, Any]] = []
            shape_rows: list[dict[str, bool]] = []
            rendered_by_sample: dict[str, dict[str, Any]] = {}
            for sample_id in sample_ids:
                items = evidence[sample_id]
                roster_tokens = tokenize_count(client, counts, items[0].content)
                document_tokens = tokenize_count(client, counts, items[1].content)
                brief_rows.append(
                    {
                        "sample_id": sample_id,
                        "roster_tokens": roster_tokens,
                        "document_tokens": document_tokens,
                        "brief_tokens": roster_tokens + document_tokens,
                        "roster_whitespace_tokens": whitespace_token_count(
                            items[0].content
                        ),
                        "document_whitespace_tokens": whitespace_token_count(
                            items[1].content
                        ),
                        "brief_whitespace_tokens": (
                            whitespace_token_count(items[0].content)
                            + whitespace_token_count(items[1].content)
                        ),
                        "roster_derived_sha256": items[0].derivation.derived_sha256,
                        "document_derived_sha256": items[1].derivation.derived_sha256,
                        "roster_source_relpath": items[0].derivation.source_relpath,
                        "document_source_relpath": items[1].derivation.source_relpath,
                        "line_whitespace_tokens": [
                            [whitespace_token_count(line) for line in item.content.splitlines()]
                            for item in items
                        ],
                    }
                )
                chosen = (
                    windows_by_sample[sample_id]
                    if full
                    else windows_by_sample[sample_id][:1]
                )
                for window in chosen:
                    ref = SampleRef(
                        carrier_lock_key=str(values_a["carrier_lock_key"]),
                        sample_id=sample_id,
                        media_relpath=STAND_IN_RELPATH,
                        audio_seconds=float(window["window_seconds"]),
                        sample_rate_hz=STAND_IN_RATE_HZ,
                    )
                    payload = build_arm_payload(
                        str(values["arm"]),
                        ref,
                        "e21kce1-fit-%s-%s" % (cell_id, window["window_id"]),
                        instruction,
                        decoding_params,
                        evidence=list(items),
                    )
                    transport(json.dumps(payload).encode("utf-8"))
                    messages = captured["body"]["messages"]
                    tokens, prompt = text_token_count(
                        client, counts, messages, media_marker
                    )
                    shape_rows.append(
                        wire_shape(
                            messages=messages,
                            prompt=prompt,
                            media_marker=media_marker,
                            items=items,
                            instruction=instruction,
                        )
                    )
                    required = (
                        int(window["speech_tokens"]) + tokens + max_tokens + SPECIAL_TOKENS
                    )
                    window_rows.append(
                        {
                            "window_id": window["window_id"],
                            "sample_id": sample_id,
                            "window_index": window["window_index"],
                            "window_seconds": window["window_seconds"],
                            "speech_tokens": int(window["speech_tokens"]),
                            "text_tokens": tokens,
                            "required_tokens": required,
                        }
                    )
                    if sample_id not in rendered_by_sample:
                        entry = {
                            "text_tokens": tokens,
                            "rendered_prompt_sha256": sha256_text(prompt),
                            "rendered_prompt_chars": len(prompt),
                            "wire_messages_sha256": canonical_sha256(messages),
                            "wire_message_roles": [
                                str(message["role"]) for message in messages
                            ],
                            "evidence_provenance": payload["evidence_provenance"],
                        }
                        if args.reference_media_marker:
                            entry["reference_media_marker"] = str(
                                args.reference_media_marker
                            )
                            entry[
                                "rendered_prompt_sha256_with_reference_marker"
                            ] = sha256_text(
                                prompt.replace(
                                    media_marker, str(args.reference_media_marker)
                                )
                            )
                        rendered_by_sample[sample_id] = entry

            # The envelope must be window-independent: the evidence and the
            # instruction are per-call and obs_condition_tail_chars is 0, so a
            # per-window difference would mean something else is riding in the
            # prompt.
            by_sample: dict[str, set[int]] = {}
            for row in window_rows:
                by_sample.setdefault(row["sample_id"], set()).add(row["text_tokens"])
            varying = {sid: sorted(v) for sid, v in by_sample.items() if len(v) > 1}
            if varying:
                raise SystemExit(
                    "the text envelope varies within a call: %r" % (varying,)
                )

            text_by_sample = {
                sid: sorted(v)[0] for sid, v in by_sample.items()
            }
            brief_by_sample = {row["sample_id"]: row["brief_tokens"] for row in brief_rows}
            overheads = sorted(
                {text_by_sample[sid] - brief_by_sample[sid] for sid in sample_ids}
            )
            worst_row = max(window_rows, key=lambda row: row["required_tokens"])
            worst_text_row = max(window_rows, key=lambda row: row["text_tokens"])
            per_cell[cell_id] = {
                "cell_id": cell_id,
                "baseline_fragment": baseline_by_cell[cell_id],
                "evidence_source": str(values["evidence_source"]),
                "brief_max_entries_per_class": cap,
                "config_hash": composed_by_cell[cell_id].config_hash,
                "task_instruction_sha256": sha256_text(instruction),
                "windows_rendered": len(window_rows),
                "text_token_distribution": distribution(
                    [row["text_tokens"] for row in window_rows]
                ),
                "brief_token_distribution": distribution(
                    [row["brief_tokens"] for row in brief_rows]
                ),
                "brief_whitespace_token_distribution": distribution(
                    [row["brief_whitespace_tokens"] for row in brief_rows]
                ),
                "fixed_envelope_overhead_tokens": overheads,
                "fixed_envelope_overhead_is_constant": len(overheads) == 1,
                "max_text_sample_id": worst_text_row["sample_id"],
                "max_text_window_id": worst_text_row["window_id"],
                "max_text_tokens": worst_text_row["text_tokens"],
                "max_text_envelope": rendered_by_sample[worst_text_row["sample_id"]],
                "worst_window_id": worst_row["window_id"],
                "worst_required_tokens": worst_row["required_tokens"],
                "worst_required_basis": (
                    "%d speech (13 * ceil(%.6f s)) + %d text + %d completion ceiling "
                    "+ %d special"
                    % (
                        worst_row["speech_tokens"],
                        worst_row["window_seconds"],
                        worst_row["text_tokens"],
                        max_tokens,
                        SPECIAL_TOKENS,
                    )
                ),
                "wire_shape": {
                    "requests_checked": len(shape_rows),
                    "properties": {
                        name: {
                            "holds_on_every_request": all(
                                row[name] for row in shape_rows
                            ),
                            "requests_holding": sum(1 for row in shape_rows if row[name]),
                        }
                        for name in WIRE_SHAPE_PROPERTIES
                    },
                    "all_hold": all(
                        all(row[name] for row in shape_rows)
                        for name in WIRE_SHAPE_PROPERTIES
                    ),
                },
                "brief_rows": brief_rows,
                "window_rows": window_rows,
                "rendered_by_sample": rendered_by_sample,
            }
            log(
                "  %-28s cap=%-4d windows=%4d text min/median/max = %5d / %8.1f / %5d "
                "worst_required=%5d"
                % (
                    cell_id,
                    cap,
                    len(window_rows),
                    per_cell[cell_id]["text_token_distribution"]["min"],
                    per_cell[cell_id]["text_token_distribution"]["median"],
                    per_cell[cell_id]["text_token_distribution"]["max"],
                    worst_row["required_tokens"],
                )
            )

        arm, twin = per_cell[cell_ids[0]], per_cell[cell_ids[1]]
        # The twin's guarantee, asserted by MEASUREMENT rather than by
        # construction: the placebo holds the brief's whitespace-token count
        # equal LINE BY LINE. The flight-tokenizer difference is reported
        # beside it -- placeholder words tokenize differently from proper
        # nouns, and pretending otherwise would be the dishonest half of this
        # receipt.
        line_mismatches = []
        for arm_row, twin_row in zip(arm["brief_rows"], twin["brief_rows"]):
            if arm_row["line_whitespace_tokens"] != twin_row["line_whitespace_tokens"]:
                line_mismatches.append(arm_row["sample_id"])
        arm_text = {row["window_id"]: row["text_tokens"] for row in arm["window_rows"]}
        twin_text = {row["window_id"]: row["text_tokens"] for row in twin["window_rows"]}
        deltas = [twin_text[key] - arm_text[key] for key in arm_text]
        worst_required = max(
            arm["worst_required_tokens"], twin["worst_required_tokens"]
        )
        return {
            "label": label,
            "brief_max_entries_per_class": cap,
            "full_window_pass": full,
            "cells": per_cell,
            "twin": {
                "whitespace_tokens_match_per_line_on_every_call": not line_mismatches,
                "calls_with_a_line_mismatch": line_mismatches,
                "flight_tokenizer_delta_twin_minus_arm": {
                    "min": min(deltas),
                    "median": float(statistics.median(deltas)),
                    "max": max(deltas),
                },
            },
            "fit": fit_block(worst_required, slot_tokens, slots),
        }

    def fit_block(worst_required: int, slot_tokens: int, slots: int) -> dict[str, Any]:
        return {
            "slot_tokens": slot_tokens,
            "slots": slots,
            "context_tokens": slots * slot_tokens,
            "slot_tokens_is_multiple_of_512": slot_tokens % 512 == 0,
            "worst_required_tokens": worst_required,
            "margin_tokens": slot_tokens - worst_required,
            "margin_factor": round(slot_tokens / worst_required, 4),
            "study_rule": "slot_tokens >= %d * worst_required" % FIT_MULTIPLE,
            "study_rule_required_tokens": FIT_MULTIPLE * worst_required,
            "fits_under_study_rule": slot_tokens >= FIT_MULTIPLE * worst_required,
            "strict_fit_rule": "slot_tokens >= worst_required",
            "fits_strictly": slot_tokens >= worst_required,
            "generic_slot_reserve_tokens": GENERIC_SLOT_RESERVE_TOKENS,
            "meets_generic_slot_reserve": (
                slot_tokens - worst_required >= GENERIC_SLOT_RESERVE_TOKENS
            ),
            "generic_slot_reserve_is_reachable_at_this_geometry": (
                slot_tokens > GENERIC_SLOT_RESERVE_TOKENS
            ),
            "generic_slot_reserve_note": (
                "the %d-token per-slot reserve other cells of this study are read "
                "against exceeds this geometry's WHOLE %d-token slot, so no request "
                "of any size could meet it. It is recorded for completeness and is "
                "NOT the rule that certified this geometry: the E21 window-fit "
                "receipt certified the 6,144-token slot under "
                "'slot_tokens >= 2.0 x worst_required' at a margin factor of 2.721, "
                "and that is the rule the cap decision below is made on"
                % (GENERIC_SLOT_RESERVE_TOKENS, slot_tokens)
            ),
        }

    try:
        client = _LoopbackPromptAuditClient(
            host="127.0.0.1", port=port, timeout_seconds=600.0
        )
        props = client.request_json("GET", "/props", None)
        counts["GET /props"] += 1
        media_marker = props.get("media_marker")
        if not isinstance(media_marker, str) or not media_marker:
            raise SystemExit("resident props lack a media marker")
        live_slot_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
        if int(live_slot_ctx) < slot_tokens:
            raise SystemExit(
                "resident slot n_ctx %s is smaller than the fragment's declared %d; "
                "refusing to certify a fit the server cannot honour"
                % (live_slot_ctx, slot_tokens)
            )
        chat_template = props.get("chat_template")
        chat_template_sha256 = (
            sha256_text(chat_template) if isinstance(chat_template, str) else ""
        )
        log("props OK: slot n_ctx=%s, media marker %r" % (live_slot_ctx, media_marker))

        # PASS 1 -- the WHOLE brief, every window of both cells. Always
        # measured, whatever the fragments currently carry: the receipt has to
        # answer "does the whole brief fit" from its own numbers, or a reader
        # would have to take the cap on trust. Cap 0 is the uncapped renderer
        # by definition (core.class_lists.DEFAULT_MAX_ENTRIES_PER_CLASS).
        log("pass 1: the WHOLE brief (cap 0), all %d windows x 2 cells" % len(windows))
        passes["whole_brief"] = render_pass(client, 0, label="whole_brief", full=True)

        # PASS 2 -- the sweep. Only if the whole brief does not fit.
        chosen_cap = 0
        if not passes["whole_brief"]["fit"]["fits_under_study_rule"]:
            log("the whole brief does NOT fit; sweeping the cap grid")
            overhead = max(
                max(entry["fixed_envelope_overhead_tokens"])
                for entry in passes["whole_brief"]["cells"].values()
            )
            sweep_rows = []
            for cap in CAP_GRID:
                if cap == 0:
                    continue
                worst_brief = 0
                worst_sample = ""
                for cell_id in cell_ids:
                    for sample_id, items in evidence_for(cell_id, cap).items():
                        brief = tokenize_count(
                            client, counts, items[0].content
                        ) + tokenize_count(client, counts, items[1].content)
                        if brief > worst_brief:
                            worst_brief, worst_sample = brief, sample_id
                estimated_text = worst_brief + overhead
                estimated_required = (
                    worst_speech_tokens + estimated_text + max_tokens + SPECIAL_TOKENS
                )
                sweep_rows.append(
                    {
                        "brief_max_entries_per_class": cap,
                        "worst_brief_tokens": worst_brief,
                        "worst_brief_sample_id": worst_sample,
                        "estimated_worst_text_tokens": estimated_text,
                        "estimated_worst_required_tokens": estimated_required,
                        "estimated_fits_under_study_rule": (
                            slot_tokens >= FIT_MULTIPLE * estimated_required
                        ),
                    }
                )
                log(
                    "  sweep cap=%-4d worst brief %5d tokens -> estimated required %5d "
                    "(study rule: %s)"
                    % (
                        cap,
                        worst_brief,
                        estimated_required,
                        "fits" if sweep_rows[-1]["estimated_fits_under_study_rule"] else "over",
                    )
                )
            fitting = [
                row["brief_max_entries_per_class"]
                for row in sweep_rows
                if row["estimated_fits_under_study_rule"]
            ]
            if not fitting:
                raise SystemExit(
                    "no candidate cap on the grid fits; the cell cannot fly at this "
                    "geometry and the flight must stop and report"
                )
            candidate = max(fitting)
            over = [
                row["brief_max_entries_per_class"]
                for row in sweep_rows
                if not row["estimated_fits_under_study_rule"]
            ]
            next_larger = min(over) if over else None
            sweep = {
                "rule": (
                    "the sweep estimates a cap's envelope as (the brief's own "
                    "tokenized halves) + (the fixed per-request overhead measured in "
                    "the whole-brief pass). Tokenization is not exactly additive across the two "
                    "'\\n\\n' joins, so this is a NARROWING step only: the chosen cap "
                    "and the next larger candidate are both re-rendered in full "
                    "below, and the decision is made on those exact numbers"
                ),
                "fixed_overhead_tokens_used": overhead,
                "worst_speech_tokens_used": worst_speech_tokens,
                "rows": sweep_rows,
                "largest_estimated_fitting_cap": candidate,
                "smallest_estimated_over_cap": next_larger,
            }

            # PASS 3 -- the chosen candidate, every window of both cells.
            log("pass 3: candidate cap %d, all %d windows x 2 cells"
                % (candidate, len(windows)))
            passes["candidate"] = render_pass(
                client, candidate, label="candidate", full=True
            )
            if not passes["candidate"]["fit"]["fits_under_study_rule"]:
                raise SystemExit(
                    "the swept candidate %d does not fit when rendered in full; the "
                    "estimate was optimistic and the grid must be re-run" % candidate
                )
            chosen_cap = candidate
            # The measurement chooses the cap; the FRAGMENTS are what flies.
            # A re-run against fragments carrying anything other than the
            # chosen value is refused rather than quietly reported, because a
            # receipt whose decision disagrees with the committed configs
            # certifies a cell that does not exist.
            if committed_cap not in (0, chosen_cap):
                raise SystemExit(
                    "the fragments carry brief_max_entries_per_class %d but the "
                    "measurement chooses %d; set the fragments to the chosen value "
                    "(both of them) or re-run the grid"
                    % (committed_cap, chosen_cap)
                )

            # PASS 4 -- the next larger candidate, one window per call. The
            # refusal has to be measured too, or "the largest that fits" is an
            # assertion rather than a result.
            if next_larger is not None:
                log("pass 4: the next larger candidate %d, one window per call"
                    % next_larger)
                passes["next_larger"] = render_pass(
                    client, next_larger, label="next_larger", full=False
                )
                if passes["next_larger"]["fit"]["fits_under_study_rule"]:
                    raise SystemExit(
                        "the next larger candidate %d ALSO fits when rendered in "
                        "full; the sweep's estimate was pessimistic and the chosen "
                        "cap is not the largest that fits" % next_larger
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

    if counts.get("generations", 0):
        raise SystemExit("a prompt-fit measurement must never generate a token")

    # Fail-closed on the wire shape. A fit that certified a request whose
    # evidence blocks arrived in the wrong order, or whose instruction was
    # lost, would be certifying the wrong prompt.
    shape_failures = [
        (label, cell_id, name)
        for label, entry in passes.items()
        for cell_id, cell in entry["cells"].items()
        for name in WIRE_SHAPE_PROPERTIES
        if not cell["wire_shape"]["properties"][name]["holds_on_every_request"]
    ]
    if shape_failures:
        raise SystemExit("wire-shape properties failed: %r" % (shape_failures,))
    log(
        "wire shape: all %d properties hold on every rendered request of every "
        "pass and cell" % len(WIRE_SHAPE_PROPERTIES)
    )

    final = passes.get("candidate", passes["whole_brief"])
    decision = {
        "cap_in_the_committed_fragments_at_measurement_time": committed_cap,
        "whole_brief_fits_under_study_rule": passes["whole_brief"]["fit"][
            "fits_under_study_rule"
        ],
        "whole_brief_fits_strictly": passes["whole_brief"]["fit"]["fits_strictly"],
        "whole_brief_worst_required_tokens": passes["whole_brief"]["fit"][
            "worst_required_tokens"
        ],
        "chosen_cap": chosen_cap,
        "a_cap_is_required": chosen_cap != 0,
        "committed_fragments_agree_with_the_decision": committed_cap == chosen_cap,
        "why_largest_not_smallest": (
            "the preregistration asks for 'the smallest brief_max_entries_per_class "
            "that fits'. Read literally that is degenerate: the fit is MONOTONE in "
            "the cap, so cap 1 always fits and would be chosen every time. The "
            "intent is the smallest INTERVENTION -- the largest cap whose worst "
            "request still fits, i.e. the least of the brief that has to be thrown "
            "away. That is what is chosen here, and the next larger candidate is "
            "measured too so the choice is proved at the boundary from both sides"
        ),
        "applied_identically_to_both_cells": True,
        "why_identically": (
            "the two fragments differ in exactly one key, evidence_source. A cap "
            "set on one and not the other would make KU-E1c a second treatment "
            "instead of a form control, and the cell's whole claim -- that a gain "
            "surviving the twin is knowledge rather than prompt shape -- would be "
            "void. The composed configs are re-checked for a single differing key "
            "before any measurement is taken"
        ),
        "final_worst_required_tokens": final["fit"]["worst_required_tokens"],
        "final_margin_tokens": final["fit"]["margin_tokens"],
        "final_margin_factor": final["fit"]["margin_factor"],
        "verdict": "FITS" if final["fit"]["fits_under_study_rule"] else "DOES NOT FIT",
    }

    receipt: dict[str, Any] = {
        "schema": "saea-e21-kc-e1-prompt-fit-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "attempt_id": str(plan.attempt_id),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "study_commit": study_commit,
        "working_tree_clean": not dirty,
        "flight_run_id": FLIGHT_RUN_ID,
        "experiment_fragment": args.experiment,
        "dataset_fragment": dataset,
        "model_fragment": model,
        "preregistration": (
            "docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-"
            "preregistration.md"
        ),
        "what_this_is": (
            "precondition 2 of the v2 preregistration: the pre-meeting brief and "
            "both cells' complete requests measured on the FLIGHT tokenizer, for "
            "every one of the 1,593 fixed 90-second windows the flight would "
            "contact, at zero generated tokens"
        ),
        "zero_contact": {
            "generated_tokens": 0,
            "completion_requests": 0,
            "audio_seconds_delivered": 0.0,
            "routes_called": dict(counts),
            "servers_started": 1,
            "media_stand_in": {
                "relpath": STAND_IN_RELPATH,
                "seconds": STAND_IN_SECONDS,
                "sample_rate_hz": STAND_IN_RATE_HZ,
                "bytes": len(stand_in_bytes),
                "sha256": hashlib.sha256(stand_in_bytes).hexdigest(),
                "why": (
                    "the media is a single opaque marker in the rendered prompt, so "
                    "the audio bytes cannot move a text count. Sending the real "
                    "90-second slices would deliver 39.3 hours of call audio to the "
                    "core for a measurement that reads none of it; their token cost "
                    "enters through the one-second window rule instead, per window, "
                    "from their durations"
                ),
            },
        },
        "geometry": {
            "slots": slots,
            "slot_tokens": slot_tokens,
            "context_tokens": slots * slot_tokens,
            "max_tokens": max_tokens,
            "server_args": server_args,
            "live_slot_n_ctx": live_slot_ctx,
            "chat_template_sha256": chat_template_sha256,
            "media_marker": media_marker,
            "server_load_seconds": round(load_seconds, 3),
        },
        "population": {
            "carrier_lock_key": str(values_a["carrier_lock_key"]),
            "split_role": str(experiment_doc["population"]["split_role"]),
            "split_identity_hash": SPLIT_IDENTITY_HASH,
            "calls": len(sample_ids),
            "windows": len(windows),
            "roster_receipt": str(ROSTER_RECEIPT.relative_to(REPO)),
            "roster_receipt_sha256": sha256_file(ROSTER_RECEIPT),
            "longest_window_seconds": worst_window_seconds,
            "longest_window_speech_tokens": worst_speech_tokens,
            "window_id_convention": "<sample_id>#w<index>, the same ids analysis.e21_window_pairing mints",
        },
        "speech_token_rule": {
            "rule": "n_tokens = 13 * ceil(audio_seconds)",
            "provenance": (
                "the mmproj encoder's one-second window rule certified by "
                "docs/checks/speech-aware-evidence-acquisition/"
                "2026-09-04-e21-full44-direct-baseline-v1/window-fit/window-fit.json, "
                "which reproduced all 342 sealed COST records of "
                "SAEA-E-005B-N10-zero at this exact protocol"
            ),
            "window_fit_receipt_sha256": sha256_file(WINDOW_FIT),
        },
        "comparator_envelope": {
            "source": "the same window-fit receipt",
            "text_envelope_tokens": 62,
            "worst_prompt_tokens": 1232,
            "worst_required_tokens": 2258,
            "margin_factor": 2.721,
            "note": (
                "the direct baseline's constant 62-token envelope is the floor this "
                "cell's brief is added on top of; the difference is the price of the "
                "brief, in tokens, on the flight tokenizer"
            ),
        },
        "brief_provenance_receipt": {
            "relpath": str(BRIEF_PROVENANCE.relative_to(REPO)),
            "sha256": sha256_file(BRIEF_PROVENANCE),
            "whitespace_tokens_min_median_max": [263, 969, 2565],
            "note": (
                "whitespace tokens are a LOWER BOUND on model tokens; this receipt "
                "reports both, per call, so the bound can be seen to hold"
            ),
        },
        "cells": [
            {
                "cell_id": cell_id,
                "baseline_fragment": baseline_by_cell[cell_id],
                "evidence_source": str(
                    composed_by_cell[cell_id].values["evidence_source"]
                ),
                "config_hash": composed_by_cell[cell_id].config_hash,
            }
            for cell_id in cell_ids
        ],
        "one_factor_check": {
            "differing_composed_keys": differing,
            "rule": (
                "exactly ['evidence_source'], or that plus the twin's own "
                "['evidence_pad_plan'] byte pin since 2026-09-07, asserted before "
                "any measurement"
            ),
        },
        "passes": passes,
        "wire_shape_summary": {
            "properties": list(WIRE_SHAPE_PROPERTIES),
            "requests_checked": sum(
                cell["wire_shape"]["requests_checked"]
                for entry in passes.values()
                for cell in entry["cells"].values()
            ),
            "all_properties_hold_on_every_request": True,
            "why_here_and_not_in_the_wire_check": (
                "core.model.transport.LlamaServerTransport re-runs the full I5 "
                "session liveness, pinned-binary and socket-ownership check on "
                "every send, so the REAL transport can only be driven beside a "
                "REAL resident server. The contact-free wire check therefore "
                "proves everything up to and including the payload, from the "
                "sealed trace; this block proves what the transport does with "
                "that payload, on the same requests the fit measures"
            ),
        },
        "cap_sweep": sweep or None,
        "decision": decision,
        "not_certified_here": (
            "VRAM, throughput and the flight's own go/no-go. This receipt certifies "
            "only that the protocol's largest request fits the declared slot and "
            "what the brief costs in tokens. It is not an authorization to fly: "
            "KC-E1 needs its own exposure row and the owner's own GO"
        ),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # The per-window rows are the bulk and they are evidence, not summary:
    # they move to their own file so prompt-fit.json stays readable, and the
    # summary carries their sha256 so the two cannot drift apart.
    rows_document = {
        "schema": "saea-e21-kc-e1-prompt-fit-window-rows-v1",
        "run_id": args.run_id,
        "attempt_id": str(plan.attempt_id),
        "window_id_convention": "<sample_id>#w<index>",
        "passes": {
            label: {
                "brief_max_entries_per_class": entry["brief_max_entries_per_class"],
                "full_window_pass": entry["full_window_pass"],
                "cells": {
                    cell_id: cell.pop("window_rows")
                    for cell_id, cell in entry["cells"].items()
                },
            }
            for label, entry in passes.items()
        },
    }
    rows_path = out_dir / "per-window-rows.json"
    rows_path.write_text(
        json.dumps(rows_document, indent=1, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    receipt["per_window_rows"] = {
        "relpath": rows_path.name,
        "sha256": sha256_file(rows_path),
        "rows": sum(
            len(rows)
            for entry in rows_document["passes"].values()
            for rows in entry["cells"].values()
        ),
    }
    log("wrote %s (%d bytes)" % (rows_path, rows_path.stat().st_size))

    out_path = out_dir / "prompt-fit.json"
    out_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    log("wrote %s (%d bytes)" % (out_path, out_path.stat().st_size))
    log(
        "DECISION: the whole brief (cap 0) %s at worst required %d; chosen cap %d, "
        "worst required %d against a %d-token slot (margin %d, factor %.3f)"
        % (
            "fits" if decision["whole_brief_fits_under_study_rule"] else "DOES NOT FIT",
            decision["whole_brief_worst_required_tokens"],
            chosen_cap,
            decision["final_worst_required_tokens"],
            slot_tokens,
            decision["final_margin_tokens"],
            decision["final_margin_factor"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
