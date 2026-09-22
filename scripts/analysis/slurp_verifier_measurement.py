#!/usr/bin/env python3
"""What the SLURP base's verifier is worth: selection, coverage and confidence.

Owner decision 74 of 2026-09-21, Stage-3 prelude. Zero model, tokenizer,
encoder, ASR, server, GPU and network contact. The only scorer invocations are
the registered model-free SLURP scorings, every one of them over a COPY of
sealed bytes written under this read's own output root; no sealed file is ever
opened for writing, moved or renamed, and no run directory is written. No
utterance text, gold label, transcript, filler or model output is printed or
persisted: this driver reports counts, rates, scenario names and hashes only.

WHY. The SLURP base spends three of its five contacts per row on a verifier --
the Reviewer visits, and the Planner routes ACCEPT or REVISE on what they say.
Cell B2 v3 additionally bought five Solver samples per row and committed one of
them. Neither mechanism has ever been priced against the question that decides
whether test-time compute is worth buying at all: **does the verifier select
the correct answer when one is available?** Brown et al. (arXiv:2407.21787,
2024) separate COVERAGE (some sample is correct) from SELECTION (the committed
sample is correct) and report that majority voting and reward models plateau
long before coverage does; Chen et al. (arXiv:2403.02419, 2024) report that
Vote and Filter-Vote can rise and then FALL in the number of LM calls, because
more calls help easy queries and hurt hard ones. Those two framings are the
frame of this read (see the programme's own literature commons,
``wiki/survey/workbench/training-free-rl-2026-09-21/README.md`` section 4).

WHAT IT MEASURES

  1. SELECTION PRECISION AND RECALL OF THE ROUTE. On the sealed anchor, cell
     B1 and cell B1-notool arms, the per-row official correctness of the
     INITIAL Solver draft is compared with the per-row official correctness of
     the DELIVERED answer, and both are crossed with the Planner's
     ACCEPT-vs-REVISE route. "Precision" is P(the draft was wrong | the route
     was REVISE); "recall" is P(the route was REVISE | the draft was wrong).
     The draft side is re-scored by the registered official scorer over a COPY
     of the drafts, never over a sealed run directory. On the rows where the
     first Solver visit's ``response_text_sha256`` equals the row's delivered
     ``response_text_sha256`` -- which is the overwhelming majority -- the
     draft IS the delivered text, proved byte for byte rather than assumed;
     only the remaining rows have their draft text recovered from the sealed
     trace, and each recovered text is re-hashed against the receipt's sha
     before it is used.

  2. COVERAGE VERSUS SELECTION ON THE B2 v3 ROLLOUTS. Each of the five sealed
     Solver samples per row is rendered back to the canonical answer payload
     -- exactly the payload ``analysis.native_commit_replay.replay_row``
     builds -- and scored once, complete, by the registered official scorer.
     Coverage@k is the unbiased estimator ``1 - C(n-c, k) / C(n, k)``.
     Selection is the sealed delivered answer's own official correctness. The
     registered commit policy is re-applied offline as the third point and
     asserted to reproduce the sealed delivered answer, which is the licence
     for scoring rendered samples at all. Pooled and per scenario.

  3. A CONFIDENCE SIGNAL, IF ONE EXISTS. The sealed receipts are searched for
     anything confidence-like and each candidate is ranked by AUROC against
     official correctness: the B2 v3 sample-agreement count
     (``solver_group.delivered.intent_support``), the per-row Reviewer
     iteration count, and the Planner route itself. The Reviewer's own
     findings are NOT a candidate and the report says why.

STAGES
  --stage reviewer     stage 1 and the route-side half of stage 3.
  --stage rollouts     stage 2 and the sample-agreement half of stage 3.
  --stage report       the Markdown tables.
  --stage primitives   item E37 (owner decision 84): parse rate, per-token
                        counts, REVISE-* precision/recall, the token x
                        correctness confusion table, cross-visit agreement
                        and the Planner route conditioned on the token, for
                        every arm of PRIMITIVE_ARMS. Empty and a no-op
                        SKIP until cell R-PRIM has flown; NOT part of
                        --stage all.
  --stage all          reviewer, rollouts and report, in order.
  --self-check         recompute one pinned number and refuse on a mismatch.

USAGE
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
  python scripts/analysis/slurp_verifier_measurement.py --stage all \\
      --data-root "$SPEECHRL_DATA_DIR" \\
      --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \\
      --out-dir "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-PRELUDE-V1/verifier"

Development numbers only (owner decision 28): TRAIN Fold A is an exposed
discovery roster and nothing here is a test claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:  # noqa: PLC0415 - a script, not a module
    sys.path.insert(0, str(REPO_ROOT / "src"))

# E37 (owner decision 84, 2026-09-22): the primitive-verdict vocabulary and
# receipt-mark dispositions, imported so this driver's "primitives" stage
# reads the same registered names the harness itself writes.
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (  # noqa: E402
    REACT_EXHAUSTION_DISPOSITION,
    REVIEWER_VERDICT_ILLEGAL_DISPOSITION,
)
from speech_aware_evidence_acquisition.rails.review_primitives import (  # noqa: E402
    REVIEW_PRIMITIVE_TOKENS,
)

SCHEMA = "saea-slurp-verifier-measurement-v1"
SCORER = "slurp-slu-official-train"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-evo-fold-a-v2.json"
ROSTER_SHA256 = "1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d"
ROSTER_ROWS = 1080
SAMPLES = 5

# The empty answer a malformed sample is rendered as, so that the official
# evaluator still receives a prediction for every row. A malformed sample is
# never correct under any metric, which is exactly the accounting coverage@k
# needs.
EMPTY_ANSWER = {"action": "", "entities": [], "scenario": ""}


@dataclass(frozen=True)
class ReviewerArm:
    key: str
    label: str
    run_id: str
    attempt_id: str
    verdict: str


REVIEWER_ARMS: tuple[ReviewerArm, ...] = (
    ReviewerArm(
        "anchor", "the sealed dual-store anchor (Reviewer x3 + Planner, tool present)",
        "SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1",
        "attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1",
        "docs/results/2026-09-16-slurp-train-a-review-stage-attribution.md",
    ),
    ReviewerArm(
        "b1", "cell B1's arm (module M1: speech-keyed exemplars, tool present)",
        "SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2",
        "attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-recovery-v2",
        "docs/results/2026-09-17-slurp-b1-exemplars-k20-verdict.md",
    ),
    ReviewerArm(
        "b1notool", "cell B1-notool (the Reviewer's task-contract tool withdrawn)",
        "SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1",
        "attempt-slurp-native-exemplars-k20-notool-train-fold-a-generation-v1",
        "docs/results/2026-09-20-slurp-b1-notool-verdict.md",
    ),
)

B2_RUN = "SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-V3"
B2_ATTEMPT = "attempt-slurp-native-samples5-anchor-train-fold-a-generation-v3"
B2_VERDICT = "docs/results/2026-09-19-slurp-b2-samples5-verdict.md"
B2_COMMIT_POLICY = "saea-commit-plurality-support-v1"
B2_COMMIT_PARAMS = {"min_support": 3, "similarity_threshold": 0.8}

# The greedy-repeat twin the task asks about. Owner decision 8, restated by
# decision 15, launches it only on a positive arm CI95; cell B2 v3's arm read
# -1.4598 and the verdict records that the twin "is not due, it does not fly".
# This driver refuses to invent it and asserts its absence instead.
B2_TWIN_EXPECTED_ABSENT = (
    "no greedy-repeat twin of cell B2 v3 exists: the verdict "
    "docs/results/2026-09-19-slurp-b2-samples5-verdict.md records that the twin "
    "was NOT due and did NOT fly, so nothing in the sealed record separates "
    "five samples at temperature 0.7 from five greedy repeats"
)

SELF_CHECK = {
    "name": "the sealed anchor's initial-Solver against delivered counts",
    "expected": {
        "draft_intent_correct": 843, "delivered_intent_correct": 842,
        "intent_saves": 0, "intent_harms": 1,
        "draft_entity_set_exact": 379, "delivered_entity_set_exact": 379,
        "draft_full_task_exact": 317, "delivered_full_task_exact": 317,
        "planner_revise_rows": 5,
    },
    "source": "docs/results/2026-09-16-slurp-train-a-review-stage-attribution.md "
              "('Complete-cohort finding': intent 843 -> 842 with 0 saves and 1 harm; "
              "entity set exact 379 / 379 with zero saves and zero harms; full intent "
              "and entity exact 317 / 317; 'the initial Planner accepts 1,075 drafts "
              "and requests revision for five')",
}


class VerifierError(RuntimeError):
    """A sealed input is missing or does not have the shape this read needs."""


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows
    ) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return sha256_file(path)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )


def run_dir(data_root: Path, run_id: str, attempt_id: str) -> Path:
    directory = data_root / "runs" / run_id / attempt_id
    if not directory.is_dir():
        raise VerifierError(f"no sealed attempt directory at {directory}")
    return directory


def load_roster(repo_root: Path) -> dict[str, dict[str, Any]]:
    path = repo_root / ROSTER_RELPATH
    digest = sha256_file(path)
    if digest != ROSTER_SHA256:
        raise VerifierError(
            f"roster {path} hashes {digest}, not the pinned {ROSTER_SHA256}"
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(item["sample_id"]): {
            "stratum": item["stratum"],
            "headset": bool(item["headset"]),
        }
        for item in document["items"]
    }


def sealed_per_sample(directory: Path, run_id: str) -> dict[str, dict[str, float]]:
    """The arm's own sealed official per-row scores -- never recomputed."""

    path = directory / f"{run_id}.scores.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document[SCORER]["per_sample"]
    return {str(row["sample_id"]): row for row in rows}


