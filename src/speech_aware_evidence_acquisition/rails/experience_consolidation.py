"""Apply one semantic consolidation plan to existing provisional experience records.

This pure construction step owns no model, execution, persistence or admission.
Callers must verify sealed proposal/consolidation sources and complete-system
feedback before supplying their pins. Hashes bind inputs; they do not authenticate
arbitrary caller-created evidence. Runtime still uses the existing memory loaders.
"""
from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence

from .experience_memory import ExperienceMemoryError, ExperienceRecord
from .hashing import content_hash

SNAPSHOT_SCHEMA = "saea-candidate-experience-snapshot-v1"
SCOPED_SNAPSHOT_SCHEMA = "saea-candidate-experience-snapshot-v2"
RECEIPT_SCHEMA = "saea-experience-consolidation-receipt-v1"
_SOURCE_KEYS = {
    "complete_system_feedback_sha256", "proposal_artifact_sha256",
    "consolidation_response_sha256",
}


class ConsolidationError(ValueError):
    """A construction snapshot or consolidation contract is invalid."""


def _require(condition, message):
    if not condition:
        raise ConsolidationError(message)


def _sha(value, label):
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value),
             f"{label} must be a lowercase SHA-256")
    return value


def _text(value, label):
    _require(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty")
    return value


def _signed(value):
    return {**value, "content_sha256": content_hash(value)}


def _candidate(record, construction, roster, scopes=None):
    _require(isinstance(record, ExperienceRecord), "proposal must be an ExperienceRecord")
    record.validate()
    _require(record.validation.status == "provisional"
             and record.superseded_by_record_id is None,
             "only active provisional experience is eligible")
    if scopes is not None:
        _require(record.train_construction_sha256 in scopes, "proposal has an unknown construction scope")
        construction = record.train_construction_sha256
        roster = frozenset(scopes[construction])
    _require(record.train_construction_sha256 == construction
             and record.validation.roster_sha256 == construction,
             "proposal construction binding differs")
    _require(record.source.partition_role == "train"
             and record.source.source_sample_id in roster,
             "proposal source is outside the pinned TRAIN roster")
    _require(all(ref.partition_role == "train"
                 for ref in record.supporting_source_refs + record.contradicting_source_refs),
             "proposal support and contradiction must remain TRAIN-only")


def _records(records, construction, roster, scopes=None):
    seen_ids, seen_semantics = set(), set()
    for record in records:
        _candidate(record, construction, roster, scopes)
        _require(record.record_id not in seen_ids, "duplicate active record identity")
        _require(record.semantic_hash() not in seen_semantics,
                 "duplicate active experience content")
        seen_ids.add(record.record_id)
        seen_semantics.add(record.semantic_hash())


def initialize_candidate_snapshot(
    *, memory_id: str, train_construction_sha256: str,
    expected_train_sample_ids: Sequence[str], records: Sequence[ExperienceRecord] = (),
) -> dict[str, object]:
    """Import provisional records without changing their immutable identities."""
    _text(memory_id, "memory ID")
    _sha(train_construction_sha256, "construction")
    _require(not isinstance(expected_train_sample_ids, (str, bytes)),
             "TRAIN roster must be a sequence")
    roster = tuple(expected_train_sample_ids)
    _require(roster and all(isinstance(s, str) and s.strip() for s in roster)
             and len(set(roster)) == len(roster), "TRAIN roster is empty or duplicated")
    values = tuple(records)
    _records(values, train_construction_sha256, frozenset(roster))
    # Import roots only: dropping an older revision's issued-ID history would
    # permit identity reuse. Continue an existing snapshot for later rounds.
    _require(all(record.revision == 1 for record in values),
             "initialize only root records; continue the original snapshot for revisions")
    return _signed({
        "schema": SNAPSHOT_SCHEMA, "scope": "provisional-construction-only",
        "memory_id": memory_id, "train_construction_sha256": train_construction_sha256,
        "train_sample_ids": sorted(roster), "parent_snapshot_sha256": None,
        "records": [record.as_json() for record in values],
        "issued_record_ids": sorted(record.record_id for record in values),
    })


def _load_snapshot(snapshot):
    _require(isinstance(snapshot, Mapping), "snapshot must be an object")
    expected = {
        "schema", "scope", "memory_id", "train_construction_sha256", "train_sample_ids",
        "parent_snapshot_sha256", "records", "issued_record_ids", "content_sha256",
    }
    scoped = snapshot.get("schema") == SCOPED_SNAPSHOT_SCHEMA
    if scoped:
        expected.add("construction_scopes")
    _require(set(snapshot) == expected, "snapshot fields differ")
    unsigned = {k: v for k, v in snapshot.items() if k != "content_sha256"}
    _require(snapshot["content_sha256"] == content_hash(unsigned), "snapshot fingerprint differs")
    _require(snapshot["schema"] in {SNAPSHOT_SCHEMA, SCOPED_SNAPSHOT_SCHEMA}
             and snapshot["scope"] == "provisional-construction-only", "snapshot scope differs")
    _text(snapshot["memory_id"], "memory ID")
    construction = _sha(snapshot["train_construction_sha256"], "construction")
    if snapshot["parent_snapshot_sha256"] is not None:
        _sha(snapshot["parent_snapshot_sha256"], "parent snapshot")
    roster, issued = snapshot["train_sample_ids"], snapshot["issued_record_ids"]
    for values, name, nonempty in ((roster, "TRAIN roster", True), (issued, "issued IDs", False)):
        _require(isinstance(values, list) and (values or not nonempty)
                 and all(isinstance(s, str) and s.strip() for s in values),
                 f"{name} is malformed")
        _require(values == sorted(set(values)), f"{name} must be sorted and unique")
    scopes = None
    if scoped:
        scopes = snapshot["construction_scopes"]
        _require(isinstance(scopes, Mapping) and scopes.get(construction) == roster,
                 "cumulative construction scope differs")
        for sha, ids in scopes.items():
            _sha(sha, "source construction scope")
            _require(isinstance(ids, list) and ids and all(isinstance(s, str) and s for s in ids)
                     and ids == sorted(set(ids)) and set(ids) <= set(roster),
                     "source construction scope is outside cumulative exposure")
    _require(isinstance(snapshot["records"], list), "snapshot records must be a list")
    try:
        records = tuple(ExperienceRecord.from_json(value) for value in snapshot["records"])
        _records(records, construction, frozenset(roster), scopes)
    except ExperienceMemoryError as error:
        raise ConsolidationError(str(error)) from error
    _require(all(record.record_id in issued
                 and (record.supersedes_record_id is None or record.supersedes_record_id in issued)
                 for record in records), "snapshot lost issued record identities")
    return records



def extend_candidate_construction(snapshot, *, round_construction_sha256, round_sample_ids,
                                  cumulative_construction_sha256, cumulative_sample_ids):
    """Extend verified exposure; do not rebase old records or authorize self-application.

    The caller verifies the roster files and frozen predecessor. This pure
    operation checks set semantics and preserves every previously issued ID.
    """
    _load_snapshot(snapshot)
    current_sha = _sha(round_construction_sha256, "round construction")
    cumulative_sha = _sha(cumulative_construction_sha256, "cumulative construction")
    _require(not isinstance(round_sample_ids, (str, bytes)), "round roster must be a sequence")
    current = tuple(round_sample_ids)
    _require(current and all(isinstance(s, str) and s.strip() for s in current),
             "round roster is empty or malformed")
    _require(len(current) == len(set(current)), "round roster is duplicated")
    old = set(snapshot["train_sample_ids"])
    _require(not old & set(current), "round construction and previous exposure overlap")
    _require(not isinstance(cumulative_sample_ids, (str, bytes)), "cumulative roster must be a sequence")
    cumulative = tuple(cumulative_sample_ids)
    _require(all(isinstance(s, str) and s.strip() for s in cumulative)
             and len(cumulative) == len(set(cumulative))
             and set(cumulative) == old | set(current),
             "cumulative exposure must be the exact prior/current union")
    scopes = copy.deepcopy(snapshot.get("construction_scopes", {
        snapshot["train_construction_sha256"]: snapshot["train_sample_ids"]}))
    for sha, ids in ((current_sha, sorted(current)), (cumulative_sha, sorted(cumulative))):
        _require(sha not in scopes or scopes[sha] == ids, "construction scope hash aliases a different roster")
        scopes[sha] = ids
    result = _signed({
        **{k: copy.deepcopy(v) for k, v in snapshot.items() if k != "content_sha256"},
        "schema": SCOPED_SNAPSHOT_SCHEMA,
        "parent_snapshot_sha256": snapshot["content_sha256"],
        "train_construction_sha256": cumulative_sha, "train_sample_ids": sorted(cumulative),
        "construction_scopes": scopes,
    })
    _load_snapshot(result)
    return result


def consolidate_experience_candidates(
    snapshot: Mapping[str, object], plan: Mapping[str, object],
    proposals: Mapping[str, ExperienceRecord], *, round_id: str,
    source_bindings: Mapping[str, str],
) -> dict[str, object]:
    """Validate and apply all operations, or return a rejected receipt with no successor.

    The model chooses ADD/UPDATE/DELETE and existing proposal/record IDs only.
    The adapter assigns new immutable record IDs. A revised record explicitly
    supersedes its predecessor; deletion retains the issued ID forever.
    Proposals are already materialized by the shared sealed-proposal path.
    Every proposed record is checked, including unused ones. No source/admission
    metadata is invented, and no selected candidate becomes admitted memory.

    Persist returned artifacts with core.preparation under caller-owned registered
    source bindings; this function deliberately does not write or activate them.
    """
    records = _load_snapshot(snapshot)
    _text(round_id, "round ID")
    _require(isinstance(source_bindings, Mapping) and set(source_bindings) == _SOURCE_KEYS,
             "complete-system feedback, proposal and consolidation source pins are required")
    for key, value in source_bindings.items():
        _sha(value, key)
    _require(isinstance(proposals, Mapping), "proposals must be a mapping")
    _require(all(isinstance(k, str) and k.strip() for k in proposals),
             "proposal IDs must be nonempty strings")
    # A malformed model plan is still retained. Non-JSON API inputs are caller
    # contract errors, not model output; canonical hashing rejects them.
    plan_hash = content_hash(plan)
    receipt = {
        "schema": RECEIPT_SCHEMA, "scope": "provisional-construction-only",
        "runtime_authorized": False, "round_id": round_id,
        "base_snapshot_sha256": snapshot["content_sha256"],
        "source_bindings": dict(source_bindings), "plan": copy.deepcopy(plan),
        "plan_sha256": plan_hash,
        "proposal_record_sha256s": {
            k: v.record_sha256 if isinstance(v, ExperienceRecord) else None
            for k, v in proposals.items()
        },
        "status": "rejected", "snapshot": None, "applied_operations": [],
        "failed_operation_index": None, "error": None,
    }
    index = None
    try:
        _require(isinstance(plan, Mapping)
                 and set(plan) == {"base_snapshot_sha256", "operations"},
                 "plan must contain only base_snapshot_sha256 and operations")
        _require(plan["base_snapshot_sha256"] == snapshot["content_sha256"],
                 "plan targets a different base snapshot")
        _require(isinstance(plan["operations"], list), "operations must be a list")
        construction = snapshot["train_construction_sha256"]
        roster = frozenset(snapshot["train_sample_ids"])
        for proposal in proposals.values():
            _candidate(proposal, construction, roster, snapshot.get("construction_scopes"))
            _require(proposal.revision == 1, "use unmodified materialized proposal roots")
        active = {record.record_id: record for record in records}
        base_ids = frozenset(active)
        issued = set(snapshot["issued_record_ids"])
        targeted, applied = set(), []
        for index, operation in enumerate(plan["operations"]):
            _require(isinstance(operation, Mapping), "operation must be an object")
            op = operation.get("operation")
            expected = {
                "ADD": {"operation", "proposal_id"},
                "UPDATE": {"operation", "record_id", "proposal_id"},
                "DELETE": {"operation", "record_id"},
            }
            _require(isinstance(op, str) and op in expected, "unknown explicit operation")
            _require(set(operation) == expected[op], f"{op} fields differ")
            target = operation.get("record_id")
            predecessor = None
            if op != "ADD":
                _text(target, "target record ID")
                _require(target not in targeted, "multiple operations target the same record")
                # New records from this plan are never legal targets in that plan.
                _require(target in base_ids, "unknown target record ID")
                targeted.add(target)
                predecessor = active.pop(target)
            new_id = None
            if op != "DELETE":
                proposal_id = _text(operation["proposal_id"], "proposal ID")
                _require(proposal_id in proposals, "unknown proposal ID")
                proposal = proposals[proposal_id]
                new_id = "experience-" + content_hash({
                    "memory_id": snapshot["memory_id"], "base": snapshot["content_sha256"],
                    "round_id": round_id, "plan_sha256": plan_hash, "index": index,
                    "proposal_sha256": proposal.record_sha256,
                    "source_bindings": dict(source_bindings),
                })
                _require(new_id not in issued, "new record identity was already issued")
                value = proposal.unsigned_json()
                value.update(
                    record_id=new_id,
                    revision=predecessor.revision + 1 if predecessor else 1,
                    supersedes_record_id=target if predecessor else None,
                )
                active[new_id] = ExperienceRecord.from_unsigned_json(value)
                issued.add(new_id)
            applied.append({
                "operation_index": index, "operation": op,
                "old_record_id": target, "new_record_id": new_id,
                "proposal_id": operation.get("proposal_id"),
            })
        _records(tuple(active.values()), construction, roster, snapshot.get("construction_scopes"))
        if not applied:
            successor, status = copy.deepcopy(snapshot), "unchanged"
        else:
            successor = _signed({
                **{k: copy.deepcopy(v) for k, v in snapshot.items() if k != "content_sha256"},
                "parent_snapshot_sha256": snapshot["content_sha256"],
                "records": [record.as_json() for record in active.values()],
                "issued_record_ids": sorted(issued),
            })
            status = "applied"
        receipt.update(status=status, snapshot=successor, applied_operations=applied)
    except (ConsolidationError, ExperienceMemoryError) as error:
        receipt.update(error=str(error), failed_operation_index=index)
    return _signed(receipt)
