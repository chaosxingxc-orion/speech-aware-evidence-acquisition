"""E32: the native phase PROGRAM that carries the Acquisition phase, so cell
B9a (item E18, owner decisions 43/44/78) can be flown.

E18 (docs/superpowers/specs/2026-09-19-e18-acquisition-node-design.md)
built the sixth node -- the loader, the three registered kinds, the boundary
constants and the graph -- and proved all of it against a SYNTHETIC
PhaseProgram built inline by tests/unit/test_e18_acquisition_node.py.
No committed policy fragment carried a fifth, "acquisition" phase, so
composing any real baseline with the two E18 keys was refused: "native role
references an unknown program phase".

This module proves the REAL, REGISTERED program
configs/policy/phase-native-candidates-review-revise-acquire-v1.json
(program id "phase-native-candidates-review-revise-acquire-v1"):

1. it loads through default_phase_program with five phases and
   max_contacts 11 -- the SAME ceiling as the four-phase
   phase-native-candidates-review-revise-v1, because the registered
   zero-contact acquisition kinds add nothing to the bounded graph formula;
2. a B9a-style baseline -- built here from
   configs/baseline/slurp-native-default-plan-lock-baseline-v1.json (the
   sealed PLAN arm own fragment, present in this worktree at e367a629)
   plus the two E18 keys -- composes against it with ceiling 11 and
   acquisition_policy_id == "saea-acquire-knowledge-requery-v1";
3. the SAME fragment WITHOUT the two keys is the OFF arm, and stays on the
   OLD four-phase program id (the one the sealed PLAN arm already flies):
   it still loads there, and is REFUSED against the new five-phase program,
   because the fifth phase would then have no covering role -- "native
   roles must cover the program once each". The new program is therefore
   only ever composed WITH the keys armed;
4. the OLD four-phase program refuses the two keys armed, because it has no
   phase named "acquisition" -- "native role references an unknown program
   phase", the exact refusal the item problem statement quotes;
5. rails.phase_material.load_phase_material_specs exempts the armed,
   zero-contact acquisition phase from its "every phase must declare its
   own material" rule (no contact is ever dispatched there for kind (a)
   knowledge-requery), while still requiring material for every other
   phase exactly as before;
6. a model-free wire proof, through the real parser, the real OpenJiuwen
   role graph and the shared fake transport (the same
   _ActualEpisodeHarness pattern
   tests/unit/test_e18_acquisition_node.py uses): one fake-model episode
   under the NEW program id where the Planner routes ACQUIRE once --
   the acquisition receipt precedes the second Solver revision and the row
   delivers -- and one where the Planner routes ACCEPT immediately and
   no acquisition receipt exists at all.

Zero model, tokenizer, encoder or server contacts; nothing under
SPEECHRL_DATA_DIR is read or written. Item 6 needs OpenJiuwen installed
(skipped otherwise, exactly as the E18 proofs are).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import acquisition as acq
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.phase_material import (
    PhaseMaterialError,
    load_phase_material_specs,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    ACQUISITION_STAGE,
)

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness

REPO_ROOT = Path(__file__).resolve().parents[2]
PROGRAM_ID = "phase-native-candidates-review-revise-acquire-v1"
OLD_PROGRAM_ID = "phase-native-candidates-review-revise-v1"


def _default_plan_lock_baseline() -> dict:
    path = (
        REPO_ROOT
        / "configs/baseline/slurp-native-default-plan-lock-baseline-v1.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _armed_native_episode_block(native_episode: dict) -> dict:
    """The SAME native_episode block plus the two E18 keys (design section
    4): roles.acquisition and native_episode.acquisition, both required
    together."""

    block = copy.deepcopy(native_episode)
    block["roles"]["acquisition"] = {
        "phase_id": "acquisition",
        "max_iterations": 0,
        "kinds": ["knowledge-requery"],
    }
    block["acquisition"] = {
        "policy": acq.KNOWLEDGE_REQUERY_POLICY_ID,
        "budget": {"max_acquisitions_per_row": 1, "contact_budget": 0},
    }
    return block


# ---------------------------------------------------------------------------
# 1. The program itself.
# ---------------------------------------------------------------------------


def test_the_program_loads_with_five_phases_and_ceiling_eleven():
    program = default_phase_program(PROGRAM_ID)
    assert program.phase_names() == (
        "perception", "reviewer", "planner", "solver", "acquisition",
    )
    assert program.max_contacts == 11
    assert program.stop_rule == "native-role-episode"
    for phase in program.phases:
        phase.validate()
    acquisition = program.phase("acquisition")
    assert acquisition.knowledge == "none"
    assert acquisition.response_format_id is None
    assert acquisition.barrier is False


# ---------------------------------------------------------------------------
# 2. Composing the B9a baseline.
# ---------------------------------------------------------------------------


def test_a_b9a_style_fragment_composes_on_the_new_program_with_ceiling_eleven():
    baseline = _default_plan_lock_baseline()
    values = {
        "policy": PROGRAM_ID,
        "carrier_lock_key": "slurp",
        "native_episode": _armed_native_episode_block(baseline["native_episode"]),
    }
    program = default_phase_program(PROGRAM_ID)

    parsed = load_native_episode_config(values, program)

    assert parsed.acquisition_enabled is True
    assert parsed.acquisition_policy_id == acq.KNOWLEDGE_REQUERY_POLICY_ID
    assert parsed.acquisition_policy_id == "saea-acquire-knowledge-requery-v1"
    assert parsed.acquisition_role.phase_id == "acquisition"
    assert parsed.acquisition_budget == {
        "max_acquisitions_per_row": 1, "contact_budget": 0,
    }
    assert parsed.max_contacts == 11
    assert program.max_contacts == 11


def test_the_off_arm_fragment_still_loads_under_the_old_four_phase_program():
    baseline = _default_plan_lock_baseline()
    values = {
        "policy": OLD_PROGRAM_ID,
        "carrier_lock_key": "slurp",
        "native_episode": baseline["native_episode"],
    }
    old_program = default_phase_program(OLD_PROGRAM_ID)

    parsed = load_native_episode_config(values, old_program)

    assert parsed.acquisition_enabled is False
    assert parsed.max_contacts == 11


def test_the_off_arm_fragment_is_refused_against_the_new_five_phase_program():
    baseline = _default_plan_lock_baseline()
    values = {"policy": PROGRAM_ID, "native_episode": baseline["native_episode"]}
    new_program = default_phase_program(PROGRAM_ID)

    with pytest.raises(ValueError, match="cover the program"):
        load_native_episode_config(values, new_program)


def test_the_old_four_phase_program_refuses_the_armed_keys():
    baseline = _default_plan_lock_baseline()
    values = {
        "policy": OLD_PROGRAM_ID,
        "native_episode": _armed_native_episode_block(baseline["native_episode"]),
    }
    old_program = default_phase_program(OLD_PROGRAM_ID)

    with pytest.raises(ValueError, match="unknown program phase"):
        load_native_episode_config(values, old_program)


# ---------------------------------------------------------------------------
# 3. phase_material: the zero-contact acquisition phase is exempt.
# ---------------------------------------------------------------------------


def test_phase_material_exempts_the_zero_contact_acquisition_phase():
    baseline = _default_plan_lock_baseline()
    values = {
        "native_episode": _armed_native_episode_block(baseline["native_episode"]),
        "phase_material": baseline["phase_material"],
    }
    program = default_phase_program(PROGRAM_ID)

    specs = load_phase_material_specs(values, program)

    assert set(specs) == {"perception", "reviewer", "planner", "solver"}
    assert "acquisition" not in specs


def test_phase_material_still_requires_every_other_phase():
    baseline = _default_plan_lock_baseline()
    material = dict(baseline["phase_material"])
    del material["solver"]
    values = {
        "native_episode": _armed_native_episode_block(baseline["native_episode"]),
        "phase_material": material,
    }
    program = default_phase_program(PROGRAM_ID)

    with pytest.raises(PhaseMaterialError, match="no entry"):
        load_phase_material_specs(values, program)


def test_phase_material_is_not_exempt_when_the_module_is_unarmed():
    baseline = _default_plan_lock_baseline()
    values = {
        "native_episode": baseline["native_episode"],
        "phase_material": baseline["phase_material"],
    }
    old_program = default_phase_program(OLD_PROGRAM_ID)

    specs = load_phase_material_specs(values, old_program)

    assert set(specs) == {"perception", "reviewer", "planner", "solver"}


# ---------------------------------------------------------------------------
# 4. The model-free wire proof.
# ---------------------------------------------------------------------------


def _wire_proof_values(*, max_revisions: int = 1) -> dict:
    return {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": "e32-new-program-wire-proof",
            "max_revisions": max_revisions,
            "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
            "roles": {
                "perception": {"phase_id": "perception", "max_iterations": 1},
                "solver": {"phase_id": "solver", "max_iterations": 1},
                "reviewer": {"phase_id": "reviewer", "max_iterations": 3},
                "planner": {"phase_id": "planner", "max_iterations": 1},
                "acquisition": {
                    "phase_id": "acquisition", "max_iterations": 0,
                    "kinds": ["knowledge-requery"],
                },
            },
            "acquisition": {
                "policy": acq.KNOWLEDGE_REQUERY_POLICY_ID,
                "budget": {"max_acquisitions_per_row": 1, "contact_budget": 0},
            },
        },
    }


def _wire_proof_harness(
    tmp_path,
    *,
    planner_actions,
    requery_items=(("kb:value-9", "intent-boundaries", "alarm_set: set an alarm"),),
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=11,
        planner_actions=planner_actions,
        exhaustion_policy="deliver-latest-solver",
    )
    program = default_phase_program(PROGRAM_ID)
    config = load_native_episode_config(_wire_proof_values(), program)
    harness.config = config
    harness.program = program
    harness.repo_root = REPO_ROOT

    base_material_for_phase = harness.material_for_phase

    def material_for_phase(phase, context, sealed):
        material = base_material_for_phase(phase, context, sealed)
        if phase == "perception":
            material = PhaseMaterial(
                instruction=material.instruction,
                response_format={"type": "json_object"},
                contact_id=material.contact_id,
                purpose=material.purpose,
            )
        return material

    harness.material_for_phase = material_for_phase
    calls = []

    def requery(*, phase_id, filters, exclude_value_ids, scope, context):
        calls.append({
            "phase_id": phase_id,
            "filters": tuple(filters),
            "excluded": frozenset(exclude_value_ids),
            "scope": dict(scope),
        })
        return [
            acq.AcquiredItem(value_id, source_id, content)
            for value_id, source_id, content in requery_items
        ]

    harness.acquisition_requery = requery
    harness.requery_calls = calls
    return harness


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_an_acquire_then_accept_row_delivers_with_the_acquisition_receipt_first(tmp_path):
    harness = _wire_proof_harness(tmp_path, planner_actions=("ACQUIRE", "ACCEPT"))
    try:
        summary = harness.run()
    finally:
        harness.close()

    [result] = summary.results
    assert result.final_response_text == "solver-answer:s1:visit:2"

    receipt = result.native_episode_receipt
    stages = [visit["stage"] for visit in receipt["role_visits"]]
    assert ACQUISITION_STAGE in stages
    acquisition_index = stages.index(ACQUISITION_STAGE)
    assert "solver" in stages[acquisition_index + 1:]

    visit = receipt["role_visits"][acquisition_index]
    assert visit["role_id"] == "acquisition"
    assert "execution_receipt" not in visit
    record = visit["acquisition_receipt"]
    assert record["kind"] == "knowledge-requery"
    assert record["policy_id"] == acq.KNOWLEDGE_REQUERY_POLICY_ID
    assert record["contacts_used"] == 0

    block = receipt["acquisition"]
    assert block["node_phase_id"] == "acquisition"
    assert block["kind"] == "knowledge-requery"
    assert block["contacts_used"] == 0

    [call] = harness.requery_calls
    assert call["phase_id"] == "solver"


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_an_accept_first_row_carries_no_acquisition_receipt(tmp_path):
    harness = _wire_proof_harness(tmp_path, planner_actions=("ACCEPT",))
    try:
        summary = harness.run()
    finally:
        harness.close()

    [result] = summary.results
    assert result.final_response_text == "solver-answer:s1:visit:1"

    receipt = result.native_episode_receipt
    stages = [visit["stage"] for visit in receipt["role_visits"]]
    # The Acquisition node NEVER visited: no role_visits stage, no execution
    # receipt, no requery call. The armed module still carries its own
    # per-row summary block (design section 7), but with zero acquisitions.
    assert ACQUISITION_STAGE not in stages
    block = receipt["acquisition"]
    assert block["acquisitions"] == []
    assert block["contacts_used"] == 0
    assert harness.requery_calls == []
