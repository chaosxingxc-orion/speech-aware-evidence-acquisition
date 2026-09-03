"""Synthetic-only ordering tests for the fixed-eight post-seal dispatcher."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-native-structured-action-fixed8-v1/launcher/"
    "postseal_native_structured_action_fixed8.py"
)
IDS = tuple(f"tier{index}:00000{index}" for index in range(1, 9))


def _runner():
    name = "test_a2t_native_structured_action_postseal_runner_module"
    spec = importlib.util.spec_from_file_location(name, RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixed8_sample_ids_reads_identity_only_receipt_items(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _runner()
    roster = tmp_path / module.ROSTER_RELPATH
    roster.parent.mkdir(parents=True)
    roster.write_text(
        json.dumps({"items": [{"sample_id": sample_id} for sample_id in IDS]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "REPO", tmp_path)

    assert module.fixed8_sample_ids() == IDS


@dataclass(frozen=True)
class _Subset:
    manifest: Path


def test_dispatch_proves_both_strict_cells_before_historical_materialization(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _runner()
    events: list[str] = []
    authorization = object()

    def prove(**kwargs):
        events.append("prove")
        assert kwargs["sample_ids"] == IDS
        return authorization

    def materialize(**kwargs):
        events.append("materialize")
        assert kwargs["authorization"] is authorization
        return {
            "REGISTRY_NO_SCHEMA": _Subset(tmp_path / "registry.json"),
            "HANDBOOK_NO_SCHEMA": _Subset(tmp_path / "handbook.json"),
        }

    def plan(**kwargs):
        events.append("plan")
        assert set(kwargs["manifests"]) == set(module.CELL_ORDER)
        assert kwargs["manifests"]["REGISTRY_NO_SCHEMA"]["sample_ids"] == IDS
        return "four-whole-manifest-jobs"

    monkeypatch.setattr(module, "prove_strict_cells_sealed", prove)
    monkeypatch.setattr(module, "materialize_historical_subsets", materialize)
    monkeypatch.setattr(module, "build_four_job_plan", plan)

    result = module.dispatch_postseal(
        sample_ids=IDS,
        strict_seals={cell: {"manifest": tmp_path / f"{cell}.json"} for cell in module.STRICT_CELLS},
        historical_sources={
            cell: {"manifest": tmp_path / f"{cell}.json"}
            for cell in module.HISTORICAL_CELLS
        },
        output_root=tmp_path / "historical-subsets",
        jobs_path=tmp_path / "score-jobs.jsonl",
        score_output_dir=tmp_path / "scores",
    )

    assert result == "four-whole-manifest-jobs"
    assert events == ["prove", "materialize", "plan"]


def test_dispatch_never_opens_historical_sources_when_strict_proof_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _runner()

    def fail_proof(**_kwargs):
        raise RuntimeError("strict cells are not sealed")

    monkeypatch.setattr(module, "prove_strict_cells_sealed", fail_proof)
    monkeypatch.setattr(
        module,
        "materialize_historical_subsets",
        lambda **_kwargs: pytest.fail("historical source opened before strict proof"),
    )

    with pytest.raises(RuntimeError, match="strict cells are not sealed"):
        module.dispatch_postseal(
            sample_ids=IDS,
            strict_seals={cell: {} for cell in module.STRICT_CELLS},
            historical_sources={cell: {} for cell in module.HISTORICAL_CELLS},
            output_root=tmp_path / "historical-subsets",
            jobs_path=tmp_path / "score-jobs.jsonl",
            score_output_dir=tmp_path / "scores",
        )


def test_fixed8_sample_ids_reads_identity_only_item_roster(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The frozen receipt records the fixed eight under ``items``."""

    module = _runner()
    monkeypatch.setattr(
        module,
        "_read_object",
        lambda *_args: {"items": [{"sample_id": sample_id} for sample_id in IDS]},
    )

    assert module.fixed8_sample_ids() == IDS


