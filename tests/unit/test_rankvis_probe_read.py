"""scripts/analysis/rankvis_probe_read.py -- the RANKVIS probe read driver.

All synthetic: no real cell, no real sealed run, no utterance, gold or model
text (placeholder scenario/action strings only, exactly the SLURP prediction
JSON shape ``parse_slu_response`` expects -- never content that could be
mistaken for a real label). Covers the pure math, the two independently
testable pieces of the recipe (the rendering gate and the conversion
contrast) on hand-built dicts, and one end-to-end synthetic sealed-run tree
for the happy path and the "no sidecar" refusal.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "rankvis_probe_read.py"

_spec = importlib.util.spec_from_file_location("rankvis_probe_read", DRIVER_PATH)
rvpr = importlib.util.module_from_spec(_spec)
sys.modules["rankvis_probe_read"] = rvpr
_spec.loader.exec_module(rvpr)


# ---------------------------------------------------------------------------
# 1. Pure math
# ---------------------------------------------------------------------------


def test_wilson_and_clopper_pearson_bracket_the_point_estimate():
    m, n = 3, 10
    wilson = rvpr.wilson_ci95(m, n)
    exact = rvpr.clopper_pearson_ci95(m, n)
    point = m / n
    assert wilson[0] < point < wilson[1]
    assert exact[0] < point < exact[1]
    # Clopper-Pearson is the exact interval and is never narrower than Wilson.
    assert exact[0] <= wilson[0] + 1e-9
    assert exact[1] >= wilson[1] - 1e-9


def test_wilson_ci95_refuses_zero_trials():
    with pytest.raises(ValueError):
        rvpr.wilson_ci95(0, 0)


def test_rate_block_reads_against_the_no_op_never_zero():
    block = rvpr.rate_block(5, 20, no_op_expected=1.25)
    assert block["m"] == 5 and block["n"] == 20
    assert block["no_op_expectation"] == 1.25
    assert block["m_minus_no_op"] == pytest.approx(3.75)
    assert block["read_against_no_op_never_zero"] is True


def test_redeclaration_block_arithmetic_and_bar():
    below = rvpr.redeclaration_block(
        2, no_op_expected_full=1.0, intent_pp_per_row=0.2, rows_needed_net_of_no_op=3,
    )
    assert below["net_conversions_m_minus_no_op"] == pytest.approx(1.0)
    assert below["expected_effect_pp"] == pytest.approx(0.2)
    assert below["m_clears_the_bar"] is False

    above = rvpr.redeclaration_block(
        5, no_op_expected_full=1.0, intent_pp_per_row=0.2, rows_needed_net_of_no_op=3,
    )
    assert above["m_clears_the_bar"] is True
    assert above["stated_not_applied"] is True


def test_store_of_and_store_slice():
    assert rvpr._store_of("train-exemplars::value:x") == "train-exemplars"
    assert rvpr._store_of("no-separator") is None
    ids = ("intent-boundaries::a", "train-exemplars::x", "train-exemplars::y")
    assert rvpr._store_slice(ids, "train-exemplars") == ("train-exemplars::x", "train-exemplars::y")
    assert rvpr._store_slice(ids, "intent-boundaries") == ("intent-boundaries::a",)


# ---------------------------------------------------------------------------
# 2. The rendering gate, on hand-built dicts -- no sealed run needed.
# ---------------------------------------------------------------------------

BOUNDARY = ("intent-boundaries::b1", "intent-boundaries::b2")
#: e2's facet (fB) outranks e1/e3's facet (fA), so the recomputed retrieval-
#: rank order is (e2, e1, e3): e2 first (fB, higher score), then e1, e3 tied
#: on fA and broken by value id.
EXEMPLARS_TODAY = (
    "train-exemplars::e1", "train-exemplars::e2", "train-exemplars::e3",
)
EXEMPLARS_RANK_ORDER = (
    "train-exemplars::e2", "train-exemplars::e1", "train-exemplars::e3",
)


def _rank_labelled_items(store: str, ids: tuple[str, ...], extra_text: str = "") -> list[dict]:
    """One row's rendered block for ``store``: ids in document order, each
    carrying the real ``RANK_VISIBLE_LABEL`` (never a duplicated string)."""

    return [
        {
            "evidence_id": value_id,
            "content": rvpr.RANK_VISIBLE_LABEL.format(rank=rank) + "fixture-value-text" + extra_text,
        }
        for rank, value_id in enumerate(ids, start=1)
    ]


def _sealed_contacts_for(
    ids: list[str], *, boundary: tuple[str, ...] = BOUNDARY,
    exemplars: tuple[str, ...] = EXEMPLARS_RANK_ORDER, extra_text: str = "",
) -> dict[str, list[dict]]:
    """One well-formed sealed MODEL_REQUEST contact per sample id: both
    configured stores rendered with contiguous 1..n rank labels in document
    order -- the ``sealed_requests`` shape :func:`rvpr.rendering_gate` reads."""

    return {
        sample_id: [{
            "sample_id": sample_id,
            "supplied_evidence": (
                _rank_labelled_items("intent-boundaries", boundary, extra_text)
                + _rank_labelled_items("train-exemplars", exemplars, extra_text)
            ),
        }]
        for sample_id in ids
    }


def _rank_inputs_row() -> dict:
    return {
        "snapshot_sha256": "5" * 64,
        "query_state_sha256": "6" * 64,
        "ranking_policy_id": "saea-rank-test-v1",
        "fusion_policy_id": "saea-fuse-test-v1",
        "candidates": [{"facet_id": "fB", "score": 0.9}, {"facet_id": "fA", "score": 0.5}],
        "supporting_facet_ids": ["fA", "fB"],
        "values": [
            {"value_id": "train-exemplars::e1", "associated_facet_ids": ["fA"]},
            {"value_id": "train-exemplars::e2", "associated_facet_ids": ["fB"]},
            {"value_id": "train-exemplars::e3", "associated_facet_ids": ["fA"]},
        ],
    }


def _phase_result(initial_ids, final_ids) -> dict:
    return {
        "initial_query_state": {"retrieved_value_ids": list(initial_ids)},
        "final_query_state": {"retrieved_value_ids": list(final_ids)},
    }


def _base_roster_probe_comparator(ids):
    roster = {"ids": list(ids)}
    probe = {
        "phase_results": {
            sample_id: _phase_result(BOUNDARY, BOUNDARY + EXEMPLARS_RANK_ORDER)
            for sample_id in ids
        }
    }
    comparator = {
        "initial_boundary_value_ids": {sample_id: BOUNDARY for sample_id in ids},
        "exemplar_value_ids": {sample_id: EXEMPLARS_TODAY for sample_id in ids},
    }
    rank_inputs = {sample_id: {"train-exemplars": _rank_inputs_row()} for sample_id in ids}
    return roster, probe, comparator, rank_inputs


def test_recomputed_exemplar_order_matches_the_real_reorder_function():
    order = rvpr._recomputed_exemplar_order(_rank_inputs_row(), EXEMPLARS_TODAY)
    assert order == EXEMPLARS_RANK_ORDER


def test_rendering_gate_verifies_every_row_when_everything_agrees():
    roster, probe, comparator, rank_inputs = _base_roster_probe_comparator(["s1", "s2", "s3"])
    sealed = _sealed_contacts_for(["s1", "s2", "s3"])
    gate = rvpr.rendering_gate(roster, probe, comparator, rank_inputs, sealed)
    assert gate["all_rows_verified"] is True
    assert gate["stores"]["intent-boundaries"]["rows_verified"] == 3
    assert gate["stores"]["train-exemplars"]["rows_verified"] == 3
    assert gate["stores"]["train-exemplars"]["sidecar_stricter_check"]["sidecar_present"] is True


def test_rendering_gate_passes_without_a_sidecar_when_the_sealed_requests_carry_the_labels():
    """The bug RANKVIS exists to fix: no flight seals the sidecar today, but
    the gate's own definition (2026-09-28 ruling) is the rank labels in the
    sealed requests themselves, so the sidecar's absence alone must not
    refuse the read."""

    roster, probe, comparator, _rank_inputs = _base_roster_probe_comparator(["s1", "s2"])
    sealed = _sealed_contacts_for(["s1", "s2"])
    gate = rvpr.rendering_gate(roster, probe, comparator, None, sealed)
    assert gate["all_rows_verified"] is True
    assert gate["stores"]["train-exemplars"]["sidecar_stricter_check"]["sidecar_present"] is False
    assert gate["stores"]["train-exemplars"]["sidecar_stricter_check"]["rows_unverifiable_no_sidecar_row"] == 2
    assert gate["stores"]["train-exemplars"]["rows_verified"] == 2
    assert gate["stores"]["intent-boundaries"]["rows_verified"] == 2


def test_rendering_gate_seed_and_sidecar_checks_are_informational_only():
    """A moved seed, a dropped/added exemplar, or a lexicographic (not
    retrieval-rank) exemplar order no longer refuse the read by themselves --
    they are reported beside the primary rank-label check, never folded into
    ``all_rows_verified``."""

    roster, probe, comparator, rank_inputs = _base_roster_probe_comparator(["s1"])
    # The probe's own sealed seed differs from the comparator's, and the
    # sealed exemplar ids are today's lexicographic order (not what the
    # sidecar would recompute) -- neither moves the rank-labelled request.
    probe["phase_results"]["s1"] = _phase_result(
        ("intent-boundaries::OTHER",), BOUNDARY + EXEMPLARS_TODAY
    )
    sealed = _sealed_contacts_for(["s1"], exemplars=EXEMPLARS_TODAY)
    gate = rvpr.rendering_gate(roster, probe, comparator, rank_inputs, sealed)
    assert gate["all_rows_verified"] is True
    assert gate["stores"]["intent-boundaries"]["seed_equality_note"]["rows_mismatched"] == 1
    assert gate["stores"]["train-exemplars"]["sidecar_stricter_check"]["rows_order_mismatched"] == 1


def test_rendering_gate_fails_a_row_missing_the_rank_label():
    roster, probe, comparator, rank_inputs = _base_roster_probe_comparator(["s1"])
    sealed = _sealed_contacts_for(["s1"])
    sealed["s1"][0]["supplied_evidence"][0]["content"] = "no label here"
    gate = rvpr.rendering_gate(roster, probe, comparator, rank_inputs, sealed)
    assert gate["all_rows_verified"] is False
    assert gate["stores"]["intent-boundaries"]["rows_failed"] == 1
    assert gate["stores"]["intent-boundaries"]["failed_rows"] == [
        {"sample_id": "s1", "store": "intent-boundaries"}
    ]
    # The unaffected store still passes: a partial failure still reports
    # what it could verify.
    assert gate["stores"]["train-exemplars"]["rows_verified"] == 1


def test_rendering_gate_fails_a_row_with_a_non_monotone_rank():
    roster, probe, comparator, rank_inputs = _base_roster_probe_comparator(["s1"])
    sealed = _sealed_contacts_for(["s1"])
    items = sealed["s1"][0]["supplied_evidence"]
    # Swap the two intent-boundaries ranks: document order now reads 2, 1.
    items[0]["content"], items[1]["content"] = items[1]["content"], items[0]["content"]
    gate = rvpr.rendering_gate(roster, probe, comparator, rank_inputs, sealed)
    assert gate["all_rows_verified"] is False
    assert gate["stores"]["intent-boundaries"]["rows_failed"] == 1
    assert gate["stores"]["intent-boundaries"]["failed_rows"] == [
        {"sample_id": "s1", "store": "intent-boundaries"}
    ]


def test_rendering_gate_fails_a_row_with_a_count_mismatch():
    roster, probe, comparator, rank_inputs = _base_roster_probe_comparator(["s1"])
    sealed = _sealed_contacts_for(["s1"])
    # Drop the last train-exemplars item: the rendered block now carries 2
    # values (still labelled 1..2), not the 3 the sealed phase receipt
    # (final_query_state) says were delivered.
    del sealed["s1"][0]["supplied_evidence"][-1]
    gate = rvpr.rendering_gate(roster, probe, comparator, rank_inputs, sealed)
    assert gate["all_rows_verified"] is False
    assert gate["stores"]["train-exemplars"]["rows_failed"] == 1
    assert gate["stores"]["train-exemplars"]["failed_rows"] == [
        {"sample_id": "s1", "store": "train-exemplars"}
    ]


def test_rendering_gate_fails_a_row_with_no_sealed_request_at_all():
    roster, probe, comparator, rank_inputs = _base_roster_probe_comparator(["s1"])
    gate = rvpr.rendering_gate(roster, probe, comparator, rank_inputs, {})
    assert gate["all_rows_verified"] is False
    assert gate["stores"]["intent-boundaries"]["rows_failed"] == 1
    assert gate["stores"]["train-exemplars"]["rows_failed"] == 1


# ---------------------------------------------------------------------------
# 2b. rank_label_report -- the primary check's pure function, no sealed run
# or gate needed. Fixtures for pass, a missing label, a non-monotone rank,
# and a count mismatch (the four cases the coordinator ruling names).
# ---------------------------------------------------------------------------


def test_rank_label_report_verifies_a_well_formed_block():
    contacts = [{"supplied_evidence": _rank_labelled_items("train-exemplars", EXEMPLARS_RANK_ORDER)}]
    report = rvpr.rank_label_report(contacts, "train-exemplars", delivered_count=3)
    assert report == {
        "contact_found": True, "rendered_count": 3, "unlabelled_count": 0,
        "ranks_ok": True, "count_matches_receipt": True, "delivered_count": 3,
        "verified": True,
    }


def test_rank_label_report_fails_on_a_missing_label():
    items = _rank_labelled_items("train-exemplars", EXEMPLARS_RANK_ORDER)
    items[1]["content"] = "no rank label at all"
    contacts = [{"supplied_evidence": items}]
    report = rvpr.rank_label_report(contacts, "train-exemplars", delivered_count=3)
    assert report["verified"] is False
    assert report["unlabelled_count"] == 1
    assert report["ranks_ok"] is False


def test_rank_label_report_fails_on_a_non_monotone_rank():
    items = _rank_labelled_items("train-exemplars", EXEMPLARS_RANK_ORDER)
    items[1]["content"], items[2]["content"] = items[2]["content"], items[1]["content"]
    contacts = [{"supplied_evidence": items}]
    report = rvpr.rank_label_report(contacts, "train-exemplars", delivered_count=3)
    assert report["verified"] is False
    assert report["unlabelled_count"] == 0
    assert report["ranks_ok"] is False


def test_rank_label_report_fails_on_a_count_mismatch():
    contacts = [{"supplied_evidence": _rank_labelled_items("train-exemplars", EXEMPLARS_RANK_ORDER)}]
    report = rvpr.rank_label_report(contacts, "train-exemplars", delivered_count=4)
    assert report["verified"] is False
    assert report["ranks_ok"] is True
    assert report["count_matches_receipt"] is False


def test_rank_label_report_uses_the_first_contact_that_carries_the_store():
    later = {"supplied_evidence": _rank_labelled_items("train-exemplars", EXEMPLARS_RANK_ORDER)}
    earlier_wrong = {"supplied_evidence": [{"evidence_id": "train-exemplars::v1", "content": "no label"}]}
    contacts = [earlier_wrong, later]
    report = rvpr.rank_label_report(contacts, "train-exemplars", delivered_count=1)
    assert report["verified"] is False  # the FIRST carrying contact is checked, not the later well-formed one
    assert report["rendered_count"] == 1


def test_rank_label_report_ignores_other_stores_items():
    items = _rank_labelled_items("train-exemplars", EXEMPLARS_RANK_ORDER) + [
        {"evidence_id": "intent-boundaries::b1", "content": "garbage, wrong store"}
    ]
    contacts = [{"supplied_evidence": items}]
    report = rvpr.rank_label_report(contacts, "train-exemplars", delivered_count=3)
    assert report["verified"] is True
    assert report["rendered_count"] == 3


def test_rank_label_report_missing_store_entirely_matches_a_zero_receipt():
    report = rvpr.rank_label_report([{"supplied_evidence": []}], "train-exemplars", delivered_count=0)
    assert report["contact_found"] is False
    assert report["verified"] is True


def test_rank_label_report_missing_store_entirely_fails_a_nonzero_receipt():
    report = rvpr.rank_label_report([{"supplied_evidence": []}], "train-exemplars", delivered_count=3)
    assert report["contact_found"] is False
    assert report["verified"] is False


# ---------------------------------------------------------------------------
# 3. The conversion contrast, on hand-built dicts.
# ---------------------------------------------------------------------------


def _slu(scenario: str, action: str) -> str:
    return json.dumps({"scenario": scenario, "action": action, "entities": []})


def test_contrast_classifies_the_four_way_split():
    ids = ["s1", "s2", "s3"]
    probe = {
        "per_sample": {
            "s1": {rvpr.FIELD: 1.0}, "s2": {rvpr.FIELD: 0.0}, "s3": {rvpr.FIELD: 0.0},
        },
        "outputs": {
            "s1": {"text": _slu("gold", "answer")},
            "s2": {"text": _slu("same", "wrong")},
            "s3": {"text": _slu("different", "wrong")},
        },
    }
    comparator = {
        "outputs": {
            "s1": {"text": _slu("comparator", "wrong")},
            "s2": {"text": _slu("same", "wrong")},
            "s3": {"text": _slu("comparator", "otherwrong")},
        },
    }
    block = rvpr.contrast(ids, probe, comparator)
    assert block["m_wrong_to_gold"] == 1
    assert block["r_gold_to_wrong"] == 0
    assert block["four_way_split"] == {
        "wrong_to_gold": 1, "gold_to_wrong": 0, "same_wrong_intent": 1, "different_wrong_intent": 1,
    }


def test_by_stage_block_counts_rows_and_m_per_stage():
    ids = ["s1", "s2", "s3"]
    contrast_rows = {
        "per_row": [
            {"sample_id": "s1", "probe_intent_exact": True},
            {"sample_id": "s2", "probe_intent_exact": False},
            {"sample_id": "s3", "probe_intent_exact": False},
        ]
    }
    roster = {
        "stage_by_id": {
            "s1": "CONSUMPTION-PERCEPTION-DROP",
            "s2": "CONSUMPTION-SOLVER-CHOICE",
            "s3": "CONSUMPTION-SOLVER-CHOICE",
        }
    }
    by_stage = rvpr.by_stage_block(ids, contrast_rows, roster)
    assert by_stage == {
        "CONSUMPTION-PERCEPTION-DROP": {"rows": 1, "m": 1},
        "CONSUMPTION-SOLVER-CHOICE": {"rows": 2, "m": 0},
    }


# ---------------------------------------------------------------------------
# 4. End to end: a full synthetic sealed-run tree.
# ---------------------------------------------------------------------------


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, document: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, indent=2, sort_keys=True)
    path.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


def _write_jsonl(path: Path, rows: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n"
    path.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


#: The three synthetic roster rows shared by every end-to-end test.
ROSTER_IDS = ["s1", "s2", "s3"]
NULL_SAVE_RATE = {"1": 0.4, "2-8": 0.1}
BAND_BY_ID = {"s1": "1", "s2": "2-8", "s3": "2-8"}
IN_SYNTHESIS_SUBSET = {"s1": True, "s2": True, "s3": False}
STAGE_BY_ID = {
    "s1": "CONSUMPTION-PERCEPTION-DROP", "s2": "CONSUMPTION-SOLVER-CHOICE", "s3": "CONSUMPTION-SOLVER-CHOICE",
}
SPLIT_IDENTITY_HASH = "7" * 64
CONFIG_HASH = "synthetic-config-hash-v1"


def _write_sealed_run(
    data_root: Path, *, run_id: str, attempt_id: str, exact_by_id: dict, text_by_id: dict,
    initial_ids_by_id: dict, final_ids_by_id: dict,
) -> None:
    run_dir = data_root / "runs" / run_id / attempt_id
    outputs = [
        {"sample_id": sid, "text": text_by_id[sid]} for sid in ROSTER_IDS
    ]
    outputs_sha = _write_jsonl(run_dir / f"{run_id}.outputs.jsonl", outputs)
    per_sample = [{"sample_id": sid, rvpr.FIELD: exact_by_id[sid]} for sid in ROSTER_IDS]
    aggregate_intent = sum(exact_by_id.values()) / len(ROSTER_IDS)
    scores_doc = {
        rvpr.SCORER: {
            "per_sample": per_sample,
            "aggregate": {"samples": len(ROSTER_IDS), "official": {"intent_accuracy": aggregate_intent}},
        }
    }
    scores_sha = _write_json(run_dir / f"{run_id}.scores.json", scores_doc)
    phases_doc = {
        "schema": "saea-flight-phase-summaries-v1",
        "phases": [{"results": [
            {
                "sample_id": sid,
                "initial_query_state": {"retrieved_value_ids": list(initial_ids_by_id[sid])},
                "final_query_state": {"retrieved_value_ids": list(final_ids_by_id[sid])},
            }
            for sid in ROSTER_IDS
        ]}],
    }
    _write_json(run_dir / f"{run_id}.phases.json", phases_doc)
    manifest = {
        "run_id": run_id, "status": "COMPLETED", "study_repo_dirt": False,
        "attempt": {"attempt_id": attempt_id},
        "split": {"count": len(ROSTER_IDS), "ids": ROSTER_IDS, "identity_hash": SPLIT_IDENTITY_HASH},
        "outputs": {"sha256": outputs_sha}, "scores": {"sha256": scores_sha},
        "config": {"config_hash": CONFIG_HASH},
        "scorers": [rvpr.SCORER],
        "study_commit": "deadbeef",
    }
    _write_json(run_dir / f"{run_id}.run-manifest.json", manifest)
    _write_json(data_root / "attempts" / run_id / f"{attempt_id}.json", {"state": "FINALIZED"})
    result_text = json.dumps({"ok": True}, sort_keys=True)
    (run_dir / "score-batch").mkdir(parents=True, exist_ok=True)
    (run_dir / "score-batch" / "result.json").write_text(result_text, encoding="utf-8")
    result_sha = _sha256_bytes(result_text.encode("utf-8"))
    _write_json(
        run_dir / "score-batch" / "batch-summary.json",
        {"job_count": 1, "succeeded": 1, "jobs": [
            {"job_id": "job-1", "status": "SUCCEEDED", "result_file": "result.json", "result_sha256": result_sha},
        ]},
    )
    _write_jsonl(run_dir / "score-jobs.jsonl", [{"job_id": "job-1"}])


def _write_registered_package(repo: Path) -> None:
    package = repo / rvpr.PACKAGE
    per_row = [
        {
            "sample_id": sid, "agree_gold_position_band": BAND_BY_ID[sid],
            "in_synthesis_subset": IN_SYNTHESIS_SUBSET[sid],
            "primary": STAGE_BY_ID[sid], "stage": STAGE_BY_ID[sid],
        }
        for sid in ROSTER_IDS
    ]
    id_list_sha = rvpr.id_list_sha256(ROSTER_IDS)
    synthesis_ids = sorted(sid for sid in ROSTER_IDS if IN_SYNTHESIS_SUBSET[sid])
    synthesis_id_list_sha = rvpr.id_list_sha256(synthesis_ids)
    no_op_full = sum(NULL_SAVE_RATE[BAND_BY_ID[sid]] for sid in ROSTER_IDS)
    no_op_subset = sum(NULL_SAVE_RATE[BAND_BY_ID[sid]] for sid in synthesis_ids)
    roster_doc = {
        "roster": {"per_row": per_row, "id_list_sha256": id_list_sha, "split_identity_hash": SPLIT_IDENTITY_HASH},
        "synthesis_subset": {"id_list_sha256": synthesis_id_list_sha},
    }
    roster_sha = _write_json(package / "roster-derivation-v1.json", roster_doc)

    baseline_relpath = "configs/baseline/synthetic-rankvis-baseline-v1.json"
    baseline_doc = {"native_episode": {"knowledge_value_rendering": dict(rvpr.EXPECTED_RENDERING)}}
    baseline_sha = _write_json(repo / baseline_relpath, baseline_doc)

    facts_doc = {
        "schema": rvpr.FACTS_SCHEMA,
        "cell": {"run_id": rvpr.PROBE_RUN_ID, "baseline": baseline_relpath, "baseline_sha256": baseline_sha},
        "roster": {"rows": len(ROSTER_IDS), "id_list_sha256": id_list_sha},
        "roster_derivation": {"sha256": roster_sha},
        "synthesis_subset": {"rows": len(synthesis_ids), "id_list_sha256": synthesis_id_list_sha},
        "no_op_expectation": {
            "null_save_rate": NULL_SAVE_RATE,
            "expected_null_conversions": no_op_full,
            "expected_null_conversions_synthesis_subset": no_op_subset,
        },
        "re_declaration_rule": {"pp_per_row": 0.2, "m_needed_for_the_2p5_pp_bar": 3},
    }
    _write_json(package / "registered-facts-v1.json", facts_doc)
    _write_json(
        package / "generation-plan-registered-v1.json",
        {"composed_config_hash": CONFIG_HASH, "attempt_id": "attempt-synthetic-rankvis-generation-v1"},
    )


def _write_sidecar(data_root: Path, run_id: str, attempt_id: str) -> None:
    _write_json(
        data_root / "runs" / run_id / attempt_id / f"{run_id}.retrieval-rank-inputs.json",
        {"schema": rvpr.RENDERING_SIDECAR_SCHEMA, "rows": {
            sid: {"train-exemplars": _rank_inputs_row()} for sid in ROSTER_IDS
        }},
    )


def _write_sealed_trace(
    data_root: Path, *, run_id: str, attempt_id: str, ids: list[str], extra_text: str = "",
) -> None:
    """The sealed run's own append-only MODEL_REQUEST trace
    (``core.tracing.TraceSink``): one JSON line per row's sole contact,
    carrying a well-formed rank-labelled block for both configured stores --
    the rendering gate's primary evidence since the 2026-09-28 ruling."""

    run_dir = data_root / "runs" / run_id / attempt_id
    sealed = _sealed_contacts_for(ids, extra_text=extra_text)
    lines = []
    for sample_id in ids:
        payload = sealed[sample_id][0]
        record = {
            "channel": "MODEL_REQUEST",
            "record_id": f"{sample_id}/request",
            "payload": {"arm": "synthetic-test-arm", "payload": payload, "payload_sha256": "0" * 64},
        }
        lines.append(json.dumps(record, sort_keys=True))
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / f"{run_id}.trace.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_end_to_end(tmp_path: Path, *, extra_text: str = "") -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    data_root = tmp_path / "data"
    _write_registered_package(repo)
    attempt_id = "attempt-synthetic-rankvis-generation-v1"

    # The comparator: intent-wrong on every row, today's lexicographic
    # exemplar order.
    _write_sealed_run(
        data_root, run_id=rvpr.COMPARATOR_RUN_ID, attempt_id=rvpr.COMPARATOR_ATTEMPT_ID,
        exact_by_id={"s1": 0.0, "s2": 0.0, "s3": 0.0},
        text_by_id={sid: _slu("comparator", "wrong") for sid in ROSTER_IDS},
        initial_ids_by_id={sid: BOUNDARY for sid in ROSTER_IDS},
        final_ids_by_id={sid: BOUNDARY + EXEMPLARS_TODAY for sid in ROSTER_IDS},
    )
    # The probe: s1 converts to gold, s2 and s3 stay wrong; every row's
    # exemplar block is rendered in the recomputed retrieval-rank order.
    _write_sealed_run(
        data_root, run_id=rvpr.PROBE_RUN_ID, attempt_id=attempt_id,
        exact_by_id={"s1": 1.0, "s2": 0.0, "s3": 0.0},
        text_by_id={
            "s1": _slu("gold", "answer"),
            "s2": _slu("comparator", "wrong"),
            "s3": _slu("different", "wrong"),
        },
        initial_ids_by_id={sid: BOUNDARY for sid in ROSTER_IDS},
        final_ids_by_id={sid: BOUNDARY + EXEMPLARS_RANK_ORDER for sid in ROSTER_IDS},
    )
    _write_sidecar(data_root, rvpr.PROBE_RUN_ID, attempt_id)
    _write_sealed_trace(
        data_root, run_id=rvpr.PROBE_RUN_ID, attempt_id=attempt_id, ids=ROSTER_IDS,
        extra_text=extra_text,
    )
    return repo, data_root


