"""``analysis.pemb_read``: the P-EMB pinned offline read suite
(docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md). Model-free,
read-only -- every test drives hand-built synthetic manifests/fixtures;
this module is never pointed at a real embedding-vector manifest by the
task that wrote it.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.pemb_read import (
    EMB_CLOSED_MAX_TOP1,
    EMB_OPENS_183_MIN_RECOVERIES,
    EMB_OPENS_183_MIN_TOP1,
    EMB_ROUTES_MIN_ACCURACY,
    EMB_WEAK_MAX_ACCURACY,
    ConfusionCell,
    PembReadError,
    _refuse_if_already_run,
    build_confusion_table,
    build_run_a_report,
    build_run_b_report,
    cosine_similarity,
    derive_tool_correct_partition,
    evaluate_run_a_verdict,
    evaluate_run_b_verdict,
    gold_tools_for_run_b,
    rank_cosine,
    render_run_a_report,
    render_run_b_report,
    resolve_a0_attempt_dir,
    run_a_report_to_json,
    run_b_report_to_json,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.probes.a2t_pop_flight import SPLIT_IDENTITY_HASH
from speech_aware_evidence_acquisition.rails.probes.pemb_flight import (
    RUN_A_ID,
    RUN_B_ID,
    LoadedEmbeddingManifest,
)

from test_a2t_pop_flight import _write_zero_supply_outputs  # reuse the SAME fixture-world helper

# ---------------------------------------------------------------------------
# cosine_similarity / rank_cosine.
# ---------------------------------------------------------------------------


def test_cosine_similarity_of_identical_vectors_is_one():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_cosine_similarity_of_orthogonal_vectors_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_of_opposite_vectors_is_minus_one():
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_similarity_is_scale_invariant():
    assert cosine_similarity([1.0, 0.0], [50.0, 0.0]) == pytest.approx(1.0)


def test_cosine_similarity_refuses_zero_norm_vector():
    with pytest.raises(PembReadError, match="zero-norm"):
        cosine_similarity([0.0, 0.0], [1.0, 0.0])


def test_rank_cosine_orders_by_similarity_descending():
    query = [1.0, 0.0]
    candidates = {"far": [0.0, 1.0], "near": [0.9, 0.1], "exact": [1.0, 0.0]}
    ranking = rank_cosine(query, candidates)
    assert [candidate_id for candidate_id, _ in ranking] == ["exact", "near", "far"]
    assert ranking[0][1] == pytest.approx(1.0)


def test_rank_cosine_tie_breaks_by_candidate_id_ascending():
    query = [1.0, 0.0]
    candidates = {"b": [1.0, 0.0], "a": [1.0, 0.0]}
    ranking = rank_cosine(query, candidates)
    assert [candidate_id for candidate_id, _ in ranking] == ["a", "b"]


def test_rank_cosine_refuses_empty_candidates():
    with pytest.raises(PembReadError, match="non-empty"):
        rank_cosine([1.0, 0.0], {})


# ---------------------------------------------------------------------------
# build_confusion_table.
# ---------------------------------------------------------------------------


def test_build_confusion_table_counts_and_sorts():
    pairs = [("iot", "iot"), ("iot", "iot"), ("email", "iot"), ("iot", "email")]
    table = build_confusion_table(pairs)
    assert table[0] == ConfusionCell(gold="iot", predicted="iot", count=2)
    assert set((c.gold, c.predicted, c.count) for c in table) == {
        ("iot", "iot", 2),
        ("email", "iot", 1),
        ("iot", "email", 1),
    }


def test_build_confusion_table_respects_limit():
    pairs = [("a", "a"), ("b", "b"), ("c", "c")]
    table = build_confusion_table(pairs, limit=2)
    assert len(table) == 2


# ---------------------------------------------------------------------------
# evaluate_run_a_verdict -- all three branches, boundaries included.
# ---------------------------------------------------------------------------


def test_evaluate_run_a_verdict_routes_at_and_above_threshold():
    verdict, _detail = evaluate_run_a_verdict(EMB_ROUTES_MIN_ACCURACY)
    assert verdict == "EMB-ROUTES"
    verdict, _detail = evaluate_run_a_verdict(1.0)
    assert verdict == "EMB-ROUTES"


def test_evaluate_run_a_verdict_weak_at_and_below_threshold():
    verdict, _detail = evaluate_run_a_verdict(EMB_WEAK_MAX_ACCURACY)
    assert verdict == "EMB-WEAK"
    verdict, _detail = evaluate_run_a_verdict(0.0)
    assert verdict == "EMB-WEAK"


def test_evaluate_run_a_verdict_inconclusive_strictly_between():
    verdict, _detail = evaluate_run_a_verdict(0.5)
    assert verdict == "INCONCLUSIVE-EMB1"


# ---------------------------------------------------------------------------
# evaluate_run_b_verdict -- all three branches, including the AND clause.
# ---------------------------------------------------------------------------


def test_evaluate_run_b_verdict_opens_183_requires_both_clauses():
    verdict, _detail = evaluate_run_b_verdict(
        top1_accuracy_183=EMB_OPENS_183_MIN_TOP1, recoveries_183=EMB_OPENS_183_MIN_RECOVERIES
    )
    assert verdict == "EMB-OPENS-183"


def test_evaluate_run_b_verdict_high_top1_but_low_recoveries_is_not_opens_183():
    # top1 passes the ratio threshold but the absolute-count clause fails --
    # the AND is enforced, never either clause alone.
    verdict, detail = evaluate_run_b_verdict(top1_accuracy_183=0.9, recoveries_183=10)
    assert verdict != "EMB-OPENS-183"
    assert "10" in detail


def test_evaluate_run_b_verdict_high_recoveries_but_low_top1_ratio_is_not_opens_183():
    verdict, _detail = evaluate_run_b_verdict(top1_accuracy_183=0.05, recoveries_183=60)
    assert verdict != "EMB-OPENS-183"


def test_evaluate_run_b_verdict_closed_at_and_below_threshold():
    verdict, _detail = evaluate_run_b_verdict(top1_accuracy_183=EMB_CLOSED_MAX_TOP1, recoveries_183=0)
    assert verdict == "EMB-CLOSED"
    verdict, _detail = evaluate_run_b_verdict(top1_accuracy_183=0.0, recoveries_183=0)
    assert verdict == "EMB-CLOSED"


def test_evaluate_run_b_verdict_inconclusive_strictly_between():
    verdict, _detail = evaluate_run_b_verdict(top1_accuracy_183=0.2, recoveries_183=20)
    assert verdict == "INCONCLUSIVE-EMB2"


# ---------------------------------------------------------------------------
# build_run_a_report -- synthetic 2D-vector manifest, exact predictions.
# ---------------------------------------------------------------------------


def _manifest_a():
    audio = {
        "s1": [0.9, 0.1],  # close to "iot"
        "s2": [0.1, 0.9],  # close to "email"
        "s3": [0.2, 0.8],  # close to "email" -- gold is "iot", a miss
    }
    text = {"iot": [1.0, 0.0], "email": [0.0, 1.0]}
    return LoadedEmbeddingManifest(run_id=RUN_A_ID, audio=audio, text=text)


_GOLD_A = {"s1": "iot", "s2": "email", "s3": "iot"}
_LABELS_A = ("email", "iot")


def test_build_run_a_report_computes_accuracy_and_confusion():
    manifest = _manifest_a()
    report = build_run_a_report(manifest, _GOLD_A, _LABELS_A, expected_audio_n=3, expected_label_n=2)
    assert report.n_samples == 3
    assert report.n_correct == 2
    assert report.accuracy == pytest.approx(2 / 3)
    assert report.verdict == "EMB-ROUTES"  # 0.6667 >= 0.65
    by_id = {p.sample_id: p for p in report.predictions}
    assert by_id["s1"].predicted_scenario == "iot"
    assert by_id["s1"].top1_correct is True
    assert by_id["s3"].predicted_scenario == "email"
    assert by_id["s3"].top1_correct is False
    assert set((c.gold, c.predicted, c.count) for c in report.confusion) == {
        ("iot", "iot", 1),
        ("email", "email", 1),
        ("iot", "email", 1),
    }


def test_build_run_a_report_is_idempotent():
    manifest = _manifest_a()
    report1 = build_run_a_report(manifest, _GOLD_A, _LABELS_A, expected_audio_n=3, expected_label_n=2)
    report2 = build_run_a_report(manifest, _GOLD_A, _LABELS_A, expected_audio_n=3, expected_label_n=2)
    assert report1 == report2


def test_build_run_a_report_rejects_wrong_run_id():
    manifest = LoadedEmbeddingManifest(run_id="not-run-a", audio={}, text={})
    with pytest.raises(PembReadError, match="run_id"):
        build_run_a_report(manifest, {}, (), expected_audio_n=0, expected_label_n=0)


def test_build_run_a_report_rejects_audio_gold_id_mismatch():
    manifest = _manifest_a()
    bad_gold = dict(_GOLD_A)
    del bad_gold["s3"]
    with pytest.raises(PembReadError, match="id sets disagree"):
        build_run_a_report(manifest, bad_gold, _LABELS_A, expected_audio_n=3, expected_label_n=2)


def test_build_run_a_report_rejects_label_set_mismatch():
    manifest = _manifest_a()
    with pytest.raises(PembReadError, match="id sets disagree"):
        build_run_a_report(manifest, _GOLD_A, ("iot",), expected_audio_n=3, expected_label_n=2)


def test_build_run_a_report_rejects_wrong_expected_counts():
    manifest = _manifest_a()
    with pytest.raises(PembReadError, match="audio vector"):
        build_run_a_report(manifest, _GOLD_A, _LABELS_A, expected_audio_n=60, expected_label_n=2)


def test_run_a_report_to_json_and_render_round_trip():
    manifest = _manifest_a()
    report = build_run_a_report(manifest, _GOLD_A, _LABELS_A, expected_audio_n=3, expected_label_n=2)
    document = run_a_report_to_json(report)
    # Must be JSON-serializable and carry the verdict + every prediction.
    text = json.dumps(document)
    assert json.loads(text)["verdict"] == "EMB-ROUTES"
    assert len(document["predictions"]) == 3
    rendered = render_run_a_report(report)
    assert "EMB-ROUTES" in rendered
    assert "n_samples=3" in rendered


# ---------------------------------------------------------------------------
# build_run_b_report -- synthetic 3D-vector manifest, exact predictions.
# ---------------------------------------------------------------------------


def _manifest_b():
    audio = {
        "s1": [1.0, 0.0, 0.0],  # correct partition, predicts toolA
        "s2": [0.0, 1.0, 0.0],  # correct partition, predicts toolB
        "s3": [0.0, 0.0, 1.0],  # wrong partition, predicts toolC -- gold {toolA, toolC}: a recovery
        "s4": [1.0, 0.0, 0.0],  # wrong partition, predicts toolA -- gold {toolB}: not a recovery
        "s5": [0.0, 0.0, 1.0],  # wrong partition, predicts toolC -- gold {toolC}: a recovery
    }
    text = {"toolA": [1.0, 0.0, 0.0], "toolB": [0.0, 1.0, 0.0], "toolC": [0.0, 0.0, 1.0]}
    return LoadedEmbeddingManifest(run_id=RUN_B_ID, audio=audio, text=text)


_GOLD_B = {
    "s1": frozenset({"toolA"}),
    "s2": frozenset({"toolB"}),
    "s3": frozenset({"toolA", "toolC"}),
    "s4": frozenset({"toolB"}),
    "s5": frozenset({"toolC"}),
}
_TOOL_CORRECT_IDS_B = frozenset({"s1", "s2"})
_TOOL_WRONG_IDS_B = frozenset({"s3", "s4", "s5"})


def test_build_run_b_report_computes_recoveries_and_accuracies():
    manifest = _manifest_b()
    report = build_run_b_report(
        manifest, _GOLD_B, _TOOL_CORRECT_IDS_B, _TOOL_WRONG_IDS_B, expected_audio_n=5, expected_row_n=3
    )
    assert report.n_samples == 5
    assert report.n_tool_correct == 2
    assert report.n_tool_wrong == 3
    assert report.recoveries_183 == 2  # s3, s5
    assert report.top1_accuracy_183 == pytest.approx(2 / 3)
    assert report.top5_accuracy_183 == pytest.approx(1.0)  # only 3 candidates total, gold always in top-5
    assert report.top1_accuracy_217 == pytest.approx(1.0)  # s1, s2 both correct
    by_id = {p.sample_id: p for p in report.predictions}
    assert by_id["s4"].top1_correct is False
    assert by_id["s3"].top1_correct is True
    # recoveries_183 (2) is far below EMB_OPENS_183_MIN_RECOVERIES (55) --
    # the real registered verdict on this tiny fixture must never claim
    # EMB-OPENS-183 just because the ratio clause alone would pass.
    assert report.verdict != "EMB-OPENS-183"


def test_build_run_b_report_is_idempotent():
    manifest = _manifest_b()
    report1 = build_run_b_report(
        manifest, _GOLD_B, _TOOL_CORRECT_IDS_B, _TOOL_WRONG_IDS_B, expected_audio_n=5, expected_row_n=3
    )
    report2 = build_run_b_report(
        manifest, _GOLD_B, _TOOL_CORRECT_IDS_B, _TOOL_WRONG_IDS_B, expected_audio_n=5, expected_row_n=3
    )
    assert report1 == report2


def test_build_run_b_report_rejects_overlapping_partitions():
    manifest = _manifest_b()
    with pytest.raises(PembReadError, match="overlap"):
        build_run_b_report(
            manifest, _GOLD_B, frozenset({"s1", "s3"}), _TOOL_WRONG_IDS_B, expected_audio_n=5, expected_row_n=3
        )


def test_build_run_b_report_rejects_partition_id_set_mismatch():
    manifest = _manifest_b()
    incomplete_wrong = frozenset({"s3", "s4"})  # missing s5
    with pytest.raises(PembReadError, match="id sets disagree"):
        build_run_b_report(
            manifest, _GOLD_B, _TOOL_CORRECT_IDS_B, incomplete_wrong, expected_audio_n=5, expected_row_n=3
        )


def test_build_run_b_report_rejects_gold_id_mismatch():
    manifest = _manifest_b()
    bad_gold = dict(_GOLD_B)
    del bad_gold["s5"]
    with pytest.raises(PembReadError, match="id sets disagree"):
        build_run_b_report(
            manifest, bad_gold, _TOOL_CORRECT_IDS_B, _TOOL_WRONG_IDS_B, expected_audio_n=5, expected_row_n=3
        )


def test_run_b_report_to_json_and_render_round_trip():
    manifest = _manifest_b()
    report = build_run_b_report(
        manifest, _GOLD_B, _TOOL_CORRECT_IDS_B, _TOOL_WRONG_IDS_B, expected_audio_n=5, expected_row_n=3
    )
    document = run_b_report_to_json(report)
    text = json.dumps(document)
    parsed = json.loads(text)
    assert parsed["recoveries_183"] == 2
    rendered = render_run_b_report(report)
    assert "recoveries=2" in rendered


# ---------------------------------------------------------------------------
# gold_tools_for_run_b.
# ---------------------------------------------------------------------------


def test_gold_tools_for_run_b_reads_the_multiset_as_a_name_set(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    gold = gold_tools_for_run_b(lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root)
    assert gold["tier1_direct:000001"] == frozenset({"setLighting"})
    assert set(gold.keys()) == {"tier1_direct:000001", "tier3_multi_intent:000004", "tier7_multiturn:000009"}


# ---------------------------------------------------------------------------
# resolve_a0_attempt_dir / derive_tool_correct_partition -- the SAME
# consumed-A0 attempt machinery rails.probes.a2t_pop_flight.
# derive_em_correct_ids reads, partitioned differently.
# ---------------------------------------------------------------------------


def _write_headroom(path, *, attempt_dir) -> None:
    document = {
        "schema": "saea-a2t-a0-headroom-v1",
        "attempt_dir": str(attempt_dir),
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "count": 120,
        "sample_ids": ["tier1_direct:000001"],
    }
    path.write_text(json.dumps(document), encoding="utf-8")


def test_resolve_a0_attempt_dir_pins_and_returns_the_attempt(tmp_path):
    attempt_dir = tmp_path / "attempt"
    headroom_path = tmp_path / "headroom.json"
    _write_headroom(headroom_path, attempt_dir=attempt_dir)
    resolved = resolve_a0_attempt_dir(headroom_path)
    assert resolved == attempt_dir


def test_resolve_a0_attempt_dir_refuses_a_drifted_split_hash(tmp_path):
    headroom_path = tmp_path / "headroom.json"
    document = {
        "schema": "saea-a2t-a0-headroom-v1",
        "attempt_dir": "/fake",
        "split_identity_hash": "not-the-pin",
        "count": 1,
        "sample_ids": ["tier1_direct:000001"],
    }
    headroom_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(Exception, match="does not match the pinned"):
        resolve_a0_attempt_dir(headroom_path)


def test_derive_tool_correct_partition_splits_217_183_style(audio2tool_world, tmp_path):
    attempt_dir = tmp_path / "attempt"
    _write_zero_supply_outputs(attempt_dir, audio2tool_world)
    lock = load_lock(audio2tool_world.lock_path)
    correct_ids, wrong_ids = derive_tool_correct_partition(
        attempt_dir,
        lock,
        audio2tool_world.data_root,
        repo_root=audio2tool_world.repo_root,
        expected_correct_n=2,
        expected_wrong_n=1,
    )
    assert correct_ids == frozenset({"tier1_direct:000001", "tier3_multi_intent:000004"})
    assert wrong_ids == frozenset({"tier7_multiturn:000009"})


def test_derive_tool_correct_partition_rejects_wrong_expected_counts(audio2tool_world, tmp_path):
    attempt_dir = tmp_path / "attempt"
    _write_zero_supply_outputs(attempt_dir, audio2tool_world)
    lock = load_lock(audio2tool_world.lock_path)
    with pytest.raises(PembReadError, match="217/400 fail-closed"):
        derive_tool_correct_partition(
            attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )  # default expected_correct_n=217, but only 2 exist here


def test_derive_tool_correct_partition_rejects_wrong_arm_rows(audio2tool_world, tmp_path):
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "arm": "supplied",
        "sample_id": "tier1_direct:000001",
        "messages": [],
        "response_text": "[]",
        "metrics": {},
        "consumption": {},
    }
    (attempt_dir / "outputs.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    lock = load_lock(audio2tool_world.lock_path)
    with pytest.raises(PembReadError, match="zero-supply"):
        derive_tool_correct_partition(
            attempt_dir,
            lock,
            audio2tool_world.data_root,
            repo_root=audio2tool_world.repo_root,
            expected_correct_n=0,
            expected_wrong_n=0,
        )


def test_derive_tool_correct_partition_rejects_malformed_rows(audio2tool_world, tmp_path):
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    (attempt_dir / "outputs.jsonl").write_text("not json\n", encoding="utf-8")
    lock = load_lock(audio2tool_world.lock_path)
    with pytest.raises(PembReadError, match="malformed"):
        derive_tool_correct_partition(
            attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )


def test_derive_tool_correct_partition_rejects_duplicate_rows(audio2tool_world, tmp_path):
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "arm": "zero-supply",
        "sample_id": "tier1_direct:000001",
        "messages": [],
        "response_text": "[]",
        "metrics": {},
        "consumption": {},
    }
    lines = [json.dumps(row), json.dumps(row)]
    (attempt_dir / "outputs.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    lock = load_lock(audio2tool_world.lock_path)
    with pytest.raises(PembReadError, match="duplicate"):
        derive_tool_correct_partition(
            attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )


# ---------------------------------------------------------------------------
# CLI one-shot / idempotence guard.
# ---------------------------------------------------------------------------


def test_refuse_if_already_run_returns_none_when_verdict_exists(tmp_path, capsys):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "verdict.json").write_text("{}", encoding="utf-8")
    result = _refuse_if_already_run(output_dir)
    assert result is None
    assert "REFUSED" in capsys.readouterr().err


def test_refuse_if_already_run_returns_path_when_absent(tmp_path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    result = _refuse_if_already_run(output_dir)
    assert result == output_dir / "verdict.json"
