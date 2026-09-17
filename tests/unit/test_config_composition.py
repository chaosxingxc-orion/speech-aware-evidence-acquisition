"""Deterministic config composition: disjoint fragments, stable hashes."""

import json

import pytest

from speech_aware_evidence_acquisition.core.config import (
    DEFAULT_RUNTIME_RECEIPT_RELPATH,
    ComposedConfig,
    ConfigError,
    assert_preparation_source_receipts_are_well_formed,
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


# ---------------------------------------------------------------------------
# E3b defect 3: three committed E3 fragments (configs/baseline/
# slurp-native-dual-store-train-fold-a-exemplars-k20{,-twin}-v1.json and
# -k12-v1.json) pinned their exemplar knowledge receipt with
# ``"root": "repo"`` -- a value ``core.preparation.verify_source_receipts``
# has never accepted (only "repository" and "data"). The refusal used to
# surface only hundreds of steps into a flight, inside prepare-supply. This
# validator runs at ``compose()`` -- config LOAD time -- instead.
# ---------------------------------------------------------------------------


def test_preparation_source_receipts_bad_root_is_refused_at_compose_time(tmp_path):
    _write_fragments(
        tmp_path,
        experiment_extra={
            "preparation_source_receipts": [
                {"root": "repo", "relpath": "docs/receipts/x.json", "sha256": "a" * 64}
            ]
        },
    )
    with pytest.raises(ConfigError, match="preparation_source_receipts"):
        compose(tmp_path, "m", "d", "b", "e")


@pytest.mark.parametrize("root", ["repository", "data"])
def test_preparation_source_receipts_accepted_roots_compose_cleanly(tmp_path, root):
    _write_fragments(
        tmp_path,
        experiment_extra={
            "preparation_source_receipts": [
                {"root": root, "relpath": "docs/receipts/x.json", "sha256": "a" * 64}
            ]
        },
    )
    composed = compose(tmp_path, "m", "d", "b", "e")
    assert composed.values["preparation_source_receipts"][0]["root"] == root


@pytest.mark.parametrize(
    "receipts",
    [
        [],  # empty list
        [{"root": "repository", "relpath": "x.json"}],  # missing sha256
        [{"root": "repository", "relpath": "x.json", "sha256": "a" * 64, "extra": 1}],
        [{"root": "repository", "relpath": "x.json", "sha256": "not-hex"}],
        [{"root": "repository", "relpath": "", "sha256": "a" * 64}],
        "not-a-list",
    ],
)
def test_preparation_source_receipts_malformed_pins_are_refused(tmp_path, receipts):
    _write_fragments(
        tmp_path, experiment_extra={"preparation_source_receipts": receipts}
    )
    with pytest.raises(ConfigError, match="preparation_source_receipts"):
        compose(tmp_path, "m", "d", "b", "e")


def test_preparation_source_receipts_absent_key_is_a_noop():
    # No key at all: legacy fragments that never declared a receipt compose
    # exactly as before.
    assert_preparation_source_receipts_are_well_formed({})


def test_the_three_fixed_e3_fragments_pass_the_compose_time_validator():
    """Regression proof, on the real repository bytes: the three fragments
    this defect names (configs/baseline/slurp-native-dual-store-train-fold-
    a-exemplars-k20{,-twin}-v1.json, -k12-v1.json) now pin "repository", not
    "repo", and pass the validator that would otherwise refuse them at
    compose() time."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    for name in (
        "slurp-native-dual-store-train-fold-a-exemplars-k20-v1.json",
        "slurp-native-dual-store-train-fold-a-exemplars-k20-twin-v1.json",
        "slurp-native-dual-store-train-fold-a-exemplars-k12-v1.json",
    ):
        document = json.loads(
            (REPO_ROOT / "configs" / "baseline" / name).read_text(encoding="utf-8")
        )
        receipts = document["preparation_source_receipts"]
        assert all(pin["root"] != "repo" for pin in receipts)
        assert_preparation_source_receipts_are_well_formed(document)


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


def test_dev500_confirmatory_prompt_fit_receipt_certifies_all_four_arms():
    """The executed four-arm prompt-fit receipt (model-free row
    SAEA-SN-MF-DEV500-CONFIRMATORY-PROMPT-FIT-NP8) is bound to the SAME
    composition the previous test pins, and every arm's worst envelope fits
    one 8,192-token slot of the np8 BASE service after the 64-token
    completion reserve. The ABL bounds are conservative production-function
    renderings (no launcher renderer exists yet); the flown ABL
    constructions must stay inside these volumes or the fit is re-run --
    this test keeps that contract from being quietly forgotten."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64",
        "slurp-speech-native-dev500",
        "slurp-dev500-kb-alpha-blend",
        "slurp-dev500-confirmatory-campaign-v1",
    )
    prompt_fit = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "checks"
            / "speech-aware-evidence-acquisition"
            / "2026-08-24-dev500-confirmatory-prompt-fit"
            / "prompt-fit.json"
        ).read_text(encoding="utf-8")
    )

    assert prompt_fit["model_contact"] is False
    assert prompt_fit["config_hash"] == composed.config_hash
    assert prompt_fit["exposure_run_id"] == (
        "SAEA-SN-MF-DEV500-CONFIRMATORY-PROMPT-FIT-NP8"
    )
    assert prompt_fit["knowledge_snapshot_sha256"] == (
        composed.values["dev500_knowledge_snapshot"]["snapshot_sha256"]
    )
    assert prompt_fit["prompt_order"] == composed.values["prompt_order"]
    # The DEV-100 campaign's certified template, byte-equal across the rows.
    assert prompt_fit["tokenizer"]["chat_template_sha256"] == (
        "45777d2e798aae1d1ce6844e69edcb23fc0c710009554711c78efab9044da2c8"
    )

    context_per_slot = 65536 // composed.values["profile_slot_count"]
    assert prompt_fit["context_tokens_per_slot"] == context_per_slot == 8192
    assert prompt_fit["maximum_completion_tokens"] == (
        composed.values["decoding_params"]["max_tokens"]
    )

    by_envelope = {row["envelope_id"]: row for row in prompt_fit["envelopes"]}
    arm_by_envelope = {
        "direct-decode": "M0",
        "evidence-decode-worst": "BLEND",
        "abl-randret-worst": "ABL-RANDRET",
        "abl-randicl-worst": "ABL-RANDICL",
    }
    assert {row["arm_id"] for row in prompt_fit["envelopes"]} == set(
        arm_by_envelope.values()
    )
    for envelope_id, arm_id in arm_by_envelope.items():
        assert by_envelope[envelope_id]["arm_id"] == arm_id
    assert by_envelope["direct-decode"]["prompt_tokens_upper_bound"] == 1832
    assert by_envelope["evidence-decode-worst"]["prompt_tokens_upper_bound"] == 6187
    assert by_envelope["abl-randret-worst"]["prompt_tokens_upper_bound"] == 6187
    assert by_envelope["abl-randicl-worst"]["prompt_tokens_upper_bound"] == 7234
    # k_worst in the receipt equals the fragment's fusion-knob derivation.
    assert prompt_fit["randicl_k_worst"] == 11
    assert prompt_fit["maximum_speech_feature_tokens"] == 130

    # Every arm fits one slot; the worst is the RANDICL control, and it fits.
    assert prompt_fit["worst_envelope_id"] == "abl-randicl-worst"
    assert prompt_fit["maximum_prompt_tokens_upper_bound"] == 7234
    assert prompt_fit["context_margin_tokens"] == 894
    assert prompt_fit["maximum_prompt_fits_one_slot"] is True
    for row in prompt_fit["envelopes"]:
        assert (
            context_per_slot
            - row["prompt_tokens_upper_bound"]
            - prompt_fit["maximum_completion_tokens"]
            == row["context_margin_tokens"]
            >= 0
        )


