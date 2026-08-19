"""``rails.probes.ptrap_flight``: the P-TRAP two-arm self-percept-trap
flight orchestration (docs/readiness/2026-08-19-ptrap-preregistration-
REGISTERED.md). Engineering-only, zero live model contact -- every test
drives either pure synthetic fixtures (``build_trap_sets``) or a
``MockCoreClient`` (``run_ptrap_flight``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters
from speech_aware_evidence_acquisition.rails.probes.ptrap_flight import (
    DEFAULT_TRAP_SEED,
    EXPECTED_SPLIT_IDENTITY_HASH,
    PTRAP_ARMS,
    TRAP_K_CAP,
    V1_ARM,
    V2_ARM,
    HarvestedWrongValue,
    PTrapArmResult,
    PTrapFlightError,
    PTrapFlightSummary,
    SampleTrapSet,
    TrapEntry,
    assert_split_identity_hash,
    build_trap_sets,
    run_ptrap_flight,
    validate_ptrap_flight_summary,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

_G0_BINDING_DIR = Path(__file__).resolve().parents[2] / "configs" / "probes" / "g0-binding"
_ROSTER_TABLE_PATH = _G0_BINDING_DIR / "pslu-rosters-train-only.json"


def _adapter(slurp_world) -> SlurpAdapter:
    lock = load_lock(slurp_world.lock_path)
    return SlurpAdapter(lock, slurp_world.data_root)


def _flight_world(slurp_world):
    adapter = _adapter(slurp_world)
    devel = adapter.load_split("devel")
    s_iot = devel[0]  # gold entities: house_place=kitchen
    s_email = devel[2]  # gold entities: () (no entities)
    return adapter, s_iot, s_email


def hv(sample_id: str, entity_type: str, filler: str) -> HarvestedWrongValue:
    return HarvestedWrongValue(sample_id=sample_id, entity_type=entity_type, filler=filler)


# ---------------------------------------------------------------------------
# split identity hash.
# ---------------------------------------------------------------------------


def test_assert_split_identity_hash_accepts_the_registered_value():
    assert_split_identity_hash(EXPECTED_SPLIT_IDENTITY_HASH)  # does not raise


def test_assert_split_identity_hash_rejects_anything_else():
    with pytest.raises(PTrapFlightError, match="does not match"):
        assert_split_identity_hash("a" * 64)


# ---------------------------------------------------------------------------
# build_trap_sets -- pure, synthetic fixtures.
# ---------------------------------------------------------------------------


def test_build_trap_sets_v1_caps_at_five_and_preserves_emission_order():
    wrong = {
        "s1": (
            hv("s1", "date", "tuesday"),
            hv("s1", "person", "bob"),
            hv("s1", "person", "alice"),
            hv("s1", "business_name", "acme"),
            hv("s1", "place_name", "paris"),
            hv("s1", "currency_name", "dollar"),  # 6th -- must be dropped by the K-cap
        )
    }
    gold = {"s1": ()}
    result = build_trap_sets(wrong_values_by_sample=wrong, gold_entities_by_sample_id=gold, sample_ids=["s1"])
    trap_set = result["s1"]
    assert trap_set.v1_k == TRAP_K_CAP == 5
    assert [e.filler for e in trap_set.v1_entries] == ["tuesday", "bob", "alice", "acme", "paris"]
    assert trap_set.own_pool_size == 6


def test_build_trap_sets_v1_excludes_gold_overlap_regardless_of_type():
    """rails.probes.ptrap_flight module docstring note 2: a WRONG-typed A0
    emission can still leak a DIFFERENT gold slot's own value."""

    wrong = {"s1": (hv("s1", "date", "six"), hv("s1", "person", "bob"))}
    gold = {"s1": (SlotEntity(type="time", filler="six"),)}  # "six" is gold, under a DIFFERENT type
    result = build_trap_sets(wrong_values_by_sample=wrong, gold_entities_by_sample_id=gold, sample_ids=["s1"])
    trap_set = result["s1"]
    assert [e.filler for e in trap_set.v1_entries] == ["bob"]
    assert [e.filler for e in trap_set.v1_excluded_gold_overlap] == ["six"]


def test_build_trap_sets_k_zero_when_pool_empty_or_sample_absent():
    gold = {"s1": (), "s2": ()}
    result = build_trap_sets(wrong_values_by_sample={}, gold_entities_by_sample_id=gold, sample_ids=["s1", "s2"])
    assert result["s1"].v1_k == 0
    assert result["s1"].v2_k == 0
    assert result["s2"].v1_k == 0


