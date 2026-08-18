"""``rails.probes.a2t_s2b_flight``: the P-A2T Stage-2b two-arm supply-probe
flight orchestration
(docs/readiness/2026-08-18-pa2t-stage2b-preregistration-REGISTERED.md).
Engineering-only, zero live model contact -- every test here drives
``rails.core_client.MockCoreClient`` or plain synthetic fixtures; the real
Stage-2 arm-plan under ``SPEECHRL_DATA_DIR`` is never touched (a hand-built
``ArmPlan`` stands in for it, mirroring the mission's own "reused verbatim"
contract at the type level).
"""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_s2_read import ArmPlan
from speech_aware_evidence_acquisition.data.audio2tool import render_registry_row
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolSample
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes.a2t_s2b_flight import (
    A2T_S2B_ARMS,
    B1_ARM,
    B2_ARM,
    B2_HIGHLIGHT_HEADER,
    B2_HIGHLIGHT_HEADER_SHA256,
    A2tS2bFlightError,
    build_flight_plan,
    render_b1_tool_schemas,
    render_b2_tool_schemas,
    run_a2t_s2b_flight,
    write_outputs_jsonl,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import HeadroomManifest

from test_a2t_s2_flight import _REGISTRY_ROWS, _row  # reuse the SAME 12-tool synthetic registry

# ---------------------------------------------------------------------------
# Small ArmPlan fixture standing in for Stage-2's real, already-flown
# {RUN_ID}.arm-plan.json (loaded verbatim by a real launcher via
# analysis.a2t_s2_read.load_arm_plan; here constructed directly since
# ArmPlan is a plain, already-tested dataclass -- no need for a second JSON
# round trip in THIS module's own tests).
# ---------------------------------------------------------------------------

_SAMPLE_IDS = (
    "tier1_direct:000001",
    "tier1_direct:000002",
    "tier1_direct:000003",
    "tier3_multi_intent:000004",
    "tier3_multi_intent:000005",
)


def _small_arm_plan(**overrides) -> tuple[HeadroomManifest, ArmPlan]:
    headroom = HeadroomManifest(sample_ids=_SAMPLE_IDS, attempt_dir="/fake", split_identity_hash=None)
    selected_tools = {
        "tier1_direct:000001": ("tool01",),
        "tier1_direct:000002": ("tool02",),
        "tier1_direct:000003": ("tool03",),
        "tier3_multi_intent:000004": ("tool04", "tool05"),
        "tier3_multi_intent:000005": ("tool06",),
    }
    s1p_tool_names = {sid: names for sid, names in selected_tools.items()}
    s4_tool_name = {
        "tier1_direct:000001": "tool02",
        "tier1_direct:000002": "tool03",
        "tier1_direct:000003": "tool01",
        "tier3_multi_intent:000004": "tool06",
        "tier3_multi_intent:000005": "tool04",
    }
    # A Sattolo-style cycle over every distinct tool s4_tool_name touches
    # PLUS every tool selected_tools names (build_flight_plan's own global
    # fixed-point check scans this dict, not the per-sample maps).
    s4_derangement = {
        "tool01": "tool02",
        "tool02": "tool03",
        "tool03": "tool01",
        "tool04": "tool06",
        "tool05": "tool04",
        "tool06": "tool05",
    }
    kwargs = dict(
        seed=20260807,
        headroom_ids=_SAMPLE_IDS,
        n0r_sample_ids=_SAMPLE_IDS[:2],
        selected_tools=selected_tools,
        s1p_tool_names=s1p_tool_names,
        s2_tool_names={sid: names for sid, names in selected_tools.items()},
        s4_derangement=s4_derangement,
        s4_tool_name=s4_tool_name,
    )
    kwargs.update(overrides)
    return headroom, ArmPlan(**kwargs)


_FULL_REGISTRY_TEXT = "\n".join(render_registry_row(row) for row in _REGISTRY_ROWS)


def _sample(sample_id: str) -> Audio2ToolSample:
    return Audio2ToolSample(
        sample_id=sample_id,
        audio_ref=AudioRef(path="unused", sha256="0" * 64).validate(),
        audio_seconds=1.0,
        media_relpath=f"datasets/audio2tool/public/{sample_id.replace(':', '_')}.wav",
    )


# ---------------------------------------------------------------------------
# render_b1_tool_schemas / render_b2_tool_schemas
# ---------------------------------------------------------------------------


def test_render_b1_tool_schemas_strips_defaults_and_matches_row_joined():
    rows = [_REGISTRY_ROWS[0], _REGISTRY_ROWS[1]]
    rendered = render_b1_tool_schemas(rows)
    assert rendered == "\n".join(render_registry_row(row, strip_defaults=True) for row in rows)
    for line in rendered.split("\n"):
        assert "argument_defaults" not in json.loads(line)


def test_render_b2_tool_schemas_is_byte_precise_composition():
    wrong_row = _REGISTRY_ROWS[3]
    result = render_b2_tool_schemas(_FULL_REGISTRY_TEXT, wrong_row)
    assert result == (
        f"{_FULL_REGISTRY_TEXT}\n\n{B2_HIGHLIGHT_HEADER}\n{render_registry_row(wrong_row)}"
    )
    assert result.startswith(_FULL_REGISTRY_TEXT + "\n\n")
    assert result.endswith(render_registry_row(wrong_row))
    assert B2_HIGHLIGHT_HEADER in result


def test_render_b2_tool_schemas_wrong_row_keeps_its_defaults():
    """Unlike B1, B2's wrong row is rendered WITHOUT stripping defaults
    (module docstring: this arm probes schema/attention, not the
    default-value channel)."""

    wrong_row = dict(_REGISTRY_ROWS[0])
    wrong_row["argument_defaults"] = "deviceId='light_1'"
    result = render_b2_tool_schemas(_FULL_REGISTRY_TEXT, wrong_row)
    assert "argument_defaults" in json.loads(result.split("\n")[-1])


def test_b2_highlight_header_text_is_pinned_by_hash():
    assert hashlib.sha256(B2_HIGHLIGHT_HEADER.encode("utf-8")).hexdigest() == B2_HIGHLIGHT_HEADER_SHA256


def test_b2_highlight_header_names_particularly_relevant():
    # The prereg's own quoted phrase (section 1): a clearly-marked
    # "particularly relevant" header.
    assert "particularly relevant" in B2_HIGHLIGHT_HEADER.lower()


# ---------------------------------------------------------------------------
# build_flight_plan
# ---------------------------------------------------------------------------


def test_build_flight_plan_happy_path_reuses_stage2_mapping_verbatim():
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    assert plan.headroom_ids == tuple(sorted(_SAMPLE_IDS))
    assert plan.full_registry_text == _FULL_REGISTRY_TEXT
    for sample_id in plan.headroom_ids:
        assert plan.b1_tool_names_by_sample[sample_id] == arm_plan.s1p_tool_names[sample_id]
        assert plan.b2_wrong_tool_by_sample[sample_id] == arm_plan.s4_tool_name[sample_id]
        # Never a fixed point: the reused wrong tool is never one of the
        # sample's own correctly selected tools.
        assert plan.b2_wrong_tool_by_sample[sample_id] not in arm_plan.selected_tools[sample_id]


def test_build_flight_plan_is_deterministic():
    headroom, arm_plan = _small_arm_plan()
    plan1 = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    plan2 = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    assert plan1.b1_tool_names_by_sample == plan2.b1_tool_names_by_sample
    assert plan1.b2_wrong_tool_by_sample == plan2.b2_wrong_tool_by_sample


def test_build_flight_plan_rejects_headroom_arm_plan_mismatch():
    headroom, arm_plan = _small_arm_plan()
    headroom = HeadroomManifest(
        sample_ids=headroom.sample_ids[:-1], attempt_dir=headroom.attempt_dir, split_identity_hash=None
    )
    with pytest.raises(A2tS2bFlightError, match="does not match"):
        build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)


