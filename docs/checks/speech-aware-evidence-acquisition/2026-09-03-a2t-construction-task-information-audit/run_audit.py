"""Reproduce the construction-task and retrieval-information audit."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[4]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_construction_task_information_audit import (  # noqa: E402
    audit_construction_task_information,
)
from speech_aware_evidence_acquisition.analysis.a2t_label_candidate_reduction import (  # noqa: E402
    analyze_label_candidate_reduction,
)
from speech_aware_evidence_acquisition.analysis.a2t_grouped_candidate_validation import (  # noqa: E402
    analyze_grouped_candidate_validation,
)
from speech_aware_evidence_acquisition.analysis.a2t_observation_text_ablation import (  # noqa: E402
    analyze_observation_text_ablation,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    load_tool_registry,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.action_family_contracts import (  # noqa: E402
    build_action_family_corpus,
    split_construction_validation,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)


PARTITION_SEED = 20260807
PARTITION_IDENTITY = "4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90"
VALIDATION_SEED = 20260903
VALIDATION_FRACTION = 0.20
K_GRID = (1, 3, 5, 8, 16, 32, 64, 100, 152)
TIER_K_GRID = (5, 16, 32, 64)
_DIALOGUE_RELATIVE_PATH = Path("public/tier7_multiturn_data/tier7_multiturn.json")
_ASCII_TRANSLATION = {
    0x00B0: " degrees",
    0x2011: "-",
    0x2013: "-",
    0x2014: " -- ",
    0x2018: "'",
    0x201D: '"',
    0x2026: "...",
}
_METRIC_FIELDS = (
    "sample_count",
    "requested_k",
    "effective_k",
    "required_item_recall",
    "full_set_coverage",
    "precision",
    "mean_distractor_burden",
    "positive_score_required_item_recall",
    "positive_score_full_set_coverage",
    "mean_zero_score_fallback_count",
    "maximum_decision_space_reduction_bits",
)
_SOURCE_RELPATHS = (
    "src/speech_aware_evidence_acquisition/analysis/a2t_construction_task_information_audit.py",
    "src/speech_aware_evidence_acquisition/analysis/a2t_label_candidate_reduction.py",
    "src/speech_aware_evidence_acquisition/analysis/a2t_grouped_candidate_validation.py",
    "src/speech_aware_evidence_acquisition/analysis/a2t_observation_text_ablation.py",
    "src/speech_aware_evidence_acquisition/analysis/a2t_lexical_ceiling.py",
    "src/speech_aware_evidence_acquisition/rails/action_family_contracts.py",
    "src/speech_aware_evidence_acquisition/rails/knowledge_build_a2t.py",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(value: Mapping[str, object]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")
    return _sha256_bytes(payload)


def _translate_dialogue_text(value: str) -> tuple[str, dict[str, int]]:
    """Translate the source's closed punctuation inventory to English ASCII."""

    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("complete-dialogue source must contain non-empty text")
    observed = Counter(ord(character) for character in value if not character.isascii())
    unknown = sorted(set(observed) - set(_ASCII_TRANSLATION))
    if unknown:
        names = ", ".join(f"U+{codepoint:04X}" for codepoint in unknown)
        raise RuntimeError(
            f"complete-dialogue source has unregistered non-ASCII: {names}"
        )
    translated = " ".join(value.translate(_ASCII_TRANSLATION).split())
    if not translated.isascii():
        raise RuntimeError("complete-dialogue translation did not produce ASCII")
    return translated, {
        f"U+{codepoint:04X}": observed[codepoint] for codepoint in sorted(observed)
    }


def _humanize_identifier(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value).replace("_", " ")
    return " ".join(spaced.casefold().split())


