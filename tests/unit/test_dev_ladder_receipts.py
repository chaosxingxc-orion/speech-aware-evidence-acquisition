"""DEV-ladder identity governance receipts (work item C2-receipts, owner-approved
2026-08-23 knowledge-plane baseline program; authority
``docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md`` sections 2.2 and
5). ``scripts/build_dev_ladder.py`` freezes FINAL60 (reserved/unread) and the
nested DEV-100 (sub) DEV-500 (sub) DEV-1000 devel-side optimization ladder.

Mirrors tests/unit/test_kb_construction_split.py's real-frozen-receipt pattern:
these tests read the ACTUAL committed receipts under
``docs/receipts/probe-samples/`` and the historic probe-60 exclusion source
directly -- no fixture world, no data-root access, no audio touched. Like
test_kb_construction_split.py, every assertion here is a receipt-internal (or
cross-receipt) invariant; the scenario-stratification-covers-all-18-scenarios
claim is checked against each receipt's own committed ``scenario_allocation``
field rather than by re-deriving from the SLURP loader, since this unit-test
module -- like its template -- never touches SPEECHRL_DATA_DIR.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.split_receipt import (
    SplitReceiptError,
    VerifiedSplit,
    load_verified_split,
)
from speech_aware_evidence_acquisition.data.splits import (
    prefixed,
    split_identity_hash as slash_hash,
)
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT
from speech_aware_evidence_acquisition.reproduction.probe_split import (
    load_verified_probe_split,
)
from speech_aware_evidence_acquisition.reproduction.sampling import (
    split_identity_hash as key_hash,
)

RECEIPTS_DIR = Path(REPO_ROOT) / "docs" / "receipts" / "probe-samples"
FINAL60_PATH = RECEIPTS_DIR / "FINAL60.json"
DEV100_PATH = RECEIPTS_DIR / "DEV-100.json"
DEV500_PATH = RECEIPTS_DIR / "DEV-500.json"
DEV1000_PATH = RECEIPTS_DIR / "DEV-1000.json"
PROBE60_PATH = (
    Path(REPO_ROOT) / "configs" / "probes" / "g0-binding" / "pslu-sample-devel-n60.json"
)

ALL_RECEIPT_PATHS = {
    "FINAL60": FINAL60_PATH,
    "DEV-100": DEV100_PATH,
    "DEV-500": DEV500_PATH,
    "DEV-1000": DEV1000_PATH,
}

# Pinned so a regenerated receipt that silently drew different ids fails
# loudly (same discipline as test_kb_construction_split.py's EXPECTED_IDS /
# test_wave1_substrate_configs.py's pinned set) -- here as full identity
# hashes rather than an enumerated id set, since the largest tier carries
# 1000 items.
EXPECTED_COUNTS = {"FINAL60": 60, "DEV-100": 100, "DEV-500": 500, "DEV-1000": 1000}
EXPECTED_SPLIT_ROLE = {
    "FINAL60": "reserved-final-unread",
    "DEV-100": "dev",
    "DEV-500": "dev",
    "DEV-1000": "dev",
}
EXPECTED_SPLIT_IDENTITY_HASH = {
    "FINAL60": "3c082a1a040f7d004e67ca39cf4e078ecd410a132a0d7b3f103c868da65c1b8e",
    "DEV-1000": "9fb44e3384b8ad8e0d8f825b88eb0a3051c218b699975051d8a0481aabc0243b",
    "DEV-500": "c0f1c7531fb8972885abf1d840cc101bbfa38ae04e3929cc46e0f5b9ef35452b",
    "DEV-100": "d676d38b4d27b3a136ba2523b96ae3c71ba2b8b436f7712f4f0c976c3ea833e1",
}
EXPECTED_RUN_IDENTITY_HASH = {
    "FINAL60": "5afd9844bc0c2babcbc98e000281163d03ebdc10241403b7bb074d889dfdc5c3",
    "DEV-1000": "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84",
    "DEV-500": "a00f8c8615ea9508a812f93117b9838f2a1a84ec2b3f06c07edc28b04da6acf4",
    "DEV-100": "e9a7b7febcf4fe3dc228370f7487e1e75dea3d63d447a07fbfe87c1404e2d853",
}
EXPECTED_PROBE60_HASH = "fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5"
EXPECTED_SCENARIOS = {
    "alarm", "audio", "calendar", "cooking", "datetime", "email", "general",
    "iot", "lists", "music", "news", "play", "qa", "recommendation", "social",
    "takeaway", "transport", "weather",
}
GOLD_FIELD_NAMES = {"scenario", "action", "intent", "entities", "sentence", "n_gold_slots"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _ids(payload: dict) -> set[str]:
    return {item["id"] for item in payload["items"]}


@pytest.fixture(scope="module")
def receipts() -> dict[str, dict]:
    return {name: _load(path) for name, path in ALL_RECEIPT_PATHS.items()}


@pytest.fixture(scope="module")
def probe60() -> dict:
    return _load(PROBE60_PATH)


# ---------------------------------------------------------------------------
# Pinned counts and identity hashes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(ALL_RECEIPT_PATHS))
def test_receipt_has_pinned_count_and_role(receipts, name):
    payload = receipts[name]
    assert len(payload["items"]) == EXPECTED_COUNTS[name]
    assert payload["n_items"] == EXPECTED_COUNTS[name]
    assert payload["split_role"] == EXPECTED_SPLIT_ROLE[name]
    assert payload["carrier"] == "slurp"
    assert payload["split"] == "devel"
    assert payload["seed"] == 20260823


@pytest.mark.parametrize("name", sorted(ALL_RECEIPT_PATHS))
def test_receipt_identity_hashes_are_pinned(receipts, name):
    payload = receipts[name]
    assert payload["split_identity_hash"] == EXPECTED_SPLIT_IDENTITY_HASH[name]
    assert payload["run_identity_hash"] == EXPECTED_RUN_IDENTITY_HASH[name]


# ---------------------------------------------------------------------------
# Both hashes recompute from the id/key lists
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(ALL_RECEIPT_PATHS))
def test_receipt_hashes_recompute_from_item_lists(receipts, name):
    """The receipt-key hash (colon convention, over 'key') and the
    run-identity hash (slash convention, over carrier-prefixed 'id') both
    independently recompute -- the same two checks
    reproduction.probe_split.load_verified_probe_split enforces fail-closed
    for the receipt-key hash, plus the E0 ledger convention derivation."""

    payload = receipts[name]
    keys = [item["key"] for item in payload["items"]]
    ids = [item["id"] for item in payload["items"]]
    assert key_hash(keys) == payload["split_identity_hash"]
    assert slash_hash(prefixed("slurp", ids)) == payload["run_identity_hash"]


# ---------------------------------------------------------------------------
# Disjointness and nesting
# ---------------------------------------------------------------------------


def test_final60_is_disjoint_from_every_dev_tier(receipts):
    final60_ids = _ids(receipts["FINAL60"])
    for name in ("DEV-100", "DEV-500", "DEV-1000"):
        assert final60_ids.isdisjoint(_ids(receipts[name])), name


def test_dev_ladder_nests_exactly(receipts):
    """DEV-100 (sub) DEV-500 (sub) DEV-1000 -- exact subset at every step, so
    ladder results across tiers are monotone-comparable (owner ruling
    2026-08-23 section 2.2)."""

    ids_100 = _ids(receipts["DEV-100"])
    ids_500 = _ids(receipts["DEV-500"])
    ids_1000 = _ids(receipts["DEV-1000"])
    assert ids_100 <= ids_500
    assert ids_500 <= ids_1000
    assert len(ids_100) == 100
    assert len(ids_500) == 500
    assert len(ids_1000) == 1000


def test_dev_tier_nesting_metadata_matches_parent_hashes(receipts):
    dev500_nesting = receipts["DEV-500"]["nesting"]
    assert dev500_nesting["parent_tier"] == "DEV-1000"
    assert dev500_nesting["parent_split_identity_hash"] == receipts["DEV-1000"]["split_identity_hash"]
    assert dev500_nesting["is_exact_subset_of_parent"] is True

    dev100_nesting = receipts["DEV-100"]["nesting"]
    assert dev100_nesting["parent_tier"] == "DEV-500"
    assert dev100_nesting["parent_split_identity_hash"] == receipts["DEV-500"]["split_identity_hash"]
    assert dev100_nesting["is_exact_subset_of_parent"] is True

    assert "nesting" not in receipts["DEV-1000"]
    assert "nesting" not in receipts["FINAL60"]


# ---------------------------------------------------------------------------
# probe-60 exclusion
# ---------------------------------------------------------------------------


def test_historic_probe60_receipt_hash_is_pinned(probe60):
    """Sanity on the exclusion SOURCE itself: the historic frozen probe-60
    receipt this mission excludes ids from still carries the exact hash
    every DEV-ladder receipt's own exclusions.historic_probe60 block cites."""

    assert probe60["split_identity_hash"] == EXPECTED_PROBE60_HASH
    assert len(probe60["items"]) == 60


