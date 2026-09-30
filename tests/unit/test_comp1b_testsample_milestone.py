"""The COMP-1b TEST-SAMPLE milestone registration (owner decisions 151 and 202): model-free proofs.

* the committed package refuses to flip today (FIT run ids not named by allowance v1, pending pins;
  the expectation is re-declared from the A2 read) -- the preflip gate on the committed tree;
* the same gate passes on a FAKE tree where every blocker is cleared, and refuses each blocker alone;
* the two milestone cells pin the committed allowance, name its read run ids, score with the TEST
  sibling and carry no smoke.

No media, no gold, no data root beyond a tmp directory.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "flights" / "comp1"))

from comp1b_testsample_preflip_check import CELLS, PACKAGE, ZERO, refusals  # noqa: E402

ALLOWANCE = "docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json"


def _experiment(root: Path, cell: str) -> dict:
    return json.loads((root / "configs/experiment" / f"{cell}.json").read_text(encoding="utf-8"))


def test_committed_package_is_blocked_on_every_named_blocker():
    # Current blocker set (2026-09-30): the expectation is re-declared from the A2 read (e36bee27f);
    # what remains is the allowance v2 naming the FIT run ids (owner decision 207), the pending
    # sample-preparation pins, and the owner countersign / read-driver gates named in the facts file.
    facts = json.loads((REPO / PACKAGE / "registered-facts-v1.json").read_text(encoding="utf-8"))
    assert facts["redeclared_from_a2_read"] is True
    assert facts["redeclaration"]["to_expected_effect_pp"] == pytest.approx(4.6)
    assert facts["stage3_measurement"]["SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1"]["expected_effect_pp"] == pytest.approx(4.6)
    found = refusals(REPO, None)
    kinds = {line.split(":", 1)[0] for line in found}
    assert kinds == {"fit-run-not-permitted", "pending-pin"}
    fit_runs = {line.split()[1] for line in found if line.startswith("fit-run-not-permitted:")}
    assert fit_runs == {"SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-FIT-V1", "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-FIT-V1"}
    pending = [p for p in facts["pending_pins"] if not p.endswith("/phase-supply-v1.json")]
    assert pending, "the sample-preparation pins are still pending"
    for relpath in pending:
        assert any(relpath in line for line in found if line.startswith("pending-pin:")), relpath
    blockers = " ".join(facts["blockers_before_the_flip"])
    assert "OWNER GATE" in blockers and "countersignature" in blockers
    assert "ALLOWANCE" in blockers and "READ DRIVER" in blockers


def test_cells_pin_the_allowance_score_with_the_test_sibling_and_carry_no_smoke():
    allowance = json.loads((REPO / ALLOWANCE).read_text(encoding="utf-8"))
    sha = hashlib.sha256((REPO / ALLOWANCE).read_bytes()).hexdigest()
    for cell in CELLS:
        document = _experiment(REPO, cell)
        entry = document["cells"][0]
        assert document["owner_allowance"] == {"path": ALLOWANCE, "sha256": sha}
        assert entry["run_id"] in allowance["read_run_ids"]
        assert entry["readiness"]["state"] == "held"
        assert document["execution_plan"]["split_role"] == "final-report"
        assert document["population"]["split_identity_hash"] == allowance["split"]["split_identity_hash"]
        baseline = json.loads((REPO / "configs/baseline" / f"{entry['baseline_fragment']}.json").read_text(encoding="utf-8"))
        assert baseline["scorers"] == ["slurp-slu-official-test", "cost"]
    plan = json.loads((REPO / "configs/campaign/slurp-native-stage3-comp1b-testsample-v1.json").read_text(encoding="utf-8"))
    assert [c["cell"] for c in plan["cells"]] == list(CELLS)
    assert not list((REPO / "configs/experiment").glob("*testsample*smoke*"))


def _fake_tree(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    data = tmp_path / "data"
    for rel in [f"{PACKAGE}/registered-facts-v1.json", ALLOWANCE] + [f"configs/experiment/{c}.json" for c in CELLS]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / rel, root / rel)
    for cell in CELLS:
        base = _experiment(REPO, cell)["cells"][0]["baseline_fragment"]
        (root / "configs/baseline").mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / "configs/baseline" / f"{base}.json", root / "configs/baseline" / f"{base}.json")
    # clear every blocker: re-declare, a successor-shaped allowance naming the FIT ids, real pins, artifacts on disk
    facts_path = root / PACKAGE / "registered-facts-v1.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["redeclared_from_a2_read"] = True
    facts_path.write_text(json.dumps(facts), encoding="utf-8")
    allowance = json.loads((root / ALLOWANCE).read_text(encoding="utf-8"))
    fits = []
    for cell in CELLS:
        base = _experiment(root, cell)["cells"][0]["baseline_fragment"]
        fits.append(json.loads((root / "configs/baseline" / f"{base}.json").read_text(encoding="utf-8"))["native_contact_fit"]["run_id"])
    allowance["permitted_run_ids"] = allowance["permitted_run_ids"] + fits
    successor = "docs/receipts/owner/fake-allowance-v2.json"
    (root / successor).write_text(json.dumps(allowance), encoding="utf-8")
    successor_sha = hashlib.sha256((root / successor).read_bytes()).hexdigest()
    fake_sha = "a" * 64

    def unzero(node):
        if isinstance(node, dict):
            return {k: unzero(v) for k, v in node.items()}
        if isinstance(node, list):
            return [unzero(v) for v in node]
        return fake_sha if node == ZERO else node

    for cell in CELLS:
        exp_path = root / "configs/experiment" / f"{cell}.json"
        document = json.loads(exp_path.read_text(encoding="utf-8"))
        document["owner_allowance"] = {"path": successor, "sha256": successor_sha}
        own = f"prepared/{document['cells'][0]['run_id']}/phase-supply-v1.json"
        for requirement in document["cells"][0]["readiness"]["requirements"]:
            if requirement["relpath"] != own:
                requirement["sha256"] = fake_sha
                (data / requirement["relpath"]).parent.mkdir(parents=True, exist_ok=True)
                (data / requirement["relpath"]).write_text("fake", encoding="utf-8")
        exp_path.write_text(json.dumps(document), encoding="utf-8")
        base_path = root / "configs/baseline" / f"{document['cells'][0]['baseline_fragment']}.json"
        base_path.write_text(json.dumps(unzero(json.loads(base_path.read_text(encoding="utf-8")))), encoding="utf-8")
    return root, data


def test_fake_tree_with_every_blocker_cleared_passes(tmp_path):
    root, data = _fake_tree(tmp_path)
    assert refusals(root, data) == []


def test_fake_tree_refuses_each_blocker_alone(tmp_path):
    root, data = _fake_tree(tmp_path)
    facts_path = root / PACKAGE / "registered-facts-v1.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["redeclared_from_a2_read"] = False
    facts_path.write_text(json.dumps(facts), encoding="utf-8")
    assert [line.split(":", 1)[0] for line in refusals(root, data)] == ["expectation-not-redeclared"]
    facts["redeclared_from_a2_read"] = True
    facts_path.write_text(json.dumps(facts), encoding="utf-8")
    # a missing data-root artifact
    requirement = _experiment(root, CELLS[1])["cells"][0]["readiness"]["requirements"][0]
    (data / requirement["relpath"]).unlink()
    assert [line.split(":", 1)[0] for line in refusals(root, data)] == ["pending-artifact-missing"]
