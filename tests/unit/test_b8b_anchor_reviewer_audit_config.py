"""Cell B8b-anchor config-switch proof: the slot-audit block on the ANCHOR base.

Item E19 (2026-09-19, owner decision 32) re-bases cell B8b. Cell B7a v2 read
the Node Context Policy L1 stack HARMFUL, so every cell registered on it closed
and the audit block moved to the SEALED dual-store anchor -- which declares no
``native_episode.context_policy`` at all. These tests pin that the new
fragments differ from the anchor's by exactly two ``native_episode`` keys plus
bookkeeping, and that the composed configuration loads with the block armed and
NO policy declared:

1. the four-row smoke baseline is the arm baseline apart from its own FIT
   identity (the 4 x 11 x 4 = 176 endpoint ceiling) and its own prepared pin;
2. against the sealed anchor's own baseline, the only top-level key that moves
   is ``native_episode``, and inside it the only keys that move are
   ``reviewer_audit`` -- the factor -- and ``finite_completion_policy``, the
   harness declaration that renders no request byte;
3. neither fragment declares ``context_policy``: the composed policy is the
   key's own bare raw arm, which is what makes the ON-vs-OFF request diff
   exactly the block on the Reviewer contacts;
4. the armed pins name real committed bytes and hash to them;
5. dropping the two keys reconstructs the anchor's own ``native_episode``
   block;
6. the composed configuration loads with the block armed and the contact
   ceiling unmoved, and the loader still refuses the block by name on another
   carrier;
7. both experiment fragments are registered ``held`` at the anchor's roster and
   budgets, and the superseded L1-based registration is not referenced as a
   base.

Model-free: committed JSON, the repository's own ``core.config.compose``, and
no model, tokenizer, encoder, scorer, server or network contact.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "configs" / "baseline"
EXPERIMENT_DIR = REPO_ROOT / "configs" / "experiment"
CAMPAIGN_DIR = REPO_ROOT / "configs" / "campaign"

MODEL_FRAGMENT = (
    "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
)
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"

#: The sealed dual-store anchor: the OFF arm, and the base this cell is on.
ANCHOR = "slurp-native-dual-store-train-fold-a-anchor-v1"

ARM = "slurp-native-anchor-reviewer-audit-train-fold-a-v1"
SMOKE_BASELINE = "slurp-native-anchor-reviewer-audit-smoke-4-v1"
ARM_EXPERIMENT = "slurp-native-reviewer-audit-anchor-train-fold-a-v1"
SMOKE_EXPERIMENT = "slurp-native-reviewer-audit-anchor-smoke-4-v1"

REVIEWER_AUDIT_KEY = "reviewer_audit"
FINITE_COMPLETION_KEY = "finite_completion_policy"
FINITE_COMPLETION_VALUE = "deliver-latest-or-abstain"
#: Item E22 (the ReAct-exhaustion disposition, not the Earnings-22 carrier): the
#: second failure-mode declaration, armed 2026-09-19 after the arm aborted on a
#: Reviewer ReAct loop that exhausted its iterations by tool calls.
REACT_EXHAUSTION_KEY = "react_exhaustion_policy"
REACT_EXHAUSTION_VALUE = "continue-without-answer"

#: Bookkeeping-only top-level keys: run/attempt identity, the provenance-only
#: speech-feature ids and free-English notes. None shapes a rendered request.
BOOKKEEPING_KEYS = frozenset({
    "native_contact_fit",
    "prepared_phase_supply",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "what_this_is",
})


def _load_baseline(name: str) -> dict:
    return json.loads((BASELINE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _load_experiment(name: str) -> dict:
    return json.loads((EXPERIMENT_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _compose(baseline: str, experiment: str):
    from speech_aware_evidence_acquisition.core.config import compose

    return compose(str(REPO_ROOT), MODEL_FRAGMENT, DATASET_FRAGMENT, baseline, experiment)


def test_the_smoke_baseline_is_the_arm_baseline_plus_bookkeeping_only():
    arm = _load_baseline(ARM)
    smoke = _load_baseline(SMOKE_BASELINE)
    non_bookkeeping = (set(arm) | set(smoke)) - BOOKKEEPING_KEYS
    assert sorted(
        key for key in non_bookkeeping if arm.get(key) != smoke.get(key)
    ) == []
    assert smoke["native_contact_fit"]["contact_cap"] == 176
    assert arm["native_contact_fit"]["contact_cap"] == 47520
    assert arm["native_episode"][REVIEWER_AUDIT_KEY] == (
        smoke["native_episode"][REVIEWER_AUDIT_KEY]
    )
    assert arm["native_episode"][FINITE_COMPLETION_KEY] == (
        smoke["native_episode"][FINITE_COMPLETION_KEY]
    ) == FINITE_COMPLETION_VALUE
    assert arm["native_episode"][REACT_EXHAUSTION_KEY] == (
        smoke["native_episode"][REACT_EXHAUSTION_KEY]
    ) == REACT_EXHAUSTION_VALUE
    # Each cell carries its OWN prepared artifact, under its own run id.
    for name, baseline in (("TRAIN-FOLD-A", arm), ("SMOKE-4", smoke)):
        relpath = baseline["prepared_phase_supply"]["relpath"]
        assert relpath == (
            f"prepared/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-{name}-V1/"
            "phase-supply-v1.json"
        )


@pytest.mark.parametrize("on_name", [ARM, SMOKE_BASELINE], ids=["arm", "smoke"])
def test_the_only_keys_that_move_against_the_anchor_are_the_factor_and_the_two_failure_mode_declarations(on_name):
    off = _load_baseline(ANCHOR)
    on = _load_baseline(on_name)
    comparable = (set(off) | set(on)) - BOOKKEEPING_KEYS
    assert sorted(key for key in comparable if off.get(key) != on.get(key)) == [
        "native_episode"
    ]
    # Named one by one so a regression cannot hide behind the set comparison.
    for key in (
        "arm",
        "policy",
        "evidence_source",
        "evidence_mismatch",
        "knowledge_stores",
        "phase_material",
        "phase_tools",
        "scorers",
        "serving_slots",
        "serving_slot_tokens",
        "task_instruction_template",
        "task_instruction_template_active",
        "task_instruction_fill",
        "speech_packet_promotion_receipt",
        "speech_packet_promotion_receipt_sha256",
        "preparation_source_receipts",
    ):
        assert off[key] == on[key], key
    moved = sorted(
        key
        for key in set(off["native_episode"]) | set(on["native_episode"])
        if off["native_episode"].get(key) != on["native_episode"].get(key)
    )
    assert moved == [FINITE_COMPLETION_KEY, REACT_EXHAUSTION_KEY, REVIEWER_AUDIT_KEY]
    assert on["native_episode"][FINITE_COMPLETION_KEY] == FINITE_COMPLETION_VALUE
    assert on["native_episode"][REACT_EXHAUSTION_KEY] == REACT_EXHAUSTION_VALUE
    assert FINITE_COMPLETION_KEY not in off["native_episode"]
    assert REACT_EXHAUSTION_KEY not in off["native_episode"]
    assert REVIEWER_AUDIT_KEY not in off["native_episode"]


@pytest.mark.parametrize(
    "name", [ANCHOR, ARM, SMOKE_BASELINE], ids=["anchor", "arm", "smoke"]
)
def test_no_fragment_of_this_cell_declares_a_node_context_policy(name):
    """E19's whole point: the block attaches to the SEALED draft, so the base
    stays the anchor's own all-raw shape and no boundary is rendered."""

    assert "context_policy" not in _load_baseline(name)["native_episode"]
    assert "role_context" not in _load_baseline(name)["native_episode"]


