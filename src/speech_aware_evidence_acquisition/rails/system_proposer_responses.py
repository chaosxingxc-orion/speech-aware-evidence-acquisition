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
from .system_proposer_capsule import attest_outbound, HARD_BUDGET, SUBSCRIPTION_BUDGET
from .system_text_policy import PolicyError, canonical, require, sha
from .system_proposer_continuation import checked_output, checked_tool, require_limits

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
    text. No live provider is admitted by this module. The ChatGPT-plan profile
    requires owner217's metered acceptance budget and a separate provider admission.
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
            hard = (admission.get("output_cap_enforcement") == "provider-hard-limit"
                    and admission.get("provider_profile") != "chatgpt-plan-preview"
                    and admission.get("budget_profile", HARD_BUDGET) == HARD_BUDGET)
            subscription = (admission.get("provider_profile") == "chatgpt-plan-preview"
                    and admission.get("output_cap_enforcement") == "metered-reject-after-completion"
                    and admission.get("budget_profile") == SUBSCRIPTION_BUDGET
                    and admission.get("owner_decision") == 217)
            require(admission.get("status") == "admitted" and admission.get("endpoint") == endpoint
                    and admission.get("paid_api_spend") == 0
                    and (hard or subscription)
                    and callable(bearer), "transport admission is incompatible")
            sha(admission.get("protocol_sha256"))
            require(parsed.scheme == "https" and parsed.hostname == "api.openai.com" and parsed.port in (None, 443),
                    "live credential destination is not approved")
        self.endpoint, self.parsed, self.bearer = endpoint, parsed, bearer
        self.admission = copy.deepcopy(admission)
        self.timeout = timeout
        self.fixture_only = fixture_only
        self.last_response_metadata = None

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
                except Exception as error:
                    from .system_subscription_auth import CredentialFailure, safe_credential_failure
                    safe = safe_credential_failure(error)
                    raise CredentialFailure(safe["category"], transport=True) from None
                require(isinstance(token, str) and token and not any(c.isspace() for c in token), "invalid credential")
                headers["Authorization"] = "Bearer " + token
            connection.request("POST", self.parsed.path, body=canonical(request).encode("utf-8"), headers=headers)
            headers.clear()
            response = connection.getresponse()
            content_type = response.getheader("Content-Type", "").split(";")[0].strip().lower()
            self.last_response_metadata = {"status": response.status, "content_type": content_type}
            # The pinned official subscription SDK documents valid SSE without
            # Content-Type. Event parsing and completed/usage gates still apply.
            missing_allowed = (self.fixture_only or (self.admission is not None
                               and self.admission.get("provider_profile") == "chatgpt-plan-preview"))
            mime_ok = content_type == "text/event-stream" or (not content_type and missing_allowed)
            if response.status != 200 or not mime_ok:
                body = response.read(MAX_STREAM_BYTES + 1)
                if raw_sink is not None:
                    raw_sink.write(body[:MAX_STREAM_BYTES])
                    raw_sink.flush()
                require(len(body) <= MAX_STREAM_BYTES, "HTTP error body exceeds evidence bound")
                require(response.status == 200, f"HTTP request failed with status {response.status}")
                raise PolicyError("HTTP response is not SSE")
            yield from parse_sse(response, raw_sink=raw_sink)
        except (OSError, http.client.HTTPException) as error:
            # Do not copy exception bodies, account identifiers or headers to logs.
            raise PolicyError("HTTP transport interrupted; no retry permitted") from error
        finally:
            connection.close()


