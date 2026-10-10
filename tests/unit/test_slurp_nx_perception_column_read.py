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


# E2b: distinction strings per (arm, sample id), one per candidate in note order. Arms or rows not listed carry no
# distinction field at all (the pre-R6 shape).
TAGS = {}


def _note(intents, presence=None, heard=None, distinctions=None):
    document = {"candidates": [{"intent_id": i} for i in intents]}
    if distinctions is not None:
        for row, text in zip(document["candidates"], distinctions):
            row["distinction"] = text
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
            note = _note(intents, presence, heard, TAGS.get((branch.branch_id, sid)))
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


# ---------------------------------------------------------------------------
# E2b: the distinction tag (TAG-GRAMMAR-v1), parser and metrics


@pytest.mark.parametrize(
    "text, tag_set, cls, verdict, mentions, reason",
    [
        ("E=none; no entity here", None, "ok", "none", (), None),
        ("E=some; fine words", None, "ok", "some", (), None),
        ("E=some; M=a b c d; M=x; fine words", None, "ok", "some", ("a b c d", "x"), None),
        ("E=some; M=a; M=b; M=c; fine words", None, "ok", "some", ("a", "b", "c"), None),
        ("E=unsure; short clip", ("none", "some", "unsure"), "ok", "unsure", (), None),
        ("E=unsure; short clip", None, "invalid", None, (), "head_value"),
        ("E=None; x", None, "invalid", None, (), "head_value"),
        ("E=; x", None, "invalid", None, (), "head_form"),
        ("E=some", None, "invalid", None, (), "no_trailer"),
        ("E=some; M=x", None, "invalid", None, (), "no_trailer"),
        ("E=some;M=x; words", None, "invalid", None, (), "separator"),
        ("E=some; M=a b c d e; words", None, "invalid", None, (), "mention_form"),
        ("E=some; M=a  b; words", None, "invalid", None, (), "mention_form"),
        ("E=some; M=; words", None, "invalid", None, (), "mention_form"),
        ("E=some; M=a; M=b; M=c; M=d; words", None, "invalid", None, (), "mention_count"),
        ("E=none; M=x; words", None, "invalid", None, (), "mention_after_none"),
        ("E=unsure; M=x; words", ("none", "some", "unsure"), "invalid", None, (), "mention_after_unsure"),
        ("E=some; words not a mention; words", None, "invalid", None, (), "middle_not_mention"),
        ("E=some; one two three four five six seven eight nine", None, "invalid", None, (), "trailer_form"),
        ("E=some;  double", None, "invalid", None, (), "trailer_form"),
        ("E=some; café", None, "invalid", None, (), "trailer_form"),
        ("e=some; x", None, "absent", None, (), None),
        ("a plain distinction", None, "absent", None, (), None),
        ("", None, "absent", None, (), None),
        (None, None, "absent", None, (), None),
        (7, None, "absent", None, (), None),
    ],
)
def test_the_distinction_tag_parser_implements_the_pinned_grammar(text, tag_set, cls, verdict, mentions, reason):
    kwargs = {} if tag_set is None else {"tag_set": tag_set}
    parsed = reader.parse_distinction_tag(text, **kwargs)
    assert (parsed["cls"], parsed["verdict"], parsed["mentions"], parsed["reason"]) == (
        cls, verdict, mentions, reason)


def test_the_grammar_text_the_parser_cites_exists_and_names_the_same_limits():
    text = (_REPO / reader.TAG_GRAMMAR_RELPATH).read_text(encoding="utf-8")
    assert "E=" in text and "at most three mentions" in text and "at most 4" in text and "at most 8" in text
    assert (reader.MAX_MENTIONS, reader.MAX_MENTION_WORDS, reader.MAX_TRAILER_WORDS) == (3, 4, 8)


