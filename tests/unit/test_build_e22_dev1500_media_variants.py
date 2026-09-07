"""Model-free coverage for the three Earnings-22 dev1500 probe media variants.

Every assertion runs on synthetic segments and synthetic WAV bytes under
``tmp_path``, or on the committed receipts the build landed. No data root, no
parent MP3, no model, network, tokenizer or scorer contact.
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
SCRIPT = REPO / "scripts/build_e22_dev1500_media_variants.py"
CHECK_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-e22-dev1500-encoding-variants"
)


def _module():
    spec = importlib.util.spec_from_file_location("e22_media_variants_test", SCRIPT)
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


# ---------------------------------------------------------------------------
# The boundary-exact rule
# ---------------------------------------------------------------------------


def _segments(spans: list[tuple[float, float]], call: str = "c1") -> dict:
    return {
        f"{call}-{index}": {"source_id": call, "start_ts": start, "end_ts": end}
        for index, (start, end) in enumerate(spans)
    }


def test_the_midpoint_rule_splits_an_overlap_and_leaves_a_gap_alone():
    segments = _segments([(0.0, 2.0), (1.8, 4.0), (5.0, 6.0)])
    spans, props = MOD.boundary_exact_spans(segments)
    # pair 0/1 overlaps by 0.2 s -> both move to the midpoint 1.9
    assert spans["c1-0"] == (0.0, 1.9)
    assert spans["c1-1"][0] == pytest.approx(1.9)
    # pair 1/2 is separated by 1.0 s -> neither boundary moves
    assert spans["c1-1"][1] == pytest.approx(4.0)
    assert spans["c1-2"] == (5.0, 6.0)
    assert props["overlapping_pairs_before"] == 1
    assert props["overlapping_pairs_after"] == 0
    assert props["positive_gaps_closed"] == 0


def test_the_first_and_last_outer_boundaries_never_move():
    segments = _segments([(1.0, 3.0), (2.5, 5.0), (4.0, 7.0)])
    spans, _ = MOD.boundary_exact_spans(segments)
    assert spans["c1-0"][0] == 1.0
    assert spans["c1-2"][1] == 7.0


def test_the_recut_is_strictly_subtractive():
    segments = _segments([(0.0, 2.0), (1.5, 4.0), (3.0, 6.0)])
    spans, _ = MOD.boundary_exact_spans(segments)
    for index, (start, end) in enumerate([(0.0, 2.0), (1.5, 4.0), (3.0, 6.0)]):
        new_start, new_end = spans[f"c1-{index}"]
        assert new_start >= start
        assert new_end <= end
        assert new_end > new_start


def test_calls_are_independent():
    segments = {**_segments([(0.0, 2.0), (1.8, 4.0)], "a"), **_segments([(0.0, 9.0)], "b")}
    spans, props = MOD.boundary_exact_spans(segments)
    assert props["calls"] == 2
    assert spans["b-0"] == (0.0, 9.0)


def test_an_out_of_order_call_is_refused():
    segments = {
        "c1-0": {"source_id": "c1", "start_ts": 5.0, "end_ts": 6.0},
        "c1-1": {"source_id": "c1", "start_ts": 1.0, "end_ts": 2.0},
    }
    with pytest.raises(MOD.BuildError):
        MOD.boundary_exact_spans(segments)


def test_the_slice_offsets_reproduce_a_recut_of_the_parent():
    item = {
        "sample_id": "c1-1",
        "segment_start_seconds": 1.0,
        "segment_end_seconds": 3.0,
    }
    clip_len = 32000  # 2.0 s
    first, last = MOD.boundary_exact_slice(item, (1.25, 2.5), clip_len)
    assert first == 4000  # round(1.25*16000) - round(1.0*16000)
    assert last == 24000  # round(2.5*16000) - round(1.0*16000)


def test_a_slice_that_is_not_subtractive_is_refused():
    item = {
        "sample_id": "c1-1",
        "segment_start_seconds": 1.0,
        "segment_end_seconds": 3.0,
    }
    with pytest.raises(MOD.BuildError):
        MOD.boundary_exact_slice(item, (0.5, 3.0), 32000)
    with pytest.raises(MOD.BuildError):
        MOD.boundary_exact_slice(item, (1.0, 3.5), 32000)


def test_a_clamped_clip_keeps_its_clamp():
    # The sealed clip is shorter than end-start because the parent ran out;
    # the slice must clamp to the clip, never past it.
    item = {
        "sample_id": "c1-9",
        "segment_start_seconds": 1.0,
        "segment_end_seconds": 3.0,
    }
    clip_len = 20000  # 1.25 s, clamped
    first, last = MOD.boundary_exact_slice(item, (1.0, 2.9), clip_len)
    assert (first, last) == (0, clip_len)


# ---------------------------------------------------------------------------
# The two additive variants
# ---------------------------------------------------------------------------


def test_tail_silence_appends_exactly_two_seconds_of_zeros():
    samples = array("h", [1, -1, 2, -2])
    out = MOD.transform("tail-silence-2s", samples, {}, None)
    assert len(out) == 4 + 32000
    assert list(out[:4]) == [1, -1, 2, -2]
    assert set(out[4:]) == {0}


def test_pad30_pads_short_clips_and_leaves_long_ones_alone():
    short = array("h", [3] * 16000)
    out = MOD.transform("pad-30s", short, {}, None)
    assert len(out) == 480000
    assert set(out[16000:]) == {0}
    exactly = array("h", [3] * 480000)
    assert MOD.transform("pad-30s", exactly, {}, None) is exactly
    longer = array("h", [3] * 500000)
    assert len(MOD.transform("pad-30s", longer, {}, None)) == 500000


def test_an_unknown_variant_fails_closed():
    with pytest.raises(MOD.BuildError):
        MOD.transform("nope", array("h", [0]), {}, None)


def test_read_clip_refuses_a_container_that_is_not_16k_mono(tmp_path):
    path = tmp_path / "stereo.wav"
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(array("h", [0, 0, 0, 0]).tobytes())
    with pytest.raises(MOD.BuildError):
        MOD.read_clip(path)


def test_read_clip_round_trips_int16(tmp_path):
    path = tmp_path / "clip.wav"
    _wav(path, [0, 32767, -32768, 5])
    assert list(MOD.read_clip(path)) == [0, 32767, -32768, 5]


# ---------------------------------------------------------------------------
# The landed receipts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant", sorted(MOD.VARIANTS))
def test_the_landed_build_receipt_is_internally_consistent(variant):
    receipt = json.loads(
        (CHECK_DIR / variant / "build-receipt.json").read_text(encoding="utf-8")
    )
    view = json.loads(
        (CHECK_DIR / variant / "roster/flight-roster-receipt.json").read_text(
            encoding="utf-8"
        )
    )
    spec = MOD.VARIANTS[variant]
    assert receipt["variant"] == variant
    assert receipt["count"] == 1500 == view["count"]
    assert receipt["split_role"] == "dev"
    assert receipt["test_split_read"] is False
    assert sorted(receipt["strata_counts"].values()) == [150] * 10
    assert receipt["contacts"]["frozen_core"] == 0
    assert receipt["contacts"]["parent_mp3_decodes"] == 0
    assert receipt["opened"]["reference_sentences"] == 0
    assert receipt["opened"]["hypothesis_text"] == 0
    # Every id carries the variant suffix and none collides with dev-v1's.
    ids = [str(item["sample_id"]) for item in view["items"]]
    assert all(sample_id.endswith("@" + spec["suffix"]) for sample_id in ids)
    assert ids == sorted(ids)
    assert len(set(ids)) == 1500
    # The media root is the variant's own and nothing points back at dev-v1.
    assert all(
        str(item["media_relpath"]).startswith(spec["subdir"] + "/") for item in view["items"]
    )
    # The probe view digest the supplement binds to is the one on disk.
    supplement = json.loads(
        (REPO / spec["supplement"]).read_text(encoding="utf-8")
    )
    view_bytes = (
        REPO / receipt["outputs"]["probe_view"]
    ).read_bytes()
    assert supplement["source_binding_sha256"] == hashlib.sha256(view_bytes).hexdigest()
    assert supplement["count"] == 1500
    assert supplement["schema"] == "saea-d1-media-supplement-v1"
    assert set(supplement) == {
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


def test_the_landed_recut_reproduces_the_committed_clip_boundary_audit():
    receipt = json.loads(
        (CHECK_DIR / "boundary-exact/build-receipt.json").read_text(encoding="utf-8")
    )
    props = receipt["recut_properties"]
    # The 2026-09-06 clip-boundary audit measured 4,681 overlapping adjacent
    # pairs over 6,028 pairs in ten calls; the re-cut must remove all of them
    # and close none of the 1,324 positive gaps.
    assert props["calls"] == 10
    assert props["segments"] == 6038
    assert props["overlapping_pairs_before"] == 4681
    assert props["overlapping_pairs_after"] == 0
    assert props["positive_gaps_closed"] == 0
    assert receipt["measured_media"]["samples_added_total"] == 0
    assert receipt["measured_media"]["samples_removed_total"] > 0


def test_the_three_variants_have_distinct_split_identities():
    identities = {
        variant: json.loads(
            (CHECK_DIR / variant / "build-receipt.json").read_text(encoding="utf-8")
        )["split_identity_hash"]
        for variant in MOD.VARIANTS
    }
    assert len(set(identities.values())) == 3
    dev1500 = "c626e62f8876bf52a2904a0d2ec91807a530f3195c10facc8c036f661b2bf88a"
    assert dev1500 not in set(identities.values())
