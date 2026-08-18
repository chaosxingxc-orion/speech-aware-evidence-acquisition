"""``analysis.a2t_loss_decomp``: the P-A2T selection-loss decomposition
registered model-free re-read (SAEA-CHECK-a2t-loss-decomp).

Engineering-only, zero live model contact -- reuses ``A2tS2World`` and its
response-text builders directly from ``test_a2t_s2_read``, and the B/C-arm
attempt builders directly from ``test_a2t_s2b_read``/``test_a2t_s2c_read``
(SAME data root, lock, registry, gold shapes, arm-plan document -- the SAME
20-headroom-sample synthetic world every sibling read suite's own test file
already uses). This module is NEVER pointed at a real, already-consumed
attempt directory; that is a separately gated, one-shot execution mission.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_loss_decomp import (
    ALL_ARMS,
    ARM_DIR_ROLE,
    DRAGGED_TO_SUPPLIED,
    DRIFTED_OTHER,
    DRIFT_CONFIRMED_MAX_RATIO,
    DRAG_CONFIRMED_MIN_RATIO,
    EMPTY,
    MULTIPLICITY,
    PARSE_FAIL,
    A2tLossDecompError,
    ArmLossTable,
    _sha256_file,
    assert_structural_premises,
    build_arm_loss_table,
    build_loss_decomp_report,
    classify_loss,
    evaluate_b2_verdict,
    reconcile_arm,
    report_to_json,
    verify_archive_manifest,
)
from speech_aware_evidence_acquisition.analysis.a2t_s2_read import (
    RUN_ID,
    ArmPlan,
    load_arm_plan,
    load_attempt_rows,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import N0R_ARM, S1P_ARM, S2_ARM
from speech_aware_evidence_acquisition.rails.probes.a2t_s2b_flight import B1_ARM, B2_ARM
from speech_aware_evidence_acquisition.rails.probes.a2t_s2c_flight import C1_ARM, C2_ARM, C3_ARM
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall

from test_a2t_s2_read import (  # reuse the SAME synthetic world + response builders
    A2tS2World,
    DERANGEMENT,
    _arm_plan_document,
    _correct_response,
    _gold_value,
    _tool_for,
    _wrong_tool_response,
)
from test_a2t_s2_read import _build_attempt as _s2_build_attempt
from test_a2t_s2b_read import _build_attempt as _s2b_build_attempt
from test_a2t_s2c_read import _build_attempt as _s2c_build_attempt


@pytest.fixture()
def loss_world(tmp_path):
    return A2tS2World(tmp_path)


def _third_tool_response(sample_id: str) -> str:
    """Neither the correct tool nor the (B2-only) highlighted derangement
    target -- two steps around the 5-cycle, always distinct from both."""

    tool = _tool_for(sample_id)
    other = DERANGEMENT[DERANGEMENT[tool]]
    return json.dumps([{"name": other, "arguments": {"x": _gold_value(sample_id)}}])


def _empty_response(_sample_id: str) -> str:
    return "[]"


def _parse_fail_response(_sample_id: str) -> str:
    return "not valid json at all"


def _expected_calls_for_world(world: A2tS2World) -> dict[str, tuple[ToolCall, ...]]:
    """Fresh, single-tool-per-sample gold ``ToolCall`` tuples mirroring
    ``A2tS2World``'s own ``expected_tool_call`` fixture data -- the
    loss-detection comparator (module docstring note 1, 2026-08-18
    amendment): reused verbatim via ``reproduction.toolcall_scoring.
    score_item``, never the deduplicated ``arm_plan.selected_tools``. Tests
    that need a DUPLICATED gold tool name (the amendment's own diagnosed
    defect) override one entry directly."""

    return {
        sample_id: (ToolCall(name=_tool_for(sample_id), arguments={"x": _gold_value(sample_id)}),)
        for sample_id in world.sample_ids
    }


def _write_manifest_for_dir(dir_path: Path) -> None:
    entries = []
    for path in sorted(Path(dir_path).rglob("*")):
        if path.is_file() and path.name != "MANIFEST.sha256":
            rel = path.relative_to(dir_path).as_posix()
            entries.append(f"{_sha256_file(path)} *./{rel}")
    (Path(dir_path) / "MANIFEST.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


# ===========================================================================
# classify_loss -- the four mechanical classes.
# ===========================================================================


def test_classify_loss_parse_fail_when_unparsed():
    assert classify_loss(parsed=False, predicted_names=(), supplied_wrong_tool="toolX") == PARSE_FAIL


def test_classify_loss_empty_when_parsed_but_no_names():
    assert classify_loss(parsed=True, predicted_names=(), supplied_wrong_tool="toolX") == EMPTY


def test_classify_loss_dragged_when_matches_supplied_wrong_tool():
    assert (
        classify_loss(parsed=True, predicted_names=("toolX",), supplied_wrong_tool="toolX")
        == DRAGGED_TO_SUPPLIED
    )


def test_classify_loss_drifted_when_different_wrong_tool():
    assert (
        classify_loss(parsed=True, predicted_names=("toolY",), supplied_wrong_tool="toolX")
        == DRIFTED_OTHER
    )


def test_classify_loss_drifted_when_no_supplied_wrong_tool_at_all():
    """N0r/correct-tool arms: supplied_wrong_tool is always None, so even a
    response that happens to name what would-be-B2's wrong tool is still
    DRIFTED-OTHER, never DRAGGED-TO-SUPPLIED."""

    assert classify_loss(parsed=True, predicted_names=("toolX",), supplied_wrong_tool=None) == DRIFTED_OTHER


def test_classify_loss_multiplicity_when_same_distinct_set_wrong_multiplicity():
    """2026-08-18 amendment (module docstring note 1): a loss whose own
    distinct-tool SET matches the correct SET exactly -- right tool(s),
    wrong call COUNT -- classifies MULTIPLICITY, checked BEFORE DRAGGED."""

    assert (
        classify_loss(
            parsed=True,
            predicted_names=("toolA", "toolB"),
            supplied_wrong_tool=None,
            correct_tool_names=("toolA", "toolB"),
        )
        == MULTIPLICITY
    )


def test_classify_loss_multiplicity_checked_before_dragged():
    """Even when ``supplied_wrong_tool`` happens to be a member of the
    correct SET (never actually reachable given the derangement no-fixed-
    point premise, note 3 -- but checked here directly, unit-level), the
    registered order still classifies MULTIPLICITY first."""

    assert (
        classify_loss(
            parsed=True,
            predicted_names=("toolA",),
            supplied_wrong_tool="toolA",
            correct_tool_names=("toolA",),
        )
        == MULTIPLICITY
    )


def test_classify_loss_old_calls_without_correct_tool_names_are_unaffected():
    """Backward compatibility: omitting ``correct_tool_names`` (default
    ``()``) never spuriously fires MULTIPLICITY for a non-empty prediction,
    so every pre-amendment call site's own behavior is preserved."""

    assert (
        classify_loss(parsed=True, predicted_names=("toolX",), supplied_wrong_tool="toolX")
        == DRAGGED_TO_SUPPLIED
    )
    assert (
        classify_loss(parsed=True, predicted_names=("toolY",), supplied_wrong_tool="toolX")
        == DRIFTED_OTHER
    )


