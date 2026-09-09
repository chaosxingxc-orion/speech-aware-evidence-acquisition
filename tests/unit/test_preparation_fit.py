"""Fit actual request envelopes using only an explicitly authorized client."""

import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_fit import (
    GuardedTokenizer,
    fit_requests,
    packet_token_counts,
)


class Client:
    def __init__(self):
        self.calls = []

    def request_json(self, method, path, payload):
        self.calls.append((method, path))
        if path == "/apply-template":
            count = payload["messages"][0]["content"]
            return {"prompt": "A" + "<m>B" * count}
        return {"tokens": list(payload["content"])}


class Renderer:
    def __init__(self):
        self.requests = []

    def render_request(self, raw):
        payload = json.loads(raw)
        self.requests.append(payload)
        return {"messages": [{"content": len(payload["speech"])}], "max_tokens": 5}


def test_guarded_client_refuses_generation_budget_and_lost_lease():
    client, guards = Client(), []
    wrapped = GuardedTokenizer(client, guard=lambda: guards.append(1), contact_cap=1)
    with pytest.raises(PreparationError, match="route"):
        wrapped.request_json("POST", "/v1/chat/completions", {})
    assert not client.calls
    wrapped.request_json("POST", "/tokenize", {"content": "x"})
    assert len(guards) == 1
    with pytest.raises(PreparationError, match="cap"):
        wrapped.request_json("GET", "/props", None)
    assert len(client.calls) == 1
    wrapped = GuardedTokenizer(
        client,
        guard=lambda: (_ for _ in ()).throw(RuntimeError("lease lost")),
        contact_cap=1,
    )
    with pytest.raises(RuntimeError, match="lease lost"):
        wrapped.request_json("GET", "/props", None)
    assert len(client.calls) == 1


def test_full_roster_exact_body_multi_packet_fit_has_no_raw_content():
    transport, client = Renderer(), Client()
    payloads = [
        {"sample_id": "s1", "speech": [3, 4]},
        {"sample_id": "s2", "speech": [1]},
    ]
    result = fit_requests(
        payloads,
        expected_sample_ids=["s1", "s2"],
        transport=transport,
        client=client,
        speech_counts=lambda payload: payload["speech"],
        media_marker="<m>",
        slot_tokens=20,
    )
    assert transport.requests == payloads
    assert result["sample_count"] == 2
    assert result["every_request_fits"]
    assert result["rows"][0]["required_tokens"] == 17
    assert result["rows"][1]["required_tokens"] == 10
    assert "messages" not in json.dumps(result)
    assert result["boundary_sha256"]


@pytest.mark.parametrize("ids", [[], ["s1", "s1"], ["foreign"]])
def test_incomplete_roster_refused_before_any_endpoint(ids):
    transport, client = Renderer(), Client()
    with pytest.raises(PreparationError, match="roster"):
        fit_requests(
            [{"sample_id": sid} for sid in ids],
            expected_sample_ids=["s1"],
            transport=transport,
            client=client,
            speech_counts=lambda p: (),
            media_marker="<m>",
            slot_tokens=20,
        )
    assert not client.calls and not transport.requests


def test_all_rows_measured_even_when_first_does_not_fit():
    result = fit_requests(
        [{"sample_id": "s1", "speech": [30]}, {"sample_id": "s2", "speech": [1]}],
        expected_sample_ids=["s1", "s2"],
        transport=Renderer(),
        client=Client(),
        speech_counts=lambda p: p["speech"],
        media_marker="<m>",
        slot_tokens=20,
    )
    assert result["sample_count"] == 2
    assert not result["every_request_fits"]
    assert result["worst_sample_id"] == "s1"


def test_packet_counts_bind_each_descriptor_and_decoder(tmp_path):
    seen = []

    def load(root, bindings, **kwargs):
        seen.append((root, bindings, kwargs))
        return (
            SimpleNamespace(
                chunks=[SimpleNamespace(n_tokens=2), SimpleNamespace(n_tokens=3)]
            ),
            SimpleNamespace(chunks=[SimpleNamespace(n_tokens=7)]),
        )

    payload = {
        "speech_feature_parts": [
            {"packet_id": "q", "sha256": "a" * 64, "role": "query"},
            {"packet_id": "k", "sha256": "b" * 64, "role": "key"},
        ]
    }
    assert packet_token_counts(
        payload, feature_root=tmp_path, decoder_sha256="c" * 64, loader=load
    ) == (5, 7)
    assert seen[0][1] == (
        {"packet_id": "q", "sha256": "a" * 64},
        {"packet_id": "k", "sha256": "b" * 64},
    )
    assert seen[0][2]["expected_decoder_gguf_sha256"] == "c" * 64
    with pytest.raises(PreparationError, match="packet"):
        packet_token_counts(
            {}, feature_root=tmp_path, decoder_sha256="c" * 64, loader=load
        )


