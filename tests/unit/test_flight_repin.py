"""Synthetic-package tests for the registered-cell re-pin tool.

Every test builds its own throwaway git repo with fake model/dataset/baseline/
experiment fragments, a fake readiness package, and a fake exposure ledger --
never a real registered package under ``docs/readiness/`` or ``configs/``. The
model-free ``prepare-supply`` step is always a fake, injected via
``prepare_supply_fn``; ``run_check_fn`` is disabled (``None``) in every test
here, since ``core.flight.cli check`` requires a real carrier/model/lock that
has no place in a unit test -- that integration is exercised only by hand
against a real study checkout.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.flight.repin import (
    NO_ARTIFACT_REASONS,
    NO_CONSTRUCTION_SUPPLY_MESSAGE,
    NO_SUPPLIED_PHASE_MESSAGE,
    RepinError,
    apply_decision_and_readiness,
    repin_package,
    rewrite_ledger_notes,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

RUN_ID = "TEST-RUN-1"
CELL_ID = "cell-1"
EXPERIMENT_ID = "experiment-1"
CARRIER_LOCK_KEY = "testcarrier"
IDS = ["row-a", "row-b", "row-c"]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True, text=True)


def _init_git(repo: Path) -> None:
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial fixture")


def _write(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(document, str):
        path.write_text(document, encoding="utf-8", newline="\n")
    else:
        path.write_text(json.dumps(document, indent=2), encoding="utf-8", newline="\n")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Fake:
    """A fake ``prepare_supply_fn`` that raises for run ids in ``mismatched``
    when called on an EXISTING path (simulating a stale pin), and otherwise
    writes a fresh artifact and returns its receipt."""

    def __init__(self, mismatched: set[str] | None = None, outputs: dict[str, dict] | None = None):
        self.mismatched = mismatched or set()
        self.outputs = outputs or {}
        self.calls: list[dict] = []

    def __call__(self, *, run_id, output_path, **kwargs):
        self.calls.append({"run_id": run_id, "output_path": str(output_path), **kwargs})
        output_path = Path(output_path)
        if output_path.exists():
            if run_id in self.mismatched:
                raise RuntimeError(f"simulated identity mismatch for {run_id}")
            return {"path": str(output_path), "sha256": _sha(output_path), "cache": "warm"}
        document = {
            "schema": "saea-prepared-artifact-v1",
            "kind": "phase-supply",
            "inputs": {},
            "contact_class": "model-free",
            "output": self.outputs.get(run_id, {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}),
            "output_sha256": "0" * 64,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(document, indent=2).encode()
        output_path.write_bytes(raw)
        return {"path": str(output_path), "sha256": hashlib.sha256(raw).hexdigest(), "cache": "cold"}


def build_package(tmp_path: Path, *, old_artifact_output: dict | None = None, consumed: str = "no"):
    """Build a synthetic repo + data root carrying one registered cell,
    committed as the clean starting tree. Returns a dict of paths and the
    freshly composed old identity values."""

    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()

    _write(repo / "configs/model/model-1.json", {"model_lock_key": "test-model"})
    _write(repo / "configs/dataset/dataset-1.json", {"carrier_lock_key": CARRIER_LOCK_KEY})

    old_artifact_path = data / "prepared" / RUN_ID / "phase-supply-v1.json"
    old_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    old_document = {
        "schema": "saea-prepared-artifact-v1",
        "kind": "phase-supply",
        "inputs": {},
        "contact_class": "model-free",
        "output": old_artifact_output if old_artifact_output is not None else {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}},
        "output_sha256": "0" * 64,
    }
    old_artifact_path.write_bytes(json.dumps(old_document, indent=2).encode())
    old_artifact_sha = _sha(old_artifact_path)

    _write(
        repo / "configs/baseline/baseline-1.json",
        {
            "arm": "test-arm",
            "prepared_phase_supply": {
                "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                "sha256": old_artifact_sha,
            },
        },
    )

    declared_split = split_identity_hash(prefixed(CARRIER_LOCK_KEY, IDS))
    experiment_document = {
        "cells": [
            {
                "cell_id": CELL_ID,
                "model_fragment": "model-1",
                "dataset_fragment": "dataset-1",
                "baseline_fragment": "baseline-1",
                "run_id": RUN_ID,
                "attempt_id": "attempt-1",
                "readiness": {
                    "state": "held",
                    "reason": "not yet admitted",
                    "requirements": [
                        {
                            "kind": "preparation",
                            "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                            "sha256": old_artifact_sha,
                            "reason": "model-free prepared supply",
                        }
                    ],
                },
            }
        ],
        "population": {"split_identity_hash": declared_split},
        "populations": [{"ids": list(IDS)}],
    }
    _write(repo / "configs/experiment" / f"{EXPERIMENT_ID}.json", experiment_document)

    composed = compose(repo, "model-1", "dataset-1", "baseline-1", EXPERIMENT_ID)
    old_config_hash = composed.config_hash
    old_protocol_hash = protocol_hash(old_config_hash, "test-arm", declared_split)

    readiness_dir = repo / "docs/readiness/test-pkg"
    protocol_document_path = readiness_dir / "protocol-registered-v1.json"
    _write(
        protocol_document_path,
        {
            "schema": "test-protocol-v1",
            "cell": {
                "composed_config_hash": old_config_hash,
                "execution_plan_protocol_hash": old_protocol_hash,
                "prepared_phase_supply": {
                    "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                    "sha256": old_artifact_sha,
                },
            },
        },
    )
    old_doc_sha = _sha(protocol_document_path)

    plan_registered_path = readiness_dir / "generation-plan-registered-v1.json"
    _write(
        plan_registered_path,
        {
            "composed_config_hash": old_config_hash,
            "execution_plan": {"protocol_hash": old_protocol_hash, "run_id": RUN_ID},
            "protocol_document": {
                "relpath": "docs/readiness/test-pkg/protocol-registered-v1.json",
                "sha256": old_doc_sha,
            },
        },
    )
    old_plan_sha = _sha(plan_registered_path)

    _write(
        readiness_dir / "generation-plan-v1.json",
        {
            "composed_config_hash": old_config_hash,
            "prospective_execution_plan": {"protocol_hash": old_protocol_hash, "run_id": RUN_ID},
            "protocol_document": {
                "relpath": "docs/readiness/test-pkg/protocol-registered-v1.json",
                "sha256": old_doc_sha,
            },
        },
    )

    _write(
        readiness_dir / "README.md",
        f"composed config / protocol: `{old_config_hash}` / `{old_protocol_hash}`\n"
        f"protocol document sha256: `{old_doc_sha}`\n",
    )

    preregistration_path = repo / "docs/readiness/test-pkg-preregistration.md"
    _write(
        preregistration_path,
        f"treatment protocol `{old_protocol_hash}` composed config `{old_config_hash}`\n",
    )

    ledger_path = repo / "docs/exposure-ledger.md"
    notes = (
        f"Runtime protocol {old_protocol_hash}; protocol document {old_doc_sha}; "
        f"composed config {old_config_hash}; Plan SHA256 {old_plan_sha}."
    )
    ledger_text = (
        "# Exposure ledger\n\n"
        "| date | run/experiment id | consumed | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"| 2026-01-01 | {RUN_ID} | {consumed} | "
        f"docs/readiness/test-pkg/generation-plan-registered-v1.json | {notes} |\n"
        "| 2026-01-01 | UNRELATED-RUN | no | some/other/plan.json | unrelated row, untouched |\n"
    )
    _write(ledger_path, ledger_text)

    _init_git(repo)

    return {
        "repo": repo,
        "data": data,
        "readiness_dir": readiness_dir,
        "preregistration_path": preregistration_path,
        "ledger_path": ledger_path,
        "old_config_hash": old_config_hash,
        "old_protocol_hash": old_protocol_hash,
        "old_doc_sha": old_doc_sha,
        "old_plan_sha": old_plan_sha,
        "old_artifact_sha": old_artifact_sha,
        "plan_registered_path": plan_registered_path,
        "protocol_document_path": protocol_document_path,
    }


def run(pkg: dict, fake: Fake, **kwargs) -> dict:
    return repin_package(
        repo_root=pkg["repo"],
        data_root=pkg["data"],
        runtime_root=pkg["repo"],
        lock_path=pkg["repo"] / "lock.json",
        experiments=[(EXPERIMENT_ID, None)],
        readiness_dir=pkg["readiness_dir"],
        preregistration_path=pkg["preregistration_path"],
        prepare_supply_fn=fake,
        run_check_fn=None,
        **kwargs,
    )


def _all_text(pkg: dict) -> str:
    parts = [pkg["ledger_path"].read_text(encoding="utf-8")]
    for path in pkg["readiness_dir"].glob("*"):
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))
    parts.append(pkg["preregistration_path"].read_text(encoding="utf-8"))
    return "\n".join(parts)


# --------------------------------------------------------------------------
# Hash rewriting in dependency order, zero residue.
# --------------------------------------------------------------------------


def test_rewrites_every_dependent_hash_with_zero_residue(tmp_path):
    pkg = build_package(tmp_path)
    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})

    summary = run(pkg, fake)

    cell_report = summary["cells"][0]
    new_config = cell_report["new"]["config_hash"]
    new_protocol = cell_report["new"]["protocol_hash"]
    assert new_config != pkg["old_config_hash"]
    assert new_protocol != pkg["old_protocol_hash"]
    assert cell_report["artifact"]["rebuilt"] is True

    text = _all_text(pkg)
    assert pkg["old_config_hash"] not in text
    assert pkg["old_protocol_hash"] not in text
    assert pkg["old_doc_sha"] not in text
    assert pkg["old_plan_sha"] not in text
    assert new_config in text
    assert new_protocol in text

    # Round 2 propagated: every plan's protocol_document.sha256 now names the
    # rewritten protocol-registered-v1.json's OWN current sha256.
    new_doc_sha = _sha(pkg["protocol_document_path"])
    plan_registered = json.loads(pkg["plan_registered_path"].read_text(encoding="utf-8"))
    assert plan_registered["protocol_document"]["sha256"] == new_doc_sha

    # Round 3 propagated: the ledger's "Plan SHA256" now names that same
    # plan file's OWN current sha256 (computed after rounds 1+2 rewrote it).
    new_plan_sha = _sha(pkg["plan_registered_path"])
    ledger_text = pkg["ledger_path"].read_text(encoding="utf-8")
    assert f"Plan SHA256 {new_plan_sha}" in ledger_text

    # The unrelated ledger row is untouched.
    assert "unrelated row, untouched" in ledger_text


def test_no_rebuild_when_artifact_already_matches(tmp_path):
    pkg = build_package(tmp_path)
    fake = Fake(mismatched=set())  # the current pin already matches

    summary = run(pkg, fake)

    cell_report = summary["cells"][0]
    assert cell_report["artifact"]["rebuilt"] is False
    assert cell_report["old"]["config_hash"] == cell_report["new"]["config_hash"]
    assert cell_report["old"]["protocol_hash"] == cell_report["new"]["protocol_hash"]
    assert summary["files_rewritten"] == {}
    # Nothing under the package changed at all.
    assert pkg["old_config_hash"] in pkg["readiness_dir"].joinpath("README.md").read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Refusal on residue.
# --------------------------------------------------------------------------


def test_refuses_on_residue_left_outside_the_package(tmp_path):
    pkg = build_package(tmp_path)
    stray = pkg["repo"] / "docs" / "some-other-note.md"
    _write(stray, f"stray mention of {pkg['old_config_hash']} left behind\n")
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "add stray file with the old hash")

    fake = Fake(mismatched={RUN_ID})
    with pytest.raises(RepinError, match="residue"):
        run(pkg, fake)


# --------------------------------------------------------------------------
# Refusal on consumed rows.
# --------------------------------------------------------------------------


def test_refuses_when_the_exposure_row_is_already_consumed(tmp_path):
    pkg = build_package(tmp_path, consumed="yes")
    fake = Fake(mismatched={RUN_ID})

    baseline_before = (pkg["repo"] / "configs/baseline/baseline-1.json").read_text(encoding="utf-8")
    with pytest.raises(RepinError, match="consumed"):
        run(pkg, fake)
    # Refused before touching anything.
    assert (pkg["repo"] / "configs/baseline/baseline-1.json").read_text(encoding="utf-8") == baseline_before
    assert fake.calls == []


def test_refuses_when_the_exposure_row_is_missing(tmp_path):
    pkg = build_package(tmp_path)
    text = pkg["ledger_path"].read_text(encoding="utf-8").replace(RUN_ID, "SOME-OTHER-RUN")
    pkg["ledger_path"].write_text(text, encoding="utf-8")
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "rename the row away")

    fake = Fake(mismatched={RUN_ID})
    with pytest.raises(RepinError, match="no row"):
        run(pkg, fake)


# --------------------------------------------------------------------------
# Dirty-tree refusal.
# --------------------------------------------------------------------------


def test_refuses_on_unrelated_dirty_tree(tmp_path):
    pkg = build_package(tmp_path)
    unrelated = pkg["repo"] / "configs" / "model" / "model-1.json"
    unrelated.write_text(unrelated.read_text(encoding="utf-8") + " ", encoding="utf-8")

    fake = Fake(mismatched={RUN_ID})
    with pytest.raises(RepinError, match="tracked modifications"):
        run(pkg, fake)


# --------------------------------------------------------------------------
# Readiness flip and decision requirement insertion.
# --------------------------------------------------------------------------


def test_decision_requirement_insertion_and_ready_flip(tmp_path):
    pkg = build_package(tmp_path)
    decision_relpath = "coordination/test-pkg/decision-v1.json"
    decision_path = pkg["data"] / decision_relpath
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.write_text(json.dumps({"schema": "saea-campaign-decision-v1"}), encoding="utf-8")

    fake = Fake(mismatched=set())
    summary = run(pkg, fake, decision=(decision_relpath, "decision-1"), set_ready=True)
    assert summary["cells"]

    document = json.loads((pkg["repo"] / "configs/experiment" / f"{EXPERIMENT_ID}.json").read_text(encoding="utf-8"))
    readiness = document["cells"][0]["readiness"]
    assert readiness["state"] == "ready"
    decision_entries = [r for r in readiness["requirements"] if r.get("kind") == "decision"]
    assert len(decision_entries) == 1
    assert decision_entries[0]["expected_decision_id"] == "decision-1"
    assert decision_entries[0]["relpath"] == decision_relpath
    assert decision_entries[0]["sha256"] == _sha(decision_path)

    # A second call with the SAME decision does not insert a duplicate.
    run(pkg, fake, decision=(decision_relpath, "decision-1"), set_ready=True)
    document = json.loads((pkg["repo"] / "configs/experiment" / f"{EXPERIMENT_ID}.json").read_text(encoding="utf-8"))
    readiness = document["cells"][0]["readiness"]
    decision_entries = [r for r in readiness["requirements"] if r.get("kind") == "decision"]
    assert len(decision_entries) == 1


def test_apply_decision_and_readiness_helper_is_upsert(tmp_path):
    pkg = build_package(tmp_path)
    decision_relpath = "coordination/test-pkg/decision-v1.json"
    decision_path = pkg["data"] / decision_relpath
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.write_bytes(b"{}")

    first = apply_decision_and_readiness(
        repo_root=pkg["repo"], data_root=pkg["data"], experiment=EXPERIMENT_ID, cell_id=CELL_ID,
        decision=(decision_relpath, "decision-1"), set_ready=True,
    )
    assert first is True
    second = apply_decision_and_readiness(
        repo_root=pkg["repo"], data_root=pkg["data"], experiment=EXPERIMENT_ID, cell_id=CELL_ID,
        decision=(decision_relpath, "decision-1"), set_ready=True,
    )
    assert second is False


# --------------------------------------------------------------------------
# Output-equality refusal.
# --------------------------------------------------------------------------


def test_refuses_when_rebuilt_output_changes_without_the_override(tmp_path):
    pkg = build_package(tmp_path, old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}})
    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})

    baseline_before = (pkg["repo"] / "configs/baseline/baseline-1.json").read_text(encoding="utf-8")
    with pytest.raises(RepinError, match="different output"):
        run(pkg, fake)
    # The transient pin drop was rolled back on refusal.
    assert (pkg["repo"] / "configs/baseline/baseline-1.json").read_text(encoding="utf-8") == baseline_before


def test_allow_output_change_accepts_a_different_selection(tmp_path):
    pkg = build_package(tmp_path, old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}})
    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})

    summary = run(pkg, fake, allow_output_change=True)
    assert summary["cells"][0]["artifact"]["rebuilt"] is True
    row_counts = summary["cells"][0]["artifact"]["row_counts"]
    assert row_counts == {"old": {"facets": 0, "values": 2}, "new": {"facets": 0, "values": 1}}


# --------------------------------------------------------------------------
# Idempotence.
# --------------------------------------------------------------------------


def test_second_run_after_the_fix_lands_changes_nothing(tmp_path):
    pkg = build_package(tmp_path)
    fake = Fake(mismatched={RUN_ID})
    first = run(pkg, fake)
    assert first["cells"][0]["artifact"]["rebuilt"] is True

    snapshot = {
        path: path.read_bytes()
        for path in [
            pkg["repo"] / "configs/baseline/baseline-1.json",
            pkg["repo"] / "configs/experiment" / f"{EXPERIMENT_ID}.json",
            pkg["ledger_path"],
            *[p for p in pkg["readiness_dir"].glob("*") if p.is_file()],
            pkg["preregistration_path"],
        ]
    }

    # The artifact the tool just built now matches, so the fake never mismatches again.
    fake_again = Fake(mismatched=set())
    second = run(pkg, fake_again)
    assert second["cells"][0]["artifact"]["rebuilt"] is False
    assert second["files_rewritten"] == {}
    assert second["cells"][0]["old"]["config_hash"] == second["cells"][0]["new"]["config_hash"]

    for path, content in snapshot.items():
        assert path.read_bytes() == content, f"{path} changed on the idempotent second run"


# --------------------------------------------------------------------------
# Focused unit coverage for the ledger notes editor.
# --------------------------------------------------------------------------


def test_a_sealed_sibling_row_carrying_the_old_hash_is_neither_rewritten_nor_residue(tmp_path):
    """Item E26: a package DERIVED from a sealed one carries the parent's hashes
    until it is re-pinned. The parent's CLOSED row must keep them (it flew
    under them), the re-pin must not count them as residue, and only the
    package's own row and prose move."""
    pkg = build_package(tmp_path)
    ledger = pkg["ledger_path"]
    text = ledger.read_text(encoding="utf-8")
    parent_row = (
        f"| 2025-12-31 | PARENT-SEALED-RUN | yes | docs/readiness/parent-pkg/generation-plan-registered-v1.json | "
        f"Closed: sealed under runtime protocol {pkg['old_protocol_hash']}; composed config {pkg['old_config_hash']}; "
        f"protocol document {pkg['old_doc_sha']}. |\n"
    )
    ledger.write_text(text + parent_row, encoding="utf-8")
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "the sealed parent row carries the hashes the derived package inherited")

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    summary = run(pkg, fake)

    new_config = summary["cells"][0]["new"]["config_hash"]
    after = ledger.read_text(encoding="utf-8")
    parent_line = next(line for line in after.splitlines() if "PARENT-SEALED-RUN" in line)
    own_line = next(line for line in after.splitlines() if f"| {RUN_ID} |" in line)
    assert pkg["old_config_hash"] in parent_line and pkg["old_protocol_hash"] in parent_line
    assert pkg["old_doc_sha"] in parent_line
    assert new_config not in parent_line
    assert new_config in own_line and pkg["old_config_hash"] not in own_line
    # outside the ledger the old hashes are gone, exactly as before
    assert pkg["old_config_hash"] not in (pkg["repo"] / "docs/readiness/test-pkg-preregistration.md").read_text(encoding="utf-8")


