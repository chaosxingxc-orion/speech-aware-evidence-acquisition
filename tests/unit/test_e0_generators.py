"""E0 generators produce truthful artifacts and the real gate accepts what they bind."""

import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import (
    MODEL_LOCK_KEY,
    RUNTIME_RECEIPT_SCHEMA_V3,
    ExecutionPlan,
    FrozenCoreGate,
    GateClosed,
)
from speech_aware_evidence_acquisition.e0.artifacts import (
    ARTIFACTS_SUBDIR,
    REPO_ROOT,
    sha256_file,
    write_json_artifact,
)
from speech_aware_evidence_acquisition.e0.d1_identity import (
    build_d1,
    build_d1_media_supplement,
    build_speech_native_engineering_gate_view,
    build_speech_native_probe_receipt,
    build_speech_native_runtime_view,
)
from speech_aware_evidence_acquisition.contracts import (
    CONSTRUCTION_VISIBLE_ARMS,
    CONSTRUCTION_VISIBLE_FIELD,
)
from speech_aware_evidence_acquisition.e0.d2_leakage import (
    ARM_VISIBLE_FIELDS,
    build_d2,
    excluded_lock_keys,
)
from speech_aware_evidence_acquisition.e0.d3_scoring import build_d3
from speech_aware_evidence_acquisition.e0.d4_trace import build_d4
from speech_aware_evidence_acquisition.e0.generate import _close
from speech_aware_evidence_acquisition.e0.runtime_receipt import (
    ArtifactError,
    build_runtime_receipt,
)

