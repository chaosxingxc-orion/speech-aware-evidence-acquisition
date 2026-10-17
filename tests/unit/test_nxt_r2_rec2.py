"""NX-T R2 rec2: the RESUME of the aborted rec1 column attempt (owner ruling 328 of 2026-10-17), model-free.

Checks the family's second recovery record (index, exception, run-cumulative caps, resume pin and counts read from the committed snapshot, the computed resume mode),
its refusals, the writer's rec2 package and ledger form, the chain's ``arm-only`` resume precondition (executed in process against a synthetic data root) and the
snapshot / mode / replay-proof tools. Nothing here touches the data root, a model or the GPU.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "nx", REPO / "scripts" / "flights" / "direct", REPO / "scripts" / "flights" / "tfrl", REPO / "scripts" / "flights" / "lib",
               REPO / "scripts" / "analysis", REPO / "scripts" / "checks", REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import nxt_r2_family as fam  # noqa: E402
import nxt_r2_write_registration as writer  # noqa: E402
import slurp_nxt_thinking_budget_column_read as reader  # noqa: E402

PKG = REPO / fam.PACKAGE


def _load(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def _snapshots() -> tuple[dict, dict]:
    first, stopped = (_load(rel) for rel in fam.PREDECESSOR_SNAPSHOTS["arm"])
    return first, stopped


def _input() -> dict:
    return _load(fam.RECOVERY_INPUTS["arm"][1])


def _plan(kind: str) -> dict:
    return json.loads((PKG / fam.plan_file_name("arm", kind)).read_text(encoding="utf-8"))


# ---- the family record ---------------------------------------------------------------------------------------------------------------------


def test_the_rec2_record_is_index_two_under_the_owner_exception_with_both_earlier_attempts():
    first, stopped = _snapshots()
    rec = fam.recovery("arm")
    assert rec["recovery_index"] == 2 and fam.recovery_index("arm") == 2 and fam.recovery_index("smoke") == 0 and rec["owner_exception"] == "owner ruling 328 of 2026-10-17"
    assert [r["recovery_index"] for r in fam.RECOVERY_HISTORY["arm"]] == [1, 2] and fam.RECOVERIES["arm"] is fam.RECOVERY_HISTORY["arm"][1]
    assert [p["attempt_id"] for p in rec["predecessors"]] == [first["attempt_id"], stopped["attempt_id"]]
    assert first["attempt_id"].endswith("-generation-v1") and stopped["attempt_id"].endswith("-generation-rec1-v1") and stopped["state"] == "ABORTED"
    assert (first["actual_calls"], stopped["actual_calls"]) == (42, 172) and stopped["fit"]["run_id"].endswith("-FIT-REC1-V1")
    assert rec["predecessor_attempt_id"] == stopped["attempt_id"] and rec["predecessor_fit_run_id"] == stopped["fit"]["run_id"]
    # the rec1 record stays readable as history, with its own (first-attempt) accounting and no exception
    rec1 = fam.RECOVERY_HISTORY["arm"][0]
    assert [p["contacts_spent"] for p in rec1["predecessors"]] == [42] and "owner_exception" not in rec1 and "resume_from" not in rec1
    fam.rcv.validate_recovery(rec1)
    fam.rcv.validate_recovery(rec)


def test_the_run_cumulative_caps_carry_both_earlier_attempts_spend():
    first, stopped = _snapshots()
    assert fam.predecessor_spend("arm") == (42 + 172, first["actual_audio_seconds"] + stopped["actual_audio_seconds"]) and fam.predecessor_spend("smoke") == (0, 0.0)
    assert fam.generation_calls("arm") == 11880 + 42 + 172 == 12094 and fam.original_generation_calls("arm") == 11880
    assert fam.cell_audio_cap("arm") == 35317 == fam.cell_audio_cap("arm") and fam.audio_cap("arm") == 34703
    assert fam.history_caps("arm", 1, {})["generation_calls_cap"] == 11880 + 42 and fam.history_caps("arm", 1, {})["repeated_speech_audio_seconds_cap"] == 34836
    # the GPU-hour ceiling is unchanged by the recovery
    assert fam.CELLS["arm"]["gpu_hours"] == fam.planned_gpu_hours(fam.ROWS)


def test_the_resume_pin_and_counts_are_read_from_the_snapshot_never_typed():
    _first, stopped = _snapshots()
    rec, doc = fam.recovery("arm"), _input()
    mode = doc["resume_mode"]
    assert mode in ("checkpoint", "trace")
    counts = rec["resume_counts"]
    assert counts == stopped["resume"][mode]["counts"] and counts["kept"] + counts["flown"] == counts["roster"] == fam.ROWS
    assert counts["kept"] > 0 and counts["flown"] > 0
    letter = {"checkpoint": "B", "trace": "A"}[mode]
    assert rec["resume_mode"] == f"resume-mode-{letter}-keep-{counts['kept']}-fly-{counts['flown']}"
    key = {"checkpoint": "checkpoint_sha256", "trace": "trace_sha256"}[mode]
    assert rec["resume_from"] == {"attempt_id": stopped["attempt_id"], key: stopped["trace"][key]} and re.fullmatch(r"[0-9a-f]{64}", rec["resume_from"][key])
    # both scans of the stopped attempt agree on the rows they keep
    assert stopped["resume"]["trace"]["kept_sample_ids_sha256"] == stopped["resume"]["checkpoint"]["kept_sample_ids_sha256"]
    assert stopped["resume"]["trace"]["counts"]["kept"] == stopped["resume"]["checkpoint"]["counts"]["kept"]


def test_the_resume_mode_is_the_computed_one_checkpoint_only_when_the_code_and_the_header_binding_both_hold():
    _first, stopped = _snapshots()
    doc = _input()
    evidence = doc["resume_mode_evidence"]
    header = stopped["resume"]["checkpoint_header"]
    code_same = stopped["mode_inputs"]["implementation_differing_modules"] == [] and not evidence["modules_differing_by_git_diff"]
    hash_same = evidence["rec2_protocol_hash"] == header["protocol_hash"] == evidence["checkpoint_header_protocol_hash"]
    assert evidence["protocol_hash_equal"] is hash_same
    assert (doc["resume_mode"] == "checkpoint") == (code_same and hash_same and evidence["checkpoint_reader_refusal"] is None)
    assert doc["resume_mode_basis"] and evidence["rec1_flight_commit"] == "9790c071f"
    # the writer's offline guard agrees with the recorded mode: the rec2 registration's own protocol hash is what the checkpoint reader would compare
    ids = writer.identities(REPO)
    assert writer.assert_resume_mode_is_launchable(REPO, ids) is None
    if doc["resume_mode"] == "trace":
        assert ids["arm"]["protocol_hash"] != header["protocol_hash"]


def test_a_mode_b_declaration_is_refused_when_the_protocol_hash_differs(monkeypatch):
    rec = copy.deepcopy(fam.recovery("arm"))
    rec["resume_from"] = {"attempt_id": rec["predecessor_attempt_id"], "checkpoint_sha256": "a" * 64}
    monkeypatch.setitem(fam.RECOVERIES, "arm", rec)
    ids = writer.identities(REPO)
    with pytest.raises(SystemExit, match="mode B refused"):
        writer.assert_resume_mode_is_launchable(REPO, ids)
    _first, stopped = _snapshots()
    header = stopped["resume"]["checkpoint_header"]
    same = {"arm": {"protocol_hash": header["protocol_hash"], "split_identity_hash": header["split_identity_hash"]}}
    assert writer.assert_resume_mode_is_launchable(REPO, same) is None


def test_the_builder_refuses_a_malformed_input_a_bad_mode_and_a_changed_code_identity():
    first, stopped = _snapshots()
    doc = _input()
    for key in fam.RECOVERY_INPUT_KEYS_REC2:
        broken = {k: v for k, v in doc.items() if k != key}
        with pytest.raises(ValueError, match=key):
            fam.build_arm_rec2(broken, first, stopped)
    with pytest.raises(ValueError, match="resume_mode"):
        fam.build_arm_rec2(dict(doc, resume_mode="both"), first, stopped)
    changed = copy.deepcopy(stopped)
    changed["mode_inputs"]["implementation_differing_modules"] = ["runner"]
    with pytest.raises(ValueError, match="mode B"):
        fam.build_arm_rec2(dict(doc, resume_mode="checkpoint"), first, changed)
    bad_counts = copy.deepcopy(stopped)
    bad_counts["resume"]["trace"]["counts"]["flown"] += 1
    with pytest.raises(ValueError, match="do not add up"):
        fam.build_arm_rec2(dict(doc, resume_mode="trace"), first, bad_counts)
    # mode B builds when the code identity is unchanged: the pin is the checkpoint sha256 and the text names mode B
    b = fam.build_arm_rec2(dict(doc, resume_mode="checkpoint", resume_mode_basis="the identity holds."), first, stopped)
    assert set(b["resume_from"]) == {"attempt_id", "checkpoint_sha256"} and b["resume_from"]["checkpoint_sha256"] == stopped["trace"]["checkpoint_sha256"]
    assert b["resume_mode"].startswith("resume-mode-B-") and "mode B (row checkpoint)" in b["flown_phrase"] and b["resume_counts"] == stopped["resume"]["checkpoint"]["counts"]
    fam.rcv.validate_recovery(b)


def test_a_second_recovery_record_is_refused_without_the_owner_exception():
    rec = copy.deepcopy(fam.recovery("arm"))
    for bad in (None, "", "   "):
        broken = {k: v for k, v in rec.items() if k != "owner_exception"}
        if bad is not None:
            broken["owner_exception"] = bad
        with pytest.raises(fam.rcv.RecoveryError, match="owner_exception"):
            fam.rcv.validate_recovery(broken)
    with pytest.raises(fam.rcv.RecoveryError, match="every earlier attempt"):
        fam.rcv.validate_recovery(dict(rec, predecessors=rec["predecessors"][-1:]))


def test_the_eligible_ids_extend_the_rec1_receipts_list_by_exactly_the_rec2_fit_run_and_attempts():
    run, fit1, fit2 = fam.CELLS["arm"]["run"], fam.RECOVERY_HISTORY["arm"][1]["predecessor_fit_run_id"], fam.CELLS["arm"]["fit_run"]
    ids = fam.eligible_run_ids()
    rec1_list = ids[:-1]
    assert ids[-1] == fit2 and fit2.endswith("-FIT-REC2-V1") and rec1_list[-1].endswith("-FIT-REC1-V1") and len(ids) == 6 and len(set(ids)) == 6
    assert ids[:4] == [fam.CELLS["smoke"]["run"], fam.CELLS["smoke"]["fit_run"], run, ids[3]] and ids[3].endswith("-FIT-V1")
    attempts = fam.eligible_attempt_ids()
    assert len(attempts) == 8 and len(set(attempts)) == 8 and attempts[-2:] == [fam.CELLS["arm"]["attempt"], fam.CELLS["arm"]["fit_attempt"]]
    assert fam.CELLS["arm"]["attempt"].endswith("-generation-rec2-v1") and fam.CELLS["arm"]["fit_attempt"].endswith("-fit-rec2-v1") and fit1 == rec1_list[-1]


# ---- the package and the writer ------------------------------------------------------------------------------------------------------------


def test_the_rec2_plans_carry_the_recovery_block_the_resume_blocks_the_caps_and_the_replay_proof():
    gen, fit = _plan("generation"), _plan("fit")
    assert fam.plan_file_name("arm", "generation") == "generation-plan-registered-rec2-v1.json" and fam.plan_file_name("arm", "fit") == "fit-plan-registered-rec2-v1.json"
    assert fam.superseded_plan_file_names("arm") == ["generation-plan-registered-v1.json", "fit-plan-registered-v1.json",
                                                      "generation-plan-registered-rec1-v1.json", "fit-plan-registered-rec1-v1.json"]
    for stale in fam.superseded_plan_file_names("arm"):
        assert not (PKG / stale).exists()
    assert gen["execution_plan"]["planned_model_calls"] == 12094 and gen["execution_plan"]["planned_speech_audio_seconds"] == 35317
    assert gen["execution_plan"]["attempt_id"] == fam.CELLS["arm"]["attempt"] and fit["execution_plan"]["run_id"] == fam.CELLS["arm"]["fit_run"]
    assert fit["execution_plan"]["planned_model_calls"] == fam.fit_contact_cap(fam.ROWS)                  # the FIT cap is structural, not run-cumulative
    assert gen["recovery"]["recovery_index"] == 2 and gen["recovery"]["owner_exception"] == "owner ruling 328 of 2026-10-17"
    assert gen["recovery"]["resume_from"] == fam.recovery("arm")["resume_from"] and gen["resume_from"] == fam.recovery("arm")["resume_from"] and "resume_from" not in fit
    budget = gen["resume_budget"]
    counts = fam.recovery("arm")["resume_counts"]
    assert (budget["kept_rows"], budget["flown_rows"]) == (counts["kept"], counts["flown"]) and budget["flown_worst_case_program_contacts"] == counts["flown"] * fam.CONTACTS_PER_ROW
    assert budget["run_cumulative_worst_case_calls"] <= budget["cap_calls"] and budget["headroom_calls"] > 0 and budget["gpu_hours_ceiling"] == fam.CELLS["arm"]["gpu_hours"]
    assert budget["mode"] == _input()["resume_mode"]
    proof = gen["resume_replay_proof"]
    assert proof["rows_failing"] == 0 and proof["sealed_twice"] == 0 and proof["rows_checked"] == counts["kept"] and proof["model_contacts"] == 0
    assert re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{7,12}", proof["code_commit"]) and re.fullmatch(r"[0-9a-f]{64}", proof["checker_sha256"])
    pinned = proof["predecessor_attempts"][0]
    assert pinned["trace_sha256"] == gen["resume_from"]["trace_sha256"] and pinned["complete"] == counts["kept"] and pinned["rows_failing"] == 0
    for name in fam.RECOVERIES["arm"]["predecessors"]:
        assert name["attempt_id"] in gen["recovery_budget"]["failed_attempt_spend"]["attempt_ids"]
    cell = _load(f"configs/experiment/{fam.CELLS['arm']['cell']}.json")["cells"][0]
    assert cell["resume_from"] == fam.recovery("arm")["resume_from"] and cell["attempt_id"] == fam.CELLS["arm"]["attempt"]
    assert "resume_from" not in _load(f"configs/experiment/{fam.CELLS['smoke']['cell']}.json")["cells"][0]


def test_protocol_facts_and_draft_receipt_carry_both_snapshots_and_the_resume_account():
    protocol = json.loads((PKG / "protocol-registered-v1.json").read_text(encoding="utf-8"))
    facts = json.loads((PKG / "registered-facts-v1.json").read_text(encoding="utf-8"))
    draft = json.loads((PKG / "root-admission-draft-v1.json").read_text(encoding="utf-8"))
    expected = [{"path": rel, "sha256": hashlib.sha256((REPO / rel).read_bytes()).hexdigest()} for rel in fam.PREDECESSOR_SNAPSHOTS["arm"]]
    assert protocol["predecessor_snapshots"]["arm"] == expected == facts["predecessor_snapshots"]["arm"]
    assert protocol["superseded_attempt_ids"] == [r[k] for r in fam.RECOVERY_HISTORY["arm"] for k in ("predecessor_attempt_id", "predecessor_fit_attempt_id")]
    assert "owner ruling 328" in protocol["failure_policy"] and "Recovery rec1 is spent" in protocol["failure_policy"]
    assert facts["resume"]["arm"]["resume_from"] == fam.recovery("arm")["resume_from"] and facts["resume"]["arm"]["counts"] == fam.recovery("arm")["resume_counts"]
    assert facts["resume"]["arm"]["owner_exception"] == "owner ruling 328 of 2026-10-17" and facts["resume"]["arm"]["fix_commit"] is None
    assert draft["eligible_run_ids"] == fam.eligible_run_ids() and draft["eligible_attempt_ids"] == fam.eligible_attempt_ids()
    assert draft["antecedents"]["recovery_plans"]["arm"]["generation"]["path"].endswith("generation-plan-registered-rec2-v1.json")
    sha = hashlib.sha256((PKG / fam.plan_file_name("arm", "generation")).read_bytes()).hexdigest()
    assert draft["antecedents"]["recovery_plans"]["arm"]["generation"]["sha256"] == sha


def test_the_recovery_ledger_block_names_both_predecessors_and_the_countersign_texts_carry_the_exception():
    ids = writer.identities(REPO)
    blocks = writer.recovery_blocks(REPO, ids, "x", "2026-10-17T15:00:00Z", "b147641b2", "/home/chao/saea-worktrees/sonnet-nxt2-rec2", "sonnet/nxt2-rec2")
    block = blocks["arm"]
    assert block.lstrip().startswith("## Cell NXT-R2 recovery rec2: ")
    rows = [line for line in block.splitlines() if line.startswith("| 2026")]
    assert len(rows) == 2 and ids["arm"]["run_id"] in rows[0] and ids["arm"]["fit_run_id"] in rows[1] and ids["arm"]["fit_run_id"].endswith("-FIT-REC2-V1")
    first, stopped = _snapshots()
    for row in rows:
        assert row.count("|") == 16 and "REGISTERED (DRAFT, root countersignature pending)" in row and "owner ruling 328 of 2026-10-17" in row and " | no | " in row
    assert first["attempt_id"] in rows[0] and stopped["attempt_id"] in rows[0] and "12094" in rows[0] and "35317" in rows[0]
    assert "SUPERSEDES the rec1 row" in rows[0] and "resumed in mode" in rows[0]
    draft_rows = (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8")
    assert block.strip() in draft_rows
    texts = json.loads((PKG / "countersign-row-texts-v1.json").read_text(encoding="utf-8"))["rows"]
    for run in (ids["arm"]["run_id"], ids["arm"]["fit_run_id"]):
        assert "RECOVERY rec2" in texts[run] and "214 calls" in texts[run] and "nxt_r2_mint_receipt.py --supersede" in texts[run] and "owner ruling 328" in texts[run]
        assert first["attempt_id"] in texts[run] and stopped["attempt_id"] in texts[run]
    assert texts[fam.READ_RUN_ID].startswith("REGISTERED BEFORE READ")
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    prereg = (REPO / fam.PREREG).read_text(encoding="utf-8")
    for text in (readme, prereg):
        assert "## Recovery rec1: " in text and "## Recovery rec2: " in text and "11880 + 42 = 11922 calls" in text and "11880 + 214 = 12094 calls" in text
        assert not re.search(r"[^\x00-\x7f]", text)
    assert "Recovery rec2 sequence" in readme and "arm-only" in readme and "NXT2_KINDS=arm" in readme


def test_the_writer_is_idempotent_on_the_recovery_ledger(tmp_path):
    ids = writer.identities(REPO)
    blocks = writer.recovery_blocks(REPO, ids, "x", "2026-10-17T15:00:00Z", "abc", "/wt", "br")
    ledger = tmp_path / "exposure-ledger.md"
    ledger.write_bytes(b"# ledger\n")
    attempt = ids["arm"]["attempt_id"]
    assert writer.rcv.append_recovery_ledger_block(ledger, blocks["arm"], attempt) is True
    once = ledger.read_bytes()
    assert writer.rcv.append_recovery_ledger_block(ledger, blocks["arm"], attempt) is False and ledger.read_bytes() == once


def test_the_reader_reports_the_kept_and_flown_split_of_a_resume_and_refuses_another_pin():
    resume_from = fam.recovery("arm")["resume_from"]
    pin_key = next(k for k in resume_from if k != "attempt_id")
    manifest = {"predecessor_attempt": {pin_key: resume_from[pin_key], "kept_sample_ids": [f"s{i}" for i in range(26)], "kept_sample_ids_sha256": "ab" * 32, "counts": {"kept": 26}}}
    block = reader.resume_block(manifest, resume_from, 1080)
    assert (block["kept"], block["flown"], block["rows"]) == (26, 1054, 1080)
    with pytest.raises(reader.ReadError, match="registered"):
        reader.resume_block({"predecessor_attempt": dict(manifest["predecessor_attempt"], **{pin_key: "0" * 64})}, resume_from, 1080)
    with pytest.raises(reader.ReadError, match="kept/flown split"):
        reader.resume_block({"predecessor_attempt": dict(manifest["predecessor_attempt"], kept_sample_ids=[])}, resume_from, 1080)
    text = reader.render_markdown({"resume": block, "arms_nodes": {}})
    assert "26 rows kept" in text and "1,054 rows flown" in text


# ---- the chain precondition ---------------------------------------------------------------------------------------------------------------


def _precondition_block() -> str:
    chain = (REPO / "scripts/flights/nx/batch_chain_nxt_r2.sh").read_text(encoding="utf-8")
    blocks = [b for b in re.findall(r"<<'PY'[^\n]*\n(.*?)\nPY\n", chain, re.S) if "resume precondition OK" in b]
    assert len(blocks) == 1
    return blocks[0]


def _run_precondition(monkeypatch, tmp_path, *, mode: str = "trace", make_pin: bool = True, record: bool = False, run_dir_files: dict | None = None,
                      moved: bool = False) -> str:
    """Execute the arm-only resume precondition block in process against a synthetic main (cell config) and data root."""

    spec = fam.CELLS["arm"]
    data, main = tmp_path / "data", tmp_path / "main"
    attempt = fam.recovery("arm")["predecessor_attempt_id"]
    suffix = ".trace.jsonl" if mode == "trace" else ".rows.ckpt.jsonl"
    pinned = data / "runs" / spec["run"] / attempt / (spec["run"] + suffix)
    pinned.parent.mkdir(parents=True)
    payload = b"synthetic predecessor bytes\n"
    pinned.write_bytes(payload + (b"moved" if moved else b""))
    key = "trace_sha256" if mode == "trace" else "checkpoint_sha256"
    resume = {"attempt_id": attempt, key: hashlib.sha256(payload).hexdigest()}
    (main / "configs" / "experiment").mkdir(parents=True)
    (main / "configs" / "experiment" / (spec["cell"] + ".json")).write_text(json.dumps({"cells": [{"resume_from": resume}]}), encoding="utf-8")
    rec = copy.deepcopy(fam.RECOVERIES["arm"])
    rec["resume_from"] = resume
    monkeypatch.setitem(fam.RECOVERIES, "arm", rec)
    if record:
        (data / "attempts" / spec["run"]).mkdir(parents=True)
        (data / "attempts" / spec["run"] / (spec["attempt"] + ".json")).write_text("{}", encoding="utf-8")
    if run_dir_files is not None:
        run_dir = data / "runs" / spec["run"] / spec["attempt"]
        run_dir.mkdir(parents=True)
        for name, body in run_dir_files.items():
            (run_dir / name).write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    monkeypatch.setenv("NXT2_MAIN", str(main))
    monkeypatch.setenv("NXT2_DATA", str(data))
    import contextlib
    import io

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(_precondition_block(), "chain-precondition", "exec"), {"__name__": "chain_precondition"})
    return out.getvalue()


def _declaration(mode: str, pin: str) -> dict:
    spec = fam.CELLS["arm"]
    return {"schema": "saea-resume-declaration-v1", "run_id": spec["run"], "attempt_id": spec["attempt"],
            "predecessors": [{"attempt_id": fam.recovery("arm")["predecessor_attempt_id"], "mode": mode, "pin_sha256": pin}]}


@pytest.mark.parametrize("mode", ["trace", "checkpoint"])
def test_the_chain_precondition_accepts_an_unmoved_pin_and_an_unopened_attempt(monkeypatch, tmp_path, mode):
    assert "resume precondition OK" in _run_precondition(monkeypatch, tmp_path, mode=mode)


@pytest.mark.parametrize("mode", ["trace", "checkpoint"])
def test_the_chain_precondition_refuses_a_moved_pin(monkeypatch, tmp_path, mode):
    with pytest.raises(AssertionError, match="pin moved"):
        _run_precondition(monkeypatch, tmp_path, mode=mode, moved=True)


def test_the_chain_precondition_refuses_an_existing_attempt_record(monkeypatch, tmp_path):
    with pytest.raises(AssertionError, match="attempt record already exists"):
        _run_precondition(monkeypatch, tmp_path, record=True)


@pytest.mark.parametrize("mode", ["trace", "checkpoint"])
def test_the_chain_precondition_tolerates_only_the_matching_preflight_declaration(monkeypatch, tmp_path, mode):
    pin = hashlib.sha256(b"synthetic predecessor bytes\n").hexdigest()
    ok = _run_precondition(monkeypatch, tmp_path / "a", mode=mode, run_dir_files={"resume-declaration.json": _declaration(mode, pin)})
    assert "tolerated" in ok and "resume precondition OK" in ok
    with pytest.raises(AssertionError, match="more than the preflight declaration"):
        _run_precondition(monkeypatch, tmp_path / "b", mode=mode, run_dir_files={"resume-declaration.json": _declaration(mode, pin), "x.trace.jsonl": "flown"})
    with pytest.raises(AssertionError, match="does not match the registered resume_from"):
        _run_precondition(monkeypatch, tmp_path / "c", mode=mode, run_dir_files={"resume-declaration.json": _declaration(mode, "0" * 64)})
    with pytest.raises(AssertionError, match="does not match the registered resume_from"):
        _run_precondition(monkeypatch, tmp_path / "d", mode=mode, run_dir_files={"resume-declaration.json": _declaration("checkpoint" if mode == "trace" else "trace", pin)})


def test_the_chain_declares_the_driver_runs_the_resume_gate_and_is_syntactically_valid():
    nx = REPO / "scripts" / "flights" / "nx"
    chain = (nx / "batch_chain_nxt_r2.sh").read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(nx / "batch_chain_nxt_r2.sh")], capture_output=True).returncode == 0
    assert "bash $SP/batch_driver.sh" in chain and "resume_gate_run" in chain and "exit 6" in chain
    driver = (REPO / "scripts/flights/batch/batch_driver.sh").read_text(encoding="utf-8")
    assert 'source "$SP/resume_gate_lib.sh"' in driver and "resume_gate_run" in driver and "resume_prelaunch_gate.sh" in driver
    flip = (nx / "nxt_r2_flip.sh").read_text(encoding="utf-8")
    assert "owner ruling 328" in flip and "NXT2_KINDS=arm" in flip


# ---- the tools --------------------------------------------------------------------------------------------------------------------------------


def test_the_rec2_tools_compile_are_ascii_and_never_write_the_data_root():
    for name in ("nxt_r2_rec2_snapshot.py", "nxt_r2_rec2_mode.py", "nxt_r2_rec2_replay_proof.py"):
        source = (REPO / "scripts/flights/nx" / name).read_text(encoding="utf-8")
        compile(source, name, "exec")
        assert source.isascii()
    snapshot = (REPO / "scripts/flights/nx/nxt_r2_rec2_snapshot.py").read_text(encoding="utf-8")
    assert "outside the data root" in snapshot and "write_bytes" in snapshot and snapshot.count("write_bytes") == 1       # only the --out receipt
    mode = (REPO / "scripts/flights/nx/nxt_r2_rec2_mode.py").read_text(encoding="utf-8")
    assert "materialize_dir=Path(args.scratch)" in mode and "write_bytes(" in mode and "data_root" in mode


def test_the_replay_proof_builder_checks_the_attempt_the_trace_and_the_complete_count():
    import nxt_r2_rec2_replay_proof as proofmod

    rec = fam.recovery("arm")
    if "trace_sha256" not in rec["resume_from"]:
        pytest.skip("mode B: the proof is the prelaunch gate's checkpoint receipt")
    counts = rec["resume_counts"]
    attempt = {"attempt_id": rec["resume_from"]["attempt_id"], "trace_sha256": rec["resume_from"]["trace_sha256"], "samples_started": counts["kept"] + counts["partial"],
               "complete": counts["kept"], "incomplete": counts["partial"], "rows_checked": counts["kept"], "rows_failing": 0}
    report = {"attempts": [attempt], "rows_checked_total": counts["kept"], "rows_failing_total": 0, "union": {"sealed_twice": 0, "complete_rows": counts["kept"]},
              "resume_py_sha256": "c" * 64, "model_contacts": 0}
    proof = proofmod.build_proof(report, "abc1234", "2026-10-17T15:05:00Z", REPO)
    assert proof["rows_checked"] == counts["kept"] and proof["rows_failing"] == 0 and proof["sealed_twice"] == 0 and proof["code_commit"] == "abc1234"
    for bad in (dict(report, attempts=[dict(attempt, trace_sha256="0" * 64)]), dict(report, attempts=[dict(attempt, complete=counts["kept"] + 1)]),
                dict(report, attempts=[dict(attempt, attempt_id="other")])):
        with pytest.raises(SystemExit):
            proofmod.build_proof(bad, "abc1234", "2026-10-17T15:05:00Z", REPO)
    assert "--trace-pin" in (REPO / "scripts/flights/lib/recovery.py").read_text(encoding="utf-8")


def test_the_writer_cli_exposes_the_recovery_flags():
    out = subprocess.run([sys.executable, "-B", str(REPO / "scripts/flights/nx/nxt_r2_write_registration.py"), "--help"], capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0
    for flag in ("--append-recovery-ledger", "--recovery-registered-at", "--recovery-base-commit", "--study-commit", "--data-root"):
        assert flag in out.stdout
