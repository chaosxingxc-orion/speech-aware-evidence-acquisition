"""Wave-1 substrate-ablation config fragments (A-1a/A-2a/A-3a, docs/readiness/
2026-08-09-exploration-plan.md section 2): every new baseline fragment
composes with the real committed model/dataset/experiment fragments, and each
new arm differs from configs/baseline/bare-core-ojw.json in exactly the
ablated field(s) -- a real set-difference over the raw JSON, not a spot check.

A-2a note: buffer size, min/max/fallback advance are FOUR raw JSON keys, but
one ablated VARIABLE -- the exploration plan explicitly requires scaling
min/max/fallback advance proportionally to buffer size so the contrast tests
buffer size alone, not "buffer size plus a different advance regime". The
per-arm expected-diff sets below encode that: a single key for A-1a/A-3a,
the four-key geometry bundle for A-2a.
"""

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

BASELINE_DIR = Path(REPO_ROOT) / "configs" / "baseline"

NEW_ARM_NAMES = (
    "a1a-fixed-window-ojw",
    "a2a-buffer30-ojw",
    "a2a-buffer90-ojw",
    "a3a-vadtrim-off-ojw",
    "a3a-loudnorm-ojw",
)

# name -> set of top-level keys whose VALUE is expected to differ from
# bare-core-ojw.json (module docstring: A-2a's is a coordinated bundle).
EXPECTED_DIFF_KEYS = {
    "a1a-fixed-window-ojw": {"obs_boundary_mode"},
    "a2a-buffer30-ojw": {
        "obs_buffer_seconds",
        "obs_min_advance_seconds",
        "obs_max_advance_seconds",
        "obs_fallback_advance_seconds",
    },
    "a2a-buffer90-ojw": {
        "obs_buffer_seconds",
        "obs_min_advance_seconds",
        "obs_max_advance_seconds",
        "obs_fallback_advance_seconds",
    },
    "a3a-vadtrim-off-ojw": {"obs_vad_trim_min_seconds"},
    "a3a-loudnorm-ojw": {"obs_preprocess"},
}