def _run_driver(repo: Path, data_root: Path, output_root: Path) -> int:
    parser = rvpr.build_arg_parser()
    args = parser.parse_args([
        "--repo-root", str(repo), "--data-root", str(data_root), "--output-root", str(output_root),
    ])
    return rvpr.run(args)


def test_end_to_end_happy_path_reads_m_and_verifies_the_gate(tmp_path, capsys):
    repo, data_root = _build_end_to_end(tmp_path)
    output_root = tmp_path / "out"
    status = _run_driver(repo, data_root, output_root)
    assert status == 0
    result = json.loads((output_root / "read-v1.json").read_text(encoding="utf-8"))
    assert result["contrast"]["m_wrong_to_gold"] == 1
    assert result["rate"]["n"] == 3
    assert result["subset_rate"]["n"] == 2
    assert result["subset_rate"]["m"] == 1
    assert result["rendering_gate"]["all_rows_verified"] is True
    assert result["redeclaration"]["expected_effect_pp"] == pytest.approx((1 - 0.6) * 0.2)
    markdown = (output_root / "read-v1.md").read_text(encoding="utf-8")
    assert "Cell RANKVIS read: m = 1 of 3" in markdown
    printed = capsys.readouterr().out
    assert "written under" in printed


def test_end_to_end_passes_without_the_sidecar_when_sealed_requests_carry_the_labels(tmp_path):
    """The bug RANKVIS exists to fix: no flight seals the sidecar today, and
    the 2026-09-28 ruling's fix is that the read no longer refuses merely
    for that -- the gate's own definition is the rank labels in the sealed
    requests themselves, which the fixture's sealed trace already carries."""

    repo, data_root = _build_end_to_end(tmp_path)
    sidecar = data_root / "runs" / rvpr.PROBE_RUN_ID / "attempt-synthetic-rankvis-generation-v1" / f"{rvpr.PROBE_RUN_ID}.retrieval-rank-inputs.json"
    sidecar.unlink()
    output_root = tmp_path / "out"
    status = _run_driver(repo, data_root, output_root)
    assert status == 0
    result = json.loads((output_root / "read-v1.json").read_text(encoding="utf-8"))
    assert result["rendering_gate"]["all_rows_verified"] is True
    assert result["rendering_gate"]["stores"]["train-exemplars"]["sidecar_stricter_check"]["sidecar_present"] is False


