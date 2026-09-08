"""Frozen tool-tier semantic routing for Audio2Tool AgentLoop flights.

The index is fit only from caller-supplied construction rows and their pinned
vectors.  Query vectors enter after the index is frozen.  This module performs
no embedding, model, network, scorer, or file-system contact, and it never
renders construction examples into a model prompt.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``fuse_semantic_rankings`` is catalog id
``saea-tool-a2t-semantic-ranking-fusion-v1`` on the ``SUPPLY`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import math
from numbers import Real
from typing import Mapping, Sequence

from .knowledge_build_a2t import A2tKbRow


RRF_CONSTANT = 60


class SemanticRouterError(ValueError):
    """The construction index, query vector, or fusion input is malformed."""


@dataclass(frozen=True)
class RankedTool:
    """One selected tool and its deterministic semantic score."""

    tool_name: str
    rank: int
    score: float | None
    supported_by_construction: bool


@dataclass(frozen=True)
class SemanticRanking:
    """A complete private ranking plus the bounded selected prefix."""

    selected: tuple[RankedTool, ...]
    full_ranked_tool_names: tuple[str, ...]
    index_sha256: str
    query_vector_sha256: str

    @property
    def selected_tool_names(self) -> tuple[str, ...]:
        return tuple(item.tool_name for item in self.selected)


@dataclass(frozen=True)
class FusedSemanticRanking:
    """Reciprocal-rank fusion over complete rankings from one frozen index."""

    selected_tool_names: tuple[str, ...]
    full_ranked_tool_names: tuple[str, ...]
    source_names: tuple[str, ...]
    index_sha256: str
    rrf_constant: int
    fusion_sha256: str


def _hash_field(digest: object, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _validate_vector(raw: Sequence[Real], *, context: str) -> object:
    import numpy as np

    if isinstance(raw, (str, bytes)):
        raise SemanticRouterError(f"{context} must be a non-empty numeric sequence")
    try:
        vector = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise SemanticRouterError(
            f"{context} must contain finite numeric values"
        ) from error
    if vector.ndim != 1 or vector.size == 0:
        raise SemanticRouterError(f"{context} must be a non-empty numeric sequence")
    try:
        if any(isinstance(value, bool) for value in raw):
            raise SemanticRouterError(
                f"{context} must contain finite non-boolean numeric values"
            )
    except TypeError as error:
        raise SemanticRouterError(
            f"{context} must be a non-empty numeric sequence"
        ) from error
    if not bool(np.isfinite(vector).all()):
        raise SemanticRouterError(f"{context} must contain finite numeric values")
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0.0:
        raise SemanticRouterError(f"{context} must have nonzero finite norm")
    return vector


class ToolTierSemanticIndex:
    """Maximum-cosine index over normalized build-only tool-tier centroids."""

    def __init__(
        self,
        *,
        construction_rows: tuple[A2tKbRow, ...],
        registry_tool_names: tuple[str, ...],
        dimension: int,
        centroid_rows: tuple[object, ...],
        centroid_tool_names: tuple[str, ...],
        index_sha256: str,
    ) -> None:
        import numpy as np

        self.construction_rows = construction_rows
        self.registry_tool_names = registry_tool_names
        self.dimension = dimension
        self._centroid_matrix = np.asarray(centroid_rows, dtype=np.float64)
        self._centroid_tool_names = centroid_tool_names
        self.index_sha256 = index_sha256

    @property
    def tool_tier_centroid_count(self) -> int:
        return len(self._centroid_tool_names)

    @classmethod
    def build(
        cls,
        *,
        construction_rows: Sequence[A2tKbRow],
        vectors_by_unit_id: Mapping[str, Sequence[Real]],
        registry_tool_names: Sequence[str],
    ) -> ToolTierSemanticIndex:
        import numpy as np

        if (
            isinstance(construction_rows, (str, bytes))
            or not isinstance(construction_rows, Sequence)
            or not construction_rows
        ):
            raise SemanticRouterError("construction_rows must be non-empty")
        rows = tuple(
            sorted(construction_rows, key=lambda value: getattr(value, "unit_id", ""))
        )
        if any(not isinstance(row, A2tKbRow) for row in rows):
            raise SemanticRouterError("construction_rows must contain A2tKbRow values")
        unit_ids = tuple(row.unit_id for row in rows)
        if any(not value for value in unit_ids) or len(unit_ids) != len(set(unit_ids)):
            raise SemanticRouterError(
                "construction_rows have malformed or duplicate unit ids"
            )
        if any(row.call_count != 1 + len(row.extra_call_names) for row in rows):
            raise SemanticRouterError("construction_rows have inconsistent call labels")

        if isinstance(registry_tool_names, (str, bytes)) or not isinstance(
            registry_tool_names, Sequence
        ):
            raise SemanticRouterError("registry_tool_names must be a sequence")
        registry = tuple(sorted(registry_tool_names))
        if (
            not registry
            or len(registry) != len(set(registry))
            or any(not isinstance(name, str) or not name for name in registry)
        ):
            raise SemanticRouterError(
                "registry_tool_names must contain unique non-empty names"
            )
        unknown = sorted(
            {
                name
                for row in rows
                for name in (row.tool_name, *row.extra_call_names)
                if name not in registry
            }
        )
        if unknown:
            raise SemanticRouterError(
                f"construction_rows contain unknown registry labels: {unknown!r}"
            )

        if not isinstance(vectors_by_unit_id, Mapping) or set(
            vectors_by_unit_id
        ) != set(unit_ids):
            raise SemanticRouterError(
                "vectors_by_unit_id must exactly cover construction unit ids"
            )
        normalized: dict[str, object] = {}
        dimension: int | None = None
        for unit_id in unit_ids:
            vector = _validate_vector(
                vectors_by_unit_id[unit_id], context=f"vector {unit_id!r}"
            )
            if dimension is None:
                dimension = int(vector.size)
            elif int(vector.size) != dimension:
                raise SemanticRouterError(
                    "all construction vectors must share one dimension"
                )
            normalized[unit_id] = vector / np.linalg.norm(vector)
        assert dimension is not None

        members: dict[tuple[str, str], list[object]] = defaultdict(list)
        for row in rows:
            for tool_name in dict.fromkeys((row.tool_name, *row.extra_call_names)):
                members[(tool_name, row.tier)].append(normalized[row.unit_id])

        centroid_rows: list[object] = []
        centroid_tool_names: list[str] = []
        digest = hashlib.sha256()
        _hash_field(digest, b"saea-a2t-tool-tier-semantic-index-v1")
        _hash_field(digest, dimension.to_bytes(8, "big"))
        for name in registry:
            _hash_field(digest, name.encode("utf-8"))
        for (tool_name, tier), values in sorted(members.items()):
            centroid = np.asarray(values, dtype=np.float64).mean(axis=0)
            norm = float(np.linalg.norm(centroid))
            if not math.isfinite(norm) or norm == 0.0:
                raise SemanticRouterError(
                    f"tool-tier centroid {tool_name!r}/{tier!r} has zero norm"
                )
            centroid = centroid / norm
            centroid_rows.append(centroid)
            centroid_tool_names.append(tool_name)
            _hash_field(digest, tool_name.encode("utf-8"))
            _hash_field(digest, tier.encode("utf-8"))
            _hash_field(digest, centroid.astype(">f8", copy=False).tobytes())
        if not centroid_rows:
            raise SemanticRouterError("construction_rows produced no centroids")
        return cls(
            construction_rows=rows,
            registry_tool_names=registry,
            dimension=dimension,
            centroid_rows=tuple(centroid_rows),
            centroid_tool_names=tuple(centroid_tool_names),
            index_sha256=digest.hexdigest(),
        )

    def rank(self, query_vector: Sequence[Real], *, top_k: int) -> SemanticRanking:
        import numpy as np

        if (
            type(top_k) is not int
            or top_k <= 0
            or top_k > len(self.registry_tool_names)
        ):
            raise SemanticRouterError(
                "top_k must be a positive integer no larger than the registry"
            )
        query = _validate_vector(query_vector, context="query_vector")
        if int(query.size) != self.dimension:
            raise SemanticRouterError(
                f"query_vector dimension {int(query.size)} != index dimension {self.dimension}"
            )
        query_bytes = query.astype(">f8", copy=False).tobytes()
        query_sha256 = hashlib.sha256(query_bytes).hexdigest()
        query = query / np.linalg.norm(query)
        centroid_scores = self._centroid_matrix @ query
        scores = {name: -math.inf for name in self.registry_tool_names}
        for index, tool_name in enumerate(self._centroid_tool_names):
            scores[tool_name] = max(scores[tool_name], float(centroid_scores[index]))
        full = tuple(
            sorted(
                self.registry_tool_names,
                key=lambda tool_name: (-scores[tool_name], tool_name),
            )
        )
        selected = tuple(
            RankedTool(
                tool_name=tool_name,
                rank=rank,
                score=(scores[tool_name] if math.isfinite(scores[tool_name]) else None),
                supported_by_construction=math.isfinite(scores[tool_name]),
            )
            for rank, tool_name in enumerate(full[:top_k], start=1)
        )
        return SemanticRanking(
            selected=selected,
            full_ranked_tool_names=full,
            index_sha256=self.index_sha256,
            query_vector_sha256=query_sha256,
        )


def fuse_semantic_rankings(
    rankings: Sequence[SemanticRanking],
    *,
    top_k: int,
    source_names: Sequence[str],
    constant: int = RRF_CONSTANT,
) -> FusedSemanticRanking:
    """Fuse complete rankings without reading labels or raw query text."""

    if (
        isinstance(rankings, (str, bytes))
        or not isinstance(rankings, Sequence)
        or not rankings
        or any(not isinstance(value, SemanticRanking) for value in rankings)
    ):
        raise SemanticRouterError("rankings must contain SemanticRanking values")
    sources = tuple(source_names)
    if (
        len(sources) != len(rankings)
        or len(sources) != len(set(sources))
        or any(not isinstance(name, str) or not name for name in sources)
    ):
        raise SemanticRouterError(
            "source_names must uniquely name every supplied ranking"
        )
    if type(constant) is not int or constant <= 0:
        raise SemanticRouterError("RRF constant must be a positive integer")
    first = rankings[0]
    if any(value.index_sha256 != first.index_sha256 for value in rankings):
        raise SemanticRouterError("all rankings must come from the same index")
    registry = first.full_ranked_tool_names
    if any(
        len(value.full_ranked_tool_names) != len(registry)
        or set(value.full_ranked_tool_names) != set(registry)
        or len(value.full_ranked_tool_names) != len(set(value.full_ranked_tool_names))
        for value in rankings
    ):
        raise SemanticRouterError("all rankings must cover the same unique registry")
    if type(top_k) is not int or top_k <= 0 or top_k > len(registry):
        raise SemanticRouterError(
            "top_k must be a positive integer no larger than the registry"
        )
    ranks = [
        {
            tool_name: rank
            for rank, tool_name in enumerate(value.full_ranked_tool_names, 1)
        }
        for value in rankings
    ]
    scores = {
        tool_name: sum(1.0 / (constant + rank[tool_name]) for rank in ranks)
        for tool_name in registry
    }
    full = tuple(sorted(registry, key=lambda name: (-scores[name], name)))
    digest = hashlib.sha256()
    _hash_field(digest, b"saea-a2t-semantic-ranking-fusion-v1")
    _hash_field(digest, first.index_sha256.encode("ascii"))
    _hash_field(digest, constant.to_bytes(8, "big"))
    for source_name, ranking in zip(sources, rankings, strict=True):
        _hash_field(digest, source_name.encode("utf-8"))
        _hash_field(digest, ranking.query_vector_sha256.encode("ascii"))
        for tool_name in ranking.full_ranked_tool_names:
            _hash_field(digest, tool_name.encode("utf-8"))
    return FusedSemanticRanking(
        selected_tool_names=full[:top_k],
        full_ranked_tool_names=full,
        source_names=sources,
        index_sha256=first.index_sha256,
        rrf_constant=constant,
        fusion_sha256=digest.hexdigest(),
    )


__all__ = [
    "FusedSemanticRanking",
    "RRF_CONSTANT",
    "RankedTool",
    "SemanticRanking",
    "SemanticRouterError",
    "ToolTierSemanticIndex",
    "fuse_semantic_rankings",
]
