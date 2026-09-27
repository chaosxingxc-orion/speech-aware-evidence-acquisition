"""``conec-class-lists`` and its two form twins: the E5 pre-meeting brief, the
whitespace twin, the TOKEN-matched twin, and the construction/evaluation
separation.

Every test here runs on a SYNTHETIC ConEC world (``synthetic_world``), so the
brief's shape is asserted against text this file writes rather than against
bytes on the real data root. The one thing that is asserted about the real
layout is the boundary: :func:`test_the_renderer_opens_no_reference_path`
records every path the evidence source touches and refuses anything outside
``contexts/``.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core import class_lists
from speech_aware_evidence_acquisition.core.base import EVIDENCE_SOURCES, EvidenceError
from speech_aware_evidence_acquisition.core.class_lists import (
    CLASS_LIST_TOKEN_MATCHED_TRANSFORMS,
    CLASS_LIST_TRANSFORMS,
    DEFAULT_MAX_ENTRIES_PER_CLASS,
    PLACEBO_PAD_FILLER,
    PLACEBO_PAD_PLAN_SCHEMA,
    PLACEHOLDER_WORDS,
    ClassListError,
    annotate_normalized,
    context_tokens,
    pad_placebo,
    placebo_of,
    placebo_pad_repeats,
    render_document_brief,
    render_roster_brief,
    resolve_placebo_pad_params,
    roster_entries,
    token_matched_placebo_of,
    whitespace_token_count,
)
from speech_aware_evidence_acquisition.core.evidence import (
    _conec_class_lists,
    _conec_class_lists_placebo,
    _conec_class_lists_placebo_token_matched,
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


# ---------------------------------------------------------------------------
# The TOKEN-matched form twin (owner ruling 2026-09-06)
# ---------------------------------------------------------------------------
#
# The counter below is a FAKE with the real tokenizer's one relevant property:
# a long word costs more than a short one, which is exactly why the whitespace
# twin measured 161 tokens light on the flight tokenizer. Every test in this
# section therefore exercises the mechanism, never a llama-server.


def fake_token_counter(text: str) -> int:
    """One token per whitespace word, two for a word over seven characters, one
    per newline. Every entry in ``PLACEHOLDER_WORDS`` and the pad filler itself
    cost exactly one; a proper noun or a bracketed normalized form costs two, so
    a twin of placeholder nouns comes out short exactly the way the real one
    does, and can never come out long."""

    return sum(2 if len(word) > 7 else 1 for word in text.split()) + text.count("\n")


def blind_counter(text: str) -> int:
    """A counter the filler cannot move: it prices only words longer than the
    filler's own, so a gap opens but no number of fillers ever closes it."""

    return sum(2 if len(word) > 4 else 0 for word in text.split()) + text.count("\n")


def _prefix_counts(text: str) -> list[int]:
    lines = text.splitlines()
    return [fake_token_counter("\n".join(lines[: index + 1])) for index in range(len(lines))]


def test_the_two_token_matched_transforms_and_the_source_are_registered():
    assert "conec-class-lists-placebo-token-matched" in EVIDENCE_SOURCES.names()
    for name in CLASS_LIST_TOKEN_MATCHED_TRANSFORMS:
        assert TRANSFORMS.resolve(name, "v1").version == "v1"
    assert not set(CLASS_LIST_TOKEN_MATCHED_TRANSFORMS) & set(CLASS_LIST_TRANSFORMS)


def test_the_pad_filler_is_the_twins_own_neutral_noun():
    assert PLACEBO_PAD_FILLER == " " + PLACEHOLDER_WORDS[0]
    assert fake_token_counter(PLACEBO_PAD_FILLER) == 1


def test_the_whitespace_twin_is_short_on_a_counter_that_prices_words():
    """The finding this whole section exists to repair, reproduced in one
    assertion: equal whitespace tokens, fewer real ones."""

    brief = render_roster_brief(ROSTER, 0)
    twin = placebo_of(brief)
    assert whitespace_token_count(twin) == whitespace_token_count(brief)
    assert fake_token_counter(twin) < fake_token_counter(brief)


def test_every_padded_line_measures_its_brief_line_in_context():
    brief = render_roster_brief(ROSTER, 0)
    padded, repeats = token_matched_placebo_of(brief, token_counter=fake_token_counter)
    assert len(repeats) == len(brief.splitlines())
    # Per line, in context -- and therefore the whole block at the last index.
    assert _prefix_counts(padded) == _prefix_counts(brief)
    assert fake_token_counter(padded) == fake_token_counter(brief)
    # The provenance sentence is copied verbatim, so it needs no pad at all.
    assert repeats[0] == 0
    assert any(count > 0 for count in repeats[1:])


