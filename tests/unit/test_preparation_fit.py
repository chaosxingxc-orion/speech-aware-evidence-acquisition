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


def test_fit_uses_shared_configured_transport_builder(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.preparation_fit import fit_phase_runtime
    import speech_aware_evidence_acquisition.core.configured_transport as configured

    runtime, _policy, _attach, _client, kwargs = fit_fixture(tmp_path)
    supplied_factory = kwargs["transport_factory"]
    calls = []

    def build(values, data_root, **builder_kwargs):
        calls.append((values, data_root, builder_kwargs))
        return Renderer()

    monkeypatch.setattr(configured, "build_configured_transport", build)
    fit_phase_runtime(runtime, tmp_path / "fit-shared-transport.json", **kwargs)
    assert len(calls) == 1
    assert calls[0][0] == runtime.preparation_context()["values"]
    assert calls[0][1] == tmp_path
    assert calls[0][2]["transport_factory"] is supplied_factory


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


def test_prepared_phase_reuses_real_payloads_and_warm_fit_has_zero_contacts(tmp_path):
    from dataclasses import FrozenInstanceError
    from speech_aware_evidence_acquisition.core.preparation_fit import (
        fit_phase_runtime, materialize_phase_fit,
    )
    runtime, _policy, attach, client, kwargs = fit_fixture(tmp_path)
    original = runtime.materialize_phase_requests()
    prepared = materialize_phase_fit(runtime)
    original[0]["speech"].append(999)
    runtime.materialize_phase_requests = lambda: pytest.fail("materialized twice")
    with pytest.raises(FrozenInstanceError):
        prepared.run_id = "changed"
    path = tmp_path / "prepared-fit.json"
    fit_phase_runtime(runtime, path, prepared_phase=prepared, **kwargs)
    output = json.loads(path.read_bytes())["output"]
    assert output["rows"][0]["speech_tokens"] == 7
    client.calls.clear()
    fit_phase_runtime(runtime, path, prepared_phase=prepared, **kwargs)
    assert client.calls == [] and attach.call_count == 1


@pytest.mark.parametrize("drift", ["run", "attempt", "config", "source", "cap", "roster"])
def test_prepared_phase_drift_refused_before_authorization(tmp_path, drift):
    from dataclasses import replace
    from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
    from speech_aware_evidence_acquisition.core.preparation_fit import (
        fit_phase_runtime, materialize_phase_fit,
    )
    runtime, _policy, attach, client, kwargs = fit_fixture(tmp_path)
    prepared = materialize_phase_fit(runtime)
    context = runtime.preparation_context()
    if drift in {"run", "attempt"}:
        context[drift + "_id"] = "different"
    elif drift == "roster":
        context["sample_ids"] = ["s1", "s2"]
    elif drift == "cap":
        payload = json.loads(prepared.payload_bytes[0])
        payload["decoding_params"] = {"max_tokens": 256}
        prepared = replace(prepared, payload_bytes=(canonical_bytes(payload),))
    else:
        previous = runtime.request_fit_inputs
        runtime.request_fit_inputs = lambda p: {**previous(p), drift: "different"}
    with pytest.raises(PreparationError):
        fit_phase_runtime(runtime, tmp_path / "fit.json", prepared_phase=prepared, **kwargs)
    assert not runtime.authorize_preparation_contacts.called
    assert not attach.called and not client.calls


@pytest.mark.parametrize("ids", [[], ["s1", "s1"], ["s2"]])
def test_phase_materializer_rejects_incomplete_or_duplicate_roster(tmp_path, ids):
    from speech_aware_evidence_acquisition.core.preparation_fit import materialize_phase_fit
    runtime, _policy, attach, client, _kwargs = fit_fixture(tmp_path)
    runtime.materialize_phase_requests = lambda: [{"sample_id": sid} for sid in ids]
    with pytest.raises(PreparationError, match="roster"):
        materialize_phase_fit(runtime)
    assert not attach.called and not client.calls


def test_prepared_phase_and_window_batch_are_mutually_exclusive(tmp_path):
    from speech_aware_evidence_acquisition.core.preparation_fit import (
        fit_phase_runtime, materialize_phase_fit,
    )
    runtime, _policy, attach, client, kwargs = fit_fixture(tmp_path)
    prepared = materialize_phase_fit(runtime)
    with pytest.raises(PreparationError, match="either"):
        fit_phase_runtime(
            runtime, tmp_path / "fit.json", prepared_phase=prepared,
            window_batch=object(), **kwargs,
        )
    assert not attach.called and not client.calls


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


def test_capacity_identity_normalizes_only_owned_supply_trace_routes():
    from copy import deepcopy
    from speech_aware_evidence_acquisition.core.preparation_fit import boundary_identity
    from speech_aware_evidence_acquisition.core.preparation import PreparationError

    first = {
        "sample_id": "sample", "request_id": "flight-0001",
        "decoding_params": {"id_slot": 0, "max_tokens": 256},
        "evidence_provenance": [
            {"lock_key": "rails-supply", "relpath": "rails-message/flight-0001/0", "sha256": "a" * 64},
            {"lock_key": "rails-supply", "relpath": "rails-message/flight-0001/1", "sha256": "b" * 64},
        ],
        "supplied_evidence": [{"content": "first"}, {"content": "second"}],
    }
    second = deepcopy(first)
    second["request_id"] = "flight-0039"
    second["decoding_params"]["id_slot"] = 3
    for index, source in enumerate(second["evidence_provenance"]):
        source["relpath"] = f"rails-message/flight-0039/{index}"
    original = deepcopy(first)
    assert boundary_identity([first]) == boundary_identity([second])
    assert first == original
    for mutate in (
        lambda value: value["evidence_provenance"][0].update(sha256="c" * 64),
        lambda value: value["supplied_evidence"].reverse(),
        lambda value: value["decoding_params"].update(max_tokens=64),
    ):
        changed = deepcopy(second)
        mutate(changed)
        assert boundary_identity([first]) != boundary_identity([changed])
    wrong_owner = deepcopy(second)
    wrong_owner["evidence_provenance"][0]["relpath"] = "rails-message/another-request/0"
    with pytest.raises(PreparationError, match="not bound to this request"):
        boundary_identity([wrong_owner])
    external = deepcopy(first)
    external["evidence_provenance"][0]["lock_key"] = "carrier-source"
    changed = deepcopy(external)
    changed["evidence_provenance"][0]["relpath"] = "different-source"
    assert boundary_identity([external]) != boundary_identity([changed])


def test_formal_window_fit_counts_bound_packets_instead_of_raw_input_endpoint(tmp_path):
    from speech_aware_evidence_acquisition.core.preparation_fit import fit_phase_runtime
    from speech_aware_evidence_acquisition.core.preparation_windows import WindowRequestBatch

    runtime, _policy, _attach, client, kwargs = fit_fixture(tmp_path)
    payload = {
        "sample_id": "s1", "media_relpath": "slice.wav", "speech": [7],
        "speech_feature_parts": [{"packet_id": "q", "sha256": "a" * 64, "role": "query"}],
    }
    batch = WindowRequestBatch(
        (payload,), ("s1#w0001",), ({"sample_id": "s1", "media_relpath": "slice.wav"},),
    )
    path = tmp_path / "formal-window-fit.json"
    fit_phase_runtime(runtime, path, window_batch=batch, **kwargs)
    output = json.loads(path.read_bytes())["output"]
    assert output["rows"][0]["speech_tokens"] == 7
    assert output["rows"][0]["required_tokens"] == 16
    assert output["rows"][0]["fit_multiple"] == 2.0
    assert client.calls == [
        ("GET", "/props"), ("POST", "/apply-template"),
        ("POST", "/tokenize"), ("POST", "/tokenize"),
    ]


def test_fit_counts_effective_rendered_query_and_historical_packets_once():
    from speech_aware_evidence_acquisition.core.preparation_fit import (
        rendered_speech_feature_descriptors,
    )

    query = {"packet_id": "query", "sha256": "a" * 64, "role": "query"}
    historical = {"packet_id": "history", "sha256": "b" * 64, "role": "key"}
    body = {
        "messages": [
            {"role": "system", "content": "Solve."},
            {
                "role": "user",
                "content": [
                    {"type": "input_speech_features", "speech_features": query},
                    {
                        "type": "text",
                        "text": "A prior paired return.",
                    },
                    {
                        "type": "input_speech_features",
                        "speech_features": historical,
                    },
                    {
                        "type": "input_speech_features",
                        "speech_features": historical,
                    },
                ],
            },
        ],
        "max_tokens": 5,
    }

    class RenderedTransport:
        def __init__(self):
            self.calls = 0

        def render_request(self, _raw):
            self.calls += 1
            return body

    class RenderedClient:
        def request_json(self, _method, path, payload):
            if path == "/apply-template":
                count = sum(
                    part.get("type") == "input_speech_features"
                    for message in payload["messages"]
                    if isinstance(message.get("content"), list)
                    for part in message["content"]
                )
                return {"prompt": "A" + "<m>B" * count}
            if path == "/tokenize":
                return {"tokens": list(payload["content"])}
            raise AssertionError(path)

    seen = []

    def speech_counts(payload):
        descriptors = payload["speech_feature_parts"]
        seen.append(tuple(descriptors))
        return tuple(2 if item["role"] == "query" else 7 for item in descriptors)

    payload = {"sample_id": "s1", "speech_feature_parts": [query]}
    transport = RenderedTransport()
    result = fit_requests(
        [payload],
        expected_sample_ids=["s1"],
        transport=transport,
        client=RenderedClient(),
        speech_counts=speech_counts,
        media_marker="<m>",
        slot_tokens=100,
    )

    assert rendered_speech_feature_descriptors(body) == (
        query,
        historical,
        historical,
    )
    assert seen == [(query, historical, historical)]
    assert result["rows"][0]["speech_tokens"] == 16
    assert result["rows"][0]["media_count"] == 3
    assert transport.calls == 1
    assert payload["speech_feature_parts"] == [query]

def test_independent_prepared_text_fit_has_zero_media_and_keeps_output_reserve(tmp_path):
    from speech_aware_evidence_acquisition.core.preparation_fit import fit_phase_runtime
    from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
    from speech_aware_evidence_acquisition.rails.prepared_text import (
        PREPARED_TEXT_INSTRUCTION, PREPARED_TEXT_SCHEMA,
    )

    runtime, _policy, _attach, client, kwargs = fit_fixture(tmp_path)
    context = runtime.preparation_context()
    context["values"]["arm"] = "prepared-context-text"
    payload = dict.fromkeys(ARM_VISIBLE_FIELDS["prepared-context-text"])
    payload.update(
        sample_id="s1", prepared_text=PREPARED_TEXT_SCHEMA,
        task_instruction=PREPARED_TEXT_INSTRUCTION,
        history=[
            {"role": "agent_state", "state_kind": "prepared-training-feedback"},
            {"role": "control"},
        ],
    )
    runtime.materialize_phase_requests = lambda: [payload]

    class TextRenderer:
        def render_request(self, raw):
            assert json.loads(raw) == payload
            return {"messages": [{"content": 0}], "max_tokens": 2048}

    kwargs["transport_factory"] = lambda *a, **k: TextRenderer()
    kwargs["speech_counter"] = lambda _payload: pytest.fail("text cannot read speech packets")
    path = tmp_path / "text-fit.json"
    fit_phase_runtime(runtime, path, **kwargs)
    result = json.loads(path.read_bytes())["output"]
    assert result["contacts"] == len(client.calls) == 3
    assert result["generation_contacts"] == 0
    row = result["rows"][0]
    assert row["media_count"] == row["speech_tokens"] == 0
    assert row["maximum_completion_tokens"] == 2048
    assert row["required_tokens"] == 2051
    assert result["every_request_fits"] is False

    payload["tool_schemas"] = []
    before = len(client.calls)
    with pytest.raises(PreparationError, match="undeclared fields"):
        fit_phase_runtime(runtime, tmp_path / "invalid-text-fit.json", **kwargs)
    assert len(client.calls) == before
