"""Text-only branch of the batch inspector and the TFRL_ONLY switch of the iteration queue builder / flip wrapper.

Synthetic sealed trees only: no model, no data root, no utterance text.
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
INSPECT = REPO / "scripts" / "flights" / "batch" / "batch_inspect.py"
TFRL = REPO / "scripts" / "flights" / "tfrl"
RUN, ATT, COMMIT = "RUN-X", "attempt-x", "c" * 40
PLAN = "configs/campaign/slurp-native-stage3-tfrl-proposer-i1-v1.json"


def _seal(root, run=RUN, att=ATT, rows=3, requests=3, calls_used=3, tool_calls=0, native_rows=False, commit=COMMIT):
    (root / "attempts" / run).mkdir(parents=True)
    (root / "attempts" / run / f"{att}.json").write_text(
        json.dumps({"state": "FINALIZED", "actual": {"calls": calls_used}}))
    d = root / "runs" / run / att
    d.mkdir(parents=True)
    (d / "x.run-manifest.json").write_text(json.dumps(
        {"status": "COMPLETED", "study_commit": commit, "study_repo_dirt": [], "result_kind": "task-answer"}))
    receipt = {"native_episode_receipt": {"contact_count": 9}} if native_rows else {}
    (d / "x.outputs.jsonl").write_text("".join(
        json.dumps({"sample_id": f"s{i}", **receipt}) + "\n" for i in range(rows)))
    (d / "x.generation-manifest.json").write_text(json.dumps(
        {"cost": {"calls_used": calls_used, "tool_calls": tool_calls}}))
    (d / "score-jobs.jsonl").write_text("{}\n")
    (d / "x.trace.jsonl").write_text("".join(
        json.dumps({"channel": "MODEL_REQUEST", "payload": {}}) + "\n" for _ in range(requests)))
    return d


def _env():
    return dict(os.environ, PYTHONPATH=str(REPO / "src"), PYTHONDONTWRITEBYTECODE="1")


def _inspect(root, *extra, rows=3, ceiling=3, commit=COMMIT):
    proc = subprocess.run([sys.executable, "-B", str(INSPECT), str(root), RUN, ATT, "arm", str(rows), str(ceiling), "1",
                           commit, *extra], capture_output=True, text=True, env=_env())
    return proc.returncode, json.loads(proc.stdout)


def test_text_only_pass(tmp_path):
    _seal(tmp_path)
    rc, rep = _inspect(tmp_path, "--text-only")
    assert rc == 0 and rep["pass"] is True and rep["text_only"] is True
    assert rep["requests"] == 3 and rep["rows"] == 3


def test_text_only_outputs_count_mismatch_fails(tmp_path):
    _seal(tmp_path, rows=2)
    rc, rep = _inspect(tmp_path, "--text-only")
    assert rc == 2 and any("rows 2" in f for f in rep["fails"])


def test_text_only_over_ceiling_fails(tmp_path):
    _seal(tmp_path, requests=10, calls_used=10)
    rc, rep = _inspect(tmp_path, "--text-only")
    assert rc == 2
    assert any("above rows x ceiling" in f for f in rep["fails"]) and any("calls_used" in f for f in rep["fails"])


def test_text_only_tool_use_and_native_receipts_fail(tmp_path):
    _seal(tmp_path, tool_calls=1, native_rows=True)
    rc, rep = _inspect(tmp_path, "--text-only")
    assert rc == 2
    assert any("tool calls" in f for f in rep["fails"]) and any("native episode receipts" in f for f in rep["fails"])


def test_text_only_wrong_flight_commit_fails(tmp_path):
    _seal(tmp_path)
    rc, rep = _inspect(tmp_path, "--text-only", commit="d" * 40)
    assert rc == 2 and any("flight commit" in f for f in rep["fails"])


def test_native_path_unchanged_without_flag(tmp_path):
    # Without --text-only the trace and cost are not held to rows x ceiling and no text_only key appears.
    _seal(tmp_path, requests=10, calls_used=10)
    rc, rep = _inspect(tmp_path)
    assert rc == 0 and "text_only" not in rep
    # Per-row native receipts above the ceiling still fail exactly as before.
    other = tmp_path / "n"
    other.mkdir()
    _seal(other, native_rows=True)
    rc, rep = _inspect(other, ceiling=3)
    assert rc == 2 and any("above the contact ceiling 3" in f for f in rep["fails"])


def test_campaign_mode_derives_text_only_ceiling_from_the_registered_cap(tmp_path):
    # Real composed proposer cell: 3 rows, planned_model_calls 9 -> ceiling 3 per row; the sealed tree is synthetic.
    run = "SAEA-SLURP-STAGE3-TFRL-PROPOSER-I1-V1"
    att = "attempt-slurp-native-stage3-tfrl-proposer-i1-generation-v1"
    d = _seal(tmp_path, run=run, att=att, requests=9, calls_used=9)
    cmd = [sys.executable, "-B", str(INSPECT), str(tmp_path), run, att, "arm", "3", "1", "1", COMMIT,
           "--repo-root", str(REPO), "--campaign-plan", str(REPO / PLAN)]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=_env())
    rep = json.loads(proc.stdout)
    assert proc.returncode == 0 and rep["pass"] is True and rep["members"][0]["report"]["text_only"] is True
    (d / "x.trace.jsonl").write_text(
        "".join(json.dumps({"channel": "MODEL_REQUEST", "payload": {}}) + "\n" for _ in range(10)))
    proc = subprocess.run(cmd, capture_output=True, text=True, env=_env())
    assert proc.returncode == 2 and json.loads(proc.stdout)["pass"] is False


def _queue_module():
    spec = importlib.util.spec_from_file_location("tfrl_i1_queue", TFRL / "tfrl_i1_queue.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FACTS = {"rows": {"typed": 3, "ace": 18}, "accounting": {"contacts_per_row": 5}}


def test_queue_builder_tfrl_only():
    q = _queue_module()

    def load(path):
        return FACTS

    both = q.build_steps(1, "proposers", "tfrl-i1", load)
    assert [s["short"] for s in both] == ["tfrl-i1-typed", "tfrl-i1-ace"] and [s["order"] for s in both] == [1, 2]
    ace = q.build_steps(1, "proposers", "tfrl-i1", load, "ace")
    assert len(ace) == 1 and ace[0]["expected_rows"] == 18 and ace[0]["short"] == "tfrl-i1-ace"
    assert ace[0] == {**both[1], "order": 1}
    typed = q.build_steps(1, "proposers", "tfrl-i1", load, "typed")
    assert [s["expected_rows"] for s in typed] == [3]
    with pytest.raises(ValueError):
        q.build_steps(1, "proposers", "tfrl-i1", load, "bogus")
    with pytest.raises(ValueError):
        q.build_steps(1, "column", "tfrl-i1", load, "ace")
    col = q.build_steps(1, "column", "tfrl-i1", load)
    assert col[0]["ceiling_per_row"] == 5 and col[0]["expected_rows"] == 1080


@pytest.mark.skipif(sys.platform == "win32", reason="bash wrappers are exercised under WSL")
@pytest.mark.parametrize("script", ["batch_chain_tfrl_i1.sh", "tfrl_i1_flip.sh"])
def test_wrappers_parse_and_reject_bad_tfrl_only(script):
    path = str(TFRL / script)
    assert subprocess.run(["bash", "-n", path]).returncode == 0
    for only, which in (("bogus", "proposers"), ("ace", "column")):
        proc = subprocess.run(["bash", path, which], env=dict(os.environ, TFRL_ONLY=only),
                              capture_output=True, text=True)
        assert proc.returncode == 2, (script, only, proc.stderr)
