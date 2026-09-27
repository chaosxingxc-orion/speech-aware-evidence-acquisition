"""Model-free finalize-from-disk: determinism, isolation, and fail-closed edges.

Covers the rebuild path introduced for the 2026-08-23 E108 incident, in which
every model contact of a flight completed, every durable record landed, and
post-run metrics assembly then raised -- leaving an attempt that could never be
finalized. See ``docs/readiness/
2026-08-23-e108-attempt-finalization-adjudication.md`` section 5.
"""

from __future__ import annotations

import hashlib
import json
import types
from dataclasses import asdict
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.driver import speech_native
from speech_aware_evidence_acquisition.core.driver.speech_native import (
    FINALIZE_FROM_DISK_MODE_ID,
    SpeechNativeProfileError,
    _count_jsonl_lines,
    _iter_trace_lines,
    _trace_facts_from_lines,
    build_flight_receipt_from_disk,
    derive_server_log_window_for_contacts,
    read_attempt_trace_facts,
)
from speech_aware_evidence_acquisition.core.resources import NOT_AVAILABLE

SESSION_STARTED_AT = "2026-08-21T12:00:00+00:00"
RUN_ID = "SAEA-SN-TEST-FINALIZE-FROM-DISK"
ATTEMPT_ID = "attempt-20260821T120000Z-test"
_FIRST_LOG_LINE = "0.00.050.000 I log_info: startup\n"
_ATTEMPT_LOG_LINES = (
    "0.01.000.000 I slot launch_slot_: id  0 | task 101 | processing task\n"
    "0.01.100.000 I slot launch_slot_: id  1 | task 102 | processing task\n"
    "0.01.900.000 I slot print_timing: id  0 | task 101 | "
    "prompt eval time =     100.00 ms /  1000 tokens\n"
    "0.02.000.000 I slot      release: id  0 | task 101 | stop processing\n"
    "0.02.900.000 I slot print_timing: id  1 | task 102 | "
    "prompt eval time =     100.00 ms /  1000 tokens\n"
    "0.03.000.000 I slot      release: id  1 | task 102 | stop processing\n"
)


def _packet_sha(sample_id: str) -> str:
    return hashlib.sha256(sample_id.encode("utf-8")).hexdigest()


def _plan() -> ExecutionPlan:
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="slurp",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=2,
        planned_gpu_hours=0.5,
        planned_speech_audio_seconds=100,
        protocol_hash="b" * 64,
        attempt_id=ATTEMPT_ID,
    ).validate()


def _profile_identity() -> dict[str, object]:
    return {
        "slot_count": 2,
        "queue_depth": 4,
        "key_card_count": 18,
        "key_order_ids": ["canonical"],
        "key_representation_id": "K1",
        "matcher_policy_id": "M11",
        "decision_graph_id": "slurp-signature-complete-decision-graph-v5",
        "decision_graph_path": "configs/knowledge/graph.json",
        "decision_graph_file_sha256": "c" * 64,
        "agent_policy_id": "speech-conditioned-adaptive-evidence-gap-v2",
        "agent_aggregator_id": "adaptive-evidence-gap-primary-control-v1",
        "agent_executor_id": "legacy-contact-dag-v1",
        "mechanism_control_id": "matched",
        "dispatch_granularity": "task",
        "query_mapping_sha256": NOT_AVAILABLE,
        "key_text_mapping_sha256": None,
        "top_k": 3,
        "context_tokens_total": 8192,
        "context_tokens_per_slot": 4096,
    }


