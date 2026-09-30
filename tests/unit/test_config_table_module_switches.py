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
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails.config_tables import (
    RUN_LEVEL_SWITCH_KEYS,
    STORES_PIN_FIELDS,
    ConfigTableError,
    config_key_diff,
    is_episode_null_arm,
    is_run_null_arm,
    is_stores_null_arm,
    is_stores_repin_arm,
    load_config_tables,
    resolve_episode_switch_key,
    resolve_run_switch_key,
    resolve_stores_switch_key,
    stores_arm_matches,
    stores_pins,
    switch_key,
)
from speech_aware_evidence_acquisition.rails.controllers import (
    PHASE_KNOWLEDGE_KINDS,
    default_phase_program,
)
from speech_aware_evidence_acquisition.rails.phase_review import LOOP_REFUSAL_REASON
from speech_aware_evidence_acquisition.rails.phase_supply import load_phase_supply_specs

REPO_ROOT = Path(__file__).resolve().parents[2]

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
# 8. SLURP standing fallback candidate --
#    knowledge_views.<phase>.material.fill_params.fallback_candidates
#
# FIX-1 (docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md,
# E5a): a Perception-phase ``fill_params`` key, validated in
# ``rails.artifact_results.build_slurp_hypothesis_artifact_validator`` next
# to the rest of the same hypothesis contract (``id``, ``max_candidates``,
# ``source_catalog``). It needs NO new table code: ``knowledge_views``
# already wraps a phase's ``phase_material`` entry -- ``fill_params``
# included -- verbatim (``rails.config_tables.unwrap_knowledge_views``:
# "each phase's material / supply object is carried over UNCHANGED"), so the
# switch resolves through the SAME ``knowledge_views.<phase>.material`` entry
# ``knowledge_views.<phase>.material.state_fill`` already resolves through
# for the slot-schema view (test 4 above) -- one more field one level
# deeper, not a new entry kind.
#
# The option is validated and hashed here, but it is deliberately inert for
# what the model itself is asked to produce (the response-format JSON schema
# ``rails.artifact_results.slurp_intent_hypotheses_response_format`` builds
# never reads it): the actual consumption-time append happens where the
# candidate state is READ -- ``rails.knowledge_provider`` (slot-card supply,
# ``candidate_supply.<phase>.fallback_candidates``) and ``rails.role_context``
# (Solver/Reviewer rendering, its own ``role_context.params.fallback_candidates``)
# -- each of which declares this SAME option, by the same name, at its own
# existing consumption site, exactly as ``max_candidates`` and
# ``projection_policy`` already are. Those two consumption-side switches are
# proven directly against real request/audit output in
# ``test_candidate_semantic_supply.py`` and ``test_role_context.py`` rather
# than through this file's config-diff shape (neither ``candidate_supply``
# nor ``role_context.params`` is a ``knowledge_views``/``judges`` table entry
# today).
# ---------------------------------------------------------------------------

FALLBACK_PERCEPTION_FILL_PARAMS = {
    "id": "slurp-intent-hypotheses-v1",
    "max_candidates": 3,
    "source_catalog": {
        "data_relpath": "prepared/x/catalog.json", "sha256": SHA, "source_sha256": SHA,
    },
}


def _fallback_perception_material(**fill_param_overrides):
    return _material(
        "probes/slurp_native_role_perception_v3.txt",
        response_format_id="slurp-intent-hypotheses-v1",
        fill_params={**FALLBACK_PERCEPTION_FILL_PARAMS, **fill_param_overrides},
    )


def test_fallback_candidate_is_one_key_in_the_knowledge_views_table(tmp_path):
    program_id = "phase-native-candidates-review-revise-v1"
    base = {"arm": "slurp-fallback", "policy": program_id}
    other_phases = {
        "reviewer": {"material": _material("probes/slurp_native_role_reviewer_v1.txt")},
        "planner": {"material": _material("probes/slurp_native_role_planner_v1.txt")},
        "solver": {"material": _material("probes/slurp_native_role_solver_v2.txt")},
    }
    off_views = {
        "perception": {"material": _fallback_perception_material()},
        **other_phases,
    }
    on_views = {
        "perception": {
            "material": _fallback_perception_material(fallback_candidates=["general_quirky"])
        },
        **other_phases,
    }
    key = _one_key_switch(
        tmp_path, program_id,
        dict(base, knowledge_views=on_views),
        dict(base, knowledge_views=off_views),
    )
    assert key == "knowledge_views.perception.material.fill_params.fallback_candidates"


def test_fallback_candidate_switch_key_resolves_to_the_material_entry():
    from speech_aware_evidence_acquisition.rails.config_tables import resolve_switch_key

    assert resolve_switch_key(
        "knowledge_views",
        "knowledge_views.perception.material.fill_params.fallback_candidates",
    ) == "material"


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


# ---------------------------------------------------------------------------
# 8. the cross-call dispatcher -- obs_prefetch_depth, the RUN switch class
#
# Not one of the assessment's seven. It arrived from the other side, on
# master, while WAVE W4 was being written, and it is the case the four tables
# cannot hold: one config key, no per-phase entry, and no request byte moved.
# Its admission (SAEA-E21-FULL44-DISPATCH-ADMISSION-V1, NEUTRAL) is the reason
# rails.config_tables carries a fifth switch class.
#
# The proof runs on the COMMITTED bytes of both arms rather than on synthetic
# fragments, because the dispatcher's own sealed cell flew exactly these two.
# ---------------------------------------------------------------------------


def _committed_baseline(name):
    path = REPO_ROOT / "configs" / "baseline" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_cross_call_dispatcher_is_one_run_level_key(tmp_path):
    off_bytes = _committed_baseline("e21-buf90-zero-locked-scored4")
    on_bytes = _committed_baseline("e21-buf90-zero-locked-scored4-prefetch1")

    on = _compose_arm(tmp_path, "on", on_bytes)
    off = _compose_arm(tmp_path, "off", off_bytes)
    assert on.config_hash != off.config_hash
    assert switch_key(on.values, off.values) == "obs_prefetch_depth"

    # The OFF arm is the key's ABSENCE, which is the driver's documented
    # default of 0 -- so OFF is a twin of the pre-knob baseline, not a third
    # cell identity.
    assert "obs_prefetch_depth" not in off_bytes
    assert is_run_null_arm(off_bytes.get("obs_prefetch_depth")) is True
    assert is_run_null_arm(0) is True
    assert is_run_null_arm(on_bytes["obs_prefetch_depth"]) is False


