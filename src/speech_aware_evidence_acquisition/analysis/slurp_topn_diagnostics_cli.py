"""Config-driven source-bound SLURP Top-N diagnostics.

This companion to score_compare_cli verifies sealed bundles and complete score
receipts before delegating all diagnostic counting to the pure aggregator. It
never scores or infers a reference from a prediction. Raw-source uncertainty
uses the existing speaker-cluster resampling function when explicitly configured.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..core.bundle.verify import verify_bundle
from ..core.bundle.raw_contact_source import (
    RawContactSourceError,
    _load_verified_trace,
    verify_aborted_contact_source,
)
from ..core.roster import read_roster
from ..core.scoring_receipt import SavedScoreReceiptRef, verify_complete_score_receipt
from ..data.lock import load_lock
from ..data.slurp import load_slurp_split
from ..data.splits import prefixed, split_identity_hash
from ..rails.phase_material import sealed_states_from_manifest
from ..rails.slurp_intent_hypotheses import parse_slurp_intent_hypothesis_state
from ..reproduction.slurp_scoring import parse_slu_response
from ..reproduction.probe_split import load_verified_probe_split
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
                or not 1 <= raw_range[0] <= raw_range[1] <= 3
            ):
                raise SlurpTopNAnalysisError(
                    "distinct source candidate_count_range must be [1..3, low <= high]"
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
            + (" from 1 through 3 for a distinct source" if distinct else "")
        )
    if distinct and raw_width > 3:
        raise SlurpTopNAnalysisError(
            "candidate_count must be a positive integer from 1 through 3 for a distinct source"
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


def _source_rows(binding, bundle, full_ids, *, state_loader, distinct=False):
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
    width = _source_candidate_width(binding, distinct=distinct)
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


def _branch_rows(
    name, bundle, source_path, source_sha, source_states, full_ids,
    entity_correctness: Mapping[str, bool | None] | None = None,
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
        outcomes.append(
            BranchOutcomeRow(
                sample_id, final_intent, refusal is not None,
                None if entity_correctness is None else entity_correctness.get(sample_id),
            )
        )
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
    width = raw.get("max_candidates", 3)
    if isinstance(width, bool) or not isinstance(width, int) or not 1 <= width <= 3:
        raise SlurpTopNAnalysisError("raw max_candidates must be an integer from 1 through 3")
    legal_ids = _raw_legal_ids(raw.get("legal_intent_ids"))
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
    if isinstance(candidate_width, bool) or not isinstance(candidate_width, int) or not 1 <= candidate_width <= 3:
        raise SlurpTopNAnalysisError("observed width reports require candidate_width from 1 through 3")
    groups: dict[int, list[SourceCandidateRow]] = {width: [] for width in (1, 2, 3)}
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
            reference_loader=reference_loader,
        )
    source_section = _map(spec.get("source_diagnostics"), "analysis.source_diagnostics")
    source_name, source, distinct_source = _select_source_binding(source_section)
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
        source, source_bundle, full_ids, state_loader=state_loader, distinct=distinct_source
    )
    references = _references(
        _map(source_section.get("reference_source"), "reference_source"),
        full_ids, loader=reference_loader
    )
    branches = {}
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
        branches[str(name)] = _branch_rows(
            str(name), bundles[name], source_path, source_sha, source_states, full_ids,
            entity_correctness,
        )
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
        if distinct_source:
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