# ---------------------------------------------------------------------------
# EXPERIMENT A4 -- the retain-override dispatch variant. Unlike every DEV-100
# composition above, A4 moves NO knob: its single registered variable is a
# DISPATCH RULE implemented launcher-side. That makes two properties uniquely
# load-bearing here, and both are asserted rather than described.
#
# First, the frozen-cell assertion must be EQUAL to
# configs/policy/kb-policy-v1-dev100.json rather than a restatement of it, so
# that a knob move in either place breaks this test. A4's whole claim is
# "nothing but the dispatch rule changed"; if the fragment could drift from
# the policy file, that claim would be unfalsifiable.
#
# Second, the registered prediction, its exposed-data-FIT disclosure and its
# variance-honesty statement are pinned here, because a prediction that can
# be edited after the fact is not a prediction. The band's arithmetic is
# checked for internal consistency too: with the loss side zero BY
# CONSTRUCTION at this bar, the central point must be exactly
# base + recovered.
# ---------------------------------------------------------------------------


def test_dev100_retain_override_a4_composes_on_the_np8_base_service():
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT
    from speech_aware_evidence_acquisition.rails import kb_policy

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64",
        "slurp-speech-native-dev100",
        "slurp-dev100-kb-alpha-blend",
        "slurp-dev100-retain-override-campaign-v1",
    )
    values = composed.values

    assert values["experiment_id"] == "SAEA-DEV100-RETAIN-OVERRIDE"
    assert values["execution_profile"] == "bounded-discovery-probe"

    # DEV-role split identity, load_split convention -- the same population
    # the sealed round-4/round-5 base flew.
    assert values["split_name"] == "DEV-100"
    assert values["split_role"] == "dev"
    assert values["count"] == 100
    assert values["audio_seconds_total"] == 275.700125
    assert values["split_identity_hash"] == (
        "e9a7b7febcf4fe3dc228370f7487e1e75dea3d63d447a07fbfe87c1404e2d853"
    )
    assert values["retain_override_split"]["receipt_integrity_hash"] == (
        "d676d38b4d27b3a136ba2523b96ae3c71ba2b8b436f7712f4f0c976c3ea833e1"
    )
    assert values["speech_packet_promotion_receipt_sha256"] == (
        "8d2dc4dc9056ed604b22cbb66cd46724d3ee0246b6aca5665e6bfaf67cf0503d"
    )

    # The BASE-build np8 serving surface: A4 attaches to the resident service
    # and never launches one, so argv drift is an attachment refusal.
    assert values["runtime_receipt"] == "receipts/runtime-q4km-mmproj-free.json"
    assert values["profile_slot_count"] == 8
    assert values["prompt_order"] == "speech-query-prefix-v2"
    assert values["server_args"] == [
        "-c", "65536", "-np", "8", "-b", "2048", "-ub", "512",
        "-fa", "on", "-ngl", "999", "-ctk", "q8_0", "-ctv", "q8_0",
        "--cache-prompt", "--cache-ram", "0",
        "--no-cache-idle-slots", "--slot-prompt-similarity", "0",
    ]

    # THE FROZEN-CELL ASSERTION, checked AGAINST the policy file.
    frozen_policy = json.loads(
        (REPO_ROOT / "configs" / "policy" / "kb-policy-v1-dev100.json").read_text(
            encoding="utf-8"
        )
    )
    knobs = frozen_policy["knobs"]
    cell = values["retain_override_frozen_cell_assertion"]
    assert cell["alpha"] == knobs["alpha"] == 0.45
    assert cell["tau"] == knobs["tau"] == 0.65
    assert cell["top_k_per_dimension"] == knobs["recall_top_k_per_dimension"] == 5
    assert knobs["fusion"] == {"m": 5, "c": 2, "l": 3}
    assert cell["fusion_m"] == knobs["fusion"]["m"]
    assert cell["fusion_c"] == knobs["fusion"]["c"]
    assert cell["fusion_top_l"] == knobs["fusion"]["l"]
    assert cell["rank_weights"] == knobs["rank_weights"]
    assert cell["prior_source"] == knobs["prior_source"] == "train"
    assert cell["rank_weight_id"] == knobs["rank_weighting"] == "rrf"
    assert cell["label_identity_repair_commit"] == "f1060078"
    # A4 is NOT a width move: the K-WIDEN K1 seal proved width inert, so the
    # cell must be back at 5, not at K1's 8.
    assert cell["top_k_per_dimension"] != 8 and cell["fusion_m"] != 8

    # The C3 policy chain, unchanged from the sealed campaign.
    chain = values["retain_override_policy_chain"]
    assert chain["controller_policy_id"] == kb_policy.CONTROLLER_POLICY_ID
    assert chain["ranker_policy_id"] == kb_policy.RANK_POLICY_ID
    assert chain["fuser_policy_id"] == kb_policy.FUSE_POLICY_ID
    assert chain["agent_executor_id"] == "openjiuwen-workflow-v1"
    assert chain["m11_pair_boundary_stage"] is False

    # The pinned TRAIN snapshot, exactly the KB-BUILD receipt's own hash.
    kb_receipt = json.loads(
        (REPO_ROOT / "docs" / "receipts" / "knowledge" / "slurp-kb-size-full.json").read_text(
            encoding="utf-8"
        )
    )
    assert values["retain_override_knowledge_snapshot"]["snapshot_sha256"] == (
        kb_receipt["snapshot_sha256"]
    )
    assert values["retain_override_knowledge_snapshot"]["source_split"] == "train"

    # THE REGISTERED VARIABLE: the delta bar and the mandatory disagreement
    # condition. The signal's runtime legality is part of the contract.
    trigger = values["retain_override_trigger"]
    assert trigger["formula"] == "delta = cos_top1 - cos_direct"
    assert trigger["delta_bar"] == 0.14
    assert trigger["disagreement_condition"].startswith("MANDATORY")
    assert "ZERO extra frozen-core or tool contacts" in trigger["runtime_legality"]
    assert "no second answering model" in trigger["runtime_legality"]
    # The three degenerate signals the projections ruled out stay ruled out.
    assert set(trigger["rejected_alternatives"]) == {
        "fused_top1_score",
        "fused_top2_margin",
        "cos_top1_alone",
        "raising_alpha_past_0.5",
    }

    # THE REGISTERED PREDICTION, pinned verbatim.
    prediction = values["retain_override_registered_prediction"]
    assert prediction["verbatim"] == (
        "at delta >= 0.14 on DEV-100 r4-basis: 3 triggered, 3 of the 5 "
        "retain-override-loss samples recovered, ZERO correct retains "
        "disturbed (zero-loss by construction of the bar), +3 contacts; "
        "accuracy band pessimistic/central/optimistic = 74.1 / 75.0 / 75.0 "
        "vs the sealed base 72."
    )
    assert prediction["triggered"] == 3
    assert prediction["losses_recovered_of_five"] == 3
    assert prediction["correct_retains_disturbed"] == 0
    assert prediction["extra_frozen_core_contacts"] == 3
    assert prediction["accuracy_band"] == {
        "pessimistic": 74.1,
        "central": 75.0,
        "optimistic": 75.0,
    }
    assert prediction["absolute_bounds"] == [72, 75]
    assert prediction["named_samples_r4"] == ["002814", "010037", "011819"]
    assert prediction["named_samples_r5_additional"] == ["012045"]
    assert prediction["out_of_reach_at_any_usable_bar"] == ["014125"]
    # Internal consistency: with the loss side zero BY CONSTRUCTION, the
    # central point is exactly base + recovered, and that is also the ceiling.
    base = 72
    assert prediction["accuracy_band"]["central"] == float(
        base + prediction["losses_recovered_of_five"]
    )
    assert prediction["absolute_bounds"][1] == base + prediction["losses_recovered_of_five"]
    assert prediction["absolute_bounds"][0] == base

    # THE DISCLOSURE. A bar fitted on exposed data must say so, and must name
    # its own out-of-sample test.
    assert "FIT, NOT VALIDATED" in prediction["exposed_data_fit_disclosure"]
    assert "unexposed 500" in prediction["exposed_data_fit_disclosure"]
    assert "DEV-1000" in prediction["exposed_data_fit_disclosure"]
    assert "JUST OUTSIDE" in prediction["variance_honesty"]
    assert "ZERO BY CONSTRUCTION" in prediction["variance_honesty"]
    # The measured conversion anchors travel with the band they generated.
    anchors = prediction["conversion_anchors_measured"]
    assert anchors["gold_is_fused_top1"] == "108/110 = 98.2 percent"
    assert anchors["gold_absent_from_the_fused_supply"] == "0/67 = 0.0 percent"
    assert len(prediction["falsifiers"]) == 4

    # Arms and ceilings.
    arms = {arm["arm_id"]: arm for arm in values["retain_override_arms"]}
    assert list(arms) == ["M0", "BLEND_OVERRIDE"]
    assert arms["M0"]["contacts_per_sample"] == 0
    assert arms["BLEND_OVERRIDE"]["contacts_per_sample"] == 2
    assert arms["BLEND_OVERRIDE"]["tool_contacts_per_sample"] == 1
    ceilings = values["retain_override_ceilings"]
    assert ceilings["frozen_core_contacts_total"] == 300
    assert ceilings["frozen_core_contacts_per_round"] == 210
    assert ceilings["pinned_tool_embedding_contacts_total"] == 200
    assert ceilings["metered_audio_seconds_total"] == 900
    assert ceilings["gpu_hours_total"] == 0.4
    assert len(ceilings["mandatory_rails"]) == 6
    # The rail that makes the launcher-side implementation auditable: no
    # control-plane file may move, so "the override is branch-only" stays a
    # falsifiable claim about a frozen control plane.
    assert any(
        "rails/" in rail and "core/" in rail and "no file under" in rail
        for rail in ceilings["mandatory_rails"]
    )

    # A4 is ONE round; no ladder, no successor, no intra-round retry.
    stopping = values["retain_override_stopping_rule"]
    assert stopping["hard_cap_rounds"] == 1
    assert "SINGLE registered round" in stopping["one_shot"]
    assert set(stopping) >= {
        "adopt_candidate",
        "falsified",
        "inconclusive",
        "evaluation_moment",
    }

    # Slot geometry: the np8 base service's 8,192-token slots.
    assert 65536 // values["profile_slot_count"] == 8192

    # Record the composed identity so a fragment edit is a visible test move.
    assert composed.config_hash == (
        "10ea2794ddc932692cad3face415a5f7ee42d44ee9c124e751f2c6c602cd0c4c"
    )


