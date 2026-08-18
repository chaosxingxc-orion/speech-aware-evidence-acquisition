"""``rails.probes.pslu_flight``: the P-SLU six-arm, two-phase flight
orchestration (docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md).
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
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
    PSLU_ARMS,
    PsluFlightError,
    PsluRosters,
    PsluSampleManifest,
    _source_references_ontology_miner,
    assert_never_calls_ontology_miner,
    load_pslu_rosters,
    load_pslu_sample_manifest,
    pslu_supply_packet,
    render_roster_entries,
    render_type_vocabulary,
    run_pslu_flight,
    select_pslu_samples,
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


def _adapter(slurp_world) -> SlurpAdapter:
    lock = load_lock(slurp_world.lock_path)
    return SlurpAdapter(lock, slurp_world.data_root)


# ---------------------------------------------------------------------------
# render_roster_entries / render_type_vocabulary
# ---------------------------------------------------------------------------


def test_render_roster_entries_joins_type_value_pairs():
    text = render_roster_entries([("house_place", "kitchen"), ("device_type", "light")])
    assert text == "house_place=kitchen; device_type=light"


def test_render_type_vocabulary_comma_joins_bare_types():
    assert render_type_vocabulary(["a", "b", "c"]) == "a, b, c"


# ---------------------------------------------------------------------------
# load_pslu_rosters
# ---------------------------------------------------------------------------


def _write_roster_table(path: Path, **overrides) -> None:
    document = {
        "probe": "P-SLU",
        "legality_tier": "legal",
        "train_synthetic_refused": {"train_jsonl_overlap_with_devel": 0},
        "arms": {
            "A1_scenario_roster": {
                "rosters": {
                    "iot": [["house_place", "kitchen"], ["device_type", "light"]],
                    "email": [["email_folder", "inbox"]],
                }
            },
            "A2_global_type_vocabulary": {
                "types": ["house_place", "device_type", "email_folder", "time"]
            },
            "A3_full_ontology_dose_capped": {"roster": [["house_place", "kitchen"], ["time", "six"]]},
            "A4_deranged": {"mapping": {"iot": "email", "email": "iot"}},
        },
    }
    document.update(overrides)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_load_pslu_rosters_happy_path(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(path)
    rosters = load_pslu_rosters(path)
    assert rosters.scenario_rosters["iot"] == (("house_place", "kitchen"), ("device_type", "light"))
    assert rosters.global_types == ("house_place", "device_type", "email_folder", "time")
    assert rosters.full_roster == (("house_place", "kitchen"), ("time", "six"))
    assert rosters.derangement == {"iot": "email", "email": "iot"}


def test_load_pslu_rosters_rejects_wrong_probe(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(path, probe="P-A2T")
    with pytest.raises(PsluFlightError, match="probe must be"):
        load_pslu_rosters(path)


def test_load_pslu_rosters_rejects_non_legal_tier(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(path, legality_tier="ceiling")
    with pytest.raises(PsluFlightError, match="legality_tier"):
        load_pslu_rosters(path)


def test_load_pslu_rosters_rejects_nonzero_devel_overlap(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(path, train_synthetic_refused={"train_jsonl_overlap_with_devel": 5})
    with pytest.raises(PsluFlightError, match="overlap_with_devel"):
        load_pslu_rosters(path)


def test_load_pslu_rosters_against_the_real_binding_table():
    """The mission's own registered artifact -- proves this loader actually
    parses it, not merely a hand-shrunk test fixture."""

    path = (
        Path(__file__).resolve().parents[2]
        / "configs" / "probes" / "g0-binding" / "pslu-rosters-train-only.json"
    )
    rosters = load_pslu_rosters(path)
    assert "iot" in rosters.scenario_rosters
    assert len(rosters.global_types) == 55
    assert len(rosters.full_roster) == 100
    assert rosters.derangement["audio"] == "cooking"


# ---------------------------------------------------------------------------
# load_pslu_sample_manifest / select_pslu_samples
# ---------------------------------------------------------------------------


def _write_sample_manifest(path: Path, **overrides) -> None:
    document = {
        "probe": "P-SLU",
        "seed": 20260807,
        "split_identity_hash": "a" * 64,
        "items": [
            {"sample_id": "slurp:devel:000102:audio-102"},
            {"sample_id": "slurp:devel:000101:audio-101"},
        ],
    }
    document.update(overrides)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_load_pslu_sample_manifest_happy_path(tmp_path):
    path = tmp_path / "manifest.json"
    _write_sample_manifest(path)
    manifest = load_pslu_sample_manifest(path)
    assert manifest.sample_ids == ("slurp:devel:000102:audio-102", "slurp:devel:000101:audio-101")
    assert manifest.seed == 20260807
    assert manifest.split_identity_hash == "a" * 64


def test_load_pslu_sample_manifest_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "manifest.json"
    _write_sample_manifest(
        path,
        items=[{"sample_id": "x"}, {"sample_id": "x"}],
    )
    with pytest.raises(PsluFlightError, match="duplicate sample_id"):
        load_pslu_sample_manifest(path)


def test_load_pslu_sample_manifest_against_the_real_binding_table():
    path = (
        Path(__file__).resolve().parents[2]
        / "configs" / "probes" / "g0-binding" / "pslu-sample-devel-n60.json"
    )
    manifest = load_pslu_sample_manifest(path)
    assert len(manifest.sample_ids) == 60
    assert manifest.seed == 20260807
    assert manifest.split_identity_hash == (
        "fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5"
    )


def test_select_pslu_samples_filters_and_reorders(slurp_world):
    adapter = _adapter(slurp_world)
    all_devel = adapter.load_split("devel")  # sorted by sample_id: 101, 101-headset, 102
    manifest = PsluSampleManifest(
        sample_ids=("slurp:devel:000102:audio-102", "slurp:devel:000101:audio-101"),
        split_identity_hash="a" * 64,
        seed=1,
    )
    selected = select_pslu_samples(all_devel, manifest)
    assert [s.sample_id for s in selected] == list(manifest.sample_ids)


def test_select_pslu_samples_raises_on_a_missing_id(slurp_world):
    adapter = _adapter(slurp_world)
    all_devel = adapter.load_split("devel")
    manifest = PsluSampleManifest(sample_ids=("bogus-id",), split_identity_hash="a" * 64, seed=1)
    with pytest.raises(PsluFlightError, match="not present in the loaded split"):
        select_pslu_samples(all_devel, manifest)


# ---------------------------------------------------------------------------
# pslu_supply_packet -- per-arm roster selection
# ---------------------------------------------------------------------------


def test_a0_has_no_supply():
    assert pslu_supply_packet("A0", scenario=None, rosters=_ROSTERS) is None


def test_a1_uses_the_named_scenarios_roster():
    packet = pslu_supply_packet("A1", scenario="iot", rosters=_ROSTERS)
    assert packet.prompt_block == "house_place=kitchen; device_type=light"


def test_a1_without_a_scenario_raises():
    with pytest.raises(PsluFlightError, match="A1 requires"):
        pslu_supply_packet("A1", scenario=None, rosters=_ROSTERS)


def test_a1_unknown_scenario_raises():
    with pytest.raises(PsluFlightError, match="no A1 roster"):
        pslu_supply_packet("A1", scenario="bogus", rosters=_ROSTERS)


def test_a1p_uses_the_predicted_scenarios_roster():
    packet = pslu_supply_packet("A1p", scenario="email", rosters=_ROSTERS)
    assert packet.prompt_block == "email_folder=inbox"


def test_a1p_falls_back_to_a2_when_scenario_is_none():
    packet = pslu_supply_packet("A1p", scenario=None, rosters=_ROSTERS)
    assert packet.prompt_block == render_type_vocabulary(_ROSTERS.global_types)
    assert packet.assembly_template_id == "pslu-A1p-fallback-A2-roster-v1"


def test_a1p_falls_back_to_a2_when_scenario_is_unknown():
    packet = pslu_supply_packet("A1p", scenario="not-a-real-scenario", rosters=_ROSTERS)
    assert packet.prompt_block == render_type_vocabulary(_ROSTERS.global_types)


def test_a2_is_the_global_type_vocabulary():
    packet = pslu_supply_packet("A2", scenario="iot", rosters=_ROSTERS)
    assert packet.prompt_block == "house_place, device_type, email_folder, time"


def test_a3_is_the_full_dose_capped_roster():
    packet = pslu_supply_packet("A3", scenario=None, rosters=_ROSTERS)
    assert packet.prompt_block == "house_place=kitchen; time=six"


def test_a4_uses_the_deranged_partners_roster():
    packet = pslu_supply_packet("A4", scenario="iot", rosters=_ROSTERS)
    assert packet.prompt_block == "email_folder=inbox"  # iot's deranged partner is email


def test_a4_without_a_scenario_raises():
    with pytest.raises(PsluFlightError, match="A4 requires"):
        pslu_supply_packet("A4", scenario=None, rosters=_ROSTERS)


def test_unknown_arm_raises():
    with pytest.raises(PsluFlightError, match="unknown P-SLU arm"):
        pslu_supply_packet("A99", scenario="iot", rosters=_ROSTERS)


# ---------------------------------------------------------------------------
# the ontology-miner call guard
# ---------------------------------------------------------------------------


def test_the_real_module_source_never_references_the_ontology_miner():
    assert_never_calls_ontology_miner()  # no args -- self-checks the real file


def test_guard_catches_a_live_import():
    source = "from ...data.slurp import load_slurp_ontology\n"
    assert _source_references_ontology_miner(source) is True
    with pytest.raises(PsluFlightError, match="load_slurp_ontology"):
        assert_never_calls_ontology_miner(source)


def test_guard_catches_a_bare_call():
    source = "def f(lock, root):\n    return load_slurp_ontology(lock, root)\n"
    assert _source_references_ontology_miner(source) is True


def test_guard_catches_an_attribute_access():
    source = "import speech_aware_evidence_acquisition.data.slurp as slurp\nslurp.load_slurp_ontology(1, 2)\n"
    assert _source_references_ontology_miner(source) is True


def test_guard_does_not_trip_on_a_docstring_mention():
    source = '"""This module never calls load_slurp_ontology -- see the docstring."""\nx = 1\n'
    assert _source_references_ontology_miner(source) is False
    assert_never_calls_ontology_miner(source)  # does not raise


# ---------------------------------------------------------------------------
# run_pslu_flight -- end to end
# ---------------------------------------------------------------------------


def _flight_world(slurp_world):
    adapter = _adapter(slurp_world)
    devel = adapter.load_split("devel")
    s_iot = devel[0]  # slurp:devel:000101:audio-101, gold scenario "iot"
    s_email = devel[2]  # slurp:devel:000102:audio-102, gold scenario "email"
    return adapter, s_iot, s_email


def _responder(s_iot):
    def responder(messages):
        content = messages[1]["content"]
        is_phase1 = len(content) == 1  # A0 sends audio only, every other arm prepends text
        if is_phase1:
            # Deliberately WRONG for s_iot (gold "iot") -- proves A1' reads
            # the phase-1 prediction, never the gold scenario.
            return json.dumps({"scenario": "email", "action": "query", "entities": []})
        return json.dumps({"scenario": "iot", "action": "hue_lighton", "entities": []})

    return responder


def test_run_pslu_flight_produces_a0_then_five_phase2_arms_per_sample(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))

    summary = run_pslu_flight(adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS)

    assert [r.arm for r in summary.results] == [
        "A0", "A0",
        "A1", "A1p", "A2", "A3", "A4",
        "A1", "A1p", "A2", "A3", "A4",
    ]
    assert len(client.calls) == 12
    assert set(PSLU_ARMS) == {"A0", "A1", "A1p", "A2", "A3", "A4"}


def test_run_pslu_flight_a1_prime_reads_the_phase1_prediction_not_gold(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))

    summary = run_pslu_flight(adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS)

    assert summary.predicted_scenario_by_sample_id[s_iot.sample_id] == "email"  # wrong, as scripted
    assert summary.predicted_scenario_by_sample_id[s_email.sample_id] == "email"  # right

    a1_iot = next(r for r in summary.results if r.arm == "A1" and r.sample_id == s_iot.sample_id)
    a1p_iot = next(
        r for r in summary.results if r.arm == "A1p" and r.sample_id == s_iot.sample_id and not r.silence_swapped
    )
    a1_text = a1_iot.messages[1]["content"][0]["text"]
    a1p_text = a1p_iot.messages[1]["content"][0]["text"]
    assert a1_text == "house_place=kitchen; device_type=light"  # A1: gold "iot" roster
    assert a1p_text == "email_folder=inbox"  # A1': predicted "email" roster -- differs from A1
    assert a1_text != a1p_text


def test_run_pslu_flight_phase1_row_carries_whether_it_parsed(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))
    summary = run_pslu_flight(adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS)
    a0_rows = [r for r in summary.results if r.arm == "A0"]
    assert all(row.phase1_scenario_parsed is True for row in a0_rows)
    phase2_rows = [r for r in summary.results if r.arm != "A0"]
    assert all(row.phase1_scenario_parsed is None for row in phase2_rows)


def test_run_pslu_flight_silence_swap_adds_one_extra_a1p_row(slurp_world):
    """``silence_swap_media_relpaths`` carries whatever media_relpath a REAL
    SliceRegistry actually produced for s_iot's raw, colon-bearing SLURP id
    (``slurp:devel:000101:audio-101``) -- not a hand-typed path the real
    registry could never build. This is the regression test for
    docs/checks/speech-aware-evidence-acquisition/2026-08-17-pslu-flight/
    2026-08-18-attempt2-flight-execution.md: the original version of this
    test hardcoded exactly the string the pre-fix registry refused to
    produce, so it hid the defect behind a green suite."""

    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))
    assert ":" in s_iot.sample_id  # the defect only bites a colon-bearing raw id
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
    assert ":" not in silence_relpath  # raw id sanitized into the filesystem token

    summary = run_pslu_flight(
        adapter=adapter,
        core_client=client,
        samples=[s_iot, s_email],
        rosters=_ROSTERS,
        silence_swap_media_relpaths={s_iot.sample_id: silence_relpath},
    )

    assert len(summary.results) == 13  # 12 base + 1 silence-swap
    swapped = [r for r in summary.results if r.silence_swapped]
    assert len(swapped) == 1
    assert swapped[0].arm == "A1p"
    assert swapped[0].sample_id == s_iot.sample_id
    assert swapped[0].messages[1]["content"][-1] == {
        "type": "input_audio", "media_relpath": silence_relpath,
    }
    # The roster text is UNCHANGED by the swap -- only the audio changes.
    normal_a1p = next(
        r for r in summary.results if r.arm == "A1p" and r.sample_id == s_iot.sample_id and not r.silence_swapped
    )
    assert swapped[0].messages[1]["content"][0] == normal_a1p.messages[1]["content"][0]


def test_run_pslu_flight_rejects_empty_samples(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    with pytest.raises(PsluFlightError, match="at least one sample"):
        run_pslu_flight(adapter=adapter, core_client=MockCoreClient(), samples=(), rosters=_ROSTERS)


def test_run_pslu_flight_rejects_unknown_silence_swap_sample_ids(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))
    with pytest.raises(PsluFlightError, match="outside this flight"):
        run_pslu_flight(
            adapter=adapter,
            core_client=client,
            samples=[s_iot],
            rosters=_ROSTERS,
            silence_swap_media_relpaths={"bogus-sample-id": "x.wav"},
        )
