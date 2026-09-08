"""Row selection and ceiling-constant tests for the SLURP @ts2 packet-promotion runner."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "slurp_dev1000_ts2_preprocess.py"

# The script's own module-level guards require these before it can even be
# imported (defense against running against a stale installed copy rather
# than this checkout's src/) -- set them here, non-destructively, rather than
# depending on the invoking shell to have exported them already.
_SRC = str(REPO / "src")
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing_pythonpath.split(":"):
    os.environ["PYTHONPATH"] = _SRC + (":" + _existing_pythonpath if _existing_pythonpath else "")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

_SPEC = importlib.util.spec_from_file_location("slurp_dev1000_ts2_preprocess", SCRIPT)
assert _SPEC and _SPEC.loader
module = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = module
_SPEC.loader.exec_module(module)


def test_plan_speech_seconds_ceiling_is_the_recovery_registered_value() -> None:
    # The 2026-09-08 recovery re-registration raised docs/exposure-ledger.md's
    # SAEA-SN-DEV1000-TS2-PREPROCESS-V1 row from 4905 to 4908 speech-audio
    # seconds, admitting exactly the one row a durable duplicate gate encode
    # left short. The adapter's cumulative budget check compares against the
    # ATTEMPT's own declared plan value, not the ledger cell directly, so this
    # constant must track the ledger's registered cell exactly.
    assert module.PLAN_SPEECH_SECONDS_CEILING == 4908
    assert module.PLAN_CALLS_CEILING == 1004
    assert module.PLAN_GPU_HOURS_CEILING == 0.1


def _write_audio(root: Path, relpath: str, payload: bytes) -> tuple[str, str]:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return relpath, hashlib.sha256(payload).hexdigest()


def _runtime_view(items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": "saea-speech-native-runtime-view-v1",
        "split_role": "dev",
        "count": len(items),
        "items": items,
    }


def test_gate_sample_ids_select_exactly_the_membership_subset(tmp_path: Path) -> None:
    gate_ids = sorted(module.GATE_SAMPLE_IDS)
    items = []
    for index, sample_id in enumerate(gate_ids):
        relpath, digest = _write_audio(tmp_path, f"gate-{index}.flac", f"gate-audio-{index}".encode())
        items.append({
            "sample_id": sample_id, "media_relpath": relpath, "audio_sha256": digest,
            "audio_seconds": 1.5 + index,
        })
    # Two rows OUTSIDE the gate's 4 -- the full split the gate is a membership
    # subset of always carries far more than just the 4 selected rows.
    for index in range(2):
        relpath, digest = _write_audio(
            tmp_path, f"other-{index}.flac", f"other-audio-{index}".encode())
        items.append({
            "sample_id": f"slurp:devel:999{index:03d}:audio-0@ts2",
            "media_relpath": relpath, "audio_sha256": digest, "audio_seconds": 9.0,
        })

    values = _runtime_view(items)
    samples = module.roster_samples(
        values, tmp_path, workers=2, select_ids=module.GATE_SAMPLE_IDS)

    assert [sample.sample_id for sample in samples] == gate_ids
    assert len(samples) == len(module.GATE_SAMPLE_IDS)


def test_selecting_an_id_outside_the_split_fails_closed(tmp_path: Path) -> None:
    relpath, digest = _write_audio(tmp_path, "known.flac", b"known-audio")
    values = _runtime_view([{
        "sample_id": "slurp:devel:000011:audio-1497266596@ts2",
        "media_relpath": relpath, "audio_sha256": digest, "audio_seconds": 2.0,
    }])
    with pytest.raises(SystemExit, match="not members of this split"):
        module.roster_samples(
            values, tmp_path, workers=1,
            select_ids=frozenset({"slurp:devel:999999:audio-0@ts2"}))


def test_full_split_without_select_ids_requires_the_declared_count_to_match(
    tmp_path: Path,
) -> None:
    relpath, digest = _write_audio(tmp_path, "one.flac", b"one-audio")
    values = _runtime_view([{
        "sample_id": "slurp:devel:000011:audio-1497266596@ts2",
        "media_relpath": relpath, "audio_sha256": digest, "audio_seconds": 2.0,
    }])
    values["count"] = 2  # disagrees with the single real item
    with pytest.raises(SystemExit, match="count disagrees"):
        module.roster_samples(values, tmp_path, workers=1, select_ids=None)
