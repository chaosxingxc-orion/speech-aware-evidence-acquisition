"""``data.references.reference_entity_mentions``: wer_tags column + sidecar
grouping (owner decision D-3, entity-class WER scorer admission)."""

import json

import pytest

from speech_aware_evidence_acquisition.data.carriers import entity_scoped_carrier_lock_keys
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.references import (
    UNTYPED_ENTITY_TYPE,
    EntityMention,
    ReferenceError,
    reference_entity_mentions,
)


def _write_nlp(path, rows):
    lines = ["token|speaker|tags|wer_tags"]
    for token, wer_tags in rows:
        lines.append(f"{token}|0||{wer_tags}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_sidecar(path, mapping):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping), encoding="utf-8")


def test_earnings21_original_is_the_only_entity_scoped_carrier():
    assert entity_scoped_carrier_lock_keys() == frozenset({"earnings21-original"})


def test_groups_tokens_by_entity_id_in_reference_order(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    _write_nlp(
        nlp,
        [
            ("The", "[]"),
            ("Acme", "['0']"),
            ("Corporation", "['0']"),
            ("reported", "[]"),
            ("March", "['1']"),
            ("2020", "['1']"),
        ],
    )
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    _write_sidecar(sidecar, {"0": {"entity_type": "ORG"}, "1": {"entity_type": "DATE"}})
    lock = load_lock(synthetic_world.lock_path)
    mentions = reference_entity_mentions(
        lock, synthetic_world.data_root, "earnings21-original", "4000001"
    )
    assert mentions == [
        EntityMention(
            entity_id="0", entity_type="ORG", token_indices=(1, 2), tokens=("Acme", "Corporation")
        ),
        EntityMention(
            entity_id="1", entity_type="DATE", token_indices=(4, 5), tokens=("March", "2020")
        ),
    ]


def test_non_contiguous_entity_span_groups_correctly(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    _write_nlp(
        nlp,
        [
            ("Q3", "['0']"),
            ("results", "[]"),
            ("for", "[]"),
            ("Q3", "['0']"),
        ],
    )
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    _write_sidecar(sidecar, {"0": {"entity_type": "CARDINAL"}})
    lock = load_lock(synthetic_world.lock_path)
    mentions = reference_entity_mentions(
        lock, synthetic_world.data_root, "earnings21-original", "4000001"
    )
    assert len(mentions) == 1
    assert mentions[0].token_indices == (0, 3)
    assert mentions[0].tokens == ("Q3", "Q3")


def test_token_with_multiple_entity_ids_contributes_to_each(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    _write_nlp(nlp, [("2020", "['0', '1']")])
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    _write_sidecar(sidecar, {"0": {"entity_type": "YEAR"}, "1": {"entity_type": "CARDINAL"}})
    lock = load_lock(synthetic_world.lock_path)
    mentions = reference_entity_mentions(
        lock, synthetic_world.data_root, "earnings21-original", "4000001"
    )
    assert {mention.entity_id for mention in mentions} == {"0", "1"}
    assert all(mention.token_indices == (0,) for mention in mentions)


def test_entity_id_absent_from_the_sidecar_is_labelled_untyped(synthetic_world):
    """An ID the sidecar never LISTS is an absent annotation, not a corrupt one.

    The Earnings-21 release ships exactly one (call 4320211's `.nlp` tags a token
    with entity ID 1057 while its sidecar carries only 0-904). Refusing outright
    used to take the whole manifest's scorer list down with it; the mention is
    now labelled UNTYPED_ENTITY_TYPE, so it is still never given a real class but
    it is counted and it shows up in `by_entity_type` -- see that constant's own
    docstring."""

    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    _write_nlp(nlp, [("Acme", "['0']"), ("Corp", "['1']")])
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    _write_sidecar(sidecar, {"0": {"entity_type": "ORG"}})
    lock = load_lock(synthetic_world.lock_path)
    mentions = reference_entity_mentions(
        lock, synthetic_world.data_root, "earnings21-original", "4000001"
    )
    assert mentions == [
        EntityMention(
            entity_id="0", entity_type="ORG", token_indices=(0,), tokens=("Acme",)
        ),
        EntityMention(
            entity_id="1",
            entity_type=UNTYPED_ENTITY_TYPE,
            token_indices=(1,),
            tokens=("Corp",),
        ),
    ]


def test_untyped_sentinel_cannot_collide_with_a_real_entity_type():
    """Every label either gold layer uses is an uppercase spaCy-style tag, so a
    leading-double-underscore sentinel is outside that space by construction."""

    assert UNTYPED_ENTITY_TYPE.startswith("__")
    assert not UNTYPED_ENTITY_TYPE.strip("_").islower()


def test_listed_entity_id_with_an_unusable_entity_type_still_fails_closed(synthetic_world):
    """A LISTED ID whose entry is corrupt is a different case and stays fatal."""

    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    _write_nlp(nlp, [("Acme", "['0']")])
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    _write_sidecar(sidecar, {"0": {"entity_type": 7}})
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ReferenceError, match="no usable entity_type"):
        reference_entity_mentions(lock, synthetic_world.data_root, "earnings21-original", "4000001")


def test_listed_entity_id_whose_entry_is_not_a_mapping_still_fails_closed(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    _write_nlp(nlp, [("Acme", "['0']")])
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    _write_sidecar(sidecar, {"0": "ORG"})
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ReferenceError, match="no usable entity_type"):
        reference_entity_mentions(lock, synthetic_world.data_root, "earnings21-original", "4000001")


def test_malformed_wer_tags_cell_fails_closed(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.parent.mkdir(parents=True, exist_ok=True)
    nlp.write_text("token|speaker|tags|wer_tags\nAcme|0||not-a-literal\n", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ReferenceError, match="literal"):
        reference_entity_mentions(lock, synthetic_world.data_root, "earnings21-original", "4000001")


def test_wrong_shaped_wer_tags_cell_fails_closed(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.parent.mkdir(parents=True, exist_ok=True)
    # A dict, not a list of strings -- parses fine via ast.literal_eval but is
    # the wrong shape for a wer_tags cell.
    nlp.write_text("token|speaker|tags|wer_tags\nAcme|0||{'0': 1}\n", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ReferenceError, match="list of strings"):
        reference_entity_mentions(lock, synthetic_world.data_root, "earnings21-original", "4000001")


def test_missing_wer_tags_column_fails_closed(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.parent.mkdir(parents=True, exist_ok=True)
    nlp.write_text("token|speaker\nAcme|0\n", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ReferenceError, match="wer_tags"):
        reference_entity_mentions(lock, synthetic_world.data_root, "earnings21-original", "4000001")


def test_unsupported_carrier_fails_closed(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ReferenceError, match="entity layer"):
        reference_entity_mentions(lock, synthetic_world.data_root, "earnings22-original", "5000000")


def test_missing_sidecar_fails_closed(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    _write_nlp(nlp, [("Acme", "['0']")])
    # SyntheticWorld's own fixture already wrote a "{}" sidecar for 4000001;
    # remove it to exercise the missing-sidecar path specifically.
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    sidecar.unlink()
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ReferenceError, match="cannot read entity sidecar"):
        reference_entity_mentions(lock, synthetic_world.data_root, "earnings21-original", "4000001")


def test_malformed_sidecar_json_fails_closed(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    _write_nlp(nlp, [("Acme", "['0']")])
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    sidecar.write_text("{not valid json", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ReferenceError, match="not valid JSON"):
        reference_entity_mentions(lock, synthetic_world.data_root, "earnings21-original", "4000001")