def test_the_document_half_matches_too():
    brief = render_document_brief(DOCUMENT, 0)
    padded, _ = token_matched_placebo_of(brief, token_counter=fake_token_counter)
    assert _prefix_counts(padded) == _prefix_counts(brief)


def test_the_cap_is_honoured_on_both_halves_of_the_pair():
    for brief in (render_roster_brief(ROSTER, 2), render_document_brief(DOCUMENT, 2)):
        padded, _ = token_matched_placebo_of(brief, token_counter=fake_token_counter)
        assert _prefix_counts(padded) == _prefix_counts(brief)


def test_the_pad_is_deterministic_and_reads_no_content():
    brief = render_roster_brief(ROSTER, 0)
    first, first_repeats = token_matched_placebo_of(brief, token_counter=fake_token_counter)
    second, second_repeats = token_matched_placebo_of(brief, token_counter=fake_token_counter)
    assert (first, first_repeats) == (second, second_repeats)

    # A function of the LINE INDEX and the counts alone: replayed onto a
    # different twin of the same line count, the same plan appends the same
    # suffixes, character for character.
    other = placebo_of(render_document_brief(DOCUMENT, 0))
    plan = [1, 4, 0, 2][: len(other.splitlines())]
    replayed = pad_placebo(other, plan)
    for line, original, count in zip(replayed.splitlines(), other.splitlines(), plan):
        assert line == original + PLACEBO_PAD_FILLER * count


def test_a_twin_line_longer_than_its_brief_line_is_refused():
    """An unpadded line is refused rather than truncated: a control that had to
    be cut down is neither matched nor a rendering of ``placebo_of``."""

    brief = "head\nlabel: a"
    twin = "head\nlabel: encyclopaedia"
    with pytest.raises(ClassListError, match="can never be padded down"):
        placebo_pad_repeats(brief, twin, token_counter=fake_token_counter)


def test_a_filler_that_moves_no_token_is_refused():
    brief = "head\nlabel: alpha beta gamma"
    twin = placebo_of(brief)
    with pytest.raises(ClassListError, match="cannot close a token gap"):
        placebo_pad_repeats(brief, twin, token_counter=blind_counter)


def test_a_twin_with_a_different_line_count_is_refused():
    with pytest.raises(ClassListError, match="line count"):
        placebo_pad_repeats("a\nb", "a", token_counter=fake_token_counter)


def test_a_pad_plan_that_does_not_cover_every_line_is_refused():
    with pytest.raises(ClassListError, match="repeat counts for a 2-line twin"):
        pad_placebo("a\nb", [1])
    with pytest.raises(ClassListError, match="must be an integer"):
        pad_placebo("a\nb", [1, "2"])
    with pytest.raises(ClassListError, match="outside 0"):
        pad_placebo("a\nb", [1, -1])


def test_text_that_does_not_round_trip_through_splitlines_is_refused():
    with pytest.raises(ClassListError, match="round-trip"):
        pad_placebo("a\nb\n", [0, 0])


# ---------------------------------------------------------------------------
# The pinned pad-plan artifact
# ---------------------------------------------------------------------------


def _write_plan(root: pathlib.Path, halves, cap=0):
    relpath = "configs/knowledge/e21-brief-placebo-v2/pad-plan-v1.json"
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schema": PLACEBO_PAD_PLAN_SCHEMA,
        "caps": {str(cap): {"halves": list(halves)}},
    }
    blob = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.write_bytes(blob)
    return relpath, hashlib.sha256(blob).hexdigest()


def _half(text: str, repeats):
    return {
        "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "pad_repeats": list(repeats),
    }


def test_declared_params_carry_the_pads_themselves(tmp_path):
    relpath, digest = _write_plan(tmp_path, [_half(ROSTER, [0, 3, 1, 0])])
    values = {
        "brief_max_entries_per_class": 0,
        "evidence_pad_plan": {"artifact_relpath": relpath, "artifact_sha256": digest},
    }
    params = resolve_placebo_pad_params(values, repo_root=tmp_path)
    assert params["max_entries_per_class"] == 0
    assert params["pad_artifact_sha256"] == digest
    key = hashlib.sha256(ROSTER.encode("utf-8")).hexdigest()
    assert params["line_pad_repeats"] == {key: [0, 3, 1, 0]}


