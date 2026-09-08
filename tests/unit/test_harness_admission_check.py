"""``scripts/checks/harness_admission_check.py``: the admission gate's gate.

The check must PASS on the committed receipt and, more importantly, FAIL on
each defect it exists to catch -- a switch that names no table, a key that
names no entry of its table, an OFF arm that is not the table's null arm, a
``proof`` that names a test nobody wrote, an admitted module that reaches no
default plan, a harmful module armed in one, and a provisionally-admitted
module armed in one before its obligation is met. Every negative control is a
synthetic receipt; the committed one is never mutated.

Loaded via ``importlib.util`` for the reason the other check tests give:
``scripts/`` carries no ``__init__.py`` and is not part of the package.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_PATH = REPO_ROOT / "scripts" / "checks" / "harness_admission_check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("harness_admission_check", CHECK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hac = _load_module()

PROOF = (
    "tests/unit/test_config_table_module_switches.py"
    "::test_repair_alignment_is_one_key_in_the_judges_table"
)


def _committed() -> dict:
    return json.loads(
        (REPO_ROOT / hac.RECEIPT_RELPATH).read_text(encoding="utf-8")
    )


def _entry(**overrides) -> dict:
    entry = {
        "carrier": "slurp",
        "evidence": {"primary": "a sealed contrast"},
        "module": "a module",
        "row": "SAEA-ROW-1",
        "status": "ADMITTED",
        "switch": {
            "key": "judges.<phase>.judges",
            "off": None,
            "on": ["slurp-legal-label-flag-v1"],
            "proof": PROOF,
            "table": "judges",
        },
    }
    entry.update(overrides)
    return entry


def _receipt(entries, plans=None) -> dict:
    return {
        "default_plans": plans or [],
        "entries": entries,
        "gate": "the design note's section 8 gate",
        "schema": hac.EXPECTED_SCHEMA,
        "status_values": {
            "ADMITTED": "gain",
            "HARMFUL": "a guard fails",
            "NEUTRAL": "no harm, no gain",
            "PENDING": "registered, not decided",
        },
        "switch_rule": "one config key",
    }


def _run(tmp_path, document):
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return hac.evaluate(REPO_ROOT, path)


def _plan(tmp_path, relpath, fragment):
    """Write one default-plan fragment into a synthetic repo root, and seed
    the proof test the switch declaration names, so the plan rules are what
    these cases actually measure."""

    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fragment), encoding="utf-8")
    proof_relpath, _, proof_name = PROOF.partition("::")
    proof = tmp_path / proof_relpath
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(f"def {proof_name}():\n    pass\n", encoding="utf-8")
    return relpath


# ---------------------------------------------------------------------------
# The committed receipt
# ---------------------------------------------------------------------------


def test_the_committed_receipt_passes():
    result = hac.evaluate(REPO_ROOT)
    assert result["failures"] == []
    assert result["passed"] is True


def test_the_committed_receipts_only_module_is_barred_from_every_plan():
    """Its verdict note fixed the consequence before the verdict was known:
    an UNMET replication obligation means no entry into the default plan."""

    (row,) = hac.evaluate(REPO_ROOT)["entries"]
    assert row["blocked"] is True
    assert row["blocked_reason"] == "provisional obligation UNMET"
    assert row["in_default_plans"] == []


def test_the_committed_receipts_switch_names_a_real_table_key_and_a_real_test():
    entry = _committed()["entries"][0]
    assert entry["switch"]["table"] in hac.CONFIG_TABLE_NAMES
    assert hac.resolve_switch_key(entry["switch"]["table"], entry["switch"]["key"]) == "judges"
    relpath, _, name = entry["switch"]["proof"].partition("::")
    assert f"def {name}(" in (REPO_ROOT / relpath).read_text(encoding="utf-8")


def test_the_main_entry_point_returns_zero_on_the_committed_receipt(capsys):
    assert hac.main([]) == 0
    assert "PASS" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Rule 1: the switch resolves in a table
# ---------------------------------------------------------------------------


def test_a_missing_switch_fails(tmp_path):
    entry = _entry()
    del entry["switch"]
    result = _run(tmp_path, _receipt([entry]))
    assert any("missing ['switch']" in failure for failure in result["failures"])


def test_a_switch_naming_no_config_table_fails(tmp_path):
    entry = _entry()
    entry["switch"]["table"] = "modes"
    result = _run(tmp_path, _receipt([entry]))
    assert any("the config tables are" in failure for failure in result["failures"])


def test_a_key_that_names_no_entry_of_its_table_fails(tmp_path):
    entry = _entry()
    entry["switch"]["key"] = "judges.<phase>.verdicts"
    result = _run(tmp_path, _receipt([entry]))
    assert any("names no entry of the" in failure for failure in result["failures"])


def test_a_key_that_does_not_start_with_its_table_fails(tmp_path):
    entry = _entry()
    entry["switch"]["key"] = "phase_review.<phase>.judges"
    result = _run(tmp_path, _receipt([entry]))
    assert any("does not start with its table" in failure for failure in result["failures"])


def test_an_off_arm_that_is_not_the_tables_null_arm_fails(tmp_path):
    entry = _entry()
    entry["switch"]["off"] = []
    result = _run(tmp_path, _receipt([entry]))
    assert any("third cell identity" in failure for failure in result["failures"])


def test_an_on_arm_that_is_the_null_arm_fails(tmp_path):
    entry = _entry()
    entry["switch"]["on"] = None
    result = _run(tmp_path, _receipt([entry]))
    assert any("must arm something" in failure for failure in result["failures"])


def test_a_proof_naming_a_test_nobody_wrote_fails(tmp_path):
    entry = _entry()
    entry["switch"]["proof"] = (
        "tests/unit/test_config_table_module_switches.py::test_wishful_thinking"
    )
    result = _run(tmp_path, _receipt([entry]))
    assert any("does not define" in failure for failure in result["failures"])


def test_a_proof_naming_a_file_that_does_not_exist_fails(tmp_path):
    entry = _entry()
    entry["switch"]["proof"] = "tests/unit/test_nothing.py::test_x"
    result = _run(tmp_path, _receipt([entry]))
    assert any("which does not exist" in failure for failure in result["failures"])


def test_a_proof_that_is_not_a_node_id_fails(tmp_path):
    entry = _entry()
    entry["switch"]["proof"] = "somebody checked it"
    result = _run(tmp_path, _receipt([entry]))
    assert any("node id" in failure for failure in result["failures"])


# ---------------------------------------------------------------------------
# Rule 2: an admitted or neutral module reaches a default plan
# ---------------------------------------------------------------------------


def test_an_admitted_module_with_no_default_plan_fails(tmp_path):
    result = _run(tmp_path, _receipt([_entry()]))
    assert any("no default plan for" in failure for failure in result["failures"])


def test_an_admitted_module_armed_in_a_default_plan_passes(tmp_path):
    relpath = _plan(
        tmp_path,
        "configs/baseline/plan.json",
        {"policy": "phase-direct-only-v1", "judges": {"direct": {"judges": ["x"]}}},
    )
    result = hac.evaluate(
        tmp_path,
        _write(tmp_path, _receipt([_entry()], [{"carrier": "slurp", "config": relpath}])),
    )
    assert result["failures"] == []
    assert result["entries"][0]["in_default_plans"] == [relpath]


def test_a_plan_that_declares_the_tables_null_arm_does_not_arm_the_module(tmp_path):
    relpath = _plan(tmp_path, "configs/baseline/plan.json", {"judges": None})
    result = hac.evaluate(
        tmp_path,
        _write(tmp_path, _receipt([_entry()], [{"carrier": "slurp", "config": relpath}])),
    )
    assert any("no default plan for" in failure for failure in result["failures"])


def test_a_plan_for_another_carrier_does_not_count(tmp_path):
    relpath = _plan(
        tmp_path, "configs/baseline/plan.json", {"judges": {"direct": {"judges": ["x"]}}}
    )
    result = hac.evaluate(
        tmp_path,
        _write(
            tmp_path,
            _receipt([_entry()], [{"carrier": "earnings21-original", "config": relpath}]),
        ),
    )
    assert any("no default plan for" in failure for failure in result["failures"])


def test_a_pending_module_is_neither_required_nor_barred(tmp_path):
    result = _run(tmp_path, _receipt([_entry(status="PENDING")]))
    assert result["failures"] == []


def test_a_default_plan_naming_a_missing_file_fails(tmp_path):
    result = _run(
        tmp_path,
        _receipt([_entry(status="PENDING")], [{"carrier": "slurp", "config": "configs/x.json"}]),
    )
    assert any("does not exist" in failure for failure in result["failures"])


# ---------------------------------------------------------------------------
# Rule 3: a harmful or unmet-provisional module never enters a plan
# ---------------------------------------------------------------------------


def test_a_harmful_module_armed_in_a_default_plan_fails(tmp_path):
    relpath = _plan(
        tmp_path, "configs/baseline/plan.json", {"judges": {"direct": {"judges": ["x"]}}}
    )
    result = hac.evaluate(
        tmp_path,
        _write(
            tmp_path,
            _receipt(
                [_entry(status="HARMFUL")], [{"carrier": "slurp", "config": relpath}]
            ),
        ),
    )
    assert any("status HARMFUL, but it is armed" in failure for failure in result["failures"])


def test_a_harmful_module_absent_from_every_plan_passes(tmp_path):
    result = _run(tmp_path, _receipt([_entry(status="HARMFUL")]))
    assert result["failures"] == []


def test_a_provisionally_admitted_module_armed_in_a_plan_fails(tmp_path):
    relpath = _plan(
        tmp_path, "configs/baseline/plan.json", {"judges": {"direct": {"judges": ["x"]}}}
    )
    result = hac.evaluate(
        tmp_path,
        _write(
            tmp_path,
            _receipt(
                [_entry(provisional={"state": "UNMET", "reason": "one sample"})],
                [{"carrier": "slurp", "config": relpath}],
            ),
        ),
    )
    assert any(
        "provisional obligation UNMET, but it is armed" in failure
        for failure in result["failures"]
    )


def test_a_met_provisional_obligation_stops_blocking(tmp_path):
    relpath = _plan(
        tmp_path, "configs/baseline/plan.json", {"judges": {"direct": {"judges": ["x"]}}}
    )
    result = hac.evaluate(
        tmp_path,
        _write(
            tmp_path,
            _receipt(
                [_entry(provisional={"state": "MET", "reason": "replicated"})],
                [{"carrier": "slurp", "config": relpath}],
            ),
        ),
    )
    assert result["failures"] == []
    assert result["entries"][0]["blocked"] is False


# ---------------------------------------------------------------------------
# Receipt shape
# ---------------------------------------------------------------------------


def test_an_old_schema_fails(tmp_path):
    document = _receipt([_entry(status="PENDING")])
    document["schema"] = "saea-harness-admission-v1"
    result = _run(tmp_path, document)
    assert any("expected" in failure for failure in result["failures"])


def test_a_missing_top_level_key_fails(tmp_path):
    document = _receipt([_entry(status="PENDING")])
    del document["switch_rule"]
    result = _run(tmp_path, document)
    assert any("missing top-level key(s)" in failure for failure in result["failures"])


def test_two_entries_deciding_one_module_and_carrier_fail(tmp_path):
    result = _run(
        tmp_path,
        _receipt([_entry(status="PENDING"), _entry(status="PENDING")]),
    )
    assert any("a second entry decides" in failure for failure in result["failures"])


def test_an_unknown_status_fails(tmp_path):
    result = _run(tmp_path, _receipt([_entry(status="PROBABLY-FINE")]))
    assert any("is not one of" in failure for failure in result["failures"])


def test_an_unreadable_receipt_raises(tmp_path):
    path = tmp_path / "receipt.json"
    path.write_text("{not json", encoding="utf-8")
    try:
        hac.evaluate(REPO_ROOT, path)
    except hac.HarnessAdmissionCheckError as error:
        assert "cannot read" in str(error)
    else:  # pragma: no cover - the check must refuse
        raise AssertionError("an unreadable receipt must raise")


def test_the_committed_receipt_is_not_mutated_by_any_of_this():
    assert _committed() == copy.deepcopy(_committed())
    assert _committed()["schema"] == hac.EXPECTED_SCHEMA


def _write(root: Path, document: dict) -> Path:
    path = root / "receipt.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path
