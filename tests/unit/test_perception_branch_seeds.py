"""``core.flight.runtime.FlightRuntime._perception_branch_seeds`` (same-flight
instrument, PHASE 2, merge set C, item 4 -- the identity-bound runtime piece
docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-
variants-design.md section 3 ("Branch seeds") and section 5 name).

Structurally the twin of ``tests/unit/test_knowledge_store_release_
alternates.py``'s own ``FlightRuntime._supply_action_router`` tests: a bare
``SimpleNamespace`` stand-in for ``self`` (no real flight, no model, no
server, no GPU), the SAME synthetic first-phase-supplying knowledge-store
fixture (``test_knowledge_stores._first_phase_config``), and the method
called directly, unbound, exactly as those tests call
``FlightRuntime._supply_action_router(runtime, ...)``.
"""

from __future__ import annotations

import types
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
    _perception_branches_identity,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    parse_perception_branches,
)

from test_knowledge_stores import _first_phase_config

STORE = "intent-boundaries"
FIT = {
    "slot_tokens": 24576,
    "completion_ceiling": 512,
    "base_prompt_tokens": 4000,
    "tokens_per_supplied_item": 100,
}


def _fake_runtime(config, *, data_root):
    """A bare ``self`` stand-in for ``FlightRuntime`` (no real flight).

    ``_perception_branch_seeds`` calls ``self._supply_action_router`` (a
    real ``FlightRuntime`` method) internally, so -- unlike a test that calls
    ``FlightRuntime._supply_action_router(runtime, ...)`` directly -- this
    fake must carry a properly BOUND method of its own, not just the
    attributes that method reads.
    """

    runtime = SimpleNamespace(
        _composed=SimpleNamespace(values=config),
        _data_root=data_root,
        _knowledge_store_binding=load_knowledge_store_binding(config, data_root=data_root),
        _knowledge_store_router_options={},
    )
    runtime._supply_action_router = types.MethodType(
        FlightRuntime._supply_action_router, runtime,
    )
    return runtime


def _group(*, b_overrides=None, level=1):
    branch_b = {
        "branch_id": "B", "max_supplied_items": 8,
        "overrides": b_overrides or {f"knowledge_stores.{STORE}.phase_supply.direct.k": 1},
    }
    return parse_perception_branches(
        {
            "level": level,
            "fit_estimate": dict(FIT),
            "branches": [
                branch_b,
                {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8},
                {"branch_id": "A", "deliver": True, "max_supplied_items": 8},
            ],
        },
        first_phase_id="direct",
        declared_stores=(STORE, "slot-contracts"),
    )


def _binding_and_seed(config):
    binding = {
        "speech_packet_bindings": {
            "s1": {"packet_id": "speech/s1", "sha256": "a" * 64},
        },
    }
    program = default_phase_program("phase-direct-only-supplied-v1")
    plan = SimpleNamespace(split_identity_hash="b" * 64)
    return program, binding, plan


def test_a_seed_reproduces_the_flights_own_prepared_seed(tmp_path):
    config, _snapshots = _first_phase_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    group = _group()
    program, binding, plan = _binding_and_seed(config)
    expected = {
        "s1": (
            "intent-boundaries::value:dim-light",
            "slot-contracts::value:dim-light",
        )
    }

    seeds, receipts = FlightRuntime._perception_branch_seeds(
        runtime, program, binding, group, expected, plan,
    )

    assert seeds["A"] == expected
    assert seeds["T"] == expected
    assert {row["branch_id"] for row in receipts} == {"A", "T", "B"}


def test_twin_takes_a_seed_exactly(tmp_path):
    config, _snapshots = _first_phase_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    group = _group()
    program, binding, plan = _binding_and_seed(config)
    expected = {
        "s1": (
            "intent-boundaries::value:dim-light",
            "slot-contracts::value:dim-light",
        )
    }

    seeds, _receipts = FlightRuntime._perception_branch_seeds(
        runtime, program, binding, group, expected, plan,
    )

    assert seeds["T"] == seeds["A"]


def test_a_router_disagreeing_with_the_flights_seed_is_refused(tmp_path):
    config, _snapshots = _first_phase_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    group = _group()
    program, binding, plan = _binding_and_seed(config)
    tampered = {"s1": ("not-the-real-value",)}

    with pytest.raises(FlightRuntimeError, match="different.*first-phase seed"):
        FlightRuntime._perception_branch_seeds(
            runtime, program, binding, group, tampered, plan,
        )


def test_a_b_branch_knob_reaches_the_router_and_refuses_an_undeclared_path(tmp_path):
    """``fuse_coverage.m`` is an ADMITTED tail (``PERCEPTION_BRANCH_KNOB_
    TAILS``), but this synthetic fixture's ``phase_supply`` spec declares no
    ``fuse_coverage`` key at all -- so a genuinely wired branch router must
    reach ``_supply_action_router``'s own "overrides undeclared path"
    refusal, proving the knob is actually applied rather than silently
    dropped."""

    config, _snapshots = _first_phase_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    group = _group(
        b_overrides={f"knowledge_stores.{STORE}.phase_supply.direct.fuse_coverage.m": 2},
    )
    program, binding, plan = _binding_and_seed(config)
    expected = {
        "s1": (
            "intent-boundaries::value:dim-light",
            "slot-contracts::value:dim-light",
        )
    }

    with pytest.raises(FlightRuntimeError, match="overrides undeclared path"):
        FlightRuntime._perception_branch_seeds(
            runtime, program, binding, group, expected, plan,
        )


