"""WAVE W4: the seven harness modules, re-expressed as config-table entries.

The openJiuwen implementation assessment (``docs/readiness/
2026-09-08-openjiuwen-implementation-assessment-v1.md`` section 7) tabulated
seven harness modules and found that only ONE of them -- the silence tail --
is cleanly one config key today. The unit plan is two keys that must move
together; the slot schema is one key whose OFF arm still changes the program
id and the contact count; and the remaining four need a ``policy`` change, a
``scorers`` change or a policy subclass to turn off. A module whose OFF arm is
a different code path is not a twin of its ON arm, so the design note's gate
("module ON versus module OFF in the same harness on the same roster, one
config key, never a second code path") cannot be run on it.

Each test below is the machine form of that requirement for one module:
compose the ON arm and the OFF arm as four real config fragments, flatten
both composed configs, and assert they differ in EXACTLY ONE dotted key --
the one the receipt's ``switch`` names. Both arms are then loaded through
``rails.config_tables`` so the proof is about a configuration that actually
validates, not about two JSON documents that happen to differ by one key.

The seventh module (the window hook) has no table entry yet, and its test is
the negative control: it measures how many keys its switch moves TODAY and
pins the two runner rails that block the loop-back which would replace it.
"""

import json

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails.config_tables import (
    ConfigTableError,
    config_key_diff,
    load_config_tables,
    switch_key,
)
from speech_aware_evidence_acquisition.rails.controllers import (
    PHASE_KNOWLEDGE_KINDS,
    default_phase_program,
)
from speech_aware_evidence_acquisition.rails.phase_review import LOOP_REFUSAL_REASON
from speech_aware_evidence_acquisition.rails.phase_supply import load_phase_supply_specs

SHA = "b" * 64

LEGAL_LABEL_JUDGE = "slurp-legal-label-flag-v1"
SLOT_SCHEMA_JUDGE = "slurp-slot-schema-conformance-v1"
REPAIR_JUDGE = "e21-substitution-alignment-flag-v1"
SLOT_SCHEMA_VIEW = "slurp-intent-slot-schema-for-state"

MODEL = {"transport": "llama-server", "base_url": "http://x"}
DATASET = {"carrier_lock_key": "earnings21-original", "split_name": "dev"}


def _material(template="probes/select.txt", **extra):
    return {"instruction_template": template, **extra}


#: A SLURP slots-phase material entry. ``state_fill`` reads the predecessor
#: state, so E1 requires the sealed-manifest binding beside it; both arms of
#: the slot-schema proof therefore carry the binding and only the view moves.
PREDECESSOR = {
    "predecessor_binding": "sealed-manifest",
    "predecessor_source": {
        "manifest_relpath": "runs/SAEA-W4/attempt-0/SAEA-W4.run-manifest.json",
        "manifest_sha256": SHA,
        "producer_policy_id": "SAEA-W4-DIRECT",
    },
}


SUPPLY = {
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
        "embedded_signal": "speech: the row's own sealed speech packet",
    },
    "facet_source": {
        "kind": "sealed-vectors",
        "relpath": "vectors/f.jsonl",
        "sha256": SHA,
        "tool_contact_ledger_row": "row-1",
        "embedded_signal": "the facet representation text",
    },
}


def _compose_arm(root, name, baseline, experiment=None):
    """Write and compose one arm's four fragments under ``root/name``."""

    arm_root = root / name
    for kind, fragment in (
        ("model", MODEL),
        ("dataset", DATASET),
        ("baseline", baseline),
        ("experiment", {"experiment_id": "SAEA-W4-PROOF", **(experiment or {})}),
    ):
        path = arm_root / "configs" / kind / "f.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fragment), encoding="utf-8")
    return compose(arm_root, "f", "f", "f", "f")


def _one_key_switch(tmp_path, program_id, on_baseline, off_baseline):
    """Compose both arms, load both through the tables, and return the ONE
    config key on which they differ.

    ``switch_key`` refuses a pair that moves more than one key, so a
    regression that split a module across two keys fails here rather than
    silently producing a comparison that is not a twin.
    """

    program = default_phase_program(program_id)
    on = _compose_arm(tmp_path, "on", on_baseline)
    off = _compose_arm(tmp_path, "off", off_baseline)
    load_config_tables(on.values, program)
    load_config_tables(off.values, program)
    assert on.config_hash != off.config_hash
    return switch_key(on.values, off.values)


# ---------------------------------------------------------------------------
# 1. silence tail -- observe.<phase>.tail_silence_seconds
#
# Assessment verdict today: YES, already one clean key
# (``obs_slice_tail_silence_seconds``, 0 = the bytes before the knob existed).
# It is lifted into the table verbatim; the point of the proof is that the
# lift did not cost the property.
# ---------------------------------------------------------------------------


