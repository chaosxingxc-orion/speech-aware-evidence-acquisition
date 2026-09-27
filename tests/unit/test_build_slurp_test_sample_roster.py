"""``scripts/build_slurp_test_sample_roster.py``: the pure stratification rule,
the partition proof, the size arithmetic, and the two committed receipts.

The builder is imported by FILE PATH: the shared venv carries a regular
top-level ``scripts`` package (verl 0.8.0) that shadows this repository's
namespace directory. Nothing here opens the data root; the committed-receipt
tests read only committed bytes and skip when the receipts are absent.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.roster import RosterError, read_roster
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
PARENT_RELPATH = "docs/receipts/rosters/slurp-test-full-13078-v1.json"


def _load_builder():
    path = REPO_ROOT / "scripts" / "build_slurp_test_sample_roster.py"
    spec = importlib.util.spec_from_file_location("saea_build_slurp_test_sample_roster", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_builder()


# --------------------------------------------------------------------------- #
# the stratification rule
# --------------------------------------------------------------------------- #


def test_partition_quotas_floors_even_splits_and_singletons() -> None:
    capacity = {"a": 40, "b": 12, "c": 7, "d": 2, "e": 1}
    quotas, accounting = builder.partition_quotas(capacity, 20, sample_floor=5, closure_floor=5)
    # a and b clear both floors: floor 5 each; c (7) and d (2) split evenly with the
    # closure taking the larger half; e (1) goes to the closure alone.
    assert accounting["floor_driven_utterances"] == 5 + 5 + 3 + 1 + 0
    assert accounting["remainder_utterances"] == 6
    # The remainder can only land where capacity survives both floors: a has 30,
    # b has 2, the rest 0. Largest remainder at weights 40:12 gives a 5, b 1.
    assert quotas == {"a": 10, "b": 6, "c": 3, "d": 1, "e": 0}
    assert [row["intent"] for row in accounting["even_split_intents"]] == ["c", "d"]
    assert accounting["single_prompt_intents_to_closure"] == ["e"]
    # Every intent with two or more prompts is present in BOTH rosters.
    for intent, cap in capacity.items():
        if cap >= 2:
            assert quotas[intent] >= 1
            assert cap - quotas[intent] >= 1


def test_partition_quotas_refuses_a_total_below_the_floor_minimum() -> None:
    capacity = {"a": 40, "b": 12, "c": 7, "d": 2, "e": 1}
    with pytest.raises(builder.SampleBuildError, match="below the floor-driven minimum"):
        builder.partition_quotas(capacity, 10, sample_floor=5, closure_floor=5)


def test_partition_quotas_is_deterministic_and_order_free() -> None:
    capacity = {"z": 30, "y": 25, "x": 11, "w": 3}
    first, _ = builder.partition_quotas(capacity, 30)
    second, _ = builder.partition_quotas(dict(reversed(list(capacity.items()))), 30)
    assert first == second
    assert sum(first.values()) == 30


# --------------------------------------------------------------------------- #
# the partition proof
# --------------------------------------------------------------------------- #


def _ids(prefix: str, prompts: int, per_prompt: int) -> list[str]:
    return [
        f"slurp:test:{p:06d}:{prefix}-{p}-{r}" for p in range(prompts) for r in range(per_prompt)
    ]


def test_verify_partition_proves_a_clean_split_at_three_levels() -> None:
    parent = _ids("audio", 6, 3)
    sample = [sid for sid in parent if int(sid.split(":")[2]) < 2]
    closure = [sid for sid in parent if int(sid.split(":")[2]) >= 2]
    proof = builder.verify_partition(parent, sample, closure)
    assert proof["intersection_recordings"] == 0
    assert proof["intersection_utterances"] == 0
    assert proof["intersection_prompt_numbers"] == 0
    assert proof["union_equals_parent"] is True
    assert proof["union_split_identity_hash"] == split_identity_hash(prefixed("slurp", parent))


def test_verify_partition_refuses_an_overlap_and_a_short_union() -> None:
    parent = _ids("audio", 6, 3)
    sample = parent[:6]
    with pytest.raises(builder.SampleBuildError, match="partition proof failed"):
        builder.verify_partition(parent, sample, parent[5:])  # one shared recording
    with pytest.raises(builder.SampleBuildError, match="partition proof failed"):
        builder.verify_partition(parent, sample, parent[7:])  # one recording in neither
    # A prompt split across the two rosters is refused even when recordings are disjoint.
    with pytest.raises(builder.SampleBuildError, match="partition proof failed"):
        builder.verify_partition(parent, parent[:1], parent[1:])


# --------------------------------------------------------------------------- #
# the size arithmetic
# --------------------------------------------------------------------------- #


def test_size_arithmetic_matches_the_instrument() -> None:
    assert builder.utterances_for_target(2000, 2974, 13078) == 455
    assert builder.utterances_for_target(3000, 2974, 13078) == 682
    assert builder.half_width_pp(0.95, 13078) == pytest.approx(0.374, abs=0.001)
    assert builder.paired_half_width_pp(913) == pytest.approx(1.152, abs=0.0005)
    # Equal weights and equal counts reduce to the plain proportion half-width.
    plain = builder.half_width_pp(0.95, 400)
    weighted = builder.weighted_half_width_pp(0.95, {"a": 1.0, "b": 1.0}, {"a": 200, "b": 200})
    assert weighted == pytest.approx(plain, abs=0.001)


def test_size_table_marks_an_infeasible_target_instead_of_raising() -> None:
    # 10 intents x 12 prompts = 120 prompts; floor 5 + closure floor 5 leaves 2 per
    # intent, so the floors need 50 prompts and at most 20 more can be apportioned.
    capacity = {f"i{k}": 12 for k in range(10)}
    recordings = {key: 4 * value for key, value in capacity.items()}
    table = builder.size_table(capacity, recordings, 480, (100, 240, 300))
    rows = {row["target_recordings"]: row for row in table["rows"]}
    assert rows[100]["feasible_at_design_floor"] is False  # 25 prompts < 50
    assert "floor rule alone" in rows[100]["infeasibility_note"]
    assert rows[240]["feasible_at_design_floor"] is True  # 60 prompts: 50 floors + 10
    assert rows[240]["remainder_utterances"] == 10
    assert "sample_natural_mixture_poststratified_h_pp_at_p95" in rows[240]
    assert rows[300]["feasible_at_design_floor"] is False  # 75 prompts: 25 > 20 left
    assert "exceeds the capacity" in rows[300]["infeasibility_note"]


# --------------------------------------------------------------------------- #
# the committed receipts
# --------------------------------------------------------------------------- #


def _committed(pattern: str) -> Path | None:
    matches = sorted((REPO_ROOT / "docs/receipts/rosters").glob(pattern))
    assert len(matches) <= 1, matches
    return matches[0] if matches else None


@pytest.mark.skipif(
    _committed("slurp-test-sample-*-v1.json") is None, reason="sample receipt not committed"
)
def test_the_committed_sample_and_closure_are_exactly_the_frozen_parent() -> None:
    sample_path = _committed("slurp-test-sample-*-v1.json")
    closure_path = _committed("slurp-test-closure-*-v1.json")
    assert sample_path is not None and closure_path is not None
    parent = read_roster(REPO_ROOT / PARENT_RELPATH)  # verifies the recorded hash
    sample = read_roster(sample_path)
    closure = read_roster(closure_path)

    parent_ids = {str(item["sample_id"]) for item in parent["items"]}
    sample_ids = {str(item["sample_id"]) for item in sample["items"]}
    closure_ids = {str(item["sample_id"]) for item in closure["items"]}
    assert not (sample_ids & closure_ids)
    assert sample_ids | closure_ids == parent_ids
    assert len(sample_ids) + len(closure_ids) == 13078
    assert split_identity_hash(prefixed("slurp", sorted(parent_ids))) == parent["split_identity_hash"]

    # Whole prompts travel together: no utterance is split across the rosters.
    def utterances(ids: set[str]) -> set[str]:
        return {":".join(sid.split(":")[:3]) for sid in ids}

    assert not (utterances(sample_ids) & utterances(closure_ids))

    for receipt, sibling in ((sample, closure), (closure, sample)):
        assert receipt["split_role"] == "final-report"
        assert receipt["roster_role"] == "evaluation"
        assert receipt["stratum_withheld_per_item"] is True
        assert all("stratum" not in item for item in receipt["items"])
        assert receipt["derived_from"]["source_roster"]["split_identity_hash"] == parent["split_identity_hash"]
        assert receipt["derived_from"]["source_roster"]["sha256"] == hashlib.sha256(
            (REPO_ROOT / PARENT_RELPATH).read_bytes()
        ).hexdigest()
        assert receipt["derived_from"]["sibling_roster"]["split_identity_hash"] == sibling["split_identity_hash"]
        assert receipt["derived_from"]["partition_proof"]["union_split_identity_hash"] == parent["split_identity_hash"]
        assert receipt["gold_access"]["audio_opened"] is False
        assert receipt["target_gold_opened_before_receipt"] is True
        assert receipt["roster_id"].startswith(("SLURP-TEST-SAMPLE-", "SLURP-TEST-CLOSURE-"))
        assert receipt["roster_id"].split("-")[3] == str(len(receipt["items"]))

    # The per-intent tables are one table, carried by both, and they add up.
    assert sample["per_intent"] == closure["per_intent"]
    table = sample["per_intent"]
    assert len(table) == 59
    assert sum(row["sample_recordings"] for row in table.values()) == len(sample_ids)
    assert sum(row["closure_recordings"] for row in table.values()) == len(closure_ids)
    assert sum(row["test_recordings"] for row in table.values()) == 13078
    assert sum(row["test_utterances"] for row in table.values()) == 2974
    for intent, row in table.items():
        assert row["sample_utterances"] + row["closure_utterances"] == row["test_utterances"], intent
        assert row["sample_recordings"] + row["closure_recordings"] == row["test_recordings"], intent
        assert row["closure_utterances"] >= 1, intent  # the final read covers every intent
        if row["test_utterances"] >= 2:
            assert row["sample_utterances"] >= 1, intent
    assert sum(sample["strata_counts"].values()) == len(sample_ids)
    assert sum(closure["strata_counts"].values()) == len(closure_ids)


@pytest.mark.skipif(
    _committed("slurp-test-sample-*-v1.json") is None, reason="sample receipt not committed"
)
def test_the_committed_receipts_pin_their_proof_and_size_table() -> None:
    sample = read_roster(_committed("slurp-test-sample-*-v1.json"))  # type: ignore[arg-type]
    for key in ("disjointness", "size_table"):
        relpath = sample[key]["relpath"]
        measured = hashlib.sha256((REPO_ROOT / relpath).read_bytes()).hexdigest()
        assert measured == sample[key]["sha256"], relpath
    proof = json.loads((REPO_ROOT / sample["disjointness"]["relpath"]).read_text(encoding="utf-8"))
    assert proof["verdict"] == "CLEAN"
    assert proof["violations"] == []
    assert proof["offline_guard"]["outbound_connection_attempts"] == 0
    assert proof["passes"]["4_exposure_closure_new_rosters"]["consumed_rows"] == []


def test_a_tampered_committed_receipt_is_refused(tmp_path: Path) -> None:
    path = _committed("slurp-test-sample-*-v1.json")
    if path is None:
        pytest.skip("sample receipt not committed")
    document = json.loads(path.read_text(encoding="utf-8"))
    document["items"] = document["items"][:-1]
    target = tmp_path / "tampered.json"
    target.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(RosterError, match="split_identity_hash mismatch"):
        read_roster(target)
