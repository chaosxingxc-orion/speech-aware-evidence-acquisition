"""The vectorised pre-selection in ``rails.kb_policy.multidim_recall``.

What is pinned here. The exact loop scored every key vector with a
builtin-``sum`` dot product -- 1.1-1.4 s per row on the SLURP exemplar store,
on the event loop every in-flight row shares (owner decision 159's gap
decomposition). The repair lets a BLAS product choose WHICH rows the exact
loop re-scores (every row within ``2 * _PRESELECT_SLACK`` of the k-th BLAS
cosine) and delivers only exact-loop floats. The requirement is the delivered
recall -- the same facets, the same order, the same score bits -- never the
BLAS floats, which differ from the exact loop's in the last bits.

Every comparison is BITWISE on the full returned mapping, insertion order
included, against the exact loop (the pre-selection switched off) and against
the per-pair oracle as the module read before either cache existed.

Zero model, GPU, network and embedding contacts. The two real-roster tests read
sealed vectors from ``SPEECHRL_DATA_DIR`` and skip where it is absent.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import struct
from pathlib import Path
from typing import Mapping, Sequence

import pytest

from speech_aware_evidence_acquisition.rails import kb_policy
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)

_SHA_C = "c" * 64


@pytest.fixture(autouse=True)
def _fresh_caches(monkeypatch):
    """Each test starts with empty module caches and leaves the real ones alone."""

    monkeypatch.setattr(kb_policy, "_KEY_MATRICES", kb_policy._KeyMatrixCache())
    monkeypatch.setattr(kb_policy, "_KEY_NORMS", kb_policy._KeyNormCache())


# ---------------------------------------------------------------------------
# Oracles
# ---------------------------------------------------------------------------


def _reference_cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """The per-pair cosine as ``rails.kb_policy._cosine`` read at ``2afb4b5c``."""

    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    norm_a = math.sqrt(sum(float(x) * float(x) for x in a))
    norm_b = math.sqrt(sum(float(y) * float(y) for y in b))
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _reference_recall(snapshot, query_vectors, facet_vectors, k):
    """The cosine-only recall loop at ``2afb4b5c`` (no cache, no pre-selection)."""

    recalled: dict[str, dict[str, float]] = {}
    for dimension in sorted({facet.dimension for facet in snapshot.facets}):
        if dimension in kb_policy.PRIOR_MASS_DIMENSIONS:
            continue
        query = query_vectors.get(dimension)
        if query is None:
            continue
        scored = []
        for facet in sorted(
            (f for f in snapshot.facets if f.dimension == dimension),
            key=lambda f: f.facet_id,
        ):
            vector = facet_vectors(facet.facet_id).get(dimension)
            if vector is None:
                continue
            score = _reference_cosine(query, vector)
            if score > 0.0:
                scored.append((score, facet.facet_id))
        scored.sort(key=lambda item: (-item[0], item[1]))
        for score, facet_id in scored[:k]:
            recalled.setdefault(facet_id, {})[dimension] = score
    return recalled


def _exact_recall(monkeypatch, *args):
    """``multidim_recall`` with the pre-selection switched off: the exact loop."""

    with monkeypatch.context() as patch:
        patch.setattr(kb_policy, "_preselected_exact_scores", lambda *a, **k: None)
        return kb_policy.multidim_recall(*args)


def _bits(recalled: Mapping[str, Mapping[str, float]]):
    """The mapping as an ordered list with every score's IEEE-754 bytes."""

    return [
        (
            facet_id,
            [(dim, struct.pack("<d", score).hex()) for dim, score in dims.items()],
        )
        for facet_id, dims in recalled.items()
    ]


# ---------------------------------------------------------------------------
# Synthetic snapshots
# ---------------------------------------------------------------------------


def _snapshot(
    count: int, prefix: str = "u", dimension: str = "content"
) -> KnowledgeSnapshot:
    facets, values = [], []
    for index in range(count):
        facet_id = f"facet:{dimension}:{prefix}{index:04d}"
        facets.append(
            KeyFacet(
                facet_id=facet_id,
                dimension=dimension,
                representation=f'TRAIN utterance {prefix}{index:04d}: "utterance {index}"',
                representation_kind="text",
                source_sample_ids=(f"train:{prefix}{index:04d}",),
            ).validate()
        )
        values.append(
            ValueBundle(
                value_id=f"value:{prefix}{index:04d}",
                content=f"TRAIN utterance {prefix}{index:04d}.",
                associated_facet_ids=(facet_id,),
                source_sample_ids=(f"train:{prefix}{index:04d}",),
                provenance_refs=(f"utterance:{prefix}{index:04d}",),
                task_target=f"target_{index % 5}",
                prior_score=0.5,
            ).validate()
        )
    return KnowledgeSnapshot(
        snapshot_id=f"vectorised-recall-test-{prefix}",
        source_split_identity_hash=_SHA_C,
        source_sample_ids=tuple(f"train:{prefix}{index:04d}" for index in range(count)),
        builder_policy_id="saea-kb-distmodel-v1",
        facets=tuple(facets),
        values=tuple(values),
    ).validate()


