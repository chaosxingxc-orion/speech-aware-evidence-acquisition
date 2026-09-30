"""P-SV-1 seal abort regression (2026-09-29): a Perception branch's degenerate candidate list
is a MEASURED OUTCOME, never a seal failure.

Cell P-SV-1 (``slurp-native-stage3-psv1-fold-b-v1``) flew 1,080 rows (8,709 calls) and aborted
at seal with ``BundleError: ... perception-branch receipt is invalid: perception branch
candidate_intent_ids must be a non-empty ordered list of distinct non-empty strings (I7v)``: the
runner sealed each branch note's parsed intent list VERBATIM, and 61 branch notes over 49 rows
listed one intent twice (a-agree 21, b-top2contrast 17, t-twin 23). The fix (receipt schema v2):

* ``candidate_intent_ids`` keeps the parsed order with duplicates collapsed (first occurrence);
* ``candidate_intent_ids_raw_count`` records how many ids the note listed;
* ``note_parse_status`` is one of ``ok`` / ``duplicates-collapsed`` / ``empty`` / ``malformed``;
  ``empty`` and ``malformed`` carry an empty list (no ``("unparsed",)`` sentinel);
* the level-2 fold carries the presentation outcome and ``min_candidates_met`` through (it
  dropped them before: every P-SV-1 ``b-top2contrast`` row sealed None/None, and a level-2
  ``min_candidates`` branch -- P-SV-2 ``b-list3`` -- would have refused every row);
* a seal-only resume re-derives the whole block from the recorded trace.

Zero model, real server, GPU or network contact; synthetic ids and texts only.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _verify_perception_branch_trace_binding,
)
from speech_aware_evidence_acquisition.core.flight.resume import read_predecessor_attempt
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    PERCEPTION_BRANCH_RECEIPT_SCHEMA,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V2,
    parse_perception_branch_note,
    validate_perception_branch_receipt,
)
from speech_aware_evidence_acquisition.rails.perception_presentations import (
    TOP2_CONTRAST_PRESENTATION_ID,
    TOP2_CONTRAST_SKIP_REASON_FEWER_THAN_TWO_CANDIDATES,
    TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    PerceptionBranchError,
    PerceptionBranchReplayContact,
    parse_perception_branches,
    perception_branch_record,
    replay_perception_branch_block,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_bundle_perception_branches import check, fixture
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import ACTIONS, PHASES, _ActualEpisodeHarness

EXACT_PSV1_ERROR = (
    "perception-branch receipt is invalid: perception branch candidate_intent_ids must be a "
    "non-empty ordered list of distinct non-empty strings (I7v)"
)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def note(*intent_ids: str) -> str:
    return json.dumps({"candidates": [{"intent_id": value} for value in intent_ids]})


# ---------------------------------------------------------------------------
# 1. The exact failure, reproduced on the v1 receipt shape P-SV-1 sealed.
# ---------------------------------------------------------------------------


def _v1_row_with_duplicate_list():
    row, trace = fixture()
    branch = row["native_episode_receipt"]["perception_branches"]["branches"][0]
    branch["note_parse_status"] = "ok"
    branch["candidate_intent_ids"] = ["alarm_set", "alarm_set"]
    return row, trace


def test_v1_duplicate_list_reproduces_the_exact_psv1_seal_error():
    row, trace = _v1_row_with_duplicate_list()
    with pytest.raises(BundleError) as caught:
        check(row, trace)
    assert str(caught.value).endswith(EXACT_PSV1_ERROR)


def test_v1_receipts_keep_their_original_rule():
    """An already-sealed v1 bundle (the P-SV-1 4-row smoke) still verifies unchanged."""

    row, trace = fixture()
    assert row["native_episode_receipt"]["perception_branches"]["schema"] == (
        PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1
    )
    check(row, trace)


# ---------------------------------------------------------------------------
# 2. The parse.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (note("a", "b", "c"), ("ok", ("a", "b", "c"), 3)),
        (note("a", "b", "a"), ("duplicates-collapsed", ("a", "b"), 3)),
        (note("a", "a"), ("duplicates-collapsed", ("a",), 2)),
        (note("b", "a", "a", "b"), ("duplicates-collapsed", ("b", "a"), 4)),
        (note(), ("empty", (), 0)),
        ("not json", ("malformed", (), 0)),
        (json.dumps({"no_candidates": []}), ("malformed", (), 0)),
        (json.dumps({"candidates": [{"intent_id": ""}]}), ("malformed", (), 0)),
        (json.dumps({"candidates": [{"intent_id": "a"}, {"slots": []}]}), ("malformed", (), 0)),
        (json.dumps(["a"]), ("malformed", (), 0)),
        (None, ("malformed", (), 0)),
    ],
)
def test_parse_perception_branch_note(text, expected):
    assert parse_perception_branch_note(text) == expected


# ---------------------------------------------------------------------------
# 3. The record constructor and the v2 validator (I7v).
# ---------------------------------------------------------------------------

FIT = {
    "slot_tokens": 24576, "completion_ceiling": 512,
    "base_prompt_tokens": 4000, "tokens_per_supplied_item": 100,
}


def _group(level=1, *, b=None):
    return parse_perception_branches(
        {
            "level": level, "fit_estimate": dict(FIT),
            "branches": [
                b or {"branch_id": "B", "max_supplied_items": 8, "min_candidates": 3},
                {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8},
                {"branch_id": "A", "deliver": True, "max_supplied_items": 8},
            ],
        },
        first_phase_id="perception", max_candidates_ceiling=3,
    )


def _receipt(group, notes):
    from speech_aware_evidence_acquisition.rails.supply_variants import perception_branch_receipt

    records = []
    for index, branch in enumerate(group.branches):
        status, ids, raw = parse_perception_branch_note(notes[branch.branch_id])
        records.append(perception_branch_record(
            branch=branch, branch_index=index, contact_id=f"c{index}",
            request_sha256=sha(f"req{index}"), response_text_sha256=sha(notes[branch.branch_id]),
            note_sha256=sha(notes[branch.branch_id]), note_parse_status=status,
            candidate_intent_ids=ids, candidate_intent_ids_raw_count=raw,
            supplied_value_ids=("v1",),
            min_candidates_met=(
                None if branch.min_candidates is None else len(ids) >= branch.min_candidates
            ),
        ))
    return perception_branch_receipt(group=group, phase_id="perception", records=records)


def _validate(receipt, group):
    validate_perception_branch_receipt(
        receipt, branch_ids=group.branch_ids, delivered_branch_id="A", twin_branch_id="T",
        phase_id="perception", level=group.level,
    )


def test_v2_receipt_records_every_degenerate_outcome_and_validates():
    group = _group()
    receipt = _receipt(group, {"B": note("a", "a", "b"), "T": note(), "A": "garbage"})
    assert receipt["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA
    rows = {row["branch_id"]: row for row in receipt["branches"]}
    assert rows["B"]["note_parse_status"] == "duplicates-collapsed"
    assert rows["B"]["candidate_intent_ids"] == ["a", "b"]
    assert rows["B"]["candidate_intent_ids_raw_count"] == 3
    # A padded [a, a, b] meets a bound of 2, never 3: counted on the collapsed list.
    assert rows["B"]["min_candidates_met"] is False
    assert rows["T"]["note_parse_status"] == "empty"
    assert rows["T"]["candidate_intent_ids"] == []
    assert rows["A"]["note_parse_status"] == "malformed"
    assert rows["A"]["candidate_intent_ids"] == []
    assert rows["A"]["candidate_intent_ids_raw_count"] == 0
    _validate(receipt, group)


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda row: row.update(candidate_intent_ids=["a", "a"]), "distinct"),
        (lambda row: row.update(note_parse_status="ok"), "raw count equals"),
        (lambda row: row.update(note_parse_status="empty"), "carries no candidate"),
        (lambda row: row.update(note_parse_status="parsed"), "must be one of"),
        (lambda row: row.update(candidate_intent_ids_raw_count=2), "listed more"),
        (lambda row: row.update(candidate_intent_ids_raw_count=True), "non-negative integer"),
        (lambda row: row.update(candidate_intent_ids=[]), "at least one"),
        (lambda row: row.update(min_candidates_met=True), "min_candidates_met disagrees"),
        (lambda row: row.pop("candidate_intent_ids_raw_count"), "invalid shape"),
    ],
)
def test_v2_validator_refuses_an_inconsistent_triple(mutate, match):
    group = _group()
    receipt = _receipt(group, {"B": note("a", "a", "b"), "T": note("a"), "A": note("a")})
    mutate(receipt["branches"][0])
    with pytest.raises(ValueError, match=match):
        _validate(receipt, group)


def test_v2_validator_refuses_a_malformed_note_carrying_ids():
    group = _group()
    receipt = _receipt(group, {"B": "garbage", "T": note("a"), "A": note("a")})
    receipt["branches"][0]["candidate_intent_ids"] = ["unparsed"]
    with pytest.raises(ValueError, match="carries no candidate"):
        _validate(receipt, group)


def test_record_constructor_refuses_an_uncollapsed_list():
    group = _group()
    with pytest.raises(PerceptionBranchError, match="distinct"):
        perception_branch_record(
            branch=group.branch("A"), branch_index=2, contact_id="c2",
            request_sha256=sha("r"), response_text_sha256=sha("n"), note_sha256=sha("n"),
            note_parse_status="ok", candidate_intent_ids=("a", "a"),
            supplied_value_ids=("v1",),
        )


# ---------------------------------------------------------------------------
# 4. The bundle's I7v re-derives the note fields from the trace (v2).
# ---------------------------------------------------------------------------


def _v2_bundle_fixture():
    row, trace = fixture()
    block = row["native_episode_receipt"]["perception_branches"]
    block["schema"] = PERCEPTION_BRANCH_RECEIPT_SCHEMA_V2  # a v2 bundle: rows carry no key_source
    notes = {"B": note("a", "b", "a"), "T": note(), "A": note("a", "b")}
    for index, branch in enumerate(block["branches"]):
        text = notes[branch["branch_id"]]
        trace[f"request-perception-{index}/response"]["text"] = text
        trace[f"request-perception-{index}/response"]["response_text_sha256"] = sha(text)
        visit_contact = row["native_episode_receipt"]["role_visits"][0]["execution_receipt"][
            "contacts"][index]
        visit_contact["response_text_sha256"] = sha(text)
        status, ids, raw = parse_perception_branch_note(text)
        branch.update(
            response_text_sha256=sha(text), note_sha256=sha(text), note_parse_status=status,
            candidate_intent_ids=list(ids), candidate_intent_ids_raw_count=raw,
        )
    a_text = notes["A"]
    row.update(text=a_text, response_text_sha256=sha(a_text))
    return row, trace


def test_v2_bundle_accepts_collapsed_and_empty_lists():
    row, trace = _v2_bundle_fixture()
    _verify_perception_branch_trace_binding(row, trace)


def test_v2_bundle_refuses_note_fields_that_do_not_re_derive_from_the_trace():
    row, trace = _v2_bundle_fixture()
    branch = row["native_episode_receipt"]["perception_branches"]["branches"][0]
    branch.update(candidate_intent_ids=["b", "a"])
    with pytest.raises(BundleError, match="do not re-derive"):
        _verify_perception_branch_trace_binding(row, trace)


# ---------------------------------------------------------------------------
# 5. The pure replay (seal-only resume-recovery of a v1 block).
# ---------------------------------------------------------------------------

VX = "intent-boundaries::intent-boundary:alarm_set"
VY = "intent-boundaries::intent-boundary:alarm_query"


def _contrast_group():
    return parse_perception_branches(
        {
            "level": 2, "fit_estimate": dict(FIT),
            "branches": [
                {
                    "branch_id": "B", "max_supplied_items": 8,
                    "presentation_id": TOP2_CONTRAST_PRESENTATION_ID,
                    "contrast_pairs": {"relpath": "prepared/X/table.json", "sha256": "a" * 64},
                },
                {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8},
                {"branch_id": "A", "deliver": True, "max_supplied_items": 8},
            ],
        },
        first_phase_id="perception",
        registered_presentation_ids=(TOP2_CONTRAST_PRESENTATION_ID,),
        top2_contrast_presentation_id=TOP2_CONTRAST_PRESENTATION_ID,
    )


def _legacy_ids(text):
    """The pre-fix runner's verbatim list, or its ``("unparsed",)`` sentinel."""

    try:
        return [c["intent_id"] for c in json.loads(text)["candidates"]] or ["unparsed"]
    except (ValueError, TypeError, KeyError):
        return ["unparsed"]


