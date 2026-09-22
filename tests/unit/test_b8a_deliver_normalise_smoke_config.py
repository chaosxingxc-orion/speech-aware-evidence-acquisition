"""Cell B8a config-switch proof: the delivery-time normaliser node on the B1 base.

Cell B8a (owner decision 27 of 2026-09-19, owner directive 26 of 2026-09-18) turns
on exactly one thing against cell B1's recovery arm: the ``episode``-class key
``native_episode.deliver_normaliser``, armed as
``{"normaliser": "saea-deliver-normalise-v3"}``. The node makes no contact and
runs after every contact of the episode is already spent, so an ON arm and its
comparator must be IDENTICAL in every key that shapes a request.

These tests pin exactly that, on the committed fragments and on the COMPOSED
configuration:

1. the four-row smoke baseline is the E11 arm baseline apart from its own FIT
   identity (the 4 x 11 x 4 = 176 endpoint ceiling), its own two speech-feature
   identity ids, its own prepared-supply pin and its note;
2. against cell B1's recovery-arm baseline, the only model-facing key that moves
   is ``native_episode``, and inside ``native_episode`` the only key that moves
   is ``deliver_normaliser`` -- every store, template, policy, geometry and
   ``phase_*`` key is byte-identical;
3. the armed value is the registered rule id, it resolves in
   ``core.base.DELIVERY_NORMALISERS``, and ``rails.native_episode_config``
   loads the composed smoke configuration with ``deliver_normaliser_id`` set;
4. dropping the one key reconstructs cell B1's own ``native_episode`` block
   exactly -- the OFF arm of this module is the base, not a third identity;
5. the smoke experiment fragment is registered ``held`` with no decision
   requirement, at the four-row roster, the smoke budgets and the worker route.

Model-free: it reads committed JSON, composes it with the repository's own
``core.config.compose``, and makes no model, tokenizer, encoder, scorer, server
or network contact.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "configs" / "baseline"
EXPERIMENT_DIR = REPO_ROOT / "configs" / "experiment"

MODEL_FRAGMENT = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"

B1_ARM = "slurp-native-anchor-exemplars-k20-train-fold-a-recovery-v2"
E11_ARM = "slurp-native-anchor-exemplars-k20-deliver-normalise-v3-train-fold-a-v1"
B8A_SMOKE_BASELINE = "slurp-native-anchor-exemplars-k20-deliver-normalise-v3-smoke-4-v1"
B8A_SMOKE_EXPERIMENT = "slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1"
B1_SMOKE_BASELINE = "slurp-native-anchor-exemplars-k20-smoke-4-recovery-v2"
B1_SMOKE_EXPERIMENT = "slurp-native-exemplars-k20-anchor-smoke-4-recovery-v2"

DELIVER_NORMALISER_KEY = "deliver_normaliser"
ARMED_VALUE = {"normaliser": "saea-deliver-normalise-v3"}

#: Bookkeeping-only top-level keys: run/attempt identity, the prepared-artifact
#: pin, the provenance-only speech-feature ids and free-English notes. None of
#: them shapes a rendered request; every one of them must differ between two
#: distinct run identities.
BOOKKEEPING_KEYS = frozenset(
    {
        "native_contact_fit",
        "prepared_phase_supply",
        "preparation_source_receipts",
        "speech_feature_key_representation_id",
        "speech_feature_matcher_policy_id",
        "what_this_is",
        "what_the_train_exemplars_store_is",
    }
)

#: ``scorers`` names what a sealed manifest is SCORED with. It is read-side, it
#: renders into no request byte, and the E11 fragments deliberately declare
#: ``slurp-slu-official-projected-v3-train`` beside the primary so the
#: projected scorer's no-op on an ON arm's own outputs is itself part of the
#: receipt. It is therefore set aside for the request-channel comparison and
#: asserted separately.
READ_SIDE_KEYS = frozenset({"scorers"})


def _load_baseline(name: str) -> dict:
    return json.loads((BASELINE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _load_experiment(name: str) -> dict:
    return json.loads((EXPERIMENT_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _compose(baseline: str, experiment: str):
    from speech_aware_evidence_acquisition.core.config import compose

    return compose(str(REPO_ROOT), MODEL_FRAGMENT, DATASET_FRAGMENT, baseline, experiment)


def test_the_smoke_baseline_is_the_e11_arm_baseline_plus_bookkeeping_only():
    arm = _load_baseline(E11_ARM)
    smoke = _load_baseline(B8A_SMOKE_BASELINE)

    non_bookkeeping = (set(arm) | set(smoke)) - BOOKKEEPING_KEYS
    differing = sorted(key for key in non_bookkeeping if arm.get(key) != smoke.get(key))
    assert differing == []

    assert smoke["native_contact_fit"]["contact_cap"] == 176
    assert smoke["native_contact_fit"]["run_id"] == (
        "SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-FIT-V1"
    )
    assert smoke["speech_feature_matcher_policy_id"] != arm["speech_feature_matcher_policy_id"]


def test_the_only_model_facing_key_that_moves_against_the_b1_arm_is_native_episode():
    b1 = _load_baseline(B1_ARM)
    smoke = _load_baseline(B8A_SMOKE_BASELINE)

    comparable = (set(b1) | set(smoke)) - BOOKKEEPING_KEYS - READ_SIDE_KEYS
    differing = sorted(key for key in comparable if b1.get(key) != smoke.get(key))
    assert differing == ["native_episode"]

    # The knowledge channel, every instruction template, the policy and the
    # serving geometry are byte-identical -- named one by one so a future
    # regression cannot hide behind the set comparison above.
    for key in (
        "arm",
        "knowledge_stores",
        "phase_material",
        "phase_tools",
        "policy",
        "serving_slot_tokens",
        "serving_slots",
        "task_instruction_fill",
        "task_instruction_template",
        "task_instruction_template_active",
    ):
        assert b1[key] == smoke[key], key


def test_inside_native_episode_the_only_key_that_moves_is_the_delivery_node():
    b1_episode = _load_baseline(B1_ARM)["native_episode"]
    smoke_episode = _load_baseline(B8A_SMOKE_BASELINE)["native_episode"]

    differing = sorted(
        key
        for key in set(b1_episode) | set(smoke_episode)
        if b1_episode.get(key) != smoke_episode.get(key)
    )
    assert differing == [DELIVER_NORMALISER_KEY]
    assert DELIVER_NORMALISER_KEY not in b1_episode
    assert smoke_episode[DELIVER_NORMALISER_KEY] == ARMED_VALUE


def test_turning_the_node_off_reconstructs_the_b1_arms_own_episode_block():
    b1_episode = _load_baseline(B1_ARM)["native_episode"]
    smoke_episode = copy.deepcopy(_load_baseline(B8A_SMOKE_BASELINE)["native_episode"])

    smoke_episode.pop(DELIVER_NORMALISER_KEY)
    assert smoke_episode == b1_episode


def test_the_armed_rule_is_registered_and_is_defined_for_this_carrier():
    from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS

    # Importing rails.delivery_normalisers is what POPULATES the registry.
    from speech_aware_evidence_acquisition.rails import (  # noqa: F401
        delivery_normalisers as _delivery_normalisers,
    )

    smoke = _load_baseline(B8A_SMOKE_BASELINE)
    rule_id = smoke["native_episode"][DELIVER_NORMALISER_KEY]["normaliser"]
    normaliser = DELIVERY_NORMALISERS.resolve(rule_id)
    assert normaliser.id == "saea-deliver-normalise-v3"
    assert normaliser.carrier_lock_key == smoke.get("carrier_lock_key", "slurp")


def test_the_composed_smoke_loads_a_native_episode_with_the_node_armed():
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )

    values = _compose(B8A_SMOKE_BASELINE, B8A_SMOKE_EXPERIMENT).values
    config = load_native_episode_config(values, default_phase_program(str(values["policy"])))
    assert config.deliver_normaliser_id == "saea-deliver-normalise-v3"

    # And the OFF base loads the same episode with no node at all.
    b1_values = _compose(B1_SMOKE_BASELINE, B1_SMOKE_EXPERIMENT).values
    b1_config = load_native_episode_config(
        b1_values, default_phase_program(str(b1_values["policy"]))
    )
    assert b1_config.deliver_normaliser_id is None
    assert config.episode_id == b1_config.episode_id
    assert config.max_contacts == b1_config.max_contacts


def test_the_composed_request_channel_equals_the_b1_smokes():
    """The node changes no request, so every composed key that shapes a request
    must be byte-identical to cell B1's own four-row smoke."""

    smoke = _compose(B8A_SMOKE_BASELINE, B8A_SMOKE_EXPERIMENT).values
    b1_smoke = _compose(B1_SMOKE_BASELINE, B1_SMOKE_EXPERIMENT).values

    # Experiment-level identity keys necessarily differ between two cells.
    experiment_bookkeeping = {
        "cells",
        "date",
        "execution_plan",
        "experiment_id",
        "failure_policy",
        "family_budget",
        "fragment_kind",
        "population",
        "populations",
        "purpose",
    }
    comparable = (
        (set(smoke) | set(b1_smoke))
        - BOOKKEEPING_KEYS
        - READ_SIDE_KEYS
        - experiment_bookkeeping
    )
    differing = sorted(key for key in comparable if smoke.get(key) != b1_smoke.get(key))
    assert differing == ["native_episode"]

    episode_differing = sorted(
        key
        for key in set(smoke["native_episode"]) | set(b1_smoke["native_episode"])
        if smoke["native_episode"].get(key) != b1_smoke["native_episode"].get(key)
    )
    assert episode_differing == [DELIVER_NORMALISER_KEY]


