"""Cell W5 -- knowledge-wave item W5, slot-side retrieval (owner decision 170) -- is the retained
AGREE arm with ONE store ADDED: ``knowledge_stores.slot-exemplars`` (plus its two provenance
receipts and its order-table readiness requirement). Config only: no data root, no lock, no
adapter, no contact.
"""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash

REPO = Path(__file__).resolve().parents[2]
ARM = "slurp-native-stage3-w5-fold-a-v1"
SMOKE = "slurp-native-stage3-w5-fold-a-smoke-4-v1"
PARENT = {ARM: "slurp-native-stage3-agree-w1-fold-a-v1", SMOKE: "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"}
RUN = {ARM: "SAEA-SLURP-STAGE3-W5-FOLD-A-V1", SMOKE: "SAEA-SLURP-STAGE3-W5-FOLD-A-SMOKE-4-V1"}
PACKAGE = REPO / "docs/readiness/2026-09-27-slurp-stage3-w5-fold-a-v1"
PREREG = REPO / "docs/readiness/2026-09-27-slurp-stage3-w5-fold-a-v1-preregistration.md"
STORE = "knowledge_stores.slot-exemplars"
BOOKKEEPING = ("preparation_source_receipts", "native_contact_fit.", "prepared_phase_supply", "what_this_is")
SHARED_AA = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
AGREEMENT = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl"
SCOPE = "prepared/SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1/agreement.jsonl"


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


def _diff(experiment: str) -> dict:
    document, mine = _compose(experiment)
    parent_doc, parent = _compose(PARENT[experiment])
    experiment_keys = set(document) | set(parent_doc)
    a, b = _flatten(parent.values), _flatten(mine.values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    store = [k for k in changed if k.startswith(STORE + ".")]
    bookkeeping = [k for k in changed if k.startswith(BOOKKEEPING)]
    block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in store and k not in bookkeeping]
    other = [k for k in changed if k not in store and k not in bookkeeping and k not in block]
    return {"store": store, "other": other, "mine": mine, "parent": parent, "a": a}


def test_the_arm_and_smoke_add_one_store_and_move_nothing_else() -> None:
    for experiment in (ARM, SMOKE):
        diff = _diff(experiment)
        assert diff["other"] == [], (experiment, diff["other"])
        assert diff["store"] and not any(k in diff["a"] for k in diff["store"])
        stores = diff["mine"].values["knowledge_stores"]
        for name in ("intent-boundaries", "slot-contracts", "train-exemplars"):
            assert stores[name] == diff["parent"].values["knowledge_stores"][name]
        added = stores["slot-exemplars"]
        assert added["store_role"] == "train-exemplars" and set(added["phase_supply"]) == {"solver"}
        spec = added["phase_supply"]["solver"]
        m1 = stores["train-exemplars"]["phase_supply"]["solver"]
        # same speech query and TRAIN keys as M1; the order is the pinned table read through w_agree only
        assert spec["query_source"] == m1["query_source"] and spec["facet_source"] == m1["facet_source"]
        assert spec["rank_weights"] == {"w_agree": 1.0, "w_cos": 0.0, "w_prior": 0.0}
        assert spec["fuse_policy"] == "saea-fuse-associated-values-v1"
        assert spec["fuse_coverage"] == {"c": 1, "m": 300, "top_l": 9} and spec["k"] == 300
        assert spec["agreement_source"]["relpath"] == SCOPE
        assert spec["query_source"]["embedded_signal"].startswith("speech:")
        assert diff["mine"].values["phase_material"] == diff["parent"].values["phase_material"]
        assert diff["mine"].values["native_episode"] == diff["parent"].values["native_episode"]


def test_receipts_are_appended_not_rewritten() -> None:
    for experiment in (ARM, SMOKE):
        diff = _diff(experiment)
        old = diff["parent"].values["preparation_source_receipts"]
        new = diff["mine"].values["preparation_source_receipts"]
        assert new[: len(old)] == old
        assert [r["relpath"] for r in new[len(old):]] == [
            "knowledge/slurp/saea-kb-distmodel-v1/slot-exemplars-w5-v1/release.json",
            "prepared/SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1/receipt.json",
        ]
        supply = diff["mine"].values.get("prepared_phase_supply")
        assert supply is None or supply["relpath"].startswith(f"prepared/{RUN[experiment]}/"), supply


