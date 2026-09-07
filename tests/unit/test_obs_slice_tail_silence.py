"""``obs_slice_tail_silence_seconds``: the Earnings-21 obs knob and its oracle.

Section 6.3 of ``docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-
preregistration.md``: Earnings-21's 90-second windows are cut at RUNTIME by
``reproduction.obs_loop``; nothing in the harness consumes pre-cut slices, so
the ``@ts2`` cell needs ONE named, thin knob on the already-registered
``obs-agent-loop`` policy rather than a dataset fragment. Default ``0.0`` is
today's bytes; ``2.0`` appends 32,000 zero samples at 16 kHz to every window
AFTER the buffered cut and before the request.

The committed ``@ts2`` media is that knob's BYTE-EXACT ORACLE, which is why it
was built for a carrier that could not yet use it:
:func:`test_the_knob_reproduces_every_committed_ts2_window_hash` runs the
knob's own encoder over all 1,593 SEALED window slices the direct baseline
wrote and requires 1,593 of 1,593 SHA-256s to equal the ones
``docs/receipts/artifacts/d1-e21-buf90-1593-tail2s.json`` already records. A
runtime change that would otherwise be unverifiable becomes an identity check.

That test SKIPS (never softens) when ``$SPEECHRL_DATA_DIR`` or the sealed
slices are absent; everything else here is pure and runs anywhere.
"""

from __future__ import annotations

import hashlib
import json
import wave
from array import array
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.reproduction.obs_audio import (
    SLICE_TAIL_SILENCE_TRANSFORM,
    append_tail_silence,
    encode_slice,
    tail_silence_samples,
    write_wav_bytes,
)
from speech_aware_evidence_acquisition.reproduction.obs_loop import (
    ObsLoopConfig,
    ObsLoopError,
)

from test_obs_loop_policy import (  # noqa: E402
    SAMPLE_ID,
    _World,
    _fixed_mode_skip_values,
    _noise,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
E21_TS2_ROSTER = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-07-e21-buf90-tail2s-media"
    / "roster/flight-roster-receipt.json"
)
E21_TS2_SUPPLEMENT = REPO_ROOT / "docs/receipts/artifacts/d1-e21-buf90-1593-tail2s.json"


# ---------------------------------------------------------------------------
# 1. The rule: exactly 2.0 s, in seconds, against the file's own rate
# ---------------------------------------------------------------------------


def test_two_seconds_at_16k_is_32000_samples_and_the_rate_is_read_not_assumed() -> None:
    assert tail_silence_samples(16000, 2.0) == 32000
    # The same rule at the Audio2Tool release's rate; stating the tail in
    # SECONDS is what keeps 2.0 s two seconds on a 24 kHz carrier.
    assert tail_silence_samples(24000, 2.0) == 48000
    assert tail_silence_samples(16000, 0.0) == 0


def test_a_tail_that_is_not_a_whole_number_of_samples_is_refused() -> None:
    with pytest.raises(ValueError, match="whole number of samples"):
        tail_silence_samples(16000, 0.0000001)
    with pytest.raises(ValueError):
        tail_silence_samples(0, 2.0)
    with pytest.raises(ValueError):
        tail_silence_samples(16000, -1.0)


def test_the_tail_is_strictly_additive() -> None:
    samples = array("h", [0, 1, -1, 32767, -32768, 7, -7])
    produced = append_tail_silence(samples, 16000, 2.0)
    assert len(produced) == len(samples) + 32000
    assert produced[: len(samples)] == samples
    assert not any(produced[len(samples) :])
    # Zero seconds is the identity.
    assert append_tail_silence(samples, 16000, 0.0) == samples


# ---------------------------------------------------------------------------
# 2. encode_slice: the one encoder, and its default is today's bytes
# ---------------------------------------------------------------------------


def test_the_default_encoder_is_byte_identical_to_the_historical_path() -> None:
    samples = _noise(1.0)
    raw, transforms, pre_sha256 = encode_slice(samples, 16000)
    assert raw == write_wav_bytes(samples, 16000)
    assert transforms == ()
    assert pre_sha256 is None


def test_the_tail_declares_itself_and_chains_to_the_raw_cut() -> None:
    samples = _noise(1.0)
    raw, transforms, pre_sha256 = encode_slice(samples, 16000, tail_silence_seconds=2.0)
    assert raw == write_wav_bytes(append_tail_silence(samples, 16000, 2.0), 16000)
    assert transforms == (f"{SLICE_TAIL_SILENCE_TRANSFORM}-2s",)
    # pre_sha256 is the RAW cut -- the bytes the sealed comparator sent.
    assert pre_sha256 == hashlib.sha256(write_wav_bytes(samples, 16000)).hexdigest()


