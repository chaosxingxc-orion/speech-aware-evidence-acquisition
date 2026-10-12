"""The construction-source lock column of the typed loop (coordinator resolution of 2026-10-11 to decision 263-A).

The proposer's tables and the ACE reflector's material come from ONE lock column flown on the construction roster R01C (TRAIN rows outside Fold
A and Fold B), never from Fold B. This file proves, model-free and in a WRITABLE OVERLAY of the repository (the real tree is never written):

* the roster R01C is disjoint from Fold A and Fold B by split identity AND by sample id, and the committed ``stage3-deltas-v1r`` registration's
  construction scope and permitted roster are R01C and a subset of it;
* the derived cell composes: the plain review-off lock (program ``phase-native-module-v1-c2``, two contacts per row, no column, no supply arm), the
  R01C pins, the FIT caps, the finite-completion policies, a resolving ``shared-rollout`` label, and requests byte-identical to lock v2.3's;
* the model-free gates see exactly the refusals an unsigned, unminted, unflipped cell owes, and the effect-floor gate accepts the new
  ``material-source`` design only without a benefit claim;
* the measured knowledge-source guard (the runner refuses a query sample inside the composite knowledge source roster) is recorded as a named blocker
  and agrees with the data root whenever the data root is present;
* the DRAFT discipline: HELD, DRAFT rows appended at the END of the ledger only on request, wrappers valid, the mint tool's new kind.

No contact, no ledger row in the real ledger, no flip. Synthetic and aggregate only; no utterance, gold label or model output appears here.
"""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
TFRL = REPO / "scripts" / "flights" / "tfrl"
for _extra in (REPO / "scripts" / "checks", TFRL, REPO / "src", REPO / "tests" / "unit"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import derive_tfrl_construction_cells as dc  # noqa: E402
import finite_completion_policy_check as finite_gate  # noqa: E402
import flight_registration_check as flight_gate  # noqa: E402
import stage3_effect_floor_check as floor_gate  # noqa: E402
import test_finite_completion_policy_check as finite_t  # noqa: E402
import tfrl_family as tf  # noqa: E402
import tfrl_overlay  # noqa: E402
import write_tfrl_construction_registration as creg  # noqa: E402
from test_stage3_effect_floor_check import _build as floor_build  # noqa: E402
from test_stage3_effect_floor_check import _declaration, _kinds as floor_kinds  # noqa: E402

from speech_aware_evidence_acquisition.core import roster as roster_module  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.stage3_algorithms import validate_stage3_algorithm_label  # noqa: E402
from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters import slurp_module_construction as variant  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402

COMMIT, AT = "c" * 40, "2026-10-11T12:00:00.000000+00:00"
DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
FOLD_A, FOLD_B = "docs/receipts/rosters/slurp-evo-fold-a-v2.json", "docs/receipts/rosters/slurp-evo-fold-b-v2.json"
PERMITTED = "docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json"
DEV_ROSTERS = ("docs/receipts/probe-samples/DEV-1000.json", "docs/receipts/rosters/slurp-dev-2000-added-v1.json",
               "docs/receipts/rosters/slurp-dev-2000-v1.json", "docs/receipts/rosters/slurp-dev-500-b-v1.json")


def ids_of(relpath: str) -> set[str]:
    document = json.loads((REPO / relpath).read_text(encoding="utf-8"))
    return {str(item.get("sample_id") or item["id"]) for item in document["items"]}


def baseline(root: Path, kind: str = "arm") -> dict:
    name = tf.const_names(kind)["baseline"]
    return json.loads((root / "configs" / "baseline" / f"{name}.json").read_text(encoding="utf-8"))


def experiment(root: Path, kind: str = "arm") -> dict:
    name = tf.const_names(kind)["experiment"]
    return json.loads((root / "configs" / "experiment" / f"{name}.json").read_text(encoding="utf-8"))


def fresh_overlay(dest: Path) -> Path:
    """A writable overlay in which THIS package's own files are real, empty-of-history files: ``make_overlay`` seeds every existing file and
    directory of ``docs/readiness`` and ``configs/*`` as a symlink to the real tree, so a write to a name that already exists in the repository
    would write THROUGH to it. The package directory, the preregistration, the cells' fragments and the campaign plan are unlinked, and the
    overlay's ledger copy loses this package's DRAFT block, so a registration run writes only inside the overlay and starts from a clean ledger."""

    root = tfrl_overlay.make_overlay(dest, REPO)
    names = [tf.const_names(kind) for kind in ("arm", "smoke")]
    victims = [root / tf.CONST_PACKAGE_DIR, root / tf.CONST_PREREG_RELPATH, root / names[0]["campaign"]]
    for n in names:
        victims += [root / "configs" / "baseline" / f"{n['baseline']}.json", root / "configs" / "experiment" / f"{n['experiment']}.json"]
    for victim in victims:
        if victim.is_symlink():
            victim.unlink()
    ledger = root / "docs" / "exposure-ledger.md"
    assert not ledger.is_symlink()
    text = ledger.read_text(encoding="utf-8")
    cut = text.find("\n## Loop construction-source lock column")
    if cut >= 0:
        ledger.write_text(text[:cut].rstrip("\n") + "\n", encoding="utf-8", newline="\n")
    return root


@pytest.fixture(scope="module")
def derived(tmp_path_factory):
    """The construction-source cells, derived and registered once in a writable overlay (with the DRAFT rows appended to its own ledger copy)."""

    root = fresh_overlay(tmp_path_factory.mktemp("overlay"))
    result = creg.write_package(root, COMMIT, AT, data_root=None, append_ledger=True)
    return SimpleNamespace(root=root, result=result)


# ---------------------------------------------------------------------------------------------------------------------------
# the roster: R01C is disjoint from Fold A and Fold B
# ---------------------------------------------------------------------------------------------------------------------------


def test_r01c_is_disjoint_from_fold_a_and_fold_b_by_split_identity_and_by_sample_id():
    r01c = json.loads((REPO / tf.CONST_ROSTER["arm"]).read_text(encoding="utf-8"))
    fold_a = json.loads((REPO / FOLD_A).read_text(encoding="utf-8"))
    fold_b = json.loads((REPO / FOLD_B).read_text(encoding="utf-8"))
    # the receipts verify (split identity recomputed from the item ids) and the three identities differ
    assert roster_module.verify_roster(r01c) == r01c["split_identity_hash"] == "f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515"
    assert roster_module.verify_roster(fold_a) == fold_a["split_identity_hash"]
    assert roster_module.verify_roster(fold_b) == fold_b["split_identity_hash"]
    assert len({r01c["split_identity_hash"], fold_a["split_identity_hash"], fold_b["split_identity_hash"]}) == 3
    ids, a_ids, b_ids = ids_of(tf.CONST_ROSTER["arm"]), ids_of(FOLD_A), ids_of(FOLD_B)
    assert len(ids) == tf.CONST_ROWS == 625 and len(a_ids) == len(b_ids) == 1080
    assert ids & a_ids == set() and ids & b_ids == set()
    # utterance level too (a recording of the same utterance is the same speech)
    utt = {str(i["utterance_id"]) for i in r01c["items"]}
    assert utt.isdisjoint({str(i["utterance_id"]) for i in fold_a["items"]}) and utt.isdisjoint({str(i["utterance_id"]) for i in fold_b["items"]})
    for rel in DEV_ROSTERS:
        assert ids & ids_of(rel) == set(), rel
    # the receipt's own recorded proof says the same
    proof = r01c["disjointness_proof"]
    for key in ("slurp-evo-fold-a-v2", "slurp-evo-fold-b-v2"):
        assert proof[key]["shared_recordings"] == 0 and proof[key]["shared_utterances"] == 0
    assert (r01c["roster_role"], r01c["split_role"]) == ("construction", "discovery")


def test_the_delta_store_scope_is_r01c_and_its_permitted_roster_is_a_subset_of_it():
    registration = json.loads((TFRL.parent.parent.parent / "docs/readiness/2026-10-11-slurp-tfrl-loop-v1/ace-playbook-i0-release-registration.json").read_text(encoding="utf-8"))
    r01c_sha = tf.sha256_file(REPO / tf.CONST_ROSTER["arm"])
    # the construction scope pinned by the committed registration is byte-identical to the committed R01C receipt
    assert registration["construction_scope"]["sha256"] == r01c_sha
    permitted_sha = tf.sha256_file(REPO / PERMITTED)
    assert registration["permitted_roster"]["sha256"] == permitted_sha
    permitted = json.loads((REPO / PERMITTED).read_text(encoding="utf-8"))
    assert permitted["split_identity_hash"] == registration["source_split_identity_hash"]
    assert len(ids_of(PERMITTED)) == 225 and ids_of(PERMITTED) <= ids_of(tf.CONST_ROSTER["arm"])
    forbidden = {pin["relpath"] for pin in registration["forbidden_rosters"]}
    assert forbidden == {FOLD_A, FOLD_B, "docs/receipts/probe-samples/DEV-1000.json"}
    assert ids_of(PERMITTED).isdisjoint(ids_of(FOLD_A) | ids_of(FOLD_B))


def test_the_smoke_roster_is_the_first_four_r01c_rows():
    smoke = json.loads((REPO / tf.CONST_ROSTER["smoke"]).read_text(encoding="utf-8"))
    ids = [str(i["sample_id"]) for i in json.loads((REPO / tf.CONST_ROSTER["arm"]).read_text(encoding="utf-8"))["items"]]
    assert [str(i["sample_id"]) for i in smoke["items"]] == ids[:4] and roster_module.verify_roster(smoke) == smoke["split_identity_hash"]


# ---------------------------------------------------------------------------------------------------------------------------
# composition
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_cell_is_the_plain_review_off_lock_with_two_contacts_and_no_column(derived):
    document = baseline(derived.root)
    block = document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
    assert document["policy"] == tf.CONST_PROGRAM == "phase-native-module-v1-c2"
    assert block["lock"] == tf.CONST_LOCK == "v2.2" and block["columns"] == [] and block["review_loop"] == "off"
    assert "template_frame" not in block and "supply_frame" not in block
    episode = document["native_episode"]
    assert (episode["review_loop"], episode["max_revisions"]) == ("off", 0)
    assert episode["finite_completion_policy"] == "deliver-latest-or-abstain" and episode["react_exhaustion_policy"] == "continue-without-answer"
    assert "supply_variants" not in json.dumps(episode["roles"]) and "template_variants" not in json.dumps(episode["roles"])
    assert "prepared_phase_supply" not in document
    assert document["scorers"] == ["slurp-slu-official-train", "cost"]
    states = {c["component_id"]: c["state"] for c in block["components"]}
    assert states[cm.AGREE_VOTE_SEED] == states[cm.CENTROID_BOUNDARY_KEY] == "on"
    assert [k for k, v in states.items() if v == "on"] == [cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY]
    # FIT caps: rows x contacts x 4 endpoints
    assert document["native_contact_fit"]["contact_cap"] == 625 * 2 * 4 == 5000
    assert baseline(derived.root, "smoke")["native_contact_fit"]["contact_cap"] == 4 * 2 * 4
    assert document["native_contact_fit"]["run_id"] == tf.const_names("arm")["fit_run_id"]
    # the loader accepts the cell under the real carrier hooks
    assert derived.result["loader_verification"] == {"ok": True, "refusal": None}
    cm.verify_declared_module(block, document, repo_root=derived.root)
    parsed = load_native_episode_config(dict(document, carrier_lock_key="slurp"), default_phase_program(document["policy"]))
    assert parsed.max_contacts == 2 and parsed.supply_variant_group is None


def test_the_cell_pins_r01c_vectors_and_the_roster_s_own_built_agreement_table(derived):
    document = baseline(derived.root)
    perception = document["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    solver = document["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    assert perception["query_source"]["relpath"] == "vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-segments.jsonl"
    assert solver["query_source"]["relpath"] == "vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-content-v1.jsonl"
    assert "fold-b" not in json.dumps(document).lower() and "nx-r6" not in json.dumps(document).lower()
    seed = next(c for c in document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]["components"] if c["component_id"] == cm.AGREE_VOTE_SEED)
    source = seed["params"]["agreement_source"]
    assert source["relpath"] == dc.AGREEMENT_RELPATH and source["tool_contact_ledger_row"] == dc.AGREEMENT_ID
    assert source["sha256"] == variant.R01C_AGREEMENT["sha256"] == "87e253f66f3b5058e7c778034c343c4e9f0b43586d623d8e1fe6508f9bf3abb3"
    # the packet promotion receipt is the R01 one (the R01C rows are a selection of it)
    assert "CONSTRUCTION-R01" in document["speech_packet_promotion_receipt"]
    requirements = experiment(derived.root)["cells"][0]["readiness"]["requirements"]
    assert [r["kind"] for r in requirements] == ["decision", "preparation", "preparation"]
    assert requirements[1]["relpath"] == dc.AGREEMENT_RELPATH and requirements[1]["sha256"] == variant.R01C_AGREEMENT["sha256"]
    # the pool receipt of the variant is pinned beside the roster receipts; the full-pool receipt is not
    receipts = {r["relpath"]: r for r in document["preparation_source_receipts"]}
    assert "docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars-minus-r01.json" in receipts
    assert "docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars.json" not in receipts
    assert receipts[dc.AGREEMENT_RECEIPT_RELPATH]["sha256"] == variant.R01C_AGREEMENT_RECEIPT_SHA256


def test_the_variant_moves_only_the_pool_pins_and_refuses_lock_v2_3(derived):
    """The construction variant on v2.2 differs from the plain v2.2 compile in exactly the two pool leaves; v2.3 (whose inert ace-playbook
    anchor names 50 R01C ids) is refused, and P-ACE-0 makes the v2.2 choice cost nothing (the plain v2.2 and v2.3 policy blocks differ only by
    that store)."""

    block = baseline(derived.root)["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
    assert block["construction_roster"] == "r01c" and block["lock"] == "v2.2"
    hooks = carrier_module_hooks(repo_root=derived.root)
    plain_block = {k: v for k, v in block.items() if k != "construction_roster"}
    on_variant = cm.compile_module(block, hooks, repo_root=derived.root)
    on_plain = cm.compile_module(plain_block, hooks, repo_root=derived.root)
    assert cm.differing_paths(on_variant.values(), on_plain.values()) == [
        "knowledge_stores.train-exemplars.release.relpath", "knowledge_stores.train-exemplars.release.sha256",
        "knowledge_stores.train-exemplars.snapshot.relpath", "knowledge_stores.train-exemplars.snapshot.sha256"]
    assert on_variant.program_id == on_plain.program_id == tf.CONST_PROGRAM
    with pytest.raises(cm.ConsumptionModuleConfigError, match="ace-playbook"):
        cm.compile_module({**block, "lock": "v2.3"}, hooks, repo_root=derived.root)
    a, b = on_plain.values(), cm.compile_module({**plain_block, "lock": "v2.3"}, hooks, repo_root=derived.root).values()
    assert set(b["knowledge_stores"]) - set(a["knowledge_stores"]) == {tf.ACE_STORE_ID}
    assert {k: v for k, v in b["knowledge_stores"].items() if k != tf.ACE_STORE_ID} == a["knowledge_stores"]
    assert all(a[key] == b[key] for key in a if key != "knowledge_stores")


def test_the_experiment_fragments_are_held_and_carry_the_r01c_population(derived):
    for kind, rows in (("arm", 625), ("smoke", 4)):
        names = tf.const_names(kind)
        doc = experiment(derived.root, kind)
        cell = doc["cells"][0]
        assert cell["readiness"]["state"] == "held" and cell["cell_id"] == names["experiment"] and cell["run_id"] == names["run_id"]
        assert cell["dataset_fragment"] == tf.CONST_DATASET and doc["split_id"] == tf.CONST_SPLIT_ID
        roster = json.loads((REPO / tf.CONST_ROSTER[kind]).read_text(encoding="utf-8"))
        assert doc["population"]["count"] == rows and doc["population"]["split_identity_hash"] == roster["split_identity_hash"]
        assert doc["populations"][0]["ids"] == [i["sample_id"] for i in roster["items"]]
        assert doc["execution_profile"] == "bounded-discovery-probe" and doc["execution_plan"]["split_role"] == "discovery"
        assert doc["family_budget"]["generation_calls_cap"] == rows * 2
        assert kind == "smoke" or doc["generation_budget"]["cap"] == rows * 2
        assert doc["family_budget"]["fit_endpoint_calls_cap"] == rows * 2 * 4
        assert doc["family_budget"]["official_complete_scoring_jobs"] == (1 if kind == "arm" else 0)
        text = json.dumps(doc)
        assert "nx-r6" not in text.lower() and "fold-b" not in text.lower()
        composed = compose(derived.root, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], names["experiment"])
        assert composed.values["policy"] == tf.CONST_PROGRAM and composed.values["carrier_lock_key"] == "slurp"
    assert experiment(derived.root)["cells"][0]["allowed_execution_stages"] == ["check", "prepare-supply", "worker", "campaign"]
    assert experiment(derived.root, "smoke")["cells"][0]["allowed_execution_stages"] == ["check", "prepare-supply", "worker"]


def test_derivation_is_idempotent(derived):
    names = tf.const_names("arm")
    files = [derived.root / "configs" / "baseline" / f"{names['baseline']}.json",
             derived.root / "configs" / "experiment" / f"{names['experiment']}.json", derived.root / names["campaign"]]
    before = [f.read_bytes() for f in files]
    dc.derive(repo_root=derived.root)
    assert [f.read_bytes() for f in files] == before


def test_the_committed_cells_equal_a_fresh_derivation(tmp_path):
    root = fresh_overlay(tmp_path / "o")
    assert not (root / "configs" / "baseline" / f"{tf.const_names('arm')['baseline']}.json").exists()
    dc.derive(repo_root=root)
    for kind in ("arm", "smoke"):
        names = tf.const_names(kind)
        for sub, key in (("baseline", "baseline"), ("experiment", "experiment")):
            rel = f"configs/{sub}/{names[key]}.json"
            assert (root / rel).read_bytes() == (REPO / rel).read_bytes(), rel


def test_every_policy_and_scorer_value_resolves_in_the_core_registries(derived):
    from speech_aware_evidence_acquisition.core import base

    values = baseline(derived.root)
    default_phase_program(values["policy"])
    assert values["evidence_source"] in base.EVIDENCE_SOURCES.names()
    for scorer in values["scorers"]:
        assert scorer in base.SCORERS.names()


# ---------------------------------------------------------------------------------------------------------------------------
# hashes and labels
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_registered_plans_pin_the_recomputed_config_and_protocol_hashes(derived):
    from speech_aware_evidence_acquisition.core.config import protocol_hash

    pkg = derived.root / tf.CONST_PACKAGE_DIR
    for kind in ("arm", "smoke"):
        names = tf.const_names(kind)
        doc = experiment(derived.root, kind)
        cell = doc["cells"][0]
        composed = compose(derived.root, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], names["experiment"])
        expected = protocol_hash(composed.config_hash, composed.values["arm"], doc["population"]["split_identity_hash"])
        for plan_kind in ("generation", "fit"):
            plan = json.loads((pkg / f"{names['prefix']}{plan_kind}-plan-registered-v1.json").read_text(encoding="utf-8"))
            assert plan["composed_config_hash"] == composed.config_hash and plan["execution_plan"]["protocol_hash"] == expected
            assert plan["execution_plan"]["split_identity_hash"] == doc["population"]["split_identity_hash"]
            assert plan["execution_plan"]["split_role"] == "discovery" and plan["status"].startswith("DRAFT-HELD")
            assert plan["prepared_phase_supply"]["sha256"] == "MINTED_AT_THE_FLIP"
    facts = json.loads((pkg / "registered-facts-v1.json").read_text(encoding="utf-8"))
    assert facts["composed_config_hashes"]["arm"] == json.loads((pkg / "generation-plan-registered-v1.json").read_text(encoding="utf-8"))["composed_config_hash"]
    assert facts["accounting"]["contacts_per_row"] == 2 and facts["accounting"]["lock"] == "v2.2"