def _write_attempt(tmp_path: Path, *, decisions_text: str | None = None) -> Path:
    attempt_dir = tmp_path / ATTEMPT_ID
    attempt_dir.mkdir()
    (attempt_dir / f"{RUN_ID}.plan.json").write_text(
        json.dumps(asdict(_plan())), encoding="utf-8"
    )
    (attempt_dir / f"{RUN_ID}.session-receipt.json").write_text(
        json.dumps(
            {"schema": "saea-session-receipt-v2", "started_at": SESSION_STARTED_AT}
        ),
        encoding="utf-8",
    )
    (attempt_dir / f"{RUN_ID}.mmproj-audit.json").write_text(
        json.dumps({"mmproj_loaded": False, "mmproj_hit_count": 0}), encoding="utf-8"
    )
    (attempt_dir / f"{RUN_ID}.trace-manifest.json").write_text(
        json.dumps({"run_id": RUN_ID, "records": {}}), encoding="utf-8"
    )
    rows: list[str] = []
    for index, sample_id in enumerate(("sample-a", "sample-b"), start=1):
        sha = _packet_sha(sample_id)
        rows.append(
            json.dumps(
                {
                    "record_id": f"speech-native-profile-{index:04d}/request",
                    "channel": "MODEL_REQUEST",
                    "payload": {
                        "arm": "speech-feature-query",
                        "payload_sha256": "d" * 64,
                        "payload": {
                            "sample_id": sample_id,
                            "query_source": "speech_features",
                            "mmproj_loaded": False,
                            "speech_packet_sha256": sha,
                            "speech_feature_parts": [
                                {
                                    "packet_id": f"packet-{sample_id}",
                                    "sha256": sha,
                                    "role": "query",
                                }
                            ],
                        },
                    },
                }
            )
        )
        rows.append(
            json.dumps(
                {
                    "record_id": f"speech-native-profile-{index:04d}/response",
                    "channel": "MODEL_RESPONSE",
                    # Deliberately not a usable payload shape: any code that
                    # opened this channel would break, which is the point.
                    "payload": "OPAQUE-RESPONSE-NEVER-OPENED",
                }
            )
        )
        rows.append(
            json.dumps(
                {
                    "record_id": f"speech-native-profile-{index:04d}/cost",
                    "channel": "COST",
                    "payload": {
                        "calls": 1,
                        "prompt_tokens": 1000,
                        "completion_tokens": 20,
                        "audio_seconds": 3.5,
                        "latency_seconds": 1.0,
                    },
                }
            )
        )
    (attempt_dir / f"{RUN_ID}.trace.jsonl").write_text(
        "\n".join(rows) + "\n", encoding="utf-8"
    )
    if decisions_text is None:
        decisions_text = (
            json.dumps({"task_id": "t1", "sample_id": "sample-a"})
            + "\n"
            + json.dumps({"task_id": "t2", "sample_id": "sample-b"})
            + "\n"
        )
    (attempt_dir / "decisions.jsonl").write_text(decisions_text, encoding="utf-8")
    return attempt_dir


def _write_server_log(
    tmp_path: Path, *, attempt_lines: str = _ATTEMPT_LOG_LINES
) -> Path:
    log_path = tmp_path / "server.log"
    log_path.write_text(_FIRST_LOG_LINE + attempt_lines, encoding="utf-8")
    return log_path


def _build(tmp_path: Path, attempt_dir: Path, log_path: Path, **overrides):
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps({"binding": True}), encoding="utf-8")
    packet_receipt_path = tmp_path / "packets.json"
    packet_receipt_path.write_text(json.dumps({"packets": []}), encoding="utf-8")
    kwargs: dict[str, object] = {
        "attempt_dir": attempt_dir,
        "plan": _plan(),
        "config_hash": "e" * 64,
        "profile_identity": _profile_identity(),
        "contact_ceiling_per_task": 1,
        "expected_task_count": 2,
        "result_mode": "predictions",
        "transport_prompt_order": "key-then-speech-v1",
        "binding_path": binding_path,
        "packet_receipt_path": packet_receipt_path,
        "server_log_path": log_path,
        "server_log_start_offset": len(_FIRST_LOG_LINE.encode("utf-8")),
        "server_log_end_offset": log_path.stat().st_size,
        "session_started_at": SESSION_STARTED_AT,
        "source_session_receipt_sha256": "f" * 64,
        "authorization": "docs/readiness/2026-08-23-e108-attempt-finalization-adjudication.md#5",
        "exposure_row": "SAEA-SN-MF-TEST-FINALIZE-FROM-DISK",
        "rebuilt_at": "2026-08-23T18:30:00+00:00",
    }
    kwargs.update(overrides)
    return build_flight_receipt_from_disk(**kwargs)  # type: ignore[arg-type]


def test_rebuild_is_deterministic_over_its_data_derived_fields(tmp_path):
    attempt_dir = _write_attempt(tmp_path)
    log_path = _write_server_log(tmp_path)

    first = _build(
        tmp_path, attempt_dir, log_path, rebuilt_at="2026-08-23T18:30:00+00:00"
    )
    second = _build(
        tmp_path, attempt_dir, log_path, rebuilt_at="2027-01-01T00:00:00+00:00"
    )

    assert first["finalization"]["rebuilt_at"] != second["finalization"]["rebuilt_at"]
    assert (
        first["finalization"]["content_sha256"]
        == second["finalization"]["content_sha256"]
    )
    first_body = dict(first)
    second_body = dict(second)
    first_body.pop("finalization")
    second_body.pop("finalization")
    assert first_body == second_body


