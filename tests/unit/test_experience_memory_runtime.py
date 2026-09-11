from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.roster import (
    RosterItem,
    freeze_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails.experience_memory import (
    Applicability,
    ExperienceRecord,
    ExperienceSource,
    SourceRef,
    ValidationBinding,
)
from speech_aware_evidence_acquisition.rails.experience_memory_runtime import (
    CORRECTIVE_MEMORY_TOOL,
    ExperienceMemoryBindingError,
    load_experience_memory_binding,
)
from speech_aware_evidence_acquisition.rails.phase_tools import build_phase_tools
from test_phase_planner import _context as _old_context, _material
from test_rails_runner import _knowledge_snapshot


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(
    roster_sha: str,
    *,
    record_id: str = "memory-a",
    sample_id: str = "slurp:train:001:audio",
    required: tuple[str, ...] = ("state:prior-response-present",),
    excluded: tuple[str, ...] = ("state:knowledge-absent",),
) -> ExperienceRecord:
    return ExperienceRecord.create(
        record_id=record_id,
        revision=1,
        kind="conditional-rule",
        train_construction_sha256=roster_sha,
        source=ExperienceSource(
            "train", sample_id, "1" * 64, "2" * 64, "3" * 64, "4" * 64
        ),
        applicability=Applicability(
            ("slurp-slot-slu",),
            ("revise",),
            ("supply", "use"),
            required,
            excluded,
        ),
        diagnosis="The earlier step may have omitted a grounded constraint.",
        guidance="Review the available evidence before changing the answer.",
        limitations=("This guidance does not supply a final answer.",),
        supporting_source_refs=(SourceRef("support", "5" * 64),),
        contradicting_source_refs=(SourceRef("contradiction", "6" * 64),),
        validation=ValidationBinding(
            "admitted", "7" * 64, "8" * 64, "9" * 64, "a" * 64
        ),
    )


def _world(
    tmp_path: Path,
    records=None,
    *,
    roster_role: str = "construction",
    roster_carrier: str = "slurp",
    roster_sample_id: str = "slurp:train:001:audio",
):
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir(parents=True)
    data.mkdir(parents=True)
    roster = freeze_roster(
        roster_id="slurp-train-construction",
        carrier_lock_key=roster_carrier,
        split_role="discovery",
        roster_role=roster_role,
        candidates=(RosterItem(roster_sample_id, "train"),),
        per_stratum=1,
        seed=1,
    )
    roster_path = repo / "rosters/train.json"
    write_roster(roster, roster_path)
    roster_sha = _sha(roster_path)
    records = tuple(records or (_record(roster_sha),))
    manifest = {
        "schema": "saea-experience-memory-manifest-v1",
        "memory_id": "slurp-corrections",
        "memory_version": 1,
        "construction_partition_role": "train",
        "train_construction_sha256": roster_sha,
        "records": [record.as_json() for record in records],
    }
    manifest_path = data / "memory/manifest.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
    manifest_sha = _sha(manifest_path)
    admission = {
        "schema": "saea-experience-memory-admission-v1",
        "status": "admitted",
        "manifest_sha256": manifest_sha,
        "construction_roster_sha256": roster_sha,
        "admitted_record_sha256s": [record.record_sha256 for record in records],
    }
    admission_path = data / "memory/admission.json"
    admission_path.write_text(json.dumps(admission, sort_keys=True) + "\n")
    config = {
        "experience_memory": {
            "manifest": {"relpath": "memory/manifest.json", "sha256": manifest_sha},
            "construction_roster": {
                "repo_relpath": "rosters/train.json",
                "sha256": roster_sha,
            },
            "admission": {
                "relpath": "memory/admission.json",
                "sha256": _sha(admission_path),
            },
            "task_id": "slurp-slot-slu",
            "component_tags": ["supply", "use"],
            "max_records": 1,
        }
    }
    return repo, data, config


def _load(tmp_path: Path, **updates):
    repo, data, config = _world(tmp_path)
    config["experience_memory"].update(updates)
    return load_experience_memory_binding(
        config, repo_root=repo, data_root=data, carrier_lock_key="slurp"
    )


def test_binding_loads_once_and_selects_bounded_structural_match(tmp_path):
    binding = _load(tmp_path)
    context = replace(
        _old_context(),
        prior_response_sha256s=("b" * 64,),
        query_state=replace(_old_context().query_state, retrieved_value_ids=("value-1",)),
    )
    selection = binding.select(next_phase="revise", context=context)
    assert [item["record_id"] for item in selection.visible["selected_records"]] == [
        "memory-a"
    ]
    assert selection.visible["condition_tags"] == [
        "state:knowledge-present",
        "state:prior-response-present",
        "state:tool-result-absent",
    ]
    encoded = json.dumps(selection.visible)
    assert "slurp:train:001:audio" not in encoded
    assert selection.lineage["selected_records"][0]["source"]["source_sample_id"].startswith(
        "slurp:train:"
    )


def test_no_match_is_explicit_and_max_records_applies(tmp_path):
    repo, data, config = _world(tmp_path)
    binding = load_experience_memory_binding(
        config, repo_root=repo, data_root=data, carrier_lock_key="slurp"
    )
    empty = binding.select(next_phase="other", context=_old_context())
    assert empty.visible["selected_records"] == []

    roster_sha = config["experience_memory"]["construction_roster"]["sha256"]
    repo, data, config = _world(
        tmp_path / "two",
        records=(
            _record(roster_sha, record_id="z"),
            _record(roster_sha, record_id="a", excluded=()),
        ),
    )
    binding = load_experience_memory_binding(
        config, repo_root=repo, data_root=data, carrier_lock_key="slurp"
    )
    context = replace(_old_context(), prior_response_sha256s=("b" * 64,))
    assert [
        row["record_id"]
        for row in binding.select(next_phase="revise", context=context).visible[
            "selected_records"
        ]
    ] == ["a"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda c: c["experience_memory"]["manifest"].update(sha256="0" * 64), "manifest SHA"),
        (lambda c: c["experience_memory"]["admission"].update(sha256="0" * 64), "admission"),
        (lambda c: c["experience_memory"].update(component_tags=["solver"]), "component"),
    ],
)
def test_wrong_binding_refuses(tmp_path, mutation, message):
    repo, data, config = _world(tmp_path)
    mutation(config)
    with pytest.raises(ExperienceMemoryBindingError, match=message):
        load_experience_memory_binding(
            config, repo_root=repo, data_root=data, carrier_lock_key="slurp"
        )


