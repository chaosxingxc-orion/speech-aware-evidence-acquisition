"""Deterministic config composition: disjoint fragments, stable hashes."""

import json

import pytest

from speech_aware_evidence_acquisition.core.config import (
    DEFAULT_RUNTIME_RECEIPT_RELPATH,
    ComposedConfig,
    ConfigError,
    compose,
    model_materialization_root,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
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


def test_d1_media_supplement_relpath_is_optional_and_path_confined():
    assert d1_media_supplement_relpath({}) is None
    assert d1_media_supplement_sha256({}) is None
    values = {
        "d1_media_supplement": "receipts/artifacts/d1-speech-native-train90.json",
        "d1_media_supplement_sha256": "a" * 64,
    }
    assert d1_media_supplement_relpath(
        values
    ) == "receipts/artifacts/d1-speech-native-train90.json"
    assert d1_media_supplement_sha256(values) == "a" * 64


@pytest.mark.parametrize(
    "value",
    ["", "/etc/passwd", "C:/outside.json", "../outside.json", "a\\b.json", 1],
)
def test_d1_media_supplement_relpath_refuses_unsafe_values(value):
    with pytest.raises(ConfigError, match="d1_media_supplement"):
        d1_media_supplement_relpath(
            {"d1_media_supplement": value, "d1_media_supplement_sha256": "a" * 64}
        )


def test_d1_media_supplement_requires_a_paired_valid_hash():
    with pytest.raises(ConfigError, match="must be configured together"):
        d1_media_supplement_relpath(
            {"d1_media_supplement": "receipts/artifacts/d1.json"}
        )
    with pytest.raises(ConfigError, match="64-hex"):
        d1_media_supplement_sha256(
            {
                "d1_media_supplement": "receipts/artifacts/d1.json",
                "d1_media_supplement_sha256": "bad",
            }
        )


def test_model_materialization_root_defaults_to_canonical_data_root():
    assert model_materialization_root({}) is None


def test_model_materialization_root_accepts_an_explicit_posix_absolute_root():
    assert model_materialization_root(
        {"model_materialization_root": "/home/chao"}
    ) == "/home/chao"


@pytest.mark.parametrize(
    "value",
    ["", "home/chao", "/home/../slow", "/home//chao", "C:\\models", 7],
)
def test_model_materialization_root_refuses_ambiguous_or_unsafe_values(value):
    with pytest.raises(ConfigError, match="model_materialization_root"):
        model_materialization_root({"model_materialization_root": value})


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


def test_speech_native_np24_profile_preserves_context_budget_and_batch_shape():
    """The one-time resident-profile candidate increases request slots without
    increasing total KV context or weakening the measured M11 prompt margin."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    path = (
        REPO_ROOT
        / "configs"
        / "model"
        / "q4km-mmproj-free-speech-native-np24-max64.json"
    )
    values = json.loads(path.read_text(encoding="utf-8"))

    assert values["server_args"] == [
        "-c", "65536", "-np", "24", "-b", "2048", "-ub", "512",
        "-fa", "on", "-ngl", "999", "-ctk", "q8_0", "-ctv", "q8_0",
    ]
    assert values["profile_slot_count"] == 24
    assert values["decoding_params"]["max_tokens"] == 64
    context_per_slot = 65536 // values["profile_slot_count"]
    assert context_per_slot == 2730
    assert context_per_slot - (1873 + values["decoding_params"]["max_tokens"]) == 793
    assert values["speech_feature_root"] == (
        "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a"
    )
    assert "LLAMA_MTMD_FEAT_CACHE_DIR" not in values["server_env"]


def test_speech_native_np32_profile_is_terminal_decode_width_candidate():
    """The terminal slot-width candidate maximizes decode batching while the
    measured M11 prompt and registered completion ceiling still fit a slot."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    model_dir = REPO_ROOT / "configs" / "model"
    base = json.loads(
        (model_dir / "q4km-mmproj-free-speech-native-np16-max64.json").read_text(
            encoding="utf-8"
        )
    )
    candidate = json.loads(
        (model_dir / "q4km-mmproj-free-speech-native-np32-max64.json").read_text(
            encoding="utf-8"
        )
    )

    expected_args = list(base["server_args"])
    parallel_index = expected_args.index("-np") + 1
    expected_args[parallel_index] = "32"
    assert candidate["server_args"] == expected_args
    assert candidate["profile_slot_count"] == 32
    assert candidate["decoding_params"] == base["decoding_params"]
    context_per_slot = 65536 // candidate["profile_slot_count"]
    assert context_per_slot == 2048
    assert context_per_slot - (1873 + candidate["decoding_params"]["max_tokens"]) == 111
    assert {
        key: value
        for key, value in candidate.items()
        if key not in {"server_args", "profile_slot_count"}
    } == {
        key: value
        for key, value in base.items()
        if key not in {"server_args", "profile_slot_count"}
    }


def test_speech_native_np16_wide_batch_profile_changes_only_batch_geometry():
    """The saturated-window successor keeps np16/context/science fixed and
    changes only llama.cpp logical and physical batch ceilings."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    model_dir = REPO_ROOT / "configs" / "model"
    base = json.loads(
        (model_dir / "q4km-mmproj-free-speech-native-np16-max64.json").read_text(
            encoding="utf-8"
        )
    )
    wide = json.loads(
        (
            model_dir
            / "q4km-mmproj-free-speech-native-np16-b4096-ub1024-max64.json"
        ).read_text(encoding="utf-8")
    )

    expected_args = list(base["server_args"])
    expected_args[expected_args.index("2048")] = "4096"
    expected_args[expected_args.index("512")] = "1024"
    assert wide["server_args"] == expected_args
    assert wide["profile_slot_count"] == base["profile_slot_count"] == 16
    assert wide["decoding_params"] == base["decoding_params"]
    assert wide["speech_feature_root"] == base["speech_feature_root"]
    assert wide["server_env"] == base["server_env"]
    assert {
        key: value for key, value in wide.items() if key != "server_args"
    } == {
        key: value for key, value in base.items() if key != "server_args"
    }


def test_speech_native_np16_ngram_profile_adds_only_target_verified_drafting():
    """The engine hypothesis keeps the frozen target profile fixed and caps
    one sampled token plus seven target-verified drafts at the CUDA batch limit."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    model_dir = REPO_ROOT / "configs" / "model"
    base = json.loads(
        (model_dir / "q4km-mmproj-free-speech-native-np16-max64.json").read_text(
            encoding="utf-8"
        )
    )
    candidate = json.loads(
        (
            model_dir
            / "q4km-mmproj-free-speech-native-np16-ngram24-draft7-max64.json"
        ).read_text(encoding="utf-8")
    )

    speculative_args = [
        "--spec-type",
        "ngram-mod",
        "--spec-ngram-mod-n-match",
        "24",
        "--spec-ngram-mod-n-min",
        "1",
        "--spec-ngram-mod-n-max",
        "7",
    ]
    assert candidate["server_args"] == [*base["server_args"], *speculative_args]
    assert candidate["profile_slot_count"] == base["profile_slot_count"] == 16
    assert candidate["decoding_params"] == base["decoding_params"]
    assert 16 * (1 + 7) == 128
    assert not {
        "-md",
        "--model-draft",
        "--spec-draft-model",
        "--spec-draft-model-url",
        "--spec-draft-model-hf",
    }.intersection(candidate["server_args"])
    assert {
        key: value for key, value in candidate.items() if key != "server_args"
    } == {
        key: value for key, value in base.items() if key != "server_args"
    }


def test_engineering_packet_equivalence_uses_parallel_packet_validation():
    """The label-free gate must validate cached packets in parallel."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np16-speech-batch-26802-eng",
        "slurp-speech-native-eng-gate8",
        "speech-native-packet-equivalence",
        "speech-native-engineering-gate",
    )

    assert composed.values["profile_validation_workers"] == 16


def test_cross_slot_engineering_gate_pins_the_matching_exact_eight_receipt():
    """The current packet root must not reuse the legacy-root receipt hashes."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np16-speech-batch-26802-eng",
        "slurp-speech-native-eng-gate8",
        "speech-native-packet-equivalence-04ccc72a",
        "speech-native-cross-slot-batch-engineering-gate",
    )

    assert composed.values["speech_packet_promotion_receipt"] == (
        "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/"
        "ENG-GATE8-promotion.json"
    )
    assert composed.values["speech_packet_promotion_receipt_sha256"] == (
        "34184bfef9a60bb28bc0bdbc7c5bf33d1dea7c5da7bd686d6f0aa3c99d3bc15b"
    )


