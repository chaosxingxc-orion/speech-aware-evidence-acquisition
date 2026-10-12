"""Synthetic two-cell tests for the one-pass package re-pin (owner decision 270 A).

Each test builds a throwaway git repo with TWO registered cells that share a protocol document, a
preregistration, a README and an exposure ledger. The iterative mode is emulated exactly as the flip
scripts run it (per-cell re-pin, commit, repeat until a whole pass commits nothing; plan-pin refresh;
second loop) and compared with ONE call of ``repin_package_one_pass`` on an identical copy.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.core.flight.repin import (
    RepinError,
    compute_cell_identity,
    repin_package,
)
from speech_aware_evidence_acquisition.core.flight.repin_onepass import (
    load_refresh_fn,
    main as onepass_main,
    repin_package_one_pass,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

CARRIER = "testcarrier"
IDS = ["row-a", "row-b"]
PKG = "test-pkg"
RD = f"docs/readiness/{PKG}"
PREREG = f"docs/readiness/{PKG}-preregistration.md"
DECISION = ("coordination/test-pkg/root-admission-v1.json", "test-admission-v1")
CELLS = {"a": ("exp-a", "cell-a", "RUN-A", "arm-a"), "b": ("exp-b", "cell-b", "RUN-B", "arm-b")}

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="git/bash fixtures run in WSL")


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True, text=True)
    return done.stdout.strip()


def _write(path: Path, doc: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = doc if isinstance(doc, str) else json.dumps(doc, indent=2)
    path.write_text(text, encoding="utf-8", newline="\n")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakePrepare:
    """Stale only for the v1 artifact of ``stale_runs``; builds deterministic v2+ artifacts."""

    def __init__(self, stale_runs=(), always_stale=False):
        self.stale_runs, self.always_stale, self.calls = set(stale_runs), always_stale, 0

    def __call__(self, *, run_id, output_path, **_kw):
        self.calls += 1
        output_path = Path(output_path)
        if output_path.exists():
            if self.always_stale or (run_id in self.stale_runs and output_path.name == "phase-supply-v1.json"):
                raise RuntimeError("simulated identity mismatch")
            return {"sha256": _sha(output_path)}
        raw = json.dumps({"kind": "phase-supply", "run": run_id, "output": {"facets": {}, "values": {}}}, indent=2).encode()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(raw)
        return {"sha256": hashlib.sha256(raw).hexdigest()}


def build(tmp_path: Path, name: str = "w", doc_in_notes: bool = False) -> dict:
    root = tmp_path / name
    repo, data = root / "repo", root / "data"
    repo.mkdir(parents=True)
    data.mkdir()
    _write(repo / "configs/model/model-1.json", {"model_lock_key": "m"})
    _write(repo / "configs/dataset/dataset-1.json", {"carrier_lock_key": CARRIER})
    _write(data / DECISION[0], {"decision": DECISION[1]})
    split = split_identity_hash(prefixed(CARRIER, IDS))
    old_hashes, protocol_cells = {}, {}
    for key, (exp, cell, run, arm) in CELLS.items():
        art = data / "prepared" / run / "phase-supply-v1.json"
        art.parent.mkdir(parents=True)
        art.write_bytes(json.dumps({"kind": "phase-supply", "run": run, "stale": True, "output": {"facets": {}, "values": {}}}, indent=2).encode())
        pin = {"relpath": f"prepared/{run}/phase-supply-v1.json", "sha256": _sha(art)}
        _write(repo / f"configs/baseline/base-{key}.json", {"arm": arm, "prepared_phase_supply": pin})
        _write(repo / f"configs/experiment/{exp}.json", {
            "cells": [{"cell_id": cell, "model_fragment": "model-1", "dataset_fragment": "dataset-1",
                       "baseline_fragment": f"base-{key}", "run_id": run, "attempt_id": f"attempt-{key}",
                       "readiness": {"state": "held", "reason": "x", "requirements": [
                           {"kind": "preparation", "relpath": pin["relpath"], "sha256": pin["sha256"], "reason": "r"}]}}],
            "population": {"split_identity_hash": split}, "populations": [{"ids": list(IDS)}]})
        config = compose(repo, "model-1", "dataset-1", f"base-{key}", exp).config_hash
        old_hashes[key] = (config, protocol_hash(config, arm, split), pin)
        protocol_cells[key] = {"composed_config_hash": config, "protocol_hash": old_hashes[key][1]}
    rd = repo / RD
    _write(rd / "protocol-registered-v1.json", {"schema": "p", "cells": protocol_cells})
    doc_sha = _sha(rd / "protocol-registered-v1.json")
    notes_rows = []
    for key, (exp, cell, run, arm) in CELLS.items():
        config, proto, pin = old_hashes[key]
        plan = rd / f"{key}-generation-plan-registered-v1.json"
        _write(plan, {"cell": cell, "experiment": exp, "composed_config_hash": config,
                      "execution_plan": {"protocol_hash": proto, "run_id": run},
                      "prepared_phase_supply": {"relpath": pin["relpath"], "sha256": "0" * 64, "note": "placeholder"},
                      "protocol_document": {"relpath": f"{RD}/protocol-registered-v1.json", "sha256": doc_sha}})
        notes_rows.append(f"| 2026-01-01 | {run} | no | {RD}/{key}-generation-plan-registered-v1.json | "
                          f"protocol {proto}; {'doc ' + doc_sha + '; ' if doc_in_notes else ''}config {config}; Plan SHA256 {_sha(plan)}. |")
    _write(rd / "README.md", "".join(f"{k}: {v[0]} / {v[1]}\n" for k, v in old_hashes.items()) + f"doc {doc_sha}\n")
    _write(repo / PREREG, "".join(f"{v[1]}\n" for v in old_hashes.values()))
    _write(repo / "docs/exposure-ledger.md",
           "# Ledger\n\n| date | run/experiment id | consumed | artifacts | notes |\n| --- | --- | --- | --- | --- |\n"
           + "\n".join(notes_rows) + "\n| 2026-01-01 | OTHER | no | x.json | untouched |\n")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    msg = root / "msg.txt"
    msg.write_text("one-pass flip\n", encoding="utf-8", newline="\n")
    return {"repo": repo, "data": data, "msg": msg, "root": root, "old": old_hashes}


def clone(pkg: dict, tmp_path: Path, name: str) -> dict:
    root = tmp_path / name
    shutil.copytree(pkg["root"], root)
    return {**pkg, "repo": root / "repo", "data": root / "data", "msg": root / "msg.txt", "root": root}


def common(pkg: dict) -> dict:
    return dict(repo_root=pkg["repo"], data_root=pkg["data"], runtime_root=pkg["repo"], lock_path=pkg["repo"] / "lock.json",
                readiness_dir=RD, preregistration_path=PREREG, decision=DECISION, set_ready=True)


def commit_if_dirty(repo: Path, msg: Path) -> bool:
    if not _git(repo, "status", "--porcelain", "--untracked-files=no"):
        return False
    _git(repo, "add", "-u")
    _git(repo, "commit", "-q", "-F", str(msg))
    return True


def iterate(pkg: dict, fake) -> int:
    """The flip scripts' shape: per-cell repin + commit until a pass commits nothing; refresh + commit; loop again."""
    commits = 0

    def loop():
        nonlocal commits
        for _ in range(8):
            changed = False
            for key, (exp, *_rest) in CELLS.items():
                repin_package(experiments=[(exp, None)], prepare_supply_fn=fake, run_check_fn=None, **common(pkg))
                if commit_if_dirty(pkg["repo"], pkg["msg"]):
                    commits += 1
                    changed = True
            if not changed:
                return
        raise AssertionError("iterative emulation did not converge")

    loop()
    load_refresh_fn(pkg["repo"])(pkg["repo"], pkg["repo"] / RD)
    if commit_if_dirty(pkg["repo"], pkg["msg"]):
        commits += 1
    loop()
    return commits


