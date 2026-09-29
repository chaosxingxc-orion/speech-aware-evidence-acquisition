"""The idle watchdog's pure decision rules (owner decision 182): ready-chain selection, the
SERVER-DEATH STOP classifier and the uptime-restart rule (coordinator's 2026-09-28 night
diagnosis) -- every branch, on synthetic facts. No WSL, no real markers, no subprocess: file
existence and file content are injected, so each rule is tested exactly as ``idle_watchdog.sh``
calls it.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


select_module = _load("idle_watchdog_select", "scripts/flights/batch/idle_watchdog_select.py")
recovery_module = _load("idle_watchdog_recovery", "scripts/flights/batch/idle_watchdog_recovery.py")

select_entry = select_module.select_entry
classify_stop = recovery_module.classify_stop
extract_log_path = recovery_module.extract_log_path
restart_needs_uptime = recovery_module.restart_needs_uptime
COMMIT_A = "a" * 40
COMMIT_B = "b" * 40


def _entry(name, **overrides):
    base = {
        "name": name,
        "carrier": "slurp",
        "geometry": "slurp-np4",
        "chain_script": f"scripts/flights/{name}/batch_chain_{name}.sh",
        "flight_commit_file": f"/home/chao/{name}-flight-commit.txt",
        "hold_file": None,
        "enabled": True,
    }
    base.update(overrides)
    return base


def _config(chains, allowed_carriers=("slurp",)):
    return {"allowed_carriers": list(allowed_carriers), "chains": chains}


def _select(config, existing=(), contents=None, batch_flight_commit=None,
            batch_done_present=False, stop_present=False):
    existing = set(existing)
    contents = contents or {}
    return select_entry(
        config,
        exists=lambda p: p in existing,
        read_first_line=lambda p: contents.get(p, ""),
        batch_flight_commit=batch_flight_commit,
        batch_done_present=batch_done_present,
        stop_present=stop_present,
    )


# ---------------------------------------------------------------- the happy path


def test_selects_first_entry_when_its_flight_commit_exists_and_unflown():
    config = _config([_entry("rankvis")])
    result = _select(config, existing=["/home/chao/rankvis-flight-commit.txt"],
                      contents={"/home/chao/rankvis-flight-commit.txt": COMMIT_A})
    assert result["decision"] == "launch"
    assert result["entry"] == "rankvis"
    assert result["commit"] == COMMIT_A
    assert result["geometry"] == "slurp-np4"
    assert any("selected" in line for line in result["log"])


def test_null_flight_commit_file_has_no_gate():
    config = _config([_entry("filler", flight_commit_file=None, ext4_copy_target="/home/chao/saea-queue/filler_queue.sh")])
    result = _select(config)
    assert result["decision"] == "launch"
    assert result["entry"] == "filler"
    assert result["commit"] is None
    assert result["ext4_copy_target"] == "/home/chao/saea-queue/filler_queue.sh"


# ---------------------------------------------------------------- missing / empty commit files


def test_skips_entry_with_missing_flight_commit_file_and_falls_through():
    config = _config([_entry("wsv1"), _entry("w4sv")])
    result = _select(config, existing=["/home/chao/w4sv-flight-commit.txt"],
                      contents={"/home/chao/w4sv-flight-commit.txt": COMMIT_A})
    assert result["decision"] == "launch"
    assert result["entry"] == "w4sv"
    assert any("wsv1" in line and "missing" in line for line in result["log"])


def test_skips_entry_with_empty_flight_commit_file():
    config = _config([_entry("rankvis"), _entry("wsv1")])
    result = _select(config, existing=["/home/chao/rankvis-flight-commit.txt", "/home/chao/wsv1-flight-commit.txt"],
                      contents={"/home/chao/rankvis-flight-commit.txt": "", "/home/chao/wsv1-flight-commit.txt": COMMIT_A})
    assert result["decision"] == "launch"
    assert result["entry"] == "wsv1"
    assert any("rankvis" in line and "empty" in line for line in result["log"])


def test_no_eligible_entry_when_all_flight_commit_files_missing():
    config = _config([_entry("wsv1"), _entry("w4sv")])
    result = _select(config)
    assert result["decision"] == "none"
    assert result["entry"] is None
    assert "no eligible entry in the ready-chain list" in result["log"]


# ---------------------------------------------------------------- hold files


def test_skips_entry_with_hold_file_present():
    config = _config([_entry("wsv1", hold_file="/home/chao/saea-queue/pre-wsv.hold"), _entry("w4sv")])
    result = _select(
        config,
        existing=["/home/chao/saea-queue/pre-wsv.hold", "/home/chao/wsv1-flight-commit.txt", "/home/chao/w4sv-flight-commit.txt"],
        contents={"/home/chao/wsv1-flight-commit.txt": COMMIT_A, "/home/chao/w4sv-flight-commit.txt": COMMIT_B},
    )
    assert result["decision"] == "launch"
    assert result["entry"] == "w4sv"
    assert any("wsv1" in line and "hold file" in line for line in result["log"])


def test_absent_hold_file_does_not_block():
    config = _config([_entry("wsv1", hold_file="/home/chao/saea-queue/pre-wsv.hold")])
    result = _select(config, existing=["/home/chao/wsv1-flight-commit.txt"],
                      contents={"/home/chao/wsv1-flight-commit.txt": COMMIT_A})
    assert result["decision"] == "launch"
    assert result["entry"] == "wsv1"


# ---------------------------------------------------------------- batch-done already recorded


def test_skips_entry_already_done_at_its_commit():
    config = _config([_entry("rankvis"), _entry("wsv1")])
    result = _select(
        config,
        existing=["/home/chao/rankvis-flight-commit.txt", "/home/chao/wsv1-flight-commit.txt"],
        contents={"/home/chao/rankvis-flight-commit.txt": COMMIT_A, "/home/chao/wsv1-flight-commit.txt": COMMIT_B},
        batch_flight_commit=COMMIT_A,
        batch_done_present=True,
    )
    assert result["decision"] == "launch"
    assert result["entry"] == "wsv1"
    assert any("rankvis" in line and "batch-done already present" in line for line in result["log"])


def test_does_not_skip_when_batch_done_is_for_a_different_commit():
    config = _config([_entry("rankvis")])
    result = _select(
        config,
        existing=["/home/chao/rankvis-flight-commit.txt"],
        contents={"/home/chao/rankvis-flight-commit.txt": COMMIT_A},
        batch_flight_commit=COMMIT_B,
        batch_done_present=True,
    )
    assert result["decision"] == "launch"
    assert result["entry"] == "rankvis"


def test_does_not_skip_when_batch_done_is_absent_even_at_the_same_commit():
    config = _config([_entry("rankvis")])
    result = _select(
        config,
        existing=["/home/chao/rankvis-flight-commit.txt"],
        contents={"/home/chao/rankvis-flight-commit.txt": COMMIT_A},
        batch_flight_commit=COMMIT_A,
        batch_done_present=False,
    )
    assert result["decision"] == "launch"


# ---------------------------------------------------------------- STOP present


def test_stop_present_returns_none_regardless_of_eligible_entries():
    config = _config([_entry("rankvis")])
    result = _select(config, existing=["/home/chao/rankvis-flight-commit.txt"],
                      contents={"/home/chao/rankvis-flight-commit.txt": COMMIT_A}, stop_present=True)
    assert result["decision"] == "none"
    assert result["entry"] is None
    assert "STOP" in result["log"][0]


# ---------------------------------------------------------------- disabled entries


def test_skips_disabled_entry():
    config = _config([_entry("e41-sub10", enabled=False, note="deferred"), _entry("filler", flight_commit_file=None)])
    result = _select(config)
    assert result["decision"] == "launch"
    assert result["entry"] == "filler"
    assert any("e41-sub10" in line and "disabled" in line and "deferred" in line for line in result["log"])


def test_disabled_entry_is_skipped_even_if_otherwise_eligible():
    config = _config([_entry("rankvis", enabled=False)])
    result = _select(config, existing=["/home/chao/rankvis-flight-commit.txt"],
                      contents={"/home/chao/rankvis-flight-commit.txt": COMMIT_A})
    assert result["decision"] == "none"


# ---------------------------------------------------------------- carrier gate (owner directive 2026-09-28)


def test_skips_entry_with_no_carrier_declared():
    config = _config([_entry("rankvis", carrier=None), _entry("wsv1")])
    result = _select(config, existing=["/home/chao/wsv1-flight-commit.txt"],
                      contents={"/home/chao/wsv1-flight-commit.txt": COMMIT_A})
    assert result["decision"] == "launch"
    assert result["entry"] == "wsv1"
    assert any("rankvis" in line and "no carrier" in line for line in result["log"])


def test_skips_entry_with_carrier_not_in_allowed_carriers():
    config = _config([_entry("e41-sub10", carrier="earnings", enabled=True), _entry("rankvis")],
                      allowed_carriers=("slurp",))
    result = _select(config, existing=["/home/chao/e41-sub10-flight-commit.txt", "/home/chao/rankvis-flight-commit.txt"],
                      contents={"/home/chao/e41-sub10-flight-commit.txt": COMMIT_A,
                                "/home/chao/rankvis-flight-commit.txt": COMMIT_B})
    assert result["decision"] == "launch"
    assert result["entry"] == "rankvis"
    assert any("e41-sub10" in line and "not in allowed_carriers" in line for line in result["log"])


def test_empty_allowed_carriers_admits_any_declared_carrier():
    config = _config([_entry("e41-sub10", carrier="earnings")], allowed_carriers=())
    result = _select(config, existing=["/home/chao/e41-sub10-flight-commit.txt"],
                      contents={"/home/chao/e41-sub10-flight-commit.txt": COMMIT_A})
    assert result["decision"] == "launch"
    assert result["entry"] == "e41-sub10"


# ---------------------------------------------------------------- the shipped config sanity-checks itself


def test_shipped_ready_chains_config_matches_the_documented_contract():
    config = select_module.load_config(REPO / "scripts/flights/batch/ready_chains.json")
    assert config["allowed_carriers"] == ["slurp"]
    names = [c["name"] for c in config["chains"]]
    assert names == ["rankvis", "wsv1", "w4sv", "e41-sub10", "filler"]
    by_name = {c["name"]: c for c in config["chains"]}
    assert by_name["e41-sub10"]["enabled"] is False
    assert by_name["e41-sub10"]["carrier"] == "earnings"
    for name in ("rankvis", "wsv1", "w4sv", "filler"):
        assert by_name[name]["enabled"] is True
        assert by_name[name]["carrier"] == "slurp"
    assert by_name["filler"]["flight_commit_file"] is None
    assert by_name["filler"]["ext4_copy_target"] == "/home/chao/saea-queue/filler_queue.sh"
    for entry in config["chains"]:
        assert "carrier" in entry and entry["carrier"], entry["name"]


def test_shipped_config_is_valid_json_readable_by_json_module():
    text = (REPO / "scripts/flights/batch/ready_chains.json").read_text(encoding="utf-8")
    parsed = json.loads(text)
    assert isinstance(parsed["chains"], list) and len(parsed["chains"]) == 5


# ================================================================== the STOP-text classifier
# (coordinator diagnosis, 2026-09-28 night: the resident llama-server died on a CUDA abort after
# 14.6 h, and the COMP-1 resume attempt then STOPped on a urllib3 RemoteDisconnected / "Remote end
# closed connection" -- the server was gone, not the experiment).


def test_classify_stop_true_on_remote_disconnected_in_the_stop_text_itself():
    assert classify_stop("2026-09-29T00:03:00Z worker exit 1 (urllib3.exceptions.RemoteDisconnected)") is True


def test_classify_stop_true_on_remote_end_closed_connection():
    assert classify_stop("2026-09-29T00:03:00Z ConnectionError: Remote end closed connection without response") is True


def test_classify_stop_true_when_the_marker_is_only_in_the_referenced_log_text():
    stop_text = "2026-09-29T00:03:00Z arm failed on step 1 (campaign rc 1, inspect rc 0); see /home/chao/batch-campaign-1.log"
    log_text = "Traceback (most recent call last):\n  ...\nurllib3.exceptions.ProtocolError: Remote end closed connection without response"
    assert classify_stop(stop_text, log_text) is True


def test_classify_stop_false_on_an_unrelated_failure():
    assert classify_stop("2026-09-29T00:03:00Z batch flight worktree has tracked changes") is False


def test_classify_stop_false_on_empty_text():
    assert classify_stop("") is False


def test_classify_stop_false_does_not_fire_on_partial_or_near_miss_text():
    # "disconnected" alone, or a different exception name, is never enough -- only the two exact
    # markers ever count (never any other STOP text, per owner decision 182's recovery carve-out).
    assert classify_stop("2026-09-29T00:03:00Z the client disconnected unexpectedly") is False
    assert classify_stop("2026-09-29T00:03:00Z requests.exceptions.ConnectionError: reset by peer") is False


def test_extract_log_path_from_the_batch_driver_see_convention():
    text = "arm failed on step 1 (campaign rc 1, inspect rc 0); see /home/chao/batch-campaign-1-roll3-20260929T000000Z.log"
    assert extract_log_path(text) == "/home/chao/batch-campaign-1-roll3-20260929T000000Z.log"


def test_extract_log_path_strips_trailing_punctuation():
    assert extract_log_path("...; see /home/chao/x.log.") == "/home/chao/x.log"
    assert extract_log_path("...; see /home/chao/x.log,") == "/home/chao/x.log"


def test_extract_log_path_none_when_no_see_clause():
    assert extract_log_path("batch-STOP: flight.lock present before step 1") is None


# ================================================================== the uptime-restart rule


def test_restart_needs_uptime_true_past_the_bound():
    assert restart_needs_uptime(43201.0, max_uptime_seconds=43200.0) is True


def test_restart_needs_uptime_false_at_or_under_the_bound():
    assert restart_needs_uptime(43200.0, max_uptime_seconds=43200.0) is False
    assert restart_needs_uptime(100.0, max_uptime_seconds=43200.0) is False


def test_restart_needs_uptime_false_when_elapsed_is_unknown():
    # None (no readable process) is a missing fact, not evidence of an old server: never forces a
    # restart on its own.
    assert restart_needs_uptime(None, max_uptime_seconds=43200.0) is False


def test_restart_needs_uptime_default_bound_is_twelve_hours():
    assert recovery_module.DEFAULT_MAX_UPTIME_SECONDS == 12 * 3600.0
    assert restart_needs_uptime(12 * 3600.0 + 1) is True
    assert restart_needs_uptime(12 * 3600.0) is False


def test_restart_needs_uptime_matches_the_coordinators_incident_figures():
    # The server that died was resident 14.6 h; the bound is 12 h, so this specific incident would
    # have been caught by the proactive restart had it fired earlier.
    fourteen_point_six_hours = 14.6 * 3600.0
    assert restart_needs_uptime(fourteen_point_six_hours, max_uptime_seconds=12 * 3600.0) is True
