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
    _is_resume_parent_readiness_record,
    _is_superseded_donor_readiness_record,
    _resume_parent_package_dirs,
    _superseded_donor_package_dirs,
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


def build_package(
    tmp_path: Path,
    *,
    old_artifact_output: dict | None = None,
    consumed: str = "no",
    baseline_extra_fn=None,
    own_resume_from=None,
):
    """Build a synthetic repo + data root carrying one registered cell,
    committed as the clean starting tree. Returns a dict of paths and the
    freshly composed old identity values.

    ``baseline_extra_fn``, when given, is called with the freshly computed
    ``old_artifact_sha`` and its return value (a dict) is merged into the
    baseline fragment BEFORE ``compose()`` runs -- so every downstream
    document (protocol, plan, README, preregistration, ledger) is written
    against the resulting (extra-field-inclusive) config/protocol hash, the
    same way :func:`compute_cell_identity` will see it. This lets a test
    plant a stale value inside the cell's OWN baseline fragment, in a field
    this tool never rewrites, without breaking the fixture's internal
    consistency.

    ``own_resume_from``, when given, is written as the cell's own
    ``resume_from`` field BEFORE ``compose()`` runs -- a resume/seal-only
    cell declaring the aborted attempt(s) it resumes (item E4-1,
    2026-09-29)."""

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

    baseline_document = {
        "arm": "test-arm",
        "prepared_phase_supply": {
            "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
            "sha256": old_artifact_sha,
        },
    }
    if baseline_extra_fn is not None:
        baseline_document.update(baseline_extra_fn(old_artifact_sha))
    _write(repo / "configs/baseline/baseline-1.json", baseline_document)

    declared_split = split_identity_hash(prefixed(CARRIER_LOCK_KEY, IDS))
    cell_document = {
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
    if own_resume_from is not None:
        cell_document["resume_from"] = own_resume_from
    experiment_document = {
        "cells": [cell_document],
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


def test_a_foreign_sealed_readiness_package_is_neither_rewritten_nor_residue(tmp_path):
    """Item: the 2026-09-28 COMP-1 -REC recovery cell, derived from the
    sealed COMP-1 arm, inherited that parent's own hash-pinned pins and
    quoted the parent's protocol document verbatim under its own
    ``parent_protocol`` field. The parent's OWN package directory -- a real
    ``docs/readiness/<other>/`` directory this tool never touches, not just a
    ledger row -- keeps those hashes forever; the derived cell's own re-pin
    must succeed and must never rewrite the parent's bytes."""
    pkg = build_package(tmp_path)

    parent_dir = pkg["repo"] / "docs/readiness/parent-pkg"
    _write(
        parent_dir / "protocol-registered-v1.json",
        {
            "schema": "test-protocol-v1",
            "cell": {"run_id": "PARENT-RUN"},
            "composed_config_hash": pkg["old_config_hash"],
            "execution_plan_protocol_hash": pkg["old_protocol_hash"],
        },
    )
    _write(
        parent_dir / "README.md",
        f"sealed parent: composed config `{pkg['old_config_hash']}`, protocol `{pkg['old_protocol_hash']}`\n",
    )
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "add a sealed parent readiness package carrying the inherited hashes")

    parent_snapshot = {path: path.read_bytes() for path in parent_dir.iterdir() if path.is_file()}

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    summary = run(pkg, fake)  # must not raise RepinError

    assert summary["cells"][0]["new"]["config_hash"] != pkg["old_config_hash"]
    for path, content in parent_snapshot.items():
        assert path.read_bytes() == content, f"{path} was rewritten by a re-pin that does not own it"

    text = _all_text(pkg)
    assert pkg["old_config_hash"] not in text
    assert pkg["old_protocol_hash"] not in text


def test_a_stale_hash_left_in_the_cells_own_package_is_still_residue(tmp_path):
    """The foreign-package exemption must stop exactly at the cell's own
    ``readiness_dir``: a file sitting INSIDE it that this tool does not
    itself rewrite (only ``*.json`` and ``README.md`` are rewritten) is still
    the cell's own, and a stale hash left there is still residue -- even with
    an unrelated, disjoint-run-id sealed package present elsewhere."""
    pkg = build_package(tmp_path)

    parent_dir = pkg["repo"] / "docs/readiness/parent-pkg"
    _write(parent_dir / "protocol-registered-v1.json", {"cell": {"run_id": "PARENT-RUN"}})
    _write(pkg["readiness_dir"] / "stray-notes.txt", f"leftover mention of {pkg['old_config_hash']}\n")
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "add a stray untouched file inside the cell's own package")

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    with pytest.raises(RepinError, match="residue"):
        run(pkg, fake)


# --------------------------------------------------------------------------
# Same-run-id resume: sealed records of an earlier attempt, and hash-pinned
# tables, within a package that legitimately names the current run id (the
# 2026-09-28 COMP-1 RESUME ruling).
# --------------------------------------------------------------------------


