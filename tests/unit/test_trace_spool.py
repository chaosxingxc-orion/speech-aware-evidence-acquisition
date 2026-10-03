"""Preserve exact trace bytes while keeping pending payloads on local disk."""

from concurrent.futures import ThreadPoolExecutor
import json

import pytest

from speech_aware_evidence_acquisition.core.tracing import TraceBuffer, TraceSink
from speech_aware_evidence_acquisition.core.trace_spool import (
    TraceSpool,
    TraceSpoolError,
)

RUN = "SAEA-E-000-spool"


def spool(tmp_path, **limits):
    return TraceSpool(
        tmp_path / "data",
        RUN,
        **{"max_record_bytes": 4096, "max_total_bytes": 100_000, **limits},
    )


def test_spooled_buffers_merge_by_reference_and_replay_exact_bytes(tmp_path):
    store = spool(tmp_path)
    first, second, combined = [TraceBuffer(RUN, spool=store) for _ in range(3)]
    payload = {"use_values": ["original"]}
    second.emit("USE", "b", {"use_text": "later"})
    first.emit("USE", "a", payload)
    payload["use_values"].append("changed")
    combined.extend_from(first)
    combined.extend_from(second)
    assert store.receipt()["written_records"] == 2
    assert store.receipt()["read_records"] == 0
    assert combined.resident_payload_bytes == 0
    assert list(first.iter_records()) == list(second.iter_records()) == []
    store.close()
    direct, restored = [TraceSink(tmp_path / n, RUN) for n in ("direct", "restored")]
    direct.emit("USE", "a", {"use_values": ["original"]})
    direct.emit("USE", "b", {"use_text": "later"})
    combined.flush_into(restored)
    combined.flush_into(restored)
    direct.close()
    restored.close()
    assert (tmp_path / "direct" / f"{RUN}.trace.jsonl").read_bytes() == (
        tmp_path / "restored" / f"{RUN}.trace.jsonl"
    ).read_bytes()
    assert store.path.exists()
    assert store.receipt()["read_records"] == 2
    assert store.receipt()["peak_read_record_bytes"] <= 4096
    with pytest.raises(TraceSpoolError, match="closed"):
        combined.emit("USE", "c", {"use_text": "cannot reopen"})


def test_independent_spools_never_alias_and_cross_store_merge_streams(tmp_path):
    a, b = spool(tmp_path), spool(tmp_path)
    assert a.path != b.path
    source, target = TraceBuffer(RUN, spool=a), TraceBuffer(RUN, spool=b)
    source.emit("USE", "a", {"use_text": "owned"})
    target.extend_from(source)
    assert a.receipt()["read_records"] == b.receipt()["written_records"] == 1
    assert target.records == [("USE", "a", {"use_text": "owned"})]
    with pytest.raises(ValueError):
        target.extend_from(target)
    with pytest.raises(ValueError):
        target.extend_from(TraceBuffer("another"))
    with pytest.raises(TraceSpoolError, match="owner"):
        TraceBuffer("another", spool=a)
    a.close()
    b.close()


def test_concurrent_writes_have_nonoverlapping_verified_records(tmp_path):
    store = spool(tmp_path)
    buffers = [TraceBuffer(RUN, spool=store) for _ in range(32)]

    def write(i):
        buffers[i].emit("USE", str(i), {"use_text": str(i) * 400})

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(len(buffers))))
    store.close()
    assert store.receipt()["written_records"] == 32
    assert store.receipt()["stored_bytes"] == store.path.stat().st_size
    for i, buffer in enumerate(buffers):
        assert buffer.records == [("USE", str(i), {"use_text": str(i) * 400})]


def test_caps_refuse_before_append_and_preserve_previous_bytes(tmp_path):
    store = spool(tmp_path, max_record_bytes=128, max_total_bytes=200)
    buffer = TraceBuffer(RUN, spool=store)
    buffer.emit("USE", "a", {"use_text": "x" * 15})
    original = store.path.read_bytes()
    with pytest.raises(TraceSpoolError, match="record.*bound"):
        buffer.emit("USE", "large", {"use_text": "x" * 1024})
    buffer.emit("USE", "b", {"use_text": "x" * 15})
    two = store.path.read_bytes()
    assert two.startswith(original)
    with pytest.raises(TraceSpoolError, match="total.*bound"):
        buffer.emit("USE", "c", {"use_text": "x" * 15})
    assert store.path.read_bytes() == two
    store.close()


@pytest.mark.parametrize("tamper", ["change", "truncate", "missing"])
def test_corrupt_or_missing_intermediates_fail_without_regeneration(tmp_path, tamper):
    store = spool(tmp_path)
    buffer = TraceBuffer(RUN, spool=store)
    buffer.emit("USE", "a", {"use_text": "evidence"})
    store.close()
    original = store.path.read_bytes()
    if tamper == "missing":
        store.path.unlink()
    else:
        store.path.write_bytes(
            original[:-4]
            if tamper == "truncate"
            else original.replace(b"evidence", b"modified")
        )
    with pytest.raises(TraceSpoolError, match="unavailable|integrity"):
        list(buffer.iter_records())