def test_the_run_switch_class_is_a_closed_allowlist():
    """A flat key is not admitted to the run class by being flat. Every other
    obs knob on that same fragment is refused, because a module that changes
    the request the core sees belongs in a config table.

    Three keys today: ``obs_prefetch_depth`` (the cross-call dispatcher),
    ``slurp_projection_v3_delivery`` (E4, SLURP v2 base program module M3,
    2026-09-17 -- section 9a below has that key's own dedicated proof) and
    ``dispatch`` (the native-episode slot fill, owner decision 159,
    2026-09-27 -- its falsifier is tests/unit/test_dispatch_slot_fill.py and
    the byte-identity receipt the harness-admission entry names)."""

    assert set(RUN_LEVEL_SWITCH_KEYS) == {
        "obs_prefetch_depth",
        "slurp_projection_v3_delivery",
        "dispatch",
    }
    assert resolve_run_switch_key("dispatch") == "dispatch"
    assert resolve_run_switch_key("obs_prefetch_depth") == "obs_prefetch_depth"
    for refused in ("obs_batch_slices", "obs_boundary_mode", "obs_buffer_seconds"):
        with pytest.raises(ConfigTableError, match="closed allowlist"):
            resolve_run_switch_key(refused)
    with pytest.raises(ConfigTableError, match="is dotted"):
        resolve_run_switch_key("run.obs_prefetch_depth")


# ---------------------------------------------------------------------------
# 8a. USE projection v3 delivery -- slurp_projection_v3_delivery, the SECOND
# ``run`` switch class key (E4, SLURP v2 base program module M3, 2026-09-17).
#
# Same admission shape as the cross-call dispatcher above: one flat key, no
# per-phase table entry, and the module's OWN falsifier is that it moves no
# request byte at all -- it runs strictly after the Solver's response is
# already in hand and rewrites only what gets sealed into the outputs row,
# keeping the raw pre-projection text in custody
# (rails.slurp_projection_v3.apply_slurp_projection_v3_delivery). Unlike the
# dispatcher, this key's own harness-admission entry is NOT written by this
# change: that entry's own switch_rule requires a 'falsifier' of kind
# 'request-bytes-identical' PLUS the receipt of an actual flown comparator
# pair, and this module's own E4 engineering mission flies nothing (zero
# model contacts) -- the receipt is for the coordinator to add once a B-phase
# cell actually flies the transform live. This test proves the KEY MECHANICS
# (closed allowlist membership, null arm, one-key config diff on the real
# committed baseline pair) that the admission entry will cite when it lands.
# ---------------------------------------------------------------------------


def test_the_projection_v3_delivery_switch_is_one_run_level_key_on_the_held_baseline_pair():
    off_bytes = _committed_baseline("slurp-native-dual-store-train-fold-a-review-off-v1")
    on_bytes = _committed_baseline(
        "slurp-native-dual-store-train-fold-a-review-off-projected-v3-v1"
    )

    # The held ON fragment also changes its own scorers list and
    # speech-feature identity (deliberately, per its own ``what_this_is``:
    # a unique cache/dedup identity and the v3-projected scorer declared
    # side by side with the primary) -- ``switch_key`` therefore cannot
    # narrow this PAIR to one key, exactly as the review-loop-off pair above
    # is not one key either. What this test pins instead is the SAME thing
    # ``config_key_diff`` pins for that pair: the flat switch key is present
    # on exactly one side, with the OFF side's absence being the documented
    # null arm.
    diff = config_key_diff(on_bytes, off_bytes)
    assert "slurp_projection_v3_delivery" in diff

    assert "slurp_projection_v3_delivery" not in off_bytes
    assert is_run_null_arm(off_bytes.get("slurp_projection_v3_delivery")) is True
    assert is_run_null_arm(0) is True
    assert is_run_null_arm(on_bytes["slurp_projection_v3_delivery"]) is False
    assert on_bytes["slurp_projection_v3_delivery"] == 1


def test_the_projection_v3_delivery_switch_alone_is_one_key_when_nothing_else_moves():
    """Isolated from the held fragment's OTHER deliberate changes (deliverable
    3's scorers/speech-feature identity bump): composing two otherwise
    IDENTICAL fragments that differ only in this one flat key IS resolved by
    ``switch_key`` to exactly this key -- the same proof
    ``test_the_cross_call_dispatcher_is_one_run_level_key`` gives
    ``obs_prefetch_depth``."""

    off_bytes = _committed_baseline("slurp-native-dual-store-train-fold-a-review-off-v1")
    on_bytes = dict(off_bytes)
    on_bytes["slurp_projection_v3_delivery"] = 1

    assert switch_key(on_bytes, off_bytes) == "slurp_projection_v3_delivery"


# ---------------------------------------------------------------------------
# 8. E1 review loop off (M0) -- the 'episode' class's
#    native_episode.review_loop key (harness-admission v3, Fable E6)
#
# The module's own channel (docs/superpowers/specs/2026-09-16-slurp-v2-base-
# program-design.md section 3, row M0) is native_episode.max_revisions 0 +
# reviewer/planner max_iterations 0 TOGETHER: three leaves under
# native_episode that share no common dotted prefix (max_revisions is a
# direct child; roles.reviewer.max_iterations and roles.planner.max_iterations
# share only "native_episode.roles", not with max_revisions). switch_key's
# own shared-prefix walk still refuses this by construction -- measured
# below, not asserted from opinion -- and it is not a spelling defect fixable
# by moving the fields around: native_episode is a required, structured block
# for this program with no absent/0 default the way obs_prefetch_depth has
# one, so there is no flat top-level spelling either (resolve_run_switch_key
# rejects any dotted key on sight).
#
# Rather than teach core.config.compose to EXPAND one declared key into those
# three leaves before hashing -- letting two different JSON fragments hash to
# the same cell identity, a change to the composition pipeline this module's
# admission does not need -- rails.native_episode_config.
# load_native_episode_config gained an OPTIONAL, VALIDATED marker instead:
# native_episode.review_loop, "on" or "off". The three leaves stay
# authoritative and required exactly as before this field existed; the
# marker is refused the instant it disagrees with what they already say
# (test_review_loop_marker_disagreeing_with_the_leaves_is_refused below).
# rails.config_tables now names the marker directly: table "episode", key
# "native_episode.review_loop", OFF is the marker "off" (or its absence),
# resolved by resolve_episode_switch_key / is_episode_null_arm. The class's
# proof for this module treats the three leaves -- and the policy id's
# consequent max_contacts change -- as DERIVED, exactly as the 'stores'
# class's own proof treats a store's identity/prose fields as bookkeeping.
# ---------------------------------------------------------------------------

#: The three leaves native_episode.review_loop derives from and is validated
#: against (rails.native_episode_config.load_native_episode_config). A
#: proof-level exemption, not a schema field: the leaves stay required and
#: authoritative in every committed fragment; only the PROOF below treats
#: them as implied by the marker rather than as free variables of their own.
REVIEW_LOOP_DERIVED_LEAVES = frozenset({
    "native_episode.max_revisions",
    "native_episode.roles.planner.max_iterations",
    "native_episode.roles.reviewer.max_iterations",
})

#: Bookkeeping this module's proof also sets aside: attempt/run identity, the
#: Reviewer tool authority that is simply absent when Reviewer never runs,
#: the policy id (paired one-for-one with the max_contacts ceiling by
#: rails.native_episode_config's own cross-role validation), the
#: speech-feature identity pair this arm pins separately from the anchor, and
#: the free-English description.
REVIEW_LOOP_BOOKKEEPING_KEYS = frozenset({
    # Each cell binds its own model-free prepared Perception supply (the artifact's
    # identity pins the composed config), so the pin is per-cell bookkeeping, not
    # part of the module's channel -- the same exemption the E3 stores proof makes
    # for preparation_source_receipts.
    "prepared_phase_supply.relpath",
    "prepared_phase_supply.sha256",
    "native_contact_fit.attempt_id",
    "native_contact_fit.contact_cap",
    "native_contact_fit.run_id",
    "phase_tools.reviewer.allowed_tools",
    "phase_tools.reviewer.knowledge_views",
    "phase_tools.reviewer.mode",
    "phase_tools.reviewer.source_authority_role",
    "policy",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "what_this_is",
})


