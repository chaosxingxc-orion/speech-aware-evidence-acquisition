"""``rails.probes.pcorrf_flight``: the P-CORR-F four-arm type-corrective
supply flight orchestration (docs/readiness/2026-08-20-pcorrf-
preregistration-REGISTERED.md). Engineering-only, zero live model contact
-- every test drives either pure synthetic fixtures or a
``rails.core_client.MockCoreClient``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import MappingProxyType

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters
from speech_aware_evidence_acquisition.rails.probes.pcorrf_flight import (
    CEILING_AUDIO_SECONDS,
    CEILING_CALLS,
    CEILING_GPU_HOURS,
    DEFAULT_SEED,
    EXPECTED_SPLIT_IDENTITY_HASH,
    L2B_K,
    L2B_MIN_SCORE,
    LEGALITY_REFERENCE_SOURCE,
    LEGALITY_SPAN_SOURCE,
    LEGALITY_TIER,
    PCORRF_ARMS,
    PLANNED_TOTAL_CALLS,
    PROBE_ID,
    TRAIN_POOL_N_PAIRS,
    TRAIN_POOL_N_TYPES,
    TRAIN_POOL_N_VALUES,
    TRAIN_POOL_SHA256,
    W1_ARM,
    W2_ARM,
    W3_ARM,
    W4_ARM,
    CorrectiveEntry,
    HarvestedA0Slots,
    PCorrFArmResult,
    PCorrFBindingTable,
    PCorrFFlightError,
    PCorrFFlightSummary,
    SampleCorrectiveSet,
    TrainPool,
    assert_binding_config_sha256,
    assert_corrective_binding_hash,
    assert_ledger_row_consumed,
    assert_never_references_forbidden_gold_symbols,
    assert_pcorrf_legality,
    assert_split_identity_hash,
    assert_train_pool_sha256,
    assert_within_registered_ceilings,
    binding_config_sha256,
    build_corrective_binding,
    build_corrective_sets,
    build_execution_plan,
    build_l1_entries,
    build_l2b_entries,
    build_pcorrf_legality_values,
    compute_corrective_binding_hash,
    harvest_a0_emitted_slots,
    mine_train_pool,
    pcorrf_supply_packet,
    run_pcorrf_flight,
    validate_pcorrf_corrective_sets,
    validate_pcorrf_flight_summary,
)

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


def _pool(pairs: dict[str, tuple[str, ...]]) -> TrainPool:
    """A small synthetic TrainPool -- ``pairs``: normalized value -> legal types."""

    legal_types = {value: tuple(sorted(types)) for value, types in pairs.items()}
    canonical = {value: value for value in pairs}
    return TrainPool(
        legal_types_by_value=MappingProxyType(legal_types),
        canonical_value_by_normalized=MappingProxyType(canonical),
        all_values_sorted=tuple(sorted(pairs.keys())),
        n_pairs=sum(len(t) for t in pairs.values()),
        n_values=len(pairs),
        n_types=len({t for types in pairs.values() for t in types}),
        sha256="synthetic-pool-sha256",
    )


def _harvested(sample_id: str, slots: tuple[tuple[str, str], ...], text: str = "x") -> HarvestedA0Slots:
    return HarvestedA0Slots(
        sample_id=sample_id, emitted_slots=slots, response_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest()
    )


# ---------------------------------------------------------------------------
# Constants / split identity.
# ---------------------------------------------------------------------------


def test_pcorrf_arms_constant_matches_registered_order():
    assert PCORRF_ARMS == (W1_ARM, W2_ARM, W3_ARM, W4_ARM) == ("W1", "W2", "W3", "W4")


def test_planned_total_calls_is_240():
    assert PLANNED_TOTAL_CALLS == 240


def test_registered_ceilings():
    assert CEILING_CALLS == 260
    assert CEILING_AUDIO_SECONDS == 1000
    assert CEILING_GPU_HOURS == 0.35


def test_assert_split_identity_hash_accepts_the_registered_value():
    assert_split_identity_hash(EXPECTED_SPLIT_IDENTITY_HASH)  # does not raise


def test_assert_split_identity_hash_rejects_anything_else():
    with pytest.raises(PCorrFFlightError, match="does not match"):
        assert_split_identity_hash("a" * 64)


def test_probe_id():
    assert PROBE_ID == "SAEA-PROBE-pcorrf-240"


# ---------------------------------------------------------------------------
# Ledger anchor check (mission instruction: verify consumed=yes BEFORE
# opening the consumed artifact).
# ---------------------------------------------------------------------------


def test_assert_ledger_row_consumed_accepts_a_yes_row():
    ledger_text = "| 2026-08-17 | SAEA-PROBE-pslu-n60 | " + " | ".join(["x"] * 6) + " | yes | 450 | 1500 | 0.5 | x | x | x |"
    assert_ledger_row_consumed(ledger_text)  # does not raise


def test_assert_ledger_row_consumed_rejects_missing_row():
    with pytest.raises(PCorrFFlightError, match="no row"):
        assert_ledger_row_consumed("nothing relevant here")


def test_assert_ledger_row_consumed_rejects_no_row():
    ledger_text = "| 2026-08-17 | SAEA-PROBE-pslu-n60 | " + " | ".join(["x"] * 6) + " | no | 0 | 0 | 0 | x | x | x |"
    with pytest.raises(PCorrFFlightError, match="expected 'yes'"):
        assert_ledger_row_consumed(ledger_text)


def test_assert_ledger_row_consumed_rejects_ambiguous_rows():
    row = "| 2026-08-17 | SAEA-PROBE-pslu-n60 | " + " | ".join(["x"] * 6) + " | yes | 0 | 0 | 0 | x | x | x |"
    with pytest.raises(PCorrFFlightError, match="expected exactly one"):
        assert_ledger_row_consumed(row + "\n" + row)


# ---------------------------------------------------------------------------
# mine_train_pool -- against the tiny synthetic slurp_world train.jsonl.
# ---------------------------------------------------------------------------


def test_mine_train_pool_mines_the_fixtures_own_train_split(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    pool = mine_train_pool(lock, slurp_world.data_root)
    # slurp_world's own train.jsonl: slurp_id 301 (house_place=kitchen), 302 (no entities).
    assert pool.n_pairs == 1
    assert pool.n_values == 1
    assert pool.n_types == 1
    assert pool.legal_types_by_value["kitchen"] == ("house_place",)
    assert pool.canonical_value_by_normalized["kitchen"] == "kitchen"
    assert "kitchen" in pool.all_values_sorted


def test_mine_train_pool_is_deterministic(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    first = mine_train_pool(lock, slurp_world.data_root)
    second = mine_train_pool(lock, slurp_world.data_root)
    assert first.sha256 == second.sha256


def test_assert_train_pool_sha256_rejects_a_pool_not_matching_the_pin(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    pool = mine_train_pool(lock, slurp_world.data_root)
    with pytest.raises(PCorrFFlightError, match="drifted"):
        assert_train_pool_sha256(pool)  # the fixture's own tiny pool never matches the REAL pinned corpus


def test_train_pool_pinned_constants_are_well_formed():
    assert len(TRAIN_POOL_SHA256) == 64
    assert TRAIN_POOL_N_PAIRS == 4157
    assert TRAIN_POOL_N_VALUES == 3961
    assert TRAIN_POOL_N_TYPES == 55


# ---------------------------------------------------------------------------
# harvest_a0_emitted_slots -- gold-free, synthetic outputs.jsonl fixture.
# ---------------------------------------------------------------------------


def _write_outputs_jsonl(path: Path, rows: list[dict]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_harvest_a0_emitted_slots_reads_only_non_silence_swapped_a0_rows(tmp_path):
    attempt_dir = tmp_path / "attempt"
    _write_outputs_jsonl(
        attempt_dir / "outputs.jsonl",
        [
            {
                "arm": "A0", "sample_id": "s1", "silence_swapped": False,
                "response_text": '{"scenario": "iot", "action": "hue_lighton", "entities": [{"type": "place_name", "filler": "kitchen"}]}',
                "messages": [], "metrics": {}, "consumption": {},
            },
            {"arm": "A0", "sample_id": "s2", "silence_swapped": True, "response_text": "{}", "messages": [], "metrics": {}, "consumption": {}},
            {"arm": "A1", "sample_id": "s3", "silence_swapped": False, "response_text": "{}", "messages": [], "metrics": {}, "consumption": {}},
        ],
    )
    result = harvest_a0_emitted_slots(attempt_dir)
    assert set(result.keys()) == {"s1"}
    assert result["s1"].emitted_slots == (("place_name", "kitchen"),)
    assert len(result["s1"].response_sha256) == 64


def test_harvest_a0_emitted_slots_never_reads_gold():
    """Structural proof: harvest_a0_emitted_slots's own signature takes only
    a path -- no gold/lock/root parameter exists for it to read gold
    through."""

    import inspect

    params = inspect.signature(harvest_a0_emitted_slots).parameters
    assert list(params) == ["pslu_attempt_dir"]


def test_harvest_a0_emitted_slots_rejects_missing_attempt_dir(tmp_path):
    with pytest.raises(PCorrFFlightError, match="no outputs.jsonl"):
        harvest_a0_emitted_slots(tmp_path / "nowhere")


def test_harvest_a0_emitted_slots_rejects_duplicate_sample_rows(tmp_path):
    attempt_dir = tmp_path / "attempt"
    row = {"arm": "A0", "sample_id": "s1", "silence_swapped": False, "response_text": "{}", "messages": [], "metrics": {}, "consumption": {}}
    _write_outputs_jsonl(attempt_dir / "outputs.jsonl", [row, row])
    with pytest.raises(PCorrFFlightError, match="duplicate"):
        harvest_a0_emitted_slots(attempt_dir)


# ---------------------------------------------------------------------------
# build_l1_entries / build_l2b_entries -- pure, synthetic pool fixtures.
# ---------------------------------------------------------------------------


def test_build_l1_entries_supplies_every_legal_type_for_an_emitted_value():
    pool = _pool({"kitchen": ("house_place", "location")})
    entries = build_l1_entries((("place_name", "kitchen"),), pool, origin_sample_id="s1")
    assert entries == (
        CorrectiveEntry("house_place", "kitchen", "s1"),
        CorrectiveEntry("location", "kitchen", "s1"),
    )


def test_build_l1_entries_ignores_the_emitted_type_itself():
    """L1 never consults the emitted type -- it supplies EVERY legal type
    the pool knows for that value, which may or may not include what the
    core originally emitted."""

    pool = _pool({"kitchen": ("house_place",)})
    entries = build_l1_entries((("some_wrong_type", "kitchen"),), pool, origin_sample_id="s1")
    assert entries == (CorrectiveEntry("house_place", "kitchen", "s1"),)


def test_build_l1_entries_skips_values_with_no_pool_match():
    pool = _pool({"kitchen": ("house_place",)})
    entries = build_l1_entries((("place_name", "atlantis"),), pool, origin_sample_id="s1")
    assert entries == ()


def test_build_l1_entries_deduplicates_repeated_emitted_values():
    pool = _pool({"kitchen": ("house_place",)})
    entries = build_l1_entries((("a", "kitchen"), ("b", "kitchen")), pool, origin_sample_id="s1")
    assert entries == (CorrectiveEntry("house_place", "kitchen", "s1"),)


def test_build_l1_entries_is_empty_for_no_emitted_slots():
    pool = _pool({"kitchen": ("house_place",)})
    assert build_l1_entries((), pool, origin_sample_id="s1") == ()


def test_build_l2b_entries_widens_via_retrieval_and_excludes_l1_keys():
    pool = _pool({"kitchen": ("house_place",), "kitchenette": ("house_place",)})
    l1_keys = frozenset({("house_place", "kitchen")})
    entries = build_l2b_entries(
        (("place_name", "kitchen"),), pool, origin_sample_id="s1", exclude_keys=l1_keys, k=3, min_score=0.70
    )
    assert entries == (CorrectiveEntry("house_place", "kitchenette", "s1"),)


def test_build_l2b_entries_empty_when_no_emitted_slots():
    pool = _pool({"kitchen": ("house_place",)})
    assert build_l2b_entries((), pool, origin_sample_id="s1", exclude_keys=frozenset()) == ()


def test_l2b_default_params_match_the_registration():
    assert L2B_K == 3
    assert L2B_MIN_SCORE == 0.70


# ---------------------------------------------------------------------------
# build_corrective_sets / validate_pcorrf_corrective_sets.
# ---------------------------------------------------------------------------


def _slots(sample_id_to_slots: dict[str, tuple[tuple[str, str], ...]]):
    return sample_id_to_slots


def test_build_corrective_sets_w2_is_fixed_point_free():
    pool = _pool({"monday": ("date",), "tuesday": ("date",), "wednesday": ("date",)})
    slots = {"s1": (("date", "monday"),), "s2": (("date", "tuesday"),), "s3": (("date", "wednesday"),)}
    result = build_corrective_sets(emitted_slots_by_sample=slots, pool=pool, sample_ids=["s1", "s2", "s3"])
    for sid, cs in result.items():
        for entry in cs.w2_entries:
            assert entry.origin_sample_id != sid


def test_build_corrective_sets_w2_length_matched_when_pool_sufficient():
    pool = _pool({"monday": ("date",), "tuesday": ("date",), "wednesday": ("date",), "bob": ("person",), "carol": ("person",), "dave": ("person",)})
    slots = {
        "s1": (("date", "monday"), ("person", "bob")),
        "s2": (("date", "tuesday"), ("person", "carol")),
        "s3": (("date", "wednesday"), ("person", "dave")),
    }
    result = build_corrective_sets(emitted_slots_by_sample=slots, pool=pool, sample_ids=["s1", "s2", "s3"])
    for cs in result.values():
        assert cs.l1_k == 2
        assert cs.w2_k == 2


def test_build_corrective_sets_w2_shrinks_when_donor_pool_runs_dry():
    pool = _pool({"monday": ("date",), "bob": ("person",), "paris": ("place_name",), "tuesday": ("date",)})
    slots = {
        "s1": (("date", "monday"), ("person", "bob"), ("place_name", "paris")),
        "s2": (("date", "tuesday"),),
        "s3": (),
    }
    result = build_corrective_sets(emitted_slots_by_sample=slots, pool=pool, sample_ids=["s1", "s2", "s3"])
    assert result["s1"].l1_k == 3
    assert result["s1"].w2_k == 1  # only s2's own single entry is available as a donor
    assert result["s1"].w2_entries[0].filler == "tuesday"
    assert result["s1"].w2_entries[0].origin_sample_id == "s2"


def test_build_corrective_sets_k_zero_when_pool_has_no_match_or_sample_absent():
    pool = _pool({"kitchen": ("house_place",)})
    result = build_corrective_sets(emitted_slots_by_sample={}, pool=pool, sample_ids=["s1", "s2"])
    assert result["s1"].l1_k == 0
    assert result["s1"].w2_k == 0
    assert result["s2"].l1_k == 0


def test_build_corrective_sets_is_deterministic_given_the_same_seed_and_sample_order():
    pool = _pool({"monday": ("date",), "tuesday": ("date",), "wednesday": ("date",), "bob": ("person",), "carol": ("person",), "dave": ("person",)})
    slots = {
        "s1": (("date", "monday"),),
        "s2": (("date", "tuesday"), ("person", "carol")),
        "s3": (("date", "wednesday"), ("person", "dave")),
    }
    first = build_corrective_sets(emitted_slots_by_sample=slots, pool=pool, sample_ids=["s1", "s2", "s3"], seed=DEFAULT_SEED)
    second = build_corrective_sets(emitted_slots_by_sample=slots, pool=pool, sample_ids=["s3", "s1", "s2"], seed=DEFAULT_SEED)
    for sid in ("s1", "s2", "s3"):
        assert first[sid].w2_entries == second[sid].w2_entries


def test_build_corrective_sets_rejects_duplicate_sample_ids():
    pool = _pool({})
    with pytest.raises(PCorrFFlightError, match="duplicate"):
        build_corrective_sets(emitted_slots_by_sample={}, pool=pool, sample_ids=["s1", "s1"])


def test_build_corrective_sets_w4_added_excludes_l1_and_reports_diagnostics():
    pool = _pool({"kitchen": ("house_place",), "kitchenette": ("house_place",)})
    slots = {"s1": (("place_name", "kitchen"),)}
    result = build_corrective_sets(emitted_slots_by_sample=slots, pool=pool, sample_ids=["s1"])
    cs = result["s1"]
    assert cs.emitted_slot_count == 1
    assert cs.l1_entries == (CorrectiveEntry("house_place", "kitchen", "s1"),)
    assert cs.w4_added_entries == (CorrectiveEntry("house_place", "kitchenette", "s1"),)


def test_validate_pcorrf_corrective_sets_rejects_a_length_mismatch():
    good = SampleCorrectiveSet(
        sample_id="s1",
        l1_entries=(CorrectiveEntry("date", "monday", "s1"),),
        w2_entries=(CorrectiveEntry("date", "tuesday", "s2"), CorrectiveEntry("person", "bob", "s2")),
        w4_added_entries=(),
        emitted_slot_count=1,
    )
    with pytest.raises(PCorrFFlightError, match="length-matched"):
        validate_pcorrf_corrective_sets({"s1": good}, expected_sample_ids=["s1"])


def test_validate_pcorrf_corrective_sets_rejects_a_fixed_point_violation():
    bad = SampleCorrectiveSet(
        sample_id="s1",
        l1_entries=(CorrectiveEntry("date", "monday", "s1"),),
        w2_entries=(CorrectiveEntry("date", "tuesday", "s1"),),  # origin == target
        w4_added_entries=(),
        emitted_slot_count=1,
    )
    with pytest.raises(PCorrFFlightError, match="fixed-point-free"):
        validate_pcorrf_corrective_sets({"s1": bad}, expected_sample_ids=["s1"])


def test_validate_pcorrf_corrective_sets_rejects_a_w4_l1_duplicate():
    bad = SampleCorrectiveSet(
        sample_id="s1",
        l1_entries=(CorrectiveEntry("house_place", "kitchen", "s1"),),
        w2_entries=(),
        w4_added_entries=(CorrectiveEntry("house_place", "kitchen", "s1"),),  # duplicates L1
        emitted_slot_count=1,
    )
    with pytest.raises(PCorrFFlightError, match="dedupe invariant"):
        validate_pcorrf_corrective_sets({"s1": bad}, expected_sample_ids=["s1"])


def test_validate_pcorrf_corrective_sets_rejects_a_missing_sample():
    with pytest.raises(PCorrFFlightError, match="does not match"):
        validate_pcorrf_corrective_sets({}, expected_sample_ids=["s1"])


def test_validate_pcorrf_corrective_sets_accepts_a_legal_shape():
    good = SampleCorrectiveSet(
        sample_id="s1",
        l1_entries=(CorrectiveEntry("date", "monday", "s1"),),
        w2_entries=(CorrectiveEntry("date", "tuesday", "s2"),),
        w4_added_entries=(CorrectiveEntry("place_name", "paris", "s1"),),
        emitted_slot_count=1,
    )
    validate_pcorrf_corrective_sets({"s1": good}, expected_sample_ids=["s1"])  # does not raise


# ---------------------------------------------------------------------------
# Tri-derivation corrective binding hash (guard 1).
# ---------------------------------------------------------------------------


def test_compute_corrective_binding_hash_is_deterministic():
    a = compute_corrective_binding_hash(response_sha256_by_sample={"s1": "aa", "s2": "bb"}, pool_sha256="pp", seed=1)
    b = compute_corrective_binding_hash(response_sha256_by_sample={"s2": "bb", "s1": "aa"}, pool_sha256="pp", seed=1)
    assert a == b
    assert len(a) == 64


def test_compute_corrective_binding_hash_changes_with_any_input():
    base = compute_corrective_binding_hash(response_sha256_by_sample={"s1": "aa"}, pool_sha256="pp", seed=1)
    assert compute_corrective_binding_hash(response_sha256_by_sample={"s1": "ab"}, pool_sha256="pp", seed=1) != base
    assert compute_corrective_binding_hash(response_sha256_by_sample={"s1": "aa"}, pool_sha256="qq", seed=1) != base
    assert compute_corrective_binding_hash(response_sha256_by_sample={"s1": "aa"}, pool_sha256="pp", seed=2) != base


def test_build_corrective_binding_embeds_a_hash_that_the_validator_reproduces():
    pool = _pool({"kitchen": ("house_place",)})
    harvested = {"s1": _harvested("s1", (("place_name", "kitchen"),), text="hello")}
    table = build_corrective_binding(harvested=harvested, pool=pool, sample_ids=["s1"], seed=DEFAULT_SEED)
    assert_corrective_binding_hash(table, harvested=harvested, seed=DEFAULT_SEED)  # site #2 -- does not raise


def test_assert_corrective_binding_hash_rejects_a_tampered_table():
    pool = _pool({"kitchen": ("house_place",)})
    harvested = {"s1": _harvested("s1", (("place_name", "kitchen"),), text="hello")}
    table = build_corrective_binding(harvested=harvested, pool=pool, sample_ids=["s1"], seed=DEFAULT_SEED)
    tampered = PCorrFBindingTable(
        corrective_sets=table.corrective_sets, pool_sha256=table.pool_sha256, seed=table.seed, binding_hash="deadbeef"
    )
    with pytest.raises(PCorrFFlightError, match="mismatch"):
        assert_corrective_binding_hash(tampered, harvested=harvested, seed=DEFAULT_SEED)


def test_assert_corrective_binding_hash_rejects_a_changed_a0_response():
    pool = _pool({"kitchen": ("house_place",)})
    harvested = {"s1": _harvested("s1", (("place_name", "kitchen"),), text="hello")}
    table = build_corrective_binding(harvested=harvested, pool=pool, sample_ids=["s1"], seed=DEFAULT_SEED)
    drifted_harvested = {"s1": _harvested("s1", (("place_name", "kitchen"),), text="a different response")}
    with pytest.raises(PCorrFFlightError, match="mismatch"):
        assert_corrective_binding_hash(table, harvested=drifted_harvested, seed=DEFAULT_SEED)


def test_assert_corrective_binding_hash_rejects_a_seed_mismatch():
    pool = _pool({"kitchen": ("house_place",)})
    harvested = {"s1": _harvested("s1", (("place_name", "kitchen"),), text="hello")}
    table = build_corrective_binding(harvested=harvested, pool=pool, sample_ids=["s1"], seed=DEFAULT_SEED)
    with pytest.raises(PCorrFFlightError, match="seed"):
        assert_corrective_binding_hash(table, harvested=harvested, seed=DEFAULT_SEED + 1)


# ---------------------------------------------------------------------------
# Guard 2: source-introspection, forbidden gold symbols.
# ---------------------------------------------------------------------------


def test_assert_never_references_forbidden_gold_symbols_accepts_the_real_module_source():
    assert_never_references_forbidden_gold_symbols()  # does not raise (checks THIS module's own source)


@pytest.mark.parametrize(
    "snippet",
    [
        "from speech_aware_evidence_acquisition.analysis.ptrap_read import harvest_a0_wrong_values",
        "from speech_aware_evidence_acquisition.data.slurp import load_slurp_split",
        "from speech_aware_evidence_acquisition.analysis.pslu_read import load_gold_by_sample_id",
        "x = harvest_a0_wrong_values",
        "y = some_module.load_slurp_split",
    ],
)
def test_assert_never_references_forbidden_gold_symbols_rejects_forbidden_references(snippet):
    with pytest.raises(PCorrFFlightError, match="forbidden symbol"):
        assert_never_references_forbidden_gold_symbols(snippet)


def test_assert_never_references_forbidden_gold_symbols_allows_prose_mention_only_via_ast():
    """Docstring-only prose naming a forbidden symbol is fine (module
    docstring: AST-based, never a substring search) -- but a REAL reference
    in code is not; this test proves the checker parses actual code, not
    docstrings, by using a snippet whose only text is a string literal."""

    snippet = 'x = "harvest_a0_wrong_values mentioned only as a string, never referenced"'
    assert_never_references_forbidden_gold_symbols(snippet)  # does not raise


# ---------------------------------------------------------------------------
# Legality guard 3.
# ---------------------------------------------------------------------------


def test_legality_declared_values_match_the_registration():
    assert LEGALITY_SPAN_SOURCE == "percept-keyed-type-lookup"
    assert LEGALITY_REFERENCE_SOURCE == "slurp-train-ontology"
    assert LEGALITY_TIER == "legal"


def test_build_pcorrf_legality_values_shape():
    values = build_pcorrf_legality_values()
    assert values["span_source"] == LEGALITY_SPAN_SOURCE
    assert values["reference_source"] == LEGALITY_REFERENCE_SOURCE
    assert values["legality_tier"] == LEGALITY_TIER


def test_assert_pcorrf_legality_never_refuses(tmp_path):
    assert_pcorrf_legality(tmp_path)  # does not raise (neither declared value is a ceiling marker)


# ---------------------------------------------------------------------------
# Ceilings + contracts.ExecutionPlan.
# ---------------------------------------------------------------------------


def test_assert_within_registered_ceilings_accepts_the_registered_plan():
    assert_within_registered_ceilings(calls=240, audio_seconds=730, gpu_hours=0.15)  # does not raise


def test_assert_within_registered_ceilings_rejects_over_budget_calls():
    with pytest.raises(PCorrFFlightError, match="calls exceeds"):
        assert_within_registered_ceilings(calls=CEILING_CALLS + 1, audio_seconds=1, gpu_hours=0.01)


def test_assert_within_registered_ceilings_rejects_over_budget_audio():
    with pytest.raises(PCorrFFlightError, match="audio-second"):
        assert_within_registered_ceilings(calls=1, audio_seconds=CEILING_AUDIO_SECONDS + 1, gpu_hours=0.01)


def test_assert_within_registered_ceilings_rejects_over_budget_gpu():
    with pytest.raises(PCorrFFlightError, match="GPU-hour"):
        assert_within_registered_ceilings(calls=1, audio_seconds=1, gpu_hours=CEILING_GPU_HOURS + 0.01)


def test_build_execution_plan_validates_cleanly():
    plan = build_execution_plan()
    assert plan.run_id == PROBE_ID
    assert plan.execution_profile == "bounded-discovery-probe"
    assert plan.split_role == "discovery"
    assert plan.split_identity_hash == EXPECTED_SPLIT_IDENTITY_HASH
    assert plan.planned_model_calls == PLANNED_TOTAL_CALLS


def test_build_execution_plan_rejects_an_over_ceiling_plan():
    with pytest.raises(Exception):
        build_execution_plan(planned_model_calls=CEILING_CALLS + 1)


def test_binding_config_sha256_is_pinned():
    assert_binding_config_sha256()  # does not raise
    assert len(binding_config_sha256()) == 64


# ---------------------------------------------------------------------------
# pcorrf_supply_packet -- per-arm rendering shapes.
# ---------------------------------------------------------------------------


def _sample_corrective_set(l1=(), w2=(), w4_added=()) -> SampleCorrectiveSet:
    return SampleCorrectiveSet(sample_id="s1", l1_entries=l1, w2_entries=w2, w4_added_entries=w4_added, emitted_slot_count=1)


def test_pcorrf_supply_packet_w1_is_a3_plus_l1():
    cs = _sample_corrective_set(l1=(CorrectiveEntry("house_place", "kitchen", "s1"),))
    packet = pcorrf_supply_packet(W1_ARM, "s1", base_roster_entries=(("date", "monday"),), corrective_set=cs)
    assert packet is not None
    assert packet.dose.n_items == 2
    assert packet.prompt_block == "date=monday; house_place=kitchen"


def test_pcorrf_supply_packet_w2_is_a3_plus_cross_sample_entries():
    cs = _sample_corrective_set(w2=(CorrectiveEntry("house_place", "kitchen", "s2"),))
    packet = pcorrf_supply_packet(W2_ARM, "s1", base_roster_entries=(("date", "monday"),), corrective_set=cs)
    assert packet is not None
    assert packet.prompt_block == "date=monday; house_place=kitchen"


def test_pcorrf_supply_packet_w3_is_l1_alone_never_the_a3_base():
    cs = _sample_corrective_set(l1=(CorrectiveEntry("house_place", "kitchen", "s1"),))
    packet = pcorrf_supply_packet(W3_ARM, "s1", base_roster_entries=(("date", "monday"),), corrective_set=cs)
    assert packet is not None
    assert packet.prompt_block == "house_place=kitchen"  # base roster never appears


def test_pcorrf_supply_packet_w3_is_none_when_l1_is_empty():
    """K=0 under L1 -> W3 flies TRUE zero-supply (module docstring: never
    an empty-but-present roster block)."""

    cs = _sample_corrective_set(l1=())
    packet = pcorrf_supply_packet(W3_ARM, "s1", base_roster_entries=(("date", "monday"),), corrective_set=cs)
    assert packet is None


def test_pcorrf_supply_packet_w4_is_a3_plus_l1_plus_l2b():
    cs = _sample_corrective_set(
        l1=(CorrectiveEntry("house_place", "kitchen", "s1"),),
        w4_added=(CorrectiveEntry("house_place", "kitchenette", "s1"),),
    )
    packet = pcorrf_supply_packet(W4_ARM, "s1", base_roster_entries=(("date", "monday"),), corrective_set=cs)
    assert packet is not None
    assert packet.prompt_block == "date=monday; house_place=kitchen; house_place=kitchenette"


def test_pcorrf_supply_packet_rejects_unknown_arm():
    cs = _sample_corrective_set()
    with pytest.raises(PCorrFFlightError, match="unknown P-CORR-F arm"):
        pcorrf_supply_packet("W9", "s1", base_roster_entries=(), corrective_set=cs)


# ---------------------------------------------------------------------------
# validate_pcorrf_flight_summary -- fail-closed structural checks.
# ---------------------------------------------------------------------------


def _row(arm: str, sample_id: str, entries: tuple[CorrectiveEntry, ...]) -> PCorrFArmResult:
    return PCorrFArmResult(
        arm=arm, sample_id=sample_id, messages=(), response_text="{}", metrics={}, consumption=None,
        k=len(entries), corrective_entries=tuple(e.as_json() for e in entries),
    )


def test_validate_pcorrf_flight_summary_rejects_duplicate_rows():
    rows = (_row(W1_ARM, "s1", ()), _row(W1_ARM, "s1", ()))
    with pytest.raises(PCorrFFlightError, match="duplicate row"):
        validate_pcorrf_flight_summary(PCorrFFlightSummary(results=rows, binding_table=None), expected_sample_ids=["s1"])


def test_validate_pcorrf_flight_summary_rejects_w2_fixed_point_violation():
    entry = CorrectiveEntry("date", "monday", "s1")  # origin == target
    rows = (_row(W2_ARM, "s1", (entry,)),)
    with pytest.raises(PCorrFFlightError, match="fixed-point-free"):
        validate_pcorrf_flight_summary(PCorrFFlightSummary(results=rows, binding_table=None), expected_sample_ids=["s1"])


def test_validate_pcorrf_flight_summary_rejects_w2_k_exceeding_w1_k():
    w1_entry = CorrectiveEntry("date", "monday", "s1")
    w2_entries = (CorrectiveEntry("date", "tuesday", "s2"), CorrectiveEntry("person", "bob", "s2"))
    rows = (_row(W1_ARM, "s1", (w1_entry,)), _row(W2_ARM, "s1", w2_entries))
    with pytest.raises(PCorrFFlightError, match="length-matched"):
        validate_pcorrf_flight_summary(PCorrFFlightSummary(results=rows, binding_table=None), expected_sample_ids=["s1"])


def test_validate_pcorrf_flight_summary_rejects_a_row_outside_the_manifest():
    rows = (_row(W1_ARM, "unknown-sample", ()),)
    with pytest.raises(PCorrFFlightError, match="not in the expected"):
        validate_pcorrf_flight_summary(PCorrFFlightSummary(results=rows, binding_table=None), expected_sample_ids=["s1"])


def test_validate_pcorrf_flight_summary_accepts_a_partial_idempotent_shape():
    """Deliberately not a completeness check (module docstring): a partial
    summary from an idempotent resume is a legal shape."""

    rows = (_row(W1_ARM, "s1", ()),)
    validate_pcorrf_flight_summary(PCorrFFlightSummary(results=rows, binding_table=None), expected_sample_ids=["s1", "s2"])


# ---------------------------------------------------------------------------
# run_pcorrf_flight -- end to end over the real SlurpAdapter (MockCoreClient).
# ---------------------------------------------------------------------------


def _responder(text_by_media_relpath: dict[str, str]):
    def responder(messages):
        for part in messages[1]["content"]:
            if isinstance(part, dict) and part.get("type") == "input_audio":
                return text_by_media_relpath[part["media_relpath"]]
        raise AssertionError("no input_audio content part found")

    return responder


def _binding_for(samples, pool, seed=DEFAULT_SEED) -> tuple[PCorrFBindingTable, dict[str, HarvestedA0Slots]]:
    harvested = {sample.sample_id: _harvested(sample.sample_id, (), text=sample.sample_id) for sample in samples}
    table = build_corrective_binding(harvested=harvested, pool=pool, sample_ids=[s.sample_id for s in samples], seed=seed)
    return table, harvested


def test_run_pcorrf_flight_produces_four_requests_per_sample_in_registered_order(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    responses = {s_iot.media_relpath: "{}", s_email.media_relpath: "{}"}
    client = MockCoreClient(responder=_responder(responses))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    pool = _pool({})
    table, harvested = _binding_for([s_iot, s_email], pool)
    summary = run_pcorrf_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email],
        base_roster_entries=rosters.full_roster, binding_table=table, harvested=harvested,
        root=slurp_world.data_root, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
    )
    assert len(summary.results) == 8  # 2 samples x 4 arms
    arms_in_order = [(row.arm, row.sample_id) for row in summary.results]
    assert arms_in_order == [
        (W1_ARM, s_iot.sample_id), (W2_ARM, s_iot.sample_id), (W3_ARM, s_iot.sample_id), (W4_ARM, s_iot.sample_id),
        (W1_ARM, s_email.sample_id), (W2_ARM, s_email.sample_id), (W3_ARM, s_email.sample_id), (W4_ARM, s_email.sample_id),
    ]


def test_run_pcorrf_flight_w3_flies_zero_supply_when_l1_is_empty(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "{}"}))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    pool = _pool({})  # no legal values at all -> every L1/L2b is empty
    table, harvested = _binding_for([s_iot], pool)
    summary = run_pcorrf_flight(
        adapter=adapter, core_client=client, samples=[s_iot],
        base_roster_entries=rosters.full_roster, binding_table=table, harvested=harvested,
        root=slurp_world.data_root, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
    )
    w3_row = next(row for row in summary.results if row.arm == W3_ARM)
    assert w3_row.k == 0
    assert len(w3_row.messages[1]["content"]) == 1  # audio only, no text supply block


def test_run_pcorrf_flight_skips_already_completed_cells(slurp_world):
    """Arm-level (and row-level) idempotence: a cell already present in
    ``already_completed`` is NEVER re-fired."""

    adapter, s_iot, s_email = _flight_world(slurp_world)
    responses = {s_iot.media_relpath: "{}", s_email.media_relpath: "{}"}
    client = MockCoreClient(responder=_responder(responses))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    pool = _pool({})
    table, harvested = _binding_for([s_iot, s_email], pool)
    already_completed = {W1_ARM: frozenset({s_iot.sample_id, s_email.sample_id}), W2_ARM: frozenset({s_iot.sample_id})}
    summary = run_pcorrf_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email],
        base_roster_entries=rosters.full_roster, binding_table=table, harvested=harvested,
        root=slurp_world.data_root, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        already_completed=already_completed,
    )
    fired = {(row.arm, row.sample_id) for row in summary.results}
    assert (W1_ARM, s_iot.sample_id) not in fired
    assert (W1_ARM, s_email.sample_id) not in fired
    assert (W2_ARM, s_iot.sample_id) not in fired
    assert (W2_ARM, s_email.sample_id) in fired
    assert len(client.calls) == 5  # 8 total cells - 2 skipped W1 - 1 skipped W2 = 5


def test_run_pcorrf_flight_rejects_a_wrong_split_identity_hash(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "{}"}))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    pool = _pool({})
    table, harvested = _binding_for([s_iot], pool)
    with pytest.raises(PCorrFFlightError, match="does not match"):
        run_pcorrf_flight(
            adapter=adapter, core_client=client, samples=[s_iot],
            base_roster_entries=rosters.full_roster, binding_table=table, harvested=harvested,
            root=slurp_world.data_root, split_identity_hash="a" * 64,
        )


def test_run_pcorrf_flight_rejects_empty_samples(slurp_world):
    adapter, _, _ = _flight_world(slurp_world)
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    pool = _pool({})
    table, harvested = _binding_for([], pool)
    with pytest.raises(PCorrFFlightError, match="at least one sample"):
        run_pcorrf_flight(
            adapter=adapter, core_client=MockCoreClient(), samples=(),
            base_roster_entries=rosters.full_roster, binding_table=table, harvested=harvested,
            root=slurp_world.data_root, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        )


def test_run_pcorrf_flight_rejects_a_sample_with_no_binding_entry(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "{}"}))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    empty_table = PCorrFBindingTable(corrective_sets={}, pool_sha256="p", seed=DEFAULT_SEED, binding_hash=compute_corrective_binding_hash(response_sha256_by_sample={}, pool_sha256="p", seed=DEFAULT_SEED))
    with pytest.raises(PCorrFFlightError, match="binding_table carries no"):
        run_pcorrf_flight(
            adapter=adapter, core_client=client, samples=[s_iot],
            base_roster_entries=rosters.full_roster, binding_table=empty_table, harvested={},
            root=slurp_world.data_root, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        )


def test_run_pcorrf_flight_rejects_a_tampered_binding_hash(slurp_world):
    """End-to-end proof that the tri-derivation guard's THIRD site (flight
    preflight) actually fires."""

    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "{}"}))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    pool = _pool({})
    table, harvested = _binding_for([s_iot], pool)
    tampered = PCorrFBindingTable(
        corrective_sets=table.corrective_sets, pool_sha256=table.pool_sha256, seed=table.seed, binding_hash="deadbeef"
    )
    with pytest.raises(PCorrFFlightError, match="mismatch"):
        run_pcorrf_flight(
            adapter=adapter, core_client=client, samples=[s_iot],
            base_roster_entries=rosters.full_roster, binding_table=tampered, harvested=harvested,
            root=slurp_world.data_root, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        )


def test_run_pcorrf_flight_rejects_over_ceiling_planned_calls(slurp_world):
    """66 samples x 4 arms = 264 > CEILING_CALLS=260 -- the flight's own
    internal calls-ceiling recheck must refuse BEFORE issuing any request
    (never merely rely on the caller having built an over-sized samples
    list without a plan-level check)."""

    import dataclasses

    adapter, s_iot, _ = _flight_world(slurp_world)
    samples = [dataclasses.replace(s_iot, sample_id=f"{s_iot.sample_id}-fake-{i}") for i in range(66)]
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "{}"}))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    pool = _pool({})
    table, harvested = _binding_for(samples, pool)
    with pytest.raises(PCorrFFlightError, match="exceeds the registered ceiling"):
        run_pcorrf_flight(
            adapter=adapter, core_client=client, samples=samples,
            base_roster_entries=rosters.full_roster, binding_table=table, harvested=harvested,
            root=slurp_world.data_root, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        )
    assert len(client.calls) == 0  # refused BEFORE issuing any request