def fit_fixture(tmp_path):
    from unittest.mock import Mock
    from speech_aware_evidence_acquisition.core.preparation import artifact_inputs

    payloads = [{"sample_id": "s1", "speech": [3, 4]}]
    context = {
        "data_root": tmp_path,
        "run_id": "run",
        "attempt_id": "attempt",
        "runtime_receipt": {},
        "runtime_root": tmp_path,
        "required_identity": {"decoder": "c" * 64},
        "values": {},
        "geometry": {"slot_tokens": 20},
        "sample_ids": ["s1"],
    }
    runtime = SimpleNamespace(
        preparation_context=lambda: context,
        materialize_phase_requests=lambda: payloads,
        request_fit_inputs=lambda p, **kwargs: artifact_inputs(
            config={}, split_identity_hash="a" * 64, sources={"boundary": p}
        ),
        authorize_preparation_contacts=Mock(),
    )
    policy = SimpleNamespace(assert_lease=Mock())
    session = SimpleNamespace(
        host="127.0.0.1",
        port=1,
        model_files=[SimpleNamespace(path="model.gguf", sha256="c" * 64)],
    )
    attach = Mock(return_value=(tmp_path, {"session_id": "root"}, session))

    class WithProps(Client):
        def request_json(self, method, path, payload):
            if path == "/props":
                self.calls.append((method, path))
                return {"media_marker": "<m>"}
            return super().request_json(method, path, payload)

    client = WithProps()
    kwargs = {
        "policy": policy,
        "contact_cap": 10,
        "attach": attach,
        "client_factory": lambda **k: client,
        "transport_factory": lambda *a, **k: Renderer(),
        "speech_counter": lambda p: p["speech"],
    }
    return runtime, policy, attach, client, kwargs


def test_attach_only_fit_warm_reuse_and_persisted_contact_accounting(tmp_path):
    from speech_aware_evidence_acquisition.core.preparation_fit import fit_phase_runtime

    runtime, policy, attach, client, kwargs = fit_fixture(tmp_path)
    path = tmp_path / "fit.json"
    receipt = fit_phase_runtime(runtime, path, **kwargs)
    assert receipt["cache"] == "cold"
    output = json.loads(path.read_bytes())["output"]
    assert output["session_id"] == "root"
    assert output["contacts"] == len(client.calls) == 5
    assert len(path.with_name("fit.json.contacts.jsonl").read_text().splitlines()) == 5
    assert policy.assert_lease.call_count == 6
    assert attach.call_args.kwargs["required_identity"] == {"decoder": "c" * 64}
    assert runtime.authorize_preparation_contacts.call_count == 1
    client.calls.clear()
    assert fit_phase_runtime(runtime, path, **kwargs)["cache"] == "warm"
    assert not client.calls
    assert attach.call_count == 1


def test_incomplete_fit_cannot_silently_retry_same_attempt(tmp_path):
    from speech_aware_evidence_acquisition.core.preparation_fit import fit_phase_runtime

    runtime, _policy, _attach, client, kwargs = fit_fixture(tmp_path)
    kwargs["contact_cap"] = 1
    path = tmp_path / "fit.json"
    with pytest.raises(PreparationError, match="cap"):
        fit_phase_runtime(runtime, path, **kwargs)
    assert not path.exists()
    with pytest.raises(PreparationError, match="prior fit contact journal"):
        fit_phase_runtime(runtime, path, **kwargs)
    assert len(client.calls) == 1


def test_fit_authorization_precedes_attachment(tmp_path):
    from speech_aware_evidence_acquisition.core.preparation_fit import fit_phase_runtime

    runtime, _policy, attach, client, kwargs = fit_fixture(tmp_path)
    runtime.authorize_preparation_contacts.side_effect = RuntimeError("unregistered")
    with pytest.raises(RuntimeError, match="unregistered"):
        fit_phase_runtime(runtime, tmp_path / "fit.json", **kwargs)
    assert not client.calls and not attach.called


def test_boundary_identity_ignores_only_nonprompt_routing():
    from speech_aware_evidence_acquisition.core.preparation_fit import boundary_identity

    original = [
        {
            "sample_id": "s1",
            "request_id": "first",
            "decoding_params": {"id_slot": 0, "max_tokens": 5},
        }
    ]
    changed = [
        {
            "sample_id": "s1",
            "request_id": "second",
            "decoding_params": {"id_slot": 2, "max_tokens": 5},
        }
    ]
    assert boundary_identity(original) == boundary_identity(changed)
    changed[0]["decoding_params"]["max_tokens"] = 6
    assert boundary_identity(original) != boundary_identity(changed)


