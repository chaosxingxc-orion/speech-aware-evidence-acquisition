"""No-contact reader for the future sealed semantic AgentLoop flight.

This reader accepts a prepared JSON input only after the four manifests are
complete and the three official whole-manifest score payloads exist. It never
invokes an official scorer, opens a model session, performs runtime retrieval,
or makes a network request.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping

from speech_aware_evidence_acquisition.analysis.a2t_semantic_agentloop_postseal import (
    RetrievalDiagnosticSample,
    analyze_semantic_agentloop_flight,
)


def _object(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be an object")
    return value


def _diagnostics(value: object) -> tuple[RetrievalDiagnosticSample, ...]:
    if not isinstance(value, list):
        raise RuntimeError("retrieval_samples must be an array")
    rows = []
    for index, raw in enumerate(value):
        row = _object(raw, f"retrieval_samples[{index}]")
        required = {
            "sample_id",
            "tier",
            "retrieval_sealed",
            "required_tool_ids",
            "ranked_tool_ids",
        }
        optional = {
            "required_ordered_call_skeleton",
            "gold_calls",
            "ranked_ordered_call_skeletons",
            "proposed_action_sets",
        }
        if not required.issubset(row) or not set(row).issubset(required | optional):
            raise RuntimeError(
                f"retrieval_samples[{index}] must contain required fields {sorted(required)} "
                f"and only optional trace fields {sorted(optional)}"
            )
        rows.append(RetrievalDiagnosticSample(**row))
    return tuple(rows)


def build_report(
    document: Mapping[str, object], *, bootstrap_replicates: int, bootstrap_seed: int
) -> Mapping[str, object]:
    """Validate one explicit post-seal input document and return its report."""

    expected = {"manifests", "score_payloads", "retrieval_samples"}
    if set(document) != expected:
        raise RuntimeError(f"input must contain exactly {sorted(expected)}")
    return analyze_semantic_agentloop_flight(
        manifests=_object(document["manifests"], "manifests"),
        score_payloads=_object(document["score_payloads"], "score_payloads"),
        retrieval_samples=_diagnostics(document["retrieval_samples"]),
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze a sealed semantic AgentLoop flight without contact."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260903)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise RuntimeError(f"refusing to overwrite existing report: {args.out}")
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read input document: {error}") from error
    report = build_report(
        _object(document, "input"),
        bootstrap_replicates=args.bootstrap_replicates,
        bootstrap_seed=args.bootstrap_seed,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
