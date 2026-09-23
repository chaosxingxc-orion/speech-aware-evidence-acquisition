"""Owner decision 107 + provisional decision 109: the carved DEVEL-REMAINDER
roster (V2) and its generalised runtime view.

V1 froze the whole remainder, reservations and all. The coordinator ruling of
2026-09-23 carved the 60 ``reserved-final-unread`` FINAL60 recordings and the 60
already-contacted historic probe-60 recordings out of it and re-froze the roster
as ``SLURP-DEVEL-REMAINDER-V2`` (6,570 rows). V1 stays committed as the
superseded parent and is never rewritten -- several committed documents pin its
receipt file hash -- so this module checks V2 as the live roster and keeps a
short section proving V1 is still there, intact, and correctly superseded.

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
ROSTER_RELPATH = "docs/receipts/rosters/slurp-devel-remainder-v2.json"
VIEW_RELPATH = "configs/dataset/slurp-speech-native-devel-remainder-v2.json"
CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-23-slurp-devel-remainder-v2-packets"
)
ROSTER_CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-23-slurp-devel-remainder-v2-roster"
)
PARENT_ROSTER_RELPATH = "docs/receipts/rosters/slurp-devel-remainder-v1.json"
PARENT_VIEW_RELPATH = "configs/dataset/slurp-speech-native-devel-remainder.json"
PARENT_CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-devel-remainder-packets"
)
PARENT_ROSTER_CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-devel-remainder-roster"
)
FINAL60_RELPATH = "docs/receipts/probe-samples/FINAL60.json"
PROBE60_RELPATH = "configs/probes/g0-binding/pslu-sample-devel-n60.json"
ROWS = 6570
PARENT_ROWS = 6690
CARVED_OUT = 120


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
    assert roster_builder.DEFAULT_VERSION == 1
    assert roster_builder.ROSTER_RELPATH == PARENT_ROSTER_RELPATH
    assert "owner decision 107" in roster_builder.AUTHORITY
    assert "provisional decision 109" in roster_builder.CARVE_OUT_AUTHORITY
    assert roster_builder.GENERATOR == "scripts/build_slurp_devel_remainder_roster.py"


def test_version_helpers_derive_every_v2_path_from_the_version_alone() -> None:
    """``--version 2`` must reach the committed V2 artifacts without a second literal."""

    assert roster_builder.roster_id(2) == "SLURP-DEVEL-REMAINDER-V2"
    assert roster_builder.roster_relpath(2) == ROSTER_RELPATH
    assert roster_builder.check_dir(2) == ROSTER_CHECK_DIR
    # V1 keeps the check directory it was committed under.
    assert roster_builder.roster_id(1) == "SLURP-DEVEL-REMAINDER-V1"
    assert roster_builder.roster_relpath(1) == PARENT_ROSTER_RELPATH
    assert roster_builder.check_dir(1) == PARENT_ROSTER_CHECK_DIR
    assert roster_builder.check_dir(3).endswith("-v3-roster")


def test_carve_out_labels_are_stable_for_the_two_reservations() -> None:
    assert roster_builder.carve_out_label(FINAL60_RELPATH) == "final60"
    assert roster_builder.carve_out_label(PROBE60_RELPATH) == "historic_probe60"
    # Anything else gets a deterministic label from its stem, never a crash.
    assert roster_builder.carve_out_label("docs/receipts/rosters/some-Set.v9.json") == "some_set_v9"


@pytest.mark.parametrize("argv", [["--version", "0"], ["--version", "-2"]])
def test_roster_builder_refuses_a_non_positive_version(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        roster_builder.main(argv)


def test_roster_builder_refuses_a_missing_exclude_receipt() -> None:
    with pytest.raises(SystemExit):
        roster_builder.main(
            ["--version", "2", "--exclude-receipt", "docs/receipts/rosters/not-a-file.json"]
        )


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


def test_committed_roster_is_the_carved_devel_remainder() -> None:
    receipt = _json(ROSTER_RELPATH)
    assert receipt["schema"] == "saea-roster-receipt-v1"
    assert receipt["roster_id"] == "SLURP-DEVEL-REMAINDER-V2"
    assert receipt["roster_version"] == 2
    assert receipt["carrier_lock_key"] == "slurp"
    assert receipt["split_role"] == "dev"
    assert receipt["roster_role"] == "evaluation"
    assert receipt["seed"] == 20260923
    assert receipt["stratum_withheld_per_item"] is True
    assert receipt["target_gold_opened_before_receipt"] is False
    assert len(receipt["items"]) == ROWS
    assert receipt["excluded_count"] == 2000 + CARVED_OUT
    assert all(str(item["sample_id"]).startswith("slurp:devel:") for item in receipt["items"])
    assert "stratum" not in receipt["items"][0]


def test_the_carve_out_removes_both_reservations_id_by_id() -> None:
    receipt = _json(ROSTER_RELPATH)
    carved = receipt["carved_out_reserved_sets"]
    final60 = {str(item["id"]) for item in _json(FINAL60_RELPATH)["items"]}
    probe60 = {str(item["sample_id"]) for item in _json(PROBE60_RELPATH)["items"]}
    assert len(final60) == len(probe60) == 60
    assert not final60 & probe60, "the two reservations must be disjoint"
    assert carved["union_recordings"] == len(final60 | probe60) == CARVED_OUT
    assert carved["pairwise_shared_recordings"]["final60|historic_probe60"] == 0
    assert carved["carved_out_recordings_still_in_the_remainder"] == 0
    rows = {str(item["sample_id"]) for item in receipt["items"]}
    assert not rows & final60
    assert not rows & probe60
    assert {str(entry["relpath"]) for entry in carved["receipts"]} == {
        FINAL60_RELPATH,
        PROBE60_RELPATH,
    }
    assert "provisional decision 109" in carved["authority"]


def test_the_carve_out_union_hash_is_the_sorted_excluded_id_list() -> None:
    import hashlib

    carved = _json(ROSTER_RELPATH)["carved_out_reserved_sets"]
    excluded = sorted(
        {str(item["id"]) for item in _json(FINAL60_RELPATH)["items"]}
        | {str(item["sample_id"]) for item in _json(PROBE60_RELPATH)["items"]}
    )
    digest = hashlib.sha256("\n".join(excluded).encode("utf-8")).hexdigest()
    assert carved["union_sample_id_list_sha256"] == digest


def test_the_utterance_level_residue_is_reported_not_hidden() -> None:
    """A recording-level carve-out cannot remove sibling recordings; say so."""

    receipt = _json(ROSTER_RELPATH)
    carved = receipt["carved_out_reserved_sets"]
    assert carved["union_utterances"] == CARVED_OUT
    assert carved["carved_out_utterances_still_represented_in_the_remainder"] == 108
    assert carved["remainder_recordings_of_carved_out_utterances"] == 383
    rows = {str(item["sample_id"]) for item in receipt["items"]}
    reserved_utterances = {
        sid.rsplit(":", 1)[0]
        for sid in (
            {str(item["id"]) for item in _json(FINAL60_RELPATH)["items"]}
            | {str(item["sample_id"]) for item in _json(PROBE60_RELPATH)["items"]}
        )
    }
    measured = sum(1 for sid in rows if sid.rsplit(":", 1)[0] in reserved_utterances)
    assert measured == carved["remainder_recordings_of_carved_out_utterances"]


def test_v2_supersedes_v1_without_rewriting_it() -> None:
    import hashlib

    parent_bytes = (REPO / PARENT_ROSTER_RELPATH).read_bytes()
    supersedes = _json(ROSTER_RELPATH)["supersedes"]
    assert supersedes["roster_id"] == "SLURP-DEVEL-REMAINDER-V1"
    assert supersedes["relpath"] == PARENT_ROSTER_RELPATH
    assert supersedes["recordings"] == PARENT_ROWS
    assert supersedes["receipt_file_sha256"] == hashlib.sha256(parent_bytes).hexdigest()
    parent = _json(PARENT_ROSTER_RELPATH)
    # The parent is untouched: no superseded_by key was grafted onto it, because
    # committed documents pin its file hash.
    assert "superseded_by" not in parent
    assert "carved_out_reserved_sets" not in parent
    assert len(parent["items"]) == PARENT_ROWS
    assert parent["reserved_sets_inside_the_remainder"]["final60"][
        "recordings_inside_the_remainder"
    ] == 60
    # and its own artifacts stay committed beside V2's
    assert (REPO / PARENT_VIEW_RELPATH).is_file()
    assert (REPO / PARENT_CHECK_DIR / "media-inventory.json").is_file()
    assert (REPO / PARENT_ROSTER_CHECK_DIR / "disjointness.json").is_file()


def test_committed_roster_hash_verifies() -> None:
    from speech_aware_evidence_acquisition.core.roster import verify_roster

    assert verify_roster(_json(ROSTER_RELPATH)) == _json(ROSTER_RELPATH)[
        "split_identity_hash"
    ]


def test_the_four_parts_are_the_complete_devel_split() -> None:
    receipt = _json(ROSTER_RELPATH)
    completeness = receipt["completeness"]
    assert completeness["union_equals_the_complete_devel_split"] is True
    assert completeness["parts_are_pairwise_disjoint"] is True
    assert completeness["four_parts_sum"] == completeness["devel_recordings"] == 8690
    assert completeness["remainder_recordings"] == ROWS
    assert completeness["carved_out_recordings"] == CARVED_OUT

    remainder = {str(item["sample_id"]) for item in receipt["items"]}
    dev1000 = {str(item["id"]) for item in _json("docs/receipts/probe-samples/DEV-1000.json")["items"]}
    added = {
        str(item["sample_id"])
        for item in _json("docs/receipts/rosters/slurp-dev-2000-added-v1.json")["items"]
    }
    carved = {str(item["id"]) for item in _json(FINAL60_RELPATH)["items"]} | {
        str(item["sample_id"]) for item in _json(PROBE60_RELPATH)["items"]
    }
    assert not remainder & dev1000
    assert not remainder & added
    assert not remainder & carved
    assert len(remainder | dev1000 | added | carved) == 8690


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
    # The carve-out is proven by id in the same block, not merely promised.
    assert proof["shared_with_carved_out_final60_recordings"] == 0
    assert proof["shared_with_carved_out_historic_probe60_recordings"] == 0
    assert proof["shared_with_any_carved_out_recording"] == 0
    assert proof["non_devel_ids_in_remainder"] == 0
    checked = {str(entry["relpath"]): entry for entry in receipt["construction_rosters_checked"]}
    assert set(checked) == set(roster_builder.CONSTRUCTION_ROSTERS)
    for entry in checked.values():
        assert entry["shared_with_remainder"] == 0
        assert entry["items"] > 0
        assert len(str(entry["receipt_file_sha256"])) == 64


def test_utterance_overlap_is_reported_not_hidden() -> None:
    overlap = _json(ROSTER_RELPATH)["utterance_overlap"]
    assert overlap["remainder_utterances"] == 1827
    assert overlap["remainder_utterances_also_in_either_sealed_half"] == 1719
    # 12 of V1's 120 never-read utterances had ONLY their reserved recording and
    # leave with it; the other 108 keep sibling recordings (see REM-D1).
    assert overlap["remainder_utterances_never_read_before"] == 108
    assert overlap["remainder_utterances_also_in_dev1000"] == 887
    assert overlap["remainder_utterances_also_in_dev2000_added"] == 832


def test_reserved_sets_are_no_longer_inside_the_remainder() -> None:
    reserved = _json(ROSTER_RELPATH)["reserved_sets_inside_the_remainder"]
    assert reserved["final60"]["split_role"] == "reserved-final-unread"
    assert reserved["final60"]["recordings_inside_the_remainder"] == 0
    assert reserved["historic_probe60"]["recordings_inside_the_remainder"] == 0
    assert reserved["final60_and_probe60_share_a_recording"] == 0
    assert reserved["final60_and_probe60_share_an_utterance"] == 0
    # what a recording-level carve-out could not take with it
    assert reserved["final60"]["remainder_recordings_of_those_utterances"] == 194
    assert reserved["historic_probe60"]["remainder_recordings_of_those_utterances"] == 189
    assert "CARVES THEM OUT" in reserved["reading"]


def test_the_three_deviations_are_recorded_with_an_owner_action() -> None:
    deviations = _json(ROSTER_RELPATH)["deviations"]
    assert [entry["id"] for entry in deviations] == ["REM-D1", "REM-D2", "REM-D3"]
    for entry in deviations:
        assert entry["statement"] and entry["why_unavoidable"] and entry["owner_action"]
    # REM-D1 now states the carve-out AND the residue it could not remove.
    assert "CARVED OUT" in deviations[0]["statement"]
    assert "383" in deviations[0]["statement"]


def test_roster_disjointness_check_document_is_committed() -> None:
    proof = _json(f"{ROSTER_CHECK_DIR}/disjointness.json")
    assert proof["schema"] == "saea-devel-remainder-roster-disjointness-v1"
    assert proof["roster"]["roster_id"] == "SLURP-DEVEL-REMAINDER-V2"
    assert proof["roster"]["count"] == ROWS
    assert proof["roster"]["split_identity_hash"] == _json(ROSTER_RELPATH)["split_identity_hash"]
    assert proof["carved_out_reserved_sets"]["union_recordings"] == CARVED_OUT
    assert proof["offline_guard"]["outbound_connection_attempts"] == 0


# -------------------------------------------------- the runtime-view builder


def test_split_of_refuses_a_mixture_and_resolves_a_single_split() -> None:
    assert view_builder.split_of(["slurp:devel:000001:audio-a"]) == "devel"
    assert view_builder.split_of(["slurp:train:000001:audio-a"]) == "train"
    with pytest.raises(SystemExit):
        view_builder.split_of(["slurp:devel:000001:audio-a", "slurp:train:000002:audio-b"])
    with pytest.raises(SystemExit):
        view_builder.split_of(["slurp:nosuchsplit:000001:audio-a"])


def test_default_split_name_drops_the_carrier_prefix_and_any_version() -> None:
    """Which POPULATION is the split name; which FREEZE of it is the roster id."""

    assert view_builder.default_split_name("SLURP-DEVEL-REMAINDER-V1") == "DEVEL-REMAINDER"
    assert view_builder.default_split_name("SLURP-DEVEL-REMAINDER-V2") == "DEVEL-REMAINDER"
    assert view_builder.default_split_name("SLURP-DEVEL-REMAINDER-V10") == "DEVEL-REMAINDER"
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
    assert view["count"] == ROWS == len(view["items"])
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
    assert inventory["roster"]["roster_id"] == "SLURP-DEVEL-REMAINDER-V2"
    assert inventory["counts"]["recordings"] == ROWS
    assert inventory["counts"]["distinct_utterances"] == 1827
    assert inventory["counts"]["audio_seconds_declared_ceiling"] == 18612
    assert inventory["counts"]["total_bytes"] == 352145084
    assert inventory["d1_closure"]["supplement_required"] is False
    assert inventory["d1_closure"]["closure_ids_for_carrier"] == 8690
    assert inventory["cpu_pipeline"]["workers"] == 8
    # THE measurement the carve-out was meant to produce: nothing on this roster
    # has ever been encoded, so the pass is contact-fresh row for row.
    assert inventory["legacy_feature_cache"]["warm_rows"] == 0
    assert inventory["legacy_feature_cache"]["cold_rows"] == ROWS
    assert inventory["promoted_packet_coverage"]["covered_rows"] == 0
    assert inventory["offline_guard"]["outbound_connection_attempts"] == 0
    assert plan["schema"] == "saea-slurp-speech-native-packet-plan-v1"
    assert plan["rows"] == ROWS
    assert plan["rows_needing_encode"] == ROWS
    assert plan["rows_promotable_with_zero_contacts"] == 0
    assert plan["binding"]["runtime_view_sha256"] == _json(VIEW_RELPATH)["runtime_view_sha256"]


def test_the_superseded_v1_packet_artifacts_are_still_committed_unchanged() -> None:
    """V1's 60 warm rows were exactly the carve-out; keep the evidence of that."""

    parent = _json(f"{PARENT_CHECK_DIR}/media-inventory.json")
    assert parent["counts"]["recordings"] == PARENT_ROWS
    assert parent["legacy_feature_cache"]["warm_rows"] == 60
    assert parent["roster"]["roster_id"] == "SLURP-DEVEL-REMAINDER-V1"
