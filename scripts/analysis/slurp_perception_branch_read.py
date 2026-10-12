#!/usr/bin/env python3
"""Level-1 read for the same-flight Perception-branch instrument (same-flight instrument phase
2, merge set C, item 4, design docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-
perception-variants-design.md section 2, "What the column read measures").

TWO CLI MODES.

* Legacy (``--outputs --gold --branch [--against] [--metric]``): the hand-run level-1 glue below,
  unchanged.
* RECIPE mode (``--recipe --run --attempt --roster --level {1,2} --analysis-root --data-root
  --repo-root --lock [--rescore] [--dry-run]``), driven by ``scripts/flights/psv/psv_read.sh``:
  the registered P-SV-K branch read (owner decision 184). It resolves the sealed attempt from the
  recipe (the seal-only attempt for P-SV-1, whose manifest must name the registered predecessor
  trace), reads every branch record from the sealed outputs (schema v1 or v2), refuses unless the
  delivering branch's note list equals the node-ledger driver's own P-node parse of the same
  note, loads gold ONLY through the governed TRAIN loader (``data.slurp.load_slurp_split``),
  computes the level-1 tables and paired reads, and at level 2 renders and scores each branch's
  first-visit Solver column ONCE (``stage3_rollout_score.py --mode perception-branches``, the
  official scorer through ``score_complete_derived_copy``; idempotent unless ``--rescore``), runs
  the twin-null and branch passes through ``stage3_paired_read.py`` column arms, applies the
  registered decision rule, and writes one hashes-and-numbers receipt
  (``saea-perception-branch-read-v1``). ``--dry-run`` stops before any gold or scorer use and
  prints counts only.

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
import os

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


#: The receipt's own ``note_parse_status`` values that carry no candidate (receipt schema v2,
#: 2026-09-29). Either one is gold-ABSENT for every read: ``present`` False, ``rank`` None.
NO_CANDIDATE_STATUSES = frozenset({"empty", "malformed"})


def branch_candidates(item: Mapping[str, object]) -> tuple[str, ...]:
    """ONE branch record's candidate list as every read consumes it.

    Schema v2 already seals the collapsed list (first occurrence kept) and an empty list for an
    ``empty``/``malformed`` note. A v1 record (sealed before 2026-09-29) is normalised the same
    way: its ``malformed`` ``("unparsed",)`` sentinel reads as no candidate -- never as an
    intent id -- and a repeated intent keeps its first rank.
    """

    if item.get("note_parse_status") in NO_CANDIDATE_STATUSES:
        return ()
    candidates = item.get("candidate_intent_ids")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return ()
    return tuple(dict.fromkeys(value for value in candidates if isinstance(value, str) and value))


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
        if not isinstance(branch_id, str) or not isinstance(item.get("candidate_intent_ids"), Sequence):
            continue
        outcomes[branch_id] = branch_row_outcome(branch_candidates(item), gold_intent_id)
    return outcomes


def _paired_bootstrap_over(
    keyed_diff: Mapping[str, float], *, n_replicates: int = BOOT_N, seed: int = BOOT_SEED,
) -> dict[str, object]:
    ids = sorted(keyed_diff)
    if not ids:
        raise PerceptionBranchReadError(
            "no row (or utterance) carried both a gold label and both branches"
        )
    result = paired_cluster_bootstrap(
        sample_ids=ids,
        statistic=lambda xs: 100.0 * sum(keyed_diff[x] for x in xs) / len(xs),
        n_replicates=n_replicates, seed=seed, ci_level=BOOT_LEVEL,
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
    branch_id: str, against: str = "A", seed: int = BOOT_SEED, n_replicates: int = BOOT_N,
) -> dict[str, object]:
    """The paired per-row ``top1`` difference between ``branch_id`` and ``against`` (design
    section 2: "Primary: paired per-row top1 difference B - A; null T - A")."""

    diffs = _per_row_metric_diff(rows, gold_by_sample, branch_id=branch_id, against=against, metric="top1")
    discordant = sum(1 for value in diffs.values() if value != 0.0)
    return {"branch_id": branch_id, "against": against, "metric": "top1", "discordant": discordant,
            **_paired_bootstrap_over(diffs, seed=seed, n_replicates=n_replicates)}


def paired_present_read(
    rows: Sequence[Mapping[str, object]], gold_by_sample: Mapping[str, str], *,
    branch_id: str, against: str = "A", seed: int = BOOT_SEED, n_replicates: int = BOOT_N,
) -> dict[str, object]:
    """The paired per-row ``present`` (gold-on-list) difference -- P-SV-2's own declared primary
    metric (design section 6, O4 ruling: "present" as `stage3_measurement` primary)."""

    diffs = _per_row_metric_diff(
        rows, gold_by_sample, branch_id=branch_id, against=against, metric="present",
    )
    discordant = sum(1 for value in diffs.values() if value != 0.0)
    return {"branch_id": branch_id, "against": against, "metric": "present", "discordant": discordant,
            **_paired_bootstrap_over(diffs, seed=seed, n_replicates=n_replicates)}


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
    branch_id: str, against: str = "A", seed: int = BOOT_SEED, n_replicates: int = BOOT_N,
    metric: str = "top1",
) -> dict[str, object]:
    """The SAME paired ``top1`` (or ``present``) read, clustered by utterance id instead of row
    id -- reported BESIDE the row-level read, never in its place (design section 2)."""

    per_row = _per_row_metric_diff(rows, gold_by_sample, branch_id=branch_id, against=against, metric=metric)
    by_utterance: dict[str, list[float]] = {}
    for sample_id, diff in per_row.items():
        by_utterance.setdefault(utterance_id(sample_id), []).append(diff)
    per_utterance_mean = {utt: sum(values) / len(values) for utt, values in by_utterance.items()}
    return {"branch_id": branch_id, "against": against, "metric": metric, "clustering": "utterance",
            **_paired_bootstrap_over(per_utterance_mean, seed=seed, n_replicates=n_replicates)}


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
                "candidate_intent_ids": list(branch_candidates(item)),
                "note_parse_status": item.get("note_parse_status"),
                "candidate_intent_ids_raw_count": item.get("candidate_intent_ids_raw_count"),
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


# ---------------------------------------------------------------------------
# RECIPE MODE (owner decision 184; driven by scripts/flights/psv/psv_read.sh)
# ---------------------------------------------------------------------------

RECIPE_SCHEMA = "saea-slurp-paired-analysis-recipe-v1"
READ_RECEIPT_SCHEMA = "saea-perception-branch-read-v1"
DRY_RUN_SCHEMA = "saea-perception-branch-read-dry-run-v1"
RECEIPT_NAME = "perception-branch-read.json"
#: Where ``stage3_rollout_score.py --mode perception-branches`` writes the level-2 columns and
#: their official scores: the sealed run's own ``supply-variants/`` directory, the ONE column
#: directory ``slurp_paired_roster_read.load_arm`` reads a column arm from.
COLUMN_DIR = "supply-variants"
COLUMN_SCORE_SCHEMA = "saea-stage3-perception-branch-solver-first-visit-v1"
DEFAULT_SCORER_ID = "slurp-slu-official-train"
#: The node-information-gain ledger's P-node conversion, P(Solver first answer correct | gold at
#: Perception rank r) (docs/results/2026-09-28-slurp-node-information-gain-ledger.md section 0).
#: Reported BESIDE the branch conversion; never gating.
LEDGER_CONVERSION_PCT = {"1": 97.57, "2": 26.98, "3": 12.0}
RULE_LEVEL2_INTENT = "level2-intent"
RULE_PRESENCE = "presence"
PASS_TWIN = "twin-null"
PASS_BRANCH = "branch"
RANK_BUCKETS = ("1", "2", "3", "4+", "absent")
SLU_COUNT_GROUPS = (
    ("slu_f1_word_tp", "slu_f1_char_tp"),
    ("slu_f1_word_fp", "slu_f1_char_fp"),
    ("slu_f1_word_fn", "slu_f1_char_fn"),
)
VERDICT_NOMINATED = "NOMINATED"
VERDICT_HARM = "BRANCH-LOCAL HARM"
VERDICT_NOT_NOMINATED = "NOT NOMINATED"


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _counter_dict(counter) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(counter.items(), key=lambda kv: str(kv[0]))}


class RecipePlan:
    """The registered read, as the recipe fixes it (never as a caller wishes it)."""

    def __init__(self, path: Path, document: Mapping[str, object]) -> None:
        import hashlib
        import re

        self.path = path
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        if document.get("schema") != RECIPE_SCHEMA:
            raise PerceptionBranchReadError(f"{path.name}: not a {RECIPE_SCHEMA} recipe")
        arms = document.get("arms")
        passes = document.get("passes")
        resampling = document.get("resampling")
        if not all(isinstance(x, Mapping) for x in (arms, passes, resampling)):
            raise PerceptionBranchReadError(f"{path.name}: recipe lacks arms/passes/resampling")
        try:
            arm, replicate, twin = arms["arm"], arms["in_chain_replicate"], arms["twin"]
            branch_pass, twin_pass = passes["branch"], passes["twin-null"]
        except KeyError as error:
            raise PerceptionBranchReadError(f"{path.name}: recipe lacks {error}") from error
        runs = {arm.get("run_id"), replicate.get("run_id"), twin.get("run_id")}
        attempts = {arm.get("attempt_id"), replicate.get("attempt_id"), twin.get("attempt_id")}
        if len(runs) != 1 or len(attempts) != 1:
            raise PerceptionBranchReadError(
                f"{path.name}: a same-flight branch read names ONE run and ONE attempt"
            )
        self.run_id = str(arm["run_id"])
        self.attempt_id = str(arm["attempt_id"])
        self.delivering = str(replicate["branch"])
        self.treatment = str(arm["branch"])
        self.twin = str(twin["branch"])
        if (branch_pass.get("left") != self.delivering or twin_pass.get("left") != self.delivering
                or branch_pass.get("right") != self.treatment or twin_pass.get("right") != self.twin):
            raise PerceptionBranchReadError(
                f"{path.name}: passes disagree with arms (both contrasts put the delivering "
                "branch on the LEFT)"
            )
        if resampling.get("cluster_key") != "sample_id":
            raise PerceptionBranchReadError(f"{path.name}: a branch read resamples by row (sample_id)")
        self.seed = int(resampling["seed"])
        self.draws = int(resampling["bootstrap_draws"])
        self.cluster_key = "sample_id"
        self.recipe_id = str(document["recipe_id"])
        run_ids = document.get("run_ids") if isinstance(document.get("run_ids"), Mapping) else {}
        self.read_run_id = str(document.get("read_run_id") or run_ids.get("read") or "")
        if not self.read_run_id:
            raise PerceptionBranchReadError(f"{path.name}: recipe names no READ run id")
        rule = str(document.get("decision_rule") or "")
        if "(2) THE CONTRAST:" in rule and "official intent accuracy (primary)" in rule:
            self.rule_kind = RULE_LEVEL2_INTENT
        elif "(2) PRESENCE:" in rule:
            self.rule_kind = RULE_PRESENCE
        else:
            raise PerceptionBranchReadError(f"{path.name}: decision rule has no registered kind")
        twin_clause = re.search(r"\(1\) THE TWIN NULL:(.*?)\s\(2\)", rule, re.S)
        self.twin_floor_text = twin_clause.group(1).strip() if twin_clause else None
        self.predecessor_trace_sha256: str | None = None
        recovery = document.get("recovery_reading_rule")
        if recovery is not None:
            match = re.search(r"trace ([0-9a-f]{64})", str(recovery))
            if match is None:
                raise PerceptionBranchReadError(
                    f"{path.name}: recovery reading rule names no predecessor trace"
                )
            self.predecessor_trace_sha256 = match.group(1)

    @classmethod
    def load(cls, path: Path) -> "RecipePlan":
        return cls(path, json.loads(path.read_text(encoding="utf-8")))

    def as_json(self, repo_root: Path) -> dict[str, object]:
        try:
            relpath = str(self.path.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            relpath = str(self.path)
        return {
            "relpath": relpath, "sha256": self.sha256, "recipe_id": self.recipe_id,
            "read_run_id": self.read_run_id, "run_id": self.run_id, "attempt_id": self.attempt_id,
            "branches": {"delivering": self.delivering, "treatment": self.treatment,
                         "twin": self.twin},
            "rule_kind": self.rule_kind, "seed": self.seed, "draws": self.draws,
            "cluster_key": self.cluster_key,
            "predecessor_trace_sha256": self.predecessor_trace_sha256,
        }


class SealedRun:
    """The sealed attempt's own manifest and outputs rows (hash-bound to each other)."""

    def __init__(self, data_root: Path, plan: RecipePlan) -> None:
        self.data_root = data_root
        self.run_id = plan.run_id
        self.attempt_id = plan.attempt_id
        self.directory = data_root / "runs" / plan.run_id / plan.attempt_id
        self.manifest_path = self.directory / f"{plan.run_id}.run-manifest.json"
        if not self.manifest_path.is_file():
            raise PerceptionBranchReadError(f"no sealed run manifest at {self.manifest_path}")
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.manifest_sha256 = _sha256_file(self.manifest_path)
        if self.manifest.get("status") != "COMPLETED" or self.manifest.get("run_id") != plan.run_id:
            raise PerceptionBranchReadError("the sealed manifest is not the COMPLETED requested run")
        self.outputs_path = self.directory / f"{plan.run_id}.outputs.jsonl"
        self.outputs_sha256 = _sha256_file(self.outputs_path)
        if self.outputs_sha256 != (self.manifest.get("outputs") or {}).get("sha256"):
            raise PerceptionBranchReadError("sealed outputs differ from the manifest's outputs hash")
        predecessor = self.manifest.get("predecessor_attempt")
        self.predecessor = predecessor if isinstance(predecessor, Mapping) else None
        if plan.predecessor_trace_sha256 is not None and (
            self.predecessor is None
            or self.predecessor.get("trace_sha256") != plan.predecessor_trace_sha256
        ):
            raise PerceptionBranchReadError(
                "the seal-only manifest does not name the registered predecessor trace"
            )
        with self.outputs_path.open(encoding="utf-8") as handle:
            self.rows = [json.loads(line) for line in handle if line.strip()]
        ids = [row.get("sample_id") for row in self.rows]
        if any(not isinstance(x, str) for x in ids) or len(set(ids)) != len(ids):
            raise PerceptionBranchReadError("sealed outputs carry missing or duplicate sample ids")
        split = self.manifest.get("split") or {}
        if split.get("count") is not None and int(split["count"]) != len(ids):
            raise PerceptionBranchReadError("sealed outputs do not cover the sealed split")
        self.sample_ids = tuple(ids)
        self.split_identity_hash = split.get("identity_hash")


