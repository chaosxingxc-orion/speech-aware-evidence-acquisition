"""Model-free coverage for the ``E22-DEV-ESB-1500-V1`` roster builder.

Every assertion reads committed receipts or synthetic fixtures: no data root,
no media bytes, no model, network, tokenizer or scorer contact. The
re-hash pass is exercised against synthetic files under ``tmp_path``, so the
refusal it is supposed to raise is tested rather than assumed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/build_e22_dev1500_roster.py"
ROSTER = REPO / "docs/receipts/rosters/e22-dev-esb-1500-v1.json"
VIEW = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e22-dev-esb-1500-v1/roster/flight-roster-receipt.json"
)
SUPPLEMENT = REPO / "docs/receipts/artifacts/d1-e22-esb-dev1500-utterances.json"
SOURCE_VIEW = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-e22-dev-esb-prompt-ab-v1/roster/flight-roster-receipt.json"
)
SOURCE_SUPPLEMENT = REPO / "docs/receipts/artifacts/d1-e22-esb-dev10-utterances.json"


def _module():
    spec = importlib.util.spec_from_file_location("e22_dev1500_roster_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The committed artifacts
# ---------------------------------------------------------------------------


def test_the_roster_is_1500_rows_at_150_per_call() -> None:
    receipt = _load(ROSTER)
    assert receipt["roster_id"] == "E22-DEV-ESB-1500-V1"
    assert receipt["seed"] == 20260906
    assert receipt["split_role"] == "dev"
    assert receipt["roster_role"] == "evaluation"
    assert len(receipt["items"]) == 1500
    assert set(receipt["strata_counts"].values()) == {150}
    assert len(receipt["strata_counts"]) == 10


def test_the_roster_identity_hash_reverifies() -> None:
    from speech_aware_evidence_acquisition.core.roster import verify_roster

    receipt = _load(ROSTER)
    assert verify_roster(receipt) == receipt["split_identity_hash"]


def test_every_drawn_id_comes_from_the_sealed_dev10_roster() -> None:
    drawn = {item["sample_id"] for item in _load(ROSTER)["items"]}
    source = {item["sample_id"] for item in _load(SOURCE_VIEW)["items"]}
    assert drawn <= source
    assert len(drawn) == 1500


def test_the_draw_is_reproducible_from_the_committed_source() -> None:
    module = _module()
    receipt = module.draw(_load(SOURCE_VIEW))
    committed = _load(ROSTER)
    assert receipt["split_identity_hash"] == committed["split_identity_hash"]
    assert [item["sample_id"] for item in receipt["items"]] == [
        item["sample_id"] for item in committed["items"]
    ]


# ---------------------------------------------------------------------------
# The probe view
# ---------------------------------------------------------------------------


def test_the_probe_view_names_the_same_1500_and_keeps_the_sealed_media() -> None:
    view = _load(VIEW)
    roster = _load(ROSTER)
    source = {item["sample_id"]: item for item in _load(SOURCE_VIEW)["items"]}
    assert view["schema"] == "saea-e22-esb-utterance-roster-receipt-v1"
    assert view["count"] == 1500
    assert view["split_name"] == "E22-ESB-DEV1500-UTTERANCES"
    assert view["version"] == source["4453225-0"]["media_relpath"].split("/")[2]
    assert [item["sample_id"] for item in view["items"]] == [
        item["sample_id"] for item in roster["items"]
    ]
    for item in view["items"]:
        sealed = source[item["sample_id"]]
        assert item["media_relpath"] == sealed["media_relpath"]
        assert item["audio_sha256"] == sealed["audio_sha256"]
        assert item["bytes"] == sealed["bytes"]


def test_the_probe_views_derived_fields_are_recomputed_not_copied() -> None:
    view = _load(VIEW)
    source = _load(SOURCE_VIEW)
    items = view["items"]
    assert view["count"] != source["count"]
    assert view["audio_seconds_total"] == pytest.approx(
        round(sum(float(item["audio_seconds"]) for item in items), 6)
    )
    assert view["audio_seconds_longest_item"] == pytest.approx(
        round(max(float(item["audio_seconds"]) for item in items), 6)
    )
    assert view["audio_seconds_shortest_item"] == pytest.approx(
        round(min(float(item["audio_seconds"]) for item in items), 6)
    )
    per_call = Counter(item["parent_sample_id"] for item in items)
    assert {call: block["utterances"] for call, block in view["per_call"].items()} == dict(
        per_call
    )


def test_the_probe_views_own_digests_reproduce() -> None:
    module = _module()
    view = _load(VIEW)
    ids = [item["sample_id"] for item in view["items"]]
    assert view["ids_sha256"] == module.ids_sha256(ids)
    assert view["items_sha256"] == module.canonical_sha256(view["items"])


def test_the_probe_view_records_where_it_came_from() -> None:
    view = _load(VIEW)
    module = _module()
    assert view["derived_from"]["roster_receipt"] == module.SOURCE_ROSTER_RELPATH
    assert view["derived_from"]["roster_receipt_sha256"] == module.SOURCE_ROSTER_SHA256
    assert view["derived_from"]["media_root_unchanged"] is True
    assert "150" in view["derived_from"]["rule"]
    assert "20260906" in view["derived_from"]["rule"]


# ---------------------------------------------------------------------------
# The D1 supplement
# ---------------------------------------------------------------------------


def test_the_supplement_is_the_subset_with_its_own_digests() -> None:
    module = _module()
    media = _load(SUPPLEMENT)
    roster_ids = [item["sample_id"] for item in _load(ROSTER)["items"]]
    assert media["schema"] == "saea-d1-media-supplement-v1"
    assert media["carrier_lock_key"] == "earnings22-original"
    assert media["count"] == 1500
    assert [entry["id"] for entry in media["manifest"]] == roster_ids
    assert media["ids_sha256"] == module.ids_sha256(roster_ids)
    assert media["manifest_sha256"] == module.canonical_sha256(media["manifest"])
    assert media["total_bytes"] == sum(entry["bytes"] for entry in media["manifest"])


def test_the_supplement_chains_to_the_same_parent_and_binds_to_the_new_view() -> None:
    media = _load(SUPPLEMENT)
    source = _load(SOURCE_SUPPLEMENT)
    assert media["parent_d1_sha256"] == source["parent_d1_sha256"]
    assert media["source_binding_sha256"] == hashlib.sha256(VIEW.read_bytes()).hexdigest()
    assert media["source_binding_sha256"] != source["source_binding_sha256"]


def test_the_supplement_carries_only_the_gates_exact_keys() -> None:
    assert set(_load(SUPPLEMENT)) == {
        "schema",
        "study",
        "carrier_lock_key",
        "parent_d1_sha256",
        "source_binding_sha256",
        "count",
        "ids_sha256",
        "manifest",
        "manifest_sha256",
        "total_bytes",
    }


def test_every_supplement_entry_matches_the_sealed_dev10_one() -> None:
    media = {entry["id"]: entry for entry in _load(SUPPLEMENT)["manifest"]}
    source = {entry["id"]: entry for entry in _load(SOURCE_SUPPLEMENT)["manifest"]}
    for sample_id, entry in media.items():
        assert entry == source[sample_id]


# ---------------------------------------------------------------------------
# The re-hash pass, on synthetic files
# ---------------------------------------------------------------------------


def _synthetic_supplement(tmp_path: Path, payload: bytes) -> dict:
    relpath = "derived/e22-esb-utterances/dev-v1/C1/C1-0.wav"
    target = tmp_path / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return {
        "schema": "saea-d1-media-supplement-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier_lock_key": "earnings22-original",
        "parent_d1_sha256": "a" * 64,
        "source_binding_sha256": "b" * 64,
        "count": 1,
        "ids_sha256": "c" * 64,
        "manifest": [
            {
                "id": "C1-0",
                "media_relpath": relpath,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "audio_seconds": 1.0,
                "sample_rate_hz": 16000,
                "roles": ["query"],
            }
        ],
        "manifest_sha256": "d" * 64,
        "total_bytes": len(payload),
    }


def test_the_rehash_pass_accepts_bytes_that_still_match(tmp_path: Path) -> None:
    module = _module()
    source = _synthetic_supplement(tmp_path, b"RIFF-not-really-a-wav")
    document, evidence = module.supplement(
        source, ["C1-0"], view_sha256="e" * 64, root=tmp_path, rehash=True
    )
    assert document["count"] == 1
    assert document["source_binding_sha256"] == "e" * 64
    assert evidence["files_rehashed"] == 1
    assert evidence["all_digests_matched_the_sealed_supplement"] is True
    assert evidence["audio_samples_decoded"] == 0


def test_the_rehash_pass_refuses_drifted_media(tmp_path: Path) -> None:
    module = _module()
    source = _synthetic_supplement(tmp_path, b"RIFF-not-really-a-wav")
    target = tmp_path / source["manifest"][0]["media_relpath"]
    target.write_bytes(b"RIFF-different-bytes!")
    with pytest.raises(module.BuildError, match="media identity drift"):
        module.supplement(source, ["C1-0"], view_sha256="e" * 64, root=tmp_path, rehash=True)


def test_the_supplement_refuses_an_id_it_cannot_find(tmp_path: Path) -> None:
    module = _module()
    source = _synthetic_supplement(tmp_path, b"RIFF-not-really-a-wav")
    with pytest.raises(module.BuildError, match="kept 1 entries for 2 drawn ids"):
        module.supplement(
            source, ["C1-0", "C1-9"], view_sha256="e" * 64, root=tmp_path, rehash=False
        )


def test_load_pinned_refuses_a_drifted_source() -> None:
    module = _module()
    with pytest.raises(module.BuildError, match="identity drift"):
        module.load_pinned(module.SOURCE_ROSTER_RELPATH, "f" * 64, "dev10 roster")
