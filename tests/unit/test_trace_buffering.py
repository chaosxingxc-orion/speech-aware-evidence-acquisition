"""Per-sample trace buffering for batched execution (owner directive
2026-08-08): TraceBuffer records a sample's trace in-memory (eagerly
validated, mutation-proof) and replays it into the single per-run TraceSink
in split-id order; DispatchingSink routes the shared adapter's emissions to
the current task's buffer via a contextvar (task-local under asyncio,
propagated into asyncio.to_thread workers), falling through to the real
sink when unset -- the sequential path is untouched.
"""

import asyncio
import copy
import json

import pytest

from speech_aware_evidence_acquisition.contracts import TraceContractError
from speech_aware_evidence_acquisition.core.tracing import (
    DispatchingSink,
    TraceBuffer,
    TraceSink,
    set_current_trace_buffer,
)

RUN_ID = "SAEA-E-000-tracebuf"


def _read_records(run_dir):
    # TraceSink creates its file lazily on the first emit, so "no file" and
    # "no records" are the same fact here.
    path = run_dir / f"{RUN_ID}.trace.jsonl"
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    return [json.loads(line) for line in raw.splitlines() if line]


class TestTraceBuffer:
    def test_flush_reproduces_a_direct_emit_sink_byte_for_byte(self, tmp_path):
        events = [
            ("OBS", "req-0001/obs", {"obs_a": 1}),
            ("MODEL_REQUEST", "req-0001/request", {"payload_sha256": "0" * 64}),
            ("USE", "req-0001/use", {"use_admitted": True}),
        ]
        direct = TraceSink(tmp_path / "direct", RUN_ID)
        for event in events:
            direct.emit(*event)
        direct.close()

        buffered = TraceBuffer(RUN_ID)
        assert buffered.run_id == RUN_ID
        for event in events:
            buffered.emit(*event)
        sink = TraceSink(tmp_path / "buffered", RUN_ID)
        buffered.flush_into(sink)
        sink.close()

        direct_bytes = (tmp_path / "direct" / f"{RUN_ID}.trace.jsonl").read_bytes()
        buffered_bytes = (tmp_path / "buffered" / f"{RUN_ID}.trace.jsonl").read_bytes()
        assert buffered_bytes == direct_bytes
        assert (
            tmp_path / "buffered" / f"{RUN_ID}.trace-manifest.json"
        ).read_bytes() == (tmp_path / "direct" / f"{RUN_ID}.trace-manifest.json").read_bytes()

    def test_emit_validates_eagerly_like_the_real_sink(self):
        buffer = TraceBuffer(RUN_ID)
        with pytest.raises(TraceContractError):
            buffer.emit("NOT_A_CHANNEL", "req-0001/x", {"x": 1})
        # axis namespace discipline is enforced at emit time, not at flush
        with pytest.raises(TraceContractError):
            buffer.emit("OBS", "req-0001/obs", {"use_smuggled": True})

    def test_buffered_payloads_are_mutation_proof(self, tmp_path):
        buffer = TraceBuffer(RUN_ID)
        live = {"obs_ids": ["a"]}
        buffer.emit("OBS", "req-0001/obs", live)
        live["obs_ids"].append("b")  # mutated AFTER emit, like a live list
        sink = TraceSink(tmp_path / "run", RUN_ID)
        buffer.flush_into(sink)
        records = _read_records(tmp_path / "run")
        assert records[0]["payload"]["obs_ids"] == ["a"]

    def test_flush_is_one_shot(self, tmp_path):
        buffer = TraceBuffer(RUN_ID)
        buffer.emit("OBS", "req-0001/obs", {"obs_a": 1})
        sink = TraceSink(tmp_path / "run", RUN_ID)
        buffer.flush_into(sink)
        buffer.flush_into(sink)  # second flush replays nothing (no dup error)
        assert len(_read_records(tmp_path / "run")) == 1


class TestDispatchingSink:
    def test_passthrough_when_no_buffer_is_current(self, tmp_path):
        sink = TraceSink(tmp_path / "run", RUN_ID)
        dispatcher = DispatchingSink(sink)
        assert dispatcher.run_id == RUN_ID
        set_current_trace_buffer(None)
        dispatcher.emit("OBS", "req-0001/obs", {"obs_a": 1})
        assert len(_read_records(tmp_path / "run")) == 1

    def test_routes_to_task_local_buffers_under_asyncio_and_to_thread(self, tmp_path):
        """Two concurrent tasks, each with its own buffer set task-locally;
        emissions from the task itself AND from inside asyncio.to_thread
        (where the real adapter call runs) land in that task's buffer."""

        sink = TraceSink(tmp_path / "run", RUN_ID)
        dispatcher = DispatchingSink(sink)
        buffers = {"a": TraceBuffer(RUN_ID), "b": TraceBuffer(RUN_ID)}

        async def sample_task(tag):
            set_current_trace_buffer(buffers[tag])
            dispatcher.emit("OBS", f"req-{tag}/obs", {"obs_tag": tag})
            await asyncio.to_thread(
                dispatcher.emit,
                "MODEL_REQUEST",
                f"req-{tag}/request",
                {"payload_sha256": "0" * 64},
            )
            await asyncio.sleep(0)
            dispatcher.emit("USE", f"req-{tag}/use", {"use_admitted": True})

        async def main():
            await asyncio.gather(
                asyncio.create_task(sample_task("a")),
                asyncio.create_task(sample_task("b")),
            )

        asyncio.run(main())
        assert len(_read_records(tmp_path / "run")) == 0  # nothing leaked through
        for tag, buffer in buffers.items():
            ids = [record_id for _, record_id, _ in buffer.records]
            assert ids == [f"req-{tag}/obs", f"req-{tag}/request", f"req-{tag}/use"]

    def test_deterministic_file_order_is_flush_order(self, tmp_path):
        sink = TraceSink(tmp_path / "run", RUN_ID)
        first = TraceBuffer(RUN_ID)
        second = TraceBuffer(RUN_ID)
        second.emit("OBS", "req-0002/obs", {"obs_a": 2})  # emitted FIRST in time
        first.emit("OBS", "req-0001/obs", {"obs_a": 1})
        first.flush_into(sink)
        second.flush_into(sink)
        ids = [record["record_id"] for record in _read_records(tmp_path / "run")]
        assert ids == ["req-0001/obs", "req-0002/obs"]  # split-id order, not time


def test_deepcopy_helper_assumption():
    """The buffer relies on deepcopy freezing nested payload values."""

    payload = {"a": [1, {"b": 2}]}
    frozen = copy.deepcopy(payload)
    payload["a"][1]["b"] = 3
    assert frozen == {"a": [1, {"b": 2}]}
