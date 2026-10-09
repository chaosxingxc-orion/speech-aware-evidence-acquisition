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
        # owner decision 172, docs/superpowers/specs/2026-09-27-same-flight-supply-variant-
        # instrument-design.md: set on a cell to exercise the instrument-registration checks.
        # ``measurement`` is written as the EXPERIMENT fragment's top-level ``stage3_measurement``
        # (precedence 3 of stage3_effect_floor_check.py); ``supply_variants`` is written into the
        # EXPERIMENT baseline's ``native_episode.roles.solver.supply_variants``, exactly where the
        # real baselines carry it (see configs/baseline/*var2-supply-variants*.json).
        self.measurement: dict | None = None
        self.supply_variants: dict | None = None
        # resume-replay proof (coordinator, after the COMP-1 resume attempt 3 seal abort):
        # ``resume_from`` is written onto the EXPERIMENT cell exactly like a real resume cell
        # declares it; ``resume_replay_proof`` is written into the package's own
        # generation-plan-registered-v1.json when set, else that file keeps its plain {"run_id"}
        # shape (no block at all -- the "missing" case every other test already exercises).
        self.resume_from: dict | None = None
        self.resume_replay_proof: dict | None = None
        # Same-flight instrument, PHASE 2 (merge set C): written into the EXPERIMENT
        # baseline's native_episode.roles.perception.branches, exactly where the real
        # baselines will carry it once a phase-2 fragment is minted.
        self.perception_branches: dict | None = None
        # NX programme instrument E1: written into the EXPERIMENT baseline's
        # native_episode.roles.solver.template_variants (a node-template column cell).
        self.template_variants: dict | None = None

    def write_roster_receipt(
        self, roster_id: str, disjointness_proof: dict | None = None, **extra: object
    ) -> None:
        """A roster receipt under ``docs/receipts/rosters/`` (item D3's tuning/read overlap
        check reads exactly this convention: filename slug, top-level ``roster_id``,
        ``disjointness_proof``)."""

        payload: dict = {"schema": "saea-roster-receipt-v1", "roster_id": roster_id}
        if disjointness_proof is not None:
            payload["disjointness_proof"] = disjointness_proof
        payload.update(extra)
        _write(self.repo / "docs" / "receipts" / "rosters" / f"{roster_id.lower()}.json", payload)

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
            baseline: dict = {"native_contact_fit": {"run_id": fit_id}}
            if experiment == EXPERIMENT and self.supply_variants is not None:
                baseline["native_episode"] = {
                    "roles": {"solver": {"supply_variants": self.supply_variants}}
                }
            if experiment == EXPERIMENT and self.template_variants is not None:
                native_episode = baseline.setdefault("native_episode", {})
                native_episode.setdefault("roles", {}).setdefault("solver", {})[
                    "template_variants"
                ] = self.template_variants
            if experiment == EXPERIMENT and self.perception_branches is not None:
                native_episode = baseline.setdefault("native_episode", {})
                native_episode.setdefault("roles", {})["perception"] = {
                    "branches": self.perception_branches
                }
            _write(self.repo / "configs" / "baseline" / f"{experiment}-baseline.json", baseline)
            fragment: dict = {
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
            }
            if experiment == EXPERIMENT and self.measurement is not None:
                fragment["stage3_measurement"] = self.measurement
            if experiment == EXPERIMENT and self.resume_from is not None:
                fragment["cells"][0]["resume_from"] = self.resume_from
            _write(self.repo / "configs" / "experiment" / f"{experiment}.json", fragment)
        _write(self.repo / "configs" / "campaign" / "plan.json",
               {"schema": "saea-campaign-plan-v1", "cells": [{"cell": EXPERIMENT, "experiment": EXPERIMENT}]})
        registered_plan: dict = {"run_id": RUN}
        if self.resume_replay_proof is not None:
            registered_plan["resume_replay_proof"] = self.resume_replay_proof
        _write(self.repo / "docs" / "readiness" / PACKAGE / "generation-plan-registered-v1.json",
               registered_plan)
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


@pytest.mark.parametrize("run_id", [RUN, FIT])
@pytest.mark.parametrize("same_pin", [True, False])
def test_registered_supply_pin_must_match_the_members_actual_baseline(world, run_id, same_pin):
    world.build()
    pin = {"relpath": "prepared/own/phase-supply-v1.json", "sha256": "a" * 64}
    fragment = json.loads((world.repo / "configs/experiment" / f"{EXPERIMENT}.json").read_text())
    baseline = world.repo / "configs/baseline" / (fragment["cells"][0]["baseline_fragment"] + ".json")
    document = json.loads(baseline.read_text())
    document["prepared_phase_supply"] = pin
    _write(baseline, document)
    plan = world.repo / "docs/readiness" / PACKAGE / "generation-plan-registered-v1.json"
    if run_id == FIT:
        plan = plan.with_name("fit-plan-registered-v1.json")
    _write(plan, {"execution_plan": {"run_id": run_id},
                  "prepared_phase_supply": pin if same_pin else {
                      "relpath": "prepared/sibling/phase-supply-v1.json", "sha256": "b" * 64}})
    result = world.run(cells=[EXPERIMENT])
    assert ("registered-supply-binding" in _kinds(result)) is not same_pin
    assert result["passed"] is same_pin


def test_multi_cell_family_checks_each_members_own_fit_identity(world: World) -> None:
    del world.rows[SMOKE_FIT]
    world.build()
    path = world.repo / "configs/experiment" / f"{EXPERIMENT}.json"
    fragment = json.loads(path.read_text())
    sibling = json.loads((world.repo / "configs/experiment" / f"{SMOKE}.json").read_text())
    fragment["cells"].append(sibling["cells"][0])
    _write(path, fragment)
    report = world.run(cells=[f"{EXPERIMENT}:{EXPERIMENT}", f"{EXPERIMENT}:{SMOKE}"])
    arm = next(c for c in report["cells"] if c["cell_id"] == EXPERIMENT)
    other = next(c for c in report["cells"] if c["cell_id"] == SMOKE)
    assert arm["run_ids"]["native_contact_fit"] == FIT
    assert other["run_ids"]["native_contact_fit"] == SMOKE_FIT
    assert any(f["kind"] == "missing-row" and f["run_id"] == SMOKE_FIT for f in other["findings"])
    assert not report["passed"]


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


# --------------------------------------------------------------------------
# resume-replay proof (coordinator, after the COMP-1 resume attempt 3 seal abort)
# --------------------------------------------------------------------------

RESUME_FROM = {"attempt_id": "attempt-proof-fold-a-generation-v1", "trace_sha256": "a" * 64}
CLEAN_PROOF = {
    "rows_checked": 1080, "rows_failing": 0, "sealed_twice": 0,
    "checker_sha256": "b" * 64, "code_commit": "deadbeef",
}


