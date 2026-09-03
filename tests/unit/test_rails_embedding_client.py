"""``rails.embedding_client``: the P-EMB embedding-tier client (SAEA-PROBE-
pemb1-78 / SAEA-PROBE-pemb2-552). Engineering-only, ZERO live model contact
-- every test here drives a fake ``post``/``get`` pair or
:class:`MockEmbeddingClient`, never a real socket.
"""

from __future__ import annotations

import itertools
import json
import math

import pytest

from speech_aware_evidence_acquisition.rails.embedding_client import (
    BatchedEmbeddingClientProtocol,
    EMBEDDING_DIM,
    EmbeddingClient,
    EmbeddingClientError,
    EmbeddingClientProtocol,
    EmbeddingVector,
    MockEmbeddingClient,
    assert_no_conflicting_generation_server,
    deterministic_unit_vector,
    resolve_expected_media_marker,
)

_MARKER = "<__media__>"
_BASE_URL = "http://127.0.0.1:8091"


def _unit_vector(seed: float = 1.0, dims: int = EMBEDDING_DIM) -> list[float]:
    values = [0.0] * dims
    values[0] = seed
    return values


def _pooled_response(vector, *, nested: bool = False) -> bytes:
    embedding = [list(vector)] if nested else list(vector)
    return json.dumps([{"index": 0, "embedding": embedding}]).encode("utf-8")


def _batched_response(*vectors) -> bytes:
    return json.dumps(
        [
            {"index": index, "embedding": list(vector)}
            for index, vector in enumerate(vectors)
        ]
    ).encode("utf-8")


def _props_response(marker: str = _MARKER, *, field: str = "media_marker") -> bytes:
    return json.dumps({field: marker, "total_slots": 1}).encode("utf-8")


class _FakeTransport:
    """Captures every POST body and GET url; returns canned bytes."""

    def __init__(
        self, *, post_response: bytes | None = None, get_response: bytes | None = None
    ):
        self.post_calls: list[tuple[str, dict]] = []
        self.get_calls: list[str] = []
        self._post_response = post_response
        self._get_response = get_response

    def post(self, url: str, body: bytes) -> bytes:
        payload = json.loads(body.decode("utf-8"))
        self.post_calls.append((url, payload))
        if self._post_response is None:
            raise AssertionError("no post_response configured")
        return self._post_response

    def get(self, url: str) -> bytes:
        self.get_calls.append(url)
        if self._get_response is None:
            raise AssertionError("no get_response configured")
        return self._get_response


def _client(transport: _FakeTransport, *, marker: str = _MARKER) -> EmbeddingClient:
    # A bounded-safe monotonic clock (0.0, 0.75, 1.5, ...) rather than a
    # fixed 2-item iterator: any number of embed_*/close calls on one
    # client instance stays well-defined, never a StopIteration.
    return EmbeddingClient(
        base_url=_BASE_URL,
        expected_media_marker=marker,
        post=transport.post,
        get=transport.get,
        now=itertools.count(0.0, 0.75).__next__,
    )


# ---------------------------------------------------------------------------
# Construction / loopback enforcement.
# ---------------------------------------------------------------------------


def test_construction_refuses_a_non_loopback_base_url():
    transport = _FakeTransport()
    with pytest.raises(EmbeddingClientError):
        EmbeddingClient(
            base_url="http://example.com:8091",
            expected_media_marker=_MARKER,
            post=transport.post,
            get=transport.get,
        )


def test_construction_refuses_empty_marker():
    transport = _FakeTransport()
    with pytest.raises(EmbeddingClientError, match="expected_media_marker"):
        EmbeddingClient(
            base_url=_BASE_URL,
            expected_media_marker="",
            post=transport.post,
            get=transport.get,
        )


def test_construction_accepts_localhost_and_ipv6_loopback():
    transport = _FakeTransport()
    EmbeddingClient(
        base_url="http://localhost:8091",
        expected_media_marker=_MARKER,
        post=transport.post,
        get=transport.get,
    )
    EmbeddingClient(
        base_url="http://[::1]:8091",
        expected_media_marker=_MARKER,
        post=transport.post,
        get=transport.get,
    )


# ---------------------------------------------------------------------------
# verify_media_marker.
# ---------------------------------------------------------------------------