def test_information_complete_e108_m11_composes_on_the_resident_np16_service():
    """The 108-query action-support successor pins only promoted speech packets,
    action-complete text keys, and the admitted residual-boundary graph."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np16-max64",
        "slurp-speech-native-evidence-e108",
        "speech-native-evidence-e108-information-complete-m11",
        "speech-native-evidence-e108-k1-m11-information-complete-action-support",
    )
    values = composed.values

    assert values["server_args"] == [
        "-c", "65536", "-np", "16", "-b", "2048", "-ub", "512",
        "-fa", "on", "-ngl", "999", "-ctk", "q8_0", "-ctv", "q8_0",
    ]
    assert values["server_env"] == {
        "LLAMA_SPEECH_FEATURE_ROOT": (
            "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a"
        ),
        "LLAMA_SPEECH_DECODER_SHA256": (
            "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
        ),
    }
    assert values["speech_packet_promotion_receipt"].endswith(
        "/EVIDENCE-E108-promotion.json"
    )
    assert values["speech_packet_promotion_receipt_sha256"] == (
        "4aafd75ab86734159e39d8dedfc3ec12346d75d683119984c7b1aece761c1555"
    )
    assert values["speech_native_binding"] == (
        "configs/probes/g0-binding/"
        "speech-native-train-binding-evidence-e108-information-complete-knowledge.json"
    )
    assert values["speech_native_binding_file_sha256"] == (
        "a2ccd4b004ce2e31329bf7b69ce0ebb9cff642eec2d25cde8087ffc679203dfe"
    )
    assert values["speech_native_decision_graph"] == (
        "configs/knowledge/slurp-signature-complete-decision-graph-v5.json"
    )
    assert values["speech_native_decision_graph_file_sha256"] == (
        "58c9457312d71a7c7a13e92e53e2a4f9fff5c45a9722eb5680d0fd465fe8a2fc"
    )
    assert values["speech_native_prompt_fit_receipt"] == (
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-08-22-m11-v5-prompt-fit/prompt-fit.json"
    )
    assert values["speech_native_prompt_fit_receipt_sha256"] == (
        "a5931ccd3c9e02150496d0475829e926becc02ed83322d45f4121dd00ee2a289"
    )
    assert values["profile_key_order_ids"] == ["canonical"]
    assert values["profile_queue_depth_multiplier"] == 4
    assert values["profile_validation_workers"] == 16
    assert values["speech_native_dispatch_granularity"] == "contact"
    assert values["speech_native_contact_ceiling_per_task"] == 5
    assert values["speech_native_top_k"] == 3
    assert values["key_representation_id"] == "K1"
    assert values["matcher_policy_id"] == "M11"
    assert values["speech_native_agent_policy_id"] == (
        "speech-conditioned-adaptive-evidence-gap-v2"
    )
    assert values["speech_native_agent_aggregator_id"] == (
        "adaptive-evidence-gap-primary-control-v1"
    )
    assert values["speech_native_training_free_reader_policy_id"] == (
        "speaker-grouped-oof-information-advantage-v1"
    )
    assert values["speech_native_training_free_reader_contract"] == {
        "support_minimum_query_count": 100,
        "support_minimum_top_k_reachable": 100,
        "support_minimum_action_variable_queries": 24,
        "support_minimum_adaptive_boundary_queries": 18,
        "support_minimum_boundary_non_primary_actions": 12,
        "support_minimum_incremental_boundary_repairs": 3,
        "support_minimum_oracle_gain": 6,
        "support_maximum_mechanism_failures": 0,
        "oof_fold_count": 3,
        "oof_minimum_state_support": 5,
        "oof_minimum_changed_prediction_support": 3,
        "oof_minimum_helpful_transitions": 2,
        "oof_minimum_estimated_net_gain": 2,
        "oof_maximum_harmful_transitions": 0,
        "promotion_minimum_net_gain": 3,
        "promotion_minimum_positive_folds": 2,
        "promotion_minimum_worst_fold_delta": 0,
        "promotion_maximum_harmful_transitions": 1,
        "promotion_minimum_action_rate": 0.05,
        "promotion_maximum_action_rate": 0.5,
        "promotion_requires_lower_mean_calls": True,
    }
    context_per_slot = 65536 // values["profile_slot_count"]
    exact_prompt_upper_bound = 2341
    maximum_completion_tokens = 64
    assert (
        context_per_slot - exact_prompt_upper_bound - maximum_completion_tokens == 1691
    )


def test_information_complete_e108_m11_composes_on_the_resident_zero_copy_service():
    """The same 108-query action-support cell, attached to the RESIDENT
    singleton-zero-copy service under the primary `speech-query-prefix-v2`
    serving layout adopted by the 2026-08-23 paired prefix probe.

    Two properties are load-bearing and are asserted rather than described.
    First, the model fragment must reproduce the running service argv exactly:
    this composition attaches to an already-resident server and never launches
    one, so any server_args drift is an attachment refusal, not a new process.
    Second, the scientific contract must NOT drift from the canonical-order
    sibling above -- graph pin, policy ids, and every reader-contract threshold
    stay byte-identical, and only the prompt-fit receipt and the experiment id
    move, because only the transport layout changed.
    """

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np16-zcopy-speech-query-prefix-max64",
        "slurp-speech-native-evidence-e108",
        "speech-native-evidence-e108-information-complete-m11",
        "speech-native-evidence-e108-k1-m11-information-complete-action-support-zcopy",
    )
    values = composed.values

    # The resident SAEA-SN-Q4KM-NP16-HOT-PREFIX-ZCOPY argv, byte for byte.
    assert values["server_args"] == [
        "-c", "65536", "-np", "16", "-b", "2048", "-ub", "512",
        "-fa", "on", "-ngl", "999", "-ctk", "q8_0", "-ctv", "q8_0",
        "--cache-prompt", "--cache-ram", "0",
        "--no-cache-idle-slots", "--slot-prompt-similarity", "0",
    ]
    assert values["runtime_receipt"] == (
        "receipts/runtime-q4km-mmproj-free-speech-batch-26802-singleton-zero-copy.json"
    )
    assert values["prompt_order"] == "speech-query-prefix-v2"
    assert values["decoding_params"] == {
        "temperature": 0,
        "seed": 20260803,
        "max_tokens": 64,
        "id_slot": "per-sample",
    }
    assert values["server_env"] == {
        "LLAMA_SPEECH_FEATURE_ROOT": (
            "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a"
        ),
        "LLAMA_SPEECH_DECODER_SHA256": (
            "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
        ),
    }

    # The zero-copy cell pins its OWN prompt-fit receipt: the canonical-order
    # audit does not certify the prefix layout's token geometry.
    assert values["experiment_id"] == (
        "SAEA-SN-EVIDENCE-E108-K1M11-INFORMATION-COMPLETE-ACTION-SUPPORT-ZCOPY"
    )
    assert values["speech_native_prompt_fit_receipt"] == (
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-08-23-e108-zcopy-prompt-fit/prompt-fit.json"
    )
    assert values["speech_native_prompt_fit_receipt_sha256"] == (
        "c2ee949a58c368dc3e3c4b3541f64ad845158771d90ca66327b955de30c46b4f"
    )

    # Everything else is the canonical-order cell, unchanged.
    canonical = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np16-max64",
        "slurp-speech-native-evidence-e108",
        "speech-native-evidence-e108-information-complete-m11",
        "speech-native-evidence-e108-k1-m11-information-complete-action-support",
    )
    shared_scientific_keys = (
        "key_representation_id",
        "matcher_policy_id",
        "matcher_prompt_policy_id",
        "speech_native_decision_graph",
        "speech_native_decision_graph_file_sha256",
        "speech_native_binding",
        "speech_native_binding_file_sha256",
        "speech_native_agent_policy_id",
        "speech_native_agent_aggregator_id",
        "speech_native_training_free_reader_policy_id",
        "speech_native_training_free_reader_contract",
        "speech_packet_promotion_receipt",
        "speech_packet_promotion_receipt_sha256",
        "speech_native_top_k",
        "speech_native_contact_ceiling_per_task",
        "speech_native_dispatch_granularity",
        "profile_key_order_ids",
        "count",
        "split_name",
        "arm",
        "purpose",
    )
    for key in shared_scientific_keys:
        assert values[key] == canonical.values[key], key

    # The prefix layout costs 68 tokens at the worst envelope and still leaves
    # a large slot margin (audit c2ee949a..., worst envelope boundary:B001:K003:ba).
    context_per_slot = 65536 // values["profile_slot_count"]
    exact_prompt_upper_bound = 2409
    maximum_completion_tokens = 64
    assert (
        context_per_slot - exact_prompt_upper_bound - maximum_completion_tokens == 1623
    )


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


def test_cross_slot_prompt_bound_m11_profile_preserves_the_frozen_workload():
    """The cross-slot admission changes only the engine and its session receipt."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np16-speech-batch-26802-prompt-bound-max64",
        "slurp-speech-native-opt-a36",
        "speech-native-engineering-adaptive-m11-k3-v4-contact",
        "speech-native-engineering-adaptive-m11-data-knowledge",
    )
    values = composed.values

    assert values["runtime_receipt"] == (
        "receipts/runtime-q4km-mmproj-free-speech-batch-26802.json"
    )
    assert values["server_args"] == [
        "-c", "65536", "-np", "16", "-b", "2048", "-ub", "512",
        "-fa", "on", "-ngl", "999", "-ctk", "q8_0", "-ctv", "q8_0",
    ]
    assert values["decoding_params"]["max_tokens"] == 64
    assert values["speech_native_prompt_fit_receipt"] == (
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-08-23-m11-v3-speech-batch-26802-prompt-fit/prompt-fit.json"
    )
    assert values["speech_native_prompt_fit_receipt_sha256"] == (
        "f76b817aac1b4afd260ba7727b10e171a5646f9c8b84c627ce6a07c32add3062"
    )
    assert values["profile_key_order_ids"] == [
        "canonical", "reverse", "rotate-1", "rotate-7"
    ]
    assert values["speech_native_decision_graph_file_sha256"] == (
        "07e51acc91b91636ae0451f5b9b2ebe719464140427b024701028621ccdeb6fb"
    )
    assert values["matcher_policy_id"] == "M11"