def test_a_same_run_id_earlier_attempt_plan_document_is_not_residue(tmp_path):
    """A RESUME shares its parent arm's run id, so the parent's own sealed
    ``fit-plan-registered-v1.json`` (a different, ABORTED attempt) mentions
    that run id and is no longer exempted by ``_is_foreign_readiness_package``
    alone. It still carries the superseded supply pin the resume rebuilds --
    that is history, not residue, because the document names an attempt
    other than ``attempt-1`` (the one this fixture re-pins)."""
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
    )

    parent_dir = pkg["repo"] / "docs/readiness/parent-pkg"
    _write(
        parent_dir / "fit-plan-registered-v1.json",
        {
            "execution_plan": {"attempt_id": "attempt-1-aborted-fit", "run_id": RUN_ID},
            "prepared_phase_supply": {
                "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                "sha256": pkg["old_artifact_sha"],
            },
            "purpose": f"{RUN_ID}: the aborted attempt's own fit plan",
        },
    )
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "add the aborted attempt's sealed fit plan, naming the shared run id")

    parent_snapshot = (parent_dir / "fit-plan-registered-v1.json").read_bytes()

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    run(pkg, fake, allow_output_change=True)  # must not raise RepinError

    assert (parent_dir / "fit-plan-registered-v1.json").read_bytes() == parent_snapshot
    assert pkg["old_artifact_sha"] not in _all_text(pkg)


def test_a_hash_pinned_table_naming_the_shared_run_id_is_not_residue(tmp_path):
    """A file whose OWN bytes are pinned by sha256 from a sibling document in
    the same package (the admission draft's ``attribution_classes`` block,
    mirroring ``root-admission-draft-v1.json``) is a frozen derivation
    snapshot: rewriting it would break that external pin. It is not residue
    even though it names the shared run id and internally still carries the
    superseded supply pin."""
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
    )

    parent_dir = pkg["repo"] / "docs/readiness/parent-pkg"
    attribution_path = parent_dir / "attribution-classes-v1.json"
    _write(
        attribution_path,
        {
            "derivation_id": "TEST-ATTRIBUTION-CLASSES-V1",
            "inputs": {
                "arm_supply": {
                    "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                    "sha256": pkg["old_artifact_sha"],
                }
            },
        },
    )
    attribution_sha = _sha(attribution_path)
    _write(
        parent_dir / "root-admission-draft-v1.json",
        {
            "attribution_classes": {
                "path": "docs/readiness/parent-pkg/attribution-classes-v1.json",
                "sha256": attribution_sha,
            }
        },
    )
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "add a sha256-pinned attribution-classes table naming the shared run id")

    parent_snapshot = attribution_path.read_bytes()

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    run(pkg, fake, allow_output_change=True)  # must not raise RepinError

    assert attribution_path.read_bytes() == parent_snapshot
    assert pkg["old_artifact_sha"] not in _all_text(pkg)


def test_a_current_attempt_plan_document_with_a_stale_pin_is_still_residue(tmp_path):
    """Neither exemption reaches the RE-PINNED attempt's own plan documents:
    a foreign-directory file naming the SAME attempt id as the cell being
    re-pinned is not a 'sealed record of an earlier attempt', so a stale pin
    left inside it is still residue."""
    pkg = build_package(tmp_path)

    parent_dir = pkg["repo"] / "docs/readiness/parent-pkg"
    _write(
        parent_dir / "generation-plan-registered-v1.json",
        {
            "execution_plan": {"attempt_id": "attempt-1", "run_id": RUN_ID},
            "prepared_phase_supply": {
                "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                "sha256": pkg["old_artifact_sha"],
            },
            "purpose": f"{RUN_ID}: same attempt id as the cell being re-pinned",
        },
    )
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "add a foreign-directory plan document naming the CURRENT attempt")

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    with pytest.raises(RepinError, match="residue"):
        run(pkg, fake)


def test_a_foreign_package_naming_no_current_run_id_is_still_exempt_first(tmp_path):
    """1fd88e1e's original rule is tried FIRST and still exempts a genuinely
    foreign package (one that names none of the current run ids) without
    ever reaching the narrower sealed-record/hash-pin fallback -- a file that
    is neither a plan document nor pinned by any sibling is still exempt as
    long as it stays silent about the run id being re-pinned."""
    pkg = build_package(tmp_path)

    parent_dir = pkg["repo"] / "docs/readiness/other-pkg"
    _write(
        parent_dir / "notes.json",
        {"unrelated_field": "nothing to see here", "coincidental_value": pkg["old_artifact_sha"]},
    )
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "add an unrelated sealed note that happens to echo the old artifact sha")

    parent_snapshot = (parent_dir / "notes.json").read_bytes()

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    run(pkg, fake)  # must not raise RepinError

    assert (parent_dir / "notes.json").read_bytes() == parent_snapshot


