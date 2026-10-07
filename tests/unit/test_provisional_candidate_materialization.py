# ruff: noqa: F811  # imported pytest fixture shares its requested name
from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from test_group_relative_feedback import source_pair  # noqa: F401
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

from speech_aware_evidence_acquisition.contracts import TraceRecord
from speech_aware_evidence_acquisition.core.delivery import native_abstention_records
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.core.preparation import (
    canonical_bytes,
    digest,
    prepare_artifact,
)
from speech_aware_evidence_acquisition.core.provisional_candidate_materialization import (
    MaterializationError,
    prepare_provisional_candidates,
)
from speech_aware_evidence_acquisition.rails.candidate_experience_memory import (
    prepare_candidate_experience_source_attestation,
)
from speech_aware_evidence_acquisition.rails.experience_memory import (
    ExperienceMemoryCatalog,
    ExperienceMemoryError,
    ExperienceRecord,
)
from speech_aware_evidence_acquisition.rails.training_proposal_context import (
    prepare_training_proposal_contexts,
    training_proposal_context_preparation_inputs,
)

pytest_plugins = ("test_bundle",)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))
    return _sha(path)


def _source(sample_id: str, option: int) -> dict[str, str]:
    digit = str(option)
    return {
        "partition_role": "train",
        "source_sample_id": sample_id,
        "trajectory_sha256": digit * 64,
        "action_sha256": chr(96 + option) * 64,
        "response_sha256": chr(98 + option) * 64,
        "outcome_sha256": chr(100 + option) * 64,
    }


def _proposal(
    *,
    primary: str = "option-2",
    supporting: list[str] | None = None,
    contradicting: list[str] | None = None,
) -> dict[str, object]:
    return {
        "kind": "corrective-experience",
        "diagnosis": "The first option omitted a necessary distinction.",
        "guidance": "Retain the explicit distinction when this state recurs.",
        "limitations": ["This candidate still requires disjoint evaluation."],
        "applicability": {
            "task_ids": ["slurp"],
            "phases": ["solver"],
            "component_tags": ["org"],
            "required_conditions": ["state:prior-response-present"],
            "excluded_conditions": ["state:prior-response-absent"],
        },
        "primary_option": primary,
        "supporting_options": supporting or [primary],
        "contradicting_options": contradicting or ["option-1"],
    }