def _public_registry_retrieval_keys(
    registry: Sequence[Mapping[str, object]],
) -> dict[str, str]:
    """Build value-free English retrieval keys from public tool metadata."""

    result: dict[str, str] = {}
    for row in registry:
        tool_name = row.get("tool_name")
        domain = row.get("domain")
        category = row.get("category")
        description = row.get("description")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (tool_name, domain, category, description)
        ):
            raise RuntimeError("registry semantic retrieval fields must be non-empty")
        assert isinstance(tool_name, str)
        assert isinstance(domain, str)
        assert isinstance(category, str)
        assert isinstance(description, str)
        if tool_name in result:
            raise RuntimeError("registry tool names must be unique")
        text = (
            f"Tool {_humanize_identifier(tool_name)}. "
            f"Domain {_humanize_identifier(domain)}. "
            f"Category {_humanize_identifier(category)}. "
            f"{description.strip()}"
        )
        if not text.isascii():
            raise RuntimeError("public registry retrieval keys must be ASCII English")
        result[tool_name] = text
    if not result:
        raise RuntimeError("registry must contain at least one public tool key")
    return result


def _project_metrics(
    metrics: Mapping[str, Mapping[str, object]],
    *,
    k_grid: Sequence[int] | None = None,
) -> dict[str, dict[str, object]]:
    selected = tuple(int(key) for key in metrics) if k_grid is None else tuple(k_grid)
    return {
        str(k): {field: metrics[str(k)][field] for field in _METRIC_FIELDS}
        for k in selected
    }


def _source_hashes(repo: Path) -> dict[str, str]:
    paths = (
        *_SOURCE_RELPATHS,
        str(Path(__file__).resolve().relative_to(repo)).replace("\\", "/"),
    )
    return {
        relpath: _sha256_bytes((repo / relpath).read_bytes())
        for relpath in sorted(paths)
    }