def test_verify_media_marker_succeeds_and_records_props():
    transport = _FakeTransport(get_response=_props_response())
    client = _client(transport)
    props = client.verify_media_marker()
    assert props["media_marker"] == _MARKER
    assert client.marker_verified is True
    assert transport.get_calls == [_BASE_URL + "/props"]


def test_verify_media_marker_fails_closed_on_missing_field():
    transport = _FakeTransport(
        get_response=json.dumps({"total_slots": 1}).encode("utf-8")
    )
    client = _client(transport)
    with pytest.raises(EmbeddingClientError, match="media_marker"):
        client.verify_media_marker()
    assert client.marker_verified is False


def test_verify_media_marker_fails_closed_on_mismatch():
    transport = _FakeTransport(get_response=_props_response(marker="<other>"))
    client = _client(transport)
    with pytest.raises(EmbeddingClientError, match="does not match"):
        client.verify_media_marker()
    assert client.marker_verified is False


def test_verify_media_marker_fails_closed_on_invalid_json():
    transport = _FakeTransport(get_response=b"not json")
    client = _client(transport)
    with pytest.raises(EmbeddingClientError, match="invalid JSON"):
        client.verify_media_marker()


def test_verify_media_marker_fails_closed_on_non_object_response():
    transport = _FakeTransport(get_response=b"[1, 2, 3]")
    client = _client(transport)
    with pytest.raises(EmbeddingClientError, match="JSON object"):
        client.verify_media_marker()


# ---------------------------------------------------------------------------
# marker-must-be-verified-first ordering.
# ---------------------------------------------------------------------------


def test_embed_text_refuses_before_marker_verified():
    transport = _FakeTransport(post_response=_pooled_response(_unit_vector()))
    client = _client(transport)
    with pytest.raises(EmbeddingClientError, match="verify_media_marker"):
        client.embed_text(contact_id="alarm", text="alarm")
    assert transport.post_calls == []


def test_embed_audio_refuses_before_marker_verified():
    transport = _FakeTransport(post_response=_pooled_response(_unit_vector()))
    client = _client(transport)
    with pytest.raises(EmbeddingClientError, match="verify_media_marker"):
        client.embed_audio(contact_id="s1", audio_bytes=b"fake-wav-bytes")
    assert transport.post_calls == []


# ---------------------------------------------------------------------------
# embed_text / embed_audio request-shape + response parsing.
# ---------------------------------------------------------------------------


def test_embed_text_sends_plain_content_string_no_sampling_params():
    transport = _FakeTransport(
        get_response=_props_response(),
        post_response=_pooled_response(_unit_vector(2.0)),
    )
    client = _client(transport)
    client.verify_media_marker()
    vector = client.embed_text(contact_id="alarm", text="alarm")
    assert isinstance(vector, EmbeddingVector)
    assert vector.contact_id == "alarm"
    assert vector.kind == "text"
    url, body = transport.post_calls[0]
    assert url == _BASE_URL + "/embedding"
    # Determinism-friendly: EXACTLY {"content": [...]} -- no decoding/sampling key of any kind.
    assert set(body.keys()) == {"content"}
    assert body["content"] == ["alarm"]


def test_embed_text_batch_sends_one_request_and_ledgers_each_item_in_order():
    transport = _FakeTransport(
        get_response=_props_response(),
        post_response=_batched_response(_unit_vector(1.0), _unit_vector(2.0)),
    )
    client = _client(transport)
    client.verify_media_marker()

    vectors = client.embed_text_batch(
        (("first", "hello"), ("second", "world", "query: "))
    )

    assert [vector.contact_id for vector in vectors] == ["first", "second"]
    assert [vector.values[0] for vector in vectors] == [1.0, 2.0]
    assert transport.post_calls == [
        (_BASE_URL + "/embedding", {"content": ["hello", "query: world"]})
    ]
    assert [contact.contact_id for contact in client.contacts] == ["first", "second"]
    assert all(contact.kind == "text" for contact in client.contacts)
    assert all(
        contact.latency_seconds == pytest.approx(0.75) for contact in client.contacts
    )
    assert client.http_request_count == 1
    summary = client.close()
    assert summary["contact_count"] == 2
    assert summary["http_request_count"] == 1


