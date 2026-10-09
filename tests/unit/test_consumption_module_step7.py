"""Evidence-consumption module, migration step 7 (NX, 2026-10-09): lock v2.2.

``saea-deliver-normalise-v4g`` (version 1) becomes the SLURP default delivery
normaliser under the lock id ``v2.2`` (component ``delivery-normaliser``, state
``on (lock)``; record ``docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md``).
The change is OPT-IN by lock id: a block naming no ``lock``, ``v2.0`` or ``v2.1``
keeps v3, the other carriers are unchanged, and the composed config hashes of
the registered module / NX R1 cells do not move (those hashes are pinned below
from the tree at master 8d61c14b2, BEFORE this step).

Model-free throughout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "scripts" / "analysis") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts" / "analysis"))

import module_equivalence_proof as proof  # noqa: E402

from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters import (  # noqa: E402
    audio2tool_module_hooks as ah, earnings22_module_hooks as e22h, earnings_module_hooks as eh,
    slurp_module_hooks as smh, slurp_module_lock_v2_2 as l22,
)

V3, V4G = "saea-deliver-normalise-v3", "saea-deliver-normalise-v4g"
LEAF = "native_episode.deliver_normaliser.normaliser"

#: Composed config hashes BEFORE step 7 (arm, smoke) of the three registered module cells.
COMPOSED_HASHES_BEFORE = {
    "slurp-native-stage3-module-comp1b-dev2000-added-v1":
        "1f1208d9540051d454a427886d914260aaa20474b8d57cfcfe059bf081ff58eb",
    "slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-v1":
        "67d8be44ead7d882f4a98da82a200f6cb775c828b500831ba4031c58f6ad3fe4",
    "slurp-native-stage3-nx-r1-solver-fold-b-v1":
        "a31825ae0c0f8b03312911403c86cee3ee8f03420d2a5cf21860c6ea7284eae2",
    "slurp-native-stage3-nx-r1-solver-fold-b-smoke-4-v1":
        "1c407d10926d0357534fb4f5f9193d63e61acb2c4530fdff47b17493cc737a02",
    "slurp-native-stage3-nx-r1-i2-solver-fold-b-v1":
        "ed16cc5f3ba29c33cfe6119605da761610b2323fa685692ffd6139cacf71bb10",
    "slurp-native-stage3-nx-r1-i2-solver-fold-b-smoke-4-v1":
        "062ee067e5f2ef079935680f92cbfdcbc3673cb0467939c7f3ca55649106534d",
}


def _hooks():
    return smh.carrier_module_hooks(repo_root=_REPO)


@pytest.mark.parametrize("experiment", sorted(COMPOSED_HASHES_BEFORE))
def test_the_registered_cells_compose_to_their_pre_step7_hashes(experiment):
    cell = json.loads((_REPO / "configs" / "experiment" / f"{experiment}.json").read_text(encoding="utf-8"))["cells"][0]
    composed = compose(_REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
    assert composed.config_hash == COMPOSED_HASHES_BEFORE[experiment]


def test_the_slurp_default_resolves_per_lock_id():
    assert l22.default_deliver_normaliser_for_lock(None) == V3
    assert l22.default_deliver_normaliser_for_lock("v2.0") == V3
    assert l22.default_deliver_normaliser_for_lock("v2.1") == V3
    assert l22.default_deliver_normaliser_for_lock("v2.2") == V4G
    with pytest.raises(KeyError):
        l22.default_deliver_normaliser_for_lock("v9.9")
    hooks = _hooks()
    assert hooks.default_deliver_normaliser() == V3  # the no-lock default is untouched
    assert {k: v() for k, v in hooks.lock_deliver_normalisers.items()} == {"v2.0": V3, "v2.1": V3, "v2.2": V4G}
    assert V4G in DELIVERY_NORMALISERS.names()
    assert l22.LOCK_V2_2_COMPONENT_STATES["delivery-normaliser"]["state"] == "on (lock)"


def test_current_lock_is_not_moved_by_step_7():
    assert smh.CURRENT_LOCK == _hooks().current_lock == "v2.1"


def test_lock_v2_2_is_the_v2_1_layer_with_exactly_the_normaliser_leaf_moved():
    hooks = _hooks()
    v21, v22 = dict(hooks.lock_versions["v2.1"]()), dict(hooks.lock_versions["v2.2"]())
    assert cm.differing_paths(v21, v22) == [LEAF]
    assert v21["native_episode"]["deliver_normaliser"] == {"normaliser": V3}
    assert v22["native_episode"]["deliver_normaliser"] == {"normaliser": V4G}


def test_all_off_blocks_compile_per_lock_and_old_locks_keep_v3():
    hooks = _hooks()
    for lock, expected in ((None, V3), ("v2.0", V3), ("v2.1", V3), ("v2.2", V4G)):
        composed = cm.compile_module(proof.module_block((), lock=lock), hooks)
        assert composed.values()["native_episode"]["deliver_normaliser"]["normaliser"] == expected
        assert composed.lock_version == lock


def test_a_v4g_layer_is_refused_under_a_lock_that_expects_v3(monkeypatch):
    hooks = _hooks()
    versions = dict(hooks.lock_versions)
    versions["v2.1"] = versions["v2.2"]
    bad = smh.carrier_module_hooks(repo_root=_REPO)
    bad = type(bad)(**{**{f: getattr(bad, f) for f in type(bad).__dataclass_fields__}, "lock_versions": versions})
    with pytest.raises(cm.ConsumptionModuleConfigError, match="default deliver normaliser"):
        cm.compile_module(proof.module_block((), lock="v2.1"), bad)


def test_no_stage_or_contract_composes_onto_the_v4g_lock():
    hooks = _hooks()
    for component in (cm.SCOPE_RULE, cm.SOLVER_CITATION_CONTRACT):
        # accepted on v2.1 ...
        cm.compile_module(proof.module_block((component,), lock="v2.1"), hooks)
        # ... refused on v2.2 (no registered composition with v4g).
        with pytest.raises(cm.ConsumptionModuleConfigError, match="no registered composition"):
            cm.compile_module(proof.module_block((component,), lock="v2.2"), hooks)


def test_the_other_carriers_are_unchanged():
    a2t, e21, e22 = ah.carrier_module_hooks(), eh.carrier_module_hooks(), e22h.carrier_module_hooks()
    assert a2t.default_deliver_normaliser is None
    assert e21.default_deliver_normaliser() == eh.DEFAULT_DELIVER_NORMALISER
    assert e22.default_deliver_normaliser() == e22h.DEFAULT_DELIVER_NORMALISER
    for hooks in (a2t, e21, e22):
        assert hooks.lock_deliver_normalisers is None
        assert hooks.lock_versions is None and hooks.current_lock is None
