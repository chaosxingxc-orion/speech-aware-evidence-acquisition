"""Trace sink: append-only JSONL, hash manifest, repo-refusal, close semantics.

Since 2026-09-26 the sink keeps one append handle open and flushes per record
(the per-record open/append/close cost 7.06 ms per record on the drvfs/9p run
root; docs/results/2026-09-26-slurp-seal-path-profile.md section 3). The
tests at the end hold the two properties that change nothing for readers:
the bytes are identical to the per-record pattern, and a process killed at
any instant leaves a trace complete up to the last ``emit`` that returned.
"""

import json
import os
import signal
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import TraceContractError, TraceRecord
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT
from speech_aware_evidence_acquisition.core.tracing import TraceSink, TraceSinkError


def test_emit_appends_validated_lines_and_manifest(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-test")
    assert sink.run_id == "SAEA-E-000-test"
    h1 = sink.emit("OBS", "s1/obs", {"obs_speech_ref": "earnings21-original/1"})
    h2 = sink.emit("COST", "s1/cost", {"calls": 1, "latency_seconds": 0.5})
    lines = (tmp_path / "run" / "SAEA-E-000-test.trace.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["channel"] == "OBS"
    assert sink.manifest() == {"s1/obs": h1, "s1/cost": h2}


def test_axis_prefix_violations_propagate(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-test")
    with pytest.raises(TraceContractError):
        sink.emit("OBS", "bad", {"supply_evidence": "smuggled"})


def test_duplicate_record_id_refused(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-test")
    sink.emit("OBS", "dup", {"obs_x": 1})
    with pytest.raises(TraceSinkError, match="duplicate"):
        sink.emit("OBS", "dup", {"obs_x": 2})


def test_run_dir_inside_repo_refused():
    with pytest.raises(TraceSinkError, match="repository"):
        TraceSink(REPO_ROOT / "docs" / "sneaky-run", "SAEA-E-000-test")


def test_close_writes_manifest_and_freezes(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-test")
    sink.emit("OBS", "s1/obs", {"obs_x": 1})
    manifest_hash = sink.close()
    assert len(manifest_hash) == 64
    document = json.loads(
        (tmp_path / "run" / "SAEA-E-000-test.trace-manifest.json").read_text("utf-8")
    )
    assert document["records"] == sink.manifest()
    with pytest.raises(TraceSinkError, match="closed"):
        sink.emit("OBS", "s2/obs", {"obs_x": 2})


def test_construction_refused_when_trace_file_already_exists(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-test")
    sink.emit("OBS", "s1/obs", {"obs_x": 1})
    with pytest.raises(TraceSinkError, match="exists"):
        TraceSink(tmp_path / "run", "SAEA-E-000-test")


def test_construction_refused_when_manifest_already_exists(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-closed")
    sink.emit("OBS", "s1/obs", {"obs_x": 1})
    sink.close()
    with pytest.raises(TraceSinkError, match="exists"):
        TraceSink(tmp_path / "run", "SAEA-E-000-closed")


def test_run_id_windows_drive_relative_path_refused(tmp_path):
    with pytest.raises(TraceSinkError, match="invalid run id"):
        TraceSink(tmp_path / "run", "D:evil")


def test_run_id_with_hyphens_and_digits_still_accepted(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-test")
    assert sink.run_id == "SAEA-E-000-test"


# ---------------------------------------------------------------------------
# One open handle, flushed per record (2026-09-26): bytes and crash semantics
# ---------------------------------------------------------------------------

_RECORDS = [
    ("OBS", "s1/obs", {"obs_speech_ref": "earnings21-original/1", "obs_seconds": 12.5}),
    ("MODEL_REQUEST", "req-0001/request", {"payload_sha256": "0" * 64, "nested": {"z": 1, "a": [1, 2.0, None, True]}}),
    ("ORG", "s1/org", {"org_note": "café 中文 \U0001f600 line\nbreak\ttab \"quote\" \\ back"}),
    ("SUPPLY", "s1/supply", {"supply_items": [{"id": "k1", "text": "x" * 100_000}]}),
    ("COST", "req-0001/cost", {"calls": 1, "latency_seconds": 0.25, "prompt_tokens": 10, "completion_tokens": 2}),
    ("USE", "s1/use", {"use_admitted": True, "use_reason": ""}),
]


def _legacy_per_record_append(path: Path, records) -> None:
    """The pre-2026-09-26 ``emit`` file pattern, byte for byte: the same
    serialised line, ``open("a", encoding="utf-8", newline="\\n")``, one
    ``write(line + "\\n")`` and a close per record, no fsync."""

    for channel, record_id, payload in records:
        line = TraceRecord(channel=channel, record_id=record_id, payload=payload).serialize()
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")


def test_persistent_handle_writes_the_same_bytes_as_the_per_record_pattern(tmp_path):
    legacy = tmp_path / "legacy.trace.jsonl"
    _legacy_per_record_append(legacy, _RECORDS)

    sink = TraceSink(tmp_path / "run", "SAEA-E-000-bytes")
    for record in _RECORDS:
        sink.emit(*record)
    sink.close()

    current = (tmp_path / "run" / "SAEA-E-000-bytes.trace.jsonl").read_bytes()
    assert current == legacy.read_bytes()
    assert current.endswith(b"\n")
    assert len(current.split(b"\n")) - 1 == len(_RECORDS)


def test_trace_file_is_created_lazily_on_the_first_emit_and_closed_on_close(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-lazy")
    path = tmp_path / "run" / "SAEA-E-000-lazy.trace.jsonl"
    assert not path.exists()
    sink.emit("OBS", "s1/obs", {"obs_x": 1})
    assert path.exists()
    # Every record is in the kernel when emit returns: another reader sees it
    # before close, exactly as with the per-record close.
    assert json.loads(path.read_text(encoding="utf-8"))["record_id"] == "s1/obs"
    sink.close()
    assert sink._handle is None
    sink.close()  # a second close re-writes the manifest and needs no handle


def test_concurrent_emitters_never_tear_a_line(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-threads")
    errors: list[BaseException] = []

    def worker(tag: str) -> None:
        try:
            for index in range(50):
                sink.emit("OBS", f"{tag}/{index}/obs", {"obs_tag": tag, "obs_blob": "y" * (20_000 if index % 5 == 0 else 100)})
        except BaseException as error:  # pragma: no cover - surfaced below
            errors.append(error)

    threads = [threading.Thread(target=worker, args=(f"t{n}",)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    sink.close()

    assert errors == []
    lines = (tmp_path / "run" / "SAEA-E-000-threads.trace.jsonl").read_bytes().split(b"\n")
    assert lines.pop() == b""
    ids = [json.loads(line)["record_id"] for line in lines]
    assert len(ids) == 200 and len(set(ids)) == 200
    assert sink.manifest().keys() == set(ids)


_KILL_CHILD = textwrap.dedent(
    """
    import os, signal, sys
    sys.path.insert(0, sys.argv[1])
    from speech_aware_evidence_acquisition.core.tracing import TraceSink
    sink = TraceSink(sys.argv[2], "SAEA-E-000-kill")
    for index in range(int(sys.argv[3])):
        sink.emit("OBS", f"s{index}/obs", {"obs_index": index, "obs_blob": "x" * (70000 if index % 7 == 0 else 300)})
    os.kill(os.getpid(), signal.SIGKILL)
    """
)

_KILL_CONTROL = textwrap.dedent(
    """
    import json, os, signal, sys
    handle = open(os.path.join(sys.argv[2], "control.jsonl"), "a", encoding="utf-8", newline="\\n")
    for index in range(int(sys.argv[3])):
        handle.write(json.dumps({"record_id": f"s{index}/obs", "obs_blob": "x" * (70000 if index % 7 == 0 else 300)}) + "\\n")
    os.kill(os.getpid(), signal.SIGKILL)
    """
)


def _run_killed_child(script: str, run_dir: Path, count: int) -> None:
    import speech_aware_evidence_acquisition.core.tracing as tracing

    src = Path(tracing.__file__).resolve().parents[2]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script, str(src), str(run_dir), str(count)],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert completed.returncode == -signal.SIGKILL, completed.stderr


@pytest.mark.skipif(os.name == "nt", reason="SIGKILL semantics are the WSL/Linux flight host's")
def test_a_killed_process_leaves_the_trace_complete_up_to_the_last_returned_emit(tmp_path):
    """The property both recovery readers rely on: ``core.flight.resume.
    _scan_trace`` refuses a predecessor trace on one malformed line, and
    ``read_attempt_trace_facts`` counts an interrupted attempt's contacts.
    Records larger than every Python buffer (70,000 chars) sit beside small
    ones so an unflushed buffer or a torn tail would show."""

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    count = 40
    _run_killed_child(_KILL_CHILD, run_dir, count)

    data = (run_dir / "SAEA-E-000-kill.trace.jsonl").read_bytes()
    assert data.endswith(b"\n")
    lines = data.split(b"\n")
    assert lines.pop() == b""
    assert len(lines) == count
    for index, line in enumerate(lines):
        record = json.loads(line)  # every line whole: no torn record anywhere
        assert record["record_id"] == f"s{index}/obs"
        assert len(record["payload"]["obs_blob"]) == (70000 if index % 7 == 0 else 300)
    assert not (run_dir / "SAEA-E-000-kill.trace-manifest.json").exists()


@pytest.mark.skipif(os.name == "nt", reason="SIGKILL semantics are the WSL/Linux flight host's")
def test_control_a_buffered_handle_without_flush_would_have_lost_records(tmp_path):
    """Shows the previous test can fail: the same kill against a plain
    buffered handle with no per-record flush leaves records behind in the
    process (the tail below 8 KiB never reaches the kernel)."""

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    count = 40
    _run_killed_child(_KILL_CONTROL, run_dir, count)

    data = (run_dir / "control.jsonl").read_bytes()
    whole = [line for line in data.split(b"\n")[:-1]]
    assert len(whole) < count