def test_cells_are_held_with_the_agreement_and_scope_requirements() -> None:
    for experiment in (ARM, SMOKE):
        cell = _read(REPO / "configs/experiment" / f"{experiment}.json")["cells"][0]
        state = cell["readiness"]["state"]
        assert state in ("held", "ready")
        reqs = cell["readiness"]["requirements"]
        preps = [r["relpath"] for r in reqs if r["kind"] == "preparation"]
        assert AGREEMENT in preps and SCOPE in preps
        if state == "held":
            assert preps == [AGREEMENT, SCOPE]
        else:
            assert [r.get("expected_decision_id") for r in reqs if r["kind"] == "decision"] == [
                "slurp-stage3-w5-fold-a-admission-v1"]
        assert cell["run_id"] == RUN[experiment]


def test_campaign_plan_carries_the_arm_alone() -> None:
    plan = _read(REPO / "configs/campaign/slurp-native-stage3-w5-fold-a-v1.json")
    assert plan == {"cells": [{"cell": ARM, "experiment": ARM}], "schema": "saea-campaign-plan-v1"}


def test_registered_hashes_are_the_composed_ones() -> None:
    facts = _read(PACKAGE / "registered-facts-v1.json")
    for key, experiment in (("arm", ARM), ("smoke", SMOKE)):
        document, composed = _compose(experiment)
        split = document["population"]["split_identity_hash"]
        identity = facts["identity"][key]
        assert identity["composed_config_hash"] == composed.config_hash
        assert identity["protocol_hash"] == protocol_hash(composed.config_hash, composed.values["arm"], split)
        plan = _read(PACKAGE / (("" if key == "arm" else "smoke-") + "generation-plan-registered-v1.json"))
        assert plan["composed_config_hash"] == composed.config_hash
        assert plan["execution_plan"]["protocol_hash"] == identity["protocol_hash"]


def test_measurement_declaration_is_no_harm_slu_primary_at_the_shared_aa() -> None:
    facts = _read(PACKAGE / "registered-facts-v1.json")
    block = facts["stage3_measurement"][RUN[ARM]]
    assert block["admission"] == "no-harm" and block["claims_benefit"] is False
    assert block["expected_effect_pp"] == 0.0 and block["harm_margin_pp"] == 1.2485
    assert block["harm_margin_pp_by_metric"] == {"slu_f1": 1.2485, "intent_accuracy": 0.9943}
    assert block["replicate_run_id"] == SHARED_AA
    assert block["primary_metric"].startswith("official pooled SLU-F1")
    assert facts["expectation_basis"]["expected_pp"] < 2.5, "the measured expectation cleared the floor; revisit"
    assert '"replicate_run_id": "' + SHARED_AA + '"' in PREREG.read_text(encoding="utf-8")


def test_analysis_recipe_and_ledger_rows() -> None:
    recipe = _read(PACKAGE / "analysis-recipe-v1.json")
    assert recipe["run_ids"]["read"] == recipe["read_run_id"] == "SAEA-SLURP-STAGE3-W5-FOLD-A-PAIRED-READ-V1"
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8").split("\n")
    ids = (RUN[ARM], "SAEA-SLURP-STAGE3-W5-FOLD-A-FIT-V1", RUN[SMOKE], "SAEA-SLURP-STAGE3-W5-FOLD-A-SMOKE-4-FIT-V1",
           "SAEA-SLURP-STAGE3-W5-FOLD-A-PAIRED-READ-V1", "SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1",
           "SAEA-SLURP-W5-FOLD-A-OFFLINE-ESTIMATE-V1")
    for run_id in ids:
        rows = [ln for ln in ledger if ln.startswith("|") and len(ln.split("|")) > 3 and ln.split("|")[2].strip() == run_id]
        assert len(rows) == 1, run_id
        assert len(rows[0].split("|")) == 17, run_id
