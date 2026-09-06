"""Unit tests for the EVO-S1 fold flight products.

Synthetic rosters and an injected media probe only: no governed corpus, no
flac, no committed receipt, no contact. One test does exercise the REAL gate
reader (``contracts.gate_media_identity._MediaIdentityMixin``) against a
supplement this module built, because "the gate would accept it" is the whole
point of the artifact and a shape test would not prove it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_evo_flight_products import (
    FlightProductError,
    build_d1_supplement,
    build_runtime_view,
    canonical_sha256,
    channel_mix,
    measure_media,
    packet_coverage,
    probe_receipt,
)

SECONDS = {1: 2.5, 2: 3.25}


def roster(*, seconds: dict[int, float] | None = None) -> dict[str, object]:
    seconds = seconds or SECONDS
    items = [
        {
            "sample_id": f"slurp:train:{index:06d}:audio-{index}",
            "stratum": "weather",
            "audio_seconds": value,
            "headset": index % 2 == 1,
            "utterance_id": f"slurp:train:{index:06d}",
        }
        for index, value in sorted(seconds.items())
    ]
    return {
        "roster_id": "SLURP-EVO-FOLD-A-V2",
        "split_role": "discovery",
        "seed": 20260906,
        "split_identity_hash": "c" * 64,
        "items": items,
    }


def relpaths(document) -> dict[str, str]:
    return {
        str(item["sample_id"]): f"datasets/slurp/slurp_real/audio-{index}.flac"
        for index, item in enumerate(document["items"])
    }


def fake_probe(seconds_by_name: dict[str, float]):
    def probe(path: Path) -> tuple[int, str, float, int]:
        name = Path(path).name
        return 4096, hashlib.sha256(name.encode()).hexdigest(), seconds_by_name[name], 16000

    return probe


@pytest.fixture(name="data_root")
def data_root_fixture(tmp_path_factory) -> Path:
    """A governed-root stand-in holding empty flac files.

    ``_confined_media_path`` resolves every path strictly under the root and
    refuses anything that is not a real file, so the files have to exist; the
    injected probe means their BYTES are never read.
    """

    root = tmp_path_factory.mktemp("data-root")
    media = root / "datasets" / "slurp" / "slurp_real"
    media.mkdir(parents=True)
    for index in range(4):
        (media / f"audio-{index}.flac").write_bytes(b"")
    return root


def measured(document, root: Path, *, drift: float = 0.0) -> list[dict[str, object]]:
    paths = relpaths(document)
    seconds = {
        Path(paths[str(item["sample_id"])]).name: float(item["audio_seconds"]) + drift
        for item in document["items"]
    }
    return measure_media(
        document,
        relpath_by_id=paths,
        data_root=root,
        workers=2,
        probe=fake_probe(seconds),
    )


def parent_d1(ids: tuple[str, ...] = ()) -> dict[str, object]:
    return {
        "carriers": {
            "slurp": {
                "layers": {
                    "media": {
                        "manifest": [
                            {"id": sample_id, "bytes": 1, "sha256": "d" * 64}
                            for sample_id in ids
                        ]
                        or [{"id": "slurp:devel:000011:audio-1", "bytes": 1, "sha256": "d" * 64}]
                    }
                }
            }
        }
    }


def test_measure_media_reports_the_headers_it_read(data_root) -> None:
    document = roster()
    manifest = measured(document, data_root)
    assert [entry["id"] for entry in manifest] == [
        "slurp:train:000001:audio-1",
        "slurp:train:000002:audio-2",
    ]
    assert [entry["audio_seconds"] for entry in manifest] == [2.5, 3.25]
    assert all(entry["roles"] == ["query"] for entry in manifest)
    assert all(entry["sample_rate_hz"] == 16000 for entry in manifest)


def test_a_roster_duration_that_drifted_from_the_header_is_refused(data_root) -> None:
    with pytest.raises(FlightProductError, match="duration drift"):
        measured(roster(), data_root, drift=0.5)


def test_a_row_the_train_loader_does_not_carry_is_refused(data_root) -> None:
    document = roster()
    with pytest.raises(FlightProductError, match="absent from the train loader"):
        measure_media(
            document,
            relpath_by_id={},
            data_root=data_root,
            workers=1,
            probe=fake_probe({}),
        )


def test_a_supplement_never_duplicates_a_base_d1_sample(data_root) -> None:
    document = roster()
    manifest = measured(document, data_root)
    with pytest.raises(FlightProductError, match="already in the immutable D1"):
        build_d1_supplement(
            manifest,
            parent_d1=parent_d1(("slurp:train:000001:audio-1",)),
            parent_d1_sha256="e" * 64,
            source_binding_sha256="f" * 64,
        )


def test_the_supplement_carries_exactly_the_keys_the_gate_requires(data_root) -> None:
    manifest = measured(roster(), data_root)
    supplement = build_d1_supplement(
        manifest,
        parent_d1=parent_d1(),
        parent_d1_sha256="e" * 64,
        source_binding_sha256="f" * 64,
    )
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
    assert supplement["count"] == 2
    assert supplement["total_bytes"] == 8192
    assert supplement["manifest_sha256"] == canonical_sha256(manifest)
    assert supplement["ids_sha256"] == hashlib.sha256(
        "\n".join(sorted(str(entry["id"]) for entry in manifest)).encode("utf-8")
    ).hexdigest()


def test_the_real_gate_reader_accepts_a_supplement_this_module_built(tmp_path, data_root) -> None:
    from speech_aware_evidence_acquisition.contracts.gate import FrozenCoreGate

    manifest = measured(roster(), data_root)
    # The gate resolves D1 THROUGH the E0 closure receipt, never by a
    # hardcoded filename, so the test lays out that exact chain.
    parent_path = tmp_path / "artifacts" / "d1-identity.json"
    parent_path.parent.mkdir(parents=True)
    parent = parent_d1()
    parent_path.write_text(json.dumps(parent), encoding="utf-8")
    parent_sha256 = hashlib.sha256(parent_path.read_bytes()).hexdigest()
    (tmp_path / "e0.json").write_text(
        json.dumps(
            {
                "deliverables": {
                    "d1_identity": {
                        "artifact": "artifacts/d1-identity.json",
                        "sha256": parent_sha256,
                        "status": "CLOSED",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    supplement = build_d1_supplement(
        manifest,
        parent_d1=parent,
        parent_d1_sha256=parent_sha256,
        source_binding_sha256="f" * 64,
    )
    path = tmp_path / "supplement.json"
    path.write_text(json.dumps(supplement), encoding="utf-8")
    gate = replace(
        FrozenCoreGate(
            e0_receipt=tmp_path / "e0.json",
            runtime_receipt=tmp_path / "runtime.json",
            data_root=tmp_path,
            lock_path=tmp_path / "lock.json",
            runtime_root=tmp_path,
            exposure_ledger=tmp_path / "ledger.md",
            source_root=tmp_path,
        ),
        d1_media_supplement=path,
        d1_media_supplement_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    records = gate._d1_media_supplement_records("slurp", {})
    assert set(records) == {entry["id"] for entry in manifest}
    relpath, media_bytes, sha256, seconds, rate = records["slurp:train:000001:audio-1"]
    assert (media_bytes, seconds, rate) == (4096, 2.5, 16000)
    assert relpath == "datasets/slurp/slurp_real/audio-0.flac"
    assert len(sha256) == 64


def test_the_runtime_view_republishes_the_roster_run_identity(data_root) -> None:
    document = roster()
    manifest = measured(document, data_root)
    supplement = build_d1_supplement(
        manifest,
        parent_d1=parent_d1(),
        parent_d1_sha256="e" * 64,
        source_binding_sha256="f" * 64,
    )
    view = build_runtime_view(
        document,
        manifest,
        supplement=supplement,
        supplement_relpath="receipts/artifacts/d1-slurp-evo-fold-a-v2.json",
        supplement_artifact_sha256="a" * 64,
        source_binding_sha256="f" * 64,
    )
    assert view["split_name"] == "SLURP-EVO-FOLD-A-V2"
    assert view["split_identity_hash"] == document["split_identity_hash"]
    assert view["split_role"] == "discovery"
    assert view["count"] == 2
    assert view["audio_seconds_total"] == pytest.approx(5.75)
    assert view["d1_manifest_sha256"] == supplement["manifest_sha256"]
    assert view["items"][0]["packet_id"] == "slurp/train/000001/audio-1"
    unsigned = {k: v for k, v in view.items() if k != "runtime_view_sha256"}
    assert view["runtime_view_sha256"] == canonical_sha256(unsigned)


def test_a_view_whose_supplement_binds_another_roster_is_refused(data_root) -> None:
    document = roster()
    manifest = measured(document, data_root)
    supplement = build_d1_supplement(
        manifest,
        parent_d1=parent_d1(),
        parent_d1_sha256="e" * 64,
        source_binding_sha256="f" * 64,
    )
    with pytest.raises(FlightProductError, match="does not bind this roster"):
        build_runtime_view(
            document,
            manifest,
            supplement=supplement,
            supplement_relpath="receipts/artifacts/x.json",
            supplement_artifact_sha256="a" * 64,
            source_binding_sha256="0" * 64,
        )


def test_the_probe_receipt_verifies_through_the_driver_loader(tmp_path, data_root) -> None:
    from speech_aware_evidence_acquisition.reproduction.probe_split import (
        load_verified_probe_split,
    )

    document = roster()
    manifest = measured(document, data_root)
    supplement = build_d1_supplement(
        manifest,
        parent_d1=parent_d1(),
        parent_d1_sha256="e" * 64,
        source_binding_sha256="f" * 64,
    )
    view = build_runtime_view(
        document,
        manifest,
        supplement=supplement,
        supplement_relpath="receipts/artifacts/d1-slurp-evo-fold-a-v2.json",
        supplement_artifact_sha256="a" * 64,
        source_binding_sha256="f" * 64,
    )
    receipt = probe_receipt(view)
    directory = tmp_path / "docs" / "receipts" / "probe-samples"
    directory.mkdir(parents=True)
    (directory / "SLURP-EVO-FOLD-A-V2.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    verified = load_verified_probe_split(tmp_path, "SLURP-EVO-FOLD-A-V2")
    assert verified.split_role == "discovery"
    assert verified.carrier_lock_key == "slurp"
    assert verified.ids == (
        "slurp:train:000001:audio-1",
        "slurp:train:000002:audio-2",
    )
    # The run-identity convention the runtime view publishes is the one the
    # loader derives, so a plan built from either artifact agrees.
    assert verified.identity_hash != receipt["split_identity_hash"]
    assert receipt["source_split_identity_hash"] == view["split_identity_hash"]


def test_a_tampered_runtime_view_cannot_become_a_probe_receipt(data_root) -> None:
    document = roster()
    manifest = measured(document, data_root)
    supplement = build_d1_supplement(
        manifest,
        parent_d1=parent_d1(),
        parent_d1_sha256="e" * 64,
        source_binding_sha256="f" * 64,
    )
    view = build_runtime_view(
        document,
        manifest,
        supplement=supplement,
        supplement_relpath="receipts/artifacts/d1-slurp-evo-fold-a-v2.json",
        supplement_artifact_sha256="a" * 64,
        source_binding_sha256="f" * 64,
    )
    with pytest.raises(FlightProductError, match="SHA-256 mismatch"):
        probe_receipt({**view, "count": 3})


def test_channel_mix_and_packet_coverage_are_measured_not_assumed(tmp_path) -> None:
    document = roster(seconds={1: 1.0, 2: 1.0, 3: 1.0})
    assert channel_mix(document) == {
        "recordings": 3,
        "headset_recordings": 2,
        "far_field_recordings": 1,
        "headset_share": pytest.approx(0.666667),
    }
    manifest = [{"id": item["sample_id"]} for item in document["items"]]
    (tmp_path / "slurp-q4km-packets-04ccc72a" / "slurp/train/000001/audio-1").mkdir(
        parents=True
    )
    (tmp_path / "slurp-q4km").mkdir()
    coverage = packet_coverage(manifest, feature_cache_root=tmp_path)
    assert coverage["rows"] == 3
    assert coverage["packets_present_by_root"]["slurp-q4km-packets-04ccc72a"] == 1
    assert coverage["packets_present_by_root"]["slurp-q4km-packets"] == 0
    assert coverage["rows_needing_a_packet"] == 2
    assert coverage["legacy_caches_on_disk"] == ["slurp-q4km"]
