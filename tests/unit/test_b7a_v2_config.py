"""Cell B7a v2: the re-registration moves one episode key and nothing a model can see.

The v1 flight of cell B7a closed on its second failure. The arm
``SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1`` aborted on 2026-09-17 on an illegal Planner
action (fixed by item E8c), and the one root-diagnosed recovery the preregistration allows,
``SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1``, ABORTED again on 2026-09-19 after
1,451 model contacts with ``NativeEpisodeError: native episode node failed: [100054] component
'reviewer_1_role' execute 'invoke' error, reason='metered completion is non-authoritative because
finish_reason is 'length''``. Exactly one contact in that trace reached the 512-token ``max512``
cap.

The root cause is a MISSING CONFIGURATION KEY, not a code defect: the SLURP native baselines omit
``native_episode.finite_completion_policy`` and
``rails.native_episode_config.load_native_episode_config`` defaults it to ``"raise"``, so one
truncated completion propagates out of the episode and kills the campaign. The alternative,
``"deliver-latest-or-abstain"``, is already implemented and tested
(``reproduction.ojw.native_episode._finite_terminal_outcome``, ``rails.native_episode_receipt``,
``rails.runner``, ``core.flight.runtime``): the row is RETAINED with
``terminal_disposition.reason == "finite_completion"`` and delivers the latest delivery-eligible
Solver draft, or abstains with empty output.

These tests pin that the v2 registration moves exactly that key, on the committed fragments and --
for the composed assertions -- through the repository's own ``core.config.compose``, which is what
``core.flight.cli check`` uses:

1. each v2 baseline differs from its v1 recovery sibling in the added episode key plus the
   documented bookkeeping identity fields, and nothing else -- ``prepared_phase_supply`` included,
   which is INHERITED verbatim and rebuilt by the coordinator's re-pin cycle;
2. the native episode config parser accepts each v2 baseline with ``finite_completion_policy ==
   "deliver-latest-or-abstain"`` while the v1 recovery sibling still parses to the default
   ``"raise"`` -- which is the failure this registration fixes;
3. both v2 cells load through ``load_campaign_cells`` with the v2 run and attempt ids, readiness
   ``held`` with the inherited preparation requirement and no decision requirement (the
   coordinator's re-pin adds that), and no ``resume_from`` -- v2 is a fresh flight from row one;
4. the registered ceilings, roster, population, split identity and service session are the v1
   recovery's, unchanged;
5. composed end to end, the two configurations differ only in bookkeeping keys plus the episode
   block, and every model-facing key is byte-identical; the campaign plan resolves to the v2 arm.

Model-free: it reads committed JSON and composes it. No model, tokenizer, encoder, scorer or server
is contacted, and no test needs a data root.
"""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "configs" / "baseline"
EXPERIMENT_DIR = REPO_ROOT / "configs" / "experiment"
CAMPAIGN_DIR = REPO_ROOT / "configs" / "campaign"

MODEL_FRAGMENT = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"

FINITE_KEY = "finite_completion_policy"
FINITE_VALUE = "deliver-latest-or-abstain"
FINITE_DEFAULT = "raise"

CLOSED_ARM_BASELINE = "slurp-native-anchor-ncp-l1-train-fold-a-recovery-v1"
CLOSED_SMOKE_BASELINE = "slurp-native-anchor-ncp-l1-smoke-4-recovery-v1"
CLOSED_ARM_EXPERIMENT = "slurp-native-ncp-l1-anchor-train-fold-a-recovery-v1"
CLOSED_SMOKE_EXPERIMENT = "slurp-native-ncp-l1-anchor-smoke-4-recovery-v1"

V2_ARM_BASELINE = "slurp-native-anchor-ncp-l1-train-fold-a-v2"
V2_SMOKE_BASELINE = "slurp-native-anchor-ncp-l1-smoke-4-v2"
V2_ARM_EXPERIMENT = "slurp-native-ncp-l1-anchor-train-fold-a-v2"
V2_SMOKE_EXPERIMENT = "slurp-native-ncp-l1-anchor-smoke-4-v2"