def test_the_cells_own_baseline_fragment_with_a_stale_value_is_still_residue(tmp_path):
    """Rule (c): configs of the CURRENT run id are never exempt. A stray
    field inside the cell's own baseline fragment -- a file this tool never
    rewrites wholesale, only its ``prepared_phase_supply`` key -- that still
    carries the superseded artifact sha256 after the rebuild is still
    residue, even though it lives beside the very field the tool DID
    correctly update."""
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
        baseline_extra_fn=lambda sha: {"frozen_note": sha},
    )

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    with pytest.raises(RepinError, match="residue"):
        run(pkg, fake, allow_output_change=True)


# --------------------------------------------------------------------------
# resume_from parent config exemption (item E4-1, 2026-09-29): a
# resume/seal-only cell's FIRST re-pin inherits its parent's supply pin byte
# for byte, so the exact old value being superseded is also the parent's own,
# permanently unchanged pin -- quoted in the PARENT's own configs/experiment
# and configs/baseline fragments, which share the resume's run id (a RESUME
# never gets a fresh run id) but name the parent's own attempt id, not the
# resume's. ``_is_foreign_config`` alone cannot exempt it (the run id is not
# disjoint); this is the configs-side twin of the existing docs-side
# sealed-package-record rule, scoped to exactly the cell(s) the current
# re-pin's own ``resume_from`` names.
# --------------------------------------------------------------------------


def test_a_resume_parents_own_config_quoting_the_old_pin_converges(tmp_path):
    """The parent's own ``configs/experiment`` and ``configs/baseline``
    fragments -- found by the resume cell's own ``resume_from.attempt_id``,
    never by run id alone -- keep the superseded phase-supply-v1 pin forever
    (E26: never rewrite a parent's own record); the resume cell's own re-pin
    must still succeed and must never touch the parent's bytes."""
    resume_trace_sha256 = hashlib.sha256(b"attempt-0-trace").hexdigest()
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
        own_resume_from={"attempt_id": "attempt-0", "trace_sha256": resume_trace_sha256},
    )

    parent_baseline_path = pkg["repo"] / "configs/baseline/parent-baseline-1.json"
    _write(
        parent_baseline_path,
        {
            "arm": "parent-arm",
            "prepared_phase_supply": {
                "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                "sha256": pkg["old_artifact_sha"],
            },
        },
    )
    parent_experiment_path = pkg["repo"] / "configs/experiment/parent-experiment.json"
    _write(
        parent_experiment_path,
        {
            "cells": [
                {
                    "cell_id": "parent-cell",
                    "model_fragment": "model-1",
                    "dataset_fragment": "dataset-1",
                    "baseline_fragment": "parent-baseline-1",
                    "run_id": RUN_ID,
                    "attempt_id": "attempt-0",
                    "readiness": {
                        "state": "ready",
                        "reason": "",
                        "requirements": [
                            {
                                "kind": "preparation",
                                "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                                "sha256": pkg["old_artifact_sha"],
                                "reason": "the parent arm's own model-free prepared supply",
                            }
                        ],
                    },
                }
            ],
        },
    )
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "add the parent arm's own experiment and baseline fragments")

    parent_baseline_snapshot = parent_baseline_path.read_bytes()
    parent_experiment_snapshot = parent_experiment_path.read_bytes()

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    summary = run(pkg, fake, allow_output_change=True)  # must not raise RepinError

    assert summary["cells"][0]["artifact"]["rebuilt"] is True
    assert parent_baseline_path.read_bytes() == parent_baseline_snapshot
    assert parent_experiment_path.read_bytes() == parent_experiment_snapshot
    # The resume cell's OWN fragments, by contrast, are rewritten in place.
    own_baseline_text = (pkg["repo"] / "configs/baseline/baseline-1.json").read_text(encoding="utf-8")
    own_experiment_text = (pkg["repo"] / "configs/experiment" / f"{EXPERIMENT_ID}.json").read_text(encoding="utf-8")
    assert pkg["old_artifact_sha"] not in own_baseline_text
    assert pkg["old_artifact_sha"] not in own_experiment_text
    assert pkg["old_artifact_sha"] not in _all_text(pkg)