def test_the_foreign_row_mask_flags_only_other_rows():
    from speech_aware_evidence_acquisition.core.flight.repin import _foreign_ledger_row_mask
    text = (
        "prose with a hash\n"
        "| date | run/experiment id | consumed | notes |\n"
        "| --- | --- | --- | --- |\n"
        "| d | RUN-A | yes | closed |\n"
        "| d | RUN-B | no | open |\n"
        "trailing prose\n"
    )
    assert _foreign_ledger_row_mask(text, {"RUN-B"}) == [False, False, False, True, False, False]


def test_rewrite_ledger_notes_touches_only_the_matched_rows_notes_cell():
    text = (
        "| date | run/experiment id | consumed | notes |\n"
        "| --- | --- | --- | --- |\n"
        "| d | RUN-A | no | old-value stays put in RUN-A's notes |\n"
        "| d | RUN-B | no | old-value here too |\n"
    )
    updated, changed = rewrite_ledger_notes(text, run_ids={"RUN-B"}, mapping={"old-value": "new-value"})
    assert changed == 1
    assert "RUN-A | no | old-value stays put" in updated
    assert "RUN-B | no | new-value here too" in updated


def test_a_missing_preparation_requirement_is_created_on_first_pin(tmp_path):
    """A package registered with an empty requirements list gets its
    'preparation' requirement created by the first successful pin."""
    from speech_aware_evidence_acquisition.core.flight import repin as module
    exp = tmp_path / "exp.json"
    exp.write_text(json.dumps({"cells": [{"cell_id": "c", "readiness": {"state": "held", "requirements": []}}]}), encoding="utf-8")
    pin = module.ArtifactPin(relpath="prepared/X/phase-supply-v1.json", sha256="a" * 64)
    module._set_preparation_requirement(exp, cell_id="c", run_id="X", previous_pin=None, pin=pin)
    doc = json.loads(exp.read_text(encoding="utf-8"))
    reqs = doc["cells"][0]["readiness"]["requirements"]
    assert [r["kind"] for r in reqs] == ["preparation"]
    assert reqs[0]["relpath"] == pin.relpath and reqs[0]["sha256"] == pin.sha256
    # a second pin updates in place, never duplicates
    module._set_preparation_requirement(
        exp, cell_id="c", run_id="X", previous_pin=pin, pin=module.ArtifactPin(relpath="prepared/X/phase-supply-v2.json", sha256="b" * 64)
    )
    doc = json.loads(exp.read_text(encoding="utf-8"))
    assert len(doc["cells"][0]["readiness"]["requirements"]) == 1
    assert doc["cells"][0]["readiness"]["requirements"][0]["sha256"] == "b" * 64


