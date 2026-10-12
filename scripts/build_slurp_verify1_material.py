#!/usr/bin/env python
"""Build the VERIFY-1 prepared-material record: COUNTS AND PERMUTATIONS ONLY.

Cell VERIFY-1 (Stage-3 board route F11) shows the frozen core, per row, the
five sealed ROLL-1 Solver candidates of that row and asks it to pick one. The
candidate block itself is rendered at flight time, from the sealed bundle and
the pinned permutation seed, by
``rails.phase_material.load_sealed_sample_groups`` -- nothing is prepared into
the request. What this script prepares is the READ's half of that: the per-row
record that says which sealed sample index sat in which POSITION, how many
DISTINCT answers the row rendered, and how many of its samples failed to parse.
Without it a chosen position is an unresolvable number.

It is therefore deliberately NOT an input to any contact:

* nothing in ``configs/`` pins this document, and no flight code opens it. The
  flight derives the same permutation from ``(manifest bytes, permutation
  seed)`` through the same function, so the record and the wire agree by
  construction rather than by pinning, and
  ``tests/unit/test_sealed_samples_balanced_order.py`` proves that agreement;
* it persists NO model answer, utterance, transcript or gold. Per row it writes
  the sample id, the permutation, the sha256 of each rendered candidate, the
  sha256 of the rendered block, the distinct-answer count and the parse counts.
  Candidate TEXT never leaves the flight path.

All 625 rows are the primary population. Report the 420 content-distinct rows, 414 content-distinct rows with all candidates parsed, 205 identical-answer controls, and 225 row-F1-disagreeing rows separately. Preserve the six rows containing nine malformed source samples; flag their canonical empty renderings. Invalid verifier responses fall back to sealed source sample index 0. Do not exclude failures from complete-roster estimates. Position histograms are descriptive, not tests of semantic selection.

Zero model, tokenizer, encoder, embedder, scorer, server, GPU, network and
paid-API contacts. The only bytes read are the committed R01C roster receipt and
the sealed ROLL-1 bundle under ``SPEECHRL_DATA_DIR``.

Usage (from a worktree, in WSL)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src \\
    SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT \\
    python -B scripts/build_slurp_verify1_material.py \\
      --repo-root $REPO --data-root $SPEECHRL_DATA_DIR [--check] [--json out.json]

``--check`` re-derives everything and fails if the committed record would
change, which is what a gate or a re-pin cycle runs.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys
from pathlib import Path

MATERIAL_SCHEMA = "saea-slurp-verify1-material-v1"

#: The sealed grouped-Solver bundle every candidate block is rendered from,
#: relative to the DATA root. Cell ROLL-1's own generation attempt.
ROLLOUT_MANIFEST_RELPATH = (
    "runs/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1/"
    "attempt-slurp-native-stage3-rollout-r01-generation-v1/"
    "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1.run-manifest.json"
)
ROLLOUT_MANIFEST_SHA256 = (
    "87ba077dfb2c053679b1befa4f36e98021a3efde55783a3b293f77d56381790a"
)
ROLLOUT_RUN_ID = "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1"
ROLLOUT_ATTEMPT_ID = "attempt-slurp-native-stage3-rollout-r01-generation-v1"

ROSTER_RELPATH = "docs/receipts/rosters/slurp-stage3-construction-r01c.json"
ROSTER_SHA256 = "e8abc65ba4626cccb4aae9d2eb1bd73f077a6e9a407b3dba9c18bbe4c03eeddd"
ROSTER_ID = "SLURP-STAGE3-CONSTRUCTION-R01C"
SPLIT_IDENTITY_HASH = (
    "f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515"
)

#: The pinned presentation-order seed. It rides the cell's config hash through
#: ``phase_material.choose.predecessor_source.permutation_seed`` and nothing
#: else decides a position.
PERMUTATION_SEED = 20260925
EXPECTED_SAMPLE_COUNT = 5

PHASE_NAME = "choose"
OUT_RELPATH = "docs/receipts/verify1/slurp-stage3-verify-1-material-v1.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(document: object) -> str:
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _roster_ids(repo_root: Path) -> tuple[str, ...]:
    path = repo_root / ROSTER_RELPATH
    measured = _sha256_file(path)
    if measured != ROSTER_SHA256:
        raise SystemExit(
            f"roster receipt {path} hashes to {measured}, not the pinned "
            f"{ROSTER_SHA256}"
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document["items"]
    ids = tuple(
        str(item["sample_id"]) if isinstance(item, dict) else str(item)
        for item in items
    )
    if len(set(ids)) != len(ids):
        raise SystemExit("roster receipt carries duplicate sample ids")
    return ids


def build(repo_root: Path, data_root: Path) -> dict:
    from speech_aware_evidence_acquisition.rails.phase_material import (
        SEALED_SAMPLES_HEADER,
        load_sealed_sample_groups,
    )

    manifest = data_root / ROLLOUT_MANIFEST_RELPATH
    measured = _sha256_file(manifest)
    if measured != ROLLOUT_MANIFEST_SHA256:
        raise SystemExit(
            f"sealed rollout manifest {manifest} hashes to {measured}, not the "
            f"pinned {ROLLOUT_MANIFEST_SHA256}"
        )
    ids = _roster_ids(repo_root)
    groups = load_sealed_sample_groups(
        manifest,
        expected_sha256=ROLLOUT_MANIFEST_SHA256,
        phase_name=PHASE_NAME,
        producer_policy_id=ROLLOUT_RUN_ID,
        sample_ids=ids,
        expected_sample_count=EXPECTED_SAMPLE_COUNT,
        permutation_seed=PERMUTATION_SEED,
        permutation_rule="balanced-block-v1",
    )
    rows = []
    histogram: collections.Counter[int] = collections.Counter()
    position_of_index: dict[int, collections.Counter[int]] = {
        index: collections.Counter() for index in range(EXPECTED_SAMPLE_COUNT)
    }
    unparseable_rows = 0
    unparseable_samples = 0
    block_chars: list[int] = []
    for sample_id in ids:
        group = groups[sample_id]
        histogram[group.distinct_answers] += 1
        for position, index in enumerate(group.permutation):
            position_of_index[index][position + 1] += 1
        if group.parse_failed:
            unparseable_rows += 1
            unparseable_samples += group.parse_failed
        chars = len(group.state.content)
        block_chars.append(chars)
        rows.append(
            {
                "sample_id": sample_id,
                "permutation": list(group.permutation),
                "rendered_sha256": list(group.rendered_sha256),
                "block_chars": chars,
                "block_sha256": hashlib.sha256(
                    group.state.content.encode("utf-8")
                ).hexdigest(),
                "distinct_answers": group.distinct_answers,
                "parse_ok": group.parse_ok,
                "parse_failed": group.parse_failed,
            }
        )
    informative = [row for row in rows if row["distinct_answers"] >= 2]
    control = [row for row in rows if row["distinct_answers"] == 1]
    informative_clean = [row for row in informative if row["parse_failed"] == 0]
    document = {
        "schema": MATERIAL_SCHEMA,
        "what_this_is": (
            "The VERIFY-1 read's per-row resolution table: which sealed ROLL-1 "
            "Solver sample index sat in which 1-based POSITION of the candidate "
            "block the frozen core was shown, plus that row's distinct-answer and "
            "parse counts. Model-free: counts, ids, permutations and hashes only. "
            "No candidate text, utterance, transcript or gold is persisted, and no "
            "flight reads this file -- the wire derives the same permutation from "
            "the sealed manifest bytes and the pinned seed."
        ),
        "source": {
            "rollout_run_id": ROLLOUT_RUN_ID,
            "rollout_attempt_id": ROLLOUT_ATTEMPT_ID,
            "manifest_relpath": ROLLOUT_MANIFEST_RELPATH,
            "manifest_sha256": ROLLOUT_MANIFEST_SHA256,
            "roster_relpath": ROSTER_RELPATH,
            "roster_sha256": ROSTER_SHA256,
            "roster_id": ROSTER_ID,
            "split_identity_hash": SPLIT_IDENTITY_HASH,
        },
        "presentation": {
            "permutation_seed": PERMUTATION_SEED,
            "permutation_rule_id": "balanced-block-v1",
            "expected_sample_count": EXPECTED_SAMPLE_COUNT,
            "phase_name": PHASE_NAME,
            "block_header": SEALED_SAMPLES_HEADER,
            "permutation_rule": (
                "balanced-block-v1: rank complete source roster by seed-bound hash; "
                "each block uses all cyclic rotations of a seeded Fisher-Yates permutation; "
                "derive smoke rows from the same full-roster assignment."
            ),
        },
        "populations": {
            "rows": len(rows),
            "informative_content_distinct": len(informative),
            "informative_content_distinct_all_parsed": len(informative_clean),
            "position_bias_control_single_answer": len(control),
            "rows_with_unparseable_sample": unparseable_rows,
            "unparseable_samples": unparseable_samples,
            "distinct_answer_histogram": {
                str(key): histogram[key] for key in sorted(histogram)
            },
            "ruling": 'All 625 rows are the primary population. Report the 420 content-distinct rows, 414 content-distinct rows with all candidates parsed, 205 identical-answer controls, and 225 row-F1-disagreeing rows separately. Preserve the six rows containing nine malformed source samples; flag their canonical empty renderings. Invalid verifier responses fall back to sealed source sample index 0. Do not exclude failures from complete-roster estimates. Position histograms are descriptive, not tests of semantic selection.',
        },
        "block_size": {
            "max_chars": max(block_chars),
            "mean_chars": round(sum(block_chars) / len(block_chars), 4),
            "min_chars": min(block_chars),
        },
        "position_of_sample_index": {
            str(index): {
                str(position): count
                for position, count in sorted(counter.items())
            }
            for index, counter in sorted(position_of_index.items())
        },
        "rows": rows,
    }
    document["rows_sha256"] = hashlib.sha256(
        _canonical(rows).encode("utf-8")
    ).hexdigest()
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)
    if not args.data_root:
        parser.error("--data-root or SPEECHRL_DATA_DIR is required")
    repo_root = Path(args.repo_root).resolve()
    document = build(repo_root, Path(args.data_root))
    rendered = json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    out = repo_root / OUT_RELPATH
    if args.check:
        if not out.is_file() or out.read_text(encoding="utf-8") != rendered:
            print(f"OUT OF DATE: {OUT_RELPATH}", file=sys.stderr)
            return 1
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8", newline="\n")
    summary = {
        "out": OUT_RELPATH,
        "out_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "rows_sha256": document["rows_sha256"],
        "populations": document["populations"],
        "block_size": document["block_size"],
        "position_of_sample_index": document["position_of_sample_index"],
    }
    text = json.dumps(summary, indent=1, sort_keys=True)
    print(text)
    if args.json:
        Path(args.json).write_text(text + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
