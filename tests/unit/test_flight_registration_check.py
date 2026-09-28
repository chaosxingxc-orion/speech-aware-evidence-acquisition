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
        # Same-flight instrument, PHASE 2 (merge set C): written into the EXPERIMENT
        # baseline's native_episode.roles.perception.branches, exactly where the real
        # baselines will carry it once a phase-2 fragment is minted.
        self.perception_branches: dict | None = None

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
            _write(self.repo / "configs" / "experiment" / f"{experiment}.json", fragment)
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


def _three_branches(*, level: int = 1, twin_id: str | None = "T") -> dict:
    branches = [
        {
            "branch_id": "B", "max_supplied_items": 8,
            "overrides": {
                "knowledge_stores.intent-boundaries.phase_supply.perception.k": 16
            },
        },
        {"branch_id": "A", "deliver": True, "max_supplied_items": 8},
    ]
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
    cell = next(c for c in data["cells"] if c["cell_id"] == EXPERIMENT)
    assert cell["perception_branch"]["measurement_design"] == "same-flight-perception-variant"
    assert cell["perception_branch"]["level"] == 1
    assert cell["perception_branch"]["branches"] == 3
    assert cell["perception_branch"]["aa_arm_id"] == "T"


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
