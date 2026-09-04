#!/usr/bin/env python3
"""Zero-contact official-scorer re-read of the sealed SLURP DEV rosters.

Runs the PINNED, UNMODIFIED official SLURP ``scripts/evaluation/evaluate.py``
(commit 8eb16545762be97ace75334109d73824217311f1, in its own
``~/.venvs/slurp-official-eval`` environment, never modified) over the sealed
outputs of the DEV-1000 baseline lock and the DEV-500 confirmatory flight,
through the registered ``slurp-slu-official`` scorer -- which additionally
runs this study's per-sample port and asserts the two agree.

No model, GPU, tool, embedding, network or audio contact.  The held-out
``test`` split is never named, loaded or scored: ``split_id="devel"`` and
``allow_heldout`` is left at its default ``False``.

ROW-SHAPE NOTE (reported, not patched): the August flights predate the
canonical ``core.flight.FlightRuntime.seal`` outputs contract.  They carry
``final_response_text`` and no ``run-manifest.json``, so neither
``core.scoring_batch`` (which requires a ``*.run-manifest.json``) nor the
registered scorer (which reads ``text``) can consume them directly.  This
script therefore writes a 1:1 KEY-RENAME projection of the sealed bytes --
``sample_id`` unchanged, ``text`` = the sealed ``final_response_text``
verbatim, nothing else read by the scorer -- records the source and
projection SHA-256, and scores the projection.  No response text is altered.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(sys.argv[1]).resolve()
OUT_PATH = Path(sys.argv[2]).resolve()
WORK_DIR = Path(sys.argv[3]).resolve()
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.base import SCORERS  # noqa: E402
import speech_aware_evidence_acquisition.core.scorers  # noqa: F401,E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import sha256_file  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (  # noqa: E402
    SLURP_OFFICIAL_COMMIT,
    PredictedSlurpSample,
    official_evaluator_root,
    run_official_evaluate,
    write_official_inputs,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
)

RUNS = Path(os.environ["SPEECHRL_DATA_DIR"]) / "runs"

ARMS = [
    ("DEV1000-M0", "SAEA-DEV1000-BASELINE-LOCK", "attempt-20260825T053342Z-dev1000m0",
     "arm1-m0-outputs.jsonl", "DEV-1000", "direct baseline (M0)"),
    ("DEV1000-BLEND", "SAEA-DEV1000-BASELINE-LOCK", "attempt-20260825T054707Z-dev1000blend",
     "arm2-blend-outputs.jsonl", "DEV-1000", "locked knowledge cell (BLEND)"),
    ("DEV500-M0", "SAEA-DEV500-CONFIRMATORY", "attempt-20260824T203716Z-dev500m0",
     "arm1-m0-outputs.jsonl", "DEV-500", "direct baseline (M0)"),
    ("DEV500-BLEND", "SAEA-DEV500-CONFIRMATORY", "attempt-20260824T205527Z-dev500blend",
     "arm2-blend-outputs.jsonl", "DEV-500", "knowledge cell (BLEND)"),
    ("DEV500-RANDRET", "SAEA-DEV500-CONFIRMATORY", "attempt-20260824T212928Z-dev500randret",
     "arm3-randret-outputs.jsonl", "DEV-500-NEW400", "negative control: random retrieval"),
    ("DEV500-RANDICL", "SAEA-DEV500-CONFIRMATORY", "attempt-20260824T213948Z-dev500randicl",
     "arm4-randicl-outputs.jsonl", "DEV-500-NEW400", "negative control: random ICL"),
]

ROSTERS = {
    "DEV-1000": "docs/receipts/probe-samples/DEV-1000.json",
    "DEV-500": "docs/receipts/probe-samples/DEV-500.json",
    "DEV-500-NEW400": "docs/receipts/probe-samples/DEV-500-NEW400.json",
}


def read_sealed_rows(path):
    text = Path(path).read_text(encoding="utf-8")
    lines = [line for line in text.split("\n") if line]
    return [json.loads(line) for line in lines]


def project(rows, dest):
    dest = Path(dest)
    with dest.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    {"sample_id": row["sample_id"], "text": row["final_response_text"]},
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    return dest


def main():
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    rosters = {}
    for name, relpath in ROSTERS.items():
        path = REPO_ROOT / relpath
        doc = json.loads(path.read_text(encoding="utf-8"))
        rosters[name] = {
            "receipt": relpath,
            "receipt_sha256": sha256_file(path),
            "n_items": doc["n_items"],
            "split": doc["split"],
            "split_role": doc["split_role"],
            "split_identity_hash": doc["split_identity_hash"],
            "ids": [item["id"] for item in doc["items"]],
        }

    devel_records = load_slurp_split(lock, root, "devel")
    devel_by_id = {record.sample_id: record for record in devel_records}

    report = {
        "schema": "saea-slurp-scoring-alignment-v1",
        "zero_contact": {
            "model_calls": 0,
            "gpu_seconds": 0,
            "audio_seconds": 0,
            "tool_contacts": 0,
            "network_contacts": 0,
        },
        "evaluator": {
            "commit": SLURP_OFFICIAL_COMMIT,
            "root": str(official_evaluator_root(root)),
            "average": "micro",
        },
        "split_discipline": {
            "split_id": "devel",
            "allow_heldout": False,
            "test_split_touched": False,
            "devel_sentences": len({record.utterance_id for record in devel_records}),
            "devel_recordings": len(devel_records),
            "audio_subdir": "slurp_real",
            "synthetic_rows": 0,
            "recording_filename_prefixes": sorted(
                {record.sample_id.rsplit(":", 1)[1].split("-")[0] for record in devel_records}
            ),
        },
        "rosters": {
            name: {key: value for key, value in data.items() if key != "ids"}
            for name, data in rosters.items()
        },
        "arms": {},
    }

    for key, run_id, attempt_id, filename, roster_name, description in ARMS:
        source = RUNS / run_id / attempt_id / filename
        rows = read_sealed_rows(source)
        projection = project(rows, WORK_DIR / (key + ".projection.jsonl"))

        roster_ids = set(rosters[roster_name]["ids"])
        predicted_ids = {row["sample_id"] for row in rows}
        missing = sorted(roster_ids - predicted_ids)
        extra = sorted(predicted_ids - roster_ids)

        result = SCORERS.resolve("slurp-slu-official")(projection, lock, root)
        aggregate = result["aggregate"]
        per_sample = result["per_sample"]
        unparsed = [entry["sample_id"] for entry in per_sample if not entry["parsed"]]
        intent_correct = sum(int(entry["scenario_action_exact"]) for entry in per_sample)
        scenario_correct = sum(int(entry["scenario_exact"]) for entry in per_sample)
        action_correct = sum(int(entry["action_exact"]) for entry in per_sample)

        n_scored = len(per_sample)
        n_roster = len(roster_ids)
        official = dict(aggregate["official"])
        official.pop("stdout", None)
        arm = {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "description": description,
            "roster": roster_name,
            "sealed_outputs": str(source),
            "sealed_outputs_sha256": sha256_file(source),
            "sealed_outputs_rows": len(rows),
            "projection_sha256": sha256_file(projection),
            "projection_rule": (
                "1:1 key rename of the sealed rows: {sample_id, text=final_response_text}; "
                "no response text altered, no row added or dropped"
            ),
            "n_gold_roster": n_roster,
            "n_predicted": n_scored,
            "n_gold_rows_without_prediction": len(missing),
            "gold_rows_without_prediction": missing[:20],
            "n_predictions_outside_roster": len(extra),
            "predictions_outside_roster": extra[:20],
            "n_unparsed_responses": len(unparsed),
            "unparsed_sample_ids": unparsed[:20],
            "official": official,
            "port_micro": aggregate["port_micro"],
            "identity_check": aggregate["identity_check"],
            "scorer_version": aggregate["scorer_version"],
            "counts_on_scored_rows": {
                "scenario_correct": scenario_correct,
                "action_correct": action_correct,
                "intent_correct": intent_correct,
            },
            "unanswered_counted_wrong": {
                "denominator": n_roster,
                "scenario_accuracy": scenario_correct / n_roster if n_roster else 0.0,
                "action_accuracy": action_correct / n_roster if n_roster else 0.0,
                "intent_accuracy": intent_correct / n_roster if n_roster else 0.0,
                "note": (
                    "same numerators as the official run, denominator forced to the full "
                    "roster; identical to the official numbers when nothing is missing"
                ),
            },
        }
        report["arms"][key] = arm
        print("scored " + key + ": n=" + str(n_scored)
              + " intent=" + str(official["intent_accuracy"]))

    # Hazard demonstration: evaluate.py silently SKIPS gold rows that carry no
    # prediction.  Same 1,000 DEV-1000 M0 predictions, gold widened to the whole
    # 8,690-recording devel split: the printed scores do not move.
    m0_rows = read_sealed_rows(
        RUNS / "SAEA-DEV1000-BASELINE-LOCK" / "attempt-20260825T053342Z-dev1000m0"
        / "arm1-m0-outputs.jsonl"
    )
    predictions = []
    for row in m0_rows:
        scenario, action, entities, _parsed = parse_slu_response(row["final_response_text"])
        predictions.append(
            PredictedSlurpSample(
                sample_id=row["sample_id"],
                scenario=scenario,
                action=action,
                entities=tuple(entities),
            )
        )
    missing_from_devel = [
        prediction.sample_id
        for prediction in predictions
        if prediction.sample_id not in devel_by_id
    ]
    with tempfile.TemporaryDirectory(prefix="saea-slurp-hazard-") as tmp:
        gold_path, pred_path = write_official_inputs(devel_records, predictions, Path(tmp))
        wide = run_official_evaluate(
            gold_path, pred_path, evaluator_root=official_evaluator_root(root)
        )
    report["skip_hazard_demonstration"] = {
        "predictions": len(predictions),
        "predictions_not_in_devel": len(missing_from_devel),
        "gold_rows": len(devel_records),
        "gold_rows_without_prediction": len(devel_records) - len(predictions),
        "scenario_accuracy": wide.scenario_accuracy,
        "action_accuracy": wide.action_accuracy,
        "intent_accuracy": wide.intent_accuracy,
        "slu_f1": wide.slu_f1,
        "span_f1": wide.span_f1,
        "reading": (
            "identical to the roster-scoped DEV1000-M0 numbers: the evaluate.py loop "
            "`if gold_id in pred_examples` never penalises an unanswered gold row"
        ),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print("wrote " + str(OUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
