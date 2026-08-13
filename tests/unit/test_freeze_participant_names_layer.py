"""Unit tests for ``scripts/freeze_participant_names_layer.py`` (deliverable
2, ``conec-names`` gate-closure incident, 2026-08-13): schema equality
against a hand-built expected object, proving the digest recipe this script
reuses from ``data.identity`` (``_dir_layer``/``layer_report``) produces
EXACTLY the same shape as the sibling ``e21_contexts`` layer already frozen
in ``docs/receipts/artifacts/d1-identity.json``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "freeze_participant_names_layer.py"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location(
        "freeze_participant_names_layer", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_participant_names_layer_matches_hand_built_schema(tmp_path, script):
    """Schema equality with a hand-built expected object (deliverable 3):
    every field -- count, ids_sha256, manifest, manifest_sha256,
    total_bytes, excluded_non_layer_files -- computed independently here by
    the SAME formulas data.identity.Layer documents, then compared for
    exact equality against the script's own output."""

    names_dir = tmp_path / "participant_names"
    names_dir.mkdir()
    entries = {
        "4320211": b"Jane Doe - CEO\nJohn Roe - CFO\n",
        "4330115": b"Alice Smith - COO\n",
    }
    for sample_id, content in entries.items():
        (names_dir / f"{sample_id}.names.txt").write_bytes(content)
    # A non-.names.txt entry, mirroring e21_contexts' own participant_names/
    # pdfs extras -- proves excluded_non_layer_files is populated exactly
    # the way the sibling layer's own entry is.
    (names_dir / "README.txt").write_text("not a names file\n", encoding="utf-8")

    fragment = script.build_participant_names_layer(names_dir)

    expected_manifest = sorted(
        (
            {"id": sample_id, "bytes": len(content), "sha256": _sha(content)}
            for sample_id, content in entries.items()
        ),
        key=lambda entry: entry["id"],
    )
    expected_ids_sha256 = _sha("\n".join(sorted(entries)).encode("utf-8"))
    expected_manifest_sha256 = _sha(
        "\n".join(
            f"{entry['id']},{entry['bytes']},{entry['sha256']}" for entry in expected_manifest
        ).encode("utf-8")
    )
    expected = {
        "e21_participant_names": {
            "count": len(entries),
            "ids_sha256": expected_ids_sha256,
            "total_bytes": sum(len(content) for content in entries.values()),
            "manifest_sha256": expected_manifest_sha256,
            "manifest": expected_manifest,
            "excluded_non_layer_files": ["README.txt"],
        }
    }
    assert fragment == expected


def test_schema_matches_sibling_e21_contexts_layer_keys(tmp_path, script):
    """The real e21_contexts layer in d1-identity.json carries exactly:
    count, excluded_non_layer_files, ids_sha256, manifest, manifest_sha256,
    total_bytes (inspected directly). build_participant_names_layer's own
    output -- when the directory holds a non-layer entry, matching
    e21_contexts' own shape -- must carry the identical key set."""

    names_dir = tmp_path / "participant_names"
    names_dir.mkdir()
    (names_dir / "4320211.names.txt").write_bytes(b"Jane Doe - CEO\n")
    (names_dir / "extra_dir").mkdir()

    fragment = script.build_participant_names_layer(names_dir)
    layer = fragment["e21_participant_names"]
    d1_identity_path = REPO_ROOT / "docs" / "receipts" / "artifacts" / "d1-identity.json"
    real_document = json.loads(d1_identity_path.read_text(encoding="utf-8"))
    real_e21_contexts_keys = set(
        real_document["carriers"]["conec"]["layers"]["e21_contexts"].keys()
    )
    assert set(layer.keys()) == real_e21_contexts_keys


def test_no_extras_omits_excluded_non_layer_files(tmp_path, script):
    """``layer_report`` only adds ``excluded_non_layer_files`` when there
    are any -- proven directly rather than assumed."""

    names_dir = tmp_path / "participant_names"
    names_dir.mkdir()
    (names_dir / "4320211.names.txt").write_bytes(b"Jane Doe - CEO\n")

    fragment = script.build_participant_names_layer(names_dir)
    assert "excluded_non_layer_files" not in fragment["e21_participant_names"]


def test_deterministic_across_repeated_calls(tmp_path, script):
    names_dir = tmp_path / "participant_names"
    names_dir.mkdir()
    (names_dir / "4320211.names.txt").write_bytes(b"Jane Doe - CEO\n")
    (names_dir / "4330115.names.txt").write_bytes(b"Alice Smith - COO\n")

    first = script.build_participant_names_layer(names_dir)
    second = script.build_participant_names_layer(names_dir)
    assert first == second


def test_missing_directory_raises_identity_error(tmp_path, script):
    with pytest.raises(script.IdentityError, match="directory missing"):
        script.build_participant_names_layer(tmp_path / "does-not-exist")


def test_cli_never_writes_to_d1_identity_json(tmp_path, script, capsys):
    """The generator prints to stdout / ``--write-fragment`` only -- it must
    never touch ``docs/receipts/artifacts/d1-identity.json`` itself (the
    coordinator inserts surgically, module docstring's "encoding
    discipline")."""

    names_dir = tmp_path / "participant_names"
    names_dir.mkdir()
    (names_dir / "4320211.names.txt").write_bytes(b"Jane Doe - CEO\n")
    fragment_path = tmp_path / "fragment.json"
    d1_identity_path = REPO_ROOT / "docs" / "receipts" / "artifacts" / "d1-identity.json"
    before = d1_identity_path.read_bytes()

    exit_code = script.main(
        [
            "--participant-names-dir",
            str(names_dir),
            "--write-fragment",
            str(fragment_path),
        ]
    )

    assert exit_code == 0
    assert d1_identity_path.read_bytes() == before
    assert fragment_path.is_file()
    written = json.loads(fragment_path.read_text(encoding="utf-8"))
    assert written == script.build_participant_names_layer(names_dir)

    captured = capsys.readouterr()
    assert json.loads(captured.out) == written


def test_cli_missing_directory_exits_nonzero_without_traceback(tmp_path, script, capsys):
    exit_code = script.main(["--participant-names-dir", str(tmp_path / "absent")])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "directory missing" in captured.err