def test_silence_tail_is_one_key(tmp_path):
    base = {
        "arm": "e21-tail",
        "policy": "phase-draft-revise-v1",
        "knowledge_views": {
            "draft": {"material": _material()},
            "revise": {"material": _material("probes/fill.txt")},
        },
    }
    assert _one_key_switch(
        tmp_path,
        "phase-draft-revise-v1",
        dict(base, observe={"draft": {"tail_silence_seconds": 2.0}}),
        dict(base, observe=None),
    ) == "observe.draft.tail_silence_seconds"


# ---------------------------------------------------------------------------
# 2. unit plan -- observe.<phase>.unit_plan
#
# Assessment verdict today: NO. ``obs_unit_plan`` and ``obs_unit_plan_sha256``
# are TWO keys that must move together, and the ojw executor refuses the pair
# by name, so on/off also changes executor. One nullable object fixes both.
# ---------------------------------------------------------------------------


def test_unit_plan_is_one_key_even_though_it_carries_a_path_and_a_pin(tmp_path):
    base = {
        "arm": "e21-units",
        "policy": "phase-draft-revise-v1",
        "knowledge_views": {
            "draft": {"material": _material()},
            "revise": {"material": _material("probes/fill.txt")},
        },
    }
    assert _one_key_switch(
        tmp_path,
        "phase-draft-revise-v1",
        dict(
            base,
            observe={
                "draft": {"unit_plan": {"relpath": "docs/obs/units.json", "sha256": SHA}}
            },
        ),
        dict(base, observe=None),
    ) == "observe.draft.unit_plan"


def test_the_unit_plans_two_legacy_keys_are_two_keys(tmp_path):
    """The defect the table entry removes, measured rather than asserted."""

    base = {"arm": "e21-units", "policy": "obs-agent-loop"}
    on = _compose_arm(
        tmp_path,
        "on",
        dict(base, obs_unit_plan="docs/obs/units.json", obs_unit_plan_sha256=SHA),
    )
    off = _compose_arm(tmp_path, "off", base)
    assert config_key_diff(on.values, off.values) == (
        "obs_unit_plan",
        "obs_unit_plan_sha256",
    )
    with pytest.raises(ConfigTableError, match="unrelated config keys"):
        switch_key(on.values, off.values)


# ---------------------------------------------------------------------------
# 3. legal-label projection -- judges.<phase>.judges
#
# Assessment verdict today: NO, and for a subtler reason than the others --
# the switch is the ``scorers`` list (``slurp-slu-projected-v2`` versus
# ``slurp-slu-official``), which is a MEASUREMENT switch. Flipping it changes
# what is scored, not what the system did. As a judge entry it becomes a
# system ablation with the scorer left alone, which is the only form the
# admission gate can read.
# ---------------------------------------------------------------------------


def test_legal_label_projection_is_one_key_with_the_scorer_left_alone(tmp_path):
    base = {
        "arm": "slurp-direct",
        "policy": "phase-direct-only-v1",
        "scorers": ["slurp-slu-official"],
        "knowledge_views": {"direct": {"material": _material()}},
    }
    key = _one_key_switch(
        tmp_path,
        "phase-direct-only-v1",
        dict(base, judges={"direct": {"judges": [LEGAL_LABEL_JUDGE]}}),
        dict(base, judges=None),
    )
    assert key == "judges.direct.judges"
    assert not key.startswith("scorers")


# ---------------------------------------------------------------------------
# 4. slot schema -- knowledge_views.<phase>.material.state_fill
#
# Assessment verdict today: NEARLY -- one key, but turning it off meant
# dropping to ``phase-direct-only-v1``, which changes the contact count too.
# In the table the phase, the program id and the contact count all stay
# fixed and only the view moves.
# ---------------------------------------------------------------------------


def test_slot_schema_view_is_one_key_and_keeps_the_program_and_contact_count(tmp_path):
    program_id = "phase-slots-given-intent-supplied-v1"
    base = {"arm": "slurp-slots", "policy": program_id}
    key = _one_key_switch(
        tmp_path,
        program_id,
        dict(
            base,
            knowledge_views={
                "slots": {
                    "material": _material(state_fill=SLOT_SCHEMA_VIEW, **PREDECESSOR)
                }
            },
        ),
        dict(
            base,
            knowledge_views={"slots": {"material": _material(**PREDECESSOR)}},
        ),
    )
    assert key == "knowledge_views.slots.material.state_fill"
    assert default_phase_program(program_id).max_contacts == 1