def test_embed_text_batch_uses_response_indexes_to_restore_input_order():
    response = json.dumps(
        [
            {"index": 1, "embedding": _unit_vector(2.0)},
            {"index": 0, "embedding": _unit_vector(1.0)},
        ]
    ).encode("utf-8")
    transport = _FakeTransport(get_response=_props_response(), post_response=response)
    client = _client(transport)
    client.verify_media_marker()

    vectors = client.embed_text_batch((("first", "hello"), ("second", "world")))

    assert [vector.contact_id for vector in vectors] == ["first", "second"]
    assert [vector.values[0] for vector in vectors] == [1.0, 2.0]


@pytest.mark.parametrize(
    ("items", "message"),
    (
        ((), "non-empty"),
        ((("same", "one"), ("same", "two")), "distinct"),
        ((("", "text"),), "contact_id"),
        ((("id", ""),), "text"),
        ((("id", "text", None),), "prefix"),
        ((("id",),), "two or three"),
    ),
)
def test_embed_text_batch_rejects_malformed_items_before_post(items, message):
    transport = _FakeTransport(get_response=_props_response())
    client = _client(transport)
    client.verify_media_marker()

    with pytest.raises(EmbeddingClientError, match=message):
        client.embed_text_batch(items)

    assert transport.post_calls == []
    assert client.contacts == ()
    assert client.http_request_count == 0


def test_embed_text_batch_response_count_mismatch_is_atomic_but_request_is_audited():
    transport = _FakeTransport(
        get_response=_props_response(),
        post_response=_batched_response(_unit_vector()),
    )
    client = _client(transport)
    client.verify_media_marker()

    with pytest.raises(EmbeddingClientError, match="expected 2"):
        client.embed_text_batch((("first", "hello"), ("second", "world")))

    assert client.contacts == ()
    assert client.http_request_count == 1


def test_embed_text_batch_illegal_later_vector_does_not_partially_ledger():
    illegal = _unit_vector()
    illegal[4] = math.nan
    transport = _FakeTransport(
        get_response=_props_response(),
        post_response=_batched_response(_unit_vector(), illegal),
    )
    client = _client(transport)
    client.verify_media_marker()

    with pytest.raises(EmbeddingClientError, match="non-finite"):
        client.embed_text_batch((("first", "hello"), ("second", "world")))

    assert client.contacts == ()
    assert client.http_request_count == 1


def test_embed_text_batch_wrong_dimension_is_atomic():
    transport = _FakeTransport(
        get_response=_props_response(),
        post_response=_batched_response(_unit_vector(), [1.0, 0.0]),
    )
    client = _client(transport)
    client.verify_media_marker()

    with pytest.raises(EmbeddingClientError, match="dim"):
        client.embed_text_batch((("first", "hello"), ("second", "world")))

    assert client.contacts == ()
    assert client.http_request_count == 1


def test_embed_text_batch_refuses_before_verify_and_after_close():
    transport = _FakeTransport(
        post_response=_batched_response(_unit_vector()),
        get_response=_props_response(),
    )
    client = _client(transport)
    with pytest.raises(EmbeddingClientError, match="verify_media_marker"):
        client.embed_text_batch((("first", "hello"),))
    client.verify_media_marker()
    client.close()
    with pytest.raises(EmbeddingClientError, match="close"):
        client.embed_text_batch((("first", "hello"),))
    assert transport.post_calls == []


def test_embed_audio_sends_non_chat_marker_schema():
    transport = _FakeTransport(
        get_response=_props_response(),
        post_response=_pooled_response(_unit_vector(3.0)),
    )
    client = _client(transport)
    client.verify_media_marker()
    vector = client.embed_audio(contact_id="s1", audio_bytes=b"RIFF-fake-audio-bytes")
    assert vector.kind == "audio"
    url, body = transport.post_calls[0]
    assert url == _BASE_URL + "/embedding"
    assert set(body.keys()) == {"content"}
    assert len(body["content"]) == 1
    item = body["content"][0]
    assert set(item.keys()) == {"prompt_string", "multimodal_data"}
    assert item["prompt_string"] == _MARKER
    import base64

    assert base64.b64decode(item["multimodal_data"][0]) == b"RIFF-fake-audio-bytes"


def test_embed_audio_accepts_flat_and_nested_pooled_shapes():
    vec = _unit_vector(1.5)
    for nested in (False, True):
        transport = _FakeTransport(
            get_response=_props_response(),
            post_response=_pooled_response(vec, nested=nested),
        )
        client = _client(transport)
        client.verify_media_marker()
        result = client.embed_audio(contact_id="s1", audio_bytes=b"x")
        assert list(result.values) == vec


