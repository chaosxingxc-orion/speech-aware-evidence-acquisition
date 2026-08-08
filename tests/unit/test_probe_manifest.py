"""Unit tests for the probe-protocol manifest builder (P0.C)."""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.reproduction.manifest import (
    PROBE_MANIFEST_VERSION,
    PROBES,
    build_manifest,
)


@pytest.fixture()
def templates_dir(tmp_path):
    referenced = {
        template
        for probe in PROBES.values()
        for templates in probe["arms"].values()
        for template in templates
    }
    for name in referenced:
        (tmp_path / name).write_bytes(f"template body of {name}\n".encode())
    return tmp_path


def test_manifest_hashes_every_referenced_template(templates_dir):
    manifest = build_manifest(templates_dir)
    assert manifest["manifest_version"] == PROBE_MANIFEST_VERSION
    for probe in PROBES.values():
        for templates in probe["arms"].values():
            for name in templates:
                expected = hashlib.sha256(
                    (templates_dir / name).read_bytes()
                ).hexdigest()
                assert manifest["templates"][name]["sha256"] == expected


def test_manifest_carries_probe_specs_verbatim(templates_dir):
    manifest = build_manifest(templates_dir)
    assert manifest["probes"] == PROBES


def test_missing_referenced_template_fails_closed(templates_dir):
    first = next(
        template
        for probe in PROBES.values()
        for templates in probe["arms"].values()
        for template in templates
    )
    (templates_dir / first).unlink()
    with pytest.raises(FileNotFoundError):
        build_manifest(templates_dir)


def test_manifest_is_json_serializable_and_deterministic(templates_dir):
    first = json.dumps(build_manifest(templates_dir), sort_keys=True)
    second = json.dumps(build_manifest(templates_dir), sort_keys=True)
    assert first == second


def test_written_manifest_bytes_are_lf_only_on_every_platform(templates_dir, tmp_path):
    """The manifest's on-disk bytes must equal its git blob bytes (LF), because
    the ExecutionPlan protocol hash binds to them — CRLF translation on
    Windows would silently change the hash authority."""
    from speech_aware_evidence_acquisition.reproduction.manifest import write_manifest

    out = tmp_path / "manifest.json"
    write_manifest(templates_dir, out)
    assert b"\r" not in out.read_bytes()
