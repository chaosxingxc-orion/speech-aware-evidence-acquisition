"""KB-BUILD's EMPTY-CONTRACT annotated-exemplar view and its store builder
(``train-exemplars-with-empty-v1``, 2026-09-24).

Same discipline as ``test_knowledge_build_annotated_exemplars_view.py``: a
small synthetic ``KbRow`` corpus, model-free and filesystem-free except for
``tmp_path``, zero contacts of every kind.

The three properties that matter:

* the empty form the view renders is the SOLVER'S OWN, read out of the
  committed output contract rather than restated here;
* the change is confined to entity-free values -- every facet (so the whole
  RETRIEVAL KEY side), every id, prior score and provenance ref, and every
  entity-bearing value's content, is byte-identical to the parent view;
* the pool SELECTION does not move: the builder's exclusion tuple is the
  parent pool builder's, character for character.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge_build import (
    SOLVER_EMPTY_ENTITY_LIST_FORM,
    VIEW_ANNOTATED_EXEMPLARS,
    VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT,
    VIEW_EXEMPLAR,
    KbRow,
    KnowledgeBuildSpec,
    build_knowledge_snapshot,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    load_knowledge_store_binding,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SOLVER_CONTRACT = _REPO_ROOT / "configs" / "probes" / "slurp_native_role_solver_v2.txt"


def _load(relpath: str, name: str):
    script = _REPO_ROOT / relpath
    spec = importlib.util.spec_from_file_location(name, script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load(
    "scripts/build_slurp_train_exemplars_with_empty_store.py",
    "train_exemplars_with_empty_under_test",
)
pool_builder = _load(
    "scripts/build_slurp_exemplar_pool_assets.py", "exemplar_pool_assets_under_test"
)


def _row(
    utterance_id: str,
    *,
    scenario: str,
    action: str,
    words: str,
    entity_fillers: dict[str, tuple[str, ...]] | None = None,
) -> KbRow:
    sample_id = f"slurp:train:{utterance_id}:audio-{utterance_id}"
    fillers = entity_fillers or {}
    return KbRow(
        utterance_id=utterance_id,
        content=words,
        scenario=scenario,
        action=action,
        intent=f"{scenario}_{action}",
        entity_types=tuple(sorted(fillers)),
        entity_fillers=fillers,
        sample_ids=(sample_id,),
        speaker_by_sample_id={sample_id: "FO-001"},
        media_relpath_by_sample_id={sample_id: f"datasets/slurp/audio-{utterance_id}.flac"},
    )


def _rows() -> tuple[KbRow, ...]:
    return (
        _row("1", scenario="alarm", action="set", words="wake me at nine am on friday",
             entity_fillers={"date": ("friday",), "time": ("nine am",)}),
        _row("2", scenario="alarm", action="set", words="wake me at six",
             entity_fillers={"time": ("six",)}),
        _row("3", scenario="iot", action="hue_lightoff", words="lights off"),
        _row("4", scenario="cooking", action="recipe", words="find a recipe",
             entity_fillers={"food_type": ("pasta", "salad")}),
        _row("5", scenario="general", action="greet", words="good morning"),
    )


#: The two entity-free rows of the synthetic corpus.
EMPTY_VALUE_IDS = frozenset({"value:3", "value:5"})


def _build(view: str):
    return build_knowledge_snapshot(
        KnowledgeBuildSpec(
            carrier_lock_key="slurp", dimensions=("content",), view=view
        ).validate(),
        rows=_rows(),
        forbidden_sample_ids=frozenset(),
    )


# ---------------------------------------------------------------------------
# The empty form is the Solver's own
# ---------------------------------------------------------------------------


def test_the_empty_form_is_the_solver_output_contracts_own() -> None:
    contract = _SOLVER_CONTRACT.read_text(encoding="utf-8")
    # The contract's answer shape names the entity list ...
    assert '"entities":[' in contract
    # ... and says in words what an empty answer is.
    assert "return an empty entities array" in contract
    # The constant is that key with the empty array, exactly as the model
    # would have to emit it -- and is NOT a word the contract never uses.
    assert SOLVER_EMPTY_ENTITY_LIST_FORM == '"entities":[]'
    assert SOLVER_EMPTY_ENTITY_LIST_FORM[:-1] in contract
    assert "none" not in contract


def test_an_entity_free_utterance_renders_the_contract_empty_form() -> None:
    values = {value.value_id: value for value in _build(
        VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT
    ).values}
    assert values["value:3"].content == 'lights off | iot_hue_lightoff | "entities":[]'
    assert values["value:5"].content == 'good morning | general_greet | "entities":[]'
    for value_id in EMPTY_VALUE_IDS:
        assert not values[value_id].content.endswith("| none")


def test_the_parent_view_still_renders_the_bare_word_none() -> None:
    """The default is frozen: the locked SLURP v2.0 plan pins the parent
    store's hash, so the parent rendering must not move by a byte."""

    values = {value.value_id: value for value in _build(VIEW_ANNOTATED_EXEMPLARS).values}
    assert values["value:3"].content == "lights off | iot_hue_lightoff | none"
    assert values["value:5"].content == "good morning | general_greet | none"


