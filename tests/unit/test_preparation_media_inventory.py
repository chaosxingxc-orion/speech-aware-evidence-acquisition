import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.preparation import PreparationError, digest
from speech_aware_evidence_acquisition.core.preparation_encoding import (
    encode_window_feature_cache,
)
from speech_aware_evidence_acquisition.core.preparation_media_inventory import (
    SOURCE_MEDIA_FEATURE_INVENTORY_SCHEMA,
    build_slurp_train_recalled_media_feature_inventory,
    build_source_media_feature_inventory,
    prepare_slurp_train_recalled_media_feature_inventory,
)

SHA = "a" * 64
IDENTITY = {
    "runtime_receipt_sha256": "b" * 64,
    "build_commit": "c" * 40,
    "decoder_gguf_sha256": "d" * 64,
    "mmproj_sha256": "e" * 64,
}


def _roster(tmp_path, media_bytes=b"synthetic train audio"):
    data = tmp_path / "data"
    media = data / "datasets" / "slurp" / "slurp_real" / "train.flac"
    media.parent.mkdir(parents=True)
    media.write_bytes(media_bytes)
    entry = {
        "candidate_facet_id": "facet:content:1",
        "source_sample_id": "slurp:train:000001:train",
        "media_relpath": "datasets/slurp/slurp_real/train.flac",
        "audio_sha256": hashlib.sha256(media_bytes).hexdigest(),
        "audio_bytes": len(media_bytes),
        "utterance_id": "1",
    }
    readiness_entries = [
        {
            "candidate_facet_id": entry["candidate_facet_id"],
            "deterministic_selected_source": {
                "sample_id": entry["source_sample_id"],
                "media_relpath": entry["media_relpath"],
            },
            "utterance_id": entry["utterance_id"],
        }
    ]
    readiness = tmp_path / "readiness.json"
    readiness.write_text(
        json.dumps(
            {
                "schema": "saea-slurp-train-candidate-media-readiness-v1",
                "source_to_media_inventory": {
                    "entries": readiness_entries,
                    "entry_canonical_sha256": digest(readiness_entries),
                },
            }
        ),
        encoding="utf-8",
    )
    roster = {
        "schema": "saea-slurp-train-recalled-candidate-preparation-roster-v1",
        "source_readiness": {
            "path": str(readiness),
            "sha256": hashlib.sha256(readiness.read_bytes()).hexdigest(),
            "entry_canonical_sha256": digest(readiness_entries),
        },
        "roster_count": 1,
        "entries": [entry],
    }
    path = tmp_path / "roster.json"
    path.write_text(json.dumps(roster), encoding="utf-8")
    return data, path, entry


def test_builds_source_bound_media_inventory(tmp_path):
    data, roster, entry = _roster(tmp_path)
    inventory = build_slurp_train_recalled_media_feature_inventory(
        roster_path=roster,
        expected_roster_sha256=hashlib.sha256(roster.read_bytes()).hexdigest(),
        data_root=data,
        encoder_identity=IDENTITY,
    )
    assert inventory["schema"] == SOURCE_MEDIA_FEATURE_INVENTORY_SCHEMA
    assert inventory["source_kind"] == "registered-media"
    assert inventory["encoding_inputs"] == [
        {
            "audio_sha256": entry["audio_sha256"],
            "source_sample_id": entry["source_sample_id"],
        }
    ]
    assert inventory["sources"][0]["media_relpath"] == entry["media_relpath"]


def test_media_inventory_refuses_changed_source_bytes(tmp_path):
    data, roster, _ = _roster(tmp_path)
    (data / "datasets" / "slurp" / "slurp_real" / "train.flac").write_bytes(b"changed")
    with pytest.raises(PreparationError, match="bytes differ"):
        build_slurp_train_recalled_media_feature_inventory(
            roster_path=roster,
            expected_roster_sha256=hashlib.sha256(roster.read_bytes()).hexdigest(),
            data_root=data,
            encoder_identity=IDENTITY,
        )


@dataclass
class _Timing:
    request_id: str


class _Client:
    def __init__(self):
        self.complete_calls = []
        self.timings = []
        self.closed = 0

    def register_slice(self, _record):
        raise AssertionError("registered media must not be forged as an OBS slice")

    def complete(self, messages, *, decoding_params):
        self.complete_calls.append((messages, decoding_params))
        self.timings.append(_Timing("encoder-request-1"))

    def close(self):
        self.closed += 1
        return {
            "trace_manifest_hash": "b" * 64,
            "cost": {"calls_used": len(self.timings)},
        }


def _inspection(media):
    from speech_aware_evidence_acquisition.core.preparation_encoding import (
        legacy_audio_feature_cache_key,
    )

    return type(
        "Inspection",
        (),
        {
            "audio_sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
            "cache_key": legacy_audio_feature_cache_key(media.read_bytes()),
            "chunks": (),
        },
    )()