def test_slot_affine_cache_profile_binds_hot_hbm_policy_and_parallel_build():
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np16-singleton-zero-copy-cache-hot-max64",
        "slurp-speech-native-opt-a36",
        "speech-native-engineering-adaptive-m11-k3-v4-task-affine-speech-prefix",
        "speech-native-engineering-adaptive-m11-data-knowledge",
    )
    values = composed.values

    assert values["runtime_receipt"] == (
        "receipts/runtime-q4km-mmproj-free-speech-batch-26802-"
        "singleton-zero-copy.json"
    )
    assert values["server_args"][-6:] == [
        "--cache-prompt",
        "--cache-ram",
        "0",
        "--no-cache-idle-slots",
        "--slot-prompt-similarity",
        "0",
    ]
    assert values["speech_native_dispatch_granularity"] == "task"
    assert values["speech_native_request_layout_id"] == (
        "slot-affine-speech-prefix-v1"
    )
    assert values["prompt_order"] == "speech-features-text-keys-v1"
    assert values["decoding_params"]["id_slot"] == "per-sample"
    assert values["speech_native_prompt_fit_receipt"] == (
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-08-23-m11-hot-prefix-prompt-fit/prompt-fit-exact.json"
    )
    assert values["speech_native_prompt_fit_receipt_sha256"] == (
        "730354358c47258fe0d9468c9062fbf8898ecab30a6304a3affdf8e7615d46ec"
    )


