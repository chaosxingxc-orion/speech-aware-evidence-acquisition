"""``MODEL_LOGPROBS``: the decode-confidence trace record, and the byte
identity of every run that never asks for one.

2026-09-08 logprob-as-judge probe. The transport already forwarded a server
``choices[0].logprobs`` object into its envelope (2026-08-13 obs-replay-loop
policy) and ``CoreResponse.logprobs`` already carried it, but nothing ever
WROTE it down: MF-8 measured the consequence directly -- the string ``logprob``
occurs zero times in the sealed SLURP comparator's 540 KB outputs file and zero
times in its 10 MB trace, so the distribution the core computed for every one
of those 1,000 contacts is gone and can only be recovered by re-flying.

Two properties are under test here, and the second is the load-bearing one:

1. a request that DOES declare ``decoding_params.logprobs`` lands the raw
   object in its own hashed ``MODEL_LOGPROBS`` record, re-verifiable from its
   own bytes;
2. a request that does NOT declare it produces a trace file that is byte-
   identical to the one the same request produced before this record existed --
   no empty record, no extra key, no changed hash.
"""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, TraceRecord
from speech_aware_evidence_acquisition.contracts.errors import TraceContractError
from speech_aware_evidence_acquisition.core.base import PayloadBindingContext
from speech_aware_evidence_acquisition.core.model import (
    MAX_TOP_LOGPROBS,
    FrozenCoreAdapter,
    FrozenCoreError,
)
from speech_aware_evidence_acquisition.core.tracing import TraceSink
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS

_ARM = "bare-core"


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        return None


def _plan(**overrides):
    values = dict(
        run_id="SAEA-E-000-logprobs",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings22-original",
        split_role="dev",
        split_identity_hash="a" * 64,
        planned_model_calls=4,
        planned_gpu_hours=0.5,
        planned_speech_audio_seconds=1000,
        protocol_hash="b" * 64,
        attempt_id="attempt-0001",
    )
    values.update(overrides)
    return ExecutionPlan(**values)


def _binding(tmp_path):
    data_root = tmp_path / "data"
    relpath = "datasets/earnings21-22/earnings22/media/5000001.mp3"
    media = data_root / relpath
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake-mp3-bytes")
    return PayloadBindingContext(
        carrier_lock_key="earnings22-original",
        allowed_sample_ids=frozenset({"5000001"}),
        sample_facts={"5000001": (100.0, 16000)},
        data_root=data_root,
        carrier_root=data_root / "datasets" / "earnings21-22" / "earnings22",
    )


def _payload(**overrides):
    payload = {
        "request_id": "req-1",
        "carrier_lock_key": "earnings22-original",
        "sample_id": "5000001",
        "speech_ref": "earnings22-original/5000001",
        "media_relpath": "datasets/earnings21-22/earnings22/media/5000001.mp3",
        "audio_seconds": 100.0,
        "sample_rate_hz": 16000,
        "task_instruction": "Transcribe the speech verbatim.",
        "history": [],
        "decoding_params": {"temperature": 0, "seed": 20260803},
    }
    assert set(payload) == set(ARM_VISIBLE_FIELDS[_ARM])
    payload.update(overrides)
    return payload


def _server_logprobs(k=5):
    """The pinned build's own chat-endpoint shape (llama.cpp 04ccc72a,
    ``tools/server/server-task.cpp:456-460`` and ``:306-325``)."""

    def entry(token, logprob, alternatives):
        return {
            "id": 1000 + len(token),
            "token": token,
            "bytes": list(token.encode("utf-8")),
            "logprob": logprob,
            "top_logprobs": alternatives,
        }

    def alt(token, logprob):
        return {
            "id": 2000 + len(token),
            "token": token,
            "bytes": list(token.encode("utf-8")),
            "logprob": logprob,
        }

    return {
        "content": [
            entry(
                "hello",
                -0.05,
                [alt("hello", -0.05)] + [alt(f"a{i}", -4.0 - i) for i in range(1, k)],
            ),
            entry(
                " world",
                -1.75,
                [alt(" world", -1.75)] + [alt(f"b{i}", -2.0 - i) for i in range(1, k)],
            ),
        ]
    }


