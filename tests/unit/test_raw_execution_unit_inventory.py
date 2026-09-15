"""Exact raw-window source reuse, without decoding, encoding or model contact."""
import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.model.slices import SliceRecord, SliceRegistry
from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_windows import (
    WindowFeatureEncoderIdentity, WindowRequestBatch,
    load_raw_execution_unit_roster, prepare_window_feature_inventory,
)

def _world(tmp_path):
    data = tmp_path / "data"
    parent = data / "dataset/parent.wav"
    parent.parent.mkdir(parents=True)
    parent.write_bytes(b"original synthetic parent")
    sample = SimpleNamespace(sample_id="parent", media_relpath="dataset/parent.wav", audio_seconds=2.0)
    registry = SliceRegistry(data_root=data, run_id="source-run", parent_facts={"parent": (sample.media_relpath, 2.0)})
    records = []
    for i in range(2):
        rel = registry.slice_relpath("parent", i)
        path = data / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"window{i}".encode())
        records.append(SliceRecord("parent", sample.media_relpath, hashlib.sha256(parent.read_bytes()).hexdigest(),
            float(i), float(i+1), 1.0, 16000, rel, hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, i))
    batch = WindowRequestBatch(
        tuple({"sample_id":"parent", "media_relpath":x.media_relpath, "audio_seconds":1.0, "sample_rate_hz":16000} for x in records),
        ("parent#w0001", "parent#w0002"),
        tuple(x.trace_view() for x in records))
    inventory = data / "prepared/inventory.json"
    prepare_window_feature_inventory(inventory, batches={"batch":batch}, data_root=data,
        encoder_identity=WindowFeatureEncoderIdentity("a"*64, "b"*40, "c"*64, "d"*64))
    spec = {"relpath":"prepared/inventory.json", "sha256":hashlib.sha256(inventory.read_bytes()).hexdigest(),
        "batch":"batch", "registry_run_id":"source-run", "unit_count":2, "split_identity_hash":"e"*64}
    return data, sample, records, inventory, spec

def _load(world):
    data, sample, _, _, spec = world
    return load_raw_execution_unit_roster(spec, data_root=data, samples=(sample,), split_identity_hash="e"*64)

def test_reuses_full_raw_slice_inventory_and_one_parent_identity(tmp_path):
    world = _world(tmp_path)
    roster, registry = _load(world)
    assert tuple(u.request_key for u in roster.units) == ("parent#w0001", "parent#w0002")
    assert all(u.parent_sample_id == "parent" for u in roster.units)
    assert all(registry.lookup("parent", u.slice_record.media_relpath) == u.slice_record for u in roster.units)
    assert all(u.slice_record == old for u,old in zip(roster.units, world[2], strict=True))

@pytest.mark.parametrize("key,value", [
    ("sha256", "f"*64), ("split_identity_hash","f"*64),
    ("batch", "absent"), ("unit_count", 1), ("registry_run_id","foreign-run"),
])
def test_source_declaration_mismatch_refuses(tmp_path,key,value):
    world = _world(tmp_path)
    world[-1][key] = value
    with pytest.raises(PreparationError):
        _load(world)

def test_changed_slice_bytes_refuse(tmp_path):
    world = _world(tmp_path)
    (world[0]/world[2][1].media_relpath).write_bytes(b"changed")
    with pytest.raises(PreparationError, match="raw source refused"):
        _load(world)

def test_partial_parent_roster_refuses(tmp_path):
    world = _world(tmp_path)
    with pytest.raises(PreparationError, match="roster/order"):
        load_raw_execution_unit_roster(world[-1], data_root=world[0],
            samples=(world[1], SimpleNamespace(sample_id="extra",media_relpath="unused.wav",audio_seconds=1.0)),
            split_identity_hash="e"*64)

@pytest.mark.parametrize("change", ["reversed", "duplicate"])
def test_pinned_but_invalid_unit_order_refuses(tmp_path, change):
    from speech_aware_evidence_acquisition.core.preparation import digest
    world = _world(tmp_path)
    doc = json.loads(world[3].read_text())
    rows = doc["output"]["batches"][0]["requests"]
    rows[:] = list(reversed(rows)) if change == "reversed" else [rows[0],rows[0]]
    doc["output_sha256"] = digest(doc["output"])
    doc["inputs"]["window_sources_sha256"] = digest(doc["output"]["batches"])
    world[3].write_text(json.dumps(doc))
    world[-1]["sha256"] = hashlib.sha256(world[3].read_bytes()).hexdigest()
    with pytest.raises(PreparationError, match="duplicated, missing or out of order"):
        _load(world)
