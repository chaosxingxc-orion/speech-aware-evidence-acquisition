"""NX programme E2 for the Perception node: the node-local Perception column reader, on synthetic
sealed records.

No real run exists yet, so the reader is built against records shaped exactly as the Perception
template instrument seals them (receipt ``saea-perception-branch-arms-v4`` under
``native_episode_receipt.perception_branches``, level 2, the Perception and Solver visits' contacts,
one trace pair per contact), with gold given as plain intent ids and entity tuples.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
for _extra in (_REPO / "scripts" / "analysis",):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import slurp_nx_perception_column_read as reader  # noqa: E402

from speech_aware_evidence_acquisition.rails.native_episode_receipt import (  # noqa: E402
    parse_perception_branch_note,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (  # noqa: E402
    parse_perception_template_variants,
    perception_branch_receipt,
    perception_branch_record,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity  # noqa: E402

FIT = {
    "slot_tokens": 24576, "completion_ceiling": 640,
    "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120,
}
SECRET = "zanzibar-quokka"  # a value that must never reach an output
ARMS = ("p1", "p2", "aa", "lock")


def _group():
    return parse_perception_template_variants(
        {
            "node": "perception", "max_supplied_items": 4, "fit_estimate": dict(FIT),
            "arms": [
                {"arm_id": "p1", "template_tokens": 400, "instruction_template": {
                    "relpath": "configs/probes/nx/p1.txt", "sha256": "a" * 64}},
                {"arm_id": "p2", "template_tokens": 400, "instruction_template": {
                    "relpath": "configs/probes/nx/p2.txt", "sha256": "b" * 64}},
                {"arm_id": "aa", "replicate_of": "lock"},
                {"arm_id": "lock", "deliver": True, "template_tokens": 380},
            ],
        },
        phase_id="perception", locked_template="probes/lock.txt",
    )


def _answer(*entities, scenario="calendar", action="set"):
    return json.dumps({
        "scenario": scenario, "action": action,
        "entities": [{"type": t, "filler": f} for t, f in entities],
    })


def _note(intents, presence=None, heard=None):
    document = {"candidates": [{"intent_id": i} for i in intents]}
    if presence is not None:
        document["entity_presence"] = presence
    if heard is not None:
        document["heard_values"] = heard
    return json.dumps(document)


# Gold for six rows over four utterances (two utterances have two rows): intent and entities.
GOLD = {
    "slurp:train:1:a": ("calendar_set", (("date", "monday"), ("time", "nine"))),
    "slurp:train:1:b": ("calendar_set", (("date", "monday"),)),
    "slurp:train:2:a": ("alarm_query", ()),
    "slurp:train:2:b": ("alarm_query", ()),
    "slurp:train:3:a": ("play_music", (("place_name", SECRET),)),
    "slurp:train:4:a": ("calendar_set", (("date", "friday"),)),
}
# Per arm: (candidate intents, entity_presence, heard_values, prompt_tokens)
NOTES = {
    "lock": {
        "slurp:train:1:a": (["calendar_set", "alarm_set"], None, None, 1000),
        "slurp:train:1:b": (["alarm_set", "calendar_set"], None, None, 1000),
        "slurp:train:2:a": (["alarm_query"], None, None, 1000),
        "slurp:train:2:b": (["alarm_set"], None, None, 1000),
        "slurp:train:3:a": (["play_music"], None, None, 1000),
        "slurp:train:4:a": ([], None, None, 1000),
    },
    # p1 carries the presence verdict: right "none" on 2:a, wrong "none" on 3:a, "unsure" on 2:b,
    # "present" on the rest, and a wider list on 1:b.
    "p1": {
        "slurp:train:1:a": (["calendar_set"], "present", 2, 1400),
        "slurp:train:1:b": (["calendar_set", "alarm_set"], "present", 1, 1400),
        "slurp:train:2:a": (["alarm_query"], "none", 0, 1400),
        "slurp:train:2:b": (["alarm_query"], "unsure", 0, 1400),
        "slurp:train:3:a": (["play_music"], "none", 0, 1400),
        "slurp:train:4:a": (["calendar_set"], "present", 1, 1400),
    },
    "p2": {sid: (c, "maybe", None, 1200) for sid, (c, _p, _h, _t) in {
        "slurp:train:1:a": (["calendar_set"], 0, 0, 0),
        "slurp:train:1:b": (["calendar_set"], 0, 0, 0),
        "slurp:train:2:a": (["alarm_query"], 0, 0, 0),
        "slurp:train:2:b": (["alarm_query"], 0, 0, 0),
        "slurp:train:3:a": (["play_music"], 0, 0, 0),
        "slurp:train:4:a": (["calendar_set"], 0, 0, 0),
    }.items()},
}
NOTES["aa"] = {sid: tuple(v) for sid, v in NOTES["lock"].items()}

SOLVER = {
    "lock": {
        "slurp:train:1:a": _answer(("date", "monday"), ("time", "nine")),
        "slurp:train:1:b": _answer(("date", "tuesday")),
        "slurp:train:2:a": _answer(("date", "monday")),
        "slurp:train:2:b": _answer(),
        "slurp:train:3:a": _answer(),
        "slurp:train:4:a": "I cannot answer that",
    },
    "p1": {
        "slurp:train:1:a": _answer(("date", "monday")),
        "slurp:train:1:b": _answer(("date", "monday")),
        "slurp:train:2:a": _answer(),
        "slurp:train:2:b": _answer(),
        "slurp:train:3:a": _answer(),
        "slurp:train:4:a": _answer(("date", "friday")),
    },
}
SOLVER["p2"] = dict(SOLVER["lock"])
SOLVER["aa"] = dict(SOLVER["lock"])


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sealed():
    """Outputs rows and trace records as the instrument seals them."""

    group = _group()
    rows, trace = [], {}
    for sid in GOLD:
        records, perception_contacts, solver_contacts = [], [], []
        for index, branch in enumerate(group.branches):
            intents, presence, heard, tokens = NOTES[branch.branch_id][sid]
            note = _note(intents, presence, heard)
            answer = SOLVER[branch.branch_id][sid]
            p_req, s_req = f"rP-{sid}-{branch.branch_id}", f"rS-{sid}-{branch.branch_id}"
            p_id, s_id = f"cP-{sid}-{branch.branch_id}", f"cS-{sid}-{branch.branch_id}"
            trace[f"{p_req}/request"] = {"payload_sha256": _sha(p_req)}
            trace[f"{p_req}/response"] = {"text": note, "usage": {"prompt_tokens": tokens}}
            trace[f"{s_req}/request"] = {"payload_sha256": _sha(s_req)}
            trace[f"{s_req}/response"] = {"text": answer, "usage": {"prompt_tokens": 2000}}
            perception_contacts.append({
                "agent_contact_id": p_id, "request_id": p_req,
                "request_sha256": _sha(p_req), "response_text_sha256": _sha(note),
            })
            solver_contacts.append({
                "agent_contact_id": s_id, "request_id": s_req,
                "request_sha256": _sha(s_req), "response_text_sha256": _sha(answer),
            })
            status, candidates, raw = parse_perception_branch_note(note)
            records.append(perception_branch_record(
                branch=branch, branch_index=index, contact_id=p_id, request_sha256=_sha(p_req),
                response_text_sha256=_sha(note), note_sha256=_sha(note), note_parse_status=status,
                candidate_intent_ids=candidates, candidate_intent_ids_raw_count=raw,
                supplied_value_ids=(), solver_contact_id=s_id, solver_request_sha256=_sha(s_req),
                solver_response_text_sha256=_sha(answer), candidate_supply_value_ids=(),
                template_group=True,
            ))
        rows.append({
            "sample_id": sid,
            "native_episode_receipt": {
                "perception_branches": perception_branch_receipt(
                    group=group, phase_id="perception", records=records),
                "role_visits": [
                    {"stage": "perception", "execution_receipt": {"contacts": perception_contacts}},
                    {"stage": "solver", "execution_receipt": {"contacts": solver_contacts}},
                ],
            },
        })
    return rows, trace


def _gold_map():
    return {
        sid: {"intent": intent, "entities": tuple(SlotEntity(t, f) for t, f in entities)}
        for sid, (intent, entities) in GOLD.items()
    }


def _read(**kwargs):
    sealed = reader.load_sealed_columns(*_sealed())
    return reader.read_columns(
        sealed["notes"], sealed["solver_texts"], _gold_map(), arm_ids=list(sealed["arm_ids"]),
        delivering=sealed["delivering"], twin=sealed["twin"], draws=300, **kwargs,
    )


# ---------------------------------------------------------------------------
# the pure parts


def test_entity_presence_reads_the_optional_verdict_and_nothing_else():
    assert reader.entity_presence_of(_note(["x"], "none", 0)) == {"verdict": "none", "heard_values": 0}
    assert reader.entity_presence_of(_note(["x"], "present", 3)) == {"verdict": "present", "heard_values": 3}
    assert reader.entity_presence_of(_note(["x"], "unsure"))["heard_values"] is None
    assert reader.entity_presence_of(_note(["x"]))["verdict"] == "absent"
    assert reader.entity_presence_of(_note(["x"], "maybe"))["verdict"] == "invalid"
    assert reader.entity_presence_of("not json")["verdict"] == "absent"
    assert reader.entity_presence_of(json.dumps([1]))["verdict"] == "absent"
    # heard_values must be a non-negative integer, never a bool or a negative number
    assert reader.entity_presence_of(_note(["x"], "none", True))["heard_values"] is None
    assert reader.entity_presence_of(_note(["x"], "none", -1))["heard_values"] is None


def test_the_sealed_loader_reads_every_arm_and_binds_trace_to_the_receipt():
    sealed = reader.load_sealed_columns(*_sealed())
    assert sealed["arm_ids"] == ARMS
    assert (sealed["delivering"], sealed["twin"]) == ("lock", "aa")
    assert sealed["templates"][0]["relpath"] == "probes/nx/p1.txt" and sealed["templates"][3] is None
    assert sorted(sealed["notes"]["p1"]) == sorted(GOLD)
    assert sealed["notes"]["p1"]["slurp:train:2:a"]["verdict"] == {"verdict": "none", "heard_values": 0}
    assert sealed["notes"]["lock"]["slurp:train:2:a"]["verdict"]["verdict"] == "absent"
    assert sealed["notes"]["p1"]["slurp:train:1:a"]["prompt_tokens"] == 1400
    assert sealed["solver_texts"]["p1"]["slurp:train:4:a"] == SOLVER["p1"]["slurp:train:4:a"]


def test_the_loader_refuses_a_tampered_trace_and_a_non_template_receipt():
    rows, trace = _sealed()
    victim = "rP-slurp:train:1:a-p1/response"
    trace[victim] = {**trace[victim], "text": _note(["tampered"])}
    with pytest.raises(reader.PerceptionColumnReadError, match="trace differs"):
        reader.load_sealed_columns(rows, trace)
    rows, trace = _sealed()
    rows[0]["native_episode_receipt"]["perception_branches"]["schema"] = "saea-perception-branch-arms-v3"
    with pytest.raises(reader.PerceptionColumnReadError, match="template columns only"):
        reader.load_sealed_columns(rows, trace)
    rows, trace = _sealed()
    rows[1]["native_episode_receipt"]["perception_branches"]["branches"][0]["instruction_template"] = {
        "relpath": "probes/nx/other.txt", "sha256": "c" * 64}
    with pytest.raises(reader.PerceptionColumnReadError, match="differ from the first row"):
        reader.load_sealed_columns(rows, trace)


# ---------------------------------------------------------------------------
# the read


def test_the_note_metrics_pair_each_arm_against_the_delivering_arm():
    report = _read()
    assert report["rows"] == 6 and report["rows_empty_gold"] == 2 and report["delivering_arm"] == "lock"
    p1 = report["arms"]["p1"]
    # gold on list: lock is present on
    # 1:a, 1:b (second), 2:a, 3:a (4/6) and absent on 2:b and 4:a; p1 is present on all six.
    assert report["arms"]["lock"]["notes"]["present"]["count"] == 4
    assert p1["notes"]["present"]["count"] == 6
    paired = p1["paired_vs_delivering"]["present"]
    assert paired["n"] == 6 and paired["b_arm_only"] == 2 and paired["c_delivering_only"] == 0
    assert paired["diff"] == pytest.approx(200.0 / 6, abs=1e-6)
    # top-1: lock is top-1 on 1:a, 2:a, 3:a; p1 on all six
    assert p1["notes"]["top1"]["count"] == 6 and report["arms"]["lock"]["notes"]["top1"]["count"] == 3
    assert p1["notes"]["gold_rank"] == {"1": 6, "2": 0, "3": 0, "4+": 0, "absent": 0}
    assert p1["notes"]["prompt_tokens"]["mean"] == 1400
    assert p1["paired_vs_delivering"]["prompt_tokens"]["diff"] == pytest.approx(400.0)
    assert p1["paired_vs_delivering"]["list_size"]["n"] == 6
    # the twin repeats the delivering arm exactly
    twin = report["arms"]["aa"]["paired_vs_delivering"]["present"]
    assert twin["diff"] == 0.0 and twin["b_arm_only"] == twin["c_delivering_only"] == 0
    assert report["bootstrap"] == {
        "draws": 300, "seed": 20260915, "ci_level": 0.95,
        "cluster": "whole utterance (first three colon segments of the sample id)",
    }


def test_the_entity_presence_verdict_is_scored_against_the_empty_gold_label():
    report = _read()
    e = report["arms"]["p1"]["entity_presence"]
    assert e["verdict_counts"] == {"present": 3, "none": 2, "unsure": 1, "invalid": 0, "absent": 0}
    # none: right on 2:a (empty gold), wrong on 3:a (non-empty gold); 2:b is unsure.
    assert (e["none_precision"]["count"], e["none_precision"]["n"]) == (1, 2)
    assert (e["none_recall"]["count"], e["none_recall"]["n"]) == (1, 2)
    # present: right on 1:a, 1:b, 4:a (non-empty gold), all three correct
    assert (e["present_precision"]["count"], e["present_precision"]["n"]) == (3, 3)
    assert (e["present_recall"]["count"], e["present_recall"]["n"]) == (3, 4)
    assert e["unsure_rate"]["count"] == 1
    assert e["heard_values"]["empty_gold"] == {"n": 2, "mean": 0.0}
    assert e["heard_values"]["nonempty_gold"]["n"] == 4
    # arms that carry no verdict are reported as such, not as zeros of precision
    lock = report["arms"]["lock"]["entity_presence"]
    assert lock["rows_carrying_a_verdict"] == 0 and lock["none_precision"]["rate"] is None
    # a carried-but-invalid value is counted as invalid
    assert report["arms"]["p2"]["entity_presence"]["verdict_counts"]["invalid"] == 6
    paired = report["arms"]["p1"]["paired_vs_delivering"]
    assert paired["none_on_empty"]["n"] == 2 and paired["none_on_empty"]["b_arm_only"] == 1
    assert paired["none_on_nonempty"]["n"] == 4 and paired["none_on_nonempty"]["b_arm_only"] == 1


def test_the_level_two_solver_column_reuses_the_solver_readers_scoring():
    report = _read()
    solver = report["solver_column"]
    assert solver["primary_metric"] == "exact_set_normalised"
    lock, p1 = solver["arms"]["lock"], solver["arms"]["p1"]
    # lock is exact on 1:a, 2:b; p1 is exact on 1:b, 2:a, 2:b, 4:a, and loses 1:a.
    assert lock["marginal"]["exact_set"]["count"] == 2
    assert p1["marginal"]["exact_set"]["count"] == 4
    assert p1["paired_vs_delivering"]["exact_set"]["b_arm_only"] == 3
    assert p1["paired_vs_delivering"]["exact_set"]["c_delivering_only"] == 1
    assert p1["paired_vs_delivering"]["empty_gold_false_fill"]["diff_pp"] == pytest.approx(-50.0)
    assert solver["arms"]["aa"]["paired_vs_delivering"]["exact_set"]["diff_pp"] == 0.0
    assert set(solver["mechanical_screen"]) == {"p1", "p2"}


def test_the_read_refuses_a_missing_gold_row_and_an_unbalanced_arm():
    sealed = reader.load_sealed_columns(*_sealed())
    gold = _gold_map()
    del gold["slurp:train:4:a"]
    with pytest.raises(reader.PerceptionColumnReadError, match="absent from the gold"):
        reader.read_columns(sealed["notes"], sealed["solver_texts"], gold, arm_ids=list(ARMS),
                            delivering="lock", twin="aa", draws=50)
    notes = {**sealed["notes"], "p1": {k: v for k, v in sealed["notes"]["p1"].items() if k != "slurp:train:4:a"}}
    with pytest.raises(reader.PerceptionColumnReadError, match="does not cover"):
        reader.read_columns(notes, sealed["solver_texts"], _gold_map(), arm_ids=list(ARMS),
                            delivering="lock", twin="aa", draws=50)


def test_no_text_reaches_the_report_or_the_tables():
    report = _read()
    document = json.dumps(report, sort_keys=True) + reader.render(report)
    for forbidden in (SECRET, "monday", "friday", "nine", "tuesday", "candidates", "intent_id"):
        assert forbidden not in document
    # slot TYPE names and arm ids are allowed
    assert "date" in document and "p1" in document


def test_the_tables_render_every_section():
    text = reader.render(_read())
    for heading in (
        "## Perception note: marginal rates (%)", "## Perception note: paired difference vs the delivering arm",
        "## Entity-presence verdict (rows carrying one)", "## Level-2 Solver column",
    ):
        assert heading in text
