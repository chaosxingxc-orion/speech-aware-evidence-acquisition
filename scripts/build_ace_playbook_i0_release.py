#!/usr/bin/env python3
"""Build and prepare the EMPTY ``ace-playbook`` release i0 (owner decisions 263 A / 266-A, 2026-10-11).

MODEL-FREE. Zero frozen-core, tool, embedding, GPU or network contacts. The single data-root write it makes is the
write-once ``ace-playbook-i0`` store release under ``$SPEECHRL_DATA_DIR`` (staging inputs under
``prepared/SAEA-SLURP-ACE-PLAYBOOK-I0/`` and the compiled release under
``knowledge/slurp/semantic/ace-playbook-i0/``).

The release is the iteration-0 playbook with zero items. ``rails.tfrl_ace_material.build_playbook_release`` turns it into one
inert anchor row addressed to the node ``planner``; the Solver slice of that store is therefore empty and the Solver route
declines every phase (the P-ACE-0 proof, ``tests/unit/test_lock_v2_3_ace_store.py``). Lock v2.3
(``rails/adapters/slurp_module_lock_v2_3.py``) declares the store at exactly the release and snapshot pins this script prints.

The registration reuses the construction scope, the permitted roster and the forbidden rosters (Fold A, Fold B, DEV-1000) of the
committed ``stage3-deltas-v1r`` registration, so the release is confined to the construction population exactly as every other
delta store is.

    python -B scripts/build_ace_playbook_i0_release.py [--data-root DIR] [--dry-run]
    python -B scripts/build_ace_playbook_i0_release.py --verify

The build REFUSES to overwrite: it stops when the staging directory, the output namespace, the committed registration or the
committed receipt already exists. ``--verify`` re-reads the committed receipt and checks every pinned byte on disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

PACKAGE = "docs/readiness/2026-10-11-slurp-tfrl-loop-v1"
REGISTRATION_RELPATH = f"{PACKAGE}/ace-playbook-i0-release-registration.json"
RECEIPT_RELPATH = f"{PACKAGE}/ace-playbook-i0-release-receipt-v1.json"
RELEASE_DIR = "prepared/SAEA-SLURP-ACE-PLAYBOOK-I0"
OUTPUT_NAMESPACE = "knowledge/slurp/semantic/ace-playbook-i0"
REGISTRATION_ID = "SAEA-SLURP-ACE-PLAYBOOK-PREPARATION-I0"
RECEIPT_SCHEMA = "saea-ace-playbook-i0-release-receipt-v1"
#: The roster pins of the committed ``stage3-deltas-v1r`` registration (docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/).
PARENT_REGISTRATION = "docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-v1r-release-registration.json"
CARRIERS = 50


class BuildError(SystemExit):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding(repo_root: Path) -> tuple[dict, str]:
    parent = json.loads((repo_root / PARENT_REGISTRATION).read_text(encoding="utf-8"))
    binding = {key: parent[key] for key in ("construction_scope", "permitted_roster", "forbidden_rosters")}
    return binding, str(parent["source_split_identity_hash"])


def _carrier_ids(data_root: Path, binding: dict) -> list[str]:
    pin = binding["permitted_roster"]
    path = data_root / pin["relpath"]
    if not path.is_file() or _sha256(path) != pin["sha256"]:
        raise BuildError(f"the permitted roster {pin['relpath']} is missing from the data root or does not hash to its pin")
    roster = json.loads(path.read_text(encoding="utf-8"))
    ids = sorted(str(item["sample_id"]) for item in roster["items"])
    if len(ids) < CARRIERS:
        raise BuildError("the permitted roster is smaller than the anchor row's carrier list")
    return ids[:CARRIERS]


def build(repo_root: Path, data_root: Path, *, dry_run: bool) -> dict:
    from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (  # noqa: PLC0415
        prepare_semantic_knowledge_store,
    )
    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415

    registration_path = repo_root / REGISTRATION_RELPATH
    receipt_path = repo_root / RECEIPT_RELPATH
    for label, path in (
        ("staging directory", data_root / RELEASE_DIR), ("output namespace", data_root / OUTPUT_NAMESPACE),
        ("registration", registration_path), ("receipt", receipt_path),
    ):
        if path.exists():
            raise BuildError(f"REFUSED: the {label} already exists ({path}); this release is write-once")
    binding, identity = _binding(repo_root)
    carriers = _carrier_ids(data_root, binding)
    playbook = ace.empty_playbook()
    if dry_run:
        rows = ace.playbook_release_rows(playbook, carrier_sample_ids=carriers, legal_intent_ids=())
        return {"dry_run": True, "iteration": playbook["iteration"], "rows": len(rows), "anchor_node": rows[0]["node_target"],
                "playbook_content_hash": playbook["content_hash"], "source_split_identity_hash": identity}
    staged = ace.build_playbook_release(
        playbook, data_root=data_root, carrier_sample_ids=carriers, legal_intent_ids=(), source_split_identity_hash=identity,
        release_dir=RELEASE_DIR, registration_binding=binding, registration_path=registration_path,
        registration_id=REGISTRATION_ID, output_namespace=OUTPUT_NAMESPACE,
    )
    result = prepare_semantic_knowledge_store(registration_path, repo_root=repo_root, data_root=data_root)
    completion = result["completion"]
    receipt = {
        "schema": RECEIPT_SCHEMA, "iteration": 0, "empty": True, "decision": "263 A / 266-A",
        "playbook_content_hash": playbook["content_hash"], "source_split_identity_hash": identity,
        "registration": {"relpath": REGISTRATION_RELPATH, "sha256": _sha256(registration_path)},
        "staging": {k: staged[k] for k in ("playbook", "authored", "source", "wrap_receipt", "row_count", "empty")},
        "release": completion["release"], "snapshot": completion["snapshot"],
        "completion": result["completion_pin"], "cache": result["cache"],
        "contacts": {"model": 0, "tool": 0, "scorer": 0},
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return receipt


def verify(repo_root: Path, data_root: Path) -> dict:
    receipt = json.loads((repo_root / RECEIPT_RELPATH).read_text(encoding="utf-8"))
    problems = []
    registration = repo_root / receipt["registration"]["relpath"]
    if _sha256(registration) != receipt["registration"]["sha256"]:
        problems.append("registration bytes differ from the receipt")
    for key in ("release", "snapshot", "completion"):
        pin = receipt[key]
        path = data_root / pin["relpath"]
        if not path.is_file():
            problems.append(f"{key} file is missing: {pin['relpath']}")
        elif key != "snapshot" and _sha256(path) != pin["sha256"]:
            problems.append(f"{key} file bytes differ from the receipt")
    if problems:
        raise BuildError("VERIFY FAILED: " + "; ".join(problems))
    return {"verified": True, "release": receipt["release"], "snapshot": receipt["snapshot"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR"))
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root:
        raise BuildError("set SPEECHRL_DATA_DIR or pass --data-root")
    repo_root, data_root = Path(args.repo_root), Path(args.data_root)
    out = verify(repo_root, data_root) if args.verify else build(repo_root, data_root, dry_run=args.dry_run)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
