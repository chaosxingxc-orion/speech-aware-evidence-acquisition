#!/usr/bin/env python3
"""Level-1 read for the same-flight Perception-branch instrument (same-flight instrument phase
2, merge set C, item 4, design docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-
perception-variants-design.md section 2, "What the column read measures").

WHAT THIS READS. Per row, every declared branch's own candidate-rank list
(``native_episode_receipt.perception_branches.branches[].candidate_intent_ids``, ordered) plus a
gold intent id supplied by the caller (offline only -- this module never reads a gold label
itself; it is handed a ``{sample_id: gold_intent_id}`` mapping by whatever caller has already
loaded one, keeping this module's own boundary "no gold label of any evaluated row is read"
model-free and I/O-free):

* **gold rank per branch** (1/2/3/absent) and **present** (gold anywhere on the list);
* **top1** (gold ranked first);
* the **paired per-row** ``top1``/``present`` difference between a branch and the delivering
  branch (A), bootstrapped by row (``analysis.bootstrap.paired_cluster_bootstrap``, the SAME
  10,000-replicate, seed-20260807, 95 %-CI primitive the node-information-gain ledger driver
  (``scripts/analysis/slurp_node_gain_ledger.py``) already uses -- design section 4, "Resampling");
* the SAME read clustered by UTTERANCE id instead of row id, reported BESIDE the row-level read,
  never in its place (design section 2).

REFUSAL (item 1's own scoping): :func:`assert_a_reproduces_ledger_counts` refuses the whole read,
before any B/T comparison, unless branch A's own rank-1/2/3 rates over this read reproduce the
node-information-gain ledger's own counts within a tolerance -- a genuine disagreement means the
read roster or A's own construction has drifted from what the ledger measured (design section 3,
AT-P1: A's own request is byte-identical to a branch-free flight's), and the read must stop rather
than compare B or T against an A that is not the AGREE arm the ledger characterised.

ZERO CONTACT, ZERO GOLD READ OF ITS OWN. This module performs no model, server, GPU, network,
tokenizer or file I/O of any kind on its own critical statistical path: every function here is a
pure transform over rows and a gold mapping the CALLER already holds. A thin CLI (``main``) exists
only to glue a JSONL bundle and a JSON gold map together for a human running this by hand; the
statistical functions are what a caller-side script (or a test) should import and call directly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.bootstrap import (  # noqa: E402
    paired_cluster_bootstrap,
)

#: The SAME bootstrap constants scripts/analysis/slurp_node_gain_ledger.py already uses (design
#: section 4, "Resampling": "10,000 draws").
BOOT_SEED = 20260807
BOOT_N = 10_000
BOOT_LEVEL = 0.95


class PerceptionBranchReadError(ValueError):
    """A row, a gold mapping or a reproduction check is invalid for this read."""


def branch_gold_rank(candidate_intent_ids: Sequence[str], gold_intent_id: str) -> int | None:
    """Gold's 1-based rank in ONE branch's own ordered candidate list, or ``None`` when gold is
    off the list entirely (design section 2: "gold's rank in the note (1/2/3/absent)")."""

    for index, candidate in enumerate(candidate_intent_ids):
        if candidate == gold_intent_id:
            return index + 1
    return None


def branch_row_outcome(candidate_intent_ids: Sequence[str], gold_intent_id: str) -> dict[str, object]:
    """``{rank, present, top1}`` for one branch's own note on one row."""

    rank = branch_gold_rank(candidate_intent_ids, gold_intent_id)
    return {"rank": rank, "present": rank is not None, "top1": rank == 1}


def level1_row_outcomes(row: Mapping[str, object], gold_intent_id: str) -> dict[str, dict[str, object]]:
    """``{branch_id: {rank, present, top1}}`` for every declared branch of ONE sealed row."""

    episode = row.get("native_episode_receipt")
    branches = episode.get("perception_branches") if isinstance(episode, Mapping) else None
    if not isinstance(branches, Mapping):
        raise PerceptionBranchReadError(
            f"row {row.get('sample_id')!r} carries no perception_branches receipt"
        )
    rows = branches.get("branches")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise PerceptionBranchReadError(
            f"row {row.get('sample_id')!r} perception_branches has no ordered branches"
        )
    outcomes: dict[str, dict[str, object]] = {}
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        branch_id = item.get("branch_id")
        candidates = item.get("candidate_intent_ids")
        if not isinstance(branch_id, str) or not isinstance(candidates, Sequence):
            continue
        outcomes[branch_id] = branch_row_outcome(candidates, gold_intent_id)
    return outcomes