def test_end_to_end_refuses_when_no_sealed_trace_file_exists(tmp_path):
    repo, data_root = _build_end_to_end(tmp_path)
    trace_path = (
        data_root / "runs" / rvpr.PROBE_RUN_ID / "attempt-synthetic-rankvis-generation-v1"
        / f"{rvpr.PROBE_RUN_ID}.trace.jsonl"
    )
    trace_path.unlink()
    output_root = tmp_path / "out"
    status = _run_driver(repo, data_root, output_root)
    assert status == 2
    refusal = json.loads((output_root / "refusal-v1.json").read_text(encoding="utf-8"))
    assert refusal["refused_at_step"] == 2
    assert refusal["conversion_number_written"] is False
    assert not (output_root / "read-v1.json").exists()


def test_end_to_end_refuses_when_a_sealed_request_is_missing_a_rank_label(tmp_path):
    repo, data_root = _build_end_to_end(tmp_path)
    trace_path = (
        data_root / "runs" / rvpr.PROBE_RUN_ID / "attempt-synthetic-rankvis-generation-v1"
        / f"{rvpr.PROBE_RUN_ID}.trace.jsonl"
    )
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    record["payload"]["payload"]["supplied_evidence"][0]["content"] = "no rank label here"
    lines[0] = json.dumps(record, sort_keys=True)
    trace_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    output_root = tmp_path / "out"
    status = _run_driver(repo, data_root, output_root)
    assert status == 2
    refusal = json.loads((output_root / "refusal-v1.json").read_text(encoding="utf-8"))
    assert refusal["refused_at_step"] == 2
    assert not (output_root / "read-v1.json").exists()


