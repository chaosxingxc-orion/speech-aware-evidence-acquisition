import hashlib

import pytest

from speech_aware_evidence_acquisition.rails.a2t_canonical_family_ground import (
    CanonicalContract,
)
from speech_aware_evidence_acquisition.rails.a2t_executable_semantic_cards import (
    ExecutableSemanticCardCorpus,
    TaskSemanticCard,
    ToolSemanticCard,
)
from speech_aware_evidence_acquisition.rails.a2t_select_fill_ground import (
    JointKnowledgeGround,
    ParameterKnowledgeGround,
    RoutingKnowledgeGround,
    SelectFillGroundError,
    build_parameter_knowledge_ground,
    build_joint_knowledge_ground,
    build_routing_knowledge_ground,
)


def _card(name: str, choose: str, *, example: str = "Example: use it") -> ToolSemanticCard:
    return ToolSemanticCard(
        tool_name=name,
        choose_semantics=choose,
        avoid_semantics=f"Avoid {name} for unrelated operations.",
        signature=f"{name}(mode: String)",
        constraints="mode: [one, two]",
        legal_argument_key_sets=(("mode",),),
        compatibility_rules=(),
        role_guidance=(f"role guidance for {name}",),
        examples=(example,),
        text=f"full card text for {name}",
    )


def _corpus() -> ExecutableSemanticCardCorpus:
    return ExecutableSemanticCardCorpus(
        text="corpus",
        sha256="0" * 64,
        tool_cards=(_card("alpha", "alpha operation"), _card("beta", "beta operation")),
        task_cards=(
            TaskSemanticCard("multi-call-ordering", "Multi-call guidance."),
            TaskSemanticCard("correction-resolution", "Correction guidance."),
            TaskSemanticCard("implicit-end-state-resolution", "Implicit guidance."),
            TaskSemanticCard("multiturn-carryover", "Multiturn guidance."),
            TaskSemanticCard("other", "Do not leak this unrelated task card."),
        ),
        report={},
    )


def _contracts() -> dict[str, CanonicalContract]:
    return {
        name: CanonicalContract(
            contract_id=f"contract-{name}",
            family_tag="synthetic-family",
            tool_name=name,
            operation=f"{name} operation",
            types=(("mode", "String"),),
            constraints="mode: [one, two]",
            legal_key_skeletons=(("mode",),),
            required_keys=("mode",),
            optional_keys=(),
            conditional_keys=(),
            forbidden_keys=(),
            ordered_keys=("mode",),
            defaults="mode defaults to one when the operation is explicit",
            omission_rules=("Do not invent an operation from its default.",),
            canonicalization_rules=("entity",),
        )
        for name in ("alpha", "beta")
    }


def _canonicalizers() -> dict[str, str]:
    return {"entity": "Copy entity text from speech without substitution."}


def _parameter_ground(*occurrences: str, byte_cap: int = 32_768):
    return build_parameter_knowledge_ground(
        _corpus(),
        occurrences,
        contracts_by_tool=_contracts(),
        canonicalizers=_canonicalizers(),
        byte_cap=byte_cap,
    )


def test_routing_ground_is_candidate_scoped_and_uses_selection_schema() -> None:
    packet = build_routing_knowledge_ground(_corpus(), ("beta", "alpha"))

    assert isinstance(packet, RoutingKnowledgeGround)
    assert packet.candidate_tool_names == ("beta", "alpha")
    assert "Exact tool: beta" in packet.text
    assert "alpha operation" in packet.text
    assert "full card text" not in packet.text
    assert "signature" not in packet.text.lower()
    assert "Multi-call guidance." in packet.text
    assert "Correction guidance." in packet.text
    assert "Implicit guidance." in packet.text
    assert "Multiturn guidance." in packet.text
    assert "Do not leak this unrelated" not in packet.text
    assert packet.text.isascii()
    assert packet.text_sha256 == hashlib.sha256(packet.text.encode("ascii")).hexdigest()
    schema = packet.response_format["json_schema"]["schema"]
    assert schema["minItems"] == 1
    assert schema["maxItems"] == 7
    assert schema["items"]["properties"]["name"]["enum"] == ["alpha", "beta"]