def test_dev100_retain_override_a4_reuses_the_standing_r6_prompt_fit_envelope():
    """A4 registers NO fresh prompt-fit row, and this test is what keeps that
    decision honest rather than convenient.

    The claim is narrow and checkable: A4 reverts every knob to the frozen
    width-5 cell, so the evidence-prompt WORST CASE is byte-identical to the
    one the standing session-bound R6 row measured. The supplied-value ceiling
    is fusion_c * fusion_top_l = 6 regardless of anything else, and the flown
    runner renders zero facet representations. The registered override changes
    only WHICH trajectories reach that envelope, never its shape.

    If a later edit widens m, raises c or top_l, or makes the runner render
    facet texts, this test fails and the round must re-measure its fit.
    """

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64",
        "slurp-speech-native-dev100",
        "slurp-dev100-kb-alpha-blend",
        "slurp-dev100-retain-override-campaign-v1",
    )
    values = composed.values
    cell = values["retain_override_frozen_cell_assertion"]

    prompt_fit = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "checks"
            / "speech-aware-evidence-acquisition"
            / "2026-08-24-dev100-c3-prompt-fit-np8-r6"
            / "prompt-fit.json"
        ).read_text(encoding="utf-8")
    )

    assert prompt_fit["model_contact"] is False
    assert prompt_fit["exposure_run_id"] == "SAEA-SN-MF-DEV100-C3-PROMPT-FIT-NP8"
    assert prompt_fit["knowledge_snapshot_sha256"] == (
        values["retain_override_knowledge_snapshot"]["snapshot_sha256"]
    )
    assert prompt_fit["prompt_order"] == values["prompt_order"]

    # The R6 row measured the m=5 material A4 flies: 5 visible key facets and
    # the c*top_l = 6 supplied values.
    assert prompt_fit["visible_key_facets"] == cell["fusion_m"] == 5
    assert prompt_fit["visible_values"] == cell["fusion_c"] * cell["fusion_top_l"] == 6

    # And it fits, with the margin the A4 report cites.
    context_per_slot = 65536 // values["profile_slot_count"]
    assert prompt_fit["context_tokens_per_slot"] == context_per_slot == 8192
    assert prompt_fit["maximum_completion_tokens"] == (
        values["decoding_params"]["max_tokens"]
    )
    assert prompt_fit["worst_envelope_id"] == "evidence-decode-worst"
    assert prompt_fit["maximum_prompt_tokens_upper_bound"] == 6174
    assert prompt_fit["context_margin_tokens"] == 1954
    assert prompt_fit["maximum_prompt_fits_one_slot"] is True
    assert (
        context_per_slot
        - prompt_fit["maximum_prompt_tokens_upper_bound"]
        - prompt_fit["maximum_completion_tokens"]
        == prompt_fit["context_margin_tokens"]
    )

    # The fragment's own precondition text must keep naming the standing row
    # and the receipt-hash condition that binds it.
    precondition = values["retain_override_per_round_discipline"]["prompt_fit_precondition"]
    assert "SAEA-SN-MF-DEV100-C3-PROMPT-FIT-NP8-R6" in precondition
    assert "6,174" in precondition and "8,192" in precondition
    assert "session receipt" in precondition


