"""The pre-launch flight registration gate (owner decision 163), on synthetic trees.

``scripts/checks/flight_registration_check.py`` refuses a ready, unflown cell unless every
generation and FIT run id carries a ROOT COUNTERSIGNED exposure row, the decision receipt that row
names exists on the data root with the run id eligible, and the cell's readiness package declares
a READ run id whose own ledger row exists. Every finding is exercised here on a miniature
repository and data root built under ``tmp_path``; one test at the end runs the gate over the real
repository when the data root is materialised and asserts only a documented exit code.

Zero model, tokenizer, encoder, scorer, network and GPU contacts.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_CHECKS = _REPO / "scripts" / "checks"
if str(_CHECKS) not in sys.path:
    sys.path.insert(0, str(_CHECKS))

import flight_registration_check as gate  # noqa: E402

EXPERIMENT = "slurp-native-stage3-proof-fold-a-v1"
SMOKE = "slurp-native-stage3-proof-fold-a-smoke-4-v1"
RUN = "SAEA-SLURP-STAGE3-PROOF-FOLD-A-V1"
FIT = "SAEA-SLURP-STAGE3-PROOF-FOLD-A-FIT-V1"
SMOKE_RUN = "SAEA-SLURP-STAGE3-PROOF-FOLD-A-SMOKE-4-V1"
SMOKE_FIT = "SAEA-SLURP-STAGE3-PROOF-FOLD-A-SMOKE-4-FIT-V1"
READ = "SAEA-SLURP-STAGE3-PROOF-FOLD-A-READ-V1"
PACKAGE = "2026-09-27-slurp-stage3-proof-fold-a-v1"
RECEIPT = "coordination/slurp-stage3-proof-fold-a-v1/root-admission-v1.json"
DECISION_ID = "slurp-stage3-proof-fold-a-admission-v1"

LEDGER_COLUMNS = (
    "date", "run/experiment id", "execution profile", "scope", "model/tool",
    "speech carrier + split", "split role", "split identity hash", "consumed", "calls",
    "speech audio seconds", "gpu hours", "inherited exposure", "artifacts", "notes",
)
SIGNED = (
    "REGISTERED BEFORE CONTACT (root countersigned 2026-09-27 12:00 UTC by the coordinator; "
    f"decision receipt {RECEIPT}, decision id {DECISION_ID})"
)
DRAFT = "REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) 2026-09-27"


def _row(run_id: str, notes: str, *, date: str = "2026-09-27", consumed: str = "no",
         artifact: str | None = None) -> dict[str, str]:
    return {
        "date": date,
        "run/experiment id": run_id,
        "execution profile": "bounded-discovery-probe",
        "consumed": consumed,
        "artifacts": artifact or f"docs/readiness/{PACKAGE}/generation-plan-registered-v1.json",
        "notes": notes,
    }


def _ledger_text(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Exposure ledger", "",
        "| " + " | ".join(LEDGER_COLUMNS) + " |",
        "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(name, "-")) for name in LEDGER_COLUMNS) + " |")
    return "\n".join(lines) + "\n"


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


class World:
    """A synthetic repository + data root: one arm cell, one smoke cell, one package."""

    def __init__(self, tmp_path: Path) -> None:
        self.repo = tmp_path / "repo"
        self.data = tmp_path / "data"
        self.data.mkdir(parents=True)
        self.rows = {
            RUN: _row(RUN, SIGNED),
            FIT: _row(FIT, SIGNED),
            SMOKE_RUN: _row(SMOKE_RUN, SIGNED),
            SMOKE_FIT: _row(SMOKE_FIT, SIGNED),
            READ: _row(READ, "REGISTERED BEFORE RESULT READING (DRAFT, root countersignature pending)",
                       artifact=f"docs/readiness/{PACKAGE}/analysis-recipe-v1.json"),
        }
        self.eligible = [RUN, FIT, SMOKE_RUN, SMOKE_FIT]
        self.recipe = {"schema": "synthetic", "run_ids": {"arm": RUN, "read": READ}}
        self.states = {EXPERIMENT: "ready", SMOKE: "ready"}
        self.pin_sha: str | None = None  # None -> pin the real receipt hash

    def build(self) -> "World":
        receipt = {
            "schema": "saea-campaign-decision-v1",
            "decision_id": DECISION_ID,
            "status": "decided",
            "eligible_run_ids": list(self.eligible),
        }
        _write(self.data / RECEIPT, receipt)
        receipt_sha = hashlib.sha256((self.data / RECEIPT).read_bytes()).hexdigest()
        for experiment, run_id, fit_id in ((EXPERIMENT, RUN, FIT), (SMOKE, SMOKE_RUN, SMOKE_FIT)):
            _write(self.repo / "configs" / "baseline" / f"{experiment}-baseline.json",
                   {"native_contact_fit": {"run_id": fit_id}})
            _write(self.repo / "configs" / "experiment" / f"{experiment}.json", {
                "date": "2026-09-27",
                "cells": [{
                    "cell_id": experiment,
                    "run_id": run_id,
                    "baseline_fragment": f"{experiment}-baseline",
                    "readiness": {
                        "state": self.states[experiment],
                        "requirements": [{
                            "kind": "decision",
                            "expected_decision_id": DECISION_ID,
                            "relpath": RECEIPT,
                            "sha256": self.pin_sha or receipt_sha,
                        }],
                    },
                }],
            })
        _write(self.repo / "configs" / "campaign" / "plan.json",
               {"schema": "saea-campaign-plan-v1", "cells": [{"cell": EXPERIMENT, "experiment": EXPERIMENT}]})
        _write(self.repo / "docs" / "readiness" / PACKAGE / "generation-plan-registered-v1.json", {"run_id": RUN})
        _write(self.repo / "docs" / "readiness" / PACKAGE / "analysis-recipe-v1.json", self.recipe)
        _write(self.repo / "docs" / "exposure-ledger.md", _ledger_text(list(self.rows.values())))
        return self

    def run(self, **kwargs) -> dict:
        return gate.evaluate(self.repo, self.data, gate.EXPOSURE_LEDGER, **kwargs)


def _kinds(data: dict, cell_id: str = EXPERIMENT) -> list[str]:
    cell = next(c for c in data["cells"] if c["cell_id"] == cell_id)
    return [finding["kind"] for finding in cell["findings"]]


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


def test_a_complete_registration_passes_both_modes(world: World) -> None:
    world.build()
    tree = world.run()
    assert tree["passed"] and tree["mode"] == "tree"
    assert _kinds(tree) == [] and _kinds(tree, SMOKE) == []
    launch = world.run(cells=[f"{EXPERIMENT}:{EXPERIMENT}", SMOKE])
    assert launch["passed"] and launch["mode"] == "launch"
    arm = next(c for c in launch["cells"] if c["cell_id"] == EXPERIMENT)
    assert arm["run_ids"] == {"generation": RUN, "native_contact_fit": FIT}
    assert arm["read_run_id"] == READ and arm["read_row_countersigned"] is False
    assert arm["package"] == f"docs/readiness/{PACKAGE}"


def test_a_draft_flight_row_is_refused(world: World) -> None:
    world.rows[FIT] = _row(FIT, DRAFT)
    data = world.build().run(cells=[EXPERIMENT])
    assert not data["passed"]
    assert "row-not-countersigned" in _kinds(data)


def test_the_roll3_disclosure_wording_is_not_a_countersignature(world: World) -> None:
    world.rows[RUN] = _row(RUN, (
        "REGISTERED BEFORE CONTACT (draft at contact -- DEFECT DISCLOSED: the root countersignature "
        f"was NOT written into this row before the flight; decision receipt {RECEIPT})"
    ))
    data = world.build().run(cells=[EXPERIMENT])
    assert "row-not-countersigned" in _kinds(data)


def test_a_missing_or_duplicated_flight_row_is_refused(world: World) -> None:
    del world.rows[FIT]
    assert "missing-row" in _kinds(world.build().run(cells=[EXPERIMENT]))


def test_a_missing_receipt_is_refused(world: World) -> None:
    world.build()
    (world.data / RECEIPT).unlink()
    assert "receipt-missing" in _kinds(world.run(cells=[EXPERIMENT]))


def test_a_run_id_the_receipt_does_not_list_is_refused(world: World) -> None:
    world.eligible = [RUN, SMOKE_RUN, SMOKE_FIT]
    data = world.build().run(cells=[EXPERIMENT])
    cell = data["cells"][0]
    assert [f["run_id"] for f in cell["findings"] if f["kind"] == "run-not-eligible"] == [FIT]


def test_a_receipt_that_moved_after_its_pin_is_refused(world: World) -> None:
    world.pin_sha = "0" * 64
    assert "receipt-hash-mismatch" in _kinds(world.build().run(cells=[EXPERIMENT]))


def test_a_recipe_without_a_read_run_id_is_refused(world: World) -> None:
    world.recipe = {"schema": "synthetic", "output": {"analysis_root": f"analysis/{READ}"}}
    data = world.build().run(cells=[EXPERIMENT])
    assert _kinds(data) == ["no-read-run-id"]


def test_top_level_read_run_id_is_accepted(world: World) -> None:
    world.recipe = {"schema": "synthetic", "read_run_id": READ}
    assert world.build().run(cells=[EXPERIMENT])["passed"]


def test_a_declared_read_without_its_ledger_row_is_refused(world: World) -> None:
    del world.rows[READ]
    assert _kinds(world.build().run(cells=[EXPERIMENT])) == ["read-row-missing"]


def test_a_consumed_cell_is_reported_and_never_blocks(world: World) -> None:
    world.rows[RUN] = _row(RUN, DRAFT)
    world.build()
    (world.data / "runs" / RUN / "attempt-x").mkdir(parents=True)
    data = world.run(cells=[EXPERIMENT])
    cell = data["cells"][0]
    assert data["passed"] and cell["severity"] == "advisory"
    assert cell["consumed_by"] == f"runs/{RUN}"
    assert "row-not-countersigned" in _kinds(data)


def test_tree_mode_blocks_a_new_cell_and_advises_a_stale_one(world: World) -> None:
    world.rows[RUN] = _row(RUN, DRAFT)
    world.build()
    assert not world.run()["passed"]
    later = world.run(strict_from=dt.date(2026, 9, 28))
    cell = next(c for c in later["cells"] if c["cell_id"] == EXPERIMENT)
    assert later["passed"] and cell["scope_note"].startswith("stale-ready")
    # ...and the same stale cell is still refused at launch.
    assert not world.run(cells=[EXPERIMENT], strict_from=dt.date(2026, 9, 28))["passed"]


def test_a_named_held_cell_is_refused_and_tree_mode_only_previews_it(world: World) -> None:
    world.states[EXPERIMENT] = "held"
    world.build()
    assert _kinds(world.run(cells=[EXPERIMENT]))[0] == "not-ready"
    tree = world.run(include_held=True)
    held = next(c for c in tree["cells"] if c["cell_id"] == EXPERIMENT)
    assert tree["passed"] and held["scope_note"].startswith("preview")


def test_the_campaign_plan_adds_its_cells(world: World) -> None:
    world.rows[RUN] = _row(RUN, DRAFT)
    world.build()
    data = world.run(cells=[SMOKE], plans=[world.repo / "configs" / "campaign" / "plan.json"])
    assert sorted(c["cell_id"] for c in data["cells"]) == sorted([EXPERIMENT, SMOKE])
    assert data["blocking_cells"] == [EXPERIMENT]


def test_an_unknown_cell_is_an_error_not_a_pass(world: World) -> None:
    world.build()
    with pytest.raises(gate.FlightRegistrationCheckError):
        world.run(cells=["no-such-cell"])
    assert gate.main(["--repo-root", str(world.repo), "--data-root", str(world.data),
                      "--cell", "no-such-cell"]) == 2


def test_main_exit_codes(world: World, capsys) -> None:
    world.build()
    base = ["--repo-root", str(world.repo), "--data-root", str(world.data)]
    assert gate.main(base + ["--cell", EXPERIMENT]) == 0
    assert "ok:" in capsys.readouterr().out
    (world.data / RECEIPT).unlink()
    assert gate.main(base + ["--cell", EXPERIMENT]) == 1
    assert "[receipt-missing]" in capsys.readouterr().out
    assert gate.main(["--repo-root", str(world.repo), "--data-root", str(world.data / "absent")]) == 2


def test_the_batch_driver_runs_the_gate_in_prelaunch() -> None:
    text = (_REPO / "scripts" / "flights" / "batch" / "batch_driver.sh").read_text(encoding="utf-8")
    prelaunch = text.split("prelaunch() {", 1)[1].split("\n}\n", 1)[0]
    assert 'registration_gate "$1"' in prelaunch
    assert "REGCHECK=$MAIN/scripts/checks/flight_registration_check.py" in text
    assert "REFUSED" in text.split("registration_gate() {", 1)[1].split("\n}\n", 1)[0]


def _data_root() -> Path | None:
    raw = os.environ.get("SPEECHRL_DATA_DIR", "").strip()
    root = Path(raw) if raw else None
    return root if root is not None and root.is_dir() else None


@pytest.mark.skipif(_data_root() is None, reason="SPEECHRL_DATA_DIR is not materialised on this host")
def test_the_real_tree_terminates_with_a_documented_exit_code() -> None:
    code = gate.main(["--repo-root", str(_REPO), "--data-root", str(_data_root()), "--json"])
    assert code in (0, 1)
