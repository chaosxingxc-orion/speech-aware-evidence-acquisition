"""B-2a bias-list support: deterministic extraction, the distractor-only set
difference, the two registered evidence sources, and the oracle-unreachable
guard (docs/readiness/2026-08-09-exploration-plan.md section 3b).
"""

import pytest

from speech_aware_evidence_acquisition.core import evidence  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import EVIDENCE_SOURCES, EvidenceError
from speech_aware_evidence_acquisition.core.bias_lists import (
    DEFAULT_BIAS_LIST_MAX_ENTRIES,
    _assert_no_oracle_overlap,
    distractor_only_terms,
    extract_bias_candidates,
    format_bias_list_content,
    resolve_bias_list_max_entries,
)
from speech_aware_evidence_acquisition.core.evidence import OracleEvidenceError
from speech_aware_evidence_acquisition.data.lock import load_lock

from conftest import (
    BIAS_WORLD_CONEC_CONTEXT_TEXT,
    BIAS_WORLD_DISTRACTOR_ONLY_TERMS,
    BIAS_WORLD_ORACLE_TERMS,
)

# ---------------------------------------------------------------------------
# extract_bias_candidates -- pure function, no fixture needed
# ---------------------------------------------------------------------------


def test_extract_bias_candidates_is_deterministic():
    text = BIAS_WORLD_CONEC_CONTEXT_TEXT
    assert extract_bias_candidates(text) == extract_bias_candidates(text)


def test_extract_bias_candidates_captures_roster_lines():
    candidates = extract_bias_candidates(BIAS_WORLD_CONEC_CONTEXT_TEXT)
    assert "Maureen Mulholland - Senior Vice President, General Counsel" in candidates
    assert "Brett Ponton - President and CEO" in candidates


def test_extract_bias_candidates_captures_capitalized_spans_with_ampersand():
    candidates = extract_bias_candidates(BIAS_WORLD_CONEC_CONTEXT_TEXT)
    assert "Goldman Sachs & Co" in candidates


def test_extract_bias_candidates_captures_listline_tokens():
    candidates = extract_bias_candidates(BIAS_WORLD_CONEC_CONTEXT_TEXT)
    for token in ("danaher", "corporation", "ponton", "nyse"):
        assert token in candidates


def test_extract_bias_candidates_captures_ticker_tokens():
    candidates = extract_bias_candidates(BIAS_WORLD_CONEC_CONTEXT_TEXT)
    assert "IBM" in candidates


def test_extract_bias_candidates_preserves_first_appearance_order():
    candidates = extract_bias_candidates(BIAS_WORLD_CONEC_CONTEXT_TEXT)
    assert candidates == [
        "Maureen Mulholland - Senior Vice President, General Counsel",
        "Brett Ponton - President and CEO",
        "Goldman Sachs & Co",
        "danaher",
        "corporation",
        "ponton",
        "nyse",
        "IBM",
    ]


def test_extract_bias_candidates_dedupes_case_insensitively_keeping_first_seen_casing():
    text = "Danaher 1\nDANAHER 1\ndanaher 1\n"
    assert extract_bias_candidates(text) == ["Danaher"]


def test_extract_bias_candidates_caps_to_max_entries():
    text = "alpha 1\nbeta 1\ngamma 1\ndelta 1\n"
    assert extract_bias_candidates(text, max_entries=2) == ["alpha", "beta"]


def test_extract_bias_candidates_listline_requires_min_length_three():
    text = "us 1\nny 1\nc 1\nabc 1\n"
    assert extract_bias_candidates(text) == ["abc"]


def test_extract_bias_candidates_on_a_plain_ctx_fixture_yields_nothing():
    # The trivial "ctx" content the shared synthetic_world fixture uses for
    # every OTHER conec-contexts test (test_core_components.py,
    # test_driver.py) matches none of the four patterns -- confirms the
    # evidence source (not this pure function) is the one that must fail
    # closed on an empty extraction, exercised separately below.
    assert extract_bias_candidates("ctx") == []


@pytest.mark.parametrize("bad", [0, -1, 1.5, True, "100", None])
def test_extract_bias_candidates_rejects_a_bad_max_entries(bad):
    with pytest.raises(EvidenceError, match="bias_list_max_entries"):
        extract_bias_candidates("alpha 1\n", max_entries=bad)


def test_extract_bias_candidates_rejects_non_string_text():
    with pytest.raises(EvidenceError, match="text"):
        extract_bias_candidates(None)


# ---------------------------------------------------------------------------
# format_bias_list_content
# ---------------------------------------------------------------------------


def test_format_bias_list_content_shape():
    content = format_bias_list_content(["alpha", "beta"], "HEADER:")
    assert content == "HEADER:\nalpha\nbeta"


def test_format_bias_list_content_rejects_empty_candidates():
    with pytest.raises(EvidenceError, match="candidates"):
        format_bias_list_content([], "HEADER:")


