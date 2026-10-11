"""The 266-E reader (scripts/analysis/slurp_direct_fold_b_core_read.py) on synthetic fixtures: no sealed run, no model, no network.

Synthetic arms carry per-sample SLU counts, an intent flag, delivered text and a trace; the tests check the contrast arithmetic, the twin offset, the
per-scenario table, the preregistered verdict words, the answer-length / cost tables and the reasoning-leak guard count, and that no delivered or
reasoning text ever reaches an artifact.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "flights" / "direct"))
_spec = importlib.util.spec_from_file_location("slurp_direct_fold_b_core_read", REPO / "scripts" / "analysis" / "slurp_direct_fold_b_core_read.py")
reader = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = reader
_spec.loader.exec_module(reader)

import direct_fb_family as fam  # noqa: E402

SECRET = "the quick brown fox SECRET-UTTERANCE"
IDS = [f"slurp:train:{i:06d}:audio-{i}" for i in range(24)]
SCENARIOS = ["alarm", "weather", "music"]


def scenario_of(sid: str) -> str:
    return SCENARIOS[int(sid.split(":")[2]) % 3]


def cluster_of(sid: str) -> str:
    return "u" + sid.split(":")[2]


def row(tp: int, fp: int, fn: int, intent: int, parsed: int = 1) -> dict:
    return {"slu_f1_word_tp": float(tp), "slu_f1_char_tp": float(tp), "slu_f1_word_fp": float(fp), "slu_f1_char_fp": float(fp),
            "slu_f1_word_fn": float(fn), "slu_f1_char_fn": float(fn), "scenario_action_exact": float(intent), "parsed": float(parsed)}


def arm(tp: int, fp: int, fn: int, intent: int = 1) -> dict:
    return {sid: row(tp, fp, fn, intent) for sid in IDS}


def test_percentile_and_interval_arithmetic():
    assert reader.percentile([1, 2, 3, 4], 50) == 2.5 and reader.percentile([], 50) != reader.percentile([], 50)
    block = reader.interval([0.0, 0.1, 0.2, 0.3, 0.4], 0.2)
    assert block["point_pp"] == pytest.approx(20.0) and block["ci95_lo_pp"] < block["point_pp"] < block["ci95_hi_pp"]


def test_contrast_delta_is_thinking_minus_the_mean_of_the_two_instruct_passes_and_the_offset_is_replicate_minus_instruct():
    arms = {"instruct": arm(8, 2, 2), "replicate": arm(7, 3, 3), "thinking": arm(9, 1, 1)}
    out = reader.paired_contrasts(arms, IDS, cluster_of, seed=1, draws=200)
    f = lambda tp, fp, fn: 2 * tp / (2 * tp + fp + fn)  # noqa: E731
    assert out["slu_f1"]["instruct_pct"] == pytest.approx(100 * f(8, 2, 2)) and out["slu_f1"]["thinking_pct"] == pytest.approx(100 * f(9, 1, 1))
    assert out["slu_f1"]["delta_thinking_vs_mean_instruct"]["point_pp"] == pytest.approx(100 * (f(9, 1, 1) - 0.5 * (f(8, 2, 2) + f(7, 3, 3))))
    assert out["slu_f1"]["twin_offset_replicate_minus_instruct"]["point_pp"] == pytest.approx(100 * (f(7, 3, 3) - f(8, 2, 2)))
    assert out["n"] == 24


def test_intent_contrast_and_saves_harms_ties():
    inst = {sid: row(1, 0, 0, 1 if i < 12 else 0) for i, sid in enumerate(IDS)}
    rep = {sid: row(1, 0, 0, 1 if i < 12 else 0) for i, sid in enumerate(IDS)}
    think = {sid: row(1, 0, 0, 1 if i < 18 else 0) for i, sid in enumerate(IDS)}
    out = reader.paired_contrasts({"instruct": inst, "replicate": rep, "thinking": think}, IDS, cluster_of, seed=2, draws=100)["intent"]
    assert out["delta_thinking_vs_mean_instruct"]["point_pp"] == pytest.approx(25.0)
    assert out["saves_harms_ties"]["thinking_vs_instruct"] == {"saves": 6, "harms": 0, "ties": 18}
    assert out["saves_harms_ties"]["replicate_vs_instruct"] == {"saves": 0, "harms": 0, "ties": 24}


def test_per_scenario_table_has_natural_and_equal_weightings():
    def unequal(sid: str) -> str:                       # 16 alarm rows and 8 music rows: the natural mixture and the equal weighting differ
        return "alarm" if int(sid.split(":")[2]) < 16 else "music"

    think = arm(9, 1, 1)
    for sid in IDS:
        if unequal(sid) == "music":
            think[sid] = row(5, 5, 5, 0)
    arms = {"instruct": arm(8, 2, 2), "replicate": arm(8, 2, 2), "thinking": think}
    table = reader.per_scenario_table(arms, IDS, unequal)
    assert set(table["scenarios"]) == {"alarm", "music"} and (table["scenarios"]["alarm"]["n"], table["scenarios"]["music"]["n"]) == (16, 8)
    assert table["scenarios"]["music"]["slu_delta_pp"] < 0 < table["scenarios"]["alarm"]["slu_delta_pp"]
    expected_equal = sum(e["slu_delta_pp"] for e in table["scenarios"].values()) / 2
    assert table["equal_scenario"]["slu_delta_pp"] == pytest.approx(expected_equal)
    assert table["natural_mixture"]["slu_delta_pp"] != pytest.approx(expected_equal)
    assert table["natural_mixture"]["slu_delta_pp"] > table["equal_scenario"]["slu_delta_pp"]     # the larger good scenario weighs more


@pytest.mark.parametrize("delta,lo,hi,offset,leaks,word", [
    (3.0, 1.0, 5.0, 0.4, 0, "RESOLVED-ABOVE-BAR"),
    (3.0, 0.2, 5.0, 0.4, 0, "NOT RESOLVED"),          # the lower bound does not clear the twin offset
    (2.4, 1.0, 4.0, 0.0, 0, "NOT RESOLVED"),          # under the bar
    (3.0, 1.0, 5.0, 0.4, 1, "NOT RESOLVED"),          # a reasoning leak voids the resolution
    (-3.0, -5.0, -1.0, 0.4, 0, "HARM"),
    (-3.0, -5.0, 0.2, 0.4, 0, "NOT RESOLVED"),
    (0.1, -1.0, 1.2, 0.3, 0, "NOT RESOLVED"),
])
def test_verdict_words(delta, lo, hi, offset, leaks, word):
    assert reader.verdict(delta, lo, hi, offset, leaks) == word and word in reader.VERDICT_WORDS


def test_answer_length_cap_hits_and_cost_projection():
    costs = [{"completion_tokens": t, "prompt_tokens": 2300, "latency_seconds": 4.0} for t in (100, 200, 300, 2048)]
    table = reader.answer_length_table(costs, cap=2048)
    assert table["cap_hits"] == 1 and table["n"] == 4 and table["completion_tokens"]["max"] == 2048 and table["completion_tokens"]["p50"] == 250
    cost = reader.cost_table(costs, rows=1080, slots=4)
    assert cost["seconds_per_contact"]["mean"] == 4.0 and cost["projection_gpu_hours"] == pytest.approx(1080 * 4.0 / 4 / 3600)


def test_the_reader_cap_is_the_amended_family_cap():
    """The cap-hit table counts completion tokens against the amended 8,192 cap (2,048 before the 2026-10-11 decode-cost sign-off)."""

    assert reader.THINKING_CAP == fam.THINK_MAX_TOKENS == 8192


def test_empty_completion_receipts_are_counted_from_the_trace_without_text(tmp_path):
    lines = [
        {"channel": "TOOL", "record_id": "c-direct-a/empty-completion", "payload": {
            "schema": "saea-empty-completion-v1", "cap_hit": True, "completion_tokens": 8192, "finish_reason": "length", "max_tokens": 8192}},
        {"channel": "TOOL", "record_id": "c-direct-b/empty-completion", "payload": {
            "schema": "saea-empty-completion-v1", "cap_hit": False, "completion_tokens": 40, "finish_reason": "stop", "max_tokens": 8192}},
        {"channel": "TOOL", "record_id": "x/native-completion", "payload": {"schema": "saea-native-completion-v1"}},
        {"channel": "COST", "record_id": "r/cost", "payload": {"completion_tokens": 8192}},
    ]
    path = tmp_path / "trace.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in lines) + "\n", encoding="utf-8")
    receipts = reader.load_trace_empty_receipts(path)
    assert reader.receipt_table(receipts) == {"n": 2, "cap_hit": 1, "finish_reasons": {"length": 1, "stop": 1}}
    smoke = reader.smoke_stage([{"completion_tokens": 8192, "prompt_tokens": 2300, "latency_seconds": 5.0}], {}, receipts=receipts)
    assert smoke["empty_completion_receipts"]["cap_hit"] == 1 and smoke["answer_length"]["cap_hits"] == 1


def test_text_flags_count_empty_no_object_and_reasoning_leaks_without_keeping_text():
    assert reader.text_flags("") == {"empty": True, "no_object": True, "leak": False}
    assert reader.text_flags('{"a": 1}') == {"empty": False, "no_object": False, "leak": False}
    assert reader.text_flags("<think>hmm</think>{}")["leak"] is True
    counts = reader.flag_counts({"a": reader.text_flags(""), "b": reader.text_flags("x"), "c": reader.text_flags("</think>{}")})
    assert counts == {"rows": 3, "empty_content": 1, "no_json_object": 2, "reasoning_leak": 1}


def _write_run(root: Path, key: str, *, outputs: list[dict], costs: list[dict], per_sample: list[dict] | None, status: str = "COMPLETED") -> None:
    spec = fam.CELLS[key]
    run_dir = root / "runs" / spec["run"] / spec["attempt"]
    run_dir.mkdir(parents=True)
    (run_dir / f"{spec['run']}.outputs.jsonl").write_text("\n".join(json.dumps(o) for o in outputs) + "\n", encoding="utf-8")
    trace = [{"channel": "MODEL_RESPONSE", "record_id": f"flight-{i}/response", "payload": {"text": SECRET, "usage": {"completion_tokens": c["completion_tokens"]}}}
             for i, c in enumerate(costs)]
    trace += [{"channel": "COST", "record_id": f"flight-{i}/cost", "payload": dict(c, calls=1, audio_seconds=2.0)} for i, c in enumerate(costs)]
    (run_dir / f"{spec['run']}.trace.jsonl").write_text("\n".join(json.dumps(r) for r in trace) + "\n", encoding="utf-8")
    if per_sample is not None:
        (run_dir / f"{spec['run']}.run-manifest.json").write_text(json.dumps({"status": status}), encoding="utf-8")
        (run_dir / f"{spec['run']}.scores.json").write_text(json.dumps({reader.SCORER: {"aggregate": {}, "per_sample": per_sample}}), encoding="utf-8")


def test_smoke_stage_end_to_end_on_a_synthetic_run_never_persists_text(tmp_path):
    costs = [{"completion_tokens": t, "prompt_tokens": 2300, "latency_seconds": 5.0} for t in (300, 500, 700, reader.THINKING_CAP)]
    smoke_ids = [i["sample_id"] for i in fam.roster_doc("smoke")["items"]]
    outputs = [{"sample_id": sid, "text": f'{{"x": "{SECRET}"}}', "request_sha256": "a"} for sid in smoke_ids[:3]] + [{"sample_id": smoke_ids[3], "text": f"<think>{SECRET}</think>"}]
    _write_run(tmp_path, "smoke", outputs=outputs, costs=costs, per_sample=None)
    code = reader.main(["--stage", "smoke", "--data-root", str(tmp_path), "--repo-root", str(REPO), "--analysis-root", str(tmp_path / "out")])
    assert code == 0
    result = json.loads((tmp_path / "out" / "smoke-decode-cost.json").read_text(encoding="utf-8"))
    assert result["delivered_content"]["reasoning_leak"] == 1 and result["answer_length"]["cap_hits"] == 1
    assert result["cost"]["projection_gpu_hours"] > 0 and result["contacts"]["model"] == 0
    for artifact in (tmp_path / "out").iterdir():
        assert SECRET not in artifact.read_text(encoding="utf-8")


def test_read_stage_end_to_end_resolves_a_clear_thinking_gain_and_stays_text_free(tmp_path):
    roster = fam.roster_doc("arm")
    ids = [i["sample_id"] for i in roster["items"]]

    def per_sample(tp, fp, fn, intent):
        return [dict(row(tp, fp, fn, intent), sample_id=sid) for sid in ids]

    for key, counts in (("instruct", (8, 2, 2, 1)), ("replicate", (8, 2, 2, 1)), ("thinking", (9, 1, 1, 1))):
        outputs = [{"sample_id": sid, "text": f'{{"s": "{SECRET}"}}'} for sid in ids]
        costs = [{"completion_tokens": 40, "prompt_tokens": 2300, "latency_seconds": 1.0} for _ in ids]
        _write_run(tmp_path, key, outputs=outputs, costs=costs, per_sample=per_sample(*counts))
    code = reader.main(["--stage", "read", "--data-root", str(tmp_path), "--repo-root", str(REPO), "--analysis-root", str(tmp_path / "out"), "--draws", "200"])
    assert code == 0
    result = json.loads((tmp_path / "out" / "read.json").read_text(encoding="utf-8"))
    assert result["verdict"] == "RESOLVED-ABOVE-BAR" and result["reasoning_leak_total"] == 0
    assert set(result["delivered_content"]) == {"instruct", "replicate", "thinking"} and result["scorer_parse_failures"] == {"instruct": 0, "replicate": 0, "thinking": 0}
    assert len(result["per_scenario"]["scenarios"]) == len({i["stratum"] for i in roster["items"]})
    for artifact in (tmp_path / "out").iterdir():
        assert SECRET not in artifact.read_text(encoding="utf-8")


def test_read_stage_refuses_an_incomplete_manifest_and_a_wrong_id_set(tmp_path):
    ids = [i["sample_id"] for i in fam.roster_doc("arm")["items"]]
    for key in fam.ARM_KEYS:
        status = "FAILED" if key == "thinking" else "COMPLETED"
        _write_run(tmp_path, key, outputs=[{"sample_id": ids[0], "text": "{}"}], costs=[{"completion_tokens": 1, "prompt_tokens": 1, "latency_seconds": 1.0}],
                   per_sample=[dict(row(1, 0, 0, 1), sample_id=ids[0])], status=status)
    assert reader.main(["--stage", "read", "--data-root", str(tmp_path), "--repo-root", str(REPO), "--analysis-root", str(tmp_path / "out")]) == 2
    other = tmp_path / "second"
    for key in fam.ARM_KEYS:
        _write_run(other, key, outputs=[{"sample_id": ids[0], "text": "{}"}], costs=[], per_sample=[dict(row(1, 0, 0, 1), sample_id=ids[0])])
    assert reader.main(["--stage", "read", "--data-root", str(other), "--repo-root", str(REPO), "--analysis-root", str(other / "out")]) == 2


def test_rows_table_refuses_a_text_field():
    with pytest.raises(reader.ReadError, match="is text"):
        reader.rows_table({reader.SCORER: {"per_sample": [{"sample_id": "a", "slu_f1_f1": 1.0, "answer": "words"}]}}, reader.SCORER)