def test_rms_norm_runs_first_and_the_pre_hash_stays_the_raw_cut() -> None:
    samples = _noise(1.0)
    raw, transforms, pre_sha256 = encode_slice(
        samples,
        16000,
        preprocess=("rms-norm",),
        rms_target_dbfs=-20.0,
        tail_silence_seconds=2.0,
    )
    plain, _, plain_pre = encode_slice(
        samples, 16000, preprocess=("rms-norm",), rms_target_dbfs=-20.0
    )
    assert transforms == ("rms-norm", f"{SLICE_TAIL_SILENCE_TRANSFORM}-2s")
    assert pre_sha256 == plain_pre
    assert len(raw) == len(plain) + 2 * 32000


# ---------------------------------------------------------------------------
# 3. The config knob
# ---------------------------------------------------------------------------


def test_the_knob_defaults_to_zero(tmp_path) -> None:
    assert ObsLoopConfig.from_values(_fixed_mode_skip_values(), tmp_path).slice_tail_silence_seconds == 0.0


def test_the_knob_parses_and_refuses_bad_values(tmp_path) -> None:
    config = ObsLoopConfig.from_values(
        _fixed_mode_skip_values(obs_slice_tail_silence_seconds=2.0), tmp_path
    )
    assert config.slice_tail_silence_seconds == 2.0
    with pytest.raises(ObsLoopError, match="must be >= 0"):
        ObsLoopConfig.from_values(
            _fixed_mode_skip_values(obs_slice_tail_silence_seconds=-1.0), tmp_path
        )
    with pytest.raises(ObsLoopError, match="finite number"):
        ObsLoopConfig.from_values(
            _fixed_mode_skip_values(obs_slice_tail_silence_seconds="2.0"), tmp_path
        )
    with pytest.raises(ValueError, match="whole number of samples"):
        ObsLoopConfig.from_values(
            _fixed_mode_skip_values(obs_slice_tail_silence_seconds=0.0000001), tmp_path
        )


def test_the_knob_is_a_known_key_so_a_typo_still_fails_closed(tmp_path) -> None:
    with pytest.raises(ObsLoopError, match="unknown obs-loop config keys"):
        ObsLoopConfig.from_values(
            _fixed_mode_skip_values(obs_slice_tail_silence_second=2.0), tmp_path
        )


# ---------------------------------------------------------------------------
# 4. End to end through BOTH executor paths of the registered policy
# ---------------------------------------------------------------------------


def _slice_facts(world):
    facts = []
    for payload in world.adapter.payloads:
        relpath = payload["media_relpath"]
        record = world.registry.lookup(SAMPLE_ID, relpath)
        facts.append((record, (world.data_root / relpath).read_bytes()))
    return facts


@pytest.mark.parametrize("batch_slices", [1, 4], ids=["sequential", "parallel"])
def test_the_knob_appends_the_tail_after_the_cut_on_both_executor_paths(
    tmp_path, monkeypatch, batch_slices
) -> None:
    """Same windows, same spans, same cursor -- only the delivered bytes grow.

    This is the property the pairing depends on: if the tail moved the cut,
    window k+1 would start 2 s later and the cell would no longer be paired
    row for row against the sealed comparator.
    """

    pcm = _noise(100.0)
    plain = _World(
        tmp_path / "plain",
        monkeypatch,
        pcm=pcm,
        texts=["span one", "span two", "span three"],
        values=_fixed_mode_skip_values(obs_batch_slices=batch_slices),
    )
    plain.run()
    tailed = _World(
        tmp_path / "tailed",
        monkeypatch,
        pcm=pcm,
        texts=["span one", "span two", "span three"],
        values=_fixed_mode_skip_values(
            obs_batch_slices=batch_slices, obs_slice_tail_silence_seconds=2.0
        ),
    )
    tailed.run()

    plain_facts = _slice_facts(plain)
    tailed_facts = _slice_facts(tailed)
    assert len(tailed_facts) == len(plain_facts) >= 2

    for (plain_record, plain_bytes), (tailed_record, tailed_bytes) in zip(
        plain_facts, tailed_facts
    ):
        # The cut is identical: same span, same metered seconds, same order.
        assert tailed_record.start_seconds == plain_record.start_seconds
        assert tailed_record.end_seconds == plain_record.end_seconds
        assert tailed_record.audio_seconds == plain_record.audio_seconds
        assert tailed_record.iteration == plain_record.iteration
        # The delivered bytes are the cut plus exactly 2.0 s of silence.
        assert tailed_bytes == write_wav_bytes(
            append_tail_silence(
                array("h", plain_bytes[44:]), plain_record.sample_rate_hz, 2.0
            ),
            plain_record.sample_rate_hz,
        )
        assert tailed_record.bytes == len(tailed_bytes) == plain_record.bytes + 2 * 32000
        assert tailed_record.sha256 == hashlib.sha256(tailed_bytes).hexdigest()
        # The record says what was done, and chains to the sealed cut.
        assert tailed_record.preprocess == (f"{SLICE_TAIL_SILENCE_TRANSFORM}-2s",)
        assert tailed_record.pre_sha256 == plain_record.sha256