def _encoding_kwargs(tmp_path, inventory, data, client):
    cache = tmp_path / "cache"
    cache.mkdir()
    return {
        "inventory": inventory,
        "data_root": data,
        "client": client,
        "custody_guard": lambda: None,
        "encoder_identity": IDENTITY,
        "legacy_cache_dir": cache,
        "expected_n_embd": 4,
        "output_path": tmp_path / "encoded.json",
        "run_id": "run",
        "attempt_id": "attempt",
        "session_id": "session",
        "runtime_receipt_file_sha256": SHA,
        "runtime_receipt_document_sha256": SHA,
        "session_receipt_file_sha256": SHA,
        "decoding_params": {"temperature": 0, "max_tokens": 1},
    }


def test_registered_media_warm_hit_uses_zero_contacts(tmp_path, monkeypatch):
    data, roster, entry = _roster(tmp_path)
    inventory = build_slurp_train_recalled_media_feature_inventory(
        roster_path=roster,
        expected_roster_sha256=hashlib.sha256(roster.read_bytes()).hexdigest(),
        data_root=data,
        encoder_identity=IDENTITY,
    )
    client = _Client()
    args = _encoding_kwargs(tmp_path, inventory, data, client)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache",
        lambda *, audio_path, **_: _inspection(audio_path),
    )
    media = data / entry["media_relpath"]
    from speech_aware_evidence_acquisition.core.preparation_encoding import (
        legacy_audio_feature_cache_key,
    )

    key = legacy_audio_feature_cache_key(media.read_bytes())
    (args["legacy_cache_dir"] / f"{key}_o0.feat").write_bytes(b"existing")
    args["warm_provenance"] = {
        entry["audio_sha256"]: {
            "audio_sha256": entry["audio_sha256"],
            "cache_key": key,
            "encoder_identity": IDENTITY,
            "source_contact_id": "prior-contact",
            "source_provenance_receipt_sha256": SHA,
        }
    }
    encode_window_feature_cache(**args)
    assert client.complete_calls == [] and client.closed == 1


def test_registered_media_cold_miss_sends_raw_media_without_slice_registration(
    tmp_path, monkeypatch
):
    data, roster, entry = _roster(tmp_path)
    inventory = build_slurp_train_recalled_media_feature_inventory(
        roster_path=roster,
        expected_roster_sha256=hashlib.sha256(roster.read_bytes()).hexdigest(),
        data_root=data,
        encoder_identity=IDENTITY,
    )
    client = _Client()
    args = _encoding_kwargs(tmp_path, inventory, data, client)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache",
        lambda *, audio_path, **_: _inspection(audio_path),
    )
    encode_window_feature_cache(**args)
    assert len(client.complete_calls) == 1
    assert client.complete_calls[0][0][1]["content"] == [
        {"type": "input_audio", "media_relpath": entry["media_relpath"]}
    ]
    assert client.closed == 1


def test_registered_media_union_of_warm_hit_and_cold_miss_contacts_only_cold_input(
    tmp_path, monkeypatch
):
    data = tmp_path / "data"
    first = data / "datasets" / "slurp" / "slurp_real" / "first.flac"
    second = data / "datasets" / "slurp" / "slurp_real" / "second.flac"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"first synthetic train audio")
    second.write_bytes(b"second synthetic train audio")
    entries = []
    for index, media in enumerate((first, second), start=1):
        content = media.read_bytes()
        entries.append(
            {
                "candidate_facet_id": f"facet:content:{index}",
                "source_sample_id": f"slurp:train:{index:06d}:{media.stem}",
                "media_relpath": str(media.relative_to(data)),
                "audio_sha256": hashlib.sha256(content).hexdigest(),
                "audio_bytes": len(content),
                "utterance_id": str(index),
            }
        )
    readiness_entries = [
        {
            "candidate_facet_id": entry["candidate_facet_id"],
            "deterministic_selected_source": {
                "sample_id": entry["source_sample_id"],
                "media_relpath": entry["media_relpath"],
            },
            "utterance_id": entry["utterance_id"],
        }
        for entry in entries
    ]
    readiness = tmp_path / "readiness.json"
    readiness.write_text(
        json.dumps(
            {
                "schema": "saea-slurp-train-candidate-media-readiness-v1",
                "source_to_media_inventory": {
                    "entries": readiness_entries,
                    "entry_canonical_sha256": digest(readiness_entries),
                },
            }
        ),
        encoding="utf-8",
    )
    roster = tmp_path / "roster.json"
    roster.write_text(
        json.dumps(
            {
                "schema": "saea-slurp-train-recalled-candidate-preparation-roster-v1",
                "source_readiness": {
                    "path": str(readiness),
                    "sha256": hashlib.sha256(readiness.read_bytes()).hexdigest(),
                    "entry_canonical_sha256": digest(readiness_entries),
                },
                "roster_count": 2,
                "entries": entries,
            }
        ),
        encoding="utf-8",
    )
    inventory = build_slurp_train_recalled_media_feature_inventory(
        roster_path=roster,
        expected_roster_sha256=hashlib.sha256(roster.read_bytes()).hexdigest(),
        data_root=data,
        encoder_identity=IDENTITY,
    )
    client = _Client()
    args = _encoding_kwargs(tmp_path, inventory, data, client)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache",
        lambda *, audio_path, **_: _inspection(audio_path),
    )
    from speech_aware_evidence_acquisition.core.preparation_encoding import (
        legacy_audio_feature_cache_key,
    )

    first_key = legacy_audio_feature_cache_key(first.read_bytes())
    (args["legacy_cache_dir"] / f"{first_key}_o0.feat").write_bytes(b"warm")
    args["warm_provenance"] = {
        entries[0]["audio_sha256"]: {
            "audio_sha256": entries[0]["audio_sha256"],
            "cache_key": first_key,
            "encoder_identity": IDENTITY,
            "source_contact_id": "prior-contact",
            "source_provenance_receipt_sha256": SHA,
        }
    }
    encode_window_feature_cache(**args)
    assert len(client.complete_calls) == 1
    assert client.complete_calls[0][0][1]["content"] == [
        {"type": "input_audio", "media_relpath": entries[1]["media_relpath"]}
    ]
    assert client.closed == 1