def test_dev1000_baseline_lock_composes_with_the_v2_candidate_and_the_lock_statistic():
    """The DEV-1000 BASELINE-LOCK campaign -- the ladder's terminal dev tier --
    composes on the resident np8 BASE service, and its scientific contract is
    machine-readable and pinned.

    Five things are locked down here so a later edit cannot move them quietly.

    First, POPULATION IDENTITY by both hash conventions: DEV-1000 itself, the
    nested EXPOSED DEV-500, and the UNEXPOSED-500 statistic population. The
    preregistration section 2 quotes DEV-100's load-split hash for DEV-1000 by
    copy error; the fragment records that erratum explicitly and pins the
    correct value, so the record stays auditable rather than silently
    corrected.

    Second, the v2 LOCK CANDIDATE is pinned and asserted knob-equal to the
    frozen candidate file, with the delta retain-override bar carried
    machine-readably. The bar's exposed-data fit is a REGISTERED DISCLOSURE and
    must remain present in the fragment.

    Third, the two preregistered arms (M0 / BLEND) and their worst-case contact
    budgets, plus the explicit statement that BOTH fly the full 1,000 -- the
    lock statistic's partition belongs to the separately registered one-touch
    read, never to flight time.

    Fourth, the LOCK STATISTIC: population, paired statistic, bootstrap spec,
    McNemar, and the preregistered lock condition, which is strictly stronger
    than "excludes zero" (90 percent CI lower bound >= +10 pp) and carries the
    CONFIRMED-BUT-SHRUNKEN branch that does NOT lock.

    Fifth, the section-4 ceilings and the DEV-1000 promotion receipt (1,000
    packets) by absolute path and file hash.
    """

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64",
        "slurp-speech-native-dev1000",
        "slurp-dev1000-kb-alpha-blend",
        "slurp-dev1000-baseline-lock-v1",
    )
    values = composed.values

    assert values["experiment_id"] == "SAEA-DEV1000-BASELINE-LOCK"
    assert values["execution_profile"] == "bounded-discovery-probe"

    # ---- 1. population identity, both conventions ------------------------
    assert values["split_name"] == "DEV-1000"
    assert values["split_role"] == "dev"
    assert values["count"] == 1000
    assert values["audio_seconds_total"] == 2884.7936875
    assert values["split_identity_hash"] == (
        "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84"
    )
    split_block = values["dev1000_split"]
    assert split_block["receipt_integrity_hash"] == (
        "9fb44e3384b8ad8e0d8f825b88eb0a3051c218b699975051d8a0481aabc0243b"
    )
    # The erratum is recorded, not silently repaired.
    erratum = split_block["preregistration_hash_erratum"]
    assert "e9a7b7fe" in erratum and "8580d199" in erratum
    assert "copy error" in erratum
    assert "moves no sample" in erratum.lower()

    nested = split_block["nested_exposed_subset"]
    assert nested["count"] == 500
    assert nested["split_identity_hash"] == (
        "a00f8c8615ea9508a812f93117b9838f2a1a84ec2b3f06c07edc28b04da6acf4"
    )
    assert "never pooled" in nested["exposure"]

    unexposed = split_block["unexposed_statistic_population"]
    assert unexposed["count"] == 500
    assert unexposed["audio_seconds_total"] == 1462.712
    assert unexposed["split_identity_hash"] == (
        "48a96f6fcb9cc391dd776aededa9c27ec4e89195b06a656ae68e814948416ecd"
    )
    assert unexposed["receipt_integrity_hash"] == (
        "1d6d4ba61028c36f22f03de87d48afebeda1b53bd3b32b1a001e117068ddc66d"
    )
    # The nested + unexposed counts must exhaust the tier.
    assert nested["count"] + unexposed["count"] == values["count"] == 1000
    # The id-field convention is the A4 lesson, recorded so a later reader
    # cannot repeat the empty-intersection bug.
    assert "id" in unexposed["id_field_convention"]
    assert "empty intersection" in unexposed["id_field_convention"]
    assert unexposed["flight_time_use"].startswith("NONE")

    # The receipts on disk must actually carry those hashes and partition.
    dev1000_receipt = json.loads(
        (REPO_ROOT / "docs" / "receipts" / "probe-samples" / "DEV-1000.json").read_text(
            encoding="utf-8"
        )
    )
    dev500_receipt = json.loads(
        (REPO_ROOT / "docs" / "receipts" / "probe-samples" / "DEV-500.json").read_text(
            encoding="utf-8"
        )
    )
    new500_receipt = json.loads(
        (
            REPO_ROOT / "docs" / "receipts" / "probe-samples" / "DEV-1000-NEW500.json"
        ).read_text(encoding="utf-8")
    )
    assert dev1000_receipt["run_identity_hash"] == values["split_identity_hash"]
    assert dev1000_receipt["split_identity_hash"] == split_block["receipt_integrity_hash"]
    assert new500_receipt["run_identity_hash"] == unexposed["split_identity_hash"]
    dev1000_ids = {item["id"] for item in dev1000_receipt["items"]}
    dev500_ids = {item["id"] for item in dev500_receipt["items"]}
    new500_ids = {item["id"] for item in new500_receipt["items"]}
    assert len(dev1000_ids) == 1000 and len(dev500_ids) == 500 and len(new500_ids) == 500
    assert new500_ids == dev1000_ids - dev500_ids
    assert not (new500_ids & dev500_ids)
    assert new500_ids | dev500_ids == dev1000_ids

    # ---- 2. the v2 lock candidate ----------------------------------------
    candidate = values["dev1000_lock_candidate"]
    candidate_path = REPO_ROOT / "configs" / "policy" / "kb-policy-v2-lock-candidate.json"
    assert candidate["policy_config"] == "configs/policy/kb-policy-v2-lock-candidate.json"
    candidate_file = json.loads(candidate_path.read_text(encoding="utf-8"))
    # The fragment restates the candidate's knobs; they must EQUAL the file.
    assert candidate["knobs"] == candidate_file["knobs"]
    knobs = candidate["knobs"]
    assert knobs["alpha"] == 0.45
    assert knobs["tau"] == 0.65
    assert knobs["fusion"] == {"m": 5, "c": 2, "l": 3}
    assert knobs["prior_source"] == "train"
    assert knobs["retain_override"]["bar"] == 0.14
    # v2 supersedes v1, and the v1 knobs are byte-carried apart from the
    # override -- the override adds a key, it does not move a knob.
    v1 = json.loads(
        (REPO_ROOT / "configs" / "policy" / "kb-policy-v1-dev100.json").read_text(
            encoding="utf-8"
        )
    )
    assert candidate["supersedes"] == "configs/policy/kb-policy-v1-dev100.json"
    assert candidate_file["supersedes"] == "configs/policy/kb-policy-v1-dev100.json"
    for shared in (
        "alpha",
        "tau",
        "recall_top_k_per_dimension",
        "rank_weighting",
        "rank_weights",
        "fusion",
        "prior_source",
    ):
        assert knobs[shared] == v1["knobs"][shared], shared
    assert set(knobs) - set(v1["knobs"]) == {"retain_override"}

    # The exposed-data fit is a REGISTERED disclosure; it must not vanish.
    disclosure = candidate["delta_bar_fit_on_exposed_data_disclosure"]
    assert "FIT on EXPOSED data" in disclosure
    assert "DEV-500 NEW400" in disclosure
    assert "voids this lock registration" in disclosure
    assert candidate["branch_only_property"].startswith("recall, rank and fuse")
    assert "rails/" in candidate["implementation_boundary"]

    # ---- 3. the two arms, both flying the full tier ----------------------
    arms = {arm["arm_id"]: arm for arm in values["dev1000_arms"]}
    assert list(arms) == ["M0", "BLEND"]
    assert arms["M0"]["contacts_per_sample"] == 1
    assert arms["M0"]["worst_case_frozen_core_contacts"] == 1000
    assert arms["BLEND"]["contacts_per_sample"] == 2
    assert arms["BLEND"]["tool_contacts_per_sample"] == 1
    assert arms["BLEND"]["worst_case_frozen_core_contacts"] == 2000
    for arm in arms.values():
        assert arm["flown_population"] == "DEV-1000 (all 1,000)"
    # Ablations are explicitly NOT re-run at this tier.
    assert values["dev1000_ablations_not_rerun"]["rule"] == (
        "ablations are NOT re-run at this tier"
    )
    assert "SCALE-STABILITY" in values["dev1000_ablations_not_rerun"]["rationale"]

    # ---- 4. the lock statistic and its preregistered condition -----------
    statistic = values["dev1000_lock_statistic"]
    assert statistic["population"] == (
        "the 500 unexposed samples only (DEV-1000 minus DEV-500)"
    )
    assert statistic["population_count"] == unexposed["count"] == 500
    assert statistic["statistic"] == "paired per-sample BLEND minus M0"
    assert statistic["bootstrap"] == {
        "kind": "paired cluster bootstrap",
        "n_replicates": 10000,
        "seed": 20260807,
        "confidence_levels": [0.9, 0.95],
    }
    assert statistic["mcnemar_exact_on_discordant_pairs"] is True
    # STRICTLY STRONGER than the DEV-500 condition: not "excludes zero".
    assert statistic["lock_condition_pp"] == 10.0
    assert statistic["lock_condition"] == (
        "the 90 percent CI lower bound is at least +10 pp"
    )
    assert "excludes zero" not in statistic["lock_condition"]
    assert "does NOT lock" in statistic["confirmed_but_shrunken"]
    assert "returns the program to iteration" in statistic["confirmed_but_shrunken"]
    assert any(
        "exposed-500" in line and "never pooled" in line
        for line in statistic["reported_alongside"]
    )

    # One-touch discipline, and the flight row's own scope limit.
    assert "ONE registered read" in values["dev1000_one_touch"]["rule"]
    scope = values["dev1000_one_touch"]["flight_row_scope"]
    assert "MECHANICAL landing ONLY" in scope
    assert "own registered read row" in scope

    # ---- 5. ceilings and the promotion receipt ---------------------------
    ceilings = values["dev1000_ceilings"]
    assert ceilings["frozen_core_contacts_total"] == 3400
    assert ceilings["pinned_tool_embedding_contacts_total"] == 1200
    assert ceilings["metered_audio_seconds_total"] == 9000
    assert ceilings["gpu_hours_total"] == 3.0
    assert len(ceilings["mandatory_rails"]) == 6
    # The worst case the launcher computes must fit the cells it declares.
    assert (
        arms["M0"]["worst_case_frozen_core_contacts"]
        + arms["BLEND"]["worst_case_frozen_core_contacts"]
        <= ceilings["frozen_core_contacts_total"]
    )
    assert 3 * values["audio_seconds_total"] <= ceilings["metered_audio_seconds_total"]
    assert "RUN-CUMULATIVE" in ceilings["one_shot_semantics"]

    assert values["speech_packet_promotion_receipt"].endswith("/DEV-1000-promotion.json")
    assert values["speech_packet_promotion_receipt_sha256"] == (
        "2accbdc5a2f39fa650218928f92ab7b304717e108646c78051f8c203426a8fe6"
    )

    # ---- serving surface: the resident np8 BASE service, unchanged -------
    assert values["runtime_receipt"] == "receipts/runtime-q4km-mmproj-free.json"
    assert values["profile_slot_count"] == 8
    assert 65536 // values["profile_slot_count"] == 8192
    assert values["prompt_order"] == "speech-query-prefix-v2"
    assert values["server_args"] == [
        "-c", "65536", "-np", "8", "-b", "2048", "-ub", "512",
        "-fa", "on", "-ngl", "999", "-ctk", "q8_0", "-ctv", "q8_0",
        "--cache-prompt", "--cache-ram", "0",
        "--no-cache-idle-slots", "--slot-prompt-similarity", "0",
    ]

    # The pinned TRAIN snapshot, exactly the KB-BUILD receipt's own hash.
    kb_receipt = json.loads(
        (REPO_ROOT / "docs" / "receipts" / "knowledge" / "slurp-kb-size-full.json").read_text(
            encoding="utf-8"
        )
    )
    assert values["dev1000_knowledge_snapshot"]["snapshot_sha256"] == (
        kb_receipt["snapshot_sha256"]
    )
    assert values["dev1000_knowledge_snapshot"]["source_split"] == "train"

    # Record the composed identity so a fragment edit is a visible test move.
    assert composed.config_hash == (
        "b94f81a6140467e861885167fa4f5ff0832e79d4fe5830d3e9fa9a0eb6986ab5"
    )


