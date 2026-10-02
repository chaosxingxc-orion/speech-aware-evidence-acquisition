"""Local HTTP/SSE tests: no account, remote model, or experiment contact."""
import copy
import http.server
import io
import json
import threading
from contextlib import contextmanager

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule, ProposalDispatch
from speech_aware_evidence_acquisition.rails.system_proposer_responses import (
    ResponsesHTTP, ResponsesProposer, parse_sse,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_proposer_capsule import fixture


def completed(output=None, **changes):
    response = {"id": "resp_fixture", "model": "gpt-6-sol", "status": "completed",
        "output": output if output is not None else [{"type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": '{"changes":{}}'}]}],
        "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}}
    response.update(changes)
    return {"type": "response.completed", "response": response}


def call(identity, **changes):
    value = {"type": "function_call", "call_id": "call_fixture", "name": "read_artifact",
             "arguments": json.dumps({"artifact_id": identity, "offset": 0, "limit": 16384})}
    value.update(changes)
    return value


def sse(records):
    return b"".join(("event: " + r["type"] + "\ndata: " + json.dumps(r) + "\n\n").encode() for r in records)


@contextmanager
def server(replies):
    requests = []
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            requests.append({"body": json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
                             "authorization": self.headers.get("Authorization"), "path": self.path})
            status, headers, body = replies[len(requests) - 1]
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    instance = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{instance.server_port}/v1/responses", requests
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join()


def setup(tmp_path, endpoint, **options):
    packet, roots = fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    admission = []
    transport = ResponsesProposer(capsule, ResponsesHTTP(endpoint, fixture_only=True),
        audit_dir=tmp_path / "transport", input_counter=lambda request: 100,
        before_contact=lambda receipt: admission.append(receipt), contact_cap=2, **options)
    return capsule, transport, admission


def reply(*records):
    return 200, {"Content-Type": "text/event-stream"}, sse(records)


def test_direct_route_without_content_type_still_requires_sse_completion():
    with server([(200, {}, sse([completed()]))]) as (endpoint, _):
        client = ResponsesHTTP(endpoint, fixture_only=True)
        assert list(client.events({"model": "gpt-6-sol"}))[0]["type"] == "response.completed"
        assert client.last_response_metadata == {"status": 200, "content_type": ""}


def test_invalid_mime_retains_bounded_body_and_metadata():
    raw = io.BytesIO()
    with server([(200, {"Content-Type": "text/html"}, b"synthetic proxy response")]) as (endpoint, _):
        client = ResponsesHTTP(endpoint, fixture_only=True)
        with pytest.raises(PolicyError, match="not SSE"):
            list(client.events({"model": "gpt-6-sol"}, raw_sink=raw))
        assert client.last_response_metadata == {"status": 200, "content_type": "text/html"}
    assert raw.getvalue() == b"synthetic proxy response"


def test_full_local_http_broker_continuation_and_dispatch(tmp_path):
    # The whole path uses the production transport and an actual loopback socket.
    capsule, transport, admission = setup(tmp_path, "http://127.0.0.1:1/v1/responses")
    identity = capsule.initial_input()["artifacts"][0]["artifact_id"]
    first = completed([call(identity)])
    replies = [reply(first), reply(completed())]
    with server(replies) as (endpoint, requests):
        transport.client = ResponsesHTTP(endpoint, fixture_only=True)
        result = ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert result["raw_response"] == '{"changes":{}}'
    assert result["input_tokens"] == 200 and result["output_tokens"] == 20
    assert len(admission) == len(requests) == 2
    assert requests[0]["body"] == capsule.request()
    assert requests[1]["body"]["max_output_tokens"] == 4086
    assert requests[1]["body"]["input"][1] == first["response"]["output"][0]
    supplied = requests[1]["body"]["input"][2]
    assert supplied["type"] == "function_call_output"
    assert json.loads(supplied["output"])["eof"] is True
    assert all(r["authorization"] is None for r in requests)
    (tmp_path / "wire-requests.json").write_text(json.dumps(requests, sort_keys=True) + "\n")
    (tmp_path / "admitted-contacts.json").write_text(json.dumps(admission, sort_keys=True) + "\n")
    assert all(p.exists() for p in (tmp_path / "transport" / f"contact-{i:03d}" / "events.jsonl" for i in (1, 2)))
    assert (tmp_path / "transport/contact-001/response.sse").read_bytes() == sse([first])
    assert capsule.access_log[0]["status"] == "supplied"
    with pytest.raises(PolicyError, match="consumed"):
        ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)