@pytest.fixture()
def materialization_world(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.provisional_candidate_materialization as module
    import speech_aware_evidence_acquisition.rails.training_proposal_context as proposal_module

    data_root = tmp_path / "data"
    sample_ids = ("slurp:train:1", "slurp:train:2")
    contexts = []
    for sample_id in sample_ids:
        contexts.append(
            {
                "source_sample_id": sample_id,
                "source_feedback_sha256": hashlib.sha256(sample_id.encode()).hexdigest(),
                "candidate_bindings": [
                    {
                        "label": f"option-{option}",
                        "candidate_id": f"candidate-{option}",
                        "reward_link_sha256": str(6 + option) * 64,
                        "source": _source(sample_id, option),
                    }
                    for option in (1, 2)
                ],
                "model_context": {"task_family": "slurp", "candidates": []},
                "model_context_sha256": digest(
                    {"task_family": "slurp", "candidates": []}
                ),
            }
        )
    prepared_output = {
        "schema": "saea-training-proposal-contexts-v2",
        "status": "source-verified",
        "role": "training-feedback-proposal",
        "construction_roster_sha256": "d" * 64,
        "feedback_sha256": "e" * 64,
        "sources": [],
        "contexts": contexts,
    }
    source_bindings_path = data_root / "prepared" / "source-bindings.json"
    source_bindings = [{"fixture": "source-a"}, {"fixture": "source-b"}]
    source_bindings_sha = _write_json(source_bindings_path, source_bindings)
    def rebuild(value):
        if value != source_bindings:
            raise AssertionError("wrong source bindings")
        return copy.deepcopy(prepared_output)

    monkeypatch.setattr(module, "build_training_proposal_contexts", rebuild)
    monkeypatch.setattr(proposal_module, "build_training_proposal_contexts", rebuild)
    prepared_path = data_root / "prepared" / "proposal-contexts.json"
    prepared_inputs = training_proposal_context_preparation_inputs(prepared_output)
    prepared_receipt = prepare_artifact(
        prepared_path,
        kind="training-proposal-contexts",
        inputs=prepared_inputs,
        producer=lambda: prepared_output,
        contact_class="model-free",
    )
    roster = {
        "schema": "saea-roster-receipt-v1",
        "roster_id": "SLURP-TRAIN-CONSTRUCTION",
        "carrier_lock_key": "slurp",
        "split_role": "discovery",
        "roster_role": "construction",
        "seed": 7,
        "per_stratum": {"all": 2},
        "strata_counts": {"all": 2},
        "items": [
            {"sample_id": sample_id, "stratum": "all"} for sample_id in sample_ids
        ],
        "excluded_count": 0,
        "split_identity_hash": split_identity_hash(prefixed("slurp", sample_ids)),
    }
    # This fixture uses the construction identity already carried by the exact
    # prepared contexts. Roster parsing is monkeypatched only at its hash
    # formula boundary; materializer joins still use the real item bytes.
    roster_path = data_root / "coordination" / "construction-roster.json"
    roster_sha = _write_json(roster_path, roster)
    prepared_output["construction_roster_sha256"] = roster_sha
    prepared_path.unlink()
    prepared_inputs = training_proposal_context_preparation_inputs(prepared_output)
    prepared_receipt = prepare_artifact(
        prepared_path,
        kind="training-proposal-contexts",
        inputs=prepared_inputs,
        producer=lambda: prepared_output,
        contact_class="model-free",
    )

    decision_path = data_root / "coordination" / "materialization-decision.json"
    protocol_path = data_root / "coordination" / "proposal-protocol.json"
    manifest_path = data_root / "runs" / "proposal" / "attempt" / "run-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    outputs_path = manifest_path.parent / "proposal.outputs.jsonl"

    def install_outputs(proposals_by_sample=None):
        proposals_by_sample = proposals_by_sample or {
            sample_ids[0]: [_proposal()], sample_ids[1]: []
        }
        rows = []
        for sample_id in sample_ids:
            content = json.dumps(
                {"status": "provisional", "proposals": proposals_by_sample[sample_id]},
                sort_keys=True,
                separators=(",", ":"),
            )
            rows.append(
                {
                    "sample_id": sample_id,
                    "artifact_role": "training-feedback-proposal",
                    "artifact_content": content,
                    "artifact_content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                    "artifact_source_sha256": prepared_receipt["sha256"],
                    "text": content,
                }
            )
        outputs_path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        return rows

    rows = install_outputs()
    contract = {
        "id": "training-feedback-proposal-v1",
        "prepared_contexts": {
            "data_relpath": "prepared/proposal-contexts.json",
            "sha256": prepared_receipt["sha256"],
            "output_sha256": digest(prepared_output),
        },
        "applicability": {
            "allowed_task_ids": ["slurp"],
            "allowed_roles": ["solver"],
            "allowed_component_tags": ["org", "use"],
        },
    }
    manifest = {
        "status": "COMPLETED",
        "result_kind": "artifact",
        "run_id": "SAEA-SYNTHETIC-TRAIN-PROPOSAL",
        "split": {
            "role": "discovery",
            "carrier_lock_key": "slurp",
            "identity_hash": "d" * 64,
            "ids": list(sample_ids),
        },
        "outputs": {"path": str(outputs_path), "sha256": _sha(outputs_path)},
        "artifact_result": {
            "schema": "saea-artifact-result-binding-v3",
            "role": "training-feedback-proposal",
            "construction_roster": {
                "repo_relpath": "docs/rosters/train.json",
                "sha256": roster_sha,
            },
            "content_contract": contract,
        },
    }
    manifest_sha = _write_json(manifest_path, manifest)
    protocol = {
        "schema": "saea-training-proposal-protocol-binding-v1",
        "proposal_run_id": manifest["run_id"],
        "runtime_protocol_hash": "9" * 64,
        "construction_roster_sha256": roster_sha,
        "prepared_contexts_sha256": prepared_receipt["sha256"],
    }
    manifest["protocol_hash"] = protocol["runtime_protocol_hash"]
    manifest_sha = _write_json(manifest_path, manifest)
    protocol_sha = _write_json(protocol_path, protocol)
    decision = {
        "schema": "saea-provisional-candidate-materialization-decision-v1",
        "action": "materialize-all-provisionally",
        "source_bundle_manifest_sha256": manifest_sha,
        "proposal_protocol_sha256": protocol_sha,
        "construction_roster_sha256": roster_sha,
        "selection": "none",
        "admission": "none",
    }
    decision_sha = _write_json(decision_path, decision)
    state = {"value": "FINALIZED"}

    def verified(path):
        assert Path(path) == manifest_path
        return VerifiedBundle(
            manifest_path=manifest_path,
            manifest=manifest,
            outputs_path=outputs_path,
            outputs_rows=tuple(rows),
            trace_records={},
            split_ids=frozenset(sample_ids),
            attempt_state=state["value"],
        )

    monkeypatch.setattr(module, "verify_bundle", verified)
    config = {
        "schema": "saea-provisional-candidate-materialization-config-v1",
        "materialization_id": "synthetic-provisional-candidates-v1",
        "max_candidates": 4,
        "proposal_bundle": {"path": str(manifest_path), "sha256": manifest_sha},
        "prepared_contexts": contract["prepared_contexts"],
        "source_bindings": {
            "path": str(source_bindings_path),
            "sha256": source_bindings_sha,
        },
        "materialization_decision": {
            "path": str(decision_path),
            "sha256": decision_sha,
        },
        "proposal_protocol": {"path": str(protocol_path), "sha256": protocol_sha},
        "construction_roster": {"path": str(roster_path), "sha256": roster_sha},
    }
    config_path = data_root / "coordination" / "materialization-config.json"
    config_sha = _write_json(config_path, config)
    return {
        "module": module,
        "data_root": data_root,
        "sample_ids": sample_ids,
        "contexts": prepared_output,
        "rows": rows,
        "install_outputs": install_outputs,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "state": state,
        "config": config,
        "config_path": config_path,
        "config_sha": config_sha,
        "paths": {
            "source_bindings": source_bindings_path,
            "prepared": prepared_path,
            "roster": roster_path,
            "decision": decision_path,
            "protocol": protocol_path,
        },
    }


def _prepare(world):
    return prepare_provisional_candidates(
        config_path=world["config_path"],
        expected_config_sha256=world["config_sha"],
        data_root=world["data_root"],
    )


def _source_derived_abstention_delivery(sample_id: str) -> dict[str, object]:
    source_contact = {
        "agent_contact_id": "synthetic-program:solver:0:" + sample_id,
        "request_id": "synthetic-final-request",
        "request_sha256": "1" * 64,
        "response_sha256": "2" * 64,
        "response_text_sha256": "3" * 64,
    }
    derived_id, _request, response = native_abstention_records(
        sample_id=sample_id,
        source_contact=source_contact,
        finish_reason="length",
    )
    return {
        "kind": "abstention",
        "delivered_solver": False,
        "derived_request_id": derived_id,
        "response_sha256": response["response_sha256"],
        "response_text_sha256": response["response_text_sha256"],
    }


def _rebind_public_prepared_contexts(world) -> None:
    """Republish reconstructed synthetic contexts and update exact public pins."""
    source_bindings = json.loads(world["paths"]["source_bindings"].read_bytes())
    world["paths"]["prepared"].unlink()
    receipt = prepare_training_proposal_contexts(
        source_bindings, world["paths"]["prepared"]
    )
    prepared = json.loads(world["paths"]["prepared"].read_bytes())
    pin = {
        "data_relpath": "prepared/proposal-contexts.json",
        "sha256": receipt["sha256"],
        "output_sha256": prepared["output_sha256"],
    }
    for row in world["rows"]:
        row["artifact_source_sha256"] = receipt["sha256"]
    world["config"]["prepared_contexts"] = pin
    world["manifest"]["artifact_result"]["content_contract"][
        "prepared_contexts"
    ] = pin
    world["config"]["proposal_bundle"]["sha256"] = _write_json(
        world["manifest_path"], world["manifest"]
    )
    protocol = json.loads(world["paths"]["protocol"].read_bytes())
    protocol["prepared_contexts_sha256"] = receipt["sha256"]
    world["config"]["proposal_protocol"]["sha256"] = _write_json(
        world["paths"]["protocol"], protocol
    )
    decision = json.loads(world["paths"]["decision"].read_bytes())
    decision["source_bundle_manifest_sha256"] = world["config"]["proposal_bundle"][
        "sha256"
    ]
    decision["proposal_protocol_sha256"] = world["config"]["proposal_protocol"][
        "sha256"
    ]
    world["config"]["materialization_decision"]["sha256"] = _write_json(
        world["paths"]["decision"], decision
    )
    world["config_sha"] = _write_json(world["config_path"], world["config"])


def test_empty_results_are_preserved_and_warm_materialization_is_identical(
    materialization_world,
):
    world = materialization_world
    rows = world["install_outputs"]({sample_id: [] for sample_id in world["sample_ids"]})
    world["rows"][:] = rows
    world["manifest"]["outputs"]["sha256"] = _sha(
        Path(world["manifest"]["outputs"]["path"])
    )
    world["manifest_path"].write_bytes(canonical_bytes(world["manifest"]))
    world["config"]["proposal_bundle"]["sha256"] = _sha(world["manifest_path"])
    decision = json.loads(world["paths"]["decision"].read_bytes())
    decision["source_bundle_manifest_sha256"] = world["config"]["proposal_bundle"][
        "sha256"
    ]
    world["config"]["materialization_decision"]["sha256"] = _write_json(
        world["paths"]["decision"], decision
    )
    world["config_sha"] = _write_json(world["config_path"], world["config"])

    first = _prepare(world)
    second = _prepare(world)
    output = json.loads(Path(first["path"]).read_bytes())["output"]
    assert output["status"] == "provisional"
    assert [sample["records"] for sample in output["samples"]] == [[], []]
    assert first["cache"] == "cold"
    assert second["cache"] == "warm"
    assert first["sha256"] == second["sha256"]


def test_maps_options_to_real_hidden_sources_without_reordering(materialization_world):
    world = materialization_world
    receipt = _prepare(world)
    output = json.loads(Path(receipt["path"]).read_bytes())["output"]
    first = output["samples"][0]
    assert first["source_sample_id"] == world["sample_ids"][0]
    record = first["records"][0]
    assert record["source"] == _source(world["sample_ids"][0], 2)
    assert [ref["ref_id"] for ref in record["supporting_source_refs"]] == [
        "reward-link:" + "8" * 64
    ]
    assert record["supporting_source_refs"][0]["sha256"] == "8" * 64
    from speech_aware_evidence_acquisition.rails.experience_memory_sources import (
        reward_link_hash_source_ref,
    )
    assert record["supporting_source_refs"][0] == reward_link_hash_source_ref("8" * 64).as_json()
    assert [ref["ref_id"] for ref in record["contradicting_source_refs"]] == [
        "reward-link:" + "7" * 64
    ]
    assert record["validation"] == {
        "status": "provisional",
        "decision_sha256": world["config"]["materialization_decision"]["sha256"],
        "protocol_sha256": world["config"]["proposal_protocol"]["sha256"],
        "roster_sha256": world["config"]["construction_roster"]["sha256"],
        "result_sha256": world["rows"][0]["artifact_content_sha256"],
    }
    assert output["interpretation"] == (
        "Proposal provenance only; these provisional candidates are not evaluation "
        "evidence and are not admitted runtime memory."
    )


def test_public_materialization_accepts_source_derived_abstention_binding(
    materialization_world,
):
    world = materialization_world
    binding = world["contexts"]["contexts"][0]["candidate_bindings"][1]
    binding["delivery"] = _source_derived_abstention_delivery(world["sample_ids"][0])
    _rebind_public_prepared_contexts(world)

    receipt = _prepare(world)
    output = json.loads(Path(receipt["path"]).read_bytes())["output"]
    assert output["samples"][0]["records"][0]["source"] == _source(
        world["sample_ids"][0], 2
    )


@pytest.mark.parametrize(
    "case", ["forged_delivery", "extra_delivery_field", "extra_binding_field"]
)
def test_public_materialization_refuses_forged_abstention_binding(
    materialization_world, case,
):
    world = materialization_world
    binding = world["contexts"]["contexts"][0]["candidate_bindings"][1]
    binding["delivery"] = _source_derived_abstention_delivery(world["sample_ids"][0])
    if case == "forged_delivery":
        binding["delivery"]["kind"] = "unknown"
    elif case == "extra_delivery_field":
        binding["delivery"]["unexpected"] = "forged"
    else:
        binding["unexpected"] = "forged"
    _rebind_public_prepared_contexts(world)

    with pytest.raises(MaterializationError, match="candidate binding|delivery"):
        _prepare(world)


@pytest.mark.parametrize("bad_label", ["option-9", "candidate-2"])
def test_unknown_or_foreign_labels_are_refused(materialization_world, bad_label):
    world = materialization_world
    proposals = {
        world["sample_ids"][0]: [
            _proposal(primary=bad_label, supporting=[bad_label])
        ],
        world["sample_ids"][1]: [],
    }
    rows = world["install_outputs"](proposals)
    world["rows"][:] = rows
    with pytest.raises(MaterializationError, match="canonical typed proposal"):
        _prepare(world)


@pytest.mark.parametrize("name", ["source_bindings", "prepared", "roster"])
def test_source_prepared_or_roster_byte_mutation_is_refused(materialization_world, name):
    world = materialization_world
    path = world["paths"][name]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(MaterializationError, match="hash|prepared"):
        _prepare(world)


@pytest.mark.parametrize("mode", ["missing", "duplicate"])
def test_result_rows_must_join_the_exact_construction_roster(materialization_world, mode):
    world = materialization_world
    if mode == "missing":
        world["rows"].pop()
    else:
        world["rows"].append(copy.deepcopy(world["rows"][0]))
    with pytest.raises(MaterializationError, match="duplicate|exact construction roster"):
        _prepare(world)


def test_fake_model_authored_provenance_is_refused(materialization_world):
    world = materialization_world
    content = json.loads(world["rows"][0]["artifact_content"])
    content["proposals"][0]["validation"] = {"status": "admitted"}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":"))
    world["rows"][0]["artifact_content"] = encoded
    world["rows"][0]["artifact_content_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    with pytest.raises(MaterializationError, match="canonical typed proposal"):
        _prepare(world)


def test_actual_bundle_state_must_be_finalized(materialization_world):
    world = materialization_world
    world["state"]["value"] = "OPENED"
    with pytest.raises(MaterializationError, match="FINALIZED"):
        _prepare(world)


@pytest.mark.parametrize("document", ["protocol_run", "protocol_hash", "decision"])
def test_correctly_rehashed_but_unrelated_provenance_is_refused(
    materialization_world, document
):
    world = materialization_world
    path = world["paths"]["protocol" if document.startswith("protocol_") else document]
    value = json.loads(path.read_bytes())
    if document.startswith("protocol_"):
        if document == "protocol_run":
            value["proposal_run_id"] = "ANOTHER-PROPOSAL-RUN"
        else:
            value["runtime_protocol_hash"] = "0" * 64
        new_sha = _write_json(path, value)
        world["config"]["proposal_protocol"]["sha256"] = new_sha
        decision = json.loads(world["paths"]["decision"].read_bytes())
        decision["proposal_protocol_sha256"] = new_sha
        world["config"]["materialization_decision"]["sha256"] = _write_json(
            world["paths"]["decision"], decision
        )
        match = "verified proposal inputs"
    else:
        value["action"] = "select-best-and-admit"
        world["config"]["materialization_decision"]["sha256"] = _write_json(
            path, value
        )
        match = "without selection or admission"
    world["config_sha"] = _write_json(world["config_path"], world["config"])
    with pytest.raises(MaterializationError, match=match):
        _prepare(world)


def test_pinned_config_and_candidate_bound_are_enforced(materialization_world):
    world = materialization_world
    with pytest.raises(MaterializationError, match="config hash"):
        prepare_provisional_candidates(
            config_path=world["config_path"],
            expected_config_sha256="0" * 64,
            data_root=world["data_root"],
        )

    world["config"]["max_candidates"] = 0
    world["config_sha"] = _write_json(world["config_path"], world["config"])
    with pytest.raises(MaterializationError, match="selection or truncation"):
        _prepare(world)


def test_mutated_input_is_refused_before_preparation_publishes(
    materialization_world, monkeypatch
):
    world = materialization_world
    module = world["module"]
    original = module._validate_decision_binding

    def mutate_after_validation(*args, **kwargs):
        original(*args, **kwargs)
        source = world["paths"]["source_bindings"]
        source.write_bytes(source.read_bytes() + b" ")

    monkeypatch.setattr(module, "_validate_decision_binding", mutate_after_validation)
    monkeypatch.setattr(
        module,
        "prepare_artifact",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("prepare_artifact must remain behind input guards")
        ),
    )
    output_path = (
        world["data_root"]
        / "provisional"
        / "experience-candidates"
        / "synthetic-provisional-candidates-v1.json"
    )
    with pytest.raises(MaterializationError, match="source bindings changed"):
        _prepare(world)
    assert not output_path.exists()


