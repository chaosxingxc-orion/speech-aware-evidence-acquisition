#!/usr/bin/env python3
"""KU-S4 wire check -- zero model contacts, zero servers, zero sockets.

Three halves, reported separately because they fail for different reasons.

``request``
    The real ``core.flight.FlightRuntime.wire_check`` on the KU-S4N arm and
    its form twin, four DEV-1000 rows each. Everything between the two fakes
    (``WireCheckGate`` / ``WireCheckTransport``, which never opens a socket)
    is real: ``core.config.compose``, the label-free roster with every media
    file re-hashed, the candidate snapshot's content-hash verification, the
    sha256-verified candidate bank behind
    ``rails.knowledge_provider.SlurpIntentCandidateProvider``, the phase
    program, ``rails.phase_supply.build_bootstrap_selection``'s pre-flight
    seeding, ``rails.phase_review``'s legality judge, ``rails.runner``'s
    containment fold on every contact instruction, the request build and the
    payload-binding stage. The boundary payloads are then read back OUT OF
    THE REAL TRACE each run writes and asserted field by field.

``multipacket``
    The proof KU-S4a and KU-S4b need before a single exemplar packet exists:
    that a request carrying ONE query packet and ``k`` KEY packets composes
    through the REAL policy and the REAL media-identity stage.

    * ``core.policies.build_arm_payload`` -- the arm's own D2-frozen payload
      builder -- accepts ``speech_feature_parts`` of length ``k + 1`` with
      exactly one ``query``, and refuses two queries, zero queries and an
      unknown role;
    * ``rails.core_client._parse_speech_feature_messages`` -- the client-side
      parser -- returns the same ``k + 1`` descriptors from a ``(system,
      user)`` message pair carrying ``k + 1`` ``input_speech_features``
      content parts;
    * ``core.model.transport._ordered_speech_feature_content`` -- the
      transport's own content ordering -- emits ``k + 1`` media markers in
      order beside the typed supply blocks;
    * ``core.model.speech_features.load_speech_feature_packets`` -- the
      media-identity stage -- loads and hash-verifies all ``k + 1`` packets
      against the comparator's own feature root.

    The key packets are REAL, already-promoted TRAIN encoder packets from the
    receipts beside the comparator's own. They are SHAPE STAND-INS: the
    KU-S4a exemplar plan's own recordings are NOT promoted, which is the
    precondition this check documents rather than hides.

``body``
    The payload-to-HTTP-body step belongs to
    ``core.model.transport.LlamaServerTransport``, which verifies an attested
    live session at construction and therefore cannot be built in a
    model-free check. It is proved instead by the committed unit tests this
    half names and runs, which already cover multi-packet requests.

Usage (WSL2, inside the wt-kus4 worktree)::

    python scripts/slurp_kus4_wire_check.py
    python scripts/slurp_kus4_wire_check.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

ROW_ID = "SAEA-SLURP-MF-KU-S4-PREP-V1"
OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-09-slurp-kus4-wire-check"
)

WIRE_EXPERIMENT = "slurp-kus4-wire-check-4-v1"
CELLS = ("kus4n-candidates", "kus4n-candidates-twin")

#: The sealed comparator's own rendered system message. Every KU-S4 arm must
#: reproduce it byte for byte; the family's whole claim is that only the
#: SUPPLY and the phase program's control turn move.
SEALED_SYSTEM_MESSAGE_SHA256 = (
    "4073f79ef25c4796b0a46cb2ac7f5d4982c83084982b87ddd8a70504090d37db"
)

#: Real, already-promoted TRAIN packets, used as SHAPE STAND-INS for the
#: exemplar key packets KU-S4a/b will need. Named as a receipt rather than as
#: literal ids so the check reads whatever that receipt actually holds.
KEY_PACKET_RECEIPT = Path(
    "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/TRAIN90-promotion.json"
)
DEV_PACKET_RECEIPT = Path(
    "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/DEV-1000-promotion.json"
)
FEATURE_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")

#: How many KEY packets the composition proof binds beside the one query.
MULTIPACKET_K = 8

_PYTEST_DURATION = re.compile(r"\s+in\s+[\d.]+s\s*$")

BODY_TESTS = (
    "tests/unit/test_llama_server_transport.py",
    "tests/unit/test_slurp_intent_candidates.py",
)


def _load_runner():
    path = REPO / "scripts" / "flights" / "run_slurp_closed_list_cell.py"
    spec = importlib.util.spec_from_file_location("saea_slurp_closed_list_runner", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load flight runner at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _trace_payloads(receipt: Mapping[str, object]) -> list[Mapping[str, object]]:
    from speech_aware_evidence_acquisition.data.lock import data_root

    run_id = str(receipt["wire_check_run_id"])
    attempt_id = str(receipt["attempt_id"])
    path = (
        Path(data_root()) / "wire-check" / run_id / attempt_id / f"{run_id}.trace.jsonl"
    )
    if not path.exists():
        raise SystemExit(f"wire-check trace not found at {path}")
    payloads: list[tuple[str, Mapping[str, object]]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("channel") == "MODEL_REQUEST":
            payloads.append((record["record_id"], record["payload"]["payload"]))
    payloads.sort(key=lambda item: item[0])
    return [payload for _, payload in payloads]


def request_half(runner, *, max_workers: int) -> dict[str, Any]:
    from speech_aware_evidence_acquisition.rails.slurp_intent_candidates import (
        VALUE_ID_PREFIX,
    )

    experiment_doc = runner.load_experiment(WIRE_EXPERIMENT)
    cells = runner.load_cells(WIRE_EXPERIMENT)
    receipts: dict[str, Mapping[str, object]] = {}
    payloads: dict[str, list[Mapping[str, object]]] = {}
    identities: dict[str, Mapping[str, object]] = {}
    for cell_id in CELLS:
        cell = cells[cell_id]
        dataset = str(cell["dataset_fragment"])
        runtime, identity = runner.build_runtime(
            cell=cell,
            dataset=dataset,
            experiment=WIRE_EXPERIMENT,
            run_id=str(experiment_doc["experiment_id"]),
            attempt_id=f"attempt-wire-kus4-{cell_id}",
            campaign_active=False,
            limit_sample_ids=runner.population_ids(experiment_doc, dataset),
            sealed_head=None,
        )
        receipt = dict(runtime.wire_check(seal_and_score=False, max_workers=max_workers))
        receipts[cell_id] = receipt
        identities[cell_id] = identity
        payloads[cell_id] = _trace_payloads(receipt)

    problems: list[str] = []
    per_cell: dict[str, Any] = {}
    supplied_by_cell: dict[str, dict[str, list[str]]] = {}
    for cell_id in CELLS:
        receipt = receipts[cell_id]
        identity = identities[cell_id]
        if receipt["model_contacts"] != 0:
            problems.append(f"{cell_id}: wire check reported a model contact")
        if not receipt["payload_keys_equal_arm_visible_fields"]:
            problems.append(f"{cell_id}: payload keys are not the arm's D2 field set")
        if identity["resolved_instruction_sha256"] != SEALED_SYSTEM_MESSAGE_SHA256:
            problems.append(
                f"{cell_id}: system message {identity['resolved_instruction_sha256'][:16]} is "
                "not the sealed comparator's"
            )
        supplied: dict[str, list[str]] = {}
        instructions: set[str] = set()
        for payload in payloads[cell_id]:
            sample_id = str(payload["sample_id"])
            evidence = payload.get("supplied_evidence") or []
            ids = [str(item["evidence_id"]) for item in evidence]
            supplied[sample_id] = ids
            if not ids:
                problems.append(f"{cell_id}/{sample_id}: no supplied candidate block")
            if any(not item.startswith(VALUE_ID_PREFIX) for item in ids):
                problems.append(
                    f"{cell_id}/{sample_id}: supplied evidence carries a non-candidate id"
                )
            history = payload.get("history") or []
            control = [turn for turn in history if turn.get("role") == "control"]
            if len(control) != 1:
                problems.append(
                    f"{cell_id}/{sample_id}: expected exactly one control turn, got "
                    f"{len(control)}"
                )
            else:
                instructions.add(str(control[0]["content"]))
            if str(payload.get("task_instruction", "")) and hashlib.sha256(
                str(payload["task_instruction"]).encode("utf-8")
            ).hexdigest() != SEALED_SYSTEM_MESSAGE_SHA256:
                problems.append(f"{cell_id}/{sample_id}: task_instruction is not the sealed one")
        if len(instructions) != 1:
            problems.append(f"{cell_id}: the four rows do not share one control turn")
        supplied_by_cell[cell_id] = supplied
        per_cell[cell_id] = {
            "arm": receipt["arm"],
            "config_hash": receipt["config_hash"],
            "protocol_hash": receipt["protocol_hash"],
            "split_id": receipt["split_id"],
            "split_identity_hash": receipt["split_identity_hash"],
            "sample_count": receipt["sample_count"],
            "contact_count": receipt["contact_count"],
            "payload_keys": receipt["payload_keys"],
            "speech_packets_verified": receipt["speech_packets_verified"],
            "model_contacts": receipt["model_contacts"],
            "system_message_sha256": identity["resolved_instruction_sha256"],
            "candidate_bank": identity.get("ku_s4_bindings", {}).get("candidate_bank"),
            "review_material": identity.get("ku_s4_bindings", {}).get("review_material"),
            "supplied_evidence_ids": {
                sample_id: sorted(ids) for sample_id, ids in sorted(supplied.items())
            },
            "supplied_block_counts": {
                sample_id: len(ids) for sample_id, ids in sorted(supplied.items())
            },
            "control_turn_sha256": sorted(
                {
                    hashlib.sha256(str(turn["content"]).encode("utf-8")).hexdigest()
                    for payload in payloads[cell_id]
                    for turn in (payload.get("history") or [])
                    if turn.get("role") == "control"
                }
            ),
            "policy": receipt.get("policy"),
            "policy_kind": receipt.get("policy_kind"),
            "contacts_per_sample": receipt.get("contacts_per_sample"),
            "phases": receipt.get("phases"),
            "phase_supply": receipt.get("phase_supply"),
            "phase_review": receipt.get("phase_review"),
            # SORTED, and the sort is the point: the runtime reports this in
            # DISPATCH order, and two runs of the same cell may dispatch four
            # rows in two orders -- recording the raw list would make this
            # receipt irreproducible while proving nothing. The per-row counts
            # keyed by sample id are in `supplied_block_counts` above.
            "typed_knowledge_blocks_sorted": sorted(
                receipt.get("typed_knowledge_blocks") or []
            ),
            "typed_knowledge_blocks_total": receipt.get("typed_knowledge_blocks_total"),
        }
        if receipt.get("policy") != "phase-direct-only-supplied-v1":
            problems.append(
                f"{cell_id}: policy is {receipt.get('policy')!r}, not the supplied "
                "direct program"
            )
        if receipt.get("contacts_per_sample") != 1:
            problems.append(
                f"{cell_id}: contacts_per_sample is {receipt.get('contacts_per_sample')!r}"
            )
        supply_receipt = receipt.get("phase_supply") or {}
        phases_supplied = [
            entry.get("spec", {}).get("phase")
            for entry in (supply_receipt.get("phases") or [])
        ]
        if phases_supplied != ["direct"]:
            problems.append(
                f"{cell_id}: phase_supply covers {phases_supplied}, expected ['direct']"
            )
        blocks = receipt.get("typed_knowledge_blocks") or []
        if not blocks or any(count <= 0 for count in blocks):
            problems.append(
                f"{cell_id}: typed_knowledge_blocks {blocks} -- a supplied phase must "
                "carry its candidates on the traced channel"
            )
        evidence_counts = sorted(len(ids) for ids in supplied.values())
        if sorted(blocks) != evidence_counts:
            problems.append(
                f"{cell_id}: typed_knowledge_blocks {sorted(blocks)} disagree with the "
                f"supplied evidence counts {evidence_counts}"
            )

    arm, twin = CELLS
    if per_cell[arm]["config_hash"] == per_cell[twin]["config_hash"]:
        problems.append("config_hash did not move between the arm and its twin")
    if per_cell[arm]["control_turn_sha256"] != per_cell[twin]["control_turn_sha256"]:
        problems.append("the arm and the twin do not ship the same control turn")
    for sample_id, ids in supplied_by_cell[arm].items():
        twin_ids = supplied_by_cell[twin].get(sample_id, [])
        if len(ids) != len(twin_ids):
            problems.append(
                f"{sample_id}: twin supplies {len(twin_ids)} blocks against the arm's {len(ids)}"
            )
        if set(ids) & set(twin_ids):
            problems.append(
                f"{sample_id}: twin shares a candidate with the arm; the twin draws from the "
                "intents the arm did NOT choose"
            )

    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "experiment": WIRE_EXPERIMENT,
        "cells": per_cell,
    }


def multipacket_half() -> dict[str, Any]:
    from speech_aware_evidence_acquisition.core.model.speech_features import (
        load_speech_feature_packets,
    )
    from speech_aware_evidence_acquisition.core.model.transport import (
        _ordered_speech_feature_content,
    )
    from speech_aware_evidence_acquisition.core.policies import ArmError, build_arm_payload
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.data.lock import data_root, load_lock
    from speech_aware_evidence_acquisition.core.base import EvidenceItem
    from speech_aware_evidence_acquisition.data.loader import SampleRef
    from speech_aware_evidence_acquisition.rails.core_client import (
        FrozenCoreClientError,
        _parse_speech_feature_messages,
    )

    problems: list[str] = []
    if not KEY_PACKET_RECEIPT.is_file() or not DEV_PACKET_RECEIPT.is_file():
        return {
            "status": "FAIL",
            "problems": [f"promotion receipt missing: {KEY_PACKET_RECEIPT}"],
        }
    dev_packets = json.loads(DEV_PACKET_RECEIPT.read_text(encoding="utf-8"))["packets"]
    key_packets = json.loads(KEY_PACKET_RECEIPT.read_text(encoding="utf-8"))["packets"]
    query = sorted(dev_packets, key=lambda entry: entry["packet_id"])[0]
    keys = sorted(key_packets, key=lambda entry: entry["packet_id"])[:MULTIPACKET_K]
    if len(keys) != MULTIPACKET_K:
        problems.append(f"only {len(keys)} promoted TRAIN packets available")

    descriptors = [
        {"packet_id": query["packet_id"], "sha256": query["packet_sha256"], "role": "query"}
    ] + [
        {"packet_id": entry["packet_id"], "sha256": entry["packet_sha256"], "role": "key"}
        for entry in keys
    ]

    # --- stage 1: the real policy -----------------------------------------
    sample_id = query["packet_id"].replace("/", ":")
    lock = load_lock(
        Path("/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
    )
    root = data_root()
    record = next(
        item
        for item in load_slurp_split(lock, root, "devel")
        if item.sample_id == sample_id
    )
    sample = SampleRef(
        carrier_lock_key="slurp",
        sample_id=record.sample_id,
        media_relpath=record.media_relpath,
        audio_seconds=record.audio_seconds,
        sample_rate_hz=16000,
    )
    candidate_block = EvidenceItem(
        evidence_id="value:intent-candidate:alarm_set",
        source_uri="knowledge-snapshot://f179f5db/value:intent-candidate:alarm_set",
        content=(
            "Candidate intent for the spoken command in this request: alarm_set "
            '(scenario "alarm", action "set").'
        ),
        provenance={
            "lock_key": "slurp",
            "relpath": "knowledge/slurp/saea-slurp-intent-candidates-v1/snapshot.json",
            "sha256": "f179f5db51413fd3141f2d0b65fd49cea35f48b67429c838badf745dc3c779c5",
        },
    )
    payload = build_arm_payload(
        "speech-feature-query",
        sample,
        "kus4-multipacket",
        "instruction",
        {"temperature": 0, "seed": 20260903},
        evidence=[candidate_block],
        speech_feature_parts=descriptors,
        speech_packet_sha256=str(query["packet_sha256"]),
        query_source="speech_features",
        key_representation_id="saea-slurp-intent-ku-s4a-v1:direct",
        matcher_policy_id="saea-slurp-intent-ku-s4a-v1",
        mmproj_loaded=False,
    )
    built = payload.get("speech_feature_parts")
    if not isinstance(built, list) or len(built) != MULTIPACKET_K + 1:
        problems.append(
            f"build_arm_payload emitted {0 if built is None else len(built)} descriptors, "
            f"expected {MULTIPACKET_K + 1}"
        )
    if sum(1 for part in built or () if part["role"] == "query") != 1:
        problems.append("the built payload does not carry exactly one query descriptor")

    # --- stage 1b: the negative controls ----------------------------------
    refusals: dict[str, str] = {}
    for label, bad in (
        ("two_queries", [dict(descriptors[0]), dict(descriptors[0], packet_id=descriptors[1]["packet_id"], sha256=descriptors[1]["sha256"])]),
        ("zero_queries", [dict(part, role="key") for part in descriptors]),
        ("unknown_role", [dict(descriptors[0]), dict(descriptors[1], role="exemplar")]),
    ):
        try:
            build_arm_payload(
                "speech-feature-query",
                sample,
                "kus4-multipacket",
                "instruction",
                {"temperature": 0, "seed": 20260903},
                evidence=[candidate_block],
                speech_feature_parts=bad,
                speech_packet_sha256=str(query["packet_sha256"]),
                query_source="speech_features",
                key_representation_id="x",
                matcher_policy_id="y",
                mmproj_loaded=False,
            )
        except ArmError as error:
            refusals[label] = str(error)
        else:
            problems.append(f"the real policy accepted a {label} descriptor list")

    # --- stage 2: the client-side parser ----------------------------------
    content: list[dict[str, object]] = [
        {"type": "input_speech_features", "speech_features": dict(part)}
        for part in descriptors
    ]
    content.append(
        {
            "type": "text",
            "text": "Candidate intent for the spoken command in this request: alarm_set "
            '(scenario "alarm", action "set").',
            "evidence_id": "value:intent-candidate:alarm_set",
            "source_uri": "knowledge-snapshot://x/value:intent-candidate:alarm_set",
            "knowledge_role": "value",
        }
    )
    try:
        _instruction, supply_parts, parsed = _parse_speech_feature_messages(
            (
                {"role": "system", "content": "instruction"},
                {"role": "user", "content": content},
            )
        )
    except FrozenCoreClientError as error:
        problems.append(f"the client parser refused a multi-packet message pair: {error}")
        supply_parts, parsed = [], []
    if len(parsed) != MULTIPACKET_K + 1:
        problems.append(
            f"the client parser returned {len(parsed)} descriptors, expected "
            f"{MULTIPACKET_K + 1}"
        )

    # --- stage 3: the transport's own content ordering --------------------
    ordered = _ordered_speech_feature_content(
        prompt_order="speech-query-prefix-v2",
        evidence_texts=[str(part["text"]) for part in supply_parts],
        feature_parts=[
            {"type": "input_speech_features", "speech_features": dict(part)}
            for part in descriptors
        ],
        state_texts=[],
        knowledge_roles=tuple("value" for _ in supply_parts),
    )
    markers = sum(
        1 for part in ordered if part.get("type") == "input_speech_features"
    )
    if markers != MULTIPACKET_K + 1:
        problems.append(
            f"the transport ordering emitted {markers} media markers, expected "
            f"{MULTIPACKET_K + 1}"
        )

    # --- stage 4: media identity ------------------------------------------
    loaded = load_speech_feature_packets(
        FEATURE_ROOT,
        tuple(
            {"packet_id": part["packet_id"], "sha256": part["sha256"]}
            for part in descriptors
        ),
        workers=4,
    )
    if len(loaded) != MULTIPACKET_K + 1:
        problems.append(
            f"the media-identity stage loaded {len(loaded)} packets, expected "
            f"{MULTIPACKET_K + 1}"
        )

    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "k_keys": MULTIPACKET_K,
        "descriptors": len(descriptors),
        "query_packet_id": query["packet_id"],
        "key_packet_ids": [entry["packet_id"] for entry in keys],
        "key_packets_are_shape_stand_ins": (
            "REAL, already-promoted TRAIN encoder packets from "
            f"{KEY_PACKET_RECEIPT.name}, used to prove the SHAPE. The KU-S4a exemplar "
            "plan's own recordings are not promoted -- 162 of 2,742 -- which is the "
            "precondition the preparation receipt prices and the preregistration makes "
            "a blocking clause."
        ),
        "stages": {
            "policy_build_arm_payload": "PASS" if not problems else "see problems",
            "policy_refusals": refusals,
            "client_parse_speech_feature_messages": len(parsed),
            "transport_content_markers": markers,
            "media_identity_packets_loaded": len(loaded),
        },
        "payload_field_set": sorted(payload),
        "sockets_opened": 0,
        "model_contacts": 0,
    }


def body_half(*, run_tests: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "proved_by": list(BODY_TESTS),
        "why_not_here": (
            "core.model.transport.LlamaServerTransport verifies an attested live session "
            "(pid, binary image and listening socket) at construction, so it cannot be "
            "built inside a model-free check; the committed unit tests build it against a "
            "self-attesting local process and a fake post(), and three of them already "
            "cover multi-packet requests."
        ),
    }
    if not run_tests:
        result["status"] = "SKIPPED"
        return result
    process = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *BODY_TESTS],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    lines = [line for line in process.stdout.strip().splitlines() if line.strip()]
    result["status"] = "PASS" if process.returncode == 0 else "FAIL"
    result["pytest_returncode"] = process.returncode
    result["pytest_summary"] = _PYTEST_DURATION.sub("", lines[-1]) if lines else ""
    if process.returncode != 0:
        result["pytest_tail"] = lines[-20:]
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--skip-request", action="store_true")
    parser.add_argument("--skip-body", action="store_true")
    args = parser.parse_args(argv)

    runner = _load_runner()
    document: dict[str, Any] = {
        "schema": "saea-slurp-kus4-wire-check-v1",
        "row_id": ROW_ID,
        "study": "speech-aware-evidence-acquisition",
        "model_contacts": 0,
        "servers_started": 0,
        "sockets_opened": 0,
        "question": (
            "does the KU-S4N arm differ from the sealed closed-list comparator by exactly "
            "the supplied candidate blocks plus the phase program's control turn, does its "
            "twin ship the same form with disjoint candidates, and does a one-query-plus-k-"
            "keys request compose through the real policy, the real client parser, the real "
            "transport ordering and the real media-identity stage"
        ),
        "multipacket": multipacket_half(),
        "body": body_half(run_tests=not args.skip_body),
    }
    document["request"] = (
        {"status": "SKIPPED", "reason": "--skip-request"}
        if args.skip_request
        else request_half(runner, max_workers=args.max_workers)
    )
    statuses = {
        half: document[half]["status"] for half in ("request", "multipacket", "body")
    }
    document["halves"] = statuses
    document["status"] = (
        "PASS"
        if all(value in ("PASS", "SKIPPED") for value in statuses.values())
        else "FAIL"
    )

    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUT_DIR / "wire-check.json"
        path.write_text(
            json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        (OUT_DIR / "MANIFEST.sha256").write_text(
            f"{digest}  wire-check.json\n", encoding="utf-8", newline="\n"
        )
        print(f"{digest}  {path}")
    else:
        print(json.dumps(document, indent=2, sort_keys=True, default=str))
    return 0 if document["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
