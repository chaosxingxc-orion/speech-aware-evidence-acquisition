"""E14: the Solver scenario-hints block at ``solver:candidate-hypothesis``.

Model-free, tokenizer-free, encoder-free, server-free, and -- the point of the
module -- CONTACT-free: the block is a pure function of this row's Perception
candidate list, the pinned construction table and the declared bounds.

The four questions this module answers:

1. is the block an ADDITION -- is the L1 candidate list above it byte-identical
   to the base's, and does no other boundary move?
2. does the block ADD NO INFORMATION beyond the pinned table, the template's
   own words, a legal intent id and two closed phrases?
3. does the RECEIPT say what was rendered, from which bytes, and say so even
   when nothing was rendered?
4. does the loader REFUSE an unusable arm -- another view, a bad pin, a
   widened bound, a boundary that is not at L1 -- before any contact?

Design: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
sections 16 and 16.2 (cell B8c).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.node_context_binding import (
    build_solver_hints_binding,
    is_solver_hints_null_arm,
    solver_hints_requires_structured_boundary,
    validate_node_context_policy_config,
    validate_solver_hints_config,
)
from speech_aware_evidence_acquisition.rails.node_context_policy import (
    NO_CUES,
    NO_NEIGHBOUR,
    PROVENANCE_HINTS,
    PROVENANCES,
    SOLVER_HINTS_BOUNDARY,
    SOLVER_HINTS_RENDERER,
    SOLVER_HINTS_TEMPLATE,
    NodeContextPolicyError,
    RenderedBlock,
    build_slurp_node_context_policy,
    load_node_context_template,
)
from speech_aware_evidence_acquisition.rails.scenario_hints import (
    CUE_LIMIT,
    NEIGHBOUR_LIMIT,
    SCENARIO_HINTS_MAX_CANDIDATES,
    SCENARIO_HINTS_RECEIPT_SCHEMA,
    SCENARIO_HINTS_VIEW_ID,
)

from test_node_context_policy import (
    ACTIONS,
    DRAFT_SCHEMA,
    LIMITS,
    PHASE_IDS,
    REPO_ROOT,
    _json,
    _state,
)
from test_slurp_scenario_hints_view import (
    cue,
    neighbour,
    profile,
    write_table,
)

LEGAL_INTENTS = ("alarm_set", "alarm_remove", "calendar_query", "datetime_query")
LEGAL_ENTITY_TYPES = ("time", "date", "event_name")
PARAMS = {
    "max_candidates": 3,
    "projection_policy": (
        "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
    ),
    "draft_response_schema": json.loads(json.dumps(DRAFT_SCHEMA)),
    "legal_entity_types": list(LEGAL_ENTITY_TYPES),
}

CANDIDATES = _json({"candidates": [
    {"intent_id": "alarm_set", "distinction": "The command may create an alarm.",
     "evidence_refs": [], "unresolved_fields": []},
    {"intent_id": "alarm_remove", "distinction": "The command may remove an alarm.",
     "evidence_refs": [], "unresolved_fields": []},
    {"intent_id": "calendar_query", "distinction": "The command may read a diary.",
     "evidence_refs": [], "unresolved_fields": []},
]})
DRAFT = _json({"scenario": "alarm", "action": "set",
               "entities": [{"type": "time", "filler": "seven"}]})

INTENTS = [
    profile("alarm_set", 100, [
        neighbour("alarm_remove", 120, 100, [
            cue("wake", 40, 3), cue("snooze", 30, 2), cue("buzzer", 20, 1),
        ]),
        neighbour("datetime_query", 60, 100, [cue("tomorrow", 12, 4)]),
    ]),
    profile("alarm_remove", 80, [
        neighbour("alarm_set", 110, 80, [cue("cancel", 25, 0)]),
    ]),
    profile("calendar_query", 50),
    profile("datetime_query", 40, [neighbour("alarm_set", 50, 40)]),
]


def _states(*, candidates=CANDIDATES):
    return (
        _state("p1", "phase:perception", candidates),
        _state("s1", "phase:solver", DRAFT),
    )


def _armed(root: Path, **overrides) -> dict[str, object]:
    release_pin, snapshot_pin = write_table(root, intents=INTENTS)
    document: dict[str, object] = {
        "view": SCENARIO_HINTS_VIEW_ID,
        "release": release_pin,
        "snapshot": snapshot_pin,
    }
    document.update(overrides)
    return document


def _binding(root: Path, **overrides):
    document = _armed(root, **overrides)
    return build_solver_hints_binding(
        validate_solver_hints_config(document), REPO_ROOT, root
    )


def _policy(*, solver_hints=None, boundaries=None, level="structured"):
    return build_slurp_node_context_policy(
        repo_root=REPO_ROOT,
        policy_id="typed-slurp-node-context-v1",
        level=level,
        boundaries=boundaries or {},
        legal_intent_ids=LEGAL_INTENTS,
        params=PARAMS,
        solver_hints=solver_hints,
    )


def _compile(policy, role_kind, states=None):
    return policy.compile(
        role_kind=role_kind,
        phase_ids=PHASE_IDS,
        sample_id="s1",
        states=tuple(states if states is not None else _states()),
        available_evidence_ids=("evidence-one",),
        episode_limits=LIMITS,
        actions=ACTIONS,
    )


def _rows(compilation, role_kind=SOLVER_HINTS_BOUNDARY[0]):
    return [
        row
        for row in compilation.receipt["boundaries"]
        if row["boundary"]["consumer_role_kind"] == role_kind
        and row["boundary"]["semantic_class"] == SOLVER_HINTS_BOUNDARY[1]
    ]


# ---------------------------------------------------------------------------
# 1. The template
# ---------------------------------------------------------------------------


def test_the_committed_template_declares_the_hints_renderer():
    template = load_node_context_template(REPO_ROOT, SOLVER_HINTS_TEMPLATE)
    assert template.renderer == SOLVER_HINTS_RENDERER
    assert (REPO_ROOT / "configs" / SOLVER_HINTS_TEMPLATE).is_file()
    assert set(template.sections) == {
        "header", "candidate", "neighbour", "neighbour_empty",
        "candidate_empty", "footer",
    }
    assert re.fullmatch(r"[0-9a-f]{64}", template.sha256)


def test_a_template_of_another_renderer_is_refused(tmp_path):
    with pytest.raises(ValueError, match="requires a 'scenario-hints' template"):
        _binding(tmp_path, template="probes/ncp_slurp_candidate_hypothesis_v1.txt")


# ---------------------------------------------------------------------------
# 2. The block is an addition
# ---------------------------------------------------------------------------


def test_the_candidate_list_above_the_block_is_byte_identical(tmp_path):
    off = _compile(_policy(), "solver")
    on = _compile(_policy(solver_hints=_binding(tmp_path)), "solver")
    off_text = off.states[0].content
    on_text = on.states[0].content
    assert on_text.startswith(off_text + "\n")
    block = on_text[len(off_text) + 1:]
    assert block.startswith(f"SCENARIO HINTS ({SCENARIO_HINTS_VIEW_ID};")
    assert "SCENARIO HINTS" not in off_text
    # The transform still adds no state, drops none and reorders none.
    assert len(on.states) == len(off.states) == 2


def test_no_other_boundary_and_no_other_role_moves(tmp_path):
    binding = _binding(tmp_path)
    for role_kind in ("reviewer", "planner"):
        off = _compile(_policy(), role_kind)
        on = _compile(_policy(solver_hints=binding), role_kind)
        assert [state.content for state in on.states] == [
            state.content for state in off.states
        ]
        assert all(
            "solver_hints" not in row for row in on.receipt["boundaries"]
        )
    # Even inside the Solver contact, only the candidate boundary moves.
    off = _compile(_policy(), "solver")
    on = _compile(_policy(solver_hints=binding), "solver")
    moved = [
        index
        for index, (before, after) in enumerate(zip(off.states, on.states, strict=True))
        if before.content != after.content
    ]
    assert moved == [0]


def test_rendering_is_byte_stable(tmp_path):
    binding = _binding(tmp_path)
    first = _compile(_policy(solver_hints=binding), "solver")
    second = _compile(_policy(solver_hints=binding), "solver")
    assert first.states[0].content == second.states[0].content
    assert first.receipt["receipt_sha256"] == second.receipt["receipt_sha256"]


def test_the_block_is_bounded_by_the_candidates_the_neighbours_and_the_cues(tmp_path):
    binding = _binding(tmp_path)
    compilation = _compile(_policy(solver_hints=binding), "solver")
    row = _rows(compilation)[0]["solver_hints"]
    assert row["counts"]["candidates"] <= SCENARIO_HINTS_MAX_CANDIDATES
    assert row["counts"]["neighbours"] <= (
        SCENARIO_HINTS_MAX_CANDIDATES * NEIGHBOUR_LIMIT
    )
    assert row["counts"]["cues"] <= (
        SCENARIO_HINTS_MAX_CANDIDATES * NEIGHBOUR_LIMIT * CUE_LIMIT
    )
    # calendar_query has no neighbour, so its closed phrase is rendered.
    block = compilation.states[0].content
    assert NO_NEIGHBOUR in block
    assert row["covered_intent_ids"] == [
        "alarm_set", "alarm_remove", "calendar_query",
    ]


def test_narrowed_bounds_narrow_the_block(tmp_path):
    wide = _compile(_policy(solver_hints=_binding(tmp_path / "wide")), "solver")
    narrow = _compile(
        _policy(
            solver_hints=_binding(
                tmp_path / "narrow", max_neighbours=1, max_cues=1,
            )
        ),
        "solver",
    )
    wide_row = _rows(wide)[0]["solver_hints"]
    narrow_row = _rows(narrow)[0]["solver_hints"]
    assert narrow_row["counts"]["neighbours"] < wide_row["counts"]["neighbours"]
    assert narrow_row["counts"]["cues"] < wide_row["counts"]["cues"]
    assert narrow_row["block_chars"] < wide_row["block_chars"]
    assert narrow_row["bounds"]["max_cues"] == 1


def test_a_zero_cue_bound_renders_the_closed_empty_phrase(tmp_path):
    compilation = _compile(
        _policy(solver_hints=_binding(tmp_path, max_cues=0)), "solver",
    )
    assert NO_CUES in compilation.states[0].content


# ---------------------------------------------------------------------------
# 3. The block adds no information
# ---------------------------------------------------------------------------


def test_every_substituted_value_carries_a_table_or_closed_provenance(tmp_path):
    """The 'adds no information' property, section 10's falsifier shape: a
    scenario-hints substitution is a TABLE value, a legal intent id, or one of
    the two closed phrases -- never free text and never a row's own words."""

    binding = _binding(tmp_path)
    policy = _policy(solver_hints=binding)
    rendered = policy._append_solver_hints(
        RenderedBlock(text=""), candidate_ids=["alarm_set", "calendar_query"],
    )
    assert PROVENANCE_HINTS in PROVENANCES
    table_words = {
        item.word
        for entry in binding.table.intents.values()
        for row in entry.neighbours
        for item in row.cues
    }
    legal = set(LEGAL_INTENTS)
    for substitution in rendered.substitutions:
        assert substitution.provenance in PROVENANCES
        if substitution.provenance == "legal-inventory":
            assert substitution.value in legal
        elif substitution.provenance == "closed-vocabulary":
            assert substitution.value in {NO_CUES, NO_NEIGHBOUR}
        else:
            assert substitution.provenance == PROVENANCE_HINTS
            if substitution.field_name == "cues":
                assert set(substitution.value.split(", ")) <= table_words
            elif substitution.field_name == "intent_rows":
                assert substitution.value.isdigit()
            elif substitution.field_name == "view_id":
                assert substitution.value == SCENARIO_HINTS_VIEW_ID
            else:
                assert substitution.field_name == "leakage"
                assert re.fullmatch(
                    r"\d+\.\d % \(\d+ of \d+ nearest neighbours\)",
                    substitution.value,
                )