def test_an_unrelated_config_outside_the_resume_chain_still_refuses(tmp_path):
    """The resume-parent-config exemption names only the specific cell(s) the
    current re-pin's own ``resume_from`` chain points at (found by attempt
    id). A DIFFERENT cell that happens to share the same run id and quote the
    same superseded pin, but whose own attempt id is not named by
    ``resume_from``, is not the parent -- it is a foreign cell (or a defect),
    and the scan must still refuse on it."""
    resume_trace_sha256 = hashlib.sha256(b"attempt-0-trace").hexdigest()
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
        own_resume_from={"attempt_id": "attempt-0", "trace_sha256": resume_trace_sha256},
    )

    _write(
        pkg["repo"] / "configs/baseline/unrelated-baseline-1.json",
        {
            "arm": "unrelated-arm",
            "prepared_phase_supply": {
                "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                "sha256": pkg["old_artifact_sha"],
            },
        },
    )
    _write(
        pkg["repo"] / "configs/experiment/unrelated-experiment.json",
        {
            "cells": [
                {
                    "cell_id": "unrelated-cell",
                    "model_fragment": "model-1",
                    "dataset_fragment": "dataset-1",
                    "baseline_fragment": "unrelated-baseline-1",
                    "run_id": RUN_ID,
                    "attempt_id": "attempt-unrelated",
                    "readiness": {"state": "ready", "reason": ""},
                }
            ],
        },
    )
    _git(pkg["repo"], "add", "-A")
    _git(
        pkg["repo"], "commit", "-q", "-m",
        "add an unrelated cell sharing the run id and the old pin, outside the resume_from chain",
    )

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    with pytest.raises(RepinError, match="residue"):
        run(pkg, fake, allow_output_change=True)


# --------------------------------------------------------------------------
# resume_from parent READINESS PACKAGE exemption (item E4-2, 2026-09-29): the
# 2026-09-29 P-SV-1 seal-only flip's second instance of the same defect. A
# resume/seal-only cell shares its parent's run id, so one exposure-ledger row
# serves both; that row's own 'artifacts' column is set once, at the run id's
# FIRST registration, and is never rewritten to point at a new package
# afterward -- so it still names the PARENT's own docs/readiness/<package>/
# directory even once the resume's own re-pin targets a brand new package.
# The parent's own README and registered-facts legitimately quote the
# parent's own frozen pins forever (rule E26); neither
# ``_is_foreign_readiness_package`` (the package still names the shared run
# id) nor ``_is_sealed_package_record`` (a non-JSON README, and a JSON file
# naming no attempt and pinned by no sibling) reaches them.
# --------------------------------------------------------------------------


def _point_ledger_artifacts_at_parent_pkg(pkg: dict) -> None:
    """Rewrite the fixture's one ledger row for ``RUN_ID`` so its 'artifacts'
    column names ``docs/readiness/parent-pkg/...`` instead of the resume
    cell's own ``test-pkg`` -- the real-world shape once a resume/seal-only
    flip retargets ``readiness_dir`` to a brand new package while the shared
    run id's ledger row keeps pointing at wherever it was first registered.
    Also strips the fixture's 'Plan SHA256 ...' note so round 3 of
    :func:`rewrite_dependent_hashes` (an orthogonal mechanism: it resolves the
    NEW plan file's own sha256 from that same 'artifacts' column) finds
    nothing to compare against a plan file this test never populates to
    match; that round is not what this test exercises.
    """

    text = pkg["ledger_path"].read_text(encoding="utf-8")
    text = text.replace(f"Plan SHA256 {pkg['old_plan_sha']}.", "no plan hash recorded in this fixture.")
    text = text.replace(
        "docs/readiness/test-pkg/generation-plan-registered-v1.json",
        "docs/readiness/parent-pkg/generation-plan-registered-v1.json",
    )
    pkg["ledger_path"].write_text(text, encoding="utf-8", newline="\n")


def test_a_resume_parents_own_readiness_package_quoting_the_old_pin_converges(tmp_path):
    """The parent's own ``docs/readiness/parent-pkg/`` -- resolved from the
    shared ledger row's 'artifacts' column, never a hand-rolled cell-id-to-
    directory guess -- keeps the superseded phase-supply pin forever in its
    README and ``registered-facts-v1.json`` (standing in for the real
    defect's branch-seed pin: the exemption treats every superseded old
    value the same way, whatever kind of pin it is). The resume cell's own
    re-pin must still succeed and must never touch the parent's bytes."""
    resume_trace_sha256 = hashlib.sha256(b"attempt-0-trace").hexdigest()
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
        own_resume_from={"attempt_id": "attempt-0", "trace_sha256": resume_trace_sha256},
    )
    _point_ledger_artifacts_at_parent_pkg(pkg)

    parent_dir = pkg["repo"] / "docs/readiness/parent-pkg"
    _write(
        parent_dir / "README.md",
        f"{RUN_ID}: the parent's own pinned prepared supply "
        f"(`prepared/{RUN_ID}/phase-supply-v1.json`, sha256 `{pkg['old_artifact_sha']}`).\n",
    )
    _write(
        parent_dir / "registered-facts-v1.json",
        {
            "run_id": RUN_ID,
            "prepared_phase_supply": {
                "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                "sha256": pkg["old_artifact_sha"],
            },
        },
    )
    _write(
        parent_dir / "generation-plan-registered-v1.json",
        {"purpose": f"{RUN_ID}: the parent's own plan, never rewritten by the resume's re-pin"},
    )
    _git(pkg["repo"], "add", "-A")
    _git(
        pkg["repo"], "commit", "-q", "-m",
        "point the ledger row at the parent package and add the parent's own sealed records",
    )

    parent_snapshot = {path: path.read_bytes() for path in parent_dir.iterdir() if path.is_file()}

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    summary = run(pkg, fake, allow_output_change=True)  # must not raise RepinError

    assert summary["cells"][0]["artifact"]["rebuilt"] is True
    for path, content in parent_snapshot.items():
        assert path.read_bytes() == content, f"{path} was rewritten by a re-pin that does not own it"
    assert pkg["old_artifact_sha"] not in _all_text(pkg)