@pytest.mark.parametrize("name", sorted(ALL_RECEIPT_PATHS))
def test_probe60_ids_absent_from_every_receipt(receipts, probe60, name):
    probe60_sample_ids = {item["sample_id"] for item in probe60["items"]}
    probe60_utterance_ids = {item["utterance_id"] for item in probe60["items"]}
    payload = receipts[name]
    receipt_ids = _ids(payload)
    assert receipt_ids.isdisjoint(probe60_sample_ids)
    # utterance-granularity exclusion (module docstring of the generator):
    # no item id may even belong to an excluded UTTERANCE via a different
    # recording -- every id is 'slurp:devel:{utterance_id:06d}:{filename}'.
    receipt_utterance_ids = {sample_id.split(":")[2].lstrip("0") or "0" for sample_id in receipt_ids}
    assert receipt_utterance_ids.isdisjoint(probe60_utterance_ids)


@pytest.mark.parametrize("name", sorted(ALL_RECEIPT_PATHS))
def test_receipt_records_probe60_exclusion_provenance(receipts, name):
    exclusion = receipts[name]["exclusions"]["historic_probe60"]
    assert exclusion["split_identity_hash"] == EXPECTED_PROBE60_HASH
    assert exclusion["excluded_utterance_count"] == 60
    assert exclusion["receipt"] == "configs/probes/g0-binding/pslu-sample-devel-n60.json"