# ---------------------------------------------------------------------------
# The change is confined
# ---------------------------------------------------------------------------


def test_every_facet_is_byte_identical_to_the_parent_view() -> None:
    """The RETRIEVAL KEY side does not move, which is why the sealed KU-S3
    facet vectors keep binding by id and no encoder is ever contacted."""

    parent = {facet.facet_id: facet for facet in _build(VIEW_ANNOTATED_EXEMPLARS).facets}
    derived = _build(VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT).facets
    assert {facet.facet_id for facet in derived} == set(parent)
    for facet in derived:
        assert facet == parent[facet.facet_id]
        assert "annotated-exemplar retrieval key" in facet.representation


def test_only_the_entity_free_values_change() -> None:
    parent = {value.value_id: value for value in _build(VIEW_ANNOTATED_EXEMPLARS).values}
    derived = _build(VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT).values
    changed = set()
    for value in derived:
        other = parent[value.value_id]
        assert value.prior_score == other.prior_score
        assert value.task_target == other.task_target
        assert value.associated_facet_ids == other.associated_facet_ids
        assert value.source_sample_ids == other.source_sample_ids
        assert value.provenance_refs == other.provenance_refs
        if value.content != other.content:
            changed.add(value.value_id)
            # Only the trailing field moved.
            assert value.content.rsplit(" | ", 1)[0] == other.content.rsplit(" | ", 1)[0]
    assert changed == EMPTY_VALUE_IDS


def test_the_selection_and_split_identity_do_not_move() -> None:
    parent = _build(VIEW_ANNOTATED_EXEMPLARS)
    derived = _build(VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT)
    assert derived.source_sample_ids == parent.source_sample_ids
    assert derived.source_split_identity_hash == parent.source_split_identity_hash
    # A different rendering is a different snapshot, and says so.
    assert derived.snapshot_id != parent.snapshot_id
    assert derived.content_hash() != parent.content_hash()


def test_the_empty_contract_view_is_a_legal_content_recall_view() -> None:
    KnowledgeBuildSpec(
        carrier_lock_key="slurp",
        dimensions=("content",),
        view=VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT,
    ).validate()
    with pytest.raises(RailsError, match="requires the 'content' dimension"):
        KnowledgeBuildSpec(
            carrier_lock_key="slurp",
            dimensions=("label", "prior"),
            view=VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT,
        ).validate()


def test_the_other_views_are_untouched() -> None:
    exemplar = _build(VIEW_EXEMPLAR)
    values = {value.value_id: value for value in exemplar.values}
    assert values["value:3"].content.startswith('Exemplar sentence: "lights off"')
    assert SOLVER_EMPTY_ENTITY_LIST_FORM not in values["value:3"].content


# ---------------------------------------------------------------------------
# The store builder
# ---------------------------------------------------------------------------


def test_the_exclusion_is_the_parent_pool_builders_own() -> None:
    """Construction-roster hygiene is inherited, not restated: the same three
    roster receipts, in the same order."""

    assert builder.EXCLUDE_ROSTER_RELPATHS == pool_builder.EXCLUDE_ROSTER_RELPATHS
    assert builder.EXPECTED_UTTERANCE_COUNT == pool_builder.EXPECTED_UTTERANCE_COUNT
    assert (
        builder.EXPECTED_SOURCE_SPLIT_IDENTITY_HASH
        == pool_builder.EXPECTED_SOURCE_SPLIT_IDENTITY_HASH
    )
    assert builder.FACET_VECTORS_SHA256 == pool_builder.FACET_VECTORS_SHA256
    assert builder.SEED == pool_builder.SEED


def test_the_store_identity_stays_train_exemplars() -> None:
    """A re-pin, not a second store: ``load_knowledge_store_binding`` requires
    ``release.store_id`` to equal the ``knowledge_stores`` key, and every
    exemplar evidence id is prefixed ``train-exemplars::value:``."""

    assert builder.STORE_ID == "train-exemplars"
    assert builder.STORE_ROLE == "train-exemplars"
    assert builder.RELEASE_NAME == "train-exemplars-with-empty-v1"


def test_entity_free_value_ids_come_from_the_rows_not_from_parsing() -> None:
    assert builder.entity_free_value_ids(_rows()) == EMPTY_VALUE_IDS


def _parent_document(snapshot) -> dict:
    return json.loads(json.dumps(snapshot.frozen_json()))


