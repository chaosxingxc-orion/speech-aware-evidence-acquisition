"""Cell ROLL-AA (board route F2): the within-flight A/A null against cell ROLL-1.

In the ``tests/unit/test_stage3_rollout_baseline_cell.py`` style: the ROLL-AA
baseline and the ROLL-1 baseline agree on every key except the per-flight
bookkeeping AND the enumerated F2 factor (the Solver group and the policy id) --
so "the A/A null differs from the rollout only in the announced keys" is a
property of bytes, not of prose.

The second half proves the thing the cell is actually for: that the registered
Solver group really is an A/A form. ``samples`` is 2, ``twin`` is the E2b
``greedy-repeat`` marker (the only value ``rails.native_episode_config`` accepts,
and the only way ``decoding_overrides.temperature`` may be 0 at all),
``temperature`` is 0, ``seed_offset`` is 0, and the composed per-sample request
decoding params differ in EXACTLY one field -- ``seed`` -- which greedy decoding
does not consult.

The third half proves the ceiling: the committed phase program
``phase-native-candidates-review-revise-samples2-v1`` declares ``max_contacts``
13, which is the bounded graph ceiling ``1 + (1 + 1) * (1 * 2 + 3 + 1)`` the
loader computes; the loader refuses by name when the two disagree, so a config
that drifts can never compose.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINES = REPO_ROOT / "configs" / "baseline"
EXPERIMENTS = REPO_ROOT / "configs" / "experiment"
ROSTERS = REPO_ROOT / "docs" / "receipts" / "rosters"

ROLLOUT = BASELINES / "slurp-native-stage3-rollout-baseline-v1.json"
ROLLOUT_SMOKE = BASELINES / "slurp-native-stage3-rollout-smoke-4-baseline-v1.json"
ROLL_AA = BASELINES / "slurp-native-stage3-roll-aa-baseline-v1.json"
ROLL_AA_SMOKE = BASELINES / "slurp-native-stage3-roll-aa-smoke-4-baseline-v1.json"
PROGRAM = (
    REPO_ROOT / "configs" / "policy"
    / "phase-native-candidates-review-revise-samples2-v1.json"
)

#: Per-flight bookkeeping: the fit receipt, the prepared supply, the free-English
#: descriptions and the two notes this registration added for the reader.
BOOKKEEPING = frozenset({
    "native_contact_fit",
    "prepared_phase_supply",
    "what_this_is",
    "roster_note",
    "a_a_null_note",
})

#: The F2 factor: exactly what the ROLL-AA baseline is allowed to move against
#: cell ROLL-1 outside bookkeeping.
ENUMERATED = frozenset({"native_episode", "policy"})

EXPECTED_SOLVER = {
    "commit": {
        "min_support": 2,
        "policy": "saea-commit-plurality-support-v1",
        "similarity_threshold": 0.8,
    },
    "decoding_overrides": {"seed_offset": 0, "temperature": 0.0},
    "max_iterations": 1,
    "phase_id": "solver",
    "samples": 2,
    "twin": "greedy-repeat",
}

CEILING = 13


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("parent", "child"), [(ROLLOUT, ROLL_AA), (ROLLOUT_SMOKE, ROLL_AA_SMOKE)]
)
def test_roll_aa_moves_only_the_announced_keys(parent: Path, child: Path) -> None:
    left, right = _load(parent), _load(child)
    moved = {
        key
        for key in (set(left) | set(right)) - BOOKKEEPING
        if left.get(key) != right.get(key)
    }
    assert moved <= ENUMERATED, sorted(moved - ENUMERATED)


@pytest.mark.parametrize(
    ("parent", "child"), [(ROLLOUT, ROLL_AA), (ROLLOUT_SMOKE, ROLL_AA_SMOKE)]
)
def test_only_the_solver_role_moves_inside_the_episode(parent: Path, child: Path) -> None:
    left = _load(parent)["native_episode"]
    right = _load(child)["native_episode"]
    moved = {key for key in set(left) | set(right) if left.get(key) != right.get(key)}
    assert moved == {"roles"}, sorted(moved)
    left_roles, right_roles = left["roles"], right["roles"]
    assert set(left_roles) == set(right_roles)
    moved_roles = {
        kind for kind in left_roles if left_roles[kind] != right_roles.get(kind)
    }
    assert moved_roles == {"solver"}, sorted(moved_roles)


@pytest.mark.parametrize("path", [ROLL_AA, ROLL_AA_SMOKE])
def test_the_registered_solver_group_is_the_a_a_form(path: Path) -> None:
    solver = _load(path)["native_episode"]["roles"]["solver"]
    assert solver == EXPECTED_SOLVER
    # min_support may never exceed samples; the loader refuses it, and the
    # registration's own choice (2 of 2) is pinned here so a later edit to
    # either number is a test failure rather than a silent re-interpretation.
    assert solver["commit"]["min_support"] <= solver["samples"]


@pytest.mark.parametrize("path", [ROLL_AA, ROLL_AA_SMOKE])
def test_the_policy_program_carries_the_samples_two_ceiling(path: Path) -> None:
    assert _load(path)["policy"] == PROGRAM.stem
    program = _load(PROGRAM)
    assert program["program_id"] == PROGRAM.stem
    assert program["max_contacts"] == CEILING
    assert program["stop_rule"] == "native-role-episode"
    # the phase list is the samples5 program's, unchanged
    parent = _load(
        PROGRAM.with_name("phase-native-candidates-review-revise-samples5-v1.json")
    )
    assert program["phases"] == parent["phases"]
    assert program["max_contacts"] != parent["max_contacts"]


def test_the_two_samples_are_one_request_up_to_an_inert_seed() -> None:
    """The whole thesis of cell ROLL-AA, proved without a contact."""

    from speech_aware_evidence_acquisition.rails.runner import _solver_fragment_seed
    from speech_aware_evidence_acquisition.reproduction.ojw.native_request import (
        compose_solver_sample_decoding_params,
    )

    overrides = EXPECTED_SOLVER["decoding_overrides"]
    fragment_seed = _solver_fragment_seed(PROGRAM.stem)
    base = {"id_slot": "per-sample", "max_tokens": 512, "seed": 20260913, "temperature": 0}
    composed = [
        compose_solver_sample_decoding_params(
            base, fragment_seed=fragment_seed, decoding_overrides=overrides, sample_index=index
        )
        for index in range(EXPECTED_SOLVER["samples"])
    ]
    differ = sorted(
        key
        for key in set(composed[0]) | set(composed[1])
        if composed[0].get(key) != composed[1].get(key)
    )
    assert differ == ["seed"]
    assert [entry["temperature"] for entry in composed] == [0.0, 0.0]
    assert [entry["seed"] for entry in composed] == [fragment_seed, fragment_seed + 1]


def test_the_episode_config_admits_temperature_zero_only_under_the_twin() -> None:
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        NativeEpisodeRole,
    )

    kwargs = dict(
        samples=2,
        decoding_overrides=EXPECTED_SOLVER["decoding_overrides"],
        commit=EXPECTED_SOLVER["commit"],
    )
    NativeEpisodeRole("solver", "solver", 1, (), "full", twin="greedy-repeat", **kwargs)
    # Without the marker the SAME role is refused, and the refusal names the
    # interval that excludes 0: "decoding_overrides.temperature must be in (0, 2]".
    with pytest.raises(ValueError, match=r"temperature must be in"):
        NativeEpisodeRole("solver", "solver", 1, (), "full", **kwargs)


@pytest.mark.parametrize(
    ("relpath", "rows", "split_identity_hash"),
    [
        (
            "slurp-stage3-roll-aa-r01c-200-v1.json",
            200,
            "dbb60c9db5c2d2dc4f5bd06274ee1ab70d0dd3d4f8a0b70b21e5f1d6127487a3",
        ),
        (
            "slurp-stage3-roll-aa-r01c-smoke-4-v1.json",
            4,
            "e9dcea536028d17737b999c65267e47645ca7b3f6f9c4f57622961cf29363ed5",
        ),
    ],
)
def test_the_rosters_are_pure_prefixes_of_r01c(
    relpath: str, rows: int, split_identity_hash: str
) -> None:
    from speech_aware_evidence_acquisition.core.roster import verify_roster

    parent = _load(ROSTERS / "slurp-stage3-construction-r01c.json")
    receipt = _load(ROSTERS / relpath)
    assert verify_roster(receipt) == split_identity_hash
    assert receipt["roster_role"] == "construction"
    assert receipt["split_role"] == "discovery"
    assert len(receipt["items"]) == rows
    # a PURE selection: the parent's own items, verbatim, in the parent's order
    assert receipt["items"] == parent["items"][:rows]


@pytest.mark.parametrize(
    ("relpath", "rows", "calls", "seconds", "split_identity_hash"),
    [
        (
            "slurp-native-stage3-roll-aa-v1.json",
            200,
            2600,
            10235,
            "dbb60c9db5c2d2dc4f5bd06274ee1ab70d0dd3d4f8a0b70b21e5f1d6127487a3",
        ),
        (
            "slurp-native-stage3-roll-aa-smoke-4-v1.json",
            4,
            52,
            222,
            "e9dcea536028d17737b999c65267e47645ca7b3f6f9c4f57622961cf29363ed5",
        ),
    ],
)
def test_the_experiment_fragments_are_held_and_budgeted_at_the_ceiling(
    relpath: str, rows: int, calls: int, seconds: int, split_identity_hash: str
) -> None:
    document = _load(EXPERIMENTS / relpath)
    assert document["population"]["count"] == rows
    assert document["population"]["split_identity_hash"] == split_identity_hash
    assert len(document["populations"][0]["ids"]) == rows
    assert document["execution_plan"]["planned_model_calls"] == calls == rows * CEILING
    assert document["execution_plan"]["planned_speech_audio_seconds"] == seconds
    assert document["execution_plan"]["execution_profile"] == "bounded-discovery-probe"
    assert document["stage3_algorithm"]["id"] == "shared-rollout"
    assert document["stage3_algorithm"]["operators_used"] == ["rollout"]
    for cell in document["cells"]:
        # `held` with no requirements as registered (5744ed8c); the flips (2aabfc26 arm, bfcd0f22 smoke) set
        # `ready` with the family's decision receipt and the cell's OWN minted supply.
        readiness = cell["readiness"]
        assert readiness["state"] in ("held", "ready")
        if readiness["state"] == "held":
            assert readiness["requirements"] == []
        else:
            by_kind = {req["kind"]: req for req in readiness["requirements"]}
            assert len(by_kind) == len(readiness["requirements"]) == 2, readiness["requirements"]
            assert by_kind["decision"]["expected_decision_id"] == "slurp-stage3-roll-aa-admission-v1"
            assert by_kind["preparation"]["relpath"] == f"prepared/{cell['run_id']}/phase-supply-v1.json"
