"""Model-free construction-only Audio2Tool task-information audit tests."""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_construction_task_information_audit import (
    A2tConstructionTaskInformationError,
    audit_construction_task_information,
)
from speech_aware_evidence_acquisition.rails.action_family_contracts import (
    ActionContract,
    ActionFamily,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (
    A2tKbRow,
    TIERS,
)


def _contract(
    tool_name: str,
    family_tag: str,
    *,
    ordered_keys: tuple[str, ...] = (),
    legal_skeletons: tuple[tuple[str, ...], ...] = ((),),
    required_keys: tuple[str, ...] = (),
    optional_keys: tuple[str, ...] = (),
    conditional_keys: tuple[str, ...] = (),
    types: tuple[tuple[str, str], ...] = (),
    default_declared: bool = False,
) -> ActionContract:
    return ActionContract(
        contract_id=f"contract-{tool_name}",
        tool_name=tool_name,
        family_tag=family_tag,
        operation=f"Perform the {tool_name} operation.",
        ordered_keys=ordered_keys,
        legal_key_skeletons=legal_skeletons,
        required_keys=required_keys,
        optional_keys=optional_keys,
        conditional_keys=conditional_keys,
        forbidden_keys=(),
        types=types,
        defaults=(
            "deviceId defaults to the active device."
            if default_declared
            else "No public default is declared."
        ),
        omission_rules=(
            "Never omit a required key.",
            "Omit an optional key when it is not bound.",
        ),
        constraints="No public constraint is declared.",
        canonicalization_rules=("boolean", "null"),
    )


def _family(tag: str, label: str, *tool_names: str) -> ActionFamily:
    return ActionFamily(
        tag=tag,
        label=label,
        tool_names=tuple(sorted(tool_names)),
        bundle_sha256="0" * 64,
        bundle_utf8_bytes=1,
    )


def _row(
    index: int,
    tier: str,
    tool_name: str,
    arg_signature: tuple[str, ...],
    *,
    extra_call_names: tuple[str, ...] = (),
) -> A2tKbRow:
    pairs = tuple((key, f'"PRIVATE VALUE {key}"') for key in arg_signature)
    return A2tKbRow(
        unit_id=f"{tier}:{index:06d}",
        tier=tier,
        query_idx=index,
        text=f"PRIVATE CONSTRUCTION UTTERANCE {index}",
        domain="private",
        category="private",
        tool_id=index,
        tool_name=tool_name,
        arg_signature=arg_signature,
        arg_pairs=pairs,
        call_render="PRIVATE CONCRETE CALL",
        extra_call_names=extra_call_names,
        call_count=1 + len(extra_call_names),
        sample_ids=(f"{tier}:{index:06d}",),
        item_ids=(index,),
        media_relpath_by_sample_id={},
        speaker_ids=("PRIVATE SPEAKER",),
    )


@pytest.fixture
def metadata() -> tuple[tuple[ActionContract, ...], tuple[ActionFamily, ...]]:
    contracts = (
        _contract(
            "playMusic",
            "media-playback",
            ordered_keys=("track", "deviceId"),
            legal_skeletons=(("track",), ("track", "deviceId")),
            required_keys=("track",),
            optional_keys=("deviceId",),
            types=(("track", "String"), ("deviceId", "String")),
            default_declared=True,
        ),
        _contract("stopMusic", "media-playback"),
        _contract(
            "setLight",
            "smart-home-lighting",
            ordered_keys=("deviceId", "state", "scene"),
            legal_skeletons=(
                ("deviceId",),
                ("deviceId", "state"),
                ("deviceId", "scene"),
            ),
            required_keys=("deviceId",),
            optional_keys=("state",),
            conditional_keys=("scene",),
            types=(
                ("deviceId", "String"),
                ("state", "Boolean"),
                ("scene", "String|null"),
            ),
        ),
        _contract("getLockStatus", "smart-home-lighting"),
    )
    families = (
        _family("media-playback", "Media / Playback", "playMusic", "stopMusic"),
        _family(
            "smart-home-lighting",
            "Smart Home / Lighting",
            "getLockStatus",
            "setLight",
        ),
    )
    return contracts, families


@pytest.fixture
def rows() -> tuple[A2tKbRow, ...]:
    return (
        _row(1, "tier1_direct", "playMusic", ("track",)),
        _row(
            2,
            "tier3_multi_intent",
            "playMusic",
            ("track",),
            extra_call_names=("stopMusic", "setLight"),
        ),
        _row(
            3,
            "tier6_correction",
            "setLight",
            ("deviceId", "state"),
            extra_call_names=("setLight",),
        ),
        _row(4, "tier7_multiturn", "stopMusic", ()),
        _row(5, "tier8_intent_blending", "setLight", ("deviceId",)),
    )


def test_reports_tier_tool_family_and_call_shape_distributions(
    rows: tuple[A2tKbRow, ...],
    metadata: tuple[tuple[ActionContract, ...], tuple[ActionFamily, ...]],
) -> None:
    contracts, families = metadata

    result = audit_construction_task_information(
        construction_rows=rows,
        contracts=contracts,
        families=families,
        long_tail_max_unit_support=2,
        top_k=(1, 2, 3, 4),
    )
    report = result.report

    assert report["population"] == {
        "construction_unit_count": 5,
        "registry_tool_count": 4,
        "family_count": 2,
        "call_occurrence_count": 8,
    }
    tiers = report["tiers"]
    assert tiers["counts"]["tier3_multi_intent"] == 1
    assert tiers["counts"]["tier2_parametric"] == 0
    assert tiers["shares"]["tier7_multiturn"] == pytest.approx(0.2)
    calls = report["call_structure"]
    assert calls["calls_per_unit"] == {"1": 3, "2": 1, "3": 1}
    assert calls["multi_call_unit_count"] == 2
    assert calls["multi_call_rate"] == pytest.approx(0.4)
    assert calls["distinct_tools_per_unit"] == {"1": 4, "3": 1}
    assert calls["distinct_families_per_unit"] == {"1": 4, "2": 1}

    tools = report["tool_support"]
    assert tools["unit_support_by_tool"] == {
        "getLockStatus": 0,
        "playMusic": 2,
        "setLight": 3,
        "stopMusic": 2,
    }
    assert tools["call_occurrences_by_tool"] == {
        "getLockStatus": 0,
        "playMusic": 2,
        "setLight": 4,
        "stopMusic": 2,
    }
    assert tools["unit_support_distribution"] == {"0": 1, "2": 2, "3": 1}
    assert tools["long_tail_tools"] == ["playMusic", "stopMusic"]
    assert tools["missing_registry_tools"] == ["getLockStatus"]

    family = report["family_support"]
    assert family["call_occurrences_by_family"] == {
        "media-playback": 4,
        "smart-home-lighting": 4,
    }
    assert family["call_occurrence_shares"] == {
        "media-playback": pytest.approx(0.5),
        "smart-home-lighting": pytest.approx(0.5),
    }


def test_reports_primary_skeletons_contract_burdens_and_cooccurrence(
    rows: tuple[A2tKbRow, ...],
    metadata: tuple[tuple[ActionContract, ...], tuple[ActionFamily, ...]],
) -> None:
    contracts, families = metadata

    report = audit_construction_task_information(
        construction_rows=rows,
        contracts=contracts,
        families=families,
        long_tail_max_unit_support=2,
    ).report

    skeletons = report["argument_structure"]
    assert skeletons["primary_argument_count_per_unit"] == {"0": 1, "1": 3, "2": 1}
    assert skeletons["argument_bearing_primary_unit_count"] == 4
    assert skeletons["no_argument_primary_unit_count"] == 1
    assert skeletons["key_skeleton_frequency"] == [
        {
            "tool_name": "playMusic",
            "keys": ["track"],
            "primary_unit_count": 2,
            "primary_unit_share": pytest.approx(0.4),
        },
        {
            "tool_name": "setLight",
            "keys": ["deviceId"],
            "primary_unit_count": 1,
            "primary_unit_share": pytest.approx(0.2),
        },
        {
            "tool_name": "setLight",
            "keys": ["deviceId", "state"],
            "primary_unit_count": 1,
            "primary_unit_share": pytest.approx(0.2),
        },
        {
            "tool_name": "stopMusic",
            "keys": [],
            "primary_unit_count": 1,
            "primary_unit_share": pytest.approx(0.2),
        },
    ]
    assert skeletons["skeleton_support"][0] == {
        "keys": ["track"],
        "primary_unit_count": 2,
        "supporting_tool_count": 1,
        "supporting_tools": ["playMusic"],
    }
    assert skeletons["extra_call_argument_structure_available"] is False

    burdens = report["contract_burdens"]
    assert burdens["tools_permitting_no_argument_call"] == 2
    assert burdens["tools_with_declared_defaults"] == 1
    assert burdens["tools_with_optional_keys"] == 2
    assert burdens["tools_with_conditional_keys"] == 1
    assert burdens["tools_with_multiple_legal_skeletons"] == 2
    assert burdens["typed_key_rule_count"] == 5
    assert burdens["type_rule_frequency"] == {
        "Boolean": 1,
        "String": 3,
        "String|null": 1,
    }

    edges = report["cooccurrence"]
    assert edges["tool_edges"] == [
        {
            "left": "playMusic",
            "right": "setLight",
            "unit_count": 1,
            "unit_share": pytest.approx(0.2),
        },
        {
            "left": "playMusic",
            "right": "stopMusic",
            "unit_count": 1,
            "unit_share": pytest.approx(0.2),
        },
        {
            "left": "setLight",
            "right": "stopMusic",
            "unit_count": 1,
            "unit_share": pytest.approx(0.2),
        },
    ]
    assert edges["family_edges"] == [
        {
            "left": "media-playback",
            "right": "smart-home-lighting",
            "unit_count": 1,
            "unit_share": pytest.approx(0.2),
        }
    ]


def test_reports_entropy_top_k_mass_and_no_safe_prior_pruning_claim(
    rows: tuple[A2tKbRow, ...],
    metadata: tuple[tuple[ActionContract, ...], tuple[ActionFamily, ...]],
) -> None:
    contracts, families = metadata

    prior = audit_construction_task_information(
        construction_rows=rows,
        contracts=contracts,
        families=families,
        top_k=(1, 2, 3, 4),
    ).report["raw_tool_prior"]

    assert prior["entropy_bits"] == pytest.approx(1.5)
    assert prior["effective_label_count"] == pytest.approx(2**1.5)
    assert prior["normalized_entropy"] == pytest.approx(0.75)
    assert prior["ranked_tools"] == [
        {"rank": 1, "tool_name": "setLight", "call_occurrences": 4, "prior_mass": 0.5},
        {
            "rank": 2,
            "tool_name": "playMusic",
            "call_occurrences": 2,
            "prior_mass": 0.25,
        },
        {
            "rank": 3,
            "tool_name": "stopMusic",
            "call_occurrences": 2,
            "prior_mass": 0.25,
        },
        {
            "rank": 4,
            "tool_name": "getLockStatus",
            "call_occurrences": 0,
            "prior_mass": 0.0,
        },
    ]
    assert prior["top_k_mass"] == {"1": 0.5, "2": 0.75, "3": 1.0, "4": 1.0}
    assert prior["minimum_k_for_mass"] == {
        "0.50": 1,
        "0.80": 3,
        "0.90": 3,
        "0.95": 3,
        "0.99": 3,
        "1.00": 3,
    }
    assert prior["safe_registry_label_reduction_supported"] is False
    assert "cannot safely exclude" in prior["interpretation"]


def test_maps_each_requested_task_information_need(
    rows: tuple[A2tKbRow, ...],
    metadata: tuple[tuple[ActionContract, ...], tuple[ActionFamily, ...]],
) -> None:
    contracts, families = metadata

    needs = audit_construction_task_information(
        construction_rows=rows,
        contracts=contracts,
        families=families,
    ).report["task_information_needs"]

    assert set(needs) == {
        "tool_discrimination",
        "multiplicity_and_order",
        "key_skeleton_selection",
        "value_binding",
        "default_and_omission",
        "tier_conditioned_composition",
    }
    assert needs["tool_discrimination"]["registry_labels"] == 4
    assert needs["multiplicity_and_order"]["multi_call_units"] == 2
    assert needs["key_skeleton_selection"]["observed_primary_skeletons"] == 4
    assert needs["value_binding"]["typed_key_rules"] == 5
    assert (
        needs["value_binding"]["concrete_argument_values_structurally_validated"]
        is True
    )
    assert (
        needs["value_binding"]["concrete_argument_values_used_as_analysis_features"]
        is False
    )
    assert needs["default_and_omission"]["tools_with_declared_defaults"] == 1
    complex_tiers = needs["tier_conditioned_composition"]
    assert complex_tiers["tier3_multi_intent"]["unit_count"] == 1
    assert complex_tiers["tier6_correction"]["unit_count"] == 1
    assert complex_tiers["tier7_multiturn"]["unit_count"] == 1
    assert complex_tiers["tier8_intent_blending"]["unit_count"] == 1


def test_canonical_json_is_order_independent_and_excludes_private_content(
    rows: tuple[A2tKbRow, ...],
    metadata: tuple[tuple[ActionContract, ...], tuple[ActionFamily, ...]],
) -> None:
    contracts, families = metadata

    first = audit_construction_task_information(
        construction_rows=rows,
        contracts=contracts,
        families=families,
    )
    second = audit_construction_task_information(
        construction_rows=tuple(reversed(rows)),
        contracts=tuple(reversed(contracts)),
        families=tuple(reversed(families)),
    )

    assert first.canonical_json == second.canonical_json
    assert json.loads(first.canonical_json) == first.report
    assert first.canonical_json.isascii()
    for private_value in (
        "PRIVATE CONSTRUCTION UTTERANCE",
        "PRIVATE VALUE",
        "PRIVATE CONCRETE CALL",
        "PRIVATE SPEAKER",
    ):
        assert private_value not in first.canonical_json
    assert first.report["input_boundary"] == {
        "construction_rows_only": True,
        "canonical_contract_and_family_metadata_only": True,
        "evaluation_or_test_rows_consumed": 0,
        "model_outputs_consumed": 0,
        "model_contacts": 0,
        "scorer_contacts": 0,
        "network_contacts": 0,
        "construction_text_or_argument_values_emitted": False,
    }


def test_accepts_sorted_row_skeleton_when_contract_uses_public_argument_order() -> None:
    contract = _contract(
        "playMusic",
        "media-playback",
        ordered_keys=("track", "deviceId"),
        legal_skeletons=(("track", "deviceId"),),
        required_keys=("track", "deviceId"),
        types=(("track", "String"), ("deviceId", "String")),
    )
    family = _family("media-playback", "Media / Playback", "playMusic")
    row = _row(
        1,
        "tier1_direct",
        "playMusic",
        ("deviceId", "track"),
    )

    result = audit_construction_task_information(
        construction_rows=(row,),
        contracts=(contract,),
        families=(family,),
    )

    structure = result.report["argument_structure"]
    assert structure["key_skeleton_frequency"][0]["keys"] == [
        "track",
        "deviceId",
    ]
    assert structure["skeleton_support"][0]["keys"] == ["track", "deviceId"]
    assert structure["legal_skeleton_support_by_tool"] == [
        {
            "tool_name": "playMusic",
            "keys": ["track", "deviceId"],
            "primary_unit_count": 1,
            "observed": True,
        }
    ]
    assert structure["observed_legal_skeleton_count"] == 1
    assert structure["unobserved_legal_skeleton_count"] == 0


def test_accepts_default_backed_empty_skeleton_with_registry_required_keys() -> None:
    contract = _contract(
        "activateRoutine",
        "smart-home-routines",
        ordered_keys=("routineId",),
        legal_skeletons=((), ("routineId",)),
        required_keys=("routineId",),
        types=(("routineId", "String"),),
        default_declared=True,
    )
    family = _family(
        "smart-home-routines",
        "Smart Home / Routines",
        "activateRoutine",
    )
    row = _row(1, "tier1_direct", "activateRoutine", ())

    result = audit_construction_task_information(
        construction_rows=(row,),
        contracts=(contract,),
        families=(family,),
    )

    assert result.report["argument_structure"]["no_argument_primary_unit_count"] == 1
    assert result.report["contract_burdens"]["tools_permitting_no_argument_call"] == 1


def test_quarantines_syntax_incompatible_construction_skeleton_from_support() -> None:
    contract = _contract(
        "startCleaning",
        "smart-home-cleaning",
        ordered_keys=("deviceId",),
        legal_skeletons=(("deviceId",),),
        required_keys=("deviceId",),
        types=(("deviceId", "String"),),
    )
    family = _family(
        "smart-home-cleaning",
        "Smart Home / Cleaning",
        "startCleaning",
    )
    row = _row(
        1,
        "tier3_multi_intent",
        "startCleaning",
        ("deviceId", "zones:["),
    )

    result = audit_construction_task_information(
        construction_rows=(row,),
        contracts=(contract,),
        families=(family,),
    )
    structure = result.report["argument_structure"]

    assert structure["syntax_incompatible_primary_unit_count"] == 1
    assert structure["skeleton_eligible_primary_unit_count"] == 0
    assert structure["key_skeleton_frequency"] == []
    assert structure["primary_argument_count_per_unit"] == {"2": 1}
    assert "zones:[" not in result.canonical_json


def test_fails_closed_on_invalid_construction_rows(
    rows: tuple[A2tKbRow, ...],
    metadata: tuple[tuple[ActionContract, ...], tuple[ActionFamily, ...]],
) -> None:
    contracts, families = metadata
    valid = rows[0]
    cases = (
        (valid, valid, "duplicate unit"),
        (A2tKbRow(**{**valid.__dict__, "tool_name": "unknownTool"}), "unknown tool"),
        (
            A2tKbRow(
                **{
                    **valid.__dict__,
                    "extra_call_names": ("unknownTool",),
                    "call_count": 2,
                }
            ),
            "unknown tool",
        ),
        (A2tKbRow(**{**valid.__dict__, "call_count": 2}), "call_count"),
        (A2tKbRow(**{**valid.__dict__, "arg_pairs": ()}), "arg_signature"),
        (
            A2tKbRow(
                **{
                    **valid.__dict__,
                    "arg_signature": ("deviceId",),
                    "arg_pairs": (("deviceId", '"PRIVATE VALUE"'),),
                }
            ),
            "legal skeleton",
        ),
        (A2tKbRow(**{**valid.__dict__, "tier": "unknown_tier"}), "unknown tier"),
    )
    for case in cases:
        if len(case) == 3:
            bad_rows = case[:2]
            message = case[2]
        else:
            bad_rows = (case[0],)
            message = case[1]
        with pytest.raises(A2tConstructionTaskInformationError, match=message):
            audit_construction_task_information(
                construction_rows=bad_rows,
                contracts=contracts,
                families=families,
            )


def test_fails_closed_on_invalid_contract_or_family_metadata(
    rows: tuple[A2tKbRow, ...],
    metadata: tuple[tuple[ActionContract, ...], tuple[ActionFamily, ...]],
) -> None:
    contracts, families = metadata
    duplicate_contracts = contracts + (contracts[0],)
    with pytest.raises(A2tConstructionTaskInformationError, match="duplicate contract"):
        audit_construction_task_information(
            construction_rows=rows,
            contracts=duplicate_contracts,
            families=families,
        )

    missing_member = (
        ActionFamily(**{**families[0].__dict__, "tool_names": ("playMusic",)}),
        families[1],
    )
    with pytest.raises(A2tConstructionTaskInformationError, match="family membership"):
        audit_construction_task_information(
            construction_rows=rows,
            contracts=contracts,
            families=missing_member,
        )

    bad_skeleton = ActionContract(
        **{**contracts[0].__dict__, "legal_key_skeletons": (("ghost",),)}
    )
    with pytest.raises(A2tConstructionTaskInformationError, match="legal skeleton"):
        audit_construction_task_information(
            construction_rows=rows,
            contracts=(bad_skeleton, *contracts[1:]),
            families=families,
        )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"construction_rows": ()}, "at least one construction row"),
        ({"long_tail_max_unit_support": 0}, "long-tail"),
        ({"top_k": (0, 1)}, "top-k"),
        ({"tier_order": (*TIERS, TIERS[0])}, "tier order"),
    ),
)
def test_fails_closed_on_invalid_audit_controls(
    rows: tuple[A2tKbRow, ...],
    metadata: tuple[tuple[ActionContract, ...], tuple[ActionFamily, ...]],
    kwargs: dict[str, object],
    message: str,
) -> None:
    contracts, families = metadata
    arguments: dict[str, object] = {
        "construction_rows": rows,
        "contracts": contracts,
        "families": families,
    }
    arguments.update(kwargs)

    with pytest.raises(A2tConstructionTaskInformationError, match=message):
        audit_construction_task_information(**arguments)  # type: ignore[arg-type]