def test_a_tag_set_the_arm_does_not_allow_is_refused():
    assert reader.validate_tag_set(("unsure", "some", "none")) == ("none", "some", "unsure")
    for bad in (("none",), ("some", "unsure"), ("none", "some", "maybe"), ("none", "some", "some"), ()):
        with pytest.raises(reader.PerceptionColumnReadError):
            reader.validate_tag_set(bad)
    with pytest.raises(reader.PerceptionColumnReadError):
        reader.parse_distinction_tag("E=some; x", tag_set=("none",))
    assert reader.parse_tag_set_args(["p3=none,some,unsure", "p1=none,some"]) == {
        "p3": ("none", "some", "unsure"), "p1": ("none", "some")}
    for bad in (["p1"], ["=none,some"], ["p1="], ["p1=none,some", "p1=none,some,unsure"], ["p1=none,maybe"]):
        with pytest.raises(reader.PerceptionColumnReadError):
            reader.parse_tag_set_args(bad)
    # a tag set naming an arm the run does not have is refused by the loader and by the read
    with pytest.raises(reader.PerceptionColumnReadError, match="does not have"):
        reader.load_sealed_columns(*_sealed(), tag_sets={"zz": ("none", "some")})
    sealed = reader.load_sealed_columns(*_sealed())
    with pytest.raises(reader.PerceptionColumnReadError, match="does not have"):
        reader.read_columns(sealed["notes"], sealed["solver_texts"], _gold_map(), arm_ids=list(ARMS),
                            delivering="lock", twin="aa", tag_sets={"zz": ("none", "some")}, draws=50)


def test_note_tags_and_the_list_majority():
    note = _note(["a", "b", "c"], distinctions=["E=some; x", "E=some; M=m; y", "E=none; z"])
    parses = reader.note_tags(note)
    assert [p["verdict"] for p in parses] == ["some", "some", "none"]
    assert reader.list_majority(parses) == "some"
    assert reader.list_majority(reader.note_tags(_note(["a", "b"], distinctions=["E=some; x", "E=none; y"]))) == "split"
    assert reader.list_majority(reader.note_tags(_note(["a", "b", "c"], distinctions=["E=some; x", "bad", "x"]))) == "some"
    assert reader.list_majority(reader.note_tags(_note(["a"], distinctions=["E=unsure; y"]))) == "invalid"
    assert reader.list_majority(reader.note_tags(_note(["a"], distinctions=["plain"]))) == "absent"
    assert reader.list_majority([]) == "absent"
    for junk in ("not json", json.dumps([1]), json.dumps({"candidates": "x"}), None):
        assert reader.note_tags(junk) == []
    # a note without distinction fields at all (the pre-R6 shape) is absent on every candidate
    assert [p["cls"] for p in reader.note_tags(_note(["a", "b"]))] == ["absent", "absent"]
    summary = reader.tag_summary(parses)
    assert summary["rank1_verdict"] == "some" and summary["majority"] == "some"
    assert reader.tag_summary([])["rank1_verdict"] == "absent"


def _with_tags():
    TAGS.clear()
    TAGS.update({
        ("p1", "slurp:train:1:a"): ["E=some; real words here"],
        ("p1", "slurp:train:1:b"): ["E=some; two candidates", "E=none; the other"],
        ("p1", "slurp:train:2:a"): ["E=none; speech has no entity"],
        ("p1", "slurp:train:2:b"): ["E=unsure; short clip"],
        ("p1", "slurp:train:3:a"): ["E=none; wrongly empty"],
        ("p1", "slurp:train:4:a"): ["a plain distinction"],
        ("p2", "slurp:train:1:a"): ["E=some; M=Monday; M=nine; date and time given"],
        ("p2", "slurp:train:1:b"): ["E=some; M=tuesday; day given"],
        ("p2", "slurp:train:2:a"): ["E=none; nothing entity"],
        ("p2", "slurp:train:2:b"): ["E=none; M=oops; bad mention"],
        ("p2", "slurp:train:3:a"): ["E=some; M=" + SECRET.upper() + "; place named"],
        ("p2", "slurp:train:4:a"): ["E=some; M=Friday; M=noon; a day"],
    })


@pytest.fixture
def tagged():
    _with_tags()
    yield
    TAGS.clear()