def _load_baseline(name: str) -> dict:
    return json.loads((BASELINE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _diff_keys(a: dict, b: dict) -> set:
    """Keys present in both with a differing value, PLUS any key whose mere
    presence/absence differs -- a fragment that adds or drops a key entirely
    is exactly the kind of mistake a spot check would miss."""

    keys = set(a) | set(b)
    return {key for key in keys if a.get(key, object()) != b.get(key, object())}


# ---------------------------------------------------------------------------
# Composition: every new fragment is disjoint-key-compatible with the real
# committed model/dataset/experiment fragments (compose() itself proves
# disjointness; the assertions below pin the values that matter for a
# substrate probe -- see tests/unit/test_config_composition.py's own
# compose-vs-run distinction, repeated here: this proves composition only).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("baseline_name", NEW_ARM_NAMES)
def test_new_arm_composes_with_the_wave1_split(baseline_name):
    composed = compose(REPO_ROOT, "qwen3-omni-llamacpp", "wave1-e21-sub5", baseline_name, "r0-smoke")
    assert composed.values["arm"] == "bare-core"
    assert composed.values["policy"] == "obs-agent-loop-ojw"
    assert composed.values["evidence_source"] == "none"
    assert composed.values["evidence_mismatch"] is False
    assert composed.values["scorers"] == ["asr-wer", "cost"]
    assert composed.values["carrier_lock_key"] == "earnings21-original"
    assert composed.values["split_name"] == "wave1-e21-sub5-sample"
    assert composed.values["model_lock_key"] == "qwen3-omni-30b-a3b-instruct-gguf"


def test_bare_core_ojw_composes_with_the_wave1_split():
    """The A-1a/A-2a control point (buffer 60 s / model-guided boundary) is
    literally bare-core-ojw -- no new fragment -- so it must compose with the
    new dataset split exactly like the new arms do."""

    composed = compose(REPO_ROOT, "qwen3-omni-llamacpp", "wave1-e21-sub5", "bare-core-ojw", "r0-smoke")
    assert composed.values["arm"] == "bare-core"
    assert composed.values["policy"] == "obs-agent-loop-ojw"
    assert composed.values["obs_buffer_seconds"] == 60
    assert composed.values["obs_boundary_mode"] == "model"


# ---------------------------------------------------------------------------
# One-ablated-variable check: real set-difference against bare-core-ojw.json.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("baseline_name", NEW_ARM_NAMES)
def test_new_arm_differs_from_bare_core_ojw_in_exactly_the_ablated_keys(baseline_name):
    bare_core = _load_baseline("bare-core-ojw")
    arm = _load_baseline(baseline_name)
    assert _diff_keys(arm, bare_core) == EXPECTED_DIFF_KEYS[baseline_name]


def test_a2a_geometry_arms_satisfy_the_obs_loop_advance_window_invariant():
    """0 < min <= max <= buffer and min <= fallback <= max -- the exact rule
    ObsLoopConfig.from_values enforces (reproduction/obs_loop.py). Checked
    directly against the invariant here (not by importing obs_loop.py, which
    is off-limits to edit and is exercised end-to-end by
    test_new_arm_composes_with_the_wave1_split already) so a future rescale
    of the geometry constants is caught before a run ever attempts it."""

    for name in ("a2a-buffer30-ojw", "a2a-buffer90-ojw"):
        values = _load_baseline(name)
        buffer_s = values["obs_buffer_seconds"]
        min_adv = values["obs_min_advance_seconds"]
        max_adv = values["obs_max_advance_seconds"]
        fallback = values["obs_fallback_advance_seconds"]
        assert 0 < min_adv <= max_adv <= buffer_s, name
        assert min_adv <= fallback <= max_adv, name


def test_a2a_geometry_is_scaled_proportionally_to_bare_core_ojw():
    """The exploration plan requires the SAME advance/buffer ratios as the
    60 s reference (min_advance 20/60, max_advance 55/60, fallback 50/60) so
    the contrast isolates buffer size -- not a coincidentally-close rescale."""

    reference = _load_baseline("bare-core-ojw")
    ref_buffer = reference["obs_buffer_seconds"]
    ref_ratios = {
        key: reference[key] / ref_buffer
        for key in (
            "obs_min_advance_seconds",
            "obs_max_advance_seconds",
            "obs_fallback_advance_seconds",
        )
    }
    for name in ("a2a-buffer30-ojw", "a2a-buffer90-ojw"):
        values = _load_baseline(name)
        buffer_s = values["obs_buffer_seconds"]
        for key, ratio in ref_ratios.items():
            # Integer-second geometry rounds to the nearest second, so allow
            # the rounding slack (<1 s) rather than demanding exact equality.
            assert abs(values[key] - ratio * buffer_s) < 1.0, (name, key)


def test_wave1_probe_sample_receipt_is_a_verified_probe_split():
    """The receipt built by scripts/build_probe_samples.py's
    build_wave1_e21_sub5() resolves through the same strict-parse +
    hash-verify path (reproduction.probe_split) the driver uses at run time
    -- proves the receipt is not merely well-formed JSON but a genuinely
    consumable split."""

    from speech_aware_evidence_acquisition.reproduction.probe_split import (
        load_verified_probe_split,
    )

    split = load_verified_probe_split(REPO_ROOT, "wave1-e21-sub5-sample")
    assert split.carrier_lock_key == "earnings21-original"
    assert split.split_role == "discovery"
    assert len(split.ids) == 5
    # The frozen 5-of-10 identity (docs/receipts/probe-samples/
    # wave1-e21-sub5-sample.json, seed 20260807): pinned here so a
    # regenerated receipt that silently picks different ids fails loudly.
    assert set(split.ids) == {
        "4330115",
        "4366522",
        "4385072",
        "4387383",
        "4397829",
    }
