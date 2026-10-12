#!/usr/bin/env python3
"""Prove, offline and with zero contacts, that a ``conec-class-lists`` evidence
item now RESOLVES through the D1 evidence-identity rail for a real evaluation
call -- and that it still refuses without the supplement.

Six checks, all through the production rail
(``contracts.FrozenCoreGate.verify_evidence_identity`` and
``verify_evidence_content_identity``), never a re-implementation:

1. **before** -- a gate with NO supplement refuses the roster relpath of an
   evaluation call (`GateClosed`, "lacks a 'e21_participant_names' manifest"),
   which is the pre-existing state the KC-E1 v1 preregistration recorded as its
   hard gate.
2. **after (file rail)** -- the same gate WITH the supplement accepts the same
   relpath for every one of the 44 calls.
3. **after (content rail)** -- the same 44 samples' already-read roster bytes
   pass ``verify_evidence_content_identity`` under the same routing.
4. **the brief's own two halves** -- the two ``EvidenceItem``s
   ``core.evidence.EVIDENCE_SOURCES['conec-class-lists']`` returns for an
   evaluation call carry two carrier-bound derivation records; BOTH of their
   ``source_relpath``s pass the file rail, one routed to ``e21_contexts`` and one
   to the supplemented ``e21_participant_names``.
5. **negative control (tamper)** -- a one-byte-different roster content is
   refused by the content rail.
6. **negative control (foreign sample)** -- a sample id outside the 44 is refused.

The evaluation call is drawn from the frozen ``r4-e21-sub10`` roster recorded in
``docs/receipts/splits.json`` -- the roster half of an EVALUATION call's brief is
exactly the thing the gate has to be able to resolve before KC-E1 can fly.

Zero contacts of every kind: no model, GPU, tool, embedder, tokenizer, network,
audio decode or paid API. Only ConEC context bytes and the committed receipts are
opened; no reference transcript, timestamp file, ``wer_tags`` sidecar or bias list.
Nothing here authorizes a flight -- it closes one precondition.
"""

from __future__ import annotations
import os

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.contracts import FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.contracts.errors import GateClosed  # noqa: E402
from speech_aware_evidence_acquisition.core.evidence import (  # noqa: E402
    EVIDENCE_SOURCES,
    conec_names_file_relpath,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    load_lock,
    umbrella_lock_path,
)

CARRIER = "earnings21-original"
SUPPLEMENT_RELPATH = "receipts/artifacts/d1-e21-participant-names.json"
DEFAULT_DATA_ROOT = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
)


EVALUATION_ROSTER_RECEIPT = "docs/receipts/probe-samples/r4-e21-sub10-sample.json"


def _evaluation_ids() -> tuple[list[str], str]:
    """The frozen ``r4-e21-sub10`` evaluation ten and their split identity hash,
    read from the committed probe-sample receipt (identity only -- no reference,
    annotation or transcript byte is opened)."""

    document = json.loads((REPO_ROOT / EVALUATION_ROSTER_RECEIPT).read_text(encoding="utf-8"))
    return (
        sorted(str(item["id"]) for item in document["items"]),
        str(document["split_identity_hash"]),
    )