@pytest.mark.parametrize("item", [
    call("unused", name="shell", arguments='{"cmd":"read private data"}'),
    {"type": "additional_tools", "tools": [{"name": "shell"}]},
    {"type": "message", "role": "system", "content": []},
    {"type": "message", "role": "assistant", "content": [{"type": "refusal", "refusal": "No."}]},
    call("not-registered"),
    call("unused", arguments='{"artifact_id":"a","artifact_id":"b","offset":0,"limit":10}'),
])
def test_unknown_tools_context_and_denied_reads_never_continue(tmp_path, item):
    with server([reply(completed([item]))]) as (endpoint, requests):
        capsule, transport, _ = setup(tmp_path, endpoint)
        with pytest.raises(PolicyError):
            ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert len(requests) == 1
    assert json.loads((tmp_path / "dispatch/B-1-1/outcome.json").read_text())["status"] == "failed"
    assert (tmp_path / "transport/contact-001/events.jsonl").exists()


@pytest.mark.parametrize("changes", [
    {"model": "another-model"}, {"status": "incomplete"}, {"usage": None},
    {"usage": {"input_tokens": True, "output_tokens": 1}},
    {"usage": {"input_tokens": 101, "output_tokens": 1}},
    {"usage": {"input_tokens": 100, "output_tokens": 4097}},
    {"output": []},
])
def test_bad_completion_preserved_and_not_retried(tmp_path, changes):
    with server([reply(completed(**changes))]) as (endpoint, requests):
        capsule, transport, _ = setup(tmp_path, endpoint)
        with pytest.raises(PolicyError):
            ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert len(requests) == 1
    assert json.loads((tmp_path / "transport/outcome.json").read_text())["status"] == "failed"


def test_input_budget_stops_before_any_socket_or_admission(tmp_path):
    with server([]) as (endpoint, requests):
        capsule, transport, admission = setup(tmp_path, endpoint)
        transport.input_counter = lambda _request: 32769
        with pytest.raises(PolicyError, match="input"):
            ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert requests == admission == []


def test_modified_initial_contract_is_refused_before_socket(tmp_path):
    with server([]) as (endpoint, requests):
        capsule, transport, _ = setup(tmp_path, endpoint)
        request = capsule.request()
        request["input"].append({"role": "developer", "content": "Unregistered context."})
        with pytest.raises(PolicyError, match="outbound"):
            transport(request)
    assert requests == []


def test_contact_limit_never_creates_a_third_request(tmp_path):
    with server([]) as (endpoint, _):
        capsule, transport, _ = setup(tmp_path, endpoint)
    identity = capsule.initial_input()["artifacts"][0]["artifact_id"]
    with server([reply(completed([call(identity)])), reply(completed([call(identity, call_id="call_second")]))]) as (endpoint, requests):
        transport.client = ResponsesHTTP(endpoint, fixture_only=True)
        with pytest.raises(PolicyError, match="contact"):
            ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert len(requests) == 2


@pytest.mark.parametrize("status", [302, 307, 401, 429, 500])
def test_no_redirect_auth_retry_or_transient_retry(tmp_path, status):
    with server([(status, {"Location": "http://127.0.0.1:1/secret"}, b"private error body")]) as (endpoint, requests):
        capsule, transport, _ = setup(tmp_path, endpoint)
        with pytest.raises(PolicyError, match="HTTP"):
            ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert len(requests) == 1
    assert "private error body" not in (tmp_path / "transport/outcome.json").read_text()


