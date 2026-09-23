"""Model-free coverage for the R01C clean-subset builder.

The builder's whole claim is that R01C is a PURE SELECTION of R01 taken at
UTTERANCE granularity. This module drives its selection, receipt, runtime-view
and vector-subset functions with synthetic rosters, snapshots and vector files
-- no corpus byte, transcript, label, vector or model is touched anywhere -- and
asserts exactly that: which rows leave, that order survives, that the counts and
the identity hash agree with what came out, and that the surviving bytes are the
parent's own.

The oracles are the production ones wherever one exists: the roster receipt is
handed to ``core.roster.verify_roster``, the runtime view's signature is checked
by the same canonical-JSON rule ``data.slurp.load_slurp_engineering_gate``
applies, and the identity hash is recomputed with ``data.splits``.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.roster import RosterError, verify_roster
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/build_slurp_stage3_construction_clean_subset.py"


def _builder():
    spec = importlib.util.spec_from_file_location(
        "slurp_stage3_clean_subset_under_test", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = _builder()


def _item(numeric: int, recording: str, stratum: str, seconds: float, rank: int) -> dict:
    return {
        "audio_seconds": seconds,
        "draw_rank": rank,
        "headset": recording.endswith("-headset"),
        "sample_id": f"slurp:train:{numeric:06d}:{recording}",
        "stratum": stratum,
        "utterance_id": f"slurp:train:{numeric:06d}",
    }


#: Four utterances, one of them present TWICE (the ``-headset`` sibling of
#: utterance 000002) so the utterance-granularity rule has something to prove.
ITEMS = [
    _item(1, "audio-a", "alarm", 1.5, 3),
    _item(2, "audio-b", "email", 2.5, 1),
    _item(2, "audio-b-headset", "email", 2.5, 2),
    _item(3, "audio-c", "alarm", 3.5, 4),
    _item(4, "audio-d", "qa", 4.5, 5),
]


def test_selection_is_by_utterance_not_by_recording():
    """A knowledge source takes its whole utterance with it, sibling included."""

    kept, excluded = BUILDER.select_clean_items(
        ITEMS, ["slurp:train:000002:audio-b"]
    )
    assert [item["sample_id"] for item in excluded] == [
        "slurp:train:000002:audio-b",
        "slurp:train:000002:audio-b-headset",
    ]
    assert [item["sample_id"] for item in kept] == [
        "slurp:train:000001:audio-a",
        "slurp:train:000003:audio-c",
        "slurp:train:000004:audio-d",
    ]


def test_a_source_naming_only_the_sibling_still_removes_both():
    kept, excluded = BUILDER.select_clean_items(
        ITEMS, ["slurp:train:000002:audio-b-headset"]
    )
    assert len(excluded) == 2 and len(kept) == 3


def test_order_is_preserved_and_items_are_the_parent_objects():
    kept, _ = BUILDER.select_clean_items(ITEMS, ["slurp:train:000003:audio-c"])
    assert [item["sample_id"] for item in kept] == [
        "slurp:train:000001:audio-a",
        "slurp:train:000002:audio-b",
        "slurp:train:000002:audio-b-headset",
        "slurp:train:000004:audio-d",
    ]
    # pure selection: no item is copied or rewritten
    assert all(any(item is source for source in ITEMS) for item in kept)


def test_an_empty_source_set_keeps_everything():
    kept, excluded = BUILDER.select_clean_items(ITEMS, [])
    assert kept == ITEMS and excluded == []


def test_a_source_outside_the_roster_removes_nothing():
    kept, excluded = BUILDER.select_clean_items(
        ITEMS, ["slurp:train:009999:audio-z"]
    )
    assert len(kept) == len(ITEMS) and excluded == []


@pytest.mark.parametrize(
    "bad", ["slurp:train:000001", "audio2tool:train:000001:x", "nonsense"]
)
def test_a_malformed_recording_id_fails_closed(bad: str):
    with pytest.raises(BUILDER.SubsetError):
        BUILDER.select_clean_items(ITEMS, [bad])


def test_a_roster_item_without_a_sample_id_fails_closed():
    with pytest.raises(BUILDER.SubsetError):
        BUILDER.select_clean_items([{"stratum": "alarm"}], [])


# -- receipt ---------------------------------------------------------------


def _parent_receipt(tmp_path: Path) -> tuple[dict, str, Path]:
    ids = [item["sample_id"] for item in ITEMS]
    receipt = {
        "schema": "saea-roster-receipt-v1",
        "roster_id": "SLURP-STAGE3-CONSTRUCTION-TEST",
        "carrier_lock_key": "slurp",
        "split_role": "discovery",
        "roster_role": "construction",
        "seed": 20260922,
        "per_stratum": {"alarm": 2, "email": 2, "qa": 1},
        "strata_counts": {"alarm": 2, "email": 2, "qa": 1},
        "items": ITEMS,
        "excluded_count": 0,
        "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
        "pool_receipt": {"relpath": "docs/receipts/knowledge/fake.json", "sha256": "0" * 64},
        "vectors": {"relpath": "vectors/fake.jsonl", "sha256": "1" * 64, "dimension": "content"},
        "disjointness_proof": {"excluded_utterances_before_the_draw": 0},
    }
    verify_roster(receipt)
    path = tmp_path / "parent.json"
    path.write_bytes(BUILDER.committed_json_bytes(receipt))
    return receipt, BUILDER.sha256_file(path), path


def _guard_report() -> dict:
    return {
        "binding_sha256": "2" * 64,
        "composite_snapshot_sha256": "3" * 64,
        "composite_source_sample_ids": 1,
        "stores": {},
    }


def _receipt_for(tmp_path: Path, sources: list[str]) -> dict:
    parent, parent_sha256, _ = _parent_receipt(tmp_path)
    kept, excluded = BUILDER.select_clean_items(parent["items"], sources)
    return BUILDER.build_receipt(
        parent,
        "docs/receipts/rosters/parent.json",
        parent_sha256,
        kept,
        excluded,
        _guard_report(),
        sources,
        {"relpath": "docs/receipts/artifacts/d1.json", "note": "test"},
        {"outbound_connection_attempts": 0, "attempted_targets": []},
    )


def test_the_receipt_verifies_and_reports_the_counts_it_produced(tmp_path: Path):
    receipt = _receipt_for(tmp_path, ["slurp:train:000002:audio-b"])
    assert verify_roster(receipt) == receipt["split_identity_hash"]
    assert receipt["roster_id"] == "SLURP-STAGE3-CONSTRUCTION-R01C"
    assert receipt["roster_role"] == "construction"
    assert len(receipt["items"]) == 3
    assert receipt["excluded_count"] == 2
    assert receipt["exclusion"]["excluded_recordings"] == 2
    assert receipt["exclusion"]["excluded_utterances"] == 1
    assert receipt["exclusion"]["excluded_sample_ids"] == [
        "slurp:train:000002:audio-b",
        "slurp:train:000002:audio-b-headset",
    ]
    assert receipt["strata_counts"] == {"alarm": 2, "qa": 1}
    assert receipt["exclusion"]["excluded_per_stratum"] == {"email": 2}
    assert receipt["per_stratum"] == receipt["strata_counts"]
    assert sum(receipt["strata_counts"].values()) == len(receipt["items"])
    assert receipt["parent"]["count"] == len(ITEMS)
    assert receipt["parent"]["split_identity_hash"] != receipt["split_identity_hash"]
    assert receipt["knowledge_source_guard"]["overlap_with_r01c_recordings"] == 0
    assert receipt["seed"] == 20260922


def test_the_receipt_identity_is_recomputed_from_the_surviving_ids(tmp_path: Path):
    receipt = _receipt_for(tmp_path, ["slurp:train:000003:audio-c"])
    ids = [item["sample_id"] for item in receipt["items"]]
    assert receipt["split_identity_hash"] == split_identity_hash(prefixed("slurp", ids))


def test_a_receipt_that_still_carries_a_knowledge_source_is_refused(tmp_path: Path):
    """The guard is asserted on the OUTPUT, not assumed from the selector."""

    parent, parent_sha256, _ = _parent_receipt(tmp_path)
    with pytest.raises(BUILDER.SubsetError):
        BUILDER.build_receipt(
            parent,
            "docs/receipts/rosters/parent.json",
            parent_sha256,
            parent["items"],  # nothing dropped
            [],
            _guard_report(),
            ["slurp:train:000001:audio-a"],
            {},
            {"outbound_connection_attempts": 0, "attempted_targets": []},
        )


# -- runtime view ----------------------------------------------------------


def _parent_view() -> dict:
    items = [
        {
            "sample_id": item["sample_id"],
            "media_relpath": f"datasets/slurp/slurp_real/{item['sample_id'].split(':')[3]}.flac",
            "audio_sha256": "4" * 64,
            "audio_seconds": item["audio_seconds"],
            "sample_rate_hz": 16000,
            "packet_id": item["sample_id"].replace(":", "/"),
        }
        for item in ITEMS
    ]
    unsigned = {
        "schema": "saea-speech-native-runtime-view-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION",
        "carrier_lock_key": "slurp",
        "split_name": "STAGE3-CONSTRUCTION-TEST",
        "split_role": "discovery",
        "seed": 20260922,
        "split_identity_hash": "5" * 64,
        "source_binding_sha256": "6" * 64,
        "d1_media_supplement": "receipts/artifacts/d1-parent.json",
        "d1_media_supplement_sha256": "7" * 64,
        "d1_manifest_sha256": "8" * 64,
        "count": len(items),
        "audio_seconds_total": round(sum(i["audio_seconds"] for i in items), 9),
        "items": items,
    }
    return {**unsigned, "runtime_view_sha256": BUILDER.canonical_sha256(unsigned)}


def test_the_runtime_view_is_the_parents_rows_re_signed(tmp_path: Path):
    receipt = _receipt_for(tmp_path, ["slurp:train:000002:audio-b"])
    view = BUILDER.build_runtime_view(_parent_view(), receipt)

    assert view["count"] == 3
    assert view["split_name"] == "STAGE3-CONSTRUCTION-R01C"
    assert view["split_identity_hash"] == receipt["split_identity_hash"]
    assert view["source_binding_sha256"] == BUILDER.canonical_sha256(receipt)
    assert view["audio_seconds_total"] == pytest.approx(1.5 + 3.5 + 4.5)
    assert [item["sample_id"] for item in view["items"]] == sorted(
        item["sample_id"] for item in receipt["items"]
    )
    # the D1 supplement triple is carried verbatim: the parent covers a superset
    parent = _parent_view()
    for key in (
        "d1_media_supplement",
        "d1_media_supplement_sha256",
        "d1_manifest_sha256",
        "seed",
        "status",
    ):
        assert view[key] == parent[key]
    # the exact 16-key contract data.slurp.load_slurp_engineering_gate requires
    assert set(view) == set(parent)
    unsigned = {k: v for k, v in view.items() if k != "runtime_view_sha256"}
    assert view["runtime_view_sha256"] == BUILDER.canonical_sha256(unsigned)


def test_a_tampered_parent_view_is_refused(tmp_path: Path):
    receipt = _receipt_for(tmp_path, ["slurp:train:000002:audio-b"])
    parent = _parent_view()
    parent["count"] = 99
    with pytest.raises(BUILDER.SubsetError):
        BUILDER.build_runtime_view(parent, receipt)


# -- vector subsets --------------------------------------------------------


def _vector_bytes() -> bytes:
    lines = [
        json.dumps(
            {"id": item["sample_id"], "vectors": {"content": [float(index)]}},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        for index, item in enumerate(ITEMS)
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def test_the_vector_subset_keeps_the_parents_own_line_bytes():
    raw = _vector_bytes()
    kept_ids = [
        "slurp:train:000001:audio-a",
        "slurp:train:000003:audio-c",
        "slurp:train:000004:audio-d",
    ]
    payload, rows = BUILDER.subset_vector_lines(raw, kept_ids, label="test")
    assert rows == 3
    parent_lines = raw.decode("utf-8").splitlines()
    kept_lines = payload.decode("utf-8").splitlines()
    assert kept_lines == [
        line for line in parent_lines if json.loads(line)["id"] in set(kept_ids)
    ]
    # order is the parent's, and the file ends with exactly one newline
    assert [json.loads(line)["id"] for line in kept_lines] == kept_ids
    assert payload.endswith(b"}\n") and not payload.endswith(b"\n\n")


def test_a_vector_file_missing_an_id_fails_closed():
    with pytest.raises(BUILDER.SubsetError):
        BUILDER.subset_vector_lines(
            _vector_bytes(), ["slurp:train:009999:audio-z"], label="test"
        )


def test_a_vector_file_repeating_an_id_fails_closed():
    raw = _vector_bytes()
    doubled = raw + raw.splitlines()[0] + b"\n"
    with pytest.raises(BUILDER.SubsetError):
        BUILDER.subset_vector_lines(
            doubled, ["slurp:train:000001:audio-a"], label="test"
        )


# -- constants the registration depends on ---------------------------------


def test_the_builder_targets_the_registered_roll1_cell_and_paths():
    assert BUILDER.ROSTER_ID == "SLURP-STAGE3-CONSTRUCTION-R01C"
    assert BUILDER.SPLIT_NAME == "STAGE3-CONSTRUCTION-R01C"
    assert BUILDER.SPLIT_ROLE == "discovery"
    assert BUILDER.CELL_BASELINE_FRAGMENT == "slurp-native-stage3-rollout-baseline-v1"
    assert (REPO / BUILDER.PARENT_ROSTER_RELPATH).is_file()
    assert (REPO / BUILDER.PARENT_VIEW_RELPATH).is_file()
    assert (REPO / BUILDER.ROSTER_RELPATH).is_file()
    assert (REPO / BUILDER.RUNTIME_VIEW_RELPATH).is_file()


def test_the_committed_r01c_receipt_is_the_one_this_builder_describes():
    receipt = json.loads(
        (REPO / BUILDER.ROSTER_RELPATH).read_text(encoding="utf-8")
    )
    parent = json.loads(
        (REPO / BUILDER.PARENT_ROSTER_RELPATH).read_text(encoding="utf-8")
    )
    assert verify_roster(receipt) == receipt["split_identity_hash"]
    assert receipt["selection_rule"] == BUILDER.SELECTION_RULE
    assert len(receipt["items"]) + receipt["excluded_count"] == len(parent["items"])
    parent_ids = [str(item["sample_id"]) for item in parent["items"]]
    kept_ids = [str(item["sample_id"]) for item in receipt["items"]]
    assert kept_ids == [sid for sid in parent_ids if sid in set(kept_ids)]
    assert receipt["knowledge_source_guard"]["overlap_with_r01c_recordings"] == 0
    assert receipt["offline_guard"]["outbound_connection_attempts"] == 0


def test_the_committed_r01c_dataset_fragment_matches_its_receipt():
    receipt = json.loads(
        (REPO / BUILDER.ROSTER_RELPATH).read_text(encoding="utf-8")
    )
    view = json.loads(
        (REPO / BUILDER.RUNTIME_VIEW_RELPATH).read_text(encoding="utf-8")
    )
    unsigned = {k: v for k, v in view.items() if k != "runtime_view_sha256"}
    assert view["runtime_view_sha256"] == BUILDER.canonical_sha256(unsigned)
    assert view["split_name"] == BUILDER.SPLIT_NAME
    assert view["count"] == len(receipt["items"])
    assert view["split_identity_hash"] == receipt["split_identity_hash"]
    assert view["source_binding_sha256"] == BUILDER.canonical_sha256(receipt)
    assert {item["sample_id"] for item in view["items"]} == {
        item["sample_id"] for item in receipt["items"]
    }


def test_a_receipt_with_a_duplicate_row_is_refused_by_the_shared_oracle(tmp_path: Path):
    receipt = _receipt_for(tmp_path, ["slurp:train:000002:audio-b"])
    receipt["items"] = list(receipt["items"]) + [receipt["items"][0]]
    with pytest.raises(RosterError):
        verify_roster(receipt)
