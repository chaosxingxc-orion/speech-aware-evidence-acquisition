"""Exact-context Responses transport for the existing system-text proposer.

This is not a second experiment runtime or an answering model. The operator must
admit a provider, tokenizer and contact plan separately before live use. No account
discovery, credential copying, paid API default, retry or experiment dispatch is
provided here. A loopback-only fixture exercises the same HTTP and broker path.
"""
from __future__ import annotations

import copy
import http.client
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit

from .hashing import content_hash
from .prepared_feedback import reject_non_latin_scripts
from .system_proposer_capsule import attest_outbound
from .system_text_policy import PolicyError, canonical, require, sha

MAX_STREAM_BYTES = 8 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON field")
            result[key] = value
        return result

    def constant(_value):
        raise PolicyError("non-finite JSON value")

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError) as error:
        raise PolicyError("malformed protocol JSON") from error


def parse_sse(stream, *, timeout=300, raw_sink=None):
    """Read bounded SSE records without treating deltas as a completed response."""
    data, total, deadline = [], 0, time.monotonic() + timeout
    while True:
        require(time.monotonic() < deadline, "stream deadline exceeded")
        raw = stream.readline(MAX_LINE_BYTES + 1)
        if raw_sink is not None:
            raw_sink.write(raw)
            raw_sink.flush()
        if not raw:
            require(not data, "truncated SSE record")
            return
        total += len(raw)
        require(len(raw) <= MAX_LINE_BYTES and total <= MAX_STREAM_BYTES, "stream size limit exceeded")
        try:
            line = raw.decode("utf-8").rstrip("\r\n")
        except UnicodeError as error:
            raise PolicyError("non-UTF8 stream") from error
        if not line and data:
            value = strict_json("\n".join(data))
            require(isinstance(value, dict) and isinstance(value.get("type"), str), "invalid SSE event")
            data = []
            yield value
        elif line.startswith("data:"):
            data.append(line[5:].removeprefix(" "))


class ResponsesHTTP:
    """One HTTP POST, no redirects/proxies/retries, and no credential persistence.

    Live admissions are caller-verified, hash-pinned research records, not model
    text. No live provider is admitted by this module. In particular the current
    ChatGPT-plan profile does not support max_output_tokens and is refused.
    """
    def __init__(self, endpoint, *, fixture_only=False, bearer=None, admission=None, timeout=60):
        parsed = urlsplit(endpoint)
        require(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
                "endpoint cannot carry credentials, queries or fragments")
        require(parsed.path == "/v1/responses", "endpoint path differs")
        require(type(timeout) in (int, float) and 0 < timeout <= 300, "invalid HTTP timeout")
        if fixture_only:
            require(parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and bearer is None,
                    "fixture requires literal unauthenticated loopback")
            require(admission is None, "fixture cannot carry live admission")
        else:
            require(isinstance(admission, dict), "live transport requires separately verified admission")
            require(admission.get("sha256") == content_hash({k: v for k, v in admission.items() if k != "sha256"}),
                    "transport admission fingerprint differs")
            require(admission.get("status") == "admitted" and admission.get("endpoint") == endpoint
                    and admission.get("paid_api_spend") == 0
                    and admission.get("output_cap_enforcement") == "provider-hard-limit"
                    and admission.get("provider_profile") != "chatgpt-plan-preview"
                    and callable(bearer), "transport admission is incompatible")
            sha(admission.get("protocol_sha256"))
            require(parsed.scheme == "https" and parsed.hostname == "api.openai.com" and parsed.port in (None, 443),
                    "live credential destination is not approved")
        self.endpoint, self.parsed, self.bearer = endpoint, parsed, bearer
        self.admission = copy.deepcopy(admission)
        self.timeout = timeout

    def events(self, request, *, raw_sink=None):
        if self.admission is not None:
            require(request["model"] == self.admission.get("model_version"), "admitted model differs")
        connection_type = http.client.HTTPSConnection if self.parsed.scheme == "https" else http.client.HTTPConnection
        connection = connection_type(self.parsed.hostname, self.parsed.port, timeout=self.timeout)
        try:
            headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
            if self.bearer is not None:
                try:
                    token = self.bearer()
                except Exception:
                    raise PolicyError("registered credential unavailable") from None
                require(isinstance(token, str) and token and not any(c.isspace() for c in token), "invalid credential")
                headers["Authorization"] = "Bearer " + token
            connection.request("POST", self.parsed.path, body=canonical(request).encode("utf-8"), headers=headers)
            headers.clear()
            response = connection.getresponse()
            require(response.status == 200, f"HTTP request failed with status {response.status}")
            require(response.getheader("Content-Type", "").split(";")[0].strip() == "text/event-stream",
                    "HTTP response is not SSE")
            yield from parse_sse(response, raw_sink=raw_sink)
        except (OSError, http.client.HTTPException) as error:
            # Do not copy exception bodies, account identifiers or headers to logs.
            raise PolicyError("HTTP transport interrupted; no retry permitted") from error
        finally:
            connection.close()


