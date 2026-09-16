"""Config-driven source-bound SLURP Top-N diagnostics.

This companion to score_compare_cli verifies sealed bundles and complete score
receipts before delegating all diagnostic counting to the pure aggregator. It
never scores or infers a reference from a prediction. Raw-source uncertainty
uses the existing speaker-cluster resampling function when explicitly configured.
The native-system mode reads Perception state from a separately pinned phase
artifact of the same verified task-answer run; it never invents candidate state
for a direct arm.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..core.bundle.verify import verify_bundle
from ..core.bundle.raw_contact_source import (
    RawContactSourceError,
    _load_verified_trace,
    verify_aborted_contact_source,
)
from ..core.model.native_framework_history import framework_contact_instruction
from ..core.roster import read_roster
from ..core.scoring_receipt import SavedScoreReceiptRef, verify_complete_score_receipt
from ..data.lock import load_lock
from ..data.slurp import load_slurp_split
from ..data.splits import prefixed, split_identity_hash
from ..rails.phase_material import sealed_states_from_manifest
from ..rails.candidate_contract_lookup import MAX_CANDIDATE_IDS
from ..rails.hashing import content_hash
from ..rails.knowledge import AgentStateArtifact
from ..rails.errors import RailsError
from ..rails.slurp_candidate_contracts import build_slurp_candidate_contract_provider
from ..rails.slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS,
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    parse_slurp_intent_hypothesis_state,
)
from ..reproduction.slurp_scoring import parse_slu_response
from ..reproduction.probe_split import load_verified_probe_split
from .native_episode_diagnostics import (
    NativeEpisodeDiagnosticError,
    analyze_verified_native_episode_statistics,
)
from .null_calibration_cli import digest, pinned_json, rows_for
from .paired import resampled_statistic
from .slurp_topn_diagnostics import (
    BranchOutcomeRow,
    ReferenceIntentRow,
    SourceCandidateRow,
    TopNDiagnosticError,
    aggregate_topn_diagnostics,
)


class SlurpTopNAnalysisError(ValueError):
    """An analysis config or source binding failed closed."""


_NATIVE_SOURCE_KEY = "native_system_perception_source"


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
        document = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(document, Mapping) and "carrier" in document and "carrier_lock_key" not in document:
            if path.parent.name != "probe-samples":
                raise SlurpTopNAnalysisError("legacy roster must use its registered probe-samples path")
            verified = load_verified_probe_split(path.parents[3], path.stem)
            item_ids = [item["id"] for item in document["items"]]
            if set(item_ids) != set(verified.ids):
                raise SlurpTopNAnalysisError("legacy roster item IDs differ from verified keys")
        else:
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


def _select_source_binding(
    source_section: Mapping[str, object],
) -> tuple[str, Mapping[str, object], bool]:
    """Select exactly one registered source binding.

    The historical fixed Top-3 key remains the default. The distinct-source
    key is an explicit opt-in and is reported to the caller as such.
    """
    fixed = source_section.get("shared_fixed_top3_source")
    distinct = source_section.get("shared_distinct_source")
    if fixed is not None and distinct is not None:
        raise SlurpTopNAnalysisError(
            "source binding must select exactly one fixed or distinct source"
        )
    if distinct is not None:
        return "shared_distinct_source", _map(distinct, "shared distinct source"), True
    if fixed is not None:
        return "shared_fixed_top3_source", _map(fixed, "shared fixed Top-3 source"), False
    raise SlurpTopNAnalysisError(
        "source binding must provide shared_fixed_top3_source or shared_distinct_source"
    )


def _source_candidate_width(
    binding: Mapping[str, object], *, distinct: bool,
) -> int:
    """Resolve the parser width while enforcing the distinct-source range."""
    raw_width = binding.get("candidate_count")
    raw_range = binding.get("candidate_count_range")
    if distinct:
        if raw_range is not None:
            if (
                isinstance(raw_range, (str, bytes))
                or not isinstance(raw_range, Sequence)
                or len(raw_range) != 2
                or any(isinstance(value, bool) or not isinstance(value, int) for value in raw_range)
                or not 1 <= raw_range[0] <= raw_range[1] <= MAX_CANDIDATE_IDS
            ):
                raise SlurpTopNAnalysisError(
                    "distinct source candidate_count_range must be positive, "
                    "ordered, and within the shared candidate bound"
                )
            if raw_width is None:
                raw_width = raw_range[1]
        elif raw_width is None:
            raw_width = 3
    if raw_width is None:
        raw_width = 3
    if isinstance(raw_width, bool) or not isinstance(raw_width, int) or raw_width < 1:
        raise SlurpTopNAnalysisError(
            "candidate_count must be a positive integer"
            + (" within the shared candidate bound for a distinct source" if distinct else "")
        )
    if distinct and raw_width > MAX_CANDIDATE_IDS:
        raise SlurpTopNAnalysisError(
            "candidate_count exceeds the shared candidate bound"
        )
    if distinct and raw_range is not None and not raw_range[0] <= raw_width <= raw_range[1]:
        raise SlurpTopNAnalysisError(
            "distinct source candidate_count must be within candidate_count_range"
        )
    return raw_width


def _entity_correctness_from_verified_score_document(
    document: Mapping[str, object],
    *,
    scorer: str,
    expected_ids: set[str],
) -> dict[str, bool | None]:
    """Map verified official exact entity sufficient counts to row booleans.

    slot_f1_exact_fp and slot_f1_exact_fn are the only accepted evidence.
    Missing fields leave every row unavailable; F1 values are never used as
    a substitute.
    """
    if not isinstance(scorer, str) or not scorer:
        raise SlurpTopNAnalysisError("entity score scorer must be nonempty text")
    try:
        rows = rows_for(
            dict(document), scorer,
            ("slot_f1_exact_fp", "slot_f1_exact_fn"),
        )
    except ValueError as error:
        if "missing or has invalid retained field" in str(error):
            return {sample_id: None for sample_id in expected_ids}
        raise SlurpTopNAnalysisError(
            f"verified entity score rows are unavailable: {error}"
        ) from error
    if set(rows) != expected_ids:
        raise SlurpTopNAnalysisError("verified entity score roster mismatch")
    result: dict[str, bool | None] = {}
    for sample_id in expected_ids:
        fp = rows[sample_id]["slot_f1_exact_fp"]
        fn = rows[sample_id]["slot_f1_exact_fn"]
        if not math.isfinite(fp) or not math.isfinite(fn) or fp < 0 or fn < 0:
            raise SlurpTopNAnalysisError(
                f"verified entity counts are invalid for {sample_id!r}"
            )
        result[sample_id] = fp == 0.0 and fn == 0.0
    return result


def _entity_correctness_from_verified_receipt(
    receipt: Mapping[str, object],
    *,
    scorer: str,
    expected_ids: set[str],
) -> dict[str, bool | None]:
    """Load the hash-pinned score result from an already verified receipt."""
    score_pin = receipt.get("score_result")
    if not isinstance(score_pin, Mapping):
        return {sample_id: None for sample_id in expected_ids}
    try:
        document = pinned_json(dict(score_pin))
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        raise SlurpTopNAnalysisError(
            f"verified score result cannot be read: {error}"
        ) from error
    return _entity_correctness_from_verified_score_document(
        document, scorer=scorer, expected_ids=expected_ids
    )


def _metadata(value: object, expected: set[str]) -> dict[str, Mapping[str, object]]:
    document = pinned_json(_map(value, "analysis.metadata"))
    rows = document.get("rows") if isinstance(document, Mapping) else None
    if isinstance(rows, Mapping):
        converted = []
        for sample_id, row in rows.items():
            if not isinstance(row, Mapping) or row.get("sample_id", sample_id) != sample_id:
                raise SlurpTopNAnalysisError("analysis.metadata row identity mismatch")
            converted.append({"sample_id": sample_id, **row})
        rows = converted
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


def _source_pin(binding, *, distinct=False):
    """Resolve the actual source artifact without relabelling it a model run."""
    artifact = binding.get("hypothesis_artifact") if distinct else None
    manifest = binding.get("manifest")
    if artifact is not None and manifest is not None and artifact != manifest:
        raise SlurpTopNAnalysisError("conflicting source artifact and manifest pins")
    return _pin(artifact if artifact is not None else manifest, "source artifact")


def _source_contract(bundle, *, distinct=False):
    """Read the contract under the verified original or derived source authority."""
    from ..core.bundle.hypothesis_source import is_derived_hypothesis_bundle

    manifest = _map(getattr(bundle, "manifest", None), "verified source manifest")
    if distinct and is_derived_hypothesis_bundle(bundle):
        source_inputs = _map(manifest.get("source_inputs"), "derived source inputs")
        source_pin = _map(source_inputs.get("source_config"), "original source config")
        baseline = _map(pinned_json(dict(source_pin)), "original source baseline")
        artifact = _map(baseline.get("artifact_result"), "original artifact_result")
        contract = _map(artifact.get("content_contract"), "original content contract")
        data_root = manifest.get("data_root")
        if not isinstance(data_root, str) or not data_root:
            raise SlurpTopNAnalysisError("derived source data_root must be explicit")
        return contract, Path(data_root)
    if (manifest.get("status") != "COMPLETED"
            or getattr(bundle, "attempt_state", None) != "FINALIZED"):
        raise SlurpTopNAnalysisError(
            "source must be FINALIZED/COMPLETED or an explicitly verified distinct derivation"
        )
    artifact = _map(manifest.get("artifact_result"), "source artifact_result")
    if (artifact.get("schema") != "saea-artifact-result-binding-v2"
            or artifact.get("role") != "slurp-intent-hypotheses"):
        raise SlurpTopNAnalysisError("common source is not a typed SLURP hypothesis artifact")
    contract = _map(artifact.get("content_contract"), "source content contract")
    catalog = _map(contract.get("source_catalog"), "source candidate catalog")
    source_meta = _map(manifest.get("artifact_content_source"), "source content source")
    data_root = Path(str(source_meta.get("path")))
    relpath = catalog.get("data_relpath")
    if not isinstance(relpath, str) or not relpath:
        raise SlurpTopNAnalysisError("source candidate catalog lacks data_relpath")
    for _ in relpath.split("/"):
        data_root = data_root.parent
    return contract, data_root


def _source_rows(binding, bundle, full_ids, *, state_loader, distinct=False):
    manifest_path, manifest_sha = _source_pin(binding, distinct=distinct)
    manifest = _map(getattr(bundle, "manifest", None), "verified source manifest")
    if set(getattr(bundle, "split_ids", ())) != set(full_ids):
        raise SlurpTopNAnalysisError("common source roster does not match full roster")
    contract, data_root = _source_contract(bundle, distinct=distinct)
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
    try:
        validator = build_slurp_hypothesis_artifact_validator(contract, data_root=data_root)
    except Exception as error:
        raise SlurpTopNAnalysisError(f"source candidate catalog validation failed: {error}") from error
    width = _source_candidate_width(binding, distinct=distinct)
    if width > len(validator.legal_intent_ids):
        raise SlurpTopNAnalysisError(
            "source candidate width exceeds the legal intent inventory"
        )
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


def _pinned_json_mapping(value: object, label: str) -> tuple[Path, str, Mapping[str, object]]:
    path, sha256 = _pin(value, label)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SlurpTopNAnalysisError(f"{label} is not readable JSON: {error}") from error
    return path, sha256, _map(document, label)


def _validate_flight_receipts(
    document: Mapping[str, object],
    *,
    run_id: str,
    attempt_id: str,
    phase_path: Path,
    phase_sha256: str,
) -> Mapping[str, object]:
    """Return the recorded phase-supply receipt after checking its ledger.

    The driver may preserve either ``FlightReceipts.as_json()`` itself or the
    CLI object which carries it under ``receipts``.  Both contain the same
    self-hashed stage ledger; accepting the wrapper does not weaken it.
    """
    inner = document.get("receipts", document)
    receipt = _map(inner, "native flight receipts")
    if (
        receipt.get("schema") != "saea-flight-receipts-v1"
        or receipt.get("run_id") != run_id
        or receipt.get("attempt_id") != attempt_id
    ):
        raise SlurpTopNAnalysisError("native flight receipt run binding mismatch")
    claimed = receipt.get("receipts_hash")
    unsigned = dict(receipt)
    unsigned.pop("receipts_hash", None)
    if claimed != content_hash(unsigned):
        raise SlurpTopNAnalysisError("native flight receipt self-hash mismatch")
    stages = _map(receipt.get("stages"), "native flight receipt stages")
    for stage_name, raw_stage in stages.items():
        stage = _map(raw_stage, f"native flight stage {stage_name!r}")
        unsigned_stage = dict(stage)
        stage_hash = unsigned_stage.pop("stage_hash", None)
        if stage.get("stage") != stage_name or stage_hash != content_hash(unsigned_stage):
            raise SlurpTopNAnalysisError(
                f"native flight stage {stage_name!r} self-hash mismatch"
            )
    run_stage = _map(stages.get("run_phases"), "native run_phases receipt")
    seal_stage = _map(stages.get("seal"), "native seal receipt")
    if (
        Path(str(seal_stage.get("phases_path"))).resolve() != phase_path.resolve()
        or seal_stage.get("phases_sha256") != phase_sha256
    ):
        raise SlurpTopNAnalysisError("native seal receipt does not bind the phase artifact")
    return _map(run_stage.get("phase_supply"), "native phase-supply receipt")


def _native_phase_supply_receipt(
    binding: Mapping[str, object],
    *,
    run_id: str,
    attempt_id: str,
    phase_path: Path,
    phase_sha256: str,
) -> tuple[Mapping[str, object] | None, dict[str, object]]:
    flight = binding.get("flight_receipts")
    if binding.get("candidate_selection_audit") is not None:
        raise SlurpTopNAnalysisError(
            "native candidate selection audits require genuine preserved flight_receipts"
        )
    if flight is None:
        return None, {
            "status": "unavailable",
            "reason": (
                "the campaign producer did not preserve FlightReceipts; "
                "source-derived candidate diagnostics do not prove actual slot-card supply"
            ),
        }
    path, sha256, document = _pinned_json_mapping(
        flight, "native flight receipts"
    )
    if "receipts" in document and (
        document.get("run_id") != run_id
        or document.get("attempt_id") != attempt_id
    ):
        raise SlurpTopNAnalysisError("native flight receipt wrapper binding mismatch")
    return (
        _validate_flight_receipts(
            document,
            run_id=run_id,
            attempt_id=attempt_id,
            phase_path=phase_path,
            phase_sha256=phase_sha256,
        ),
        {
            "status": "verified",
            "kind": "flight-receipts",
            "path": str(path),
            "sha256": sha256,
        },
    )


def _trace_contact_for_state(
    bundle: object,
    *,
    sample_id: str,
    source_phase: str,
    state: AgentStateArtifact,
    contact: Mapping[str, object],
    allow_prior_history: bool = False,
    execution_contact: Mapping[str, object] | None = None,
) -> None:
    """Join a phase-local Perception state to manifest-verified raw trace records."""
    plan = _map(contact.get("plan"), "native Perception contact plan")
    agent_contact_id = plan.get("contact_id")
    trace_records = getattr(bundle, "trace_records", None)
    if not isinstance(trace_records, Mapping):
        raise SlurpTopNAnalysisError("verified native bundle lacks trace records")
    uses = [
        (record_id, record)
        for record_id, record in trace_records.items()
        if isinstance(record_id, str)
        and record_id.endswith("/native-role-contact")
        and isinstance(record, Mapping)
        and record.get("use_agent_contact_id") == agent_contact_id
    ]
    if len(uses) != 1:
        raise SlurpTopNAnalysisError(
            f"native Perception trace contact mismatch for {sample_id!r}"
        )
    use_record_id, use = uses[0]
    request_id = use_record_id.removesuffix("/native-role-contact")
    request = trace_records.get(f"{request_id}/request")
    response = trace_records.get(f"{request_id}/response")
    if not isinstance(request, Mapping) or not isinstance(response, Mapping):
        raise SlurpTopNAnalysisError(
            f"native Perception trace request or response missing for {sample_id!r}"
        )
    payload = request.get("payload")
    history = payload.get("history") if isinstance(payload, Mapping) else None
    control_rows = (
        [
            row
            for row in history
            if isinstance(row, Mapping) and row.get("role") == "control"
        ]
        if isinstance(history, list)
        else []
    )
    current_control_rows = [
        row for row in control_rows if row.get("contact_id") == agent_contact_id
    ]
    control = current_control_rows[0] if len(current_control_rows) == 1 else {}
    control_text = control.get("content")
    # Perception has no local tools. Compare the complete canonical producer
    # envelope, whose initial user message carries the phase instruction.
    expected_control = (
        framework_contact_instruction(
            role_id=source_phase, sample_id=sample_id, contact_id=agent_contact_id,
            messages=[
                {"role": "system", "content": payload["task_instruction"]},
                {"role": "user", "content": plan["instruction"]},
            ],
            local_tool_result_ids=[],
        )
        if isinstance(payload, Mapping)
        and isinstance(payload.get("task_instruction"), str)
        and payload["task_instruction"]
        and isinstance(plan.get("instruction"), str) and plan["instruction"]
        else None
    )
    expected_text_sha256 = hashlib.sha256(state.content.encode("utf-8")).hexdigest()
    if (
        not isinstance(payload, Mapping)
        or payload.get("request_id") != request_id
        or payload.get("sample_id") != sample_id
        or request.get("payload_sha256") != use.get("use_request_sha256")
        or use.get("use_role_id") != source_phase
        or len(current_control_rows) != 1
        or (not allow_prior_history and len(control_rows) != 1)
        or (not allow_prior_history and len(history) != 1)
        or history[-1] != control
        or not isinstance(control_text, str)
        or control_text != expected_control
        or hashlib.sha256(control_text.encode("utf-8")).hexdigest()
        != control.get("content_sha256")
        or response.get("text") != state.content
        or response.get("response_text_sha256") != expected_text_sha256
        or response.get("response_text_sha256")
        != use.get("use_response_text_sha256")
        or response.get("response_sha256") != use.get("use_response_sha256")
        or (
            execution_contact is not None
            and (
                execution_contact.get("agent_contact_id") != agent_contact_id
                or execution_contact.get("request_id") != request_id
                or execution_contact.get("request_sha256")
                != request.get("payload_sha256")
                or execution_contact.get("response_sha256")
                != response.get("response_sha256")
                or execution_contact.get("response_text_sha256")
                != response.get("response_text_sha256")
            )
        )
        or state.source_response_sha256 != response.get("response_text_sha256")
        or contact.get("response_sha256") != response.get("response_text_sha256")
        or contact.get("query_state_sha256") != state.source_query_state_sha256
        or plan.get("query_state_sha256") != state.source_query_state_sha256
        or state.state_id != f"{agent_contact_id}:{source_phase}:{sample_id}"
    ):
        raise SlurpTopNAnalysisError(
            f"native Perception state differs from manifest-verified trace for {sample_id!r}"
        )


def verify_native_perception_state_contact(
    bundle: object,
    *,
    sample_id: str,
    source_phase: str,
    state: AgentStateArtifact,
    contact: Mapping[str, object],
    allow_prior_history: bool = False,
    execution_contact: Mapping[str, object] | None = None,
) -> None:
    """Expose the manifest-verified Perception contact join.

    Refreshed visits may carry prior history, but their current control envelope
    must remain unique and last. The singleton reader keeps the stricter default.
    """

    _trace_contact_for_state(
        bundle,
        sample_id=sample_id,
        source_phase=source_phase,
        state=state,
        contact=contact,
        allow_prior_history=allow_prior_history,
        execution_contact=execution_contact,
    )


def _validate_candidate_audits(
    phase_supply: Mapping[str, object],
    *,
    states: Mapping[str, AgentStateArtifact],
    parsed_states: Mapping[str, object],
    legal_inventory_sha256: str,
    legal_inventory_count: int,
    selection_phase: str,
    source_phase: str,
    projection_policy: str,
    max_candidates: int,
) -> dict[str, int]:
    if phase_supply.get("schema") != "saea-named-knowledge-store-routing-v1":
        raise SlurpTopNAnalysisError("native phase supply is not named-store routing")
    candidate_supply = _map(
        phase_supply.get("candidate_supply"), "native candidate supply receipt"
    )
    if candidate_supply.get("schema") != "saea-candidate-semantic-supply-v1":
        raise SlurpTopNAnalysisError("native candidate supply receipt schema mismatch")
    if (
        candidate_supply.get("candidate_inventory_authority")
        != "task-adapter-candidate-contract-provider"
        or candidate_supply.get("candidate_inventory_sha256")
        != legal_inventory_sha256
        or candidate_supply.get("candidate_inventory_count") != legal_inventory_count
    ):
        raise SlurpTopNAnalysisError("native candidate legal inventory hash mismatch")
    specs = candidate_supply.get("specs")
    if not isinstance(specs, list):
        raise SlurpTopNAnalysisError("native candidate supply specs are malformed")
    matches = [
        spec for spec in specs
        if isinstance(spec, Mapping) and spec.get("phase") == selection_phase
    ]
    if len(matches) != 1:
        raise SlurpTopNAnalysisError("native candidate supply must have one selection-phase spec")
    spec = matches[0]
    spec_store_id = spec.get("store_id")
    if (
        not isinstance(spec_store_id, str)
        or not spec_store_id
        or spec.get("candidate_state_phase") != source_phase
        or spec.get("compact_source_phase") != source_phase
        or spec.get("projection_policy") != projection_policy
        or spec.get("max_candidates") != max_candidates
        or spec.get("provider") != "slurp-candidate-semantic-v1"
        or spec.get("rank_policy") != "saea-ranked-candidate-round-robin-v1"
        or spec.get("fuse_policy") != "saea-candidate-semantic-passthrough-v1"
    ):
        raise SlurpTopNAnalysisError("native candidate supply policy binding mismatch")
    stores = _map(phase_supply.get("stores"), "native named-store receipts")
    store_receipt = _map(
        stores.get(spec_store_id), "native candidate named-store receipt"
    )
    audits = _map(
        phase_supply.get("candidate_selections"), "native candidate selection audits"
    )
    nested_audits = candidate_supply.get("candidate_selections")
    if nested_audits is not None and nested_audits != audits:
        raise SlurpTopNAnalysisError("native candidate selection audit copies differ")
    counts = {sample_id: 0 for sample_id in states}
    store_fields = (
        "store_id", "store_role", "store_snapshot_sha256", "store_release_sha256",
        "store_source_sha256", "composite_snapshot_sha256",
    )
    outer_fields = (
        *store_fields, "query_state_sha256", "qualified_selected_value_ids",
        "supply_disposition", "selection_receipt_sha256",
    )
    for audit_key, raw_audit in audits.items():
        audit = _map(raw_audit, f"native candidate audit {audit_key!r}")
        sample_id = audit.get("sample_id")
        if sample_id not in states:
            raise SlurpTopNAnalysisError("native candidate audit has a foreign sample")
        if not isinstance(audit_key, str) or not audit_key.startswith(
            f"{selection_phase}:{sample_id}:"
        ) or audit_key.rsplit(":", 1)[-1] != audit.get("query_state_sha256"):
            raise SlurpTopNAnalysisError("native candidate audit key binding mismatch")
        state = states[str(sample_id)]
        parsed = parsed_states[str(sample_id)]
        projection = getattr(parsed, "projection", None)
        expected_projection = None if projection is None else json.loads(
            json.dumps(asdict(projection))
        )
        if (
            audit.get("schema") != "saea-candidate-semantic-selection-v1"
            or audit.get("candidate_state_id") != state.state_id
            or audit.get("candidate_state_sha256")
            != hashlib.sha256(state.content.encode("utf-8")).hexdigest()
            or audit.get("candidate_source_response_sha256")
            != state.source_response_sha256
            or audit.get("candidate_ids")
            != [candidate.intent_id for candidate in parsed.candidates]
            or audit.get("candidate_projection") != expected_projection
            or audit.get("legal_candidate_inventory_sha256") != legal_inventory_sha256
            or audit.get("selection_policy_id")
            != "saea-ranked-candidate-round-robin-v1"
            or audit.get("max_candidates") != max_candidates
            or audit.get("compact_source_phase") != source_phase
        ):
            raise SlurpTopNAnalysisError("native candidate audit source or policy mismatch")
        provenance_hashes = store_fields[2:]
        if (
            audit.get("store_id") != spec_store_id
            or audit.get("store_role") != "slot-contracts"
            or any(
                not isinstance(audit.get(field), str)
                or len(str(audit.get(field))) != 64
                for field in provenance_hashes
            )
            or any(audit.get(field) != store_receipt.get(field) for field in store_fields)
        ):
            raise SlurpTopNAnalysisError("native candidate audit lacks released-store provenance")
        selection_unsigned = {
            key: value for key, value in audit.items()
            if key not in outer_fields and key != "selection_sha256"
        }
        if audit.get("selection_sha256") != content_hash(selection_unsigned):
            raise SlurpTopNAnalysisError("native candidate selection hash mismatch")
        receipt_unsigned = dict(audit)
        receipt_hash = receipt_unsigned.pop("selection_receipt_sha256", None)
        if receipt_hash != content_hash(receipt_unsigned):
            raise SlurpTopNAnalysisError("native candidate selection receipt hash mismatch")
        counts[str(sample_id)] += 1
    if any(count == 0 for count in counts.values()):
        raise SlurpTopNAnalysisError("native candidate selection audit roster is incomplete")
    return counts


def _native_system_rows(
    binding: Mapping[str, object],
    bundle: object,
    full_ids: Sequence[str],
    *,
    legal_ids: frozenset[str],
) -> tuple[
    tuple[SourceCandidateRow, ...],
    tuple[BranchOutcomeRow, ...],
    dict[str, object],
]:
    """Load internal native Perception state from one verified answer bundle."""
    manifest = _map(getattr(bundle, "manifest", None), "verified native manifest")
    if (
        manifest.get("status") != "COMPLETED"
        or getattr(bundle, "attempt_state", None) != "FINALIZED"
    ):
        raise SlurpTopNAnalysisError("native source must be FINALIZED/COMPLETED")
    if set(getattr(bundle, "split_ids", ())) != set(full_ids):
        raise SlurpTopNAnalysisError("native source roster does not match full roster")
    split = _map(manifest.get("split"), "native manifest split")
    if (
        split.get("identity_hash") != binding.get("split_identity_hash")
        or binding.get("split_identity_hash")
        != split_identity_hash(prefixed("slurp", full_ids))
    ):
        raise SlurpTopNAnalysisError("native source split identity mismatch")
    run_id = manifest.get("run_id")
    plan = _map(manifest.get("plan"), "native manifest plan")
    attempt_id, protocol_hash = plan.get("attempt_id"), plan.get("protocol_hash")
    if not all(isinstance(value, str) and value for value in (run_id, attempt_id, protocol_hash)):
        raise SlurpTopNAnalysisError("native manifest run binding is incomplete")
    phase_pin = _map(binding.get("phase_artifact"), "native phase artifact pin")
    phase_path, phase_sha256, phases = _pinned_json_mapping(
        phase_pin, "native phase artifact"
    )
    manifest_path = Path(getattr(bundle, "manifest_path", binding["manifest"]["path"]))
    if phase_path.resolve().parent != manifest_path.resolve().parent:
        raise SlurpTopNAnalysisError("native phase artifact is outside the manifest run directory")
    if (
        phases.get("schema") != "saea-flight-phase-summaries-v1"
        or phases.get("run_id") != run_id
        or phases.get("attempt_id") != attempt_id
    ):
        raise SlurpTopNAnalysisError("native phase artifact run binding mismatch")
    producer = binding.get("producer_policy_id")
    source_phase = binding.get("compact_source_phase", "perception")
    selection_phase = binding.get("candidate_selection_phase", "solver")
    projection_policy = binding.get(
        "projection_policy", BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
    )
    width = _source_candidate_width(binding, distinct=True)
    if (
        not isinstance(producer, str) or not producer
        or source_phase != "perception"
        or not isinstance(selection_phase, str) or not selection_phase
        or projection_policy not in BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS
        or (
            width > 3
            and projection_policy
            != CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
        )
        or width > len(legal_ids)
        or phases.get("policy") != producer
    ):
        raise SlurpTopNAnalysisError("native source phase or projection policy binding mismatch")
    summaries = phases.get("phases")
    if not isinstance(summaries, list):
        raise SlurpTopNAnalysisError("native phase artifact lacks phase summaries")
    matched = [
        summary for summary in summaries
        if isinstance(summary, Mapping) and summary.get("controller_policy_id") == producer
    ]
    if len(matched) != 1:
        raise SlurpTopNAnalysisError("native phase artifact must have one system summary")
    summary = matched[0]
    if summary.get("run_id") != run_id or summary.get("protocol_hash") != protocol_hash:
        raise SlurpTopNAnalysisError("native phase summary run or protocol binding mismatch")
    result_rows = summary.get("results")
    if not isinstance(result_rows, list):
        raise SlurpTopNAnalysisError("native phase summary lacks results")
    results: dict[str, Mapping[str, object]] = {}
    for row in result_rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("sample_id"), str):
            raise SlurpTopNAnalysisError("native phase result is malformed")
        if row["sample_id"] in results:
            raise SlurpTopNAnalysisError("native phase results contain duplicate samples")
        results[row["sample_id"]] = row
    if set(results) != set(full_ids):
        raise SlurpTopNAnalysisError("native phase result roster mismatch")
    outputs: dict[str, Mapping[str, object]] = {}
    for row in getattr(bundle, "outputs_rows", ()):
        if not isinstance(row, Mapping) or not isinstance(row.get("sample_id"), str):
            raise SlurpTopNAnalysisError("native output row is malformed")
        if row["sample_id"] in outputs:
            raise SlurpTopNAnalysisError("native outputs contain duplicate samples")
        outputs[row["sample_id"]] = row
    if set(outputs) != set(full_ids):
        raise SlurpTopNAnalysisError("native output roster mismatch")
    legal_inventory_sha256 = content_hash({"candidate_ids": sorted(legal_ids)})
    states: dict[str, AgentStateArtifact] = {}
    parsed_states: dict[str, object] = {}
    branches: list[BranchOutcomeRow] = []
    source_rows: list[SourceCandidateRow] = []
    final_parse_status: dict[str, bool] = {}
    for sample_id in full_ids:
        result, output_row = results[sample_id], outputs[sample_id]
        text = output_row.get("text")
        if (
            not isinstance(text, str)
            or result.get("final_response_text") != text
            or result.get("final_response_sha256")
            != hashlib.sha256(text.encode("utf-8")).hexdigest()
            or result.get("native_episode_receipt") != output_row.get("native_episode_receipt")
            or not isinstance(result.get("native_episode_receipt"), Mapping)
        ):
            raise SlurpTopNAnalysisError(
                f"native final output binding mismatch for {sample_id!r}"
            )
        raw_states = result.get("agent_states")
        if not isinstance(raw_states, list):
            raise SlurpTopNAnalysisError(f"native states missing for {sample_id!r}")
        matches = [
            raw for raw in raw_states
            if isinstance(raw, Mapping) and raw.get("state_kind") == f"phase:{source_phase}"
        ]
        if len(matches) != 1:
            raise SlurpTopNAnalysisError(
                f"native source requires exactly one Perception state for {sample_id!r}"
            )
        try:
            state = AgentStateArtifact.from_json(matches[0]).validate()
            parsed = parse_slurp_intent_hypothesis_state(
                state,
                expected_sample_id=sample_id,
                legal_intent_ids=legal_ids,
                max_candidates=width,
                compact_source_phase=source_phase,
                projection_policy=projection_policy,
            )
        except (KeyError, TypeError, ValueError, RailsError) as error:
            raise SlurpTopNAnalysisError(
                f"native Perception state for {sample_id!r} is invalid: {error}"
            ) from error
        contacts = result.get("contacts")
        if not isinstance(contacts, list):
            raise SlurpTopNAnalysisError(f"native contacts missing for {sample_id!r}")
        source_contacts = [
            contact for contact in contacts
            if isinstance(contact, Mapping)
            and isinstance(contact.get("plan"), Mapping)
            and state.state_id
            == f"{contact['plan'].get('contact_id')}:{source_phase}:{sample_id}"
        ]
        if (
            len(source_contacts) != 1
            or source_contacts[0].get("query_state_sha256")
            != state.source_query_state_sha256
            or source_contacts[0].get("response_sha256")
            != state.source_response_sha256
            or state.producer_policy_id != producer
        ):
            raise SlurpTopNAnalysisError(
                f"native Perception state source contact mismatch for {sample_id!r}"
            )
        _trace_contact_for_state(
            bundle,
            sample_id=sample_id,
            source_phase=source_phase,
            state=state,
            contact=source_contacts[0],
        )
        states[sample_id], parsed_states[sample_id] = state, parsed
        candidate_ids = tuple(candidate.intent_id for candidate in parsed.candidates)
        source_rows.append(SourceCandidateRow(sample_id, candidate_ids))
        scenario, action, _entities, parsed_final = parse_slu_response(text)
        final_parse_status[sample_id] = parsed_final
        final_intent = (
            f"{scenario}_{action}" if isinstance(scenario, str) and scenario
            and isinstance(action, str) and action else None
        )
        branches.append(BranchOutcomeRow(
            sample_id, final_intent, False, None,
            missing_final_intent=final_intent is None,
        ))
    phase_supply, audit_source = _native_phase_supply_receipt(
        binding,
        run_id=run_id,
        attempt_id=attempt_id,
        phase_path=phase_path,
        phase_sha256=phase_sha256,
    )
    audit_counts = (
        {}
        if phase_supply is None
        else _validate_candidate_audits(
            phase_supply,
            states=states,
            parsed_states=parsed_states,
            legal_inventory_sha256=legal_inventory_sha256,
            legal_inventory_count=len(legal_ids),
            selection_phase=selection_phase,
            source_phase=source_phase,
            projection_policy=projection_policy,
            max_candidates=width,
        )
    )
    try:
        postseal = analyze_verified_native_episode_statistics(
            sample_ids=full_ids,
            controller_policy_id=producer,
            phase_results=results,
            output_rows=outputs,
            trace_records=_map(
                getattr(bundle, "trace_records", None),
                "verified native trace records",
            ),
        )
    except NativeEpisodeDiagnosticError as error:
        raise SlurpTopNAnalysisError(
            f"native episode diagnostics failed: {error}"
        ) from error
    raw_widths: list[int] = []
    projected_widths: list[int] = []
    duplicate_counts: list[int] = []
    for sample_id in full_ids:
        parsed = parsed_states[sample_id]
        projection = getattr(parsed, "projection", None)
        if projection is None:
            raise SlurpTopNAnalysisError(
                f"native Perception projection is unavailable for {sample_id!r}"
            )
        raw_width = len(projection.raw_positions)
        projected_width = len(parsed.candidates)
        raw_widths.append(raw_width)
        projected_widths.append(projected_width)
        duplicate_counts.append(raw_width - projected_width)

    def histogram(values: Sequence[int]) -> dict[str, int]:
        return {
            str(value): sum(item == value for item in values)
            for value in sorted(set(values))
        }

    return tuple(source_rows), tuple(branches), {
        "phase_artifact": {"path": str(phase_path), "sha256": phase_sha256},
        "candidate_source": {
            "status": "verified-source-derived-projection",
            "custody": (
                "independently pinned phase artifact joined to the "
                "manifest-verified raw request/response trace"
            ),
        },
        "actual_candidate_supply": {
            **audit_source,
            "candidate_selection_audits": (
                None if phase_supply is None else sum(audit_counts.values())
            ),
            "samples_with_candidate_selection_audit": (
                None if phase_supply is None else len(audit_counts)
            ),
        },
        "perception_projection_diagnostics": {
            "sample_count": len(full_ids),
            "raw_candidate_position_count": sum(raw_widths),
            "projected_distinct_candidate_count": sum(projected_widths),
            "duplicate_candidate_position_count": sum(duplicate_counts),
            "raw_width_histogram": histogram(raw_widths),
            "projected_width_histogram": histogram(projected_widths),
            "duplicate_count_histogram": histogram(duplicate_counts),
            "semantics": (
                "Duplicates are repeated intent IDs in the untouched compact "
                "Perception candidates before first-occurrence projection."
            ),
        },
        "final_answer_format_diagnostics": {
            "sample_count": len(full_ids),
            "parsed_count": sum(final_parse_status.values()),
            "malformed_count": sum(
                not value for value in final_parse_status.values()
            ),
            "refusal_count": 0,
            "semantics": (
                "Finalized native episodes have an accepted Solver response; "
                "nonempty malformed SLURP answers are counted separately."
            ),
        },
        "native_episode_postseal_diagnostics": postseal,
        "projection_policy": projection_policy,
        "candidate_count_range": [1, width],
        "legal_candidate_inventory_sha256": legal_inventory_sha256,
    }


def load_verified_native_system_candidate_rows(
    binding: Mapping[str, object],
    bundle: object,
    full_ids: Sequence[str],
    *,
    legal_ids: frozenset[str],
):
    """Expose the existing verified native Perception join to offline sidecars."""

    return _native_system_rows(binding, bundle, full_ids, legal_ids=legal_ids)


def _verified_reference_records(binding, expected_ids, *, loader):
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
    return tuple(by_id[sample_id] for sample_id in expected_ids)


def _references(binding, expected_ids, *, loader):
    return tuple(
        ReferenceIntentRow(record.sample_id, record.intent)
        for record in _verified_reference_records(
            binding, expected_ids, loader=loader
        )
    )


def load_verified_slurp_reference_intents(binding, expected_ids, *, loader):
    """Expose the existing source-bound reference join to offline sidecars.

    Callers must discard the returned intent strings before persisting any
    model-visible or runtime artifact.
    """

    return _references(binding, expected_ids, loader=loader)


def load_verified_slurp_reference_records(binding, expected_ids, *, loader):
    """Return full scoring-side records through the existing verified join.

    Gold fields are offline-only. Callers must never pass these records into a
    runtime request or copy reference strings into a model-visible artifact.
    """

    return _verified_reference_records(binding, expected_ids, loader=loader)


def _authoritative_candidate_ids(binding: Mapping[str, object], *, loader) -> frozenset[str]:
    """Load the exact candidate-contract authority used by the task adapter."""
    if binding.get("kind") != "slurp-split":
        raise SlurpTopNAnalysisError("legal inventory requires a slurp-split binding")
    lock_path, _ = _pin(binding.get("lock"), "reference lock")
    data_root = binding.get("data_root")
    if not isinstance(data_root, str) or not data_root:
        raise SlurpTopNAnalysisError("reference data_root must be explicit")
    try:
        provider = loader(load_lock(lock_path), Path(data_root))
        legal = frozenset(provider.candidate_ids)
    except Exception as error:
        raise SlurpTopNAnalysisError(
            f"authoritative candidate contract provider failed: {error}"
        ) from error
    if not legal or any(not isinstance(intent_id, str) or not intent_id for intent_id in legal):
        raise SlurpTopNAnalysisError(
            "authoritative candidate contract inventory is empty or malformed"
        )
    return legal


def load_authoritative_slurp_candidate_ids(
    binding: Mapping[str, object], *, loader
) -> frozenset[str]:
    """Expose the task adapter's existing legal candidate inventory loader."""

    return _authoritative_candidate_ids(binding, loader=loader)


