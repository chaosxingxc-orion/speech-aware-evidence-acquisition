"""The key-norm cache in ``rails.kb_policy`` (KU-S3 preregistration of
2026-09-07, section 5: the "bit-exact 3x" that was named, priced and left to
the coordinator).

What is pinned here. ``rails.kb_policy._cosine`` at commit ``2afb4b5c``
recomputed BOTH L2 norms for every pair, which priced the KU-S3 pre-flight
seed at 2.28 s per sample over 11,514 content facets of 2,048 floats. The
repair computes each key vector's norm once, in the same arithmetic (same
builtin ``sum`` in the same element order, same ``math.sqrt``), so every
cosine is the IDENTICAL float and every selection is byte-identical. The
per-pair formula as it read at ``2afb4b5c`` is kept HERE as the oracle
(:func:`_reference_cosine`), never in the module.

Zero model, GPU, network and embedding contacts; random vectors and a
synthetic snapshot only.
"""

from __future__ import annotations

import json
import math
import random
import struct
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping, Sequence

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import kb_policy
from speech_aware_evidence_acquisition.rails import phase_supply as ps
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)

_SHA_C = "c" * 64


# ---------------------------------------------------------------------------
# The oracle: the per-pair formula exactly as the module read at 2afb4b5c
# ---------------------------------------------------------------------------


def _reference_cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """``rails.kb_policy._cosine`` at ``2afb4b5c``, verbatim: both norms
    recomputed for every pair."""

    if not isinstance(a, Sequence) or not isinstance(b, Sequence):
        return 0.0
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    norm_a = math.sqrt(sum(float(x) * float(x) for x in a))
    norm_b = math.sqrt(sum(float(y) * float(y) for y in b))
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _reference_recall(
    snapshot: KnowledgeSnapshot,
    query_vectors: Mapping[str, Sequence[float] | None],
    facet_vectors,
    top_k_per_dimension: int,
) -> dict[str, dict[str, float]]:
    """``rails.kb_policy.multidim_recall``'s cosine branch at ``2afb4b5c``,
    scored through :func:`_reference_cosine`; prior-mass dimensions exactly
    as the module still does them."""

    values_by_facet: dict[str, list[ValueBundle]] = {}
    for value in snapshot.values:
        for facet_id in value.associated_facet_ids:
            values_by_facet.setdefault(facet_id, []).append(value)
    recalled: dict[str, dict[str, float]] = {}
    for dimension in sorted({facet.dimension for facet in snapshot.facets}):
        dim_facets = sorted(
            (facet for facet in snapshot.facets if facet.dimension == dimension),
            key=lambda facet: facet.facet_id,
        )
        scored: list[tuple[float, str]] = []
        if dimension in kb_policy.PRIOR_MASS_DIMENSIONS:
            for facet in dim_facets:
                associated = values_by_facet.get(facet.facet_id, ())
                masses = [v.prior_score for v in associated if v.prior_score is not None]
                mass = max(masses) if masses else 0.0
                if mass > 0.0:
                    scored.append((mass, facet.facet_id))
        else:
            query_vector = query_vectors.get(dimension)
            if query_vector is None:
                continue
            for facet in dim_facets:
                facet_vector = facet_vectors(facet.facet_id).get(dimension)
                if facet_vector is None:
                    continue
                score = _reference_cosine(query_vector, facet_vector)
                if score > 0.0:
                    scored.append((score, facet.facet_id))
        scored.sort(key=lambda item: (-item[0], item[1]))
        for score, facet_id in scored[:top_k_per_dimension]:
            recalled.setdefault(facet_id, {})[dimension] = score
    return recalled


def _bits(value: float) -> str:
    """The IEEE-754 bytes of ``value``: bitwise identity, not ``==`` (which
    would call ``-0.0`` and ``0.0`` equal)."""

    return struct.pack("<d", value).hex()


def _vector(rng: random.Random, dim: int, scale: float) -> tuple[float, ...]:
    return tuple((rng.random() * 2.0 - 1.0) * scale for _ in range(dim))


