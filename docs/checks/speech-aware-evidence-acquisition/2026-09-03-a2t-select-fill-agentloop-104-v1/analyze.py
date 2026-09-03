"""Two-phase, no-contact reader for the sealed SELECT/FILL flight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping

from speech_aware_evidence_acquisition.analysis.a2t_select_fill_postseal import (
    analyze_sealed_inputs,
    seal_inputs,
)


def _object(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be an object")
    return value


def _read(path: Path, label: str) -> Mapping[str, object]:
    try:
        return _object(json.loads(path.read_text(encoding="utf-8")), label)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read {label}: {error}") from error


def _write_new(path: Path, value: Mapping[str, object], label: str) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite {label}: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seal or analyze the 104-row SELECT/FILL flight without contact."
    )
    commands = parser.add_subparsers(dest="mode", required=True)
    seal = commands.add_parser("seal-inputs")
    seal_source = seal.add_mutually_exclusive_group(required=True)
    seal_source.add_argument("--source", type=Path)
    seal_source.add_argument("--recovery-receipt", type=Path)
    seal.add_argument("--out", type=Path, required=True)
    analyze = commands.add_parser("analyze")
    analyze.add_argument("--seal", type=Path, required=True)
    analyze.add_argument("--score-batch", type=Path, required=True)
    analyze.add_argument("--lock", type=Path, required=True)
    analyze.add_argument("--data-root", type=Path, required=True)
    analyze.add_argument("--repo-root", type=Path, required=True)
    analyze.add_argument("--out", type=Path, required=True)
    analyze.add_argument("--bootstrap-replicates", type=int, default=10_000)
    analyze.add_argument("--bootstrap-seed", type=int, default=20260903)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "seal-inputs":
        source = (
            _read(args.source, "seal source")
            if args.source is not None
            else {"recovery_receipt": str(args.recovery_receipt.resolve())}
        )
        seal_inputs(source, output_path=args.out)
        return 0
    if args.out.exists():
        raise RuntimeError(f"refusing to overwrite analysis report: {args.out}")
    lock = _read(args.lock, "dataset lock")

    def gold_loader():
        from speech_aware_evidence_acquisition.data.audio2tool import (
            load_expected_calls,
        )

        return load_expected_calls(
            lock,
            args.data_root,
            repo_root=args.repo_root,
        )

    report = analyze_sealed_inputs(
        seal_path=args.seal,
        batch_summary_path=args.score_batch,
        gold_loader=gold_loader,
        bootstrap_replicates=args.bootstrap_replicates,
        bootstrap_seed=args.bootstrap_seed,
    )
    _write_new(args.out, report, "analysis report")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
