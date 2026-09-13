"""Config-driven source-bound SLURP Top-N diagnostics.

This companion to score_compare_cli verifies sealed bundles and complete score
receipts before delegating all diagnostic counting to the pure aggregator. It
never scores, resamples, or infers a reference from a prediction.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..contracts import TraceRecord
from ..core.attempts import STATE_ABORTED
from ..core.bundle.delivery_replay import canonical
from ..core.bundle.verify import verify_bundle
from ..core.roster import read_roster
from ..core.scoring_receipt import SavedScoreReceiptRef, verify_complete_score_receipt
from ..data.lock import load_lock
from ..data.slurp import load_slurp_split
from ..data.splits import prefixed, split_identity_hash
from ..rails.phase_material import sealed_states_from_manifest
from ..rails.slurp_intent_hypotheses import parse_slurp_intent_hypothesis_state
from ..reproduction.slurp_scoring import parse_slu_response
from .null_calibration_cli import digest, pinned_json
from .slurp_topn_diagnostics import (
    BranchOutcomeRow,
    ReferenceIntentRow,
    SourceCandidateRow,
    TopNDiagnosticError,
    aggregate_topn_diagnostics,
)


class SlurpTopNAnalysisError(ValueError):
    """An analysis config or source binding failed closed."""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _map(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SlurpTopNAnalysisError(f"{label} must be a mapping")
    return value


def _pin(value: object, label: str) -> tuple[Path, str]:
    binding = _map(value, label)
    raw_path, expected = binding.get("path"), binding.get("sha256")
    if not isinstance(raw_path, str) or not raw_path:
        raise SlurpTopNAnalysisError(f"{label}.path must be nonempty text")
    if not isinstance(expected, str) or len(expected) != 64:
        raise SlurpTopNAnalysisError(f"{label}.sha256 must be a 64-character hash")
    path = Path(raw_path)
    if not path.is_file():
        raise SlurpTopNAnalysisError(f"{label} does not exist: {path}")
    actual = _sha256_file(path)
    if actual != expected:
        raise SlurpTopNAnalysisError(
            f"{label} hash mismatch: configured {expected}, measured {actual}"
        )
    return path, expected


def _roster_ids(value: object, label: str) -> tuple[str, ...]:
    path, _ = _pin(value, label)
    try:
        document = read_roster(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise SlurpTopNAnalysisError(f"{label} is not a verified roster: {error}") from error
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise SlurpTopNAnalysisError(f"{label} has no roster items")
    ids = []
    for item in items:
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
            raise SlurpTopNAnalysisError(f"{label} contains an invalid item id")
        ids.append(item["id"])
    if len(ids) != len(set(ids)):
        raise SlurpTopNAnalysisError(f"{label} contains duplicate item ids")
    return tuple(ids)


def _metadata(value: object, expected: set[str]) -> dict[str, Mapping[str, object]]:
    document = pinned_json(_map(value, "analysis.metadata"))
    rows = document.get("rows") if isinstance(document, Mapping) else None
    if not isinstance(rows, list) or not rows:
        raise SlurpTopNAnalysisError("analysis.metadata must contain rows")
    indexed = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("sample_id"), str):
            raise SlurpTopNAnalysisError("analysis.metadata rows need sample_id")
        sample_id = row["sample_id"]
        if sample_id in indexed:
            raise SlurpTopNAnalysisError(f"analysis.metadata duplicates {sample_id!r}")
        indexed[sample_id] = row
    if set(indexed) != expected:
        raise SlurpTopNAnalysisError("analysis.metadata roster does not match full roster")
    return indexed


def _source_rows(binding, bundle, full_ids, *, state_loader):
    manifest_path, manifest_sha = _pin(binding.get("manifest"), "source manifest")
    manifest = _map(getattr(bundle, "manifest", None), "verified source manifest")
    if manifest.get("status") != "COMPLETED" or getattr(bundle, "attempt_state", None) != "FINALIZED":
        raise SlurpTopNAnalysisError("common source must be FINALIZED and COMPLETED")
    if set(getattr(bundle, "split_ids", ())) != set(full_ids):
        raise SlurpTopNAnalysisError("common source roster does not match full roster")
    artifact = _map(manifest.get("artifact_result"), "source artifact_result")
    if (artifact.get("schema") != "saea-artifact-result-binding-v2"
            or artifact.get("role") != "slurp-intent-hypotheses"):
        raise SlurpTopNAnalysisError("common source is not a typed SLURP hypothesis artifact")
    contract = _map(artifact.get("content_contract"), "source content contract")
    catalog = _map(contract.get("source_catalog"), "source candidate catalog")
    if catalog.get("source_sha256") != binding.get("candidate_contract_source_sha256"):
        raise SlurpTopNAnalysisError("source candidate catalog hash differs from configured source hash")
    if binding.get("split_identity_hash") != split_identity_hash(prefixed("slurp", full_ids)):
        raise SlurpTopNAnalysisError("source split identity does not match the full roster")
    producer = binding.get("producer_policy_id", "phase-intent-hypotheses-only-v1")
    phase_name = binding.get("phase_name", "slots")
    if not isinstance(producer, str) or not producer or not isinstance(phase_name, str) or not phase_name:
        raise SlurpTopNAnalysisError("source producer_policy_id and phase_name are required")
    try:
        states = state_loader(
            manifest_path, expected_sha256=manifest_sha, phase_name=phase_name,
            producer_policy_id=producer, sample_ids=full_ids,
            bundle_verifier=lambda _path: bundle,
        )
    except Exception as error:
        raise SlurpTopNAnalysisError(f"common source state loading failed: {error}") from error
    if set(states) != set(full_ids):
        raise SlurpTopNAnalysisError("common source state roster mismatch")
    from ..rails.artifact_results import build_slurp_hypothesis_artifact_validator
    source_meta = _map(manifest.get("artifact_content_source"), "source content source")
    source_path = Path(str(source_meta.get("path")))
    relpath = catalog.get("data_relpath")
    if not isinstance(relpath, str) or not relpath:
        raise SlurpTopNAnalysisError("source candidate catalog lacks data_relpath")
    data_root = source_path
    for _ in relpath.split("/"):
        data_root = data_root.parent
    try:
        validator = build_slurp_hypothesis_artifact_validator(contract, data_root=data_root)
    except Exception as error:
        raise SlurpTopNAnalysisError(f"source candidate catalog validation failed: {error}") from error
    width = binding.get("candidate_count", 3)
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise SlurpTopNAnalysisError("candidate_count must be a positive integer")
    rows = []
    for sample_id in full_ids:
        try:
            state = states[sample_id]
            parsed = parse_slurp_intent_hypothesis_state(
                state, expected_sample_id=sample_id,
                legal_intent_ids=validator.legal_intent_ids, max_candidates=width
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SlurpTopNAnalysisError(
                f"source hypothesis for {sample_id!r} is invalid: {error}"
            ) from error
        rows.append(SourceCandidateRow(sample_id, tuple(x.intent_id for x in parsed.candidates)))
    return tuple(rows), manifest, states


def _references(binding, expected_ids, *, loader):
    if binding.get("kind") != "slurp-split":
        raise SlurpTopNAnalysisError("reference source kind must be slurp-split")
    split_id, split_hash = binding.get("split_id"), binding.get("split_identity_hash")
    lock_path, _ = _pin(binding.get("lock"), "reference lock")
    data_root = binding.get("data_root")
    if not isinstance(split_id, str) or not split_id:
        raise SlurpTopNAnalysisError("reference split_id must be nonempty text")
    if not isinstance(split_hash, str) or len(split_hash) != 64:
        raise SlurpTopNAnalysisError("reference split_identity_hash must be pinned")
    if not isinstance(data_root, str) or not data_root:
        raise SlurpTopNAnalysisError("reference data_root must be explicit")
    try:
        records = loader(
            load_lock(lock_path), Path(data_root), split_id,
            allow_heldout=bool(binding.get("allow_heldout", False)),
            allow_synthetic=bool(binding.get("allow_synthetic", False)),
        )
    except Exception as error:
        raise SlurpTopNAnalysisError(f"reference adapter failed: {error}") from error
    ids = tuple(record.sample_id for record in records)
    by_id = {record.sample_id: record for record in records}
    if len(by_id) != len(ids) or len(ids) != len(set(ids)):
        raise SlurpTopNAnalysisError("reference adapter returned duplicate sample ids")
    loaded_split_hash = binding.get("loaded_split_identity_hash")
    if loaded_split_hash is not None and (
        not isinstance(loaded_split_hash, str)
        or split_identity_hash(prefixed("slurp", ids)) != loaded_split_hash
    ):
        raise SlurpTopNAnalysisError("reference adapter loaded-split identity differs from configured hash")
    if not set(expected_ids) <= set(by_id):
        raise SlurpTopNAnalysisError("reference adapter roster does not contain the full analysis roster")
    selected_hash = split_identity_hash(prefixed("slurp", expected_ids))
    if selected_hash != split_hash:
        raise SlurpTopNAnalysisError("reference analysis-roster identity differs from configured hash")
    return tuple(ReferenceIntentRow(sample_id, by_id[sample_id].intent) for sample_id in expected_ids)


def _branch_rows(name, bundle, source_path, source_sha, source_states, full_ids):
    manifest = _map(getattr(bundle, "manifest", None), f"{name} manifest")
    if manifest.get("schema") != "saea-derived-delivery-v1" or getattr(bundle, "attempt_state", None) != "DERIVED":
        raise SlurpTopNAnalysisError(f"{name} must be a verified derived-delivery bundle")
    phases = manifest.get("phase_sources")
    if not isinstance(phases, list):
        raise SlurpTopNAnalysisError(f"{name} lacks phase_sources")
    phase_by_id = {}
    for phase in phases:
        if not isinstance(phase, Mapping) or not isinstance(phase.get("sample_id"), str):
            raise SlurpTopNAnalysisError(f"{name} phase source row is malformed")
        sample_id = phase["sample_id"]
        if sample_id in phase_by_id:
            raise SlurpTopNAnalysisError(f"{name} duplicates phase source {sample_id!r}")
        predecessor = _map(phase.get("predecessor_manifest"), f"{name} predecessor manifest")
        if (Path(str(predecessor.get("path"))).resolve() != source_path.resolve()
                or predecessor.get("sha256") != source_sha):
            raise SlurpTopNAnalysisError(f"{name} does not bind the common source manifest")
        state = source_states.get(sample_id)
        if state is None or phase.get("sealed_state_sha256") != state.content_hash():
            raise SlurpTopNAnalysisError(f"{name} source state binding mismatch for {sample_id!r}")
        phase_by_id[sample_id] = phase
    if set(phase_by_id) != set(full_ids):
        raise SlurpTopNAnalysisError(f"{name} phase source roster mismatch")
    output_by_id = {}
    for row in getattr(bundle, "outputs_rows", ()):
        if not isinstance(row, Mapping) or not isinstance(row.get("sample_id"), str):
            raise SlurpTopNAnalysisError(f"{name} output row is malformed")
        sample_id = row["sample_id"]
        if sample_id in output_by_id:
            raise SlurpTopNAnalysisError(f"{name} duplicates output {sample_id!r}")
        output_by_id[sample_id] = row
    if set(output_by_id) != set(full_ids):
        raise SlurpTopNAnalysisError(f"{name} output roster mismatch")
    outcomes = []
    for sample_id in full_ids:
        row, phase = output_by_id[sample_id], phase_by_id[sample_id]
        text = row.get("text")
        if not isinstance(text, str):
            raise SlurpTopNAnalysisError(f"{name} output {sample_id!r} lacks text")
        delivery_sha = row.get("delivery_text_sha256")
        if (delivery_sha != phase.get("delivered_text_sha256")
                or hashlib.sha256(text.encode()).hexdigest() != delivery_sha):
            raise SlurpTopNAnalysisError(f"{name} output text binding mismatch for {sample_id!r}")
        scenario, action, _entities, _parsed = parse_slu_response(text)
        final_intent = (
            f"{scenario}_{action}" if isinstance(scenario, str) and scenario
            and isinstance(action, str) and action else None
        )
        refusal = phase.get("refusal_reason")
        if refusal is not None and (not isinstance(refusal, str) or not refusal):
            raise SlurpTopNAnalysisError(f"{name} refusal reason malformed for {sample_id!r}")
        outcomes.append(BranchOutcomeRow(sample_id, final_intent, refusal is not None, None))
    return tuple(outcomes)


@dataclass(frozen=True)
class RawProposalRow:
    """One untouched raw shortlist; repeated IDs remain repeated in candidate_ids."""

    sample_id: str
    request_id: str
    candidate_ids: tuple[str, ...]


def _raw_legal_ids(binding: object) -> frozenset[str]:
    document = pinned_json(_map(binding, "raw legal intent inventory"))
    if isinstance(document, list):
        values = document
    else:
        values = document.get("intent_ids", document.get("ids"))
        if values is None:
            items = document.get("items")
            if isinstance(items, list):
                values = [
                    item.get("intent_id", item.get("id"))
                    for item in items
                    if isinstance(item, Mapping)
                ]
    if not isinstance(values, list) or not values:
        raise SlurpTopNAnalysisError(
            "raw legal intent inventory must contain a non-empty intent_ids list"
        )
    if any(not isinstance(value, str) or not value for value in values):
        raise SlurpTopNAnalysisError("raw legal intent inventory has an invalid intent ID")
    if len(values) != len(set(values)):
        raise SlurpTopNAnalysisError("raw legal intent inventory contains duplicate IDs")
    return frozenset(values)


def _raw_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise SlurpTopNAnalysisError(f"raw response has duplicate JSON key {key!r}")
        document[key] = value
    return document


def _raw_candidate_ids(
    text: object,
    *,
    sample_id: str,
    legal_intent_ids: frozenset[str],
    max_candidates: int,
) -> tuple[str, ...]:
    if not isinstance(text, str) or not text:
        raise SlurpTopNAnalysisError(f"raw response for {sample_id!r} has no text")
    try:
        document = json.loads(text, object_pairs_hook=_raw_json_object)
    except (TypeError, json.JSONDecodeError) as error:
        raise SlurpTopNAnalysisError(
            f"raw response for {sample_id!r} is not JSON: {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise SlurpTopNAnalysisError(f"raw response for {sample_id!r} must be an object")
    if set(document) == {"schema", "semantics", "sample_id", "candidates"}:
        if (
            document["schema"] != "saea-slurp-intent-hypotheses-v1"
            or document["semantics"] != "ranked-mutually-exclusive-intent-alternatives"
            or document["sample_id"] != sample_id
        ):
            raise SlurpTopNAnalysisError(
                f"raw response for {sample_id!r} has an invalid typed envelope"
            )
    elif set(document) != {"candidates"}:
        raise SlurpTopNAnalysisError(
            f"raw response for {sample_id!r} must contain only candidates"
        )
    candidates = document.get("candidates")
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= max_candidates:
        raise SlurpTopNAnalysisError(
            f"raw response for {sample_id!r} has an invalid candidate count"
        )
    candidate_ids: list[str] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping) or set(candidate) != {
            "intent_id", "distinction", "evidence_refs", "unresolved_fields"
        }:
            raise SlurpTopNAnalysisError(
                f"raw response candidate {index} for {sample_id!r} is malformed"
            )
        intent_id = candidate["intent_id"]
        if not isinstance(intent_id, str) or not intent_id:
            raise SlurpTopNAnalysisError(
                f"raw response candidate {index} for {sample_id!r} has no intent ID"
            )
        if intent_id not in legal_intent_ids:
            raise SlurpTopNAnalysisError(
                f"raw response candidate {index} for {sample_id!r} has illegal intent ID"
            )
        if not isinstance(candidate["distinction"], str):
            raise SlurpTopNAnalysisError(
                f"raw response candidate {index} for {sample_id!r} has invalid distinction"
            )
        for field in ("evidence_refs", "unresolved_fields"):
            values = candidate[field]
            if (
                not isinstance(values, list)
                or any(not isinstance(value, str) or not value for value in values)
                or len(values) > 32
                or len(values) != len(set(values))
            ):
                raise SlurpTopNAnalysisError(
                    f"raw response candidate {index} for {sample_id!r} has invalid {field}"
                )
        candidate_ids.append(intent_id)
    # Deliberately do not reject repeated intent IDs: this diagnostic measures the
    # raw source, including repeated positions, and never repairs or deduplicates it.
    return tuple(candidate_ids)


def _raw_trace_channels(
    trace_path: Path,
    trace_manifest_path: Path,
    bundle: object,
    *,
    trace_sha256: str | None = None,
    trace_manifest_sha256: str | None = None,
) -> dict[str, dict[str, Mapping[str, object]]]:
    if trace_sha256 is not None and _sha256_file(trace_path) != trace_sha256:
        raise SlurpTopNAnalysisError("raw trace changed after its pinned verification")
    if (
        trace_manifest_sha256 is not None
        and _sha256_file(trace_manifest_path) != trace_manifest_sha256
    ):
        raise SlurpTopNAnalysisError(
            "raw trace manifest changed after its pinned verification"
        )
    try:
        lines = trace_path.read_text(encoding="utf-8").splitlines()
        trace_manifest = json.loads(trace_manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SlurpTopNAnalysisError(f"raw trace cannot be read: {error}") from error
    records: dict[str, tuple[str, Mapping[str, object], str]] = {}
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise SlurpTopNAnalysisError(
                f"raw trace line {number} is malformed: {error}"
            ) from error
        if not isinstance(document, Mapping) or not {
            "channel", "record_id", "payload"
        } <= set(document):
            raise SlurpTopNAnalysisError(
                f"raw trace line {number} lacks channel/record_id/payload"
            )
        record_id = document["record_id"]
        if not isinstance(record_id, str) or not record_id:
            raise SlurpTopNAnalysisError(f"raw trace line {number} has invalid record_id")
        if record_id in records:
            raise SlurpTopNAnalysisError(f"raw trace duplicates record_id {record_id!r}")
        try:
            record = TraceRecord(
                channel=document["channel"],
                record_id=record_id,
                payload=document["payload"],
            ).validate()
            content_hash = record.content_hash()
        except Exception as error:
            raise SlurpTopNAnalysisError(
                f"raw trace record {record_id!r} is invalid: {error}"
            ) from error
        records[record_id] = (record.channel, dict(record.payload), content_hash)
    manifest_records = trace_manifest.get("records") if isinstance(trace_manifest, Mapping) else None
    if not isinstance(manifest_records, Mapping) or set(manifest_records) != set(records):
        raise SlurpTopNAnalysisError("raw trace manifest does not match raw record IDs")
    for record_id, (_channel, _payload, content_hash) in records.items():
        if manifest_records.get(record_id) != content_hash:
            raise SlurpTopNAnalysisError(
                f"raw trace manifest hash mismatch for {record_id!r}"
            )
    verified_records = getattr(bundle, "trace_records", None)
    if not isinstance(verified_records, Mapping) or set(verified_records) != set(records):
        raise SlurpTopNAnalysisError(
            "verified bundle trace does not match the pinned raw trace record set"
        )
    if any(verified_records[key] != payload for key, (_channel, payload, _hash) in records.items()):
        raise SlurpTopNAnalysisError("verified bundle trace payload differs from raw trace")
    channels: dict[str, dict[str, Mapping[str, object]]] = {}
    for record_id, (channel, payload, _content_hash) in records.items():
        channels.setdefault(channel, {})[record_id] = payload
    return channels


def _raw_request_id(record_id: object, suffix: str) -> str:
    if not isinstance(record_id, str) or not record_id.endswith(suffix):
        raise SlurpTopNAnalysisError(
            f"raw trace record ID must end with {suffix!r}: {record_id!r}"
        )
    request_id = record_id[: -len(suffix)]
    if not request_id:
        raise SlurpTopNAnalysisError("raw trace request ID is empty")
    return request_id


def _transport_response_sha256(
    raw_wire: bytes,
    *,
    expected_text: str,
    expected_usage: object,
    expected_finish_reason: object,
) -> str:
    """Rebuild the adapter envelope hash from the immutable wire bytes."""
    try:
        parsed = json.loads(raw_wire.decode("utf-8"), object_pairs_hook=_raw_json_object)
        choice = parsed["choices"][0]
        message = choice["message"]
        response_tool_calls = message.get("tool_calls") if isinstance(message, Mapping) else None
        argument_errors: list[int] = []
        if isinstance(response_tool_calls, list) and response_tool_calls:
            canonical_calls = []
            for index, call in enumerate(response_tool_calls):
                function = call["function"]
                name = function["name"]
                raw_arguments = function.get("arguments")
                try:
                    arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else None
                    if not isinstance(arguments, dict):
                        raise ValueError("tool call arguments must decode to an object")
                except (TypeError, ValueError):
                    arguments = {}
                    argument_errors.append(index)
                canonical_calls.append({"name": name, "arguments": arguments})
            text = json.dumps(canonical_calls)
        else:
            text = message["content"]
        usage = {
            str(key): int(value)
            for key, value in dict(parsed.get("usage", {})).items()
            if not isinstance(value, Mapping)
        }
        envelope: dict[str, object] = {"text": text, "usage": usage}
        envelope["wire_response_b64"] = base64.b64encode(raw_wire).decode("ascii")
        envelope["wire_response_sha256"] = hashlib.sha256(raw_wire).hexdigest()
        envelope["wire_finish_reason"] = choice.get("finish_reason")
        if isinstance(response_tool_calls, list) and response_tool_calls:
            envelope["tool_calls"] = response_tool_calls
            if argument_errors:
                envelope["tool_call_argument_parse_errors"] = argument_errors
        if isinstance(choice, Mapping) and "logprobs" in choice:
            envelope["logprobs"] = choice["logprobs"]
    except (KeyError, TypeError, ValueError, IndexError, UnicodeError) as error:
        raise SlurpTopNAnalysisError(
            f"wire response cannot reconstruct the transport envelope: {error}"
        ) from error
    if text != expected_text or usage != expected_usage or envelope["wire_finish_reason"] != expected_finish_reason:
        raise SlurpTopNAnalysisError("wire response disagrees with normalized response fields")
    return hashlib.sha256(json.dumps(envelope).encode("utf-8")).hexdigest()


def _raw_source_rows(
    trace_path: Path,
    trace_manifest_path: Path,
    bundle: object,
    *,
    expected_ids: tuple[str, ...],
    legal_intent_ids: frozenset[str],
    max_candidates: int,
    expected_contacts: int,
    trace_sha256: str | None = None,
    trace_manifest_sha256: str | None = None,
) -> tuple[RawProposalRow, ...]:
    channels = _raw_trace_channels(
        trace_path,
        trace_manifest_path,
        bundle,
        trace_sha256=trace_sha256,
        trace_manifest_sha256=trace_manifest_sha256,
    )
    required = ("MODEL_REQUEST", "MODEL_RESPONSE", "MODEL_WIRE_RESPONSE", "COST")
    missing_channels = [channel for channel in required if channel not in channels]
    if missing_channels:
        raise SlurpTopNAnalysisError(f"raw trace lacks required channels: {missing_channels}")
    indexed = {}
    for channel in required:
        indexed[channel] = {}
        for record_id, payload in channels[channel].items():
            suffix = {
                "MODEL_REQUEST": "/request",
                "MODEL_RESPONSE": "/response",
                "MODEL_WIRE_RESPONSE": "/wire-response",
                "COST": "/cost",
            }[channel]
            request_id = _raw_request_id(record_id, suffix)
            if request_id in indexed[channel]:
                raise SlurpTopNAnalysisError(
                    f"raw trace has duplicate {channel} request ID {request_id!r}"
                )
            indexed[channel][request_id] = payload
    if any(len(indexed[channel]) != expected_contacts for channel in required):
        raise SlurpTopNAnalysisError(
            "raw trace required channels do not each contain expected_contacts records"
        )
    request_ids = set(indexed["MODEL_REQUEST"])
    if any(set(indexed[channel]) != request_ids for channel in required[1:]):
        raise SlurpTopNAnalysisError(
            "raw trace required channels do not have identical request IDs"
        )
    if len(request_ids) != len(expected_ids):
        raise SlurpTopNAnalysisError("raw request count does not match the pinned roster")
    by_sample: dict[str, RawProposalRow] = {}
    for request_id, request in indexed["MODEL_REQUEST"].items():
        inner = request.get("payload")
        if (
            not isinstance(inner, Mapping)
            or inner.get("request_id") != request_id
            or not isinstance(inner.get("sample_id"), str)
            or not inner["sample_id"]
            or request.get("payload_sha256") != hashlib.sha256(canonical(inner)).hexdigest()
        ):
            raise SlurpTopNAnalysisError(f"raw request {request_id!r} identity/hash is invalid")
        sample_id = inner["sample_id"]
        if sample_id in by_sample:
            raise SlurpTopNAnalysisError(f"raw trace has duplicate sample ID {sample_id!r}")
        response = indexed["MODEL_RESPONSE"][request_id]
        text = response.get("text")
        if (
            not isinstance(text, str)
            or response.get("response_text_sha256")
            != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise SlurpTopNAnalysisError(f"raw response {request_id!r} text hash is invalid")
        wire = indexed["MODEL_WIRE_RESPONSE"][request_id]
        wire_request = wire.get("request_id")
        if wire_request != request_id or wire.get("sample_id") != sample_id:
            raise SlurpTopNAnalysisError(f"raw wire response {request_id!r} identity is invalid")
        if wire.get("finish_reason") != "stop":
            raise SlurpTopNAnalysisError(f"raw wire response {request_id!r} did not stop normally")
        try:
            raw_wire = base64.b64decode(wire["response_b64"], validate=True)
        except (KeyError, TypeError, ValueError) as error:
            raise SlurpTopNAnalysisError(
                f"raw wire response {request_id!r} bytes are invalid"
            ) from error
        wire_sha = hashlib.sha256(raw_wire).hexdigest()
        if wire.get("response_sha256") != wire_sha:
            raise SlurpTopNAnalysisError(f"raw response {request_id!r} wire hash is invalid")
        normalized_sha = _transport_response_sha256(
            raw_wire,
            expected_text=text,
            expected_usage=response.get("usage", {}),
            expected_finish_reason=wire.get("finish_reason"),
        )
        if response.get("response_sha256") != normalized_sha:
            raise SlurpTopNAnalysisError(
                f"raw response {request_id!r} normalized envelope hash is invalid"
            )
        cost = indexed["COST"][request_id]
        if cost.get("request_id", request_id) != request_id or cost.get("calls") != 1:
            raise SlurpTopNAnalysisError(f"raw cost {request_id!r} identity/calls are invalid")
        try:
            candidate_ids = _raw_candidate_ids(
                text, sample_id=sample_id, legal_intent_ids=legal_intent_ids,
                max_candidates=max_candidates,
            )
        except SlurpTopNAnalysisError:
            raise
        by_sample[sample_id] = RawProposalRow(sample_id, request_id, candidate_ids)
    if set(by_sample) != set(expected_ids):
        raise SlurpTopNAnalysisError("raw response sample IDs do not match the pinned roster")
    return tuple(by_sample[sample_id] for sample_id in expected_ids)


def _raw_aggregate(
    rows, references, metadata, ids: set[str], *, stratum_field: str, _include_per_stratum: bool = True
):
    selected = [row for row in rows if row.sample_id in ids]
    refs = {row.sample_id: row.intent_id for row in references if row.sample_id in ids}
    if len(selected) != len(ids) or set(refs) != ids:
        raise SlurpTopNAnalysisError("raw diagnostic population binding is incomplete")
    if len({row.sample_id for row in selected}) != len(selected):
        raise SlurpTopNAnalysisError("raw diagnostic rows contain duplicate samples")
    summary = {
        "count": len(selected),
        "rank1_correct_count": 0,
        "distinct_proposal_coverage_count": 0,
        "by_observed_distinct_width": {},
        "per_stratum": {},
    }
    strata: dict[str, set[str]] = {}
    for row in selected:
        if not row.candidate_ids:
            raise SlurpTopNAnalysisError(f"raw row {row.sample_id!r} has no proposals")
        gold = refs[row.sample_id]
        rank1_correct = row.candidate_ids[0] == gold
        covered = gold in set(row.candidate_ids)
        width = len(set(row.candidate_ids))
        summary["rank1_correct_count"] += rank1_correct
        summary["distinct_proposal_coverage_count"] += covered
        width_report = summary["by_observed_distinct_width"].setdefault(
            str(width), {"count": 0, "rank1_correct_count": 0,
                         "distinct_proposal_coverage_count": 0}
        )
        width_report["count"] += 1
        width_report["rank1_correct_count"] += rank1_correct
        width_report["distinct_proposal_coverage_count"] += covered
        value = metadata[row.sample_id].get(stratum_field)
        if not isinstance(value, str) or not value:
            raise SlurpTopNAnalysisError(
                f"metadata {stratum_field} missing for {row.sample_id!r}"
            )
        strata.setdefault(value, set()).add(row.sample_id)
    summary["rank1_accuracy"] = summary["rank1_correct_count"] / len(selected)
    summary["distinct_proposal_coverage"] = (
        summary["distinct_proposal_coverage_count"] / len(selected)
    )
    for width_report in summary["by_observed_distinct_width"].values():
        count = width_report["count"]
        width_report["rank1_accuracy"] = width_report["rank1_correct_count"] / count
        width_report["distinct_proposal_coverage"] = (
            width_report["distinct_proposal_coverage_count"] / count
        )
    if _include_per_stratum:
        for stratum, members in sorted(strata.items()):
            nested = _raw_aggregate(
                rows, references, metadata, members,
                stratum_field=stratum_field, _include_per_stratum=False,
            )
            summary["per_stratum"][stratum] = nested
    return summary


def run_raw_source(
    config_path,
    output,
    *,
    bundle_verifier=verify_bundle,
    reference_loader=load_slurp_split,
):
    """Read and describe one pinned ABORTED raw source; never repairs or scores it."""
    config_path, output = Path(config_path), Path(output)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SlurpTopNAnalysisError(f"cannot read analysis config: {error}") from error
    if not isinstance(config, Mapping) or config.get("execution_profile") != "model-free-check":
        raise SlurpTopNAnalysisError("raw source analysis requires model-free-check")
    spec = _map(config.get("analysis"), "analysis")
    raw = _map(spec.get("raw_source_diagnostics"), "analysis.raw_source_diagnostics")
    release = _map(raw.get("source_quality_read_release"), "source quality read release")
    if release.get("authorized") is not True or not isinstance(release.get("release_id"), str):
        raise SlurpTopNAnalysisError(
            "raw source analysis requires an explicit authorized source-quality read release"
        )
    expected_contacts = raw.get("expected_contacts")
    if isinstance(expected_contacts, bool) or not isinstance(expected_contacts, int) or expected_contacts < 1:
        raise SlurpTopNAnalysisError("expected_contacts must be a positive integer")
    full_ids = _roster_ids(spec.get("full_roster"), "analysis.full_roster")
    primary_ids = _roster_ids(spec.get("roster"), "analysis.roster")
    if len(full_ids) != expected_contacts or not set(primary_ids) <= set(full_ids):
        raise SlurpTopNAnalysisError("raw source roster does not match expected contacts")
    metadata = _metadata(spec.get("metadata"), set(full_ids))
    trace_path, trace_sha = _pin(raw.get("raw_trace"), "raw trace")
    trace_manifest_path, trace_manifest_sha = _pin(
        raw.get("trace_manifest"), "raw trace manifest"
    )
    manifest_path, manifest_sha = _pin(raw.get("manifest"), "aborted source manifest")
    try:
        bundle = bundle_verifier(manifest_path)
    except Exception as error:
        raise SlurpTopNAnalysisError(f"aborted source bundle verification failed: {error}") from error
    manifest = _map(getattr(bundle, "manifest", None), "verified aborted source manifest")
    if (
        manifest.get("status") != "ABORTED"
        or getattr(bundle, "attempt_state", None) != STATE_ABORTED
    ):
        raise SlurpTopNAnalysisError("raw source must be an ABORTED bundle and attempt")
    if Path(str(getattr(bundle, "manifest_path", manifest_path))).resolve() != manifest_path.resolve():
        raise SlurpTopNAnalysisError("verified bundle manifest path differs from pinned manifest")
    for key, path, sha in (
        ("raw_trace", trace_path, trace_sha), ("trace_manifest", trace_manifest_path, trace_manifest_sha)
    ):
        bound = _map(manifest.get(key), f"aborted source manifest {key}")
        if (
            Path(str(bound.get("path"))).resolve() != path.resolve()
            or bound.get("sha256") != sha
        ):
            raise SlurpTopNAnalysisError(f"aborted source manifest {key} differs from pinned file")
    split = _map(manifest.get("split"), "aborted source split")
    expected_split_hash = raw.get("split_identity_hash")
    if expected_split_hash != split_identity_hash(prefixed("slurp", full_ids)):
        raise SlurpTopNAnalysisError("raw source split identity does not match full roster")
    if split.get("identity_hash") != expected_split_hash or set(getattr(bundle, "split_ids", ())) != set(full_ids):
        raise SlurpTopNAnalysisError("aborted source split binding does not match full roster")
    width = raw.get("max_candidates", 3)
    if isinstance(width, bool) or not isinstance(width, int) or not 1 <= width <= 3:
        raise SlurpTopNAnalysisError("raw max_candidates must be an integer from 1 through 3")
    legal_ids = _raw_legal_ids(raw.get("legal_intent_ids"))
    rows = _raw_source_rows(
        trace_path, trace_manifest_path, bundle, expected_ids=full_ids,
        legal_intent_ids=legal_ids,
        max_candidates=width,
        expected_contacts=expected_contacts,
        trace_sha256=trace_sha,
        trace_manifest_sha256=trace_manifest_sha,
    )
    reference_binding = _map(
        _map(spec.get("source_diagnostics"), "analysis.source_diagnostics").get("reference_source"),
        "raw reference source",
    )
    references = _references(reference_binding, full_ids, loader=reference_loader)
    field = raw.get("stratum_field", spec.get("stratum_field", "scenario"))
    if not isinstance(field, str) or not field:
        raise SlurpTopNAnalysisError("raw stratum_field must be nonempty text")
    populations = {
        "NEW500": set(primary_ids),
        "DEV1000": set(full_ids),
        "OLD500": set(full_ids) - set(primary_ids),
    }
    reports = {
        population: _raw_aggregate(rows, references, metadata, ids, stratum_field=field)
        for population, ids in populations.items()
        if ids
    }
    result = {
        "schema": "saea-slurp-raw-source-diagnostics-v1",
        "experiment_id": config.get("experiment_id"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"path": str(config_path.resolve()), "sha256": digest(config_path)},
        "source": {
            "manifest": {"path": str(manifest_path), "sha256": manifest_sha},
            "raw_trace": {"path": str(trace_path), "sha256": trace_sha},
            "trace_manifest": {"path": str(trace_manifest_path), "sha256": trace_manifest_sha},
            "attempt_state": STATE_ABORTED,
            "expected_contacts": expected_contacts,
        },
        "source_quality_read_release": {
            "release_id": release["release_id"], "authorized": True
        },
        "populations": {name: len(ids) for name, ids in populations.items()},
        "max_candidates": width,
        "stratum_field": field,
        "diagnostics": reports,
        "uncertainty": {
            "status": "descriptive_only",
            "reason": "one aborted source has no paired comparison; observed distinct width is not calibrated confidence",
        },
        "model_calls": 0,
        "encoder_calls": 0,
        "tokenizer_calls": 0,
        "scorer_invocations": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return result

def _subset(rows: Sequence, ids: set[str]) -> tuple:
    return tuple(row for row in rows if row.sample_id in ids)


def run(
    config_path, output, *, bundle_verifier=verify_bundle,
    score_receipt_verifier=verify_complete_score_receipt,
    reference_loader=load_slurp_split, state_loader=sealed_states_from_manifest,
):
    """Verify all source bindings, then write descriptive diagnostics."""
    config_path, output = Path(config_path), Path(output)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SlurpTopNAnalysisError(f"cannot read analysis config: {error}") from error
    if not isinstance(config, Mapping) or config.get("execution_profile") != "model-free-check":
        raise SlurpTopNAnalysisError("analysis requires model-free-check")
    spec = _map(config.get("analysis"), "analysis")
    if "raw_source_diagnostics" in spec:
        return run_raw_source(
            config_path,
            output,
            bundle_verifier=bundle_verifier,
            reference_loader=reference_loader,
        )
    source_section = _map(spec.get("source_diagnostics"), "analysis.source_diagnostics")
    source = _map(source_section.get("shared_fixed_top3_source"), "shared fixed Top-3 source")
    full_ids = _roster_ids(spec.get("full_roster"), "analysis.full_roster")
    primary_ids = _roster_ids(spec.get("roster"), "analysis.roster")
    if not set(primary_ids) <= set(full_ids):
        raise SlurpTopNAnalysisError("primary roster must be a subset of full roster")
    metadata = _metadata(spec.get("metadata"), set(full_ids))
    source_path, source_sha = _pin(source.get("manifest"), "source manifest")
    source_bundle = bundle_verifier(source_path)
    inputs = _map(spec.get("inputs"), "analysis.inputs")
    if not inputs:
        raise SlurpTopNAnalysisError("analysis.inputs must be nonempty")
    bundles = {}
    for name, value in inputs.items():
        binding = _map(value, f"analysis.inputs.{name}")
        manifest_path, _ = _pin(binding.get("manifest"), f"{name} manifest")
        bundles[name] = bundle_verifier(manifest_path)
    receipts = {}
    for name, value in inputs.items():
        binding = _map(value, f"analysis.inputs.{name}")
        if binding.get("score_source", "complete-score-receipt") != "complete-score-receipt":
            raise SlurpTopNAnalysisError(f"{name} must use a complete-score-receipt")
        receipt_path, receipt_sha = _pin(binding.get("score_receipt"), f"{name} score receipt")
        receipt = _map(binding.get("score_receipt"), f"{name} score receipt")
        cell_id = receipt.get("cell_id")
        if not isinstance(cell_id, str) or not cell_id:
            raise SlurpTopNAnalysisError(f"{name} score receipt cell_id is required")
        try:
            receipts[name] = score_receipt_verifier(
                SavedScoreReceiptRef(cell_id=cell_id, path=receipt_path, sha256=receipt_sha),
                bundles[name],
            )
        except Exception as error:
            raise SlurpTopNAnalysisError(f"{name} complete score receipt failed: {error}") from error
    source_rows, source_manifest, source_states = _source_rows(
        source, source_bundle, full_ids, state_loader=state_loader
    )
    references = _references(
        _map(source_section.get("reference_source"), "reference_source"),
        full_ids, loader=reference_loader
    )
    branches = {
        str(name): _branch_rows(
            str(name), bundles[name], source_path, source_sha, source_states, full_ids
        )
        for name in inputs
    }
    width = source.get("candidate_count", 3)
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise SlurpTopNAnalysisError("candidate_count must be a positive integer")
    populations = {
        "NEW500": set(primary_ids),
        "DEV1000": set(full_ids),
        "OLD500": set(full_ids) - set(primary_ids),
    }
    field = spec.get("stratum_field", "scenario")
    if not isinstance(field, str) or not field:
        raise SlurpTopNAnalysisError("stratum_field must be nonempty text")
    reports = {}
    for population, ids in populations.items():
        if not ids:
            raise SlurpTopNAnalysisError(f"population {population} is empty")
        src, refs = _subset(source_rows, ids), _subset(references, ids)
        br = {name: _subset(rows, ids) for name, rows in branches.items()}
        try:
            report = aggregate_topn_diagnostics(src, refs, br, candidate_width=width).as_json()
        except TopNDiagnosticError as error:
            raise SlurpTopNAnalysisError(f"{population} aggregation failed: {error}") from error
        strata = {}
        for sample_id in ids:
            value = metadata[sample_id].get(field)
            if not isinstance(value, str) or not value:
                raise SlurpTopNAnalysisError(f"metadata {field} missing for {sample_id!r}")
            strata.setdefault(value, set()).add(sample_id)
        report["per_stratum"] = {
            key: aggregate_topn_diagnostics(
                _subset(src, members), _subset(refs, members),
                {name: _subset(rows, members) for name, rows in br.items()},
                candidate_width=width,
            ).as_json()
            for key, members in sorted(strata.items())
        }
        reports[population] = report
    result = {
        "schema": "saea-slurp-topn-diagnostics-v1",
        "experiment_id": config.get("experiment_id"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"path": str(config_path.resolve()), "sha256": digest(config_path)},
        "source": {**source, "manifest": {"path": str(source_path), "sha256": source_sha}},
        "score_gate": {
            name: {"path": value["score_receipt"]["path"],
                   "sha256": value["score_receipt"]["sha256"], "verified": True}
            for name, value in inputs.items()
        },
        "populations": {name: len(ids) for name, ids in populations.items()},
        "stratum_field": field, "diagnostics": reports,
        "model_calls": 0, "encoder_calls": 0, "tokenizer_calls": 0,
        "scorer_invocations": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.config, args.output)
    print(json.dumps({"experiment_id": result["experiment_id"],
                      "populations": result["populations"],
                      "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