def test_the_label_resolves_as_shared_rollout_and_the_label_gate_accepts_the_cells(derived):
    import stage3_algorithm_label_check as label_gate

    for kind in ("arm", "smoke"):
        doc = experiment(derived.root, kind)
        record, used = validate_stage3_algorithm_label(doc["stage3_algorithm"], cell=doc["cells"][0]["cell_id"])
        assert record.id == "shared-rollout" and set(used) == {"rollout", "scoring"}
    result = label_gate.evaluate(derived.root)
    assert result["passed"] is True and result["violations"] == []
    mine = [c for c in result["stage3_cells"] if c["cell"] in (tf.const_names("arm")["experiment"], tf.const_names("smoke")["experiment"])]
    assert len(mine) == 2 and {c["algorithm_id"] for c in mine} == {"shared-rollout"}


# ---------------------------------------------------------------------------------------------------------------------------
# gates
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_finite_completion_gate_passes_the_derived_cell(derived, tmp_path):
    finite_t._build(tmp_path, policy="deliver-latest-or-abstain")
    path = tmp_path / "configs" / "baseline" / f"{finite_t.BASELINE}.json"
    path.write_text(json.dumps(baseline(derived.root), indent=2, sort_keys=True), encoding="utf-8")
    result = finite_gate.evaluate(tmp_path)
    assert result["passed"] is True and result["violations"] == []
    broken = baseline(derived.root)
    broken["native_episode"].pop("react_exhaustion_policy")
    path.write_text(json.dumps(broken, indent=2, sort_keys=True), encoding="utf-8")
    assert not finite_gate.evaluate(tmp_path)["passed"]