def test_build_trap_sets_v2_is_fixed_point_free():
    wrong = {
        "s1": (hv("s1", "date", "monday"),),
        "s2": (hv("s2", "date", "tuesday"),),
        "s3": (hv("s3", "date", "wednesday"),),
    }
    gold = {"s1": (), "s2": (), "s3": ()}
    result = build_trap_sets(wrong_values_by_sample=wrong, gold_entities_by_sample_id=gold, sample_ids=["s1", "s2", "s3"])
    for sample_id, trap_set in result.items():
        for entry in trap_set.v2_entries:
            assert entry.origin_sample_id != sample_id


def test_build_trap_sets_v2_length_matched_when_pool_sufficient():
    wrong = {
        "s1": (hv("s1", "date", "monday"), hv("s1", "person", "bob")),
        "s2": (hv("s2", "date", "tuesday"), hv("s2", "person", "carol")),
        "s3": (hv("s3", "date", "wednesday"), hv("s3", "person", "dave")),
    }
    gold = {"s1": (), "s2": (), "s3": ()}
    result = build_trap_sets(wrong_values_by_sample=wrong, gold_entities_by_sample_id=gold, sample_ids=["s1", "s2", "s3"])
    for trap_set in result.values():
        assert trap_set.v1_k == 2
        assert trap_set.v2_k == 2  # length-matched: donor pool (4 candidates) comfortably covers K=2


def test_build_trap_sets_v2_shrinks_when_donor_pool_runs_dry():
    """s1 has K=3 (from its own pool), but every OTHER sample together
    contributes only ONE candidate -- V2's own K must shrink to 1, never be
    padded/repeated to force equality with V1's own K."""

    wrong = {
        "s1": (hv("s1", "date", "monday"), hv("s1", "person", "bob"), hv("s1", "place_name", "paris")),
        "s2": (hv("s2", "date", "tuesday"),),
    }
    gold = {"s1": (), "s2": ()}
    result = build_trap_sets(wrong_values_by_sample=wrong, gold_entities_by_sample_id=gold, sample_ids=["s1", "s2"])
    trap_set = result["s1"]
    assert trap_set.v1_k == 3
    assert trap_set.v2_k == 1
    assert trap_set.v2_entries[0].filler == "tuesday"
    assert trap_set.v2_entries[0].origin_sample_id == "s2"


def test_build_trap_sets_v2_excludes_donor_candidates_overlapping_targets_own_gold():
    wrong = {
        "s1": (hv("s1", "date", "monday"),),
        "s2": (hv("s2", "date", "six"), hv("s2", "person", "carol")),  # "six" collides with s1's OWN gold
    }
    gold = {"s1": (SlotEntity(type="time", filler="six"),), "s2": ()}
    result = build_trap_sets(wrong_values_by_sample=wrong, gold_entities_by_sample_id=gold, sample_ids=["s1", "s2"])
    trap_set = result["s1"]
    assert trap_set.v1_k == 1
    assert [e.filler for e in trap_set.v2_entries] == ["carol"]  # "six" excluded, never drawn
    assert [e.filler for e in trap_set.v2_excluded_gold_overlap] == ["six"]


def test_build_trap_sets_is_deterministic_given_the_same_seed_and_sample_order():
    wrong = {
        "s1": (hv("s1", "date", "monday"),),
        "s2": (hv("s2", "date", "tuesday"), hv("s2", "person", "carol")),
        "s3": (hv("s3", "date", "wednesday"), hv("s3", "person", "dave")),
    }
    gold = {"s1": (), "s2": (), "s3": ()}
    first = build_trap_sets(
        wrong_values_by_sample=wrong, gold_entities_by_sample_id=gold, sample_ids=["s1", "s2", "s3"], seed=DEFAULT_TRAP_SEED
    )
    second = build_trap_sets(
        wrong_values_by_sample=wrong, gold_entities_by_sample_id=gold, sample_ids=["s3", "s1", "s2"], seed=DEFAULT_TRAP_SEED
    )
    for sample_id in ("s1", "s2", "s3"):
        assert first[sample_id].v2_entries == second[sample_id].v2_entries


def test_build_trap_sets_rejects_duplicate_sample_ids():
    with pytest.raises(PTrapFlightError, match="duplicate"):
        build_trap_sets(wrong_values_by_sample={}, gold_entities_by_sample_id={"s1": ()}, sample_ids=["s1", "s1"])


def test_build_trap_sets_rejects_missing_gold():
    with pytest.raises(PTrapFlightError, match="no gold entities"):
        build_trap_sets(wrong_values_by_sample={}, gold_entities_by_sample_id={}, sample_ids=["s1"])


# ---------------------------------------------------------------------------
# validate_ptrap_flight_summary -- fail-closed structural checks.
# ---------------------------------------------------------------------------


def _row(arm: str, sample_id: str, trap_entries: tuple[TrapEntry, ...]) -> PTrapArmResult:
    return PTrapArmResult(
        arm=arm,
        sample_id=sample_id,
        messages=(),
        response_text="{}",
        metrics={},
        consumption=None,
        k=len(trap_entries),
        trap_entries=tuple(e.as_json() for e in trap_entries),
    )