def test_dropping_the_factor_and_the_two_declarations_reconstructs_the_anchors_episode_block():
    off = _load_baseline(ANCHOR)["native_episode"]
    for name in (ARM, SMOKE_BASELINE):
        on = copy.deepcopy(_load_baseline(name)["native_episode"])
        on.pop(REVIEWER_AUDIT_KEY)
        on.pop(FINITE_COMPLETION_KEY)
        on.pop(REACT_EXHAUSTION_KEY)
        assert on == off, name


def test_the_armed_block_pins_the_released_view_by_its_committed_bytes():
    block = _load_baseline(ARM)["native_episode"][REVIEWER_AUDIT_KEY]
    assert block["view"] == "slot-audit-v1"
    for field, expected_prefix in (
        ("release", "knowledge/slurp/semantic/slot-audit-v1/"),
        ("snapshot", "knowledge/slurp/semantic/slot-audit-v1/"),
    ):
        pin = block[field]
        assert pin["relpath"].startswith(expected_prefix)
        raw = (REPO_ROOT / pin["relpath"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == pin["sha256"], field
    assert block["thresholds"] == {
        "empty_draft_min_entity_row_share": 0.5,
        "missing_common_min_row_share": 0.5,
        "profile_min_row_share": 0.05,
    }


def test_the_composed_smoke_loads_a_native_episode_with_the_block_armed():
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    values = _compose(SMOKE_BASELINE, SMOKE_EXPERIMENT).values
    config = load_native_episode_config(
        values, default_phase_program(str(values["policy"]))
    )
    assert config.reviewer_audit_json is not None
    assert json.loads(config.reviewer_audit_json)["view"] == "slot-audit-v1"
    # E19: armed with NO declared policy. That is the whole re-basing.
    assert config.context_policy_json is None
    assert config.solver_hints_json is None
    # The block adds no contact, so the bounded ceiling does not move.
    assert config.max_contacts == 11
    assert config.finite_completion_policy == FINITE_COMPLETION_VALUE


def test_the_loader_still_refuses_the_block_on_another_carrier():
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    values = copy.deepcopy(_compose(SMOKE_BASELINE, SMOKE_EXPERIMENT).values)
    program = default_phase_program(str(values["policy"]))
    values["carrier_lock_key"] = "audio2tool"
    with pytest.raises(ValueError, match="carrier 'slurp'"):
        load_native_episode_config(values, program)


@pytest.mark.parametrize(
    "name,run_id,stages",
    [
        (
            SMOKE_EXPERIMENT,
            "SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1",
            ["check", "prepare-supply", "worker"],
        ),
        (
            ARM_EXPERIMENT,
            "SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1",
            ["check", "prepare-supply", "worker", "campaign"],
        ),
    ],
    ids=["smoke", "arm"],
)
def test_both_experiment_fragments_are_registered_held(name, run_id, stages):
    experiment = _load_experiment(name)
    (cell,) = experiment["cells"]
    state = cell["readiness"]["state"]
    # Held: no decision requirement yet -- the coordinator's re-pin cycle
    # appends and pins the root decision receipt and flips the state.
    assert state in {"held", "ready"}
    kinds = [entry["kind"] for entry in cell["readiness"]["requirements"]]
    assert "preparation" in kinds and set(kinds) <= {"decision", "preparation"}
    if state == "held":
        assert kinds == ["preparation"]
    assert cell["run_id"] == run_id
    assert cell["allowed_execution_stages"] == stages
    assert cell["cell_id"] == name
    assert experiment["experiment_id"] == run_id
    assert experiment["execution_profile"] == "bounded-discovery-probe"
    assert experiment["service_session"] == (
        "serving-slurp-native-candidate-five-train-a-np4-v1"
    )
    assert experiment["date"] == "2026-09-19"
    # The re-based cell names no retired L1 fragment as its base.
    assert "ncp-l1" not in cell["baseline_fragment"]
    assert cell["baseline_fragment"] == (
        "slurp-native-anchor-reviewer-audit-"
        + ("smoke-4" if "smoke" in name else "train-fold-a")
        + "-v1"
    )


def test_the_arm_keeps_the_anchors_roster_and_budgets_because_it_adds_no_contact():
    arm = _load_experiment(ARM_EXPERIMENT)
    assert arm["population"]["count"] == 1080
    assert arm["population"]["split_identity_hash"] == (
        "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"
    )
    assert arm["family_budget"] == {
        "asr_calls": 0,
        "ceilings_are_not_targets": True,
        "encoder_calls": 0,
        "fit_endpoint_calls_cap": 47520,
        "generation_calls_cap": 11880,
        "gpu_hours_fit_inclusive": 12.0,
        "native_task_contract_calls_cap": 6480,
        "official_complete_scoring_jobs": 1,
        "repeated_speech_audio_seconds_cap": 33930,
    }
    smoke = _load_experiment(SMOKE_EXPERIMENT)
    assert smoke["population"]["count"] == 4
    assert smoke["family_budget"]["official_complete_scoring_jobs"] == 0
    assert smoke["family_budget"]["generation_calls_cap"] == 44


def test_the_single_cell_campaign_plan_names_only_this_cell():
    plan = json.loads(
        (CAMPAIGN_DIR / f"{ARM_EXPERIMENT}.json").read_text(encoding="utf-8")
    )
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [
        {"cell": ARM_EXPERIMENT, "experiment": ARM_EXPERIMENT}
    ]
