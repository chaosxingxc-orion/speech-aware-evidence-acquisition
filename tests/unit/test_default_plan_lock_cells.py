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
B9A = BASELINES / "slurp-native-plan-acquisition-b9a-baseline-v1.json"
B9A_SMOKE = BASELINES / "slurp-native-plan-acquisition-b9a-smoke-4-baseline-v1.json"
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


@pytest.mark.skipif(not B9A.exists(), reason="cell B9a is not registered yet")
def test_b9a_moves_exactly_the_e18_module_against_the_plan():
    """Cell B9a (item E18, decisions 43 / 44 / 78): the locked default plan plus exactly the acquisition module --
    ``native_episode.acquisition`` and ``native_episode.roles.acquisition`` -- and nothing else outside the
    bookkeeping; the contact ceiling is unchanged because kind (a) costs no contact."""
    flown, b9a = _load(FLOWN), _load(B9A)
    assert _non_bookkeeping_diff(flown, b9a) == ["native_episode", "policy"]
    assert b9a["policy"] == "phase-native-candidates-review-revise-acquire-v1"  # item E32: the program with the acquisition phase, ceiling 11
    ne_plan, ne_b9a = flown["native_episode"], b9a["native_episode"]
    episode_diff = sorted(key for key in set(ne_plan) | set(ne_b9a) if ne_plan.get(key) != ne_b9a.get(key))
    assert episode_diff == ["acquisition", "roles"]
    assert ne_b9a["acquisition"] == {"policy": "saea-acquire-knowledge-requery-v1", "budget": {"max_acquisitions_per_row": 1, "contact_budget": 0}}
    roles_diff = sorted(r for r in set(ne_plan["roles"]) | set(ne_b9a["roles"]) if ne_plan["roles"].get(r) != ne_b9a["roles"].get(r))
    assert roles_diff == ["acquisition"]
    assert ne_b9a["roles"]["acquisition"] == {"phase_id": "acquisition", "max_iterations": 0, "kinds": ["knowledge-requery"]}
    assert ne_b9a["max_revisions"] == 1
    if B9A_SMOKE.exists():
        assert _non_bookkeeping_diff(_load(FLOWN_SMOKE), _load(B9A_SMOKE)) == ["native_episode", "policy"]



B9A_REC = BASELINES / "slurp-native-plan-acquisition-b9a-recovery-baseline-v1.json"
B9A_REC_SMOKE = BASELINES / "slurp-native-plan-acquisition-b9a-recovery-smoke-4-baseline-v1.json"


def test_the_b9a_recovery_is_the_b9a_arm_byte_for_byte_outside_its_bookkeeping():
    """The one recovery re-registration of cell B9a (item E36 fixed the runtime binding, not the cell): new ids only."""
    assert _non_bookkeeping_diff(_load(B9A), _load(B9A_REC)) == []
    assert _non_bookkeeping_diff(_load(B9A_SMOKE), _load(B9A_REC_SMOKE)) == []
    rec = _load(B9A_REC)
    assert rec["policy"] == "phase-native-candidates-review-revise-acquire-v1"
    assert rec["native_episode"]["acquisition"]["policy"] == "saea-acquire-knowledge-requery-v1"
    assert "RECOVERY (2026-09-22)" in rec["what_this_is"]


B9A_V2 = BASELINES / "slurp-native-plan-acquisition-b9a-v2-baseline-v1.json"
B9A_V2_SMOKE = BASELINES / "slurp-native-plan-acquisition-b9a-v2-smoke-4-baseline-v1.json"