def test_a_foreign_readiness_package_naming_the_run_id_still_refuses_alongside_a_resume(tmp_path):
    """The parent-package exemption names only the ONE package the shared
    ledger row's 'artifacts' column resolves to. A DIFFERENT package that
    also names the shared run id (so ``_is_foreign_readiness_package`` does
    not exempt it either) and quotes the same superseded pin is not the
    resolved parent -- it is a foreign package (or a defect) -- and the scan
    must still refuse on it, even though a resume_from chain is active and
    its actual parent package converges cleanly."""
    resume_trace_sha256 = hashlib.sha256(b"attempt-0-trace").hexdigest()
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
        own_resume_from={"attempt_id": "attempt-0", "trace_sha256": resume_trace_sha256},
    )
    _point_ledger_artifacts_at_parent_pkg(pkg)

    parent_dir = pkg["repo"] / "docs/readiness/parent-pkg"
    _write(parent_dir / "generation-plan-registered-v1.json", {"purpose": f"{RUN_ID}: the resolved parent's plan"})

    other_dir = pkg["repo"] / "docs/readiness/genuinely-foreign-pkg"
    _write(
        other_dir / "README.md",
        f"{RUN_ID}: an unrelated package that happens to quote the same superseded pin "
        f"sha256 `{pkg['old_artifact_sha']}`.\n",
    )
    _git(pkg["repo"], "add", "-A")
    _git(
        pkg["repo"], "commit", "-q", "-m",
        "add the resolved parent package plus a genuinely foreign one quoting the same pin",
    )

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    with pytest.raises(RepinError, match="residue"):
        run(pkg, fake, allow_output_change=True)


def test_a_resume_cells_own_package_with_stale_residue_still_refuses(tmp_path):
    """The parent-package exemption never widens to the resume cell's OWN
    package: a stray file left inside its own ``readiness_dir`` (one this
    tool does not itself rewrite) that still carries the superseded pin is
    still residue, even with the parent-package exemption active for a
    genuine resume_from chain."""
    resume_trace_sha256 = hashlib.sha256(b"attempt-0-trace").hexdigest()
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
        own_resume_from={"attempt_id": "attempt-0", "trace_sha256": resume_trace_sha256},
    )
    _point_ledger_artifacts_at_parent_pkg(pkg)

    parent_dir = pkg["repo"] / "docs/readiness/parent-pkg"
    _write(parent_dir / "generation-plan-registered-v1.json", {"purpose": f"{RUN_ID}: the resolved parent's plan"})
    _write(pkg["readiness_dir"] / "stray-notes.txt", f"leftover mention of {pkg['old_artifact_sha']}\n")
    _git(pkg["repo"], "add", "-A")
    _git(
        pkg["repo"], "commit", "-q", "-m",
        "add the resolved parent package plus a stray leftover file inside the resume's own package",
    )

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    with pytest.raises(RepinError, match="residue"):
        run(pkg, fake, allow_output_change=True)


def test_resume_parent_package_dirs_reads_the_ledger_artifacts_column(tmp_path):
    """:func:`_resume_parent_package_dirs` resolves a run id's package the
    same way the registration gate's own fallback does: the
    ``docs/readiness/<package>/`` directory named in that run id's ledger row
    'artifacts' column (``PACKAGE_REF`` in ``flight_registration_check.py``,
    reused verbatim as ``_READINESS_PACKAGE_REF``). A run id with no such
    entry, an unknown run id, empty ``run_ids``, or a missing ledger file all
    resolve to nothing rather than raising -- this is a best-effort residue
    exemption, not a hard requirement."""
    ledger_path = tmp_path / "exposure-ledger.md"
    ledger_path.write_text(
        "# Exposure ledger\n\n"
        "| date | run/experiment id | consumed | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 2026-01-01 | RUN-A | no | docs/readiness/pkg-a/plan-registered-v1.json | notes |\n"
        "| 2026-01-01 | RUN-B | no | some/other/plan.json | notes |\n",
        encoding="utf-8",
    )

    assert _resume_parent_package_dirs(tmp_path, ledger_path, {"RUN-A"}) == {
        (tmp_path / "docs" / "readiness" / "pkg-a").resolve()
    }
    assert _resume_parent_package_dirs(tmp_path, ledger_path, {"RUN-B"}) == set()
    assert _resume_parent_package_dirs(tmp_path, ledger_path, {"RUN-C"}) == set()
    assert _resume_parent_package_dirs(tmp_path, ledger_path, set()) == set()
    assert _resume_parent_package_dirs(tmp_path, tmp_path / "missing.md", {"RUN-A"}) == set()


