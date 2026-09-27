"""Identity-matched rewriting of a cell's own 'preparation' readiness requirement.

Until 2026-09-26 ``core.flight.repin._set_preparation_requirement`` rewrote
EVERY ``kind == "preparation"`` entry of a cell's readiness requirements to the
freshly minted prepared-supply pin. That was invisible while every committed
cell carried exactly one such entry (its own supply), and it would have
silently broken the first flip of the registered AGREE family, whose cells
carry two: the pre-computed exemplar-intent agreement table and their own
supply. These tests pin the repaired rule -- match on the artifact's identity
(its ``relpath``, the only key ``core.flight.campaign.declared_readiness``
verifies a requirement by), never on ``kind`` -- against the real AGREE
fragments (read-only, copied into ``tmp_path``) and against the pre-fix
implementation frozen here as the comparison oracle.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Mapping
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.flight import repin as module
from speech_aware_evidence_acquisition.core.flight.repin import (
    ArtifactPin,
    RepinError,
    is_own_supply_requirement,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
AGREE_W1_FRAGMENT = REPO_ROOT / "configs/experiment/slurp-native-stage3-agree-w1-fold-a-v1.json"
AGREE_SMOKE_FRAGMENT = REPO_ROOT / "configs/experiment/slurp-native-stage3-agree-w1-fold-a-smoke-4-v1.json"
AGREE_AA_FRAGMENT = REPO_ROOT / "configs/experiment/slurp-native-stage3-agree-aa-fold-a-v1.json"
AGREE_ARM_CELL = "slurp-native-stage3-agree-w1-fold-a-v1"
AGREE_SMOKE_CELL = "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"
AGREEMENT_TABLE_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl"
NEW_SHA = "f" * 64


def _legacy_set_preparation_requirement(experiment_path: Path, *, cell_id: str, pin: ArtifactPin) -> None:
    """The pre-fix implementation (study commit 9255ac71), frozen verbatim as
    the comparison oracle: every ``kind == "preparation"`` entry is rewritten."""
    document = module._read_json(experiment_path)
    if not isinstance(document, dict) or not isinstance(document.get("cells"), list):
        raise RepinError(f"experiment fragment {experiment_path} has no cells list")
    found = False
    for cell_doc in document["cells"]:
        if not isinstance(cell_doc, Mapping) or cell_doc.get("cell_id") != cell_id:
            continue
        readiness = cell_doc.get("readiness")
        requirements = readiness.get("requirements") if isinstance(readiness, Mapping) else None
        if not isinstance(requirements, list):
            continue
        for entry in requirements:
            if isinstance(entry, dict) and entry.get("kind") == "preparation":
                entry["relpath"] = pin.relpath
                entry["sha256"] = pin.sha256
                found = True
    if not found:
        for cell_doc in document["cells"]:
            if not isinstance(cell_doc, Mapping) or cell_doc.get("cell_id") != cell_id:
                continue
            readiness = cell_doc.get("readiness")
            if not isinstance(readiness, dict):
                continue
            requirements = readiness.setdefault("requirements", [])
            if isinstance(requirements, list):
                requirements.append({
                    "kind": "preparation",
                    "relpath": pin.relpath,
                    "sha256": pin.sha256,
                    "reason": "Model-free first-phase supply prepared by core.flight.repin on the launch commit; zero model, tokenizer or encoder contact.",
                })
                found = True
    if not found:
        raise RepinError(
            f"cell {cell_id!r} in {experiment_path} has no readiness block to carry a 'preparation' requirement"
        )
    module._write_json(experiment_path, document)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy(source: Path, tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copyfile(source, target)
    return target


def _write_fragment(tmp_path: Path, name: str, cells: list[dict]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps({"cells": cells}, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _cell(document: Mapping, cell_id: str) -> dict:
    return next(cell for cell in document["cells"] if cell.get("cell_id") == cell_id)


def _requirements(path: Path, cell_id: str) -> list[dict]:
    return _cell(json.loads(path.read_text(encoding="utf-8")), cell_id)["readiness"]["requirements"]


def _canonical(value: object) -> bytes:
    """Key order included: byte-for-byte as ``_write_json`` would serialize it."""
    return json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8")


def _both(tmp_path: Path, source: Path, *, cell_id: str, run_id: str, previous_pin: ArtifactPin | None, pin: ArtifactPin):
    """Run the fixed and the legacy implementation on two copies of ``source``."""
    fixed = _copy(source, tmp_path, "fixed.json")
    legacy = _copy(source, tmp_path, "legacy.json")
    report = module._set_preparation_requirement(fixed, cell_id=cell_id, run_id=run_id, previous_pin=previous_pin, pin=pin)
    _legacy_set_preparation_requirement(legacy, cell_id=cell_id, pin=pin)
    return fixed, legacy, report


# --------------------------------------------------------------------------
# The real AGREE package, read-only: two requirements, only the own one moves.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fragment", "cell_id"),
    [(AGREE_W1_FRAGMENT, AGREE_ARM_CELL), (AGREE_SMOKE_FRAGMENT, AGREE_SMOKE_CELL)],
    ids=["arm", "smoke"],
)
def test_the_agree_cells_keep_their_agreement_table_and_update_only_their_own_supply(tmp_path, fragment, cell_id):
    committed_sha = _sha(fragment)
    committed = json.loads(fragment.read_text(encoding="utf-8"))
    cell = _cell(committed, cell_id)
    run_id = cell["run_id"]
    before = cell["readiness"]["requirements"]
    # Precondition on the committed package: two 'preparation' requirements,
    # the agreement table first, this cell's own (not yet minted) supply
    # second, and no baseline pin yet -- exactly the shape the fix is for.
    assert [entry["kind"] for entry in before] == ["preparation", "preparation"]
    assert before[0]["relpath"] == AGREEMENT_TABLE_RELPATH
    assert before[1]["relpath"] == f"prepared/{run_id}/phase-supply-v1.json"
    baseline = json.loads((REPO_ROOT / "configs/baseline" / f"{cell['baseline_fragment']}.json").read_text(encoding="utf-8"))
    assert "prepared_phase_supply" not in baseline

    pin = ArtifactPin(f"prepared/{run_id}/phase-supply-v2.json", NEW_SHA)
    fixed, legacy, report = _both(tmp_path, fragment, cell_id=cell_id, run_id=run_id, previous_pin=None, pin=pin)
    after = _requirements(fixed, cell_id)

    assert report == {"updated": 1, "appended": 0, "kept": 1}
    assert len(after) == len(before)
    assert _canonical(after[0]) == _canonical(before[0]), "the agreement-table requirement must survive byte-for-byte"
    assert after[1]["relpath"] == pin.relpath and after[1]["sha256"] == pin.sha256
    assert after[1]["reason"] == before[1]["reason"] and list(after[1]) == list(before[1])
    # the sibling cell in the same fragment is untouched
    for other in (entry["cell_id"] for entry in committed["cells"] if entry["cell_id"] != cell_id):
        assert _canonical(_requirements(fixed, other)) == _canonical(_cell(committed, other)["readiness"]["requirements"])
    # and the legacy oracle reproduces the defect: it overwrote the agreement table too
    clobbered = _requirements(legacy, cell_id)
    assert clobbered[0]["relpath"] == pin.relpath and clobbered[0]["sha256"] == NEW_SHA
    assert fixed.read_bytes() != legacy.read_bytes()
    assert _sha(fragment) == committed_sha, "the committed fixture is read-only"


def test_the_agree_aa_replicate_with_one_requirement_rewrites_exactly_as_before(tmp_path):
    committed_sha = _sha(AGREE_AA_FRAGMENT)
    committed = json.loads(AGREE_AA_FRAGMENT.read_text(encoding="utf-8"))
    (cell,) = committed["cells"]
    run_id = cell["run_id"]
    own = [entry["relpath"] for entry in cell["readiness"]["requirements"] if entry["kind"] == "preparation"]
    assert own == [f"prepared/{run_id}/phase-supply-v1.json"]

    pin = ArtifactPin(f"prepared/{run_id}/phase-supply-v2.json", NEW_SHA)
    fixed, legacy, report = _both(tmp_path, AGREE_AA_FRAGMENT, cell_id=cell["cell_id"], run_id=run_id, previous_pin=None, pin=pin)

    assert report == {"updated": 1, "appended": 0, "kept": 0}
    assert fixed.read_bytes() == legacy.read_bytes()
    assert _requirements(fixed, cell["cell_id"])[0]["relpath"] == pin.relpath
    assert _sha(AGREE_AA_FRAGMENT) == committed_sha


# --------------------------------------------------------------------------
# Synthetic shapes: none, one, foreign-only, inherited pin, duplicates.
# --------------------------------------------------------------------------


DECISION = {
    "kind": "decision",
    "expected_decision_id": "decision-1",
    "relpath": "coordination/decision.json",
    "sha256": "d" * 64,
    "reason": "held for the owner decision",
}


def test_a_cell_with_no_preparation_requirement_gets_exactly_one_appended(tmp_path):
    source = _write_fragment(tmp_path, "src.json", [{"cell_id": "c", "run_id": "MINE", "readiness": {"state": "held", "requirements": [dict(DECISION)]}}])
    pin = ArtifactPin("prepared/MINE/phase-supply-v1.json", NEW_SHA)

    fixed, legacy, report = _both(tmp_path, source, cell_id="c", run_id="MINE", previous_pin=None, pin=pin)

    assert report == {"updated": 0, "appended": 1, "kept": 0}
    requirements = _requirements(fixed, "c")
    assert [entry["kind"] for entry in requirements] == ["decision", "preparation"]
    assert _canonical(requirements[0]) == _canonical(DECISION)
    assert requirements[1]["relpath"] == pin.relpath and requirements[1]["sha256"] == pin.sha256
    assert requirements[1]["reason"].startswith("Model-free first-phase supply prepared by core.flight.repin")
    assert fixed.read_bytes() == legacy.read_bytes()


def test_an_empty_requirements_list_gets_exactly_one_appended(tmp_path):
    source = _write_fragment(tmp_path, "src.json", [{"cell_id": "c", "run_id": "MINE", "readiness": {"state": "held", "requirements": []}}])
    pin = ArtifactPin("prepared/MINE/phase-supply-v1.json", NEW_SHA)

    fixed, legacy, report = _both(tmp_path, source, cell_id="c", run_id="MINE", previous_pin=None, pin=pin)

    assert report == {"updated": 0, "appended": 1, "kept": 0}
    assert len(_requirements(fixed, "c")) == 1
    assert fixed.read_bytes() == legacy.read_bytes()


def test_a_requirement_matching_by_kind_but_not_by_identity_is_not_touched(tmp_path):
    foreign = [
        {"kind": "preparation", "relpath": "prepared/OTHER-RUN/phase-supply-v1.json", "sha256": "1" * 64, "reason": "a sibling's supply"},
        {"kind": "preparation", "relpath": "prepared/MINE/agreement.jsonl", "sha256": "2" * 64, "reason": "a table under this run id that is not a phase supply"},
        {"kind": "preparation", "relpath": "coordination/wire-verdict.json", "sha256": "3" * 64, "reason": "a wire verdict"},
    ]
    source = _write_fragment(tmp_path, "src.json", [{"cell_id": "c", "run_id": "MINE", "readiness": {"state": "held", "requirements": [dict(entry) for entry in foreign]}}])
    pin = ArtifactPin("prepared/MINE/phase-supply-v1.json", NEW_SHA)

    fixed, legacy, report = _both(tmp_path, source, cell_id="c", run_id="MINE", previous_pin=None, pin=pin)

    assert report == {"updated": 0, "appended": 1, "kept": 3}
    requirements = _requirements(fixed, "c")
    assert len(requirements) == 4
    for kept, original in zip(requirements[:3], foreign):
        assert _canonical(kept) == _canonical(original)
    assert requirements[3]["relpath"] == pin.relpath and requirements[3]["sha256"] == pin.sha256
    # the legacy oracle rewrote all three foreign entries and appended nothing
    assert [entry["relpath"] for entry in _requirements(legacy, "c")] == [pin.relpath] * 3


def test_the_superseded_pin_is_matched_even_under_a_sibling_run_id(tmp_path):
    """A cell that inherited a sibling's supply verbatim (B8b from B7r) names
    that sibling's artifact in both its baseline pin and its requirement; the
    superseded pin identifies the entry although it is not under this run id."""
    inherited = {"kind": "preparation", "relpath": "prepared/SIBLING-RUN/phase-supply-v1.json", "sha256": "1" * 64, "reason": "inherited supply"}
    source = _write_fragment(tmp_path, "src.json", [{"cell_id": "c", "run_id": "MINE", "readiness": {"state": "held", "requirements": [dict(inherited)]}}])
    pin = ArtifactPin("prepared/MINE/phase-supply-v1.json", NEW_SHA)
    previous = ArtifactPin(inherited["relpath"], inherited["sha256"])

    fixed, legacy, report = _both(tmp_path, source, cell_id="c", run_id="MINE", previous_pin=previous, pin=pin)

    assert report == {"updated": 1, "appended": 0, "kept": 0}
    assert fixed.read_bytes() == legacy.read_bytes()
    (only,) = _requirements(fixed, "c")
    assert only["relpath"] == pin.relpath and only["sha256"] == NEW_SHA and only["reason"] == "inherited supply"

    # without the superseded pin the same entry is a foreign supply and is kept
    fixed_without = _copy(source, tmp_path, "without.json")
    report_without = module._set_preparation_requirement(fixed_without, cell_id="c", run_id="MINE", previous_pin=None, pin=pin)
    assert report_without == {"updated": 0, "appended": 1, "kept": 1}
    assert _canonical(_requirements(fixed_without, "c")[0]) == _canonical(inherited)


def test_duplicate_own_supply_entries_are_all_updated_as_before(tmp_path):
    """Sixteen committed Stage-3 cells carry their own-supply requirement
    twice (byte-identical entries); both name the cell's supply and both move,
    exactly as the legacy tool moved them."""
    own = {"kind": "preparation", "relpath": "prepared/MINE/phase-supply-v1.json", "sha256": "1" * 64, "reason": "own supply"}
    source = _write_fragment(tmp_path, "src.json", [{"cell_id": "c", "run_id": "MINE", "readiness": {"state": "ready", "requirements": [dict(own), dict(own)]}}])
    pin = ArtifactPin("prepared/MINE/phase-supply-v2.json", NEW_SHA)

    fixed, legacy, report = _both(tmp_path, source, cell_id="c", run_id="MINE", previous_pin=ArtifactPin(own["relpath"], own["sha256"]), pin=pin)

    assert report == {"updated": 2, "appended": 0, "kept": 0}
    assert fixed.read_bytes() == legacy.read_bytes()
    assert [entry["relpath"] for entry in _requirements(fixed, "c")] == [pin.relpath, pin.relpath]


def test_only_the_named_cell_is_edited(tmp_path):
    own = {"kind": "preparation", "relpath": "prepared/MINE/phase-supply-v1.json", "sha256": "1" * 64, "reason": "own supply"}
    other = {"kind": "preparation", "relpath": "prepared/THEIRS/phase-supply-v1.json", "sha256": "2" * 64, "reason": "the other cell's supply"}
    source = _write_fragment(
        tmp_path,
        "src.json",
        [
            {"cell_id": "c", "run_id": "MINE", "readiness": {"state": "held", "requirements": [dict(own)]}},
            {"cell_id": "d", "run_id": "THEIRS", "readiness": {"state": "held", "requirements": [dict(other)]}},
        ],
    )
    pin = ArtifactPin("prepared/MINE/phase-supply-v2.json", NEW_SHA)

    fixed, legacy, report = _both(tmp_path, source, cell_id="c", run_id="MINE", previous_pin=None, pin=pin)

    assert report == {"updated": 1, "appended": 0, "kept": 0}
    assert fixed.read_bytes() == legacy.read_bytes()
    assert _canonical(_requirements(fixed, "d")) == _canonical([other])


def test_a_cell_without_a_readiness_block_is_still_refused(tmp_path):
    source = _write_fragment(tmp_path, "src.json", [{"cell_id": "c", "run_id": "MINE"}])
    with pytest.raises(RepinError, match="no readiness block"):
        module._set_preparation_requirement(source, cell_id="c", run_id="MINE", previous_pin=None, pin=ArtifactPin("prepared/MINE/phase-supply-v1.json", NEW_SHA))


# --------------------------------------------------------------------------
# The identity rule itself.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("entry", "previous_relpath", "expected"),
    [
        ({"kind": "preparation", "relpath": "prepared/MINE/phase-supply-v1.json"}, None, True),
        ({"kind": "preparation", "relpath": "prepared/MINE/phase-supply-v37.json"}, None, True),
        ({"kind": "preparation", "relpath": "prepared/MINE/phase-supply.json"}, None, False),
        ({"kind": "preparation", "relpath": "prepared/MINE/agreement.jsonl"}, None, False),
        ({"kind": "preparation", "relpath": "prepared/MINE-2/phase-supply-v1.json"}, None, False),
        ({"kind": "preparation", "relpath": "prepared/OTHER/phase-supply-v1.json"}, None, False),
        ({"kind": "preparation", "relpath": "prepared/OTHER/phase-supply-v1.json"}, "prepared/OTHER/phase-supply-v1.json", True),
        ({"kind": "preparation", "relpath": "prepared/OTHER/speech-supply.json"}, "prepared/OTHER/speech-supply.json", True),
        ({"kind": "decision", "relpath": "prepared/MINE/phase-supply-v1.json"}, None, False),
        ({"kind": "decision", "relpath": "prepared/OTHER/phase-supply-v1.json"}, "prepared/OTHER/phase-supply-v1.json", False),
        ({"kind": "preparation"}, None, False),
        ({"kind": "preparation", "relpath": ""}, None, False),
        ("prepared/MINE/phase-supply-v1.json", None, False),
    ],
)
def test_is_own_supply_requirement_matches_on_relpath_identity_never_on_kind_alone(entry, previous_relpath, expected):
    assert is_own_supply_requirement(entry, run_id="MINE", previous_relpath=previous_relpath) is expected
