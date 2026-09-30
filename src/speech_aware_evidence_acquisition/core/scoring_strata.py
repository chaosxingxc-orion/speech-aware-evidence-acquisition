"""``--strata-inside-scorer``: aggregate-only post-stratification inside the official-scoring step.

WHY (coordinator ruling 2026-09-30). The milestone read on the signed test sample
(``SLURP-TEST-SAMPLE-3010-V1``, floored, stratified by gold intent) must be post-stratified, but
its roster receipt allows gold only as "per-intent aggregate counts only; no label beside a sample
id" (decision 141 item 5) and the allowance lets gold be read "ONLY by the official scorer, after
delivery". A per-row gold bank is therefore not a legal channel. Post-stratification happens HERE,
in the official-scoring step, which already sees gold after delivery, and leaves it as AGGREGATES
ONLY.

WHAT. :func:`score_paired_strata` takes two sealed official score results (the ``<run>.scores.json``
of each arm, or a derived column's score, both ``{scorer_id: {"per_sample": [...], "aggregate":
{...}}}``) scored by the SAME registered official SLURP scorer, the roster receipt, and the
receipt-derived population counts. Inside this process it

1. refuses before any gold is touched: an unknown scorer id, a roster receipt without a
   ``stratification`` block, an output path that exists, is not a ``.json`` file, or sits in a
   directory it cannot write, and any request for a per-row file;
2. matches both arms' official per-sample rows by ``sample_id`` against the roster (every roster
   row, nothing else, each arm's official identity check passed);
3. reads each row's gold intent ``scenario_action`` through the official scorer's own gold binding
   (``reproduction.slurp_official_eval.official_gold_intents``), in memory only;
4. computes, per gold-intent stratum, ``n_h`` and each arm's ``intent_correct_h`` / ``TP_h`` /
   ``FP_h`` / ``FN_h`` (pooled SLU-F1 word + char totals), and runs the paired bootstraps ITSELF
   through the shared estimators (``analysis.stratified_paired``): per-stratum intervals and the
   raw, post-stratified and equal-stratum deltas, within-stratum resampling (raw: the roster's own
   mixture), ``draws`` draws, ``seed``, clusters from the roster's ``cluster_key``;
5. writes ONE file -- the aggregate receipt (schema ``saea-scorer-strata-aggregate-v1``) -- after
   proving its serialised bytes carry no roster sample id; its ``receipt_sha256`` is the canonical
   hash of the rest of the document.

SAME DRAWS AS THE READ DRIVER. ``scripts/analysis/stage3_paired_read.py``'s gold-bank path and
this step call the same functions with the same sorted roster ids, the same stratum values (the
gold intent string, which is exactly the bank's ``gold_intent``: ``data.slurp`` computes both as
``f"{scenario}_{action}"``), the same cluster function, seed and draw count.
``analysis.paired.resampled_statistic`` seeds a fresh ``random.Random(seed)`` per bootstrap and
walks strata in ascending name order, so the two paths draw identical bootstrap indices and
produce identical floats.

NEVER WRITTEN: a per-row stratum; any row-level output that pairs a sample id (or an utterance id)
with a gold field; a gold label beside an id; utterance text; model output. The receipt carries
stratum names (gold intents) only as keys of per-stratum AGGREGATES, the form the roster receipt
itself publishes.

MODEL-FREE: zero model, tokenizer, encoder and network contacts; the only data-root read is the
official scorer's gold binding (and the flac-header check that binding always performs).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..analysis import stratified_paired as SP

SCHEMA = "saea-scorer-strata-aggregate-v1"
DEFAULT_SEED = 20260929
DEFAULT_DRAWS = 10_000

NEVER_WRITTEN = (
    "a per-row stratum",
    "any row-level output pairing a sample id or utterance id with a gold field",
    "a gold label string beside any id",
    "utterance text, transcripts or model output",
)

GoldIntents = Callable[[str, Sequence[str]], Mapping[str, str]]


class ScorerStrataError(RuntimeError):
    """The scorer-side stratified read refuses; nothing is written."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_json(path: Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _official_rows(path: Path, scorer_id: str, label: str) -> dict[str, dict[str, float]]:
    """``{sample_id: {field: float}}`` from one sealed official score result -- the paired roster
    read's ``_rows_table`` rule (booleans to 0/1, numbers kept, other types skipped, a text value
    refused)."""

    document = _load_json(path)
    if isinstance(document, Mapping) and "scores" in document and scorer_id not in document:
        document = document["scores"]  # a ``core.driver score --include-per-sample`` stdout file
    entry = document.get(scorer_id) if isinstance(document, Mapping) else None
    if not isinstance(entry, Mapping):
        raise ScorerStrataError(f"{label} scores carry no {scorer_id!r} result")
    identity = ((entry.get("aggregate") or {}).get("identity_check") or {})
    if identity.get("passed") is not True:
        raise ScorerStrataError(f"{label} {scorer_id} result did not pass the official identity check")
    per_sample = entry.get("per_sample")
    if not isinstance(per_sample, list) or not per_sample:
        raise ScorerStrataError(f"{label} {scorer_id} result carries no per_sample rows")
    table: dict[str, dict[str, float]] = {}
    for row in per_sample:
        sample_id = row.get("sample_id") if isinstance(row, Mapping) else None
        if not isinstance(sample_id, str) or not sample_id or sample_id in table:
            raise ScorerStrataError(f"{label} per_sample rows need unique sample ids")
        values: dict[str, float] = {}
        for key, value in row.items():
            if key == "sample_id":
                continue
            if isinstance(value, str):
                raise ScorerStrataError(f"{label} per_sample field {key!r} is text; refused")
            if isinstance(value, bool):
                values[key] = 1.0 if value else 0.0
            elif isinstance(value, (int, float)):
                values[key] = float(value)
        table[sample_id] = values
    return table


