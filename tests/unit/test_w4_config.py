"""Cell W4 -- knowledge-wave item W4, slot conventions (owner decision 164) -- is the retained
AGREE arm with ONE pin moved: ``knowledge_stores.slot-contracts`` re-pinned to the
slot-contracts-w4-v1 release (plus its two provenance receipts). Config only: no data root,
no lock, no adapter, no contact.
"""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash

REPO = Path(__file__).resolve().parents[2]
ARM = "slurp-native-stage3-w4-fold-a-v1"
SMOKE = "slurp-native-stage3-w4-fold-a-smoke-4-v1"
PARENT = {ARM: "slurp-native-stage3-agree-w1-fold-a-v1", SMOKE: "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"}
RUN = {ARM: "SAEA-SLURP-STAGE3-W4-FOLD-A-V1", SMOKE: "SAEA-SLURP-STAGE3-W4-FOLD-A-SMOKE-4-V1"}
PACKAGE = REPO / "docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1"
PREREG = REPO / "docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1-preregistration.md"
PIN = "knowledge_stores.slot-contracts"
NEW = {
    "release": {"relpath": "knowledge/slurp/semantic/slot-contracts-w4-v1/release.json",
                "sha256": "c7bdeee6e0859fbba6bce79cd3d42347a5b74770f7564094e3d3a0edfe003fb0"},
    "snapshot": {"relpath": "knowledge/slurp/semantic/slot-contracts-w4-v1/snapshot.json",
                 "sha256": "51d634cfcb398038377feca89d2783f59a705546390839e7cf4dd7d15ad3b9d6"},
}
BOOKKEEPING = ("preparation_source_receipts", "native_contact_fit.", "prepared_phase_supply", "what_this_is")
SHARED_AA = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"


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
    pin = [k for k in changed if k.startswith(PIN + ".")]
    bookkeeping = [k for k in changed if k.startswith(BOOKKEEPING)]
    block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in pin and k not in bookkeeping]
    other = [k for k in changed if k not in pin and k not in bookkeeping and k not in block]
    return {"pin": pin, "other": other, "mine": mine, "parent": parent, "document": document}


def test_the_arm_and_smoke_move_the_slot_store_pin_and_nothing_else() -> None:
    for experiment in (ARM, SMOKE):
        diff = _diff(experiment)
        assert diff["other"] == [], (experiment, diff["other"])
        assert sorted(diff["pin"]) == sorted(f"{PIN}.{p}.{f}" for p in ("release", "snapshot") for f in ("relpath", "sha256"))
        store = diff["mine"].values["knowledge_stores"]["slot-contracts"]
        assert store["release"] == NEW["release"] and store["snapshot"] == NEW["snapshot"]
        parent_store = diff["parent"].values["knowledge_stores"]["slot-contracts"]
        # candidate supply (what decides WHICH cards reach a row) is untouched
        assert store["candidate_supply"] == parent_store["candidate_supply"]
        for name in ("intent-boundaries", "train-exemplars"):
            assert diff["mine"].values["knowledge_stores"][name] == diff["parent"].values["knowledge_stores"][name]
        assert diff["mine"].values["phase_material"] == diff["parent"].values["phase_material"]
        assert diff["mine"].values["native_episode"] == diff["parent"].values["native_episode"]


def test_receipts_are_appended_not_rewritten() -> None:
    for experiment in (ARM, SMOKE):
        diff = _diff(experiment)
        old = diff["parent"].values["preparation_source_receipts"]
        new = diff["mine"].values["preparation_source_receipts"]
        assert new[: len(old)] == old
        assert [r["relpath"] for r in new[len(old):]] == [
            "knowledge/slurp/semantic/slot-contracts-w4-v1/completion.json",
            "knowledge/slurp/semantic/slot-contracts-w4-v1/release.json",
        ]
        # none as registered (HELD); the flip's re-pin pins this cell's OWN minted supply, never a foreign one
        supply = diff["mine"].values.get("prepared_phase_supply")
        assert supply is None or supply["relpath"].startswith(f"prepared/{RUN[experiment]}/"), supply


def test_cells_are_held_with_only_the_agreement_requirement() -> None:
    agreement = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl"
    for experiment in (ARM, SMOKE):
        cell = _read(REPO / "configs/experiment" / f"{experiment}.json")["cells"][0]
        # HELD with the agreement table alone as registered (6c2f6782); once flipped, the re-pin keeps the table
        # (the foreign-requirement fix a9c4b735) and adds the family decision and this cell's own supply -- the
        # COMP-1 flip is the pattern.
        state = cell["readiness"]["state"]
        assert state in ("held", "ready")
        reqs = cell["readiness"]["requirements"]
        if state == "held":
            assert [r["relpath"] for r in reqs] == [agreement]
        else:
            assert [r["relpath"] for r in reqs if r["kind"] == "preparation" and r["relpath"] == agreement] == [agreement]
            assert [r.get("expected_decision_id") for r in reqs if r["kind"] == "decision"] == [
                "slurp-stage3-w4-fold-a-admission-v1"]
            own = [r for r in reqs if r["kind"] == "preparation" and r["relpath"] != agreement]
            assert len(own) == 1 and own[0]["relpath"].startswith(f"prepared/{RUN[experiment]}/"), own
        assert cell["run_id"] == RUN[experiment]


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
    analogue = facts["expectation_basis"]["m4b_analogue"]["w4_expected_pp"]
    assert analogue["first"] < 2.5, "the analogue cleared the benefit floor; the declaration must be revisited"
    fence = PREREG.read_text(encoding="utf-8")
    assert '"replicate_run_id": "' + SHARED_AA + '"' in fence


def test_analysis_recipe_declares_its_read_run_id() -> None:
    recipe = _read(PACKAGE / "analysis-recipe-v1.json")
    assert recipe["run_ids"]["read"] == recipe["read_run_id"] == "SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1"
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    assert "| SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1 |" in ledger


def test_ledger_rows_have_fifteen_cells_and_no_stray_pipe() -> None:
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8").split("\n")
    ids = (RUN[ARM], "SAEA-SLURP-STAGE3-W4-FOLD-A-FIT-V1", RUN[SMOKE], "SAEA-SLURP-STAGE3-W4-FOLD-A-SMOKE-4-FIT-V1",
           "SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1", "SAEA-SLURP-SLOT-CONVENTIONS-W4-PREPARE-V1",
           "SAEA-SLURP-W4-FOLD-A-OFFLINE-ESTIMATE-V1")
    for run_id in ids:
        rows = [ln for ln in ledger if ln.startswith("|") and len(ln.split("|")) > 3 and ln.split("|")[2].strip() == run_id]
        assert len(rows) == 1, run_id
        assert len(rows[0].split("|")) == 17, run_id


def test_committed_tables_carry_values_of_closed_types_only() -> None:
    tables = _read(PACKAGE / "conventions-tables-v1.json")
    for row in tables["vocabulary"]:
        if row["class"] != "closed":
            assert row["closed_value_list"] is None, row["slot_type"]
    for row in tables["annotation_scope"]:
        assert set(row) >= {"tagged_when_spoken_counts", "usually_untagged_counts"}
        assert "tagged_when_spoken" not in row and "usually_untagged" not in row