def test_payload_contract_is_checked_before_spool_mutation(tmp_path):
    store = spool(tmp_path)
    buffer = TraceBuffer(RUN, spool=store)
    with pytest.raises(ValueError):
        buffer.emit("USE", "bad", {"obs_wrong_axis": "no"})
    assert store.receipt()["written_records"] == 0
    store.close()


@pytest.mark.parametrize(
    "limits",
    [
        {"max_record_bytes": True},
        {"max_record_bytes": 0},
        {"max_total_bytes": -1},
        {"max_total_bytes": 100},
    ],
)
def test_invalid_bounds_do_not_create_files(tmp_path, limits):
    with pytest.raises(TraceSpoolError):
        spool(tmp_path, **limits)
    assert not (tmp_path / "data").exists()


def test_spool_refuses_repository_root_and_bad_identity(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.trace_spool as module

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path / "repo")
    with pytest.raises(TraceSpoolError, match="repository"):
        spool(tmp_path / "repo")
    with pytest.raises(TraceSpoolError, match="identity"):
        TraceSpool(tmp_path, "../../escape", max_record_bytes=1, max_total_bytes=2)


def test_record_iteration_does_not_materialize_whole_spool(tmp_path):
    store = spool(tmp_path, max_total_bytes=2_000_000)
    buffer = TraceBuffer(RUN, spool=store)
    for i in range(300):
        buffer.emit("USE", str(i), {"use_text": "x" * 3000})
    store.close()
    iterator = buffer.iter_records()
    assert next(iterator)[1] == "0"
    assert store.receipt()["read_records"] == 1
    assert buffer.resident_payload_bytes == 0
    assert store.receipt()["stored_bytes"] > 900_000
    iterator.close()
    manifest = json.loads(store.path.with_suffix(".json").read_text())
    assert manifest["run_id"] == RUN
    assert manifest["written_records"] == 300
    assert manifest["retained_payload_bytes"] == 0


def test_pipeline_storage_configuration_is_explicit_and_round_trips():
    from speech_aware_evidence_acquisition.rails.dispatch_slot_fill import (
        parse_native_node_pipeline,
        NativeNodePipelineError,
    )

    base = {
        "schema": "saea-native-node-pipeline-v1",
        "node_order": ["solver"],
        "group_size": 20,
        "prepare_workers": 2,
        "max_jobs": 160,
    }
    assert parse_native_node_pipeline({"native_node_pipeline": base}).as_json() == base
    storage = {
        "schema": "saea-native-trace-spool-v1",
        "max_record_bytes": 4096,
        "max_total_bytes": 1_000_000,
    }
    declared = {**base, "trace_spool": storage}
    parsed = parse_native_node_pipeline({"native_node_pipeline": declared})
    assert parsed.as_json() == declared
    for bad in (
        None,
        {},
        {**storage, "extra": 1},
        {**storage, "max_record_bytes": True},
        {**storage, "schema": "wrong"},
        {**storage, "max_total_bytes": 1},
    ):
        with pytest.raises(NativeNodePipelineError):
            parse_native_node_pipeline(
                {"native_node_pipeline": {**base, "trace_spool": bad}}
            )


def test_write_failure_closes_admission_and_keeps_evidence(tmp_path):
    store = spool(tmp_path)
    original_handle = store._handle

    class FailingWriter:
        def write(self, raw):
            raise OSError("synthetic disk full")

        def close(self):
            original_handle.close()

    store._handle = FailingWriter()
    buffer = TraceBuffer(RUN, spool=store)
    with pytest.raises(TraceSpoolError, match="write failed"):
        buffer.emit("USE", "a", {"use_text": "retained"})
    with pytest.raises(TraceSpoolError, match="failed"):
        buffer.emit("USE", "b", {"use_text": "no retry"})
    store.close()
    store.close()
    assert store.receipt()["failed"]
    assert store.path.exists()


def test_default_buffer_still_reports_its_retained_payload_and_migrates(tmp_path):
    original = TraceBuffer(RUN)
    original.emit("USE", "a", {"use_text": "kept"})
    assert original.resident_payload_bytes > 0
    store = spool(tmp_path)
    disk = TraceBuffer(RUN, spool=store)
    disk.extend_from(original)
    assert original.records == []
    restored = TraceBuffer(RUN)
    restored.extend_from(disk)
    assert restored.records == [("USE", "a", {"use_text": "kept"})]
    store.close()


def test_process_memory_reports_missing_as_unknown_and_keeps_scope(tmp_path):
    from speech_aware_evidence_acquisition.core.trace_spool import (
        process_memory_snapshot,
    )

    path = tmp_path / "status"
    missing = process_memory_snapshot(path)
    assert missing["rss_bytes"] is None and missing["peak_rss_bytes"] is None
    path.write_text("VmRSS: 123 kB\nVmHWM: 456 kB\n")
    got = process_memory_snapshot(path)
    assert got["rss_bytes"] == 123 * 1024
    assert got["peak_rss_bytes"] == 456 * 1024
    assert got["scope"] == "whole current process; not per sample or owner"
    path.write_text("VmRSS: invalid kB\nVmHWM: 12 other\n")
    assert process_memory_snapshot(path)["rss_bytes"] is None
    assert process_memory_snapshot(path)["peak_rss_bytes"] is None
