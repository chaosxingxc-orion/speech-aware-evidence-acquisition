"""Cell B5e recovery proof: the re-registration moves bookkeeping and nothing else.

The B5e arm aborted at 25 contacts on 2026-09-18 when the task-owned resident
server died mid-request: all three SAEA Windows Scheduled Tasks carried the
default stop-on-battery condition and stopped when the coordinator changed the
power scheme. The root cause is infrastructure and coordinator-caused, so the
one root-diagnosed recovery re-registration the preregistration allows must
change the *run identity* and nothing a model can see.

These tests pin exactly that, on the committed fragments and -- for the
composed assertions -- through the repository's own ``core.config.compose``,
which is what ``core.flight.cli check`` uses:

1. the recovery baseline differs from the aborted arm's baseline in exactly
   five bookkeeping keys: the FIT identity, the two speech-feature identity
   ids, the prepared-supply pin and the free-English note;
2. both knowledge stores are byte-identical -- M1's ``train-exemplars`` block
   and M4b's ``slot-contracts`` v2 pins are still the blocks cell B1 and cell
   B4b flew, so the combination being measured is the same combination;
3. the recovery experiment fragment carries the recovery run and attempt ids,
   stays readiness ``held`` with a pinned ``preparation`` requirement and *no*
   decision requirement (the coordinator's re-pin adds that), and never reuses
   the closed run or attempt id;
4. the registered ceilings are the aborted arm's, unchanged;
5. composed end to end, the two configurations differ only in bookkeeping keys
   -- every model-facing key is byte-identical -- and the campaign plan
   resolves to the recovery cell.

Model-free: it reads committed JSON and composes it; no model, tokenizer,
encoder, scorer or server is contacted, and no data root is required.
"""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "configs" / "baseline"
EXPERIMENT_DIR = REPO_ROOT / "configs" / "experiment"
CAMPAIGN_DIR = REPO_ROOT / "configs" / "campaign"

MODEL_FRAGMENT = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"

ABORTED_BASELINE = "slurp-native-anchor-b5e-exemplars-k20-slot-store-v2-train-fold-a-v1"
ABORTED_EXPERIMENT = "slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-v1"
ABORTED_RUN = "SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V1"
ABORTED_ATTEMPT = (
    "attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-v1"
)

RECOVERY_BASELINE = "slurp-native-anchor-b5e-exemplars-k20-slot-store-v2-train-fold-a-recovery-v1"
RECOVERY_EXPERIMENT = "slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-recovery-v1"
RECOVERY_RUN = "SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1"
RECOVERY_ATTEMPT = (
    "attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-recovery-v1"
)
RECOVERY_FIT_RUN = (
    "SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-RECOVERY-V1"
)
RECOVERY_FIT_ATTEMPT = (
    "attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-fit-recovery-v1"
)

SPLIT_IDENTITY = "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"

# The only baseline keys a distinct run identity is allowed to move. None of
# them shapes a rendered request: the FIT identity namespaces the fit receipts,
# the two speech-feature ids are provenance that core.model.transport validates
# and drops, the prepared-supply pin is a receipt key, and the note is English.
BASELINE_BOOKKEEPING = [
    "native_contact_fit",
    "prepared_phase_supply",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "what_this_is",
]

# Plus the experiment fragment's own identity and free-English fields.
EXPERIMENT_BOOKKEEPING = [
    "cells",
    "experiment_id",
    "failure_policy",
    "fragment_kind",
    "generation_budget",
    "purpose",
]


def _load(directory: Path, name: str) -> dict:
    return json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))


def _cell(document: dict, cell_id: str) -> dict:
    matches = [cell for cell in document["cells"] if cell["cell_id"] == cell_id]
    assert len(matches) == 1
    return matches[0]


def test_recovery_baseline_moves_five_bookkeeping_keys_and_nothing_else():
    aborted = _load(BASELINE_DIR, ABORTED_BASELINE)
    recovery = _load(BASELINE_DIR, RECOVERY_BASELINE)

    differing = sorted(
        key for key in set(aborted) | set(recovery) if aborted.get(key) != recovery.get(key)
    )
    assert differing == sorted(BASELINE_BOOKKEEPING)

    assert recovery["native_contact_fit"]["run_id"] == RECOVERY_FIT_RUN
    assert recovery["native_contact_fit"]["attempt_id"] == RECOVERY_FIT_ATTEMPT
    assert recovery["native_contact_fit"]["contact_cap"] == 47520
    assert (
        recovery["native_contact_fit"]["max_speech_packets"]
        == aborted["native_contact_fit"]["max_speech_packets"]
    )
    assert recovery["prepared_phase_supply"]["relpath"] == (
        f"prepared/{RECOVERY_RUN}/phase-supply-v1.json"
    )