def test_the_parent_relation_check_accepts_the_real_pair() -> None:
    parent = _parent_document(_build(VIEW_ANNOTATED_EXEMPLARS))
    derived = _build(VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT)
    relation = builder.assert_parent_relation(derived, parent, empty_ids=EMPTY_VALUE_IDS)
    assert relation["facets_changed"] == 0
    assert relation["values_total"] == 5
    assert relation["values_byte_identical"] == 3
    assert relation["values_changed"] == 2


@pytest.mark.parametrize(
    "mutation",
    ["facet_representation", "entity_bearing_content", "value_id_set", "prior_score"],
)
def test_the_parent_relation_check_refuses_any_other_drift(mutation) -> None:
    parent = _parent_document(_build(VIEW_ANNOTATED_EXEMPLARS))
    derived = _build(VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT)
    if mutation == "facet_representation":
        parent["facets"][0]["representation"] += " drifted"
    elif mutation == "entity_bearing_content":
        for value in parent["values"]:
            if value["value_id"] not in EMPTY_VALUE_IDS:
                value["content"] += " drifted"
                break
    elif mutation == "value_id_set":
        parent["values"] = parent["values"][:-1]
        parent["facets"] = parent["facets"][:-1]
    else:
        for value in parent["values"]:
            if value["value_id"] not in EMPTY_VALUE_IDS:
                value["prior_score"] = 0.123456
                break
    with pytest.raises(SystemExit):
        builder.assert_parent_relation(derived, parent, empty_ids=EMPTY_VALUE_IDS)


def test_the_composition_report_carries_labels_and_counts_only() -> None:
    report = builder.composition(_rows())
    assert report["entity_bearing"] == 3
    assert report["entity_free"] == 2
    assert report["total"] == 5
    assert set(report["by_scenario"]) == {"alarm", "cooking", "general", "iot"}
    assert report["by_scenario"]["iot"] == {
        "entity_bearing": 0,
        "entity_free": 1,
        "total": 1,
        "entity_free_share": 1.0,
    }
    # Labels, counts and shares only -- no utterance text, no filler.
    serialized = json.dumps(report)
    for row in _rows():
        assert row.content not in serialized
        for fillers in row.entity_fillers.values():
            for filler in fillers:
                assert filler not in serialized


# ---------------------------------------------------------------------------
# The runtime loader accepts the released shape
# ---------------------------------------------------------------------------


def _publish(root: Path, reldir: str, snapshot) -> dict[str, object]:
    (root / reldir).mkdir(parents=True, exist_ok=True)
    source_relpath = f"{reldir}/source.jsonl"
    source_raw = b'{"corpus": "synthetic"}\n'
    (root / source_relpath).write_bytes(source_raw)
    snapshot_relpath = f"{reldir}/snapshot.json"
    (root / snapshot_relpath).write_text(
        json.dumps(snapshot.frozen_json()), encoding="utf-8"
    )
    release = {
        "schema": builder.RELEASE_SCHEMA,
        "store_id": builder.STORE_ID,
        "store_role": builder.STORE_ROLE,
        "snapshot_sha256": snapshot.content_hash(),
        "source_split_identity_hash": snapshot.source_split_identity_hash,
        "builder_policy_id": snapshot.builder_policy_id,
        "source": {
            "relpath": source_relpath,
            "sha256": hashlib.sha256(source_raw).hexdigest(),
        },
    }
    release_relpath = f"{reldir}/release.json"
    release_raw = json.dumps(release, sort_keys=True).encode("utf-8")
    (root / release_relpath).write_bytes(release_raw)
    return {
        "store_role": builder.STORE_ROLE,
        "snapshot": {"relpath": snapshot_relpath, "sha256": snapshot.content_hash()},
        "release": {
            "relpath": release_relpath,
            "sha256": hashlib.sha256(release_raw).hexdigest(),
        },
    }


def test_the_released_shape_loads_under_the_unchanged_store_key(tmp_path) -> None:
    """A variant cell re-pins ``knowledge_stores['train-exemplars']`` and
    nothing else: the key, the role and every evidence prefix are unchanged."""

    snapshot = _build(VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT)
    config = {
        "knowledge_stores": {
            builder.STORE_ID: _publish(tmp_path, "knowledge/with-empty", snapshot)
        }
    }
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    store = binding.stores[builder.STORE_ID]
    assert store.store_role == builder.STORE_ROLE
    contents = {value.value_id: value.content for value in store.snapshot.values}
    assert contents["value:3"].endswith(SOLVER_EMPTY_ENTITY_LIST_FORM)
    composite = binding.composite_snapshot.validate()
    assert set(composite.source_sample_ids) == set(snapshot.source_sample_ids)