def test_embed_refuses_multi_row_pooled_response():
    transport = _FakeTransport(
        get_response=_props_response(),
        post_response=json.dumps(
            [{"index": 0, "embedding": [_unit_vector(), _unit_vector()]}]
        ).encode("utf-8"),
    )
    client = _client(transport)
    client.verify_media_marker()
    with pytest.raises(EmbeddingClientError, match="single pooled row"):
        client.embed_audio(contact_id="s1", audio_bytes=b"x")


def test_embed_refuses_response_with_wrong_row_count():
    transport = _FakeTransport(
        get_response=_props_response(),
        post_response=json.dumps(
            [
                {"index": 0, "embedding": _unit_vector()},
                {"index": 1, "embedding": _unit_vector()},
            ]
        ).encode("utf-8"),
    )
    client = _client(transport)
    client.verify_media_marker()
    with pytest.raises(EmbeddingClientError, match="expected 1"):
        client.embed_text(contact_id="a", text="a")


def test_embed_fails_closed_on_wrong_dim():
    transport = _FakeTransport(
        get_response=_props_response(), post_response=_pooled_response([0.1, 0.2, 0.3])
    )
    client = _client(transport)
    client.verify_media_marker()
    with pytest.raises(EmbeddingClientError, match="dim"):
        client.embed_text(contact_id="a", text="a")


def test_embed_fails_closed_on_non_finite_value():
    vector = _unit_vector()
    vector[5] = math.nan
    transport = _FakeTransport(
        get_response=_props_response(), post_response=_pooled_response(vector)
    )
    client = _client(transport)
    client.verify_media_marker()
    with pytest.raises(EmbeddingClientError, match="non-finite"):
        client.embed_text(contact_id="a", text="a")


def test_embed_fails_closed_on_infinite_value():
    vector = _unit_vector()
    vector[5] = math.inf
    transport = _FakeTransport(
        get_response=_props_response(), post_response=_pooled_response(vector)
    )
    client = _client(transport)
    client.verify_media_marker()
    with pytest.raises(EmbeddingClientError, match="non-finite"):
        client.embed_audio(contact_id="a", audio_bytes=b"x")


def test_embed_text_refuses_empty_contact_id_or_text():
    transport = _FakeTransport(get_response=_props_response())
    client = _client(transport)
    client.verify_media_marker()
    with pytest.raises(EmbeddingClientError):
        client.embed_text(contact_id="", text="alarm")
    with pytest.raises(EmbeddingClientError):
        client.embed_text(contact_id="alarm", text="")


def test_embed_audio_refuses_empty_bytes():
    transport = _FakeTransport(get_response=_props_response())
    client = _client(transport)
    client.verify_media_marker()
    with pytest.raises(EmbeddingClientError):
        client.embed_audio(contact_id="s1", audio_bytes=b"")


# ---------------------------------------------------------------------------
# Per-contact logging.
# ---------------------------------------------------------------------------


def test_contacts_records_one_entry_per_call_with_dims_and_latency():
    transport = _FakeTransport(
        get_response=_props_response(), post_response=_pooled_response(_unit_vector())
    )
    client = _client(transport)
    client.verify_media_marker()
    client.embed_text(contact_id="alarm", text="alarm")
    assert len(client.contacts) == 1
    contact = client.contacts[0]
    assert contact.contact_id == "alarm"
    assert contact.kind == "text"
    assert contact.dims == EMBEDDING_DIM
    assert contact.latency_seconds == pytest.approx(0.75)
    assert contact.as_json()["contact_id"] == "alarm"


# ---------------------------------------------------------------------------
# close().
# ---------------------------------------------------------------------------


def test_close_reports_contact_count_and_refuses_a_second_call():
    transport = _FakeTransport(
        get_response=_props_response(), post_response=_pooled_response(_unit_vector())
    )
    client = _client(transport)
    client.verify_media_marker()
    client.embed_text(contact_id="a", text="a")
    summary = client.close()
    assert summary["contact_count"] == 1
    with pytest.raises(EmbeddingClientError, match="twice"):
        client.close()


def test_embed_after_close_is_refused():
    transport = _FakeTransport(
        get_response=_props_response(), post_response=_pooled_response(_unit_vector())
    )
    client = _client(transport)
    client.verify_media_marker()
    client.close()
    with pytest.raises(EmbeddingClientError, match="close"):
        client.embed_text(contact_id="a", text="a")


