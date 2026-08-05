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


# ---------------------------------------------------------------------------
# M-5 (external-threat-model review): a fragment with a duplicate top-level
# key silently took the LAST value under json.loads's default parsing --
# a human reading the fragment top-to-bottom sees the FIRST value, so the
# two readers disagree about what the fragment means. Fixed via an
# object_pairs_hook that raises at parse time, before compose()'s own
# (unrelated) cross-fragment collision check ever runs.
# ---------------------------------------------------------------------------


def test_duplicate_key_within_a_single_fragment_fails_closed(tmp_path):
    _write_fragments(tmp_path)
    path = tmp_path / "configs" / "baseline" / "b.json"
    # Hand-write raw JSON text with a duplicate "policy" key -- a dict
    # literal in Python cannot express this, so json.dumps() can't produce
    # it either; the attack is a hand-edited (or generated) JSON file.
    path.write_text(
        '{"arm": "bare-core", "policy": "fixed", "task_instruction": "t", '
        '"policy": "sneaky-second-value"}',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="duplicate key 'policy'"):
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
    # T8 fix (IMPORTANT 2): a real composed config must carry a non-empty
    # `scorers` list -- otherwise core.bundle.build_manifest bakes in [] and
    # core.scorers.score_bundle refuses every real run outright.
    assert composed.values["scorers"] == ["asr-wer", "cost"]


# ---------------------------------------------------------------------------
# R0 repair T8: the three formal engineering-control configs + the
# mismatched-evidence negative control compose (disjoint keys) with the real
# existing model/dataset/experiment fragments -- the P1-3 gap was that only
# bare-core.json existed as a runnable named config.
#
# T8 fix (IMPORTANT 1): compose() alone proves only "disjoint keys", never
# "this pairing can actually complete a run" -- evidence_source:
# "conec-contexts" only has data for earnings21-original samples
# (core/evidence.py::_conec_contexts hardcodes an earnings21/ relpath), so
# pairing an evidence-bearing baseline with the earnings22-dev-subset10
# dataset fragment composes cleanly but cannot run (see
# tests/unit/test_driver.py's *_real_four_fragment_composition tests, which
# use configs/dataset/earnings21-discovery.json instead and prove the run
# itself completes). The parametrized compose-only test below is kept
# against earnings22-dev-subset10 deliberately, to make that gap-between-
# compose-and-run explicit and regression-tested, not to imply runnability.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "baseline_name, expected_arm, expects_retrieval_query",
    [
        ("fixed-legal-context", "fixed-legal-context", False),
        ("fixed-retrieval", "fixed-retrieval", True),
        ("mismatched-evidence", "fixed-legal-context", False),
    ],
)
def test_repo_engineering_control_fragments_compose_disjoint_keys_only(
    baseline_name, expected_arm, expects_retrieval_query
):
    """Compose-only: proves disjoint keys and expected values. Does NOT prove
    the composition can complete a run -- see the module docstring above and
    tests/unit/test_driver.py for the real-run proof with the correct
    (earnings21-original-carrier) dataset fragment."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp", "earnings22-dev-subset10", baseline_name, "r0-smoke"
    )
    assert composed.values["arm"] == expected_arm
    assert composed.values["policy"] == "fixed"
    assert composed.values["evidence_source"] == "conec-contexts"
    assert composed.values["scorers"] == ["asr-wer", "cost"]
    assert isinstance(composed.values["task_instruction"], str) and composed.values[
        "task_instruction"
    ]
    assert ("retrieval_query" in composed.values) == expects_retrieval_query
    # No key collision (compose() itself would raise ConfigError otherwise);
    # every fragment's own identity keys are still present and un-shadowed.
    assert composed.values["experiment_id"] == "SAEA-E-001"
    assert composed.values["carrier_lock_key"] == "earnings22-original"
    assert composed.values["model_lock_key"] == "qwen3-omni-30b-a3b-instruct-gguf"


@pytest.mark.parametrize(
    "baseline_name, expected_arm",
    [
        ("fixed-legal-context", "fixed-legal-context"),
        ("fixed-retrieval", "fixed-retrieval"),
        ("mismatched-evidence", "fixed-legal-context"),
    ],
)
def test_repo_engineering_control_fragments_compose_with_the_carrier_their_evidence_needs(
    baseline_name, expected_arm
):
    """The CORRECT real pairing: configs/dataset/earnings21-discovery.json
    names carrier_lock_key earnings21-original, which is what
    evidence_source: conec-contexts actually has data for. See
    tests/unit/test_driver.py for the same pairing driven through a real
    run_experiment call."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp", "earnings21-discovery", baseline_name, "r0-smoke"
    )
    assert composed.values["arm"] == expected_arm
    assert composed.values["carrier_lock_key"] == "earnings21-original"
    assert composed.values["split_name"] == "discovery"
    assert composed.values["scorers"] == ["asr-wer", "cost"]


def test_mismatched_evidence_config_sets_the_mismatch_flag():
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "qwen3-omni-llamacpp",
        "earnings21-discovery",
        "mismatched-evidence",
        "r0-smoke",
    )
    assert composed.values["evidence_mismatch"] is True


@pytest.mark.parametrize("baseline_name", ["bare-core", "fixed-legal-context", "fixed-retrieval"])
def test_non_mismatch_engineering_controls_do_not_set_the_mismatch_flag(baseline_name):
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    dataset = "earnings22-dev-subset10" if baseline_name == "bare-core" else "earnings21-discovery"
    composed = compose(REPO_ROOT, "qwen3-omni-llamacpp", dataset, baseline_name, "r0-smoke")
    assert composed.values["evidence_mismatch"] is False
