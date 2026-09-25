"""Balanced source-candidate presentation and strict selector parsing."""
from collections import Counter
import pytest
from speech_aware_evidence_acquisition.rails.phase_material import (
    balanced_sealed_sample_permutations, PhaseMaterialError,
)
from speech_aware_evidence_acquisition.rails.artifact_results import (
    parse_slurp_verifier_choice, ArtifactContentError,
)

def test_balanced_source_positions_and_input_order_independence():
    ids = [f"row-{i}" for i in range(625)]
    got = balanced_sealed_sample_permutations(ids, seed=20260925, count=5)
    assert got == balanced_sealed_sample_permutations(ids[::-1], seed=20260925, count=5)
    for position in range(5):
        assert Counter(order[position] for order in got.values()) == {i:125 for i in range(5)}
    assert all(sorted(order) == list(range(5)) for order in got.values())

def test_incomplete_block_is_balanced_to_one():
    got = balanced_sealed_sample_permutations([f"row-{i}" for i in range(23)], seed=2, count=5)
    for position in range(5):
        counts = Counter(order[position] for order in got.values())
        assert max(counts.values()) - min(counts.values()) <= 1

@pytest.mark.parametrize("ids,count", [(["x","x"],5), (["x"],0), (["x"],True), ([""],5)])
def test_invalid_balance_inputs_are_rejected(ids,count):
    with pytest.raises(PhaseMaterialError):
        balanced_sealed_sample_permutations(ids, seed=2, count=count)

def test_selector_reason_obeys_the_declared_bound():
    with pytest.raises(ArtifactContentError, match="reason"):
        parse_slurp_verifier_choice('{"chosen_position":1,"reason":"long"}',
                                   candidate_count=5, max_reason_chars=3)
    assert parse_slurp_verifier_choice('{"chosen_position":1,"reason":"ok"}',
                                      candidate_count=5, max_reason_chars=3)["chosen_position"] == 1
