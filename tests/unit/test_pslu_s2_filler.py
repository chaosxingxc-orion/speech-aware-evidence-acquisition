"""``rails.probes.pslu_s2_filler``: F1 filler-roster generator + fail-closed
binding check (Stage-2 follow-up probe SAEA-PROBE-pslu-s2-183). Engineering-
only, zero live model contact.
"""

from __future__ import annotations

import itertools
import json
import string
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import PsluRosters, render_roster_entries
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_filler import (
    F1_ROSTER_SIZE,
    FillerBindingError,
    PsluS2FillerError,
    _filler_binding_report,
    _gold_slot_values,
    _ontology_values,
    check_f1_filler_binding,
    f1_filler_supply_packet,
    generate_f1_filler_roster,
    load_filler_lexicon,
)

_ROSTERS = PsluRosters(
    scenario_rosters={
        "iot": (("house_place", "kitchen"), ("device_type", "light")),
        "email": (("email_folder", "inbox"),),
    },
    global_types=("house_place", "device_type", "email_folder", "time"),
    full_roster=(("house_place", "kitchen"), ("time", "six")),
    derangement={"iot": "email", "email": "iot"},
)


def _synthetic_lexicon(n: int) -> tuple[str, ...]:
    """``n`` distinct 3-letter lowercase-alphabetic tokens ("aaa", "aab",
    ...) -- deterministic, disjoint from any real English word this study's
    own gold/ontology data could plausibly carry, good enough for a
    synthetic fixture."""

    letters = string.ascii_lowercase
    combos = itertools.islice(("".join(p) for p in itertools.product(letters, repeat=3)), n)
    return tuple(combos)


def _write_lexicon(path: Path, words, **overrides) -> None:
    document = {
        "lexicon_version": "pslu-s2-filler-lexicon-v1",
        "probe": "P-SLU-S2",
        "slurp_derived": False,
        "words": list(words),
    }
    document.update(overrides)
    path.write_text(json.dumps(document), encoding="utf-8")


# ---------------------------------------------------------------------------
# load_filler_lexicon
# ---------------------------------------------------------------------------


def test_load_filler_lexicon_happy_path(tmp_path):
    path = tmp_path / "lex.json"
    words = _synthetic_lexicon(200)
    _write_lexicon(path, words)
    assert load_filler_lexicon(path) == words


def test_load_filler_lexicon_rejects_wrong_probe(tmp_path):
    path = tmp_path / "lex.json"
    _write_lexicon(path, _synthetic_lexicon(200), probe="P-A2T")
    with pytest.raises(PsluS2FillerError, match="probe must be"):
        load_filler_lexicon(path)


def test_load_filler_lexicon_rejects_wrong_version(tmp_path):
    path = tmp_path / "lex.json"
    _write_lexicon(path, _synthetic_lexicon(200), lexicon_version="bogus")
    with pytest.raises(PsluS2FillerError, match="lexicon_version"):
        load_filler_lexicon(path)


def test_load_filler_lexicon_rejects_slurp_derived_true(tmp_path):
    path = tmp_path / "lex.json"
    _write_lexicon(path, _synthetic_lexicon(200), slurp_derived=True)
    with pytest.raises(PsluS2FillerError, match="slurp_derived"):
        load_filler_lexicon(path)


def test_load_filler_lexicon_rejects_too_few_words(tmp_path):
    path = tmp_path / "lex.json"
    _write_lexicon(path, _synthetic_lexicon(50))
    with pytest.raises(PsluS2FillerError, match="at least"):
        load_filler_lexicon(path)


def test_load_filler_lexicon_rejects_duplicate_word(tmp_path):
    path = tmp_path / "lex.json"
    words = list(_synthetic_lexicon(200))
    words[5] = words[0]
    _write_lexicon(path, words)
    with pytest.raises(PsluS2FillerError, match="duplicate word"):
        load_filler_lexicon(path)


