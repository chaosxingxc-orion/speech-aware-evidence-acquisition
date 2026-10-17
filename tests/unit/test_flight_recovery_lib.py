"""The generic recovery re-registration library (``scripts/flights/lib/recovery.py``). Model-free and synthetic: attempt records are built in a temp data root."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "lib", REPO / "scripts" / "flights" / "direct"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import direct_fb_family as dfb  # noqa: E402
import recovery as rcv  # noqa: E402

RUN, ATT = "SAEA-TEST-RUN-V1", "attempt-test-generation-v1"
FIT_RUN, FIT_ATT = "SAEA-TEST-FIT-V1", "attempt-test-fit-v1"


def _attempt(root: Path, calls=1204, audio=3298.2618750000015, state="OPENED", run=RUN, attempt=ATT) -> Path:
    path = root / "attempts" / run / f"{attempt}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"actual": {"audio_seconds": audio, "calls": calls}, "attempt_id": attempt, "carrier_lock_key": "slurp",
                                "reserved": {"audio_seconds": 50477.0, "calls": 17280}, "run_id": run, "schema": "saea-attempt-v1", "state": state}), encoding="utf-8")
    return path


def _record(snapshot: dict) -> dict:
    return {
        "recovery_index": 1, "recovered_at": "2026-10-14", "ledger_title": "the test re-registration", "agent": "the test agent",
        "predecessor_attempt_id": ATT, "predecessor_fit_run_id": FIT_RUN, "predecessor_fit_attempt_id": FIT_ATT, "fit_predecessor_phrase": "never opened",
        "predecessor_state": "OPENED, killed", "predecessors": [rcv.predecessor_from_snapshot(snapshot)], "reason": "r", "root_cause": "infra",
        "amendment": "a", "fix": "none", "unchanged": "u", "rule": "A second failure closes the cell.", "fit_cap_rule": "structural",
    }


def test_the_spend_is_read_from_the_attempt_record_not_typed(tmp_path):
    _attempt(tmp_path)
    snap = rcv.snapshot_predecessor(tmp_path, RUN, ATT)
    assert snap["schema"] == rcv.SNAPSHOT_SCHEMA and snap["state"] == "OPENED"
    assert snap["actual_calls"] == 1204 and snap["actual_audio_seconds"] == 3298.2618750000015
    assert snap["reserved_calls"] == 17280 and snap["attempt_record_relpath"] == f"attempts/{RUN}/{ATT}.json" and len(snap["attempt_record_sha256"]) == 64
    entry = rcv.predecessor_from_snapshot(snap)
    assert entry == {"attempt_id": ATT, "state": "OPENED", "contacts_spent": 1204, "speech_seconds_spent": 3298.2618750000015}


def test_fit_progress_counts_envelopes_by_listing_only(tmp_path):
    prepared = tmp_path / "prepared" / FIT_RUN / FIT_ATT
    prepared.mkdir(parents=True)
    for n in range(3):
        (prepared / f"{n:064x}.request-fit.json").write_text("{}", encoding="utf-8")
        (prepared / f"{n:064x}.request-fit.json.contacts.jsonl").write_text("", encoding="utf-8")
    progress = rcv.read_fit_progress(tmp_path, FIT_RUN, FIT_ATT)
    assert progress == {"run_id": FIT_RUN, "attempt_id": FIT_ATT, "attempt_record_present": False, "prepared_dir_present": True, "prepared_request_fit_envelopes": 3}
    assert rcv.read_fit_progress(tmp_path, "OTHER", "x")["prepared_dir_present"] is False


def test_verify_refuses_a_predecessor_that_is_still_spending(tmp_path):
    _attempt(tmp_path)
    snap = rcv.snapshot_predecessor(tmp_path, RUN, ATT)
    assert rcv.verify_predecessor_snapshot(snap, tmp_path)["actual_calls"] == 1204
    _attempt(tmp_path, state="ABORTED")                                    # an abort rewrites state and bytes, not the realised spend
    assert rcv.verify_predecessor_snapshot(snap, tmp_path)["state"] == "ABORTED"
    _attempt(tmp_path, calls=1300)
    with pytest.raises(rcv.RecoveryError, match="still spending"):
        rcv.verify_predecessor_snapshot(snap, tmp_path)


def test_a_malformed_or_missing_attempt_record_is_refused(tmp_path):
    with pytest.raises(rcv.RecoveryError, match="no attempt record"):
        rcv.read_predecessor_attempt(tmp_path, RUN, ATT)
    path = _attempt(tmp_path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["actual"]["calls"] = "lots"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(rcv.RecoveryError, match="malformed actual"):
        rcv.read_predecessor_attempt(tmp_path, RUN, ATT)


def test_cumulative_budget_is_the_original_plan_plus_the_realised_spend(tmp_path):
    _attempt(tmp_path)
    snap = rcv.snapshot_predecessor(tmp_path, RUN, ATT)
    recs = {"arm": _record(snap)}
    assert rcv.predecessor_spend(recs, "arm") == (1204, 3298.2618750000015) and rcv.predecessor_spend(recs, "smoke") == (0, 0.0)
    assert rcv.cumulative_budget(recs, "arm", 17280, 50477) == (18484, 53776)               # audio rounded UP (50477 + 3298.26 = 53775.26)
    assert rcv.cumulative_budget(recs, "smoke", 64, 100) == (64, 100)
    caps = {"generation_calls_cap": 18484, "repeated_speech_audio_seconds_cap": 53776, "fit_endpoint_calls_cap": 43200}
    budget = rcv.recovery_budget(recs, "arm", caps)
    assert budget["original_plan"] == {"planned_model_calls": 17280, "planned_speech_audio_seconds": 50477}
    assert budget["failed_attempt_spend"]["attempt_ids"] == [ATT] and budget["cumulative_plan"] == {"planned_model_calls": 18484, "planned_speech_audio_seconds": 53776}


def test_the_lifted_helpers_agree_with_the_direct_fb_family():
    """The lib is the direct_fb mechanism lifted: same suffix, same spend, same cumulative arithmetic, same plan names."""

    for key in dfb.ALL_KEYS:
        assert rcv.rec_suffix(dfb.RECOVERIES, key) == dfb.rec_suffix(key)
        assert rcv.predecessor_spend(dfb.RECOVERIES, key) == dfb.predecessor_spend(key)
        assert rcv.cumulative_budget(dfb.RECOVERIES, key, 1080, 3155) == dfb.cumulative_budget(key, 1080, 3155)
        assert rcv.plan_file_name(f"{key}-", "generation", key in dfb.RECOVERIES) == dfb.plan_file_name(key, "generation")
        assert rcv.plan_file_name(f"{key}-", "fit", key in dfb.RECOVERIES) == dfb.plan_file_name(key, "fit")
        assert rcv.superseded_plan_file_names(f"{key}-", key in dfb.RECOVERIES) == dfb.superseded_plan_file_names(key)
        if key in dfb.RECOVERIES:
            rcv.validate_recovery(dfb.RECOVERIES[key])


def test_plan_file_names():
    assert rcv.plan_file_name("", "generation", True) == "generation-plan-registered-rec1-v1.json"
    assert rcv.plan_file_name("smoke-", "fit", False) == "smoke-fit-plan-registered-v1.json"
    assert rcv.superseded_plan_file_names("", True) == ["generation-plan-registered-v1.json", "fit-plan-registered-v1.json"]
    assert rcv.superseded_plan_file_names("", False) == []


def test_validate_recovery_names_what_is_missing(tmp_path):
    _attempt(tmp_path)
    good = _record(rcv.snapshot_predecessor(tmp_path, RUN, ATT))
    rcv.validate_recovery(good)
    with pytest.raises(rcv.RecoveryError, match="misses keys"):
        rcv.validate_recovery({k: v for k, v in good.items() if k != "root_cause"})
    with pytest.raises(rcv.RecoveryError, match="not among the predecessors"):
        rcv.validate_recovery({**good, "predecessor_attempt_id": "other"})


def test_persisted_recovery_carries_the_persisted_subset_and_its_own_stamp(tmp_path):
    _attempt(tmp_path)
    recs = {"arm": _record(rcv.snapshot_predecessor(tmp_path, RUN, ATT))}
    block = rcv.persisted_recovery(recs, "arm", "2026-10-14T16:30:00+00:00", "abc123")
    assert set(block) == set(rcv.PERSISTED_RECOVERY_KEYS) | {"registered_at_utc", "base_commit"}
    assert "fix" not in block and "agent" not in block and block["base_commit"] == "abc123" and list(block) == sorted(block)


def _block(recs, tmp_name="x"):
    caps = {"generation_calls_cap": 18484, "repeated_speech_audio_seconds_cap": 53776, "fit_endpoint_calls_cap": 43200, "gpu_hours_fit_inclusive": 41.4}
    return rcv.recovery_ledger_block(
        recs, "arm", mark="## Cell TEST recovery rec1: ", authority="owner test authority", package="docs/readiness/test", role="test arm", run=RUN,
        fit_run="SAEA-TEST-FIT-REC1-V1", attempt="attempt-test-generation-rec1-v1", fit_attempt="attempt-test-fit-rec1-v1", session="serving-test", scope="scope text",
        fit_scope="fit scope text", model_tool="model", carrier="slurp TRAIN Fold B 1,080", split_hash="a" * 64, caps=caps, config_hash="c" * 64,
        protocol_hash="d" * 64, registered_at="2026-10-14T16:30:00+00:00", base_commit="abc123", worktree="/wt", branch="br",
        plan_names=("generation-plan-registered-rec1-v1.json", "fit-plan-registered-rec1-v1.json"), inherited="inherited")


def test_the_ledger_block_has_the_266e_form(tmp_path):
    _attempt(tmp_path)
    recs = {"arm": _record(rcv.snapshot_predecessor(tmp_path, RUN, ATT))}
    block = _block(recs)
    lines = block.split("\n")
    assert lines[1].startswith("## Cell TEST recovery rec1: the test re-registration (DRAFT, root countersignature pending)")
    header = "| " + " | ".join(rcv.LEDGER_COLUMN_NAMES) + " |"
    assert header in lines and "| " + " | ".join("---" for _ in rcv.LEDGER_COLUMN_NAMES) + " |" in lines
    rows = [ln for ln in lines if ln.startswith("| 2026")]
    assert len(rows) == 2 and all(r.count("|") == 16 for r in rows)
    gen, fit = rows
    assert f"| {RUN} |" in gen and "| SAEA-TEST-FIT-REC1-V1 |" in fit and "| no | 18484 | 53776 | 41.4 |" in gen and "| no | 43200 | 53776 | 41.4 |" in fit
    assert "DRAFT, root countersignature pending" in gen and "SUPERSEDES the first-attempt row" in gen
    assert "17280 + 1204 = 18484 calls" in gen and "50477 + 3298.26 = 53776 speech-seconds" in gen
    assert f"supersedes FIT run {FIT_RUN} / attempt {FIT_ATT}, never opened" in fit and "docs/readiness/test/generation-plan-registered-rec1-v1.json" in gen
    assert "root countersigned" not in block and "\n\n" in block


def test_the_ledger_block_append_is_idempotent_on_the_rec1_attempt_id(tmp_path):
    _attempt(tmp_path)
    recs = {"arm": _record(rcv.snapshot_predecessor(tmp_path, RUN, ATT))}
    ledger = tmp_path / "ledger.md"
    ledger.write_bytes(b"# Ledger\n\n| a |\n")
    block = _block(recs)
    assert rcv.append_recovery_ledger_block(ledger, block, "attempt-test-generation-rec1-v1") is True
    once = ledger.read_bytes()
    assert rcv.append_recovery_ledger_block(ledger, block, "attempt-test-generation-rec1-v1") is False and ledger.read_bytes() == once
    assert once.startswith(b"# Ledger\n\n| a |\n") and b"\r" not in once


def test_countersign_text_names_the_spend_and_the_receipt_clause(tmp_path):
    _attempt(tmp_path)
    recs = {"arm": _record(rcv.snapshot_predecessor(tmp_path, RUN, ATT))}
    text = rcv.countersign_text(recs, "arm", authority="owner X", role="test arm", label="the test arm", attempt="a-rec1", fit_run="F-REC1", fit_attempt="f-rec1",
                                receipt_clause="the receipt is re-minted", tail="the READ row stays a draft")
    assert text.startswith("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp>") and "1204 calls and 3298.26 speech-seconds spent" in text
    assert "a-rec1" in text and "F-REC1" in text and "the receipt is re-minted" in text and text.endswith("the READ row stays a draft)")


def test_recovery_section_text(tmp_path):
    _attempt(tmp_path)
    recs = {"arm": _record(rcv.snapshot_predecessor(tmp_path, RUN, ATT))}
    caps = {"generation_calls_cap": 18484, "repeated_speech_audio_seconds_cap": 53776}
    text = rcv.recovery_section(recs, "arm", role="test arm", run=RUN, attempt="a-rec1", fit_run="F-REC1", fit_attempt="f-rec1", caps=caps,
                                plan_names=("g-rec1.json", "f-rec1.json"))
    assert "## Recovery rec1: the test arm" in text and "17280 + 1204 = 18484 calls" in text and "`g-rec1.json`, `f-rec1.json`" in text
    assert "A second failure closes the cell." in text


def test_cli_snapshot_and_verify(tmp_path, capsys):
    _attempt(tmp_path)
    out = tmp_path / "snap.json"
    assert rcv.main(["snapshot", "--data-root", str(tmp_path), "--run-id", RUN, "--attempt-id", ATT, "--out", str(out)]) == 0
    assert json.loads(capsys.readouterr().out)["actual_calls"] == 1204
    assert rcv.main(["verify", "--data-root", str(tmp_path), "--snapshot", str(out)]) == 0
    assert json.loads(capsys.readouterr().out)["verified"] is True
    assert rcv.load_snapshot(out)["attempt_id"] == ATT
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(rcv.RecoveryError):
        rcv.load_snapshot(bad)


# ---- a second recovery (rec2) needs an explicit owner exception ------------------------------------------------------------------------------


def _second(tmp_path: Path, **overrides) -> dict:
    first = rcv.snapshot_predecessor(_root_with(tmp_path, ATT, 1204, 3298.5), RUN, ATT)
    stopped = rcv.snapshot_predecessor(_root_with(tmp_path, "attempt-test-generation-rec1-v1", 10298, 30101.2), RUN, "attempt-test-generation-rec1-v1")
    record = _record(stopped)
    record.update(recovery_index=2, predecessors=[rcv.predecessor_from_snapshot(first), rcv.predecessor_from_snapshot(stopped)],
                  predecessor_attempt_id=stopped["attempt_id"], owner_exception="owner ruling 999 B of 2099-01-01", flown_phrase="resumed in mode A from the stopped attempt")
    record.update(overrides)
    return record


def _root_with(root: Path, attempt: str, calls: int, audio: float) -> Path:
    _attempt(root, calls=calls, audio=audio, attempt=attempt)
    return root


def test_a_second_record_without_an_owner_exception_is_refused(tmp_path):
    record = _second(tmp_path)
    rcv.validate_recovery(record)
    for bad in ("", "   ", None):
        broken = dict(record, owner_exception=bad)
        with pytest.raises(rcv.RecoveryError, match="owner_exception"):
            rcv.validate_recovery(broken)
    del_missing = {k: v for k, v in record.items() if k != "owner_exception"}
    with pytest.raises(rcv.RecoveryError, match="owner_exception"):
        rcv.validate_recovery(del_missing)
    with pytest.raises(rcv.RecoveryError, match="every earlier attempt"):
        rcv.validate_recovery(dict(record, predecessors=record["predecessors"][1:]))
    with pytest.raises(rcv.RecoveryError, match="positive integer"):
        rcv.validate_recovery(dict(record, recovery_index=0))


def test_rec2_markers_plan_names_caps_and_texts_follow_the_index(tmp_path):
    record = _second(tmp_path)
    recs = {"arm": record}
    assert rcv.rec_suffix(recs, "arm") == "-rec2" and rcv.rec_suffix(recs, "smoke") == ""
    assert rcv.plan_file_name("", "generation", 2) == "generation-plan-registered-rec2-v1.json"
    assert rcv.plan_file_name("", "generation", True) == "generation-plan-registered-rec1-v1.json" and rcv.plan_file_name("", "fit", False) == "fit-plan-registered-v1.json"
    assert rcv.superseded_plan_file_names("", 1) == ["generation-plan-registered-v1.json", "fit-plan-registered-v1.json"]
    assert rcv.superseded_plan_file_names("", 2) == ["generation-plan-registered-v1.json", "fit-plan-registered-v1.json",
                                                     "generation-plan-registered-rec1-v1.json", "fit-plan-registered-rec1-v1.json"]
    assert rcv.superseded_plan_file_names("x-", 0) == []
    assert rcv.predecessor_spend(recs, "arm") == (11502, 3298.5 + 30101.2) and rcv.cumulative_budget(recs, "arm", 17280, 50477) == (28782, 83877)
    assert rcv.persisted_recovery(recs, "arm", "2026-10-17T00:00:00Z", "abc")["owner_exception"] == "owner ruling 999 B of 2099-01-01"
    caps = {"generation_calls_cap": 28782, "repeated_speech_audio_seconds_cap": 83877, "fit_endpoint_calls_cap": 43200, "gpu_hours_fit_inclusive": 41.4}
    section = rcv.recovery_section(recs, "arm", role="column", run=RUN, attempt="a2", fit_run="F2", fit_attempt="fa2", caps=caps, plan_names=("g2", "f2"))
    assert "## Recovery rec2: the column" in section and "17280 + 11502 = 28782 calls" in section and "Owner exception: owner ruling 999 B of 2099-01-01" in section
    assert "Resumed in mode A from the stopped attempt under generation attempt `a2`" in section and ATT in section and "attempt-test-generation-rec1-v1" in section
    text = rcv.countersign_text(recs, "arm", authority="auth", role="column", label="L", attempt="a2", fit_run="F2", fit_attempt="fa2", receipt_clause="rc", tail="t")
    assert "RECOVERY rec2" in text and "owner ruling 999 B" in text and "11502 calls" in text and ATT in text and "attempt-test-generation-rec1-v1" in text
    block = rcv.recovery_ledger_block(recs, "arm", mark="## M: ", authority="auth", package="pkg", role="column", run=RUN, fit_run="F2", attempt="a2", fit_attempt="fa2",
                                      session="s", scope="sc", fit_scope="fs", model_tool="m", carrier="c", split_hash="h", caps=caps, config_hash="ch",
                                      protocol_hash="ph", registered_at="2026-10-17T00:00:00Z", base_commit="abc", worktree="/wt", branch="br",
                                      plan_names=("g2", "f2"), inherited="i")
    rows = [ln for ln in block.splitlines() if ln.startswith("| 2026")]
    assert len(rows) == 2 and "SUPERSEDES the rec1 row" in rows[0] and "17280 + 11502 = 28782 calls" in rows[0] and "rec2 identities" in rows[1]
    assert ATT in rows[0] and "attempt-test-generation-rec1-v1" in rows[0]


def test_the_trace_pin_is_read_hashed_and_verified(tmp_path):
    import hashlib

    _attempt(tmp_path)
    attempt_dir = tmp_path / "runs" / RUN / ATT
    attempt_dir.mkdir(parents=True)
    (attempt_dir / f"{RUN}.trace.jsonl").write_bytes(b'{"a": 1}\n')
    (attempt_dir / f"{RUN}.rows.ckpt.jsonl").write_bytes(b"ckpt\n")
    snap = rcv.snapshot_predecessor(tmp_path, RUN, ATT, trace_pin=True)
    assert snap["trace"]["trace_sha256"] == hashlib.sha256(b'{"a": 1}\n').hexdigest() and snap["trace"]["checkpoint_sha256"] == hashlib.sha256(b"ckpt\n").hexdigest()
    assert rcv.verify_trace_pin(snap, tmp_path)["trace_bytes"] == 9
    (attempt_dir / f"{RUN}.trace.jsonl").write_bytes(b'{"a": 2}\n')
    with pytest.raises(rcv.RecoveryError, match="predecessor moved"):
        rcv.verify_trace_pin(snap, tmp_path)
    with pytest.raises(rcv.RecoveryError, match="pins no trace"):
        rcv.verify_trace_pin(rcv.snapshot_predecessor(tmp_path, RUN, ATT), tmp_path)
    assert "trace" not in rcv.snapshot_predecessor(tmp_path, RUN, ATT)