def test_window_requests_keep_parent_identity_and_require_every_window():
    from speech_aware_evidence_acquisition.core.preparation import (
        measure_multimodal_request,
    )

    payloads = [
        {"sample_id": "call", "media_relpath": "i0.wav", "speech": []},
        {"sample_id": "call", "media_relpath": "i1.wav", "speech": []},
    ]

    class CountClient:
        def request_json(self, method, path, payload):
            assert path == "/v1/chat/completions/input_tokens"
            return {"input_tokens": 10}

    result = fit_requests(
        payloads,
        expected_sample_ids=["i0.wav", "i1.wav"],
        request_key=lambda p: p["media_relpath"],
        request_measure=measure_multimodal_request,
        transport=Renderer(),
        client=CountClient(),
        speech_counts=lambda p: (),
        media_marker="<m>",
        slot_tokens=40,
        fit_multiple=2,
    )
    assert [row["sample_id"] for row in result["rows"]] == ["call", "call"]
    assert [row["request_key"] for row in result["rows"]] == ["i0.wav", "i1.wav"]
    assert result["every_request_fits"]


def test_window_batch_fit_uses_real_multimodal_count_route(tmp_path):
    from speech_aware_evidence_acquisition.core.preparation_fit import fit_phase_runtime
    from speech_aware_evidence_acquisition.core.preparation_windows import (
        WindowRequestBatch,
    )

    runtime, _policy, _attach, client, kwargs = fit_fixture(tmp_path)
    payloads = ({"sample_id": "s1", "media_relpath": "slice.wav", "speech": []},)
    batch = WindowRequestBatch(
        payloads, ("s1#w0001",), ({"sample_id": "s1", "media_relpath": "slice.wav"},)
    )
    original = client.request_json

    def count(method, path, payload):
        if path == "/v1/chat/completions/input_tokens":
            client.calls.append((method, path))
            return {"input_tokens": 2}
        return original(method, path, payload)

    client.request_json = count
    runtime.materialize_phase_requests = lambda: pytest.fail(
        "window fit used phase fake transport"
    )
    kwargs["speech_counter"] = lambda p: pytest.fail(
        "window fit estimated speech tokens"
    )
    path = tmp_path / "window-fit.json"
    fit_phase_runtime(runtime, path, window_batch=batch, **kwargs)
    output = json.loads(path.read_bytes())["output"]
    assert output["rows"][0]["request_key"] == "s1#w0001"
    assert output["rows"][0]["fit_multiple"] == 2.0
    assert output["rows"][0]["measurement"] == "resident-multimodal-input-tokens"
    assert client.calls == [
        ("GET", "/props"),
        ("POST", "/v1/chat/completions/input_tokens"),
    ]
    authorization_calls = runtime.authorize_preparation_contacts.call_count
    client.calls.clear()
    assert fit_phase_runtime(runtime, path, window_batch=batch, **kwargs)["cache"] == "warm"
    assert runtime.authorize_preparation_contacts.call_count == authorization_calls
    assert client.calls == []


def test_shared_fit_dispatches_raw_window_batch_before_attachment(tmp_path):
    """A coordinator and the CLI both reach this shared fitter entry point."""
    from unittest.mock import Mock

    from speech_aware_evidence_acquisition.core.preparation_fit import fit_phase_runtime
    from speech_aware_evidence_acquisition.core.preparation_windows import (
        WindowRequestBatch,
    )

    runtime, _policy, attach, client, kwargs = fit_fixture(tmp_path)
    batch = WindowRequestBatch(
        ({"sample_id": "s1", "media_relpath": "slice.wav", "speech": []},),
        ("s1#w0001",),
        ({"sample_id": "s1", "media_relpath": "slice.wav", "sha256": "a"},),
    )
    runtime.materialize_phase_requests = Mock(
        side_effect=AssertionError("raw fit selected phase request materialization")
    )
    events = []
    runtime.materialize_request_fit_batch = Mock(
        side_effect=lambda **_kwargs: (events.append("materialize"), batch)[1]
    )
    attach.side_effect = lambda *args, **kwargs: (
        events.append("attach"), attach.return_value
    )[1]
    original = client.request_json

    def count(method, path, payload):
        if path == "/v1/chat/completions/input_tokens":
            client.calls.append((method, path))
            return {"input_tokens": 2}
        return original(method, path, payload)

    client.request_json = count
    fit_phase_runtime(runtime, tmp_path / "fit.json", **kwargs)
    runtime.materialize_request_fit_batch.assert_called_once_with(execution_plan=None)
    assert attach.called
    assert events == ["materialize", "attach"]
    assert client.calls == [
        ("GET", "/props"),
        ("POST", "/v1/chat/completions/input_tokens"),
    ]
