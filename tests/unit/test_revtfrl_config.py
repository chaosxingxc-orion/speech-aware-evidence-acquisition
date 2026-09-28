"""Cell REV-TFRL-1 -- the first training-free RL optimisation of the Reviewer node (owner decision
165) -- is the AGREE arm with ONE pin moved (the Reviewer instruction), read at an in-chain A/A that is
the base the brief names (AGREE with G5's Reviewer instruction).

Config only: no data root, no lock, no adapter, no contact.
"""

from __future__ import annotations

import difflib
import hashlib
import io
import json
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core import stage3_algorithms as registry
from speech_aware_evidence_acquisition.core.config import compose

REPO = Path(__file__).resolve().parents[2]

ARM = "slurp-native-stage3-revtfrl-fold-a-v1"
AA = "slurp-native-stage3-revtfrl-aa-fold-a-v1"
SMOKE = "slurp-native-stage3-revtfrl-fold-a-smoke-4-v1"
RUNS = {
    ARM: ("SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-V1", "SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-FIT-V1"),
    AA: ("SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-V1", "SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-FIT-V1"),
    SMOKE: ("SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-SMOKE-4-FIT-V1"),
}
PARENT = {ARM: "slurp-native-stage3-agree-w1-fold-a-v1", AA: "slurp-native-stage3-agree-w1-fold-a-v1",
          SMOKE: "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"}
ONE_PIN = "phase_material.reviewer.instruction_template"
BOOKKEEPING = ("native_contact_fit.", "prepared_phase_supply", "what_this_is")
NEW = "probes/slurp_native_role_reviewer_contrastive_v1.txt"
G5 = "probes/slurp_native_role_reviewer_v1_g5_v1.txt"
SOURCE = "probes/slurp_native_role_reviewer_candidate_recovery_v1.txt"
AGREEMENT = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl"
AGREEMENT_SHA = "018ca6ef0d10bbf8d19645994420820faf7f31961cf91a6080116e4b434016c1"
DECISION_ID = "slurp-stage3-revtfrl-fold-a-admission-v1"
CAMPAIGN = REPO / "configs/campaign/slurp-native-stage3-revtfrl-fold-a-v1.json"


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
    return document, compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"],
                             experiment)


def _diff(experiment: str) -> dict:
    document, mine = _compose(experiment)
    parent_doc, parent = _compose(PARENT[experiment])
    baseline_keys = set(_read(REPO / "configs/baseline" / (parent_doc["cells"][0]["baseline_fragment"] + ".json")))
    experiment_keys = set(document) | set(parent_doc)
    assert not (experiment_keys & baseline_keys)
    a, b = _flatten(parent.values), _flatten(mine.values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    one_pin = [k for k in changed if k == ONE_PIN]
    bookkeeping = [k for k in changed if k.startswith(BOOKKEEPING)]
    block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in one_pin and k not in bookkeeping]
    other = [k for k in changed if k not in one_pin and k not in bookkeeping and k not in block]
    return {"one_pin": one_pin, "other": other, "values": mine.values, "parent": parent.values}


@pytest.mark.parametrize("experiment", [ARM, AA, SMOKE])
def test_the_composed_config_moves_the_reviewer_pin_and_bookkeeping_only(experiment: str) -> None:
    diff = _diff(experiment)
    assert diff["other"] == []
    assert diff["one_pin"] == [ONE_PIN]
    expected = G5 if experiment == AA else NEW
    assert diff["values"]["phase_material"]["reviewer"]["instruction_template"] == expected
    assert diff["parent"]["phase_material"]["reviewer"]["instruction_template"] == "probes/slurp_native_role_reviewer_v1.txt"
    mine = {k: v for k, v in diff["values"]["phase_material"].items() if k != "reviewer"}
    theirs = {k: v for k, v in diff["parent"]["phase_material"].items() if k != "reviewer"}
    assert mine == theirs, "the Perception / Solver / Planner material must be the AGREE arm's"


@pytest.mark.parametrize("experiment", [ARM, AA, SMOKE])
def test_the_base_is_the_agree_form_with_no_tools_and_no_committed_supply(experiment: str) -> None:
    _document, composed = _compose(experiment)
    values = composed.values
    perception = values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    assert perception["rank_weights"] == {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 1.0}
    assert perception["k"] == 60 and perception["fuse_coverage"] == {"m": 8, "c": 1, "top_l": 8}
    assert perception["agreement_source"]["relpath"] == AGREEMENT
    assert "phase_tools" not in values
    # HELD as registered; the flip's re-pin mints this cell's OWN first-phase supply under its
    # own run id (item E16), never a foreign one -- the COMP-1 flip is the pattern.
    supply = values.get("prepared_phase_supply")
    run_id = RUNS[experiment][0]
    assert supply is None or _is_own_supply(supply["relpath"], run_id), supply


