"""Synthetic-pool tests for ``scripts/build_slurp_stage3_construction_roster.py`` (S3-1).

Exercises the pure, model-free functions the generator's ``main`` composes --
stratum quota apportionment, the farthest-point cosine traversal, KB-snapshot
value parsing, forbidden-roster exclusion and the disjointness proof -- on
synthetic data. No real dataset, vector file or network access.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "build_slurp_stage3_construction_roster.py"

_spec = importlib.util.spec_from_file_location(
    "build_slurp_stage3_construction_roster", MODULE_PATH
)
mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault(_spec.name, mod)
_spec.loader.exec_module(mod)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# stratum_quotas
# ---------------------------------------------------------------------------


def test_stratum_quotas_18_strata_800_total_matches_the_receipted_split():
    strata = [
        "alarm", "audio", "calendar", "cooking", "datetime", "email", "general",
        "iot", "lists", "music", "news", "play", "qa", "recommendation", "social",
        "takeaway", "transport", "weather",
    ]
    quotas = mod.stratum_quotas(strata, total=800)
    assert sum(quotas.values()) == 800
    assert set(quotas) == set(strata)
    # 800 // 18 = 44 remainder 8: the 8 alphabetically-first strata take 45.
    fortyfive = sorted(name for name, n in quotas.items() if n == 45)
    fortyfour = sorted(name for name, n in quotas.items() if n == 44)
    assert fortyfive == sorted(strata)[:8]
    assert fortyfour == sorted(strata)[8:]
    assert not (set(fortyfive) & set(fortyfour))


def test_stratum_quotas_is_order_independent_and_deterministic():
    strata_a = ["z", "a", "m", "b"]
    strata_b = list(reversed(strata_a))
    assert mod.stratum_quotas(strata_a, total=10) == mod.stratum_quotas(strata_b, total=10)


def test_stratum_quotas_refuses_empty_strata():
    with pytest.raises(SystemExit):
        mod.stratum_quotas([], total=10)


# ---------------------------------------------------------------------------
# farthest_point_draw
# ---------------------------------------------------------------------------


def _two_cluster_vectors():
    """Ten points in two tight, well-separated clusters (5 + 5), 2-D."""

    import numpy as np

    cluster_a = np.array(
        [[1.0, 0.0 + i * 1e-4] for i in range(5)], dtype=np.float64
    )
    cluster_b = np.array(
        [[0.0, 1.0 + i * 1e-4] for i in range(5)], dtype=np.float64
    )
    ids = [f"u{i:02d}" for i in range(10)]
    vecs = np.vstack([cluster_a, cluster_b])
    return ids, vecs


def test_farthest_point_draw_is_deterministic_for_a_fixed_seed():
    ids, vecs = _two_cluster_vectors()
    first = mod.farthest_point_draw(ids, vecs, 6, seed_text="20260922:test")
    second = mod.farthest_point_draw(ids, vecs, 6, seed_text="20260922:test")
    assert first == second


def test_farthest_point_draw_covers_both_clusters_before_exhausting_one():
    """The second pick (after a random first) must come from the OTHER
    cluster: the farthest-point rule always prefers an uncovered cluster to
    a near-duplicate of the already-selected point."""

    ids, vecs = _two_cluster_vectors()
    for seed in range(8):
        drawn = mod.farthest_point_draw(ids, vecs, 2, seed_text=f"seed:{seed}")
        first_cluster = int(drawn[0][0][1:]) < 5
        second_cluster = int(drawn[1][0][1:]) < 5
        assert first_cluster != second_cluster, drawn


def test_farthest_point_draw_first_point_has_no_min_cosine():
    ids, vecs = _two_cluster_vectors()
    drawn = mod.farthest_point_draw(ids, vecs, 3, seed_text="x")
    assert drawn[0][1] is None
    assert all(value is not None for _, value in drawn[1:])


def test_farthest_point_draw_draw_rank_order_is_farthest_first():
    """Every later pick's recorded min_cosine_to_selected is <= the previous
    one's, up to float tolerance, because each round consumes the globally
    farthest remaining candidate under a monotonically non-decreasing
    closest-similarity frontier -- not a strict claim across arbitrary
    point sets, but true for two isolated clusters with 5 members apiece."""

    ids, vecs = _two_cluster_vectors()
    drawn = mod.farthest_point_draw(ids, vecs, 10, seed_text="rank-order")
    values = [v for _, v in drawn if v is not None]
    # within a single homogeneous cluster, similarity to the growing selected
    # set only rises; the leading (first two, cross-cluster) values are the
    # smallest observed.
    assert values[0] <= min(values[1:])


def test_farthest_point_draw_refuses_a_quota_larger_than_the_pool():
    ids, vecs = _two_cluster_vectors()
    with pytest.raises(SystemExit):
        mod.farthest_point_draw(ids, vecs, 11, seed_text="too-big")


# ---------------------------------------------------------------------------
# mean_pairwise_cosine
# ---------------------------------------------------------------------------


def test_mean_pairwise_cosine_lower_for_a_diverse_set_than_a_clustered_one():
    import numpy as np

    diverse = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0]])
    clustered = np.array([[1.0, 0.0], [1.0, 1e-6], [1.0, -1e-6], [1.0, 2e-6]])
    assert mod.mean_pairwise_cosine(diverse) < mod.mean_pairwise_cosine(clustered)


def test_mean_pairwise_cosine_none_below_two_points():
    import numpy as np

    assert mod.mean_pairwise_cosine(np.array([[1.0, 0.0]])) is None


# ---------------------------------------------------------------------------
# pool_candidates (synthetic KB snapshot)
# ---------------------------------------------------------------------------


def _synthetic_snapshot(n: int = 4) -> dict:
    values = []
    scenarios = ["alarm", "audio", "calendar", "cooking"]
    for i in range(1, n + 1):
        scenario = scenarios[(i - 1) % len(scenarios)]
        values.append(
            {
                "value_id": f"value:{i}",
                "associated_facet_ids": [f"facet:content:{i}"],
                "content": "REDACTED",
                "prior_score": 0.5,
                "provenance_refs": [
                    f"governed-jsonl:datasets/slurp/metadata/train.jsonl#slurp_id={i}",
                    f"sample:slurp:train:{i:06d}:audio-2{i}",
                    f"sample:slurp:train:{i:06d}:audio-1{i}",
                    "speaker:FO-000",
                    f"utterance:{i}",
                ],
                "source_sample_ids": [
                    f"slurp:train:{i:06d}:audio-2{i}",
                    f"slurp:train:{i:06d}:audio-1{i}",
                ],
                "task_target": f"{scenario}_set",
            }
        )
    return {
        "builder_policy_id": "saea-kb-distmodel-v1",
        "facets": [],
        "snapshot_id": "synthetic",
        "snapshot_sha256": "synthetic",
        "snapshot_version": "knowledge-snapshot-v1",
        "source_partition_role": "train",
        "source_sample_ids": [],
        "source_split_identity_hash": "synthetic",
        "values": values,
    }


def test_pool_candidates_reads_stratum_from_task_target_never_gold():
    snapshot = _synthetic_snapshot(4)
    candidates = mod.pool_candidates(snapshot)
    assert len(candidates) == 4
    entry = candidates["slurp:train:000001"]
    assert entry["stratum"] == "alarm"
    # the FIRST recording by id (lexicographic), not by provenance order.
    assert entry["sample_id"] == "slurp:train:000001:audio-11"
    assert entry["facet_id"] == "facet:content:1"


def test_pool_candidates_refuses_a_facet_id_mismatch():
    snapshot = _synthetic_snapshot(1)
    snapshot["values"][0]["associated_facet_ids"] = ["facet:content:999"]
    with pytest.raises(SystemExit):
        mod.pool_candidates(snapshot)


def test_pool_candidates_refuses_a_repeated_utterance():
    snapshot = _synthetic_snapshot(1)
    snapshot["values"].append(dict(snapshot["values"][0]))
    with pytest.raises(SystemExit):
        mod.pool_candidates(snapshot)


def test_pool_candidates_refuses_a_value_with_no_sample_provenance():
    snapshot = _synthetic_snapshot(1)
    snapshot["values"][0]["provenance_refs"] = ["speaker:FO-000", "utterance:1"]
    with pytest.raises(SystemExit):
        mod.pool_candidates(snapshot)


# ---------------------------------------------------------------------------
# exclude_forbidden / disjointness_report
# ---------------------------------------------------------------------------


def _synthetic_candidates() -> dict:
    return {
        "slurp:train:000001": {"utterance_id": "slurp:train:000001", "stratum": "alarm",
                                "sample_id": "slurp:train:000001:audio-1", "facet_id": "facet:content:1"},
        "slurp:train:000002": {"utterance_id": "slurp:train:000002", "stratum": "audio",
                                "sample_id": "slurp:train:000002:audio-1", "facet_id": "facet:content:2"},
        "slurp:train:000003": {"utterance_id": "slurp:train:000003", "stratum": "audio",
                                "sample_id": "slurp:train:000003:audio-1", "facet_id": "facet:content:3"},
    }


def test_exclude_forbidden_removes_only_the_named_utterance():
    candidates = _synthetic_candidates()
    forbidden = {"docs/receipts/rosters/fake-a.json": {"slurp:train:000002:audio-1"}}
    remaining, excluded = mod.exclude_forbidden(candidates, forbidden)
    assert excluded == ["slurp:train:000002"]
    assert set(remaining) == {"slurp:train:000001", "slurp:train:000003"}
    # the input mapping is never mutated.
    assert set(candidates) == {"slurp:train:000001", "slurp:train:000002", "slurp:train:000003"}


def test_exclude_forbidden_is_a_noop_on_disjoint_ids():
    candidates = _synthetic_candidates()
    forbidden = {"docs/receipts/rosters/fake-a.json": {"slurp:devel:000099:audio-1"}}
    remaining, excluded = mod.exclude_forbidden(candidates, forbidden)
    assert excluded == []
    assert set(remaining) == set(candidates)


def test_disjointness_report_flags_a_shared_recording():
    final_recordings = {"slurp:train:000001:audio-1"}
    final_utterances = {"slurp:train:000001"}
    forbidden = {"docs/receipts/rosters/fake-a.json": {"slurp:train:000001:audio-1"}}
    report = mod.disjointness_report(final_recordings, final_utterances, forbidden)
    entry = report["fake-a"]
    assert entry["shared_recordings"] == 1
    assert entry["shared_utterances"] == 1


def test_disjointness_report_zero_on_a_clean_draw():
    final_recordings = {"slurp:train:000001:audio-1"}
    final_utterances = {"slurp:train:000001"}
    forbidden = {"docs/receipts/rosters/fake-a.json": {"slurp:devel:000099:audio-1"}}
    report = mod.disjointness_report(final_recordings, final_utterances, forbidden)
    entry = report["fake-a"]
    assert entry["shared_recordings"] == 0
    assert entry["shared_utterances"] == 0


# ---------------------------------------------------------------------------
# canonicalisation helpers
# ---------------------------------------------------------------------------


def test_canonical_sha256_is_key_order_independent():
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert mod.canonical_sha256(a) == mod.canonical_sha256(b)


def test_utterance_id_of_zero_pads_to_six_digits():
    assert mod.utterance_id_of("1") == "slurp:train:000001"
    assert mod.utterance_id_of("123456") == "slurp:train:123456"


def test_is_headset_detects_the_suffix():
    assert mod.is_headset("datasets/slurp/slurp_real/audio-1-headset.flac") is True
    assert mod.is_headset("datasets/slurp/slurp_real/audio-1.flac") is False