def completed_stream_output(response, events, *, subscription=False):
    """Reconcile whole completed items; never promote text deltas into answers."""
    require(isinstance(response, dict) and response.get("status") == "completed", "incomplete response")
    created, added, done = None, {}, {}
    for event in events:
        kind = event["type"]
        if kind == "response.created":
            require(created is None, "multiple response identities in stream")
            created = event.get("response", {}).get("id")
            require(isinstance(created, str) and created, "missing streamed response identity")
        elif kind in {"response.output_item.added", "response.output_item.done"}:
            index, item = event.get("output_index"), event.get("item")
            require(created is not None and type(index) is int and index >= 0 and isinstance(item, dict)
                    and isinstance(item.get("id"), str) and item["id"]
                    and isinstance(item.get("type"), str), "invalid streamed item identity")
            if kind.endswith(".added"):
                require(index not in added and item["id"] not in {identity[0] for identity in added.values()},
                        "duplicate streamed item")
                added[index] = (item["id"], item["type"])
            else:
                # ReasoningItem.status is optional. The whole output_item.done
                # event and final response completion establish custody; do not
                # invent a status, discard opaque state, or accept unfinished items.
                complete = (item.get("status") == "completed"
                            or (item["type"] == "reasoning" and "status" not in item))
                require(index not in done and added.get(index) == (item["id"], item["type"])
                        and complete, "streamed item is not a completed registered item")
                done[index] = item
    if created is not None:
        require(created == response.get("id"), "completion belongs to another response")
    aggregate = response.get("output")
    if done:
        require(created is not None and set(done) == set(added) == set(range(len(done))),
                "streamed item sequence is incomplete")
        output = [done[index] for index in range(len(done))]
        if aggregate:
            require(aggregate == output, "stream and aggregate outputs disagree")
        else:
            require(subscription and aggregate == [], "omitted aggregate is not admitted")
        return {**copy.deepcopy(response), "output": copy.deepcopy(output)}
    require(isinstance(aggregate, list) and aggregate and not added, "completion has no complete output")
    return copy.deepcopy(response)