def test_shared_cli_passes_only_pinned_inputs(materialization_world, monkeypatch, capsys):
    world = materialization_world
    seen = {}

    def fake_prepare(**kwargs):
        seen.update(kwargs)
        return {"path": "/tmp/provisional.json", "sha256": "a" * 64}

    monkeypatch.setattr(world["module"], "prepare_provisional_candidates", fake_prepare)
    assert world["module"].main(
        [
            "--config",
            str(world["config_path"]),
            "--config-sha256",
            world["config_sha"],
            "--data-root",
            str(world["data_root"]),
        ]
    ) == 0
    assert seen == {
        "config_path": world["config_path"],
        "expected_config_sha256": world["config_sha"],
        "data_root": world["data_root"],
    }
    assert json.loads(capsys.readouterr().out)["sha256"] == "a" * 64


def test_provisional_records_remain_outside_admitted_runtime_catalog(
    materialization_world,
):
    world = materialization_world
    receipt = _prepare(world)
    output = json.loads(Path(receipt["path"]).read_bytes())["output"]
    record = ExperienceRecord.from_json(output["samples"][0]["records"][0])
    with pytest.raises(ExperienceMemoryError, match="admitted"):
        ExperienceMemoryCatalog(
            memory_id="must-refuse-provisional",
            memory_version=1,
            manifest_sha256=receipt["sha256"],
            train_construction_sha256=world["contexts"][
                "construction_roster_sha256"
            ],
            expected_train_sample_ids=frozenset(world["sample_ids"]),
            records=(record,),
        )