def _output(response, seen_calls):
    """Validate model-owned continuation items; never accept new tool declarations."""
    output = response.get("output")
    require(isinstance(output, list) and output, "completion has no output")
    reject_non_latin_scripts(output)
    calls, texts = [], []
    for item in output:
        require(isinstance(item, dict), "invalid output item")
        require(item.get("status") in (None, "completed"), "unfinished output item")
        kind = item.get("type")
        if kind == "function_call":
            require(not set(item) - {"id", "type", "call_id", "name", "arguments", "status"}, "extra call fields")
            require(item.get("name") == "read_artifact", "unregistered tool request")
            identity = item.get("call_id")
            require(isinstance(identity, str) and identity and identity not in seen_calls, "duplicate or empty tool call")
            require(isinstance(item.get("arguments"), str), "tool arguments must be JSON text")
            seen_calls.add(identity)
            calls.append(item)
        elif kind == "message":
            require(not set(item) - {"id", "type", "role", "status", "content", "phase"}
                    and item.get("role") == "assistant", "unregistered message role or fields")
            require(isinstance(item.get("content"), list), "invalid message content")
            for part in item["content"]:
                require(isinstance(part, dict) and part.get("type") == "output_text"
                        and isinstance(part.get("text"), str)
                        and not set(part) - {"type", "text", "annotations", "logprobs"}, "refusal or unsupported message content")
                texts.append(part["text"])
        elif kind == "reasoning":
            require(not set(item) - {"id", "type", "summary", "content", "encrypted_content", "status"},
                    "unregistered reasoning fields")
        else:
            raise PolicyError("unregistered continuation item")
    require(len(calls) <= 1, "parallel tool calls are not registered")
    return calls, "".join(texts)


