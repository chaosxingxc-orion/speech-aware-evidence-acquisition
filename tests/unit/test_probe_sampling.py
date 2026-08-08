"""Unit tests for seeded stratified sampling + split-identity hashing (P0.D)."""

from __future__ import annotations

import hashlib

from speech_aware_evidence_acquisition.reproduction.sampling import (
    split_identity_hash,
    stratified_sample,
)


def items(stratum, n):
    return [{"stratum": stratum, "key": f"{stratum}:{i:05d}"} for i in range(n)]


class TestStratifiedSample:
    def test_same_seed_gives_identical_selection(self):
        pool = items("a", 100) + items("b", 100)
        first = stratified_sample(pool, per_stratum=10, seed=20260807, stratum_of=lambda x: x["stratum"])
        second = stratified_sample(pool, per_stratum=10, seed=20260807, stratum_of=lambda x: x["stratum"])
        assert first == second

    def test_different_seed_gives_different_selection(self):
        pool = items("a", 100)
        one = stratified_sample(pool, per_stratum=10, seed=1, stratum_of=lambda x: x["stratum"])
        two = stratified_sample(pool, per_stratum=10, seed=2, stratum_of=lambda x: x["stratum"])
        assert one != two

    def test_each_stratum_contributes_exactly_k(self):
        pool = items("a", 40) + items("b", 40) + items("c", 40)
        sample = stratified_sample(pool, per_stratum=7, seed=3, stratum_of=lambda x: x["stratum"])
        counts = {}
        for entry in sample:
            counts[entry["stratum"]] = counts.get(entry["stratum"], 0) + 1
        assert counts == {"a": 7, "b": 7, "c": 7}

    def test_small_stratum_is_taken_whole_not_padded(self):
        pool = items("a", 3) + items("b", 40)
        sample = stratified_sample(pool, per_stratum=10, seed=3, stratum_of=lambda x: x["stratum"])
        a_taken = [entry for entry in sample if entry["stratum"] == "a"]
        assert len(a_taken) == 3

    def test_selection_order_is_stable_sorted_by_key(self):
        pool = items("a", 50)
        sample = stratified_sample(
            pool, per_stratum=5, seed=9, stratum_of=lambda x: x["stratum"], key_of=lambda x: x["key"]
        )
        keys = [entry["key"] for entry in sample]
        assert keys == sorted(keys)

    def test_selection_does_not_depend_on_pool_order(self):
        pool = items("a", 60)
        sample_fwd = stratified_sample(
            pool, per_stratum=6, seed=11, stratum_of=lambda x: x["stratum"], key_of=lambda x: x["key"]
        )
        sample_rev = stratified_sample(
            list(reversed(pool)), per_stratum=6, seed=11, stratum_of=lambda x: x["stratum"], key_of=lambda x: x["key"]
        )
        assert sample_fwd == sample_rev


class TestSplitIdentityHash:
    def test_hash_is_sha256_over_sorted_lf_joined_keys(self):
        keys = ["carrier:b", "carrier:a"]
        expected = hashlib.sha256("carrier:a\ncarrier:b".encode()).hexdigest()
        assert split_identity_hash(keys) == expected

    def test_hash_is_order_insensitive(self):
        assert split_identity_hash(["x:2", "x:1"]) == split_identity_hash(["x:1", "x:2"])

    def test_duplicate_keys_are_rejected(self):
        import pytest

        with pytest.raises(ValueError):
            split_identity_hash(["x:1", "x:1"])
