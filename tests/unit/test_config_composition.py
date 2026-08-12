"""Deterministic config composition: disjoint fragments, stable hashes."""

import json

import pytest

from speech_aware_evidence_acquisition.core.config import (
    DEFAULT_RUNTIME_RECEIPT_RELPATH,
    ComposedConfig,
    ConfigError,
    compose,
    model_lock_key,
    protocol_hash,
    resolve_runtime_receipt_path,
    runtime_receipt_relpath,
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


# ---------------------------------------------------------------------------
# Second-pinned-model plumbing: an optional "runtime_receipt" key in the
# model fragment selects WHICH committed runtime receipt a session/gate pair
# binds to, defaulting to today's "receipts/runtime.json" when the key is
# absent -- every fragment that predates the key keeps composing to the
# exact same config_hash it always did.
# ---------------------------------------------------------------------------


def test_runtime_receipt_relpath_defaults_when_key_absent():
    assert runtime_receipt_relpath({}) == DEFAULT_RUNTIME_RECEIPT_RELPATH == "receipts/runtime.json"


def test_runtime_receipt_relpath_returns_the_explicit_value():
    assert (
        runtime_receipt_relpath({"runtime_receipt": "receipts/runtime-q4km.json"})
        == "receipts/runtime-q4km.json"
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/etc/passwd",
        "C:/receipts/runtime.json",
        "receipts\\runtime.json",
        "../outside.json",
        "receipts/../../outside.json",
        123,
        None,
    ],
)
def test_runtime_receipt_relpath_rejects_unsafe_or_malformed_values(value):
    with pytest.raises(ConfigError, match="runtime_receipt"):
        runtime_receipt_relpath({"runtime_receipt": value})


def test_resolve_runtime_receipt_path_joins_under_the_repo_docs_directory(tmp_path):
    assert (
        resolve_runtime_receipt_path(tmp_path, {})
        == tmp_path / "docs" / "receipts" / "runtime.json"
    )
    assert resolve_runtime_receipt_path(
        tmp_path, {"runtime_receipt": "receipts/runtime-q4km.json"}
    ) == tmp_path / "docs" / "receipts" / "runtime-q4km.json"


def test_config_hash_changes_when_a_fragment_declares_runtime_receipt(tmp_path):
    """Proves the flow-through end to end via the real compose() pipeline
    (not merely the helper's own isolated logic): two model fragments,
    identical except one declares ``runtime_receipt``, must compose to
    DIFFERENT config_hash -> protocol_hash values -- exactly like any other
    model-config key already does, since compose() merges every fragment's
    top-level keys verbatim before hashing."""

    for kind, name, body in (
        ("dataset", "d", {"carrier_lock_key": "earnings22-original", "split_name": "dev"}),
        ("baseline", "b", {"arm": "bare-core", "policy": "fixed", "task_instruction": "t"}),
        ("experiment", "e", {"experiment_id": "SAEA-E-001"}),
    ):
        path = tmp_path / "configs" / kind / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body), encoding="utf-8")

    model_dir = tmp_path / "configs" / "model"
    model_dir.mkdir(parents=True)
    (model_dir / "m-default.json").write_text(
        json.dumps({"transport": "llama-server", "base_url": "http://x"}), encoding="utf-8"
    )
    (model_dir / "m-q4km.json").write_text(
        json.dumps(
            {
                "transport": "llama-server",
                "base_url": "http://x",
                "runtime_receipt": "receipts/runtime-q4km.json",
            }
        ),
        encoding="utf-8",
    )

    default_composed = compose(tmp_path, "m-default", "d", "b", "e")
    q4km_composed = compose(tmp_path, "m-q4km", "d", "b", "e")

    assert "runtime_receipt" not in default_composed.values
    assert q4km_composed.values["runtime_receipt"] == "receipts/runtime-q4km.json"
    assert default_composed.config_hash != q4km_composed.config_hash
    assert protocol_hash(
        default_composed.config_hash, "bare-core", "s" * 64
    ) != protocol_hash(q4km_composed.config_hash, "bare-core", "s" * 64)


