"""Join actual generated slot edits to the existing semantic release path.

No model is invoked here. A construction instruction is not an outcome: its
exact text must occur in the sealed generator request and its actual output must
materialize the released authored rows. Completion alone never proves that join.
"""
import hashlib
import json
from pathlib import Path

from .hashing import content_hash
from .semantic_knowledge_edits import apply_slot_value_edits, PROPOSAL_SCHEMA
from .system_text_policy import _read_pin, require, sha


def _require_executed_instruction(record, *, sample_id, instruction, arm):
    """Bind the current request's instruction, never a historical mention of it."""
    # VerifiedBundle.trace_records contains the validated trace payload, with
    # its outer channel/record_id already consumed by the shared verifier.
    require(isinstance(arm, str) and record.get("arm") == arm and "tool_id" not in record,
            "construction source is not the registered model request")
    sha(record.get("payload_sha256"))
    request = record.get("payload", {})
    require(request.get("sample_id") == sample_id and request.get("carrier_lock_key") == "slurp",
            "construction request sample or carrier differs")
    history = request.get("history", [])
    require(isinstance(history, list) and all(isinstance(item, dict) for item in history),
            "construction request history differs from the shared client")
    if not history:
        require(request.get("task_instruction") == instruction,
                "new construction instruction was not executed in the sealed generator request")
        return
    # FrozenCoreClient puts the current PhaseMaterial instruction in the final
    # CONTROL item. The top-level task contract is a different prompt component.
    control = history[-1]
    require(set(control) == {"turn", "role", "contact_id", "content", "content_sha256"}
            and control["role"] == "control"
            and all(item.get("role") == "agent_state" for item in history[:-1])
            and type(control["turn"]) is int and control["turn"] == len(history)
            and isinstance(control["contact_id"], str) and bool(control["contact_id"].strip())
            and control["content"] == instruction
            and control["content_sha256"] == hashlib.sha256(instruction.encode("utf-8")).hexdigest(),
            "new construction instruction was not executed in the current sealed control request")


def materialize_slot_construction(*, base_rows, contract, generation_pin, instruction, data_root):
    from ..core.bundle.verify import verify_bundle
    _read_pin(generation_pin, data_root)
    bundle = verify_bundle(Path(data_root) / generation_pin["relpath"])
    manifest = bundle.manifest
    require(manifest.get("status") == "COMPLETED" and bundle.attempt_state == "FINALIZED"
            and manifest.get("result_kind") == "artifact"
            and manifest.get("plan", {}).get("split_role") == "discovery"
            and manifest.get("plan", {}).get("carrier_lock_key") == "slurp",
            "construction requires a finalized registered discovery artifact generation")
    require(bundle.outputs_rows and all(r["sample_id"].startswith("slurp:train:") for r in bundle.outputs_rows),
            "construction generation must retain TRAIN source identities")
    sample_ids = [r["sample_id"] for r in bundle.outputs_rows]
    request_ids = [r.get("request_id") for r in bundle.outputs_rows]
    require(len(set(sample_ids)) == len(sample_ids)
            and all(isinstance(identity, str) and identity for identity in request_ids)
            and len(set(request_ids)) == len(request_ids), "construction output identities must be unique")
    groups = contract.get("evidence_groups", {})
    require(isinstance(groups, dict) and all(isinstance(ids, list) for ids in groups.values())
            and set(sample_ids) <= {sid for ids in groups.values() for sid in ids},
            "actual construction source is absent from cumulative evidence groups")
    edits = []
    for output in bundle.outputs_rows:
        record = bundle.trace_records.get(output["request_id"] + "/request", {})
        _require_executed_instruction(record, sample_id=output["sample_id"], instruction=instruction,
                                      arm=manifest.get("arm"))
        proposal = json.loads(output["text"])
        require(set(proposal) == {"schema", "base_rows_sha256", "edits"}
                and proposal["schema"] == PROPOSAL_SCHEMA
                and proposal["base_rows_sha256"] == content_hash(base_rows),
                "actual construction output differs from the frozen slot-edit contract")
        edits.extend(proposal["edits"])
    proposal = {"schema": PROPOSAL_SCHEMA, "base_rows_sha256": content_hash(base_rows), "edits": edits}
    result = apply_slot_value_edits(base_rows, proposal, contract=contract,
                                   verified_generation_ref="artifact-run:" + generation_pin["sha256"])
    result["generated_proposal"] = proposal
    return result


def verify_released_slot_construction(link, *, instruction, data_root, repo_root):
    """Rebuild the generated edit join and reverify the normal governed release."""
    from ..core.semantic_knowledge_preparation import prepare_semantic_knowledge_store
    require(set(link) == {"schema", "instruction_sha256", "knowledge", "base_rows", "edit_contract",
                         "generation", "registration", "completion"}
            and link["schema"] == "saea-system-text-construction-link-v1"
            and link["instruction_sha256"] == content_hash(instruction), "construction link fields differ")
    base_rows = json.loads(_read_pin(link["base_rows"], data_root))
    contract = json.loads(_read_pin(link["edit_contract"], data_root))
    materialized = materialize_slot_construction(base_rows=base_rows, contract=contract,
        generation_pin=link["generation"], instruction=instruction, data_root=data_root)
    registration = json.loads(_read_pin(link["registration"], repo_root))
    authored_pin = registration["authored_source"]
    authored_root = repo_root if authored_pin.get("root") == "repository" else data_root
    authored = json.loads(_read_pin({k: authored_pin[k] for k in ("relpath", "sha256")}, authored_root))
    require(authored["rows"] == materialized["rows"], "released source differs from generated slot edits")
    completion = json.loads(_read_pin(link["completion"], data_root))
    # The snapshot pin is a semantic content hash, not a file hash. Reuse the
    # shared release verifier, which checks both conventions and exact bytes.
    prepared = prepare_semantic_knowledge_store(Path(repo_root) / link["registration"]["relpath"],
                                                repo_root=Path(repo_root), data_root=Path(data_root))
    require(prepared["completion"] == completion and prepared["completion_pin"] == link["completion"],
            "shared semantic completion differs from construction link")
    require(link["knowledge"] == {k: completion[k] for k in ("snapshot", "release")},
            "construction release pins differ")
    return materialized
