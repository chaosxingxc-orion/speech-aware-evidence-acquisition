#!/usr/bin/env python3
"""Helper steps of the ADV-1 runbook (``scripts/flights/batch/adv1_prepare.sh``).

MODEL-FREE. Zero frozen-core, tool, embedding, encoder, tokenizer, scorer, GPU
and network contacts: every byte read is an already-sealed local file (S3-3's
``pairs.json`` and the committed R01C roster receipt) and everything written is
ids, counts and digests. No utterance text, transcript, gold label, scenario,
action, entity or model output is read, printed or persisted anywhere here --
``pairs.json`` itself carries none (``scripts/analysis/stage3_rollout_score.py``
module docstring).

Two steps, both idempotent:

``roster``
    Write ``docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1
    .json``: the construction-role roster over exactly the rows S3-3 named as
    disagreeing. It is a PURE SELECTION of the R01C receipt -- every surviving
    item is the parent's item verbatim, in the parent's order -- exactly as
    R01C is a pure selection of R01
    (``scripts/build_slurp_stage3_construction_clean_subset.py``) and as
    ``SLURP-EVO-S1-PROPOSER-R01`` is a construction sub-roster for the proposer
    arm. It exists because ``construction-advantage-text`` is a
    construction-visible arm: ``contracts.gate_exposure
    ._require_construction_role_for_visible_targets`` refuses the touch unless
    the cell's own ``split_identity_hash`` is that of a COMMITTED
    ``roster_role='construction'`` receipt of carrier ``slurp``.

``report``
    Print the fill values for the ADV-1 fragments and write them as a
    ``roll1_fill_placeholders.py`` values file; with ``--experiment`` also
    insert the ``populations`` block ``core.flight.repin`` cross-checks against
    the recomputed split identity.

``smoke-roster``
    Write ``docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-smoke
    -4-v1.json``: the FIRST ``--rows`` items of the disagreeing receipt above,
    in that receipt's own order, as a construction-role roster of their own.
    The program rule is that every NEW module form flies a four-row smoke
    before its full cell, and ``construction-advantage-text`` is a
    construction-visible arm, so the smoke cell's OWN ``split_identity_hash``
    must also be a committed ``roster_role='construction'`` receipt --
    ``contracts.gate_exposure._require_construction_role_for_visible_targets``
    knows nothing about parent rosters and would refuse a four-row subset of
    one. Like ``roster`` this is a pure SELECTION: every surviving item is the
    parent's item verbatim, no rng is consulted, and no utterance text, gold
    label, scenario, action or model output is read, printed or persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_DEFAULT = Path(__file__).resolve().parents[3]

PARENT_ROSTER = "docs/receipts/rosters/slurp-stage3-construction-r01c.json"
ROSTER_OUT = "docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json"
ROSTER_ID = "SLURP-STAGE3-ADVANTAGE-R01C-DISAGREEING-V1"
SMOKE_ROSTER_OUT = (
    "docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-smoke-4-v1.json"
)
SMOKE_ROSTER_ID = "SLURP-STAGE3-ADVANTAGE-R01C-DISAGREEING-SMOKE-4-V1"
SMOKE_ROWS = 4
EXPERIMENT = "configs/experiment/slurp-native-stage3-advantage-r01-v1.json"
DATASET_FRAGMENT = "slurp-speech-native-stage3-construction-r01c"
CARRIER = "slurp"
SPEC = "docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md"


class Adv1PrepareError(RuntimeError):
    """An input is missing or does not have the shape this helper needs."""


def _import_repo(repo_root: Path):
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from speech_aware_evidence_acquisition.core import roster as roster_module  # noqa: PLC0415
    from speech_aware_evidence_acquisition.data import splits  # noqa: PLC0415

    return roster_module, splits


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Adv1PrepareError(f"{path} is unreadable: {error}") from error


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disagreeing_ids(pairs_document: Mapping[str, Any]) -> list[str]:
    """The ascending sample ids of ``pairs.json``'s disagreeing rows."""

    rows = pairs_document.get("pairs")
    if not isinstance(rows, list) or not rows:
        raise Adv1PrepareError("pairs.json carries no non-empty 'pairs' array")
    ids: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise Adv1PrepareError(f"pairs.json pairs[{index}] must be an object")
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise Adv1PrepareError(f"pairs.json pairs[{index}] has no sample_id")
        ids.append(sample_id)
    if len(set(ids)) != len(ids):
        raise Adv1PrepareError("pairs.json repeats a sample_id")
    count = pairs_document.get("count")
    if count is not None and count != len(ids):
        raise Adv1PrepareError(f"pairs.json count {count} != len(pairs) {len(ids)}")
    return sorted(ids)