def test_admission_set_and_slurp_train_membership_are_exact(tmp_path):
    repo, data, config = _world(tmp_path)
    admission = data / config["experience_memory"]["admission"]["relpath"]
    document = json.loads(admission.read_text())
    document["admitted_record_sha256s"].append("f" * 64)
    admission.write_text(json.dumps(document, sort_keys=True) + "\n")
    config["experience_memory"]["admission"]["sha256"] = _sha(admission)
    with pytest.raises(ExperienceMemoryBindingError, match="record set"):
        load_experience_memory_binding(
            config, repo_root=repo, data_root=data, carrier_lock_key="slurp"
        )
    with pytest.raises(ExperienceMemoryBindingError, match="SLURP"):
        load_experience_memory_binding(
            config, repo_root=repo, data_root=data, carrier_lock_key="audio2tool"
        )


def test_construction_role_carrier_and_train_prefix_are_required(tmp_path):
    for name, kwargs, message in (
        ("role", {"roster_role": "evaluation"}, "construction role"),
        ("carrier", {"roster_carrier": "conec"}, "carrier differs"),
        (
            "prefix",
            {"roster_sample_id": "slurp:dev:001:audio"},
            "slurp:train",
        ),
    ):
        repo, data, config = _world(tmp_path / name, **kwargs)
        with pytest.raises(ExperienceMemoryBindingError, match=message):
            load_experience_memory_binding(
                config, repo_root=repo, data_root=data, carrier_lock_key="slurp"
            )


def test_admission_status_and_duplicate_record_hashes_refuse(tmp_path):
    for name, update, message in (
        ("status", {"status": "provisional"}, "not admitted"),
        ("duplicates", None, "record set"),
    ):
        repo, data, config = _world(tmp_path / name)
        admission_path = data / config["experience_memory"]["admission"]["relpath"]
        document = json.loads(admission_path.read_text())
        if update is not None:
            document.update(update)
        else:
            document["admitted_record_sha256s"].append(
                document["admitted_record_sha256s"][0]
            )
        admission_path.write_text(json.dumps(document, sort_keys=True) + "\n")
        config["experience_memory"]["admission"]["sha256"] = _sha(admission_path)
        with pytest.raises(ExperienceMemoryBindingError, match=message):
            load_experience_memory_binding(
                config, repo_root=repo, data_root=data, carrier_lock_key="slurp"
            )


def test_unsupported_projector_tags_refuse(tmp_path):
    repo, data, config = _world(tmp_path)
    roster_sha = config["experience_memory"]["construction_roster"]["sha256"]
    repo, data, config = _world(
        tmp_path / "bad-tag",
        records=(_record(roster_sha, required=("signal:evidence-conflict",)),),
    )
    with pytest.raises(ExperienceMemoryBindingError, match="unsupported condition"):
        load_experience_memory_binding(
            config, repo_root=repo, data_root=data, carrier_lock_key="slurp"
        )