# ===========================================================================
# evaluate_b2_verdict -- DRAG-CONFIRMED / DRIFT-CONFIRMED / MIXED.
# ===========================================================================


def _table(arm: str, n_samples: int, counts: dict) -> ArmLossTable:
    full = {k: 0 for k in (DRAGGED_TO_SUPPLIED, DRIFTED_OTHER, MULTIPLICITY, EMPTY, PARSE_FAIL)}
    full.update(counts)
    return ArmLossTable(
        arm=arm, n_samples=n_samples, n_losses=sum(full.values()), class_counts=full, rows=()
    )


def test_evaluate_b2_verdict_drag_confirmed_at_exact_margin():
    # 11/21 is the registered floor -- exactly at the margin still fires.
    b2 = _table(B2_ARM, 120, {DRAGGED_TO_SUPPLIED: 11, DRIFTED_OTHER: 10})
    n0r = _table(N0R_ARM, 40, {DRIFTED_OTHER: 5})
    verdict = evaluate_b2_verdict(b2, n0r)

    assert verdict.dragged_count == 11
    assert verdict.total_losses == 21
    assert verdict.drag_confirmed is True
    assert verdict.drag_confirmed_clause.verdict == "met"
    assert verdict.drift_confirmed is False
    assert verdict.overall == "DRAG-CONFIRMED"


def test_evaluate_b2_verdict_drag_confirmed_just_below_margin_is_not_drag():
    b2 = _table(B2_ARM, 120, {DRAGGED_TO_SUPPLIED: 10, DRIFTED_OTHER: 11})
    n0r = _table(N0R_ARM, 40, {DRIFTED_OTHER: 5})
    verdict = evaluate_b2_verdict(b2, n0r)

    assert 10 / 21 < DRAG_CONFIRMED_MIN_RATIO
    assert verdict.drag_confirmed is False
    assert verdict.overall != "DRAG-CONFIRMED"


def test_evaluate_b2_verdict_drift_confirmed_reports_n0r_reference_shape():
    b2 = _table(B2_ARM, 120, {DRAGGED_TO_SUPPLIED: 5, DRIFTED_OTHER: 12, EMPTY: 3, PARSE_FAIL: 1})
    n0r_counts = {DRIFTED_OTHER: 3, EMPTY: 2}
    n0r = _table(N0R_ARM, 40, n0r_counts)
    verdict = evaluate_b2_verdict(b2, n0r)

    assert verdict.dragged_count == 5
    assert 5 / 21 <= DRIFT_CONFIRMED_MAX_RATIO
    assert verdict.drift_confirmed is True
    assert verdict.drag_confirmed is False
    assert verdict.overall == "DRIFT-CONFIRMED"
    # The side-by-side reporting obligation (note 2): both shapes are always
    # carried on the verdict object, never dropped just because no
    # statistical test applies to them.
    assert verdict.b2_shape[DRAGGED_TO_SUPPLIED] == 5
    assert verdict.n0r_reference_shape == {
        DRAGGED_TO_SUPPLIED: 0, DRIFTED_OTHER: 3, MULTIPLICITY: 0, EMPTY: 2, PARSE_FAIL: 0
    }


