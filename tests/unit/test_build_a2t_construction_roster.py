"""``scripts/build_a2t_construction_roster.py`` (enabler E2.3): the landed
construction and reserved-evaluation rosters, checked as COMMITTED BYTES.

The generator itself needs the governed Audio2Tool manifests under
``SPEECHRL_DATA_DIR`` and is therefore not re-run here; what is checked is
the property the owner rule actually cares about -- that the two receipts
this repository committed are internally consistent, carry the roles the
2026-09-05 decision assigns them, and are block-disjoint from every
committed evaluation identity. Zero contacts: only committed JSON is read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.roster import (
    hash_matches_legacy_receipt,
    read_roster,
)
from speech_aware_evidence_acquisition.data.audio2tool import audio2tool_receipts
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.data.variant_ids import published_sample_key
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (
    EVALUATION_ROSTER_ROLE,
    exposed_identity_report,
    exposed_sample_ids,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

CONSTRUCTION = REPO_ROOT / "docs/receipts/rosters/a2t-construction-800-v1.json"
FRESH = REPO_ROOT / "docs/receipts/rosters/a2t-fresh-800-v1.json"
PROBE_VIEW = REPO_ROOT / "docs/receipts/probe-samples/a2t-construction-800-v1.json"
#: The committed KB v3 exposure-union / block-partition receipt
#: (exposure row SAEA-SN-MF-A2T-KB-EXPOSURE-UNION-V3).
KB_V3_PARTITION = REPO_ROOT / "docs/receipts/knowledge/a2t-partition-proposal.json"
TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)


def _blocks(receipt: dict) -> set[int]:
    return {int(item["query_idx"]) for item in receipt["items"]}


@pytest.mark.parametrize("path", [CONSTRUCTION, FRESH, PROBE_VIEW])
def test_the_receipt_is_committed(path: Path) -> None:
    assert path.is_file(), f"{path} is missing"


def test_both_rosters_are_800_rows_100_per_tier_and_verify() -> None:
    for path, role in ((CONSTRUCTION, "construction"), (FRESH, "evaluation")):
        receipt = read_roster(path)  # recomputes split_identity_hash, fail-closed
        assert receipt["carrier_lock_key"] == "audio2tool"
        assert receipt["roster_role"] == role
        assert receipt["split_role"] == "discovery"
        assert receipt["seed"] == 20260803
        assert len(receipt["items"]) == 800
        assert receipt["strata_counts"] == {tier: 100 for tier in TIERS}
        ids = [str(item["sample_id"]) for item in receipt["items"]]
        assert receipt["split_identity_hash"] == split_identity_hash(
            prefixed("audio2tool", ids)
        )


def test_the_two_rosters_share_no_sample_and_no_block() -> None:
    construction = read_roster(CONSTRUCTION)
    fresh = read_roster(FRESH)
    assert not _blocks(construction) & _blocks(fresh)
    assert not {str(item["sample_id"]) for item in construction["items"]} & {
        str(item["sample_id"]) for item in fresh["items"]
    }


def test_neither_roster_touches_a_committed_evaluation_identity() -> None:
    """The zero-overlap proof, recomputed here from the exposure sources
    rather than trusted from the receipts' own recorded numbers -- except
    that A2T-FRESH-800 is now itself source (c) of that union, so it is
    subtracted before the comparison."""

    fresh = read_roster(FRESH)
    fresh_ids = {str(item["sample_id"]) for item in fresh["items"]}
    prior_exposure = exposed_sample_ids(REPO_ROOT) - fresh_ids

    construction_ids = {
        str(item["sample_id"]) for item in read_roster(CONSTRUCTION)["items"]
    }
    assert not construction_ids & prior_exposure
    assert not fresh_ids & prior_exposure


def test_the_construction_roster_is_excluded_from_the_exposure_union() -> None:
    union = exposed_sample_ids(REPO_ROOT)
    construction_ids = {
        str(item["sample_id"]) for item in read_roster(CONSTRUCTION)["items"]
    }
    assert not construction_ids & union
    report = exposed_identity_report(REPO_ROOT)
    roster_rows = [row for row in report["sources"] if row["kind"] == "roster-receipt"]
    roster_sources = {str(row["name"]) for row in roster_rows}

    # COORDINATOR DECISION 2026-09-07. This assertion used to name
    # ``a2t-fresh-800-v1`` and nothing else, and went red when two more
    # evaluation-role Audio2Tool rosters landed: ``a2t-evo-curve-400-v1`` (a
    # SUBSET of already-exposed evaluation ids, drawn for the EVO curve) and
    # ``a2t-calibration-400-ts2-v1`` (the ``@ts2`` MEDIA VARIANT of the frozen
    # 400). Both are evaluation identities of an already-exposed evaluation
    # population, so both belong in the union, and admitting them by CLASS --
    # rather than by re-typing a name list that the next variant roster breaks
    # again -- is what this test now checks. The property that actually
    # matters is that such a roster can only WIDEN the hold-out; the two
    # assertions below say so, and the third proves the construction side did
    # not shrink.
    assert "a2t-fresh-800-v1" in roster_sources
    assert all(str(row["roster_role"]) == EVALUATION_ROSTER_ROLE for row in roster_rows)
    assert all(
        str(row["relpath"]).startswith("docs/receipts/rosters/") for row in roster_rows
    )

    v3 = json.loads(KB_V3_PARTITION.read_text(encoding="utf-8"))
    assert v3["exposure_row"] == "SAEA-SN-MF-A2T-KB-EXPOSURE-UNION-V3"
    v3_union = v3["exposure_union"]
    v3_roster_names = {
        str(row["name"]) for row in v3_union["sources"] if row["kind"] == "roster-receipt"
    }
    assert v3_roster_names == {"a2t-fresh-800-v1"}
    # The union only ever grew.
    assert len(union) >= int(v3_union["union_sample_ids"])

    reserved_blocks = {int(block) for block in v3["reserved_exposed_blocks"]}
    for name in sorted(roster_sources - v3_roster_names):
        receipt = read_roster(REPO_ROOT / "docs/receipts/rosters" / f"{name}.json")
        assert receipt["roster_role"] == "evaluation"
        ids = {str(item["sample_id"]) for item in receipt["items"]}
        # Every id it names is an evaluation identity this repository had
        # ALREADY exposed, under its own published key.
        assert {published_sample_key(sample_id) for sample_id in ids} <= union
        # And every block it touches was ALREADY reserved. A variant roster
        # names no pool unit at all (its ids carry the ``@`` suffix, so they
        # match no ``query_idx``), and the curve roster was drawn from ids the
        # union already held -- so neither can take a block away from the
        # construction pool.
        blocks = {int(item["query_idx"]) for item in receipt["items"] if "query_idx" in item}
        assert blocks <= reserved_blocks, name

    # Therefore the construction side of the partition is exactly what the
    # committed KB v3 receipt recorded, and has not shrunk.
    assert (
        int(v3["report"]["blocks_total"]) - len(reserved_blocks)
        == int(v3["report"]["blocks_construction"])
        == 1689
    )


def test_the_reserved_roster_has_no_probe_sample_view() -> None:
    """A2T-FRESH-800 must stay unhydratable until rung 3: the Audio2Tool
    loader resolves items only from probe-sample receipts, so the absence of
    one is what actually keeps the roster closed."""

    assert not (
        REPO_ROOT / "docs/receipts/probe-samples/a2t-fresh-800-v1.json"
    ).exists()
    loaded = audio2tool_receipts(REPO_ROOT)
    assert "a2t-construction-800-v1" in loaded
    assert not any(name.startswith("a2t-fresh") for name in loaded)
    fresh_ids = {str(item["sample_id"]) for item in read_roster(FRESH)["items"]}
    loadable = {
        f"{item['tier']}:{int(item['id']):06d}"
        for payload in loaded.values()
        for item in payload["items"]
    }
    assert not fresh_ids & loadable


def test_the_construction_probe_view_loads_and_names_the_same_samples() -> None:
    assert hash_matches_legacy_receipt(PROBE_VIEW) is True
    view = json.loads(PROBE_VIEW.read_text(encoding="utf-8"))
    receipt = read_roster(CONSTRUCTION)
    assert view["roster_role"] == "construction"
    assert view["split_role"] == "discovery"
    assert view["n_items"] == 800
    assert view["roster_split_identity_hash"] == receipt["split_identity_hash"]
    assert {str(item["key"]) for item in view["items"]} == {
        f"audio2tool:{item['sample_id']}" for item in receipt["items"]
    }


def test_the_receipts_record_a_zero_overlap_proof_and_zero_contacts() -> None:
    for path in (CONSTRUCTION, FRESH):
        receipt = read_roster(path)
        proof = receipt["block_disjointness"]
        assert proof["overlap_with_exposure_union_blocks"] == 0
        assert proof["overlap_with_exposure_union_sample_ids"] == 0
        assert proof["overlap_between_the_two_rosters"] == 0
        assert receipt["offline_guard"]["outbound_connection_attempts"] == 0
        assert receipt["target_gold_opened_before_receipt"] is False
        assert receipt["exposure_row"] == "SAEA-SN-MF-A2T-CONSTRUCTION-ROSTER-V1"
    assert read_roster(FRESH)["status"] == "RESERVED_AND_UNOPENED"