def test_an_unpinned_or_edited_pad_plan_is_refused(tmp_path):
    relpath, digest = _write_plan(tmp_path, [_half(ROSTER, [0, 1])])
    with pytest.raises(ClassListError, match="never be rendered from an unpinned"):
        resolve_placebo_pad_params({"brief_max_entries_per_class": 0}, repo_root=tmp_path)
    edited = "0" * 64
    with pytest.raises(ClassListError, match="not the configured"):
        resolve_placebo_pad_params(
            {
                "brief_max_entries_per_class": 0,
                "evidence_pad_plan": {
                    "artifact_relpath": relpath,
                    "artifact_sha256": edited,
                },
            },
            repo_root=tmp_path,
        )
    with pytest.raises(ClassListError, match="not under configs/"):
        resolve_placebo_pad_params(
            {
                "brief_max_entries_per_class": 0,
                "evidence_pad_plan": {
                    "artifact_relpath": "docs/pad-plan.json",
                    "artifact_sha256": digest,
                },
            },
            repo_root=tmp_path,
        )


def test_a_cap_the_plan_never_measured_is_refused(tmp_path):
    relpath, digest = _write_plan(tmp_path, [_half(ROSTER, [0, 1])], cap=0)
    with pytest.raises(ClassListError, match="carries no plan for"):
        resolve_placebo_pad_params(
            {
                "brief_max_entries_per_class": 12,
                "evidence_pad_plan": {
                    "artifact_relpath": relpath,
                    "artifact_sha256": digest,
                },
            },
            repo_root=tmp_path,
        )


def test_the_token_matched_source_replays_the_plan_and_chains(
    synthetic_world, tmp_path, monkeypatch
):
    """End to end on the synthetic world: the source renders the padded twin,
    every line measures its brief line, and the derivation registry re-derives
    both halves from the same ConEC bytes and the same declared params."""

    lock = _install(synthetic_world)
    arm = _conec_class_lists(lock, synthetic_world.data_root, CALL, "earnings21-original")
    roster_repeats = placebo_pad_repeats(
        render_roster_brief(ROSTER, 0),
        placebo_of(render_roster_brief(ROSTER, 0)),
        token_counter=fake_token_counter,
    )
    document_repeats = placebo_pad_repeats(
        render_document_brief(DOCUMENT, 0),
        placebo_of(render_document_brief(DOCUMENT, 0)),
        token_counter=fake_token_counter,
    )
    relpath, digest = _write_plan(
        tmp_path,
        [_half(ROSTER, roster_repeats), _half(DOCUMENT, document_repeats)],
    )
    monkeypatch.setattr(class_lists, "REPO_ROOT", tmp_path)
    values = {
        "brief_max_entries_per_class": 0,
        "evidence_pad_plan": {"artifact_relpath": relpath, "artifact_sha256": digest},
    }
    twin = _conec_class_lists_placebo_token_matched(
        lock, synthetic_world.data_root, CALL, "earnings21-original", values
    )

    assert [item.provenance["brief_part"] for item in twin] == ["roster", "document"]
    for arm_item, twin_item in zip(arm, twin):
        assert _prefix_counts(twin_item.content) == _prefix_counts(arm_item.content)
        assert fake_token_counter(twin_item.content) == fake_token_counter(arm_item.content)
        assert "Dru Anderson" not in twin_item.content
        assert "culp" not in twin_item.content

    registry = DerivedEvidenceRegistry()
    for item in twin:
        params = resolve_declared_transform_params(item.derivation.transform_name, values)
        registry.register(
            item.derivation,
            source_content=item.derivation_source_bytes,
            derived_content=item.content.encode("utf-8"),
            params=params,
        )
        assert registry.lookup(CALL, item.derivation.transform_name) is not None


def test_the_token_matched_source_refuses_a_call_the_plan_never_measured(
    synthetic_world, tmp_path, monkeypatch
):
    lock = _install(synthetic_world)
    relpath, digest = _write_plan(
        tmp_path, [{"source_sha256": "1" * 64, "pad_repeats": [0]}]
    )
    monkeypatch.setattr(class_lists, "REPO_ROOT", tmp_path)
    with pytest.raises(EvidenceError, match="pad plan has no entry for source bytes"):
        _conec_class_lists_placebo_token_matched(
            lock,
            synthetic_world.data_root,
            CALL,
            "earnings21-original",
            {
                "brief_max_entries_per_class": 0,
                "evidence_pad_plan": {
                    "artifact_relpath": relpath,
                    "artifact_sha256": digest,
                },
            },
        )