def test_build_flight_plan_rejects_duplicate_registry_tool_name():
    headroom, arm_plan = _small_arm_plan()
    dup_rows = list(_REGISTRY_ROWS) + [_row(99, "tool01")]
    with pytest.raises(A2tS2bFlightError, match="duplicate tool_name"):
        build_flight_plan(headroom, arm_plan, dup_rows, _FULL_REGISTRY_TEXT)


def test_build_flight_plan_rejects_missing_s1p_mapping():
    headroom, arm_plan = _small_arm_plan()
    s1p = dict(arm_plan.s1p_tool_names)
    del s1p[_SAMPLE_IDS[0]]
    headroom, arm_plan = _small_arm_plan(s1p_tool_names=s1p)
    with pytest.raises(A2tS2bFlightError, match="s1p_tool_names has no entry"):
        build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)


def test_build_flight_plan_rejects_missing_s4_mapping():
    headroom, arm_plan = _small_arm_plan()
    s4 = dict(arm_plan.s4_tool_name)
    del s4[_SAMPLE_IDS[0]]
    headroom, arm_plan = _small_arm_plan(s4_tool_name=s4)
    with pytest.raises(A2tS2bFlightError, match="s4_tool_name has no entry"):
        build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)


def test_build_flight_plan_rejects_unknown_b1_tool():
    headroom, arm_plan = _small_arm_plan()
    s1p = dict(arm_plan.s1p_tool_names)
    s1p[_SAMPLE_IDS[0]] = ("not-a-real-tool",)
    headroom, arm_plan = _small_arm_plan(s1p_tool_names=s1p)
    with pytest.raises(A2tS2bFlightError, match="absent from the loaded registry"):
        build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)


def test_build_flight_plan_rejects_unknown_b2_tool():
    headroom, arm_plan = _small_arm_plan()
    s4 = dict(arm_plan.s4_tool_name)
    s4[_SAMPLE_IDS[0]] = "not-a-real-tool"
    headroom, arm_plan = _small_arm_plan(s4_tool_name=s4)
    with pytest.raises(A2tS2bFlightError, match="absent from the loaded registry"):
        build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)


