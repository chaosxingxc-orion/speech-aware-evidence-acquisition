"""Machine sign-off (M6, owner ruling 314 A): scripts/flights/batch/smoke_signoff.py and chain_lib.sh.

Fixtures only: a synthetic smoke decode-cost table and temp directories. No model, server, GPU, data root or lock is touched.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BATCH = REPO / "scripts" / "flights" / "batch"
CONDITIONS = REPO / "docs" / "readiness" / "2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1-signoff-conditions-v1.json"
sys.path.insert(0, str(BATCH))
import smoke_signoff as so  # noqa: E402

NO_THINK = {"both-off": ["perception", "solver"], "perception-off": ["perception"], "solver-off": ["solver"]}


def node(mode: str) -> dict:
    nt = mode == "no-think"
    return {"mode": mode, "contacts": 4, "cap_hits": 0, "empty_content": 0, "no_json_object": 0, "finish_reason_length": 0,
            "contacts_with_reasoning_chars": 0 if nt else 4, "marker_in_content": 0, "reasoning_chars_mean": 0.0 if nt else 9000.0}


def good_table() -> dict:
    arms = {}
    for arm in ("both-off", "both-on", "both-on-twin", "perception-off", "solver-off"):
        arms[arm] = {n: node("no-think" if n in NO_THINK.get(arm, []) else "think") for n in ("perception", "solver")}
    return {"schema": "saea-nxt-r1-thinking-policy-column-smoke-v1", "arms": arms, "unattributed_contacts": 0, "absent_columns": 0,
            "throughput": {"arm_mix_measured_rows": 3.32, "arm_mix_registered_rows": 3.25}}


@pytest.fixture()
def env(tmp_path):
    data = tmp_path / "data"
    table = data / "analysis" / "SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1" / "smoke-decode-cost.json"
    table.parent.mkdir(parents=True)
    table.write_text(json.dumps(good_table()), encoding="utf-8")
    return {"data": data, "table": table, "marker": tmp_path / "signoff.marker", "tmp": tmp_path}


def sign(env, *extra):
    return so.main(["--conditions", str(CONDITIONS), "--data-root", str(env["data"]), "--marker", str(env["marker"]), *extra])


def mutate(env, fn):
    table = good_table()
    fn(table)
    env["table"].write_text(json.dumps(table), encoding="utf-8")


def test_conditions_file_is_valid():
    so.validate_conditions(json.loads(CONDITIONS.read_text(encoding="utf-8")))


def test_pass_writes_marker_with_evidence(env):
    assert sign(env, "--veto-minutes", "20", "--utc", "2026-10-15T01:02:03Z") == 0
    text = env["marker"].read_text(encoding="utf-8")
    first, body = text.split("\n", 1)
    assert first.startswith("machine sign-off under owner ruling 314 A: PASS 2026-10-15T01:02:03Z")
    evidence = json.loads(body)
    assert evidence["verdict"] == "PASS" and evidence["checks_failed"] == 0 and evidence["veto_minutes"] == 20.0
    assert len(evidence["conditions_sha256"]) == 64 and len(evidence["table_sha256"]) == 64
    assert not env["marker"].with_name("signoff.marker.refused").exists()


def test_existing_marker_is_never_overwritten(env):
    env["marker"].write_text("coordinator signed\n", encoding="utf-8")
    assert sign(env) == 0
    assert env["marker"].read_text(encoding="utf-8") == "coordinator signed\n"


@pytest.mark.parametrize("label,fn,failing_id", [
    ("reasoning bytes on a no-think node", lambda t: t["arms"]["both-off"]["perception"].update(reasoning_chars_mean=12.0, contacts_with_reasoning_chars=1),
     "both-off/perception/reasoning_chars_mean"),
    ("think marker in content", lambda t: t["arms"]["solver-off"]["solver"].update(marker_in_content=1), "solver-off/solver/marker_in_content"),
    ("cap hit", lambda t: t["arms"]["both-on"]["solver"].update(cap_hits=1), "both-on/solver/cap_hits"),
    ("empty answer", lambda t: t["arms"]["both-on"]["perception"].update(empty_content=1), "both-on/perception/empty_content"),
    ("malformed JSON", lambda t: t["arms"]["perception-off"]["solver"].update(no_json_object=2), "perception-off/solver/no_json_object"),
    ("mix above 1.3x", lambda t: t["throughput"].update(arm_mix_measured_rows=4.3), "arm-mix/measured<=ratio*registered"),
    ("missing arm", lambda t: t["arms"].pop("both-on-twin"), "arm-present/both-on-twin"),
    ("mode label disagrees with registration", lambda t: t["arms"]["both-on"]["solver"].update(mode="no-think"), "both-on/solver/mode-matches-registration"),
    ("unattributed contacts", lambda t: t.update(unattributed_contacts=3), "extra/unattributed-contacts/unattributed_contacts"),
    ("an absent Solver column (a non-delivering arm's Solver contact ended on a finite completion)", lambda t: t.update(absent_columns=1),
     "extra/absent-columns/absent_columns"),
    ("a table that does not carry absent_columns at all", lambda t: t.pop("absent_columns"), "extra/absent-columns"),
    ("wrong table schema", lambda t: t.update(schema="other"), "table.schema"),
])
def test_fail_writes_refused_not_marker(env, label, fn, failing_id):
    mutate(env, fn)
    assert sign(env) == 3, label
    refused = env["marker"].with_name("signoff.marker.refused")
    assert not env["marker"].exists()
    ids = [c["id"] for c in json.loads(refused.read_text(encoding="utf-8").split("\n", 1)[1])["checks"]]
    assert failing_id in ids


def test_mix_exactly_at_the_limit_passes(env):
    mutate(env, lambda t: t["throughput"].update(arm_mix_measured_rows=1.3 * 3.25))
    assert sign(env) == 0


def test_missing_table_is_a_refusal_and_pass_clears_a_stale_refused(env):
    env["table"].unlink()
    assert sign(env) == 3
    refused = env["marker"].with_name("signoff.marker.refused")
    assert refused.exists()
    env["table"].write_text(json.dumps(good_table()), encoding="utf-8")
    assert sign(env) == 0 and not refused.exists()


# -- chain_lib.sh ---------------------------------------------------------------------------------

def bash(env, body: str, **extra_env):
    lib = BATCH / "chain_lib.sh"
    full = {"PATH": "/usr/bin:/bin:/usr/local/bin", "LOG": str(env["tmp"] / "chain.log"), "SIGNOFF_POLL_SECONDS": "0.2",
            "SIGNOFF_VETO_UNIT_SECONDS": "1", "CHAIN_STOP_FILE": str(env["tmp"] / "STOP"), "SIGNOFF_PY": sys.executable,
            "DATA": str(env["data"]), **extra_env}
    return subprocess.run(["bash", "-c", f'. "{lib}"; {body}'], env=full, capture_output=True, text=True, timeout=60)


READER = "true"


def call(env, veto="0", reader=READER):
    return f'wait_or_machine_signoff "{reader}" "{CONDITIONS}" "{env["marker"]}" {veto}'


def test_chain_machine_signoff_without_veto(env):
    done = bash(env, call(env, "0"))
    assert done.returncode == 0, done.stderr
    assert env["marker"].read_text(encoding="utf-8").startswith("machine sign-off")
    assert "machine sign-off PASS" in (env["tmp"] / "chain.log").read_text(encoding="utf-8")


def test_chain_veto_by_deleting_the_marker(env):
    script = f'( sleep 1; rm -f "{env["marker"]}" ) & {call(env, "3")}'
    done = bash(env, script)
    assert done.returncode == 10
    assert "VETO: sign-off marker" in (env["tmp"] / "chain.log").read_text(encoding="utf-8")


def test_chain_veto_by_batch_stop(env):
    script = f'( sleep 1; touch "{env["tmp"] / "STOP"}" ) & {call(env, "3")}'
    done = bash(env, script)
    assert done.returncode == 8
    assert "VETO: " in (env["tmp"] / "chain.log").read_text(encoding="utf-8")


def test_chain_veto_window_elapses(env):
    done = bash(env, call(env, "1"))
    assert done.returncode == 0
    assert "veto window elapsed" in (env["tmp"] / "chain.log").read_text(encoding="utf-8")


def test_chain_failed_conditions_fall_back_to_the_coordinator(env):
    mutate(env, lambda t: t["arms"]["both-off"]["perception"].update(reasoning_chars_mean=5.0))
    done = bash(env, call(env, "0"), SIGNOFF_WAIT_SECONDS="1")
    assert done.returncode == 5
    assert env["marker"].with_name("signoff.marker.refused").exists() and not env["marker"].exists()
    done = bash(env, f'( sleep 1; echo coordinator > "{env["marker"]}" ) & {call(env, "5")}', SIGNOFF_WAIT_SECONDS="20")
    assert done.returncode == 0
    assert "coordinator sign-off marker present" in (env["tmp"] / "chain.log").read_text(encoding="utf-8")


def test_chain_reader_failure_falls_back(env):
    done = bash(env, call(env, "0", reader="false"), SIGNOFF_WAIT_SECONDS="1")
    assert done.returncode == 5
    assert "reader failed" in (env["tmp"] / "chain.log").read_text(encoding="utf-8")


def test_chain_existing_coordinator_marker_is_immediate(env):
    env["marker"].write_text("coordinator\n", encoding="utf-8")
    assert bash(env, call(env, "30")).returncode == 0


def test_chain_batch_stop_while_waiting(env):
    mutate(env, lambda t: t.update(unattributed_contacts=1))
    (env["tmp"] / "STOP").write_text("x", encoding="utf-8")
    assert bash(env, call(env, "0"), SIGNOFF_WAIT_SECONDS="30").returncode == 8


# -- close_rows_after_seal --------------------------------------------------------------------------

STUB = '''#!/usr/bin/env python3
import sys, io
args = sys.argv[1:]
ids = [args[i + 1] for i, a in enumerate(args) if a == "--run-id"]
root = args[args.index("--repo-root") + 1]
p = root + "/docs/exposure-ledger.md"
t = io.open(p, encoding="utf-8").read()
for r in ids:
    t = t.replace(f"| {r} | no |", f"| {r} | yes |")
io.open(p, "w", encoding="utf-8", newline="").write(t)
'''


def test_close_rows_after_seal_is_idempotent_and_commits_the_ledger_alone(tmp_path, env):
    repo = tmp_path / "repo"
    (repo / "scripts/flights/batch").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "scripts/flights/batch/ledger_mark_consumed.py").write_text(STUB, encoding="utf-8")
    (repo / "docs/exposure-ledger.md").write_text("| RUN-A | no |\n| RUN-B | no |\n", encoding="utf-8")
    (repo / "other.txt").write_text("keep", encoding="utf-8")
    git = lambda *a: subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True, text=True)
    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "init")
    (repo / "other.txt").write_text("dirty but unrelated", encoding="utf-8")
    done = bash(env, "close_rows_after_seal RUN-A", CLOSE_ROWS_REPO=str(repo), CLOSE_ROWS_PY=sys.executable, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    assert done.returncode == 0, done.stderr
    assert "| RUN-A | yes |" in (repo / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    assert "| RUN-B | no |" in (repo / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    assert git("show", "--name-only", "--format=", "HEAD").stdout.split() == ["docs/exposure-ledger.md"]
    head = git("rev-parse", "HEAD").stdout
    again = bash(env, "close_rows_after_seal RUN-A", CLOSE_ROWS_REPO=str(repo), CLOSE_ROWS_PY=sys.executable)
    assert again.returncode == 0 and git("rev-parse", "HEAD").stdout == head
    assert "already closed" in (env["tmp"] / "chain.log").read_text(encoding="utf-8")
