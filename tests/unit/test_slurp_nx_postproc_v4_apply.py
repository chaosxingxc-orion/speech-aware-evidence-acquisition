"""NX: refusals of ``scripts/analysis/slurp_nx_postproc_v4_apply.py`` (model-free, no data root)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]


def _apply_module():
    name = "slurp_nx_postproc_v4_apply"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _REPO / "scripts/analysis/slurp_nx_postproc_v4_apply.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


A = _apply_module()


def _run(tmp_path: Path, blocks: dict) -> Path:
    directory = tmp_path / "runs" / "RUN" / "attempt"
    directory.mkdir(parents=True)
    (directory / "RUN.scores.json").write_text(json.dumps(blocks), encoding="utf-8")
    return tmp_path


def test_the_names_resolve_to_the_registered_ids():
    assert A.NORMALISERS == {"v4": "saea-deliver-normalise-v4", "v4g": "saea-deliver-normalise-v4g"}


def test_a_devel_run_resolves_its_scorer_and_split(tmp_path):
    root = _run(tmp_path, {"slurp-slu-official-projected-v3": {}})
    spec = A.resolve_run("RUN/attempt", root)
    assert (spec["scorer"], spec["split"]) == ("slurp-slu-official-projected-v3", "devel")


def test_a_train_run_resolves_the_train_split(tmp_path):
    root = _run(tmp_path, {"slurp-slu-official-train": {}})
    assert A.resolve_run("RUN/attempt", root)["split"] == "train"


def test_the_test_split_scorer_is_refused(tmp_path):
    root = _run(tmp_path, {"slurp-slu-official-test": {}})
    with pytest.raises(A.ApplyError, match="test split is closed"):
        A.resolve_run("RUN/attempt", root)


def test_a_run_with_no_or_two_slurp_scorers_is_refused(tmp_path):
    root = _run(tmp_path, {"other": {}})
    with pytest.raises(A.ApplyError, match="exactly one SLURP scorer"):
        A.resolve_run("RUN/attempt", root)


def test_a_malformed_pool_is_refused(tmp_path):
    with pytest.raises(A.ApplyError, match="--pool is"):
        A.resolve_run("not-a-pool", tmp_path)


def test_a_run_without_sealed_scores_is_refused(tmp_path):
    with pytest.raises(A.ApplyError, match="no sealed scores"):
        A.resolve_run("RUN/attempt", tmp_path)


def test_fold_b_rows_are_refused():
    roster = json.loads((_REPO / A.FOLD_B_ROSTER).read_text(encoding="utf-8"))
    sid = str(roster["items"][0]["sample_id"])
    with pytest.raises(A.ApplyError, match="Fold B"):
        A.refuse_fold_b([sid])
    A.refuse_fold_b([])


def test_search_driver_labels_are_reserved():
    assert set(A.RESERVED_LABELS) == {"select-a2", "confirm-fold-a"}
