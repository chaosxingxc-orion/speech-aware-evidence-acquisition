"""E12: the Reviewer slot-audit block through the PRODUCTION render path.

Every episode here runs the real OpenJiuwen role graph, the real
``rails.runner`` and the real ``LlamaServerTransport.render_request`` over the
shared fake transport, against the REAL committed slot-audit table. No model,
no tokenizer, no server, no run directory, and -- the point of the module --
no contact of any kind added by the block.

The request-channel falsifier: with the audit armed, every contact of every
role BUT the Reviewer renders bytes identical to the base's own pins, and
every Reviewer contact differs in exactly the appended block.

E19 (2026-09-19, owner decision 32) adds the second half of the module:
the same falsifier with NO ``context_policy`` declared at all, which is the
sealed anchor's own shape and the base cell B8b-anchor flies on.

Design: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
sections 16 (cell B8b) and 19 (E19).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.node_context_binding import (
    validate_node_context_policy_config,
    validate_reviewer_audit_config,
)
from speech_aware_evidence_acquisition.rails.node_context_policy import (
    SLOT_AUDIT_BOUNDARY,
    SLOT_AUDIT_TEMPLATE,
)
from speech_aware_evidence_acquisition.rails.slot_audit import (
    SLOT_AUDIT_FLAGS,
    SLOT_AUDIT_RECEIPT_SCHEMA,
    SLOT_AUDIT_VIEW_ID,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness
from test_node_context_policy_runner import (
    REPO_ROOT,
    _anchor_outputs,
    _policy_document,
    _request_digests,
)
from test_role_context_binding import perception_format
from test_slurp_slot_audit_view import RELEASE_RELPATH, SNAPSHOT_RELPATH

#: The Reviewer contacts of the harness episode; every other key is a contact
#: whose bytes the block may not move.
REVIEWER_KEYS = ("reviewer/1/1", "reviewer/1/2", "reviewer/2/1")


def _pin(relpath: str) -> dict[str, str]:
    return {
        "relpath": relpath,
        "sha256": hashlib.sha256((REPO_ROOT / relpath).read_bytes()).hexdigest(),
    }


def _reviewer_audit_document(**overrides) -> dict[str, object]:
    document: dict[str, object] = {
        "view": SLOT_AUDIT_VIEW_ID,
        "release": _pin(RELEASE_RELPATH),
        "snapshot": _pin(SNAPSHOT_RELPATH),
    }
    document.update(overrides)
    return document


def _episode(tmp_path, *, policy, reviewer_audit=None):
    """The same production harness E8a's runner proofs use, with the E12 key.

    Copied in shape from ``test_node_context_policy_runner._episode`` rather
    than parameterised into it, so that module's own pins stay a function of
    exactly what it declares.
    """

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_task_tool=True,
    )
    harness._output = _anchor_outputs(harness)
    harness.repo_root = REPO_ROOT
    harness.config = replace(
        harness.config,
        # E19: ``policy=None`` is the anchor's own shape -- the fragment
        # declares no ``context_policy`` key at all.
        context_policy_json=(
            None if policy is None
            else validate_node_context_policy_config(policy)
        ),
        reviewer_audit_json=(
            None if reviewer_audit is None
            else validate_reviewer_audit_config(reviewer_audit)
        ),
    )
    harness.program = replace(
        harness.program,
        phases=tuple(
            replace(phase, response_format_id="slurp-intent-hypotheses-v1")
            if phase.name == "perception" else phase
            for phase in harness.program.phases
        ),
    ).validate()
    original = harness.material_for_phase

    def material_for_phase(phase, context, sealed):
        material = original(phase, context, sealed)
        if phase == "perception":
            return replace(material, response_format=perception_format()).validate()
        return material

    harness.material_for_phase = material_for_phase
    try:
        summary = harness.run()
    finally:
        harness.close()
    return harness, summary


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_armed_block_moves_only_the_reviewer_contacts(tmp_path):
    off_harness, off_summary = _episode(tmp_path / "off", policy=_policy_document())
    on_harness, on_summary = _episode(
        tmp_path / "on",
        policy=_policy_document(),
        reviewer_audit=_reviewer_audit_document(),
    )
    off_digests = _request_digests(off_harness)
    on_digests = _request_digests(on_harness)
    assert set(off_digests) == set(on_digests)
    moved = sorted(key for key in off_digests if off_digests[key] != on_digests[key])
    assert moved == sorted(REVIEWER_KEYS)
    # The episode graph is unchanged: the same contacts, the same transitions
    # outside the Reviewer's own, and no added contact.
    assert len(on_summary.results[0].contacts) == len(off_summary.results[0].contacts)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_reviewer_request_gains_exactly_the_appended_block(tmp_path):
    off_harness, _off = _episode(tmp_path / "off", policy=_policy_document())
    on_harness, on_summary = _episode(
        tmp_path / "on",
        policy=_policy_document(),
        reviewer_audit=_reviewer_audit_document(),
    )

    def wire(harness, key):
        return json.dumps(
            harness.prepared[key]["rendered"], sort_keys=True, ensure_ascii=False
        )

    key = ("s1", "reviewer", 1, 2)
    off_text = wire(off_harness, key)
    on_text = wire(on_harness, key)
    assert "SLOT AUDIT" not in off_text
    assert f"SLOT AUDIT ({SLOT_AUDIT_VIEW_ID};" in on_text
    assert len(on_text) > len(off_text)

    receipt = on_summary.results[0].native_episode_receipt
    rows = [
        row
        for record in receipt["node_context_policy_compilations"]
        for row in record["compilation"]["boundaries"]
        if (
            row["boundary"]["consumer_role_kind"] == SLOT_AUDIT_BOUNDARY[0]
            and row["boundary"]["semantic_class"] == SLOT_AUDIT_BOUNDARY[1]
        )
    ]
    assert rows
    for row in rows:
        audit = row["slot_audit"]
        assert audit["schema"] == SLOT_AUDIT_RECEIPT_SCHEMA
        assert audit["applied"] is True
        assert audit["view_id"] == SLOT_AUDIT_VIEW_ID
        assert audit["template_id"] == SLOT_AUDIT_TEMPLATE
        assert set(audit["flag_counts"]) == set(SLOT_AUDIT_FLAGS)
        assert audit["block_chars"] > 0
    # Every OTHER boundary row is untouched by the audit.
    other = [
        row
        for record in receipt["node_context_policy_compilations"]
        for row in record["compilation"]["boundaries"]
        if "slot_audit" not in row
    ]
    assert other


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_block_pins_its_three_assets_in_every_compilation_record(tmp_path):
    _harness, summary = _episode(
        tmp_path,
        policy=_policy_document(),
        reviewer_audit=_reviewer_audit_document(),
    )
    spelling = f"{SLOT_AUDIT_BOUNDARY[0]}:{SLOT_AUDIT_BOUNDARY[1]}"
    for record in summary.results[0].native_episode_receipt[
        "node_context_policy_compilations"
    ]:
        pins = record["template_sha256s"]
        assert pins[f"{spelling}:slot-audit-release"] == _pin(RELEASE_RELPATH)["sha256"]
        assert pins[f"{spelling}:slot-audit-snapshot"] == _pin(SNAPSHOT_RELPATH)["sha256"]
        assert f"{spelling}:slot-audit" in pins


# ---------------------------------------------------------------------------
# E19: the same block on a base that declares no policy at all
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_on_the_anchor_shape_the_block_moves_only_the_reviewer_contacts(tmp_path):
    """Cell B8b-anchor's whole request-channel claim, in one assertion.

    OFF is the anchor itself: no ``context_policy``, no ``reviewer_audit``,
    so the node-context transform never runs. ON adds the audit key and
    nothing else. Perception, Solver and Planner requests must be
    byte-identical across the two arms.
    """

    off_harness, off_summary = _episode(tmp_path / "off", policy=None)
    on_harness, on_summary = _episode(
        tmp_path / "on", policy=None, reviewer_audit=_reviewer_audit_document(),
    )
    off_digests = _request_digests(off_harness)
    on_digests = _request_digests(on_harness)
    assert set(off_digests) == set(on_digests)
    moved = sorted(key for key in off_digests if off_digests[key] != on_digests[key])
    assert moved == sorted(REVIEWER_KEYS)
    assert len(on_summary.results[0].contacts) == len(
        off_summary.results[0].contacts
    )
    # The OFF arm records no node-context compilation at all: the key's
    # absence composes the pre-E12 tree exactly.
    assert "node_context_policy_compilations" not in (
        off_summary.results[0].native_episode_receipt
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_on_the_anchor_shape_the_reviewer_gains_exactly_the_block(tmp_path):
    """The sealed draft goes out unchanged and the block follows it; every
    other boundary emits a raw row whose rendered bytes ARE its source's."""

    off_harness, _off = _episode(tmp_path / "off", policy=None)
    on_harness, on_summary = _episode(
        tmp_path / "on", policy=None, reviewer_audit=_reviewer_audit_document(),
    )

    def wire(harness, key):
        return json.dumps(
            harness.prepared[key]["rendered"], sort_keys=True, ensure_ascii=False
        )

    key = ("s1", "reviewer", 1, 2)
    off_text = wire(off_harness, key)
    on_text = wire(on_harness, key)
    assert "SLOT AUDIT" not in off_text
    assert f"SLOT AUDIT ({SLOT_AUDIT_VIEW_ID};" in on_text
    assert len(on_text) > len(off_text)

    receipt = on_summary.results[0].native_episode_receipt
    rows = [
        row
        for record in receipt["node_context_policy_compilations"]
        for row in record["compilation"]["boundaries"]
    ]
    assert rows
    audited = [row for row in rows if "slot_audit" in row]
    assert audited
    for row in rows:
        # E19: the composed policy is the key's own bare "raw" arm, so
        # every row is raw and renders no template.
        assert row["level"] == "raw"
        assert row["template_id"] is None
        if "slot_audit" not in row:
            assert row["rendered_sha256"] == row["source"]["content_sha256"]
            continue
        assert row["boundary"]["consumer_role_kind"] == SLOT_AUDIT_BOUNDARY[0]
        assert row["boundary"]["semantic_class"] == SLOT_AUDIT_BOUNDARY[1]
        audit = row["slot_audit"]
        assert audit["schema"] == SLOT_AUDIT_RECEIPT_SCHEMA
        assert audit["view_id"] == SLOT_AUDIT_VIEW_ID
        assert audit["template_id"] == SLOT_AUDIT_TEMPLATE
        assert set(audit["flag_counts"]) == set(SLOT_AUDIT_FLAGS)
        if audit["applied"]:
            assert audit["block_chars"] > 0
            assert row["rendered_sha256"] != row["source"]["content_sha256"]
        else:
            assert audit["reason"] == "draft-unparsed"
            assert row["rendered_sha256"] == row["source"]["content_sha256"]
    spelling = f"{SLOT_AUDIT_BOUNDARY[0]}:{SLOT_AUDIT_BOUNDARY[1]}"
    for record in receipt["node_context_policy_compilations"]:
        pins = record["template_sha256s"]
        assert sorted(pins) == sorted((
            f"{spelling}:slot-audit",
            f"{spelling}:slot-audit-release",
            f"{spelling}:slot-audit-snapshot",
        ))


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_off_arm_is_the_keys_absence_down_to_the_byte(tmp_path):
    """``reviewer_audit_json`` None renders exactly what the pre-E12 tree
    rendered for the same policy -- the same bytes, the same receipt fields."""

    first_harness, first_summary = _episode(tmp_path / "a", policy=_policy_document())
    second_harness, _second = _episode(tmp_path / "b", policy=_policy_document())
    assert _request_digests(first_harness) == _request_digests(second_harness)
    for record in first_summary.results[0].native_episode_receipt[
        "node_context_policy_compilations"
    ]:
        assert all(
            "slot_audit" not in row for row in record["compilation"]["boundaries"]
        )
        assert not any("slot-audit" in key for key in record["template_sha256s"])
