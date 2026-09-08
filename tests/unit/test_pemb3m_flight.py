"""``rails.probes.pemb3m_flight``: the P-EMB-3M four-arm multi-model
routing comparison flight (docs/readiness/
2026-08-20-pemb3m-preregistration-REGISTERED.md). Engineering-only, ZERO
live model contact -- every test drives ``rails.embedding_client.
MockEmbeddingClient`` / ``rails.local_encoder_client.MockLocalEncoderClient``
or a hand-built duck-typed double.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path, REPO_ROOT
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter, SlurpSample
from speech_aware_evidence_acquisition.rails.embedding_client import (
    EMBEDDING_DIM,
    MockEmbeddingClient,
    deterministic_unit_vector,
)
from speech_aware_evidence_acquisition.rails.local_encoder_client import (
    CLSP_EMBEDDING_DIM,
    GLAP_EMBEDDING_DIM,
    STATUS_DROPPED_DEPS,
    STATUS_OK,
    MockLocalEncoderClient,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes import pemb3m_flight as f
from speech_aware_evidence_acquisition.rails.probes.pemb_flight import PembFlightError
from speech_aware_evidence_acquisition.rails.probes.pkey_flight import assemble_t0_messages


def _slurp_adapter(world) -> SlurpAdapter:
    return SlurpAdapter(load_lock(world.lock_path), world.data_root)


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
                "name": "glap",
                "local_subdir": "models/glap",
                "source": {"kind": "observed-local", "id": "UNRESOLVED_LOCAL_SOURCE"},
                "revision": "UNRESOLVED_LOCAL_REVISION",
                "lifecycle": "LOCAL_CANDIDATE",
                "verification": {"size_bytes": 222, "files": 9},
            },
            {
                "name": "clsp",
                "local_subdir": "models/clsp",
                "source": {"kind": "observed-local", "id": "UNRESOLVED_LOCAL_SOURCE"},
                "revision": "UNRESOLVED_LOCAL_REVISION",
                "lifecycle": "LOCAL_CANDIDATE",
                "verification": {"size_bytes": 333, "files": 9},
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


# ---------------------------------------------------------------------------
# Registered constants.
# ---------------------------------------------------------------------------


def test_registered_totals():
    assert f.PROBE_ID == "SAEA-PROBE-pemb3m-388"
    assert f.ARM_QUERY_N == 60
    assert f.ARM_LABEL_N == 18
    assert f.ARM_TOTAL_N == 78
    assert f.PLANNED_TOTAL_EMBEDDING_CONTACTS == 312
    assert f.CASCADE_T0_SUPPLEMENT_MAX_CONTACTS == 66
    assert f.GATE_CONTACTS_MAX == 10
    assert f.DEFAULT_PLANNED_MODEL_CALLS == 388


def test_registered_ceilings():
    assert f.CEILING_CALLS == 440
    assert f.CEILING_AUDIO_SECONDS == 900
    assert f.CEILING_GPU_HOURS == 0.5


def test_pemb3m_flight_error_is_a_pemb_flight_error_subclass():
    assert issubclass(f.Pemb3mFlightError, PembFlightError)


def test_arm_dims_match_e1_identity():
    assert f.ARM_M1.embedding_dim == EMBEDDING_DIM == 2048
    assert f.ARM_M2.embedding_dim == GLAP_EMBEDDING_DIM == 1024
    assert f.ARM_M3.embedding_dim == CLSP_EMBEDDING_DIM == 512
    assert f.ARM_M4.embedding_dim == f.QWEN3_EMB_EMBEDDING_DIM == 1024


def test_arms_by_id_maps_every_registered_arm_id():
    assert set(f.ARMS_BY_ID) == set(f.ARM_IDS)
    assert f.ARMS_BY_ID[f.ARM_M1_ID] is f.ARM_M1
    assert f.ARMS_BY_ID[f.ARM_M4_ID] is f.ARM_M4


def test_control_arm_ids():
    assert f.CONTROL_ARM_IDS == (f.ARM_M2_ID, f.ARM_M3_ID)


def test_arm_run_id_places_each_arm_under_the_probe_id():
    assert f.arm_run_id(f.ARM_M1_ID) == "SAEA-PROBE-pemb3m-388/m1-lco-primary"
    assert f.arm_run_id(f.ARM_M4_ID) == "SAEA-PROBE-pemb3m-388/m4-cascade"


def test_arm_run_id_refuses_an_unknown_arm_id():
    with pytest.raises(f.Pemb3mFlightError, match="unknown arm_id"):
        f.arm_run_id("not-a-real-arm")


def test_bare_prefixes_per_pemb1_precedent():
    document = f.build_binding_config_document(_synthetic_lock())
    assert document["prefixes"] == {"audio_prefix": "", "text_prefix": ""}


# ---------------------------------------------------------------------------
# resolve_model_binding / binding config sha256.
# ---------------------------------------------------------------------------


def test_resolve_model_binding_passes_through_local_candidate_fields_verbatim():
    binding = f.resolve_model_binding(_synthetic_lock(), "glap")
    assert binding["name"] == "glap"
    assert binding["local_subdir"] == "models/glap"
    assert binding["lifecycle"] == "LOCAL_CANDIDATE"
    assert binding["size_bytes"] == 222
    assert binding["files_count"] == 9
    assert binding["file_hashes"] == ()


def test_resolve_model_binding_carries_a_real_sha256_when_the_lock_has_one():
    binding = f.resolve_model_binding(_synthetic_lock(), "qwen3-embedding-0.6b-gguf")
    assert binding["file_hashes"] == ({"filename": "Qwen3-Embedding-0.6B-Q8_0.gguf", "sha256": "a" * 64},)


def test_resolve_model_binding_refuses_an_unknown_key():
    with pytest.raises(f.Pemb3mFlightError):
        f.resolve_model_binding(_synthetic_lock(), "does-not-exist")


@pytest.mark.requires_umbrella_checkout
def test_binding_config_sha256_matches_the_pinned_constant_on_the_real_umbrella_lock():
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    assert f.binding_config_sha256(lock) == f.BINDING_CONFIG_SHA256


@pytest.mark.requires_umbrella_checkout
def test_assert_binding_config_sha256_accepts_the_real_lock():
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    f.assert_binding_config_sha256(lock)  # does not raise


def test_assert_binding_config_sha256_refuses_a_drifted_lock():
    drifted = _synthetic_lock()
    with pytest.raises(f.Pemb3mFlightError, match="sha256"):
        f.assert_binding_config_sha256(drifted)


def test_binding_config_sha256_at_flight_matches_the_sealed_pemb3m_receipt():
    """The 2026-09-08 re-pin (umbrella commit faebc8f, owner Decision 11-D)
    changes the LIVE ``BINDING_CONFIG_SHA256`` because the umbrella lock's
    own ``lco-embedding-omni-3b-gguf`` entry was resolved from an unresolved
    local candidate to a real HF source -- it does not touch, and cannot
    touch, the already-sealed 2026-08-20 P-EMB-3M flight's own evidence.
    Read the sealed receipt directly (never recomputed) so a future edit to
    ``BINDING_CONFIG_SHA256_AT_FLIGHT`` that drifted from what was actually
    sealed would be caught here, not discovered by an auditor."""
    receipt_path = (
        REPO_ROOT
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-08-20-pemb3m-flight"
        / "flight-receipt.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["binding_config_sha256"] == f.BINDING_CONFIG_SHA256_AT_FLIGHT


def test_build_binding_config_document_covers_every_arm_and_the_t0_pin():
    document = f.build_binding_config_document(_synthetic_lock())
    assert document["split_identity_hash"] == f.EXPECTED_SPLIT_IDENTITY_HASH
    assert document["query_count"] == f.ARM_QUERY_N
    assert document["label_count"] == f.ARM_LABEL_N
    assert document["t0_transcript_registry_sha256"] == f.PKEY2_338_TRANSCRIPT_REGISTRY_SHA256
    assert [arm["arm_id"] for arm in document["arms"]] == list(f.ARM_IDS)


# ---------------------------------------------------------------------------
# Ceilings.
# ---------------------------------------------------------------------------


def test_assert_within_registered_ceilings_accepts_a_legal_plan():
    f.assert_within_registered_ceilings(calls=388, audio_seconds=900, gpu_hours=0.5)  # does not raise


def test_assert_within_registered_ceilings_refuses_over_calls():
    with pytest.raises(f.Pemb3mFlightError, match="calls"):
        f.assert_within_registered_ceilings(calls=441, audio_seconds=0, gpu_hours=0)


def test_assert_within_registered_ceilings_refuses_over_audio_seconds():
    with pytest.raises(f.Pemb3mFlightError, match="audio-second"):
        f.assert_within_registered_ceilings(calls=0, audio_seconds=901, gpu_hours=0)


def test_assert_within_registered_ceilings_refuses_over_gpu_hours():
    with pytest.raises(f.Pemb3mFlightError, match="GPU-hour"):
        f.assert_within_registered_ceilings(calls=0, audio_seconds=0, gpu_hours=0.51)


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
    with pytest.raises(f.Pemb3mFlightError, match="calls"):
        f.build_execution_plan(lock=_synthetic_lock(), planned_model_calls=f.CEILING_CALLS + 1)


def test_build_execution_plan_calls_assert_execution_scope_directly(monkeypatch):
    calls = []
    original = f.assert_execution_scope

    def spy(profile):
        calls.append(profile)
        return original(profile)

    monkeypatch.setattr(f, "assert_execution_scope", spy)
    f.build_execution_plan(lock=_synthetic_lock())
    assert calls == ["bounded-discovery-probe"]


# ---------------------------------------------------------------------------
# Pre-flight gate (a) -- POOLING-DIFFER.
# ---------------------------------------------------------------------------


def test_pooling_differ_gate_reports_no_override_when_vectors_differ():
    last_client = MockEmbeddingClient(vector_source=lambda kind, cid: deterministic_unit_vector("last-" + cid))
    mean_client = MockEmbeddingClient(vector_source=lambda kind, cid: deterministic_unit_vector("mean-" + cid))
    result = f.run_pooling_differ_gate(last_client=last_client, mean_client=mean_client, audio_bytes=b"AUDIO")
    assert result.pooling_override_present is False
    assert result.last_vector.values != result.mean_vector.values


def test_pooling_differ_gate_reports_override_present_when_byte_identical():
    same_source = lambda kind, cid: deterministic_unit_vector("same")
    last_client = MockEmbeddingClient(vector_source=same_source)
    mean_client = MockEmbeddingClient(vector_source=same_source)
    result = f.run_pooling_differ_gate(last_client=last_client, mean_client=mean_client, audio_bytes=b"AUDIO")
    assert result.pooling_override_present is True
    assert result.last_vector.values == result.mean_vector.values


def test_pooling_differ_gate_uses_exactly_two_contacts_per_client():
    last_client = MockEmbeddingClient()
    mean_client = MockEmbeddingClient()
    f.run_pooling_differ_gate(last_client=last_client, mean_client=mean_client, audio_bytes=b"AUDIO")
    assert len(last_client.calls) == 1
    assert len(mean_client.calls) == 1


def test_pooling_differ_gate_refuses_mismatched_dims():
    last_client = MockEmbeddingClient(expected_dim=2048)
    mean_client = MockEmbeddingClient(expected_dim=1024)
    with pytest.raises(f.Pemb3mFlightError, match="dim"):
        f.run_pooling_differ_gate(last_client=last_client, mean_client=mean_client, audio_bytes=b"AUDIO")


# ---------------------------------------------------------------------------
# Pre-flight gate (b) -- control import feasibility.
# ---------------------------------------------------------------------------


def test_control_import_feasibility_gates_ok_for_both_controls():
    results = f.run_control_import_feasibility_gates(
        loaders={
            f.ARM_M2_ID: ("glap", MockLocalEncoderClient),
            f.ARM_M3_ID: ("clsp", lambda: MockLocalEncoderClient(expected_dim=CLSP_EMBEDDING_DIM)),
        }
    )
    assert results[f.ARM_M2_ID].status == STATUS_OK
    assert results[f.ARM_M3_ID].status == STATUS_OK


def test_control_import_feasibility_gates_reports_dropped_deps_without_blocking():
    def failing_loader():
        raise ImportError("glap not installed")

    results = f.run_control_import_feasibility_gates(
        loaders={f.ARM_M2_ID: ("glap", failing_loader), f.ARM_M3_ID: ("clsp", MockLocalEncoderClient)}
    )
    assert results[f.ARM_M2_ID].status == STATUS_DROPPED_DEPS
    assert results[f.ARM_M3_ID].status == STATUS_OK


def test_control_import_feasibility_gates_refuses_a_non_control_arm_id():
    with pytest.raises(f.Pemb3mFlightError, match="unknown"):
        f.run_control_import_feasibility_gates(loaders={f.ARM_M1_ID: ("lco", MockLocalEncoderClient)})


# ---------------------------------------------------------------------------
# Pre-flight gate (c) -- ledger row + cascade source check.
# ---------------------------------------------------------------------------

_LEDGER_HEADER = (
    "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | "
    "split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | "
    "inherited exposure | artifacts | notes |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
)


def _ledger_row(run_experiment_id: str, consumed: str) -> str:
    return (
        f"| 2026-08-19 | {run_experiment_id} | bounded-discovery-probe | scope | model | carrier | discovery | "
        f"{'a' * 64} | {consumed} | 1 | 1 | 1 | inherited | artifacts | notes |\n"
    )


def test_assert_ledger_row_consumed_accepts_yes():
    text = _LEDGER_HEADER + _ledger_row("SAEA-PROBE-pkey2-338", "yes")
    f.assert_ledger_row_consumed(text)  # does not raise


def test_assert_ledger_row_consumed_refuses_no():
    text = _LEDGER_HEADER + _ledger_row("SAEA-PROBE-pkey2-338", "no")
    with pytest.raises(f.Pemb3mFlightError, match="consumed"):
        f.assert_ledger_row_consumed(text)


def test_assert_ledger_row_consumed_refuses_a_missing_row():
    with pytest.raises(f.Pemb3mFlightError, match="no row"):
        f.assert_ledger_row_consumed(_LEDGER_HEADER)


def test_assert_ledger_row_consumed_refuses_an_ambiguous_row():
    text = _LEDGER_HEADER + _ledger_row("SAEA-PROBE-pkey2-338", "yes") + _ledger_row("SAEA-PROBE-pkey2-338", "yes")
    with pytest.raises(f.Pemb3mFlightError, match="one"):
        f.assert_ledger_row_consumed(text)


def test_assert_ledger_row_consumed_against_the_real_ledger_file():
    repo_root = REPO_ROOT
    text = (repo_root / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    f.assert_ledger_row_consumed(text)  # does not raise -- pkey2-338 is consumed=yes


def _write_transcript_registry(root: Path, sample_ids) -> None:
    registry_path = root / f.PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    document = {}
    for sample_id in sample_ids:
        text = f"transcript for {sample_id}"
        import hashlib

        document[sample_id] = {"sample_id": sample_id, "text": text, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    registry_path.write_text(json.dumps(document), encoding="utf-8")


def test_run_cascade_source_check_reports_complete(tmp_path):
    sample_ids = frozenset(f"slurp:devel:{i:06d}" for i in range(3))
    _write_transcript_registry(tmp_path, sample_ids)
    ledger_text = _LEDGER_HEADER + _ledger_row("SAEA-PROBE-pkey2-338", "yes")
    result = f.run_cascade_source_check(
        data_root=tmp_path, ledger_text=ledger_text, expected_sample_ids=sample_ids, expected_registry_sha256=None
    )
    assert result.status == f.CASCADE_SOURCE_STATUS_COMPLETE
    assert result.supplement_required is False
    assert set(result.transcripts) == sample_ids


def test_run_cascade_source_check_reports_absent_when_file_missing(tmp_path):
    ledger_text = _LEDGER_HEADER + _ledger_row("SAEA-PROBE-pkey2-338", "yes")
    result = f.run_cascade_source_check(
        data_root=tmp_path, ledger_text=ledger_text, expected_sample_ids=frozenset({"slurp:devel:000000"})
    )
    assert result.status == f.CASCADE_SOURCE_STATUS_ABSENT
    assert result.supplement_required is True


def test_run_cascade_source_check_reports_partial(tmp_path):
    _write_transcript_registry(tmp_path, {"slurp:devel:000000"})
    ledger_text = _LEDGER_HEADER + _ledger_row("SAEA-PROBE-pkey2-338", "yes")
    expected = frozenset({"slurp:devel:000000", "slurp:devel:000001"})
    result = f.run_cascade_source_check(
        data_root=tmp_path, ledger_text=ledger_text, expected_sample_ids=expected, expected_registry_sha256=None
    )
    assert result.status == f.CASCADE_SOURCE_STATUS_PARTIAL
    assert result.supplement_required is True


def test_run_cascade_source_check_refuses_before_consumed_row_is_verified(tmp_path):
    _write_transcript_registry(tmp_path, {"slurp:devel:000000"})
    ledger_text = _LEDGER_HEADER + _ledger_row("SAEA-PROBE-pkey2-338", "no")
    with pytest.raises(f.Pemb3mFlightError, match="consumed"):
        f.run_cascade_source_check(
            data_root=tmp_path, ledger_text=ledger_text, expected_sample_ids=frozenset({"slurp:devel:000000"})
        )


def test_run_cascade_source_check_refuses_a_drifted_registry_hash(tmp_path):
    registry_path = tmp_path / f.PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({"slurp:devel:000000": {"text": "x", "sha256": "0" * 64}}), encoding="utf-8")
    ledger_text = _LEDGER_HEADER + _ledger_row("SAEA-PROBE-pkey2-338", "yes")
    with pytest.raises(f.Pemb3mFlightError, match="sha256"):
        f.run_cascade_source_check(
            data_root=tmp_path, ledger_text=ledger_text, expected_sample_ids=frozenset({"slurp:devel:000000"})
        )


def test_run_cascade_source_check_against_the_real_consumed_artifact(tmp_path, monkeypatch):
    import os

    data_root_env = os.environ.get("SPEECHRL_DATA_DIR")
    if not data_root_env:
        pytest.skip("SPEECHRL_DATA_DIR not set in this environment")
    repo_root = REPO_ROOT
    ledger_text = (repo_root / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_sample_manifest

    manifest = load_pslu_sample_manifest(repo_root / "configs/probes/g0-binding/pslu-sample-devel-n60.json")
    expected_ids = frozenset(manifest.sample_ids)
    result = f.run_cascade_source_check(data_root=Path(data_root_env), ledger_text=ledger_text, expected_sample_ids=expected_ids)
    assert result.status == f.CASCADE_SOURCE_STATUS_COMPLETE
    assert result.registry_sha256 == f.PKEY2_338_TRANSCRIPT_REGISTRY_SHA256


# ---------------------------------------------------------------------------
# CASCADE-T0 supplement.
# ---------------------------------------------------------------------------


class _StubCoreClient:
    def __init__(self, response_text: str = "the transcript"):
        self.response_text = response_text
        self.calls = []

    def complete(self, messages, *, decoding_params=None):
        self.calls.append((messages, decoding_params))
        return self.response_text


def test_run_cascade_t0_supplement_flight_happy_path(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = _StubCoreClient()
    registry = f.run_cascade_t0_supplement_flight(core_client=client, samples=samples)
    assert set(registry) == {s.sample_id for s in samples}
    assert len(client.calls) == len(samples)
    for record in registry.values():
        assert record.text == "the transcript"


def test_run_cascade_t0_supplement_flight_reuses_pkey_t0_construction_verbatim(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = _StubCoreClient()
    f.run_cascade_t0_supplement_flight(core_client=client, samples=samples)
    expected_first_messages = assemble_t0_messages(samples[0])
    assert client.calls[0][0] == expected_first_messages


def test_run_cascade_t0_supplement_flight_refuses_over_max_contacts(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = _StubCoreClient()
    with pytest.raises(f.Pemb3mFlightError, match="exceeds the registered ceiling"):
        f.run_cascade_t0_supplement_flight(core_client=client, samples=samples, max_contacts=1)


def test_run_cascade_t0_supplement_flight_refuses_empty_samples():
    with pytest.raises(f.Pemb3mFlightError, match="at least one"):
        f.run_cascade_t0_supplement_flight(core_client=_StubCoreClient(), samples=())


def test_run_cascade_t0_supplement_flight_refuses_duplicate_sample_ids(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    with pytest.raises(f.Pemb3mFlightError, match="duplicate"):
        f.run_cascade_t0_supplement_flight(core_client=_StubCoreClient(), samples=[samples[0], samples[0]])


# ---------------------------------------------------------------------------
# Pre-flight gate (d) -- encode-only.
# ---------------------------------------------------------------------------


def test_run_encode_only_preflight_gate_passes():
    report = f.run_encode_only_preflight_gate()
    assert "speech_aware_evidence_acquisition.rails.probes.pemb3m_flight" in report.checked_modules


# ---------------------------------------------------------------------------
# M4 repeat-call determinism gate.
# ---------------------------------------------------------------------------


def test_run_m4_repeat_call_gate_produces_two_contacts():
    client = MockEmbeddingClient(expected_dim=1024, vector_source=lambda kind, cid: deterministic_unit_vector("fixed", dims=1024))
    vector_a, vector_b = f.run_m4_repeat_call_gate(client=client, text="same text")
    assert vector_a.contact_id == "m4-jitter-a"
    assert vector_b.contact_id == "m4-jitter-b"
    assert len(client.calls) == 2
    assert vector_a.values == vector_b.values  # deterministic mock: perfect repeat


# ---------------------------------------------------------------------------
# run_m1_arm_flight.
# ---------------------------------------------------------------------------


def test_run_m1_arm_flight_happy_path(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    labels = ("email", "iot")
    client = MockEmbeddingClient()
    summary = f.run_m1_arm_flight(
        client=client,
        samples=samples,
        canonical_labels=labels,
        split_identity_hash=f.EXPECTED_SPLIT_IDENTITY_HASH,
        data_root=slurp_world.data_root,
        expected_query_n=len(samples),
        expected_label_n=2,
    )
    assert summary.run_id == f.arm_run_id(f.ARM_M1_ID)
    assert summary.arm_id == f.ARM_M1_ID
    assert summary.embedding_dim == EMBEDDING_DIM
    assert len(summary.query_vectors) == len(samples)
    assert len(summary.label_vectors) == 2
    assert client.marker_verified is True


def test_run_m1_arm_flight_rejects_wrong_split_identity_hash(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(PembFlightError, match="split_identity_hash"):
        f.run_m1_arm_flight(
            client=client,
            samples=samples,
            canonical_labels=("email", "iot"),
            split_identity_hash="not-the-pin",
            data_root=slurp_world.data_root,
            expected_query_n=len(samples),
            expected_label_n=2,
        )
    assert client.calls == []


def test_run_m1_arm_flight_rejects_duplicate_labels(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    with pytest.raises(f.Pemb3mFlightError, match="duplicate canonical label"):
        f.run_m1_arm_flight(
            client=MockEmbeddingClient(),
            samples=samples,
            canonical_labels=("iot", "iot"),
            split_identity_hash=f.EXPECTED_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_query_n=len(samples),
            expected_label_n=2,
        )


def test_run_m1_arm_flight_rejects_wrong_query_count(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    with pytest.raises(f.Pemb3mFlightError, match="query sample"):
        f.run_m1_arm_flight(
            client=MockEmbeddingClient(),
            samples=samples,
            canonical_labels=("email", "iot"),
            split_identity_hash=f.EXPECTED_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_query_n=999,
            expected_label_n=2,
        )


# ---------------------------------------------------------------------------
# run_local_encoder_arm_flight (M2/M3).
# ---------------------------------------------------------------------------


def test_run_local_encoder_arm_flight_happy_path_m2(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockLocalEncoderClient(expected_dim=GLAP_EMBEDDING_DIM)
    summary = f.run_local_encoder_arm_flight(
        arm_id=f.ARM_M2_ID,
        client=client,
        samples=samples,
        canonical_labels=("email", "iot"),
        split_identity_hash=f.EXPECTED_SPLIT_IDENTITY_HASH,
        data_root=slurp_world.data_root,
        expected_query_n=len(samples),
        expected_label_n=2,
    )
    assert summary.arm_id == f.ARM_M2_ID
    assert summary.embedding_dim == GLAP_EMBEDDING_DIM
    assert len(summary.query_vectors) == len(samples)


def test_run_local_encoder_arm_flight_happy_path_m3(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockLocalEncoderClient(expected_dim=CLSP_EMBEDDING_DIM)
    summary = f.run_local_encoder_arm_flight(
        arm_id=f.ARM_M3_ID,
        client=client,
        samples=samples,
        canonical_labels=("email", "iot"),
        split_identity_hash=f.EXPECTED_SPLIT_IDENTITY_HASH,
        data_root=slurp_world.data_root,
        expected_query_n=len(samples),
        expected_label_n=2,
    )
    assert summary.embedding_dim == CLSP_EMBEDDING_DIM


def test_run_local_encoder_arm_flight_refuses_a_non_control_arm_id(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    with pytest.raises(f.Pemb3mFlightError, match="must be one of"):
        f.run_local_encoder_arm_flight(
            arm_id=f.ARM_M1_ID,
            client=MockLocalEncoderClient(),
            samples=samples,
            canonical_labels=("email", "iot"),
            split_identity_hash=f.EXPECTED_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_query_n=len(samples),
            expected_label_n=2,
        )


# ---------------------------------------------------------------------------
# run_m4_arm_flight.
# ---------------------------------------------------------------------------


def test_run_m4_arm_flight_happy_path(slurp_world):
    from speech_aware_evidence_acquisition.rails.probes.pkey_flight import build_transcript_record

    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    transcript_registry = {s.sample_id: build_transcript_record(s.sample_id, f"transcript {s.sample_id}") for s in samples}
    client = MockEmbeddingClient(expected_dim=1024)
    summary = f.run_m4_arm_flight(
        client=client,
        transcript_registry=transcript_registry,
        canonical_labels=("email", "iot"),
        split_identity_hash=f.EXPECTED_SPLIT_IDENTITY_HASH,
        expected_query_n=len(samples),
        expected_label_n=2,
    )
    assert summary.arm_id == f.ARM_M4_ID
    assert summary.embedding_dim == 1024
    assert len(summary.query_vectors) == len(samples)
    # M4 never touches audio -- every recorded call is "text".
    assert all(kind == "text" for kind, _cid in client.calls)


def test_run_m4_arm_flight_refuses_wrong_transcript_registry_count(slurp_world):
    from speech_aware_evidence_acquisition.rails.probes.pkey_flight import build_transcript_record

    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    partial_registry = {samples[0].sample_id: build_transcript_record(samples[0].sample_id, "x")}
    with pytest.raises(f.Pemb3mFlightError, match="T0 transcript"):
        f.run_m4_arm_flight(
            client=MockEmbeddingClient(expected_dim=1024),
            transcript_registry=partial_registry,
            canonical_labels=("email", "iot"),
            split_identity_hash=f.EXPECTED_SPLIT_IDENTITY_HASH,
            expected_query_n=len(samples),
            expected_label_n=2,
        )


def test_run_m4_arm_flight_accepts_jitter_vectors(slurp_world):
    from speech_aware_evidence_acquisition.rails.probes.pkey_flight import build_transcript_record

    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    transcript_registry = {s.sample_id: build_transcript_record(s.sample_id, "t") for s in samples}
    client = MockEmbeddingClient(expected_dim=1024)
    jitter_client = MockEmbeddingClient(expected_dim=1024, vector_source=lambda kind, cid: deterministic_unit_vector("j", dims=1024))
    jitter_a, jitter_b = f.run_m4_repeat_call_gate(client=jitter_client, text="x")
    summary = f.run_m4_arm_flight(
        client=client,
        transcript_registry=transcript_registry,
        canonical_labels=("email", "iot"),
        split_identity_hash=f.EXPECTED_SPLIT_IDENTITY_HASH,
        jitter_vectors=(jitter_a, jitter_b),
        expected_query_n=len(samples),
        expected_label_n=2,
    )
    assert len(summary.jitter_vectors) == 2


def test_run_m4_arm_flight_refuses_a_single_jitter_vector(slurp_world):
    from speech_aware_evidence_acquisition.rails.probes.pkey_flight import build_transcript_record

    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    transcript_registry = {s.sample_id: build_transcript_record(s.sample_id, "t") for s in samples}
    lone_client = MockEmbeddingClient(expected_dim=1024)
    lone_client.verify_media_marker()
    lone_vector = lone_client.embed_text(contact_id="lone", text="x")
    with pytest.raises(f.Pemb3mFlightError, match="jitter"):
        f.run_m4_arm_flight(
            client=MockEmbeddingClient(expected_dim=1024),
            transcript_registry=transcript_registry,
            canonical_labels=("email", "iot"),
            split_identity_hash=f.EXPECTED_SPLIT_IDENTITY_HASH,
            jitter_vectors=(lone_vector,),
            expected_query_n=len(samples),
            expected_label_n=2,
        )


# ---------------------------------------------------------------------------
# Manifest persistence -- write/load round trip, dim-generic, side-keyed.
# ---------------------------------------------------------------------------


def _tiny_summary(arm_id: str, dim: int) -> f.Pemb3mArmSummary:
    from speech_aware_evidence_acquisition.rails.embedding_client import EmbeddingVector

    def vec(cid, kind):
        values = tuple([1.0] + [0.0] * (dim - 1))
        return EmbeddingVector(contact_id=cid, kind=kind, values=values)

    return f.Pemb3mArmSummary(
        run_id=f.arm_run_id(arm_id),
        arm_id=arm_id,
        embedding_dim=dim,
        query_vectors=(vec("q1", "audio"), vec("q2", "audio")),
        label_vectors=(vec("l1", "text"),),
    )


def test_write_then_load_manifest_round_trips(tmp_path):
    summary = _tiny_summary(f.ARM_M3_ID, CLSP_EMBEDDING_DIM)
    manifest_path = f.write_pemb3m_arm_manifest(tmp_path, summary)
    assert manifest_path.is_file()
    loaded = f.load_pemb3m_arm_manifest(tmp_path, f.ARM_M3_ID)
    assert loaded.dims == CLSP_EMBEDDING_DIM
    assert set(loaded.query) == {"q1", "q2"}
    assert set(loaded.label) == {"l1"}
    assert loaded.jitter == {}


def test_write_then_load_manifest_round_trips_jitter_side(tmp_path):
    from speech_aware_evidence_acquisition.rails.embedding_client import EmbeddingVector

    dim = 4
    values_a = (1.0, 0.0, 0.0, 0.0)
    values_b = (0.0, 1.0, 0.0, 0.0)
    summary = f.Pemb3mArmSummary(
        run_id=f.arm_run_id(f.ARM_M4_ID),
        arm_id=f.ARM_M4_ID,
        embedding_dim=dim,
        query_vectors=(EmbeddingVector(contact_id="q1", kind="text", values=values_a),),
        label_vectors=(EmbeddingVector(contact_id="l1", kind="text", values=values_b),),
        jitter_vectors=(
            EmbeddingVector(contact_id="m4-jitter-a", kind="text", values=values_a),
            EmbeddingVector(contact_id="m4-jitter-b", kind="text", values=values_a),
        ),
    )
    f.write_pemb3m_arm_manifest(tmp_path, summary)
    loaded = f.load_pemb3m_arm_manifest(tmp_path, f.ARM_M4_ID)
    assert set(loaded.jitter) == {"m4-jitter-a", "m4-jitter-b"}


def test_load_manifest_refuses_missing_file(tmp_path):
    with pytest.raises(f.Pemb3mFlightError, match="missing"):
        f.load_pemb3m_arm_manifest(tmp_path, f.ARM_M1_ID)


def test_load_manifest_refuses_a_tampered_vector_file(tmp_path):
    summary = _tiny_summary(f.ARM_M2_ID, GLAP_EMBEDDING_DIM)
    f.write_pemb3m_arm_manifest(tmp_path, summary)
    # Corrupt one on-disk vector file after writing.
    vector_path = next((tmp_path / "derived" / "embeddings" / f.arm_run_id(f.ARM_M2_ID) / "query").glob("*.npy"))
    vector_path.write_bytes(b"corrupted")
    with pytest.raises(f.Pemb3mFlightError, match="sha256 mismatch"):
        f.load_pemb3m_arm_manifest(tmp_path, f.ARM_M2_ID)


def test_write_manifest_refuses_more_than_two_jitter_vectors():
    from speech_aware_evidence_acquisition.rails.embedding_client import EmbeddingVector

    def vec(cid):
        return EmbeddingVector(contact_id=cid, kind="text", values=(1.0,))

    summary = f.Pemb3mArmSummary(
        run_id=f.arm_run_id(f.ARM_M4_ID),
        arm_id=f.ARM_M4_ID,
        embedding_dim=1,
        query_vectors=(vec("q1"),),
        label_vectors=(vec("l1"),),
        jitter_vectors=(vec("j1"), vec("j2"), vec("j3")),
    )
    with pytest.raises(f.Pemb3mFlightError, match="jitter"):
        f._validate_arm_summary(summary, expected_query_n=1, expected_label_n=1)


# ---------------------------------------------------------------------------
# is_arm_complete / run_pemb3m_sweep_flight -- arm-level idempotence.
# ---------------------------------------------------------------------------


def test_is_arm_complete_false_before_any_write(tmp_path):
    assert f.is_arm_complete(tmp_path, f.ARM_M1_ID) is False


def test_is_arm_complete_true_after_write(tmp_path):
    f.write_pemb3m_arm_manifest(tmp_path, _tiny_summary(f.ARM_M1_ID, 4))
    assert f.is_arm_complete(tmp_path, f.ARM_M1_ID) is True


def test_run_pemb3m_sweep_flight_refuses_unknown_arm_id(tmp_path):
    with pytest.raises(f.Pemb3mFlightError, match="unknown arm"):
        f.run_pemb3m_sweep_flight(root=tmp_path, arm_runners={"not-real": lambda: None})


def test_run_pemb3m_sweep_flight_never_respawns_a_completed_arm(tmp_path):
    calls = {"n": 0}

    def runner():
        calls["n"] += 1
        return _tiny_summary(f.ARM_M1_ID, 4)

    results1 = f.run_pemb3m_sweep_flight(root=tmp_path, arm_runners={f.ARM_M1_ID: runner})
    assert calls["n"] == 1
    assert set(results1[f.ARM_M1_ID].query) == {"q1", "q2"}

    results2 = f.run_pemb3m_sweep_flight(root=tmp_path, arm_runners={f.ARM_M1_ID: runner})
    assert calls["n"] == 1  # runner NEVER invoked a second time
    assert set(results2[f.ARM_M1_ID].query) == {"q1", "q2"}


def test_run_pemb3m_sweep_flight_refuses_a_runner_returning_the_wrong_arm(tmp_path):
    def runner():
        return _tiny_summary(f.ARM_M2_ID, 4)

    with pytest.raises(f.Pemb3mFlightError, match="returned a summary"):
        f.run_pemb3m_sweep_flight(root=tmp_path, arm_runners={f.ARM_M1_ID: runner})
