"""SLURP's CONSTRUCTION VARIANT of the module lock (2026-10-12): the lock re-pinned for the construction roster R01C.

WHY. The lock's ``train-exemplars`` pool release (``size-pool-annotated-exemplars``, 37,407 source ids) contains EVERY R01C row, and
``rails.runner.run_speech_native_agent_loop`` refuses a query sample inside the composite knowledge source roster. The committed VAR-2
R01C cell avoided the guard by pinning the ``size-pool-annotated-exemplars-minus-r01`` twin (34,474 source ids, 0 shared with R01C;
receipt ``docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars-minus-r01.json``). This module is that pin as a lock-layer
MECHANISM, not a new lock: a block that names ``construction_roster: "r01c"`` compiles onto the lock layer it selects with exactly two
leaves moved, ``knowledge_stores.train-exemplars.release`` and ``.snapshot`` (the minus-r01 twins). Nothing else changes: no template, knob,
normaliser, tool or other store.

THE ROSTER-OWN AGREEMENT TABLE. The agree-vote-seed table is a function of the roster and the pool (the share of a row's own top-20 pool
recall per boundary intent). R01C's table is ``SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-R01C-V1`` -- built model-free by
``scripts/build_slurp_intent_exemplar_agreement.py`` against the minus-r01 snapshot, so it is the table's minus-r01 twin by construction.
Its pin is part of the variant: a cell on the variant must declare exactly that table (``check_cell``).

FAIL-CLOSED. The variant is accepted only on R01C: ``check_cell`` refuses a cell whose two sealed speech-query vector pins are not R01C's,
and a layer that is not the full-pool lock (v2.3's ``ace-playbook`` i0 anchor names 50 R01C rows, so it would trip the same guard). A block
that names no variant is refused on R01C while it pins the full pool, with the guard's own message.

BOUNDARY. The variant exists ONLY to flow the material-source column (the proposer's tables and the ACE reflector's material) without
self-leakage. It never delivers a benefit claim; the column is a lock column read for material, not an arm against a comparator.
"""

from __future__ import annotations

import copy
from typing import Mapping, Sequence

from ..consumption_module import ConsumptionModuleConfigError, ConstructionHooks

CONSTRUCTION_R01C = "r01c"
#: Both sealed R01C speech-query vector files live here (cell identity, never policy).
R01C_VECTOR_PREFIX = "vectors/slurp-stage3-construction-r01c-v1/"
POOL_STORE = "train-exemplars"
ACE_STORE = "ace-playbook"
FULL_POOL_RELEASE_SHA256 = "171aa4a82c2b15fff2c72e907ea80298be8d72309cca0d7367eb50debb042129"
FULL_POOL_SNAPSHOT_SHA256 = "4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9"
MINUS_R01_POOL_RELEASE = {
    "relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/release.json",
    "sha256": "83620eb0b02f12424a00cd5572904f4df48a49c329b1b0e1a9321d4b9ec14fd0",
}
MINUS_R01_POOL_SNAPSHOT = {
    "relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json",
    "sha256": "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63",
}
#: ``scripts/build_slurp_intent_exemplar_agreement.py`` over the R01C roster against the minus-r01 snapshot (625 rows, 20 votes each).
R01C_AGREEMENT = {
    "relpath": "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-R01C-V1/agreement.jsonl",
    "sha256": "87e253f66f3b5058e7c778034c343c4e9f0b43586d623d8e1fe6508f9bf3abb3",
    "tool_contact_ledger_row": "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-R01C-V1",
}
R01C_AGREEMENT_RECEIPT_SHA256 = "ca6a516a2c2fd883b5b98a81bc02e63e88cef27796056710badd3f40e3bf7818"
AGREEMENT_PATH = ("knowledge_stores", "intent-boundaries", "phase_supply", "perception", "agreement_source")


def _at(node: object, path: Sequence[str]) -> object | None:
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return None
        node = node[key]
    return node


def layer_r01c(lock_layer: Mapping[str, object]) -> Mapping[str, object]:
    """The lock layer with the ``train-exemplars`` pool moved to the minus-r01 twins. Fail-closed on a layer that declares the
    ``ace-playbook`` store (its i0 anchor row names 50 R01C ids) and on a pool that is not the full-pool lock's."""

    layer = copy.deepcopy(dict(lock_layer))
    stores = layer.get("knowledge_stores")
    if not isinstance(stores, dict) or POOL_STORE not in stores:
        raise ConsumptionModuleConfigError(f"construction_roster {CONSTRUCTION_R01C!r}: the lock layer declares no {POOL_STORE!r} store")
    if ACE_STORE in stores:
        raise ConsumptionModuleConfigError(
            f"construction_roster {CONSTRUCTION_R01C!r}: the lock layer declares the {ACE_STORE!r} store, whose i0 anchor row names 50 R01C "
            "source ids -- the runner's knowledge-source guard would refuse every R01C query; compose the construction column on lock v2.2"
        )
    pool = stores[POOL_STORE]
    if (_at(pool, ("release", "sha256")), _at(pool, ("snapshot", "sha256"))) != (FULL_POOL_RELEASE_SHA256, FULL_POOL_SNAPSHOT_SHA256):
        raise ConsumptionModuleConfigError(f"construction_roster {CONSTRUCTION_R01C!r}: the lock layer's pool is not the full-pool release")
    pool["release"], pool["snapshot"] = dict(MINUS_R01_POOL_RELEASE), dict(MINUS_R01_POOL_SNAPSHOT)
    return layer


def construction_hooks(roster_pin_paths: Sequence[Sequence[str]]) -> ConstructionHooks:
    """``CarrierHooks.construction``: the r01c variant and the loader's cell check over the roster-pin paths."""

    def on_r01c(values: Mapping[str, object]) -> tuple[bool, bool]:
        pins = [_at(values, path) for path in roster_pin_paths]
        paths = [str(pin.get("relpath", "")) if isinstance(pin, Mapping) else "" for pin in pins]
        return any(p.startswith(R01C_VECTOR_PREFIX) for p in paths), bool(paths) and all(p.startswith(R01C_VECTOR_PREFIX) for p in paths)

    def check_cell(name: str | None, values: Mapping[str, object]) -> None:
        any_r01c, all_r01c = on_r01c(values)
        pool_snapshot = _at(values, ("knowledge_stores", POOL_STORE, "snapshot", "sha256"))
        if name is None:
            if any_r01c and pool_snapshot == FULL_POOL_SNAPSHOT_SHA256:
                raise ConsumptionModuleConfigError(
                    "AgentLoop query samples overlap the TRAIN knowledge source roster: the lock's train-exemplars pool "
                    "(size-pool-annotated-exemplars) contains every R01C row; declare consumption_module.construction_roster "
                    f"{CONSTRUCTION_R01C!r} so the pool is the minus-r01 twin"
                )
            return
        if name != CONSTRUCTION_R01C or not all_r01c:
            raise ConsumptionModuleConfigError(
                f"construction_roster {name!r} is accepted only on the R01C roster (both sealed speech-query vector pins under "
                f"{R01C_VECTOR_PREFIX})"
            )
        agreement = _at(values, AGREEMENT_PATH)
        if agreement is not None and {k: agreement.get(k) for k in R01C_AGREEMENT} != R01C_AGREEMENT:
            raise ConsumptionModuleConfigError(
                f"construction_roster {name!r}: the cell's agreement table is not the pinned R01C table {R01C_AGREEMENT['relpath']}"
            )

    return ConstructionHooks(variants={CONSTRUCTION_R01C: layer_r01c}, check_cell=check_cell)