def test_is_resume_parent_readiness_record_matches_package_and_preregistration_sibling(tmp_path):
    """:func:`_is_resume_parent_readiness_record` exempts every file inside a
    named parent package directory and its sibling preregistration note
    (``docs/readiness/<package>-preregistration*.md``), but nothing else --
    not an unrelated sibling file, not another package's own directory, and
    nothing at all once ``resume_parent_package_dirs`` is empty."""
    readiness_root = (tmp_path / "docs" / "readiness").resolve()
    package_dir = (readiness_root / "parent-pkg").resolve()

    inside_file = readiness_root / "parent-pkg" / "README.md"
    inside_file.parent.mkdir(parents=True)
    inside_file.write_text("x", encoding="utf-8")
    sibling_preregistration = readiness_root / "parent-pkg-preregistration.md"
    sibling_preregistration.write_text("x", encoding="utf-8")
    unrelated_sibling = readiness_root / "parent-pkg-other-notes.md"
    unrelated_sibling.write_text("x", encoding="utf-8")
    other_dir_file = readiness_root / "other-pkg" / "README.md"
    other_dir_file.parent.mkdir(parents=True)
    other_dir_file.write_text("x", encoding="utf-8")

    dirs = {package_dir}
    assert _is_resume_parent_readiness_record(
        inside_file, readiness_root=readiness_root, resume_parent_package_dirs=dirs
    ) is True
    assert _is_resume_parent_readiness_record(
        sibling_preregistration, readiness_root=readiness_root, resume_parent_package_dirs=dirs
    ) is True
    assert _is_resume_parent_readiness_record(
        unrelated_sibling, readiness_root=readiness_root, resume_parent_package_dirs=dirs
    ) is False
    assert _is_resume_parent_readiness_record(
        other_dir_file, readiness_root=readiness_root, resume_parent_package_dirs=dirs
    ) is False
    assert _is_resume_parent_readiness_record(
        inside_file, readiness_root=readiness_root, resume_parent_package_dirs=set()
    ) is False


# --------------------------------------------------------------------------
# Superseded-donor-package exemption (2026-09-29, cell A2/COMP-1b on
# DEV-2000-ADDED, owner decision 198): a cell CARRIED FORWARD into the
# current package from a now-superseded donor package -- the mirror image of
# a resume (a resume BUILDS on a still-live sealed parent; here the donor
# GIVES UP a cell it once owned). The donor's own row(s) (a DIFFERENT run id
# from the carried-over cell's own -- the donor's own arm/FIT/smoke rows, not
# the carried-over cell's row, which is simply re-pointed) carry the exact
# marker "SUPERSEDED <date> by cell <id> (docs/readiness/<this package>,
# ...)"; the donor package's own registered documents legitimately still
# quote the carried-over cell's pre-carry-over pin, frozen forever (E26).
# --------------------------------------------------------------------------


def _add_donor_ledger_row(
    pkg: dict, *, donor_run_id: str, donor_package: str, marker_package: str | None
) -> None:
    """Append a second ledger row for ``donor_run_id``, pointing its
    'artifacts' column at ``donor_package``. When ``marker_package`` is
    given, the row's notes carry the exact SUPERSEDED marker naming it as
    the superseding package; when it is ``None``, the notes describe
    supersession only in prose, without the exact marker."""

    if marker_package is not None:
        notes = (
            "this cell never flew and never will in this form. "
            f"SUPERSEDED 2026-09-29 by cell A2 (docs/readiness/{marker_package}, "
            "owner decision 198: carried into a new package); no file deleted."
        )
    else:
        notes = "this cell is retired and its work was superseded by later cells; no file deleted."
    text = pkg["ledger_path"].read_text(encoding="utf-8")
    text += (
        f"| 2026-01-01 | {donor_run_id} | no | "
        f"docs/readiness/{donor_package}/generation-plan-registered-v1.json | {notes} |\n"
    )
    pkg["ledger_path"].write_text(text, encoding="utf-8", newline="\n")