def test_load_filler_lexicon_rejects_non_lowercase_word(tmp_path):
    path = tmp_path / "lex.json"
    words = list(_synthetic_lexicon(200))
    words[0] = "Bad_Word1"
    _write_lexicon(path, words)
    with pytest.raises(PsluS2FillerError, match="not a lowercase-alphabetic token"):
        load_filler_lexicon(path)


def test_load_filler_lexicon_against_the_real_shipped_file():
    """The mission's own registered artifact -- proves this loader actually
    parses it, not merely a hand-shrunk test fixture."""

    path = (
        Path(__file__).resolve().parents[2]
        / "configs" / "probes" / "g0-binding" / "pslu-s2-filler-lexicon.json"
    )
    words = load_filler_lexicon(path)
    assert len(words) == 300
    assert len(set(words)) == 300


# ---------------------------------------------------------------------------
# generate_f1_filler_roster
# ---------------------------------------------------------------------------


def test_generate_f1_filler_roster_is_deterministic():
    lexicon = _synthetic_lexicon(200)
    assert generate_f1_filler_roster(lexicon) == generate_f1_filler_roster(lexicon)


def test_generate_f1_filler_roster_default_size_is_100():
    entries = generate_f1_filler_roster(_synthetic_lexicon(200))
    assert len(entries) == F1_ROSTER_SIZE == 100


def test_generate_f1_filler_roster_type_and_value_halves_are_disjoint():
    entries = generate_f1_filler_roster(_synthetic_lexicon(200))
    types = {t for t, _ in entries}
    values = {v for _, v in entries}
    assert len(types) == 100
    assert len(values) == 100
    assert types.isdisjoint(values)
    assert all(t != v for t, v in entries)


def test_generate_f1_filler_roster_raises_when_lexicon_too_small():
    with pytest.raises(PsluS2FillerError, match="need at least"):
        generate_f1_filler_roster(_synthetic_lexicon(50))


def test_generate_f1_filler_roster_different_seed_changes_the_draw():
    lexicon = _synthetic_lexicon(200)
    a = generate_f1_filler_roster(lexicon, seed=1)
    b = generate_f1_filler_roster(lexicon, seed=2)
    assert a != b


# ---------------------------------------------------------------------------
# f1_filler_supply_packet -- byte-compatible with A3's own rendering.
# ---------------------------------------------------------------------------


def test_f1_filler_supply_packet_is_byte_compatible_with_a3_rendering():
    entries = (("aaa", "bbb"), ("ccc", "ddd"))
    packet = f1_filler_supply_packet(entries)
    assert packet.prompt_block == render_roster_entries(entries)
    assert packet.assembly_template_id == "pslu-F1-roster-v1"
    assert packet.dose.n_items == 2
    assert [item.item_id for item in packet.items] == ["F1-000", "F1-001"]
    assert [item.text for item in packet.items] == ["aaa=bbb", "ccc=ddd"]


# ---------------------------------------------------------------------------
# _filler_binding_report -- pure, no I/O.
# ---------------------------------------------------------------------------


def test_filler_binding_report_clean_when_no_overlap():
    report = _filler_binding_report(
        (("aaa", "bbb"),), ontology_types=("house_place",), ontology_values=("kitchen",), gold_values=("kitchen",)
    )
    assert report.clean
    assert report.overlap_with_ontology_types == ()
    assert report.overlap_with_ontology_values == ()
    assert report.overlap_with_gold_values == ()


def test_filler_binding_report_detects_type_half_overlap_with_ontology_types():
    report = _filler_binding_report(
        (("house_place", "bbb"),), ontology_types=("house_place",), ontology_values=(), gold_values=()
    )
    assert not report.clean
    assert report.overlap_with_ontology_types == ("house_place",)


def test_filler_binding_report_detects_value_half_overlap_with_ontology_values():
    report = _filler_binding_report(
        (("aaa", "kitchen"),), ontology_types=(), ontology_values=("kitchen",), gold_values=()
    )
    assert not report.clean
    assert report.overlap_with_ontology_values == ("kitchen",)


def test_filler_binding_report_detects_overlap_with_gold_values():
    report = _filler_binding_report((("aaa", "kitchen"),), ontology_types=(), ontology_values=(), gold_values=("kitchen",))
    assert not report.clean
    assert report.overlap_with_gold_values == ("kitchen",)


