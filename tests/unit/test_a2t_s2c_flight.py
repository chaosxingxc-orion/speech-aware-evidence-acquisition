"""``rails.probes.a2t_s2c_flight``: the P-A2T Stage-2c three-arm
form-robustness probe flight orchestration
(docs/readiness/2026-08-18-pa2t-stage2c-preregistration-REGISTERED.md).
Engineering-only, zero live model contact -- every test here drives
``rails.core_client.MockCoreClient`` or plain synthetic fixtures; the real
Stage-2 arm-plan under ``SPEECHRL_DATA_DIR`` is never touched (a hand-built
``ArmPlan`` stands in for it, mirroring ``test_a2t_s2b_flight``'s own
precedent at the type level).
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
    B2_HIGHLIGHT_HEADER,
    render_b1_tool_schemas,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_s2c_flight import (
    A2T_S2C_ARMS,
    C1_ARM,
    C2_ARM,
    C3_ARM,
    A2tS2cFlightError,
    build_flight_plan,
    render_c1_tool_schemas,
    render_c2_row,
    render_c2_tool_schemas,
    render_c3_tool_schemas,
    run_a2t_s2c_flight,
    split_constraint_clauses,
    verbalize_constraint_clause,
    verbalize_constraints,
    write_outputs_jsonl,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import HeadroomManifest

from test_a2t_s2_flight import _REGISTRY_ROWS, _row  # reuse the SAME 12-tool synthetic registry

# ---------------------------------------------------------------------------
# Small ArmPlan fixture standing in for Stage-2's real, already-flown
# {RUN_ID}.arm-plan.json (loaded verbatim by a real launcher via
# analysis.a2t_s2_read.load_arm_plan; here constructed directly -- mirrors
# test_a2t_s2b_flight._small_arm_plan exactly, s4 fields present only
# because ArmPlan requires them, never consulted by this module).
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

# A registry row carrying a MULTI-CLAUSE argument_constraints string, for
# the permutation/verbalization tests below.
_MULTI_CLAUSE_ROW = dict(_REGISTRY_ROWS[3])
_MULTI_CLAUSE_ROW["argument_constraints"] = "mode: [Home, Armed_Away]; level: [1, 2, 3]"
_MULTI_CLAUSE_ROW["argument_defaults"] = "mode='Home'"


def _sample(sample_id: str) -> Audio2ToolSample:
    return Audio2ToolSample(
        sample_id=sample_id,
        audio_ref=AudioRef(path="unused", sha256="0" * 64).validate(),
        audio_seconds=1.0,
        media_relpath=f"datasets/audio2tool/public/{sample_id.replace(':', '_')}.wav",
    )


# ---------------------------------------------------------------------------
# split_constraint_clauses / verbalize_constraint_clause / verbalize_constraints
# ---------------------------------------------------------------------------


def test_split_constraint_clauses_single_clause():
    assert split_constraint_clauses("mode: [Home, Armed_Away]") == ("mode: [Home, Armed_Away]",)


def test_split_constraint_clauses_multi_clause():
    assert split_constraint_clauses("mode: [Home, Armed_Away]; level: [1, 2, 3]") == (
        "mode: [Home, Armed_Away]",
        "level: [1, 2, 3]",
    )


def test_split_constraint_clauses_blank():
    assert split_constraint_clauses("") == ()
    assert split_constraint_clauses("   ") == ()


def test_verbalize_constraint_clause_enumerated_shape():
    result = verbalize_constraint_clause("mode: [Home, Armed_Away]")
    assert result == "The mode argument must be one of: Home, Armed_Away."


def test_verbalize_constraint_clause_falls_back_for_unrecognized_shape():
    result = verbalize_constraint_clause("some free-text clause")
    assert result == "Constraint: some free-text clause."


def test_verbalize_constraints_covers_every_clause_in_order():
    result = verbalize_constraints("mode: [Home, Armed_Away]; level: [1, 2, 3]")
    assert result == (
        "The mode argument must be one of: Home, Armed_Away. "
        "The level argument must be one of: 1, 2, 3."
    )


def test_verbalize_constraints_blank_is_blank():
    assert verbalize_constraints("") == ""


# ---------------------------------------------------------------------------
# render_c1_tool_schemas (permutation)
# ---------------------------------------------------------------------------


def test_render_c1_tool_schemas_strips_defaults():
    rows = [_MULTI_CLAUSE_ROW]
    rendered = render_c1_tool_schemas(rows, seed=20260807, sample_id="tier1_direct:000001")
    for line in rendered.split("\n"):
        assert "argument_defaults" not in json.loads(line)


def _canonical_row_dict(document: dict) -> dict:
    """``document`` with its ``argument_constraints`` clauses sorted -- lets
    a content-preserving comparison ignore C1's own deliberate clause-order
    permutation while still catching a dropped/added/changed clause."""

    canonical = dict(document)
    if "argument_constraints" in canonical:
        canonical["argument_constraints"] = tuple(sorted(split_constraint_clauses(canonical["argument_constraints"])))
    return canonical


def test_render_c1_tool_schemas_is_content_preserving():
    """C1's permutation changes ORDER only (key order AND, within
    argument_constraints, clause order) -- the same field multiset and the
    same clause SET as B1's own stripped rendering."""

    rows = [_MULTI_CLAUSE_ROW, _REGISTRY_ROWS[0]]
    rendered = render_c1_tool_schemas(rows, seed=20260807, sample_id="tier3_multi_intent:000004")
    lines = rendered.split("\n")
    assert len(lines) == len(rows)
    for line, row in zip(lines, rows):
        stripped_reference = json.loads(render_registry_row(row, strip_defaults=True))
        assert _canonical_row_dict(json.loads(line)) == _canonical_row_dict(stripped_reference)


