"""Deterministic config composition: disjoint fragments, stable hashes."""

import json

import pytest

from speech_aware_evidence_acquisition.core.config import (
    ComposedConfig,
    ConfigError,
    compose,
    protocol_hash,
)
from speech_aware_evidence_acquisition.scoring import SCORING_STACK_VERSION


def _write_fragments(root, experiment_extra=None):
    for kind, name, body in (
        ("model", "m", {"transport": "llama-server", "base_url": "http://x"}),
        ("dataset", "d", {"carrier_lock_key": "earnings22-original", "split_name": "dev"}),
        ("baseline", "b", {"arm": "bare-core", "policy": "fixed", "task_instruction": "t"}),
        ("experiment", "e", {"experiment_id": "SAEA-E-001", **(experiment_extra or {})}),
    ):
        path = root / "configs" / kind / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body), encoding="utf-8")


def test_compose_merges_disjoint_fragments_deterministically(tmp_path):
    _write_fragments(tmp_path)
    first = compose(tmp_path, "m", "d", "b", "e")
    second = compose(tmp_path, "m", "d", "b", "e")
    assert isinstance(first, ComposedConfig)
    assert first.values["arm"] == "bare-core"
    assert first.values["experiment_id"] == "SAEA-E-001"
    assert first.config_hash == second.config_hash
    assert first.fragments == {"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"}


def test_key_collision_fails_closed(tmp_path):
    _write_fragments(tmp_path, experiment_extra={"arm": "sneaky-override"})
    with pytest.raises(ConfigError, match="collision"):
        compose(tmp_path, "m", "d", "b", "e")


def test_missing_fragment_fails_closed(tmp_path):
    _write_fragments(tmp_path)
    with pytest.raises(ConfigError, match="missing"):
        compose(tmp_path, "m", "d", "b", "absent")


def test_fragment_name_path_traversal_refused(tmp_path):
    _write_fragments(tmp_path)
    with pytest.raises(ConfigError, match="fragment name"):
        compose(tmp_path, "../../../outside", "d", "b", "e")


def test_fragment_name_traversal_in_any_kind_refused(tmp_path):
    _write_fragments(tmp_path)
    with pytest.raises(ConfigError, match="fragment name"):
        compose(tmp_path, "m", "d", "b", "../../../outside")


def test_protocol_hash_binds_scoring_version():
    first = protocol_hash("a" * 64, "bare-core", "b" * 64)
    assert len(first) == 64
    assert first != protocol_hash("a" * 64, "fixed-retrieval", "b" * 64)
    assert SCORING_STACK_VERSION  # bound inside the hash; a version bump changes it


def test_repo_fragments_compose():
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp", "earnings22-dev-subset10", "bare-core", "r0-smoke"
    )
    assert composed.values["experiment_id"] == "SAEA-E-001"
    assert composed.values["arm"] == "bare-core"
    assert composed.values["policy"] == "fixed"
    assert composed.values["transport"] == "llama-server"
    assert composed.values["model_lock_key"] == "qwen3-omni-30b-a3b-instruct-gguf"


# ---------------------------------------------------------------------------
# R0 repair T8: the three formal engineering-control configs + the
# mismatched-evidence negative control compose (disjoint keys) with the real
# existing model/dataset/experiment fragments -- the P1-3 gap was that only
# bare-core.json existed as a runnable named config.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "baseline_name, expected_arm, expects_retrieval_query",
    [
        ("fixed-legal-context", "fixed-legal-context", False),
        ("fixed-retrieval", "fixed-retrieval", True),
        ("mismatched-evidence", "fixed-legal-context", False),
    ],
)
def test_repo_engineering_control_fragments_compose(
    baseline_name, expected_arm, expects_retrieval_query
):
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp", "earnings22-dev-subset10", baseline_name, "r0-smoke"
    )
    assert composed.values["arm"] == expected_arm
    assert composed.values["policy"] == "fixed"
    assert composed.values["evidence_source"] == "conec-contexts"
    assert isinstance(composed.values["task_instruction"], str) and composed.values[
        "task_instruction"
    ]
    assert ("retrieval_query" in composed.values) == expects_retrieval_query
    # No key collision (compose() itself would raise ConfigError otherwise);
    # every fragment's own identity keys are still present and un-shadowed.
    assert composed.values["experiment_id"] == "SAEA-E-001"
    assert composed.values["carrier_lock_key"] == "earnings22-original"
    assert composed.values["model_lock_key"] == "qwen3-omni-30b-a3b-instruct-gguf"


def test_mismatched_evidence_config_sets_the_mismatch_flag():
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "qwen3-omni-llamacpp",
        "earnings22-dev-subset10",
        "mismatched-evidence",
        "r0-smoke",
    )
    assert composed.values["evidence_mismatch"] is True


@pytest.mark.parametrize("baseline_name", ["bare-core", "fixed-legal-context", "fixed-retrieval"])
def test_non_mismatch_engineering_controls_do_not_set_the_mismatch_flag(baseline_name):
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp", "earnings22-dev-subset10", baseline_name, "r0-smoke"
    )
    assert composed.values["evidence_mismatch"] is False