def _branch_rows(
    name, bundle, source_path, source_sha, source_states, full_ids,
    entity_correctness: Mapping[str, bool | None] | None = None,
    delivery_diagnostics: dict[str, Mapping[str, object]] | None = None,
):
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
        diagnostics = phase.get("delivery_diagnostics")
        if diagnostics is not None:
            if not isinstance(diagnostics, Mapping):
                raise SlurpTopNAnalysisError(
                    f"{name} delivery diagnostics malformed for {sample_id!r}"
                )
            for key, value in diagnostics.items():
                if not isinstance(key, str) or not key:
                    raise SlurpTopNAnalysisError(
                        f"{name} delivery diagnostic key malformed for {sample_id!r}"
                    )
                if isinstance(value, bool):
                    continue
                if isinstance(value, int) and value >= 0:
                    continue
                raise SlurpTopNAnalysisError(
                    f"{name} delivery diagnostic value malformed for {sample_id!r}"
                )
        if delivery_diagnostics is not None:
            delivery_diagnostics[sample_id] = {
                "flags": None if diagnostics is None else dict(diagnostics),
                "refusal_reason": refusal,
            }
        outcomes.append(
            BranchOutcomeRow(
                sample_id, final_intent, refusal is not None,
                None if entity_correctness is None else entity_correctness.get(sample_id),
            )
        )
    return tuple(outcomes)