def _roster(path: Path, cluster_key: str) -> tuple[dict, list[str], dict[str, str]]:
    document = _load_json(path)
    if not isinstance(document, Mapping):
        raise ScorerStrataError("the roster receipt is not a JSON object")
    stratification = document.get("stratification")
    if not isinstance(stratification, Mapping) or not stratification:
        raise ScorerStrataError(
            "--strata-inside-scorer refuses a roster whose receipt carries no 'stratification' "
            "block: only a roster DESIGNED as stratified is post-stratified inside the scorer"
        )
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise ScorerStrataError("the roster receipt carries no items")
    cluster_of: dict[str, str] = {}
    for item in items:
        sample_id = item.get("sample_id") or item.get("id") if isinstance(item, Mapping) else None
        if not isinstance(sample_id, str) or not sample_id or sample_id in cluster_of:
            raise ScorerStrataError("the roster receipt needs unique, non-empty item sample ids")
        cluster = item.get(cluster_key)
        if not isinstance(cluster, str) or not cluster:
            raise ScorerStrataError(f"a roster item carries no usable {cluster_key!r}")
        cluster_of[sample_id] = cluster
    return dict(document), sorted(cluster_of), cluster_of


def _check_output(output: Path) -> None:
    if output.suffix != ".json":
        raise ScorerStrataError("--output must name ONE aggregate .json receipt")
    if output.exists():
        raise ScorerStrataError(f"{output} already exists; an aggregate receipt is never overwritten")
    if not output.parent.is_dir():
        raise ScorerStrataError(f"{output.parent} is not a directory")


def default_gold_intents(lock: Mapping[str, object], data_root: Path) -> GoldIntents:
    """The official scorer's own gold binding (deferred import: nothing touches the data root
    until every refusal above has passed)."""

    def gold(scorer_id: str, sample_ids: Sequence[str]) -> Mapping[str, str]:
        from ..reproduction.slurp_official_eval import official_gold_intents

        return official_gold_intents(scorer_id, sample_ids, lock, data_root)

    return gold