def test_dev1000_baseline_lock_reuses_the_standing_r6_prompt_fit_envelope():
    """The lock arms carry NO new prompt-fit measurement: the delta override
    changes only WHICH trajectories dispatch, never the prompt SHAPE, and M0
    carries no evidence slot at all. So the standing session-bound row
    SAEA-SN-MF-DEV100-C3-PROMPT-FIT-NP8-R6 binds both arms, and its
    precondition is a session-receipt hash equality asserted before takeoff.

    This test keeps the fragment honest about WHY the standing fit applies:
    the supplied-value ceiling stays c*top_l, the runner renders zero facet
    representations, and the envelope the R6 row measured is therefore the
    worst case BLEND(v2) can reach.
    """

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64",
        "slurp-speech-native-dev1000",
        "slurp-dev1000-kb-alpha-blend",
        "slurp-dev1000-baseline-lock-v1",
    )
    values = composed.values

    precondition = values["dev1000_per_arm_discipline"]["prompt_fit_precondition"]
    assert "SAEA-SN-MF-DEV100-C3-PROMPT-FIT-NP8-R6" in precondition
    assert "6,174" in precondition and "8,192" in precondition
    assert "+1,954" in precondition
    assert "session receipt" in precondition
    # The load-bearing reason, stated: the override moves dispatch, not shape.
    assert "never its shape" in precondition
    assert "ZERO facet representations" in precondition
    # And the fail-closed consequence, stated.
    assert "MF row" in precondition and "re-measure" in precondition
    assert "negative margin STOPS the mission" in precondition

    # The envelope arithmetic the standing row measured must still close
    # against this composition's own slot geometry and completion reserve.
    knobs = values["dev1000_lock_candidate"]["knobs"]
    assert knobs["fusion"]["c"] * knobs["fusion"]["l"] == 6
    assert knobs["fusion"]["m"] == 5
    context_per_slot = 65536 // values["profile_slot_count"]
    assert context_per_slot - 6174 - values["decoding_params"]["max_tokens"] == 1954

    # The resend/canary discipline the row inherits.
    discipline = values["dev1000_per_arm_discipline"]
    assert discipline["record_server_np"] is True
    assert discipline["record_identical_prompt_resend_pair"] is True