# --------------------------------------------------------------------------
# Item E38: a direct-only cell (no supplied first phase) flips without a pin.
# --------------------------------------------------------------------------


class FakeNoSupply(Fake):
    """A ``prepare_supply_fn`` that behaves like the real one on a program
    without a supplied first phase: it raises the preparation runtime's own
    message and writes nothing."""

    def __call__(self, *, run_id, output_path, **kwargs):
        self.calls.append({"run_id": run_id, "output_path": str(output_path), **kwargs})
        raise RuntimeError("PreparationError: program has no supplied first phase to prepare")


def _make_direct_only(pkg: dict) -> None:
    """Turn the synthetic package into a direct-only cell: no baseline pin, no
    'preparation' readiness requirement, no protocol-document pin, and every
    registered hash rewritten to the pin-free identity -- committed clean."""
    repo = pkg["repo"]
    baseline = repo / "configs/baseline/baseline-1.json"
    document = json.loads(baseline.read_text(encoding="utf-8"))
    document.pop("prepared_phase_supply")
    _write(baseline, document)
    experiment_path = repo / "configs/experiment" / f"{EXPERIMENT_ID}.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    readiness = experiment["cells"][0]["readiness"]
    readiness["requirements"] = [r for r in readiness["requirements"] if r.get("kind") != "preparation"]
    _write(experiment_path, experiment)
    protocol = json.loads(pkg["protocol_document_path"].read_text(encoding="utf-8"))
    protocol["cell"].pop("prepared_phase_supply", None)
    _write(pkg["protocol_document_path"], protocol)
    composed = compose(repo, "model-1", "dataset-1", "baseline-1", EXPERIMENT_ID)
    new_config = composed.config_hash
    new_protocol = protocol_hash(new_config, "test-arm", split_identity_hash(prefixed(CARRIER_LOCK_KEY, IDS)))
    targets = [p for p in pkg["readiness_dir"].glob("*") if p.is_file()] + [pkg["preregistration_path"], pkg["ledger_path"]]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        text = text.replace(pkg["old_config_hash"], new_config).replace(pkg["old_protocol_hash"], new_protocol)
        path.write_text(text, encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "a direct-only cell: no supplied phase, no pin")


