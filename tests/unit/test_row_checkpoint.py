"""Owner decision 309 (2026-10-14): the durable row-by-row checkpoint file.

Model-free, server-free: the writer, the reader's chain and torn-tail rules,
the arm-group completeness rule, the per-row cost of one append + fsync, and the
bundle-side re-derivation of a checkpoint-mode predecessor block.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core import row_checkpoint as rc
from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    verify_predecessor_attempt,
    verify_predecessor_attempts,
)
from speech_aware_evidence_acquisition.core.row_checkpoint import (
    RowCheckpointError,
    RowCheckpointWriter,
    arm_group_defect,
    compare_with_sealed,
    kept_trace_text,
    read_checkpoint,
    verify_manifest_block,
)

RUN = "SAEA-TEST-CKPT-001"


def _trace_lines(sample_id: str, request_id: str, *, extra: int = 0) -> list[str]:
    records = [
        ("MODEL_REQUEST", f"{request_id}/request", {"payload": {"sample_id": sample_id}, "payload_sha256": "a" * 64}),
        ("MODEL_RESPONSE", f"{request_id}/response", {"text": f"answer {sample_id}", "response_sha256": "b" * 64, "response_text_sha256": "c" * 64}),
        ("COST", f"{request_id}/cost", {"latency_seconds": 0.5, "audio_seconds": 2.0, "prompt_tokens": 10, "completion_tokens": 3}),
    ]
    records += [
        ("ORG", f"{sample_id}/filler-{index}", {"org_filler": "x" * 600})
        for index in range(extra)
    ]
    return rc.serialize_trace_records(records)


def _row(sample_id: str, request_id: str) -> dict:
    return {
        "request_id": request_id, "sample_id": sample_id, "carrier_lock_key": "slurp",
        "arm": "arm", "text": f"answer {sample_id}", "admitted": True,
        "request_sha256": "a" * 64, "response_sha256": "b" * 64,
        "response_text_sha256": "c" * 64,
    }


def _writer(tmp_path: Path, **kwargs) -> RowCheckpointWriter:
    return RowCheckpointWriter(
        tmp_path / "attempt-1", RUN, "attempt-1",
        identity={"protocol_hash": "p" * 64, "split_identity_hash": "s" * 64}, **kwargs,
    )


def _append(writer, sample_id: str, index: int, **kwargs) -> None:
    writer.append_row(
        sample_id=sample_id, complete=kwargs.pop("complete", True),
        output_rows=kwargs.pop("output_rows", [_row(sample_id, f"flight-{index:04d}")]),
        trace_lines=_trace_lines(sample_id, f"flight-{index:04d}"), **kwargs,
    )


def test_every_append_is_fsynced_and_the_chain_reads_back(tmp_path, monkeypatch):
    calls = []
    real = rc.os.fsync
    monkeypatch.setattr(rc.os, "fsync", lambda fd: (calls.append(fd), real(fd))[1])
    writer = _writer(tmp_path)
    after_header = len(calls)
    assert after_header >= 1  # the header record is durable before any row exists
    for index, sample_id in enumerate(("s1", "s2", "s3"), start=1):
        before = len(calls)
        _append(writer, sample_id, index)
        # exactly one fsync per appended row, and the line is already on disk
        assert len(calls) == before + 1
        assert read_checkpoint(writer.path).rows[-1].sample_id == sample_id
    writer.close()
    document = read_checkpoint(writer.path)
    assert [row.sample_id for row in document.rows] == ["s1", "s2", "s3"]
    assert document.complete_rows == 3 and document.torn_tail_bytes == 0
    assert document.header["protocol_hash"] == "p" * 64
    assert document.sha256 == hashlib.sha256(writer.path.read_bytes()).hexdigest()
    # per-row cost and contact count come from the row's own trace
    assert document.rows[0].contacts == 1 and document.rows[0].audio_seconds == 2.0
    assert document.rows[0].cost["prompt_tokens"] == 10


def test_a_second_writer_on_the_same_attempt_directory_is_refused(tmp_path):
    _writer(tmp_path).close()
    with pytest.raises(RowCheckpointError, match="already exists"):
        _writer(tmp_path)


def test_a_sample_settles_once(tmp_path):
    writer = _writer(tmp_path)
    _append(writer, "s1", 1)
    with pytest.raises(RowCheckpointError, match="twice"):
        _append(writer, "s1", 2)


def _lines(path: Path) -> list[bytes]:
    return path.read_bytes().split(b"\n")[:-1]


def _tamper(tmp_path: Path, mutate) -> Path:
    writer = _writer(tmp_path)
    for index, sample_id in enumerate(("s1", "s2", "s3"), start=1):
        _append(writer, sample_id, index)
    writer.close()
    lines = _lines(writer.path)
    lines = mutate(lines)
    writer.path.write_bytes(b"\n".join(lines) + b"\n")
    return writer.path


def test_an_edited_record_breaks_the_chain(tmp_path):
    def edit(lines):
        lines[2] = lines[2].replace(b"answer s2", b"answer XX")
        return lines

    with pytest.raises(RowCheckpointError, match="edited after it was written"):
        read_checkpoint(_tamper(tmp_path, edit))


def test_a_deleted_record_breaks_the_chain(tmp_path):
    with pytest.raises(RowCheckpointError, match="seq"):
        read_checkpoint(_tamper(tmp_path, lambda lines: lines[:2] + lines[3:]))


def test_a_reordered_pair_of_records_breaks_the_chain(tmp_path):
    def swap(lines):
        lines[2], lines[3] = lines[3], lines[2]
        return lines

    with pytest.raises(RowCheckpointError, match="seq"):
        read_checkpoint(_tamper(tmp_path, swap))


def test_a_rehashed_forgery_still_breaks_the_next_link(tmp_path):
    """Rewriting a record AND its own sha256 still fails: the next record
    chains to the original sha."""

    def forge(lines):
        record = json.loads(lines[2])
        record.pop("sha")
        record["output_rows"][0]["text"] = "forged"
        body = rc._canonical(record)
        forged = {**record, "sha": rc._sha256_text(body)}
        lines[2] = rc._canonical(forged).encode("utf-8")
        return lines

    with pytest.raises(RowCheckpointError, match="does not chain"):
        read_checkpoint(_tamper(tmp_path, forge))


def test_a_torn_last_line_is_dropped_but_the_pin_covers_it(tmp_path):
    writer = _writer(tmp_path)
    for index, sample_id in enumerate(("s1", "s2"), start=1):
        _append(writer, sample_id, index)
    writer.close()
    whole = writer.path.read_bytes()
    half = json.dumps({"kind": "row", "sample_id": "s3"})[:20].encode()
    writer.path.write_bytes(whole + half)
    document = read_checkpoint(writer.path)
    assert [row.sample_id for row in document.rows] == ["s1", "s2"]
    assert document.torn_tail_bytes == len(half)
    # the whole-file pin includes the torn tail: a pin taken on the clean file refuses
    with pytest.raises(RowCheckpointError, match="hashes to"):
        read_checkpoint(writer.path, expected_sha256=hashlib.sha256(whole).hexdigest())
    read_checkpoint(writer.path, expected_sha256=document.sha256)


def test_a_newline_terminated_garbage_line_is_a_broken_chain_not_a_torn_tail(tmp_path):
    writer = _writer(tmp_path)
    _append(writer, "s1", 1)
    writer.close()
    writer.path.write_bytes(writer.path.read_bytes() + b"not json\n")
    with pytest.raises(RowCheckpointError, match="malformed"):
        read_checkpoint(writer.path)


def test_per_row_cost_of_one_append_and_fsync_over_1000_rows(tmp_path):
    """The measured cost the report quotes: 1,000 synthetic rows, each with a
    realistic ~8 KB trace and a ~1 KB canonical record, one append + fsync each."""

    writer = _writer(tmp_path)
    started = time.perf_counter()
    for index in range(1000):
        sample_id = f"s{index:04d}"
        writer.append_row(
            sample_id=sample_id, complete=True,
            output_rows=[_row(sample_id, f"flight-{index:04d}")],
            trace_lines=_trace_lines(sample_id, f"flight-{index:04d}", extra=10),
        )
    elapsed = time.perf_counter() - started
    writer.close()
    per_row_ms = 1000.0 * elapsed / 1000
    print(f"ROW_CHECKPOINT_COST total={elapsed:.3f}s per_row={per_row_ms:.3f}ms "
          f"bytes={writer.path.stat().st_size}")
    assert read_checkpoint(writer.path).complete_rows == 1000
    # A row takes seconds of GPU time; one append + fsync must stay far below it.
    assert per_row_ms < 100.0


def test_arm_groups_are_kept_only_when_every_arm_is_present():
    def block(arm_count, present):
        return {
            "schema": "x", "arm_count": arm_count, "delivered_arm_id": present[-1],
            "arms": [{"arm_index": i, "arm_id": arm} for i, arm in enumerate(present)],
        }

    ok = {"sample_id": "s", "supply_variants": block(3, ["a", "b", "c"])}
    assert arm_group_defect(ok) is None
    missing_one = {"sample_id": "s", "supply_variants": block(3, ["a", "b"])}
    assert "arm_count 3" in arm_group_defect(missing_one)
    wrong_delivering = {"sample_id": "s", "supply_variants": {**block(2, ["a", "b"]), "delivered_arm_id": "a"}}
    assert "delivering arm" in arm_group_defect(wrong_delivering)
    gap = {"sample_id": "s", "supply_variants": {**block(2, ["a", "b"]),
           "arms": [{"arm_index": 0, "arm_id": "a"}, {"arm_index": 2, "arm_id": "b"}]}}
    assert "not 0.." in arm_group_defect(gap)
    branches = {"sample_id": "s", "native_episode_receipt": {"perception_branches": {
        "branches": [{"branch_index": 0, "branch_id": "A"}, {"branch_index": 1, "branch_id": "B"}]}}}
    assert arm_group_defect(branches) is None
    branches["native_episode_receipt"]["perception_branches"]["branches"].pop()
    # a lone branch 0 is a consistent (single-branch) group; a hole is not
    branches["native_episode_receipt"]["perception_branches"]["branches"] = [
        {"branch_index": 1, "branch_id": "B"}]
    assert "branch_index" in arm_group_defect(branches)
    assert arm_group_defect({"sample_id": "s"}) is None


def test_a_row_with_an_incomplete_arm_group_is_not_keepable(tmp_path):
    writer = _writer(tmp_path)
    truncated = {**_row("s1", "flight-0001"), "supply_variants": {
        "arm_count": 3, "delivered_arm_id": "b", "arms": [
            {"arm_index": 0, "arm_id": "a"}, {"arm_index": 1, "arm_id": "b"}]}}
    _append(writer, "s1", 1, output_rows=[truncated])
    _append(writer, "s2", 2)
    writer.close()
    document = read_checkpoint(writer.path)
    assert [row.keepable for row in document.rows] == [False, True]
    assert "incomplete arm group" in document.rows[0].keep_defect()


def test_compare_with_sealed_reports_a_missing_extra_and_different_row(tmp_path):
    writer = _writer(tmp_path)
    for index, sample_id in enumerate(("s1", "s2"), start=1):
        _append(writer, sample_id, index)
    _append(writer, "s3", 3, complete=False, output_rows=[], reason="boom")
    writer.close()
    document = read_checkpoint(writer.path)
    sealed = {"s1": _row("s1", "flight-0001"), "s2": {**_row("s2", "flight-0002"), "text": "other"},
              "s3": _row("s3", "flight-0003")}
    report = compare_with_sealed(document, sealed, ["s1", "s2", "s3", "s4"])
    assert report["status"] == "MISMATCH"
    text = " ".join(report["problems"])
    assert "no checkpoint record" in text and "differ from the sealed row" in text
    clean = compare_with_sealed(document, {k: sealed[k] for k in ("s1", "s3")} | {"s2": _row("s2", "flight-0002")},
                                ["s1", "s2", "s3"])
    assert clean["status"] == "VERIFIED" and clean["unrendered_rows"] == 1


def test_the_manifest_block_is_rederived_from_disk(tmp_path):
    writer = _writer(tmp_path)
    _append(writer, "s1", 1)
    writer.close()
    document = read_checkpoint(writer.path)
    block = document.manifest_block()
    verify_manifest_block(block, [_row("s1", "flight-0001")])
    with pytest.raises(RowCheckpointError, match="differs from the sealed outputs row"):
        verify_manifest_block(block, [{**_row("s1", "flight-0001"), "text": "x"}])
    with pytest.raises(RowCheckpointError, match="hashes to"):
        verify_manifest_block({**block, "sha256": "0" * 64}, [_row("s1", "flight-0001")])
    with pytest.raises(RowCheckpointError, match="exactly"):
        verify_manifest_block({**block, "extra": 1}, [])


# ---------------------------------------------------------------------------
# Bundle side: a checkpoint-mode predecessor block is re-derived from the pin.
# ---------------------------------------------------------------------------


def _checkpoint_block(tmp_path: Path, *, kept=("s1", "s2")):
    writer = _writer(tmp_path)
    for index, sample_id in enumerate(("s1", "s2", "s3"), start=1):
        _append(writer, sample_id, index)
    writer.close()
    document = read_checkpoint(writer.path)
    trace_dir = tmp_path / "resume" / "attempt-1"
    trace_dir.mkdir(parents=True)
    trace_path = trace_dir / f"{RUN}.trace.jsonl"
    rows = [row for row in document.rows if row.sample_id in kept]
    trace_path.write_text(kept_trace_text(rows), encoding="utf-8", newline="\n")
    ordered = sorted(kept)
    block = {
        "schema": "saea-resume-predecessor-attempt-v1", "run_id": RUN, "attempt_id": "attempt-1",
        "trace_path": str(trace_path), "trace_sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
        "kept_sample_ids": ordered,
        "kept_sample_ids_sha256": hashlib.sha256(
            json.dumps(ordered, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
        "counts": {"kept": len(ordered), "flown": 3 - len(ordered), "partial": 0},
        "mode": "checkpoint", "checkpoint_path": str(writer.path),
        "checkpoint_sha256": document.sha256,
    }
    return block, trace_path, writer.path


def _manifest(block):
    return {"run_id": RUN, "predecessor_attempt": block}


def test_a_checkpoint_mode_block_verifies_against_its_materialized_trace(tmp_path):
    block, _trace, _ckpt = _checkpoint_block(tmp_path)
    records, kept = verify_predecessor_attempt(
        _manifest(block), split_ids=frozenset({"s1", "s2", "s3"}), attempt_id="attempt-2")
    assert kept == frozenset({"s1", "s2"})
    assert "flight-0001/request" in records
    per_sample, kept_all = verify_predecessor_attempts(
        _manifest(block), split_ids=frozenset({"s1", "s2", "s3"}), attempt_id="attempt-2")
    assert kept_all == kept and set(per_sample) == {"s1", "s2"}


def test_a_checkpoint_mode_block_refuses_a_trace_that_is_not_the_stored_lines(tmp_path):
    block, trace_path, _ckpt = _checkpoint_block(tmp_path)
    forged = trace_path.read_text(encoding="utf-8").replace("answer s1", "answer ZZ")
    trace_path.write_text(forged, encoding="utf-8", newline="\n")
    block = {**block, "trace_sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest()}
    with pytest.raises(BundleError, match="not the kept rows' stored trace lines"):
        verify_predecessor_attempt(
            _manifest(block), split_ids=frozenset({"s1", "s2", "s3"}), attempt_id="attempt-2")


def test_a_checkpoint_mode_block_refuses_a_tampered_checkpoint(tmp_path):
    block, _trace, ckpt = _checkpoint_block(tmp_path)
    ckpt.write_bytes(ckpt.read_bytes().replace(b"answer s1", b"answer s9", 1))
    with pytest.raises(BundleError, match="hashes to"):
        verify_predecessor_attempt(
            _manifest(block), split_ids=frozenset({"s1", "s2", "s3"}), attempt_id="attempt-2")


def test_a_checkpoint_mode_block_cannot_keep_a_sample_the_checkpoint_lacks(tmp_path):
    block, _trace, _ckpt = _checkpoint_block(tmp_path)
    ids = ["s1", "s2", "s4"]
    block = {**block, "kept_sample_ids": ids, "counts": {"kept": 3, "flown": 0, "partial": 0},
             "kept_sample_ids_sha256": hashlib.sha256(
                 json.dumps(ids, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()}
    with pytest.raises(BundleError, match="not a COMPLETE row"):
        verify_predecessor_attempt(
            _manifest(block), split_ids=frozenset({"s1", "s2", "s3", "s4"}), attempt_id="attempt-2")


def test_the_mode_a_block_shape_is_unchanged(tmp_path):
    block, _trace, _ckpt = _checkpoint_block(tmp_path)
    plain = {k: v for k, v in block.items() if k not in ("mode", "checkpoint_path", "checkpoint_sha256")}
    # a mode-A block still verifies as a plain trace (no checkpoint involved)
    verify_predecessor_attempt(
        _manifest(plain), split_ids=frozenset({"s1", "s2", "s3"}), attempt_id="attempt-2")
    # but the checkpoint fields without the mode are refused
    with pytest.raises(BundleError, match="exactly"):
        verify_predecessor_attempt(
            _manifest({**plain, "checkpoint_sha256": block["checkpoint_sha256"]}),
            split_ids=frozenset({"s1", "s2", "s3"}), attempt_id="attempt-2")


# ---------------------------------------------------------------------------
# The resume prelaunch gate takes the mode-B declaration.
# ---------------------------------------------------------------------------


def _gate():
    import sys

    checks = Path(__file__).resolve().parents[2] / "scripts" / "checks"
    if str(checks) not in sys.path:
        sys.path.insert(0, str(checks))
    import resume_prelaunch_gate_check

    return resume_prelaunch_gate_check


def _gate_repo(tmp_path: Path, resume_from) -> tuple[Path, Path]:
    repo, data = tmp_path / "repo", tmp_path / "data"
    config = repo / "configs" / "experiment" / "exp.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"cells": [
        {"cell_id": "cell", "run_id": RUN, "resume_from": resume_from}]}), encoding="utf-8")
    return repo, data


def test_the_prelaunch_gate_accepts_a_checkpoint_declaration_and_checks_its_hash(tmp_path, capsys):
    gate = _gate()
    attempt_dir = tmp_path / "data" / "runs" / RUN / "attempt-1"
    writer = RowCheckpointWriter(attempt_dir, RUN, "attempt-1", identity={})
    _append(writer, "s1", 1)
    _append(writer, "s2", 2)
    writer.close()
    pin = rc.sha256_file(writer.path)
    repo, data = _gate_repo(tmp_path, {"attempt_id": "attempt-1", "checkpoint_sha256": pin})
    arguments = ["--repo-root", str(repo), "--data-root", str(data), "--experiment", "exp", "--cell", "cell"]
    assert gate.main(arguments) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["mode"] == "checkpoint" and receipt["rows_checked"] == 2
    assert receipt["rows_failing"] == 0 and receipt["sealed_twice"] == 0
    # a wrong pin is refused (exit 2), by name
    repo, data = _gate_repo(tmp_path / "again", {"attempt_id": "attempt-1", "checkpoint_sha256": "0" * 64})
    shutil_target = tmp_path / "again" / "data" / "runs" / RUN
    shutil_target.parent.mkdir(parents=True)
    import shutil

    shutil.copytree(tmp_path / "data" / "runs" / RUN, shutil_target)
    arguments = ["--repo-root", str(repo), "--data-root", str(data), "--experiment", "exp", "--cell", "cell"]
    assert gate.main(arguments) == 2
    assert "hashes to" in capsys.readouterr().err