def _real_materialized_source(
    source_pair, synthetic_world, *, roles=("solver",)
):
    data_root = synthetic_world.data_root
    source_bindings_path = data_root / "prepared" / "whole-path-source-bindings.json"
    source_bindings_sha = _write_json(source_bindings_path, source_pair)
    prepared_path = data_root / "prepared" / "whole-path-proposal-contexts.json"
    prepared_receipt = prepare_training_proposal_contexts(source_pair, prepared_path)
    prepared_document = json.loads(prepared_path.read_bytes())
    prepared_output = prepared_document["output"]
    sample_ids = tuple(
        context["source_sample_id"] for context in prepared_output["contexts"]
    )
    roster_path = Path(
        source_pair[0]["config"]["construction_roster"]["path"]
    ).resolve()
    roster_sha = _sha(roster_path)
    assert prepared_output["construction_roster_sha256"] == roster_sha

    source_manifest_path = Path(source_pair[0]["config"]["manifest"]["path"])
    source_manifest = json.loads(source_manifest_path.read_bytes())
    proposal_dir = data_root / "runs" / "synthetic-proposal" / "attempt-whole-path"
    proposal_dir.mkdir(parents=True)
    outputs_path = proposal_dir / "proposal.outputs.jsonl"
    trace_path = proposal_dir / "proposal.trace.jsonl"
    trace_manifest_path = proposal_dir / "proposal.trace-manifest.json"
    state_path = proposal_dir / "proposal-attempt.json"
    shutil.copyfile(source_manifest["outputs"]["path"], outputs_path)
    shutil.copyfile(source_manifest["raw_trace"]["path"], trace_path)
    shutil.copyfile(source_manifest["trace_manifest"]["path"], trace_manifest_path)
    shutil.copyfile(source_manifest["attempt"]["state_path"], state_path)

    contract = {
        "id": "training-feedback-proposal-v1",
        "prepared_contexts": {
            "data_relpath": "prepared/whole-path-proposal-contexts.json",
            "sha256": prepared_receipt["sha256"],
            "output_sha256": prepared_document["output_sha256"],
        },
        "applicability": {
            "allowed_task_ids": ["slurp"],
            "allowed_roles": list(roles),
            "allowed_component_tags": ["org", "use"],
        },
    }
    from speech_aware_evidence_acquisition.rails.training_feedback_artifacts import (
        build_training_feedback_artifact_validator,
    )

    validator = build_training_feedback_artifact_validator(contract, data_root=data_root)
    rows = [json.loads(line) for line in outputs_path.read_text().splitlines() if line]
    by_request = {}
    for index, row in enumerate(rows):
        content = {"status": "provisional", "proposals": []}
        if index == 0:
            proposal = _proposal()
            proposal["applicability"]["phases"] = list(roles)
            content["proposals"] = [proposal]
        raw = json.dumps(content)
        canonical = validator.canonicalize(raw, sample_id=row["sample_id"])
        row.update(
            text=raw,
            response_text_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            result_kind="artifact",
            artifact_role="training-feedback-proposal",
            artifact_content=canonical,
            artifact_content_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
            artifact_source_sha256=prepared_receipt["sha256"],
        )
        by_request[row["request_id"]] = row
    outputs_path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    records = []
    for line in trace_path.read_text().splitlines():
        document = json.loads(line)
        if document["record_id"].endswith("/response"):
            request_id = document["record_id"][: -len("/response")]
            if request_id in by_request:
                output = by_request[request_id]
                document["payload"]["text"] = output["text"]
                document["payload"]["response_text_sha256"] = output[
                    "response_text_sha256"
                ]
        records.append(
            TraceRecord(document["channel"], document["record_id"], document["payload"])
        )
    trace_path.write_text("".join(record.serialize() + "\n" for record in records))
    trace_manifest_path.write_text(
        json.dumps({"records": {record.record_id: record.content_hash() for record in records}})
    )

    proposal_manifest = copy.deepcopy(source_manifest)
    proposal_manifest.update(
        result_kind="artifact",
        artifact_result={
            "schema": "saea-artifact-result-binding-v3",
            "role": "training-feedback-proposal",
            "construction_roster": {
                "repo_relpath": "docs/rosters/synthetic-train.json",
                "sha256": roster_sha,
            },
            "content_contract": contract,
        },
        artifact_content_source={
            "path": str(prepared_path),
            "sha256": prepared_receipt["sha256"],
        },
        scorers=[],
        scores=None,
        outputs={"path": str(outputs_path), "sha256": _sha(outputs_path)},
        raw_trace={"path": str(trace_path), "sha256": _sha(trace_path)},
        trace_manifest={
            "path": str(trace_manifest_path),
            "sha256": _sha(trace_manifest_path),
        },
        attempt={
            **source_manifest["attempt"],
            "state_path": str(state_path),
        },
    )
    manifest_path = proposal_dir / "proposal.run-manifest.json"
    manifest_sha = _write_json(manifest_path, proposal_manifest)

    protocol_path = data_root / "coordination" / "whole-path-protocol.json"
    protocol_sha = _write_json(
        protocol_path,
        {
            "schema": "saea-training-proposal-protocol-binding-v1",
            "proposal_run_id": proposal_manifest["run_id"],
            "runtime_protocol_hash": proposal_manifest["protocol_hash"],
            "construction_roster_sha256": roster_sha,
            "prepared_contexts_sha256": prepared_receipt["sha256"],
        },
    )
    decision_path = data_root / "coordination" / "whole-path-decision.json"
    decision_sha = _write_json(
        decision_path,
        {
            "schema": "saea-provisional-candidate-materialization-decision-v1",
            "action": "materialize-all-provisionally",
            "source_bundle_manifest_sha256": manifest_sha,
            "proposal_protocol_sha256": protocol_sha,
            "construction_roster_sha256": roster_sha,
            "selection": "none",
            "admission": "none",
        },
    )
    config = {
        "schema": "saea-provisional-candidate-materialization-config-v1",
        "materialization_id": "whole-path-provisional-v1",
        "max_candidates": 4,
        "proposal_bundle": {"path": str(manifest_path), "sha256": manifest_sha},
        "prepared_contexts": contract["prepared_contexts"],
        "source_bindings": {
            "path": str(source_bindings_path),
            "sha256": source_bindings_sha,
        },
        "materialization_decision": {
            "path": str(decision_path),
            "sha256": decision_sha,
        },
        "proposal_protocol": {"path": str(protocol_path), "sha256": protocol_sha},
        "construction_roster": {"path": str(roster_path), "sha256": roster_sha},
    }
    config_path = data_root / "coordination" / "whole-path-config.json"
    config_sha = _write_json(config_path, config)
    receipt = prepare_provisional_candidates(
        config_path=config_path,
        expected_config_sha256=config_sha,
        data_root=data_root,
    )
    output = json.loads(Path(receipt["path"]).read_bytes())["output"]
    assert tuple(sample["source_sample_id"] for sample in output["samples"]) == sample_ids
    assert [len(sample["records"]) for sample in output["samples"]] == [1, 0]
    attestation = prepare_candidate_experience_source_attestation(
        config_path=config_path,
        expected_config_sha256=config_sha,
        data_root=data_root,
        candidate_artifact_relpath=(
            "provisional/experience-candidates/whole-path-provisional-v1.json"
        ),
        expected_candidate_sha256=receipt["sha256"],
        output_relpath="prepared/whole-path-candidate-source-attestation.json",
    )
    attested = json.loads(Path(attestation["path"]).read_bytes())["output"]
    assert attested["candidate_artifact_sha256"] == receipt["sha256"]
    assert attested["construction_roster_sha256"] == roster_sha
    assert attested["records"][0]["source"]["source_sample_id"] == sample_ids[0]
    assert attested["interpretation"].endswith(
        "this is not evaluation evidence or admission."
    )

    return {
        "data_root": data_root, "config": config, "config_path": config_path,
        "state_path": state_path, "receipt": receipt, "attestation": attestation,
        "roster_path": roster_path, "roster_sha": roster_sha, "sample_ids": sample_ids,
    }