def test_a2t_g1_fragments_compose_and_carry_the_derived_serving_geometry():
    """Audio2Tool stage G1: the four committed fragments compose, the policy
    cell is the byte-identical locked v1 cell, and the serving geometry the
    composition declares is the OUTPUT of the campaign plan's section 8.1
    derivation rule -- slot width clears the measured worst-case envelope plus
    the speech allowance plus the derived output ceiling, with the margin the
    fragment states."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np2-a2t-max1024",
        "audio2tool-g1-104",
        "a2t-g1-kb-alpha-blend",
        "a2t-g1-v1",
    )
    values = composed.values
    assert values["experiment_id"] == "SAEA-A2T-G1"
    assert values["execution_profile"] == "bounded-discovery-probe"
    assert values["carrier_lock_key"] == "audio2tool"

    # The derived geometry, and it must clear its own stated requirement.
    args = list(values["server_args"])
    context_total = int(args[args.index("-c") + 1])
    parallel = int(args[args.index("-np") + 1])
    assert (context_total, parallel) == (65536, 2)
    assert values["profile_slot_count"] == 2
    per_slot = context_total // parallel
    assert per_slot == 32768
    output_ceiling = int(values["decoding_params"]["max_tokens"])
    assert output_ceiling == 1024

    derivation = values["a2t_g1_serving_geometry_derivation"]
    envelopes = derivation["step_1_measured_envelopes"]
    worst = int(envelopes["blend_evidence_decode_worst_text_tokens"])
    speech = int(envelopes["speech_allowance_tokens"])
    assert int(envelopes["m0_direct_decode_text_tokens"]) == 13236
    assert worst == 19047
    slot = derivation["step_3_slot_width"]
    assert slot["tokens_per_slot"] == per_slot
    assert slot["parallel_slots"] == parallel
    assert slot["context_total"] == context_total
    # The requirement and margin the fragment states are ARITHMETIC, not prose.
    assert slot["requirement_worst_case"] == worst + speech + output_ceiling
    assert slot["margin_tokens"] == per_slot - slot["requirement_worst_case"]
    assert slot["margin_tokens"] > 0
    # np3 is the smallest that clears at all, and it clears by far less.
    smallest = int(slot["smallest_clearing_np"])
    assert smallest == 3
    assert context_total // smallest > slot["requirement_worst_case"]
    assert context_total // (smallest + 1) < slot["requirement_worst_case"]
    assert slot["smallest_clearing_np_margin"] == (
        context_total // smallest - slot["requirement_worst_case"]
    )
    assert int(derivation["step_2_output_ceiling"]["value"]) == output_ceiling

    # Amendment 2 framing: derived by a rule, not a disclosed exception.
    claim = values["a2t_g1_claim"]
    assert "BYTE-IDENTICAL" in claim["policy_cell"]
    assert "DERIVED PER CARRIER" in claim["serving_geometry"].upper()
    assert "not a degree of freedom" in claim["serving_geometry"]


def test_a2t_g1_policy_cell_is_the_byte_identical_locked_v1_cell():
    """The G1 experiment fragment's knob table must equal the committed v1
    policy cell's own knob table, key for key -- the transfer claim in code."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np2-a2t-max1024",
        "audio2tool-g1-104",
        "a2t-g1-kb-alpha-blend",
        "a2t-g1-v1",
    )
    fragment_knobs = composed.values["a2t_g1_policy_cell"]["knobs"]
    cell_path = REPO_ROOT / "configs" / "policy" / "kb-policy-v1-dev100.json"
    cell_knobs = json.loads(cell_path.read_text(encoding="utf-8"))["knobs"]
    assert fragment_knobs == cell_knobs
    assert fragment_knobs["alpha"] == 0.45
    assert fragment_knobs["tau"] == 0.65
    assert fragment_knobs["recall_top_k_per_dimension"] == 5
    assert fragment_knobs["fusion"] == {"m": 5, "c": 2, "l": 3}
    assert fragment_knobs["percept_admission"] == "facet-side (value vectors sealed)"
    # The v2 delta retain-override is explicitly NOT carried onto this carrier.
    assert "retain_override" not in fragment_knobs
    assert "NOT CARRIED" in composed.values["a2t_g1_policy_cell"]["delta_retain_override"]