def test_build_flight_plan_rejects_per_sample_fixed_point():
    """The reused wrong tool coincides with the sample's own correct
    selection -- a fail-closed defense-in-depth recheck (module docstring),
    distinct from the global derangement fixed-point check below."""

    headroom, arm_plan = _small_arm_plan()
    s4 = dict(arm_plan.s4_tool_name)
    s4[_SAMPLE_IDS[0]] = "tool01"  # == selected_tools[_SAMPLE_IDS[0]]
    headroom, arm_plan = _small_arm_plan(s4_tool_name=s4)
    with pytest.raises(A2tS2bFlightError, match="per-sample fixed point"):
        build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)


def test_build_flight_plan_rejects_global_derangement_fixed_point():
    headroom, arm_plan = _small_arm_plan()
    derangement = dict(arm_plan.s4_derangement)
    derangement["tool01"] = "tool01"
    headroom, arm_plan = _small_arm_plan(s4_derangement=derangement)
    with pytest.raises(A2tS2bFlightError, match="fixed point"):
        build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)


# ---------------------------------------------------------------------------
# run_a2t_s2b_flight
# ---------------------------------------------------------------------------


def _mock_responder(messages):
    return json.dumps([{"name": "tool01", "arguments": {}}])


def test_run_a2t_s2b_flight_end_to_end_with_mock_client():
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids]
    client = MockCoreClient(responder=_mock_responder)

    counter = {"t": 0.0}

    def fake_now():
        counter["t"] += 1.0
        return counter["t"]

    summary = run_a2t_s2b_flight(core_client=client, samples=samples, plan=plan, now=fake_now)

    n = len(plan.headroom_ids)
    assert len(summary.results) == 2 * n
    by_arm: dict[str, list] = {}
    for result in summary.results:
        by_arm.setdefault(result.arm, []).append(result)
    assert {arm: len(rows) for arm, rows in by_arm.items()} == {B1_ARM: n, B2_ARM: n}
    assert set(by_arm) == set(A2T_S2B_ARMS)

    # Fixed order per sample: B1 then B2 (module docstring).
    for index in range(n):
        assert summary.results[2 * index].arm == B1_ARM
        assert summary.results[2 * index + 1].arm == B2_ARM
        assert summary.results[2 * index].sample_id == summary.results[2 * index + 1].sample_id

    # B1's supplied_tool label matches its reused S1p roster.
    b1_results = {r.sample_id: r for r in by_arm[B1_ARM]}
    for sample_id in plan.headroom_ids:
        expected_label = ",".join(sorted(set(plan.b1_tool_names_by_sample[sample_id])))
        assert b1_results[sample_id].supplied_tool == expected_label

    # B2's supplied_tool is the single reused wrong tool name.
    b2_results = {r.sample_id: r for r in by_arm[B2_ARM]}
    for sample_id in plan.headroom_ids:
        assert b2_results[sample_id].supplied_tool == plan.b2_wrong_tool_by_sample[sample_id]


def test_run_a2t_s2b_flight_b1_prompt_omits_defaults_and_is_narrower_than_b2():
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids]
    client = MockCoreClient(responder=_mock_responder)

    run_a2t_s2b_flight(core_client=client, samples=samples, plan=plan)

    b1_messages = client.calls[0][0]
    b2_messages = client.calls[1][0]
    b1_system = b1_messages[0]["content"]
    b2_system = b2_messages[0]["content"]
    assert "argument_defaults" not in b1_system
    assert len(b1_system) < len(b2_system)
    # B2 carries the full registry text as a literal substring (byte
    # identical to A0's own prompt), plus the pinned header.
    assert _FULL_REGISTRY_TEXT in b2_system
    assert B2_HIGHLIGHT_HEADER in b2_system


def test_run_a2t_s2b_flight_rejects_plan_sample_mismatch():
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids[:-1]]  # drop one
    client = MockCoreClient(responder=_mock_responder)
    with pytest.raises(A2tS2bFlightError, match="not present in samples"):
        run_a2t_s2b_flight(core_client=client, samples=samples, plan=plan)


def test_run_a2t_s2b_flight_rejects_empty_samples():
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    client = MockCoreClient(responder=_mock_responder)
    with pytest.raises(A2tS2bFlightError, match="at least one sample"):
        run_a2t_s2b_flight(core_client=client, samples=[], plan=plan)


def test_write_outputs_jsonl_round_trips_b1_b2_rows(tmp_path):
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids]
    client = MockCoreClient(responder=_mock_responder)
    summary = run_a2t_s2b_flight(core_client=client, samples=samples, plan=plan)

    out_path = tmp_path / "outputs.jsonl"
    write_outputs_jsonl(out_path, summary.results)
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(summary.results)
    for line, result in zip(lines, summary.results):
        document = json.loads(line)
        assert set(document) == {"arm", "sample_id", "supplied_tool", "response", "timing"}
        assert document["arm"] in A2T_S2B_ARMS