def test_review_loop_off_switch_moves_three_native_episode_keys_today():
    """Measured, not asserted, and still true now that the marker exists:
    the three leaves alone share no common dotted prefix, so a NAIVE
    switch_key call over the raw fragments (or over native_episode alone)
    still refuses them. This is exactly why the class needs its own
    class-aware proof (below) rather than the generic single-prefix
    algorithm every other module in this file uses."""

    on = _committed_baseline("slurp-native-dual-store-train-fold-a-anchor-v1")
    off = _committed_baseline("slurp-native-dual-store-train-fold-a-review-off-v1")

    with pytest.raises(ConfigTableError, match="unrelated config keys"):
        switch_key(on, off)

    # Restricted to the native_episode block alone -- the module's actual
    # mechanism -- the marker plus the three leaves still share no common
    # prefix (review_loop and max_revisions are both direct children), so
    # even that narrower view is not one key by the generic algorithm.
    episode_diff = config_key_diff(on["native_episode"], off["native_episode"])
    assert episode_diff == (
        "max_revisions",
        "review_loop",
        "roles.planner.max_iterations",
        "roles.reviewer.max_iterations",
    )
    with pytest.raises(ConfigTableError, match="unrelated config keys"):
        switch_key(on["native_episode"], off["native_episode"])

    # Not a run-level key either: the mechanism is nested inside a required,
    # structured block, and resolve_run_switch_key refuses any dotted key by
    # construction, so there is no flat top-level spelling of this module.
    with pytest.raises(ConfigTableError, match="is dotted"):
        resolve_run_switch_key("native_episode.max_revisions")
    assert "native_episode" not in RUN_LEVEL_SWITCH_KEYS
    assert "review_loop" not in RUN_LEVEL_SWITCH_KEYS


def test_review_loop_off_is_one_episode_class_key_once_derived_leaves_are_set_aside():
    """The positive proof harness-admission v3 needed: once the three leaves
    review_loop derives from, and the bookkeeping every module in this file
    already sets aside, are removed from the raw whole-fragment diff, exactly
    one key is left -- the marker itself."""

    on = _committed_baseline("slurp-native-dual-store-train-fold-a-anchor-v1")
    off = _committed_baseline("slurp-native-dual-store-train-fold-a-review-off-v1")

    diff = set(config_key_diff(on, off))
    remaining = diff - REVIEW_LOOP_DERIVED_LEAVES - REVIEW_LOOP_BOOKKEEPING_KEYS
    assert remaining == {"native_episode.review_loop"}

    assert (
        resolve_episode_switch_key("native_episode.review_loop")
        == "native_episode.review_loop"
    )
    assert is_episode_null_arm("native_episode.review_loop", "off") is True
    assert is_episode_null_arm("native_episode.review_loop", None) is True
    assert is_episode_null_arm("native_episode.review_loop", "on") is False

    # The anchor (ON) never declares the marker at all -- legal, because the
    # marker is optional and its absence is not itself a claim about the
    # loop's state; only a DECLARED value is checked against the leaves.
    assert "review_loop" not in on["native_episode"]
    assert off["native_episode"]["review_loop"] == "off"


def test_review_loop_marker_disagreeing_with_the_leaves_is_refused():
    """Item 5's own requirement: a validator that refuses inconsistency
    between the review_loop marker and the three leaves it derives from."""

    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    off = _committed_baseline("slurp-native-dual-store-train-fold-a-review-off-v1")
    off_program = default_phase_program(off["policy"])

    # The committed fragment, unmutated, still validates -- the marker
    # agrees with the leaves it derives from.
    load_native_episode_config(off, off_program)

    mutated = json.loads(json.dumps(off))
    mutated["native_episode"]["review_loop"] = "on"
    with pytest.raises(ValueError, match="inconsistent"):
        load_native_episode_config(mutated, off_program)

    mutated["native_episode"]["review_loop"] = "sideways"
    with pytest.raises(ValueError, match="'on' or 'off'"):
        load_native_episode_config(mutated, off_program)


def test_review_loop_off_is_the_review_loop_enabled_property_on_the_loaded_config():
    """The one thing that DOES cleanly gate the module at the loaded-config
    level: NativeEpisodeConfig.review_loop_enabled, which E1 exposes as the
    single reliable witness of the paired shape -- backed by
    load_native_episode_config's own cross-role validation, which is what
    makes reading Reviewer's max_iterations alone sufficient."""

    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    on = _committed_baseline("slurp-native-dual-store-train-fold-a-anchor-v1")
    off = _committed_baseline("slurp-native-dual-store-train-fold-a-review-off-v1")
    on_program = default_phase_program(on["policy"])
    off_program = default_phase_program(off["policy"])

    on_config = load_native_episode_config(on, on_program)
    off_config = load_native_episode_config(off, off_program)

    assert on_config.review_loop_enabled is True
    assert off_config.review_loop_enabled is False
    assert on_program.max_contacts == 11
    assert off_program.max_contacts == 2


# 9. grouped-Solver sampling (E2, SLURP v2 base program M2) -- the
#    'episode' class's native_episode.roles.solver key (harness-admission
#    v3, Fable E6).
#
# The M2 design row (docs/superpowers/specs/2026-09-16-slurp-v2-base-
# program-design.md section 3) names the switch class "judges", but the
# judges table's own entries are `{judges, on_flag, params}` -- the
# Reviewer's SCORE-and-FLAG seat (owner Decision 11-C: "the Reviewer SCORES
# and FLAGS and never proposes a revision"). Grouped sampling changes what
# the SOLVER decodes (temperature, seed) and how its N answers are combined
# into the delivered draft, which is a different seat's decision, not a
# Reviewer judgment. Forcing it into `judges.<phase>.{judges,on_flag,params}`
# would either not fit at all (there is no judge id for "sample N times")
# or misrepresent a Solver-side decoding/aggregation module as a Reviewer
# verdict. It also fails the ``run`` class's own admission test: ``run`` is
# reserved for a module whose OWN falsifier proves the request never moves a
# byte (``rails.config_tables.resolve_run_switch_key``'s docstring, and the
# cross-call dispatcher's own falsifier above); grouped sampling deliberately
# DOES move request bytes (temperature, seed), so it is explicitly excluded
# from ``run`` by that same rule ("a module that changes the request the
# core sees belongs in a config table, not here").
#
# What IS true, and what this test proves with the same ``switch_key``
# machine check every module above uses: the whole module is ONE nested
# object at ``native_episode.roles.solver`` (``samples``,
# ``decoding_overrides``, ``commit``), sitting inside the ALREADY-EXISTING
# per-run ``native_episode`` configuration block (validated by
# ``rails.native_episode_config.load_native_episode_config``, gated on the
# ``native-role-episode`` stop rule) rather than one of the four per-phase
# tables. Its OFF arm (the key absent, ``samples`` defaulting to 1) is
# provably a config-hash twin of today's behaviour
# (``test_native_episode_config.py::
# test_anchor_config_ceiling_is_unchanged_by_the_new_field`` and
# ``test_native_request_grouped_solver.py::
# test_samples_one_ungrouped_adapter_is_unaffected``). The open decision this
# comment used to record is now resolved: harness-admission v3 (Fable E6,
# 2026-09-16) registers a SIXTH switch class, ``episode``, for exactly this
# kind of per-run, non-``run``-class object, on a closed allowlist
# (``rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS``) rather than by widening
# ``CONFIG_TABLE_NAMES`` -- ``native_episode.roles.solver`` is admitted to it
# unchanged, because it was already exactly one key under the generic
# ``switch_key`` algorithm and needed no new expansion or exemption logic
# (contrast M0's ``native_episode.review_loop`` in section 8 above, which
# does).
# ---------------------------------------------------------------------------


