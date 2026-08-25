"""The Audio2Tool G0 gate: a LEXICAL reachability ceiling over a built A2T
knowledge snapshot (campaign plan
``docs/readiness/2026-08-25-a2t-generality-campaign-plan.md`` section 3.6).

WHY LEXICAL AND NOT DENSE. The SLURP reachability ceiling
(``analysis.dev500_confirmatory_read.reachability_ceiling``) ranks content
facets by cosine against a flown query embedding. Producing an embedding on
this carrier requires the pinned ``qwen3-emb`` sidecar, which is a TOOL
CONTACT, and G0 is registered at ZERO contacts of any kind. So this module
computes the ceiling under a deterministic, locally implemented Okapi BM25
instead, and reports it as the proxy it is.

THE PROXY CUTS BOTH WAYS, and both directions are stated at every citation:

* **Pessimistic in the ranking function.** Token overlap cannot follow a
  paraphrase the way a dense encoder can. A dense ranker over the same
  facets would place at least some gold-tool facets higher than BM25 does,
  so on the ranking axis this number is a lower bound on what retrieval
  could reach.
* **Optimistic in the query representation.** The query text used here is
  the manifest's own transcript of the spoken command. At runtime the
  controller never sees that text; it sees a speech-derived percept (in the
  locked two-contact form, a first-contact knowledge decode). On the query
  axis this number is therefore an upper bound.

Neither direction dominates, so the honest statement is that this is a
CEILING ON THE LEXICAL CHANNEL CONDITIONED ON A PERFECT TRANSCRIPT, and the
gate treats it as a necessary condition, never a sufficient one: if even
this optimistic-transcript, closed-pool ranking cannot put a gold-tool
exemplar in the top-5, no fusion policy downstream can.

Everything here is pure Python plus the standard library. No embeddings, no
tokenizer, no model contact, no network.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Mapping, Sequence

from ..rails.errors import RailsError
from ..rails.knowledge import KnowledgeSnapshot

CEILING_POLICY_ID = "saea-a2t-lexical-ceiling-bm25-v1"

#: Okapi BM25 parameters, frozen here so the ceiling is reproducible from the
#: policy id alone.
BM25_K1 = 1.5
BM25_B = 0.75

DEFAULT_K_GRID: tuple[int, ...] = (1, 3, 5, 8, 16, 32, 128)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> tuple[str, ...]:
    """Lowercase, split on runs of non-alphanumeric characters. Deterministic,
    dependency-free, and identical for facets and queries."""

    return tuple(_TOKEN_RE.findall(text.lower()))


@dataclass(frozen=True)
class Bm25Index:
    """An inverted BM25 index over a fixed, ordered document list."""

    doc_ids: tuple[str, ...]
    doc_lengths: tuple[int, ...]
    average_length: float
    postings: Mapping[str, tuple[tuple[int, int], ...]]
    document_frequency: Mapping[str, int]

    @classmethod
    def build(cls, documents: Sequence[tuple[str, str]]) -> "Bm25Index":
        """``documents`` is an ordered sequence of ``(doc_id, text)`` pairs."""

        if not documents:
            raise RailsError("Bm25Index.build: documents must be non-empty")
        doc_ids: list[str] = []
        lengths: list[int] = []
        raw_postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for index, (doc_id, text) in enumerate(documents):
            tokens = tokenize(text)
            doc_ids.append(doc_id)
            lengths.append(len(tokens))
            for term, count in sorted(Counter(tokens).items()):
                raw_postings[term].append((index, count))
        total = sum(lengths)
        return cls(
            doc_ids=tuple(doc_ids),
            doc_lengths=tuple(lengths),
            average_length=(total / len(lengths)) if lengths else 0.0,
            postings={term: tuple(items) for term, items in sorted(raw_postings.items())},
            document_frequency={term: len(items) for term, items in raw_postings.items()},
        )

    def scores(self, query: str) -> dict[int, float]:
        """Sparse BM25 scores for one query, keyed by document index. Only
        documents sharing at least one query term appear."""

        n_docs = len(self.doc_ids)
        accumulated: dict[int, float] = defaultdict(float)
        for term in sorted(set(tokenize(query))):
            postings = self.postings.get(term)
            if not postings:
                continue
            df = self.document_frequency[term]
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            for doc_index, term_frequency in postings:
                length_norm = (
                    1.0 - BM25_B + BM25_B * (self.doc_lengths[doc_index] / self.average_length)
                    if self.average_length > 0
                    else 1.0
                )
                accumulated[doc_index] += idf * (
                    term_frequency
                    * (BM25_K1 + 1.0)
                    / (term_frequency + BM25_K1 * length_norm)
                )
        return dict(accumulated)

    def ranking(self, query: str) -> tuple[int, ...]:
        """Document indices in descending BM25 score. Ties break by ascending
        ``doc_id`` so the ranking is fully deterministic; documents with a
        zero score are appended in ``doc_id`` order, which is the worst case
        for the gold facet and therefore the conservative convention."""

        scored = self.scores(query)
        ordered = sorted(
            scored.items(), key=lambda item: (-item[1], self.doc_ids[item[0]])
        )
        head = tuple(index for index, _score in ordered)
        if len(head) == len(self.doc_ids):
            return head
        seen = set(head)
        tail = tuple(
            index
            for index, _doc_id in sorted(
                ((i, self.doc_ids[i]) for i in range(len(self.doc_ids)) if i not in seen),
                key=lambda pair: pair[1],
            )
        )
        return head + tail


def content_facet_targets(snapshot: KnowledgeSnapshot) -> dict[str, str]:
    """``content`` facet id -> the ``task_target`` (gold tool name) of the
    value that facet belongs to. Mirrors
    ``dev500_confirmatory_read.reachability_ceiling``'s own mapping step."""

    by_facet: dict[str, str] = {}
    for value in snapshot.values:
        if value.task_target is None:
            continue
        for facet_id in value.associated_facet_ids:
            by_facet.setdefault(facet_id, value.task_target)
    targets = {
        facet.facet_id: by_facet[facet.facet_id]
        for facet in snapshot.facets
        if facet.dimension == "content" and facet.facet_id in by_facet
    }
    if not targets:
        raise RailsError("snapshot exposes no content facet with a task target")
    return targets


