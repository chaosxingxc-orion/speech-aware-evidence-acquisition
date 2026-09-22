"""Model-free coverage for the additive SLURP D1 media supplement builder.

The oracle for the receipt's SHAPE is the production gate itself
(``contracts.gate_media_identity``): the supplement written here is handed to a
real ``FrozenCoreGate`` built by the contract suite's ``GateFixture``, and the
assertions are about what that gate admits and refuses -- never about a
re-implementation of its parser.

Every media file in this module is a synthetic 16 kHz PCM WAV written by the
standard library. No corpus byte, transcript, label or model is touched.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import wave
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import GateClosed
from speech_aware_evidence_acquisition.data.slurp import load_slurp_engineering_gate


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/build_slurp_stage3_construction_r01_d1_supplement.py"
GATE_FIXTURE = REPO / "tests/contract/gate_fixture.py"

SPLIT_NAME = "STAGE3-CONSTRUCTION-TEST"
MEDIA_SUBDIR = "datasets/slurp/slurp_real"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _builder():
    return _load_module(SCRIPT, "slurp_stage3_d1_supplement_under_test")


def _gate_fixture_class():
    return _load_module(GATE_FIXTURE, "slurp_stage3_gate_fixture_under_test").GateFixture


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_wav(path: Path, *, frames: int, rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x01\x00" * frames)


def _canonical(document: object) -> str:
    return _sha(
        json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


class _World:
    """A two-row SLURP roster, its runtime view and a parent D1 artifact."""

    def __init__(self, data_root: Path, tmp_path: Path, *, base_ids: tuple[str, ...] = ()):
        self.data_root = data_root
        self.rows: list[dict[str, object]] = []
        for index, frames in enumerate((1600, 3200), start=1):
            sample_id = f"slurp:train:00000{index}:audio-{index}"
            relpath = f"{MEDIA_SUBDIR}/audio-{index}.wav"
            media = data_root / relpath
            _write_wav(media, frames=frames)
            raw = media.read_bytes()
            self.rows.append(
                {
                    "sample_id": sample_id,
                    "media_relpath": relpath,
                    "audio_sha256": _sha(raw),
                    "audio_seconds": round(frames / 16000, 9),
                    "sample_rate_hz": 16000,
                    "packet_id": sample_id.replace(":", "/"),
                    "_bytes": len(raw),
                }
            )
        self.roster_path = tmp_path / "roster.json"
        self.view_path = tmp_path / "runtime-view.json"
        self.parent_path = tmp_path / "d1-identity.json"
        self.write_roster()
        self.write_view()
        self.write_parent(base_ids)

    @property
    def sample_ids(self) -> list[str]:
        return [str(row["sample_id"]) for row in self.rows]

    def _public_rows(self) -> list[dict[str, object]]:
        return [
            {key: value for key, value in row.items() if not key.startswith("_")}
            for row in self.rows
        ]

    def write_roster(self) -> None:
        roster = {
            "schema": "saea-roster-receipt-v1",
            "carrier_lock_key": "slurp",
            "roster_id": SPLIT_NAME,
            "roster_role": "construction",
            "split_role": "discovery",
            "seed": 20260922,
            "split_identity_hash": "b" * 64,
            "count": len(self.rows),
            "items": [
                {
                    "sample_id": row["sample_id"],
                    "audio_seconds": row["audio_seconds"],
                    "stratum": "general",
                }
                for row in self.rows
            ],
        }
        self.roster = roster
        self.roster_path.write_text(
            json.dumps(roster, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def write_view(self, **overrides: object) -> None:
        items = self._public_rows()
        unsigned: dict[str, object] = {
            "schema": "saea-speech-native-runtime-view-v1",
            "study": "speech-aware-evidence-acquisition",
            "status": "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION",
            "carrier_lock_key": "slurp",
            "split_name": SPLIT_NAME,
            "split_role": "discovery",
            "seed": 20260922,
            "split_identity_hash": "b" * 64,
            "source_binding_sha256": _canonical(self.roster),
            "d1_media_supplement": None,
            "d1_media_supplement_sha256": None,
            "d1_manifest_sha256": None,
            "count": len(items),
            "audio_seconds_total": round(
                sum(float(item["audio_seconds"]) for item in items), 9
            ),
            "items": items,
        }
        unsigned.update(overrides)
        view = {**unsigned, "runtime_view_sha256": _canonical(unsigned)}
        self.view = view
        self.view_path.write_text(
            json.dumps(view, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def write_parent(self, base_ids: tuple[str, ...]) -> None:
        manifest = []
        for row in self.rows:
            if str(row["sample_id"]) in base_ids:
                manifest.append(
                    {
                        "id": row["sample_id"],
                        "bytes": row["_bytes"],
                        "sha256": row["audio_sha256"],
                    }
                )
        # The gate refuses an empty base media manifest, so a devel-shaped row
        # that no roster names is always present.
        filler = b"devel-media-that-no-roster-names" * 8
        manifest.append(
            {"id": "slurp:devel:000001:audio-0", "bytes": len(filler), "sha256": _sha(filler)}
        )
        self.parent = {
            "carriers": {"slurp": {"layers": {"media": {"manifest": manifest}}}}
        }
        self.parent_path.write_text(
            json.dumps(self.parent, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def build(self, module, **kwargs):
        return module.build_supplement(
            roster_path=self.roster_path,
            runtime_view_path=self.view_path,
            data_root=self.data_root,
            parent_d1_path=self.parent_path,
            **kwargs,
        )


def test_supplement_binds_its_roster_and_is_deterministic(tmp_path: Path) -> None:
    module = _builder()
    world = _World(tmp_path / "data", tmp_path)

    supplement, skipped = world.build(module)
    again, again_skipped = world.build(module, workers=1)

    assert skipped == [] and again_skipped == []
    assert supplement == again
    assert json.dumps(supplement, sort_keys=True) == json.dumps(again, sort_keys=True)

    assert supplement["schema"] == "saea-d1-media-supplement-v1"
    assert supplement["study"] == "speech-aware-evidence-acquisition"
    assert supplement["carrier_lock_key"] == "slurp"
    assert supplement["parent_d1_sha256"] == _sha(world.parent_path.read_bytes())
    assert supplement["source_binding_sha256"] == _canonical(world.roster)
    assert supplement["source_binding_sha256"] == world.view["source_binding_sha256"]
    assert supplement["count"] == 2
    assert [entry["id"] for entry in supplement["manifest"]] == world.sample_ids
    assert supplement["manifest"][0] == {
        "id": world.rows[0]["sample_id"],
        "media_relpath": world.rows[0]["media_relpath"],
        "bytes": world.rows[0]["_bytes"],
        "sha256": world.rows[0]["audio_sha256"],
        "audio_seconds": world.rows[0]["audio_seconds"],
        "sample_rate_hz": 16000,
        "roles": ["query"],
    }
    assert supplement["manifest_sha256"] == _canonical(supplement["manifest"])
    assert supplement["ids_sha256"] == _sha("\n".join(world.sample_ids).encode("utf-8"))
    assert supplement["total_bytes"] == sum(row["_bytes"] for row in world.rows)


def test_base_closure_ids_are_skipped_not_supplemented(tmp_path: Path) -> None:
    module = _builder()
    world = _World(tmp_path / "data", tmp_path)
    already_inside = world.sample_ids[0]
    world.write_parent((already_inside,))

    supplement, skipped = world.build(module)

    assert skipped == [already_inside]
    assert [entry["id"] for entry in supplement["manifest"]] == world.sample_ids[1:]
    assert supplement["count"] == 1

    # A base record that disagrees about the bytes is an identity conflict, not
    # something to silently supplement over.
    tampered = json.loads(world.parent_path.read_text(encoding="utf-8"))
    for entry in tampered["carriers"]["slurp"]["layers"]["media"]["manifest"]:
        if entry["id"] == already_inside:
            entry["bytes"] = int(entry["bytes"]) + 1
    world.parent_path.write_text(json.dumps(tampered, sort_keys=True), encoding="utf-8")
    with pytest.raises(module.SupplementError, match="identity disagreement"):
        world.build(module)


def test_builder_refuses_a_view_that_does_not_bind_its_roster(tmp_path: Path) -> None:
    module = _builder()
    world = _World(tmp_path / "data", tmp_path)
    world.write_view(source_binding_sha256="c" * 64)
    with pytest.raises(module.SupplementError, match="does not bind this roster"):
        world.build(module)


def test_builder_refuses_media_that_drifted_from_the_view(tmp_path: Path) -> None:
    module = _builder()
    world = _World(tmp_path / "data", tmp_path)
    _write_wav(world.data_root / str(world.rows[0]["media_relpath"]), frames=4800)
    with pytest.raises(module.SupplementError, match="media hash drift"):
        world.build(module)


def _gate_world(tmp_path: Path, module):
    """A real ``FrozenCoreGate`` whose D1 artifact and media are this world's."""

    fixture = _gate_fixture_class()(tmp_path)
    world = _World(fixture.data_root, tmp_path)
    d1_path = fixture.receipts / "e0" / "d1_identity.json"
    d1_bytes = world.parent_path.read_bytes()
    d1_path.write_bytes(d1_bytes)
    fixture.deliverables["d1_identity"]["sha256"] = _sha(d1_bytes)
    world.parent_path = d1_path
    supplement, skipped = world.build(module)
    assert skipped == []
    supplement_path = tmp_path / "d1-slurp-supplement.json"
    supplement_path.write_text(
        json.dumps(supplement, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    gate = replace(
        fixture.gate(),
        d1_media_supplement=supplement_path,
        d1_media_supplement_sha256=_sha(supplement_path.read_bytes()),
    )
    return fixture, world, supplement, supplement_path, gate


def test_gate_admits_the_supplemented_ids_and_their_exact_bytes(tmp_path: Path) -> None:
    module = _builder()
    _fixture, world, _supplement, _path, gate = _gate_world(tmp_path, module)

    closure = gate.media_identity_closure_ids("slurp")
    assert set(world.sample_ids) <= closure
    assert "slurp:devel:000001:audio-0" in closure

    facts = {
        str(row["sample_id"]): (str(row["media_relpath"]), float(row["audio_seconds"]))
        for row in world.rows
    }
    gate.verify_media_identity("slurp", facts)
    gate.assert_media_identity_closure("slurp", world.sample_ids)


def test_gate_refuses_a_tampered_byte_count(tmp_path: Path) -> None:
    module = _builder()
    _fixture, world, supplement, path, _gate = _gate_world(tmp_path, module)

    tampered = json.loads(json.dumps(supplement))
    tampered["manifest"][0]["bytes"] = int(tampered["manifest"][0]["bytes"]) + 1
    tampered["manifest_sha256"] = _canonical(tampered["manifest"])
    tampered["total_bytes"] = sum(int(entry["bytes"]) for entry in tampered["manifest"])
    path.write_text(json.dumps(tampered, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    fixture_gate = replace(
        _fixture.gate(),
        d1_media_supplement=path,
        d1_media_supplement_sha256=_sha(path.read_bytes()),
    )
    facts = {
        str(world.rows[0]["sample_id"]): (
            str(world.rows[0]["media_relpath"]),
            float(world.rows[0]["audio_seconds"]),
        )
    }
    with pytest.raises(GateClosed, match="media identity drift"):
        fixture_gate.verify_media_identity("slurp", facts)


def test_gate_refuses_an_unrecomputed_manifest_hash(tmp_path: Path) -> None:
    module = _builder()
    _fixture, _world, supplement, path, _gate = _gate_world(tmp_path, module)

    tampered = json.loads(json.dumps(supplement))
    tampered["manifest"][0]["bytes"] = int(tampered["manifest"][0]["bytes"]) + 1
    path.write_text(json.dumps(tampered, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    fixture_gate = replace(
        _fixture.gate(),
        d1_media_supplement=path,
        d1_media_supplement_sha256=_sha(path.read_bytes()),
    )
    with pytest.raises(GateClosed, match="manifest SHA-256 mismatch"):
        fixture_gate.media_identity_closure_ids("slurp")


def test_pinned_runtime_view_keeps_its_key_set_and_parses(tmp_path: Path) -> None:
    module = _builder()
    world = _World(tmp_path / "data", tmp_path)
    supplement, _skipped = world.build(module)
    supplement_path = tmp_path / "receipts/artifacts/d1-slurp-test.json"
    artifact_sha256 = module.write_json(supplement_path, supplement)

    pinned = module.pin_runtime_view(
        world.view,
        supplement=supplement,
        supplement_relpath="receipts/artifacts/d1-slurp-test.json",
        supplement_artifact_sha256=artifact_sha256,
    )

    assert set(pinned) == set(world.view)
    assert pinned["d1_media_supplement"] == "receipts/artifacts/d1-slurp-test.json"
    assert pinned["d1_media_supplement_sha256"] == artifact_sha256
    assert pinned["d1_manifest_sha256"] == supplement["manifest_sha256"]
    assert pinned["runtime_view_sha256"] != world.view["runtime_view_sha256"]
    unsigned = {key: value for key, value in pinned.items() if key != "runtime_view_sha256"}
    assert pinned["runtime_view_sha256"] == _canonical(unsigned)

    # The production loader is the oracle for the fragment: exact key set,
    # all-or-nothing supplement triple, re-measured media.
    module.write_json(world.view_path, pinned)
    gate = load_slurp_engineering_gate(
        world.view_path,
        data_root=world.data_root,
        expected_count=len(world.rows),
        expected_split_name=SPLIT_NAME,
        workers=1,
    )
    assert gate.runtime_view_sha256 == pinned["runtime_view_sha256"]
    assert gate.d1_media_supplement == "receipts/artifacts/d1-slurp-test.json"
    assert gate.d1_media_supplement_sha256 == artifact_sha256
    assert [sample.sample_id for sample in gate.samples] == world.sample_ids


def test_pin_refuses_a_docs_prefixed_path_or_a_foreign_supplement(tmp_path: Path) -> None:
    module = _builder()
    world = _World(tmp_path / "data", tmp_path)
    supplement, _skipped = world.build(module)

    with pytest.raises(module.SupplementError, match="must not repeat it"):
        module.pin_runtime_view(
            world.view,
            supplement=supplement,
            supplement_relpath="docs/receipts/artifacts/d1-slurp-test.json",
            supplement_artifact_sha256="a" * 64,
        )

    foreign = {**supplement, "source_binding_sha256": "d" * 64}
    with pytest.raises(module.SupplementError, match="does not bind"):
        module.pin_runtime_view(
            world.view,
            supplement=foreign,
            supplement_relpath="receipts/artifacts/d1-slurp-test.json",
            supplement_artifact_sha256="a" * 64,
        )


def test_committed_r01_defaults_name_the_registered_artifacts() -> None:
    module = _builder()
    assert module.DEFAULT_ROSTER == REPO / "docs/receipts/rosters/slurp-stage3-construction-r01.json"
    assert module.DEFAULT_RUNTIME_VIEW == (
        REPO / "configs/dataset/slurp-speech-native-stage3-construction-r01.json"
    )
    assert module.DEFAULT_OUTPUT == (
        REPO / "docs/receipts/artifacts/d1-slurp-stage3-construction-r01.json"
    )
    assert module.DEFAULT_SAMPLE_ID_PREFIX == "slurp:train:"
    assert module.DEFAULT_ROSTER.is_file()
    assert module.DEFAULT_RUNTIME_VIEW.is_file()


def test_committed_r01_fragment_pins_the_committed_supplement() -> None:
    """The shipped fragment names the shipped receipt, by path and by bytes."""

    module = _builder()
    view = json.loads(module.DEFAULT_RUNTIME_VIEW.read_text(encoding="utf-8"))
    supplement_relpath = view["d1_media_supplement"]
    assert supplement_relpath == "receipts/artifacts/d1-slurp-stage3-construction-r01.json"
    artifact = REPO / "docs" / supplement_relpath
    assert view["d1_media_supplement_sha256"] == module.sha256_file(artifact)
    supplement = json.loads(artifact.read_text(encoding="utf-8"))
    assert view["d1_manifest_sha256"] == supplement["manifest_sha256"]
    assert supplement["manifest_sha256"] == module.canonical_sha256(supplement["manifest"])
    assert view["source_binding_sha256"] == supplement["source_binding_sha256"]
    unsigned = {key: value for key, value in view.items() if key != "runtime_view_sha256"}
    assert view["runtime_view_sha256"] == module.canonical_sha256(unsigned)
    roster = json.loads(module.DEFAULT_ROSTER.read_text(encoding="utf-8"))
    assert supplement["source_binding_sha256"] == module.canonical_sha256(roster)
    # R01 is all-TRAIN and base D1 records no TRAIN id: nothing was skipped.
    assert supplement["count"] == view["count"]
    assert {entry["id"] for entry in supplement["manifest"]} == {
        item["sample_id"] for item in view["items"]
    }