def test_branch_identity_receipts_differ_by_declared_axis(tmp_path):
    config, _snapshots = _first_phase_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    group = _group()
    program, binding, plan = _binding_and_seed(config)
    expected = {
        "s1": (
            "intent-boundaries::value:dim-light",
            "slot-contracts::value:dim-light",
        )
    }

    _seeds, receipts = FlightRuntime._perception_branch_seeds(
        runtime, program, binding, group, expected, plan,
    )
    by_id = {row["branch_id"]: row["identity_sha256"] for row in receipts}
    assert len(by_id["A"]) == 64
    # A and T declare no axis at all, so their identity is the same; B
    # declares one knob, so its identity must differ from both.
    assert by_id["A"] == by_id["T"]
    assert by_id["B"] != by_id["A"]


def _presentation_only_group():
    """A ``B`` branch shaped exactly like the real ``b-top2contrast``/
    ``b-list3`` branches this fix was written for: no ``overrides`` (no
    knobs), no ``release_swap`` -- only a ``presentation_id``, which is
    recorded in the identity receipt but never changes the router."""

    branch_b = {
        "branch_id": "B", "max_supplied_items": 8,
        "presentation_id": "top2-contrast-v1",
    }
    return parse_perception_branches(
        {
            "level": 1,
            "fit_estimate": dict(FIT),
            "branches": [
                branch_b,
                {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8},
                {"branch_id": "A", "deliver": True, "max_supplied_items": 8},
            ],
        },
        first_phase_id="direct",
        declared_stores=(STORE, "slot-contracts"),
    )


def test_a_row_with_no_first_phase_candidate_still_reaches_a_presentation_only_branch(
    tmp_path,
):
    """The bug this test pins (2026-09-29): ``_perception_branch_seeds``'s
    live-compute path never applied ``_merge_unconditional_first_phase``, so
    a row neither named store recalls any first-phase candidate for was
    silently absent from a B branch's own seed even when the flight's own
    seed -- built through the SAME merge, over a ``prepared_phase_supply``
    artifact or a ``supply_for_phase`` seed -- still carried it. A
    presentation-only branch (no knobs, no release_swap -- exactly
    ``b-top2contrast``'s shape) must see the SAME row set A does.
    """

    config, _snapshots = _first_phase_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    group = _presentation_only_group()
    program, _binding, plan = _binding_and_seed(config)
    fallback_id = "fallback::unconditional-v1"

    def seam(*, speech_packet_bindings, **_ignored):
        return {
            "direct": {
                sample_id: (fallback_id,)
                for sample_id in sorted(speech_packet_bindings)
            }
        }

    # "s2" has no entry at all in the synthetic store's own query-vector
    # file (only "s1" does), so both named stores' own bootstrap skips it
    # entirely -- the same shape a genuine zero-candidate recall leaves
    # behind (design section 3; docs/readiness/2026-09-28-slurp-fold-b-
    # phase2-inputs-v1/README.md's "known recall property"). The outer
    # binding's ``supply_for_store`` seam is the flight's OWN unconditional
    # route, exactly the seam ``core.flight.runtime._merge_unconditional_
    # first_phase`` reads off ``binding["supply_for_store"]``.
    binding = {
        "speech_packet_bindings": {
            "s1": {"packet_id": "speech/s1", "sha256": "a" * 64},
            "s2": {"packet_id": "speech/s2", "sha256": "c" * 64},
        },
        "supply_for_store": SimpleNamespace(unconditional_first_phase=seam),
    }
    expected = {
        "s1": (
            "intent-boundaries::value:dim-light",
            "slot-contracts::value:dim-light",
            fallback_id,
        ),
        "s2": (fallback_id,),
    }

    seeds, _receipts = FlightRuntime._perception_branch_seeds(
        runtime, program, binding, group, expected, plan,
    )

    assert seeds["A"] == expected
    assert seeds["T"] == expected
    # THE FIX: the presentation-only B branch recalls no candidate of its
    # own for "s2" either, but still carries the row via the same
    # unconditional merge A's own seed used -- matching A's behaviour
    # exactly instead of silently dropping the row.
    assert seeds["B"] == expected
    assert set(seeds["B"]) == {"s1", "s2"}


def test_existing_branches_are_unchanged_when_no_unconditional_route_exists(
    tmp_path,
):
    """Regression pin for the merge-call fix: every cell flown to date binds
    no store with an ``unconditional_first_phase`` seam (``binding`` here
    carries no ``supply_for_store`` at all, exactly like every existing
    caller), so the added merge call is a byte-identical no-op and a row
    WITH a candidate is completely unaffected -- for A, T, and a knob-
    overridden B alike."""

    config, _snapshots = _first_phase_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    group = _group()
    program, binding, plan = _binding_and_seed(config)
    assert "supply_for_store" not in binding
    expected = {
        "s1": (
            "intent-boundaries::value:dim-light",
            "slot-contracts::value:dim-light",
        )
    }

    seeds, _receipts = FlightRuntime._perception_branch_seeds(
        runtime, program, binding, group, expected, plan,
    )

    assert seeds["A"] == expected
    assert seeds["T"] == expected
    # B overrides intent-boundaries' own k to 1 -- still the single
    # recalled facet, byte-identical to its pre-fix value.
    assert seeds["B"] == expected


def test_perception_branches_identity_is_empty_when_undeclared():
    assert _perception_branches_identity(None) == {}
    assert _perception_branches_identity({}) == {}
    assert _perception_branches_identity({"roles": {}}) == {}


def test_perception_branches_identity_reads_the_declared_block():
    branches_block = {"level": 1, "branches": [], "fit_estimate": {}}
    native_episode = {"roles": {"perception": {"branches": branches_block}}}
    assert _perception_branches_identity(native_episode) == branches_block
