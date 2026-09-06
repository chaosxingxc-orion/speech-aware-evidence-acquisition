#!/usr/bin/env python3
"""Hold the EVO-S1 serving geometry up so a model-free step can price a candidate.

Exposure row ``SAEA-SLURP-EVO-S1-PROMPT-FIT-V1``, whose scope is "the
tokenizer/template measurement pass and the `token_counter` binding it
publishes". ``scripts/slurp_evo_s1_prompt_fit.py`` measured that binding and
stopped its server; the CANDIDATES step of a round then has to USE it, because
``rails.evolution._slurp_control_candidates`` refuses to price round 1's F3 form
twin with anything but the serving geometry's own ``/tokenize`` and
``validate_slurp_candidate_artifact`` refuses any other ``token_counter_id``.

So this entry does exactly one thing: spawn the resident server under a
gate-checked ``contracts.ExecutionPlan``, run ONE command with it up, and stop it
with its own stop receipt. **Zero generated tokens of its own.** The command it
runs is the model-free evolution driver, which makes no model contact either --
it POSTs to ``/tokenize`` and reads back token counts.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/slurp_evo_s1_serve_tokenizer.py -- \\
        python scripts/run_evolution_round.py --config ... --round 1 \\
          --token-counter-url http://127.0.0.1:8080
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if Path(_pkg.__file__ or "") != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose, d1_media_supplement_relpath, d1_media_supplement_sha256, model_materialization_root)
from speech_aware_evidence_acquisition.core.flight.runtime import merge_server_args  # noqa: E402
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt, start_session, stop_session)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import SLURP_LOCK_KEY  # noqa: E402

RUNTIME_ROOT = Path("/home/chao")
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64"
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"
BASELINE_FRAGMENT = "slurp-phase-slots-given-intent-schema-projected-v2-fold-a"
EXPERIMENT_FRAGMENT = "slurp-evo-s1-slot-schema-v1"
RUN_ID = "SAEA-SLURP-EVO-S1-PROMPT-FIT-V1"
PLAN_CALLS, PLAN_GPU_HOURS, PLAN_AUDIO = 8, 0.4, 60


def log(message: str) -> None:
    print("[%s] %s" % (datetime.now(timezone.utc).strftime("%H:%M:%SZ"), message), flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER,
                        help="the command to run with the server up (after --)")
    args = parser.parse_args(argv)
    command = [item for item in args.command if item != "--"]
    if not command:
        raise SystemExit("nothing to run: pass the command after --")

    root = data_root()
    composed = compose(REPO, MODEL_FRAGMENT, DATASET_FRAGMENT, BASELINE_FRAGMENT, EXPERIMENT_FRAGMENT)
    values = composed.values
    slots, slot_tokens = int(values["serving_slots"]), int(values["serving_slot_tokens"])
    plan = ExecutionPlan(
        run_id=RUN_ID, execution_profile="bounded-discovery-probe",
        carrier_lock_key=SLURP_LOCK_KEY, split_role="discovery",
        split_identity_hash=str(values["split_identity_hash"]),
        planned_model_calls=PLAN_CALLS, planned_gpu_hours=PLAN_GPU_HOURS,
        planned_speech_audio_seconds=PLAN_AUDIO, protocol_hash=composed.config_hash,
        attempt_id="attempt-%s-evos1tokenizer" % datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    ).validate()
    model_root = model_materialization_root(values)
    gate = FrozenCoreGate.for_study_repo(
        REPO, root, RUNTIME_ROOT, runtime_receipt_relpath=str(values["runtime_receipt"]),
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=(Path(model_root) if model_root else None),
        d1_media_supplement_relpath=d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values))
    log("frozen-core gate PASS (lock %s)" % gate.assert_model_touch_allowed(plan)[:12])

    runtime_receipt = load_runtime_receipt(REPO / "docs" / str(values["runtime_receipt"]))
    run_dir = root / "runs" / RUN_ID / str(plan.attempt_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    port = int(str(values["base_url"]).rsplit(":", 1)[-1])
    started = time.time()
    session = start_session(
        runtime_root=RUNTIME_ROOT, data_root=root, runtime_receipt=runtime_receipt,
        host="127.0.0.1", port=port, session_id="%s-%s" % (RUN_ID, plan.attempt_id),
        extra_argv=merge_server_args(values["server_args"], slots=slots,
                                     context_tokens=slots * slot_tokens),
        extra_env=dict(values.get("server_env", {})),
        receipt_path=run_dir / "session.receipt.json",
        server_log_path=run_dir / "session.server.log",
        role=str(runtime_receipt.get("role", "legacy")),
        model_root=(Path(model_root) if model_root else None), ready_timeout_seconds=1800.0)
    load_seconds = time.time() - started
    log("server up in %.1fs on %d (-np %d, -c %d)" % (load_seconds, port, slots, slots * slot_tokens))

    command_started = time.time()
    try:
        completed = subprocess.run(command, cwd=str(REPO), check=False)  # noqa: S603
    finally:
        stop = stop_session(session, runtime_receipt=runtime_receipt, runtime_root=RUNTIME_ROOT,
                            receipt_path=run_dir / "session.stop-receipt.json",
                            force_after_timeout=True)
        log("server stopped: %s" % stop.get("termination_signal"))
    document = {
        "schema": "saea-slurp-evo-s1-tokenizer-session-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "exposure_run_id": RUN_ID, "attempt_id": plan.attempt_id,
        "scope": "hold the flight's serving geometry up so a model-free step can price a candidate",
        "model_contacts": 0, "generated_tokens": 0,
        "serving_geometry": {"slots": slots, "slot_tokens": slot_tokens,
                             "context_tokens": slots * slot_tokens},
        "token_counter_url": "http://127.0.0.1:%d" % port,
        "command": list(command), "command_returncode": completed.returncode,
        "command_wall_seconds": round(time.time() - command_started, 3),
        "session": {"session_id": session.session_id, "pid": session.pid,
                    "load_seconds": round(load_seconds, 2), "stop": stop},
    }
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        log("wrote %s" % args.output)
    else:
        print(json.dumps(document, indent=2, sort_keys=True, default=str))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