def test_validate_ptrap_flight_summary_rejects_gold_zero_overlap_violation():
    """The BINDING-TIME fail-closed check (preregistration section 2):
    every trap entry's own normalized filler must never equal a gold slot
    value of ITS OWN target sample."""

    bad_entry = TrapEntry(entity_type="date", filler="six", origin_sample_id="s1")
    rows = (_row(V1_ARM, "s1", (bad_entry,)), _row(V2_ARM, "s1", ()))
    summary = PTrapFlightSummary(results=rows, trap_sets={})
    with pytest.raises(PTrapFlightError, match="zero-overlap"):
        validate_ptrap_flight_summary(
            summary,
            expected_sample_ids=["s1"],
            gold_entities_by_sample_id={"s1": (SlotEntity(type="time", filler="six"),)},
        )


def test_validate_ptrap_flight_summary_rejects_v2_k_exceeding_v1_k():
    v1_entry = TrapEntry(entity_type="date", filler="monday", origin_sample_id="s1")
    v2_entries = (
        TrapEntry(entity_type="date", filler="tuesday", origin_sample_id="s2"),
        TrapEntry(entity_type="person", filler="bob", origin_sample_id="s2"),
    )
    rows = (_row(V1_ARM, "s1", (v1_entry,)), _row(V2_ARM, "s1", v2_entries))
    summary = PTrapFlightSummary(results=rows, trap_sets={})
    with pytest.raises(PTrapFlightError, match="length-matched"):
        validate_ptrap_flight_summary(summary, expected_sample_ids=["s1"], gold_entities_by_sample_id={"s1": ()})


def test_validate_ptrap_flight_summary_rejects_v2_fixed_point_violation():
    v1_entry = TrapEntry(entity_type="date", filler="monday", origin_sample_id="s1")
    v2_entry = TrapEntry(entity_type="date", filler="tuesday", origin_sample_id="s1")  # origin == target
    rows = (_row(V1_ARM, "s1", (v1_entry,)), _row(V2_ARM, "s1", (v2_entry,)))
    summary = PTrapFlightSummary(results=rows, trap_sets={})
    with pytest.raises(PTrapFlightError, match="fixed-point-free"):
        validate_ptrap_flight_summary(summary, expected_sample_ids=["s1"], gold_entities_by_sample_id={"s1": ()})


def test_validate_ptrap_flight_summary_rejects_v1_k_over_cap():
    entries = tuple(TrapEntry(entity_type="date", filler=f"day{i}", origin_sample_id="s1") for i in range(TRAP_K_CAP + 1))
    rows = (_row(V1_ARM, "s1", entries), _row(V2_ARM, "s1", ()))
    summary = PTrapFlightSummary(results=rows, trap_sets={})
    with pytest.raises(PTrapFlightError, match="TRAP_K_CAP"):
        validate_ptrap_flight_summary(summary, expected_sample_ids=["s1"], gold_entities_by_sample_id={"s1": ()})


def test_validate_ptrap_flight_summary_accepts_a_legal_shape():
    v1_entry = TrapEntry(entity_type="date", filler="monday", origin_sample_id="s1")
    v2_entry = TrapEntry(entity_type="date", filler="tuesday", origin_sample_id="s2")
    rows = (_row(V1_ARM, "s1", (v1_entry,)), _row(V2_ARM, "s1", (v2_entry,)))
    summary = PTrapFlightSummary(results=rows, trap_sets={})
    validate_ptrap_flight_summary(summary, expected_sample_ids=["s1"], gold_entities_by_sample_id={"s1": ()})  # does not raise


def test_validate_ptrap_flight_summary_rejects_missing_sample_id():
    rows = (_row(V1_ARM, "s1", ()), _row(V2_ARM, "s1", ()))
    summary = PTrapFlightSummary(results=rows, trap_sets={})
    with pytest.raises(PTrapFlightError, match="does not match"):
        validate_ptrap_flight_summary(summary, expected_sample_ids=["s1", "s2"], gold_entities_by_sample_id={"s1": (), "s2": ()})


# ---------------------------------------------------------------------------
# run_ptrap_flight -- end to end over the real SlurpAdapter (MockCoreClient).
# ---------------------------------------------------------------------------


def _responder(text_by_media_relpath: dict[str, str]):
    def responder(messages):
        for part in messages[1]["content"]:
            if isinstance(part, dict) and part.get("type") == "input_audio":
                return text_by_media_relpath[part["media_relpath"]]
        raise AssertionError("no input_audio content part found")

    return responder


