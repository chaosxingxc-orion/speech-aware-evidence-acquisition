"""Unit tests for the same-flight Perception-branch instrument's PRESENTATION
rendering and RESPONSE-CONTRACT sentence (design docs/superpowers/specs/
2026-09-28-same-flight-instrument-phase2-perception-variants-design.md
section 3, "What to build" items 1-4 of the P-SV-1/P-SV-2 defect fix): the
``top2-contrast-v1`` content-item render, the ``min_candidates`` sentence,
the contrast-pair table loader, and the parser/receipt coupling refusals the
two axes require.

No model, server, GPU or network contact anywhere in this file; synthetic
strings and ids only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_perception_branch_receipt,
)
from speech_aware_evidence_acquisition.rails.perception_presentations import (
    TOP2_CONTRAST_PRESENTATION_ID,
    TOP2_CONTRAST_SKIP_REASON_FEWER_THAN_TWO_CANDIDATES,
    TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT,
    branch_supplied_intent_ids,
)
from speech_aware_evidence_acquisition.rails.runner import (
    _perception_branch_min_candidates_sentence,
    _render_perception_branch_presentation,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    PerceptionBranchError,
    parse_perception_branches,
    perception_branch_record,
)

FIT = {
    "slot_tokens": 24576,
    "completion_ceiling": 512,
    "base_prompt_tokens": 4000,
    "tokens_per_supplied_item": 100,
}
STORE = "intent-boundaries"
CONTRAST_PIN = {
    "relpath": "prepared/SAEA-TEST-PERCEPTION-CONTRAST-PAIRS-V1/table.json",
    "sha256": "a" * 64,
}
INTENT_X = "general_quirky"
INTENT_Y = "play_music"
VALUE_X = f"{STORE}::intent-boundary:{INTENT_X}"
VALUE_Y = f"{STORE}::intent-boundary:{INTENT_Y}"


def _a():
    return {"branch_id": "A", "deliver": True, "max_supplied_items": 8}


def _t():
    return {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8}


def _b_contrast(contrast_pairs=CONTRAST_PIN, presentation_id=TOP2_CONTRAST_PRESENTATION_ID):
    """A valid ``b-top2contrast``-shaped branch row by default; pass
    ``contrast_pairs=None`` to omit the pin (for a refusal test)."""

    row = {"branch_id": "B", "max_supplied_items": 8}
    if presentation_id is not None:
        row["presentation_id"] = presentation_id
    if contrast_pairs is not None:
        row["contrast_pairs"] = dict(contrast_pairs)
    return row


def _group(
    branches, *, level=1, max_candidates_ceiling=None,
    top2_contrast_presentation_id=TOP2_CONTRAST_PRESENTATION_ID,
):
    return parse_perception_branches(
        {"level": level, "fit_estimate": dict(FIT), "branches": branches},
        first_phase_id="perception", declared_stores=(STORE,),
        registered_presentation_ids=(TOP2_CONTRAST_PRESENTATION_ID, "rank-visible-v1"),
        max_candidates_ceiling=max_candidates_ceiling,
        top2_contrast_presentation_id=top2_contrast_presentation_id,
    )


# ---------------------------------------------------------------------------
# (e) parser refusals: the contrast_pairs <-> presentation_id coupling.
# ---------------------------------------------------------------------------


def test_top2_contrast_without_contrast_pairs_is_refused():
    with pytest.raises(PerceptionBranchError, match="must carry a contrast_pairs pin"):
        _group([_b_contrast(contrast_pairs=None), _t(), _a()])


def test_contrast_pairs_on_a_non_contrast_branch_is_refused():
    with pytest.raises(PerceptionBranchError, match="presentation_id is not"):
        _group(
            [
                {
                    "branch_id": "B", "max_supplied_items": 8, "min_candidates": 2,
                    "contrast_pairs": dict(CONTRAST_PIN),
                },
                _t(), _a(),
            ],
            max_candidates_ceiling=3,
        )


def test_contrast_pairs_on_a_bare_branch_is_refused():
    """No presentation_id at all (not even a different one): still refused."""

    with pytest.raises(PerceptionBranchError, match="presentation_id is not"):
        _group(
            [_b_contrast(contrast_pairs=CONTRAST_PIN, presentation_id=None), _t(), _a()],
        )


def test_coupling_check_is_opt_in():
    """Omitting ``top2_contrast_presentation_id`` (like ``registered_presentation_ids``
    when omitted) gets shape checking only -- no coupling enforcement."""

    group = _group(
        [_b_contrast(), _t(), _a()], top2_contrast_presentation_id=None,
    )
    assert group.branch("B").contrast_pairs == CONTRAST_PIN


@pytest.mark.parametrize("mutate", [
    lambda pin: {**pin, "sha256": "not-hex"},
    lambda pin: {**pin, "sha256": "a" * 63},
    lambda pin: {**pin, "relpath": ""},
    lambda pin: {"relpath": pin["relpath"]},
    lambda pin: {**pin, "extra": "field"},
])
def test_malformed_contrast_pairs_pin_is_refused(mutate):
    with pytest.raises(PerceptionBranchError, match="contrast_pairs"):
        _group([_b_contrast(contrast_pairs=mutate(CONTRAST_PIN)), _t(), _a()])


def test_a_and_t_may_not_carry_contrast_pairs():
    a_row = _a()
    a_row["contrast_pairs"] = dict(CONTRAST_PIN)
    with pytest.raises(PerceptionBranchError, match="A or its twin"):
        _group([_b_contrast(), _t(), a_row], top2_contrast_presentation_id=None)
    t_row = _t()
    t_row["contrast_pairs"] = dict(CONTRAST_PIN)
    with pytest.raises(PerceptionBranchError, match="A or its twin"):
        _group([_b_contrast(), t_row, _a()], top2_contrast_presentation_id=None)


def test_contrast_pairs_defaults_to_none_and_round_trips_as_json():
    group = _group([_b_contrast(), _t(), _a()])
    branch = group.branch("B")
    assert branch.contrast_pairs == CONTRAST_PIN
    assert branch.as_json()["contrast_pairs"] == CONTRAST_PIN
    assert group.branch("A").contrast_pairs is None
    assert group.branch("T").contrast_pairs is None


def test_min_candidates_branch_still_parses_beside_the_new_axis():
    group = _group(
        [{"branch_id": "B", "max_supplied_items": 8, "min_candidates": 2}, _t(), _a()],
        max_candidates_ceiling=3,
    )
    assert group.branch("B").min_candidates == 2
    assert group.branch("B").contrast_pairs is None


# ---------------------------------------------------------------------------
# branch_supplied_intent_ids (pure derivation over rendered supply).
# ---------------------------------------------------------------------------


def test_branch_supplied_intent_ids_extracts_first_two_distinct():
    assert branch_supplied_intent_ids((VALUE_X, VALUE_Y)) == (INTENT_X, INTENT_Y)


def test_branch_supplied_intent_ids_stops_at_two_and_skips_duplicates():
    assert branch_supplied_intent_ids((VALUE_X, VALUE_X, VALUE_Y, "other::intent-boundary:z")) == (
        INTENT_X, INTENT_Y,
    )


def test_branch_supplied_intent_ids_ignores_non_intent_boundary_values():
    assert branch_supplied_intent_ids(("value:dim-light", VALUE_X)) == (INTENT_X,)


def test_branch_supplied_intent_ids_skips_shared_guidance_sentinel():
    sentinel = f"{STORE}::intent-boundary:shared-guidance"
    assert branch_supplied_intent_ids((sentinel, VALUE_X, VALUE_Y)) == (INTENT_X, INTENT_Y)


def test_branch_supplied_intent_ids_empty_when_fewer_than_one():
    assert branch_supplied_intent_ids(()) == ()
    assert branch_supplied_intent_ids((VALUE_X,)) == (INTENT_X,)


# ---------------------------------------------------------------------------
# (b) _render_perception_branch_presentation: renders, or skips with a reason.
# ---------------------------------------------------------------------------


def test_render_presentation_returns_none_none_for_a_non_presentation_branch():
    group = _group([{"branch_id": "B", "max_supplied_items": 8, "min_candidates": 2}, _t(), _a()], max_candidates_ceiling=3)
    item, reason = _render_perception_branch_presentation(
        branch=group.branch("B"), supplied_value_ids=(VALUE_X, VALUE_Y), contrast_pairs=None,
    )
    assert item is None and reason is None


def test_render_presentation_skips_fewer_than_two_candidates():
    group = _group([_b_contrast(), _t(), _a()])
    item, reason = _render_perception_branch_presentation(
        branch=group.branch("B"), supplied_value_ids=(VALUE_X,), contrast_pairs={},
    )
    assert item is None
    assert reason == TOP2_CONTRAST_SKIP_REASON_FEWER_THAN_TWO_CANDIDATES


def test_render_presentation_skips_absent_pair():
    group = _group([_b_contrast(), _t(), _a()])
    item, reason = _render_perception_branch_presentation(
        branch=group.branch("B"), supplied_value_ids=(VALUE_X, VALUE_Y), contrast_pairs={},
    )
    assert item is None
    assert reason == TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT


def test_render_presentation_renders_exactly_one_item():
    group = _group([_b_contrast(), _t(), _a()])
    table = {
        frozenset({INTENT_X, INTENT_Y}): {
            "activation_sentence": "Pick X when the utterance names a light.",
            "exclusion_sentence": "Pick Y otherwise.",
        },
    }
    item, reason = _render_perception_branch_presentation(
        branch=group.branch("B"), supplied_value_ids=(VALUE_X, VALUE_Y), contrast_pairs=table,
    )
    assert reason is None
    assert item["type"] == "text"
    assert item["knowledge_role"] == "value"
    assert item["text"] == (
        "Pick X when the utterance names a light.\nPick Y otherwise."
    )
    assert item["evidence_id"] == "perception-branch-presentation:B"
    assert item["source_uri"] == "perception-branch-presentation://top2-contrast-v1/B"


def test_render_presentation_is_order_independent_on_the_pair_key():
    """The rank-1/rank-2 order at the CALL SITE may differ from the table's
    own row order; the pair identifies the contrast, not which one ranked
    first (module docstring)."""

    group = _group([_b_contrast(), _t(), _a()])
    table = {
        frozenset({INTENT_X, INTENT_Y}): {
            "activation_sentence": "A.", "exclusion_sentence": "B.",
        },
    }
    forward, _ = _render_perception_branch_presentation(
        branch=group.branch("B"), supplied_value_ids=(VALUE_X, VALUE_Y), contrast_pairs=table,
    )
    backward, _ = _render_perception_branch_presentation(
        branch=group.branch("B"), supplied_value_ids=(VALUE_Y, VALUE_X), contrast_pairs=table,
    )
    assert forward["text"] == backward["text"]


# ---------------------------------------------------------------------------
# (d) min_candidates response-contract sentence.
# ---------------------------------------------------------------------------


def test_min_candidates_sentence_none_when_undeclared():
    group = _group([_b_contrast(), _t(), _a()])
    assert _perception_branch_min_candidates_sentence(group.branch("B")) is None
    assert _perception_branch_min_candidates_sentence(group.branch("A")) is None
    assert _perception_branch_min_candidates_sentence(group.branch("T")) is None


def test_min_candidates_sentence_states_both_bounds():
    group = _group(
        [{"branch_id": "B", "max_supplied_items": 8, "min_candidates": 2}, _t(), _a()],
        max_candidates_ceiling=3,
    )
    item = _perception_branch_min_candidates_sentence(group.branch("B"))
    assert item["type"] == "text"
    assert item["knowledge_role"] == "value"
    assert "at least 2" in item["text"] and "at most 3" in item["text"]
    assert item["evidence_id"] == "perception-branch-contract:B"


# ---------------------------------------------------------------------------
# (f) receipt: perception_branch_record accepts and shapes the new fields.
# ---------------------------------------------------------------------------

SHA = "c" * 64


def test_perception_branch_record_carries_the_new_fields_default_none():
    group = _group([_b_contrast(), _t(), _a()])
    record = perception_branch_record(
        branch=group.branch("A"), branch_index=2, contact_id="c2",
        request_sha256=SHA, response_text_sha256=SHA, note_sha256=SHA,
        note_parse_status="ok", candidate_intent_ids=("intent_a",),
        supplied_value_ids=("v1",),
    )
    assert record["presentation_skip_reason"] is None
    assert record["contrast_block_sha256"] is None
    assert record["min_candidates_met"] is None


def test_perception_branch_record_accepts_a_rendered_contrast_block():
    group = _group([_b_contrast(), _t(), _a()])
    record = perception_branch_record(
        branch=group.branch("B"), branch_index=0, contact_id="c0",
        request_sha256=SHA, response_text_sha256=SHA, note_sha256=SHA,
        note_parse_status="ok", candidate_intent_ids=("intent_a", "intent_b"),
        supplied_value_ids=("v1", "v2"), contrast_block_sha256=SHA,
    )
    assert record["contrast_block_sha256"] == SHA
    assert record["presentation_skip_reason"] is None


def test_perception_branch_record_refuses_both_skip_reason_and_block():
    group = _group([_b_contrast(), _t(), _a()])
    with pytest.raises(PerceptionBranchError, match="cannot carry both"):
        perception_branch_record(
            branch=group.branch("B"), branch_index=0, contact_id="c0",
            request_sha256=SHA, response_text_sha256=SHA, note_sha256=SHA,
            note_parse_status="ok", candidate_intent_ids=("intent_a",),
            supplied_value_ids=("v1",),
            contrast_block_sha256=SHA,
            presentation_skip_reason=TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT,
        )


def test_perception_branch_record_requires_min_candidates_met_bool_when_declared():
    group = _group(
        [{"branch_id": "B", "max_supplied_items": 8, "min_candidates": 2}, _t(), _a()],
        max_candidates_ceiling=3,
    )
    with pytest.raises(PerceptionBranchError, match="min_candidates_met"):
        perception_branch_record(
            branch=group.branch("B"), branch_index=0, contact_id="c0",
            request_sha256=SHA, response_text_sha256=SHA, note_sha256=SHA,
            note_parse_status="ok", candidate_intent_ids=("intent_a",),
            supplied_value_ids=("v1",),
        )
    record = perception_branch_record(
        branch=group.branch("B"), branch_index=0, contact_id="c0",
        request_sha256=SHA, response_text_sha256=SHA, note_sha256=SHA,
        note_parse_status="ok", candidate_intent_ids=("intent_a",),
        supplied_value_ids=("v1",), min_candidates_met=False,
    )
    assert record["min_candidates_met"] is False


def test_perception_branch_record_refuses_presentation_outcome_without_presentation_id():
    group = _group([_b_contrast(), _t(), _a()])
    with pytest.raises(PerceptionBranchError, match="declares no presentation_id"):
        perception_branch_record(
            branch=group.branch("A"), branch_index=2, contact_id="c2",
            request_sha256=SHA, response_text_sha256=SHA, note_sha256=SHA,
            note_parse_status="ok", candidate_intent_ids=("intent_a",),
            supplied_value_ids=("v1",),
            presentation_skip_reason=TOP2_CONTRAST_SKIP_REASON_FEWER_THAN_TWO_CANDIDATES,
        )


def _sealed_receipt_with_new_fields(group):
    from speech_aware_evidence_acquisition.rails.supply_variants import perception_branch_receipt

    records = []
    for index, branch in enumerate(group.branches):
        kwargs = dict(
            branch=branch, branch_index=index, contact_id=f"c{index}",
            request_sha256=SHA, response_text_sha256=SHA, note_sha256=SHA,
            note_parse_status="ok", candidate_intent_ids=("intent_a", "intent_b"),
            supplied_value_ids=(VALUE_X, VALUE_Y),
        )
        if branch.branch_id == "B":
            kwargs["contrast_block_sha256"] = SHA
        records.append(perception_branch_record(**kwargs))
    return perception_branch_receipt(group=group, phase_id="perception", records=records)


def test_receipt_validator_accepts_the_new_fields():
    group = _group([_b_contrast(), _t(), _a()])
    receipt = _sealed_receipt_with_new_fields(group)
    validate_perception_branch_receipt(
        receipt, branch_ids=group.branch_ids, delivered_branch_id="A",
        twin_branch_id="T", phase_id="perception", level=1,
    )


def test_receipt_validator_refuses_a_and_t_carrying_a_presentation_outcome():
    group = _group([_b_contrast(), _t(), _a()])
    receipt = _sealed_receipt_with_new_fields(group)
    # Sneak a presentation outcome onto A (the delivering branch), which the
    # parser itself would never emit -- this receipt-level check is the
    # second, independent rail over the sealed bytes.
    for row in receipt["branches"]:
        if row["branch_id"] == "A":
            row["contrast_block_sha256"] = SHA
            row["presentation_id"] = TOP2_CONTRAST_PRESENTATION_ID
    with pytest.raises(ValueError, match="must declare no axis"):
        validate_perception_branch_receipt(
            receipt, branch_ids=group.branch_ids, delivered_branch_id="A",
            twin_branch_id="T", phase_id="perception", level=1,
        )


# ---------------------------------------------------------------------------
# (c) FlightRuntime loads and verifies the contrast-pair table, once per
# flight, fail-closed on a SHA-256 mismatch.
# ---------------------------------------------------------------------------


def _table_document(rows):
    return {
        "schema": "saea-slurp-perception-contrast-pairs-v1",
        "artifact_id": "SAEA-TEST-PERCEPTION-CONTRAST-PAIRS-V1",
        "builder_id": "saea-test-perception-contrast-pairs-v1",
        "builder": {"relpath": "scripts/build_slurp_intent_contrast_pairs.py", "sha256": "b" * 64},
        "min_pair_pool_support": 5,
        "rows": rows,
    }


def _write_table(data_root: Path, rows) -> dict:
    relpath = "prepared/SAEA-TEST-PERCEPTION-CONTRAST-PAIRS-V1/table.json"
    path = data_root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_table_document(rows), sort_keys=True).encode("utf-8")
    path.write_bytes(payload)
    return {"relpath": relpath, "sha256": hashlib.sha256(payload).hexdigest()}


def _runtime_stub(data_root: Path):
    return SimpleNamespace(_data_root=data_root)


def test_load_contrast_pairs_table_round_trips_the_pinned_rows(tmp_path):
    pin = _write_table(tmp_path, {
        f"{INTENT_X}|{INTENT_Y}": {
            "intents": [INTENT_X, INTENT_Y],
            "activation_sentence": "Pick X.",
            "exclusion_sentence": "Pick Y.",
        },
    })
    table = FlightRuntime._load_perception_contrast_pairs_table(_runtime_stub(tmp_path), pin)
    assert table[frozenset({INTENT_X, INTENT_Y})] == {
        "activation_sentence": "Pick X.", "exclusion_sentence": "Pick Y.",
    }


def test_load_contrast_pairs_table_refuses_a_sha256_mismatch(tmp_path):
    pin = _write_table(tmp_path, {})
    tampered = {**pin, "sha256": "0" * 64}
    with pytest.raises(FlightRuntimeError, match="SHA-256 mismatch"):
        FlightRuntime._load_perception_contrast_pairs_table(_runtime_stub(tmp_path), tampered)


def test_load_contrast_pairs_table_refuses_a_malformed_row(tmp_path):
    pin = _write_table(tmp_path, {
        "bad": {"intents": [INTENT_X, INTENT_X], "activation_sentence": "x", "exclusion_sentence": "y"},
    })
    with pytest.raises(FlightRuntimeError, match="invalid intent pair"):
        FlightRuntime._load_perception_contrast_pairs_table(_runtime_stub(tmp_path), pin)


def test_load_contrast_pairs_table_refuses_an_unregistered_schema(tmp_path):
    relpath = "prepared/SAEA-TEST-PERCEPTION-CONTRAST-PAIRS-V1/bad-schema.json"
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"schema": "not-the-real-one", "rows": {}}, sort_keys=True).encode("utf-8")
    path.write_bytes(payload)
    pin = {"relpath": relpath, "sha256": hashlib.sha256(payload).hexdigest()}
    with pytest.raises(FlightRuntimeError, match="unregistered schema"):
        FlightRuntime._load_perception_contrast_pairs_table(_runtime_stub(tmp_path), pin)


def test_contrast_pairs_for_group_loads_once_and_caches_by_pin(tmp_path):
    pin = _write_table(tmp_path, {
        f"{INTENT_X}|{INTENT_Y}": {
            "intents": [INTENT_X, INTENT_Y],
            "activation_sentence": "Pick X.", "exclusion_sentence": "Pick Y.",
        },
    })
    group = _group([_b_contrast(contrast_pairs=pin), _t(), _a()])
    runtime = _runtime_stub(tmp_path)
    calls = []

    def counting_loader(loaded_pin):
        calls.append(loaded_pin)
        return FlightRuntime._load_perception_contrast_pairs_table(runtime, loaded_pin)

    # An INSTANCE attribute (a plain function, not a bound method) shadows
    # the class method only for this stub -- no class-level monkeypatching
    # of ``FlightRuntime`` itself, which other tests in this process share.
    runtime._load_perception_contrast_pairs_table = counting_loader
    tables = FlightRuntime._perception_contrast_pairs_for_group(runtime, group)
    assert set(tables) == {"B"}
    assert tables["B"][frozenset({INTENT_X, INTENT_Y})]["activation_sentence"] == "Pick X."
    assert len(calls) == 1


def test_contrast_pairs_for_group_empty_when_no_branch_declares_one():
    group = _group(
        [{"branch_id": "B", "max_supplied_items": 8, "min_candidates": 2}, _t(), _a()],
        max_candidates_ceiling=3,
    )
    runtime = _runtime_stub(Path("."))
    assert FlightRuntime._perception_contrast_pairs_for_group(runtime, group) == {}
