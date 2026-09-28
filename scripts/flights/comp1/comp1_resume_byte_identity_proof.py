#!/usr/bin/env python3
"""Model-free byte-identity proof for the COMP-1 resume-recovery (owner decision 22).

WHY THIS EXISTS. Owner decision 22 (``core/flight/resume.py``, module docstring) admits a
resume-recovery only when "the code and the request bytes are unchanged -- an infrastructure
failure ..., never a harness or config defect". The COMP-1 arm
``SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1`` aborted on a HARNESS defect (the Solver citation parser
refused a repeated id; ``docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md``) and
the fix (``rails/solver_citation.py`` only) changes code. So the letter of decision 22 is broken.
Its PURPOSE -- every kept row is exactly what the recovery tree would have sealed -- is what this
script proves, re-runnably, so the owner can rule on a receipt rather than on a note.

WHAT IT PROVES, from the sealed predecessor trace alone:

1. the trace hashes to the declared ``resume_from.trace_sha256``;
2. ``core.flight.resume.read_predecessor_attempt`` (the registered replay the runtime itself uses)
   classifies the rows as the diagnosis states (471 COMPLETE, 1 INCOMPLETE, 608 never started);
3. every cited Solver contact in the trace (``response_format`` named
   ``saea_solver_cited_answer_v1``) is re-bound with ``bind_cited_completion`` under BOTH the
   predecessor code (``rails/solver_citation.py`` read with ``git show <flight commit>:...``) and
   the fixed code (this tree). Its supplied-id set is recovered from the request's own
   per-contact grammar and must re-render byte-identically through
   ``cited_answer_response_format_for``. Where the predecessor code accepted, the capture
   (state bytes, cited ids, record) must be IDENTICAL under the fix;
4. every ``solver_citations`` record SEALED in a kept row's ``/native-episode`` receipt must equal,
   byte for byte in canonical JSON, the record the FIXED code produces for that contact -- so the
   kept rows' custody is what the recovery tree would have written;
5. exactly one contact is refused by the predecessor code and accepted by the fix, its intent list
   collapses with ``duplicate_citation_ids_dropped`` > 0, the supplied-id check passes, and it
   lies in the one INCOMPLETE row (so it is re-flown, never kept).

Zero model, tokenizer, encoder, scorer, server, GPU and network contacts. It reads the trace
read-only and never writes under the attempt directory. It prints and persists ids, counts and
hashes only -- never an utterance, transcript, gold label, answer or response text.

    PYTHONPATH=<tree>/src python scripts/flights/comp1/comp1_resume_byte_identity_proof.py \\
        --repo-root <tree> --data-root "$SPEECHRL_DATA_DIR" [--output <relpath under data root>]

Exit 0 with verdict PASS when every assertion holds; exit 1 with verdict FAIL otherwise (the
receipt is still written, naming the failed assertions); exit 2 when an input cannot be read.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

RUN_ID = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
ABORTED_ATTEMPT_ID = "attempt-slurp-native-stage3-comp1-fold-a-generation-v1"
DECLARED_TRACE_SHA256 = "029a2dbbd62bc8752ff9e7d6a53dfee0cb49872f48b11267e49c4022c9561997"
FLIGHT_COMMIT = "cb628f592934921a48102a5451ce1dd2f5c0fc98"
FAILING_REQUEST_ID = "flight-1854"
PROGRAM_ID = "phase-native-candidates-review-revise-cited-v1"
CITED_SCHEMA_NAME = "saea_solver_cited_answer_v1"
MODULE_RELPATH = "src/speech_aware_evidence_acquisition/rails/solver_citation.py"
DEFAULT_OUTPUT = "coordination/slurp-stage3-comp1-fold-a-v1/resume-byte-identity-proof-v1.json"
SCHEMA = "saea-comp1-resume-byte-identity-proof-v1"

#: The counts the diagnosis measured. A different count is a FAIL, never a silent re-baseline.
EXPECTED = {
    "roster_rows": 1080,
    "complete_rows": 471,
    "incomplete_rows": 1,
    "unstarted_rows": 608,
    "cited_contacts": 482,
    "identical_captures": 481,
    "refused_by_predecessor_sealed_by_fix": 1,
    "regressions": 0,
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_module_from_source(name: str, source: str, origin: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = origin
    sys.modules[name] = module  # dataclasses resolve their module through sys.modules
    exec(compile(source, origin, "exec"), module.__dict__)  # noqa: S102 -- committed repository code
    return module


def _supplied_ids(response_format: dict) -> tuple[str, ...] | None:
    """The per-contact supplied ids, read from the request's own intent citation grammar."""

    try:
        intent = response_format["json_schema"]["schema"]["properties"]["citations"]["properties"]["intent"]
    except (KeyError, TypeError):
        return None
    if intent.get("maxItems") == 0 and "items" not in intent:
        return ()
    enum = (intent.get("items") or {}).get("enum")
    return tuple(enum) if isinstance(enum, list) else None


