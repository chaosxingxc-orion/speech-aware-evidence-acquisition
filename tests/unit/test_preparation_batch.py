"""Batch preparation preserves one-shot contacts and immutable artifacts."""

from __future__ import annotations

import fcntl
import hashlib
import os

import pytest

from speech_aware_evidence_acquisition.core import preparation
from speech_aware_evidence_acquisition.core.preparation import (
    PreparationError,
    load_artifact,
    prepare_artifact,
    prepare_artifact_batch,
)


def _inputs(name: str) -> dict[str, object]:
    return {"sample_id": name, "source_sha256": name[0] * 64}


def _item(path, name):
    return {"path": path, "inputs": _inputs(name)}


def test_batch_calls_once_for_missing_unique_items_and_restores_original_order(tmp_path):
    first, second = tmp_path / "z.json", tmp_path / "a.json"
    seen = []
    receipts = prepare_artifact_batch(
        [_item(first, "zulu"), _item(second, "alpha"), _item(first, "zulu")],
        kind="prepared-speech-observation-v1",
        producer=lambda indices: seen.append(indices)
        or [{"transcript": "z"}, {"transcript": "a"}],
    )
    assert seen == [[0, 1]]
    assert [row["cache"] for row in receipts] == ["cold", "cold", "cold"]
    assert receipts[0] == receipts[2]
    assert load_artifact(
        first, expected_sha256=receipts[0]["sha256"],
        kind="prepared-speech-observation-v1", inputs=_inputs("zulu")
    ) == {"transcript": "z"}


def test_batch_only_sends_cold_original_indices_and_all_warm_skips_producer(tmp_path):
    warm, cold = tmp_path / "warm.json", tmp_path / "cold.json"
    prepare_artifact(
        warm, kind="prepared-speech-observation-v1", inputs=_inputs("warm"),
        producer=lambda: {"transcript": "already"}, contact_class="speech-tool",
    )
    calls = []
    mixed = prepare_artifact_batch(
        [_item(warm, "warm"), _item(cold, "cold")],
        kind="prepared-speech-observation-v1",
        producer=lambda indices: calls.append(indices) or [{"transcript": "new"}],
    )
    all_warm = prepare_artifact_batch(
        [_item(cold, "cold"), _item(warm, "warm")],
        kind="prepared-speech-observation-v1",
        producer=lambda _indices: pytest.fail("all-warm batch invoked producer"),
    )
    assert calls == [[1]]
    assert [row["cache"] for row in mixed] == ["warm", "cold"]
    assert [row["cache"] for row in all_warm] == ["warm", "warm"]


def test_batch_rejects_duplicate_resolved_path_with_different_inputs(tmp_path):
    path = tmp_path / "same.json"
    alias = tmp_path / "child" / ".." / "same.json"
    with pytest.raises(PreparationError, match="duplicate.*different inputs"):
        prepare_artifact_batch(
            [_item(path, "alpha"), _item(alias, "beta")],
            kind="prepared-speech-observation-v1",
            producer=lambda _indices: pytest.fail("invalid batch reached producer"),
        )
    assert not path.with_name(path.name + ".speech-tool-started.json").exists()


def test_batch_persists_every_marker_before_producer_and_never_replays(tmp_path):
    paths = [tmp_path / "one.json", tmp_path / "two.json"]

    def fail(indices):
        assert indices == [0, 1]
        for path in paths:
            assert path.with_name(path.name + ".speech-tool-started.json").exists()
        raise RuntimeError("batch interrupted")

    with pytest.raises(RuntimeError, match="batch interrupted"):
        prepare_artifact_batch(
            [_item(paths[0], "one"), _item(paths[1], "two")],
            kind="prepared-speech-observation-v1", producer=fail,
        )
    with pytest.raises(PreparationError, match="prior speech-tool"):
        prepare_artifact_batch(
            [_item(paths[0], "one"), _item(paths[1], "two")],
            kind="prepared-speech-observation-v1",
            producer=lambda _indices: pytest.fail("interrupted batch replayed"),
        )


@pytest.mark.parametrize(
    "outputs, message",
    [([{"transcript": "only one"}], "output count"),
     ([{"bad": float("nan")}, {}], "serializable")],
)
def test_batch_validates_all_outputs_before_writing(tmp_path, outputs, message):
    paths = [tmp_path / "one.json", tmp_path / "two.json"]
    with pytest.raises(PreparationError, match=message):
        prepare_artifact_batch(
            [_item(paths[0], "one"), _item(paths[1], "two")],
            kind="prepared-speech-observation-v1",
            producer=lambda _indices: outputs,
        )
    assert not any(path.exists() for path in paths)
    assert all(path.with_name(path.name + ".speech-tool-started.json").exists()
               for path in paths)