METRICS = ("intent_exact", "entity_set_exact", "full_task_exact")


def correctness(row: Mapping[str, Any]) -> dict[str, Any]:
    """The three per-row notions of "the answer is right" this read uses.

    They are the three rows of the sealed 2026-09-16 review-stage attribution
    ("Intent exact", "Entity set exact", "Full intent and entity exact"), so
    this driver's anchor numbers are checkable against a sealed predecessor.
    Entity-set exactness is defined on the official COUNTS -- no false positive
    and no false negative -- rather than on an F1 of 1.0, because a row whose
    gold and prediction are both empty has no counts at all and its F1 is a
    convention rather than a fact.
    """

    intent = float(row["scenario_action_exact"]) >= 1.0
    entities = (float(row["slot_f1_exact_fp"]) == 0.0
                and float(row["slot_f1_exact_fn"]) == 0.0)
    return {
        "intent_exact": intent,
        "entity_set_exact": entities,
        "full_task_exact": bool(intent and entities),
        "slu_f1": float(row["slu_f1_f1"]),
    }


def score_copy(scorer_id: str, outputs_copy: Path, result_path: Path, lock, root: Path):
    """One complete registered scoring over a COPY, cached by its result file.

    This is the same invocation ``core.scoring_batch`` makes inside its own job
    process (``core.scorers.score_bundle`` calls ``scorer_fn(outputs, lock,
    root)``), one complete score per arm-side, never sharded. ``scoring_batch``
    itself cannot be the runner here: it scores a complete, bundle-verified run
    directory, and every side scored here is a derived copy with no manifest
    and no bundle. The precedent is ``analysis.b8a_delivery_node_read``.
    """

    from speech_aware_evidence_acquisition.core.base import SCORERS  # noqa: PLC0415
    import speech_aware_evidence_acquisition.core.scorers  # noqa: PLC0415, F401

    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))[scorer_id], 0.0
    scorer = SCORERS.resolve(scorer_id)
    started = time.time()
    result = scorer(outputs_copy, lock, root)
    elapsed = time.time() - started
    aggregate = result["aggregate"]
    if aggregate.get("split_id") not in (None, "train"):
        raise VerifierError(f"{scorer_id} did not resolve TRAIN gold for {outputs_copy}")
    if not aggregate["identity_check"]["passed"]:
        raise VerifierError(f"{scorer_id} port/official identity check failed")
    write_json(result_path, {scorer_id: result})
    return result, elapsed


