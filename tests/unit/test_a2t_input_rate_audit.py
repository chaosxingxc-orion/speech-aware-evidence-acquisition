"""Model-free coverage for the Audio2Tool input-rate audit.

Every assertion runs either on synthetic signals built in-process or on the
committed receipt the audit landed. No llama.cpp checkout is required, no
compiler is required, no data root is touched, and **no gold label, reference
transcript, evaluation query, tool name, sealed output or score is opened** --
the audit's own receipt carries resampler measurements on synthetic tones and
nothing else.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/run_a2t_input_rate_audit.py"
RECEIPT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-a2t-input-rate-audit"
)


def _module():
    spec = importlib.util.spec_from_file_location("a2t_input_rate_audit_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = _module()
SUMMARY = json.loads((RECEIPT_DIR / "summary.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The pure arithmetic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("freq", "expected"),
    [(100, "passband"), (7999, "passband"), (8000, "at_output_nyquist"), (8001, "stopband")],
)
def test_band_class_splits_at_the_output_nyquist(freq: int, expected: str) -> None:
    assert MOD.band_class(freq) == expected


@pytest.mark.parametrize(
    ("freq", "expected"),
    [(100, 100), (7500, 7500), (8000, 8000), (8100, 7900), (11000, 5000)],
)
def test_folded_frequency_mirrors_about_the_output_nyquist(freq: int, expected: int) -> None:
    assert MOD.folded_frequency(freq) == pytest.approx(expected)


def test_reference_dbfs_is_the_rms_of_the_probe_tone() -> None:
    # A 0.5-amplitude sine has RMS 0.5/sqrt(2) = 0.35355, i.e. -9.031 dBFS.
    assert MOD.reference_dbfs() == pytest.approx(-9.0309, abs=1e-3)


def test_spectrum_row_finds_a_clean_tone_at_its_own_frequency() -> None:
    numpy = pytest.importorskip("numpy")
    n = MOD.TARGET_RATE_HZ
    times = numpy.arange(n) / float(MOD.TARGET_RATE_HZ)
    vector = MOD.TONE_AMPLITUDE * 32767.0 * numpy.sin(2.0 * numpy.pi * 1000.0 * times)
    row = MOD.spectrum_row(vector, 1000.0)
    assert row["landed_at_hz"] == pytest.approx(1000.0)
    assert row["share_at_landing_bin"] > 0.999
    assert row["output_rms_dbfs"] == pytest.approx(MOD.reference_dbfs(), abs=1e-3)


def test_tone_wav_is_a_24k_mono_int16_wav_of_the_right_length() -> None:
    import io
    import wave

    payload = MOD.tone_wav(1000.0, 2400)
    with wave.open(io.BytesIO(payload), "rb") as handle:
        assert handle.getframerate() == MOD.SOURCE_RATE_HZ
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getnframes() == 2400


def test_length_probe_covers_every_residue_mod_three() -> None:
    # The residue is the ONLY thing that decides whether floor and ceil differ,
    # so a probe grid that misses one would not be able to see the truncation.
    assert {n % 3 for n in MOD.LENGTH_PROBE_SAMPLES} == {0, 1, 2}


# ---------------------------------------------------------------------------
# The committed receipt
# ---------------------------------------------------------------------------


def test_receipt_identity_and_scope() -> None:
    assert SUMMARY["schema"] == "saea-a2t-input-rate-audit-v1"
    assert SUMMARY["exposure_row"] == "SAEA-A2T-MF-INPUT-RATE-AUDIT-V1"
    assert SUMMARY["execution_profile"] == "model-free-check"
    assert SUMMARY["test_split_read"] is False
    assert SUMMARY["source_rate_hz"] == 24000
    assert SUMMARY["target_rate_hz"] == 16000


def test_receipt_records_no_contact_of_any_kind() -> None:
    contacts = SUMMARY["contacts"]
    for key in (
        "frozen_core",
        "tokenizer",
        "embedder",
        "retriever",
        "scorer",
        "network",
        "gpu_hours",
        "paid_api_spend",
        "llama_cpp_targets_built",
        "llama_cpp_binaries_executed",
        "llama_cpp_files_written",
        "dataset_media_files_opened",
        "outbound_connection_attempts",
    ):
        assert contacts[key] == 0, key
    assert all(value == 0 for key, value in SUMMARY["opened"].items() if key != "note")


def test_receipt_pins_the_sealed_build_and_a_clean_tree() -> None:
    pinned = SUMMARY["pinned_llama_cpp"]
    assert pinned["build_commit"] == MOD.BUILD_COMMIT
    assert pinned["working_tree"] == "clean"
    assert pinned["cited_sources"] == MOD.CITED_SOURCES


def test_the_length_rule_is_floor_for_llama_cpp_and_ceil_for_the_study() -> None:
    rule = SUMMARY["verdicts"]["output_length_rule"]
    assert rule["llama_cpp_always_floor_two_thirds"] is True
    assert rule["study_always_ceil_two_thirds"] is True
    # At most one 16 kHz sample, and the latent short-read zero pad did not fire.
    assert rule["llama_cpp_max_dropped_seconds"] < 1.0 / 16000
    assert rule["llama_cpp_short_read_zero_pad_observed"] is False
    for row in SUMMARY["length_probe"]["rows"]:
        assert row["llama_cpp_frame_count"] == row["floor_two_thirds"]
        assert row["study_soxr_hq_output_samples"] == row["ceil_two_thirds"]
        assert row["llama_cpp_frames_read"] == row["llama_cpp_frame_count"]


def test_miniaudio_droops_in_the_passband_and_aliases_above_it() -> None:
    """The two claims the audit note's headline makes, read back from the receipt."""

    mini = SUMMARY["verdicts"]["llama_cpp_miniaudio_linear"]
    soxr = SUMMARY["verdicts"]["study_soxr_hq"]
    # Passband: miniaudio loses several dB before the Nyquist, soxr essentially none
    # until its own transition band.
    assert mini["passband_worst_attenuation_db"] > 3.0
    assert mini["passband_min_share_at_own_frequency"] < 0.95
    assert soxr["passband_min_share_at_own_frequency"] > 0.99
    # Stopband: miniaudio folds an above-Nyquist tone back within ~6 dB of its input
    # level; soxr's worst leak is 80+ dB down.
    assert mini["stopband_worst_leakage_db_below_input"] < 10.0
    assert soxr["stopband_worst_leakage_db_below_input"] > 80.0


