"""Config-driven source-bound SLURP Top-N diagnostics.

This companion to score_compare_cli verifies sealed bundles and complete score
receipts before delegating all diagnostic counting to the pure aggregator. It
never scores, resamples, or infers a reference from a prediction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

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
