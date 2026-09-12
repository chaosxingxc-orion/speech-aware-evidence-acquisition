"""Shared preparation artifacts and exact fit are tested without endpoints."""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.preparation import (
    PreparationError,
    artifact_inputs,
    canonical_bytes,
    load_artifact,
    measure_request,
    prepare_artifact,
)


def _inputs():
    return artifact_inputs(
        config={"policy": "one", "prompt_fit_receipt": "later"},
        split_identity_hash="a" * 64,
        sources={"vectors": "b" * 64},
    )


def test_warm_artifact_skips_producer_and_pins_file(tmp_path):
    path = tmp_path / "seed.json"
    calls = []
    first = prepare_artifact(
        path,
        kind="phase-supply",
        inputs=_inputs(),
        producer=lambda: calls.append(1) or {"values": {"s": ["v"]}},
    )
    second = prepare_artifact(
        path,
        kind="phase-supply",
        inputs=_inputs(),
        producer=lambda: pytest.fail("warm preparation recomputed"),
    )
    assert calls == [1]
    assert (
        first["sha256"]
        == second["sha256"]
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )
    assert second["cache"] == "warm"
    assert load_artifact(
        path, expected_sha256=second["sha256"], kind="phase-supply", inputs=_inputs()
    ) == {"values": {"s": ["v"]}}


@pytest.mark.parametrize("change", ["inputs", "sha", "payload", "kind"])
def test_stale_or_corrupt_artifact_refused(tmp_path, change):
    path = tmp_path / "seed.json"
    receipt = prepare_artifact(
        path, kind="phase-supply", inputs=_inputs(), producer=lambda: {"a": 1}
    )
    inputs, digest, kind = _inputs(), receipt["sha256"], "phase-supply"
    if change == "inputs":
        inputs = {**inputs, "split_identity_hash": "c" * 64}
    if change == "sha":
        digest = "0" * 64
    if change == "kind":
        kind = "packets"
    if change == "payload":
        obj = json.loads(path.read_text())
        obj["output"]["a"] = 2
        path.write_text(json.dumps(obj))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(PreparationError):
        load_artifact(path, expected_sha256=digest, kind=kind, inputs=inputs)


def test_existing_wrong_key_not_overwritten(tmp_path):
    path = tmp_path / "seed.json"
    prepare_artifact(
        path, kind="phase-supply", inputs=_inputs(), producer=lambda: {"a": 1}
    )
    original = path.read_bytes()
    with pytest.raises(PreparationError):
        prepare_artifact(
            path,
            kind="phase-supply",
            inputs={"changed": True},
            producer=lambda: pytest.fail("should refuse first"),
        )
    assert path.read_bytes() == original


def test_binding_excludes_only_receipt_pins():
    a = artifact_inputs(config={"k": 5}, split_identity_hash="a" * 64, sources={})
    b = artifact_inputs(
        config={
            "k": 5,
            "prepared_phase_supply": {"sha256": "x"},
            "prompt_fit_receipt": "x",
            "prompt_fit_receipt_sha256": "y",
        },
        split_identity_hash="a" * 64,
        sources={},
    )
    assert a == b
    assert a != artifact_inputs(
        config={"k": 6}, split_identity_hash="a" * 64, sources={}
    )


@pytest.mark.parametrize("split", ["", "test", "a" * 63])
def test_bad_split_hash_refused(split):
    with pytest.raises(PreparationError):
        artifact_inputs(config={}, split_identity_hash=split, sources={})


class Tokenizer:
    def __init__(self, prompt="A<media>B<media>C"):
        self.prompt, self.calls = prompt, []

    def request_json(self, method, path, payload):
        self.calls.append((method, path, payload))
        if path == "/apply-template":
            return {"prompt": self.prompt}
        if path == "/tokenize":
            return {"tokens": list(payload["content"])}
        pytest.fail("generation or undeclared endpoint")


def test_actual_envelope_count_multiple_media_and_reserve():
    client = Tokenizer()
    body = {
        "messages": [{"role": "system", "content": "instruction"}],
        "max_tokens": 64,
    }
    row = measure_request(
        client, body, media_marker="<media>", speech_tokens=(13, 26), slot_tokens=128
    )
    assert row["text_tokens"] == 3
    assert row["speech_tokens"] == 39
    assert row["required_tokens"] == 108  # 3 + 39 + 64 + 2
    assert row["margin_tokens"] == 20
    assert row["fits"] is True
    assert client.calls[0][2] == {"messages": body["messages"]}
    assert len(client.calls) == 4