def test_shared_controller_carries_memory_guidance_to_successor_solver(tmp_path):
    from speech_aware_evidence_acquisition.core.base import Registry
    from speech_aware_evidence_acquisition.rails.runner import (
        run_speech_native_agent_loop,
    )
    from test_rails_runner import (
        _RecordingAgentClient,
        _agent_trace,
        _one_sample_adapter,
        _plan,
    )

    repo, data, binding_config = _world(tmp_path)
    binding = load_experience_memory_binding(
        binding_config, repo_root=repo, data_root=data, carrier_lock_key="slurp"
    )
    snapshot = _knowledge_snapshot()
    context = replace(
        _old_context(),
        knowledge_snapshot_sha256=snapshot.content_hash(),
        query_state=replace(
            _old_context().query_state,
            retrieved_value_ids=(snapshot.values[0].value_id,),
        ),
    )
    phase_config = {
        "phase_tools": {
            "draft": {
                "mode": "fixed",
                "allowed_tools": [CORRECTIVE_MEMORY_TOOL],
                "fixed_action": {"tool_id": CORRECTIVE_MEMORY_TOOL, "arguments": {}},
            }
        },
        **binding_config,
    }
    dispatcher = build_phase_tools(
        phase_config,
        rc.default_phase_program("phase-draft-revise-v1"),
        snapshot=snapshot,
        experience_memory=binding,
    )
    controller = rc.EvidenceAgentController(
        program=rc.default_phase_program("phase-draft-revise-v1"),
        material_for_phase=_material,
        tools_for_phase=dispatcher,
    )
    contact = controller.initial_contact(context)
    move = controller.advance(context, contact, "draft answer")
    tool_state = move.new_agent_states[-1]
    visible = json.loads(tool_state.content)
    assert visible["result"]["selected_records"][0]["guidance"].startswith("Review")
    assert tool_state.cited_value_ids == ()
    assert move.next_contact.purpose == "revise"
    assert dispatcher.receipt()["memory_lineage"][0]["selected_records"][0][
        "source"
    ]["source_sample_id"].startswith("slurp:train:")
    staged_context = replace(
        context,
        agent_states=(move.new_agent_states[0],),
        prior_response_sha256s=(move.new_agent_states[0].source_response_sha256,),
    )
    with pytest.raises(Exception, match="already attempted"):
        dispatcher("draft", "revise", staged_context)

    registry = Registry("test controller")
    registry.register(
        "phase-draft-revise-v1",
        lambda _sample_id: rc.EvidenceAgentController(
            program=rc.default_phase_program("phase-draft-revise-v1"),
            material_for_phase=_material,
            tools_for_phase=build_phase_tools(
                phase_config,
                rc.default_phase_program("phase-draft-revise-v1"),
                snapshot=snapshot,
                experience_memory=binding,
            ),
        ),
    )
    client = _RecordingAgentClient()
    summary = run_speech_native_agent_loop(
        data_root=tmp_path / "runner",
        plan=_plan(execution_profile="model-free-check"),
        adapter=_one_sample_adapter(),
        core_client=client,
        split_id="all",
        knowledge_snapshot=snapshot,
        speech_packet_bindings={
            "s1": {"packet_id": "fake/dev/s1", "sha256": "c" * 64}
        },
        controller_policy_id="phase-draft-revise-v1",
        controller_registry=registry,
        bootstrap_value_ids=(snapshot.values[0].value_id,),
        max_contacts=2,
        slot_count=1,
        queue_depth=1,
        trace_sink=_agent_trace(),
        agent_executor_id="reference-trajectory-v1",
    )
    assert len(summary.results[0].contacts) == 2
    successor_states = client.calls[1][1]["agent_state"]
    tool_result = next(row for row in successor_states if row["state_kind"] == "tool-result")
    assert "Review the available evidence" in tool_result["content"]
    assert "slurp:train:001:audio" not in tool_result["content"]


def test_configured_memory_tool_requires_binding_and_old_config_is_unchanged():
    snapshot = _knowledge_snapshot()
    program = rc.default_phase_program("phase-draft-revise-v1")
    assert build_phase_tools({}, program, snapshot=snapshot) is None
    config = {
        "phase_tools": {
            "draft": {
                "mode": "fixed",
                "allowed_tools": [CORRECTIVE_MEMORY_TOOL],
                "fixed_action": {"tool_id": CORRECTIVE_MEMORY_TOOL, "arguments": {}},
            }
        }
    }
    with pytest.raises(Exception, match="memory binding"):
        build_phase_tools(config, program, snapshot=snapshot)


def test_runtime_refuses_invalid_binding_before_gate_or_contact(tmp_path):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError
    from test_flight_runtime import _FakeGate, _make_runtime

    gate = _FakeGate()
    missing = {
        "manifest": {"relpath": "memory/missing.json", "sha256": "0" * 64},
        "construction_roster": {
            "repo_relpath": "rosters/missing.json",
            "sha256": "1" * 64,
        },
        "admission": {"relpath": "memory/admission.json", "sha256": "2" * 64},
        "task_id": "slurp-slot-slu",
        "component_tags": ["supply", "use"],
        "max_records": 1,
    }
    runtime = _make_runtime(
        tmp_path,
        gate=gate,
        config_kwargs={
            "carrier_lock_key": "slurp",
            "policy": "phase-draft-revise-v1",
            "baseline_extra": {
                "experience_memory": missing,
                "phase_tools": {
                    "draft": {
                        "mode": "fixed",
                        "allowed_tools": [CORRECTIVE_MEMORY_TOOL],
                        "fixed_action": {
                            "tool_id": CORRECTIVE_MEMORY_TOOL,
                            "arguments": {},
                        },
                    }
                },
            },
        },
    )
    with pytest.raises(FlightRuntimeError, match="experience manifest"):
        runtime.preflight()
    assert gate.calls == 0
