"""Item E40: a byte-identical packet whose identity differs only in the encoder
receipt is SHARED, not refused -- plus the driver's zero-contact --promote-only
mode.

The finding this file freezes (2026-09-22, model-free probe): the Stage-3 R01
construction roster overlaps 8 packet ids promoted in August, whose packets
carry the August runtime-receipt document hash while today's receipt
canonicalises to a different one. Audio, decoder, mmproj, position mode, causal
flag AND every chunk's feature/position hash are byte-identical. Bytes are the
evidence hash authority, so that difference is provenance and must be RECORDED,
never refused and never overwritten.

Zero model / encoder / tokenizer / network / GPU contact and no real audio: the
whole harness is synthetic legacy-cache bytes and synthetic packets under
``tmp_path``. No byte under /home/chao/feat-cache is read or written.
"""

from __future__ import annotations

import importlib.util
import json
import os
import struct
import sys
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "slurp_evo_fold_preprocess.py"

_SRC = str(REPO / "src")
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing_pythonpath.split(":"):
    os.environ["PYTHONPATH"] = _SRC + (":" + _existing_pythonpath if _existing_pythonpath else "")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


module = _load("slurp_evo_fold_preprocess_e40", "scripts/slurp_evo_fold_preprocess.py")
audit = _load(
    "packet_promotion_overlap_audit_e40", "scripts/analysis/packet_promotion_overlap_audit.py"
)

from speech_aware_evidence_acquisition.contracts import ExecutionPlan  # noqa: E402
from speech_aware_evidence_acquisition.contracts.errors import (  # noqa: E402
    ExecutionScopeError,
)
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    PROMOTION_MODE_ENCODE_AND_PROMOTE,
    PROMOTION_MODE_PROMOTE_ONLY,
    FrozenCoreError,
    SharedSpeechFeaturePacketRecord,
    legacy_audio_feature_cache_key,
    load_speech_feature_packet,
    load_speech_packet_promotion_receipt,
    materialize_legacy_cached_speech_feature_packets,
)

N_EMBD = 4
N_TOKENS = 2
VIEW_SHA256 = "d" * 64

# Two DIFFERENT runtime receipt DOCUMENTS whose canonical hashes are the two
# encoder receipt identities of the finding. Nothing else about them differs.
RUNTIME_OLD = {
    "schema": "saea-runtime-receipt-v1",
    "role": "preprocess",
    "recorded": "august",
    "gguf_files": [
        {"path": "models/decoder.gguf", "sha256": "c" * 64},
        {"path": "models/mmproj-bf16.gguf", "sha256": "f" * 64},
    ],
}
RUNTIME_NEW = {**RUNTIME_OLD, "recorded": "september"}
OLD_RECEIPT_SHA256 = module.canonical_sha256(RUNTIME_OLD)
NEW_RECEIPT_SHA256 = module.canonical_sha256(RUNTIME_NEW)
DECODER = RUNTIME_NEW["gguf_files"][0]
MMPROJ = RUNTIME_NEW["gguf_files"][1]

ROWS = ("shared-a", "shared-b", "fresh-c", "fresh-d")
SHARED_ROWS = ROWS[:2]
FRESH_ROWS = ROWS[2:]


# ---------------------------------------------------------------------------
# Synthetic four-row world: media bytes, legacy cache entries, packet root.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _AudioRef:
    sha256: str


@dataclass(frozen=True)
class _Sample:
    sample_id: str
    media_relpath: str
    audio_ref: _AudioRef
    audio_seconds: float


@dataclass(frozen=True)
class _World:
    root: Path
    cache: Path
    packets: Path
    samples: tuple[_Sample, ...]

    def binding(self, names):
        return tuple(
            {
                "packet_id": _packet_id(name),
                "audio_path": str(self.root / _media_relpath(name)),
            }
            for name in names
        )

    def packet_dir(self, name: str) -> Path:
        return self.packets / _packet_id(name)


def _packet_id(name: str) -> str:
    return "slurp/train/e40/%s" % name


def _media_relpath(name: str) -> str:
    return "media/%s.bin" % name


def _audio_bytes(name: str) -> bytes:
    return ("synthetic-media-%s" % name).encode("utf-8")


