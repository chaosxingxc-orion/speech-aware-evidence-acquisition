"""Contract 5: exposure-claim schema validates; the model entry gate refuses without receipts."""

import json
from pathlib import Path

import pytest

import hashlib

from speech_aware_evidence_acquisition.contracts import (
    E0_RECEIPT_SCHEMA,
    MODEL_LOCK_KEY,
    RUNTIME_RECEIPT_SCHEMA,
    STUDY_SLUG,
    ExecutionPlan,
    ExecutionScopeError,
    ExposureSchemaError,
    FrozenCoreGate,
    GateClosed,
    validate_exposure_claim,
)


REPO_ROOT = Path(__file__).resolve().parents[2]

VALID_CLAIM = {
    "scope": "earnings21-original dev slice, D0 acquisition only",
    "date": "2026-08-03",
    "counts": {"model_calls": 0, "speech_audio_seconds": 0},
    "inherited": "W1 probe campaigns on other carriers; zero model exposure on the three carriers",
}


def test_valid_exposure_claim_passes():
    validate_exposure_claim(VALID_CLAIM)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda claim: claim.pop("scope"),
        lambda claim: claim.pop("inherited"),
        lambda claim: claim.update(date="03/08/2026"),
        lambda claim: claim.update(counts={}),
        lambda claim: claim.update(counts={"model_calls": -1}),
        lambda claim: claim.update(extra_field=1),
    ],
)
def test_malformed_exposure_claims_fail(mutation):
    claim = {key: (dict(value) if isinstance(value, dict) else value) for key, value in VALID_CLAIM.items()}
    mutation(claim)
    with pytest.raises(ExposureSchemaError):
        validate_exposure_claim(claim)