def test_format_bias_list_content_rejects_empty_header():
    with pytest.raises(EvidenceError, match="header"):
        format_bias_list_content(["alpha"], "")


# ---------------------------------------------------------------------------
# resolve_bias_list_max_entries
# ---------------------------------------------------------------------------


def test_resolve_bias_list_max_entries_defaults_when_values_is_none():
    assert resolve_bias_list_max_entries(None) == DEFAULT_BIAS_LIST_MAX_ENTRIES


def test_resolve_bias_list_max_entries_defaults_when_key_absent():
    assert resolve_bias_list_max_entries({}) == DEFAULT_BIAS_LIST_MAX_ENTRIES


def test_resolve_bias_list_max_entries_reads_the_config_knob():
    assert resolve_bias_list_max_entries({"bias_list_max_entries": 7}) == 7


def test_resolve_bias_list_max_entries_rejects_a_bad_value():
    with pytest.raises(EvidenceError, match="bias_list_max_entries"):
        resolve_bias_list_max_entries({"bias_list_max_entries": 0})


# ---------------------------------------------------------------------------
# _assert_no_oracle_overlap -- the defensive re-verification, tested directly
# ---------------------------------------------------------------------------


def test_assert_no_oracle_overlap_passes_when_disjoint():
    _assert_no_oracle_overlap(["ZQXVBIAS DELTA"], ["ZQXVBIAS ALPHA", "ZQXVBIAS BRAVO"])


def test_assert_no_oracle_overlap_raises_on_a_leak():
    with pytest.raises(EvidenceError, match="leaks"):
        _assert_no_oracle_overlap(["ZQXVBIAS ALPHA"], ["ZQXVBIAS ALPHA", "ZQXVBIAS BRAVO"])


def test_assert_no_oracle_overlap_is_case_insensitive():
    with pytest.raises(EvidenceError, match="leaks"):
        _assert_no_oracle_overlap(["zqxvbias alpha"], ["ZQXVBIAS ALPHA"])


# ---------------------------------------------------------------------------
# distractor_only_terms -- the set difference, computed from the two files
# ---------------------------------------------------------------------------