@pytest.mark.parametrize(
    (
        "model",
        "baseline",
        "prompt_order",
        "request_layout",
        "prompt_receipt",
        "prompt_receipt_sha256",
    ),
    (
        (
            "q4km-mmproj-free-speech-native-np16-hot-prefix-speech-query-v2",
            "speech-native-engineering-m11-prefix-probe-speech-query-v2",
            "speech-query-prefix-v2",
            "slot-affine-speech-prefix-v1",
            "docs/checks/speech-aware-evidence-acquisition/2026-08-23-m11-prefix-probe-speech-query-prompt-fit/prompt-fit.json",
            "9c48de33b518ed06b630e4d691c8fda1c4b9c78d0ab2bb14e5e5ac00be1cf9ef",
        ),
        (
            "q4km-mmproj-free-speech-native-np16-hot-prefix-dual-v2",
            "speech-native-engineering-m11-prefix-probe-dual-v2",
            "knowledge-speech-state-v2",
            "slot-affine-knowledge-speech-state-v1",
            "docs/checks/speech-aware-evidence-acquisition/2026-08-23-m11-prefix-probe-dual-prompt-fit/prompt-fit.json",
            "b4b86e32ece88a9ee33092c9ed6e3981ddd32145a69a616c95e307c2b5198330",
        ),
    ),
)
def test_prefix_probe_profiles_bind_wire_order_and_exact_prompt_receipt(
    model,
    baseline,
    prompt_order,
    request_layout,
    prompt_receipt,
    prompt_receipt_sha256,
):
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    values = compose(
        REPO_ROOT,
        model,
        "slurp-speech-native-eng-gate8",
        baseline,
        "speech-native-engineering-adaptive-m11-data-knowledge",
    ).values

    assert values["prompt_order"] == prompt_order
    assert values["speech_native_request_layout_id"] == request_layout
    assert values["profile_key_order_ids"] == ["canonical", "reverse"]
    assert values["speech_native_dispatch_granularity"] == "task"
    assert values["decoding_params"]["id_slot"] == "per-sample"
    assert values["speech_native_prompt_fit_receipt"] == prompt_receipt
    assert values["speech_native_prompt_fit_receipt_sha256"] == prompt_receipt_sha256


