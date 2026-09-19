"""Efficiency cell EFF-1 config proof: constant tool rendering on the sealed anchor.

Cell EFF-1 (owner decision 41 of 2026-09-19; item E17, merged at ``d6fade1e``)
turns on exactly one thing against the SEALED dual-store anchor's configuration:
the ``episode``-class key ``native_episode.tool_schema_rendering``, armed
``"constant"``. Its PURPOSE is throughput -- prefilled prompt tokens per row and
GPU hours per 1,080 rows -- and its ADMISSION RULE is NEUTRAL on the official
number.

These tests pin exactly that, on the committed fragments, on the COMPOSED
configuration and on the production render path:

1. the four-row smoke baseline is the EFF-1 arm baseline apart from bookkeeping
   (its own FIT identity with the 4 x 11 x 4 = 176 endpoint ceiling, its own
   prepared-supply pin and its note);
2. against the sealed anchor's baseline the only key that moves is
   ``native_episode``, and inside it exactly two keys move:
   ``tool_schema_rendering`` -- the factor -- and ``finite_completion_policy``,
   which is NOT a factor. The second renders no request byte and is required of
   every live SLURP native cell by
   ``scripts/checks/finite_completion_policy_check.py`` (item E13); the sealed
   anchor flew without it and
   ``docs/receipts/slurp-finite-completion-exposure-v1.json`` proves zero finite
   completions on it, so the comparator side is provably unaffected;
3. dropping the two keys reconstructs the anchor's own ``native_episode`` block;
4. the composed configuration parses ``tool_schema_rendering == "constant"`` and
   names the Reviewer's own single ordered array as the constant one, while the
   anchor parses the ``"per-role"`` default and no constant array;
5. under the production render path with a FAKE model, a Reviewer contact is
   byte-identical between the anchor arm and the EFF-1 arm, and perception,
   solver and planner differ in exactly the added ``tools`` key with
   ``tool_choice`` still ``"none"`` -- rendering widened, authority not;
6. both experiment fragments are registered ``held``, at the anchor's own roster
   and at the registered ceilings, and the campaign plan names the arm.

Model-free: committed JSON, the repository's own ``core.config.compose``, the
real OpenJiuwen role graph over the shared fake transport, and no model,
tokenizer, encoder, scorer, server or network contact.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

# The live-process fixture the session identity rail (I5) needs when the real
# ``rails.runner`` runs against the shared fake transport.
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "configs" / "baseline"
EXPERIMENT_DIR = REPO_ROOT / "configs" / "experiment"
CAMPAIGN_DIR = REPO_ROOT / "configs" / "campaign"

MODEL_FRAGMENT = (
    "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
)
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"

ANCHOR_BASELINE = "slurp-native-dual-store-train-fold-a-anchor-v1"
ANCHOR_EXPERIMENT = "slurp-native-dual-store-train-fold-a-anchor-recovery-v1"
ANCHOR_RECOVERY_BASELINE = "slurp-native-dual-store-train-fold-a-anchor-recovery-v1"

EFF1_ARM_BASELINE = "slurp-native-anchor-tool-constant-train-fold-a-v1"
EFF1_SMOKE_BASELINE = "slurp-native-anchor-tool-constant-smoke-4-v1"
EFF1_ARM_EXPERIMENT = "slurp-native-tool-constant-anchor-train-fold-a-v1"
EFF1_SMOKE_EXPERIMENT = "slurp-native-tool-constant-anchor-smoke-4-v1"

#: The factor. Its OFF arm is the key's ABSENCE, which is the anchor's own
#: configuration (``rails.config_tables.is_episode_null_arm``).
RENDERING_KEY = "tool_schema_rendering"
RENDERING_ON = "constant"

#: The harness declaration beside it. Not a factor: it renders no request byte.
FINITE_COMPLETION_KEY = "finite_completion_policy"
FINITE_COMPLETION_VALUE = "deliver-latest-or-abstain"

TASK_CONTRACT_TOOL_NAME = "saea-tool-task-contract-v1"

#: Bookkeeping-only top-level keys: run/attempt identity, the provenance-only
#: speech-feature ids and free-English notes. None shapes a rendered request.
BOOKKEEPING_KEYS = frozenset({
    "native_contact_fit",
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


# ---------------------------------------------------------------------------
# 1. The committed fragments: one factor, plus one declaration that is not one.
# ---------------------------------------------------------------------------


def test_the_smoke_baseline_is_the_arm_baseline_plus_bookkeeping_only():
    arm = _load_baseline(EFF1_ARM_BASELINE)
    smoke = _load_baseline(EFF1_SMOKE_BASELINE)

    non_bookkeeping = (set(arm) | set(smoke)) - BOOKKEEPING_KEYS
    assert sorted(key for key in non_bookkeeping if arm.get(key) != smoke.get(key)) == []

    # The smoke's only reason to exist is that the full cell's FIT and
    # generation accounting is never charged smoke contacts.
    assert arm["native_contact_fit"]["contact_cap"] == 47520
    assert smoke["native_contact_fit"]["contact_cap"] == 176
    assert smoke["native_contact_fit"]["run_id"] == (
        "SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-SMOKE-4-FIT-V1"
    )
    assert arm["native_contact_fit"]["run_id"] == (
        "SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-TRAIN-FOLD-A-FIT-V1"
    )
    # Each cell pins its OWN prepared supply, so the re-pin tool finds the pin
    # valid, rebuilds nothing, and adds nothing to assert_no_residue's scan.
    assert arm["prepared_phase_supply"]["relpath"] == (
        "prepared/SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-TRAIN-FOLD-A-V1/phase-supply-v1.json"
    )
    assert smoke["prepared_phase_supply"]["relpath"] == (
        "prepared/SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-SMOKE-4-V1/phase-supply-v1.json"
    )
    assert arm["prepared_phase_supply"] != smoke["prepared_phase_supply"]


@pytest.mark.parametrize("on_name", [EFF1_ARM_BASELINE, EFF1_SMOKE_BASELINE], ids=["arm", "smoke"])
def test_the_only_keys_that_move_against_the_anchor_are_the_two_episode_keys(on_name):
    off = _load_baseline(ANCHOR_BASELINE)
    on = _load_baseline(on_name)

    comparable = (set(off) | set(on)) - BOOKKEEPING_KEYS
    assert sorted(key for key in comparable if off.get(key) != on.get(key)) == [
        "native_episode"
    ]

    # Named one by one so a regression cannot hide behind the set comparison.
    for key in (
        "arm",
        "evidence_mismatch",
        "evidence_source",
        "knowledge_stores",
        "phase_material",
        "phase_tools",
        "policy",
        "preparation_source_receipts",
        "scorers",
        "serving_slot_tokens",
        "serving_slots",
        "speech_packet_promotion_receipt",
        "speech_packet_promotion_receipt_sha256",
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
    ) == [FINITE_COMPLETION_KEY, RENDERING_KEY]

    # The factor, and the anchor's OFF arm is the key's ABSENCE.
    assert on_episode[RENDERING_KEY] == RENDERING_ON
    assert RENDERING_KEY not in off_episode

    # Not a factor: the harness declaration item E13's gate requires of every
    # live SLURP native cell. The sealed anchor flew without it.
    assert on_episode[FINITE_COMPLETION_KEY] == FINITE_COMPLETION_VALUE
    assert FINITE_COMPLETION_KEY not in off_episode

    stripped = copy.deepcopy(on_episode)
    stripped.pop(RENDERING_KEY)
    stripped.pop(FINITE_COMPLETION_KEY)
    assert stripped == off_episode


def test_the_base_is_node_free_and_keeps_reviewer_only_tool_authority():
    """The anchor base carries no node: no context policy, no delivery
    normaliser, no reviewer audit. And the Reviewer is the only tool-bearing
    role, which is what makes the constant array equal to its own array."""

    for name in (ANCHOR_BASELINE, EFF1_ARM_BASELINE, EFF1_SMOKE_BASELINE):
        doc = _load_baseline(name)
        episode = doc["native_episode"]
        for absent in ("context_policy", "deliver_normaliser", "reviewer_audit"):
            assert absent not in episode, (name, absent)
        assert set(doc["phase_tools"]) == {"reviewer"}
        assert doc["phase_tools"]["reviewer"]["allowed_tools"] == [TASK_CONTRACT_TOOL_NAME]
        assert doc["phase_tools"]["reviewer"]["mode"] == "native-tools"


# ---------------------------------------------------------------------------
# 2. The composed configuration parses the armed value.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "baseline,experiment",
    [(EFF1_ARM_BASELINE, EFF1_ARM_EXPERIMENT), (EFF1_SMOKE_BASELINE, EFF1_SMOKE_EXPERIMENT)],
    ids=["arm", "smoke"],
)
def test_the_composed_cell_parses_constant_rendering(baseline, experiment):
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    values = _compose(baseline, experiment).values
    config = load_native_episode_config(values, default_phase_program(str(values["policy"])))

    assert config.tool_schema_rendering == RENDERING_ON
    # The union IS the one tool-bearing role's own ordered array, so that
    # role's request is byte-identical to the per-role arm's.
    assert config.constant_tool_names == (TASK_CONTRACT_TOOL_NAME,)
    assert config.role("reviewer").tool_names == (TASK_CONTRACT_TOOL_NAME,)
    for role_id in ("perception", "solver", "planner"):
        assert config.role(role_id).tool_names == ()
    assert config.finite_completion_policy == FINITE_COMPLETION_VALUE

    off_values = _compose(ANCHOR_RECOVERY_BASELINE, ANCHOR_EXPERIMENT).values
    off_config = load_native_episode_config(
        off_values, default_phase_program(str(off_values["policy"]))
    )
    assert off_config.tool_schema_rendering == "per-role"
    assert off_config.constant_tool_names is None
    # The key adds no contact: the bounded ceiling does not move.
    assert config.max_contacts == off_config.max_contacts == 11
    assert config.episode_id == off_config.episode_id


# ---------------------------------------------------------------------------
# 3. The production render path: the Reviewer bytes do not move.
# ---------------------------------------------------------------------------

#: The five contacts of one row, in the order the pinned slot sees them.
CONTACT_KEYS = (
    ("s1", "perception", 1, 1),
    ("s1", "solver", 1, 1),
    ("s1", "reviewer", 1, 1),
    ("s1", "reviewer", 1, 2),
    ("s1", "planner", 1, 1),
)
TOOL_FREE_KEYS = (CONTACT_KEYS[0], CONTACT_KEYS[1], CONTACT_KEYS[4])
TOOL_BEARING_KEYS = (CONTACT_KEYS[2], CONTACT_KEYS[3])


def _rendered_bodies(tmp_path, *, rendering):
    """One row through the real role graph and the real render path."""

    from test_native_episode_runner import _ActualEpisodeHarness

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=5,
        planner_actions=("ACCEPT",),
        reviewer_task_tool=True,
    )
    harness.config = replace(harness.config, tool_schema_rendering=rendering)
    try:
        summary = harness.run()
    finally:
        harness.close()
    assert set(harness.prepared) == set(CONTACT_KEYS), sorted(harness.prepared)
    return {key: harness.prepared[key]["rendered"] for key in CONTACT_KEYS}, summary


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_reviewer_request_is_byte_identical_and_only_tools_is_added(tmp_path):
    """The EFF-1 cell's parsed rendering mode against the anchor's, driven
    through the production transport with a fake model.

    This is the wire-side proof ``core.flight.cli wire-check`` cannot make for
    a native-episode cell: the tool-BEARING role's bytes do not move at all,
    and the three tool-FREE roles differ in exactly the added ``tools`` array
    with ``tool_choice`` still ``"none"`` -- rendering widened, authority not.
    """

    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    # The two modes come from the two CELLS, not from literals.
    on_values = _compose(EFF1_ARM_BASELINE, EFF1_ARM_EXPERIMENT).values
    off_values = _compose(ANCHOR_RECOVERY_BASELINE, ANCHOR_EXPERIMENT).values
    on_mode = load_native_episode_config(
        on_values, default_phase_program(str(on_values["policy"]))
    ).tool_schema_rendering
    off_mode = load_native_episode_config(
        off_values, default_phase_program(str(off_values["policy"]))
    ).tool_schema_rendering
    assert (off_mode, on_mode) == ("per-role", "constant")

    off, _off_summary = _rendered_bodies(tmp_path / "anchor", rendering=off_mode)
    on, on_summary = _rendered_bodies(tmp_path / "eff1", rendering=on_mode)

    # The role that already carried the array is untouched, byte for byte.
    for key in TOOL_BEARING_KEYS:
        assert on[key] == off[key], key
        assert on[key]["tool_choice"] == "auto"

    # The three tool-free contacts differ in exactly one key: the added array.
    for key in TOOL_FREE_KEYS:
        assert "tools" not in off[key], key
        assert {k: v for k, v in on[key].items() if k != "tools"} == off[key], key
        assert on[key]["tool_choice"] == "none"
        assert off[key]["tool_choice"] == "none"

    # One rendered array over the whole row -- the constancy the cell measures.
    assert len({json.dumps(on[key]["tools"], sort_keys=True) for key in CONTACT_KEYS}) == 1

    receipt = on_summary.results[0].native_episode_receipt["tool_schema_rendering"]
    assert receipt["schema"] == "saea-native-tool-schema-rendering-v1"
    assert receipt["mode"] == RENDERING_ON
    assert receipt["distinct_tool_schemas_sha256"] == 1


# ---------------------------------------------------------------------------
# 4. The experiment fragments, as registered.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,run_id,stages",
    [
        (
            EFF1_SMOKE_EXPERIMENT,
            "SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-SMOKE-4-V1",
            ["check", "prepare-supply", "worker"],
        ),
        (
            EFF1_ARM_EXPERIMENT,
            "SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-TRAIN-FOLD-A-V1",
            ["check", "prepare-supply", "worker", "campaign"],
        ),
    ],
    ids=["smoke", "arm"],
)
def test_both_experiment_fragments_are_registered_held(name, run_id, stages):
    experiment = _load_experiment(name)
    (cell,) = experiment["cells"]
    state = cell["readiness"]["state"]
    assert state in {"held", "ready"}
    # Held: this cell's own preparation requirement and nothing else.
    # Ready: the coordinator's re-pin appended and pinned the decision receipt.
    assert [entry["kind"] for entry in cell["readiness"]["requirements"]] == (
        ["preparation"] if state == "held" else ["decision", "preparation"]
    )
    assert cell["run_id"] == run_id
    assert cell["allowed_execution_stages"] == stages
    assert experiment["execution_profile"] == "bounded-discovery-probe"
    assert experiment["service_session"] == (
        "serving-slurp-native-candidate-five-train-a-np4-v1"
    )
    assert experiment["date"] == "2026-09-19"


def test_the_arm_keeps_the_anchors_roster_and_the_registered_ceilings():
    """The key adds no contact, so every ceiling is the registered SLURP
    ceiling and the roster is the anchor's own 1,080 rows."""

    arm = _load_experiment(EFF1_ARM_EXPERIMENT)
    assert arm["population"]["count"] == 1080
    assert arm["population"]["split_identity_hash"] == (
        "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"
    )
    assert arm["split_id"] == "SLURP-EVO-FOLD-A-V2"
    assert len(arm["populations"][0]["ids"]) == 1080
    assert arm["family_budget"] == {
        "asr_calls": 0,
        "ceilings_are_not_targets": True,
        "encoder_calls": 0,
        "fit_endpoint_calls_cap": 47520,
        "generation_calls_cap": 11880,
        "gpu_hours_fit_inclusive": 12.0,
        "native_task_contract_calls_cap": 6480,
        "official_complete_scoring_jobs": 1,
        "repeated_speech_audio_seconds_cap": 33930,
    }
    assert arm["generation_budget"]["cap"] == 11880


def test_the_smoke_flies_the_four_rows_every_form_smoke_of_this_roster_flies():
    smoke = _load_experiment(EFF1_SMOKE_EXPERIMENT)
    reference = _load_experiment("slurp-native-ncp-l1-anchor-smoke-4-v2")
    assert smoke["populations"] == reference["populations"]
    assert smoke["population"]["split_identity_hash"] == (
        reference["population"]["split_identity_hash"]
    )
    assert smoke["family_budget"] == reference["family_budget"]
    # All four smoke rows are members of the arm's 1,080-row roster, which is
    # what makes the sealed anchor's own trace their byte comparator.
    arm_ids = set(_load_experiment(EFF1_ARM_EXPERIMENT)["populations"][0]["ids"])
    assert set(smoke["populations"][0]["ids"]) <= arm_ids


def test_the_campaign_plan_names_the_arm_and_only_the_arm():
    plan = json.loads(
        (CAMPAIGN_DIR / f"{EFF1_ARM_EXPERIMENT}.json").read_text(encoding="utf-8")
    )
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [
        {"cell": EFF1_ARM_EXPERIMENT, "experiment": EFF1_ARM_EXPERIMENT}
    ]