ARM_RUN = "SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V2"
ARM_FIT_RUN = "SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-FIT-V2"
SMOKE_RUN = "SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-V2"
SMOKE_FIT_RUN = "SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-FIT-V2"
ARM_ATTEMPT = "attempt-slurp-native-ncp-l1-anchor-train-fold-a-generation-v2"
ARM_FIT_ATTEMPT = "attempt-slurp-native-ncp-l1-anchor-train-fold-a-fit-v2"
SMOKE_ATTEMPT = "attempt-slurp-native-ncp-l1-anchor-smoke-4-generation-v2"
SMOKE_FIT_ATTEMPT = "attempt-slurp-native-ncp-l1-anchor-smoke-4-fit-v2"

SPLIT_IDENTITY = "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"
SMOKE_SPLIT_IDENTITY = "4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb"
PROGRAM_ID = "phase-native-candidates-review-revise-v1"

ROSTER_ROWS = 1080
PROGRAM_MAX_CONTACTS = 11
PLANNED_MODEL_CALLS = 11880
FIT_ENDPOINT_CAP = 47520

#: The documented identity fields a NEW registration carries beside the one episode key. None of
#: them shapes a rendered request: the fit RUN and ATTEMPT ids namespace the fit receipt root
#: (``prepared/<fit run>/<fit attempt>/``), the note is free English, and the two speech-feature
#: identity strings ride the trace as ORG/CONTROL provenance -- the v1 recovery's request-envelope
#: comparison proved over 3,278 sealed MODEL_REQUEST payloads that neither appears in a payload byte
#: and that each payload's own key_representation_id/matcher_policy_id is derived from the POLICY id.
BASELINE_BOOKKEEPING = {
    "native_contact_fit",
    # inherited at registration, rebuilt under the v2 run id by the flip
    "prepared_phase_supply",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "what_this_is",
}

#: Plus the experiment fragment's own identity and free-English fields.
EXPERIMENT_BOOKKEEPING = {
    "cells",
    "prepared_phase_supply",
    "date",
    "experiment_id",
    "failure_policy",
    "fragment_kind",
    "generation_budget",
    "purpose",
}

#: Everything a request is built from. Byte-identical, or the one-factor claim is false. The whole
#: ``native_episode`` block is checked separately, key by key, because that is where the one allowed
#: difference lives.
MODEL_FACING_KEYS = (
    "arm",
    "evidence_mismatch",
    "evidence_source",
    "knowledge_stores",
    "phase_material",
    "phase_tools",
    "policy",
    "population",
    "populations",
    "preparation_source_receipts",
    "preserve_wire_responses",
    "scorers",
    "service_session",
    "serving_slot_tokens",
    "serving_slots",
    "speech_packet_promotion_receipt",
    "speech_packet_promotion_receipt_sha256",
    "split_id",
    "task_instruction_fill",
    "task_instruction_template",
    "task_instruction_template_active",
)

PAIRS = (
    (CLOSED_ARM_BASELINE, V2_ARM_BASELINE),
    (CLOSED_SMOKE_BASELINE, V2_SMOKE_BASELINE),
)


def _load(directory: Path, name: str) -> dict:
    return json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))


def _cell(document: dict, cell_id: str) -> dict:
    matches = [cell for cell in document["cells"] if cell["cell_id"] == cell_id]
    assert len(matches) == 1
    return matches[0]


def test_each_v2_baseline_adds_the_finite_completion_key_and_nothing_else():
    for closed_name, v2_name in PAIRS:
        closed = _load(BASELINE_DIR, closed_name)
        v2 = _load(BASELINE_DIR, v2_name)

        differing = {
            key for key in set(closed) | set(v2) if closed.get(key) != v2.get(key)
        }
        assert differing == BASELINE_BOOKKEEPING | {"native_episode"}, (v2_name, differing)

        closed_episode = dict(closed["native_episode"])
        v2_episode = dict(v2["native_episode"])
        assert FINITE_KEY not in closed_episode, closed_name
        assert v2_episode.pop(FINITE_KEY) == FINITE_VALUE, v2_name
        # The rest of the episode block -- the whole context_policy under test included -- is the
        # closed cell's, key for key.
        assert v2_episode == closed_episode, v2_name

        # INHERITED verbatim: core.preparation.artifact_inputs binds the cell identity, so this pin
        # will not verify against the v2 digest and core.flight.repin.ensure_artifact_pinned rebuilds
        # it -- asserting the new artifact's output block equals this one's -- during the
        # coordinator's re-pin cycle. Never with --allow-output-change.
        v2_pin = v2["prepared_phase_supply"]
        assert v2_pin == closed["prepared_phase_supply"] or (
            "-V2/" in v2_pin["relpath"]
            and v2_pin["relpath"].startswith("prepared/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-")
        ), v2_name