def measurement(root: Path, kind: str = "arm") -> tuple[str, dict]:
    facts = json.loads((root / tf.CONST_PACKAGE_DIR / "registered-facts-v1.json").read_text(encoding="utf-8"))
    run_id = tf.const_names(kind)["run_id"]
    return run_id, facts["stage3_measurement"][run_id]


def test_the_effect_floor_gate_accepts_material_source_without_a_benefit_claim(derived, tmp_path):
    assert "material-source" in floor_gate.DESIGNS and floor_gate.floor_for("material-source", 625)[0] is None
    run_id, block = measurement(derived.root)
    assert block["measurement_design"] == "material-source" and block["claims_benefit"] is False and block["expected_effect_pp"] == 0.0
    assert block["rows"] == 625
    declaration = _declaration(measurement_design=block["measurement_design"], expected_effect_pp=block["expected_effect_pp"], rows=block["rows"],
                               claims_benefit=block["claims_benefit"])
    floor_build(tmp_path, declaration=declaration, rows=625, registered_date="2026-10-11", run_id=run_id)
    assert floor_kinds(floor_gate.evaluate(tmp_path)) == []
    # a benefit claim under this design is refused, exactly as for a form proof
    claimed = tmp_path / "claimed"
    claimed.mkdir()
    floor_build(claimed, declaration=_declaration(measurement_design="material-source", expected_effect_pp=2.0, rows=625, claims_benefit=True),
                rows=625, registered_date="2026-10-11")
    assert floor_kinds(floor_gate.evaluate(claimed)) == ["form-proof-claims-benefit"]
    smoke_id, smoke_block = measurement(derived.root, "smoke")
    assert smoke_block["measurement_design"] == "form-proof" and smoke_block["claims_benefit"] is False and smoke_block["rows"] == 4