def _paired_bootstrap_over(
    keyed_diff: Mapping[str, float], *, n_replicates: int = BOOT_N,
) -> dict[str, object]:
    ids = sorted(keyed_diff)
    if not ids:
        raise PerceptionBranchReadError(
            "no row (or utterance) carried both a gold label and both branches"
        )
    result = paired_cluster_bootstrap(
        sample_ids=ids,
        statistic=lambda xs: 100.0 * sum(keyed_diff[x] for x in xs) / len(xs),
        n_replicates=n_replicates, seed=BOOT_SEED, ci_level=BOOT_LEVEL,
    )
    return {
        "n": len(ids), "point_pp": round(result.point_estimate, 4),
        "ci95": [round(result.ci_low, 4), round(result.ci_high, 4)],
    }


def _per_row_metric_diff(
    rows: Sequence[Mapping[str, object]], gold_by_sample: Mapping[str, str], *,
    branch_id: str, against: str, metric: str,
) -> dict[str, float]:
    diffs: dict[str, float] = {}
    for row in rows:
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str):
            continue
        gold = gold_by_sample.get(sample_id)
        if gold is None:
            continue
        outcomes = level1_row_outcomes(row, gold)
        if branch_id not in outcomes or against not in outcomes:
            continue
        diffs[sample_id] = float(outcomes[branch_id][metric]) - float(outcomes[against][metric])
    return diffs


def paired_top1_read(
    rows: Sequence[Mapping[str, object]], gold_by_sample: Mapping[str, str], *,
    branch_id: str, against: str = "A",
) -> dict[str, object]:
    """The paired per-row ``top1`` difference between ``branch_id`` and ``against`` (design
    section 2: "Primary: paired per-row top1 difference B - A; null T - A")."""

    diffs = _per_row_metric_diff(rows, gold_by_sample, branch_id=branch_id, against=against, metric="top1")
    discordant = sum(1 for value in diffs.values() if value != 0.0)
    return {"branch_id": branch_id, "against": against, "metric": "top1", "discordant": discordant,
            **_paired_bootstrap_over(diffs)}


def paired_present_read(
    rows: Sequence[Mapping[str, object]], gold_by_sample: Mapping[str, str], *,
    branch_id: str, against: str = "A",
) -> dict[str, object]:
    """The paired per-row ``present`` (gold-on-list) difference -- P-SV-2's own declared primary
    metric (design section 6, O4 ruling: "present" as `stage3_measurement` primary)."""

    diffs = _per_row_metric_diff(
        rows, gold_by_sample, branch_id=branch_id, against=against, metric="present",
    )
    return {"branch_id": branch_id, "against": against, "metric": "present", **_paired_bootstrap_over(diffs)}


def twin_null_bar(rows: Sequence[Mapping[str, object]], gold_by_sample: Mapping[str, str]) -> dict[str, object]:
    """``|T - A|`` and its half-width (design section 2: "bar |T - A| + its half-width (phase-1
    law)") -- the within-flight A/A null every same-flight-perception-variant read requires."""

    read = paired_top1_read(rows, gold_by_sample, branch_id="T", against="A")
    half_width = (read["ci95"][1] - read["ci95"][0]) / 2.0
    return {**read, "abs_point_pp": abs(read["point_pp"]), "half_width_pp": round(half_width, 4)}


def utterance_id(sample_id: str) -> str:
    """The utterance identity a row's own sample id is grouped under for the utterance-level
    read (W3a's own convention: the first three colon-separated segments)."""

    return ":".join(sample_id.split(":")[:3])


def utterance_level_top1_read(
    rows: Sequence[Mapping[str, object]], gold_by_sample: Mapping[str, str], *,
    branch_id: str, against: str = "A",
) -> dict[str, object]:
    """The SAME paired ``top1`` read, clustered by utterance id instead of row id -- reported
    BESIDE the row-level read, never in its place (design section 2)."""

    per_row = _per_row_metric_diff(rows, gold_by_sample, branch_id=branch_id, against=against, metric="top1")
    by_utterance: dict[str, list[float]] = {}
    for sample_id, diff in per_row.items():
        by_utterance.setdefault(utterance_id(sample_id), []).append(diff)
    per_utterance_mean = {utt: sum(values) / len(values) for utt, values in by_utterance.items()}
    return {"branch_id": branch_id, "against": against, "metric": "top1", "clustering": "utterance",
            **_paired_bootstrap_over(per_utterance_mean)}