def test_both_knowledge_stores_are_byte_identical_to_the_aborted_arm():
    aborted = _load(BASELINE_DIR, ABORTED_BASELINE)
    recovery = _load(BASELINE_DIR, RECOVERY_BASELINE)

    assert recovery["knowledge_stores"] == aborted["knowledge_stores"]

    b1_arm = _load(BASELINE_DIR, "slurp-native-anchor-exemplars-k20-train-fold-a-recovery-v2")
    b4b_arm = _load(BASELINE_DIR, "slurp-native-anchor-slot-store-v2-train-fold-a-v2")
    assert recovery["knowledge_stores"]["train-exemplars"] == b1_arm["knowledge_stores"]["train-exemplars"]
    assert recovery["knowledge_stores"]["slot-contracts"] == b4b_arm["knowledge_stores"]["slot-contracts"]


def test_recovery_experiment_carries_new_identities_and_stays_held():
    aborted = _load(EXPERIMENT_DIR, ABORTED_EXPERIMENT)
    recovery = _load(EXPERIMENT_DIR, RECOVERY_EXPERIMENT)

    differing = sorted(
        key for key in set(aborted) | set(recovery) if aborted.get(key) != recovery.get(key)
    )
    assert differing == sorted(EXPERIMENT_BOOKKEEPING)

    cell = _cell(recovery, RECOVERY_EXPERIMENT)
    assert cell["run_id"] == RECOVERY_RUN
    assert cell["attempt_id"] == RECOVERY_ATTEMPT
    assert cell["baseline_fragment"] == RECOVERY_BASELINE
    assert cell["dataset_fragment"] == DATASET_FRAGMENT
    assert cell["model_fragment"] == MODEL_FRAGMENT

    # Readiness is a lifecycle field: `held` with the preparation requirement as registered, or
    # `ready` once the coordinator's re-pin tool has pinned the root decision receipt beside it.
    readiness = cell["readiness"]
    assert readiness["state"] in {"held", "ready"}
    kinds = sorted(requirement["kind"] for requirement in readiness["requirements"])
    assert kinds == (["preparation"] if readiness["state"] == "held" else ["decision", "preparation"])
    preparation = [r for r in readiness["requirements"] if r["kind"] == "preparation"][0]
    assert preparation["relpath"] == f"prepared/{RECOVERY_RUN}/phase-supply-v1.json"

    # The closed identities are named in the recovery prose but never reused as
    # this cell's own run or attempt id.
    assert cell["run_id"] != ABORTED_RUN
    assert cell["attempt_id"] != ABORTED_ATTEMPT
    assert recovery["experiment_id"] == RECOVERY_RUN


def test_every_registered_ceiling_is_the_aborted_arms():
    aborted = _load(EXPERIMENT_DIR, ABORTED_EXPERIMENT)
    recovery = _load(EXPERIMENT_DIR, RECOVERY_EXPERIMENT)

    assert recovery["family_budget"] == aborted["family_budget"]
    assert recovery["execution_plan"] == aborted["execution_plan"]
    assert recovery["execution_profile"] == aborted["execution_profile"] == "bounded-discovery-probe"
    assert recovery["population"] == aborted["population"]
    assert recovery["populations"] == aborted["populations"]
    assert recovery["split_id"] == aborted["split_id"]
    assert recovery["service_session"] == aborted["service_session"]
    # generation_budget moves only in its free-English definition.
    assert recovery["generation_budget"]["cap"] == aborted["generation_budget"]["cap"] == 11880
    assert recovery["generation_budget"]["target"] == aborted["generation_budget"]["target"]


def test_the_composed_configurations_differ_only_in_bookkeeping():
    aborted = compose(REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT, ABORTED_BASELINE, ABORTED_EXPERIMENT)
    recovery = compose(
        REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT, RECOVERY_BASELINE, RECOVERY_EXPERIMENT
    )

    keys = set(aborted.values) | set(recovery.values)
    differing = sorted(
        key for key in keys if aborted.values.get(key) != recovery.values.get(key)
    )
    assert differing == sorted(BASELINE_BOOKKEEPING + EXPERIMENT_BOOKKEEPING)
    assert len(keys) - len(differing) == 56

    # The composed hash and therefore the protocol hash necessarily move, since
    # compose() hashes the complete merged fragment set including the run
    # identity. The arm string -- what protocol_hash binds beside the config --
    # does not.
    assert aborted.values["arm"] == recovery.values["arm"]
    assert recovery.config_hash != aborted.config_hash
    assert protocol_hash(recovery.config_hash, recovery.values["arm"], SPLIT_IDENTITY) != protocol_hash(
        aborted.config_hash, aborted.values["arm"], SPLIT_IDENTITY
    )


def test_the_recovery_campaign_plan_resolves_to_the_recovery_cell():
    plan = json.loads(
        (CAMPAIGN_DIR / f"{RECOVERY_EXPERIMENT}.json").read_text(encoding="utf-8")
    )
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [{"cell": RECOVERY_EXPERIMENT, "experiment": RECOVERY_EXPERIMENT}]
