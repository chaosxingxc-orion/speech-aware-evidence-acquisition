"""Config-layer tests for the Perception-branch group (same-flight instrument
phase 2, merge set C, item 3): parsing wired into
``rails.native_episode_config.load_native_episode_config``, the
contact-ceiling term, and the cross-mechanism refusals.

Reuses the real VAR2 supply-variant baseline fragment purely as a
structurally valid, already-registered four-role config with a generous
program contact ceiling (17): its OWN ``roles.solver.supply_variants`` is
removed in every test that instead arms ``roles.perception.branches``, so the
two mechanisms are never both present unless a test is deliberately checking
their mutual refusal.
"""

from __future__ import annotations

import copy

import pytest

from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)

from test_stage3_supply_variant_interleaving import VAR2_FRAGMENT, _fragment

STORE = "intent-boundaries"
FIT = {
    "slot_tokens": 24576,
    "completion_ceiling": 512,
    "base_prompt_tokens": 9600,
    "tokens_per_supplied_item": 120,
}


def _branches_block(level=1):
    return {
        "level": level,
        "fit_estimate": dict(FIT),
        "branches": [
            {
                "branch_id": "B", "max_supplied_items": 8,
                "overrides": {f"knowledge_stores.{STORE}.phase_supply.perception.k": 16},
            },
            {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8},
            {"branch_id": "A", "deliver": True, "max_supplied_items": 8},
        ],
    }


def _values_with_branches(level=1):
    values = _fragment(VAR2_FRAGMENT)
    del values["native_episode"]["roles"]["solver"]["supply_variants"]
    values["native_episode"]["roles"]["perception"]["branches"] = _branches_block(level)
    return values


def test_perception_branches_compose_and_extend_the_ceiling_level1():
    values = _values_with_branches(level=1)
    program = default_phase_program(values["policy"])
    config = load_native_episode_config(values, program, allow_subceiling=True)
    # base (no Solver arm group, no branch group) = 1 + (1 + 1) * (1 + 3 + 1)
    # = 1 + 2*5 = 11; level 1 adds K - 1 = 2.
    assert config.max_contacts == 13
    perception_role = next(role for role in config.roles if role.role_kind == "perception")
    assert perception_role.perception_branches.level == 1
    assert perception_role.perception_branches.branch_ids == ("B", "T", "A")
    solver_role = next(role for role in config.roles if role.role_kind == "solver")
    assert solver_role.supply_variants is None


def test_perception_branches_extend_the_ceiling_level2():
    values = _values_with_branches(level=2)
    program = default_phase_program(values["policy"])
    config = load_native_episode_config(values, program, allow_subceiling=True)
    # base 11; level 2 adds 2 * (K - 1) = 4.
    assert config.max_contacts == 15


def test_perception_branches_refuse_beside_solver_supply_variants():
    values = _fragment(VAR2_FRAGMENT)  # keeps its own roles.solver.supply_variants
    values["native_episode"]["roles"]["perception"]["branches"] = _branches_block(1)
    program = default_phase_program(values["policy"])
    with pytest.raises(ValueError, match="cannot combine"):
        load_native_episode_config(values, program, allow_subceiling=True)


def test_perception_branches_require_max_iterations_one():
    values = _values_with_branches(level=1)
    values["native_episode"]["roles"]["perception"]["max_iterations"] = 2
    program = default_phase_program(values["policy"])
    with pytest.raises(ValueError, match="max_iterations"):
        load_native_episode_config(values, program, allow_subceiling=True)


def test_perception_branches_refuse_an_invalid_block_by_name():
    values = _values_with_branches(level=1)
    values["native_episode"]["roles"]["perception"]["branches"]["branches"][1][
        "replicate_of"
    ] = "not-a"
    program = default_phase_program(values["policy"])
    with pytest.raises(ValueError, match="roles.perception.branches is invalid"):
        load_native_episode_config(values, program, allow_subceiling=True)


def test_perception_branches_refuse_on_another_role():
    values = _values_with_branches(level=1)
    values["native_episode"]["roles"]["solver"]["branches"] = copy.deepcopy(
        values["native_episode"]["roles"]["perception"]["branches"]
    )
    del values["native_episode"]["roles"]["perception"]["branches"]
    program = default_phase_program(values["policy"])
    with pytest.raises(ValueError, match="each native role requires"):
        load_native_episode_config(values, program, allow_subceiling=True)


def test_perception_branches_refuse_beside_knowledge_value_rendering():
    values = _values_with_branches(level=1)
    values["native_episode"]["knowledge_value_rendering"] = {
        "schema": "saea-knowledge-value-rendering-v1",
        "order": "retrieval-rank",
        "rank_visible": True,
        "stores": [STORE],
    }
    program = default_phase_program(values["policy"])
    with pytest.raises(ValueError, match="Perception branch group"):
        load_native_episode_config(values, program, allow_subceiling=True)


def test_a_config_declaring_neither_mechanism_still_composes_byte_identically():
    values = _fragment(VAR2_FRAGMENT)
    del values["native_episode"]["roles"]["solver"]["supply_variants"]
    program = default_phase_program(values["policy"])
    config = load_native_episode_config(values, program, allow_subceiling=True)
    # Pre-phase-2 formula: 1 + 2 * (1 + 3 + 1) = 11.
    assert config.max_contacts == 11
    perception_role = next(role for role in config.roles if role.role_kind == "perception")
    assert perception_role.perception_branches is None