def test_rebuilt_receipt_carries_the_degraded_gpu_telemetry_fields(tmp_path):
    attempt_dir = _write_attempt(tmp_path)
    log_path = _write_server_log(tmp_path)

    receipt = _build(tmp_path, attempt_dir, log_path)

    saturated = receipt["saturated_gpu"]
    assert saturated["gpu_telemetry_defect"]
    assert saturated["utilization_median_pct"] == NOT_AVAILABLE
    assert saturated["utilization_p10_pct"] == NOT_AVAILABLE
    assert saturated["server_slot_launch_count"] == 2
    assert saturated["server_slot_release_count"] == 2
    assert receipt["resource"]["gpu_seconds"] == NOT_AVAILABLE
    assert receipt["eligibility"]["gpu_telemetry_available"] is False
    # The scientific conjuncts still hold even though the GPU gate cannot.
    assert receipt["eligibility"]["zero_request_failures"] is True
    assert receipt["eligibility"]["zero_oom_markers"] is True
    assert receipt["eligible"] is False
    assert receipt["status"] == "COMPLETED"
    assert receipt["request_failures"] == []
    assert receipt["completion_issues"] == []
    assert receipt["finalization"]["mode"] == FINALIZE_FROM_DISK_MODE_ID
    assert receipt["finalization"]["service_contact_count"] == 0
    assert receipt["profile"]["task_count"] == 2
    assert receipt["profile"]["actual_contact_count"] == 2
    assert receipt["decisions"]["count"] == 2
    assert receipt["trace_speech_query"]["valid_speech_query_count"] == 2
    assert receipt["trace_speech_query"]["invalid_speech_query_count"] == 0


def test_rebuild_refuses_an_attempt_that_already_has_a_receipt(tmp_path):
    attempt_dir = _write_attempt(tmp_path)
    log_path = _write_server_log(tmp_path)
    (attempt_dir / "flight-receipt.json").write_text("{}", encoding="utf-8")

    with pytest.raises(SpeechNativeProfileError, match="already finalized"):
        _build(tmp_path, attempt_dir, log_path)


def test_rebuild_fails_closed_on_an_unbalanced_slot_lifecycle(tmp_path):
    attempt_dir = _write_attempt(tmp_path)
    corrupted = "".join(
        line + "\n"
        for line in _ATTEMPT_LOG_LINES.splitlines()
        if "release: id  1" not in line
    )
    log_path = _write_server_log(tmp_path, attempt_lines=corrupted)

    with pytest.raises(
        SpeechNativeProfileError, match="unbalanced or contact-incomplete"
    ):
        _build(tmp_path, attempt_dir, log_path)


def test_rebuild_fails_closed_when_decision_rows_do_not_cover_the_split(tmp_path):
    attempt_dir = _write_attempt(
        tmp_path, decisions_text=json.dumps({"task_id": "t1"}) + "\n"
    )
    log_path = _write_server_log(tmp_path)

    with pytest.raises(SpeechNativeProfileError, match="do not match the registered"):
        _build(tmp_path, attempt_dir, log_path)


def test_rebuild_fails_closed_when_the_plan_copy_disagrees(tmp_path):
    attempt_dir = _write_attempt(tmp_path)
    log_path = _write_server_log(tmp_path)
    drifted = asdict(_plan())
    drifted["planned_model_calls"] = 9
    (attempt_dir / f"{RUN_ID}.plan.json").write_text(
        json.dumps(drifted), encoding="utf-8"
    )

    with pytest.raises(SpeechNativeProfileError, match="plan copy does not match"):
        _build(tmp_path, attempt_dir, log_path)


def test_rebuild_fails_closed_when_the_process_audit_is_not_mmproj_free(tmp_path):
    attempt_dir = _write_attempt(tmp_path)
    log_path = _write_server_log(tmp_path)
    (attempt_dir / f"{RUN_ID}.mmproj-audit.json").write_text(
        json.dumps({"mmproj_loaded": True, "mmproj_hit_count": 3}), encoding="utf-8"
    )

    with pytest.raises(SpeechNativeProfileError, match="mmproj-free"):
        _build(tmp_path, attempt_dir, log_path)


def test_decision_rows_are_counted_without_ever_being_parsed(tmp_path):
    path = tmp_path / "decisions.jsonl"
    # Not JSON at all: a counter that parsed rows could not survive this.
    path.write_text("not json {{{\n\nstill not json ]]]\n", encoding="utf-8")

    assert _count_jsonl_lines(path) == 2