def build_roster_receipt(
    *, parent: Mapping[str, Any], ids: list[str], pairs_pin: Mapping[str, Any], splits
) -> dict[str, Any]:
    """A pure selection of the parent receipt over ``ids``; no draw, no rng."""

    keep = set(ids)
    parent_items = parent.get("items")
    if not isinstance(parent_items, list) or not parent_items:
        raise Adv1PrepareError(f"{PARENT_ROSTER} carries no items")
    items = [item for item in parent_items if str(item["sample_id"]) in keep]
    missing = keep - {str(item["sample_id"]) for item in items}
    if missing:
        raise Adv1PrepareError(
            f"{len(missing)} disagreeing sample id(s) are not in {PARENT_ROSTER}: "
            f"{sorted(missing)[:3]}"
        )
    counts = dict(sorted(Counter(str(item["stratum"]) for item in items).items()))
    receipt: dict[str, Any] = {
        "schema": parent["schema"],
        "roster_id": ROSTER_ID,
        "carrier_lock_key": CARRIER,
        "split_role": "discovery",
        "roster_role": "construction",
        "seed": parent.get("seed"),
        "per_stratum": counts,
        "strata_counts": counts,
        "items": items,
        "excluded_count": len(parent_items) - len(items),
        "split_identity_hash": splits.split_identity_hash(splits.prefixed(CARRIER, ids)),
        "authority": (
            f"Stage-3 S3-4 ADV-1 ({SPEC} section S3-4): the semantic-advantage contact runs on "
            "exactly the rows S3-3 selected as disagreeing. construction-advantage-text is a "
            "construction-visible arm, so contracts.gate_exposure."
            "_require_construction_role_for_visible_targets requires this population to be a "
            "committed roster_role='construction' roster of its own; the precedent is "
            "SLURP-EVO-S1-PROPOSER-R01."
        ),
        "roster_role_note": (
            "construction: the arm sees this row's own construction gold and produces an "
            "artifact (an advantage statement), never an answer to an evaluated row "
            "(owner decision 82)."
        ),
        "draw_method": (
            "No draw. This receipt is a pure SELECTION of the parent receipt's frozen items: "
            "every surviving item is the parent's item verbatim, in the parent's order "
            "(ascending sample_id). The seed is the parent's and is carried for provenance "
            "only -- no rng is consulted anywhere in this build."
        ),
        "selection_rule": (
            "R01C restricted to the rows whose N=5 ROLL-1 rollout group disagreed "
            "(best-minus-worst official SLU-F1 > 0), as S3-3's pairs.json names them; order "
            "preserved."
        ),
        "generator": "scripts/flights/batch/adv1_prepare_steps.py",
        "parent": {
            "roster_id": parent.get("roster_id"),
            "count": len(parent_items),
            "relpath": PARENT_ROSTER,
            "split_identity_hash": parent.get("split_identity_hash"),
        },
        "selection_source": dict(pairs_pin),
        "offline_guard": {"attempted_targets": [], "outbound_connection_attempts": 0},
    }
    for carried in ("d1_supplement", "disjointness_proof", "knowledge_source_guard"):
        if carried in parent:
            receipt[carried] = parent[carried]
    return receipt