def test_exact_boundary_and_study_multiple():
    body = {"messages": [], "max_tokens": 4}
    assert measure_request(
        Tokenizer("A"), body, media_marker="<media>", speech_tokens=(), slot_tokens=7
    )["fits"]
    row = measure_request(
        Tokenizer("A"),
        body,
        media_marker="<media>",
        speech_tokens=(),
        slot_tokens=13,
        fit_multiple=2,
    )
    assert not row["fits"]
    assert row["margin_tokens"] == -1


@pytest.mark.parametrize("speech", [(), (1,), (1, 2, 3)])
def test_marker_count_must_match_actual_packets(speech):
    with pytest.raises(PreparationError):
        measure_request(
            Tokenizer(),
            {"messages": [], "max_tokens": 4},
            media_marker="<media>",
            speech_tokens=speech,
            slot_tokens=128,
        )


def test_fit_forwards_tools_and_refuses_empty_marker():
    client = Tokenizer("A")
    body = {"messages": [], "tools": [{"type": "function"}], "max_tokens": 1}
    measure_request(client, body, media_marker="<m>", speech_tokens=(), slot_tokens=8)
    assert client.calls[0][2]["tools"] == body["tools"]
    with pytest.raises(PreparationError):
        measure_request(client, body, media_marker="", speech_tokens=(), slot_tokens=8)


def test_warm_contact_class_cannot_be_relabeled(tmp_path):
    path = tmp_path / "prepared.json"
    prepare_artifact(
        path,
        kind="test",
        inputs=_inputs(),
        producer=lambda: {},
        contact_class="encoder",
    )
    with pytest.raises(PreparationError, match="contact class"):
        prepare_artifact(
            path,
            kind="test",
            inputs=_inputs(),
            producer=lambda: {},
            contact_class="model-free",
        )


@pytest.mark.parametrize("response", [None, [], {"prompt": None}])
def test_malformed_template_response_is_refused(response):
    client = type("BadClient", (), {"request_json": lambda *args: response})()
    with pytest.raises(PreparationError, match="prompt"):
        measure_request(
            client,
            {"messages": [], "max_tokens": 1},
            media_marker="<m>",
            speech_tokens=(),
            slot_tokens=20,
        )


