"""Owner decision 107: the devel-remainder preprocess roster, the -np 8 sidecar
fragment pair, the ``--workers`` fit refusal and the 4-row geometry-equivalence
preflight (scripts/slurp_evo_fold_preprocess.py).

Zero model / encoder / network / GPU contact: every test reads a committed
config fragment through core.config.compose, exercises a pure helper of the
driver, or drives the packet/legacy-cache comparison against a tmp_path feature
root. No real packet under /home/chao/feat-cache is written, no sidecar is
started and no media file of the governed release is decoded.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import struct
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "slurp_evo_fold_preprocess.py"

# The script's own module-level guards require these before it can be imported
# (defense against a stale installed copy) -- set non-destructively, exactly as
# tests/unit/test_e33_preprocess_rosters.py already does for the same driver.
_SRC = str(REPO / "src")
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing_pythonpath.split(":"):
    os.environ["PYTHONPATH"] = _SRC + (":" + _existing_pythonpath if _existing_pythonpath else "")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

_SPEC = importlib.util.spec_from_file_location("slurp_evo_fold_preprocess_devrem", SCRIPT)
assert _SPEC and _SPEC.loader
module = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = module
_SPEC.loader.exec_module(module)

from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    SpeechFeatureChunkData,
    materialize_speech_feature_packet,
)


def _compose(key: str):
    spec = module.PREPROCESS_ROSTERS[key]
    return module.compose(
        module.REPO, spec.sidecar_fragment, spec.dataset_fragment,
        module.BASELINE_FRAGMENT, spec.experiment_fragment,
    )


# ------------------------------------------------------------ roster table


def test_devel_remainder_spec_is_the_registered_one() -> None:
    spec = module.PREPROCESS_ROSTERS["devel-remainder"]
    assert spec.run_id == "SAEA-SN-DEVEL-REMAINDER-PREPROCESS"
    assert spec.dataset_fragment == "slurp-speech-native-devel-remainder-v2"
    assert spec.experiment_fragment == "slurp-devel-remainder-preprocess-v2"
    assert spec.sample_id_prefix == "slurp:devel:"
    assert spec.split_role == "dev"
    assert spec.promotion_receipt_name == "DEVEL-REMAINDER-promotion.json"
    assert spec.default_attempt_id == "attempt-packets-devel-remainder-v1"
    # V2 of the roster (provisional decision 109 carved out the 120 reserved
    # recordings); the run id and the attempt are unchanged, no contact was made
    # under them.
    assert (spec.plan_calls, spec.plan_speech_seconds, spec.plan_gpu_hours) == (6570, 18612, 1.0)
    assert spec.sidecar_fragment == module.MODEL_FRAGMENT_NP8
    assert spec.equivalence is None


def test_np8_equivalence_spec_promotes_nothing_and_names_the_scratch_geometry() -> None:
    spec = module.PREPROCESS_ROSTERS["devel-remainder-np8-equivalence-4"]
    assert spec.run_id == "SAEA-SN-DEVEL-REMAINDER-NP8-EQUIVALENCE-4-V1"
    assert spec.promotion_receipt_name is None
    assert (spec.plan_calls, spec.plan_speech_seconds) == (4, 12)
    assert spec.sidecar_fragment == module.MODEL_FRAGMENT_NP8_SCRATCH
    assert spec.equivalence is not None
    assert spec.equivalence.reference_feature_root == module.DEFAULT_FEATURE_ROOT
    assert spec.equivalence.reference_promotion_receipt == "DEV-2000-ADDED-promotion.json"
    assert spec.equivalence.reference_geometry_slots == 4


def test_every_sealed_roster_keeps_the_np4_sidecar_fragment() -> None:
    for key in ("fold-a", "fold-b", "dev2000-added", "stage3-construction-r01",
                "stage3-construction-r01-recovery"):
        spec = module.PREPROCESS_ROSTERS[key]
        assert spec.sidecar_fragment == module.MODEL_FRAGMENT
        assert spec.equivalence is None


# ------------------------------------------------------- the two geometries


def test_np8_fragment_is_the_np4_fragment_with_one_value_changed() -> None:
    np4 = json.loads(
        (REPO / "configs/model/q4km-preprocess-featcache-cpu-sidecar.json").read_text("utf-8")
    )
    np8 = json.loads(
        (REPO / "configs/model/q4km-preprocess-featcache-cpu-sidecar-np8.json").read_text("utf-8")
    )
    assert set(np4) == set(np8)
    for key in np4:
        if key != "server_args":
            assert np4[key] == np8[key], key
    assert np4["server_args"][np4["server_args"].index("-np") + 1] == "4"
    assert np8["server_args"][np8["server_args"].index("-np") + 1] == "8"
    assert [t for t in np4["server_args"] if t != "4"] == [
        t for t in np8["server_args"] if t != "8"
    ]


def test_scratch_fragment_differs_from_np8_only_in_its_feature_cache_directory() -> None:
    np8 = json.loads(
        (REPO / "configs/model/q4km-preprocess-featcache-cpu-sidecar-np8.json").read_text("utf-8")
    )
    scratch = json.loads(
        (REPO / "configs/model/q4km-preprocess-featcache-cpu-sidecar-np8-scratch.json").read_text(
            "utf-8"
        )
    )
    assert set(np8) == set(scratch)
    for key in np8:
        if key != "server_env":
            assert np8[key] == scratch[key], key
    assert np8["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"] == str(module.DEFAULT_LEGACY_CACHE_DIR)
    assert Path(
        scratch["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"]
    ) != module.DEFAULT_LEGACY_CACHE_DIR


# ------------------------------------------------------------ server slots


def test_server_slots_reads_np_out_of_the_composed_fragment() -> None:
    assert module._server_slots(_compose("devel-remainder").values, "np8") == 8
    assert module._server_slots(_compose("dev2000-added").values, "np4") == 4


@pytest.mark.parametrize(
    "server_args",
    [(), ("-c", "16384"), ("-np",), ("-np", "zero"), ("-np", "0")],
)
def test_server_slots_refuses_a_fragment_that_does_not_declare_a_usable_np(server_args) -> None:
    with pytest.raises(SystemExit):
        module._server_slots({"server_args": server_args}, "synthetic")


def test_worker_fit_refuses_more_workers_than_slots_and_accepts_fewer() -> None:
    module._assert_worker_fit(4, 4, "roster", "fragment")
    module._assert_worker_fit(1, 8, "roster", "fragment")
    with pytest.raises(SystemExit) as error:
        module._assert_worker_fit(9, 8, "roster", "fragment")
    assert "exceeds the 8 slots" in str(error.value)


def test_cli_refuses_nine_workers_on_the_eight_slot_geometry() -> None:
    with pytest.raises(SystemExit) as error:
        module.main(["--roster", "devel-remainder", "--preflight-only", "--workers", "9"])
    assert "exceeds the 8 slots" in str(error.value)


# ------------------------------------------------- equivalence isolation


def _equivalence_values(**overrides):
    values = dict(_compose("devel-remainder-np8-equivalence-4").values)
    values.update(overrides)
    return values


def test_equivalence_isolation_accepts_the_committed_configuration() -> None:
    spec = module.PREPROCESS_ROSTERS["devel-remainder-np8-equivalence-4"]
    values = _equivalence_values()
    packet_root = Path(str(values["feature_root"]))
    legacy_cache = Path(str(values["legacy_cache_dir"]))
    assert packet_root != module.DEFAULT_FEATURE_ROOT
    assert legacy_cache != module.DEFAULT_LEGACY_CACHE_DIR
    module._assert_equivalence_isolation(
        values, spec, "devel-remainder-np8-equivalence-4", packet_root, legacy_cache
    )


def test_equivalence_isolation_refuses_the_resident_legacy_cache() -> None:
    spec = module.PREPROCESS_ROSTERS["devel-remainder-np8-equivalence-4"]
    values = _equivalence_values(
        server_env={"LLAMA_MTMD_FEAT_CACHE_DIR": str(module.DEFAULT_LEGACY_CACHE_DIR)}
    )
    with pytest.raises(SystemExit) as error:
        module._assert_equivalence_isolation(
            values, spec, "equiv", Path("/tmp/scratch-packets"), module.DEFAULT_LEGACY_CACHE_DIR
        )
    assert "SCRATCH legacy cache" in str(error.value)


def test_equivalence_isolation_refuses_the_resident_packet_root() -> None:
    spec = module.PREPROCESS_ROSTERS["devel-remainder-np8-equivalence-4"]
    values = _equivalence_values()
    with pytest.raises(SystemExit) as error:
        module._assert_equivalence_isolation(
            values, spec, "equiv", module.DEFAULT_FEATURE_ROOT,
            Path(str(values["legacy_cache_dir"])),
        )
    assert "resident packet root" in str(error.value)


def test_equivalence_isolation_refuses_a_promotion_receipt_key() -> None:
    spec = module.PREPROCESS_ROSTERS["devel-remainder-np8-equivalence-4"]
    values = _equivalence_values(promotion_receipt="/home/chao/feat-cache/x-promotion.json")
    with pytest.raises(SystemExit) as error:
        module._assert_equivalence_isolation(
            values, spec, "equiv", Path(str(values["feature_root"])),
            Path(str(values["legacy_cache_dir"])),
        )
    assert "promotes nothing" in str(error.value)


def test_equivalence_isolation_refuses_a_sidecar_writing_somewhere_else() -> None:
    spec = module.PREPROCESS_ROSTERS["devel-remainder-np8-equivalence-4"]
    values = _equivalence_values(
        server_env={"LLAMA_MTMD_FEAT_CACHE_DIR": "/home/chao/feat-cache/somewhere-else"}
    )
    with pytest.raises(SystemExit) as error:
        module._assert_equivalence_isolation(
            values, spec, "equiv", Path(str(values["feature_root"])),
            Path(str(values["legacy_cache_dir"])),
        )
    assert "empty directory" in str(error.value)


def test_promote_only_is_refused_for_a_geometry_equivalence_roster() -> None:
    with pytest.raises(SystemExit) as error:
        module.main(
            ["--roster", "devel-remainder-np8-equivalence-4", "--promote-only",
             "--attempt-id", "attempt-x"]
        )
    assert "promotes nothing" in str(error.value)


def test_a_geometry_equivalence_roster_resolves_no_promotion_receipt() -> None:
    spec = module.PREPROCESS_ROSTERS["devel-remainder-np8-equivalence-4"]
    with pytest.raises(SystemExit):
        module._resolve_promotion_receipt(
            {}, spec, module.DEFAULT_FEATURE_ROOT, "devel-remainder-np8-equivalence-4"
        )


# ------------------------------------------------ the comparison itself


class _Sample:
    """The two fields _compare_row_against_resident_packet reads off a sample."""

    def __init__(self, sample_id: str, media_relpath: str, audio_seconds: float, sha: str):
        self.sample_id = sample_id
        self.media_relpath = media_relpath
        self.audio_seconds = audio_seconds
        self.audio_ref = type("_Ref", (), {"sha256": sha})()


def _write_feat(cache_dir: Path, key: str, ordinal: int, n_tokens: int, n_embd: int, fill: int):
    payload = bytes([fill]) * (n_tokens * n_embd * 4)
    raw = struct.pack("<QQ", n_tokens, n_embd) + payload
    (cache_dir / f"{key}_o{ordinal}.feat").write_bytes(raw)
    return payload


def _fixture(tmp_path: Path, monkeypatch, *, scratch_fill: int, resident_fill: int):
    from speech_aware_evidence_acquisition.core.model.speech_features import (
        legacy_audio_feature_cache_key,
    )

    root = tmp_path / "data"
    (root / "slurp").mkdir(parents=True)
    media_relpath = "slurp/audio-equivalence.flac"
    (root / media_relpath).write_bytes(b"not really audio, only hashed")
    key = legacy_audio_feature_cache_key((root / media_relpath).read_bytes())

    scratch = tmp_path / "scratch-cache"
    scratch.mkdir()
    payload = _write_feat(scratch, key, 0, 2, 2, scratch_fill)

    resident_cache = tmp_path / "resident-cache"
    resident_cache.mkdir()
    _write_feat(resident_cache, key, 0, 2, 2, resident_fill)
    monkeypatch.setattr(module, "DEFAULT_LEGACY_CACHE_DIR", resident_cache)

    reference_root = tmp_path / "resident-packets"
    sample_id = "slurp:devel:000001:audio-equivalence"
    materialize_speech_feature_packet(
        feature_root=reference_root,
        packet_id=sample_id.replace(":", "/"),
        audio_sha256="a" * 64,
        encoder_receipt_sha256="b" * 64,
        decoder_gguf_sha256="c" * 64,
        mmproj_sha256="d" * 64,
        position_mode="mrope_1d",
        causal_attention=True,
        chunks=(
            SpeechFeatureChunkData(
                n_tokens=2, n_pos=2, n_embd=2,
                feature_bytes=bytes([resident_fill]) * 16,
                position_bytes=struct.pack("<8i", 0, 1, 0, 1, 0, 1, 0, 1),
            ),
        ),
    )
    sample = _Sample(sample_id, media_relpath, 1.5, "a" * 64)
    return sample, root, scratch, reference_root, payload


def test_comparison_reports_identical_features_as_equivalent(tmp_path, monkeypatch) -> None:
    sample, root, scratch, reference_root, payload = _fixture(
        tmp_path, monkeypatch, scratch_fill=0x11, resident_fill=0x11
    )
    row = module._compare_row_against_resident_packet(
        sample=sample, root=root, legacy_cache=scratch, reference_root=reference_root
    )
    assert row["feature_payload_identical_to_resident_packet"] is True
    assert row["legacy_cache_file_identical_to_resident_cache"] is True
    assert row["resident_legacy_cache_still_warm"] is True
    assert row["scratch_chunks"][0]["feature_payload_sha256"] == hashlib.sha256(payload).hexdigest()
    assert row["resident_packet"]["chunks"][0]["feature_sha256"] == (
        row["scratch_chunks"][0]["feature_payload_sha256"]
    )


def test_comparison_reports_a_single_differing_byte_as_not_equivalent(tmp_path, monkeypatch) -> None:
    sample, root, scratch, reference_root, _ = _fixture(
        tmp_path, monkeypatch, scratch_fill=0x22, resident_fill=0x11
    )
    row = module._compare_row_against_resident_packet(
        sample=sample, root=root, legacy_cache=scratch, reference_root=reference_root
    )
    assert row["feature_payload_identical_to_resident_packet"] is False
    assert row["legacy_cache_file_identical_to_resident_cache"] is False


def test_comparison_refuses_a_scratch_cache_the_encode_never_filled(tmp_path, monkeypatch) -> None:
    sample, root, _scratch, reference_root, _ = _fixture(
        tmp_path, monkeypatch, scratch_fill=0x11, resident_fill=0x11
    )
    empty = tmp_path / "empty-scratch"
    empty.mkdir()
    with pytest.raises(SystemExit) as error:
        module._compare_row_against_resident_packet(
            sample=sample, root=root, legacy_cache=empty, reference_root=reference_root
        )
    assert "no entry" in str(error.value)


# ------------------------------------------------ the composed fragments


def test_composed_devel_remainder_config_binds_6570_devel_rows_on_eight_slots() -> None:
    values = _compose("devel-remainder").values
    assert values["experiment_id"] == "SAEA-SN-DEVEL-REMAINDER-PREPROCESS"
    assert values["execution_profile"] == "bounded-discovery-probe"
    assert values["split_role"] == "dev"
    assert int(values["count"]) == 6570
    assert float(values["audio_seconds_total"]) == pytest.approx(18611.584875)
    assert values["split_identity_hash"] == (
        "f8af142bec49755d70364b665b31e3963972084fb73a568c9921f53b41fd341a"
    )
    assert module._server_slots(values, "np8") == 8
    assert values["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"] == str(
        module.DEFAULT_LEGACY_CACHE_DIR
    )
    assert "feature_root" not in values  # promotes into the resident root, additively
    assert all(str(item["sample_id"]).startswith("slurp:devel:") for item in values["items"])


def test_composed_equivalence_config_binds_four_scratch_rows() -> None:
    values = _compose("devel-remainder-np8-equivalence-4").values
    assert values["experiment_id"] == "SAEA-SN-DEVEL-REMAINDER-NP8-EQUIVALENCE-4-V1"
    assert int(values["count"]) == 4
    assert module._server_slots(values, "scratch") == 8
    assert Path(str(values["legacy_cache_dir"])) != module.DEFAULT_LEGACY_CACHE_DIR
    assert Path(str(values["feature_root"])) != module.DEFAULT_FEATURE_ROOT
    assert "promotion_receipt" not in values