def test_the_default_run_is_byte_identical_to_the_historical_path(
    tmp_path, monkeypatch
) -> None:
    """The knob's default must move nothing at all -- every sealed Earnings
    run's window bytes, hashes and derivation records depend on it."""

    pcm = _noise(100.0)
    before = _World(
        tmp_path / "a",
        monkeypatch,
        pcm=pcm,
        texts=["one", "two", "three"],
        values=_fixed_mode_skip_values(),
    )
    before.run()
    after = _World(
        tmp_path / "b",
        monkeypatch,
        pcm=pcm,
        texts=["one", "two", "three"],
        values=_fixed_mode_skip_values(obs_slice_tail_silence_seconds=0.0),
    )
    after.run()
    for (record_a, bytes_a), (record_b, bytes_b) in zip(
        _slice_facts(before), _slice_facts(after)
    ):
        assert bytes_a == bytes_b
        assert record_a.preprocess == record_b.preprocess == ()
        assert record_a.pre_sha256 is record_b.pre_sha256 is None
        assert record_a.sha256 == record_b.sha256


# ---------------------------------------------------------------------------
# 5. THE FALSIFIER: 1,593 of 1,593 committed @ts2 window hashes
# ---------------------------------------------------------------------------


def _data_root() -> Path:
    from speech_aware_evidence_acquisition.data.lock import data_root

    try:
        return data_root()
    except Exception as error:  # noqa: BLE001 -- environment, not behaviour
        pytest.skip(f"$SPEECHRL_DATA_DIR is not resolvable here: {error}")


def _read_wav_16k_mono(path: Path) -> array:
    with wave.open(str(path), "rb") as handle:
        assert (handle.getframerate(), handle.getnchannels(), handle.getsampwidth()) == (
            16000,
            1,
            2,
        ), f"{path} is not 16 kHz mono int16"
        return array("h", handle.readframes(handle.getnframes()))


def test_the_knob_reproduces_every_committed_ts2_window_hash() -> None:
    """The oracle, all 1,593 windows, no sampling.

    Each committed ``@ts2`` window was built by appending 2.0 s to the SEALED
    90-second slice that ``SAEA-E21-FULL44-DIRECT-BASELINE-V2`` itself wrote.
    Feeding that same sealed slice through the knob's own encoder must
    reproduce the committed SHA-256 exactly -- and ``pre_sha256`` must equal
    the sealed slice's own hash, which is the chain back to the comparator's
    bytes.
    """

    receipt = json.loads(E21_TS2_ROSTER.read_text(encoding="utf-8"))
    supplement = json.loads(E21_TS2_SUPPLEMENT.read_text(encoding="utf-8"))
    items = receipt["items"]
    assert len(items) == 1593
    committed = {str(entry["id"]): str(entry["sha256"]) for entry in supplement["manifest"]}
    assert len(committed) == 1593

    root = _data_root()
    first = root / str(items[0]["source_media_relpath"])
    if not first.is_file():
        pytest.skip(
            "the sealed SAEA-E21-FULL44-DIRECT-BASELINE-V2 obs-slices are absent on "
            f"this machine ({first})"
        )

    matched = 0
    mismatched: list[str] = []
    for item in items:
        sealed = _read_wav_16k_mono(root / str(item["source_media_relpath"]))
        raw, transforms, pre_sha256 = encode_slice(
            sealed, 16000, preprocess=(), tail_silence_seconds=2.0
        )
        sample_id = str(item["sample_id"])
        if (
            hashlib.sha256(raw).hexdigest() == str(item["audio_sha256"])
            == committed[sample_id]
            and pre_sha256 == str(item["source_audio_sha256"])
            and transforms == (f"{SLICE_TAIL_SILENCE_TRANSFORM}-2s",)
            and len(raw) == int(item["bytes"])
        ):
            matched += 1
        else:
            mismatched.append(sample_id)

    assert mismatched == []
    assert matched == 1593
