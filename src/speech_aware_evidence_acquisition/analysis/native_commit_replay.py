"""Offline COMMIT-policy re-aggregation over a sealed grouped-Solver run.

E2 (SLURP v2 base program M2), item 5: read a sealed episode receipt set --
one ``outputs.jsonl`` whose rows carry the ``solver_group`` custody
``reproduction.ojw.native_group_solver.run_grouped_solver_samples`` produces
(every raw sample: ``sample_index``, ``seed``, ``temperature``,
``parse_status``, ``parsed_answer``) -- and re-apply a registered
``core.base.COMMIT_POLICIES`` entry with DIFFERENT parameters, without any
model, tool or network contact. This is a read-only sensitivity tool (the
B2 cell's preregistered ``s in {2, 3, 4}`` offline table, for example): it
writes a NEW ``outputs.jsonl``-shaped file plus a provenance JSON to a
caller-named output directory, refuses to overwrite an existing replay, and
never opens the sealed input file for writing.

Expected sealed row shape (one JSON object per line, exactly the shape
``core.flight.runtime`` seals for a grouped-Solver sample): at minimum
``sample_id`` (str) and ``solver_group`` (the mapping
:func:`rails.native_episode_receipt.validate_solver_group_receipt`
validates). A row without ``solver_group`` cannot be replayed by this tool
and is refused, because it carries no raw per-sample custody to re-commit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping, Sequence

from ..e0.artifacts import sha256_file, write_json_artifact
from ..rails.commit_policies import ParsedSlurpAnswer, SolverSampleVote
from ..reproduction.slurp_scoring import SlotEntity

RESULT_SCHEMA = "saea-native-commit-replay-v1"


class NativeCommitReplayError(RuntimeError):
    """The replay cannot proceed: a bad sealed input, or an attempted overwrite."""


def _read_sealed_rows(outputs_path: Path) -> list[dict[str, object]]:
    """Read a sealed ``outputs.jsonl`` exactly as ``analysis.a2t_v2_rescore``
    does: one JSON object per nonblank line, unique ``sample_id``, no
    tolerance for a malformed line. Read-only -- this function never writes
    to ``outputs_path``."""

    try:
        text = outputs_path.read_text(encoding="utf-8")
    except OSError as error:
        raise NativeCommitReplayError(f"cannot read {outputs_path}: {error}") from error
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise NativeCommitReplayError(f"{outputs_path} is empty")
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise NativeCommitReplayError(
                f"{outputs_path} line {number} is malformed: {error}"
            ) from error
        if not isinstance(row, Mapping):
            raise NativeCommitReplayError(f"{outputs_path} line {number} is not an object")
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise NativeCommitReplayError(f"{outputs_path} line {number} lacks a sample_id")
        if sample_id in seen:
            raise NativeCommitReplayError(
                f"{outputs_path} has a duplicate sample_id {sample_id!r}"
            )
        seen.add(sample_id)
        rows.append(dict(row))
    return rows


def _votes_from_solver_group(solver_group: Mapping[str, object]) -> list[SolverSampleVote]:
    records = solver_group.get("samples") if isinstance(solver_group, Mapping) else None
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or not records:
        raise NativeCommitReplayError("solver_group carries no sample records to replay")
    votes: list[SolverSampleVote] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise NativeCommitReplayError("a solver_group sample record must be a mapping")
        sample_index = record.get("sample_index")
        parsed = None
        if record.get("parse_status") == "ok":
            parsed_answer = record.get("parsed_answer")
            if not isinstance(parsed_answer, Mapping):
                raise NativeCommitReplayError(
                    "a solver_group sample marked 'ok' requires a parsed_answer"
                )
            entities = tuple(
                SlotEntity(type=entity["type"], filler=entity["filler"])
                for entity in parsed_answer.get("entities", [])
            )
            parsed = ParsedSlurpAnswer(
                scenario=parsed_answer.get("scenario", ""),
                action=parsed_answer.get("action", ""),
                entities=entities,
            )
        votes.append(SolverSampleVote(sample_index=sample_index, parsed=parsed))
    return votes


def replay_row(
    row: Mapping[str, object], *, policy, commit_params: Mapping[str, object],
) -> dict[str, object]:
    """Re-commit ONE sealed row's raw samples under ``policy``.

    Never reads or writes anything beyond ``row`` itself; the caller
    resolves ``policy`` once for the whole run.
    """

    solver_group = row.get("solver_group")
    if not isinstance(solver_group, Mapping):
        raise NativeCommitReplayError(
            f"row {row.get('sample_id')!r} carries no solver_group custody to replay"
        )
    votes = _votes_from_solver_group(solver_group)
    outcome = policy(votes, **dict(commit_params))
    payload = {
        "scenario": outcome.answer.scenario,
        "action": outcome.answer.action,
        "entities": [
            {"type": entity.type, "filler": entity.filler} for entity in outcome.answer.entities
        ],
    }
    return {
        "sample_id": row["sample_id"],
        "final_response_text": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        "replayed_commit_policy_id": outcome.policy_id,
        "replayed_intent_support": outcome.intent_support,
    }


def replay(
    *,
    outputs_path: Path,
    policy_id: str,
    commit_params: Mapping[str, object],
    output_dir: Path,
) -> dict[str, object]:
    """Read a sealed run, re-commit every row under ``policy_id`` /
    ``commit_params``, and write the result to a fresh ``output_dir``.

    Refuses to overwrite: ``output_dir`` must not already contain
    ``outputs.jsonl`` or ``provenance.json``. Never opens ``outputs_path``
    for writing.
    """

    from ..core.base import COMMIT_POLICIES, CoreError  # noqa: PLC0415
    # Function-local: importing rails.commit_policies is what POPULATES
    # core.base.COMMIT_POLICIES (same registration discipline as the rest of
    # this package).
    from ..rails import commit_policies as _commit_policies  # noqa: PLC0415, F401

    outputs_path = Path(outputs_path)
    output_dir = Path(output_dir)
    outputs_target = output_dir / "outputs.jsonl"
    provenance_target = output_dir / "provenance.json"
    if outputs_target.exists() or provenance_target.exists():
        raise NativeCommitReplayError(
            f"refusing to overwrite an existing replay at {output_dir}"
        )
    try:
        policy = COMMIT_POLICIES.resolve(policy_id)
    except CoreError as error:
        raise NativeCommitReplayError(str(error)) from error

    rows = _read_sealed_rows(outputs_path)
    replayed = [
        replay_row(row, policy=policy, commit_params=commit_params) for row in rows
    ]

    source_sha256 = sha256_file(outputs_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    text = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) for row in replayed
    ) + "\n"
    outputs_target.write_text(text, encoding="utf-8", newline="\n")
    provenance = {
        "schema": RESULT_SCHEMA,
        "source": {"outputs_path": str(outputs_path), "sha256": source_sha256},
        "policy_id": policy_id,
        "parameters": dict(commit_params),
        "model_calls": 0,
        "rows": len(replayed),
    }
    write_json_artifact(provenance_target, provenance)
    return provenance


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline re-aggregation of a sealed grouped-Solver run under a "
            "(possibly different) core.base.COMMIT_POLICIES entry. Zero model "
            "contact; never touches the sealed input file."
        ),
    )
    parser.add_argument("--outputs", required=True, help="sealed outputs.jsonl path")
    parser.add_argument(
        "--policy", required=True, help="registered core.base.COMMIT_POLICIES id",
    )
    parser.add_argument("--min-support", type=int, required=True)
    parser.add_argument("--similarity-threshold", type=float, required=True)
    parser.add_argument(
        "--output-dir", required=True, help="a new, not-yet-existing output directory",
    )
    args = parser.parse_args(argv)
    replay(
        outputs_path=Path(args.outputs),
        policy_id=args.policy,
        commit_params={
            "min_support": args.min_support,
            "similarity_threshold": args.similarity_threshold,
        },
        output_dir=Path(args.output_dir),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["NativeCommitReplayError", "main", "replay", "replay_row"]
