"""Cell B1r config proof: the request-identical replicate of the exemplar-supply cell.

Cell B1r (owner decision 37 of 2026-09-19) changes **nothing** against the
sealed cell B1 recovery arm
(``SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2``, study
commit ``a35630c0``). It is a *replicate*: the single thing that moves between
the two passes is batch composition under greedy decoding. What a registration
can still get wrong is exactly what these tests pin, on the committed
fragments, on the COMPOSED configuration and on the production render path:

1. the four-row smoke baseline is the B1r arm baseline apart from bookkeeping
   (its own FIT identity with the 4 x 11 x 4 = 176 endpoint ceiling, its own
   two speech-feature identity ids, its own prepared-supply pin and its note);
2. against cell B1's own baselines the only key that moves is
   ``native_episode``, and inside it exactly one key:
   ``finite_completion_policy``, which is NOT a factor. It renders no request
   byte and is required of every live SLURP native cell by
   ``scripts/checks/finite_completion_policy_check.py`` (item E13); cell B1
   flew without it and ``docs/receipts/slurp-finite-completion-exposure-v1.json``
   proves zero finite completions on it, so the comparator side is provably
   unaffected. Dropping the key reconstructs cell B1's own ``native_episode``;
3. ``native_episode.tool_schema_rendering`` (item E17) is ABSENT from both
   fragments and the composed cell parses the ``"per-role"`` default. Request
   identity with cell B1 requires per-role rendering, so B1r is a PER-ROLE
   cell and is unaffected by efficiency cell EFF-1's outcome;
4. under the production render path with a FAKE model, every contact of a row
   is byte-identical between cell B1's finite-completion policy and cell B1r's
   -- the declared key moves no request byte at all;
5. the train-exemplars store block, the module under replication, is
   byte-identical to cell B1's, and so is every other model-facing key;
6. both experiment fragments are registered ``held``, on cell B1's own roster,
   at cell B1's own registered ceilings, and the campaign plan names the arm.

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

# Cell B1, sealed: the arm this cell replicates, and its own four-row smoke.
B1_ARM_BASELINE = "slurp-native-anchor-exemplars-k20-train-fold-a-recovery-v2"
B1_SMOKE_BASELINE = "slurp-native-anchor-exemplars-k20-smoke-4-recovery-v2"
B1_ARM_EXPERIMENT = "slurp-native-exemplars-k20-anchor-train-fold-a-recovery-v2"
B1_SMOKE_EXPERIMENT = "slurp-native-exemplars-k20-anchor-smoke-4-recovery-v2"

# Cell B1r, this registration.
B1R_ARM_BASELINE = "slurp-native-anchor-exemplars-k20-replicate-v1"
B1R_SMOKE_BASELINE = "slurp-native-anchor-exemplars-k20-replicate-smoke-4-v1"
B1R_ARM_EXPERIMENT = "slurp-native-exemplars-k20-anchor-replicate-v1"
B1R_SMOKE_EXPERIMENT = "slurp-native-exemplars-k20-anchor-replicate-smoke-4-v1"

#: The one declared key cell B1 did not carry. NOT a factor: it renders no
#: request byte. Its OFF arm is the key's absence, which IS cell B1's
#: configuration (``rails.config_tables.is_episode_null_arm``).
FINITE_COMPLETION_KEY = "finite_completion_policy"
FINITE_COMPLETION_VALUE = "deliver-latest-or-abstain"
FINITE_COMPLETION_DEFAULT = "raise"

#: Item E17's efficiency switch, which this cell deliberately does NOT arm.
RENDERING_KEY = "tool_schema_rendering"

TASK_CONTRACT_TOOL_NAME = "saea-tool-task-contract-v1"

#: Bookkeeping-only top-level keys: run/attempt identity, the provenance-only
#: speech-feature ids, the prepared-supply pin and free-English notes. None
#: shapes a rendered request.
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
# 1. The committed fragments: no factor, plus one declaration that is not one.
# ---------------------------------------------------------------------------


def test_the_smoke_baseline_is_the_arm_baseline_plus_bookkeeping_only():
    arm = _load_baseline(B1R_ARM_BASELINE)
    smoke = _load_baseline(B1R_SMOKE_BASELINE)

    non_bookkeeping = (set(arm) | set(smoke)) - BOOKKEEPING_KEYS
    assert sorted(key for key in non_bookkeeping if arm.get(key) != smoke.get(key)) == []

    # The smoke's only reason to exist is that the full cell's FIT and
    # generation accounting is never charged smoke contacts.
    assert arm["native_contact_fit"]["contact_cap"] == 47520
    assert smoke["native_contact_fit"]["contact_cap"] == 176
    assert arm["native_contact_fit"]["run_id"] == (
        "SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-FIT-V1"
    )
    assert smoke["native_contact_fit"]["run_id"] == (
        "SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-SMOKE-4-FIT-V1"
    )
    # E16: a prepared artifact is evidence only for the implementation that
    # produced it, so each cell pins its OWN, built model-free under its own
    # run id, rather than inheriting cell B1's.
    assert arm["prepared_phase_supply"]["relpath"] == (
        "prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-V1/phase-supply-v1.json"
    )
    assert smoke["prepared_phase_supply"]["relpath"] == (
        "prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-SMOKE-4-V1/phase-supply-v1.json"
    )
    assert arm["prepared_phase_supply"] != smoke["prepared_phase_supply"]
    for doc in (arm, smoke):
        assert doc["prepared_phase_supply"]["relpath"] != (
            _load_baseline(B1_ARM_BASELINE)["prepared_phase_supply"]["relpath"]
        )


@pytest.mark.parametrize(
    "replicate,b1",
    [(B1R_ARM_BASELINE, B1_ARM_BASELINE), (B1R_SMOKE_BASELINE, B1_SMOKE_BASELINE)],
    ids=["arm", "smoke"],
)
def test_the_only_key_that_moves_against_cell_b1_is_the_finite_completion_declaration(
    replicate, b1
):
    off = _load_baseline(b1)
    on = _load_baseline(replicate)

    comparable = (set(off) | set(on)) - BOOKKEEPING_KEYS
    assert sorted(key for key in comparable if off.get(key) != on.get(key)) == [
        "native_episode"
    ]

    # Named one by one so a regression cannot hide behind the set comparison.
    # ``knowledge_stores`` is the module under replication and it does not move.
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
        "what_the_train_exemplars_store_is",
    ):
        assert off[key] == on[key], key

    off_episode = off["native_episode"]
    on_episode = on["native_episode"]
    assert sorted(
        key
        for key in set(off_episode) | set(on_episode)
        if off_episode.get(key) != on_episode.get(key)
    ) == [FINITE_COMPLETION_KEY]

    # Not a factor: the harness declaration item E13's gate requires of every
    # live SLURP native cell. Cell B1 flew without it.
    assert on_episode[FINITE_COMPLETION_KEY] == FINITE_COMPLETION_VALUE
    assert FINITE_COMPLETION_KEY not in off_episode

    stripped = copy.deepcopy(on_episode)
    stripped.pop(FINITE_COMPLETION_KEY)
    assert stripped == off_episode


def test_the_exemplar_supply_block_is_cell_b1s_byte_for_byte():
    """The module under replication is what must NOT move."""

    b1 = _load_baseline(B1_ARM_BASELINE)["knowledge_stores"]
    for name in (B1R_ARM_BASELINE, B1R_SMOKE_BASELINE):
        stores = _load_baseline(name)["knowledge_stores"]
        assert stores == b1, name
        supply = stores["train-exemplars"]["phase_supply"]["solver"]
        assert supply["k"] == 20
        assert supply["fuse_policy"] == "saea-fuse-supplyfilter-v1"
        assert supply["fuse_coverage"] == {"c": 20, "m": 20, "top_l": 20}
        assert supply["rank_policy"] == "saea-rank-wcos-prior-agree-v1"
        assert supply["rank_weights"] == {"w_agree": 0.0, "w_cos": 1.0, "w_prior": 0.0}
        assert supply["tau"] == 0.0
        assert supply["query_source"]["kind"] == "sealed-vectors"


def test_this_cell_keeps_per_role_tool_schema_rendering():
    """Request identity with cell B1 requires the anchor's PER-ROLE rendering,
    so item E17's switch is deliberately NOT armed and cell B1r's result is
    unaffected by efficiency cell EFF-1's outcome."""

    for name in (B1R_ARM_BASELINE, B1R_SMOKE_BASELINE, B1_ARM_BASELINE, B1_SMOKE_BASELINE):
        episode = _load_baseline(name)["native_episode"]
        assert RENDERING_KEY not in episode, name
        # And the base stays node-free, exactly as cell B1 flew it.
        for absent in ("context_policy", "deliver_normaliser", "reviewer_audit"):
            assert absent not in episode, (name, absent)
        doc = _load_baseline(name)
        assert set(doc["phase_tools"]) == {"reviewer"}
        assert doc["phase_tools"]["reviewer"]["allowed_tools"] == [TASK_CONTRACT_TOOL_NAME]


