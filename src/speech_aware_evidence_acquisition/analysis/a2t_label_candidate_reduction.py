"""Construction-only, perfect-transcript Audio2Tool label candidate analysis.

The analysis builds BM25 keys from one query-block-disjoint construction fold
and evaluates unique tool-label rankings on another construction fold.  Every
call label on a construction row is attached to that row's text key.  Gold is
used only to measure the already-produced validation ranking; no output from
this module is runtime eligible.  It measures label retrieval, not argument
coverage, multiplicity recovery, or frozen-core consumption.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
from typing import Mapping, Sequence

from .a2t_lexical_ceiling import Bm25Index, tokenize
from ..rails.knowledge_build_a2t import A2tKbRow


RESULT_SCHEMA = "saea-a2t-label-candidate-reduction-v3"


class LabelCandidateReductionError(ValueError):
    """The construction-only candidate-reduction boundary is malformed."""


@dataclass(frozen=True)
class LabelCandidateReductionAudit:
    """A JSON-compatible report and its canonical serialization."""

    report: Mapping[str, object]
    canonical_json: str


def _validate_registry(value: Sequence[str]) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise LabelCandidateReductionError(
            "registry tool names must be a sequence of unique non-empty text"
        )
    names = tuple(value)
    if (
        not names
        or any(not isinstance(name, str) or not name for name in names)
        or len(names) != len(set(names))
    ):
        raise LabelCandidateReductionError(
            "registry tool names must be a sequence of unique non-empty text"
        )
    return tuple(sorted(names))


def _validate_k_grid(value: Sequence[int]) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise LabelCandidateReductionError(
            "k_grid must contain unique positive integers"
        )
    values = tuple(value)
    if (
        not values
        or len(values) != len(set(values))
        or any(type(item) is not int or item <= 0 for item in values)
    ):
        raise LabelCandidateReductionError(
            "k_grid must contain unique positive integers"
        )
    return tuple(sorted(values))


def _validate_public_tool_keys(
    value: Mapping[str, str] | None,
    *,
    registry: Sequence[str],
) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or set(value) != set(registry):
        raise LabelCandidateReductionError(
            "public tool keys must exactly cover the registered tool names"
        )
    keys: dict[str, str] = {}
    for tool in registry:
        text = value[tool]
        if (
            not isinstance(text, str)
            or not text.strip()
            or any(ord(character) > 127 for character in text)
        ):
            raise LabelCandidateReductionError(
                "public tool keys must contain non-empty ASCII English text"
            )
        keys[tool] = text.strip()
    return keys


def _validate_rows(
    rows: Sequence[A2tKbRow],
    *,
    label: str,
    registry: frozenset[str],
) -> tuple[A2tKbRow, ...]:
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence) or not rows:
        raise LabelCandidateReductionError(f"{label} must be non-empty")
    ordered = tuple(sorted(rows, key=lambda row: getattr(row, "unit_id", "")))
    seen: set[str] = set()
    for row in ordered:
        if not isinstance(row, A2tKbRow):
            raise LabelCandidateReductionError(f"{label} must contain A2tKbRow values")
        if not isinstance(row.unit_id, str) or not row.unit_id or row.unit_id in seen:
            raise LabelCandidateReductionError(
                f"{label} has duplicate or malformed units"
            )
        seen.add(row.unit_id)
        if type(row.query_idx) is not int or row.query_idx < 0:
            raise LabelCandidateReductionError(f"{label} has malformed query_idx")
        if not isinstance(row.text, str) or not row.text.strip():
            raise LabelCandidateReductionError(f"{label} has empty retrieval text")
        if not isinstance(row.extra_call_names, tuple):
            raise LabelCandidateReductionError(f"{label} has malformed call labels")
        call_names = (row.tool_name, *row.extra_call_names)
        if row.call_count != len(call_names):
            raise LabelCandidateReductionError(f"{label} has inconsistent call_count")
        unknown = sorted(set(call_names) - registry)
        if unknown:
            kind = "construction" if label == "construction_rows" else "validation"
            raise LabelCandidateReductionError(
                f"unknown {kind} tool labels: {unknown!r}"
            )
    return ordered


def _tool_ranking(
    *,
    index: Bm25Index,
    query: str,
    labels_by_document: Sequence[tuple[str, ...]],
    registry: Sequence[str],
) -> tuple[tuple[str, ...], frozenset[str]]:
    document_scores = index.scores(query)
    score_by_tool = {tool: 0.0 for tool in registry}
    for document_index, score in document_scores.items():
        for tool in labels_by_document[document_index]:
            score_by_tool[tool] = max(score_by_tool[tool], score)
    ranking = tuple(sorted(registry, key=lambda tool: (-score_by_tool[tool], tool)))
    return ranking, frozenset(
        tool for tool, score in score_by_tool.items() if score > 0.0
    )


def candidate_sample_metrics(
    sample_rows: Sequence[Mapping[str, object]],
    *,
    k: int,
    registry_count: int,
) -> dict[str, object]:
    effective_k = min(k, registry_count)
    required_total = 0
    retrieved_total = 0
    matched_total = 0
    full = 0
    positive_full = 0
    distractors = 0
    positive_matched_total = 0
    zero_score_fallbacks = 0
    for sample in sample_rows:
        required = set(sample["required_tool_names"])
        retrieved = tuple(sample["ranked_tool_names"])[:effective_k]
        positive = set(sample["positive_score_tool_names"])
        matched = len(required & set(retrieved))
        positive_matched = len(required & set(retrieved) & positive)
        required_total += len(required)
        retrieved_total += len(retrieved)
        matched_total += matched
        positive_matched_total += positive_matched
        full += int(matched == len(required))
        positive_full += int(positive_matched == len(required))
        distractors += len(retrieved) - matched
        zero_score_fallbacks += len(set(retrieved) - positive)
    count = len(sample_rows)
    return {
        "sample_count": count,
        "requested_k": k,
        "effective_k": effective_k,
        "required_item_recall": matched_total / required_total,
        "full_set_coverage": full / count,
        "precision": matched_total / retrieved_total,
        "mean_distractor_burden": distractors / count,
        "positive_score_required_item_recall": positive_matched_total / required_total,
        "positive_score_full_set_coverage": positive_full / count,
        "mean_zero_score_fallback_count": zero_score_fallbacks / count,
        "maximum_decision_space_reduction_bits": math.log2(
            registry_count / effective_k
        ),
    }


def _rank_summary(ranks: Sequence[int]) -> dict[str, int]:
    ordered = sorted(ranks)
    return {
        "minimum": ordered[0],
        "median": ordered[len(ordered) // 2],
        "p90": ordered[max(0, math.ceil(0.90 * len(ordered)) - 1)],
        "maximum": ordered[-1],
    }


def _normalized_text(text: str) -> str:
    return " ".join(text.casefold().split())


def _subgroup_metrics(
    samples: Sequence[Mapping[str, object]],
    *,
    k_values: Sequence[int],
    registry_count: int,
) -> dict[str, object]:
    return {
        "unit_count": len(samples),
        "k_metrics": (
            {
                str(k): candidate_sample_metrics(
                    samples, k=k, registry_count=registry_count
                )
                for k in k_values
            }
            if samples
            else {}
        ),
    }


def analyze_label_candidate_reduction(
    *,
    construction_rows: Sequence[A2tKbRow],
    validation_rows: Sequence[A2tKbRow],
    registry_tool_names: Sequence[str],
    k_grid: Sequence[int],
    public_tool_key_text_by_name: Mapping[str, str] | None = None,
) -> LabelCandidateReductionAudit:
    """Measure block-disjoint, perfect-transcript required-label coverage at k."""

    registry = _validate_registry(registry_tool_names)
    registry_set = frozenset(registry)
    k_values = _validate_k_grid(k_grid)
    public_tool_keys = _validate_public_tool_keys(
        public_tool_key_text_by_name,
        registry=registry,
    )
    construction = _validate_rows(
        construction_rows,
        label="construction_rows",
        registry=registry_set,
    )
    validation = _validate_rows(
        validation_rows,
        label="validation_rows",
        registry=registry_set,
    )
    overlap = sorted(
        {row.query_idx for row in construction} & {row.query_idx for row in validation}
    )
    if overlap:
        raise LabelCandidateReductionError(
            "construction and validation query_idx blocks overlap"
        )

    construction_documents = tuple((row.unit_id, row.text) for row in construction)
    construction_labels_by_document = tuple(
        tuple(dict.fromkeys((row.tool_name, *row.extra_call_names)))
        for row in construction
    )
    public_documents = tuple(
        (f"public-tool:{tool}", public_tool_keys[tool])
        for tool in registry
        if tool in public_tool_keys
    )
    index = Bm25Index.build((*construction_documents, *public_documents))
    labels_by_document = (
        *construction_labels_by_document,
        *((tool,) for tool in registry if tool in public_tool_keys),
    )
    labels_by_normalized_text: dict[str, set[frozenset[str]]] = {}
    for row, labels in zip(construction, construction_labels_by_document, strict=True):
        labels_by_normalized_text.setdefault(_normalized_text(row.text), set()).add(
            frozenset(labels)
        )
    build_token_sequences = {tokenize(row.text) for row in construction}
    observed_labels = {
        tool for labels in construction_labels_by_document for tool in labels
    }
    samples: list[dict[str, object]] = []
    all_required_labels: set[str] = set()
    required_occurrences = 0
    duplicate_occurrences = 0
    for row in validation:
        call_names = (row.tool_name, *row.extra_call_names)
        required = tuple(dict.fromkeys(call_names))
        ranking, positive_score_tools = _tool_ranking(
            index=index,
            query=row.text,
            labels_by_document=labels_by_document,
            registry=registry,
        )
        ranks = {tool: rank for rank, tool in enumerate(ranking, start=1)}
        last_rank = max(ranks[tool] for tool in required)
        all_required_labels.update(required)
        required_occurrences += len(call_names)
        duplicate_occurrences += len(call_names) - len(required)
        normalized_text = _normalized_text(row.text)
        exact_text_twin = normalized_text in labels_by_normalized_text
        token_sequence_twin = tokenize(row.text) in build_token_sequences
        exact_text_same_required = (
            exact_text_twin
            and frozenset(required) in (labels_by_normalized_text[normalized_text])
        )
        samples.append(
            {
                "unit_id": row.unit_id,
                "tier": row.tier,
                "required_tool_names": list(required),
                "required_call_occurrence_count": len(call_names),
                "duplicate_required_call_occurrence_count": len(call_names)
                - len(required),
                "ranked_tool_names": list(ranking),
                "positive_score_tool_names": sorted(positive_score_tools),
                "positive_score_tool_count": len(positive_score_tools),
                "required_tools_with_positive_score": [
                    tool for tool in required if tool in positive_score_tools
                ],
                "normalized_build_text_twin": exact_text_twin,
                "build_token_sequence_twin": token_sequence_twin,
                "normalized_text_twin_same_required_label_set": (
                    exact_text_same_required
                ),
                "last_required_label_rank": last_rank,
            }
        )

    k_metrics = {
        str(k): candidate_sample_metrics(samples, k=k, registry_count=len(registry))
        for k in k_values
    }
    tiers = sorted({str(sample["tier"]) for sample in samples})
    per_tier = {
        tier: {
            str(k): candidate_sample_metrics(
                [sample for sample in samples if sample["tier"] == tier],
                k=k,
                registry_count=len(registry),
            )
            for k in k_values
        }
        for tier in tiers
    }
    exact_text_twins = [
        sample for sample in samples if sample["normalized_build_text_twin"] is True
    ]
    non_exact_text_twins = [
        sample for sample in samples if sample["normalized_build_text_twin"] is False
    ]
    report: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "scope": {
            "construction_training_rows_only": True,
            "query_idx_block_disjoint_validation": True,
            "perfect_transcript_conditioned": True,
            "runtime_eligible": False,
            "retrieval_coverage_only": True,
            "model_consumption_upper_bound": False,
            "multiplicity_coverage_measured": False,
            "argument_or_value_coverage_measured": False,
            "model_contacts": 0,
            "scorer_contacts": 0,
            "network_contacts": 0,
        },
        "population": {
            "construction_unit_count": len(construction),
            "validation_unit_count": len(validation),
            "registry_label_count": len(registry),
            "construction_observed_label_count": len(observed_labels),
            "validation_required_unique_label_count": len(all_required_labels),
            "validation_required_call_occurrence_count": required_occurrences,
        },
        "retrieval_key_design": {
            "one_key_per_construction_unit": True,
            "every_primary_and_extra_call_label_attached": True,
            "construction_key_count": len(construction_documents),
            "public_tool_key_count": len(public_documents),
            "public_tool_keys_from_caller_supplied_registry_metadata": bool(
                public_tool_keys
            ),
            "tool_score": (
                "maximum BM25 score over construction or caller-supplied public "
                "registry keys carrying the tool"
            ),
            "ranking_tie_break": "ascending registered tool name",
        },
        "required_label_cardinality": {
            str(size): count
            for size, count in sorted(
                Counter(
                    len(sample["required_tool_names"]) for sample in samples
                ).items()
            )
        },
        "duplicate_required_call_occurrence_count": duplicate_occurrences,
        "cross_fold_duplicate_audit": {
            "normalization": "casefolded whitespace-collapsed text",
            "tokenization": "lowercase [a-z0-9]+ token sequence",
            "normalized_text_twin_validation_units": len(exact_text_twins),
            "token_sequence_twin_validation_units": sum(
                sample["build_token_sequence_twin"] is True for sample in samples
            ),
            "normalized_text_twin_same_required_label_set_units": sum(
                sample["normalized_text_twin_same_required_label_set"] is True
                for sample in samples
            ),
            "subgroups": {
                "normalized_text_twin": _subgroup_metrics(
                    exact_text_twins,
                    k_values=k_values,
                    registry_count=len(registry),
                ),
                "no_normalized_text_twin": _subgroup_metrics(
                    non_exact_text_twins,
                    k_values=k_values,
                    registry_count=len(registry),
                ),
            },
        },
        "last_required_label_rank": _rank_summary(
            [int(sample["last_required_label_rank"]) for sample in samples]
        ),
        "k_metrics": k_metrics,
        "per_tier": per_tier,
        "samples": samples,
    }
    canonical = json.dumps(
        report,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return LabelCandidateReductionAudit(report=report, canonical_json=canonical)


__all__ = [
    "LabelCandidateReductionAudit",
    "LabelCandidateReductionError",
    "RESULT_SCHEMA",
    "analyze_label_candidate_reduction",
    "candidate_sample_metrics",
]