def test_evaluate_b2_verdict_mixed_in_the_gap_between_thresholds():
    b2 = _table(B2_ARM, 120, {DRAGGED_TO_SUPPLIED: 8, DRIFTED_OTHER: 13})  # 8/21 ~= 0.381
    n0r = _table(N0R_ARM, 40, {})
    verdict = evaluate_b2_verdict(b2, n0r)

    assert DRIFT_CONFIRMED_MAX_RATIO < 8 / 21 < DRAG_CONFIRMED_MIN_RATIO
    assert verdict.drag_confirmed is False
    assert verdict.drift_confirmed is False
    assert verdict.overall == "MIXED"


def test_evaluate_b2_verdict_zero_losses_is_mixed_not_drift():
    """Degenerate zero-loss case (note 2): guarded explicitly rather than
    treated as a vacuous DRIFT-CONFIRMED (0 <= 5/21 would be vacuously true
    without the total>0 guard)."""

    b2 = _table(B2_ARM, 120, {})
    n0r = _table(N0R_ARM, 40, {})
    verdict = evaluate_b2_verdict(b2, n0r)

    assert verdict.total_losses == 0
    assert verdict.drag_confirmed is False
    assert verdict.drift_confirmed is False
    assert verdict.overall == "MIXED"


def test_evaluate_b2_verdict_multiplicity_counts_toward_denominator_not_dragged():
    """MULTIPLICITY losses widen B2's own total-loss denominator exactly
    like EMPTY/PARSE-FAIL (2026-08-18 amendment, module docstring note 1):
    they weigh AGAINST DRAG-CONFIRMED without ever counting as dragged --
    the B2 verdict's own math (denominator = total losses) is unchanged."""

    b2 = _table(B2_ARM, 120, {DRAGGED_TO_SUPPLIED: 11, DRIFTED_OTHER: 9, MULTIPLICITY: 1})
    n0r = _table(N0R_ARM, 40, {DRIFTED_OTHER: 5})
    verdict = evaluate_b2_verdict(b2, n0r)

    assert verdict.dragged_count == 11
    assert verdict.total_losses == 21
    assert verdict.b2_shape[MULTIPLICITY] == 1
    # 11/21 still exactly meets the DRAG-CONFIRMED floor even with a
    # MULTIPLICITY loss folded into the denominator.
    assert verdict.drag_confirmed is True
    assert verdict.overall == "DRAG-CONFIRMED"


# ===========================================================================
# assert_structural_premises -- level one (note 3).
# ===========================================================================


def _plan_from_document(document: dict) -> ArmPlan:
    return ArmPlan(
        seed=document["seed"],
        headroom_ids=tuple(document["headroom_ids"]),
        n0r_sample_ids=tuple(document["n0r_sample_ids"]),
        selected_tools={k: tuple(v) for k, v in document["selected_tools"].items()},
        s1p_tool_names={k: tuple(v) for k, v in document["s1p_tool_names"].items()},
        s2_tool_names={k: tuple(v) for k, v in document["s2_tool_names"].items()},
        s4_derangement=dict(document["s4_derangement"]),
        s4_tool_name=dict(document["s4_tool_name"]),
    )


def test_assert_structural_premises_passes_for_a_consistent_arm_plan(loss_world):
    plan = _plan_from_document(_arm_plan_document(loss_world))
    assert_structural_premises(plan)  # must not raise


def test_assert_structural_premises_refuses_when_s1p_diverges_from_a0_selection(loss_world):
    document = _arm_plan_document(loss_world)
    sample_id = loss_world.sample_ids[0]
    document["s1p_tool_names"][sample_id] = ["not-the-selected-tool"]
    plan = _plan_from_document(document)

    with pytest.raises(A2tLossDecompError, match="premise does not hold"):
        assert_structural_premises(plan)


def test_assert_structural_premises_refuses_when_b2_wrong_tool_equals_correct_tool(loss_world):
    document = _arm_plan_document(loss_world)
    sample_id = loss_world.sample_ids[0]
    correct = document["selected_tools"][sample_id][0]
    document["s4_tool_name"][sample_id] = correct  # derangement fixed-point injected
    plan = _plan_from_document(document)

    with pytest.raises(A2tLossDecompError, match="derangement no-fixed-point premise"):
        assert_structural_premises(plan)


# ===========================================================================
# build_arm_loss_table -- per-row classification end to end (no attempt-dir
# I/O; OutputRow objects built directly).
# ===========================================================================


def _row(arm: str, sample_id: str, response: str):
    from speech_aware_evidence_acquisition.analysis.a2t_s2_read import OutputRow

    return OutputRow(arm=arm, sample_id=sample_id, supplied_tool="unused", response=response, timing={})


