"""The Stage-3 training-free RL algorithm registry, its label, and its gate.

Owner decision 101 (2026-09-22): every Stage-3 cell carries a machine-checked
``stage3_algorithm`` label resolving in ``core.base.STAGE3_ALGORITHMS``. Three
layers are proved here: the registry's own records, the label validator, and
``scripts/checks/stage3_algorithm_label_check.py`` on a synthetic repository
(pass, missing label, unknown id, bad operator, allowlisted) plus the real
tree.

Zero model, tokenizer, encoder, network and GPU contacts; no
``SPEECHRL_DATA_DIR`` read.
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

from speech_aware_evidence_acquisition.core.base import STAGE3_ALGORITHMS  # noqa: E402
from speech_aware_evidence_acquisition.core import (  # noqa: E402
    stage3_algorithms as registry,
)

EXPECTED_IDS = {
    "ace-grow-refine-v1",
    "finite-action-bandit-v1",
    "finite-system-policy-bandit-v1",
    "gepa-reflective-pareto-v1",
    "inference-time-verification-v1",
    "none",
    "sealed-credit-system-policy-v1",
    "shared-rollout",
    "system-text-black-box-v1",
    "tfgrpo-semantic-advantage-v1",
    "tfgrpo-system-memory-disjoint-v1",
}

LABELLED_FRAGMENTS = {
    "slurp-native-stage3-rollout-r01-v1": ("shared-rollout", ["rollout"]),
    "slurp-native-stage3-rollout-r01-smoke-4-v1": ("shared-rollout", ["rollout"]),
    "slurp-native-stage3-advantage-r01-v1": (
        "tfgrpo-semantic-advantage-v1",
        ["credit_assignment"],
    ),
    "slurp-native-stage3-delta-cell-r01-v1": (
        "tfgrpo-semantic-advantage-v1",
        ["update", "context_application"],
    ),
}


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------


def test_the_registry_holds_exactly_the_registered_algorithm_families() -> None:
    assert set(registry.registered_ids()) == EXPECTED_IDS
    assert set(STAGE3_ALGORITHMS.names()) == EXPECTED_IDS


@pytest.mark.parametrize("algorithm_id", sorted(EXPECTED_IDS))
def test_every_record_is_well_formed(algorithm_id: str) -> None:
    record = registry.resolve_stage3_algorithm(algorithm_id)
    assert record.id == algorithm_id
    assert record.status in registry.STAGE3_STATUSES
    assert set(record.operators) <= set(registry.STAGE3_OPERATORS)
    assert len(set(record.operators)) == len(record.operators)
    for text in (record.family, record.display_name, record.citation, record.what_it_changes):
        assert isinstance(text, str) and text.strip()


def test_three_families_plus_a_shared_substrate_and_a_none_record() -> None:
    families = {
        registry.resolve_stage3_algorithm(name).family for name in registry.registered_ids()
    }
    assert {"training-free-grpo", "gepa", "ace"} <= families
    assert registry.resolve_stage3_algorithm("shared-rollout").operators == (
        "rollout",
        "scoring",
    )
    none = registry.resolve_stage3_algorithm(registry.NONE_ALGORITHM_ID)
    assert none.operators == () and none.status == "not-applicable"
    assert isinstance(none.reason, str) and none.reason.strip()


def test_the_inference_time_verification_record_is_a_flown_selection_family() -> None:
    """The VERIFY-1 line's own record (coordinator authorisation, 2026-09-25).

    The record read ``planned`` while the family had already flown, which the
    2026-09-26 academic-baseline report caught: VERIFY-1 spent 625 contacts on this
    family and sealed a verdict, so ``base-loop`` -- implemented and flown as a
    registered cell family -- is the true status and ``planned`` was a stale claim
    that no cell existed. A status is a fact about this repository, not a label of
    intent. The operator pair is what a verifier
    changes -- it scores the core's own samples and selects one -- and neither
    ``update`` nor ``context_application`` is among them, because no store, view
    or instruction text is touched.
    """

    record = registry.resolve_stage3_algorithm("inference-time-verification-v1")
    assert record.family == "test-time-scaling"
    assert record.status == "base-loop"
    assert record.operators == ("scoring", "selection")
    assert record.reason is None
    assert "2026-09-24-slurp-sample-aggregation-offline-read.md" in record.citation


def test_a_verification_label_may_not_claim_an_update_operator() -> None:
    """A cell on this family that claimed to change the store is mislabelled."""

    with pytest.raises(registry.Stage3AlgorithmError, match="does not define"):
        registry.validate_stage3_algorithm_label(
            {
                "id": "inference-time-verification-v1",
                "operators_used": ["selection", "update"],
                "note": "a cell that claims an operator the family does not define",
            },
            cell="synthetic",
        )


def test_a_verification_label_declaring_selection_resolves() -> None:
    record, used = registry.validate_stage3_algorithm_label(
        {
            "id": "inference-time-verification-v1",
            "operators_used": ["selection"],
            "note": "one contact per row selects among that row's own sealed samples.",
        },
        cell="synthetic",
    )
    assert record.id == "inference-time-verification-v1"
    assert used == ("selection",)


def test_a_record_with_an_unknown_operator_is_refused() -> None:
    with pytest.raises(registry.Stage3AlgorithmError, match="unknown operator"):
        registry.Stage3Algorithm(
            id="x", family="f", display_name="d", citation="c",
            operators=("rollout", "teleport"), status="planned", what_it_changes="w",
        )


def test_a_not_applicable_record_must_state_a_reason() -> None:
    with pytest.raises(registry.Stage3AlgorithmError, match="must state its reason"):
        registry.Stage3Algorithm(
            id="x", family="f", display_name="d", citation="c", operators=(),
            status="not-applicable", what_it_changes="w",
        )


def test_an_unregistered_id_does_not_resolve() -> None:
    with pytest.raises(registry.Stage3AlgorithmError, match="unknown"):
        registry.resolve_stage3_algorithm("ppo-v1")


# ---------------------------------------------------------------------------
# The label
# ---------------------------------------------------------------------------


def test_a_good_label_resolves_to_its_record_and_operators() -> None:
    record, used = registry.validate_stage3_algorithm_label(
        {
            "id": "tfgrpo-semantic-advantage-v1",
            "operators_used": ["update", "context_application"],
            "note": "CELL-1 applies the experiential deltas.",
        },
        cell="cell",
    )
    assert record.id == "tfgrpo-semantic-advantage-v1"
    assert used == ("update", "context_application")


@pytest.mark.parametrize(
    "label, match",
    [
        ("shared-rollout", "must be an object"),
        ({"operators_used": ["rollout"], "note": "n"}, r"missing key\(s\) \['id'\]"),
        ({"id": "shared-rollout", "note": ""}, "note must be a non-empty"),
        ({"id": "shared-rollout", "note": "n", "family": "x"}, r"unknown key\(s\)"),
        ({"id": "tfgrpo-v9", "operators_used": [], "note": "n"}, "unknown"),
        (
            {"id": "shared-rollout", "operators_used": ["selection"], "note": "n"},
            "does not define",
        ),
        (
            {"id": "shared-rollout", "operators_used": ["rollout", "rollout"], "note": "n"},
            "repeats an operator",
        ),
        ({"id": "shared-rollout", "operators_used": [], "note": "n"}, "is empty"),
        ({"id": "shared-rollout", "operators_used": "rollout", "note": "n"}, "must be a list"),
    ],
)
def test_a_malformed_label_is_refused(label: object, match: str) -> None:
    with pytest.raises(registry.Stage3AlgorithmError, match=match):
        registry.validate_stage3_algorithm_label(label, cell="cell")


def test_the_none_label_may_declare_no_operator() -> None:
    record, used = registry.validate_stage3_algorithm_label(
        {"id": "none", "operators_used": [], "note": "A control cell on the locked plan."},
        cell="cell",
    )
    assert record.id == "none" and used == ()


# ---------------------------------------------------------------------------
# The real tree
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stem", sorted(LABELLED_FRAGMENTS))
def test_each_held_stage3_fragment_carries_its_label(stem: str) -> None:
    document = json.loads(
        (REPO / "configs/experiment" / f"{stem}.json").read_text(encoding="utf-8")
    )
    expected_id, expected_operators = LABELLED_FRAGMENTS[stem]
    record, used = registry.validate_stage3_algorithm_label(
        registry.label_of(document), cell=stem
    )
    assert record.id == expected_id
    assert list(used) == expected_operators


def test_a_run_id_resolves_to_its_cells_label() -> None:
    summary = registry.summary_for_run_id(REPO, "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1")
    assert summary is not None
    assert summary["id"] == "shared-rollout"
    assert summary["operators_used"] == ["rollout"]
    assert summary["source"].endswith("slurp-native-stage3-rollout-r01-v1.json")
    assert registry.summary_for_run_id(REPO, "SAEA-NO-SUCH-RUN-V1") is None


def test_the_override_wins_over_the_fragment_lookup() -> None:
    summary = registry.summary_for_run_id(
        REPO, "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1", "gepa-reflective-pareto-v1"
    )
    assert summary["id"] == "gepa-reflective-pareto-v1"
    assert summary["source"] == "cli"


def test_the_gate_passes_on_the_real_repository() -> None:
    data = gate.evaluate(REPO)
    assert data["passed"], data["violations"]
    labelled = {row["cell"]: row["algorithm_id"] for row in data["stage3_cells"]}
    for stem, (expected_id, _operators) in LABELLED_FRAGMENTS.items():
        assert labelled[stem] == expected_id
    assert set(data["allowlisted_cells"]) <= set(labelled)


def test_every_allowlist_entry_names_a_registered_algorithm() -> None:
    for _stem, (prose_id, reason) in gate.ALLOWLIST.items():
        registry.resolve_stage3_algorithm(prose_id)
        assert reason.strip()


# ---------------------------------------------------------------------------
# The gate, on a synthetic repository
# ---------------------------------------------------------------------------


def _repo(tmp_path: Path, fragments: dict[str, dict]) -> Path:
    directory = tmp_path / "configs" / "experiment"
    directory.mkdir(parents=True)
    for stem, document in fragments.items():
        (directory / f"{stem}.json").write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return tmp_path


def _cell(**label: object) -> dict:
    document = {
        "experiment_id": "SAEA-SLURP-STAGE3-SYNTHETIC-V1",
        "purpose": "synthetic Stage-3 cell",
    }
    if label:
        document["stage3_algorithm"] = label
    return document


def test_a_labelled_synthetic_cell_passes(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path,
        {
            "slurp-native-stage3-synthetic-v1": _cell(
                id="shared-rollout", operators_used=["rollout"], note="a rollout."
            )
        },
    )
    data = gate.evaluate(repo)
    assert data["passed"]
    assert data["stage3_cells"][0]["algorithm_id"] == "shared-rollout"
    assert data["cells_per_algorithm"] == {"shared-rollout": 1}


def test_a_stage3_cell_without_a_label_fails(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"slurp-native-stage3-synthetic-v1": _cell()})
    data = gate.evaluate(repo)
    assert not data["passed"]
    assert data["violations"][0]["kind"] == "missing-label"
    assert "carries no top-level 'stage3_algorithm'" in data["violations"][0]["message"]


def test_an_unregistered_id_fails(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path,
        {
            "slurp-native-stage3-synthetic-v1": _cell(
                id="ppo-v1", operators_used=["update"], note="n"
            )
        },
    )
    data = gate.evaluate(repo)
    assert not data["passed"]
    assert data["violations"][0]["kind"] == "invalid-label"
    assert "unknown" in data["violations"][0]["message"]


def test_an_operator_the_algorithm_does_not_define_fails(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path,
        {
            "slurp-native-stage3-synthetic-v1": _cell(
                id="shared-rollout", operators_used=["update"], note="n"
            )
        },
    )
    data = gate.evaluate(repo)
    assert not data["passed"]
    assert "does not define" in data["violations"][0]["message"]


def test_an_allowlisted_cell_passes_without_a_label(tmp_path: Path) -> None:
    stem = "slurp-native-review-primitives-v1"
    repo = _repo(tmp_path, {stem: {"experiment_id": "SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-V1"}})
    data = gate.evaluate(repo)
    assert data["passed"]
    row = data["stage3_cells"][0]
    assert row["cell"] == stem
    assert row["source"] == "allowlist-prose"
    assert row["algorithm_id"] == gate.ALLOWLIST[stem][0]


def test_a_fragment_naming_a_stage3_spec_is_in_scope(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path,
        {
            "slurp-native-some-cell-v1": {
                "experiment_id": "SAEA-SLURP-NATIVE-SOME-CELL-V1",
                "purpose": f"per {gate.STAGE3_SPEC_RELPATHS[1]} section S3-6",
            }
        },
    )
    data = gate.evaluate(repo)
    assert not data["passed"]
    assert data["violations"][0]["kind"] == "missing-label"


def test_prose_about_stage_3_does_not_make_a_stage_2_cell_in_scope(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path,
        {
            "slurp-native-b1-v1": {
                "experiment_id": "SAEA-SLURP-NATIVE-B1-V1",
                "purpose": "No Stage-3 claim is made here; Stage 3 owns the confirmatory read.",
            }
        },
    )
    data = gate.evaluate(repo)
    assert data["passed"]
    assert data["stage3_cells"] == []


def test_main_returns_zero_on_a_clean_synthetic_repository(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path,
        {
            "slurp-native-stage3-synthetic-v1": _cell(
                id="ace-grow-refine-v1", operators_used=["update"], note="a curator."
            )
        },
    )
    assert gate.main(["--repo-root", str(repo)]) == 0
    assert gate.main(["--repo-root", str(repo), "--json"]) == 0


def test_main_returns_one_on_an_unlabelled_synthetic_repository(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"slurp-native-stage3-synthetic-v1": _cell()})
    assert gate.main(["--repo-root", str(repo)]) == 1
