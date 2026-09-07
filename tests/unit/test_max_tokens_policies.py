"""Unit tests for ``core.base.MAX_TOKENS_POLICIES`` and its one registered
entry, ``core.policies.DurationProportionalMaxTokens`` (E22 cell (b), the
duration-proportional generation cap of ``docs/readiness/
2026-09-06-e22-dev-usage-cells-v1-preregistration.md`` section 2.1).

No model, GPU, server or network contact anywhere in this file: the policy is
arithmetic over one float.
"""

from __future__ import annotations

import math

import pytest

from speech_aware_evidence_acquisition.analysis.e22_overgeneration import cap_tokens
from speech_aware_evidence_acquisition.core.base import CoreError, MAX_TOKENS_POLICIES
from speech_aware_evidence_acquisition.core.policies import (
    DURATION_PROPORTIONAL_MAX_TOKENS_V1,
)

# The two constants the over-generation analysis measured on the sealed dev
# population and committed to
# docs/checks/.../2026-09-06-e22-overgeneration-analysis/summary.json. Cell (b)
# flies them at alpha 1.5.
WPS_P95 = 4.999220954734555
TOKENS_PER_WORD = 1.2991996296395218
ALPHA = 1.5

RULE = {
    "policy": DURATION_PROPORTIONAL_MAX_TOKENS_V1,
    "alpha": ALPHA,
    "words_per_second_p95": WPS_P95,
    "tokens_per_word": TOKENS_PER_WORD,
    "floor": 1,
    "ceiling": 1024,
}


def _policy():
    return MAX_TOKENS_POLICIES.resolve(DURATION_PROPORTIONAL_MAX_TOKENS_V1)


def test_the_policy_id_resolves_in_the_core_base_registry():
    """Owner rule 2026-09-03: every component id a config declares resolves in
    a ``core.base`` registry. ``scripts/checks/engineering_base_check.py`` reads
    exactly this registration out of ``core/policies.py``."""

    assert DURATION_PROPORTIONAL_MAX_TOKENS_V1 in MAX_TOKENS_POLICIES.names()
    assert _policy() is not None


def test_resolution_equals_the_over_generation_simulator_row_for_row():
    """The cell measures a cap whose payoff a model-free simulator already
    projected. If the two disagree on one row, the prediction check of section
    4 compares two different interventions."""

    policy = _policy()
    seconds = [
        0.219938,  # this subset's shortest utterance
        0.5,
        1.0,
        5.0,
        10.0,
        32.88,  # this subset's longest utterance
        78.36,  # the full dev10's longest, above this subset's range
        200.0,
    ]
    for value in seconds:
        expected = min(1024, max(1, cap_tokens(ALPHA, value, WPS_P95, TOKENS_PER_WORD)))
        assert policy.resolve(RULE, value) == expected


def test_the_published_ladder_of_section_2_1_reproduces():
    """The four caps the preregistration wrote down before any capped request
    existed: 10 tokens for 1 s, 49 for 5 s, 98 for 10 s, 321 for 32.88 s."""

    policy = _policy()
    assert policy.resolve(RULE, 1.0) == 10
    assert policy.resolve(RULE, 5.0) == 49
    assert policy.resolve(RULE, 10.0) == 98
    assert policy.resolve(RULE, 32.88) == 321


def test_every_resolved_cap_is_a_tightening_never_a_loosening():
    """Section 2.1: at alpha 1.5 the cap is under the sealed arm's own 1,024
    everywhere in this population, so the cell can only shorten a generation."""

    policy = _policy()
    longest = 32.88
    step = 0.01
    value = step
    while value <= longest + 1e-9:
        assert policy.resolve(RULE, value) <= 1024
        value += step
    assert policy.resolve(RULE, longest) < 1024


def test_the_floor_and_the_ceiling_both_clamp():
    policy = _policy()
    floored = dict(RULE, floor=7)
    assert policy.resolve(floored, 0.001) == 7
    capped = dict(RULE, ceiling=32)
    assert policy.resolve(capped, 600.0) == 32
    # And the raw value is what is clamped, not something re-derived: a
    # duration whose raw cap sits between floor and ceiling is untouched.
    assert policy.resolve(dict(RULE, floor=1, ceiling=10_000), 5.0) == cap_tokens(
        ALPHA, 5.0, WPS_P95, TOKENS_PER_WORD
    )


def test_resolution_is_monotone_in_duration():
    policy = _policy()
    caps = [policy.resolve(RULE, seconds) for seconds in (1.0, 2.0, 4.0, 8.0, 16.0)]
    assert caps == sorted(caps)
    assert len(set(caps)) == len(caps)


@pytest.mark.parametrize(
    "mutation",
    [
        {"alpha": None},
        {"alpha": 0},
        {"alpha": -1.0},
        {"alpha": True},
        {"alpha": float("nan")},
        {"words_per_second_p95": "4.9"},
        {"tokens_per_word": 0.0},
        {"floor": 0},
        {"floor": 1.5},
        {"ceiling": True},
    ],
)
def test_a_malformed_parameter_is_refused(mutation):
    policy = _policy()
    with pytest.raises(CoreError):
        policy.parameters(dict(RULE, **mutation))


def test_a_missing_or_extra_parameter_is_refused():
    """Fail-closed in both directions: a missing key is a rule the policy
    cannot evaluate, an extra key is a knob its author believes is honoured."""

    policy = _policy()
    incomplete = {key: value for key, value in RULE.items() if key != "ceiling"}
    with pytest.raises(CoreError, match="missing"):
        policy.parameters(incomplete)
    with pytest.raises(CoreError, match="extra"):
        policy.parameters(dict(RULE, stop="\n"))


def test_a_floor_above_the_ceiling_is_refused():
    policy = _policy()
    with pytest.raises(CoreError, match="exceeds ceiling"):
        policy.parameters(dict(RULE, floor=2048, ceiling=1024))


def test_a_non_mapping_rule_is_refused():
    policy = _policy()
    with pytest.raises(CoreError, match="must be a mapping"):
        policy.parameters(1024)


@pytest.mark.parametrize("seconds", [0, -1.0, None, "8.18", True, math.inf, math.nan])
def test_a_bad_audio_duration_is_refused(seconds):
    """A cap resolved from a missing or malformed duration would be a silent
    default; there is no default here."""

    policy = _policy()
    with pytest.raises(CoreError, match="audio_seconds"):
        policy.resolve(RULE, seconds)