def test_build_arm_loss_table_classifies_b2_rows_across_all_four_classes(loss_world):
    world = loss_world
    plan = _plan_from_document(_arm_plan_document(world))
    ids = world.sample_ids  # 20 samples

    drag_id, drift_id, empty_id, fail_id, correct_id = ids[0], ids[1], ids[2], ids[3], ids[4]
    rows = [
        _row(B2_ARM, drag_id, _wrong_tool_response(drag_id)),
        _row(B2_ARM, drift_id, _third_tool_response(drift_id)),
        _row(B2_ARM, empty_id, _empty_response(empty_id)),
        _row(B2_ARM, fail_id, _parse_fail_response(fail_id)),
        _row(B2_ARM, correct_id, _correct_response(correct_id)),
    ] + [_row(B2_ARM, sid, _correct_response(sid)) for sid in ids if sid not in (drag_id, drift_id, empty_id, fail_id, correct_id)]

    table = build_arm_loss_table(B2_ARM, rows, plan, _expected_calls_for_world(world))

    assert table.n_samples == 20
    assert table.n_losses == 4
    assert table.class_counts == {
        DRAGGED_TO_SUPPLIED: 1, DRIFTED_OTHER: 1, MULTIPLICITY: 0, EMPTY: 1, PARSE_FAIL: 1
    }
    by_id = {r.sample_id: r for r in table.rows}
    assert by_id[drag_id].klass == DRAGGED_TO_SUPPLIED
    assert by_id[drag_id].arm_tool == DERANGEMENT[_tool_for(drag_id)]
    assert by_id[drag_id].a0_tool == _tool_for(drag_id)
    assert by_id[drift_id].klass == DRIFTED_OTHER
    assert by_id[empty_id].klass == EMPTY
    assert by_id[empty_id].arm_tool == "(empty)"
    assert by_id[fail_id].klass == PARSE_FAIL
    assert by_id[fail_id].arm_tool == "(parse-fail)"


def test_build_arm_loss_table_correct_tool_arm_never_produces_dragged(loss_world):
    """Level-two defense-in-depth (note 3): S1' has no supplied WRONG tool,
    so a S1p row naming DERANGEMENT[tool] (what WOULD be B2's drag target)
    is classified DRIFTED-OTHER, never DRAGGED-TO-SUPPLIED."""

    world = loss_world
    plan = _plan_from_document(_arm_plan_document(world))
    sid = world.sample_ids[0]
    rows = [_row(S1P_ARM, sid, _wrong_tool_response(sid))] + [
        _row(S1P_ARM, other, _correct_response(other)) for other in world.sample_ids if other != sid
    ]

    table = build_arm_loss_table(S1P_ARM, rows, plan, _expected_calls_for_world(world))

    assert table.n_losses == 1
    assert table.rows[0].klass == DRIFTED_OTHER
    assert table.class_counts[DRAGGED_TO_SUPPLIED] == 0


def test_build_arm_loss_table_n0r_iterates_its_own_subset_not_full_headroom(loss_world):
    """Note 6: N0r's own domain is n0r_sample_ids, not headroom_ids."""

    world = loss_world
    n0r_subset = world.sample_ids[:8]
    document = _arm_plan_document(world, n0r_sample_ids=n0r_subset)
    plan = _plan_from_document(document)
    rows = [_row(N0R_ARM, sid, _correct_response(sid)) for sid in n0r_subset]

    table = build_arm_loss_table(N0R_ARM, rows, plan, _expected_calls_for_world(world))

    assert table.n_samples == 8
    assert table.n_losses == 0


def test_build_arm_loss_table_refuses_when_a_domain_sample_has_no_row(loss_world):
    world = loss_world
    plan = _plan_from_document(_arm_plan_document(world))
    rows = [_row(S1P_ARM, sid, _correct_response(sid)) for sid in world.sample_ids[:-1]]  # one missing

    with pytest.raises(A2tLossDecompError, match="no row for"):
        build_arm_loss_table(S1P_ARM, rows, plan, _expected_calls_for_world(world))


def _duplicated_gold_fixture(world: A2tS2World):
    """A headroom sample whose GOLD carries a duplicated tool name --
    reproduces the refused first execution's own diagnosis (module
    docstring note 1, 2026-08-18 amendment): the real headroom sample
    ``tier3_multi_intent:003994``'s own
    ``{setZoneTemperature: 2, setCabinOverheatProtection: 1}``. Returns
    ``(plan, expected_calls, dup_id, tool_a, tool_b, dup_response_text)``
    where ``dup_response_text`` names the SAME distinct tool SET as gold
    ({tool_a, tool_b}) but ONE FEWER tool_a call -- right tools, wrong
    call COUNT."""

    document = _arm_plan_document(world)
    dup_id, other_id = world.sample_ids[0], world.sample_ids[1]
    tool_a = _tool_for(dup_id)
    tool_b = _tool_for(other_id)
    document["selected_tools"][dup_id] = sorted([tool_a, tool_b])
    document["s1p_tool_names"][dup_id] = sorted([tool_a, tool_b])
    plan = _plan_from_document(document)

    expected_calls = _expected_calls_for_world(world)
    expected_calls[dup_id] = (
        ToolCall(name=tool_a, arguments={"x": _gold_value(dup_id)}),
        ToolCall(name=tool_a, arguments={"x": _gold_value(dup_id)}),
        ToolCall(name=tool_b, arguments={"x": _gold_value(dup_id)}),
    )

    dup_response_text = json.dumps(
        [
            {"name": tool_a, "arguments": {"x": _gold_value(dup_id)}},
            {"name": tool_b, "arguments": {"x": _gold_value(dup_id)}},
        ]
    )
    return plan, expected_calls, dup_id, tool_a, tool_b, dup_response_text


