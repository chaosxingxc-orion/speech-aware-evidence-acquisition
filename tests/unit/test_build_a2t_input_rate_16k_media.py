"""Model-free coverage for the Audio2Tool input-rate standardized media build.

Every assertion runs on synthetic audio built in-process or on the committed
receipts the build landed. No data root, no model, network, tokenizer or scorer
contact, and **no gold label, reference transcript, evaluation query, tool name,
sealed output or score is opened** -- the committed artifacts read here carry
identifiers, media paths and measured media identity only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from array import array
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/build_a2t_input_rate_16k_media.py"
CHECKS = REPO / "docs/checks/speech-aware-evidence-acquisition"

EXPECTED = {
    "16k": {
        "dir": "2026-09-07-a2t-calibration-400-16k-media",
        "variant": "input-rate-16k",
        "split_name": "A2T-CALIBRATION-400-16K",
        "split_identity": (
            "292b7220abc5e44325c01aad555d3813aa24cb4db8f5d6e414fded836d7f12b0"
        ),
        "seconds": 2159.647312,
        "bytes": 69126314,
        "tail_samples": 0,
    },
    "16k+ts2": {
        "dir": "2026-09-07-a2t-calibration-400-16k-tail2s-media",
        "variant": "input-rate-16k+tail-silence-2s",
        "split_name": "A2T-CALIBRATION-400-16K-TAIL2S",
        "split_identity": (
            "655b5ed6a65325891e9824d3bb25964681d50c8bb9f36e2deb11822e3179db67"
        ),
        "seconds": 2959.647312,
        "bytes": 94726314,
        "tail_samples": 400 * 32000,
    },
}


def _module():
    spec = importlib.util.spec_from_file_location("a2t_input_rate_16k_build_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = _module()


def _receipt(name: str) -> dict:
    path = CHECKS / EXPECTED[name]["dir"] / "build-receipt.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _view(name: str) -> dict:
    path = CHECKS / EXPECTED[name]["dir"] / "roster/flight-roster-receipt.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The rules, on synthetic input
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_in", [1, 2, 3, 24000, 24001, 24002, 24003, 35932, 857145])
def test_expected_output_samples_is_ceil_two_thirds(n_in: int) -> None:
    assert MOD.expected_output_samples(n_in) == math.ceil(n_in * 2 / 3)


def test_expected_output_samples_never_loses_a_sample() -> None:
    # The property the build asserts per clip: the standardized duration is never
    # SHORTER than the sealed one. llama.cpp's own decoder floors instead.
    for n_in in range(1, 400):
        out = MOD.expected_output_samples(n_in)
        assert out / MOD.TARGET_SAMPLE_RATE_HZ >= n_in / MOD.SOURCE_SAMPLE_RATE_HZ


def test_the_pinned_tail_is_exactly_two_seconds_at_sixteen_k() -> None:
    dev = MOD.load_dev_builder()
    probe = array("h", [0, 1, -1, 32767, -32768, 7, -7])
    produced = MOD.append_tail(dev, probe, "probe")
    assert len(produced) == len(probe) + 32000
    assert produced[: len(probe)] == probe
    assert not any(produced[len(probe) :])


def test_append_tail_refuses_a_tail_that_is_not_two_seconds(monkeypatch) -> None:
    class Fake:
        @staticmethod
        def transform(variant, samples, meta, extra):  # noqa: ANN001, ARG004
            return samples + array("h", bytes(2 * 100))

    with pytest.raises(MOD.BuildError, match="not exactly 2.0 s"):
        MOD.append_tail(Fake, array("h", [1, 2, 3]), "probe")


def test_band_energy_shares_separates_low_from_high() -> None:
    numpy = pytest.importorskip("numpy")
    times = numpy.arange(MOD.SOURCE_SAMPLE_RATE_HZ) / float(MOD.SOURCE_SAMPLE_RATE_HZ)
    low = array(
        "h",
        numpy.rint(0.5 * 32767 * numpy.sin(2 * numpy.pi * 1000 * times)).astype("int16").tolist(),
    )
    high = array(
        "h",
        numpy.rint(0.5 * 32767 * numpy.sin(2 * numpy.pi * 9000 * times)).astype("int16").tolist(),
    )
    low_shares = MOD.band_energy_shares(low, MOD.SOURCE_SAMPLE_RATE_HZ)
    high_shares = MOD.band_energy_shares(high, MOD.SOURCE_SAMPLE_RATE_HZ)
    assert low_shares["source_energy_above_4k_share"] < 1e-6
    assert low_shares["source_energy_above_8k_share"] < 1e-6
    assert high_shares["source_energy_above_8k_share"] > 0.999
    assert set(low_shares) == {
        f"source_energy_above_{edge // 1000}k_share" for edge in MOD.BAND_EDGES_HZ
    }


def test_band_energy_shares_is_zero_on_an_empty_clip() -> None:
    shares = MOD.band_energy_shares(array("h"), MOD.SOURCE_SAMPLE_RATE_HZ)
    assert all(value == 0.0 for value in shares.values())


# ---------------------------------------------------------------------------
# The variant descriptors
# ---------------------------------------------------------------------------


def test_the_two_variants_share_no_output_path_or_identity() -> None:
    keys = ("subdir", "roster_id", "split_name", "roster_receipt", "supplement", "out_dir")
    for key in keys:
        values = [str(variant[key]) for variant in MOD.VARIANTS.values()]
        assert len(set(values)) == len(values), key


def test_the_variant_ids_recover_the_sealed_key() -> None:
    from speech_aware_evidence_acquisition.reproduction.esb_reference import (
        published_segment_key,
    )

    for variant in MOD.VARIANTS.values():
        variant_id = f"tier1_direct:000045@{variant['id_suffix']}"
        assert published_segment_key(variant_id) == "tier1_direct:000045"
    # And an unsuffixed id is untouched, which is what keeps every pre-existing
    # population byte-for-byte unaffected.
    assert published_segment_key("tier1_direct:000045") == "tier1_direct:000045"


# ---------------------------------------------------------------------------
# The committed receipts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_receipt_identity(name: str) -> None:
    receipt = _receipt(name)
    expected = EXPECTED[name]
    assert receipt["schema"] == "saea-a2t-input-rate-16k-media-build-receipt-v1"
    assert receipt["exposure_row"] == "SAEA-SN-MF-A2T-CAL400-16K-MEDIA-V1"
    assert receipt["execution_profile"] == "model-free-check"
    assert receipt["variant"] == expected["variant"]
    assert receipt["split_name"] == expected["split_name"]
    assert receipt["split_identity_hash"] == expected["split_identity"]
    assert receipt["split_role"] == "discovery"
    assert receipt["count"] == 400
    assert receipt["source_sample_rate_hz"] == 24000
    assert receipt["sample_rate_hz"] == 16000
    assert receipt["test_split_read"] is False
    assert receipt["strata_counts"] == {tier: 50 for tier in receipt["strata_counts"]}
    assert len(receipt["strata_counts"]) == 8


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_receipt_measured_media(name: str) -> None:
    media = _receipt(name)["measured_media"]
    expected = EXPECTED[name]
    assert media["audio_seconds_total"] == pytest.approx(expected["seconds"], abs=1e-6)
    assert media["total_bytes"] == expected["bytes"]
    assert media["samples_added_by_tail_total"] == expected["tail_samples"]
    assert media["samples_removed_total"] == 0
    assert media["clips_left_unchanged"] == 0
    # Durations equal the source within one 16 kHz sample -- the deliverable's own
    # falsifier, read back from the receipt.
    assert media["max_abs_duration_delta_seconds"] < media["one_sample_at_16k_seconds"]


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_no_row_ever_lost_audio(name: str) -> None:
    view = _view(name)
    tail = 2.0 if MOD.VARIANTS[name]["tail"] else 0.0
    for item in view["items"]:
        # Positive, so the standardization never truncates; below one sample, so it
        # never invents audio either.
        assert 0.0 <= item["duration_delta_seconds"] < 1.0 / 16000
        assert item["sample_rate_hz"] == 16000
        assert item["source_sample_rate_hz"] == 24000
        assert item["samples_removed"] == 0
        assert item["audio_seconds"] == pytest.approx(
            item["standardized_audio_seconds"] + tail, abs=1e-9
        )
        assert item["sample_id"].endswith("@" + MOD.VARIANTS[name]["id_suffix"])


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_receipt_records_a_model_free_build_that_did_run_librosa(name: str) -> None:
    contacts = _receipt(name)["contacts"]
    for key in (
        "frozen_core",
        "tokenizer",
        "embedder",
        "retriever",
        "scorer",
        "network",
        "gpu_hours",
        "paid_api_spend",
        "parent_container_decodes",
        "ffmpeg_calls",
        "outbound_connection_attempts",
    ):
        assert contacts[key] == 0, key
    # The honest half: this build DOES resample, so librosa ran.
    assert contacts["sealed_wav_decodes"] == 400
    assert contacts["librosa_calls"] == 2 * 400 + len(MOD.PROBE_FREQUENCIES_HZ)
    assert all(value == 0 for key, value in _receipt(name)["opened"].items() if key != "note")


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_receipt_pins_the_decoder(name: str) -> None:
    pins = _receipt(name)["decoder_pins"]
    assert pins["decoder"] == MOD.DECODER_QUALNAME
    assert pins["decoder_source_sha256"] == MOD.DECODER_SOURCE_SHA256
    assert pins["res_type"] == "soxr_hq"
    assert pins["librosa_version"] == MOD.PINNED_LIBROSA_VERSION
    assert pins["soxr_version"] == MOD.PINNED_SOXR_VERSION
    assert pins["ffmpeg_on_path"] is False


def test_only_the_tail_variant_pins_the_tail_rule() -> None:
    assert _receipt("16k")["tail_rule_implementation"] is None
    tail = _receipt("16k+ts2")["tail_rule_implementation"]
    assert tail["module"] == MOD.DEV_BUILDER_RELPATH
    assert tail["sha256"] == MOD.DEV_BUILDER_SHA256


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_the_corpus_band_energy_is_recorded_at_every_edge(name: str) -> None:
    bands = _receipt(name)["source_band_energy"]
    assert set(bands) == {f"above_{edge // 1000}k_share" for edge in MOD.BAND_EDGES_HZ}
    for summary in bands.values():
        assert summary["n"] == 400
        assert summary["min"] <= summary["median"] <= summary["max"]
    # The finding the preregistration signs its prediction from: almost nothing
    # above the 8 kHz output Nyquist.
    above_8k = bands["above_8k_share"]
    assert above_8k["median"] < 1e-5
    assert _receipt(name)["clips_above_share"]["above_8k_more_than_0.01"] == 1


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_probe_view_and_supplement_reproduce(name: str) -> None:
    receipt = _receipt(name)
    view_path = CHECKS / EXPECTED[name]["dir"] / "roster/flight-roster-receipt.json"
    assert (
        hashlib.sha256(view_path.read_bytes()).hexdigest()
        == receipt["outputs"]["probe_view_sha256"]
    )
    supplement_path = REPO / receipt["outputs"]["d1_media_supplement"]
    assert (
        hashlib.sha256(supplement_path.read_bytes()).hexdigest()
        == receipt["outputs"]["d1_media_supplement_sha256"]
    )
    view = json.loads(view_path.read_text(encoding="utf-8"))
    supplement = json.loads(supplement_path.read_text(encoding="utf-8"))
    assert supplement["schema"] == "saea-d1-media-supplement-v1"
    assert supplement["carrier_lock_key"] == "audio2tool"
    assert supplement["count"] == view["count"] == 400
    assert supplement["ids_sha256"] == view["ids_sha256"]
    assert supplement["source_binding_sha256"] == receipt["outputs"]["probe_view_sha256"]
    ids = [str(item["sample_id"]) for item in view["items"]]
    assert ids == sorted(ids)
    assert len(set(ids)) == 400
    assert (
        hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest() == view["ids_sha256"]
    )


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_media_paths_stay_inside_the_variant_root(name: str) -> None:
    root = str(MOD.VARIANTS[name]["subdir"])
    for item in _view(name)["items"]:
        assert str(item["media_relpath"]).startswith(root + "/")
        assert ".." not in str(item["media_relpath"])
        assert str(item["source_media_relpath"]).startswith("datasets/audio2tool/")


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_manifest_reproduces(name: str) -> None:
    for directory in (
        CHECKS / EXPECTED[name]["dir"],
        CHECKS / EXPECTED[name]["dir"] / "roster",
    ):
        lines = (directory / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
        recorded = {
            name_.lstrip("*"): digest for digest, name_ in (line.split() for line in lines)
        }
        present = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.iterdir()
            if path.is_file() and path.name != "MANIFEST.sha256"
        }
        assert recorded == present


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_roster_receipt_matches_the_build(name: str) -> None:
    receipt = _receipt(name)
    roster = json.loads(
        (REPO / receipt["outputs"]["roster_receipt"]).read_text(encoding="utf-8")
    )
    assert roster["split_identity_hash"] == receipt["split_identity_hash"]
    assert roster["roster_id"] == MOD.VARIANTS[name]["roster_id"]
    assert roster["split_role"] == "discovery"
    assert len(roster["items"]) == 400


def test_the_two_variants_have_different_identities_from_each_other_and_the_sealed_400() -> None:
    sealed = "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"
    identities = {_receipt(name)["split_identity_hash"] for name in EXPECTED}
    assert len(identities) == 2
    assert sealed not in identities
    for name in EXPECTED:
        assert _receipt(name)["comparator"]["split_identity_hash"] == sealed


def test_the_union_rebuild_price_is_scaled_from_this_build_and_carries_no_wall_time() -> None:
    price = _receipt("16k")["union_rebuild_price"]
    assert price["rows"] == 4000
    assert price["source_audio_seconds"] == pytest.approx(23418.083083)
    basis = price["measured_basis"]
    assert basis["rows"] == 400
    assert basis["scale"] == pytest.approx(
        price["source_audio_seconds"] / basis["source_audio_seconds"], rel=1e-9
    )
    assert price["projected_output_bytes"] == pytest.approx(
        basis["output_bytes"] * basis["scale"], rel=1e-6
    )
    # Wall time is not sealed anywhere in the receipt: it is not reproducible.
    assert "wall_seconds" not in json.dumps(_receipt("16k"))