def test_filler_binding_report_checks_the_full_token_set_not_just_role_matched_halves():
    """Note 3 of the module docstring: the TYPE half is ALSO checked against
    gold/ontology VALUES (and vice versa) -- a strictly stronger reading
    than "type vs types only"."""

    report = _filler_binding_report((("kitchen", "bbb"),), ontology_types=(), ontology_values=("kitchen",), gold_values=())
    assert not report.clean
    assert report.overlap_with_ontology_values == ("kitchen",)


def test_filler_binding_report_normalizes_before_comparing():
    report = _filler_binding_report((("AAA", "Kitchen!"),), ontology_types=(), ontology_values=(), gold_values=("kitchen",))
    assert not report.clean
    assert report.overlap_with_gold_values == ("kitchen",)


# ---------------------------------------------------------------------------
# _ontology_values / _gold_slot_values / check_f1_filler_binding.
# ---------------------------------------------------------------------------


def test_ontology_values_unions_scenario_rosters_and_full_roster():
    assert set(_ontology_values(_ROSTERS)) == {"kitchen", "light", "inbox", "six"}


def test_gold_slot_values_reads_the_devel_split_gold_fillers(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    adapter = SlurpAdapter(lock, slurp_world.data_root)
    sample_ids = tuple(s.sample_id for s in adapter.load_split("devel"))
    values = _gold_slot_values(lock, slurp_world.data_root, sample_ids)
    assert "kitchen" in values  # sample 101's own gold house_place filler (module docstring)


def test_gold_slot_values_raises_on_a_missing_sample_id(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    with pytest.raises(FillerBindingError, match="missing"):
        _gold_slot_values(lock, slurp_world.data_root, ("bogus-sample-id",))


def test_check_f1_filler_binding_passes_when_clean(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    adapter = SlurpAdapter(lock, slurp_world.data_root)
    sample_ids = tuple(s.sample_id for s in adapter.load_split("devel"))
    entries = (("aaa", "bbb"), ("ccc", "ddd"))
    report = check_f1_filler_binding(entries, rosters=_ROSTERS, lock=lock, root=slurp_world.data_root, sample_ids=sample_ids)
    assert report.clean


def test_check_f1_filler_binding_refuses_on_gold_value_overlap(slurp_world):
    """Fixture where overlap EXISTS -- proves the binding check refuses
    (mission instruction)."""

    lock = load_lock(slurp_world.lock_path)
    adapter = SlurpAdapter(lock, slurp_world.data_root)
    sample_ids = tuple(s.sample_id for s in adapter.load_split("devel"))
    entries = (("aaa", "kitchen"),)  # "kitchen" is sample 101's own gold filler
    with pytest.raises(FillerBindingError, match="gold_values"):
        check_f1_filler_binding(entries, rosters=_ROSTERS, lock=lock, root=slurp_world.data_root, sample_ids=sample_ids)


def test_check_f1_filler_binding_refuses_on_ontology_type_overlap(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    adapter = SlurpAdapter(lock, slurp_world.data_root)
    sample_ids = tuple(s.sample_id for s in adapter.load_split("devel"))
    entries = (("house_place", "zzz"),)
    with pytest.raises(FillerBindingError, match="ontology_types"):
        check_f1_filler_binding(entries, rosters=_ROSTERS, lock=lock, root=slurp_world.data_root, sample_ids=sample_ids)


def test_check_f1_filler_binding_refuses_on_ontology_value_overlap(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    adapter = SlurpAdapter(lock, slurp_world.data_root)
    sample_ids = tuple(s.sample_id for s in adapter.load_split("devel"))
    entries = (("zzz", "inbox"),)  # "inbox" is the frozen _ROSTERS' own "email" scenario value
    with pytest.raises(FillerBindingError, match="ontology_values"):
        check_f1_filler_binding(entries, rosters=_ROSTERS, lock=lock, root=slurp_world.data_root, sample_ids=sample_ids)
