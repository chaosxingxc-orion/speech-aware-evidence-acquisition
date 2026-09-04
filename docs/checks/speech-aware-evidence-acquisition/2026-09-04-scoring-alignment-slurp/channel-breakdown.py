#!/usr/bin/env python3
"""Per-microphone-channel breakdown of the sealed SLURP DEV arms (zero contact).

SLURP encodes the recording channel in the filename: ``audio-<epoch>-headset.flac``
is the close-range headset take, ``audio-<epoch>.flac`` the far-field mic-array take
of the same sentence.  This script splits every sealed arm's rows by that suffix and
reports scenario / action / intent (scen_act) exact-match accuracy per channel,
using the SAME per-sample port (``reproduction.slurp_scoring``) the official scorer
already agreed with to 1e-16 in ``rescore.json``.

No model, GPU, tool, embedding, network or audio contact.  ``split_id="devel"``,
``allow_heldout=False``: the held-out test split is never named or loaded.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(sys.argv[1]).resolve()
OUT_PATH = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
)

RUNS = Path(os.environ["SPEECHRL_DATA_DIR"]) / "runs"

ARMS = [
    ("DEV1000-M0", "SAEA-DEV1000-BASELINE-LOCK", "attempt-20260825T053342Z-dev1000m0",
     "arm1-m0-outputs.jsonl"),
    ("DEV1000-BLEND", "SAEA-DEV1000-BASELINE-LOCK", "attempt-20260825T054707Z-dev1000blend",
     "arm2-blend-outputs.jsonl"),
    ("DEV500-M0", "SAEA-DEV500-CONFIRMATORY", "attempt-20260824T203716Z-dev500m0",
     "arm1-m0-outputs.jsonl"),
    ("DEV500-BLEND", "SAEA-DEV500-CONFIRMATORY", "attempt-20260824T205527Z-dev500blend",
     "arm2-blend-outputs.jsonl"),
    ("DEV500-RANDRET", "SAEA-DEV500-CONFIRMATORY", "attempt-20260824T212928Z-dev500randret",
     "arm3-randret-outputs.jsonl"),
    ("DEV500-RANDICL", "SAEA-DEV500-CONFIRMATORY", "attempt-20260824T213948Z-dev500randicl",
     "arm4-randicl-outputs.jsonl"),
]

ROSTERS = {
    "DEV-1000": "docs/receipts/probe-samples/DEV-1000.json",
    "DEV-500": "docs/receipts/probe-samples/DEV-500.json",
    "DEV-500-NEW400": "docs/receipts/probe-samples/DEV-500-NEW400.json",
}


def channel(sample_id):
    return "headset" if sample_id.rsplit(":", 1)[1].endswith("-headset") else "far_field"


def main():
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    devel = load_slurp_split(lock, root, "devel")
    gold = {record.sample_id: record for record in devel}

    report = {
        "schema": "saea-slurp-channel-breakdown-v1",
        "zero_contact": {"model_calls": 0, "gpu_seconds": 0, "audio_seconds": 0,
                         "tool_contacts": 0, "network_contacts": 0},
        "channel_rule": (
            "SLURP recording filenames: '<stem>-headset.flac' is the close-range headset take, "
            "'<stem>.flac' the far-field mic-array take of the same sentence"
        ),
        "devel_channel_counts": dict(Counter(channel(k) for k in gold)),
        "roster_channel_counts": {},
        "arms": {},
    }
    for name, relpath in ROSTERS.items():
        doc = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
        report["roster_channel_counts"][name] = dict(
            Counter(channel(item["id"]) for item in doc["items"])
        )

    for key, run_id, attempt_id, filename in ARMS:
        path = RUNS / run_id / attempt_id / filename
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]
        buckets = {}
        for row in rows:
            sample_id = row["sample_id"]
            record = gold[sample_id]
            scenario, action, _entities, parsed = parse_slu_response(row["final_response_text"])
            bucket = buckets.setdefault(
                channel(sample_id),
                {"n": 0, "scenario_correct": 0, "action_correct": 0, "intent_correct": 0,
                 "unparsed": 0},
            )
            bucket["n"] += 1
            bucket["scenario_correct"] += int(scenario == record.scenario)
            bucket["action_correct"] += int(action == record.action)
            bucket["intent_correct"] += int(
                scenario == record.scenario and action == record.action
            )
            bucket["unparsed"] += int(not parsed)
        for bucket in buckets.values():
            n = bucket["n"]
            bucket["scenario_accuracy"] = bucket["scenario_correct"] / n
            bucket["action_accuracy"] = bucket["action_correct"] / n
            bucket["intent_accuracy"] = bucket["intent_correct"] / n
        total_n = sum(b["n"] for b in buckets.values())
        total_intent = sum(b["intent_correct"] for b in buckets.values())
        report["arms"][key] = {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "by_channel": buckets,
            "pooled_intent_accuracy": total_intent / total_n,
            "pooled_n": total_n,
        }
        print(key, {c: round(b["intent_accuracy"], 4) for c, b in sorted(buckets.items())})

    OUT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print("wrote " + str(OUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