@pytest.mark.parametrize("url", ["http://localhost/v1/responses", "http://127.0.0.1.evil/v1/responses",
    "http://user:password@127.0.0.1/v1/responses", "file:///tmp/data", "https://api.openai.com/v1/responses"])
def test_fixture_mode_refuses_nonliteral_loopback_or_credentials(url):
    with pytest.raises(PolicyError):
        ResponsesHTTP(url, fixture_only=True)


def test_live_mode_requires_separate_pinned_admission_not_a_token(tmp_path):
    with pytest.raises(PolicyError, match="admission"):
        ResponsesHTTP("https://api.openai.com/v1/responses", bearer=lambda: "never-read")


def test_sse_multiline_comments_and_crlf():
    raw = b': ping\r\nevent: example\r\ndata: {"type":\r\ndata: "example"}\r\n\r\n'
    assert list(parse_sse(io.BytesIO(raw))) == [{"type": "example"}]


@pytest.mark.parametrize("raw", [b'data: {"type":"a","type":"b"}\n\n', b'data: {}',
    b'data: [DONE]\n\n', b'data: {"value":NaN}\n\n', b'data: {invalid}\n\n'])
def test_malformed_or_truncated_sse_is_rejected(raw):
    with pytest.raises(PolicyError):
        list(parse_sse(io.BytesIO(raw)))


def test_truncated_stream_keeps_partial_events_without_retry(tmp_path):
    with server([reply({"type": "response.created", "response": {"id": "partial"}})]) as (endpoint, requests):
        capsule, transport, _ = setup(tmp_path, endpoint)
        with pytest.raises(PolicyError, match="completion"):
            ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert len(requests) == 1
    assert "partial" in (tmp_path / "transport/contact-001/events.jsonl").read_text()
    outcome = json.loads((tmp_path / "transport/outcome.json").read_text())
    assert outcome["unmetered_contacts"] == 1
    assert outcome["usage_complete"] is False


def live_admission():
    value = {"status": "admitted", "endpoint": "https://api.openai.com/v1/responses",
        "paid_api_spend": 0, "output_cap_enforcement": "provider-hard-limit",
        "provider_profile": "synthetic-test-only", "protocol_sha256": "a" * 64,
        "model_version": "gpt-6-sol"}
    return {**value, "sha256": content_hash(value)}


def test_https_credentials_never_enter_payload_or_evidence(monkeypatch, tmp_path):
    from speech_aware_evidence_acquisition.rails import system_proposer_responses as module
    captured = []
    class Connection:
        def __init__(self, host, port, timeout):
            assert host == "api.openai.com" and port is None
        def request(self, method, path, body, headers):
            captured.append((method, path, json.loads(body), copy.deepcopy(headers)))
        def getresponse(self):
            response = io.BytesIO(sse([completed()]))
            response.status = 200
            response.getheader = lambda *_args: "text/event-stream"
            return response
        def close(self):
            pass
    monkeypatch.setattr(module.http.client, "HTTPSConnection", Connection)
    client = ResponsesHTTP("https://api.openai.com/v1/responses", admission=live_admission(), bearer=lambda: "synthetic-secret")
    assert list(client.events({"model": "gpt-6-sol"}))[0] == completed()
    assert captured[0][3]["Authorization"] == "Bearer synthetic-secret"
    assert "synthetic-secret" not in json.dumps(captured[0][2])
    with pytest.raises(PolicyError, match="model"):
        list(client.events({"model": "changed"}))
    assert len(captured) == 1


def test_plan_without_hard_cap_is_refused_before_credentials():
    value = live_admission()
    value["provider_profile"] = "chatgpt-plan-preview"
    value["sha256"] = content_hash({k: v for k, v in value.items() if k != "sha256"})
    with pytest.raises(PolicyError, match="incompatible"):
        ResponsesHTTP(value["endpoint"], admission=value, bearer=lambda: pytest.fail("credential must not be read"))


