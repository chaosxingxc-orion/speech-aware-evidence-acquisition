"""NX: refusals of ``scripts/analysis/slurp_nx_postproc_v4_apply.py`` (model-free, no data root)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

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


# ---------------------------------------------------------------------------
# Fold B admission by a registered analysis recipe

_R1_RUN = "SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1"
_R1_ATT = "attempt-slurp-native-stage3-nx-r1-solver-fold-b-generation-v1"


def _recipe_root(tmp_path, *, run=_R1_RUN, attempt=_R1_ATT, columns=("v4", "v4g"), applied=("lock", "aa", "r1-c1")):
    directory = tmp_path / "repo" / "docs" / "readiness" / "pkg"
    directory.mkdir(parents=True)
    names = {"v4": "saea-deliver-normalise-v4", "v4g": "saea-deliver-normalise-v4g"}
    recipe = {
        "recipe_id": "synthetic-recipe",
        "arms": {"arm": {"run_id": run, "attempt_id": attempt}},
        "offline_columns": {"columns": {c: {"normaliser": names[c]} for c in columns}, "applied_to": list(applied)},
    }
    (directory / "analysis-recipe-v1.json").write_text(json.dumps(recipe), encoding="utf-8")
    return tmp_path / "repo"


def _sealed_run_dir(tmp_path, *, manifest=True):
    directory = tmp_path / "data" / "runs" / _R1_RUN / _R1_ATT
    directory.mkdir(parents=True)
    if manifest:
        (directory / f"{_R1_RUN}.run-manifest.json").write_text("{}", encoding="utf-8")
    return tmp_path / "data"


def _fold_b_id():
    roster = json.loads((_REPO / A.FOLD_B_ROSTER).read_text(encoding="utf-8"))
    return str(roster["items"][0]["sample_id"])


def test_a_fold_b_pool_named_by_a_recipe_declaring_the_column_is_admitted(tmp_path):
    root, data = _recipe_root(tmp_path), _sealed_run_dir(tmp_path)
    admission = A.recipe_admission(_R1_RUN, _R1_ATT, "v4g", "lock", data, root)
    assert admission["recipe_id"] == "synthetic-recipe" and len(admission["recipe_sha256"]) == 64
    A.refuse_fold_b([_fold_b_id()], admission)  # no raise
    assert A.recipe_admission(_R1_RUN, _R1_ATT, "v4", None, data, root) is not None


def test_the_registered_r1_recipe_admits_the_r1_run(tmp_path):
    data = _sealed_run_dir(tmp_path)
    for variant in ("v4", "v4g"):
        for column in ("lock", "aa", "r1-c1", "r1-c5"):
            assert A.recipe_admission(_R1_RUN, _R1_ATT, variant, column, data) is not None


def test_a_fold_b_pool_without_a_naming_recipe_is_refused(tmp_path):
    data = _sealed_run_dir(tmp_path)
    for kwargs in ({"run": "OTHER-RUN"}, {"attempt": "other-attempt"}, {"columns": ("v4",)}, {"applied": ("lock",)}):
        root = _recipe_root(tmp_path / f"r{len(str(kwargs))}{abs(hash(str(kwargs))) % 997}", **kwargs)
        variant, column = ("v4g", "r1-c1") if kwargs.get("columns") or kwargs.get("applied") else ("v4", "lock")
        admission = A.recipe_admission(_R1_RUN, _R1_ATT, variant, column, data, root)
        assert admission is None
        with pytest.raises(A.ApplyError, match="Fold B is not read by this script"):
            A.refuse_fold_b([_fold_b_id()], admission)
    with pytest.raises(A.ApplyError, match="Fold B"):
        A.refuse_fold_b([_fold_b_id()], None)


def test_a_recipe_does_not_admit_an_unsealed_attempt(tmp_path):
    root, data = _recipe_root(tmp_path), _sealed_run_dir(tmp_path, manifest=False)
    with pytest.raises(A.ApplyError, match="not sealed"):
        A.recipe_admission(_R1_RUN, _R1_ATT, "v4", None, data, root)


def test_a_recipe_never_opens_the_test_split(tmp_path):
    # the split gate runs before (and independently of) any recipe: a test scorer is refused by resolve_run
    data = _sealed_run_dir(tmp_path)
    (data / "runs" / _R1_RUN / _R1_ATT / f"{_R1_RUN}.scores.json").write_text(
        json.dumps({"slurp-slu-official-test": {}}), encoding="utf-8")
    with pytest.raises(A.ApplyError, match="test split is closed"):
        A.resolve_run(f"{_R1_RUN}/{_R1_ATT}", data)


def test_reserved_labels_are_still_refused_for_an_admitted_run(tmp_path):
    data = _sealed_run_dir(tmp_path)
    (data / "runs" / _R1_RUN / _R1_ATT / f"{_R1_RUN}.scores.json").write_text(
        json.dumps({"slurp-slu-official-train": {}}), encoding="utf-8")
    args = SimpleNamespace(apply="v4g", pool=f"{_R1_RUN}/{_R1_ATT}", column="lock", label="confirm-fold-a",
                           data_root=str(data), lock="unused", allow_rewrite_identical=False)
    with pytest.raises(A.ApplyError, match="reserved"):
        A.apply(args)


# ---------------------------------------------------------------------------
# --column on a synthetic sealed run carrying a template-arm group

def _column_fixture(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.bundle as bundle_module
    from test_slurp_nx_solver_column_read import ANSWERS, _sealed

    outputs, trace = _sealed()
    directory = tmp_path / "runs" / "RUN" / "attempt"
    directory.mkdir(parents=True)
    (directory / "RUN.run-manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(bundle_module, "verify_bundle",
                        lambda path: SimpleNamespace(outputs_rows=outputs, trace_records=trace))
    return {"run_id": "RUN", "attempt": "attempt"}, ANSWERS


def test_column_reads_one_arms_raw_first_visit_answers_from_the_sealed_group(tmp_path, monkeypatch):
    spec, answers = _column_fixture(tmp_path, monkeypatch)
    texts, block = A.column_texts(tmp_path, spec, "t1")
    assert texts == answers["t1"]
    assert block["kind"] == "template-arm" and block["arm_id"] == "t1" and block["delivering_arm"] == "lock"
    assert block["arm_ids"] == ["t1", "t2", "aa", "lock"] and len(block["manifest_sha256"]) == 64
    assert A.column_texts(tmp_path, spec, "lock")[0] == answers["lock"]
    assert A.column_texts(tmp_path, spec, "aa")[0] == answers["aa"]


def test_column_naming_an_arm_outside_the_group_is_refused(tmp_path, monkeypatch):
    spec, _ = _column_fixture(tmp_path, monkeypatch)
    with pytest.raises(A.ApplyError, match="is not in the run's arm group"):
        A.column_texts(tmp_path, spec, "no-such-arm")


def test_column_texts_score_through_the_driver_vectors(tmp_path, monkeypatch):
    from test_slurp_nx_solver_column_read import GOLD

    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

    spec, _ = _column_fixture(tmp_path, monkeypatch)
    gold = {sid: {"scenario": "calendar", "action": "set", "entities": [SlotEntity(t, f) for t, f in ents]}
            for sid, ents in GOLD.items()}
    matrix = {}
    for arm in ("t1", "lock"):
        texts, _block = A.column_texts(tmp_path, spec, arm)
        ids = sorted(texts)
        matrix[arm], _unparsed = A.score_vectors(ids, texts, gold)
        assert matrix[arm].shape == (len(GOLD), 10)
    assert (matrix["t1"] != matrix["lock"]).any()
