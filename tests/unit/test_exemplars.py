"""Acoustic exemplar banks (core.exemplars): the exemplar_manifest_id
key-legality matrix, manifest loading/verification, and per-sample bank
resolution (deliverables 1/2 of the M-C-prime exemplar-bank wiring)."""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.exemplars import (
    EXEMPLAR_MANIFEST_SCHEMA,
    ExemplarError,
    assert_exemplar_manifest_id_legal,
    load_exemplar_manifest,
    resolve_exemplar_bank,
    resolve_exemplar_manifest_id,
)


def _write_wav(root, manifest_id, sample_id, term, content: bytes):
    path = root / "derived" / "exemplar-pairs" / manifest_id / sample_id / f"{term}.wav"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _write_manifest(root, manifest_id, samples: dict, *, schema=EXEMPLAR_MANIFEST_SCHEMA):
    path = root / "derived" / "exemplar-pairs" / manifest_id / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"samples": samples}
    if schema is not None:
        document["schema"] = schema
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


class TestResolveExemplarManifestId:
    def test_absent_is_none(self):
        assert resolve_exemplar_manifest_id({}) is None

    def test_valid_value_resolves_verbatim(self):
        assert resolve_exemplar_manifest_id({"exemplar_manifest_id": "mc2-v1"}) == "mc2-v1"

    def test_empty_string_refuses(self):
        with pytest.raises(ExemplarError, match="exemplar_manifest_id"):
            resolve_exemplar_manifest_id({"exemplar_manifest_id": ""})

    @pytest.mark.parametrize("bad", [7, 1.5, True, False, None, ["mc2-v1"]])
    def test_non_string_refuses(self, bad):
        with pytest.raises(ExemplarError, match="exemplar_manifest_id"):
            resolve_exemplar_manifest_id({"exemplar_manifest_id": bad})


class TestAssertExemplarManifestIdLegal:
    def test_absent_key_is_fine_regardless_of_prompt_order(self):
        assert_exemplar_manifest_id_legal({})
        assert_exemplar_manifest_id_legal({"prompt_order": "system-instruction-v1"})
        assert_exemplar_manifest_id_legal({"prompt_order": "evidence-first-system-v2"})

    def test_accepted_with_v3_prompt_order(self):
        assert_exemplar_manifest_id_legal(
            {"exemplar_manifest_id": "mc2-v1", "prompt_order": "evidence-first-system-v3"}
        )

    def test_refused_without_prompt_order_declared(self):
        """Absent prompt_order resolves to the transport's own default
        ("system-instruction-v1"), not a silent pass."""

        with pytest.raises(ExemplarError, match="prompt_order"):
            assert_exemplar_manifest_id_legal({"exemplar_manifest_id": "mc2-v1"})

    @pytest.mark.parametrize(
        "prompt_order", ["system-instruction-v1", "evidence-first-system-v2", "typo-order"]
    )
    def test_refused_with_any_non_v3_prompt_order(self, prompt_order):
        with pytest.raises(ExemplarError, match="prompt_order"):
            assert_exemplar_manifest_id_legal(
                {"exemplar_manifest_id": "mc2-v1", "prompt_order": prompt_order}
            )

    def test_refused_even_with_an_empty_manifest_id_value(self):
        with pytest.raises(ExemplarError, match="exemplar_manifest_id"):
            assert_exemplar_manifest_id_legal({"exemplar_manifest_id": ""})


