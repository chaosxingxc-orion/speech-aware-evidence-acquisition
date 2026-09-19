"""E12: the Reviewer slot-audit block at the ``reviewer:current-draft``
boundary -- rendering, determinism, receipts and the config switch.

Model-free, tokenizer-free, server-free: every block here is rendered by the
production policy object over synthetic ``AgentStateArtifact`` values and the
COMMITTED template, against a synthetic table written to ``tmp_path``.

Design: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
section 16 (cell B8b), sections 3-4 (the boundary and its templates) and
section 9 (the receipt form).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.config_tables import (
    is_episode_null_arm,
)
from speech_aware_evidence_acquisition.rails.node_context_binding import (
    RAW_NODE_CONTEXT_POLICY_ID,
    build_slot_audit_binding,
    is_reviewer_audit_null_arm,
    reviewer_audit_boundary_attachment,
    validate_node_context_policy_config,
    validate_reviewer_audit_config,
)
from speech_aware_evidence_acquisition.rails.node_context_policy import (
    SLOT_AUDIT_ATTACHMENT_L1,
    SLOT_AUDIT_ATTACHMENT_RAW,
    SLOT_AUDIT_BOUNDARY,
    SLOT_AUDIT_RENDERER,
    SLOT_AUDIT_TEMPLATE,
    SLURP_CLOSED_DRAFT_SCHEMA,
    NodeContextPolicyError,
    build_slurp_node_context_policy,
    load_node_context_template,
    resolve_slot_audit_binding,
)
from speech_aware_evidence_acquisition.rails.slot_audit import (
    DETAIL_EMPTY_DRAFT,
    DETAIL_MISSING_COMMON,
    DETAIL_REPRESENTATION,
    DETAIL_TYPE_UNSEEN,
    FLAG_EMPTY_DRAFT,
    FLAG_MISSING_COMMON,
    FLAG_REPRESENTATION,
    FLAG_TYPE_UNSEEN,
    SLOT_AUDIT_FLAGS,
    SLOT_AUDIT_RECEIPT_SCHEMA,
    SLOT_AUDIT_VIEW_ID,
    load_slot_audit_table,
    slot_audit_thresholds,
)

from test_node_context_policy import (
    ACTIONS,
    CANDIDATES,
    LIMITS,
    PARAMS,
    PHASE_IDS,
    REPO_ROOT,
    _compile,
    _json,
    _policy,
    _state,
)
from test_slurp_slot_audit_view import (
    RELEASE_RELPATH,
    SNAPSHOT_RELPATH,
    SYNTHETIC_INTENTS,
    _write_table,
)

#: The synthetic table's own intents are ``alarm_set`` and ``general_quirky``;
#: the shared draft contract's legal intents are ``alarm_set``,
#: ``alarm_remove`` and ``calendar_query``, so ``alarm_set`` is the one intent
#: both know -- which is what every rendering test below uses.
DRAFT_IN_TABLE = _json({
    "scenario": "alarm", "action": "set",
    "entities": [{"type": "time", "filler": "seven"}],
})
DRAFT_EMPTY = _json({"scenario": "alarm", "action": "set", "entities": []})
DRAFT_DIGITS = _json({
    "scenario": "alarm", "action": "set",
    "entities": [{"type": "time", "filler": "7:30 am"}],
})
DRAFT_OFF_TABLE = _json({
    "scenario": "calendar", "action": "query",
    "entities": [{"type": "date", "filler": "2017-03-15"}],
})
MALFORMED_DRAFT = "I think this is probably an alarm."


def _binding(tmp_path: Path):
    release, snapshot = _write_table(tmp_path, intents=SYNTHETIC_INTENTS)
    table = load_slot_audit_table(
        tmp_path, release=release, snapshot=snapshot, view_id=SLOT_AUDIT_VIEW_ID
    )
    return (
        resolve_slot_audit_binding(
            REPO_ROOT, table=table, thresholds=slot_audit_thresholds()
        ),
        release,
        snapshot,
    )


def _audited_policy(tmp_path: Path, **kwargs):
    binding, _release, _snapshot = _binding(tmp_path)
    return build_slurp_node_context_policy(
        repo_root=REPO_ROOT,
        policy_id="typed-slurp-node-context-v1",
        level="structured",
        boundaries=kwargs.pop("boundaries", {}),
        legal_intent_ids=("alarm_set", "alarm_remove", "calendar_query"),
        params=PARAMS,
        slot_audit=binding,
        **kwargs,
    )


def _raw_audited_policy(tmp_path: Path):
    """E19: the audit armed on the key's own bare ``raw`` arm -- no
    params, no template, nothing rendered at any boundary."""

    binding, _release, _snapshot = _binding(tmp_path)
    return build_slurp_node_context_policy(
        repo_root=REPO_ROOT,
        policy_id=RAW_NODE_CONTEXT_POLICY_ID,
        level="raw",
        boundaries={},
        slot_audit=binding,
    )


def _states(draft: str):
    return [
        _state("p1", "phase:perception", CANDIDATES),
        _state("s1", "phase:solver", draft),
    ]


def _draft_block(compilation):
    return compilation.states[1].content


def _draft_row(compilation):
    return next(
        row for row in compilation.receipt["boundaries"]
        if row["boundary"]["semantic_class"] == "current-draft"
    )


# ---------------------------------------------------------------------------
# (a) the committed template
# ---------------------------------------------------------------------------


def test_the_committed_template_declares_the_audit_renderer():
    template = load_node_context_template(REPO_ROOT, SLOT_AUDIT_TEMPLATE)
    assert template.renderer == SLOT_AUDIT_RENDERER
    assert set(template.sections) == {
        "header", "profile_header", "profile_item", "profile_empty",
        "flag", "flags_empty", "footer",
    }


def test_a_template_of_another_renderer_is_refused(tmp_path):
    binding, _release, _snapshot = _binding(tmp_path)
    with pytest.raises(NodeContextPolicyError, match="requires a 'slot-audit'"):
        resolve_slot_audit_binding(
            REPO_ROOT,
            table=binding.table,
            thresholds=binding.thresholds,
            template="probes/ncp_slurp_current_draft_reviewer_v1.txt",
        )


# ---------------------------------------------------------------------------
# (b) the block is an ADDITION -- the L1 draft block is byte-identical
# ---------------------------------------------------------------------------


def test_the_audit_is_appended_and_the_l1_draft_block_is_byte_identical(tmp_path):
    base = _compile(_policy(), "reviewer", _states(DRAFT_IN_TABLE))
    armed = _compile(_audited_policy(tmp_path), "reviewer", _states(DRAFT_IN_TABLE))
    base_block = _draft_block(base)
    armed_block = _draft_block(armed)
    assert armed_block.startswith(f"{base_block}\n")
    audit = armed_block[len(base_block) + 1:]
    assert audit.startswith(f"SLOT AUDIT ({SLOT_AUDIT_VIEW_ID};")
    assert "alarm_set" in audit
    # The draft's own fillers never reach the audit block.
    assert "seven" not in audit


def test_no_other_boundary_moves_when_the_audit_is_armed(tmp_path):
    """The audit is declared at ONE boundary. Every other consumer of every
    other state renders exactly the bytes the unarmed policy renders."""

    states = _states(DRAFT_IN_TABLE) + [
        _state("r1", "phase:reviewer", "The draft looks plausible."),
        _state("pl1", "phase:planner", "ACCEPT"),
    ]
    armed = _audited_policy(tmp_path)
    base = _policy()
    for role_kind in ("perception", "solver", "planner"):
        assert [state.content for state in _compile(armed, role_kind, states).states] == [
            state.content for state in _compile(base, role_kind, states).states
        ], role_kind
    # And at the Reviewer, only the current-draft state differs.
    armed_states = _compile(armed, "reviewer", states).states
    base_states = _compile(base, "reviewer", states).states
    differing = [
        index
        for index, (left, right) in enumerate(zip(armed_states, base_states))
        if left.content != right.content
    ]
    assert differing == [1]


# ---------------------------------------------------------------------------
# (c) determinism
# ---------------------------------------------------------------------------


def test_the_block_renders_byte_stably(tmp_path):
    policy = _audited_policy(tmp_path)
    digests = {
        hashlib.sha256(
            _draft_block(_compile(policy, "reviewer", _states(DRAFT_EMPTY))).encode()
        ).hexdigest()
        for _ in range(200)
    }
    assert len(digests) == 1
    # A freshly built policy over a freshly loaded table renders the same.
    rebuilt = _audited_policy(tmp_path)
    assert (
        hashlib.sha256(
            _draft_block(_compile(rebuilt, "reviewer", _states(DRAFT_EMPTY))).encode()
        ).hexdigest()
        in digests
    )


def test_the_rendered_block_matches_its_receipted_digest(tmp_path):
    policy = _audited_policy(tmp_path)
    compilation = _compile(policy, "reviewer", _states(DRAFT_EMPTY))
    block = _draft_block(compilation)
    row = _draft_row(compilation)
    audit = row["slot_audit"]
    rendered = block[len(block) - audit["block_chars"]:]
    assert hashlib.sha256(rendered.encode()).hexdigest() == audit["block_sha256"]


# ---------------------------------------------------------------------------
# (d) the receipt
# ---------------------------------------------------------------------------


def test_the_receipt_row_binds_the_table_the_template_and_the_flags(tmp_path):
    binding, release, snapshot = _binding(tmp_path)
    policy = build_slurp_node_context_policy(
        repo_root=REPO_ROOT, policy_id="typed-slurp-node-context-v1",
        level="structured", boundaries={},
        legal_intent_ids=("alarm_set", "alarm_remove", "calendar_query"),
        params=PARAMS, slot_audit=binding,
    )
    row = _draft_row(_compile(policy, "reviewer", _states(DRAFT_EMPTY)))
    audit = row["slot_audit"]
    assert audit["schema"] == SLOT_AUDIT_RECEIPT_SCHEMA
    assert audit["view_id"] == SLOT_AUDIT_VIEW_ID
    assert audit["release_sha256"] == release["sha256"]
    assert audit["snapshot_sha256"] == snapshot["sha256"]
    assert audit["table_content_hash"] == binding.table.content_hash()
    assert audit["template_id"] == SLOT_AUDIT_TEMPLATE
    assert audit["template_sha256"] == binding.template.sha256
    assert audit["thresholds"] == slot_audit_thresholds().as_json()
    assert audit["applied"] is True and audit["reason"] is None
    assert audit["intent_id"] == "alarm_set" and audit["intent_in_table"] is True
    assert set(audit["flag_counts"]) == set(SLOT_AUDIT_FLAGS)
    assert audit["flag_counts"][FLAG_EMPTY_DRAFT] == 1
    assert audit["flag_counts"][FLAG_MISSING_COMMON] == 1
    # The flag list names TYPES and counts, never a filler.
    assert all(
        set(flag) <= {"flag", "detail", "entity_type", "rows", "of_rows"}
        for flag in audit["flags"]
    )


def test_an_unparsed_draft_records_an_unapplied_audit(tmp_path):
    policy = _audited_policy(tmp_path)
    compilation = _compile(policy, "reviewer", _states(MALFORMED_DRAFT))
    row = _draft_row(compilation)
    assert row["parse_status"] == "malformed"
    audit = row["slot_audit"]
    assert audit["applied"] is False
    assert audit["reason"] == "draft-unparsed"
    assert audit["block_sha256"] is None and audit["block_chars"] is None
    assert audit["flag_counts"] == dict.fromkeys(SLOT_AUDIT_FLAGS, 0)
    assert "SLOT AUDIT" not in _draft_block(compilation)


def test_only_the_armed_boundary_carries_an_audit_block_in_its_receipt(tmp_path):
    policy = _audited_policy(tmp_path)
    states = _states(DRAFT_IN_TABLE) + [
        _state("r1", "phase:reviewer", "The draft looks plausible."),
    ]
    for role_kind in ("reviewer", "planner", "solver"):
        compilation = _compile(policy, role_kind, states)
        for row in compilation.receipt["boundaries"]:
            armed = (
                role_kind == SLOT_AUDIT_BOUNDARY[0]
                and row["boundary"]["semantic_class"] == SLOT_AUDIT_BOUNDARY[1]
            )
            assert ("slot_audit" in row) is armed, (role_kind, row["boundary"])


def test_an_unarmed_policy_keeps_the_pre_e12_receipt_fields(tmp_path):
    """The OFF arm's receipt row is the pre-E12 row, field for field and digest
    for digest."""

    base = _compile(_policy(), "reviewer", _states(DRAFT_IN_TABLE))
    row = _draft_row(base)
    assert "slot_audit" not in row
    armed = _draft_row(_compile(_audited_policy(tmp_path), "reviewer", _states(DRAFT_IN_TABLE)))
    assert armed["receipt_sha256"] != row["receipt_sha256"]
    stripped = {key: value for key, value in armed.items() if key not in {
        "slot_audit", "receipt_sha256", "rendered_state_id", "rendered_sha256",
        "rendered_chars",
    }}
    assert stripped == {key: value for key, value in row.items() if key not in {
        "receipt_sha256", "rendered_state_id", "rendered_sha256", "rendered_chars",
    }}


# ---------------------------------------------------------------------------
# (e) the flags reach the rendered block
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "draft,expected",
    [
        (DRAFT_EMPTY, (FLAG_EMPTY_DRAFT, FLAG_MISSING_COMMON)),
        (DRAFT_DIGITS, (FLAG_REPRESENTATION,)),
        (DRAFT_IN_TABLE, ()),
        (DRAFT_OFF_TABLE, (FLAG_REPRESENTATION,)),
    ],
    ids=["empty", "digits", "clean", "off-table"],
)
def test_every_fired_flag_reaches_the_block_and_the_receipt(tmp_path, draft, expected):
    policy = _audited_policy(tmp_path)
    compilation = _compile(policy, "reviewer", _states(draft))
    block = _draft_block(compilation)
    audit = _draft_row(compilation)["slot_audit"]
    assert tuple(flag["flag"] for flag in audit["flags"]) == expected
    for name in expected:
        assert f"  {name}: " in block
    if not expected:
        assert "no audit flag fires on this draft" in block


def test_an_intent_outside_the_table_renders_the_no_profile_line(tmp_path):
    policy = _audited_policy(tmp_path)
    compilation = _compile(policy, "reviewer", _states(DRAFT_OFF_TABLE))
    block = _draft_block(compilation)
    assert "this intent has no construction rows in the table" in block
    assert _draft_row(compilation)["slot_audit"]["intent_in_table"] is False


# ---------------------------------------------------------------------------
# (f) the block adds no information
# ---------------------------------------------------------------------------


def test_the_block_introduces_nothing_outside_its_declared_sources(tmp_path):
    """Every token of the audit block is a template literal, a flag name, an
    entity type or intent id the draft or the table already carries, a decimal
    count, or a token of a RELEASED convention sentence. Nothing else."""

    binding, _release, _snapshot = _binding(tmp_path)

    def words(text: str) -> set[str]:
        return {
            token.strip("(),;:.%-") for token in text.split()
        } - {""}

    allowed = words(
        "\n".join(
            line
            for lines in binding.template.sections.values()
            for line in lines
        )
    )
    allowed |= set(SLOT_AUDIT_FLAGS) | {SLOT_AUDIT_VIEW_ID}
    # The four detail forms are themselves a CLOSED committed vocabulary; a
    # rendered detail is one of them with a type name, a share rendering or a
    # released convention sentence substituted in, and nothing else.
    for form in (
        DETAIL_TYPE_UNSEEN, DETAIL_EMPTY_DRAFT,
        DETAIL_MISSING_COMMON, DETAIL_REPRESENTATION,
    ):
        allowed |= words(re.sub(r"\{[a-z_]+\}", " ", form))
    allowed |= set(binding.table.intents)
    allowed |= {
        entity_type
        for profile in binding.table.intents.values()
        for entity_type, _rows, _share in profile.types
    }
    for convention in binding.table.conventions.values():
        allowed |= words(convention.statement)
        allowed.add(convention.entity_type)
    number = re.compile(r"^[0-9]+(\.[0-9]+)?$")
    policy = _audited_policy(tmp_path)
    for draft in (DRAFT_EMPTY, DRAFT_DIGITS, DRAFT_IN_TABLE):
        compilation = _compile(policy, "reviewer", _states(draft))
        block = _draft_block(compilation)
        audit = _draft_row(compilation)["slot_audit"]
        rendered = block[len(block) - audit["block_chars"]:]
        for token in words(rendered):
            assert token in allowed or number.fullmatch(token), (token, draft)


# ---------------------------------------------------------------------------
# (g) the switch
# ---------------------------------------------------------------------------


def _config(tmp_path: Path, **overrides):
    release, snapshot = _write_table(tmp_path, intents=SYNTHETIC_INTENTS)
    document = {"view": SLOT_AUDIT_VIEW_ID, "release": release, "snapshot": snapshot}
    document.update(overrides)
    return document


def test_the_switch_null_arm_is_the_keys_absence(tmp_path):
    key = "native_episode.reviewer_audit"
    assert is_reviewer_audit_null_arm(None) is True
    assert is_episode_null_arm(key, None) is True
    assert is_episode_null_arm(key, _config(tmp_path)) is False


def test_the_switch_config_is_validated_fail_closed(tmp_path):
    document = _config(tmp_path)
    canonical = validate_reviewer_audit_config(document)
    assert json.loads(canonical) == document
    assert validate_reviewer_audit_config(json.loads(canonical)) == canonical

    with pytest.raises(ValueError, match="unknown or missing fields"):
        validate_reviewer_audit_config({**document, "nope": 1})
    with pytest.raises(ValueError, match="unknown or missing fields"):
        validate_reviewer_audit_config({"view": SLOT_AUDIT_VIEW_ID})
    with pytest.raises(ValueError, match="must be 'slot-audit-v1'"):
        validate_reviewer_audit_config({**document, "view": "slot-audit-v2"})
    with pytest.raises(ValueError, match="must pin a committed"):
        validate_reviewer_audit_config({
            **document, "snapshot": {"relpath": "docs/x.json", "sha256": "0" * 64},
        })
    with pytest.raises(ValueError, match="probes/"):
        validate_reviewer_audit_config({**document, "template": "x.txt"})
    with pytest.raises(ValueError, match="unknown key"):
        validate_reviewer_audit_config({**document, "thresholds": {"nope": 0.5}})
    with pytest.raises(ValueError, match="must be an object"):
        validate_reviewer_audit_config("slot-audit-v1")


def test_the_switch_resolves_the_boundary_attachment(tmp_path):
    """E19 (owner decision 32): the switch no longer REQUIRES L1. It
    resolves which of the two things the block is appended to, and
    refuses only the level whose rendering would clean it away."""

    spelling = f"{SLOT_AUDIT_BOUNDARY[0]}:{SLOT_AUDIT_BOUNDARY[1]}"
    structured = validate_node_context_policy_config({
        "level": "structured",
        "policy_id": "typed-slurp-node-context-v1",
        "params": json.loads(json.dumps(PARAMS)),
    })
    assert reviewer_audit_boundary_attachment(structured) == (
        SLOT_AUDIT_ATTACHMENT_L1
    )
    # No declared policy at all -- the anchor's own shape.
    assert reviewer_audit_boundary_attachment(None) == SLOT_AUDIT_ATTACHMENT_RAW
    raw = validate_node_context_policy_config("raw")
    assert reviewer_audit_boundary_attachment(raw) == SLOT_AUDIT_ATTACHMENT_RAW
    overridden = validate_node_context_policy_config({
        "level": "structured",
        "policy_id": "typed-slurp-node-context-v1",
        "params": json.loads(json.dumps(PARAMS)),
        "boundaries": {spelling: {"level": "raw"}},
    })
    assert reviewer_audit_boundary_attachment(overridden) == (
        SLOT_AUDIT_ATTACHMENT_RAW
    )
    # The third level never reaches the attachment: this carrier
    # registers a cleaning renderer only for review-finding, so a
    # cleaned reviewer:current-draft is refused before an audit is read.
    with pytest.raises(ValueError, match="cannot be cleaned"):
        validate_node_context_policy_config({
            "level": "structured",
            "policy_id": "typed-slurp-node-context-v1",
            "params": json.loads(json.dumps(PARAMS)),
            "boundaries": {spelling: {
                "level": "cleaned",
                "cleaning": {
                    "phase_id": "context_clean_draft",
                    "instruction_template": (
                        "probes/ncp_slurp_cleaning_review_v1.txt"
                    ),
                    "response_format_id": "ncp-review-issues-v1",
                    "on_invalid": "fallback-l1",
                },
            }},
        })


def test_the_policy_attaches_an_audit_at_raw(tmp_path):
    spelling = f"{SLOT_AUDIT_BOUNDARY[0]}:{SLOT_AUDIT_BOUNDARY[1]}"
    at_raw = _audited_policy(tmp_path, boundaries={spelling: {"level": "raw"}})
    assert at_raw.slot_audit_attachment == SLOT_AUDIT_ATTACHMENT_RAW
    assert _audited_policy(tmp_path).slot_audit_attachment == (
        SLOT_AUDIT_ATTACHMENT_L1
    )
    assert _raw_audited_policy(tmp_path).slot_audit_attachment == (
        SLOT_AUDIT_ATTACHMENT_RAW
    )


# ---------------------------------------------------------------------------
# (e) E19: the same block, appended to the SEALED draft
# ---------------------------------------------------------------------------


def test_the_closed_draft_contract_is_the_one_the_l1_fragments_declare():
    """One contract, two attachments. The committed L1 baseline declares
    the draft schema in its params; the sealed-draft attachment binds
    :data:`SLURP_CLOSED_DRAFT_SCHEMA` instead, and they are the same
    bytes -- so a draft parses identically either way."""

    fragment = json.loads(
        (
            REPO_ROOT / "configs" / "baseline"
            / "slurp-native-anchor-ncp-l1-reviewer-audit-train-fold-a-v1.json"
        ).read_text(encoding="utf-8")
    )
    declared = fragment["native_episode"]["context_policy"]["params"][
        "draft_response_schema"
    ]
    assert json.dumps(declared, sort_keys=True) == json.dumps(
        SLURP_CLOSED_DRAFT_SCHEMA, sort_keys=True
    )


def test_the_audit_appends_to_the_sealed_draft_under_an_all_raw_policy(tmp_path):
    """E19: the block's bytes are the L1 arm's bytes; what changes is the
    ONE thing they follow -- here the sealed Solver response itself."""

    states = _states(DRAFT_IN_TABLE)
    raw_armed = _compile(_raw_audited_policy(tmp_path), "reviewer", states)
    l1_armed = _compile(_audited_policy(tmp_path), "reviewer", states)
    sealed = states[1].content
    exposed = raw_armed.states[1].content
    assert exposed.startswith(sealed + "\n")
    block = exposed[len(sealed) + 1:]
    l1_text = l1_armed.states[1].content
    assert l1_text.endswith("\n" + block)
    # Every OTHER state passes through byte for byte.
    assert raw_armed.states[0].content == states[0].content


def test_the_sealed_draft_row_is_raw_and_names_the_block_it_added(tmp_path):
    compilation = _compile(
        _raw_audited_policy(tmp_path), "reviewer", _states(DRAFT_IN_TABLE)
    )
    row = _draft_row(compilation)
    assert row["level"] == "raw"
    assert row["template_id"] is None
    audit = row["slot_audit"]
    assert audit["applied"] is True
    assert audit["intent_id"] == "alarm_set"
    assert audit["block_chars"] > 0
    sealed = _states(DRAFT_IN_TABLE)[1].content
    block = compilation.states[1].content[len(sealed) + 1:]
    assert audit["block_sha256"] == hashlib.sha256(block.encode()).hexdigest()
    # The one place a raw row's rendered bytes are not its source's, and
    # it is never silent: no ``slot_audit``, no inequality.
    assert row["rendered_sha256"] != row["source"]["content_sha256"]
    others = [
        other for other in compilation.receipt["boundaries"] if other is not row
    ]
    assert others
    for other in others:
        assert "slot_audit" not in other
        assert other["rendered_sha256"] == other["source"]["content_sha256"]


def test_an_unparsed_draft_under_the_raw_attachment_keeps_the_sealed_bytes(
    tmp_path,
):
    states = _states(MALFORMED_DRAFT)
    compilation = _compile(_raw_audited_policy(tmp_path), "reviewer", states)
    assert compilation.states[1].content == states[1].content
    row = _draft_row(compilation)
    assert row["rendered_sha256"] == row["source"]["content_sha256"]
    assert row["slot_audit"]["applied"] is False
    assert row["slot_audit"]["reason"] == "draft-unparsed"


def test_an_all_raw_policy_with_no_audit_is_untouched_by_e19(tmp_path):
    """The OFF arm of the OFF arm: no audit, no derived state, no
    ``slot_audit`` key anywhere in the receipt."""

    policy = build_slurp_node_context_policy(
        repo_root=REPO_ROOT,
        policy_id=RAW_NODE_CONTEXT_POLICY_ID,
        level="raw",
        boundaries={},
    )
    states = _states(DRAFT_IN_TABLE)
    compilation = _compile(policy, "reviewer", states)
    assert [state.content for state in compilation.states] == [
        state.content for state in states
    ]
    for row in compilation.receipt["boundaries"]:
        assert "slot_audit" not in row
        assert row["rendered_sha256"] == row["source"]["content_sha256"]


def test_building_the_binding_reads_and_checks_the_pinned_bytes(tmp_path):
    document = _config(tmp_path)
    # The binding reads BOTH the table and the committed template from the
    # SAME root, which is what makes one pinned root the whole provenance.
    probes = tmp_path / "configs" / "probes"
    probes.mkdir(parents=True, exist_ok=True)
    (probes / Path(SLOT_AUDIT_TEMPLATE).name).write_bytes(
        (REPO_ROOT / "configs" / SLOT_AUDIT_TEMPLATE).read_bytes()
    )
    canonical = validate_reviewer_audit_config(document)
    binding = build_slot_audit_binding(canonical, tmp_path)
    assert binding.table.view_id == SLOT_AUDIT_VIEW_ID
    assert binding.template.template_id == SLOT_AUDIT_TEMPLATE
    poisoned = validate_reviewer_audit_config({
        **document, "snapshot": {**document["snapshot"], "sha256": "0" * 64},
    })
    with pytest.raises(ValueError, match="hashes to"):
        build_slot_audit_binding(poisoned, tmp_path)


def test_the_released_view_binds_against_the_repository(tmp_path):
    """The shipped fragment's own shape: the two committed files, read from
    the repository root, under the registered view id."""

    document = {
        "view": SLOT_AUDIT_VIEW_ID,
        "release": {
            "relpath": RELEASE_RELPATH,
            "sha256": hashlib.sha256(
                (REPO_ROOT / RELEASE_RELPATH).read_bytes()
            ).hexdigest(),
        },
        "snapshot": {
            "relpath": SNAPSHOT_RELPATH,
            "sha256": hashlib.sha256(
                (REPO_ROOT / SNAPSHOT_RELPATH).read_bytes()
            ).hexdigest(),
        },
    }
    binding = build_slot_audit_binding(
        validate_reviewer_audit_config(document), REPO_ROOT
    )
    assert len(binding.table.intents) == 60
    assert binding.table.construction_utterance_count == 9354


def test_the_audit_makes_no_contact(tmp_path):
    """Zero contacts, stated as a structural fact: the compilation that renders
    the block takes no cleaning invoker, registers no contact and returns the
    same number of states it was handed."""

    policy = _audited_policy(tmp_path)
    states = _states(DRAFT_EMPTY)
    compilation = policy.compile(
        role_kind="reviewer",
        phase_ids=PHASE_IDS,
        sample_id="s1",
        states=tuple(states),
        available_evidence_ids=(),
        episode_limits=LIMITS,
        actions=ACTIONS,
        cleaning_invoker=None,
    )
    assert len(compilation.states) == len(states)
    assert all(
        row["cleaning_contact"] is None
        for row in compilation.receipt["boundaries"]
    )
    assert "SLOT AUDIT" in _draft_block(compilation)