def test_trace_facts_never_open_the_model_response_payload(tmp_path):
    attempt_dir = _write_attempt(tmp_path)

    facts = read_attempt_trace_facts(attempt_dir / f"{RUN_ID}.trace.jsonl")

    assert facts["trace_usage"]["model_response_count"] == 2
    # Token maxima come from the COST channel, never from a response payload.
    assert facts["trace_usage_source"] == "cost-channel-token-accounting-v1"
    assert facts["trace_usage"]["max_prompt_tokens"] == 1000
    assert facts["trace_usage"]["max_completion_tokens"] == 20
    assert facts["cost"]["calls_used"] == 2
    assert facts["cost"]["audio_seconds_used"] == pytest.approx(7.0)
    assert facts["distinct_query_sample_id_count"] == 2
    assert facts["distinct_query_packet_id_count"] == 2


def test_trace_facts_flag_a_request_that_lost_its_speech_carriage(tmp_path):
    attempt_dir = _write_attempt(tmp_path)
    trace_path = attempt_dir / f"{RUN_ID}.trace.jsonl"
    rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
    rows[0]["payload"]["payload"]["query_source"] = "transcript"
    trace_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )

    facts = read_attempt_trace_facts(trace_path)

    assert facts["speech_query"]["query_source_failure_count"] == 1
    assert facts["speech_query"]["invalid_speech_query_count"] == 1


# ---------------------------------------------------------------------------
# The large-read line source (2026-09-26) against the former text-mode
# iteration: identical lines, identical facts, identical refusals.
# ---------------------------------------------------------------------------


def _legacy_text_lines(path: Path):
    """The pre-2026-09-26 line source of ``read_attempt_trace_facts``:
    ``open(path, "r", encoding="utf-8")`` iterated line by line."""

    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            yield line


def _append_record(trace_path: Path, record: dict, *, terminate: bool = True) -> None:
    with trace_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + ("\n" if terminate else ""))


def test_large_read_lines_equal_text_mode_lines_at_every_block_boundary(tmp_path):
    trace_path = _write_attempt(tmp_path) / f"{RUN_ID}.trace.jsonl"
    _append_record(
        trace_path,
        {"channel": "ORG", "record_id": "s/org", "payload": {"org_note": "café 中文 \U0001f600" * 40}},
    )
    reference = [line.rstrip("\n") for line in _legacy_text_lines(trace_path)]
    assert reference and len(reference) > 4

    for block_bytes in (1, 3, 7, 64, 4096, 64 * 1024 * 1024):
        assert list(_iter_trace_lines(trace_path, block_bytes=block_bytes)) == reference


def test_large_read_facts_equal_text_mode_facts(tmp_path):
    trace_path = _write_attempt(tmp_path) / f"{RUN_ID}.trace.jsonl"

    assert read_attempt_trace_facts(trace_path) == _trace_facts_from_lines(_legacy_text_lines(trace_path))
    for block_bytes in (1, 5, 1000):
        assert _trace_facts_from_lines(_iter_trace_lines(trace_path, block_bytes=block_bytes)) == _trace_facts_from_lines(
            _legacy_text_lines(trace_path)
        )


def test_large_read_handles_a_final_unterminated_line_like_text_mode(tmp_path):
    trace_path = _write_attempt(tmp_path) / f"{RUN_ID}.trace.jsonl"
    _append_record(
        trace_path,
        {"channel": "COST", "record_id": "x/cost", "payload": {"calls": 1, "prompt_tokens": 7, "completion_tokens": 1, "audio_seconds": 1.0, "latency_seconds": 0.5}},
        terminate=False,
    )
    assert not trace_path.read_bytes().endswith(b"\n")

    assert [line.rstrip("\n") for line in _legacy_text_lines(trace_path)] == list(_iter_trace_lines(trace_path, block_bytes=11))
    facts = read_attempt_trace_facts(trace_path)
    assert facts == _trace_facts_from_lines(_legacy_text_lines(trace_path))
    assert facts["trace_usage"]["cost_record_count"] == 3


def test_large_read_of_an_empty_trace_equals_text_mode(tmp_path):
    trace_path = tmp_path / "empty.trace.jsonl"
    trace_path.write_bytes(b"")

    assert list(_iter_trace_lines(trace_path)) == []
    assert read_attempt_trace_facts(trace_path) == _trace_facts_from_lines(_legacy_text_lines(trace_path))
    assert read_attempt_trace_facts(trace_path)["cost"]["calls_used"] == 0


