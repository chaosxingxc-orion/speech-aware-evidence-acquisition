"""Build the second fresh 104-row Audio2Tool discovery roster.

This is an identity and carrier-metadata operation. It performs no model,
network, tokenizer, scorer, or inference contact and never writes over an
existing receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import wave


REPO = Path(__file__).resolve().parents[4]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from speech_aware_evidence_acquisition.analysis.a2t_fresh_agentloop_roster import (  # noqa: E402
    build_partition_flight_receipt,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.a2t_frozen_semantic_assets import (  # noqa: E402
    CONSTRUCTION_PARTITION_IDENTITY_SHA256,
    CONSTRUCTION_ROWS_SHA256,
    SEMANTIC_INDEX_SHA256,
    SOURCE_RECEIPT_SHA256,
    SOURCE_VECTOR_SHA256,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)


CHECK_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = CHECK_DIR / "flight-roster-receipt.json"
PRIOR_ROSTER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-fresh-agentloop-roster/flight-roster-receipt.json"
)
EXPECTED_PRIOR_ROSTER_SHA256 = (
    "457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e"
)
PARTITION_SEED = 20260807
PARTITION_PER_TIER = 50
ROSTER_PER_TIER = 13
ROSTER_NAMESPACE = "speech-aware-evidence-acquisition-a2t-select-fill-fresh-v1"
SPLIT_NAME = "A2T-SELECT-FILL-FRESH-FLIGHT"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read exact JSON artifact {path}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON artifact {path} must contain one object")
    return value


def _audio_metadata(path: Path, *, relative_path: str) -> tuple[str, str, float]:
    if not path.is_file() or path.suffix.casefold() != ".wav":
        raise RuntimeError(f"roster carrier must be one existing WAV file: {path}")
    try:
        with wave.open(str(path), "rb") as handle:
            frame_rate = handle.getframerate()
            frame_count = handle.getnframes()
    except (OSError, wave.Error) as error:
        raise RuntimeError(f"cannot inspect WAV carrier {path}: {error}") from error
    if frame_rate <= 0 or frame_count <= 0:
        raise RuntimeError(f"WAV carrier has invalid duration metadata: {path}")
    return relative_path, _sha256_file(path), frame_count / frame_rate


def build(*, data_root: Path) -> dict[str, object]:
    lock_path = umbrella_lock_path(REPO)
    lock = load_lock(lock_path)
    rows, inventory = a2t_pool_rows(lock, data_root)
    partition = propose_partition(
        rows,
        exposed_sample_ids(REPO),
        seed=PARTITION_SEED,
        per_tier=PARTITION_PER_TIER,
    )
    if (
        partition.split_identity_hash()
        != CONSTRUCTION_PARTITION_IDENTITY_SHA256
    ):
        raise RuntimeError("frozen construction/evaluation partition identity drift")
    if len(partition.construction) != 12_601:
        raise RuntimeError("frozen construction row count drift")
    if _sha256_file(PRIOR_ROSTER) != EXPECTED_PRIOR_ROSTER_SHA256:
        raise RuntimeError("prior 104-row roster bytes drift")
    prior = _load_json(PRIOR_ROSTER)
    prior_items = prior.get("items")
    if not isinstance(prior_items, list) or len(prior_items) != 104:
        raise RuntimeError("prior roster must contain exactly 104 identity rows")

    by_item = {(row.tier, item): row for row in rows for item in row.item_ids}
    metadata: dict[str, tuple[str, str, float]] = {}
    for tier, item_id, _text, _tool in partition.eval_items:
        row = by_item[(tier, item_id)]
        sample_id = f"{tier}:{item_id:06d}"
        relative_path = row.media_relpath_by_sample_id[sample_id]
        metadata[sample_id] = _audio_metadata(
            data_root / relative_path,
            relative_path=relative_path,
        )

    receipt = build_partition_flight_receipt(
        rows,
        partition,
        exposed_sample_ids=exposed_sample_ids(REPO),
        excluded_identity_rows=prior_items,
        per_tier=ROSTER_PER_TIER,
        namespace=ROSTER_NAMESPACE,
        split_name=SPLIT_NAME,
        carrier_metadata=metadata,
    )
    receipt["partition_identity_hash"] = partition.split_identity_hash()
    receipt["source"] = {
        "lock_sha256": _sha256_file(lock_path),
        "pool_rows": len(rows),
        "pool_items": inventory["pool_items"],
    }
    receipt["prior_roster_exclusion"] = {
        "path": PRIOR_ROSTER.relative_to(REPO).as_posix(),
        "sha256": EXPECTED_PRIOR_ROSTER_SHA256,
        "split_identity_hash": prior.get("split_identity_hash"),
        "count": len(prior_items),
    }
    receipt["frozen_construction_assets"] = {
        "construction_rows_sha256": CONSTRUCTION_ROWS_SHA256,
        "embedding_receipt_sha256": SOURCE_RECEIPT_SHA256,
        "embedding_vector_sha256": SOURCE_VECTOR_SHA256,
        "semantic_index_sha256": SEMANTIC_INDEX_SHA256,
        "new_embedding_contacts": 0,
    }
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing roster receipt: {output}")
    receipt = build(data_root=args.data_root.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "sha256": _sha256_file(output),
                "count": receipt["count"],
                "split_identity_hash": receipt["split_identity_hash"],
                "contacts": receipt["contacts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