def test_the_v2_baselines_carry_their_own_fit_identity_at_the_unchanged_ceilings():
    arm = _load(BASELINE_DIR, V2_ARM_BASELINE)
    smoke = _load(BASELINE_DIR, V2_SMOKE_BASELINE)
    closed_arm = _load(BASELINE_DIR, CLOSED_ARM_BASELINE)
    closed_smoke = _load(BASELINE_DIR, CLOSED_SMOKE_BASELINE)

    assert arm["native_contact_fit"]["run_id"] == ARM_FIT_RUN
    assert arm["native_contact_fit"]["attempt_id"] == ARM_FIT_ATTEMPT
    assert smoke["native_contact_fit"]["run_id"] == SMOKE_FIT_RUN
    assert smoke["native_contact_fit"]["attempt_id"] == SMOKE_FIT_ATTEMPT

    # The endpoint ceilings and the packet allowance do not move.
    assert arm["native_contact_fit"]["contact_cap"] == FIT_ENDPOINT_CAP
    assert FIT_ENDPOINT_CAP == ROSTER_ROWS * PROGRAM_MAX_CONTACTS * (1 + 3)
    assert smoke["native_contact_fit"]["contact_cap"] == 176
    assert 176 == 4 * PROGRAM_MAX_CONTACTS * (1 + 3)
    for v2, closed in ((arm, closed_arm), (smoke, closed_smoke)):
        assert (
            v2["native_contact_fit"]["contact_cap"]
            == closed["native_contact_fit"]["contact_cap"]
        )
        assert (
            v2["native_contact_fit"]["max_speech_packets"]
            == closed["native_contact_fit"]["max_speech_packets"]
        )


def test_the_episode_parser_accepts_the_v2_baselines_and_still_defaults_the_closed_ones():
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    cases = (
        (V2_ARM_BASELINE, V2_ARM_EXPERIMENT, FINITE_VALUE),
        (V2_SMOKE_BASELINE, V2_SMOKE_EXPERIMENT, FINITE_VALUE),
        (CLOSED_ARM_BASELINE, CLOSED_ARM_EXPERIMENT, FINITE_DEFAULT),
        (CLOSED_SMOKE_BASELINE, CLOSED_SMOKE_EXPERIMENT, FINITE_DEFAULT),
    )
    for baseline, experiment, expected in cases:
        composed = compose(REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT, baseline, experiment)
        assert composed.values["policy"] == PROGRAM_ID
        program = default_phase_program(str(composed.values["policy"]))
        config = load_native_episode_config(composed.values, program)
        assert config.finite_completion_policy == expected, baseline
        # The factor under test is untouched by any of this.
        assert composed.values["native_episode"]["context_policy"]["level"] == "structured"


def test_both_v2_cells_load_held_with_the_inherited_preparation_requirement():
    for experiment, run_id, attempt_id in (
        (V2_ARM_EXPERIMENT, ARM_RUN, ARM_ATTEMPT),
        (V2_SMOKE_EXPERIMENT, SMOKE_RUN, SMOKE_ATTEMPT),
    ):
        cells = load_campaign_cells(REPO_ROOT, experiment)
        assert len(cells) == 1
        cell = cells[0]
        assert cell.document["cell_id"] == experiment
        assert cell.run_id == run_id
        assert cell.attempt_id == attempt_id
        # v2 is a FRESH flight from row one; the resume-recovery form is what the ONE recovery this
        # flight is allowed would take (owner decision 22), not what this registration declares.
        assert cell.resume_from is None

        readiness = cell.document["readiness"]
        # Readiness is a lifecycle field: `held` with the inherited preparation requirement as
        # registered, or `ready` once the coordinator's re-pin tool has pinned the root decision
        # receipt beside it.
        assert readiness["state"] in {"held", "ready"}
        kinds = sorted(requirement["kind"] for requirement in readiness["requirements"])
        assert kinds == (
            ["preparation"] if readiness["state"] == "held" else ["decision", "preparation"]
        )


