"""Owner decision 107: the DEVEL-REMAINDER roster and its generalised runtime view.

Zero model / encoder / network / GPU contact: every test reads a committed
receipt, a committed config fragment, or a pure helper of the two generators
imported by path. No media file is decoded and no utterance text, gold label,
intent or slot annotation is read.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ROSTER_SCRIPT = REPO / "scripts" / "build_slurp_devel_remainder_roster.py"
VIEW_SCRIPT = REPO / "scripts" / "build_slurp_runtime_view.py"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-devel-remainder-v1.json"
VIEW_RELPATH = "configs/dataset/slurp-speech-native-devel-remainder.json"
CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-devel-remainder-packets"
)
ROSTER_CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-devel-remainder-roster"
)


def _module(path: Path, name: str):
    if str(REPO / "src") not in sys.path:
        sys.path.insert(0, str(REPO / "src"))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


roster_builder = _module(ROSTER_SCRIPT, "build_slurp_devel_remainder_roster_test")
view_builder = _module(VIEW_SCRIPT, "build_slurp_runtime_view_test")


def _json(relpath: str) -> dict:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


# --------------------------------------------------------------- generators


def test_roster_builder_constants_are_the_registered_ones() -> None:
    assert roster_builder.ROSTER_ID == "SLURP-DEVEL-REMAINDER-V1"
    assert roster_builder.SEED == 20260923
    assert roster_builder.ROSTER_RELPATH == ROSTER_RELPATH
    assert "owner decision 107" in roster_builder.AUTHORITY
    assert roster_builder.GENERATOR == "scripts/build_slurp_devel_remainder_roster.py"


def test_roster_builder_checks_every_dev2000_added_construction_roster() -> None:
    """The DEV-2000-ADDED receipt's own construction_rosters_checked list is a
    SUBSET of what this roster proves itself disjoint from -- the same logic,
    plus the two Stage-3 construction rosters frozen after it."""

    added = _json("docs/receipts/rosters/slurp-dev-2000-added-v1.json")
    inherited = [str(entry["relpath"]) for entry in added["construction_rosters_checked"]]
    assert inherited, "the DEV-2000-ADDED receipt lost its construction roster list"
    assert set(inherited) <= set(roster_builder.CONSTRUCTION_ROSTERS)
    assert "docs/receipts/rosters/slurp-stage3-construction-r01.json" in (
        roster_builder.CONSTRUCTION_ROSTERS
    )
    assert "docs/receipts/rosters/slurp-stage3-construction-r01c.json" in (
        roster_builder.CONSTRUCTION_ROSTERS
    )
    for relpath in roster_builder.CONSTRUCTION_ROSTERS:
        assert (REPO / relpath).is_file(), relpath


def test_utterance_and_slurp_id_helpers() -> None:
    sample_id = "slurp:devel:000017:audio-1501773854-headset"
    assert roster_builder.utterance_of(sample_id) == "slurp:devel:000017"
    assert roster_builder.slurp_id_of(sample_id) == "000017"
    assert roster_builder.is_headset("slurp/devel/audio-1-headset.flac") is True
    assert roster_builder.is_headset("slurp/devel/audio-1.flac") is False


# ------------------------------------------------------------ the receipt


def test_committed_roster_is_the_whole_devel_remainder() -> None:
    receipt = _json(ROSTER_RELPATH)
    assert receipt["schema"] == "saea-roster-receipt-v1"
    assert receipt["roster_id"] == "SLURP-DEVEL-REMAINDER-V1"
    assert receipt["carrier_lock_key"] == "slurp"
    assert receipt["split_role"] == "dev"
    assert receipt["roster_role"] == "evaluation"
    assert receipt["seed"] == 20260923
    assert receipt["stratum_withheld_per_item"] is True
    assert receipt["target_gold_opened_before_receipt"] is False
    assert len(receipt["items"]) == 6690
    assert receipt["excluded_count"] == 2000
    assert all(str(item["sample_id"]).startswith("slurp:devel:") for item in receipt["items"])
    assert "stratum" not in receipt["items"][0]


def test_committed_roster_hash_verifies() -> None:
    from speech_aware_evidence_acquisition.core.roster import verify_roster

    assert verify_roster(_json(ROSTER_RELPATH)) == _json(ROSTER_RELPATH)[
        "split_identity_hash"
    ]


def test_the_three_parts_are_the_complete_devel_split() -> None:
    receipt = _json(ROSTER_RELPATH)
    completeness = receipt["completeness"]
    assert completeness["union_equals_the_complete_devel_split"] is True
    assert completeness["parts_are_pairwise_disjoint"] is True
    assert completeness["three_parts_sum"] == completeness["devel_recordings"] == 8690
    assert completeness["remainder_recordings"] == 6690

    remainder = {str(item["sample_id"]) for item in receipt["items"]}
    dev1000 = {str(item["id"]) for item in _json("docs/receipts/probe-samples/DEV-1000.json")["items"]}
    added = {
        str(item["sample_id"])
        for item in _json("docs/receipts/rosters/slurp-dev-2000-added-v1.json")["items"]
    }
    assert not remainder & dev1000
    assert not remainder & added
    assert len(remainder | dev1000 | added) == 8690


def test_dev_ladder_nesting_is_proven_in_the_receipt() -> None:
    nesting = _json(ROSTER_RELPATH)["dev_ladder_nesting"]
    assert nesting["dev100_subset_of_dev500"] is True
    assert nesting["dev500_subset_of_dev1000"] is True
    assert nesting["dev100_subset_of_dev1000"] is True
    assert nesting["dev500b_subset_of_dev2000_added"] is True
    assert nesting["dev2000_equals_dev1000_union_added"] is True


def test_disjointness_proof_is_all_zero_and_construction_rosters_are_listed() -> None:
    receipt = _json(ROSTER_RELPATH)
    proof = receipt["disjointness_proof"]
    for key, value in proof.items():
        if key.startswith("shared_with"):
            assert value == 0, key
    assert proof["non_devel_ids_in_remainder"] == 0
    checked = {str(entry["relpath"]): entry for entry in receipt["construction_rosters_checked"]}
    assert set(checked) == set(roster_builder.CONSTRUCTION_ROSTERS)
    for entry in checked.values():
        assert entry["shared_with_remainder"] == 0
        assert entry["items"] > 0
        assert len(str(entry["receipt_file_sha256"])) == 64


def test_utterance_overlap_is_reported_not_hidden() -> None:
    overlap = _json(ROSTER_RELPATH)["utterance_overlap"]
    assert overlap["remainder_utterances"] == 1839
    assert overlap["remainder_utterances_also_in_either_sealed_half"] == 1719
    assert overlap["remainder_utterances_never_read_before"] == 120
    assert overlap["remainder_utterances_also_in_dev1000"] == 887
    assert overlap["remainder_utterances_also_in_dev2000_added"] == 832


def test_reserved_sets_inside_the_remainder_are_counted() -> None:
    reserved = _json(ROSTER_RELPATH)["reserved_sets_inside_the_remainder"]
    assert reserved["final60"]["split_role"] == "reserved-final-unread"
    assert reserved["final60"]["recordings_inside_the_remainder"] == 60
    assert reserved["historic_probe60"]["recordings_inside_the_remainder"] == 60
    assert reserved["final60_and_probe60_share_a_recording"] == 0


def test_the_three_deviations_are_recorded_with_an_owner_action() -> None:
    deviations = _json(ROSTER_RELPATH)["deviations"]
    assert [entry["id"] for entry in deviations] == ["REM-D1", "REM-D2", "REM-D3"]
    for entry in deviations:
        assert entry["statement"] and entry["why_unavoidable"] and entry["owner_action"]


def test_roster_disjointness_check_document_is_committed() -> None:
    proof = _json(f"{ROSTER_CHECK_DIR}/disjointness.json")
    assert proof["schema"] == "saea-devel-remainder-roster-disjointness-v1"
    assert proof["roster"]["count"] == 6690
    assert proof["roster"]["split_identity_hash"] == _json(ROSTER_RELPATH)["split_identity_hash"]
    assert proof["offline_guard"]["outbound_connection_attempts"] == 0


# -------------------------------------------------- the runtime-view builder


def test_split_of_refuses_a_mixture_and_resolves_a_single_split() -> None:
    assert view_builder.split_of(["slurp:devel:000001:audio-a"]) == "devel"
    assert view_builder.split_of(["slurp:train:000001:audio-a"]) == "train"
    with pytest.raises(SystemExit):
        view_builder.split_of(["slurp:devel:000001:audio-a", "slurp:train:000002:audio-b"])
    with pytest.raises(SystemExit):
        view_builder.split_of(["slurp:nosuchsplit:000001:audio-a"])


def test_default_split_name_drops_the_carrier_prefix_and_version() -> None:
    assert view_builder.default_split_name("SLURP-DEVEL-REMAINDER-V1") == "DEVEL-REMAINDER"
    assert view_builder.default_split_name("SLURP-DEV-2000-ADDED-V1") == "DEV-2000-ADDED"
    assert (
        view_builder.default_split_name("SLURP-STAGE3-CONSTRUCTION-R01")
        == "STAGE3-CONSTRUCTION-R01"
    )


@pytest.mark.parametrize("workers", [0, -1, 9, 20])
def test_runtime_view_builder_refuses_more_than_eight_cpu_workers(workers: int) -> None:
    with pytest.raises(SystemExit):
        view_builder.main(
            [
                "--roster-receipt",
                ROSTER_RELPATH,
                "--output",
                VIEW_RELPATH,
                "--checks-dir",
                CHECK_DIR,
                "--workers",
                str(workers),
            ]
        )


def test_runtime_view_builder_caps_workers_at_eight() -> None:
    assert view_builder.MAX_WORKERS == 8


# ------------------------------------------------------- the runtime view


def test_committed_runtime_view_matches_the_roster() -> None:
    view = _json(VIEW_RELPATH)
    receipt = _json(ROSTER_RELPATH)
    assert view["schema"] == "saea-speech-native-runtime-view-v1"
    assert view["carrier_lock_key"] == "slurp"
    assert view["split_name"] == "DEVEL-REMAINDER"
    assert view["split_role"] == "dev"
    assert view["count"] == 6690 == len(view["items"])
    assert view["split_identity_hash"] == receipt["split_identity_hash"]
    assert view["seed"] == receipt["seed"]
    assert view["d1_media_supplement"] is None
    assert view["d1_media_supplement_sha256"] is None
    assert view["d1_manifest_sha256"] is None
    assert {str(item["sample_id"]) for item in view["items"]} == {
        str(item["sample_id"]) for item in receipt["items"]
    }


def test_runtime_view_rows_are_media_identity_only() -> None:
    view = _json(VIEW_RELPATH)
    allowed = {
        "sample_id",
        "media_relpath",
        "audio_sha256",
        "audio_seconds",
        "sample_rate_hz",
        "packet_id",
    }
    for item in view["items"][:50]:
        assert set(item) == allowed
        assert str(item["packet_id"]) == str(item["sample_id"]).replace(":", "/")
        assert len(str(item["audio_sha256"])) == 64


def test_runtime_view_hash_is_the_canonical_hash_of_its_own_unsigned_body() -> None:
    view = _json(VIEW_RELPATH)
    unsigned = {key: value for key, value in view.items() if key != "runtime_view_sha256"}
    assert view_builder.canonical_sha256(unsigned) == view["runtime_view_sha256"]


def test_media_inventory_and_packet_plan_are_committed_and_say_no_supplement_is_needed() -> None:
    inventory = _json(f"{CHECK_DIR}/media-inventory.json")
    plan = _json(f"{CHECK_DIR}/packet-preparation-plan.json")
    assert inventory["schema"] == "saea-slurp-speech-native-media-inventory-v1"
    assert inventory["counts"]["recordings"] == 6690
    assert inventory["counts"]["audio_seconds_declared_ceiling"] == 18979
    assert inventory["d1_closure"]["supplement_required"] is False
    assert inventory["d1_closure"]["closure_ids_for_carrier"] == 8690
    assert inventory["cpu_pipeline"]["workers"] == 8
    assert inventory["legacy_feature_cache"]["warm_rows"] == 60
    assert inventory["legacy_feature_cache"]["cold_rows"] == 6630
    assert inventory["promoted_packet_coverage"]["covered_rows"] == 0
    assert inventory["offline_guard"]["outbound_connection_attempts"] == 0
    assert plan["schema"] == "saea-slurp-speech-native-packet-plan-v1"
    assert plan["rows"] == 6690
    assert plan["rows_needing_encode"] == 6630
    assert plan["rows_promotable_with_zero_contacts"] == 60
    assert plan["binding"]["runtime_view_sha256"] == _json(VIEW_RELPATH)["runtime_view_sha256"]
