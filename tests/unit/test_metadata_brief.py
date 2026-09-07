"""``e22-metadata-brief`` and its two form twins: the Earnings-22 pre-meeting
brief, the deranged twin, the TOKEN-matched twin, and every refusal that keeps
them honest.

Every test runs on a SYNTHETIC metadata table this file writes, so the brief's
shape is asserted against text under test control rather than against corpus
bytes. The one thing asserted about the real layout is the boundary: the
evidence source's path is resolved from the carrier descriptor and refuses a
table the composed config did not pin.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core import metadata_brief as mb
from speech_aware_evidence_acquisition.core.base import EVIDENCE_SOURCES, EvidenceError
from speech_aware_evidence_acquisition.core.class_lists import (
    PLACEBO_PAD_FILLER,
    pad_placebo,
)
from speech_aware_evidence_acquisition.core.evidence import (
    brief_call_id,
    e22_metadata_file_relpath,
    resolve_declared_transform_params,
)
from speech_aware_evidence_acquisition.core.evidence_derivation import (
    TRANSFORMS,
    DerivedEvidenceRegistry,
)
from speech_aware_evidence_acquisition.data.lock import load_lock

HEADER = (
    "File ID,Ticker Symbol,Country by Ticker,UN Defined,Major Dialect Family,"
    "Language Family + Area Based,File Length (seconds),Sampling Rate (Hz)"
)
ROWS = (
    "4453225,APNHF,South Africa,Sub-Saharan Africa,Other,English,4307,16000",
    "4474506,COST,United States,Europe and Northern America,North American,English,3975,24000",
    "4479944,HDB,India,Central and Southern Asia,Other,Asian,3892,44100",
)
TABLE = HEADER + "\n" + "\n".join(ROWS) + "\n"
CALLS = ("4453225", "4474506", "4479944")

#: A wider table for the partner-selection tests: 4453226 restates 4453225's
#: country, region and dialect family under a different ticker (the exact
#: near-copy the distinctness rule exists to skip), and two further calls give
#: the selector somewhere else to go.
WIDE_ROWS = ROWS + (
    "4453226,SPPJY,South Africa,Sub-Saharan Africa,Other,English,4634,44100",
    "4470684,IVTJF,UK,Europe and Northern America,British Isles,English,4696,24000",
    "4481952,CAHPF,Australia,Oceania,Oceanic,English,3710,24000",
)
TABLE_WIDE = HEADER + "\n" + "\n".join(WIDE_ROWS) + "\n"
WIDE_CALLS = ("4453225", "4453226", "4470684", "4474506", "4479944", "4481952")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Reading the table
# ---------------------------------------------------------------------------


def test_the_table_is_read_into_verbatim_lines():
    header, rows = mb.metadata_header_and_rows(TABLE)
    assert header == HEADER
    assert set(rows) == set(CALLS)
    assert rows["4474506"] == ROWS[1]


def test_a_missing_brief_column_is_refused():
    narrow = "File ID,File Length (seconds)\n4453225,4307\n"
    with pytest.raises(mb.MetadataBriefError, match="missing column"):
        mb.metadata_header_and_rows(narrow)


def test_a_duplicate_call_is_refused():
    doubled = TABLE + ROWS[0] + "\n"
    with pytest.raises(mb.MetadataBriefError, match="twice"):
        mb.metadata_header_and_rows(doubled)


def test_a_call_the_table_does_not_carry_is_refused():
    with pytest.raises(mb.MetadataBriefError, match="no row for call"):
        mb.call_source_slice(TABLE, "9999999")


def test_the_source_slice_is_a_literal_quotation_of_two_lines():
    slice_text = mb.call_source_slice(TABLE, "4474506")
    assert slice_text == f"{HEADER}\n{ROWS[1]}"
    assert slice_text.splitlines() == [HEADER, ROWS[1]]
    assert mb.call_id_of_slice(slice_text) == "4474506"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_the_brief_renders_one_heading_and_five_labelled_facts():
    rendered = mb.render_brief(mb.call_source_slice(TABLE, "4474506"))
    lines = rendered.splitlines()
    assert len(lines) == 1 + len(mb.BRIEF_FIELDS)
    assert lines[0] == mb.BRIEF_HEADING
    assert lines[1].startswith("Ticker symbol: COST")
    assert lines[2].startswith("Country: United States")
    assert lines[3].startswith("UN region: Europe and Northern America")
    assert lines[4].startswith("Major dialect family: North American")
    assert lines[5].startswith("Language family and area: English")


def test_every_value_carries_its_whisper_normalized_form():
    rendered = mb.render_brief(mb.call_source_slice(TABLE, "4474506"))
    assert "[normalized: cost]" in rendered
    assert "[normalized: united states]" in rendered
    # An already-lowercase value costs no annotation.
    assert "english [normalized" not in rendered


def test_the_brief_names_no_recording_property():
    rendered = mb.render_brief(mb.call_source_slice(TABLE, "4474506"))
    assert "3975" not in rendered
    assert "24000" not in rendered
    assert "File Length" not in rendered


def test_the_brief_names_no_company_and_no_external_source():
    """The owner ruling of 2026-09-07: Earnings-22 collects no external
    information. The table carries no company name and the renderer has no
    field, no key and no code path that could add one."""

    assert all(column != "Company" for column, _ in mb.BRIEF_FIELDS)
    rendered = mb.render_brief(mb.call_source_slice(TABLE, "4474506"))
    assert "Costco" not in rendered
    assert "company" not in rendered.split("--", 1)[1].split("\n", 1)[1].lower()


def test_a_blank_field_is_refused_rather_than_rendered_short():
    blank = HEADER + "\n4453225,,South Africa,Sub-Saharan Africa,Other,English,4307,16000\n"
    with pytest.raises(mb.MetadataBriefError, match="empty"):
        mb.render_brief(mb.call_source_slice(blank, "4453225"))


def test_brief_terms_drop_the_normalization_annotation():
    terms = mb.brief_terms(mb.call_source_slice(TABLE, "4474506"))
    assert terms["Ticker symbol"] == "COST"
    assert terms["Country"] == "United States"
    assert "[normalized" not in "".join(terms.values())


# ---------------------------------------------------------------------------
# The derangement
# ---------------------------------------------------------------------------


def test_the_derangement_is_a_fixed_point_free_bijection():
    mapping = mb.derange_calls(CALLS)
    assert set(mapping) == set(CALLS)
    assert set(mapping.values()) == set(CALLS)
    assert all(key != value for key, value in mapping.items())
    assert mapping == mb.derange_calls(tuple(reversed(CALLS)))


def test_one_call_can_never_be_deranged():
    with pytest.raises(mb.MetadataBriefError, match="at least two calls"):
        mb.derange_calls(("4453225",))


def test_a_derangement_with_a_fixed_point_is_refused():
    with pytest.raises(mb.MetadataBriefError, match="to itself"):
        mb.validate_derangement({"a1": "a1", "b2": "a1"})


def test_a_derangement_that_is_not_a_bijection_is_refused():
    with pytest.raises(mb.MetadataBriefError, match="bijection"):
        mb.validate_derangement({"a1": "c3", "b2": "c3"})


# ---------------------------------------------------------------------------
# Pinned artifacts
# ---------------------------------------------------------------------------


def _pin(relpath: str, digest: str) -> dict[str, str]:
    return {"artifact_relpath": relpath, "artifact_sha256": digest}


def test_the_metadata_pin_must_name_a_datasets_path_and_a_real_digest():
    good = {mb.BRIEF_SOURCE_KEY: _pin("datasets/x/metadata.csv", "0" * 64)}
    assert mb.resolve_brief_source_pin(good) == ("datasets/x/metadata.csv", "0" * 64)
    with pytest.raises(mb.MetadataBriefError, match="not under 'datasets/'"):
        mb.resolve_brief_source_pin({mb.BRIEF_SOURCE_KEY: _pin("configs/x.csv", "0" * 64)})
    with pytest.raises(mb.MetadataBriefError, match="escapes"):
        mb.resolve_brief_source_pin(
            {mb.BRIEF_SOURCE_KEY: _pin("datasets/../etc/passwd", "0" * 64)}
        )
    with pytest.raises(mb.MetadataBriefError, match="sha256"):
        mb.resolve_brief_source_pin({mb.BRIEF_SOURCE_KEY: _pin("datasets/x.csv", "nope")})
    with pytest.raises(mb.MetadataBriefError, match="exactly"):
        mb.resolve_brief_source_pin({mb.BRIEF_SOURCE_KEY: {"artifact_relpath": "datasets/x"}})
    with pytest.raises(mb.MetadataBriefError, match="composed config"):
        mb.resolve_brief_source_pin(None)


def _write_derangement(repo_root, mapping) -> dict[str, object]:
    path = repo_root / "configs" / "knowledge" / "e22-brief-v1" / "derangement-v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {"schema": mb.DERANGEMENT_SCHEMA, "derangement": mapping}, sort_keys=True
    )
    path.write_text(payload, encoding="utf-8", newline="\n")
    return {
        mb.DERANGEMENT_KEY: _pin(
            "configs/knowledge/e22-brief-v1/derangement-v1.json", _sha256(payload)
        )
    }


def test_a_derangement_artifact_edited_after_its_pin_is_refused(tmp_path):
    mb._load_pinned_json.cache_clear()
    values = {mb.BRIEF_SOURCE_KEY: _pin("datasets/x/metadata.csv", "0" * 64)}
    values.update(_write_derangement(tmp_path, mb.derange_calls(CALLS)))
    resolved = mb.resolve_derangement_params(values, repo_root=tmp_path)
    assert resolved["derangement"] == mb.derange_calls(CALLS)

    path = tmp_path / "configs" / "knowledge" / "e22-brief-v1" / "derangement-v1.json"
    path.write_text(
        json.dumps({"schema": mb.DERANGEMENT_SCHEMA, "derangement": {"a1": "b2", "b2": "a1"}}),
        encoding="utf-8",
        newline="\n",
    )
    mb._load_pinned_json.cache_clear()
    with pytest.raises(mb.MetadataBriefError, match="hashes to"):
        mb.resolve_derangement_params(values, repo_root=tmp_path)


def _write_pad_plan(repo_root, entries) -> dict[str, object]:
    path = repo_root / "configs" / "knowledge" / "e22-brief-v1" / "pad-plan-v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"schema": mb.PAD_PLAN_SCHEMA, "entries": entries}, sort_keys=True)
    path.write_text(payload, encoding="utf-8", newline="\n")
    return {
        mb.PAD_PLAN_KEY: _pin(
            "configs/knowledge/e22-brief-v1/pad-plan-v1.json", _sha256(payload)
        )
    }


def test_the_token_matched_twin_replays_the_pinned_pad_plan(tmp_path):
    mb._load_pinned_json.cache_clear()
    partner_slice = mb.call_source_slice(TABLE, "4474506")
    repeats = [0, 3, 1, 0, 2, 0]
    values = {mb.BRIEF_SOURCE_KEY: _pin("datasets/x/metadata.csv", "0" * 64)}
    values.update(_write_derangement(tmp_path, mb.derange_calls(CALLS)))
    values.update(
        _write_pad_plan(
            tmp_path,
            [{"source_sha256": _sha256(partner_slice), "pad_repeats": repeats}],
        )
    )
    params = mb.resolve_token_matched_params(values, repo_root=tmp_path)
    padded = mb.e22_metadata_brief_deranged_tm_content(partner_slice, params)
    plain = mb.render_brief(partner_slice)
    assert len(padded.splitlines()) == len(plain.splitlines())
    for line, base, count in zip(padded.splitlines(), plain.splitlines(), repeats):
        assert line == base + PLACEBO_PAD_FILLER * count


def test_the_ARM_is_padded_too_and_gains_no_fact(tmp_path):
    """The padder here is SYMMETRIC, unlike KU-E1c's: a real-call twin can be
    longer than the brief it twins, so the pair meets in the middle. What the arm
    gains has to be filler and nothing else."""

    mb._load_pinned_json.cache_clear()
    arm_slice = mb.call_source_slice(TABLE, "4453225")
    repeats = [0, 1, 0, 2, 0, 0]
    values = {mb.BRIEF_SOURCE_KEY: _pin("datasets/x/metadata.csv", "0" * 64)}
    values.update(
        _write_pad_plan(
            tmp_path, [{"source_sha256": _sha256(arm_slice), "pad_repeats": repeats}]
        )
    )
    params = mb.resolve_arm_token_matched_params(values, repo_root=tmp_path)
    padded = mb.e22_metadata_brief_tm_content(arm_slice, params)
    plain = mb.render_brief(arm_slice)
    for line, base, count in zip(padded.splitlines(), plain.splitlines(), repeats):
        assert line == base + PLACEBO_PAD_FILLER * count
    stripped = padded.replace(PLACEBO_PAD_FILLER, "")
    assert stripped == plain.replace(PLACEBO_PAD_FILLER, "")


def test_the_symmetric_padder_matches_both_sides_prefix_for_prefix():
    counter = lambda text: len(text.split())  # noqa: E731
    arm = mb.render_brief(mb.call_source_slice(TABLE, "4453225"))
    twin = mb.render_brief(mb.call_source_slice(TABLE, "4479944"))
    arm_repeats, twin_repeats = mb.pair_pad_repeats(arm, twin, token_counter=counter)
    padded_arm = pad_placebo(arm, arm_repeats)
    padded_twin = pad_placebo(twin, twin_repeats)
    assert mb.prefix_counts(padded_arm, counter) == mb.prefix_counts(padded_twin, counter)
    # The shorter side is the one that grows at each line: never both.
    assert all(a == 0 or t == 0 for a, t in zip(arm_repeats, twin_repeats))


def test_the_symmetric_padder_refuses_a_twin_of_a_different_shape():
    counter = lambda text: len(text.split())  # noqa: E731
    arm = mb.render_brief(mb.call_source_slice(TABLE, "4453225"))
    with pytest.raises(mb.MetadataBriefError, match="line count"):
        mb.pair_pad_repeats(arm, "one line only", token_counter=counter)


def test_partner_selection_never_restates_the_arms_facts():
    """The defect this constraint exists for: the first pairing this repository
    built gave call 4453225 a whitespace-identical partner that restated its
    country, its region and its dialect family verbatim."""

    counter = lambda text: len(text.split())  # noqa: E731
    slices = {call: mb.call_source_slice(TABLE_WIDE, call) for call in WIDE_CALLS}
    briefs = {call: mb.render_brief(text) for call, text in slices.items()}
    terms = {call: mb.brief_terms(text) for call, text in slices.items()}
    partners, plans = mb.select_twin_partners(
        briefs_by_call=briefs,
        roster_calls=("4453225",),
        candidate_calls=WIDE_CALLS,
        token_counter=counter,
        terms_by_call=terms,
    )
    # 4453226 is 4453225's twin in every field but the ticker, so it is skipped.
    assert partners["4453225"] != "4453226"
    for field in mb.DISTINCT_TWIN_FIELDS:
        assert terms[partners["4453225"]][field] != terms["4453225"][field]
    assert set(plans) == {"4453225"}
    assert len(plans["4453225"]) == 2


def test_partner_selection_never_draws_from_the_roster():
    counter = lambda text: len(text.split())  # noqa: E731
    slices = {call: mb.call_source_slice(TABLE_WIDE, call) for call in WIDE_CALLS}
    briefs = {call: mb.render_brief(text) for call, text in slices.items()}
    partners, _ = mb.select_twin_partners(
        briefs_by_call=briefs,
        roster_calls=("4453225", "4474506"),
        candidate_calls=WIDE_CALLS,
        token_counter=counter,
    )
    assert set(partners.values()).isdisjoint({"4453225", "4474506"})
    assert len(set(partners.values())) == 2


def test_partner_selection_refuses_when_the_pool_is_the_roster():
    counter = lambda text: len(text.split())  # noqa: E731
    briefs = {call: mb.render_brief(mb.call_source_slice(TABLE, call)) for call in CALLS}
    with pytest.raises(mb.MetadataBriefError, match="outside the roster"):
        mb.select_twin_partners(
            briefs_by_call=briefs,
            roster_calls=CALLS,
            candidate_calls=CALLS,
            token_counter=counter,
        )


def test_a_twin_with_no_plan_entry_is_refused_rather_than_rendered_unpadded(tmp_path):
    mb._load_pinned_json.cache_clear()
    values = {mb.BRIEF_SOURCE_KEY: _pin("datasets/x/metadata.csv", "0" * 64)}
    values.update(_write_derangement(tmp_path, mb.derange_calls(CALLS)))
    values.update(
        _write_pad_plan(tmp_path, [{"source_sha256": "a" * 64, "pad_repeats": [0]}])
    )
    params = mb.resolve_token_matched_params(values, repo_root=tmp_path)
    with pytest.raises(mb.MetadataBriefError, match="no entry for source bytes"):
        mb.e22_metadata_brief_deranged_tm_content(mb.call_source_slice(TABLE, "4474506"), params)


def test_an_unpinned_transform_is_refused():
    with pytest.raises(mb.MetadataBriefError, match="pinned metadata_relpath"):
        mb.e22_metadata_brief_content(mb.call_source_slice(TABLE, "4474506"), {})


# ---------------------------------------------------------------------------
# The evidence sources, end to end on the synthetic world
# ---------------------------------------------------------------------------


def _e22_world(world, tmp_path):
    """The synthetic world's Earnings-22 metadata table replaced by a full
    eight-column one, plus the composed values the sources need."""

    (world.e22 / "metadata.csv").write_text(TABLE, encoding="utf-8", newline="\n")
    lock = load_lock(world.lock_path)
    relpath = e22_metadata_file_relpath(lock, "earnings22-original")
    values = {
        mb.BRIEF_SOURCE_KEY: _pin(relpath, _sha256(TABLE)),
    }
    values.update(_write_derangement(tmp_path, mb.derange_calls(CALLS)))
    return lock, values, relpath


def test_the_arm_renders_this_calls_own_brief(synthetic_world, tmp_path, monkeypatch):
    mb._load_pinned_json.cache_clear()
    monkeypatch.setattr(mb, "REPO_ROOT", tmp_path)
    lock, values, relpath = _e22_world(synthetic_world, tmp_path)
    source = EVIDENCE_SOURCES.resolve("e22-metadata-brief")
    items = source(lock, synthetic_world.data_root, "4474506-103@ts2", "earnings22-original", values)
    assert len(items) == 1
    item = items[0]
    assert "Ticker symbol: COST" in item.content
    assert item.provenance["call_id"] == "4474506"
    assert item.provenance["source_call_id"] == "4474506"
    assert item.provenance["relpath"] == relpath
    assert item.derivation.carrier_bound is False
    assert item.derivation.transform_name == "e22-metadata-brief"
    assert item.derivation.source_sha256 == _sha256(mb.call_source_slice(TABLE, "4474506"))


def test_the_twin_renders_another_calls_brief_and_never_this_ones(
    synthetic_world, tmp_path, monkeypatch
):
    mb._load_pinned_json.cache_clear()
    monkeypatch.setattr(mb, "REPO_ROOT", tmp_path)
    lock, values, _ = _e22_world(synthetic_world, tmp_path)
    partner = mb.derange_calls(CALLS)["4474506"]
    source = EVIDENCE_SOURCES.resolve("e22-metadata-brief-deranged")
    item = source(
        lock, synthetic_world.data_root, "4474506-103@ts2", "earnings22-original", values
    )[0]
    assert item.provenance["call_id"] == "4474506"
    assert item.provenance["source_call_id"] == partner
    assert item.content == mb.render_brief(mb.call_source_slice(TABLE, partner))
    assert "COST" not in item.content
    # Same shape as the arm's: same heading, same labels, same line count.
    arm = EVIDENCE_SOURCES.resolve("e22-metadata-brief")(
        lock, synthetic_world.data_root, "4474506-103@ts2", "earnings22-original", values
    )[0]
    assert len(item.content.splitlines()) == len(arm.content.splitlines())
    assert [line.split(":", 1)[0] for line in item.content.splitlines()] == [
        line.split(":", 1)[0] for line in arm.content.splitlines()
    ]


def test_a_table_edited_after_the_pin_is_refused(synthetic_world, tmp_path, monkeypatch):
    mb._load_pinned_json.cache_clear()
    monkeypatch.setattr(mb, "REPO_ROOT", tmp_path)
    lock, values, _ = _e22_world(synthetic_world, tmp_path)
    (synthetic_world.e22 / "metadata.csv").write_text(
        TABLE.replace("COST", "XXXX"), encoding="utf-8", newline="\n"
    )
    source = EVIDENCE_SOURCES.resolve("e22-metadata-brief")
    with pytest.raises(EvidenceError, match="hashes to"):
        source(lock, synthetic_world.data_root, "4474506-103@ts2", "earnings22-original", values)


def test_a_fragment_pinning_a_different_table_is_refused(
    synthetic_world, tmp_path, monkeypatch
):
    mb._load_pinned_json.cache_clear()
    monkeypatch.setattr(mb, "REPO_ROOT", tmp_path)
    lock, values, _ = _e22_world(synthetic_world, tmp_path)
    values = dict(values)
    values[mb.BRIEF_SOURCE_KEY] = _pin("datasets/elsewhere/metadata.csv", _sha256(TABLE))
    source = EVIDENCE_SOURCES.resolve("e22-metadata-brief")
    with pytest.raises(EvidenceError, match="never rendered from a table"):
        source(lock, synthetic_world.data_root, "4474506-103@ts2", "earnings22-original", values)


def test_a_carrier_with_no_metadata_table_fails_closed(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="declares no metadata table"):
        e22_metadata_file_relpath(lock, "slurp")


def test_the_call_id_is_recovered_from_a_clip_id():
    assert brief_call_id("4474506-103@ts2") == "4474506"
    assert brief_call_id("4474506-103") == "4474506"
    assert brief_call_id("4474506") == "4474506"
    with pytest.raises(EvidenceError):
        brief_call_id("")


def test_the_derivation_registry_re_derives_every_source(
    synthetic_world, tmp_path, monkeypatch
):
    """The rail the driver runs: re-invoke the pinned transform on the same
    source bytes with the params THIS config declares, and get the same content
    back. Proves the applied params and the verified params cannot disagree."""

    mb._load_pinned_json.cache_clear()
    monkeypatch.setattr(mb, "REPO_ROOT", tmp_path)
    lock, values, _ = _e22_world(synthetic_world, tmp_path)
    registry = DerivedEvidenceRegistry()
    for name in ("e22-metadata-brief", "e22-metadata-brief-deranged"):
        item = EVIDENCE_SOURCES.resolve(name)(
            lock, synthetic_world.data_root, "4474506-103@ts2", "earnings22-original", values
        )[0]
        params = resolve_declared_transform_params(item.derivation.transform_name, values)
        registry.register(
            item.derivation,
            source_content=item.derivation_source_bytes,
            derived_content=item.content.encode("utf-8"),
            params=params,
        )
    assert TRANSFORMS.resolve("e22-metadata-brief", "v1") is not None


def test_the_renderer_opens_no_reference_path(synthetic_world, tmp_path, monkeypatch):
    """The boundary assertion: the only data-root file the evidence source
    opens is the carrier's own metadata table. No reference, transcript,
    alignment, segment table or media byte."""

    mb._load_pinned_json.cache_clear()
    monkeypatch.setattr(mb, "REPO_ROOT", tmp_path)
    lock, values, relpath = _e22_world(synthetic_world, tmp_path)
    opened: list[str] = []
    real_read_bytes = type(tmp_path).read_bytes

    def _spy(self, *args, **kwargs):
        opened.append(str(self))
        return real_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(type(tmp_path), "read_bytes", _spy)
    EVIDENCE_SOURCES.resolve("e22-metadata-brief")(
        lock, synthetic_world.data_root, "4474506-103@ts2", "earnings22-original", values
    )
    under_data_root = [
        path for path in opened if str(synthetic_world.data_root) in path
    ]
    assert under_data_root == [str(synthetic_world.data_root / relpath)]
