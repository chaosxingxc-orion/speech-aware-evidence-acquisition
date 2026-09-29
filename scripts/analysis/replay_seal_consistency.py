"""Offline seal-consistency replay over the sealed trace(s) of one run.

Model-free and read-only: no model, server, tokenizer, GPU, queue or socket
contact, and nothing under the attempt directories is ever written. For every
attempt named on the command line this script

1. scans the attempt's trace with ``core.flight.resume.read_predecessor_attempt``
   (the exact reader a resume-recovery seals kept rows from);
2. renders EVERY complete row, one row at a time, through the real
   ``FlightRuntime._canonical_output_rows`` seal stage (a skeleton runtime over
   the cell's own composed fragments), so every seal-time consistency check the
   finaliser performs runs per row instead of stopping at the first refusal --
   among them "native delivery normalisation output differs from the
   delivered text";
3. re-runs the model-free bundle row invariants over each rendered row: I7
   (the delivered text hashes to the row's ``response_text_sha256``; carrier
   and arm bind to the composed cell), I7n
   (``core.bundle.outputs._verify_delivery_normalisation`` against the
   delivered contact's recorded response bytes) and I7g
   (``_verify_grouped_commit``) where applicable; and
4. checks the union across attempts: no sample is sealed twice.

It prints one JSON document: per attempt, samples started / complete /
incomplete (reason classes only), rows checked, and every failing row as a
sha256 prefix of its sample id with the check name. Never utterance text,
transcripts, gold labels, tool arguments or model output. Exit status 0 only
when no row fails and no sample is sealed twice.

Usage (WSL, PYTHONPATH=<tree>/src, SPEECHRL_DATA_DIR set)::

    python scripts/analysis/replay_seal_consistency.py \\
        --experiment slurp-native-stage3-comp1-fold-a-v1-resume \\
        --run-id SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 \\
        --attempt attempt-slurp-native-stage3-comp1-fold-a-generation-v1 \\
        --attempt attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import sys
from pathlib import Path

SCHEMA = "saea-seal-consistency-replay-v1"


def _id_hash(sample_id: str) -> str:
    return hashlib.sha256(sample_id.encode("utf-8")).hexdigest()[:12]


def _reason_class(reason: object) -> str:
    """Strip quoted ids and digests from a message so only its class remains."""

    text = re.sub(r"'[^']*'", "<id>", str(reason))
    text = re.sub(r"[0-9a-f]{12,}", "<hex>", text)
    return text[:200]


def _cell(repo_root: Path, experiment: str, run_id: str):
    from speech_aware_evidence_acquisition.core.flight.campaign import (  # noqa: PLC0415
        load_campaign_cells,
    )

    for cell in load_campaign_cells(repo_root, experiment):
        if cell.run_id == run_id:
            return cell
    raise SystemExit(f"experiment {experiment!r} declares no cell for run {run_id!r}")


def _skeleton(composed):
    """A FlightRuntime carrying only what the seal stage reads: the composed
    cell. No transport, session, gate, lease or attempt accounting exists."""

    from speech_aware_evidence_acquisition.core.flight.runtime import (  # noqa: PLC0415
        FlightRuntime,
    )

    runtime = object.__new__(FlightRuntime)
    runtime._composed = composed
    runtime._plan = None
    runtime._resume = None
    runtime._resume_flown_sample_ids = ()
    runtime._identity_packet_bindings = None
    runtime._artifact_result_binding = None
    runtime._artifact_content_validator = None
    runtime._phase_summaries = ()
    runtime._output_rows = ()
    return runtime


def _check_attempt(runtime, run_dir: Path, run_id: str, attempt_id: str, policy: str):
    from speech_aware_evidence_acquisition.core.bundle import outputs as bundle  # noqa: PLC0415
    from speech_aware_evidence_acquisition.core.flight.resume import (  # noqa: PLC0415
        read_predecessor_attempt,
    )
    from speech_aware_evidence_acquisition.core.flight.runtime import (  # noqa: PLC0415
        FlightRuntime,
    )
    from speech_aware_evidence_acquisition.rails.native_episode_receipt import (  # noqa: PLC0415
        validate_native_episode_delivery_receipt,
    )

    scan = read_predecessor_attempt(
        run_id=run_id, attempt_id=attempt_id, attempt_dir=run_dir / attempt_id,
        program_id=policy,
    )
    values = runtime._composed.values
    carrier = values.get("carrier_lock_key")
    arm = values.get("arm")
    failures: list[dict[str, str]] = []
    checked = 0
    normalised = 0
    for sample_id in scan.complete_sample_ids:
        label = _id_hash(sample_id)
        summaries, timings = scan.replay([sample_id], controller_policy_id=policy)
        rows = FlightRuntime._rows_from_phase_summaries(summaries, policy=policy)
        checked += 1
        try:
            (row,) = runtime._canonical_output_rows(
                None, output_rows=rows, timings=timings, phase_summaries=summaries,
            )
        except Exception as error:  # noqa: BLE001 - every refusal is a finding
            failures.append({
                "sample_id_sha256_12": label, "check": "seal._canonical_output_rows",
                "error": f"{type(error).__name__}: {_reason_class(error)}",
            })
            continue
        text = row.get("text")
        if (
            not isinstance(text, str)
            or hashlib.sha256(text.encode("utf-8")).hexdigest()
            != row.get("response_text_sha256")
        ):
            failures.append({"sample_id_sha256_12": label, "check": "I7.text_hash", "error": ""})
        if row.get("carrier_lock_key") != carrier or row.get("arm") != arm:
            failures.append({"sample_id_sha256_12": label, "check": "I7.carrier_arm", "error": ""})
        block = bundle._delivery_normalisation_receipt(row)
        if block is not None:
            normalised += 1
            receipt = scan.complete[sample_id].native_episode_receipt
            try:
                delivery = validate_native_episode_delivery_receipt(
                    receipt, error_type=RuntimeError,
                )
                request_id = delivery.final_contact.get("request_id")
                source = next(
                    contact.text for contact in scan.contacts[sample_id]
                    if contact.request_id == request_id
                )
                bundle._verify_delivery_normalisation(row, block, {"text": source})
            except Exception as error:  # noqa: BLE001
                failures.append({
                    "sample_id_sha256_12": label, "check": "I7n",
                    "error": f"{type(error).__name__}: {_reason_class(error)}",
                })
        if "solver_group" in row:
            try:
                bundle._verify_grouped_commit(row)
            except Exception as error:  # noqa: BLE001
                failures.append({
                    "sample_id_sha256_12": label, "check": "I7g",
                    "error": f"{type(error).__name__}: {_reason_class(error)}",
                })
    return scan, {
        "attempt_id": attempt_id,
        "trace_sha256": scan.trace_sha256,
        "samples_started": len(scan.started_sample_ids),
        "complete": len(scan.complete),
        "incomplete": len(scan.incomplete),
        "incomplete_reason_classes": dict(collections.Counter(
            _reason_class(reason) for reason in scan.incomplete.values()
        )),
        "rows_checked": checked,
        "rows_with_deliver_normaliser": normalised,
        "rows_failing": len({item["sample_id_sha256_12"] for item in failures}),
        "failures_by_check": dict(collections.Counter(item["check"] for item in failures)),
        "failures_by_error_class": dict(collections.Counter(item["error"] for item in failures)),
        "failing_rows_first_20": failures[:20],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline seal-consistency replay.")
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", action="append", required=True)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args(argv)

    from speech_aware_evidence_acquisition.core.config import compose  # noqa: PLC0415
    from speech_aware_evidence_acquisition.core.flight import (  # noqa: PLC0415
        resume as resume_module,
    )

    data_root = args.data_root or Path(os.environ["SPEECHRL_DATA_DIR"])
    document = _cell(args.repo_root, args.experiment, args.run_id).document
    composed = compose(
        args.repo_root, document["model_fragment"], document["dataset_fragment"],
        document["baseline_fragment"], args.experiment,
    )
    policy = str(composed.values.get("policy"))
    runtime = _skeleton(composed)
    run_dir = data_root / "runs" / args.run_id
    report: dict[str, object] = {
        "schema": SCHEMA,
        "run_id": args.run_id,
        "experiment": args.experiment,
        "policy": policy,
        "resume_py_sha256": hashlib.sha256(
            Path(resume_module.__file__).read_bytes()
        ).hexdigest(),
        "model_contacts": 0,
        "attempts": [],
    }
    owners: dict[str, list[str]] = collections.defaultdict(list)
    for attempt_id in args.attempt:
        scan, block = _check_attempt(runtime, run_dir, args.run_id, attempt_id, policy)
        report["attempts"].append(block)
        for sample_id in scan.complete_sample_ids:
            owners[sample_id].append(attempt_id)
    twice = [sample for sample, where in owners.items() if len(where) > 1]
    report["union"] = {
        "complete_rows": len(owners),
        "sealed_twice": len(twice),
        "sealed_twice_first_10": [_id_hash(sample) for sample in twice[:10]],
    }
    report["rows_checked_total"] = sum(item["rows_checked"] for item in report["attempts"])
    report["rows_failing_total"] = sum(item["rows_failing"] for item in report["attempts"])
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["rows_failing_total"] == 0 and not twice else 1


if __name__ == "__main__":
    raise SystemExit(main())