def auroc(scores: Sequence[float], labels: Sequence[bool]) -> dict[str, Any]:
    """Mann-Whitney AUROC with mid-ranks for ties.

    ``labels`` True is the POSITIVE class. An AUROC of 0.5 is a signal that
    ranks the positive class no better than chance.
    """

    positives = [s for s, y in zip(scores, labels) if y]
    negatives = [s for s, y in zip(scores, labels) if not y]
    if not positives or not negatives:
        return {"auroc": None, "n_positive": len(positives), "n_negative": len(negatives),
                "reason": "one class is empty"}
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    index = 0
    while index < len(order):
        stop = index
        while stop + 1 < len(order) and scores[order[stop + 1]] == scores[order[index]]:
            stop += 1
        mid = (index + stop) / 2.0 + 1.0
        for position in range(index, stop + 1):
            ranks[order[position]] = mid
        index = stop + 1
    rank_sum = sum(r for r, y in zip(ranks, labels) if y)
    n_pos, n_neg = len(positives), len(negatives)
    value = (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return {"auroc": value, "n_positive": n_pos, "n_negative": n_neg,
            "distinct_scores": len(set(scores))}


def coverage_at_k(correct: int, n: int, k: int) -> float:
    """The unbiased ``pass@k`` estimator: ``1 - C(n-c, k) / C(n, k)``."""

    if k > n:
        raise VerifierError("coverage@k requires k <= n")
    if n - correct < k:
        return 1.0
    return 1.0 - math.comb(n - correct, k) / math.comb(n, k)


def rate(numerator: int, denominator: int) -> float | None:
    return (numerator / denominator) if denominator else None


# ---------------------------------------------------------------------------
# Stage 1: the route
# ---------------------------------------------------------------------------


def scan_episodes(directory: Path, run_id: str) -> dict[str, dict[str, Any]]:
    """Every row's role graph, route and draft identity, from outputs.jsonl.

    The identity that makes the rest of this stage cheap and exact: the row's
    top-level ``response_text_sha256`` is the delivered text's hash, and the
    FIRST ``solver``-stage role visit's ``execution_receipt.final_contact.
    response_text_sha256`` is the initial draft's. Where the two are equal the
    delivered text IS the initial draft, byte for byte.
    """

    path = directory / f"{run_id}.outputs.jsonl"
    out: dict[str, dict[str, Any]] = {}
    for row in iter_jsonl(path):
        sample_id = str(row["sample_id"])
        receipt = row["native_episode_receipt"]
        visits = receipt["role_visits"]
        solver_visits = [v for v in visits if v["stage"] == "solver"]
        reviewer_visits = [v for v in visits if v["stage"] == "review"]
        planner_visits = [v for v in visits if v["stage"] == "planner"]
        if not solver_visits:
            raise VerifierError(f"row {sample_id} has no solver visit")
        draft_sha = solver_visits[0]["execution_receipt"]["final_contact"]["response_text_sha256"]
        delivered_sha = str(row["response_text_sha256"])
        routes = [str(entry["action"]) for entry in receipt["planner_routes"]]
        out[sample_id] = {
            "delivered_text": row["text"],
            "delivered_sha256": delivered_sha,
            "draft_sha256": draft_sha,
            "draft_is_delivered": draft_sha == delivered_sha,
            "solver_visits": len(solver_visits),
            "reviewer_visits": len(reviewer_visits),
            "reviewer_contacts": sum(
                len(v["execution_receipt"]["contacts"]) for v in reviewer_visits
            ),
            "planner_visits": len(planner_visits),
            "planner_routes": routes,
            "any_revise": "REVISE" in routes,
            "first_route": routes[0] if routes else None,
            "revision_executed": len(solver_visits) > 1,
            "episode_shape": [v["stage"] for v in visits],
            # E37 (owner decision 84): present exactly when the row's
            # arm declares native_episode.reviewer_verdict, one mark per
            # Reviewer visit ({"visit", "token", "disposition", "head"}).
            # None on every row of every unarmed arm -- the receipt carries
            # no such key at all, and this scan never invents one.
            "reviewer_verdicts": receipt.get("reviewer_verdicts"),
        }
    if len(out) != ROSTER_ROWS:
        raise VerifierError(f"{run_id}: {len(out)} rows, expected {ROSTER_ROWS}")
    return out


def recover_draft_texts(
    directory: Path, run_id: str, wanted: Mapping[str, str]
) -> dict[str, str]:
    """Recover the few initial-draft texts that differ from the delivered text.

    ``wanted`` maps sample_id -> the draft's ``response_text_sha256``. The
    sealed trace is STREAMED line by line (it is hundreds of megabytes) and a
    single compiled alternation of the wanted hashes pre-filters the lines, so
    nothing but the matching records is ever parsed. Every recovered text is
    re-hashed against the receipt's own sha before it is returned.
    """

    if not wanted:
        return {}
    path = directory / f"{run_id}.trace.jsonl"
    # One response hash can be the draft of SEVERAL rows -- identical Solver
    # output is common when the draft is a boilerplate or degenerate answer --
    # so the index is sha -> {sample_id}, never sha -> sample_id.
    by_sha: dict[str, set[str]] = {}
    for sample_id, sha in wanted.items():
        by_sha.setdefault(str(sha), set()).add(sample_id)
    pattern = re.compile("|".join(re.escape(sha) for sha in by_sha))
    found: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not pattern.search(line):
                continue
            record = json.loads(line)
            if record.get("channel") != "MODEL_RESPONSE":
                continue
            payload = record.get("payload") or {}
            sha = str(payload.get("response_text_sha256"))
            sample_ids = by_sha.get(sha)
            if not sample_ids:
                continue
            text = payload.get("text")
            if not isinstance(text, str):
                raise VerifierError(f"trace record for {sha} carries no text")
            if sha256_text(text) != sha:
                raise VerifierError(f"recovered draft for {sha} does not re-hash")
            for sample_id in sample_ids:
                found[sample_id] = text
            if len(found) == len(wanted):
                break
    missing = sorted(set(wanted) - set(found))
    if missing:
        raise VerifierError(f"{run_id}: no trace record for the drafts of {missing}")
    return found


def stage_reviewer(
    data_root: Path, repo_root: Path, lock_path: Path, out_dir: Path
) -> dict[str, Any]:
    from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: PLC0415

    lock = load_lock(lock_path)
    roster = load_roster(repo_root)
    arms: dict[str, Any] = {}

    for arm in REVIEWER_ARMS:
        directory = run_dir(data_root, arm.run_id, arm.attempt_id)
        episodes = scan_episodes(directory, arm.run_id)
        differing = {
            sample_id: entry["draft_sha256"]
            for sample_id, entry in episodes.items()
            if not entry["draft_is_delivered"]
        }
        print(f"[{arm.key}] {len(episodes)} rows; "
              f"{len(episodes) - len(differing)} drafts byte-identical to the delivered "
              f"answer; {len(differing)} recovered from the sealed trace", flush=True)
        recovered = recover_draft_texts(directory, arm.run_id, differing)

        draft_rows = [
            {"sample_id": sample_id,
             "text": recovered.get(sample_id, entry["delivered_text"])}
            for sample_id, entry in sorted(episodes.items())
        ]
        work = out_dir / arm.key
        draft_path = work / "draft-outputs.jsonl"
        draft_sha = write_jsonl(draft_path, draft_rows)
        result, elapsed = score_copy(
            SCORER, draft_path, work / f"{SCORER}-draft-scores.json", lock, data_root
        )
        print(f"[{arm.key}] draft copy scored in {elapsed:.1f}s: official slu_f1 "
              f"{100 * float(result['aggregate']['official']['slu_f1']):.4f}", flush=True)

        draft_scores = {str(r["sample_id"]): r for r in result["per_sample"]}
        delivered_scores = sealed_per_sample(directory, arm.run_id)

        rows: list[dict[str, Any]] = []
        for sample_id, entry in sorted(episodes.items()):
            draft = correctness(draft_scores[sample_id])
            delivered = correctness(delivered_scores[sample_id])
            rows.append({
                "sample_id": sample_id,
                "stratum": roster[sample_id]["stratum"],
                "route_revise": entry["any_revise"],
                "revision_executed": entry["revision_executed"],
                "reviewer_visits": entry["reviewer_visits"],
                "reviewer_contacts": entry["reviewer_contacts"],
                "planner_routes": entry["planner_routes"],
                "draft_is_delivered": entry["draft_is_delivered"],
                "draft": draft,
                "delivered": delivered,
            })

        arms[arm.key] = {
            "label": arm.label,
            "run_id": arm.run_id,
            "attempt_id": arm.attempt_id,
            "verdict": arm.verdict,
            "draft_copy": {"path": str(draft_path), "sha256": draft_sha,
                           "rows": len(draft_rows),
                           "rows_recovered_from_the_trace": len(recovered),
                           "scoring_seconds": elapsed},
            "draft_official": {
                "slu_f1_pp": 100 * float(result["aggregate"]["official"]["slu_f1"]),
                "intent_pp": 100 * float(result["aggregate"]["official"]["intent_accuracy"]),
            },
            "summary": summarise_route(rows),
            "rows": rows,
        }

    payload = {
        "schema": SCHEMA,
        "stage": "reviewer",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_profile": "model-free-check",
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "asr": 0,
                     "server": 0, "network": 0,
                     "scorer_official_over_copies": len(REVIEWER_ARMS)},
        "definitions": {
            "draft": "the FIRST Solver role visit's final response, identified by its "
                     "response_text_sha256 in the row's own native episode receipt",
            "delivered": "the row's sealed delivered text",
            "route_revise": "the row's planner_routes contain at least one REVISE",
            "precision": "P(the draft was wrong | the route was REVISE)",
            "recall": "P(the route was REVISE | the draft was wrong)",
        },
        "arms": arms,
    }
    write_json(out_dir / "reviewer.json", payload)
    print(f"reviewer -> {out_dir / 'reviewer.json'}")
    return payload