def _near_tie_fixture(seed: int, width: int = 2048):
    """A cluster of keys that are PERMUTATIONS of one base vector, recalled by a
    constant query: every cosine in the cluster is the same real number, and
    the floats differ only by summation-order rounding -- the near-ties (and
    exact ties, resolved by facet id) a BLAS order and the builtin ``sum``
    break differently. Exact value duplicates as distinct tuple objects, a
    zero-norm key and a background of unrelated keys complete it."""

    rng = random.Random(seed)
    base = [rng.random() + 0.05 for _ in range(width)]
    cluster = []
    for _ in range(180):
        permuted = base[:]
        rng.shuffle(permuted)
        cluster.append(tuple(permuted))
    cluster.extend(
        tuple(list(cluster[i])) for i in (3, 3, 17, 90)
    )  # equal values, new objects
    background = [tuple(rng.gauss(0.0, 1.0) for _ in range(width)) for _ in range(120)]
    keys = cluster + background + [tuple(0.0 for _ in range(width))]
    order = list(range(len(keys)))
    rng.shuffle(order)  # the cluster is spread across facet ids, not a prefix
    snapshot = _snapshot(len(keys), prefix=f"s{seed}")
    content_ids = [f.facet_id for f in snapshot.facets]
    table = {
        content_ids[slot]: {"content": keys[index]} for slot, index in enumerate(order)
    }
    queries = [
        tuple(1.0 for _ in range(width)),
        tuple(0.37 for _ in range(width)),
        tuple(base),
    ]
    return snapshot, table, queries


# ---------------------------------------------------------------------------
# (1) near-ties: identical to the exact loop, bit for bit, at every k
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [20260927, 7, 11])
def test_near_tie_fixture_recall_is_bitwise_the_exact_loop(monkeypatch, seed):
    import numpy as np

    snapshot, table, queries = _near_tie_fixture(seed)
    lookup = lambda fid: table.get(fid, {})  # noqa: E731
    blas_disagrees = False
    blas_order_differs = False
    for query in queries:
        for k in (1, 5, 8, 20, 60, 183, 184, 185, 300, 500):
            fast = kb_policy.multidim_recall(snapshot, {"content": query}, lookup, k)
            exact = _exact_recall(monkeypatch, snapshot, {"content": query}, lookup, k)
            assert _bits(fast) == _bits(exact), (seed, k)
            assert _bits(exact) == _bits(
                _reference_recall(snapshot, {"content": query}, lookup, k)
            )
        # The fixture bites: the BLAS floats differ from the exact ones, and
        # ranking by them alone would deliver a different ordered list.
        ids = sorted(table)
        matrix = np.array([table[fid]["content"] for fid in ids], dtype=np.float64)
        norms = np.array([kb_policy._l2_norm(table[fid]["content"]) for fid in ids])
        qn = kb_policy._l2_norm(query)
        with np.errstate(divide="ignore", invalid="ignore"):
            approx = (matrix @ np.array(query)) / (norms * qn)
        exact_scores = [_reference_cosine(query, table[fid]["content"]) for fid in ids]
        blas_disagrees |= any(
            float(a) != e for a, e, n in zip(approx, exact_scores, norms) if n > 0
        )
        blas_rank = sorted(
            (i for i in range(len(ids)) if norms[i] > 0 and approx[i] > 0),
            key=lambda i: (-float(approx[i]), ids[i]),
        )[:60]
        exact_rank = sorted(
            (i for i in range(len(ids)) if exact_scores[i] > 0),
            key=lambda i: (-exact_scores[i], ids[i]),
        )[:60]
        blas_order_differs |= blas_rank != exact_rank
    assert blas_disagrees
    assert blas_order_differs


def test_segment_recall_is_bitwise_the_exact_loop(monkeypatch):
    snapshot, table, queries = _near_tie_fixture(5, width=512)
    lookup = lambda fid: table.get(fid, {})  # noqa: E731
    segments = [{"content": query} for query in queries]
    for k in (8, 16, 60):
        fast = kb_policy.multidim_segment_recall(snapshot, segments, lookup, k)
        with monkeypatch.context() as patch:
            patch.setattr(kb_policy, "_preselected_exact_scores", lambda *a, **kw: None)
            exact = kb_policy.multidim_segment_recall(snapshot, segments, lookup, k)
        assert _bits(fast) == _bits(exact)


# ---------------------------------------------------------------------------
# (2) the exact loop still runs wherever the pre-selection does not apply
# ---------------------------------------------------------------------------