def _capture(module, text, finish_reason, supplied, contact_id, role_id, rtsha):
    try:
        capture = module.bind_cited_completion(
            text, finish_reason=finish_reason, supplied_value_ids=supplied,
            contact_id=contact_id, role_id=role_id, response_text_sha256=rtsha,
        )
    except module.SolverCitationError as error:
        return None, str(error)
    return capture, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="relpath under the data root")
    args = parser.parse_args(argv)
    repo, data = args.repo_root.resolve(), args.data_root.resolve()

    from speech_aware_evidence_acquisition.core.flight import resume as resume_module  # noqa: PLC0415
    from speech_aware_evidence_acquisition.core.flight.resume import (  # noqa: PLC0415
        predecessor_trace_path,
        read_predecessor_attempt,
    )
    from speech_aware_evidence_acquisition.rails import solver_citation as fixed  # noqa: PLC0415

    attempt_dir = data / "runs" / RUN_ID / ABORTED_ATTEMPT_ID
    trace = predecessor_trace_path(attempt_dir, RUN_ID)
    try:
        predecessor_source = subprocess.run(
            ["git", "-C", str(repo), "show", f"{FLIGHT_COMMIT}:{MODULE_RELPATH}"],
            check=True, capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"cannot read the predecessor code at {FLIGHT_COMMIT[:8]}: {error}", file=sys.stderr)
        return 2
    predecessor = _load_module_from_source(
        "_comp1_predecessor_solver_citation", predecessor_source.decode("utf-8"),
        f"{FLIGHT_COMMIT}:{MODULE_RELPATH}",
    )
    fixed_path = Path(fixed.__file__).resolve()
    fixed_bytes = fixed_path.read_bytes()
    failures: list[str] = []

    # 1 + 2: the pinned trace and the registered replay's classification.
    try:
        attempt = read_predecessor_attempt(
            run_id=RUN_ID, attempt_id=ABORTED_ATTEMPT_ID, attempt_dir=attempt_dir,
            expected_trace_sha256=DECLARED_TRACE_SHA256, program_id=PROGRAM_ID,
        )
    except Exception as error:  # noqa: BLE001 -- any refusal is the answer
        print(f"predecessor replay refused: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    roster_path = repo / "configs" / "experiment" / "slurp-native-stage3-comp1-fold-a-v1.json"
    roster = json.loads(roster_path.read_text(encoding="utf-8"))["populations"][0]["ids"]
    complete = set(attempt.complete_sample_ids)
    incomplete = set(attempt.incomplete_sample_ids)
    started = set(attempt.started_sample_ids)
    counts = {
        "roster_rows": len(roster),
        "complete_rows": len(complete),
        "incomplete_rows": len(incomplete),
        "unstarted_rows": len(set(roster) - started),
        "trace_records": attempt.record_count,
        "trace_contacts": attempt.contact_count(),
    }
    if started - set(roster):
        failures.append("the predecessor flew rows outside the arm's roster")

    # 3 + 4 + 5: one streaming pass over the trace for the cited contacts and the sealed records.
    requests: dict[str, dict] = {}
    responses: dict[str, tuple[str, str]] = {}
    finishes: dict[str, object] = {}
    sealed: dict[str, list[dict]] = {}
    suffix = f"/{PROGRAM_ID}/native-episode"
    with trace.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            channel, record_id, payload = record.get("channel"), record.get("record_id"), record.get("payload")
            if channel == "MODEL_REQUEST" and record_id.endswith("/request"):
                inner = payload.get("payload") or {}
                response_format = (inner.get("decoding_params") or {}).get("response_format")
                if isinstance(response_format, dict) and (
                    (response_format.get("json_schema") or {}).get("name") == CITED_SCHEMA_NAME
                ):
                    requests[record_id[: -len("/request")]] = {
                        "sample_id": inner.get("sample_id"), "response_format": response_format,
                    }
            elif channel == "MODEL_RESPONSE" and record_id.endswith("/response"):
                responses[record_id[: -len("/response")]] = (payload.get("text"), payload.get("response_text_sha256"))
            elif channel == "MODEL_WIRE_RESPONSE" and record_id.endswith("/wire-response"):
                finishes[record_id[: -len("/wire-response")]] = payload.get("finish_reason")
            elif channel == "USE" and record_id.endswith(suffix):
                receipt = payload.get("use_native_episode") or {}
                block = receipt.get("solver_citations")
                if isinstance(block, dict):
                    sealed[record_id[: -len(suffix)]] = [dict(row) for row in block.get("contacts", [])]

    identical = refused_then_sealed = regressions = 0
    sealed_matched = sealed_identical = 0
    grammar_rerender_mismatch = 0
    failing: dict[str, object] = {}
    matched_sealed_keys: set[tuple[str, int]] = set()
    for request_id, meta in requests.items():
        sample_id = meta["sample_id"]
        text, rtsha = responses.get(request_id, (None, None))
        finish = finishes.get(request_id)
        supplied = _supplied_ids(meta["response_format"])
        if text is None or supplied is None:
            failures.append(f"{request_id}: cited contact without a response or a readable grammar")
            continue
        if fixed.cited_answer_response_format_for(supplied) != meta["response_format"]:
            grammar_rerender_mismatch += 1
        # The sealed record of this contact, when its row is kept, supplies the contact and role ids.
        rows = sealed.get(sample_id, [])
        position = next(
            (index for index, row in enumerate(rows)
             if row.get("response_text_sha256") == rtsha and (sample_id, index) not in matched_sealed_keys),
            None,
        )
        contact_id = rows[position]["contact_id"] if position is not None else request_id
        role_id = rows[position]["role_id"] if position is not None else "solver"
        before, before_error = _capture(predecessor, text, finish, supplied, contact_id, role_id, rtsha)
        after, after_error = _capture(fixed, text, finish, supplied, contact_id, role_id, rtsha)
        if before is not None and after is not None:
            same = (
                before.state_content == after.state_content
                and before.cited_value_ids == after.cited_value_ids
                and _canonical(dict(before.record)) == _canonical(dict(after.record))
            )
            if same:
                identical += 1
            else:
                regressions += 1
                failures.append(f"{request_id}: capture differs between the predecessor and the fix")
        elif before is None and after is not None:
            refused_then_sealed += 1
            failing = {
                "request_id": request_id,
                "sample_id_sha256_prefix": _sha256_bytes(str(sample_id).encode("utf-8"))[:12],
                "response_text_sha256_prefix": str(rtsha)[:12],
                "finish_reason": finish,
                "predecessor_refusal": before_error,
                "fixed_parse": after.record.get("parse"),
                "duplicate_citation_ids_dropped": after.record.get("duplicate_citation_ids_dropped", 0),
                "intent_ids_after_collapse": len(after.record.get("intent_evidence_ids", [])),
                "supplied_ids": len(supplied),
                "row_state": (
                    "INCOMPLETE" if sample_id in incomplete
                    else "COMPLETE" if sample_id in complete else "UNKNOWN"
                ),
            }
        else:
            regressions += 1
            failures.append(
                f"{request_id}: refused by the fix ({after_error})"
                + ("" if before is None else " though the predecessor sealed it")
            )
        if position is not None:
            matched_sealed_keys.add((sample_id, position))
            sealed_matched += 1
            if after is not None and _canonical(dict(after.record)) == _canonical(rows[position]):
                sealed_identical += 1
            else:
                failures.append(f"{request_id}: the fixed record differs from the record the kept row sealed")

    sealed_total = sum(len(rows) for sample_id, rows in sealed.items() if sample_id in complete)
    sealed_outside_complete = sum(len(rows) for sample_id, rows in sealed.items() if sample_id not in complete)
    counts.update({
        "cited_contacts": len(requests),
        "identical_captures": identical,
        "refused_by_predecessor_sealed_by_fix": refused_then_sealed,
        "regressions": regressions,
        "grammar_rerender_mismatches": grammar_rerender_mismatch,
        "kept_rows_sealed_citation_records": sealed_total,
        "sealed_records_matched_to_a_trace_contact": sealed_matched,
        "sealed_records_identical_under_the_fix": sealed_identical,
        "sealed_records_outside_complete_rows": sealed_outside_complete,
    })
    for key, value in EXPECTED.items():
        if counts.get(key) != value:
            failures.append(f"{key} = {counts.get(key)}, expected {value}")
    if grammar_rerender_mismatch:
        failures.append("a request grammar does not re-render from its own supplied ids")
    if sealed_matched != sealed_total or sealed_identical != sealed_total:
        failures.append("not every kept row's sealed citation record is identical under the fix")
    if failing.get("request_id") != FAILING_REQUEST_ID:
        failures.append(f"the refused-then-sealed contact is {failing.get('request_id')!r}, not {FAILING_REQUEST_ID}")
    if not failing.get("duplicate_citation_ids_dropped"):
        failures.append("the failing contact did not record a collapsed repeat")
    if failing.get("row_state") != "INCOMPLETE":
        failures.append("the failing contact is not in the one INCOMPLETE (re-flown) row")

    verdict = "PASS" if not failures else "FAIL"
    receipt = {
        "schema": SCHEMA,
        "verdict": verdict,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": RUN_ID,
        "aborted_attempt_id": ABORTED_ATTEMPT_ID,
        "trace": {"relpath": str(trace.relative_to(data)), "sha256": attempt.trace_sha256,
                  "declared_sha256": DECLARED_TRACE_SHA256},
        "predecessor_code": {"commit": FLIGHT_COMMIT, "relpath": MODULE_RELPATH,
                             "sha256": _sha256_bytes(predecessor_source)},
        "fixed_code": {"relpath": MODULE_RELPATH, "sha256": _sha256_bytes(fixed_bytes)},
        "resume_replay_code": {
            "relpath": "src/speech_aware_evidence_acquisition/core/flight/resume.py",
            "sha256": _sha256_bytes(Path(resume_module.__file__).read_bytes()),
            "non_wire_contact_blocks": sorted(getattr(resume_module, "NON_WIRE_CONTACT_BLOCKS", ())),
        },
        "study_head": subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        "counts": counts,
        "expected": EXPECTED,
        "failing_contact": failing,
        "failures": failures,
        "rule": ("owner decision 22 admits a resume only when code and request bytes are unchanged; this "
                 "receipt proves the request bytes unchanged (every cited grammar re-renders), every kept "
                 "row's sealed citation record byte-identical under the fixed code, and the one changed "
                 "disposition confined to the re-flown row. Whether that admits a resume is the owner's ruling."),
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0, "gpu": 0, "network": 0},
        "content_policy": "ids, counts and hashes only; no utterance, transcript, gold, answer or response text",
    }
    output = data / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.write_text(body, encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": verdict, "receipt": str(output),
                      "receipt_sha256": _sha256_bytes(body.encode("utf-8")), "counts": counts,
                      "failing_contact": {k: v for k, v in failing.items() if k != "predecessor_refusal"},
                      "failures": failures}, indent=1, sort_keys=True))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
