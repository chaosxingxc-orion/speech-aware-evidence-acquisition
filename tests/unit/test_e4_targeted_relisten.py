"""E4 v1: core-native targeted re-listen (owner decision 185).

Design: docs/superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-
design.md (sections 1, 4, 6, and the section 8 coordinator rulings).
Node-gain motivation: docs/results/2026-09-28-slurp-node-information-gain-
ledger.md sections 4-5.

Every test here is model-free: synthetic episodes and synthetic response
text only, no model, server, network or GPU contact, and no utterance text,
transcript, gold label or model output is printed or persisted.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.bundle import outputs as bundle_outputs
from speech_aware_evidence_acquisition.rails import relisten as rl
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)

ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT
_CHECKS = ROOT / "scripts" / "checks"
if str(_CHECKS) not in sys.path:
    sys.path.insert(0, str(_CHECKS))

import stage3_effect_floor_check as floor_mod  # noqa: E402
import flight_registration_check as reg_mod  # noqa: E402

_score_spec = importlib.util.spec_from_file_location(
    "stage3_rollout_score", ROOT / "scripts/analysis/stage3_rollout_score.py"
)
score_mod = importlib.util.module_from_spec(_score_spec)
sys.modules.setdefault("stage3_rollout_score", score_mod)
_score_spec.loader.exec_module(score_mod)


# ---------------------------------------------------------------------------
# 1. blind-then-choice ordering / forced choice fires on differ and on unheard
# ---------------------------------------------------------------------------


def test_confirm_never_fires_on_an_exact_heard_match():
    blind = rl.parse_blind_response(json.dumps({"heard": True, "value": "seven pm"}))
    assert blind.disposition == rl.BLIND_VALUE
    assert rl.should_fire_confirm(blind, "7 pm") is False  # canonical match via P2


def test_confirm_fires_on_a_genuine_value_disagreement():
    blind = rl.parse_blind_response(json.dumps({"heard": True, "value": "eight pm"}))
    assert rl.should_fire_confirm(blind, "7 pm") is True


def test_confirm_fires_on_unheard_so_both_contacts_vote():
    blind = rl.parse_blind_response(json.dumps({"heard": False, "value": ""}))
    assert blind.disposition == rl.BLIND_UNHEARD
    assert rl.should_fire_confirm(blind, "7 pm") is True


def test_confirm_never_fires_on_an_over_length_or_empty_value():
    over_length = rl.parse_blind_response(
        json.dumps({"heard": True, "value": " ".join(["word"] * 9)})
    )
    assert over_length.disposition == rl.BLIND_INVALID_LENGTH
    assert rl.should_fire_confirm(over_length, "7 pm") is False

    empty = rl.parse_blind_response(json.dumps({"heard": True, "value": "   "}))
    assert empty.disposition == rl.BLIND_INVALID_LENGTH
    assert rl.should_fire_confirm(empty, "7 pm") is False


def test_blind_contact_is_composed_and_parsed_before_any_confirm_decision():
    """Ordering: a caller can only know whether to fire the confirm contact
    (or what to present it) after the blind response is parsed -- confirm
    firing and its two options are pure functions OF the parsed blind
    result, never of anything decided in parallel with it."""

    order_of_operations: list[str] = []

    def fake_blind_contact() -> str:
        order_of_operations.append("blind")
        return json.dumps({"heard": True, "value": "eight pm"})

    blind = rl.parse_blind_response(fake_blind_contact())
    if rl.should_fire_confirm(blind, "7 pm"):
        order_of_operations.append("confirm")
    assert order_of_operations == ["blind", "confirm"]


# ---------------------------------------------------------------------------
# 2. no current value in the blind prompt
# ---------------------------------------------------------------------------


def test_blind_template_carries_no_delivered_value_placeholder():
    text = (REPO_ROOT / "configs/probes/slurp_relisten_blind_v1.txt").read_text(encoding="utf-8")
    assert "{slot_type}" in text and "{intent}" in text
    # No placeholder for the delivered/current value could exist in this
    # template at all -- the only two substitution points are slot type and
    # intent (section 1: "not c").
    for forbidden in ("{value}", "{current}", "{delivered", "{filler}", "{c}"):
        assert forbidden not in text


def test_parse_blind_response_signature_takes_no_delivered_value():
    """Structural guarantee: the blind parser -- and therefore whatever
    composed its prompt -- has no parameter through which a delivered value
    could reach it."""

    import inspect

    params = inspect.signature(rl.parse_blind_response).parameters
    assert "delivered_value" not in params
    assert "current" not in params


# ---------------------------------------------------------------------------
# 3. receipts sealed
# ---------------------------------------------------------------------------


def _record(
    index=0, slot_type="time", *, disposition=rl.BLIND_VALUE, value="eight pm",
    confirm_letter=None, order=None, delivered_value="7 pm",
):
    blind = rl.BlindResult(disposition, value if disposition != rl.BLIND_UNHEARD else None,
                            len(value.split()) if value else 0)
    kwargs = {}
    if confirm_letter is not None:
        kwargs["confirm_contact_id"] = f"confirm-{index}"
    return rl.decide_entity(
        index=index, slot_type=slot_type, delivered_value=delivered_value,
        blind=blind, blind_contact_id=f"blind-{index}",
        confirm_letter=confirm_letter, order=order, **kwargs,
    )


def test_seal_relisten_receipt_shape_and_contact_accounting():
    order = rl.confirm_order("sample-1", "time")
    accepted = _record(0, confirm_letter=("A" if order[0] == rl.CONFIRM_CANDIDATE else "B"), order=order)
    skipped = rl.decide_entity(
        index=1, slot_type="place_name", delivered_value="paris",
        blind=rl.BlindResult(rl.BLIND_VALUE, "paris", 1), blind_contact_id="blind-1",
        confirm_letter=None, order=None,
    )
    receipt = rl.seal_relisten_receipt([accepted, skipped], max_slots_per_row=3)
    assert receipt["schema"] == rl.RELISTEN_RECEIPT_SCHEMA
    assert receipt["policy"] == rl.RELISTEN_POLICY_ID
    assert receipt["triggered_count"] == 2
    # one blind for each of the two triggered entities, plus one confirm for
    # the entity whose blind disagreed with the delivered value.
    assert receipt["contacts_used"] == 3
    assert [entity["index"] for entity in receipt["entities"]] == [0, 1]
    assert accepted.accept is True
    assert receipt["entities"][0]["accept"] is True
    assert receipt["entities"][0]["blind"]["contact_id"] == "blind-0"
    assert receipt["entities"][0]["confirm"]["contact_id"] == "confirm-0"
    # never the value's own bytes, only hashes and flags.
    assert "eight pm" not in json.dumps(receipt)
    assert receipt["entities"][0]["blind"]["value_sha256"] == hashlib.sha256(
        b"eight pm"
    ).hexdigest()


def test_seal_relisten_receipt_refuses_more_records_than_the_declared_cap():
    records = [_record(i) for i in range(4)]
    with pytest.raises(rl.RelistenError, match="max_slots_per_row"):
        rl.seal_relisten_receipt(records, max_slots_per_row=3)


# ---------------------------------------------------------------------------
# 4. delivered answer unchanged (shadow delivery)
# ---------------------------------------------------------------------------


def test_bind_shadow_entities_never_mutates_the_delivered_entities_input():
    delivered = [{"type": "time", "filler": "7 pm"}, {"type": "place_name", "filler": "paris"}]
    delivered_copy = [dict(e) for e in delivered]
    order = rl.confirm_order("sample-1", "time")
    letter_for_candidate = "A" if order[0] == rl.CONFIRM_CANDIDATE else "B"
    accepted = _record(0, confirm_letter=letter_for_candidate, order=order)
    receipt = rl.seal_relisten_receipt([accepted], max_slots_per_row=3)
    rl.bind_shadow_entities(delivered, receipt, bound_values={0: "eight pm"})
    assert delivered == delivered_copy  # the caller's own delivered list is untouched


# ---------------------------------------------------------------------------
# 5. shadow columns (a)/(b) reconstruction
# ---------------------------------------------------------------------------


def test_column_a_replaces_only_on_accept():
    delivered = [{"type": "time", "filler": "7 pm"}, {"type": "place_name", "filler": "paris"}]
    order = rl.confirm_order("sample-1", "time")
    letter_for_candidate = "A" if order[0] == rl.CONFIRM_CANDIDATE else "B"
    accepted = _record(0, confirm_letter=letter_for_candidate, order=order)
    unaccepted = rl.decide_entity(
        index=1, slot_type="place_name", delivered_value="paris",
        blind=rl.BlindResult(rl.BLIND_VALUE, "paris", 1), blind_contact_id="blind-1",
        confirm_letter=None, order=None,
    )
    receipt = rl.seal_relisten_receipt([accepted, unaccepted], max_slots_per_row=3)
    column_a, column_b = rl.bind_shadow_entities(
        delivered, receipt, bound_values={0: "eight pm"},
    )
    assert column_a == [{"type": "time", "filler": "eight pm"}, {"type": "place_name", "filler": "paris"}]
    assert column_b == column_a  # nothing unheard here, so (b) drops nothing


def test_column_b_drops_only_when_both_contacts_vote_unheard():
    delivered = [{"type": "time", "filler": "7 pm"}, {"type": "place_name", "filler": "paris"}]
    order = rl.confirm_order("sample-1", "time")
    unheard_letter_for_unheard_vote = "A" if order[0] == rl.CONFIRM_CANDIDATE else "B"
    blind = rl.BlindResult(rl.BLIND_UNHEARD, None, 0)
    dropped = rl.decide_entity(
        index=0, slot_type="time", delivered_value="7 pm", blind=blind,
        blind_contact_id="blind-0", confirm_letter=unheard_letter_for_unheard_vote,
        order=order, confirm_contact_id="confirm-0",
    )
    assert dropped.confirm_unheard_vote is True
    assert dropped.accept is False  # v1 never manufactures a value from a non-value blind
    kept = rl.decide_entity(
        index=1, slot_type="place_name", delivered_value="paris",
        blind=rl.BlindResult(rl.BLIND_VALUE, "paris", 1), blind_contact_id="blind-1",
        confirm_letter=None, order=None,
    )
    receipt = rl.seal_relisten_receipt([dropped, kept], max_slots_per_row=3)
    column_a, column_b = rl.bind_shadow_entities(delivered, receipt)
    assert column_a == delivered  # (a) never deletes an entity
    assert column_b == [{"type": "place_name", "filler": "paris"}]


def test_column_b_keeps_an_unheard_entity_when_confirm_disagrees():
    """The confirm contact contradicting the blind (choosing the delivered
    slot) is a vote AGAINST 'unheard': no drop."""

    delivered = [{"type": "time", "filler": "7 pm"}]
    order = rl.confirm_order("sample-1", "time")
    letter_for_delivered = "A" if order[0] == rl.CONFIRM_DELIVERED else "B"
    record = rl.decide_entity(
        index=0, slot_type="time", delivered_value="7 pm",
        blind=rl.BlindResult(rl.BLIND_UNHEARD, None, 0), blind_contact_id="blind-0",
        confirm_letter=letter_for_delivered, order=order, confirm_contact_id="confirm-0",
    )
    assert record.confirm_unheard_vote is False
    receipt = rl.seal_relisten_receipt([record], max_slots_per_row=3)
    column_a, column_b = rl.bind_shadow_entities(delivered, receipt)
    assert column_a == column_b == delivered


# ---------------------------------------------------------------------------
# 6. AT1 check (render_relisten_shadow_columns)
# ---------------------------------------------------------------------------


def _trace_contact(trace, contact_id, raw_text):
    trace[f"{contact_id}/response"] = {
        "text": raw_text, "response_text_sha256": hashlib.sha256(raw_text.encode()).hexdigest(),
    }


def _bundle(tmp_path, rows, trace):
    manifest_path = tmp_path / "runs" / "RUN" / "ATT" / "RUN.manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{}")
    ids = tuple(row["sample_id"] for row in rows)
    return SimpleNamespace(
        manifest={"status": "COMPLETED", "run_id": "RUN",
                  "config": {"config_hash": "c" * 64},
                  "outputs": {"sha256": "d" * 64}, "raw_trace": {"sha256": "e" * 64},
                  "scores": {"sha256": "f" * 64}},
        attempt_state="FINALIZED", manifest_path=manifest_path,
        split_ids=frozenset(ids), outputs_rows=tuple(rows), trace_records=trace,
    )


@pytest.fixture(autouse=True)
def _stub_delivery(monkeypatch):
    from speech_aware_evidence_acquisition.rails import native_episode_receipt
    monkeypatch.setattr(
        native_episode_receipt, "validate_native_episode_delivery_receipt",
        lambda episode, **_kwargs: SimpleNamespace(kind=episode.get("kind", "accepted")),
    )


def test_render_relisten_shadow_columns_no_receipt_row_is_at1_by_construction(tmp_path):
    text = json.dumps({"scenario": "alarm", "action": "set", "entities": []})
    row = {"sample_id": "s1", "text": text, "native_episode_receipt": {"kind": "accepted"},
           "relisten": None}
    bundle = _bundle(tmp_path, [row], {})
    manifest = score_mod.render_relisten_shadow_columns(
        bundle, {"s1": "alarm"}, tmp_path / "analysis",
        run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64,
    )
    assert manifest["at1_column_reproduction_checked_rows"] == 2
    for name in rl.SHADOW_COLUMNS:
        rows = list(score_mod.iter_jsonl(Path(manifest["copies"][name]["path"])))
        assert rows[0]["text"] == text


def test_render_relisten_shadow_columns_keeps_a_non_canonical_sealed_text_when_nothing_binds(tmp_path):
    """AT1 on a natively committed answer: the sealed text is the core's own
    compact JSON (key order scenario/action/entities), not the sorted-key
    canonical render. A row whose receipt accepted nothing keeps that text
    byte for byte in both columns (E4-1 read, 2026-09-29)."""
    text = json.dumps(
        {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "7 pm"}]},
        separators=(",", ":"),
    )
    assert text != score_mod.render_answer(json.loads(text))
    order = rl.confirm_order("s1", "time")
    heard_same = rl.decide_entity(
        index=0, slot_type="time", delivered_value="7 pm",
        blind=rl.BlindResult(rl.BLIND_UNHEARD, None, 0), blind_contact_id="blind-0",
        confirm_letter=("B" if order[0] == rl.CONFIRM_CANDIDATE else "A"),
        order=order, confirm_contact_id="confirm-0",
    )
    assert heard_same.accept is False
    receipt = rl.seal_relisten_receipt([heard_same], max_slots_per_row=3)
    row = {"sample_id": "s1", "text": text, "native_episode_receipt": {"kind": "accepted"},
           "relisten": receipt}
    bundle = _bundle(tmp_path, [row], {})
    manifest = score_mod.render_relisten_shadow_columns(
        bundle, {"s1": "alarm"}, tmp_path / "analysis",
        run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64,
    )
    a_rows = list(score_mod.iter_jsonl(Path(manifest["copies"][rl.COLUMN_REPLACE_ONLY]["path"])))
    assert a_rows[0]["text"] == text
    assert manifest["at1_column_reproduction_checked_rows"] >= 1
    b_rows = list(score_mod.iter_jsonl(Path(manifest["copies"][rl.COLUMN_REPLACE_DROP_UNHEARD]["path"])))
    if heard_same.dropped_when_unheard:
        assert json.loads(b_rows[0]["text"])["entities"] == []
    else:
        assert b_rows[0]["text"] == text


def test_render_relisten_shadow_columns_reads_a_kept_row_contact_from_its_predecessor(tmp_path):
    """A seal-only completion's own trace is empty; the kept row's blind
    contact is read from that row's own verified predecessor trace."""
    pred_trace = {}
    _trace_contact(pred_trace, "blind-0", json.dumps({"heard": True, "value": "eight pm"}))
    text = json.dumps({"scenario": "alarm", "action": "set",
                       "entities": [{"type": "time", "filler": "7 pm"}]})
    order = rl.confirm_order("s1", "time")
    accepted = rl.decide_entity(
        index=0, slot_type="time", delivered_value="7 pm",
        blind=rl.parse_blind_response(pred_trace["blind-0/response"]["text"]),
        blind_contact_id="blind-0",
        confirm_letter=("A" if order[0] == rl.CONFIRM_CANDIDATE else "B"),
        order=order, confirm_contact_id="confirm-0",
    )
    receipt = rl.seal_relisten_receipt([accepted], max_slots_per_row=3)
    row = {"sample_id": "s1", "text": text, "native_episode_receipt": {"kind": "accepted"},
           "relisten": receipt}
    kwargs = dict(run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64)
    with pytest.raises(score_mod.Stage3ScoreError, match="no sealed blind trace"):
        score_mod.render_relisten_shadow_columns(
            _bundle(tmp_path / "a", [row], {}), {"s1": "alarm"}, tmp_path / "a" / "out", **kwargs)
    manifest = score_mod.render_relisten_shadow_columns(
        _bundle(tmp_path / "b", [row], {}), {"s1": "alarm"}, tmp_path / "b" / "out",
        predecessor_records={"s1": pred_trace}, **kwargs)
    a_rows = list(score_mod.iter_jsonl(Path(manifest["copies"][rl.COLUMN_REPLACE_ONLY]["path"])))
    assert json.loads(a_rows[0]["text"])["entities"] == [{"type": "time", "filler": "eight pm"}]
    # another row's predecessor records never serve this row
    with pytest.raises(score_mod.Stage3ScoreError, match="no sealed blind trace"):
        score_mod.render_relisten_shadow_columns(
            _bundle(tmp_path / "c", [row], {}), {"s1": "alarm"}, tmp_path / "c" / "out",
            predecessor_records={"s2": pred_trace}, **kwargs)


