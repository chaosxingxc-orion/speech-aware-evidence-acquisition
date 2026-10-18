"""The registered Solver reasoning diagnostic (owner ruling 330 A): selection, request reconstruction, the guarded re-issue and the package bindings.

Everything runs offline: stub servers only (the transport's injected ``post``), synthetic sealed traces in ``tmp_path``, and (when present on this host) the
read-only sealed smoke trace of NX-T R2b for a real-bytes reconstruction check. No model, server, tokenizer or GPU is contacted.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
DIAG_DIR = REPO / "scripts" / "flights" / "diag"
sys.path.insert(0, str(DIAG_DIR))
SPEC = importlib.util.spec_from_file_location("solver_reasoning_diag", DIAG_DIR / "solver_reasoning_diag.py")
diag = importlib.util.module_from_spec(SPEC)
sys.modules["solver_reasoning_diag"] = diag
SPEC.loader.exec_module(diag)

from speech_aware_evidence_acquisition.core.reasoning_knobs import DIAGNOSTIC_RUN_ID, ReasoningRetention  # noqa: E402

from test_llama_server_transport import (  # noqa: E402,F401  (the autouse fixture must be imported to run)
    _base_url, _boundary_payload, _fake_runtime_receipt, _fake_session, _live, _spawn_live_matching_process, _transport,
)
from test_thinking_transport_and_native_knobs import GUARD, KNOBS, MESSAGE, _post_script, _wire  # noqa: E402

SMOKE_TRACE = Path("/home/chao/saea-data/speechrl-data/runs/SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-SMOKE-4-V1/"
                   "attempt-slurp-native-stage3-nxt-r2b-solver-budget-fold-b-smoke-4-generation-v1/SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-SMOKE-4-V1.trace.jsonl")


# --------------------------------------------------------------------------------------------------------------------- synthetic rows


def _row(index: int, *, forced3: bool, forced6: bool, supplied: int, gold_empty: bool) -> dict:
    def arm(forced: bool) -> dict:
        return {"forced_close": forced, "supplied_items": supplied, "contact_id": f"c{index}", "request_key": f"flight-{index:04d}",
                "payload_sha256": "0" * 64, "gold_empty": gold_empty, "supplied_evidence_ids": [f"e{i}" for i in range(supplied)]}
    return {"sample_id": f"slurp:train:{index:06d}:audio-{index}", "arms": {diag.ARM_DELIVERING: arm(forced3), diag.ARM_RAISED: arm(forced6)}}


def _population(n: int = 600) -> list[dict]:
    rows = []
    for index in range(n):
        rows.append(_row(index, forced3=index % 3 == 0, forced6=index % 4 == 0, supplied=30 + (index * 7) % 25, gold_empty=index % 5 == 0))
    return rows


def test_every_row_falls_in_exactly_one_group_by_its_two_forced_flags():
    cases = {(True, True): "forced-both", (True, False): "forced-3072-only", (False, True): "forced-6144-only", (False, False): "natural-both"}
    for (f3, f6), group in cases.items():
        assert diag.classify_row(_row(1, forced3=f3, forced6=f6, supplied=39, gold_empty=False))["group"] == group
    assert diag.classify_row(_row(1, forced3=True, forced6=True, supplied=39, gold_empty=False))["supplied_bin"] == "lt40"
    assert diag.classify_row(_row(1, forced3=True, forced6=True, supplied=40, gold_empty=True)) == {
        "group": "forced-both", "supplied_bin": "ge40", "gold_empty": True, "supplied_items": 40}


def test_the_selection_holds_the_quotas_and_the_stratification():
    selection = diag.select_roster(_population())
    rows = selection["rows"]
    assert len(rows) == 40
    by_group = {}
    for row in rows:
        by_group.setdefault(row["group"], []).append(row)
    assert {group: len(items) for group, items in by_group.items()} == dict(diag.GROUPS)
    for group, quota in diag.GROUPS:
        cells = [(r["stratum"]["supplied_bin"], r["stratum"]["gold_empty"]) for r in by_group[group]]
        assert all(cells.count(cell) == quota // 4 for cell in diag.STRATA), (group, cells)
        assert all(r["fill"] == "stratum" for r in by_group[group])
    assert len({r["sample_id"] for r in rows}) == 40
    assert selection["selection_report"]["forced-both"]["backfilled"] == 0


def test_the_selection_is_deterministic_and_independent_of_row_order():
    population = _population()
    first = [r["sample_id"] for r in diag.select_roster(population)["rows"]]
    assert first == [r["sample_id"] for r in diag.select_roster(list(reversed(population)))["rows"]]
    assert first == [r["sample_id"] for r in diag.select_roster(population)["rows"]]
    assert first != [r["sample_id"] for r in diag.select_roster(population, seed=diag.SEED + 1)["rows"]]


def test_a_short_stratum_is_backfilled_from_its_group_and_the_shortfall_is_recorded():
    population = [r for r in _population() if not (diag.classify_row(r)["group"] == "forced-both" and diag.classify_row(r)["supplied_bin"] == "ge40"
                                                       and diag.classify_row(r)["gold_empty"])]
    # keep exactly one row in that stratum so the share (4) cannot be met
    lone = _row(9001, forced3=True, forced6=True, supplied=50, gold_empty=True)
    selection = diag.select_roster(population + [lone])
    report = selection["selection_report"]["forced-both"]
    assert report["selected"] == 16 and report["backfilled"] == 3
    assert report["cells"]["ge40/empty-gold"] == {"pool": 1, "share": 4, "taken": 1, "short": 3}
    assert sum(1 for r in selection["rows"] if r["group"] == "forced-both" and r["fill"] == "backfill") == 3


def test_rank_is_the_documented_hash():
    assert diag.rank_key(7, "forced-both", "s1") == hashlib.sha256(b"7|forced-both|s1").hexdigest()


# --------------------------------------------------------------------------------------------------------------------- reconstruction


def _payload(sample="slurp:train:000010:audio-1", contact="phase-native-module-v1-c4:solver:1:slurp:train:000010:audio-1", budget=3072, cap=4096) -> dict:
    return {"request_id": "flight-0014", "sample_id": sample, "audio_seconds": 1.79, "task_instruction": "Decide. Caf" + chr(0xE9) + " " + chr(0x2013) + " " + chr(0x4F8B),
            "history": [{"role": "agent_state", "content": "x"}, {"role": "control", "contact_id": contact, "content": "go"}],
            "decoding_params": {"temperature": 0, "seed": 20260913, "thinking_budget_tokens": budget, "max_tokens": cap, "id_slot": 1}}


def test_the_rebuilt_request_hashes_with_the_adapters_own_canonical_serialisation():
    from speech_aware_evidence_acquisition.core.model.request_types import _canonical

    payload = _payload()
    assert diag.canonical_request_bytes(payload) == _canonical(payload)
    assert diag.request_sha256(payload) == hashlib.sha256(_canonical(payload)).hexdigest()
    reordered = dict(reversed(list(payload.items())))
    assert diag.request_sha256(reordered) == diag.request_sha256(payload)         # key order never matters
    changed = _payload(budget=6144)
    assert diag.request_sha256(changed) != diag.request_sha256(payload)


def _fixture_data_root(tmp_path: Path, payloads: dict[str, dict], *, tamper: str | None = None) -> Path:
    paths = diag.sealed_paths(tmp_path)
    paths["trace"].parent.mkdir(parents=True)
    with paths["trace"].open("w", encoding="utf-8", newline="\n") as handle:
        for key, payload in payloads.items():
            sealed = diag.request_sha256(payload)
            if key == tamper:
                payload = {**payload, "task_instruction": "changed after sealing"}
            handle.write(json.dumps({"channel": "MODEL_REQUEST", "payload": {"arm": "a", "payload": payload, "payload_sha256": sealed},
                                     "record_id": f"{key}/request"}, sort_keys=True) + "\n")
            handle.write(json.dumps({"channel": "COST", "payload": {"forced_close": False}, "record_id": f"{key}/cost"}) + "\n")
    return tmp_path


def _roster_for(payloads: dict[str, dict]) -> dict:
    rows = []
    for key, payload in payloads.items():
        rows.append({"sample_id": payload["sample_id"], "group": "natural-both",
                     "reissue": {"contact_id": payload["history"][-1]["contact_id"], "request_key": key, "payload_sha256": diag.request_sha256(payload),
                                 "id_slot": payload["decoding_params"]["id_slot"]},
                     "sealed": {diag.ARM_DELIVERING: {"reasoning_content_sha256": None, "forced_close": False, "response_text_sha256": None}}})
    return {"rows": rows}


def test_verify_proves_each_rebuilt_request_hashes_to_the_sealed_payload_hash(tmp_path):
    payloads = {"flight-0014": _payload(), "flight-0020": _payload(sample="slurp:train:000011:audio-2",
                                                                    contact="phase-native-module-v1-c4:solver:1:slurp:train:000011:audio-2")}
    root = _fixture_data_root(tmp_path, payloads)
    report = diag.verify_roster(_roster_for(payloads), root)
    assert report["all_match"] and report["verified"] == 2 and report["contacts"] == 0
    assert all(r["hash_match"] and r["budget_matches_arm"] and r["control_contact_matches"] for r in report["results"])


def test_verify_fails_closed_on_a_changed_payload_a_wrong_budget_or_a_missing_record(tmp_path):
    payloads = {"flight-0014": _payload(), "flight-0020": _payload(sample="slurp:train:000011:audio-2", budget=6144, cap=7168,
                                                                    contact="phase-native-module-v1-c4:solver:0:slurp:train:000011:audio-2")}
    root = _fixture_data_root(tmp_path, payloads, tamper="flight-0014")
    roster = _roster_for(payloads)
    roster["rows"].append({**roster["rows"][0], "sample_id": "slurp:train:000099:audio-9",
                           "reissue": {**roster["rows"][0]["reissue"], "request_key": "flight-9999"}})
    report = diag.verify_roster(roster, root)
    assert not report["all_match"] and len(report["failures"]) == 3
    assert any("flight-9999" in f for f in report["failures"])


def test_the_offline_proof_covers_the_real_sealed_smoke_trace_when_it_is_present():
    if not SMOKE_TRACE.is_file():
        pytest.skip("the sealed R2b smoke trace is not on this host")
    checked = 0
    for channel, key, payload in diag.iter_trace(SMOKE_TRACE, (b'"MODEL_REQUEST"',)):
        assert diag.request_sha256(payload["payload"]) == payload["payload_sha256"], key
        checked += 1
    assert checked >= 16


# --------------------------------------------------------------------------------------------------------------------- the guarded re-issue


def _fake_send_factory(sealed_reasoning: str, *, text='{"scenario":"iot","action":"hue_lightup","entities":[]}'):
    calls = []

    def send(request_bytes: bytes) -> bytes:
        calls.append(request_bytes)
        return json.dumps({"text": text, "usage": {"prompt_tokens": 10, "completion_tokens": 20}, "finish_reason": "stop",
                           "reasoning": {"reasoning_content_sha256": hashlib.sha256(sealed_reasoning.encode()).hexdigest(), "reasoning_chars": len(sealed_reasoning),
                                         "reasoning_tokens": None, "forced_close": False}}).encode()
    return send, calls


def _reissue_fixture(slots=(0, 1, 1, 2)):
    rows, payloads = [], {}
    for index, slot in enumerate(slots):
        payload = _payload(sample=f"slurp:train:{index:06d}:audio-{index}", contact=f"phase-native-module-v1-c4:solver:1:slurp:train:{index:06d}:audio-{index}")
        payload["decoding_params"]["id_slot"] = slot
        payload["request_id"] = f"flight-{index:04d}"
        key = f"flight-{index:04d}"
        payloads[key] = {"payload": payload, "payload_sha256": diag.request_sha256(payload)}
        rows.append({"sample_id": payload["sample_id"], "group": diag.GROUPS[index % 4][0],
                     "reissue": {"request_key": key, "payload_sha256": diag.request_sha256(payload), "id_slot": slot, "contact_id": "c"},
                     "sealed": {diag.ARM_DELIVERING: {"reasoning_content_sha256": hashlib.sha256(b"same").hexdigest(), "forced_close": False,
                                                     "response_text_sha256": hashlib.sha256(b'{"scenario":"iot","action":"hue_lightup","entities":[]}').hexdigest()}}})
    return rows, payloads


def test_the_reissue_groups_requests_by_the_sealed_slot_and_sends_the_sealed_bytes(tmp_path):
    rows, payloads = _reissue_fixture()
    groups = diag.sealed_slot_groups(rows)
    assert {slot: len(items) for slot, items in groups.items()} == {0: 1, 1: 2, 2: 1}
    send, calls = _fake_send_factory("same")
    results = diag.reissue_rows(rows, payloads, send, tmp_path / "diag")
    assert len(results) == 4 and len(calls) == 4
    assert {hashlib.sha256(c).hexdigest() for c in calls} == {r["reissue"]["payload_sha256"] for r in rows}
    assert all(r["reasoning_hash_match"] and r["answer_match"] and r["forced_close_reproduced"] for r in results)
    assert all(r["request_sha256_sent"] == r["request_sha256_sealed"] for r in results)
    lines = (tmp_path / "diag" / "results.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4 and len(list((tmp_path / "diag" / "answers").glob("*.txt"))) == 4


def test_a_reasoning_hash_mismatch_is_recorded_not_raised(tmp_path):
    rows, payloads = _reissue_fixture((0,))
    send, _ = _fake_send_factory("different reasoning")
    [result] = diag.reissue_rows(rows, payloads, send, tmp_path / "diag")
    assert result["reasoning_hash_match"] is False and result["sealed_reasoning_content_sha256"] != result["reasoning_content_sha256"]
    summary = diag.summarize_results([result])
    assert summary["contacts"] == 1 and summary["by_group"][result["group"]]["reasoning_hash_match"] == 0


def test_results_carry_statistics_and_hashes_but_no_text(tmp_path):
    rows, payloads = _reissue_fixture((0,))
    send, _ = _fake_send_factory("TOPSECRET-REASONING", text='{"scenario":"iot","action":"hue_lightup","entities":[{"type":"x","filler":"TOPSECRET-ANSWER"}]}')
    diag.reissue_rows(rows, payloads, send, tmp_path / "diag")
    blob = (tmp_path / "diag" / "results.jsonl").read_text(encoding="utf-8")
    assert "TOPSECRET" not in blob


def test_a_request_that_does_not_hash_to_its_sealed_payload_is_never_sent(tmp_path):
    rows, payloads = _reissue_fixture((0,))
    key = rows[0]["reissue"]["request_key"]
    payloads[key]["payload"]["task_instruction"] = "changed"
    send, calls = _fake_send_factory("same")
    with pytest.raises(diag.DiagError, match="does not hash to the sealed payload hash"):
        diag.reissue_rows(rows, payloads, send, tmp_path / "diag")
    assert calls == []


def test_the_call_ceiling_is_a_hard_stop_and_the_first_failure_stops_the_workers(tmp_path):
    rows, payloads = _reissue_fixture((0, 0, 0, 0))
    send, calls = _fake_send_factory("same")
    with pytest.raises(diag.DiagError, match="call ceiling 2 reached"):
        diag.reissue_rows(rows, payloads, send, tmp_path / "diag", ceiling=2)
    assert len(calls) == 2
    rows, payloads = _reissue_fixture((0, 0, 0))
    seen = []

    def failing(request_bytes):
        seen.append(request_bytes)
        raise RuntimeError("server went away")

    with pytest.raises(RuntimeError, match="server went away"):
        diag.reissue_rows(rows, payloads, failing, tmp_path / "diag2")
    assert len(seen) == 1                                   # nothing is retried and the worker stops


def test_the_reissue_through_the_real_transport_retains_the_bytes_only_under_the_diagnostic_directory(tmp_path):
    """End to end over the stub server: transport with retention -> bytes on disk, hash compared with the sealed hash, nothing else written."""

    data_root = tmp_path / "data"
    data_root.mkdir()
    retention = ReasoningRetention.from_plan(SimpleNamespace(run_id=DIAGNOSTIC_RUN_ID, execution_profile="bounded-discovery-probe"), data_root)
    reasoning = "the private deliberation " + MESSAGE
    transport = _transport(_base_url(), tmp_path, post=_post_script([_wire('{"scenario":"iot","action":"hue_lightup","entities":[]}', reasoning=reasoning)], []),
                           reasoning_content_guard=GUARD, reasoning_telemetry=True, forced_close_message=MESSAGE,
                           reasoning_bytes_policy="retain-diagnostic-v1", reasoning_retention=retention)
    payload = _boundary_payload(tmp_path)
    payload["decoding_params"] = {"temperature": 0, "seed": 20260913, **KNOBS, "id_slot": 0}
    key = "flight-0001"
    payloads = {key: {"payload": payload, "payload_sha256": diag.request_sha256(payload)}}
    rows = [{"sample_id": payload["sample_id"], "group": "forced-both",
             "reissue": {"request_key": key, "payload_sha256": diag.request_sha256(payload), "id_slot": 0, "contact_id": "c"},
             "sealed": {diag.ARM_DELIVERING: {"reasoning_content_sha256": hashlib.sha256(reasoning.encode()).hexdigest(), "forced_close": True,
                                             "response_text_sha256": None}}}]
    [result] = diag.reissue_rows(rows, payloads, transport, retention.diagnostic_root)
    assert result["reasoning_hash_match"] is True and result["forced_close"] is True and result["forced_close_reproduced"] is True
    assert result["retained_relpath"] == "reasoning/5000001.txt"
    assert (retention.directory / "5000001.txt").read_bytes() == reasoning.encode()
    assert "private deliberation" not in (retention.diagnostic_root / "results.jsonl").read_text(encoding="utf-8")
    files = sorted(p.relative_to(data_root).as_posix() for p in data_root.rglob("*") if p.is_file())
    assert files == [f"diagnostics/{DIAGNOSTIC_RUN_ID}/answers/5000001.txt", f"diagnostics/{DIAGNOSTIC_RUN_ID}/reasoning/5000001.txt",
                     f"diagnostics/{DIAGNOSTIC_RUN_ID}/results.jsonl"]


# --------------------------------------------------------------------------------------------------------------------- the package


def test_the_registered_package_binds_roster_protocol_and_plan(tmp_path):
    roster, protocol, plan_doc = diag.check_registration(REPO)
    assert roster["selected_counts"] == dict(diag.GROUPS) and len(roster["rows"]) == 40
    plan = plan_doc["execution_plan"]
    assert plan["run_id"] == diag.RUN_ID == DIAGNOSTIC_RUN_ID
    assert plan["execution_profile"] == "bounded-discovery-probe" and plan["planned_model_calls"] == 56 and plan["planned_gpu_hours"] < 1
    assert protocol["claims_benefit"] is False and protocol["reissue"]["arm"] == diag.ARM_DELIVERING
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan

    validated = ExecutionPlan(**plan).validate()
    assert ReasoningRetention.from_plan(validated, tmp_path).run_id == DIAGNOSTIC_RUN_ID
    for other in ("SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1", "SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1"):
        from dataclasses import replace

        with pytest.raises(Exception, match="not the diagnostic run"):
            ReasoningRetention.from_plan(replace(validated, run_id=other), tmp_path)


def test_the_roster_rows_are_the_sealed_budget_3072_solver_requests_with_consistent_group_flags():
    roster = json.loads((REPO / diag.PACKAGE / diag.ROSTER_NAME).read_text(encoding="utf-8"))
    flags = {"forced-both": (True, True), "forced-3072-only": (True, False), "forced-6144-only": (False, True), "natural-both": (False, False)}
    for row in roster["rows"]:
        assert row["reissue"]["thinking_budget_tokens"] == 3072 and row["reissue"]["max_tokens"] == 4096
        assert row["raised_arm_request"]["thinking_budget_tokens"] == 6144 and row["raised_arm_request"]["max_tokens"] == 7168
        sealed = row["sealed"]
        assert (sealed[diag.ARM_DELIVERING]["forced_close"], sealed[diag.ARM_RAISED]["forced_close"]) == flags[row["group"]]
        assert len(row["reissue"]["payload_sha256"]) == 64 and row["sealed"][diag.ARM_DELIVERING]["reasoning_content_sha256"]
    assert len({r["sample_id"] for r in roster["rows"]}) == 40
    assert roster["raised_arm_reissue"] is True
    assert len(diag.contacts_from_roster(roster)) == 56


def test_a_changed_roster_protocol_or_plan_breaks_the_registration(tmp_path):
    package = tmp_path / diag.PACKAGE
    shutil.copytree(REPO / diag.PACKAGE, package)
    diag.check_registration(tmp_path)
    protocol = package / diag.PROTOCOL_NAME
    protocol.write_bytes(protocol.read_bytes().replace(b"false", b"true", 1))
    with pytest.raises(diag.DiagError, match="protocol_hash"):
        diag.check_registration(tmp_path)
    shutil.copy2(REPO / diag.PACKAGE / diag.PROTOCOL_NAME, protocol)
    roster = package / diag.ROSTER_NAME
    roster.write_bytes(roster.read_bytes() + b" ")
    with pytest.raises(diag.DiagError, match="roster file's sha256"):
        diag.check_registration(tmp_path)


# --------------------------------------------------------------------------------------------------------------------- the launcher


LAUNCHER = DIAG_DIR / "solver_reasoning_diag.sh"
SID = "serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1"


def _launch(tmp_path, *, sessions=(SID,), lock=False, pids="", stopped=(), existing_attempt=False):
    data = tmp_path / "data"
    (data / "locks").mkdir(parents=True, exist_ok=True)
    for sid in sessions:
        (data / "serving" / sid).mkdir(parents=True, exist_ok=True)
        (data / "serving" / sid / "session.json").write_text("{}", encoding="utf-8")
        if sid in stopped:
            (data / "serving" / sid / "session-stop.json").write_text("{}", encoding="utf-8")
    if lock:
        (data / "locks" / "flight.lock").write_text('{"pid": 1}', encoding="utf-8")
    if existing_attempt:
        (data / "diagnostics" / diag.RUN_ID / "reasoning").mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    body = f"printf '%s\\n' '{pids}'\nexit 0\n" if pids else "exit 1\n"
    (bin_dir / "pgrep").write_text("#!/bin/sh\n" + body, encoding="utf-8")
    (bin_dir / "pgrep").chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "SAEA_DATA": str(data), "SAEA_SWAP_PENDING": str(tmp_path / "no-swap"),
           "SAEA_SWAP_LOCK": str(tmp_path / "no-lock")}
    return subprocess.run(["bash", str(LAUNCHER), "--check-only"], env=env, capture_output=True, text=True, timeout=120)


@pytest.mark.skipif(shutil.which("bash") is None or os.name == "nt", reason="the launcher runs under WSL bash")
def test_the_launcher_proceeds_only_beside_the_think_budget_np4_session_with_no_flight(tmp_path):
    ok = _launch(tmp_path / "ok")
    assert ok.returncode == 0 and "OK:" in ok.stdout, ok.stderr
    for label, kwargs, needle in (
        ("lock", {"lock": True}, "flight"),
        ("flight", {"pids": "9000001 python -m speech_aware_evidence_acquisition.core.flight.cli campaign"}, "flight"),
        ("wrong-session", {"sessions": ("serving-slurp-native-candidate-five-train-a-np4-v1",)}, "not " + SID),
        ("no-session", {"sessions": ()}, "found 0"),
        ("two-sessions", {"sessions": (SID, "serving-slurp-thinking-direct-fold-b-np4-max8192-v1")}, "found 2"),
        ("stopped-session", {"stopped": (SID,)}, "found 0"),
        ("previous-attempt", {"existing_attempt": True}, "already holds an attempt"),
    ):
        refused = _launch(tmp_path / label, **kwargs)
        assert refused.returncode == 70 and needle in refused.stderr, (label, refused.returncode, refused.stderr)


# --------------------------------------------------------------------------------------------------------------------- the raised arm (coordinator decision 2)


def _raised_roster(n_forced_both: int = 2):
    rows, payloads = [], {}
    for index in range(n_forced_both):
        low = _payload(sample=f"slurp:train:{index:06d}:audio-{index}", contact=f"phase-native-module-v1-c4:solver:1:slurp:train:{index:06d}:audio-{index}")
        high = _payload(sample=low["sample_id"], contact=f"phase-native-module-v1-c4:solver:0:slurp:train:{index:06d}:audio-{index}", budget=6144, cap=7168)
        low["request_id"], high["request_id"] = f"flight-{index:04d}", f"flight-{index + 100:04d}"
        low["decoding_params"]["id_slot"] = high["decoding_params"]["id_slot"] = index % 2
        keys = (f"flight-{index:04d}", f"flight-{index + 100:04d}")
        payloads[keys[0]] = {"payload": low, "payload_sha256": diag.request_sha256(low)}
        payloads[keys[1]] = {"payload": high, "payload_sha256": diag.request_sha256(high)}
        sealed = {"reasoning_content_sha256": hashlib.sha256(b"same").hexdigest(), "forced_close": True, "response_text_sha256": None}
        rows.append({"sample_id": low["sample_id"], "group": "forced-both",
                     "reissue": {"request_key": keys[0], "payload_sha256": diag.request_sha256(low), "id_slot": index % 2, "contact_id": low["history"][-1]["contact_id"]},
                     "raised_arm_request": {"request_key": keys[1], "payload_sha256": diag.request_sha256(high), "id_slot": index % 2,
                                            "contact_id": high["history"][-1]["contact_id"]},
                     "sealed": {diag.ARM_DELIVERING: sealed, diag.ARM_RAISED: sealed}})
    rows.append({"sample_id": "slurp:train:000900:audio-9", "group": "natural-both",
                 "reissue": {"request_key": "k", "payload_sha256": "0" * 64, "id_slot": 0, "contact_id": "c"}, "sealed": {diag.ARM_DELIVERING: {}}})
    return {"rows": rows, "raised_arm_reissue": True}, payloads


def test_contacts_put_every_3072_request_first_then_the_6144_requests_of_the_forced_both_rows():
    roster, _ = _raised_roster()
    contacts = diag.contacts_from_roster(roster)
    assert [(c["arm"], c["group"]) for c in contacts] == [("budget-3072", "forced-both")] * 2 + [("budget-3072", "natural-both")] + [("solver-6144", "forced-both")] * 2
    off = dict(roster, raised_arm_reissue=False)
    assert len(diag.contacts_from_roster(off)) == 3
    groups = diag.sealed_slot_groups(contacts)
    assert [c["arm"] for c in groups[0]] == ["budget-3072", "budget-3072", "solver-6144"]
    assert all(group[0]["arm"] == "budget-3072" for group in groups.values())          # within a slot the 3072 request leads


def test_the_6144_requests_rebuild_to_their_sealed_hashes_with_the_6144_budget(tmp_path):
    roster, payloads = _raised_roster()
    roster["rows"].pop()                                     # drop the natural row (no trace record)
    root = _fixture_data_root(tmp_path, {key: record["payload"] for key, record in payloads.items()})
    report = diag.verify_roster(roster, root)
    assert report["all_match"] and report["contacts_checked"] == 4
    assert sorted(r["arm"] for r in report["results"]) == ["budget-3072", "budget-3072", "solver-6144", "solver-6144"]
    wrong = {**roster, "rows": [dict(roster["rows"][0], raised_arm_request=dict(roster["rows"][0]["reissue"]))]}       # a 3072 request posing as the raised one
    assert not diag.verify_roster(wrong, root)["all_match"]


def test_the_raised_contacts_are_sent_after_the_low_ones_and_keep_their_own_files_and_sealed_facts(tmp_path):
    roster, payloads = _raised_roster(1)
    roster["rows"].pop()
    send, calls = _fake_send_factory("same")
    contacts = diag.contacts_from_roster(roster)
    results = diag.reissue_rows(contacts, payloads, send, tmp_path / "diag", ceiling=56)
    assert [r["arm"] for r in results] == ["budget-3072", "solver-6144"]
    assert [hashlib.sha256(c).hexdigest() for c in calls] == [contacts[0]["reissue"]["payload_sha256"], contacts[1]["reissue"]["payload_sha256"]]
    assert sorted(p.name for p in (tmp_path / "diag" / "answers").glob("*")) == ["slurp_train_000000_audio-0.b6144.txt", "slurp_train_000000_audio-0.txt"]
    summary = diag.summarize_results(results)
    assert summary["by_group"]["forced-both"]["contacts"] == 1 and summary["by_group"]["forced-both@6144"]["contacts"] == 1


def test_the_plan_ceiling_covers_all_56_contacts_and_stays_under_one_gpu_hour():
    roster, _protocol, plan_doc = diag.check_registration(REPO)
    assert len(diag.contacts_from_roster(roster)) == 56 == plan_doc["execution_plan"]["planned_model_calls"] == diag.CALL_CEILING
    assert plan_doc["execution_plan"]["planned_gpu_hours"] < 1.0
    budget = plan_doc["budget"]
    assert budget["re_issues_budget_3072"] == 40 and budget["re_issues_budget_6144"] == 16
    assert plan_doc["execution_plan"]["planned_speech_audio_seconds"] >= 56 * 4.73