def test_a_cell_without_a_supplied_phase_flips_on_its_decision_alone(tmp_path):
    pkg = build_package(tmp_path)
    _make_direct_only(pkg)
    baseline = pkg["repo"] / "configs/baseline/baseline-1.json"
    decision_path = pkg["data"] / "coordination/decision.json"
    _write(decision_path, {"decision_id": "decision-1", "eligible_run_ids": [RUN_ID]})
    fake = FakeNoSupply()
    summary = run(pkg, fake, decision=("coordination/decision.json", "decision-1"), set_ready=True)
    assert fake.calls and fake.calls[0]["run_id"] == RUN_ID
    report = summary["cells"][0]["artifact"]
    assert report["rebuilt"] is False and report["pin"] is None
    assert report["skipped"] == "program has no supplied first phase to prepare"
    after = json.loads(baseline.read_text(encoding="utf-8"))
    assert "prepared_phase_supply" not in after
    experiment = json.loads((pkg["repo"] / f"configs/experiment/{EXPERIMENT_ID}.json").read_text(encoding="utf-8"))
    readiness = experiment["cells"][0]["readiness"]
    assert readiness["state"] == "ready"
    kinds = [entry["kind"] for entry in readiness["requirements"]]
    assert "decision" in kinds and "preparation" not in kinds
    assert not list((pkg["data"] / "prepared" / RUN_ID).glob("phase-supply-v2.json"))


