"""WAVE W4: the four config tables and their null arm.

The property the whole wave rests on is in the first section: a table
written out as its null arm composes to the SAME config hash as the table
being absent. Without it, "module off" is a third cell identity and the
admission gate's paired arm is not a twin of the pre-table baseline.
"""

import json

import pytest

from speech_aware_evidence_acquisition.core.config import (
    NULL_ARM_TABLE_KEYS,
    compose,
    drop_null_arms,
    fragment_hash,
)
from speech_aware_evidence_acquisition.rails.config_tables import (
    CONFIG_TABLE_NAMES,
    LEGACY_OBSERVE_KEYS,
    ConfigTableError,
    ConfigTables,
    config_key_diff,
    flatten_config,
    load_config_tables,
    load_judges_table,
    load_knowledge_views_table,
    load_observe_table,
    load_toolkits_table,
    table_entry_keys,
    unwrap_judges,
    unwrap_knowledge_views,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.phase_material import (
    load_phase_material_specs,
)
from speech_aware_evidence_acquisition.rails.phase_review import (
    load_phase_review_specs,
)
from speech_aware_evidence_acquisition.rails.phase_supply import load_phase_supply_specs

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]

JUDGE_ID = "e21-substitution-alignment-flag-v1"
SHA = "a" * 64


def _write_fragments(root, *, baseline_extra=None):
    for kind, name, body in (
        ("model", "m", {"transport": "llama-server", "base_url": "http://x"}),
        ("dataset", "d", {"carrier_lock_key": "earnings21-original", "split_name": "dev"}),
        (
            "baseline",
            "b",
            {"arm": "bare-core", "policy": "fixed", **(baseline_extra or {})},
        ),
        ("experiment", "e", {"experiment_id": "SAEA-E-001"}),
    ):
        path = root / "configs" / kind / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body), encoding="utf-8")


def _draft_revise():
    return default_phase_program("phase-draft-revise-v1")


def _material(template="probes/select.txt"):
    return {"instruction_template": template}


# ---------------------------------------------------------------------------
# 1. The null arm IS the absence -- of the hash, and of the composed values.
# ---------------------------------------------------------------------------


def test_the_four_tables_and_the_hash_rule_name_the_same_keys():
    assert CONFIG_TABLE_NAMES == NULL_ARM_TABLE_KEYS
    assert CONFIG_TABLE_NAMES == ("judges", "knowledge_views", "observe", "toolkits")


@pytest.mark.parametrize("table", CONFIG_TABLE_NAMES)
@pytest.mark.parametrize("null_arm", [None, {}])
def test_a_null_arm_composes_to_the_hash_of_the_block_being_absent(
    tmp_path, table, null_arm
):
    absent = tmp_path / "absent"
    declared = tmp_path / "declared"
    _write_fragments(absent)
    _write_fragments(declared, baseline_extra={table: null_arm})
    without = compose(absent, "m", "d", "b", "e")
    with_null = compose(declared, "m", "d", "b", "e")
    assert with_null.config_hash == without.config_hash
    assert dict(with_null.values) == dict(without.values)
    assert table not in with_null.values


@pytest.mark.parametrize("table", CONFIG_TABLE_NAMES)
def test_a_non_null_arm_does_move_the_config_hash(tmp_path, table):
    absent = tmp_path / "absent"
    declared = tmp_path / "declared"
    _write_fragments(absent)
    _write_fragments(declared, baseline_extra={table: {"draft": {"tail": 1}}})
    assert (
        compose(declared, "m", "d", "b", "e").config_hash
        != compose(absent, "m", "d", "b", "e").config_hash
    )


@pytest.mark.parametrize("table", CONFIG_TABLE_NAMES)
def test_fragment_hash_applies_the_same_null_arm_rule(table):
    assert fragment_hash({"arm": "x", table: None}) == fragment_hash({"arm": "x"})
    assert fragment_hash({"arm": "x", table: {}}) == fragment_hash({"arm": "x"})