def test_parameter_ground_deduplicates_documents_but_preserves_occurrences() -> None:
    packet = _parameter_ground("beta", "alpha", "beta")

    assert isinstance(packet, ParameterKnowledgeGround)
    assert packet.selected_tool_occurrences == ("beta", "alpha", "beta")
    assert packet.selected_tool_names == ("beta", "alpha")
    assert packet.text.count("Exact tool: beta") == 1
    assert packet.text.count("Exact tool: alpha") == 1
    assert "mode: String" in packet.text
    assert "Required keys: mode" in packet.text
    assert "Declared defaults for omission semantics: mode defaults to one" in packet.text
    assert "Omission rules: Do not invent an operation from its default." in packet.text
    assert "Applicable canonicalizers: entity" in packet.text
    assert "entity: Copy entity text from speech without substitution." in packet.text
    assert "role guidance for beta" in packet.text
    assert "Example: use it" in packet.text
    assert "Correction guidance." in packet.text
    assert "Multiturn guidance." in packet.text
    assert "Do not leak this unrelated" not in packet.text
    schema = packet.response_format["json_schema"]["schema"]
    assert schema["minItems"] == schema["maxItems"] == 3
    assert len(schema["prefixItems"]) == 3
    beta_arguments = schema["prefixItems"][0]["oneOf"][0]["properties"][
        "arguments"
    ]
    assert beta_arguments["properties"]["mode"] == {
        "type": "string",
        "enum": ["one", "two"],
    }
    assert packet.report["selected_occurrence_count"] == 3
    assert packet.report["selected_tool_count"] == 2
    assert packet.report["selected_default_declaration_count"] == 2
    assert packet.report["selected_omission_rule_count"] == 2
    assert packet.report["selected_canonicalizer_count"] == 1


def test_parameter_ground_accepts_empty_selection() -> None:
    packet = _parameter_ground()
    assert packet.selected_tool_names == ()
    assert packet.selected_tool_occurrences == ()
    schema = packet.response_format["json_schema"]["schema"]
    assert schema["minItems"] == schema["maxItems"] == 0
    assert schema["prefixItems"] == []
    assert "items" not in schema


def test_joint_ground_exposes_the_same_routing_and_parameter_facts() -> None:
    packet = build_joint_knowledge_ground(
        _corpus(),
        ("beta", "alpha"),
        contracts_by_tool=_contracts(),
        canonicalizers=_canonicalizers(),
    )

    assert isinstance(packet, JointKnowledgeGround)
    assert packet.candidate_tool_names == ("beta", "alpha")
    assert "Choose: beta operation" in packet.text
    assert "Avoid beta for unrelated operations." in packet.text
    assert "Required keys: mode" in packet.text
    assert "Declared defaults for omission semantics: mode defaults to one" in packet.text
    assert "Omission rules: Do not invent an operation from its default." in packet.text
    assert "entity: Copy entity text from speech without substitution." in packet.text
    assert "Role guidance: role guidance for beta" in packet.text
    assert "Example: use it" in packet.text
    assert "full card text" not in packet.text
    schema = packet.response_format["json_schema"]["schema"]
    assert schema["minItems"] == 1
    assert schema["maxItems"] == 7
    assert {
        branch["properties"]["name"]["const"]
        for branch in schema["items"]["oneOf"]
    } == {"alpha", "beta"}
    assert packet.report["candidate_count"] == 2
    assert packet.report["answer_cardinality"] == {"minimum": 1, "maximum": 7}


@pytest.mark.parametrize(
    "builder, selection, message",
    [
        (build_routing_knowledge_ground, (), "candidate list"),
        (build_routing_knowledge_ground, ("alpha", "alpha"), "duplicate"),
        (build_routing_knowledge_ground, ("missing",), "unknown"),
    ],
)
def test_selection_validation_fails_closed(builder, selection, message: str) -> None:
    with pytest.raises(SelectFillGroundError, match=message):
        builder(_corpus(), selection)


@pytest.mark.parametrize(
    "selection, message",
    [
        (("missing",), "unknown"),
        (("alpha",) * 8, "at most 7"),
    ],
)
def test_parameter_selection_validation_fails_closed(selection, message: str) -> None:
    with pytest.raises(SelectFillGroundError, match=message):
        build_parameter_knowledge_ground(
            _corpus(),
            selection,
            contracts_by_tool=_contracts(),
            canonicalizers=_canonicalizers(),
        )


def test_parameter_contract_inputs_fail_closed() -> None:
    with pytest.raises(SelectFillGroundError, match="contract coverage"):
        build_parameter_knowledge_ground(
            _corpus(),
            ("alpha",),
            contracts_by_tool={"beta": _contracts()["beta"]},
            canonicalizers=_canonicalizers(),
        )
    with pytest.raises(SelectFillGroundError, match="canonicalizer coverage"):
        build_parameter_knowledge_ground(
            _corpus(),
            ("alpha",),
            contracts_by_tool=_contracts(),
            canonicalizers={},
        )


def test_byte_cap_and_non_ascii_fail_closed() -> None:
    with pytest.raises(SelectFillGroundError, match="byte cap"):
        build_routing_knowledge_ground(_corpus(), ("alpha",), byte_cap=1)
    bad = _corpus()
    cards = (_card("é", "bad"),)
    bad = ExecutableSemanticCardCorpus(
        text=bad.text, sha256=bad.sha256, tool_cards=cards, task_cards=bad.task_cards, report=bad.report
    )
    with pytest.raises(SelectFillGroundError, match="ASCII"):
        build_routing_knowledge_ground(bad, ("é",))