def _assert_aggregate_only(text: str, ids: Sequence[str]) -> None:
    leaked = sum(1 for sample_id in ids if sample_id in text)
    if leaked:
        raise ScorerStrataError(
            f"refusing to write: the aggregate receipt would carry {leaked} roster sample id(s)"
        )


def score_paired_strata(
    *,
    scorer_id: str,
    left_scores: Path,
    right_scores: Path,
    roster: Path,
    population_counts: Path,
    output: Path,
    cluster_key: str = "sample_id",
    seed: int = DEFAULT_SEED,
    draws: int = DEFAULT_DRAWS,
    gold_intents: GoldIntents,
    population_counts_label: str | None = None,
    labels: tuple[str, str] = ("left", "right"),
) -> dict[str, object]:
    """Stratify two official score results by gold intent inside the scoring step and write ONE
    aggregate receipt; returns the receipt document (module docstring)."""

    from ..reproduction.slurp_official_eval import OFFICIAL_GOLD_SPLIT_OF_SCORER

    output, left_scores, right_scores = Path(output), Path(left_scores), Path(right_scores)
    roster, population_counts = Path(roster), Path(population_counts)
    if scorer_id not in OFFICIAL_GOLD_SPLIT_OF_SCORER:
        raise ScorerStrataError(
            f"{scorer_id!r} is not an official SLURP scorer binding; known: "
            f"{sorted(OFFICIAL_GOLD_SPLIT_OF_SCORER)}"
        )
    if isinstance(draws, bool) or not isinstance(draws, int) or draws <= 0:
        raise ScorerStrataError("draws must be a positive integer")
    _check_output(output)
    roster_doc, ids, cluster_map = _roster(roster, cluster_key)
    counts_doc = _load_json(population_counts)
    left_rows = _official_rows(left_scores, scorer_id, labels[0])
    right_rows = _official_rows(right_scores, scorer_id, labels[1])
    for label, rows in zip(labels, (left_rows, right_rows)):
        if set(rows) != set(ids):
            raise ScorerStrataError(f"the {label} arm's scored rows are not exactly the roster")

    # Gold enters here, in memory only, through the official scorer's own binding.
    gold = dict(gold_intents(scorer_id, ids))
    if set(gold) != set(ids) or any(not isinstance(gold[s], str) or not gold[s] for s in ids):
        raise ScorerStrataError("the gold binding did not return one intent for every roster row")

    def stratum_of(sample_id: str) -> str:
        return gold[sample_id]

    def cluster_of(sample_id: str) -> str:
        return cluster_map[sample_id]

    strata = sorted(set(gold.values()))
    try:
        weights = SP.population_weights(counts_doc, strata, label="--population-counts")
        numbers = SP.stratified_paired_read(
            left_rows, right_rows, ids, stratum_of=stratum_of, cluster_of=cluster_of,
            weights=weights, seed=seed, draws=draws,
        )
    except (SP.StratifiedPairedError, ValueError) as error:
        raise ScorerStrataError(str(error)) from error
    members = SP.stratum_members(ids, stratum_of)
    per_stratum: dict[str, dict] = {}
    for stratum, row in numbers["per_stratum"].items():  # type: ignore[union-attr]
        per_stratum[stratum] = {
            **row,
            "counts": {
                labels[0]: SP.stratum_counts(left_rows, members[stratum]),
                labels[1]: SP.stratum_counts(right_rows, members[stratum]),
            },
        }
    del gold, members  # nothing row-level survives past this point
    split_id, _ = OFFICIAL_GOLD_SPLIT_OF_SCORER[scorer_id]
    document: dict[str, object] = {
        "schema": SCHEMA,
        "mode": "--strata-inside-scorer",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "network": 0,
                     "gold": f"official scorer binding {scorer_id} ({split_id}), in memory, after delivery"},
        "scorer_id": scorer_id,
        "gold_split": split_id,
        "seed": seed,
        "draws": draws,
        "cluster_key": cluster_key,
        "sign_convention": f"delta = {labels[1]} minus {labels[0]}",
        "stratum_definition": "gold intent scenario_action, read by the official scorer's own gold binding",
        "inputs": {
            "left_scores": {"path": str(left_scores), "sha256": _sha256(left_scores)},
            "right_scores": {"path": str(right_scores), "sha256": _sha256(right_scores)},
            "roster": {"path": str(roster), "sha256": _sha256(roster),
                       "roster_id": roster_doc.get("roster_id"), "rows": len(ids),
                       "stratification_block": True},
            "population_counts": {"path": population_counts_label or str(population_counts),
                                  "sha256": _sha256(population_counts)},
        },
        "strata_count": len(per_stratum),
        "per_stratum": per_stratum,
        "weightings": {
            "raw": {"definition": "the roster's own mixture (no reweighting); unstratified "
                                  "paired cluster bootstrap", **numbers["raw"]},  # type: ignore[dict-item]
            "post_stratified": {
                "definition": SP.POST_STRATIFIED_DEFINITION,
                "population_weights": weights,
                "dropped_strata": SP.dropped_strata(counts_doc, strata),
                **numbers["post_stratified"],  # type: ignore[dict-item]
            },
            "equal_stratum": {
                "definition": "the unweighted mean over strata of the per-stratum deltas",
                **numbers["equal_stratum"],  # type: ignore[dict-item]
            },
        },
        "resampling": ("per-stratum and weighted deltas: paired cluster bootstrap WITHIN "
                       "gold-intent strata (each stratum resampled to its own size, strata in "
                       "ascending name order, one fresh random.Random(seed) per bootstrap); raw: "
                       "unstratified, exactly the paired roster read's contrast"),
        "never_written": list(NEVER_WRITTEN),
    }
    document["receipt_sha256"] = SP.canonical_digest(document, exclude=("receipt_sha256",))
    text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    _assert_aggregate_only(text, ids)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m speech_aware_evidence_acquisition.core.scoring_strata",
        description="Aggregate-only post-stratification inside the official-scoring step.",
    )
    parser.add_argument("--strata-inside-scorer", action="store_true", required=True,
                        help="the mode switch; required, so no call stratifies by accident")
    parser.add_argument("--scorer-id", required=True)
    parser.add_argument("--left-scores", required=True)
    parser.add_argument("--right-scores", required=True)
    parser.add_argument("--roster", required=True)
    parser.add_argument("--population-counts", required=True)
    parser.add_argument("--population-counts-label", default=None)
    parser.add_argument("--output", required=True, help="ONE aggregate .json receipt (never overwritten)")
    parser.add_argument("--cluster-key", default="sample_id")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--lock-path", default=None)
    # Present only to be refused by name: this mode never writes a per-row file.
    for flag in ("--include-per-sample", "--per-row-output", "--per-row"):
        parser.add_argument(flag, dest=flag.strip("-").replace("-", "_"), default=None, nargs="?", const=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    for name in ("include_per_sample", "per_row_output", "per_row"):
        if getattr(args, name) is not None:
            print("REFUSED: --strata-inside-scorer never writes a per-row file", file=sys.stderr)
            return 2
    try:
        from ..data.lock import data_root, load_lock, umbrella_lock_path

        lock = load_lock(Path(args.lock_path) if args.lock_path else umbrella_lock_path())
        root = Path(args.data_root) if args.data_root else data_root()
        score_paired_strata(
            scorer_id=args.scorer_id, left_scores=Path(args.left_scores),
            right_scores=Path(args.right_scores), roster=Path(args.roster),
            population_counts=Path(args.population_counts), output=Path(args.output),
            cluster_key=args.cluster_key, seed=args.seed, draws=args.draws,
            gold_intents=default_gold_intents(lock, root),
            population_counts_label=args.population_counts_label,
        )
    except Exception as error:  # noqa: BLE001 -- every refusal is reported, nothing is written
        print(f"REFUSED: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
