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
import json
import os
import subprocess
import sys
from pathlib import Path

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


def test_perception_branch_two_knobs_under_one_route_is_one_axis():
    """P-SV-3 (scripts/flights/psv/psv_family.py CELLS['psv3']): a branch's
    ``overrides`` may name BOTH ``fuse_coverage.m`` and ``fuse_coverage.top_l``
    (raised together, since the fuser scans only the top ``m`` ranked facets
    and stops once ``len(selected) == top_l`` -- moving only one of the two
    leaves the delivered boundary-item count unchanged). This is still exactly
    ONE axis category (``parse_perception_branches``'s ``axis_categories =
    sum((bool(knobs), ...))`` counts the whole ``knobs`` tuple once), so it
    must load, not refuse, and must carry both knobs on the same branch.
    """

    values = _values_with_branches(level=2)
    branches = values["native_episode"]["roles"]["perception"]["branches"]["branches"]
    branches[0]["overrides"] = {
        f"knowledge_stores.{STORE}.phase_supply.perception.fuse_coverage.m": 12,
        f"knowledge_stores.{STORE}.phase_supply.perception.fuse_coverage.top_l": 12,
    }
    program = default_phase_program(values["policy"])
    config = load_native_episode_config(values, program, allow_subceiling=True)
    perception_role = next(role for role in config.roles if role.role_kind == "perception")
    b_branch = perception_role.perception_branches.branch("B")
    assert len(b_branch.knobs) == 2
    assert {knob.tail for knob in b_branch.knobs} == {("fuse_coverage", "m"), ("fuse_coverage", "top_l")}
    assert {knob.value for knob in b_branch.knobs} == {12}


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


# ---------------------------------------------------------------------------
# P-SV registration finding (coordinator, 2026-09-28): ``rails.
# native_episode_config`` used to import the BARE ``core.base.
# PERCEPTION_PRESENTATIONS`` registry object, never the module
# (``rails.perception_presentations``) whose own module-level ``.register(
# ...)`` calls populate it -- the same "import the registering module, not
# just the registry" rule ``rails.acquisition``/``core.base.
# ACQUISITION_POLICIES`` already follows. Whichever process happened to
# import ``rails.perception_presentations`` FIRST (for some unrelated
# reason) masked the bug; a fresh process that loads a branched config
# without ever having imported it hit "presentation_id 'top2-contrast-v1'
# is not registered; registered ids are []" on ``cli check``. This runs the
# load in a SEPARATE, fresh interpreter -- the only way to prove the fix
# does not depend on import order elsewhere in the test session.
# ---------------------------------------------------------------------------

_FRESH_PROCESS_LOAD_SCRIPT = """
import json
import sys

sys.path.insert(0, {src_dir!r})

from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)

values = json.loads(open({fragment_path!r}, encoding="utf-8").read())
values["carrier_lock_key"] = "slurp"
del values["native_episode"]["roles"]["solver"]["supply_variants"]
values["native_episode"]["roles"]["perception"]["branches"] = {{
    "level": 1,
    "fit_estimate": {fit!r},
    "branches": [
        {{
            "branch_id": "B", "max_supplied_items": 8,
            "presentation_id": "top2-contrast-v1",
            "contrast_pairs": {{
                "relpath": "prepared/SAEA-TEST-PERCEPTION-CONTRAST-PAIRS-V1/table.json",
                "sha256": "a" * 64,
            }},
        }},
        {{"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8}},
        {{"branch_id": "A", "deliver": True, "max_supplied_items": 8}},
    ],
}}
program = default_phase_program(values["policy"])
config = load_native_episode_config(values, program, allow_subceiling=True)
assert config is not None
perception_role = next(role for role in config.roles if role.role_kind == "perception")
assert perception_role.perception_branches.branches[0].presentation_id == "top2-contrast-v1"
print("OK")
"""


def test_a_fresh_process_resolves_top2_contrast_v1_with_no_prior_import():
    repo_root = Path(__file__).resolve().parents[2]
    src_dir = str(repo_root / "src")
    fragment_path = str(repo_root / "configs" / "baseline" / VAR2_FRAGMENT)
    script = _FRESH_PROCESS_LOAD_SCRIPT.format(
        src_dir=src_dir, fragment_path=fragment_path, fit=FIT,
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, env=env, timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK" in completed.stdout


# ---------------------------------------------------------------------------
# Refusals: finite_supply_policy and an acquisition policy that re-enters
# Perception, beside a declared branch group (design section 3, "Refused").
# ---------------------------------------------------------------------------


def test_perception_branches_refuse_beside_finite_supply_policy():
    values = _values_with_branches(level=1)
    values["finite_supply_policy"] = {}
    program = default_phase_program(values["policy"])
    with pytest.raises(ValueError, match="finite_supply_policy"):
        load_native_episode_config(values, program, allow_subceiling=True)


def test_perception_branches_refuse_beside_an_acquisition_policy_that_reenters_perception():
    from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec

    phases = ("perception", "solver", "reviewer", "planner", "acquisition")
    program = PhaseProgram(
        program_id="phase-native-role-perception-branch-acquisition-test",
        phases=tuple(PhaseSpec(name, name, "none", None, False) for name in phases),
        max_contacts=20,
        stop_rule="native-role-episode",
    ).validate()
    values = {"native_episode": {
        "schema": "saea-native-episode-config-v1",
        "episode_id": "native-role-perception-branch-acquisition-test",
        "max_revisions": 1,
        "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
        "roles": {
            name: {"phase_id": name, "max_iterations": 1}
            for name in ("perception", "solver", "reviewer", "planner")
        },
        "acquisition": {
            "policy": "saea-acquire-speech-reobserve-v1",
            "budget": {"max_acquisitions_per_row": 1, "contact_budget": 1},
        },
    }}
    values["native_episode"]["roles"]["acquisition"] = {
        "phase_id": "acquisition", "max_iterations": 1, "kinds": ["speech-reobserve"],
    }
    values["native_episode"]["roles"]["perception"]["branches"] = _branches_block(level=1)
    with pytest.raises(ValueError, match="re-enters Perception"):
        load_native_episode_config(values, program, allow_subceiling=True)