# ---------------------------------------------------------------------------
# 5. repair post-processor -- judges.<phase>.judges
#
# Assessment verdict today: NO. ``response_postprocessor`` is read ONLY by the
# ``obs-repair-loop`` policy and is REQUIRED there, so off means switching
# ``policy`` -- a different harness.
#
# WHICH TABLE, and why. The design note's Decision 11-C is the deciding rule:
# the Reviewer "SCORES and FLAGS, it never proposes a revision", and the note
# names "``e21-entity-repair-substitutions-v1``'s refusal reasons" among the
# frozen checks BEHIND the Reviewer. The module therefore splits along the
# line the decision already draws: its criticism half -- the alignment rule
# that decides which proposed edits are legal, and refuses the rest -- is a
# JUDGE, registered as ``e21-substitution-alignment-flag-v1`` whose
# ``JudgeVerdict`` structurally cannot carry replacement text
# (``core.base.assert_criticism_only``); its delivery half stays a Solver-side
# constraint on the revise phase. It is not an ``observe`` entry (it reads a
# response, never the audio) and not a ``knowledge_views`` entry (it supplies
# the phase with nothing).
# ---------------------------------------------------------------------------


def test_repair_alignment_is_one_key_in_the_judges_table(tmp_path):
    base = {
        "arm": "e21-kc-e1f",
        "policy": "phase-draft-revise-v1",
        "knowledge_views": {
            "draft": {"material": _material()},
            "revise": {"material": _material("probes/fill.txt")},
        },
    }
    assert _one_key_switch(
        tmp_path,
        "phase-draft-revise-v1",
        dict(base, judges={"revise": {"judges": [REPAIR_JUDGE]}}),
        dict(base, judges=None),
    ) == "judges.revise.judges"


def test_the_repair_judge_is_criticism_only():
    """The reason the criticism half can live in the ``judges`` table at all:
    its verdict type cannot carry a replacement, so a judge entry can never
    become a second answering path."""

    from speech_aware_evidence_acquisition.core.base import JUDGES, JudgeVerdict

    verdict = JUDGES.resolve(REPAIR_JUDGE)
    assert not hasattr(JudgeVerdict, "replacement_text")
    assert not any(
        "replacement" in name or "revision" in name
        for name in getattr(JudgeVerdict, "__dataclass_fields__", {})
    )
    assert verdict is not None


# ---------------------------------------------------------------------------
# 6. retrieval provider -- knowledge_views.<phase>.supply
#
# Assessment verdict today: NO, "because the phase must ALSO declare
# knowledge: 'supplied', which is baked into the program id, so on/off means
# swapping phase-slots-given-intent-v1 <-> ...-supplied-v1".
#
# That is true of the CONVENTION and not of the CODE, and the difference
# matters because it decides whether change #6 needs a PhaseSpec relaxation.
# ``PhaseSpec.knowledge == "supplied"`` already means the phase MAY be
# supplied (``rails/controllers.py``: '"supplied": the phase MAY have a
# supply_for_phase-sourced SupplyPacket'), and ``load_phase_supply_specs``
# returns an empty mapping for an absent block without complaint. So ONE
# supplied-declaring program id already carries both arms, and the
# ``"optional"`` kind the assessment asks for is not needed.
# ---------------------------------------------------------------------------


def test_retrieval_provider_is_one_key_on_one_program_id(tmp_path):
    program_id = "phase-slots-given-intent-supplied-v1"
    base = {"arm": "slurp-supplied", "policy": program_id}
    key = _one_key_switch(
        tmp_path,
        program_id,
        dict(
            base,
            knowledge_views={"slots": {"material": _material(), "supply": SUPPLY}},
        ),
        dict(base, knowledge_views={"slots": {"material": _material()}}),
    )
    assert key == "knowledge_views.slots.supply"


def test_a_supplied_phase_with_no_supply_block_is_already_legal():
    """The evidence for the paragraph above: no PHASE_KNOWLEDGE_KINDS
    relaxation is required, so this wave adds no key to that closed set."""

    program = default_phase_program("phase-slots-given-intent-supplied-v1")
    assert program.phases[0].knowledge == "supplied"
    assert load_phase_supply_specs({}, program) == {}
    assert PHASE_KNOWLEDGE_KINDS == frozenset({"none", "supplied"})