# ---------------------------------------------------------------------------
# (a) bitwise identity of the cached-norm cosine over >= 10,000 pairs at 2048
# ---------------------------------------------------------------------------


def test_cached_norm_cosines_are_bitwise_the_per_pair_formula_over_ten_thousand_pairs():
    rng = random.Random(20260909)
    dim = 2048
    scales = (1.0, 0.0031, 275.0, 1e-4, 1.0)
    keys = tuple(_vector(rng, dim, scales[i % len(scales)]) for i in range(100))
    queries = tuple(_vector(rng, dim, scales[(i * 7) % len(scales)]) for i in range(100))

    cache = kb_policy._KeyNormCache()
    pairs = 0
    for query in queries:
        query_norm = kb_policy._l2_norm(query)
        for key in keys:
            cached = kb_policy._cosine_with_norms(query, key, query_norm, cache.norm(key))
            assert _bits(cached) == _bits(_reference_cosine(query, key))
            pairs += 1
    assert pairs == 10_000
    # One entry per key vector: every key's norm was computed once and hit
    # 99 times; the 100 query norms were computed once per query.
    assert len(cache) == 100
    # A hit is the oracle's own norm arithmetic, and it never recomputes.
    first_key = keys[0]
    oracle_norm = math.sqrt(sum(float(x) * float(x) for x in first_key))
    assert _bits(cache.norm(first_key)) == _bits(oracle_norm)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(kb_policy, "_l2_norm", lambda _vector: pytest.fail("cache miss"))
        assert _bits(cache.norm(first_key)) == _bits(oracle_norm)


def test_the_public_cosine_is_the_same_formula_as_the_oracle():
    """``_cosine`` is what every vectorised analysis pins itself to; it must
    keep returning the oracle's bits and the oracle's guards."""

    rng = random.Random(7)
    keys = tuple(_vector(rng, 2048, 1.0) for _ in range(20))
    queries = tuple(_vector(rng, 2048, 0.02) for _ in range(20))
    for query in queries:
        for key in keys:
            assert _bits(kb_policy._cosine(query, key)) == _bits(_reference_cosine(query, key))
    # The guards, in the oracle's order.
    zero = (0.0,) * 8
    for left, right in (
        ("not a vector", keys[0]),
        (keys[0], None),
        (keys[0][:7], keys[1]),
        ((), ()),
        (zero, keys[0][:8]),
        (keys[0][:8], zero),
    ):
        assert kb_policy._cosine(left, right) == _reference_cosine(left, right) == 0.0


# ---------------------------------------------------------------------------
# multidim_recall through the cache, cold and warm, equals the 2afb4b5c loop
# ---------------------------------------------------------------------------


def _random_snapshot(count: int, prefix: str = "u") -> KnowledgeSnapshot:
    facets = []
    values = []
    for index in range(count):
        facet_id = f"facet:content:{prefix}{index:03d}"
        facets.append(
            KeyFacet(
                facet_id=facet_id,
                dimension="content",
                representation=(
                    f'TRAIN utterance {prefix}{index:03d} (slot-filler retrieval key): '
                    f'"utterance {index}"'
                ),
                representation_kind="text",
                source_sample_ids=(f"train:{prefix}{index:03d}",),
            ).validate()
        )
        values.append(
            ValueBundle(
                value_id=f"value:{prefix}{index:03d}",
                content=(
                    f"Slot type=filler pairs observed in TRAIN utterance {prefix}{index:03d}: "
                    f"kind=k{index % 7}."
                ),
                associated_facet_ids=(facet_id,),
                source_sample_ids=(f"train:{prefix}{index:03d}",),
                provenance_refs=(f"utterance:{prefix}{index:03d}",),
                task_target=f"target_{index % 5}",
                prior_score=0.5,
            ).validate()
        )
    # One prior-mass dimension too, so the union path is covered.
    facets.append(
        KeyFacet(
            facet_id="facet:label:target_0",
            dimension="label",
            representation="target_0",
            representation_kind="text",
            source_sample_ids=(f"train:{prefix}000",),
        ).validate()
    )
    values[0] = ValueBundle(
        value_id=values[0].value_id,
        content=values[0].content,
        associated_facet_ids=(values[0].associated_facet_ids[0], "facet:label:target_0"),
        source_sample_ids=values[0].source_sample_ids,
        provenance_refs=values[0].provenance_refs,
        task_target=values[0].task_target,
        prior_score=0.5,
    ).validate()
    return KnowledgeSnapshot(
        snapshot_id=f"norm-cache-test-{prefix}",
        source_split_identity_hash=_SHA_C,
        source_sample_ids=tuple(f"train:{prefix}{index:03d}" for index in range(count)),
        builder_policy_id="saea-kb-distmodel-v1",
        facets=tuple(facets),
        values=tuple(values),
    ).validate()