@pytest.mark.parametrize("name", ("DEV-100", "DEV-500", "DEV-1000"))
def test_dev_tiers_also_record_final60_exclusion_provenance(receipts, name):
    exclusion = receipts[name]["exclusions"]["final60"]
    assert exclusion["split_identity_hash"] == receipts["FINAL60"]["split_identity_hash"]
    assert exclusion["excluded_utterance_count"] == 60


# ---------------------------------------------------------------------------
# No gold fields anywhere in a receipt item
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(ALL_RECEIPT_PATHS))
def test_receipt_items_carry_identity_fields_only(receipts, name):
    """Identity-only shape, exactly like the existing SLURP probe-sample
    receipts (e.g. GATE18.json): every item is {'id', 'key'} -- no gold
    scenario/action/intent/entities/sentence field ever appears per item."""

    for item in receipts[name]["items"]:
        assert set(item) == {"id", "key"}
        assert not (set(item) & GOLD_FIELD_NAMES)
        assert item["key"] == f"slurp:{item['id']}"
        assert item["id"].startswith("slurp:devel:")


@pytest.mark.parametrize("name", sorted(ALL_RECEIPT_PATHS))
def test_receipt_top_level_carries_no_gold_field(receipts, name):
    assert not (set(receipts[name]) & GOLD_FIELD_NAMES)