def _random_table(snapshot, rng, width, convert=tuple):
    return {
        f.facet_id: {"content": convert(rng.uniform(-1.0, 1.0) for _ in range(width))}
        for f in snapshot.facets
    }


def test_list_vectors_take_the_exact_loop_and_build_no_matrix(monkeypatch):
    rng = random.Random(1)
    snapshot = _snapshot(40)
    table = _random_table(snapshot, rng, 32, convert=list)
    lookup = lambda fid: table.get(fid, {})  # noqa: E731
    query = {"content": tuple(rng.uniform(-1.0, 1.0) for _ in range(32))}
    assert _bits(kb_policy.multidim_recall(snapshot, query, lookup, 7)) == _bits(
        _reference_recall(snapshot, query, lookup, 7)
    )
    assert len(kb_policy._KEY_MATRICES) == 0


@pytest.mark.parametrize(
    "poison",
    [
        lambda v: (1,) + v[1:],  # an int component
        lambda v: (float("nan"),) + v[1:],
        lambda v: (float("inf"),) + v[1:],
        lambda v: (1e300,) + v[1:],  # a norm out of the proven range
    ],
)
def test_a_refused_key_set_is_remembered_and_scored_by_the_exact_loop(
    monkeypatch, poison
):
    rng = random.Random(2)
    snapshot = _snapshot(30)
    table = _random_table(snapshot, rng, 24)
    first = snapshot.facets[4].facet_id
    table[first] = {"content": poison(table[first]["content"])}
    lookup = lambda fid: table.get(fid, {})  # noqa: E731
    query = {"content": tuple(rng.uniform(-1.0, 1.0) for _ in range(24))}
    for _ in range(2):
        got = kb_policy.multidim_recall(snapshot, query, lookup, 6)
        assert _bits(got) == _bits(
            _exact_recall(monkeypatch, snapshot, query, lookup, 6)
        )
    assert len(kb_policy._KEY_MATRICES) == 1
    assert kb_policy._KEY_MATRICES._entries[0].matrix is None


def test_query_edge_cases_match_the_exact_loop(monkeypatch):
    rng = random.Random(3)
    snapshot = _snapshot(25)
    table = _random_table(snapshot, rng, 16)
    table[snapshot.facets[0].facet_id] = {"content": tuple(0.0 for _ in range(16))}
    lookup = lambda fid: table.get(fid, {})  # noqa: E731
    for query in (
        tuple(0.0 for _ in range(16)),  # zero query: nothing admitted
        tuple([2] + [0.5] * 15),  # an int component: exact loop
        tuple(rng.uniform(-1.0, 1.0) for _ in range(16)),
        [rng.uniform(-1.0, 1.0) for _ in range(16)],  # a list query is fine
        tuple(rng.uniform(-1.0, 1.0) for _ in range(15)),  # wrong width: skipped
    ):
        for k in (1, 3, 24, 25, 40):
            fast = kb_policy.multidim_recall(snapshot, {"content": query}, lookup, k)
            exact = _exact_recall(monkeypatch, snapshot, {"content": query}, lookup, k)
            assert _bits(fast) == _bits(exact)


# ---------------------------------------------------------------------------
# (3) the matrix cache: identity-keyed, built once, bounded
# ---------------------------------------------------------------------------


def test_the_matrix_is_built_once_per_key_set_and_matched_by_identity(monkeypatch):
    rng = random.Random(4)
    snapshot = _snapshot(20)
    table = _random_table(snapshot, rng, 8)
    lookup = lambda fid: table.get(fid, {})  # noqa: E731
    query = {"content": tuple(rng.uniform(-1.0, 1.0) for _ in range(8))}
    first = kb_policy.multidim_recall(snapshot, query, lookup, 5)
    assert len(kb_policy._KEY_MATRICES) == 1
    # A hit never rebuilds.
    with monkeypatch.context() as patch:
        patch.setattr(kb_policy, "_build_key_matrix", lambda v: pytest.fail("rebuilt"))
        assert _bits(kb_policy.multidim_recall(snapshot, query, lookup, 5)) == _bits(
            first
        )
    # Equal VALUES in new objects are a different key set: rebuilt, not aliased.
    copied = {
        fid: {"content": tuple(list(row["content"]))} for fid, row in table.items()
    }
    kb_policy.multidim_recall(snapshot, query, lambda fid: copied.get(fid, {}), 5)
    assert len(kb_policy._KEY_MATRICES) == 2
    # Bounded: the least recently used key set is dropped past four.
    for seed in range(4):
        other = _random_table(snapshot, random.Random(100 + seed), 8)
        kb_policy.multidim_recall(
            snapshot, query, lambda fid, t=other: t.get(fid, {}), 5
        )
    assert len(kb_policy._KEY_MATRICES) == 4
    assert (
        kb_policy._KEY_MATRICES.get(
            tuple(table[f.facet_id]["content"] for f in snapshot.facets)
        )
        is None
    )