def _raw_delivery_diagnostic_report(
    delivery_rows: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str] | set[str] | frozenset[str],
) -> dict[str, object]:
    """Count verified phase delivery flags without reading or scoring outputs.

    delivery_rows is populated while the derived bundle is verified. A missing
    delivery_diagnostics mapping remains unavailable rather than being silently
    interpreted as zero. The old aggregator's out_of_shortlist_attempts is a
    delivered-text projection; this report counts the raw phase flags and
    refusal reasons retained by the bundle.
    """
    ids = tuple(sample_ids)
    if len(ids) != len(set(ids)):
        raise SlurpTopNAnalysisError("raw delivery diagnostic sample ids contain duplicates")
    if not set(ids) <= set(delivery_rows):
        raise SlurpTopNAnalysisError("raw delivery diagnostic roster mismatch")
    flag_values: dict[str, int] = {}
    refusal_reasons: dict[str, int] = {}
    available = 0
    for sample_id in ids:
        row = delivery_rows[sample_id]
        if not isinstance(row, Mapping):
            raise SlurpTopNAnalysisError(
                f"raw delivery diagnostic row malformed for {sample_id!r}"
            )
        flags = row.get("flags")
        flags_available = isinstance(flags, Mapping)
        if flags is None:
            flags = {}
        if not isinstance(flags, Mapping):
            raise SlurpTopNAnalysisError(
                f"raw delivery diagnostic flags malformed for {sample_id!r}"
            )
        if flags_available:
            available += 1
        for key, value in flags.items():
            if not isinstance(key, str) or not key:
                raise SlurpTopNAnalysisError("raw delivery diagnostic flag key malformed")
            if isinstance(value, bool):
                enabled = value
            elif isinstance(value, int) and value >= 0:
                enabled = value != 0
            else:
                raise SlurpTopNAnalysisError(
                    f"raw delivery diagnostic flag value malformed for {sample_id!r}"
                )
            flag_values[key] = flag_values.get(key, 0) + int(enabled)
        refusal = row.get("refusal_reason")
        if refusal is not None:
            if not isinstance(refusal, str) or not refusal:
                raise SlurpTopNAnalysisError(
                    f"raw delivery refusal reason malformed for {sample_id!r}"
                )
            refusal_reasons[refusal] = refusal_reasons.get(refusal, 0) + 1
    return {
        "sample_count": len(ids),
        "diagnostics_available": available == len(ids),
        "diagnostics_available_count": available,
        "diagnostics_unavailable_count": len(ids) - available,
        "flag_row_counts": dict(sorted(flag_values.items())),
        "refused_count": sum(refusal_reasons.values()),
        "refusal_reason_counts": dict(sorted(refusal_reasons.items())),
    }