def test_drop_null_arms_leaves_every_other_explicit_null_alone():
    """Narrow by construction: elsewhere in this study an explicit ``null``
    is a real declaration (``d1_media_supplement`` is refused unless it and
    its sha256 are both present or both absent), so a blanket drop-every-null
    rule would quietly erase a pairing the gate depends on."""

    values = {"d1_media_supplement": None, "decoding_params": None, "observe": None}
    assert drop_null_arms(values) == {
        "d1_media_supplement": None,
        "decoding_params": None,
    }


def test_drop_null_arms_is_a_no_op_on_a_mapping_without_a_table_key():
    values = {"arm": "bare-core", "policy": "fixed", "scorers": []}
    assert drop_null_arms(values) == values


def test_a_null_arm_in_one_fragment_still_collides_with_a_table_in_another(tmp_path):
    """The drop happens AFTER the cross-fragment collision check, so two
    fragments declaring the same table are still refused rather than silently
    resolved in the non-null one's favour."""

    _write_fragments(tmp_path, baseline_extra={"observe": None})
    path = tmp_path / "configs" / "experiment" / "e.json"
    path.write_text(
        json.dumps({"experiment_id": "SAEA-E-001", "observe": {"draft": {}}}),
        encoding="utf-8",
    )
    with pytest.raises(Exception, match="collision"):
        compose(tmp_path, "m", "d", "b", "e")


