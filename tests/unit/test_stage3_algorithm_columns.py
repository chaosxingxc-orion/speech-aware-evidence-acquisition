"""E-T5 (decision 263-A): the per-column ``columns`` key of the Stage-3 label.

A cell that flies lock / twin / parent / typed / ACE columns in one fragment
labels each column's algorithm in ``stage3_algorithm.columns`` ({arm_id:
algorithm_id}); every value must resolve in ``core.base.STAGE3_ALGORITHMS``.
Also pins the ACE record's citation (arXiv 2510.04618).

Zero model, tokenizer, encoder, network and GPU contacts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_CHECKS = REPO / "scripts" / "checks"
if str(_CHECKS) not in sys.path:
    sys.path.insert(0, str(_CHECKS))

import stage3_algorithm_label_check as gate  # noqa: E402

from speech_aware_evidence_acquisition.core import (  # noqa: E402
    stage3_algorithms as registry,
)

TYPED = "sealed-credit-system-policy-v1"
ACE = "ace-grow-refine-v1"

COLUMNS = {
    "lock": "shared-rollout",
    "aa": "shared-rollout",
    "par": TYPED,
    "typ": TYPED,
    "ace": ACE,
    "twin": "none",
}


def _label(**extra: object) -> dict:
    label = {
        "id": TYPED,
        "operators_used": ["credit_assignment", "update"],
        "note": "iteration cell with typed and ACE columns.",
    }
    label.update(extra)
    return label


def _repo(tmp_path: Path, label: dict) -> Path:
    directory = tmp_path / "configs" / "experiment"
    directory.mkdir(parents=True)
    document = {
        "experiment_id": "SAEA-SLURP-STAGE3-SYNTHETIC-V1",
        "purpose": "synthetic",
        "stage3_algorithm": label,
    }
    (directory / "slurp-native-stage3-synthetic-v1.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return tmp_path


def test_columns_is_a_known_label_key() -> None:
    assert registry.COLUMNS_KEY == "columns"
    assert "columns" in registry._KNOWN_LABEL_KEYS


def test_a_label_with_resolving_columns_validates() -> None:
    record, used = registry.validate_stage3_algorithm_label(
        _label(columns=COLUMNS), cell="synthetic"
    )
    assert record.id == TYPED
    assert used == ("credit_assignment", "update")


def test_columns_resolve_to_records() -> None:
    resolved = registry.validate_stage3_algorithm_columns(COLUMNS, cell="synthetic")
    assert resolved["ace"].id == ACE
    assert resolved["typ"].family == "sealed-credit-system-policy"
    assert resolved["twin"].id == registry.NONE_ALGORITHM_ID


def test_a_label_without_columns_is_unchanged() -> None:
    record, _ = registry.validate_stage3_algorithm_label(_label(), cell="synthetic")
    assert record.id == TYPED
    assert registry.columns_of(_label()) == {}
    assert registry.columns_of(_label(columns=COLUMNS)) == COLUMNS


def test_an_unregistered_column_algorithm_is_refused() -> None:
    with pytest.raises(registry.Stage3AlgorithmError, match=r"columns\['ace'\]"):
        registry.validate_stage3_algorithm_label(
            _label(columns={"ace": "ace-v9"}), cell="synthetic"
        )


@pytest.mark.parametrize("bad", [[], {}, "ace", {"": ACE}, {"ace": ""}, {"ace": None}])
def test_a_malformed_columns_value_is_refused(bad: object) -> None:
    with pytest.raises(registry.Stage3AlgorithmError):
        registry.validate_stage3_algorithm_label(_label(columns=bad), cell="synthetic")


def test_the_ace_record_cites_the_paper() -> None:
    record = registry.resolve_stage3_algorithm(ACE)
    assert "2510.04618" in record.citation
    assert "see design spec" not in record.citation
    assert record.status == "planned"


def test_the_gate_accepts_and_reports_columns(tmp_path: Path) -> None:
    data = gate.evaluate(_repo(tmp_path, _label(columns=COLUMNS)))
    assert data["passed"], data["violations"]
    row = data["stage3_cells"][0]
    assert row["algorithm_id"] == TYPED
    assert row["columns"] == COLUMNS


def test_the_gate_refuses_an_unresolved_column(tmp_path: Path) -> None:
    data = gate.evaluate(_repo(tmp_path, _label(columns={"ace": "nope"})))
    assert not data["passed"]
    assert data["violations"][0]["kind"] == "invalid-label"
    assert "columns" in data["violations"][0]["message"]


def test_the_gate_still_passes_on_the_real_repository() -> None:
    data = gate.evaluate(REPO)
    assert data["passed"], data["violations"]