def cmd_roster(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    roster_module, splits = _import_repo(repo_root)
    pairs_path = Path(args.pairs)
    pairs_document = _read_json(pairs_path)
    ids = disagreeing_ids(pairs_document)
    parent = _read_json(repo_root / PARENT_ROSTER)
    roster_module.verify_roster(parent)
    pairs_pin = {
        "relpath": args.pairs_relpath,
        "root": "data",
        "sha256": sha256_file(pairs_path),
        "rollout_run_id": pairs_document.get("run_id"),
        "rollout_attempt_id": pairs_document.get("attempt_id"),
        "scorer_id": pairs_document.get("scorer_id"),
        # S3-4s (owner decision 106): which pairs.json payload version this
        # selection was made from. "saea-stage3-rollout-pairs-v2" is the one
        # that carries the per-row trajectory block ADV-1's v2 instruction
        # renders from; a file without the key is a pre-S3-4s v1 payload.
        "pairs_schema": pairs_document.get("pairs_schema", "saea-stage3-rollout-score-v1"),
    }
    receipt = build_roster_receipt(parent=parent, ids=ids, pairs_pin=pairs_pin, splits=splits)
    measured = roster_module.verify_roster(receipt)
    out_path = repo_root / args.roster_out
    if out_path.is_file():
        existing = _read_json(out_path)
        if existing.get("split_identity_hash") != measured:
            raise Adv1PrepareError(
                f"{args.roster_out} already exists with a different split identity "
                f"({existing.get('split_identity_hash')!r} vs {measured!r}); refusing to rewrite"
            )
        print(f"roster  {args.roster_out} already present and identical ({measured})")
    elif args.write:
        roster_module.write_roster(receipt, out_path)
        print(f"roster  wrote {args.roster_out} rows={len(ids)} split_identity={measured}")
    else:
        print(f"roster  (dry) would write {args.roster_out} rows={len(ids)} split_identity={measured}")
    print(f"roster  file_sha256={sha256_file(out_path) if out_path.is_file() else '(not written)'}")
    return 0


def build_smoke_roster_receipt(
    *, parent: Mapping[str, Any], rows: int, parent_relpath: str, parent_sha256: str, splits
) -> dict[str, Any]:
    """The first ``rows`` items of the disagreeing receipt, as a roster of their own."""

    parent_items = parent.get("items")
    if not isinstance(parent_items, list) or not parent_items:
        raise Adv1PrepareError(f"{parent_relpath} carries no items")
    if rows < 1 or rows > len(parent_items):
        raise Adv1PrepareError(
            f"--rows {rows} is outside 1..{len(parent_items)} for {parent_relpath}"
        )
    items = list(parent_items[:rows])
    ids = [str(item["sample_id"]) for item in items]
    counts = dict(sorted(Counter(str(item["stratum"]) for item in items).items()))
    receipt: dict[str, Any] = {
        "schema": parent["schema"],
        "roster_id": SMOKE_ROSTER_ID,
        "carrier_lock_key": CARRIER,
        "split_role": "discovery",
        "roster_role": "construction",
        "seed": parent.get("seed"),
        "per_stratum": counts,
        "strata_counts": counts,
        "items": items,
        "excluded_count": len(parent_items) - len(items),
        "split_identity_hash": splits.split_identity_hash(splits.prefixed(CARRIER, ids)),
        "authority": (
            f"Stage-3 S3-4 ADV-1 ({SPEC} section S3-4) plus the program's own four-row form "
            "smoke rule (study CLAUDE.md, owner 2026-09-03: a NEW module form flies a four-row "
            "smoke before its full cell). construction-advantage-text is a construction-visible "
            "arm, so contracts.gate_exposure._require_construction_role_for_visible_targets "
            "refuses the touch unless the FLYING cell's own split_identity_hash is that of a "
            "committed roster_role='construction' receipt; that gate knows nothing about parent "
            "rosters, so the four smoke rows need a committed receipt of their own."
        ),
        "roster_role_note": (
            "construction: the arm sees this row's own construction gold and produces an "
            "artifact (an advantage statement), never an answer to an evaluated row "
            "(owner decision 82)."
        ),
        "draw_method": (
            "No draw. This receipt is a pure SELECTION of the parent receipt's frozen items: "
            f"the FIRST {rows} items, in the parent's own order (ascending sample_id), each item "
            "verbatim. The seed is the parent's and is carried for provenance only -- no rng is "
            "consulted anywhere in this build, and no score, quality or label is read."
        ),
        "selection_rule": (
            f"the first {rows} rows, by the parent receipt's own order, of {ROSTER_ID} -- a "
            "structural form smoke, never a quality-based selection."
        ),
        "generator": "scripts/flights/batch/adv1_prepare_steps.py",
        "parent": {
            "roster_id": parent.get("roster_id"),
            "count": len(parent_items),
            "relpath": parent_relpath,
            "sha256": parent_sha256,
            "split_identity_hash": parent.get("split_identity_hash"),
        },
        "offline_guard": {"attempted_targets": [], "outbound_connection_attempts": 0},
    }
    for carried in (
        "d1_supplement",
        "disjointness_proof",
        "knowledge_source_guard",
        "selection_source",
    ):
        if carried in parent:
            receipt[carried] = parent[carried]
    return receipt


def cmd_smoke_roster(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    roster_module, splits = _import_repo(repo_root)
    parent_path = repo_root / args.parent
    parent = _read_json(parent_path)
    roster_module.verify_roster(parent)
    receipt = build_smoke_roster_receipt(
        parent=parent,
        rows=args.rows,
        parent_relpath=args.parent,
        parent_sha256=sha256_file(parent_path),
        splits=splits,
    )
    measured = roster_module.verify_roster(receipt)
    out_path = repo_root / args.roster_out
    if out_path.is_file():
        existing = _read_json(out_path)
        if existing.get("split_identity_hash") != measured:
            raise Adv1PrepareError(
                f"{args.roster_out} already exists with a different split identity "
                f"({existing.get('split_identity_hash')!r} vs {measured!r}); refusing to rewrite"
            )
        print(f"smoke-roster  {args.roster_out} already present and identical ({measured})")
    elif args.write:
        roster_module.write_roster(receipt, out_path)
        print(f"smoke-roster  wrote {args.roster_out} rows={args.rows} split_identity={measured}")
    else:
        print(
            f"smoke-roster  (dry) would write {args.roster_out} rows={args.rows} "
            f"split_identity={measured}"
        )
    present = sha256_file(out_path) if out_path.is_file() else "(not written)"
    print(f"smoke-roster  file_sha256={present}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    _roster_module, splits = _import_repo(repo_root)
    pairs_path = Path(args.pairs)
    pairs_document = _read_json(pairs_path)
    ids = disagreeing_ids(pairs_document)
    split_identity = splits.split_identity_hash(splits.prefixed(CARRIER, ids))
    values = {
        "PENDING_S3_3_PAIRS_JSON_RELPATH": args.pairs_relpath,
        "PENDING_S3_3_PAIRS_JSON_SHA256": sha256_file(pairs_path),
        "PENDING_S3_3_DISAGREEING_ROW_COUNT": len(ids),
        "PENDING_S3_3_DISAGREEING_SPLIT_ID": ROSTER_ID.removeprefix("SLURP-"),
        "PENDING_S3_3_DISAGREEING_SPLIT_IDENTITY_HASH": split_identity,
    }
    print(json.dumps({"stage": "adv1-fill-values", **values,
                      "rollout_run_id": pairs_document.get("run_id"),
                      "rollout_attempt_id": pairs_document.get("attempt_id")},
                     indent=2, sort_keys=True))
    out_path = Path(args.values_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"report  values -> {out_path}")

    if args.experiment:
        experiment_path = repo_root / args.experiment
        raw = io.open(experiment_path, encoding="utf-8", newline="").read()
        document = json.loads(raw)
        document["populations"] = [{"dataset_fragment": DATASET_FRAGMENT, "ids": ids}]
        text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        text = re.sub(
            r'"allowed_execution_stages": \[\s*((?:"[a-z-]+",?\s*)+)\]',
            lambda m: '"allowed_execution_stages": ['
            + ", ".join(json.dumps(s) for s in re.findall(r'"([a-z-]+)"', m.group(1)))
            + "]",
            text,
        )
        json.loads(text)
        if args.write:
            io.open(experiment_path, "w", encoding="utf-8", newline="").write(text)
            print(f"report  populations ({len(ids)} ids) -> {args.experiment}")
        else:
            print(f"report  (dry) would write populations ({len(ids)} ids) -> {args.experiment}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_DEFAULT))
    parser.add_argument("--write", action="store_true", help="write; the default is a dry read")
    sub = parser.add_subparsers(dest="command", required=True)

    roster = sub.add_parser("roster", help="write the disagreeing-row construction roster receipt")
    roster.add_argument("--pairs", required=True, help="absolute path to S3-3's pairs.json")
    roster.add_argument("--pairs-relpath", required=True, help="the same file, relative to the data root")
    roster.add_argument("--roster-out", default=ROSTER_OUT)
    roster.set_defaults(func=cmd_roster)

    report = sub.add_parser("report", help="print and write the ADV-1 fill values")
    report.add_argument("--pairs", required=True, help="absolute path to S3-3's pairs.json")
    report.add_argument("--pairs-relpath", required=True, help="the same file, relative to the data root")
    report.add_argument("--values-out", required=True, help="where to write the fill values JSON")
    report.add_argument("--experiment", default=EXPERIMENT, help="fragment to receive populations")
    report.set_defaults(func=cmd_report)

    smoke = sub.add_parser(
        "smoke-roster", help="write the four-row form-smoke construction roster receipt"
    )
    smoke.add_argument("--parent", default=ROSTER_OUT, help="the disagreeing-row receipt")
    smoke.add_argument("--rows", type=int, default=SMOKE_ROWS)
    smoke.add_argument("--roster-out", default=SMOKE_ROSTER_OUT)
    smoke.set_defaults(func=cmd_smoke_roster)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Adv1PrepareError as error:
        print(f"adv1_prepare_steps: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