def _raw_delivery_reports_by_observed_width(
    source_rows: Sequence[SourceCandidateRow],
    delivery_rows: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str] | set[str] | frozenset[str],
) -> dict[str, dict[str, object]]:
    """Group raw delivery flags by the verified distinct candidate width."""
    ids = set(sample_ids)
    groups: dict[int, list[str]] = {1: [], 2: [], 3: []}
    for row in source_rows:
        if row.sample_id not in ids:
            continue
        width = len(set(row.candidate_ids))
        if width not in groups:
            raise SlurpTopNAnalysisError(
                f"observed candidate width {width} is outside supported range"
            )
        groups[width].append(row.sample_id)
    return {
        str(width): _raw_delivery_diagnostic_report(delivery_rows, members)
        for width, members in groups.items()
        if members
    }


def _raw_delivery_reports_by_branch_and_width(
    source_rows: Sequence[SourceCandidateRow],
    delivery_by_branch: Mapping[str, Mapping[str, Mapping[str, object]]],
    sample_ids: Sequence[str] | set[str] | frozenset[str],
) -> dict[str, dict[str, dict[str, object]]]:
    """Transpose per-branch raw delivery reports into width-first groups."""
    per_branch = {
        name: _raw_delivery_reports_by_observed_width(source_rows, rows, sample_ids)
        for name, rows in delivery_by_branch.items()
    }
    return {
        str(width): {
            name: reports[str(width)]
            for name, reports in per_branch.items()
            if str(width) in reports
        }
        for width in (1, 2, 3)
        if any(str(width) in reports for reports in per_branch.values())
    }


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
        if values is None and isinstance(document.get("profiles"), list):
            values = [item.get("candidate_id") for item in document["profiles"]
                      if isinstance(item, Mapping)]
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