# ---------------------------------------------------------------------------
# Scenario stratification sanity (receipt-internal: scenario_allocation)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(ALL_RECEIPT_PATHS))
def test_scenario_allocation_covers_all_18_scenarios(receipts, name):
    allocation = receipts[name]["scenario_allocation"]
    assert set(allocation) == EXPECTED_SCENARIOS
    assert all(count >= 1 for count in allocation.values())
    assert sum(allocation.values()) == EXPECTED_COUNTS[name]


def test_final60_scenario_allocation_is_as_even_as_the_pool_allows(receipts):
    """FINAL60's own selection_rule (owner ruling 2026-08-23 section 2.2:
    'allocate as evenly as the split allows'): with 60 items over 18
    scenarios and every scenario's eligible pool far larger than 60/18, no
    scenario should be far off the equal share."""

    allocation = receipts["FINAL60"]["scenario_allocation"]
    assert min(allocation.values()) >= 3
    assert max(allocation.values()) <= 4


# ---------------------------------------------------------------------------
# Real frozen receipts verify through the probe-split seam
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ("DEV-100", "DEV-500", "DEV-1000"))
def test_real_frozen_dev_tier_receipt_verifies_and_derives_a_run_hash(name):
    """Pre-flight over the ACTUAL committed receipt (identity only, no data
    root touched): it parses, its colon-key hash re-verifies, and the
    slash-convention run hash an ExecutionPlan would carry is derivable --
    mirrors test_kb_construction_split.py's own real-receipt check."""

    split = load_verified_probe_split(REPO_ROOT, name)
    assert isinstance(split, VerifiedSplit)
    assert split.carrier_lock_key == "slurp"
    assert split.split_role == "dev"
    assert len(split.ids) == EXPECTED_COUNTS[name]
    assert split.prefixed_ids == tuple(prefixed("slurp", split.ids))
    assert split.identity_hash == slash_hash(split.prefixed_ids)
    assert split.identity_hash == EXPECTED_RUN_IDENTITY_HASH[name]


def test_final60_fails_closed_through_the_probe_split_seam():
    """FINAL60's split_role ('reserved-final-unread') sits deliberately
    outside reproduction.probe_split's Stage-2 role allowlist
    ({'discovery', 'dev'}): the same split<->plan<->config seam any run
    would resolve a probe split through REFUSES FINAL60 fail-closed. That
    refusal is FINAL60's 'reserved, unread' contract, not an accident."""

    with pytest.raises(SplitReceiptError, match="not a Stage-2 role"):
        load_verified_probe_split(REPO_ROOT, "FINAL60")


@pytest.mark.parametrize("name", ("DEV-100", "DEV-500", "DEV-1000"))
def test_dev_tier_dispatches_through_load_verified_split(name, tmp_path):
    """Any split name outside the three contract splits dispatches purely
    off the receipt file, so a dummy lock/root (never touched on this path)
    is enough -- mirrors test_kb_construction_split.py's own dataset-fragment
    resolution check."""

    split = load_verified_split(REPO_ROOT, name, lock={}, root=tmp_path)
    assert split.carrier_lock_key == "slurp"
    assert len(split.ids) == EXPECTED_COUNTS[name]
    assert split.identity_hash == slash_hash(split.prefixed_ids)


def test_final60_fails_closed_through_load_verified_split_too():
    """The generic split<->plan<->config dispatcher (load_verified_split)
    reaches the same fail-closed refusal for FINAL60 as the direct probe-split
    seam does -- there is no alternate path that resolves it."""

    with pytest.raises(SplitReceiptError, match="not a Stage-2 role"):
        load_verified_split(REPO_ROOT, "FINAL60", lock={}, root=REPO_ROOT)