def test_the_key_norm_cache_keeps_its_contract():
    """``_KEY_NORMS`` still holds exactly the key set the last recall touched."""

    rng = random.Random(6)
    snapshot = _snapshot(12)
    table = _random_table(snapshot, rng, 16)
    lookup = lambda fid: table.get(fid, {})  # noqa: E731
    kb_policy.multidim_recall(
        snapshot, {"content": tuple(rng.random() for _ in range(16))}, lookup, 3
    )
    assert set(kb_policy._KEY_NORMS._entries) == {
        id(row["content"]) for row in table.values()
    }


# ---------------------------------------------------------------------------
# (4) real sealed vectors (SPEECHRL_DATA_DIR)
# ---------------------------------------------------------------------------


def _data_root() -> Path | None:
    raw = os.environ.get("SPEECHRL_DATA_DIR", "").strip()
    root = Path(raw) if raw else None
    return root if root is not None and root.is_dir() else None


requires_data_root = pytest.mark.skipif(
    _data_root() is None, reason="SPEECHRL_DATA_DIR is not materialised on this host"
)

_EXEMPLAR_SNAPSHOT = (
    "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
)
_EXEMPLAR_FACETS = "vectors/slurp-kus3/facet-vectors.jsonl"
_FOLD_A_CONTENT = "vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl"
_IB_SNAPSHOT = "knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json"
_IB_FACETS = "prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl"
_FOLD_A_SEGMENTS = "vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl"


def _head_vectors(path: Path, lines: int, dimension: str):
    """The first ``lines`` rows of a sealed vector file, parsed exactly as
    ``load_sealed_vectors`` parses them (tuples of ``float``)."""

    table = {}
    with path.open(encoding="utf-8") as handle:
        for _ in range(lines):
            document = json.loads(handle.readline())
            table[document["id"]] = {
                dimension: tuple(float(v) for v in document["vectors"][dimension])
            }
    return table


def _snapshot_at(root: Path, relpath: str) -> KnowledgeSnapshot:
    return KnowledgeSnapshot.from_frozen_json(
        json.loads((root / relpath).read_text(encoding="utf-8"))
    )


@requires_data_root
def test_real_exemplar_store_sample_is_bitwise_the_exact_loop(monkeypatch):
    """The first 1,500 sealed exemplar key vectors (the store's own snapshot;
    facets without a loaded vector are skipped by both paths alike) against 24
    sealed Fold A speech queries, at every k the committed configs use."""

    root = _data_root()
    snapshot = _snapshot_at(root, _EXEMPLAR_SNAPSHOT)
    facets = _head_vectors(root / _EXEMPLAR_FACETS, 1500, "content")
    queries = _head_vectors(root / _FOLD_A_CONTENT, 24, "content")
    lookup = lambda fid: facets.get(fid, {})  # noqa: E731
    compared = 0
    for query in queries.values():
        for k in (8, 20, 60):
            fast = kb_policy.multidim_recall(snapshot, dict(query), lookup, k)
            exact = _exact_recall(monkeypatch, snapshot, dict(query), lookup, k)
            assert _bits(fast) == _bits(exact)
            assert 0 < len(fast) <= k
            compared += 1
    assert compared == 72


@requires_data_root
def test_real_intent_boundary_store_fold_a_is_bitwise_the_exact_loop(monkeypatch):
    """Every sealed Fold A segment query against the 60 released intent-boundary
    keys, through the segment recall the first-phase supply uses."""

    from speech_aware_evidence_acquisition.rails.phase_supply import (
        load_sealed_segment_vectors,
        load_sealed_vectors,
    )

    root = _data_root()

    def sha(relpath):
        return hashlib.sha256((root / relpath).read_bytes()).hexdigest()

    snapshot = _snapshot_at(root, _IB_SNAPSHOT)
    facets = load_sealed_vectors(
        root / _IB_FACETS,
        expected_sha256=sha(_IB_FACETS),
        dimensions=["intent-boundary"],
    )
    queries = load_sealed_segment_vectors(
        root / _FOLD_A_SEGMENTS,
        expected_sha256=sha(_FOLD_A_SEGMENTS),
        dimensions=["intent-boundary"],
    )
    lookup = lambda fid: facets.get(fid, {})  # noqa: E731
    assert len(queries) == 1080
    for record in queries.values():
        for k in (8, 60):
            fast = kb_policy.multidim_segment_recall(
                snapshot, record.segments, lookup, k
            )
            with monkeypatch.context() as patch:
                patch.setattr(
                    kb_policy, "_preselected_exact_scores", lambda *a, **kw: None
                )
                exact = kb_policy.multidim_segment_recall(
                    snapshot, record.segments, lookup, k
                )
            assert _bits(fast) == _bits(exact)