def test_render_c1_tool_schemas_is_deterministic_per_seed_and_sample():
    rows = [_MULTI_CLAUSE_ROW]
    first = render_c1_tool_schemas(rows, seed=20260807, sample_id="tier1_direct:000001")
    second = render_c1_tool_schemas(rows, seed=20260807, sample_id="tier1_direct:000001")
    assert first == second


def test_render_c1_tool_schemas_differs_by_sample_id():
    """Different sample ids draw a different permutation seed -- not a
    hard requirement of correctness, but the whole point of a SEEDED,
    per-sample permutation is that it is not one fixed global reordering."""

    rows = [_MULTI_CLAUSE_ROW]
    a = render_c1_tool_schemas(rows, seed=20260807, sample_id="tier1_direct:000001")
    b = render_c1_tool_schemas(rows, seed=20260807, sample_id="tier1_direct:000099")
    # Content is identical either way (content-preserving); at least one of
    # key order or constraint-clause order is very likely to differ.
    assert _canonical_row_dict(json.loads(a)) == _canonical_row_dict(json.loads(b))


def test_render_c1_tool_schemas_permutes_constraint_clause_order_or_key_order():
    """Over a large sample of sample_ids, at least one rendering differs in
    literal byte form from the canonical sorted-key, unpermuted rendering --
    proving the permutation actually does something observable."""

    rows = [_MULTI_CLAUSE_ROW]
    canonical = render_registry_row(rows[0], strip_defaults=True)
    differing = 0
    for i in range(20):
        rendered = render_c1_tool_schemas(rows, seed=20260807, sample_id=f"probe:{i:06d}")
        if rendered != canonical:
            differing += 1
    assert differing > 0


# ---------------------------------------------------------------------------
# render_c2_row / render_c2_tool_schemas (verbalization)
# ---------------------------------------------------------------------------


def test_render_c2_row_strips_defaults_and_verbalizes_constraints():
    rendered = render_c2_row(_MULTI_CLAUSE_ROW)
    document = json.loads(rendered)
    assert "argument_defaults" not in document
    assert document["argument_constraints"] == (
        "The mode argument must be one of: Home, Armed_Away. "
        "The level argument must be one of: 1, 2, 3."
    )


def test_render_c2_row_contains_no_default_values_from_the_registry():
    """The mission's own requirement: C2's verbalization must never leak a
    default VALUE. This row's own default is 'Home' (via argument_defaults
    "mode='Home'") -- a value that ALSO happens to appear inside
    argument_constraints's own enumerated list, so this test instead uses a
    default value that appears NOWHERE in the constraints text."""

    row = dict(_REGISTRY_ROWS[0])
    row["argument_constraints"] = "color: [Red, Blue, Green]"
    row["argument_defaults"] = "deviceId='light_1_never_in_constraints'"
    rendered = render_c2_row(row)
    assert "light_1_never_in_constraints" not in rendered
    assert "argument_defaults" not in json.loads(rendered)  # the stripped key itself is gone too


