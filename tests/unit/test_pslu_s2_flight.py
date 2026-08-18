"""``rails.probes.pslu_s2_flight``: the P-SLU Stage-2 follow-up F1 + A1'r
(two-phase) flight orchestration (SAEA-PROBE-pslu-s2-183,
``docs/readiness/2026-08-18-pslu-s2-preregistration-REGISTERED.md``).
Engineering-only, zero live model contact -- every test drives a
``MockCoreClient``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.model import SliceRegistry
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.consumption import build_consumption_trace
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
    PsluRosters,
    pslu_supply_packet,
    render_roster_entries,
    render_type_vocabulary,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import (
    A1R_ARM,
    A1R_PHASE1_ARM,
    F1_ARM,
    PSLU_S2_ARMS,
    ClosedSetMapping,
    PsluS2ArmResult,
    PsluS2FlightError,
    PsluS2FlightSummary,
    _assert_this_module_never_calls_ontology_miner,
    canonical_scenario_labels,
    closed_set_phase1_supply_packet,
    map_predicted_scenario_to_canonical,
    run_pslu_s2_flight,
    validate_pslu_s2_flight_summary,
)
from speech_aware_evidence_acquisition.rails.silence_swap import build_silence_swap_slice

_ROSTERS = PsluRosters(
    scenario_rosters={
        "iot": (("house_place", "kitchen"), ("device_type", "light")),
        "email": (("email_folder", "inbox"),),
    },
    global_types=("house_place", "device_type", "email_folder", "time"),
    full_roster=(("house_place", "kitchen"), ("time", "six")),
    derangement={"iot": "email", "email": "iot"},
)

_FILLER_ENTRIES = (("zzfillertype1", "zzfillervalue1"), ("zzfillertype2", "zzfillervalue2"))


def _adapter(slurp_world) -> SlurpAdapter:
    lock = load_lock(slurp_world.lock_path)
    return SlurpAdapter(lock, slurp_world.data_root)


def _flight_world(slurp_world):
    adapter = _adapter(slurp_world)
    devel = adapter.load_split("devel")
    s_iot = devel[0]  # slurp:devel:000101:audio-101, gold scenario "iot"
    s_email = devel[2]  # slurp:devel:000102:audio-102, gold scenario "email"
    return adapter, s_iot, s_email


def _index_responder(responses):
    """Returns ``responses[i]`` on the i-th call -- valid ONLY when the
    flight's own call order is known ahead of time (F1 then A1'r
    phase1/phase2 per sample, in that order -- module docstring)."""

    state = {"n": 0}

    def responder(messages):
        i = state["n"]
        state["n"] += 1
        return responses[i]

    return responder


# ---------------------------------------------------------------------------
# canonical_scenario_labels / closed_set_phase1_supply_packet
# ---------------------------------------------------------------------------


def test_canonical_scenario_labels_is_the_sorted_scenario_rosters_keys():
    assert canonical_scenario_labels(_ROSTERS) == ("email", "iot")


def test_closed_set_phase1_supply_packet_lists_every_label_and_carries_no_items():
    labels = canonical_scenario_labels(_ROSTERS)
    packet = closed_set_phase1_supply_packet(labels)
    assert "email" in packet.prompt_block
    assert "iot" in packet.prompt_block
    assert "closed list" in packet.prompt_block
    assert packet.items == ()
    assert packet.dose.n_items == 0


# ---------------------------------------------------------------------------
# map_predicted_scenario_to_canonical -- the deterministic three-tier parser.
# ---------------------------------------------------------------------------

_LABELS = ("alarm", "audio", "email", "iot")


def test_map_predicted_scenario_exact_match():
    mapping = map_predicted_scenario_to_canonical("iot", _LABELS)
    assert mapping == ClosedSetMapping("iot", "iot", "exact", False)


def test_map_predicted_scenario_case_insensitive_match():
    mapping = map_predicted_scenario_to_canonical("IoT", _LABELS)
    assert mapping == ClosedSetMapping("IoT", "iot", "case_insensitive", False)


def test_map_predicted_scenario_unique_substring_match():
    mapping = map_predicted_scenario_to_canonical("Setting an alarm for six", _LABELS)
    assert mapping == ClosedSetMapping("Setting an alarm for six", "alarm", "unique_substring", False)


def test_map_predicted_scenario_unmapped_when_ambiguous_substring():
    """Both "audio" and "alarm" ... no -- craft two labels that BOTH occur as
    substrings of the same predicted text to prove ambiguity refuses a
    guess."""

    labels = ("cat", "cats")
    mapping = map_predicted_scenario_to_canonical("my cats are here", labels)
    assert mapping.outcome == "unmapped"
    assert mapping.canonical_label is None
    assert mapping.fallback is True


def test_map_predicted_scenario_unmapped_when_no_candidate_matches():
    mapping = map_predicted_scenario_to_canonical("Completely unrelated nonsense", _LABELS)
    assert mapping == ClosedSetMapping("Completely unrelated nonsense", None, "unmapped", True)


def test_map_predicted_scenario_unmapped_when_predicted_is_none():
    mapping = map_predicted_scenario_to_canonical(None, _LABELS)
    assert mapping == ClosedSetMapping(None, None, "unmapped", True)


def test_map_predicted_scenario_mapping_as_json():
    mapping = map_predicted_scenario_to_canonical("iot", _LABELS)
    assert mapping.as_json() == {
        "predicted_raw": "iot", "canonical_label": "iot", "outcome": "exact", "fallback": False,
    }


# ---------------------------------------------------------------------------
# run_pslu_s2_flight -- end to end.
# ---------------------------------------------------------------------------


def test_run_pslu_s2_flight_produces_f1_then_a1r_two_phase_per_sample(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient()  # default canned (non-JSON) responder -- exercises the unmapped fallback path
    summary = run_pslu_s2_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS, filler_entries=_FILLER_ENTRIES
    )

    assert [r.arm for r in summary.results] == [
        "F1", "F1",
        "A1r-phase1", "A1r",
        "A1r-phase1", "A1r",
    ]
    assert len(client.calls) == 6
    assert set(PSLU_S2_ARMS) == {"F1", "A1r-phase1", "A1r"}
    assert summary.canonical_labels == ("email", "iot")


def test_run_pslu_s2_flight_f1_roster_text_is_fixed_across_every_sample(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient()
    summary = run_pslu_s2_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS, filler_entries=_FILLER_ENTRIES
    )
    f1_rows = [r for r in summary.results if r.arm == "F1"]
    assert len(f1_rows) == 2
    texts = {row.messages[1]["content"][0]["text"] for row in f1_rows}
    assert texts == {render_roster_entries(_FILLER_ENTRIES)}


def test_run_pslu_s2_flight_phase2_uses_phase1s_own_parsed_label_not_gold(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    assert s_iot.scenario == "iot"
    responses = [
        json.dumps({"scenario": "x", "action": "y", "entities": []}),  # F1
        json.dumps({"scenario": "email", "action": "query", "entities": []}),  # phase 1: wrong on purpose
        json.dumps({"scenario": "z", "action": "w", "entities": []}),  # phase 2
    ]
    client = MockCoreClient(responder=_index_responder(responses))
    summary = run_pslu_s2_flight(
        adapter=adapter, core_client=client, samples=[s_iot], rosters=_ROSTERS, filler_entries=_FILLER_ENTRIES
    )

    phase1_row = next(r for r in summary.results if r.arm == "A1r-phase1")
    assert phase1_row.closed_set_mapping == ClosedSetMapping("email", "email", "exact", False)

    phase2_row = next(r for r in summary.results if r.arm == "A1r" and not r.silence_swapped)
    phase2_text = phase2_row.messages[1]["content"][0]["text"]
    expected = pslu_supply_packet("A1p", scenario="email", rosters=_ROSTERS)
    assert phase2_text == expected.prompt_block == "email_folder=inbox"  # differs from gold "iot" roster


def test_run_pslu_s2_flight_phase2_falls_back_to_a2_when_phase1_is_unmapped(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    responses = [
        json.dumps({"scenario": "x", "action": "y", "entities": []}),  # F1
        json.dumps({"scenario": "Completely unrelated nonsense", "action": "y", "entities": []}),  # phase 1: unmapped
        json.dumps({"scenario": "z", "action": "w", "entities": []}),  # phase 2
    ]
    client = MockCoreClient(responder=_index_responder(responses))
    summary = run_pslu_s2_flight(
        adapter=adapter, core_client=client, samples=[s_iot], rosters=_ROSTERS, filler_entries=_FILLER_ENTRIES
    )

    phase1_row = next(r for r in summary.results if r.arm == "A1r-phase1")
    assert phase1_row.closed_set_mapping.fallback is True
    assert phase1_row.closed_set_mapping.canonical_label is None

    phase2_row = next(r for r in summary.results if r.arm == "A1r" and not r.silence_swapped)
    phase2_text = phase2_row.messages[1]["content"][0]["text"]
    assert phase2_text == render_type_vocabulary(_ROSTERS.global_types)


def test_run_pslu_s2_flight_silence_swap_adds_one_extra_a1r_row(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    assert ":" in s_iot.sample_id
    registry = SliceRegistry(
        data_root=slurp_world.data_root,
        run_id="run-x",
        parent_facts={s_iot.sample_id: (s_iot.media_relpath, s_iot.audio_seconds)},
    )
    silence_record = build_silence_swap_slice(
        registry=registry,
        data_root=slurp_world.data_root,
        sample_id=s_iot.sample_id,
        parent_media_relpath=s_iot.media_relpath,
        duration_seconds=s_iot.audio_seconds,
        sample_rate_hz=16000,
    )
    registry.register(silence_record)
    silence_relpath = silence_record.media_relpath

    client = MockCoreClient()
    summary = run_pslu_s2_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS,
        filler_entries=_FILLER_ENTRIES, silence_swap_media_relpaths={s_iot.sample_id: silence_relpath},
    )

    assert len(summary.results) == 7  # 6 base + 1 silence-swap
    swapped = [r for r in summary.results if r.silence_swapped]
    assert len(swapped) == 1
    assert swapped[0].arm == "A1r"
    assert swapped[0].sample_id == s_iot.sample_id
    assert swapped[0].messages[1]["content"][-1] == {"type": "input_audio", "media_relpath": silence_relpath}

    normal_a1r = next(r for r in summary.results if r.arm == "A1r" and r.sample_id == s_iot.sample_id and not r.silence_swapped)
    # The roster text is UNCHANGED by the swap -- only the audio changes.
    assert swapped[0].messages[1]["content"][0] == normal_a1r.messages[1]["content"][0]


def test_run_pslu_s2_flight_rejects_empty_samples(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    with pytest.raises(PsluS2FlightError, match="at least one sample"):
        run_pslu_s2_flight(
            adapter=adapter, core_client=MockCoreClient(), samples=(), rosters=_ROSTERS, filler_entries=_FILLER_ENTRIES
        )


def test_run_pslu_s2_flight_rejects_duplicate_samples(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    with pytest.raises(PsluS2FlightError, match="duplicate sample_id"):
        run_pslu_s2_flight(
            adapter=adapter, core_client=MockCoreClient(), samples=[s_iot, s_iot], rosters=_ROSTERS,
            filler_entries=_FILLER_ENTRIES,
        )


def test_run_pslu_s2_flight_rejects_unknown_silence_swap_sample_ids(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    with pytest.raises(PsluS2FlightError, match="outside this flight"):
        run_pslu_s2_flight(
            adapter=adapter, core_client=MockCoreClient(), samples=[s_iot], rosters=_ROSTERS,
            filler_entries=_FILLER_ENTRIES, silence_swap_media_relpaths={"bogus-sample-id": "x.wav"},
        )


# ---------------------------------------------------------------------------
# validate_pslu_s2_flight_summary -- fail-closed structural checks.
# ---------------------------------------------------------------------------


def _dummy_row(arm: str, sample_id: str, *, silence_swapped: bool = False) -> PsluS2ArmResult:
    return PsluS2ArmResult(
        arm=arm,
        sample_id=sample_id,
        messages=(),
        response_text="x",
        metrics={},
        consumption=build_consumption_trace(span_id="full", supply=None, response_text="x"),
        silence_swapped=silence_swapped,
    )


def _complete_summary(sample_ids, *, silence_ids=()) -> PsluS2FlightSummary:
    results = []
    for sample_id in sample_ids:
        results.append(_dummy_row("F1", sample_id))
        results.append(_dummy_row("A1r-phase1", sample_id))
        results.append(_dummy_row("A1r", sample_id))
    for sample_id in silence_ids:
        results.append(_dummy_row("A1r", sample_id, silence_swapped=True))
    return PsluS2FlightSummary(results=tuple(results), canonical_labels=("email", "iot"))


def test_validate_pslu_s2_flight_summary_accepts_a_complete_summary():
    summary = _complete_summary(["s1", "s2", "s3"], silence_ids=["s1", "s2", "s3"])
    validate_pslu_s2_flight_summary(
        summary, expected_sample_ids=["s1", "s2", "s3"], expected_silence_swap_sample_ids=["s1", "s2", "s3"]
    )


def test_validate_pslu_s2_flight_summary_accepts_zero_silence_swaps_by_default():
    summary = _complete_summary(["s1"], silence_ids=[])
    validate_pslu_s2_flight_summary(summary, expected_sample_ids=["s1"])


def test_validate_pslu_s2_flight_summary_rejects_missing_arm_row():
    summary = _complete_summary(["s1", "s2"], silence_ids=["s1", "s2"])
    # Drop one F1 row -- arm count mismatch.
    results = tuple(r for r in summary.results if not (r.arm == "F1" and r.sample_id == "s2"))
    summary = PsluS2FlightSummary(results=results, canonical_labels=summary.canonical_labels)
    with pytest.raises(PsluS2FlightError, match="does not match the expected"):
        validate_pslu_s2_flight_summary(
            summary, expected_sample_ids=["s1", "s2"], expected_silence_swap_sample_ids=["s1", "s2"]
        )


def test_validate_pslu_s2_flight_summary_rejects_duplicate_sample_id_row():
    summary = _complete_summary(["s1"], silence_ids=["s1"])
    results = summary.results + (_dummy_row("F1", "s1"),)  # duplicate F1/s1
    summary = PsluS2FlightSummary(results=results, canonical_labels=summary.canonical_labels)
    with pytest.raises(PsluS2FlightError, match="duplicate sample_id"):
        validate_pslu_s2_flight_summary(summary, expected_sample_ids=["s1"], expected_silence_swap_sample_ids=["s1"])


def test_validate_pslu_s2_flight_summary_rejects_wrong_silence_swap_set():
    summary = _complete_summary(["s1", "s2"], silence_ids=["s1"])  # only s1, expected s1 AND s2
    with pytest.raises(PsluS2FlightError, match="silence-swap sample id set does not match"):
        validate_pslu_s2_flight_summary(
            summary, expected_sample_ids=["s1", "s2"], expected_silence_swap_sample_ids=["s1", "s2"]
        )


def test_validate_pslu_s2_flight_summary_rejects_duplicate_silence_swap_row():
    summary = _complete_summary(["s1"], silence_ids=[])
    results = summary.results + (
        _dummy_row("A1r", "s1", silence_swapped=True),
        _dummy_row("A1r", "s1", silence_swapped=True),
    )
    summary = PsluS2FlightSummary(results=results, canonical_labels=summary.canonical_labels)
    with pytest.raises(PsluS2FlightError, match="duplicate silence-swap sample_id"):
        validate_pslu_s2_flight_summary(summary, expected_sample_ids=["s1"], expected_silence_swap_sample_ids=["s1"])


def test_validate_pslu_s2_flight_summary_rejects_silence_swap_on_the_wrong_arm():
    summary = _complete_summary(["s1"], silence_ids=[])
    results = summary.results + (_dummy_row("F1", "s1", silence_swapped=True),)
    summary = PsluS2FlightSummary(results=results, canonical_labels=summary.canonical_labels)
    with pytest.raises(PsluS2FlightError, match="expected 'A1r'"):
        validate_pslu_s2_flight_summary(summary, expected_sample_ids=["s1"], expected_silence_swap_sample_ids=["s1"])


def test_validate_pslu_s2_flight_summary_rejects_expected_id_duplicates():
    summary = _complete_summary(["s1"], silence_ids=["s1"])
    with pytest.raises(PsluS2FlightError, match="expected_sample_ids carries a duplicate"):
        validate_pslu_s2_flight_summary(summary, expected_sample_ids=["s1", "s1"])


def test_validate_pslu_s2_flight_summary_rejects_expected_silence_id_duplicates():
    summary = _complete_summary(["s1"], silence_ids=["s1"])
    with pytest.raises(PsluS2FlightError, match="expected_silence_swap_sample_ids carries a duplicate"):
        validate_pslu_s2_flight_summary(
            summary, expected_sample_ids=["s1"], expected_silence_swap_sample_ids=["s1", "s1"]
        )


# ---------------------------------------------------------------------------
# The ontology-miner call guard (this module's OWN source).
# ---------------------------------------------------------------------------


def test_the_real_module_source_never_references_the_ontology_miner():
    _assert_this_module_never_calls_ontology_miner()  # no args -- self-checks the real file


def test_guard_catches_a_live_import_in_this_modules_own_source():
    source = "from ...data.slurp import load_slurp_ontology\n"
    from speech_aware_evidence_acquisition.rails.probes.pslu_flight import PsluFlightError

    with pytest.raises(PsluFlightError, match="load_slurp_ontology"):
        _assert_this_module_never_calls_ontology_miner(source)


def test_guard_does_not_trip_on_a_docstring_mention():
    source = '"""This module never calls load_slurp_ontology -- see the docstring."""\nx = 1\n'
    _assert_this_module_never_calls_ontology_miner(source)  # does not raise