# ---------------------------------------------------------------------------
# 2. The composed configuration parses the declaration and nothing else.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "baseline,experiment",
    [
        (B1R_ARM_BASELINE, B1R_ARM_EXPERIMENT),
        (B1R_SMOKE_BASELINE, B1R_SMOKE_EXPERIMENT),
    ],
    ids=["arm", "smoke"],
)
def test_the_composed_cell_parses_the_declaration_and_per_role_rendering(baseline, experiment):
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    values = _compose(baseline, experiment).values
    config = load_native_episode_config(values, default_phase_program(str(values["policy"])))

    assert config.finite_completion_policy == FINITE_COMPLETION_VALUE
    # NOT armed: the anchor's per-role rendering, which is what request
    # identity with cell B1 requires.
    assert config.tool_schema_rendering == "per-role"
    assert config.constant_tool_names is None
    assert config.role("reviewer").tool_names == (TASK_CONTRACT_TOOL_NAME,)
    for role_id in ("perception", "solver", "planner"):
        assert config.role(role_id).tool_names == ()

    b1_values = _compose(B1_ARM_BASELINE, B1_ARM_EXPERIMENT).values
    b1_config = load_native_episode_config(
        b1_values, default_phase_program(str(b1_values["policy"]))
    )
    assert b1_config.finite_completion_policy == FINITE_COMPLETION_DEFAULT
    assert b1_config.tool_schema_rendering == "per-role"
    # The declaration adds no contact: the bounded ceiling does not move.
    assert config.max_contacts == b1_config.max_contacts == 11
    assert config.episode_id == b1_config.episode_id
    assert config.max_revisions == b1_config.max_revisions == 1