from conftest import (
    AUDIO2TOOL_D1_SAMPLE_ID,
    E21_IDS,
    SLURP_D1_SAMPLE_ID,
    SLURP_D1_SLURP_ID,
    SUBSET10_IDS,
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class TestD1:
    def _build(self, synthetic_world):
        return build_d1(
            synthetic_world.lock_path,
            synthetic_world.data_root,
            repo_root=synthetic_world.repo_root,
        )

    def test_closure_on_clean_world(self, synthetic_world):
        artifact = self._build(synthetic_world)
        carriers = artifact["carriers"]
        assert carriers["earnings21-original"]["sample_count"] == len(E21_IDS)
        assert carriers["earnings22-original"]["sample_count"] == 12
        for name, report in carriers.items():
            if name in ("slurp", "audio2tool"):
                continue
            for fact in report["cross_layer_relations"]:
                if fact["right"] == "subset10_media":
                    assert fact["relation"] == "right_subset_of_left"
                else:
                    assert fact["relation"] == "equal"
        assert "license_facts" in carriers["conec"]
        # Bounded discovery-probe carriers (2026-08-15 owner amendment):
        # single-layer media identity, admitted alongside the three core
        # carriers so verify_media_identity('slurp')/('audio2tool') accept.
        slurp_media = carriers["slurp"]["layers"]["media"]["manifest"]
        assert [entry["id"] for entry in slurp_media] == [SLURP_D1_SAMPLE_ID]
        assert len(slurp_media[0]["sha256"]) == 64
        audio2tool_media = carriers["audio2tool"]["layers"]["media"]["manifest"]
        assert [entry["id"] for entry in audio2tool_media] == [AUDIO2TOOL_D1_SAMPLE_ID]
        assert len(audio2tool_media[0]["sha256"]) == 64


class TestD1MediaSupplement:
    @staticmethod
    def _binding(tmp_path):
        items = [
            {
                "sample_id": "slurp:train:000001:q1",
                "media_relpath": "datasets/slurp/slurp_real/q1.flac",
                "value_label": "alarm",
            },
            {
                "sample_id": "slurp:train:000002:q2",
                "media_relpath": "datasets/slurp/slurp_real/q2.flac",
                "value_label": "audio",
            },
        ]
        engineering_identity = {
            "schema": "saea-speech-native-split-v1",
            "name": "ENG-GATE8",
            "seed": 7,
            "sample_ids": [item["sample_id"] for item in items],
        }
        unsigned = {
            "schema": "saea-speech-native-binding-v1",
            "engineering_gate": {
                **engineering_identity,
                "split_identity_hash": _sha(
                    json.dumps(
                        engineering_identity,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ),
                "items": [
                    {
                        "sample_id": item["sample_id"],
                        "media_relpath": item["media_relpath"],
                    }
                    for item in items
                ],
            },
            "splits": {
                "OPT-A36": {"items": items},
                "OPT-B18": {"items": []},
                "GATE18": {"items": []},
            },
            "key_material": [
                {
                    "audio_key_source_sample_id": "slurp:train:000003:k1",
                    "sources": [
                        {
                            "sample_id": "slurp:train:000003:k1",
                            "media_relpath": "datasets/slurp/slurp_real/k1.flac",
                            "sentence": "text must not enter the supplement",
                        }
                    ],
                }
            ],
        }
        canonical = json.dumps(
            unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        binding = {**unsigned, "binding_sha256": _sha(canonical)}
        path = tmp_path / "binding.json"
        path.write_text(json.dumps(binding), encoding="utf-8")
        return path

    def test_bounded_supplement_hashes_media_in_parallel_without_copying_text(self, tmp_path):
        binding_path = self._binding(tmp_path)
        data_root = tmp_path / "data"
        media_root = data_root / "datasets/slurp/slurp_real"
        media_root.mkdir(parents=True)
        for sample in ("q1", "q2", "k1"):
            (media_root / f"{sample}.flac").write_bytes(sample.encode() * 100)
        parent_d1 = tmp_path / "d1-identity.json"
        parent_d1.write_bytes(b"immutable-parent-d1")
        lock = threading.Lock()
        active = 0
        peak = 0

        def media_probe(path):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.02)
            try:
                raw = path.read_bytes()
                return len(raw), _sha(raw), 1.25, 16000
            finally:
                with lock:
                    active -= 1

        supplement = build_d1_media_supplement(
            binding_path=binding_path,
            data_root=data_root,
            parent_d1_path=parent_d1,
            workers=3,
            expected_query_count=2,
            expected_audio_key_count=1,
            media_probe=media_probe,
        )

        assert supplement["count"] == 3
        assert 2 <= peak <= 3
        by_id = {entry["id"]: entry for entry in supplement["manifest"]}
        assert by_id["slurp:train:000001:q1"]["roles"] == ["query"]
        assert by_id["slurp:train:000003:k1"]["roles"] == ["audio_key"]
        assert "text must not enter" not in json.dumps(supplement)
        assert supplement["parent_d1_sha256"] == _sha(parent_d1.read_bytes())
        view = build_speech_native_engineering_gate_view(
            binding_path=binding_path,
            supplement=supplement,
            supplement_artifact_sha256="c" * 64,
        )
        assert view["count"] == 2
        assert view["split_identity_hash"] == json.loads(
            binding_path.read_text(encoding="utf-8")
        )["engineering_gate"]["split_identity_hash"]
        assert [item["packet_id"] for item in view["items"]] == [
            "slurp/train/000001/q1",
            "slurp/train/000002/q2",
        ]
        assert all(
            set(item)
            == {
                "sample_id",
                "media_relpath",
                "audio_sha256",
                "audio_seconds",
                "sample_rate_hz",
                "packet_id",
            }
            for item in view["items"]
        )
        assert "text must not enter" not in json.dumps(view)

    def test_supplement_refuses_binding_hash_drift(self, tmp_path):
        binding_path = self._binding(tmp_path)
        document = json.loads(binding_path.read_text(encoding="utf-8"))
        document["splits"]["OPT-A36"]["items"][0]["sample_id"] = (
            "slurp:train:000004:changed"
        )
        binding_path.write_text(json.dumps(document), encoding="utf-8")
        parent_d1 = tmp_path / "d1-identity.json"
        parent_d1.write_bytes(b"immutable-parent-d1")
        with pytest.raises(Exception, match="binding SHA-256"):
            build_d1_media_supplement(
                binding_path=binding_path,
                data_root=tmp_path,
                parent_d1_path=parent_d1,
                expected_query_count=2,
                expected_audio_key_count=1,
            )

    def test_runtime_view_generalizes_existing_split_without_exposing_gold(self, tmp_path):
        binding_path = self._binding(tmp_path)
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        split = binding["splits"]["OPT-A36"]
        identity = {
            "schema": "saea-speech-native-split-v1",
            "name": "OPT-A36",
            "seed": 7,
            "sample_ids": [item["sample_id"] for item in split["items"]],
        }
        split.update(
            {
                **identity,
                "split_identity_hash": _sha(
                    json.dumps(
                        identity,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ),
            }
        )
        unsigned_binding = {
            key: value for key, value in binding.items() if key != "binding_sha256"
        }
        binding["binding_sha256"] = _sha(
            json.dumps(
                unsigned_binding,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        binding_path.write_text(json.dumps(binding), encoding="utf-8")
        supplement = {
            "source_binding_sha256": binding["binding_sha256"],
            "manifest_sha256": "d" * 64,
            "manifest": [
                {
                    "id": item["sample_id"],
                    "media_relpath": item["media_relpath"],
                    "sha256": str(index) * 64,
                    "audio_seconds": 1.0,
                    "sample_rate_hz": 16000,
                }
                for index, item in enumerate(split["items"], start=1)
            ],
        }

        view = build_speech_native_runtime_view(
            binding_path=binding_path,
            supplement=supplement,
            supplement_artifact_sha256="c" * 64,
            selection_name="OPT-A36",
            expected_count=2,
        )
        receipt = build_speech_native_probe_receipt(view)

        assert view["schema"] == "saea-speech-native-runtime-view-v1"
        assert view["split_name"] == "OPT-A36"
        assert view["split_identity_hash"] == split["split_identity_hash"]
        assert view["count"] == 2
        serialized = json.dumps(view)
        assert "value_label" not in serialized
        assert "normalized_sentence" not in serialized
        assert receipt["split_role"] == "discovery"
        assert [item["id"] for item in receipt["items"]] == identity["sample_ids"]
        assert receipt["source_runtime_view_sha256"] == view["runtime_view_sha256"]

    def test_supplement_and_runtime_view_accept_successor_discovery_split(self, tmp_path):
        binding_path = self._binding(tmp_path)
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        extension_items = [
            {
                "sample_id": f"slurp:train:00000{index}:x{index}",
                "media_relpath": f"datasets/slurp/slurp_real/x{index}.flac",
                "value_label": "alarm",
            }
            for index in (4, 5)
        ]
        identity = {
            "schema": "saea-speech-native-split-v1",
            "name": "DISCOVERY-X2",
            "seed": 11,
            "sample_ids": [item["sample_id"] for item in extension_items],
        }
        binding["splits"]["DISCOVERY-X2"] = {
            **identity,
            "split_identity_hash": _sha(
                json.dumps(
                    identity,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ),
            "items": extension_items,
        }
        unsigned = {
            key: value for key, value in binding.items() if key != "binding_sha256"
        }
        binding["binding_sha256"] = _sha(
            json.dumps(
                unsigned,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        binding_path.write_text(json.dumps(binding), encoding="utf-8")
        data_root = tmp_path / "data"
        media_root = data_root / "datasets/slurp/slurp_real"
        media_root.mkdir(parents=True)
        for sample in ("q1", "q2", "x4", "x5", "k1"):
            (media_root / f"{sample}.flac").write_bytes(sample.encode() * 100)
        parent_d1 = tmp_path / "d1-identity.json"
        parent_d1.write_bytes(b"immutable-parent-d1")

        def media_probe(path):
            raw = path.read_bytes()
            return len(raw), _sha(raw), 1.25, 16000

        supplement = build_d1_media_supplement(
            binding_path=binding_path,
            data_root=data_root,
            parent_d1_path=parent_d1,
            workers=2,
            expected_query_count=4,
            expected_audio_key_count=1,
            media_probe=media_probe,
        )
        view = build_speech_native_runtime_view(
            binding_path=binding_path,
            supplement=supplement,
            supplement_artifact_sha256="c" * 64,
            selection_name="DISCOVERY-X2",
            expected_count=2,
            supplement_relpath="receipts/artifacts/d1-speech-native-x2.json",
        )
        receipt = build_speech_native_probe_receipt(view)

        assert supplement["count"] == 5
        assert view["split_name"] == "DISCOVERY-X2"
        assert view["d1_media_supplement"] == (
            "receipts/artifacts/d1-speech-native-x2.json"
        )
        assert receipt["split_role"] == "discovery"


class TestD1ClosureFailures(TestD1):
    def test_layer_drift_refuses_closure(self, synthetic_world):
        (synthetic_world.conec / "earnings21" / "contexts" / "extra_call.txt").write_text(
            "ctx", encoding="utf-8"
        )
        with pytest.raises(Exception, match="invariant violated"):
            self._build(synthetic_world)

    def test_lock_count_disagreement_refuses_closure(self, synthetic_world):
        lock = json.loads(synthetic_world.lock_path.read_text(encoding="utf-8"))
        lock["datasets"][0]["verification"]["main_audio_files"] = 99
        synthetic_world.lock_path.write_text(json.dumps(lock), encoding="utf-8")
        with pytest.raises(Exception, match="disagrees with the umbrella lock"):
            self._build(synthetic_world)

    def test_missing_slurp_devel_media_refuses_closure(self, synthetic_world):
        """The two bounded-discovery-probe carriers are closed with the SAME
        fail-closed discipline as the three core carriers: a caller lacking
        SLURP media data never gets a silently narrower artifact."""

        slurp_flac_dir = synthetic_world.slurp_audio_root / "slurp_real"
        for flac in slurp_flac_dir.glob("*.flac"):
            flac.unlink()
        with pytest.raises(Exception, match="media missing"):
            self._build(synthetic_world)

    def test_missing_audio2tool_receipt_refuses_closure(self, synthetic_world):
        (
            synthetic_world.repo_root
            / "docs"
            / "receipts"
            / "probe-samples"
            / "d1-test-audio2tool-sample.json"
        ).unlink()
        with pytest.raises(Exception, match="audio2tool"):
            self._build(synthetic_world)


class TestD2:
    def test_negative_controls_all_executed(self, synthetic_world):
        artifact = build_d2(synthetic_world.lock_path)
        boundary = artifact["negative_controls"]["boundary_injections"]
        assert boundary["executed"] == 12 * 3
        assert boundary["all_rejected"] is True
        assert artifact["negative_controls"]["trace_axis_smuggling"]["executed"] == 4
        exclusion = artifact["general_audio_exclusion"]
        assert set(exclusion["excluded_lock_keys"]) == set(excluded_lock_keys())
        assert not set(exclusion["excluded_lock_keys"]) & set(
            exclusion["configured_lock_keys"]
        )

    def test_native_tools_arm_is_bare_core_plus_tool_schemas(self, synthetic_world):
        """D1a: "bare-core-native-tools" is a NEW arm, introduced rather than
        mutating the frozen "bare-core" entry -- its own field set is exactly
        bare-core's plus "tool_schemas", nothing dropped and nothing else
        added (module docstring of e0.d2_leakage: growing the arm vocabulary
        means a new key, never appending a field to an existing tuple).

        D1b (2026-09-03, extended, not weakened): the same "own field set
        plus tool_schemas, nothing else" invariant holds for the packet-path
        sibling arm "speech-feature-query-native-tools" introduced alongside
        the rails bridge's own native-tools acceptance
        (rails.core_client.FrozenCoreClient) -- and neither new arm mutates
        any frozen entry the other one, or the base "bare-core"/
        "speech-feature-query" arms, already declared."""

        assert ARM_VISIBLE_FIELDS["bare-core-native-tools"] == (
            *ARM_VISIBLE_FIELDS["bare-core"],
            "tool_schemas",
        )
        assert ARM_VISIBLE_FIELDS["speech-feature-query-native-tools"] == (
            *ARM_VISIBLE_FIELDS["speech-feature-query"],
            "tool_schemas",
        )
        artifact = build_d2(synthetic_world.lock_path)
        arms = artifact["runtime_visible_fields_by_arm"]
        assert arms["bare-core-native-tools"] == {
            "clean_payload_accepted": True,
            "visible_fields": list(ARM_VISIBLE_FIELDS["bare-core-native-tools"]),
        }
        assert arms["speech-feature-query-native-tools"] == {
            "clean_payload_accepted": True,
            "visible_fields": list(ARM_VISIBLE_FIELDS["speech-feature-query-native-tools"]),
        }
        # bare-core and speech-feature-query themselves are untouched by
        # either new arm's existence.
        assert arms["bare-core"]["visible_fields"] == list(ARM_VISIBLE_FIELDS["bare-core"])
        assert arms["speech-feature-query"]["visible_fields"] == list(
            ARM_VISIBLE_FIELDS["speech-feature-query"]
        )

    def test_construction_proposer_arm_is_bare_core_plus_one_gold_field(
        self, synthetic_world
    ):
        """E2.4: "construction-proposer-text" is the ONE arm on which the
        frozen core may see gold, and it is bare-core's own field set plus
        exactly ``construction_targets`` -- a NEW arm, never a mutation of a
        frozen entry."""

        assert ARM_VISIBLE_FIELDS["construction-proposer-text"] == (
            *ARM_VISIBLE_FIELDS["bare-core"],
            CONSTRUCTION_VISIBLE_FIELD,
        )
        artifact = build_d2(synthetic_world.lock_path)
        arms = artifact["runtime_visible_fields_by_arm"]
        assert arms["construction-proposer-text"] == {
            "clean_payload_accepted": True,
            "visible_fields": list(ARM_VISIBLE_FIELDS["construction-proposer-text"]),
        }
        assert arms["bare-core"]["visible_fields"] == list(
            ARM_VISIBLE_FIELDS["bare-core"]
        )

    def test_exactly_the_contract_declared_arms_carry_construction_gold(
        self, synthetic_world
    ):
        """The D2 artifact records the visibility statement it EXECUTED: the
        set of arms declaring ``construction_targets`` equals
        ``contracts.CONSTRUCTION_VISIBLE_ARMS``, and no other arm carries the
        field."""

        artifact = build_d2(synthetic_world.lock_path)
        visibility = artifact["construction_gold_visibility"]
        assert visibility["field"] == CONSTRUCTION_VISIBLE_FIELD
        assert visibility["arms"] == sorted(CONSTRUCTION_VISIBLE_ARMS)
        assert visibility["arms_declaring_the_field"] == sorted(
            CONSTRUCTION_VISIBLE_ARMS
        )
        assert visibility["no_other_arm_declares_it"] is True
        assert "roster_role" in visibility["boundary_argument"]
        carriers = {
            arm
            for arm, fields in ARM_VISIBLE_FIELDS.items()
            if CONSTRUCTION_VISIBLE_FIELD in fields
        }
        assert carriers == set(CONSTRUCTION_VISIBLE_ARMS)

    def test_a_gold_visible_arm_the_contract_does_not_declare_fails_closed(
        self, synthetic_world, monkeypatch
    ):
        """Drift in either direction is refused: an arm that grows the gold
        field without being named in the contract stops the generator, so the
        D2 freeze can never quietly widen who sees gold."""

        monkeypatch.setitem(
            ARM_VISIBLE_FIELDS,
            "sneaky-arm",
            (*ARM_VISIBLE_FIELDS["bare-core"], CONSTRUCTION_VISIBLE_FIELD),
        )
        with pytest.raises(Exception, match="construction-visibility drift"):
            build_d2(synthetic_world.lock_path)

    def test_excluded_keys_come_from_config_not_code(self):
        keys = excluded_lock_keys()
        assert len(keys) == 3
        source_root = (
            Path(__file__).resolve().parents[2] / "src" / "speech_aware_evidence_acquisition"
        )
        for source in source_root.rglob("*.py"):
            text = source.read_text(encoding="utf-8").lower()
            for key in keys:
                assert key.lower() not in text, f"{source.name} hard-codes {key}"


class TestD3:
    def test_golden_vectors_and_source_freeze(self):
        artifact = build_d3()
        assert artifact["golden_vectors"]["all_matched"] is True
        assert artifact["golden_vectors"]["executed"] >= 8
        frozen = artifact["frozen_sources_sha256"]
        scoring_dir = REPO_ROOT / "src" / "speech_aware_evidence_acquisition" / "scoring"
        actual_sources = {
            f"src/speech_aware_evidence_acquisition/scoring/{path.name}"
            for path in scoring_dir.glob("*.py")
        }
        assert set(frozen) == actual_sources, "freeze must cover the whole scoring package"
        for relpath, digest in frozen.items():
            assert digest == sha256_file(REPO_ROOT / relpath), relpath


class TestD4:
    def test_ten_sample_receipt(self, synthetic_world):
        artifact = build_d4(synthetic_world.lock_path, synthetic_world.data_root)
        assert artifact["sample_count"] == 10
        assert [sample["sample_id"] for sample in artifact["samples"]] == sorted(SUBSET10_IDS)
        first = artifact["samples"][0]
        assert {record["channel"] for record in first["trace_records"]} == {
            "OBS",
            "ORG",
            "SUPPLY",
            "USE",
            "COST",
        }
        for record in first["trace_records"]:
            # Receipt carries metadata only: no serialized trace content is embedded.
            assert set(record) == {"channel", "record_id", "payload_keys", "content_sha256"}
            assert record["record_id"].startswith("SAEA-E0-D4/")
            assert len(record["content_sha256"]) == 64
        assert artifact["validations"]["model_calls"] == 0
        assert first["provenance"]["media_sha256"]
        org = next(r for r in first["trace_records"] if r["channel"] == "ORG")
        assert "org_context_files" in org["payload_keys"]
        assert all(key.startswith("org_") for key in org["payload_keys"])


class TestCloseAndGate:
    """The generated closure receipt must satisfy the real FrozenCoreGate."""

    def _generated_receipts(self, synthetic_world, tmp_path) -> Path:
        receipts = tmp_path / "receipts"
        for name, builder in (
            (
                "d1-identity.json",
                lambda: build_d1(
                    synthetic_world.lock_path,
                    synthetic_world.data_root,
                    repo_root=synthetic_world.repo_root,
                ),
            ),
            ("d2-leakage.json", lambda: build_d2(synthetic_world.lock_path)),
            ("d3-scoring.json", build_d3),
            ("d4-trace.json", lambda: build_d4(synthetic_world.lock_path, synthetic_world.data_root)),
        ):
            write_json_artifact(receipts / ARTIFACTS_SUBDIR / name, builder())
        _close(receipts)
        return receipts

    def _model_world(self, synthetic_world, tmp_path) -> tuple[Path, Path, dict]:
        data_root = synthetic_world.data_root
        model_dir = data_root / "models" / MODEL_LOCK_KEY
        model_dir.mkdir(parents=True)
        gguf = b"GGUF fake main model" * 8
        mmproj = b"GGUF fake mmproj" * 4
        (model_dir / "model.gguf").write_bytes(gguf)
        (model_dir / "mmproj.gguf").write_bytes(mmproj)
        lock = json.loads(synthetic_world.lock_path.read_text(encoding="utf-8"))
        lock["models"] = [
            {
                "name": MODEL_LOCK_KEY,
                "local_subdir": f"models/{MODEL_LOCK_KEY}",
                "files": 2,
                "size_bytes": len(gguf) + len(mmproj),
            }
        ]
        synthetic_world.lock_path.write_text(json.dumps(lock), encoding="utf-8")
        runtime_root = tmp_path / "runtime"
        binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"fake-llama-server")
        library = binary.parent / "libfake.so"
        library.write_bytes(b"fake-inference-library")
        runtime = {
            "schema": "saea-runtime-receipt-v2",
            "study": "speech-aware-evidence-acquisition",
            "model_lock_key": MODEL_LOCK_KEY,
            "llama_cpp": {
                "build_commit": "a" * 40,
                "reported_build": "version: 1 (aaaaaaa)",
                "binary_path": "llama.cpp/build/bin/llama-server",
                "binary_bytes": binary.stat().st_size,
                "binary_sha256": _sha(b"fake-llama-server"),
            },
            "gguf_files": [
                {
                    "path": f"models/{MODEL_LOCK_KEY}/mmproj.gguf",
                    "bytes": len(mmproj),
                    "sha256": _sha(mmproj),
                },
                {
                    "path": f"models/{MODEL_LOCK_KEY}/model.gguf",
                    "bytes": len(gguf),
                    "sha256": _sha(gguf),
                },
            ],
            "runtime_libraries": [
                {
                    "path": "llama.cpp/build/bin/libfake.so",
                    "bytes": library.stat().st_size,
                    "sha256": _sha(b"fake-inference-library"),
                }
            ],
        }
        return runtime_root, binary, runtime

    @pytest.mark.requires_wsl2_execution_authority
    def test_generated_receipts_open_and_tampering_recloses(
        self, synthetic_world, tmp_path
    ):
        receipts = self._generated_receipts(synthetic_world, tmp_path)
        runtime_root, _, runtime = self._model_world(synthetic_world, tmp_path)
        (receipts / "runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
        ledger = tmp_path / "ledger.md"
        ledger.write_text(
            "| date | run/experiment id | execution profile | scope | model/tool "
            "| speech carrier + split | split role | split identity hash | consumed "
            "| calls | speech audio seconds | gpu hours | inherited exposure "
            "| artifacts | notes |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
            "| 2026-08-04 | RUN-1 | baseline-reproduction | s | m | earnings21-original dev | dev "
            f"| {'a' * 64} | no | 1 | 60 | 0.1 | none | none | test |\n",
            encoding="utf-8",
        )
        gate = FrozenCoreGate(
            e0_receipt=receipts / "e0-closure.json",
            runtime_receipt=receipts / "runtime.json",
            data_root=synthetic_world.data_root,
            lock_path=synthetic_world.lock_path,
            runtime_root=runtime_root,
            exposure_ledger=ledger,
            # The generated D3 artifact froze the real repo's scoring sources.
            source_root=REPO_ROOT,
        )
        plan = ExecutionPlan(
            run_id="RUN-1",
            execution_profile="baseline-reproduction",
            carrier_lock_key="earnings21-original",
            split_role="dev",
            split_identity_hash="a" * 64,
            planned_model_calls=1,
            planned_gpu_hours=0.1,
            planned_speech_audio_seconds=60,
            protocol_hash="b" * 64,
        )
        gate.assert_model_touch_allowed(plan)

        artifact = receipts / ARTIFACTS_SUBDIR / "d4-trace.json"
        tampered = artifact.read_text(encoding="utf-8").replace(
            '"model_calls": 0', '"model_calls": 1'
        )
        artifact.write_text(tampered, encoding="utf-8")
        with pytest.raises(GateClosed, match="hash drift"):
            gate.assert_model_touch_allowed(plan)

    def test_verify_media_identity_accepts_slurp_and_audio2tool(
        self, synthetic_world, tmp_path
    ):
        """Direct reproduction of the refused-flight probe
        (docs/checks/speech-aware-evidence-acquisition/2026-08-17-pslu-flight/
        launcher/probe_d1.py): D1's own media identity artifact, resolved
        THROUGH the generated E0 closure receipt, now closes over both
        bounded discovery-probe carriers -- ``verify_media_identity`` accepts
        rather than refusing with "D1 identity artifact has no per-sample
        media identity for carrier ...'."""

        receipts = self._generated_receipts(synthetic_world, tmp_path)
        runtime_root, _, runtime = self._model_world(synthetic_world, tmp_path)
        (receipts / "runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
        gate = FrozenCoreGate(
            e0_receipt=receipts / "e0-closure.json",
            runtime_receipt=receipts / "runtime.json",
            data_root=synthetic_world.data_root,
            lock_path=synthetic_world.lock_path,
            runtime_root=runtime_root,
            exposure_ledger=tmp_path / "unused-ledger.md",
            source_root=REPO_ROOT,
        )
        slurp_flac = (
            synthetic_world.slurp_audio_root / "slurp_real" / f"audio-{SLURP_D1_SLURP_ID}.flac"
        )
        gate.verify_media_identity(
            "slurp",
            {
                SLURP_D1_SAMPLE_ID: (
                    str(slurp_flac.relative_to(synthetic_world.data_root)).replace("\\", "/"),
                    # A tiny silent FLAC compresses far below any real MP3
                    # bitrate; a small audio_seconds keeps the implied-kbps
                    # plausibility band happy without touching this test's
                    # real point (D1 byte identity, not bitrate plausibility).
                    0.1,
                )
            },
        )
        a2t_wav = (
            synthetic_world.audio2tool_public
            / "tier1_direct_audios"
            / "query_00001"
            / "turn.wav"
        )
        gate.verify_media_identity(
            "audio2tool",
            {
                AUDIO2TOOL_D1_SAMPLE_ID: (
                    str(a2t_wav.relative_to(synthetic_world.data_root)).replace("\\", "/"),
                    0.5,
                )
            },
        )
        with pytest.raises(GateClosed, match="no D1-recorded media identity"):
            gate.verify_media_identity("slurp", {"slurp:devel:999999:nope": ("x/y.flac", 1.0)})


@pytest.mark.skipif(
    os.name == "nt" or shutil.which("git") is None,
    reason="POSIX git checkout with an executable fake llama-server required",
)
class TestRuntimeReceiptGenerator:
    def _llama_checkout(self, tmp_path: Path) -> Path:
        runtime_root = tmp_path / "runtime"
        llama = runtime_root / "llama.cpp"
        llama.mkdir(parents=True)
        # Real llama.cpp ignores its build tree, which is what lets the built
        # binary postdate the clean commit.
        (llama / ".gitignore").write_text("build/\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(llama)], check=True)
        subprocess.run(["git", "-C", str(llama), "add", "-A"], check=True)
        subprocess.run(
            [
                "git", "-C", str(llama),
                "-c", "user.email=t@example.invalid", "-c", "user.name=t",
                "commit", "-q", "-m", "build",
            ],
            check=True,
        )
        commit = subprocess.run(
            ["git", "-C", str(llama), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        binary = llama / "build" / "bin" / "llama-server"
        binary.parent.mkdir(parents=True)
        binary.write_text(f"#!/bin/sh\necho 'version: 1 ({commit[:7]})'\n", encoding="utf-8")
        binary.chmod(0o755)
        (binary.parent / "libfake-impl.so").write_bytes(b"fake-inference-library")
        return runtime_root

    def _with_models(self, synthetic_world) -> None:
        model_dir = synthetic_world.data_root / "models" / MODEL_LOCK_KEY
        model_dir.mkdir(parents=True)
        (model_dir / "model.gguf").write_bytes(b"gguf-one")
        (model_dir / "mmproj.gguf").write_bytes(b"gguf-two")
        lock = json.loads(synthetic_world.lock_path.read_text(encoding="utf-8"))
        lock["models"] = [
            {
                "name": MODEL_LOCK_KEY,
                "local_subdir": f"models/{MODEL_LOCK_KEY}",
                "files": 2,
                "size_bytes": 16,
            }
        ]
        synthetic_world.lock_path.write_text(json.dumps(lock), encoding="utf-8")

    def test_receipt_binds_commit_files_libraries_and_bytes(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        receipt = build_runtime_receipt(
            synthetic_world.lock_path, synthetic_world.data_root, runtime_root
        )
        commit = receipt["llama_cpp"]["build_commit"]
        assert len(commit) == 40
        assert commit[:7] in receipt["llama_cpp"]["reported_build"]
        assert len(receipt["gguf_files"]) == 2
        assert sum(entry["bytes"] for entry in receipt["gguf_files"]) == 16
        assert [entry["path"] for entry in receipt["runtime_libraries"]] == [
            "llama.cpp/build/bin/libfake-impl.so"
        ]

    def test_v3_inference_receipt_binds_decoder_only(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        receipt = build_runtime_receipt(
            synthetic_world.lock_path,
            synthetic_world.data_root,
            runtime_root,
            role="inference",
        )
        assert receipt["schema"] == RUNTIME_RECEIPT_SCHEMA_V3
        assert receipt["role"] == "inference"
        assert [Path(entry["path"]).name for entry in receipt["gguf_files"]] == [
            "model.gguf"
        ]

    def test_receipt_hashes_an_explicit_model_materialization_root(
        self, synthetic_world, tmp_path
    ):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        materialization_root = tmp_path / "fast-ext4"
        canonical_subdir = Path("models") / MODEL_LOCK_KEY
        shutil.copytree(
            synthetic_world.data_root / canonical_subdir,
            materialization_root / canonical_subdir,
        )
        shutil.rmtree(synthetic_world.data_root / canonical_subdir)

        receipt = build_runtime_receipt(
            synthetic_world.lock_path,
            synthetic_world.data_root,
            runtime_root,
            model_root=materialization_root,
            role="inference",
        )

        assert receipt["gguf_files"][0]["path"] == (
            f"models/{MODEL_LOCK_KEY}/model.gguf"
        )
        assert receipt["gguf_files"][0]["sha256"] == _sha(b"gguf-one")

    def test_v3_preprocess_receipt_binds_decoder_and_mmproj(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        receipt = build_runtime_receipt(
            synthetic_world.lock_path,
            synthetic_world.data_root,
            runtime_root,
            role="preprocess",
        )
        assert receipt["schema"] == RUNTIME_RECEIPT_SCHEMA_V3
        assert receipt["role"] == "preprocess"
        assert {Path(entry["path"]).name for entry in receipt["gguf_files"]} == {
            "model.gguf",
            "mmproj.gguf",
        }

    def test_stale_build_from_other_commit_refused(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.write_text("#!/bin/sh\necho 'version: 1 (0123abc)'\n", encoding="utf-8")
        binary.chmod(0o755)
        with pytest.raises(ArtifactError, match="stale or foreign build"):
            build_runtime_receipt(
                synthetic_world.lock_path, synthetic_world.data_root, runtime_root
            )

    def test_dirty_tree_refused(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        (runtime_root / "llama.cpp" / "uncommitted.txt").write_text("x", encoding="utf-8")
        with pytest.raises(ArtifactError, match="dirty"):
            build_runtime_receipt(
                synthetic_world.lock_path, synthetic_world.data_root, runtime_root
            )

    def test_wrong_file_count_refused(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        stray = synthetic_world.data_root / "models" / MODEL_LOCK_KEY / "stray.gguf"
        stray.write_bytes(b"extra")
        with pytest.raises(ArtifactError, match="lock freezes"):
            build_runtime_receipt(
                synthetic_world.lock_path, synthetic_world.data_root, runtime_root
            )

    # -----------------------------------------------------------------
    # Second-pinned-model plumbing (INT4 Q4_K_M alongside the frozen Q8_0):
    # build_runtime_receipt(model_lock_key=...) resolves a DIFFERENT umbrella-
    # lock entry, entirely independent of the default MODEL_LOCK_KEY, and
    # records exactly the key it actually used. Only build_runtime_receipt
    # is exercised here -- contracts.FrozenCoreGate still enforces its own
    # frozen MODEL_LOCK_KEY equality check unconditionally (see
    # gate_runtime.py); selecting a receipt for a different model is not, by
    # itself, an authorization to gate-open against it.
    # -----------------------------------------------------------------

    _ALT_MODEL_LOCK_KEY = "qwen3-omni-30b-a3b-instruct-gguf-q4km"

    def _with_named_model(
        self, synthetic_world, name: str, files: dict[str, bytes]
    ) -> None:
        model_dir = synthetic_world.data_root / "models" / name
        model_dir.mkdir(parents=True)
        total = 0
        for filename, content in files.items():
            (model_dir / filename).write_bytes(content)
            total += len(content)
        lock = json.loads(synthetic_world.lock_path.read_text(encoding="utf-8"))
        lock.setdefault("models", [])
        lock["models"].append(
            {
                "name": name,
                "local_subdir": f"models/{name}",
                "files": len(files),
                "size_bytes": total,
            }
        )
        synthetic_world.lock_path.write_text(json.dumps(lock), encoding="utf-8")

    def test_receipt_binds_a_non_default_model_lock_key(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_named_model(
            synthetic_world,
            self._ALT_MODEL_LOCK_KEY,
            {"model.gguf": b"q4km-fake-main-shard", "mmproj.gguf": b"q4km-fake-mmproj"},
        )
        # The DEFAULT MODEL_LOCK_KEY has no lock entry at all here -- proving
        # this call path never falls back to it.
        receipt = build_runtime_receipt(
            synthetic_world.lock_path,
            synthetic_world.data_root,
            runtime_root,
            model_lock_key=self._ALT_MODEL_LOCK_KEY,
        )
        assert receipt["model_lock_key"] == self._ALT_MODEL_LOCK_KEY
        assert len(receipt["gguf_files"]) == 2
        assert all(
            entry["path"].startswith(f"models/{self._ALT_MODEL_LOCK_KEY}/")
            for entry in receipt["gguf_files"]
        )

    def test_receipt_model_lock_key_defaults_to_the_frozen_key(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        receipt = build_runtime_receipt(
            synthetic_world.lock_path, synthetic_world.data_root, runtime_root
        )
        assert receipt["model_lock_key"] == MODEL_LOCK_KEY

    def test_unknown_model_lock_key_refused(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        with pytest.raises(Exception, match="not found"):
            build_runtime_receipt(
                synthetic_world.lock_path,
                synthetic_world.data_root,
                runtime_root,
                model_lock_key="no-such-model-in-the-lock",
            )

    def test_cli_runtime_command_writes_a_named_receipt_for_a_named_model(
        self, synthetic_world, tmp_path, monkeypatch
    ):
        """Deliverable 4: the operator entry point (extended ``e0.generate
        runtime`` -- ``--model-lock-key``/``--out``) builds and prints the
        SHA-256 of a receipt for a second pinned model, without ever writing
        to the default ``docs/receipts/runtime.json`` location."""

        from speech_aware_evidence_acquisition.e0.generate import main as generate_main

        monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
        runtime_root = self._llama_checkout(tmp_path)
        self._with_named_model(
            synthetic_world,
            self._ALT_MODEL_LOCK_KEY,
            {"model.gguf": b"q4km-fake-main-shard", "mmproj.gguf": b"q4km-fake-mmproj"},
        )
        out_path = tmp_path / "receipts-out" / "runtime-q4km.json"
        exit_code = generate_main(
            [
                "runtime",
                "--lock", str(synthetic_world.lock_path),
                "--runtime-root", str(runtime_root),
                "--model-lock-key", self._ALT_MODEL_LOCK_KEY,
                "--out", str(out_path),
                "--receipts-dir", str(tmp_path / "unused-default-receipts-dir"),
            ]
        )
        assert exit_code == 0
        assert out_path.is_file()
        receipt = json.loads(out_path.read_text(encoding="utf-8"))
        assert receipt["model_lock_key"] == self._ALT_MODEL_LOCK_KEY
        assert not (tmp_path / "unused-default-receipts-dir" / "runtime.json").exists()

    def test_cli_runtime_command_defaults_preserve_the_q8_receipt_path_and_key(
        self, synthetic_world, tmp_path, monkeypatch
    ):
        """No flags -> byte-identical behaviour to before this change: the
        default receipt still lands at ``<receipts-dir>/runtime.json`` and
        still names the frozen Q8_0 ``MODEL_LOCK_KEY``."""

        from speech_aware_evidence_acquisition.e0.generate import main as generate_main

        monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        receipts_dir = tmp_path / "receipts"
        exit_code = generate_main(
            [
                "runtime",
                "--lock", str(synthetic_world.lock_path),
                "--runtime-root", str(runtime_root),
                "--receipts-dir", str(receipts_dir),
            ]
        )
        assert exit_code == 0
        default_path = receipts_dir / "runtime.json"
        assert default_path.is_file()
        receipt = json.loads(default_path.read_text(encoding="utf-8"))
        assert receipt["model_lock_key"] == MODEL_LOCK_KEY

    def test_cli_runtime_command_can_bind_the_existing_named_llama_checkout(
        self, synthetic_world, tmp_path, monkeypatch
    ):
        from speech_aware_evidence_acquisition.e0.generate import main as generate_main

        monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
        runtime_root = self._llama_checkout(tmp_path)
        (runtime_root / "llama.cpp").rename(runtime_root / "llama.cpp-featcache")
        (runtime_root / "llama.cpp-featcache" / "build").rename(
            runtime_root / "llama.cpp-featcache" / "build-candidate"
        )
        (
            runtime_root / "llama.cpp-featcache" / ".git" / "info" / "exclude"
        ).write_text("build-candidate/\n", encoding="utf-8")
        self._with_models(synthetic_world)
        out_path = tmp_path / "runtime-inference.json"
        exit_code = generate_main(
            [
                "runtime",
                "--lock", str(synthetic_world.lock_path),
                "--runtime-root", str(runtime_root),
                "--llama-dir-name", "llama.cpp-featcache",
                "--binary-relpath", "build-candidate/bin/llama-server",
                "--role", "inference",
                "--out", str(out_path),
            ]
        )
        assert exit_code == 0
        receipt = json.loads(out_path.read_text(encoding="utf-8"))
        assert receipt["role"] == "inference"
        assert receipt["llama_cpp"]["binary_path"] == (
            "llama.cpp-featcache/build-candidate/bin/llama-server"
        )

    def test_cli_runtime_command_rejects_binary_path_escape(
        self, synthetic_world, tmp_path, monkeypatch
    ):
        from speech_aware_evidence_acquisition.e0.generate import main as generate_main

        monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        out_path = tmp_path / "escaped-runtime.json"

        exit_code = generate_main(
            [
                "runtime",
                "--lock", str(synthetic_world.lock_path),
                "--runtime-root", str(runtime_root),
                "--binary-relpath", "../foreign/llama-server",
                "--out", str(out_path),
            ]
        )

        assert exit_code == 1
        assert not out_path.exists()