def test_the_seven_khz_row_is_the_one_the_note_quotes() -> None:
    rows = {int(row["frequency_hz"]): row for row in SUMMARY["tone_probe"]["rows"]}
    reference = SUMMARY["verdicts"]["reference_tone_dbfs"]
    seven = rows[7000]
    assert seven["band"] == "passband"
    mini_db = seven["llama_cpp_miniaudio_linear"]["output_rms_dbfs"]
    soxr_db = seven["study_soxr_hq"]["output_rms_dbfs"]
    assert reference - mini_db == pytest.approx(2.07, abs=0.05)
    assert reference - soxr_db == pytest.approx(0.0, abs=0.01)


def test_manifest_reproduces_over_the_landed_files() -> None:
    lines = (RECEIPT_DIR / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    recorded = {name.lstrip("*"): digest for digest, name in (line.split() for line in lines)}
    present = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in RECEIPT_DIR.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    }
    assert recorded == present


def test_tone_csv_carries_one_row_per_probed_frequency() -> None:
    text = (RECEIPT_DIR / "tone-response.csv").read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line]
    assert lines[0].startswith("frequency_hz,band,landed_at_hz,")
    assert len(lines) == 1 + len(MOD.TONE_FREQUENCIES_HZ)
    assert [int(line.split(",")[0]) for line in lines[1:]] == list(MOD.TONE_FREQUENCIES_HZ)
