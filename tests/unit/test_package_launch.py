"""One-command package launch (M7): scripts/flights/batch/package_launch.py against a fake repository.

Fixtures only: a temp git repo, fake derive / write / mint / flip commands and a fake PowerShell. No model, server, GPU, data root, lock,
re-pin or real flip is touched.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BATCH = REPO / "scripts" / "flights" / "batch"
sys.path.insert(0, str(BATCH))
import package_launch as pl  # noqa: E402

LEDGER_ROW = ("| 2026-10-15 | RUN-A | bounded-discovery-probe | DRAFT -- REGISTERED. Column: scope | model | slurp | discovery | hash | no | 1 | 2 | 3 | "
              "inherited | plan.json | DRAFT at study commit abc; plan SHA256 def; nothing authorised. |")
READ_ROW = LEDGER_ROW.replace("RUN-A", "RUN-READ-V1").replace("DRAFT at study commit abc", "DRAFT. REGISTERED WITH THE FLIGHT")

FAKE_FLIP = r'''#!/bin/bash
# fake flip_package_ext4.sh: args --flip S --package P --cells C --pins-commit-msg M --log L [-- K=V]
while [ $# -gt 0 ]; do case "$1" in --log) LOG=$2; shift 2;; --cells) CELLS=$2; shift 2;; --) shift; break;; *) shift 2;; esac; done
echo flip >> "$ORDER"
if [ -n "${FLIP_EXTRA_OUT:-}" ]; then { echo "$#"; for a in "$@"; do echo "$a"; done; } > "$FLIP_EXTRA_OUT"; fi
HEAD=$(git rev-parse HEAD)
{ echo "== gate"; IFS=, read -ra A <<< "$CELLS"; for c in "${A[@]}"; do echo "flight registration check: $FAKE_VERDICT (1 cell(s))"; done
  echo "flight commit file: $HEAD HEAD $HEAD"; echo "master verified at flight commit $HEAD"; echo "FLIP_CHAIN_DONE 2026-10-15T00:00:00Z"; } > "$LOG"
echo "$FAKE_FLIGHT_COMMIT_VALUE" | sed "s/HEAD/$HEAD/" > "$FLIGHT_FILE"
exit ${FAKE_FLIP_RC:-0}
'''

FAKE_PS = '''#!/bin/bash
echo chain >> "$ORDER"
echo "${FAKE_PS_OUT:-SAEA-Chain-TEST started: state=Running action=x}"
'''


def run(*cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=str(cwd), check=True, capture_output=True, text=True, env=env).stdout


@pytest.fixture()
def fx(tmp_path, monkeypatch):
    repo, aux = tmp_path / "repo", tmp_path / "aux"
    repo.mkdir()
    aux.mkdir()
    run("git", "init", "-q", cwd=repo)
    run("git", "config", "user.name", "t", cwd=repo)
    run("git", "config", "user.email", "t@t", cwd=repo)
    (repo / "docs").mkdir()
    (repo / "configs").mkdir()
    (repo / "docs" / "rd").mkdir()
    (repo / "docs" / "exposure-ledger.md").write_text(LEDGER_ROW + "\n" + READ_ROW + "\n", encoding="utf-8")
    (repo / "docs" / "rd" / "countersign-row-texts-v1.json").write_text(json.dumps({"rows": {
        "RUN-A": "REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by test)",
        "RUN-READ-V1": "REGISTERED BEFORE READ (root countersigned <UTC timestamp>)"}}), encoding="utf-8")
    run("git", "add", "-A", cwd=repo)
    run("git", "commit", "-q", "-m", "init", cwd=repo)
    order = aux / "order.txt"
    flight = aux / "t-flight-commit.txt"
    (aux / "fake_flip.sh").write_text(FAKE_FLIP, encoding="utf-8")
    ps = aux / "fake_ps.sh"
    ps.write_text(FAKE_PS, encoding="utf-8")
    ps.chmod(ps.stat().st_mode | stat.S_IEXEC)
    data = aux / "data"
    (data / "coordination").mkdir(parents=True)
    spec = {
        "schema": pl.SPEC_SCHEMA, "short": "t", "launch_id": "t1", "package": "pkg", "readiness_dir": "docs/rd",
        "log": str(aux / "launch.out"), "receipts": str(aux / "launch" / "launch-steps.jsonl"), "data_root": str(data),
        "steps": {
            "derive": {"cmd": "echo derive >> $ORDER; echo d >> configs/derived.txt"},
            "write": {"cmd": "echo write >> $ORDER; echo 'at {head}' >> docs/rd/reg.md"},
            "countersign": {"texts": "{readiness_dir}/countersign-row-texts-v1.json"},
            "mint": {"cmd": "echo mint >> $ORDER; echo RUN-A > $DATA/coordination/receipt.json",
                     "done_if": {"file": "coordination/receipt.json", "contains": ["RUN-A"]}},
            "commit": {"paths": ["configs", "docs"], "message": "register test package"},
            "flip": {"wrapper": f"bash {aux / 'fake_flip.sh'}", "script": "x_flip.sh", "package": "docs/rd", "cells": ["c1", "c2"],
                     "pins_commit_msg": str(aux / "msg.txt"), "log": str(aux / "flip.out"), "flight_commit_file": str(flight)},
            "chain": {"task": "SAEA-Chain-TEST", "wrapper": "/x/wrapper.sh", "flight_commit_file": str(flight)},
            "read": {"cmd": "echo read >> $ORDER"},
        },
    }
    spec_path = aux / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    for key, value in {"ORDER": str(order), "DATA": str(data), "FLIGHT_FILE": str(flight), "FAKE_VERDICT": "check: PASS",
                       "FAKE_FLIGHT_COMMIT_VALUE": "HEAD", "PACKAGE_LAUNCH_ALIVE_CMD": "true", "SAEA_POWERSHELL": str(ps)}.items():
        monkeypatch.setenv(key, value)
    return {"repo": repo, "aux": aux, "spec": spec_path, "order": order, "flight": flight, "data": data}


def launch(fx, *flags):
    return pl.main([str(fx["spec"]), "--repo-root", str(fx["repo"]), *flags])


def steps_run(fx):
    return fx["order"].read_text(encoding="utf-8").split() if fx["order"].exists() else []


def receipts(fx):
    path = fx["aux"] / "launch" / "launch-steps.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def test_dry_run_acts_on_nothing(fx):
    assert launch(fx, "--dry-run") == 3          # the countersign step would refuse without the flag
    assert launch(fx, "--dry-run", "--root-countersign") == 0
    assert steps_run(fx) == [] and receipts(fx) == []
    assert not (fx["aux"] / "launch.out").exists()
    assert run("git", "status", "--porcelain", cwd=fx["repo"]) == ""


def test_dry_run_reports_a_refusal_for_the_first_step(fx):
    (fx["repo"] / "stray.txt").write_text("x", encoding="utf-8")
    assert launch(fx, "--dry-run") == 2


def test_full_launch_orders_the_steps_and_countersigns_only_with_the_flag(fx):
    assert launch(fx) == 3                                   # derive, write run; countersign refuses without the flag
    assert steps_run(fx) == ["derive", "write"]
    ledger = (fx["repo"] / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    assert "DRAFT -- REGISTERED" in ledger and "root countersigned" not in ledger
    assert launch(fx, "--root-countersign") == 0
    assert steps_run(fx) == ["derive", "write", "mint", "flip", "chain"]
    assert [r["step"] for r in receipts(fx) if r["status"] in ("ok", "skipped-done")] == ["derive", "write", "countersign", "mint", "commit", "flip", "chain"]
    ledger = (fx["repo"] / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    row = [l for l in ledger.splitlines() if "| RUN-A |" in l][0]
    assert "REGISTERED BEFORE CONTACT (root countersigned 20" in row and "<UTC timestamp>" not in row
    assert "at study commit abc; plan SHA256 def; nothing authorised." in row          # the remainder after the DRAFT token is kept
    assert "Column: scope" in row and "DRAFT -- REGISTERED" not in row
    assert "DRAFT. REGISTERED WITH THE FLIGHT" in ledger                                # the READ row is not countersigned at launch
    assert run("git", "status", "--porcelain", cwd=fx["repo"]) == ""


def test_second_run_is_idempotent(fx):
    assert launch(fx, "--root-countersign") == 0
    first = steps_run(fx)
    head = run("git", "rev-parse", "HEAD", cwd=fx["repo"])
    assert launch(fx, "--root-countersign") == 0
    assert steps_run(fx) == first and run("git", "rev-parse", "HEAD", cwd=fx["repo"]) == head


def test_idempotent_without_receipts_for_countersign_mint_and_commit(fx):
    assert launch(fx, "--root-countersign", "--until", "commit") == 0
    (fx["aux"] / "launch" / "launch-steps.jsonl").unlink()
    head = run("git", "rev-parse", "HEAD", cwd=fx["repo"])
    # derive/write re-run (idempotent writers by contract) and dirty the tree; countersign, mint and commit report nothing new to do
    assert launch(fx, "--from", "countersign", "--until", "commit", "--root-countersign") == 0
    statuses = {r["step"]: r["status"] for r in receipts(fx)}
    assert statuses["countersign"] == "skipped-done" and statuses["mint"] == "skipped-done" and statuses["commit"] == "skipped-done"
    assert run("git", "rev-parse", "HEAD", cwd=fx["repo"]) == head


def test_resume_from_a_step_and_until(fx):
    assert launch(fx, "--root-countersign", "--until", "commit") == 0
    assert steps_run(fx) == ["derive", "write", "mint"]
    assert launch(fx, "--from", "flip", "--until", "flip") == 0
    assert steps_run(fx)[-1] == "flip" and "chain" not in steps_run(fx)
    assert launch(fx, "--from", "chain") == 0
    assert steps_run(fx)[-1] == "chain"


def test_redo_reruns_a_done_step(fx):
    assert launch(fx, "--root-countersign", "--until", "commit") == 0
    assert launch(fx, "--from", "derive", "--until", "derive", "--redo", "derive") == 0
    assert steps_run(fx).count("derive") == 2


def test_fail_closed_at_the_first_failing_step(fx):
    spec = json.loads(fx["spec"].read_text(encoding="utf-8"))
    spec["steps"]["write"]["cmd"] = "echo write >> $ORDER; exit 7"
    fx["spec"].write_text(json.dumps(spec), encoding="utf-8")
    assert launch(fx, "--root-countersign") == 1
    assert steps_run(fx) == ["derive", "write"]
    assert [(r["step"], r["status"]) for r in receipts(fx)] == [("derive", "ok"), ("write", "failed")]


def test_dirty_master_refuses_before_derive(fx):
    (fx["repo"] / "stray.txt").write_text("x", encoding="utf-8")
    assert launch(fx) == 2 and steps_run(fx) == []


def test_merge_in_progress_refuses(fx):
    (fx["repo"] / ".git" / "MERGE_HEAD").write_text("0" * 40, encoding="utf-8")
    assert launch(fx) == 2 and steps_run(fx) == []


def test_alive_driver_refuses_the_flip_and_the_chain_but_not_registration(fx, monkeypatch):
    assert launch(fx, "--root-countersign", "--until", "commit") == 0
    monkeypatch.setenv("PACKAGE_LAUNCH_ALIVE_CMD", "echo 123 bash batch_driver.sh")
    assert launch(fx, "--from", "flip") == 2
    assert steps_run(fx)[-1] != "flip"
    assert launch(fx, "--from", "mint", "--until", "commit", "--redo", "mint") == 0   # registration steps are safe in flight


def test_flight_lock_refuses(fx):
    assert launch(fx, "--root-countersign", "--until", "commit") == 0
    (fx["data"] / "locks").mkdir()
    (fx["data"] / "locks" / "flight.lock").write_text("x", encoding="utf-8")
    assert launch(fx, "--from", "flip") == 2


def test_hollow_flip_is_a_failure_even_with_exit_zero(fx, monkeypatch):
    assert launch(fx, "--root-countersign", "--until", "commit") == 0
    monkeypatch.setenv("FAKE_VERDICT", "check: FAIL")
    assert launch(fx, "--from", "flip") == 1
    assert receipts(fx)[-1]["status"] == "failed" and "chain" not in steps_run(fx)


def test_flip_log_without_a_pass_per_cell_fails(fx):
    launch_obj = pl.Launch(json.loads(fx["spec"].read_text(encoding="utf-8")), fx["repo"], dry=True, root_countersign=False, redo=set())
    head = launch_obj.head()
    log = f"== gate\nflight registration check: check: PASS\nflight commit file: {head}\nmaster verified at flight commit {head}\nFLIP_CHAIN_DONE x\n"
    with pytest.raises(pl.StepFailed, match="1 PASS"):
        launch_obj.parse_flip_log(log, 2)
    launch_obj.parse_flip_log(log.replace("check: PASS\n", "check: PASS\nflight registration check: check: PASS\n"), 2)


def test_flight_commit_file_must_equal_master_head_before_the_chain(fx, monkeypatch):
    assert launch(fx, "--root-countersign", "--until", "flip") == 0
    fx["flight"].write_text("0" * 40 + "\n", encoding="utf-8")
    assert launch(fx, "--from", "chain") == 2
    assert "chain" not in steps_run(fx)


def test_flip_that_leaves_a_stale_flight_commit_file_fails(fx, monkeypatch):
    assert launch(fx, "--root-countersign", "--until", "commit") == 0
    monkeypatch.setenv("FAKE_FLIGHT_COMMIT_VALUE", "deadbeef")
    assert launch(fx, "--from", "flip") == 1


def test_chain_task_already_running_is_a_failure(fx, monkeypatch):
    assert launch(fx, "--root-countersign", "--until", "flip") == 0
    monkeypatch.setenv("FAKE_PS_OUT", "SAEA-Chain-TEST : already running (action 'x')")
    assert launch(fx, "--from", "chain") == 1


def test_countersign_refuses_a_row_that_is_neither_draft_nor_registered(fx):
    ledger = fx["repo"] / "docs" / "exposure-ledger.md"
    ledger.write_text(ledger.read_text(encoding="utf-8").replace("DRAFT at study commit", "SOMETHING at study commit"), encoding="utf-8")
    run("git", "commit", "-q", "-am", "odd", cwd=fx["repo"])
    assert launch(fx, "--root-countersign") == 1


def test_a_flip_env_value_with_a_space_reaches_the_wrapper_as_one_word(fx, monkeypatch):
    # 2026-10-17: `NXT2_KINDS=smoke arm` unquoted reached flip_package_ext4.sh as two words ("bad extra env 'arm'").
    spec = json.loads(fx["spec"].read_text(encoding="utf-8"))
    spec["steps"]["flip"]["env"] = {"NXT2_KINDS": "smoke arm", "TFRL_ONLY": "1"}
    fx["spec"].write_text(json.dumps(spec), encoding="utf-8")
    out = fx["aux"] / "flip-extra.txt"
    monkeypatch.setenv("FLIP_EXTRA_OUT", str(out))
    assert launch(fx, "--root-countersign", "--until", "flip") == 0
    assert out.read_text(encoding="utf-8").splitlines() == ["2", "NXT2_KINDS=smoke arm", "TFRL_ONLY=1"]


def test_the_pins_commit_message_file_is_written_from_the_spec_when_missing(fx):
    spec = json.loads(fx["spec"].read_text(encoding="utf-8"))
    spec["steps"]["flip"]["pins_commit_text"] = "re-pin X\n\nCo-Authored-By: T <t@x>"
    fx["spec"].write_text(json.dumps(spec), encoding="utf-8")
    msg = fx["aux"] / "msg.txt"
    assert not msg.exists()
    assert launch(fx, "--root-countersign", "--until", "flip") == 0
    assert msg.read_text(encoding="utf-8") == "re-pin X\n\nCo-Authored-By: T <t@x>\n"

