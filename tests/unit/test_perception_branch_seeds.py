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


def test_perception_branches_identity_is_empty_when_undeclared():
    assert _perception_branches_identity(None) == {}
    assert _perception_branches_identity({}) == {}
    assert _perception_branches_identity({"roles": {}}) == {}


def test_perception_branches_identity_reads_the_declared_block():
    branches_block = {"level": 1, "branches": [], "fit_estimate": {}}
    native_episode = {"roles": {"perception": {"branches": branches_block}}}
    assert _perception_branches_identity(native_episode) == branches_block