def test_the_b9a_v2_baseline_moves_exactly_the_two_e36b_keys_against_the_recovery_baseline():
    """Item E36b (owner decisions 90 and 70): cell B9a v2 is the sealed B9a-rec baseline plus
    EXACTLY the two new acquisition keys (``acquisition.budget.max_items_per_acquisition`` and
    ``acquisition.retrieval``) -- nothing else moves, including every other acquisition key."""

    rec, v2 = _load(B9A_REC), _load(B9A_V2)
    assert _non_bookkeeping_diff(rec, v2) == ["native_episode"]
    episode_diff = sorted(
        key for key in set(rec["native_episode"]) | set(v2["native_episode"])
        if rec["native_episode"].get(key) != v2["native_episode"].get(key)
    )
    assert episode_diff == ["acquisition"]
    rec_acquisition = rec["native_episode"]["acquisition"]
    v2_acquisition = v2["native_episode"]["acquisition"]
    assert rec_acquisition["policy"] == v2_acquisition["policy"]
    assert v2_acquisition["budget"] == {
        "max_acquisitions_per_row": 1, "contact_budget": 0, "max_items_per_acquisition": 5,
    }
    assert rec_acquisition["budget"] == {
        "max_acquisitions_per_row": 1, "contact_budget": 0,
    }
    assert v2_acquisition["retrieval"] == {
        "policy": "saea-requery-idf-v1",
        "min_token_chars": 4,
        "max_document_frequency": 0.05,
        "exclude_visible_tokens": True,
    }
    assert "retrieval" not in rec_acquisition
    if B9A_V2_SMOKE.exists() and B9A_REC_SMOKE.exists():
        smoke_diff = _non_bookkeeping_diff(_load(B9A_REC_SMOKE), _load(B9A_V2_SMOKE))
        assert smoke_diff == ["native_episode"]


def test_the_b9a_v2_experiment_cell_is_held_with_the_e36b_baseline_pinned():
    exp_path = REPO_ROOT / "configs" / "experiment" / "slurp-native-plan-acquisition-b9a-v2-v1.json"
    document = json.loads(exp_path.read_text(encoding="utf-8"))
    [cell] = document["cells"]
    assert cell["readiness"]["state"] == "held"
    assert cell["baseline_fragment"] == "slurp-native-plan-acquisition-b9a-v2-baseline-v1"
    assert cell["allowed_execution_stages"] == ["check", "worker", "campaign"]
    assert cell["run_id"] == "SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-V2-V1"

    smoke_path = (
        REPO_ROOT / "configs" / "experiment" / "slurp-native-plan-acquisition-b9a-v2-smoke-4-v1.json"
    )
    smoke_document = json.loads(smoke_path.read_text(encoding="utf-8"))
    [smoke_cell] = smoke_document["cells"]
    assert smoke_cell["readiness"]["state"] == "held"
    assert smoke_cell["baseline_fragment"] == "slurp-native-plan-acquisition-b9a-v2-smoke-4-baseline-v1"
R_PRIM = BASELINES / "slurp-native-review-primitives-baseline-v1.json"
R_PRIM_SMOKE = BASELINES / "slurp-native-review-primitives-smoke-4-baseline-v1.json"


def test_r_prim_moves_exactly_the_reviewer_verdict_module_against_the_plan():
    """Cell R-PRIM (item E37, owner decision 84): the locked default plan
    (cell PLAN) plus exactly the primitive-verdict module --
    native_episode.reviewer_verdict and the Reviewer's swapped instruction
    template -- and nothing else outside the bookkeeping."""
    flown, r_prim = _load(FLOWN), _load(R_PRIM)
    diff = _non_bookkeeping_diff(flown, r_prim)
    assert diff == ["native_episode", "phase_material"]

    ne_plan, ne_r_prim = flown["native_episode"], r_prim["native_episode"]
    episode_diff = sorted(
        key for key in set(ne_plan) | set(ne_r_prim) if ne_plan.get(key) != ne_r_prim.get(key)
    )
    assert episode_diff == ["reviewer_verdict"]
    assert ne_r_prim["reviewer_verdict"] == {"vocabulary": "saea-review-primitives-v1"}

    pm_plan, pm_r_prim = flown["phase_material"], r_prim["phase_material"]
    material_diff = sorted(
        key for key in set(pm_plan) | set(pm_r_prim) if pm_plan.get(key) != pm_r_prim.get(key)
    )
    assert material_diff == ["reviewer"]
    reviewer_plan, reviewer_r_prim = pm_plan["reviewer"], pm_r_prim["reviewer"]
    reviewer_diff = sorted(
        key for key in set(reviewer_plan) | set(reviewer_r_prim)
        if reviewer_plan.get(key) != reviewer_r_prim.get(key)
    )
    assert reviewer_diff == ["instruction_template"]
    assert (
        reviewer_r_prim["instruction_template"]
        == "probes/slurp_native_role_reviewer_primitives_v1.txt"
    )


def test_r_prim_smoke_carries_the_same_one_factor():
    plan_smoke, r_prim_smoke = _load(FLOWN_SMOKE), _load(R_PRIM_SMOKE)
    diff = _non_bookkeeping_diff(plan_smoke, r_prim_smoke)
    assert diff == ["native_episode", "phase_material"]
