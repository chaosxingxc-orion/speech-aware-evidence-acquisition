"""The v2.0 lock cells PLAN / PLANr (owner decisions 30, 57 option b, 78): the flown baseline IS the default plan.

The harness-admission receipt names ``configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`` as
the SLURP default plan; cell PLAN flies ``configs/baseline/slurp-native-default-plan-lock-baseline-v1.json``, derived
by script from the sealed B1-notool fragment plus the plan's decided keys. This test is the registration's
``contact_free_evidence.proof_test``: the two fragments agree on every key except the per-flight bookkeeping, the
smoke baseline likewise, and (once registered) the PLANr fragment equals PLAN's byte for byte except its own
bookkeeping -- so "the plan flown is the plan locked" is a property of bytes, not of prose.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINES = REPO_ROOT / "configs" / "baseline"
PLAN = BASELINES / "slurp-native-dual-store-train-fold-a-default-plan-v1.json"
FLOWN = BASELINES / "slurp-native-default-plan-lock-baseline-v1.json"
FLOWN_SMOKE = BASELINES / "slurp-native-default-plan-lock-smoke-4-baseline-v1.json"
REPLICATE = BASELINES / "slurp-native-default-plan-lock-replicate-baseline-v1.json"
REPLICATE_SMOKE = BASELINES / "slurp-native-default-plan-lock-replicate-smoke-4-baseline-v1.json"
BASE = BASELINES / "slurp-native-anchor-exemplars-k20-notool-v1.json"

#: Per-flight bookkeeping: the fit receipt, the prepared supply and its provenance, the speech-feature identity ids
#: (each flight prepares its own artifacts under its own run id) and the free-English descriptions.
BOOKKEEPING = frozenset({
    "native_contact_fit",
    "prepared_phase_supply",
    "preparation_source_receipts",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "what_this_is",
    "what_the_train_exemplars_store_is",
})


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _non_bookkeeping_diff(a: dict, b: dict) -> list[str]:
    return sorted(key for key in (set(a) | set(b)) - BOOKKEEPING if a.get(key) != b.get(key))


def test_the_flown_baseline_is_the_default_plan_on_every_decided_key():
    plan, flown = _load(PLAN), _load(FLOWN)
    assert _non_bookkeeping_diff(plan, flown) == []
    assert "phase_tools" not in flown
    assert flown["native_episode"]["deliver_normaliser"] == {"normaliser": "saea-deliver-normalise-v3"}
    assert flown["native_episode"]["review_loop"] == "on"
    assert flown["native_episode"]["finite_completion_policy"] == "deliver-latest-or-abstain"
    assert flown["native_episode"]["react_exhaustion_policy"] == "continue-without-answer"
    assert flown["knowledge_stores"]["slot-contracts"]["release"]["relpath"].endswith("slot-contracts-v2/release.json")
    assert "train-exemplars" in flown["knowledge_stores"]


def test_the_smoke_baseline_carries_the_same_decided_keys():
    plan, smoke = _load(PLAN), _load(FLOWN_SMOKE)
    assert _non_bookkeeping_diff(plan, smoke) == []


def test_the_flown_baseline_moves_exactly_the_plans_decided_keys_against_the_tool_free_base():
    """Against the sealed B1-notool fragment the arm differs in the slot-contract pins, the normaliser node, the
    review-loop marker and the E20 context-fit declaration (compact-or-abstain: the plan's widest Solver request
    exceeds the np4 slot's operational reserve by about 300 tokens with a positive physical margin, so the live fit
    gate compacts only the rows that do not fit and receipts every drop), and in nothing else outside the
    bookkeeping."""
    base, flown = _load(BASE), _load(FLOWN)
    diff = _non_bookkeeping_diff(base, flown)
    assert diff == ["knowledge_stores", "native_episode"]
    store_diff = sorted(
        store for store in set(base["knowledge_stores"]) | set(flown["knowledge_stores"])
        if base["knowledge_stores"].get(store) != flown["knowledge_stores"].get(store)
    )
    assert store_diff == ["slot-contracts"]
    episode_diff = sorted(
        key for key in set(base["native_episode"]) | set(flown["native_episode"])
        if base["native_episode"].get(key) != flown["native_episode"].get(key)
    )
    assert episode_diff == ["context_fit_policy", "deliver_normaliser", "review_loop"]
    assert flown["native_episode"]["context_fit_policy"] == "compact-or-abstain"


@pytest.mark.skipif(not REPLICATE.exists(), reason="cell PLANr is not registered yet")
def test_the_replicate_is_the_plan_arm_byte_for_byte_outside_its_bookkeeping():
    flown, rep = _load(FLOWN), _load(REPLICATE)
    assert _non_bookkeeping_diff(flown, rep) == []
    if REPLICATE_SMOKE.exists():
        assert _non_bookkeeping_diff(_load(FLOWN_SMOKE), _load(REPLICATE_SMOKE)) == []
