"""Raw composed preflight and live dispatch must use the same output ceiling."""
from copy import deepcopy

import pytest

from speech_aware_evidence_acquisition.core.config import ConfigError, effective_request_values
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    _serving_geometry_max_tokens, load_native_episode_config,
)
from test_native_episode_config import config, program


@pytest.mark.parametrize("explicit_geometry", [False, True])
@pytest.mark.parametrize("declared,requested", [(512, 1024), (1024, 256)])
def test_request_cap_override_governs_raw_and_resolved_role_admission(explicit_geometry, declared, requested):
    values = config()
    values["decoding_params"] = {"max_tokens": declared}
    if explicit_geometry:
        values["serving_geometry"] = {"max_tokens": declared}
    values["request_decoding_overrides"] = {"max_tokens": requested}
    values["native_episode"]["roles"]["reviewer"]["max_completion_tokens"] = requested
    before = deepcopy(values)
    raw = load_native_episode_config(values, program())
    resolved = load_native_episode_config(effective_request_values(values), program())
    assert raw == resolved
    assert raw.role("reviewer").max_completion_tokens == requested
    assert values == before
    values["native_episode"]["roles"]["reviewer"]["max_completion_tokens"] = requested + 1
    with pytest.raises(ValueError, match="must not exceed"):
        load_native_episode_config(values, program())


def test_non_capacity_override_preserves_explicit_legacy_geometry():
    values = {"serving_geometry": {"max_tokens": 1024}, "decoding_params": {"max_tokens": 512},
              "request_decoding_overrides": {"seed": 7}}
    assert _serving_geometry_max_tokens(values) == 1024
    assert _serving_geometry_max_tokens({}) is None
    assert _serving_geometry_max_tokens({"decoding_params": {"max_tokens": True}}) is None
    assert _serving_geometry_max_tokens({"decoding_params": {"max_tokens": 512}}) == 512


def test_invalid_request_cap_is_rejected_before_role_or_transport_admission():
    with pytest.raises(ConfigError, match="max_tokens"):
        _serving_geometry_max_tokens({"decoding_params": {"max_tokens": 512},
                                     "request_decoding_overrides": {"max_tokens": True}})