def test_admission_refusal_keeps_request_but_opens_no_socket(tmp_path):
    with server([]) as (endpoint, requests):
        capsule, transport, _ = setup(tmp_path, endpoint)
        def deny(_receipt):
            raise PolicyError("registration refused")
        transport.before_contact = deny
        with pytest.raises(PolicyError, match="registration"):
            ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert requests == []
    assert (tmp_path / "transport/contact-001/request.json").exists()
    outcome = json.loads((tmp_path / "transport/outcome.json").read_text())
    assert outcome["attempted_contacts"] == 0


def test_malformed_stream_raw_bytes_are_preserved(tmp_path):
    raw = b'data: {"malformed":\xff}\n\n'
    with server([(200, {"Content-Type": "text/event-stream"}, raw)]) as (endpoint, requests):
        capsule, transport, _ = setup(tmp_path, endpoint)
        with pytest.raises(PolicyError):
            ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert len(requests) == 1
    observed = (tmp_path / "transport/contact-001/response.sse").read_bytes()
    # Preserve every received byte; do not drain an invalid/unbounded peer.
    assert observed == raw.splitlines(keepends=True)[0]


def test_completed_reasoning_is_preserved_for_tool_continuation(tmp_path):
    with server([]) as (endpoint, _):
        capsule, transport, _ = setup(tmp_path, endpoint)
    identity = capsule.initial_input()["artifacts"][0]["artifact_id"]
    reasoning = {"type": "reasoning", "summary": [{"type": "summary_text", "text": "Read registered material."}]}
    with server([reply(completed([reasoning, call(identity)])), reply(completed())]) as (endpoint, requests):
        transport.client = ResponsesHTTP(endpoint, fixture_only=True)
        ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert requests[1]["body"]["input"][1] == reasoning


def test_transport_interruption_does_not_erase_already_metered_usage(tmp_path):
    with server([]) as (endpoint, _):
        capsule, transport, _ = setup(tmp_path, endpoint)
    identity = capsule.initial_input()["artifacts"][0]["artifact_id"]
    with server([reply(completed([call(identity)])), reply({"type": "response.created"})]) as (endpoint, requests):
        transport.client = ResponsesHTTP(endpoint, fixture_only=True)
        with pytest.raises(PolicyError):
            ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    outcome = json.loads((tmp_path / "transport/outcome.json").read_text())
    assert outcome["observed_input_tokens"] == 100 and outcome["observed_output_tokens"] == 10
    assert outcome["attempted_contacts"] == 2 and outcome["unmetered_contacts"] == 1


def test_credential_failure_is_sanitized(monkeypatch):
    def fail():
        raise RuntimeError("synthetic-private-token")
    client = ResponsesHTTP("https://api.openai.com/v1/responses", admission=live_admission(), bearer=fail)
    with pytest.raises(PolicyError, match="credential") as caught:
        list(client.events({"model": "gpt-6-sol"}))
    assert caught.value.__suppress_context__ is True
    assert "synthetic-private-token" not in str(caught.value)


def test_connection_reset_is_not_retried(monkeypatch, tmp_path):
    from speech_aware_evidence_acquisition.rails import system_proposer_responses as module
    calls = []
    class Broken:
        def __init__(self, *_args, **_kwargs):
            pass
        def request(self, *_args, **_kwargs):
            calls.append(1)
            raise ConnectionResetError("synthetic error")
        def close(self):
            pass
    monkeypatch.setattr(module.http.client, "HTTPConnection", Broken)
    capsule, transport, _ = setup(tmp_path, "http://127.0.0.1:1/v1/responses")
    with pytest.raises(PolicyError, match="interrupted"):
        ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert calls == [1]


def test_provider_receipt_is_bound_to_proposal_protocol(tmp_path):
    capsule, transport, _ = setup(tmp_path, "http://127.0.0.1:1/v1/responses")
    transport.client = ResponsesHTTP("https://api.openai.com/v1/responses", admission=live_admission(),
        bearer=lambda: pytest.fail("credential must not be requested"))
    with pytest.raises(PolicyError, match="protocols"):
        ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
