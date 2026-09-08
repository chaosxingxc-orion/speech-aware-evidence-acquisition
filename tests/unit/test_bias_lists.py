"""B-2a bias-list support: deterministic extraction, the distractor-only set
difference, the two registered evidence sources, and the oracle-unreachable
guard (docs/readiness/2026-08-09-exploration-plan.md section 3b).
"""

import pytest

from speech_aware_evidence_acquisition.core import evidence  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import (
    EVIDENCE_SOURCES,
    EvidenceError,
    FrozenHistoricalComponent,
)
from speech_aware_evidence_acquisition.core.bias_lists import (
    DEFAULT_BIAS_LIST_MAX_ENTRIES,
    _assert_no_oracle_overlap,
    bias_list_relpath,
    conec_bias_list_content,
    distractor_only_content,
    distractor_only_source_document,
    distractor_only_source_texts,
    distractor_only_terms,
    extract_bias_candidates,
    format_bias_list_content,
    resolve_bias_list_max_entries,
)
from speech_aware_evidence_acquisition.core.evidence import (
    OracleEvidenceError,
    resolve_declared_transform_params,
)
from speech_aware_evidence_acquisition.core.evidence_derivation import (
    TRANSFORMS,
    DerivedEvidenceError,
    DerivedEvidenceRegistry,
)
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
        source = EVIDENCE_SOURCES.resolve(name)
        if isinstance(source, FrozenHistoricalComponent):
            # WAVE R7 (2026-09-08): a retired Audio2Tool AgentLoop id resolves so
            # the base can account for it and REFUSES every call, so it cannot
            # leak anything -- there is nothing to call. Skipped by TYPE rather
            # than by catching its refusal, so a live source that started
            # raising CoreError could never hide here.
            continue
        try:
            items = source(
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


# ---------------------------------------------------------------------------
# The registered pure transforms (core.evidence_derivation.TRANSFORMS):
# determinism + agreement with the evidence source's own content (deliverable
# 4/5 -- "no second, independently drifting copy of this logic").
# ---------------------------------------------------------------------------


def test_conec_bias_list_content_is_registered_and_deterministic():
    spec = TRANSFORMS.resolve("conec-bias-list", "v1")
    params = {"max_entries": DEFAULT_BIAS_LIST_MAX_ENTRIES}
    first = spec.apply(BIAS_WORLD_CONEC_CONTEXT_TEXT, params)
    second = conec_bias_list_content(BIAS_WORLD_CONEC_CONTEXT_TEXT, params)
    assert first == second
    assert first == conec_bias_list_content(BIAS_WORLD_CONEC_CONTEXT_TEXT, dict(params))


def test_conec_bias_list_content_matches_the_evidence_source_own_content(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-bias-list")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )[0]
    params = {"max_entries": DEFAULT_BIAS_LIST_MAX_ENTRIES}
    assert conec_bias_list_content(BIAS_WORLD_CONEC_CONTEXT_TEXT, params) == item.content


def test_conec_bias_list_content_rejects_a_non_mapping_params():
    with pytest.raises(EvidenceError, match="mapping"):
        conec_bias_list_content("alpha 1\n", "not-a-mapping")


def test_distractor_only_source_texts_reads_both_shipped_files(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    oracle_text, distractor_text, oracle_relpath, distractor_relpath = (
        distractor_only_source_texts(lock, bias_list_world.data_root)
    )
    for term in BIAS_WORLD_ORACLE_TERMS:
        assert term in oracle_text
    for term in list(BIAS_WORLD_ORACLE_TERMS) + list(BIAS_WORLD_DISTRACTOR_ONLY_TERMS):
        assert term in distractor_text
    assert oracle_relpath == bias_list_relpath(lock, "oracle_list.txt")
    assert distractor_relpath == bias_list_relpath(lock, "distractor_list.txt")


def test_distractor_only_content_is_registered_and_deterministic(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    oracle_text, distractor_text, oracle_relpath, distractor_relpath = (
        distractor_only_source_texts(lock, bias_list_world.data_root)
    )
    document = distractor_only_source_document(
        oracle_text, distractor_text, oracle_relpath, distractor_relpath
    )
    params = {"max_entries": DEFAULT_BIAS_LIST_MAX_ENTRIES}
    spec = TRANSFORMS.resolve("distractor-only", "v1")
    first = spec.apply(document, params)
    second = distractor_only_content(document, params)
    assert first == second
    # Two INDEPENDENT calls (a freshly rebuilt document each time) -> the
    # SAME derived bytes (deliverable 5's determinism requirement).
    rebuilt_document = distractor_only_source_document(
        oracle_text, distractor_text, oracle_relpath, distractor_relpath
    )
    assert distractor_only_content(rebuilt_document, params) == first


def test_distractor_only_content_matches_the_evidence_source_own_content(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("distractor-only-bias-list")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )[0]
    oracle_text, distractor_text, oracle_relpath, distractor_relpath = (
        distractor_only_source_texts(lock, bias_list_world.data_root)
    )
    document = distractor_only_source_document(
        oracle_text, distractor_text, oracle_relpath, distractor_relpath
    )
    params = {"max_entries": DEFAULT_BIAS_LIST_MAX_ENTRIES}
    assert distractor_only_content(document, params) == item.content


def test_distractor_only_content_rejects_malformed_source_documents():
    with pytest.raises(EvidenceError, match="not valid JSON"):
        distractor_only_content("not json", {"max_entries": 5})
    with pytest.raises(EvidenceError, match="missing oracle_text/distractor_text"):
        distractor_only_content("{}", {"max_entries": 5})


# ---------------------------------------------------------------------------
# Derivation-chain wiring (2026-08-09, docs/readiness/2026-08-09-conec-
# evidence-shape.md "Blocking gap"): every source's EvidenceItem carries a
# DerivedEvidenceRecord that core.evidence_derivation.DerivedEvidenceRegistry
# accepts end to end using the SOURCE's own real content -- deliverable 6's
# "happy path per source" for conec-bias-list/distractor-only-bias-list
# (conec-contexts' own is covered in test_core_components.py).
# ---------------------------------------------------------------------------


def test_conec_bias_list_derivation_record_chains_and_is_carrier_bound(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-bias-list")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )[0]
    record = item.derivation
    assert record is not None
    assert record.sample_id == bias_list_world.sample_id
    assert record.carrier_bound is True
    assert record.transform_name == "conec-bias-list"
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


def test_distractor_only_derivation_record_chains_and_is_not_carrier_bound(bias_list_world):
    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("distractor-only-bias-list")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )[0]
    record = item.derivation
    assert record is not None
    assert record.sample_id == bias_list_world.sample_id
    # The honest treatment (deliverable 3): NO per-sample carrier binding --
    # this arm's source is the combined bias_lists/ corpus, never a
    # fabricated single-file per-sample path.
    assert record.carrier_bound is False
    assert record.transform_name == "distractor-only"
    oracle_relpath = bias_list_relpath(lock, "oracle_list.txt")
    distractor_relpath = bias_list_relpath(lock, "distractor_list.txt")
    assert record.source_relpath == f"{oracle_relpath}+{distractor_relpath}"
    params = resolve_declared_transform_params(record.transform_name, None)
    registry = DerivedEvidenceRegistry()
    registry.register(
        record,
        source_content=item.derivation_source_bytes,
        derived_content=item.content.encode("utf-8"),
        params=params,
    )


def test_conec_bias_list_derivation_refused_when_the_source_file_is_tampered(bias_list_world):
    """A tampered source (the ConEC context file this arm derives from) must
    break the chain at SOURCE -- never silently re-hash the tampered bytes."""

    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-bias-list")(
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


def test_conec_bias_list_derivation_refused_on_wrong_params_hash(bias_list_world):
    """The run's config declares a DIFFERENT bias_list_max_entries than the
    source used -- the chain must break at PARAMS."""

    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-bias-list")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )[0]
    registry = DerivedEvidenceRegistry()
    with pytest.raises(DerivedEvidenceError, match="broke at PARAMS"):
        registry.register(
            item.derivation,
            source_content=item.derivation_source_bytes,
            derived_content=item.content.encode("utf-8"),
            params={"max_entries": 1},  # the source actually used the default (100)
        )


def test_conec_bias_list_derivation_refused_for_an_unregistered_transform_name(bias_list_world):
    from dataclasses import replace

    lock = load_lock(bias_list_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-bias-list")(
        lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
    )[0]
    forged = replace(item.derivation, transform_name="not-a-real-transform")
    params = resolve_declared_transform_params("conec-bias-list", None)
    registry = DerivedEvidenceRegistry()
    with pytest.raises(DerivedEvidenceError, match="unregistered transform"):
        registry.register(
            forged,
            source_content=item.derivation_source_bytes,
            derived_content=item.content.encode("utf-8"),
            params=params,
        )


def test_resolve_declared_transform_params_for_every_wired_transform():
    assert resolve_declared_transform_params("identity", None) == {}
    assert resolve_declared_transform_params("conec-bias-list", None) == {
        "max_entries": DEFAULT_BIAS_LIST_MAX_ENTRIES
    }
    assert resolve_declared_transform_params("distractor-only", {"bias_list_max_entries": 3}) == {
        "max_entries": 3
    }
    with pytest.raises(EvidenceError, match="no declared-params resolver"):
        resolve_declared_transform_params("not-a-real-transform", None)


# ---------------------------------------------------------------------------
# The oracle list must remain unreachable through any REGISTERED transform's
# WIRING, not merely through its returned content (deliverable 6): no
# evidence source's derivation record may ever name the oracle list file as
# its source.
# ---------------------------------------------------------------------------


def test_oracle_list_is_unreachable_through_any_registered_transforms_wiring(bias_list_world):
    """No source OTHER than ``distractor-only-bias-list`` may ever chain its
    derivation record to the oracle list file at all. ``distractor-only-
    bias-list`` legitimately READS it (to compute a set difference,
    core.bias_lists._distractor_only_from_terms) but must never apply the
    ``identity`` transform to a source that includes it -- that would just
    pass oracle content straight through; only the registered
    ``distractor-only`` transform may touch it, and that transform's own
    ``_assert_no_oracle_overlap`` guard is what keeps its OUTPUT oracle-free
    (proven directly by ``test_no_registered_evidence_source_can_return_
    oracle_content`` above)."""

    lock = load_lock(bias_list_world.lock_path)
    oracle_relpath = bias_list_relpath(lock, "oracle_list.txt")
    checked = []
    for name in EVIDENCE_SOURCES.names():
        source = EVIDENCE_SOURCES.resolve(name)
        if isinstance(source, FrozenHistoricalComponent):
            # WAVE R7 (2026-09-08): a retired Audio2Tool AgentLoop id resolves so
            # the base can account for it and REFUSES every call, so it cannot
            # leak anything -- there is nothing to call. Skipped by TYPE rather
            # than by catching its refusal, so a live source that started
            # raising CoreError could never hide here.
            continue
        try:
            items = source(
                lock, bias_list_world.data_root, bias_list_world.sample_id, "earnings21-original"
            )
        except (EvidenceError, OracleEvidenceError):
            continue
        for item in items:
            if item.derivation is None:
                continue
            checked.append(name)
            names_oracle = oracle_relpath in item.derivation.source_relpath.split("+")
            if names_oracle:
                assert name == "distractor-only-bias-list", (
                    f"evidence source {name!r} unexpectedly chains its derivation "
                    "record to the oracle list file"
                )
                assert item.derivation.transform_name != "identity", (
                    "distractor-only-bias-list must never apply the identity "
                    "transform to a source that includes the oracle list"
                )
            else:
                assert item.derivation.source_relpath != oracle_relpath, (
                    f"evidence source {name!r} chains its derivation record to the "
                    "oracle list file"
                )
    assert {"conec-contexts", "conec-bias-list", "distractor-only-bias-list"} <= set(checked)