def test_q4km_repo_fragment_composes_with_the_expected_runtime_selection():
    """The real committed fragment (deliverable 3): the locked serving
    baseline. Since the 2026-08-12 A-double-prime re-lock this is the
    hbmfree shape: feature-cache build receipt, mmproj evicted to host,
    np8 with slots sized to the measured evidence-prompt ceiling."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp-q4km", "earnings22-dev-subset10", "bare-core", "r0-smoke"
    )
    assert composed.values["model_lock_key"] == "qwen3-omni-30b-a3b-instruct-gguf-q4km"
    # 2026-08-09: 900 -> 240 s, plus a 1024-token generation cap (two arms
    # aborted on ONE runaway slice each; the cap makes the worst case
    # finite). 2026-08-11 RE-LOCK (config A-prime, cacheorder re-verify
    # 73488c): 240 -> 420 s -- a runaway EVIDENCE slice decoding toward the
    # cap at ~3 tok/s needs ~340 s and deterministically crossed the 240 s
    # ceiling (the armed retry logging named it: TimeoutError x2 -> skip x2
    # -> abort); 420 s lets it finish into a quarantined saturation flag
    # instead of killing the arm. Same re-lock adds per-sample slot
    # affinity and the stable-first prompt order (evidence ahead of the
    # instruction+tail in the system message; bare-core prompts are
    # byte-identical under both orders).
    assert composed.values["timeout_seconds"] == 420.0
    assert composed.values["decoding_params"]["max_tokens"] == 1024
    assert composed.values["decoding_params"]["id_slot"] == "per-sample"
    assert composed.values["prompt_order"] == "evidence-first-system-v2"
    # 2026-08-12 RE-LOCK (config A-double-prime, hbmfree probes A+B): the
    # feature cache makes the audio encoder a no-op on warm corpora (806/806
    # hits, zero encoder calls), so --no-mmproj-offload evicts the mmproj's
    # 2.9 GB from the GPU with none of the config-B-era CPU-encode penalty
    # (probe A: peak 18,738 MiB, WER on the no-tail floor, wall in-band).
    # The freed HBM buys evidence-arm np8: slots re-sized to the MEASURED
    # prompt ceiling (R4 max 7,611 + 1,024 gen -> 10,240/slot; the ConEC
    # worst-case 12,288 guess is retired), and -c 81920 -np 8 fits at
    # 22,114 MiB peak where the mmproj-resident equivalent could not boot
    # (config C's grave). Same matched-evidence workload: 43.2 min on the
    # np4 sequential era -> 20 min (probe B, SAEA-BENCH-hbmfree-evid).
    # The cache dir env is part of the config hash; the receipt binds the
    # patched build (5d9dfcb58).
    assert composed.values["server_args"] == [
        "-c", "81920", "-np", "8", "-fa", "on", "-ngl", "999",
        "-ctk", "q8_0", "-ctv", "q8_0", "--no-mmproj-offload",
    ]
    assert "-ot" not in composed.values["server_args"]
    assert composed.values["runtime_receipt"] == "receipts/runtime-q4km-featcache.json"
    assert runtime_receipt_relpath(composed.values) == "receipts/runtime-q4km-featcache.json"
    assert composed.values["server_env"] == {
        "LLAMA_MTMD_FEAT_CACHE_DIR": "/home/chao/feat-cache/q4km"
    }

    base_composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp", "earnings22-dev-subset10", "bare-core", "r0-smoke"
    )
    assert base_composed.config_hash != composed.config_hash


# ---------------------------------------------------------------------------
# model_lock_key: the composed config's own declaration of WHICH pinned model
# this run is for -- the same declaration `runtime_receipt_relpath` already
# uses to select the receipt FILE. Read directly, no default: every model
# fragment names its own frozen umbrella-lock entry explicitly (unlike
# `runtime_receipt`, which is genuinely optional), so an omitted or malformed
# value fails closed rather than silently falling back to any one model.
# ---------------------------------------------------------------------------


def test_model_lock_key_returns_the_declared_value():
    assert model_lock_key({"model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf-q4km"}) == (
        "qwen3-omni-30b-a3b-instruct-gguf-q4km"
    )


@pytest.mark.parametrize("values", [{}, {"model_lock_key": ""}, {"model_lock_key": 123}, {"model_lock_key": None}])
def test_model_lock_key_rejects_missing_or_malformed_values(values):
    with pytest.raises(ConfigError, match="model_lock_key"):
        model_lock_key(values)


def test_q4km_repo_fragment_model_lock_key_matches_its_own_receipt_selection():
    """The real committed Q4_K_M fragment declares the SAME model_lock_key
    that its own runtime_receipt selection is built for -- a run composed
    from this fragment binds one identity throughout, not two independently
    drifting strings."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp-q4km", "earnings22-dev-subset10", "bare-core", "r0-smoke"
    )
    assert model_lock_key(composed.values) == "qwen3-omni-30b-a3b-instruct-gguf-q4km"

    base_composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp", "earnings22-dev-subset10", "bare-core", "r0-smoke"
    )
    assert model_lock_key(base_composed.values) == "qwen3-omni-30b-a3b-instruct-gguf"