def test_registry_descriptor_binds_a_present_recovery_receipt(tmp_path: Path) -> None:
    module = _runner()
    mission = tmp_path / "mission"
    for cell in module.STRICT_CELLS:
        arm_dir = mission / cell.lower()
        arm_dir.mkdir(parents=True)
        manifest = {
            key: {"sha256": character * 64}
            for key, character in (
                ("outputs", "a"),
                ("raw_trace", "b"),
                ("trace_manifest", "c"),
            )
        }
        (arm_dir / f"{module.RUN_ID}.run-manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
    receipt = mission / "recovery-v2-flight-receipt.json"
    receipt.write_text('{"schema":"fixture"}\n', encoding="utf-8")

    descriptors = module.strict_seals_from_mission(mission)

    assert descriptors["REGISTRY_STRICT_ACTION"]["recovered_from_aborted_attempt"] is True
    assert descriptors["REGISTRY_STRICT_ACTION"]["recovery_receipt"] == receipt.resolve()
    assert descriptors["REGISTRY_STRICT_ACTION"]["recovery_receipt_sha256"] == hashlib.sha256(
        receipt.read_bytes()
    ).hexdigest()
    assert "recovered_from_aborted_attempt" not in descriptors["HANDBOOK_STRICT_ACTION"]


def test_registry_descriptor_uses_the_immutable_successor_bundle_when_present(
    tmp_path: Path,
) -> None:
    module = _runner()
    mission = tmp_path / "mission"
    for cell in module.STRICT_CELLS:
        arm_dir = mission / cell.lower()
        arm_dir.mkdir(parents=True)
        (arm_dir / f"{module.RUN_ID}.run-manifest.json").write_text(
            json.dumps(
                {
                    key: {"sha256": character * 64}
                    for key, character in (
                        ("outputs", "a"),
                        ("raw_trace", "b"),
                        ("trace_manifest", "c"),
                    )
                }
            ),
            encoding="utf-8",
        )
    successor = mission / "registry_strict_action_recovery_v2"
    successor.mkdir()
    successor_manifest = successor / f"{module.RUN_ID}.run-manifest.json"
    successor_manifest.write_text(
        json.dumps(
            {
                key: {"sha256": character * 64}
                for key, character in (
                    ("outputs", "d"),
                    ("raw_trace", "e"),
                    ("trace_manifest", "f"),
                )
            }
        ),
        encoding="utf-8",
    )
    (mission / "recovery-v2-flight-receipt.json").write_text("{}\n", encoding="utf-8")

    descriptors = module.strict_seals_from_mission(mission)

    assert descriptors["REGISTRY_STRICT_ACTION"]["manifest"] == successor_manifest.resolve()
    assert descriptors["REGISTRY_STRICT_ACTION"]["outputs_sha256"] == "d" * 64


def test_handbook_descriptor_uses_the_recovery_bundle_after_continuation(
    tmp_path: Path,
) -> None:
    module = _runner()
    mission = tmp_path / "mission"
    registry_successor = mission / module.REGISTRY_SUCCESSOR_DIRECTORY
    registry_successor.mkdir(parents=True)
    handbook_recovery = mission / module.HANDBOOK_RECOVERY_DIRECTORY
    handbook_recovery.mkdir()
    for directory, characters in (
        (registry_successor, ("a", "b", "c")),
        (handbook_recovery, ("d", "e", "f")),
    ):
        manifest_run_id = (
            module.RUN_ID
            if directory == registry_successor
            else module.RECOVERY_V2_RUN_ID
        )
        (directory / f"{manifest_run_id}.run-manifest.json").write_text(
            json.dumps(
                {
                    key: {"sha256": character * 64}
                    for key, character in zip(
                        ("outputs", "raw_trace", "trace_manifest"),
                        characters,
                        strict=True,
                    )
                }
            ),
            encoding="utf-8",
        )
    (mission / "recovery-v2-flight-receipt.json").write_text("{}\n", encoding="utf-8")

    descriptors = module.strict_seals_from_mission(mission)

    assert descriptors["HANDBOOK_STRICT_ACTION"]["manifest"] == (
        handbook_recovery / f"{module.RECOVERY_V2_RUN_ID}.run-manifest.json"
    ).resolve()
    assert descriptors["HANDBOOK_STRICT_ACTION"]["outputs_sha256"] == "d" * 64
