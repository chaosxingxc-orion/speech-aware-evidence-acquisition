#!/usr/bin/env python3
"""backfill_sealonly_read_inputs.py -- write the two derived files a seal-only
completion did not seal, next to an ALREADY-SEALED run (E10e, 2026-09-29).

`core.flight.cli seal-only` opens no server, no slot, no client, and never
reaches the deferred-scoring path (`core.flight.scoring.seal_scoring_inputs`)
that writes `<run_id>.generation-manifest.json`, and its own `run_phases()`
never populates `self._phase_summaries` (nothing left to fly), so it also
never writes `<run_id>.phases.json`. Both are now written AT SEAL TIME by
`core.flight.runtime.FlightRuntime.seal()` for every NEW seal-only completion
(`_write_seal_only_generation_manifest`, `_seal_only_phases_document`); this
script closes the gap for a run that ALREADY sealed before that fix existed
(e.g. `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1`'s
`attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only`).

It calls the EXACT SAME three `FlightRuntime` methods `seal()` now calls --
`_merged_canonical_rows`, `_seal_only_predecessor_cost_summary` (through
`_write_seal_only_generation_manifest`), and `_seal_only_phases_document` --
over a bare runtime skeleton bound to the cell's own composed configuration
and its declared `resume_from` predecessors, scanned exactly as
`core.flight.runtime.FlightRuntime._load_resume_predecessor` scans them at a
live preflight. It never re-derives the cost or phase shape a second way.

MODEL-FREE and READ-MOSTLY: it reads the target run's own sealed
`<run_id>.run-manifest.json` and every declared predecessor's trace (never a
predecessor's `outputs.jsonl`/`scores.json`, and never gold), and writes
ONLY the two named files, at the target run's own attempt directory. It
REFUSES before writing anything if:

* the target run manifest is missing or not ``COMPLETED``;
* either target file already exists (never overwrites a sealed read input);
* the cell declares no ``resume_from``, or any declared predecessor's trace
  is missing, re-hashed, or does not cover this attempt's own roster
  (exactly `_load_resume_predecessor`'s own refusals, reused here rather
  than re-implemented).

Usage (WSL, PYTHONPATH=<tree>/src)::

    python -B scripts/analysis/backfill_sealonly_read_inputs.py \\
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" \\
        --experiment slurp-native-stage3-comp1-fold-a-v1-resume \\
        --run-id SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 \\
        --attempt-id attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only

Do not run this against a live data root while a flight is using it: it opens
no lease and takes no lock, so it is safe to run in parallel with an
UNRELATED run's flight, but it should never race a flight or another backfill
touching the SAME run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Sequence


class BackfillError(RuntimeError):
    """The target run cannot be backfilled as declared."""


def _cell(repo_root: Path, experiment: str, run_id: str):
    from speech_aware_evidence_acquisition.core.flight.campaign import (  # noqa: PLC0415
        CampaignError,
        load_campaign_cells,
    )

    try:
        cells = load_campaign_cells(repo_root, experiment)
    except CampaignError as error:
        raise BackfillError(str(error)) from error
    for cell in cells:
        if cell.run_id == run_id:
            return cell
    raise BackfillError(f"experiment {experiment!r} declares no cell for run {run_id!r}")


def backfill(
    *, repo_root: Path, data_root: Path, experiment: str, run_id: str, attempt_id: str,
) -> dict[str, object]:
    """Write ``<run_id>.generation-manifest.json`` and ``<run_id>.phases.json``
    next to the already-sealed ``attempt_id``. Returns the two written
    documents (never printed with response text -- the phases document
    carries delivered text verbatim, so a caller that logs this return value
    must treat it with the same care as any other sealed artifact)."""

    from speech_aware_evidence_acquisition.core.config import compose  # noqa: PLC0415
    from speech_aware_evidence_acquisition.core.flight.resume import (  # noqa: PLC0415
        MergedPredecessors,
        ResumeRecoveryError,
        read_predecessor_attempt,
        resume_declarations_from_document,
    )
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: PLC0415

    # Cheap, config-free refusals FIRST: whether this run can be backfilled
    # at all is decided by what is already on disk, before any experiment
    # fragment is even read.
    run_dir = data_root / "runs" / run_id / attempt_id
    manifest_path = run_dir / f"{run_id}.run-manifest.json"
    if not manifest_path.is_file():
        raise BackfillError(f"no sealed run manifest at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPLETED":
        raise BackfillError(f"{manifest_path} status is {manifest.get('status')!r}, not COMPLETED")

    generation_path = run_dir / f"{run_id}.generation-manifest.json"
    phases_path = run_dir / f"{run_id}.phases.json"
    existing = [path for path in (generation_path, phases_path) if path.exists()]
    if existing:
        raise BackfillError(
            "refusing to overwrite already-sealed file(s): "
            + ", ".join(str(path) for path in existing)
        )

    cell = _cell(repo_root, experiment, run_id)
    if cell.attempt_id != attempt_id:
        raise BackfillError(
            f"cell {cell.document['cell_id']!r} declares attempt_id {cell.attempt_id!r}, "
            f"not the requested {attempt_id!r}"
        )
    if cell.resume_from is None:
        raise BackfillError(
            f"cell {cell.document['cell_id']!r} declares no resume_from; this is not a "
            "resume-recovery cell and has no predecessors to backfill from"
        )

    composed = compose(
        repo_root, cell.document["model_fragment"], cell.document["dataset_fragment"],
        cell.document["baseline_fragment"], experiment,
    )
    policy = str(composed.values.get("policy") or "")
    if not policy:
        raise BackfillError("composed baseline fragment declares no non-empty 'policy'")
    program = default_phase_program(policy)
    raw_native = composed.values.get("native_episode")
    relisten = raw_native.get("relisten") if isinstance(raw_native, dict) else None

    declarations = resume_declarations_from_document(cell.resume_from)
    predecessors = []
    for declaration in declarations:
        if declaration.mode != "trace":
            raise BackfillError(
                f"predecessor {declaration.attempt_id!r} is a row-checkpoint (mode B) "
                "declaration; this backfill replays traces and has no checkpoint reader"
            )
        attempt_dir = data_root / "runs" / run_id / declaration.attempt_id
        try:
            predecessor = read_predecessor_attempt(
                run_id=run_id, attempt_id=declaration.attempt_id, attempt_dir=attempt_dir,
                expected_trace_sha256=declaration.trace_sha256, program_id=program.program_id,
                relisten=relisten,
            )
        except ResumeRecoveryError as error:
            raise BackfillError(str(error)) from error
        predecessors.append(predecessor)
    try:
        merged = MergedPredecessors(tuple(predecessors))
    except ResumeRecoveryError as error:
        raise BackfillError(str(error)) from error

    roster_ids = (manifest.get("split") or {}).get("ids")
    if not isinstance(roster_ids, list) or not roster_ids:
        raise BackfillError(f"{manifest_path} split block carries no non-empty 'ids' list")
    roster = tuple(str(sample_id) for sample_id in roster_ids)
    missing = sorted(set(roster) - set(merged.complete_sample_ids))
    if missing:
        raise BackfillError(
            f"{len(missing)} roster sample(s) are not COMPLETE in the declared "
            f"predecessors, e.g. {missing[:5]}; this attempt is not fully covered by "
            "resume_from over its own sealed roster"
        )

    runtime = _skeleton(
        composed=composed, resume=merged, data_root=data_root, run_id=run_id,
        attempt_id=attempt_id, roster=roster,
    )
    _canonical_rows, _predecessor_block, seal_only_phase_results = (
        runtime._merged_canonical_rows()
    )
    if not seal_only_phase_results:
        raise BackfillError("the replay produced no phase results; nothing to backfill")

    generation_document = runtime._write_seal_only_generation_manifest(run_dir)
    phases_document = runtime._seal_only_phases_document(seal_only_phase_results)
    phases_path.write_text(
        json.dumps(phases_document, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "generation_manifest_path": str(generation_path),
        "generation_manifest_sha256": _sha256_file(generation_path),
        "phases_path": str(phases_path),
        "phases_sha256": _sha256_file(phases_path),
        "predecessor_attempt_ids": [predecessor.attempt_id for predecessor in predecessors],
        "roster_rows": len(roster),
        "phase_results": len(seal_only_phase_results),
    }


def _skeleton(
    *, composed, resume, data_root: Path, run_id: str, attempt_id: str,
    roster: Sequence[str],
):
    """A bare ``FlightRuntime`` carrying only what ``_merged_canonical_rows``,
    ``_write_seal_only_generation_manifest`` and ``_seal_only_phases_document``
    read -- no transport, session, gate, lease or attempt accounting exists,
    exactly the same seam ``scripts/analysis/replay_seal_consistency.py``'s
    own ``_skeleton`` uses for the same reason (a model-free replay proof
    needs no more of ``FlightRuntime`` than this)."""

    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime  # noqa: PLC0415

    runtime = object.__new__(FlightRuntime)
    runtime._composed = composed
    runtime._plan = SimpleNamespace(
        run_id=run_id, attempt_id=attempt_id,
        carrier_lock_key=composed.values.get("carrier_lock_key"),
    )
    runtime._resume = resume
    runtime._resume_flown_sample_ids = ()
    runtime._seal_only = True
    runtime._data_root = data_root
    runtime._run_id = run_id
    runtime._attempt_id = attempt_id
    runtime._explicit_run_dir = None
    runtime._client = None
    runtime._output_rows = []
    runtime._samples = tuple(SimpleNamespace(sample_id=sample_id) for sample_id in roster)
    runtime._identity_packet_bindings = None
    runtime._artifact_result_binding = None
    runtime._artifact_content_validator = None
    runtime._phase_summaries = ()
    return runtime


def _sha256_file(path: Path) -> str:
    import hashlib

    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    args = parser.parse_args(argv)
    try:
        written = backfill(
            repo_root=Path(args.repo_root).resolve(),
            data_root=Path(args.data_root),
            experiment=args.experiment,
            run_id=args.run_id,
            attempt_id=args.attempt_id,
        )
    except BackfillError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    print(json.dumps(
        {key: written[key] for key in (
            "generation_manifest_path", "generation_manifest_sha256",
            "phases_path", "phases_sha256", "predecessor_attempt_ids",
            "roster_rows", "phase_results",
        )},
        indent=2, sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