def _receipt_of(row: Mapping[str, object]) -> Mapping[str, object]:
    episode = row.get("native_episode_receipt")
    receipt = episode.get("perception_branches") if isinstance(episode, Mapping) else None
    if not isinstance(receipt, Mapping) or not isinstance(receipt.get("branches"), Sequence):
        raise PerceptionBranchReadError(
            f"row {row.get('sample_id')!r} carries no perception_branches receipt"
        )
    return receipt


def sealed_branch_order(rows: Sequence[Mapping[str, object]], plan: RecipePlan) -> tuple[str, ...]:
    """The ONE declared branch order every sealed row carries (A last), checked against the
    recipe's three branches."""

    order: tuple[str, ...] | None = None
    for row in rows:
        receipt = _receipt_of(row)
        ids = tuple(str(item.get("branch_id")) for item in receipt["branches"]
                    if isinstance(item, Mapping))
        if order is None:
            order = ids
        elif ids != order:
            raise PerceptionBranchReadError("sealed rows disagree on the branch order")
        if not ids or receipt.get("delivered_branch_id") != ids[-1]:
            raise PerceptionBranchReadError("a sealed receipt's delivering branch is not last")
    if not order:
        raise PerceptionBranchReadError("no sealed row")
    if order[-1] != plan.delivering:
        raise PerceptionBranchReadError(
            f"the sealed delivering branch {order[-1]!r} is not the recipe's {plan.delivering!r}"
        )
    for branch_id in (plan.treatment, plan.twin):
        if branch_id not in order:
            raise PerceptionBranchReadError(f"recipe branch {branch_id!r} is not sealed")
    return order


