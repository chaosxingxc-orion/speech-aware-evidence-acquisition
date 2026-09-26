"""Read provisional model operations; never mutate or admit an experience."""
import hashlib
import json

from .prepared_text_source import verify_prepared_text_source
from ..rails.experience_consolidation import _load_snapshot
from ..rails.hashing import content_hash
from ..rails.prepared_feedback import reject_non_latin_scripts
from ..rails.system_group_update_context import PREPARED_SCHEMA, KIND, build_system_group_update_contexts


def parse_group_operations(raw_text, snapshot):
    """Preserve invalid model text and allow conflicts for the later batch stage."""
    records = _load_snapshot(snapshot)
    targets = {r.record_id for r in records}
    result = {"raw_text": raw_text, "raw_text_sha256": hashlib.sha256(raw_text.encode()).hexdigest(),
              "base_snapshot_sha256": snapshot["content_sha256"], "status": "invalid",
              "operations": None, "error": None}
    try:
        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("operation has duplicate keys")
                value[key] = item
            return value
        operations = json.loads(raw_text, object_pairs_hook=unique)
        if not isinstance(operations, list):
            raise ValueError("group operations must be a JSON array")
        reject_non_latin_scripts(operations)
        for operation in operations:
            if not isinstance(operation, dict) or set(operation) != {"operation", "id", "content"}:
                raise ValueError("operation fields differ")
            op, target, content = operation["operation"], operation["id"], operation["content"]
            if not isinstance(op, str) or op not in {"ADD", "UPDATE", "DELETE", "NONE"}:
                raise ValueError("unknown group operation")
            if op in {"UPDATE", "DELETE"}:
                if not isinstance(target, str) or target not in targets:
                    raise ValueError("operation targets an unknown frozen record")
            elif target is not None:
                raise ValueError("ADD and NONE cannot assign an identity")
            if not isinstance(content, str) or (not content.strip() if op in {"ADD", "UPDATE"} else content != ""):
                raise ValueError("operation content differs from its kind")
        result.update(status="valid", operations=operations)
    except (ValueError, TypeError) as error:
        result["error"] = str(error)
    return result


def read_system_group_operations(manifest_pin, *, repo_root, data_root):
    """Rebuild sealed group inputs and bind every parsed operation to their frozen base."""
    source = verify_prepared_text_source(
        manifest_pin, repo_root=repo_root, data_root=data_root, input_schema=PREPARED_SCHEMA,
        artifact_kind=KIND, rebuild_contexts=build_system_group_update_contexts)
    document = source.prepared_document
    entries = []
    for group in document["population"]:
        row = source.rows.get(group["sample_id"])
        if group["disposition"] == "ready":
            if row is None:
                raise ValueError("sealed group update population differs")
            parsed = parse_group_operations(row["text"], document["base_snapshot"])
            disposition = ("blocked-unusable-update" if row["status"] != "usable"
                           else "ready" if parsed["status"] == "valid"
                           else "blocked-invalid-operation")
        else:
            if row is not None:
                raise ValueError("unregistered update output for a held group")
            parsed, disposition = None, group["disposition"]
        entries.append({"sample_id": group["sample_id"], "disposition": disposition,
                        "update_response": row, "parsed": parsed,
                        "experience_source": group["experience_source"]})
    if set(source.rows) != set(document["ready_sample_ids"]):
        raise ValueError("sealed group update population differs")
    report = {
        "schema": "saea-system-group-operation-inputs-v1",
        "source_manifest_sha256": source.manifest_sha256,
        "source_construction_roster_sha256": document["source_construction_roster_sha256"],
        "full_construction_sample_ids": document["full_construction_sample_ids"],
        "base_snapshot": document["base_snapshot"], "population": entries,
        "round_id": document["round_id"],
        "runtime_authorized": False, "model_contacts_added": 0, "scorer_contacts_added": 0,
        "claim_boundary": "Provisional operation proposals; batch consolidation and typed source materialization remain required.",
    }
    report.update({k: document[k] for k in ("memory_construction", "round_policy_receipt") if k in document})
    report["content_sha256"] = content_hash(report)
    return report
