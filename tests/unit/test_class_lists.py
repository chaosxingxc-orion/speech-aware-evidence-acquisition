"""``conec-class-lists`` / ``conec-class-lists-placebo``: the E5 pre-meeting
brief, its form twin, and the construction/evaluation separation.

Every test here runs on a SYNTHETIC ConEC world (``synthetic_world``), so the
brief's shape is asserted against text this file writes rather than against
bytes on the real data root. The one thing that is asserted about the real
layout is the boundary: :func:`test_the_renderer_opens_no_reference_path`
records every path the evidence source touches and refuses anything outside
``contexts/``.
"""

from __future__ import annotations

import pathlib

import pytest

from speech_aware_evidence_acquisition.core.base import EVIDENCE_SOURCES, EvidenceError
from speech_aware_evidence_acquisition.core.class_lists import (
    CLASS_LIST_TRANSFORMS,
    DEFAULT_MAX_ENTRIES_PER_CLASS,
    PLACEHOLDER_WORDS,
    ClassListError,
    annotate_normalized,
    context_tokens,
    placebo_of,
    render_document_brief,
    render_roster_brief,
    roster_entries,
    whitespace_token_count,
)
from speech_aware_evidence_acquisition.core.evidence import (
    _conec_class_lists,
    _conec_class_lists_placebo,
    resolve_declared_transform_params,
)
from speech_aware_evidence_acquisition.core.evidence_derivation import (
    TRANSFORMS,
    DerivedEvidenceRegistry,
)
from speech_aware_evidence_acquisition.data.lock import load_lock

# A miniature press release in ConEC's own document shape: lowercased,
# function words stripped, one token per line, a constant count beside it.
DOCUMENT = "\n".join(
    f"{token} 1"
    for token in (
        "high point ncbusiness wire nyse culp inc today reported third quarter "
        "results mattress fabrics segment upholstery fabrics segment net sales "
        "million"
    ).split()
)

ROSTER = (
    "Dru Anderson - Senior Vice President and Investor Relations\n"
    "Boyd Chumbley - President of Culp Upholstery Fabric Division\n"
    "Robert Griffin - Raymond James & Associates, Inc.\n"
    "Marco Rodriguez - Stonegate Capital Markets\n"
)

CALL = "4320211"
OTHER_CALL = "4330115"


def _conec_dir(world):
    return world.conec / "earnings21" / "contexts"


def _install(world, sample_id=CALL, document=DOCUMENT, roster=ROSTER):
    """Replace the fixture's placeholder ConEC files with real-shaped ones."""

    contexts = _conec_dir(world)
    (contexts / f"{sample_id}.txt").write_text(document, encoding="utf-8")
    (contexts / "participant_names" / f"{sample_id}.names.txt").write_text(
        roster, encoding="utf-8"
    )
    return load_lock(world.lock_path)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_both_sources_and_all_four_transforms_are_registered():
    assert "conec-class-lists" in EVIDENCE_SOURCES.names()
    assert "conec-class-lists-placebo" in EVIDENCE_SOURCES.names()
    for name in CLASS_LIST_TRANSFORMS:
        assert TRANSFORMS.resolve(name, "v1").version == "v1"


def test_declared_transform_params_resolve_for_every_class_list_transform():
    for name in CLASS_LIST_TRANSFORMS:
        assert resolve_declared_transform_params(name, None) == {
            "max_entries_per_class": DEFAULT_MAX_ENTRIES_PER_CLASS
        }
        assert resolve_declared_transform_params(name, {"brief_max_entries_per_class": 5}) == {
            "max_entries_per_class": 5
        }


# ---------------------------------------------------------------------------
# Reading the two ConEC shapes
# ---------------------------------------------------------------------------


def test_roster_entries_split_on_conecs_own_separator():
    assert roster_entries(ROSTER)[0] == (
        "Dru Anderson",
        "Senior Vice President and Investor Relations",
    )
    assert roster_entries("Solo Speaker\n") == [("Solo Speaker", "")]


def test_context_tokens_keep_document_order_and_repeats():
    tokens = context_tokens(DOCUMENT)
    assert tokens[:4] == ["high", "point", "ncbusiness", "wire"]
    assert tokens.count("fabrics") == 2


def test_a_context_line_that_is_not_token_count_is_refused():
    with pytest.raises(ClassListError, match="not '<token> <count>'"):
        context_tokens("culp\ninc 1\n")


# ---------------------------------------------------------------------------
# The classes
# ---------------------------------------------------------------------------


