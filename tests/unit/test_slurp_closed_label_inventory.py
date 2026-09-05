"""The SLURP closed label inventory: the scenario/action PAIRING the flat
ontology rosters throw away, its compact rendering, its registered instruction
fill, and the config seam a ``core.flight.FlightRuntime`` cell uses to put it
on the wire.

Why this exists. The sealed 2026-08-25 DEV-1000 M0 arm's system message DID
enumerate 18 scenarios, 46 actions and 55 entity types -- but as two
independent lists, so a reader sees 18 x 46 = 828 implied intents where only
60 (scenario, action) pairs occur in ``train``. A model-free structural read
of that arm's own 1,000 sealed predictions found 32.20 percent of them naming
a pair that never occurs in train, against 8.60 percent naming an unlisted
scenario and 6.90 percent an unlisted action. Closing that gap is what
``actions_by_scenario`` and :func:`render_slurp_label_inventory` are for.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.core.base import INSTRUCTION_FILLS, CoreError
from speech_aware_evidence_acquisition.core.instructions import (
    resolve_active_task_instruction,
    resolve_task_instruction,
)
from speech_aware_evidence_acquisition.data.lock import REPO_ROOT, load_lock
from speech_aware_evidence_acquisition.data.loader import LoaderError
from speech_aware_evidence_acquisition.data.slurp import (
    SlurpOntology,
    load_slurp_ontology,
    render_slurp_closed_label_inventory,
    render_slurp_label_inventory,
    render_slurp_ontology,
)

TEMPLATE_RELPATH = "probes/slurp_direct_closed_list.txt"
FILL_NAME = "slurp-label-inventory"
BASELINE_FRAGMENT = REPO_ROOT / "configs" / "baseline" / "slurp-direct-closed-list.json"


# ---------------------------------------------------------------------------
# The pairing itself
# ---------------------------------------------------------------------------


def test_ontology_mines_the_scenario_action_pairing_from_train_only(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    ontology = load_slurp_ontology(lock, slurp_world.data_root)
    # train.jsonl holds exactly iot/hue_lightdim and weather/query.
    assert ontology.actions_by_scenario == {
        "iot": ("hue_lightdim",),
        "weather": ("query",),
    }
    assert ontology.intents == ("iot_hue_lightdim", "weather_query")
    # devel's iot/hue_lighton and email/query, and test's alarm/set, are absent.
    assert "hue_lighton" not in ontology.actions_by_scenario["iot"]
    assert "email" not in ontology.actions_by_scenario
    assert "alarm" not in ontology.actions_by_scenario


def test_pairing_follows_the_include_synthetic_flag(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    default = load_slurp_ontology(lock, slurp_world.data_root)
    widened = load_slurp_ontology(lock, slurp_world.data_root, include_synthetic=True)
    assert "alarm" not in default.actions_by_scenario
    assert widened.actions_by_scenario["alarm"] == ("set",)
    assert "alarm_set" in widened.intents


def test_pairing_agrees_with_the_flat_rosters_it_travels_beside(slurp_world):
    """Every paired name is also a listed name, and vice versa -- the two
    renderings can never disagree about which labels exist."""

    lock = load_lock(slurp_world.lock_path)
    ontology = load_slurp_ontology(lock, slurp_world.data_root)
    assert set(ontology.actions_by_scenario) == set(ontology.scenarios)
    paired_actions = {
        action for actions in ontology.actions_by_scenario.values() for action in actions
    }
    assert paired_actions == set(ontology.actions)


def test_intent_spelling_matches_slurp_record_intent(slurp_world):
    """``SlurpRecord.intent`` is the COMPUTED ``f"{scenario}_{action}"``
    string (``data.slurp`` module docstring); an inventory that spelled its
    intents any other way could not be compared with a gold label."""

    lock = load_lock(slurp_world.lock_path)
    ontology = load_slurp_ontology(lock, slurp_world.data_root)
    for intent in ontology.intents:
        scenario, _, action = intent.partition("_")
        assert action in ontology.actions_by_scenario[scenario]


# ---------------------------------------------------------------------------
# The compact rendering
# ---------------------------------------------------------------------------


def test_render_label_inventory_is_one_line_per_scenario_plus_one_type_line(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    ontology = load_slurp_ontology(lock, slurp_world.data_root)
    rendered = render_slurp_label_inventory(ontology)
    lines = rendered.split("\n")
    # header, pair header, one line per scenario, entity-type line
    assert len(lines) == 2 + len(ontology.actions_by_scenario) + 1
    assert lines[2] == "iot: hue_lightdim"
    assert lines[3] == "weather: query"
    assert lines[-1].startswith("Entity types (1 in total")
    assert lines[-1].endswith("house_place")
    assert "2 intents in total" in lines[1]


def test_render_label_inventory_carries_no_example_fillers(slurp_world):
    """The block is a LABEL inventory, not a few-shot block: the ontology's
    example filler values must not appear in it."""

    lock = load_lock(slurp_world.lock_path)
    ontology = load_slurp_ontology(lock, slurp_world.data_root)
    rendered = render_slurp_label_inventory(ontology)
    for fillers in ontology.entity_types.values():
        for filler in fillers:
            assert filler not in rendered


def test_render_label_inventory_is_deterministic_and_sorted(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    ontology = load_slurp_ontology(lock, slurp_world.data_root)
    assert render_slurp_label_inventory(ontology) == render_slurp_label_inventory(ontology)
    shuffled = SlurpOntology(
        scenarios=ontology.scenarios,
        actions=ontology.actions,
        entity_types=ontology.entity_types,
        actions_by_scenario={
            scenario: tuple(reversed(actions))
            for scenario, actions in reversed(list(ontology.actions_by_scenario.items()))
        },
    )
    assert render_slurp_label_inventory(shuffled) == render_slurp_label_inventory(ontology)


def test_render_label_inventory_refuses_an_ontology_without_the_pairing():
    bare = SlurpOntology(scenarios=("iot",), actions=("query",), entity_types={})
    with pytest.raises(LoaderError, match="actions_by_scenario"):
        render_slurp_label_inventory(bare)


def test_closed_inventory_is_the_unchanged_contract_plus_the_block(slurp_world):
    """The fill's whole contract: the first half is byte-identical to
    :func:`render_slurp_ontology`, so an arm using it extends the sealed M0
    prompt by a pure suffix rather than replacing it."""

    lock = load_lock(slurp_world.lock_path)
    ontology = load_slurp_ontology(lock, slurp_world.data_root)
    contract = render_slurp_ontology(ontology)
    block = render_slurp_label_inventory(ontology)
    rendered = render_slurp_closed_label_inventory(lock, slurp_world.data_root)
    assert rendered == f"{contract}\n\n{block}"
    assert rendered.startswith(contract)
    # the unchanged half is still the JSON document every earlier reader parsed
    assert json.loads(rendered[: len(contract)])["scenarios"] == list(ontology.scenarios)


# ---------------------------------------------------------------------------
# Registration and the config seam
# ---------------------------------------------------------------------------


def test_fill_is_registered_under_its_name():
    assert FILL_NAME in INSTRUCTION_FILLS.names()
    assert INSTRUCTION_FILLS.resolve(FILL_NAME) is render_slurp_closed_label_inventory


def test_template_renders_the_sealed_instruction_shape(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    values = {
        "task_instruction_template": TEMPLATE_RELPATH,
        "task_instruction_fill": FILL_NAME,
    }
    rendered = resolve_task_instruction(values, REPO_ROOT, lock, slurp_world.data_root)
    # The template's fixed half is rails.adapters.slurp._INSTRUCTION verbatim,
    # followed by the same "Task contract:" header rails.runner appends.
    from speech_aware_evidence_acquisition.rails.adapters.slurp import _INSTRUCTION

    assert rendered.startswith(_INSTRUCTION + "\n\nTask contract:\n")
    assert "{tool_schemas}" not in rendered
    assert "Closed label inventory." in rendered


def test_active_resolver_returns_none_without_the_opt_in(slurp_world):
    """A fragment carrying a template pair but no ``..._active`` flag keeps
    the adapter's own instruction -- the property that stops this seam from
    silently rewriting the four sealed Audio2Tool calibration cells."""

    lock = load_lock(slurp_world.lock_path)
    values = {
        "task_instruction_template": TEMPLATE_RELPATH,
        "task_instruction_fill": FILL_NAME,
    }
    assert resolve_active_task_instruction(values, REPO_ROOT, lock, slurp_world.data_root) is None


def test_active_resolver_returns_the_template_when_opted_in(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    values = {
        "task_instruction_template": TEMPLATE_RELPATH,
        "task_instruction_fill": FILL_NAME,
        "task_instruction_template_active": True,
    }
    resolved = resolve_active_task_instruction(values, REPO_ROOT, lock, slurp_world.data_root)
    assert resolved is not None and "Closed label inventory." in resolved


def test_active_resolver_prefers_a_literal_and_refuses_both(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    assert (
        resolve_active_task_instruction(
            {"task_instruction": "literal"}, REPO_ROOT, lock, slurp_world.data_root
        )
        == "literal"
    )
    with pytest.raises(CoreError, match="both a literal"):
        resolve_active_task_instruction(
            {
                "task_instruction": "literal",
                "task_instruction_template": TEMPLATE_RELPATH,
                "task_instruction_fill": FILL_NAME,
                "task_instruction_template_active": True,
            },
            REPO_ROOT,
            lock,
            slurp_world.data_root,
        )


def test_active_resolver_refuses_an_active_flag_without_a_template(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    with pytest.raises(CoreError, match="no task_instruction_template"):
        resolve_active_task_instruction(
            {"task_instruction_template_active": True},
            REPO_ROOT,
            lock,
            slurp_world.data_root,
        )


# ---------------------------------------------------------------------------
# The committed fragment and template
# ---------------------------------------------------------------------------


def test_committed_template_is_pinned_in_the_probe_manifest():
    import hashlib

    manifest = json.loads(
        (REPO_ROOT / "configs" / "probes" / "manifest.json").read_text(encoding="utf-8")
    )
    template_path = REPO_ROOT / "configs" / "probes" / "slurp_direct_closed_list.txt"
    measured = hashlib.sha256(template_path.read_bytes()).hexdigest()
    assert manifest["templates"]["slurp_direct_closed_list.txt"]["sha256"] == measured
    entry = manifest["probes"]["SLURP-DEV1000-CLOSED-LIST-DIRECT"]
    assert entry["arms"]["direct"] == ["slurp_direct_closed_list.txt"]
    assert entry["profile"] == "baseline-reproduction"
    assert manifest["samples"]["SLURP-DEV1000-CLOSED-LIST-DIRECT"]["receipt"] == "DEV-1000.json"


def test_committed_baseline_fragment_declares_the_active_template_pair():
    fragment = json.loads(BASELINE_FRAGMENT.read_text(encoding="utf-8"))
    assert fragment["task_instruction_template"] == TEMPLATE_RELPATH
    assert fragment["task_instruction_fill"] == FILL_NAME
    assert fragment["task_instruction_template_active"] is True
    assert "task_instruction" not in fragment
    # The arm and the audio path must be the sealed M0 arm's, not a new one.
    assert fragment["arm"] == "speech-feature-query"
    assert fragment["policy"] == "fixed"
    assert fragment["evidence_source"] == "none"
    assert fragment["scorers"] == ["slurp-slu-official", "slurp-slu", "cost"]
    assert fragment["speech_packet_promotion_receipt"].endswith("DEV-1000-promotion.json")


@pytest.mark.parametrize(
    "relpath",
    [
        "configs/experiment/slurp-dev1000-closed-list-direct-v1.json",
        "configs/experiment/slurp-dev1000-closed-list-direct-smoke-v1.json",
    ],
)
def test_committed_experiment_fragments_declare_a_complete_execution_plan(relpath):
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        REQUIRED_EXECUTION_PLAN_FIELDS,
    )

    doc = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
    plan = doc["execution_plan"]
    assert set(REQUIRED_EXECUTION_PLAN_FIELDS) <= set(plan)
    assert plan["execution_profile"] == "baseline-reproduction"
    assert plan["split_role"] == "dev"
    assert isinstance(doc["split_id"], str) and doc["split_id"]
    cells = doc["cells"]
    assert len(cells) == 1
    assert cells[0]["baseline_fragment"] == "slurp-direct-closed-list"
    assert cells[0]["arm"] == "speech-feature-query"


def test_smoke_fragment_names_its_four_rows_and_the_flight_names_none():
    smoke = json.loads(
        (
            REPO_ROOT
            / "configs"
            / "experiment"
            / "slurp-dev1000-closed-list-direct-smoke-v1.json"
        ).read_text(encoding="utf-8")
    )
    flight = json.loads(
        (
            REPO_ROOT / "configs" / "experiment" / "slurp-dev1000-closed-list-direct-v1.json"
        ).read_text(encoding="utf-8")
    )
    ids = smoke["populations"][0]["ids"]
    assert len(ids) == 4 and len(set(ids)) == 4
    assert all(sample_id.startswith("slurp:devel:") for sample_id in ids)
    view = json.loads(
        (
            REPO_ROOT / "configs" / "dataset" / "slurp-speech-native-dev1000.json"
        ).read_text(encoding="utf-8")
    )
    known = {item["sample_id"] for item in view["items"]}
    assert set(ids) <= known
    assert "populations" not in flight


def _real_corpus():
    """(lock, root) for the materialized corpus, or a skip."""

    from speech_aware_evidence_acquisition.data.lock import data_root, umbrella_lock_path

    try:
        root = data_root()
        lock = load_lock(umbrella_lock_path())
    except Exception as error:  # noqa: BLE001 -- an unmaterialized asset is a skip
        pytest.skip(f"SLURP corpus unavailable: {error}")
    metadata = root / "datasets" / "slurp" / "metadata" / "train.jsonl"
    if not metadata.is_file():
        pytest.skip("SLURP governed train.jsonl is not materialized")
    return lock, root


def test_real_corpus_pairing_is_the_published_60_of_828():
    """The measured counts the whole cell rests on: 18 scenarios x 46 actions
    implies 828 combinations, 60 occur, and 55 entity types exist."""

    lock, root = _real_corpus()
    ontology = load_slurp_ontology(lock, root)
    assert len(ontology.scenarios) == 18
    assert len(ontology.actions) == 46
    assert len(ontology.entity_types) == 55
    assert len(ontology.intents) == 60
    assert len(ontology.scenarios) * len(ontology.actions) == 828


def test_flight_script_pins_the_real_sealed_m0_instruction_prefix():
    """The flight script's pinned comparator constants must agree with what
    the registered template plus fill actually render.

    The script is read as TEXT rather than imported: it carries deliberate
    import-time guards on ``REPO``/``PYTHONPATH`` that a test process has no
    business satisfying, and the two sibling flight scripts are loaded the
    same way. What matters is that the number it refuses on is the number
    this repository actually produces.
    """

    import hashlib
    import re

    lock, root = _real_corpus()
    values = {
        "task_instruction_template": TEMPLATE_RELPATH,
        "task_instruction_fill": FILL_NAME,
        "task_instruction_template_active": True,
    }
    rendered = resolve_active_task_instruction(values, REPO_ROOT, lock, root)
    source = (
        REPO_ROOT / "scripts" / "flights" / "run_slurp_closed_list_cell.py"
    ).read_text(encoding="utf-8")
    pinned_hash = re.search(r'SEALED_M0_INSTRUCTION_SHA256 = \(\s*"([0-9a-f]{64})"', source)
    pinned_chars = re.search(r"SEALED_M0_INSTRUCTION_CHARS = (\d+)", source)
    assert pinned_hash and pinned_chars
    chars = int(pinned_chars.group(1))
    assert len(rendered) > chars
    measured = hashlib.sha256(rendered[:chars].encode("utf-8")).hexdigest()
    assert measured == pinned_hash.group(1)
    # and the suffix is exactly the compact inventory, joined by one blank line
    ontology = load_slurp_ontology(lock, root)
    assert rendered[chars:] == "\n\n" + render_slurp_label_inventory(ontology)


def test_no_committed_fragment_names_the_held_out_split():
    for relpath in (
        "configs/baseline/slurp-direct-closed-list.json",
        "configs/experiment/slurp-dev1000-closed-list-direct-v1.json",
        "configs/experiment/slurp-dev1000-closed-list-direct-smoke-v1.json",
    ):
        text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
        assert "slurp:test:" not in text
        assert "allow_heldout" not in text