def _output(response, seen_calls, *, subscription=False):
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
            allowed = {"id", "type", "call_id", "name", "arguments", "status"}
            if subscription:
                allowed.add("namespace")
                require(item.get("namespace") in (None, "artifacts"), "unregistered tool namespace")
            require(not set(item) - allowed, "extra call fields")
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
    def __init__(self, capsule, client, *, audit_dir, input_counter, before_contact, contact_cap, continuation_limits=None):
        require(callable(input_counter) and callable(before_contact), "meter and contact admission are required")
        require(type(contact_cap) is int and contact_cap > 0, "invalid contact cap")
        require_limits(continuation_limits)
        if client.admission is not None:
            require(client.admission.get("continuation_limits") == continuation_limits, "provider continuation envelope differs")
        self.continuation_limits = copy.deepcopy(continuation_limits)
        self.capsule, self.client = capsule, client
        self.audit_dir, self.contact_cap = Path(audit_dir), contact_cap
        self.input_counter, self.before_contact = input_counter, before_contact

    def __call__(self, initial):
        self.audit_dir.mkdir(parents=True, exist_ok=False)
        total_input, total_output = 0, 0
        previous_input = 0
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
                require(self.client.admission.get("budget_profile", HARD_BUDGET)
                        == packet.get("budget_profile", HARD_BUDGET), "provider and proposal budget profiles differ")
            history = copy.deepcopy(expected["input"])
            for number in range(1, self.contact_cap + 1):
                remaining = packet["output_token_cap"] - total_output
                require(remaining > 0, "proposal output budget exhausted")
                contract = self.capsule.request(remaining_output=remaining,
                    remaining_input=packet["input_token_cap"] - total_input, history=history,
                    remaining_contacts=self.contact_cap - number + 1, previous_input_tokens=previous_input)
                request = copy.deepcopy(contract)
                counted = self.input_counter(copy.deepcopy(request))
                require(type(counted) is int and counted >= 0
                        and total_input + counted <= packet["input_token_cap"], "proposal input budget exhausted or unknown")
                contact = self.audit_dir / f"contact-{number:03d}"
                contact.mkdir()
                evidence = {**attest_outbound(request, {**contract, "input": history}),
                    "contact": number, "input_token_bound": counted, "remaining_output_tokens": remaining,
                    "session_id": packet["session_id"], "proposal_input_sha256": packet["input_sha256"],
                    "budget_profile": packet.get("budget_profile", HARD_BUDGET),
                    "provider_hard_output_cap": packet.get("budget_profile", HARD_BUDGET) == HARD_BUDGET}
                write(contact / "request.json", request)
                write(contact / "reservation.json", evidence)
                self.before_contact(copy.deepcopy(evidence))
                attempted += 1
                final = None
                custody_events = []
                with (contact / "response.sse").open("xb") as raw_stream:
                    iterator = self.client.events(copy.deepcopy(request), raw_sink=raw_stream)
                    try:
                        with (contact / "events.jsonl").open("x", encoding="utf-8") as events:
                            for event in iterator:
                                # Save exact parsed event content before inspecting results.
                                events.write(canonical(event) + "\n")
                                events.flush()
                                if event["type"] in {"response.created", "response.output_item.added", "response.output_item.done"}:
                                    custody_events.append(event)
                                require(event["type"] not in {"error", "response.failed", "response.incomplete"},
                                        "provider failed or incomplete; no retry permitted")
                                if event["type"] == "response.completed":
                                    final = event.get("response")
                                    break
                    finally:
                        iterator.close()
                        if self.client.last_response_metadata is not None:
                            write(contact / "http-response.json", self.client.last_response_metadata)
                require(isinstance(final, dict), "stream ended without completion")
                require(final.get("status") == "completed" and final.get("model") == packet["model_version"],
                        "completion status or model differs")
                usage = final.get("usage")
                require(isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0
                        for k in ("input_tokens", "output_tokens")), "provider token metering unavailable")
                total_input += usage["input_tokens"]
                previous_input = usage["input_tokens"]
                total_output += usage["output_tokens"]
                metered += 1
                write(contact / "usage.json", {"reported": usage, "cumulative_input_tokens": total_input,
                                               "cumulative_output_tokens": total_output})
                require(usage["input_tokens"] <= counted and total_input <= packet["input_token_cap"]
                        and usage["output_tokens"] <= remaining, "provider exceeded the registered token bound")
                final = completed_stream_output(final, custody_events,
                    subscription=packet.get("budget_profile") == SUBSCRIPTION_BUDGET)
                calls, text = _output(final, seen_calls, subscription=packet.get("budget_profile") == SUBSCRIPTION_BUDGET)
                if not calls:
                    require(bool(text.strip()), "completion has no proposal text")
                    result = {"raw_response": text, "model_version": packet["model_version"],
                              "input_tokens": total_input, "output_tokens": total_output}
                    write(self.audit_dir / "outcome.json", {"status": "received", "contacts": number,
                        "input_tokens": total_input, "output_tokens": total_output, "activation": "none"})
                    return result
                require(number < self.contact_cap, "proposal contact budget exhausted")
                checked_output(final["output"], self.continuation_limits)
                tool = calls[0]
                arguments = strict_json(tool["arguments"])
                supplied = self.capsule.read_artifact(arguments)
                tool_item = checked_tool(supplied, tool["call_id"], self.continuation_limits)
                history.extend(copy.deepcopy(final["output"]))
                history.append(tool_item)
        except Exception as error:
            outcome = {"status": "failed", "error_type": type(error).__name__,
                "failure_reason": str(error) if isinstance(error, PolicyError) else None,
                "observed_input_tokens": total_input, "observed_output_tokens": total_output,
                "attempted_contacts": attempted, "unmetered_contacts": attempted - metered,
                "usage_complete": attempted == metered, "activation": "none", "retry_permitted": False}
            from .system_subscription_auth import CredentialFailure, safe_credential_failure
            if type(error) is CredentialFailure:
                outcome["credential_failure"] = safe_credential_failure(error)
            write(self.audit_dir / "outcome.json", outcome)
            raise