class CheckSpy:
    def __init__(self, repo: Path, ledger_must_hold_final_plan_sha: bool = True):
        self.repo, self.calls, self.dirty_at_call = repo, [], []

    def __call__(self, *, repo_root, experiment, cell_id, **_kw):
        self.calls.append(cell_id)
        self.dirty_at_call.append(_git(self.repo, "status", "--porcelain", "--untracked-files=no"))
        cell = next(c for c in load_campaign_cells(self.repo, experiment) if c.document["cell_id"] == cell_id)
        ident = compute_cell_identity(self.repo, experiment, cell)
        return {"preflight": {"config_hash": ident.config_hash, "protocol_hash": ident.protocol_hash}}


def tree(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD^{tree}")


def run_one_pass(pkg: dict, fake, **kw):
    return repin_package_one_pass(
        experiments=[(e, None) for e, *_ in CELLS.values()], prepare_supply_fn=fake, commit_message_file=pkg["msg"], **common(pkg), **kw)


def test_one_pass_tree_is_byte_identical_to_the_iterative_fixed_point(tmp_path):
    base = build(tmp_path)
    it, op = clone(base, tmp_path, "it"), clone(base, tmp_path, "op")
    commits = iterate(it, FakePrepare(stale_runs={"RUN-A", "RUN-B"}))
    summary = run_one_pass(op, FakePrepare(stale_runs={"RUN-A", "RUN-B"}), run_check_fn=None)
    assert commits >= 3  # the iterative mode needs several commits for the same result
    assert tree(it["repo"]) == tree(op["repo"])
    assert _git(op["repo"], "rev-list", "--count", "HEAD") == "2"  # init + ONE flip commit
    assert summary["commit"] == _git(op["repo"], "rev-parse", "HEAD")
    for path in ("docs/exposure-ledger.md", f"{RD}/README.md", PREREG, f"{RD}/protocol-registered-v1.json",
                 f"{RD}/a-generation-plan-registered-v1.json", "configs/experiment/exp-a.json", "configs/baseline/base-b.json"):
        assert (it["repo"] / path).read_bytes() == (op["repo"] / path).read_bytes(), path
    # the fixed point itself: no old hash left, plan shas in the ledger match the plan files, doc sha matches
    ledger = (op["repo"] / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    for key, (config, proto, _pin) in op["old"].items():
        assert config not in ledger and proto not in ledger
        assert f"Plan SHA256 {_sha(op['repo'] / RD / f'{key}-generation-plan-registered-v1.json')}" in ledger
    doc_sha = _sha(op["repo"] / RD / "protocol-registered-v1.json")
    assert json.loads((op["repo"] / RD / "a-generation-plan-registered-v1.json").read_text())["protocol_document"]["sha256"] == doc_sha
    assert "untouched" in ledger


def test_a_further_iterative_pass_over_the_one_pass_result_commits_nothing(tmp_path):
    pkg = build(tmp_path)
    run_one_pass(pkg, FakePrepare(stale_runs={"RUN-A", "RUN-B"}), run_check_fn=None)
    head = _git(pkg["repo"], "rev-parse", "HEAD")
    assert iterate(pkg, FakePrepare(stale_runs={"RUN-A", "RUN-B"})) == 0
    assert _git(pkg["repo"], "rev-parse", "HEAD") == head


def test_check_runs_once_per_cell_on_the_committed_final_tree(tmp_path):
    pkg = build(tmp_path)
    spy = CheckSpy(pkg["repo"])
    summary = run_one_pass(pkg, FakePrepare(stale_runs={"RUN-A"}), run_check_fn=spy, ready_receipt_cells=["cell-b"],
                           package_name="test-pkg")
    assert spy.calls == ["cell-a", "cell-b"]
    assert spy.dirty_at_call == ["", ""]  # clean tree: the single commit already exists
    assert len(summary["checks"]) == 2
    assert (pkg["data"] / "coordination/test-pkg/check-cell-b-ready-v1.json").is_file()
    assert not (pkg["data"] / "coordination/test-pkg/check-cell-a-ready-v1.json").exists()
    assert sorted(p.name for p in (pkg["data"] / "coordination/test-pkg").glob("check-*-repin-*.json")) != []


def test_second_run_is_idempotent_but_still_checks(tmp_path):
    pkg = build(tmp_path)
    run_one_pass(pkg, FakePrepare(stale_runs={"RUN-A", "RUN-B"}), run_check_fn=None)
    head = _git(pkg["repo"], "rev-parse", "HEAD")
    spy = CheckSpy(pkg["repo"])
    summary = run_one_pass(pkg, FakePrepare(stale_runs={"RUN-A", "RUN-B"}), run_check_fn=spy)
    assert _git(pkg["repo"], "rev-parse", "HEAD") == head and summary["files_rewritten"] == {}
    assert spy.calls == ["cell-a", "cell-b"]


def test_check_mismatch_is_refused_after_the_commit(tmp_path):
    pkg = build(tmp_path)

    def bad(**_kw):
        return {"preflight": {"config_hash": "0" * 64, "protocol_hash": "1" * 64}}

    with pytest.raises(RepinError, match="measured"):
        run_one_pass(pkg, FakePrepare(), run_check_fn=bad)
    assert _git(pkg["repo"], "status", "--porcelain", "--untracked-files=no") == ""  # committed on the flip branch only


def test_refuses_dirty_tree_consumed_row_missing_receipt_and_residue(tmp_path):
    pkg = build(tmp_path)
    (pkg["repo"] / "docs/unrelated.md").write_text("x", encoding="utf-8")
    _git(pkg["repo"], "add", "docs/unrelated.md")
    _git(pkg["repo"], "commit", "-q", "-m", "u")
    (pkg["repo"] / "docs/unrelated.md").write_text("dirty", encoding="utf-8")
    with pytest.raises(RepinError, match="tracked modifications"):
        run_one_pass(pkg, FakePrepare(), run_check_fn=None)
    _git(pkg["repo"], "checkout", "--", "docs/unrelated.md")

    ledger = pkg["repo"] / "docs/exposure-ledger.md"
    original = ledger.read_text(encoding="utf-8")
    ledger.write_text(original.replace("| RUN-A | no |", "| RUN-A | yes |"), encoding="utf-8", newline="\n")
    _git(pkg["repo"], "commit", "-qam", "consume")
    with pytest.raises(RepinError, match="already consumed"):
        run_one_pass(pkg, FakePrepare(), run_check_fn=None)
    ledger.write_text(original, encoding="utf-8", newline="\n")
    _git(pkg["repo"], "commit", "-qam", "restore")

    other = clone(pkg, tmp_path, "norcpt")
    (other["data"] / DECISION[0]).unlink()
    with pytest.raises(RepinError, match="decision receipt not found"):
        run_one_pass(other, FakePrepare(stale_runs={"RUN-A"}), run_check_fn=None)

    stray = clone(pkg, tmp_path, "stray")
    config_a = stray["old"]["a"][0]
    (stray["repo"] / "docs/stray.md").write_text(f"mentions {config_a}\n", encoding="utf-8")
    _git(stray["repo"], "add", "docs/stray.md")
    _git(stray["repo"], "commit", "-q", "-m", "stray")
    with pytest.raises(RepinError, match="residue"):
        run_one_pass(stray, FakePrepare(stale_runs={"RUN-A"}), run_check_fn=None)


def test_nine_p_root_is_refused_by_the_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SAEA_ALLOW_9P_FLIP", raising=False)
    code = onepass_main(["--repo-root", "/mnt/c/definitely-not-here", "--data-root", "d", "--runtime-root", "r", "--lock-path", "l",
                         "--experiment", "e", "--readiness-dir", "x", "--preregistration", "y"])
    assert code == 64
    assert "9p" in capsys.readouterr().err


def test_a_commit_message_is_required_for_a_real_check(tmp_path):
    pkg = build(tmp_path)
    with pytest.raises(RepinError, match="committed"):
        repin_package_one_pass(experiments=[("exp-a", None)], prepare_supply_fn=FakePrepare(), run_check_fn=CheckSpy(pkg["repo"]),
                               **common(pkg))


def test_fragments_that_never_settle_are_refused_by_name(tmp_path):
    pkg = build(tmp_path)
    with pytest.raises(RepinError, match="did not settle"):
        run_one_pass(pkg, FakePrepare(always_stale=True), run_check_fn=None, max_fragment_rounds=3)


def test_a_ledger_note_quoting_the_doc_sha_ends_on_the_true_final_doc_sha(tmp_path):
    """The iterative mode leaves each row on the intermediate doc sha written by ITS cell's call (the later
    cell's call rewrites the document again and no package file still holds the intermediate sha); the
    one-pass fixed point computes the document sha once and every row carries it."""
    pkg = build(tmp_path, doc_in_notes=True)
    run_one_pass(pkg, FakePrepare(stale_runs={"RUN-A", "RUN-B"}), run_check_fn=None)
    final = _sha(pkg["repo"] / RD / "protocol-registered-v1.json")
    ledger = (pkg["repo"] / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    assert ledger.count(f"doc {final}") == 2