def render_branch_column(row: Mapping[str, object], branch_id: str) -> dict[str, object]:
    """One branch's own LEVEL-1 column (design section 2): the row it belongs to, its own note
    and response digests, and its ordered candidate list -- never an ``admitted`` field. A column
    is custody kept for the READ, not a delivered, scored output row; only a delivered row is
    ever admitted (AT-P8: :func:`assert_column_package_never_admits`).
    """

    episode = row.get("native_episode_receipt")
    branches = episode.get("perception_branches") if isinstance(episode, Mapping) else None
    rows = branches.get("branches") if isinstance(branches, Mapping) else None
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise PerceptionBranchReadError(
            f"row {row.get('sample_id')!r} carries no perception_branches receipt"
        )
    for item in rows:
        if isinstance(item, Mapping) and item.get("branch_id") == branch_id:
            return {
                "sample_id": row.get("sample_id"),
                "branch_id": branch_id,
                "response_text_sha256": item.get("response_text_sha256"),
                "note_sha256": item.get("note_sha256"),
                "candidate_intent_ids": list(item.get("candidate_intent_ids") or ()),
            }
    raise PerceptionBranchReadError(f"branch {branch_id!r} is not in this row's receipt")


def stub_score_column(column: Mapping[str, object], gold_intent_id: str) -> dict[str, object]:
    """A minimal stand-in scorer for the column-paired-read contract (AT-P5): correct iff the
    column's own TOP candidate equals gold. A real cell's own OFFICIAL scorer (SLURP's
    ``evaluate.py``) replaces this at read time -- this function exists only to prove the
    render -> score -> paired-read pipeline end to end on a fake sealed run, never as a
    substitute for the official number.
    """

    candidates = column.get("candidate_intent_ids") or ()
    top = candidates[0] if candidates else None
    return {
        "sample_id": column.get("sample_id"), "branch_id": column.get("branch_id"),
        "correct": top == gold_intent_id,
    }


def column_paired_read(
    rows: Sequence[Mapping[str, object]], gold_by_sample: Mapping[str, str], *,
    branch_id: str, against: str = "A",
    scorer: Callable[[Mapping[str, object], str], Mapping[str, object]] = stub_score_column,
) -> dict[str, object]:
    """Render both branches' columns, score each with ``scorer``, and bootstrap the paired
    ``correct`` difference by row (AT-P5's own "column render, stub scoring and the column
    paired read")."""

    diffs: dict[str, float] = {}
    for row in rows:
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str):
            continue
        gold = gold_by_sample.get(sample_id)
        if gold is None:
            continue
        left = scorer(render_branch_column(row, branch_id), gold)
        right = scorer(render_branch_column(row, against), gold)
        diffs[sample_id] = float(bool(left["correct"])) - float(bool(right["correct"]))
    return {"branch_id": branch_id, "against": against, "metric": "column_correct",
            **_paired_bootstrap_over(diffs)}


def assert_column_package_never_admits(column: Mapping[str, object]) -> None:
    """AT-P8: a column package never emits ``admitted`` -- that verdict belongs to a delivered,
    scored OUTPUT ROW (``core.bundle.outputs``), never to a branch's own custody column."""

    if "admitted" in column:
        raise PerceptionBranchReadError(
            "a column package must never carry its own 'admitted' verdict"
        )


def level2_answer_column(row: Mapping[str, object], branch_id: str) -> dict[str, object]:
    """One branch's LEVEL-2 answer column (design section 3, "Level 2"): the branch's own Solver
    contact identity and response digest, and the candidate-supply ids that contact's slot
    contract was re-resolved from. Refuses a branch that carries no level-2 fields at all.
    """

    episode = row.get("native_episode_receipt")
    branches = episode.get("perception_branches") if isinstance(episode, Mapping) else None
    rows = branches.get("branches") if isinstance(branches, Mapping) else None
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise PerceptionBranchReadError(
            f"row {row.get('sample_id')!r} carries no perception_branches receipt"
        )
    for item in rows:
        if isinstance(item, Mapping) and item.get("branch_id") == branch_id:
            if "solver_response_text_sha256" not in item:
                raise PerceptionBranchReadError(
                    f"branch {branch_id!r} carries no level-2 Solver column"
                )
            return {
                "sample_id": row.get("sample_id"), "branch_id": branch_id,
                "solver_contact_id": item.get("solver_contact_id"),
                "solver_response_text_sha256": item.get("solver_response_text_sha256"),
                "candidate_supply_value_ids": list(item.get("candidate_supply_value_ids") or ()),
            }
    raise PerceptionBranchReadError(f"branch {branch_id!r} is not in this row's receipt")