def _v1_lossy_block(notes, *, supplied):
    """The block exactly as P-SV-1 sealed it: schema v1, verbatim lists, and the level-2 fold's
    dropped presentation outcome (None/None on the contrast branch)."""

    group = _contrast_group()
    rows = []
    contacts = {}
    for index, branch in enumerate(group.branches):
        text = notes[branch.branch_id]
        rows.append({
            "branch_index": index, "branch_id": branch.branch_id, "deliver": branch.deliver,
            "replicate_of": branch.replicate_of, "resolved_knobs": [], "release_swap": None,
            "presentation_id": branch.presentation_id, "min_candidates": None,
            "supplied_value_ids": list(supplied), "supplied_count": len(supplied),
            "max_supplied_items": 8, "contact_id": f"p{index}",
            "request_sha256": sha(f"preq{index}"), "response_text_sha256": sha(text),
            "note_sha256": sha(text), "note_parse_status": "ok",
            "candidate_intent_ids": _legacy_ids(text),
            "presentation_skip_reason": None, "contrast_block_sha256": None,
            "min_candidates_met": None,
            "solver_contact_id": f"s{index}", "solver_request_sha256": sha(f"sreq{index}"),
            "solver_response_text_sha256": sha(f"answer{index}"),
            "candidate_supply_value_ids": [],
        })
        contacts[f"p{index}"] = PerceptionBranchReplayContact(
            request_sha256=sha(f"preq{index}"), response_text_sha256=sha(text), text=text,
        )
        contacts[f"s{index}"] = PerceptionBranchReplayContact(
            request_sha256=sha(f"sreq{index}"), response_text_sha256=sha(f"answer{index}"),
            text=f"answer{index}",
        )
    block = {
        "schema": PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1, "phase_id": "perception", "level": 2,
        "branch_count": 3, "delivered_branch_id": "A", "branch_visits": "first",
        "visit_index": 0,
        "fit_estimate": {
            "slot_tokens": 24576, "completion_ceiling": 512, "base_prompt_tokens": 4000,
            "tokens_per_supplied_item": 100, "reserve_tokens": 3072,
            "prompt_limit_tokens": 20992,
        },
        "branches": rows,
    }
    return block, contacts