def _native_episode_experiment(solver_extra=None):
    roles = {
        name: {"phase_id": name, "max_iterations": 1}
        for name in ("perception", "solver", "reviewer", "planner")
    }
    if solver_extra:
        roles["solver"] = {**roles["solver"], **solver_extra}
    return {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": "e2-grouped-solver-proof",
            "max_revisions": 0,
            "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
            "roles": roles,
        },
    }


def _e2_program(max_contacts):
    from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec

    return PhaseProgram(
        program_id="phase-e2-grouped-solver-proof",
        phases=tuple(
            PhaseSpec(name, name, "none", None, False)
            for name in ("perception", "solver", "reviewer", "planner")
        ),
        max_contacts=max_contacts,
        stop_rule="native-role-episode",
    ).validate()


def test_grouped_solver_sampling_is_one_native_episode_roles_solver_key(tmp_path):
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    off = _compose_arm(tmp_path, "off", {}, experiment=_native_episode_experiment())
    on = _compose_arm(
        tmp_path, "on", {},
        experiment=_native_episode_experiment({
            "samples": 5,
            "decoding_overrides": {"temperature": 0.7, "seed_offset": 0},
            "commit": {
                "policy": "saea-commit-plurality-support-v1",
                "min_support": 3,
                "similarity_threshold": 0.8,
            },
        }),
    )
    assert on.config_hash != off.config_hash
    assert switch_key(on.values, off.values) == "native_episode.roles.solver"

    # perception 1 + (0 + 1) * (reviewer 1 + planner 1 + solver 1) = 4, the
    # historical ceiling, unchanged by this module's OFF arm.
    off_parsed = load_native_episode_config(off.values, _e2_program(4))
    assert off_parsed.max_contacts == 4
    assert off_parsed.role("solver").samples == 1

    # perception 1 + (0 + 1) * (reviewer 1 + planner 1 + solver 1 * 5) = 8.
    on_parsed = load_native_episode_config(on.values, _e2_program(8))
    assert on_parsed.max_contacts == 8
    assert on_parsed.role("solver").samples == 5


def test_grouped_solver_sampling_key_resolves_in_the_episode_class():
    """The class-membership half of the proof: unlike M0's review_loop, this
    key needed no derived-leaves exemption -- it is already exactly one key
    under the generic algorithm (test above), and the episode class's own
    resolver and null-arm rule agree with that."""

    assert (
        resolve_episode_switch_key("native_episode.roles.solver")
        == "native_episode.roles.solver"
    )
    assert is_episode_null_arm("native_episode.roles.solver", None) is True
    assert is_episode_null_arm(
        "native_episode.roles.solver", {"phase_id": "solver", "max_iterations": 1}
    ) is True
    assert is_episode_null_arm(
        "native_episode.roles.solver",
        {
            "phase_id": "solver",
            "max_iterations": 1,
            "samples": 5,
            "decoding_overrides": {"temperature": 0.7, "seed_offset": 0},
            "commit": {
                "policy": "saea-commit-plurality-support-v1",
                "min_support": 3,
                "similarity_threshold": 0.8,
            },
        },
    ) is False
    with pytest.raises(ConfigTableError, match="not admitted"):
        resolve_episode_switch_key("native_episode.roles.reviewer")
    with pytest.raises(ConfigTableError, match="does not start with"):
        resolve_episode_switch_key("roles.solver")


# ---------------------------------------------------------------------------
# 10. exemplar-grounded Solver store (E3, SLURP v2 base program M1) -- the
#     'stores' class's knowledge_stores.<store_id> key (harness-admission
#     v3, Fable E6).
#
# tests/unit/test_e3_exemplar_supply_config_switch.py already proves, on the
# real committed fragments, that adding the train-exemplars store is a
# single JSON top-level 'knowledge_stores' key with a single added child
# key, whose own sub-block's OFF arm reconstructs the pre-module
# knowledge_stores block byte for byte. This section names that shape
# directly through the 'stores' class's own resolver and null-arm rule, so
# the two proofs cannot silently drift apart.
# ---------------------------------------------------------------------------

_E3_ANCHOR = "slurp-native-dual-store-train-fold-a-anchor-v1.json"
_E3_K20 = "slurp-native-dual-store-train-fold-a-exemplars-k20-v1.json"

#: The same bookkeeping top-level keys
#: test_e3_exemplar_supply_config_switch.py's own BOOKKEEPING_KEYS names.
_E3_BOOKKEEPING_KEYS = frozenset({
    "native_contact_fit",
    "speech_feature_key_representation_id",
    "what_this_is",
    "what_the_train_exemplars_store_is",
    "preparation_source_receipts",
})


def _load_baseline_json(name):
    return json.loads((REPO_ROOT / "configs" / "baseline" / name).read_text(encoding="utf-8"))


def test_exemplar_supply_store_key_resolves_in_the_stores_class():
    key = resolve_stores_switch_key("knowledge_stores.train-exemplars")
    assert key == "knowledge_stores.train-exemplars"
    assert is_stores_null_arm(None) is True
    assert is_stores_null_arm({"store_role": "train-exemplars"}) is False
    with pytest.raises(ConfigTableError, match="must be"):
        resolve_stores_switch_key("phase_material.train-exemplars")
    with pytest.raises(ConfigTableError, match="must be"):
        resolve_stores_switch_key("knowledge_stores")
    with pytest.raises(ConfigTableError, match="must be"):
        resolve_stores_switch_key("knowledge_stores.train-exemplars.phase_supply")


def test_exemplar_supply_store_is_the_only_key_moved_on_the_committed_fragments():
    """The same real fragments test_e3_exemplar_supply_config_switch.py
    proves the module's shape on, re-read here through the 'stores' class's
    own resolver rather than by hand."""

    anchor = _load_baseline_json(_E3_ANCHOR)
    k20 = _load_baseline_json(_E3_K20)

    non_bookkeeping_keys = (set(anchor) | set(k20)) - _E3_BOOKKEEPING_KEYS
    differing = sorted(
        key for key in non_bookkeeping_keys if anchor.get(key) != k20.get(key)
    )
    assert differing == ["knowledge_stores"]

    entry_key = resolve_stores_switch_key("knowledge_stores.train-exemplars")
    store_id = entry_key.split(".", 1)[1]
    assert store_id == "train-exemplars"
    assert is_stores_null_arm(anchor["knowledge_stores"].get(store_id)) is True
    assert is_stores_null_arm(k20["knowledge_stores"].get(store_id)) is False