def test_the_composed_knowledge_and_material_values_are_cell_b1s():
    """Everything the model sees is composed identically on both passes."""

    replicate = _compose(B1R_ARM_BASELINE, B1R_ARM_EXPERIMENT).values
    b1 = _compose(B1_ARM_BASELINE, B1_ARM_EXPERIMENT).values
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
        assert replicate[key] == b1[key], key


# ---------------------------------------------------------------------------
# 3. The production render path: the declared key moves no request byte.
# ---------------------------------------------------------------------------

#: The five contacts of one row, in the order the pinned slot sees them.
CONTACT_KEYS = (
    ("s1", "perception", 1, 1),
    ("s1", "solver", 1, 1),
    ("s1", "reviewer", 1, 1),
    ("s1", "reviewer", 1, 2),
    ("s1", "planner", 1, 1),
)


def _rendered_bodies(tmp_path, *, finite_completion_policy):
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
    harness.config = replace(
        harness.config, finite_completion_policy=finite_completion_policy
    )
    try:
        harness.run()
    finally:
        harness.close()
    assert set(harness.prepared) == set(CONTACT_KEYS), sorted(harness.prepared)
    return {key: harness.prepared[key]["rendered"] for key in CONTACT_KEYS}


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_every_composed_request_is_byte_identical_between_b1_and_b1r(tmp_path):
    """Cell B1's parsed finite-completion policy against cell B1r's, driven
    through the production transport with a fake model.

    This is the wire-side proof ``core.flight.cli wire-check`` cannot make for
    a native-episode cell: the ONE declared key that differs between the two
    registrations moves not a single request byte, on any role, including the
    Solver contact that carries the exemplar block. What differs between the
    two passes is therefore batch composition and nothing else.
    """

    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )

    # The two policies come from the two CELLS, not from literals.
    b1r_values = _compose(B1R_ARM_BASELINE, B1R_ARM_EXPERIMENT).values
    b1_values = _compose(B1_ARM_BASELINE, B1_ARM_EXPERIMENT).values
    b1r_policy = load_native_episode_config(
        b1r_values, default_phase_program(str(b1r_values["policy"]))
    ).finite_completion_policy
    b1_policy = load_native_episode_config(
        b1_values, default_phase_program(str(b1_values["policy"]))
    ).finite_completion_policy
    assert (b1_policy, b1r_policy) == (FINITE_COMPLETION_DEFAULT, FINITE_COMPLETION_VALUE)

    b1_rendered = _rendered_bodies(tmp_path / "b1", finite_completion_policy=b1_policy)
    b1r_rendered = _rendered_bodies(tmp_path / "b1r", finite_completion_policy=b1r_policy)

    for key in CONTACT_KEYS:
        assert b1r_rendered[key] == b1_rendered[key], key

    # And the Solver contact -- the one the exemplar supply reaches -- carries
    # no tools array on either side, because rendering stays per-role.
    assert "tools" not in b1r_rendered[("s1", "solver", 1, 1)]
    assert b1r_rendered[("s1", "solver", 1, 1)]["tool_choice"] == "none"
    assert b1r_rendered[("s1", "reviewer", 1, 1)]["tool_choice"] == "auto"


