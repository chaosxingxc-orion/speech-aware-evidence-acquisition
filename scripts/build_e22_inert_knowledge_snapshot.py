#!/usr/bin/env python3
"""Build the inert Earnings-22 knowledge snapshot placeholder (model-free, write-once).

``FlightRuntime._load_knowledge_snapshot`` and ``rails.runner.run_speech_native_agent_loop`` require a
validated, NON-EMPTY ``KnowledgeSnapshot`` for every phase-program contact, even one whose phases all
declare ``knowledge: "none"``; Earnings-22 has no governed knowledge. This script freezes a deterministic
one-facet, one-value placeholder so the Earnings-22 direct-only cells can pin a real hash like the
Earnings-21 and Audio2Tool cells do. A ``knowledge: "none"`` phase binds it INVISIBLY (nothing enters a
prompt, nothing is matched), so the placeholder carries no task signal. It is bound to no dataset sample:
its single "source sample" id is a synthetic label and its split identity hash is the SHA-256 of a fixed
label, never a DEV/TEST roster.

Run: ``PYTHONDONTWRITEBYTECODE=1 python -B scripts/build_e22_inert_knowledge_snapshot.py [--write]``.
Without ``--write`` it only prints the document hash. The asset lives under the data root (never in Git).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

RELPATH = "knowledge/e22/inert/all-off-placeholder-v1/snapshot.json"
SNAPSHOT_ID = "SAEA-E22-INERT-ALL-OFF-PLACEHOLDER-V1"
BUILDER_POLICY_ID = "saea-inert-placeholder-snapshot-v1"
SPLIT_IDENTITY_LABEL = "saea-e22-inert-knowledge-placeholder-v1"
SAMPLE_ID = "e22-inert-placeholder-sample"
FACET_ID = "e22-inert-placeholder-facet"
VALUE_ID = "e22-inert-placeholder-value"


def build_snapshot():
    from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: PLC0415
        KeyFacet, KnowledgeSnapshot, ValueBundle,
    )

    facet = KeyFacet(
        facet_id=FACET_ID, dimension="inert-placeholder", representation_kind="text",
        representation="inert placeholder facet that is never matched",
        source_sample_ids=(SAMPLE_ID,),
    )
    value = ValueBundle(
        value_id=VALUE_ID, content="inert placeholder value that is never supplied",
        associated_facet_ids=(FACET_ID,), source_sample_ids=(SAMPLE_ID,),
        provenance_refs=("e22-inert-placeholder-v1",),
    )
    return KnowledgeSnapshot(
        snapshot_id=SNAPSHOT_ID,
        source_split_identity_hash=hashlib.sha256(SPLIT_IDENTITY_LABEL.encode("utf-8")).hexdigest(),
        source_sample_ids=(SAMPLE_ID,), builder_policy_id=BUILDER_POLICY_ID,
        facets=(facet,), values=(value,), source_partition_role="external-governed",
    ).validate()


def frozen_bytes() -> bytes:
    document = build_snapshot().frozen_json()
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the asset under the data root (write-once)")
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        parser.error("PYTHONDONTWRITEBYTECODE=1 is required")
    payload = frozen_bytes()
    snapshot = build_snapshot()
    result = {"relpath": RELPATH, "content_hash": snapshot.content_hash(),
              "file_sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
    if args.write:
        from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: PLC0415

        path = Path(data_root()) / RELPATH
        if path.exists():
            if path.read_bytes() != payload:
                print("refusing: existing asset differs from the deterministic build", file=sys.stderr)
                return 1
            result["status"] = "VERIFIED_EXISTING"
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            result["status"] = "WRITTEN"
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
