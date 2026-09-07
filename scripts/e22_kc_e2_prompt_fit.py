#!/usr/bin/env python3
"""Prompt fit and pad plan for the Earnings-22 pre-meeting-brief cells (KC-E2 /
KU-E2c), before any flight.

Sibling of ``scripts/e21_kc_e1_prompt_fit.py`` for the Earnings-22 carrier and
its own ``-c 40960 -np 8`` geometry, and the executable form of section 8 of
``docs/readiness/2026-09-07-e22-kc-e2-pre-meeting-brief-v1-preregistration.md``.
It closes BOTH preconditions in one pass, because both are the same
measurement:

1. **the fit** -- does the widest request this cell would send occupy at most
   half its 5,120-token slot? Measured on the FLIGHT tokenizer, not estimated;
2. **the pad plan** -- how many neutral filler repeats each line of each arm and
   each line of each twin needs so the two sides measure identically on that same
   tokenizer (owner ruling 2026-09-06). The plan is written as a hash-pinned
   artifact under ``configs/knowledge/e22-brief-v1/`` and the flight replays it
   with no tokenizer at all.

METHOD, and why it is exact rather than a bound
-----------------------------------------------
TEXT is measured through the resident server's own non-generative routes, the
technique ``scripts/a2t_calibration_prompt_fit.py`` established and
``scripts/e22_dev_esb_prompt_fit.py`` carried to this carrier: ``POST
/apply-template`` renders the EXACT wire messages through the pinned GGUF chat
template, and ``POST /tokenize`` counts the rendered prompt around the single
opaque media marker ``GET /props`` reports. **Nothing decodes and zero tokens are
generated.**

The wire messages are not rebuilt here. They come from the REAL
``rails.task_adapter.TaskAdapter.assemble_prompt`` of the REAL
``EsbUtteranceAdapter`` this carrier's flight entry point builds, driven with the
REAL evidence blocks ``scripts/flights/run_e22_esb_cell.py`` resolves through
``core.base.EVIDENCE_SOURCES`` -- so what is measured is the flight's own request
text rather than a second spelling of it.

SPEECH is the mmproj encoder's one-second window rule ``n_tokens = 13 *
ceil(audio_seconds)``, the rule this geometry's own model fragment records and
which the 2026-09-07 encoding probes then reproduced to the token on 4,500 sealed
rows. No audio is encoded here.

WHY THE MEASUREMENT IS PER CALL AND NOT PER CLIP
-------------------------------------------------
The brief is a function of the CALL, so the 1,500 clips of this roster carry ten
distinct system messages per arm, not 1,500. The fit is therefore measured once
per call per arm -- twenty renders -- and the worst request is that arm's widest
system message plus the roster's longest clip, which is a true worst case
because the two maxima are independent.

Usage (WSL2, with the resident session up)::

    python scripts/e22_kc_e2_prompt_fit.py --write
    python scripts/e22_kc_e2_prompt_fit.py --write --write-pad-plan
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

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
    raise SystemExit("package resolves to %s, not this checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.core.class_lists import (  # noqa: E402
    PLACEBO_PAD_FILLER,
    pad_placebo,
)
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.metadata_brief import (  # noqa: E402
    DISTINCT_TWIN_FIELDS,
    PAD_PLAN_SCHEMA,
    brief_terms,
    call_source_slice,
    metadata_header_and_rows,
    pair_pad_repeats,
    prefix_counts,
    render_brief,
    select_twin_partners,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402

DEFAULT_EXPERIMENT = "e22-kc-e2-brief-dev1500-v1"
DEFAULT_DATASET = "earnings22-esb-dev1500-tail2s"
DEFAULT_MODEL = "q4km-e22-dev-esb-mmproj-gpu-04ccc72a-np8-c40960"
ARM_BASELINE = "e22-kc-e2-brief-whole-prompt"
TWIN_BASELINE = "e22-ku-e2c-brief-placebo"

CHECK = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-e22-kc-e2-brief-dev1500-v1"
)
DEFAULT_OUTPUT = CHECK / "prompt-fit" / "prompt-fit.json"
PAD_PLAN_OUT = REPO / "configs/knowledge/e22-brief-v1/pad-plan-v1.json"
DERANGEMENT_OUT = REPO / "configs/knowledge/e22-brief-v1/derangement-v1.json"
CLIP_CALL_MAP_RELPATH = "docs/receipts/artifacts/e22-dev1500-clip-call-map.json"
METADATA_RELPATH = "datasets/earnings21-22/earnings22/metadata.csv"

#: The mmproj encoder's exact one-second window rule.
SPEECH_TOKENS_PER_SECOND_WINDOW = 13
#: Two special tokens, the same allowance every sealed flight on this carrier
#: carried.
SPECIAL_TOKENS = 2
#: slot_tokens >= FIT_MULTIPLE * worst_required, this repository's own fit rule.
FIT_MULTIPLE = 2

RUNTIME_ROOT = Path("/home/chao")


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def speech_tokens(audio_seconds: float) -> int:
    return SPEECH_TOKENS_PER_SECOND_WINDOW * math.ceil(float(audio_seconds))


def log(message: str) -> None:
    print(
        "[%s] %s" % (datetime.now(tz=timezone.utc).strftime("%H:%M:%SZ"), message),
        flush=True,
    )


def load_json(path: Path) -> Mapping[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The measurement seam
# ---------------------------------------------------------------------------


class TemplateTokenCounter:
    """``text -> flight tokens``, through the pinned chat template.

    The seam ``core.metadata_brief.pair_pad_repeats`` and
    ``core.metadata_brief.select_twin_partners`` take: passing THIS counter is
    what makes the pad plan a FLIGHT-TOKEN plan rather than a whitespace one.

    Every call renders ONE system message carrying ``text`` through ``POST
    /apply-template`` and tokenizes the result through ``POST /tokenize``. The
    count returned is the rendered prompt's, minus the constant envelope an empty
    system message costs, so what the padder matches is the BRIEF's contribution
    and not the template's boilerplate. The envelope is measured once, on the
    same route, and cached.
    """

    def __init__(self, client, counts: dict[str, int]) -> None:
        self._client = client
        self._counts = counts
        self._cache: dict[str, int] = {}
        self._envelope = self._rendered_tokens("")

    def _rendered_tokens(self, text: str) -> int:
        rendered = self._client.request_json(
            "POST", "/apply-template", {"messages": [{"role": "system", "content": text}]}
        )
        self._counts["POST /apply-template"] += 1
        prompt = rendered.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise SystemExit("apply-template returned no prompt")
        response = self._client.request_json(
            "POST",
            "/tokenize",
            {"content": prompt, "add_special": False, "parse_special": True},
        )
        self._counts["POST /tokenize"] += 1
        tokens = response.get("tokens")
        if not isinstance(tokens, list):
            raise SystemExit("tokenize returned no token list")
        return len(tokens)

    def __call__(self, text: str) -> int:
        cached = self._cache.get(text)
        if cached is None:
            cached = self._rendered_tokens(text) - self._envelope
            self._cache[text] = cached
        return cached

    @property
    def envelope_tokens(self) -> int:
        return self._envelope

    @property
    def measurements(self) -> int:
        return len(self._cache)


def request_text_tokens(client, counts, messages, media_marker) -> tuple[int, str]:
    """``(text tokens, rendered prompt)`` for one arm's WHOLE wire request.

    The whole-request measurement, as opposed to the counter above: this is what
    the fit rule is applied to, and it counts every token the template emits
    around the media marker, not only the brief's own.
    """

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


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def load_inputs(root: Path) -> dict[str, Any]:
    """The roster's calls, the pinned metadata table and every call's brief.

    Zero gold: identifiers, durations and the corpus's own metadata row. No
    reference, transcript, segment table or annotation byte is opened.
    """

    clip_call = load_json(REPO / CLIP_CALL_MAP_RELPATH)
    metadata_blob = (Path(root) / METADATA_RELPATH).read_bytes()
    metadata_sha256 = sha256_bytes(metadata_blob)
    if metadata_sha256 != str(clip_call["metadata_sha256"]):
        raise SystemExit(
            "metadata table hashes to %s, not the clip-call map's %s"
            % (metadata_sha256, clip_call["metadata_sha256"])
        )
    text = metadata_blob.decode("utf-8")
    _, table_rows = metadata_header_and_rows(text)
    calls = [str(call) for call in clip_call["calls"]]
    slices = {call: call_source_slice(text, call) for call in table_rows}
    return {
        "calls": calls,
        "clip_call": {str(k): str(v) for k, v in dict(clip_call["clip_call_map"]).items()},
        "metadata_relpath": METADATA_RELPATH,
        "metadata_sha256": metadata_sha256,
        "slices": slices,
        "briefs": {call: render_brief(slice_text) for call, slice_text in slices.items()},
        "terms": {call: brief_terms(slice_text) for call, slice_text in slices.items()},
        "table_rows": sorted(table_rows),
    }


# ---------------------------------------------------------------------------
# The pad plan
# ---------------------------------------------------------------------------


def build_pad_plan(
    inputs: Mapping[str, Any],
    counter,
    *,
    committed_derangement: Mapping[str, str] | None,
    measured_on: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, str], bool]:
    """The flight-token pad plan for every roster call's (arm, twin) pair.

    The COMMITTED pairing is verified first, pair by pair, on this tokenizer. It
    is kept when every pair still matches -- so the committed artifact's sha256,
    and therefore both fragments' composed hashes, do not move for nothing. It is
    re-selected, by the same ``select_twin_partners`` rule measured on THIS
    counter, only when a pair fails; the returned flag says which happened, and a
    re-selection is a fact the receipt reports rather than a silent repair.
    """

    calls = list(inputs["calls"])
    briefs = inputs["briefs"]
    reselected = False
    partners: dict[str, str] = {}
    plans: dict[str, tuple[list[int], list[int]]] = {}

    if committed_derangement is not None:
        try:
            for call in calls:
                partner = committed_derangement[call]
                plans[call] = pair_pad_repeats(
                    briefs[call], briefs[partner], token_counter=counter
                )
                partners[call] = partner
        except Exception as error:  # noqa: BLE001 (any refusal means re-select)
            log("committed pairing failed on the flight tokenizer: %s" % error)
            partners, plans, reselected = {}, {}, True

    if not partners:
        reselected = True
        partners, plans = select_twin_partners(
            briefs_by_call=briefs,
            roster_calls=calls,
            candidate_calls=inputs["table_rows"],
            token_counter=counter,
            terms_by_call=inputs["terms"],
        )

    entries: list[dict[str, Any]] = []
    per_call: list[dict[str, Any]] = []
    for call in calls:
        partner = partners[call]
        arm_repeats, twin_repeats = plans[call]
        arm_slice = inputs["slices"][call]
        twin_slice = inputs["slices"][partner]
        padded_arm = pad_placebo(briefs[call], arm_repeats)
        padded_twin = pad_placebo(briefs[partner], twin_repeats)
        arm_prefixes = prefix_counts(padded_arm, counter)
        twin_prefixes = prefix_counts(padded_twin, counter)
        if arm_prefixes != twin_prefixes:
            raise SystemExit(
                "call %s: the padded pair does not measure equal on the flight "
                "tokenizer (%s vs %s)" % (call, arm_prefixes, twin_prefixes)
            )
        entries.append(
            {
                "role": "arm",
                "roster_call": call,
                "source_call": call,
                "source_sha256": sha256_text(arm_slice),
                "pad_repeats": arm_repeats,
                "padded_prefix_tokens": arm_prefixes,
            }
        )
        entries.append(
            {
                "role": "twin",
                "roster_call": call,
                "source_call": partner,
                "source_sha256": sha256_text(twin_slice),
                "pad_repeats": twin_repeats,
                "padded_prefix_tokens": twin_prefixes,
            }
        )
        per_call.append(
            {
                "roster_call": call,
                "twin_call": partner,
                "arm_tokens_unpadded": prefix_counts(briefs[call], counter)[-1],
                "twin_tokens_unpadded": prefix_counts(briefs[partner], counter)[-1],
                "matched_tokens": arm_prefixes[-1],
                "arm_pad_repeats": arm_repeats,
                "twin_pad_repeats": twin_repeats,
                "fields_distinct": all(
                    inputs["terms"][partner][field] != inputs["terms"][call][field]
                    for field in DISTINCT_TWIN_FIELDS
                ),
            }
        )
    document = {
        "schema": PAD_PLAN_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "for_flight_experiment": DEFAULT_EXPERIMENT,
        "filler": PLACEBO_PAD_FILLER,
        "keyed_by": (
            "source_sha256 -- the sha256 of the call's two-line metadata source slice, "
            "which is exactly the DerivedEvidenceRecord.source_sha256 the derivation "
            "registry re-proves for that item"
        ),
        "what_this_is": (
            "the per-line pad plan that makes core.evidence's e22-metadata-brief-token-"
            "matched and e22-metadata-brief-deranged-token-matched a matched PAIR on the "
            "flight tokenizer. Line i of a half grows by pad_repeats[i] whole repeats of "
            "'filler' and by nothing else, so the flight replays a measurement instead of "
            "taking one. The padder is SYMMETRIC (core.metadata_brief.pair_pad_repeats): "
            "a real Earnings-22 brief can be longer than the one it twins, so whichever "
            "side is short at a line is the side that grows."
        ),
        "measured_on": dict(measured_on),
        "derangement_reselected": reselected,
        "entries": entries,
        "per_call": per_call,
    }
    return document, partners, reselected


# ---------------------------------------------------------------------------
# The fit
# ---------------------------------------------------------------------------


def fit_block(
    *,
    geometry: Mapping[str, Any],
    worst_text_tokens: int,
    longest_seconds: float,
) -> dict[str, Any]:
    slot_tokens = int(geometry["slot_tokens"])
    max_tokens = int(geometry["max_tokens"])
    worst_speech = speech_tokens(longest_seconds)
    worst_required = worst_speech + worst_text_tokens + max_tokens + SPECIAL_TOKENS
    return {
        "slot_tokens": slot_tokens,
        "slots": int(geometry["slots"]),
        "max_tokens": max_tokens,
        "longest_audio_seconds": longest_seconds,
        "worst_speech_tokens": worst_speech,
        "worst_text_tokens": worst_text_tokens,
        "special_tokens": SPECIAL_TOKENS,
        "worst_required_tokens": worst_required,
        "margin_tokens": slot_tokens - worst_required,
        "ratio": round(slot_tokens / worst_required, 4) if worst_required else 0.0,
        "fits_strictly": slot_tokens >= worst_required,
        "satisfies_margin_rule": slot_tokens >= FIT_MULTIPLE * worst_required,
        "rule": "slot_tokens >= %d x worst_required" % FIT_MULTIPLE,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true", help="write the fit receipt")
    parser.add_argument(
        "--write-pad-plan",
        action="store_true",
        help="write configs/knowledge/e22-brief-v1/pad-plan-v1.json (and the "
        "re-selected derangement, if the committed pairing failed on this tokenizer)",
    )
    args = parser.parse_args(argv)

    from speech_aware_evidence_acquisition.core.driver.speech_native import (
        _LoopbackPromptAuditClient,
    )

    root = Path(data_root())
    inputs = load_inputs(root)
    log("%d roster calls, %d corpus calls" % (len(inputs["calls"]), len(inputs["table_rows"])))

    composed = {
        baseline: compose(REPO, args.model, args.dataset, baseline, args.experiment)
        for baseline in (ARM_BASELINE, TWIN_BASELINE)
    }
    values = composed[ARM_BASELINE].values
    geometry = values["serving_geometry"]
    port = int(str(values["base_url"]).rsplit(":", 1)[-1])
    roster = load_json(REPO / str(values["e22_esb_roster_receipt"]))
    longest = max(float(item["audio_seconds"]) for item in roster["items"])

    counts = {"GET /props": 0, "POST /apply-template": 0, "POST /tokenize": 0, "generations": 0}
    client = _LoopbackPromptAuditClient(host="127.0.0.1", port=port, timeout_seconds=180.0)
    props = client.request_json("GET", "/props", None)
    counts["GET /props"] += 1
    media_marker = props.get("media_marker")
    if not isinstance(media_marker, str) or not media_marker:
        raise SystemExit("resident props lack a media marker")
    live_slot_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
    if int(live_slot_ctx) < int(geometry["slot_tokens"]):
        raise SystemExit(
            "resident slot n_ctx %s is smaller than the fragment's declared %s"
            % (live_slot_ctx, geometry["slot_tokens"])
        )
    chat_template = props.get("chat_template")
    chat_template_sha256 = sha256_text(chat_template) if isinstance(chat_template, str) else ""
    log("props OK: slot n_ctx=%s, media marker %r" % (live_slot_ctx, media_marker))

    counter = TemplateTokenCounter(client, counts)
    log("empty-system envelope measured at %d tokens" % counter.envelope_tokens)

    committed = None
    if DERANGEMENT_OUT.is_file():
        committed = {
            str(k): str(v)
            for k, v in dict(load_json(DERANGEMENT_OUT)["derangement"]).items()
        }
    measured_on = {
        "model_fragment": args.model,
        "server_args": [str(value) for value in values["server_args"]],
        "route": "POST /apply-template + POST /tokenize (add_special false, parse_special true)",
        "chat_template_sha256": chat_template_sha256,
        "empty_system_envelope_tokens": counter.envelope_tokens,
        "metadata_relpath": inputs["metadata_relpath"],
        "metadata_sha256": inputs["metadata_sha256"],
    }
    pad_plan, partners, reselected = build_pad_plan(
        inputs, counter, committed_derangement=committed, measured_on=measured_on
    )
    log(
        "pad plan built for %d calls; derangement reselected: %s"
        % (len(inputs["calls"]), reselected)
    )

    # The widest request per arm: the widest padded brief, rendered as a whole
    # wire request through the real adapter's own prompt shape.
    per_arm: dict[str, Any] = {}
    for baseline, role in ((ARM_BASELINE, "arm"), (TWIN_BASELINE, "twin")):
        arm_values = composed[baseline].values
        instruction = str(arm_values["task_instruction"])
        widest_call = None
        widest_tokens = -1
        widest_prompt = ""
        for entry in pad_plan["entries"]:
            if entry["role"] != role:
                continue
            call = str(entry["roster_call"])
            source_call = str(entry["source_call"])
            block = pad_placebo(inputs["briefs"][source_call], entry["pad_repeats"])
            # The evidence-block HEADER is the flight's own, character for
            # character: scripts/flights/run_e22_esb_cell.py renders
            # f"[evidence {item.evidence_id}] {item.content}" and
            # core.evidence mints that id as "<transform>/<sample_id>". The
            # sample id is the CLIP, not the call, so the header carries the
            # roster's own first clip of this call -- the widest is what the fit
            # rule is applied to and clip ids are equal-width here.
            transform = (
                str(arm_values["evidence_source"])
                .replace("e22-metadata-brief-deranged-token-matched", "e22-metadata-brief-deranged-tm")
                .replace("e22-metadata-brief-token-matched", "e22-metadata-brief-tm")
            )
            clip = min(
                clip_id for clip_id, clip_call in inputs["clip_call"].items() if clip_call == call
            )
            system_text = "[evidence %s/%s] %s\n\n%s" % (transform, clip, block, instruction)
            messages = [
                {"role": "system", "content": system_text},
                {
                    "role": "user",
                    "content": [{"type": "input_audio", "media_relpath": "x.wav"}],
                },
            ]
            tokens, prompt = request_text_tokens(client, counts, messages, media_marker)
            if tokens > widest_tokens:
                widest_call, widest_tokens, widest_prompt = call, tokens, prompt
        per_arm[baseline] = {
            "role": role,
            "config_hash": composed[baseline].config_hash,
            "evidence_source": str(arm_values["evidence_source"]),
            "task_instruction_sha256": sha256_text(instruction),
            "widest_call": widest_call,
            "widest_text_tokens": widest_tokens,
            "widest_prompt_sha256": sha256_text(widest_prompt),
            "fit": fit_block(
                geometry=geometry,
                worst_text_tokens=widest_tokens,
                longest_seconds=longest,
            ),
        }
        log(
            "%s: widest text envelope %d tokens on call %s, ratio %.3f"
            % (baseline, widest_tokens, widest_call, per_arm[baseline]["fit"]["ratio"])
        )

    receipt = {
        "schema": "saea-e22-kc-e2-prompt-fit-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "contacts": {**counts, "generated_tokens": 0, "model_contacts": 0},
        "fragments": {
            "experiment": args.experiment,
            "dataset": args.dataset,
            "model": args.model,
            "baselines": [ARM_BASELINE, TWIN_BASELINE],
        },
        "server": {
            "declared_slots": int(geometry["slots"]),
            "declared_slot_tokens": int(geometry["slot_tokens"]),
            "live_slot_n_ctx": live_slot_ctx,
            "chat_template_sha256": chat_template_sha256,
            "media_marker": media_marker,
        },
        "roster": {
            "clips": len(inputs["clip_call"]),
            "calls": len(inputs["calls"]),
            "longest_audio_seconds": longest,
        },
        "per_arm": per_arm,
        "pad_plan": {
            "entries": len(pad_plan["entries"]),
            "derangement_reselected": reselected,
            "per_call": pad_plan["per_call"],
        },
        "all_fits": all(entry["fit"]["satisfies_margin_rule"] for entry in per_arm.values()),
        "all_pairs_matched": True,
        "header_residual": (
            "the two arms' evidence-block HEADERS name different transforms "
            "(e22-metadata-brief[-tm] against e22-metadata-brief-deranged[-tm]), so the "
            "whole request text is a few tokens wider for the twin even after the "
            "briefs are matched. The per-arm widest_text_tokens above measure that "
            "residual rather than hide it; it is the same residual KU-E1c reported at 7 "
            "tokens, and it exists because a twin that named the arm's transform would "
            "be indistinguishable from it in a sealed trace."
        ),
        "boundary": (
            "only GET /props, POST /apply-template and POST /tokenize are called, none "
            "of which decodes; zero tokens are generated and no media byte is opened"
        ),
    }
    print(json.dumps({k: v for k, v in receipt.items() if k != "per_arm"}, indent=2, default=str))

    if args.write_pad_plan:
        PAD_PLAN_OUT.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(pad_plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        PAD_PLAN_OUT.write_text(payload, encoding="utf-8", newline="\n")
        digest = sha256_text(payload)
        print(
            json.dumps(
                {
                    "pad_plan": str(PAD_PLAN_OUT.relative_to(REPO)),
                    "pad_plan_sha256": digest,
                    "derangement_reselected": reselected,
                    "next_step": (
                        "pin this path and sha256 as evidence_brief_pad_plan in BOTH "
                        "baseline fragments and move each evidence_source to its "
                        "-token-matched name"
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
        if reselected:
            print(
                "WARNING: the committed derangement did not hold on the flight "
                "tokenizer; re-run scripts/build_e22_brief_knowledge.py is NOT the fix "
                "-- the pairing this plan used is in its own per_call block and the "
                "derangement artifact must be rewritten from it before the twin flies",
                file=sys.stderr,
            )
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("wrote %s" % args.output)
    return 0 if receipt["all_fits"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
