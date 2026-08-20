"""``rails.local_encoder_client``: the in-process GLAP/CLSP encode-only
client (P-EMB-3M arms M2/M3). Engineering-only, ZERO live model contact --
every test drives synthetic ``encode_text_fn``/``encode_audio_fn`` callables
or :class:`MockLocalEncoderClient`, never real ``transformers``/``torch``.
"""

from __future__ import annotations

import math

import pytest

from speech_aware_evidence_acquisition.rails.local_encoder_client import (
    CLSP_EMBEDDING_DIM,
    GLAP_EMBEDDING_DIM,
    STATUS_DROPPED_DEPS,
    STATUS_OK,
    LocalEncoderClientError,
    LocalTransformersEncoderClient,
    MockLocalEncoderClient,
    run_import_feasibility_gate,
)


def _unit_vector(dim: int, seed: float = 1.0) -> list[float]:
    values = [0.0] * dim
    values[0] = seed
    return values


# ---------------------------------------------------------------------------
# LocalTransformersEncoderClient -- construction.
# ---------------------------------------------------------------------------


def test_construction_refuses_empty_model_id():
    with pytest.raises(LocalEncoderClientError, match="model_id"):
        LocalTransformersEncoderClient(
            model_id="",
            expected_dim=GLAP_EMBEDDING_DIM,
            encode_text_fn=lambda text: _unit_vector(GLAP_EMBEDDING_DIM),
            encode_audio_fn=lambda audio: _unit_vector(GLAP_EMBEDDING_DIM),
        )


def test_construction_refuses_non_positive_expected_dim():
    with pytest.raises(LocalEncoderClientError, match="expected_dim"):
        LocalTransformersEncoderClient(
            model_id="glap",
            expected_dim=0,
            encode_text_fn=lambda text: [],
            encode_audio_fn=lambda audio: [],
        )


def test_model_id_and_expected_dim_are_exposed():
    client = LocalTransformersEncoderClient(
        model_id="glap",
        expected_dim=GLAP_EMBEDDING_DIM,
        encode_text_fn=lambda text: _unit_vector(GLAP_EMBEDDING_DIM),
        encode_audio_fn=lambda audio: _unit_vector(GLAP_EMBEDDING_DIM),
    )
    assert client.model_id == "glap"
    assert client.expected_dim == GLAP_EMBEDDING_DIM


# ---------------------------------------------------------------------------
# embed_text / embed_audio -- happy path + contact recording.
# ---------------------------------------------------------------------------


def test_embed_text_happy_path_records_a_contact():
    client = LocalTransformersEncoderClient(
        model_id="glap",
        expected_dim=GLAP_EMBEDDING_DIM,
        encode_text_fn=lambda text: _unit_vector(GLAP_EMBEDDING_DIM),
        encode_audio_fn=lambda audio: _unit_vector(GLAP_EMBEDDING_DIM),
        now=iter([0.0, 0.5]).__next__,
    )
    vector = client.embed_text(contact_id="label-1", text="iot")
    assert vector.contact_id == "label-1"
    assert vector.kind == "text"
    assert vector.dims == GLAP_EMBEDDING_DIM
    assert len(client.contacts) == 1
    assert client.contacts[0].kind == "text"
    assert client.contacts[0].latency_seconds == pytest.approx(0.5)


def test_embed_audio_happy_path_records_a_contact():
    client = LocalTransformersEncoderClient(
        model_id="clsp",
        expected_dim=CLSP_EMBEDDING_DIM,
        encode_text_fn=lambda text: _unit_vector(CLSP_EMBEDDING_DIM),
        encode_audio_fn=lambda audio: _unit_vector(CLSP_EMBEDDING_DIM),
    )
    vector = client.embed_audio(contact_id="s1", audio_bytes=b"AUDIO")
    assert vector.kind == "audio"
    assert vector.dims == CLSP_EMBEDDING_DIM
    assert len(client.contacts) == 1


def test_encode_text_fn_receives_the_exact_text():
    seen = []

    def encode_text(text):
        seen.append(text)
        return _unit_vector(GLAP_EMBEDDING_DIM)

    client = LocalTransformersEncoderClient(
        model_id="glap", expected_dim=GLAP_EMBEDDING_DIM, encode_text_fn=encode_text, encode_audio_fn=lambda a: []
    )
    client.embed_text(contact_id="s1", text="hello world")
    assert seen == ["hello world"]


def test_encode_audio_fn_receives_bytes_not_bytearray():
    seen = []

    def encode_audio(data):
        seen.append(type(data))
        return _unit_vector(GLAP_EMBEDDING_DIM)

    client = LocalTransformersEncoderClient(
        model_id="glap", expected_dim=GLAP_EMBEDDING_DIM, encode_text_fn=lambda t: [], encode_audio_fn=encode_audio
    )
    client.embed_audio(contact_id="s1", audio_bytes=bytearray(b"AUDIO"))
    assert seen == [bytes]


# ---------------------------------------------------------------------------
# Fail-closed legality checks.
# ---------------------------------------------------------------------------


def test_embed_text_refuses_empty_text():
    client = LocalTransformersEncoderClient(
        model_id="glap", expected_dim=GLAP_EMBEDDING_DIM, encode_text_fn=lambda t: [], encode_audio_fn=lambda a: []
    )
    with pytest.raises(LocalEncoderClientError, match="non-empty string"):
        client.embed_text(contact_id="s1", text="")


def test_embed_audio_refuses_empty_bytes():
    client = LocalTransformersEncoderClient(
        model_id="glap", expected_dim=GLAP_EMBEDDING_DIM, encode_text_fn=lambda t: [], encode_audio_fn=lambda a: []
    )
    with pytest.raises(LocalEncoderClientError, match="non-empty bytes"):
        client.embed_audio(contact_id="s1", audio_bytes=b"")