def test_build_arm_loss_table_detects_multiset_loss_missed_by_identity_comparison(loss_world):
    """The refused first execution's own diagnosis, reproduced directly: a
    duplicated-gold-tool sample that IS a loss under the parents' own
    multiset ``tool_accuracy`` comparison but would have been silently
    treated as a retained correct selection under the pre-amendment
    deduplicated-SET comparison -- classified MULTIPLICITY, never missed."""

    world = loss_world
    plan, expected_calls, dup_id, tool_a, tool_b, dup_response_text = _duplicated_gold_fixture(world)

    rows = [_row(B2_ARM, dup_id, dup_response_text)] + [
        _row(B2_ARM, sid, _correct_response(sid)) for sid in world.sample_ids if sid != dup_id
    ]

    table = build_arm_loss_table(B2_ARM, rows, plan, expected_calls)

    assert table.n_losses == 1
    assert table.rows[0].sample_id == dup_id
    assert table.rows[0].klass == MULTIPLICITY
    assert table.class_counts == {
        DRAGGED_TO_SUPPLIED: 0, DRIFTED_OTHER: 0, MULTIPLICITY: 1, EMPTY: 0, PARSE_FAIL: 0
    }


def test_build_arm_loss_table_correct_tool_arm_allows_multiplicity_without_assertion(loss_world):
    """Note 3's structural-impossibility defense-in-depth guards
    DRAGGED-TO-SUPPLIED only; MULTIPLICITY is legal for EVERY arm, including
    correct-tool arms (module docstring note 1, 2026-08-18 amendment) -- no
    assertion fires even though S1p carries no supplied WRONG tool at all."""

    world = loss_world
    plan, expected_calls, dup_id, tool_a, tool_b, dup_response_text = _duplicated_gold_fixture(world)

    rows = [_row(S1P_ARM, dup_id, dup_response_text)] + [
        _row(S1P_ARM, sid, _correct_response(sid)) for sid in world.sample_ids if sid != dup_id
    ]

    table = build_arm_loss_table(S1P_ARM, rows, plan, expected_calls)  # must not raise

    assert table.n_losses == 1
    assert table.rows[0].klass == MULTIPLICITY
    assert table.class_counts[DRAGGED_TO_SUPPLIED] == 0


def test_loss_row_internal_consistency_guard_fires_on_unreachable_state(monkeypatch, loss_world):
    """Level-two defense-in-depth (note 3), exercised directly: if
    ``_supplied_wrong_tool`` were ever monkeypatched to hand a correct-tool
    arm a wrong-tool target (a bug this module's own design otherwise makes
    structurally impossible), the post-hoc guard inside ``_loss_row_for``
    refuses rather than silently mislabeling a S1p loss as DRAGGED."""

    import speech_aware_evidence_acquisition.analysis.a2t_loss_decomp as module

    world = loss_world
    plan = _plan_from_document(_arm_plan_document(world))
    sid = world.sample_ids[0]
    wrong = DERANGEMENT[_tool_for(sid)]
    monkeypatch.setattr(module, "_supplied_wrong_tool", lambda arm, arm_plan, sample_id: wrong)

    with pytest.raises(A2tLossDecompError, match="structural-impossibility invariant violated"):
        module._loss_row_for(
            S1P_ARM, _row(S1P_ARM, sid, _wrong_tool_response(sid)), plan, _expected_calls_for_world(world)
        )


# ===========================================================================
# verify_archive_manifest -- MANIFEST.sha256 integrity gate.
# ===========================================================================


def test_verify_archive_manifest_passes_for_a_consistent_archive(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "a.txt").write_text("alpha", encoding="utf-8")
    (archive / "b.txt").write_text("beta", encoding="utf-8")
    _write_manifest_for_dir(archive)

    verified = verify_archive_manifest(archive)
    assert verified == ("a.txt", "b.txt")


def test_verify_archive_manifest_refuses_missing_manifest(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "a.txt").write_text("alpha", encoding="utf-8")

    with pytest.raises(A2tLossDecompError, match="missing"):
        verify_archive_manifest(archive)


def test_verify_archive_manifest_refuses_on_tampered_file(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "a.txt").write_text("alpha", encoding="utf-8")
    _write_manifest_for_dir(archive)

    (archive / "a.txt").write_text("TAMPERED", encoding="utf-8")

    with pytest.raises(A2tLossDecompError, match="sha256 mismatch"):
        verify_archive_manifest(archive)