def test_the_roster_brief_separates_participants_affiliations_and_divisions():
    brief = render_roster_brief(ROSTER, 0)
    lines = brief.splitlines()
    assert lines[0].startswith("Pre-meeting brief for this earnings call, part 1 of 2")
    participants = next(line for line in lines if line.startswith("Participants and roles: "))
    organizations = next(
        line for line in lines if line.startswith("Organizations named in the roster: ")
    )
    divisions = next(
        line for line in lines if line.startswith("Divisions and segments named in the roster: ")
    )
    # Every speaker appears; only the roles with no title cue are read as
    # outside organizations; the division comes off the role that names one.
    assert "Dru Anderson (Senior Vice President and Investor Relations)" in participants
    assert "Raymond James & Associates, Inc." in organizations
    assert "Stonegate Capital Markets" in organizations
    assert "Senior Vice President" not in organizations
    assert "Culp Upholstery Fabric Division" in divisions


def test_the_document_brief_reads_company_ticker_and_segment_candidates():
    brief = render_document_brief(DOCUMENT, 0)
    lines = brief.splitlines()
    assert lines[0].startswith("Pre-meeting brief for this earnings call, part 2 of 2")
    company = next(line for line in lines if line.startswith("Company and ticker candidates: "))
    segments = next(line for line in lines if line.startswith("Product and segment candidates: "))
    terms = next(
        line for line in lines if line.startswith("Other terms from the call's documents: ")
    )
    assert "culp inc" in company  # the legal-entity suffix takes the tokens before it
    assert "nyse culp" in company  # the exchange cue takes the token after it
    assert "mattress fabrics segment" in segments
    assert "upholstery fabrics segment" in segments
    assert "ncbusiness" in terms
    # The residual list is de-duplicated but keeps document order.
    residual = terms.partition(": ")[2].split("; ")
    assert residual.count("fabrics") == 1
    assert residual.index("high") < residual.index("million")


def test_the_cap_truncates_every_class_and_zero_means_the_whole_brief():
    capped = render_document_brief(DOCUMENT, 1)
    for line in capped.splitlines()[1:]:
        assert "; " not in line
    assert whitespace_token_count(render_document_brief(DOCUMENT, 0)) > whitespace_token_count(
        capped
    )


def test_a_negative_or_absurd_cap_is_refused():
    with pytest.raises(ClassListError, match="between 0"):
        render_document_brief(DOCUMENT, -1)


# ---------------------------------------------------------------------------
# The normalized-form annotation
# ---------------------------------------------------------------------------


def test_the_normalized_form_is_shown_only_where_casing_or_punctuation_moves():
    assert annotate_normalized("C.L. King") == "C.L. King [normalized: c l king]"
    assert annotate_normalized("Stonegate Capital Markets").startswith("Stonegate Capital Markets")
    # Both sides of every Earnings metric are normalized, so an all-lowercase
    # document token whose only change is the NUMBER normalizer is not
    # annotated: "third" and "million" already agree after normalization.
    assert annotate_normalized("third") == "third"
    assert annotate_normalized("million") == "million"


# ---------------------------------------------------------------------------
# The form twin
# ---------------------------------------------------------------------------


def test_the_placebo_holds_labels_lines_and_token_count_and_drops_the_content():
    brief = render_roster_brief(ROSTER, 0)
    twin = placebo_of(brief)
    assert whitespace_token_count(twin) == whitespace_token_count(brief)
    assert len(twin.splitlines()) == len(brief.splitlines())
    for line in brief.splitlines():
        label = line.partition(": ")[0]
        assert any(other.startswith(label) for other in twin.splitlines())
    for leaked in ("Dru", "Anderson", "Culp", "Raymond", "Stonegate"):
        assert leaked not in twin
    assert set(twin.splitlines()[1].partition(": ")[2].split()) <= set(PLACEHOLDER_WORDS)


def test_the_placebo_is_a_function_of_shape_alone():
    """Two calls whose briefs have the same shape get byte-identical twins --
    the property that makes this a FORM control rather than a second arm."""

    other = ROSTER.replace("Dru Anderson", "Ada Lovelace").replace("Culp", "Acme")
    assert placebo_of(render_roster_brief(ROSTER, 0)) == placebo_of(
        render_roster_brief(other, 0)
    )


def test_the_placebo_evidence_source_matches_the_arm_token_for_token(synthetic_world):
    lock = _install(synthetic_world)
    real = _conec_class_lists(lock, synthetic_world.data_root, CALL, "earnings21-original")
    twin = _conec_class_lists_placebo(
        lock, synthetic_world.data_root, CALL, "earnings21-original"
    )
    assert len(twin) == len(real) == 2
    for arm_item, twin_item in zip(real, twin):
        assert whitespace_token_count(twin_item.content) == whitespace_token_count(
            arm_item.content
        )


