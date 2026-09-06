#!/usr/bin/env python3
"""CLI: EVO-S1 construction capacity on SLURP TRAIN (MODEL-FREE, zero contacts).

Exposure row ``SAEA-SLURP-MF-EVO-CONSTRUCTION-CAPACITY-V1``, registered before
the first count; the arithmetic lives in ``analysis.slurp_evo_capacity``.
Authority ``docs/readiness/2026-09-05-three-dimension-experiment-program.md``
sections 4c and 5.

ZERO CONTACTS: no frozen core, tokenizer, embedder, retriever, scorer,
network, GPU or audio decode. Governed TRAIN metadata plus two committed
receipts. ``--write`` lands the receipt; without it the census only prints.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.slurp_evo_capacity import (  # noqa: E402
    EXEMPLAR_QUOTA_PER_SCENARIO,
    FOLD_QUOTA_PER_SCENARIO,
    census_document,
    load_schemas,
    train_units,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)

AUTHORITY = "docs/readiness/2026-09-05-three-dimension-experiment-program.md"
EXPOSURE_ROW_ID = "SAEA-SLURP-MF-EVO-CONSTRUCTION-CAPACITY-V1"
DEV_RECEIPT = REPO_ROOT / "docs/receipts/probe-samples/DEV-1000.json"
SCHEMA_RECEIPT = REPO_ROOT / "docs/receipts/knowledge/slurp-intent-slot-schema-v1.json"
OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-slurp-evo-construction-capacity"
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fold-quota", type=int, default=FOLD_QUOTA_PER_SCENARIO)
    parser.add_argument(
        "--exemplar-quota", type=int, default=EXEMPLAR_QUOTA_PER_SCENARIO
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    units = train_units(lock, root)
    schema_full, schema_committed = load_schemas(lock, root)
    committed = _read_json(SCHEMA_RECEIPT)
    if committed["content_hash"] != schema_committed.content_hash():
        raise SystemExit(
            "refusing to write: the committed slot-schema receipt does not reproduce "
            f"({committed['content_hash']} vs {schema_committed.content_hash()})"
        )
    dev_receipt = _read_json(DEV_RECEIPT)

    document = census_document(
        units,
        schema_full=schema_full,
        schema_committed={
            intent: len(schema_committed.intents[intent].types)
            for intent in schema_committed.intent_ids
        },
        dev_mixture=dev_receipt["scenario_allocation"],
        dev_receipt=dev_receipt,
        fold_quota=args.fold_quota,
        exemplar_quota=args.exemplar_quota,
        shared={
            "authority": AUTHORITY,
            "exposure_row": EXPOSURE_ROW_ID,
            "generator": "scripts/build_slurp_evo_construction_capacity.py",
            "artifact_a0": {
                "receipt": "docs/receipts/knowledge/slurp-intent-slot-schema-v1.json",
                "receipt_sha256": _sha256(SCHEMA_RECEIPT),
                "content_hash": committed["content_hash"],
                "rendered_full_text": committed["rendered_full_text"],
                "totals": committed["totals"],
                "reproduced": True,
            },
            "offline_guard": {
                "exposure_row": EXPOSURE_ROW_ID,
                "outbound_connection_attempts": attempts.count,
                "attempted_targets": list(attempts.targets),
            },
        },
    )

    population = document["population"]
    print(
        f"TRAIN: {population['utterances']} utterances, "
        f"{population['recordings']} recordings "
        f"({population['headset_recordings']} headset / "
        f"{population['far_field_recordings']} far-field), "
        f"{population['speakers']} speakers, {population['scenarios']} scenarios, "
        f"{population['intents']} intents"
    )
    for row in document["capacity"]:
        print(
            f"{row['scenario']:>16}: {row['train_utterances']:>5} utterances "
            f"(+{row['headroom_utterances']} over need), "
            f"{row['utterances_with_entities']:>5} with entities "
            f"(+{row['headroom_exemplar_utterances']} over the exemplar quota)"
        )
    print(f"verdict: {json.dumps(document['verdict'], sort_keys=True)}")
    print(f"offline guard: {attempts.count} outbound connection attempts")
    if not args.write:
        print("(print only; pass --write to land the receipt)")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "capacity.json"
    if path.exists():
        raise SystemExit(f"refusing to overwrite an existing receipt: {path}")
    path.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {path.relative_to(REPO_ROOT)} sha256={_sha256(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