def test_multidim_recall_is_bitwise_the_2afb4b5c_loop_cold_and_warm():
    rng = random.Random(20260908)
    snapshot = _random_snapshot(64)
    table = {
        facet.facet_id: {"content": _vector(rng, 256, 1.0)}
        for facet in snapshot.facets
        if facet.dimension == "content"
    }
    lookup = lambda facet_id: table.get(facet_id, {})  # noqa: E731
    for _query_index in range(3):
        query = {"content": _vector(rng, 256, 0.3)}
        expected = _reference_recall(snapshot, query, lookup, 5)
        cold_or_warm = kb_policy.multidim_recall(snapshot, query, lookup, 5)
        assert set(cold_or_warm) == set(expected)
        for facet_id, dims in expected.items():
            assert set(cold_or_warm[facet_id]) == set(dims)
            for dimension, score in dims.items():
                assert _bits(cold_or_warm[facet_id][dimension]) == _bits(score)
        assert cold_or_warm["facet:label:target_0"] == {"label": 0.5}
    # Warm: the cache holds exactly this key set, and nothing else.
    assert len(kb_policy._KEY_NORMS) == 64


def test_the_cache_is_scoped_to_one_key_set_and_never_caches_a_list():
    rng = random.Random(3)
    first = _random_snapshot(12, prefix="a")
    second = _random_snapshot(9, prefix="b")
    first_table = {
        facet.facet_id: {"content": _vector(rng, 16, 1.0)}
        for facet in first.facets
        if facet.dimension == "content"
    }
    second_table = {
        facet.facet_id: {"content": _vector(rng, 16, 1.0)}
        for facet in second.facets
        if facet.dimension == "content"
    }
    query = {"content": _vector(rng, 16, 1.0)}

    kb_policy.multidim_recall(first, query, lambda fid: first_table.get(fid, {}), 3)
    assert len(kb_policy._KEY_NORMS) == 12
    first_ids = {id(row["content"]) for row in first_table.values()}
    assert first_ids == set(kb_policy._KEY_NORMS._entries)

    # A different key set REPLACES the cache; the first set is not pinned.
    kb_policy.multidim_recall(second, query, lambda fid: second_table.get(fid, {}), 3)
    assert len(kb_policy._KEY_NORMS) == 9
    assert not (first_ids & set(kb_policy._KEY_NORMS._entries))

    # A recall that touches no key vector leaves the cache alone.
    kb_policy.multidim_recall(second, {}, lambda fid: {}, 3)
    assert len(kb_policy._KEY_NORMS) == 9

    # Mutable vectors are never cached: an in-place edit can never go stale.
    list_table = {fid: {"content": list(row["content"])} for fid, row in second_table.items()}
    list_lookup = lambda fid: list_table.get(fid, {})  # noqa: E731
    before = kb_policy.multidim_recall(second, query, list_lookup, 3)
    assert before == _reference_recall(second, query, list_lookup, 3)
    assert len(kb_policy._KEY_NORMS) == 0
    for row in list_table.values():
        row["content"][0] = row["content"][0] * 100.0 + 1.0
    after = kb_policy.multidim_recall(second, query, list_lookup, 3)
    assert after == _reference_recall(second, query, list_lookup, 3)
    assert len(kb_policy._KEY_NORMS) == 0


# ---------------------------------------------------------------------------
# (b) the seeded first-phase selection on a fixed fixture, before == after
# ---------------------------------------------------------------------------