def test_the_block_never_carries_the_rows_own_draft_or_speech(tmp_path):
    compilation = _compile(_policy(solver_hints=_binding(tmp_path)), "solver")
    block = compilation.states[0].content.split("SCENARIO HINTS", 1)[1]
    assert "seven" not in block          # the draft's filler
    assert "evidence-one" not in block   # the episode's evidence id
    assert "slurp:train:" not in block


# ---------------------------------------------------------------------------
# 4. The receipt
# ---------------------------------------------------------------------------


def test_the_receipt_names_every_byte_the_block_was_composed_from(tmp_path):
    binding = _binding(tmp_path)
    compilation = _compile(_policy(solver_hints=binding), "solver")
    rows = _rows(compilation)
    assert len(rows) == 1
    row = rows[0]["solver_hints"]
    assert row["schema"] == SCENARIO_HINTS_RECEIPT_SCHEMA
    assert row["applied"] is True
    assert row["reason"] is None
    assert row["view_id"] == SCENARIO_HINTS_VIEW_ID
    assert row["release_sha256"] == binding.table.release_sha256
    assert row["snapshot_sha256"] == binding.table.snapshot_sha256
    assert row["table_content_hash"] == binding.table.content_hash()
    assert row["template_id"] == SOLVER_HINTS_TEMPLATE
    assert row["template_sha256"] == binding.template.sha256
    assert row["candidate_ids"] == ["alarm_set", "alarm_remove", "calendar_query"]
    assert row["block_chars"] > 0
    assert re.fullmatch(r"[0-9a-f]{64}", row["block_sha256"])
    # The recorded size is exactly what the rendered state gained.
    off_text = _compile(_policy(), "solver").states[0].content
    assert row["block_chars"] == (
        len(compilation.states[0].content) - len(off_text) - 1
    )