def test_exposure_ledger_header_carries_contract_columns():
    """Parse the real table header — prose mentions of a column name do not count."""

    ledger = (REPO_ROOT / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    header = None
    for line in ledger.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and "run/experiment id" in stripped.lower():
            header = [cell.strip().lower() for cell in stripped.strip("|").split("|")]
            break
    assert header is not None, "exposure ledger must have a markdown table header row"
    for column in (
        "date",
        "run/experiment id",
        "execution profile",
        "scope",
        "model/tool",
        "speech carrier + split",
        "split role",
        "split identity hash",
        "consumed",
        "calls",
        "speech audio seconds",
        "gpu hours",
        "inherited exposure",
    ):
        assert column in header, f"exposure ledger header lacks column {column!r}"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class GateFixture:
    """A fully valid receipt/lock/file world in tmp_path that each test then tampers."""

    SUBDIR = f"models/{MODEL_LOCK_KEY}"
    GGUF_1 = b"GGUF-fake-model-shard-one" * 64
    GGUF_2 = b"GGUF-fake-mmproj" * 32
    BINARY = b"ELF-fake-llama-server" * 16
    LIBRARY = b"ELF-fake-libllama-impl" * 32
    ARTIFACT = b'{"receipt": "closed"}\n'
    SCORING_SOURCE = b"def score():\n    return 0\n"
    SCORING_REL = "src/speech_aware_evidence_acquisition/scoring/wer.py"
    RUN_ID = "SAEA-E-000-smoke"
    CARRIER = "earnings21-original"

    def __init__(self, tmp_path: Path) -> None:
        self.receipts = tmp_path / "receipts"
        self.data_root = tmp_path / "data"
        self.runtime_root = tmp_path / "runtime"
        self.source_root = tmp_path
        self.lock_path = tmp_path / "datasets.lock.json"
        model_dir = self.data_root / self.SUBDIR
        model_dir.mkdir(parents=True)
        (model_dir / "model-q8_0.gguf").write_bytes(self.GGUF_1)
        (model_dir / "mmproj-bf16.gguf").write_bytes(self.GGUF_2)
        binary = self.runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(self.BINARY)
        (binary.parent / "libfake-impl.so").write_bytes(self.LIBRARY)

        self.scoring_dir = tmp_path / "src" / "speech_aware_evidence_acquisition" / "scoring"
        self.scoring_dir.mkdir(parents=True)
        (self.scoring_dir / "wer.py").write_bytes(self.SCORING_SOURCE)
        self.d3_artifact = json.dumps(
            {"frozen_sources_sha256": {self.SCORING_REL: _sha(self.SCORING_SOURCE)}}
        ).encode("utf-8")

        (self.receipts / "e0").mkdir(parents=True)
        self.deliverables = {}
        for name in FrozenCoreGate.E0_DELIVERABLES:
            content = self.d3_artifact if name == "d3_scoring" else self.ARTIFACT
            artifact = self.receipts / "e0" / f"{name}.json"
            artifact.write_bytes(content)
            self.deliverables[name] = {
                "status": "CLOSED",
                "artifact": f"e0/{name}.json",
                "sha256": _sha(content),
            }
        self.lock = {
            "models": [
                {
                    "name": MODEL_LOCK_KEY,
                    "local_subdir": self.SUBDIR,
                    "files": 2,
                    "size_bytes": len(self.GGUF_1) + len(self.GGUF_2),
                    "note": "extra lock fields are tolerated",
                }
            ],
            "datasets": [{"name": self.CARRIER}],
        }
        self.exposure_ledger = tmp_path / "exposure-ledger.md"
        self.write_ledger_rows(
            f"| 2026-08-04 | {self.RUN_ID} | baseline-reproduction | earnings21 dev slice "
            f"| qwen3-omni | {self.CARRIER} dev | dev | {'a' * 64} | no "
            "| 10 | 600 | 1.0 | W1 probes on other carriers only | mlflow://pending "
            "| pre-registered |\n"
        )
        self.e0 = {
            "schema": E0_RECEIPT_SCHEMA,
            "study": STUDY_SLUG,
            "deliverables": self.deliverables,
        }
        self.runtime = {
            "schema": RUNTIME_RECEIPT_SCHEMA,
            "study": STUDY_SLUG,
            "model_lock_key": MODEL_LOCK_KEY,
            "llama_cpp": {
                "build_commit": "d" * 40,
                "reported_build": "version: 9999 (ddddddd)",
                "binary_path": "llama.cpp/build/bin/llama-server",
                "binary_bytes": len(self.BINARY),
                "binary_sha256": _sha(self.BINARY),
            },
            "gguf_files": [
                {
                    "path": f"{self.SUBDIR}/model-q8_0.gguf",
                    "bytes": len(self.GGUF_1),
                    "sha256": _sha(self.GGUF_1),
                },
                {
                    "path": f"{self.SUBDIR}/mmproj-bf16.gguf",
                    "bytes": len(self.GGUF_2),
                    "sha256": _sha(self.GGUF_2),
                },
            ],
            "runtime_libraries": [
                {
                    "path": "llama.cpp/build/bin/libfake-impl.so",
                    "bytes": len(self.LIBRARY),
                    "sha256": _sha(self.LIBRARY),
                }
            ],
        }

    def write_ledger_rows(self, rows: str) -> None:
        self.exposure_ledger.write_text(
            "| date | run/experiment id | execution profile | scope | model/tool "
            "| speech carrier + split | split role | split identity hash | consumed "
            "| calls | speech audio seconds | gpu hours | inherited exposure "
            "| artifacts | notes |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n" + rows,
            encoding="utf-8",
        )

    def gate(self) -> FrozenCoreGate:
        (self.receipts / "e0-closure.json").write_text(json.dumps(self.e0), encoding="utf-8")
        (self.receipts / "runtime.json").write_text(json.dumps(self.runtime), encoding="utf-8")
        self.lock_path.write_text(json.dumps(self.lock), encoding="utf-8")
        return FrozenCoreGate(
            e0_receipt=self.receipts / "e0-closure.json",
            runtime_receipt=self.receipts / "runtime.json",
            data_root=self.data_root,
            lock_path=self.lock_path,
            runtime_root=self.runtime_root,
            exposure_ledger=self.exposure_ledger,
            source_root=self.source_root,
        )

    def plan(self, **overrides: object) -> ExecutionPlan:
        base: dict = dict(
            run_id=self.RUN_ID,
            execution_profile="baseline-reproduction",
            carrier_lock_key=self.CARRIER,
            split_role="dev",
            split_identity_hash="a" * 64,
            planned_model_calls=10,
            planned_gpu_hours=1.0,
            planned_speech_audio_seconds=600,
            protocol_hash="b" * 64,
        )
        base.update(overrides)
        return ExecutionPlan(**base)


@pytest.fixture()
def world(tmp_path):
    return GateFixture(tmp_path)


def test_fully_valid_receipts_open_the_gate(world):
    world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_when_receipts_are_missing(tmp_path, world):
    gate = FrozenCoreGate(
        tmp_path / "absent-e0.json",
        tmp_path / "absent-runtime.json",
        world.data_root,
        world.lock_path,
        world.runtime_root,
        world.exposure_ledger,
        world.source_root,
    )
    world.lock_path.write_text(json.dumps(world.lock), encoding="utf-8")
    with pytest.raises(GateClosed, match="missing or unreadable"):
        gate.assert_model_touch_allowed(world.plan())


def test_gate_refuses_nonexistent_model_file(world):
    world.runtime["gguf_files"][1]["path"] = f"{world.SUBDIR}/definitely-does-not-exist.gguf"
    with pytest.raises(GateClosed, match="does not exist"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_fabricated_hash_and_size(world):
    world.runtime["gguf_files"][0]["sha256"] = "0" * 64
    with pytest.raises(GateClosed, match="SHA-256 drift"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.runtime["gguf_files"][0]["sha256"] = _sha(world.GGUF_1)
    world.runtime["gguf_files"][0]["bytes"] = 12345
    with pytest.raises(GateClosed, match="size drift"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_model_byte_drift_on_disk(world):
    (world.data_root / world.SUBDIR / "model-q8_0.gguf").write_bytes(b"tampered")
    with pytest.raises(GateClosed, match="drift"):
        world.gate().assert_model_touch_allowed(world.plan())


@pytest.mark.parametrize(
    "bad_path",
    [
        "/definitely/does/not/exist/model.gguf",
        "C:/leak/model.gguf",
        "../outside.gguf",
        "models/../../escape.gguf",
    ],
)
def test_gate_refuses_absolute_and_traversal_paths(world, bad_path):
    world.runtime["gguf_files"][1]["path"] = bad_path
    with pytest.raises(GateClosed):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_duplicate_and_extra_model_files(world):
    world.runtime["gguf_files"][1] = dict(world.runtime["gguf_files"][0])
    with pytest.raises(GateClosed, match="duplicates"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.runtime["gguf_files"] = [
        world.runtime["gguf_files"][0],
        {
            "path": f"{world.SUBDIR}/mmproj-bf16.gguf",
            "bytes": len(world.GGUF_2),
            "sha256": _sha(world.GGUF_2),
        },
        {
            "path": f"{world.SUBDIR}/model-q8_0.gguf",
            "bytes": len(world.GGUF_1),
            "sha256": _sha(world.GGUF_1),
        },
    ]
    with pytest.raises(GateClosed, match="extra or missing"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_lock_key_mismatch_and_missing_lock_entry(world):
    world.runtime["model_lock_key"] = "some-other-model"
    with pytest.raises(GateClosed, match="does not match"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.runtime["model_lock_key"] = MODEL_LOCK_KEY
    world.lock["models"][0]["name"] = "renamed-away"
    with pytest.raises(GateClosed, match="not found in datasets lock"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_path_outside_lock_subdir(world):
    stray = world.data_root / "models" / "other"
    stray.mkdir(parents=True)
    (stray / "model.gguf").write_bytes(world.GGUF_1)
    world.runtime["gguf_files"][0]["path"] = "models/other/model.gguf"
    with pytest.raises(GateClosed, match="canonical subdir"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_unbacked_build_commit(world):
    world.runtime["llama_cpp"]["build_commit"] = "abc123"
    with pytest.raises(GateClosed, match="full 40-hex"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.runtime["llama_cpp"]["build_commit"] = "d" * 40
    world.runtime["llama_cpp"]["binary_sha256"] = "e" * 64
    with pytest.raises(GateClosed, match="binary drift"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.runtime["llama_cpp"]["binary_sha256"] = _sha(world.BINARY)
    world.runtime["llama_cpp"]["binary_path"] = "llama.cpp/missing/llama-server"
    with pytest.raises(GateClosed, match="does not exist"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_e0_artifact_hash_drift(world):
    world.deliverables["d2_leakage"]["sha256"] = "f" * 64
    with pytest.raises(GateClosed, match="artifact hash drift"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_open_deliverable_and_missing_artifact(world):
    world.deliverables["d3_scoring"]["status"] = "OPEN"
    with pytest.raises(GateClosed, match="d3_scoring"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.deliverables["d3_scoring"]["status"] = "CLOSED"
    (world.receipts / "e0" / "d4_trace.json").unlink()
    with pytest.raises(GateClosed, match="d4_trace"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_schema_or_identity_mismatch(world):
    world.e0["schema"] = "some-other-schema"
    with pytest.raises(GateClosed, match="schema mismatch"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.e0["schema"] = E0_RECEIPT_SCHEMA
    world.runtime["study"] = "another-study"
    with pytest.raises(GateClosed, match="study identity mismatch"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_lock_total_size_mismatch(world):
    world.lock["models"][0]["size_bytes"] += 1
    with pytest.raises(GateClosed, match="total"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_confirmatory_split_even_with_allowed_profile(world):
    with pytest.raises(ExecutionScopeError, match="confirmatory"):
        world.gate().assert_model_touch_allowed(world.plan(split_role="confirmatory"))


def test_gate_refuses_over_budget_plans_regardless_of_label(world):
    for overrides in (
        {"planned_model_calls": 3001},
        {"planned_gpu_hours": 40.5},
        {"planned_speech_audio_seconds": 72001},
    ):
        with pytest.raises(ExecutionScopeError, match="cap"):
            world.gate().assert_model_touch_allowed(world.plan(**overrides))


def test_gate_refuses_missing_or_malformed_hashes(world):
    with pytest.raises(ExecutionScopeError, match="split_identity_hash"):
        world.gate().assert_model_touch_allowed(world.plan(split_identity_hash="short"))
    with pytest.raises(ExecutionScopeError, match="protocol_hash"):
        world.gate().assert_model_touch_allowed(world.plan(protocol_hash=""))


def test_gate_refuses_run_without_preregistered_exposure_row(world):
    with pytest.raises(GateClosed, match="pre-registered exposure row"):
        world.gate().assert_model_touch_allowed(
            world.plan(run_id="SAEA-E-999-unregistered")
        )


def test_gate_refuses_scoring_source_drift(world):
    (world.scoring_dir / "wer.py").write_bytes(b"def score():\n    return 1  # tampered\n")
    with pytest.raises(GateClosed, match="scoring freeze drift"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_unlisted_scoring_module(world):
    (world.scoring_dir / "wer_v2.py").write_bytes(b"def score2():\n    return 2\n")
    with pytest.raises(GateClosed, match="does not name"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_missing_scoring_freeze_mapping(world):
    artifact = world.receipts / "e0" / "d3_scoring.json"
    artifact.write_bytes(world.ARTIFACT)
    world.deliverables["d3_scoring"]["sha256"] = _sha(world.ARTIFACT)
    with pytest.raises(GateClosed, match="frozen_sources_sha256"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_runtime_library_drift_and_unlisted_files(world):
    lib = world.runtime_root / "llama.cpp" / "build" / "bin" / "libfake-impl.so"
    lib.write_bytes(b"rebuilt-from-patched-source")
    with pytest.raises(GateClosed, match="drift"):
        world.gate().assert_model_touch_allowed(world.plan())

    lib.write_bytes(world.LIBRARY)
    stray = world.runtime_root / "llama.cpp" / "build" / "bin" / "libextra-plugin.so"
    stray.write_bytes(b"unlisted plugin")
    with pytest.raises(GateClosed, match="runtime directory drift"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_reported_build_mismatch(world):
    world.runtime["llama_cpp"]["reported_build"] = "version: 9999 (abcdef1)"
    with pytest.raises(GateClosed, match="prefix-match"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_ledger_row_disagreeing_with_plan(world):
    with pytest.raises(GateClosed, match="disagrees with the execution plan"):
        world.gate().assert_model_touch_allowed(world.plan(split_identity_hash="b" * 64))
    with pytest.raises(GateClosed, match="disagrees with the execution plan"):
        world.gate().assert_model_touch_allowed(world.plan(split_role="discovery"))


def test_gate_refuses_budget_exceeding_registration(world):
    with pytest.raises(GateClosed, match="pre-registered"):
        world.gate().assert_model_touch_allowed(world.plan(planned_model_calls=2999))


def test_gate_refuses_consumed_row(world):
    world.write_ledger_rows(
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'a' * 64} | yes "
        "| 10 | 600 | 1.0 | none | none | consumed |\n"
    )
    with pytest.raises(GateClosed, match="already consumed"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_duplicate_registration(world):
    row = (
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'a' * 64} | no "
        "| 10 | 600 | 1.0 | none | none | dup |\n"
    )
    world.write_ledger_rows(row + row)
    with pytest.raises(GateClosed, match="more than once"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_profile_and_seconds_disagreement(world):
    with pytest.raises(GateClosed, match="disagrees with the execution plan"):
        world.gate().assert_model_touch_allowed(
            world.plan(execution_profile="bounded-discovery-probe")
        )
    with pytest.raises(GateClosed, match="pre-registered"):
        world.gate().assert_model_touch_allowed(
            world.plan(planned_speech_audio_seconds=700)
        )
    with pytest.raises(GateClosed, match="pre-registered"):
        world.gate().assert_model_touch_allowed(world.plan(planned_gpu_hours=2.0))


def test_gate_refuses_cumulative_slice_budget_exhaustion(world):
    """N individually-bounded runs cannot sum past the frozen slice caps."""

    other = (
        "| 2026-08-04 | SAEA-E-001-prior | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'c' * 64} | no "
        "| 2995 | 600 | 1.0 | none | none | prior run |\n"
    )
    mine = (
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'a' * 64} | no "
        "| 10 | 600 | 1.0 | none | none | this run |\n"
    )
    world.write_ledger_rows(other + mine)
    with pytest.raises(GateClosed, match="first-slice cap"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_scoring_module_hidden_in_a_subdirectory(world):
    nested = world.scoring_dir / "helpers"
    nested.mkdir()
    (nested / "extra.py").write_bytes(b"def helper():\n    return 3\n")
    with pytest.raises(GateClosed, match="does not name"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_non_source_file_in_scoring_package(world):
    (world.scoring_dir / "table.json").write_bytes(b"{}")
    with pytest.raises(GateClosed, match="non-source entry"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_subdirectory_in_runtime_bin(world):
    plugins = world.runtime_root / "llama.cpp" / "build" / "bin" / "plugins"
    plugins.mkdir()
    (plugins / "evil.so").write_bytes(b"plugin")
    with pytest.raises(GateClosed, match="non-file entry"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_ignores_rows_in_a_second_table(world):
    injected = (
        "\nsome prose after the first table\n\n"
        "| date | run/experiment id | execution profile | scope | model/tool "
        "| speech carrier + split | split role | split identity hash | consumed "
        "| calls | speech audio seconds | inherited exposure | artifacts | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        f"| 2026-08-04 | SAEA-E-777-injected | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'a' * 64} | no "
        "| 10 | 600 | none | none | injected |\n"
    )
    world.exposure_ledger.write_text(
        world.exposure_ledger.read_text(encoding="utf-8") + injected, encoding="utf-8"
    )
    with pytest.raises(GateClosed, match="pre-registered exposure row"):
        world.gate().assert_model_touch_allowed(world.plan(run_id="SAEA-E-777-injected"))


def test_gate_refuses_unknown_carrier_lock_key(world):
    with pytest.raises(GateClosed, match="datasets lock"):
        world.gate().assert_model_touch_allowed(world.plan(carrier_lock_key="not-in-lock"))


def test_bare_profile_strings_are_no_longer_accepted(world):
    with pytest.raises(ExecutionScopeError, match="ExecutionPlan"):
        world.gate().assert_model_touch_allowed("baseline-reproduction")