# --------------------------------------------------------------------------
# Item E42: a construction-visible TEXT arm has no prepared phase supply.
#
# ``run_phases`` dispatches such an arm through ``_dispatch_fixed_policy``, so
# it never builds a knowledge snapshot, a speech packet binding or a phase
# supply; the preparation runtime says so by name and the re-pin records the
# skip instead of trying to derive an artifact that does not exist. (Before
# this slice the re-pin of cell ADV-1 died on the SPEECH-arm refusal
# "phase programs require an explicit feature or raw speech arm".)
# --------------------------------------------------------------------------


def test_the_no_artifact_messages_mirror_the_preparation_runtime():
    """The two literals this module matches on are the runtime's own."""
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        NO_CONSTRUCTION_PHASE_SUPPLY_MESSAGE,
    )

    assert NO_CONSTRUCTION_SUPPLY_MESSAGE == NO_CONSTRUCTION_PHASE_SUPPLY_MESSAGE
    assert set(NO_ARTIFACT_REASONS) == {
        NO_SUPPLIED_PHASE_MESSAGE,
        NO_CONSTRUCTION_SUPPLY_MESSAGE,
    }


class FakeConstructionArm(Fake):
    """A ``prepare_supply_fn`` that behaves like the real one on a
    construction-visible text arm: it raises the preparation runtime's own
    message, on an existing path and on a fresh one alike, and writes
    nothing."""

    def __call__(self, *, run_id, output_path, **kwargs):
        self.calls.append({"run_id": run_id, "output_path": str(output_path), **kwargs})
        raise RuntimeError(f"PreparationError: {NO_CONSTRUCTION_SUPPLY_MESSAGE}")


