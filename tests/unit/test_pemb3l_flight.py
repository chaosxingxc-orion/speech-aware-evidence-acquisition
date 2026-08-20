"""``rails.probes.pemb3l_flight``: the P-EMB-3L three-arm sweep flight
delta (docs/readiness/2026-08-20-pemb3l-preregistration-REGISTERED.md).
Engineering-only, ZERO live model contact -- every test here drives
``rails.embedding_client.MockEmbeddingClient``.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.embedding_client import (
    EMBEDDING_DIM,
    MockEmbeddingClient,
)
from speech_aware_evidence_acquisition.rails.probes.pemb3l_flight import (
    ARM_AUDIO_N,
    ARM_IDS,
    ARM_L1,
    ARM_L1_ID,
    ARM_L2,
    ARM_L2_ID,
    ARM_L3,
    ARM_L3_ID,
    ARM_LABEL_N,
    ARM_TOTAL_N,
    ARMS,
    ARMS_BY_ID,
    AUDIO_INSTRUCT_PREFIX,
    BINDING_CONFIG_SHA256,
    CITED_MEAN_BARE_ACCURACY,
    EXPECTED_TOTAL_CONTACTS,
    POOLING_LAST,
    POOLING_MEAN,
    PROBE_ID,
    TEXT_INSTRUCT_PREFIX,
    Pemb3lArm,
    Pemb3lFlightError,
    arm_run_id,
    assert_binding_config_sha256,
    binding_config_sha256,
    load_pemb3l_arm_manifest,
    run_pemb3l_arm_flight,
    run_pemb3l_sweep_flight,
    write_pemb3l_arm_manifest,
    write_pemb3l_sweep_manifests,
)
from speech_aware_evidence_acquisition.rails.probes.pemb_flight import (
    EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
    LoadedEmbeddingManifest,
    PembFlightError,
)


def _slurp_adapter(world) -> SlurpAdapter:
    return SlurpAdapter(load_lock(world.lock_path), world.data_root)


# ---------------------------------------------------------------------------
# Registered constants -- 78/78/78, 234 total.
# ---------------------------------------------------------------------------


def test_registered_totals():
    assert PROBE_ID == "SAEA-PROBE-pemb3l-234"
    assert ARM_AUDIO_N == 60
    assert ARM_LABEL_N == 18
    assert ARM_TOTAL_N == 78
    assert EXPECTED_TOTAL_CONTACTS == 234
    assert len(ARMS) == 3
    assert ARM_IDS == (ARM_L1_ID, ARM_L2_ID, ARM_L3_ID)


def test_pemb3l_flight_error_is_a_pemb_flight_error_subclass():
    # analysis.pemb_read.main's own "except PembFlightError" clause must
    # catch this without modification.
    assert issubclass(Pemb3lFlightError, PembFlightError)


# ---------------------------------------------------------------------------
# Pooling-mode tagging.
# ---------------------------------------------------------------------------


def test_arm_pooling_modes_match_the_registration():
    assert ARM_L1.pooling_mode == POOLING_LAST
    assert ARM_L2.pooling_mode == POOLING_LAST
    assert ARM_L3.pooling_mode == POOLING_MEAN


def test_arms_by_id_maps_every_registered_arm_id():
    assert set(ARMS_BY_ID.keys()) == set(ARM_IDS)
    assert ARMS_BY_ID[ARM_L1_ID] is ARM_L1
    assert ARMS_BY_ID[ARM_L2_ID] is ARM_L2
    assert ARMS_BY_ID[ARM_L3_ID] is ARM_L3


def test_last_pooling_arms_share_one_session_l3_needs_a_separate_one():
    last_pooling_arms = [arm.arm_id for arm in ARMS if arm.pooling_mode == POOLING_LAST]
    mean_pooling_arms = [arm.arm_id for arm in ARMS if arm.pooling_mode == POOLING_MEAN]
    assert last_pooling_arms == [ARM_L1_ID, ARM_L2_ID]
    assert mean_pooling_arms == [ARM_L3_ID]


# ---------------------------------------------------------------------------
# Instruct-prefix strings -- EXACT per the registration.
# ---------------------------------------------------------------------------


def test_instruct_prefix_strings_are_exact():
    assert AUDIO_INSTRUCT_PREFIX == "Represent this utterance for intent retrieval: "
    assert TEXT_INSTRUCT_PREFIX == "Represent this intent label for retrieval: "


def test_l1_carries_no_prefix_l2_and_l3_carry_the_same_instruct_prefixes():
    assert ARM_L1.audio_prefix == ""
    assert ARM_L1.text_prefix == ""
    assert ARM_L2.audio_prefix == AUDIO_INSTRUCT_PREFIX
    assert ARM_L2.text_prefix == TEXT_INSTRUCT_PREFIX
    assert ARM_L3.audio_prefix == AUDIO_INSTRUCT_PREFIX
    assert ARM_L3.text_prefix == TEXT_INSTRUCT_PREFIX


# ---------------------------------------------------------------------------
# Binding config sha256 -- pinning + drift refusal.
# ---------------------------------------------------------------------------


def test_binding_config_sha256_matches_the_pinned_constant():
    assert binding_config_sha256() == BINDING_CONFIG_SHA256


def test_assert_binding_config_sha256_accepts_the_live_table():
    assert_binding_config_sha256()  # does not raise


def test_assert_binding_config_sha256_refuses_a_drifted_prefix(monkeypatch):
    import speech_aware_evidence_acquisition.rails.probes.pemb3l_flight as pemb3l_flight

    drifted_l2 = Pemb3lArm(
        arm_id=ARM_L2_ID,
        pooling_mode=POOLING_LAST,
        audio_prefix="Represent this utterance for intent retrieval (DRIFTED): ",
        text_prefix=TEXT_INSTRUCT_PREFIX,
    )
    monkeypatch.setattr(pemb3l_flight, "ARMS", (ARM_L1, drifted_l2, ARM_L3))
    with pytest.raises(Pemb3lFlightError, match="sha256"):
        pemb3l_flight.assert_binding_config_sha256()


def test_assert_binding_config_sha256_refuses_a_drifted_pooling_mode(monkeypatch):
    import speech_aware_evidence_acquisition.rails.probes.pemb3l_flight as pemb3l_flight

    drifted_l3 = Pemb3lArm(
        arm_id=ARM_L3_ID, pooling_mode=POOLING_LAST, audio_prefix=AUDIO_INSTRUCT_PREFIX, text_prefix=TEXT_INSTRUCT_PREFIX
    )
    monkeypatch.setattr(pemb3l_flight, "ARMS", (ARM_L1, ARM_L2, drifted_l3))
    with pytest.raises(Pemb3lFlightError, match="sha256"):
        pemb3l_flight.assert_binding_config_sha256()


def test_module_self_check_passed_at_import_time_on_the_real_table():
    # If the module imported successfully above, its own module-bottom
    # assert_binding_config_sha256() call already passed -- this test just
    # documents that fact explicitly rather than relying on import success
    # alone to prove it.
    assert binding_config_sha256() == BINDING_CONFIG_SHA256


# ---------------------------------------------------------------------------
# arm_run_id.
# ---------------------------------------------------------------------------


def test_arm_run_id_places_each_arm_under_the_probe_id():
    assert arm_run_id(ARM_L1_ID) == "SAEA-PROBE-pemb3l-234/l1-last-bare"
    assert arm_run_id(ARM_L2_ID) == "SAEA-PROBE-pemb3l-234/l2-last-instruct"
    assert arm_run_id(ARM_L3_ID) == "SAEA-PROBE-pemb3l-234/l3-mean-instruct"


def test_arm_run_id_refuses_an_unknown_arm_id():
    with pytest.raises(Pemb3lFlightError, match="unknown arm_id"):
        arm_run_id("not-a-real-arm")


# ---------------------------------------------------------------------------
# CITED mean-bare constant.
# ---------------------------------------------------------------------------


def test_cited_mean_bare_accuracy_matches_the_consumed_pemb1_read():
    # docs/readiness/2026-08-19-pemb1-verdict.md section 1:
    # "argmax-cosine accuracy vs gold ... 3 / 60 = 0.0500".
    assert CITED_MEAN_BARE_ACCURACY == pytest.approx(3 / 60)
    assert CITED_MEAN_BARE_ACCURACY == 0.0500


# ---------------------------------------------------------------------------
# run_pemb3l_arm_flight.
# ---------------------------------------------------------------------------


def test_run_pemb3l_arm_flight_happy_path_l1(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")  # 3 synthetic samples
    labels = ("email", "iot")
    client = MockEmbeddingClient()

    summary = run_pemb3l_arm_flight(
        client=client,
        arm=ARM_L1,
        samples=samples,
        canonical_labels=labels,
        split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
        data_root=slurp_world.data_root,
        expected_audio_n=3,
        expected_label_n=2,
    )

    assert summary.run_id == arm_run_id(ARM_L1_ID)
    assert len(summary.audio_vectors) == 3
    assert len(summary.text_vectors) == 2
    assert client.marker_verified is True
    # L1 is bare -- every prefix recorded by the mock must be the empty string.
    assert all(prefix == "" for prefix in client.prefixes)


def test_run_pemb3l_arm_flight_applies_the_instruct_prefixes_for_l2(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    labels = ("email", "iot")
    client = MockEmbeddingClient()

    run_pemb3l_arm_flight(
        client=client,
        arm=ARM_L2,
        samples=samples,
        canonical_labels=labels,
        split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
        data_root=slurp_world.data_root,
        expected_audio_n=3,
        expected_label_n=2,
    )

    audio_prefixes = {prefix for (kind, _cid), prefix in zip(client.calls, client.prefixes) if kind == "audio"}
    text_prefixes = {prefix for (kind, _cid), prefix in zip(client.calls, client.prefixes) if kind == "text"}
    assert audio_prefixes == {AUDIO_INSTRUCT_PREFIX}
    assert text_prefixes == {TEXT_INSTRUCT_PREFIX}


def test_run_pemb3l_arm_flight_rejects_an_arm_not_in_the_pinned_table(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    rogue_arm = Pemb3lArm(arm_id=ARM_L1_ID, pooling_mode=POOLING_MEAN, audio_prefix="", text_prefix="")
    with pytest.raises(Pemb3lFlightError, match="not one of the pinned ARMS"):
        run_pemb3l_arm_flight(
            client=client,
            arm=rogue_arm,
            samples=samples,
            canonical_labels=("email", "iot"),
            split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_audio_n=3,
            expected_label_n=2,
        )


def test_run_pemb3l_arm_flight_rejects_wrong_split_identity_hash(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    # assert_run_a_split_identity_hash is rails.probes.pemb_flight's own,
    # reused verbatim (module docstring) -- it raises the PARENT
    # PembFlightError, never the Pemb3lFlightError subclass.
    with pytest.raises(PembFlightError, match="split_identity_hash"):
        run_pemb3l_arm_flight(
            client=client,
            arm=ARM_L1,
            samples=samples,
            canonical_labels=("email", "iot"),
            split_identity_hash="not-the-pin",
            data_root=slurp_world.data_root,
            expected_audio_n=3,
            expected_label_n=2,
        )
    assert client.calls == []


def test_run_pemb3l_arm_flight_rejects_wrong_audio_count(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(Pemb3lFlightError, match="60"):
        run_pemb3l_arm_flight(
            client=client,
            arm=ARM_L1,
            samples=samples,
            canonical_labels=("email", "iot"),
            split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_label_n=2,
        )


def test_run_pemb3l_arm_flight_rejects_duplicate_labels(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(Pemb3lFlightError, match="duplicate canonical label"):
        run_pemb3l_arm_flight(
            client=client,
            arm=ARM_L1,
            samples=samples,
            canonical_labels=("iot", "iot"),
            split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_audio_n=3,
            expected_label_n=2,
        )


def test_run_pemb3l_arm_flight_rejects_a_padded_label(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(Pemb3lFlightError, match="bare"):
        run_pemb3l_arm_flight(
            client=client,
            arm=ARM_L1,
            samples=samples,
            canonical_labels=(" iot", "email"),
            split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_audio_n=3,
            expected_label_n=2,
        )


def test_run_pemb3l_arm_flight_rejects_duplicate_sample_ids(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(Pemb3lFlightError, match="duplicate sample_id"):
        run_pemb3l_arm_flight(
            client=client,
            arm=ARM_L1,
            samples=[samples[0], samples[0]],
            canonical_labels=("email", "iot"),
            split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_audio_n=2,
            expected_label_n=2,
        )


# ---------------------------------------------------------------------------
# run_pemb3l_sweep_flight.
# ---------------------------------------------------------------------------


def test_run_pemb3l_sweep_flight_happy_path_produces_78_per_arm(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    labels = ("email", "iot")
    last_client = MockEmbeddingClient()
    mean_client = MockEmbeddingClient()
    clients = {ARM_L1_ID: last_client, ARM_L2_ID: last_client, ARM_L3_ID: mean_client}

    summaries = run_pemb3l_sweep_flight(
        clients=clients,
        samples=samples,
        canonical_labels=labels,
        split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
        data_root=slurp_world.data_root,
        expected_audio_n=3,
        expected_label_n=2,
    )

    assert len(summaries) == 3
    assert [s.run_id for s in summaries] == [arm_run_id(arm_id) for arm_id in ARM_IDS]
    for summary in summaries:
        assert len(summary.audio_vectors) == 3
        assert len(summary.text_vectors) == 2
    # L1 + L2 share the last-pooling client; L3 uses the mean-pooling client.
    assert len(last_client.calls) == 2 * (3 + 2)
    assert len(mean_client.calls) == 3 + 2


def test_run_pemb3l_sweep_flight_refuses_a_missing_client(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(Pemb3lFlightError, match="missing client"):
        run_pemb3l_sweep_flight(
            clients={ARM_L1_ID: client, ARM_L2_ID: client},  # L3 missing
            samples=samples,
            canonical_labels=("email", "iot"),
            split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_audio_n=3,
            expected_label_n=2,
        )


# ---------------------------------------------------------------------------
# Manifest persistence -- write/load reuses rails.probes.pemb_flight's own
# writer/loader verbatim, under the arm-scoped run_id.
# ---------------------------------------------------------------------------


def test_write_and_load_pemb3l_arm_manifest_round_trip(tmp_path, slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    summary = run_pemb3l_arm_flight(
        client=client,
        arm=ARM_L2,
        samples=samples,
        canonical_labels=("email", "iot"),
        split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
        data_root=slurp_world.data_root,
        expected_audio_n=3,
        expected_label_n=2,
    )

    manifest_path = write_pemb3l_arm_manifest(tmp_path, summary)
    assert manifest_path == tmp_path / "derived" / "embeddings" / arm_run_id(ARM_L2_ID) / "manifest.json"
    assert manifest_path.is_file()

    loaded = load_pemb3l_arm_manifest(tmp_path, ARM_L2_ID)
    assert isinstance(loaded, LoadedEmbeddingManifest)
    assert loaded.run_id == arm_run_id(ARM_L2_ID)
    assert set(loaded.audio.keys()) == {v.contact_id for v in summary.audio_vectors}
    assert set(loaded.text.keys()) == {"email", "iot"}
    for vector in summary.audio_vectors:
        assert loaded.audio[vector.contact_id].shape == (EMBEDDING_DIM,)


def test_write_pemb3l_sweep_manifests_places_each_arm_under_its_own_subdir(tmp_path, slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    labels = ("email", "iot")
    last_client = MockEmbeddingClient()
    mean_client = MockEmbeddingClient()
    clients = {ARM_L1_ID: last_client, ARM_L2_ID: last_client, ARM_L3_ID: mean_client}

    summaries = run_pemb3l_sweep_flight(
        clients=clients,
        samples=samples,
        canonical_labels=labels,
        split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
        data_root=slurp_world.data_root,
        expected_audio_n=3,
        expected_label_n=2,
    )
    manifest_paths = write_pemb3l_sweep_manifests(tmp_path, summaries)
    assert len(manifest_paths) == 3
    for arm_id, path in zip(ARM_IDS, manifest_paths):
        assert path == tmp_path / "derived" / "embeddings" / arm_run_id(arm_id) / "manifest.json"
        assert path.is_file()
        loaded = load_pemb3l_arm_manifest(tmp_path, arm_id)
        assert loaded.run_id == arm_run_id(arm_id)
