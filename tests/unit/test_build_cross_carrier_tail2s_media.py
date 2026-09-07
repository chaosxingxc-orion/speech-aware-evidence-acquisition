"""Model-free coverage for the cross-carrier ``tail-silence-2s`` media build.

Every assertion runs on synthetic audio under ``tmp_path`` or on the committed
receipts the build landed. No data root, no parent container, no model, network,
tokenizer or scorer contact, and **no gold label, reference transcript,
evaluation query, tool name, sealed output or score is opened** -- the committed
artifacts read here carry identifiers, media paths, measured media identity and
window spans only.
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
SCRIPT = REPO / "scripts/build_cross_carrier_tail2s_media.py"
CHECKS = REPO / "docs/checks/speech-aware-evidence-acquisition"

EXPECTED = {
    "slurp": {
        "dir": "2026-09-07-slurp-dev1000-tail2s-media",
        "count": 1000,
        "rate": 16000,
        "container": "flac",
        "split_identity": (
            "9f78d0ff2dbaf81f5e9f666ee036a3c994d69a7f464e555089e25decfd97f5c5"
        ),
        "source_seconds": 2884.793688,
        "variant_seconds": 4884.793687,
        "strata": 1,
    },
    "audio2tool": {
        "dir": "2026-09-07-a2t-calibration-400-tail2s-media",
        "count": 400,
        "rate": 24000,
        "container": "wav",
        "split_identity": (
            "6aa3aa43becbb4e11a42d174b181e2acc9ba5b5bdd599b2edbef93589536b503"
        ),
        "source_seconds": 2159.647,
        "variant_seconds": 2959.647,
        "strata": 8,
    },
    "earnings21": {
        "dir": "2026-09-07-e21-buf90-tail2s-media",
        "count": 1593,
        "rate": 16000,
        "container": "wav",
        "split_identity": (
            "c0765070db77dbda571262636716fc5d41b90a03ccc7ea6e0d644f649655522e"
        ),
        "source_seconds": 141345.852688,
        "variant_seconds": 144531.852688,
        "strata": 44,
    },
}


def _module():
    spec = importlib.util.spec_from_file_location("cross_carrier_ts2_build_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = _module()


def _receipt(carrier: str) -> dict:
    path = CHECKS / EXPECTED[carrier]["dir"] / "build-receipt.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _view(carrier: str) -> dict:
    path = CHECKS / EXPECTED[carrier]["dir"] / "roster" / "flight-roster-receipt.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The rule itself
# ---------------------------------------------------------------------------


def test_append_tail_is_two_seconds_at_every_supported_rate() -> None:
    for rate, tail in ((16000, 32000), (24000, 48000)):
        out = MOD.append_tail(array("h", [5, -5, 5]), rate)
        assert len(out) == 3 + tail
        assert list(out[:3]) == [5, -5, 5]
        assert set(out[3:]) == {0}


@pytest.mark.parametrize("rate", [0, -16000, 16000.0, True, "16000"])
def test_append_tail_refuses_a_rate_that_is_not_a_positive_integer(rate) -> None:
    with pytest.raises(MOD.BuildError, match="positive integer"):
        MOD.append_tail(array("h", [1]), rate)


def test_the_seconds_rule_reproduces_the_pinned_16khz_transform() -> None:
    """The equivalence the build proves before it touches a single clip."""

    dev = MOD.load_dev_builder()  # calls assert_rule_equivalence internally
    for samples in ([], [0], [32767, -32768, 1, -1, 0, 9]):
        probe = array("h", samples)
        pinned = dev.transform(MOD.VARIANT, probe, {"sample_id": "t"}, None)
        assert pinned == MOD.append_tail(probe, MOD.REFERENCE_SAMPLE_RATE_HZ)


def test_equivalence_check_fails_when_the_rule_drifts() -> None:
    class Drifted:
        VARIANTS = {MOD.VARIANT: {"suffix": MOD.ID_SUFFIX}}
        TAIL_SILENCE_SAMPLES = 32000

        @staticmethod
        def transform(variant, samples, item, spans):
            return samples + array("h", bytes(2 * 16))  # a 1 ms tail, not 2.0 s

    with pytest.raises(MOD.BuildError, match="does not reproduce the pinned"):
        MOD.assert_rule_equivalence(Drifted)


def test_the_pinned_builder_hash_is_the_one_the_e22_test_build_pins() -> None:
    """One rule, one pin: this build and the Earnings-22 TEST build agree."""

    sibling = (REPO / "scripts/build_e22_test_tail2s_media.py").read_text(
        encoding="utf-8"
    )
    assert MOD.DEV_BUILDER_SHA256 in sibling
    measured = MOD.sha256_file(REPO / MOD.DEV_BUILDER_RELPATH)
    assert measured == MOD.DEV_BUILDER_SHA256


# ---------------------------------------------------------------------------
# Containers
# ---------------------------------------------------------------------------


def _wav(path: Path, samples: list[int], rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(array("h", samples).tobytes())


def test_read_wav_round_trips_and_refuses_a_foreign_rate(tmp_path: Path) -> None:
    target = tmp_path / "clip.wav"
    _wav(target, [1, -2, 3], 24000)
    assert list(MOD.read_wav(target, 24000)) == [1, -2, 3]
    with pytest.raises(MOD.BuildError, match="16000 Hz mono int16"):
        MOD.read_wav(target, 16000)


def test_flac_encoding_is_lossless_and_deterministic() -> None:
    samples = array("h", [0, 1, -1, 32767, -32768] * 200)
    first = MOD.write_flac_bytes(samples, 16000)
    assert MOD.write_flac_bytes(samples, 16000) == first
    import soundfile as sf  # local, as the builder does

    import io

    decoded, rate = sf.read(io.BytesIO(first), dtype="int16", always_2d=False)
    assert rate == 16000
    assert array("h", decoded.tobytes()) == samples


# ---------------------------------------------------------------------------
# build_one, on synthetic bytes
# ---------------------------------------------------------------------------


def test_build_one_appends_the_tail_and_never_touches_the_sealed_samples(
    tmp_path: Path,
) -> None:
    samples = [7, -7, 11, -11]
    relpath = "derived/probe/clip.wav"
    _wav(tmp_path / relpath, samples, 16000)
    digest = MOD.sha256_file(tmp_path / relpath)
    carrier = {
        "container": "wav",
        "sample_rate_hz": 16000,
        "subdir": "derived/probe-ts2",
    }
    row = {
        "source_sample_id": "probe",
        "sample_id": "probe@ts2",
        "stratum": "s",
        "source_media_relpath": relpath,
        "source_audio_sha256": digest,
        "source_audio_seconds": len(samples) / 16000,
        "media_basename": "clip@ts2",
        "media_subdir": "",
        "extra": {"note": "carried through"},
    }
    entry = MOD.build_one(
        MOD.load_dev_builder(), row, carrier, tmp_path, write=True
    )
    assert entry["samples_added"] == 32000
    assert entry["samples_removed"] == 0
    assert entry["sample_rate_hz"] == 16000
    assert entry["note"] == "carried through"
    written = MOD.read_wav(tmp_path / entry["media_relpath"], 16000)
    assert list(written[: len(samples)]) == samples
    assert set(written[len(samples) :]) == {0}
    assert MOD.sha256_file(tmp_path / entry["media_relpath"]) == entry["audio_sha256"]


def test_build_one_refuses_a_source_whose_bytes_drifted(tmp_path: Path) -> None:
    relpath = "derived/probe/clip.wav"
    _wav(tmp_path / relpath, [1, 2, 3], 16000)
    row = {
        "source_sample_id": "probe",
        "sample_id": "probe@ts2",
        "stratum": "s",
        "source_media_relpath": relpath,
        "source_audio_sha256": "0" * 64,
        "source_audio_seconds": 3 / 16000,
        "media_basename": "clip@ts2",
        "media_subdir": "",
        "extra": {},
    }
    with pytest.raises(MOD.BuildError, match="source media drift"):
        MOD.build_one(
            MOD.load_dev_builder(),
            row,
            {"container": "wav", "sample_rate_hz": 16000, "subdir": "x"},
            tmp_path,
            write=False,
        )


def test_build_one_refuses_a_length_that_disagrees_with_the_receipt(
    tmp_path: Path,
) -> None:
    relpath = "derived/probe/clip.wav"
    _wav(tmp_path / relpath, [1] * 16000, 16000)
    row = {
        "source_sample_id": "probe",
        "sample_id": "probe@ts2",
        "stratum": "s",
        "source_media_relpath": relpath,
        "source_audio_sha256": MOD.sha256_file(tmp_path / relpath),
        "source_audio_seconds": 2.0,
        "media_basename": "clip@ts2",
        "media_subdir": "",
        "extra": {},
    }
    with pytest.raises(MOD.BuildError, match="pinned receipt records"):
        MOD.build_one(
            MOD.load_dev_builder(),
            row,
            {"container": "wav", "sample_rate_hz": 16000, "subdir": "x"},
            tmp_path,
            write=False,
        )


# ---------------------------------------------------------------------------
# The committed receipts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("carrier", sorted(EXPECTED))
def test_committed_build_receipt_matches_the_declared_population(carrier: str) -> None:
    receipt = _receipt(carrier)
    expected = EXPECTED[carrier]
    assert receipt["schema"] == MOD.BUILD_RECEIPT_SCHEMA
    assert receipt["variant"] == MOD.VARIANT
    assert receipt["execution_profile"] == "model-free-check"
    assert receipt["count"] == expected["count"]
    assert receipt["container"] == expected["container"]
    assert receipt["split_identity_hash"] == expected["split_identity"]
    assert len(receipt["strata_counts"]) == expected["strata"]
    assert sum(receipt["strata_counts"].values()) == expected["count"]
    assert receipt["rule_implementation"]["sha256"] == MOD.DEV_BUILDER_SHA256
    assert receipt["test_split_read"] is False


@pytest.mark.parametrize("carrier", sorted(EXPECTED))
def test_committed_receipt_records_zero_contacts_and_zero_gold(carrier: str) -> None:
    receipt = _receipt(carrier)
    contacts = receipt["contacts"]
    for field in (
        "frozen_core",
        "tokenizer",
        "embedder",
        "retriever",
        "scorer",
        "network",
        "gpu_hours",
        "paid_api_spend",
        "parent_container_decodes",
        "librosa_calls",
        "ffmpeg_calls",
        "outbound_connection_attempts",
    ):
        assert contacts[field] == 0, field
    opened = receipt["opened"]
    for field in (
        "gold_labels",
        "reference_transcripts",
        "evaluation_query_text",
        "tool_registry_rows",
        "sealed_outputs",
        "hypothesis_text",
        "scores",
    ):
        assert opened[field] == 0, field


@pytest.mark.parametrize("carrier", sorted(EXPECTED))
def test_the_tail_accounting_closes_exactly(carrier: str) -> None:
    """Variant seconds - source seconds must be exactly 2.0 s per clip."""

    receipt = _receipt(carrier)
    expected = EXPECTED[carrier]
    media = receipt["measured_media"]
    assert media["samples_removed_total"] == 0
    assert media["clips_left_unchanged"] == 0
    assert media["samples_added_total"] == expected["count"] * int(
        MOD.TAIL_SILENCE_SECONDS * expected["rate"]
    )
    assert media["source_audio_seconds_total"] == pytest.approx(
        expected["source_seconds"], abs=1e-6
    )
    assert media["audio_seconds_total"] == pytest.approx(
        expected["variant_seconds"], abs=1e-6
    )
    assert media["audio_seconds_total"] - media["source_audio_seconds_total"] == (
        pytest.approx(2.0 * expected["count"], abs=1e-3)
    )


@pytest.mark.parametrize("carrier", sorted(EXPECTED))
def test_probe_view_ids_are_sorted_suffixed_and_unique(carrier: str) -> None:
    view = _view(carrier)
    ids = [str(item["sample_id"]) for item in view["items"]]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids) == EXPECTED[carrier]["count"]
    assert all(identifier.endswith("@ts2") for identifier in ids)
    assert view["ids_sha256"] == MOD.ids_sha256(ids)
    assert view["items_sha256"] == MOD.canonical_sha256(view["items"])
    # The sealed key is recoverable by splitting on '@', which is what makes the
    # paired join against the comparator exact.
    assert all(
        item["sample_id"].rsplit("@", 1)[0] == item["source_sample_id"]
        for item in view["items"]
    )


@pytest.mark.parametrize("carrier", sorted(EXPECTED))
def test_media_paths_stay_inside_this_variant_root(carrier: str) -> None:
    view = _view(carrier)
    receipt = _receipt(carrier)
    root = receipt["media_root"] + "/"
    for item in view["items"]:
        assert str(item["media_relpath"]).startswith(root)
        assert "@ts2." in str(item["media_relpath"])
        # Never inside the comparator's own media root.
        assert not str(item["media_relpath"]).startswith(
            str(item["source_media_relpath"])
        )


@pytest.mark.parametrize("carrier", sorted(EXPECTED))
def test_d1_supplement_agrees_with_the_probe_view(carrier: str) -> None:
    receipt = _receipt(carrier)
    supplement = json.loads(
        (REPO / receipt["outputs"]["d1_media_supplement"]).read_text(encoding="utf-8")
    )
    view = _view(carrier)
    assert supplement["schema"] == MOD.SUPPLEMENT_SCHEMA
    assert supplement["count"] == EXPECTED[carrier]["count"]
    assert supplement["source_binding_sha256"] == receipt["outputs"]["probe_view_sha256"]
    by_id = {str(row["id"]): row for row in supplement["manifest"]}
    for item in view["items"]:
        row = by_id[str(item["sample_id"])]
        assert row["sha256"] == item["audio_sha256"]
        assert row["bytes"] == item["bytes"]
        assert row["media_relpath"] == item["media_relpath"]
        assert row["sample_rate_hz"] == EXPECTED[carrier]["rate"]
    assert supplement["total_bytes"] == receipt["measured_media"]["total_bytes"]


@pytest.mark.parametrize("carrier", sorted(EXPECTED))
def test_frozen_roster_receipt_hash_matches_the_build_receipt(carrier: str) -> None:
    from speech_aware_evidence_acquisition.core.roster import (
        canonical_receipt_bytes,
        read_roster,
    )

    receipt = _receipt(carrier)
    roster = read_roster(REPO / receipt["outputs"]["roster_receipt"])
    assert roster["split_identity_hash"] == receipt["split_identity_hash"]
    digest = hashlib.sha256(canonical_receipt_bytes(roster)).hexdigest()
    assert digest == receipt["outputs"]["roster_receipt_sha256"]


@pytest.mark.parametrize("carrier", sorted(EXPECTED))
def test_the_variant_identity_differs_from_its_comparator(carrier: str) -> None:
    """The whole point of the ``@ts2`` suffix: a separate split identity."""

    receipt = _receipt(carrier)
    comparator = receipt["comparator"]["split_identity_hash"]
    assert receipt["split_identity_hash"] != comparator


@pytest.mark.parametrize("carrier", sorted(EXPECTED))
def test_manifest_lists_every_file_in_the_receipt_directory(carrier: str) -> None:
    directory = CHECKS / EXPECTED[carrier]["dir"]
    for folder in (directory, directory / "roster"):
        lines = (folder / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
        listed = {line.split(" *", 1)[1] for line in lines if line}
        present = {
            path.name
            for path in folder.iterdir()
            if path.is_file() and path.name != "MANIFEST.sha256"
        }
        assert listed == present
        for line in lines:
            digest, name = line.split(" *", 1)
            assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest


# ---------------------------------------------------------------------------
# The measurement the cross-carrier prediction rests on
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("carrier", sorted(EXPECTED))
def test_trailing_silence_summary_reproduces_from_the_per_item_rows(
    carrier: str,
) -> None:
    view = _view(carrier)
    summary = view["sealed_clip_trailing_silence"]
    values = [float(item["source_trailing_silence_seconds"]) for item in view["items"]]
    assert summary["n"] == len(values) == EXPECTED[carrier]["count"]
    assert summary["min"] == min(values)
    assert summary["max"] == max(values)
    assert summary["ends_exactly_at_an_active_frame"] == sum(
        1 for value in values if value == 0.0
    )
    assert summary["trailing_silence_at_least_2_00_s"] == sum(
        1 for value in values if value >= 2.0
    )
    assert summary["mean"] == pytest.approx(sum(values) / len(values), abs=1e-6)


def test_earnings21_windows_end_mid_speech_far_more_often_than_the_other_two() -> None:
    """The finding the Earnings-21 cell rests on, asserted rather than narrated.

    A fixed 90-second cut has no reason to land in a pause, and it does not:
    two thirds of the sealed windows end on an ACTIVE frame. The SLURP and
    Audio2Tool clips are utterance recordings and end far more politely.
    """

    shares = {}
    for carrier in EXPECTED:
        summary = _view(carrier)["sealed_clip_trailing_silence"]
        shares[carrier] = (
            summary["ends_exactly_at_an_active_frame"] / summary["n"]
        )
    assert shares["earnings21"] > 0.60
    assert shares["audio2tool"] < 0.10
    assert shares["earnings21"] > shares["slurp"] > shares["audio2tool"]


# ---------------------------------------------------------------------------
# The SLURP packet-promotion plan
# ---------------------------------------------------------------------------


def test_only_slurp_carries_a_packet_promotion_plan() -> None:
    assert "packet_promotion_plan" not in _receipt("audio2tool")
    assert "packet_promotion_plan" not in _receipt("earnings21")
    plan = _receipt("slurp")["packet_promotion_plan"]
    encode = plan["encode_pass"]
    assert encode["contacts"] == 1000
    assert encode["gpu_hours"] == 0.0
    assert encode["max_tokens"] == 1
    assert encode["execution_profile"] == "bounded-discovery-probe"
    assert "NOT registered here" in encode["exposure_row"]
    assert plan["promotion"]["contacts"] == 0
    assert encode["audio_seconds"] == pytest.approx(4884.794, abs=1e-3)


def test_packet_promotion_is_needed_because_the_cache_key_is_the_media_bytes() -> None:
    """Not a guess: the key really is FNV-1a over the file's own bytes."""

    from speech_aware_evidence_acquisition.core.model.speech_features import (
        legacy_audio_feature_cache_key,
    )

    sealed = b"sealed clip bytes"
    assert legacy_audio_feature_cache_key(sealed) != legacy_audio_feature_cache_key(
        sealed + b"\x00\x00"
    )
