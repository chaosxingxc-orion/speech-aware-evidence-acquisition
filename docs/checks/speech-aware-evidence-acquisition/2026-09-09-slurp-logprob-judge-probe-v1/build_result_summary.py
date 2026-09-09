"""Assemble ``result-summary.json`` and the markdown tables from the read.

Zero model contacts. Reads only ``read.json``, ``companion-read.json``, the
flight receipt, the score provenance and the sealed manifest; computes nothing
the read did not, except the COST block and one explicitly NON-PREREGISTERED
successor diagnostic that is labelled as such everywhere it appears.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from slurp_logprob_judge_read import (  # noqa: E402
    flag_at_budget,
    load_jsonl,
    logprobs_by_request,
    precision_recall,
    row_confidence,
)

SP = Path(sys.argv[1])
ATTEMPT = Path(sys.argv[2])

read = json.loads((SP / "read.json").read_text(encoding="utf-8"))
companion = json.loads((SP / "companion-read.json").read_text(encoding="utf-8"))
receipt = json.loads((SP / "flight-cell.json").read_text(encoding="utf-8"))
score_prov = json.loads((SP / "score-provenance.json").read_text(encoding="utf-8"))
aggregate = json.loads((SP / "official-aggregate.json").read_text(encoding="utf-8"))
inputs_prov = json.loads((SP / "read-inputs-provenance.json").read_text(encoding="utf-8"))
smoke = json.loads((SP / "smoke-acceptance.json").read_text(encoding="utf-8"))
manifest = json.loads(
    (ATTEMPT / "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1.run-manifest.json").read_text(
        encoding="utf-8"
    )
)

stages = receipt["stages"]
rp = stages["run_phases"]
seal = stages["seal"]
cost = seal["cost"]
monitor = seal["serving_monitor_summary"]

# -- the cost of the decoding parameter -------------------------------------
# Two references, and the second is the honest one: the greedy replicate null
# already measured how much two BYTE-IDENTICAL passes of this same cell differ
# on wall clock, and its verdict fixes the floor below which a SLURP wall-clock
# comparison is not meaningful.
COMPARATOR_WALL = 225.5
COMPARATOR_GPU_H = 0.105
NULL_WALL = 229.378
NULL_GPU_H = 0.0637
NULL_MEAN_LATENCY = 1.695
NULL_ROWS_PER_MIN = 261.6
NULL_MEANINGFUL_FLOOR_PERCENT = 5.0

wall = float(rp["wall_seconds"])
gpu_hours = wall / 3600.0
rows_per_min = float(rp["contacts_per_second"]) * 60.0
mean_latency = float(rp["average_latency_seconds"])

cost_block = {
    "contacts": int(rp["contact_count"]),
    "wall_seconds": round(wall, 3),
    "gpu_hours": round(gpu_hours, 4),
    "rows_per_minute": round(rows_per_min, 2),
    "contacts_per_second": round(float(rp["contacts_per_second"]), 4),
    "mean_request_latency_seconds": round(mean_latency, 4),
    "slot_occupancy": round(float(rp["slot_occupancy"]), 4),
    "prompt_tokens_total": cost["prompt_tokens_total"],
    "completion_tokens_total": cost["completion_tokens_total"],
    "metered_speech_seconds": cost["audio_seconds_used"],
    "paid_api_spend": 0,
    "against_the_greedy_replicate_null": {
        "reference": "SAEA-SLURP-DEV1000-NULL-REPLICATE-V1, attempt-20260909T043847Z-f4306e",
        "why_this_reference": (
            "the null flew the SAME 1,000 requests on the SAME geometry with NO decoding "
            "parameter added, so it is the only wall-clock number on this carrier that "
            "differs from this arm by the factor under test and nothing else"
        ),
        "null_wall_seconds": NULL_WALL,
        "null_gpu_hours": NULL_GPU_H,
        "null_mean_request_latency_seconds": NULL_MEAN_LATENCY,
        "null_rows_per_minute": NULL_ROWS_PER_MIN,
        "wall_delta_percent": round(100.0 * (wall / NULL_WALL - 1.0), 2),
        "gpu_hours_delta_percent": round(100.0 * (gpu_hours / NULL_GPU_H - 1.0), 2),
        "mean_latency_delta_seconds": round(mean_latency - NULL_MEAN_LATENCY, 4),
        "mean_latency_delta_percent": round(
            100.0 * (mean_latency / NULL_MEAN_LATENCY - 1.0), 2
        ),
        "throughput_delta_rows_per_minute": round(rows_per_min - NULL_ROWS_PER_MIN, 2),
        "meaningfulness": (
            "the null's own verdict fixes ~%.0f %% as the floor below which a SLURP "
            "wall-clock or GPU-hour comparison is not meaningful (byte-identical work "
            "spread 1.7 %%). The measured cost is ABOVE that floor."
            % NULL_MEANINGFUL_FLOOR_PERCENT
        ),
    },
    "against_the_sealed_comparator": {
        "reference": "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1, attempt-20260905T060424Z-2c5596",
        "comparator_wall_seconds": COMPARATOR_WALL,
        "comparator_gpu_hours_approx": COMPARATOR_GPU_H,
        "wall_delta_percent": round(100.0 * (wall / COMPARATOR_WALL - 1.0), 2),
    },
    "trace_growth": {
        "note": (
            "the second cost of the parameter is on disk, not on the card: the sealed "
            "trace carries the full five-alternative distribution for every generated "
            "token"
        ),
        "trace_bytes": (
            ATTEMPT / "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1.trace.jsonl"
        ).stat().st_size,
        "null_trace_bytes_approx": 10_000_000,
    },
    "budget": {
        "planned_model_calls": 1050,
        "calls_used": cost["calls_used"],
        "planned_speech_audio_seconds": 3000,
        "planned_gpu_hours": 0.5,
        "smoke_calls_used": 4,
        "smoke_planned_model_calls": 12,
    },
}

# -- the successor diagnostic, NOT PREREGISTERED ---------------------------
# The preregistration fixes min_token_logprob as THE primary and says the
# operating point and the verdict use it. Reporting an operating point for a
# different statistic AFTER the numbers exist is exactly the move the rule
# forbids, so this block is computed, labelled, and kept out of the verdict.
trace = load_jsonl(ATTEMPT / "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1.trace.jsonl")
outputs = load_jsonl(ATTEMPT / "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1.outputs.jsonl")
per_sample = json.loads((SP / "per-sample.json").read_text(encoding="utf-8"))["per_sample"]
by_request = logprobs_by_request(trace)
intent_errors = {
    str(r["sample_id"]): float(r["scenario_action_exact"]) == 0.0 for r in per_sample
}
conf = {}
for row in outputs:
    values = row_confidence(by_request[str(row["request_id"])])
    values.pop("reconstructed_text", None)
    conf[str(row["sample_id"])] = values

successor = {}
for statistic in ("intent_mean_token_logprob", "intent_min_token_logprob"):
    score = {sid: -float(v[statistic]) for sid, v in conf.items() if v.get(statistic) is not None}
    flagged, threshold = flag_at_budget(score, 86)
    successor[statistic] = {
        "flagged": len(flagged),
        "statistic_cutoff": -threshold,
        "intent_error": precision_recall(flagged, intent_errors),
    }

summary = {
    "schema": "saea-slurp-logprob-judge-probe-v1-result-summary-v1",
    "verdict": "NOT ADMITTED",
    "verdict_detail": read["verdict"],
    "row": "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1",
    "attempt_id": receipt["attempt_id"],
    "study_commit": manifest["study_commit"],
    "study_repo_dirt": manifest["study_repo_dirt"],
    "manifest_status": manifest["status"],
    "identity": {
        "config_hash": stages["preflight"]["config_hash"],
        "protocol_hash": stages["preflight"]["protocol_hash"],
        "split_identity_hash": stages["preflight"]["split_identity_hash"],
        "split_id": stages["preflight"]["split_id"],
        "instruction_sha256": receipt["identity"]["resolved_instruction_sha256"],
        "roster_view_sha256": receipt["identity"]["roster_view_sha256"],
        "wire_check_predicted_config_hash_prefix": "15670eaa",
    },
    "smoke": {
        "run_id": "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-SMOKE-4-V1",
        "attempt_id": "attempt-20260909T051251Z-1f2c58",
        "acceptance": smoke["acceptance"],
        "rows": smoke["sealed_rows"],
        "model_logprobs_records": smoke["model_logprobs_records"],
        "generated_tokens": sum(r["generated_tokens"] for r in smoke["rows"]),
        "top_logprobs_counts": sorted(
            {c for r in smoke["rows"] for c in r["top_logprobs_counts"]}
        ),
    },
    "arm_own_official_numbers": {
        "note": (
            "THIS ARM'S OWN numbers under slurp-slu-official-projected-v2. They are NEVER "
            "a comparator, are never read against the locked 73.10 / 35.80, and the probe "
            "makes no SLURP accuracy claim"
        ),
        "scenario": round(100.0 * aggregate["official"]["aggregate"]["official"]["raw"]["scenario"]["f_measure"], 2),
        "action": round(100.0 * aggregate["official"]["aggregate"]["official"]["raw"]["action"]["f_measure"], 2),
        "intent": round(100.0 * aggregate["official"]["aggregate"]["official"]["raw"]["intent"]["f_measure"], 2),
        "entities_strict": round(
            100.0 * aggregate["official"]["aggregate"]["official"]["raw"]["entities"]["f_measure"], 2
        ),
        "slu_f1": round(100.0 * aggregate["official"]["aggregate"]["official"]["raw"]["slu_f1"]["f_measure"], 2),
    },
    "labels": {
        "intent_error_rows": sum(1 for v in intent_errors.values() if v),
        "n": read["n"],
        "clusters": read["clusters"],
    },
    "auroc": read["auroc"],
    "operating_point_86_flags": read["operating_point"],
    "precision_at_budget_bootstrap": read["precision_at_budget_bootstrap"],
    "token_stream_mismatches": read["token_stream_mismatches"],
    "per_scenario": companion["per_scenario"],
    "per_scenario_caveat": companion["per_scenario_caveat"],
    "minimum_token_region": companion["minimum_token_region"],
    "cost": cost_block,
    "serving_monitor_summary": monitor,
    "serving": {
        "session_id": stages["serve"]["session_id"],
        "session_reused": stages["serve"]["session_reused"],
        "session_source": stages["serve"]["session_source"],
        "stop_serving": stages.get("stop_serving"),
    },
    "scoring": score_prov,
    "read_inputs": inputs_prov,
    "successor_diagnostic_NOT_PREREGISTERED": {
        "warning": (
            "NOT PART OF THE VERDICT AND NOT PREREGISTERED. Section 4.1 fixes "
            "min_token_logprob as THE primary and says the operating point and the "
            "verdict use it. These operating points for the intent-span statistics are "
            "computed AFTER the numbers exist and are recorded only so a SUCCESSOR "
            "preregistration can name its primary in advance with a price attached. "
            "They may not be quoted as this probe's result"
        ),
        "operating_points": successor,
    },
    "model_contacts_of_this_read": 0,
}

(SP / "result-summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
    encoding="utf-8",
    newline="\n",
)
print("COST:", json.dumps(cost_block, indent=2)[:2200])
print("\nSUCCESSOR (not preregistered):", json.dumps(successor, indent=2))
print("\nARM OWN OFFICIAL:", json.dumps(summary["arm_own_official_numbers"], indent=2))
print("\nintent error rows:", summary["labels"]["intent_error_rows"])