def test_end_to_end_outputs_contain_no_fixture_text(tmp_path, capsys):
    """The gate parses sealed request text but must only ever emit ids,
    ranks, counts and booleans -- never the fixture's own content string."""

    marker = "FIXTURE-CONTENT-MUST-NEVER-LEAK-9f3c2a"
    repo, data_root = _build_end_to_end(tmp_path, extra_text=marker)
    output_root = tmp_path / "out"
    status = _run_driver(repo, data_root, output_root)
    assert status == 0
    json_text = (output_root / "read-v1.json").read_text(encoding="utf-8")
    markdown_text = (output_root / "read-v1.md").read_text(encoding="utf-8")
    printed = capsys.readouterr().out
    assert marker not in json_text
    assert marker not in markdown_text
    assert marker not in printed


def test_end_to_end_refuses_when_a_comparator_row_is_not_intent_wrong(tmp_path):
    repo, data_root = _build_end_to_end(tmp_path)
    # Corrupt the comparator's own scores so it is no longer intent-wrong on
    # every row, as the roster's own definition requires.
    comparator_scores = (
        data_root / "runs" / rvpr.COMPARATOR_RUN_ID / rvpr.COMPARATOR_ATTEMPT_ID
        / f"{rvpr.COMPARATOR_RUN_ID}.scores.json"
    )
    doc = json.loads(comparator_scores.read_text(encoding="utf-8"))
    doc[rvpr.SCORER]["per_sample"][0][rvpr.FIELD] = 1.0
    text = json.dumps(doc, indent=2, sort_keys=True)
    comparator_scores.write_text(text, encoding="utf-8")
    # The manifest's pinned hash must move with it, or an earlier gate (not
    # this one) refuses first.
    manifest_path = (
        data_root / "runs" / rvpr.COMPARATOR_RUN_ID / rvpr.COMPARATOR_ATTEMPT_ID
        / f"{rvpr.COMPARATOR_RUN_ID}.run-manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scores"]["sha256"] = _sha256_bytes(text.encode("utf-8"))
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    output_root = tmp_path / "out"
    status = _run_driver(repo, data_root, output_root)
    assert status == 2
    refusal = json.loads((output_root / "refusal-v1.json").read_text(encoding="utf-8"))
    assert refusal["refused_at_step"] == 4
    assert "intent-CORRECT" in refusal["reason"]


def test_end_to_end_refuses_when_the_baseline_does_not_declare_the_rendering_key(tmp_path):
    repo, data_root = _build_end_to_end(tmp_path)
    baseline_path = repo / "configs" / "baseline" / "synthetic-rankvis-baseline-v1.json"
    doc = json.loads(baseline_path.read_text(encoding="utf-8"))
    doc["native_episode"]["knowledge_value_rendering"]["rank_visible"] = False
    text = json.dumps(doc, indent=2, sort_keys=True)
    baseline_path.write_text(text, encoding="utf-8")
    facts_path = repo / rvpr.PACKAGE / "registered-facts-v1.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["cell"]["baseline_sha256"] = _sha256_bytes(text.encode("utf-8"))
    facts_path.write_text(json.dumps(facts, indent=2, sort_keys=True), encoding="utf-8")

    output_root = tmp_path / "out"
    status = _run_driver(repo, data_root, output_root)
    assert status == 2
    refusal = json.loads((output_root / "refusal-v1.json").read_text(encoding="utf-8"))
    assert refusal["refused_at_step"] == 1
    assert "rank labels" in refusal["reason"]