def test_a_superseded_donors_own_readiness_package_quoting_the_old_pin_converges(tmp_path):
    """The donor package -- resolved from a DIFFERENT row's 'artifacts'
    column, found by the ledger's own SUPERSEDED marker naming this cell's
    own package by name -- keeps the carried-over cell's pre-carry-over pin
    forever in its own registered documents. The re-pin must still succeed
    and must never touch the donor's bytes."""
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
    )
    _add_donor_ledger_row(pkg, donor_run_id="DONOR-RUN-1", donor_package="donor-pkg", marker_package="test-pkg")

    donor_dir = pkg["repo"] / "docs/readiness/donor-pkg"
    _write(
        donor_dir / "aa-generation-plan-registered-v1.json",
        {
            "purpose": f"{RUN_ID}: the cell's own plan document, as registered under the donor",
            "prepared_phase_supply": {
                "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                "sha256": pkg["old_artifact_sha"],
            },
        },
    )
    _write(
        donor_dir / "registered-facts-v1.json",
        {
            "run_id": RUN_ID,
            "prepared_phase_supply": {
                "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                "sha256": pkg["old_artifact_sha"],
            },
        },
    )
    _git(pkg["repo"], "add", "-A")
    _git(
        pkg["repo"], "commit", "-q", "-m",
        "mark a donor row superseded by this package and add the donor's own frozen records",
    )

    donor_snapshot = {path: path.read_bytes() for path in donor_dir.iterdir() if path.is_file()}

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    summary = run(pkg, fake, allow_output_change=True)  # must not raise RepinError

    assert summary["cells"][0]["artifact"]["rebuilt"] is True
    for path, content in donor_snapshot.items():
        assert path.read_bytes() == content, f"{path} was rewritten by a re-pin that does not own it"
    assert pkg["old_artifact_sha"] not in _all_text(pkg)


def test_a_live_foreign_package_quoting_the_hash_still_refuses(tmp_path):
    """A package with NO supersession marker at all -- an ordinary foreign
    package that happens to name the current run id and quote the old pin --
    is not exempted by this item: ``_superseded_donor_package_dirs`` finds no
    marker naming this cell's own package, so the donor-package set stays
    empty and the scan refuses exactly as it always did."""
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
    )
    _add_donor_ledger_row(pkg, donor_run_id="DONOR-RUN-1", donor_package="live-foreign-pkg", marker_package=None)

    live_dir = pkg["repo"] / "docs/readiness/live-foreign-pkg"
    _write(
        live_dir / "README.md",
        f"{RUN_ID}: still live, quotes sha256 `{pkg['old_artifact_sha']}` for its own reasons.\n",
    )
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "add a live foreign package with no supersession marker at all")

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    with pytest.raises(RepinError, match="residue"):
        run(pkg, fake, allow_output_change=True)


def test_a_superseded_marker_naming_a_different_package_still_refuses(tmp_path):
    """Supersession must be explicit AND must name THIS cell's own package by
    name: a marker that names some OTHER package is not this cell's own
    donor, and the scan must still refuse -- the exemption is not
    name-symmetric with 'superseded' appearing anywhere in the ledger."""
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
    )
    _add_donor_ledger_row(
        pkg, donor_run_id="DONOR-RUN-1", donor_package="donor-pkg", marker_package="some-other-pkg"
    )

    donor_dir = pkg["repo"] / "docs/readiness/donor-pkg"
    _write(
        donor_dir / "aa-generation-plan-registered-v1.json",
        {
            "purpose": f"{RUN_ID}: the cell's own plan document, as registered under the donor",
            "prepared_phase_supply": {
                "relpath": f"prepared/{RUN_ID}/phase-supply-v1.json",
                "sha256": pkg["old_artifact_sha"],
            },
        },
    )
    _git(pkg["repo"], "add", "-A")
    _git(
        pkg["repo"], "commit", "-q", "-m",
        "mark a donor row superseded by a DIFFERENT package, not this cell's own",
    )

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    with pytest.raises(RepinError, match="residue"):
        run(pkg, fake, allow_output_change=True)