def test_the_declared_scorers_add_only_the_projected_v3_diagnostic():
    b1 = _load_baseline(B1_ARM)
    smoke = _load_baseline(B8A_SMOKE_BASELINE)

    assert b1["scorers"] == ["slurp-slu-official-train", "cost"]
    assert smoke["scorers"] == [
        "slurp-slu-official-train",
        "slurp-slu-official-projected-v3-train",
        "cost",
    ]
    # The primary is unchanged and first; the addition is a read-side
    # diagnostic that is expected to be a no-op on this cell's own outputs.
    assert smoke["scorers"][0] == b1["scorers"][0]


def test_the_smoke_experiment_is_registered_at_the_four_row_roster():
    # Registered held at 9a25420c; flipped to ready by the re-pin tool at d5378d07 (the flip adds
    # the decision requirement in front of the preparation one). The test reads the flown state.
    experiment = _load_experiment(B8A_SMOKE_EXPERIMENT)
    (cell,) = experiment["cells"]

    assert cell["readiness"]["state"] == "ready"
    kinds = [entry["kind"] for entry in cell["readiness"]["requirements"]]
    assert kinds == ["decision", "preparation"]
    assert "slurp-b8a-deliver-normalise-admission-v1" in cell["readiness"]["reason"]
    assert (
        "coordination/slurp-b8a-deliver-normalise-v1/root-admission-v1.json"
        in cell["readiness"]["reason"]
    )

    assert cell["baseline_fragment"] == B8A_SMOKE_BASELINE
    assert cell["run_id"] == "SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-V1"
    assert cell["allowed_execution_stages"] == ["check", "prepare-supply", "worker"]

    assert experiment["population"]["count"] == 4
    assert len(experiment["populations"][0]["ids"]) == 4
    assert experiment["execution_profile"] == "bounded-discovery-probe"
    assert experiment["family_budget"]["generation_calls_cap"] == 44
    assert experiment["family_budget"]["fit_endpoint_calls_cap"] == 176
    assert experiment["family_budget"]["official_complete_scoring_jobs"] == 0
    assert experiment["service_session"] == "serving-slurp-native-candidate-five-train-a-np4-v1"


def test_the_smoke_flies_the_same_four_rows_every_form_smoke_of_this_roster_flies():
    smoke = _load_experiment(B8A_SMOKE_EXPERIMENT)
    b1_smoke = _load_experiment(B1_SMOKE_EXPERIMENT)

    assert smoke["populations"] == b1_smoke["populations"]
    assert (
        smoke["population"]["split_identity_hash"]
        == b1_smoke["population"]["split_identity_hash"]
    )
    assert smoke["split_id"] == b1_smoke["split_id"]
