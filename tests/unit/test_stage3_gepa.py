"""Stage-3 layer A, the GEPA arm: the proof obligations of the design note
``docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md``.

Six groups of obligations:

1. The closed-form proposal parser never raises, retains every illegal block
   with its reason, and enforces the one invariant its ADV-1 sibling does not
   (a contact is addressed to ONE node).
2. The registered program, controller and response format load, and the format
   and the parser are one contract.
3. The per-group instruction renderer refuses a template missing a placeholder
   and substitutes every one of them literally.
4. The group builder ranks, de-duplicates, tops up carriers, slices the current
   deltas and excludes a scenario with no eligible row -- deterministically.
5. The material resolver dispatches on the PROGRAM (both construction-visible
   cells fly the same arm), verifies every pin it was handed, refuses a custody
   drift, and never writes rendered text into a receipt.
6. The GEPA curation produces the group-keyed row shape, drops a wrong-node
   block, absorbs a verbatim repeat as a REVISION, and leaves the existing twin
   builder's two invariants exact.

Every fixture is synthetic: no real SLURP utterance, gold or model output
appears anywhere in this file.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    AGENT_CONTROLLERS,
    RESPONSE_FORMATS,
)
from speech_aware_evidence_acquisition.rails import controllers as _controllers  # noqa: E402,F401
from speech_aware_evidence_acquisition.rails.stage3_gepa import (  # noqa: E402
    LEGAL_GEPA_DELTA_KINDS,
    LEGAL_GEPA_NODES,
    MAX_GEPA_BLOCKS,
    NO_CURRENT_DELTAS,
    STAGE3_GEPA_ARM,
    STAGE3_GEPA_PHASE_NAME,
    STAGE3_GEPA_PROGRAM_ID,
    STAGE3_GEPA_RESPONSE_FORMAT_ID,
    STAGE3_GEPA_TEMPLATE_RELPATH,
    TEMPLATE_PLACEHOLDERS,
    Stage3GepaError,
    gepa_group_id,
    parse_gepa_proposal,
    render_current_deltas,
    render_gepa_instruction,
    render_group_row_block,
    stage3_gepa_response_format_v1,
)
from speech_aware_evidence_acquisition.rails.stage3_advantage_material import (  # noqa: E402
    Stage3AdvantageMaterialError,
)
from speech_aware_evidence_acquisition.rails.stage3_gepa_material import (  # noqa: E402
    GEPA_CONTACT_SCHEMA,
    Stage3GepaMaterialError,
    build_gepa_material,
)


def _load_script(name: str):
    path = REPO_ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"saea_test_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GROUPS = _load_script("build_slurp_stage3_gepa_groups.py")
CURATOR = _load_script("build_slurp_stage3_gepa_delta_rows.py")
TWIN = _load_script("build_slurp_stage3_delta_twin.py")


def _block(node="solver", kind="slot-contract", target="alarm_set", statement="say less"):
    return f"NODE: {node}\nDELTA-KIND: {kind}\nTARGET: {target}\nSTATEMENT: {statement}\n"


# --------------------------------------------------------------------------- 1


def test_the_parser_never_raises_on_anything():
    for value in (None, 17, b"bytes", "", "prose with no keys at all", {"a": 1}):
        parsed = parse_gepa_proposal(value, node="solver")
        assert parsed.legal is False
        assert parsed.illegal_reasons


def test_a_single_well_formed_block_is_legal_and_carries_its_task_target():
    parsed = parse_gepa_proposal(_block(), node="solver")
    assert parsed.legal is True
    assert len(parsed.blocks) == 1
    assert parsed.blocks[0].task_target() == "solver:slot-contract:alarm_set"
    assert parsed.blocks[0].word_count() == 2
    assert parsed.expected_node == "solver"


def test_five_blocks_are_the_form_and_a_sixth_is_retained_and_illegal():
    text = "".join(_block(statement=f"statement number {index}") for index in range(6))
    parsed = parse_gepa_proposal(text, node="solver")
    assert len(parsed.blocks) == 6
    assert parsed.legal is False
    assert any("exceed" in reason for reason in parsed.illegal_reasons)
    assert parsed.blocks[MAX_GEPA_BLOCKS].legal is False
    assert len(parsed.legal_blocks()) == MAX_GEPA_BLOCKS


def test_a_block_naming_another_node_is_retained_and_marked_illegal():
    parsed = parse_gepa_proposal(_block(node="reviewer"), node="solver")
    assert parsed.legal is False
    assert parsed.blocks[0].node == "reviewer"
    assert any(
        "is not this group's node" in reason for reason in parsed.blocks[0].illegal_reasons
    )
    # Without the group's node the very same text reads legal: the invariant is
    # the CONTACT's, not the grammar's.
    assert parse_gepa_proposal(_block(node="reviewer")).legal is True


def test_out_of_vocabulary_and_over_long_blocks_are_retained_with_their_reasons():
    parsed = parse_gepa_proposal(_block(kind="wishful-thinking"), node="solver")
    assert any("illegal delta-kind" in r for r in parsed.blocks[0].illegal_reasons)
    long_statement = " ".join(["word"] * 41)
    parsed = parse_gepa_proposal(_block(statement=long_statement), node="solver")
    assert any("exceeds 40 words" in r for r in parsed.blocks[0].illegal_reasons)
    parsed = parse_gepa_proposal("DELTA-KIND: slot-contract\n", node="solver")
    assert any("missing keys" in r for r in parsed.blocks[0].illegal_reasons)


def test_the_receipt_carries_digests_and_labels_but_never_the_statement():
    receipt = parse_gepa_proposal(_block(statement="a secret lesson"), node="solver").receipt()
    blob = json.dumps(receipt)
    assert "a secret lesson" not in blob
    assert receipt["blocks"][0]["statement_sha256"] == hashlib.sha256(
        b"a secret lesson"
    ).hexdigest()
    assert receipt["expected_node"] == "solver"


# --------------------------------------------------------------------------- 2


def test_the_program_controller_and_response_format_are_registered():
    program = _controllers.default_phase_program(STAGE3_GEPA_PROGRAM_ID)
    assert [phase.name for phase in program.phases] == [STAGE3_GEPA_PHASE_NAME]
    assert program.max_contacts == 1
    assert program.phases[0].response_format_id == STAGE3_GEPA_RESPONSE_FORMAT_ID
    assert program.phases[0].knowledge == "none"
    assert STAGE3_GEPA_PROGRAM_ID in set(AGENT_CONTROLLERS.names())
    assert STAGE3_GEPA_RESPONSE_FORMAT_ID in set(RESPONSE_FORMATS.names())


def test_the_response_format_and_the_parser_are_one_contract():
    schema = stage3_gepa_response_format_v1({}, REPO_ROOT)["json_schema"]["schema"]
    blocks = schema["properties"]["blocks"]
    assert blocks["maxItems"] == MAX_GEPA_BLOCKS
    item = blocks["items"]["properties"]
    assert item["node"]["enum"] == list(LEGAL_GEPA_NODES)
    assert item["delta_kind"]["enum"] == list(LEGAL_GEPA_DELTA_KINDS)
    # A structured reply of exactly this shape is read by the SAME parser.
    reply = json.dumps(
        {
            "blocks": [
                {
                    "node": "planner",
                    "delta_kind": "planner-rule",
                    "target": "alarm_set",
                    "statement": "stop revising",
                }
            ]
        }
    )
    parsed = parse_gepa_proposal(reply, node="planner")
    assert parsed.legal is True
    assert parsed.source_form == "json"
    assert parsed.blocks[0].target == "alarm_set"


def test_the_gepa_arm_is_the_existing_construction_visible_arm():
    from speech_aware_evidence_acquisition.contracts.identifiers import (
        CONSTRUCTION_VISIBLE_ARMS,
    )

    assert STAGE3_GEPA_ARM in CONSTRUCTION_VISIBLE_ARMS


# --------------------------------------------------------------------------- 3


def test_the_committed_template_carries_every_placeholder_and_renders_them():
    template = (REPO_ROOT / "configs" / STAGE3_GEPA_TEMPLATE_RELPATH).read_text(
        encoding="utf-8"
    )
    for placeholder in TEMPLATE_PLACEHOLDERS:
        assert placeholder in template
    rendered = render_gepa_instruction(
        template,
        scenario="alarm",
        node="solver",
        current_deltas_text="1. keep it short",
        worst_rows_text="WORST BLOCK",
        best_rows_text="BEST BLOCK",
    )
    for placeholder in TEMPLATE_PLACEHOLDERS:
        assert placeholder not in rendered
    assert "WORST BLOCK" in rendered and "BEST BLOCK" in rendered


def test_the_renderer_refuses_a_template_missing_a_placeholder_or_a_bad_node():
    with pytest.raises(Stage3GepaError):
        render_gepa_instruction(
            "{scenario} {node} {current_deltas} {worst_rows}",
            scenario="alarm",
            node="solver",
            current_deltas_text="",
            worst_rows_text="",
            best_rows_text="",
        )
    template = (REPO_ROOT / "configs" / STAGE3_GEPA_TEMPLATE_RELPATH).read_text(
        encoding="utf-8"
    )
    with pytest.raises(Stage3GepaError):
        render_gepa_instruction(
            template,
            scenario="alarm",
            node="not-a-node",
            current_deltas_text="",
            worst_rows_text="",
            best_rows_text="",
        )


def test_an_empty_current_delta_slice_is_stated_rather_than_omitted():
    assert render_current_deltas([]) == NO_CURRENT_DELTAS
    assert render_current_deltas(["  ", ""]) == NO_CURRENT_DELTAS
    assert render_current_deltas(["a", "b"]).splitlines() == ["1. a", "2. b"]


def test_a_row_block_names_its_side_and_shows_every_section():
    block = render_group_row_block(
        position=2,
        label="WORSE OUTCOME",
        candidate_list_text="1. alarm_set",
        best_answer_text="A",
        worst_answer_text="B",
        delivered_answer_text="D",
        reviewer_verdicts_text="visit 1: accept",
        planner_route_text="1. deliver (legal)",
        gold_text="G",
    )
    assert "--- ROW 2 (WORSE OUTCOME) ---" in block
    for marker in (
        "PERCEPTION CANDIDATES:",
        "SOLVER SAMPLE A",
        "SOLVER SAMPLE B",
        "DELIVERED ANSWER:",
        "REVIEWER VERDICTS:",
        "PLANNER ROUTE:",
        "CORRECT ANSWER:",
    ):
        assert marker in block


# --------------------------------------------------------------------------- 4
# The group builder.


def _eligible(**rows):
    return {
        sample_id: {"stratum": stratum, "best_index": 0, "worst_index": 1, "disagreement": mass}
        for sample_id, (stratum, mass) in rows.items()
    }


def test_scenario_rows_rank_ascending_dedup_and_read_outward_from_the_extreme():
    eligible = _eligible(**{f"s{i}": ("alarm", 0.1) for i in range(5)})
    means = {f"s{i}": float(i) for i in range(5)}
    out = GROUPS.scenario_rows(eligible, means, k=2, metric="group-mean")["alarm"]
    assert out["worst"] == ["s0", "s1"]
    assert out["best"] == ["s4", "s3"]
    assert out["ordered"] == ["s0", "s1", "s4", "s3"]
    # k larger than the population: the ranked list is SPLIT rather than taken
    # twice, so no row is ever both a worst-outcome and a best-outcome example.
    out = GROUPS.scenario_rows(eligible, means, k=9, metric="group-mean")["alarm"]
    assert out["worst"] == ["s0", "s1", "s2"]
    assert out["best"] == ["s4", "s3"]
    assert sorted(out["ordered"]) == sorted(means)
    assert len(out["ordered"]) == len(set(out["ordered"]))
    assert not set(out["worst"]) & set(out["best"])
    # a single eligible row is shown once, as the worst
    single = GROUPS.scenario_rows(
        {"only": {"stratum": "alarm", "disagreement": 0.1}}, {"only": 0.1}, k=6,
        metric="group-mean",
    )["alarm"]
    assert single["worst"] == ["only"] and single["best"] == []


def test_the_ranking_metric_is_a_choice_and_disagreement_ranks_differently():
    eligible = _eligible(a=("alarm", 0.9), b=("alarm", 0.1))
    means = {"a": 0.0, "b": 1.0}
    by_mean = GROUPS.scenario_rows(eligible, means, k=1, metric="group-mean")["alarm"]
    by_dis = GROUPS.scenario_rows(eligible, means, k=1, metric="disagreement")["alarm"]
    assert by_mean["worst"] == ["a"]
    assert by_dis["worst"] == ["b"]


def test_current_delta_slice_is_node_and_scenario_bound_ranked_and_capped():
    authored = [
        {"value_id": "delta:1:aaa", "node_target": "solver", "facet_ids": ["alarm_set"], "prior_score": 0.1},
        {"value_id": "delta:1:bbb", "node_target": "solver", "facet_ids": ["alarm_remove"], "prior_score": 0.9},
        {"value_id": "delta:1:ccc", "node_target": "reviewer", "facet_ids": ["alarm_set"], "prior_score": 0.5},
        {"value_id": "delta:1:ddd", "node_target": "solver", "facet_ids": ["email_query"], "prior_score": 0.7},
    ]
    got = GROUPS.current_delta_slice(authored, scenario="alarm", node="solver", cap=9)
    assert got == ["delta:1:bbb", "delta:1:aaa"]
    assert GROUPS.current_delta_slice(authored, scenario="alarm", node="solver", cap=1) == [
        "delta:1:bbb"
    ]
    assert GROUPS.current_delta_slice(authored, scenario="news", node="solver", cap=9) == []


def test_carriers_are_distinct_per_scenario_and_top_up_from_the_roster():
    eligible = _eligible(a=("alarm", 0.5))
    means = {"a": 0.5}
    roster = {
        sample_id: {"stratum": "alarm", "audio_seconds": 1.0}
        for sample_id in ("a", "b", "c", "d", "e")
    }
    groups, counts = GROUPS.build_groups(
        eligible=eligible,
        means=means,
        roster=roster,
        authored=[],
        gold_intents={"a": "alarm_set"},
        k=6,
        metric="group-mean",
        current_delta_cap=12,
    )
    assert len(groups) == 4
    carriers = [group["carrier_sample_id"] for group in groups]
    assert len(set(carriers)) == 4
    assert groups[0]["carrier_from"] == "group"
    assert [group["carrier_from"] for group in groups[1:]] == ["roster-topup"] * 3
    assert counts["carriers_from_roster_topup"] == 3
    # every group still shows the SAME single group row
    assert {tuple(group["row_sample_ids"]) for group in groups} == {("a",)}
    assert groups[0]["gold_intent_ids"] == ["alarm_set"]
    assert groups[0]["disagreement_mean"] == pytest.approx(0.5)


def test_a_scenario_that_cannot_supply_four_distinct_carriers_is_refused():
    eligible = _eligible(a=("alarm", 0.5))
    with pytest.raises(GROUPS.Stage3GepaGroupsError):
        GROUPS.build_groups(
            eligible=eligible,
            means={"a": 0.5},
            roster={"a": {"stratum": "alarm", "audio_seconds": 1.0}},
            authored=[],
            gold_intents={},
            k=6,
            metric="group-mean",
            current_delta_cap=12,
        )


def test_scenario_of_reads_the_prefix_of_an_intent_id():
    assert GROUPS.scenario_of("iot_hue_lightchange") == "iot"
    assert GROUPS.scenario_of("alarm") == "alarm"


# --------------------------------------------------------------------------- 5
# The material resolver.


def _answer(scenario="alarm", action="set", filler="seven"):
    return json.dumps(
        {
            "scenario": scenario,
            "action": action,
            "entities": [{"type": "time", "filler": filler}],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def gepa_fixture(tmp_path, monkeypatch):
    """A whole synthetic flight: pairs.json, sealed custody, deltas, groups."""

    data_root = tmp_path / "data"
    run_id, attempt_id = "RUN-V1", "attempt-v1"
    run_dir = data_root / "runs" / run_id / attempt_id
    run_dir.mkdir(parents=True)
    analysis = data_root / "analysis" / "SCORE-V1"
    analysis.mkdir(parents=True)
    prepared = data_root / "prepared" / "GEPA-V1"
    prepared.mkdir(parents=True)

    best, worst = _answer(filler="seven"), _answer(filler="eight")
    rows, pairs, sealed = [], [], []
    for index, sample_id in enumerate(("row-a", "row-b")):
        rows.append(
            {
                "sample_id": sample_id,
                "best": {"sample_index": 0, "response_text_sha256": _digest(best)},
                "worst": {"sample_index": 1, "response_text_sha256": _digest(worst)},
            }
        )
        pairs.append(
            {
                "sample_id": sample_id,
                "stratum": "alarm",
                "best_index": 0,
                "worst_index": 1,
                "disagreement": 0.25 + index,
                "trajectory": {
                    "available": True,
                    "perception": {
                        "candidate_intent_ids": ["alarm_set", "alarm_remove"],
                        "raw_candidate_count": 3,
                    },
                    "delivered": {
                        "kind": "commit",
                        "revision_count": 1,
                        "reviewer_verdicts": [{"visit": 1, "token": "ACCEPT"}],
                        "planner_actions": [{"action": "deliver", "legal": True}],
                    },
                },
            }
        )
        sealed.append(
            {
                "sample_id": sample_id,
                "text": "DELIVERED TEXT",
                "solver_group": {
                    "samples": [
                        {
                            "sample_index": 0,
                            "parse_status": "ok",
                            "parsed_answer": json.loads(best),
                        },
                        {
                            "sample_index": 1,
                            "parse_status": "ok",
                            "parsed_answer": json.loads(worst),
                        },
                    ]
                },
            }
        )
    pairs_path = analysis / "pairs.json"
    pairs_path.write_text(
        json.dumps(
            {
                "schema": "saea-stage3-rollout-score-v1",
                "pairs_schema": "saea-stage3-rollout-pairs-v2",
                "run_id": run_id,
                "attempt_id": attempt_id,
                "rollout_run_id": run_id,
                "rows": rows,
                "pairs": pairs,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / f"{run_id}.outputs.jsonl").write_text(
        "\n".join(json.dumps(row) for row in sealed) + "\n", encoding="utf-8"
    )
    deltas_path = prepared / "authored.json"
    deltas_path.write_text(
        json.dumps(
            {
                "schema": "saea-stage3-authored-deltas-v2",
                "iteration": 1,
                "facet_rule": "source-intent",
                "rows": [
                    {
                        "value_id": "delta:1:aaa",
                        "content": "CURRENT STATEMENT ONE",
                        "associated_facet_ids": ["alarm_set"],
                        "node_target": "solver",
                        "source_sample_ids": ["row-a"],
                        "provenance_refs": ["advantage:RUN:row-a:0:1:0"],
                        "task_target": "solver:slot-contract:alarm_set",
                        "prior_score": 0.5,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def pin(path: Path) -> dict:
        return {
            "relpath": str(path.relative_to(data_root)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    groups_document = {
        "schema": "saea-stage3-gepa-groups-v1",
        "k": 1,
        "rank_metric": "group-mean",
        "scenarios": ["alarm"],
        "excluded_scenarios": [],
        "rollout_run_id": run_id,
        "rollout_attempt_id": attempt_id,
        "pairs": pin(pairs_path),
        "deltas": {**pin(deltas_path), "iteration": 1},
        "groups": [
            {
                "group_id": "gepa:alarm:solver",
                "scenario": "alarm",
                "node": "solver",
                "carrier_sample_id": "row-a",
                "carrier_from": "group",
                "worst_sample_ids": ["row-a"],
                "best_sample_ids": ["row-b"],
                "row_sample_ids": ["row-a", "row-b"],
                "row_count": 2,
                "disagreement_mean": 0.75,
                "gold_intent_ids": ["alarm_set"],
                "current_delta_value_ids": ["delta:1:aaa"],
            }
        ],
    }
    groups_path = prepared / "gepa-groups-v1.json"
    groups_path.write_text(json.dumps(groups_document), encoding="utf-8")

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.slurp.load_slurp_train_construction_rows",
        lambda lock, root, ids: {
            sample_id: {
                "scenario": "alarm",
                "action": "set",
                "entities": [("time", "seven")],
            }
            for sample_id in ids
        },
    )

    values = {
        "arm": STAGE3_GEPA_ARM,
        "policy": STAGE3_GEPA_PROGRAM_ID,
        "carrier_lock_key": "slurp",
        "phase_material": {
            STAGE3_GEPA_PHASE_NAME: {
                "instruction_template": STAGE3_GEPA_TEMPLATE_RELPATH
            }
        },
        "gepa_groups": {
            "relpath": str(groups_path.relative_to(data_root)),
            "sha256": hashlib.sha256(groups_path.read_bytes()).hexdigest(),
            "rollout_run_id": run_id,
            "rollout_attempt_id": attempt_id,
        },
    }

    class _Sample:
        def __init__(self, sample_id):
            self.sample_id = sample_id

    return {
        "values": values,
        "data_root": data_root,
        "samples": [_Sample("row-a")],
        "groups_path": groups_path,
        "pairs_path": pairs_path,
    }


def test_the_material_renders_one_contact_per_group_and_binds_every_group_row(gepa_fixture):
    material = build_gepa_material(
        gepa_fixture["values"],
        lock={},
        data_root=gepa_fixture["data_root"],
        repo_root=REPO_ROOT,
        samples=gepa_fixture["samples"],
    )
    assert len(material.contacts) == 1
    contact = material.contacts[0]
    assert contact.group_id == gepa_group_id("alarm", "solver")
    assert contact.sample_id == "row-a"
    assert contact.construction_target_ids == ("row-a", "row-b")
    # The client binds the UNION and the request narrows it.
    assert [entry["sample_id"] for entry in material.bound_targets] == ["row-a", "row-b"]
    assert set(contact.construction_target_ids) <= {
        entry["sample_id"] for entry in material.bound_targets
    }
    instruction = contact.instruction
    assert "CURRENT STATEMENT ONE" in instruction
    assert instruction.count("--- ROW") == 2
    assert "WORSE OUTCOME" in instruction and "BETTER OUTCOME" in instruction
    assert contact.prompt_sha256 == _digest(instruction)


def test_no_receipt_of_the_material_ever_carries_rendered_text(gepa_fixture):
    material = build_gepa_material(
        gepa_fixture["values"],
        lock={},
        data_root=gepa_fixture["data_root"],
        repo_root=REPO_ROOT,
        samples=gepa_fixture["samples"],
    )
    blob = json.dumps(material.as_json())
    assert "CURRENT STATEMENT ONE" not in blob
    assert "DELIVERED TEXT" not in blob
    assert "seven" not in blob
    contact_json = material.contacts[0].as_json()
    assert contact_json["schema"] == GEPA_CONTACT_SCHEMA
    assert contact_json["row_count"] == 2
    assert contact_json["current_delta_value_ids"] == ["delta:1:aaa"]
    assert contact_json["prompt_characters"] > 0


def test_a_moved_pin_or_a_custody_drift_is_a_refusal_not_a_different_prompt(gepa_fixture):
    values = dict(gepa_fixture["values"])
    values["gepa_groups"] = {**values["gepa_groups"], "sha256": "0" * 64}
    with pytest.raises(Stage3GepaMaterialError):
        build_gepa_material(
            values,
            lock={},
            data_root=gepa_fixture["data_root"],
            repo_root=REPO_ROOT,
            samples=gepa_fixture["samples"],
        )
    # A sealed sample that no longer renders to the pinned digest.
    document = json.loads(gepa_fixture["pairs_path"].read_text(encoding="utf-8"))
    document["rows"][0]["best"]["response_text_sha256"] = "1" * 64
    gepa_fixture["pairs_path"].write_text(json.dumps(document), encoding="utf-8")
    groups = json.loads(gepa_fixture["groups_path"].read_text(encoding="utf-8"))
    groups["pairs"]["sha256"] = hashlib.sha256(
        gepa_fixture["pairs_path"].read_bytes()
    ).hexdigest()
    gepa_fixture["groups_path"].write_text(json.dumps(groups), encoding="utf-8")
    values = dict(gepa_fixture["values"])
    values["gepa_groups"] = {
        **values["gepa_groups"],
        "sha256": hashlib.sha256(gepa_fixture["groups_path"].read_bytes()).hexdigest(),
    }
    # The custody check is ADV-1's own, reused unchanged, so it raises the
    # SHARED parent error. Stage3GepaMaterialError subclasses it precisely so
    # that core.flight.runtime's single except clause covers both arms.
    assert issubclass(Stage3GepaMaterialError, Stage3AdvantageMaterialError)
    with pytest.raises(Stage3AdvantageMaterialError):
        build_gepa_material(
            values,
            lock={},
            data_root=gepa_fixture["data_root"],
            repo_root=REPO_ROOT,
            samples=gepa_fixture["samples"],
        )


def test_a_flown_row_that_carries_no_group_is_refused(gepa_fixture):
    class _Sample:
        sample_id = "row-not-a-carrier"

    with pytest.raises(Stage3GepaMaterialError):
        build_gepa_material(
            gepa_fixture["values"],
            lock={},
            data_root=gepa_fixture["data_root"],
            repo_root=REPO_ROOT,
            samples=[_Sample()],
        )


def test_the_resolver_dispatches_on_the_program_not_on_the_arm(gepa_fixture, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import runtime as rt

    called = {}

    def fake_gepa(values, *, lock, data_root, repo_root, samples):
        called["gepa"] = True
        return "GEPA"

    def fake_advantage(values, *, lock, data_root, repo_root, samples):
        called["advantage"] = True
        return "ADVANTAGE"

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.stage3_gepa_material.build_gepa_material",
        fake_gepa,
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.stage3_advantage_material."
        "build_advantage_material",
        fake_advantage,
    )
    values = dict(gepa_fixture["values"])
    assert (
        rt._default_construction_material(
            values,
            lock={},
            data_root=gepa_fixture["data_root"],
            repo_root=REPO_ROOT,
            samples=gepa_fixture["samples"],
        )
        == "GEPA"
    )
    assert called == {"gepa": True}

    called.clear()
    values["policy"] = "phase-stage3-advantage-v2"
    assert (
        rt._default_construction_material(
            values,
            lock={},
            data_root=gepa_fixture["data_root"],
            repo_root=REPO_ROOT,
            samples=gepa_fixture["samples"],
        )
        == "ADVANTAGE"
    )
    assert called == {"advantage": True}


# --------------------------------------------------------------------------- 6
# Curation and the twin.


def _groups_by_id():
    return {
        "gepa:alarm:solver": {
            "group_id": "gepa:alarm:solver",
            "scenario": "alarm",
            "node": "solver",
            "row_sample_ids": ["row-a", "row-b"],
            "disagreement_mean": 0.75,
        }
    }


def test_curation_keys_a_row_to_its_group_and_carries_the_group_mass():
    rows, counts = CURATOR.build_gepa_candidate_rows(
        proposal_outputs=[
            {"group_id": "gepa:alarm:solver", "response_text": _block(statement="keep it short")}
        ],
        groups_by_id=_groups_by_id(),
        run_id="GEPA-RUN-V1",
        iteration=2,
        facet_rule="source-intent",
        gold_intents={"row-a": "alarm_set", "row-b": "alarm_remove"},
        legal_intents=frozenset({"alarm_set", "alarm_remove"}),
    )
    assert counts["legal"] == 1 and counts["blocks_legal"] == 1
    (row,) = rows
    assert row["node_target"] == "solver"
    assert row["task_target"] == "solver:slot-contract:alarm_set"
    assert row["source_sample_ids"] == ["row-a", "row-b"]
    assert row["provenance_refs"] == ["gepa:GEPA-RUN-V1:alarm:solver:0"]
    assert row["prior_score"] == pytest.approx(0.75)
    assert row["value_id"].startswith("delta:2:")
    # source-intent: both source rows' gold intents, TARGET already among them
    assert row["associated_facet_ids"] == ["alarm_set", "alarm_remove"]


def test_curation_drops_a_wrong_node_block_and_counts_it():
    rows, counts = CURATOR.build_gepa_candidate_rows(
        proposal_outputs=[
            {"group_id": "gepa:alarm:solver", "response_text": _block(node="planner")}
        ],
        groups_by_id=_groups_by_id(),
        run_id="GEPA-RUN-V1",
        iteration=2,
        facet_rule="source-intent",
        gold_intents={"row-a": "alarm_set"},
        legal_intents=frozenset({"alarm_set"}),
    )
    assert rows == []
    assert counts["blocks_wrong_node"] == 1
    assert counts["illegal"] == 1


def test_curation_drops_an_unmatched_group_and_an_unroutable_statement():
    rows, counts = CURATOR.build_gepa_candidate_rows(
        proposal_outputs=[{"group_id": "gepa:nowhere:solver", "response_text": _block()}],
        groups_by_id=_groups_by_id(),
        run_id="R",
        iteration=2,
        facet_rule="source-intent",
        gold_intents={},
        legal_intents=frozenset(),
    )
    assert rows == [] and counts["unmatched_group"] == 1
    rows, counts = CURATOR.build_gepa_candidate_rows(
        proposal_outputs=[{"group_id": "gepa:alarm:solver", "response_text": _block()}],
        groups_by_id=_groups_by_id(),
        run_id="R",
        iteration=2,
        facet_rule="source-intent",
        gold_intents={},
        legal_intents=frozenset(),
    )
    assert rows == [] and counts["blocks_no_facet"] == 1


def test_a_verbatim_repeat_of_a_predecessor_row_is_a_REVISION_not_a_new_row():
    predecessor = [
        {
            "value_id": "delta:1:aaa",
            "content": "keep it short",
            "associated_facet_ids": ["alarm_set"],
            "node_target": "solver",
            "source_sample_ids": ["row-z"],
            "provenance_refs": ["advantage:R:row-z:0:1:0"],
            "task_target": "solver:slot-contract:alarm_set",
            "prior_score": 0.5,
        }
    ]
    candidates, _ = CURATOR.build_gepa_candidate_rows(
        proposal_outputs=[
            {"group_id": "gepa:alarm:solver", "response_text": _block(statement="keep it short")}
        ],
        groups_by_id=_groups_by_id(),
        run_id="GEPA-RUN-V1",
        iteration=2,
        facet_rule="source-intent",
        gold_intents={"row-a": "alarm_set", "row-b": "alarm_remove"},
        legal_intents=frozenset({"alarm_set", "alarm_remove"}),
    )
    survivors, counts = CURATOR.BASE.curate(
        predecessor_rows=predecessor,
        candidate_rows=candidates,
        merge_facets=True,
    )
    assert len(survivors) == 1
    assert counts["exact_duplicate"] == 1 and counts["new_accepted"] == 0
    assert survivors[0]["value_id"] == "delta:1:aaa"
    assert "gepa:GEPA-RUN-V1:alarm:solver:0" in survivors[0]["provenance_refs"]
    assert survivors[0]["associated_facet_ids"] == ["alarm_set", "alarm_remove"]


def test_the_existing_twin_builder_holds_its_two_invariants_on_a_gepa_document():
    rows = []
    for index, node in enumerate(
        ("solver", "solver", "reviewer", "perception", "perception")
    ):
        target = f"target_{index}"
        rows.append(
            {
                "value_id": f"delta:2:{index:012d}",
                "content": f"statement number {index}",
                "associated_facet_ids": [target],
                "node_target": node,
                "source_sample_ids": ["row-a", "row-b"],
                "provenance_refs": [f"gepa:R:alarm:{node}:{index}"],
                "task_target": f"{node}:slot-contract:{target}",
                "prior_score": 0.5,
            }
        )
    document = {"schema": "saea-stage3-authored-deltas-v2", "iteration": 2, "rows": rows}
    twin = TWIN.build_twin_document(document, seed=20260924)
    assert TWIN.authored_token_count(twin) == TWIN.authored_token_count(document)
    assert TWIN.facet_count_multiset(twin) == TWIN.facet_count_multiset(document)
    assert [row["content"] for row in twin["rows"]] == [row["content"] for row in rows]
