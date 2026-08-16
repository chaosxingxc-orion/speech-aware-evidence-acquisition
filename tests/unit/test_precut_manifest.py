"""Unit tests for ``scripts/precut_manifest.py`` (PRE Track A): hash-verify a
synthetic slice corpus against synthetic obs-derivation records, no real
data dependency."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "precut_manifest.py"

RUN_ID = "TEST-RUN"
CARRIER = "earnings21-original"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("precut_manifest", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _World:
    """One call's slice dir + obs-derivation record, byte-consistent by
    construction; individual tests corrupt/delete/add files afterwards."""

    def __init__(self, tmp_path: Path, sample_id: str, slice_contents: list[bytes]) -> None:
        self.data_root = tmp_path / "data"
        self.sample_id = sample_id
        self.call_dir = self.data_root / "derived" / "obs-slices" / RUN_ID / sample_id
        self.call_dir.mkdir(parents=True)
        self.attempt_dir = self.data_root / "runs" / RUN_ID / "attempt-20260101T000000Z-abc123"
        self.attempt_dir.mkdir(parents=True)

        slices = []
        for iteration, content in enumerate(slice_contents):
            filename = f"i{iteration:04d}.wav"
            (self.call_dir / filename).write_bytes(content)
            slices.append(
                {
                    "iteration": iteration,
                    "media_relpath": f"derived/obs-slices/{RUN_ID}/{sample_id}/{filename}",
                    "sha256": _sha256(content),
                    "bytes": len(content),
                    "start_seconds": iteration * 90.0,
                    "end_seconds": (iteration + 1) * 90.0,
                }
            )
        self.record = {
            "run_id": RUN_ID,
            "sample_id": sample_id,
            "schema": "saea-obs-derivation-v1",
            "parent_media_relpath": f"datasets/earnings21-22/earnings21/media/{sample_id}.mp3",
            "parent_sha256": "f" * 64,
            "slices": slices,
        }
        record_path = self.attempt_dir / f"{RUN_ID}.obs-derivation.{sample_id}.json"
        record_path.write_text(json.dumps(self.record), encoding="utf-8")

    def write_ids_file(self, path: Path, ids: list[str]) -> None:
        payload = {"items": [{"id": sample_id} for sample_id in ids]}
        path.write_text(json.dumps(payload), encoding="utf-8")


def test_clean_corpus_has_zero_mismatches_and_records_all_slices(tmp_path, script):
    world = _World(tmp_path, "1000001", [b"slice-a" * 10, b"slice-b" * 12, b"slice-c" * 5])
    manifest = script.build_manifest(
        data_root=world.data_root,
        run_id=RUN_ID,
        ids=["1000001"],
        carrier_lock_key=CARRIER,
        split_name="test-split",
        workers=4,
    )
    assert manifest["schema"] == "saea-precut-manifest-v1"
    assert manifest["cross_verification"]["mismatches"] == []
    assert manifest["failures"] == []
    assert manifest["cross_verification"]["records_compared"] == 3
    assert manifest["per_call"]["1000001"]["slice_count"] == 3
    assert manifest["throughput"]["workers"] == 4
    assert manifest["throughput"]["wall_seconds"] >= 0


def test_split_identity_hash_matches_slash_convention(tmp_path, script):
    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

    world = _World(tmp_path, "1000001", [b"only-slice"])
    manifest = script.build_manifest(
        data_root=world.data_root,
        run_id=RUN_ID,
        ids=["1000001"],
        carrier_lock_key=CARRIER,
        split_name="test-split",
        workers=2,
    )
    expected = split_identity_hash(prefixed(CARRIER, ["1000001"]))
    assert manifest["split"]["split_identity_hash"] == expected


def test_tampered_byte_is_reported_as_hash_mismatch(tmp_path, script):
    world = _World(tmp_path, "1000001", [b"original-bytes"])
    # Corrupt the on-disk slice after the record was frozen.
    (world.call_dir / "i0000.wav").write_bytes(b"tampered-bytes!!")

    manifest = script.build_manifest(
        data_root=world.data_root,
        run_id=RUN_ID,
        ids=["1000001"],
        carrier_lock_key=CARRIER,
        split_name="test-split",
        workers=2,
    )
    mismatches = manifest["cross_verification"]["mismatches"]
    assert len(mismatches) == 1
    assert mismatches[0]["reason"] == "hash_or_size_mismatch"
    assert mismatches[0]["sample_id"] == "1000001"


def test_missing_file_is_reported_as_missing_on_disk(tmp_path, script):
    world = _World(tmp_path, "1000001", [b"slice-a", b"slice-b"])
    (world.call_dir / "i0001.wav").unlink()

    manifest = script.build_manifest(
        data_root=world.data_root,
        run_id=RUN_ID,
        ids=["1000001"],
        carrier_lock_key=CARRIER,
        split_name="test-split",
        workers=2,
    )
    mismatches = manifest["cross_verification"]["mismatches"]
    assert len(mismatches) == 1
    assert mismatches[0]["reason"] == "missing_on_disk"
    assert mismatches[0]["iteration"] == 1


def test_extra_file_not_in_record_is_reported(tmp_path, script):
    world = _World(tmp_path, "1000001", [b"slice-a"])
    (world.call_dir / "i0099.wav").write_bytes(b"unexpected-extra-slice")

    manifest = script.build_manifest(
        data_root=world.data_root,
        run_id=RUN_ID,
        ids=["1000001"],
        carrier_lock_key=CARRIER,
        split_name="test-split",
        workers=2,
    )
    mismatches = manifest["cross_verification"]["mismatches"]
    assert len(mismatches) == 1
    assert mismatches[0]["reason"] == "extra_file_not_in_record"
    assert mismatches[0]["filename"] == "i0099.wav"


def test_missing_obs_derivation_record_is_a_failure_not_a_mismatch(tmp_path, script):
    world = _World(tmp_path, "1000001", [b"slice-a"])

    manifest = script.build_manifest(
        data_root=world.data_root,
        run_id=RUN_ID,
        ids=["1000001", "9999999"],
        carrier_lock_key=CARRIER,
        split_name="test-split",
        workers=2,
    )
    assert manifest["cross_verification"]["mismatches"] == []
    assert len(manifest["failures"]) == 1
    assert manifest["failures"][0]["sample_id"] == "9999999"
    assert "9999999" not in manifest["per_call"]


def test_cli_exits_nonzero_and_writes_manifest_on_mismatch(tmp_path, script, capsys):
    world = _World(tmp_path, "1000001", [b"original"])
    (world.call_dir / "i0000.wav").write_bytes(b"corrupted")
    ids_file = tmp_path / "ids.json"
    world.write_ids_file(ids_file, ["1000001"])
    out_path = tmp_path / "out" / "manifest.json"

    exit_code = script.main(
        [
            "--data-root",
            str(world.data_root),
            "--run-id",
            RUN_ID,
            "--ids-file",
            str(ids_file),
            "--carrier-lock-key",
            CARRIER,
            "--workers",
            "2",
            "--out",
            str(out_path),
        ]
    )
    assert exit_code == 1
    assert out_path.is_file()
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(written["cross_verification"]["mismatches"]) == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err


def test_cli_exits_zero_on_clean_corpus(tmp_path, script):
    world = _World(tmp_path, "1000001", [b"slice-a", b"slice-b"])
    ids_file = tmp_path / "ids.json"
    world.write_ids_file(ids_file, ["1000001"])
    out_path = tmp_path / "out" / "manifest.json"

    exit_code = script.main(
        [
            "--data-root",
            str(world.data_root),
            "--run-id",
            RUN_ID,
            "--ids-file",
            str(ids_file),
            "--carrier-lock-key",
            CARRIER,
            "--workers",
            "2",
            "--out",
            str(out_path),
        ]
    )
    assert exit_code == 0
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["cross_verification"]["mismatches"] == []
    assert written["failures"] == []


def test_deterministic_across_repeated_calls(tmp_path, script):
    world = _World(tmp_path, "1000001", [b"slice-a", b"slice-b", b"slice-c"])
    first = script.build_manifest(
        data_root=world.data_root,
        run_id=RUN_ID,
        ids=["1000001"],
        carrier_lock_key=CARRIER,
        split_name="test-split",
        workers=3,
    )
    second = script.build_manifest(
        data_root=world.data_root,
        run_id=RUN_ID,
        ids=["1000001"],
        carrier_lock_key=CARRIER,
        split_name="test-split",
        workers=3,
    )
    # Every field except the timestamp and wall-clock/throughput numbers is
    # byte-identical across repeated runs against unchanged bytes.
    for key in ("split", "per_call", "cross_verification", "failures"):
        assert first[key] == second[key]
