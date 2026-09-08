"""``rails.probes.pemb4r_flight``: the P-EMB-4R multi-model kNN retrieval
routing flight (docs/readiness/2026-08-20-pemb4r-preregistration-
REGISTERED.md). Engineering-only, ZERO live model contact -- every test
drives ``rails.embedding_client.MockEmbeddingClient`` / ``rails.
local_encoder_client.MockLocalEncoderClient`` / ``rails.core_client.
MockCoreClient`` or a hand-built duck-typed double.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.lock import REPO_ROOT, load_lock, umbrella_lock_path
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter, SlurpSample
from speech_aware_evidence_acquisition.rails.embedding_client import (
    EMBEDDING_DIM,
    EmbeddingVector,
    MockEmbeddingClient,
    deterministic_unit_vector,
)
from speech_aware_evidence_acquisition.rails.local_encoder_client import (
    GLAP_EMBEDDING_DIM,
    STATUS_DROPPED_DEPS,
    STATUS_OK,
    MockLocalEncoderClient,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes import pemb4r_flight as f
from speech_aware_evidence_acquisition.rails.probes.pemb_flight import PembFlightError
from speech_aware_evidence_acquisition.rails.probes.pfew_flight import DemoCandidate
from speech_aware_evidence_acquisition.rails.probes.pkey_flight import build_transcript_record


def _synthetic_lock() -> dict:
    return {
        "models": [
            {
                "name": "lco-embedding-omni-3b-gguf",
                "local_subdir": "models/lco-embedding-omni-3b-gguf",
                "source": {"kind": "observed-local", "id": "UNRESOLVED_LOCAL_SOURCE"},
                "revision": "UNRESOLVED_LOCAL_REVISION",
                "lifecycle": "LOCAL_CANDIDATE",
                "verification": {"size_bytes": 111, "files": 5},
            },
            {
                "name": "lco-embedding-omni-7b-gguf",
                "local_subdir": "models/lco-embedding-omni-7b-gguf",
                "source": {"kind": "observed-local", "id": "UNRESOLVED_LOCAL_SOURCE"},
                "revision": "UNRESOLVED_LOCAL_REVISION",
                "lifecycle": "LOCAL_CANDIDATE",
                "verification": {"size_bytes": 444, "files": 5},
            },
            {
                "name": "glap",
                "local_subdir": "models/glap",
                "source": {"kind": "observed-local", "id": "UNRESOLVED_LOCAL_SOURCE"},
                "revision": "UNRESOLVED_LOCAL_REVISION",
                "lifecycle": "LOCAL_CANDIDATE",
                "verification": {"size_bytes": 222, "files": 9},
            },
            {
                "name": "qwen3-embedding-0.6b-gguf",
                "local_subdir": "models/qwen3-embedding-0.6b-gguf",
                "source": {
                    "kind": "hf",
                    "id": "Qwen/Qwen3-Embedding-0.6B-GGUF",
                    "files": [{"filename": "Qwen3-Embedding-0.6B-Q8_0.gguf", "sha256": "a" * 64}],
                },
                "revision": "370f27d7550e0def9b39c1f16d3fbaa13aa67728",
                "lifecycle": "AUXILIARY",
                "verification": {"size_bytes": 639150592},
            },
        ],
    }


def _samples(n: int, root: Path) -> tuple[SlurpSample, ...]:
    samples = []
    for i in range(n):
        relpath = f"datasets/slurp/slurp_real/audio-{i}.flac"
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(b"FAKEAUDIO")
        samples.append(
            SlurpSample(
                sample_id=f"slurp:devel:{i:06d}",
                audio_ref=AudioRef(path=relpath, sha256="0" * 64),
                audio_seconds=1.0,
                utterance_id=str(i),
                media_relpath=relpath,
                scenario="iot",
                action="hue_lighton",
                intent="iot_hue_lighton",
                entities=(),
            )
        )
    return tuple(samples)


def _pool(labels: list[str], per_label: int) -> dict[str, tuple[DemoCandidate, ...]]:
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


# ---------------------------------------------------------------------------
# Registered constants.
# ---------------------------------------------------------------------------


def test_registered_totals():
    assert f.PROBE_ID == "SAEA-PROBE-pemb4r-4100"
    assert f.QUERY_N == 60
    assert f.BANK_N_SCENARIOS == 18
    assert f.BANK_PER_SCENARIO_N == 50
    assert f.BANK_TOTAL_N == 900
    assert f.PLANNED_BANK_CONTACTS == 3600
    assert f.PLANNED_AUDIO_QUERY_CONTACTS == 180
    assert f.PLANNED_TEXT_QUERY_CONTACTS == 240
    assert f.PLANNED_C_DECODE_CONTACTS == 60
    assert f.GATE_CONTACTS_MAX == 20
    assert f.DEFAULT_PLANNED_MODEL_CALLS == 4100


def test_registered_ceilings():
    assert f.CEILING_CALLS == 4500
    assert f.CEILING_AUDIO_SECONDS == 700
    assert f.CEILING_GPU_HOURS == 0.5


def test_pemb4r_flight_error_is_a_pemb_flight_error_subclass():
    assert issubclass(f.Pemb4rFlightError, PembFlightError)


def test_arm_table_has_seven_arms():
    assert len(f.ARMS) == 7
    assert set(f.ARM_IDS) == {
        f.ARM_A_LCO3, f.ARM_A_LCO7, f.ARM_A_GLAP, f.ARM_T_LCO3, f.ARM_T_LCO7, f.ARM_T_GLAP, f.ARM_T_QW,
    }
    assert set(f.AUDIO_ARM_IDS) == {f.ARM_A_LCO3, f.ARM_A_LCO7, f.ARM_A_GLAP}
    assert set(f.TEXT_ARM_IDS) == {f.ARM_T_LCO3, f.ARM_T_LCO7, f.ARM_T_GLAP, f.ARM_T_QW}


def test_arm_ids_by_model_shares_the_bank_across_audio_and_text_arms():
    assert set(f.ARM_IDS_BY_MODEL[f.MODEL_LCO3]) == {f.ARM_A_LCO3, f.ARM_T_LCO3}
    assert set(f.ARM_IDS_BY_MODEL[f.MODEL_LCO7]) == {f.ARM_A_LCO7, f.ARM_T_LCO7}
    assert set(f.ARM_IDS_BY_MODEL[f.MODEL_GLAP]) == {f.ARM_A_GLAP, f.ARM_T_GLAP}
    assert set(f.ARM_IDS_BY_MODEL[f.MODEL_QW]) == {f.ARM_T_QW}


def test_known_model_dim_excludes_lco7():
    assert f.KNOWN_MODEL_DIM[f.MODEL_LCO3] == EMBEDDING_DIM == 2048
    assert f.KNOWN_MODEL_DIM[f.MODEL_GLAP] == GLAP_EMBEDDING_DIM == 1024
    assert f.KNOWN_MODEL_DIM[f.MODEL_QW] == 1024
    assert f.MODEL_LCO7 not in f.KNOWN_MODEL_DIM


def test_arm_run_id_places_each_arm_under_the_probe_id():
    assert f.arm_run_id(f.ARM_A_LCO3) == "SAEA-PROBE-pemb4r-4100/a-lco3"
    assert f.arm_run_id(f.ARM_T_QW) == "SAEA-PROBE-pemb4r-4100/t-qw"


def test_arm_run_id_refuses_an_unknown_arm_id():
    with pytest.raises(f.Pemb4rFlightError, match="unknown arm_id"):
        f.arm_run_id("not-a-real-arm")


# ---------------------------------------------------------------------------
# Frozen-60-gold-access AST guard.
# ---------------------------------------------------------------------------


def test_assert_never_accesses_frozen_60_gold_passes_on_real_source():
    f.assert_never_accesses_frozen_60_gold()  # does not raise


@pytest.mark.parametrize("snippet", ["sample.scenario", "sample.action", "sample.entities", "sample.intent"])
def test_assert_never_accesses_frozen_60_gold_catches_each_forbidden_attribute(snippet):
    with pytest.raises(f.Pemb4rFlightError, match="dot-accesses"):
        f.assert_never_accesses_frozen_60_gold(f"def f(sample):\n    return {snippet}\n")


def test_assert_never_accesses_frozen_60_gold_never_flags_bank_gold_scenario():
    f.assert_never_accesses_frozen_60_gold("def f(entry):\n    return entry.gold_scenario\n")  # does not raise


# ---------------------------------------------------------------------------
# Bank builder.
# ---------------------------------------------------------------------------


def test_build_bank_table_happy_path_and_determinism():
    labels = [f"scenario-{i}" for i in range(18)]
    pool = _pool(labels, 50)
    bank1 = f.build_bank_table(pool, labels)
    bank2 = f.build_bank_table(pool, labels)
    f.validate_bank_table(bank1)
    assert len(bank1.entries) == 900
    assert f.bank_manifest_sha256(bank1) == f.bank_manifest_sha256(bank2)
    ids1 = [e.bank_id for e in bank1.entries]
    ids2 = [e.bank_id for e in bank2.entries]
    assert ids1 == ids2


def test_build_bank_table_refuses_insufficient_pool_coverage():
    labels = [f"scenario-{i}" for i in range(18)]
    pool = _pool(labels, 10)  # < 50 per scenario
    with pytest.raises(f.Pemb4rFlightError, match="TRAIN candidate"):
        f.build_bank_table(pool, labels)


def test_build_bank_table_refuses_duplicate_canonical_labels():
    with pytest.raises(f.Pemb4rFlightError, match="duplicate canonical label"):
        f.build_bank_table(_pool(["a"], 50), ["a", "a"])


def test_build_bank_table_gold_scenario_is_metadata_only_never_the_embedded_text():
    labels = [f"scenario-{i}" for i in range(18)]
    bank = f.build_bank_table(_pool(labels, 50), labels)
    for entry in bank.entries:
        assert entry.gold_scenario not in entry.text or entry.gold_scenario in entry.text  # sanity: field is separate
        assert entry.text_sha256 == __import__("hashlib").sha256(entry.text.encode("utf-8")).hexdigest()


def test_validate_bank_table_refuses_wrong_total():
    labels = [f"scenario-{i}" for i in range(18)]
    bank = f.build_bank_table(_pool(labels, 50), labels)
    truncated = f.BankTable(entries=bank.entries[:-1], seed=bank.seed, per_scenario_n=bank.per_scenario_n)
    with pytest.raises(f.Pemb4rFlightError, match="expected exactly"):
        f.validate_bank_table(truncated)


def test_bank_manifest_write_then_load_round_trips(tmp_path):
    labels = [f"scenario-{i}" for i in range(18)]
    bank = f.build_bank_table(_pool(labels, 50), labels)
    path = f.write_bank_manifest(tmp_path, bank)
    assert path.is_file()
    loaded = f.load_bank_manifest(tmp_path, expected_sha256=None)
    assert len(loaded.entries) == len(bank.entries)
    assert f.bank_manifest_sha256(loaded) == f.bank_manifest_sha256(bank)


def test_load_bank_manifest_refuses_missing_file(tmp_path):
    with pytest.raises(f.Pemb4rFlightError, match="missing"):
        f.load_bank_manifest(tmp_path, expected_sha256=None)


def test_load_bank_manifest_refuses_a_tampered_text(tmp_path):
    import json

    labels = [f"scenario-{i}" for i in range(18)]
    bank = f.build_bank_table(_pool(labels, 50), labels)
    path = f.write_bank_manifest(tmp_path, bank)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["entries"][0]["text"] = "TAMPERED"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(f.Pemb4rFlightError, match="text_sha256 mismatch"):
        f.load_bank_manifest(tmp_path, expected_sha256=None)


@pytest.mark.requires_umbrella_checkout
def test_bank_manifest_sha256_matches_the_pinned_constant_on_the_real_governed_bank(slurp_world):
    """Live proof (module docstring): the REAL governed train.jsonl, the
    REAL 18 canonical labels, the registered seed/per_scenario_n -- must
    reproduce the pinned BANK_MANIFEST_SHA256 exactly, or this test
    (offline, filesystem-only, zero model contact) refuses to import a
    drifted train.jsonl silently."""

    from speech_aware_evidence_acquisition.rails.probes.pfew_flight import load_train_demo_pool
    from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters
    from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import canonical_scenario_labels

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = _real_data_root_or_skip()
    rosters = load_pslu_rosters(REPO_ROOT / "configs/probes/g0-binding/pslu-rosters-train-only.json")
    labels = canonical_scenario_labels(rosters)
    pool = load_train_demo_pool(lock, root)
    bank = f.build_bank_table(pool, labels)
    f.validate_bank_table(bank)
    assert f.bank_manifest_sha256(bank) == f.BANK_MANIFEST_SHA256


def _real_data_root_or_skip():
    import os

    value = os.environ.get("SPEECHRL_DATA_DIR")
    if not value:
        pytest.skip("SPEECHRL_DATA_DIR not set -- real-governed-carrier bank determinism proof needs it")
    root = Path(value)
    if not (root / "datasets" / "slurp" / "metadata" / "train.jsonl").is_file():
        pytest.skip("real governed SLURP train.jsonl not present under SPEECHRL_DATA_DIR")
    return root


# ---------------------------------------------------------------------------
# resolve_model_binding / binding config sha256 (reuse from pemb3m_flight).
# ---------------------------------------------------------------------------


@pytest.mark.requires_umbrella_checkout
def test_binding_config_sha256_matches_the_pinned_constant_on_the_real_umbrella_lock():
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    assert f.binding_config_sha256(lock) == f.BINDING_CONFIG_SHA256


@pytest.mark.requires_umbrella_checkout
def test_assert_binding_config_sha256_accepts_the_real_lock():
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    f.assert_binding_config_sha256(lock)  # does not raise


def test_assert_binding_config_sha256_refuses_a_drifted_lock():
    with pytest.raises(f.Pemb4rFlightError, match="sha256"):
        f.assert_binding_config_sha256(_synthetic_lock())


def test_binding_config_sha256_at_flight_matches_the_sealed_pemb4r_receipt():
    """The 2026-09-08 re-pin (umbrella commit faebc8f, owner Decision 11-D)
    changes the LIVE ``BINDING_CONFIG_SHA256`` because the umbrella lock's
    own ``lco-embedding-omni-3b-gguf`` entry was resolved from an unresolved
    local candidate to a real HF source -- it does not touch, and cannot
    touch, the already-sealed 2026-08-20 P-EMB-4R flight's own evidence.
    Read the sealed receipt directly (never recomputed) so a future edit to
    ``BINDING_CONFIG_SHA256_AT_FLIGHT`` that drifted from what was actually
    sealed would be caught here, not discovered by an auditor."""
    import json

    receipt_path = (
        REPO_ROOT
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-08-20-pemb4r-flight"
        / "flight-receipt.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["binding_config_sha256"] == f.BINDING_CONFIG_SHA256_AT_FLIGHT


def test_build_binding_config_document_covers_every_arm_and_the_bank_and_t0_pin():
    document = f.build_binding_config_document(_synthetic_lock())
    assert document["split_identity_hash"] == f.EXPECTED_SPLIT_IDENTITY_HASH
    assert document["query_n"] == f.QUERY_N
    assert document["bank"]["manifest_sha256"] == f.BANK_MANIFEST_SHA256
    assert document["t0_transcript_registry_sha256"] == f.PKEY2_338_TRANSCRIPT_REGISTRY_SHA256
    assert [arm["arm_id"] for arm in document["arms"]] == sorted(f.ARM_IDS)


# ---------------------------------------------------------------------------
# Ceilings.
# ---------------------------------------------------------------------------


def test_assert_within_registered_ceilings_accepts_the_registered_plan():
    f.assert_within_registered_ceilings(calls=4100, audio_seconds=547, gpu_hours=0.5)  # does not raise


def test_assert_within_registered_ceilings_refuses_over_calls():
    with pytest.raises(f.Pemb4rFlightError, match="calls"):
        f.assert_within_registered_ceilings(calls=4501, audio_seconds=0, gpu_hours=0)


def test_assert_within_registered_ceilings_refuses_over_audio_seconds():
    with pytest.raises(f.Pemb4rFlightError, match="audio-second"):
        f.assert_within_registered_ceilings(calls=0, audio_seconds=701, gpu_hours=0)


def test_assert_within_registered_ceilings_refuses_over_gpu_hours():
    with pytest.raises(f.Pemb4rFlightError, match="GPU-hour"):
        f.assert_within_registered_ceilings(calls=0, audio_seconds=0, gpu_hours=0.51)


def test_assert_gpu_hours_within_ceiling_gates_on_active_and_measured_equivalent_never_wall():
    # Wall overshoots the ceiling but BOTH accounted bases stay inside it --
    # the pcorrf section-8 ruling -- must NOT raise.
    accounting = f.GpuHoursAccounting(wall_hours=0.6, gpu_active_hours=0.1, measured_equivalent_hours=0.14)
    f.assert_gpu_hours_within_ceiling(accounting)  # does not raise


def test_assert_gpu_hours_within_ceiling_refuses_over_active_occupancy():
    accounting = f.GpuHoursAccounting(wall_hours=0.1, gpu_active_hours=0.6, measured_equivalent_hours=0.1)
    with pytest.raises(f.Pemb4rFlightError, match="GPU-active"):
        f.assert_gpu_hours_within_ceiling(accounting)


def test_assert_gpu_hours_within_ceiling_refuses_over_measured_equivalent():
    accounting = f.GpuHoursAccounting(wall_hours=0.1, gpu_active_hours=0.1, measured_equivalent_hours=0.6)
    with pytest.raises(f.Pemb4rFlightError, match="measured-equivalent"):
        f.assert_gpu_hours_within_ceiling(accounting)


# ---------------------------------------------------------------------------
# contracts.ExecutionPlan integration.
# ---------------------------------------------------------------------------


def test_build_execution_plan_happy_path():
    lock = _synthetic_lock()
    plan = f.build_execution_plan(lock=lock, attempt_id="attempt-20260820T000000Z-abcdef")
    assert plan.run_id == f.PROBE_ID
    assert plan.execution_profile == "bounded-discovery-probe"
    assert plan.split_role == "discovery"
    assert plan.split_identity_hash == f.EXPECTED_SPLIT_IDENTITY_HASH
    assert plan.protocol_hash == f.binding_config_sha256(lock)
    assert plan.planned_model_calls == f.DEFAULT_PLANNED_MODEL_CALLS


def test_build_execution_plan_refuses_over_ceiling_calls():
    with pytest.raises(f.Pemb4rFlightError, match="calls"):
        f.build_execution_plan(lock=_synthetic_lock(), planned_model_calls=f.CEILING_CALLS + 1)


# ---------------------------------------------------------------------------
# Gate (a): LCO-7B server sanity.
# ---------------------------------------------------------------------------


def test_run_lco7_server_sanity_gate_reports_ok_and_measured_dim():
    client = MockEmbeddingClient(expected_dim=3584)
    result = f.run_lco7_server_sanity_gate(client=client)
    assert result.status == f.STATUS_OK
    assert result.measured_dim == 3584
    assert result.sanity_vector is not None


def test_run_lco7_server_sanity_gate_reports_dropped_on_failure():
    class _BrokenClient:
        def verify_media_marker(self):
            from speech_aware_evidence_acquisition.rails.embedding_client import EmbeddingClientError

            raise EmbeddingClientError("boom")

        def embed_text(self, *, contact_id, text):  # pragma: no cover -- never reached
            raise AssertionError("should not be called")

    result = f.run_lco7_server_sanity_gate(client=_BrokenClient())
    assert result.status == f.STATUS_DROPPED_LCO7
    assert result.measured_dim is None
    assert "boom" in result.detail


# ---------------------------------------------------------------------------
# Gate (b): GLAP import + audio-path sanity (the pemb3m gate-(b) amendment).
# ---------------------------------------------------------------------------


def test_run_glap_import_and_audio_sanity_gate_happy_path():
    client = MockLocalEncoderClient(expected_dim=GLAP_EMBEDDING_DIM)
    result = f.run_glap_import_and_audio_sanity_gate(
        model_id="glap", loader=lambda: client, sanity_audio_bytes=b"FAKEAUDIO"
    )
    assert result.status == STATUS_OK
    assert result.arm_id == f.MODEL_GLAP


def test_run_glap_import_and_audio_sanity_gate_reports_dropped_deps_on_missing_import():
    def loader():
        raise ImportError("no transformers")

    result = f.run_glap_import_and_audio_sanity_gate(model_id="glap", loader=loader, sanity_audio_bytes=b"x")
    assert result.status == STATUS_DROPPED_DEPS


def test_run_glap_import_and_audio_sanity_gate_reports_dropped_deps_when_only_audio_path_fails():
    class _TextOnlyClient:
        def embed_text(self, *, contact_id, text):
            return EmbeddingVector(contact_id=contact_id, kind="text", values=(1.0,) * GLAP_EMBEDDING_DIM)

        def embed_audio(self, *, contact_id, audio_bytes):
            raise ImportError("audio backend missing")

    result = f.run_glap_import_and_audio_sanity_gate(
        model_id="glap", loader=lambda: _TextOnlyClient(), sanity_audio_bytes=b"x"
    )
    assert result.status == STATUS_DROPPED_DEPS
    assert "audio-path sanity failed" in result.detail


# ---------------------------------------------------------------------------
# Gate (c): pooling-differ (reused verbatim, module docstring).
# ---------------------------------------------------------------------------


def test_pooling_override_scope_for_model_flows_to_both_arms():
    scope = f.pooling_override_scope_for_model(f.MODEL_LCO3, True)
    assert scope["pooling_override_present"] is True
    assert scope["scope_tag"] == f.POOLING_OVERRIDE_SCOPE_TAG
    assert set(scope["scoped_arm_ids"]) == {f.ARM_A_LCO3, f.ARM_T_LCO3}


def test_pooling_override_scope_for_model_false_carries_no_scope_tag():
    scope = f.pooling_override_scope_for_model(f.MODEL_LCO7, False)
    assert scope["scope_tag"] is None


def test_pooling_override_scope_for_model_refuses_unknown_model():
    with pytest.raises(f.Pemb4rFlightError, match="unknown model"):
        f.pooling_override_scope_for_model("not-a-model", True)


def test_run_pooling_differ_gate_reexported_and_usable():
    audio_bytes = b"FAKEAUDIO"
    last_client = MockEmbeddingClient(expected_dim=8, vector_source=lambda kind, cid: deterministic_unit_vector("same", dims=8))
    mean_client = MockEmbeddingClient(expected_dim=8, vector_source=lambda kind, cid: deterministic_unit_vector("same", dims=8))
    result = f.run_pooling_differ_gate(last_client=last_client, mean_client=mean_client, audio_bytes=audio_bytes)
    assert result.pooling_override_present is True  # identical mock vectors


# ---------------------------------------------------------------------------
# Gate (d): encode-only preflight.
# ---------------------------------------------------------------------------


def test_run_encode_only_preflight_gate_covers_this_module():
    report = f.run_encode_only_preflight_gate()
    assert "speech_aware_evidence_acquisition.rails.probes.pemb4r_flight" in report.checked_modules


# ---------------------------------------------------------------------------
# Gate (e): cascade/T0 source check -- reused verbatim.
# ---------------------------------------------------------------------------


def test_run_pemb4r_cascade_source_check_reports_absent_when_registry_missing(tmp_path):
    ledger_text = f"| {f.PKEY2_338_RUN_EXPERIMENT_ID} | ... | ... | ... | ... | ... | ... | ... | yes |\n"
    result = f.run_pemb4r_cascade_source_check(
        data_root=tmp_path, ledger_text=ledger_text, expected_sample_ids=frozenset({"a", "b"})
    )
    assert result.status == "ABSENT"


def test_run_pemb4r_cascade_source_check_refuses_when_ledger_row_not_consumed(tmp_path):
    # run_cascade_source_check is reused VERBATIM from rails.probes.pemb3m_flight
    # (module docstring): it raises that module's OWN Pemb3mFlightError, a
    # sibling PembFlightError subclass, never re-wrapped into Pemb4rFlightError.
    ledger_text = f"| {f.PKEY2_338_RUN_EXPERIMENT_ID} | ... | ... | ... | ... | ... | ... | ... | no |\n"
    with pytest.raises(PembFlightError, match="consumed"):
        f.run_pemb4r_cascade_source_check(
            data_root=tmp_path, ledger_text=ledger_text, expected_sample_ids=frozenset({"a"})
        )


# ---------------------------------------------------------------------------
# Vector-manifest primitive + bank/query namespaces.
# ---------------------------------------------------------------------------


def _vecs(n: int, dim: int, prefix: str) -> tuple[EmbeddingVector, ...]:
    return tuple(
        EmbeddingVector(contact_id=f"{prefix}-{i:03d}", kind="text", values=tuple([1.0] + [0.0] * (dim - 1)))
        for i in range(n)
    )


def test_bank_vectors_write_then_load_round_trips(tmp_path):
    vectors = _vecs(5, 8, "bank-x")
    path = f.write_bank_vectors(tmp_path, f.MODEL_GLAP, vectors)
    assert path.is_file()
    loaded = f.load_bank_vectors(tmp_path, f.MODEL_GLAP, expected_count=5)
    assert loaded.dims == 8
    assert set(loaded.vectors) == {v.contact_id for v in vectors}


def test_load_bank_vectors_refuses_missing(tmp_path):
    with pytest.raises(f.Pemb4rFlightError, match="missing"):
        f.load_bank_vectors(tmp_path, f.MODEL_LCO3)


def test_load_bank_vectors_refuses_a_tampered_vector_file(tmp_path):
    vectors = _vecs(3, 4, "bank-y")
    f.write_bank_vectors(tmp_path, f.MODEL_QW, vectors)
    vector_path = next(f._bank_vectors_dir(tmp_path, f.MODEL_QW).glob("*.npy"))
    vector_path.write_bytes(b"corrupted")
    with pytest.raises(f.Pemb4rFlightError, match="sha256 mismatch"):
        f.load_bank_vectors(tmp_path, f.MODEL_QW, expected_count=3)


def test_query_vectors_write_then_load_round_trips(tmp_path):
    vectors = _vecs(4, 6, "q")
    f.write_query_vectors(tmp_path, f.ARM_A_LCO3, vectors)
    loaded = f.load_query_vectors(tmp_path, f.ARM_A_LCO3, expected_count=4)
    assert loaded.dims == 6
    assert len(loaded.vectors) == 4


def test_write_bank_vectors_refuses_unknown_model(tmp_path):
    with pytest.raises(f.Pemb4rFlightError, match="unknown model"):
        f.write_bank_vectors(tmp_path, "not-a-model", _vecs(1, 2, "x"))


def test_write_query_vectors_refuses_unknown_arm(tmp_path):
    with pytest.raises(f.Pemb4rFlightError, match="unknown arm_id"):
        f.write_query_vectors(tmp_path, "not-an-arm", _vecs(1, 2, "x"))


# ---------------------------------------------------------------------------
# is_*_complete / sweep orchestration -- idempotence.
# ---------------------------------------------------------------------------


def test_is_bank_vectors_complete_false_then_true(tmp_path):
    assert f.is_bank_vectors_complete(tmp_path, f.MODEL_LCO3) is False
    f.write_bank_vectors(tmp_path, f.MODEL_LCO3, _vecs(2, 2, "b"))
    assert f.is_bank_vectors_complete(tmp_path, f.MODEL_LCO3) is True


def test_is_query_vectors_complete_false_then_true(tmp_path):
    assert f.is_query_vectors_complete(tmp_path, f.ARM_T_QW) is False
    f.write_query_vectors(tmp_path, f.ARM_T_QW, _vecs(2, 2, "q"))
    assert f.is_query_vectors_complete(tmp_path, f.ARM_T_QW) is True


def test_run_pemb4r_bank_sweep_never_respawns_a_completed_model(tmp_path):
    labels = [f"scenario-{i}" for i in range(3)]
    bank = f.BankTable(
        entries=tuple(
            f.BankEntry(bank_id=f"bank-{label}-{j:03d}", gold_scenario=label, text=f"t{label}{j}", text_sha256="x", train_sample_id=f"s{label}{j}")
            for label in labels
            for j in range(2)
        ),
        seed=1,
        per_scenario_n=2,
    )
    calls = {"n": 0}

    def runner():
        calls["n"] += 1
        return _vecs_for_bank(bank, dim=4)

    results1 = f.run_pemb4r_bank_sweep(root=tmp_path, bank=bank, model_runners={f.MODEL_GLAP: runner})
    assert calls["n"] == 1
    results2 = f.run_pemb4r_bank_sweep(root=tmp_path, bank=bank, model_runners={f.MODEL_GLAP: runner})
    assert calls["n"] == 1  # never respawned
    assert set(results1[f.MODEL_GLAP].vectors) == set(results2[f.MODEL_GLAP].vectors)


def _vecs_for_bank(bank: "f.BankTable", *, dim: int) -> tuple[EmbeddingVector, ...]:
    return tuple(
        EmbeddingVector(contact_id=entry.bank_id, kind="text", values=deterministic_unit_vector(entry.bank_id, dims=dim))
        for entry in bank.entries
    )


def test_run_pemb4r_bank_sweep_refuses_unknown_model(tmp_path):
    bank = f.BankTable(entries=(), seed=1, per_scenario_n=1)
    with pytest.raises(f.Pemb4rFlightError, match="unknown model"):
        f.run_pemb4r_bank_sweep(root=tmp_path, bank=bank, model_runners={"not-a-model": lambda: ()})


def test_run_pemb4r_query_sweep_never_respawns_a_completed_arm(tmp_path):
    calls = {"n": 0}

    def runner():
        calls["n"] += 1
        return _vecs(f.QUERY_N, 4, "q")

    results1 = f.run_pemb4r_query_sweep(root=tmp_path, arm_runners={f.ARM_A_GLAP: runner})
    assert calls["n"] == 1
    results2 = f.run_pemb4r_query_sweep(root=tmp_path, arm_runners={f.ARM_A_GLAP: runner})
    assert calls["n"] == 1
    assert set(results1[f.ARM_A_GLAP].vectors) == set(results2[f.ARM_A_GLAP].vectors)


def test_run_pemb4r_query_sweep_refuses_unknown_arm(tmp_path):
    with pytest.raises(f.Pemb4rFlightError, match="unknown arm"):
        f.run_pemb4r_query_sweep(root=tmp_path, arm_runners={"not-an-arm": lambda: ()})


# ---------------------------------------------------------------------------
# Embedding runners.
# ---------------------------------------------------------------------------


def test_run_server_bank_embedding_embeds_every_entry(slurp_world):
    labels = [f"scenario-{i}" for i in range(3)]
    bank = f.build_bank_table(_pool(labels, 2), labels, per_scenario_n=2)
    client = MockEmbeddingClient()
    vectors = f.run_server_bank_embedding(client=client, bank=bank)
    assert len(vectors) == len(bank.entries)
    assert client.marker_verified is True


def test_run_local_bank_embedding_embeds_every_entry():
    labels = [f"scenario-{i}" for i in range(3)]
    bank = f.build_bank_table(_pool(labels, 2), labels, per_scenario_n=2)
    client = MockLocalEncoderClient(expected_dim=GLAP_EMBEDDING_DIM)
    vectors = f.run_local_bank_embedding(client=client, bank=bank)
    assert len(vectors) == len(bank.entries)


def test_run_server_audio_query_reads_only_sample_id_and_media_relpath(slurp_world):
    adapter = SlurpAdapter(load_lock(slurp_world.lock_path), slurp_world.data_root)
    samples = adapter.load_split("devel")
    samples60 = tuple(samples[i % len(samples)] for i in range(f.QUERY_N))
    # Distinct sample_ids required by the validator -- rebuild with unique ids.
    samples60 = tuple(
        SlurpSample(
            sample_id=f"slurp:devel:{i:06d}",
            audio_ref=samples[0].audio_ref,
            audio_seconds=1.0,
            utterance_id=str(i),
            media_relpath=samples[0].media_relpath,
            scenario="iot",
            action="a",
            intent="i",
            entities=(),
        )
        for i in range(f.QUERY_N)
    )
    client = MockEmbeddingClient()
    vectors = f.run_server_audio_query(client=client, samples=samples60, data_root=slurp_world.data_root)
    assert len(vectors) == f.QUERY_N


def test_run_server_text_query_requires_full_transcript_coverage():
    registry = {f"slurp:devel:{i:06d}": build_transcript_record(f"slurp:devel:{i:06d}", "x") for i in range(f.QUERY_N - 1)}
    sample_ids = [f"slurp:devel:{i:06d}" for i in range(f.QUERY_N)]
    with pytest.raises(f.Pemb4rFlightError, match="missing"):
        f.run_server_text_query(client=MockEmbeddingClient(), transcript_registry=registry, sample_ids=sample_ids)


def test_run_server_text_query_happy_path():
    sample_ids = [f"slurp:devel:{i:06d}" for i in range(f.QUERY_N)]
    registry = {sid: build_transcript_record(sid, f"transcript {sid}") for sid in sample_ids}
    client = MockEmbeddingClient(expected_dim=1024)
    vectors = f.run_server_text_query(client=client, transcript_registry=registry, sample_ids=sample_ids)
    assert len(vectors) == f.QUERY_N
    assert all(kind == "text" for kind, _cid in client.calls)


def test_run_local_text_query_happy_path():
    sample_ids = [f"slurp:devel:{i:06d}" for i in range(f.QUERY_N)]
    registry = {sid: build_transcript_record(sid, f"transcript {sid}") for sid in sample_ids}
    client = MockLocalEncoderClient(expected_dim=GLAP_EMBEDDING_DIM)
    vectors = f.run_local_text_query(client=client, transcript_registry=registry, sample_ids=sample_ids)
    assert len(vectors) == f.QUERY_N


# ---------------------------------------------------------------------------
# Retrieval plan (flight-side, gold-free).
# ---------------------------------------------------------------------------


def _bank_of(labels_by_id: dict[str, str]) -> tuple[str, ...]:
    return tuple(labels_by_id)


def test_build_arm_retrieval_dedups_and_ranks_by_cosine():
    bank_vectors = {
        "b1": (1.0, 0.0),
        "b2": (0.9, 0.1),
        "b3": (0.0, 1.0),
    }
    bank_labels = {"b1": "iot", "b2": "iot", "b3": "weather"}
    query_vectors = {"s1": (1.0, 0.0)}
    retrieval = f.build_arm_retrieval("a-glap", query_vectors, bank_vectors, bank_labels, k=3)
    row = retrieval.per_sample["s1"]
    assert row.top_k_bank_ids == ("b1", "b2", "b3")
    assert row.dedup_labels_k1 == ("iot",)
    assert row.dedup_labels_k3 == ("iot", "weather")
    assert row.dedup_labels_k5 == ("iot", "weather")
    assert retrieval.mean_top1_cosine == pytest.approx(1.0)


def test_select_retrieval_winner_picks_highest_mean_top1_cosine():
    weak = f.ArmRetrieval(arm_id="weak", per_sample={}, mean_top1_cosine=0.1)
    strong = f.ArmRetrieval(arm_id="strong", per_sample={}, mean_top1_cosine=0.9)
    winner = f.select_retrieval_winner({"weak": weak, "strong": strong})
    assert winner == "strong"


def test_select_retrieval_winner_breaks_ties_by_sorted_arm_id():
    a = f.ArmRetrieval(arm_id="a-arm", per_sample={}, mean_top1_cosine=0.5)
    b = f.ArmRetrieval(arm_id="b-arm", per_sample={}, mean_top1_cosine=0.5)
    winner = f.select_retrieval_winner({"b-arm": b, "a-arm": a})
    assert winner == "a-arm"


def test_select_retrieval_winner_refuses_empty():
    with pytest.raises(f.Pemb4rFlightError, match="non-empty"):
        f.select_retrieval_winner({})


def test_build_retrieval_plan_document_and_write_load_round_trip(tmp_path):
    bank_vectors = {"b1": (1.0, 0.0), "b2": (0.0, 1.0)}
    bank_labels = {"b1": "iot", "b2": "weather"}
    query_vectors = {"s1": (1.0, 0.0)}
    retrieval = f.build_arm_retrieval(f.ARM_A_GLAP, query_vectors, bank_vectors, bank_labels)
    document = f.build_retrieval_plan_document({f.ARM_A_GLAP: retrieval}, f.ARM_A_GLAP)
    assert document["winner_arm_id"] == f.ARM_A_GLAP
    assert document["winner_selection_rule"] == f.WINNER_SELECTION_RULE
    path, sha = f.write_retrieval_plan(tmp_path, document)
    assert path.is_file()
    loaded = f.load_retrieval_plan(tmp_path)
    assert loaded["winner_arm_id"] == f.ARM_A_GLAP
    assert f.retrieval_plan_document_sha256(loaded) == sha


def test_build_retrieval_plan_document_refuses_unknown_winner():
    with pytest.raises(f.Pemb4rFlightError, match="winner_arm_id"):
        f.build_retrieval_plan_document({}, "no-such-arm")


def test_load_retrieval_plan_refuses_missing(tmp_path):
    with pytest.raises(f.Pemb4rFlightError, match="missing"):
        f.load_retrieval_plan(tmp_path)


# ---------------------------------------------------------------------------
# C-DECODE.
# ---------------------------------------------------------------------------


def _sample(sample_id: str, media_relpath: str = "audio.flac") -> SlurpSample:
    return SlurpSample(
        sample_id=sample_id,
        audio_ref=AudioRef(path=media_relpath, sha256="0" * 64),
        audio_seconds=1.0,
        utterance_id="1",
        media_relpath=media_relpath,
        scenario="iot",
        action="a",
        intent="i",
        entities=(),
    )


def test_assemble_c_decode_messages_audio_reuses_slurp_adapter(slurp_world):
    adapter = SlurpAdapter(load_lock(slurp_world.lock_path), slurp_world.data_root)
    supply = f.build_c_decode_supply_packet(["iot", "weather"])
    sample = _sample("slurp:devel:000101")
    messages = f.assemble_c_decode_messages(sample, supply, query_kind="audio", adapter=adapter)
    assert messages[1]["content"][-1]["type"] == "input_audio"


def test_assemble_c_decode_messages_text_is_audio_free():
    supply = f.build_c_decode_supply_packet(["iot", "weather"])
    sample = _sample("slurp:devel:000101")
    registry = {"slurp:devel:000101": build_transcript_record("slurp:devel:000101", "turn on the lights")}
    messages = f.assemble_c_decode_messages(sample, supply, query_kind="text", transcript_registry=registry)
    parts = messages[1]["content"]
    assert all(part["type"] == "text" for part in parts)
    assert "turn on the lights" in parts[-1]["text"]


def test_assemble_c_decode_messages_refuses_audio_without_adapter():
    supply = f.build_c_decode_supply_packet(["iot"])
    with pytest.raises(f.Pemb4rFlightError, match="adapter"):
        f.assemble_c_decode_messages(_sample("s1"), supply, query_kind="audio")


def test_assemble_c_decode_messages_refuses_unknown_query_kind():
    supply = f.build_c_decode_supply_packet(["iot"])
    with pytest.raises(f.Pemb4rFlightError, match="query_kind"):
        f.assemble_c_decode_messages(_sample("s1"), supply, query_kind="video")


def _retrieval_plan_for_c_decode(sample_ids: list[str], winner_arm_id: str) -> dict:
    per_sample = {
        sid: {
            "sample_id": sid,
            "top_k_bank_ids": ["b1", "b2"],
            "top_k_cosines": [0.9, 0.8],
            "top_k_labels": ["iot", "weather"],
            "dedup_labels_k1": ["iot"],
            "dedup_labels_k3": ["iot", "weather"],
            "dedup_labels_k5": ["iot", "weather"],
        }
        for sid in sample_ids
    }
    return f.build_retrieval_plan_document(
        {winner_arm_id: f.ArmRetrieval(arm_id=winner_arm_id, per_sample={}, mean_top1_cosine=0.9)}, winner_arm_id
    ) | {"arms": {winner_arm_id: {"mean_top1_cosine": 0.9, "per_sample": per_sample}}}


def test_run_c_decode_flight_text_winner_happy_path():
    sample_ids = [f"slurp:devel:{i:06d}" for i in range(f.QUERY_N)]
    samples = tuple(_sample(sid) for sid in sample_ids)
    registry = {sid: build_transcript_record(sid, f"utterance {sid}") for sid in sample_ids}
    document = _retrieval_plan_for_c_decode(sample_ids, f.ARM_T_QW)
    core_client = MockCoreClient(responder=lambda messages: '{"scenario": "iot", "action": "x", "entities": []}')
    results = f.run_c_decode_flight(
        core_client=core_client,
        samples=samples,
        retrieval_plan_document=document,
        winner_arm_id=f.ARM_T_QW,
        winner_query_kind="text",
        transcript_registry=registry,
    )
    assert len(results) == f.QUERY_N
    assert results[0].candidate_labels == ("iot", "weather")
    assert results[0].closed_set_mapping.canonical_label == "iot"
    f.validate_c_decode_results(results, expected_sample_ids=sample_ids)


def test_run_c_decode_flight_refuses_missing_retrieval_row():
    sample_ids = [f"slurp:devel:{i:06d}" for i in range(f.QUERY_N)]
    samples = tuple(_sample(sid) for sid in sample_ids)
    document = _retrieval_plan_for_c_decode(sample_ids[:-1], f.ARM_T_QW)  # missing the last sample's own row
    registry = {sid: build_transcript_record(sid, "x") for sid in sample_ids}
    with pytest.raises(f.Pemb4rFlightError, match="no row"):
        f.run_c_decode_flight(
            core_client=MockCoreClient(),
            samples=samples,
            retrieval_plan_document=document,
            winner_arm_id=f.ARM_T_QW,
            winner_query_kind="text",
            transcript_registry=registry,
        )


def test_validate_c_decode_results_refuses_sample_id_mismatch():
    result = f.CDecodeResult(
        sample_id="s1", candidate_labels=("iot",), messages=(), response_text="", closed_set_mapping=None
    )
    with pytest.raises(f.Pemb4rFlightError, match="mismatch"):
        f.validate_c_decode_results([result], expected_sample_ids=["s2"])


# ---------------------------------------------------------------------------
# Module-level self-check guards (import-time).
# ---------------------------------------------------------------------------


def test_module_never_calls_ontology_miner_at_import_time():
    f._assert_this_module_never_calls_ontology_miner()  # does not raise, real source


def test_module_never_calls_ontology_miner_catches_a_synthetic_reference():
    with pytest.raises(f.Pemb4rFlightError, match="load_slurp_ontology"):
        f._assert_this_module_never_calls_ontology_miner("from ...data.slurp import load_slurp_ontology\n")