def test_dev100_kb_alpha_blend_campaign_composes_on_the_resident_zero_copy_service():
    """The DEV-100 optimization campaign attaches to the SAME resident
    zero-copy service the E108 cell flew on, over the DEV-100 runtime view.

    Three properties are load-bearing and asserted rather than described.

    First, the campaign is a DEV-role composition: the dataset fragment's
    embedded ``split_identity_hash`` is the SLASH-prefixed run identity
    ``load_split``/``ExecutionPlan``/``protocol_hash`` use, not the DEV-100
    receipt's colon-keyed receipt-integrity value -- binding the two by
    construction is what closes the defect class that refused the 2026-08-22
    E108 current-binding plan.

    Second, the model fragment must reproduce the running service argv
    exactly: this composition attaches to an already-resident server and
    never launches one, so any server_args drift is an attachment refusal.

    Third, the campaign's scientific contract -- the C3 policy chain, the
    round-0 knob table, the pinned TRAIN snapshot, the preregistered stopping
    rule, and the section-4 ceilings -- is machine-readable and pinned here,
    so a later round cannot quietly move a knob or a stopping condition
    without this test changing with it.
    """

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT
    from speech_aware_evidence_acquisition.rails import kb_policy

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np16-zcopy-speech-query-prefix-max64",
        "slurp-speech-native-dev100",
        "slurp-dev100-kb-alpha-blend",
        "slurp-dev100-kb-alpha-blend-campaign-v1",
    )
    values = composed.values

    assert values["experiment_id"] == "SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN"
    assert values["execution_profile"] == "bounded-discovery-probe"

    # DEV-role split identity, load_split convention.
    assert values["split_name"] == "DEV-100"
    assert values["split_role"] == "dev"
    assert values["count"] == 100
    assert values["audio_seconds_total"] == 275.700125
    assert values["split_identity_hash"] == (
        "e9a7b7febcf4fe3dc228370f7487e1e75dea3d63d447a07fbfe87c1404e2d853"
    )
    assert values["kb_campaign_split"]["receipt_integrity_hash"] == (
        "d676d38b4d27b3a136ba2523b96ae3c71ba2b8b436f7712f4f0c976c3ea833e1"
    )
    assert values["kb_campaign_dataset_fragment"] == "slurp-speech-native-dev100"
    # DEV media is already inside the immutable D1 closure, so the view
    # declares no supplement at all.
    assert values["d1_media_supplement"] is None
    assert values["d1_media_supplement_sha256"] is None

    # The resident SAEA-SN-Q4KM-NP16-HOT-PREFIX-ZCOPY argv, byte for byte.
    assert values["server_args"] == [
        "-c", "65536", "-np", "16", "-b", "2048", "-ub", "512",
        "-fa", "on", "-ngl", "999", "-ctk", "q8_0", "-ctv", "q8_0",
        "--cache-prompt", "--cache-ram", "0",
        "--no-cache-idle-slots", "--slot-prompt-similarity", "0",
    ]
    assert values["prompt_order"] == "speech-query-prefix-v2"
    assert values["server_env"] == {
        "LLAMA_SPEECH_FEATURE_ROOT": (
            "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a"
        ),
        "LLAMA_SPEECH_DECODER_SHA256": (
            "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
        ),
    }
    assert values["speech_packet_promotion_receipt"].endswith("/DEV-100-promotion.json")
    assert values["speech_packet_promotion_receipt_sha256"] == (
        "8d2dc4dc9056ed604b22cbb66cd46724d3ee0246b6aca5665e6bfaf67cf0503d"
    )

    # The frozen baseline form (owner ruling 2026-08-23 section 7.1).
    assert values["kb_campaign_policy_chain"] == {
        "controller_policy_id": "saea-kb-alpha-blend-v1",
        "ranker_policy_id": "saea-rank-wcos-prior-agree-v1",
        "fuser_policy_id": "saea-fuse-supplyfilter-v1",
        "agent_executor_id": "openjiuwen-workflow-v1",
        "policy_config_baseline": "configs/policy/kb-policy-v1.json",
        "m11_pair_boundary_stage": False,
        "m11_pair_boundary_rationale": (
            "M11 operating-point sweep verdict: zero repairs as flown; its two "
            "missed repairs are captured by the blend layer at zero additional "
            "contacts."
        ),
    }
    assert values["kb_campaign_policy_chain"]["controller_policy_id"] == (
        kb_policy.CONTROLLER_POLICY_ID
    )
    assert values["kb_campaign_policy_chain"]["ranker_policy_id"] == (
        kb_policy.RANK_POLICY_ID
    )
    assert values["kb_campaign_policy_chain"]["fuser_policy_id"] == (
        kb_policy.FUSE_POLICY_ID
    )

    # Round-0 knobs: the sweep-recommended cell, mid-plateau on alpha.
    knobs = values["kb_campaign_round0_knobs"]
    assert knobs["alpha"] == 0.6
    assert knobs["rank_weight_id"] == "rrf"
    assert knobs["evidence_variant"] == "rank+prior+agreement"
    assert knobs["tau"] == 0.5
    assert knobs["top_k_per_dimension"] == 5
    assert knobs["prior_source"] == "train"
    assert knobs["rank_weights"] == {"w_cos": 0.5, "w_prior": 0.3, "w_agree": 0.2}

    # The pinned TRAIN snapshot, exactly the KB-BUILD receipt's own hash.
    kb_receipt = json.loads(
        (REPO_ROOT / "docs" / "receipts" / "knowledge" / "slurp-kb-size-full.json").read_text(
            encoding="utf-8"
        )
    )
    assert values["kb_campaign_knowledge_snapshot"]["snapshot_sha256"] == (
        kb_receipt["snapshot_sha256"]
    )
    assert values["kb_campaign_knowledge_snapshot"]["source_split"] == "train"

    # The preregistered stopping rule, machine-readable.
    assert values["kb_campaign_stopping_rule"] == {
        "converged": {
            "metric": "best_arm_correct_sample_count",
            "maximum_absolute_delta_samples": 1,
            "consecutive_rounds": 2,
            "maximum_correct_to_wrong_growth": 0,
        },
        "falsified": {
            "condition": "no_arm_beats_direct_decode",
            "after_completed_rounds": 3,
        },
        "hard_cap_rounds": 6,
        "evaluation_moment": (
            "between rounds only, after every arm of a round has completed "
            "(runner seal-before-score); gold never enters runtime"
        ),
    }

    # Preregistration section 4 ceilings.
    ceilings = values["kb_campaign_ceilings"]
    assert ceilings["frozen_core_contacts_total"] == 1800
    assert ceilings["frozen_core_contacts_per_round"] == 300
    assert ceilings["pinned_tool_embedding_contacts_total"] == 1500
    assert ceilings["metered_audio_seconds_total"] == 2400
    assert ceilings["gpu_hours_total"] == 2.0

    # Prompt geometry: the C3 bound is NEGATIVE on this service and the test
    # says so. The registered receipt measured the worst reachable
    # evidence-decode envelope at 7,773 prompt tokens against the 4,096
    # tokens one slot of the resident `-np 16` service provides, so round 0
    # cannot fly as composed. This assertion exists to keep that fact from
    # being quietly forgotten: it fails the moment someone "fixes" the
    # receipt without re-measuring, and it fails just as loudly if the
    # geometry is repaired without moving the campaign onto a service whose
    # slot actually holds the prompt.
    prompt_fit = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "checks"
            / "speech-aware-evidence-acquisition"
            / "2026-08-24-dev100-c3-prompt-fit"
            / "prompt-fit.json"
        ).read_text(encoding="utf-8")
    )
    assert prompt_fit["model_contact"] is False
    assert prompt_fit["config_hash"] == composed.config_hash
    assert prompt_fit["knowledge_snapshot_sha256"] == (
        values["kb_campaign_knowledge_snapshot"]["snapshot_sha256"]
    )
    assert prompt_fit["prompt_order"] == values["prompt_order"]

    context_per_slot = 65536 // 16
    assert prompt_fit["context_tokens_per_slot"] == context_per_slot
    assert prompt_fit["maximum_completion_tokens"] == values["decoding_params"]["max_tokens"]
    assert (
        context_per_slot
        - prompt_fit["maximum_prompt_tokens_upper_bound"]
        - prompt_fit["maximum_completion_tokens"]
        == prompt_fit["context_margin_tokens"]
    )

    by_envelope = {row["envelope_id"]: row for row in prompt_fit["envelopes"]}
    # The direct-decode contact fits with room to spare; the
    # evidence-conditioned one does not fit at all.
    assert by_envelope["direct-decode"]["prompt_tokens_upper_bound"] == 1819
    assert by_envelope["evidence-decode-worst"]["prompt_tokens_upper_bound"] == 7773
    assert prompt_fit["worst_envelope_id"] == "evidence-decode-worst"
    assert prompt_fit["context_margin_tokens"] == -3741
    assert prompt_fit["maximum_prompt_fits_one_slot"] is False

    # The largest slot count that DOES admit the measured worst case, which
    # is what a future campaign fragment has to serve on.
    required = (
        prompt_fit["maximum_prompt_tokens_upper_bound"]
        + prompt_fit["maximum_completion_tokens"]
    )
    assert required == 7837
    assert 65536 // 8 >= required
    assert 65536 // 16 < required

    # Record the composed identity so a fragment edit is a visible test move.
    assert composed.config_hash == "668a0f1c6adfc11228535dd6bcedf56284c446551077a1e137576533e8b638dd"