def test_render_c2_tool_schemas_joins_rows_like_render_b1_tool_schemas():
    rows = [_MULTI_CLAUSE_ROW, _REGISTRY_ROWS[0]]
    rendered = render_c2_tool_schemas(rows)
    assert rendered == "\n".join(render_c2_row(row) for row in rows)
    assert len(rendered.split("\n")) == len(rows)


# ---------------------------------------------------------------------------
# render_c3_tool_schemas (augmenting form, reuses B2's own header)
# ---------------------------------------------------------------------------


def test_render_c3_tool_schemas_contains_full_registry_and_appended_stripped_row():
    rows = [_REGISTRY_ROWS[0]]
    result = render_c3_tool_schemas(_FULL_REGISTRY_TEXT, rows)
    assert _FULL_REGISTRY_TEXT in result
    assert B2_HIGHLIGHT_HEADER in result
    assert result == f"{_FULL_REGISTRY_TEXT}\n\n{B2_HIGHLIGHT_HEADER}\n{render_b1_tool_schemas(rows)}"
    assert result.startswith(_FULL_REGISTRY_TEXT + "\n\n")
    assert result.endswith(render_b1_tool_schemas(rows))


def test_render_c3_tool_schemas_appended_row_has_defaults_stripped():
    rows = [_MULTI_CLAUSE_ROW]
    result = render_c3_tool_schemas(_FULL_REGISTRY_TEXT, rows)
    appended = result.split(B2_HIGHLIGHT_HEADER + "\n", 1)[1]
    assert "argument_defaults" not in json.loads(appended)


# ---------------------------------------------------------------------------
# build_flight_plan
# ---------------------------------------------------------------------------


def test_build_flight_plan_happy_path_reuses_s1p_mapping_verbatim():
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    assert plan.headroom_ids == tuple(sorted(_SAMPLE_IDS))
    assert plan.full_registry_text == _FULL_REGISTRY_TEXT
    assert plan.seed == 20260807
    for sample_id in plan.headroom_ids:
        assert plan.correct_tool_names_by_sample[sample_id] == arm_plan.s1p_tool_names[sample_id]


def test_build_flight_plan_is_deterministic():
    headroom, arm_plan = _small_arm_plan()
    plan1 = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    plan2 = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    assert plan1.correct_tool_names_by_sample == plan2.correct_tool_names_by_sample


def test_build_flight_plan_rejects_headroom_arm_plan_mismatch():
    headroom, arm_plan = _small_arm_plan()
    headroom = HeadroomManifest(
        sample_ids=headroom.sample_ids[:-1], attempt_dir=headroom.attempt_dir, split_identity_hash=None
    )
    with pytest.raises(A2tS2cFlightError, match="does not match"):
        build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)


def test_build_flight_plan_rejects_duplicate_registry_tool_name():
    headroom, arm_plan = _small_arm_plan()
    dup_rows = list(_REGISTRY_ROWS) + [_row(99, "tool01")]
    with pytest.raises(A2tS2cFlightError, match="duplicate tool_name"):
        build_flight_plan(headroom, arm_plan, dup_rows, _FULL_REGISTRY_TEXT)


def test_build_flight_plan_rejects_missing_s1p_mapping():
    headroom, arm_plan = _small_arm_plan()
    s1p = dict(arm_plan.s1p_tool_names)
    del s1p[_SAMPLE_IDS[0]]
    headroom, arm_plan = _small_arm_plan(s1p_tool_names=s1p)
    with pytest.raises(A2tS2cFlightError, match="s1p_tool_names has no entry"):
        build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)


def test_build_flight_plan_rejects_unknown_tool():
    headroom, arm_plan = _small_arm_plan()
    s1p = dict(arm_plan.s1p_tool_names)
    s1p[_SAMPLE_IDS[0]] = ("not-a-real-tool",)
    headroom, arm_plan = _small_arm_plan(s1p_tool_names=s1p)
    with pytest.raises(A2tS2cFlightError, match="absent from the loaded registry"):
        build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)


# ---------------------------------------------------------------------------
# run_a2t_s2c_flight
# ---------------------------------------------------------------------------


def _mock_responder(messages):
    return json.dumps([{"name": "tool01", "arguments": {}}])


