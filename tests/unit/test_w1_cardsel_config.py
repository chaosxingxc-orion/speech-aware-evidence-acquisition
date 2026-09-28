"""Cell W1 -- slot-card selection -- is the retained AGREE arm with ONE key added, read on no
harm at the shared in-chain A/A.

Config only: no data root, no lock, no adapter, no contact.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash

REPO = Path(__file__).resolve().parents[2]

ARM = "slurp-native-stage3-w1-cardsel-fold-a-v1"
SMOKE = "slurp-native-stage3-w1-cardsel-fold-a-smoke-4-v1"
PARENT = {ARM: "slurp-native-stage3-agree-w1-fold-a-v1", SMOKE: "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"}
ARM_RUN = "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1"
SMOKE_RUN = "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-V1"
SHARED_AA = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
READ_ROW = "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1"
PACKAGE = REPO / "docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1"
ONE_KEY = "knowledge_stores.slot-contracts.candidate_supply.solver.candidate_legality_source"
BOOKKEEPING = ("native_contact_fit.", "prepared_phase_supply", "what_this_is", "preparation_source_receipts")
LEGALITY_RELPATH = "prepared/SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1/legality.json"
LEGALITY_RECEIPT = "prepared/SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1/receipt.json"
DECISION_ID = "slurp-stage3-w1-cardsel-fold-a-admission-v1"
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


@pytest.mark.parametrize("experiment", [ARM, SMOKE])
def test_the_composed_diff_is_the_one_key_plus_bookkeeping(experiment):
    document, mine = _compose(experiment)
    parent_doc, parent = _compose(PARENT[experiment])
    baseline_keys = set(_read(REPO / "configs/baseline" / (parent_doc["cells"][0]["baseline_fragment"] + ".json")))
    experiment_keys = set(document) | set(parent_doc)
    assert not (experiment_keys & baseline_keys)
    a, b = _flatten(parent.values), _flatten(mine.values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    one_key = [k for k in changed if k.startswith(ONE_KEY + ".")]
    bookkeeping = [k for k in changed if k.startswith(BOOKKEEPING)]
    block = [k for k in changed if k.split(".", 1)[0] in experiment_keys]
    other = [k for k in changed if k not in one_key and k not in bookkeeping and k not in block]
    assert other == []
    assert {k.rsplit(".", 1)[1] for k in one_key} == {"kind", "relpath", "sha256", "tool_contact_ledger_row", "embedded_signal"}
    # HELD as registered; the flip's re-pin mints this cell's OWN first-phase supply under its
    # own run id (item E16), never a foreign one -- the COMP-1 flip is the pattern.
    supply = mine.values.get("prepared_phase_supply")
    run_id = document["cells"][0]["run_id"]
    assert supply is None or _is_own_supply(supply["relpath"], run_id), supply
    route = mine.values["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solver"]
    assert route["candidate_legality_source"]["relpath"] == LEGALITY_RELPATH
    assert (route["max_candidates"], route["max_values_per_candidate"], route["max_total_values"]) == (3, 16, 28)
    # the legality receipt is the only receipt added
    before = {(e["root"], e["relpath"]) for e in parent.values["preparation_source_receipts"]}
    after = {(e["root"], e["relpath"]) for e in mine.values["preparation_source_receipts"]}
    assert after - before == {("data", LEGALITY_RECEIPT)} and before <= after
    # every other store, the agreement term and all phase material are AGREE's
    assert mine.values["phase_material"] == parent.values["phase_material"]
    for store in ("intent-boundaries", "train-exemplars"):
        assert mine.values["knowledge_stores"][store] == parent.values["knowledge_stores"][store]


@pytest.mark.parametrize("experiment", [ARM, SMOKE])
def test_readiness_is_held_with_the_agreement_table_only(experiment):
    cell = _read(REPO / "configs/experiment" / f"{experiment}.json")["cells"][0]
    parent_cell = _read(REPO / "configs/experiment" / f"{PARENT[experiment]}.json")["cells"][0]
    readiness = cell["readiness"]
    assert readiness["state"] in ("held", "ready")
    agreement = [r for r in parent_cell["readiness"]["requirements"] if r["relpath"].endswith("agreement.jsonl")]
    mine_agreement = [r for r in readiness["requirements"] if r["relpath"].endswith("agreement.jsonl")]
    assert mine_agreement == agreement
    others = [r for r in readiness["requirements"] if not r["relpath"].endswith("agreement.jsonl")]
    if readiness["state"] == "held":
        assert others == []
    else:
        decisions = [r for r in others if r.get("kind") == "decision"]
        assert [d["expected_decision_id"] for d in decisions] == [DECISION_ID]
        own = [r for r in others if r not in decisions]
        assert len(own) == 1 and _is_own_supply(own[0]["relpath"], cell["run_id"]), own


def test_the_campaign_plan_carries_the_arm_alone():
    plan = _read(REPO / "configs/campaign/slurp-native-stage3-w1-cardsel-fold-a-v1.json")
    assert [c["cell"] for c in plan["cells"]] == [ARM]


def test_the_package_declares_a_no_harm_item_at_the_shared_aa():
    facts = _read(PACKAGE / "registered-facts-v1.json")
    block = facts["stage3_measurement"][ARM_RUN]
    assert block["admission"] == "no-harm" and block["claims_benefit"] is False
    assert block["expected_effect_pp"] == 0.0 and block["harm_margin_pp"] == H_SLU
    assert block["harm_margin_pp_by_metric"] == {"intent_accuracy": H_INTENT, "slu_f1": H_SLU}
    assert block["measurement_design"] == "cross-flight-with-in-chain-replicate"
    assert block["replicate_run_id"] == SHARED_AA
    assert block["declared_ceiling"]["tokens_per_solver_contact_mean"] > 0
    assert facts["stage3_measurement"][SMOKE_RUN]["measurement_design"] == "form-proof"


def test_the_package_hashes_are_the_committed_configs_and_the_recipe_declares_its_read():
    protocol = _read(PACKAGE / "protocol-registered-v1.json")
    for key, experiment in (("arm", ARM), ("smoke", SMOKE)):
        document, composed = _compose(experiment)
        assert protocol["cells"][key]["composed_config_hash"] == composed.config_hash
        assert protocol["cells"][key]["protocol_hash"] == protocol_hash(
            composed.config_hash, composed.values["arm"], document["population"]["split_identity_hash"]
        )
    recipe = _read(PACKAGE / "analysis-recipe-v1.json")
    assert recipe["run_ids"]["read"] == READ_ROW
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    for run_id in (ARM_RUN, SMOKE_RUN, "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-FIT-V1",
                   "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-FIT-V1", READ_ROW,
                   "SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1", "SAEA-SLURP-W1-CARD-SELECTION-MEASUREMENT-V1"):
        assert ledger.count(f"| {run_id} |") == 1, run_id


def test_the_measured_legality_is_the_pinned_one():
    measurement = _read(PACKAGE / "card-selection-measurement-v1.json")
    _document, composed = _compose(ARM)
    source = composed.values["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solver"]["candidate_legality_source"]
    assert measurement["inputs"]["legality"]["sha256"] == source["sha256"]
    assert measurement["validation"]["replayed_flown_selection_identical_in_order"] == 1080