# ---------------------------------------------------------------------------
# 11. Node Context Policy (E8a, 2026-09-17) -- the 'episode' class's THIRD
#     key, native_episode.context_policy.
#
# docs/superpowers/specs/2026-09-17-node-context-policy-design.md section 5
# asks for exactly one switch key, whose OFF arm is level L0. This section is
# the design's own named proof test: the key resolves in the episode class,
# its OFF arm is the key absent / the literal "raw" / an object that is raw at
# every boundary, and its ON arm arms something. The committed anchor fragment
# declares none of it, which is why the anchor's own composed hash is
# unchanged by E8a (pinned in
# tests/unit/test_node_context_policy_runner.py).
# ---------------------------------------------------------------------------


def test_node_context_policy_is_one_episode_class_key():
    from speech_aware_evidence_acquisition.rails.config_tables import (
        EPISODE_LEVEL_SWITCH_KEYS,
    )

    key = "native_episode.context_policy"
    assert key in EPISODE_LEVEL_SWITCH_KEYS
    # The allowlist is CLOSED and this enumeration is its ratchet: admitting a
    # key is a code change with a test, never a receipt edit. The fourth,
    # native_episode.deliver_normaliser, was admitted by E11 (owner directive
    # 26, 2026-09-18), the fifth, native_episode.reviewer_audit, by E12
    # (the same directive, 2026-09-19), the sixth,
    # native_episode.finite_completion_policy, by E13 (2026-09-19, the B7a
    # abort) and the seventh, native_episode.solver_hints, by E14 (owner
    # directive 26 again, 2026-09-19); all four have their own proof, the
    # seventh in tests/unit/test_b8c_solver_hints_config.py. The eighth,
    # native_episode.tool_schema_rendering, was admitted by E17 (2026-09-19,
    # throughput lever L1) and is the first admitted for EFFICIENCY rather
    # than for a capability; its proof is
    # tests/unit/test_e17_constant_tool_rendering.py plus section 12d below.
    # The ninth, native_episode.acquisition, was admitted by E18 (2026-09-19,
    # owner decisions 43 and 44) and is the first that adds a NODE to the
    # graph -- the sixth, Acquisition -- rather than a mode of an existing
    # one; its proof is tests/unit/test_e18_acquisition_node.py. The tenth,
    # native_episode.context_fit_policy, was admitted by E20 (2026-09-19,
    # owner decision 45) and is the SECOND failure-mode key, after E13's:
    # it decides what an over-long request does. Its proof is
    # tests/unit/test_e20_context_fit_policy.py. The eleventh,
    # native_episode.knowledge_index, was admitted by E21 (2026-09-19, owner
    # decisions 48 and 50): it arms the knowledge INDEX in the constant
    # prefix together with the per-row pointer block and bounded expansion
    # that replace today's total rendering of everything retrieved. Its
    # proof is tests/unit/test_e21_knowledge_index.py. The twelfth,
    # native_episode.react_exhaustion_policy, was admitted by item E22
    # (2026-09-19, the ReAct-exhaustion disposition, not the Earnings-22
    # carrier, after the B8b-anchor abort) and is the THIRD failure-mode
    # key: it decides what a tool role's exhausted ReAct loop does. Its
    # proof is tests/unit/test_e22_react_exhaustion.py. The thirteenth,
    # native_episode.reviewer_verdict, was admitted by item E37 (owner
    # decision 84, 2026-09-22): the Reviewer's verdict becomes a closed set
    # of primitives (rails.review_primitives), parsed and recorded as a
    # native_episode_receipt.reviewer_verdicts mark; the verdict is a
    # recommendation, never a route -- the Planner keeps routing authority.
    # Its proof is tests/unit/test_e37_reviewer_verdict.py.
    assert sorted(EPISODE_LEVEL_SWITCH_KEYS) == [
        "native_episode.acquisition",
        "native_episode.context_fit_policy",
        "native_episode.context_policy",
        "native_episode.deliver_normaliser",
        "native_episode.finite_completion_policy",
        "native_episode.knowledge_index",
        "native_episode.react_exhaustion_policy",
        "native_episode.review_loop",
        "native_episode.reviewer_audit",
        "native_episode.reviewer_verdict",
        "native_episode.roles.solver",
        "native_episode.solver_hints",
        "native_episode.tool_schema_rendering",
    ]
    assert resolve_episode_switch_key(key) == key

    # OFF: absent, the literal "raw", or raw at every boundary.
    assert is_episode_null_arm(key, None) is True
    assert is_episode_null_arm(key, "raw") is True
    assert is_episode_null_arm(key, {"level": "raw"}) is True
    assert is_episode_null_arm(
        key, {"level": "raw", "boundaries": {"solver:current-draft": {"level": "raw"}}}
    ) is True
    assert is_episode_null_arm(
        key,
        {
            "level": "structured",
            "boundaries": {
                f"{role}:{semantic}": {"level": "raw"}
                for role, semantic in _slurp_boundaries()
            },
        },
    ) is True

    # ON: anything that arms a boundary above raw.
    assert is_episode_null_arm(key, {"level": "structured"}) is False
    assert is_episode_null_arm(
        key,
        {"level": "raw", "boundaries": {"planner:review-finding": {"level": "structured"}}},
    ) is False

    # A dotted path under native_episode, never a flat run-level key.
    with pytest.raises(ConfigTableError, match="is dotted"):
        resolve_run_switch_key(key)
    with pytest.raises(ConfigTableError, match="does not start with"):
        resolve_episode_switch_key("context_policy")


# ---------------------------------------------------------------------------
# 11b. The delivery-time normaliser node (E11, 2026-09-18, owner directive
#      26) -- the 'episode' class's FOURTH key,
#      native_episode.deliver_normaliser.
#
# It is an episode key rather than a run-level one because it is a NODE of the
# episode, declared inside the native_episode block beside the roles it runs
# after, and it is not a 'judges' TABLE entry because that table wraps a
# phase's phase_review block -- the Reviewer seat, which owner Decision 11-C
# makes criticism-only, and a node that rewrites the delivered answer can
# never be criticism-only. Its OFF arm is simply the key's absence: a delivery
# node is either absent or armed, and the OFF arm renders exactly the pre-key
# delivered bytes (and the pre-key request bytes, since the node runs after
# every contact of the episode is already spent -- pinned in
# tests/unit/test_native_episode_runner_deliver_normaliser.py).
# ---------------------------------------------------------------------------


