#!/usr/bin/env python3
"""Assemble the committed flight receipt for the OBS-E1 speaker-turn-unit cell.

Reads only the run's own sealed artifacts, its section 6 falsifier document and
the attached session's monitor. No model, GPU, tool, network or audio contact.

usage: e21_obs_e1_flight_receipt.py <attempt_dir> <run_id> <t0> <t1> <falsifier.json> <out.json>
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/"
    "speech-aware-evidence-acquisition"
)
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.core.session.serving import (  # noqa: E402
    summarize_monitor_file,
)

DATA_ROOT = Path(
    os.environ.get(
        "SPEECHRL_DATA_DIR",
        (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"),
    )
)
SESSION_ID = "e21-np6-c36864-20260908"
SESSION_DIR = DATA_ROOT / "serving" / SESSION_ID

CELL_CONFIG_HASH = "4e5549ee9eed1187251439cfaf4dc2b3a4da6d54ef842e6b7993cb4c4907b027"
CELL_PROTOCOL_HASH = "39b7cc2c4b071467bd876ca686ffd119ba2168563a568e32100a238b1b60d314"
SPLIT_IDENTITY = "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
PLAN_SHA256 = "0f5f013959b89fa0acc3bb366324e701cbe3a022f7b29ef3e364d621d98eb03b"

#: This carrier's realized cost at this exact geometry, one pass each. The
#: comparator's row is the basis section 7 bracketed the GPU projection from.
FAMILY_GPU_HOURS = {
    "SAEA-E21-FULL44-DIRECT-BASELINE-V2 (1,593 windows)": 0.9734,
    "SAEA-E21-KC-E1-BRIEF-44-V1 (1,593 windows)": 0.9948,
    "SAEA-E21-KU-E1C-PLACEBO-44-V1 (1,593 windows)": 1.0087,
    "SAEA-E21-FULL44-TAIL2S-V1 (1,593 windows)": 0.9765,
    "SAEA-E21-FULL44-NULL-REPLICATE-V1 (1,593 windows)": 1.0085,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> int:
    attempt_dir = Path(sys.argv[1])
    run_id = sys.argv[2]
    t0, t1 = float(sys.argv[3]), float(sys.argv[4])
    falsifier = json.loads(Path(sys.argv[5]).read_text(encoding="utf-8"))
    out = Path(sys.argv[6])

    manifest_path = attempt_dir / f"{run_id}.run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plan_path = attempt_dir / f"{run_id}.plan.json"
    if not plan_path.is_file():
        plan_path = attempt_dir / "execution-plan.json"
    outputs_path = attempt_dir / f"{run_id}.outputs.jsonl"
    trace_path = attempt_dir / f"{run_id}.trace.jsonl"
    scores_path = attempt_dir / f"{run_id}.scores.json"

    cost = manifest["cost"]
    monitor = summarize_monitor_file(
        SESSION_DIR / "monitor.jsonl", from_epoch=t0, to_epoch=t1
    )

    prompt_tokens: list[int] = []
    completion_tokens: list[int] = []
    per_call_units: dict[str, int] = {}
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        payload = record.get("payload") or {}
        if record.get("channel") == "COST":
            if payload.get("prompt_tokens") is not None:
                prompt_tokens.append(int(payload["prompt_tokens"]))
            if payload.get("completion_tokens") is not None:
                completion_tokens.append(int(payload["completion_tokens"]))
        if record.get("channel") == "MODEL_REQUEST" and not payload.get("stitch"):
            inner = payload.get("payload")
            if isinstance(inner, dict) and "sample_id" in inner:
                sample_id = str(inner["sample_id"])
                per_call_units[sample_id] = per_call_units.get(sample_id, 0) + 1

    prompt_tokens.sort()

    def quantile(values, fraction):
        if not values:
            return None
        return values[min(len(values) - 1, int(fraction * (len(values) - 1)))]

    wall = t1 - t0
    units = sum(per_call_units.values())
    config_hash = (manifest.get("config") or {}).get("config_hash")
    receipt = {
        "schema": "saea-e21-obs-e1-flight-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": run_id,
        "attempt_id": (
            manifest["attempt"]["attempt_id"]
            if isinstance(manifest.get("attempt"), dict)
            else manifest.get("attempt")
        ),
        "status": manifest["status"],
        "study_commit": manifest["study_commit"],
        "study_repo_dirt": manifest["study_repo_dirt"],
        "decides_nothing": (
            "This receipt reports the FLIGHT. The paired verdict, its intervals and the "
            "decision under section 6's rule live in verdict/result-summary.json and in "
            "docs/readiness/2026-09-08-e21-obs-speaker-turn-units-v1-verdict.md."
        ),
        "config_hash": config_hash,
        "protocol_hash": manifest["protocol_hash"],
        "identity": {
            "expected_config_hash": CELL_CONFIG_HASH,
            "expected_protocol_hash": CELL_PROTOCOL_HASH,
            "config_hash_matches_seam_receipt": config_hash == CELL_CONFIG_HASH,
            "protocol_hash_matches_seam_receipt": manifest["protocol_hash"]
            == CELL_PROTOCOL_HASH,
            "split_identity_hash_matches_comparator": (manifest.get("split") or {}).get(
                "identity_hash"
            )
            == SPLIT_IDENTITY,
            "unit_plan_sha256": PLAN_SHA256,
            "rule": (
                "The cell's composed identity was recomputed and compared against the "
                "model-free seam-v2 wire check's own recorded hashes BEFORE the first "
                "contact, as a preregistered stop condition, and is re-read here from the "
                "sealed manifest. The split identity is the comparator's, unchanged."
            ),
        },
        "split": manifest["split"],
        "plan": json.loads(plan_path.read_text(encoding="utf-8")),
        "scorers": manifest.get("scorers"),
        "legality": manifest.get("legality"),
        "transport_unit": {
            "comparator": "fixed 90-second windows, ceil(D/90) per call, 1,593 in one pass",
            "cell": "speaker-turn units from the hash-pinned v2 plan, 5,122 in one pass",
            "calls": len(per_call_units),
            "units": units,
            "per_call": dict(sorted(per_call_units.items())),
            "unit_plan_relpath": "docs/receipts/obs/e21-speaker-turn-units-v2.json",
            "unit_plan_sha256": PLAN_SHA256,
        },
        "tokens": {
            "prompt_total": sum(prompt_tokens),
            "completion_total": sum(completion_tokens),
            "comparator_prompt_total": 1935965,
            "comparator_completion_total": 439532,
            "prompt_min": prompt_tokens[0] if prompt_tokens else None,
            "prompt_p25": quantile(prompt_tokens, 0.25),
            "prompt_median": quantile(prompt_tokens, 0.5),
            "prompt_p75": quantile(prompt_tokens, 0.75),
            "prompt_p99": quantile(prompt_tokens, 0.99),
            "prompt_max": prompt_tokens[-1] if prompt_tokens else None,
            "slot_tokens": 6144,
            "worst_request_margin_factor": (
                round(6144 / prompt_tokens[-1], 4) if prompt_tokens else None
            ),
            "slot_fit_note": (
                "no unit exceeds 90 s, so the worst request stays inside the 2,258-token "
                "90-second window the slot receipt certified at 2.72x against the "
                "6,144-token slot"
            ),
        },
        "cost": {
            "calls_used": cost["calls_used"],
            "audio_seconds_used": cost["audio_seconds_used"],
            "comparator_audio_seconds_used": 141345.8526875,
            "gpu_seconds": cost["gpu_seconds"],
            "gpu_hours": round(cost["gpu_seconds"] / 3600.0, 4),
            "cpu_seconds": cost.get("cpu_seconds"),
            "latency_seconds_total": cost.get("latency_seconds_total"),
            "peak_vram_mib": cost.get("peak_vram_mib"),
            "gate_setup_seconds": cost.get("gate_setup_seconds"),
            "prompt_tokens_total": cost.get("prompt_tokens_total"),
            "completion_tokens_total": cost.get("completion_tokens_total"),
            "planned_calls": 5635,
            "planned_speech_audio_seconds": 167000,
            "planned_gpu_hours": 3.4,
            "registered_calls": 6000,
            "registered_speech_audio_seconds": 170000,
            "registered_gpu_hours": 4.0,
            "paid_api_spend": 0,
            "gpu_projection_bracket": {
                "audio_proportional_floor": 1.044,
                "contact_proportional_ceiling": 3.130,
                "basis": (
                    "the comparator's realized 0.9734 GPU-h for 1,593 contacts over "
                    "141,345.85 s at this exact geometry, scaled by the v2 plan's own "
                    "delivered audio and contact count"
                ),
            },
            "family_gpu_hours": FAMILY_GPU_HOURS,
        },
        "throughput": {
            "run_wall_seconds": round(wall, 1),
            "run_wall_minutes": round(wall / 60.0, 2),
            "units_per_minute": round(units / (wall / 60.0), 3) if wall else None,
            "comparator_windows_per_minute": 16.38,
            "realized_realtime_factor": (
                round(cost["audio_seconds_used"] / cost["gpu_seconds"], 2)
                if cost.get("gpu_seconds")
                else None
            ),
            "realtime_factor_convention": (
                "metered cut audio seconds divided by the manifest's own nvidia-smi "
                "busy-time seconds -- the convention every receipt in this family uses"
            ),
            "wall_clock_realtime_factor": (
                round(cost["audio_seconds_used"] / wall, 2) if wall else None
            ),
        },
        "serving": {
            "mode": "attached-serving-session",
            "session_id": SESSION_ID,
            "flight_started_a_server": False,
            "flight_stopped_a_server": False,
            "geometry": {
                "server_c": 36864,
                "server_np": 6,
                "slots": 6,
                "slot_tokens": 6144,
            },
            "session_receipt": {
                "path": str(SESSION_DIR / "session-receipt.json"),
                "sha256": sha256(SESSION_DIR / "session-receipt.json"),
            },
            "monitor_summary": monitor,
            "monitor_summary_basis": (
                "core.session.serving.summarize_monitor_file over the attempt's run wall "
                f"window {int(t0)}-{int(t1)}; core.driver.run_experiment_bundled writes no "
                "session-attach receipt, so head and tail idle count as parked against "
                "this flight rather than being hidden."
            ),
        },
        "saturation": {
            "saturated_unit_count": falsifier["saturated_unit_count"],
            "saturated_units": falsifier["saturated_units"],
            "skipped_unit_count": falsifier["skipped_unit_count"],
            "skipped_units": falsifier["skipped_units"],
            "max_tokens": 1024,
            "rule": (
                "reproduction.obs_loop: a slice whose completion reaches the decode cap is "
                "a TRUNCATED decode, not a transcript end, so it contributes the empty "
                "string to the stitched hypothesis and is counted instead of scored "
                "silently."
            ),
        },
        "falsifier": {
            key: falsifier[key]
            for key in (
                "schema",
                "result",
                "failures",
                "calls",
                "units",
                "cut_seconds",
                "delivered_seconds",
                "delivered_bytes",
                "oracle",
                "unit_plan",
                "prompt_tokens_per_unit",
                "completion_tokens_per_unit",
                "per_call",
            )
        },
        "artifacts": {
            "manifest": str(manifest_path),
            "manifest_sha256": sha256(manifest_path),
            "outputs": str(outputs_path),
            "outputs_sha256": sha256(outputs_path),
            "trace": str(trace_path),
            "trace_sha256": sha256(trace_path),
            "plan": str(plan_path),
            "plan_sha256": sha256(plan_path),
            **(
                {"scores": str(scores_path), "scores_sha256": sha256(scores_path)}
                if scores_path.is_file()
                else {}
            ),
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(receipt, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "units": receipt["transport_unit"]["units"],
                "calls": receipt["transport_unit"]["calls"],
                "gpu_hours": receipt["cost"]["gpu_hours"],
                "units_per_minute": receipt["throughput"]["units_per_minute"],
                "prompt_tokens_total": receipt["tokens"]["prompt_total"],
                "saturated": receipt["saturation"]["saturated_unit_count"],
                "parked_fraction": monitor.get("parked_fraction"),
                "identity": receipt["identity"],
                "out": str(out),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