def test_dev100_kb_alpha_blend_campaign_composes_on_the_np8_zcopy_service():
    """The CAMPAIGN composition after preregistration amendment 5b: the same
    DEV-100 campaign contract served on the np8 zero-copy variant.

    Amendment 5b (docs/readiness/2026-08-23-dev100-campaign-preregistration.md)
    adopted two remedies for the negative np16 prompt-fit verdict pinned by
    the previous test: the contract-dedup rendering fix in rails/kb_policy.py
    (commit 72096bad) and the `-np 8` serving variant, whose 8,192-token slots
    admit the measured worst-case envelope (7,773 + 64 = 7,837 <= 8,192) even
    BEFORE the rendering fix. This test pins the np8 model fragment as a
    byte-for-byte sibling of the np16 fragment except the two slot-count
    fields, re-asserts the full campaign contract on the new composition, and
    records the np8 composed hash — the hash the campaign row registers.
    """

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np8-zcopy-speech-query-prefix-max64",
        "slurp-speech-native-dev100",
        "slurp-dev100-kb-alpha-blend",
        "slurp-dev100-kb-alpha-blend-campaign-v1",
    )
    values = composed.values

    assert values["experiment_id"] == "SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN"
    assert values["execution_profile"] == "bounded-discovery-probe"

    # Identical scientific surface to the np16 composition: same DEV-role
    # split identity, same promotion receipt, same campaign contract.
    assert values["split_name"] == "DEV-100"
    assert values["split_role"] == "dev"
    assert values["count"] == 100
    assert values["split_identity_hash"] == (
        "e9a7b7febcf4fe3dc228370f7487e1e75dea3d63d447a07fbfe87c1404e2d853"
    )
    assert values["kb_campaign_split"]["receipt_integrity_hash"] == (
        "d676d38b4d27b3a136ba2523b96ae3c71ba2b8b436f7712f4f0c976c3ea833e1"
    )
    assert values["speech_packet_promotion_receipt_sha256"] == (
        "8d2dc4dc9056ed604b22cbb66cd46724d3ee0246b6aca5665e6bfaf67cf0503d"
    )

    # The np8 serving variant: identical argv except `-np 8`, and the
    # profile slot count moves with it. Everything else byte-identical to
    # the resident zcopy profile.
    assert values["server_args"] == [
        "-c", "65536", "-np", "8", "-b", "2048", "-ub", "512",
        "-fa", "on", "-ngl", "999", "-ctk", "q8_0", "-ctv", "q8_0",
        "--cache-prompt", "--cache-ram", "0",
        "--no-cache-idle-slots", "--slot-prompt-similarity", "0",
    ]
    assert values["profile_slot_count"] == 8
    assert values["prompt_order"] == "speech-query-prefix-v2"
    assert values["server_env"] == {
        "LLAMA_SPEECH_FEATURE_ROOT": (
            "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a"
        ),
        "LLAMA_SPEECH_DECODER_SHA256": (
            "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
        ),
    }

    # The np8 fragment is the np16 fragment except exactly the two slot
    # fields — enforced by construction, not by prose.
    np16 = json.loads(
        (
            REPO_ROOT / "configs" / "model"
            / "q4km-mmproj-free-speech-native-np16-zcopy-speech-query-prefix-max64.json"
        ).read_text(encoding="utf-8")
    )
    np8 = json.loads(
        (
            REPO_ROOT / "configs" / "model"
            / "q4km-mmproj-free-speech-native-np8-zcopy-speech-query-prefix-max64.json"
        ).read_text(encoding="utf-8")
    )
    np16_args = list(np16["server_args"])
    np16_args[np16_args.index("-np") + 1] = "8"
    assert np8["server_args"] == np16_args
    assert np8["profile_slot_count"] == 8
    for key in np16:
        if key in ("server_args", "profile_slot_count"):
            continue
        assert np8[key] == np16[key], key

    # Slot geometry: 8,192-token slots admit the measured np16 worst case
    # (7,773 prompt + 64 completion) even before the contract-dedup fix.
    context_per_slot = 65536 // 8
    assert context_per_slot == 8192
    assert context_per_slot >= 7773 + values["decoding_params"]["max_tokens"]

    # Round-0 knobs and ceilings are untouched by the serving change.
    knobs = values["kb_campaign_round0_knobs"]
    assert knobs["alpha"] == 0.6
    assert knobs["rank_weight_id"] == "rrf"
    assert knobs["evidence_variant"] == "rank+prior+agreement"
    assert knobs["tau"] == 0.5
    assert knobs["top_k_per_dimension"] == 5
    assert knobs["prior_source"] == "train"
    ceilings = values["kb_campaign_ceilings"]
    assert ceilings["frozen_core_contacts_total"] == 1800
    assert ceilings["frozen_core_contacts_per_round"] == 300

    # The campaign's registered composed identity (amendment 5b: "the
    # campaign's composed config hash is therefore the np8 composition").
    assert composed.config_hash == "5397ea3ead594409b440ed9d8abc3690f6230d8b357207eb509977e411405944"


