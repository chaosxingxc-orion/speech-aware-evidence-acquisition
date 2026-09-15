"""Model-free breadth audit over the shared SLURP recall/rank/fuse path.

Selection is completed and hash-committed before an offline reference join.
The selection API accepts no reference rows, which keeps task labels outside
the retrieval path. Reports retain identities, Boolean support facts, ranks,
counts, and hashes; they never export reference intent strings or transcripts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping, Sequence

from ..rails.hashing import canonical_json_bytes, content_hash
from ..rails.kb_policy import (
    ASSOCIATED_VALUES_FUSE_POLICY_ID,
    FuseKnobs,
    RANK_POLICY_ID,
    RankWeights,
)
from ..rails.knowledge import KnowledgeSnapshot, QueryState
from ..rails.knowledge_provider import KbFacetProvider
from ..rails.knowledge_stores import qualify_id
from ..rails.phase_supply import SealedSegmentQuery, prepare_recall_rows

AUDIT_SCHEMA = "saea-slurp-retrieval-supply-audit-v1"
SELECTION_SCHEMA = "saea-slurp-retrieval-supply-selection-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")


class AuditError(ValueError):
    """A pinned input, cohort, replay anchor, or output is invalid."""


@dataclass(frozen=True)
class SelectionAnchor:
    """Identity-only replay material safe to load before reference access."""

    sample_ids: tuple[str, ...]
    selected_ids_sha256: tuple[str, ...]


@dataclass(frozen=True)
class ObservedSupportRow:
    """Released breadth-eight flags used only after selection is sealed."""

    sample_id: str
    selected_ids_sha256: str
    own_intent_supplied: bool
    c0_covered: bool


@dataclass(frozen=True)
class ReferenceIntentRow:
    """Offline reference facts loaded only after selection is sealed."""

    sample_id: str
    intent_id: str
    scenario_id: str


@dataclass(frozen=True)
class SampleSelection:
    """In-memory selection needed for the later offline join."""

    selected_value_ids: tuple[str, ...]
    ranked_facets: tuple[tuple[str, float], ...]
    selected_ids_sha256: str
    ranked_facets_sha256: str
    knowledge_char_count: int
    knowledge_utf8_bytes: int


@dataclass(frozen=True)
class SelectionGrid:
    """All model-free selections, built without reference labels."""

    sample_ids: tuple[str, ...]
    breadths: tuple[int, ...]
    store_id: str
    snapshot_sha256: str
    by_breadth: Mapping[int, Mapping[str, SampleSelection]]
    _value_by_id: Mapping[str, object] = field(repr=False, compare=False)

    def commitment(self) -> dict[str, object]:
        rows: dict[str, list[dict[str, object]]] = {}
        for breadth in self.breadths:
            rows[str(breadth)] = [
                {
                    "sample_id": sample_id,
                    "selected_value_ids_sha256": self.by_breadth[breadth][
                        sample_id
                    ].selected_ids_sha256,
                    "ranked_facets_sha256": self.by_breadth[breadth][
                        sample_id
                    ].ranked_facets_sha256,
                    "selection_count": len(
                        self.by_breadth[breadth][sample_id].selected_value_ids
                    ),
                }
                for sample_id in self.sample_ids
            ]
        body = {
            "schema": SELECTION_SCHEMA,
            "sample_count": len(self.sample_ids),
            "ordered_sample_ids_sha256": content_hash(list(self.sample_ids)),
            "breadths": list(self.breadths),
            "store_id": self.store_id,
            "snapshot_sha256": self.snapshot_sha256,
            "rows": rows,
            "reference_joined": False,
        }
        return {**body, "selection_sha256": content_hash(body)}


def _require_sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise AuditError(f"{field} must be a lowercase 64-hex SHA-256")
    return value


def _ratio(numerator: int, denominator: int) -> dict[str, object]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _validate_cohort(
    expected: Sequence[str], actual: Sequence[str], *, field: str
) -> tuple[str, ...]:
    expected_ids = tuple(expected)
    actual_ids = tuple(actual)
    if (
        not expected_ids
        or len(set(expected_ids)) != len(expected_ids)
        or actual_ids != expected_ids
    ):
        raise AuditError(f"{field} must match the exact ordered cohort")
    return expected_ids


def _read_pinned_json(path: Path, expected_sha256: str, field: str) -> Mapping[str, object]:
    expected = _require_sha(expected_sha256, f"{field} SHA-256")
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise AuditError(f"cannot read {field}: {path}") from error
    if hashlib.sha256(raw).hexdigest() != expected:
        raise AuditError(f"{field} SHA-256 mismatch")
    try:
        document = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AuditError(f"{field} is not valid UTF-8 JSON") from error
    if not isinstance(document, Mapping):
        raise AuditError(f"{field} must be a JSON object")
    return document


def _support_samples(document: Mapping[str, object]) -> Sequence[Mapping[str, object]]:
    output = document.get("output")
    support = output.get("initial_intent_support") if isinstance(output, Mapping) else None
    rows = support.get("samples") if isinstance(support, Mapping) else None
    if not isinstance(rows, list) or not rows:
        raise AuditError("support diagnostic lacks sample rows")
    if not all(isinstance(row, Mapping) for row in rows):
        raise AuditError("support diagnostic sample rows are malformed")
    return rows


def load_selection_anchor(
    path: Path,
    *,
    expected_sha256: str,
    expected_sample_ids: Sequence[str] | None = None,
    expected_sample_count: int | None = None,
    expected_ordered_sample_ids_sha256: str | None = None,
) -> SelectionAnchor:
    """Load only sample identity and breadth-eight selection hashes."""

    document = _read_pinned_json(path, expected_sha256, "support diagnostic")
    rows = _support_samples(document)
    sample_ids = tuple(row.get("sample_id") for row in rows)
    if expected_sample_ids is None:
        if (
            not sample_ids
            or any(not isinstance(item, str) or not item for item in sample_ids)
            or len(set(sample_ids)) != len(sample_ids)
        ):
            raise AuditError("support diagnostic must carry a unique ordered cohort")
        expected = sample_ids
    else:
        expected = _validate_cohort(
            expected_sample_ids, sample_ids, field="support diagnostic"
        )
    if expected_sample_count is not None and len(expected) != expected_sample_count:
        raise AuditError("support diagnostic sample count differs from expected cohort")
    if (
        expected_ordered_sample_ids_sha256 is not None
        and content_hash(list(expected))
        != _require_sha(
            expected_ordered_sample_ids_sha256,
            "expected ordered sample IDs SHA-256",
        )
    ):
        raise AuditError("support diagnostic ordered cohort hash differs from expected")
    hashes = tuple(
        _require_sha(
            row.get("supplied_intent_value_ids_sha256"),
            f"support diagnostic sample {sample_id} selected hash",
        )
        for sample_id, row in zip(expected, rows, strict=True)
    )
    output = document.get("output")
    cohort = output.get("cohort") if isinstance(output, Mapping) else None
    if not isinstance(cohort, Mapping):
        raise AuditError("support diagnostic lacks cohort metadata")
    if (
        cohort.get("sample_count") != len(expected)
        or cohort.get("ordered_sample_ids_sha256") != content_hash(list(expected))
    ):
        raise AuditError("support diagnostic cohort metadata differs from ordered cohort")
    return SelectionAnchor(expected, hashes)


def load_observed_support(
    path: Path, *, expected_sha256: str, expected_sample_ids: Sequence[str]
) -> tuple[ObservedSupportRow, ...]:
    """Load released C0 flags after the selection commitment exists."""

    document = _read_pinned_json(path, expected_sha256, "support diagnostic")
    rows = _support_samples(document)
    expected = _validate_cohort(
        expected_sample_ids,
        tuple(row.get("sample_id") for row in rows),
        field="support diagnostic",
    )
    result = []
    for sample_id, row in zip(expected, rows, strict=True):
        own = row.get("gold_intent_value_supplied")
        covered = row.get("c0_gold_covered")
        if not isinstance(own, bool) or not isinstance(covered, bool):
            raise AuditError("support diagnostic C0 flags must be Boolean")
        result.append(
            ObservedSupportRow(
                sample_id,
                _require_sha(
                    row.get("supplied_intent_value_ids_sha256"),
                    f"support diagnostic sample {sample_id} selected hash",
                ),
                own,
                covered,
            )
        )
    return tuple(result)


def build_selection_grid(
    *,
    snapshot: KnowledgeSnapshot,
    query_vectors_by_sample: Mapping[
        str, Mapping[str, tuple[float, ...]] | SealedSegmentQuery
    ],
    facet_vectors: Mapping[str, Mapping[str, tuple[float, ...]]],
    ordered_sample_ids: Sequence[str],
    breadths: Sequence[int],
    store_id: str,
    workers: int = 1,
) -> SelectionGrid:
    """Run existing recall/rank/fuse functions without accepting references."""

    snapshot.validate()
    sample_ids = tuple(ordered_sample_ids)
    if (
        not sample_ids
        or len(set(sample_ids)) != len(sample_ids)
        or tuple(query_vectors_by_sample) != sample_ids
    ):
        raise AuditError("query vectors must match the exact ordered cohort")
    breadth_tuple = tuple(breadths)
    if (
        not breadth_tuple
        or len(set(breadth_tuple)) != len(breadth_tuple)
        or any(isinstance(item, bool) or not isinstance(item, int) or item <= 0
               for item in breadth_tuple)
    ):
        raise AuditError("breadths must be unique positive integers")
    if not isinstance(store_id, str) or not store_id or "::" in store_id:
        raise AuditError("store_id must be a nonempty local store ID")
    if workers != 1:
        raise AuditError("this audit requires exactly one CPU worker")

    snapshot_sha256 = snapshot.content_hash()
    value_by_id = {value.value_id: value for value in snapshot.values}
    split_hash = content_hash(list(sample_ids))
    table: dict[int, Mapping[str, SampleSelection]] = {}
    for breadth in breadth_tuple:
        prepared = prepare_recall_rows(
            snapshot,
            query_vectors_by_sample,
            facet_vectors,
            breadth,
            workers=workers,
        )
        provider = KbFacetProvider(
            build_spec=None,
            rank_policy_id=RANK_POLICY_ID,
            rank_weights=RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0),
            fuse_knobs=FuseKnobs(tau=0.0, m=breadth, c=1, top_l=breadth),
            top_k_per_dimension=breadth,
            prepared_recall=prepared,
        )
        provider.adopt(
            snapshot,
            policy_id="frozen-snapshot:retrieval-supply-audit",
            source_ids=(),
            snapshot_sha256=snapshot_sha256,
        )
        selected_rows: dict[str, SampleSelection] = {}
        for sample_id in sample_ids:
            query_record = query_vectors_by_sample[sample_id]
            packet_sha = (
                query_record.audio_sha256
                if isinstance(query_record, SealedSegmentQuery)
                else content_hash(dict(query_record))
            )
            state = QueryState(
                query_id=f"slurp-retrieval-supply-audit:{breadth}:{sample_id}",
                query_sample_id=sample_id,
                speech_packet_id=f"audit:{sample_id}",
                speech_packet_sha256=packet_sha,
                use_split_identity_hash=split_hash,
            ).validate()
            ranking = provider.candidates(state, k=breadth)
            decision = provider.fuse(
                (ranking,),
                k=breadth,
                policy_id=ASSOCIATED_VALUES_FUSE_POLICY_ID,
            )
            rank_result = provider.last_rank_result()
            ranked_facets = tuple(
                (candidate.facet_id, float(candidate.score))
                for candidate in rank_result.candidates
            )
            selected = tuple(decision.selected_value_ids)
            try:
                contents = tuple(value_by_id[value_id].content for value_id in selected)
            except KeyError as error:
                raise AuditError("fuser selected an unknown value ID") from error
            qualified = [qualify_id(store_id, value_id) for value_id in selected]
            selected_rows[sample_id] = SampleSelection(
                selected_value_ids=selected,
                ranked_facets=ranked_facets,
                selected_ids_sha256=content_hash(qualified),
                ranked_facets_sha256=content_hash(
                    [
                        {"facet_id": facet_id, "score": score}
                        for facet_id, score in ranked_facets
                    ]
                ),
                knowledge_char_count=sum(len(text) for text in contents),
                knowledge_utf8_bytes=sum(len(text.encode("utf-8")) for text in contents),
            )
        table[breadth] = MappingProxyType(selected_rows)
    return SelectionGrid(
        sample_ids=sample_ids,
        breadths=breadth_tuple,
        store_id=store_id,
        snapshot_sha256=snapshot_sha256,
        by_breadth=MappingProxyType(table),
        _value_by_id=MappingProxyType(value_by_id),
    )


def _positive_own_rank(
    selection: SampleSelection, associated_facet_ids: frozenset[str]
) -> int | None:
    for rank, (facet_id, score) in enumerate(selection.ranked_facets, start=1):
        if facet_id in associated_facet_ids and score > 0.0:
            return rank
    return None


def build_audit_report(
    *,
    selection: SelectionGrid,
    reference_rows: Sequence[ReferenceIntentRow],
    observed_rows: Sequence[ObservedSupportRow],
    replay_breadth: int,
    expected_replay_own_supplied: int,
    expected_replay_supply_and_covered: int,
) -> dict[str, object]:
    """Join sealed selections to offline references and released C0 flags."""

    refs = tuple(reference_rows)
    observed = tuple(observed_rows)
    _validate_cohort(
        selection.sample_ids,
        tuple(row.sample_id for row in refs),
        field="reference rows",
    )
    _validate_cohort(
        selection.sample_ids,
        tuple(row.sample_id for row in observed),
        field="observed support rows",
    )
    if replay_breadth not in selection.by_breadth:
        raise AuditError("replay breadth is absent from the selection grid")
    if any(
        not isinstance(row.intent_id, str) or not row.intent_id
        or not isinstance(row.scenario_id, str) or not row.scenario_id
        for row in refs
    ):
        raise AuditError("reference intent/scenario identities must be nonempty strings")
    if any(
        selection.by_breadth[replay_breadth][row.sample_id].selected_ids_sha256
        != row.selected_ids_sha256
        for row in observed
    ):
        raise AuditError("replay selected value hash differs from released C0 supply")
    own_count = sum(row.own_intent_supplied for row in observed)
    covered_count = sum(
        row.own_intent_supplied and row.c0_covered for row in observed
    )
    if own_count != expected_replay_own_supplied:
        raise AuditError("replay own-supplied count differs from the registered anchor")
    if covered_count != expected_replay_supply_and_covered:
        raise AuditError(
            "replay supply-and-covered count differs from the registered anchor"
        )

    value_by_id = selection._value_by_id
    if not value_by_id:
        raise AuditError("selection lacks its source-bound value association lookup")

    observed_by_id = {row.sample_id: row for row in observed}
    breadth_reports: dict[str, object] = {}
    for breadth in selection.breadths:
        samples = []
        scenario_counts: dict[str, list[int]] = {}
        supported_total = 0
        miss_supported = 0
        neither_supported = 0
        positive_ranks: dict[int, int] = {}
        selection_count = 0
        char_count = 0
        byte_count = 0
        for reference in refs:
            selected = selection.by_breadth[breadth][reference.sample_id]
            own_value_id = f"intent-boundary:{reference.intent_id}"
            value = value_by_id.get(own_value_id)
            if value is None:
                raise AuditError("reference intent has no exact own-intent value")
            supported = own_value_id in selected.selected_value_ids
            rank = _positive_own_rank(
                selected, frozenset(value.associated_facet_ids)
            )
            observed_row = observed_by_id[reference.sample_id]
            c0_miss = not observed_row.c0_covered
            neither = c0_miss and not observed_row.own_intent_supplied
            supported_total += int(supported)
            miss_supported += int(c0_miss and supported)
            neither_supported += int(neither and supported)
            if rank is not None:
                positive_ranks[rank] = positive_ranks.get(rank, 0) + 1
            scenario = scenario_counts.setdefault(reference.scenario_id, [0, 0])
            scenario[0] += int(supported)
            scenario[1] += 1
            selection_count += len(selected.selected_value_ids)
            char_count += selected.knowledge_char_count
            byte_count += selected.knowledge_utf8_bytes
            samples.append(
                {
                    "sample_id": reference.sample_id,
                    "own_intent_card_supplied": supported,
                    "positive_score_own_facet_rank": rank,
                    "selected_value_ids_sha256": selected.selected_ids_sha256,
                    "ranked_facets_sha256": selected.ranked_facets_sha256,
                    "c0_miss": c0_miss,
                    "c0_neither": neither,
                }
            )
        breadth_reports[str(breadth)] = {
            "aggregate": {
                "own_intent_card_supplied": _ratio(
                    supported_total, len(selection.sample_ids)
                ),
                "selection_count": selection_count,
                "knowledge_char_count": char_count,
                "knowledge_utf8_bytes": byte_count,
                "positive_score_own_facet_rank_distribution": {
                    str(rank): count for rank, count in sorted(positive_ranks.items())
                },
                "coverage_among_c0_misses": _ratio(
                    miss_supported,
                    sum(not row.c0_covered for row in observed),
                ),
                "coverage_among_c0_neither": _ratio(
                    neither_supported,
                    sum(
                        not row.c0_covered and not row.own_intent_supplied
                        for row in observed
                    ),
                ),
            },
            "per_scenario": {
                scenario: {
                    "own_intent_card_supplied": _ratio(counts[0], counts[1])
                }
                for scenario, counts in sorted(scenario_counts.items())
            },
            "samples": samples,
        }
    report = {
        "schema": AUDIT_SCHEMA,
        "semantics": {
            "diagnostic": "Deterministic selection coverage at fixed supply breadths.",
            "own_support": "Only the exact own-intent value counts as support; mentions in other cards do not.",
            "selection_uses_references": False,
            "generated_candidate_accuracy": False,
            "causal_gain_estimate": False,
            "token_counts_included": False,
        },
        "cohort": {
            "sample_count": len(selection.sample_ids),
            "ordered_sample_ids_sha256": content_hash(list(selection.sample_ids)),
        },
        "selection": {
            "schema": SELECTION_SCHEMA,
            "selection_sha256": selection.commitment()["selection_sha256"],
            "snapshot_sha256": selection.snapshot_sha256,
            "store_id": selection.store_id,
        },
        "replay": {
            "breadth": replay_breadth,
            "per_sample_selected_hash_match": True,
            "own_intent_card_supplied": own_count,
            "supply_and_c0_covered": covered_count,
        },
        "breadths": breadth_reports,
    }
    return report


def write_new_json(path: Path, document: Mapping[str, object]) -> dict[str, str]:
    """Atomically write canonical JSON and refuse an existing destination."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise AuditError(f"output already exists: {target}")
    raw = canonical_json_bytes(document) + b"\n"
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)
    except FileExistsError as error:
        raise AuditError(f"output already exists: {target}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return {"path": str(target), "sha256": hashlib.sha256(raw).hexdigest()}



__all__ = [
    "AUDIT_SCHEMA",
    "SELECTION_SCHEMA",
    "AuditError",
    "ObservedSupportRow",
    "ReferenceIntentRow",
    "SampleSelection",
    "SelectionAnchor",
    "SelectionGrid",
    "build_audit_report",
    "build_selection_grid",
    "load_observed_support",
    "load_selection_anchor",
    "write_new_json",
]