def test_verify_archive_manifest_cross_check_refuses_on_drifted_live_copy(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "flight-receipt.json").write_text('{"status": "COMPLETED"}', encoding="utf-8")
    _write_manifest_for_dir(archive)

    live = tmp_path / "attempt" / "flight-receipt.json"
    live.parent.mkdir()
    live.write_text('{"status": "TAMPERED"}', encoding="utf-8")

    with pytest.raises(A2tLossDecompError, match="does not match the archived"):
        verify_archive_manifest(archive, cross_check={"flight-receipt.json": live})


def test_verify_archive_manifest_cross_check_passes_on_byte_identical_live_copy(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "flight-receipt.json").write_text('{"status": "COMPLETED"}', encoding="utf-8")
    _write_manifest_for_dir(archive)

    live = tmp_path / "attempt" / "flight-receipt.json"
    live.parent.mkdir()
    live.write_text('{"status": "COMPLETED"}', encoding="utf-8")

    verified = verify_archive_manifest(archive, cross_check={"flight-receipt.json": live})
    assert verified == ("flight-receipt.json",)


# ===========================================================================
# reconcile_arm -- three-way reconciliation, and the real-scale exact gate.
# ===========================================================================


def test_reconcile_arm_matches_when_all_three_agree_at_small_scale():
    table = _table(S1P_ARM, 20, {DRIFTED_OTHER: 2})
    parent = {"n_samples": 20, "tool_selection_retention": 18 / 20}
    archived = {"n_samples": 20, "tool_selection_retention": 18 / 20}

    row = reconcile_arm(S1P_ARM, table, parent, archived)
    assert row.matched is True
    assert row.computed_loss_count == row.parent_recomputed_loss_count == row.archived_loss_count == 2


def test_reconcile_arm_refuses_when_archived_disagrees():
    table = _table(S1P_ARM, 20, {DRIFTED_OTHER: 2})
    parent = {"n_samples": 20, "tool_selection_retention": 18 / 20}
    archived = {"n_samples": 20, "tool_selection_retention": 19 / 20}  # implies 1 loss, not 2

    row = reconcile_arm(S1P_ARM, table, parent, archived)
    assert row.matched is False
    assert row.archived_loss_count == 1
    assert row.computed_loss_count == 2


def test_reconcile_arm_exact_gate_applies_and_passes_at_real_scale():
    table = _table(B2_ARM, 120, {DRAGGED_TO_SUPPLIED: 21})
    parent = {"n_samples": 120, "tool_selection_retention": 99 / 120}
    archived = {"n_samples": 120, "tool_selection_retention": 99 / 120}

    row = reconcile_arm(B2_ARM, table, parent, archived)
    assert row.matched is True
    assert "exact_gate=21/120 (applies" in row.detail


def test_reconcile_arm_exact_gate_counts_multiplicity_losses_too():
    """MULTIPLICITY losses count toward B2's own total exactly like every
    other loss class (module docstring note 1, 2026-08-18 amendment) -- the
    real-scale 21/120 gate still applies when some of those 21 are
    MULTIPLICITY, not just DRAGGED/DRIFTED/EMPTY/PARSE-FAIL."""

    table = _table(B2_ARM, 120, {DRAGGED_TO_SUPPLIED: 11, DRIFTED_OTHER: 9, MULTIPLICITY: 1})
    parent = {"n_samples": 120, "tool_selection_retention": 99 / 120}
    archived = {"n_samples": 120, "tool_selection_retention": 99 / 120}

    row = reconcile_arm(B2_ARM, table, parent, archived)
    assert row.matched is True
    assert row.computed_loss_count == 21
    assert "exact_gate=21/120 (applies" in row.detail


def test_reconcile_arm_refuses_when_b2_losses_are_not_exactly_21_at_real_scale():
    """The mission's own literal requirement: at the real 120-sample scale,
    B2 must yield EXACTLY 21 losses, else fail closed -- even when the
    three-way count otherwise agrees internally at some OTHER number."""

    table = _table(B2_ARM, 120, {DRAGGED_TO_SUPPLIED: 20})
    parent = {"n_samples": 120, "tool_selection_retention": 100 / 120}  # implies 20, agrees with table
    archived = {"n_samples": 120, "tool_selection_retention": 100 / 120}  # implies 20, agrees with both

    row = reconcile_arm(B2_ARM, table, parent, archived)
    assert row.computed_loss_count == row.parent_recomputed_loss_count == row.archived_loss_count == 20
    assert row.matched is False  # the exact-gate (21) still refuses despite the internal three-way agreement


def test_reconcile_arm_gate_not_applicable_at_a_smaller_synthetic_scale():
    table = _table(B2_ARM, 20, {DRAGGED_TO_SUPPLIED: 15, DRIFTED_OTHER: 5})
    parent = {"n_samples": 20, "tool_selection_retention": 0.0}
    archived = {"n_samples": 20, "tool_selection_retention": 0.0}

    row = reconcile_arm(B2_ARM, table, parent, archived)
    assert row.matched is True  # gate is skipped -- n_samples=20 != the real B2 size (120)
    assert "not applicable at n_samples=20" in row.detail


