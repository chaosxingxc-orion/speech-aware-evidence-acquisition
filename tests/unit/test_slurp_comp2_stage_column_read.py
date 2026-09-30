"""COMP-2 offline stage-column read (owner decision 203): tests on FAKES only.

No sealed run, no gold, no scorer subprocess and no data root beyond tmp_path: the registered stage runs
over synthetic delivered answers with a synthetic scope-rule table, and the scorer is injected.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "analysis"))

import slurp_comp2_stage_column_read as C  # noqa: E402
from speech_aware_evidence_acquisition.rails import delivery_normalisers as DN  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response  # noqa: E402


def _answer(entities):
    return json.dumps({"scenario": "calendar", "action": "set",
                       "entities": [{"type": t, "filler": f} for t, f in entities]}, sort_keys=True)


def _table(rows):
    return DN.ScopeRuleTable(rows, sha256="a" * 64, floor=5)


def _row(intent, tp, fp, fn):
    return {"intent": intent, "counts": (float(tp), float(fp), float(fn))}


def test_floor_scales_from_the_1080_anchor():
    assert C.floor_pp(1080) == pytest.approx(1.49)
    assert C.floor_pp(1000) == pytest.approx(1.49 * math.sqrt(1.08))


def test_q2_verdict_legs():
    own = {"point_pp": 1.8, "ci95_pp": [0.4, 3.1]}
    assert C.q2_verdict(own, {"point_pp": 1.2}, 1080)["verdict"] == "PASSES-Q2"
    below = C.q2_verdict({"point_pp": 1.2, "ci95_pp": [0.3, 2.0]}, {"point_pp": 1.2}, 1080)
    assert below["verdict"] == "FAILS-Q2" and below["unmet"] == ["own_point_at_or_above_floor"]
    weak = C.q2_verdict(own, {"point_pp": 0.9}, 1080)
    assert weak["unmet"] == ["replicate_same_sign_at_least_1pp"]
    wide = C.q2_verdict({"point_pp": 1.8, "ci95_pp": [-0.1, 3.1]}, {"point_pp": 1.5}, 1080)
    assert wide["unmet"] == ["own_ci_excludes_zero"]
    flipped = C.q2_verdict(own, {"point_pp": -1.5}, 1080)
    assert "replicate_same_sign_at_least_1pp" in flipped["unmet"]


def test_pooled_counts_and_contrast_point():
    ids = ["a", "b", "c"]
    left = {"a": _row(True, 2, 2, 0), "b": _row(False, 1, 0, 1), "c": _row(True, 0, 2, 0)}
    right = {"a": _row(True, 2, 0, 0), "b": _row(False, 1, 0, 1), "c": _row(True, 0, 0, 0)}
    out = C.contrast(ids, left, right, n_replicates=200)
    expected = 100 * (C.pooled_f1((3, 0, 1)) - C.pooled_f1((3, 4, 1)))
    assert out["slu_f1"]["point_pp"] == pytest.approx(expected, abs=1e-4)
    assert out["intent"]["point_pp"] == 0.0 and out["intent_rows_changed"] == 0


def test_stage_column_drops_only_the_table_phrases_and_proves_the_parse():
    table = _table({"remind me": (10, 1), "tomorrow": (10, 9)})
    texts = {"s1": _answer([("event_name", "remind me"), ("date", "tomorrow")]),
             "s2": _answer([("date", "tomorrow")]),
             "s3": "not an answer"}
    stage = DN.DELIVERY_NORMALISERS.resolve(DN.DELIVER_SCOPE_RULE_V1)
    staged = C.apply_stage(texts, stage, table, parse_slu_response)
    assert staged["s1"]["dropped"] == [0] and staged["s1"]["dropped_types"] == ["event_name"]
    kept = parse_slu_response(staged["s1"]["text"])[2]
    assert [(e.type, e.filler) for e in kept] == [("date", "tomorrow")]
    assert staged["s2"]["dropped"] == [] and staged["s2"]["text"] == texts["s2"]
    assert staged["s3"]["dropped"] == [] and staged["s3"]["text"] == texts["s3"]


def test_write_column_is_complete_and_immutable(tmp_path):
    staged = {"b": {"text": "y"}, "a": {"text": "x"}}
    path = tmp_path / "col.jsonl"
    digest = C.write_column(path, ["a", "b"], staged)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [{"sample_id": "a", "text": "x"}, {"sample_id": "b", "text": "y"}]
    assert C.write_column(path, ["a", "b"], staged) == digest
    with pytest.raises(C.ColumnReadError):
        C.write_column(path, ["a", "b"], {"a": {"text": "z"}, "b": {"text": "y"}})


def test_score_column_uses_the_injected_scorer_and_checks_the_pooled_reproduction(tmp_path):
    per_sample = [{"sample_id": "a", "scenario_action_exact": 1.0, "slu_f1_word_tp": 1, "slu_f1_char_tp": 1,
                   "slu_f1_word_fp": 0, "slu_f1_char_fp": 0, "slu_f1_word_fn": 0, "slu_f1_char_fn": 0}]
    seen = {}

    def fake(**kwargs):
        seen.update(kwargs)
        return {"per_sample": per_sample, "aggregate": {"official": {"slu_f1": 1.0, "intent_accuracy": 1.0}}}

    out = C.score_column({"manifest": tmp_path / "m.json"}, tmp_path / "arm-col.jsonl", "f" * 64, "slurp-slu-official",
                         tmp_path, {}, tmp_path, {"read_id": "X"}, scorer=fake)
    assert out["official"]["slu_f1"] == 1.0 and seen["column_binding"] == {"read_id": "X"}
    bad = lambda **kw: {"per_sample": per_sample, "aggregate": {"official": {"slu_f1": 0.5, "intent_accuracy": 1.0}}}  # noqa: E731
    with pytest.raises(C.ColumnReadError):
        C.score_column({"manifest": tmp_path / "m.json"}, tmp_path / "arm-col.jsonl", "f" * 64, "s", tmp_path, {},
                       tmp_path, {}, scorer=bad)


def test_none_hint_coverage_is_descriptive_and_gold_free():
    ranked = {"r1": ["e1", "e2", "e3", "e4", "e5"], "r2": ["e1", "e6", "e6", "e6", "e6"], "r3": []}
    free = {"e1": True, "e2": True, "e3": True, "e4": False, "e5": False, "e6": False}
    out = C.none_hint_coverage(ranked, free, {"r1": 2, "r2": 0})
    assert out["rows_with_supply"] == 2 and out["rows_triggered"] == 1
    assert out["rows_triggered_with_delivered_entities"] == 1 and out["entities_delivered_on_triggered_rows"] == 2
    assert out["unresolved_exemplar_ids"] == 0


def test_tables_per_scenario_and_entity_class():
    ids = ["a", "b"]
    base = {"a": _row(True, 2, 2, 0), "b": _row(True, 2, 0, 0)}
    edited = {"a": _row(True, 2, 0, 0), "b": _row(True, 2, 0, 0)}
    out = C.per_scenario(ids, {"a": "alarm", "b": "iot"}, base, edited, {"a"})
    assert out["per_scenario"]["alarm"]["rows_edited"] == 1 and out["per_scenario"]["iot"]["delta_pp"] == 0.0
    assert out["equal_scenario_delta_pp"] == pytest.approx(out["per_scenario"]["alarm"]["delta_pp"] / 2, abs=1e-4)
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity
    pred = {"a": (SlotEntity("date", "x"), SlotEntity("time", "y")), "b": ()}
    gold = {"a": (SlotEntity("time", "y"),), "b": ()}
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items
    table = C.per_entity_class(ids, {"a": {"dropped": [0]}, "b": {"dropped": []}}, pred, gold, entity_items)
    assert table == {"date": {"dropped": 1, "spurious": 1}}


def test_countersignature_parse():
    draft = "| 2026-09-29 | RID | model-free-check | x | REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) |"
    signed = "| 2026-09-29 | RID | model-free-check | x | (root countersigned 2026-09-30 by root) |"
    assert C.read_countersigned(draft, "RID") is False
    assert C.read_countersigned(signed, "RID") is True
    assert C.read_countersigned(signed, "OTHER") is None


def test_the_a2_preset_refuses_before_any_score_while_its_read_row_is_a_draft(tmp_path, monkeypatch):
    # A FAKE repo root whose ledger carries the A2 READ row as a DRAFT: the refusal is tested without
    # depending on the live ledger (whose row was countersigned on 2026-09-30).
    fake_repo = tmp_path / "repo"
    (fake_repo / "docs").mkdir(parents=True)
    read_id = C.PRESETS["a2"]["read_id"]
    (fake_repo / C.LEDGER).write_text(
        f"| 2026-09-29 | {read_id} | model-free-check | x | REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) |\n",
        encoding="utf-8")
    monkeypatch.setattr(C, "REPO_ROOT", fake_repo)
    data_root = tmp_path / "data"
    data_root.mkdir()
    args = argparse.Namespace(preset="a2", data_root=str(data_root), lock="unused", none_hint=False, dry_run=False)
    with pytest.raises(C.ColumnReadError, match="REFUSED.*not root countersigned"):
        C.run(args)
    assert not any(data_root.iterdir())
    (fake_repo / C.LEDGER).write_text("", encoding="utf-8")
    with pytest.raises(C.ColumnReadError, match="REFUSED.*missing"):
        C.run(args)
    assert not any(data_root.iterdir())
