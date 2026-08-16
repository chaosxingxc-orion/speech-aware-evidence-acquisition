"""Unit tests for ``scripts/build_entity_inventory.py`` (PRE Track A,
RUNTIME-PROHIBITED gold-side tool). Uses the shared ``synthetic_world``
fixture (tests/unit/conftest.py) -- real layer layouts, fake bytes -- so
``data.references.reference_entity_mentions`` is exercised exactly as
``core.scorers`` exercises it, with no real data dependency."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.references import EntityMention

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_entity_inventory.py"
CARRIER = "earnings21-original"


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("build_entity_inventory", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_nlp(path: Path, rows: list[tuple[str, str]]) -> None:
    lines = ["token|speaker|tags|wer_tags"]
    for token, wer_tags in rows:
        lines.append(f"{token}|0||{wer_tags}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_sidecar(path: Path, mapping: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping), encoding="utf-8")


def _seed_valid_entities(world, sample_id: str) -> None:
    nlp = world.e21 / "transcripts" / "nlp_references" / f"{sample_id}.nlp"
    _write_nlp(
        nlp,
        [
            ("The", "[]"),
            ("Acme", "['0']"),
            ("Corporation", "['0']"),
            ("reported", "[]"),
            ("March", "['1']"),
            ("2020", "['1']"),
        ],
    )
    sidecar = world.e21 / "transcripts" / "wer_tags" / f"{sample_id}.wer_tag.json"
    _write_sidecar(sidecar, {"0": {"entity_type": "ORG"}, "1": {"entity_type": "DATE"}})


# ---------------------------------------------------------------------------
# mention_record: span computation
# ---------------------------------------------------------------------------


def test_mention_record_contiguous_span(script):
    mention = EntityMention(
        entity_id="0", entity_type="ORG", token_indices=(1, 2), tokens=("Acme", "Corporation")
    )
    record = script.mention_record(mention)
    assert record == {
        "entity_id": "0",
        "entity_type": "ORG",
        "token_indices": [1, 2],
        "tokens": ["Acme", "Corporation"],
        "span": {"start_index": 1, "end_index": 2, "contiguous": True},
    }


def test_mention_record_non_contiguous_span(script):
    mention = EntityMention(
        entity_id="0", entity_type="CARDINAL", token_indices=(0, 3), tokens=("Q3", "Q3")
    )
    record = script.mention_record(mention)
    assert record["span"] == {"start_index": 0, "end_index": 3, "contiguous": False}


# ---------------------------------------------------------------------------
# build_call_inventory: runtime_prohibited flag + shape
# ---------------------------------------------------------------------------


def test_build_call_inventory_carries_runtime_prohibited_flag(synthetic_world, script):
    _seed_valid_entities(synthetic_world, "4000001")
    lock = load_lock(synthetic_world.lock_path)
    document = script.build_call_inventory(lock, synthetic_world.data_root, CARRIER, "4000001")
    assert document["runtime_prohibited"] is True
    assert document["note"] == script.RUNTIME_PROHIBITED_NOTE
    assert document["entity_count"] == 2
    entity_ids = {mention["entity_id"] for mention in document["mentions"]}
    assert entity_ids == {"0", "1"}


# ---------------------------------------------------------------------------
# build_inventory: multi-call orchestration, coverage, failures
# ---------------------------------------------------------------------------


def test_build_inventory_covers_valid_calls_and_records_failures(tmp_path, synthetic_world, script):
    _seed_valid_entities(synthetic_world, "4000001")
    _seed_valid_entities(synthetic_world, "4000002")
    # 4000003 is left at conftest's DEFAULT synthetic content (header-only
    # .nlp, no wer_tags column) -- a clean ReferenceError case.
    lock = load_lock(synthetic_world.lock_path)
    out_dir = tmp_path / "entity-inventory"

    manifest, manifest_path, manifest_sha256 = script.build_inventory(
        data_root=synthetic_world.data_root,
        lock=lock,
        carrier_lock_key=CARRIER,
        ids=["4000001", "4000002", "4000003"],
        out_dir=out_dir,
        workers=12,
        split_name="test-split",
    )

    assert set(manifest["per_sample"]) == {"4000001", "4000002"}
    assert len(manifest["failures"]) == 1
    assert manifest["failures"][0]["sample_id"] == "4000003"
    assert manifest["runtime_prohibited"] is True
    assert manifest["note"] == script.RUNTIME_PROHIBITED_NOTE
    assert manifest_path.is_file()
    assert manifest_path.read_bytes()  # non-empty, hashed
    assert isinstance(manifest_sha256, str) and len(manifest_sha256) == 64

    # Per-call files are written and each carries the same flag.
    per_call_doc = json.loads((out_dir / "4000001.json").read_text(encoding="utf-8"))
    assert per_call_doc["runtime_prohibited"] is True
    assert per_call_doc["note"] == script.RUNTIME_PROHIBITED_NOTE
    assert per_call_doc["entity_count"] == 2


def test_split_identity_hash_matches_slash_convention(tmp_path, synthetic_world, script):
    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

    _seed_valid_entities(synthetic_world, "4000001")
    lock = load_lock(synthetic_world.lock_path)
    manifest, _path, _sha = script.build_inventory(
        data_root=synthetic_world.data_root,
        lock=lock,
        carrier_lock_key=CARRIER,
        ids=["4000001"],
        out_dir=tmp_path / "out",
        workers=12,
        split_name="test-split",
    )
    expected = split_identity_hash(prefixed(CARRIER, ["4000001"]))
    assert manifest["split"]["split_identity_hash"] == expected


def test_workers_are_capped_by_id_count_without_error(tmp_path, synthetic_world, script):
    _seed_valid_entities(synthetic_world, "4000001")
    lock = load_lock(synthetic_world.lock_path)
    manifest, _path, _sha = script.build_inventory(
        data_root=synthetic_world.data_root,
        lock=lock,
        carrier_lock_key=CARRIER,
        ids=["4000001"],
        out_dir=tmp_path / "out",
        workers=999,
        split_name="test-split",
    )
    assert manifest["throughput"]["workers"] == 999
    assert set(manifest["per_sample"]) == {"4000001"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_exit_code_zero_when_all_ids_covered(tmp_path, synthetic_world, script):
    _seed_valid_entities(synthetic_world, "4000001")
    ids_file = tmp_path / "ids.json"
    ids_file.write_text(json.dumps({"items": [{"id": "4000001"}]}), encoding="utf-8")
    out_dir = tmp_path / "out"

    exit_code = script.main(
        [
            "--ids-file",
            str(ids_file),
            "--carrier-lock-key",
            CARRIER,
            "--data-root",
            str(synthetic_world.data_root),
            "--lock-path",
            str(synthetic_world.lock_path),
            "--out-dir",
            str(out_dir),
            "--workers",
            "12",
        ]
    )
    assert exit_code == 0
    assert (out_dir / "4000001.json").is_file()
    assert (out_dir / "manifest.json").is_file()


def test_cli_exit_code_nonzero_on_any_failure(tmp_path, synthetic_world, script, capsys):
    # 4000003 keeps conftest's default content (no wer_tags column -> fails).
    ids_file = tmp_path / "ids.json"
    ids_file.write_text(json.dumps({"items": [{"id": "4000003"}]}), encoding="utf-8")
    out_dir = tmp_path / "out"

    exit_code = script.main(
        [
            "--ids-file",
            str(ids_file),
            "--carrier-lock-key",
            CARRIER,
            "--data-root",
            str(synthetic_world.data_root),
            "--lock-path",
            str(synthetic_world.lock_path),
            "--out-dir",
            str(out_dir),
            "--workers",
            "12",
        ]
    )
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err