@pytest.mark.parametrize("experiment", [ARM, AA, SMOKE])
def test_ids_readiness_and_label(experiment: str) -> None:
    document = _read(REPO / "configs/experiment" / f"{experiment}.json")
    cell = document["cells"][0]
    run_id, fit_run_id = RUNS[experiment]
    assert cell["run_id"] == run_id
    baseline = _read(REPO / "configs/baseline" / f"{cell['baseline_fragment']}.json")
    assert baseline["native_contact_fit"]["run_id"] == fit_run_id
    readiness = cell["readiness"]
    assert readiness["state"] in ("held", "ready")
    agreement_reqs = [r for r in readiness["requirements"] if r["relpath"] == AGREEMENT]
    assert len(agreement_reqs) == 1
    assert agreement_reqs[0]["sha256"] == AGREEMENT_SHA
    decisions = [r for r in readiness["requirements"] if r.get("kind") == "decision"]
    if readiness["state"] == "held":
        assert [r["relpath"] for r in readiness["requirements"]] == [AGREEMENT]
        assert not decisions
    else:
        assert [d["expected_decision_id"] for d in decisions] == [DECISION_ID]
        own = [r for r in readiness["requirements"] if r["kind"] == "preparation" and r["relpath"] != AGREEMENT]
        assert len(own) == 1 and _is_own_supply(own[0]["relpath"], run_id), own
    record, used = registry.validate_stage3_algorithm_label(document["stage3_algorithm"], cell=experiment)
    if experiment == AA:
        assert record.id == "none" and used == ()
    else:
        assert record.id == "sealed-credit-system-policy-v1" and used == ("context_application",)
    assert ("campaign" in cell["allowed_execution_stages"]) is (experiment != SMOKE)


def test_the_campaign_flies_the_aa_then_the_arm_in_one_chain() -> None:
    plan = _read(CAMPAIGN)
    assert [c["cell"] for c in plan["cells"]] == [AA, ARM]


def test_the_arm_and_the_aa_share_every_cap() -> None:
    arm = _read(REPO / "configs/experiment" / f"{ARM}.json")
    aa = _read(REPO / "configs/experiment" / f"{AA}.json")
    agree = _read(REPO / "configs/experiment" / f"{PARENT[ARM]}.json")
    assert arm["family_budget"] == aa["family_budget"] == agree["family_budget"]
    assert arm["execution_plan"] == agree["execution_plan"]


def test_the_new_instruction_is_the_sealed_contrastive_text_with_the_registered_edits_only() -> None:
    source = io.open(REPO / "configs" / SOURCE, encoding="utf-8").read().split()
    new = io.open(REPO / "configs" / NEW, encoding="utf-8").read().split()
    edits = [(tag, " ".join(source[i1:i2]), " ".join(new[j1:j2]))
             for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=source, b=new, autojunk=False).get_opcodes()
             if tag != "equal"]
    removed = " ".join(e[1] for e in edits)
    added = " ".join(e[2] for e in edits)
    # the renamed structures, the deleted tool clause, and the kept transcript boundary -- nothing else
    for word in ("proposal.", "exemplar-supported", "additions", "exposed", "tools"):
        assert word in removed
    for word in ("Perception", "retrieved", "examples", "transcript,"):
        assert word in added
    assert len(" ".join(new)) - len(" ".join(source)) < 60
    text = " ".join(new).lower()
    assert "tool call" not in text and "call only tools" not in text
    assert "competing intent" in text and "do not assume the draft is wrong" in text


def test_the_package_pins_the_instruction_bytes_when_present() -> None:
    proof_path = REPO / "docs/readiness/2026-09-27-slurp-stage3-reviewer-tfrl-v1/instruction-edit-proof-v1.json"
    if not proof_path.is_file():
        pytest.skip("the registration package has not been written yet")
    proof = _read(proof_path)
    assert proof["new"]["sha256"] == hashlib.sha256((REPO / "configs" / NEW).read_bytes()).hexdigest()
    assert proof["replaces"]["sha256"] == hashlib.sha256((REPO / "configs" / G5).read_bytes()).hexdigest()
