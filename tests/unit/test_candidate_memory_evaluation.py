"""Candidate lineage joins over connected real in-process source/runtime traces.

The native source assembly boundary is substituted here and tested separately;
materialization, candidate loading, QueryState replay and native lineage are real.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from test_group_relative_feedback import source_pair as _source_pair
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_provisional_candidate_materialization import _connected_candidate_native_source

from speech_aware_evidence_acquisition.analysis import candidate_memory_evaluation as module
from speech_aware_evidence_acquisition.analysis.native_episode_source import VerifiedNativeEpisodeSource
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.config import ComposedConfig

pytest_plugins = ("test_bundle",)
source_pair = _source_pair


def _inputs(world, monkeypatch):
    manifest = {"study_commit": "a" * 40}
    ids = world["world"]["evaluation_ids"]
    bundle = VerifiedBundle(
        Path("/synthetic/manifest.json"), manifest, None, tuple(world["canonical"]),
        world["traces"], frozenset(ids), "FINALIZED",
    )
    source = VerifiedNativeEpisodeSource(
        bundle, ComposedConfig(world["values"], "b" * 64, {}),
        world["plan"], ids, world["phases"],
        {row["sample_id"]: row for row in world["canonical"]}, "c" * 64, {},
    )
    monkeypatch.setattr(module, "verify_native_episode_source", lambda **_kwargs: source)
    return dict(
        manifest_path=bundle.manifest_path, expected_manifest_sha256="d" * 64,
        phase_artifact_path=Path("/synthetic/phases.json"), expected_phase_sha256="c" * 64,
        repo_root=world["world"]["repo_root"], data_root=world["data_root"],
    )


@pytest.mark.parametrize("memory_call,empty_pack", ((True, False), (True, True), (False, False)))
def test_actual_candidate_selection_exposure_and_no_call_are_distinct(
    source_pair, synthetic_world, tmp_path, monkeypatch, memory_call, empty_pack
):
    world = _connected_candidate_native_source(
        source_pair, synthetic_world, tmp_path, monkeypatch,
        memory_call=memory_call, empty_pack=empty_pack,
    )
    report = module.verify_candidate_memory_evaluation_source(**_inputs(world, monkeypatch))
    assert report["source_verified"] is True
    assert report["admission"] == "none"
    assert len(report["successful_memory_calls"]) == (2 if memory_call else 0)
    assert len(report["samples_without_successful_memory_call"]) == (0 if memory_call else 2)
    for call in report["successful_memory_calls"]:
        assert call["selection_empty"] is empty_pack
        assert call["selected_record_sha256s"] == ([] if empty_pack else [
            world["memory"].records[0].record_sha256
        ])
        assert call["exposed"] is True


@pytest.mark.parametrize("mutation", ("artifact", "condition", "extra"))
def test_internal_lineage_cannot_be_rebound_after_generic_exposure_verification(
    source_pair, synthetic_world, tmp_path, monkeypatch, mutation
):
    world = _connected_candidate_native_source(
        source_pair, synthetic_world, tmp_path, monkeypatch
    )
    events = world["traces"]
    key = next(key for key, row in events.items() if "use_internal_memory_lineage" in row)
    lineage = events[key]["use_internal_memory_lineage"]
    if mutation == "artifact":
        lineage["candidate_artifact_sha256"] = "0" * 64
    elif mutation == "condition":
        lineage["condition_tags"] = ["state:knowledge-present"]
    else:
        events["foreign-lineage"] = {"use_internal_memory_lineage": copy.deepcopy(lineage)}
    with pytest.raises(module.CandidateMemoryEvaluationError):
        module.verify_candidate_memory_evaluation_source(**_inputs(world, monkeypatch))
