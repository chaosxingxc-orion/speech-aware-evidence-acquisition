"""B-2a phrase-reconstruction transform (2026-08-10, docs/readiness/
2026-08-09-conec-evidence-shape.md "B-2a redesigned again"): deterministic
multi-word phrase candidates re-assembled from a ConEC context file's OWN
line order, at a word-count budget matched to the unigram bag arm's content
volume -- see docs/arms/b2a-bias-lists.arms contrast 2 for the hypothesis.
"""

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core import evidence  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import EVIDENCE_SOURCES, EvidenceError
from speech_aware_evidence_acquisition.core.bias_lists import (
    DEFAULT_BIAS_LIST_MAX_ENTRIES,
    DEFAULT_BIAS_PHRASE_MAX_TOKENS,
    _listline_token_runs,
    bias_list_relpath,
    conec_bias_phrase_content,
    reconstruct_bias_phrases,
    resolve_bias_phrase_max_tokens,
)
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.evidence import resolve_declared_transform_params
from speech_aware_evidence_acquisition.core.evidence_derivation import (
    TRANSFORMS,
    DerivedEvidenceError,
    DerivedEvidenceRegistry,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

from conftest import BIAS_WORLD_ORACLE_TERMS

# The real, materialized ConEC shape (docs/readiness/2026-08-09-conec-
# evidence-shape.md: "one lowercase token per line with a trailing count",
# 0/44 files with a line longer than 8 words): a headline block, exactly the
# fragmentation example the task itself names ("GOLDMAN SACHS" ->
# goldman/sachs on separate lines).
REAL_SHAPE_CONTEXT_TEXT = (
    "goldman 1\n"
    "sachs 1\n"
    "reports 1\n"
    "first 1\n"
    "quarter 1\n"
    "financial 1\n"
    "results 1\n"
)

BASELINE_DIR = Path(REPO_ROOT) / "configs" / "baseline"


# ---------------------------------------------------------------------------
# _listline_token_runs -- the adjacency primitive: a non-listline line breaks
# a run, so a phrase is only ever built from two lines BOTH confirmed to be
# the corpus's own real shape.
# ---------------------------------------------------------------------------


def test_listline_token_runs_is_one_run_on_a_pure_listline_file():
    assert _listline_token_runs(REAL_SHAPE_CONTEXT_TEXT) == [
        ["goldman", "sachs", "reports", "first", "quarter", "financial", "results"]
    ]


def test_listline_token_runs_breaks_at_a_non_listline_line():
    text = "alpha 1\nbeta 1\nNOT A LISTLINE\nAlpha 1\nBeta 1\n"
    assert _listline_token_runs(text) == [["alpha", "beta"], ["Alpha", "Beta"]]


def test_listline_token_runs_is_empty_on_text_with_no_listline_shape():
    assert _listline_token_runs("ctx") == []


# ---------------------------------------------------------------------------
# reconstruct_bias_phrases -- determinism, re-derivability, source-only
# content, adjacency, dedup, and the word-count budget.
# ---------------------------------------------------------------------------


def test_reconstruct_bias_phrases_is_deterministic_and_re_derivable():
    first = reconstruct_bias_phrases(REAL_SHAPE_CONTEXT_TEXT)
    second = reconstruct_bias_phrases(REAL_SHAPE_CONTEXT_TEXT)
    assert first == second
    # A THIRD, independently-derived call (fresh string object, not the same
    # cached text) must still reproduce byte-identical output.
    third = reconstruct_bias_phrases(str(REAL_SHAPE_CONTEXT_TEXT))
    assert third == first


def test_reconstruct_bias_phrases_builds_overlapping_adjacent_bigrams_in_document_order():
    assert reconstruct_bias_phrases(REAL_SHAPE_CONTEXT_TEXT) == [
        "goldman sachs",
        "sachs reports",
        "reports first",
        "first quarter",
        "quarter financial",
        "financial results",
    ]


def test_reconstruct_bias_phrases_never_emits_a_word_absent_from_the_source():
    source_tokens = {
        token for run in _listline_token_runs(REAL_SHAPE_CONTEXT_TEXT) for token in run
    }
    for phrase in reconstruct_bias_phrases(REAL_SHAPE_CONTEXT_TEXT):
        for word in phrase.split():
            assert word in source_tokens


def test_reconstruct_bias_phrases_does_not_bridge_across_a_non_listline_line():
    text = "alpha 1\nbeta 1\nNOT A LISTLINE\ngamma 1\ndelta 1\n"
    candidates = reconstruct_bias_phrases(text)
    assert candidates == ["alpha beta", "gamma delta"]
    assert "beta gamma" not in candidates


def test_reconstruct_bias_phrases_dedupes_case_insensitively_keeping_first_seen_casing():
    text = "alpha 1\nbeta 1\nNOT A LISTLINE\nAlpha 1\nBeta 1\n"
    assert reconstruct_bias_phrases(text) == ["alpha beta"]


def test_reconstruct_bias_phrases_respects_the_token_budget():
    # Budget 5: "goldman sachs" fits (0+2<=5), "sachs reports" fits (2+2<=5),
    # "reports first" does not (4+2=6>5) -- stop there, never skip ahead.
    candidates = reconstruct_bias_phrases(REAL_SHAPE_CONTEXT_TEXT, max_tokens=5)
    assert candidates == ["goldman sachs", "sachs reports"]
    assert sum(len(phrase.split()) for phrase in candidates) == 4


def test_reconstruct_bias_phrases_with_an_odd_budget_never_overfills():
    candidates = reconstruct_bias_phrases(REAL_SHAPE_CONTEXT_TEXT, max_tokens=3)
    assert candidates == ["goldman sachs"]
    assert sum(len(phrase.split()) for phrase in candidates) == 2


def test_reconstruct_bias_phrases_default_budget_caps_at_50_entries_when_the_source_has_enough_tokens():
    """The real corpus (745-947 lines/call, docs/readiness/2026-08-09-conec-
    evidence-shape.md) always has far more than 50 distinct adjacent pairs,
    so the default 100-word budget is reliably exhausted -- exactly matching
    the bag arm's own 100-word content volume at its default cap."""

    text = "\n".join(f"tok{i} 1" for i in range(300)) + "\n"
    candidates = reconstruct_bias_phrases(text)
    assert len(candidates) == 50
    assert sum(len(phrase.split()) for phrase in candidates) == 100


def test_reconstruct_bias_phrases_too_small_a_budget_yields_nothing():
    assert reconstruct_bias_phrases(REAL_SHAPE_CONTEXT_TEXT, max_tokens=1) == []


def test_reconstruct_bias_phrases_yields_nothing_on_a_single_token_run():
    assert reconstruct_bias_phrases("solo 1\n") == []


def test_reconstruct_bias_phrases_yields_nothing_when_no_listline_shape_present():
    assert reconstruct_bias_phrases("ctx") == []


@pytest.mark.parametrize("bad", [0, -1, 1.5, True, "100", None])
def test_reconstruct_bias_phrases_rejects_a_bad_max_tokens(bad):
    with pytest.raises(EvidenceError, match="bias_phrase_max_tokens"):
        reconstruct_bias_phrases(REAL_SHAPE_CONTEXT_TEXT, max_tokens=bad)


def test_reconstruct_bias_phrases_rejects_non_string_text():
    with pytest.raises(EvidenceError, match="text"):
        reconstruct_bias_phrases(None)


# ---------------------------------------------------------------------------
# The budget-matching claim itself, pinned as a regression: the phrase arm's
# default budget equals the bag arm's default entry count (a bag entry is
# always exactly one word, so this IS the word-content match).
# ---------------------------------------------------------------------------


def test_phrase_budget_matches_the_bag_arms_default_content_volume():
    assert DEFAULT_BIAS_PHRASE_MAX_TOKENS == DEFAULT_BIAS_LIST_MAX_ENTRIES == 100


# ---------------------------------------------------------------------------
# resolve_bias_phrase_max_tokens -- the config knob resolver.
# ---------------------------------------------------------------------------


def test_resolve_bias_phrase_max_tokens_defaults_when_values_is_none():
    assert resolve_bias_phrase_max_tokens(None) == DEFAULT_BIAS_PHRASE_MAX_TOKENS


def test_resolve_bias_phrase_max_tokens_defaults_when_key_absent():
    assert resolve_bias_phrase_max_tokens({}) == DEFAULT_BIAS_PHRASE_MAX_TOKENS


def test_resolve_bias_phrase_max_tokens_reads_the_config_knob():
    assert resolve_bias_phrase_max_tokens({"bias_phrase_max_tokens": 12}) == 12


def test_resolve_bias_phrase_max_tokens_rejects_a_bad_value():
    with pytest.raises(EvidenceError, match="bias_phrase_max_tokens"):
        resolve_bias_phrase_max_tokens({"bias_phrase_max_tokens": 0})


def test_resolve_bias_phrase_max_tokens_rejects_a_non_mapping_values():
    with pytest.raises(EvidenceError, match="mapping"):
        resolve_bias_phrase_max_tokens(123)


# ---------------------------------------------------------------------------
# The registered transform (core.evidence_derivation.TRANSFORMS): the SAME
# function the evidence source and the derivation registry both call --
# deliverable's "no second, independently drifting copy of this logic".
# ---------------------------------------------------------------------------


def test_conec_bias_phrase_content_is_registered_and_deterministic():
    spec = TRANSFORMS.resolve("conec-bias-phrases", "v1")
    params = {"max_tokens": DEFAULT_BIAS_PHRASE_MAX_TOKENS}
    first = spec.apply(REAL_SHAPE_CONTEXT_TEXT, params)
    second = conec_bias_phrase_content(REAL_SHAPE_CONTEXT_TEXT, params)
    assert first == second
    assert first == conec_bias_phrase_content(REAL_SHAPE_CONTEXT_TEXT, dict(params))


def test_conec_bias_phrase_content_shape():
    content = conec_bias_phrase_content(REAL_SHAPE_CONTEXT_TEXT, {"max_tokens": 100})
    assert content.startswith("ConEC-derived reconstructed phrase candidates")
    assert "goldman sachs" in content
    assert "financial results" in content


def test_conec_bias_phrase_content_rejects_a_non_mapping_params():
    with pytest.raises(EvidenceError, match="mapping"):
        conec_bias_phrase_content(REAL_SHAPE_CONTEXT_TEXT, "not-a-mapping")


def test_conec_bias_phrase_content_raises_on_empty_reconstruction():
    with pytest.raises(EvidenceError, match="no phrase candidates"):
        conec_bias_phrase_content("ctx", {"max_tokens": 100})


# ---------------------------------------------------------------------------
# The registered evidence source: wiring, cap, and fail-closed shapes.
# ---------------------------------------------------------------------------


def test_conec_bias_phrases_source_wiring_and_content_shape(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    items = EVIDENCE_SOURCES.resolve("conec-bias-phrases")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )
    assert len(items) == 1
    item = items[0]
    assert item.evidence_id == f"conec-bias-phrases/{bias_list_world.sample_id}"
    assert item.content.startswith("ConEC-derived reconstructed phrase candidates")
    # BIAS_WORLD_CONEC_CONTEXT_TEXT's one listline run is
    # danaher/corporation/ponton/nyse (conftest.py) -- overlapping bigrams:
    for expected in ("danaher corporation", "corporation ponton", "ponton nyse"):
        assert expected in item.content
    assert item.provenance["lock_key"] == "conec"
    assert item.provenance["extraction"] == "conec-bias-phrases-v1"
    assert item.provenance["candidate_count"] == 3
    assert item.provenance["max_tokens"] == DEFAULT_BIAS_PHRASE_MAX_TOKENS
    assert len(item.provenance["sha256"]) == 64


def test_conec_bias_phrases_source_respects_the_config_cap(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    items = EVIDENCE_SOURCES.resolve("conec-bias-phrases")(
        lock,
        bias_list_world.data_root,
        bias_list_world.sample_id,
        "earnings21-original",
        {"bias_phrase_max_tokens": 4},
    )
    item = items[0]
    assert item.provenance["candidate_count"] == 2
    assert item.provenance["max_tokens"] == 4
    assert "danaher corporation" in item.content
    assert "corporation ponton" in item.content
    assert "ponton nyse" not in item.content


def test_conec_bias_phrases_source_fails_closed_when_reconstruction_is_empty(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="no phrase candidates"):
        EVIDENCE_SOURCES.resolve("conec-bias-phrases")(
            lock, synthetic_world.data_root, "4000001", "earnings21-original"
        )


def test_conec_bias_phrases_source_fails_closed_for_a_carrier_with_no_evidence_layer(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="no ConEC evidence layer"):
        EVIDENCE_SOURCES.resolve("conec-bias-phrases")(
            lock, synthetic_world.data_root, "5000000", "earnings22-original"
        )


def test_conec_bias_phrases_source_fails_closed_when_missing(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="missing"):
        EVIDENCE_SOURCES.resolve("conec-bias-phrases")(
            lock, synthetic_world.data_root, "0000000", "earnings21-original"
        )


def test_conec_bias_phrases_never_reaches_oracle_content(bias_list_world):
    """Direct check of the task's own leakage-boundary requirement: this path
    never opens oracle_list.txt at all (unlike distractor-only-bias-list,
    which legitimately reads it to compute a set difference) -- also proven
    across the WHOLE registry by test_bias_lists.py's own oracle-unreachable
    tests, which now cover this source automatically once registered."""

    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-bias-phrases")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )[0]
    lowered = item.content.casefold()
    for oracle_term in BIAS_WORLD_ORACLE_TERMS:
        assert oracle_term.casefold() not in lowered
    oracle_relpath = bias_list_relpath(lock, "oracle_list.txt")
    assert oracle_relpath not in item.derivation.source_relpath


# ---------------------------------------------------------------------------
# Derivation-chain wiring (core.evidence_derivation.DerivedEvidenceRegistry):
# the happy path, plus the SOURCE/PARAMS/unregistered-transform refusals.
# ---------------------------------------------------------------------------


def test_conec_bias_phrases_derivation_record_chains_and_is_carrier_bound(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-bias-phrases")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )[0]
    record = item.derivation
    assert record is not None
    assert record.sample_id == bias_list_world.sample_id
    assert record.carrier_bound is True
    assert record.transform_name == "conec-bias-phrases"
    assert record.transform_version == "v1"
    assert record.source_relpath == (
        f"datasets/conec/earnings21/contexts/{bias_list_world.sample_id}.txt"
    )
    params = resolve_declared_transform_params(record.transform_name, None)
    registry = DerivedEvidenceRegistry()
    registry.register(
        record,
        source_content=item.derivation_source_bytes,
        derived_content=item.content.encode("utf-8"),
        params=params,
    )


def test_conec_bias_phrases_derivation_refused_when_the_source_file_is_tampered(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-bias-phrases")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )[0]
    params = resolve_declared_transform_params(item.derivation.transform_name, None)
    registry = DerivedEvidenceRegistry()
    with pytest.raises(DerivedEvidenceError, match="broke at SOURCE"):
        registry.register(
            item.derivation,
            source_content=b"tampered conec context, not what was actually read",
            derived_content=item.content.encode("utf-8"),
            params=params,
        )


def test_conec_bias_phrases_derivation_refused_on_wrong_params_hash(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-bias-phrases")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )[0]
    registry = DerivedEvidenceRegistry()
    with pytest.raises(DerivedEvidenceError, match="broke at PARAMS"):
        registry.register(
            item.derivation,
            source_content=item.derivation_source_bytes,
            derived_content=item.content.encode("utf-8"),
            params={"max_tokens": 4},  # the source actually used the default (100)
        )


def test_conec_bias_phrases_derivation_refused_for_an_unregistered_transform_name(bias_list_world):
    from dataclasses import replace

    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-bias-phrases")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )[0]
    forged = replace(item.derivation, transform_name="not-a-real-transform")
    params = resolve_declared_transform_params("conec-bias-phrases", None)
    registry = DerivedEvidenceRegistry()
    with pytest.raises(DerivedEvidenceError, match="unregistered transform"):
        registry.register(
            forged,
            source_content=item.derivation_source_bytes,
            derived_content=item.content.encode("utf-8"),
            params=params,
        )


def test_resolve_declared_transform_params_for_conec_bias_phrases():
    assert resolve_declared_transform_params("conec-bias-phrases", None) == {
        "max_tokens": DEFAULT_BIAS_PHRASE_MAX_TOKENS
    }
    assert resolve_declared_transform_params(
        "conec-bias-phrases", {"bias_phrase_max_tokens": 12}
    ) == {"max_tokens": 12}


# ---------------------------------------------------------------------------
# The config fragment (configs/baseline/bias-phrases-ojw.json): composes, and
# differs from the bag arm (bias-conec-obsloop.json) in exactly the intended
# keys -- evidence_source, and the budget knob (bias_list_max_entries drops
# out, bias_phrase_max_tokens appears -- a rename shows up as two changed
# keys in a raw key-set diff, not one).
# ---------------------------------------------------------------------------


def _load_baseline(name: str) -> dict:
    return json.loads((BASELINE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _diff_keys(a: dict, b: dict) -> set:
    keys = set(a) | set(b)
    return {key for key in keys if a.get(key, object()) != b.get(key, object())}


def test_bias_phrases_ojw_differs_from_bias_conec_obsloop_in_exactly_the_intended_keys():
    bag = _load_baseline("bias-conec-obsloop")
    phrases = _load_baseline("bias-phrases-ojw")
    assert _diff_keys(bag, phrases) == {
        "evidence_source",
        "bias_list_max_entries",
        "bias_phrase_max_tokens",
    }
    assert bag["evidence_source"] == "conec-bias-list"
    assert phrases["evidence_source"] == "conec-bias-phrases"
    assert "bias_phrase_max_tokens" not in bag
    assert "bias_list_max_entries" not in phrases


def test_bias_phrases_ojw_fragment_composes_with_the_b2a_experiment_and_r4_split():
    composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp", "r4-e21-sub10", "bias-phrases-ojw", "b2a-bias-lists"
    )
    assert composed.values["arm"] == "fixed-legal-context"
    assert composed.values["policy"] == "obs-agent-loop-ojw"
    assert composed.values["evidence_source"] == "conec-bias-phrases"
    assert composed.values["evidence_mismatch"] is False
    assert composed.values["bias_phrase_max_tokens"] == DEFAULT_BIAS_PHRASE_MAX_TOKENS
    assert composed.values["scorers"] == ["asr-wer", "cost"]
    assert composed.values["carrier_lock_key"] == "earnings21-original"
    assert composed.values["split_name"] == "r4-e21-sub10-sample"
    assert composed.values["experiment_id"] == "SAEA-E-003"
    assert composed.values["model_lock_key"] == "qwen3-omni-30b-a3b-instruct-gguf"


def test_bias_conec_obsloop_fragment_still_composes_with_the_b2a_experiment_and_r4_split():
    """The bag arm this task's phrase arm is contrasted against, now that
    both share docs/arms/b2a-bias-lists.arms -- proven runnable through the
    real compose() pipeline, not merely readable as JSON."""

    composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp", "r4-e21-sub10", "bias-conec-obsloop", "b2a-bias-lists"
    )
    assert composed.values["evidence_source"] == "conec-bias-list"
    assert composed.values["bias_list_max_entries"] == DEFAULT_BIAS_LIST_MAX_ENTRIES
    assert composed.values["experiment_id"] == "SAEA-E-003"