# ===========================================================================
# build_loss_decomp_report -- full pipeline (attempt dirs + archives).
# ===========================================================================


def _build_full_environment(tmp_path: Path, world: A2tS2World):
    """Constructs three attempt dirs (S2/S2b/S2c), a headroom manifest, one
    shared arm-plan.json, and the seven git-committed-style archive dirs
    (headroom / 3 flight / 3 read) this suite's integrity section verifies
    -- with archived retention numbers derived from THIS module's own
    ``build_arm_loss_table`` so the three-way reconciliation is consistent
    by construction. Returns a dict of every path
    ``build_loss_decomp_report`` needs."""

    from test_a2t_s2_read import _headroom_path

    ids = world.sample_ids  # 20 samples
    drag_ids = set(ids[:15])
    drift_ids = set(ids[15:17])
    empty_ids = set(ids[17:19])
    fail_ids = {ids[19]}

    def b2_fn(sample_id):
        if sample_id in drag_ids:
            return _wrong_tool_response(sample_id)
        if sample_id in drift_ids:
            return _third_tool_response(sample_id)
        if sample_id in empty_ids:
            return _empty_response(sample_id)
        return _parse_fail_response(sample_id)

    n0r_drift_id, n0r_empty_id = ids[0], ids[1]

    def n0r_fn(sample_id):
        if sample_id == n0r_drift_id:
            return _wrong_tool_response(sample_id)
        if sample_id == n0r_empty_id:
            return _empty_response(sample_id)
        return _correct_response(sample_id)

    c3_drift_id, c3_empty_id, c3_fail_id = ids[0], ids[1], ids[2]

    def c3_fn(sample_id):
        if sample_id == c3_drift_id:
            return _third_tool_response(sample_id)
        if sample_id == c3_empty_id:
            return _empty_response(sample_id)
        if sample_id == c3_fail_id:
            return _parse_fail_response(sample_id)
        return _correct_response(sample_id)

    s2_attempt_dir = _s2_build_attempt(
        tmp_path, world, s1p_fn=_correct_response, s2_fn=_correct_response,
        s4_fn=_correct_response, n0r_fn=n0r_fn, name="s2-attempt",
    )
    s2b_attempt_dir = _s2b_build_attempt(
        tmp_path, world, b1_fn=_correct_response, b2_fn=b2_fn, name="s2b-attempt",
    )
    s2c_attempt_dir = _s2c_build_attempt(
        tmp_path, world, c1_fn=_correct_response, c2_fn=_correct_response, c3_fn=c3_fn, name="s2c-attempt",
    )
    headroom_path = _headroom_path(tmp_path, world)
    arm_plan_path = s2_attempt_dir / f"{RUN_ID}.arm-plan.json"

    plan = load_arm_plan(arm_plan_path)
    s2_rows, _ = load_attempt_rows(s2_attempt_dir)
    s2b_rows, _ = load_attempt_rows(s2b_attempt_dir)
    s2c_rows, _ = load_attempt_rows(s2c_attempt_dir)
    rows_by_role = {"s2": s2_rows, "s2b": s2b_rows, "s2c": s2c_rows}

    expected_calls = _expected_calls_for_world(world)
    expected_tables = {
        arm: build_arm_loss_table(
            arm, [r for r in rows_by_role[ARM_DIR_ROLE[arm]] if r.arm == arm], plan, expected_calls
        )
        for arm in ALL_ARMS
    }

    archives_root = tmp_path / "archives"
    headroom_archive_dir = archives_root / "headroom"
    headroom_archive_dir.mkdir(parents=True)
    shutil.copy2(headroom_path, headroom_archive_dir / "headroom.json")
    _write_manifest_for_dir(headroom_archive_dir)

    attempt_dir_by_role = {"s2": s2_attempt_dir, "s2b": s2b_attempt_dir, "s2c": s2c_attempt_dir}
    flight_archive_dirs = {}
    for role, attempt_dir in attempt_dir_by_role.items():
        d = archives_root / f"{role}-flight"
        d.mkdir(parents=True)
        shutil.copy2(attempt_dir / "flight-receipt.json", d / "flight-receipt.json")
        _write_manifest_for_dir(d)
        flight_archive_dirs[role] = d

    arms_by_role = {"s2": (N0R_ARM, S1P_ARM, S2_ARM), "s2b": (B1_ARM, B2_ARM), "s2c": (C1_ARM, C2_ARM, C3_ARM)}
    read_archive_dirs = {}
    for role, arms in arms_by_role.items():
        d = archives_root / f"{role}-read"
        d.mkdir(parents=True)
        per_arm = {}
        for arm in arms:
            table = expected_tables[arm]
            n = table.n_samples
            retention = (n - table.n_losses) / n
            per_arm[arm] = {"overall": {"n_samples": n, "tool_selection_retention": retention}}
        (d / "verdict.json").write_text(json.dumps({"per_arm": per_arm}), encoding="utf-8")
        _write_manifest_for_dir(d)
        read_archive_dirs[role] = d

    return {
        "s2_attempt_dir": s2_attempt_dir,
        "s2b_attempt_dir": s2b_attempt_dir,
        "s2c_attempt_dir": s2c_attempt_dir,
        "headroom_path": headroom_path,
        "arm_plan_path": arm_plan_path,
        "expected_tables": expected_tables,
        "headroom_archive_dir": headroom_archive_dir,
        "flight_archive_dirs": flight_archive_dirs,
        "read_archive_dirs": read_archive_dirs,
    }