class ResponsesProposer:
    """Bounded whole-proposal loop used inside ProposalDispatch's one-shot custody.

    input_counter must be an admitted model-free exact or conservative full-request meter;
    its count is checked against actual provider usage. before_contact must verify
    the registration and durably charge the contact BEFORE the socket is opened.
    Neither callback has a permissive default. Request count is a separate cap
    from proposal opportunities, and cumulative token usage includes tool turns.
    """
    def __init__(self, capsule, client, *, audit_dir, input_counter, before_contact, contact_cap):
        require(callable(input_counter) and callable(before_contact), "meter and contact admission are required")
        require(type(contact_cap) is int and contact_cap > 0, "invalid contact cap")
        self.capsule, self.client = capsule, client
        self.audit_dir, self.contact_cap = Path(audit_dir), contact_cap
        self.input_counter, self.before_contact = input_counter, before_contact

    def __call__(self, initial):
        self.audit_dir.mkdir(parents=True, exist_ok=False)
        total_input, total_output = 0, 0
        attempted, metered = 0, 0
        seen_calls = set()

        def write(path, value):
            with path.open("x", encoding="utf-8") as stream:
                stream.write(canonical(value) + "\n")
                stream.flush()
                os.fsync(stream.fileno())

        try:
            packet = self.capsule.as_json()["packet"]
            expected = self.capsule.request()
            attest_outbound(initial, expected)
            if self.client.admission is not None:
                require(self.client.admission["protocol_sha256"] == packet.get("protocol_sha256"),
                        "provider and proposal protocols differ")
            history = copy.deepcopy(expected["input"])
            for number in range(1, self.contact_cap + 1):
                remaining = packet["output_token_cap"] - total_output
                require(remaining > 0, "proposal output budget exhausted")
                request = {**copy.deepcopy(expected), "input": copy.deepcopy(history), "max_output_tokens": remaining}
                counted = self.input_counter(copy.deepcopy(request))
                require(type(counted) is int and counted >= 0
                        and total_input + counted <= packet["input_token_cap"], "proposal input budget exhausted or unknown")
                contact = self.audit_dir / f"contact-{number:03d}"
                contact.mkdir()
                evidence = {**attest_outbound(request, {**expected, "input": history, "max_output_tokens": remaining}),
                    "contact": number, "input_token_bound": counted, "remaining_output_tokens": remaining,
                    "session_id": packet["session_id"], "proposal_input_sha256": packet["input_sha256"]}
                write(contact / "request.json", request)
                write(contact / "reservation.json", evidence)
                self.before_contact(copy.deepcopy(evidence))
                attempted += 1
                final = None
                with (contact / "response.sse").open("xb") as raw_stream:
                    iterator = self.client.events(copy.deepcopy(request), raw_sink=raw_stream)
                    try:
                        with (contact / "events.jsonl").open("x", encoding="utf-8") as events:
                            for event in iterator:
                                # Save exact parsed event content before inspecting results.
                                events.write(canonical(event) + "\n")
                                events.flush()
                                require(event["type"] not in {"error", "response.failed", "response.incomplete"},
                                        "provider failed or incomplete; no retry permitted")
                                if event["type"] == "response.completed":
                                    final = event.get("response")
                                    break
                    finally:
                        iterator.close()
                require(isinstance(final, dict), "stream ended without completion")
                require(final.get("status") == "completed" and final.get("model") == packet["model_version"],
                        "completion status or model differs")
                usage = final.get("usage")
                require(isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0
                        for k in ("input_tokens", "output_tokens")), "provider token metering unavailable")
                total_input += usage["input_tokens"]
                total_output += usage["output_tokens"]
                metered += 1
                write(contact / "usage.json", {"reported": usage, "cumulative_input_tokens": total_input,
                                               "cumulative_output_tokens": total_output})
                require(usage["input_tokens"] <= counted and total_input <= packet["input_token_cap"]
                        and usage["output_tokens"] <= remaining, "provider exceeded the registered token bound")
                calls, text = _output(final, seen_calls)
                if not calls:
                    require(bool(text.strip()), "completion has no proposal text")
                    result = {"raw_response": text, "model_version": packet["model_version"],
                              "input_tokens": total_input, "output_tokens": total_output}
                    write(self.audit_dir / "outcome.json", {"status": "received", "contacts": number,
                        "input_tokens": total_input, "output_tokens": total_output, "activation": "none"})
                    return result
                require(number < self.contact_cap, "proposal contact budget exhausted")
                tool = calls[0]
                arguments = strict_json(tool["arguments"])
                supplied = self.capsule.read_artifact(arguments)
                history.extend(copy.deepcopy(final["output"]))
                history.append({"type": "function_call_output", "call_id": tool["call_id"], "output": canonical(supplied)})
        except Exception as error:
            write(self.audit_dir / "outcome.json", {"status": "failed", "error_type": type(error).__name__,
                "observed_input_tokens": total_input, "observed_output_tokens": total_output,
                "attempted_contacts": attempted, "unmetered_contacts": attempted - metered,
                "usage_complete": attempted == metered, "activation": "none", "retry_permitted": False})
            raise