def test_deliver_normaliser_is_one_episode_class_key():
    key = "native_episode.deliver_normaliser"
    assert resolve_episode_switch_key(key) == key

    # OFF: the key absent. There is no third shape.
    assert is_episode_null_arm(key, None) is True
    # ON: a declared normaliser id.
    assert is_episode_null_arm(key, {"normaliser": "saea-deliver-normalise-v3"}) is False

    # A dotted path under native_episode, never a flat run-level key -- and
    # never the E4 seal-time key, which is the same RULE at a different place.
    with pytest.raises(ConfigTableError, match="is dotted"):
        resolve_run_switch_key(key)
    with pytest.raises(ConfigTableError, match="does not start with"):
        resolve_episode_switch_key("deliver_normaliser")


def test_the_two_b8a_fragments_arm_the_node_and_nothing_else():
    """Cell B8a is one factor: each committed ON fragment differs from the
    base it derives from in native_episode.deliver_normaliser alone, plus the
    bookkeeping identities every derived fragment carries."""

    bookkeeping = {
        "native_contact_fit",
        "scorers",
        "speech_feature_key_representation_id",
        "speech_feature_matcher_policy_id",
        "what_this_is",
    }
    pairs = (
        (
            "slurp-native-dual-store-train-fold-a-anchor-v1",
            "slurp-native-dual-store-train-fold-a-anchor-deliver-normalise-v3-v1",
        ),
        (
            "slurp-native-anchor-exemplars-k20-train-fold-a-recovery-v2",
            "slurp-native-anchor-exemplars-k20-deliver-normalise-v3-train-fold-a-v1",
        ),
    )
    for off_name, on_name in pairs:
        off = _load_baseline_json(f"{off_name}.json")
        on = _load_baseline_json(f"{on_name}.json")
        differing = sorted(
            key
            for key in (set(off) | set(on)) - bookkeeping
            if off.get(key) != on.get(key)
        )
        assert differing == ["native_episode"], (off_name, differing)

        off_episode = dict(off["native_episode"])
        on_episode = dict(on["native_episode"])
        assert on_episode.pop("deliver_normaliser") == {
            "normaliser": "saea-deliver-normalise-v3"
        }
        assert on_episode == off_episode
        assert is_episode_null_arm(
            "native_episode.deliver_normaliser",
            off_episode.get("deliver_normaliser"),
        ) is True
        # The node adds no contact, so neither fragment's ceiling moves.
        assert "slurp_projection_v3_delivery" not in on


# ---------------------------------------------------------------------------
# 11c. The Reviewer slot-audit context block (E12, 2026-09-19, owner directive
#      26) -- the 'episode' class's FIFTH key,
#      native_episode.reviewer_audit.
#
# E19 (2026-09-19, owner decision 32) re-based the block off the Node Context
# Policy L1 stack after cell B7a v2 read it HARMFUL. The KEY'S ADMISSIBLE
# SHAPE DID NOT CHANGE -- same fields, same OFF form, same closed allowlist --
# only what the block is appended to: an L1 rendering where a policy declares
# one, the sealed draft bytes where none is declared. That is why this ratchet
# is unchanged by E19 and why the key's proof moved to
# tests/unit/test_b8b_anchor_reviewer_audit_config.py beside the E12 one.
#
# It is an episode key rather than a run-level one because it MOVES REQUEST
# BYTES at one boundary by design, so no request-bytes-identical falsifier can
# exist for it; and it is not one of the four per-phase tables because it is
# not what a phase observes, is supplied with, is judged by or may call -- it
# is an analysis rendered into the context an EARLIER node's output is read
# in. It is a second key rather than a field of native_episode.context_policy
# because a cell that moves the audit must be distinguishable from a cell that
# moves the policy.
# ---------------------------------------------------------------------------


def test_reviewer_audit_is_one_episode_class_key():
    key = "native_episode.reviewer_audit"
    assert resolve_episode_switch_key(key) == key

    # OFF: the key absent. There is no third shape.
    assert is_episode_null_arm(key, None) is True
    # ON: the declared view, its two pins and its optional thresholds.
    armed = {
        "view": "slot-audit-v1",
        "release": {
            "relpath": "knowledge/slurp/semantic/slot-audit-v1/release.json",
            "sha256": SHA,
        },
        "snapshot": {
            "relpath": "knowledge/slurp/semantic/slot-audit-v1/snapshot.json",
            "sha256": SHA,
        },
    }
    assert is_episode_null_arm(key, armed) is False
    assert is_episode_null_arm(key, {**armed, "thresholds": {}}) is False

    # A dotted path under native_episode, never a flat run-level key.
    with pytest.raises(ConfigTableError, match="is dotted"):
        resolve_run_switch_key(key)
    with pytest.raises(ConfigTableError, match="does not start with"):
        resolve_episode_switch_key("reviewer_audit")


def test_the_two_b8b_fragments_arm_the_block_and_nothing_else():
    """Cell B8b is one factor: each committed ON fragment differs from cell
    B7r's base in native_episode.reviewer_audit alone, plus the bookkeeping
    identities every derived fragment carries and one harness-robustness key.

    native_episode.finite_completion_policy (coordinator, 2026-09-19, after the
    B7a recovery arm aborted on a Reviewer completion that hit the 512-token
    cap) is NOT a switch-class key and NOT a factor: it renders no request
    byte, is consumed only by rails.runner's NativeEpisodeSpec, and only
    decides whether a finite completion aborts the flight or retains the row.
    It is asserted here by name so it cannot be confused with the factor.
    """

    bookkeeping = {
        "native_contact_fit",
        # the coordinator's re-pin rebuilds the prepared supply under the
        # cell's own run id (output asserted byte-identical by the tool), so
        # the pin is per-cell bookkeeping once a cell is flipped
        "prepared_phase_supply",
        "scorers",
        "speech_feature_key_representation_id",
        "speech_feature_matcher_policy_id",
        "what_this_is",
    }
    pairs = (
        (
            "slurp-native-anchor-ncp-l1-reviewer-format-train-fold-a-v1",
            "slurp-native-anchor-ncp-l1-reviewer-audit-train-fold-a-v1",
        ),
        (
            "slurp-native-anchor-ncp-l1-reviewer-format-smoke-4-v1",
            "slurp-native-anchor-ncp-l1-reviewer-audit-smoke-4-v1",
        ),
    )
    for off_name, on_name in pairs:
        off = _load_baseline_json(f"{off_name}.json")
        on = _load_baseline_json(f"{on_name}.json")
        differing = sorted(
            key
            for key in (set(off) | set(on)) - bookkeeping
            if off.get(key) != on.get(key)
        )
        assert differing == ["native_episode"], (off_name, differing)

        off_episode = dict(off["native_episode"])
        on_episode = dict(on["native_episode"])
        armed = on_episode.pop("reviewer_audit")
        assert armed["view"] == "slot-audit-v1"
        # Since 0011fdee (2026-09-19) the B7r base carries the same
        # finite-completion policy as every queued SLURP native cell, so the
        # key is not part of the B8b factor: both sides arm it identically.
        assert on_episode.pop("finite_completion_policy") == "deliver-latest-or-abstain"
        assert off_episode.pop("finite_completion_policy") == "deliver-latest-or-abstain"
        assert on_episode == off_episode
        assert is_episode_null_arm(
            "native_episode.reviewer_audit", off_episode.get("reviewer_audit")
        ) is True
        # The block makes no contact, so neither fragment's ceiling moves, and
        # the boundary it attaches to is the one the base already declares at
        # level 'structured'.
        assert off_episode["context_policy"]["boundaries"][
            "reviewer:current-draft"
        ]["level"] == "structured"

        # Both pins name real committed bytes, and their hashes are the bytes'.
        for field_name in ("release", "snapshot"):
            pin = armed[field_name]
            path = REPO_ROOT / pin["relpath"]
            assert path.is_file(), pin["relpath"]
            import hashlib

            assert hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]


