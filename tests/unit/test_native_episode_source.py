"""Source assembly checks over real in-process native traces.

Bundle internals have their own verifier suite. These tests substitute its
already-verified return value while exercising real config/commit/phase joins.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import native_episode_source as module
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness
from test_rails_frozen_core_client import _plan


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True))
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture()
def source(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    names = dict(model="model", dataset="dataset", baseline="baseline", experiment="experiment")
    native = json.loads((
        Path(__file__).parents[2]
        / "configs/baseline/slurp-native-dual-store-train-fold-b-held-v1.json"
    ).read_text())["native_episode"]
    values = {
        "policy": "phase-native-review-revise-v1",
        "arm": "speech-feature-query-native-tools",
        "native_episode": native,
        "scorers": [],
    }
    for kind, name in names.items():
        _write(repo / "configs" / kind / f"{name}.json", values if kind == "baseline" else {})
    for command in (
        ["git", "init", "-q"],
        ["git", "add", "."],
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "commit", "-qm", "Bind the synthetic native source"],
    ):
        subprocess.run(command, cwd=repo, check=True, capture_output=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    composed = compose(repo, **names)
    ids = ("s2", "s1")
    split_sha = split_identity_hash(prefixed("fake-carrier", ids))
    plan = _plan(
        split_identity_hash=split_sha,
        protocol_hash=protocol_hash(composed.config_hash, values["arm"], split_sha),
        planned_model_calls=22,
    ).validate()
    harness = _ActualEpisodeHarness(
        tmp_path / "episode", sample_count=2, max_revisions=1, max_contacts=11,
        planner_actions=("REVISE", "ACCEPT"), sample_ids=ids, execution_plan=plan,
    )
    harness.program = default_phase_program(values["policy"])
    harness.config = load_native_episode_config(values, harness.program)
    try:
        summary = harness.run()
    finally:
        harness.close()
    phases = [result.as_json() for result in summary.results]
    outputs = tuple({
        "sample_id": row["sample_id"], "text": row["final_response_text"],
        "native_episode_receipt": row["native_episode_receipt"],
    } for row in phases)
    run_dir = tmp_path / "sealed"
    manifest_path = run_dir / "manifest.json"
    manifest = {
        "status": "COMPLETED", "study_commit": commit,
        "config": {"fragments": names, "config_hash": composed.config_hash},
        "arm": values["arm"], "scorers": [], "plan": asdict(plan),
    }
    manifest_sha = _write(manifest_path, manifest)
    phase_path = run_dir / "phases.json"
    phase_document = {
        "schema": "saea-flight-phase-summaries-v1", "run_id": plan.run_id,
        "attempt_id": plan.attempt_id, "policy": values["policy"],
        "phases": [{"run_id": plan.run_id, "protocol_hash": plan.protocol_hash,
                    "controller_policy_id": values["policy"], "results": phases}],
    }
    phase_sha = _write(phase_path, phase_document)
    bundle = VerifiedBundle(
        manifest_path, manifest, None, outputs,
        {key: payload for _axis, key, payload in harness.trace.records},
        frozenset(ids), "FINALIZED",
    )
    world = {
        "bundle": bundle, "phase_document": phase_document,
        "args": dict(manifest_path=manifest_path, expected_manifest_sha256=manifest_sha,
                     phase_artifact_path=phase_path, expected_phase_sha256=phase_sha,
                     repo_root=repo),
    }
    monkeypatch.setattr(module, "verify_bundle", lambda _path: world["bundle"])
    return world


def test_exact_native_source_preserves_actual_order(source):
    verified = module.verify_native_episode_source(**source["args"])
    assert verified.sample_ids == ("s2", "s1")
    assert verified.diagnostics["sample_count"] == 2
    assert verified.composed.values["policy"] == "phase-native-review-revise-v1"


@pytest.mark.parametrize("mutation", ("order", "foreign_attempt", "extra_summary"))
def test_rehashed_phase_substitution_is_refused(source, mutation):
    document = source["phase_document"]
    if mutation == "order":
        document["phases"][0]["results"].reverse()
    elif mutation == "foreign_attempt":
        document["attempt_id"] = "foreign-attempt"
    else:
        document["phases"].append(document["phases"][0])
    source["args"]["expected_phase_sha256"] = _write(
        source["args"]["phase_artifact_path"], document
    )
    with pytest.raises(module.NativeEpisodeSourceError):
        module.verify_native_episode_source(**source["args"])


@pytest.mark.parametrize("mutation", ("config_hash", "study_commit", "opened"))
def test_valid_bundle_cannot_substitute_source_configuration(source, mutation):
    if mutation == "opened":
        source["bundle"] = replace(source["bundle"], attempt_state="OPENED")
    else:
        manifest = source["bundle"].manifest
        if mutation == "config_hash":
            manifest["config"]["config_hash"] = "0" * 64
        else:
            manifest["study_commit"] = "0" * 40
        source["args"]["expected_manifest_sha256"] = _write(
            source["args"]["manifest_path"], manifest
        )
    with pytest.raises(module.NativeEpisodeSourceError):
        module.verify_native_episode_source(**source["args"])