def _branch_items(row: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    return {str(item.get("branch_id")): item for item in _receipt_of(row)["branches"]
            if isinstance(item, Mapping)}


def describe_branches(
    rows: Sequence[Mapping[str, object]], order: Sequence[str], delivering: str,
) -> dict[str, object]:
    """Gold-free, score-free shape counts of every sealed branch record (the dry run's body and
    the receipt's ``custody`` block): receipt schema/level, note parse status, presentation
    outcome (rendered / skip reason), ``min_candidates_met``, list sizes, level-2 fields, and the
    extra contacts the non-delivering branches spent."""

    from collections import Counter

    schema, level = Counter(), Counter()
    stats = {b: {"note_parse_status": Counter(), "presentation": Counter(),
                 "min_candidates_met": Counter(), "candidate_list_size": Counter(),
                 "level2_fields": 0} for b in order}
    extra_contacts = 0
    for row in rows:
        receipt = _receipt_of(row)
        schema[str(receipt.get("schema"))] += 1
        level[str(receipt.get("level"))] += 1
        items = _branch_items(row)
        delivered_solver = (items.get(delivering) or {}).get("solver_contact_id")
        for branch_id in order:
            item = items.get(branch_id)
            if item is None:
                raise PerceptionBranchReadError(f"row {row.get('sample_id')!r} lacks {branch_id!r}")
            s = stats[branch_id]
            s["note_parse_status"][str(item.get("note_parse_status", "ok-v1"))] += 1
            if item.get("presentation_id") is None:
                s["presentation"]["no-presentation"] += 1
            elif item.get("contrast_block_sha256") is not None:
                s["presentation"]["rendered"] += 1
            else:
                s["presentation"][f"skipped:{item.get('presentation_skip_reason')}"] += 1
            if item.get("min_candidates") is not None:
                s["min_candidates_met"][str(item.get("min_candidates_met"))] += 1
            s["candidate_list_size"][str(len(branch_candidates(item)))] += 1
            if "solver_response_text_sha256" in item:
                s["level2_fields"] += 1
            if branch_id != delivering:
                extra_contacts += 1 if item.get("contact_id") else 0
                solver = item.get("solver_contact_id")
                extra_contacts += 1 if solver and solver != delivered_solver else 0
    return {
        "rows": len(rows), "branch_order": list(order),
        "receipt_schema": _counter_dict(schema), "receipt_level": _counter_dict(level),
        "branches": {
            b: {"note_parse_status": _counter_dict(s["note_parse_status"]),
                "presentation": _counter_dict(s["presentation"]),
                "min_candidates_met": _counter_dict(s["min_candidates_met"]),
                "candidate_list_size": _counter_dict(s["candidate_list_size"]),
                "level2_fields": s["level2_fields"]}
            for b, s in stats.items()
        },
        "extra_contacts": {"total": extra_contacts,
                           "per_row": round(extra_contacts / len(rows), 4) if rows else None},
    }


def flight_contact_total(sealed: SealedRun) -> dict[str, object]:
    """The flight's own model contacts (the denominator of the extra-contact share): the sealed
    generation manifest's cost (a seal-only one sums its predecessors), else the run manifest's,
    else the predecessor attempt's own run manifest."""

    candidates = [("generation-manifest",
                   sealed.directory / f"{sealed.run_id}.generation-manifest.json"),
                  ("run-manifest", sealed.manifest_path)]
    if sealed.predecessor is not None:
        candidates.append(("predecessor-run-manifest",
                           sealed.data_root / "runs" / sealed.run_id
                           / str(sealed.predecessor.get("attempt_id"))
                           / f"{sealed.run_id}.run-manifest.json"))
    for source, path in candidates:
        if path.is_file():
            cost = json.loads(path.read_text(encoding="utf-8")).get("cost") or {}
            calls = cost.get("calls_used")
            if isinstance(calls, int) and calls > 0:
                return {"calls": calls, "source": source, "sha256": _sha256_file(path)}
    return {"calls": None, "source": "not-available"}


def _ledger_note_ids(path: Path) -> dict[str, list[str] | None] | None:
    """Per row, the FIRST ``phase:perception`` agent state's candidate ids, parsed EXACTLY as
    ``scripts/analysis/slurp_node_gain_ledger.py``'s ``load_node_states`` parses them (raw
    order, no collapse; ``None`` when the note is not JSON). ``None`` for a seal-only replay's
    narrowed phases document, which carries no agent states. Held in memory only."""

    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("seal_only_replay"):
        return None
    phases = document.get("phases")
    if not isinstance(phases, list) or not phases:
        return None
    out: dict[str, list[str] | None] = {}
    saw_states = False
    for result in phases[0].get("results") or ():
        states = result.get("agent_states")
        saw_states = saw_states or bool(states)
        ids: list[str] | None = None
        for state in states or ():
            if state.get("state_kind") == "phase:perception":
                try:
                    payload = json.loads(state.get("content") or "")
                    ids = [str(c.get("intent_id")) for c in payload.get("candidates") or ()]
                except (json.JSONDecodeError, AttributeError, TypeError):
                    ids = None
                break
        out[str(result.get("sample_id"))] = ids
    del document
    return out if saw_states else None


def ledger_note_source(sealed: SealedRun) -> tuple[Path | None, dict[str, list[str] | None] | None]:
    """The sealed ``phases.json`` that still carries agent states: the attempt's own, else (a
    seal-only completion, whose own phases document is a narrowed replay) the predecessor's."""

    paths = [sealed.directory / f"{sealed.run_id}.phases.json"]
    if sealed.predecessor is not None:
        paths.append(sealed.data_root / "runs" / sealed.run_id
                     / str(sealed.predecessor.get("attempt_id")) / f"{sealed.run_id}.phases.json")
    for path in paths:
        if path.is_file():
            ids = _ledger_note_ids(path)
            if ids is not None:
                return path, ids
    return None, None


def compare_delivering_with_ledger(
    rows: Sequence[Mapping[str, object]], delivering: str,
    ledger_ids: Mapping[str, list[str] | None],
) -> dict[str, int]:
    """Gold-free method reproduction: the delivering branch's sealed candidate list must equal
    the node-ledger driver's own parse of the delivered Perception note (after the schema-v2
    first-occurrence collapse; an unparsed note equals an empty list)."""

    equal = differ = missing = raw_duplicates = 0
    for row in rows:
        sid = str(row.get("sample_id"))
        if sid not in ledger_ids:
            missing += 1
            continue
        raw = ledger_ids[sid]
        ledger = tuple(dict.fromkeys(x for x in (raw or ()) if x))
        raw_duplicates += int(raw is not None and len(raw) != len(set(raw)))
        if branch_candidates(_branch_items(row)[delivering]) == ledger:
            equal += 1
        else:
            differ += 1
    return {"rows": len(rows), "equal": equal, "differ": differ, "missing": missing,
            "raw_duplicate_rows": raw_duplicates}


def resolve_level2_contacts(
    sealed: SealedRun, order: Sequence[str],
) -> dict[str, object]:
    """Gold-free, score-free: every row's first Solver visit carries one contact per declared
    branch, in declared order, whose response digest equals the sealed branch record's own
    ``solver_response_text_sha256``, and (seal-only) resolves in the verified predecessor trace
    with a matching digest. Counts only; no text is kept."""

    import hashlib

    from speech_aware_evidence_acquisition.core.bundle.outputs import verify_predecessor_attempts

    records: Mapping[str, Mapping[str, Mapping[str, object]]] = {}
    if sealed.predecessor is not None or sealed.manifest.get("predecessor_attempts") is not None:
        records, _kept = verify_predecessor_attempts(
            sealed.manifest, split_ids=frozenset(sealed.sample_ids), attempt_id=sealed.attempt_id,
        )
    counts = {"rows": 0, "no_solver_visit_rows": 0, "complete_branch_groups": 0,
              "order_or_digest_mismatch": 0, "resolved_in_predecessor_trace": 0,
              "unresolved": 0, "rows_kept_by_predecessor": len(records)}
    for row in sealed.rows:
        counts["rows"] += 1
        episode = row.get("native_episode_receipt") or {}
        solver = [v for v in episode.get("role_visits") or () if isinstance(v, Mapping)
                  and v.get("stage") == "solver"]
        if not solver:
            counts["no_solver_visit_rows"] += 1
            continue
        contacts = (solver[0].get("execution_receipt") or {}).get("contacts")
        if not isinstance(contacts, list) or len(contacts) != len(order):
            counts["order_or_digest_mismatch"] += 1
            continue
        counts["complete_branch_groups"] += 1
        items = _branch_items(row)
        kept = records.get(str(row.get("sample_id"))) or {}
        for i, branch_id in enumerate(order):
            contact = contacts[i] if isinstance(contacts[i], Mapping) else {}
            if items[branch_id].get("solver_response_text_sha256") != contact.get("response_text_sha256"):
                counts["order_or_digest_mismatch"] += 1
                continue
            response = kept.get(f"{contact.get('request_id')}/response")
            text = response.get("text") if isinstance(response, Mapping) else None
            if isinstance(text, str) and hashlib.sha256(text.encode("utf-8")).hexdigest() \
                    == contact.get("response_text_sha256"):
                counts["resolved_in_predecessor_trace"] += 1
            else:
                counts["unresolved"] += 1
    return counts


def load_train_gold_intents(
    lock_path: Path, data_root: Path, sample_ids: Sequence[str], *, workers: int | None = None,
) -> dict[str, str]:
    """``{sample_id: gold intent}`` through the GOVERNED TRAIN loader
    (``data.slurp.load_slurp_split``, split ``train``, never held-out) -- the only door gold
    enters this read through. Held in memory; never printed or persisted."""

    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split

    records = load_slurp_split(load_lock(lock_path), data_root, "train", workers=workers)
    by_id = {record.sample_id: record.intent for record in records}
    missing = sum(1 for sid in sample_ids if sid not in by_id)
    if missing:
        raise PerceptionBranchReadError(f"{missing} sealed rows are not in the governed TRAIN split")
    return {sid: by_id[sid] for sid in sample_ids}


def _rank_bucket(rank: int | None) -> str:
    return "absent" if rank is None else str(rank) if rank <= 3 else "4+"


def _as_contrast(read: Mapping[str, object]) -> dict[str, object]:
    low, high = read["ci95"]
    return {"n": read["n"], "delta_pp": read["point_pp"], "ci95_pp": [low, high],
            "half_width_pp": round((high - low) / 2.0, 4),
            **({"discordant": read["discordant"]} if "discordant" in read else {})}


def _utterance_read(
    diffs: Mapping[str, float], utterance_of: Mapping[str, str], *, seed: int, draws: int,
) -> dict[str, object]:
    grouped: dict[str, list[float]] = {}
    for sid, diff in diffs.items():
        grouped.setdefault(utterance_of.get(sid) or utterance_id(sid), []).append(diff)
    means = {utt: sum(v) / len(v) for utt, v in grouped.items()}
    return {"clustering": "utterance", "note": "reported beside, never gating",
            **_as_contrast(_paired_bootstrap_over(means, seed=seed, n_replicates=draws))}


def level1_read(
    rows: Sequence[Mapping[str, object]], gold: Mapping[str, str], order: Sequence[str],
    plan: RecipePlan, *, utterance_of: Mapping[str, str],
    ledger_ids: Mapping[str, list[str] | None] | None = None,
) -> dict[str, object]:
    """Level 1 (the note): per branch gold rank / present / top1 / mean gold rank, the rows by
    note parse status, and the paired row reads (treatment and twin, each minus the delivering
    branch) at the recipe's own seed and draws, with the utterance-level read beside."""

    ranks: dict[str, dict[str, int | None]] = {b: {} for b in order}
    statuses: dict[str, dict[str, str]] = {b: {} for b in order}
    for row in rows:
        sid = str(row["sample_id"])
        items = _branch_items(row)
        for branch_id, outcome in level1_row_outcomes(row, gold[sid]).items():
            ranks[branch_id][sid] = outcome["rank"]
            statuses[branch_id][sid] = str(items[branch_id].get("note_parse_status", "ok-v1"))
    per_branch = {}
    for branch_id in order:
        values = ranks[branch_id]
        n = len(values)
        present = [r for r in values.values() if r is not None]
        buckets = {bucket: 0 for bucket in RANK_BUCKETS}
        for rank in values.values():
            buckets[_rank_bucket(rank)] += 1
        by_status: dict[str, dict[str, int]] = {}
        for sid, status in statuses[branch_id].items():
            entry = by_status.setdefault(status, {"rows": 0, "present": 0})
            entry["rows"] += 1
            entry["present"] += int(values[sid] is not None)
        per_branch[branch_id] = {
            "rows": n, "rank_counts": buckets,
            "present_pct": round(100.0 * len(present) / n, 4) if n else None,
            "top1_pct": round(100.0 * buckets["1"] / n, 4) if n else None,
            "mean_gold_rank_when_present": round(sum(present) / len(present), 4) if present else None,
            "by_note_parse_status": dict(sorted(by_status.items())),
        }
    contrasts: dict[str, object] = {}
    for metric in ("present", "top1"):
        for branch_id in (plan.treatment, plan.twin):
            read_fn = paired_present_read if metric == "present" else paired_top1_read
            read = read_fn(rows, gold, branch_id=branch_id, against=plan.delivering,
                           seed=plan.seed, n_replicates=plan.draws)
            diffs = _per_row_metric_diff(rows, gold, branch_id=branch_id, against=plan.delivering,
                                         metric=metric)
            contrasts[f"{metric}:{branch_id}-minus-{plan.delivering}"] = {
                "metric": metric, "left": plan.delivering, "right": branch_id,
                **_as_contrast(read),
                "utterance_level": _utterance_read(diffs, utterance_of, seed=plan.seed,
                                                   draws=plan.draws),
            }
    ledger_rank = None
    if ledger_ids is not None:
        disagree = 0
        for row in rows:
            sid = str(row["sample_id"])
            raw = ledger_ids.get(sid) or []
            raw_rank = raw.index(gold[sid]) + 1 if gold[sid] in raw else None
            disagree += int(raw_rank != ranks[plan.delivering].get(sid))
        ledger_rank = {"rows": len(rows), "raw_rank_differs_from_collapsed_rank": disagree,
                       "note": "the ledger driver ranks by the raw list; schema v2 collapses "
                               "duplicates first -- a difference is possible only on a "
                               "duplicates-collapsed note"}
    return {"branches": per_branch, "contrasts": contrasts, "ranks_internal": ranks,
            "delivering_rank_vs_ledger_raw_rank": ledger_rank}


def _twin_bar(contrast: Mapping[str, object]) -> float:
    return round(abs(float(contrast["delta_pp"])) + float(contrast["half_width_pp"]), 4)


def decide_level2_intent(twin: Mapping[str, object], branch: Mapping[str, object]) -> dict[str, object]:
    """P-SV-1's registered rule on the level-2 official column contrasts (``twin`` = T minus A,
    ``branch`` = B minus A; each ``{"intent": contrast, "slu_f1": contrast}``)."""

    intent_bar = _twin_bar(twin["intent"])
    slu_bar = _twin_bar(twin["slu_f1"])
    low, high = branch["intent"]["ci95_pp"]
    point = float(branch["intent"]["delta_pp"])
    slu_low = float(branch["slu_f1"]["ci95_pp"][0])
    nominate = {
        "intent_ci95_lower_above_zero": low > 0,
        "intent_point_exceeds_twin_intent_bar": point > intent_bar,
        "slu_ci95_lower_not_below_minus_twin_slu_bar": slu_low >= -slu_bar,
    }
    harm = {
        "intent_ci95_upper_below_zero": high < 0,
        "intent_point_magnitude_exceeds_twin_intent_bar": abs(point) > intent_bar,
    }
    verdict = (VERDICT_NOMINATED if all(nominate.values())
               else VERDICT_HARM if all(harm.values()) else VERDICT_NOT_NOMINATED)
    return {"rule_kind": RULE_LEVEL2_INTENT, "verdict": verdict,
            "twin_bar_pp": {"intent": intent_bar, "slu_f1": slu_bar},
            "primary": {"metric": "level-2 official intent accuracy", "delta_pp": point,
                        "ci95_pp": [low, high]},
            "guard": {"metric": "level-2 official SLU-F1 (pooled)", "ci95_lower_pp": slu_low,
                      "floor_pp": -slu_bar},
            "nominate_clauses": nominate, "harm_clauses": harm}


def decide_presence(twin: Mapping[str, object], branch: Mapping[str, object]) -> dict[str, object]:
    """P-SV-2 / P-SV-3's registered rule on the level-1 ``present`` contrasts."""

    bar = _twin_bar(twin)
    low, _high = branch["ci95_pp"]
    point = float(branch["delta_pp"])
    nominate = {"present_ci95_lower_above_zero": low > 0,
                "present_point_exceeds_twin_present_bar": point > bar}
    return {"rule_kind": RULE_PRESENCE,
            "verdict": VERDICT_NOMINATED if all(nominate.values()) else VERDICT_NOT_NOMINATED,
            "twin_bar_pp": {"present": bar},
            "primary": {"metric": "level-1 gold-on-list (present)", "delta_pp": point,
                        "ci95_pp": list(branch["ci95_pp"])},
            "nominate_clauses": nominate}


def _run_subprocess(argv: Sequence[str]) -> int:
    """One child process (the column scorer or the paired read). Tests replace this seam."""

    import subprocess

    return subprocess.run(list(argv), check=False).returncode


def column_scoring_done(column_dir: Path, attempt_id: str) -> bool:
    path = column_dir / "score-summary.json"
    if not path.is_file():
        return False
    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return (summary.get("schema") == COLUMN_SCORE_SCHEMA and summary.get("stage") == "score"
            and (summary.get("source") or {}).get("attempt_id") == attempt_id)


def score_level2_columns(
    ctx: "ReadContext", *, rescore: bool,
) -> tuple[dict[str, object], bool]:
    """Render and score every branch's first-visit Solver column ONCE (idempotent: a complete
    score summary for this attempt is reused unless ``rescore``)."""

    column_dir = ctx.sealed.directory / COLUMN_DIR
    scored_now = False
    if rescore or not column_scoring_done(column_dir, ctx.plan.attempt_id):
        code = _run_subprocess([
            sys.executable, "-B", str(ctx.repo_root / "scripts/analysis/stage3_rollout_score.py"),
            "--mode", "perception-branches", "--run", ctx.plan.run_id,
            "--attempt", ctx.plan.attempt_id, "--roster", ctx.roster_relpath,
            "--analysis-root", str(column_dir), "--scorer-id", ctx.scorer_id,
            "--repo-root", str(ctx.repo_root), "--data-root", str(ctx.data_root),
            "--stage", "all",
        ])
        if code != 0:
            raise PerceptionBranchReadError(f"column render/score failed (exit {code})")
        scored_now = True
    if not column_scoring_done(column_dir, ctx.plan.attempt_id):
        raise PerceptionBranchReadError("column scoring left no complete score summary")
    summary_path = column_dir / "score-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if list(summary.get("branch_order") or ()) != list(ctx.order) or summary.get("scorer_id") != ctx.scorer_id:
        raise PerceptionBranchReadError("column score summary names another branch order or scorer")
    return {"path": str(summary_path), "sha256": _sha256_file(summary_path),
            "branches": {b: {"copy_sha256": v.get("copy_sha256"), "scores_sha256": v.get("scores_sha256")}
                         for b, v in (summary.get("branches") or {}).items()}}, scored_now


def _contrast_from_block(block: Mapping[str, object]) -> dict[str, object]:
    boot = block["cluster_bootstrap"]
    return {"left_pct": round(float(block["left_pct"]), 4),
            "right_pct": round(float(block["right_pct"]), 4),
            "delta_pp": round(float(block["delta_pp"]), 4),
            "ci95_pp": [round(float(x), 4) for x in boot["ci95_pp"]],
            "half_width_pp": round(float(boot["ci95_half_width_pp"]), 4),
            **({"saves": block["saves"], "harms": block["harms"]} if "saves" in block else {})}


def run_paired_pass(ctx: "ReadContext", pass_name: str, right: str) -> dict[str, object]:
    """One registered pass through ``stage3_paired_read.py`` column arms (left = the delivering
    branch's column, right = ``right``'s), then its intent / SLU-F1 contrasts."""

    directory = ctx.analysis_root / pass_name
    if directory.is_dir() and any(directory.iterdir()):
        raise PerceptionBranchReadError(f"{directory} already holds files (a sealed read is never overwritten)")
    directory.mkdir(parents=True, exist_ok=True)
    left = ctx.plan.delivering
    code = _run_subprocess([
        sys.executable, "-B", str(ctx.repo_root / "scripts/analysis/stage3_paired_read.py"),
        "--per-scenario", "--stage", "all",
        "--left-run", ctx.plan.run_id, "--left-attempt", ctx.plan.attempt_id,
        "--left-column", left, "--left-label", f"the delivering branch column {left}",
        "--right-run", ctx.plan.run_id, "--right-attempt", ctx.plan.attempt_id,
        "--right-column", right, "--right-label", f"the branch column {right}",
        "--scorer-id", ctx.scorer_id, "--expected-split-role", ctx.split_role,
        "--roster", ctx.roster_relpath, "--cluster-key", ctx.plan.cluster_key,
        "--split-identity-hash", ctx.split_identity_hash,
        "--seed", str(ctx.plan.seed), "--draws", str(ctx.plan.draws),
        "--recipe-id", ctx.plan.recipe_id,
        "--title", f"Perception-branch column read ({pass_name}: {right} vs {left})",
        "--analysis-root", str(directory),
        "--repo-root", str(ctx.repo_root), "--data-root", str(ctx.data_root),
    ])
    if code != 0:
        raise PerceptionBranchReadError(f"paired read {pass_name} refused or failed (exit {code})")
    path = directory / "score-contrasts.json"
    contrasts = json.loads(path.read_text(encoding="utf-8"))
    per_row = contrasts["per_row"]
    return {
        "pass": pass_name, "left": left, "right": right, "n": contrasts.get("n_rows"),
        "score_contrasts_sha256": _sha256_file(path),
        "intent": _contrast_from_block(per_row["scenario_action_exact"]),
        "slu_f1": _contrast_from_block(contrasts["pooled_micro"]["slu_f1_micro"]),
        "slu_f1_per_row": _contrast_from_block(per_row["slu_f1_f1"]),
    }


def load_column_per_sample(column_dir: Path, branch_id: str, scorer_id: str) -> dict[str, Mapping[str, object]]:
    path = column_dir / f"arm-{branch_id}-{scorer_id}-scores.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    entry = document.get(scorer_id, document)
    return {str(row["sample_id"]): row for row in entry["per_sample"]}


def _pooled_slu(rows: Mapping[str, Mapping[str, object]], ids: Sequence[str]) -> float:
    tp, fp, fn = (sum(float(rows[i].get(f, 0) or 0) for i in ids for f in group)
                  for group in SLU_COUNT_GROUPS)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return 100.0 * 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def conversion_table(
    ranks: Mapping[str, int | None], correct: Mapping[str, Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    """P(level-2 column intent correct | gold rank r in the branch note), beside the ledger's."""

    table = {bucket: {"rows": 0, "correct": 0} for bucket in RANK_BUCKETS}
    for sid, rank in ranks.items():
        entry = table[_rank_bucket(rank)]
        entry["rows"] += 1
        entry["correct"] += int(bool(correct[sid].get("scenario_action_exact")))
    for bucket, entry in table.items():
        entry["pct"] = round(100.0 * entry["correct"] / entry["rows"], 4) if entry["rows"] else None
        entry["ledger_reference_pct"] = LEDGER_CONVERSION_PCT.get(bucket)
    return table


def restricted_contrast(
    ids: Sequence[str], left: Mapping[str, Mapping[str, object]],
    right: Mapping[str, Mapping[str, object]], *, seed: int, draws: int,
) -> dict[str, object] | None:
    """Right minus left on ``ids`` only (the rendered-presentation rows), intent per row and
    pooled SLU-F1, by the same row bootstrap. Beside the verdict; never gating."""

    ids = sorted(ids)
    if not ids:
        return None
    intent = paired_cluster_bootstrap(
        sample_ids=ids,
        statistic=lambda xs: 100.0 * sum(float(bool(right[x].get("scenario_action_exact")))
                                         - float(bool(left[x].get("scenario_action_exact")))
                                         for x in xs) / len(xs),
        n_replicates=draws, seed=seed, ci_level=BOOT_LEVEL,
    )
    slu = paired_cluster_bootstrap(
        sample_ids=ids, statistic=lambda xs: _pooled_slu(right, xs) - _pooled_slu(left, xs),
        n_replicates=draws, seed=seed, ci_level=BOOT_LEVEL,
    )
    return {"n": len(ids),
            "intent": {"delta_pp": round(intent.point_estimate, 4),
                       "ci95_pp": [round(intent.ci_low, 4), round(intent.ci_high, 4)]},
            "slu_f1": {"delta_pp": round(slu.point_estimate, 4),
                       "ci95_pp": [round(slu.ci_low, 4), round(slu.ci_high, 4)]}}


class ReadContext:
    def __init__(self, *, plan, sealed, order, repo_root, data_root, analysis_root,
                 roster_relpath, roster_sha256, split_identity_hash, split_role,
                 utterance_of, scorer_id) -> None:
        self.plan, self.sealed, self.order = plan, sealed, tuple(order)
        self.repo_root, self.data_root, self.analysis_root = repo_root, data_root, analysis_root
        self.roster_relpath, self.roster_sha256 = roster_relpath, roster_sha256
        self.split_identity_hash, self.split_role = split_identity_hash, split_role
        self.utterance_of, self.scorer_id = utterance_of, scorer_id


def level2_read(ctx: ReadContext, level1: Mapping[str, object], *, rescore: bool) -> dict[str, object]:
    column_scores, scored_now = score_level2_columns(ctx, rescore=rescore)
    twin = run_paired_pass(ctx, PASS_TWIN, ctx.plan.twin)
    branch = run_paired_pass(ctx, PASS_BRANCH, ctx.plan.treatment)
    column_dir = ctx.sealed.directory / COLUMN_DIR
    per_sample = {b: load_column_per_sample(column_dir, b, ctx.scorer_id)
                  for b in (ctx.plan.delivering, ctx.plan.treatment, ctx.plan.twin)}
    ranks = level1["ranks_internal"]
    conversion = {b: conversion_table(ranks[b], per_sample[b]) for b in per_sample}
    rendered = [str(row["sample_id"]) for row in ctx.sealed.rows
                if _branch_items(row)[ctx.plan.treatment].get("contrast_block_sha256") is not None]
    has_presentation = any(_branch_items(row)[ctx.plan.treatment].get("presentation_id") is not None
                           for row in ctx.sealed.rows)
    return {
        "column_scores": column_scores,
        "scorer_contacts_this_run": len(ctx.order) if scored_now else 0,
        "passes": {PASS_TWIN: twin, PASS_BRANCH: branch},
        "conversion_by_gold_rank": conversion,
        "rendered_rows_only": (
            {"rows": len(rendered),
             "contrast": restricted_contrast(rendered, per_sample[ctx.plan.delivering],
                                             per_sample[ctx.plan.treatment],
                                             seed=ctx.plan.seed, draws=ctx.plan.draws)}
            if has_presentation else {"status": "NOT_APPLICABLE",
                                      "reason": "the treatment branch declares no presentation"}
        ),
    }


def _load_roster(repo_root: Path, relpath: str) -> tuple[dict[str, str], str, str, str]:
    path = repo_root / relpath
    document = json.loads(path.read_text(encoding="utf-8"))
    utterance_of = {str(item.get("sample_id") or item.get("id")): str(item.get("utterance_id") or "")
                    for item in document.get("items") or ()}
    role = str(document.get("split_role") or "discovery")
    return (utterance_of, _sha256_file(path), str(document.get("split_identity_hash") or ""),
            role if role in ("discovery", "dev") else "discovery")


def recipe_main(args) -> int:
    repo_root = Path(args.repo_root).resolve()
    recipe_path = Path(args.recipe)
    if not recipe_path.is_absolute():
        recipe_path = repo_root / recipe_path
    plan = RecipePlan.load(recipe_path)
    if args.run is not None and args.run != plan.run_id:
        raise PerceptionBranchReadError(f"--run {args.run!r} is not the recipe's {plan.run_id!r}")
    if args.attempt is not None and args.attempt != plan.attempt_id:
        raise PerceptionBranchReadError(
            f"--attempt {args.attempt!r} is not the recipe's sealed attempt {plan.attempt_id!r}"
        )
    if args.level == 1 and plan.rule_kind == RULE_LEVEL2_INTENT and not args.dry_run:
        raise PerceptionBranchReadError("this recipe's primary is level 2; --level 1 cannot decide it")
    data_root = Path(args.data_root)
    sealed = SealedRun(data_root, plan)
    order = sealed_branch_order(sealed.rows, plan)
    custody = describe_branches(sealed.rows, order, plan.delivering)
    utterance_of, roster_sha256, split_identity_hash, split_role = _load_roster(repo_root, args.roster)
    if set(utterance_of) != set(sealed.sample_ids):
        raise PerceptionBranchReadError("the roster does not match the sealed rows")
    if split_identity_hash and sealed.split_identity_hash != split_identity_hash:
        raise PerceptionBranchReadError("the roster's split identity is not the sealed manifest's")
    contacts = flight_contact_total(sealed)
    extra = custody["extra_contacts"]
    extra["share_of_flight"] = (round(extra["total"] / contacts["calls"], 4)
                                if contacts.get("calls") else None)
    extra["flight_contacts"] = contacts

    if args.dry_run:
        ledger_path, ledger_ids = ledger_note_source(sealed)
        column_dir = sealed.directory / COLUMN_DIR
        report = {
            "schema": DRY_RUN_SCHEMA, "recipe": plan.as_json(repo_root),
            "sealed": {"run_id": plan.run_id, "attempt_id": plan.attempt_id,
                       "manifest_sha256": sealed.manifest_sha256,
                       "outputs_sha256": sealed.outputs_sha256,
                       "predecessor_attempt_id": (sealed.predecessor or {}).get("attempt_id"),
                       "predecessor_trace_sha256": (sealed.predecessor or {}).get("trace_sha256")},
            "custody": custody,
            "level2_contacts": (resolve_level2_contacts(sealed, order)
                                if args.level == 2 else "not requested"),
            "delivering_note_vs_ledger_parse": (
                {**compare_delivering_with_ledger(sealed.rows, plan.delivering, ledger_ids),
                 "phases_path": str(ledger_path)}
                if ledger_ids is not None else "NOT_AVAILABLE: no phases.json with agent states"),
            "paired_read_inputs_present": {
                name: (sealed.directory / name).is_file()
                for name in (f"{plan.run_id}.generation-manifest.json",
                             f"{plan.run_id}.phases.json", "score-jobs.jsonl")
            },
            "column_dir_exists": column_dir.is_dir(),
            "column_scoring_done": column_scoring_done(column_dir, plan.attempt_id),
            "stopped_before": "gold, scorer and any metric",
        }
        print(json.dumps(report, indent=1, sort_keys=True))
        return 0

    analysis_root = Path(args.analysis_root)
    receipt_path = analysis_root / RECEIPT_NAME
    if receipt_path.exists():
        raise PerceptionBranchReadError(f"{receipt_path} exists (a sealed read is never overwritten)")
    ledger_path, ledger_ids = ledger_note_source(sealed)
    if ledger_ids is None:
        raise PerceptionBranchReadError(
            "no phases.json with agent states: the delivering branch's P-node counting cannot be "
            "reproduced against the node-ledger driver's parse"
        )
    ledger_check = compare_delivering_with_ledger(sealed.rows, plan.delivering, ledger_ids)
    if ledger_check["differ"] or ledger_check["missing"]:
        raise PerceptionBranchReadError(
            f"the delivering branch does not reproduce the ledger driver's P-node parse "
            f"({ledger_check['differ']} differ, {ledger_check['missing']} missing)"
        )
    gold = load_train_gold_intents(Path(args.lock), data_root, sealed.sample_ids,
                                   workers=args.workers)
    level1 = level1_read(sealed.rows, gold, order, plan, utterance_of=utterance_of,
                         ledger_ids=ledger_ids)
    del gold
    ctx = ReadContext(
        plan=plan, sealed=sealed, order=order, repo_root=repo_root, data_root=data_root,
        analysis_root=analysis_root, roster_relpath=args.roster, roster_sha256=roster_sha256,
        split_identity_hash=split_identity_hash or str(sealed.split_identity_hash or ""),
        split_role=split_role, utterance_of=utterance_of, scorer_id=args.scorer_id,
    )
    level2 = level2_read(ctx, level1, rescore=args.rescore) if args.level == 2 else None
    contrasts = level1["contrasts"]
    if plan.rule_kind == RULE_LEVEL2_INTENT:
        verdict = decide_level2_intent(level2["passes"][PASS_TWIN], level2["passes"][PASS_BRANCH])
    else:
        verdict = decide_presence(contrasts[f"present:{plan.twin}-minus-{plan.delivering}"],
                                  contrasts[f"present:{plan.treatment}-minus-{plan.delivering}"])
    level1_public = {k: v for k, v in level1.items() if k != "ranks_internal"}
    receipt = {
        "schema": READ_RECEIPT_SCHEMA,
        "status": ("DESCRIPTIVE numbers and the registered rule applied mechanically; the "
                   "nomination is the coordinator's to countersign. Branch-local; a TRAIN "
                   "development read, never a test claim."),
        "read_run_id": plan.read_run_id, "recipe": plan.as_json(repo_root),
        "sealed": {"run_id": plan.run_id, "attempt_id": plan.attempt_id,
                   "manifest_sha256": sealed.manifest_sha256,
                   "outputs_sha256": sealed.outputs_sha256,
                   "predecessor_attempt_id": (sealed.predecessor or {}).get("attempt_id"),
                   "predecessor_trace_sha256": (sealed.predecessor or {}).get("trace_sha256")},
        "roster": {"relpath": args.roster, "sha256": roster_sha256,
                   "split_identity_hash": ctx.split_identity_hash},
        "gold": {"loader": "speech_aware_evidence_acquisition.data.slurp.load_slurp_split",
                 "split": "train", "rows": len(sealed.sample_ids),
                 "persisted": False},
        "settings": {"seed": plan.seed, "draws": plan.draws, "cluster_key": plan.cluster_key,
                     "scorer_id": args.scorer_id, "level": args.level,
                     "ci_level": BOOT_LEVEL},
        "custody": custody,
        "delivering_note_vs_ledger_parse": {**ledger_check,
                                            "phases_sha256": _sha256_file(ledger_path)},
        "level1": level1_public,
        "level2": level2,
        "twin_floor_reported_beside": plan.twin_floor_text,
        "verdict": verdict,
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "server": 0, "network": 0,
                     "scorer": (level2 or {}).get("scorer_contacts_this_run", 0)},
        "driver_sha256": _sha256_file(Path(__file__)),
    }
    analysis_root.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(receipt, indent=1, sort_keys=True) + "\n"
    with receipt_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    print(json.dumps({"receipt": str(receipt_path), "verdict": verdict["verdict"],
                      "primary": verdict["primary"]}, sort_keys=True))
    return 0


def legacy_main(args) -> int:
    rows = [json.loads(line) for line in args.outputs.read_text(encoding="utf-8").splitlines() if line]
    gold_by_sample = json.loads(args.gold.read_text(encoding="utf-8"))
    read_fn: Callable[..., dict[str, object]] = (
        paired_top1_read if args.metric == "top1" else paired_present_read
    )
    result = read_fn(rows, gold_by_sample, branch_id=args.branch, against=args.against)
    print(json.dumps(result, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    legacy = parser.add_argument_group("legacy mode")
    legacy.add_argument("--outputs", type=Path, help="sealed outputs JSONL")
    legacy.add_argument("--gold", type=Path, help="{sample_id: gold_intent_id} JSON")
    legacy.add_argument("--branch", help="the B (or T) branch id to read against A")
    legacy.add_argument("--against", default="A")
    legacy.add_argument("--metric", choices=("top1", "present"), default="top1")
    recipe = parser.add_argument_group("recipe mode")
    recipe.add_argument("--recipe", help="the registered analysis recipe (repo-root relative or absolute)")
    recipe.add_argument("--run", help="must equal the recipe's run id (default: the recipe's)")
    recipe.add_argument("--attempt", help="must equal the recipe's sealed attempt (default: the recipe's)")
    recipe.add_argument("--roster", help="roster receipt relpath (repo-root relative)")
    recipe.add_argument("--level", type=int, choices=(1, 2), default=2)
    recipe.add_argument("--analysis-root", help="READ output directory")
    recipe.add_argument("--data-root", default=(os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
    recipe.add_argument("--repo-root", default=str(REPO_ROOT))
    recipe.add_argument("--lock", default="/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
    recipe.add_argument("--scorer-id", default=DEFAULT_SCORER_ID)
    recipe.add_argument("--workers", type=int, default=8, help="governed gold loader workers")
    recipe.add_argument("--rescore", action="store_true",
                        help="re-run the column render/score even when a complete summary exists")
    recipe.add_argument("--dry-run", action="store_true",
                        help="parse and count only; stop before any gold, scorer or metric")
    args = parser.parse_args(argv)
    if args.recipe is not None:
        if args.outputs is not None or args.gold is not None:
            parser.error("recipe mode and legacy mode are exclusive")
        if args.roster is None or (args.analysis_root is None and not args.dry_run):
            parser.error("recipe mode needs --roster and --analysis-root")
        try:
            return recipe_main(args)
        except PerceptionBranchReadError as error:
            print(f"REFUSED: {error}", file=sys.stderr)
            return 3
    if args.outputs is None or args.gold is None or args.branch is None:
        parser.error("legacy mode needs --outputs --gold --branch (or use --recipe)")
    return legacy_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
