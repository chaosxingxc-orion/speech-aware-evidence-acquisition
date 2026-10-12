#!/usr/bin/env python3
"""Build E21-LOOP-1's selective re-listen plan and its seeded-random form twin.

Exposure row ``SAEA-E21-MF-LOOP-1-PREP-V1`` (``model-free-check``). **Zero
model, GPU, server, tokenizer, tool, embedder, network, audio-decode and
paid-API contacts.** The only inputs are the sealed comparator's own trace and
outputs, the ConEC participant rosters through the registered reader, and the
registered gold-free judges. No reference transcript, no ``wer_tags`` sidecar
and no score file is opened, so the plan carries no information the flight
could not have computed for itself at run time.

The two plans
--------------
``--plan judges`` -- one re-listen unit per FLAGGED window: the union of that
window's judge flags, widened by the context margin on each side, floored at
the minimum length and clamped to the window, with the half-open range of the
window's own pass-1 words the cut corresponds to.

``--plan twin`` -- the FORM CONTROL. Per call it takes the SAME MULTISET of
re-cut durations the judges' plan produced and places them longest first, each
into a uniformly random unused window of that call able to carry it, at a
uniformly random offset inside it (seeded RNG). So the twin matches the arm on
contacts per call, on delivered audio per call and on the re-cut duration
multiset per call, and differs on exactly one thing: **where it listens.** That
is the control for "fewer, targeted contacts": if the arm's gain survives
against it, targeting is what bought the gain; if it does not, the gain was the
second look.

Usage (WSL2)::

    python scripts/build_e21_relisten_plan.py --plan judges --out configs/obs/...
    python scripts/build_e21_relisten_plan.py --plan twin   --out configs/obs/...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    e21_loop_flags as flags_module,
)
from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    e21_relisten_plan as rp,
)
from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    e21_window_pairing as wp,
)
from speech_aware_evidence_acquisition.analysis.e21_speaker_turn_units import (  # noqa: E402
    unit_id as mint_unit_id,
)
from speech_aware_evidence_acquisition.core.base import JUDGES  # noqa: E402
from speech_aware_evidence_acquisition.core import policies as _policies  # noqa: E402,F401
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    load_lock,
    umbrella_lock_path,
)

EXPOSURE_ROW = "SAEA-E21-MF-LOOP-1-PREP-V1"
SEALED_RUN = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
SEALED_ATTEMPT = "attempt-20260904T233816Z-bcd338"

#: The campaign's own seed, reused so two builds of the twin cannot silently
#: differ (the same discipline ``analysis.e21_window_pairing`` applies to its
#: bootstrap seed).
TWIN_SEED = 20260903

DEFAULT_DATA_ROOT = Path(
    os.environ.get(
        "SPEECHRL_DATA_DIR",
        (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"),
    )
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--plan", choices=("judges", "twin"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--context-margin-seconds",
        type=float,
        default=rp.DEFAULT_CONTEXT_MARGIN_SECONDS,
    )
    parser.add_argument(
        "--min-relisten-seconds", type=float, default=rp.MIN_RELISTEN_SECONDS
    )
    parser.add_argument(
        "--max-distance",
        type=float,
        default=None,
        help="near-miss band ceiling; the judge's own default when omitted",
    )
    args = parser.parse_args(argv)

    started = time.time()
    attempt_dir = args.data_root / "runs" / SEALED_RUN / SEALED_ATTEMPT
    outputs_path = attempt_dir / f"{SEALED_RUN}.outputs.jsonl"
    trace_path = attempt_dir / f"{SEALED_RUN}.trace.jsonl"
    outputs_text = {
        str(row["sample_id"]): str(row["text"])
        for row in (
            json.loads(line)
            for line in outputs_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    windows = wp.stitched_windows_from_trace(trace_path)
    wp.assert_stitch_reproduces_outputs(windows, outputs_text)
    lock = load_lock(umbrella_lock_path(REPO_ROOT))

    judge_params: dict[str, dict[str, object]] = {}
    if args.max_distance is not None:
        judge_params["e21-brief-name-near-miss-v1"] = {
            "max_distance": args.max_distance
        }

    rng = random.Random(TWIN_SEED)
    calls: list[dict] = []
    totals = {
        "calls": 0,
        "windows": 0,
        "flagged_windows": 0,
        "units": 0,
        "recut_seconds": 0.0,
        "window_seconds": 0.0,
    }

    for sample_id in sorted(windows):
        spans = windows[sample_id]
        person_terms, org_terms = flags_module.brief_classes(
            lock, args.data_root, sample_id
        )
        parents: list[rp.ParentWindow] = []
        judge_flags: dict[int, list[tuple[int, int]]] = {}
        for position, span in enumerate(spans, start=1):
            raw_words = span.text.split()
            parents.append(
                rp.ParentWindow(
                    window_index=position,
                    start_seconds=float(span.start_seconds),
                    end_seconds=float(span.end_seconds),
                    draft_words=len(raw_words),
                )
            )
            totals["windows"] += 1
            totals["window_seconds"] += float(span.end_seconds) - float(
                span.start_seconds
            )
            if not raw_words:
                continue
            found = flags_module.window_flags(
                span.text, person_terms, org_terms, params=judge_params
            )
            union = flags_module.union_spans(found)
            if union:
                judge_flags[position] = union

        if not judge_flags:
            raise SystemExit(
                f"call {sample_id!r} carries no flagged window; the policy refuses a "
                "call with nothing to re-hear, and a roster this plan cannot cover is "
                "a stop, never a silent omission"
            )
        totals["flagged_windows"] += len(judge_flags)

        arm_units = rp.build_units(
            sample_id,
            parents,
            judge_flags,
            margin_seconds=args.context_margin_seconds,
            min_seconds=args.min_relisten_seconds,
        )
        if args.plan == "judges":
            units = arm_units
        else:
            units = _twin_units(sample_id, parents, arm_units, rng)
        rp.assert_relisten_units(
            units, parents, min_seconds=args.min_relisten_seconds
        )
        totals["units"] += len(units)
        totals["recut_seconds"] += sum(unit.duration_seconds for unit in units)
        totals["calls"] += 1

        calls.append(
            {
                "sample_id": sample_id,
                "decoded_duration_seconds": max(
                    parent.end_seconds for parent in parents
                ),
                "windows": len(parents),
                "parent_windows": [
                    {
                        "window_index": parent.window_index,
                        "start_seconds": parent.start_seconds,
                        "end_seconds": parent.end_seconds,
                        "draft_words": parent.draft_words,
                    }
                    for parent in parents
                ],
                "units": [
                    unit.as_json(unit_id=mint_unit_id(sample_id, unit.unit_index))
                    for unit in units
                ],
            }
        )

    document = rp.plan_document(
        source="judges" if args.plan == "judges" else "seeded-random",
        margin_seconds=args.context_margin_seconds,
        min_seconds=args.min_relisten_seconds,
        calls=calls,
        provenance={
            "exposure_row": EXPOSURE_ROW,
            "sealed_run_id": SEALED_RUN,
            "sealed_attempt_id": SEALED_ATTEMPT,
            "judges": [
                {
                    "id": judge_id,
                    "version": JUDGES.resolve(judge_id).version,
                    "params": judge_params.get(judge_id, {}),
                }
                for judge_id in flags_module.DRAFT_JUDGE_IDS
            ],
            "brief_max_entries_per_class": flags_module.BRIEF_MAX_ENTRIES_PER_CLASS,
            "twin_seed": TWIN_SEED if args.plan == "twin" else None,
            "totals": {
                **{key: value for key, value in totals.items()},
                "contacts_per_window": totals["units"] / totals["windows"],
            },
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )
    payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(payload)
    print(f"wrote {args.out}")
    print(f"sha256 {_sha256_bytes(payload)}")
    print(
        json.dumps(
            {
                "plan": args.plan,
                **totals,
                "mean_recut_seconds": totals["recut_seconds"] / max(totals["units"], 1),
                "elapsed_seconds": round(time.time() - started, 1),
            },
            indent=2,
        )
    )
    return 0


def _twin_units(sample_id, parents, arm_units, rng):
    """The form control: the same number of contacts and the same re-cut
    durations, at windows and offsets the RNG chose (module docstring).

    Durations are placed LONGEST FIRST, each into a uniformly random unused
    window that can actually carry it, so the twin's duration multiset equals
    the arm's EXACTLY rather than approximately. A call's last window is
    usually shorter than 90 s, and a naive draw would quietly clip a duration
    into it -- which would make the twin cheaper than the arm on the one axis
    it exists to hold fixed.
    """

    by_index = {parent.window_index: parent for parent in parents}
    unused = set(by_index)
    placed: list[tuple[int, float]] = []
    for duration in sorted(
        (unit.duration_seconds for unit in arm_units), reverse=True
    ):
        room = sorted(
            index
            for index in unused
            if by_index[index].duration_seconds >= duration - 1e-9
        )
        if room:
            chosen = room[rng.randrange(len(room))]
        else:
            # No unused window is long enough. Take the longest one left and
            # record the clip by construction rather than by silence: the
            # wire check compares the two multisets and will name it.
            chosen = max(unused, key=lambda index: by_index[index].duration_seconds)
        unused.discard(chosen)
        placed.append((chosen, duration))

    units = []
    for position, (window_index, duration) in enumerate(sorted(placed), start=1):
        parent = by_index[window_index]
        width = min(duration, parent.duration_seconds)
        offset = rng.uniform(0.0, max(parent.duration_seconds - width, 0.0))
        start = parent.start_seconds + offset
        end = min(start + width, parent.end_seconds)
        word_start, word_end = rp.predecessor_word_range(parent, start, end)
        units.append(
            rp.RelistenUnit(
                sample_id=sample_id,
                unit_index=position,
                parent_window_index=window_index,
                start_seconds=start,
                end_seconds=end,
                predecessor_word_start=word_start,
                predecessor_word_end=word_end,
            )
        )
    return tuple(units)


if __name__ == "__main__":
    raise SystemExit(main())