def test_real_bundle_and_feedback_authority_complete_path_and_opened_refusal(
    source_pair, synthetic_world, tmp_path
):
    world = _real_materialized_source(source_pair, synthetic_world)
    data_root, config, config_path, state_path = (
        world[key] for key in ("data_root", "config", "config_path", "state_path")
    )
    state = json.loads(state_path.read_bytes())
    state["state"] = "OPENED"
    state_path.write_text(json.dumps(state))
    config["materialization_id"] = "whole-path-opened-must-refuse-v1"
    config_sha = _write_json(config_path, config)
    refused_path = (
        data_root
        / "provisional"
        / "experience-candidates"
        / "whole-path-opened-must-refuse-v1.json"
    )
    with pytest.raises(MaterializationError, match="FINALIZED"):
        prepare_provisional_candidates(
            config_path=config_path,
            expected_config_sha256=config_sha,
            data_root=data_root,
        )
    assert not refused_path.exists()



def _connected_candidate_native_source(
    source_pair, synthetic_world, tmp_path, monkeypatch, *, memory_call=True, empty_pack=False
):
    from dataclasses import replace
    from types import SimpleNamespace

    from test_candidate_experience_memory import _world
    from test_native_episode_runner import _ActualEpisodeHarness
    from test_rails_runner import _knowledge_snapshot

    from speech_aware_evidence_acquisition.analysis.native_tool_exposure import (
        analyze_verified_native_tool_exposure,
    )
    from speech_aware_evidence_acquisition.core import preparation_fit
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program

    source = _real_materialized_source(
        source_pair, synthetic_world, roles=("reviewer",)
    )
    world = _world(tmp_path / "evaluation")
    data_root = source["data_root"]
    raw = world["config"]["candidate_experience_memory"]
    for key, receipt in (
        ("artifact", source["receipt"]),
        ("source_attestation", source["attestation"]),
    ):
        path = Path(receipt["path"])
        raw[key] = {
            "data_relpath": str(path.relative_to(data_root)),
            "sha256": receipt["sha256"],
            "output_sha256": json.loads(path.read_bytes())["output_sha256"],
        }
    construction = world["repo_root"] / "construction.json"
    shutil.copyfile(source["roster_path"], construction)
    raw["construction_roster"]["sha256"] = _sha(construction)
    output = json.loads(Path(source["receipt"]["path"]).read_bytes())["output"]
    records = [
        ExperienceRecord.from_json(record)
        for sample in output["samples"] for record in sample["records"]
    ]
    raw["ordered_record_sha256s"] = (
        [] if empty_pack else [record.record_sha256 for record in records]
    )
    values = dict(
        world["config"], policy="phase-native-review-revise-v1",
        arm="speech-feature-query-native-tools",
        model_lock_key="qwen3-omni-30b-a3b-instruct-gguf",
        phase_tools={
            "reviewer": {
                "mode": "native-tools",
                "allowed_tools": ["saea-tool-corrective-memory-v1"],
                "knowledge_views": ["text"],
                "source_authority_role": "reviewer",
            }
        },
    )
    program = default_phase_program(values["policy"])
    plan = replace(
        world["plan"], planned_model_calls=len(world["evaluation_ids"]) * program.max_contacts,
        planned_speech_audio_seconds=1000,
    ).validate()
    decision = json.loads(world["decision_path"].read_bytes())
    decision.update(
        candidate_artifact_sha256=raw["artifact"]["sha256"],
        candidate_output_sha256=raw["artifact"]["output_sha256"],
        source_attestation_sha256=raw["source_attestation"]["sha256"],
        construction_roster_sha256=raw["construction_roster"]["sha256"],
        ordered_record_sha256s=raw["ordered_record_sha256s"],
    )
    raw["evaluation_decision"]["sha256"] = _write_json(world["decision_path"], decision)

    runtime = object.__new__(FlightRuntime)
    runtime._repo_root = world["repo_root"]
    runtime._data_root = data_root
    runtime._runtime_root = tmp_path
    runtime._composed = SimpleNamespace(values=values)
    runtime._model = runtime._dataset = runtime._baseline = {}
    runtime._adapter = SimpleNamespace()
    runtime._samples = tuple(
        SimpleNamespace(sample_id=item) for item in world["evaluation_ids"]
    )
    runtime._require_prior_stages = lambda _stage: None
    runtime._prepare = lambda: (values, "slurp", "TRAIN-EVALUATION", plan.split_identity_hash)
    runtime._build_execution_plan = lambda *_args: plan

    class ContactGateReached(Exception):
        pass

    def gate(*_args, **_kwargs):
        raise ContactGateReached

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Answering runtime must not reopen source outcomes")

    from speech_aware_evidence_acquisition.core import provisional_candidate_materialization
    from speech_aware_evidence_acquisition.rails import reward_link_io
    monkeypatch.setattr(
        provisional_candidate_materialization, "prepare_provisional_candidates", forbidden
    )
    monkeypatch.setattr(reward_link_io, "read_verified_reward_link_artifact", forbidden)
    runtime._gate_factory = gate
    with pytest.raises(ContactGateReached):
        runtime.preflight()
    memory = runtime._candidate_experience_memory
    assert [record.record_sha256 for record in memory.records] == raw["ordered_record_sha256s"]
    assert memory.artifact_sha256 == source["receipt"]["sha256"]

    harness = _ActualEpisodeHarness(
        tmp_path / "episode", sample_count=2, max_revisions=1,
        max_contacts=program.max_contacts, planner_actions=("REVISE", "ACCEPT"),
        reviewer_memory=memory, sample_ids=world["evaluation_ids"], execution_plan=plan,
        data_root=data_root,
    )
    if not memory_call:
        original_output = harness._output
        harness._output = lambda key: (
            "Review complete." if key[1] == "reviewer" else original_output(key)
        )
    runtime._adapter = harness.adapter
    runtime._samples = harness.samples
    assert runtime._data_root == harness.world.data_root
    runtime._split_id = "all"
    runtime._transport = harness.transport
    runtime._client = harness.client
    runtime._phase_program_material = {
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": harness.speech_bindings,
        "material_for_phase": harness.material_for_phase,
        "trace_sink": harness.trace,
        "review_for_phase": None,
    }
    runtime._continuous_phase_runner = run_continuous_program
    runtime._phase_planner_specs = lambda _policy: {}
    runtime._phase_decoding_params = lambda: {"temperature": 0, "max_tokens": 64}
    runtime._fit_base_plan = lambda actual_plan: actual_plan
    runtime._phase_tool_builder = None
    runtime._experience_memory = None
    runtime._speech_observations = None
    runtime._live_speech_config = None
    runtime._live_speech_source_bindings = {}
    runtime._phase_knowledge_catalog = lambda _snapshot: None
    runtime.assert_generation_lease = lambda: None
    runtime.speech_packet_bindings = lambda: harness.speech_bindings

    def fitted_request(request):
        harness.request_gate(request)
        fitted_request.receipts.append({"capacity_verified": False})

    fitted_request.receipts = []
    monkeypatch.setattr(
        preparation_fit, "build_native_contact_fit_gate", lambda *_args: fitted_request
    )
    try:
        rows, contacts, _kind, _dispatch, _phases = runtime._dispatch_phase_program(
            harness.client, plan, values["policy"]
        )
        runtime._output_rows = rows
        canonical = runtime._canonical_output_rows(harness.client)
    finally:
        harness.close()

    assert contacts == (16 if memory_call else 14)
    assert [row["sample_id"] for row in canonical] == list(world["evaluation_ids"])
    trace_path = harness.world.run_dir / f"{plan.run_id}.trace.jsonl"
    traces = {
        row["record_id"]: row["payload"]
        for row in (json.loads(line) for line in trace_path.read_text().splitlines())
    }
    phases = {
        result.sample_id: result.as_json()
        for summary in runtime._phase_summaries for result in summary.results
    }
    report = analyze_verified_native_tool_exposure(
        sample_ids=world["evaluation_ids"], controller_policy_id=values["policy"],
        phase_results=phases,
        output_rows={row["sample_id"]: row for row in canonical},
        trace_records=traces,
    )
    assert report["successful_call_count"] == (2 if memory_call else 0)
    assert report["exposed_successful_call_count"] == (2 if memory_call else 0)
    for sample_id in (world["evaluation_ids"] if memory_call else ()):
        for key in ((sample_id, "reviewer", 1, 2), (sample_id, "solver", 2, 1)):
            messages = harness.prepared[key]["rendered"]["messages"]
            tool = next(message for message in messages if message["role"] == "tool")
            selection = json.loads(tool["content"])["result"]
            assert [row["record_sha256"] for row in selection["selected_records"]] == (
                raw["ordered_record_sha256s"]
            )
            assert harness.events.index(("fit", key)) < harness.events.index(("dispatch", key))
    assert all(
        row["text"] == f"solver-answer:{row['sample_id']}:visit:2" for row in canonical
    )
    return {
        "world": world, "data_root": data_root, "values": values, "plan": plan,
        "canonical": canonical, "phases": phases, "traces": traces, "memory": memory,
    }


@pytest.mark.parametrize("empty_pack", [False, True])
def test_verified_source_reaches_runtime_dispatch_and_exact_native_memory_history(
    source_pair, synthetic_world, tmp_path, monkeypatch, empty_pack
):
    _connected_candidate_native_source(
        source_pair, synthetic_world, tmp_path, monkeypatch, empty_pack=empty_pack
    )
