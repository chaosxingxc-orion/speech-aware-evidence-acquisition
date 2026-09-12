"""Prepared recall preserves live state-dependent ranking and fusion."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from test_phase_supply import (
    _fragment,
    _program,
    _segment_source,
    _snapshot,
    _source,
    _write_segment_vectors,
    _write_vectors,
)
from test_prepared_phase_supply import setup_runtime
from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.rails import (
    phase_supply as ps,
    knowledge_provider as kp,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState


def world(tmp_path):
    runtime, binding, _ = setup_runtime(tmp_path)
    qs = _write_vectors(tmp_path / "q.jsonl", [("s1", {"content": [1.0, 0.0]})])
    fs = _write_vectors(
        tmp_path / "f.jsonl",
        [
            ("facet:content:u1", {"content": [1.0, 0.0]}),
            ("facet:content:u2", {"content": [0.5, 0.5]}),
        ],
    )
    values = _fragment(_source("q.jsonl", qs), _source("f.jsonl", fs), tau=0.0)
    runtime._composed.values.update(values)
    runtime._composed.values["policy"] = _program().program_id
    specs = ps.load_phase_supply_specs(runtime._composed.values, _program())
    binding["knowledge_snapshot"] = _snapshot()
    binding["supply_specs"] = specs
    return runtime, binding, specs


def test_prepare_load_cache_hit_and_actual_live_state_equivalence(
    tmp_path, monkeypatch
):
    runtime, binding, specs = world(tmp_path)
    spec = specs["evidence"]
    receipt = runtime.prepare_phase_recall(tmp_path / "recall.json", phase="evidence")
    same = runtime.prepare_phase_recall(tmp_path / "recall.json", phase="evidence")
    assert same["sha256"] == receipt["sha256"]
    pin = {"relpath": "recall.json", "sha256": receipt["sha256"]}
    runtime._composed.values["prepared_phase_recall"] = {"evidence": pin}
    rows = runtime._load_phase_recall(pin, binding, spec, "d" * 64)
    snapshot = binding["knowledge_snapshot"]
    plain = ps.build_supply_for_phase(
        specs,
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=tmp_path,
    )
    cached = ps.build_supply_for_phase(
        specs,
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=tmp_path,
        prepared_recall_by_phase={"evidence": rows},
    )
    state = QueryState("q", "s1", "p1", "b" * 64, "d" * 64)
    states = [
        state,
        replace(
            state,
            query_id="after-direct",
            loop_step=1,
            retrieved_value_ids=("value:u1",),
        ),
    ]
    expected = [
        plain("evidence", SimpleNamespace(query_state=s, sample_id="s1"))
        for s in states
    ]
    monkeypatch.setattr(
        kp,
        "multidim_recall",
        lambda *a, **k: pytest.fail("cached dispatch recomputed cosine recall"),
    )
    actual = [
        cached("evidence", SimpleNamespace(query_state=s, sample_id="s1"))
        for s in states
    ]
    assert actual == expected
    assert actual[0] != actual[1]


@pytest.mark.parametrize("drift", ["config", "split", "packet", "snapshot", "roster"])
def test_prepared_recall_refuses_bound_input_drift(tmp_path, drift):
    runtime, binding, specs = world(tmp_path)
    receipt = runtime.prepare_phase_recall(tmp_path / "recall.json", phase="evidence")
    pin = {"relpath": "recall.json", "sha256": receipt["sha256"]}
    identity = "d" * 64
    if drift == "config":
        runtime._composed.values["k"] = 99
    elif drift == "split":
        identity = "e" * 64
    elif drift == "packet":
        binding["speech_packet_bindings"]["s1"]["sha256"] = "e" * 64
    elif drift == "snapshot":
        binding["knowledge_snapshot"] = replace(
            binding["knowledge_snapshot"], snapshot_id="changed"
        )
    else:
        binding["speech_packet_bindings"]["s2"] = binding["speech_packet_bindings"][
            "s1"
        ]
    with pytest.raises(PreparationError):
        runtime._load_phase_recall(pin, binding, specs["evidence"], identity)


def test_prepared_recall_refuses_unknown_phase_before_computation(tmp_path):
    runtime, _, _ = world(tmp_path)
    with pytest.raises(PreparationError, match="no configured phase supply"):
        runtime.prepare_phase_recall(tmp_path / "x.json", phase="direct")


def test_prepared_recall_refuses_injected_provider(tmp_path):
    runtime, binding, specs = world(tmp_path)
    with pytest.raises(ps.PhaseSupplyError, match="shared kb-facet"):
        ps.build_supply_for_phase(
            specs,
            snapshot=binding["knowledge_snapshot"],
            snapshot_sha256="a" * 64,
            data_root=tmp_path,
            provider_for_phase=lambda _: object(),
            prepared_recall_by_phase={"evidence": {"s1": {}}},
        )


def test_cli_recall_mode_is_a_registered_campaign_stage():
    from speech_aware_evidence_acquisition.core.flight.campaign import EXECUTION_STAGES

    assert "prepare-phase-recall" in EXECUTION_STAGES


def test_parallel_recall_matches_serial_exactly_and_releases_state():
    snapshot = _snapshot()
    queries = {"s1": {"content": (1.0, 0.0)}, "s2": {"content": (0.0, 1.0)}}
    facets = {
        "facet:content:u1": {"content": (1.0, 0.0)},
        "facet:content:u2": {"content": (0.0, 1.0)},
    }
    serial = ps.prepare_recall_rows(snapshot, queries, facets, 2)
    parallel = ps.prepare_recall_rows(snapshot, queries, facets, 2, workers=2)
    assert serial == parallel
    assert ps._RECALL_WORKER_STATE is None



def segmented_world(tmp_path):
    runtime, binding, _ = setup_runtime(tmp_path)
    query_sha = _write_segment_vectors(
        tmp_path / "segments.jsonl",
        [{
            "id": "s1",
            "audio_sha256": "a" * 64,
            "source_frames": 2,
            "source_sample_rate_hz": 16000,
            "segments": [{
                "id": "whole",
                "start_frame": 0,
                "end_frame": 2,
                "vectors": {"content": [1.0, 0.0]},
            }],
        }],
    )
    facet_sha = _write_vectors(
        tmp_path / "facets.jsonl",
        [
            ("facet:content:u1", {"content": [1.0, 0.0]}),
            ("facet:content:u2", {"content": [0.0, 1.0]}),
        ],
    )
    values = _fragment(
        _segment_source("segments.jsonl", query_sha),
        _source("facets.jsonl", facet_sha),
        tau=0.0,
    )
    values["policy"] = _program().program_id
    runtime._composed.values.update(values)
    runtime._prepare = lambda: (
        runtime._composed.values,
        "audio2tool",
        "DEV",
        "d" * 64,
    )
    binding["knowledge_snapshot"] = _snapshot()
    binding["speech_packet_bindings"] = {
        "s1": {"packet_id": "packet/s1", "sha256": "b" * 64}
    }
    binding["source_audio_bindings"] = {
        "s1": {
            "packet_id": "packet/s1",
            "packet_sha256": "b" * 64,
            "source_audio_sha256": "a" * 64,
        }
    }
    specs = ps.load_phase_supply_specs(runtime._composed.values, _program())
    binding["supply_specs"] = specs
    binding["supply_for_phase"] = ps.build_supply_for_phase(
        specs,
        snapshot=binding["knowledge_snapshot"],
        snapshot_sha256=binding["knowledge_snapshot"].content_hash(),
        data_root=tmp_path,
        source_audio_bindings=binding["source_audio_bindings"],
    )
    return runtime, binding, specs


def test_prepared_recall_binds_distinct_source_audio_and_packet_hashes(tmp_path):
    runtime, binding, specs = segmented_world(tmp_path)
    receipt = runtime.prepare_phase_recall(
        tmp_path / "segmented-recall.json", phase="evidence"
    )
    pin = {
        "relpath": "segmented-recall.json",
        "sha256": receipt["sha256"],
    }
    rows = runtime._load_phase_recall(
        pin, binding, specs["evidence"], "d" * 64
    )
    assert set(rows) == {"s1"}


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("source_audio_sha256", "c" * 64, "source audio"),
        ("packet_sha256", "c" * 64, "packet SHA"),
        ("packet_id", "packet/other", "packet id"),
    ],
)
def test_prepared_recall_refuses_segmented_source_binding_drift(
    tmp_path, field, value, message
):
    runtime, binding, _specs = segmented_world(tmp_path)
    binding["source_audio_bindings"]["s1"][field] = value
    with pytest.raises(PreparationError, match=message):
        runtime.prepare_phase_recall(
            tmp_path / "segmented-recall.json", phase="evidence"
        )