def _call_build_report(world: A2tS2World, env: dict):
    lock = load_lock(world.lock_path)
    return build_loss_decomp_report(
        env["s2_attempt_dir"], env["s2b_attempt_dir"], env["s2c_attempt_dir"],
        lock, world.data_root,
        repo_root=world.repo_root,
        headroom_path=env["headroom_path"],
        arm_plan_path=env["arm_plan_path"],
        headroom_archive_dir=env["headroom_archive_dir"],
        s2_flight_archive_dir=env["flight_archive_dirs"]["s2"],
        s2b_flight_archive_dir=env["flight_archive_dirs"]["s2b"],
        s2c_flight_archive_dir=env["flight_archive_dirs"]["s2c"],
        s2_read_archive_dir=env["read_archive_dirs"]["s2"],
        s2b_read_archive_dir=env["read_archive_dirs"]["s2b"],
        s2c_read_archive_dir=env["read_archive_dirs"]["s2c"],
    )


def test_build_loss_decomp_report_end_to_end_drag_confirmed(tmp_path, loss_world):
    world = loss_world
    env = _build_full_environment(tmp_path, world)

    report = _call_build_report(world, env)

    b2_table = report.tables[B2_ARM]
    assert b2_table.n_losses == 20  # every B2 row is a loss in this fixture
    assert b2_table.class_counts[DRAGGED_TO_SUPPLIED] == 15
    assert b2_table.class_counts[DRIFTED_OTHER] == 2
    assert b2_table.class_counts[EMPTY] == 2
    assert b2_table.class_counts[PARSE_FAIL] == 1

    assert report.b2_verdict.overall == "DRAG-CONFIRMED"
    assert report.b2_verdict.dragged_count == 15

    n0r_table = report.tables[N0R_ARM]
    assert n0r_table.n_losses == 2
    assert n0r_table.class_counts[DRIFTED_OTHER] == 1
    assert n0r_table.class_counts[EMPTY] == 1

    c3_table = report.tables[C3_ARM]
    assert c3_table.n_losses == 3

    for arm in (S1P_ARM, S2_ARM, B1_ARM, C1_ARM, C2_ARM):
        assert report.tables[arm].n_losses == 0
        assert report.tables[arm].class_counts[DRAGGED_TO_SUPPLIED] == 0  # structural impossibility held

    assert all(row.matched for row in report.integrity.reconciliation)
    assert len(report.integrity.headroom_archive_verified_files) >= 1
    assert set(report.integrity.flight_archive_verified) == {"s2", "s2b", "s2c"}
    assert set(report.integrity.read_archive_verified) == {"s2", "s2b", "s2c"}
    assert report.integrity.unpinned_inputs == ("outputs.jsonl", "{RUN_ID}.arm-plan.json")

    document = report_to_json(report)
    assert document["schema"] == "saea-a2t-loss-decomp-read-v1"
    assert document["b2_verdict"]["overall"] == "DRAG-CONFIRMED"
    assert set(document["tables"]) == set(ALL_ARMS)


def test_build_loss_decomp_report_refuses_on_tampered_flight_archive(tmp_path, loss_world):
    world = loss_world
    env = _build_full_environment(tmp_path, world)

    # Tamper the archived, MANIFEST-pinned flight-receipt.json copy AFTER
    # its own manifest was generated -- self-consistency check must catch it.
    tampered = env["flight_archive_dirs"]["s2b"] / "flight-receipt.json"
    tampered.write_text(tampered.read_text(encoding="utf-8") + "TAMPERED", encoding="utf-8")

    with pytest.raises(A2tLossDecompError, match="MANIFEST.sha256 integrity failure"):
        _call_build_report(world, env)


def test_build_loss_decomp_report_refuses_on_reconciliation_mismatch(tmp_path, loss_world):
    world = loss_world
    env = _build_full_environment(tmp_path, world)

    # Corrupt the archived B2 read's own published retention so it no
    # longer agrees with what this module's own row walk (and the parent
    # suite's own fresh recompute) both independently compute.
    verdict_path = env["read_archive_dirs"]["s2b"] / "verdict.json"
    document = json.loads(verdict_path.read_text(encoding="utf-8"))
    document["per_arm"][B2_ARM]["overall"]["tool_selection_retention"] = 1.0  # implies 0 losses, not 20
    verdict_path.write_text(json.dumps(document), encoding="utf-8")
    _write_manifest_for_dir(env["read_archive_dirs"]["s2b"])  # re-pin so the tamper isn't ALSO a MANIFEST failure

    with pytest.raises(A2tLossDecompError, match="reconciliation failure"):
        _call_build_report(world, env)
