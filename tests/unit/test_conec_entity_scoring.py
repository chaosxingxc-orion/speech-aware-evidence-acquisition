"""``conec-entity-wer-official``: the alignment trace's identity against the
frozen aligner, the fstalign ``RecordTagWer`` accounting, the run-chunked
label transfer, and hand-computed end-to-end numbers on synthetic
transcripts."""

import json
import random

import pytest

from speech_aware_evidence_acquisition.core import scorers  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.core.scorers import (
    ScoringPhaseError,
    score_conec_entity_wer_outputs,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.reproduction.conec_entity_scoring import (
    CONEC_ENTITY_SCORER_VERSION,
    NON_ENTITY_BUCKET,
    OP_DELETION,
    OP_HIT,
    OP_INSERTION,
    OP_SUBSTITUTION,
    OVERALL_BUCKET,
    UNLABELLED_BUCKET,
    ConecScoringError,
    aligned_operations,
    entity_wer_buckets,
    merge_buckets,
    operation_counts,
    run_chunked_whisper_words,
    scorer_provenance,
    transfer_owners,
    whole_string_whisper_words,
)
from speech_aware_evidence_acquisition.scoring import align


def _write_nlp(path, rows):
    lines = ["token|speaker|tags|wer_tags"]
    for token, wer_tags in rows:
        lines.append(f"{token}|0||{wer_tags}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_sidecar(path, mapping):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping), encoding="utf-8")


def _write_outputs(tmp_path, rows, name="y.outputs.jsonl"):
    path = tmp_path / name
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    return path


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_conec_entity_wer_is_registered():
    assert "conec-entity-wer-official" in SCORERS.names()
    assert SCORERS.resolve("conec-entity-wer-official") is score_conec_entity_wer_outputs


def test_provenance_says_the_official_tool_was_not_run():
    provenance = scorer_provenance()
    assert provenance["official_tool_run"] is False
    assert provenance["official_tool"] == "revdotcom/fstalign"
    assert provenance["implementation"] == "definition-mirror"
    assert "69df0b2b357f994101d630cb3f56e22b57ebcf04" in provenance["definition_source"]
    assert provenance["scorer_version"] == CONEC_ENTITY_SCORER_VERSION


# ---------------------------------------------------------------------------
# aligned_operations IS the frozen aligner, operation for operation.
# ---------------------------------------------------------------------------


def _counts_from_trace(operations):
    kinds = [operation[0] for operation in operations]
    return {
        "hits": kinds.count(OP_HIT),
        "substitutions": kinds.count(OP_SUBSTITUTION),
        "deletions": kinds.count(OP_DELETION),
        "insertions": kinds.count(OP_INSERTION),
    }


def _mask_from_trace(operations, reference_length):
    mask = [False] * reference_length
    for kind, reference_index, _ in operations:
        if kind == OP_HIT:
            mask[reference_index] = True
    return tuple(mask)


def _assert_matches_frozen_aligner(ref, hyp):
    operations = aligned_operations(ref, hyp)
    frozen = align(ref, hyp)
    counts = _counts_from_trace(operations)
    assert counts["hits"] == frozen.hits
    assert counts["substitutions"] == frozen.substitutions
    assert counts["deletions"] == frozen.deletions
    assert counts["insertions"] == frozen.insertions
    assert _mask_from_trace(operations, len(ref)) == frozen.ref_hit_mask
    derived = operation_counts(operations, len(ref), len(hyp))
    assert derived["errors"] == frozen.errors
    assert derived["reference_words"] == frozen.reference_length


@pytest.mark.parametrize(
    "ref,hyp",
    [
        ([], []),
        (["a"], []),
        ([], ["a"]),
        (["a", "b", "c"], ["a", "b", "c"]),
        (["a", "b", "c"], ["a", "x", "c"]),
        (["a", "b", "c"], ["a", "c"]),
        (["a", "c"], ["a", "b", "c"]),
        (["a", "a", "a"], ["a"]),
        (["the", "acme", "corporation"], ["the", "acne", "corporation", "inc"]),
    ],
)
def test_trace_reproduces_the_frozen_aligner_on_fixtures(ref, hyp):
    _assert_matches_frozen_aligner(ref, hyp)


def test_trace_reproduces_the_frozen_aligner_on_randomized_sequences():
    generator = random.Random(20260906)
    vocabulary = ["a", "b", "c", "d", "e"]
    for _ in range(120):
        ref = [generator.choice(vocabulary) for _ in range(generator.randint(0, 9))]
        hyp = [generator.choice(vocabulary) for _ in range(generator.randint(0, 9))]
        _assert_matches_frozen_aligner(ref, hyp)


def test_operation_counts_refuses_a_trace_that_skips_a_reference_word():
    with pytest.raises(ConecScoringError, match="reference index"):
        operation_counts(((OP_HIT, 1, 0),), 2, 1)


def test_operation_counts_refuses_an_insertion_carrying_a_reference_index():
    with pytest.raises(ConecScoringError, match="reference index"):
        operation_counts(((OP_INSERTION, 0, 0),), 0, 1)


def test_operation_counts_refuses_a_short_trace():
    with pytest.raises(ConecScoringError, match="consumed 1 reference words"):
        operation_counts(((OP_HIT, 0, 0),), 2, 1)


# ---------------------------------------------------------------------------
# Run-chunked normalization and the label transfer onto the whole-string one.
# ---------------------------------------------------------------------------


def test_run_chunking_normalizes_a_multi_word_number_inside_one_run():
    # One run, so the Whisper normalizer sees the whole phrase and merges it
    # into a single value -- exactly what the whole-string normalization does.
    words, owners = run_chunked_whisper_words(
        ["twenty", "two", "million"], [(), (), ()]
    )
    assert words == ["22000000"]
    assert owners == [()]


def test_run_chunking_splits_at_an_entity_boundary():
    words, owners = run_chunked_whisper_words(
        ["twenty", "two"], [("7",), ()]
    )
    assert words == ["20", "2"]
    assert owners == [("7",), ()]


def test_run_chunking_refuses_mismatched_owner_length():
    with pytest.raises(ConecScoringError, match="one owner tuple per token"):
        run_chunked_whisper_words(["a", "b"], [()])


def test_transfer_owners_carries_labels_across_identical_sequences():
    transferred = transfer_owners(["a", "b", "c"], [("1",), (), ("2",)], ["a", "b", "c"])
    assert transferred == [("1",), (), ("2",)]


def test_transfer_owners_leaves_an_unmatched_position_unlabelled():
    # The whole-string normalization merged two chunked words into one; the
    # merged position has no counterpart, so it stays None rather than being
    # silently called non-entity.
    transferred = transfer_owners(
        ["x", "20", "2", "y"], [(), ("7",), ("7",), ()], ["x", "22", "y"]
    )
    assert transferred[0] == ()
    assert transferred[1] is None
    assert transferred[2] == ()


# ---------------------------------------------------------------------------
# entity_wer_buckets: fstalign RecordTagWer accounting, hand-computed.
# ---------------------------------------------------------------------------


def test_buckets_hand_computed_one_entity_substitution_one_insertion():
    # reference: acme corp reported growth      (acme corp = ORG id "0")
    # hypothesis: acme corp inc reported profit
    operations = (
        (OP_HIT, 0, 0),
        (OP_HIT, 1, 1),
        (OP_INSERTION, None, 2),
        (OP_HIT, 2, 3),
        (OP_SUBSTITUTION, 3, 4),
    )
    owners = [("0",), ("0",), (), ()]
    buckets = entity_wer_buckets(operations, owners, {"0": "ORG"})
    # The ORG mention was transcribed exactly: no error, two reference words.
    assert buckets["ORG"] == {
        "substitutions": 0,
        "deletions": 0,
        "insertions": 0,
        "errors": 0,
        "reference_words": 2,
        "wer": 0.0,
    }
    # The insertion lands next to the ORG span but fstalign attributes no
    # insertion to an entity ID -- it reaches only the overall bucket.
    assert buckets[NON_ENTITY_BUCKET]["insertions"] == 0
    assert buckets[NON_ENTITY_BUCKET]["errors"] == 1
    assert buckets[NON_ENTITY_BUCKET]["reference_words"] == 2
    assert buckets[OVERALL_BUCKET] == {
        "substitutions": 1,
        "deletions": 0,
        "insertions": 1,
        "errors": 2,
        "reference_words": 4,
        "wer": 0.5,
    }


def test_buckets_charge_a_word_to_every_entity_id_it_carries():
    operations = ((OP_SUBSTITUTION, 0, 0),)
    buckets = entity_wer_buckets(operations, [("0", "1")], {"0": "YEAR", "1": "CARDINAL"})
    assert buckets["YEAR"]["reference_words"] == 1
    assert buckets["YEAR"]["errors"] == 1
    assert buckets["CARDINAL"]["reference_words"] == 1
    assert buckets["CARDINAL"]["errors"] == 1
    assert buckets[OVERALL_BUCKET]["reference_words"] == 1


def test_buckets_count_an_unlabelled_position_separately():
    operations = ((OP_HIT, 0, 0), (OP_DELETION, 1, None))
    buckets = entity_wer_buckets(operations, [(), None], {})
    assert buckets[UNLABELLED_BUCKET]["reference_words"] == 1
    assert buckets[UNLABELLED_BUCKET]["errors"] == 1
    assert buckets[NON_ENTITY_BUCKET]["reference_words"] == 1
    assert buckets[NON_ENTITY_BUCKET]["errors"] == 0


def test_buckets_refuse_an_entity_id_with_no_type():
    with pytest.raises(ConecScoringError, match="no entity type"):
        entity_wer_buckets(((OP_HIT, 0, 0),), [("9",)], {})


def test_merge_buckets_pools_counts_and_divides_once():
    merged = merge_buckets(
        [
            {"ORG": {"substitutions": 1, "deletions": 0, "insertions": 0, "reference_words": 2}},
            {"ORG": {"substitutions": 0, "deletions": 1, "insertions": 0, "reference_words": 6}},
        ]
    )
    # Pooled 2/8 = 0.25, which is NOT the mean of 0.5 and 1/6.
    assert merged["ORG"]["wer"] == pytest.approx(0.25)
    assert merged["ORG"]["reference_words"] == 8


# ---------------------------------------------------------------------------
# End to end, over the synthetic Earnings-21 world.
# ---------------------------------------------------------------------------

_ROWS = [
    ("The", "[]"),
    ("Acme", "['0']"),
    ("Corporation", "['0']"),
    ("reported", "[]"),
    ("in", "[]"),
    ("March", "['1']"),
    ("2020", "['1']"),
]


def _setup(synthetic_world):
    _write_nlp(synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp", _ROWS)
    _write_sidecar(
        synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json",
        {"0": {"entity_type": "ORG"}, "1": {"entity_type": "DATE"}},
    )


def test_end_to_end_hand_computed(synthetic_world, tmp_path):
    """Reference normalizes to ``the acme corporation reported in march 2020``
    (7 words). The hypothesis keeps the ORG right, substitutes the DATE's year
    and inserts one word. ORG 0/2, DATE 1/2, non-entity 0/3, overall
    (1 sub + 1 ins) / 7."""

    _setup(synthetic_world)
    outputs = _write_outputs(
        tmp_path,
        [
            {
                "sample_id": "4000001",
                "carrier_lock_key": "earnings21-original",
                "text": "the acme corporation inc reported in march 2021",
            }
        ],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = score_conec_entity_wer_outputs(outputs, lock, synthetic_world.data_root)

    sample = scores["per_sample"][0]
    assert sample["sample_id"] == "4000001"
    assert sample["reference_words"] == 7
    assert sample["unlabelled_reference_words"] == 0
    buckets = sample["by_entity_type"]
    assert buckets["ORG"]["errors"] == 0
    assert buckets["ORG"]["reference_words"] == 2
    assert buckets["DATE"]["errors"] == 1
    assert buckets["DATE"]["reference_words"] == 2
    assert buckets["DATE"]["wer"] == pytest.approx(0.5)
    assert buckets[NON_ENTITY_BUCKET]["reference_words"] == 3
    assert buckets[NON_ENTITY_BUCKET]["errors"] == 0
    assert buckets[OVERALL_BUCKET]["insertions"] == 1
    assert buckets[OVERALL_BUCKET]["wer"] == pytest.approx(2 / 7)

    aggregate = scores["aggregate"]
    assert aggregate["samples"] == 1
    assert aggregate["reference_words"] == 7
    assert aggregate["official_tool_run"] is False
    assert aggregate["corpus_wer"] == pytest.approx(2 / 7)


def test_conec_alignment_payload_roundtrips_and_reconstructs_entity_counts(
    synthetic_world, tmp_path
):
    _setup(synthetic_world)
    outputs = _write_outputs(
        tmp_path,
        [
            {
                "sample_id": "4000001",
                "carrier_lock_key": "earnings21-original",
                "text": "the acme corporation inc reported in march 2021",
            }
        ],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = score_conec_entity_wer_outputs(outputs, lock, synthetic_world.data_root)
    sample = scores["per_sample"][0]

    alignment = json.loads(json.dumps(sample["alignment"], sort_keys=True))
    assert alignment["schema"] == "saea-conec-alignment-v1"
    assert alignment["reference_words"] == [
        "the", "acme", "corporation", "reported", "in", "march", "2020"
    ]
    assert alignment["hypothesis_words"] == [
        "the", "acme", "corporation", "inc", "reported", "in", "march", "2021"
    ]
    assert all(
        isinstance(operation, list) and len(operation) == 3
        for operation in alignment["operations"]
    )

    reconstructed = entity_wer_buckets(
        [tuple(operation) for operation in alignment["operations"]],
        [
            None if owners is None else tuple(owners)
            for owners in alignment["reference_owners"]
        ],
        alignment["entity_types"],
    )
    assert reconstructed == sample["by_entity_type"]
    counts = operation_counts(
        [tuple(operation) for operation in alignment["operations"]],
        len(alignment["reference_words"]),
        len(alignment["hypothesis_words"]),
    )
    overall = sample["by_entity_type"][OVERALL_BUCKET]
    assert counts[OP_SUBSTITUTION] == overall["substitutions"]
    assert counts[OP_DELETION] == overall["deletions"]
    assert counts[OP_INSERTION] == overall["insertions"]
    assert counts["reference_words"] == overall["reference_words"]
    legacy = {key: value for key, value in sample.items() if key != "alignment"}
    assert legacy["sample_id"] == "4000001"
    assert legacy["wer"] == pytest.approx(2 / 7)
    assert legacy["reference_words"] == 7
    assert legacy["unlabelled_reference_words"] == 0


def test_overall_bucket_reproduces_the_whisper_wer_of_the_same_text(synthetic_world, tmp_path):
    """The ``__ALL__`` bucket is this scorer's own identity anchor: it is the
    frozen aligner over exactly the sequences ``asr-wer-whisper`` builds."""

    _setup(synthetic_world)
    text = "the acme corporation inc reported in march 2021"
    outputs = _write_outputs(
        tmp_path,
        [{"sample_id": "4000001", "carrier_lock_key": "earnings21-original", "text": text}],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = score_conec_entity_wer_outputs(outputs, lock, synthetic_world.data_root)

    reference = whole_string_whisper_words([token for token, _ in _ROWS])
    hypothesis = whole_string_whisper_words([text])
    frozen = align(reference, hypothesis)
    overall = scores["per_sample"][0]["by_entity_type"][OVERALL_BUCKET]
    assert overall["wer"] == pytest.approx(frozen.wer)
    assert overall["substitutions"] == frozen.substitutions
    assert overall["deletions"] == frozen.deletions
    assert overall["insertions"] == frozen.insertions
    assert overall["reference_words"] == frozen.reference_length


def test_scorer_refuses_a_carrier_with_no_entity_layer(synthetic_world, tmp_path):
    outputs = _write_outputs(
        tmp_path,
        [{"sample_id": "x", "carrier_lock_key": "slurp", "text": "hello"}],
    )
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="no registered entity layer"):
        score_conec_entity_wer_outputs(outputs, lock, synthetic_world.data_root)


def test_scorer_refuses_empty_outputs(synthetic_world, tmp_path):
    outputs = tmp_path / "empty.outputs.jsonl"
    outputs.write_text("", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="is empty"):
        score_conec_entity_wer_outputs(outputs, lock, synthetic_world.data_root)