# ---------------------------------------------------------------------------
# resolve_expected_media_marker.
# ---------------------------------------------------------------------------


def test_resolve_expected_media_marker_reads_env():
    assert resolve_expected_media_marker({"LLAMA_MEDIA_MARKER": _MARKER}) == _MARKER


def test_resolve_expected_media_marker_fails_closed_on_unset():
    with pytest.raises(EmbeddingClientError, match="LLAMA_MEDIA_MARKER"):
        resolve_expected_media_marker({})


def test_resolve_expected_media_marker_fails_closed_on_empty():
    with pytest.raises(EmbeddingClientError):
        resolve_expected_media_marker({"LLAMA_MEDIA_MARKER": ""})


# ---------------------------------------------------------------------------
# assert_no_conflicting_generation_server.
# ---------------------------------------------------------------------------


def test_assert_no_conflicting_generation_server_passes_when_unreachable():
    assert_no_conflicting_generation_server(
        generation_server_reachable=lambda: False,
        generation_base_url="http://127.0.0.1:8090",
    )


def test_assert_no_conflicting_generation_server_refuses_when_reachable():
    with pytest.raises(EmbeddingClientError, match="coexist"):
        assert_no_conflicting_generation_server(
            generation_server_reachable=lambda: True,
            generation_base_url="http://127.0.0.1:8090",
        )


# ---------------------------------------------------------------------------
# MockEmbeddingClient.
# ---------------------------------------------------------------------------


def test_mock_embedding_client_requires_marker_verification_first():
    client = MockEmbeddingClient()
    with pytest.raises(EmbeddingClientError, match="verify_media_marker"):
        client.embed_text(contact_id="a", text="a")


def test_mock_embedding_client_default_vectors_are_legal_and_deterministic():
    client = MockEmbeddingClient()
    client.verify_media_marker()
    v1 = client.embed_text(contact_id="alarm", text="alarm")
    v2 = client.embed_text(contact_id="alarm", text="alarm")
    assert v1.values == v2.values
    assert len(v1.values) == EMBEDDING_DIM
    assert client.calls == [("text", "alarm"), ("text", "alarm")]


def test_mock_embedding_client_distinct_contacts_never_collide():
    client = MockEmbeddingClient()
    client.verify_media_marker()
    v1 = client.embed_audio(contact_id="s1", audio_bytes=b"x")
    v2 = client.embed_audio(contact_id="s2", audio_bytes=b"x")
    assert v1.values != v2.values


def test_mock_embedding_client_honors_a_custom_vector_source():
    def source(kind, contact_id):
        return [1.0 if index == 0 else 0.0 for index in range(EMBEDDING_DIM)]

    client = MockEmbeddingClient(vector_source=source)
    client.verify_media_marker()
    vector = client.embed_audio(contact_id="s1", audio_bytes=b"x")
    assert vector.values[0] == 1.0
    assert vector.values[1] == 0.0


def test_mock_embedding_client_supports_text_batches_without_io():
    client = MockEmbeddingClient(expected_dim=8)
    client.verify_media_marker()

    vectors = client.embed_text_batch(
        (("first", "hello"), ("second", "world", "query: "))
    )

    assert [vector.contact_id for vector in vectors] == ["first", "second"]
    assert all(vector.dims == 8 for vector in vectors)
    assert client.calls == [("text", "first"), ("text", "second")]
    assert client.prefixes == ["", "query: "]
    assert client.batch_request_count == 1


def test_batch_protocol_extends_without_breaking_the_legacy_protocol():
    class LegacyEmbeddingClient:
        def verify_media_marker(self):
            return {}

        def embed_text(self, *, contact_id, text, prefix=""):
            return None

        def embed_audio(self, *, contact_id, audio_bytes, prompt_prefix=""):
            return None

    legacy = LegacyEmbeddingClient()

    assert isinstance(legacy, EmbeddingClientProtocol)
    assert not isinstance(legacy, BatchedEmbeddingClientProtocol)
    assert isinstance(MockEmbeddingClient(), BatchedEmbeddingClientProtocol)


def test_deterministic_unit_vector_is_l2_normalized():
    vector = deterministic_unit_vector("seed-a")
    norm = math.sqrt(sum(v * v for v in vector))
    assert norm == pytest.approx(1.0, abs=1e-9)