# ---------------------------------------------------------------------------
# 7. window hook -- NOT a table entry yet, and why
#
# The per-window instruction and delivery of ``obs-repair-loop`` is a
# ``_window_hook`` override on a policy SUBCLASS
# (``reproduction/obs_loop.py`` returns None; ``reproduction/repair_loop.py``
# overrides it), selected by the ``policy`` value. It has no config key at all,
# so there is nothing to lift: it is not a mode of one module but the
# Reviewer+Solver revise PAIR, and its table form is ``judges: [...]`` plus the
# ``phase-draft-revise-v1`` program -- which is change #8's re-expression of
# the E21 obs path onto FlightRuntime, owned by a different wave, not a key
# this wave can add.
#
# The loop-back that would let one phase re-ask a flagged row inside the
# agent graph is refused by name in W1 (``on_flag: "loop"``) against two
# runner rails, so widening the tables here would half-wire it.
# ---------------------------------------------------------------------------


def test_the_window_hook_switch_moves_more_than_one_key_today(tmp_path):
    """Measured, not asserted: flipping the repair window hook off swaps the
    policy AND drops the post-processor pair -- three keys and a different
    code path."""

    on = _compose_arm(
        tmp_path,
        "on",
        {
            "arm": "e21-kc-e1f",
            "policy": "obs-repair-loop",
            "response_postprocessor": "e21-entity-repair-substitutions-v1",
            "response_postprocessor_params": {"anchor_ratio_floor": 0.5},
        },
    )
    off = _compose_arm(tmp_path, "off", {"arm": "e21-kc-e1f", "policy": "obs-agent-loop"})
    diff = config_key_diff(on.values, off.values)
    assert diff == (
        "policy",
        "response_postprocessor",
        "response_postprocessor_params.anchor_ratio_floor",
    )
    with pytest.raises(ConfigTableError, match="unrelated config keys"):
        switch_key(on.values, off.values)


def test_the_loop_back_that_would_replace_the_window_hook_is_still_refused():
    assert "on_flag='loop' is not wired yet" in LOOP_REFUSAL_REASON
    assert "_validate_new_agent_states" in LOOP_REFUSAL_REASON
    assert "schedule_wave" in LOOP_REFUSAL_REASON
    with pytest.raises(Exception, match="not wired yet"):
        from speech_aware_evidence_acquisition.rails.config_tables import (
            load_judges_table,
        )

        load_judges_table(
            {"judges": {"revise": {"judges": [REPAIR_JUDGE], "on_flag": "loop"}}},
            default_phase_program("phase-draft-revise-v1"),
        )


# ---------------------------------------------------------------------------
# The whole table, at once
# ---------------------------------------------------------------------------


def test_every_module_switch_is_one_key_and_they_compose(tmp_path):
    """All four tables armed at once still compose, and dropping every table
    to its null arm returns the cell to the pre-table baseline's own hash."""

    program_id = "phase-slots-given-intent-supplied-v1"
    program = default_phase_program(program_id)
    off_baseline = {
        "arm": "slurp-all",
        "policy": program_id,
        "phase_material": {"slots": _material()},
    }
    on_baseline = {
        "arm": "slurp-all",
        "policy": program_id,
        "knowledge_views": {
            "slots": {
                "material": _material(state_fill=SLOT_SCHEMA_VIEW, **PREDECESSOR),
                "supply": SUPPLY,
            }
        },
        "judges": {"slots": {"judges": [SLOT_SCHEMA_JUDGE]}},
        "observe": {"slots": {"tail_silence_seconds": 2.0}},
        "toolkits": {"task_type": "command"},
    }
    on = _compose_arm(tmp_path, "on", on_baseline)
    tables = load_config_tables(on.values, program)
    assert set(tables.observe) == {"slots"}
    assert set(tables.judges) == {"slots"}
    assert set(tables.knowledge_views.supply) == {"slots"}
    assert tables.toolkits.task_type == "command"

    all_null = _compose_arm(
        tmp_path,
        "null",
        dict(
            off_baseline,
            knowledge_views=None,
            judges=None,
            observe=None,
            toolkits=None,
        ),
    )
    plain = _compose_arm(tmp_path, "plain", off_baseline)
    assert all_null.config_hash == plain.config_hash


def test_a_module_cannot_be_switched_by_two_spellings_at_once(tmp_path):
    """The rule that keeps "one config key" true: the flat block and its
    wrapping table may not both be declared."""

    program = default_phase_program("phase-slots-given-intent-supplied-v1")
    composed = _compose_arm(
        tmp_path,
        "both",
        {
            "arm": "slurp",
            "policy": "phase-slots-given-intent-supplied-v1",
            "phase_material": {"slots": _material()},
            "knowledge_views": {"slots": {"material": _material()}},
        },
    )
    with pytest.raises(ConfigTableError, match="two spellings of one switch"):
        load_config_tables(composed.values, program)