def test_dev100_kb_alpha_blend_campaign_composes_on_the_np8_base_service():
    """The ROUND-0 ATTEMPT-6 composition: the same DEV-100 campaign contract
    served on the BASE llama.cpp build (build-attribution mitigation).

    Round-0 attempts 2-5 reproduced a progressive multi-slot decode pathology
    four consecutive times on the CUSTOM ``build-singleton-zero-copy`` binary
    (llama.cpp-featcache-speech-batch-26802); the reboot hypothesis (attempt
    4) and the clock-lock hypothesis (attempt 5) are both falsified. Every
    healthy sustained campaign (Aug-22/23 M11 cells, matched base np16
    1,536.27 tok/s) ran the BASE build ``llama.cpp-featcache`` pinned by
    ``docs/receipts/runtime-q4km-mmproj-free.json``. Attempt 6 therefore
    flies the SAME np8 serving geometry on the base binary: the model
    fragment is a byte-for-byte sibling of the np8 zcopy fragment except
    exactly the ``runtime_receipt`` key — enforced here by construction. The
    base build supports all four cache-discipline flags (upstream flags;
    verified against ``--help`` at attempt-6 preflight), so ``server_args``
    are unchanged.
    """

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64",
        "slurp-speech-native-dev100",
        "slurp-dev100-kb-alpha-blend",
        "slurp-dev100-kb-alpha-blend-campaign-v1",
    )
    values = composed.values

    # Identical scientific surface to the registered np8 zcopy composition.
    assert values["experiment_id"] == "SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN"
    assert values["execution_profile"] == "bounded-discovery-probe"
    assert values["split_name"] == "DEV-100"
    assert values["split_role"] == "dev"
    assert values["count"] == 100
    assert values["split_identity_hash"] == (
        "e9a7b7febcf4fe3dc228370f7487e1e75dea3d63d447a07fbfe87c1404e2d853"
    )
    assert values["speech_packet_promotion_receipt_sha256"] == (
        "8d2dc4dc9056ed604b22cbb66cd46724d3ee0246b6aca5665e6bfaf67cf0503d"
    )

    # The serving swap: the BASE build's receipt, everything else unchanged.
    assert values["runtime_receipt"] == "receipts/runtime-q4km-mmproj-free.json"
    assert values["profile_slot_count"] == 8
    assert values["prompt_order"] == "speech-query-prefix-v2"

    # The base fragment is the np8 zcopy fragment except exactly the
    # runtime_receipt key — enforced by construction, not by prose.
    zcopy = json.loads(
        (
            REPO_ROOT / "configs" / "model"
            / "q4km-mmproj-free-speech-native-np8-zcopy-speech-query-prefix-max64.json"
        ).read_text(encoding="utf-8")
    )
    base = json.loads(
        (
            REPO_ROOT / "configs" / "model"
            / "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64.json"
        ).read_text(encoding="utf-8")
    )
    assert set(base) == set(zcopy)
    assert base["runtime_receipt"] == "receipts/runtime-q4km-mmproj-free.json"
    assert zcopy["runtime_receipt"] == (
        "receipts/runtime-q4km-mmproj-free-speech-batch-26802-singleton-zero-copy.json"
    )
    for key in zcopy:
        if key == "runtime_receipt":
            continue
        assert base[key] == zcopy[key], key

    # The base receipt pins the base build, not the zero-copy build.
    receipt = json.loads(
        (REPO_ROOT / "docs" / "receipts" / "runtime-q4km-mmproj-free.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["llama_cpp"]["binary_path"] == (
        "llama.cpp-featcache/build/bin/llama-server"
    )
    assert receipt["llama_cpp"]["build_commit"] == (
        "04ccc72a2207347ca76161b93fd9d846dd0a8675"
    )
    assert receipt["llama_cpp"]["binary_sha256"] == (
        "d0b42ace8d8e02dc772a0e4a1e1667068b3ad799b1ca4c98c741cf89d58404f2"
    )

    # Round-0 knobs and ceilings are untouched by the serving change.
    knobs = values["kb_campaign_round0_knobs"]
    assert knobs["alpha"] == 0.6
    assert knobs["rank_weight_id"] == "rrf"
    assert knobs["evidence_variant"] == "rank+prior+agreement"
    ceilings = values["kb_campaign_ceilings"]
    assert ceilings["frozen_core_contacts_total"] == 1800

    # The attempt-6 composed identity (differs from the zcopy composition
    # ONLY through the runtime_receipt declaration).
    assert composed.config_hash == "7fff75d1ed8642a9e948d86e8d6c5bf9cfd669f7342d9da009167dfd62655ca5"


def test_dev500_confirmatory_campaign_composes_on_the_np8_base_service():
    """The DEV-500 CONFIRMATORY composition (preregistration
    docs/readiness/2026-08-24-dev500-confirmatory-preregistration.md): the
    frozen DEV-100 cell served on the BASE-build np8 profile over the
    DEV-500 runtime view.

    Four properties are load-bearing and asserted rather than described.

    First, the DEV-role split identity: the dataset fragment embeds the
    SLASH-prefixed run identity ``load_split``/``ExecutionPlan``/
    ``protocol_hash`` use, and the experiment fragment additionally pins the
    receipt-integrity values of DEV-500, the nested exposed DEV-100, and the
    unexposed-400 statistic population, so the one-touch read can never
    silently move to a different sample population.

    Second, the serving surface is the BASE build (campaign verdict section
    4: the zero-copy build is quarantined) at np8 -- the model fragment must
    reproduce the resident service argv exactly, because the campaign
    attaches to an already-resident server and never launches one.

    Third, the scientific contract -- the byte-frozen knob table, the four
    preregistered arms (M0 / BLEND / ABL-RANDRET / ABL-RANDICL), the
    section-1 confirmatory statistic, and the section-3 ceilings -- is
    machine-readable here, pinned against the frozen policy file, so a later
    edit cannot quietly move a knob, an arm, a seed, or a ceiling without
    this test moving with it.

    Fourth, the promotion receipt: the baseline fragment pins the DEV-500
    promotion receipt (500 packets: 400 newly materialized by
    SAEA-SN-DEV500-PREPROCESS + the 100 DEV-100 packets re-verified
    byte-identical) by absolute path and file hash.
    """

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64",
        "slurp-speech-native-dev500",
        "slurp-dev500-kb-alpha-blend",
        "slurp-dev500-confirmatory-campaign-v1",
    )
    values = composed.values

    assert values["experiment_id"] == "SAEA-DEV500-CONFIRMATORY"
    assert values["execution_profile"] == "bounded-discovery-probe"

    # DEV-role split identity, load_split convention, plus the nested and
    # unexposed populations by BOTH hash conventions.
    assert values["split_name"] == "DEV-500"
    assert values["split_role"] == "dev"
    assert values["count"] == 500
    assert values["audio_seconds_total"] == 1422.0816875
    assert values["split_identity_hash"] == (
        "a00f8c8615ea9508a812f93117b9838f2a1a84ec2b3f06c07edc28b04da6acf4"
    )
    split_block = values["dev500_split"]
    assert split_block["receipt_integrity_hash"] == (
        "c0f1c7531fb8972885abf1d840cc101bbfa38ae04e3929cc46e0f5b9ef35452b"
    )
    nested = split_block["nested_exposed_subset"]
    assert nested["count"] == 100
    assert nested["split_identity_hash"] == (
        "e9a7b7febcf4fe3dc228370f7487e1e75dea3d63d447a07fbfe87c1404e2d853"
    )
    assert nested["receipt_integrity_hash"] == (
        "d676d38b4d27b3a136ba2523b96ae3c71ba2b8b436f7712f4f0c976c3ea833e1"
    )
    unexposed = split_block["unexposed_statistic_population"]
    assert unexposed["count"] == 400
    assert unexposed["split_identity_hash"] == (
        "e1cf6fc512a16ec2f1d439655f40b1602ff5e295ec2736cecaf136402a4d036c"
    )
    assert unexposed["receipt_integrity_hash"] == (
        "36c778dafb418d8f0fb80ad53fb11f2608f3ebcd4ad9f5fa3d964ff16b54898b"
    )
    assert unexposed["audio_seconds_total"] == 1146.3815625
    assert values["dev500_dataset_fragment"] == "slurp-speech-native-dev500"
    # DEV media is inside the immutable D1 closure: no supplement.
    assert values["d1_media_supplement"] is None
    assert values["d1_media_supplement_sha256"] is None

    # The BASE-build np8 serving surface (campaign verdict section 4).
    assert values["runtime_receipt"] == "receipts/runtime-q4km-mmproj-free.json"
    assert values["profile_slot_count"] == 8
    assert values["prompt_order"] == "speech-query-prefix-v2"
    assert values["server_args"] == [
        "-c", "65536", "-np", "8", "-b", "2048", "-ub", "512",
        "-fa", "on", "-ngl", "999", "-ctk", "q8_0", "-ctv", "q8_0",
        "--cache-prompt", "--cache-ram", "0",
        "--no-cache-idle-slots", "--slot-prompt-similarity", "0",
    ]
    assert values["server_env"] == {
        "LLAMA_SPEECH_FEATURE_ROOT": (
            "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a"
        ),
        "LLAMA_SPEECH_DECODER_SHA256": (
            "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
        ),
    }

    # The DEV-500 promotion receipt: 500 packets, pinned by path and hash.
    assert values["speech_packet_promotion_receipt"].endswith("/DEV-500-promotion.json")
    assert values["speech_packet_promotion_receipt_sha256"] == (
        "c6d17fdf2f46f655d55661e4e8163818b1100a0a839a873121ab84fa0524ed8c"
    )

    # The byte-frozen knob table, asserted EQUAL to the frozen policy file
    # rather than restated -- a knob move in either place breaks this test.
    frozen_policy = json.loads(
        (REPO_ROOT / "configs" / "policy" / "kb-policy-v1-dev100.json").read_text(
            encoding="utf-8"
        )
    )
    assert values["dev500_frozen_cell"]["knobs"] == frozen_policy["knobs"]
    assert values["dev500_frozen_cell"]["policy_config"] == (
        "configs/policy/kb-policy-v1-dev100.json"
    )
    knobs = values["dev500_frozen_cell"]["knobs"]
    assert knobs["alpha"] == 0.45
    assert knobs["tau"] == 0.65
    assert knobs["fusion"] == {"m": 5, "c": 2, "l": 3}
    assert knobs["prior_source"] == "train"

    # The C3 policy chain, unchanged from the campaign.
    from speech_aware_evidence_acquisition.rails import kb_policy

    chain = values["dev500_policy_chain"]
    assert chain["controller_policy_id"] == kb_policy.CONTROLLER_POLICY_ID
    assert chain["ranker_policy_id"] == kb_policy.RANK_POLICY_ID
    assert chain["fuser_policy_id"] == kb_policy.FUSE_POLICY_ID
    assert chain["agent_executor_id"] == "openjiuwen-workflow-v1"

    # The pinned TRAIN snapshot, exactly the KB-BUILD receipt's own hash.
    kb_receipt = json.loads(
        (REPO_ROOT / "docs" / "receipts" / "knowledge" / "slurp-kb-size-full.json").read_text(
            encoding="utf-8"
        )
    )
    assert values["dev500_knowledge_snapshot"]["snapshot_sha256"] == (
        kb_receipt["snapshot_sha256"]
    )
    assert values["dev500_knowledge_snapshot"]["source_split"] == "train"

    # The four preregistered arms (section 2), machine-readable.
    arms = {arm["arm_id"]: arm for arm in values["dev500_arms"]}
    assert list(arms) == ["M0", "BLEND", "ABL-RANDRET", "ABL-RANDICL"]
    assert arms["M0"]["contacts_per_sample"] == 1
    assert arms["M0"]["worst_case_frozen_core_contacts"] == 400
    assert arms["BLEND"]["contacts_per_sample"] == 2
    assert arms["BLEND"]["tool_contacts_per_sample"] == 1
    assert arms["BLEND"]["worst_case_frozen_core_contacts"] == 800
    assert arms["ABL-RANDRET"]["worst_case_frozen_core_contacts"] == 800
    assert arms["ABL-RANDRET"]["seeded"] is True
    assert arms["ABL-RANDICL"]["worst_case_frozen_core_contacts"] == 800
    # k's worst case is DERIVED from the frozen fusion knobs: m + c*l.
    fusion = knobs["fusion"]
    assert arms["ABL-RANDICL"]["k_worst_case"] == (
        fusion["m"] + fusion["c"] * fusion["l"]
    ) == 11

    # The charter-constrained oracle substitution (section 2), disclosed.
    oracle = values["dev500_oracle_substitution"]
    assert "retrieval-reachability ceiling" in oracle["registered_substitute"]
    assert "forbids gold labels in runtime" in oracle["charter_constraint"]

    # The section-1 confirmatory statistic, frozen in advance.
    statistic = values["dev500_confirmatory_statistic"]
    assert statistic["population"] == (
        "the 400 unexposed samples only (DEV-500 minus DEV-100)"
    )
    assert statistic["statistic"] == "paired per-sample BLEND minus M0"
    assert statistic["bootstrap"] == {
        "kind": "paired cluster bootstrap",
        "n_replicates": 10000,
        "seed": 20260807,
        "confidence_levels": [0.9, 0.95],
    }
    assert statistic["claim_condition"] == "the 90 percent CI excludes zero"
    assert statistic["mcnemar_exact_on_discordant_pairs"] is True

    # One-touch discipline and the registered variance prior.
    assert "ONE registered read" in values["dev500_one_touch"]["rule"]
    assert "round-5" in values["dev500_one_touch"]["variance_prior"]

    # The section-3 ceilings.
    ceilings = values["dev500_ceilings"]
    assert ceilings["frozen_core_contacts_total"] == 3200
    assert ceilings["pinned_tool_embedding_contacts_total"] == 1000
    assert ceilings["metered_audio_seconds_total"] == 8000
    assert ceilings["gpu_hours_total"] == 3.0
    assert len(ceilings["mandatory_rails"]) == 6

    # Slot geometry: the np8 base service's 8,192-token slots admit the
    # DEV-100-measured worst case; the DEV-500 bound is certified by its own
    # prompt-fit receipt (registered separately, model-free).
    context_per_slot = 65536 // values["profile_slot_count"]
    assert context_per_slot == 8192

    # Record the composed identity so a fragment edit is a visible test move.
    assert composed.config_hash == "c1a1b915fa8dd6c4593d1f85caaad99fead3e18f0a80e06b7d5699c74793ee58"
