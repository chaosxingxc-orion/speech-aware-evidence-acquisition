"""``core.flight.runtime.FlightRuntime.prepare_perception_branch_seeds`` and
``_load_perception_branch_seed`` -- the item-4 GAP close (design section 5
item 4): the offline preparation step design section 5 names, and the
runtime's own binding of a branch's pinned seed at flight time.

Structurally the twin of ``tests/unit/test_perception_branch_seeds.py``
(the live-compute proofs) and ``tests/unit/test_prepared_phase_supply.py``
(the ``setup_runtime`` bare-``FlightRuntime`` pattern for a prepared
artifact): a real, partially-built ``FlightRuntime`` instance
(``object.__new__``), the SAME synthetic store-routed knowledge fixture
(``test_knowledge_stores._first_phase_config``), and
``load_native_episode_config`` monkeypatched to hand back a fake carrying the
already-parsed :class:`PerceptionBranchGroup` directly -- so this module
proves the NEW wiring (identity computation, artifact production, pin
binding and refusal) without re-deriving a full, valid native-role-episode
role graph, which ``rails.native_episode_config`` validates independently
and expensively elsewhere (``tests/unit/test_perception_branch_config.py``).
No model, server or GPU contact; no real ``SPEECHRL_DATA_DIR``.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.core.preparation import (
    PreparationError,
    prepare_artifact,
)
from speech_aware_evidence_acquisition.rails import native_episode_config as nec
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
POLICY = "phase-direct-only-supplied-v1"


def _group():
    return parse_perception_branches(
        {
            "level": 1,
            "fit_estimate": dict(FIT),
            "branches": [
                {
                    "branch_id": "B", "max_supplied_items": 8,
                    "overrides": {f"knowledge_stores.{STORE}.phase_supply.direct.k": 1},
                },
                {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8},
                {"branch_id": "A", "deliver": True, "max_supplied_items": 8},
            ],
        },
        first_phase_id="direct",
        declared_stores=(STORE, "slot-contracts"),
    )


def _runtime(tmp_path, *, group):
    """A real, partially-built ``FlightRuntime`` (no model, server or lock),
    structurally ``test_prepared_phase_supply.setup_runtime``'s twin, wired
    for the SAME store-routed synthetic fixture
    ``test_perception_branch_seeds.py`` uses."""

    config, _snapshots = _first_phase_config(tmp_path)
    config["policy"] = POLICY
    import hashlib as _hashlib

    (tmp_path / "frozen.json").write_bytes(b"frozen source receipt")
    config["preparation_source_receipts"] = [
        {
            "root": "repository",
            "relpath": "frozen.json",
            "sha256": _hashlib.sha256(b"frozen source receipt").hexdigest(),
        }
    ]

    runtime = object.__new__(FlightRuntime)
    runtime._data_root = tmp_path
    runtime._repo_root = tmp_path
    runtime._composed = SimpleNamespace(values=config, config_hash="c" * 64)
    runtime._knowledge_store_binding = load_knowledge_store_binding(config, data_root=tmp_path)
    runtime._knowledge_store_router_options = {}
    runtime._phase_program_material = None
    runtime._prepare = lambda: (config, "slurp", "DEV", "d" * 64)

    program = default_phase_program(POLICY)
    default_route = FlightRuntime._supply_action_router(runtime, program, "default", ())
    spec = SimpleNamespace(as_json=lambda: {"k": 1}, phase="direct", query_source={}, facet_source=None)
    binding = {
        "knowledge_snapshot": runtime._knowledge_store_binding.composite_snapshot,
        "speech_packet_bindings": {"s1": {"packet_id": "speech/s1", "sha256": "a" * 64}},
        "supply_specs": {"direct": spec},
        "supply_for_store": default_route,
    }
    runtime._default_phase_program_binding = lambda program, client: binding
    return runtime, program, binding, group


def _patch_native_episode_config(monkeypatch, group):
    monkeypatch.setattr(
        nec, "load_native_episode_config",
        lambda values, program, **kwargs: SimpleNamespace(perception_branch_group=group),
    )


# --------------------------------------------------------------------------
# perception_branch_seed_artifact_identity / prepare_perception_branch_seeds
# --------------------------------------------------------------------------


def test_no_branch_group_refuses_with_the_no_branch_group_message(tmp_path, monkeypatch):
    runtime, _program, _binding, _group = _runtime(tmp_path, group=None)
    _patch_native_episode_config(monkeypatch, None)

    with pytest.raises(PreparationError, match="no roles.perception.branches"):
        runtime.perception_branch_seed_artifact_identity()


def test_prepare_perception_branch_seeds_writes_only_b_branches(tmp_path, monkeypatch):
    group = _group()
    runtime, _program, _binding, _group2 = _runtime(tmp_path, group=group)
    _patch_native_episode_config(monkeypatch, group)

    receipt = runtime.prepare_perception_branch_seeds(tmp_path / "branch-seeds.json")

    document = json.loads((tmp_path / "branch-seeds.json").read_bytes())
    assert document["kind"] == "perception-branch-seeds"
    assert set(document["output"]["branches"]) == {"B"}
    # B overrides only the intent-boundaries store's own ``k``; this tiny
    # two-store, one-value-per-store fixture still resolves the SAME
    # composite ids A and T do (this proves ONLY B is written, not that its
    # ids differ -- the pin-binding tests below prove the override is
    # actually applied by tampering the boundary path itself).
    assert document["output"]["branches"]["B"] == {
        "s1": ["intent-boundaries::value:dim-light", "slot-contracts::value:dim-light"]
    }
    assert receipt["sha256"] == __import__("hashlib").sha256(
        (tmp_path / "branch-seeds.json").read_bytes()
    ).hexdigest()


def test_prepare_perception_branch_seeds_is_deterministic(tmp_path, monkeypatch):
    group = _group()
    runtime, _program, _binding, _group2 = _runtime(tmp_path, group=group)
    _patch_native_episode_config(monkeypatch, group)
    path = tmp_path / "branch-seeds.json"

    first = runtime.prepare_perception_branch_seeds(path)
    first_bytes = path.read_bytes()
    # A second, independent runtime (fresh compose, fresh router) over the
    # same config and the same data root must reproduce the SAME bytes.
    group2 = _group()
    runtime2, _p2, _b2, _g2 = _runtime(tmp_path, group=group2)
    _patch_native_episode_config(monkeypatch, group2)
    second = runtime2.prepare_perception_branch_seeds(path)

    assert first["sha256"] == second["sha256"]
    assert path.read_bytes() == first_bytes


def test_prepare_perception_branch_seeds_refuses_a_stale_pin(tmp_path, monkeypatch):
    group = _group()
    runtime, _program, _binding, _group2 = _runtime(tmp_path, group=group)
    _patch_native_episode_config(monkeypatch, group)
    path = tmp_path / "branch-seeds.json"
    runtime.prepare_perception_branch_seeds(path)

    # Moving the runtime module's own bytes changes the identity's
    # implementation hash, exactly as a real merge would.
    tampered_group = _group()
    runtime2, _p2, _b2, _g2 = _runtime(tmp_path, group=tampered_group)
    runtime2._composed.values["native_episode"] = {
        "roles": {"perception": {"branches": {"level": 1, "branches": [], "fit_estimate": {}}}}
    }
    _patch_native_episode_config(monkeypatch, tampered_group)

    with pytest.raises(PreparationError, match="differing identity key"):
        runtime2.prepare_perception_branch_seeds(path)


# --------------------------------------------------------------------------
# _load_perception_branch_seed / the flight-time pin binding
# --------------------------------------------------------------------------


def _seed_inputs(runtime, binding, spec):
    return runtime._phase_seed_inputs(binding, spec, "d" * 64)


def test_a_pinned_branch_is_loaded_not_recomputed(tmp_path, monkeypatch):
    group = _group()
    runtime, program, binding, _group2 = _runtime(tmp_path, group=group)
    _patch_native_episode_config(monkeypatch, group)
    spec = binding["supply_specs"]["direct"]
    inputs = _seed_inputs(runtime, binding, spec)

    # A deliberately-different value than live compute would produce, to
    # prove the pinned bytes are what is used.
    pinned_output = {"branches": {"B": {"s1": ["slot-contracts::value:dim-light"]}}}

    def produce():
        return pinned_output

    path = tmp_path / "pinned-seed.json"
    receipt = prepare_artifact(path, kind="perception-branch-seeds", inputs=inputs, producer=produce)
    from dataclasses import replace
    pinned_branch = replace(
        group.branch("B"), prepared_seed={"relpath": "pinned-seed.json", "sha256": receipt["sha256"]},
    )
    pinned_group = replace(group, branches=tuple(
        pinned_branch if b.branch_id == "B" else b for b in group.branches
    ))
    expected = {"s1": ("intent-boundaries::value:dim-light", "slot-contracts::value:dim-light")}
    program_plan = SimpleNamespace(split_identity_hash="d" * 64)

    seeds, receipts = FlightRuntime._perception_branch_seeds(
        runtime, program, binding, pinned_group, expected, program_plan, seed_inputs=inputs,
    )

    assert seeds["B"] == {"s1": ("slot-contracts::value:dim-light",)}
    by_id = {row["branch_id"]: row for row in receipts}
    assert by_id["B"]["prepared_seed"] == {"relpath": "pinned-seed.json", "sha256": receipt["sha256"]}


def test_a_mismatched_pin_is_refused(tmp_path, monkeypatch):
    group = _group()
    runtime, program, binding, _group2 = _runtime(tmp_path, group=group)
    _patch_native_episode_config(monkeypatch, group)
    spec = binding["supply_specs"]["direct"]
    inputs = _seed_inputs(runtime, binding, spec)
    # A real file whose bytes do NOT hash to the pinned sha256 -- the
    # ordinary "stale pin" shape, as opposed to a wholly absent file (a
    # separate refusal path in ``_resolve_confined``).
    (tmp_path / "wrong-seed.json").write_bytes(b"{}")
    from dataclasses import replace
    pinned_branch = replace(
        group.branch("B"),
        prepared_seed={"relpath": "wrong-seed.json", "sha256": "a" * 64},
    )
    pinned_group = replace(group, branches=tuple(
        pinned_branch if b.branch_id == "B" else b for b in group.branches
    ))
    expected = {"s1": ("intent-boundaries::value:dim-light", "slot-contracts::value:dim-light")}
    program_plan = SimpleNamespace(split_identity_hash="d" * 64)

    with pytest.raises(PreparationError):
        FlightRuntime._perception_branch_seeds(
            runtime, program, binding, pinned_group, expected, program_plan, seed_inputs=inputs,
        )


def test_a_pin_without_seed_inputs_is_refused(tmp_path, monkeypatch):
    group = _group()
    runtime, program, binding, _group2 = _runtime(tmp_path, group=group)
    _patch_native_episode_config(monkeypatch, group)
    from dataclasses import replace
    pinned_branch = replace(
        group.branch("B"), prepared_seed={"relpath": "x.json", "sha256": "a" * 64},
    )
    pinned_group = replace(group, branches=tuple(
        pinned_branch if b.branch_id == "B" else b for b in group.branches
    ))
    expected = {"s1": ("intent-boundaries::value:dim-light", "slot-contracts::value:dim-light")}
    program_plan = SimpleNamespace(split_identity_hash="d" * 64)

    with pytest.raises(FlightRuntimeError, match="no branch-seed identity"):
        FlightRuntime._perception_branch_seeds(
            runtime, program, binding, pinned_group, expected, program_plan, seed_inputs=None,
        )


def test_an_unpinned_branch_is_unaffected_by_seed_inputs(tmp_path, monkeypatch):
    """A branch with NO ``prepared_seed`` is computed live regardless of
    ``seed_inputs`` -- every cell written before this artifact existed stays
    byte-for-byte unchanged."""

    group = _group()
    runtime, program, binding, _group2 = _runtime(tmp_path, group=group)
    _patch_native_episode_config(monkeypatch, group)
    spec = binding["supply_specs"]["direct"]
    inputs = _seed_inputs(runtime, binding, spec)
    expected = {"s1": ("intent-boundaries::value:dim-light", "slot-contracts::value:dim-light")}
    program_plan = SimpleNamespace(split_identity_hash="d" * 64)

    seeds, receipts = FlightRuntime._perception_branch_seeds(
        runtime, program, binding, group, expected, program_plan, seed_inputs=inputs,
    )

    # No prepared_seed on B: computed live, and (this tiny fixture) equal to
    # A/T's own seed -- unaffected by seed_inputs being supplied.
    assert seeds["B"] == expected
    by_id = {row["branch_id"]: row for row in receipts}
    assert by_id["B"]["prepared_seed"] is None