def test_the_loader_parses_every_candidate_under_the_arms_tag_set(tagged):
    sealed = reader.load_sealed_columns(*_sealed())
    assert sealed["tag_sets"]["p1"] == ("none", "some") and sealed["tag_sets"]["lock"] == ("none", "some")
    t = sealed["notes"]["p1"]
    assert t["slurp:train:1:b"]["tag"]["rank1_verdict"] == "some" and t["slurp:train:1:b"]["tag"]["majority"] == "split"
    assert t["slurp:train:2:b"]["tag"]["rank1_verdict"] == "invalid"       # unsure under the default set
    assert t["slurp:train:4:a"]["tag"]["rank1_verdict"] == "absent"
    # the same sealed run read under a set that allows unsure
    widened = reader.load_sealed_columns(*_sealed(), tag_sets={"p1": ("none", "some", "unsure")})
    assert widened["notes"]["p1"]["slurp:train:2:b"]["tag"]["rank1_verdict"] == "unsure"
    # arms whose templates carry no tag are absent on every row (lock, aa)
    assert {v["tag"]["rank1_verdict"] for v in sealed["notes"]["lock"].values()} == {"absent"}
    # the key-path reader is untouched by the tag work
    assert sealed["notes"]["p1"]["slurp:train:2:a"]["verdict"] == {"verdict": "none", "heard_values": 0}


def test_presence_metrics_of_the_tag_on_rank1_and_on_the_list_majority(tagged):
    report = _read()
    tag = report["arms"]["p1"]["distinction_tag"]
    assert tag["tag_set"] == ["none", "some"] and report["tag_sets"]["p1"] == ["none", "some"]
    assert tag["parse"]["rank1"] == {"ok": 4, "absent": 1, "invalid": 1}
    assert tag["parse"]["every_candidate"] == {"n": 7, "ok": 5, "absent": 1, "invalid": 1}
    assert tag["parse"]["invalid_reasons"] == {"head_value": 1}
    r1 = tag["rank1"]
    assert r1["verdict_counts"] == {"none": 2, "some": 2, "unsure": 0, "split": 0, "invalid": 1, "absent": 1}
    assert (r1["none_precision"]["count"], r1["none_precision"]["n"]) == (1, 2)
    assert (r1["none_recall"]["count"], r1["none_recall"]["n"]) == (1, 1)
    assert (r1["none_recall_all_rows"]["count"], r1["none_recall_all_rows"]["n"]) == (1, 2)
    assert (r1["some_precision"]["count"], r1["some_precision"]["n"]) == (2, 2)
    assert (r1["some_recall"]["count"], r1["some_recall"]["n"]) == (2, 3)
    assert (r1["some_recall_all_rows"]["count"], r1["some_recall_all_rows"]["n"]) == (2, 4)
    assert r1["none_auc"]["n"] == 4 and r1["none_auc"]["auc"] == pytest.approx(2.5 / 3)
    lo, hi = r1["none_auc"]["ci95"]
    assert 0.0 <= lo <= hi <= 1.0
    maj = tag["majority"]
    assert maj["verdict_counts"] == {"none": 2, "some": 1, "unsure": 0, "split": 1, "invalid": 1, "absent": 1}
    # the delivering arm and the twin carry no tag: absent everywhere, no metric invented
    lock = report["arms"]["lock"]["distinction_tag"]
    assert lock["parse"]["rank1"] == {"ok": 0, "absent": 6, "invalid": 0}
    assert lock["rank1"]["none_precision"]["rate"] is None and lock["rank1"]["none_auc"]["auc"] is None


def test_unsure_is_scored_only_where_the_arm_allows_it(tagged):
    sealed = reader.load_sealed_columns(*_sealed(), tag_sets={"p1": ("none", "some", "unsure")})
    report = reader.read_columns(sealed["notes"], sealed["solver_texts"], _gold_map(), arm_ids=list(ARMS),
                                 delivering="lock", twin="aa", tag_sets=sealed["tag_sets"], draws=100)
    tag = report["arms"]["p1"]["distinction_tag"]
    assert tag["tag_set"] == ["none", "some", "unsure"]
    r1 = tag["rank1"]
    assert r1["verdict_counts"]["unsure"] == 1 and r1["verdict_counts"]["invalid"] == 0
    assert (r1["unsure_rate"]["count"], r1["unsure_rate"]["n"]) == (1, 5)
    assert (r1["unsure_by_gold"]["empty_gold"]["count"], r1["unsure_by_gold"]["empty_gold"]["n"]) == (1, 2)
    assert (r1["unsure_by_gold"]["nonempty_gold"]["count"], r1["unsure_by_gold"]["nonempty_gold"]["n"]) == (0, 3)
    assert r1["none_auc"]["auc"] == pytest.approx(4.5 / 6)
    # p2 keeps the default set
    assert report["arms"]["p2"]["distinction_tag"]["tag_set"] == ["none", "some"]