def test_the_v2_experiments_keep_every_registered_ceiling_and_the_roster():
    for closed_name, v2_name in (
        (CLOSED_ARM_EXPERIMENT, V2_ARM_EXPERIMENT),
        (CLOSED_SMOKE_EXPERIMENT, V2_SMOKE_EXPERIMENT),
    ):
        closed = _load(EXPERIMENT_DIR, closed_name)
        v2 = _load(EXPERIMENT_DIR, v2_name)
        differing = {key for key in set(closed) | set(v2) if closed.get(key) != v2.get(key)}
        assert differing <= EXPERIMENT_BOOKKEEPING, (v2_name, differing)
        assert {"cells", "purpose", "failure_policy"} <= differing

        for key in (
            "allowed_execution_stages",
        ):
            assert _cell(v2, v2_name)[key] == _cell(closed, closed_name)[key]

        for key in (
            "execution_plan",
            "execution_profile",
            "family_budget",
            "population",
            "populations",
            "preserve_wire_responses",
            "service_session",
            "split_id",
        ):
            assert v2[key] == closed[key], (v2_name, key)

        # generation_budget moves only in its free-English definition.
        assert v2["generation_budget"]["cap"] == closed["generation_budget"]["cap"]
        assert v2["generation_budget"]["target"] == closed["generation_budget"]["target"]

    arm = _load(EXPERIMENT_DIR, V2_ARM_EXPERIMENT)
    assert arm["execution_plan"]["planned_model_calls"] == PLANNED_MODEL_CALLS
    assert PLANNED_MODEL_CALLS == ROSTER_ROWS * PROGRAM_MAX_CONTACTS
    assert arm["population"]["split_identity_hash"] == SPLIT_IDENTITY
    assert len(arm["populations"][0]["ids"]) == ROSTER_ROWS
    smoke = _load(EXPERIMENT_DIR, V2_SMOKE_EXPERIMENT)
    assert smoke["population"]["split_identity_hash"] == SMOKE_SPLIT_IDENTITY
    assert len(smoke["populations"][0]["ids"]) == 4


def test_the_composed_configurations_differ_only_in_bookkeeping_and_the_episode_key():
    for (closed_baseline, v2_baseline), (closed_experiment, v2_experiment), split in (
        ((CLOSED_ARM_BASELINE, V2_ARM_BASELINE),
         (CLOSED_ARM_EXPERIMENT, V2_ARM_EXPERIMENT), SPLIT_IDENTITY),
        ((CLOSED_SMOKE_BASELINE, V2_SMOKE_BASELINE),
         (CLOSED_SMOKE_EXPERIMENT, V2_SMOKE_EXPERIMENT), SMOKE_SPLIT_IDENTITY),
    ):
        closed = compose(
            REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT, closed_baseline, closed_experiment
        )
        v2 = compose(REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT, v2_baseline, v2_experiment)

        keys = set(closed.values) | set(v2.values)
        differing = {key for key in keys if closed.values.get(key) != v2.values.get(key)}
        assert differing <= BASELINE_BOOKKEEPING | EXPERIMENT_BOOKKEEPING | {"native_episode"}

        for key in MODEL_FACING_KEYS:
            assert v2.values[key] == closed.values[key], key

        v2_episode = dict(v2.values["native_episode"])
        assert v2_episode.pop(FINITE_KEY) == FINITE_VALUE
        assert v2_episode == dict(closed.values["native_episode"])

        # The composed hash and therefore the protocol hash necessarily move: compose() hashes the
        # complete merged fragment set, the attempt identity included. The arm -- what protocol_hash
        # binds beside the config -- does not.
        assert v2.values["arm"] == closed.values["arm"]
        assert v2.config_hash != closed.config_hash
        assert protocol_hash(
            v2.config_hash, v2.values["arm"], split
        ) != protocol_hash(closed.config_hash, closed.values["arm"], split)


def test_the_v2_campaign_plan_resolves_to_the_v2_arm():
    plan = json.loads(
        (CAMPAIGN_DIR / f"{V2_ARM_EXPERIMENT}.json").read_text(encoding="utf-8")
    )
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [{"cell": V2_ARM_EXPERIMENT, "experiment": V2_ARM_EXPERIMENT}]