def test_replay_rebuilds_a_v1_duplicate_block_under_v2():
    notes = {"B": note("alarm_set", "alarm_set"), "T": note("alarm_set"), "A": note("alarm_set")}
    block, contacts = _v1_lossy_block(notes, supplied=(VX, VY))
    block_sha = sha("contrast block text")
    contacts["p0"] = PerceptionBranchReplayContact(
        request_sha256=contacts["p0"].request_sha256,
        response_text_sha256=contacts["p0"].response_text_sha256, text=contacts["p0"].text,
        presentation_block_sha256={"perception-branch-presentation:B": block_sha},
    )
    rebuilt = replay_perception_branch_block(block, contacts=contacts)
    assert rebuilt["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA  # rebuilt under the current schema
    assert all(row["key_source"] is None for row in rebuilt["branches"])
    b = rebuilt["branches"][0]
    assert b["note_parse_status"] == "duplicates-collapsed"
    assert b["candidate_intent_ids"] == ["alarm_set"]
    assert b["candidate_intent_ids_raw_count"] == 2
    assert b["contrast_block_sha256"] == block_sha
    assert b["presentation_skip_reason"] is None
    # Identity and level-2 custody are kept verbatim.
    for field in ("contact_id", "request_sha256", "solver_contact_id", "supplied_value_ids"):
        assert b[field] == block["branches"][0][field]
    assert block["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1  # input never mutated


@pytest.mark.parametrize(
    ("supplied", "reason"),
    [
        ((VX, VY), TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT),
        ((VX,), TOP2_CONTRAST_SKIP_REASON_FEWER_THAN_TWO_CANDIDATES),
    ],
)
def test_replay_re_derives_the_presentation_skip_reason(supplied, reason):
    notes = {"B": note("alarm_set"), "T": note("alarm_set"), "A": note("alarm_set")}
    block, contacts = _v1_lossy_block(notes, supplied=supplied)
    rebuilt = replay_perception_branch_block(block, contacts=contacts)
    assert rebuilt["branches"][0]["presentation_skip_reason"] == reason
    assert rebuilt["branches"][0]["contrast_block_sha256"] is None


def test_replay_refuses_an_unaccounted_contact_or_a_foreign_note():
    notes = {"B": note("a"), "T": note("a"), "A": note("a")}
    block, contacts = _v1_lossy_block(notes, supplied=(VX, VY))
    missing = dict(contacts)
    del missing["s1"]
    with pytest.raises(PerceptionBranchError, match="did not record"):
        replay_perception_branch_block(block, contacts=missing)
    swapped = dict(contacts)
    swapped["p0"] = PerceptionBranchReplayContact(
        request_sha256=contacts["p0"].request_sha256,
        response_text_sha256=contacts["p0"].response_text_sha256, text=note("other"),
    )
    with pytest.raises(PerceptionBranchError, match="does not hash"):
        replay_perception_branch_block(block, contacts=swapped)
    foreign = dict(contacts)
    foreign["p1"] = PerceptionBranchReplayContact(
        request_sha256=contacts["p1"].request_sha256,
        response_text_sha256=contacts["p1"].response_text_sha256, text=contacts["p1"].text,
        presentation_block_sha256={"perception-branch-presentation:T": sha("x")},
    )
    with pytest.raises(PerceptionBranchError, match="does not declare"):
        replay_perception_branch_block(block, contacts=foreign)


def test_replay_of_a_v2_block_is_the_identity():
    notes = {"B": note("a", "b", "a"), "T": note(), "A": "garbage"}
    block, contacts = _v1_lossy_block(notes, supplied=(VX,))
    once = replay_perception_branch_block(block, contacts=contacts)
    assert replay_perception_branch_block(once, contacts=contacts) == once


# ---------------------------------------------------------------------------
# 6. Live (fake transport, real graph): level 2 with a min_candidates branch and a contrast
#    branch seals; the seal-only replay from the trace equals the live seal.
# ---------------------------------------------------------------------------

SEED_VALUE = "value:dim-light"
LIVE_FIT = {
    "slot_tokens": 24576, "completion_ceiling": 640,
    "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120,
}


def _live_group():
    return parse_perception_branches(
        {
            "level": 2, "fit_estimate": dict(LIVE_FIT),
            "branches": [
                {"branch_id": "B3", "max_supplied_items": 4, "min_candidates": 3},
                {
                    "branch_id": "BC", "max_supplied_items": 4,
                    "presentation_id": TOP2_CONTRAST_PRESENTATION_ID,
                    "contrast_pairs": {"relpath": "prepared/X/table.json", "sha256": "a" * 64},
                },
                {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 4},
                {"branch_id": "A", "deliver": True, "max_supplied_items": 4},
            ],
        },
        first_phase_id="perception", max_candidates_ceiling=3,
        registered_presentation_ids=(TOP2_CONTRAST_PRESENTATION_ID,),
        top2_contrast_presentation_id=TOP2_CONTRAST_PRESENTATION_ID,
    )


#: Perception turn -> note: B3 pads to three with a repeat (the P-SV-2 exposure), BC lists
#: nothing, T repeats its own intent, A is well-formed.
LIVE_NOTES = {
    1: note("play_music", "play_radio", "play_music"),
    2: note(),
    3: note("play_music", "play_music"),
    4: note("play_music", "play_radio"),
}


def _run_live(tmp_path):
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        NativeEpisodeConfig,
        NativeEpisodeRole,
    )

    group = _live_group()
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=8, planner_actions=(),
    )
    harness.config = NativeEpisodeConfig(
        episode_id="native-role-runner-perception-branch-degenerate-v1",
        max_revisions=0, actions=ACTIONS,
        roles=tuple(
            NativeEpisodeRole(
                phase_id=phase, role_kind=phase,
                max_iterations=0 if phase in {"reviewer", "planner"} else 1,
                tool_names=(),
                perception_branches=(group if phase == "perception" else None),
            )
            for phase in PHASES
        ),
        max_contacts=8,
    )
    sample_id = harness.samples[0].sample_id
    harness.perception_branch_seeds = {
        "B3": {sample_id: (SEED_VALUE,)}, "BC": {sample_id: (SEED_VALUE,)},
    }
    harness.perception_contrast_pairs = {"BC": {}}

    def output(key):
        _sample_id, phase, visit, turn = key
        if phase == "perception":
            return LIVE_NOTES[turn]
        if phase == "solver":
            return f"solver-branch-{turn}-answer:{_sample_id}"
        return f"{phase}-analysis:{_sample_id}:visit:{visit}"

    harness._output = output
    return group, harness


