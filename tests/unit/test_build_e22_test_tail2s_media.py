"""Model-free coverage for the Earnings-22 ESB TEST ``tail-silence-2s`` media build.

Every assertion runs on synthetic WAV bytes under ``tmp_path`` or on the
committed receipts the build landed. No data root, no parent MP3, no model,
network, tokenizer or scorer contact, and **no reference, output or score of the
six calibration-exposed test calls is opened here either** -- the committed
artifacts this module reads carry identifiers, media paths, measured media
identity and segment spans only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import wave
from array import array
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/build_e22_test_tail2s_media.py"
CHECK_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-e22-test2735-tail2s-media"
)
PUBLISHED_PER_CALL = {
    "4432298": 351,
    "4450488": 508,
    "4470290": 178,
    "4479741": 473,
    "4483338": 619,
    "4485244": 606,
}
SOURCE_AUDIO_SECONDS = 19494.608437


def _module():
    spec = importlib.util.spec_from_file_location("e22_test_tail2s_build_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = _module()


def _wav(path: Path, samples: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(array("h", samples).tobytes())


def _item(root: Path, samples: list[int], *, call: str = "4432298") -> dict:
    relpath = f"{MOD.SOURCE_MEDIA_SUBDIR}/{call}/{call}-7.wav"
    _wav(root / relpath, samples)
    return {
        "sample_id": f"{call}-7",
        "parent_sample_id": call,
        "parent_media_relpath": "datasets/earnings21-22/earnings22/media/%s.mp3" % call,
        "parent_sha256": "00" * 32,
        "parent_decoded_seconds": 2643.84,
        "media_relpath": relpath,
        "audio_seconds": len(samples) / 16000.0,
        "segment_start_seconds": 1.0,
        "segment_end_seconds": 1.0 + len(samples) / 16000.0,
        "end_clamped_to_decoded_parent": False,
    }


# ---------------------------------------------------------------------------
# The rule is the dev builder's, and the pin is self-checking
# ---------------------------------------------------------------------------


def test_the_pinned_dev_builder_digest_is_the_file_on_disk():
    """If the dev builder is edited, this pin must be re-stated deliberately."""

    measured = MOD.sha256_file(REPO / MOD.DEV_BUILDER_RELPATH)
    assert measured == MOD.DEV_BUILDER_SHA256


def test_loading_the_dev_builder_refuses_a_drifted_file(monkeypatch):
    monkeypatch.setattr(MOD, "DEV_BUILDER_SHA256", "ab" * 32)
    with pytest.raises(MOD.BuildError, match="drifted"):
        MOD.load_dev_builder()


def test_the_transform_used_is_the_dev_builders_own():
    dev = MOD.load_dev_builder()
    assert dev.VARIANTS[MOD.VARIANT]["suffix"] == MOD.ID_SUFFIX
    assert dev.TAIL_SILENCE_SAMPLES == 32000


# ---------------------------------------------------------------------------
# One clip, on synthetic bytes
# ---------------------------------------------------------------------------


def test_exactly_two_seconds_of_digital_silence_is_appended(tmp_path):
    dev = MOD.load_dev_builder()
    samples = [1, -2, 3, -4, 5]
    item = _item(tmp_path, samples)
    digest = MOD.sha256_file(tmp_path / item["media_relpath"])

    entry = MOD.build_one(dev, item, digest, tmp_path, write=True)

    assert entry["sample_id"] == "4432298-7@ts2"
    assert entry["published_segment_id"] == "4432298-7"
    assert entry["samples_added"] == 32000
    assert entry["samples_removed"] == 0
    assert entry["n_samples"] == len(samples) + 32000
    assert entry["unchanged"] is False
    assert entry["media_relpath"] == (
        f"{MOD.SUBDIR}/4432298/4432298-7@ts2.wav"
    )

    written = tmp_path / entry["media_relpath"]
    with wave.open(str(written), "rb") as handle:
        assert (handle.getframerate(), handle.getnchannels(), handle.getsampwidth()) == (
            16000,
            1,
            2,
        )
        produced = array("h", handle.readframes(handle.getnframes()))
    assert list(produced[: len(samples)]) == samples
    assert set(produced[len(samples) :]) == {0}
    assert MOD.sha256_file(written) == entry["audio_sha256"]


def test_a_source_byte_that_moved_since_the_cut_is_refused(tmp_path):
    dev = MOD.load_dev_builder()
    item = _item(tmp_path, [1, 2, 3])
    with pytest.raises(MOD.BuildError, match="source media drift"):
        MOD.build_one(dev, item, "cd" * 32, tmp_path, write=False)


def test_a_call_outside_the_six_test_calls_is_refused(tmp_path):
    dev = MOD.load_dev_builder()
    item = _item(tmp_path, [1, 2, 3], call="4453225")
    digest = MOD.sha256_file(tmp_path / item["media_relpath"])
    with pytest.raises(MOD.BuildError, match="not one of the six ESB test calls"):
        MOD.build_one(dev, item, digest, tmp_path, write=False)


def test_a_source_path_outside_the_sealed_test_root_is_refused(tmp_path):
    dev = MOD.load_dev_builder()
    item = dict(_item(tmp_path, [1, 2, 3]))
    item["media_relpath"] = "derived/e22-esb-utterances/dev-v1/4432298/4432298-7.wav"
    with pytest.raises(MOD.BuildError, match="escapes the sealed test root"):
        MOD.build_one(dev, item, "ef" * 32, tmp_path, write=False)


def test_a_roster_length_that_disagrees_with_the_clip_is_refused(tmp_path):
    dev = MOD.load_dev_builder()
    item = dict(_item(tmp_path, [1, 2, 3]))
    item["audio_seconds"] = 9.0
    digest = MOD.sha256_file(tmp_path / item["media_relpath"])
    with pytest.raises(MOD.BuildError, match="disagrees with roster"):
        MOD.build_one(dev, item, digest, tmp_path, write=False)


# ---------------------------------------------------------------------------
# The committed receipts
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def build_receipt() -> dict:
    return json.loads(
        (CHECK_DIR / "build-receipt.json").read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def probe_view() -> dict:
    return json.loads(
        (CHECK_DIR / "roster" / "flight-roster-receipt.json").read_text(encoding="utf-8")
    )


def test_the_build_receipt_records_a_model_free_row_with_zero_contacts(build_receipt):
    assert build_receipt["schema"] == "saea-e22-test2735-media-variant-build-receipt-v1"
    assert build_receipt["exposure_row"] == "SAEA-SN-MF-E22-TEST-TS2-MEDIA-V1"
    assert build_receipt["execution_profile"] == "model-free-check"
    assert set(build_receipt["contacts"].values()) == {0}


def test_no_test_side_text_output_or_score_was_opened(build_receipt):
    opened = build_receipt["opened"]
    assert opened["reference_sentences"] == 0
    assert opened["hypothesis_text"] == 0
    assert opened["scores"] == 0
    assert opened["sealed_outputs"] == 0
    assert opened["segment_table_columns"] == []
    assert build_receipt["test_split_read"] is True
    assert "MEDIA ONLY" in build_receipt["test_split_read_scope"]


def test_the_population_is_the_whole_published_test_subset(build_receipt, probe_view):
    assert build_receipt["count"] == 2735
    assert probe_view["count"] == 2735
    assert build_receipt["strata_counts"] == PUBLISHED_PER_CALL
    assert {
        call: value["utterances"] for call, value in probe_view["per_call"].items()
    } == PUBLISHED_PER_CALL


def test_the_media_facts_are_the_source_plus_exactly_two_seconds_a_clip(build_receipt):
    measured = build_receipt["measured_media"]
    assert measured["samples_added_total"] == 2735 * 32000
    assert measured["samples_removed_total"] == 0
    assert measured["clips_left_unchanged"] == 0
    assert measured["audio_seconds_total"] == pytest.approx(
        SOURCE_AUDIO_SECONDS + 2735 * 2.0, abs=1e-6
    )
    assert measured["audio_seconds_longest_item"] == pytest.approx(38.360125, abs=1e-9)
    # 0.2199375 s + 2.0 s, rounded to six places by the probe view.
    assert measured["audio_seconds_shortest_item"] == pytest.approx(2.2199375, abs=1e-6)
    assert measured["total_bytes"] == 623947810 + 2735 * 32000 * 2


def test_the_longest_clip_still_fits_the_sealed_test_flights_slot(build_receipt):
    """The sealed geometry is -c 32768 -np 8, i.e. 4,096 tokens a slot.

    Worst required = audio tokens + the 49-token text envelope the sealed test
    smoke measured + 1,024 completion + 2 special, and this repository's fit
    rule is ``slot_tokens >= 2 * worst_required``.
    """

    longest_tokens = build_receipt["measured_media"]["audio_tokens_longest_item"]
    assert longest_tokens == 507
    worst_required = longest_tokens + 49 + 1024 + 2
    assert 4096 >= 2 * worst_required


def test_the_receipts_chain_to_the_committed_test_population(build_receipt, probe_view):
    source = build_receipt["source_population"]
    assert source["roster_receipt_sha256"] == MOD.SOURCE_VIEW_SHA256
    assert source["d1_media_supplement_sha256"] == MOD.SOURCE_SUPPLEMENT_SHA256
    assert source["split_identity_hash"] == MOD.SOURCE_SPLIT_IDENTITY
    assert source["all_source_digests_matched"] is True
    assert source["files_rehashed_before_reading"] == 2735

    view_bytes = (CHECK_DIR / "roster" / "flight-roster-receipt.json").read_bytes()
    assert (
        hashlib.sha256(view_bytes).hexdigest()
        == build_receipt["outputs"]["probe_view_sha256"]
    )
    assert probe_view["derived_from"]["rule_implementation"]["sha256"] == (
        MOD.DEV_BUILDER_SHA256
    )


def test_the_supplement_is_additive_and_binds_to_this_populations_view(build_receipt):
    supplement = json.loads(
        (REPO / MOD.SUPPLEMENT_RELPATH).read_text(encoding="utf-8")
    )
    source_supplement = json.loads(
        (REPO / MOD.SOURCE_SUPPLEMENT_RELPATH).read_text(encoding="utf-8")
    )
    assert supplement["schema"] == "saea-d1-media-supplement-v1"
    assert supplement["carrier_lock_key"] == "earnings22-original"
    assert supplement["parent_d1_sha256"] == source_supplement["parent_d1_sha256"]
    assert supplement["source_binding_sha256"] == (
        build_receipt["outputs"]["probe_view_sha256"]
    )
    assert supplement["count"] == 2735

    published = {str(row["id"]) for row in source_supplement["manifest"]}
    ids = [str(row["id"]) for row in supplement["manifest"]]
    assert len(set(ids)) == 2735
    assert all(sample_id.endswith("@ts2") for sample_id in ids)
    assert {sample_id.split("@", 1)[0] for sample_id in ids} == published
    assert all(
        str(row["media_relpath"]).startswith(MOD.SUBDIR + "/")
        for row in supplement["manifest"]
    )


def test_the_variant_identity_differs_from_the_sealed_test_populations(build_receipt):
    assert build_receipt["split_identity_hash"] != MOD.SOURCE_SPLIT_IDENTITY
    assert len(build_receipt["split_identity_hash"]) == 64


def test_the_check_directory_manifests_verify():
    for directory in (CHECK_DIR, CHECK_DIR / "roster"):
        lines = (directory / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
        assert lines
        for line in lines:
            digest, name = line.split(" *", 1)
            assert MOD.sha256_file(directory / name) == digest