def test_distractor_only_terms_is_the_set_difference(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    terms, facts = distractor_only_terms(lock, bias_list_world.data_root)
    assert terms == list(BIAS_WORLD_DISTRACTOR_ONLY_TERMS)
    for oracle_term in BIAS_WORLD_ORACLE_TERMS:
        assert oracle_term not in terms
    assert facts["distractor_only_total"] == len(BIAS_WORLD_DISTRACTOR_ONLY_TERMS)
    assert len(facts["oracle_sha256"]) == 64
    assert len(facts["distractor_sha256"]) == 64
    assert facts["oracle_relpath"] == "datasets/earnings21-22/earnings21/bias_lists/oracle_list.txt"
    assert (
        facts["distractor_relpath"]
        == "datasets/earnings21-22/earnings21/bias_lists/distractor_list.txt"
    )


def test_distractor_only_terms_caps_and_reports_the_uncapped_total(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    terms, facts = distractor_only_terms(lock, bias_list_world.data_root, max_entries=1)
    assert terms == [BIAS_WORLD_DISTRACTOR_ONLY_TERMS[0]]
    assert facts["distractor_only_total"] == len(BIAS_WORLD_DISTRACTOR_ONLY_TERMS)


def test_distractor_only_terms_fails_closed_on_a_missing_oracle_file(tmp_path):
    import json

    data_root = tmp_path / "data"
    (data_root / "datasets" / "earnings21-22" / "earnings21" / "bias_lists").mkdir(parents=True)
    (
        data_root / "datasets" / "earnings21-22" / "earnings21" / "bias_lists" / "distractor_list.txt"
    ).write_text("ZQXVBIAS ALPHA\n", encoding="utf-8")
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "name": "earnings21-original",
                        "local_subdir": "datasets/earnings21-22/earnings21",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    lock = load_lock(lock_path)
    with pytest.raises(EvidenceError, match="missing"):
        distractor_only_terms(lock, data_root)


# ---------------------------------------------------------------------------
# The two registered evidence sources
# ---------------------------------------------------------------------------


def test_conec_bias_list_source_wiring_and_content_shape(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    items = EVIDENCE_SOURCES.resolve("conec-bias-list")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )
    assert len(items) == 1
    item = items[0]
    assert item.evidence_id == f"conec-bias-list/{bias_list_world.sample_id}"
    assert item.content.startswith("ConEC-derived bias candidates")
    for expected in ("Brett Ponton - President and CEO", "danaher", "IBM"):
        assert expected in item.content
    assert item.provenance["lock_key"] == "conec"
    assert item.provenance["extraction"] == "conec-bias-list-v1"
    assert item.provenance["candidate_count"] == 8
    assert item.provenance["max_entries"] == DEFAULT_BIAS_LIST_MAX_ENTRIES
    assert len(item.provenance["sha256"]) == 64


def test_conec_bias_list_source_respects_the_config_cap(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    items = EVIDENCE_SOURCES.resolve("conec-bias-list")(
        lock,
        bias_list_world.data_root,
        bias_list_world.sample_id,
        "earnings21-original",
        {"bias_list_max_entries": 2},
    )
    item = items[0]
    assert item.provenance["candidate_count"] == 2
    assert item.provenance["max_entries"] == 2
    lines = item.content.splitlines()
    assert lines[1:] == [
        "Maureen Mulholland - Senior Vice President, General Counsel",
        "Brett Ponton - President and CEO",
    ]
    assert "Goldman Sachs & Co" not in item.content


def test_conec_bias_list_source_fails_closed_when_extraction_is_empty(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="no bias-candidate entities"):
        EVIDENCE_SOURCES.resolve("conec-bias-list")(
            lock, synthetic_world.data_root, "4000001", "earnings21-original"
        )


def test_conec_bias_list_source_fails_closed_for_a_carrier_with_no_evidence_layer(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="no ConEC evidence layer"):
        EVIDENCE_SOURCES.resolve("conec-bias-list")(
            lock, synthetic_world.data_root, "5000000", "earnings22-original"
        )


def test_conec_bias_list_source_fails_closed_when_missing(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="missing"):
        EVIDENCE_SOURCES.resolve("conec-bias-list")(
            lock, synthetic_world.data_root, "0000000", "earnings21-original"
        )


def test_distractor_only_bias_list_source_wiring_and_content_shape(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    items = EVIDENCE_SOURCES.resolve("distractor-only-bias-list")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )
    assert len(items) == 1
    item = items[0]
    assert item.evidence_id == f"distractor-only-bias-list/{bias_list_world.sample_id}"
    for term in BIAS_WORLD_DISTRACTOR_ONLY_TERMS:
        assert term in item.content
    for term in BIAS_WORLD_ORACLE_TERMS:
        assert term not in item.content
    assert item.provenance["extraction"] == "distractor-only-v1"
    assert item.provenance["candidate_count"] == len(BIAS_WORLD_DISTRACTOR_ONLY_TERMS)
    assert item.provenance["distractor_only_total"] == len(BIAS_WORLD_DISTRACTOR_ONLY_TERMS)
    assert item.provenance["lock_key"] == "earnings21-original"
    assert len(item.provenance["oracle_sha256"]) == 64


def test_distractor_only_bias_list_source_respects_the_config_cap(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    items = EVIDENCE_SOURCES.resolve("distractor-only-bias-list")(
        lock,
        bias_list_world.data_root,
        bias_list_world.sample_id,
        "earnings21-original",
        {"bias_list_max_entries": 1},
    )
    item = items[0]
    assert item.provenance["candidate_count"] == 1
    assert BIAS_WORLD_DISTRACTOR_ONLY_TERMS[0] in item.content
    assert BIAS_WORLD_DISTRACTOR_ONLY_TERMS[1] not in item.content


def test_distractor_only_bias_list_source_fails_closed_for_a_non_earnings21_carrier(
    bias_list_world,
):
    lock = load_lock(bias_list_world.lock_path)
    with pytest.raises(EvidenceError, match="no bias-list layer"):
        EVIDENCE_SOURCES.resolve("distractor-only-bias-list")(
            lock, bias_list_world.data_root, "anything", "earnings22-original"
        )


# ---------------------------------------------------------------------------
# The oracle-unreachable guard: no registered evidence source can ever
# return oracle-list content, exercised across the WHOLE registry (not a
# hardcoded name list) so a future source is covered automatically.
# ---------------------------------------------------------------------------


def test_oracle_source_is_still_unreachable():
    with pytest.raises(OracleEvidenceError, match="scoring-side"):
        EVIDENCE_SOURCES.resolve("oracle")(None, None, "x", "earnings21-original")


def test_no_registered_evidence_source_can_return_oracle_content(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    checked = []
    for name in EVIDENCE_SOURCES.names():
        try:
            items = EVIDENCE_SOURCES.resolve(name)(
                lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
            )
        except (EvidenceError, OracleEvidenceError):
            continue
        checked.append(name)
        for item in items:
            lowered = item.content.casefold()
            for oracle_term in BIAS_WORLD_ORACLE_TERMS:
                assert oracle_term.casefold() not in lowered, (
                    f"evidence source {name!r} leaked oracle content {oracle_term!r}"
                )
    # At least the sources this fixture can actually satisfy were exercised
    # (never a vacuous pass because every source raised).
    assert {"none", "conec-contexts", "conec-bias-list", "distractor-only-bias-list"} <= set(
        checked
    )
