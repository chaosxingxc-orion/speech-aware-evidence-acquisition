"""The Stage-3 effect-floor gate, on synthetic repositories.

``scripts/checks/stage3_effect_floor_check.py`` refuses a preregistration whose
declared design cannot see its declared effect, under the floor table of
``docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md``. Every
finding it can raise is exercised here on a miniature repository built in a
temporary directory -- exposure ledger, experiment fragment, readiness package
-- so the rules are tested on both sides of each boundary rather than on
whatever the real tree happens to hold today. One test at the end runs the gate
against the real repository and asserts only that it terminates with a
documented exit code (0 or 1).

Zero model, tokenizer, encoder, scorer, network and GPU contacts; no
``SPEECHRL_DATA_DIR`` read.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_CHECKS = _REPO / "scripts" / "checks"
if str(_CHECKS) not in sys.path:
    sys.path.insert(0, str(_CHECKS))

import stage3_effect_floor_check as gate  # noqa: E402

RUN_ID = "SAEA-SLURP-STAGE3-FLOOR-PROOF-V1"
FRAGMENT = "slurp-native-stage3-floor-proof-v1"
CELL = "slurp-native-stage3-floor-proof-v1"
PACKAGE = "2026-09-26-slurp-stage3-floor-proof-v1"

LEDGER_COLUMNS = (
    "date",
    "run/experiment id",
    "execution profile",
    "scope",
    "model/tool",
    "speech carrier + split",
    "split role",
    "split identity hash",
    "consumed",
    "calls",
    "speech audio seconds",
    "gpu hours",
    "inherited exposure",
    "artifacts",
    "notes",
)


def _ledger(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Exposure ledger",
        "",
        "| " + " | ".join(LEDGER_COLUMNS) + " |",
        "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |",
    ]
    for row in rows:
        lines.append(
            "| " + " | ".join(str(row.get(name, "-")) for name in LEDGER_COLUMNS) + " |"
        )
    return "\n".join(lines) + "\n"


def _build(
    root: Path,
    *,
    rows: int | None = 625,
    declaration: dict | None = None,
    declaration_in: str = "registered-facts",
    registered_date: str = "2026-09-25",
    consumed: str = "no",
    readiness_state: str | None = "ready",
    with_ledger_row: bool = True,
    run_id: str = RUN_ID,
) -> None:
    """One synthetic repository: one fragment, one ledger row, one package."""

    (root / "configs" / "experiment").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "readiness" / PACKAGE).mkdir(parents=True, exist_ok=True)

    cell: dict = {"cell_id": CELL, "run_id": run_id, "baseline_fragment": "b"}
    if readiness_state is not None:
        cell["readiness"] = {"state": readiness_state, "reason": "synthetic"}
    fragment: dict = {
        "experiment_id": run_id,
        "date": f"{registered_date}T12:00:00+00:00",
        "cells": [cell],
    }
    if rows is not None:
        fragment["population"] = {"count": rows, "dataset_fragment": "synthetic"}
    if declaration is not None and declaration_in == "fragment":
        fragment[gate.MEASUREMENT_KEY] = declaration
    (root / "configs" / "experiment" / f"{FRAGMENT}.json").write_text(
        json.dumps(fragment, indent=2, sort_keys=True), encoding="utf-8"
    )

    if declaration is not None and declaration_in == "registered-facts":
        (root / "docs" / "readiness" / PACKAGE / "registered-facts-v1.json").write_text(
            json.dumps(
                {"_note": f"synthetic facts for {run_id}", gate.MEASUREMENT_KEY: declaration},
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    if declaration is not None and declaration_in == "preregistration":
        body = json.dumps({gate.MEASUREMENT_KEY: declaration}, indent=2, sort_keys=True)
        (root / "docs" / "readiness" / f"{PACKAGE}-preregistration.md").write_text(
            f"# Synthetic preregistration for {run_id}\n\n```json\n{body}\n```\n",
            encoding="utf-8",
        )
    if declaration is not None and declaration_in == "broken-preregistration":
        (root / "docs" / "readiness" / f"{PACKAGE}-preregistration.md").write_text(
            f"# Synthetic preregistration for {run_id}\n\n"
            f'```json\n{{"{gate.MEASUREMENT_KEY}": {{"measurement_design": }}\n```\n',
            encoding="utf-8",
        )

    ledger_rows = []
    if with_ledger_row:
        ledger_rows.append(
            {
                "date": registered_date,
                "run/experiment id": run_id,
                "execution profile": "bounded-discovery-probe",
                "consumed": consumed,
                "notes": "synthetic",
            }
        )
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "exposure-ledger.md").write_text(
        _ledger(ledger_rows), encoding="utf-8"
    )


def _declaration(**overrides) -> dict:
    block = {
        "measurement_design": "offline-sealed-pool",
        "expected_effect_pp": 1.5,
        "rows": 625,
        "primary_metric": "official SLURP pooled SLU-F1 (micro)",
        "claims_benefit": True,
        "note": "synthetic",
    }
    block.update(overrides)
    return {key: value for key, value in block.items() if value is not None}


def _kinds(data: dict) -> list[str]:
    return [finding["kind"] for finding in data["findings"]]


# --------------------------------------------------------------------------
# the arithmetic
# --------------------------------------------------------------------------


def test_floor_table_reproduces_the_notes_own_anchors() -> None:
    assert gate.floor_for("offline-sealed-pool", 625)[0] == pytest.approx(0.67)
    assert gate.floor_for("same-flight-paired", 200)[0] == pytest.approx(0.735)
    # cross-flight: the rule-3 admission bar dominates the sampling half-width
    assert gate.floor_for("cross-flight-with-in-chain-replicate", 625)[0] == pytest.approx(3.0)
    assert gate.floor_for("cross-flight-with-in-chain-replicate", 1080)[0] == pytest.approx(2.5)
    assert gate.floor_for("cross-flight-no-replicate", 625)[0] == math.inf
    assert gate.floor_for("form-proof", 4)[0] is None


def test_floors_scale_as_one_over_root_n() -> None:
    assert gate.floor_for("offline-sealed-pool", 2500)[0] == pytest.approx(0.67 / 2)
    assert gate.floor_for("same-flight-paired", 800)[0] == pytest.approx(0.735 / 2)
    floor, arithmetic = gate.floor_for("offline-sealed-pool", 1250)
    assert floor == pytest.approx(0.67 * math.sqrt(625 / 1250))
    assert "sqrt(625 / 1250)" in " ".join(arithmetic)


def test_the_nearest_anchor_in_log_n_is_used() -> None:
    # 1,000 rows is nearest its own measured anchor (1.2525), not the 625 one
    assert gate._nearest_anchor(
        gate.FLOOR_TABLE["cross-flight-with-in-chain-replicate"].sampling, 1000
    ) == (1000, 1.2525)


# --------------------------------------------------------------------------
# scope, advisory and blocking
# --------------------------------------------------------------------------


def test_a_missing_declaration_is_advisory_before_the_law_date(tmp_path: Path) -> None:
    _build(tmp_path, registered_date="2026-09-25")
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["missing-declaration"]
    assert data["findings"][0]["severity"] == "advisory"
    assert data["passed"] is True
    assert gate.main(["--repo-root", str(tmp_path)]) == 0


def test_a_missing_declaration_blocks_a_cell_registered_after_the_law(tmp_path: Path) -> None:
    _build(tmp_path, registered_date="2026-09-28")
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["missing-declaration"]
    assert data["findings"][0]["severity"] == "blocking"
    assert data["passed"] is False
    assert gate.main(["--repo-root", str(tmp_path)]) == 1


def test_strict_from_moves_the_advisory_boundary(tmp_path: Path) -> None:
    _build(tmp_path, registered_date="2026-09-25")
    data = gate.evaluate(tmp_path, strict_from=gate.dt.date(2026, 9, 1))
    assert data["findings"][0]["severity"] == "blocking"
    assert gate.main(["--repo-root", str(tmp_path), "--strict-from", "2026-09-01"]) == 1
    assert gate.main(["--repo-root", str(tmp_path), "--strict-from", "not-a-date"]) == 1


def test_an_undeclared_small_cell_is_a_form_proof_by_size(tmp_path: Path) -> None:
    _build(tmp_path, rows=4, registered_date="2026-09-28")
    data = gate.evaluate(tmp_path)
    assert data["findings"] == []
    assert data["form_proof_by_size"] == [CELL]
    assert data["passed"] is True


def test_a_consumed_cell_is_reported_and_never_a_finding(tmp_path: Path) -> None:
    _build(tmp_path, consumed="yes (625 rows read)", registered_date="2026-09-28")
    data = gate.evaluate(tmp_path)
    assert data["findings"] == []
    assert data["consumed_cells"] == [CELL]
    assert data["in_scope_cells"][0]["severity"] == "reported (already flown)"


def test_a_cell_with_no_ledger_row_is_out_of_scope(tmp_path: Path) -> None:
    _build(tmp_path, with_ledger_row=False, registered_date="2026-09-28")
    data = gate.evaluate(tmp_path)
    assert data["findings"] == []
    assert data["out_of_scope"]["no_ledger_row"] == [CELL]


@pytest.mark.parametrize("state", ["superseded", "preparation-pending", None])
def test_a_cell_that_is_not_live_is_out_of_scope(tmp_path: Path, state: str | None) -> None:
    _build(tmp_path, readiness_state=state, registered_date="2026-09-28")
    data = gate.evaluate(tmp_path)
    assert data["findings"] == []
    assert [row["cell"] for row in data["out_of_scope"]["not_live_cells"]] == [CELL]


def test_a_fragment_that_is_not_stage3_is_out_of_scope(tmp_path: Path) -> None:
    _build(tmp_path, registered_date="2026-09-28")
    source = tmp_path / "configs" / "experiment" / f"{FRAGMENT}.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    document["experiment_id"] = "SAEA-SLURP-SOMETHING-ELSE-V1"
    source.unlink()
    (tmp_path / "configs" / "experiment" / "slurp-native-something-else-v1.json").write_text(
        json.dumps(document, indent=2, sort_keys=True), encoding="utf-8"
    )
    data = gate.evaluate(tmp_path)
    assert data["findings"] == []
    assert data["out_of_scope"]["not_stage3_fragments"] == 1


# --------------------------------------------------------------------------
# the findings
# --------------------------------------------------------------------------


def test_an_effect_below_the_offline_floor_is_refused(tmp_path: Path) -> None:
    _build(
        tmp_path,
        declaration=_declaration(expected_effect_pp=0.3),
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["effect-below-floor"]
    message = data["findings"][0]["message"]
    assert "0.6700 pp" in message and "n = 625" in message
    assert data["passed"] is False


def test_an_effect_above_the_offline_floor_passes(tmp_path: Path) -> None:
    _build(
        tmp_path,
        declaration=_declaration(expected_effect_pp=0.8),
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert data["findings"] == []
    assert data["passed"] is True
    assert data["in_scope_cells"][0]["declaration"]["rows_source"] == "the declaration"


def test_cross_flight_without_a_replicate_is_refused_outright(tmp_path: Path) -> None:
    _build(
        tmp_path,
        declaration=_declaration(
            measurement_design="cross-flight-no-replicate", expected_effect_pp=25.0
        ),
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["cross-flight-no-replicate"]
    assert "rule 4" in data["findings"][0]["message"]


def test_cross_flight_with_a_replicate_must_clear_the_three_point_bar(tmp_path: Path) -> None:
    _build(
        tmp_path,
        declaration=_declaration(
            measurement_design="cross-flight-with-in-chain-replicate",
            expected_effect_pp=2.0,
            replicate_run_id="SAEA-SLURP-STAGE3-FLOOR-PROOF-REPLICATE-V1",
        ),
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["effect-below-floor"]
    assert "3.0000 pp" in data["findings"][0]["message"]


def test_cross_flight_at_3_5_pp_with_a_replicate_passes(tmp_path: Path) -> None:
    _build(
        tmp_path,
        declaration=_declaration(
            measurement_design="cross-flight-with-in-chain-replicate",
            expected_effect_pp=3.5,
            replicate_run_id="SAEA-SLURP-STAGE3-FLOOR-PROOF-REPLICATE-V1",
        ),
        registered_date="2026-09-28",
    )
    assert gate.evaluate(tmp_path)["findings"] == []


def test_cross_flight_naming_no_replicate_run_id_is_refused(tmp_path: Path) -> None:
    _build(
        tmp_path,
        declaration=_declaration(
            measurement_design="cross-flight-with-in-chain-replicate",
            expected_effect_pp=3.5,
        ),
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["missing-in-chain-replicate"]


def test_a_benefit_claim_under_200_rows_is_refused(tmp_path: Path) -> None:
    _build(
        tmp_path,
        rows=16,
        declaration=_declaration(
            measurement_design="same-flight-paired", expected_effect_pp=9.0, rows=16
        ),
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["underpowered-benefit-claim"]
    assert "rule 5" in data["findings"][0]["message"]


def test_a_form_proof_may_not_claim_a_benefit(tmp_path: Path) -> None:
    _build(
        tmp_path,
        rows=4,
        declaration=_declaration(
            measurement_design="form-proof", expected_effect_pp=5.0, rows=4
        ),
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert set(_kinds(data)) == {"form-proof-claims-benefit", "underpowered-benefit-claim"}


def test_a_form_proof_that_claims_nothing_passes(tmp_path: Path) -> None:
    _build(
        tmp_path,
        rows=4,
        declaration=_declaration(
            measurement_design="form-proof",
            expected_effect_pp=0.0,
            rows=4,
            claims_benefit=False,
        ),
        registered_date="2026-09-28",
    )
    assert gate.evaluate(tmp_path)["findings"] == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"measurement_design": "eyeball"},
        {"measurement_design": None},
        {"expected_effect_pp": "about three points"},
        {"expected_effect_pp": None},
        {"rows": 0},
        {"rows": "six hundred"},
        {"claims_benefit": "yes"},
        {"replicate_run_id": 17},
    ],
)
def test_an_unreadable_declaration_is_refused(tmp_path: Path, overrides: dict) -> None:
    # ``_declaration`` drops a key whose override is None, so "None" here means
    # "the block omits this required key".
    _build(
        tmp_path,
        rows=None,
        declaration=_declaration(**overrides),
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["unparsable-declaration"]
    assert data["passed"] is False


def test_a_declaration_that_is_not_an_object_is_refused(tmp_path: Path) -> None:
    _build(tmp_path, declaration=["offline-sealed-pool"], registered_date="2026-09-28")
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["unparsable-declaration"]
    assert "must be a JSON object" in data["findings"][0]["message"]


def test_a_json_fence_that_does_not_parse_is_refused(tmp_path: Path) -> None:
    _build(
        tmp_path,
        declaration=_declaration(),
        declaration_in="broken-preregistration",
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["unparsable-declaration"]
    assert "does not parse" in data["findings"][0]["message"]


# --------------------------------------------------------------------------
# where the declaration may live
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "where", ["registered-facts", "preregistration", "fragment"]
)
def test_the_declaration_is_read_from_each_legal_place(tmp_path: Path, where: str) -> None:
    _build(
        tmp_path,
        declaration=_declaration(expected_effect_pp=0.2),
        declaration_in=where,
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["effect-below-floor"]
    source = data["in_scope_cells"][0]["declaration"]["source"]
    assert source.endswith(".json") or source.endswith(".md")


def test_registered_facts_win_over_the_preregistration(tmp_path: Path) -> None:
    _build(
        tmp_path,
        declaration=_declaration(expected_effect_pp=0.2),
        declaration_in="registered-facts",
        registered_date="2026-09-28",
    )
    body = json.dumps(
        {gate.MEASUREMENT_KEY: _declaration(expected_effect_pp=9.0)},
        indent=2,
        sort_keys=True,
    )
    (tmp_path / "docs" / "readiness" / f"{PACKAGE}-preregistration.md").write_text(
        f"# Synthetic preregistration for {RUN_ID}\n\n```json\n{body}\n```\n",
        encoding="utf-8",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["effect-below-floor"]
    assert data["in_scope_cells"][0]["declaration"]["source"].endswith(
        "registered-facts-v1.json"
    )


def test_a_run_id_keyed_mapping_registers_a_family(tmp_path: Path) -> None:
    _build(
        tmp_path,
        declaration={
            RUN_ID: _declaration(expected_effect_pp=0.2),
            "SAEA-SLURP-STAGE3-SOMEONE-ELSE-V1": _declaration(expected_effect_pp=9.0),
        },
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["effect-below-floor"]


def test_a_keyed_mapping_that_does_not_name_the_cell_is_no_declaration(
    tmp_path: Path,
) -> None:
    _build(
        tmp_path,
        declaration={"SAEA-SLURP-STAGE3-SOMEONE-ELSE-V1": _declaration()},
        registered_date="2026-09-28",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["missing-declaration"]


def test_rows_fall_back_to_the_fragments_population_count(tmp_path: Path) -> None:
    declaration = _declaration(expected_effect_pp=0.5)
    declaration.pop("rows")
    _build(tmp_path, rows=2500, declaration=declaration, registered_date="2026-09-28")
    data = gate.evaluate(tmp_path)
    parsed = data["in_scope_cells"][0]["declaration"]
    assert parsed["rows"] == 2500
    assert parsed["rows_source"] == "the fragment's population.count"
    # 0.67 * sqrt(625 / 2500) = 0.335, so +0.5 pp clears the offline floor
    assert data["findings"] == []


def test_rows_nowhere_is_an_unreadable_declaration(tmp_path: Path) -> None:
    declaration = _declaration()
    declaration.pop("rows")
    _build(tmp_path, rows=None, declaration=declaration, registered_date="2026-09-28")
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["unparsable-declaration"]
    assert "population.count" in data["findings"][0]["message"]


# --------------------------------------------------------------------------
# the command line
# --------------------------------------------------------------------------


def test_explain_prints_the_table_and_one_cells_arithmetic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _build(
        tmp_path,
        declaration=_declaration(
            measurement_design="cross-flight-with-in-chain-replicate",
            expected_effect_pp=2.0,
            replicate_run_id="SAEA-SLURP-STAGE3-FLOOR-PROOF-REPLICATE-V1",
        ),
        registered_date="2026-09-28",
    )
    assert gate.main(["--repo-root", str(tmp_path), "--explain", CELL]) == 0
    out = capsys.readouterr().out
    assert "floor table" in out
    assert "rule-3 admission bar" in out
    assert "BELOW the floor" in out
    # the table alone, with no cell, and an unknown cell, both still exit 0
    assert gate.main(["--repo-root", str(tmp_path), "--explain"]) == 0
    assert gate.main(["--repo-root", str(tmp_path), "--explain", "no-such-cell"]) == 0
    assert "no in-scope Stage-3 cell matches" in capsys.readouterr().out


def test_json_output_carries_the_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _build(tmp_path, registered_date="2026-09-28")
    assert gate.main(["--repo-root", str(tmp_path), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["schema"] == "saea-stage3-effect-floor-check-v1"
    assert data["instrument_note"] == gate.INSTRUMENT_NOTE
    assert [finding["kind"] for finding in data["findings"]] == ["missing-declaration"]


def test_a_tree_with_no_experiment_directory_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "exposure-ledger.md").write_text(_ledger([]), encoding="utf-8")
    with pytest.raises(gate.Stage3EffectFloorCheckError):
        gate.evaluate(tmp_path)


def test_a_tree_with_no_exposure_ledger_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(gate.Stage3EffectFloorCheckError):
        gate.evaluate(tmp_path)


def test_the_real_repository_terminates_with_a_documented_exit_code() -> None:
    """The gate runs on the real tree and returns one of its two exit codes."""

    assert gate.main(["--repo-root", str(_REPO)]) in (0, 1)