def assert_a_level2_column_equals_delivery(row: Mapping[str, object]) -> None:
    """AT-P7: A's level-2 column equals the sealed first Solver visit after the normaliser.

    A spends no NEW Solver contact at level 2 (design section 3, "Level 2": "A's column is A's
    own first Solver answer"), so branch A's own ``solver_response_text_sha256`` must equal the
    delivered row's own (post-normaliser) ``response_text_sha256`` -- the SAME field a delivered
    row's own delivery-time normalisation (E11) already produced.
    """

    a_column = level2_answer_column(row, "A")
    delivered = row.get("response_text_sha256")
    if a_column["solver_response_text_sha256"] != delivered:
        raise PerceptionBranchReadError(
            "branch A's level-2 column does not equal the sealed row's own delivered response "
            f"({a_column['solver_response_text_sha256']!r} != {delivered!r})"
        )


def assert_a_reproduces_ledger_counts(
    rows: Sequence[Mapping[str, object]], gold_by_sample: Mapping[str, str], *,
    expected_rank1_pct: float, expected_rank2_pct: float, expected_rank3_pct: float,
    tolerance_pct: float = 0.5,
) -> dict[str, object]:
    """Refuse the whole read unless branch A's own rank distribution reproduces the node
    ledger's own P-node counts (docs/results/2026-09-28-slurp-node-information-gain-ledger.md
    section 0: 97.57 / 26.98 / 12.0 % at rank 1/2/3) within ``tolerance_pct``.

    Called BEFORE any B/T comparison (item 1's own scope): a mismatch means the read roster or
    the branch group's own A construction has drifted from what the ledger characterised, and no
    comparison against a non-reproducing A can be trusted.
    """

    counts = {1: 0, 2: 0, 3: 0}
    other = 0
    total = 0
    for row in rows:
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str):
            continue
        gold = gold_by_sample.get(sample_id)
        if gold is None:
            continue
        outcomes = level1_row_outcomes(row, gold)
        if "A" not in outcomes:
            continue
        total += 1
        rank = outcomes["A"]["rank"]
        if rank in (1, 2, 3):
            counts[rank] += 1
        else:
            other += 1
    if total == 0:
        raise PerceptionBranchReadError("no row carried a gold label for branch A's own rank")
    observed = {rank: 100.0 * count / total for rank, count in counts.items()}
    expected = {1: expected_rank1_pct, 2: expected_rank2_pct, 3: expected_rank3_pct}
    for rank, expected_pct in expected.items():
        if abs(observed[rank] - expected_pct) > tolerance_pct:
            raise PerceptionBranchReadError(
                f"branch A's own rank-{rank} rate {observed[rank]:.2f}% disagrees with the node "
                f"ledger's {expected_pct:.2f}% by more than {tolerance_pct} pp over {total} rows -- "
                "the read roster or A's own construction has drifted from the ledger's"
            )
    return {"observed_pct": observed, "total": total, "other": other}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--outputs", type=Path, required=True, help="sealed outputs JSONL")
    parser.add_argument("--gold", type=Path, required=True, help="{sample_id: gold_intent_id} JSON")
    parser.add_argument("--branch", required=True, help="the B (or T) branch id to read against A")
    parser.add_argument("--against", default="A")
    parser.add_argument("--metric", choices=("top1", "present"), default="top1")
    args = parser.parse_args(argv)

    rows = [json.loads(line) for line in args.outputs.read_text(encoding="utf-8").splitlines() if line]
    gold_by_sample = json.loads(args.gold.read_text(encoding="utf-8"))
    read_fn: Callable[..., dict[str, object]] = (
        paired_top1_read if args.metric == "top1" else paired_present_read
    )
    result = read_fn(rows, gold_by_sample, branch_id=args.branch, against=args.against)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