def test_no_committed_fragment_declares_a_null_arm_so_no_existing_config_hash_moves():
    """The proof that this wave moved no already-flown cell's identity: not
    one composed fragment in the repository carries a table key at all, let
    alone one carrying its null arm."""

    offenders = []
    for kind in ("model", "dataset", "baseline", "experiment"):
        for path in sorted((REPO_ROOT / "configs" / kind).glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                continue
            for table in CONFIG_TABLE_NAMES:
                if table in document:
                    offenders.append(f"{kind}/{path.name}::{table}")
    assert offenders == []


# ---------------------------------------------------------------------------
# 2. observe
# ---------------------------------------------------------------------------


def test_observe_null_arm_declares_no_mode():
    program = _draft_revise()
    for values in ({}, {"observe": None}, {"observe": {}}):
        assert load_observe_table(values, program) == {}


def test_observe_loads_the_three_modes_in_program_phase_order():
    program = _draft_revise()
    specs = load_observe_table(
        {
            "observe": {
                "revise": {"tail_silence_seconds": 2.0},
                "draft": {
                    "unit_plan": {"relpath": "docs/obs/plan.json", "sha256": SHA},
                    "relisten": {
                        "judges": [JUDGE_ID],
                        "context_margin_seconds": 1.5,
                        "max_relistens_per_sample": 2,
                    },
                },
            }
        },
        program,
    )
    assert list(specs) == ["draft", "revise"]
    assert specs["revise"].tail_silence_seconds == 2.0
    assert specs["draft"].unit_plan.sha256 == SHA
    assert specs["draft"].relisten.config.derivation_kind == "recut-span"
    assert specs["draft"].as_json()["relisten"]["judges"] == [JUDGE_ID]


def test_observe_accepts_a_pinned_fixture_flag_source():
    specs = load_observe_table(
        {
            "observe": {
                "draft": {
                    "relisten": {
                        "fixture": {"relpath": "docs/obs/flags.json", "sha256": SHA},
                        "context_margin_seconds": 0.0,
                        "max_relistens_per_sample": 1,
                        "derivation_kind": "recut-span",
                    }
                }
            }
        },
        _draft_revise(),
    )
    assert specs["draft"].relisten.fixture.relpath == "docs/obs/flags.json"


@pytest.mark.parametrize(
    "entry, message",
    [
        ({}, "selects no observe mode"),
        ({"tail_silence_seconds": -1.0}, "non-negative"),
        ({"tail_silence_seconds": "2"}, "finite number"),
        ({"unit_plan": {"relpath": "p.json"}}, "must carry"),
        ({"unit_plan": {"relpath": "/abs.json", "sha256": SHA}}, "must be relative"),
        ({"unit_plan": {"relpath": "a/../b.json", "sha256": SHA}}, "traversal"),
        ({"unit_plan": {"relpath": "p.json", "sha256": "nope"}}, "64-hex"),
        ({"tail": 1.0}, "unknown key"),
        (
            {"relisten": {"context_margin_seconds": 1.0, "max_relistens_per_sample": 1}},
            "exactly one flag source",
        ),
        (
            {
                "relisten": {
                    "judges": [JUDGE_ID],
                    "fixture": {"relpath": "f.json", "sha256": SHA},
                    "context_margin_seconds": 1.0,
                    "max_relistens_per_sample": 1,
                }
            },
            "exactly one flag source",
        ),
        (
            {"relisten": {"judges": ["not-a-judge"], "context_margin_seconds": 1.0,
                          "max_relistens_per_sample": 1}},
            "not-a-judge",
        ),
        (
            {"relisten": {"judges": [JUDGE_ID], "context_margin_seconds": 1.0}},
            "max_relistens_per_sample",
        ),
    ],
)
def test_observe_refuses_a_malformed_row(entry, message):
    with pytest.raises(ConfigTableError, match=message):
        load_observe_table({"observe": {"draft": entry}}, _draft_revise())


def test_observe_refuses_a_phase_the_program_does_not_declare():
    with pytest.raises(ConfigTableError, match="does not declare"):
        load_observe_table({"observe": {"nope": {"tail_silence_seconds": 1.0}}}, _draft_revise())


def test_observe_refuses_a_relisten_whose_derivation_kind_is_unknown():
    with pytest.raises(Exception, match="derivation_kind"):
        load_observe_table(
            {
                "observe": {
                    "draft": {
                        "relisten": {
                            "judges": [JUDGE_ID],
                            "context_margin_seconds": 1.0,
                            "max_relistens_per_sample": 1,
                            "derivation_kind": "hallucinated-copy",
                        }
                    }
                }
            },
            _draft_revise(),
        )


@pytest.mark.parametrize("legacy", LEGACY_OBSERVE_KEYS)
def test_observe_refuses_a_fragment_that_also_carries_the_flat_obs_knobs(legacy):
    with pytest.raises(ConfigTableError, match="two switches for one module"):
        load_observe_table(
            {"observe": {"draft": {"tail_silence_seconds": 2.0}}, legacy: 2.0},
            _draft_revise(),
        )


def test_the_flat_obs_knobs_stay_legal_while_the_observe_table_is_absent():
    assert load_observe_table({"obs_slice_tail_silence_seconds": 2.0}, _draft_revise()) == {}


# ---------------------------------------------------------------------------
# 3. knowledge_views -- wraps E1/E6 without changing their bytes
# ---------------------------------------------------------------------------


def test_knowledge_views_produces_the_same_specs_as_the_flat_blocks():
    program = _draft_revise()
    flat = {"phase_material": {"draft": _material(), "revise": _material("probes/fill.txt")}}
    wrapped = {
        "knowledge_views": {
            "draft": {"material": _material()},
            "revise": {"material": _material("probes/fill.txt")},
        }
    }
    assert unwrap_knowledge_views(wrapped)["phase_material"] == flat["phase_material"]
    from_flat = load_phase_material_specs(flat, program)
    from_table = load_knowledge_views_table(wrapped, program).material
    assert dict(from_table) == dict(from_flat)


def test_knowledge_views_carries_a_supply_entry_verbatim():
    program = default_phase_program("phase-slots-given-intent-supplied-v1")
    supply = {
        "provider": "kb-facet-v1",
        "rank_policy": "saea-rank-wcos-prior-agree-v1",
        "fuse_policy": "saea-fuse-supplyfilter-v1",
        "k": 5,
        "tau": 0.65,
        "dimensions": ["content"],
        "query_source": {
            "kind": "sealed-vectors",
            "relpath": "vectors/q.jsonl",
            "sha256": SHA,
            "tool_contact_ledger_row": "row-1",
            "embedded_signal": "speech: the row's own packet",
        },
        "facet_source": {
            "kind": "sealed-vectors",
            "relpath": "vectors/f.jsonl",
            "sha256": SHA,
            "tool_contact_ledger_row": "row-1",
            "embedded_signal": "the facet text",
        },
    }
    flat = {"phase_material": {"slots": _material()}, "phase_supply": {"slots": supply}}
    wrapped = {
        "knowledge_views": {"slots": {"material": _material(), "supply": supply}}
    }
    assert unwrap_knowledge_views(wrapped)["phase_supply"] == {"slots": supply}
    assert dict(load_knowledge_views_table(wrapped, program).supply) == dict(
        load_phase_supply_specs(flat, program)
    )


def test_knowledge_views_null_arm_falls_back_to_the_flat_blocks():
    program = _draft_revise()
    flat = {
        "knowledge_views": None,
        "phase_material": {"draft": _material(), "revise": _material()},
    }
    assert set(load_knowledge_views_table(flat, program).material) == {"draft", "revise"}


def test_knowledge_views_refuses_a_fragment_that_also_declares_the_flat_block():
    with pytest.raises(ConfigTableError, match="two spellings of one switch"):
        load_knowledge_views_table(
            {
                "knowledge_views": {"draft": {"material": _material()}},
                "phase_material": {"draft": _material()},
            },
            _draft_revise(),
        )


def test_knowledge_views_refuses_an_unknown_entry_key():
    with pytest.raises(ConfigTableError, match="unknown key"):
        load_knowledge_views_table(
            {"knowledge_views": {"draft": {"views": ["x"]}}}, _draft_revise()
        )


def test_knowledge_views_delegates_the_missing_material_refusal_to_e1():
    """A phase program still needs material for EVERY phase -- E1's own rule,
    reached through the table rather than restated in it."""

    with pytest.raises(Exception, match="revise"):
        load_knowledge_views_table(
            {"knowledge_views": {"draft": {"material": _material()}}}, _draft_revise()
        )


# ---------------------------------------------------------------------------
# 4. judges -- wraps W1's phase_review without changing its bytes
# ---------------------------------------------------------------------------


def test_judges_produces_the_same_specs_as_phase_review():
    program = _draft_revise()
    entry = {"judges": [JUDGE_ID], "on_flag": "record"}
    assert unwrap_judges({"judges": {"revise": entry}})["phase_review"] == {
        "revise": entry
    }
    assert dict(load_judges_table({"judges": {"revise": entry}}, program)) == dict(
        load_phase_review_specs({"phase_review": {"revise": entry}}, program)
    )


def test_judges_null_arm_reviews_nothing():
    program = _draft_revise()
    for values in ({}, {"judges": None}, {"judges": {}}):
        assert load_judges_table(values, program) == {}


def test_judges_null_arm_falls_back_to_the_flat_phase_review_block():
    specs = load_judges_table(
        {"judges": None, "phase_review": {"revise": {"judges": [JUDGE_ID]}}},
        _draft_revise(),
    )
    assert set(specs) == {"revise"}


def test_judges_refuses_a_fragment_that_also_declares_phase_review():
    with pytest.raises(ConfigTableError, match="two spellings of one switch"):
        load_judges_table(
            {
                "judges": {"revise": {"judges": [JUDGE_ID]}},
                "phase_review": {"revise": {"judges": [JUDGE_ID]}},
            },
            _draft_revise(),
        )


def test_judges_refuses_an_unknown_entry_key_before_w1_sees_it():
    with pytest.raises(ConfigTableError, match="unknown key"):
        load_judges_table(
            {"judges": {"revise": {"judge": [JUDGE_ID]}}}, _draft_revise()
        )


def test_judges_inherits_w1s_on_flag_loop_refusal():
    with pytest.raises(Exception, match="on_flag='loop' is not wired yet"):
        load_judges_table(
            {"judges": {"revise": {"judges": [JUDGE_ID], "on_flag": "loop"}}},
            _draft_revise(),
        )


# ---------------------------------------------------------------------------
# 5. toolkits
# ---------------------------------------------------------------------------


def test_toolkits_null_arm_arms_no_tool():
    for values in ({}, {"toolkits": None}, {"toolkits": {}}):
        assert load_toolkits_table(values) is None


def test_toolkits_selects_one_task_type_row_of_w3s_table():
    selection = load_toolkits_table({"toolkits": {"task_type": "meeting"}})
    assert selection.task_type == "meeting"
    assert selection.roles == ("planner", "observer", "reviewer")
    assert "saea-tool-speaker-turn-units-v2" in selection.tools_by_role["observer"]


def test_toolkits_roles_select_a_subset_and_keep_table_order():
    selection = load_toolkits_table(
        {"toolkits": {"task_type": "command", "roles": ["reviewer", "planner"]}}
    )
    assert selection.roles == ("planner", "reviewer")
    assert set(selection.tools_by_role) == {"planner", "reviewer"}


def test_command_toolkit_preserves_legacy_identity_until_memory_is_explicitly_armed():
    base = {"toolkits": {"task_type": "command", "roles": ["planner"]}}
    historical = load_toolkits_table(base)
    assert historical.tools_by_role["planner"] == (
        "saea-tool-prompt-fit-tokens-v1",
        "saea-tool-task-contract-v1",
        "saea-tool-phase-knowledge-v1",
    )

    armed = load_toolkits_table(
        {
            **base,
            "experience_memory": {"pinned": "synthetic binding"},
            "phase_tools": {
                "draft": {
                    "allowed_tools": ["saea-tool-corrective-memory-v1"],
                }
            },
        }
    )
    assert armed.tools_by_role["planner"] == (
        *historical.tools_by_role["planner"],
        "saea-tool-corrective-memory-v1",
    )


@pytest.mark.parametrize(
    "entry, message",
    [
        ({"task_type": "meetings"}, "unknown task type"),
        ({"task_type": "meeting", "roles": []}, "arms no role"),
        ({"task_type": "meeting", "roles": ["solver"]}, "the roles that may call"),
        ({"task_type": "meeting", "roles": ["planner", "planner"]}, "repeats"),
        ({"task_type": "meeting", "role": ["planner"]}, "unknown key"),
        ({"roles": ["planner"]}, "task_type"),
    ],
)
def test_toolkits_refuses_a_malformed_selection(entry, message):
    with pytest.raises(ConfigTableError, match=message):
        load_toolkits_table({"toolkits": entry})


# ---------------------------------------------------------------------------
# 6. The bundle and the flattened-config diff
# ---------------------------------------------------------------------------


def test_load_config_tables_loads_all_four_and_hashes_them():
    program = _draft_revise()
    values = {
        "observe": {"draft": {"tail_silence_seconds": 2.0}},
        "knowledge_views": {
            "draft": {"material": _material()},
            "revise": {"material": _material("probes/fill.txt")},
        },
        "judges": {"revise": {"judges": [JUDGE_ID]}},
        "toolkits": {"task_type": "meeting"},
    }
    tables = load_config_tables(values, program)
    assert isinstance(tables, ConfigTables)
    assert set(tables.observe) == {"draft"}
    assert set(tables.judges) == {"revise"}
    assert tables.toolkits.task_type == "meeting"
    assert tables.content_hash() == load_config_tables(values, program).content_hash()

    off = dict(values, observe=None)
    assert load_config_tables(off, program).content_hash() != tables.content_hash()


def test_an_empty_bundle_is_the_all_null_arm():
    program = _draft_revise()
    flat = {"phase_material": {"draft": _material(), "revise": _material()}}
    tables = load_config_tables(flat, program)
    assert tables.observe == {} and tables.judges == {} and tables.toolkits is None


def test_flatten_config_walks_objects_and_leaves_lists_whole():
    flat = flatten_config({"a": {"b": {"c": 1}}, "d": [1, 2], "e": {}})
    assert flat == {"a.b.c": 1, "d": [1, 2], "e": {}}


def test_config_key_diff_names_every_changed_added_and_removed_key():
    assert config_key_diff({"a": 1, "b": {"c": 2}}, {"a": 1, "b": {"c": 3}}) == ("b.c",)
    assert config_key_diff({"a": 1, "b": 2}, {"a": 1}) == ("b",)
    assert config_key_diff({"a": 1}, {"a": 1}) == ()


def test_table_entry_keys_refuses_a_table_that_does_not_exist():
    assert table_entry_keys("observe") == ("relisten", "tail_silence_seconds", "unit_plan")
    with pytest.raises(ConfigTableError, match="unknown config table"):
        table_entry_keys("modes")