class TestLoadExemplarManifest:
    def test_manifest_missing_fails_closed(self, tmp_path):
        with pytest.raises(ExemplarError, match="missing"):
            load_exemplar_manifest(tmp_path, "mc2-v1")

    def test_wrong_schema_fails_closed(self, tmp_path):
        _write_manifest(tmp_path, "mc2-v1", {}, schema="not-the-right-schema")
        with pytest.raises(ExemplarError, match="schema"):
            load_exemplar_manifest(tmp_path, "mc2-v1")

    def test_missing_schema_fails_closed(self, tmp_path):
        _write_manifest(tmp_path, "mc2-v1", {}, schema=None)
        with pytest.raises(ExemplarError, match="schema"):
            load_exemplar_manifest(tmp_path, "mc2-v1")

    def test_found_entry_loads_and_verifies_sha256(self, tmp_path):
        content = b"exemplar-audio-bytes"
        _write_wav(tmp_path, "mc2-v1", "4000001", "alpha", content)
        _write_manifest(
            tmp_path,
            "mc2-v1",
            {
                "4000001": {
                    "alpha": {
                        "term": "alpha",
                        "status": "found",
                        "span_sha256": hashlib.sha256(content).hexdigest(),
                    }
                }
            },
        )
        manifest = load_exemplar_manifest(tmp_path, "mc2-v1")
        assert manifest.manifest_id == "mc2-v1"
        assert len(manifest.sha256) == 64
        assert manifest.banks["4000001"] == (
            {
                "media_relpath": "derived/exemplar-pairs/mc2-v1/4000001/alpha.wav",
                "label": "alpha",
            },
        )

    def test_alignment_rejected_and_no_cross_call_entries_are_excluded(self, tmp_path):
        _write_manifest(
            tmp_path,
            "mc2-v1",
            {
                "4000001": {
                    "beta": {
                        "term": "beta",
                        "status": "alignment-rejected",
                        "reject_reason": "too long",
                    },
                    "gamma": {"term": "gamma", "status": "no-cross-call-occurrence"},
                }
            },
        )
        manifest = load_exemplar_manifest(tmp_path, "mc2-v1")
        assert manifest.banks["4000001"] == ()

    def test_found_entry_missing_wav_fails_closed(self, tmp_path):
        _write_manifest(
            tmp_path,
            "mc2-v1",
            {"4000001": {"alpha": {"term": "alpha", "status": "found", "span_sha256": "0" * 64}}},
        )
        with pytest.raises(ExemplarError, match="missing"):
            load_exemplar_manifest(tmp_path, "mc2-v1")

    def test_found_entry_sha256_mismatch_fails_closed(self, tmp_path):
        _write_wav(tmp_path, "mc2-v1", "4000001", "alpha", b"real-bytes")
        _write_manifest(
            tmp_path,
            "mc2-v1",
            {"4000001": {"alpha": {"term": "alpha", "status": "found", "span_sha256": "0" * 64}}},
        )
        with pytest.raises(ExemplarError, match="mismatch"):
            load_exemplar_manifest(tmp_path, "mc2-v1")

    def test_found_entry_missing_span_sha256_fails_closed(self, tmp_path):
        _write_wav(tmp_path, "mc2-v1", "4000001", "alpha", b"real-bytes")
        _write_manifest(
            tmp_path, "mc2-v1", {"4000001": {"alpha": {"term": "alpha", "status": "found"}}}
        )
        with pytest.raises(ExemplarError, match="span_sha256"):
            load_exemplar_manifest(tmp_path, "mc2-v1")

    def test_unknown_status_fails_closed(self, tmp_path):
        _write_manifest(
            tmp_path, "mc2-v1", {"4000001": {"alpha": {"term": "alpha", "status": "mystery"}}}
        )
        with pytest.raises(ExemplarError, match="status"):
            load_exemplar_manifest(tmp_path, "mc2-v1")

    def test_mixed_sample_keeps_only_found_terms_sorted_by_term(self, tmp_path):
        content_a = b"alpha-bytes"
        content_c = b"charlie-bytes"
        _write_wav(tmp_path, "mc2-v1", "4000001", "alpha", content_a)
        _write_wav(tmp_path, "mc2-v1", "4000001", "charlie", content_c)
        _write_manifest(
            tmp_path,
            "mc2-v1",
            {
                "4000001": {
                    "charlie": {
                        "term": "charlie",
                        "status": "found",
                        "span_sha256": hashlib.sha256(content_c).hexdigest(),
                    },
                    "bravo": {"term": "bravo", "status": "alignment-rejected"},
                    "alpha": {
                        "term": "alpha",
                        "status": "found",
                        "span_sha256": hashlib.sha256(content_a).hexdigest(),
                    },
                }
            },
        )
        manifest = load_exemplar_manifest(tmp_path, "mc2-v1")
        assert [pair["label"] for pair in manifest.banks["4000001"]] == ["alpha", "charlie"]

    def test_manifest_with_no_samples_at_all_loads_fine(self, tmp_path):
        _write_manifest(tmp_path, "mc2-v1", {})
        manifest = load_exemplar_manifest(tmp_path, "mc2-v1")
        assert manifest.banks == {}


class TestResolveExemplarBank:
    def test_sample_absent_from_manifest_is_an_empty_bank(self, tmp_path):
        _write_manifest(tmp_path, "mc2-v1", {})
        manifest = load_exemplar_manifest(tmp_path, "mc2-v1")
        assert resolve_exemplar_bank(manifest, "0000000") == ()

    def test_sample_with_only_rejected_terms_is_an_empty_bank(self, tmp_path):
        _write_manifest(
            tmp_path,
            "mc2-v1",
            {"4000001": {"alpha": {"term": "alpha", "status": "no-cross-call-occurrence"}}},
        )
        manifest = load_exemplar_manifest(tmp_path, "mc2-v1")
        assert resolve_exemplar_bank(manifest, "4000001") == ()

    def test_sample_with_a_found_term_returns_its_pair(self, tmp_path):
        content = b"exemplar-audio-bytes"
        _write_wav(tmp_path, "mc2-v1", "4000001", "alpha", content)
        _write_manifest(
            tmp_path,
            "mc2-v1",
            {
                "4000001": {
                    "alpha": {
                        "term": "alpha",
                        "status": "found",
                        "span_sha256": hashlib.sha256(content).hexdigest(),
                    }
                }
            },
        )
        manifest = load_exemplar_manifest(tmp_path, "mc2-v1")
        bank = resolve_exemplar_bank(manifest, "4000001")
        assert bank == (
            {
                "media_relpath": "derived/exemplar-pairs/mc2-v1/4000001/alpha.wav",
                "label": "alpha",
            },
        )