# ---------------------------------------------------------------------------
# 4. The experiment fragments, as registered.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,run_id,stages",
    [
        (
            B1R_SMOKE_EXPERIMENT,
            "SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-SMOKE-4-V1",
            ["check", "prepare-supply", "worker"],
        ),
        (
            B1R_ARM_EXPERIMENT,
            "SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-V1",
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


def test_the_arm_keeps_cell_b1s_roster_and_registered_ceilings():
    """A replicate that moved the roster or the ceilings would not be one."""

    replicate = _load_experiment(B1R_ARM_EXPERIMENT)
    b1 = _load_experiment(B1_ARM_EXPERIMENT)

    assert replicate["populations"] == b1["populations"]
    assert len(replicate["populations"][0]["ids"]) == 1080
    assert replicate["population"]["count"] == b1["population"]["count"] == 1080
    assert replicate["population"]["split_identity_hash"] == (
        "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"
    )
    assert replicate["split_id"] == b1["split_id"] == "SLURP-EVO-FOLD-A-V2"
    assert replicate["family_budget"] == b1["family_budget"]
    assert replicate["family_budget"] == {
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
    assert replicate["execution_plan"] == b1["execution_plan"]
    assert replicate["generation_budget"]["cap"] == 11880
    assert replicate["preserve_wire_responses"] is True


def test_the_smoke_flies_cell_b1s_own_four_rows():
    replicate = _load_experiment(B1R_SMOKE_EXPERIMENT)
    b1 = _load_experiment(B1_SMOKE_EXPERIMENT)
    assert replicate["populations"] == b1["populations"]
    assert replicate["population"] == b1["population"]
    assert replicate["family_budget"] == b1["family_budget"]
    # All four smoke rows are members of the arm's 1,080-row roster.
    arm_ids = set(_load_experiment(B1R_ARM_EXPERIMENT)["populations"][0]["ids"])
    assert set(replicate["populations"][0]["ids"]) <= arm_ids


def test_the_campaign_plan_names_the_arm_and_only_the_arm():
    plan = json.loads(
        (CAMPAIGN_DIR / f"{B1R_ARM_EXPERIMENT}.json").read_text(encoding="utf-8")
    )
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [
        {"cell": B1R_ARM_EXPERIMENT, "experiment": B1R_ARM_EXPERIMENT}
    ]


def test_the_identities_are_fresh_and_never_cell_b1s():
    """A replicate mints its own run, attempt and native-fit identities; it
    never reuses cell B1's, whose rows are sealed and consumed."""

    b1_ids = set()
    for name in (B1_ARM_EXPERIMENT, B1_SMOKE_EXPERIMENT):
        (cell,) = _load_experiment(name)["cells"]
        b1_ids.add(cell["run_id"])
        b1_ids.add(cell["attempt_id"])
    for name in (B1_ARM_BASELINE, B1_SMOKE_BASELINE):
        fit = _load_baseline(name)["native_contact_fit"]
        b1_ids.add(fit["run_id"])
        b1_ids.add(fit["attempt_id"])

    replicate_ids = set()
    for name in (B1R_ARM_EXPERIMENT, B1R_SMOKE_EXPERIMENT):
        (cell,) = _load_experiment(name)["cells"]
        replicate_ids.add(cell["run_id"])
        replicate_ids.add(cell["attempt_id"])
    for name in (B1R_ARM_BASELINE, B1R_SMOKE_BASELINE):
        fit = _load_baseline(name)["native_contact_fit"]
        replicate_ids.add(fit["run_id"])
        replicate_ids.add(fit["attempt_id"])

    assert len(replicate_ids) == 8
    assert b1_ids.isdisjoint(replicate_ids)

    # The speech-feature identity strings are provenance only and are this
    # cell's own on both fragments.
    for name in (B1R_ARM_BASELINE, B1R_SMOKE_BASELINE):
        doc = _load_baseline(name)
        assert "replicate" in doc["speech_feature_matcher_policy_id"]
        assert doc["speech_feature_key_representation_id"] == (
            doc["speech_feature_matcher_policy_id"] + ":query-speech"
        )