# ---------------------------------------------------------------------------
# The evidence source
# ---------------------------------------------------------------------------


def test_the_source_returns_two_items_each_pinned_to_its_own_conec_file(synthetic_world):
    lock = _install(synthetic_world)
    roster_item, document_item = _conec_class_lists(
        lock, synthetic_world.data_root, CALL, "earnings21-original"
    )
    assert roster_item.derivation.transform_name == "conec-class-lists-roster"
    assert roster_item.derivation.source_relpath.endswith(
        f"earnings21/contexts/participant_names/{CALL}.names.txt"
    )
    assert document_item.derivation.transform_name == "conec-class-lists-document"
    assert document_item.derivation.source_relpath.endswith(f"earnings21/contexts/{CALL}.txt")
    for item in (roster_item, document_item):
        assert item.provenance["lock_key"] == "conec"
        assert item.derivation.carrier_bound is True
        assert item.derivation.sample_id == CALL


def test_the_derivation_chain_reverifies_against_the_registered_transforms(synthetic_world):
    """What ``core.driver.run_experiment`` does before a run is allowed to send
    anything: re-invoke the pinned transform on the source bytes and demand the
    content back."""

    lock = _install(synthetic_world)
    registry = DerivedEvidenceRegistry()
    for source in (_conec_class_lists, _conec_class_lists_placebo):
        for item in source(lock, synthetic_world.data_root, CALL, "earnings21-original"):
            registry.register(
                item.derivation,
                source_content=item.derivation_source_bytes,
                derived_content=item.content.encode("utf-8"),
                params=resolve_declared_transform_params(item.derivation.transform_name, None),
            )


def test_a_carrier_with_no_conec_evidence_layer_fails_closed(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="no ConEC evidence layer registered"):
        _conec_class_lists(lock, synthetic_world.data_root, "4432298", "earnings22-original")


def test_a_missing_roster_fails_closed(synthetic_world):
    lock = _install(synthetic_world)
    (_conec_dir(synthetic_world) / "participant_names" / f"{CALL}.names.txt").unlink()
    with pytest.raises(EvidenceError, match="conec participant names missing"):
        _conec_class_lists(lock, synthetic_world.data_root, CALL, "earnings21-original")


# ---------------------------------------------------------------------------
# Construction / evaluation separation
# ---------------------------------------------------------------------------


def test_a_calls_brief_is_built_from_that_calls_own_context_alone(synthetic_world):
    """The separation E5 requires: an evaluation call's brief must contain its
    own ConEC context and nothing another call's files carry. Asserted by
    giving two calls disjoint vocabularies and reading both briefs."""

    lock = _install(synthetic_world)
    _install(
        synthetic_world,
        sample_id=OTHER_CALL,
        document="\n".join(f"{token} 1" for token in "zylotech holdings nasdaq zylo".split()),
        roster="Ada Lovelace - Chief Executive Officer\n",
    )
    mine = "\n".join(
        item.content
        for item in _conec_class_lists(
            lock, synthetic_world.data_root, CALL, "earnings21-original"
        )
    )
    theirs = "\n".join(
        item.content
        for item in _conec_class_lists(
            lock, synthetic_world.data_root, OTHER_CALL, "earnings21-original"
        )
    )
    for foreign in ("zylotech", "zylo", "Ada Lovelace"):
        assert foreign not in mine
    for foreign in ("culp", "ncbusiness", "Dru Anderson"):
        assert foreign not in theirs


def test_the_renderer_opens_no_reference_path(synthetic_world, monkeypatch):
    """The hard boundary. Every path the evidence source reads is recorded, and
    the assertion is positive (each one is under ``contexts/``) rather than a
    denylist, so a future source file this test has never heard of still fails
    it unless it lives where ConEC's context does."""

    lock = _install(synthetic_world)
    touched: list[str] = []
    real_read_text = pathlib.Path.read_text
    real_open = pathlib.Path.open

    def recording_read_text(self, *args, **kwargs):
        touched.append(str(self))
        return real_read_text(self, *args, **kwargs)

    def recording_open(self, *args, **kwargs):
        touched.append(str(self))
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", recording_read_text)
    monkeypatch.setattr(pathlib.Path, "open", recording_open)
    _conec_class_lists(lock, synthetic_world.data_root, CALL, "earnings21-original")
    _conec_class_lists_placebo(lock, synthetic_world.data_root, CALL, "earnings21-original")

    assert touched, "the recorder saw nothing; the boundary claim would be vacuous"
    contexts = str(_conec_dir(synthetic_world))
    for path in touched:
        assert path.startswith(contexts), path
        assert "nlp_reference" not in path
        assert "wer_tag" not in path
        assert "timestamps" not in path
        assert "bias_lists" not in path