def _fixture_rows():
    """A fixed synthetic key set and query set. Components are rounded to
    six decimals so the JSONL round trip through ``load_sealed_vectors`` is
    exact and the fixture is the same bytes on every run."""

    rng = random.Random(20260907)
    dim = 48
    snapshot = _random_snapshot(40)
    key_rows = [
        (
            facet.facet_id,
            {"content": [round(rng.random() * 2.0 - 1.0, 6) for _ in range(dim)]},
        )
        for facet in snapshot.facets
        if facet.dimension == "content"
    ]
    query_rows = [
        (
            f"dev:s{index}",
            {"content": [round(rng.random() * 2.0 - 1.0, 6) for _ in range(dim)]},
        )
        for index in range(6)
    ]
    return snapshot, key_rows, query_rows


def _write_vectors(path: Path, rows) -> str:
    import hashlib

    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(
        json.dumps({"id": entry_id, "vectors": vectors}) + "\n" for entry_id, vectors in rows
    )
    path.write_text(body, encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seeded_selection(tmp_path: Path) -> dict[str, object]:
    """The REAL seeded path: fragment-shaped ``phase_supply`` values through
    ``FlightRuntime._resolve_phase_supply`` (which loads and re-hashes the
    vector files and constructs ``kb-facet-v1``) and then
    ``rails.phase_supply.build_bootstrap_selection``."""

    snapshot, key_rows, query_rows = _fixture_rows()
    query_sha = _write_vectors(tmp_path / "v" / "q.jsonl", query_rows)
    facet_sha = _write_vectors(tmp_path / "v" / "f.jsonl", key_rows)
    program = rc.default_phase_program("phase-slots-given-intent-supplied-v1")
    values = {
        "phase_supply": {
            "slots": {
                "provider": "kb-facet-v1",
                "rank_policy": "saea-rank-wcos-prior-agree-v1",
                "fuse_policy": "saea-fuse-supplyfilter-v1",
                "k": 5,
                "tau": 0.0,
                "dimensions": ["content"],
                "rank_weights": {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0},
                "fuse_coverage": {"m": 5, "c": 5, "top_l": 5},
                "expose_facets": True,
                "query_source": {
                    "kind": ps.SEALED_VECTORS_KIND,
                    "relpath": "v/q.jsonl",
                    "sha256": query_sha,
                    "tool_contact_ledger_row": "TEST-EMB-NORM-CACHE",
                    "embedded_signal": "speech: the test's own synthetic speech vectors",
                },
                "facet_source": {
                    "kind": ps.SEALED_VECTORS_KIND,
                    "relpath": "v/f.jsonl",
                    "sha256": facet_sha,
                    "tool_contact_ledger_row": "TEST-EMB-NORM-CACHE",
                    "embedded_signal": "text: the test's own synthetic TRAIN key vectors",
                },
            }
        }
    }
    specs = ps.load_phase_supply_specs(values, program)
    stub = SimpleNamespace(
        _composed=SimpleNamespace(values=values),
        _data_root=tmp_path,
        _phase_supply_providers=None,
        _phase_supply_receipt=None,
    )
    supply_for_phase, _resolved = FlightRuntime._resolve_phase_supply(stub, program, snapshot)
    provider = supply_for_phase.provider_factories["slots"]()
    bindings = {
        sample_id: {"packet_id": f"speech/{sample_id}", "sha256": _SHA_C}
        for sample_id, _vectors in query_rows
    }
    facets, selected = ps.build_bootstrap_selection(
        specs["slots"],
        provider=provider,
        query_vectors_by_sample=supply_for_phase.query_tables["slots"],
        speech_packet_bindings=bindings,
        split_identity_hash=_SHA_C,
    )
    return {
        "facets": {sample_id: list(ids) for sample_id, ids in sorted(facets.items())},
        "values": {sample_id: list(ids) for sample_id, ids in sorted(selected.items())},
    }


#: The selection the fixture produced at commit ``2afb4b5c`` (the per-pair
#: module), computed by running :func:`_seeded_selection` against that tree
#: in isolation on 2026-09-09 before the cache landed. Any change to the
#: fixture or to the decision path moves this literal, which is the point.
_EXPECTED_SELECTION_AT_2AFB4B5C: dict[str, object] = {
    "facets": {
        "dev:s0": ["facet:content:u007", "facet:content:u008", "facet:content:u018",
                   "facet:content:u024", "facet:content:u029"],
        "dev:s1": ["facet:content:u002", "facet:content:u005", "facet:content:u009",
                   "facet:content:u014", "facet:content:u030"],
        "dev:s2": ["facet:content:u002", "facet:content:u005", "facet:content:u019",
                   "facet:content:u028", "facet:content:u035"],
        "dev:s3": ["facet:content:u001", "facet:content:u034", "facet:content:u035",
                   "facet:content:u036", "facet:content:u037"],
        "dev:s4": ["facet:content:u001", "facet:content:u002", "facet:content:u010",
                   "facet:content:u016", "facet:content:u034"],
        "dev:s5": ["facet:content:u006", "facet:content:u009", "facet:content:u016",
                   "facet:content:u019", "facet:content:u034"],
    },
    "values": {
        "dev:s0": ["value:u007", "value:u008", "value:u018", "value:u024", "value:u029"],
        "dev:s1": ["value:u002", "value:u005", "value:u009", "value:u014", "value:u030"],
        "dev:s2": ["value:u002", "value:u005", "value:u019", "value:u028", "value:u035"],
        "dev:s3": ["value:u001", "value:u034", "value:u035", "value:u036", "value:u037"],
        "dev:s4": ["value:u001", "value:u002", "value:u010", "value:u016", "value:u034"],
        "dev:s5": ["value:u006", "value:u009", "value:u016", "value:u019", "value:u034"],
    },
}
#: sha256 of the canonical JSON of that selection, measured identically under
#: the 2afb4b5c tree and this one: aa28de7c76b10cb31d14cc76f8c6e78b9dce5761333ed1ef4eba7e03a33823bd


def test_the_seeded_selection_is_identical_before_and_after_on_the_fixed_fixture(tmp_path):
    selection = _seeded_selection(tmp_path)
    assert selection == _EXPECTED_SELECTION_AT_2AFB4B5C
    # Every sample selected five values and five supporting facets.
    assert set(selection["values"]) == {f"dev:s{index}" for index in range(6)}
    assert all(len(ids) == 5 for ids in selection["values"].values())
    assert all(len(ids) == 5 for ids in selection["facets"].values())


def test_the_seeded_selection_recall_scores_are_bitwise_the_oracle_s(tmp_path):
    """The same fixture, one level down: the recall dict the seeded path
    ranks is bitwise what the 2afb4b5c loop computes on the loaded tables."""

    snapshot, key_rows, query_rows = _fixture_rows()
    query_sha = _write_vectors(tmp_path / "v" / "q.jsonl", query_rows)
    facet_sha = _write_vectors(tmp_path / "v" / "f.jsonl", key_rows)
    queries = ps.load_sealed_vectors(
        tmp_path / "v" / "q.jsonl", expected_sha256=query_sha, dimensions=("content",)
    )
    keys = ps.load_sealed_vectors(
        tmp_path / "v" / "f.jsonl", expected_sha256=facet_sha, dimensions=("content",)
    )
    lookup = lambda facet_id: keys.get(facet_id, {})  # noqa: E731
    for sample_id, _row in query_rows:
        query = dict(queries[sample_id])
        expected = _reference_recall(snapshot, query, lookup, 5)
        measured = kb_policy.multidim_recall(snapshot, query, lookup, 5)
        assert set(measured) == set(expected)
        for facet_id, dims in expected.items():
            for dimension, score in dims.items():
                assert _bits(measured[facet_id][dimension]) == _bits(score)


@pytest.mark.parametrize("index", range(3))
def test_the_reference_recall_agrees_with_itself_on_repeat(index):
    """Guard on the oracle: the fixture is deterministic across calls."""

    left = _fixture_rows()
    right = _fixture_rows()
    assert left[1][index] == right[1][index]
    assert left[2][index] == right[2][index]
