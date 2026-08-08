"""Unit tests for the probe-protocol manifest builder (P0.C + sample binding)."""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.reproduction.manifest import (
    PROBE_MANIFEST_VERSION,
    PROBES,
    build_manifest,
)
from speech_aware_evidence_acquisition.reproduction.sampling import split_identity_hash


@pytest.fixture()
def templates_dir(tmp_path):
    referenced = {
        template
        for probe in PROBES.values()
        for templates in probe["arms"].values()
        for template in templates
    }
    templates = tmp_path / "templates"
    templates.mkdir()
    for name in referenced:
        (templates / name).write_bytes(f"template body of {name}\n".encode())
    return templates


@pytest.fixture()
def receipts_dir(tmp_path):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    for probe_name, probe in PROBES.items():
        receipt_name = probe.get("sample_receipt")
        if receipt_name is None:
            continue
        items = [
            {"key": f"{probe_name}:item:{index:04d}"} for index in range(3)
        ]
        payload = {
            "probe": probe_name,
            "seed": 20260807,
            "items": items,
            "split_identity_hash": split_identity_hash([item["key"] for item in items]),
            "split_role": "discovery",
        }
        (receipts / receipt_name).write_text(
            json.dumps(payload), encoding="utf-8", newline="\n"
        )
    return receipts


def test_manifest_hashes_every_referenced_template(templates_dir, receipts_dir):
    manifest = build_manifest(templates_dir, receipts_dir)
    assert manifest["manifest_version"] == PROBE_MANIFEST_VERSION
    for probe in PROBES.values():
        for templates in probe["arms"].values():
            for name in templates:
                expected = hashlib.sha256(
                    (templates_dir / name).read_bytes()
                ).hexdigest()
                assert manifest["templates"][name]["sha256"] == expected


def test_manifest_carries_probe_specs_verbatim(templates_dir, receipts_dir):
    manifest = build_manifest(templates_dir, receipts_dir)
    assert manifest["probes"] == PROBES


def test_missing_referenced_template_fails_closed(templates_dir, receipts_dir):
    first = next(
        template
        for probe in PROBES.values()
        for templates in probe["arms"].values()
        for template in templates
    )
    (templates_dir / first).unlink()
    with pytest.raises(FileNotFoundError):
        build_manifest(templates_dir, receipts_dir)


def test_manifest_is_json_serializable_and_deterministic(templates_dir, receipts_dir):
    first = json.dumps(build_manifest(templates_dir, receipts_dir), sort_keys=True)
    second = json.dumps(build_manifest(templates_dir, receipts_dir), sort_keys=True)
    assert first == second


def test_written_manifest_bytes_are_lf_only_on_every_platform(
    templates_dir, receipts_dir, tmp_path
):
    """The manifest's on-disk bytes must equal its git blob bytes (LF), because
    the ExecutionPlan protocol hash binds to them — CRLF translation on
    Windows would silently change the hash authority."""
    from speech_aware_evidence_acquisition.reproduction.manifest import write_manifest

    out = tmp_path / "manifest.json"
    write_manifest(templates_dir, receipts_dir, out)
    assert b"\r" not in out.read_bytes()


class TestSampleBinding:
    """Point of the samples section: ONE sampling event per carrier, verified
    and bound into the manifest; every later experiment resolves its items
    through this binding, never through a fresh draw."""

    def test_every_probe_with_a_receipt_is_bound_with_its_verified_hash(
        self, templates_dir, receipts_dir
    ):
        manifest = build_manifest(templates_dir, receipts_dir)
        for probe_name, probe in PROBES.items():
            receipt_name = probe.get("sample_receipt")
            if receipt_name is None:
                assert probe_name not in manifest["samples"]
                continue
            bound = manifest["samples"][probe_name]
            payload = json.loads((receipts_dir / receipt_name).read_text())
            assert bound["receipt"] == receipt_name
            assert bound["split_identity_hash"] == payload["split_identity_hash"]
            assert bound["n_items"] == len(payload["items"])
            assert bound["seed"] == payload["seed"]
            assert bound["split_role"] == payload["split_role"]

    def test_tampered_receipt_hash_fails_closed(self, templates_dir, receipts_dir):
        probe_name, probe = next(
            (name, spec) for name, spec in PROBES.items() if spec.get("sample_receipt")
        )
        path = receipts_dir / probe["sample_receipt"]
        payload = json.loads(path.read_text())
        payload["items"].append({"key": "smuggled:item"})
        path.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
        with pytest.raises(ValueError, match="split_identity_hash"):
            build_manifest(templates_dir, receipts_dir)

    def test_missing_receipt_file_fails_closed(self, templates_dir, receipts_dir):
        probe = next(spec for spec in PROBES.values() if spec.get("sample_receipt"))
        (receipts_dir / probe["sample_receipt"]).unlink()
        with pytest.raises(FileNotFoundError):
            build_manifest(templates_dir, receipts_dir)

    def test_manifest_states_the_sample_once_policy(self, templates_dir, receipts_dir):
        manifest = build_manifest(templates_dir, receipts_dir)
        assert "sampled exactly once" in manifest["sampling_policy"]


class TestServerArgs:
    """2026-08-08: the first real smoke hit `56032 tokens > n_ctx 4096` — the
    spawn argv carried no context/offload flags. Server args now live in the
    MODEL config (so they are config-hash → protocol-hash bound, never an
    ad-hoc operator flag) and smoke passes them to start_session."""

    def test_absent_key_means_no_extra_argv(self):
        from speech_aware_evidence_acquisition.core.driver.smoke import _server_args

        assert _server_args({"base_url": "http://127.0.0.1:8080"}) == []

    def test_list_is_stringified(self):
        from speech_aware_evidence_acquisition.core.driver.smoke import _server_args

        assert _server_args({"server_args": ["-c", 65536, "-fa"]}) == ["-c", "65536", "-fa"]

    def test_non_list_is_refused(self):
        from speech_aware_evidence_acquisition.core.driver.smoke import _server_args

        with pytest.raises(ValueError, match="server_args"):
            _server_args({"server_args": "-c 65536"})