def test_flight_registration_owes_only_the_pre_flip_refusals(derived, tmp_path):
    """``flight_registration_check --cell`` over the DERIVED cells and the DRAFT ledger rows appended in the overlay's own ledger copy."""

    data = tmp_path / "data"
    data.mkdir()
    owed = {"not-ready", "row-not-countersigned", "receipt-missing", "registered-supply-binding"}
    for kind in ("arm", "smoke"):
        cell = tf.const_names(kind)["experiment"]
        result = flight_gate.evaluate(derived.root, data, derived.root / "docs" / "exposure-ledger.md", cells=[f"{cell}:{cell}"])
        kinds = {f["kind"] for c in result["cells"] for f in c["findings"]}
        assert kinds <= owed, kinds
        assert {"not-ready", "row-not-countersigned", "receipt-missing"} <= kinds
        assert not result["passed"]


# ---------------------------------------------------------------------------------------------------------------------------
# the knowledge-source guard (the named blocker) and the cost
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_measured_guard_is_clean_and_the_resolved_blockers_are_recorded():
    facts = json.loads((REPO / tf.CONST_PACKAGE_DIR / "registered-facts-v1.json").read_text(encoding="utf-8"))
    assert facts["blockers"] == []
    assert {b["id"] for b in facts["resolved_blockers"]} == {"knowledge-source-guard", "agreement-table-owed", "ace-i0-anchor-sources-inside-r01c",
                                                             "ace-prior-score-outside-unit-interval"}
    guard = facts["knowledge_source_guard"]
    assert guard["measured"] is True and guard["roster_rows"] == 625
    pool = guard["stores"]["train-exemplars"]
    assert pool["shared_with_roster"] == 0 and pool["declared_by_this_cell"] is True and guard["cell_conflict_rows"] == 0
    # the other two declared stores are clean; lock v2.3's ace-playbook store is NOT declared by this cell (its 50 sources lie inside R01C)
    assert guard["stores"]["intent-boundaries"]["shared_with_roster"] == 0 and guard["stores"]["slot-contracts"]["shared_with_roster"] == 0
    assert guard["stores"][tf.ACE_STORE_ID]["shared_with_roster"] == 50 and guard["stores"][tf.ACE_STORE_ID]["declared_by_this_cell"] is False
    remedy = next(b for b in facts["resolved_blockers"] if b["id"] == "knowledge-source-guard")["pool_remedy"]
    assert remedy["shared_with_r01c"] == 0 and remedy["source_ids"] == 34474
    # the cell pins exactly the snapshot the guard measured
    declared = baseline(REPO)["knowledge_stores"]["train-exemplars"]["snapshot"]
    assert declared["sha256"] == pool["snapshot_sha256"]