def test_a_construction_visible_cell_flips_without_a_prepared_supply(tmp_path):
    pkg = build_package(tmp_path)
    _make_direct_only(pkg)
    baseline = pkg["repo"] / "configs/baseline/baseline-1.json"
    before = baseline.read_text(encoding="utf-8")
    decision_path = pkg["data"] / "coordination/decision.json"
    _write(decision_path, {"decision_id": "decision-1", "eligible_run_ids": [RUN_ID]})
    fake = FakeConstructionArm()

    summary = run(
        pkg,
        fake,
        decision=("coordination/decision.json", "decision-1"),
        set_ready=True,
    )

    report = summary["cells"][0]["artifact"]
    assert report["rebuilt"] is False and report["pin"] is None
    assert report["skipped"] == NO_CONSTRUCTION_SUPPLY_MESSAGE
    assert report["reason"] == NO_ARTIFACT_REASONS[NO_CONSTRUCTION_SUPPLY_MESSAGE]
    assert "construction-visible text arm" in report["reason"]
    # the baseline fragment is byte-identical: the transient drop was restored
    assert baseline.read_text(encoding="utf-8") == before
    assert "prepared_phase_supply" not in json.loads(before)
    experiment = json.loads(
        (pkg["repo"] / f"configs/experiment/{EXPERIMENT_ID}.json").read_text(encoding="utf-8")
    )
    readiness = experiment["cells"][0]["readiness"]
    assert readiness["state"] == "ready"
    kinds = [entry["kind"] for entry in readiness["requirements"]]
    assert "decision" in kinds and "preparation" not in kinds
    # nothing new was derived: the fixture's own v1 artifact is all there is
    assert not list((pkg["data"] / "prepared" / RUN_ID).glob("phase-supply-v2.json"))


