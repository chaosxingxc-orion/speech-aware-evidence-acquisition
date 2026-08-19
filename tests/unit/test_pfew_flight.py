"""``rails.probes.pfew_flight``: the P-FEW three-arm routing few-shot form
probe flight orchestration (docs/readiness/2026-08-19-pfew-preregistration-
REGISTERED.md). Engineering-only, zero live model contact -- every test
drives either pure synthetic fixtures (``build_demo_binding``,
``pfew_supply_packet``) or a ``MockCoreClient`` (``run_pfew_flight``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import (
    ClosedSetMapping,
    canonical_scenario_labels,
    closed_set_phase1_supply_packet,
)
from speech_aware_evidence_acquisition.rails.probes.pfew_flight import (
    DEFAULT_DEMO_SEED,
    EXPECTED_SPLIT_IDENTITY_HASH,
    FS_BAL_ARM,
    FS_BAL_K,
    FS_NONE_ARM,
    FS_SKEW_ARM,
    FS_SKEW_K,
    PFEW_ARMS,
    DemoBinding,
    DemoCandidate,
    PFewArmResult,
    PFewFlightError,
    PFewFlightSummary,
    SampleDemoSet,
    assert_split_identity_hash,
    build_demo_binding,
    compute_demo_binding_sha256,
    pfew_supply_packet,
    run_pfew_flight,
    validate_pfew_flight_summary,
)

_G0_BINDING_DIR = Path(__file__).resolve().parents[2] / "configs" / "probes" / "g0-binding"
_ROSTER_TABLE_PATH = _G0_BINDING_DIR / "pslu-rosters-train-only.json"


def _adapter(slurp_world) -> SlurpAdapter:
    lock = load_lock(slurp_world.lock_path)
    return SlurpAdapter(lock, slurp_world.data_root)


def _flight_world(slurp_world):
    adapter = _adapter(slurp_world)
    devel = adapter.load_split("devel")
    s_iot = devel[0]  # gold scenario "iot" (mirrors test_ptrap_flight.py's own _flight_world)
    s_email = devel[2]  # gold scenario "email" -- devel[1] is 101's OWN second recording, still "iot"
    return adapter, s_iot, s_email


@dataclass(frozen=True)
class _TargetStub:
    """Minimal duck-typed stand-in for ``SlurpSample`` -- ``build_demo_binding``
    only ever reads ``.sample_id``/``.utterance_id`` off a target."""

    sample_id: str
    utterance_id: str


def _pool(labels: list[str], per_label: int) -> dict[str, tuple[DemoCandidate, ...]]:
    """A synthetic TRAIN demo pool: ``per_label`` candidates for each of
    ``labels``, globally-unique numeric train_sample_ids."""

    pool: dict[str, tuple[DemoCandidate, ...]] = {}
    counter = 0
    for label in labels:
        entries = []
        for _ in range(per_label):
            entries.append(
                DemoCandidate(
                    train_sample_id=f"slurp:train:{counter:06d}",
                    utterance_text=f"utterance {counter} about {label}",
                    scenario_label=label,
                )
            )
            counter += 1
        pool[label] = tuple(entries)
    return pool


_LABELS = ["alarm", "calendar", "email", "iot", "music", "weather"]


# ---------------------------------------------------------------------------
# split identity hash.
# ---------------------------------------------------------------------------


def test_assert_split_identity_hash_accepts_the_registered_value():
    assert_split_identity_hash(EXPECTED_SPLIT_IDENTITY_HASH)  # does not raise


def test_assert_split_identity_hash_rejects_anything_else():
    with pytest.raises(PFewFlightError, match="does not match"):
        assert_split_identity_hash("a" * 64)


# ---------------------------------------------------------------------------
# build_demo_binding -- pure, synthetic fixtures.
# ---------------------------------------------------------------------------


def test_build_demo_binding_fs_bal_draws_four_distinct_labels_and_demos():
    pool = _pool(_LABELS, per_label=5)
    targets = [_TargetStub(sample_id=f"slurp:devel:{i:06d}:a", utterance_id=str(900000 + i)) for i in range(3)]
    binding = build_demo_binding(demo_pool=pool, canonical_labels=_LABELS, target_samples=targets)
    for target in targets:
        demo_set = binding.per_sample[target.sample_id]
        assert len(demo_set.fs_bal_demos) == FS_BAL_K
        labels = [d.scenario_label for d in demo_set.fs_bal_demos]
        assert len(set(labels)) == FS_BAL_K  # label-balanced: 4 distinct
        assert all(label in _LABELS for label in labels)


def test_build_demo_binding_fs_skew_all_demos_carry_the_seeded_skew_label():
    pool = _pool(_LABELS, per_label=5)
    targets = [_TargetStub(sample_id=f"slurp:devel:{i:06d}:a", utterance_id=str(900000 + i)) for i in range(3)]
    binding = build_demo_binding(demo_pool=pool, canonical_labels=_LABELS, target_samples=targets)
    assert binding.skew_label in _LABELS
    for target in targets:
        demo_set = binding.per_sample[target.sample_id]
        assert len(demo_set.fs_skew_demos) == FS_SKEW_K
        labels = {d.scenario_label for d in demo_set.fs_skew_demos}
        assert labels == {binding.skew_label}
        # all 4 demo transcripts are themselves distinct train candidates.
        assert len({d.train_sample_id for d in demo_set.fs_skew_demos}) == FS_SKEW_K


def test_build_demo_binding_skew_label_is_one_global_seeded_pick():
    """Registered legal resolution (module docstring): ONE seeded pick for
    the WHOLE arm, never per-sample -- predictable directly from
    random.Random(seed).choice(canonical_labels)."""

    pool = _pool(_LABELS, per_label=5)
    targets = [_TargetStub(sample_id=f"slurp:devel:{i:06d}:a", utterance_id=str(900000 + i)) for i in range(4)]
    binding = build_demo_binding(
        demo_pool=pool, canonical_labels=_LABELS, target_samples=targets, seed=DEFAULT_DEMO_SEED
    )
    expected_skew_label = random.Random(DEFAULT_DEMO_SEED).choice(tuple(_LABELS))
    assert binding.skew_label == expected_skew_label


def test_build_demo_binding_never_draws_a_targets_own_recording():
    """Structural: demos are TRAIN-only, targets are DEVEL-only -- no
    fs_bal/fs_skew demo's own train_sample_id can ever equal a target's own
    sample_id (checked directly, on top of the devel-overlap refusal test
    below which covers the slurp_id-collision case)."""

    pool = _pool(_LABELS, per_label=5)
    targets = [_TargetStub(sample_id=f"slurp:devel:{i:06d}:a", utterance_id=str(900000 + i)) for i in range(3)]
    binding = build_demo_binding(demo_pool=pool, canonical_labels=_LABELS, target_samples=targets)
    target_ids = {t.sample_id for t in targets}
    for demo_set in binding.per_sample.values():
        for demo in demo_set.fs_bal_demos + demo_set.fs_skew_demos:
            assert demo.train_sample_id not in target_ids
            assert demo.train_sample_id.startswith("slurp:train:")


def test_build_demo_binding_is_deterministic_given_the_same_seed():
    pool = _pool(_LABELS, per_label=5)
    targets = [_TargetStub(sample_id=f"slurp:devel:{i:06d}:a", utterance_id=str(900000 + i)) for i in range(5)]
    first = build_demo_binding(demo_pool=pool, canonical_labels=_LABELS, target_samples=targets, seed=DEFAULT_DEMO_SEED)
    second = build_demo_binding(demo_pool=pool, canonical_labels=_LABELS, target_samples=targets, seed=DEFAULT_DEMO_SEED)
    assert first.sha256 == second.sha256
    assert first.skew_label == second.skew_label
    for sample_id in first.per_sample:
        assert first.per_sample[sample_id].fs_bal_demos == second.per_sample[sample_id].fs_bal_demos
        assert first.per_sample[sample_id].fs_skew_demos == second.per_sample[sample_id].fs_skew_demos


def test_build_demo_binding_hash_pins_the_manifest_and_changes_with_a_different_target_set():
    pool = _pool(_LABELS, per_label=5)
    targets_a = [_TargetStub(sample_id=f"slurp:devel:{i:06d}:a", utterance_id=str(900000 + i)) for i in range(3)]
    targets_b = [_TargetStub(sample_id=f"slurp:devel:{i:06d}:a", utterance_id=str(900000 + i)) for i in range(4)]
    binding_a = build_demo_binding(demo_pool=pool, canonical_labels=_LABELS, target_samples=targets_a)
    binding_b = build_demo_binding(demo_pool=pool, canonical_labels=_LABELS, target_samples=targets_b)
    assert binding_a.sha256 != binding_b.sha256
    assert len(binding_a.sha256) == 64
    assert compute_demo_binding_sha256({"a": 1}) == compute_demo_binding_sha256({"a": 1})


def test_build_demo_binding_refuses_a_demo_that_shares_slurp_id_with_a_target_devel_sample():
    """Binding-time fail-closed check (registration section 5): "no demo
    recording id in devel". Every candidate in the pool is deliberately
    made to collide with the SAME target's own utterance_id, so ANY draw
    (regardless of RNG choice) trips the refusal."""

    colliding_utterance_id = "777777"
    pool: dict[str, tuple[DemoCandidate, ...]] = {}
    for label in _LABELS:
        pool[label] = tuple(
            DemoCandidate(
                train_sample_id=f"slurp:train:{colliding_utterance_id}",
                utterance_text=f"utterance about {label}",
                scenario_label=label,
            )
            for _ in range(5)
        )
    targets = [_TargetStub(sample_id="slurp:devel:000001:a", utterance_id=colliding_utterance_id)]
    with pytest.raises(PFewFlightError, match="devel-overlap"):
        build_demo_binding(demo_pool=pool, canonical_labels=_LABELS, target_samples=targets)


def test_build_demo_binding_refuses_insufficient_label_coverage():
    pool = _pool(["alarm", "calendar", "email"], per_label=5)  # only 3 distinct labels, need >= 4
    targets = [_TargetStub(sample_id="slurp:devel:000001:a", utterance_id="1")]
    with pytest.raises(PFewFlightError, match="FS-BAL needs"):
        build_demo_binding(demo_pool=pool, canonical_labels=_LABELS, target_samples=targets)


def test_build_demo_binding_refuses_insufficient_skew_pool():
    labels = list(_LABELS)
    expected_skew_label = random.Random(DEFAULT_DEMO_SEED).choice(tuple(labels))
    pool = _pool(labels, per_label=5)
    pool[expected_skew_label] = pool[expected_skew_label][:2]  # starve the label that WILL be chosen
    targets = [_TargetStub(sample_id="slurp:devel:000001:a", utterance_id="1")]
    with pytest.raises(PFewFlightError, match="FS-SKEW needs"):
        build_demo_binding(demo_pool=pool, canonical_labels=labels, target_samples=targets)


def test_build_demo_binding_rejects_duplicate_target_sample_ids():
    pool = _pool(_LABELS, per_label=5)
    targets = [
        _TargetStub(sample_id="slurp:devel:000001:a", utterance_id="1"),
        _TargetStub(sample_id="slurp:devel:000001:a", utterance_id="2"),
    ]
    with pytest.raises(PFewFlightError, match="duplicate"):
        build_demo_binding(demo_pool=pool, canonical_labels=_LABELS, target_samples=targets)


def test_build_demo_binding_rejects_empty_inputs():
    with pytest.raises(PFewFlightError, match="at least one canonical label"):
        build_demo_binding(demo_pool={}, canonical_labels=(), target_samples=[_TargetStub("s1", "1")])
    with pytest.raises(PFewFlightError, match="at least one target sample"):
        build_demo_binding(demo_pool=_pool(_LABELS, 5), canonical_labels=_LABELS, target_samples=[])


# ---------------------------------------------------------------------------
# pfew_supply_packet -- reuses closed_set_phase1_supply_packet verbatim.
# ---------------------------------------------------------------------------


def test_pfew_supply_packet_fs_none_reuses_closed_set_packet_unmodified():
    packet = pfew_supply_packet(FS_NONE_ARM, (), _LABELS)
    assert packet == closed_set_phase1_supply_packet(_LABELS)


def test_pfew_supply_packet_fs_none_rejects_nonempty_demos():
    demos = (DemoCandidate("slurp:train:000000", "hi", "iot"),)
    with pytest.raises(PFewFlightError, match="zero demos"):
        pfew_supply_packet(FS_NONE_ARM, demos, _LABELS)


def test_pfew_supply_packet_fs_bal_and_fs_skew_require_demos():
    with pytest.raises(PFewFlightError, match="at least one demo"):
        pfew_supply_packet(FS_BAL_ARM, (), _LABELS)
    with pytest.raises(PFewFlightError, match="at least one demo"):
        pfew_supply_packet(FS_SKEW_ARM, (), _LABELS)


def test_pfew_supply_packet_prepends_the_demo_block_before_the_reused_closed_set_instruction():
    demos = (
        DemoCandidate("slurp:train:000000", "turn on the lights", "iot"),
        DemoCandidate("slurp:train:000001", "what is the weather", "weather"),
    )
    packet = pfew_supply_packet(FS_BAL_ARM, demos, _LABELS)
    closed_set_text = closed_set_phase1_supply_packet(_LABELS).prompt_block
    assert packet.prompt_block.endswith(closed_set_text)
    assert packet.prompt_block.index("turn on the lights") < packet.prompt_block.index(closed_set_text)
    assert packet.dose.n_items == 2
    assert len(packet.items) == 2


# ---------------------------------------------------------------------------
# validate_pfew_flight_summary -- fail-closed structural checks.
# ---------------------------------------------------------------------------

_UNMAPPED = ClosedSetMapping(predicted_raw=None, canonical_label=None, outcome="unmapped", fallback=True)


def _row(arm: str, sample_id: str, demos: tuple[dict, ...] = ()) -> PFewArmResult:
    return PFewArmResult(
        arm=arm, sample_id=sample_id, messages=(), response_text="{}", metrics={}, consumption=None,
        closed_set_mapping=_UNMAPPED, demos=demos,
    )


def _demo_json(label: str, index: int = 0) -> dict:
    return {"train_sample_id": f"slurp:train:{index:06d}", "utterance_text": f"u{index}", "scenario_label": label}


def _legal_summary(sample_ids: list[str], skew_label: str = "iot") -> PFewFlightSummary:
    results = []
    for sid in sample_ids:
        results.append(_row(FS_NONE_ARM, sid))
        results.append(_row(FS_BAL_ARM, sid, tuple(_demo_json(label, i) for i, label in enumerate(["a", "b", "c", "d"]))))
        results.append(_row(FS_SKEW_ARM, sid, tuple(_demo_json(skew_label, i) for i in range(4))))
    return PFewFlightSummary(results=tuple(results), canonical_labels=tuple(sorted({"a", "b", "c", "d", skew_label})), skew_label=skew_label, demo_binding_sha256="x" * 64)


def test_validate_pfew_flight_summary_accepts_a_legal_shape():
    validate_pfew_flight_summary(_legal_summary(["s1", "s2"]), expected_sample_ids=["s1", "s2"])  # does not raise


def test_validate_pfew_flight_summary_rejects_missing_sample_id():
    summary = _legal_summary(["s1"])
    with pytest.raises(PFewFlightError, match="does not match"):
        validate_pfew_flight_summary(summary, expected_sample_ids=["s1", "s2"])


def test_validate_pfew_flight_summary_rejects_duplicate_rows():
    results = list(_legal_summary(["s1"]).results) + [_row(FS_NONE_ARM, "s1")]
    summary = PFewFlightSummary(results=tuple(results), canonical_labels=("a",), skew_label="a", demo_binding_sha256="x" * 64)
    with pytest.raises(PFewFlightError, match="duplicate"):
        validate_pfew_flight_summary(summary, expected_sample_ids=["s1"])


def test_validate_pfew_flight_summary_rejects_fs_none_row_carrying_demos():
    results = [
        _row(FS_NONE_ARM, "s1", (_demo_json("a"),)),
        _row(FS_BAL_ARM, "s1", tuple(_demo_json(label, i) for i, label in enumerate(["a", "b", "c", "d"]))),
        _row(FS_SKEW_ARM, "s1", tuple(_demo_json("a", i) for i in range(4))),
    ]
    summary = PFewFlightSummary(results=tuple(results), canonical_labels=("a", "b", "c", "d"), skew_label="a", demo_binding_sha256="x" * 64)
    with pytest.raises(PFewFlightError, match="must carry zero demos"):
        validate_pfew_flight_summary(summary, expected_sample_ids=["s1"])


def test_validate_pfew_flight_summary_rejects_fs_bal_wrong_demo_count():
    results = [
        _row(FS_NONE_ARM, "s1"),
        _row(FS_BAL_ARM, "s1", (_demo_json("a"), _demo_json("b"))),  # only 2, need 4
        _row(FS_SKEW_ARM, "s1", tuple(_demo_json("a", i) for i in range(4))),
    ]
    summary = PFewFlightSummary(results=tuple(results), canonical_labels=("a", "b"), skew_label="a", demo_binding_sha256="x" * 64)
    with pytest.raises(PFewFlightError, match=f"expected {FS_BAL_K} demos"):
        validate_pfew_flight_summary(summary, expected_sample_ids=["s1"])


def test_validate_pfew_flight_summary_rejects_fs_bal_non_distinct_labels():
    results = [
        _row(FS_NONE_ARM, "s1"),
        _row(FS_BAL_ARM, "s1", tuple(_demo_json("a", i) for i in range(4))),  # all SAME label
        _row(FS_SKEW_ARM, "s1", tuple(_demo_json("a", i) for i in range(4))),
    ]
    summary = PFewFlightSummary(results=tuple(results), canonical_labels=("a",), skew_label="a", demo_binding_sha256="x" * 64)
    with pytest.raises(PFewFlightError, match="not all distinct"):
        validate_pfew_flight_summary(summary, expected_sample_ids=["s1"])


def test_validate_pfew_flight_summary_rejects_fs_skew_label_not_matching_summary_skew_label():
    results = [
        _row(FS_NONE_ARM, "s1"),
        _row(FS_BAL_ARM, "s1", tuple(_demo_json(label, i) for i, label in enumerate(["a", "b", "c", "d"]))),
        _row(FS_SKEW_ARM, "s1", tuple(_demo_json("b", i) for i in range(4))),  # summary.skew_label == "a"
    ]
    summary = PFewFlightSummary(results=tuple(results), canonical_labels=("a", "b", "c", "d"), skew_label="a", demo_binding_sha256="x" * 64)
    with pytest.raises(PFewFlightError, match="must all equal the skew label"):
        validate_pfew_flight_summary(summary, expected_sample_ids=["s1"])


def test_pfew_arms_constant_matches_registered_order():
    assert PFEW_ARMS == (FS_NONE_ARM, FS_BAL_ARM, FS_SKEW_ARM) == ("FS-NONE", "FS-BAL", "FS-SKEW")


# ---------------------------------------------------------------------------
# run_pfew_flight -- end to end over the real SlurpAdapter (MockCoreClient).
# ---------------------------------------------------------------------------


def _responder(text_by_media_relpath: dict[str, str]):
    def responder(messages):
        for part in messages[1]["content"]:
            if isinstance(part, dict) and part.get("type") == "input_audio":
                return text_by_media_relpath[part["media_relpath"]]
        raise AssertionError("no input_audio content part found")

    return responder


def _hand_binding(canonical_labels: tuple[str, ...], sample_ids: list[str]) -> DemoBinding:
    bal_labels = list(canonical_labels[:FS_BAL_K])
    skew_label = canonical_labels[0]
    per_sample = {}
    for index, sample_id in enumerate(sample_ids):
        bal_demos = tuple(
            DemoCandidate(f"slurp:train:{index:02d}{i:04d}", f"bal utterance {index}-{i}", label)
            for i, label in enumerate(bal_labels)
        )
        skew_demos = tuple(
            DemoCandidate(f"slurp:train:9{index:02d}{i:03d}", f"skew utterance {index}-{i}", skew_label)
            for i in range(FS_SKEW_K)
        )
        per_sample[sample_id] = SampleDemoSet(sample_id=sample_id, fs_bal_demos=bal_demos, fs_skew_demos=skew_demos)
    document = {"skew_label": skew_label, "canonical_labels": list(canonical_labels), "per_sample": {}}
    return DemoBinding(
        skew_label=skew_label, canonical_labels=canonical_labels, per_sample=per_sample,
        sha256=compute_demo_binding_sha256(document),
    )


def test_run_pfew_flight_produces_180_shaped_requests_in_registered_arm_major_order(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    responses = {s_iot.media_relpath: "{}", s_email.media_relpath: "{}"}
    client = MockCoreClient(responder=_responder(responses))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    canonical_labels = canonical_scenario_labels(rosters)
    binding = _hand_binding(canonical_labels, [s_iot.sample_id, s_email.sample_id])
    summary = run_pfew_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=rosters,
        demo_binding=binding, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
    )
    assert len(summary.results) == 6  # 2 samples x 3 arms
    arms_in_order = [(row.arm, row.sample_id) for row in summary.results]
    assert arms_in_order == [
        (FS_NONE_ARM, s_iot.sample_id), (FS_NONE_ARM, s_email.sample_id),
        (FS_BAL_ARM, s_iot.sample_id), (FS_BAL_ARM, s_email.sample_id),
        (FS_SKEW_ARM, s_iot.sample_id), (FS_SKEW_ARM, s_email.sample_id),
    ]
    assert summary.skew_label == binding.skew_label
    assert summary.demo_binding_sha256 == binding.sha256


def test_run_pfew_flight_every_row_carries_a_closed_set_mapping(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    responses = {s_iot.media_relpath: "{}", s_email.media_relpath: "{}"}
    client = MockCoreClient(responder=_responder(responses))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    canonical_labels = canonical_scenario_labels(rosters)
    binding = _hand_binding(canonical_labels, [s_iot.sample_id, s_email.sample_id])
    summary = run_pfew_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=rosters,
        demo_binding=binding, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
    )
    for row in summary.results:
        assert row.closed_set_mapping is not None
        assert row.closed_set_mapping.outcome == "unmapped"  # "{}" never parses a scenario


def test_run_pfew_flight_fs_bal_and_fs_skew_prompts_carry_the_demo_block(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    responses = {s_iot.media_relpath: "{}", s_email.media_relpath: "{}"}
    client = MockCoreClient(responder=_responder(responses))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    canonical_labels = canonical_scenario_labels(rosters)
    binding = _hand_binding(canonical_labels, [s_iot.sample_id, s_email.sample_id])
    summary = run_pfew_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=rosters,
        demo_binding=binding, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
    )
    none_row = next(r for r in summary.results if r.arm == FS_NONE_ARM and r.sample_id == s_iot.sample_id)
    bal_row = next(r for r in summary.results if r.arm == FS_BAL_ARM and r.sample_id == s_iot.sample_id)
    none_text_parts = [p["text"] for p in none_row.messages[1]["content"] if p.get("type") == "text"]
    bal_text_parts = [p["text"] for p in bal_row.messages[1]["content"] if p.get("type") == "text"]
    assert not none_text_parts or "utterance" not in none_text_parts[0]
    assert any("bal utterance" in text for text in bal_text_parts)
    assert len(bal_row.demos) == FS_BAL_K
    assert len(none_row.demos) == 0


def test_run_pfew_flight_rejects_a_wrong_split_identity_hash(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "{}"}))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    canonical_labels = canonical_scenario_labels(rosters)
    binding = _hand_binding(canonical_labels, [s_iot.sample_id])
    with pytest.raises(PFewFlightError, match="does not match"):
        run_pfew_flight(
            adapter=adapter, core_client=client, samples=[s_iot], rosters=rosters,
            demo_binding=binding, split_identity_hash="a" * 64,
        )


def test_run_pfew_flight_rejects_empty_samples(slurp_world):
    adapter, _, _ = _flight_world(slurp_world)
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    canonical_labels = canonical_scenario_labels(rosters)
    binding = _hand_binding(canonical_labels, [])
    with pytest.raises(PFewFlightError, match="at least one sample"):
        run_pfew_flight(
            adapter=adapter, core_client=MockCoreClient(), samples=(), rosters=rosters,
            demo_binding=binding, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        )


def test_run_pfew_flight_rejects_a_sample_missing_from_the_demo_binding(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "{}"}))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    canonical_labels = canonical_scenario_labels(rosters)
    binding = _hand_binding(canonical_labels, [])  # no per_sample entry for s_iot
    with pytest.raises(PFewFlightError, match="demo_binding carries no SampleDemoSet"):
        run_pfew_flight(
            adapter=adapter, core_client=client, samples=[s_iot], rosters=rosters,
            demo_binding=binding, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        )


def test_run_pfew_flight_rejects_a_stale_demo_binding_with_mismatched_canonical_labels(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder({s_iot.media_relpath: "{}"}))
    rosters = load_pslu_rosters(_ROSTER_TABLE_PATH)
    binding = _hand_binding(("not-a-real-label-set",), [s_iot.sample_id])
    with pytest.raises(PFewFlightError, match="stale demo binding"):
        run_pfew_flight(
            adapter=adapter, core_client=client, samples=[s_iot], rosters=rosters,
            demo_binding=binding, split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        )
