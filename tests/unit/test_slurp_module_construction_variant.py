"""The CONSTRUCTION VARIANT of the SLURP module lock (``rails/adapters/slurp_module_construction.py``, 2026-10-12).

Model-free and offline. Proves, on the committed construction-source cells (never written here):

* the variant moves exactly the ``train-exemplars`` release and snapshot (the minus-r01 twins) and nothing else, and its pins are the ones the
  committed VAR-2 R01C cell and the minus-r01 receipt carry;
* the loader (``verify_declared_module`` under the real hooks) accepts the variant only on R01C, refuses an unknown variant, a stale
  agreement pin and lock v2.3, and refuses the PLAIN lock on R01C with the runner guard's own message;
* the runner's roster intersection (``KnowledgeStoreBinding.composite_snapshot.source_sample_ids`` against the roster, the exact expression of
  ``run_speech_native_agent_loop``) is empty for all 625 R01C rows under the variant and non-empty under the plain lock (data root required);
* ``slurp_module_hooks.py`` stays within its 260-line limit.

No contact, no write to the data root, no utterance text or label.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "src", REPO / "scripts" / "flights" / "tfrl"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import tfrl_family as tf  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters import slurp_module_construction as variant  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding  # noqa: E402

DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
CELL = tf.const_names("arm")["baseline"]
VAR2 = "slurp-native-stage3-var2-supply-variants-r01c-baseline-v1"
Q = cm.ConsumptionModuleConfigError


def cell(name: str = CELL) -> dict:
    return json.loads((REPO / "configs" / "baseline" / f"{name}.json").read_text(encoding="utf-8"))


def block_of(document: dict) -> dict:
    return document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]


def test_the_hooks_file_stays_within_its_line_limit():
    lines = (REPO / "src/speech_aware_evidence_acquisition/rails/adapters/slurp_module_hooks.py").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 260


def test_the_variant_pins_are_the_ones_the_committed_r01c_cell_and_the_minus_r01_receipt_carry():
    pool = cell(VAR2)["knowledge_stores"]["train-exemplars"]
    assert pool["release"] == variant.MINUS_R01_POOL_RELEASE and pool["snapshot"] == variant.MINUS_R01_POOL_SNAPSHOT
    receipt = [r for r in cell(VAR2)["preparation_source_receipts"] if r["relpath"].endswith("size-pool-annotated-exemplars-minus-r01.json")]
    assert len(receipt) == 1 and receipt[0]["root"] == "repository"
    cell_pool = cell()["knowledge_stores"]["train-exemplars"]
    assert cell_pool["release"] == variant.MINUS_R01_POOL_RELEASE and cell_pool["snapshot"] == variant.MINUS_R01_POOL_SNAPSHOT
    # the lock layer's own pool is the full pool the variant refuses to run on
    lock = carrier_module_hooks().lock_versions["v2.2"]()["knowledge_stores"]["train-exemplars"]
    assert (lock["release"]["sha256"], lock["snapshot"]["sha256"]) == (variant.FULL_POOL_RELEASE_SHA256, variant.FULL_POOL_SNAPSHOT_SHA256)


def test_the_variant_layer_moves_exactly_the_two_pool_pins():
    hooks = carrier_module_hooks()
    plain = hooks.lock_versions["v2.2"]()
    moved = hooks.construction.variants["r01c"](plain)
    assert cm.differing_paths(plain, moved) == [
        "knowledge_stores.train-exemplars.release.relpath", "knowledge_stores.train-exemplars.release.sha256",
        "knowledge_stores.train-exemplars.snapshot.relpath", "knowledge_stores.train-exemplars.snapshot.sha256"]
    # a pure function: the input layer is untouched and the output is stable
    assert hooks.construction.variants["r01c"](plain) == moved
    assert plain["knowledge_stores"]["train-exemplars"]["snapshot"]["sha256"] == variant.FULL_POOL_SNAPSHOT_SHA256


def test_the_variant_refuses_lock_v2_3_a_foreign_pool_and_an_unknown_name():
    hooks = carrier_module_hooks()
    with pytest.raises(Q, match="ace-playbook"):
        hooks.construction.variants["r01c"](hooks.lock_versions["v2.3"]())
    layer = copy.deepcopy(dict(hooks.lock_versions["v2.2"]()))
    layer["knowledge_stores"]["train-exemplars"]["snapshot"]["sha256"] = "0" * 64
    with pytest.raises(Q, match="not the full-pool release"):
        hooks.construction.variants["r01c"](layer)
    block = {**block_of(cell()), "construction_roster": "r02"}
    with pytest.raises(Q, match="not a construction variant"):
        cm.compile_module(block, hooks, repo_root=REPO)
    with pytest.raises(Q, match="construction_roster must match"):
        cm.parse_consumption_module_block({**block_of(cell()), "construction_roster": 7}, repo_root=REPO)


def test_the_loader_accepts_the_committed_cells_and_the_block_hash_names_the_variant():
    for name in (CELL, tf.const_names("smoke")["baseline"]):
        document = cell(name)
        cm.verify_declared_module(block_of(document), document, repo_root=REPO)
        assert block_of(document)["construction_roster"] == "r01c"
        assert cm.parse_consumption_module_block(block_of(document), repo_root=REPO).construction_roster == "r01c"
    # naming the variant is part of the block identity
    plain = {k: v for k, v in block_of(cell()).items() if k != "construction_roster"}
    assert cm.parse_consumption_module_block(plain, repo_root=REPO).block_sha256 != cm.parse_consumption_module_block(block_of(cell()), repo_root=REPO).block_sha256


def test_the_loader_refuses_the_variant_on_any_roster_that_is_not_r01c():
    document = cell()
    other = copy.deepcopy(document)
    for path in variant_roster_paths():
        node = other
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = dict(node[path[-1]], relpath="vectors/slurp-evo-fold-b-v2/query-vectors-speech-segments.jsonl")
    with pytest.raises(Q, match="accepted only on the R01C roster"):
        cm.verify_declared_module(block_of(other), other, repo_root=REPO)
    # one R01C pin is not enough: BOTH sealed vector pins must be R01C's
    half = copy.deepcopy(document)
    path = variant_roster_paths()[0]
    node = half
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = dict(node[path[-1]], relpath="vectors/slurp-evo-fold-b-v2/query-vectors-speech-segments.jsonl")
    with pytest.raises(Q, match="accepted only on the R01C roster"):
        cm.verify_declared_module(block_of(half), half, repo_root=REPO)


def variant_roster_paths():
    from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import ROSTER_PIN_PATHS  # noqa: PLC0415

    return ROSTER_PIN_PATHS


def test_the_loader_refuses_a_stale_agreement_table_under_the_variant():
    document = cell()
    stale = copy.deepcopy(document)
    stale["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["agreement_source"]["sha256"] = "0" * 64
    with pytest.raises(Q, match="not the pinned R01C table"):
        cm.verify_declared_module(block_of(stale), stale, repo_root=REPO)


def test_the_plain_lock_on_r01c_is_refused_with_the_guards_own_message():
    document = cell()
    plain_block = {k: v for k, v in block_of(document).items() if k != "construction_roster"}
    composed = cm.compile_module(plain_block, carrier_module_hooks(), repo_root=REPO)
    plain = composed.apply_to(copy.deepcopy(document))
    plain["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY] = plain_block
    assert plain["knowledge_stores"]["train-exemplars"]["snapshot"]["sha256"] == variant.FULL_POOL_SNAPSHOT_SHA256
    with pytest.raises(Q, match="AgentLoop query samples overlap the TRAIN knowledge source roster"):
        cm.verify_declared_module(plain_block, plain, repo_root=REPO)


def test_a_non_r01c_cell_on_the_plain_lock_is_untouched_by_the_check():
    """The plain-lock refusal keys on the R01C vector pins: a Fold B module cell on the plain lock still verifies."""

    hooks = carrier_module_hooks()
    fold_b = copy.deepcopy(cell())
    for path in variant_roster_paths():
        node = fold_b
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = dict(node[path[-1]], relpath="vectors/slurp-evo-fold-b-v2/query-vectors-speech-segments.jsonl")
    fold_b["knowledge_stores"]["train-exemplars"]["snapshot"] = {"relpath": "x", "sha256": variant.FULL_POOL_SNAPSHOT_SHA256}
    assert hooks.construction.check_cell(None, fold_b) is None
    assert hooks.construction.check_cell(None, {"knowledge_stores": {}}) is None


@pytest.mark.skipif(not (DATA / "knowledge").is_dir(), reason="the data root is not mounted")
def test_the_runner_roster_intersection_is_empty_for_all_625_rows_under_the_variant_and_not_under_the_plain_lock():
    """The expression of ``run_speech_native_agent_loop`` (``set(sample_ids) & set(knowledge_snapshot.source_sample_ids)``) over the composite
    of the stores the cell declares, loaded by the real store loader. Not a flight: no query, no model."""

    roster = json.loads((REPO / tf.CONST_ROSTER["arm"]).read_text(encoding="utf-8"))
    ids = {str(i["sample_id"]) for i in roster["items"]}
    assert len(ids) == 625
    document = cell()
    binding = load_knowledge_store_binding(document, data_root=DATA)
    assert set(binding.composite_snapshot.source_sample_ids) & ids == set()
    assert binding.composite_snapshot.source_split_identity_hash != roster["split_identity_hash"]
    # the same cell on the plain lock (the full pool) is exactly what the runner refuses
    plain_block = {k: v for k, v in block_of(document).items() if k != "construction_roster"}
    plain = cm.compile_module(plain_block, carrier_module_hooks(), repo_root=REPO).apply_to(copy.deepcopy(document))
    plain_binding = load_knowledge_store_binding(plain, data_root=DATA)
    assert len(set(plain_binding.composite_snapshot.source_sample_ids) & ids) == 625