def test_render_relisten_shadow_columns_replaces_and_drops(tmp_path):
    trace = {}
    _trace_contact(trace, "blind-0", json.dumps({"heard": True, "value": "eight pm"}))
    text = json.dumps({
        "scenario": "alarm", "action": "set",
        "entities": [{"type": "time", "filler": "7 pm"}, {"type": "place_name", "filler": "paris"}],
    })
    order = rl.confirm_order("s1", "time")
    accepted = rl.decide_entity(
        index=0, slot_type="time", delivered_value="7 pm",
        blind=rl.parse_blind_response(trace["blind-0/response"]["text"]),
        blind_contact_id="blind-0",
        confirm_letter=("A" if order[0] == rl.CONFIRM_CANDIDATE else "B"),
        order=order, confirm_contact_id="confirm-0",
    )
    unheard_order = rl.confirm_order("s1", "place_name")
    unheard = rl.decide_entity(
        index=1, slot_type="place_name", delivered_value="paris",
        blind=rl.BlindResult(rl.BLIND_UNHEARD, None, 0), blind_contact_id="blind-1",
        confirm_letter=("A" if unheard_order[0] == rl.CONFIRM_CANDIDATE else "B"),
        order=unheard_order, confirm_contact_id="confirm-1",
    )
    assert accepted.accept is True
    assert unheard.dropped_when_unheard is True
    receipt = rl.seal_relisten_receipt([accepted, unheard], max_slots_per_row=3)
    row = {"sample_id": "s1", "text": text, "native_episode_receipt": {"kind": "accepted"},
           "relisten": receipt}
    bundle = _bundle(tmp_path, [row], trace)
    manifest = score_mod.render_relisten_shadow_columns(
        bundle, {"s1": "alarm"}, tmp_path / "analysis",
        run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64,
    )
    a_rows = list(score_mod.iter_jsonl(Path(manifest["copies"][rl.COLUMN_REPLACE_ONLY]["path"])))
    b_rows = list(score_mod.iter_jsonl(Path(manifest["copies"][rl.COLUMN_REPLACE_DROP_UNHEARD]["path"])))
    a_payload = json.loads(a_rows[0]["text"])
    b_payload = json.loads(b_rows[0]["text"])
    assert a_payload["entities"] == [
        {"type": "time", "filler": "eight pm"}, {"type": "place_name", "filler": "paris"},
    ]
    assert b_payload["entities"] == [{"type": "time", "filler": "eight pm"}]
    # intent (scenario/action) never moves -- E4 never re-opens the decided intent.
    assert a_payload["scenario"] == b_payload["scenario"] == "alarm"
    assert a_payload["action"] == b_payload["action"] == "set"
    assert manifest["at1_column_reproduction_checked_rows"] == 0  # a replacement happened


