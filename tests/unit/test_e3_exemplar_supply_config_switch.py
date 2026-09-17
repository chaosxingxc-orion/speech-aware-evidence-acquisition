"""E3 harness-admission switch proof (deliverable 7).

``docs/receipts/harness-admission.json``'s ``switch_rule`` recognizes five
classes: the four ``rails.config_tables.CONFIG_TABLE_NAMES`` tables
(``judges``, ``knowledge_views``, ``observe``, ``toolkits``) plus ``run``.
``knowledge_views`` WRAPS the flat ``phase_material``/``phase_supply`` keys
(``rails.config_tables.WRAPPED_FLAT_KEYS``); it does not wrap
``knowledge_stores`` (the named-store block the SLURP native dual-store
anchor and this program's train-exemplars store both use), so a named
store's switch is not literally representable inside any of the five
existing classes. No receipt entry is added here for that reason AND
because no cell has been decided yet (B1 has not flown): the receipt's own
note says it is opened "with exactly the one module this note had the
authority to decide" and refuses entries a verdict has not issued.

What this test proves instead, standing in for the table system's own
"one config key" discipline until B1 is decided and this module earns its
own receipt row: the module's ONE config key, in this baseline fragment
pair, is a single JSON top-level key (``knowledge_stores``) with a single
added child key (``train-exemplars``) -- and, symmetrically, its OWN
sub-block's OFF arm (the k20 fragment with ``train-exemplars`` removed) is
byte-identical to the anchor. The remaining top-level differences are
bookkeeping (attempt/run identity, free-English notes,
``preparation_source_receipts`` provenance) that carries no retrieval or
request behavior -- none of it is ``phase_material``, ``phase_tools``, or
any other request-shaping key.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "configs" / "baseline"

ANCHOR = "slurp-native-dual-store-train-fold-a-anchor-v1.json"
K20 = "slurp-native-dual-store-train-fold-a-exemplars-k20-v1.json"
K20_TWIN = "slurp-native-dual-store-train-fold-a-exemplars-k20-twin-v1.json"
K12 = "slurp-native-dual-store-train-fold-a-exemplars-k12-v1.json"

# Bookkeeping-only top-level keys: identity/attempt ids and free-English
# notes a cell must vary to stay a distinct run identity, none of which the
# frozen core's request depends on.
BOOKKEEPING_KEYS = frozenset(
    {
        "native_contact_fit",
        "speech_feature_key_representation_id",
        "what_this_is",
        "what_the_train_exemplars_store_is",
        "preparation_source_receipts",
    }
)


def _load(name: str) -> dict:
    return json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))


def test_the_k20_fragment_differs_from_the_anchor_by_exactly_one_store():
    anchor = _load(ANCHOR)
    k20 = _load(K20)

    non_bookkeeping_keys = (set(anchor) | set(k20)) - BOOKKEEPING_KEYS
    differing = sorted(
        key for key in non_bookkeeping_keys if anchor.get(key) != k20.get(key)
    )
    assert differing == ["knowledge_stores"]

    anchor_stores, k20_stores = anchor["knowledge_stores"], k20["knowledge_stores"]
    assert set(k20_stores) - set(anchor_stores) == {"train-exemplars"}
    for store_id in anchor_stores:
        assert anchor_stores[store_id] == k20_stores[store_id]

    # Symmetrically: removing the added store from the k20 fragment (the
    # module's OFF arm) reconstructs a knowledge_stores block equal to the
    # anchor's -- the discipline core.config.drop_null_arms enforces for the
    # four wrapped tables, reproduced here by hand for this store block.
    k20_off = copy.deepcopy(k20_stores)
    del k20_off["train-exemplars"]
    assert k20_off == anchor_stores


def test_the_twin_differs_from_the_k20_fragment_by_exactly_the_query_source():
    k20 = _load(K20)
    twin = _load(K20_TWIN)

    non_bookkeeping_keys = (set(k20) | set(twin)) - BOOKKEEPING_KEYS
    differing = sorted(
        key for key in non_bookkeeping_keys if k20.get(key) != twin.get(key)
    )
    assert differing == ["knowledge_stores"]

    k20_solver = k20["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    twin_solver = twin["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    differing_solver_keys = sorted(
        key
        for key in set(k20_solver) | set(twin_solver)
        if k20_solver.get(key) != twin_solver.get(key)
    )
    assert differing_solver_keys == ["query_source"]
    assert k20_solver["k"] == twin_solver["k"] == 20
    assert k20_solver["fuse_coverage"] == twin_solver["fuse_coverage"]


def test_the_k12_fragment_differs_from_k20_by_exactly_k_and_fuse_coverage():
    k20 = _load(K20)
    k12 = _load(K12)

    non_bookkeeping_keys = (set(k20) | set(k12)) - BOOKKEEPING_KEYS
    differing = sorted(
        key for key in non_bookkeeping_keys if k20.get(key) != k12.get(key)
    )
    assert differing == ["knowledge_stores"]

    k20_solver = k20["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    k12_solver = k12["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    differing_solver_keys = sorted(
        key
        for key in set(k20_solver) | set(k12_solver)
        if k20_solver.get(key) != k12_solver.get(key)
    )
    assert differing_solver_keys == ["fuse_coverage", "k"]
    assert k12_solver["k"] == 12
    assert k12_solver["fuse_coverage"] == {"m": 12, "c": 12, "top_l": 12}
