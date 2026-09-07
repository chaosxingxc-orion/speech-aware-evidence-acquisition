"""``rails.proposer``: candidate artifacts, proposer prompts, and the gates.

Everything here is model-free. The "proposer" is a string in a test file;
what is under test is the identity rule (a candidate id that covers all seven
fields section 5 names), the strictness of the response contract, and every
form/decontamination gate a candidate must clear before a flight could touch
it.

The synthetic registry is 152 rows on purpose: the form caps this module
enforces are stated over the released registry's own shape (152 lines, plain
name sort), and a two-row fixture would let the line-count gate pass
vacuously.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.proposer import (
    DECONTAMINATION_NGRAM,
    MAX_DESCRIPTION_CHARS,
    NULL_REWRITE_GATE,
    REGISTRY_LINE_COUNT,
    TOKEN_HEADROOM,
    CandidateArtifact,
    ProposerError,
    candidate_bytes,
    candidate_id_for,
    candidate_text,
    derive_target_id,
    deterministic_candidate,
    null_rewrite_check,
    parse_proposer_response,
    placebo_candidate,
    prompt_sha256,
    proposer_instruction_version,
    proposer_candidate,
    render_placebo_instruction,
    render_proposer_instruction,
    rendered_artifact_sha256,
    validate_candidate_artifact,
    word_ngrams,
)

TARGET_TOOLS = ("tool000", "tool001")
TARGET_ID = "twin-pair-000-001"
BASELINE_TOKENS = 13_236  # the measured compact-registry volume, as a stand-in
PROMPT_SHA = "a" * 64


def registry_rows(count: int = REGISTRY_LINE_COUNT) -> list[dict[str, str]]:
    rows = []
    for index in range(count):
        name = f"tool{index:03d}"
        rows.append(
            {
                "tool_id": str(index),
                "domain": "smart_home" if index % 2 else "smart_car",
                "category": f"cat{index % 5}",
                "tool_name": name,
                "signature": f"{name}(deviceId: String)",
                "description": f"Handles case {index}.",
                "argument_defaults": "",
                "argument_constraints": "",
            }
        )
    return rows


def target_rows() -> list[dict[str, str]]:
    return [row for row in registry_rows() if row["tool_name"] in TARGET_TOOLS]


def incumbent() -> dict[str, str]:
    return {row["tool_name"]: row["description"] for row in target_rows()}


def exemplars() -> list[tuple[str, str, str]]:
    return [
        ("tier1_direct:000101", "switch the porch lamp on", "tool000(deviceId='porch')"),
        ("tier1_direct:000102", "kill the porch lamp", "tool000(deviceId='porch')"),
        ("tier2_slot:000201", "arm the alarm at home", "tool001(deviceId='panel')"),
    ]


def a_candidate(**overrides) -> CandidateArtifact:
    payload = {
        "cue": "one names a light, the other an alarm panel",
        "descriptions": {
            "tool000": "Switches a named lamp on or off.",
            "tool001": "Arms or disarms the household alarm panel.",
        },
        "target_id": TARGET_ID,
        "round": 1,
        "k": 0,
        "proposer_prompt_sha256": PROMPT_SHA,
        "exemplar_ids": ("tier1_direct:000101", "tier2_slot:000201"),
    }
    payload.update(overrides)
    cue = payload.pop("cue")
    descriptions = payload.pop("descriptions")
    return proposer_candidate(cue, descriptions, **payload)


def fixed_counter(value: int):
    return lambda _text: value


# ---------------------------------------------------------------------------
# Word n-grams (the one tokenizer every decontamination gate shares)
# ---------------------------------------------------------------------------


def test_word_ngrams_are_case_and_punctuation_insensitive():
    left = word_ngrams("Turn On The Kitchen Light, please now")
    right = word_ngrams("turn on the kitchen light please now")
    assert left == right
    assert ("turn", "on", "the", "kitchen", "light", "please") in left


def test_word_ngrams_of_short_text_is_empty():
    assert word_ngrams("only five words here now") == set()
    assert DECONTAMINATION_NGRAM == 6


# ---------------------------------------------------------------------------
# Candidate identity
# ---------------------------------------------------------------------------


def test_candidate_text_is_cue_then_name_sorted_descriptions():
    text = candidate_text({"b": "second", "a": "first"}, "the cue")
    assert text == "cue: the cue\na: first\nb: second"


def test_candidate_id_changes_with_every_identity_field():
    base = dict(
        text="cue: c\ntool000: x",
        proposer_prompt_sha256=PROMPT_SHA,
        exemplar_ids=("s1",),
        round=1,
        target_id=TARGET_ID,
        k=0,
        family="proposer",
    )
    baseline = candidate_id_for(**base)
    variations = [
        {"text": "cue: c\ntool000: y"},
        {"proposer_prompt_sha256": "b" * 64},
        {"exemplar_ids": ("s2",)},
        {"round": 2},
        {"target_id": "other"},
        {"k": 1},
        {"family": "placebo"},
    ]
    ids = {baseline}
    for variation in variations:
        ids.add(candidate_id_for(**{**base, **variation}))
    assert len(ids) == len(variations) + 1


def test_candidate_id_is_stable_across_calls():
    assert a_candidate().candidate_id == a_candidate().candidate_id


def test_validate_refuses_a_tampered_candidate_id():
    candidate = a_candidate()
    tampered = CandidateArtifact(
        candidate_id=candidate.candidate_id,
        family=candidate.family,
        target_id=candidate.target_id,
        round=candidate.round,
        k=candidate.k,
        descriptions={**candidate.descriptions, "tool000": "something else entirely"},
        cue=candidate.cue,
        proposer_prompt_sha256=candidate.proposer_prompt_sha256,
        exemplar_ids=candidate.exemplar_ids,
    )
    with pytest.raises(ProposerError, match="does not match"):
        tampered.validate()


def test_candidate_as_json_carries_the_schema_and_sorted_descriptions():
    document = a_candidate().as_json()
    assert document["schema"] == "saea-evolution-candidate-v1"
    assert list(document["descriptions"]) == ["tool000", "tool001"]
    assert json.dumps(document)  # JSON-safe


def test_candidate_bytes_measures_the_override_not_the_envelope():
    small = a_candidate(descriptions={"tool000": "Short.", "tool001": "Also short."})
    large = a_candidate(
        descriptions={
            "tool000": "A considerably longer replacement description here.",
            "tool001": "Another considerably longer replacement description.",
        }
    )
    assert candidate_bytes(small) < candidate_bytes(large)


def test_family_invariants_are_enforced():
    with pytest.raises(ProposerError, match="cue and its prompt"):
        CandidateArtifact(
            candidate_id=candidate_id_for(
                text=candidate_text({"tool000": "x"}, None),
                proposer_prompt_sha256=None,
                exemplar_ids=(),
                round=1,
                target_id=TARGET_ID,
                k=0,
                family="proposer",
            ),
            family="proposer",
            target_id=TARGET_ID,
            round=1,
            k=0,
            descriptions={"tool000": "x"},
            cue=None,
            proposer_prompt_sha256=None,
            exemplar_ids=(),
        ).validate()


# ---------------------------------------------------------------------------
# Proposer instruction
# ---------------------------------------------------------------------------


def test_proposer_instruction_bytes_are_deterministic():
    first = render_proposer_instruction(
        target_rows(), incumbent(), exemplars(), target_id=TARGET_ID, round=1, k=0
    )
    second = render_proposer_instruction(
        target_rows(), incumbent(), exemplars(), target_id=TARGET_ID, round=1, k=0
    )
    assert first == second
    assert first.endswith("\n")


def test_proposer_instruction_differs_per_slot_round_and_target():
    def render(**kwargs):
        arguments = {"target_id": TARGET_ID, "round": 1, "k": 0}
        arguments.update(kwargs)
        return render_proposer_instruction(
            target_rows(), incumbent(), exemplars(), **arguments
        )

    rendered = {render(), render(k=1), render(round=2), render(target_id="other")}
    assert len(rendered) == 4


def test_proposer_instruction_never_shows_a_sample_id():
    rendered = render_proposer_instruction(
        target_rows(), incumbent(), exemplars(), target_id=TARGET_ID, round=1, k=0
    )
    for sample_id, query_text, gold_call in exemplars():
        assert sample_id not in rendered
        assert query_text in rendered
        assert gold_call in rendered


def test_proposer_instruction_states_the_output_contract():
    rendered = render_proposer_instruction(
        target_rows(), incumbent(), exemplars(), target_id=TARGET_ID, round=1, k=0
    )
    assert '"cue"' in rendered
    assert '"descriptions"' in rendered
    assert f"at most {MAX_DESCRIPTION_CHARS} ASCII characters" in rendered
    # The pair's own registry columns are shown; nothing else is.
    assert "domain: smart_car" in rendered
    assert "tool002" not in rendered


def test_proposer_instruction_refuses_an_exemplar_for_a_foreign_tool():
    bad = [("tier1_direct:000103", "do a third thing", "tool099(deviceId='x')")]
    with pytest.raises(ProposerError, match="not one of this target"):
        render_proposer_instruction(
            target_rows(), incumbent(), bad, target_id=TARGET_ID, round=1, k=0
        )


def test_proposer_instruction_refuses_an_incumbent_that_is_not_the_target():
    with pytest.raises(ProposerError, match="exactly this target"):
        render_proposer_instruction(
            target_rows(),
            {"tool000": "only one of the two"},
            exemplars(),
            target_id=TARGET_ID,
            round=1,
            k=0,
        )


def test_proposer_instruction_refuses_duplicate_exemplar_ids():
    duplicated = exemplars() + [exemplars()[0]]
    with pytest.raises(ProposerError, match="repeat sample_id"):
        render_proposer_instruction(
            target_rows(), incumbent(), duplicated, target_id=TARGET_ID, round=1, k=0
        )


def test_placebo_instruction_shows_no_exemplar_and_asks_for_no_cue():
    rendered = render_placebo_instruction(
        target_rows(),
        incumbent(),
        target_id=TARGET_ID,
        round=1,
        k=4,
        target_lengths={"tool000": 40, "tool001": 44},
    )
    assert "carry no distinguishing cue" in rendered.lower()
    assert '"cue"' not in rendered
    assert "about 40 characters" in rendered
    for _sample_id, query_text, gold_call in exemplars():
        assert query_text not in rendered
        assert gold_call not in rendered
    assert rendered == render_placebo_instruction(
        target_rows(),
        incumbent(),
        target_id=TARGET_ID,
        round=1,
        k=4,
        target_lengths={"tool000": 40, "tool001": 44},
    )


def test_placebo_instruction_refuses_a_length_over_the_cap():
    with pytest.raises(ProposerError, match="character cap"):
        render_placebo_instruction(
            target_rows(),
            incumbent(),
            target_id=TARGET_ID,
            round=1,
            k=4,
            target_lengths={"tool000": MAX_DESCRIPTION_CHARS + 1, "tool001": 44},
        )


def test_prompt_sha256_is_the_digest_of_the_rendered_bytes():
    rendered = render_proposer_instruction(
        target_rows(), incumbent(), exemplars(), target_id=TARGET_ID, round=1, k=0
    )
    assert prompt_sha256(rendered) == hashlib.sha256(rendered.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Response parsing -- strict, and refusing
# ---------------------------------------------------------------------------


def test_parse_accepts_exactly_the_contracted_object():
    cue, descriptions = parse_proposer_response(
        '  {"cue": "lamp vs alarm", "descriptions": {"tool000": "A.", "tool001": "B."}}  ',
        expected_tools=TARGET_TOOLS,
    )
    assert cue == "lamp vs alarm"
    assert descriptions == {"tool000": "A.", "tool001": "B."}


@pytest.mark.parametrize(
    "response",
    [
        "not json at all",
        '```json\n{"cue": "c", "descriptions": {"tool000": "A.", "tool001": "B."}}\n```',
        'Here you go: {"cue": "c", "descriptions": {"tool000": "A.", "tool001": "B."}}',
        '{"descriptions": {"tool000": "A.", "tool001": "B."}}',
        '{"cue": "c", "descriptions": {"tool000": "A.", "tool001": "B."}, "note": "x"}',
        '{"cue": "", "descriptions": {"tool000": "A.", "tool001": "B."}}',
        '{"cue": "c", "descriptions": {"tool000": "A."}}',
        '{"cue": "c", "descriptions": {"tool000": "A.", "tool001": "B.", "tool002": "C."}}',
        '{"cue": "c", "descriptions": {"tool000": "A.", "tool001": 7}}',
        '{"cue": "c", "descriptions": {"tool000": "A.", "tool001": "  "}}',
        '["cue", "descriptions"]',
        "",
    ],
)
def test_parse_refuses_everything_that_is_not_the_contract(response):
    with pytest.raises(ProposerError):
        parse_proposer_response(response, expected_tools=TARGET_TOOLS)


# ---------------------------------------------------------------------------
# Deterministic control and placebo
# ---------------------------------------------------------------------------


def test_deterministic_candidate_appends_the_registry_columns():
    candidate = deterministic_candidate(
        registry_rows(), TARGET_TOOLS, round=1, k=3, target_id=TARGET_ID
    )
    assert candidate.family == "deterministic"
    assert candidate.cue is None
    assert candidate.proposer_prompt_sha256 is None
    assert candidate.exemplar_ids == ()
    assert candidate.descriptions["tool000"] == (
        "Handles case 0. (domain: smart_car; category: cat0)"
    )
    assert candidate.descriptions["tool001"] == (
        "Handles case 1. (domain: smart_home; category: cat1)"
    )
    candidate.validate()


def test_deterministic_candidate_derives_a_target_id_when_none_is_given():
    candidate = deterministic_candidate(registry_rows(), TARGET_TOOLS, round=1)
    assert candidate.target_id == derive_target_id(TARGET_TOOLS) == "tool000+tool001"
    assert candidate.k == 0


def test_deterministic_candidate_refuses_a_tool_outside_the_registry():
    with pytest.raises(ProposerError, match="not among the supplied registry rows"):
        deterministic_candidate(target_rows(), ("tool000", "tool099"), round=1)


def test_placebo_candidate_requires_the_no_cue_marker():
    descriptions = {"tool000": "Restated.", "tool001": "Also restated."}
    with pytest.raises(ProposerError, match="no_cue=True"):
        placebo_candidate(
            descriptions,
            target_id=TARGET_ID,
            round=1,
            k=4,
            proposer_prompt_sha256=PROMPT_SHA,
            no_cue=False,
        )
    candidate = placebo_candidate(
        descriptions,
        target_id=TARGET_ID,
        round=1,
        k=4,
        proposer_prompt_sha256=PROMPT_SHA,
    )
    assert candidate.family == "placebo"
    assert candidate.cue is None
    candidate.validate()


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def test_validator_accepts_a_clean_candidate_and_reports_the_overlap():
    report = validate_candidate_artifact(
        a_candidate(),
        registry_rows=registry_rows(),
        token_counter=fixed_counter(BASELINE_TOKENS + TOKEN_HEADROOM),
        compact_baseline_tokens=BASELINE_TOKENS,
        evaluation_query_texts=["a completely unrelated evaluation utterance here"],
        registry_text="",
        exemplar_texts=["switches a named lamp on or the porch"],
    )
    assert report.rendered_lines == REGISTRY_LINE_COUNT
    assert report.token_budget == BASELINE_TOKENS + TOKEN_HEADROOM
    assert report.max_description_chars == len(
        "Arms or disarms the household alarm panel."
    )
    # "switches a named lamp on or" is a 6-gram of both the description and the
    # exemplar text -- counted, never a gate.
    assert report.exemplar_overlap_count == 1
    assert report.exemplar_overlap_ngrams == ("switches a named lamp on or",)
    assert json.dumps(report.as_json())


def test_validator_refuses_non_ascii():
    candidate = a_candidate(
        descriptions={"tool000": "Switches a lamp — on or off.", "tool001": "Arms."}
    )
    with pytest.raises(ProposerError, match="non-ASCII"):
        validate_candidate_artifact(
            candidate,
            registry_rows=registry_rows(),
            token_counter=fixed_counter(BASELINE_TOKENS),
            compact_baseline_tokens=BASELINE_TOKENS,
        )


def test_validator_refuses_a_description_over_the_character_cap():
    candidate = a_candidate(
        descriptions={"tool000": "x" * (MAX_DESCRIPTION_CHARS + 1), "tool001": "Arms."}
    )
    with pytest.raises(ProposerError, match="over the 200-character cap"):
        validate_candidate_artifact(
            candidate,
            registry_rows=registry_rows(),
            token_counter=fixed_counter(BASELINE_TOKENS),
            compact_baseline_tokens=BASELINE_TOKENS,
        )


def test_validator_refuses_one_token_over_the_budget():
    candidate = a_candidate()
    validate_candidate_artifact(
        candidate,
        registry_rows=registry_rows(),
        token_counter=fixed_counter(BASELINE_TOKENS + TOKEN_HEADROOM),
        compact_baseline_tokens=BASELINE_TOKENS,
    )
    with pytest.raises(ProposerError, match="over the .* budget"):
        validate_candidate_artifact(
            candidate,
            registry_rows=registry_rows(),
            token_counter=fixed_counter(BASELINE_TOKENS + TOKEN_HEADROOM + 1),
            compact_baseline_tokens=BASELINE_TOKENS,
        )


@pytest.mark.parametrize(
    "description",
    [
        "See tier3_multi_intent:000412 for the pattern.",
        "Behaves like row 000412 in the corpus.",
    ],
)
def test_validator_refuses_a_sample_identifier(description):
    candidate = a_candidate(descriptions={"tool000": description, "tool001": "Arms."})
    with pytest.raises(ProposerError, match="sample identifier"):
        validate_candidate_artifact(
            candidate,
            registry_rows=registry_rows(),
            token_counter=fixed_counter(BASELINE_TOKENS),
            compact_baseline_tokens=BASELINE_TOKENS,
        )


EVALUATION_QUERY = "please turn on the kitchen light in the hallway"
LEAKED = "Use this to turn on the kitchen light in the hallway."


def test_validator_refuses_a_six_gram_shared_with_an_evaluation_query():
    candidate = a_candidate(descriptions={"tool000": LEAKED, "tool001": "Arms."})
    with pytest.raises(ProposerError, match="6-gram"):
        validate_candidate_artifact(
            candidate,
            registry_rows=registry_rows(),
            token_counter=fixed_counter(BASELINE_TOKENS),
            compact_baseline_tokens=BASELINE_TOKENS,
            evaluation_query_texts=[EVALUATION_QUERY],
        )


def test_validator_allows_the_same_six_gram_when_the_registry_carries_it():
    candidate = a_candidate(descriptions={"tool000": LEAKED, "tool001": "Arms."})
    report = validate_candidate_artifact(
        candidate,
        registry_rows=registry_rows(),
        token_counter=fixed_counter(BASELINE_TOKENS),
        compact_baseline_tokens=BASELINE_TOKENS,
        evaluation_query_texts=[EVALUATION_QUERY],
        registry_text="- tool000(deviceId: String): turn on the kitchen light in the hallway",
    )
    assert report.rendered_lines == REGISTRY_LINE_COUNT


def test_validator_refuses_an_override_for_a_tool_outside_the_registry():
    candidate = a_candidate(
        descriptions={"tool000": "Switches a lamp.", "toolZZZ": "Not a real tool."}
    )
    with pytest.raises(ProposerError, match="absent from the registry"):
        validate_candidate_artifact(
            candidate,
            registry_rows=registry_rows(),
            token_counter=fixed_counter(BASELINE_TOKENS),
            compact_baseline_tokens=BASELINE_TOKENS,
        )


def test_validator_refuses_a_registry_that_is_not_152_rows():
    with pytest.raises(ProposerError, match="not the expected 152"):
        validate_candidate_artifact(
            a_candidate(),
            registry_rows=registry_rows(count=151),
            token_counter=fixed_counter(BASELINE_TOKENS),
            compact_baseline_tokens=BASELINE_TOKENS,
        )


# ---------------------------------------------------------------------------
# The null-rewrite form gate (track E3e, 2026-09-07)
# ---------------------------------------------------------------------------


def test_rendered_artifact_sha256_is_the_digest_the_validator_measures():
    """One renderer, both sides of the gate. If this ever disagreed with
    ``validate_candidate_artifact`` the gate would be comparing two spellings
    rather than two artifacts."""

    candidate = a_candidate()
    measured = validate_candidate_artifact(
        candidate,
        registry_rows=registry_rows(),
        token_counter=fixed_counter(BASELINE_TOKENS),
        compact_baseline_tokens=BASELINE_TOKENS,
    )
    assert (
        rendered_artifact_sha256(
            candidate.descriptions, registry_rows=registry_rows()
        )
        == measured.rendered_sha256
    )


def test_a_candidate_that_repeats_the_incumbent_is_a_null_rewrite():
    incumbent_texts = incumbent()
    check = null_rewrite_check(
        a_candidate(descriptions=dict(incumbent_texts)),
        incumbent_texts,
        registry_rows=registry_rows(),
    )
    assert check.null_rewrite
    assert check.keys == tuple(sorted(TARGET_TOOLS))
    assert check.candidate_rendered_sha256 == check.incumbent_rendered_sha256
    assert check.reason.startswith(f"{NULL_REWRITE_GATE}:")
    assert check.as_json()["gate"] == NULL_REWRITE_GATE


def test_one_changed_character_is_no_longer_a_null_rewrite():
    incumbent_texts = incumbent()
    rewritten = dict(incumbent_texts)
    rewritten["tool000"] = rewritten["tool000"].replace(".", "!")
    check = null_rewrite_check(
        a_candidate(descriptions=rewritten), incumbent_texts, registry_rows=registry_rows()
    )
    assert not check.null_rewrite
    assert check.candidate_rendered_sha256 != check.incumbent_rendered_sha256


def test_the_gate_compares_only_the_keys_the_candidate_rewrote():
    """The incumbent mapping may cover the whole registry; a candidate that
    rewrote two tools is a null rewrite exactly when THOSE two are unchanged."""

    whole = {row["tool_name"]: row["description"] for row in registry_rows()}
    check = null_rewrite_check(
        a_candidate(descriptions={tool: whole[tool] for tool in TARGET_TOOLS}),
        whole,
        registry_rows=registry_rows(),
    )
    assert check.null_rewrite and check.keys == tuple(sorted(TARGET_TOOLS))


def test_the_gate_refuses_an_incumbent_that_does_not_cover_the_candidate():
    with pytest.raises(ProposerError, match="no entry for"):
        null_rewrite_check(
            a_candidate(), {"tool000": "only one side"}, registry_rows=registry_rows()
        )


# ---------------------------------------------------------------------------
# proposer-instruction-v2 is a SLURP-only bump (track E3e, 2026-09-07)
# ---------------------------------------------------------------------------


def test_a_blank_line_inside_the_json_costs_this_family_nothing():
    """The habit that cost EVO-S1 22 of 54 draws cannot cost EVO-A1 one.

    This family's output contract is strict JSON, and JSON treats a blank line
    as the insignificant whitespace it is -- so the between-blocks rule that
    ``proposer-instruction-v2`` adds to the SLURP instruction has no A2T
    counterpart to add, and this instruction stays v1.
    """

    spaced = json.dumps(
        {
            "cue": "one names a light, the other an alarm panel",
            "descriptions": {
                "tool000": "Switches a named lamp on or off.",
                "tool001": "Arms or disarms the household alarm panel.",
            },
        },
        indent=2,
    ).replace("\n", "\n\n")
    cue, descriptions = parse_proposer_response(spaced, expected_tools=TARGET_TOOLS)
    assert sorted(descriptions) == sorted(TARGET_TOOLS)
    assert cue
    assert proposer_instruction_version("a2t-descriptions") == "proposer-instruction-v1"