def test_an_unparsed_perception_output_records_a_skip_with_its_reason(tmp_path):
    states = _states(candidates="not json at all")
    compilation = _compile(_policy(solver_hints=_binding(tmp_path)), "solver", states)
    row = _rows(compilation)[0]["solver_hints"]
    assert row["applied"] is False
    assert row["reason"] == "candidates-unparsed"
    assert row["block_sha256"] is None
    assert row["block_chars"] is None
    assert row["counts"] == {"candidates": 0, "neighbours": 0, "cues": 0}
    assert "SCENARIO HINTS" not in compilation.states[0].content


def test_a_pre_e14_receipt_keeps_exactly_its_pre_e14_fields(tmp_path):
    off = _compile(_policy(), "solver")
    on = _compile(_policy(solver_hints=_binding(tmp_path)), "solver")
    off_row = _rows(off)[0]
    on_row = _rows(on)[0]
    assert "solver_hints" not in off_row
    assert "solver_hints" in on_row
    assert set(on_row) - set(off_row) == {"solver_hints"}
    # Only the audited boundary's digest moves; the rendering did too, so the
    # two digests must differ rather than collide.
    assert on_row["receipt_sha256"] != off_row["receipt_sha256"]


# ---------------------------------------------------------------------------
# 5. The refusals, all before contact
# ---------------------------------------------------------------------------