def test_a2t_g1_split_pins_agree_across_the_fragments_and_the_receipt():
    """Both hash conventions, the count and the audio total must agree between
    the dataset fragment, the experiment fragment and the committed subset
    receipt; and the subset must be a subset of the frozen exposed 400 when
    compared on sample_id (comparing on the receipt's carrier-prefixed key
    field silently yields an empty intersection)."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np2-a2t-max1024",
        "audio2tool-g1-104",
        "a2t-g1-kb-alpha-blend",
        "a2t-g1-v1",
    )
    values = composed.values
    receipt = json.loads(
        (REPO_ROOT / "docs" / "receipts" / "a2t" / "A2T-G1-104.json").read_text(
            encoding="utf-8"
        )
    )
    split = values["a2t_g1_split"]
    assert values["a2t_g1_split_identity_hash"] == receipt["split_identity_hash"]
    assert values["a2t_g1_run_identity_hash"] == receipt["run_identity_hash"]
    assert split["split_identity_hash"] == receipt["split_identity_hash"]
    assert split["run_identity_hash"] == receipt["run_identity_hash"]
    assert values["a2t_g1_count"] == receipt["count"] == 104
    assert split["count"] == 104
    assert abs(values["a2t_g1_audio_seconds_total"] - receipt["audio_seconds_total"]) < 1e-6
    assert set(receipt["strata_counts"].values()) == {13}
    assert len(receipt["strata_counts"]) == 8

    parent = json.loads(
        (
            REPO_ROOT / "docs" / "receipts" / "probe-samples" / "r1-audio2tool-sample.json"
        ).read_text(encoding="utf-8")
    )
    parent_ids = {
        "%s:%06d" % (item["tier"], int(item["id"])) for item in parent["items"]
    }
    subset_ids = {item["sample_id"] for item in receipt["items"]}
    assert len(parent_ids) == 400
    assert subset_ids <= parent_ids
    assert receipt["parent_split_identity_hash"] == parent["split_identity_hash"]
    # The exposure disclosure must survive: this tier is never the claim.
    assert "EXPOSED" in split["exposure"]
    assert "SECONDARY" in split["exposure"]


def test_a2t_g1_ceilings_cover_the_worst_case_flight_chain():
    """The registered ceilings must cover the run-cumulative worst case of the
    two-arm chain computed from the pinned subset, and the packet promotion
    receipt the baseline pins must be the one the preprocess row landed."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np2-a2t-max1024",
        "audio2tool-g1-104",
        "a2t-g1-kb-alpha-blend",
        "a2t-g1-v1",
    )
    values = composed.values
    ceilings = values["a2t_g1_ceilings"]
    count = int(values["a2t_g1_count"])
    # canary pair, allowed one re-run, plus the loop, plus the BLEND resend
    m0_worst = 2 * 2 + count * 1
    blend_worst = 2 * 2 + count * 2 + 1
    assert m0_worst + blend_worst <= ceilings["frozen_core_contacts_total"]
    assert count + 2 <= ceilings["pinned_tool_embedding_contacts_total"]
    audio = float(values["a2t_g1_audio_seconds_total"])
    assert audio * 3 < ceilings["metered_audio_seconds_total"]
    assert ceilings["gpu_hours_total"] == 0.6

    # The canary gate's semantics must stay stated: per-token, not wall time.
    rails = " ".join(ceilings["mandatory_rails"])
    assert "PER-TOKEN rate, not wall time" in rails
    assert "canary hash authority" in rails
    assert "OWN" in rails

    # The packet prerequisite is pinned by hash in two independent places.
    assert values["speech_packet_promotion_receipt_sha256"] == (
        values["a2t_g1_serving_geometry_derivation"]["step_5_packet_prerequisite"][
            "promotion_receipt_sha256"
        ]
    )
    assert values["speech_packet_promotion_receipt"].endswith(
        "A2T-G1-104-promotion.json"
    )