def test_source_receipts_require_full_confined_file_digest(tmp_path):
    from speech_aware_evidence_acquisition.core.preparation import (
        verify_source_receipts,
    )

    raw = b"complete frozen receipt"
    (tmp_path / "source.json").write_bytes(raw)
    pins = [
        {
            "root": "repository",
            "relpath": "source.json",
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    ]
    assert verify_source_receipts(pins, repo_root=tmp_path, data_root=tmp_path) == pins
    for bad in (
        [],
        [{**pins[0], "sha256": "0" * 64}],
        [{**pins[0], "relpath": "../source.json"}],
        [{**pins[0], "root": "unknown"}],
    ):
        with pytest.raises(PreparationError):
            verify_source_receipts(bad, repo_root=tmp_path, data_root=tmp_path)


def test_concurrent_cold_preparation_runs_one_producer(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    entered, release, calls = Event(), Event(), []
    path = tmp_path / "shared.json"

    def produce():
        calls.append(1)
        entered.set()
        assert release.wait(5)
        return {"done": True}

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            prepare_artifact, path, kind="test", inputs=_inputs(), producer=produce
        )
        assert entered.wait(5)
        try:
            with pytest.raises(PreparationError, match="busy"):
                prepare_artifact(
                    path,
                    kind="test",
                    inputs=_inputs(),
                    producer=lambda: calls.append(2),
                )
        finally:
            release.set()
        first.result(timeout=5)
    assert calls == [1]
    assert (
        prepare_artifact(
            path,
            kind="test",
            inputs=_inputs(),
            producer=lambda: pytest.fail("warm producer"),
        )["cache"]
        == "warm"
    )


def test_interrupted_encoder_is_never_automatically_repeated(tmp_path):
    path = tmp_path / "encoder.json"

    def fail():
        raise RuntimeError("encoder interrupted")

    with pytest.raises(RuntimeError, match="interrupted"):
        prepare_artifact(
            path,
            kind="packets",
            inputs=_inputs(),
            producer=fail,
            contact_class="encoder",
        )
    with pytest.raises(PreparationError, match="prior encoder"):
        prepare_artifact(
            path,
            kind="packets",
            inputs=_inputs(),
            producer=lambda: pytest.fail("encoder repeated"),
            contact_class="encoder",
        )


def test_warm_speech_tool_artifact_has_zero_additional_contacts(tmp_path):
    path = tmp_path / "speech-tool.json"
    calls = []
    first = prepare_artifact(
        path,
        kind="auxiliary-asr",
        inputs=_inputs(),
        producer=lambda: calls.append("contact") or {"text_sha256": "c" * 64},
        contact_class="speech-tool",
    )

    second = prepare_artifact(
        path,
        kind="auxiliary-asr",
        inputs=_inputs(),
        producer=lambda: pytest.fail("warm speech tool repeated a contact"),
        contact_class="speech-tool",
    )

    assert calls == ["contact"]
    assert first["cache"] == "cold"
    assert second == {**first, "cache": "warm"}


def test_interrupted_speech_tool_is_never_automatically_repeated(tmp_path):
    path = tmp_path / "speech-tool.json"
    inputs = _inputs()

    with pytest.raises(RuntimeError, match="speech tool interrupted"):
        prepare_artifact(
            path,
            kind="auxiliary-asr",
            inputs=inputs,
            producer=lambda: (_ for _ in ()).throw(
                RuntimeError("speech tool interrupted")
            ),
            contact_class="speech-tool",
        )
    assert (tmp_path / "speech-tool.json.speech-tool-started.json").read_bytes() == (
        canonical_bytes(
            {
                "schema": "saea-speech-tool-preparation-start-v1",
                "kind": "auxiliary-asr",
                "inputs": inputs,
                "contact_class": "speech-tool",
            }
        )
    )

    with pytest.raises(PreparationError, match="prior speech-tool preparation"):
        prepare_artifact(
            path,
            kind="auxiliary-asr",
            inputs=_inputs(),
            producer=lambda: pytest.fail("speech tool contact repeated"),
            contact_class="speech-tool",
        )


@pytest.mark.parametrize(
    ("changed_inputs", "contact_class", "message"),
    [
        ({**_inputs(), "sources": {"vectors": "d" * 64}}, "speech-tool", "identity"),
        ({**_inputs(), "config_sha256": "e" * 64}, "speech-tool", "identity"),
        (_inputs(), "encoder", "contact class"),
        (_inputs(), "model-free", "contact class"),
    ],
)
def test_speech_tool_start_marker_refuses_changed_binding_or_class(
    tmp_path, changed_inputs, contact_class, message
):
    path = tmp_path / "speech-tool.json"

    with pytest.raises(RuntimeError, match="speech tool interrupted"):
        prepare_artifact(
            path,
            kind="auxiliary-asr",
            inputs=_inputs(),
            producer=lambda: (_ for _ in ()).throw(
                RuntimeError("speech tool interrupted")
            ),
            contact_class="speech-tool",
        )

    with pytest.raises(PreparationError, match=message):
        prepare_artifact(
            path,
            kind="auxiliary-asr",
            inputs=changed_inputs,
            producer=lambda: pytest.fail("changed binding reached producer"),
            contact_class=contact_class,
        )


def test_warm_speech_tool_refuses_changed_sources_before_producer(tmp_path):
    path = tmp_path / "speech-tool.json"
    prepare_artifact(
        path,
        kind="auxiliary-asr",
        inputs=_inputs(),
        producer=lambda: {"text_sha256": "c" * 64},
        contact_class="speech-tool",
    )

    with pytest.raises(PreparationError, match="identity"):
        prepare_artifact(
            path,
            kind="auxiliary-asr",
            inputs={**_inputs(), "sources": {"vectors": "d" * 64}},
            producer=lambda: pytest.fail("wrong source reached producer"),
            contact_class="speech-tool",
        )


def test_concurrent_speech_tool_preparation_runs_one_producer(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    entered, release, calls = Event(), Event(), []
    path = tmp_path / "speech-tool.json"

    def produce():
        calls.append("contact")
        entered.set()
        assert release.wait(5)
        return {"text_sha256": "c" * 64}

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            prepare_artifact,
            path,
            kind="auxiliary-asr",
            inputs=_inputs(),
            producer=produce,
            contact_class="speech-tool",
        )
        assert entered.wait(5)
        try:
            with pytest.raises(PreparationError, match="busy"):
                prepare_artifact(
                    path,
                    kind="auxiliary-asr",
                    inputs=_inputs(),
                    producer=lambda: calls.append("second contact"),
                    contact_class="speech-tool",
                )
        finally:
            release.set()
        assert first.result(timeout=5)["cache"] == "cold"

    assert calls == ["contact"]


def test_encoder_start_marker_keeps_historical_name_and_bytes(tmp_path):
    path = tmp_path / "encoder.json"
    inputs = _inputs()
    prepare_artifact(
        path,
        kind="packets",
        inputs=inputs,
        producer=lambda: {"vectors": []},
        contact_class="encoder",
    )

    marker = tmp_path / "encoder.json.encoder-started.json"
    assert marker.read_bytes() == canonical_bytes({"kind": "packets", "inputs": inputs})
    assert not (tmp_path / "encoder.json.speech-tool-started.json").exists()
    assert path.read_bytes() == canonical_bytes(
        {
            "schema": "saea-prepared-artifact-v1",
            "kind": "packets",
            "inputs": inputs,
            "contact_class": "encoder",
            "output": {"vectors": []},
            "output_sha256": hashlib.sha256(canonical_bytes({"vectors": []})).hexdigest(),
        }
    )


def test_speech_tool_cannot_relabel_an_interrupted_encoder(tmp_path):
    path = tmp_path / "encoder.json"
    with pytest.raises(RuntimeError, match="encoder interrupted"):
        prepare_artifact(
            path,
            kind="packets",
            inputs=_inputs(),
            producer=lambda: (_ for _ in ()).throw(RuntimeError("encoder interrupted")),
            contact_class="encoder",
        )

    with pytest.raises(PreparationError, match="contact class"):
        prepare_artifact(
            path,
            kind="auxiliary-asr",
            inputs=_inputs(),
            producer=lambda: pytest.fail("encoder state was relabeled"),
            contact_class="speech-tool",
        )


def test_multimodal_count_measures_actual_body_and_keeps_margin_separate():
    from speech_aware_evidence_acquisition.core.preparation import (
        measure_multimodal_request,
    )

    calls = []

    class Client:
        def request_json(self, method, path, payload):
            calls.append((method, path, payload))
            return {"input_tokens": 17}

    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": "actual bytes", "format": "wav"},
                    }
                ],
            }
        ],
        "max_tokens": 3,
    }
    result = measure_multimodal_request(Client(), body, slot_tokens=43, fit_multiple=2)
    assert calls == [("POST", "/v1/chat/completions/input_tokens", body)]
    assert result["measured_prompt_tokens"] == 17
    assert result["required_tokens"] == 22
    assert result["margin_tokens"] == -1
    assert not result["fits"]