def test_heard_mentions_are_matched_on_the_registered_surface_normalisation(tagged):
    report = _read()
    p2 = report["arms"]["p2"]["distinction_tag"]
    assert p2["parse"]["rank1"] == {"ok": 5, "absent": 0, "invalid": 1}
    assert p2["parse"]["invalid_reasons"] == {"mention_after_none": 1}
    m = p2["mentions"]["rank1"]
    # gold entities on the four rows that offer mentions: monday+nine, monday, the secret place, friday
    assert m["rows_offering_any"] == 4 and m["gold_entities"] == 5
    assert (m["containment"]["count"], m["containment"]["n"]) == (4, 5)       # Monday->monday, ZANZIBAR-QUOKKA->lower
    assert (m["containment_on_ok_rows"]["count"], m["containment_on_ok_rows"]["n"]) == (4, 5)
    assert (m["option_precision"]["count"], m["option_precision"]["n"]) == (4, 6)   # tuesday and noon are not gold
    assert m["offered_options_on_empty_gold_rows"] == 0
    assert {t: (v["gold_entities"], v["count"]) for t, v in m["containment_by_slot_type"].items()} == {
        "date": (3, 2), "place_name": (1, 1), "time": (1, 1)}
    assert m["matched_options_by_slot_type"] == {"date": 2, "place_name": 1, "time": 1}
    assert p2["mentions"]["list_union"]["gold_entities"] == 5
    # arms with no mentions offer nothing and contain nothing
    p1 = report["arms"]["p1"]["distinction_tag"]["mentions"]["rank1"]
    assert p1["rows_offering_any"] == 0 and p1["containment"]["count"] == 0 and p1["option_precision"]["rate"] is None


def test_mention_table_counts_offers_on_empty_gold_rows_and_dedupes_per_row():
    gold = {"r1": {"entities": (SlotEntity("date", "Monday"),)}, "r2": {"entities": ()}}
    table = reader.mention_table(
        {"r1": ("monday", "MONDAY", "ghost"), "r2": ("ghost",)}, gold, ["r1", "r2"], ok_rows={"r1": True, "r2": True})
    assert table["offered_options"] == 3 and table["offered_options_on_empty_gold_rows"] == 1
    assert (table["option_precision"]["count"], table["option_precision"]["n"]) == (1, 3)
    assert (table["containment"]["count"], table["containment"]["n"]) == (1, 1)


def test_no_note_text_or_mention_reaches_the_tag_report_or_tables(tagged):
    report = _read()
    document = json.dumps(report, sort_keys=True) + reader.render(report)
    for forbidden in (SECRET, SECRET.upper(), "zanzibar", "monday", "tuesday", "friday", "noon", "oops",
                      "speech has no entity", "wrongly empty", "candidates", "intent_id"):
        assert forbidden not in document
    # the tables render the E2b sections
    for heading in ("## Distinction tag (E2b): parse classes", "presence verdict on the rank-1 candidate",
                    "presence verdict on the list majority", "## Distinction tag (E2b): heard mentions"):
        assert heading in document


def test_arms_without_a_tag_summary_are_read_as_before():
    sealed = reader.load_sealed_columns(*_sealed())
    notes = {arm: {sid: {k: v for k, v in row.items() if k != "tag"} for sid, row in rows.items()}
             for arm, rows in sealed["notes"].items()}
    report = reader.read_columns(notes, sealed["solver_texts"], _gold_map(), arm_ids=list(ARMS),
                                 delivering="lock", twin="aa", draws=50)
    assert all(report["arms"][arm]["distinction_tag"] is None for arm in ARMS)
    assert "Distinction tag" not in reader.render(report)
