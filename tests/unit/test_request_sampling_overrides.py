"""Request-scoped complete-episode sampling without service or legacy-cap changes."""

from copy import deepcopy
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import (
    ConfigError,
    compose,
    effective_request_decoding_params,
    effective_request_values,
)
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from test_flight_runtime import (
    _cap_runtime,
    _LegacyWideBudgetFakeAdapter,
    _make_repo,
    _make_runtime,
    _FakeSession,
)
from test_native_episode_runner import _ActualEpisodeHarness
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


SAMPLING = {
    "temperature": 0.7,
    "seed": 2026092601,
    "top_p": 1.0,
    "top_k": 0,
    "min_p": 0.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
}


def test_explicit_sampling_changes_requests_without_mutating_model_values():
    values = {
        "decoding_params": {
            "temperature": 0,
            "seed": 3,
            "max_tokens": 512,
            "id_slot": "per-sample",
        },
        "request_decoding_overrides": SAMPLING,
    }
    before = deepcopy(values)
    decoded = effective_request_decoding_params(values)
    assert decoded == {**values["decoding_params"], **SAMPLING}
    fitted_values = effective_request_values(values)
    assert fitted_values["decoding_params"] == decoded
    assert fitted_values["request_decoding_overrides"] == SAMPLING
    assert fitted_values is not values
    legacy = {"decoding_params": before["decoding_params"]}
    assert effective_request_values(legacy) is legacy
    assert values == before
    assert (
        effective_request_decoding_params(
            {"decoding_params": before["decoding_params"]}
        )
        is before["decoding_params"]
    )


@pytest.mark.parametrize(
    "override",
    [
        {},
        {"server_args": []},
        {"id_slot": 1},
        {"response_format": {}},
        {"temperature": True},
        {"temperature": float("nan")},
        {"temperature": float("inf")},
        {"temperature": -0.1},
        {"temperature": 2.1},
        {"seed": True},
        {"seed": -1},
        {"seed": 1.5},
        {"seed": 2**32},
        {"seed": 2**32 - 1},
        {"top_p": -0.1},
        {"top_p": 1.1},
        {"top_k": -1},
        {"top_k": 1.2},
        {"min_p": True},
        {"min_p": 1.1},
        {"presence_penalty": -2.1},
        {"frequency_penalty": float("nan")},
        {"max_tokens": False},
        {"max_tokens": 0},
    ],
)
def test_malformed_sampling_refuses_before_any_contact(override):
    with pytest.raises(ConfigError, match="request_decoding_overrides"):
        effective_request_decoding_params(
            {
                "decoding_params": {"max_tokens": 512},
                "request_decoding_overrides": override,
            }
        )


def test_sampling_only_override_preserves_legacy_adapter_reserve(tmp_path):
    runtime = _cap_runtime(
        tmp_path,
        64,
        adapter_cls=_LegacyWideBudgetFakeAdapter,
        config_kwargs={
            "arm": "bare-core",
            "policy": "fixed",
            "model_extra": {"decoding_params": {"max_tokens": 64}},
            "experiment_extra": {"request_decoding_overrides": SAMPLING},
        },
    )
    runtime._prepare()
    assert runtime._decoding_params()["temperature"] == 0.7
    assert runtime._completion_token_ceiling() == 512


@pytest.mark.parametrize("seed", [2026092601, 2026092602, 2026092603, 2026092604])
def test_effective_sampling_reaches_all_native_roles_and_revision(tmp_path, seed):
    runtime = object.__new__(FlightRuntime)
    repo = Path(__file__).resolve().parents[2]
    runtime._composed = compose(
        repo,
        "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
        "slurp-speech-native-stage3-construction-r01c",
        "slurp-native-stage3-system-common-r01c-v1",
        f"slurp-native-stage3-system-round1-r01c-s{seed - 2026092600}-v1",
    )
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=11,
        planner_actions=("REVISE", "ACCEPT"),
    )
    try:
        harness.run(decoding_params=runtime._phase_decoding_params())
        assert {key[1] for key in harness.prepared} == {
            "perception",
            "solver",
            "reviewer",
            "planner",
        }
        assert any(key[1] == "solver" and key[2] == 2 for key in harness.prepared)
        assert set(harness.prepared) == set(harness.dispatched)
        for prepared in harness.prepared.values():
            body = prepared["rendered"]
            for key, value in {**SAMPLING, "seed": seed}.items():
                assert body[key] == value
            assert body["max_tokens"] == 512
    finally:
        harness.close()


def test_sampling_replicas_reuse_one_resident_service(tmp_path):
    starts = []

    def start(**kwargs):
        starts.append(kwargs["session_id"])
        return _FakeSession(str(kwargs["session_id"]))

    owner = None
    identities, config_hashes = [], []
    for index, seed in enumerate(range(2026092601, 2026092605)):
        run_id = f"SAEA-SAMPLING-{index}"
        repo = _make_repo(
            tmp_path / str(index),
            run_id,
            model_extra={"decoding_params": {"temperature": 0, "max_tokens": 64}},
            experiment_extra={"request_decoding_overrides": {**SAMPLING, "seed": seed}},
        )
        runtime = _make_runtime(
            tmp_path,
            run_id=run_id,
            attempt_id=f"sampling-{index}",
            happy_path=True,
            repo_root=repo,
            session_starter=start,
        )
        runtime.preflight()
        runtime.preprocess()
        identities.append(runtime.serving_profile_fingerprint())
        config_hashes.append(runtime._composed.config_hash)
        if owner is None:
            runtime.serve()
            owner = runtime
        else:
            assert runtime.serve(reuse=owner)["reused"] is True
    assert len(starts) == 1
    assert len(set(identities)) == 1
    assert len(set(config_hashes)) == 4


@pytest.mark.parametrize(
    "override",
    [
        {
            "temperature": 0,
            "seed": 0,
            "top_p": 0,
            "top_k": 0,
            "min_p": 0,
            "presence_penalty": -2,
            "frequency_penalty": 2,
            "max_tokens": 1,
        },
        {
            "temperature": 2,
            "seed": 2**32 - 2,
            "top_p": 1,
            "top_k": 40,
            "min_p": 1,
            "presence_penalty": 2,
            "frequency_penalty": -2,
        },
    ],
)
def test_sampling_boundary_values_and_absent_base(override):
    assert (
        effective_request_decoding_params({"request_decoding_overrides": override})
        == override
    )


@pytest.mark.parametrize(
    "values",
    [
        {"decoding_params": [], "request_decoding_overrides": {"temperature": 1}},
        {"request_decoding_overrides": []},
    ],
)
def test_invalid_base_or_override_shape_refuses(values):
    with pytest.raises(ConfigError):
        effective_request_decoding_params(values)
