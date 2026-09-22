"""Stage-3 S3-6 proof obligation: the delta-cell baseline fragment differs
from the locked PLAN fragment ONLY in the ONE added store
(``knowledge_stores.stage3-deltas``) plus the per-flight bookkeeping keys
this cell must re-prepare under its own run id -- the same exclusion set the
locked plan's own proof test already uses against its predecessor
(``configs/baseline/slurp-native-default-plan-lock-baseline-v1.json``
``the_one_difference_from_slurp_direct_closed_list``-style precedent).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = REPO_ROOT / "configs" / "baseline" / "slurp-native-default-plan-lock-baseline-v1.json"

_BOOKKEEPING_KEYS = {
    "native_contact_fit",
    "prepared_phase_supply",
    "preparation_source_receipts",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "speech_packet_promotion_receipt",
    "speech_packet_promotion_receipt_sha256",
}
_DOC_KEYS = {
    "what_this_is",
    "what_the_train_exemplars_store_is",
    "what_the_stage3_deltas_store_is",
    "knowledge_stores_note",
    "smoke_note",
}
_EXCLUDED_KEYS = _BOOKKEEPING_KEYS | _DOC_KEYS


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _comparable(document: dict) -> dict:
    return {key: value for key, value in document.items() if key not in _EXCLUDED_KEYS}


def _assert_only_stage3_deltas_added(plan_ks: dict, cell_ks: dict) -> None:
    assert set(cell_ks) == set(plan_ks) | {"stage3-deltas"}
    for store_id in plan_ks:
        assert cell_ks[store_id] == plan_ks[store_id]


def test_generation_cell_differs_from_plan_only_by_the_one_store() -> None:
    plan = _load(PLAN_PATH)
    cell = _load(REPO_ROOT / "configs" / "baseline" / "slurp-native-stage3-delta-cell-baseline-v1.json")
    plan_ks = plan.pop("knowledge_stores")
    cell_ks = cell.pop("knowledge_stores")
    assert _comparable(plan) == _comparable(cell)
    _assert_only_stage3_deltas_added(plan_ks, cell_ks)
    store = cell_ks["stage3-deltas"]
    assert store["store_role"] == "stage3-deltas"
    assert set(store["context_supply"]) == {"solver"}
    solver_spec = store["context_supply"]["solver"]
    assert solver_spec["cap"] == 8
    assert solver_spec["rank_by"] == "prior_score"
    assert solver_spec["provider"] == "stage3-delta-candidate-bound-v1"


def test_twin_cell_differs_from_generation_cell_only_by_the_release_namespace() -> None:
    generation = _load(REPO_ROOT / "configs" / "baseline" / "slurp-native-stage3-delta-cell-baseline-v1.json")
    twin = _load(REPO_ROOT / "configs" / "baseline" / "slurp-native-stage3-delta-cell-twin-baseline-v1.json")
    gen_store = generation["knowledge_stores"].pop("stage3-deltas")
    twin_store = twin["knowledge_stores"].pop("stage3-deltas")
    assert generation["knowledge_stores"] == twin["knowledge_stores"]
    assert "twin" in twin_store["snapshot"]["relpath"]
    assert "twin" not in gen_store["snapshot"]["relpath"]
    assert gen_store["context_supply"] == twin_store["context_supply"]


def test_every_pin_left_for_root_is_an_explicit_pending_token() -> None:
    for filename in (
        "slurp-native-stage3-delta-cell-baseline-v1.json",
        "slurp-native-stage3-delta-cell-twin-baseline-v1.json",
        "slurp-native-stage3-delta-cell-smoke-4-baseline-v1.json",
        "slurp-native-stage3-delta-cell-twin-smoke-4-baseline-v1.json",
    ):
        document = _load(REPO_ROOT / "configs" / "baseline" / filename)
        for key in _BOOKKEEPING_KEYS:
            value = document[key]
            assert isinstance(value, str) and value.startswith("PENDING_"), (filename, key, value)
        store = document["knowledge_stores"]["stage3-deltas"]
        assert store["snapshot"]["sha256"].startswith("PENDING_")
        assert store["release"]["sha256"].startswith("PENDING_")


def test_smoke_variants_carry_the_same_store_shape_as_their_full_siblings() -> None:
    full = _load(REPO_ROOT / "configs" / "baseline" / "slurp-native-stage3-delta-cell-baseline-v1.json")
    smoke = _load(REPO_ROOT / "configs" / "baseline" / "slurp-native-stage3-delta-cell-smoke-4-baseline-v1.json")
    assert (
        full["knowledge_stores"]["stage3-deltas"]["context_supply"]
        == smoke["knowledge_stores"]["stage3-deltas"]["context_supply"]
    )