def _load_dialogue_overrides(
    *,
    manifest_path: Path,
    construction_rows: Sequence[object],
) -> tuple[dict[str, str], dict[str, object]]:
    raw_bytes = manifest_path.read_bytes()
    payload = json.loads(raw_bytes.decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError("tier-7 manifest must be a list")
    required_by_query_idx = {
        int(row.query_idx): str(row.unit_id)
        for row in construction_rows
        if row.tier == "tier7_multiturn"
    }
    translated_by_query_idx: dict[int, str] = {}
    raw_by_unit_id: dict[str, str] = {}
    replacement_counts: Counter[str] = Counter()
    for entry in payload:
        if not isinstance(entry, Mapping):
            raise RuntimeError("tier-7 manifest contains a malformed entry")
        query_idx = entry.get("query_idx")
        if type(query_idx) is not int or query_idx not in required_by_query_idx:
            continue
        source_text = entry.get("query")
        if not isinstance(source_text, str):
            raise RuntimeError("tier-7 construction entry lacks complete dialogue text")
        translated, counts = _translate_dialogue_text(source_text)
        prior = translated_by_query_idx.setdefault(query_idx, translated)
        if prior != translated:
            raise RuntimeError("complete dialogue drifts within a query block")
        unit_id = required_by_query_idx[query_idx]
        raw_prior = raw_by_unit_id.setdefault(unit_id, source_text)
        if raw_prior != source_text:
            raise RuntimeError("raw complete dialogue drifts within a query block")
        replacement_counts.update(counts)
    if set(translated_by_query_idx) != set(required_by_query_idx):
        raise RuntimeError(
            "complete dialogue mapping does not cover construction tier 7"
        )
    overrides = {
        required_by_query_idx[query_idx]: translated_by_query_idx[query_idx]
        for query_idx in sorted(required_by_query_idx)
    }
    raw_identity = _canonical_sha256(
        {unit_id: raw_by_unit_id[unit_id] for unit_id in sorted(raw_by_unit_id)}
    )
    return overrides, {
        "manifest_sha256": _sha256_bytes(raw_bytes),
        "selected_raw_text_identity_sha256": raw_identity,
        "selected_unit_count": len(overrides),
        "translation_policy": {
            f"U+{codepoint:04X}": replacement
            for codepoint, replacement in sorted(_ASCII_TRANSLATION.items())
        },
        "replacement_counts": dict(sorted(replacement_counts.items())),
        "source_text_emitted": False,
    }


def _candidate_summary(
    report: Mapping[str, object], canonical_json: str
) -> dict[str, object]:
    duplicate = report["cross_fold_duplicate_audit"]
    assert isinstance(duplicate, Mapping)
    subgroups = duplicate["subgroups"]
    assert isinstance(subgroups, Mapping)
    subgroup_summary: dict[str, object] = {}
    for name in ("normalized_text_twin", "no_normalized_text_twin"):
        subgroup = subgroups[name]
        assert isinstance(subgroup, Mapping)
        subgroup_metrics = subgroup["k_metrics"]
        assert isinstance(subgroup_metrics, Mapping)
        subgroup_summary[name] = {
            "unit_count": subgroup["unit_count"],
            "full_set_coverage_at_5": (
                subgroup_metrics["5"]["full_set_coverage"] if subgroup_metrics else None
            ),
        }
    per_tier = report["per_tier"]
    assert isinstance(per_tier, Mapping)
    return {
        "canonical_sha256": _sha256_bytes(canonical_json.encode("ascii")),
        "canonical_ascii_bytes": len(canonical_json.encode("ascii")),
        "scope": report["scope"],
        "population": report["population"],
        "required_label_cardinality": report["required_label_cardinality"],
        "duplicate_required_call_occurrence_count": report[
            "duplicate_required_call_occurrence_count"
        ],
        "last_required_label_rank": report["last_required_label_rank"],
        "k_metrics": _project_metrics(report["k_metrics"]),
        "per_tier": {
            tier: _project_metrics(metrics, k_grid=TIER_K_GRID)
            for tier, metrics in sorted(per_tier.items())
        },
        "cross_fold_duplicate_audit": {
            "normalization": duplicate["normalization"],
            "tokenization": duplicate["tokenization"],
            "normalized_text_twin_validation_units": duplicate[
                "normalized_text_twin_validation_units"
            ],
            "token_sequence_twin_validation_units": duplicate[
                "token_sequence_twin_validation_units"
            ],
            "normalized_text_twin_same_required_label_set_units": duplicate[
                "normalized_text_twin_same_required_label_set_units"
            ],
            "subgroups": subgroup_summary,
        },
    }


def _factorial_summary(
    report: Mapping[str, object], canonical_json: str
) -> dict[str, object]:
    cells = report["cells"]
    contrasts = report["contrasts"]
    assert isinstance(cells, Mapping)
    assert isinstance(contrasts, Mapping)
    return {
        "canonical_sha256": _sha256_bytes(canonical_json.encode("ascii")),
        "canonical_ascii_bytes": len(canonical_json.encode("ascii")),
        "input_boundary": report["input_boundary"],
        "population": report["population"],
        "complete_dialogue_text_identity": report["complete_dialogue_text_identity"],
        "cells": {
            name: {
                "overall": _project_metrics(cell["overall"]),
                "tier7_multiturn": _project_metrics(cell["tier7_multiturn"]),
                "last_required_label_rank": cell["last_required_label_rank"],
            }
            for name, cell in cells.items()
        },
        "contrasts": contrasts,
        "decision": report["decision"],
    }


def _grouped_summary(
    report: Mapping[str, object], canonical_json: str
) -> dict[str, object]:
    aggregate = report["aggregate"]
    assert isinstance(aggregate, Mapping)
    per_tier = aggregate["per_tier"]
    assert isinstance(per_tier, Mapping)
    subgroup_names = (
        "single_call",
        "multi_call",
        "multiple_distinct_required_labels",
        "duplicate_call_occurrences",
    )
    subgroups: dict[str, object] = {}
    for name in subgroup_names:
        subgroup = aggregate[name]
        assert isinstance(subgroup, Mapping)
        metrics = subgroup["k_metrics"]
        assert isinstance(metrics, Mapping)
        subgroups[name] = {
            "unit_count": subgroup["unit_count"],
            "k_metrics": (
                _project_metrics(metrics, k_grid=TIER_K_GRID) if metrics else {}
            ),
        }
    near = aggregate["near_duplicate_sensitivity"]
    assert isinstance(near, Mapping)
    near_subgroups: dict[str, object] = {}
    for name in ("near_duplicate", "no_near_duplicate"):
        subgroup = near[name]
        assert isinstance(subgroup, Mapping)
        metrics = subgroup["k_metrics"]
        assert isinstance(metrics, Mapping)
        near_subgroups[name] = {
            "unit_count": subgroup["unit_count"],
            "k_metrics": (
                _project_metrics(metrics, k_grid=TIER_K_GRID) if metrics else {}
            ),
        }
    folds = report["folds"]
    assert isinstance(folds, Sequence)
    return {
        "canonical_sha256": _sha256_bytes(canonical_json.encode("ascii")),
        "canonical_ascii_bytes": len(canonical_json.encode("ascii")),
        "scope": report["scope"],
        "split_policy": report["split_policy"],
        "population": report["population"],
        "retrieval_key_design": report["retrieval_key_design"],
        "folds": [
            {
                "fold_id": fold["fold_id"],
                "build_units": fold["build_units"],
                "validation_units": fold["validation_units"],
                "validation_query_blocks": fold["validation_query_blocks"],
                "validation_tier_counts": fold["validation_tier_counts"],
                "validation_multi_call_units": fold["validation_multi_call_units"],
                "validation_required_labels_absent_from_build": fold[
                    "validation_required_labels_absent_from_build"
                ],
                "candidate_report_sha256": fold["candidate_report_sha256"],
                "k_metrics": _project_metrics(fold["k_metrics"], k_grid=TIER_K_GRID),
            }
            for fold in folds
        ],
        "cross_fold_duplicate_audit": report["cross_fold_duplicate_audit"],
        "aggregate": {
            "k_metrics": _project_metrics(aggregate["k_metrics"], k_grid=TIER_K_GRID),
            "per_tier": {
                tier: _project_metrics(metrics, k_grid=TIER_K_GRID)
                for tier, metrics in sorted(per_tier.items())
            },
            **subgroups,
            "near_duplicate_sensitivity": {
                "threshold": near["threshold"],
                "metric": near["metric"],
                "maximum_jaccard": near["maximum_jaccard"],
                **near_subgroups,
            },
            "worst_fold_full_set_coverage": {
                str(k): aggregate["worst_fold_full_set_coverage"][str(k)]
                for k in TIER_K_GRID
            },
        },
        "quality_gate": report["quality_gate"],
    }


def _grouped_variant_delta(
    baseline: Mapping[str, object], augmented: Mapping[str, object]
) -> dict[str, object]:
    baseline_aggregate = baseline["aggregate"]
    augmented_aggregate = augmented["aggregate"]
    assert isinstance(baseline_aggregate, Mapping)
    assert isinstance(augmented_aggregate, Mapping)
    baseline_tiers = baseline_aggregate["per_tier"]
    augmented_tiers = augmented_aggregate["per_tier"]
    assert isinstance(baseline_tiers, Mapping)
    assert isinstance(augmented_tiers, Mapping)
    return {
        "comparison": (
            "Caller-supplied public registry semantic keys minus construction-key-only "
            "BM25 on identical label-blind grouped folds."
        ),
        "public_metadata_fields": ["tool_name", "domain", "category", "description"],
        "sample_argument_values_used": False,
        "gold_labels_used_to_build_public_keys": False,
        "key_text_emitted": False,
        "by_k": {
            str(k): {
                "overall_full_set_coverage_delta": (
                    augmented_aggregate["k_metrics"][str(k)]["full_set_coverage"]
                    - baseline_aggregate["k_metrics"][str(k)]["full_set_coverage"]
                ),
                "overall_required_item_recall_delta": (
                    augmented_aggregate["k_metrics"][str(k)]["required_item_recall"]
                    - baseline_aggregate["k_metrics"][str(k)]["required_item_recall"]
                ),
                "mean_distractor_burden_delta": (
                    augmented_aggregate["k_metrics"][str(k)]["mean_distractor_burden"]
                    - baseline_aggregate["k_metrics"][str(k)]["mean_distractor_burden"]
                ),
                "per_tier_full_set_coverage_delta": {
                    tier: (
                        augmented_tiers[tier][str(k)]["full_set_coverage"]
                        - baseline_tiers[tier][str(k)]["full_set_coverage"]
                    )
                    for tier in sorted(baseline_tiers)
                },
            }
            for k in TIER_K_GRID
        },
    }


def run_audit(*, repo: Path, root: Path) -> dict[str, object]:
    """Rebuild every compact metric from pinned local construction data."""

    lock_path = umbrella_lock_path(repo)
    lock = load_lock(lock_path)
    registry = load_tool_registry(lock, root)
    rows, inventory = a2t_pool_rows(lock, root)
    partition = propose_partition(
        rows,
        exposed_sample_ids(repo),
        seed=PARTITION_SEED,
    )
    if partition.split_identity_hash() != PARTITION_IDENTITY:
        raise RuntimeError("construction/evaluation partition identity drift")
    corpus = build_action_family_corpus(registry, partition.construction)
    build, validation = split_construction_validation(
        partition.construction,
        seed=VALIDATION_SEED,
        validation_fraction=VALIDATION_FRACTION,
    )
    manifest_path = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root) / _DIALOGUE_RELATIVE_PATH
    dialogue_overrides, dialogue_source = _load_dialogue_overrides(
        manifest_path=manifest_path,
        construction_rows=partition.construction,
    )
    registry_names = tuple(str(row["tool_name"]) for row in registry)
    public_registry_keys = _public_registry_retrieval_keys(registry)

    task = audit_construction_task_information(
        construction_rows=partition.construction,
        contracts=corpus.contracts,
        families=corpus.families,
    )
    candidate = analyze_label_candidate_reduction(
        construction_rows=build,
        validation_rows=validation,
        registry_tool_names=registry_names,
        k_grid=K_GRID,
    )
    factorial = analyze_observation_text_ablation(
        construction_rows=build,
        validation_rows=validation,
        registry_tool_names=registry_names,
        complete_dialogue_text_by_unit_id=dialogue_overrides,
        k_grid=K_GRID,
    )
    grouped = analyze_grouped_candidate_validation(
        construction_rows=partition.construction,
        registry_tool_names=registry_names,
        seed=VALIDATION_SEED,
        fold_count=5,
        k_grid=K_GRID,
        alternate_text_by_unit_id=dialogue_overrides,
    )
    grouped_public_registry = analyze_grouped_candidate_validation(
        construction_rows=partition.construction,
        registry_tool_names=registry_names,
        seed=VALIDATION_SEED,
        fold_count=5,
        k_grid=K_GRID,
        alternate_text_by_unit_id=dialogue_overrides,
        public_tool_key_text_by_name=public_registry_keys,
    )

    task_report = task.report
    argument = task_report["argument_structure"]
    contracts = task_report["contract_burdens"]
    prior = task_report["raw_tool_prior"]
    candidate_report = candidate.report
    grouped_passing = grouped.report["quality_gate"]["passing_fixed_k"]
    grouped_public_passing = grouped_public_registry.report["quality_gate"][
        "passing_fixed_k"
    ]
    construction_ids = tuple(row.unit_id for row in partition.construction)
    return {
        "schema": "saea-a2t-construction-task-information-summary-v3",
        "scope": (
            "Construction/training distribution and construction-internal, "
            "query-block-disjoint perfect-text retrieval only; no runtime, "
            "evaluation/test-derived knowledge, or model-consumption claim."
        ),
        "source_provenance": {
            "datasets_lock_sha256": _sha256_bytes(lock_path.read_bytes()),
            "source_file_sha256": _source_hashes(repo),
            "tier7_complete_dialogue": dialogue_source,
        },
        "partition": {
            "policy_id": partition.policy_id,
            "construction_seed": PARTITION_SEED,
            "construction_identity_sha256": _sha256_bytes(
                "\n".join(construction_ids).encode("ascii")
            ),
            "proposed_evaluation_identity_sha256": partition.split_identity_hash(),
            "construction_units": len(partition.construction),
            "construction_query_blocks": len(
                {row.query_idx for row in partition.construction}
            ),
            "internal_validation_seed": VALIDATION_SEED,
            "internal_validation_fraction": VALIDATION_FRACTION,
            "internal_build_units": len(build),
            "internal_validation_units": len(validation),
            "internal_build_query_blocks": len({row.query_idx for row in build}),
            "internal_validation_query_blocks": len(
                {row.query_idx for row in validation}
            ),
            "internal_split_gold_support_conditioned": True,
            "exact_normalized_text_group_disjoint": False,
        },
        "carrier_inventory": {
            "pool_items": inventory["pool_items"],
            "pool_units": inventory["pool_units"],
            "usable_items": inventory["usable_items"],
            "usable_units": inventory["usable_units"],
            "quarantined_unit_count": inventory["quarantined_unit_count"],
        },
        "construction": {
            "canonical_sha256": _sha256_bytes(task.canonical_json.encode("ascii")),
            "canonical_ascii_bytes": len(task.canonical_json.encode("ascii")),
            "population": task_report["population"],
            "tier_counts": task_report["tiers"]["counts"],
            "tier_shares": task_report["tiers"]["shares"],
            "call_structure": task_report["call_structure"],
            "argument_structure": {
                "primary_argument_count_per_unit": argument[
                    "primary_argument_count_per_unit"
                ],
                "syntax_incompatible_primary_unit_count": argument[
                    "syntax_incompatible_primary_unit_count"
                ],
                "argument_bearing_primary_unit_count": argument[
                    "argument_bearing_primary_unit_count"
                ],
                "no_argument_primary_unit_count": argument[
                    "no_argument_primary_unit_count"
                ],
                "distinct_observed_primary_key_skeleton_count": argument[
                    "distinct_observed_primary_key_skeleton_count"
                ],
                "observed_legal_skeleton_count": argument[
                    "observed_legal_skeleton_count"
                ],
                "unobserved_legal_skeleton_count": argument[
                    "unobserved_legal_skeleton_count"
                ],
            },
            "contract_burdens": contracts,
            "raw_tool_prior": {
                "entropy_bits": prior["entropy_bits"],
                "effective_label_count": prior["effective_label_count"],
                "normalized_entropy": prior["normalized_entropy"],
                "top_k_mass": prior["top_k_mass"],
                "minimum_k_for_mass": prior["minimum_k_for_mass"],
            },
        },
        "candidate_reduction": _candidate_summary(
            candidate_report, candidate.canonical_json
        ),
        "grouped_out_of_fold_candidate_reduction": _grouped_summary(
            grouped.report, grouped.canonical_json
        ),
        "public_registry_augmented_grouped_candidate_reduction": _grouped_summary(
            grouped_public_registry.report,
            grouped_public_registry.canonical_json,
        ),
        "public_registry_key_ablation": _grouped_variant_delta(
            grouped.report,
            grouped_public_registry.report,
        ),
        "multiturn_text_factorial": _factorial_summary(
            factorial.report, factorial.canonical_json
        ),
        "model_free_admission": {
            "fixed_k_candidates_passing_current_quality_gate": grouped_passing,
            "candidate_quality_gate_passed": bool(grouped_passing),
            "public_registry_augmented_fixed_k_candidates_passing": (
                grouped_public_passing
            ),
            "public_registry_augmented_quality_gate_passed": bool(
                grouped_public_passing
            ),
            "public_registry_semantic_key_ablation_promoted": False,
            "cross_fold_exact_text_twins_eliminated": True,
            "cross_fold_bm25_token_twins_eliminated": True,
            "worst_fold_gate_measured": True,
            "multi_call_subgroup_gate_measured": True,
            "near_duplicate_sensitivity_measured": True,
            "runtime_legal_history_observation_implemented": False,
            "authorized_model_contact": False,
            "decision": "CONTINUE_MODEL_FREE_RETRIEVAL_AND_OBSERVATION_DESIGN",
        },
        "contacts": {
            "model": 0,
            "network": 0,
            "scorer": 0,
            "tokenizer": 0,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--verify-summary", type=Path)
    args = parser.parse_args(argv)
    result = run_audit(
        repo=REPO,
        root=args.data_root.resolve() if args.data_root else data_root(),
    )
    rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.verify_summary is not None:
        expected = json.loads(args.verify_summary.read_text(encoding="utf-8"))
        if expected != result:
            raise RuntimeError("committed summary does not reproduce")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
