"""``rails.probes.a2t_pop_flight``: the P-A2T whole-population regression-arm
(R0/R1) flight orchestration and 97-id EM-correct roster derivation
(docs/readiness/2026-08-19-a2t-pop-preregistration-REGISTERED.md).
Engineering-only, zero live model contact -- every test here drives
``rails.core_client.MockCoreClient`` or plain synthetic fixtures; the real
attempt directory under ``SPEECHRL_DATA_DIR`` is never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolSample
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes.a2t_pop_flight import (
    A2T_POP_ARMS,
    EM_CORRECT_N,
    R0_ARM,
    R1_ARM,
    SPLIT_IDENTITY_HASH,
    A2tPopFlightError,
    HeadroomSource,
    assert_split_identity_hash_pinned,
    build_flight_plan,
    build_flight_plan_from_attempt,
    derive_em_correct_ids,
    load_headroom_source,
    render_b1_tool_schemas,
    run_a2t_pop_flight,
    write_outputs_jsonl,
)

from test_a2t_read import (  # reuse the SAME shared audio2tool_world fixture-world helpers
    _TIER1_ID,
    _TIER1_RESPONSE,
    _TIER3_ID,
    _TIER3_RESPONSE,
    _TIER7_EMPTY_RESPONSE,
    _TIER7_ID,
    _adapter,
)
from test_a2t_s2_flight import _REGISTRY_ROWS, _row, _sample  # 12-tool synthetic registry + sample builder

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_HEADROOM_PATH = (
    _REPO_ROOT
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-08-18-pa2t-a0-read"
    / "headroom.json"
)


# ---------------------------------------------------------------------------
# load_headroom_source / assert_split_identity_hash_pinned
# ---------------------------------------------------------------------------


def _write_headroom(path: Path, **overrides) -> None:
    document = {
        "schema": "saea-a2t-a0-headroom-v1",
        "attempt_dir": "/fake/attempt/dir",
        "split_identity_hash": "deadbeef" * 8,
        "count": 3,
        "sample_ids": ["tier1_direct:000001", "tier1_direct:000002", "tier1_direct:000003"],
    }
    document.update(overrides)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_load_headroom_source_happy_path(tmp_path):
    path = tmp_path / "headroom.json"
    _write_headroom(path)
    source = load_headroom_source(path)
    assert source.attempt_dir == "/fake/attempt/dir"
    assert source.split_identity_hash == "deadbeef" * 8
    assert source.headroom_sample_ids == (
        "tier1_direct:000001",
        "tier1_direct:000002",
        "tier1_direct:000003",
    )


def test_load_headroom_source_rejects_wrong_schema(tmp_path):
    path = tmp_path / "headroom.json"
    _write_headroom(path, schema="wrong-schema")
    with pytest.raises(A2tPopFlightError, match="schema"):
        load_headroom_source(path)


def test_load_headroom_source_rejects_missing_attempt_dir(tmp_path):
    path = tmp_path / "headroom.json"
    _write_headroom(path, attempt_dir="")
    with pytest.raises(A2tPopFlightError, match="attempt_dir"):
        load_headroom_source(path)


def test_load_headroom_source_rejects_missing_split_identity_hash(tmp_path):
    path = tmp_path / "headroom.json"
    _write_headroom(path, split_identity_hash="")
    with pytest.raises(A2tPopFlightError, match="split_identity_hash"):
        load_headroom_source(path)


def test_load_headroom_source_against_the_real_registered_artifact():
    source = load_headroom_source(_REAL_HEADROOM_PATH)
    assert len(source.headroom_sample_ids) == 120
    assert source.split_identity_hash == SPLIT_IDENTITY_HASH


def test_assert_split_identity_hash_pinned_accepts_the_pinned_value():
    assert_split_identity_hash_pinned(SPLIT_IDENTITY_HASH)  # does not raise


def test_assert_split_identity_hash_pinned_rejects_drift():
    with pytest.raises(A2tPopFlightError, match="does not match the pinned"):
        assert_split_identity_hash_pinned("not-the-pinned-hash")


def test_the_real_headroom_json_split_identity_hash_matches_the_pinned_constant():
    document = json.loads(_REAL_HEADROOM_PATH.read_text(encoding="utf-8"))
    assert document["split_identity_hash"] == SPLIT_IDENTITY_HASH


# ---------------------------------------------------------------------------
# derive_em_correct_ids -- built on the SAME shared audio2tool_world fixture
# test_a2t_read.py already uses (tier1:000001 EM-correct, tier3:000004
# tool-correct-EM-wrong, tier7:000009 empty/tool-wrong).
# ---------------------------------------------------------------------------


def _write_zero_supply_outputs(path: Path, world) -> None:
    adapter = _adapter(world)
    samples_by_id = {s.sample_id: s for s in adapter.load_split("discovery")}
    rows = []
    for sample_id, response_text in (
        (_TIER1_ID, _TIER1_RESPONSE),
        (_TIER3_ID, _TIER3_RESPONSE),
        (_TIER7_ID, _TIER7_EMPTY_RESPONSE),
    ):
        sample = samples_by_id[sample_id]
        metrics = adapter.score(sample, response_text)
        rows.append(
            {
                "arm": "zero-supply",
                "sample_id": sample_id,
                "messages": [],
                "response_text": response_text,
                "metrics": dict(metrics),
                "consumption": {"records": [], "copy_rate": 0.0, "dose_realized": 0, "trace_version": "consumption-trace-v1"},
            }
        )
    path.mkdir(parents=True, exist_ok=True)
    with (path / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_derive_em_correct_ids_selects_exactly_the_tool_and_exact_match_row(audio2tool_world, tmp_path):
    attempt_dir = tmp_path / "attempt"
    _write_zero_supply_outputs(attempt_dir, audio2tool_world)
    lock = load_lock(audio2tool_world.lock_path)
    ids = derive_em_correct_ids(
        attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root, expected_n=1
    )
    assert ids == (_TIER1_ID,)


def test_derive_em_correct_ids_rejects_wrong_expected_count(audio2tool_world, tmp_path):
    attempt_dir = tmp_path / "attempt"
    _write_zero_supply_outputs(attempt_dir, audio2tool_world)
    lock = load_lock(audio2tool_world.lock_path)
    with pytest.raises(A2tPopFlightError, match="97/97 fail-closed"):
        derive_em_correct_ids(
            attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )  # default expected_n=97, but only 1 EM-correct id exists here


def test_derive_em_correct_ids_rejects_wrong_arm_rows(audio2tool_world, tmp_path):
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "arm": "supplied",
        "sample_id": _TIER1_ID,
        "messages": [],
        "response_text": _TIER1_RESPONSE,
        "metrics": {},
        "consumption": {},
    }
    (attempt_dir / "outputs.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    lock = load_lock(audio2tool_world.lock_path)
    with pytest.raises(A2tPopFlightError, match="zero-supply"):
        derive_em_correct_ids(
            attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root, expected_n=1
        )


def test_derive_em_correct_ids_rejects_duplicate_rows(audio2tool_world, tmp_path):
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "arm": "zero-supply",
        "sample_id": _TIER1_ID,
        "messages": [],
        "response_text": _TIER1_RESPONSE,
        "metrics": {},
        "consumption": {},
    }
    lines = [json.dumps(row), json.dumps(row)]
    (attempt_dir / "outputs.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    lock = load_lock(audio2tool_world.lock_path)
    with pytest.raises(A2tPopFlightError, match="duplicate"):
        derive_em_correct_ids(
            attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root, expected_n=1
        )


def test_derive_em_correct_ids_rejects_malformed_rows(audio2tool_world, tmp_path):
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    (attempt_dir / "outputs.jsonl").write_text("not json\n", encoding="utf-8")
    lock = load_lock(audio2tool_world.lock_path)
    with pytest.raises(A2tPopFlightError, match="malformed"):
        derive_em_correct_ids(
            attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root, expected_n=1
        )


# ---------------------------------------------------------------------------
# build_flight_plan / build_flight_plan_from_attempt
# ---------------------------------------------------------------------------

_SAMPLE_IDS = ("tier1_direct:000001", "tier1_direct:000002", "tier3_multi_intent:000004")


def _r1_tool_names() -> dict[str, tuple[str, ...]]:
    return {
        "tier1_direct:000001": ("tool01",),
        "tier1_direct:000002": ("tool02",),
        "tier3_multi_intent:000004": ("tool03", "tool04"),
    }


def test_build_flight_plan_happy_path():
    plan = build_flight_plan(_SAMPLE_IDS, _r1_tool_names(), _REGISTRY_ROWS)
    assert plan.sample_ids == tuple(sorted(_SAMPLE_IDS))
    assert plan.r1_tool_names_by_sample == _r1_tool_names()
    assert set(plan.registry_index) == {row["tool_name"] for row in _REGISTRY_ROWS}


def test_build_flight_plan_rejects_sample_mismatch():
    tools = _r1_tool_names()
    del tools[_SAMPLE_IDS[0]]
    with pytest.raises(A2tPopFlightError, match="does not match"):
        build_flight_plan(_SAMPLE_IDS, tools, _REGISTRY_ROWS)


def test_build_flight_plan_rejects_unknown_tool():
    tools = _r1_tool_names()
    tools[_SAMPLE_IDS[0]] = ("not-a-real-tool",)
    with pytest.raises(A2tPopFlightError, match="not present in the registry"):
        build_flight_plan(_SAMPLE_IDS, tools, _REGISTRY_ROWS)


def test_build_flight_plan_rejects_duplicate_registry_tool_name():
    dup_rows = list(_REGISTRY_ROWS) + [_row(99, "tool01")]
    with pytest.raises(A2tPopFlightError, match="duplicate tool_name"):
        build_flight_plan(_SAMPLE_IDS, _r1_tool_names(), dup_rows)


def _write_attempt_outputs(path: Path, rows: list[dict]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    with (path / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _a0_row(sample_id: str, response_text: str) -> dict:
    return {
        "arm": "zero-supply",
        "sample_id": sample_id,
        "messages": [],
        "response_text": response_text,
        "metrics": {},
        "consumption": {},
    }


def test_build_flight_plan_from_attempt_reuses_derive_a0_selected_tools(tmp_path):
    rows = [
        _a0_row("tier1_direct:000001", json.dumps([{"name": "tool01", "arguments": {}}])),
        _a0_row("tier1_direct:000002", json.dumps([{"name": "tool02", "arguments": {}}])),
    ]
    _write_attempt_outputs(tmp_path, rows)
    plan = build_flight_plan_from_attempt(
        ["tier1_direct:000001", "tier1_direct:000002"], tmp_path, _REGISTRY_ROWS
    )
    assert plan.r1_tool_names_by_sample == {
        "tier1_direct:000001": ("tool01",),
        "tier1_direct:000002": ("tool02",),
    }


# ---------------------------------------------------------------------------
# End-to-end: run_a2t_pop_flight over a MockCoreClient.
# ---------------------------------------------------------------------------

from test_a2t_s2_flight import _TinyAudio2ToolWorld  # noqa: E402 -- reused synthetic-registry world


def _mock_responder(messages):
    return json.dumps([{"name": "tool01", "arguments": {}}])


def test_run_a2t_pop_flight_end_to_end_with_mock_client(tmp_path):
    plan = build_flight_plan(_SAMPLE_IDS, _r1_tool_names(), _REGISTRY_ROWS)
    adapter = _TinyAudio2ToolWorld(tmp_path).adapter()
    samples = [_sample(sample_id) for sample_id in plan.sample_ids]
    client = MockCoreClient(responder=_mock_responder)

    counter = {"t": 0.0}

    def fake_now():
        counter["t"] += 1.0
        return counter["t"]

    summary = run_a2t_pop_flight(adapter=adapter, core_client=client, samples=samples, plan=plan, now=fake_now)

    n = len(plan.sample_ids)
    assert len(summary.results) == 2 * n
    by_arm: dict[str, list] = {}
    for result in summary.results:
        by_arm.setdefault(result.arm, []).append(result)
    assert {arm: len(rows) for arm, rows in by_arm.items()} == {R0_ARM: n, R1_ARM: n}
    assert set(by_arm) == set(A2T_POP_ARMS)

    # Fixed order per sample: R0 then R1.
    for index in range(n):
        assert summary.results[2 * index].arm == R0_ARM
        assert summary.results[2 * index + 1].arm == R1_ARM
        assert summary.results[2 * index].sample_id == summary.results[2 * index + 1].sample_id

    # R0 is byte-identical to Audio2ToolAdapter.assemble_prompt(sample, None).
    r0_sample_id = plan.sample_ids[0]
    expected_r0_messages = adapter.assemble_prompt(_sample(r0_sample_id), None)
    assert client.calls[0][0] == expected_r0_messages
    assert all(r.supplied_tool is None for r in by_arm[R0_ARM])

    # R1's supplied_tool label matches its own reused roster; prompt is
    # narrower than R0's full-registry system prompt and strips defaults.
    r1_results = {r.sample_id: r for r in by_arm[R1_ARM]}
    for sample_id in plan.sample_ids:
        expected_label = ",".join(sorted(set(plan.r1_tool_names_by_sample[sample_id])))
        assert r1_results[sample_id].supplied_tool == expected_label

    r0_system = client.calls[0][0][0]["content"]
    r1_system = client.calls[1][0][0]["content"]
    assert len(r1_system) < len(r0_system)
    assert "argument_defaults" not in r1_system


def test_run_a2t_pop_flight_rejects_plan_sample_mismatch(tmp_path):
    plan = build_flight_plan(_SAMPLE_IDS, _r1_tool_names(), _REGISTRY_ROWS)
    adapter = _TinyAudio2ToolWorld(tmp_path).adapter()
    samples = [_sample(sample_id) for sample_id in plan.sample_ids[:-1]]  # drop one
    client = MockCoreClient(responder=_mock_responder)
    with pytest.raises(A2tPopFlightError, match="not present in samples"):
        run_a2t_pop_flight(adapter=adapter, core_client=client, samples=samples, plan=plan)


def test_run_a2t_pop_flight_rejects_empty_samples(tmp_path):
    plan = build_flight_plan(_SAMPLE_IDS, _r1_tool_names(), _REGISTRY_ROWS)
    adapter = _TinyAudio2ToolWorld(tmp_path).adapter()
    client = MockCoreClient(responder=_mock_responder)
    with pytest.raises(A2tPopFlightError, match="at least one sample"):
        run_a2t_pop_flight(adapter=adapter, core_client=client, samples=[], plan=plan)


def test_write_outputs_jsonl_round_trips_r0_r1_rows(tmp_path):
    plan = build_flight_plan(_SAMPLE_IDS, _r1_tool_names(), _REGISTRY_ROWS)
    adapter = _TinyAudio2ToolWorld(tmp_path).adapter()
    samples = [_sample(sample_id) for sample_id in plan.sample_ids]
    client = MockCoreClient(responder=_mock_responder)
    summary = run_a2t_pop_flight(adapter=adapter, core_client=client, samples=samples, plan=plan)

    out_path = tmp_path / "outputs.jsonl"
    write_outputs_jsonl(out_path, summary.results)
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(summary.results)
    for line, result in zip(lines, summary.results):
        document = json.loads(line)
        assert set(document) == {"arm", "sample_id", "supplied_tool", "response", "timing"}
        assert document["arm"] in A2T_POP_ARMS


def test_em_correct_n_is_the_registered_ninety_seven():
    assert EM_CORRECT_N == 97


def test_render_b1_tool_schemas_is_reused_verbatim_from_stage2b():
    from speech_aware_evidence_acquisition.rails.probes.a2t_s2b_flight import (
        render_b1_tool_schemas as s2b_render_b1_tool_schemas,
    )

    assert render_b1_tool_schemas is s2b_render_b1_tool_schemas