def test_a_construction_visible_cell_that_pins_a_supply_is_refused(tmp_path):
    """Fail closed: nothing today gives a construction-visible arm a prepared
    supply, so a cell that both composes one and pins one is undefined."""
    pkg = build_package(tmp_path)
    baseline = pkg["repo"] / "configs/baseline/baseline-1.json"
    before = baseline.read_text(encoding="utf-8")
    assert "prepared_phase_supply" in json.loads(before)
    fake = FakeConstructionArm()

    with pytest.raises(RepinError) as error:
        run(pkg, fake)

    message = str(error.value)
    assert "has no derivable prepared phase supply" in message
    assert "phase-supply-v1.json" in message
    assert baseline.read_text(encoding="utf-8") == before
    assert not list((pkg["data"] / "prepared" / RUN_ID).glob("phase-supply-v2.json"))


def test_a_stale_pin_on_an_ordinary_cell_still_rebuilds(tmp_path):
    """The E42 refusal is scoped to its own message: an ordinary stale pin
    takes the unchanged rebuild path."""
    pkg = build_package(tmp_path)
    fake = Fake(mismatched={RUN_ID})

    summary = run(pkg, fake)

    report = summary["cells"][0]["artifact"]
    assert report["rebuilt"] is True
    assert report["new_pin"]["relpath"].endswith("phase-supply-v2.json")