def _raw_source_rows(
    trace_path: Path,
    *,
    expected_ids: tuple[str, ...],
    legal_intent_ids: frozenset[str],
    max_candidates: int,
    expected_contacts: int,
    trace_sha256: str,
    expected_audio_seconds: float,
) -> tuple[RawProposalRow, ...]:
    """Parse labels only after the shared carrier contact verifier succeeds."""
    if expected_contacts != len(expected_ids):
        raise SlurpTopNAnalysisError("raw expected contact count does not match roster")
    try:
        _trace_records, contacts = _load_verified_trace(
            {"path": str(trace_path), "sha256": trace_sha256},
            expected_sample_ids=expected_ids,
            expected_audio_seconds=expected_audio_seconds,
        )
    except RawContactSourceError as error:
        raise SlurpTopNAnalysisError(str(error)) from error
    rows = []
    for sample_id in expected_ids:
        contact = contacts[sample_id]
        response = _map(contact["response"], f"raw response {sample_id!r}")
        rows.append(
            RawProposalRow(
                sample_id,
                str(contact["request_id"]),
                _raw_candidate_ids(
                    response.get("text"),
                    sample_id=sample_id,
                    legal_intent_ids=legal_intent_ids,
                    max_candidates=max_candidates,
                ),
            )
        )
    return tuple(rows)


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
    summary["coverage_headroom_count"] = (
        summary["distinct_proposal_coverage_count"] - summary["rank1_correct_count"]
    )
    summary["coverage_headroom"] = summary["coverage_headroom_count"] / len(selected)
    if _include_per_stratum:
        summary["equal_stratum"] = {
            metric: sum(item[metric] for item in summary["per_stratum"].values()) / len(strata)
            for metric in ("rank1_accuracy", "distinct_proposal_coverage", "coverage_headroom")
        }
    return summary


