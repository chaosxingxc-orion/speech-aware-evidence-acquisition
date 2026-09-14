from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.preparation import (
    canonical_bytes,
    hash_stable_file,
    prepare_artifact,
)
from speech_aware_evidence_acquisition.core.provisional_candidate_materialization import (
    ARTIFACT_KIND,
    OUTPUT_SCHEMA,
)
from speech_aware_evidence_acquisition.core.roster import write_roster
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.candidate_experience_memory import (
    DECISION_SCHEMA,
    SOURCE_ATTESTATION_KIND,
    SOURCE_ATTESTATION_SCHEMA,
    CandidateExperienceMemoryError,
    load_candidate_experience_memory,
)
from speech_aware_evidence_acquisition.rails.experience_memory import (
    Applicability,
    ExperienceMemoryCatalog,
    ExperienceMemoryError,
    ExperienceRecord,
    ExperienceSource,
    ValidationBinding,
)
from speech_aware_evidence_acquisition.rails.experience_memory_sources import (
    reward_link_hash_source_ref,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(index: int, construction_sha: str) -> ExperienceRecord:
    return ExperienceRecord.create(
        record_id=f"provisional-{index}",
        revision=1,
        kind="corrective-experience",
        train_construction_sha256=construction_sha,
        source=ExperienceSource(
            "train", f"slurp:train:construct-{index}", str(index) * 64,
            chr(96 + index) * 64, chr(98 + index) * 64,
            chr(100 + index) * 64,
        ),
        applicability=Applicability(
            task_ids=("slurp",),
            phases=("reviewer",),
            component_tags=("org",),
            required_conditions=("state:prior-response-present",),
            excluded_conditions=(),
        ),
        diagnosis=f"Diagnosis {index}.",
        guidance=f"Guidance {index}.",
        limitations=("Evaluate provisionally.",),
        supporting_source_refs=(
            reward_link_hash_source_ref(str(5 + index) * 64),
        ),
        validation=ValidationBinding(
            "provisional", "a" * 64, "b" * 64,
            construction_sha, "c" * 64,
        ),
    )


def _write_roster(
    path: Path, *, roster_id: str, role: str, sample_ids: tuple[str, ...]
) -> str:
    receipt = {
        "schema": "saea-roster-receipt-v1",
        "roster_id": roster_id,
        "carrier_lock_key": "slurp",
        "split_role": "discovery",
        "roster_role": role,
        "seed": 11,
        "per_stratum": {"all": len(sample_ids)},
        "strata_counts": {"all": len(sample_ids)},
        "items": [
            {"sample_id": sample_id, "stratum": "all"}
            for sample_id in sample_ids
        ],
        "excluded_count": 0,
        "split_identity_hash": split_identity_hash(
            prefixed("slurp", sample_ids)
        ),
    }
    write_roster(receipt, path)
    return _sha(path)


def _world(tmp_path: Path) -> dict[str, object]:
    repo_root = tmp_path / "repo"
    data_root = tmp_path / "data"
    repo_root.mkdir(parents=True)
    data_root.mkdir(parents=True)
    construction_ids = ("slurp:train:construct-1", "slurp:train:construct-2")
    evaluation_ids = ("slurp:train:evaluate-1", "slurp:train:evaluate-2")
    construction_path = repo_root / "construction.json"
    evaluation_path = repo_root / "evaluation.json"
    construction_sha = _write_roster(
        construction_path,
        roster_id="SYNTHETIC-CONSTRUCTION",
        role="construction",
        sample_ids=construction_ids,
    )
    evaluation_sha = _write_roster(
        evaluation_path,
        roster_id="SYNTHETIC-EVALUATION",
        role="evaluation",
        sample_ids=evaluation_ids,
    )
    records = (_record(1, construction_sha), _record(2, construction_sha))
    artifact_output = {
        "schema": OUTPUT_SCHEMA,
        "status": "provisional",
        "materialization_id": "synthetic-candidates",
        "interpretation": "Proposal provenance only.",
        "provenance": {
            "materialization_config_sha256": "9" * 64,
            "construction_roster_sha256": construction_sha,
        },
        "samples": [
            {
                "source_sample_id": record.source.source_sample_id,
                "proposal_result_sha256": record.validation.result_sha256,
                "records": [record.as_json()],
            }
            for record in records
        ],
    }
    artifact_path = data_root / "provisional" / "candidates.json"
    artifact_receipt = prepare_artifact(
        artifact_path,
        kind=ARTIFACT_KIND,
        inputs={
            "construction_roster_sha256": construction_sha,
            "materialization_config_sha256": "9" * 64,
            "implementation_sha256": "6" * 64,
        },
        producer=lambda: artifact_output,
        contact_class="model-free",
    )
    artifact_output_sha = json.loads(artifact_path.read_bytes())["output_sha256"]
    source_rows = [
        {
            "record_sha256": record.record_sha256,
            "source": record.source.as_json(),
            "supporting_source_refs": [
                ref.as_json() for ref in record.supporting_source_refs
            ],
            "contradicting_source_refs": [],
        }
        for record in records
    ]
    implementation_sha = hash_stable_file(
        Path(__file__).parents[2]
        / "src/speech_aware_evidence_acquisition/rails/candidate_experience_memory.py",
        "implementation",
    )[1]
    attestation_output = {
        "schema": SOURCE_ATTESTATION_SCHEMA,
        "status": "source-attested",
        "candidate_artifact_sha256": artifact_receipt["sha256"],
        "candidate_output_sha256": artifact_output_sha,
        "materialization_config_sha256": "9" * 64,
        "construction_roster_sha256": construction_sha,
        "implementation_sha256": implementation_sha,
        "materializer_implementation_sha256": "6" * 64,
        "records": source_rows,
        "interpretation": (
            "Model-free proposal source correspondence; this is not evaluation "
            "evidence or admission."
        ),
    }
    attestation_path = data_root / "prepared" / "source-attestation.json"
    attestation_receipt = prepare_artifact(
        attestation_path,
        kind=SOURCE_ATTESTATION_KIND,
        inputs={key: attestation_output[key] for key in (
            "candidate_artifact_sha256", "candidate_output_sha256",
            "materialization_config_sha256", "construction_roster_sha256",
            "materializer_implementation_sha256", "implementation_sha256",
        )},
        producer=lambda: attestation_output,
        contact_class="model-free",
    )
    attestation_output_sha = json.loads(
        attestation_path.read_bytes()
    )["output_sha256"]
    plan = ExecutionPlan(
        run_id="SAEA-SYNTHETIC-CANDIDATE-EVALUATION",
        attempt_id="attempt-synthetic-candidate-evaluation",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="slurp",
        split_role="discovery",
        split_identity_hash=split_identity_hash(
            prefixed("slurp", evaluation_ids)
        ),
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=10,
        protocol_hash="8" * 64,
    ).validate()
    ordered = [records[1].record_sha256, records[0].record_sha256]
    decision = {
        "schema": DECISION_SCHEMA,
        "action": "evaluate-provisional-pack",
        "admission": "none",
        "run_id": plan.run_id,
        "attempt_id": plan.attempt_id,
        "candidate_artifact_sha256": artifact_receipt["sha256"],
        "candidate_output_sha256": artifact_output_sha,
        "source_attestation_sha256": attestation_receipt["sha256"],
        "construction_roster_sha256": construction_sha,
        "evaluation_roster_sha256": evaluation_sha,
        "ordered_record_sha256s": ordered,
        "task_id": "slurp",
        "component_tags": ["org"],
        "allowed_roles": ["reviewer"],
    }
    decision_path = repo_root / "decision.json"
    decision_path.write_bytes(canonical_bytes(decision))
    base = json.loads((
        Path(__file__).resolve().parents[2]
        / "configs/baseline/slurp-native-dual-store-train-fold-b-held-v1.json"
    ).read_text())
    config = {
        "native_episode": base["native_episode"],
        "candidate_experience_memory": {
            "artifact": {
                "data_relpath": "provisional/candidates.json",
                "sha256": artifact_receipt["sha256"],
                "output_sha256": artifact_output_sha,
            },
            "source_attestation": {
                "data_relpath": "prepared/source-attestation.json",
                "sha256": attestation_receipt["sha256"],
                "output_sha256": attestation_output_sha,
            },
            "construction_roster": {
                "repo_relpath": "construction.json",
                "sha256": construction_sha,
            },
            "evaluation_roster": {
                "repo_relpath": "evaluation.json",
                "sha256": evaluation_sha,
            },
            "evaluation_decision": {
                "repo_relpath": "decision.json",
                "sha256": _sha(decision_path),
            },
            "ordered_record_sha256s": ordered,
            "task_id": "slurp",
            "component_tags": ["org"],
            "allowed_roles": ["reviewer"],
        }
    }
    return {
        "repo_root": repo_root,
        "data_root": data_root,
        "config": config,
        "plan": plan,
        "evaluation_ids": evaluation_ids,
        "records": records,
        "decision_path": decision_path,
    }


def _load(world: dict[str, object]):
    return load_candidate_experience_memory(
        world["config"],
        repo_root=world["repo_root"],
        data_root=world["data_root"],
        carrier_lock_key="slurp",
        plan=world["plan"],
        sample_ids=world["evaluation_ids"],
        program=default_phase_program("phase-native-review-revise-v1"),
        tool_specs={
            "reviewer": {
                "allowed_tools": ("saea-tool-corrective-memory-v1",),
            }
        },
    )


def test_loader_preserves_declared_pack_order_and_all_structural_matches(tmp_path):
    world = _world(tmp_path)
    loaded = _load(world)
    context = SimpleNamespace(
        prior_response_sha256s=("a" * 64,),
        query_state=None,
        agent_states=(),
    )
    selection = loaded.select(next_phase="reviewer", context=context)
    expected = [world["records"][1].record_sha256, world["records"][0].record_sha256]
    assert [row["record_sha256"] for row in selection.visible["selected_records"]] == expected
    assert selection.lineage["ordered_pack_record_sha256s"] == expected
    with pytest.raises(ExperienceMemoryError, match="admitted"):
        ExperienceMemoryCatalog(
            "still-admitted-only", 1, "1" * 64,
            loaded.construction_roster_sha256,
            frozenset(("slurp:train:construct-1", "slurp:train:construct-2")),
            loaded.records,
        )


def test_empty_pack_is_explicit_and_supplies_no_guidance(tmp_path):
    world = _world(tmp_path)
    binding = world["config"]["candidate_experience_memory"]
    binding["ordered_record_sha256s"] = []
    decision = json.loads(world["decision_path"].read_bytes())
    decision["ordered_record_sha256s"] = []
    world["decision_path"].write_bytes(canonical_bytes(decision))
    binding["evaluation_decision"]["sha256"] = _sha(world["decision_path"])
    loaded = _load(world)
    context = SimpleNamespace(
        prior_response_sha256s=("a" * 64,), query_state=None, agent_states=()
    )
    assert loaded.select(
        next_phase="reviewer", context=context
    ).visible["selected_records"] == []


def test_correctly_rehashed_unrelated_decision_is_refused(tmp_path):
    world = _world(tmp_path)
    decision = json.loads(world["decision_path"].read_bytes())
    decision["action"] = "admit-best-candidate"
    world["decision_path"].write_bytes(canonical_bytes(decision))
    binding = world["config"]["candidate_experience_memory"]
    binding["evaluation_decision"]["sha256"] = _sha(world["decision_path"])
    with pytest.raises(CandidateExperienceMemoryError, match="actual plan"):
        _load(world)


def test_overlap_and_oversized_pack_are_refused(tmp_path):
    world = _world(tmp_path)
    evaluation = json.loads(
        (world["repo_root"] / "evaluation.json").read_text()
    )
    evaluation["items"][0]["sample_id"] = "slurp:train:construct-1"
    evaluation["split_identity_hash"] = split_identity_hash(
        prefixed("slurp", [row["sample_id"] for row in evaluation["items"]])
    )
    path = world["repo_root"] / "evaluation-mutated.json"
    write_roster(evaluation, path)
    binding = world["config"]["candidate_experience_memory"]
    binding["evaluation_roster"] = {
        "repo_relpath": "evaluation-mutated.json", "sha256": _sha(path)
    }
    with pytest.raises(CandidateExperienceMemoryError, match="overlap"):
        _load(world)

    world = _world(tmp_path / "second")
    binding = world["config"]["candidate_experience_memory"]
    binding["ordered_record_sha256s"] = [f"{index:064x}" for index in range(33)]
    with pytest.raises(CandidateExperienceMemoryError, match="runtime bound"):
        _load(world)



@pytest.mark.parametrize("mutation", ("dev", "artifact", "foreign-attempt", "solver", "dual"))
def test_actual_evaluation_scope_is_enforced(tmp_path, mutation):
    from dataclasses import replace

    world = _world(tmp_path)
    binding = world["config"]["candidate_experience_memory"]
    if mutation == "dev":
        world["evaluation_ids"] = ("slurp:dev:foreign", *world["evaluation_ids"][1:])
    elif mutation == "artifact":
        world["config"]["result_kind"] = "artifact"
    elif mutation == "foreign-attempt":
        world["plan"] = replace(world["plan"], attempt_id="attempt-unregistered")
    elif mutation == "solver":
        binding["allowed_roles"] = ["solver"]
    else:
        world["config"]["experience_memory"] = {}
    with pytest.raises(CandidateExperienceMemoryError):
        _load(world)


def test_attestation_inputs_cannot_be_rehashed_away(tmp_path):
    world = _world(tmp_path)
    binding = world["config"]["candidate_experience_memory"]
    path = world["data_root"] / binding["source_attestation"]["data_relpath"]
    wrapper = json.loads(path.read_bytes())
    wrapper["inputs"]["candidate_artifact_sha256"] = "0" * 64
    path.write_bytes(canonical_bytes(wrapper))
    binding["source_attestation"]["sha256"] = _sha(path)
    decision = json.loads(world["decision_path"].read_bytes())
    decision["source_attestation_sha256"] = _sha(path)
    world["decision_path"].write_bytes(canonical_bytes(decision))
    binding["evaluation_decision"]["sha256"] = _sha(world["decision_path"])
    with pytest.raises(CandidateExperienceMemoryError, match="source attestation"):
        _load(world)


def test_runtime_loader_never_reopens_materialization_or_outcomes(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core import provisional_candidate_materialization
    from speech_aware_evidence_acquisition.rails import reward_link_io

    world = _world(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("answering runtime cannot inspect outcome archives")

    monkeypatch.setattr(provisional_candidate_materialization, "prepare_provisional_candidates", forbidden)
    monkeypatch.setattr(reward_link_io, "read_verified_reward_link_artifact", forbidden)
    assert _load(world).records == (world["records"][1], world["records"][0])


@pytest.mark.parametrize("valid", (True, False))
def test_flight_preflight_enforces_actual_candidate_binding_before_contact(tmp_path, valid):
    from dataclasses import replace
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError

    world = _world(tmp_path)
    values = dict(
        world["config"], policy="phase-native-review-revise-v1",
        model_lock_key="qwen3-omni-30b-a3b-instruct-gguf",
    )
    runtime = FlightRuntime.__new__(FlightRuntime)
    runtime._repo_root = world["repo_root"]
    runtime._data_root = world["data_root"]
    runtime._runtime_root = tmp_path
    runtime._composed = SimpleNamespace(values=values)
    runtime._adapter = SimpleNamespace()
    runtime._samples = tuple(SimpleNamespace(sample_id=item) for item in world["evaluation_ids"])
    runtime._require_prior_stages = lambda _stage: None
    runtime._prepare = lambda: (values, "slurp", "TRAIN-EVALUATION", world["plan"].split_identity_hash)
    selected_plan = (
        world["plan"] if valid else replace(world["plan"], attempt_id="attempt-unregistered")
    )
    runtime._build_execution_plan = lambda *_args: selected_plan
    runtime._phase_tool_specs = lambda _policy: {
        "reviewer": {"allowed_tools": ("saea-tool-corrective-memory-v1",)}
    }
    gate_called = []

    class VerifiedBeforeGate(Exception):
        pass

    def gate(*args, **kwargs):
        gate_called.append(True)
        assert runtime._candidate_experience_memory.records
        raise VerifiedBeforeGate

    runtime._gate_factory = gate
    with pytest.raises(VerifiedBeforeGate if valid else FlightRuntimeError):
        runtime.preflight()
    assert gate_called == ([True] if valid else [])
