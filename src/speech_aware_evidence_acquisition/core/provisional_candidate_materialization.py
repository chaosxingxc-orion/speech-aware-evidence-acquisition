"""Materialize source-bound TRAIN proposals as provisional experience candidates.

This model-free preparation stage converts a finalized typed proposal bundle
into a separate artifact under ``DATA/provisional/experience-candidates``.
Every source identity is recovered from the hidden candidate bindings in the
exact prepared TRAIN contexts. Model output supplies only proposal content and
option labels. It cannot supply record IDs, source metadata, hashes, validation
status, or admission. The validation binding records proposal provenance; it
is not evaluation evidence and does not admit a record for runtime use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..rails.experience_memory import (
    Applicability,
    ExperienceMemoryError,
    ExperienceRecord,
    ExperienceSource,
    SourceRef,
    ValidationBinding,
)
from ..rails.experience_memory_sources import reward_link_hash_source_ref
from ..rails.hashing import content_hash
from ..rails.training_feedback_artifacts import (
    TrainingFeedbackArtifactError,
    build_training_feedback_artifact_validator,
)
from ..rails.training_proposal_context import (
    TrainingProposalContextError,
    build_training_proposal_contexts,
    training_proposal_context_preparation_inputs,
)
from .bundle import BundleError
from .bundle.verify import verify_bundle
from .preparation import (
    PreparationError,
    digest,
    hash_stable_file,
    load_artifact,
    prepare_artifact,
)
from .roster import (
    CONSTRUCTION_ROSTER_ROLE,
    RosterError,
    read_roster,
    verify_roster,
)

CONFIG_SCHEMA = "saea-provisional-candidate-materialization-config-v1"
OUTPUT_SCHEMA = "saea-provisional-experience-candidates-v1"
ARTIFACT_KIND = "provisional-experience-candidates"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_PROTOCOL_SCHEMA = "saea-training-proposal-protocol-binding-v1"
_DECISION_SCHEMA = "saea-provisional-candidate-materialization-decision-v1"
_EMPTY_TEXT_SHA256 = hashlib.sha256(b"").hexdigest()
_CONFIG_KEYS = frozenset(
    {
        "schema",
        "materialization_id",
        "max_candidates",
        "proposal_bundle",
        "prepared_contexts",
        "source_bindings",
        "materialization_decision",
        "proposal_protocol",
        "construction_roster",
    }
)


class MaterializationError(ValueError):
    """A proposal bundle or one of its source bindings is not authoritative."""


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise MaterializationError(f"{field} must be a lowercase SHA-256")
    return value


def _path_pin(value: object, field: str) -> tuple[Path, str]:
    if not isinstance(value, Mapping) or set(value) != {"path", "sha256"}:
        raise MaterializationError(f"{field} must be an exact path/SHA-256 pin")
    raw_path = value.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise MaterializationError(f"{field} path must be nonempty text")
    path = Path(raw_path)
    if not path.is_absolute():
        raise MaterializationError(f"{field} path must be absolute")
    return path, _sha(value.get("sha256"), f"{field} SHA-256")


def _stable_pinned_bytes(value: object, field: str) -> tuple[Path, bytes, str, tuple[int, int, int]]:
    path, expected = _path_pin(value, field)
    try:
        _, actual, fingerprint = hash_stable_file(path, field)
        raw = path.read_bytes()
    except (OSError, PreparationError) as error:
        raise MaterializationError(f"cannot read {field}: {error}") from error
    if actual != expected or hashlib.sha256(raw).hexdigest() != expected:
        raise MaterializationError(f"{field} hash mismatch")
    return path, raw, actual, fingerprint


def _assert_unchanged(path: Path, expected: str, fingerprint: tuple[int, int, int], field: str) -> None:
    try:
        _, actual, after = hash_stable_file(path, field + " after materialization")
    except PreparationError as error:
        raise MaterializationError(f"cannot reverify {field}: {error}") from error
    if actual != expected or after != fingerprint:
        raise MaterializationError(f"{field} changed during materialization")


def _data_path(data_root: Path, relpath: object, field: str) -> Path:
    if (
        not isinstance(relpath, str)
        or not relpath
        or "\\" in relpath
        or ":" in relpath
        or any(part in {"", ".", ".."} for part in relpath.split("/"))
    ):
        raise MaterializationError(f"{field} must be a canonical DATA-relative path")
    root = Path(data_root).resolve()
    path = (root / relpath).resolve()
    if not path.is_relative_to(root):
        raise MaterializationError(f"{field} escapes DATA")
    return path


def _load_config(path: Path, expected_sha256: str) -> tuple[dict[str, object], str, tuple[int, int, int]]:
    expected = _sha(expected_sha256, "materialization config SHA-256")
    try:
        _, actual, fingerprint = hash_stable_file(path, "materialization config")
        raw = Path(path).read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, PreparationError) as error:
        raise MaterializationError(f"cannot read materialization config: {error}") from error
    if actual != expected or hashlib.sha256(raw).hexdigest() != expected:
        raise MaterializationError("materialization config hash mismatch")
    from .provisional_candidate_consolidation import CONFIG_SCHEMA as CONSOLIDATION_CONFIG_SCHEMA

    from .system_semantic_memory import CONFIG_SCHEMA as SEMANTIC_CONFIG_SCHEMA
    schemas = {
        SEMANTIC_CONFIG_SCHEMA: {
            "schema", "materialization_id", "max_candidates", "batch_manifest", "batch_repo_root",
        },
        CONFIG_SCHEMA: _CONFIG_KEYS,
        CONSOLIDATION_CONFIG_SCHEMA: {
            "schema", "materialization_id", "memory_id", "max_candidates",
            "initial_materialization", "rounds",
        },
    }
    if (not isinstance(value, dict) or not isinstance(value.get("schema"), str)
            or value["schema"] not in schemas):
        raise MaterializationError("materialization config schema mismatch")
    if set(value) != schemas[value["schema"]]:
        raise MaterializationError("materialization config has missing or unknown fields")
    materialization_id = value.get("materialization_id")
    if not isinstance(materialization_id, str) or _SAFE_ID.fullmatch(materialization_id) is None:
        raise MaterializationError("materialization_id is not a safe artifact identity")
    maximum = value.get("max_candidates")
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 0:
        raise MaterializationError("max_candidates must be a nonnegative integer")
    return value, actual, fingerprint


def _load_json_pin(value: object, field: str) -> tuple[object, tuple[Path, str, tuple[int, int, int]]]:
    path, raw, actual, fingerprint = _stable_pinned_bytes(value, field)
    try:
        document = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise MaterializationError(f"{field} is not valid JSON: {error}") from error
    return document, (path, actual, fingerprint)


def _validate_protocol_binding(
    value: object,
    *,
    manifest: Mapping[str, object],
    construction_sha256: str,
    prepared_contexts_sha256: str,
) -> None:
    keys = {
        "schema",
        "proposal_run_id",
        "runtime_protocol_hash",
        "construction_roster_sha256",
        "prepared_contexts_sha256",
    }
    if not isinstance(value, Mapping) or set(value) != keys:
        raise MaterializationError("proposal protocol binding has wrong fields")
    runtime_protocol = _sha(
        manifest.get("protocol_hash"), "verified proposal runtime protocol hash"
    )
    if (
        value.get("schema") != _PROTOCOL_SCHEMA
        or value.get("proposal_run_id") != manifest.get("run_id")
        or value.get("runtime_protocol_hash") != runtime_protocol
        or value.get("construction_roster_sha256") != construction_sha256
        or value.get("prepared_contexts_sha256") != prepared_contexts_sha256
    ):
        raise MaterializationError(
            "proposal protocol binding does not identify the verified proposal inputs"
        )


def _validate_decision_binding(
    value: object,
    *,
    bundle_sha256: str,
    protocol_sha256: str,
    construction_sha256: str,
) -> None:
    keys = {
        "schema",
        "action",
        "source_bundle_manifest_sha256",
        "proposal_protocol_sha256",
        "construction_roster_sha256",
        "selection",
        "admission",
    }
    if not isinstance(value, Mapping) or set(value) != keys:
        raise MaterializationError("materialization decision binding has wrong fields")
    if (
        value.get("schema") != _DECISION_SCHEMA
        or value.get("action") != "materialize-all-provisionally"
        or value.get("source_bundle_manifest_sha256") != bundle_sha256
        or value.get("proposal_protocol_sha256") != protocol_sha256
        or value.get("construction_roster_sha256") != construction_sha256
        or value.get("selection") != "none"
        or value.get("admission") != "none"
    ):
        raise MaterializationError(
            "materialization decision must bind this bundle and materialize all "
            "proposals provisionally without selection or admission"
        )


def _load_prepared_contexts(
    config: Mapping[str, object], data_root: Path, source_bindings: object
) -> tuple[dict[str, object], tuple[Path, str, tuple[int, int, int]]]:
    pin = config.get("prepared_contexts")
    if not isinstance(pin, Mapping) or set(pin) != {
        "data_relpath",
        "sha256",
        "output_sha256",
    }:
        raise MaterializationError("prepared_contexts pin has wrong fields")
    path = _data_path(data_root, pin.get("data_relpath"), "prepared_contexts.data_relpath")
    expected_file = _sha(pin.get("sha256"), "prepared contexts file SHA-256")
    expected_output = _sha(pin.get("output_sha256"), "prepared contexts output SHA-256")
    try:
        _, actual_file, fingerprint = hash_stable_file(path, "prepared TRAIN contexts")
        if actual_file != expected_file:
            raise MaterializationError("prepared TRAIN contexts file hash mismatch")
        rebuilt = build_training_proposal_contexts(source_bindings)
        inputs = training_proposal_context_preparation_inputs(rebuilt)
        output = load_artifact(
            path,
            expected_sha256=expected_file,
            kind="training-proposal-contexts",
            inputs=inputs,
        )
    except (TrainingProposalContextError, PreparationError, OSError, TypeError, ValueError) as error:
        raise MaterializationError(f"cannot verify prepared TRAIN contexts: {error}") from error
    if output != rebuilt or digest(output) != expected_output:
        raise MaterializationError("prepared TRAIN contexts differ from reconstructed source authority")
    if not isinstance(output, dict):
        raise MaterializationError("prepared TRAIN contexts output must be an object")
    return output, (path, expected_file, fingerprint)


def _validate_candidate_delivery(value: object) -> None:
    keys = {
        "kind",
        "delivered_solver",
        "derived_request_id",
        "response_sha256",
        "response_text_sha256",
    }
    request_suffix = "/delivery/native-abstention-v1"
    if not isinstance(value, Mapping) or set(value) != keys:
        raise MaterializationError("prepared candidate delivery is malformed")
    derived_request_id = value.get("derived_request_id")
    if (
        value.get("kind") != "abstention"
        or value.get("delivered_solver") is not False
        or not isinstance(derived_request_id, str)
        or len(derived_request_id) <= len(request_suffix)
        or not derived_request_id.endswith(request_suffix)
        or value.get("response_text_sha256") != _EMPTY_TEXT_SHA256
    ):
        raise MaterializationError("prepared candidate delivery is not a bound abstention")
    _sha(value.get("response_sha256"), "candidate abstention response SHA-256")


def _context_index(output: Mapping[str, object]) -> tuple[tuple[str, ...], dict[str, Mapping[str, object]]]:
    if (
        output.get("schema") != "saea-training-proposal-contexts-v2"
        or output.get("status") != "source-verified"
        or output.get("role") != "training-feedback-proposal"
    ):
        raise MaterializationError("prepared proposal document has wrong source authority")
    contexts = output.get("contexts")
    if isinstance(contexts, (str, bytes)) or not isinstance(contexts, Sequence):
        raise MaterializationError("prepared proposal contexts are missing")
    ordered: list[str] = []
    by_sample: dict[str, Mapping[str, object]] = {}
    for context in contexts:
        if not isinstance(context, Mapping):
            raise MaterializationError("prepared proposal context is malformed")
        sample_id = context.get("source_sample_id")
        if not isinstance(sample_id, str) or not sample_id or sample_id in by_sample:
            raise MaterializationError("prepared proposal context has duplicate sample IDs")
        bindings = context.get("candidate_bindings")
        if isinstance(bindings, (str, bytes)) or not isinstance(bindings, Sequence) or not bindings:
            raise MaterializationError("prepared proposal context has no candidate bindings")
        labels: set[str] = set()
        candidate_ids: set[str] = set()
        for binding in bindings:
            base_fields = {
                "label",
                "candidate_id",
                "reward_link_sha256",
                "source",
            }
            if not isinstance(binding, Mapping) or set(binding) not in (
                base_fields,
                base_fields | {"delivery"},
            ):
                raise MaterializationError("prepared candidate binding is malformed")
            if "delivery" in binding:
                _validate_candidate_delivery(binding["delivery"])
            label = binding.get("label")
            candidate_id = binding.get("candidate_id")
            source = binding.get("source")
            if (
                not isinstance(label, str)
                or not label
                or label in labels
                or not isinstance(candidate_id, str)
                or not candidate_id
                or candidate_id in candidate_ids
            ):
                raise MaterializationError("prepared candidate labels and identities must be unique")
            labels.add(label)
            candidate_ids.add(candidate_id)
            _sha(binding.get("reward_link_sha256"), "reward-link SHA-256")
            try:
                source_value = ExperienceSource.from_json(source)
            except (ExperienceMemoryError, TypeError, ValueError) as error:
                raise MaterializationError(f"candidate source is malformed: {error}") from error
            if source_value.partition_role != "train" or source_value.source_sample_id != sample_id:
                raise MaterializationError("prepared proposal context is not TRAIN-only")
        ordered.append(sample_id)
        by_sample[sample_id] = context
    if not ordered:
        raise MaterializationError("prepared proposal contexts are empty")
    return tuple(ordered), by_sample


def _source_ref(binding: Mapping[str, object]) -> SourceRef:
    return reward_link_hash_source_ref(str(binding["reward_link_sha256"]))


def _record(
    *,
    proposal: Mapping[str, object],
    context: Mapping[str, object],
    proposal_index: int,
    config_sha256: str,
    bundle_sha256: str,
    construction_sha256: str,
    decision_sha256: str,
    protocol_sha256: str,
    result_sha256: str,
) -> ExperienceRecord:
    bindings = context["candidate_bindings"]
    assert isinstance(bindings, Sequence)
    by_label = {str(binding["label"]): binding for binding in bindings}
    try:
        primary = by_label[str(proposal["primary_option"])]
        supporting = tuple(by_label[str(label)] for label in proposal["supporting_options"])
        contradicting = tuple(
            by_label[str(label)] for label in proposal["contradicting_options"]
        )
        source = ExperienceSource.from_json(primary["source"])
        applicability = Applicability.from_json(proposal["applicability"])
    except (ExperienceMemoryError, KeyError, TypeError, ValueError) as error:
        raise MaterializationError(f"proposal option/source mapping is invalid: {error}") from error
    record_id = "provisional-" + content_hash(
        {
            "materialization_config_sha256": config_sha256,
            "proposal_bundle_sha256": bundle_sha256,
            "source_sample_id": context["source_sample_id"],
            "proposal_index": proposal_index,
        }
    )
    try:
        return ExperienceRecord.create(
            record_id=record_id,
            revision=1,
            kind=str(proposal["kind"]),
            train_construction_sha256=construction_sha256,
            source=source,
            applicability=applicability,
            diagnosis=str(proposal["diagnosis"]),
            guidance=str(proposal["guidance"]),
            limitations=proposal["limitations"],
            supporting_source_refs=tuple(_source_ref(binding) for binding in supporting),
            contradicting_source_refs=tuple(
                _source_ref(binding) for binding in contradicting
            ),
            validation=ValidationBinding(
                status="provisional",
                decision_sha256=decision_sha256,
                protocol_sha256=protocol_sha256,
                roster_sha256=construction_sha256,
                result_sha256=result_sha256,
            ),
        )
    except (ExperienceMemoryError, TypeError, ValueError) as error:
        raise MaterializationError(f"cannot construct provisional experience record: {error}") from error


def _produce(
    *,
    config: Mapping[str, object],
    config_sha256: str,
    bundle_sha256: str,
    contexts: Mapping[str, Mapping[str, object]],
    rows: Sequence[Mapping[str, object]],
    decision_sha256: str,
    protocol_sha256: str,
    construction_sha256: str,
) -> dict[str, object]:
    samples = []
    total = 0
    for row in rows:
        sample_id = str(row["sample_id"])
        try:
            content = json.loads(str(row["artifact_content"]))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise MaterializationError(f"canonical typed proposal is invalid JSON: {error}") from error
        proposals = content.get("proposals") if isinstance(content, Mapping) else None
        if isinstance(proposals, (str, bytes)) or not isinstance(proposals, Sequence):
            raise MaterializationError("canonical typed proposal has no proposal sequence")
        result_sha256 = _sha(row.get("artifact_content_sha256"), "sealed proposal result SHA-256")
        records = [
            _record(
                proposal=proposal,
                context=contexts[sample_id],
                proposal_index=index,
                config_sha256=config_sha256,
                bundle_sha256=bundle_sha256,
                construction_sha256=construction_sha256,
                decision_sha256=decision_sha256,
                protocol_sha256=protocol_sha256,
                result_sha256=result_sha256,
            ).as_json()
            for index, proposal in enumerate(proposals)
        ]
        total += len(records)
        samples.append(
            {
                "source_sample_id": sample_id,
                "proposal_result_sha256": result_sha256,
                "records": records,
            }
        )
    if total > config["max_candidates"]:
        raise MaterializationError(
            "proposal bundle exceeds max_candidates; refusing selection or truncation"
        )
    return {
        "schema": OUTPUT_SCHEMA,
        "status": "provisional",
        "materialization_id": config["materialization_id"],
        "interpretation": (
            "Proposal provenance only; these provisional candidates are not evaluation "
            "evidence and are not admitted runtime memory."
        ),
        "provenance": {
            "materialization_config_sha256": config_sha256,
            "proposal_bundle_manifest_sha256": bundle_sha256,
            "proposal_outputs_sha256": config["proposal_bundle_outputs_sha256"]
            if "proposal_bundle_outputs_sha256" in config
            else None,
            "prepared_contexts_sha256": config["prepared_contexts"]["sha256"],
            "prepared_contexts_output_sha256": config["prepared_contexts"][
                "output_sha256"
            ],
            "source_bindings_sha256": config["source_bindings"]["sha256"],
            "materialization_decision_sha256": decision_sha256,
            "proposal_protocol_sha256": protocol_sha256,
            "construction_roster_sha256": construction_sha256,
        },
        "samples": samples,
    }


def prepare_provisional_candidates(
    *, config_path: Path, expected_config_sha256: str, data_root: Path
) -> dict[str, object]:
    """Verify every authority and persist one immutable provisional artifact."""

    config_path = Path(config_path).resolve()
    data_root = Path(data_root).resolve()
    config, config_sha, config_fingerprint = _load_config(
        config_path, expected_config_sha256
    )
    from .system_semantic_memory import CONFIG_SCHEMA as SEMANTIC_CONFIG_SCHEMA, prepare_system_semantic_memory
    if config["schema"] == SEMANTIC_CONFIG_SCHEMA:
        return prepare_system_semantic_memory(
            config_path=config_path, expected_config_sha256=config_sha, data_root=data_root)
    if config["schema"] != CONFIG_SCHEMA:
        from .provisional_candidate_consolidation import prepare_consolidated_candidates

        return prepare_consolidated_candidates(
            config_path=config_path, expected_config_sha256=config_sha, data_root=data_root,
        )
    manifest_path, _raw, bundle_sha, bundle_fingerprint = _stable_pinned_bytes(
        config["proposal_bundle"], "proposal bundle manifest"
    )
    try:
        bundle = verify_bundle(manifest_path)
    except (BundleError, OSError, ValueError) as error:
        raise MaterializationError(f"proposal bundle verification failed: {error}") from error
    manifest = bundle.manifest
    artifact_result = manifest.get("artifact_result")
    if (
        manifest.get("status") != "COMPLETED"
        or bundle.attempt_state != "FINALIZED"
        or manifest.get("result_kind") != "artifact"
        or not isinstance(artifact_result, Mapping)
        or artifact_result.get("schema") != "saea-artifact-result-binding-v3"
        or artifact_result.get("role") != "training-feedback-proposal"
    ):
        raise MaterializationError(
            "provisional candidates require a COMPLETED, FINALIZED typed proposal bundle"
        )
    contract = artifact_result.get("content_contract")
    if not isinstance(contract, Mapping) or contract.get("prepared_contexts") != config[
        "prepared_contexts"
    ]:
        raise MaterializationError("bundle and materialization prepared-context pins differ")

    source_bindings, source_guard = _load_json_pin(
        config["source_bindings"], "source bindings"
    )
    prepared, prepared_guard = _load_prepared_contexts(config, data_root, source_bindings)
    ordered_context_ids, contexts = _context_index(prepared)

    roster_path, _roster_raw, roster_sha, roster_fingerprint = _stable_pinned_bytes(
        config["construction_roster"], "construction roster"
    )
    try:
        roster = read_roster(roster_path)
        verify_roster(roster)
    except (OSError, ValueError, RosterError) as error:
        raise MaterializationError(f"cannot verify construction roster: {error}") from error
    if roster.get("roster_role") != CONSTRUCTION_ROSTER_ROLE:
        raise MaterializationError("materialization requires a construction roster")
    roster_ids = tuple(item["sample_id"] for item in roster["items"])
    construction_sha = _sha(
        prepared.get("construction_roster_sha256"), "TRAIN construction roster SHA-256"
    )
    roster_binding = artifact_result.get("construction_roster")
    if (
        construction_sha != roster_sha
        or not isinstance(roster_binding, Mapping)
        or roster_binding.get("sha256") != roster_sha
    ):
        raise MaterializationError("construction roster pins do not agree")
    split = manifest.get("split")
    if (
        not isinstance(split, Mapping)
        or split.get("role") != "discovery"
        or split.get("carrier_lock_key") != roster.get("carrier_lock_key")
    ):
        raise MaterializationError("proposal bundle is not the construction TRAIN cohort")

    rows = tuple(bundle.outputs_rows)
    row_ids = [row.get("sample_id") for row in rows]
    if len(row_ids) != len(set(row_ids)):
        raise MaterializationError("proposal outputs contain duplicate sample IDs")
    if (
        set(row_ids) != set(roster_ids)
        or set(row_ids) != set(ordered_context_ids)
        or set(row_ids) != set(bundle.split_ids)
        or len(row_ids) != len(roster_ids)
    ):
        raise MaterializationError("proposal outputs do not cover the exact construction roster")

    try:
        validator = build_training_feedback_artifact_validator(contract, data_root=data_root)
        for row in rows:
            sample_id = str(row.get("sample_id"))
            canonical = validator.canonicalize(str(row.get("text")), sample_id=sample_id)
            if (
                row.get("artifact_role") != "training-feedback-proposal"
                or row.get("artifact_content") != canonical
                or row.get("artifact_content_sha256")
                != hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                or row.get("artifact_source_sha256") != validator.source_sha256
            ):
                raise MaterializationError(
                    "proposal output differs from its canonical typed proposal"
                )
    except TrainingFeedbackArtifactError as error:
        raise MaterializationError(f"canonical typed proposal is invalid: {error}") from error

    decision, decision_guard = _load_json_pin(
        config["materialization_decision"], "materialization decision"
    )
    protocol, protocol_guard = _load_json_pin(
        config["proposal_protocol"], "proposal protocol"
    )
    decision_sha = config["materialization_decision"]["sha256"]
    protocol_sha = config["proposal_protocol"]["sha256"]
    _validate_protocol_binding(
        protocol,
        manifest=manifest,
        construction_sha256=construction_sha,
        prepared_contexts_sha256=config["prepared_contexts"]["sha256"],
    )
    _validate_decision_binding(
        decision,
        bundle_sha256=bundle_sha,
        protocol_sha256=protocol_sha,
        construction_sha256=construction_sha,
    )
    outputs_meta = manifest.get("outputs")
    if not isinstance(outputs_meta, Mapping):
        raise MaterializationError("proposal bundle lacks sealed outputs provenance")
    config_with_outputs = dict(config)
    config_with_outputs["proposal_bundle_outputs_sha256"] = _sha(
        outputs_meta.get("sha256"), "proposal outputs SHA-256"
    )
    inputs = {
        "materialization_config_sha256": config_sha,
        "proposal_bundle_manifest_sha256": bundle_sha,
        "proposal_outputs_sha256": config_with_outputs[
            "proposal_bundle_outputs_sha256"
        ],
        "prepared_contexts_sha256": config["prepared_contexts"]["sha256"],
        "prepared_contexts_output_sha256": config["prepared_contexts"][
            "output_sha256"
        ],
        "source_bindings_sha256": config["source_bindings"]["sha256"],
        "materialization_decision_sha256": decision_sha,
        "proposal_protocol_sha256": protocol_sha,
        "construction_roster_sha256": construction_sha,
        "implementation_sha256": hash_stable_file(
            Path(__file__), "candidate materialization implementation"
        )[1],
    }
    output_path = (
        data_root
        / "provisional"
        / "experience-candidates"
        / f"{config['materialization_id']}.json"
    )
    guards = (
        (config_path, config_sha, config_fingerprint, "materialization config"),
        (manifest_path, bundle_sha, bundle_fingerprint, "proposal bundle manifest"),
        (roster_path, roster_sha, roster_fingerprint, "construction roster"),
        (*prepared_guard, "prepared contexts"),
        (*source_guard, "source bindings"),
        (*decision_guard, "materialization decision"),
        (*protocol_guard, "proposal protocol"),
    )
    for path, expected, fingerprint, label in guards:
        _assert_unchanged(path, expected, fingerprint, label)
    try:
        receipt = prepare_artifact(
            output_path,
            kind=ARTIFACT_KIND,
            inputs=inputs,
            producer=lambda: _produce(
                config=config_with_outputs,
                config_sha256=config_sha,
                bundle_sha256=bundle_sha,
                contexts=contexts,
                rows=rows,
                decision_sha256=decision_sha,
                protocol_sha256=protocol_sha,
                construction_sha256=construction_sha,
            ),
            contact_class="model-free",
        )
    except (PreparationError, OSError, TypeError, ValueError) as error:
        if isinstance(error, MaterializationError):
            raise
        raise MaterializationError(f"cannot persist provisional candidates: {error}") from error

    for path, expected, fingerprint, label in guards:
        _assert_unchanged(path, expected, fingerprint, label)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="saea-materialize-provisional-candidates",
        description=(
            "Verify one finalized typed TRAIN proposal bundle and materialize its "
            "source-bound records as a model-free provisional artifact."
        ),
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--data-root", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    receipt = prepare_provisional_candidates(
        config_path=args.config,
        expected_config_sha256=args.config_sha256,
        data_root=args.data_root,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