@pytest.mark.skipif(not (DATA / "knowledge").is_dir(), reason="the data root is not mounted")
def test_the_guard_measured_now_equals_the_recorded_one():
    measured = dc.knowledge_source_guard(DATA, REPO)
    recorded = json.loads((REPO / tf.CONST_PACKAGE_DIR / "registered-facts-v1.json").read_text(encoding="utf-8"))["knowledge_source_guard"]
    assert measured == recorded
    minus = json.loads((DATA / creg.POOL_REMEDY["snapshot"]).read_text(encoding="utf-8"))["source_sample_ids"]
    assert len(minus) == creg.POOL_REMEDY["source_ids"] and set(minus).isdisjoint(ids_of(tf.CONST_ROSTER["arm"]))


def test_the_cost_estimate_follows_the_measured_throughput(derived):
    facts = json.loads((derived.root / tf.CONST_PACKAGE_DIR / "registered-facts-v1.json").read_text(encoding="utf-8"))
    cost = facts["accounting"]["cost_estimate"]
    assert cost["contacts"] == 1250 and cost["gpu_hours_expected"] == pytest.approx(1.38 * 0.625, abs=0.001)
    assert cost["gpu_hours_planned_cap"] >= cost["gpu_hours_expected"]
    arm = experiment(derived.root)
    assert arm["execution_plan"]["planned_model_calls"] == 1250 and arm["execution_plan"]["planned_gpu_hours"] == tf.CONST_PLANNED_GPU_HOURS_ARM
    assert arm["execution_plan"]["planned_speech_audio_seconds"] == 5454       # ceil(2,726.847 s x 2 contacts)


