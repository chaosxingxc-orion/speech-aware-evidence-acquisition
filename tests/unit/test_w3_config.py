"""Cell W3 -- W3a ALONE, the intent contrast cards (owner decision 164; re-registered 2026-09-27
by the coordinator ruling under decision 164's one-change rule, the per-intent exemplar cap W3b
dropped) -- is the retained AGREE arm with ONE knowledge-content pin, read on no harm at the
shared wave-1 A/A.

Config only: no data root, no lock, no adapter, no contact. The composed-config diff against the
AGREE parent is re-proven here, together with the pin's numbers (the released contrast store),
the ABSENCE of the cap (the Solver exemplar supply is the AGREE arm's, byte for byte) and the
package's no-harm declaration.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import KNOWLEDGE_FUSERS
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
# Registers saea-fuse-supplyfilter-v1 (and its siblings) into KNOWLEDGE_FUSERS at import time;
# without this the module-under-test check below is collection-order-dependent on some other
# test module happening to import the rails knowledge stack first.
from speech_aware_evidence_acquisition.rails import kb_policy  # noqa: F401

REPO = Path(__file__).resolve().parents[2]

ARM = "slurp-native-stage3-w3-fold-a-v1"
SMOKE = "slurp-native-stage3-w3-fold-a-smoke-4-v1"
ARM_RUN = "SAEA-SLURP-STAGE3-W3-FOLD-A-V1"
SMOKE_RUN = "SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-V1"
FIT = {ARM_RUN: "SAEA-SLURP-STAGE3-W3-FOLD-A-FIT-V1", SMOKE_RUN: "SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-FIT-V1"}
PARENT = {ARM: "slurp-native-stage3-agree-w1-fold-a-v1", SMOKE: "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"}
SHARED_AA = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
READ_RUN = "SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1"

PACKAGE = REPO / "docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1"
CARDS = REPO / "docs/receipts/knowledge/slurp-intent-contrast-cards-v1.json"
IB = "knowledge_stores.intent-boundaries."
SOLVER = "knowledge_stores.train-exemplars.phase_supply.solver."
PINNED_W3A = {IB + "release.relpath", IB + "release.sha256", IB + "snapshot.relpath", IB + "snapshot.sha256"}
PINNED_W3B = {SOLVER + "fuse_policy", SOLVER + "k", SOLVER + "fuse_coverage.c", SOLVER + "fuse_coverage.m"}
RECEIPTS = "preparation_source_receipts"
BOOKKEEPING = ("native_contact_fit.", "prepared_phase_supply", "what_this_is")
DECISION_ID = "slurp-stage3-w3-contrast-fold-a-admission-v1"
H_SLU, H_INTENT = 1.2485, 0.9943


def _is_own_supply(relpath: str, run_id: str) -> bool:
    """This cell's own first-phase supply, minted under its own run id at the flip
    (item E16); the relpath/prefix identifies the cell, the digest is rewritten by
    scripts/flights/repin_cell.py and is never asserted here."""

    return re.fullmatch(rf"prepared/{re.escape(run_id)}/phase-supply-v\d+\.json", relpath) is not None


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(_flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def _compose(experiment: str):
    document = _read(REPO / "configs/experiment" / f"{experiment}.json")
    cell = document["cells"][0]
    return document, compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)


def _changed(experiment: str) -> tuple[list[str], dict, dict]:
    document, mine = _compose(experiment)
    parent_doc, parent = _compose(PARENT[experiment])
    baseline_keys = set(_read(REPO / "configs/baseline" / (parent_doc["cells"][0]["baseline_fragment"] + ".json")))
    assert not ((set(document) | set(parent_doc)) & baseline_keys), "the experiment fragment overrides a baseline key"
    a, b = _flatten(parent.values), _flatten(mine.values)
    return sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>")), parent.values, mine.values


@pytest.mark.parametrize("experiment", [ARM, SMOKE])
def test_composed_diff_is_the_one_pin_the_receipts_and_bookkeeping(experiment):
    changed, parent, mine = _changed(experiment)
    experiment_keys = set(_read(REPO / "configs/experiment" / f"{experiment}.json"))
    other = [
        k for k in changed
        if k not in PINNED_W3A | {RECEIPTS}
        and not k.startswith(BOOKKEEPING)
        and k.split(".", 1)[0] not in experiment_keys
    ]
    assert other == [], f"{experiment}: the composed config moves beyond the W3a pin: {other}"
    assert PINNED_W3A <= set(changed)
    assert not (PINNED_W3B & set(changed)), "the per-intent exemplar cap (W3b) must be absent"
    assert mine["knowledge_stores"]["train-exemplars"] == parent["knowledge_stores"]["train-exemplars"]
    # the receipts only GROW, by exactly the contrast release's two receipts
    added = [entry for entry in mine[RECEIPTS] if entry not in parent[RECEIPTS]]
    assert all(entry in mine[RECEIPTS] for entry in parent[RECEIPTS])
    assert sorted(entry["relpath"] for entry in added) == [
        "knowledge/slurp/semantic/intent-boundaries-contrast-v1/completion.json",
        "knowledge/slurp/semantic/intent-boundaries-contrast-v1/release.json",
    ]
    # the rest of both stores, the slot store, the agreement term and every template are AGREE's
    assert mine["knowledge_stores"]["slot-contracts"] == parent["knowledge_stores"]["slot-contracts"]
    assert mine["knowledge_stores"]["intent-boundaries"]["phase_supply"] == parent["knowledge_stores"]["intent-boundaries"]["phase_supply"]
    assert mine["phase_material"] == parent["phase_material"]
    assert mine["native_episode"] == parent["native_episode"]
    # HELD as registered; the flip's re-pin mints this cell's OWN first-phase supply under its
    # own run id (item E16), never a foreign one -- the COMP-1 flip is the pattern.
    supply = mine.get("prepared_phase_supply")
    run_id = ARM_RUN if experiment == ARM else SMOKE_RUN
    assert supply is None or _is_own_supply(supply["relpath"], run_id), supply


@pytest.mark.parametrize("experiment", [ARM, SMOKE])
def test_the_pin_carries_the_released_store_and_the_solver_supply_is_agree(experiment):
    _changed_keys, parent, mine = _changed(experiment)
    cards = _read(CARDS)
    offline = _read(PACKAGE / "offline-estimates-v1.json")
    ib = mine["knowledge_stores"]["intent-boundaries"]
    assert ib["snapshot"] == {"relpath": cards["release"]["snapshot"]["relpath"], "sha256": cards["release"]["snapshot"]["content_sha256"]}
    assert ib["release"] == {"relpath": cards["release"]["release"]["relpath"], "sha256": cards["release"]["release"]["sha256"]}
    assert cards["release"]["reloaded_through_load_knowledge_store_binding"] is True
    assert cards["invariants"] == {"facets_unchanged": True, "value_ids_unchanged": True, "every_card_tokens_not_above_flown": True}
    assert cards["tokens"]["max_card_delta"] <= 0
    solver = mine["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    assert solver == parent["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    assert solver["fuse_policy"] == "saea-fuse-supplyfilter-v1"
    assert solver["fuse_policy"] in KNOWLEDGE_FUSERS.names()
    assert solver["fuse_coverage"] == {"c": 20, "m": 20, "top_l": 20}
    assert solver["k"] == 20
    assert solver["rank_weights"] == {"w_agree": 0.0, "w_cos": 1.0, "w_prior": 0.0} and solver["tau"] == 0.0
    assert offline["validation"]["fold_a_top20_equals_agree_solver_consumption"] == "1080 of 1080"
    assert offline["validation"]["fold_b_top20_intent_shares_equal_pinned_agreement_table"] == "1080 of 1080"


def test_cells_are_held_with_empty_requirements_and_their_own_ids():
    for experiment, run_id in ((ARM, ARM_RUN), (SMOKE, SMOKE_RUN)):
        document, composed = _compose(experiment)
        cell = document["cells"][0]
        assert cell["run_id"] == run_id
        readiness = cell["readiness"]
        assert readiness["state"] in ("held", "ready")
        if readiness["state"] == "held":
            assert readiness["requirements"] == []
        else:
            decisions = [r for r in readiness["requirements"] if r.get("kind") == "decision"]
            assert [d["expected_decision_id"] for d in decisions] == [DECISION_ID]
            own = [r for r in readiness["requirements"] if r["kind"] == "preparation"]
            assert len(own) == 1 and _is_own_supply(own[0]["relpath"], run_id), own
        assert composed.values["native_contact_fit"]["run_id"] == FIT[run_id]
        assert document["stage3_algorithm"]["id"] == "none"
        assert composed.values["native_episode"]["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert composed.values["native_episode"]["react_exhaustion_policy"] == "continue-without-answer"
    campaign = _read(REPO / "configs/campaign/slurp-native-stage3-w3-fold-a-v1.json")
    assert campaign["cells"] == [{"cell": ARM, "experiment": ARM}]


def test_package_declares_no_harm_at_the_shared_aa_and_registers_its_read():
    facts = _read(PACKAGE / "registered-facts-v1.json")
    arm = facts["stage3_measurement"][ARM_RUN]
    assert arm["admission"] == "no-harm" and arm["claims_benefit"] is False
    assert arm["expected_effect_pp"] == 0.0
    assert arm["harm_margin_pp"] == H_SLU
    assert arm["harm_margin_pp_by_metric"] == {"intent_accuracy": H_INTENT, "slu_f1": H_SLU}
    assert arm["replicate_run_id"] == SHARED_AA
    assert facts["stage3_measurement"][SMOKE_RUN]["measurement_design"] == "form-proof"
    recipe = _read(PACKAGE / "analysis-recipe-v1.json")
    assert recipe["run_ids"]["read"] == READ_RUN and recipe["read_run_id"] == READ_RUN
    assert recipe["arms"]["in_chain_replicate"]["run_id"] == SHARED_AA
    proofs = _read(PACKAGE / "preflight-proofs-v1.json")
    for experiment, run_id in ((ARM, ARM_RUN), (SMOKE, SMOKE_RUN)):
        _document, composed = _compose(experiment)
        key = "arm" if experiment == ARM else "smoke"
        assert proofs["cells"][key]["first_phase_supply_proof"]["identical"] is True
        assert proofs["cells"][key]["check"]["config_hash"] == composed.config_hash
        # the POPULATION's identity (the smoke flies 4 rows), which is what the runtime's check reports
        split = _read(REPO / "configs/experiment" / f"{experiment}.json")["population"]["split_identity_hash"]
        prefix = "" if experiment == ARM else "smoke-"
        plan = _read(PACKAGE / f"{prefix}generation-plan-registered-v1.json")
        assert plan["composed_config_hash"] == composed.config_hash
        assert plan["execution_plan"]["protocol_hash"] == protocol_hash(composed.config_hash, composed.values["arm"], split)