def test_a2t_g1_preprocess_fragments_compose_and_keep_the_gpu_decoder_out():
    """The label-free preprocessing composition must be CPU-only, must write
    into a build-scoped legacy cache separate from the older A2T cache, and
    must say so."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-preprocess-featcache-cpu-sidecar-a2t",
        "audio2tool-g1-104",
        "speech-native-preprocess",
        "a2t-g1-preprocess",
    )
    values = composed.values
    assert values["experiment_id"] == "SAEA-SN-A2T-G1-PREPROCESS"
    args = list(values["server_args"])
    assert args[args.index("-ngl") + 1] == "0"
    assert "--no-mmproj-offload" in args
    assert values["base_url"].endswith(":8081")
    assert values["runtime_receipt"] == "receipts/runtime-q4km-preprocess.json"
    assert values["decoding_params"]["max_tokens"] == 1
    cache = values["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"]
    assert cache == "/home/chao/feat-cache/audio2tool-q4km-04ccc72a"
    assert cache != "/home/chao/feat-cache/audio2tool-q4km"
    scope = values["a2t_g1_preprocess_scope"]
    assert scope["legacy_cache_dir"] == cache
    assert scope["count"] == 104
    assert "5d9dfcb5" in values["purpose"]
    assert "load_slurp_engineering_gate" in scope["promotion_path"]


def test_a2t_cpv2_preprocess_is_receipt_bound_and_cpu_only():
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-preprocess-featcache-cpu-sidecar-a2t",
        "audio2tool-cpv2-104",
        "speech-native-preprocess",
        "a2t-cpv2-preprocess",
    )
    values = composed.values
    assert values["experiment_id"] == "SAEA-SN-A2T-CPV2-PREPROCESS"
    args = list(values["server_args"])
    assert args[args.index("-ngl") + 1] == "0"
    assert "--no-mmproj-offload" in args
    assert values["base_url"].endswith(":8081")
    assert values["decoding_params"]["max_tokens"] == 1
    scope = values["a2t_cpv2_preprocess_scope"]
    assert scope["subset_receipt"] == "docs/receipts/a2t/A2T-CPV2-104.json"
    assert scope["count"] == 104
    assert scope["audio_seconds_total"] == 536.05
    assert scope["promotion_receipt"].endswith(
        "A2T-CPV2-104-promotion.json"
    )


def test_a2t_cpv2_main_fragments_bind_packets_prompt_fit_and_agentloop():
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q4km-mmproj-free-speech-native-np2-a2t-max1024",
        "audio2tool-cpv2-104",
        "a2t-contract-preserving-cascade-agentloop",
        "a2t-training-free-contract-preserving-cascade-104-v2",
    )
    values = composed.values
    assert values["experiment_id"] == (
        "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2"
    )
    assert values["arm"] == "speech-feature-query"
    assert values["speech_native_agent_executor_id"] == "openjiuwen-workflow-v1"
    assert values["speech_packet_promotion_receipt"].endswith(
        "A2T-CPV2-104-promotion.json"
    )
    assert values["speech_packet_promotion_receipt_sha256"] == (
        "a9ae338fbc9ba4734553b97a417403923aa6e085d3bd4446848a2abff3b65c87"
    )
    assert values["speech_native_prompt_fit_receipt_sha256"] == (
        "9b6b8464926af01b33bdd6f1f5360eb6623702033e217491b26141b3f947d5df"
    )
    assert values["profile_slot_count"] == 2