def _slurp_boundaries():
    from speech_aware_evidence_acquisition.rails.node_context_policy import (
        SLURP_BOUNDARY_IDS,
    )

    return sorted(SLURP_BOUNDARY_IDS)


def test_the_committed_anchor_declares_no_context_policy():
    anchor = _load_baseline_json(_E3_ANCHOR)
    assert "context_policy" not in anchor["native_episode"]
    assert is_episode_null_arm(
        "native_episode.context_policy",
        anchor["native_episode"].get("context_policy"),
    ) is True


# ---------------------------------------------------------------------------
# 12. date/time slot-contract revision (E9 / cell B4b, SLURP v2 base program
#     module M4b) -- the 'stores' class's SECOND arm form, the store RE-PIN.
#
# Section 10 above proves the class's FIRST form on a module that ADDS a
# store: OFF is the store's absence. M4b is the other thing a store module
# can be -- a REVISION of a store the comparator already carries -- and
# docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md left exactly one
# point open about it: its OFF arm is not the store's absence but the anchor's
# own v1 pin, so the null form cannot express it honestly. This is the proof
# node id such an entry cites: on the two REAL committed fragments, the switch
# is one top-level key, one store inside it and the two pinned leaves inside
# that store -- release and snapshot -- and nothing else moves.
# ---------------------------------------------------------------------------

_B4B_ANCHOR_V2 = "slurp-native-anchor-slot-store-v2-train-fold-a-v2.json"

#: Bookkeeping, set aside exactly as section 10 sets aside its own: free-
#: English prose, the cell's speech-feature identity ids and its per-cell
#: preparation/fit receipts. None of it is the module.
_B4B_BOOKKEEPING_KEYS = frozenset({
    "native_contact_fit",
    "preparation_source_receipts",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "what_this_is",
})

#: DERIVED rather than bookkeeping, and named as such: the prepared phase-
#: supply artifact IS the pinned store's content materialized before the
#: flight, so re-pinning the store necessarily re-prepares it. The review-loop
#: proof sets aside the leaves its marker derives from in the same way and for
#: the same reason -- a derived consequence of the one key is not a second key.
_B4B_DERIVED_KEYS = frozenset({"prepared_phase_supply"})


def test_the_stores_repin_form_is_one_key():
    anchor = _load_baseline_json(_E3_ANCHOR)
    revised = _load_baseline_json(_B4B_ANCHOR_V2)

    entry_key = resolve_stores_switch_key("knowledge_stores.slot-contracts")
    store_id = entry_key.split(".", 1)[1]
    assert store_id == "slot-contracts"

    # One top-level key, once bookkeeping and the derived supply artifact are
    # set aside.
    compared = (set(anchor) | set(revised)) - _B4B_BOOKKEEPING_KEYS - _B4B_DERIVED_KEYS
    differing = sorted(key for key in compared if anchor.get(key) != revised.get(key))
    assert differing == ["knowledge_stores"]

    # One store inside that key -- the other store is byte-identical.
    stores_off, stores_on = anchor["knowledge_stores"], revised["knowledge_stores"]
    assert sorted(stores_off) == sorted(stores_on)
    moved = sorted(name for name in stores_on if stores_off.get(name) != stores_on.get(name))
    assert moved == [store_id]

    # Two leaves inside that store, and they are the class's two pin leaves:
    # store_role, candidate_supply and every other field stay put.
    off_block, on_block = stores_off[store_id], stores_on[store_id]
    moved_leaves = sorted(
        field
        for field in set(off_block) | set(on_block)
        if off_block.get(field) != on_block.get(field)
    )
    assert moved_leaves == sorted(STORES_PIN_FIELDS) == ["release", "snapshot"]

    # Neither arm is the class's NULL arm; both are RE-PIN arms; they differ.
    off, on = stores_pins(anchor, store_id), stores_pins(revised, store_id)
    assert is_stores_null_arm(off_block) is False
    assert is_stores_null_arm(on_block) is False
    assert is_stores_repin_arm(off) is True
    assert is_stores_repin_arm(on) is True
    assert off != on
    assert off["release"]["relpath"].endswith("slot-contracts-v1/release.json")
    assert off["snapshot"]["relpath"].endswith("slot-contracts-v1/snapshot.json")
    assert on["release"]["relpath"].endswith("slot-contracts-v2/release.json")
    assert on["snapshot"]["relpath"].endswith("slot-contracts-v2/snapshot.json")

    # The question a plan-arming rule asks, answered in both directions: the
    # ON pins arm the module, the OFF pins do not, and neither does a fragment
    # that carries no such store.
    assert stores_arm_matches(revised, store_id, on) is True
    assert stores_arm_matches(revised, store_id, off) is False
    assert stores_arm_matches(anchor, store_id, off) is True
    assert stores_arm_matches(anchor, store_id, on) is False
    without = {
        "knowledge_stores": {
            name: block for name, block in stores_on.items() if name != store_id
        }
    }
    assert stores_arm_matches(without, store_id, on) is False
    assert stores_arm_matches(without, store_id, None) is True
    assert stores_arm_matches(revised, store_id, None) is False

    # The FIRST form is not loosened by the second: absence is still the null
    # arm, a re-pin arm is still not one, and an arm that moves anything
    # besides the two pins is not a re-pin at all.
    assert is_stores_null_arm(None) is True
    assert is_stores_repin_arm(None) is False
    assert is_stores_repin_arm(on_block) is False
    assert is_stores_repin_arm({**on, "store_role": store_id}) is False
    assert is_stores_repin_arm({"release": on["release"]}) is False
    assert is_stores_repin_arm(
        {"release": on["release"], "snapshot": {"relpath": "a/b.json", "sha256": "nope"}}
    ) is False
    assert is_stores_repin_arm(
        {
            "release": on["release"],
            "snapshot": {"relpath": "/absolute/b.json", "sha256": on["snapshot"]["sha256"]},
        }
    ) is False


