#!/usr/bin/env python3
"""Build and receipt the model-free G3 plain-English card corpus.

The builder reads only the frozen Audio2Tool registry and construction
partition. It never opens gold, runtime speech, transcripts, or model and
tokenizer services. The output is a UTF-8 handbook plus a JSON receipt whose
hashes bind the registry, construction partition, and rendered corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.rails.a2t_plain_english_cards import (  # noqa: E402
    build_plain_english_card_corpus,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)
from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry  # noqa: E402


EXPERIMENT_ID = "SAEA-A2T-G3-PLAIN-ENGLISH-CARDS-BUILD"
PARTITION_SEED = 20260807


def _sha_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build(repo_root: Path, root: Path) -> tuple[str, dict[str, object]]:
    """Build twice from order permutations and return corpus text and receipt."""

    lock = load_lock(umbrella_lock_path(repo_root))
    registry = load_tool_registry(lock, root)
    rows, inventory = a2t_pool_rows(lock, root)
    exposed = exposed_sample_ids(repo_root)
    partition = propose_partition(rows, exposed, seed=PARTITION_SEED)
    evaluation_ids = frozenset(partition.eval_sample_ids)
    forbidden = exposed | evaluation_ids

    first = build_plain_english_card_corpus(
        registry,
        partition.construction,
        forbidden_sample_ids=forbidden,
        max_corpus_utf8_bytes=512_000,
        max_tool_card_utf8_bytes=6_000,
    )
    second = build_plain_english_card_corpus(
        tuple(reversed(registry)),
        tuple(reversed(partition.construction)),
        forbidden_sample_ids=forbidden,
        max_corpus_utf8_bytes=512_000,
        max_tool_card_utf8_bytes=6_000,
    )
    if first != second:
        raise RuntimeError("plain-English card build is not deterministic")

    construction_ids = tuple(
        sorted(sample_id for row in partition.construction for sample_id in row.sample_ids)
    )
    receipt = {
        "schema": "saea-a2t-g3-plain-english-card-build-receipt-v1",
        "experiment_id": EXPERIMENT_ID,
        "execution_profile": "model-free-check",
        "partition": {
            "policy_id": partition.policy_id,
            "seed": partition.seed,
            "construction_unit_count": len(partition.construction),
            "construction_sample_count": len(construction_ids),
            "construction_identity_sha256": _sha_json(construction_ids),
            "exposed_sample_count": len(exposed),
            "proposed_eval_sample_count": len(evaluation_ids),
            "proposed_eval_identity_sha256": partition.split_identity_hash(),
            "forbidden_intersection_count": 0,
        },
        "registry": {
            "tool_count": len(registry),
            "sha256": _sha_json(registry),
        },
        "corpus": {
            "sha256": first.sha256,
            "construction_access_sha256": first.construction_access_sha256,
            "utf8_bytes": len(first.corpus_text.encode("utf-8")),
            "report": dict(first.report),
            "deterministic_rebuild_equal": True,
            "source_utterances_rendered": 0,
            "source_argument_values_rendered": 0,
            "source_sample_ids_rendered": 0,
        },
        "carrier_inventory": {
            "pool_items": inventory["pool_items"],
            "pool_units": inventory["pool_units"],
            "usable_units": inventory["usable_units"],
        },
        "contacts": {
            "model": 0,
            "tokenizer": 0,
            "retriever": 0,
            "network": 0,
            "scorer": 0,
            "gold_runtime": 0,
            "gpu_hours": 0.0,
        },
        "rendering_proof": {
            "ascii_only": first.corpus_text.isascii(),
            "source_utterances_rendered": 0,
            "source_argument_values_rendered": 0,
            "source_sample_ids_rendered": 0,
            "test_annotations_used": False,
        },
    }
    return first.corpus_text, receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handbook-output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.handbook_output.exists() or args.receipt_output.exists():
        raise RuntimeError("build outputs must not already exist")
    text, receipt = build(REPO_ROOT, data_root())
    args.handbook_output.parent.mkdir(parents=True, exist_ok=True)
    args.handbook_output.write_text(text, encoding="utf-8", newline="\n")
    write_json_artifact(args.receipt_output, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
