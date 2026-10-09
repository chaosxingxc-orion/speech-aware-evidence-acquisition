"""NX programme E2: the node-local Solver column reader, on synthetic sealed records.

No real run exists yet, so the reader is built against records shaped exactly as the E1
instrument seals them (receipt ``saea-supply-variant-arms-v4`` under ``supply_variants``, the first
Solver visit's contacts, one trace pair per contact), with gold given as plain entity tuples.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO = Path(__file__).resolve().parents[2]
for _extra in (_REPO / "scripts" / "analysis",):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import slurp_nx_solver_column_read as reader  # noqa: E402

from speech_aware_evidence_acquisition.rails.supply_variants import (  # noqa: E402
    parse_template_variants,
    supply_variant_arm_record,
    supply_variant_receipt,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity  # noqa: E402

FIT = {
    "slot_tokens": 24576, "completion_ceiling": 640,
    "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120,
}
SECRET = "zanzibar-quokka"  # a filler that must never reach an output


def _answer(*entities, scenario="calendar", action="set"):
    return json.dumps({
        "scenario": scenario, "action": action,
        "entities": [{"type": t, "filler": f} for t, f in entities],
    })


def _group(*, twin=True):
    arms = [
        {"arm_id": "t1", "template_tokens": 400, "instruction_template": {
            "relpath": "configs/probes/nx/t1.txt", "sha256": "a" * 64}},
        {"arm_id": "t2", "template_tokens": 400, "instruction_template": {
            "relpath": "configs/probes/nx/t2.txt", "sha256": "b" * 64}},
    ]
    if twin:
        arms.append({"arm_id": "aa", "replicate_of": "lock"})
    arms.append({"arm_id": "lock", "deliver": True, "template_tokens": 380})
    return parse_template_variants(
        {"node": "solver", "arms": arms, "max_supplied_items": 4, "fit_estimate": dict(FIT)},
        role_kind="solver", phase_id="solver", locked_template="probes/lock.txt",
    )


# Gold and the per-arm answers for six rows over four utterances (two utterances have two rows).
GOLD = {
    "slurp:train:1:a": (("date", "monday"), ("time", "nine")),
    "slurp:train:1:b": (("date", "monday"),),
    "slurp:train:2:a": (),
    "slurp:train:2:b": (),
    "slurp:train:3:a": (("place_name", SECRET),),
    "slurp:train:4:a": (("date", "friday"),),
}
ANSWERS = {
    # the delivering arm: right on 1:a, wrong value on 1:b, falsely fills the empty-gold 2:a,
    # right on 2:b, misses 3:a, unparsed on 4:a.
    "lock": {
        "slurp:train:1:a": _answer(("date", "monday"), ("time", "nine")),
        "slurp:train:1:b": _answer(("date", "tuesday")),
        "slurp:train:2:a": _answer(("date", "monday")),
        "slurp:train:2:b": _answer(),
        "slurp:train:3:a": _answer(),
        "slurp:train:4:a": "I cannot answer that",
    },
    # t1 fixes 1:b, 2:a and 4:a and loses 1:a.
    "t1": {
        "slurp:train:1:a": _answer(("date", "monday")),
        "slurp:train:1:b": _answer(("date", "monday")),
        "slurp:train:2:a": _answer(),
        "slurp:train:2:b": _answer(),
        "slurp:train:3:a": _answer(),
        "slurp:train:4:a": _answer(("date", "friday")),
    },
    # t2 is the delivering arm's twin in all but one row.
    "t2": {
        "slurp:train:1:a": _answer(("date", "monday"), ("time", "nine")),
        "slurp:train:1:b": _answer(("date", "tuesday")),
        "slurp:train:2:a": _answer(("date", "monday")),
        "slurp:train:2:b": _answer(("date", "monday")),
        "slurp:train:3:a": _answer(),
        "slurp:train:4:a": "I cannot answer that",
    },
}
ANSWERS["aa"] = dict(ANSWERS["lock"])


def _gold_map():
    return {sid: {"entities": tuple(SlotEntity(t, f) for t, f in ents)} for sid, ents in GOLD.items()}


def _read(**kwargs):
    return reader.read_columns(
        ANSWERS, _gold_map(), arm_ids=["t1", "t2", "aa", "lock"], delivering="lock", twin="aa",
        draws=300, **kwargs,
    )


# ---------------------------------------------------------------------------
# the arithmetic


def test_wilson_matches_the_textbook_interval_and_handles_the_empty_denominator():
    low, high = reader.wilson(5, 10)
    assert low == pytest.approx(0.2366, abs=1e-3) and high == pytest.approx(0.7634, abs=1e-3)
    assert reader.wilson(0, 0) == (0.0, 1.0)
    low, high = reader.wilson(0, 20)
    assert low == 0.0 and high == pytest.approx(0.1611, abs=1e-3)


def test_the_cluster_is_the_utterance():
    assert reader.utterance_id("slurp:train:1234:abc.flac") == "slurp:train:1234"
    assert reader.utterance_id("slurp:train:7") == "slurp:train:7"


def test_score_answer_separates_exact_missing_wrong_spurious_and_unparsed():
    gold = (SlotEntity("date", "monday"), SlotEntity("time", "nine"))
    exact = reader.score_answer(_answer(("date", "monday"), ("time", "nine")), gold)
    assert exact["parsed"] and exact["exact_set"] and exact["nonempty_exact"] is True
    assert exact["false_fill"] is None
    missing = reader.score_answer(_answer(("date", "monday")), gold)
    assert not missing["exact_set"] and missing["by_type"]["time"]["gold_missing"] == 1
    assert missing["by_type"]["date"]["gold_exact"] == 1
    wrong = reader.score_answer(_answer(("date", "tuesday"), ("time", "nine")), gold)
    assert not wrong["exact_set"] and wrong["by_type"]["date"]["gold_wrong"] == 1
    spurious = reader.score_answer(
        _answer(("date", "monday"), ("time", "nine"), ("place_name", "x")), gold)
    assert not spurious["exact_set"] and spurious["by_type"]["place_name"]["spurious"] == 1
    unparsed = reader.score_answer("no json here", gold)
    assert not unparsed["parsed"] and not unparsed["exact_set"] and unparsed["n_pred"] == 0
    assert unparsed["by_type"]["time"]["gold_missing"] == 1


def test_empty_gold_rows_score_false_fill_and_never_nonempty_exact():
    filled = reader.score_answer(_answer(("date", "monday")), ())
    assert filled["false_fill"] is True and filled["nonempty_exact"] is None
    assert not filled["exact_set"]
    clean = reader.score_answer(_answer(), ())
    assert clean["false_fill"] is False and clean["exact_set"] is True
    unparsed = reader.score_answer("???", ())
    assert unparsed["false_fill"] is False and not unparsed["exact_set"]


# ---------------------------------------------------------------------------
# the column read


def test_the_paired_counts_are_exact():
    report = _read()
    t1 = report["arms"]["t1"]["paired_vs_delivering"]
    # exact_set over six rows: lock right on 1:a, 2:b; t1 right on 1:b, 2:a, 2:b, 4:a
    # (and 3:a is wrong for both: both miss the gold place entity).
    exact = t1["exact_set"]
    assert exact["n"] == 6
    assert (exact["b_arm_only"], exact["c_delivering_only"]) == (3, 1)
    assert exact["rate_arm"] == pytest.approx(4 / 6) and exact["rate_delivering"] == pytest.approx(2 / 6)
    assert exact["diff_pp"] == pytest.approx(100.0 * 2 / 6)
    assert exact["discordant_share"] == pytest.approx(3 / 4)
    low, high = exact["wilson95"]
    assert low < 0.75 < high
    assert t1["parse_valid"]["b_arm_only"] == 1 and t1["parse_valid"]["c_delivering_only"] == 0
    # empty-gold rows: lock falsely fills 2:a, t1 does not
    fill = t1["empty_gold_false_fill"]
    assert fill["n"] == 2 and fill["rate_delivering"] == pytest.approx(0.5)
    assert fill["rate_arm"] == pytest.approx(0.0) and fill["diff_pp"] == pytest.approx(-50.0)
    # non-empty rows (4): lock exact on 1:a only; t1 exact on 1:b and 4:a
    nonempty = t1["nonempty_exact"]
    assert nonempty["n"] == 4 and (nonempty["b_arm_only"], nonempty["c_delivering_only"]) == (2, 1)


def test_the_twin_arm_has_a_zero_difference_and_the_delivering_arm_has_no_paired_block():
    report = _read()
    assert report["arms"]["lock"]["paired_vs_delivering"] == {}
    assert report["arms"]["lock"]["role"] == "delivering"
    assert report["arms"]["aa"]["role"] == "twin"
    for metric in ("exact_set", "parse_valid", "empty_gold_false_fill", "nonempty_exact"):
        cell = report["arms"]["aa"]["paired_vs_delivering"][metric]
        assert cell["diff_pp"] == 0.0 and cell["ci95_pp"] == [0.0, 0.0]
        assert cell["b_arm_only"] == cell["c_delivering_only"] == 0
        assert cell["discordant_share"] is None and cell["wilson95"] is None


def test_the_bootstrap_is_whole_utterance_seeded_and_reproducible():
    first, second = _read(), _read()
    assert first == second
    assert first["bootstrap"] == {
        "draws": 300, "seed": 20260915, "ci_level": 0.95,
        "cluster": "whole utterance (first three colon segments of the sample id)",
    }
    ci = first["arms"]["t1"]["paired_vs_delivering"]["exact_set"]["ci95_pp"]
    point = first["arms"]["t1"]["paired_vs_delivering"]["exact_set"]["diff_pp"]
    assert ci[0] <= point <= ci[1]
    # a different seed moves the interval but never the paired counts
    other = reader.read_columns(
        ANSWERS, _gold_map(), arm_ids=["t1", "t2", "aa", "lock"], delivering="lock", twin="aa",
        draws=300, seed=1,
    )
    assert other["arms"]["t1"]["paired_vs_delivering"]["exact_set"]["ci95_pp"] != ci
    assert other["arms"]["t1"]["paired_vs_delivering"]["exact_set"]["b_arm_only"] == 3


def test_the_default_bootstrap_is_the_programmes_ten_thousand_draws_seed_20260915():
    assert (reader.DRAWS, reader.SEED) == (10_000, 20260915)


def test_the_mechanical_screen_marks_only_the_candidates():
    screen = _read()["mechanical_screen"]
    assert set(screen) == {"t1", "t2"}  # not the twin, not the delivering arm
    assert screen["t2"]["primary_ci_lb_gt_0"] is False


def test_the_per_slot_type_table_counts_gold_and_predicted_items():
    arms = _read()["arms"]
    lock = arms["lock"]["by_slot_type"]
    # date gold: 1:a exact, 1:b wrong value, 4:a missing (unparsed); predicted: 1:a, 1:b, and the
    # spurious fill on the empty-gold row 2:a.
    assert lock["date"] == {
        "gold_items": 3, "gold_exact": 1, "gold_missing": 1, "gold_wrong": 1, "pred_items": 3,
        "spurious": 1,
    }
    assert lock["time"]["gold_items"] == 1 and lock["time"]["gold_exact"] == 1
    assert lock["place_name"]["gold_missing"] == 1
    assert arms["lock"]["predicted_items"] == 4


def test_a_row_set_that_differs_between_arms_is_refused():
    broken = copy.deepcopy(ANSWERS)
    del broken["t1"]["slurp:train:4:a"]
    with pytest.raises(reader.ColumnReadError, match="does not cover"):
        reader.read_columns(broken, _gold_map(), arm_ids=["t1", "lock"], delivering="lock", draws=50)


def test_a_missing_gold_row_is_refused():
    gold = _gold_map()
    del gold["slurp:train:3:a"]
    with pytest.raises(reader.ColumnReadError, match="absent from the gold"):
        reader.read_columns(ANSWERS, gold, arm_ids=["t1", "lock"], delivering="lock", draws=50)


def test_the_outputs_carry_no_filler_text():
    report = _read()
    text = json.dumps(report) + reader.render(report)
    assert SECRET not in text
    for filler in ("monday", "tuesday", "friday", "nine"):
        assert filler not in text


def test_the_table_renders_every_arm_and_metric():
    report = _read()
    table = reader.render(report)
    for fragment in ("| t1 |", "| aa |", "| lock |", "exact_set", "empty_gold_false_fill",
                     "Wilson95", "Mechanical screen", "## Per slot type (t1)"):
        assert fragment in table


# ---------------------------------------------------------------------------
# the sealed side: records shaped as E1 seals them


def _sealed(*, twin=True, revisions=1, rows=None):
    group = _group(twin=twin)
    arm_ids = group.arm_ids
    outputs, trace = [], {}
    for sid in (rows or sorted(GOLD)):
        contacts = []
        for index, arm_id in enumerate(arm_ids):
            rid = f"{sid}/{arm_id}"
            raw = ANSWERS[arm_id][sid]
            contact = {
                "agent_contact_id": f"solver:{sid}:{index}", "request_id": rid,
                "request_sha256": hashlib.sha256(rid.encode()).hexdigest(),
                "response_sha256": hashlib.sha256(("envelope" + rid).encode()).hexdigest(),
                "response_text_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            }
            contacts.append(contact)
            trace[rid + "/request"] = {"payload_sha256": contact["request_sha256"]}
            trace[rid + "/response"] = {
                "text": raw, "response_text_sha256": contact["response_text_sha256"],
            }
        records = [
            supply_variant_arm_record(
                arm=arm, arm_index=i, contact_id=contacts[i]["agent_contact_id"],
                supplied_value_ids=("v:1",), template_group=True,
            )
            for i, arm in enumerate(group.arms)
        ]
        receipt = supply_variant_receipt(group=group, phase_id="solver", records=records)
        visits = [{"role_id": "perception", "stage": "perception", "execution_receipt": {
            "contacts": [], "final_contact": None}},
            {"role_id": "solver", "stage": "solver", "execution_receipt": {
                "contacts": contacts, "final_contact": contacts[-1]}}]
        outputs.append({"sample_id": sid, "supply_variants": receipt,
                        "native_episode_receipt": {"role_visits": visits}})
    return outputs, trace


def test_the_loader_recovers_every_arms_raw_first_answer_in_declared_order():
    outputs, trace = _sealed()
    sealed = reader.load_sealed_arm_texts(outputs, trace)
    assert sealed["arm_ids"] == ("t1", "t2", "aa", "lock")
    assert sealed["delivering"] == "lock" and sealed["twin"] == "aa"
    assert sealed["templates"] == [
        {"relpath": "probes/nx/t1.txt", "sha256": "a" * 64},
        {"relpath": "probes/nx/t2.txt", "sha256": "b" * 64}, None, None,
    ]
    assert sealed["texts"]["t1"] == ANSWERS["t1"] and sealed["texts"]["lock"] == ANSWERS["lock"]
    assert sealed["rows_without_solver_visit"] == []
    report = reader.read_columns(
        sealed["texts"], _gold_map(), arm_ids=sealed["arm_ids"], delivering=sealed["delivering"],
        twin=sealed["twin"], draws=100,
    )
    assert report["arms"]["t1"]["paired_vs_delivering"]["exact_set"]["b_arm_only"] == 3


def test_a_group_without_a_twin_is_read():
    outputs, trace = _sealed(twin=False)
    sealed = reader.load_sealed_arm_texts(outputs, trace)
    assert sealed["arm_ids"] == ("t1", "t2", "lock") and sealed["twin"] is None


def test_a_row_with_no_solver_visit_is_skipped_and_counted():
    outputs, trace = _sealed()
    outputs.append({
        "sample_id": "slurp:train:9:a", "supply_variants": None,
        "native_episode_receipt": {"role_visits": [{"role_id": "perception", "stage": "perception"}]},
    })
    sealed = reader.load_sealed_arm_texts(outputs, trace)
    assert sealed["rows_without_solver_visit"] == ["slurp:train:9:a"]
    assert "slurp:train:9:a" not in sealed["texts"]["lock"]


def test_a_solver_visit_without_custody_is_refused():
    outputs, trace = _sealed()
    outputs[0]["supply_variants"] = None
    with pytest.raises(reader.ColumnReadError, match="sealed no template-variant custody"):
        reader.load_sealed_arm_texts(outputs, trace)


def test_a_supply_kind_receipt_is_not_a_template_column():
    outputs, trace = _sealed()
    outputs[0]["supply_variants"] = dict(outputs[0]["supply_variants"], schema="saea-supply-variant-arms-v3")
    with pytest.raises(reader.ColumnReadError, match="reads template columns only"):
        reader.load_sealed_arm_texts(outputs, trace)


def test_an_arm_group_that_differs_between_rows_is_refused():
    outputs, trace = _sealed()
    other, _ = _sealed(twin=False, rows=["slurp:train:1:a"])
    outputs[1] = dict(outputs[1], supply_variants=other[0]["supply_variants"])
    with pytest.raises(reader.ColumnReadError, match="differ from the first row's"):
        reader.load_sealed_arm_texts(outputs, trace)


def test_a_template_pin_that_differs_between_rows_is_refused():
    outputs, trace = _sealed()
    outputs[1]["supply_variants"]["arms"][0]["instruction_template"]["sha256"] = "c" * 64
    with pytest.raises(reader.ColumnReadError, match="differ from the first row's"):
        reader.load_sealed_arm_texts(outputs, trace)


def test_a_first_visit_that_is_not_the_full_arm_group_is_refused():
    outputs, trace = _sealed()
    visit = outputs[0]["native_episode_receipt"]["role_visits"][1]
    visit["execution_receipt"]["contacts"] = visit["execution_receipt"]["contacts"][:-1]
    with pytest.raises(reader.ColumnReadError, match="not the full arm group"):
        reader.load_sealed_arm_texts(outputs, trace)


def test_a_trace_text_that_differs_from_the_sealed_contact_is_refused():
    outputs, trace = _sealed()
    key = next(k for k in trace if k.endswith("/t1/response"))
    trace[key] = dict(trace[key], text="tampered")
    with pytest.raises(reader.ColumnReadError, match="trace differs"):
        reader.load_sealed_arm_texts(outputs, trace)


def test_a_missing_trace_pair_is_refused():
    outputs, trace = _sealed()
    del trace[next(k for k in trace if k.endswith("/t2/request"))]
    with pytest.raises(reader.ColumnReadError, match="no trace pair"):
        reader.load_sealed_arm_texts(outputs, trace)


def test_a_contact_named_by_another_arm_is_refused():
    outputs, trace = _sealed()
    outputs[0]["supply_variants"]["arms"][0]["contact_id"] = "solver:elsewhere"
    with pytest.raises(reader.ColumnReadError):
        reader.load_sealed_arm_texts(outputs, trace)


def test_an_empty_run_is_refused():
    with pytest.raises(reader.ColumnReadError, match="no row of the run"):
        reader.load_sealed_arm_texts([], {})


def test_the_test_split_is_never_read():
    with pytest.raises(reader.ColumnReadError, match="test split is closed"):
        reader.load_gold(None, Path("."), "test")


def test_main_writes_the_report_and_tables_without_text(tmp_path, monkeypatch, capsys):
    outputs, trace = _sealed()
    sealed = reader.load_sealed_arm_texts(outputs, trace)
    report = reader.read_columns(
        sealed["texts"], _gold_map(), arm_ids=sealed["arm_ids"], delivering=sealed["delivering"],
        twin=sealed["twin"], draws=100,
    )
    report["inputs"] = {"run_id": "R", "attempt_id": "A", "split": "train"}
    monkeypatch.setattr(reader, "build", lambda args: report)
    code = reader.main([
        "--data-root", str(tmp_path), "--run-id", "R", "--attempt-id", "A", "--split", "train",
        "--out-dir", str(tmp_path / "out"),
    ])
    assert code == 0
    written = json.loads((tmp_path / "out" / "report.json").read_text(encoding="utf-8"))
    assert written["arm_order"] == ["t1", "t2", "aa", "lock"]
    assert SECRET not in (tmp_path / "out" / "tables.md").read_text(encoding="utf-8")
    assert "wrote" in capsys.readouterr().out
    _ = SimpleNamespace