def test_batch_refuses_warm_binding_or_contact_class_changes(tmp_path):
    path = tmp_path / "warm.json"
    prepare_artifact(
        path, kind="prepared-speech-observation-v1", inputs=_inputs("warm"),
        producer=lambda: {"transcript": "ready"}, contact_class="speech-tool",
    )
    with pytest.raises(PreparationError, match="identity"):
        prepare_artifact_batch(
            [_item(path, "wrong")], kind="prepared-speech-observation-v1",
            producer=lambda _indices: pytest.fail("changed binding reached producer"),
        )
    with pytest.raises(PreparationError, match="contact class"):
        prepare_artifact_batch(
            [_item(path, "warm")], kind="prepared-speech-observation-v1",
            contact_class="model-free",
            producer=lambda _indices: pytest.fail("mixed class reached producer"),
        )


def test_batch_refuses_competing_lock_without_calling_producer(tmp_path):
    path = tmp_path / "busy.json"
    lock_path = path.with_name(path.name + ".producer.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(PreparationError, match="busy"):
            prepare_artifact_batch(
                [_item(path, "busy")], kind="prepared-speech-observation-v1",
                producer=lambda _indices: pytest.fail("busy batch reached producer"),
            )
    finally:
        os.close(descriptor)


def test_batch_preserves_outputs_published_before_write_failure(tmp_path, monkeypatch):
    paths = [tmp_path / "one.json", tmp_path / "two.json"]
    real_link, links = preparation.os.link, []

    def fail_second_link(source, destination):
        links.append(destination)
        if len(links) == 2:
            raise OSError("simulated storage failure")
        return real_link(source, destination)

    monkeypatch.setattr(preparation.os, "link", fail_second_link)
    with pytest.raises(OSError, match="storage failure"):
        prepare_artifact_batch(
            [_item(paths[0], "one"), _item(paths[1], "two")],
            kind="prepared-speech-observation-v1",
            producer=lambda _indices: [{"transcript": "one"}, {"transcript": "two"}],
        )
    assert paths[0].exists()
    assert not paths[1].exists()
    assert all(path.with_name(path.name + ".speech-tool-started.json").exists()
               for path in paths)


def test_empty_batch_does_not_invoke_producer():
    assert prepare_artifact_batch(
        [], kind="prepared-speech-observation-v1",
        producer=lambda _indices: pytest.fail("empty batch invoked producer"),
    ) == []


def test_batch_preflights_all_interruption_markers_before_creating_new_ones(tmp_path):
    clean, interrupted = tmp_path / "clean.json", tmp_path / "interrupted.json"
    with pytest.raises(RuntimeError, match="interrupted"):
        prepare_artifact(
            interrupted,
            kind="prepared-speech-observation-v1",
            inputs=_inputs("interrupted"),
            contact_class="speech-tool",
            producer=lambda: (_ for _ in ()).throw(RuntimeError("interrupted")),
        )

    with pytest.raises(PreparationError, match="prior speech-tool"):
        prepare_artifact_batch(
            [_item(clean, "clean"), _item(interrupted, "interrupted")],
            kind="prepared-speech-observation-v1",
            producer=lambda _indices: pytest.fail("invalid batch reached producer"),
        )

    assert not clean.with_name(clean.name + ".speech-tool-started.json").exists()


def test_single_artifact_serialization_stays_canonical_and_byte_stable(tmp_path):
    path = tmp_path / "single.json"
    inputs, output = _inputs("single"), {"transcript": "stable"}
    receipt = prepare_artifact(
        path,
        kind="prepared-speech-observation-v1",
        inputs=inputs,
        producer=lambda: output,
        contact_class="speech-tool",
    )
    expected = preparation.canonical_bytes(
        {
            "schema": preparation.SCHEMA,
            "kind": "prepared-speech-observation-v1",
            "inputs": inputs,
            "contact_class": "speech-tool",
            "output": output,
            "output_sha256": preparation.digest(output),
        }
    )
    assert path.read_bytes() == expected
    assert receipt["sha256"] == hashlib.sha256(expected).hexdigest()
