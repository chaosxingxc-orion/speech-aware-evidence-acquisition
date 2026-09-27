"""The idle-filler queue's decision rule (owner decision 162): every branch, on a synthetic host.

No WSL, no serving session, no git: the process table, the serving status and the committed fragment
reader are injected, so the rule is tested exactly as the queue calls it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "filler_queue_decide", REPO / "scripts/flights/filler/filler_queue_decide.py"
)
decide_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = decide_module  # dataclasses resolve the defining module through sys.modules
SPEC.loader.exec_module(decide_module)  # type: ignore[union-attr]

SESSION = decide_module.SESSION
COMMIT = "a" * 40
NOW = 1_800_000_000.0


def _healthy(now: float = NOW) -> dict:
    return {
        "session": {"session_id": SESSION},
        "last_monitor_sample": {"server_ok": True, "slots": {"busy": 0, "idle": 4, "total": 4}, "sampled_at": now - 30},
    }


def _ready_fragment(commit: str, relpath: str) -> dict:
    return {"cells": [{"readiness": {"state": "ready"}}]}


@pytest.fixture()
def host(tmp_path: Path):
    home, data, main = tmp_path / "home", tmp_path / "data", tmp_path / "main"
    for d in (home, data / "locks", data / "runs", data / "coordination", main / "docs" / "readiness"):
        d.mkdir(parents=True)
    for k in (1, 2, 3):
        (main / "docs" / "readiness" / f"2026-09-27-slurp-stage3-filler-fold-b-c{k:02d}-v1").mkdir()
    (main / "docs" / "readiness" / "2026-09-27-slurp-stage3-filler-fold-b-family-v1").mkdir()

    def mint(k: int, status: str = "decided") -> None:
        n = decide_module.chunk_names(k)
        path = data / "coordination" / n["package"] / "root-admission-v1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"status": status, "eligible_run_ids": [n["run"]]}), encoding="utf-8")

    def flip(k: int, commit: str = COMMIT) -> None:
        (home / decide_module.chunk_names(k)["commit_file"]).write_text(commit + "\n", encoding="utf-8")

    def env(**overrides):
        kwargs = dict(home=home, data_root=data, main=main, now=lambda: NOW, processes=lambda: [],
                      serving_status=_healthy, fragment_at=_ready_fragment, state_file=home / "state.jsonl")
        kwargs.update(overrides)
        return decide_module.Env(**kwargs)

    return {"home": home, "data": data, "main": main, "mint": mint, "flip": flip, "env": env}


def _ready_all(host, chunks=(1, 2, 3)) -> None:
    for k in chunks:
        host["mint"](k)
        host["flip"](k)


def test_launches_the_lowest_unflown_minted_flipped_chunk(host) -> None:
    _ready_all(host)
    d = decide_module.decide(host["env"]())
    assert d["decision"] == "LAUNCH" and d["chunk"] == 1 and d["commit"] == COMMIT


def test_halts_on_stop_before_anything_else(host) -> None:
    _ready_all(host)
    (host["home"] / "batch-STOP").write_text("2026-09-27T00:00:00Z arm failed\n", encoding="utf-8")
    (host["home"] / "mainline-ready").touch()
    d = decide_module.decide(host["env"]())
    assert d["decision"] == "HALT" and "arm failed" in d["reason"]


def test_never_launches_while_a_main_line_chain_is_ready(host) -> None:
    _ready_all(host)
    (host["home"] / "mainline-ready").touch()
    d = decide_module.decide(host["env"]())
    assert d["decision"] == "WAIT" and "main-line" in d["reason"]


@pytest.mark.parametrize("marker,reason", [
    ("process", "process alive"),
    ("lock", "flight.lock"),
    ("override", "override"),
    ("done-fresh", "batch-done"),
])
def test_waits_on_every_busy_signal(host, marker: str, reason: str) -> None:
    _ready_all(host)
    overrides = {}
    if marker == "process":
        overrides["processes"] = lambda: ["4242 python -m speech_aware_evidence_acquisition.core.flight.cli campaign"]
    elif marker == "lock":
        (host["data"] / "locks" / "flight.lock").touch()
    elif marker == "override":
        (host["home"] / "batch-flight-repo.txt").write_text("/x\n", encoding="utf-8")
    elif marker == "done-fresh":
        done = host["home"] / "batch-done"
        done.write_text("2026-09-27T00:00:00Z\n", encoding="utf-8")
        os.utime(done, (NOW - 60, NOW - 60))
    d = decide_module.decide(host["env"](**overrides))
    assert d["decision"] == "WAIT" and reason in d["reason"]


def test_an_old_batch_done_does_not_block(host) -> None:
    _ready_all(host)
    done = host["home"] / "batch-done"
    done.write_text("x\n", encoding="utf-8")
    os.utime(done, (NOW - 3600, NOW - 3600))
    assert decide_module.decide(host["env"]())["decision"] == "LAUNCH"


@pytest.mark.parametrize("status", [
    None,
    {"session": {"session_id": "serving-a2t-np3"}, "last_monitor_sample": {"server_ok": True, "slots": {"busy": 0}, "sampled_at": NOW}},
    {"session": {"session_id": SESSION}, "last_monitor_sample": {"server_ok": False, "slots": {"busy": 0}, "sampled_at": NOW}},
    {"session": {"session_id": SESSION}, "last_monitor_sample": {"server_ok": True, "slots": {"busy": 2}, "sampled_at": NOW}},
    {"session": {"session_id": SESSION}, "last_monitor_sample": {"server_ok": True, "slots": {"busy": 0}, "sampled_at": NOW - 3600}},
])
def test_waits_unless_np4_is_resident_healthy_idle_and_fresh(host, status) -> None:
    _ready_all(host)
    d = decide_module.decide(host["env"](serving_status=lambda: status))
    assert d["decision"] == "WAIT" and "serving not ready" in d["reason"]


def test_skips_flown_launched_unminted_and_unflipped_chunks(host) -> None:
    _ready_all(host, chunks=(1, 2))
    (host["data"] / "runs" / decide_module.chunk_names(1)["run"]).mkdir()  # c01 flown
    (host["home"] / "state.jsonl").write_text(json.dumps({"chunk": 2, "commit": COMMIT}) + "\n", encoding="utf-8")
    host["mint"](3)  # c03 minted but not flipped
    d = decide_module.decide(host["env"]())
    assert d["decision"] == "WAIT"
    assert d["checks"]["chunks"] == {"c01": "flown (runs/<run id> exists)",
                                     "c02": "launched before (queue state file)",
                                     "c03": "not flipped (no flight commit file)"}


def test_a_released_chunk_is_eligible_again(host) -> None:
    _ready_all(host, chunks=(1,))
    state = host["home"] / "state.jsonl"
    state.write_text(json.dumps({"chunk": 1, "commit": COMMIT}) + "\n"
                     + json.dumps({"chunk": 1, "released": True, "chain_rc": 7}) + "\n", encoding="utf-8")
    d = decide_module.decide(host["env"]())
    assert d["decision"] == "LAUNCH" and d["chunk"] == 1


def test_a_chunk_that_is_not_ready_at_its_flight_commit_is_not_launched(host) -> None:
    _ready_all(host, chunks=(1,))
    held = lambda commit, relpath: {"cells": [{"readiness": {"state": "held"}}]}  # noqa: E731
    d = decide_module.decide(host["env"](fragment_at=held))
    assert d["decision"] == "WAIT" and "not ready" in d["checks"]["chunks"]["c01"]


def test_an_undecided_receipt_is_not_minted(host) -> None:
    host["mint"](1, status="DRAFT-NOT-MINTED")
    host["flip"](1)
    d = decide_module.decide(host["env"]())
    assert d["decision"] == "WAIT" and d["checks"]["chunks"]["c01"] == "receipt not decided for this run id"


def test_registered_chunks_reads_only_chunk_packages(host) -> None:
    assert decide_module.registered_chunks(host["main"]) == [1, 2, 3]


def test_the_cli_prints_one_json_decision(host, capsys) -> None:
    _ready_all(host)
    status = host["home"] / "status.json"
    status.write_text(json.dumps(_healthy(time.time())), encoding="utf-8")
    (host["home"] / "mainline-ready").touch()
    decide_module.main(["--home", str(host["home"]), "--data-root", str(host["data"]), "--main", str(host["main"]),
                        "--state-file", str(host["home"] / "state.jsonl"), "--status-json", str(status)])
    out = json.loads(capsys.readouterr().out)
    assert out["decision"] == "WAIT" and "main-line" in out["reason"]
