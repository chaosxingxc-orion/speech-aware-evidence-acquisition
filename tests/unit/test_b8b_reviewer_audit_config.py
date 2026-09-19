"""Cell B8b config-switch proof: the Reviewer slot-audit block on the B7r base.

Cell B8b (owner directive 26 of 2026-09-18; item E12, 2026-09-19) turns on
exactly one thing against cell B7r's configuration: the ``episode``-class key
``native_episode.reviewer_audit``, armed with the released construction view
``slot-audit-v1``, its two committed pins and its thresholds. The block makes
no contact, so the contact ceiling and every budget stay B7r's; it renders at
ONE boundary, so every other request byte stays B7r's too.

These tests pin exactly that, on the committed fragments and on the COMPOSED
configuration:

1. the four-row smoke baseline is the B8b arm baseline apart from its own FIT
   identity (the 4 x 11 x 4 = 176 endpoint ceiling) and its note;
2. against cell B7r's baselines, the only key that moves is
   ``native_episode``, and inside it the only keys that move are
   ``reviewer_audit`` -- the factor -- and ``finite_completion_policy``, the
   harness-robustness key the coordinator added on 2026-09-19 after the B7a
   recovery arm aborted on a Reviewer completion that hit the 512-token cap.
   The second key is NOT a factor: it renders no request byte and only decides
   what the harness does when a completion comes back with ``finish_reason``
   ``length`` -- ``raise`` aborts the flight, ``deliver-latest-or-abstain``
   retains the row with a ``finite_completion`` terminal disposition;
3. the armed pins name real committed bytes and hash to them;
4. dropping the one key reconstructs B7r's own ``native_episode`` block;
5. the composed configuration loads with the block armed, and the loader
   refuses it by name on the wrong carrier. Item E19 (2026-09-19, owner
   decision 32) re-based the block off this L1 stack, so the boundary level
   is no longer a refusal: it RESOLVES an attachment. These sealed L1 bytes
   still parse and still take the ``l1-rendering`` attachment, which is the
   no-regression half of E19; the ``sealed-draft`` half is proved in
   ``tests/unit/test_b8b_anchor_reviewer_audit_config.py``;
6. both experiment fragments are registered ``held`` with no decision
   requirement, at B7r's own roster and budgets.

Model-free: committed JSON, the repository's own ``core.config.compose``, and
no model, tokenizer, encoder, scorer, server or network contact.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "configs" / "baseline"
EXPERIMENT_DIR = REPO_ROOT / "configs" / "experiment"

MODEL_FRAGMENT = (
    "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
)
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"

B7R_ARM = "slurp-native-anchor-ncp-l1-reviewer-format-train-fold-a-v1"
B7R_SMOKE_BASELINE = "slurp-native-anchor-ncp-l1-reviewer-format-smoke-4-v1"
B7R_SMOKE_EXPERIMENT = "slurp-native-ncp-l1-reviewer-format-anchor-smoke-4-v1"

B8B_ARM = "slurp-native-anchor-ncp-l1-reviewer-audit-train-fold-a-v1"
B8B_SMOKE_BASELINE = "slurp-native-anchor-ncp-l1-reviewer-audit-smoke-4-v1"
B8B_ARM_EXPERIMENT = "slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-v1"
B8B_SMOKE_EXPERIMENT = "slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1"

REVIEWER_AUDIT_KEY = "reviewer_audit"

#: The harness-robustness key added beside the factor (coordinator, 2026-09-19).
#: It is consumed only by ``rails.runner``'s ``NativeEpisodeSpec`` and reaches
#: no template, no prompt and no request.
FINITE_COMPLETION_KEY = "finite_completion_policy"
FINITE_COMPLETION_VALUE = "deliver-latest-or-abstain"

#: Bookkeeping-only top-level keys: run/attempt identity, the provenance-only
#: speech-feature ids and free-English notes. None shapes a rendered request.
BOOKKEEPING_KEYS = frozenset({
    "native_contact_fit",
    # re-pinned per cell by the coordinator's flip (the tool rebuilds the
    # prepared supply under the cell's own run id, output byte-identical)
    "prepared_phase_supply",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "what_this_is",
})


def _load_baseline(name: str) -> dict:
    return json.loads((BASELINE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _load_experiment(name: str) -> dict:
    return json.loads((EXPERIMENT_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _compose(baseline: str, experiment: str):
    from speech_aware_evidence_acquisition.core.config import compose

    return compose(str(REPO_ROOT), MODEL_FRAGMENT, DATASET_FRAGMENT, baseline, experiment)


def test_the_smoke_baseline_is_the_arm_baseline_plus_bookkeeping_only():
    arm = _load_baseline(B8B_ARM)
    smoke = _load_baseline(B8B_SMOKE_BASELINE)
    non_bookkeeping = (set(arm) | set(smoke)) - BOOKKEEPING_KEYS
    differing = sorted(
        key for key in non_bookkeeping if arm.get(key) != smoke.get(key)
    )
    # The two differ only in the prepared-supply pin their own roster needs
    # (bookkeeping above); every substantive key is shared.
    assert differing == []
    assert smoke["prepared_phase_supply"]["relpath"].startswith("prepared/SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-")
    assert smoke["native_contact_fit"]["contact_cap"] == 176
    assert arm["native_contact_fit"]["contact_cap"] == 47520
    assert arm["native_episode"][REVIEWER_AUDIT_KEY] == (
        smoke["native_episode"][REVIEWER_AUDIT_KEY]
    )
    assert arm["native_episode"][FINITE_COMPLETION_KEY] == (
        smoke["native_episode"][FINITE_COMPLETION_KEY]
    ) == FINITE_COMPLETION_VALUE


@pytest.mark.parametrize(
    "off_name,on_name",
    [(B7R_ARM, B8B_ARM), (B7R_SMOKE_BASELINE, B8B_SMOKE_BASELINE)],
    ids=["arm", "smoke"],
)
def test_the_only_keys_that_move_against_b7r_are_the_audit_and_the_finite_policy(
    off_name, on_name
):
    off = _load_baseline(off_name)
    on = _load_baseline(on_name)
    comparable = (set(off) | set(on)) - BOOKKEEPING_KEYS
    assert sorted(key for key in comparable if off.get(key) != on.get(key)) == [
        "native_episode"
    ]
    # Named one by one so a regression cannot hide behind the set comparison.
    for key in (
        "arm",
        "knowledge_stores",
        "phase_material",
        "phase_tools",
        "policy",
        "scorers",
        "serving_slot_tokens",
        "serving_slots",
        "task_instruction_fill",
        "task_instruction_template",
        "task_instruction_template_active",
    ):
        assert off[key] == on[key], key

    off_episode = off["native_episode"]
    on_episode = on["native_episode"]
    assert sorted(
        key
        for key in set(off_episode) | set(on_episode)
        if off_episode.get(key) != on_episode.get(key)
    ) == [REVIEWER_AUDIT_KEY]
    assert REVIEWER_AUDIT_KEY not in off_episode

    # The harness-robustness key is the registered non-default value on BOTH
    # sides: since 0011fdee (2026-09-19) the B7r base arms it too, so it is
    # not part of the factor and the diff is the audit block alone.
    assert on_episode[FINITE_COMPLETION_KEY] == FINITE_COMPLETION_VALUE
    assert off_episode[FINITE_COMPLETION_KEY] == FINITE_COMPLETION_VALUE

    stripped = copy.deepcopy(on_episode)
    stripped.pop(REVIEWER_AUDIT_KEY)
    assert stripped == off_episode


def test_the_armed_block_pins_the_released_view_by_its_committed_bytes():
    from speech_aware_evidence_acquisition.rails.slot_audit import SLOT_AUDIT_VIEW_ID

    armed = _load_baseline(B8B_ARM)["native_episode"][REVIEWER_AUDIT_KEY]
    assert armed["view"] == SLOT_AUDIT_VIEW_ID
    assert set(armed) == {"view", "release", "snapshot", "thresholds"}
    for field_name in ("release", "snapshot"):
        pin = armed[field_name]
        path = REPO_ROOT / pin["relpath"]
        assert path.is_file(), pin["relpath"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]
    assert armed["thresholds"] == {
        "empty_draft_min_entity_row_share": 0.5,
        "missing_common_min_row_share": 0.5,
        "profile_min_row_share": 0.05,
    }


def test_the_base_keeps_the_reviewer_draft_boundary_at_l1():
    """The block is an ADDITION to that boundary's L1 rendering, so the base it
    is armed on must declare it structured -- checked on the committed bytes,
    not only in the loader."""

    boundaries = _load_baseline(B8B_ARM)["native_episode"]["context_policy"][
        "boundaries"
    ]
    assert boundaries["reviewer:current-draft"] == {
        "level": "structured",
        "template": "probes/ncp_slurp_current_draft_reviewer_v1.txt",
        "on_parse_failure": "raw",
    }


def test_the_composed_smoke_loads_a_native_episode_with_the_block_armed():
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    values = _compose(B8B_SMOKE_BASELINE, B8B_SMOKE_EXPERIMENT).values
    config = load_native_episode_config(
        values, default_phase_program(str(values["policy"]))
    )
    assert config.reviewer_audit_json is not None
    assert json.loads(config.reviewer_audit_json)["view"] == "slot-audit-v1"

    off_values = _compose(B7R_SMOKE_BASELINE, B7R_SMOKE_EXPERIMENT).values
    off_config = load_native_episode_config(
        off_values, default_phase_program(str(off_values["policy"]))
    )
    assert off_config.reviewer_audit_json is None
    # The block adds no contact, so the bounded ceiling does not move.
    assert config.max_contacts == off_config.max_contacts == 11
    assert config.episode_id == off_config.episode_id
    assert config.context_policy_json == off_config.context_policy_json
    # The harness-robustness key loads as the registered value; the base keeps
    # the module default. It is carried on the episode SPEC, never rendered.
    assert config.finite_completion_policy == FINITE_COMPLETION_VALUE
    assert off_config.finite_completion_policy == FINITE_COMPLETION_VALUE
def test_the_loader_refuses_the_block_on_another_carrier_and_resolves_its_attachment():
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    values = _compose(B8B_SMOKE_BASELINE, B8B_SMOKE_EXPERIMENT).values
    program = default_phase_program(str(values["policy"]))

    wrong_carrier = copy.deepcopy(dict(values))
    wrong_carrier["carrier_lock_key"] = "audio2tool"
    with pytest.raises(ValueError, match="defined for carrier 'slurp'"):
        load_native_episode_config(wrong_carrier, program)

    # E19: what used to be two refusals is now the attachment resolution.
    # These committed L1 bytes keep the E12 attachment; the same key on a
    # raw boundary, or with no policy declared at all, takes the sealed-draft
    # attachment instead of being refused.
    from speech_aware_evidence_acquisition.rails.node_context_binding import (
        reviewer_audit_boundary_attachment,
    )
    from speech_aware_evidence_acquisition.rails.node_context_policy import (
        SLOT_AUDIT_ATTACHMENT_L1,
        SLOT_AUDIT_ATTACHMENT_RAW,
    )

    config = load_native_episode_config(copy.deepcopy(dict(values)), program)
    assert reviewer_audit_boundary_attachment(config.context_policy_json) == (
        SLOT_AUDIT_ATTACHMENT_L1
    )

    raw_boundary = copy.deepcopy(dict(values))
    raw_boundary["native_episode"]["context_policy"]["boundaries"][
        "reviewer:current-draft"
    ] = {"level": "raw"}
    raw_config = load_native_episode_config(raw_boundary, program)
    assert raw_config.reviewer_audit_json is not None
    assert reviewer_audit_boundary_attachment(
        raw_config.context_policy_json
    ) == SLOT_AUDIT_ATTACHMENT_RAW

    no_policy = copy.deepcopy(dict(values))
    no_policy["native_episode"].pop("context_policy")
    bare = load_native_episode_config(no_policy, program)
    assert bare.context_policy_json is None
    assert bare.reviewer_audit_json is not None
    assert reviewer_audit_boundary_attachment(None) == SLOT_AUDIT_ATTACHMENT_RAW


@pytest.mark.parametrize(
    "name,run_id,stages",
    [
        (
            B8B_SMOKE_EXPERIMENT,
            "SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1",
            ["check", "prepare-supply", "worker"],
        ),
        (
            B8B_ARM_EXPERIMENT,
            "SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1",
            ["check", "prepare-supply", "worker", "campaign"],
        ),
    ],
    ids=["smoke", "arm"],
)
def test_both_experiment_fragments_are_registered_held(name, run_id, stages):
    experiment = _load_experiment(name)
    (cell,) = experiment["cells"]
    state = cell["readiness"]["state"]
    # Held: no decision requirement yet. Ready: the coordinator's re-pin
    # appended and pinned the root decision receipt. Superseded (owner
    # decision 32, 2026-09-19): the L1 base read HARMFUL, so this
    # registration closed and the block returns on the anchor base through
    # a new package; the requirements stay as they were at closure.
    assert state in {"held", "ready", "superseded"}
    kinds = [entry["kind"] for entry in cell["readiness"]["requirements"]]
    assert "preparation" in kinds and set(kinds) <= {"decision", "preparation"}
    if state == "held":
        assert kinds == ["preparation"]
    assert cell["run_id"] == run_id
    assert cell["allowed_execution_stages"] == stages
    assert experiment["execution_profile"] == "bounded-discovery-probe"
    assert experiment["service_session"] == (
        "serving-slurp-native-candidate-five-train-a-np4-v1"
    )
    assert experiment["date"] == "2026-09-19"


def test_the_arm_keeps_b7rs_roster_and_budgets_because_it_adds_no_contact():
    on = _load_experiment(B8B_ARM_EXPERIMENT)
    off = _load_experiment("slurp-native-ncp-l1-reviewer-format-anchor-train-fold-a-v1")
    assert on["populations"] == off["populations"]
    assert on["population"]["split_identity_hash"] == (
        off["population"]["split_identity_hash"]
    )
    assert on["split_id"] == off["split_id"]
    assert on["family_budget"] == off["family_budget"]
    assert on["execution_plan"] == off["execution_plan"]
    assert on["generation_budget"]["cap"] == off["generation_budget"]["cap"]


def test_the_smoke_flies_the_same_four_rows_every_form_smoke_of_this_roster_flies():
    smoke = _load_experiment(B8B_SMOKE_EXPERIMENT)
    b7r_smoke = _load_experiment(B7R_SMOKE_EXPERIMENT)
    assert smoke["populations"] == b7r_smoke["populations"]
    assert smoke["population"]["split_identity_hash"] == (
        b7r_smoke["population"]["split_identity_hash"]
    )
    assert smoke["family_budget"] == b7r_smoke["family_budget"]