def test_shared_live_evidence_binding_matches_the_registered_class_list_source(synthetic_world):
    from speech_aware_evidence_acquisition.core.driver.run import materialize_evidence_binding

    lock = _install(synthetic_world)
    sample = SimpleNamespace(sample_id=CALL, carrier_lock_key="earnings21-original")
    binding = materialize_evidence_binding(
        lock, synthetic_world.data_root, [sample], {"evidence_source": "conec-class-lists"},
        evidence_budget_bytes=0,
    )
    expected = _conec_class_lists(
        lock, synthetic_world.data_root, CALL, "earnings21-original",
        {"evidence_source": "conec-class-lists"},
    )
    actual = binding.evidence_by_sample[CALL]
    assert [item.evidence_id for item in actual] == [item.evidence_id for item in expected]
    assert [item.content for item in actual] == [item.content for item in expected]
    assert binding.evidence_relpaths[CALL] == tuple(
        item.derivation.source_relpath for item in expected
    )


def test_shared_live_evidence_binding_refuses_the_wrong_conec_carrier(synthetic_world):
    from speech_aware_evidence_acquisition.core.driver.run import materialize_evidence_binding

    lock = _install(synthetic_world)
    sample = SimpleNamespace(sample_id=CALL, carrier_lock_key="earnings22-original")
    with pytest.raises(Exception, match="ConEC|context|carrier"):
        materialize_evidence_binding(
            lock, synthetic_world.data_root, [sample], {"evidence_source": "conec-class-lists"},
            evidence_budget_bytes=0,
        )


def test_shared_binding_changes_when_the_pinned_conec_source_bytes_drift(synthetic_world):
    from speech_aware_evidence_acquisition.core.driver.run import materialize_evidence_binding

    lock = _install(synthetic_world)
    sample = SimpleNamespace(sample_id=CALL, carrier_lock_key="earnings21-original")
    values = {"evidence_source": "conec-class-lists"}
    before = materialize_evidence_binding(
        lock, synthetic_world.data_root, [sample], values, evidence_budget_bytes=0
    )
    (_conec_dir(synthetic_world) / f"{CALL}.txt").write_text(
        DOCUMENT + "\nrevision 1", encoding="utf-8"
    )
    after = materialize_evidence_binding(
        load_lock(synthetic_world.lock_path), synthetic_world.data_root, [sample],
        values, evidence_budget_bytes=0
    )
    assert before.evidence_by_sample[CALL][1].content != after.evidence_by_sample[CALL][1].content
    assert before.evidence_contents[CALL] != after.evidence_contents[CALL]


def test_window_fit_inputs_refuse_evidence_source_drift_after_materialization(synthetic_world):
    from speech_aware_evidence_acquisition.core.driver.run import materialize_evidence_binding
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.core.preparation import PreparationError
    from speech_aware_evidence_acquisition.core.preparation_windows import WindowRequestBatch

    lock = _install(synthetic_world)
    sample = SimpleNamespace(sample_id=CALL, carrier_lock_key="earnings21-original")
    values = {"evidence_source": "conec-class-lists"}
    binding = materialize_evidence_binding(
        lock, synthetic_world.data_root, [sample], values, evidence_budget_bytes=0
    )
    runtime = SimpleNamespace(
        _lock=lock,
        _data_root=synthetic_world.data_root,
        _samples=[sample],
        # request_fit_inputs keys the prepared-text implementation hash on the composed arm (FlightRuntime._arm);
        # this synthetic window fit is not the prepared-text arm.
        _arm=lambda: "fixed-legal-context",
        preparation_context=lambda: {
            "values": values,
            "split_identity_hash": "a" * 64,
            "runtime_receipt": {"schema": "synthetic"},
            "required_identity": {"schema": "synthetic"},
        },
    )
    batch = WindowRequestBatch(
        ({"sample_id": CALL, "media_relpath": "derived/obs-slices/fit-run/windows/window.wav", "speech": []},),
        (f"{CALL}#w0001",),
        ({"sample_id": CALL, "media_relpath": "derived/obs-slices/fit-run/windows/window.wav"},),
        evidence_binding=binding,
    )
    admitted = FlightRuntime.request_fit_inputs(runtime, batch.payloads, window_batch=batch)
    assert admitted["sources"]["window_evidence"]
    context_path = _conec_dir(synthetic_world) / f"{CALL}.txt"
    context_path.write_text(DOCUMENT + "\nrevision 1", encoding="utf-8")
    with pytest.raises(
        PreparationError, match="window evidence sources changed after payload materialization"
    ):
        FlightRuntime.request_fit_inputs(runtime, batch.payloads, window_batch=batch)


