#!/usr/bin/env python3
"""Helper steps of the delta-store runbook (``scripts/flights/batch/adv1_to_deltas.sh``).

MODEL-FREE. Zero frozen-core, tool, embedding, encoder, tokenizer, scorer, GPU
and network contacts. No statement text, utterance text, gold label or model
output is printed or persisted by this helper -- only relpaths, counts and
digests, the discipline ``scripts/build_slurp_stage3_delta_store.py`` keeps for
its own console output.

Two steps:

``registration``
    Materialise a committed release-registration TEMPLATE into a RUNNABLE copy
    under the data root, with the authored document's real digest and the
    scope / permitted-roster digests root's own S3-5 preparations produced.
    ``core.semantic_knowledge_preparation.prepare_semantic_knowledge_store``
    verifies every one of those pins by SHA-256, so the template -- which
    carries ``PENDING_`` tokens -- is never passed to it and is never edited in
    place. The forbidden-roster pins the template carries are re-verified
    against the committed receipts and a mismatch fails closed.

``cell1-values``
    Read the released store's ``release.json`` / ``snapshot.json`` (and the
    twin's) and write the CELL-1 fill values file
    ``scripts/flights/batch/roll1_fill_placeholders.py`` consumes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_DEFAULT = Path(__file__).resolve().parents[3]
TEMPLATE_KEYS_DROPPED = ("template_note", "what_the_pins_are")


class Adv1DeltaStepError(RuntimeError):
    """An input is missing or does not have the shape this helper needs."""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Adv1DeltaStepError(f"{path} is unreadable: {error}") from error


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise Adv1DeltaStepError(f"missing {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(pin: Mapping[str, Any], *, repo_root: Path, data_root: Path) -> Path:
    root = str(pin.get("root", "data"))
    base = repo_root if root in ("repo", "repository") else data_root
    return base / str(pin["relpath"])


def cmd_registration(args: argparse.Namespace) -> int:
    repo_root, data_root = Path(args.repo_root), Path(args.data_root)
    registration = _read_json(repo_root / args.template)
    for key in TEMPLATE_KEYS_DROPPED:
        registration.pop(key, None)

    registration["source_split_identity_hash"] = args.source_split_identity_hash
    registration["authored_source"]["sha256"] = sha256_file(
        _resolve(registration["authored_source"], repo_root=repo_root, data_root=data_root)
    )
    registration["construction_scope"]["sha256"] = sha256_file(
        _resolve(registration["construction_scope"], repo_root=repo_root, data_root=data_root)
    )
    registration["permitted_roster"]["sha256"] = sha256_file(
        _resolve(registration["permitted_roster"], repo_root=repo_root, data_root=data_root)
    )
    for index, pin in enumerate(registration.get("forbidden_rosters", ())):
        measured = sha256_file(_resolve(pin, repo_root=repo_root, data_root=data_root))
        if measured != pin["sha256"]:
            raise Adv1DeltaStepError(
                f"forbidden_rosters[{index}] {pin['relpath']} is {measured}, the template pins "
                f"{pin['sha256']}; refusing to release against a moved evaluation roster"
            )

    text = json.dumps(registration, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if "PENDING_" in text:
        raise Adv1DeltaStepError("the runnable registration still carries a PENDING_ token")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({
        "stage": "registration",
        "out": str(out_path),
        "sha256": sha256_file(out_path),
        "output_namespace": registration["output_namespace"],
        "authored_source_sha256": registration["authored_source"]["sha256"],
    }, indent=2, sort_keys=True))
    return 0


def cmd_cell1_values(args: argparse.Namespace) -> int:
    data_root = Path(args.data_root)
    values = {
        "PENDING_S3_5_RELEASE_JSON_SHA256": sha256_file(data_root / args.release_relpath),
        "PENDING_S3_5_SNAPSHOT_JSON_SHA256": sha256_file(data_root / args.snapshot_relpath),
        "PENDING_S3_6_TWIN_RELEASE_JSON_SHA256": sha256_file(data_root / args.twin_release_relpath),
        "PENDING_S3_6_TWIN_SNAPSHOT_JSON_SHA256": sha256_file(data_root / args.twin_snapshot_relpath),
    }
    print(json.dumps({
        "stage": "cell1-fill-values",
        "release_relpath": args.release_relpath,
        "snapshot_relpath": args.snapshot_relpath,
        "twin_release_relpath": args.twin_release_relpath,
        "twin_snapshot_relpath": args.twin_snapshot_relpath,
        **values,
    }, indent=2, sort_keys=True))
    out_path = Path(args.values_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"cell1-values  values -> {out_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_DEFAULT))
    parser.add_argument("--data-root", required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    registration = sub.add_parser("registration", help="materialise a runnable release registration")
    registration.add_argument("--template", required=True, help="committed template, repo-root relative")
    registration.add_argument("--out", required=True, help="runnable copy, an absolute path under the data root")
    registration.add_argument(
        "--source-split-identity-hash", required=True,
        help="the ADV-1 population's split identity (the disagreeing-row construction roster's)",
    )
    registration.set_defaults(func=cmd_registration)

    values = sub.add_parser("cell1-values", help="write the CELL-1 fill values from the two releases")
    values.add_argument("--release-relpath", default="knowledge/slurp/semantic/stage3-deltas-v1/release.json")
    values.add_argument("--snapshot-relpath", default="knowledge/slurp/semantic/stage3-deltas-v1/snapshot.json")
    values.add_argument("--twin-release-relpath", default="knowledge/slurp/semantic/stage3-deltas-twin-v1/release.json")
    values.add_argument("--twin-snapshot-relpath", default="knowledge/slurp/semantic/stage3-deltas-twin-v1/snapshot.json")
    values.add_argument("--values-out", required=True)
    values.set_defaults(func=cmd_cell1_values)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Adv1DeltaStepError as error:
        print(f"adv1_to_deltas_steps: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
