"""Item E33: roster-table tests for the generalized SLURP packet preprocessing
driver (scripts/slurp_evo_fold_preprocess.py), covering the two sealed EVO-S1
TRAIN folds plus the new dev2000-added roster (SAEA-SN-DEV2000-ADDED-PREPROCESS).

Zero model / encoder / network / GPU contact: every test here either reads
committed config fragments through core.config.compose or exercises the
in-process packet-materialization conflict guard against a tmp_path packet
root. No real packet under /home/chao/feat-cache is ever touched.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "slurp_evo_fold_preprocess.py"

# The script's own module-level guards require these before it can even be
# imported (defense against running against a stale installed copy rather
# than this checkout's src/) -- set them here, non-destructively, following
# the exact pattern tests/unit/test_slurp_dev1000_ts2_preprocess.py already
# uses for its sibling driver.
_SRC = str(REPO / "src")
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing_pythonpath.split(":"):
    os.environ["PYTHONPATH"] = _SRC + (":" + _existing_pythonpath if _existing_pythonpath else "")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

_SPEC = importlib.util.spec_from_file_location("slurp_evo_fold_preprocess_e33", SCRIPT)
assert _SPEC and _SPEC.loader
module = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = module
_SPEC.loader.exec_module(module)

from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    FrozenCoreError,
    SpeechFeatureChunkData,
    materialize_speech_feature_packet,
)


def test_roster_table_has_exactly_the_registered_rosters() -> None:
    # The two sealed EVO-S1 folds, item E33's dev2000-added roster, the
    # Stage-3 S3-1 construction roster and its one recovery, owner decision 107's
    # devel-remainder expansion plus its 4-row np8 geometry-equivalence preflight, and
    # the final-report test-full roster (owner decisions 99 and 107), whose own coverage
    # lives in tests/unit/test_slurp_test_full_preprocess_roster.py, and the final-report
    # test-sample-3010 roster (owner decisions 151 and 156), covered by
    # tests/unit/test_slurp_test_sample_preparations.py. The union receipt
    # still covers the two folds only.
    assert set(module.PREPROCESS_ROSTERS) == {
        "fold-a", "fold-b", "dev2000-added", "stage3-construction-r01", "stage3-construction-r01-recovery",
        "devel-remainder", "devel-remainder-np8-equivalence-4", "test-full", "test-sample-3010",
    }
    assert module.FOLD_ROSTER_KEYS == ("fold-a", "fold-b")


def test_fold_rosters_carry_the_train_prefix_discovery_role_and_evo_run_id() -> None:
    for key, dataset, experiment in (
        ("fold-a", "slurp-speech-native-evo-fold-a-1080", "slurp-evo-fold-a-preprocess"),
        ("fold-b", "slurp-speech-native-evo-fold-b-1080", "slurp-evo-fold-b-preprocess"),
    ):
        spec = module.PREPROCESS_ROSTERS[key]
        assert spec.sample_id_prefix == "slurp:train:"
        assert spec.split_role == "discovery"
        assert spec.run_id == "SAEA-SLURP-EVO-FOLD-PACKETS-V2"
        assert spec.dataset_fragment == dataset
        assert spec.experiment_fragment == experiment
        # The fold experiment fragments already carry their own
        # promotion_receipt key, so the roster table names no default here.
        assert spec.promotion_receipt_name is None


def test_dev2000_added_roster_carries_the_devel_prefix_dev_role_and_own_run_id() -> None:
    spec = module.PREPROCESS_ROSTERS["dev2000-added"]
    assert spec.sample_id_prefix == "slurp:devel:"
    assert spec.split_role == "dev"
    assert spec.run_id == "SAEA-SN-DEV2000-ADDED-PREPROCESS"
    assert spec.dataset_fragment == "slurp-speech-native-dev2000-added"
    assert spec.experiment_fragment == "slurp-dev2000-added-preprocess"
    assert spec.promotion_receipt_name == "DEV-2000-ADDED-promotion.json"
    assert spec.default_attempt_id == "attempt-packets-dev2000-added-v1"
    assert (spec.plan_calls, spec.plan_speech_seconds, spec.plan_gpu_hours) == (1000, 2984, 1.0)


@pytest.mark.parametrize("letter,expected_key", [("a", "fold-a"), ("b", "fold-b")])
def test_fold_alias_maps_to_the_matching_roster_key(letter: str, expected_key: str) -> None:
    # --fold a / --fold b is the deprecated CLI alias for
    # --roster fold-a / --roster fold-b; main() builds this exact string.
    roster_key = "fold-%s" % letter
    assert roster_key == expected_key
    assert roster_key in module.PREPROCESS_ROSTERS


def test_fold_and_roster_are_mutually_exclusive_on_the_cli() -> None:
    with pytest.raises(SystemExit):
        module.main(["--fold", "a", "--roster", "fold-b", "--preflight-only"])


def test_missing_roster_and_fold_is_refused_for_preflight() -> None:
    with pytest.raises(SystemExit):
        module.main(["--preflight-only"])


def test_dev2000_added_runtime_view_items_all_carry_the_devel_prefix_and_count_1000() -> None:
    spec = module.PREPROCESS_ROSTERS["dev2000-added"]
    values = module.compose(
        module.REPO, module.MODEL_FRAGMENT, spec.dataset_fragment,
        module.BASELINE_FRAGMENT, spec.experiment_fragment,
    ).values
    items = values["items"]
    assert len(items) == 1000
    assert int(values["count"]) == 1000
    assert values.get("split_role") == "dev"
    for item in items:
        assert str(item["sample_id"]).startswith("slurp:devel:")


def test_promotion_receipt_resolves_under_the_default_feature_root_when_config_lacks_one() -> None:
    spec = module.PREPROCESS_ROSTERS["dev2000-added"]
    resolved = module._resolve_promotion_receipt({}, spec, module.DEFAULT_FEATURE_ROOT, "dev2000-added")
    assert resolved == module.DEFAULT_FEATURE_ROOT / "DEV-2000-ADDED-promotion.json"


def test_promotion_receipt_prefers_an_explicit_config_value_over_the_roster_default() -> None:
    spec = module.PREPROCESS_ROSTERS["fold-a"]
    values = {"promotion_receipt": "/some/explicit/path.json"}
    resolved = module._resolve_promotion_receipt(values, spec, module.DEFAULT_FEATURE_ROOT, "fold-a")
    assert resolved == Path("/some/explicit/path.json")


def test_promotion_receipt_refuses_a_roster_with_neither_a_config_value_nor_a_default_name() -> None:
    bare = module.RosterSpec(
        run_id="X", dataset_fragment="d", experiment_fragment="e",
        sample_id_prefix="slurp:devel:", split_role="dev",
        promotion_receipt_name=None, default_attempt_id="attempt-x",
        plan_calls=1, plan_speech_seconds=1, plan_gpu_hours=0.0,
    )
    with pytest.raises(SystemExit):
        module._resolve_promotion_receipt({}, bare, module.DEFAULT_FEATURE_ROOT, "bare")


def _chunk(byte_value: int) -> SpeechFeatureChunkData:
    return SpeechFeatureChunkData(
        n_tokens=1, n_pos=1, n_embd=2,
        feature_bytes=bytes([byte_value]) * 8,
        position_bytes=b"\x00" * 16,
    )


def test_packet_promotion_is_additive_and_refuses_a_conflicting_byte_mismatch(tmp_path: Path) -> None:
    """The ADDITIVE / refuse-on-conflict property the E33 registration requires
    is already guaranteed by core.model.speech_features.
    materialize_speech_feature_packet, not by anything this driver adds: an
    identical replay of an already-promoted packet id is accepted
    (idempotent), and a byte mismatch against an already-promoted packet id
    raises before anything is written. This exercises that guarantee directly
    against a temporary packet root; no real /home/chao/feat-cache byte is
    ever read or written."""

    feature_root = tmp_path / "packets"
    common = dict(
        feature_root=feature_root, packet_id="slurp/devel/000017/audio-1",
        audio_sha256="a" * 64, encoder_receipt_sha256="b" * 64,
        decoder_gguf_sha256="c" * 64, mmproj_sha256="d" * 64,
        position_mode="mrope_1d", causal_attention=True,
    )
    first = materialize_speech_feature_packet(chunks=(_chunk(0x11),), **common)
    directory = feature_root / "slurp" / "devel" / "000017" / "audio-1"
    assert directory.is_dir()

    # Additive replay: identical bytes for the same packet id is accepted and
    # returns the same, unchanged, already-served packet.
    replay = materialize_speech_feature_packet(chunks=(_chunk(0x11),), **common)
    assert replay.packet_sha256 == first.packet_sha256

    # Conflict: a different byte for the SAME packet id raises before writing
    # anything, and the already-served packet is left untouched.
    before = (directory / "chunks" / "0000.f32").read_bytes()
    with pytest.raises(FrozenCoreError):
        materialize_speech_feature_packet(chunks=(_chunk(0x22),), **common)
    after = (directory / "chunks" / "0000.f32").read_bytes()
    assert after == before


def test_packet_promotion_conflict_guard_also_catches_a_different_source_identity(
    tmp_path: Path,
) -> None:
    feature_root = tmp_path / "packets"
    common = dict(
        feature_root=feature_root, packet_id="slurp/devel/000024/audio-2",
        encoder_receipt_sha256="b" * 64,
        decoder_gguf_sha256="c" * 64, mmproj_sha256="d" * 64,
        position_mode="mrope_1d", causal_attention=True,
    )
    materialize_speech_feature_packet(chunks=(_chunk(0x33),), audio_sha256="a" * 64, **common)
    with pytest.raises(FrozenCoreError):
        # Same packet id, same bytes, DIFFERENT declared audio_sha256 -- the
        # source identity disagrees with what is already served.
        materialize_speech_feature_packet(chunks=(_chunk(0x33),), audio_sha256="e" * 64, **common)