def _raw_uncertainty(rows, references, metadata, ids, settings):
    """Estimate accuracy and within-row candidate headroom with paired cluster draws."""
    seed, replicates, level = settings["seed"], settings["n_replicates"], settings["ci_level"]
    field = settings.get("cluster_field", "speaker")
    if not isinstance(field, str) or not field:
        raise SlurpTopNAnalysisError("bootstrap cluster_field must be nonempty")
    indexed = {row.sample_id: row.candidate_ids for row in rows}
    gold = {row.sample_id: row.intent_id for row in references}
    if any(not str(metadata[s].get(field, "")) for s in ids):
        raise SlurpTopNAnalysisError("bootstrap cluster identity is missing")
    values = {
        "top1_accuracy": {s: int(indexed[s][0] == gold[s]) for s in ids},
        "distinct_proposal_coverage": {s: int(gold[s] in indexed[s]) for s in ids},
    }
    values["coverage_headroom"] = {
        s: values["distinct_proposal_coverage"][s] - values["top1_accuracy"][s] for s in ids
    }
    return {
        metric: resampled_statistic(
            sample_ids=ids,
            statistic=lambda sample, v=value: 100 * sum(v[s] for s in sample) / len(sample),
            seed=seed, n_replicates=replicates, ci_level=level,
            cluster_of=lambda s: str(metadata[s][field]),
        ).as_json()
        for metric, value in values.items()
    }