def test_the_policy_refuses_a_boundary_that_is_not_at_l1(tmp_path):
    binding = _binding(tmp_path)
    with pytest.raises(NodeContextPolicyError, match="at level 'structured'"):
        _policy(
            solver_hints=binding,
            boundaries={"solver:candidate-hypothesis": {"level": "raw"}},
        )


def test_the_declared_policy_must_put_the_boundary_at_l1():
    spelling = f"{SOLVER_HINTS_BOUNDARY[0]}:{SOLVER_HINTS_BOUNDARY[1]}"
    with pytest.raises(ValueError, match="requires a declared"):
        solver_hints_requires_structured_boundary(None)
    raw = validate_node_context_policy_config("raw")
    with pytest.raises(ValueError, match=f"requires {spelling}"):
        solver_hints_requires_structured_boundary(raw)
    document = {
        "level": "structured",
        "policy_id": "typed-slurp-node-context-v1",
        "params": json.loads(json.dumps(PARAMS)),
        "boundaries": {spelling: {"level": "raw"}},
    }
    with pytest.raises(ValueError, match="puts it at 'raw'"):
        solver_hints_requires_structured_boundary(
            validate_node_context_policy_config(document)
        )


def test_the_config_validator_refuses_every_unusable_arm(tmp_path):
    assert is_solver_hints_null_arm(None) is True
    assert is_solver_hints_null_arm(_armed(tmp_path)) is False
    good = _armed(tmp_path)
    for override, message in (
        ({"view": "scenario-hints-v2"}, "view must be"),
        ({"template": "elsewhere/x.txt"}, "probes/"),
        ({"max_cues": CUE_LIMIT + 1}, "must lie in"),
        ({"max_neighbours": "three"}, "must be an integer"),
        (
            {"release": {**good["release"], "root": "repo"}},
            "root must be",
        ),
        (
            {"snapshot": {**good["snapshot"], "relpath": "elsewhere.json"}},
            "must be a plain relative",
        ),
    ):
        with pytest.raises(ValueError, match=message):
            validate_solver_hints_config({**good, **override})
    with pytest.raises(ValueError, match="unknown or missing fields"):
        validate_solver_hints_config({**good, "thresholds": {}})
    with pytest.raises(ValueError, match="unknown or missing fields"):
        validate_solver_hints_config(
            {key: value for key, value in good.items() if key != "snapshot"}
        )
    with pytest.raises(ValueError, match="must be an object"):
        validate_solver_hints_config("scenario-hints-v1")


def test_the_canonical_text_is_what_the_binding_reads_back(tmp_path):
    document = _armed(tmp_path)
    canonical = validate_solver_hints_config(document)
    assert json.loads(canonical) == document
    assert validate_solver_hints_config(json.loads(canonical)) == canonical
    with pytest.raises(ValueError, match="canonical bound representation"):
        build_solver_hints_binding(
            json.dumps(document, sort_keys=False, indent=2), REPO_ROOT, tmp_path,
        )