def test_render_relisten_shadow_columns_reads_a_real_outputs_jsonl_round_trip(tmp_path):
    """Coordinator ruling item 2: the shadow-column reconstruction reads the
    PERSISTED block, not in-memory state. Every other render test in this
    file hands the renderer an already-Python-shaped ``row`` dict; this one
    instead writes the row through an actual ``outputs.jsonl`` file on disk
    (``json.dumps`` then a fresh ``json.loads`` per line, the same encode/
    decode a real sealed flight's row survives) and only THEN builds the
    bundle from the reloaded dicts, so no Python object identity or tuple/
    list distinction from the writer side survives into the read."""

    trace = {}
    _trace_contact(trace, "blind-0", json.dumps({"heard": True, "value": "eight pm"}))
    text = json.dumps({
        "scenario": "alarm", "action": "set",
        "entities": [{"type": "time", "filler": "7 pm"}, {"type": "place_name", "filler": "paris"}],
    })
    order = rl.confirm_order("s1", "time")
    accepted = rl.decide_entity(
        index=0, slot_type="time", delivered_value="7 pm",
        blind=rl.parse_blind_response(trace["blind-0/response"]["text"]),
        blind_contact_id="blind-0",
        confirm_letter=("A" if order[0] == rl.CONFIRM_CANDIDATE else "B"),
        order=order, confirm_contact_id="confirm-0",
    )
    receipt = rl.seal_relisten_receipt([accepted], max_slots_per_row=3)
    written_row = {
        "sample_id": "s1", "text": text, "native_episode_receipt": {"kind": "accepted"},
        "relisten": receipt,
    }
    outputs_path = tmp_path / "RUN.outputs.jsonl"
    outputs_path.write_text(
        json.dumps(written_row, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8",
    )
    reloaded_rows = [
        json.loads(line) for line in outputs_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    bundle = _bundle(tmp_path, reloaded_rows, trace)
    manifest = score_mod.render_relisten_shadow_columns(
        bundle, {"s1": "alarm"}, tmp_path / "analysis",
        run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64,
    )
    a_rows = list(score_mod.iter_jsonl(Path(manifest["copies"][rl.COLUMN_REPLACE_ONLY]["path"])))
    a_payload = json.loads(a_rows[0]["text"])
    assert a_payload["entities"] == [
        {"type": "time", "filler": "eight pm"}, {"type": "place_name", "filler": "paris"},
    ]
    assert manifest["at1_column_reproduction_checked_rows"] == 0  # a replacement happened


def test_render_relisten_shadow_columns_refuses_a_value_hash_mismatch(tmp_path):
    trace = {}
    _trace_contact(trace, "blind-0", json.dumps({"heard": True, "value": "eight pm"}))
    text = json.dumps({"scenario": "alarm", "action": "set",
                        "entities": [{"type": "time", "filler": "7 pm"}]})
    accepted = rl.RelistenEntityRecord(
        index=0, slot_type="time", blind_contact_id="blind-0",
        blind_disposition=rl.BLIND_VALUE, blind_value_sha256="0" * 64,
        blind_canonical_sha256="0" * 64, blind_word_count=2,
        confirm_fired=True, confirm_contact_id="confirm-0",
        confirm_order=(rl.CONFIRM_DELIVERED, rl.CONFIRM_CANDIDATE),
        confirm_vote=rl.CONFIRM_CANDIDATE, accept=True, confirm_unheard_vote=None,
    )
    receipt = rl.seal_relisten_receipt([accepted], max_slots_per_row=3)
    row = {"sample_id": "s1", "text": text, "native_episode_receipt": {"kind": "accepted"},
           "relisten": receipt}
    bundle = _bundle(tmp_path, [row], trace)
    with pytest.raises(score_mod.Stage3ScoreError, match="differs from its sealed hash"):
        score_mod.render_relisten_shadow_columns(
            bundle, {"s1": "alarm"}, tmp_path / "analysis",
            run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64,
        )


# ---------------------------------------------------------------------------
# 7. malformed re-listen -> unparsed flag, never an abort
# ---------------------------------------------------------------------------


def test_malformed_blind_response_never_raises_and_is_flagged_unparsed():
    for garbage in ("not json", "{}", json.dumps({"heard": "yes", "value": "x"}),
                    json.dumps({"heard": True}), json.dumps({"heard": True, "value": 5})):
        result = rl.parse_blind_response(garbage)
        assert result.disposition == rl.BLIND_UNPARSED
    # never aborts: should_fire_confirm and decide_entity both accept it.
    unparsed = rl.parse_blind_response("not json")
    assert rl.should_fire_confirm(unparsed, "7 pm") is True
    order = rl.confirm_order("s1", "time")
    record = rl.decide_entity(
        index=0, slot_type="time", delivered_value="7 pm", blind=unparsed,
        blind_contact_id="blind-0", confirm_letter="neither", order=order,
        confirm_contact_id="confirm-0",
    )
    assert record.accept is False
    assert record.blind_disposition == rl.BLIND_UNPARSED


def test_malformed_confirm_response_never_raises_and_is_conservative():
    for garbage in ("not json", "{}", json.dumps({"choice": "C"}), json.dumps({"choice": 1})):
        assert rl.parse_confirm_letter(garbage) == rl.CONFIRM_UNPARSED
    order = rl.confirm_order("s1", "time")
    record = rl.decide_entity(
        index=0, slot_type="time", delivered_value="7 pm",
        blind=rl.BlindResult(rl.BLIND_UNHEARD, None, 0), blind_contact_id="blind-0",
        confirm_letter=rl.parse_confirm_letter("garbage"), order=order,
        confirm_contact_id="confirm-0",
    )
    assert record.accept is False
    assert record.confirm_unheard_vote is True  # conservative: unparsed counts as "not heard"


# ---------------------------------------------------------------------------
# 8. ceiling arithmetic
# ---------------------------------------------------------------------------


def _base_native_episode_values():
    return {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": "e4-test-v1",
            "max_revisions": 1,
            "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
            "roles": {
                "perception": {"phase_id": "perception", "max_iterations": 1},
                "reviewer": {"phase_id": "reviewer", "max_iterations": 3},
                "planner": {"phase_id": "planner", "max_iterations": 1},
                "solver": {"phase_id": "solver", "max_iterations": 1},
            },
        }
    }


def _relisten_block(max_slots_per_row=3):
    return {
        "policy": rl.RELISTEN_POLICY_ID,
        "max_slots_per_row": max_slots_per_row,
        "value_max_words": rl.MAX_VALUE_WORDS,
        "delivery": rl.DELIVERY_MODE,
        "blind_template_id": rl.BLIND_TEMPLATE_ID,
        "confirm_template_id": rl.CONFIRM_TEMPLATE_ID,
    }


def test_absent_relisten_key_leaves_ceiling_and_config_byte_identical():
    program = default_phase_program("phase-native-candidates-review-revise-v1")
    values = _base_native_episode_values()
    config = load_native_episode_config(values, program)
    assert config.max_contacts == program.max_contacts == 11
    assert config.relisten is None
    assert config.relisten_json is None


def test_relisten_ceiling_adds_two_per_declared_slot():
    assert rl.relisten_extra_ceiling(3) == 6
    assert rl.relisten_extra_ceiling(1) == 2
    program = default_phase_program("phase-native-candidates-review-revise-relisten-v1")
    values = _base_native_episode_values()
    values["native_episode"]["relisten"] = _relisten_block(max_slots_per_row=3)
    config = load_native_episode_config(values, program)
    assert config.max_contacts == 11 + 6 == 17 == program.max_contacts
    assert config.relisten.extra_contacts_ceiling == 6


def test_relisten_refuses_beside_a_grouped_solver_visit():
    program = default_phase_program("phase-native-candidates-review-revise-relisten-v1")
    values = _base_native_episode_values()
    values["native_episode"]["relisten"] = _relisten_block()
    values["native_episode"]["roles"]["solver"]["samples"] = 2
    with pytest.raises(ValueError, match="grouped Solver"):
        load_native_episode_config(values, program)


def test_relisten_refuses_beside_a_supply_variant_arm_group():
    program = default_phase_program("phase-native-candidates-review-revise-relisten-v1")
    values = _base_native_episode_values()
    values["native_episode"]["relisten"] = _relisten_block()
    values["native_episode"]["roles"]["solver"]["supply_variants"] = {"anything": True}
    with pytest.raises(ValueError):
        load_native_episode_config(values, program)


def test_relisten_config_rejects_an_out_of_bound_cap():
    with pytest.raises(rl.RelistenError, match="max_slots_per_row"):
        rl.parse_relisten(_relisten_block(max_slots_per_row=4))
    with pytest.raises(rl.RelistenError, match="max_slots_per_row"):
        rl.parse_relisten(_relisten_block(max_slots_per_row=0))


def test_select_relisten_targets_takes_up_to_the_cap_in_delivery_order():
    entities = [{"type": t, "filler": t} for t in ("time", "place_name", "food_type", "person")]
    assert rl.select_relisten_targets(entities, 3) == (0, 1, 2)
    assert rl.select_relisten_targets(entities[:2], 3) == (0, 1)
    assert rl.select_relisten_targets([], 3) == ()


def test_confirm_order_is_deterministic_and_covers_both_orders():
    seen = set()
    for i in range(50):
        seen.add(rl.confirm_order(f"sample-{i}", "time"))
    assert seen == {(rl.CONFIRM_DELIVERED, rl.CONFIRM_CANDIDATE),
                    (rl.CONFIRM_CANDIDATE, rl.CONFIRM_DELIVERED)}
    # deterministic: the same (sample_id, slot_type) always yields the same order.
    assert rl.confirm_order("sample-7", "time") == rl.confirm_order("sample-7", "time")


# ---------------------------------------------------------------------------
# 9. gate findings
# ---------------------------------------------------------------------------


def test_stage3_effect_floor_gate_registers_the_relisten_design():
    # owner decision 190 (2026-09-29): the design's SLU floor is now the larger of the two
    # measured same-flight CONTRAST half-widths (1.49 pp at n = 1,080), not the provisional
    # ROLL-AA anchor (0.3163 pp); intent carries no floor at all on this design (identical by
    # construction on its two derived columns) and a metric-blind call is refused.
    floor, arithmetic = floor_mod.floor_for("same-flight-shadow-relisten", 1080, metric="slu")
    assert floor == pytest.approx(1.49, abs=1e-3)
    floor_1000, _ = floor_mod.floor_for("same-flight-shadow-relisten", 1000, metric="slu")
    assert floor_1000 == pytest.approx(1.49 * (1080 / 1000) ** 0.5, abs=1e-3)
    assert any("sampling half-width" in line for line in arithmetic)
    with pytest.raises(ValueError):
        floor_mod.floor_for("same-flight-shadow-relisten", 1080)
    with pytest.raises(ValueError):
        floor_mod.floor_for("same-flight-shadow-relisten", 1080, metric="intent")


def test_flight_registration_gate_requires_nominated_shadow_and_columns():
    baseline = {"native_episode": {"relisten": _relisten_block()}}
    good_fragment = {
        "stage3_measurement": {
            "measurement_design": "same-flight-shadow-relisten",
            "expected_effect_pp": 0.0, "rows": 1080, "claims_benefit": False,
            "claim": "nominated", "shadow_delivery": True,
            "columns": list(rl.SHADOW_COLUMNS),
            "tuning_roster": "slurp-train-fold-a", "read_roster": "slurp-dev-2000-added",
        }
    }
    report = reg_mod.CellReport(
        experiment="e4", cell_id="CELL-E4", run_id="SAEA-E4-TEST-V1",
        state="held", named=True,
    )
    reg_mod._check_relisten_registration(report, good_fragment, baseline, floor_mod, REPO_ROOT)
    assert report.findings == []
    assert report.relisten["columns"] == list(rl.SHADOW_COLUMNS)

    bad_fragment = json.loads(json.dumps(good_fragment))
    bad_fragment["stage3_measurement"]["claim"] = "admitted"
    bad_fragment["stage3_measurement"]["shadow_delivery"] = False
    bad_fragment["stage3_measurement"]["columns"] = [rl.COLUMN_REPLACE_ONLY]
    bad_report = reg_mod.CellReport(
        experiment="e4", cell_id="CELL-E4", run_id="SAEA-E4-TEST-V1",
        state="held", named=True,
    )
    reg_mod._check_relisten_registration(bad_report, bad_fragment, baseline, floor_mod, REPO_ROOT)
    kinds = {finding.kind for finding in bad_report.findings}
    assert kinds == {
        "relisten-claim-not-nominated", "relisten-not-shadow-delivery",
        "relisten-columns-missing",
    }


def test_flight_registration_gate_is_a_no_op_for_a_non_relisten_design():
    report = reg_mod.CellReport(
        experiment="e4", cell_id="CELL-OTHER", run_id="SAEA-OTHER-V1",
        state="held", named=True,
    )
    fragment = {"stage3_measurement": {
        "measurement_design": "same-flight-paired", "expected_effect_pp": 1.0, "rows": 1080,
    }}
    reg_mod._check_relisten_registration(report, fragment, None, floor_mod, REPO_ROOT)
    assert report.findings == []
    assert report.relisten is None


# ---------------------------------------------------------------------------
# 10. I7l bundle custody (core.bundle.outputs) -- the online node's own
# receipt, re-derived from the row's own sealed trace rather than trusted.
# ---------------------------------------------------------------------------


def _relisten_trace_pair(contact_id, text, *, sample_id="s1"):
    return {
        f"{contact_id}/request": {"payload": {"sample_id": sample_id}},
        f"{contact_id}/response": {"text": text},
    }


def test_i7l_verifies_a_genuine_accepted_relisten_row():
    order = rl.confirm_order("s1", "time")
    blind_text = json.dumps({"heard": True, "value": "eight pm"})
    confirm_letter = "A" if order[0] == rl.CONFIRM_CANDIDATE else "B"
    confirm_text = json.dumps({"choice": confirm_letter})
    accepted = rl.decide_entity(
        index=0, slot_type="time", delivered_value="7 pm",
        blind=rl.parse_blind_response(blind_text), blind_contact_id="req-blind-0",
        confirm_letter=rl.parse_confirm_letter(confirm_text), order=order,
        confirm_contact_id="req-confirm-0",
    )
    assert accepted.accept is True
    receipt = rl.seal_relisten_receipt([accepted], max_slots_per_row=3)
    row = {"sample_id": "s1", "relisten": receipt}
    trace = {
        **_relisten_trace_pair("req-blind-0", blind_text),
        **_relisten_trace_pair("req-confirm-0", confirm_text),
    }
    bundle_outputs._verify_relisten_trace_binding(row, trace)  # must not raise


def test_i7l_verifies_a_skipped_entity_with_no_confirm_contact():
    blind_text = json.dumps({"heard": True, "value": "paris"})
    skipped = rl.decide_entity(
        index=0, slot_type="place_name", delivered_value="paris",
        blind=rl.parse_blind_response(blind_text), blind_contact_id="req-blind-0",
        confirm_letter=None, order=None,
    )
    receipt = rl.seal_relisten_receipt([skipped], max_slots_per_row=3)
    row = {"sample_id": "s1", "relisten": receipt}
    bundle_outputs._verify_relisten_trace_binding(
        row, _relisten_trace_pair("req-blind-0", blind_text),
    )


def test_i7l_refuses_a_disposition_that_disagrees_with_the_trace():
    blind_text = json.dumps({"heard": True, "value": "eight pm"})
    skipped = rl.decide_entity(
        index=0, slot_type="place_name", delivered_value="paris",
        blind=rl.parse_blind_response(json.dumps({"heard": False, "value": ""})),
        blind_contact_id="req-blind-0", confirm_letter=None, order=None,
    )
    receipt = json.loads(json.dumps(rl.seal_relisten_receipt([skipped], max_slots_per_row=3)))
    # The sealed receipt honestly says "unheard"; the trace's own recorded
    # response text says otherwise -- a forged/corrupted receipt.
    row = {"sample_id": "s1", "relisten": receipt}
    with pytest.raises(bundle_outputs.BundleError, match="I7l"):
        bundle_outputs._verify_relisten_trace_binding(
            row, _relisten_trace_pair("req-blind-0", blind_text),
        )


def test_i7l_refuses_a_missing_trace_pair():
    record = rl.decide_entity(
        index=0, slot_type="time", delivered_value="7 pm",
        blind=rl.BlindResult(rl.BLIND_VALUE, "eight pm", 2),
        blind_contact_id="req-blind-missing", confirm_letter=None, order=None,
    )
    receipt = rl.seal_relisten_receipt([record], max_slots_per_row=3)
    row = {"sample_id": "s1", "relisten": receipt}
    with pytest.raises(bundle_outputs.BundleError, match="I7l"):
        bundle_outputs._verify_relisten_trace_binding(row, {})


def test_i7l_refuses_a_forged_vote():
    order = rl.confirm_order("s1", "time")
    blind_text = json.dumps({"heard": True, "value": "eight pm"})
    letter = "A" if order[0] == rl.CONFIRM_CANDIDATE else "B"
    confirm_text = json.dumps({"choice": letter})
    accepted = rl.decide_entity(
        index=0, slot_type="time", delivered_value="7 pm",
        blind=rl.parse_blind_response(blind_text), blind_contact_id="req-blind-0",
        confirm_letter=rl.parse_confirm_letter(confirm_text), order=order,
        confirm_contact_id="req-confirm-0",
    )
    receipt = json.loads(json.dumps(rl.seal_relisten_receipt([accepted], max_slots_per_row=3)))
    # Forge the sealed vote to disagree with what the trace's own confirm
    # response text actually says.
    forged_vote = (
        rl.CONFIRM_DELIVERED
        if receipt["entities"][0]["confirm"]["vote"] != rl.CONFIRM_DELIVERED
        else rl.CONFIRM_CANDIDATE
    )
    receipt["entities"][0]["confirm"]["vote"] = forged_vote
    row = {"sample_id": "s1", "relisten": receipt}
    trace = {
        **_relisten_trace_pair("req-blind-0", blind_text),
        **_relisten_trace_pair("req-confirm-0", confirm_text),
    }
    with pytest.raises(bundle_outputs.BundleError, match="I7l"):
        bundle_outputs._verify_relisten_trace_binding(row, trace)


def test_i7l_refuses_a_contacts_used_mismatch():
    blind_text = json.dumps({"heard": True, "value": "paris"})
    record = rl.decide_entity(
        index=0, slot_type="place_name", delivered_value="paris",
        blind=rl.parse_blind_response(blind_text), blind_contact_id="req-blind-0",
        confirm_letter=None, order=None,
    )
    receipt = json.loads(json.dumps(rl.seal_relisten_receipt([record], max_slots_per_row=3)))
    receipt["contacts_used"] = 99
    row = {"sample_id": "s1", "relisten": receipt}
    with pytest.raises(bundle_outputs.BundleError, match="I7l"):
        bundle_outputs._verify_relisten_trace_binding(
            row, _relisten_trace_pair("req-blind-0", blind_text),
        )


def test_i7l_is_wired_by_key_presence_alone():
    """``_verify_outputs_trace_binding`` dispatches on the row's own
    ``"relisten"`` key (mirroring ``"supply_variants"``/
    ``"perception_branches"``), never on a declared config -- so a row that
    carries the key is checked regardless of how it got there."""

    import inspect

    source = inspect.getsource(bundle_outputs._verify_outputs_trace_binding)
    assert '"relisten" in row' in source
    assert "_verify_relisten_trace_binding(row, records)" in source


# ---------------------------------------------------------------------------
# 8. CLI wiring (--mode relisten; scripts/flights/e4/e4_read.sh's own gate)
# ---------------------------------------------------------------------------


def test_cli_offers_mode_relisten(capsys):
    """``scripts/flights/e4/e4_read.sh`` refuses to run unless ``--help``
    lists a ``relisten`` mode (its own item-0 gate: ``stage3_rollout_score.py
    --help | grep -q relisten``); this is exactly that check, in-process."""

    with pytest.raises(SystemExit) as excinfo:
        score_mod.main(["--help"])
    assert excinfo.value.code == 0
    assert "relisten" in capsys.readouterr().out


def test_relisten_main_refuses_pairs_and_a_samples_override():
    args = SimpleNamespace(stage="pairs", samples=None)
    with pytest.raises(score_mod.Stage3ScoreError, match="render/score/all"):
        score_mod.relisten_main(args, Path("."), Path("."), {})
    args = SimpleNamespace(stage="all", samples=4)
    with pytest.raises(score_mod.Stage3ScoreError, match="render/score/all"):
        score_mod.relisten_main(args, Path("."), Path("."), {})


def test_relisten_main_renders_then_scores_through_the_shared_functions(tmp_path, monkeypatch):
    """``relisten_main`` (the ``--mode relisten`` CLI entry) is
    ``supply_variant_main``'s own structural twin: verify the sealed
    bundle's composed config hash, then drive
    ``render_relisten_shadow_columns`` / ``score_relisten_shadow_copies``
    (already proven correct above) with the file names
    ``scripts/flights/e4/e4_read.sh`` expects. Every dependency is a stub
    here -- this proves the WIRING, not the render/score logic itself."""

    import speech_aware_evidence_acquisition.core.bundle as bundle_mod
    import speech_aware_evidence_acquisition.core.config as config_mod

    bundle = SimpleNamespace(manifest={
        "config": {
            "config_hash": "c" * 64,
            "fragments": {"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"},
        },
    })
    monkeypatch.setattr(bundle_mod, "verify_bundle", lambda path: bundle)
    monkeypatch.setattr(
        config_mod, "compose",
        lambda repo_root, *fragments: SimpleNamespace(config_hash="c" * 64),
    )
    monkeypatch.setattr(score_mod, "run_dir", lambda root, run, attempt: tmp_path)
    monkeypatch.setattr(
        score_mod, "load_roster",
        lambda repo_root, roster: ({"s1": "alarm"}, "r" * 64, "h" * 64),
    )
    render_calls = []
    score_calls = []
    fake_manifest = {"column_order": ["a", "b"], "rows": 1, "copies": {}}
    fake_summary = {"columns": {"a": {}, "b": {}}, "sealed_delivered_rows": 1}

    def fake_render(bundle_arg, roster, out_dir, *, run_id, attempt_id, roster_sha256, config_hash):
        render_calls.append((bundle_arg, roster, out_dir, run_id, attempt_id, roster_sha256, config_hash))
        return fake_manifest

    def fake_score(scorer_id, manifest, out_dir, *, lock, data_root, delivered):
        score_calls.append((scorer_id, manifest, out_dir, lock, data_root, delivered))
        return fake_summary

    monkeypatch.setattr(score_mod, "render_relisten_shadow_columns", fake_render)
    monkeypatch.setattr(score_mod, "score_relisten_shadow_copies", fake_score)
    monkeypatch.setattr(score_mod, "sealed_per_sample", lambda directory, run, scorer: {"s1": {}})

    args = SimpleNamespace(
        stage="all", samples=None, run="RUN", attempt="ATT", roster="roster.json",
        analysis_root=str(tmp_path / "out"), scorer_id="slurp-slu-official-train",
    )
    code = score_mod.relisten_main(args, Path("/repo"), tmp_path, {"lock": True})
    assert code == 0
    assert len(render_calls) == 1
    assert render_calls[0][3:] == ("RUN", "ATT", "r" * 64, "c" * 64)
    assert len(score_calls) == 1
    assert score_calls[0][0] == "slurp-slu-official-train"
    assert score_calls[0][1] is fake_manifest


def test_relisten_main_refuses_a_config_hash_drift(tmp_path, monkeypatch):
    """The same defence-in-depth ``supply_variant_main`` applies: a sealed
    manifest's claimed config_hash must match a live recompute of its own
    named fragments, or the read is refused rather than trusted blind."""

    import speech_aware_evidence_acquisition.core.bundle as bundle_mod
    import speech_aware_evidence_acquisition.core.config as config_mod

    bundle = SimpleNamespace(manifest={
        "config": {
            "config_hash": "c" * 64,
            "fragments": {"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"},
        },
    })
    monkeypatch.setattr(bundle_mod, "verify_bundle", lambda path: bundle)
    monkeypatch.setattr(
        config_mod, "compose",
        lambda repo_root, *fragments: SimpleNamespace(config_hash="drifted"),
    )
    monkeypatch.setattr(score_mod, "run_dir", lambda root, run, attempt: tmp_path)
    args = SimpleNamespace(
        stage="all", samples=None, run="RUN", attempt="ATT", roster="roster.json",
        analysis_root=str(tmp_path / "out"), scorer_id="slurp-slu-official-train",
    )
    with pytest.raises(score_mod.Stage3ScoreError, match="current fragments differ from sealed composed config"):
        score_mod.relisten_main(args, Path("/repo"), tmp_path, {})
