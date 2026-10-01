"""Lossless bounded-memory proposer evidence, using synthetic sources only."""
import hashlib
import json
import tracemalloc
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import system_proposer_capsule as pc
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_proposer_capsule import fixture, reseal


def add_trace(packet, roots, text):
    path = roots["data"] / "trace.jsonl"
    path.write_text(text, encoding="utf-8", newline="")
    pin = {"path": str(path), "sha256": hashlib.sha256(text.encode()).hexdigest()}
    for member in packet["feedback"]["feedback"]["groups"][0]["members"]:
        member["execution"]["trace"] = pin
    reseal(packet)
    return path


def test_paged_and_memory_inputs_are_identical_and_all_boundaries_roundtrip(tmp_path):
    packet, roots = fixture(tmp_path, "L")
    text = ('Complete English evidence; preserve punctuation \u2014 and CRLF.\r\n' * 7000) + "Final record."
    source = add_trace(packet, roots, text)
    memory = pc.ProposerCapsule.from_packet(packet, roots=roots)
    paged = pc.ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")
    assert paged.as_json()["schema"] == "saea-proposer-capsule-v2"
    assert paged.initial_input() == memory.initial_input()
    assert paged.request() == memory.request()
    assert "storage" not in json.dumps(paged.initial_input())
    artifact = next(a for a in paged.as_json()["artifacts"] if a["kind"] == "feedback-trace")
    identity = artifact["artifact_id"]
    for offset in (0, 16370, pc.CACHE_CHARS - 5, pc.CACHE_CHARS + 2, len(text) - 4, len(text)):
        args = {"artifact_id": identity, "offset": offset, "limit": 16384}
        assert paged.read_artifact(args) == memory.read_artifact(args)
    source.write_text("Changed after packaging.")
    assert paged.read_artifact({"artifact_id": identity, "offset": 0, "limit": 100})["text"] == text[:100]
    assert all("text" not in a for a in paged.as_json()["artifacts"])


def test_trace_larger_than_memory_limits_streams_without_bulk_reads(tmp_path, monkeypatch):
    packet, roots = fixture(tmp_path, "L")
    path = roots["data"] / "trace.jsonl"
    block = 'Complete synthetic trace record.\n' * 8192
    digest = hashlib.sha256()
    with path.open("w") as stream:
        for _ in range(40):
            stream.write(block)
            digest.update(block.encode())
    pin = {"path": str(path), "sha256": digest.hexdigest()}
    for member in packet["feedback"]["feedback"]["groups"][0]["members"]:
        member["execution"]["trace"] = pin
    reseal(packet)
    monkeypatch.setattr(pc, "MAX_ARTIFACT_BYTES", 1024 * 1024)
    monkeypatch.setattr(pc, "MAX_CAPSULE_BYTES", 2 * 1024 * 1024)
    with pytest.raises(PolicyError, match="size"):
        pc.ProposerCapsule.from_packet(packet, roots=roots)
    original = Path.read_bytes
    def refuse_bulk(self):
        assert self != path, "large source must never be read as one byte string"
        return original(self)
    monkeypatch.setattr(Path, "read_bytes", refuse_bulk)
    tracemalloc.start()
    capsule = pc.ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < path.stat().st_size / 2
    trace = next(a for a in capsule.as_json()["artifacts"] if a["kind"] == "feedback-trace")
    assert trace["characters"] == len(block) * 40
    assert trace["sha256"] == digest.hexdigest()
    assert len([a for a in capsule.as_json()["artifacts"] if a["kind"] == "feedback-trace"]) == 1


@pytest.mark.parametrize("mutation", ["content", "symlink", "hardlink"])
def test_changed_or_linked_cached_chunk_is_never_supplied(tmp_path, mutation):
    packet, roots = fixture(tmp_path)
    capsule = pc.ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")
    artifact = capsule.as_json()["artifacts"][0]
    chunk = Path(artifact["storage"]["root"]) / artifact["storage"]["chunks"][0]["relpath"]
    if mutation == "content":
        chunk.write_text("Unregistered substitution.")
    else:
        other = tmp_path / "outside"
        chunk.rename(other)
        if mutation == "symlink":
            chunk.symlink_to(other)
        else:
            chunk.hardlink_to(other)
    with pytest.raises(PolicyError, match="hash|link"):
        capsule.read_artifact({"artifact_id": artifact["artifact_id"], "offset": 0, "limit": 100})
    assert capsule.access_log[-1]["status"] == "denied"


def test_invalid_source_does_not_publish_a_capsule_or_overwrite_cache(tmp_path):
    packet, roots = fixture(tmp_path)
    (roots["data"] / "snapshot.json").write_text("Changed before packaging.")
    with pytest.raises(PolicyError, match="hash"):
        pc.ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")
    with pytest.raises(FileExistsError):
        pc.ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")


def test_blind_broker_cannot_read_a_cached_learning_artifact(tmp_path):
    packet, roots = fixture(tmp_path)
    capsule = pc.ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")
    # Merely placing a file beside the cache never grants a model permission.
    (tmp_path / "cache" / "unregistered-feedback.txt").write_text("Forbidden outcome.")
    with pytest.raises(PolicyError, match="registered"):
        capsule.read_artifact({"artifact_id": "unregistered-feedback.txt", "offset": 0, "limit": 100})


def test_insufficient_space_refuses_before_any_artifact_copy(tmp_path, monkeypatch):
    from types import SimpleNamespace
    packet, roots = fixture(tmp_path)
    monkeypatch.setattr(pc.shutil, "disk_usage", lambda _: SimpleNamespace(free=1024))
    with pytest.raises(PolicyError, match="disk space"):
        pc.ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")
    assert list((tmp_path / "cache").iterdir()) == []


def test_streamed_utf8_error_is_preserved_as_invalid_material(tmp_path):
    packet, roots = fixture(tmp_path, "L")
    path = add_trace(packet, roots, "placeholder")
    raw = b"English first line.\n\xff"
    path.write_bytes(raw)
    for member in packet["feedback"]["feedback"]["groups"][0]["members"]:
        member["execution"]["trace"]["sha256"] = hashlib.sha256(raw).hexdigest()
    reseal(packet)
    with pytest.raises(PolicyError, match="UTF-8"):
        pc.ProposerCapsule.from_packet(packet, roots=roots, cache_root=tmp_path / "cache")