def test_deterministic_unit_vector_differs_across_seeds():
    assert deterministic_unit_vector("a") != deterministic_unit_vector("b")


# ---------------------------------------------------------------------------
# P-EMB-3M EXTENSION: expected_dim / require_marker_verification.
# ---------------------------------------------------------------------------


def _dim_vector(dim: int, seed: float = 1.0) -> list[float]:
    values = [0.0] * dim
    values[0] = seed
    return values


def test_expected_dim_defaults_to_embedding_dim():
    transport = _FakeTransport()
    client = _client(transport)
    assert client.expected_dim == EMBEDDING_DIM


def test_construction_refuses_non_positive_expected_dim():
    transport = _FakeTransport()
    with pytest.raises(EmbeddingClientError, match="expected_dim"):
        EmbeddingClient(
            base_url=_BASE_URL,
            expected_media_marker=_MARKER,
            post=transport.post,
            get=transport.get,
            expected_dim=0,
        )


def test_embed_text_accepts_a_1024_dim_vector_when_expected_dim_is_1024():
    transport = _FakeTransport(
        post_response=_pooled_response(_dim_vector(1024)),
        get_response=_props_response(),
    )
    client = EmbeddingClient(
        base_url=_BASE_URL,
        expected_media_marker=_MARKER,
        post=transport.post,
        get=transport.get,
        expected_dim=1024,
    )
    client.verify_media_marker()
    vector = client.embed_text(contact_id="s1", text="hello")
    assert vector.dims == 1024


def test_embed_text_fails_closed_on_wrong_dim_for_a_non_default_expected_dim():
    transport = _FakeTransport(
        post_response=_pooled_response(_dim_vector(2048)),
        get_response=_props_response(),
    )
    client = EmbeddingClient(
        base_url=_BASE_URL,
        expected_media_marker=_MARKER,
        post=transport.post,
        get=transport.get,
        expected_dim=1024,
    )
    client.verify_media_marker()
    with pytest.raises(EmbeddingClientError, match="!= pinned 1024"):
        client.embed_text(contact_id="s1", text="hello")


def test_require_marker_verification_defaults_to_true_and_requires_a_marker():
    transport = _FakeTransport()
    with pytest.raises(EmbeddingClientError, match="expected_media_marker"):
        EmbeddingClient(base_url=_BASE_URL, post=transport.post, get=transport.get)


def test_require_marker_verification_false_never_issues_a_get_request():
    transport = _FakeTransport(post_response=_pooled_response(_dim_vector(1024)))
    client = EmbeddingClient(
        base_url=_BASE_URL,
        post=transport.post,
        get=transport.get,
        expected_dim=1024,
        require_marker_verification=False,
    )
    props = client.verify_media_marker()
    assert props == {}
    assert client.marker_verified is True
    assert transport.get_calls == []
    vector = client.embed_text(contact_id="s1", text="hello")
    assert vector.dims == 1024


def test_require_marker_verification_false_still_requires_verify_media_marker_called_first():
    transport = _FakeTransport(post_response=_pooled_response(_dim_vector(1024)))
    client = EmbeddingClient(
        base_url=_BASE_URL,
        post=transport.post,
        get=transport.get,
        expected_dim=1024,
        require_marker_verification=False,
    )
    with pytest.raises(EmbeddingClientError, match="verify_media_marker"):
        client.embed_text(contact_id="s1", text="hello")


def test_mock_embedding_client_expected_dim_defaults_to_embedding_dim():
    client = MockEmbeddingClient()
    client.verify_media_marker()
    vector = client.embed_text(contact_id="s1", text="hello")
    assert vector.dims == EMBEDDING_DIM


def test_mock_embedding_client_honors_a_non_default_expected_dim():
    client = MockEmbeddingClient(expected_dim=1024)
    client.verify_media_marker()
    vector = client.embed_text(contact_id="s1", text="hello")
    assert vector.dims == 1024


def test_mock_embedding_client_fails_closed_when_vector_source_disagrees_with_expected_dim():
    client = MockEmbeddingClient(
        expected_dim=1024, vector_source=lambda kind, cid: _dim_vector(EMBEDDING_DIM)
    )
    client.verify_media_marker()
    with pytest.raises(EmbeddingClientError, match="!= pinned 1024"):
        client.embed_text(contact_id="s1", text="hello")