def _gate(data_root: Path, supplement_sha256: str | None) -> FrozenCoreGate:
    return FrozenCoreGate.for_study_repo(
        REPO_ROOT,
        data_root,
        REPO_ROOT,
        d1_evidence_supplement_relpath=(
            SUPPLEMENT_RELPATH if supplement_sha256 is not None else None
        ),
        d1_evidence_supplement_sha256=supplement_sha256,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    data_root = args.data_root
    supplement_path = REPO_ROOT / "docs" / SUPPLEMENT_RELPATH
    supplement = json.loads(supplement_path.read_text(encoding="utf-8"))
    import hashlib

    supplement_sha256 = hashlib.sha256(supplement_path.read_bytes()).hexdigest()

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    all_ids = sorted(entry["id"] for entry in supplement["manifest"])
    evaluation_ids, evaluation_split_hash = _evaluation_ids()
    evaluation_call = evaluation_ids[0]

    roster_relpaths = {
        sample_id: conec_names_file_relpath(lock, CARRIER, sample_id) for sample_id in all_ids
    }

    report: dict[str, object] = {
        "schema": "saea-e21-participant-names-d1-verification-v1",
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": "SAEA-SN-MF-E21-PARTICIPANT-NAMES-D1-V1",
        "carrier_lock_key": CARRIER,
        "d1_layer_key": supplement["d1_layer_key"],
        "supplement_relpath": f"docs/{SUPPLEMENT_RELPATH}",
        "supplement_sha256": supplement_sha256,
        "parent_d1_sha256": supplement["parent_d1_sha256"],
        "source_binding_sha256": supplement["source_binding_sha256"],
        "count": supplement["count"],
        "total_bytes": supplement["total_bytes"],
        "excluded_non_layer_files": supplement["excluded_non_layer_files"],
        "evaluation_roster": "r4-e21-sub10",
        "evaluation_roster_receipt": EVALUATION_ROSTER_RECEIPT,
        "evaluation_split_identity_hash": evaluation_split_hash,
        "evaluation_calls": evaluation_ids,
        "probe_evaluation_call": evaluation_call,
        "zero_contact": (
            "no model, GPU, tool, embedding, tokenizer, network, audio-decode or paid-API "
            "contact; only ConEC context bytes and committed receipts are opened, and no "
            "reference transcript, timestamp file, wer_tags sidecar or bias list is read"
        ),
        "checks": {},
    }
    checks: dict[str, object] = report["checks"]  # type: ignore[assignment]

    # 1. before
    bare = _gate(data_root, None)
    try:
        bare.verify_evidence_identity(CARRIER, {evaluation_call: roster_relpaths[evaluation_call]})
    except GateClosed as error:
        checks["1_refused_without_supplement"] = {"refused": True, "message": str(error)}
    else:
        print("FAIL: the rail resolved the roster layer with no supplement", file=sys.stderr)
        return 1

    gate = _gate(data_root, supplement_sha256)

    # 2. after, file rail, all 44
    gate.verify_evidence_identity(CARRIER, roster_relpaths)
    checks["2_file_rail_all_calls"] = {"resolved": len(roster_relpaths)}

    # 3. after, content rail, all 44
    contents = {
        sample_id: (data_root / relpath).read_bytes()
        for sample_id, relpath in roster_relpaths.items()
    }
    gate.verify_evidence_content_identity(CARRIER, contents, roster_relpaths)
    checks["3_content_rail_all_calls"] = {"resolved": len(contents)}

    # 4. the brief's own two halves for one evaluation call
    source = EVIDENCE_SOURCES.resolve("conec-class-lists")
    items = source(lock, data_root, evaluation_call, CARRIER, {"brief_max_entries_per_class": 0})
    halves = []
    for item in items:
        record = item.derivation
        assert record is not None and record.carrier_bound
        gate.verify_evidence_identity(CARRIER, {evaluation_call: record.source_relpath})
        gate.verify_evidence_content_identity(
            CARRIER,
            {evaluation_call: item.derivation_source_bytes},
            {evaluation_call: record.source_relpath},
        )
        halves.append(
            {
                "brief_part": item.provenance["brief_part"],
                "transform_name": record.transform_name,
                "source_relpath": record.source_relpath,
                "routed_d1_layer_key": (
                    supplement["d1_layer_key"]
                    if "/participant_names/" in record.source_relpath
                    else "e21_contexts"
                ),
                "source_sha256": record.source_sha256,
            }
        )
    checks["4_conec_class_lists_both_halves"] = {
        "sample_id": evaluation_call,
        "items": halves,
    }
    routed = {half["routed_d1_layer_key"] for half in halves}
    if routed != {"e21_contexts", supplement["d1_layer_key"]}:
        print(f"FAIL: the brief's halves routed to {sorted(routed)}", file=sys.stderr)
        return 1

    # 5. negative control: tampered content
    tampered = {evaluation_call: contents[evaluation_call] + b" "}
    try:
        gate.verify_evidence_content_identity(
            CARRIER, tampered, {evaluation_call: roster_relpaths[evaluation_call]}
        )
    except GateClosed as error:
        checks["5_tampered_content_refused"] = {"refused": True, "message": str(error)}
    else:
        print("FAIL: tampered roster content passed the content rail", file=sys.stderr)
        return 1

    # 6. negative control: a sample id outside the frozen 44
    foreign = "0000000"
    assert foreign not in roster_relpaths
    try:
        gate.verify_evidence_identity(
            CARRIER, {foreign: roster_relpaths[evaluation_call]}
        )
    except GateClosed as error:
        checks["6_foreign_sample_refused"] = {"refused": True, "message": str(error)}
    else:
        print("FAIL: a sample id outside the frozen 44 resolved", file=sys.stderr)
        return 1

    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8", newline="\n")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