def test_embed_refuses_empty_contact_id():
    client = LocalTransformersEncoderClient(
        model_id="glap",
        expected_dim=GLAP_EMBEDDING_DIM,
        encode_text_fn=lambda t: _unit_vector(GLAP_EMBEDDING_DIM),
        encode_audio_fn=lambda a: [],
    )
    with pytest.raises(LocalEncoderClientError, match="contact_id"):
        client.embed_text(contact_id="", text="hello")


def test_embed_fails_closed_on_wrong_dim():
    client = LocalTransformersEncoderClient(
        model_id="glap",
        expected_dim=GLAP_EMBEDDING_DIM,
        encode_text_fn=lambda t: _unit_vector(512),
        encode_audio_fn=lambda a: [],
    )
    with pytest.raises(LocalEncoderClientError, match="!= pinned 1024"):
        client.embed_text(contact_id="s1", text="hello")


def test_embed_fails_closed_on_non_finite_value():
    values = _unit_vector(GLAP_EMBEDDING_DIM)
    values[1] = math.nan
    client = LocalTransformersEncoderClient(
        model_id="glap", expected_dim=GLAP_EMBEDDING_DIM, encode_text_fn=lambda t: values, encode_audio_fn=lambda a: []
    )
    with pytest.raises(LocalEncoderClientError, match="non-finite"):
        client.embed_text(contact_id="s1", text="hello")


# ---------------------------------------------------------------------------
# MockLocalEncoderClient.
# ---------------------------------------------------------------------------


def test_mock_default_dim_is_glap():
    client = MockLocalEncoderClient()
    vector = client.embed_text(contact_id="s1", text="hello")
    assert vector.dims == GLAP_EMBEDDING_DIM


def test_mock_honors_a_non_default_expected_dim():
    client = MockLocalEncoderClient(expected_dim=CLSP_EMBEDDING_DIM)
    vector = client.embed_audio(contact_id="s1", audio_bytes=b"AUDIO")
    assert vector.dims == CLSP_EMBEDDING_DIM


def test_mock_records_every_call():
    client = MockLocalEncoderClient()
    client.embed_text(contact_id="a", text="x")
    client.embed_audio(contact_id="b", audio_bytes=b"y")
    assert client.calls == [("text", "a"), ("audio", "b")]


def test_mock_distinct_contacts_never_collide():
    client = MockLocalEncoderClient()
    v1 = client.embed_text(contact_id="s1", text="x")
    v2 = client.embed_text(contact_id="s2", text="x")
    assert v1.values != v2.values


def test_mock_honors_a_custom_vector_source():
    def source(kind, contact_id):
        return _unit_vector(GLAP_EMBEDDING_DIM, seed=2.0)

    client = MockLocalEncoderClient(vector_source=source)
    vector = client.embed_text(contact_id="s1", text="x")
    assert vector.values[0] == 2.0


def test_mock_fails_closed_when_vector_source_disagrees_with_expected_dim():
    client = MockLocalEncoderClient(expected_dim=CLSP_EMBEDDING_DIM, vector_source=lambda k, c: _unit_vector(GLAP_EMBEDDING_DIM))
    with pytest.raises(LocalEncoderClientError, match="!= pinned 512"):
        client.embed_text(contact_id="s1", text="x")


# ---------------------------------------------------------------------------
# run_import_feasibility_gate.
# ---------------------------------------------------------------------------


def test_import_feasibility_gate_ok_path():
    result = run_import_feasibility_gate(arm_id="m2-glap-control", model_id="glap", loader=MockLocalEncoderClient)
    assert result.status == STATUS_OK
    assert result.arm_id == "m2-glap-control"
    assert result.model_id == "glap"
    assert result.sanity_vector is not None
    assert result.sanity_vector.dims == GLAP_EMBEDDING_DIM


def test_import_feasibility_gate_dropped_deps_on_loader_import_error():
    def loader():
        raise ImportError("no module named glap")

    result = run_import_feasibility_gate(arm_id="m2-glap-control", model_id="glap", loader=loader)
    assert result.status == STATUS_DROPPED_DEPS
    assert "no module named glap" in result.detail
    assert result.sanity_vector is None


def test_import_feasibility_gate_dropped_deps_on_embed_import_error():
    class _FailingClient:
        def embed_text(self, *, contact_id, text):
            raise ImportError("missing optional dependency")

    result = run_import_feasibility_gate(arm_id="m3-clsp-control", model_id="clsp", loader=_FailingClient)
    assert result.status == STATUS_DROPPED_DEPS


def test_import_feasibility_gate_never_swallows_a_non_import_error():
    def loader():
        raise RuntimeError("a real bug, not a missing dependency")

    with pytest.raises(RuntimeError, match="a real bug"):
        run_import_feasibility_gate(arm_id="m2-glap-control", model_id="glap", loader=loader)


def test_import_feasibility_gate_never_invokes_a_subprocess_or_shell():
    # Structural guarantee: this module's own source contains no
    # subprocess/shell invocation of any kind (a substring search for the
    # word "pip" would false-positive against this module's own PROSE
    # describing the prohibition -- docstrings legitimately discuss "never
    # pip-installed" -- so this test checks only unambiguous invocation
    # surfaces that never appear in prose).
    import inspect

    from speech_aware_evidence_acquisition.rails import local_encoder_client

    source = inspect.getsource(local_encoder_client)
    assert "subprocess" not in source
    assert "os.system" not in source
    assert "os.popen" not in source
