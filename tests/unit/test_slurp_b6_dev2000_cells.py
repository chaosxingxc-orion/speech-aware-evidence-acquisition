"""Proof tests for cell B6 (SLURP direct-vs-plan paired read on the fresh
DEV-2000-ADDED roster; owner decisions 34, 35, 78, 79, 86, 88).

Mirrors ``tests/unit/test_default_plan_lock_cells.py``'s discipline: the
registration's claim that only an enumerated set of roster-bound bindings
moved is a property of bytes, proven here, not asserted in prose.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINES = REPO_ROOT / "configs" / "baseline"
EXPERIMENTS = REPO_ROOT / "configs" / "experiment"

DIRECT_PRECEDENT = BASELINES / "slurp-direct-max512-dev1000-base-replication-v1.json"
DIRECT_NEW = BASELINES / "slurp-direct-max512-dev2000-added-v1.json"
PLAN_PRECEDENT = BASELINES / "slurp-native-default-plan-lock-baseline-v1.json"
PLAN_NEW = BASELINES / "slurp-native-default-plan-dev2000-added-baseline-v1.json"

DIRECT_EXPERIMENT_NEW = EXPERIMENTS / "slurp-direct-max512-dev2000-added-v1.json"
PLAN_EXPERIMENT_NEW = EXPERIMENTS / "slurp-native-default-plan-dev2000-added-v1.json"

MODEL_FRAGMENT = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
DATASET_FRAGMENT = "slurp-speech-native-dev2000-added"

#: (a) the plan-arm baseline differs from cell PLAN's ONLY in these roster-bound bindings.
PLAN_BASELINE_CHANGED_PATHS = frozenset({
    "knowledge_stores.intent-boundaries.phase_supply.perception.query_source.embedded_signal",
    "knowledge_stores.intent-boundaries.phase_supply.perception.query_source.relpath",
    "knowledge_stores.intent-boundaries.phase_supply.perception.query_source.sha256",
    "knowledge_stores.intent-boundaries.phase_supply.perception.query_source.tool_contact_ledger_row",
    "knowledge_stores.train-exemplars.phase_supply.solver.query_source.embedded_signal",
    "knowledge_stores.train-exemplars.phase_supply.solver.query_source.relpath",
    "knowledge_stores.train-exemplars.phase_supply.solver.query_source.sha256",
    "knowledge_stores.train-exemplars.phase_supply.solver.query_source.tool_contact_ledger_row",
    "native_contact_fit.attempt_id",
    "native_contact_fit.contact_cap",
    "native_contact_fit.run_id",
    "preparation_source_receipts",
    "prepared_phase_supply",
    "scorers",
    "speech_packet_promotion_receipt",
    "speech_packet_promotion_receipt_sha256",
    "what_the_train_exemplars_store_is",
    "what_this_is",
})

#: (b) the direct baseline differs from the DEV-1000 precedent ONLY in these bindings.
DIRECT_BASELINE_CHANGED_PATHS = frozenset({
    "live_phase_fit.attempt_id",
    "live_phase_fit.run_id",
    "speech_packet_promotion_receipt",
    "speech_packet_promotion_receipt_sha256",
    "what_this_is",
})


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _diff_paths(a: object, b: object, prefix: str = "") -> set[str]:
    """Every dotted path whose leaf value differs between ``a`` and ``b``,
    or whose key is present on only one side. A changed dict-valued key is
    reported once at that key's own path (not recursed into) so a key
    replaced by an equal-shaped-but-different dict still shows one path,
    matching how ``PLAN_BASELINE_CHANGED_PATHS`` names whole blocks such as
    ``prepared_phase_supply``."""

    if isinstance(a, dict) and isinstance(b, dict):
        paths: set[str] = set()
        for key in set(a) | set(b):
            child = f"{prefix}.{key}" if prefix else key
            if key not in a or key not in b:
                paths.add(child)
            else:
                paths |= _diff_paths(a[key], b[key], child)
        return paths
    return set() if a == b else {prefix}


def test_plan_arm_baseline_differs_from_cell_plan_only_in_the_enumerated_bindings():
    plan, new = _load(PLAN_PRECEDENT), _load(PLAN_NEW)
    # the prepared-supply pin diffs as a whole key while unpinned and as two leaves once the flip pins it
    diff = frozenset("prepared_phase_supply" if path.startswith("prepared_phase_supply") else path for path in _diff_paths(plan, new))
    assert diff == PLAN_BASELINE_CHANGED_PATHS
    # Untouched: native_episode, phase_material, policy, both non-query_source
    # store blocks, geometry, and the E13/E20/E22 declarations.
    assert plan["native_episode"] == new["native_episode"]
    assert plan["phase_material"] == new["phase_material"]
    assert plan["policy"] == new["policy"]
    assert plan["knowledge_stores"]["slot-contracts"] == new["knowledge_stores"]["slot-contracts"]
    assert (
        plan["knowledge_stores"]["intent-boundaries"]["release"]
        == new["knowledge_stores"]["intent-boundaries"]["release"]
    )
    assert (
        plan["knowledge_stores"]["train-exemplars"]["release"]
        == new["knowledge_stores"]["train-exemplars"]["release"]
    )
    assert plan["serving_slot_tokens"] == new["serving_slot_tokens"]
    assert plan["serving_slots"] == new["serving_slots"]
    assert new["scorers"] == ["slurp-slu-official", "cost"]
    # Registered without a pin; the re-pin flip (item E38 era, 9bc4e087) prepares the supply model-free
    # under this cell's OWN run id, so once flipped the pin must point there and nowhere else.
    pin = new.get("prepared_phase_supply")
    assert pin is None or pin["relpath"].startswith("prepared/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1/")


def test_direct_arm_baseline_differs_from_dev1000_only_in_the_enumerated_bindings():
    dev1000, new = _load(DIRECT_PRECEDENT), _load(DIRECT_NEW)
    assert _diff_paths(dev1000, new) == DIRECT_BASELINE_CHANGED_PATHS
    assert dev1000["scorers"] == new["scorers"] == ["slurp-slu-official", "slurp-slu", "cost"]
    assert dev1000["policy"] == new["policy"]
    assert dev1000["task_instruction_template"] == new["task_instruction_template"]
    assert dev1000["knowledge_snapshot_relpath"] == new["knowledge_snapshot_relpath"]


def test_scorers_are_the_devel_gold_scorers_not_the_train_siblings():
    direct = _load(DIRECT_NEW)
    plan = _load(PLAN_NEW)
    assert direct["scorers"] == ["slurp-slu-official", "slurp-slu", "cost"]
    assert plan["scorers"] == ["slurp-slu-official", "cost"]
    for scorer in direct["scorers"] + plan["scorers"]:
        assert not scorer.endswith("-train")


def test_both_experiment_fragments_compose():
    from speech_aware_evidence_acquisition.core.config import compose

    direct_experiment = _load(DIRECT_EXPERIMENT_NEW)
    direct_cell = direct_experiment["cells"][0]
    direct_composed = compose(
        REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT,
        direct_cell["baseline_fragment"], DIRECT_EXPERIMENT_NEW.stem,
    )
    assert direct_composed.config_hash

    plan_experiment = _load(PLAN_EXPERIMENT_NEW)
    plan_cell = plan_experiment["cells"][0]
    plan_composed = compose(
        REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT,
        plan_cell["baseline_fragment"], PLAN_EXPERIMENT_NEW.stem,
    )
    assert plan_composed.config_hash
    assert plan_composed.values["carrier_lock_key"] == "slurp"
    assert plan_composed.values["population"]["split_identity_hash"] == (
        "ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67"
    )


def test_plan_arm_composed_config_loads_through_the_native_episode_loader():
    from speech_aware_evidence_acquisition.core.config import compose
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config

    composed = compose(
        REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT,
        "slurp-native-default-plan-dev2000-added-baseline-v1",
        "slurp-native-default-plan-dev2000-added-v1",
    )
    program = default_phase_program(str(composed.values["policy"]))
    native_config = load_native_episode_config(composed.values, program)
    assert native_config is not None
    assert native_config.deliver_normaliser_id == "saea-deliver-normalise-v3"


DATA_ROOT_ENV = "SPEECHRL_DATA_DIR"

_DATA_ROOT_BINDINGS = [
    (
        "vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl",
        "e2a5fd046dac7c87fcf53830955e41e69d20402a2305a02ebf2bfc1a33001b9d",
    ),
    (
        "vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl",
        "7d4ebdce553fd897fa86cc6b6d878ebf2298e19ee509eeceaf1aa0aca4855ee0",
    ),
    (
        "prepared/SAEA-SLURP-DEV2000-ADDED-ALIAS-V1/query-dimension-alias.json",
        "9d41262d18b7dc524807e36fb1d97b859f43920524a6dfe85f1bead2b07a5768",
    ),
    (
        "preparation-runs/SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json",
        "9c2b6cdcb17ca3b1ad35b599217ca4e7d84f3c7e5a5d55056bdbf7d92fc9dc9d",
    ),
]

_REPO_BINDINGS = [
    (
        "docs/receipts/rosters/slurp-dev-2000-added-v1.json",
        "f78dd8ad2894b1fd02bfe6050e39e3fb2c5d178a649e5d20e85ea4ecf4b8dc58",
    ),
]


def test_every_pinned_sha256_matches_the_bytes_on_disk():
    import hashlib

    for relpath, expected in _REPO_BINDINGS:
        path = REPO_ROOT / relpath
        assert path.is_file(), f"missing repo file: {relpath}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected

    raw_root = os.environ.get(DATA_ROOT_ENV, "").strip()
    if not raw_root or not Path(raw_root).is_dir():
        pytest.skip(f"{DATA_ROOT_ENV} is not reachable in this environment; skipping data-root hash checks")
    root = Path(raw_root)
    for relpath, expected in _DATA_ROOT_BINDINGS:
        path = root / relpath
        assert path.is_file(), f"missing data-root file: {relpath}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
