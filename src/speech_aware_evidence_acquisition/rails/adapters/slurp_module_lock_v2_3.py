"""SLURP lock v2.3: v2.2 plus the ``ace-playbook`` store declared at its EMPTY release i0.

Owner decisions 263 A / 266-A (2026-10-11); design
``docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md`` sections 4.1, 4.5 and 6.

v2.3 is a DECLARATION-ONLY successor. Its layer is the v2.2 layer with exactly one more entry, ``knowledge_stores.ace-playbook``
(store role ``stage3-deltas``, ``context_supply`` routed to the Solver, release and snapshot pinned to the empty iteration-0
playbook that ``scripts/build_ace_playbook_i0_release.py`` prepared). Nothing else moves: not a template, a knob, a normaliser, a
tool or a supply route of another store. The i0 release is one inert anchor row addressed to the node ``planner``; the Solver slice of
the store is empty, so the Solver route declines every phase and every request renders byte-identical to lock v2.2's (proof P-ACE-0,
``tests/unit/test_lock_v2_3_ace_store.py``). The lock exists so that a supply column can ``release_swap`` the store to
``ace-playbook-i<t>``: the compiler and the loader take a swap store from the lock layer only
(``consumption_module._compile_supply_columns``, ``verify_declared_module``), and the lock never declared one before.

The store is a COMPARATOR substrate (decision 263 A, question 2): the ACE column is non-delivering and can never be locked, so v2.3
adds no delivered behaviour. Cells flown on v2.2 stay valid; a block selects v2.3 only through its ``lock`` key (or, since this
successor is the module's ``CURRENT_LOCK``, as the null arm of new cells).

CONSTRUCTION VARIANT (2026-10-12). Both locks have a construction variant, ``consumption_module.construction_roster: "r01c"``
(``slurp_module_construction.py``), which re-pins the ``train-exemplars`` pool to the minus-r01 twin so the construction roster R01C
(whose rows lie inside the lock's own pool) passes the runner's knowledge-source guard. It is a mechanism over the lock, not a lock: every
other leaf is byte-identical, the loader accepts it only on R01C, and v2.3 refuses it (the ``ace-playbook`` i0 anchor names 50 R01C ids).
It exists ONLY to flow the material-source column (the typed loop's proposer tables and ACE reflector material) without self-leakage; it
never delivers a benefit claim.
"""

from __future__ import annotations

import copy
from typing import Callable, Mapping

from . import slurp_module_lock_v2_2 as lock_v2_2

LOCK_V2_3 = "v2.3"
ACE_STORE_ID = "ace-playbook"
ACE_STORE_ROLE = "stage3-deltas"
#: The Solver cap of the route (the ACE allowance A = 8 items of the design, 4.3).
ACE_SOLVER_CAP = 8
#: ``scripts/build_ace_playbook_i0_release.py`` receipt
#: ``docs/readiness/2026-10-11-slurp-tfrl-loop-v1/ace-playbook-i0-release-receipt-v1.json``.
ACE_I0_RELEASE = {
    "relpath": "knowledge/slurp/semantic/ace-playbook-i0/release.json",
    "sha256": "4013e503c35fbd44a6e40b0f05488ef2c2c124e0367665701c778728c1fd596d",
}
ACE_I0_SNAPSHOT = {
    "relpath": "knowledge/slurp/semantic/ace-playbook-i0/snapshot.json",
    "sha256": "3c9f36f9a3cea26d1c6b5e52c720022ba4f96ccf20c043023737202c8a12b1e2",
}

#: ``{lock version: the deliver normaliser id its layer carries}`` -- v2.3 keeps v2.2's v4g.
LOCK_DELIVER_NORMALISERS: Mapping[str, str] = {
    **lock_v2_2.LOCK_DELIVER_NORMALISERS,
    LOCK_V2_3: lock_v2_2.LOCK_V2_2_DELIVER_NORMALISER,
}


def ace_store_i0() -> dict:
    """The ``knowledge_stores.ace-playbook`` entry v2.3 declares (a fresh copy)."""

    return {
        "context_supply": {
            "solver": {
                "candidate_state_phase": "perception", "cap": ACE_SOLVER_CAP, "node_target": "solver",
                "provider": "stage3-delta-candidate-bound-v1", "rank_by": "prior_score",
            }
        },
        "release": dict(ACE_I0_RELEASE),
        "snapshot": dict(ACE_I0_SNAPSHOT),
        "store_role": ACE_STORE_ROLE,
    }


def lock_deliver_normalisers() -> Mapping[str, Callable[[], str]]:
    """The ``CarrierHooks.lock_deliver_normalisers`` table, v2.0 through v2.3."""

    return {lock: (lambda name=name: name) for lock, name in LOCK_DELIVER_NORMALISERS.items()}


def layer_from_v2_2(v2_2_layer: Mapping[str, object]) -> Mapping[str, object]:
    """The v2.2 layer with the ``ace-playbook`` store declared at release i0. Fail-closed when the v2.2 layer already
    declares a store of that id or carries no ``knowledge_stores`` mapping."""

    from ..consumption_module import ConsumptionModuleConfigError  # noqa: PLC0415

    layer = copy.deepcopy(dict(v2_2_layer))
    stores = layer.get("knowledge_stores")
    if not isinstance(stores, dict) or ACE_STORE_ID in stores:
        raise ConsumptionModuleConfigError(
            f"lock {LOCK_V2_3}: the v2.2 layer must declare knowledge_stores without a {ACE_STORE_ID!r} entry"
        )
    layer["knowledge_stores"] = {**stores, ACE_STORE_ID: ace_store_i0()}
    return layer
