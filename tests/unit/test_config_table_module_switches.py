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
    ConfigTableError,
    config_key_diff,
    is_run_null_arm,
    load_config_tables,
    resolve_run_switch_key,
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
    the request the core sees belongs in a config table."""

    assert set(RUN_LEVEL_SWITCH_KEYS) == {"obs_prefetch_depth"}
    assert resolve_run_switch_key("obs_prefetch_depth") == "obs_prefetch_depth"
    for refused in ("obs_batch_slices", "obs_boundary_mode", "obs_buffer_seconds"):
        with pytest.raises(ConfigTableError, match="closed allowlist"):
            resolve_run_switch_key(refused)
    with pytest.raises(ConfigTableError, match="is dotted"):
        resolve_run_switch_key("run.obs_prefetch_depth")


# ---------------------------------------------------------------------------
# 8. E1 review loop off (M0) -- not expressible as one switch key today
#
# The module's own channel (docs/superpowers/specs/2026-09-16-slurp-v2-base-
# program-design.md section 3, row M0) is native_episode.max_revisions 0 +
# reviewer/planner max_iterations 0 TOGETHER: three leaves under
# native_episode that share no common dotted prefix (max_revisions is a
# direct child; roles.reviewer.max_iterations and roles.planner.max_iterations
# share only "native_episode.roles", not with max_revisions). switch_key's
# own shared-prefix walk refuses this by construction -- measured below,
# not asserted from opinion.
#
# It is not a spelling defect fixable by moving the fields around, either.
# The run class requires a FLAT (undotted) top-level key on a closed
# allowlist (resolve_run_switch_key rejects any dot on sight), and
# native_episode is a required, structured block for this program -- there
# is no flat top-level spelling of "the review loop", and no absent/0
# default the way obs_prefetch_depth has one, because native_episode itself
# can never be dropped for a native-role-episode program. None of the four
# per-phase tables (judges/knowledge_views/observe/toolkits) models episode
# role-graph iteration counts either; they change what the frozen core
# observes, is supplied, is judged on, or may call, not how many times an
# agent role runs. So this module stays a "run"-less, table-less registered
# switch, like the window hook above: expressible and tested, not yet a
# harness-admission switch class.
# ---------------------------------------------------------------------------


def test_review_loop_off_switch_moves_three_native_episode_keys_today():
    """Measured, not asserted. E1 (rails.native_episode_config,
    reproduction.ojw.native_episode, rails.runner) makes the shape legal and
    NativeEpisodeConfig.review_loop_enabled the single reliable witness of
    it, but the two committed baseline fragments below are not one switch
    key -- this pins exactly what moves, so a future wave that lifts this
    into a class starts from a known diff, not an opinion."""

    on = _committed_baseline("slurp-native-dual-store-train-fold-a-anchor-v1")
    off = _committed_baseline("slurp-native-dual-store-train-fold-a-review-off-v1")

    diff = config_key_diff(on, off)
    assert diff == (
        "native_contact_fit.attempt_id",
        "native_contact_fit.contact_cap",
        "native_contact_fit.run_id",
        "native_episode.max_revisions",
        "native_episode.roles.planner.max_iterations",
        "native_episode.roles.reviewer.max_iterations",
        "phase_tools.reviewer.allowed_tools",
        "phase_tools.reviewer.knowledge_views",
        "phase_tools.reviewer.mode",
        "phase_tools.reviewer.source_authority_role",
        "policy",
        "speech_feature_key_representation_id",
        "speech_feature_matcher_policy_id",
        "what_this_is",
    )
    with pytest.raises(ConfigTableError, match="unrelated config keys"):
        switch_key(on, off)

    # Restricted to the native_episode block alone -- the module's actual
    # mechanism, with the bookkeeping fields (policy id, tool removal,
    # contact-fit cap, speech-feature identity, what_this_is) set aside --
    # the three moved leaves still share no common prefix, so even that
    # narrower view is not one key.
    episode_diff = config_key_diff(on["native_episode"], off["native_episode"])
    assert episode_diff == (
        "max_revisions",
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


# 9. grouped-Solver sampling (E2, SLURP v2 base program M2) -- documented as
# NEITHER a per-phase table entry NOR a ``run``-class flat key.
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
# test_samples_one_ungrouped_adapter_is_unaffected``). This is recorded here
# as an open decision for the coordinator/owner: either register a sixth
# switch class for a per-run, non-``run``-class object (a schema bump, v3,
# to ``docs/receipts/harness-admission.json``, not made by this change), or
# accept ``native_episode.roles.solver`` as this module's one-key home
# without adding it to ``rails.config_tables.CONFIG_TABLE_NAMES``.
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