def run_raw_source(
    config_path,
    output,
    *,
    reference_loader=load_slurp_split,
):
    """Read one pinned aborted attempt and unsealed trace; never repairs or scores it."""
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
    attempt_path, attempt_sha = _pin(raw.get("attempt"), "aborted source attempt")
    plan_path, plan_sha = _pin(raw.get("generation_plan"), "source generation plan")
    try:
        verified_source = verify_aborted_contact_source(
            attempt_pin=raw["attempt"],
            trace_pin=raw["raw_trace"],
            generation_plan_pin=raw["generation_plan"],
            expected_sample_ids=full_ids,
        )
    except RawContactSourceError as error:
        raise SlurpTopNAnalysisError(
            f"aborted contact source verification failed: {error}"
        ) from error
    release_path, release_sha = _pin(
        release.get("registration"), "source quality read registration"
    )
    release_doc = _map(
        json.loads(release_path.read_text(encoding="utf-8")),
        "source quality read registration",
    )
    if release_doc.get("experiment_id") != release["release_id"]:
        raise SlurpTopNAnalysisError("source quality read registration ID differs")
    for key, binding in (
        ("source_attempt", raw["attempt"]),
        ("source_trace", raw["raw_trace"]),
        ("source_generation_plan", raw["generation_plan"]),
        ("full_roster", spec["full_roster"]),
        ("primary_roster", spec["roster"]),
        ("metadata", spec["metadata"]),
    ):
        if release_doc.get(key) != binding:
            raise SlurpTopNAnalysisError(f"source quality read registration differs: {key}")
    legal_ids = _raw_legal_ids(raw.get("legal_intent_ids"))
    width = raw.get("max_candidates", 3)
    if (
        isinstance(width, bool)
        or not isinstance(width, int)
        or width < 1
        or (width > 3 and width > len(legal_ids))
    ):
        raise SlurpTopNAnalysisError(
            "raw max_candidates must fit the legal intent inventory"
        )
    rows = []
    for sample_id in full_ids:
        contact = verified_source.contacts_by_sample_id[sample_id]
        response = _map(contact["response"], f"raw response {sample_id!r}")
        rows.append(
            RawProposalRow(
                sample_id,
                str(contact["request_id"]),
                _raw_candidate_ids(
                    response.get("text"),
                    sample_id=sample_id,
                    legal_intent_ids=legal_ids,
                    max_candidates=width,
                ),
            )
        )
    rows = tuple(rows)
    reference_binding = _map(
        _map(spec.get("source_diagnostics"), "analysis.source_diagnostics").get("reference_source"),
        "raw reference source",
    )
    if dict(reference_binding) != release_doc.get("reference_source"):
        raise SlurpTopNAnalysisError("reference source differs from owner read registration")
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
    bootstrap = raw.get("bootstrap")
    if bootstrap is not None:
        settings = _map(bootstrap, "raw source bootstrap")
        for name, ids in populations.items():
            if not ids:
                continue
            ordered = primary_ids if name == "NEW500" else tuple(s for s in full_ids if s in ids)
            reports[name]["speaker_ci90_percent"] = _raw_uncertainty(
                rows, references, metadata, ordered, settings
            )
            for width_key, subgroup in reports[name]["by_observed_distinct_width"].items():
                member_ids = {
                    row.sample_id for row in rows
                    if len(set(row.candidate_ids)) == int(width_key)
                }
                subgroup["speaker_ci90_percent"] = _raw_uncertainty(
                    rows, references, metadata,
                    tuple(s for s in ordered if s in member_ids), settings
                )
    result = {
        "schema": "saea-slurp-raw-source-diagnostics-v1",
        "experiment_id": config.get("experiment_id"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"path": str(config_path.resolve()), "sha256": digest(config_path)},
        "source": {
            "attempt": {"path": str(attempt_path), "sha256": attempt_sha},
            "generation_plan": {"path": str(plan_path), "sha256": plan_sha},
            "raw_trace": {"path": str(trace_path), "sha256": trace_sha},
            "attempt_state": verified_source.attempt.get("state"),
            "expected_contacts": expected_contacts,
        },
        "source_quality_read_release": {
            "release_id": release["release_id"], "authorized": True,
            "registration": {"path": str(release_path), "sha256": release_sha},
        },
        "populations": {name: len(ids) for name, ids in populations.items()},
        "max_candidates": width,
        "stratum_field": field,
        "diagnostics": reports,
        "uncertainty": {
            "status": "speaker_cluster_bootstrap" if bootstrap is not None else "point_estimates_only",
            "settings": bootstrap,
            "interpretation": "Candidate coverage is potential, not final accuracy; observed width is uncalibrated.",
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


def _observed_width_reports(
    source_rows: Sequence[SourceCandidateRow],
    references: Sequence[ReferenceIntentRow],
    branches: Mapping[str, Sequence[BranchOutcomeRow]],
    *,
    candidate_width: int,
) -> dict[str, dict[str, object]]:
    """Aggregate descriptive subgroups by observed distinct candidate width."""
    if (
        isinstance(candidate_width, bool)
        or not isinstance(candidate_width, int)
        or not 1 <= candidate_width <= MAX_CANDIDATE_IDS
    ):
        raise SlurpTopNAnalysisError(
            "observed width reports require a positive candidate_width "
            "within the shared candidate bound"
        )
    groups: dict[int, list[SourceCandidateRow]] = {
        width: [] for width in range(1, candidate_width + 1)
    }
    for row in source_rows:
        observed = len(set(row.candidate_ids))
        if observed not in groups or observed > candidate_width:
            raise SlurpTopNAnalysisError(
                f"observed candidate width {observed} is outside configured width"
            )
        groups[observed].append(row)
    reports: dict[str, dict[str, object]] = {}
    for observed, members in groups.items():
        if not members:
            continue
        ids = {row.sample_id for row in members}
        report = aggregate_topn_diagnostics(
            members,
            _subset(references, ids),
            {name: _subset(rows, ids) for name, rows in branches.items()},
            candidate_width=observed,
        ).as_json()
        reports[str(observed)] = report
    return reports


def _run_native_system(
    config_path: Path,
    output: Path,
    config: Mapping[str, object],
    spec: Mapping[str, object],
    source_section: Mapping[str, object],
    source: Mapping[str, object],
    *,
    bundle_verifier,
    score_receipt_verifier,
    reference_loader,
    candidate_contract_loader,
):
    """Diagnose one native system whose Perception state is internal."""
    full_ids = _roster_ids(spec.get("full_roster"), "analysis.full_roster")
    primary_ids = _roster_ids(spec.get("roster"), "analysis.roster")
    if not set(primary_ids) <= set(full_ids):
        raise SlurpTopNAnalysisError("primary roster must be a subset of full roster")
    metadata = _metadata(spec.get("metadata"), set(full_ids))
    inputs = _map(spec.get("inputs"), "analysis.inputs")
    if set(inputs) != {"system"}:
        raise SlurpTopNAnalysisError(
            "native Perception diagnostics require exactly one system input"
        )
    system_input = _map(inputs["system"], "analysis.inputs.system")
    source_manifest = _map(source.get("manifest"), "native source manifest")
    input_manifest = _map(system_input.get("manifest"), "system manifest")
    source_path, source_sha = _pin(source_manifest, "native source manifest")
    input_path, input_sha = _pin(input_manifest, "system manifest")
    if source_path.resolve() != input_path.resolve() or source_sha != input_sha:
        raise SlurpTopNAnalysisError("native source and system input manifests differ")
    bundle = bundle_verifier(source_path)

    if system_input.get("score_source", "complete-score-receipt") != "complete-score-receipt":
        raise SlurpTopNAnalysisError("system must use a complete-score-receipt")
    receipt_path, receipt_sha = _pin(
        system_input.get("score_receipt"), "system score receipt"
    )
    receipt_binding = _map(system_input.get("score_receipt"), "system score receipt")
    cell_id = receipt_binding.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id:
        raise SlurpTopNAnalysisError("system score receipt cell_id is required")
    try:
        score_receipt = score_receipt_verifier(
            SavedScoreReceiptRef(
                cell_id=cell_id, path=receipt_path, sha256=receipt_sha
            ),
            bundle,
        )
    except Exception as error:
        raise SlurpTopNAnalysisError(
            f"system complete score receipt failed: {error}"
        ) from error

    reference_binding = _map(
        source_section.get("reference_source"), "reference_source"
    )
    legal_ids = _authoritative_candidate_ids(
        reference_binding, loader=candidate_contract_loader
    )
    source_rows, system_rows, native_source = _native_system_rows(
        source, bundle, full_ids, legal_ids=legal_ids
    )
    scorer_map = system_input.get("scorers", {})
    if scorer_map is None:
        scorer_map = {}
    if not isinstance(scorer_map, Mapping):
        raise SlurpTopNAnalysisError("system scorers must be a mapping")
    entity_correctness = _entity_correctness_from_verified_receipt(
        score_receipt,
        scorer=scorer_map.get("official", "slurp-slu-official"),
        expected_ids=set(full_ids),
    )
    system_rows = tuple(
        BranchOutcomeRow(
            row.sample_id,
            row.final_intent_id,
            row.refused,
            entity_correctness[row.sample_id],
            missing_final_intent=row.missing_final_intent,
        )
        for row in system_rows
    )
    references = _references(reference_binding, full_ids, loader=reference_loader)
    width = _source_candidate_width(source, distinct=True)
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
        branches = {"system": _subset(system_rows, ids)}
        try:
            report = aggregate_topn_diagnostics(
                src,
                refs,
                branches,
                candidate_width=width,
                allow_variable_width=True,
            ).as_json()
        except TopNDiagnosticError as error:
            raise SlurpTopNAnalysisError(
                f"{population} aggregation failed: {error}"
            ) from error
        strata: dict[str, set[str]] = {}
        for sample_id in ids:
            value = metadata[sample_id].get(field)
            if not isinstance(value, str) or not value:
                raise SlurpTopNAnalysisError(
                    f"metadata {field} missing for {sample_id!r}"
                )
            strata.setdefault(value, set()).add(sample_id)
        report["per_stratum"] = {
            key: aggregate_topn_diagnostics(
                _subset(src, members),
                _subset(refs, members),
                {"system": _subset(system_rows, members)},
                candidate_width=width,
                allow_variable_width=True,
            ).as_json()
            for key, members in sorted(strata.items())
        }
        report["candidate_width_semantics"] = (
            "maximum; actual width is the unpadded first-occurrence distinct "
            "system Perception set"
        )
        report["by_observed_distinct_width"] = _observed_width_reports(
            src, refs, branches, candidate_width=width
        )
        report["per_stratum_observed_distinct_width"] = {
            key: _observed_width_reports(
                _subset(src, members),
                _subset(refs, members),
                {"system": _subset(system_rows, members)},
                candidate_width=width,
            )
            for key, members in sorted(strata.items())
        }
        report["metric_semantics"] = {
            "branches.system.rescues": (
                "system final intent correct after system Perception rank one was wrong"
            ),
            "branches.system.harms": (
                "system final intent wrong after system Perception rank one was correct"
            ),
            "direct_vs_system_saves_harms": (
                "unavailable here; use score_compare_cli on the two complete official receipts"
            ),
        }
        reports[population] = report
    result = {
        "schema": "saea-slurp-topn-diagnostics-v1",
        "experiment_id": config.get("experiment_id"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"path": str(config_path.resolve()), "sha256": digest(config_path)},
        "source": {
            **source,
            "binding_name": _NATIVE_SOURCE_KEY,
            "manifest": {"path": str(source_path), "sha256": source_sha},
            **native_source,
        },
        "score_gate": {
            "system": {
                "path": str(receipt_path), "sha256": receipt_sha, "verified": True
            }
        },
        "populations": {name: len(ids) for name, ids in populations.items()},
        "stratum_field": field,
        "diagnostics": reports,
        "diagnostic_semantics": {
            "scope": "system-only internal Perception candidate diagnostics",
            "rank1_rescues_harms": "relative to system Perception rank one",
            "direct_vs_system_saves_harms": "score_compare_cli only",
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


def run(
    config_path, output, *, bundle_verifier=verify_bundle,
    score_receipt_verifier=verify_complete_score_receipt,
    reference_loader=load_slurp_split,
    candidate_contract_loader=build_slurp_candidate_contract_provider,
    state_loader=sealed_states_from_manifest,
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
            reference_loader=reference_loader,
        )
    source_section = _map(spec.get("source_diagnostics"), "analysis.source_diagnostics")
    native_source = source_section.get(_NATIVE_SOURCE_KEY)
    if native_source is not None:
        if any(
            source_section.get(key) is not None
            for key in ("shared_fixed_top3_source", "shared_distinct_source")
        ):
            raise SlurpTopNAnalysisError(
                "native and shared source bindings cannot be combined"
            )
        return _run_native_system(
            config_path,
            output,
            config,
            spec,
            source_section,
            _map(native_source, "native system Perception source"),
            bundle_verifier=bundle_verifier,
            score_receipt_verifier=score_receipt_verifier,
            reference_loader=reference_loader,
            candidate_contract_loader=candidate_contract_loader,
        )
    source_name, source, distinct_source = _select_source_binding(source_section)
    full_ids = _roster_ids(spec.get("full_roster"), "analysis.full_roster")
    primary_ids = _roster_ids(spec.get("roster"), "analysis.roster")
    if not set(primary_ids) <= set(full_ids):
        raise SlurpTopNAnalysisError("primary roster must be a subset of full roster")
    metadata = _metadata(spec.get("metadata"), set(full_ids))
    source_path, source_sha = _source_pin(source, distinct=distinct_source)
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
        source, source_bundle, full_ids, state_loader=state_loader, distinct=distinct_source
    )
    references = _references(
        _map(source_section.get("reference_source"), "reference_source"),
        full_ids, loader=reference_loader
    )
    branches = {}
    delivery_by_branch: dict[str, dict[str, Mapping[str, object]]] = {}
    for name, value in inputs.items():
        entity_correctness = None
        if distinct_source:
            binding = _map(value, f"analysis.inputs.{name}")
            scorer_map = binding.get("scorers", {})
            if scorer_map is None:
                scorer_map = {}
            if not isinstance(scorer_map, Mapping):
                raise SlurpTopNAnalysisError(f"{name} scorers must be a mapping")
            scorer = scorer_map.get("official", "slurp-slu-official")
            entity_correctness = _entity_correctness_from_verified_receipt(
                receipts[str(name)],
                scorer=scorer,
                expected_ids=set(full_ids),
            )
        delivery_rows: dict[str, Mapping[str, object]] = {}
        branches[str(name)] = _branch_rows(
            str(name), bundles[name], source_path, source_sha, source_states, full_ids,
            entity_correctness, delivery_rows,
        )
        delivery_by_branch[str(name)] = delivery_rows
    width = _source_candidate_width(source, distinct=distinct_source)
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
            report = aggregate_topn_diagnostics(
                src, refs, br, candidate_width=width,
                allow_variable_width=distinct_source,
            ).as_json()
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
                allow_variable_width=distinct_source,
            ).as_json()
            for key, members in sorted(strata.items())
        }
        report["metric_semantics"] = {
            "branches.*.out_of_shortlist_attempts": (
                "delivered_projection_only; derived from delivered final intent text"
            ),
            "raw_delivery_diagnostics": (
                "verified phase_sources.delivery_diagnostics and refusal_reason"
            ),
        }
        report["raw_delivery_diagnostics"] = {
            name: _raw_delivery_diagnostic_report(rows, ids)
            for name, rows in delivery_by_branch.items()
        }
        report["per_stratum_raw_delivery_diagnostics"] = {
            key: {
                name: _raw_delivery_diagnostic_report(rows, members)
                for name, rows in delivery_by_branch.items()
            }
            for key, members in sorted(strata.items())
        }
        if distinct_source:
            report["candidate_width_semantics"] = "maximum; retain the actual unpadded candidate set"
            report["by_observed_distinct_width"] = _observed_width_reports(
                src, refs, br, candidate_width=width
            )
            report["per_stratum_observed_distinct_width"] = {
                key: _observed_width_reports(
                    _subset(src, members), _subset(refs, members),
                    {name: _subset(rows, members) for name, rows in br.items()},
                    candidate_width=width,
                )
                for key, members in sorted(strata.items())
            }
            report["raw_delivery_diagnostics_by_observed_distinct_width"] = (
                _raw_delivery_reports_by_branch_and_width(
                    src, delivery_by_branch, ids
                )
            )
            report["per_stratum_raw_delivery_diagnostics_by_observed_distinct_width"] = {
                key: _raw_delivery_reports_by_branch_and_width(
                    _subset(src, members),
                    delivery_by_branch,
                    members,
                )
                for key, members in sorted(strata.items())
            }
        reports[population] = report
    source_output = {
        **source,
        "manifest": {"path": str(source_path), "sha256": source_sha},
    }
    if distinct_source:
        source_output["binding_name"] = source_name
    result = {
        "schema": "saea-slurp-topn-diagnostics-v1",
        "experiment_id": config.get("experiment_id"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"path": str(config_path.resolve()), "sha256": digest(config_path)},
        "source": source_output,
        "score_gate": {
            name: {"path": value["score_receipt"]["path"],
                   "sha256": value["score_receipt"]["sha256"], "verified": True}
            for name, value in inputs.items()
        },
        "populations": {name: len(ids) for name, ids in populations.items()},
        "stratum_field": field, "diagnostics": reports,
        "diagnostic_semantics": {
            "branches.*.out_of_shortlist_attempts": (
                "delivered_projection_only; derived from delivered final intent text"
            ),
            "raw_delivery_diagnostics": (
                "verified phase_sources.delivery_diagnostics and refusal_reason"
            ),
        },
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