def test_real_window_fit_materialization_matches_registered_live_factory_with_conec(
    synthetic_world, monkeypatch
):
    from array import array

    from speech_aware_evidence_acquisition.core.base import SampleContext
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.core.model.slices import SliceRegistry
    from speech_aware_evidence_acquisition.data.loader import SampleRef
    from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter
    from speech_aware_evidence_acquisition.reproduction import obs_loop

    class WindowAdapter(TaskAdapter):
        def preprocess_plan(self):
            return {"kind": "raw-speech-windows"}

        def instruction(self, sample):
            return "Transcribe the speech verbatim."

        def load_split(self, split_id):
            return ()

        def build_task_contract(self, sample, obs):
            return "synthetic contract"

        def gold(self, sample):
            return None

        def score_response(self, gold, response):
            return {}

    lock = _install(synthetic_world)
    parent_relpath = f"earnings21/audio/{CALL}.wav"
    parent = synthetic_world.data_root / parent_relpath
    parent.parent.mkdir(parents=True, exist_ok=True)
    parent.write_bytes(b"synthetic speech carrier")
    pcm = array("h", [0]) * (16_000 * 90)
    monkeypatch.setattr(obs_loop, "decode_parent_pcm", lambda path, rate: pcm)
    sample = SampleRef(
        carrier_lock_key="earnings21-original",
        sample_id=CALL,
        media_relpath=parent_relpath,
        audio_seconds=90.0,
        sample_rate_hz=16_000,
    )
    values = {
        "arm": "fixed-legal-context",
        "policy": "obs-agent-loop-ojw",
        "evidence_source": "conec-class-lists",
        "obs_buffer_seconds": 60,
        "obs_min_advance_seconds": 20,
        "obs_max_advance_seconds": 55,
        "obs_silence_snap_seconds": 2.0,
        "obs_fallback_advance_seconds": 50,
        "obs_boundary_mode": "fixed",
        "obs_vad": "energy",
        "obs_vad_trim_min_seconds": 0,
        "obs_preprocess": [],
        "obs_condition_tail_chars": 0,
        "obs_batch_slices": 2,
        "decoding_params": {"temperature": 0, "max_tokens": 64},
    }
    runtime = object.__new__(FlightRuntime)
    runtime._adapter = WindowAdapter()
    runtime._lock = lock
    runtime._data_root = synthetic_world.data_root
    runtime._samples = [sample]
    runtime._run_id = "SAEA-E-000-fit-parity"
    runtime._attempt_id = "attempt-synthetic"
    runtime._explicit_run_dir = synthetic_world.data_root / "runs" / "fit"
    runtime._repo_root = synthetic_world.data_root / "repo"
    runtime._plan = None
    runtime._prepare = lambda: (values, "earnings21-original", "discovery", "identity")
    # The real _prepare sets _composed; window_feature_packet_binding reads the composed values from it.
    runtime._composed = SimpleNamespace(values=values)
    batch = runtime.materialize_window_batch()
    assert batch.evidence_binding is not None
    evidence = batch.evidence_binding.evidence_by_sample[CALL]
    assert [item.evidence_id for item in evidence] == [
        "conec-class-lists-roster/4320211",
        "conec-class-lists-document/4320211",
    ]

    registry = SliceRegistry(
        data_root=synthetic_world.data_root,
        run_id="SAEA-E-000-fit-parity",
        parent_facts={CALL: (parent_relpath, 90.0)},
    )
    cfg = obs_loop.ObsLoopConfig.from_values(values, runtime._repo_root)
    windows, _records = obs_loop.materialize_fixed_windows(
        cfg,
        registry,
        synthetic_world.data_root,
        sample,
        16_000,
        pcm,
        90.0,
        hashlib.sha256(parent.read_bytes()).hexdigest(),
    )
    live_context = SampleContext(
        sample=sample,
        evidence=evidence,
        adapter=runtime._adapter,
        sink=object(),
        arm=values["arm"],
        task_instruction=runtime._adapter.instruction(sample),
        decoding_params=values["decoding_params"],
        request_id_base=f"{runtime._run_id}-{CALL}",
        extras={"config_values": values},
    )
    request_id, factory = obs_loop.window_request_factory(
        live_context, windows[0], sample=sample, rate=16_000, evidence=evidence
    )
    assert batch.payloads[0] == factory(request_id)