def test_finite_completion_policy_is_one_episode_class_key():
    """E13 (2026-09-19): the finite-completion switch, and its two OFF spellings.

    The B7a recovery arm aborted because one Reviewer completion came back with
    ``finish_reason`` ``length`` and the SLURP baselines never declared this
    key, so the parser's default ``"raise"`` turned a retained row into a
    flight abort. Admitting the key here is what lets the harness-admission
    receipt record the switch, and what lets
    ``scripts/checks/finite_completion_policy_check.py`` demand it of every
    unflown native cell.

    The key is an ``episode``-class key, never a ``run``-class one, although it
    renders no request byte: it is read inside the episode's own role chain,
    is declared inside the ``native_episode`` block, and its ON arm is
    therefore composed -- not proved absent by a falsifier receipt.
    """

    from speech_aware_evidence_acquisition.rails.config_tables import (
        EPISODE_LEVEL_SWITCH_KEYS,
    )

    key = "native_episode.finite_completion_policy"
    assert key in EPISODE_LEVEL_SWITCH_KEYS
    assert resolve_episode_switch_key(key) == key

    # OFF: the key absent, or its explicit default written out loud. The
    # parser reads the two identically, so both compose the pre-E13 episode.
    assert is_episode_null_arm(key, None) is True
    assert is_episode_null_arm(key, "raise") is True
    # ON: the one armed value the parser accepts.
    assert is_episode_null_arm(key, "deliver-latest-or-abstain") is False

    # One key, one leaf: the arms differ in exactly ``native_episode.
    # finite_completion_policy`` and in nothing else.
    off = {
        "schema": "saea-native-episode-config-v1",
        "episode_id": "e13-proof-v1",
        "max_revisions": 1,
        "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
        "roles": {
            kind: {"phase_id": kind, "max_iterations": 3 if kind == "reviewer" else 1}
            for kind in ("perception", "solver", "reviewer", "planner")
        },
    }
    on = {**off, "finite_completion_policy": "deliver-latest-or-abstain"}
    assert set(on) - set(off) == {"finite_completion_policy"}
    assert {k: v for k, v in on.items() if k != "finite_completion_policy"} == off


# ---------------------------------------------------------------------------
# 12d. Constant native tool-schema rendering (E17, 2026-09-19, throughput
#      lever L1) -- the 'episode' class's EIGHTH key,
#      native_episode.tool_schema_rendering, and the first admitted for
#      EFFICIENCY rather than for a capability.
#
# It is an episode key rather than a run-level one because it MOVES REQUEST
# BYTES on the tool-free roles by design, so no request-bytes-identical
# falsifier can exist for it; and it is not the phase_tools table because that
# table is what a phase MAY CALL -- tool AUTHORITY, which this key leaves
# exactly as it is. Rendering is not authority.
#
# The module proof (loader, request builder, production render path, the
# refusal path and the receipt) is
# tests/unit/test_e17_constant_tool_rendering.py.
# ---------------------------------------------------------------------------


def test_tool_schema_rendering_is_one_episode_class_key():
    key = "native_episode.tool_schema_rendering"
    assert resolve_episode_switch_key(key) == key

    # OFF: the key absent, or its explicit default written out loud. The
    # parser reads the two identically, so both compose the pre-E17 episode.
    assert is_episode_null_arm(key, None) is True
    assert is_episode_null_arm(key, "per-role") is True
    # ON: the one armed value the parser accepts.
    assert is_episode_null_arm(key, "constant") is False

    # A dotted path under native_episode, never a flat run-level key.
    with pytest.raises(ConfigTableError, match="is dotted"):
        resolve_run_switch_key(key)
    with pytest.raises(ConfigTableError, match="does not start with"):
        resolve_episode_switch_key("tool_schema_rendering")


def test_the_tool_schema_rendering_arms_differ_in_exactly_one_leaf():
    off = {
        "schema": "saea-native-episode-config-v1",
        "episode_id": "e17-proof-v1",
        "max_revisions": 1,
        "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
        "roles": {
            kind: {"phase_id": kind, "max_iterations": 3 if kind == "reviewer" else 1}
            for kind in ("perception", "solver", "reviewer", "planner")
        },
    }
    on = {**off, "tool_schema_rendering": "constant"}
    assert set(on) - set(off) == {"tool_schema_rendering"}
    assert {k: v for k, v in on.items() if k != "tool_schema_rendering"} == off


# ---------------------------------------------------------------------------
# Item E25 (2026-09-20): the 'phase_tools' switch class -- one role's toolkit.
#
# Cell B1-notool's module is the WITHDRAWAL of the Reviewer's task-contract
# tool. This is the entry's own named proof: the key resolves in the class,
# its OFF arm is the role's null arm, its ON arm is the toolkit mapping, and
# the two committed fragments (B1r's, which carried the toolkit, and the flown
# tool-free one) differ in phase_tools alone once the fit receipt, the
# prepared-supply binding, the what_this_is prose and the E22 failure-mode
# declaration -- armed on every cell registered after 2026-09-19 -- are set
# aside as bookkeeping and derived keys.
# ---------------------------------------------------------------------------

_E25_ON = "slurp-native-anchor-exemplars-k20-replicate-v1.json"
_E25_OFF = "slurp-native-anchor-exemplars-k20-notool-v1.json"
_E25_BOOKKEEPING_KEYS = frozenset({
    "native_contact_fit",
    "prepared_phase_supply",
    "what_this_is",
})
_E25_DERIVED_EPISODE_KEYS = frozenset({"react_exhaustion_policy"})


def test_the_reviewer_toolkit_withdrawal_is_one_phase_tools_key():
    from speech_aware_evidence_acquisition.rails.config_tables import (
        PHASE_TOOLS_SWITCH_CLASS,
        SWITCH_CLASS_NAMES,
        is_phase_tools_null_arm,
        phase_tools_role_armed,
        resolve_phase_tools_switch_key,
    )

    assert PHASE_TOOLS_SWITCH_CLASS == "phase_tools"
    # The eighth class (E25); the ninth, 'module', was appended by migration
    # step 6 of the consumption module (2026-09-30).
    assert SWITCH_CLASS_NAMES[7] == PHASE_TOOLS_SWITCH_CLASS
    assert resolve_phase_tools_switch_key("phase_tools.reviewer") == "phase_tools.reviewer"
    for bad in ("phase_tools", "phase_tools.", "phase_tools.<phase>", "toolkits.reviewer",
                "phase_tools.reviewer.mode", "", None):
        with pytest.raises(ConfigTableError):
            resolve_phase_tools_switch_key(bad)
    assert is_phase_tools_null_arm(None) is True
    assert is_phase_tools_null_arm({}) is True
    assert is_phase_tools_null_arm({"mode": "native-tools"}) is False
    assert is_phase_tools_null_arm("none") is False

    on = _load_baseline_json(_E25_ON)
    off = _load_baseline_json(_E25_OFF)
    assert phase_tools_role_armed(on, "phase_tools.reviewer") is True
    assert phase_tools_role_armed(off, "phase_tools.reviewer") is False
    assert "phase_tools" not in off
    assert on["phase_tools"]["reviewer"]["allowed_tools"] == ["saea-tool-task-contract-v1"]

    non_bookkeeping = (set(on) | set(off)) - _E25_BOOKKEEPING_KEYS
    differing = sorted(key for key in non_bookkeeping if on.get(key) != off.get(key))
    assert differing == ["native_episode", "phase_tools"]
    episode_on = {k: v for k, v in on["native_episode"].items() if k not in _E25_DERIVED_EPISODE_KEYS}
    episode_off = {k: v for k, v in off["native_episode"].items() if k not in _E25_DERIVED_EPISODE_KEYS}
    assert episode_on == episode_off
    assert off["native_episode"]["react_exhaustion_policy"] == "continue-without-answer"
    assert "react_exhaustion_policy" not in on["native_episode"]