@pytest.mark.parametrize(
    "response", [None, {}, {"input_tokens": True}, {"input_tokens": -1}]
)
def test_multimodal_count_has_no_estimate_fallback(response):
    from speech_aware_evidence_acquisition.core.preparation import (
        measure_multimodal_request,
    )

    class Client:
        def request_json(self, *args):
            return response

    with pytest.raises(PreparationError, match="multimodal"):
        measure_multimodal_request(
            Client(), {"messages": [], "max_tokens": 3}, slot_tokens=99
        )


def test_operational_campaign_readiness_is_not_a_circular_input():
    first = {
        "k": 5,
        "cells": [
            {
                "cell_id": "a",
                "baseline_fragment": "model-input",
                "readiness": {"status": "held", "requirements": []},
            }
        ],
    }
    second = {
        "k": 5,
        "cells": [
            {
                "cell_id": "a",
                "baseline_fragment": "model-input",
                "readiness": {
                    "status": "ready",
                    "requirements": [{"path": "this-fit.json", "sha256": "a" * 64}],
                },
            }
        ],
    }

    def identity(config):
        return artifact_inputs(config=config, split_identity_hash="a" * 64, sources={})

    assert identity(first) == identity(second)
    assert first["cells"][0]["readiness"]["status"] == "held"
    second["cells"][0]["baseline_fragment"] = "changed-model-input"
    assert identity(first) != identity(second)