def _trap_set(sample_id: str, v1: tuple[TrapEntry, ...], v2: tuple[TrapEntry, ...]) -> SampleTrapSet:
    return SampleTrapSet(
        sample_id=sample_id,
        v1_entries=v1,
        v2_entries=v2,
        v1_excluded_gold_overlap=(),
        v2_excluded_gold_overlap=(),
        own_pool_size=len(v1),
    )


def test_run_ptrap_flight_produces_two_requests_per_sample_in_registered_order(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    responses = {s_iot.media_relpath: "{}", s_email.media_relpath: "{}"}
    client = MockCoreClient(responder=_responder(responses))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    trap_sets = {
        s_iot.sample_id: _trap_set(
            s_iot.sample_id,
            (TrapEntry("date", "tuesday", s_iot.sample_id),),
            (TrapEntry("date", "wednesday", s_email.sample_id),),
        ),
        s_email.sample_id: _trap_set(s_email.sample_id, (), ()),
    }
    summary = run_ptrap_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email],
        base_roster_entries=rosters.full_roster, trap_sets=trap_sets,
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
    )
    assert len(summary.results) == 4  # 2 samples x 2 arms
    arms_in_order = [(row.arm, row.sample_id) for row in summary.results]
    assert arms_in_order == [
        (V1_ARM, s_iot.sample_id), (V2_ARM, s_iot.sample_id),
        (V1_ARM, s_email.sample_id), (V2_ARM, s_email.sample_id),
    ]


def test_run_ptrap_flight_rosters_include_the_base_a3_entries_plus_the_appended_traps(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    responses = {s_iot.media_relpath: "{}", s_email.media_relpath: "{}"}
    client = MockCoreClient(responder=_responder(responses))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    trap_sets = {
        s_iot.sample_id: _trap_set(s_iot.sample_id, (TrapEntry("date", "tuesday", s_iot.sample_id),), ()),
        s_email.sample_id: _trap_set(s_email.sample_id, (), ()),
    }
    summary = run_ptrap_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email],
        base_roster_entries=rosters.full_roster, trap_sets=trap_sets,
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
    )
    v1_row = next(row for row in summary.results if row.arm == V1_ARM and row.sample_id == s_iot.sample_id)
    text_parts = [part["text"] for part in v1_row.messages[1]["content"] if part.get("type") == "text"]
    assert len(text_parts) == 1
    assert text_parts[0].endswith("date=tuesday")
    assert text_parts[0].startswith(f"{rosters.full_roster[0][0]}={rosters.full_roster[0][1]}")
    assert v1_row.k == 1
    assert v1_row.trap_entries == ({"type": "date", "filler": "tuesday", "origin_sample_id": s_iot.sample_id},)


def test_run_ptrap_flight_rejects_a_wrong_split_identity_hash(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "{}"}))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    with pytest.raises(PTrapFlightError, match="does not match"):
        run_ptrap_flight(
            adapter=adapter, core_client=client, samples=[s_iot],
            base_roster_entries=rosters.full_roster, trap_sets={s_iot.sample_id: _trap_set(s_iot.sample_id, (), ())},
            split_identity_hash="a" * 64,
        )


def test_run_ptrap_flight_rejects_empty_samples(slurp_world):
    adapter, _, _ = _flight_world(slurp_world)
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    with pytest.raises(PTrapFlightError, match="at least one sample"):
        run_ptrap_flight(
            adapter=adapter, core_client=MockCoreClient(), samples=(),
            base_roster_entries=rosters.full_roster, trap_sets={},
            split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        )


def test_run_ptrap_flight_rejects_a_sample_with_no_trap_set(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "{}"}))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    with pytest.raises(PTrapFlightError, match="trap_sets carries no"):
        run_ptrap_flight(
            adapter=adapter, core_client=client, samples=[s_iot],
            base_roster_entries=rosters.full_roster, trap_sets={},
            split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        )


def test_run_ptrap_flight_rejects_a_trap_entry_leaking_this_samples_own_gold(slurp_world):
    """End-to-end proof that the binding-time fail-closed check fires even
    when the offending trap set reaches run_ptrap_flight itself (defense in
    depth on top of the unit-level validate_ptrap_flight_summary tests
    above)."""

    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "{}"}))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    leaking_entry = TrapEntry("date", "kitchen", s_iot.sample_id)  # "kitchen" is s_iot's own gold filler
    trap_sets = {s_iot.sample_id: _trap_set(s_iot.sample_id, (leaking_entry,), ())}
    with pytest.raises(PTrapFlightError, match="zero-overlap"):
        run_ptrap_flight(
            adapter=adapter, core_client=client, samples=[s_iot],
            base_roster_entries=rosters.full_roster, trap_sets=trap_sets,
            split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        )


def test_ptrap_arms_constant_matches_registered_order():
    assert PTRAP_ARMS == (V1_ARM, V2_ARM) == ("V1", "V2")
