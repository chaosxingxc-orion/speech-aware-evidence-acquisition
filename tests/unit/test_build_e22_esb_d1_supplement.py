"""Model-free D1 successor coverage for the ESB Earnings-22 utterance roster.

The point of these tests is the PARENT CHAIN. A derived utterance is media D1
never saw, so the only thing that keeps it inside D1's identity closure is that
its parent call is one of the six the owner allowed AND carries exactly the
bytes D1 itself recorded. Each refusal below is one link of that chain.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import wave
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/build_e22_esb_d1_supplement.py"
CARRIER_SUBDIR = "datasets/earnings21-22/earnings22"
DERIVED_SUBDIR = "derived/e22-esb-utterances/v1"
ESB_TEST_CALLS = ("4432298", "4450488", "4470290", "4479741", "4483338", "4485244")


def _module():
    spec = importlib.util.spec_from_file_location("e22_esb_d1_supplement_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_wav(path: Path, *, frames: int, rate: int = 16000) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\0\0" * frames)
    return path.read_bytes()


def _scaffold(tmp_path: Path) -> tuple[Path, Path, Path, list[dict[str, object]]]:
    """``(data_root, roster_path, parent_d1_path, items)`` for a minimal roster
    that covers all six ESB calls with one utterance each."""

    data_root = tmp_path / "data"
    parent_manifest = []
    items: list[dict[str, object]] = []
    for index, call in enumerate(ESB_TEST_CALLS):
        parent = data_root / CARRIER_SUBDIR / "media" / f"{call}.mp3"
        parent.parent.mkdir(parents=True, exist_ok=True)
        parent.write_bytes(b"parent-%s" % call.encode())
        parent_sha = hashlib.sha256(parent.read_bytes()).hexdigest()
        parent_manifest.append(
            {"id": call, "bytes": parent.stat().st_size, "sha256": parent_sha}
        )
        frames = 1600 * (index + 1)
        relpath = f"{DERIVED_SUBDIR}/{call}/{call}-0.wav"
        payload = _write_wav(data_root / relpath, frames=frames)
        items.append(
            {
                "sample_id": f"{call}-0",
                "parent_sample_id": call,
                "parent_media_relpath": f"{CARRIER_SUBDIR}/media/{call}.mp3",
                "parent_sha256": parent_sha,
                "parent_decoded_seconds": 100.0,
                "media_relpath": relpath,
                "audio_sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "audio_seconds": round(frames / 16000, 9),
                "sample_rate_hz": 16000,
                "segment_start_seconds": 0.0,
                "segment_end_seconds": frames / 16000,
                "end_clamped_to_decoded_parent": False,
            }
        )
    roster_path = tmp_path / "roster.json"
    roster_path.write_text(
        json.dumps(
            {
                "schema": "saea-e22-esb-utterance-roster-receipt-v1",
                "carrier": "earnings22-original",
                "split_role": "dev",
                "count": len(items),
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    parent_d1 = tmp_path / "d1-identity.json"
    parent_d1.write_text(
        json.dumps(
            {
                "carriers": {
                    "earnings22-original": {"layers": {"media": {"manifest": parent_manifest}}}
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return data_root, roster_path, parent_d1, items


def _rewrite_roster(roster_path: Path, mutate) -> None:
    document = json.loads(roster_path.read_text(encoding="utf-8"))
    mutate(document)
    roster_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_builder_emits_an_exact_hash_bound_supplement(tmp_path: Path) -> None:
    module = _module()
    data_root, roster_path, parent_d1, items = _scaffold(tmp_path)
    supplement = module.build_supplement(
        roster_path=roster_path, data_root=data_root, parent_d1_path=parent_d1
    )
    assert supplement["schema"] == "saea-d1-media-supplement-v1"
    assert supplement["carrier_lock_key"] == "earnings22-original"
    assert supplement["count"] == len(items)
    assert [entry["id"] for entry in supplement["manifest"]] == sorted(
        item["sample_id"] for item in items
    )
    assert all(entry["roles"] == ["query"] for entry in supplement["manifest"])
    assert supplement["total_bytes"] == sum(int(item["bytes"]) for item in items)
    assert supplement["parent_d1_sha256"] == hashlib.sha256(parent_d1.read_bytes()).hexdigest()
    assert supplement["source_binding_sha256"] == hashlib.sha256(
        roster_path.read_bytes()
    ).hexdigest()
    canonical = json.dumps(
        supplement["manifest"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert supplement["manifest_sha256"] == hashlib.sha256(canonical).hexdigest()


def test_builder_refuses_a_parent_outside_the_six_allowed_calls(tmp_path: Path) -> None:
    module = _module()
    data_root, roster_path, parent_d1, _items = _scaffold(tmp_path)
    _rewrite_roster(roster_path, lambda doc: doc["items"][0].update({"parent_sample_id": "4420696"}))
    with pytest.raises(ValueError, match="this profile does not pin"):
        module.build_supplement(
            roster_path=roster_path, data_root=data_root, parent_d1_path=parent_d1
        )


def test_builder_refuses_a_parent_whose_bytes_disagree_with_d1(tmp_path: Path) -> None:
    module = _module()
    data_root, roster_path, parent_d1, _items = _scaffold(tmp_path)
    _rewrite_roster(roster_path, lambda doc: doc["items"][0].update({"parent_sha256": "0" * 64}))
    with pytest.raises(ValueError, match="disagrees with D1"):
        module.build_supplement(
            roster_path=roster_path, data_root=data_root, parent_d1_path=parent_d1
        )


def test_builder_refuses_derived_audio_whose_bytes_moved(tmp_path: Path) -> None:
    module = _module()
    data_root, roster_path, parent_d1, items = _scaffold(tmp_path)
    _write_wav(data_root / str(items[0]["media_relpath"]), frames=1601)
    with pytest.raises(ValueError, match="audio hash drift"):
        module.build_supplement(
            roster_path=roster_path, data_root=data_root, parent_d1_path=parent_d1
        )


def test_builder_refuses_a_duration_the_wav_header_does_not_support(tmp_path: Path) -> None:
    module = _module()
    data_root, roster_path, parent_d1, _items = _scaffold(tmp_path)
    _rewrite_roster(roster_path, lambda doc: doc["items"][0].update({"audio_seconds": 99.0}))
    with pytest.raises(ValueError, match="audio duration drift"):
        module.build_supplement(
            roster_path=roster_path, data_root=data_root, parent_d1_path=parent_d1
        )


def test_builder_refuses_a_roster_that_does_not_cover_all_six_calls(tmp_path: Path) -> None:
    module = _module()
    data_root, roster_path, parent_d1, _items = _scaffold(tmp_path)

    def drop_one(document):
        document["items"] = document["items"][:-1]
        document["count"] = len(document["items"])

    _rewrite_roster(roster_path, drop_one)
    with pytest.raises(ValueError, match=r"not this profile's 6 calls"):
        module.build_supplement(
            roster_path=roster_path, data_root=data_root, parent_d1_path=parent_d1
        )


def test_builder_refuses_an_id_that_collides_with_a_parent_call(tmp_path: Path) -> None:
    module = _module()
    data_root, roster_path, parent_d1, items = _scaffold(tmp_path)
    collision = ESB_TEST_CALLS[0]
    relpath = f"{DERIVED_SUBDIR}/{collision}/{collision}.wav"
    payload = _write_wav(data_root / relpath, frames=1600)

    def collide(document):
        document["items"][0].update(
            {
                "sample_id": collision,
                "media_relpath": relpath,
                "audio_sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "audio_seconds": 0.1,
            }
        )

    _rewrite_roster(roster_path, collide)
    with pytest.raises(ValueError, match="already exists in the immutable D1"):
        module.build_supplement(
            roster_path=roster_path, data_root=data_root, parent_d1_path=parent_d1
        )


def test_builder_refuses_a_media_path_escaping_the_data_root(tmp_path: Path) -> None:
    module = _module()
    data_root, roster_path, parent_d1, _items = _scaffold(tmp_path)
    _rewrite_roster(
        roster_path, lambda doc: doc["items"][0].update({"media_relpath": "../outside.wav"})
    )
    with pytest.raises(ValueError, match="escapes the data root"):
        module.build_supplement(
            roster_path=roster_path, data_root=data_root, parent_d1_path=parent_d1
        )


def test_builder_refuses_a_foreign_roster_schema(tmp_path: Path) -> None:
    module = _module()
    data_root, roster_path, parent_d1, _items = _scaffold(tmp_path)
    _rewrite_roster(roster_path, lambda doc: doc.update({"schema": "something-else-v1"}))
    with pytest.raises(ValueError, match="roster identity or split role is invalid"):
        module.build_supplement(
            roster_path=roster_path, data_root=data_root, parent_d1_path=parent_d1
        )


def test_builder_refuses_a_test_split_role(tmp_path: Path) -> None:
    module = _module()
    data_root, roster_path, parent_d1, _items = _scaffold(tmp_path)
    _rewrite_roster(roster_path, lambda doc: doc.update({"split_role": "test"}))
    with pytest.raises(ValueError, match="roster identity or split role is invalid"):
        module.build_supplement(
            roster_path=roster_path, data_root=data_root, parent_d1_path=parent_d1
        )
