"""``analysis.a2t_abst_read``: the P-A2T abstention-asymmetry 2x2 pinned
offline read suite
(docs/readiness/2026-08-19-a2t-abst-preregistration-REGISTERED.md).

Engineering-only, zero live model contact -- every fixture here is a
hand-authored synthetic attempt directory built on top of a minimal
``A2tAbstWorld`` (a frozen probe-sample receipt only -- this suite never
reads gold or a tool registry, module docstring). This module is NEVER
pointed at the real flight attempt directory
(``$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-abst-44/``); that is a separate,
one-shot registered read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_abst_read import (
    CONFABULATED_CALL,
    CONFIRMED_ABSTENTION_TW_A_MIN,
    CONFIRMED_CONFABULATION_TP_S_MIN,
    PARSE_FAILURE,
    REFUTED_ABSTENTION_TP_S_MIN,
    RUN_ID,
    WELL_FORMED_ABSTENTION,
    A2tAbstReadError,
    CellAggregate,
    build_a2t_abst_report,
    build_cell_aggregate,
    build_per_sample_table,
    classify_response,
    compute_cell_rate_bootstrap,
    evaluate_asymmetry_verdict,
    main as a2t_abst_read_main,
    report_to_json,
)
from speech_aware_evidence_acquisition.analysis.a2t_s2_read import OutputRow
from speech_aware_evidence_acquisition.rails.probes.a2t_abst_flight import (
    A2T_ABST_CELLS,
    ABST_N,
    TP_A_CELL,
    TP_S_CELL,
    TW_A_CELL,
    TW_S_CELL,
)

# ---------------------------------------------------------------------------
# classify_response
# ---------------------------------------------------------------------------


def test_classify_response_well_formed_abstention():
    assert classify_response("[]") == WELL_FORMED_ABSTENTION


def test_classify_response_confabulated_call():
    assert classify_response(json.dumps([{"name": "tool99", "arguments": {}}])) == CONFABULATED_CALL


def test_classify_response_parse_failure():
    assert classify_response("not valid json at all") == PARSE_FAILURE


def test_classify_response_categories_partition_every_response():
    for text in ("[]", json.dumps([{"name": "t", "arguments": {}}]), "garbage", "", "```json\n[]\n```"):
        assert classify_response(text) in (WELL_FORMED_ABSTENTION, CONFABULATED_CALL, PARSE_FAILURE)


# ---------------------------------------------------------------------------
# build_cell_aggregate / build_per_sample_table
# ---------------------------------------------------------------------------


def test_build_cell_aggregate_counts_and_rates():
    classifications = [WELL_FORMED_ABSTENTION] * 8 + [CONFABULATED_CALL] * 2 + [PARSE_FAILURE]
    agg = build_cell_aggregate(TW_A_CELL, classifications)
    assert agg.n_samples == 11
    assert agg.well_formed_abstention_count == 8
    assert agg.well_formed_abstention_rate == pytest.approx(8 / 11)
    assert agg.confabulated_call_count == 2
    assert agg.parse_failure_count == 1


def test_build_per_sample_table_shape():
    rows_by_cell = {
        TP_A_CELL: [OutputRow(arm=TP_A_CELL, sample_id="s1", supplied_tool=None, response="[]", timing={})],
        TW_A_CELL: [
            OutputRow(
                arm=TW_A_CELL, sample_id="s1", supplied_tool="tool01",
                response=json.dumps([{"name": "x", "arguments": {}}]), timing={},
            )
        ],
    }
    table = build_per_sample_table(rows_by_cell)
    assert table == {"s1": {TP_A_CELL: WELL_FORMED_ABSTENTION, TW_A_CELL: CONFABULATED_CALL}}


# ---------------------------------------------------------------------------
# evaluate_asymmetry_verdict -- all three branches.
# ---------------------------------------------------------------------------


def _cell_agg(cell: str, *, abst: int, confab: int, parse_fail: int = 0) -> CellAggregate:
    n = abst + confab + parse_fail
    return build_cell_aggregate(cell, [WELL_FORMED_ABSTENTION] * abst + [CONFABULATED_CALL] * confab + [PARSE_FAILURE] * parse_fail)


def test_evaluate_asymmetry_verdict_confirmed():
    per_cell = {
        TP_A_CELL: _cell_agg(TP_A_CELL, abst=0, confab=11),
        TP_S_CELL: _cell_agg(TP_S_CELL, abst=3, confab=CONFIRMED_CONFABULATION_TP_S_MIN),
        TW_A_CELL: _cell_agg(TW_A_CELL, abst=CONFIRMED_ABSTENTION_TW_A_MIN, confab=3),
        TW_S_CELL: _cell_agg(TW_S_CELL, abst=0, confab=11),
    }
    verdict = evaluate_asymmetry_verdict(per_cell)
    assert verdict.confirmed_clause.verdict == "met"
    assert verdict.overall == "ASYMMETRY-CONFIRMED"


def test_evaluate_asymmetry_verdict_refuted():
    per_cell = {
        TP_A_CELL: _cell_agg(TP_A_CELL, abst=0, confab=11),
        TP_S_CELL: _cell_agg(TP_S_CELL, abst=REFUTED_ABSTENTION_TP_S_MIN, confab=5),
        TW_A_CELL: _cell_agg(TW_A_CELL, abst=0, confab=11),  # CONFIRMED's own TW-A floor NOT met
        TW_S_CELL: _cell_agg(TW_S_CELL, abst=0, confab=11),
    }
    verdict = evaluate_asymmetry_verdict(per_cell)
    assert verdict.confirmed_clause.verdict == "not_met"
    assert verdict.refuted_clause.verdict == "met"
    assert verdict.overall == "ASYMMETRY-REFUTED"


def test_evaluate_asymmetry_verdict_inconclusive():
    per_cell = {
        TP_A_CELL: _cell_agg(TP_A_CELL, abst=0, confab=11),
        TP_S_CELL: _cell_agg(TP_S_CELL, abst=3, confab=5, parse_fail=3),  # neither floor met
        TW_A_CELL: _cell_agg(TW_A_CELL, abst=5, confab=6),  # below CONFIRMED's own 8/11 floor
        TW_S_CELL: _cell_agg(TW_S_CELL, abst=0, confab=11),
    }
    verdict = evaluate_asymmetry_verdict(per_cell)
    assert verdict.confirmed_clause.verdict == "not_met"
    assert verdict.refuted_clause.verdict == "not_met"
    assert verdict.overall == "INCONCLUSIVE-ABST"


# ---------------------------------------------------------------------------
# compute_cell_rate_bootstrap
# ---------------------------------------------------------------------------


def test_compute_cell_rate_bootstrap_point_estimate_matches_the_raw_rate():
    ids = [f"s{i}" for i in range(11)]
    classification = {sid: (WELL_FORMED_ABSTENTION if i < 8 else CONFABULATED_CALL) for i, sid in enumerate(ids)}
    result = compute_cell_rate_bootstrap(ids, classification, WELL_FORMED_ABSTENTION, n_replicates=200, seed=1)
    assert result.point_estimate == pytest.approx(8 / 11)


def test_compute_cell_rate_bootstrap_is_deterministic():
    ids = ["s1", "s2", "s3"]
    classification = {"s1": WELL_FORMED_ABSTENTION, "s2": CONFABULATED_CALL, "s3": WELL_FORMED_ABSTENTION}
    first = compute_cell_rate_bootstrap(ids, classification, WELL_FORMED_ABSTENTION, n_replicates=100, seed=7)
    second = compute_cell_rate_bootstrap(ids, classification, WELL_FORMED_ABSTENTION, n_replicates=100, seed=7)
    assert first.replicates == second.replicates


# ---------------------------------------------------------------------------
# A2tAbstWorld: a minimal frozen probe-sample receipt only (no gold, no
# registry -- module docstring: this suite never reads either).
# ---------------------------------------------------------------------------


class A2tAbstWorld:
    def __init__(self, tmp_path: Path) -> None:
        self.repo_root = tmp_path / "repo"
        self.receipt_path = self.repo_root / "docs" / "receipts" / "probe-samples" / "r1-a2t-abst-test.json"
        self._materialize()

    def _materialize(self) -> None:
        from speech_aware_evidence_acquisition.reproduction.sampling import (
            split_identity_hash as compute_hash,
        )

        items = [
            {"id": i, "key": f"audio2tool:tier1_direct:{i:06d}", "query_idx": i, "tier": "tier1_direct"}
            for i in range(1, 3)
        ]
        payload = {
            "probe": "R1-a2t-abst-test",
            "carrier": "audio2tool",
            "seed": 1,
            "design": "synthetic a2t_abst_read test receipt",
            "pool_size": len(items),
            "strata_counts": {},
            "items": items,
            "split_identity_hash": compute_hash([item["key"] for item in items]),
            "split_role": "discovery",
        }
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @property
    def split_identity_hash(self) -> str:
        return json.loads(self.receipt_path.read_text(encoding="utf-8"))["split_identity_hash"]


@pytest.fixture()
def a2tabst_world(tmp_path):
    return A2tAbstWorld(tmp_path)


_IDS = tuple(f"tier1_direct:{i:06d}" for i in range(1, 12))  # 11 ids

_ABSTAIN = "[]"
_CONFAB = json.dumps([{"name": "tool99", "arguments": {}}])
_PARSE_FAIL = "not valid json at all"


def _row(cell: str, sample_id: str, response: str) -> dict:
    return {
        "arm": cell,
        "sample_id": sample_id,
        "supplied_tool": "unused",
        "response": response,
        "timing": {"started_at": "2026-08-19T00:00:00+00:00", "latency_seconds": 0.1},
    }


def _write_outputs_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write((json.dumps(row) if isinstance(row, dict) else row) + "\n")


def _write_flight_receipt(
    path: Path, *, split_identity_hash: str, status: str = "COMPLETED", arms: list | None = None,
    request_failures: list | None = None, cells: list | None = None,
    omit_cell_list: bool = False,
) -> None:
    document = {
        "status": status,
        "error": None,
        "split_identity_hash": split_identity_hash,
        "request_failures": request_failures if request_failures is not None else [],
    }
    if not omit_cell_list:
        # The real flight machinery writes ``cells``; ``arms`` is the accepted
        # alias. Passing ``cells=`` writes the real shape, exactly one key.
        if cells is not None:
            document["cells"] = cells
        else:
            document["arms"] = arms if arms is not None else list(A2T_ABST_CELLS)
    path.write_text(json.dumps(document), encoding="utf-8")


def _uniform_responses(ids: tuple[str, ...], response: str) -> dict[str, str]:
    return {sid: response for sid in ids}


def _build_attempt(
    tmp_path: Path, world: A2tAbstWorld, *,
    tp_a: dict[str, str] | None = None, tp_s: dict[str, str] | None = None,
    tw_a: dict[str, str] | None = None, tw_s: dict[str, str] | None = None,
    ids: tuple[str, ...] = _IDS, name: str = "attempt",
    write_receipt: bool = True, receipt_kwargs: dict | None = None, extra_rows: list | None = None,
    cell_ids: dict[str, tuple[str, ...]] | None = None,
) -> Path:
    attempt_dir = tmp_path / name
    responses_by_cell = {
        TP_A_CELL: tp_a or _uniform_responses(ids, _CONFAB),
        TP_S_CELL: tp_s or _uniform_responses(ids, _CONFAB),
        TW_A_CELL: tw_a or _uniform_responses(ids, _ABSTAIN),
        TW_S_CELL: tw_s or _uniform_responses(ids, _CONFAB),
    }
    cell_ids = cell_ids or {cell: ids for cell in A2T_ABST_CELLS}
    rows = []
    for cell in A2T_ABST_CELLS:
        for sid in cell_ids[cell]:
            rows.append(_row(cell, sid, responses_by_cell[cell][sid]))
    if extra_rows:
        rows.extend(extra_rows)
    _write_outputs_jsonl(attempt_dir / "outputs.jsonl", rows)
    if write_receipt:
        kwargs = dict(split_identity_hash=world.split_identity_hash)
        kwargs.update(receipt_kwargs or {})
        _write_flight_receipt(attempt_dir / "flight-receipt.json", **kwargs)
    return attempt_dir


def _build_report(tmp_path, world, attempt_dir, **kwargs):
    kwargs.setdefault("expected_n", ABST_N)
    return build_a2t_abst_report(attempt_dir, repo_root=world.repo_root, **kwargs)


# ---------------------------------------------------------------------------
# Happy-path build_a2t_abst_report, all three verdict branches end to end.
# ---------------------------------------------------------------------------


def test_build_report_confirmed_end_to_end(a2tabst_world, tmp_path):
    world = a2tabst_world
    tw_a_ids_abstain = _IDS[:CONFIRMED_ABSTENTION_TW_A_MIN]
    tp_s_ids_confab = _IDS[:CONFIRMED_CONFABULATION_TP_S_MIN]
    tw_a = {sid: (_ABSTAIN if sid in tw_a_ids_abstain else _CONFAB) for sid in _IDS}
    tp_s = {sid: (_CONFAB if sid in tp_s_ids_confab else _ABSTAIN) for sid in _IDS}
    attempt_dir = _build_attempt(tmp_path, world, tw_a=tw_a, tp_s=tp_s)
    report = _build_report(tmp_path, world, attempt_dir)

    assert report.per_cell[TW_A_CELL].well_formed_abstention_count == CONFIRMED_ABSTENTION_TW_A_MIN
    assert report.per_cell[TP_S_CELL].confabulated_call_count == CONFIRMED_CONFABULATION_TP_S_MIN
    assert report.verdict.overall == "ASYMMETRY-CONFIRMED"
    assert set(report.per_sample_table) == set(_IDS)
    for sid in _IDS:
        assert set(report.per_sample_table[sid]) == set(A2T_ABST_CELLS)


def test_build_report_refuted_end_to_end(a2tabst_world, tmp_path):
    world = a2tabst_world
    tp_s_ids_abstain = _IDS[:REFUTED_ABSTENTION_TP_S_MIN]
    tp_s = {sid: (_ABSTAIN if sid in tp_s_ids_abstain else _CONFAB) for sid in _IDS}
    tw_a = _uniform_responses(_IDS, _CONFAB)  # TW-A never abstains -- CONFIRMED cannot fire
    attempt_dir = _build_attempt(tmp_path, world, tw_a=tw_a, tp_s=tp_s)
    report = _build_report(tmp_path, world, attempt_dir)

    assert report.per_cell[TP_S_CELL].well_formed_abstention_count == REFUTED_ABSTENTION_TP_S_MIN
    assert report.verdict.overall == "ASYMMETRY-REFUTED"


def test_build_report_inconclusive_end_to_end(a2tabst_world, tmp_path):
    world = a2tabst_world
    tw_a = {sid: (_ABSTAIN if i < 5 else _CONFAB) for i, sid in enumerate(_IDS)}  # 5/11 < 8/11 floor
    tp_s = {sid: (_ABSTAIN if i < 3 else (_CONFAB if i < 8 else _PARSE_FAIL)) for i, sid in enumerate(_IDS)}
    attempt_dir = _build_attempt(tmp_path, world, tw_a=tw_a, tp_s=tp_s)
    report = _build_report(tmp_path, world, attempt_dir)

    assert report.verdict.overall == "INCONCLUSIVE-ABST"


def test_report_to_json_shape(a2tabst_world, tmp_path):
    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world)
    report = _build_report(tmp_path, world, attempt_dir)
    document = report_to_json(report)
    assert document["schema"] == "saea-a2t-abst-read-v1"
    assert document["run_id"] == RUN_ID
    assert set(document["per_cell"]) == set(A2T_ABST_CELLS)
    assert len(document["per_sample_table"]) == len(_IDS)
    assert set(document["bootstraps_descriptive"]) == {
        "well_formed_abstention_TW-A", "confabulated_call_TP-S", "well_formed_abstention_TP-S",
    }
    assert "overall" in document["verdict"]


# ---------------------------------------------------------------------------
# Harness-defect checks (fail-closed refusal, never a soft flag).
# ---------------------------------------------------------------------------


def test_build_report_rejects_malformed_row(a2tabst_world, tmp_path):
    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world)
    with (attempt_dir / "outputs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("not json\n")
    with pytest.raises(A2tAbstReadError, match="malformed"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_non_completed_status(a2tabst_world, tmp_path):
    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world, receipt_kwargs={"status": "FAILED"})
    with pytest.raises(A2tAbstReadError, match="COMPLETED"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_non_empty_request_failures(a2tabst_world, tmp_path):
    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world, receipt_kwargs={"request_failures": [{"sample_id": "x"}]})
    with pytest.raises(A2tAbstReadError, match="request_failures"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_unexpected_arms_field(a2tabst_world, tmp_path):
    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world, receipt_kwargs={"arms": [TP_A_CELL]})
    with pytest.raises(A2tAbstReadError, match="arms"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_accepts_real_receipt_cells_key(a2tabst_world, tmp_path):
    """The flight machinery names the 4 cells under ``cells``, not ``arms``.

    Regression guard: the check previously read only ``arms`` and therefore
    saw ``None`` on every real receipt, refusing the read fail-closed.
    """

    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world, receipt_kwargs={"cells": list(A2T_ABST_CELLS)})
    report = _build_report(tmp_path, world, attempt_dir)
    assert report.flight_status == "COMPLETED"
    assert set(report.per_cell) == set(A2T_ABST_CELLS)


def test_build_report_rejects_unexpected_cells_field(a2tabst_world, tmp_path):
    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world, receipt_kwargs={"cells": [TP_A_CELL]})
    with pytest.raises(A2tAbstReadError, match="cells"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_receipt_declaring_no_cell_list(a2tabst_world, tmp_path):
    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world, receipt_kwargs={"omit_cell_list": True})
    with pytest.raises(A2tAbstReadError, match="neither 'cells' nor 'arms'"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_split_identity_hash_mismatch(a2tabst_world, tmp_path):
    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world, receipt_kwargs={"split_identity_hash": "deadbeef" * 8})
    with pytest.raises(A2tAbstReadError, match="split_identity_hash mismatch"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_unknown_cell_row(a2tabst_world, tmp_path):
    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world, extra_rows=[_row("EXTRA-CELL", _IDS[0], _ABSTAIN)])
    with pytest.raises(A2tAbstReadError, match="unknown cell"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_duplicate_cell_sample_pair(a2tabst_world, tmp_path):
    world = a2tabst_world
    dup_row = _row(TP_A_CELL, _IDS[0], _CONFAB)
    attempt_dir = _build_attempt(tmp_path, world, extra_rows=[dup_row])
    with pytest.raises(A2tAbstReadError, match="duplicate row"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_wrong_row_count_per_cell(a2tabst_world, tmp_path):
    world = a2tabst_world
    short_ids = _IDS[:-1]
    cell_ids = {cell: (short_ids if cell == TP_A_CELL else _IDS) for cell in A2T_ABST_CELLS}
    attempt_dir = _build_attempt(
        tmp_path, world,
        tp_a=_uniform_responses(short_ids, _CONFAB), cell_ids=cell_ids,
    )
    with pytest.raises(A2tAbstReadError, match="n=11 fail-closed check"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_cells_with_mismatched_sample_id_sets(a2tabst_world, tmp_path):
    world = a2tabst_world
    swapped_ids = _IDS[:-1] + ("tier1_direct:999999",)
    cell_ids = {cell: (swapped_ids if cell == TW_S_CELL else _IDS) for cell in A2T_ABST_CELLS}
    attempt_dir = _build_attempt(
        tmp_path, world,
        tw_s=_uniform_responses(swapped_ids, _CONFAB), cell_ids=cell_ids,
    )
    with pytest.raises(A2tAbstReadError, match="do not share the IDENTICAL sample-id set"):
        _build_report(tmp_path, world, attempt_dir)


# ---------------------------------------------------------------------------
# CLI: end-to-end + one-shot idempotence guard.
# ---------------------------------------------------------------------------


def test_cli_refuses_to_run_twice_against_the_same_output_dir(a2tabst_world, tmp_path):
    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world)
    output_dir = tmp_path / "read-report"
    output_dir.mkdir()

    argv = [str(attempt_dir), "--output-dir", str(output_dir), "--repo-root", str(world.repo_root)]

    first_exit = a2t_abst_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    assert (output_dir / "report.txt").is_file()

    second_exit = a2t_abst_read_main(argv)
    assert second_exit == 1


def test_cli_refuses_on_harness_defect(a2tabst_world, tmp_path):
    world = a2tabst_world
    attempt_dir = _build_attempt(tmp_path, world, receipt_kwargs={"status": "FAILED"})
    output_dir = tmp_path / "read-report"
    output_dir.mkdir()

    exit_code = a2t_abst_read_main(
        [str(attempt_dir), "--output-dir", str(output_dir), "--repo-root", str(world.repo_root)]
    )
    assert exit_code == 1
    assert not (output_dir / "verdict.json").exists()