def _percentile_index(length: int, fraction: float) -> int:
    return min(length - 1, max(0, math.ceil(fraction * length) - 1))


def _percentile(sorted_values: Sequence[int], fraction: float) -> int:
    if not sorted_values:
        raise RailsError("_percentile: empty sequence")
    return sorted_values[_percentile_index(len(sorted_values), fraction)]


def _percentile_float(sorted_values: Sequence[float], fraction: float) -> float:
    if not sorted_values:
        raise RailsError("_percentile_float: empty sequence")
    return sorted_values[_percentile_index(len(sorted_values), fraction)]


def lexical_reachability_ceiling(
    snapshot: KnowledgeSnapshot,
    eval_items: Sequence[tuple[str, int, str, str]],
    *,
    k_grid: Sequence[int] = DEFAULT_K_GRID,
    near_duplicate_threshold: float = 0.8,
) -> dict[str, object]:
    """Rank every content facet against each evaluation item's own gold-side
    query text and report recall-at-k of the GOLD TOOL's facet.

    ``eval_items`` are ``(tier, item_id, query_text, gold_primary_tool)``
    tuples -- the shape ``rails.knowledge_build_a2t.PartitionProposal``
    emits.

    Returned alongside the recall curve, because a recall number means
    nothing without them: the rank position distribution of the first
    gold-tool facet, the per-tier curve, the share of the pool each item's
    gold tool occupies, the RANDOM-RANKING expectation at each k (what "the
    KB cannot help" would look like), and a NEAR-DUPLICATE AUDIT.

    The near-duplicate audit exists because the first thing a reviewer will
    say about a high ceiling on a synthetic corpus is "your knowledge base
    contains paraphrases of the evaluation items". So the ceiling is also
    reported on the subgroup of evaluation items that have NO near-duplicate
    in the construction pool (maximum token Jaccard against any content facet
    below ``near_duplicate_threshold``). That subgroup number, not the pooled
    one, is what generalizes.
    """

    if not eval_items:
        raise RailsError("lexical_reachability_ceiling: eval_items must be non-empty")
    k_values = tuple(sorted({int(k) for k in k_grid}))
    if not k_values or k_values[0] <= 0:
        raise RailsError("lexical_reachability_ceiling: k_grid must be positive ints")

    targets = content_facet_targets(snapshot)
    facet_text = {
        facet.facet_id: facet.representation
        for facet in snapshot.facets
        if facet.dimension == "content"
    }
    documents = tuple(
        (facet_id, facet_text[facet_id]) for facet_id in sorted(targets)
    )
    index = Bm25Index.build(documents)
    doc_targets = tuple(targets[doc_id] for doc_id in index.doc_ids)
    n_docs = len(index.doc_ids)
    per_tool_doc_count = Counter(doc_targets)

    doc_token_sets = tuple(frozenset(tokenize(text)) for _doc_id, text in documents)

    positions: list[int] = []
    unreachable: list[str] = []
    per_tier_hits: dict[str, Counter[int]] = defaultdict(Counter)
    per_tier_n: Counter[str] = Counter()
    hits_at_k: Counter[int] = Counter()
    random_expectation_sum: dict[int, float] = {k: 0.0 for k in k_values}
    zero_overlap = 0
    max_jaccard: list[float] = []
    novel_hits_at_k: Counter[int] = Counter()
    novel_total = 0

    for tier, item_id, query_text, gold_tool in eval_items:
        per_tier_n[tier] += 1
        gold_docs = per_tool_doc_count.get(gold_tool, 0)
        for k in k_values:
            # Probability a uniformly random ranking puts at least one of the
            # gold tool's facets in the top k.
            miss = 1.0
            for step in range(k):
                numerator = n_docs - gold_docs - step
                denominator = n_docs - step
                if numerator <= 0 or denominator <= 0:
                    miss = 0.0
                    break
                miss *= numerator / denominator
            random_expectation_sum[k] += 1.0 - miss

        scores = index.scores(query_text)
        if not scores:
            zero_overlap += 1
        # A facet can only be a near-duplicate if it shares at least one
        # token, so the BM25 candidate set is a superset of every non-zero
        # Jaccard candidate.
        query_tokens = frozenset(tokenize(query_text))
        best_jaccard = 0.0
        for doc_index in scores:
            other = doc_token_sets[doc_index]
            union = len(query_tokens | other)
            if union:
                value = len(query_tokens & other) / union
                if value > best_jaccard:
                    best_jaccard = value
        max_jaccard.append(best_jaccard)
        is_novel = best_jaccard < near_duplicate_threshold
        if is_novel:
            novel_total += 1

        ranking = index.ranking(query_text)
        position: int | None = None
        for rank, doc_index in enumerate(ranking, start=1):
            if doc_targets[doc_index] == gold_tool:
                position = rank
                break
        if position is None:
            unreachable.append(f"{tier}:{item_id:06d}")
            continue
        positions.append(position)
        for k in k_values:
            if position <= k:
                hits_at_k[k] += 1
                per_tier_hits[tier][k] += 1
                if is_novel:
                    novel_hits_at_k[k] += 1

    total = len(eval_items)
    ordered_positions = sorted(positions)
    ordered_jaccard = sorted(max_jaccard)
    return {
        "policy_id": CEILING_POLICY_ID,
        "bm25": {"k1": BM25_K1, "b": BM25_B, "tokenizer": "lowercase [a-z0-9]+ runs"},
        "population": total,
        "content_facets_ranked": n_docs,
        "gold_tool_present_in_pool": total - len(unreachable),
        "unreachable_sample_ids": unreachable,
        "zero_lexical_overlap_items": zero_overlap,
        "recall_at_k": {str(k): hits_at_k.get(k, 0) / total for k in k_values},
        "hits_at_k": {str(k): hits_at_k.get(k, 0) for k in k_values},
        "random_ranking_expectation_at_k": {
            str(k): random_expectation_sum[k] / total for k in k_values
        },
        "position": {
            "median": _percentile(ordered_positions, 0.5) if ordered_positions else None,
            "p90": _percentile(ordered_positions, 0.9) if ordered_positions else None,
            "max": ordered_positions[-1] if ordered_positions else None,
            "min": ordered_positions[0] if ordered_positions else None,
        },
        "recall_at_k_by_tier": {
            tier: {
                str(k): per_tier_hits[tier].get(k, 0) / per_tier_n[tier] for k in k_values
            }
            for tier in sorted(per_tier_n)
        },
        "population_by_tier": dict(sorted(per_tier_n.items())),
        "near_duplicate_audit": {
            "threshold": near_duplicate_threshold,
            "metric": "maximum token-set Jaccard against any construction content facet",
            "max_jaccard": {
                "median": ordered_jaccard[len(ordered_jaccard) // 2],
                "p90": _percentile_float(ordered_jaccard, 0.9),
                "max": ordered_jaccard[-1],
                "min": ordered_jaccard[0],
            },
            "share_at_or_above": {
                "0.9": sum(1 for value in max_jaccard if value >= 0.9) / total,
                "0.8": sum(1 for value in max_jaccard if value >= 0.8) / total,
                "0.5": sum(1 for value in max_jaccard if value >= 0.5) / total,
            },
            "novel_subgroup_population": novel_total,
            "novel_subgroup_recall_at_k": (
                {str(k): novel_hits_at_k.get(k, 0) / novel_total for k in k_values}
                if novel_total
                else {}
            ),
        },
    }


def gate_verdict(
    ceiling: Mapping[str, object], *, gate_k: int = 5, a0_tool_accuracy: float = 0.5425
) -> dict[str, object]:
    """The registered G0 gate: the lexical ceiling at ``gate_k`` must EXCEED
    the A0 direct-decode tool accuracy, else the campaign STOPS before any
    contact (campaign plan section 3.6)."""

    recall = ceiling["recall_at_k"]
    if not isinstance(recall, Mapping) or str(gate_k) not in recall:
        raise RailsError(f"ceiling carries no recall at k={gate_k}")
    measured = float(recall[str(gate_k)])
    passed = measured > a0_tool_accuracy
    return {
        "gate_k": gate_k,
        "a0_tool_accuracy": a0_tool_accuracy,
        "lexical_ceiling_at_gate_k": measured,
        "margin": measured - a0_tool_accuracy,
        "verdict": "PASS" if passed else "STOP",
        "condition": "lexical reachability ceiling at k must exceed the A0 tool accuracy",
        "authorizes": (
            "a PASS permits stage G1 to be registered later; it authorizes no flight by "
            "itself. A STOP is the registered honest outcome and is reported unsoftened."
        ),
    }


__all__ = [
    "BM25_B",
    "BM25_K1",
    "CEILING_POLICY_ID",
    "DEFAULT_K_GRID",
    "Bm25Index",
    "content_facet_targets",
    "gate_verdict",
    "lexical_reachability_ceiling",
    "tokenize",
]