def test_superseded_donor_package_dirs_reads_the_ledger_marker(tmp_path):
    """:func:`_superseded_donor_package_dirs` finds a donor package by its
    own row's SUPERSEDED marker naming ``readiness_dir.name`` -- never by run
    id (the donor's own row ordinarily carries a DIFFERENT run id than any
    cell being re-pinned) -- and reads the donor's package directory from
    THAT SAME row's 'artifacts' column. A marker naming some other package,
    no marker at all, or a missing ledger file all resolve to nothing."""
    ledger_path = tmp_path / "exposure-ledger.md"
    ledger_path.write_text(
        "# Exposure ledger\n\n"
        "| date | run/experiment id | consumed | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 2026-01-01 | DONOR-RUN-A | no | docs/readiness/donor-pkg-a/plan.json | "
        "SUPERSEDED 2026-09-29 by cell A2 (docs/readiness/current-pkg, owner decision 198: notes) |\n"
        "| 2026-01-01 | DONOR-RUN-B | no | docs/readiness/donor-pkg-b/plan.json | "
        "SUPERSEDED 2026-09-29 by cell A2 (docs/readiness/some-other-pkg, owner decision 198: notes) |\n"
        "| 2026-01-01 | DONOR-RUN-C | no | docs/readiness/donor-pkg-c/plan.json | no marker at all |\n",
        encoding="utf-8",
    )

    assert _superseded_donor_package_dirs(tmp_path, ledger_path, tmp_path / "docs/readiness/current-pkg") == {
        (tmp_path / "docs" / "readiness" / "donor-pkg-a").resolve()
    }
    assert _superseded_donor_package_dirs(tmp_path, ledger_path, tmp_path / "docs/readiness/some-other-pkg") == {
        (tmp_path / "docs" / "readiness" / "donor-pkg-b").resolve()
    }
    assert _superseded_donor_package_dirs(tmp_path, ledger_path, tmp_path / "docs/readiness/no-such-pkg") == set()
    assert (
        _superseded_donor_package_dirs(tmp_path, tmp_path / "missing.md", tmp_path / "docs/readiness/current-pkg")
        == set()
    )


def test_is_superseded_donor_readiness_record_matches_package_and_preregistration_sibling(tmp_path):
    """:func:`_is_superseded_donor_readiness_record` exempts every file
    inside a named donor package directory and its sibling preregistration
    note (``docs/readiness/<package>-preregistration*.md``), but nothing
    else -- not an unrelated sibling file, not another package's own
    directory, and nothing at all once ``superseded_donor_package_dirs`` is
    empty."""
    readiness_root = (tmp_path / "docs" / "readiness").resolve()
    package_dir = (readiness_root / "donor-pkg").resolve()

    inside_file = readiness_root / "donor-pkg" / "README.md"
    inside_file.parent.mkdir(parents=True)
    inside_file.write_text("x", encoding="utf-8")
    sibling_preregistration = readiness_root / "donor-pkg-preregistration.md"
    sibling_preregistration.write_text("x", encoding="utf-8")
    unrelated_sibling = readiness_root / "donor-pkg-other-notes.md"
    unrelated_sibling.write_text("x", encoding="utf-8")
    other_dir_file = readiness_root / "other-pkg" / "README.md"
    other_dir_file.parent.mkdir(parents=True)
    other_dir_file.write_text("x", encoding="utf-8")

    dirs = {package_dir}
    assert _is_superseded_donor_readiness_record(
        inside_file, readiness_root=readiness_root, superseded_donor_package_dirs=dirs
    ) is True
    assert _is_superseded_donor_readiness_record(
        sibling_preregistration, readiness_root=readiness_root, superseded_donor_package_dirs=dirs
    ) is True
    assert _is_superseded_donor_readiness_record(
        unrelated_sibling, readiness_root=readiness_root, superseded_donor_package_dirs=dirs
    ) is False
    assert _is_superseded_donor_readiness_record(
        other_dir_file, readiness_root=readiness_root, superseded_donor_package_dirs=dirs
    ) is False
    assert _is_superseded_donor_readiness_record(
        inside_file, readiness_root=readiness_root, superseded_donor_package_dirs=set()
    ) is False


def test_explain_residue_prints_the_rules_considered_for_each_hit(tmp_path, capsys):
    """``--explain-residue`` (``explain=True``) prints, per hit, which
    exemption rule(s) were considered and what each decided -- the
    diagnostic the 2026-09-28 ruling asked for so the next refusal does not
    require re-deriving the exemption logic by hand."""
    pkg = build_package(
        tmp_path,
        old_artifact_output={"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"], "row-b": ["v2"]}}},
    )

    parent_dir = pkg["repo"] / "docs/readiness/parent-pkg"
    _write(
        parent_dir / "generation-plan-registered-v1.json",
        {
            "execution_plan": {"attempt_id": "attempt-1", "run_id": RUN_ID},
            "prepared_phase_supply": {"sha256": pkg["old_artifact_sha"]},
            "purpose": f"{RUN_ID}: same attempt id as the cell being re-pinned",
        },
    )
    _git(pkg["repo"], "add", "-A")
    _git(pkg["repo"], "commit", "-q", "-m", "add a foreign-directory plan document naming the CURRENT attempt")

    fake = Fake(mismatched={RUN_ID}, outputs={RUN_ID: {"facets": {"p0": {}}, "values": {"p0": {"row-a": ["v1"]}}}})
    with pytest.raises(RepinError, match="residue"):
        run(pkg, fake, explain_residue=True, allow_output_change=True)

    captured = capsys.readouterr()
    assert "[explain-residue]" in captured.err
    assert "foreign-readiness-package=False" in captured.err
    assert "sealed-package-record=False" in captured.err


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
