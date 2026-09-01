"""Run the preregistered aggregate-only post-contact headroom audit once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[5]

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal study src directory")

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    a2t_postcontact_headroom as headroom,
)
from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    require_clean_study_repo,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    load_expected_calls,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (  # noqa: E402
    parse_tool_calls_text,
    score_item,
)

RUN_ID = "SAEA-A2T-MF-POSTCONTACT-HEADROOM-V1"
SOURCE_RUN_ID = "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2"
SPLIT_IDENTITY_SHA256 = (
    "401a28684adea908c80363df0815c9ce04b0ffa46a654975b129d4b69e60f8a1"
)
RECEIPT = REPO / "docs/receipts/a2t/A2T-CPV2-104.json"
RECEIPT_SHA256 = (
    "8f47922124c61f92fee03273c1165eb1f8f97048d910ddd4a6a7243906d78783"
)
M0_RELPATH = Path(
    f"runs/{SOURCE_RUN_ID}/flight-20260901T223557Z/m0-direct/"
    f"{SOURCE_RUN_ID}.outputs.jsonl"
)
MATCHED_RELPATH = Path(
    f"runs/{SOURCE_RUN_ID}/flight-20260901T225026Z/matched-composite/"
    f"{SOURCE_RUN_ID}.outputs.jsonl"
)
M0_SHA256 = "9efc91d7362e40255a25d099b3fb464b32ca87228f96c4db5c0aba0edcbdf400"
MATCHED_SHA256 = (
    "4f41183d01a5246a76944ad48843936fb8fe08907a84f55784079feb0c1afc9b"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> None:
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} SHA-256 drift: {actual} != {expected}")


def _read_object(path: Path) -> Mapping[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"JSON document is not an object: {path}")
    return value


def _response_map(path: Path) -> dict[str, str]:
    indexed: dict[str, str] = {}
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        row = json.loads(line)
        if not isinstance(row, Mapping):
            raise RuntimeError(f"{path} line {line_number} is not an object")
        sample_id = row.get("sample_id")
        text = row.get("text")
        if not isinstance(sample_id, str) or not isinstance(text, str):
            raise RuntimeError(f"{path} line {line_number} lacks identity or text")
        if sample_id in indexed:
            raise RuntimeError(f"{path} duplicates sample_id {sample_id!r}")
        indexed[sample_id] = text
    return indexed


def _receipt_ids() -> tuple[str, ...]:
    _require_hash(RECEIPT, RECEIPT_SHA256, "cohort receipt")
    receipt = _read_object(RECEIPT)
    items = receipt.get("items")
    if (
        receipt.get("count") != 104
        or receipt.get("run_identity_hash") != SPLIT_IDENTITY_SHA256
        or not isinstance(items, list)
    ):
        raise RuntimeError("cohort receipt identity drift")
    identities = tuple(
        str(item["sample_id"])
        for item in items
        if isinstance(item, Mapping) and isinstance(item.get("sample_id"), str)
    )
    if len(identities) != 104 or len(set(identities)) != 104:
        raise RuntimeError("cohort receipt sample identities drift")
    return identities


def run_read(root: Path) -> dict[str, object]:
    study_commit = require_clean_study_repo(REPO)
    offline = arm_offline_guard()
    m0_path = root / M0_RELPATH
    matched_path = root / MATCHED_RELPATH
    _require_hash(m0_path, M0_SHA256, "M0 outputs")
    _require_hash(matched_path, MATCHED_SHA256, "matched outputs")
    identities = _receipt_ids()
    m0 = _response_map(m0_path)
    matched = _response_map(matched_path)
    if set(m0) != set(identities) or set(matched) != set(identities):
        raise RuntimeError("paired outputs do not equal the frozen cohort")
    lock = load_lock(umbrella_lock_path(REPO))
    expected = load_expected_calls(lock, root, repo_root=REPO)
    if not set(identities).issubset(expected):
        raise RuntimeError("governed gold lacks one or more frozen identities")
    records: list[headroom.PairedExactRecord] = []
    for sample_id in identities:
        m0_calls, m0_parsed = parse_tool_calls_text(m0[sample_id])
        matched_calls, matched_parsed = parse_tool_calls_text(matched[sample_id])
        m0_score = score_item(expected[sample_id], m0_calls)
        matched_score = score_item(expected[sample_id], matched_calls)
        records.append(
            headroom.PairedExactRecord(
                sample_id=sample_id,
                m0_exact=int(m0_score.exact_match),
                matched_exact=int(matched_score.exact_match),
                m0_text=m0[sample_id],
                matched_text=matched[sample_id],
                m0_parsed=m0_parsed,
                matched_parsed=matched_parsed,
            )
        )
    result = headroom.analyse(records)
    if result.n_samples != 104:
        raise RuntimeError("headroom audit did not score all 104 frozen pairs")
    return {
        "schema": "saea-a2t-postcontact-headroom-result-v1",
        "experiment_id": RUN_ID,
        "study_commit": study_commit,
        "execution_profile": "model-free-check",
        "claim_status": "exposed-cohort aggregate feasibility only",
        "source_hashes": {
            "cohort_receipt": RECEIPT_SHA256,
            "m0_outputs": M0_SHA256,
            "matched_outputs": MATCHED_SHA256,
            "split_identity": SPLIT_IDENTITY_SHA256,
        },
        "audit": result.as_json(),
        "decision": (
            "permit only a separately preregistered model-free post-contact controller screen"
            if result.postcontact_headroom_present
            else "close post-contact arbitration on the sealed CPV2 surface"
        ),
        "contacts": {
            "frozen_core": 0,
            "retriever": 0,
            "embedding_tool": 0,
            "tokenizer": 0,
            "http_or_socket": 0,
            "audio_seconds": 0,
            "gpu_hours": 0.0,
        },
        "offline_guard": {
            "outbound_connection_attempts": offline.count,
            "targets": [],
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_read(data_root())
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
