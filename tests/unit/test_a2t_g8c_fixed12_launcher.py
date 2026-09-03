"""Contact-free contract tests for the thin G8C fixed12 launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-g8c-action-support-reachability-fixed12-v1/launcher/"
    "launch_a2t_g8c_fixed12.py"
)
SPEC = importlib.util.spec_from_file_location("launch_a2t_g8c_fixed12", LAUNCHER)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_g8c_launcher_binds_fixed12_identity_and_exact_metadata_audio_budget() -> None:
    roster = json.loads(MODULE.G8C_ROSTER.read_text(encoding="utf-8"))

    assert MODULE.RUN_ID == "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1"
    assert MODULE.SAMPLE_COUNT == 12
    assert MODULE.MAX_MODEL_CONTACTS == 408
    assert MODULE.MIN_MODEL_CONTACTS == 384
    assert MODULE.REPEATED_SPEECH_AUDIO_SECONDS == 76.694
    assert MODULE.PLANNED_SPEECH_AUDIO_SECONDS == 2608
    assert MODULE._selected_roster_ids() == tuple(
        row["sample_id"] for row in roster["selected"]
    )
    assert MODULE._verify_repeated_speech_reservation() == 76.694


def test_g8c_execution_plan_and_dynamic_cost_geometry_are_fixed12() -> None:
    plan = MODULE.execution_plan("attempt-g8c-test")
    empty_states = tuple(
        SimpleNamespace(selection=MODULE.ToolSelection((), "[]"), invalid_stage=None)
        for _ in range(12)
    )
    summary = MODULE.FlightSummary(empty_states, 396)

    assert plan.split_identity_hash == MODULE.SPLIT_IDENTITY_HASH
    assert plan.planned_model_calls == 408
    assert plan.planned_speech_audio_seconds == 2608
    assert MODULE.physical_and_logical_costs()["dynamic_formula"] == (
        "396 + nonempty_valid_selections - invalid_selects - invalid_binds"
    )
    costs = MODULE.physical_and_logical_costs(summary)
    assert costs["physical_model_contacts"] == 396
    assert costs["shared_physical_contacts"] == 348
    assert costs["logical_action_contacts"]["EXHAUSTIVE_G7"] == 360
    assert costs["logical_action_contacts"]["SUPPORT_ONLY_RESOLVE"] == 360


def test_g8c_corrected_audit_emitter_is_accepted_by_real_trace_sink(tmp_path: Path) -> None:
    state = SimpleNamespace(
        sample=SimpleNamespace(sample_id="sample-g8c"),
        contacts=(
            MODULE.ContactRecord(
                sample_id="sample-g8c",
                contact_id="g8-obs",
                stage="OBS",
                slot_id=0,
                response_sha256="a" * 64,
                prompt_fit={"total": 1},
            ),
        ),
        model_free_transitions=(),
        observation=SimpleNamespace(valid=True, text="speech observation"),
        normalized_sheet=SimpleNamespace(
            assessments=(SimpleNamespace(status="support", tool_name="tool_a"),),
            text="normalized sheet",
        ),
        support_sheet=SimpleNamespace(
            assessments=(SimpleNamespace(status="support", tool_name="tool_a"),),
            text="support sheet",
        ),
        branch_texts={branch: "[]" for branch in MODULE.BRANCH_ORDER[1:]},
        selection=MODULE.ToolSelection((), "[]"),
        bindings=MODULE.ToolBindings((), "[]"),
        invalid_stage=None,
        invalid_status=None,
        invalid_error=None,
    )
    sink = MODULE.TraceSink(tmp_path / "trace", MODULE.RUN_ID)

    MODULE._emit_state_audits(state, sink)
    sink.close()

    trace = tmp_path / "trace" / f"{MODULE.RUN_ID}.trace.jsonl"
    rows = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    assert {row["channel"] for row in rows} == {"COST", "OBS", "ORG", "SUPPLY", "USE"}
    assert all(row["record_id"].startswith("g8c:") for row in rows)
    for row in rows:
        prefix = {"OBS": "obs_", "ORG": "org_", "SUPPLY": "supply_", "USE": "use_"}.get(
            row["channel"]
        )
        if prefix:
            assert all(key.startswith(prefix) for key in row["payload"])


def test_g8c_outer_parallel_plan_keeps_four_whole_fixed12_manifests(
    tmp_path: Path,
) -> None:
    manifests = {branch: tmp_path / f"{branch}.json" for branch in MODULE.BRANCH_ORDER}

    plan = MODULE.parallel_score_plan(manifests)

    assert plan["workers"] == 4
    assert plan["dataset_sharding"] is False
    assert plan["shard_metric_averaging"] is False
    assert len(plan["jobs"]) == 4
    assert all(job["whole_manifest_only"] is True for job in plan["jobs"])
    assert all(job["row_count"] == 12 for job in plan["jobs"])
