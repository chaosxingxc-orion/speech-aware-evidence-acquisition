#!/usr/bin/env python3
"""Expert-offload placement fit for the Audio2Tool Q8_0 quantization probe.

Preregistration prerequisite 4 (``docs/readiness/
2026-09-04-a2t-q8-quantization-probe-v1-preregistration.md`` sections 3 and 4):
the Q8_0 decoder (32,484,494,336 bytes) cannot be resident on a 24,463 MiB
card, so the probe serves it with ``-ngl 999`` plus ``--n-cpu-moe N`` -- the
Mixture-of-Experts tensors of the FIRST ``N`` layers stay in host RAM while
attention, norms, embeddings, shared parts and the remaining experts sit on
the GPU.

``N`` is fixed model-free, by a VRAM fit rule, BEFORE any generation:

* start from ``--cpu-moe`` (every expert layer on the CPU);
* lower ``N`` in steps of 4 while a zero-token server start still leaves at
  least ``--min-free-mib`` free on the card at the declared serving geometry;
* the largest GPU-resident share that satisfies the rule is the value.

Each trial starts the runtime-receipt-pinned llama-server, reads ``GET
/props`` (the only route called; it decodes nothing), measures free and used
device memory with ``nvidia-smi``, and stops the server with its own stop
receipt. Zero tokens are generated and no completion endpoint is touched.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src python
    scripts/a2t_q8_placement_fit.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if (
    Path(_pkg.__file__ or "")
    != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"
):
    raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.core.driver.speech_native import (  # noqa: E402
    _LoopbackPromptAuditClient,
)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402

RUN_ID = "SAEA-A2T-Q8-PLACEMENT-FIT-V1"
FLIGHT_RUN_ID = "SAEA-A2T-Q8-QUANTIZATION-PROBE-V1"
SPLIT_IDENTITY_HASH = "11091b38ae9d53530952af632636d7e79a614350213e10c6c26583c37f85846b"
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q8-featcache-04ccc72a.json"
MODEL_LOCK_KEY = "qwen3-omni-30b-a3b-instruct-gguf"
RUNTIME_ROOT = Path("/home/chao")
MODEL_ROOT = Path("/home/chao")
FEAT_CACHE_DIR = "/home/chao/feat-cache/audio2tool-q4km-04ccc72a"

# The serving geometry the sealed R-official-raw cell served, held fixed: this
# probe varies the decoder quantization and NOTHING else about the request or
# the KV cache.
BASE_SERVER_ARGS: tuple[str, ...] = (
    "-c",
    "49152",
    "-np",
    "3",
    "-fa",
    "on",
    "-ngl",
    "999",
    "-ctk",
    "q8_0",
    "-ctv",
    "q8_0",
)
SLOTS = 3
SLOT_TOKENS = 16384

PLAN_CALLS = 1
PLAN_AUDIO = 1
PLAN_GPU_HOURS = 1.0

OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-q8-quantization-probe-400-v1"
    / "placement"
)


def log(message: str) -> None:
    print("[%s] %s" % (datetime.now(timezone.utc).strftime("%H:%M:%SZ"), message), flush=True)


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nvidia_memory() -> dict[str, int]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=memory.total,memory.used,memory.free",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    total, used, free = (int(part.strip()) for part in completed.stdout.strip().split(","))
    return {"total_mib": total, "used_mib": used, "free_mib": free}


def enforced_power_limit_watts() -> float:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=enforced.power.limit",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return float(completed.stdout.strip().splitlines()[0])


def host_memory() -> dict[str, int]:
    fields: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        name, _, rest = line.partition(":")
        value = rest.strip().split()
        if value and value[0].isdigit():
            fields[name] = int(value[0])
    return {
        "total_mib": fields.get("MemTotal", 0) // 1024,
        "available_mib": fields.get("MemAvailable", 0) // 1024,
        "free_mib": fields.get("MemFree", 0) // 1024,
    }


def process_rss_mib(pid: int) -> int:
    try:
        for line in Path("/proc/%d/status" % pid).read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


def placement_argv(offload: Mapping[str, object]) -> list[str]:
    """The fragment's server args plus the trial's expert-offload flag."""

    argv = list(BASE_SERVER_ARGS)
    if offload["flag"] == "--cpu-moe":
        argv.append("--cpu-moe")
    else:
        argv.extend(["--n-cpu-moe", str(int(offload["n"]))])
    return argv


def trial_sequence(start: int, step: int) -> list[dict[str, object]]:
    """``--cpu-moe`` first, then descending ``--n-cpu-moe`` in steps of ``step``."""

    trials: list[dict[str, object]] = [
        {"flag": "--cpu-moe", "n": start, "label": "--cpu-moe (all expert layers on CPU)"}
    ]
    value = start - step
    while value > 0:
        trials.append({"flag": "--n-cpu-moe", "n": value, "label": "--n-cpu-moe %d" % value})
        value -= step
    return trials


def run_trial(
    offload: Mapping[str, object],
    *,
    runtime_receipt: Mapping[str, object],
    root: Path,
    port: int,
    run_dir: Path,
    attempt_id: str,
) -> dict[str, object]:
    argv = placement_argv(offload)
    baseline = nvidia_memory()
    log("trial %s: spawning %s" % (offload["label"], " ".join(argv)))
    started_at = time.time()
    session = start_session(
        runtime_root=RUNTIME_ROOT,
        data_root=root,
        runtime_receipt=runtime_receipt,
        host="127.0.0.1",
        port=port,
        session_id="%s-%s-%s" % (RUN_ID, attempt_id, str(offload["n"])),
        extra_argv=argv,
        extra_env={"LLAMA_MTMD_FEAT_CACHE_DIR": FEAT_CACHE_DIR},
        receipt_path=run_dir / ("session-%s.receipt.json" % offload["n"]),
        server_log_path=run_dir / ("session-%s.server.log" % offload["n"]),
        role=str(runtime_receipt.get("role", "legacy")),
        model_root=MODEL_ROOT,
        ready_timeout_seconds=2400.0,
    )
    load_seconds = time.time() - started_at
    resident: dict[str, object] = {}
    props_ok = False
    live_slot_ctx = None
    try:
        client = _LoopbackPromptAuditClient(host="127.0.0.1", port=port, timeout_seconds=300.0)
        props = client.request_json("GET", "/props", None)
        props_ok = True
        live_slot_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
        resident = {
            "device_memory": nvidia_memory(),
            "host_memory": host_memory(),
            "server_rss_mib": process_rss_mib(int(session.pid)),
        }
    finally:
        stop_out = stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
            receipt_path=run_dir / ("session-%s.stop-receipt.json" % offload["n"]),
            force_after_timeout=True,
        )
    time.sleep(3.0)
    after = nvidia_memory()
    device = resident.get("device_memory") or {}
    log(
        "trial %s: load %.1fs, free %s MiB, used %s MiB, slot n_ctx %s"
        % (
            offload["label"],
            load_seconds,
            device.get("free_mib"),
            device.get("used_mib"),
            live_slot_ctx,
        )
    )
    return {
        "offload_flag": offload["flag"],
        "n_cpu_moe": int(offload["n"]),
        "label": offload["label"],
        "server_args": argv,
        "load_seconds": round(load_seconds, 3),
        "props_ok": props_ok,
        "live_slot_n_ctx": live_slot_ctx,
        "declared_slot_tokens": SLOT_TOKENS,
        "device_memory_before_mib": baseline,
        "device_memory_resident_mib": device,
        "device_memory_after_stop_mib": after,
        "host_memory_resident_mib": resident.get("host_memory"),
        "server_rss_mib": resident.get("server_rss_mib"),
        "stop_signal": stop_out.get("termination_signal"),
        "stop_forced": bool(stop_out.get("forced")),
        "generated_tokens": 0,
        "completion_endpoint_touched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--start", type=int, default=48)
    parser.add_argument("--step", type=int, default=4)
    parser.add_argument("--min-free-mib", type=int, default=1536)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    root = data_root()
    description = {
        "measurement": "q8 expert-offload placement fit",
        "base_server_args": list(BASE_SERVER_ARGS),
        "model_lock_key": MODEL_LOCK_KEY,
        "runtime_receipt": RUNTIME_RECEIPT_RELPATH,
        "min_free_mib": int(args.min_free_mib),
        "step": int(args.step),
        "start": int(args.start),
    }
    attempt_id = "attempt-%s-a2tq8placement" % datetime.now(tz=timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    plan = ExecutionPlan(
        run_id=args.run_id,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=SPLIT_IDENTITY_HASH,
        planned_model_calls=PLAN_CALLS,
        planned_gpu_hours=PLAN_GPU_HOURS,
        planned_speech_audio_seconds=PLAN_AUDIO,
        protocol_hash=canonical_sha256(description),
        attempt_id=attempt_id,
    ).validate()
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath=RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key=MODEL_LOCK_KEY,
        model_root=MODEL_ROOT,
    )
    lock_sha256 = gate.assert_model_touch_allowed(plan)
    log("frozen-core gate PASS (lock %s)" % lock_sha256[:12])

    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    run_dir = root / "runs" / args.run_id / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)

    power_before = enforced_power_limit_watts()
    log("GPU enforced power limit before: %.2f W" % power_before)

    trials: list[dict[str, object]] = []
    chosen: dict[str, object] | None = None
    for offload in trial_sequence(int(args.start), int(args.step)):
        record = run_trial(
            offload,
            runtime_receipt=runtime_receipt,
            root=root,
            port=int(args.port),
            run_dir=run_dir,
            attempt_id=attempt_id,
        )
        free_mib = int((record["device_memory_resident_mib"] or {}).get("free_mib", -1))
        record["free_mib"] = free_mib
        record["meets_min_free"] = free_mib >= int(args.min_free_mib)
        trials.append(record)
        if not record["meets_min_free"]:
            log(
                "trial %s left only %d MiB free (< %d); the search stops here"
                % (offload["label"], free_mib, int(args.min_free_mib))
            )
            break
        chosen = record
    if chosen is None:
        raise SystemExit(
            "no trial met the %d MiB free-memory rule; the Q8_0 decoder cannot be served "
            "at this geometry" % int(args.min_free_mib)
        )
    power_after = enforced_power_limit_watts()

    document = {
        "schema": "saea-a2t-q8-placement-fit-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "run_id": args.run_id,
        "attempt_id": attempt_id,
        "flight_run_id": FLIGHT_RUN_ID,
        "preregistration": (
            "docs/readiness/2026-09-04-a2t-q8-quantization-probe-v1-preregistration.md"
        ),
        "boundary": (
            "zero generated tokens: each trial starts the pinned server, reads GET /props "
            "and stops it. No completion endpoint is touched, no sample is sent, no gold "
            "or task text is opened. The registered call ceiling exists only because "
            "contracts.ExecutionPlan requires a positive budget"
        ),
        "rule": (
            "start from --cpu-moe (every expert layer in host RAM), then lower N in steps "
            "of %d while a zero-token server start still leaves at least %d MiB free on "
            "the card at the declared serving geometry; the largest GPU-resident share "
            "that satisfies the rule is the value" % (int(args.step), int(args.min_free_mib))
        ),
        "min_free_mib": int(args.min_free_mib),
        "step": int(args.step),
        "serving_geometry": {
            "slots": SLOTS,
            "slot_tokens": SLOT_TOKENS,
            "context_tokens": SLOTS * SLOT_TOKENS,
            "base_server_args": list(BASE_SERVER_ARGS),
        },
        "model": {
            "model_lock_key": MODEL_LOCK_KEY,
            "runtime_receipt": RUNTIME_RECEIPT_RELPATH,
            "runtime_receipt_sha256": sha256_file(REPO / "docs" / RUNTIME_RECEIPT_RELPATH),
            "gguf_files": runtime_receipt["gguf_files"],
            "llama_cpp_build_commit": runtime_receipt["llama_cpp"]["build_commit"],
            "model_materialization_root": str(MODEL_ROOT),
            "feature_cache_dir": FEAT_CACHE_DIR,
        },
        "gpu_power_limit_watts": {"before": power_before, "after": power_after},
        "trials": trials,
        "chosen": {
            "offload_flag": chosen["offload_flag"],
            "n_cpu_moe": chosen["n_cpu_moe"],
            "server_args": chosen["server_args"],
            "free_mib": chosen["free_mib"],
            "used_mib": (chosen["device_memory_resident_mib"] or {}).get("used_mib"),
            "host_available_mib": (chosen["host_memory_resident_mib"] or {}).get(
                "available_mib"
            ),
            "server_rss_mib": chosen["server_rss_mib"],
            "load_seconds": chosen["load_seconds"],
        },
        "trials_run": len(trials),
        "total_generated_tokens": 0,
    }
    if args.write:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "placement-fit.json"
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        log("placement receipt written: %s (sha256 %s)" % (path, sha256_file(path)[:12]))
    print(json.dumps(document["chosen"], indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