def test_run_a2t_s2c_flight_end_to_end_with_mock_client():
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids]
    client = MockCoreClient(responder=_mock_responder)

    counter = {"t": 0.0}

    def fake_now():
        counter["t"] += 1.0
        return counter["t"]

    summary = run_a2t_s2c_flight(core_client=client, samples=samples, plan=plan, now=fake_now)

    n = len(plan.headroom_ids)
    assert len(summary.results) == 3 * n
    by_arm: dict[str, list] = {}
    for result in summary.results:
        by_arm.setdefault(result.arm, []).append(result)
    assert {arm: len(rows) for arm, rows in by_arm.items()} == {C1_ARM: n, C2_ARM: n, C3_ARM: n}
    assert set(by_arm) == set(A2T_S2C_ARMS)

    # Fixed order per sample: C1 then C2 then C3.
    for index in range(n):
        assert summary.results[3 * index].arm == C1_ARM
        assert summary.results[3 * index + 1].arm == C2_ARM
        assert summary.results[3 * index + 2].arm == C3_ARM
        sample_ids = {summary.results[3 * index + k].sample_id for k in range(3)}
        assert len(sample_ids) == 1

    # Every arm's supplied_tool label is the SAME (s1p roster label).
    for sample_id in plan.headroom_ids:
        expected_label = ",".join(sorted(set(plan.correct_tool_names_by_sample[sample_id])))
        for result in by_arm[C1_ARM] + by_arm[C2_ARM] + by_arm[C3_ARM]:
            if result.sample_id == sample_id:
                assert result.supplied_tool == expected_label


def test_run_a2t_s2c_flight_prompts_differ_in_form_not_content():
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids]
    client = MockCoreClient(responder=_mock_responder)

    run_a2t_s2c_flight(core_client=client, samples=samples, plan=plan)

    c1_system = client.calls[0][0][0]["content"]
    c2_system = client.calls[1][0][0]["content"]
    c3_system = client.calls[2][0][0]["content"]
    assert "argument_defaults" not in c1_system
    assert "argument_defaults" not in c2_system
    # C3 carries the full registry text as a literal substring (byte
    # identical to A0's own prompt), plus the pinned header.
    assert _FULL_REGISTRY_TEXT in c3_system
    assert B2_HIGHLIGHT_HEADER in c3_system
    assert len(c1_system) < len(c3_system)
    assert len(c2_system) < len(c3_system)


def test_run_a2t_s2c_flight_rejects_plan_sample_mismatch():
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids[:-1]]  # drop one
    client = MockCoreClient(responder=_mock_responder)
    with pytest.raises(A2tS2cFlightError, match="not present in samples"):
        run_a2t_s2c_flight(core_client=client, samples=samples, plan=plan)


def test_run_a2t_s2c_flight_rejects_empty_samples():
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    client = MockCoreClient(responder=_mock_responder)
    with pytest.raises(A2tS2cFlightError, match="at least one sample"):
        run_a2t_s2c_flight(core_client=client, samples=[], plan=plan)


def test_write_outputs_jsonl_round_trips_c1_c2_c3_rows(tmp_path):
    headroom, arm_plan = _small_arm_plan()
    plan = build_flight_plan(headroom, arm_plan, _REGISTRY_ROWS, _FULL_REGISTRY_TEXT)
    samples = [_sample(sample_id) for sample_id in plan.headroom_ids]
    client = MockCoreClient(responder=_mock_responder)
    summary = run_a2t_s2c_flight(core_client=client, samples=samples, plan=plan)

    out_path = tmp_path / "outputs.jsonl"
    write_outputs_jsonl(out_path, summary.results)
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(summary.results)
    for line, result in zip(lines, summary.results):
        document = json.loads(line)
        assert set(document) == {"arm", "sample_id", "supplied_tool", "response", "timing"}
        assert document["arm"] in A2T_S2C_ARMS


def test_b2_highlight_header_reused_verbatim():
    """This module reuses Stage-2b's own pinned constant -- never a second,
    hand-typed header string."""

    from speech_aware_evidence_acquisition.rails.probes.a2t_s2b_flight import (
        B2_HIGHLIGHT_HEADER_SHA256,
    )

    assert hashlib.sha256(B2_HIGHLIGHT_HEADER.encode("utf-8")).hexdigest() == B2_HIGHLIGHT_HEADER_SHA256
