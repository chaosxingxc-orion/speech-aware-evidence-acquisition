#!/usr/bin/env python3
"""Build and seal the model-free G7 construction-example ground."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from dataclasses import asdict
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.a2t_construction_example_ground import (  # noqa: E402
    ConstructionExampleGround,
    build_construction_example_family_ground,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)


RUN_ID = "SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2"
PARTITION_SEED = 20260807
G5_CORPUS = REPO / "knowledge/audio2tool/g5-exhaustive-family-contracts-v1/corpus.json"
G7_ROSTER = REPO / "docs/receipts/a2t/A2T-G7-EXAMPLE-FIXED16.json"
DEFAULT_CORPUS = REPO / "knowledge/audio2tool/g7-construction-example-ground-v1/corpus.txt"
DEFAULT_STRUCTURED = (
    REPO / "knowledge/audio2tool/g7-construction-example-ground-v1/ground.json"
)
DEFAULT_RECEIPT = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g7-exhaustive-example-ground-fixed16-v1/ground-receipt.json"
)
PROMOTION_RECEIPT = Path(
    "/home/chao/feat-cache/a2t-q4km-packets-04ccc72a/A2T-G1-104-promotion.json"
)
LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g7-exhaustive-example-ground-fixed16-v1/launcher/"
    "launch_a2t_g7_fixed16.py"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _speech_tokens(roster: dict[str, object]) -> dict[str, int]:
    promotion = json.loads(PROMOTION_RECEIPT.read_text(encoding="ascii"))
    promoted = {row["packet_id"]: row for row in promotion["packets"]}
    g1 = json.loads((REPO / "docs/receipts/a2t/A2T-G1-104.json").read_text())
    g1_by_id = {row["sample_id"]: row for row in g1["items"]}
    result: dict[str, int] = {}
    for selected in roster["selected"]:
        sample_id = selected["sample_id"]
        item = g1_by_id[sample_id]
        packet_id = item["packet_id"]
        metadata = json.loads(
            (PROMOTION_RECEIPT.parent / packet_id / "packet.json").read_text(
                encoding="ascii"
            )
        )
        if (
            metadata["packet_id"] != packet_id
            or metadata["packet_sha256"] != promoted[packet_id]["packet_sha256"]
            or metadata["audio_sha256"] != item["audio_sha256"]
        ):
            raise RuntimeError("speech packet identity drift")
        result[sample_id] = sum(chunk["n_tokens"] for chunk in metadata["chunks"])
    return result


def _preflight(ground: ConstructionExampleGround, speech_max: int) -> dict[str, object]:
    spec = importlib.util.spec_from_file_location("g7_preflight_launcher", LAUNCHER)
    if spec is None or spec.loader is None:
        raise RuntimeError("G7 launcher cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.preflight_ground(ground, speech_feature_tokens_max=speech_max)


def build_ground(root: Path) -> tuple[ConstructionExampleGround, dict[str, object]]:
    """Build from construction rows while fail-closing every query boundary."""
    offline = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO))
    rows, inventory = a2t_pool_rows(lock, root)
    exposed = exposed_sample_ids(REPO)
    partition = propose_partition(rows, exposed, seed=PARTITION_SEED)
    roster = json.loads(G7_ROSTER.read_text(encoding="utf-8"))
    g7_ids = frozenset(row["sample_id"] for row in roster["selected"])
    forbidden_sources = frozenset(exposed) | frozenset(partition.eval_sample_ids) | g7_ids
    forbidden_blocks = frozenset(partition.reserved_exposed_blocks) | frozenset(
        partition.eval_blocks
    ) | frozenset(
        row.query_idx for row in rows if set(row.sample_ids) & g7_ids
    )
    ground = build_construction_example_family_ground(
        partition.construction,
        G5_CORPUS,
        forbidden_query_blocks=forbidden_blocks,
        forbidden_source_ids=forbidden_sources,
    )
    if offline.count:
        raise RuntimeError("offline guard observed an outbound attempt")
    receipt = {
        "schema": "saea-a2t-g7-construction-example-ground-build-v1",
        "experiment_id": RUN_ID,
        "execution_profile": "model-free-check",
        "ground": dict(ground.receipt),
        "ground_report": dict(ground.report),
        "speech_feature_tokens_by_sample": _speech_tokens(roster),
        "population_boundary": {
            "g7_roster_sha256": _sha256(G7_ROSTER),
            "g7_source_identity_count": len(g7_ids),
            "forbidden_source_identity_count": len(forbidden_sources),
            "forbidden_query_block_count": len(forbidden_blocks),
            "construction_unit_count": len(partition.construction),
            "pool_items": inventory["pool_items"],
        },
        "contacts": {
            "model": 0,
            "network": 0,
            "audio_service": 0,
            "tokenizer": 0,
            "scorer": 0,
            "gold": 0,
        },
        "offline_guard": {"outbound_connection_attempts": offline.count},
    }
    return ground, receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-output", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--receipt-output", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--structured-output", type=Path, default=DEFAULT_STRUCTURED)
    args = parser.parse_args()
    ground, receipt = build_ground(data_root())
    speech_max = max(receipt["speech_feature_tokens_by_sample"].values())
    receipt["prompt_fit"] = _preflight(ground, speech_max)
    args.corpus_output.parent.mkdir(parents=True, exist_ok=True)
    args.corpus_output.write_text(ground.text, encoding="ascii", newline="\n")
    structured = {
        "schema": "saea-a2t-construction-example-ground-runtime-v1",
        "ground_sha256": ground.sha256,
        "bundles": [asdict(bundle) for bundle in ground.bundles],
    }
    args.structured_output.parent.mkdir(parents=True, exist_ok=True)
    args.structured_output.write_text(
        json.dumps(structured, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
        newline="\n",
    )
    receipt["artifact"] = {
        "path": str(args.corpus_output.relative_to(REPO)).replace("\\", "/"),
        "sha256": ground.sha256,
        "ascii_bytes": len(ground.text.encode("ascii")),
        "structured_path": str(args.structured_output.relative_to(REPO)).replace(
            "\\", "/"
        ),
        "structured_sha256": _sha256(args.structured_output),
    }
    args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(receipt["ground_report"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