# ---------------------------------------------------------------------------------------------------------------------------
# the DRAFT discipline
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_package_is_draft_held_and_the_rows_sit_at_the_end_of_the_overlay_ledger(derived):
    pkg = derived.root / tf.CONST_PACKAGE_DIR
    for name in ("README.md", "registered-facts-v1.json", "root-admission-draft-v1.json", "draft-ledger-rows.md"):
        assert "DRAFT" in (pkg / name).read_text(encoding="utf-8"), name
    draft = json.loads((pkg / "root-admission-draft-v1.json").read_text(encoding="utf-8"))
    arm, smoke = tf.const_names("arm"), tf.const_names("smoke")
    assert draft["status"] == "DRAFT-NOT-MINTED" and draft["recorded_at_utc"] is None
    assert draft["decision_id"] == arm["decision_id"] == "slurp-tfrl-construction-lock-r01c-admission-v1"
    assert draft["eligible_run_ids"] == [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]]
    assert draft["population"]["fold_b_contact_authorized"] is False and draft["population"]["fold_a_contact_authorized"] is False
    ledger = (derived.root / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    block = (pkg / "draft-ledger-rows.md").read_text(encoding="utf-8")
    assert ledger.rstrip("\n").endswith(block.rstrip("\n"))                 # the DRAFT block is the LAST thing in the ledger
    for run_id in (arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"], arm["read_run_id"], dc.AGREEMENT_ID):
        assert ledger.count(f"| {run_id} |") == 1, run_id
    rows = [line for line in block.splitlines() if line.startswith("| 2026-")]
    assert len(rows) == 6 and all("| no |" in r and "DRAFT" in r for r in rows)
    # the branch's own ledger carries each DRAFT row exactly once (appended once, at the end); the overlay's append left it alone
    real = (REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    assert real.count(f"| {arm['run_id']} |") == 1 and real.count(f"| {dc.AGREEMENT_ID} |") == 1


def test_append_ledger_is_off_by_default(tmp_path):
    root = fresh_overlay(tmp_path / "o")
    before = (root / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    creg.write_package(root, COMMIT, AT, data_root=None)
    assert (root / "docs" / "exposure-ledger.md").read_text(encoding="utf-8") == before


def test_the_committed_package_matches_a_fresh_registration(tmp_path):
    """Re-running the writer reproduces the committed package byte for byte (the data root measurement aside: it is read from the facts)."""

    root = fresh_overlay(tmp_path / "o")
    commit = json.loads((REPO / tf.CONST_PACKAGE_DIR / "registered-facts-v1.json").read_text(encoding="utf-8"))["study_commit_at_registration"]
    if not DATA.is_dir():
        pytest.skip("the data root is not mounted; the facts embed its measurement")
    creg.write_package(root, commit, "2026-10-11T12:00:00.000000+00:00", data_root=DATA)
    for path in sorted((REPO / tf.CONST_PACKAGE_DIR).iterdir()):
        assert (root / tf.CONST_PACKAGE_DIR / path.name).read_bytes() == path.read_bytes(), path.name


def test_the_package_says_what_the_resolution_is(derived):
    text = (derived.root / tf.CONST_PACKAGE_DIR / "README.md").read_text(encoding="utf-8")
    for needle in ("iterations 1-3", "refused-candidate buffer", "ACE counters", "numbers, not knowledge", "re-flown only if the lock changes",
                   "knowledge-source-guard", "stage3-deltas-v1r", "no benefit claim"):
        assert needle in text, needle
    prereg = (derived.root / tf.CONST_PREREG_RELPATH).read_text(encoding="utf-8")
    assert "material source for iterations 1-3 of the typed loop; no benefit claim; it is re-flown only if the lock changes" in prereg
    assert '"measurement_design": "material-source"' in prereg


# ---------------------------------------------------------------------------------------------------------------------------
# wrappers and the mint tool
# ---------------------------------------------------------------------------------------------------------------------------


WRAPPERS = ["tfrl_const_flip.sh", "tfrl_const_repin_arm.sh", "tfrl_const_repin_smoke.sh", "tfrl_const_read.sh", "batch_chain_tfrl_const.sh"]


def test_the_wrappers_are_lf_valid_shell_and_name_scripts_that_exist():
    import shutil

    for name in WRAPPERS:
        raw = (TFRL / name).read_bytes()
        assert b"\r" not in raw, f"{name} has CR bytes"
        text = raw.decode("utf-8")
        assert text.startswith("#!/bin/bash")
        assert "--allow-output-change" not in text.replace("--allow-output-change must never be passed", "").replace("ALLOW_OUTPUT_CHANGE", ""), name
        if shutil.which("bash"):
            assert subprocess.run(["bash", "-n", str(TFRL / name)], capture_output=True).returncode == 0, name
        for ref in re.findall(r"(?:\$TF|\$SP|\$MAIN/scripts/flights/(?:tfrl|batch))/([A-Za-z0-9_]+\.(?:sh|py))", text):
            assert (TFRL / ref).exists() or (REPO / "scripts" / "flights" / "batch" / ref).exists(), (name, ref)
    flip = (TFRL / "tfrl_const_flip.sh").read_text(encoding="utf-8")
    assert "convergence pass" in flip and "for pass in 1 2 3 4" in flip and "repin_loop_generic.sh" in flip and "--kind construction" in flip
    chain = (TFRL / "batch_chain_tfrl_const.sh").read_text(encoding="utf-8")
    assert "core.flight.cli|batch_driver.sh" in chain and tf.SESSION in chain and "tfrl-construction-lock-r01c" in chain
    read = (TFRL / "tfrl_const_read.sh").read_text(encoding="utf-8")
    assert "--rows 625" in read and "slurp-slu-official-train" in read and "read_require_countersigned" in read


def test_the_wrapper_identities_equal_the_family_names():
    arm, smoke = tf.const_names("arm"), tf.const_names("smoke")
    arm_sh = (TFRL / "tfrl_const_repin_arm.sh").read_text(encoding="utf-8")
    smoke_sh = (TFRL / "tfrl_const_repin_smoke.sh").read_text(encoding="utf-8")
    slug = tf.CONST_SLUG
    assert arm["experiment"] == f"slurp-native-stage3-{slug}-v1" and smoke["experiment"] == f"slurp-native-stage3-{slug}-smoke-4-v1"
    assert "CELL=slurp-native-stage3-$SLUG-v1" in arm_sh and "CELL=slurp-native-stage3-$SLUG-smoke-4-v1" in smoke_sh
    for text in (arm_sh, smoke_sh):
        assert f"SLUG={slug}" in text and "DEC_ID=slurp-$SLUG-admission-v1" in text
        assert "DEC_PATH=coordination/slurp-$SLUG-v1/root-admission-v1.json" in text and "PKG=slurp-$SLUG-v1" in text
        assert tf.CONST_PREREG_RELPATH in text and tf.CONST_PACKAGE_DIR in text
    assert arm["decision_id"] == f"slurp-{slug}-admission-v1"
    assert arm["decision_path"] == f"coordination/slurp-{slug}-v1/root-admission-v1.json"
    read = (TFRL / "tfrl_const_read.sh").read_text(encoding="utf-8")
    assert f"SLUG={slug}" in read and arm["read_run_id"] == f"SAEA-SLURP-STAGE3-{slug.upper()}-COLUMN-READ-V1"


def test_the_mint_tool_has_a_construction_kind_that_never_overwrites(derived, tmp_path, monkeypatch, capsys):
    import tfrl_mint_receipt as mint

    monkeypatch.setattr(mint, "ROOT", str(derived.root))
    monkeypatch.setattr(mint, "DATA", str(tmp_path / "data"))
    assert mint.main(["--kind", "construction", "--dry"]) == 0
    assert "(dry) would write" in capsys.readouterr().out
    assert mint.main(["--kind", "construction"]) == 0
    out = tmp_path / "data" / "coordination" / "slurp-tfrl-construction-lock-r01c-v1" / "root-admission-v1.json"
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["status"] == "decided" and receipt["decision_id"] == "slurp-tfrl-construction-lock-r01c-admission-v1"
    assert len(receipt["eligible_run_ids"]) == 4
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        mint.main(["--kind", "construction"])