def test_resume_cell_without_replay_proof_is_advisory_in_tree_and_blocking_at_launch(
    world: World,
) -> None:
    world.resume_from = RESUME_FROM
    world.build()
    tree = world.run()
    assert tree["passed"]  # advisory: reported, never fails the whole-tree scan
    assert "resume-replay-unproven" in _kinds(tree)
    launch = world.run(cells=[EXPERIMENT])
    assert not launch["passed"]  # BLOCKING: a live, unflown resume cell named at launch
    assert "resume-replay-unproven" in _kinds(launch)


def test_resume_cell_with_a_clean_replay_proof_passes_both_modes(world: World) -> None:
    world.resume_from = RESUME_FROM
    world.resume_replay_proof = CLEAN_PROOF
    world.build()
    assert world.run()["passed"]
    launch = world.run(cells=[EXPERIMENT])
    assert launch["passed"]
    cell = next(c for c in launch["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["resume_replay_proof"] == CLEAN_PROOF
    assert "resume-replay-unproven" not in _kinds(launch)


def test_resume_cell_with_an_incomplete_replay_proof_is_unproven(world: World) -> None:
    world.resume_from = RESUME_FROM
    world.resume_replay_proof = {k: v for k, v in CLEAN_PROOF.items() if k != "checker_sha256"}
    data = world.build().run(cells=[EXPERIMENT])
    assert not data["passed"]
    assert "resume-replay-unproven" in _kinds(data)


def test_resume_cell_with_a_failing_replay_proof_is_still_unproven(world: World) -> None:
    world.resume_from = RESUME_FROM
    world.resume_replay_proof = {**CLEAN_PROOF, "rows_failing": 2}
    data = world.build().run(cells=[EXPERIMENT])
    assert not data["passed"]
    assert "resume-replay-unproven" in _kinds(data)


def test_resume_cell_with_a_sealed_twice_replay_proof_is_still_unproven(world: World) -> None:
    world.resume_from = RESUME_FROM
    world.resume_replay_proof = {**CLEAN_PROOF, "sealed_twice": 1}
    data = world.build().run(cells=[EXPERIMENT])
    assert not data["passed"]
    assert "resume-replay-unproven" in _kinds(data)


def test_a_consumed_resume_cell_is_never_blocked_by_missing_replay_proof(world: World) -> None:
    world.resume_from = RESUME_FROM
    world.rows[RUN] = _row(RUN, DRAFT)
    world.build()
    (world.data / "runs" / RUN / "attempt-x").mkdir(parents=True)
    data = world.run(cells=[EXPERIMENT])
    cell = data["cells"][0]
    assert data["passed"] and cell["severity"] == "advisory"
    assert "resume-replay-unproven" in _kinds(data)  # still reported, never blocking


def test_tree_mode_skips_the_resume_replay_check_for_an_unnamed_flown_cell(world: World) -> None:
    world.resume_from = RESUME_FROM
    world.build()
    (world.data / "runs" / RUN / "attempt-x").mkdir(parents=True)
    data = world.run()
    cell = next(c for c in data["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["named"] is False and cell["consumed_by"] == f"runs/{RUN}"
    assert "resume-replay-unproven" not in _kinds(data)
    assert cell.get("resume_replay_proof") is None


def test_a_cell_without_resume_from_is_unaffected_by_the_resume_replay_check(world: World) -> None:
    world.build()  # world.resume_from is None by default
    data = world.run(cells=[EXPERIMENT])
    assert "resume-replay-unproven" not in _kinds(data)
    assert data["cells"][0]["resume_replay_proof"] is None


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


# --------------------------------------------------------------------------
# supply-variant instrument registration (owner decision 172, merge set A of
# docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-design.md section 4)
# --------------------------------------------------------------------------


def _two_arms(*, arm_visits: str | None = None) -> dict:
    block: dict = {
        "arms": [
            {"arm_id": "twin", "max_supplied_items": 10},
            {"arm_id": "plan", "deliver": True, "max_supplied_items": 10},
        ],
    }
    if arm_visits is not None:
        block["arm_visits"] = arm_visits
    return block


def test_arm_visits_not_first_is_refused_for_a_same_flight_supply_variant_cell(world: World) -> None:
    world.measurement = {
        "measurement_design": "same-flight-supply-variant",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
        "variant_cost": {"extra_contacts_per_row": 1, "extra_audio_seconds": 3.2},
    }
    world.supply_variants = _two_arms()  # arm_visits absent -> parser default "every"
    data = world.build().run(cells=[EXPERIMENT])
    assert "arm-visits-not-first" in _kinds(data)


def test_arm_visits_every_is_also_refused_for_offline_sealed_pool(world: World) -> None:
    # section 2: BOTH same-flight-supply-variant and offline-sealed-pool must declare "first".
    world.measurement = {
        "measurement_design": "offline-sealed-pool",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
        "variant_cost": {"extra_contacts_per_row": 1, "extra_audio_seconds": 3.2},
    }
    world.supply_variants = _two_arms(arm_visits="every")
    data = world.build().run(cells=[EXPERIMENT])
    assert "arm-visits-not-first" in _kinds(data)


def test_arm_visits_first_with_correct_cost_and_claim_passes_and_records_roster_fields(
    world: World,
) -> None:
    world.measurement = {
        "measurement_design": "same-flight-supply-variant",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
        "aa_arm_id": "twin",
        "tuning_roster": "docs/readiness/2026-09-27-svinst/tuning-roster-receipt-v1.json",
        "read_roster": "docs/readiness/2026-09-27-svinst/read-roster-receipt-v1.json",
        "variant_cost": {"extra_contacts_per_row": 1, "extra_audio_seconds": 3.2},
    }
    world.supply_variants = _two_arms(arm_visits="first")
    data = world.build().run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    assert "arm-visits-not-first" not in kinds
    assert "variant-cost-mismatch" not in kinds
    assert "variant-claim-not-nominated" not in kinds
    cell = next(c for c in data["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["supply_variant"]["measurement_design"] == "same-flight-supply-variant"
    assert cell["supply_variant"]["arm_visits"] == "first"
    assert cell["supply_variant"]["aa_arm_id"] == "twin"
    assert cell["supply_variant"]["tuning_roster"] == (
        "docs/readiness/2026-09-27-svinst/tuning-roster-receipt-v1.json"
    )
    assert cell["supply_variant"]["read_roster"] == (
        "docs/readiness/2026-09-27-svinst/read-roster-receipt-v1.json"
    )


def test_variant_cost_mismatch_on_a_wrong_contact_count(world: World) -> None:
    world.measurement = {
        "measurement_design": "same-flight-supply-variant",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
        # two arms -> the arm list's own extra is 1, not 2
        "variant_cost": {"extra_contacts_per_row": 2, "extra_audio_seconds": 3.2},
    }
    world.supply_variants = _two_arms(arm_visits="first")
    data = world.build().run(cells=[EXPERIMENT])
    assert "variant-cost-mismatch" in _kinds(data)


def test_variant_cost_mismatch_when_the_block_is_absent(world: World) -> None:
    world.measurement = {
        "measurement_design": "offline-sealed-pool",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
    }
    world.supply_variants = _two_arms(arm_visits="first")
    data = world.build().run(cells=[EXPERIMENT])
    assert "variant-cost-mismatch" in _kinds(data)


def test_variant_claim_not_nominated_when_missing_or_wrong(world: World) -> None:
    world.measurement = {
        "measurement_design": "same-flight-supply-variant",
        "expected_effect_pp": 1.0,
        "variant_cost": {"extra_contacts_per_row": 1, "extra_audio_seconds": 3.2},
        "claim": "admitted",
    }
    world.supply_variants = _two_arms(arm_visits="first")
    data = world.build().run(cells=[EXPERIMENT])
    assert "variant-claim-not-nominated" in _kinds(data)

    del world.measurement["claim"]
    data = world.build().run(cells=[EXPERIMENT])
    assert "variant-claim-not-nominated" in _kinds(data)


def test_a_design_outside_the_instrument_skips_the_supply_variant_checks(world: World) -> None:
    # a cross-flight cell may declare supply_variants (the VAR-2 shape) without arm_visits,
    # variant_cost or claim -- this gate must not invent a new requirement for it.
    world.measurement = {
        "measurement_design": "cross-flight-with-in-chain-replicate",
        "expected_effect_pp": 5.0,
        "replicate_run_id": "SAEA-SLURP-STAGE3-SOME-REPLICATE-V1",
    }
    world.supply_variants = _two_arms()  # no arm_visits, no variant_cost, no claim
    data = world.build().run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    assert "arm-visits-not-first" not in kinds
    assert "variant-cost-mismatch" not in kinds
    assert "variant-claim-not-nominated" not in kinds


def test_offline_sealed_pool_with_no_supply_variants_at_all_is_not_checked(world: World) -> None:
    # offline-sealed-pool is NOT exclusive to this instrument: the real ROLL-1/ROLL-2/ROLL-3 and
    # filler-chunk cells declare it for an ordinary offline sealed-pool read with no supply
    # variation whatsoever, and none of them carries a supply_variants block anywhere.
    world.measurement = {
        "measurement_design": "offline-sealed-pool",
        "expected_effect_pp": 0.67,
        "claims_benefit": False,
    }
    world.supply_variants = None
    data = world.build().run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    assert "arm-visits-not-first" not in kinds
    assert "variant-cost-mismatch" not in kinds
    assert "variant-claim-not-nominated" not in kinds


# --------------------------------------------------------------------------
# Perception-branch instrument registration (same-flight instrument, PHASE 2, merge set C,
# docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-variants-design.md
# section 4)
# --------------------------------------------------------------------------


def _three_branches(
    *, level: int = 1, twin_id: str | None = "T", b_prepared_seed: dict | None = "default",
) -> dict:
    b_branch = {
        "branch_id": "B", "max_supplied_items": 8,
        "overrides": {
            "knowledge_stores.intent-boundaries.phase_supply.perception.k": 16
        },
    }
    if b_prepared_seed == "default":
        b_branch["prepared_seed"] = {
            "relpath": "prepared/SAEA-SLURP-PERCEPTION-BRANCH-B-SEED-V1/seed.json",
            "sha256": "b" * 64,
        }
    elif b_prepared_seed is not None:
        b_branch["prepared_seed"] = b_prepared_seed
    branches = [b_branch, {"branch_id": "A", "deliver": True, "max_supplied_items": 8}]
    if twin_id is not None:
        branches.insert(1, {"branch_id": twin_id, "replicate_of": "A", "max_supplied_items": 8})
    return {"level": level, "fit_estimate": {}, "branches": branches}


def test_branch_level_missing_is_refused_for_a_perception_variant_cell(world: World) -> None:
    world.measurement = {
        "measurement_design": "same-flight-perception-variant",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
        "aa_arm_id": "T",
    }
    block = _three_branches()
    del block["level"]
    world.perception_branches = block
    data = world.build().run(cells=[EXPERIMENT])
    assert "branch-level-missing" in _kinds(data)


def test_a_declared_level_passes_the_level_check(world: World) -> None:
    world.measurement = {
        "measurement_design": "same-flight-perception-variant",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
        "aa_arm_id": "T",
    }
    world.perception_branches = _three_branches(level=2)
    data = world.build().run(cells=[EXPERIMENT])
    assert "branch-level-missing" not in _kinds(data)


def test_aa_arm_missing_when_no_branch_names_replicate_of(world: World) -> None:
    world.measurement = {
        "measurement_design": "same-flight-perception-variant",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
    }
    world.perception_branches = _three_branches(twin_id=None)
    data = world.build().run(cells=[EXPERIMENT])
    assert "aa-arm-missing" in _kinds(data)


def test_aa_arm_missing_when_aa_arm_id_disagrees_with_the_declared_twin(world: World) -> None:
    world.measurement = {
        "measurement_design": "same-flight-perception-variant",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
        "aa_arm_id": "not-the-twin",
    }
    world.perception_branches = _three_branches(twin_id="T")
    data = world.build().run(cells=[EXPERIMENT])
    assert "aa-arm-missing" in _kinds(data)


def test_perception_variant_claim_not_nominated_when_missing_or_wrong(world: World) -> None:
    world.measurement = {
        "measurement_design": "same-flight-perception-variant",
        "expected_effect_pp": 1.0,
        "aa_arm_id": "T",
        "claim": "admitted",
    }
    world.perception_branches = _three_branches()
    data = world.build().run(cells=[EXPERIMENT])
    assert "variant-claim-not-nominated" in _kinds(data)

    del world.measurement["claim"]
    data = world.build().run(cells=[EXPERIMENT])
    assert "variant-claim-not-nominated" in _kinds(data)


def test_a_well_formed_perception_variant_cell_passes_and_records_fields(world: World) -> None:
    world.measurement = {
        "measurement_design": "same-flight-perception-variant",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
        "aa_arm_id": "T",
        "tuning_roster": "docs/readiness/2026-09-28-svphase2/tuning-roster-receipt-v1.json",
        "read_roster": "docs/readiness/2026-09-28-svphase2/read-roster-receipt-v1.json",
        "variant_cost": {"extra_contacts_per_row": 2, "extra_audio_seconds": 6.4},
    }
    world.perception_branches = _three_branches(level=1)
    data = world.build().run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    assert "branch-level-missing" not in kinds
    assert "aa-arm-missing" not in kinds
    assert "variant-claim-not-nominated" not in kinds
    assert "branch-seed-unpinned" not in kinds
    cell = next(c for c in data["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["perception_branch"]["measurement_design"] == "same-flight-perception-variant"
    assert cell["perception_branch"]["level"] == 1
    assert cell["perception_branch"]["branches"] == 3
    assert cell["perception_branch"]["aa_arm_id"] == "T"


def test_branch_seed_unpinned_when_a_b_branch_declares_no_prepared_seed(world: World) -> None:
    world.measurement = {
        "measurement_design": "same-flight-perception-variant",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
        "aa_arm_id": "T",
    }
    world.perception_branches = _three_branches(b_prepared_seed=None)
    data = world.build().run(cells=[EXPERIMENT])
    assert "branch-seed-unpinned" in _kinds(data)


@pytest.mark.parametrize("bad_seed", [
    {"relpath": "prepared/x.json"},
    {"relpath": "prepared/x.json", "sha256": "not-hex"},
    {"relpath": "prepared/x.json", "sha256": "b" * 63},
    {"relpath": "", "sha256": "b" * 64},
    {"relpath": "prepared/x.json", "sha256": "b" * 64, "extra": "field"},
])
def test_branch_seed_unpinned_when_the_prepared_seed_is_malformed(
    world: World, bad_seed: dict,
) -> None:
    world.measurement = {
        "measurement_design": "same-flight-perception-variant",
        "expected_effect_pp": 1.0,
        "claim": "nominated",
        "aa_arm_id": "T",
    }
    world.perception_branches = _three_branches(b_prepared_seed=bad_seed)
    data = world.build().run(cells=[EXPERIMENT])
    assert "branch-seed-unpinned" in _kinds(data)


def test_branch_seed_unpinned_never_fires_for_a_or_t():
    """A and T never need a prepared_seed of their own (design: A's seed is the cell's own
    prepared_phase_supply, T takes A's seed) -- only a B branch's absence is checked."""

    branches = _three_branches(b_prepared_seed=None)["branches"]
    kinds = {row["branch_id"]: row for row in branches}
    assert "prepared_seed" not in kinds["T"]
    assert "prepared_seed" not in kinds["A"]


def test_a_design_outside_the_instrument_skips_the_perception_branch_checks(world: World) -> None:
    world.measurement = {
        "measurement_design": "cross-flight-with-in-chain-replicate",
        "expected_effect_pp": 5.0,
        "replicate_run_id": "SAEA-SLURP-STAGE3-SOME-REPLICATE-V1",
    }
    world.perception_branches = _three_branches(twin_id=None)
    data = world.build().run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    assert "branch-level-missing" not in kinds
    assert "aa-arm-missing" not in kinds
    assert "variant-claim-not-nominated" not in kinds


def test_perception_variant_with_no_branches_block_at_all_is_not_checked(world: World) -> None:
    world.measurement = {
        "measurement_design": "same-flight-perception-variant",
        "expected_effect_pp": 1.0,
    }
    world.perception_branches = None
    data = world.build().run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    assert "branch-level-missing" not in kinds
    assert "aa-arm-missing" not in kinds
    assert "variant-claim-not-nominated" not in kinds
    cell = next(c for c in data["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell.get("supply_variant") is None


def test_a_cell_with_no_stage3_measurement_at_all_is_not_checked(world: World) -> None:
    # the real, historical VAR-2 baselines (configs/baseline/*var2-supply-variants*.json)
    # declare supply_variants with no stage3_measurement block at all.
    world.supply_variants = _two_arms()
    data = world.build().run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    assert "arm-visits-not-first" not in kinds
    assert "variant-cost-mismatch" not in kinds
    assert "variant-claim-not-nominated" not in kinds
    cell = next(c for c in data["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell.get("supply_variant") is None


# --------------------------------------------------------------------------
# tuning/read roster split registration (item D3, docs/results/2026-09-27-verdict-
# reclassification.md: the AGREE agreement term was tuned and read on the same TRAIN Fold A
# roster; docs/readiness/2026-09-27-slurp-stage3-replan-v2.md section 3, row "Circular reads")
# --------------------------------------------------------------------------


def _cross_flight_measurement(**roster_fields: object) -> dict:
    # measurement_design deliberately NOT one of the supply-variant instrument designs: item D3's
    # own AGREE cell was a plain cross-flight cell, and the split must be checked there too.
    return {
        "measurement_design": "cross-flight-with-in-chain-replicate",
        "expected_effect_pp": 3.33,
        "replicate_run_id": "SAEA-SLURP-STAGE3-SOME-REPLICATE-V1",
        **roster_fields,
    }


def test_tuning_read_overlap_blocks_on_a_direct_name_match(world: World) -> None:
    world.measurement = _cross_flight_measurement(
        tuning_roster="SLURP-STAGE3-FOLD-A-V1", read_roster="SLURP-STAGE3-FOLD-A-V1"
    )
    data = world.build().run(cells=[EXPERIMENT])
    assert "tuning-read-overlap" in _kinds(data)
    assert not data["passed"]
    assert data["blocking_cells"] == [EXPERIMENT]


def test_tuning_read_overlap_blocks_when_a_roster_receipt_proves_shared_recordings(
    world: World,
) -> None:
    world.measurement = _cross_flight_measurement(
        tuning_roster="SLURP-TUNE-POOL-V1", read_roster="SLURP-READ-FOLD-A-V1"
    )
    world.build()
    world.write_roster_receipt(
        "SLURP-TUNE-POOL-V1",
        disjointness_proof={"slurp-read-fold-a-v1": {"shared_recordings": 12, "shared_utterances": 3}},
    )
    world.write_roster_receipt("SLURP-READ-FOLD-A-V1")
    data = world.run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    assert "tuning-read-overlap" in kinds
    assert "tuning-roster-unverified" not in kinds
    assert not data["passed"]


def test_disjoint_rosters_with_a_zero_overlap_receipt_pass(world: World) -> None:
    world.measurement = _cross_flight_measurement(
        tuning_roster="SLURP-TUNE-POOL-V1", read_roster="SLURP-READ-FOLD-A-V1"
    )
    world.build()
    world.write_roster_receipt(
        "SLURP-TUNE-POOL-V1",
        disjointness_proof={"slurp-read-fold-a-v1": {"shared_recordings": 0, "shared_utterances": 0}},
    )
    world.write_roster_receipt("SLURP-READ-FOLD-A-V1")
    data = world.run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    assert "tuning-read-overlap" not in kinds
    assert "tuning-roster-unverified" not in kinds
    assert data["passed"]


def test_tuning_roster_missing_is_advisory_on_an_otherwise_blocking_cell(world: World) -> None:
    world.measurement = _cross_flight_measurement()  # no tuning_roster / read_roster at all
    data = world.build().run(cells=[EXPERIMENT])
    cell = next(c for c in data["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["severity"] == "blocking"  # ready, unflown, named: this cell IS blocking-severity
    finding = next(f for f in cell["findings"] if f["kind"] == "tuning-roster-missing")
    assert finding["severity"] == "advisory"
    assert data["passed"]  # the advisory finding alone never fails the gate
    assert data["blocking_cells"] == []


def test_a_receipt_less_named_roster_is_advisory_not_blocked(world: World) -> None:
    world.measurement = _cross_flight_measurement(
        tuning_roster="SLURP-NO-RECEIPT-TUNE-V1", read_roster="SLURP-NO-RECEIPT-READ-V1"
    )
    data = world.build().run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    assert "tuning-roster-unverified" in kinds
    assert "tuning-read-overlap" not in kinds
    finding = next(f for f in data["cells"][0]["findings"] if f["kind"] == "tuning-roster-unverified")
    assert finding["severity"] == "advisory"
    assert data["passed"]


def test_explicit_none_tuning_roster_skips_the_overlap_check(world: World) -> None:
    world.measurement = _cross_flight_measurement(
        tuning_roster="none", read_roster="SLURP-READ-FOLD-A-V1"
    )
    data = world.build().run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    assert "tuning-read-overlap" not in kinds
    assert "tuning-roster-unverified" not in kinds
    assert "tuning-roster-missing" not in kinds
    assert data["passed"]


def test_a_sealed_cell_is_never_blocked_by_tuning_read_overlap(world: World) -> None:
    world.measurement = _cross_flight_measurement(
        tuning_roster="SLURP-STAGE3-FOLD-A-V1", read_roster="SLURP-STAGE3-FOLD-A-V1"
    )
    world.rows[RUN] = _row(RUN, DRAFT)
    world.build()
    (world.data / "runs" / RUN / "attempt-x").mkdir(parents=True)
    data = world.run(cells=[EXPERIMENT])
    cell = data["cells"][0]
    assert cell["severity"] == "advisory"
    assert cell["consumed_by"] == f"runs/{RUN}"
    assert "tuning-read-overlap" in _kinds(data)
    assert data["passed"]
    assert data["blocking_cells"] == []


def test_roster_receipts_are_read_at_most_once_per_run(world: World, monkeypatch) -> None:
    # 2026-09-28 performance regression: the overlap check queries a roster id once per cell that
    # declares it, so two cells sharing the same tuning/read rosters must still open each receipt
    # file only once for the whole run, not once per cell -- the redundant re-read this fix closes.
    measurement = _cross_flight_measurement(
        tuning_roster="SLURP-TUNE-POOL-V1", read_roster="SLURP-READ-FOLD-A-V1"
    )
    world.measurement = measurement
    world.build()
    world.write_roster_receipt(
        "SLURP-TUNE-POOL-V1",
        disjointness_proof={"slurp-read-fold-a-v1": {"shared_recordings": 0, "shared_utterances": 0}},
    )
    world.write_roster_receipt("SLURP-READ-FOLD-A-V1")

    smoke_path = world.repo / "configs" / "experiment" / f"{SMOKE}.json"
    smoke_fragment = json.loads(smoke_path.read_text(encoding="utf-8"))
    smoke_fragment["stage3_measurement"] = measurement
    _write(smoke_path, smoke_fragment)

    rosters_dir = world.repo / "docs" / "receipts" / "rosters"
    reads: list[str] = []
    real_read_text = Path.read_text

    def counting_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.parent == rosters_dir:
            reads.append(str(self))
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)
    data = world.run()
    assert data["mode"] == "tree"
    assert "tuning-read-overlap" not in _kinds(data)  # zero-overlap receipts: disjoint, not blocked
    assert len(reads) == len(set(reads)) == 2, reads


def test_a_cell_without_roster_fields_triggers_no_receipt_read(world: World, monkeypatch) -> None:
    world.measurement = _cross_flight_measurement()  # no tuning_roster / read_roster at all
    world.build()
    world.write_roster_receipt("SOME-UNRELATED-ROSTER-V1")  # present, but must never be opened

    rosters_dir = world.repo / "docs" / "receipts" / "rosters"
    reads: list[str] = []
    real_read_text = Path.read_text

    def counting_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.parent == rosters_dir:
            reads.append(str(self))
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)
    data = world.run(cells=[EXPERIMENT])
    assert "tuning-roster-missing" in _kinds(data)
    assert reads == []


def test_tree_mode_skips_the_roster_check_for_an_unnamed_flown_cell(world: World) -> None:
    # a NAMED sealed cell (a launch-mode resume step) still gets the check -- see
    # test_a_sealed_cell_is_never_blocked_by_tuning_read_overlap. An unnamed one, reached only by
    # tree-mode bulk iteration, never blocks either way, so the expensive check is skipped for it.
    world.measurement = _cross_flight_measurement(
        tuning_roster="SLURP-STAGE3-FOLD-A-V1", read_roster="SLURP-STAGE3-FOLD-A-V1"
    )
    world.build()
    (world.data / "runs" / RUN / "attempt-x").mkdir(parents=True)
    data = world.run()
    cell = next(c for c in data["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["consumed_by"] == f"runs/{RUN}"
    assert cell["named"] is False
    assert "tuning-read-overlap" not in _kinds(data)
    assert cell.get("roster_split") is None


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


def test_resume_replay_proof_is_read_from_the_recovery_package_that_registers_the_cell(
    world: World,
) -> None:
    """A resume flies under the ARM's run id, so the arm's ledger row resolves the arm's ORIGINAL
    package; the resume cell's own registered plan (carrying the proof) lives in a separate recovery
    package (COMP-1: the -resume-v1 package beside the never-edited parent). The block is found
    there by run id AND cell id."""

    world.resume_from = RESUME_FROM
    world.build()
    _write(world.repo / "docs" / "readiness" / f"{PACKAGE}-resume-v1" / "generation-plan-registered-v1.json",
           {"run_id": RUN, "cell": EXPERIMENT, "resume_replay_proof": CLEAN_PROOF})
    launch = world.run(cells=[EXPERIMENT])
    assert launch["passed"]
    cell = next(c for c in launch["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["package"] == f"docs/readiness/{PACKAGE}"
    assert cell["resume_replay_proof"] == CLEAN_PROOF
    assert "resume-replay-unproven" not in _kinds(launch)


def test_a_recovery_package_for_another_cell_does_not_prove_this_resume(world: World) -> None:
    world.resume_from = RESUME_FROM
    world.build()
    _write(world.repo / "docs" / "readiness" / f"{PACKAGE}-resume-v1" / "generation-plan-registered-v1.json",
           {"run_id": RUN, "cell": "some-other-cell", "resume_replay_proof": CLEAN_PROOF})
    launch = world.run(cells=[EXPERIMENT])
    assert not launch["passed"]
    assert "resume-replay-unproven" in _kinds(launch)


# --------------------------------------------------------------------------
# key-source-unpinned (2026-09-30, the key_source Perception-branch axis)
# --------------------------------------------------------------------------


def _key_source_branches(world: World, *, write: bool = True, sha: str | None = None,
                         pin: dict | None = "default") -> dict:
    block = _three_branches(level=2)
    b = block["branches"][0]
    del b["overrides"]
    relpath = "prepared/SAEA-SLURP-CENTRED-CENTROID-KEY-V1/key-v1.jsonl"
    if write:
        (world.data / relpath).parent.mkdir(parents=True, exist_ok=True)
        (world.data / relpath).write_text("{}\n", encoding="utf-8")
    actual = hashlib.sha256(b"{}\n").hexdigest()
    facet = {
        "kind": "sealed-vectors", "relpath": relpath, "sha256": sha or actual,
        "tool_contact_ledger_row": "SAEA-SLURP-CENTRED-CENTROID-KEY-BUILD-V1",
        "embedded_signal": "text: centred centroid key",
    }
    if pin != "default":
        facet = pin
    b["key_source"] = {"store_id": "intent-boundaries", "facet_source": facet,
                       "query_source": None, "agreement_source": None}
    return block


def _perception_variant_measurement() -> dict:
    return {"measurement_design": "same-flight-perception-variant", "expected_effect_pp": 1.0,
            "claim": "nominated", "aa_arm_id": "T"}


def test_a_pinned_present_key_source_raises_no_finding(world: World) -> None:
    world.measurement = _perception_variant_measurement()
    world.perception_branches = _key_source_branches(world)
    assert "key-source-unpinned" not in _kinds(world.build().run(cells=[EXPERIMENT]))


def test_key_source_unpinned_when_the_file_is_missing(world: World) -> None:
    world.measurement = _perception_variant_measurement()
    world.perception_branches = _key_source_branches(world, write=False)
    data = world.build().run(cells=[EXPERIMENT])
    assert "key-source-unpinned" in _kinds(data)


def test_key_source_unpinned_when_the_sha_does_not_match(world: World) -> None:
    world.measurement = _perception_variant_measurement()
    world.perception_branches = _key_source_branches(world, sha="c" * 64)
    assert "key-source-unpinned" in _kinds(world.build().run(cells=[EXPERIMENT]))


@pytest.mark.parametrize("bad", [
    {"relpath": "prepared/x.jsonl"},
    {"relpath": "prepared/x.jsonl", "sha256": "not-hex"},
    {"relpath": "", "sha256": "b" * 64},
    "prepared/x.jsonl",
])
def test_key_source_unpinned_when_the_pin_is_malformed(world: World, bad) -> None:
    world.measurement = _perception_variant_measurement()
    world.perception_branches = _key_source_branches(world, pin=bad)
    assert "key-source-unpinned" in _kinds(world.build().run(cells=[EXPERIMENT]))


def test_key_source_pin_problems_names_a_zero_swap_and_a_bad_shape() -> None:
    assert gate._key_source_pin_problems(
        {"store_id": "s", "facet_source": None, "query_source": None, "agreement_source": None}, None,
    ) == ["swaps zero retrieval-key pins"]
    assert gate._key_source_pin_problems({"facet_source": None}, None)


# A successor attempt cannot inherit the historical waiver of its predecessor.
RECOVERY_ATTEMPT = "attempt-proof-fold-a-generation-recovery1-v1"


def _declare_recovery(world: World) -> None:
    path = world.repo / "configs/experiment" / f"{EXPERIMENT}.json"
    fragment = json.loads(path.read_text())
    fragment["cells"][0]["attempt_id"] = RECOVERY_ATTEMPT
    _write(path, fragment)


@pytest.mark.parametrize("old_evidence", ["run", "attempt", "prepared", "ledger"])
@pytest.mark.parametrize("state", ["ready", "held"])
def test_successor_attempt_does_not_inherit_run_level_history(
    world: World, old_evidence: str, state: str,
) -> None:
    world.states[EXPERIMENT] = state
    world.rows[RUN] = _row(RUN, DRAFT, consumed="yes" if old_evidence == "ledger" else "no")
    world.build()
    _declare_recovery(world)
    if old_evidence == "run":
        _write(world.data / "runs" / RUN / "attempt-original/session-attach.json", {})
    elif old_evidence == "attempt":
        _write(world.data / "attempts" / RUN / "attempt-original.json", {"state": "OPENED"})
    elif old_evidence == "prepared":
        _write(world.data / "prepared" / RUN / "attempt-original/fit.json", {})
    report = world.run(cells=[EXPERIMENT])
    cell = report["cells"][0]
    assert cell["consumed_by"] is None
    assert cell["severity"] == "blocking"
    assert not report["passed"]
    assert "row-not-countersigned" in _kinds(report)
    if state == "held":
        assert "not-ready" in _kinds(report)
    tree = world.run(include_held=True)
    entry = next(c for c in tree["cells"] if c["cell_id"] == EXPERIMENT)
    assert entry["consumed_by"] is None
    assert entry["severity"] == ("advisory" if state == "held" else "blocking")


@pytest.mark.parametrize("own_evidence", ["attempt", "run", "prepared"])
def test_exact_attempt_evidence_still_receives_historical_reporting(
    world: World, own_evidence: str,
) -> None:
    world.rows[RUN] = _row(RUN, DRAFT)
    world.build()
    _declare_recovery(world)
    if own_evidence == "attempt":
        relpath = f"attempts/{RUN}/{RECOVERY_ATTEMPT}.json"
        _write(world.data / relpath, {"run_id": RUN, "attempt_id": RECOVERY_ATTEMPT, "state": "OPENED"})
    else:
        relpath = f"{('runs' if own_evidence == 'run' else 'prepared')}/{RUN}/{RECOVERY_ATTEMPT}"
        _write(world.data / relpath / "receipt.json", {})
    report = world.run(cells=[EXPERIMENT])
    assert report["passed"]
    assert report["cells"][0]["consumed_by"] == relpath
    assert "row-not-countersigned" in _kinds(report)


def test_registered_successor_is_checked_and_can_pass_without_historical_waiver(world: World) -> None:
    world.build()
    _declare_recovery(world)
    _write(world.data / "runs" / RUN / "attempt-original/session-attach.json", {})
    report = world.run(cells=[EXPERIMENT])
    assert report["passed"]
    assert report["cells"][0]["consumed_by"] is None
    assert report["cells"][0]["severity"] == "blocking"


@pytest.mark.parametrize("payload", ["not json", {}, {"run_id": "ANOTHER", "attempt_id": RECOVERY_ATTEMPT}])
def test_malformed_or_mismatched_attempt_record_never_grants_history(world: World, payload) -> None:
    world.build()
    _declare_recovery(world)
    _write(world.data / "attempts" / RUN / f"{RECOVERY_ATTEMPT}.json", payload)
    with pytest.raises(gate.FlightRegistrationCheckError, match="attempt"):
        world.run(cells=[EXPERIMENT])


@pytest.mark.parametrize("attempt", ["", "../elsewhere", "/absolute", 123])
def test_invalid_attempt_identity_cannot_select_historical_artifacts(world: World, attempt) -> None:
    world.build()
    path = world.repo / "configs/experiment" / f"{EXPERIMENT}.json"
    fragment = json.loads(path.read_text())
    fragment["cells"][0]["attempt_id"] = attempt
    _write(path, fragment)
    with pytest.raises(gate.FlightRegistrationCheckError, match="attempt"):
        world.run(cells=[EXPERIMENT])


@pytest.mark.parametrize("run_id", [RUN, FIT])
@pytest.mark.parametrize("caption,valid", [
    ("slurp existing UPDATE2 first20", True),
    ("slurp, TRAIN (discovery)", True),
    ("SLURP existing UPDATE2 first20", False),
    ("slurp-extra TRAIN", False),
    ("prefix-slurp TRAIN", False),
    ("earnings21-original TRAIN", False),
    ("slurp; slurp TRAIN", False),
    ("-", False),
])
def test_declared_carrier_token_is_checked_before_runtime(world, run_id, caption, valid):
    world.rows[run_id]["speech carrier + split"] = caption
    world.build()
    filename = "generation-plan-registered-v1.json" if run_id == RUN else "fit-plan-registered-v1.json"
    _write(world.repo / "docs/readiness" / PACKAGE / filename,
           {"execution_plan": {"run_id": run_id, "carrier_lock_key": "slurp"}})
    result = world.run(cells=[EXPERIMENT])
    assert ("registered-carrier-binding" in _kinds(result)) is not valid
    assert result["passed"] is valid


@pytest.mark.parametrize("carrier", [None, "", " slurp ", 7, ["slurp"]])
def test_declared_carrier_must_be_one_nonempty_string(world, carrier):
    world.rows[RUN]["speech carrier + split"] = "slurp TRAIN"
    world.build()
    _write(world.repo / "docs/readiness" / PACKAGE / "generation-plan-registered-v1.json",
           {"execution_plan": {"run_id": RUN, "carrier_lock_key": carrier}})
    result = world.run(cells=[EXPERIMENT])
    assert not result["passed"]
    assert "registered-carrier-binding" in _kinds(result)


def test_carrier_caption_does_not_change_legacy_report_only_status(world):
    world.rows[RUN]["speech carrier + split"] = "SLURP historical caption"
    world.rows[RUN]["consumed"] = "yes"
    world.build()
    _write(world.repo / "docs/readiness" / PACKAGE / "generation-plan-registered-v1.json",
           {"execution_plan": {"run_id": RUN, "carrier_lock_key": "slurp"}})
    result = world.run(cells=[EXPERIMENT])
    assert "registered-carrier-binding" in _kinds(result)
    assert result["passed"]


@pytest.mark.parametrize("carrier", ["slurp", "audio2tool", "earnings21-original", "earnings22-original"])
def test_declared_carrier_binding_is_carrier_independent(world, carrier):
    world.rows[RUN]["speech carrier + split"] = carrier + " (discovery)"
    world.build()
    _write(world.repo / "docs/readiness" / PACKAGE / "generation-plan-registered-v1.json",
           {"execution_plan": {"run_id": RUN, "carrier_lock_key": carrier}})
    assert world.run(cells=[EXPERIMENT])["passed"]


def test_missing_carrier_row_retains_the_original_missing_row_finding(world):
    del world.rows[RUN]
    world.build()
    _write(world.repo / "docs/readiness" / PACKAGE / "generation-plan-registered-v1.json",
           {"execution_plan": {"run_id": RUN, "carrier_lock_key": "slurp"}})
    result = world.run(cells=[EXPERIMENT])
    assert not result["passed"] and "missing-row" in _kinds(result)
    assert "registered-carrier-binding" not in _kinds(result)


# A zero-contact context READ must be runnable under the existing offline reader.
def _context_read_scope(world):
    world.recipe["schema"] = "saea-context-learning-analysis-v1"
    world.rows[READ].update({
        "execution profile": "model-free-check", "split role": "discovery", "calls": "0",
        "artifacts": f"docs/readiness/{PACKAGE}/analysis-recipe-v1.json",
    })


def test_context_read_scope_allows_unsigned_zero_contact_discovery(world):
    _context_read_scope(world)
    result = world.build().run(cells=[EXPERIMENT])
    assert result["passed"]
    assert result["cells"][0]["read_row_countersigned"] is False


@pytest.mark.parametrize("field,value", [
    ("execution profile", "bounded-discovery-probe"),
    ("execution profile", "baseline-reproduction"),
    ("execution profile", "paper-scale-confirmatory"),
    ("execution profile", None),
    ("split role", "dev"),
    ("split role", "construction"),
    ("split role", "final-report"),
    ("split role", None),
    ("calls", "1"),
    ("calls", "0.0"),
    ("calls", None),
    ("artifacts", "docs/readiness/another/analysis-recipe-v1.json"),
])
def test_context_read_scope_rejected_before_runtime(world, field, value):
    _context_read_scope(world)
    if value is None:
        world.rows[READ].pop(field)
    else:
        world.rows[READ][field] = value
    result = world.build().run(cells=[EXPERIMENT])
    assert not result["passed"]
    assert "context-read-scope" in _kinds(result)


def test_context_read_scope_rejects_duplicate_read_registration(world):
    _context_read_scope(world)
    world.build()
    path = world.repo / gate.EXPOSURE_LEDGER
    path.write_text(_ledger_text([*world.rows.values(), dict(world.rows[READ])]))
    result = world.run(cells=[EXPERIMENT])
    assert not result["passed"]
    assert "context-read-row-duplicate" in _kinds(result)


def test_context_read_scope_preserves_historical_report_only_behavior(world):
    _context_read_scope(world)
    world.rows[READ]["execution profile"] = "bounded-discovery-probe"
    world.build()
    _write(world.data / "runs" / RUN / "historical.json", {})
    result = world.run(cells=[EXPERIMENT])
    assert result["passed"]
    assert "context-read-scope" in _kinds(result)


def test_context_read_scope_does_not_reinterpret_other_recipe_schemas(world):
    # The synthetic legacy recipe does not declare the context reader contract.
    result = world.build().run(cells=[EXPERIMENT])
    assert result["passed"]
    assert "context-read-scope" not in _kinds(result)


# --------------------------------------------------------------------------
# Node-template column registration (NX programme instrument E1): aa-arm-missing,
# variant-cost-mismatch, variant-claim-not-nominated, template-summary-mismatch
# --------------------------------------------------------------------------


def _template_arms(*, candidates: int = 2, twin_id: str | None = "aa") -> dict:
    arms = [
        {"arm_id": f"t{i}", "instruction_template": {"relpath": f"configs/probes/nx/t{i}.txt", "sha256": "a" * 64},
         "template_tokens": 400}
        for i in range(1, candidates + 1)
    ]
    if twin_id is not None:
        arms.append({"arm_id": twin_id, "replicate_of": "lock"})
    arms.append({"arm_id": "lock", "deliver": True, "template_tokens": 380})
    return {"node": "solver", "arms": arms, "max_supplied_items": 48, "fit_estimate": {}}


def _node_column_measurement(*, candidates: int = 2, twin: bool = True, **over: object) -> dict:
    block = {
        "measurement_design": "same-flight-node-column",
        "expected_effect_pp": 2.0,
        "primary_metric_key": "slu",
        "claim": "nominated",
        "aa_arm_id": "aa",
        "template_variants": {"node": "solver", "candidate_arms": candidates, "twin": twin},
        "variant_cost": {"extra_contacts_per_row": candidates + (1 if twin else 0), "extra_audio_seconds": 100.0},
    }
    block.update(over)
    return block


def test_a_well_formed_node_column_cell_passes_and_records_fields(world: World) -> None:
    world.measurement = _node_column_measurement()
    world.template_variants = _template_arms()
    data = world.build().run(cells=[EXPERIMENT])
    kinds = _kinds(data)
    for kind in ("aa-arm-missing", "variant-cost-mismatch", "variant-claim-not-nominated", "template-summary-mismatch"):
        assert kind not in kinds
    cell = next(c for c in data["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["node_column"]["arms"] == 4
    assert cell["node_column"]["candidate_arms"] == 2
    assert cell["node_column"]["twin"] == "aa"


def test_node_column_aa_arm_missing_without_a_twin_or_with_a_disagreeing_id(world: World) -> None:
    world.measurement = _node_column_measurement(twin=False)
    world.template_variants = _template_arms(twin_id=None)
    assert "aa-arm-missing" in _kinds(world.build().run(cells=[EXPERIMENT]))

    world.measurement = _node_column_measurement(aa_arm_id="not-the-twin")
    world.template_variants = _template_arms()
    assert "aa-arm-missing" in _kinds(world.build().run(cells=[EXPERIMENT]))


def test_node_column_variant_cost_must_match_the_arm_list(world: World) -> None:
    world.template_variants = _template_arms()
    world.measurement = _node_column_measurement(variant_cost={"extra_contacts_per_row": 5, "extra_audio_seconds": 10.0})
    assert "variant-cost-mismatch" in _kinds(world.build().run(cells=[EXPERIMENT]))

    world.measurement = _node_column_measurement(variant_cost={"extra_contacts_per_row": 3, "extra_audio_seconds": 0})
    assert "variant-cost-mismatch" in _kinds(world.build().run(cells=[EXPERIMENT]))

    world.measurement = _node_column_measurement()
    del world.measurement["variant_cost"]
    assert "variant-cost-mismatch" in _kinds(world.build().run(cells=[EXPERIMENT]))


def test_node_column_claim_is_capped_at_nominated(world: World) -> None:
    world.template_variants = _template_arms()
    world.measurement = _node_column_measurement(claim="admitted")
    assert "variant-claim-not-nominated" in _kinds(world.build().run(cells=[EXPERIMENT]))

    del world.measurement["claim"]
    assert "variant-claim-not-nominated" in _kinds(world.build().run(cells=[EXPERIMENT]))


def test_node_column_summary_must_agree_with_the_arm_list(world: World) -> None:
    world.template_variants = _template_arms(candidates=2)
    world.measurement = _node_column_measurement(
        template_variants={"node": "solver", "candidate_arms": 5, "twin": True})
    assert "template-summary-mismatch" in _kinds(world.build().run(cells=[EXPERIMENT]))


def test_a_design_outside_the_node_column_skips_the_node_checks(world: World) -> None:
    world.measurement = {
        "measurement_design": "cross-flight-with-in-chain-replicate",
        "expected_effect_pp": 5.0,
        "replicate_run_id": "SAEA-SLURP-STAGE3-SOME-REPLICATE-V1",
    }
    world.template_variants = _template_arms(twin_id=None)
    kinds = _kinds(world.build().run(cells=[EXPERIMENT]))
    for kind in ("aa-arm-missing", "template-summary-mismatch"):
        assert kind not in kinds


# ---- engineering-base cleanup 2026-10-09: placeholder supply pins and completed tokenizer-only spends ----


@pytest.mark.parametrize("declared, expected, agree", [
    # a pre-flip plan: the artifact path with an explicit placeholder hash and a provenance note
    ({"relpath": "prepared/a/phase-supply-v1.json", "sha256": "0" * 64, "note": "minted at the flip"},
     {"relpath": "prepared/a/phase-supply-v1.json", "sha256": "a" * 64}, True),
    ({"relpath": "prepared/a/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP"},
     {"relpath": "prepared/a/phase-supply-v1.json", "sha256": "a" * 64}, True),
    # annotation-only members never identify a pin
    ({"relpath": "prepared/a/phase-supply-v1.json", "sha256": "a" * 64, "output_sha256": "b" * 64, "note": "n"},
     {"relpath": "prepared/a/phase-supply-v1.json", "sha256": "a" * 64}, True),
    # a real, different hash is still a disagreement
    ({"relpath": "prepared/a/phase-supply-v1.json", "sha256": "c" * 64},
     {"relpath": "prepared/a/phase-supply-v1.json", "sha256": "a" * 64}, False),
    # a placeholder never excuses another path (a sibling member, or a different supply version)
    ({"relpath": "prepared/b/phase-supply-v1.json", "sha256": "0" * 64},
     {"relpath": "prepared/a/phase-supply-v1.json", "sha256": "a" * 64}, False),
    ({"relpath": "prepared/a/phase-supply-v2.json", "sha256": "MINTED_AT_THE_FLIP"},
     {"relpath": "prepared/a/phase-supply-v1.json", "sha256": "a" * 64}, False),
    # non-mapping declarations fall back to plain equality
    ("x", "x", True),
    ("x", {"relpath": "r"}, False),
])
def test_supply_pin_comparison_treats_placeholders_and_notes_as_unminted(declared, expected, agree):
    assert gate._supply_pins_agree(declared, expected) is agree


def _with_attempt(world: World, attempt: str = "attempt-proof-v1") -> None:
    path = world.repo / "configs" / "experiment" / f"{EXPERIMENT}.json"
    fragment = json.loads(path.read_text(encoding="utf-8"))
    fragment["cells"][0]["attempt_id"] = attempt
    _write(path, fragment)


def test_tree_mode_treats_a_completed_ledger_spend_without_an_attempt_record_as_historical(world: World) -> None:
    """Tokenizer-only capacity spends leave no attempts/ record; the ledger row is their evidence."""

    world.rows[RUN] = _row(RUN, "Zero generation. Completed 3 endpoints; no generation.", consumed="yes")
    world.build()
    _with_attempt(world)
    tree = world.run()
    cell = next(c for c in tree["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["severity"] == "advisory" and cell["consumed_by"].startswith("ledger consumed=yes + ")
    assert EXPERIMENT not in tree["blocking_cells"]
    # a named (launch-mode) cell is always gated in full, whatever the ledger says
    launch = world.run(cells=[f"{EXPERIMENT}:{EXPERIMENT}"])
    assert next(c for c in launch["cells"] if c["cell_id"] == EXPERIMENT)["consumed_by"] is None


def test_a_consumed_row_without_a_recorded_completion_does_not_waive_the_cell(world: World) -> None:
    world.rows[RUN] = _row(RUN, DRAFT, consumed="yes")
    world.build()
    _with_attempt(world)
    cell = next(c for c in world.run()["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["consumed_by"] is None


def test_a_second_attempt_sharing_the_run_id_never_inherits_the_ledger_waiver(world: World) -> None:
    world.rows[RUN] = _row(RUN, "Zero generation. COMPLETED: 9 endpoints.", consumed="yes")
    world.build()
    _with_attempt(world)
    twin = world.repo / "configs" / "experiment" / "twin-attempt.json"
    fragment = json.loads((world.repo / "configs" / "experiment" / f"{EXPERIMENT}.json").read_text(encoding="utf-8"))
    fragment["cells"][0].update(cell_id="twin-attempt", attempt_id="attempt-proof-v2")
    _write(twin, fragment)
    cell = next(c for c in world.run()["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["consumed_by"] is None
