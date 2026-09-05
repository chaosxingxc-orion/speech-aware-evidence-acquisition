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

Usage::

    python scripts/e22_dev_esb_prompt_fit.py --write
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
                    "strict upper bound: this instruction is shorter than the one the "
                    "2026-09-04 ESB test smoke measured at 49 tokens; the smoke here "
                    "re-measures it"
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
    args = parser.parse_args()
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
