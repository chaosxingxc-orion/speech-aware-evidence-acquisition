"""Offline seal-consistency replay over the sealed trace(s) of one run.

Model-free and read-only: no model, server, tokenizer, GPU, queue or socket
contact, and nothing under the attempt directories is ever written. For every
attempt named on the command line -- unpinned via ``--attempt``, or PINNED via
``--predecessor ATTEMPT_ID:SHA256`` (E10d, 2026-09-29: the same
``(attempt_id, trace_sha256)`` shape one entry of a multi-predecessor
``resume_from`` list declares) -- this script

1. scans the attempt's trace with ``core.flight.resume.read_predecessor_attempt``
   (the exact reader a resume-recovery seals kept rows from; a ``--predecessor``
   pin is checked here, refusing a trace that does not hash to it);
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
   delivered contact's recorded response bytes), I7g
   (``_verify_grouped_commit``), I7l (``_verify_relisten_trace_binding``,
   over a relisten-armed row's re-derived receipt) and I7v's Perception path
   (``_verify_perception_branch_trace_binding``, over a branched row's
   re-derived schema-v2 ``perception_branches`` block, P-SV-1 2026-09-29)
   where applicable; and
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

Or pinned, exactly as a multi-predecessor ``resume_from`` would declare them::

    python scripts/analysis/replay_seal_consistency.py \\
        --experiment slurp-native-stage3-comp1-fold-a-v1-resume \\
        --run-id SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 \\
        --predecessor attempt-slurp-native-stage3-comp1-fold-a-generation-v1:<sha256> \\
        --predecessor attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3:<sha256>
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


def _check_attempt(
    runtime, run_dir: Path, run_id: str, attempt_id: str, policy: str,
    *, expected_trace_sha256: str | None = None,
):
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

    # E10d (2026-09-29): when the caller pins a predecessor's trace sha256
    # (``--predecessor ATTEMPT_ID:SHA256``, the same declaration shape a
    # multi-predecessor ``resume_from`` list carries), the scan refuses a
    # trace that does not hash to it -- exactly what a real resume's
    # ``read_predecessor_attempt(..., expected_trace_sha256=...)`` call
    # enforces before any row is ever replayed. An unpinned ``--attempt``
    # measures without comparing, which is what a read-only audit of an
    # attempt whose hash is not yet pinned needs.
    scan = read_predecessor_attempt(
        run_id=run_id, attempt_id=attempt_id, attempt_dir=run_dir / attempt_id,
        program_id=policy, expected_trace_sha256=expected_trace_sha256,
        # E4-1 (2026-09-29): a relisten-armed cell's rows carry their
        # re-derived saea-relisten-v1 receipts, exactly as a resume keeps them.
        relisten=runtime._declared_relisten_block(),
    )
    values = runtime._composed.values
    carrier = values.get("carrier_lock_key")
    arm = values.get("arm")
    failures: list[dict[str, str]] = []
    checked = 0
    normalised = 0
    relistened = 0
    branched = 0
    note_parse_status: collections.Counter = collections.Counter()
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
        if "relisten" in row:
            # E4-1 (2026-09-29): I7l over the row's own recorded contacts --
            # each relisten contact's sample id and response text straight
            # from this attempt's trace, as the bundle verifier reads them.
            relistened += 1
            records: dict[str, dict[str, object]] = {}
            for contact in scan.contacts[sample_id]:
                records[f"{contact.request_id}/request"] = {
                    "payload": {"sample_id": contact.sample_id},
                }
                records[f"{contact.request_id}/response"] = {"text": contact.text}
            try:
                bundle._verify_relisten_trace_binding(row, records)
            except Exception as error:  # noqa: BLE001
                failures.append({
                    "sample_id_sha256_12": label, "check": "I7l",
                    "error": f"{type(error).__name__}: {_reason_class(error)}",
                })
        episode = row.get("native_episode_receipt")
        if hasattr(episode, "get") and "perception_branches" in episode:
            # P-SV-1 (2026-09-29): I7v's Perception path over the row's own
            # recorded contacts -- request digests, sample ids and response
            # text straight from this attempt's trace.
            branched += 1
            records = {}
            for contact in scan.contacts[sample_id]:
                records[f"{contact.request_id}/request"] = {
                    "payload_sha256": contact.request_sha256,
                    "payload": {
                        "sample_id": contact.sample_id,
                        # NX-T R1 seal fix (2026-10-15): the v5 (thinking-policy) wire check reads each request's
                        # decoding fields, and an absent Solver column is held against its recorded finish_reason.
                        **({} if contact.decoding_view is None else {"decoding_params": dict(contact.decoding_view)}),
                    },
                }
                records[f"{contact.request_id}/response"] = {
                    "text": contact.text,
                    "response_sha256": contact.response_sha256,
                    "response_text_sha256": contact.response_text_sha256,
                }
                if contact.finish_reason is not None:
                    records[f"{contact.request_id}/wire-response"] = {"finish_reason": contact.finish_reason}
            try:
                bundle._verify_perception_branch_trace_binding(row, records)
            except Exception as error:  # noqa: BLE001
                failures.append({
                    "sample_id_sha256_12": label, "check": "I7v",
                    "error": f"{type(error).__name__}: {_reason_class(error)}",
                })
            for item in episode["perception_branches"].get("branches", ()):
                note_parse_status[
                    f"{item.get('branch_id')}:{item.get('note_parse_status')}"
                ] += 1
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
        "rows_with_relisten_receipt": relistened,
        "rows_with_perception_branches": branched,
        "perception_branch_note_parse_status": dict(sorted(note_parse_status.items())),
        "rows_failing": len({item["sample_id_sha256_12"] for item in failures}),
        "failures_by_check": dict(collections.Counter(item["check"] for item in failures)),
        "failures_by_error_class": dict(collections.Counter(item["error"] for item in failures)),
        "failing_rows_first_20": failures[:20],
    }


def _parse_predecessor_pin(value: str) -> tuple[str, str]:
    """Parse ``ATTEMPT_ID:SHA256`` -- the same (attempt_id, trace_sha256)
    pair a ``resume_from`` predecessor declaration carries."""

    attempt_id, _, digest = value.rpartition(":")
    if not attempt_id or not re.fullmatch("[0-9a-f]{64}", digest):
        raise SystemExit(
            f"--predecessor must be ATTEMPT_ID:SHA256 (64-hex), got {value!r}"
        )
    return attempt_id, digest


def _union_report(owners: dict) -> dict:
    """The union/conflict report for the declared attempts' COMPLETE sets --
    a pure function of ``{sample_id: [attempt_id, ...]}`` so it is testable
    without a repo, a composed config or a trace file. This is the checker's
    own offline witness for exactly what
    ``core.flight.resume.MergedPredecessors`` would accept (every sample
    claimed by exactly one attempt) or refuse (any claimed by more than one)
    over the same declared attempts."""

    twice = [sample for sample, where in owners.items() if len(where) > 1]
    return {
        "complete_rows": len(owners),
        "sealed_twice": len(twice),
        "sealed_twice_first_10": [_id_hash(sample) for sample in twice[:10]],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline seal-consistency replay.")
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--attempt", action="append", default=[],
        help="an attempt id to scan unpinned (measures without comparing a hash)",
    )
    parser.add_argument(
        "--predecessor", action="append", default=[],
        help=(
            "ATTEMPT_ID:SHA256 -- a pinned predecessor declaration, exactly the "
            "shape one entry of a multi-predecessor resume_from list carries "
            "(E10d, 2026-09-29). The scan refuses a trace that does not hash "
            "to the declared value."
        ),
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args(argv)
    if not args.attempt and not args.predecessor:
        parser.error("at least one --attempt or --predecessor is required")
    if len(set(args.attempt) & {attempt_id for attempt_id, _ in map(_parse_predecessor_pin, args.predecessor)}):
        parser.error("an attempt id must not appear in both --attempt and --predecessor")

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
    # Ordered, declared-order list of (attempt_id, expected_trace_sha256 or
    # None) -- the SAME shape and order a multi-predecessor resume_from
    # declares, so the union/conflict report below is the offline witness for
    # exactly what core.flight.resume.MergedPredecessors would accept or
    # refuse over these same attempts.
    declared: list[tuple[str, str | None]] = [
        (attempt_id, None) for attempt_id in args.attempt
    ] + [_parse_predecessor_pin(value) for value in args.predecessor]
    owners: dict[str, list[str]] = collections.defaultdict(list)
    for attempt_id, expected_trace_sha256 in declared:
        scan, block = _check_attempt(
            runtime, run_dir, args.run_id, attempt_id, policy,
            expected_trace_sha256=expected_trace_sha256,
        )
        report["attempts"].append(block)
        for sample_id in scan.complete_sample_ids:
            owners[sample_id].append(attempt_id)
    report["union"] = _union_report(owners)
    report["rows_checked_total"] = sum(item["rows_checked"] for item in report["attempts"])
    report["rows_failing_total"] = sum(item["rows_failing"] for item in report["attempts"])
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return (
        0
        if report["rows_failing_total"] == 0 and report["union"]["sealed_twice"] == 0
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