def summarise_route(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    revise = [r for r in rows if r["route_revise"]]
    out: dict[str, Any] = {
        "rows": total,
        "rows_routed_revise": len(revise),
        "rows_with_an_executed_revision": sum(1 for r in rows if r["revision_executed"]),
        "rows_whose_delivered_text_is_the_initial_draft": sum(
            1 for r in rows if r["draft_is_delivered"]
        ),
        "reviewer_contacts_total": sum(int(r["reviewer_contacts"]) for r in rows),
        "reviewer_visits_histogram": {},
        "planner_route_sequences": {},
        "per_metric": {},
        "delivered_minus_draft": {},
    }
    for row in rows:
        key = str(row["reviewer_visits"])
        out["reviewer_visits_histogram"][key] = out["reviewer_visits_histogram"].get(key, 0) + 1
        seq = " -> ".join(row["planner_routes"]) or "(no planner visit)"
        out["planner_route_sequences"][seq] = out["planner_route_sequences"].get(seq, 0) + 1

    for metric in METRICS:
        wrong = [r for r in rows if not r["draft"][metric]]
        tp = sum(1 for r in revise if not r["draft"][metric])
        fp = len(revise) - tp
        precision = rate(tp, len(revise))
        recall = rate(tp, len(wrong))
        f1 = None
        if precision and recall and (precision + recall) > 0:
            f1 = 2 * precision * recall / (precision + recall)
        saves = sum(1 for r in rows if not r["draft"][metric] and r["delivered"][metric])
        harms = sum(1 for r in rows if r["draft"][metric] and not r["delivered"][metric])
        out["per_metric"][metric] = {
            "draft_correct": sum(1 for r in rows if r["draft"][metric]),
            "delivered_correct": sum(1 for r in rows if r["delivered"][metric]),
            "draft_wrong": len(wrong),
            "revise_and_draft_wrong": tp,
            "revise_and_draft_right": fp,
            "selection_precision": precision,
            "selection_recall": recall,
            "selection_f1": f1,
            "base_rate_draft_wrong": rate(len(wrong), total),
            "saves_draft_wrong_to_delivered_right": saves,
            "harms_draft_right_to_delivered_wrong": harms,
            "net_rows_changed_by_the_loop": saves - harms,
        }
        out["delivered_minus_draft"][metric] = (
            sum(1 for r in rows if r["delivered"][metric])
            - sum(1 for r in rows if r["draft"][metric])
        )

    out["slu_f1_row_mean_pp"] = {
        "draft": 100 * sum(float(r["draft"]["slu_f1"]) for r in rows) / total,
        "delivered": 100 * sum(float(r["delivered"]["slu_f1"]) for r in rows) / total,
    }
    out["auroc_reviewer_visits_vs_draft_wrong"] = auroc(
        [float(r["reviewer_visits"]) for r in rows],
        [not r["draft"]["full_task_exact"] for r in rows],
    )
    out["auroc_route_vs_draft_wrong"] = auroc(
        [1.0 if r["route_revise"] else 0.0 for r in rows],
        [not r["draft"]["full_task_exact"] for r in rows],
    )
    strata: dict[str, dict[str, int]] = {}
    for row in rows:
        entry = strata.setdefault(row["stratum"], {"rows": 0, "revise": 0, "draft_wrong": 0})
        entry["rows"] += 1
        entry["revise"] += 1 if row["route_revise"] else 0
        entry["draft_wrong"] += 0 if row["draft"]["full_task_exact"] else 1
    out["per_stratum"] = dict(sorted(strata.items()))
    return out


# ---------------------------------------------------------------------------
# Stage 2: the rollouts
# ---------------------------------------------------------------------------


def render_answer(payload: Mapping[str, Any] | None) -> str:
    """Render one parsed Solver answer to the canonical delivered payload.

    Byte-for-byte the form ``analysis.native_commit_replay.replay_row`` writes
    for a re-committed row, which is what makes the round trip
    parsed answer -> text -> ``parse_slu_response`` -> official evaluator
    legitimate; the commit replay below asserts that round trip reproduces the
    sealed delivered answer on every row.
    """

    body = EMPTY_ANSWER if payload is None else {
        "scenario": payload.get("scenario", ""),
        "action": payload.get("action", ""),
        "entities": [
            {"type": entity["type"], "filler": entity["filler"]}
            for entity in payload.get("entities", [])
        ],
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True)


def stage_rollouts(
    data_root: Path, repo_root: Path, lock_path: Path, out_dir: Path
) -> dict[str, Any]:
    from speech_aware_evidence_acquisition.analysis.native_commit_replay import (  # noqa: PLC0415
        replay_row,
    )
    from speech_aware_evidence_acquisition.core.base import COMMIT_POLICIES  # noqa: PLC0415
    from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails import commit_policies as _cp  # noqa: PLC0415, F401

    lock = load_lock(lock_path)
    roster = load_roster(repo_root)
    directory = run_dir(data_root, B2_RUN, B2_ATTEMPT)

    twin_runs = sorted(
        p.name for p in (data_root / "runs").iterdir()
        if "SAMPLES5" in p.name and ("TWIN" in p.name or "GREEDY" in p.name
                                     or "REPEAT" in p.name)
    )
    if twin_runs:
        raise VerifierError(
            f"a greedy-repeat twin appears to exist after all: {twin_runs}; "
            "this driver's absence assertion must be revisited"
        )

    sealed = sealed_per_sample(directory, B2_RUN)
    policy = COMMIT_POLICIES.resolve(B2_COMMIT_POLICY)

    samples_text: list[dict[str, str]] = [dict() for _ in range(SAMPLES)]
    committed_text: dict[str, str] = {}
    custody: dict[str, Any] = {
        "rows": 0, "malformed_samples": 0, "rows_with_a_malformed_sample": 0,
        "intent_support_histogram": {},
    }
    support: dict[str, int] = {}

    for row in iter_jsonl(directory / f"{B2_RUN}.outputs.jsonl"):
        sample_id = str(row["sample_id"])
        group = row["solver_group"]
        records = group["samples"]
        if len(records) != SAMPLES:
            raise VerifierError(f"row {sample_id} carries {len(records)} samples")
        malformed = 0
        for record in records:
            index = int(record["sample_index"])
            payload = record["parsed_answer"] if record["parse_status"] == "ok" else None
            malformed += 0 if payload is not None else 1
            samples_text[index][sample_id] = render_answer(payload)
        custody["malformed_samples"] += malformed
        custody["rows_with_a_malformed_sample"] += 1 if malformed else 0
        custody["rows"] += 1
        support[sample_id] = int(group["delivered"]["intent_support"])
        key = str(support[sample_id])
        custody["intent_support_histogram"][key] = (
            custody["intent_support_histogram"].get(key, 0) + 1
        )
        replayed = replay_row(row, policy=policy, commit_params=B2_COMMIT_PARAMS)
        committed_text[sample_id] = str(replayed["final_response_text"])

    if custody["rows"] != ROSTER_ROWS:
        raise VerifierError(f"{B2_RUN}: {custody['rows']} rows, expected {ROSTER_ROWS}")

    ids = sorted(committed_text)
    scored: dict[str, dict[str, Any]] = {}
    sides: list[tuple[str, Mapping[str, str]]] = [
        (f"sample_{index}", samples_text[index]) for index in range(SAMPLES)
    ] + [("committed_replay", committed_text)]
    for name, texts in sides:
        path = out_dir / "b2" / f"{name}-outputs.jsonl"
        digest = write_jsonl(path, [{"sample_id": i, "text": texts[i]} for i in ids])
        result, elapsed = score_copy(
            SCORER, path, out_dir / "b2" / f"{name}-{SCORER}-scores.json", lock, data_root
        )
        scored[name] = {
            "outputs_path": str(path), "outputs_sha256": digest,
            "official_slu_f1_pp": 100 * float(result["aggregate"]["official"]["slu_f1"]),
            "official_intent_pp": 100 * float(result["aggregate"]["official"]["intent_accuracy"]),
            "per_sample": {str(r["sample_id"]): r for r in result["per_sample"]},
            "scoring_seconds": elapsed,
        }
        print(f"[b2] {name}: official slu_f1 {scored[name]['official_slu_f1_pp']:.4f} "
              f"in {elapsed:.1f}s", flush=True)

    # The licence: re-applying the registered commit policy offline must
    # reproduce the sealed delivered answer's own official count fields.
    fields = ("slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn",
              "slu_f1_char_tp", "slu_f1_char_fp", "slu_f1_char_fn",
              "slot_f1_exact_tp", "slot_f1_exact_fp", "slot_f1_exact_fn")
    mismatched = [
        sample_id for sample_id in ids
        if any(float(scored["committed_replay"]["per_sample"][sample_id][field])
               != float(sealed[sample_id][field]) for field in fields)
    ]
    replay_proof = {
        "rows": len(ids),
        "rows_reproducing_every_sealed_official_count_field": len(ids) - len(mismatched),
        "mismatched_rows": mismatched,
        "fields": list(fields),
        "meaning": "the registered commit policy re-applied offline to the sealed raw "
                   "samples reproduces the sealed delivered answer's own official "
                   "counts; that is what licenses scoring the rendered per-sample "
                   "answers on the same instrument",
    }
    if mismatched:
        print(f"[b2] WARNING: the commit replay did not reproduce "
              f"{len(mismatched)} of {len(ids)} rows", flush=True)

    metrics = METRICS
    per_row: list[dict[str, Any]] = []
    for sample_id in ids:
        sample_correct = {
            metric: [
                correctness(scored[f"sample_{index}"]["per_sample"][sample_id])[metric]
                for index in range(SAMPLES)
            ]
            for metric in metrics
        }
        per_row.append({
            "sample_id": sample_id,
            "stratum": roster[sample_id]["stratum"],
            "intent_support": support[sample_id],
            "delivered": correctness(sealed[sample_id]),
            "sample_correct": sample_correct,
            "n_correct": {metric: sum(sample_correct[metric]) for metric in metrics},
        })

    def block(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {"n": len(rows)}
        for metric in metrics:
            cov = {
                f"coverage_at_{k}": 100 * sum(
                    coverage_at_k(int(r["n_correct"][metric]), SAMPLES, k) for r in rows
                ) / len(rows)
                for k in range(1, SAMPLES + 1)
            }
            selection = 100 * sum(1 for r in rows if r["delivered"][metric]) / len(rows)
            out[metric] = {
                **cov,
                "selection_pct": selection,
                "coverage_selection_gap_pp": cov[f"coverage_at_{SAMPLES}"] - selection,
                "selection_over_single_sample_pp": selection - cov["coverage_at_1"],
                "selection_efficiency": (
                    (selection - cov["coverage_at_1"])
                    / (cov[f"coverage_at_{SAMPLES}"] - cov["coverage_at_1"])
                    if cov[f"coverage_at_{SAMPLES}"] > cov["coverage_at_1"] else None
                ),
            }
        return out

    strata: dict[str, list[dict[str, Any]]] = {}
    for row in per_row:
        strata.setdefault(str(row["stratum"]), []).append(row)

    payload = {
        "schema": SCHEMA,
        "stage": "rollouts",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_profile": "model-free-check",
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "asr": 0,
                     "server": 0, "network": 0,
                     "scorer_official_over_copies": len(sides)},
        "arm": {"run_id": B2_RUN, "attempt_id": B2_ATTEMPT, "verdict": B2_VERDICT,
                "samples": SAMPLES, "temperature": 0.7,
                "commit_policy": B2_COMMIT_POLICY, "commit_params": B2_COMMIT_PARAMS},
        "greedy_repeat_twin": {"exists": False, "statement": B2_TWIN_EXPECTED_ABSENT,
                               "runs_searched": "every directory under runs/ whose name "
                                                "contains SAMPLES5 and TWIN/GREEDY/REPEAT"},
        "custody": custody,
        "commit_replay_proof": replay_proof,
        "scored_sides": {
            name: {k: v for k, v in entry.items() if k != "per_sample"}
            for name, entry in scored.items()
        },
        "definitions": {
            "coverage_at_k": "the unbiased estimator 1 - C(n-c, k)/C(n, k) averaged over "
                             "rows, with n = 5 sealed samples and c the number correct; "
                             "coverage@1 is the expected accuracy of ONE random sample "
                             "and coverage@5 is the oracle that always picks a correct "
                             "sample when one exists (Brown et al., arXiv:2407.21787)",
            "selection": "the sealed delivered answer's own official correctness -- for "
                         "this arm the registered plurality/support commit IS the "
                         "selector, so selection and majority vote are the same number "
                         "and the commit replay above proves it",
            "selection_efficiency": "(selection - coverage@1) / (coverage@5 - coverage@1): "
                                    "the share of the available headroom the selector "
                                    "actually captures",
        },
        "pooled": block(per_row),
        "equal_scenario": {
            metric: {
                key: sum(block(rows)[metric][key] for rows in strata.values()) / len(strata)
                for key in (f"coverage_at_{SAMPLES}", "coverage_at_1", "selection_pct")
            }
            for metric in metrics
        },
        "per_stratum": {name: block(rows) for name, rows in sorted(strata.items())},
        "confidence_signal": {
            "intent_support": {
                "what": "the number of the five samples that voted for the committed "
                        "intent -- sealed custody, zero extra contacts",
                **{
                    metric: auroc(
                        [float(r["intent_support"]) for r in per_row],
                        [bool(r["delivered"][metric]) for r in per_row],
                    )
                    for metric in metrics
                },
                "accuracy_by_support": {
                    str(level): {
                        "rows": sum(1 for r in per_row if r["intent_support"] == level),
                        "delivered_intent_correct": sum(
                            1 for r in per_row
                            if r["intent_support"] == level and r["delivered"]["intent_exact"]
                        ),
                    }
                    for level in range(1, SAMPLES + 1)
                },
            },
        },
        "rows": per_row,
    }
    write_json(out_dir / "rollouts.json", payload)
    print(f"rollouts -> {out_dir / 'rollouts.json'}")
    return payload


# ---------------------------------------------------------------------------
# Stage: primitives (item E37, owner decision 84, 2026-09-22)
#
# Decision 74: measure the verifier first. The closed-vocabulary Reviewer
# (rails.review_primitives) is the first Reviewer output this driver can
# actually PARSE -- 0 of 2,167 anchor/B1/B1notool Reviewer outputs parse
# under rails.review_findings' declared JSON contract -- so this stage is
# the one this module owes decision 74 for cell R-PRIM, once R-PRIM has a
# sealed arm. Until then it is proved on a SYNTHETIC receipt set with known
# precision (tests/unit/test_e37_reviewer_verdict.py); no sealed run,
# scorer or SPEECHRL_DATA_DIR read is needed for that proof.
# ---------------------------------------------------------------------------


#: The REVISE-* subset of the closed vocabulary: every legal token that
#: asserts the draft has a supported issue, as opposed to ACCEPT (no issue)
#: and UNSURE (no decision).
REVISE_PRIMITIVE_TOKENS = frozenset(
    token for token in REVIEW_PRIMITIVE_TOKENS if token.startswith("REVISE-")
)

#: The two non-token dispositions a mark may carry beside a legal token,
#: reused verbatim as pseudo-token labels in the per-token breakdowns below
#: so an illegal or exhausted visit is counted, never dropped silently.
_ILLEGAL_LABEL = REVIEWER_VERDICT_ILLEGAL_DISPOSITION
_EXHAUSTED_LABEL = REACT_EXHAUSTION_DISPOSITION


def _mark_label(mark: Mapping[str, Any]) -> str:
    """The one label a ``reviewer_verdicts`` mark contributes to every
    per-token count below: its legal token, or its disposition when it
    carries none."""

    token = mark.get("token")
    if isinstance(token, str) and token:
        return token
    return str(mark.get("disposition"))


def primitive_verdict_stats(
    rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Item E37 deliverable 6: the primitives stage's whole computation, as a
    PURE function over already-scanned rows -- no file, scorer or network
    access of any kind, so it is exactly as testable on a synthetic receipt
    set as it is on a real ``scan_episodes`` output.

    Each ``rows[sample_id]`` is a mapping carrying at least:
      * ``reviewer_verdicts``: the list ``scan_episodes`` now collects (one
        mark per Reviewer visit, or ``None``/absent on an unarmed row);
      * ``official_correct``: whether the row's DELIVERED answer was
        officially correct (bool);
      * ``planner_routes``: the row's ordered Planner actions, one per
        revision round, exactly as ``scan_episodes`` already returns them.

    Returns parse rate, per-token visit counts, REVISE-* precision/recall
    against ``official_correct``, the token x correctness confusion table,
    cross-visit agreement (rows with 2+ Reviewer visits whose legal tokens
    all match) and the Planner route conditioned on the SAME-round token.
    """

    armed_rows = {
        sample_id: entry
        for sample_id, entry in rows.items()
        if entry.get("reviewer_verdicts")
    }
    total_visits = 0
    legal_visits = 0
    token_counts: dict[str, int] = {}
    confusion: dict[str, dict[str, int]] = {}
    route_by_token: dict[str, dict[str, int]] = {}
    agreeing_rows = 0
    multi_visit_rows = 0
    predicted_wrong_rows = 0
    actual_wrong_rows = 0
    both_wrong_rows = 0

    for entry in armed_rows.values():
        marks = list(entry["reviewer_verdicts"])
        routes = list(entry.get("planner_routes") or ())
        official_correct = bool(entry["official_correct"])
        actual_wrong = not official_correct
        if actual_wrong:
            actual_wrong_rows += 1
        total_visits += len(marks)

        legal_tokens_this_row: list[str] = []
        row_predicts_wrong = False
        for mark in marks:
            label = _mark_label(mark)
            token_counts[label] = token_counts.get(label, 0) + 1
            bucket = confusion.setdefault(label, {"correct": 0, "incorrect": 0})
            bucket["correct" if official_correct else "incorrect"] += 1
            if label in REVIEW_PRIMITIVE_TOKENS:
                legal_visits += 1
                if label in REVISE_PRIMITIVE_TOKENS:
                    row_predicts_wrong = True
                legal_tokens_this_row.append(label)
            visit_index = mark.get("visit")
            if isinstance(visit_index, int) and 0 <= visit_index < len(routes):
                route_counts = route_by_token.setdefault(label, {})
                route_counts[routes[visit_index]] = route_counts.get(routes[visit_index], 0) + 1

        if row_predicts_wrong:
            predicted_wrong_rows += 1
            if actual_wrong:
                both_wrong_rows += 1
        if len(marks) >= 2:
            multi_visit_rows += 1
            if len(set(legal_tokens_this_row)) <= 1 and len(legal_tokens_this_row) == len(marks):
                agreeing_rows += 1

    def _rate(numerator: int, denominator: int) -> float | None:
        return None if denominator == 0 else numerator / denominator

    return {
        "schema": "saea-slurp-verifier-primitives-v1",
        "armed_rows": len(armed_rows),
        "total_rows": len(rows),
        "total_visits": total_visits,
        "legal_visits": legal_visits,
        "parse_rate": _rate(legal_visits, total_visits),
        "token_counts": dict(sorted(token_counts.items())),
        "confusion": {
            label: dict(sorted(buckets.items())) for label, buckets in sorted(confusion.items())
        },
        "revise_precision": _rate(both_wrong_rows, predicted_wrong_rows),
        "revise_recall": _rate(both_wrong_rows, actual_wrong_rows),
        "predicted_wrong_rows": predicted_wrong_rows,
        "actual_wrong_rows": actual_wrong_rows,
        "cross_visit_agreement_rate": _rate(agreeing_rows, multi_visit_rows),
        "multi_visit_rows": multi_visit_rows,
        "route_by_token": {
            label: dict(sorted(counts.items())) for label, counts in sorted(route_by_token.items())
        },
    }


@dataclass(frozen=True)
class PrimitiveArm:
    key: str
    label: str
    run_id: str
    attempt_id: str
    verdict: str


#: Empty until cell R-PRIM has flown and a verdict names its sealed arm --
#: exactly the discipline ``docs/receipts/harness-admission.json``'s PENDING
#: entry for native_episode.reviewer_verdict states: this module invents no
#: sealed data, so ``stage_primitives`` refuses to run rather than read
#: nothing and report zeros.
PRIMITIVE_ARMS: tuple[PrimitiveArm, ...] = (
    PrimitiveArm(
        "rprim", "cell R-PRIM (item E37: the Reviewer verdict as a closed set of primitives, on the locked plan)",
        "SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-V1",
        "attempt-slurp-native-review-primitives-train-fold-a-generation-v1",
        "docs/results/2026-09-22-slurp-review-primitives-verdict.md",
    ),
)


def stage_primitives(
    data_root: Path, repo_root: Path, lock_path: Path, out_dir: Path
) -> dict[str, Any]:
    """Item E37: parse rate, per-token counts, REVISE-* precision/recall,
    the token x correctness confusion table, cross-visit agreement and the
    Planner route conditioned on the token -- for every arm of
    :data:`PRIMITIVE_ARMS`. Model-free: it scores a COPY of each arm's
    already-sealed delivered answers, exactly as :func:`stage_reviewer`
    does, and never opens a run directory for writing.
    """

    from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: PLC0415

    if not PRIMITIVE_ARMS:
        payload = {
            "schema": "saea-slurp-verifier-primitives-v1",
            "arms": {},
            "note": (
                "PRIMITIVE_ARMS is empty: cell R-PRIM (native_episode.reviewer_verdict, "
                "item E37) is registered and HELD, not flown. This stage refuses to "
                "invent a sealed arm; rerun it once a verdict names one. The pure "
                "computation (primitive_verdict_stats) is proved on a synthetic "
                "receipt set by tests/unit/test_e37_reviewer_verdict.py."
            ),
        }
        write_json(out_dir / "primitives.json", payload)
        print("primitives -> SKIP: PRIMITIVE_ARMS is empty (cell R-PRIM has not flown)")
        return payload

    lock = load_lock(lock_path)
    arms: dict[str, Any] = {}
    for arm in PRIMITIVE_ARMS:
        directory = run_dir(data_root, arm.run_id, arm.attempt_id)
        episodes = scan_episodes(directory, arm.run_id)
        draft_rows = [
            {"sample_id": sample_id, "text": entry["delivered_text"]}
            for sample_id, entry in sorted(episodes.items())
        ]
        work = out_dir / "primitives" / arm.key
        draft_path = work / "delivered-outputs.jsonl"
        write_jsonl(draft_path, draft_rows)
        result, elapsed = score_copy(
            SCORER, draft_path, work / f"{SCORER}-delivered-scores.json", lock, data_root
        )
        print(f"[{arm.key}] delivered copy scored in {elapsed:.1f}s", flush=True)
        scores = {str(r["sample_id"]): r for r in result["per_sample"]}
        rows = {
            sample_id: {
                "reviewer_verdicts": entry["reviewer_verdicts"],
                "planner_routes": entry["planner_routes"],
                "official_correct": correctness(scores[sample_id])["full_task_exact"],
            }
            for sample_id, entry in episodes.items()
        }
        arms[arm.key] = {
            "label": arm.label, "run_id": arm.run_id, "attempt_id": arm.attempt_id,
            "verdict": arm.verdict, "stats": primitive_verdict_stats(rows),
        }
    payload = {"schema": "saea-slurp-verifier-primitives-v1", "arms": arms}
    write_json(out_dir / "primitives.json", payload)
    print(f"primitives -> {out_dir / 'primitives.json'}")
    return payload


# ---------------------------------------------------------------------------
# Stage 3: report
# ---------------------------------------------------------------------------


def pct(value: Any, places: int = 2) -> str:
    if value is None:
        return "--"
    return f"{float(value):.{places}f}"


def report(reviewer: Mapping[str, Any], rollouts: Mapping[str, Any]) -> str:
    lines: list[str] = []
    add = lines.append

    add("## Table B1 -- the route as a verifier (per-row official correctness of the "
        "initial draft against the Planner's ACCEPT/REVISE route)")
    add("")
    add("| Arm | Rows | Reviewer contacts | Rows routed REVISE | Revisions executed "
        "| Draft wrong (full task) | REVISE & wrong | Precision | Recall | Saves | Harms |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for key, arm in reviewer["arms"].items():
        s = arm["summary"]
        m = s["per_metric"]["full_task_exact"]
        add("| {key} | {rows} | {rc} | {rev} | {ex} | {wrong} | {tp} | {p} | {r} | {sv} | {hm} |".format(
            key=key, rows=s["rows"], rc=s["reviewer_contacts_total"],
            rev=s["rows_routed_revise"], ex=s["rows_with_an_executed_revision"],
            wrong=m["draft_wrong"], tp=m["revise_and_draft_wrong"],
            p=pct(None if m["selection_precision"] is None else 100 * m["selection_precision"], 1) + " %",
            r=pct(None if m["selection_recall"] is None else 100 * m["selection_recall"], 2) + " %",
            sv=m["saves_draft_wrong_to_delivered_right"],
            hm=m["harms_draft_right_to_delivered_wrong"],
        ))
    add("")

    add("## Table B2 -- what the loop moved, per metric")
    add("")
    add("| Arm | Metric | Draft correct | Delivered correct | Net | Saves | Harms | "
        "Route precision | Route recall |")
    add("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for key, arm in reviewer["arms"].items():
        for metric, m in arm["summary"]["per_metric"].items():
            add("| {k} | {mm} | {dc} | {vc} | {net:+d} | {sv} | {hm} | {p} | {r} |".format(
                k=key, mm=metric, dc=m["draft_correct"], vc=m["delivered_correct"],
                net=m["delivered_correct"] - m["draft_correct"],
                sv=m["saves_draft_wrong_to_delivered_right"],
                hm=m["harms_draft_right_to_delivered_wrong"],
                p=pct(None if m["selection_precision"] is None else 100 * m["selection_precision"], 1) + " %",
                r=pct(None if m["selection_recall"] is None else 100 * m["selection_recall"], 2) + " %",
            ))
    add("")

    add("## Table B3 -- coverage against selection on the B2 v3 rollouts (N = 5, pooled)")
    add("")
    add("| Metric | coverage@1 | coverage@2 | coverage@3 | coverage@4 | coverage@5 | "
        "selection (the commit) | coverage@5 - selection | selection - coverage@1 | "
        "selection efficiency |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for metric, block in rollouts["pooled"].items():
        if metric == "n":
            continue
        add("| {m} | {c1} | {c2} | {c3} | {c4} | {c5} | {sel} | {gap:+.2f} | {over:+.2f} | {eff} |".format(
            m=metric, c1=pct(block["coverage_at_1"]), c2=pct(block["coverage_at_2"]),
            c3=pct(block["coverage_at_3"]), c4=pct(block["coverage_at_4"]),
            c5=pct(block["coverage_at_5"]), sel=pct(block["selection_pct"]),
            gap=block["coverage_selection_gap_pp"],
            over=block["selection_over_single_sample_pp"],
            eff=pct(None if block["selection_efficiency"] is None
                    else 100 * block["selection_efficiency"], 1) + " %",
        ))
    add("")

    add("## Table B4 -- coverage against selection per scenario (full-task exact)")
    add("")
    add("| Scenario | n | coverage@1 | coverage@5 | selection | gap | selection efficiency |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for scenario, block in rollouts["per_stratum"].items():
        entry = block["full_task_exact"]
        add("| {s} | {n} | {c1} | {c5} | {sel} | {gap:+.2f} | {eff} |".format(
            s=scenario, n=block["n"], c1=pct(entry["coverage_at_1"]),
            c5=pct(entry["coverage_at_5"]), sel=pct(entry["selection_pct"]),
            gap=entry["coverage_selection_gap_pp"],
            eff=pct(None if entry["selection_efficiency"] is None
                    else 100 * entry["selection_efficiency"], 1) + " %",
        ))
    add("")

    add("## Table B5 -- every confidence-like signal the sealed receipts carry, ranked by AUROC")
    add("")
    add("| Signal | Arm | Target | AUROC | n positive | n negative | Distinct values |")
    add("| --- | --- | --- | ---: | ---: | ---: | ---: |")
    support = rollouts["confidence_signal"]["intent_support"]
    for metric in METRICS:
        block = support[metric]
        add("| sample-agreement count (1..5) | B2 v3 | delivered {m} correct | {a} | {p} | {n} | {d} |".format(
            m=metric,
            a=pct(block.get("auroc"), 3), p=block.get("n_positive"),
            n=block.get("n_negative"), d=block.get("distinct_scores", "--"),
        ))
    for key, arm in reviewer["arms"].items():
        for name, target in (("auroc_reviewer_visits_vs_draft_wrong", "Reviewer iteration count"),
                             ("auroc_route_vs_draft_wrong", "the REVISE route itself")):
            block = arm["summary"][name]
            add("| {t} | {k} | the draft is WRONG (full task) | {a} | {p} | {n} | {d} |".format(
                t=target, k=key, a=pct(block.get("auroc"), 3),
                p=block.get("n_positive"), n=block.get("n_negative"),
                d=block.get("distinct_scores", "--"),
            ))
    add("")
    add("The Reviewer's own findings are NOT in this table and cannot be: "
        "`rails.review_findings.parse_review_findings` fails on 2,167 of 2,167 Reviewer "
        "outputs of the anchor (docs/results/2026-09-17-slurp-node-context-audit-v1.md, "
        "section 6), so there is no finding count, no severity and no citation set to "
        "rank. The Reviewer speaks prose and nothing parses it.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------


def self_check(data_root: Path, out_dir: Path) -> int:
    path = out_dir / "reviewer.json"
    if not path.is_file():
        print(f"SELF-CHECK SKIP: run --stage reviewer first ({path} is missing)")
        return 1
    document = json.loads(path.read_text(encoding="utf-8"))
    summary = document["arms"]["anchor"]["summary"]
    intent = summary["per_metric"]["intent_exact"]
    entities = summary["per_metric"]["entity_set_exact"]
    full = summary["per_metric"]["full_task_exact"]
    got = {
        "draft_intent_correct": intent["draft_correct"],
        "delivered_intent_correct": intent["delivered_correct"],
        "intent_saves": intent["saves_draft_wrong_to_delivered_right"],
        "intent_harms": intent["harms_draft_right_to_delivered_wrong"],
        "draft_entity_set_exact": entities["draft_correct"],
        "delivered_entity_set_exact": entities["delivered_correct"],
        "draft_full_task_exact": full["draft_correct"],
        "delivered_full_task_exact": full["delivered_correct"],
        "planner_revise_rows": summary["rows_routed_revise"],
    }
    want = SELF_CHECK["expected"]
    ok = got == want
    print(f"SELF-CHECK {'PASS' if ok else 'FAIL'} {SELF_CHECK['name']}: "
          f"recomputed {got} against the pinned {want}; source {SELF_CHECK['source']}")
    return 0 if ok else 1


#: "primitives" (item E37) is deliberately NOT part of "all": PRIMITIVE_ARMS
#: is empty until cell R-PRIM has flown, and this driver never silently
#: no-ops inside a bundled run -- a caller who wants the empty-arm receipt
#: must ask for "primitives" by name.
STAGES = ("reviewer", "rollouts", "report", "primitives", "all")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="slurp_verifier_measurement.py",
        description=(
            "Selection precision/recall of the SLURP review loop, coverage versus "
            "selection on the B2 v3 rollouts, and every confidence-like signal the "
            "sealed receipts carry (owner decision 74). Model-free."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--stage", choices=STAGES, default="all")
    parser.add_argument("--data-root", type=Path, default=None,
                        help="SPEECHRL_DATA_DIR (default: the environment variable)")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT,
                        help="the study checkout that owns the roster receipt")
    parser.add_argument("--lock-path", type=Path, default=None,
                        help="the umbrella docs/datasets.lock.json the scorers resolve gold through")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="default: <data-root>/analysis/SAEA-SLURP-STAGE3-PRELUDE-V1/verifier")
    parser.add_argument("--self-check", action="store_true",
                        help="recompute one pinned number from the reviewer stage's own "
                             "output and exit non-zero on a mismatch")
    args = parser.parse_args(argv)

    data_root = args.data_root or Path(os.environ.get("SPEECHRL_DATA_DIR", ""))
    if not data_root or not data_root.is_dir():
        parser.error("--data-root (or SPEECHRL_DATA_DIR) must name an existing directory")
    out_dir = args.out_dir or (
        data_root / "analysis" / "SAEA-SLURP-STAGE3-PRELUDE-V1" / "verifier"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.self_check:
        return self_check(data_root, out_dir)

    lock_path = args.lock_path or (
        args.repo_root.resolve().parents[1] / "docs" / "datasets.lock.json"
    )
    if args.stage in ("reviewer", "rollouts", "all") and not lock_path.is_file():
        parser.error(f"--lock-path must name the umbrella lock (tried {lock_path})")
    if args.stage == "primitives" and PRIMITIVE_ARMS and not lock_path.is_file():
        parser.error(f"--lock-path must name the umbrella lock (tried {lock_path})")

    if args.stage in ("reviewer", "all"):
        stage_reviewer(data_root, args.repo_root, lock_path, out_dir)
    if args.stage in ("rollouts", "all"):
        stage_rollouts(data_root, args.repo_root, lock_path, out_dir)
    if args.stage == "primitives":
        stage_primitives(data_root, args.repo_root, lock_path, out_dir)
    if args.stage in ("report", "all"):
        reviewer = json.loads((out_dir / "reviewer.json").read_text(encoding="utf-8"))
        rollouts = json.loads((out_dir / "rollouts.json").read_text(encoding="utf-8"))
        text = report(reviewer, rollouts)
        (out_dir / "verifier-tables.md").write_text(text, encoding="utf-8", newline="\n")
        print(f"report -> {out_dir / 'verifier-tables.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