def _write_trace(harness, directory: Path, records=None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{harness.plan.run_id}.trace.jsonl"
    lines = [
        json.dumps({"channel": channel, "record_id": record_id, "payload": payload},
                   ensure_ascii=False, sort_keys=True)
        for channel, record_id, payload in (
            harness.trace.records if records is None else records
        )
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_live_level2_degenerate_lists_seal_and_replay_equals_the_live_seal(tmp_path):
    group, harness = _run_live(tmp_path)
    try:
        summary = harness.run()
        (result,) = summary.results
        live = result.native_episode_receipt["perception_branches"]
        assert live["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA
        validate_perception_branch_receipt(
            live, branch_ids=group.branch_ids, delivered_branch_id="A", twin_branch_id="T",
            phase_id="perception", level=2,
        )
        rows = {row["branch_id"]: row for row in live["branches"]}
        assert (rows["B3"]["note_parse_status"], rows["B3"]["candidate_intent_ids"],
                rows["B3"]["candidate_intent_ids_raw_count"], rows["B3"]["min_candidates_met"]) == (
            "duplicates-collapsed", ["play_music", "play_radio"], 3, False,
        )
        assert (rows["BC"]["note_parse_status"], rows["BC"]["candidate_intent_ids"]) == ("empty", [])
        # The level-2 fold now carries the presentation outcome through (it sealed None/None).
        assert rows["BC"]["presentation_skip_reason"] == (
            TOP2_CONTRAST_SKIP_REASON_FEWER_THAN_TWO_CANDIDATES
        )
        assert rows["T"]["note_parse_status"] == "duplicates-collapsed"
        assert rows["A"]["note_parse_status"] == "ok"

        # The bundle's I7v over the live row and the harness's own trace.
        records = {}
        for channel, record_id, payload in harness.trace.records:
            if channel in {"MODEL_REQUEST", "MODEL_RESPONSE"}:
                records[record_id] = payload
        _verify_perception_branch_trace_binding(
            {"sample_id": result.sample_id,
             "native_episode_receipt": json.loads(json.dumps(result.native_episode_receipt))},
            records,
        )

        # Seal-only replay from the recorded trace equals the live seal.
        path = _write_trace(harness, tmp_path / "aborted")
        scan = read_predecessor_attempt(
            run_id=harness.plan.run_id, attempt_id="attempt-aborted", attempt_dir=path.parent,
            program_id=harness.program.program_id,
        )
        assert scan.incomplete == {}
        replayed = scan.complete[result.sample_id]
        assert json.dumps(replayed.native_episode_receipt, sort_keys=True) == json.dumps(
            json.loads(json.dumps(result.native_episode_receipt)), sort_keys=True,
        )
        assert replayed.final_response_text == result.final_response_text

        # A v1-lossy copy of the same trace (the shape P-SV-1 sealed) replays to the SAME block.
        lossy = copy.deepcopy(list(harness.trace.records))
        for channel, _record_id, payload in lossy:
            episode = payload.get("use_native_episode") if isinstance(payload, dict) else None
            if channel == "USE" and isinstance(episode, dict) and "perception_branches" in episode:
                block = episode["perception_branches"]
                block["schema"] = PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1
                for row in block["branches"]:
                    row.pop("candidate_intent_ids_raw_count")
                    row["presentation_skip_reason"] = None
                    row["min_candidates_met"] = None if row["min_candidates"] is None else True
                    row["note_parse_status"] = "ok"
                    row["candidate_intent_ids"] = ["x", "x"]
        lossy_path = _write_trace(harness, tmp_path / "lossy", lossy)
        lossy_scan = read_predecessor_attempt(
            run_id=harness.plan.run_id, attempt_id="attempt-lossy",
            attempt_dir=lossy_path.parent, program_id=harness.program.program_id,
        )
        assert lossy_scan.incomplete == {}
        assert json.dumps(
            lossy_scan.complete[result.sample_id].native_episode_receipt["perception_branches"],
            sort_keys=True,
        ) == json.dumps(json.loads(json.dumps(live)), sort_keys=True)

        # A branch contact missing from the trace: INCOMPLETE (re-flown), never approximated.
        branch_request = next(
            contact["request_id"]
            for visit in result.native_episode_receipt["role_visits"]
            if visit.get("role_id") == "perception"
            for contact in visit["execution_receipt"]["contacts"]
        )
        short = _write_trace(harness, tmp_path / "short", [
            record for record in lossy if record[1].split("/")[0] != branch_request
        ])
        short_scan = read_predecessor_attempt(
            run_id=harness.plan.run_id, attempt_id="attempt-short", attempt_dir=short.parent,
            program_id=harness.program.program_id,
        )
        assert short_scan.complete == {}
        assert result.sample_id in short_scan.incomplete
    finally:
        harness.close()


# ---------------------------------------------------------------------------
# 7. The read: an empty or malformed note is gold-absent; a repeat keeps its first rank.
# ---------------------------------------------------------------------------


def _read_module():
    import sys

    path = str(Path(__file__).resolve().parents[2] / "scripts" / "analysis")
    if path not in sys.path:
        sys.path.insert(0, path)
    import slurp_perception_branch_read as spbr

    return spbr


def _read_row(branches):
    return {
        "sample_id": "slurp:train:synthetic",
        "native_episode_receipt": {"perception_branches": {"branches": branches}},
    }


@pytest.mark.parametrize(
    ("item", "rank"),
    [
        ({"note_parse_status": "empty", "candidate_intent_ids": []}, None),
        ({"note_parse_status": "malformed", "candidate_intent_ids": []}, None),
        # v1 legacy sentinel: never read as an intent id.
        ({"note_parse_status": "malformed", "candidate_intent_ids": ["unparsed"]}, None),
        ({"note_parse_status": "duplicates-collapsed", "candidate_intent_ids": ["x", "gold"]}, 2),
        # v1 legacy duplicate: first occurrence keeps its rank.
        ({"note_parse_status": "ok", "candidate_intent_ids": ["gold", "gold", "x"]}, 1),
    ],
)
def test_read_treats_empty_and_malformed_as_gold_absent(item, rank):
    spbr = _read_module()
    outcomes = spbr.level1_row_outcomes(_read_row([{"branch_id": "B", **item}]), "gold")
    assert outcomes["B"] == {"rank": rank, "present": rank is not None, "top1": rank == 1}
    column = spbr.render_branch_column(_read_row([{"branch_id": "B", **item}]), "B")
    assert column["candidate_intent_ids"] == list(spbr.branch_candidates(item))
    assert column["note_parse_status"] == item["note_parse_status"]
