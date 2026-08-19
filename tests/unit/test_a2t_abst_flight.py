"""``rails.probes.a2t_abst_flight``: the P-A2T abstention-asymmetry 2x2
flight orchestration
(docs/readiness/2026-08-19-a2t-abst-preregistration-REGISTERED.md).
Engineering-only, zero live model contact -- every test here drives
``rails.core_client.MockCoreClient`` or plain synthetic fixtures; the real
attempt directory under ``SPEECHRL_DATA_DIR`` is never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.audio2tool import render_registry_row
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.probes.a2t_abst_flight import (
    A2T_ABST_CELLS,
    ABST_N,
    DEFAULT_SEED,
    TP_A_CELL,
    TP_S_CELL,
    TW_A_CELL,
    TW_S_CELL,
    A2tAbstFlightError,
    build_flight_plan,
    build_flight_plan_from_attempt,
    render_registry_minus_tools,
    run_a2t_abst_flight,
    seeded_abst_draw,
    write_outputs_jsonl,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_abst_flight import (
    _swap_audio_media_relpath,
)

from test_a2t_s2_flight import _REGISTRY_ROWS, _TinyAudio2ToolWorld, _row, _sample  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_HEADROOM_PATH = (
    _REPO_ROOT
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-08-18-pa2t-a0-read"
    / "headroom.json"
)


def _real_headroom_ids() -> tuple[str, ...]:
    document = json.loads(_REAL_HEADROOM_PATH.read_text(encoding="utf-8"))
    return tuple(document["sample_ids"])


# ---------------------------------------------------------------------------
# seeded_abst_draw
# ---------------------------------------------------------------------------


def test_seeded_abst_draw_returns_exactly_n_ids():
    ids = tuple(f"tier1_direct:{i:06d}" for i in range(20))
    draw = seeded_abst_draw(ids, seed=DEFAULT_SEED, n=ABST_N)
    assert len(draw) == ABST_N == 11
    assert set(draw) <= set(ids)
    assert len(set(draw)) == ABST_N  # no duplicates


def test_seeded_abst_draw_is_deterministic():
    ids = tuple(f"tier1_direct:{i:06d}" for i in range(20))
    first = seeded_abst_draw(ids, seed=DEFAULT_SEED)
    second = seeded_abst_draw(tuple(reversed(ids)), seed=DEFAULT_SEED)
    assert first == second


def test_seeded_abst_draw_rejects_too_few_ids():
    ids = tuple(f"tier1_direct:{i:06d}" for i in range(5))
    with pytest.raises(A2tAbstFlightError, match="at least 11"):
        seeded_abst_draw(ids)


def test_seeded_abst_draw_against_the_real_registered_headroom_list():
    """Proves this function works against the mission's own committed
    artifact (mirrors ``test_n0r_seeded_draw_against_the_real_registered_
    headroom_list``'s own precedent), never the real attempt outputs.jsonl."""

    headroom_ids = _real_headroom_ids()
    draw = seeded_abst_draw(headroom_ids, seed=DEFAULT_SEED, n=ABST_N)
    assert len(draw) == ABST_N
    assert set(draw) <= set(headroom_ids)


# ---------------------------------------------------------------------------
# render_registry_minus_tools -- S4's structural withholding, minus the
# derangement.
# ---------------------------------------------------------------------------


def test_render_registry_minus_tools_removes_exactly_the_named_tool():
    rendered = render_registry_minus_tools(_REGISTRY_ROWS, ["tool01"])
    lines = rendered.split("\n")
    assert len(lines) == len(_REGISTRY_ROWS) - 1
    assert render_registry_row(_REGISTRY_ROWS[0]) not in lines  # tool01 is _REGISTRY_ROWS[0]
    for row in _REGISTRY_ROWS[1:]:
        assert render_registry_row(row) in lines


def test_render_registry_minus_tools_removes_multiple_names_for_multi_intent():
    rendered = render_registry_minus_tools(_REGISTRY_ROWS, ["tool01", "tool02"])
    lines = rendered.split("\n")
    assert len(lines) == len(_REGISTRY_ROWS) - 2
    assert render_registry_row(_REGISTRY_ROWS[0]) not in lines
    assert render_registry_row(_REGISTRY_ROWS[1]) not in lines


def test_render_registry_minus_tools_is_byte_identical_for_kept_rows():
    """Every OTHER row's own rendering is untouched -- never a re-derived
    rendering, always the SAME per-row JSON ``render_registry_row`` uses for
    the full-registry form (module docstring)."""

    rendered = render_registry_minus_tools(_REGISTRY_ROWS, ["tool01"])
    full = "\n".join(render_registry_row(row) for row in _REGISTRY_ROWS[1:])
    assert rendered == full


def test_render_registry_minus_tools_rejects_unknown_tool_name():
    with pytest.raises(A2tAbstFlightError, match="unknown tool name"):
        render_registry_minus_tools(_REGISTRY_ROWS, ["not-a-real-tool"])


# ---------------------------------------------------------------------------
# build_flight_plan
# ---------------------------------------------------------------------------

_SAMPLE_IDS = ("tier1_direct:000001", "tier1_direct:000002", "tier3_multi_intent:000004")


def _correct_tool_names() -> dict[str, tuple[str, ...]]:
    return {
        "tier1_direct:000001": ("tool01",),
        "tier1_direct:000002": ("tool02",),
        "tier3_multi_intent:000004": ("tool03", "tool04"),
    }


def test_build_flight_plan_happy_path():
    plan = build_flight_plan(_SAMPLE_IDS, _correct_tool_names(), _REGISTRY_ROWS)
    assert plan.sample_ids == tuple(sorted(_SAMPLE_IDS))
    assert plan.correct_tool_names_by_sample == _correct_tool_names()
    assert set(plan.registry_index) == {row["tool_name"] for row in _REGISTRY_ROWS}


def test_build_flight_plan_tw_text_excludes_the_correct_tool_and_keeps_everything_else():
    plan = build_flight_plan(_SAMPLE_IDS, _correct_tool_names(), _REGISTRY_ROWS)
    tw_text = plan.tw_registry_text_by_sample["tier1_direct:000001"]
    assert render_registry_row(_REGISTRY_ROWS[0]) not in tw_text.split("\n")  # tool01 removed
    assert len(tw_text.split("\n")) == len(_REGISTRY_ROWS) - 1


def test_build_flight_plan_rejects_sample_mismatch():
    tools = _correct_tool_names()
    del tools[_SAMPLE_IDS[0]]
    with pytest.raises(A2tAbstFlightError, match="does not match"):
        build_flight_plan(_SAMPLE_IDS, tools, _REGISTRY_ROWS)


def test_build_flight_plan_rejects_unknown_tool():
    tools = _correct_tool_names()
    tools[_SAMPLE_IDS[0]] = ("not-a-real-tool",)
    with pytest.raises(A2tAbstFlightError, match="not present in the registry"):
        build_flight_plan(_SAMPLE_IDS, tools, _REGISTRY_ROWS)


def test_build_flight_plan_rejects_duplicate_registry_tool_name():
    dup_rows = list(_REGISTRY_ROWS) + [_row(99, "tool01")]
    with pytest.raises(A2tAbstFlightError, match="duplicate tool_name"):
        build_flight_plan(_SAMPLE_IDS, _correct_tool_names(), dup_rows)


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
    assert plan.correct_tool_names_by_sample == {
        "tier1_direct:000001": ("tool01",),
        "tier1_direct:000002": ("tool02",),
    }


# ---------------------------------------------------------------------------
# _swap_audio_media_relpath
# ---------------------------------------------------------------------------


def test_swap_audio_media_relpath_replaces_only_the_audio_part():
    messages = (
        {"role": "system", "content": "sys"},
        {"role": "user", "content": [{"type": "input_audio", "media_relpath": "real.wav"}]},
    )
    swapped = _swap_audio_media_relpath(messages, "silence.wav")
    assert swapped[0] == {"role": "system", "content": "sys"}
    assert swapped[1]["content"] == [{"type": "input_audio", "media_relpath": "silence.wav"}]
    # Never mutates the input.
    assert messages[1]["content"][0]["media_relpath"] == "real.wav"


# ---------------------------------------------------------------------------
# End-to-end: run_a2t_abst_flight over a MockCoreClient.
# ---------------------------------------------------------------------------


def _mock_responder(messages):
    return json.dumps([{"name": "tool99", "arguments": {}}])


def _silence_map(sample_ids) -> dict[str, str]:
    return {sid: f"datasets/audio2tool/public/silence_{sid.replace(':', '_')}.wav" for sid in sample_ids}


def test_run_a2t_abst_flight_end_to_end_with_mock_client(tmp_path):
    plan = build_flight_plan(_SAMPLE_IDS, _correct_tool_names(), _REGISTRY_ROWS)
    adapter = _TinyAudio2ToolWorld(tmp_path).adapter()
    samples = [_sample(sample_id) for sample_id in plan.sample_ids]
    client = MockCoreClient(responder=_mock_responder)
    silence_map = _silence_map(plan.sample_ids)

    counter = {"t": 0.0}

    def fake_now():
        counter["t"] += 1.0
        return counter["t"]

    summary = run_a2t_abst_flight(
        adapter=adapter, core_client=client, samples=samples, plan=plan,
        silence_swap_media_relpaths=silence_map, now=fake_now,
    )

    n = len(plan.sample_ids)
    assert len(summary.results) == 4 * n
    by_cell: dict[str, list] = {}
    for result in summary.results:
        by_cell.setdefault(result.arm, []).append(result)
    assert {cell: len(rows) for cell, rows in by_cell.items()} == {cell: n for cell in A2T_ABST_CELLS}
    assert set(by_cell) == set(A2T_ABST_CELLS)

    # Fixed per-sample cell order: TP-A, TP-S, TW-A, TW-S.
    for index in range(n):
        base = 4 * index
        assert summary.results[base].arm == TP_A_CELL
        assert summary.results[base + 1].arm == TP_S_CELL
        assert summary.results[base + 2].arm == TW_A_CELL
        assert summary.results[base + 3].arm == TW_S_CELL
        assert len({summary.results[base + k].sample_id for k in range(4)}) == 1

    # TP-A is byte-identical to Audio2ToolAdapter.assemble_prompt(sample, None).
    sample_id = plan.sample_ids[0]
    expected_tp_a = adapter.assemble_prompt(_sample(sample_id), None)
    assert client.calls[0][0] == expected_tp_a

    # TP-S: same system content, media_relpath swapped to the silence path.
    tp_a_messages = client.calls[0][0]
    tp_s_messages = client.calls[1][0]
    assert tp_s_messages[0]["content"] == tp_a_messages[0]["content"]
    assert tp_s_messages[1]["content"][0]["media_relpath"] == silence_map[sample_id]
    assert tp_a_messages[1]["content"][0]["media_relpath"] != silence_map[sample_id]

    # TW-A: narrower than the full registry, correct tool's row absent.
    tw_a_system = client.calls[2][0][0]["content"]
    correct_row_text = render_registry_row(_REGISTRY_ROWS[0])  # tool01, this sample's correct tool
    assert correct_row_text not in tw_a_system
    assert len(tw_a_system) < len(tp_a_messages[0]["content"])

    # TW-S: same TW-A system content, media_relpath swapped.
    tw_s_messages = client.calls[3][0]
    assert tw_s_messages[0]["content"] == client.calls[2][0][0]["content"]
    assert tw_s_messages[1]["content"][0]["media_relpath"] == silence_map[sample_id]

    # supplied_tool (withheld-tool label): None on TP cells, the correct
    # tool's own label on TW cells.
    assert by_cell[TP_A_CELL][0].supplied_tool is None
    assert by_cell[TP_S_CELL][0].supplied_tool is None
    assert by_cell[TW_A_CELL][0].supplied_tool == "tool01"
    assert by_cell[TW_S_CELL][0].supplied_tool == "tool01"


def test_run_a2t_abst_flight_rejects_missing_silence_mapping(tmp_path):
    plan = build_flight_plan(_SAMPLE_IDS, _correct_tool_names(), _REGISTRY_ROWS)
    adapter = _TinyAudio2ToolWorld(tmp_path).adapter()
    samples = [_sample(sample_id) for sample_id in plan.sample_ids]
    client = MockCoreClient(responder=_mock_responder)
    incomplete_map = _silence_map(plan.sample_ids[:-1])  # one short
    with pytest.raises(A2tAbstFlightError, match="silence_swap_media_relpaths is missing"):
        run_a2t_abst_flight(
            adapter=adapter, core_client=client, samples=samples, plan=plan,
            silence_swap_media_relpaths=incomplete_map,
        )


def test_run_a2t_abst_flight_rejects_plan_sample_mismatch(tmp_path):
    plan = build_flight_plan(_SAMPLE_IDS, _correct_tool_names(), _REGISTRY_ROWS)
    adapter = _TinyAudio2ToolWorld(tmp_path).adapter()
    samples = [_sample(sample_id) for sample_id in plan.sample_ids[:-1]]  # drop one
    client = MockCoreClient(responder=_mock_responder)
    with pytest.raises(A2tAbstFlightError, match="not present in samples"):
        run_a2t_abst_flight(
            adapter=adapter, core_client=client, samples=samples, plan=plan,
            silence_swap_media_relpaths=_silence_map(plan.sample_ids),
        )


def test_run_a2t_abst_flight_rejects_empty_samples(tmp_path):
    plan = build_flight_plan(_SAMPLE_IDS, _correct_tool_names(), _REGISTRY_ROWS)
    adapter = _TinyAudio2ToolWorld(tmp_path).adapter()
    client = MockCoreClient(responder=_mock_responder)
    with pytest.raises(A2tAbstFlightError, match="at least one sample"):
        run_a2t_abst_flight(
            adapter=adapter, core_client=client, samples=[], plan=plan,
            silence_swap_media_relpaths=_silence_map(plan.sample_ids),
        )


def test_write_outputs_jsonl_round_trips_the_four_cells(tmp_path):
    plan = build_flight_plan(_SAMPLE_IDS, _correct_tool_names(), _REGISTRY_ROWS)
    adapter = _TinyAudio2ToolWorld(tmp_path).adapter()
    samples = [_sample(sample_id) for sample_id in plan.sample_ids]
    client = MockCoreClient(responder=_mock_responder)
    summary = run_a2t_abst_flight(
        adapter=adapter, core_client=client, samples=samples, plan=plan,
        silence_swap_media_relpaths=_silence_map(plan.sample_ids),
    )

    out_path = tmp_path / "outputs.jsonl"
    write_outputs_jsonl(out_path, summary.results)
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(summary.results)
    for line, result in zip(lines, summary.results):
        document = json.loads(line)
        assert set(document) == {"arm", "sample_id", "supplied_tool", "response", "timing"}
        assert document["arm"] in A2T_ABST_CELLS


def test_abst_n_is_the_registered_eleven():
    assert ABST_N == 11