def test_persists_source_media_inventory_through_shared_artifact_rail(tmp_path):
    data, roster, _ = _roster(tmp_path)
    output = tmp_path / "inventory.json"
    result = prepare_slurp_train_recalled_media_feature_inventory(
        output,
        roster_path=roster,
        expected_roster_sha256=hashlib.sha256(roster.read_bytes()).hexdigest(),
        data_root=data,
        encoder_identity=IDENTITY,
    )
    document = json.loads(output.read_text(encoding="utf-8"))
    assert result["contact_class"] == "model-free"
    assert document["kind"] == "source-media-feature-inventory-v1"
    assert document["output"]["schema"] == SOURCE_MEDIA_FEATURE_INVENTORY_SCHEMA


def test_generic_inventory_carries_declared_non_slurp_authority(tmp_path):
    data = tmp_path / "data"
    media = data / "other" / "sample.wav"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"generic source")
    inventory = build_source_media_feature_inventory(
        sources=[
            {
                "sample_id": "carrier:train:one",
                "media_relpath": "other/sample.wav",
                "sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
                "bytes": media.stat().st_size,
            }
        ],
        source_authority={
            "carrier": "other-carrier",
            "partition": "train",
            "roster_schema": "other-roster-v1",
            "roster_sha256": "a" * 64,
        },
        data_root=data,
        encoder_identity=IDENTITY,
    )
    assert inventory["source_authority"]["carrier"] == "other-carrier"


def test_slurp_train_adapter_refuses_repinned_substituted_roster_selection(tmp_path):
    data, roster, _ = _roster(tmp_path)
    document = json.loads(roster.read_text(encoding="utf-8"))
    document["entries"][0]["source_sample_id"] = "slurp:train:000002:substitute"
    roster.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(PreparationError, match="disagrees with readiness selection"):
        build_slurp_train_recalled_media_feature_inventory(
            roster_path=roster,
            expected_roster_sha256=hashlib.sha256(roster.read_bytes()).hexdigest(),
            data_root=data,
            encoder_identity=IDENTITY,
        )

    document["entries"][0]["source_sample_id"] = "slurp:train:000001:train"
    document["entries"][0]["utterance_id"] = "2"
    roster.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PreparationError, match="disagrees with readiness selection"):
        build_slurp_train_recalled_media_feature_inventory(
            roster_path=roster,
            expected_roster_sha256=hashlib.sha256(roster.read_bytes()).hexdigest(),
            data_root=data,
            encoder_identity=IDENTITY,
        )


def test_slurp_train_adapter_refuses_wrong_declared_readiness_entry_hash(tmp_path):
    data, roster, _ = _roster(tmp_path)
    roster_document = json.loads(roster.read_text(encoding="utf-8"))
    readiness = Path(roster_document["source_readiness"]["path"])
    readiness_document = json.loads(readiness.read_text(encoding="utf-8"))
    readiness_document["source_to_media_inventory"]["entry_canonical_sha256"] = "b" * 64
    readiness.write_text(json.dumps(readiness_document), encoding="utf-8")
    roster_document["source_readiness"]["sha256"] = hashlib.sha256(
        readiness.read_bytes()
    ).hexdigest()
    roster_document["source_readiness"]["entry_canonical_sha256"] = "b" * 64
    roster.write_text(json.dumps(roster_document), encoding="utf-8")

    with pytest.raises(PreparationError, match="readiness authority disagrees"):
        build_slurp_train_recalled_media_feature_inventory(
            roster_path=roster,
            expected_roster_sha256=hashlib.sha256(roster.read_bytes()).hexdigest(),
            data_root=data,
            encoder_identity=IDENTITY,
        )