def _transport(*, logprobs=None, wire_response=None):
    def transport(request_bytes):
        assert isinstance(request_bytes, bytes)
        envelope = (
            {}
            if wire_response is not None and "wire_response_error" in wire_response
            else {
                "text": "hello world",
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            }
        )
        if logprobs is not None:
            envelope["logprobs"] = logprobs
        if wire_response is not None:
            envelope.update(wire_response)
        return json.dumps(envelope).encode()

    return transport


def _adapter(tmp_path, *, run_dir, logprobs=None, wire_response=None, plan=None):
    sink = TraceSink(tmp_path / run_dir, "SAEA-E-000-logprobs")
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=plan or _plan(),
        arm=_ARM,
        transport=_transport(logprobs=logprobs, wire_response=wire_response),
        sink=sink,
        binding=_binding(tmp_path),
    )
    return adapter, sink


def _trace_records(tmp_path, run_dir):
    path = tmp_path / run_dir / "SAEA-E-000-logprobs.trace.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# ---------------------------------------------------------------------------
# The record itself
# ---------------------------------------------------------------------------


def test_a_logprobs_response_lands_its_own_hashed_record(tmp_path):
    served = _server_logprobs(k=5)
    adapter, sink = _adapter(tmp_path, run_dir="with", logprobs=served)
    response = adapter.request(
        _payload(
            decoding_params={
                "temperature": 0,
                "seed": 20260803,
                "logprobs": True,
                "top_logprobs": 5,
            }
        )
    )

    assert response.logprobs == served
    records = {record["record_id"]: record for record in _trace_records(tmp_path, "with")}
    assert "req-1/logprobs" in records
    record = records["req-1/logprobs"]
    assert record["channel"] == "MODEL_LOGPROBS"
    payload = record["payload"]
    # Verbatim: the reader gets the server's own object, tokens, alternatives
    # and per-alternative logprobs included -- never a summary statistic the
    # adapter chose.
    assert payload["logprobs"] == served
    assert payload["requested_top_logprobs"] == 5
    expected = hashlib.sha256(
        json.dumps(
            served, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    assert payload["logprobs_sha256"] == expected
    # The record is manifested and hashed exactly like every other record.
    assert sink.manifest()["req-1/logprobs"] == TraceRecord(
        channel="MODEL_LOGPROBS", record_id="req-1/logprobs", payload=payload
    ).content_hash()


def test_the_record_records_a_missing_k_as_absent_rather_than_the_server_default(
    tmp_path,
):
    """``logprobs: true`` with no ``top_logprobs`` makes the server apply its
    own default of 20 (``server-common.cpp:1529``). The record must not claim a
    number the request never sent."""

    adapter, _ = _adapter(tmp_path, run_dir="nok", logprobs=_server_logprobs(k=2))
    adapter.request(
        _payload(
            decoding_params={"temperature": 0, "seed": 20260803, "logprobs": True}
        )
    )
    records = {record["record_id"]: record for record in _trace_records(tmp_path, "nok")}
    assert records["req-1/logprobs"]["payload"]["requested_top_logprobs"] is None


def test_opt_in_wire_response_record_preserves_exact_bytes_and_finish_reason(tmp_path):
    raw = b'{"choices":[{"finish_reason":"length"}],"usage":{"completion_tokens":2}}\n'
    wire = {
        "wire_response_b64": __import__("base64").b64encode(raw).decode("ascii"),
        "wire_response_sha256": hashlib.sha256(raw).hexdigest(),
        "wire_finish_reason": "length",
    }
    adapter, sink = _adapter(tmp_path, run_dir="wire", wire_response=wire)
    response = adapter.request(_payload())
    records = {record["record_id"]: record for record in _trace_records(tmp_path, "wire")}
    payload = records["req-1/wire-response"]["payload"]
    assert records["req-1/wire-response"]["channel"] == "MODEL_WIRE_RESPONSE"
    assert payload["request_id"] == "req-1"
    assert payload["sample_id"] == "5000001"
    assert payload["response_b64"] == wire["wire_response_b64"]
    assert payload["response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert payload["finish_reason"] == "length"
    assert response.text == "hello world"
    assert set(records["req-1/response"]["payload"]) == {
        "response_sha256", "response_text_sha256", "text", "usage"
    }
    assert sink.manifest()["req-1/wire-response"]


def test_malformed_http_response_is_traced_before_failure(tmp_path):
    raw = b"not-json-response"
    wire = {
        "wire_response_b64": __import__("base64").b64encode(raw).decode("ascii"),
        "wire_response_sha256": hashlib.sha256(raw).hexdigest(),
        "wire_finish_reason": None,
        "wire_response_error": "Expecting value",
    }
    adapter, _ = _adapter(tmp_path, run_dir="bad-http", wire_response=wire)
    with pytest.raises(FrozenCoreError, match="malformed response"):
        adapter.request(_payload())
    records = {record["record_id"]: record for record in _trace_records(tmp_path, "bad-http")}
    assert records["req-1/wire-response"]["payload"]["response_b64"] == wire["wire_response_b64"]
    assert records["req-1/wire-response"]["payload"]["finish_reason"] is None
    assert "req-1/response" not in records


def test_malformed_wire_response_hash_fails_closed(tmp_path):
    raw = b"raw"
    adapter, _ = _adapter(
        tmp_path,
        run_dir="bad-wire",
        wire_response={
            "wire_response_b64": __import__("base64").b64encode(raw).decode("ascii"),
            "wire_response_sha256": "0" * 64,
            "wire_finish_reason": "stop",
        },
    )
    with pytest.raises(FrozenCoreError, match="hash does not match"):
        adapter.request(_payload())


def test_the_response_record_is_untouched_by_the_new_one(tmp_path):
    """MODEL_RESPONSE keeps exactly the four fields it has always carried --
    the distribution is a sibling record, never a new response field."""

    adapter, _ = _adapter(tmp_path, run_dir="sib", logprobs=_server_logprobs())
    adapter.request(
        _payload(
            decoding_params={
                "temperature": 0,
                "seed": 20260803,
                "logprobs": True,
                "top_logprobs": 5,
            }
        )
    )
    records = {record["record_id"]: record for record in _trace_records(tmp_path, "sib")}
    assert set(records["req-1/response"]["payload"]) == {
        "response_sha256",
        "response_text_sha256",
        "text",
        "usage",
    }


# ---------------------------------------------------------------------------
# Byte identity for every run that never asks
# ---------------------------------------------------------------------------


def test_a_run_that_never_asks_writes_a_byte_identical_trace(tmp_path):
    """The whole trace file, byte for byte: no MODEL_LOGPROBS line, and every
    other line exactly as before."""

    adapter, sink = _adapter(tmp_path, run_dir="plain")
    adapter.request(_payload())
    raw = (tmp_path / "plain" / "SAEA-E-000-logprobs.trace.jsonl").read_bytes()
    channels = [json.loads(line)["channel"] for line in raw.decode("utf-8").splitlines()]
    assert "MODEL_LOGPROBS" not in channels
    assert channels == ["MODEL_REQUEST", "MODEL_RESPONSE", "COST"]
    assert set(sink.manifest()) == {"req-1/request", "req-1/response", "req-1/cost"}


def test_a_transport_that_returns_no_logprobs_key_emits_no_record_even_when_asked(
    tmp_path,
):
    """Real-server availability is not guaranteed (the 2026-08-13 policy note).
    An absent object is 'unavailable', never a crash and never an empty
    record."""

    adapter, sink = _adapter(tmp_path, run_dir="absent", logprobs=None)
    response = adapter.request(
        _payload(
            decoding_params={
                "temperature": 0,
                "seed": 20260803,
                "logprobs": True,
                "top_logprobs": 5,
            }
        )
    )
    assert response.logprobs is None
    assert "req-1/logprobs" not in sink.manifest()


# ---------------------------------------------------------------------------
# Fail-closed validation, BEFORE the call is metered
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "decoding_params, message",
    [
        ({"logprobs": 5}, "logprobs must be a bool"),
        ({"logprobs": "true"}, "logprobs must be a bool"),
        ({"logprobs": True, "top_logprobs": 0}, "top_logprobs must be an integer"),
        (
            {"logprobs": True, "top_logprobs": MAX_TOP_LOGPROBS + 1},
            "top_logprobs must be an integer",
        ),
        ({"logprobs": True, "top_logprobs": True}, "top_logprobs must be an integer"),
        ({"logprobs": True, "top_logprobs": 2.0}, "top_logprobs must be an integer"),
        ({"top_logprobs": 5}, "top_logprobs requires logprobs: true"),
        ({"logprobs": False, "top_logprobs": 5}, "top_logprobs requires logprobs: true"),
    ],
)
def test_a_malformed_decode_confidence_request_is_refused_before_it_is_metered(
    tmp_path, decoding_params, message
):
    """The server would refuse these itself -- but only after this adapter had
    already recorded the call as durably spent (record_usage runs before the
    transport call, deliberately). Refusing here makes the typo free."""

    adapter, sink = _adapter(tmp_path, run_dir=f"bad-{abs(hash(message)) % 97}")
    with pytest.raises(FrozenCoreError) as error:
        adapter.request(
            _payload(
                decoding_params={"temperature": 0, "seed": 20260803, **decoding_params}
            )
        )
    assert message in str(error.value)
    assert adapter.cost_summary()["calls_used"] == 0
    assert sink.manifest() == {}


def test_the_accepted_edges_of_the_range_are_accepted(tmp_path):
    for index, k in enumerate((1, MAX_TOP_LOGPROBS)):
        adapter, _ = _adapter(
            tmp_path,
            run_dir=f"edge-{index}",
            logprobs=_server_logprobs(k=1),
            plan=_plan(attempt_id=f"attempt-000{index}"),
        )
        adapter.request(
            _payload(
                decoding_params={
                    "temperature": 0,
                    "seed": 20260803,
                    "logprobs": True,
                    "top_logprobs": k,
                }
            )
        )
        records = {
            record["record_id"]: record
            for record in _trace_records(tmp_path, f"edge-{index}")
        }
        assert records["req-1/logprobs"]["payload"]["requested_top_logprobs"] == k


# ---------------------------------------------------------------------------
# The channel is a real, validated channel
# ---------------------------------------------------------------------------


def test_wire_response_channel_is_registered_core_provenance():
    TraceRecord(
        channel="MODEL_WIRE_RESPONSE",
        record_id="req-1/wire-response",
        payload={
            "request_id": "req-1",
            "sample_id": "sample-1",
            "response_b64": "eA==",
            "response_sha256": "0" * 64,
            "finish_reason": "stop",
        },
    ).validate()


def test_the_channel_carries_no_research_axis_prefix_requirement():
    """MODEL_LOGPROBS is core provenance, like MODEL_REQUEST/MODEL_RESPONSE --
    what a Reviewer judge derives from it is the OBS/ORG/SUPPLY/USE record."""

    TraceRecord(
        channel="MODEL_LOGPROBS",
        record_id="req-1/logprobs",
        payload={"logprobs": {"content": []}, "logprobs_sha256": "0" * 64},
    ).validate()


def test_an_unknown_channel_is_still_refused():
    with pytest.raises(TraceContractError):
        TraceRecord(
            channel="MODEL_LOGPROB", record_id="x", payload={}
        ).validate()
