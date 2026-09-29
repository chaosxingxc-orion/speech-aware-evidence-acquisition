"""E10e (2026-09-29): the model-free backfill over an ALREADY-SEALED seal-only
run (``scripts/analysis/backfill_sealonly_read_inputs.py``).

The core proof: the backfill's own bare ``FlightRuntime`` skeleton
(``_skeleton``), fed the SAME composed config and merged predecessors a live
seal-only completion used, calls the EXACT SAME three methods ``seal()``
itself now calls (``_merged_canonical_rows``,
``_write_seal_only_generation_manifest``, ``_seal_only_phases_document``) and
reproduces byte-identical documents to what that live completion actually
sealed -- proving the backfill is a genuine replay of the same code, never a
second derivation of the shape.

No model, server, tokenizer or network contact anywhere in this file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_ANALYSIS = Path(__file__).resolve().parents[2] / "scripts" / "analysis"
if str(_SCRIPTS_ANALYSIS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ANALYSIS))

import backfill_sealonly_read_inputs as backfill_module  # noqa: E402

from test_flight_resume_seal_only import _two_predecessor_runtime  # noqa: E402
# Module-scoped fixture the harness's transport identity needs.
from test_llama_server_transport import _spawn_live_matching_process  # noqa: E402, F401


def _sealed_two_predecessor_run(tmp_path, monkeypatch):
    """Fly and seal the standard two-predecessor seal-only scenario; return
    ``(runtime, seal_result, run_dir)``."""

    runtime = _two_predecessor_runtime(tmp_path, monkeypatch)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()
    seal_result = runtime.seal()
    run_dir = Path(seal_result["outputs_path"]).parent
    return runtime, seal_result, run_dir


def test_backfill_skeleton_reproduces_the_generation_manifest_and_phases_seal_wrote(
    tmp_path, monkeypatch
):
    runtime, seal_result, run_dir = _sealed_two_predecessor_run(tmp_path, monkeypatch)

    generation_path = run_dir / "SAEA-TEST-RUN-001.generation-manifest.json"
    phases_path = Path(seal_result["phases_path"])
    original_generation = json.loads(generation_path.read_text(encoding="utf-8"))
    original_phases = json.loads(phases_path.read_text(encoding="utf-8"))

    # Simulate "sealed before this fix existed": the two derived files are
    # gone, only the ordinary sealed artefacts (run manifest, outputs,
    # scores, predecessor traces) remain.
    generation_path.unlink()
    phases_path.unlink()
    assert not generation_path.exists()
    assert not phases_path.exists()

    roster = tuple(sample.sample_id for sample in runtime._samples)
    backfill_runtime = backfill_module._skeleton(
        composed=runtime._composed,
        resume=runtime._resume,
        data_root=tmp_path / "data",
        run_id="SAEA-TEST-RUN-001",
        attempt_id="attempt-001",
        roster=roster,
    )

    _rows, _block, replayed = backfill_runtime._merged_canonical_rows()
    assert replayed is not None
    assert {result.sample_id for result in replayed} == {"s1", "s2"}

    rebuilt_generation = backfill_runtime._write_seal_only_generation_manifest(run_dir)
    rebuilt_phases = backfill_runtime._seal_only_phases_document(replayed)

    assert rebuilt_generation == original_generation
    assert rebuilt_phases == original_phases
    # The generation manifest was WRITTEN to disk by the call above (mirrors
    # seal()'s own write); the phases document is returned for the caller to
    # write, exactly as seal() itself renders it before writing.
    assert json.loads(generation_path.read_text(encoding="utf-8")) == original_generation


def test_backfill_function_refuses_when_a_target_file_already_exists(tmp_path, monkeypatch):
    """The outer ``backfill()`` entry point refuses before touching anything
    else -- including resolving the cell, which needs a real registered
    experiment fragment this test never writes -- once either derived file
    is already there: a sealed read input is never silently overwritten."""

    run_dir = tmp_path / "data" / "runs" / "SAEA-TEST-RUN-001" / "attempt-001"
    run_dir.mkdir(parents=True)
    (run_dir / "SAEA-TEST-RUN-001.run-manifest.json").write_text(
        json.dumps({"status": "COMPLETED", "split": {"ids": ["s1", "s2"]}}),
        encoding="utf-8",
    )
    # The generation manifest already exists (as it would if seal() had
    # already written it, or a previous backfill run had) -- backfill() must
    # refuse outright, without needing a real --experiment config to resolve
    # the cell first.
    (run_dir / "SAEA-TEST-RUN-001.generation-manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        backfill_module, "_cell",
        lambda repo_root, experiment, run_id: (_ for _ in ()).throw(
            AssertionError("backfill() must refuse before resolving the cell")
        ),
    )

    with pytest.raises(backfill_module.BackfillError, match="already-sealed"):
        backfill_module.backfill(
            repo_root=tmp_path, data_root=tmp_path / "data",
            experiment="unused", run_id="SAEA-TEST-RUN-001", attempt_id="attempt-001",
        )


def test_backfill_function_refuses_when_the_run_manifest_is_missing(tmp_path):
    with pytest.raises(backfill_module.BackfillError, match="no sealed run manifest"):
        backfill_module.backfill(
            repo_root=tmp_path, data_root=tmp_path / "data",
            experiment="unused", run_id="SAEA-NO-SUCH-RUN", attempt_id="attempt-001",
        )