def test_large_read_refuses_what_text_mode_refused(tmp_path):
    attempt_dir = _write_attempt(tmp_path)
    trace_path = attempt_dir / f"{RUN_ID}.trace.jsonl"

    # A blank line between records: json.loads("") fails in both forms.
    blank = tmp_path / "blank.trace.jsonl"
    body = trace_path.read_bytes().split(b"\n")
    blank.write_bytes(b"\n".join(body[:1] + [b""] + body[1:]))
    with pytest.raises(json.JSONDecodeError):
        _trace_facts_from_lines(_legacy_text_lines(blank))
    with pytest.raises(SpeechNativeProfileError, match="cannot verify profile trace"):
        read_attempt_trace_facts(blank)

    # Bytes that are not UTF-8: a UnicodeError in both forms.
    broken = tmp_path / "broken.trace.jsonl"
    broken.write_bytes(trace_path.read_bytes() + b'{"channel": "ORG", "record_id": "b", "payload": {"org_x": "\xff\xfe"}}\n')
    with pytest.raises(UnicodeDecodeError):
        _trace_facts_from_lines(_legacy_text_lines(broken))
    with pytest.raises(SpeechNativeProfileError, match="cannot verify profile trace"):
        read_attempt_trace_facts(broken)

    # A missing file: OSError in both forms.
    with pytest.raises(OSError):
        _trace_facts_from_lines(_legacy_text_lines(tmp_path / "absent.trace.jsonl"))
    with pytest.raises(SpeechNativeProfileError, match="cannot verify profile trace"):
        read_attempt_trace_facts(tmp_path / "absent.trace.jsonl")

    with pytest.raises(ValueError, match="block_bytes"):
        list(_iter_trace_lines(trace_path, block_bytes=0))


def test_the_server_log_window_is_derived_from_the_trailing_contacts(tmp_path):
    log_path = _write_server_log(tmp_path)

    start, end = derive_server_log_window_for_contacts(
        server_log_path=log_path, expected_contact_count=2
    )

    assert start == len(_FIRST_LOG_LINE.encode("utf-8"))
    assert end == log_path.stat().st_size
    with pytest.raises(SpeechNativeProfileError, match="slot launches"):
        derive_server_log_window_for_contacts(
            server_log_path=log_path, expected_contact_count=9
        )


def _code_names(code: types.CodeType) -> set[str]:
    names = set(code.co_names)
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            names |= _code_names(const)
    return names


FORBIDDEN_CONTACT_NAMES = frozenset(
    {
        "FrozenCoreClient",
        "FrozenCoreGate",
        "TRANSPORTS",
        "_LoopbackPromptAuditClient",
        "_write_inference_process_audit",
        "attach_session",
        "build_payload_binding",
        "http",
        "requests",
        "resolve_resource_sampler",
        "socket",
        "start_session",
        "stop_session",
        "urllib",
        "write_session_receipt",
    }
)


@pytest.mark.parametrize(
    "function",
    [
        speech_native._cli_speech_native_finalize_from_disk,
        speech_native.build_flight_receipt_from_disk,
        speech_native.read_attempt_trace_facts,
        speech_native.derive_server_log_window_for_contacts,
        speech_native._finalize_from_disk_profile_identity,
    ],
)
def test_the_finalize_path_can_never_construct_a_transport(function):
    assert not (_code_names(function.__code__) & FORBIDDEN_CONTACT_NAMES)


def test_the_rebuild_succeeds_with_every_contact_primitive_disabled(
    tmp_path, monkeypatch
):
    """Runtime proof of the same claim, covering transitive calls."""

    def refuse(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("the finalize-from-disk rebuild contacted a service")

    for name in (
        "FrozenCoreClient",
        # Was "TRANSPORTS" until commit a29950c2 ("feat: wire prepared cache
        # guard into transports") replaced the direct "from ..base import
        # TRANSPORTS" with build_configured_transport, so TRANSPORTS is no
        # longer an attribute of this module; build_configured_transport is the
        # current name that could construct a live transport here.
        "build_configured_transport",
        "attach_session",
        "start_session",
        "stop_session",
        "write_session_receipt",
        "build_payload_binding",
        "resolve_resource_sampler",
    ):
        monkeypatch.setattr(speech_native, name, refuse, raising=True)
    import socket as socket_module

    monkeypatch.setattr(socket_module, "socket", refuse, raising=True)
    monkeypatch.setattr(speech_native.http.client, "HTTPConnection", refuse)

    attempt_dir = _write_attempt(tmp_path)
    log_path = _write_server_log(tmp_path)

    receipt = _build(tmp_path, attempt_dir, log_path)

    assert receipt["finalization"]["service_contact_count"] == 0