def _feature_payload(name: str, *, ordinal: int = 0) -> bytes:
    """Deterministic, distinct per row and ordinal; never real speech."""

    seed = sha256(("%s:%d" % (name, ordinal)).encode("utf-8")).digest()
    body = (seed * (N_TOKENS * N_EMBD * 4 // len(seed) + 1))[: N_TOKENS * N_EMBD * 4]
    return struct.pack("<QQ", N_TOKENS, N_EMBD) + body


def _write_cache_entry(cache: Path, name: str, *, ordinals: int = 1, payload=None) -> None:
    key = legacy_audio_feature_cache_key(_audio_bytes(name))
    for ordinal in range(ordinals):
        raw = payload(name, ordinal) if payload else _feature_payload(name, ordinal=ordinal)
        (cache / ("%s_o%d.feat" % (key, ordinal))).write_bytes(raw)


def _world(tmp_path: Path) -> _World:
    root = tmp_path / "data"
    cache = tmp_path / "legacy-cache"
    packets = tmp_path / "packets"
    (root / "media").mkdir(parents=True)
    cache.mkdir()
    samples = []
    for name in ROWS:
        audio = _audio_bytes(name)
        (root / _media_relpath(name)).write_bytes(audio)
        _write_cache_entry(cache, name)
        samples.append(
            _Sample(
                sample_id="slurp:train:e40:%s" % name,
                media_relpath=_media_relpath(name),
                audio_ref=_AudioRef(sha256=sha256(audio).hexdigest()),
                audio_seconds=1.0,
            )
        )
    return _World(root=root, cache=cache, packets=packets, samples=tuple(samples))


def _promote(world: _World, names, *, receipt_sha256: str, decoder=DECODER, workers: int = 2):
    shared: list[SharedSpeechFeaturePacketRecord] = []
    packets = materialize_legacy_cached_speech_feature_packets(
        feature_root=world.packets,
        bindings=world.binding(names),
        legacy_cache_dir=world.cache,
        encoder_receipt_sha256=receipt_sha256,
        decoder_gguf_sha256=str(decoder["sha256"]),
        mmproj_sha256=str(MMPROJ["sha256"]),
        expected_n_embd=N_EMBD,
        causal_attention=True,
        workers=workers,
        on_shared=shared.append,
    )
    return packets, tuple(shared)


def _snapshot(directory: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


# ---------------------------------------------------------------------------
# The four-row dry run: two shared, two fresh.
# ---------------------------------------------------------------------------


def test_shared_packets_are_accepted_unchanged_and_fresh_packets_are_written(
    tmp_path: Path,
) -> None:
    world = _world(tmp_path)
    first, first_shared = _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    assert first_shared == ()
    assert [packet.encoder_receipt_sha256 for packet in first] == [OLD_RECEIPT_SHA256] * 2
    before = {name: _snapshot(world.packet_dir(name)) for name in SHARED_ROWS}
    assert not any(world.packet_dir(name).exists() for name in FRESH_ROWS)

    packets, shared = _promote(world, ROWS, receipt_sha256=NEW_RECEIPT_SHA256)

    # Not one byte of an already-promoted packet is rewritten.
    assert {name: _snapshot(world.packet_dir(name)) for name in SHARED_ROWS} == before
    # ... and the two shared packets are reported, in input order, with both
    # receipt hashes and the identity the reader can re-verify.
    assert [record.packet_id for record in shared] == [_packet_id(n) for n in SHARED_ROWS]
    for record, packet in zip(shared, first, strict=True):
        assert record.existing_encoder_receipt_sha256 == OLD_RECEIPT_SHA256
        assert record.verified_against_encoder_receipt_sha256 == NEW_RECEIPT_SHA256
        assert record.existing_packet_sha256 == packet.packet_sha256
        assert record.chunk_count == len(packet.chunks) == 1
    # The shared packets are returned unchanged (August identity kept), the two
    # fresh ones are written under the new receipt.
    by_id = {packet.packet_id: packet for packet in packets}
    assert len(packets) == 4
    for name in SHARED_ROWS:
        assert by_id[_packet_id(name)].encoder_receipt_sha256 == OLD_RECEIPT_SHA256
    for name in FRESH_ROWS:
        assert world.packet_dir(name).is_dir()
        assert by_id[_packet_id(name)].encoder_receipt_sha256 == NEW_RECEIPT_SHA256
        assert (
            load_speech_feature_packet(world.packets, _packet_id(name)).packet_sha256
            == by_id[_packet_id(name)].packet_sha256
        )


def test_an_identical_replay_reports_no_shared_packet(tmp_path: Path) -> None:
    world = _world(tmp_path)
    _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    packets, shared = _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    assert shared == ()
    assert len(packets) == 2


def test_a_different_chunk_hash_is_still_refused(tmp_path: Path) -> None:
    world = _world(tmp_path)
    _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    before = _snapshot(world.packet_dir("shared-a"))
    # Same packet id, same everything but the cached feature bytes.
    _write_cache_entry(
        world.cache,
        "shared-a",
        payload=lambda name, ordinal: _feature_payload("tampered-%s" % name, ordinal=ordinal),
    )
    with pytest.raises(FrozenCoreError, match="different chunk bytes or shape"):
        _promote(world, ("shared-a",), receipt_sha256=NEW_RECEIPT_SHA256)
    assert _snapshot(world.packet_dir("shared-a")) == before


def test_a_different_decoder_sha_is_still_refused(tmp_path: Path) -> None:
    world = _world(tmp_path)
    _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    before = _snapshot(world.packet_dir("shared-b"))
    with pytest.raises(FrozenCoreError, match="different source/model metadata"):
        _promote(
            world,
            ("shared-b",),
            receipt_sha256=NEW_RECEIPT_SHA256,
            decoder={"path": "models/other.gguf", "sha256": "1" * 64},
        )
    assert _snapshot(world.packet_dir("shared-b")) == before


def test_a_shared_packet_with_a_different_chunk_count_is_refused(tmp_path: Path) -> None:
    world = _world(tmp_path)
    _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    before = _snapshot(world.packet_dir("shared-a"))
    _write_cache_entry(world.cache, "shared-a", ordinals=2)
    with pytest.raises(FrozenCoreError, match="different chunk count"):
        _promote(world, ("shared-a",), receipt_sha256=NEW_RECEIPT_SHA256)
    assert _snapshot(world.packet_dir("shared-a")) == before


# ---------------------------------------------------------------------------
# The promotion receipt's shared_packets ledger.
# ---------------------------------------------------------------------------


def _receipt(world: _World, packets, shared, *, mode: str, contacts: int, **overrides):
    document = module._promotion_receipt_document(
        packets=packets,
        shared=shared,
        values={"runtime_view_sha256": VIEW_SHA256},
        packet_root=world.packets,
        legacy_cache=world.cache,
        decoder=DECODER,
        mmproj=MMPROJ,
        runtime_receipt=RUNTIME_NEW,
        mode=mode,
        encode_contacts=contacts,
        session_id=overrides.pop("session_id", "a-session"),
        session_receipt_sha256=overrides.pop("session_receipt_sha256", "9" * 64),
        stop_receipt_sha256=overrides.pop("stop_receipt_sha256", "8" * 64),
    )
    document.update(overrides)
    return document


def _load(world: _World, document, path: Path):
    raw = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(raw, encoding="utf-8", newline="\n")
    return load_speech_packet_promotion_receipt(
        path,
        expected_sha256=sha256(path.read_bytes()).hexdigest(),
        expected_feature_root=world.packets,
        expected_dataset_runtime_view_sha256=VIEW_SHA256,
    )


def test_the_receipt_names_exactly_the_shared_packets_with_both_receipt_hashes(
    tmp_path: Path,
) -> None:
    world = _world(tmp_path)
    existing, _ = _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    packets, shared = _promote(world, ROWS, receipt_sha256=NEW_RECEIPT_SHA256)
    document = _receipt(world, packets, shared, mode=PROMOTION_MODE_ENCODE_AND_PROMOTE, contacts=4)

    assert document["shared_packet_count"] == 2
    assert document["shared_packets"] == [
        {
            "packet_id": _packet_id(name),
            "existing_encoder_receipt_sha256": OLD_RECEIPT_SHA256,
            "verified_against_encoder_receipt_sha256": NEW_RECEIPT_SHA256,
            "existing_packet_sha256": packet.packet_sha256,
            "chunk_count": 1,
        }
        for name, packet in zip(SHARED_ROWS, existing, strict=True)
    ]
    # The per-packet entries are unchanged: a shared packet is listed under the
    # hash it has ON DISK, so re-verifying this receipt against the root holds.
    promoted = {entry["packet_id"]: entry for entry in document["packets"]}
    for name, packet in zip(SHARED_ROWS, existing, strict=True):
        assert promoted[_packet_id(name)]["packet_sha256"] == packet.packet_sha256
    assert len(document["packets"]) == 4

    loaded = _load(world, document, tmp_path / "promotion.json")
    assert loaded["shared_packet_count"] == 2
    assert loaded["mode"] == PROMOTION_MODE_ENCODE_AND_PROMOTE


def test_a_receipt_without_the_e40_keys_still_loads(tmp_path: Path) -> None:
    """Every receipt sealed before item E40 reads exactly as it always did."""

    world = _world(tmp_path)
    packets, shared = _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    document = _receipt(world, packets, shared, mode=PROMOTION_MODE_ENCODE_AND_PROMOTE, contacts=2)
    for key in ("mode", "encode_contacts", "shared_packets", "shared_packet_count"):
        document.pop(key)
    assert _load(world, document, tmp_path / "legacy.json")["count"] == 2


@pytest.mark.parametrize(
    "mutation",
    [
        {"shared_packet_count": 3},
        {"shared_packets": [{"packet_id": "slurp/train/e40/shared-a"}]},
    ],
)
def test_a_malformed_shared_ledger_is_refused(tmp_path: Path, mutation) -> None:
    world = _world(tmp_path)
    _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    packets, shared = _promote(world, ROWS, receipt_sha256=NEW_RECEIPT_SHA256)
    document = _receipt(world, packets, shared, mode=PROMOTION_MODE_ENCODE_AND_PROMOTE, contacts=4)
    document.update(mutation)
    with pytest.raises(FrozenCoreError):
        _load(world, document, tmp_path / "bad.json")


def test_a_shared_row_for_an_unpromoted_packet_is_refused(tmp_path: Path) -> None:
    world = _world(tmp_path)
    _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    packets, shared = _promote(world, ROWS, receipt_sha256=NEW_RECEIPT_SHA256)
    document = _receipt(world, packets, shared, mode=PROMOTION_MODE_ENCODE_AND_PROMOTE, contacts=4)
    document["shared_packets"][0]["packet_id"] = "slurp/train/e40/not-promoted"
    with pytest.raises(FrozenCoreError, match="is not promoted"):
        _load(world, document, tmp_path / "stray.json")


# ---------------------------------------------------------------------------
# --promote-only.
# ---------------------------------------------------------------------------


def test_the_promote_only_receipt_carries_null_session_hashes_and_zero_contacts(
    tmp_path: Path,
) -> None:
    world = _world(tmp_path)
    packets, shared = _promote(world, ROWS, receipt_sha256=NEW_RECEIPT_SHA256)
    document = _receipt(
        world, packets, shared, mode=PROMOTION_MODE_PROMOTE_ONLY, contacts=0,
        session_id="promote-only:RUN:attempt", session_receipt_sha256=None,
        stop_receipt_sha256=None,
    )
    loaded = _load(world, document, tmp_path / "promote-only.json")
    assert loaded["mode"] == PROMOTION_MODE_PROMOTE_ONLY
    assert loaded["encode_contacts"] == 0
    assert loaded["preprocess_session_receipt_sha256"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        {"preprocess_stop_receipt_sha256": "7" * 64},
        {"encode_contacts": 1},
        {"mode": "made-up-mode"},
    ],
)
def test_a_promote_only_receipt_that_claims_a_session_or_a_contact_is_refused(
    tmp_path: Path, mutation
) -> None:
    world = _world(tmp_path)
    packets, shared = _promote(world, ROWS, receipt_sha256=NEW_RECEIPT_SHA256)
    document = _receipt(
        world, packets, shared, mode=PROMOTION_MODE_PROMOTE_ONLY, contacts=0,
        session_id="promote-only:RUN:attempt", session_receipt_sha256=None,
        stop_receipt_sha256=None,
    )
    document.update(mutation)
    with pytest.raises(FrozenCoreError):
        _load(world, document, tmp_path / "bad-promote-only.json")


def test_promote_only_parses_and_requires_a_new_attempt_id() -> None:
    parsed = module.build_parser().parse_args(
        ["--roster", "fold-a", "--promote-only", "--attempt-id", "attempt-e40-v1"]
    )
    assert (parsed.promote_only, parsed.run, parsed.preflight_only) == (True, False, False)
    assert parsed.attempt_id == "attempt-e40-v1"
    # No --attempt-id: refused before any config, data root or media is read.
    with pytest.raises(SystemExit, match="requires an explicit --attempt-id"):
        module.main(["--roster", "fold-a", "--promote-only"])
    # --run and --promote-only are mutually exclusive at the parser.
    with pytest.raises(SystemExit):
        module.build_parser().parse_args(["--roster", "fold-a", "--run", "--promote-only"])


def test_promote_only_refuses_a_roster_that_is_not_fully_warm() -> None:
    assert module._require_fully_warm(800, 800, "stage3-construction-r01") is None
    with pytest.raises(SystemExit, match=r"797/800 warm \(3 cold\)"):
        module._require_fully_warm(797, 800, "stage3-construction-r01")


def test_the_promote_only_plan_is_zero_and_the_validator_still_refuses_zero() -> None:
    """The zero declaration is honest BECAUSE no plan is opened for it.

    ``contracts.ExecutionPlan`` requires finite positive calls/GPU-hours/speech
    seconds, so a zero-contact pass cannot hold a validated plan without
    weakening the validator. Item E40 weakens nothing: it opens no plan at all.
    """

    assert module.PROMOTE_ONLY_PLAN["calls"] == 0
    assert module.PROMOTE_ONLY_PLAN["speech_audio_seconds"] == 0
    assert module.PROMOTE_ONLY_PLAN["gpu_hours"] == 0.0
    with pytest.raises(ExecutionScopeError):
        ExecutionPlan(
            run_id="SAEA-E40-PROMOTE-ONLY",
            execution_profile="model-free-check",
            carrier_lock_key="slurp",
            split_role="discovery",
            split_identity_hash="a" * 64,
            planned_model_calls=int(module.PROMOTE_ONLY_PLAN["calls"]),
            planned_gpu_hours=float(module.PROMOTE_ONLY_PLAN["gpu_hours"]),
            planned_speech_audio_seconds=int(module.PROMOTE_ONLY_PLAN["speech_audio_seconds"]),
            protocol_hash="b" * 64,
            attempt_id="attempt-e40-v1",
        ).validate()


def test_promote_only_dry_run_promotes_four_rows_without_touching_a_server(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """The four-row dry run through the driver's own --promote-only path."""

    world = _world(tmp_path)
    _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    before = {name: _snapshot(world.packet_dir(name)) for name in SHARED_ROWS}

    def _forbidden(*args, **kwargs):  # pragma: no cover -- must never run
        raise AssertionError("--promote-only must not touch a server")

    monkeypatch.setattr(module, "start_session", _forbidden)
    monkeypatch.setattr(module, "stop_session", _forbidden)
    monkeypatch.setattr(module, "FrozenCoreClient", _forbidden)
    monkeypatch.setattr(module, "ExecutionPlan", _forbidden)
    monkeypatch.setattr(module, "load_runtime_receipt", lambda path: dict(RUNTIME_NEW))
    # The synthetic cache carries a toy decoder dimension, not the real 2048.
    monkeypatch.setattr(module, "EXPECTED_N_EMBD", N_EMBD)

    spec = module.RosterSpec(
        run_id="SAEA-E40-DRY-RUN", dataset_fragment="d", experiment_fragment="e",
        sample_id_prefix="slurp:train:", split_role="discovery",
        promotion_receipt_name="E40-promotion.json", default_attempt_id="attempt-unused",
        plan_calls=1, plan_speech_seconds=1, plan_gpu_hours=1.0,
    )
    args = module.build_parser().parse_args(
        ["--roster", "fold-a", "--promote-only", "--attempt-id", "attempt-e40-dry-run-v1",
         "--promote-workers", "2"]
    )
    receipt_path = world.packets / "E40-promotion.json"
    world.packets.mkdir(parents=True, exist_ok=True)

    class _Composed:
        config_hash = "c" * 64

    assert module._promote_only(
        args, roster_key="e40-dry-run", spec=spec,
        values={"runtime_view_sha256": VIEW_SHA256, "split_identity_hash": "a" * 64},
        samples=world.samples, root=world.root, packet_root=world.packets,
        legacy_cache=world.cache, promotion_receipt=receipt_path,
        composed=_Composed(), audio_seconds=4.0, warm=len(world.samples),
    ) == 0
    capsys.readouterr()

    assert {name: _snapshot(world.packet_dir(name)) for name in SHARED_ROWS} == before
    document = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert document["mode"] == PROMOTION_MODE_PROMOTE_ONLY
    assert document["encode_contacts"] == 0
    assert document["preprocess_session_receipt_sha256"] is None
    assert document["preprocess_stop_receipt_sha256"] is None
    assert document["count"] == 4
    assert document["shared_packet_count"] == 2
    assert [row["packet_id"] for row in document["shared_packets"]] == sorted(
        _packet_id(name) for name in SHARED_ROWS
    )
    assert _load(world, document, tmp_path / "roundtrip.json")["count"] == 4

    report_path = world.root / "runs" / spec.run_id / args.attempt_id / module.PROMOTE_ONLY_REPORT_NAME
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["contacts"] == 0 and report["failures"] == []
    assert report["mode"] == PROMOTION_MODE_PROMOTE_ONLY
    assert report["execution_profile"] == module.PROMOTE_ONLY_PROFILE
    assert report["declared_plan"]["calls"] == 0
    assert report["shared_packet_count"] == 2
    assert report["promotion_receipt_sha256"] == sha256(receipt_path.read_bytes()).hexdigest()

    # The same attempt id can never be recorded twice.
    with pytest.raises(SystemExit, match="records a NEW attempt"):
        module._promote_only(
            args, roster_key="e40-dry-run", spec=spec,
            values={"runtime_view_sha256": VIEW_SHA256, "split_identity_hash": "a" * 64},
            samples=world.samples, root=world.root, packet_root=world.packets,
            legacy_cache=world.cache, promotion_receipt=receipt_path,
            composed=_Composed(), audio_seconds=4.0, warm=len(world.samples),
        )


# ---------------------------------------------------------------------------
# The read-only overlap audit (scripts/analysis/packet_promotion_overlap_audit.py).
# ---------------------------------------------------------------------------


def _classify(world: _World, name: str, runtime_receipt, *, audio: bool = True):
    row = {"sample_id": "slurp:train:e40:%s" % name}
    if audio:
        row["audio_sha256"] = sha256(_audio_bytes(name)).hexdigest()
    return audit.classify(
        packet_id=_packet_id(name), packet_root=world.packets,
        expected=audit.expected_identity(runtime_receipt), roster_row=row, fresh_root=None,
    )


def test_the_audit_calls_a_provenance_only_difference_shareable(tmp_path: Path) -> None:
    world = _world(tmp_path)
    packets, _ = _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    record = _classify(world, "shared-a", RUNTIME_NEW)
    assert record["verdict"] == "shareable"
    assert record["differing_identity_fields"] == ["encoder_receipt_sha256"]
    assert record["existing_encoder_receipt_sha256"] == OLD_RECEIPT_SHA256
    assert record["expected_encoder_receipt_sha256"] == NEW_RECEIPT_SHA256
    assert record["packet_sha256"] == packets[0].packet_sha256
    assert record["chunk_count"] == 1


def test_the_audit_calls_an_unchanged_identity_identical(tmp_path: Path) -> None:
    world = _world(tmp_path)
    _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    record = _classify(world, "shared-a", RUNTIME_OLD)
    assert record["verdict"] == "identical"
    assert record["differing_identity_fields"] == []


def test_the_audit_calls_a_model_difference_conflicting(tmp_path: Path) -> None:
    world = _world(tmp_path)
    _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    other = {
        **RUNTIME_NEW,
        "gguf_files": [
            {"path": "models/decoder.gguf", "sha256": "2" * 64},
            {"path": "models/mmproj-bf16.gguf", "sha256": MMPROJ["sha256"]},
        ],
    }
    record = _classify(world, "shared-a", other)
    assert record["verdict"] == "conflicting"
    assert "decoder_gguf_sha256" in record["differing_identity_fields"]


def test_the_audit_indexes_the_overlap_across_promotion_receipts(tmp_path: Path) -> None:
    world = _world(tmp_path)
    _promote(world, SHARED_ROWS, receipt_sha256=OLD_RECEIPT_SHA256)
    for index, name in enumerate(SHARED_ROWS):
        (world.packets / ("R%d-promotion.json" % index)).write_text(
            json.dumps({"packets": [{"packet_id": _packet_id(name)}]}), encoding="utf-8"
        )
    promoted = audit.promotion_index(world.packets)
    assert sorted(promoted) == sorted(_packet_id(name) for name in SHARED_ROWS)
    rows = audit.roster_rows(
        {"items": [{"sample_id": sample.sample_id} for sample in world.samples]},
        Path("synthetic-roster.json"),
    )
    assert sorted(set(rows) & set(promoted)) == sorted(_packet_id(n) for n in SHARED_ROWS)
    # The roster derives the packet id from the sample id when it pins none.
    assert set(rows) == {_packet_id(name) for name in ROWS}