# --------------------------------------------------------------------------
# 2026-09-26: a cell's OTHER 'preparation' requirements survive the flip.
#
# The registered AGREE cells carry two 'preparation' requirements -- the
# pre-computed agreement table and their own supply. The pre-fix tool rewrote
# every ``kind == "preparation"`` entry to the fresh supply pin; the fix
# matches the own-supply entry by artifact identity and leaves the rest alone.
# --------------------------------------------------------------------------


FOREIGN_REQUIREMENT = {
    "kind": "preparation",
    "relpath": "prepared/AGREEMENT-TABLE-V1/agreement.jsonl",
    "sha256": "c" * 64,
    "reason": "a pre-computed table this cell ranks with; built elsewhere, never this cell's supply",
}


def _add_foreign_preparation_requirement(pkg: dict) -> None:
    """Give the synthetic cell a second 'preparation' requirement that is NOT
    its own supply (the AGREE shape: the foreign table first, the own supply
    second), rewrite the registered hashes to the new composed identity, and
    commit clean."""
    repo = pkg["repo"]
    experiment_path = repo / "configs/experiment" / f"{EXPERIMENT_ID}.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    experiment["cells"][0]["readiness"]["requirements"].insert(0, dict(FOREIGN_REQUIREMENT))
    _write(experiment_path, experiment)
    composed = compose(repo, "model-1", "dataset-1", "baseline-1", EXPERIMENT_ID)
    new_config = composed.config_hash
    new_protocol = protocol_hash(new_config, "test-arm", split_identity_hash(prefixed(CARRIER_LOCK_KEY, IDS)))
    targets = [p for p in pkg["readiness_dir"].glob("*") if p.is_file()] + [pkg["preregistration_path"], pkg["ledger_path"]]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        text = text.replace(pkg["old_config_hash"], new_config).replace(pkg["old_protocol_hash"], new_protocol)
        path.write_text(text, encoding="utf-8", newline="\n")
    pkg["old_config_hash"], pkg["old_protocol_hash"] = new_config, new_protocol
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "a second, foreign preparation requirement")


def test_a_foreign_preparation_requirement_survives_the_flip(tmp_path):
    """The AGREE shape end to end: with a stale own pin the re-pin mints a
    fresh supply, rewrites ONLY the own-supply requirement, and leaves the
    foreign one byte-for-byte where it was."""
    pkg = build_package(tmp_path)
    _add_foreign_preparation_requirement(pkg)
    fake = Fake(mismatched={RUN_ID})

    summary = run(pkg, fake)

    report = summary["cells"][0]["artifact"]
    assert report["rebuilt"] is True
    assert report["readiness_requirement"] == {"updated": 1, "appended": 0, "kept": 1}
    experiment = json.loads((pkg["repo"] / f"configs/experiment/{EXPERIMENT_ID}.json").read_text(encoding="utf-8"))
    requirements = experiment["cells"][0]["readiness"]["requirements"]
    assert len(requirements) == 2
    assert json.dumps(requirements[0]) == json.dumps(FOREIGN_REQUIREMENT)
    assert requirements[1]["relpath"] == report["new_pin"]["relpath"] == f"prepared/{RUN_ID}/phase-supply-v2.json"
    assert requirements[1]["sha256"] == report["new_pin"]["sha256"]
    assert requirements[1]["reason"] == "model-free prepared supply"
    assert f"prepared/{RUN_ID}/phase-supply-v1.json" not in _all_text(pkg)
