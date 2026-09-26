"""Pure candidate edits over existing semantic rows, never release authority.

The caller must verify the generating run and include all transitive TRAIN
construction ancestry in evidence_groups. Output still enters the ordinary
semantic preparation/release path and disjoint evaluation checks. No model,
filesystem, scoring or knowledge activation occurs in this module.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence

from .hashing import content_hash
from .prepared_feedback import reject_non_latin_scripts
from .semantic_knowledge_build import _SLOT_KEYS, _object, _slot, _support

CONTRACT_SCHEMA = "saea-slot-value-edit-contract-v1"
PROPOSAL_SCHEMA = "saea-slot-value-edits-v1"
LIST_FIELDS = frozenset({"extraction_cues", "admissible_formats", "limitations"})
TEXT_FIELDS = frozenset({"missing_behavior", "ambiguity_behavior"})
VALUE_FIELDS = LIST_FIELDS | TEXT_FIELDS


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _base(rows):
    _require(
        isinstance(rows, Sequence)
        and not isinstance(rows, (str, bytes))
        and bool(rows),
        "base rows must be a nonempty sequence",
    )
    by_id = {}
    for row in rows:
        _object(row, "base slot row", _SLOT_KEYS)
        slot_id, _, _ = _slot(row)
        _support(row["source_support"], "base source support")
        _require(slot_id not in by_id, "duplicate base slot")
        by_id[slot_id] = row
    return by_id


def slot_value_edit_contract(
    rows,
    *,
    slot_ids,
    fields,
    evidence_groups,
    max_edits,
    max_field_chars,
):
    """Freeze a bounded editable surface without changing any existing row."""
    by_id = _base(rows)
    _require(
        isinstance(slot_ids, (list, tuple))
        and bool(slot_ids)
        and all(isinstance(sid, str) for sid in slot_ids)
        and len(set(slot_ids)) == len(slot_ids)
        and set(slot_ids) <= set(by_id),
        "editable slot IDs must be unique existing slots",
    )
    _require(
        isinstance(fields, (list, tuple))
        and bool(fields)
        and all(isinstance(field, str) for field in fields)
        and len(set(fields)) == len(fields)
        and set(fields) <= VALUE_FIELDS,
        "only explanatory value fields may change",
    )
    _require(
        type(max_edits) is int
        and 0 < max_edits <= len(slot_ids) * len(fields)
        and type(max_field_chars) is int
        and max_field_chars > 0,
        "edit count and field length must be bounded",
    )
    _require(
        isinstance(evidence_groups, Mapping) and bool(evidence_groups),
        "complete construction evidence groups are required",
    )
    groups = {}
    for group, ids in evidence_groups.items():
        _require(
            isinstance(group, str)
            and bool(group.strip())
            and isinstance(ids, (list, tuple))
            and bool(ids)
            and all(isinstance(s, str) and s.startswith("slurp:train:") for s in ids)
            and len(set(ids)) == len(ids),
            "evidence must retain unique TRAIN ancestry",
        )
        groups[group] = sorted(ids)
    document = {
        "schema": CONTRACT_SCHEMA,
        "base_rows_sha256": content_hash(rows),
        "editable": [
            {
                "slot_id": sid,
                "field": field,
                "previous_value_sha256": content_hash(by_id[sid][field]),
            }
            for sid in sorted(slot_ids)
            for field in sorted(fields)
        ],
        "evidence_groups": dict(sorted(groups.items())),
        "max_edits": max_edits,
        "max_field_chars": max_field_chars,
    }
    document["content_sha256"] = content_hash(document)
    return document


def _contract(contract):
    _require(
        isinstance(contract, Mapping) and contract.get("schema") == CONTRACT_SCHEMA,
        "wrong edit contract",
    )
    raw = {k: v for k, v in contract.items() if k != "content_sha256"}
    _require(
        contract.get("content_sha256") == content_hash(raw),
        "edit contract hash changed",
    )
    return contract


def slot_value_edit_response_format(contract):
    """Produce a source-specific typed schema; host validation remains required."""
    contract = _contract(contract)
    branches = []
    for target in contract["editable"]:
        text = {
            "type": "string",
            "minLength": 1,
            "maxLength": contract["max_field_chars"],
        }
        replacement = (
            {
                "type": "array",
                "minItems": 1,
                "maxItems": contract["max_field_chars"],
                "items": text,
            }
            if target["field"] in LIST_FIELDS
            else text
        )
        properties = {key: {"const": value} for key, value in target.items()}
        properties.update(
            replacement=replacement,
            evidence_group_ids={
                "type": "array",
                "minItems": 1,
                "maxItems": len(contract["evidence_groups"]),
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "enum": sorted(contract["evidence_groups"]),
                },
            },
        )
        branches.append(
            {
                "type": "object",
                "additionalProperties": False,
                "required": list(properties),
                "properties": properties,
            }
        )
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "slot_value_edits_v1",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["schema", "base_rows_sha256", "edits"],
                "properties": {
                    "schema": {"const": PROPOSAL_SCHEMA},
                    "base_rows_sha256": {"const": contract["base_rows_sha256"]},
                    "edits": {
                        "type": "array",
                        "maxItems": contract["max_edits"],
                        "items": {"oneOf": branches},
                    },
                },
            },
        },
    }


def apply_slot_value_edits(rows, proposal, *, contract, verified_generation_ref):
    """Validate the complete proposal before creating independently owned rows.

    Evidence citations explain an edit; every input group remains in optimizer
    provenance even when the generator cites only a subset or proposes no change.
    A caller-supplied source reference is not itself proof of model provenance.
    """
    contract, by_id = _contract(contract), _base(rows)
    _require(content_hash(rows) == contract["base_rows_sha256"], "base rows changed")
    _require(
        isinstance(verified_generation_ref, str)
        and re.fullmatch(r"artifact-run:[a-f0-9]{64}", verified_generation_ref),
        "verified generating artifact reference required",
    )
    _require(
        isinstance(proposal, Mapping)
        and set(proposal) == {"schema", "base_rows_sha256", "edits"}
        and proposal["schema"] == PROPOSAL_SCHEMA
        and proposal["base_rows_sha256"] == contract["base_rows_sha256"],
        "proposal schema or base binding differs",
    )
    operations = proposal["edits"]
    _require(
        isinstance(operations, list) and len(operations) <= contract["max_edits"],
        "too many or malformed edits",
    )
    allowed = {
        (e["slot_id"], e["field"]): e["previous_value_sha256"]
        for e in contract["editable"]
    }
    seen, validated = set(), []
    for edit in operations:
        _require(
            isinstance(edit, Mapping)
            and set(edit)
            == {
                "slot_id",
                "field",
                "previous_value_sha256",
                "replacement",
                "evidence_group_ids",
            },
            "wrong edit fields",
        )
        key = (edit["slot_id"], edit["field"])
        _require(
            all(isinstance(part, str) for part in key)
            and key in allowed
            and key not in seen
            and key[1] in VALUE_FIELDS,
            "unknown, duplicate or non-value edit",
        )
        _require(
            edit["previous_value_sha256"]
            == allowed[key]
            == content_hash(by_id[key[0]][key[1]]),
            "stale field replacement",
        )
        value = edit["replacement"]
        texts = value if key[1] in LIST_FIELDS else [value]
        _require(
            (
                isinstance(value, list)
                if key[1] in LIST_FIELDS
                else isinstance(value, str)
            )
            and bool(texts)
            and all(isinstance(t, str) and t.strip() for t in texts),
            "replacement has the wrong shape or is blank",
        )
        _require(
            len(set(texts)) == len(texts)
            and sum(len(t) for t in texts) <= contract["max_field_chars"],
            "replacement exceeds field bound or repeats text",
        )
        reject_non_latin_scripts(texts)
        groups = edit["evidence_group_ids"]
        _require(
            isinstance(groups, list)
            and bool(groups)
            and all(
                isinstance(g, str) and g in contract["evidence_groups"] for g in groups
            )
            and len(set(groups)) == len(groups),
            "unknown or duplicate evidence group",
        )
        _require(value != by_id[key[0]][key[1]], "unchanged field must be omitted")
        seen.add(key)
        validated.append(edit)
    revised = copy.deepcopy(list(rows))
    new_by_id = {row["slot_id"]: row for row in revised}
    ancestry = sorted(
        {sid for ids in contract["evidence_groups"].values() for sid in ids}
    )
    for edit in validated:
        row = new_by_id[edit["slot_id"]]
        row[edit["field"]] = copy.deepcopy(edit["replacement"])
        support = row["source_support"]
        support["source_sample_ids"] = sorted(
            set(support["source_sample_ids"]) | set(ancestry)
        )
        support["provenance_refs"] = sorted(
            set(support["provenance_refs"])
            | {
                verified_generation_ref,
                "knowledge-edit-contract:" + contract["content_sha256"],
            }
        )
    _base(revised)
    for sid, old in by_id.items():
        _require(
            _slot(old)[:2] == _slot(new_by_id[sid])[:2], "slot routing key changed"
        )
    return {
        "schema": "saea-slot-value-edit-result-v1",
        "admission": "candidate-only",
        "rows": revised,
        "base_rows_sha256": content_hash(rows),
        "proposal_sha256": content_hash(proposal),
        "contract_sha256": contract["content_sha256"],
        "changed_fields": [
            {"slot_id": e["slot_id"], "field": e["field"]} for e in validated
        ],
        "optimizer_construction_sample_ids": ancestry,
        "model_contacts_added": 0,
        "scorer_contacts_added": 0,
    }
