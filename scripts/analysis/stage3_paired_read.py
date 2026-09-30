#!/usr/bin/env python3
"""stage3_paired_read.py -- the ONE standard paired read of a sealed Stage-3 arm against a sealed
comparator (owner decision 163: "one standard Fold-A paired read driver with per-scenario tables and
delivery/conversion").

WHY A NEW FILE. The programme-standard paired roster read ``scripts/analysis/slurp_paired_roster_read.py``
works on any sealed pair but declines the per-scenario table on a TRAIN roster and computes no
delivery / conversion or frontier numbers; ``plan_cell_read.py`` needs a registered-facts shape most
new packages do not carry; and cell AGREE's quantities "beside every verdict" had to be written by a
one-off script (``slurp_agree_beside_read.py``). This driver IMPORTS the paired roster read (by path,
unmodified) and runs its five stages exactly, then adds three optional extension stages:

``--per-scenario``
    per-scenario tables from a per-row stratum (``--strata-key``, default ``stratum``), for intent
    (``scenario_action_exact``) and the official pooled SLU-F1 (``slu_f1_micro``), reported as
    THREE weightings side by side: ``raw`` (pooled over every roster row in its own mixture --
    labelled "raw roster mean (not a population estimate)" whenever the roster receipt declares a
    floor, per ``--roster-floored``), ``post-stratified`` (population-weighted: each stratum's
    delta -- or, for SLU-F1, its TP/FP/FN totals, weighted and summed BEFORE the F1 formula is
    applied, never each stratum's own F1 score -- weighted by its population share, from
    ``--population-counts``, a receipt-derived ``{stratum: population_count}`` JSON; see
    ``build_population_counts.py``), and ``equal-stratum`` (the unweighted mean of the per-stratum
    deltas). ``--weighting {raw,post-stratified,equal-stratum}`` (default ``raw``) selects which of
    the three is written to the ``natural_mixture`` slot legacy consumers read; a FLOORED roster
    REFUSES ``--weighting raw`` outright (owner, 2026-09-29: the raw roster mean of a floored
    sample is never the natural-mixture number, and may never be labelled as one). Every bootstrap
    resamples WITHIN strata (each stratum to its own size, the same rule ``equal-stratum`` has
    always used) and applies the (fixed, non-resampled) population weights to the resulting
    per-replicate statistic. ``--strata-source {roster-item,gold-bank}`` (default ``roster-item``)
    reads ``--strata-key`` off the roster receipt's own ``items[]`` (TRAIN Fold A: available) or,
    for a dev/test roster whose own items withhold the per-row stratum by design
    (``stratum_withheld_per_item`` -- revealing a row's own gold intent would reveal the correct
    intent-classification answer), off the SAME offline gold bank ``--delivery`` already reads
    (``--gold-bank``/``--gold-bank-roster``); a roster that carries neither is reported NOT
    AVAILABLE, never filled from gold. The file ``per-scenario-tables.json`` is then REPLACED by
    the available table (schema ``saea-stage3-paired-read-per-scenario-v1``).
``--delivery``
    the delivery check and the conversion, counts only: per row and per arm, whether the flown
    Perception consumption records (``<run>.phases.json``, ``consumption.records[].supplied_item_id``)
    carry the row's own gold intent boundary entry ``intent-boundary:<gold intent>`` -- the CONV and
    KPROBE reads' and the AGREE beside read's sealed-side definition -- with the gold intent taken
    OFFLINE from the bad-case bank (``analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl``, the roster's
    own block); the newly-delivered and newly-lost sets (right against left); the intent transition
    table per delivery group; and the conversion: of the newly delivered rows the left arm answered
    wrong, how many the right arm answered right. Written to ``delivery-conversion.json``.
``--frontier``
    the frontier row (decision 75): effect x prefilled tokens per row x GPU hours per 1,080 rows,
    per arm and right-minus-left. GPU hours are the sealed ``flight-receipts.json`` serving-monitor
    active seconds; prompt tokens per row the sealed generation-manifest cost; PREFILLED tokens per
    row (``timings.prompt_n``, i.e. prompt minus cached) from the sealed wire responses in
    ``<run>.trace.jsonl``, reconciled against the sealed cost. Written to ``frontier.json``.

``--stage3`` turns all three on. With NONE of them the output is BYTE-IDENTICAL to the paired roster
read's own (same files, same bytes, same ``driver_sha256``: the stages are the imported module's
functions); ``tests/unit/test_stage3_paired_read.py`` proves this on synthetic fixtures and, where
the data root is present, on the sealed DET and AGREE reads. With an extension on, the README gains
the extension sections and ``verdict.json`` (schema ``saea-stage3-paired-read-verdict-v1``) hashes
the extension files too; its status stays ``DESCRIPTIVE`` -- this driver never decides.

PACKAGE MODE (``--package docs/readiness/<package>``; the wrapper
``scripts/flights/read_paired_cell.sh``): the package's analysis recipe names the arm
(``arms.arm``), its in-chain A/A (``arms.in_chain_replicate``) and the context comparator
(``arms.comparator``). The driver REFUSES before opening any score unless the recipe's READ run id
(``read_run_id`` / ``run_ids.read``, else the basename of ``output.analysis_root``) has a ROOT
COUNTERSIGNED exposure row, then runs two passes with every extension on: ``vs-aa`` (left = the
in-chain A/A, the GATING contrast) and ``vs-comparator`` (left = the comparator, CONTEXT only),
each under ``<data root>/<output.analysis_root>/<pass>/`` (``--output-base`` redirects them). The
roster is the receipt whose ``split_identity_hash`` is the sealed arm manifest's; the scorer is the
TRAIN official sibling on a discovery roster; the seed and draws are the recipe's ``resampling``;
the cluster key is ``sample_id`` when the recipe resamples rows. A pass directory that already
holds files is refused: a sealed read is never overwritten.

MODEL-FREE: zero model, tokenizer, encoder, embedder, scorer, server and network contacts; every
sealed byte is opened read-only; nothing is written outside the analysis root. Gold enters only as
the bank's per-row gold intent (offline, the scoring side), compared in memory and discarded. No
utterance text, gold label string, intent name, value id or delivered answer is printed or
persisted: counts, rates, scenario names, ids and hashes only.
"""

from __future__ import annotations

import argparse
import base64
import dataclasses
import hashlib
import importlib.util
import json
import shutil
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

_DRIVER_PATH = Path(__file__).resolve()
_REPO = _DRIVER_PATH.parents[2]
_SRC = str(_REPO / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

CORE_PATH = _REPO / "scripts" / "analysis" / "slurp_paired_roster_read.py"
GATE_PATH = _REPO / "scripts" / "checks" / "flight_registration_check.py"


def _import_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - broken checkout
        raise SystemExit(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: The paired roster read, imported unmodified: its stages ARE this driver's core stages.
CORE = _import_by_path("_saea_stage3_core_paired_roster_read", CORE_PATH)

from speech_aware_evidence_acquisition.analysis.null_calibration import (  # noqa: E402
    f1_of_totals,
    pooled_f1,
    pooled_totals,
)
from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic  # noqa: E402

SCHEMA_SCENARIO = "saea-stage3-paired-read-per-scenario-v1"
SCHEMA_DELIVERY = "saea-stage3-paired-read-delivery-conversion-v1"
SCHEMA_FRONTIER = "saea-stage3-paired-read-frontier-v1"
SCHEMA_VERDICT = "saea-stage3-paired-read-verdict-v1"
SCHEMA_PACKAGE = "saea-stage3-paired-read-package-run-v1"

INTENT = "scenario_action_exact"
SLU = "slu_f1_micro"
BOUNDARY_PREFIX = "intent-boundary:"
DEFAULT_BANK = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"
#: roster receipt id -> the bad-case bank's own roster key.
BANK_ROSTER_OF = {"SLURP-EVO-FOLD-A-V2": "train-fold-a", "SLURP-DEV-2000-ADDED-V1": "dev2000-added"}
ROWS_PER_FLIGHT = 1080
CONTACTS_ZERO = dict(CORE.CONTACTS_ZERO)
EXTENSION_FILES = {
    "per_scenario": "per-scenario-tables.json",
    "delivery": "delivery-conversion.json",
    "frontier": "frontier.json",
}
_README_SENTINEL = "\x00STAGE3-PER-SCENARIO\x00"


class Stage3ReadError(RuntimeError):
    """A sealed input does not match what it must, or a package cannot be read; nothing is decided."""


def digest(path: Path) -> str:
    return CORE.digest(path)


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def bare(value_id: str) -> str:
    return value_id.split("::", 1)[1] if "::" in value_id else value_id


def pct(num: float, den: float) -> float | None:
    return 100.0 * num / den if den else None


# --------------------------------------------------------------------------
# Extension options
# --------------------------------------------------------------------------


#: ``--weighting`` legal values (owner: post-stratification of a floored roster, 2026-09-29).
WEIGHTING_CHOICES = ("raw", "post-stratified", "equal-stratum")


@dataclasses.dataclass
class Extensions:
    per_scenario: bool = False
    delivery: bool = False
    frontier: bool = False
    gold_bank: str = DEFAULT_BANK
    gold_bank_sha256: str | None = None
    gold_bank_roster: str | None = None
    #: roster item field naming each row's stratum for ``--per-scenario``'s weightings
    #: (generalises the historical hardcoded ``item.get("stratum")`` lookup).
    strata_key: str = "stratum"
    #: ``"roster-item"`` (default, historical behaviour) reads ``strata_key`` off
    #: ``roster.document["items"]`` -- available for a discovery/TRAIN roster, withheld by design
    #: for a dev/test roster (``stratum_withheld_per_item``: revealing a row's own gold intent
    #: would reveal the correct intent-classification answer). ``"gold-bank"`` instead reads
    #: ``strata_key`` off the SAME offline gold bank the ``--delivery`` extension already uses
    #: (``--gold-bank``/``--gold-bank-roster``) -- the one channel this repository sanctions for a
    #: dev/test row's own gold intent to reach a read driver (offline, in memory, never persisted).
    strata_source: str = "roster-item"
    #: path to a receipt-derived ``{stratum: population_count}`` JSON (see
    #: ``build_population_counts.py``); enables the ``post_stratified`` weighting block.
    population_counts: str | None = None
    #: which weighting is written to the ``natural_mixture`` slot for callers that read only that
    #: field; the other two weightings are always reported alongside it (side by side) once
    #: ``--per-scenario`` runs. Default ``"raw"`` keeps the historical, pre-fix, byte-identical
    #: behaviour for a roster that is not floored (or for a caller that passes neither new flag).
    weighting: str = "raw"
    #: ``"auto"`` reads the roster receipt's own ``stratification`` block; ``"true"``/``"false"``
    #: force the answer (a synthetic test roster carries no such block at all).
    roster_floored: str = "auto"

    @property
    def any(self) -> bool:
        return self.per_scenario or self.delivery or self.frontier


def _extension_parser() -> argparse.ArgumentParser:
    # allow_abbrev=False: the paired read's own ``--stage all`` must never be taken for ``--stage3``.
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--stage3", action="store_true", help="all three extension stages")
    parser.add_argument("--per-scenario", action="store_true")
    parser.add_argument("--delivery", action="store_true")
    parser.add_argument("--frontier", action="store_true")
    parser.add_argument("--gold-bank", default=DEFAULT_BANK)
    parser.add_argument("--gold-bank-sha256", default=None)
    parser.add_argument("--gold-bank-roster", default=None)
    parser.add_argument("--package", default=None)
    parser.add_argument("--output-base", default=None)
    parser.add_argument("--ledger", default="docs/exposure-ledger.md")
    parser.add_argument(
        "--strata-key", default="stratum",
        help="field naming each row's stratum for --per-scenario (default: stratum)",
    )
    parser.add_argument(
        "--strata-source", choices=("roster-item", "gold-bank"), default="roster-item",
        help="where --strata-key is read from: the roster's own items (default; a discovery/TRAIN "
             "roster only) or the offline gold bank (--gold-bank/--gold-bank-roster) a dev/test "
             "roster's withheld per-item stratum requires",
    )
    parser.add_argument(
        "--population-counts", default=None,
        help="path to a receipt-derived {stratum: population_count} JSON "
             "(scripts/analysis/build_population_counts.py); enables the post-stratified weighting",
    )
    parser.add_argument(
        "--weighting", choices=WEIGHTING_CHOICES, default="raw",
        help="which weighting the natural_mixture slot carries; all three are always reported "
             "side by side once --population-counts is given (default: raw)",
    )
    parser.add_argument(
        "--roster-floored", choices=("auto", "true", "false"), default="auto",
        help="override the roster-floored auto-detector (the roster receipt's own "
             "stratification block); 'auto' reads the receipt",
    )
    return parser


# --------------------------------------------------------------------------
# Extension 1: per scenario
# --------------------------------------------------------------------------


def _interval(result, point: float, seed: int) -> dict:
    return CORE.interval_block(result.replicates, point, seed)


def _intent_delta(left: Mapping, right: Mapping, ids: Sequence[str]) -> float:
    return sum(right[s][INTENT] - left[s][INTENT] for s in ids) / len(ids)


def _slu_delta(left: Mapping, right: Mapping, ids: Sequence[str]) -> float:
    groups = CORE.MICRO_METRICS[SLU]
    return pooled_f1(right, ids, groups) - pooled_f1(left, ids, groups)


#: ``stratification`` block keys whose positive value proves a roster receipt is FLOORED (at
#: least one stratum's roster share does not equal its population share by construction, e.g.
#: SLURP-TEST-SAMPLE-3010-V1's per-intent floor of 5 prompts).
_FLOOR_COUNT_KEYS = ("floor_driven_utterances", "sample_floor_utterances", "closure_floor_utterances")


def _detect_roster_floored(document: Mapping, override: str) -> bool:
    """Whether the roster is a FLOORED sample -- its raw (unweighted) roster mean is then not a
    population estimate and may never be labelled ``natural_mixture`` (owner, 2026-09-29).

    ``override`` is the ``--roster-floored`` CLI value: ``"true"``/``"false"`` force the answer (a
    synthetic test roster carries no ``stratification`` block at all); ``"auto"`` (the default)
    reads the roster receipt's own ``stratification`` block, exactly the shape
    ``docs/receipts/rosters/slurp-test-sample-3010-v1.json`` records: floor counts, or the
    even-split / single-prompt-to-closure lists the floor rule produces at the low end.
    """

    if override in ("true", "false"):
        return override == "true"
    if override != "auto":
        raise Stage3ReadError(f"--roster-floored must be 'auto', 'true' or 'false', not {override!r}")
    strat = document.get("stratification")
    if not isinstance(strat, Mapping):
        return False
    for key in _FLOOR_COUNT_KEYS:
        value = strat.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            return True
    return bool(strat.get("even_split_intents")) or bool(strat.get("single_prompt_intents_to_closure"))


def _load_population_weights(
    path: str, strata: Sequence[str], *, repo_root: Path | None = None
) -> tuple[dict[str, float], dict]:
    """Population share per stratum, renormalised over the strata this ROSTER actually carries.

    ``path`` names a receipt-derived JSON, either ``{"population_counts": {stratum: count}, ...}``
    (``build_population_counts.py``'s own shape) or a bare ``{stratum: count}`` mapping; a relative
    ``path`` resolves against ``repo_root`` (the same convention ``--roster`` already uses), never
    against the process's current directory. A stratum the roster does not carry
    (SLURP-TEST-SAMPLE-3010-V1 has no ``general_greet`` row -- decision 141's single-prompt intent
    went to the closure roster whole) is dropped and the remaining shares are renormalised to sum
    to 1, exactly as the receipt's own ``equal_stratum`` reading already does (58 of 59 intents,
    not 59). Every stratum the roster DOES carry must have a population count, or the read refuses
    rather than silently weighting it zero.
    """

    counts_path = Path(path)
    if repo_root is not None and not counts_path.is_absolute():
        counts_path = Path(repo_root) / counts_path
    if not counts_path.is_file():
        raise Stage3ReadError(f"--population-counts {path} is not a file")
    document = load_json(counts_path)
    counts = (
        document.get("population_counts")
        if isinstance(document, Mapping) and "population_counts" in document
        else document
    )
    if not isinstance(counts, Mapping) or not counts:
        raise Stage3ReadError(f"--population-counts {path} must carry a non-empty {{stratum: count}} mapping")
    wanted = sorted(set(strata))
    missing = [s for s in wanted if s not in counts]
    if missing:
        raise Stage3ReadError(
            f"--population-counts {path} is missing a population count for stratum/strata "
            f"the roster carries: {missing}"
        )
    values: dict[str, float] = {}
    for stratum in wanted:
        value = counts[stratum]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise Stage3ReadError(f"--population-counts {path}[{stratum!r}] must be a nonnegative number")
        values[stratum] = float(value)
    total = sum(values.values())
    if total <= 0:
        raise Stage3ReadError(f"--population-counts {path} sums to zero over the roster's own strata")
    weights = {stratum: values[stratum] / total for stratum in wanted}
    return weights, {
        "relpath": path,
        "sha256": digest(counts_path),
        "strata": wanted,
        "dropped_strata": sorted(set(counts) - set(wanted)),
    }


def _grouped_by_stratum(resampled: Sequence[str], stratum_of: Callable[[str], str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for sample_id in resampled:
        groups[stratum_of(sample_id)].append(sample_id)
    return groups


def _post_stratified_intent_statistic(
    weights: Mapping[str, float], stratum_of: Callable[[str], str], left: Mapping, right: Mapping,
) -> Callable[[Sequence[str]], float]:
    def statistic(resampled: Sequence[str]) -> float:
        groups = _grouped_by_stratum(resampled, stratum_of)
        return sum(weights[s] * _intent_delta(left, right, members) for s, members in groups.items())

    return statistic


def _post_stratified_intent_level(
    weights: Mapping[str, float], stratum_of: Callable[[str], str], rows: Mapping, ids: Sequence[str],
) -> float:
    groups = _grouped_by_stratum(ids, stratum_of)
    return sum(
        weights[s] * statistics.fmean(rows[sid][INTENT] for sid in members) for s, members in groups.items()
    )


def _post_stratified_slu_statistic(
    weights: Mapping[str, float], stratum_of: Callable[[str], str], left: Mapping, right: Mapping, fields,
) -> Callable[[Sequence[str]], float]:
    """The formula (owner, 2026-09-29): weight each stratum's TP/FP/FN TOTALS before pooling,
    never each stratum's own F1 score.

    For arm A and stratum h with population weight ``w_h`` and ``n_h`` resampled rows, form the
    per-row-normalised, population-weighted contribution ``w_h * TP_h / n_h`` (and the same for
    FP, FN); summing over strata gives one pooled ``(TP*, FP*, FN*)`` triple per arm, from which
    the ordinary micro-F1 formula ``2*TP / (2*TP + FP + FN)`` is taken once. The delta is
    ``F1(right totals) - F1(left totals)``. Dividing by ``n_h`` before applying the population
    weight is what makes a floored stratum's disproportionate row count cancel out of the
    estimate; weighting the raw totals directly would still let an over-sampled stratum's
    absolute count dominate the pooled F1.
    """

    def statistic(resampled: Sequence[str]) -> float:
        groups = _grouped_by_stratum(resampled, stratum_of)
        left_totals = [0.0, 0.0, 0.0]
        right_totals = [0.0, 0.0, 0.0]
        for stratum, members in groups.items():
            weight, n = weights[stratum], len(members)
            l_triple = pooled_totals(left, members, fields)
            r_triple = pooled_totals(right, members, fields)
            for acc, triple in ((left_totals, l_triple), (right_totals, r_triple)):
                acc[0] += weight * triple[0] / n
                acc[1] += weight * triple[1] / n
                acc[2] += weight * triple[2] / n
        return f1_of_totals(tuple(right_totals)) - f1_of_totals(tuple(left_totals))

    return statistic


def _post_stratified_slu_level(
    weights: Mapping[str, float], stratum_of: Callable[[str], str], rows: Mapping, ids: Sequence[str], fields,
) -> float:
    groups = _grouped_by_stratum(ids, stratum_of)
    totals = [0.0, 0.0, 0.0]
    for stratum, members in groups.items():
        weight, n = weights[stratum], len(members)
        triple = pooled_totals(rows, members, fields)
        totals[0] += weight * triple[0] / n
        totals[1] += weight * triple[1] / n
        totals[2] += weight * triple[2] / n
    return f1_of_totals(tuple(totals))


def _post_stratified_block(
    core_args, ext: Extensions, scenarios: Sequence[str], stratum_of: Callable[[str], str],
    cluster_of: Callable[[str], str], left_rows: Mapping, right_rows: Mapping, ids: Sequence[str],
) -> dict:
    if not ext.population_counts:
        return {"status": "NOT_AVAILABLE", "reason": "no --population-counts given"}
    weights, source = _load_population_weights(
        ext.population_counts, scenarios, repo_root=core_args.repo_root
    )
    seed, draws = core_args.seed, core_args.draws
    slu_fields = CORE.MICRO_METRICS[SLU]

    intent_statistic = _post_stratified_intent_statistic(weights, stratum_of, left_rows, right_rows)
    intent_point = intent_statistic(ids)
    intent_boot = resampled_statistic(
        sample_ids=ids, statistic=intent_statistic, seed=seed, n_replicates=draws, ci_level=0.95,
        strata_of=stratum_of, cluster_of=cluster_of,
    )
    slu_statistic = _post_stratified_slu_statistic(weights, stratum_of, left_rows, right_rows, slu_fields)
    slu_point = slu_statistic(ids)
    slu_boot = resampled_statistic(
        sample_ids=ids, statistic=slu_statistic, seed=seed, n_replicates=draws, ci_level=0.95,
        strata_of=stratum_of, cluster_of=cluster_of,
    )
    return {
        "status": "AVAILABLE",
        "definition": (
            "population-weighted, post-stratified: intent = sum_h w_h * mean_h(metric) per arm, then "
            "right - left; pooled SLU-F1 = F1(sum_h w_h * TP_h/n_h, sum_h w_h * FP_h/n_h, "
            "sum_h w_h * FN_h/n_h) per arm, then right - left -- the per-stratum TP/FP/FN totals are "
            "weighted and summed BEFORE the F1 formula is applied, never the per-stratum F1 scores "
            "themselves; w_h is the stratum's population share, renormalised over the strata this "
            "roster carries"
        ),
        "weights_source": source,
        "population_weights": weights,
        "intent": {
            "left_pct": 100 * _post_stratified_intent_level(weights, stratum_of, left_rows, ids),
            "right_pct": 100 * _post_stratified_intent_level(weights, stratum_of, right_rows, ids),
            "delta_pp": 100 * intent_point,
            "ci95_pp": _interval(intent_boot, intent_point, seed)["ci95_pp"],
        },
        "slu_f1": {
            "left_pct": 100 * _post_stratified_slu_level(weights, stratum_of, left_rows, ids, slu_fields),
            "right_pct": 100 * _post_stratified_slu_level(weights, stratum_of, right_rows, ids, slu_fields),
            "delta_pp": 100 * slu_point,
            "ci95_pp": _interval(slu_boot, slu_point, seed)["ci95_pp"],
        },
    }


def stage_per_scenario(core_args, ext: Extensions, left, right, roster, contrast: dict) -> dict:
    strata_key = ext.strata_key
    ids = list(roster.ids)
    if ext.strata_source == "gold-bank":
        roster_id = str(roster.document.get("roster_id") or "")
        bank_roster = ext.gold_bank_roster or BANK_ROSTER_OF.get(roster_id)
        if bank_roster is None:
            return {
                "schema": SCHEMA_SCENARIO,
                "status": "NOT_AVAILABLE",
                "reason": (
                    "--strata-source gold-bank needs a bank roster block; none is known for "
                    f"roster {roster_id!r} (pass --gold-bank-roster)"
                ),
            }
        strata, bank_source = _bank_strata(core_args.data_root, ext, bank_roster, ids, strata_key)
        stratum_source = {"relpath": bank_source["relpath"], "sha256": bank_source["sha256"],
                          "field": f"gold-bank:{bank_roster}.{strata_key}"}
        missing_reason = (
            f"the gold bank's {bank_roster!r} block does not carry a non-empty {strata_key!r} "
            "for every roster row"
        )
    else:
        items = roster.document.get("items") or []
        strata = {str(item.get("sample_id") or item.get("id")): item.get(strata_key) for item in items}
        stratum_source = {"relpath": core_args.roster_relpath, "sha256": roster.sha256,
                          "field": f"items[].{strata_key}"}
        missing_reason = (
            f"the roster receipt does not carry a per-item {strata_key!r} on every row "
            f"(stratum_withheld_per_item={roster.document.get('stratum_withheld_per_item')!r}); "
            "no scenario is inferred from model output and none is read from gold"
        )
    if any(not isinstance(strata.get(s), str) or not strata.get(s) for s in ids):
        return {"schema": SCHEMA_SCENARIO, "status": "NOT_AVAILABLE", "reason": missing_reason}
    left_rows = CORE._rows_table(left, core_args.scorer_id)
    right_rows = CORE._rows_table(right, core_args.scorer_id)
    seed, draws = core_args.seed, core_args.draws

    def cluster_of(sample_id: str) -> str:
        return roster.cluster_of_id[sample_id]

    def scenario_of(sample_id: str) -> str:
        return strata[sample_id]

    by_scenario: dict[str, list[str]] = defaultdict(list)
    for sample_id in ids:
        by_scenario[scenario_of(sample_id)].append(sample_id)
    slu_groups = CORE.MICRO_METRICS[SLU]

    table: dict[str, dict] = {}
    for scenario in sorted(by_scenario):
        members = sorted(by_scenario[scenario])
        l_int = [left_rows[s][INTENT] for s in members]
        r_int = [right_rows[s][INTENT] for s in members]
        intent_point = _intent_delta(left_rows, right_rows, members)
        slu_point = _slu_delta(left_rows, right_rows, members)
        intent_boot = resampled_statistic(
            sample_ids=members, statistic=lambda r: _intent_delta(left_rows, right_rows, r),
            seed=seed, n_replicates=draws, ci_level=0.95, cluster_of=cluster_of,
        )
        slu_boot = resampled_statistic(
            sample_ids=members, statistic=lambda r: _slu_delta(left_rows, right_rows, r),
            seed=seed, n_replicates=draws, ci_level=0.95, cluster_of=cluster_of,
        )
        table[scenario] = {
            "n": len(members),
            "intent": {
                "left_pct": 100 * statistics.fmean(l_int),
                "right_pct": 100 * statistics.fmean(r_int),
                "delta_pp": 100 * intent_point,
                "saves": sum(1 for a, b in zip(l_int, r_int) if b > a),
                "harms": sum(1 for a, b in zip(l_int, r_int) if b < a),
                "ci95_pp": _interval(intent_boot, intent_point, seed)["ci95_pp"],
            },
            "slu_f1": {
                "left_pct": 100 * pooled_f1(left_rows, members, slu_groups),
                "right_pct": 100 * pooled_f1(right_rows, members, slu_groups),
                "delta_pp": 100 * slu_point,
                "ci95_pp": _interval(slu_boot, slu_point, seed)["ci95_pp"],
            },
        }

    def equal_weight(kind: str) -> Callable[[Sequence[str]], float]:
        delta = _intent_delta if kind == "intent" else _slu_delta

        def statistic(resampled: Sequence[str]) -> float:
            groups: dict[str, list[str]] = defaultdict(list)
            for sample_id in resampled:
                groups[scenario_of(sample_id)].append(sample_id)
            return statistics.fmean(delta(left_rows, right_rows, members) for members in groups.values())

        return statistic

    equal: dict[str, dict] = {}
    for kind in ("intent", "slu_f1"):
        statistic = equal_weight(kind)
        point = statistic(ids)
        boot = resampled_statistic(
            sample_ids=ids, statistic=statistic, seed=seed, n_replicates=draws, ci_level=0.95,
            strata_of=scenario_of, cluster_of=cluster_of,
        )
        block = _interval(boot, point, seed)
        block["resampling"] = "paired cluster bootstrap within scenario strata"
        equal[kind] = {"delta_pp": 100 * point, **block}

    natural_intent = contrast["per_row"][INTENT]
    natural_slu = contrast["pooled_micro"][SLU]
    scenarios = sorted(table)
    floored = _detect_roster_floored(roster.document, ext.roster_floored)
    raw = {
        "definition": "pooled over every roster row in its own mixture (no population reweighting)",
        "label": (
            "raw roster mean (not a population estimate)" if floored
            else "raw roster mean (population estimate; the roster is proportional to its population)"
        ),
        "intent": {
            "left_pct": natural_intent["left_pct"], "right_pct": natural_intent["right_pct"],
            "delta_pp": natural_intent["delta_pp"],
            "ci95_pp": natural_intent["cluster_bootstrap"]["ci95_pp"],
        },
        "slu_f1": {
            "left_pct": natural_slu["left_pct"], "right_pct": natural_slu["right_pct"],
            "delta_pp": natural_slu["delta_pp"],
            "ci95_pp": natural_slu["cluster_bootstrap"]["ci95_pp"],
        },
    }
    post_stratified = _post_stratified_block(
        core_args, ext, scenarios, scenario_of, cluster_of, left_rows, right_rows, ids,
    )
    weighting_blocks = {"raw": raw, "post-stratified": post_stratified, "equal-stratum": equal}
    if ext.weighting == "raw" and floored:
        raise Stage3ReadError(
            "the roster is FLOORED (its stratification block declares a floor); the raw roster "
            "mean is not a population estimate and may not be labelled natural_mixture -- pass "
            "--weighting post-stratified (with --population-counts) or --weighting equal-stratum"
        )
    if ext.weighting == "post-stratified" and post_stratified.get("status") != "AVAILABLE":
        raise Stage3ReadError(
            "--weighting post-stratified needs --population-counts (a receipt-derived "
            "{stratum: population_count} JSON; see scripts/analysis/build_population_counts.py)"
        )
    selected = weighting_blocks[ext.weighting]
    natural_mixture = {
        "selected_weighting": ext.weighting,
        "roster_floored": floored,
        "intent": selected["intent"],
        "slu_f1": selected["slu_f1"],
    }
    return {
        "schema": SCHEMA_SCENARIO,
        "status": "AVAILABLE",
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stratum_source": stratum_source,
        "left": left.spec.label,
        "right": right.spec.label,
        "sign_convention": f"delta = right({right.spec.label}) minus left({left.spec.label})",
        "cluster_key": core_args.cluster_key,
        "seed": seed,
        "draws": draws,
        "roster_floored": floored,
        "strata_rows": {s: len(by_scenario[s]) for s in scenarios},
        "per_scenario": table,
        "raw": raw,
        "post_stratified": post_stratified,
        "natural_mixture": natural_mixture,
        "equal_scenario": {
            "definition": "the unweighted mean over scenarios of the per-scenario deltas",
            **equal,
        },
        "scenarios_up_down_flat": {
            kind: [
                sum(1 for s in scenarios if table[s][kind]["delta_pp"] > 0),
                sum(1 for s in scenarios if table[s][kind]["delta_pp"] < 0),
                sum(1 for s in scenarios if table[s][kind]["delta_pp"] == 0),
            ]
            for kind in ("intent", "slu_f1")
        },
        "driver_sha256": digest(_DRIVER_PATH),
    }


# --------------------------------------------------------------------------
# Extension 2: delivery and conversion
# --------------------------------------------------------------------------


def _phase_boundaries(arm) -> tuple[dict[str, dict] | None, dict]:
    """Per row: the set of delivered intent-boundary items and each one's consumption outcome.

    Returns ``(None, source)`` -- never an all-empty boundary map -- when the sealed phase
    artefact is a seal-only replay (``seal_only_replay: true``, E10e 2026-09-29):
    ``core.flight.resume``'s model-free replay cannot reconstruct ``consumption`` custody from
    a predecessor's trace (it is knowledge-provider bookkeeping the live runner never re-emits
    to the trace), so this arm's own boundary set is UNKNOWN, not empty. Treating "unknown" as
    "delivered nothing" would fabricate a false negative delivery signal; the caller must refuse
    or mark itself NOT_AVAILABLE instead of computing over an empty boundary map.
    """

    path = arm.artifact("phases.json")
    if not path.exists():
        raise Stage3ReadError(f"{arm.spec.label}: no sealed phase artefact {path.name}")
    sha = digest(path)
    seal = ((arm.flight_receipts or {}).get("stages") or {}).get("seal") or {}
    pinned = seal.get("phases_sha256")
    if pinned and pinned != sha:
        raise Stage3ReadError(f"{arm.spec.label}: phase artefact does not hash to the seal pin")
    document = load_json(path)
    phases = document.get("phases") or []
    if document.get("schema") != "saea-flight-phase-summaries-v1" or len(phases) != 1:
        raise Stage3ReadError(f"{arm.spec.label}: unexpected phase artefact shape")
    source = {"relpath": f"runs/{arm.spec.run_id}/{arm.spec.attempt_id}/{path.name}", "sha256": sha,
              "seal_pin_checked": bool(pinned)}
    if document.get("seal_only_replay"):
        return None, {**source, "seal_only_replay": True,
                       "omitted_fields": document.get("omitted_fields") or []}
    out: dict[str, dict] = {}
    for result in phases[0].get("results") or ():
        boundary: dict[str, str] = {}
        for record in (result.get("consumption") or {}).get("records") or ():
            item = bare(str(record.get("supplied_item_id") or ""))
            if item.startswith(BOUNDARY_PREFIX):
                boundary[item] = str(record.get("outcome"))
        out[str(result["sample_id"])] = boundary
    return out, source


def _load_bank_rows(
    data_root: Path, ext: Extensions, bank_roster: str, ids: Sequence[str]
) -> tuple[dict[str, dict], dict]:
    """Every bank row (unfiltered fields), for ``bank_roster``'s block, over exactly ``ids``.

    Shared by :func:`_load_bank` (the delivery extension's own ``gold_id``/``bank_class``
    projection) and :func:`_bank_strata` (the per-scenario extension's ``--strata-source
    gold-bank`` path): a dev/test roster's own ``items[]`` withholds its per-row gold intent by
    design (``stratum_withheld_per_item``, e.g. SLURP-TEST-SAMPLE-3010-V1 and
    SLURP-DEV-2000-ADDED-V1), so the ONLY sanctioned per-row gold-intent channel a read driver has
    is this bank -- gold read OFFLINE, compared in memory, never persisted, exactly the delivery
    extension's own existing definition.
    """

    path = data_root / ext.gold_bank
    if not path.is_file():
        raise Stage3ReadError(f"gold bank {ext.gold_bank} not found under the data root")
    sha = digest(path)
    if ext.gold_bank_sha256 and ext.gold_bank_sha256 != sha:
        raise Stage3ReadError("the gold bank does not hash to --gold-bank-sha256")
    wanted = set(ids)
    rows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            entry = json.loads(line)
            sample_id = str(entry.get("sample_id"))
            if entry.get("roster") != bank_roster or sample_id not in wanted:
                continue
            if sample_id in rows:
                raise Stage3ReadError("the gold bank carries a roster row twice")
            rows[sample_id] = entry
    return rows, {"relpath": ext.gold_bank, "sha256": sha, "roster_block": bank_roster}


def _load_bank(data_root: Path, ext: Extensions, bank_roster: str, ids: Sequence[str]) -> tuple[dict, dict]:
    rows, source = _load_bank_rows(data_root, ext, bank_roster, ids)
    projected: dict[str, dict] = {}
    for sample_id, entry in rows.items():
        gold = entry.get("gold_intent")
        projected[sample_id] = {
            "gold_id": f"{BOUNDARY_PREFIX}{gold}" if gold else None,
            "bank_class": str(entry.get("plan_class")),
        }
    if sorted(projected) != sorted(ids) or any(row["gold_id"] is None for row in projected.values()):
        raise Stage3ReadError(
            f"the gold bank's {bank_roster!r} block does not carry a gold intent for every roster row"
        )
    return projected, source


def _bank_strata(
    data_root: Path, ext: Extensions, bank_roster: str, ids: Sequence[str], field: str
) -> tuple[dict[str, str], dict]:
    """``{sample_id: bank_row[field]}`` for every id the bank's ``bank_roster`` block covers with a
    non-empty text value; an id the bank omits, or whose value is empty/non-text, is left out (the
    caller's own completeness check reports it exactly like a roster-item source would)."""

    rows, source = _load_bank_rows(data_root, ext, bank_roster, ids)
    strata: dict[str, str] = {}
    for sample_id in ids:
        entry = rows.get(sample_id)
        value = entry.get(field) if entry else None
        if isinstance(value, str) and value:
            strata[sample_id] = value
    return strata, source


def _transitions(left_rows: Mapping, right_rows: Mapping, members: Sequence[str]) -> dict:
    counts = Counter((int(left_rows[s][INTENT]), int(right_rows[s][INTENT])) for s in members)
    return {"rows": len(members), "wrong_to_right": counts[(0, 1)], "right_to_wrong": counts[(1, 0)],
            "right_to_right": counts[(1, 1)], "wrong_to_wrong": counts[(0, 0)]}


def stage_delivery(core_args, ext: Extensions, left, right, roster) -> dict:
    ids = list(roster.ids)
    roster_id = str(roster.document.get("roster_id") or "")
    bank_roster = ext.gold_bank_roster or BANK_ROSTER_OF.get(roster_id)
    base = {"schema": SCHEMA_DELIVERY, "contacts": dict(CONTACTS_ZERO),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "left": left.spec.label, "right": right.spec.label}
    if bank_roster is None:
        return {**base, "status": "NOT_AVAILABLE",
                "reason": f"no gold-bank roster block is known for roster {roster_id!r}; pass --gold-bank-roster"}
    left_boundary, left_src = _phase_boundaries(left)
    right_boundary, right_src = _phase_boundaries(right)
    if left_boundary is None or right_boundary is None:
        # E10e (2026-09-29): a seal-only arm's phases.json cannot carry
        # consumption custody (see ``_phase_boundaries``). This is UNKNOWN,
        # not "no boundary item was ever supplied" -- NOT_AVAILABLE, not
        # NOT_APPLICABLE, and no delivery/conversion count is computed.
        return {**base, "status": "NOT_AVAILABLE",
                "reason": "a seal-only arm's phases.json is a trace replay and carries no "
                          "consumption custody (core.flight.resume cannot reconstruct it "
                          "from the predecessor trace)",
                "phases": {"left": left_src, "right": right_src}}
    for label, boundary in ((left.spec.label, left_boundary), (right.spec.label, right_boundary)):
        if sorted(boundary) != sorted(ids):
            raise Stage3ReadError(f"{label}: the phase artefact's rows are not the roster")
    if not any(left_boundary[s] or right_boundary[s] for s in ids):
        return {**base, "status": "NOT_APPLICABLE",
                "reason": "neither arm's Perception consumption carries any intent-boundary item",
                "phases": {"left": left_src, "right": right_src}}
    bank, bank_src = _load_bank(core_args.data_root, ext, bank_roster, ids)
    left_rows = CORE._rows_table(left, core_args.scorer_id)
    right_rows = CORE._rows_table(right, core_args.scorer_id)

    delivered_left = {s: bank[s]["gold_id"] in left_boundary[s] for s in ids}
    delivered_right = {s: bank[s]["gold_id"] in right_boundary[s] for s in ids}
    groups = {
        "newly_delivered": [s for s in ids if delivered_right[s] and not delivered_left[s]],
        "newly_lost": [s for s in ids if delivered_left[s] and not delivered_right[s]],
        "delivered_in_both": [s for s in ids if delivered_left[s] and delivered_right[s]],
        "delivered_in_neither": [s for s in ids if not delivered_left[s] and not delivered_right[s]],
    }
    newly = groups["newly_delivered"]
    newly_left_wrong = [s for s in newly if not left_rows[s][INTENT]]
    m = sum(1 for s in newly_left_wrong if right_rows[s][INTENT])
    both_left_wrong = [s for s in groups["delivered_in_both"] if not left_rows[s][INTENT]]
    return {
        **base,
        "status": "AVAILABLE",
        "definition": (
            "delivered = the row's own gold intent boundary value id (intent-boundary:<gold intent>) is "
            "among the intent-boundary items of the flown Perception consumption records "
            "(phases.json); newly delivered = delivered on the right arm and not on the left"
        ),
        "gold_source": {**bank_src, "use": "offline scoring side only; compared in memory, never persisted"},
        "phases": {"left": left_src, "right": right_src},
        "rows": len(ids),
        "delivered_rows": {"left": sum(delivered_left.values()), "right": sum(delivered_right.values())},
        "boundary_items_per_row_histogram": {
            "left": {str(k): v for k, v in sorted(Counter(len(left_boundary[s]) for s in ids).items())},
            "right": {str(k): v for k, v in sorted(Counter(len(right_boundary[s]) for s in ids).items())},
        },
        "newly_delivered_rows": len(newly),
        "newly_lost_rows": len(groups["newly_lost"]),
        "intent_transitions_by_delivery_group": {
            name: _transitions(left_rows, right_rows, members) for name, members in groups.items()
        },
        "conversion": {
            "definition": (
                "of the newly delivered rows the LEFT arm answered with a wrong intent, how many the "
                "RIGHT arm answered with the gold intent (scenario_action_exact)"
            ),
            "newly_delivered_left_wrong": len(newly_left_wrong),
            "converted_m": m,
            "conversion_rate_pct": pct(m, len(newly_left_wrong)),
            "newly_delivered_right_intent_correct": sum(1 for s in newly if right_rows[s][INTENT]),
            "newly_delivered_left_right_to_right_wrong": sum(
                1 for s in newly if left_rows[s][INTENT] and not right_rows[s][INTENT]
            ),
        },
        "already_delivered_but_left_wrong": {
            "rows": len(both_left_wrong),
            "right_intent_correct": sum(1 for s in both_left_wrong if right_rows[s][INTENT]),
        },
        "newly_delivered_by_bank_class": dict(sorted(Counter(bank[s]["bank_class"] for s in newly).items())),
        "gold_entry_consumption_outcome_on_newly_delivered_rows": dict(sorted(
            Counter(right_boundary[s].get(bank[s]["gold_id"]) for s in newly).items()
        )),
        "driver_sha256": digest(_DRIVER_PATH),
    }


# --------------------------------------------------------------------------
# Extension 3: the frontier row
# --------------------------------------------------------------------------


def _wire_tokens(arm) -> dict:
    """Stream ``<run>.trace.jsonl`` once: prompt, prefilled (``timings.prompt_n``) and cached tokens of
    every wire response, hashing the file as it is read."""

    path = arm.artifact("trace.jsonl")
    if not path.exists():
        raise Stage3ReadError(f"{arm.spec.label}: no sealed trace {path.name}")
    sha = hashlib.sha256()
    totals = Counter()
    with path.open("rb") as handle:
        for raw in handle:
            sha.update(raw)
            if b'"MODEL_WIRE_RESPONSE"' not in raw[:64]:
                continue
            record = json.loads(raw)
            if record.get("channel") != "MODEL_WIRE_RESPONSE":
                continue
            wire = json.loads(base64.b64decode(record["payload"]["response_b64"]))
            usage = wire.get("usage") or {}
            timings = wire.get("timings") or {}
            totals["contacts"] += 1
            totals["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
            if timings.get("prompt_n") is not None:
                totals["with_timings"] += 1
                totals["prefilled_tokens"] += int(timings["prompt_n"])
                totals["cached_tokens"] += int(timings.get("cache_n") or 0)
            del wire
    return {"totals": dict(totals), "trace_relpath": f"runs/{arm.spec.run_id}/{arm.spec.attempt_id}/{path.name}",
            "trace_sha256": sha.hexdigest()}


def _arm_frontier(arm, scorer_id: str) -> dict:
    rows = arm.rows or 1
    official = (arm.scores[scorer_id].get("aggregate") or {}).get("official") or {}
    cost = arm.generation_manifest.get("cost") or {}
    seal = ((arm.flight_receipts or {}).get("stages") or {}).get("seal") or {}
    monitor = seal.get("serving_monitor_summary") or {}
    wire = _wire_tokens(arm)
    totals = wire["totals"]
    gpu_hours = monitor["active_seconds"] / 3600.0 if "active_seconds" in monitor else None
    return {
        "rows": arm.rows,
        "official_intent_pct": 100 * official["intent_accuracy"] if "intent_accuracy" in official else None,
        "official_slu_pct": 100 * official["slu_f1"] if "slu_f1" in official else None,
        "contacts_per_row": (cost.get("calls_used") or 0) / rows,
        "prompt_tokens_per_row": (cost.get("prompt_tokens_total") or 0) / rows,
        "prefilled_tokens_per_row": totals.get("prefilled_tokens", 0) / rows,
        "cached_share": (totals.get("cached_tokens", 0) / totals["prompt_tokens"]) if totals.get("prompt_tokens") else None,
        "gpu_hours": gpu_hours,
        "gpu_hours_per_1080": gpu_hours * ROWS_PER_FLIGHT / rows if gpu_hours is not None else None,
        "wire": {
            "contacts": totals.get("contacts", 0),
            "contacts_with_timings": totals.get("with_timings", 0),
            "contacts_equal_sealed_calls": totals.get("contacts", 0) == int(cost.get("calls_used", -1)),
            "prompt_tokens_total_equals_sealed_cost": totals.get("prompt_tokens", 0) == int(cost.get("prompt_tokens_total", -1)),
            "trace_relpath": wire["trace_relpath"],
            "trace_sha256": wire["trace_sha256"],
        },
        "gpu_hours_source": "flight-receipts.json stages.seal.serving_monitor_summary.active_seconds",
    }


def stage_frontier(core_args, left, right, contrast: dict) -> dict:
    left_entry = _arm_frontier(left, core_args.scorer_id)
    right_entry = _arm_frontier(right, core_args.scorer_id)
    intent = contrast["per_row"][INTENT]["delta_pp"]
    slu = contrast["pooled_micro"][SLU]["delta_pp"]

    def diff(key: str):
        lv, rv = left_entry.get(key), right_entry.get(key)
        return rv - lv if isinstance(lv, (int, float)) and isinstance(rv, (int, float)) else None

    delta = {
        "intent_pp": intent,
        "slu_pp": slu,
        "gpu_hours_per_1080": diff("gpu_hours_per_1080"),
        "prefilled_tokens_per_row": diff("prefilled_tokens_per_row"),
        "prompt_tokens_per_row": diff("prompt_tokens_per_row"),
        "contacts_per_row": diff("contacts_per_row"),
        "intent_pp_per_gpu_hour_per_1080": (
            intent / right_entry["gpu_hours_per_1080"] if right_entry.get("gpu_hours_per_1080") else None
        ),
        "intent_pp_per_1000_prefilled_tokens_per_row": (
            1000 * intent / right_entry["prefilled_tokens_per_row"] if right_entry.get("prefilled_tokens_per_row") else None
        ),
    }
    return {
        "schema": SCHEMA_FRONTIER,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "definition": "decision 75: effect x prefilled tokens per row x GPU hours per 1,080 rows",
        "left": {"label": left.spec.label, **left_entry},
        "right": {"label": right.spec.label, **right_entry},
        "delta_right_minus_left": delta,
        "driver_sha256": digest(_DRIVER_PATH),
    }


# --------------------------------------------------------------------------
# Extended verdict
# --------------------------------------------------------------------------


def _f(value, digits: int = 2) -> str:
    return CORE._fmt(value, digits)


def _ci(bounds) -> str:
    return f"[{_f(bounds[0])}, {_f(bounds[1])}]" if bounds else "--"


def _render_per_scenario(block: dict) -> list[str]:
    if block.get("status") != "AVAILABLE":
        return [f"NOT AVAILABLE. {block.get('reason')}"]
    field = block["stratum_source"]["field"]
    lines = [
        f"Stratum: `{block['stratum_source']['relpath']}` (`{field}`); CI95 by the paired "
        f"cluster bootstrap (cluster key `{block['cluster_key']}`, {block['draws']} draws, seed {block['seed']}).",
        "",
        "| scenario | n | intent left | intent right | delta pp | CI95 pp | saves | harms | SLU left | SLU right | delta pp | CI95 pp |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for scenario, row in block["per_scenario"].items():
        i, s = row["intent"], row["slu_f1"]
        lines.append(
            f"| {scenario} | {row['n']} | {_f(i['left_pct'])} | {_f(i['right_pct'])} | {_f(i['delta_pp'])} | "
            f"{_ci(i['ci95_pp'])} | {i['saves']} | {i['harms']} | {_f(s['left_pct'])} | {_f(s['right_pct'])} | "
            f"{_f(s['delta_pp'])} | {_ci(s['ci95_pp'])} |"
        )
    raw, post, eq = block["raw"], block.get("post_stratified") or {}, block["equal_scenario"]
    selected = block["natural_mixture"]["selected_weighting"]
    floored = block["roster_floored"]
    lines += [
        "",
        f"Roster floored (stratification declares a floor): {floored}. Selected weighting for the "
        f"`natural_mixture` slot: **{selected}**. All three weightings, side by side:",
        "",
        "| weighting | intent delta pp | intent CI95 pp | SLU-F1 delta pp | SLU-F1 CI95 pp |",
        "| --- | ---: | --- | ---: | --- |",
        f"| raw -- {raw['label']} | {_f(raw['intent']['delta_pp'])} | {_ci(raw['intent']['ci95_pp'])} | "
        f"{_f(raw['slu_f1']['delta_pp'])} | {_ci(raw['slu_f1']['ci95_pp'])} |",
    ]
    if post.get("status") == "AVAILABLE":
        lines.append(
            f"| post-stratified (population-weighted) | {_f(post['intent']['delta_pp'])} | "
            f"{_ci(post['intent']['ci95_pp'])} | {_f(post['slu_f1']['delta_pp'])} | "
            f"{_ci(post['slu_f1']['ci95_pp'])} |"
        )
    # else: no --population-counts was given for this read; the row is omitted rather than
    # printed as unavailable, so a read that never asked for it renders a complete table.
    lines.append(
        f"| equal-stratum | {_f(eq['intent']['delta_pp'])} | {_ci(eq['intent']['ci95_pp'])} | "
        f"{_f(eq['slu_f1']['delta_pp'])} | {_ci(eq['slu_f1']['ci95_pp'])} |"
    )
    return lines


def _render_delivery(block: dict) -> list[str]:
    if block.get("status") != "AVAILABLE":
        return [f"{block.get('status')}. {block.get('reason')}"]
    c = block["conversion"]
    lines = [
        block["definition"] + ".",
        "",
        "| quantity | count |",
        "| --- | ---: |",
        f"| rows | {block['rows']} |",
        f"| delivered, left | {block['delivered_rows']['left']} |",
        f"| delivered, right | {block['delivered_rows']['right']} |",
        f"| newly delivered (right yes, left no) | {block['newly_delivered_rows']} |",
        f"| newly lost (left yes, right no) | {block['newly_lost_rows']} |",
        f"| newly delivered, left intent wrong | {c['newly_delivered_left_wrong']} |",
        f"| CONVERTED: of those, right intent correct | {c['converted_m']} |",
        f"| newly delivered, right intent correct | {c['newly_delivered_right_intent_correct']} |",
        f"| delivered in both, left wrong / right correct among them | "
        f"{block['already_delivered_but_left_wrong']['rows']} / {block['already_delivered_but_left_wrong']['right_intent_correct']} |",
        "",
        "| delivery group | rows | wrong to right | right to wrong | right to right | wrong to wrong |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, t in block["intent_transitions_by_delivery_group"].items():
        lines.append(f"| {name} | {t['rows']} | {t['wrong_to_right']} | {t['right_to_wrong']} | "
                     f"{t['right_to_right']} | {t['wrong_to_wrong']} |")
    return lines


def _render_frontier(block: dict) -> list[str]:
    left, right, delta = block["left"], block["right"], block["delta_right_minus_left"]
    fields = [("official_intent_pct", 2), ("official_slu_pct", 2), ("contacts_per_row", 4),
              ("prompt_tokens_per_row", 1), ("prefilled_tokens_per_row", 1), ("gpu_hours_per_1080", 4)]
    lines = ["| field | left | right |", "| --- | ---: | ---: |"]
    for name, digits in fields:
        lines.append(f"| {name} | {_f(left.get(name), digits)} | {_f(right.get(name), digits)} |")
    lines += [
        "",
        f"Effect (right minus left): intent {_f(delta['intent_pp'], 4)} pp, SLU-F1 {_f(delta['slu_pp'], 4)} pp; "
        f"prefilled tokens per row {_f(delta['prefilled_tokens_per_row'], 1)}; GPU hours per 1,080 rows "
        f"{_f(delta['gpu_hours_per_1080'], 4)}; intent pp per GPU hour per 1,080 "
        f"{_f(delta['intent_pp_per_gpu_hour_per_1080'], 4)}; intent pp per 1,000 prefilled tokens per row "
        f"{_f(delta['intent_pp_per_1000_prefilled_tokens_per_row'], 4)}.",
    ]
    return lines


def stage_extended_verdict(core_args, blocks: dict[str, dict]) -> dict:
    root = core_args.analysis_root
    stop = CORE._require_artifact(root, "stop.json")
    structural = CORE._require_artifact(root, "structural.json")
    contrast = CORE._require_artifact(root, "score-contrasts.json")
    efficiency = CORE._require_artifact(root, "efficiency.json")
    names = ["stop.json", "structural.json", "score-contrasts.json", "per-scenario-tables.json",
             "efficiency.json", *[EXTENSION_FILES[k] for k in ("delivery", "frontier") if k in blocks]]
    written = {name: digest(root / name) for name in names}
    written["driver.py"] = digest(CORE._DRIVER_PATH)
    written["stage3_driver.py"] = digest(_DRIVER_PATH)

    per_scenario_block = blocks.get("per_scenario")
    readme = CORE._readme(core_args, stop, structural, contrast,
                          {"natural_mixture": {"reason": _README_SENTINEL}}, efficiency, written)
    if per_scenario_block is not None:
        replacement = "\n".join(_render_per_scenario(per_scenario_block))
    else:
        core_doc = load_json(root / "per-scenario-tables.json")
        replacement = f"NOT AVAILABLE. {core_doc['natural_mixture']['reason']}"
    readme = readme.replace(f"NOT AVAILABLE. {_README_SENTINEL}", replacement)
    extra: list[str] = []
    if "delivery" in blocks:
        extra += ["## Delivery and conversion", "", *_render_delivery(blocks["delivery"]), ""]
    if "frontier" in blocks:
        extra += ["## Frontier row", "", *_render_frontier(blocks["frontier"]), ""]
    if extra:
        readme = readme.replace("## Artefact hashes", "\n".join(extra) + "\n## Artefact hashes", 1)
    readme_path = root / "README.md"
    with readme_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(readme)
    written["README.md"] = digest(readme_path)
    verdict = {
        "schema": SCHEMA_VERDICT,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DESCRIPTIVE",
        "not_claimed": list(
            CORE.CONSTRUCTION_NOT_CLAIMED if core_args.expected_split_role == "discovery" else CORE.NOT_CLAIMED
        ),
        "recipe_id": core_args.recipe_id,
        "extensions": sorted(blocks),
        "artifact_sha256": written,
    }
    if core_args.stage3_algorithm is not None:
        verdict["stage3_algorithm"] = dict(core_args.stage3_algorithm)
    CORE.write_json(root / "verdict.json", verdict)
    return verdict


# --------------------------------------------------------------------------
# One pair
# --------------------------------------------------------------------------


def run_pair(core_args, ext: Extensions) -> dict | None:
    """Run the paired read on one pair. Without an extension this is exactly the paired roster
    read's own ``run_stages``."""

    if not ext.any:
        CORE.run_stages(core_args)
        return None
    if core_args.stage != "all":
        raise Stage3ReadError("an extension stage needs --stage all")
    # A column arm (owner decision 172) locates its derived score by the scorer id, and a column
    # pair must pass the same-parent refusal -- exactly as the core's own run_stages does.
    left = CORE.load_arm(core_args.data_root, core_args.left, scorer_id=core_args.scorer_id)
    right = CORE.load_arm(core_args.data_root, core_args.right, scorer_id=core_args.scorer_id)
    CORE._assert_column_pair_invariants(left, right, core_args)
    roster = CORE.load_roster(core_args.repo_root, core_args.roster_relpath, core_args.cluster_key)
    CORE.stage_stop(core_args, left, right, roster)
    CORE.stage_structural(core_args, left, right)
    contrast, _ = CORE.stage_contrast(core_args, left, right, roster)
    CORE.stage_efficiency(core_args, left, right)
    blocks: dict[str, dict] = {}
    root = core_args.analysis_root
    if ext.per_scenario:
        block = stage_per_scenario(core_args, ext, left, right, roster, contrast)
        if block["status"] == "AVAILABLE":
            CORE.write_json(root / EXTENSION_FILES["per_scenario"], block)
            blocks["per_scenario"] = block
    if ext.delivery:
        blocks["delivery"] = stage_delivery(core_args, ext, left, right, roster)
        CORE.write_json(root / EXTENSION_FILES["delivery"], blocks["delivery"])
    if ext.frontier:
        blocks["frontier"] = stage_frontier(core_args, left, right, contrast)
        CORE.write_json(root / EXTENSION_FILES["frontier"], blocks["frontier"])
    return stage_extended_verdict(core_args, blocks)


# --------------------------------------------------------------------------
# Package mode
# --------------------------------------------------------------------------


def _gate():
    return _import_by_path("_saea_stage3_flight_registration_check", GATE_PATH)


def _recipe(package: Path, arm_run_id: str | None = None) -> tuple[Path, dict]:
    recipes = sorted(package.glob("*analysis-recipe*.json"))
    if len(recipes) > 1 and arm_run_id:
        recipes = [p for p in recipes if arm_run_id in p.read_text(encoding="utf-8")]
    if len(recipes) != 1:
        raise Stage3ReadError(f"{package} carries {len(recipes)} usable analysis recipes; expected exactly one")
    return recipes[0], load_json(recipes[0])


def read_run_id_of(recipe: dict) -> tuple[str | None, str]:
    gate = _gate()
    declared = gate.read_run_id_of(recipe)
    if declared:
        return declared, "declared by the recipe"
    root = str((recipe.get("output") or {}).get("analysis_root") or "")
    if root.startswith("analysis/") and root.count("/") == 1:
        return root.split("/", 1)[1], "the basename of output.analysis_root (the recipe declares no read_run_id)"
    return None, "the recipe declares no READ run id and no analysis root"


def _roster_for(repo_root: Path, manifest: dict) -> str:
    split = manifest.get("split") or {}
    wanted = split.get("identity_hash")
    matches = []
    for path in sorted((repo_root / "docs" / "receipts" / "rosters").glob("*.json")):
        try:
            document = load_json(path)
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(document, dict) and document.get("split_identity_hash") == wanted and document.get("items"):
            matches.append((path, document))
    if len(matches) > 1:
        matches = [m for m in matches if m[1].get("roster_id") == split.get("name")] or matches
    if len(matches) != 1:
        raise Stage3ReadError(
            f"{len(matches)} roster receipts carry the sealed split identity {str(wanted)[:12]}...; expected one"
        )
    return matches[0][0].relative_to(repo_root).as_posix()


def run_package(argv_rest: list[str], ext_ns: argparse.Namespace) -> dict:
    """``--package``: resolve the arms from the analysis recipe, refuse unless the READ row is
    countersigned, and run the gating pass (vs the in-chain A/A) and the context pass."""

    parser = argparse.ArgumentParser(prog="stage3_paired_read.py --package")
    parser.add_argument("--repo-root", default=str(_REPO))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--passes", default="vs-aa,vs-comparator")
    ns = parser.parse_args(argv_rest)
    repo_root = Path(ns.repo_root).resolve()
    data_root = Path(ns.data_root)
    package = Path(ext_ns.package)
    package = package if package.is_absolute() else repo_root / package
    if not package.is_dir():
        raise Stage3ReadError(f"package {package} is not a directory")
    recipe_path, recipe = _recipe(package)
    arms = recipe.get("arms") or {}
    arm = arms.get("arm") or {}
    replicate = arms.get("in_chain_replicate") or {}
    comparator = arms.get("comparator") or {}
    if not arm.get("run_id") or not replicate.get("run_id"):
        raise Stage3ReadError(
            f"{recipe_path.name} names no arms.arm and arms.in_chain_replicate: this read needs a sealed "
            "arm and its in-chain A/A"
        )

    # The refusal comes FIRST: no score is opened before the READ row is countersigned.
    gate = _gate()
    read_run_id, how = read_run_id_of(recipe)
    if read_run_id is None:
        raise Stage3ReadError(f"{recipe_path.name}: {how}")
    ledger = gate.parse_ledger(repo_root, Path(ext_ns.ledger))
    rows = ledger.get(read_run_id, [])
    if not rows:
        raise Stage3ReadError(f"REFUSED: the READ row {read_run_id} ({how}) is not in the exposure ledger")
    if not any(gate.is_countersigned(row) for row in rows):
        raise Stage3ReadError(f"REFUSED: the READ row {read_run_id} is not root countersigned")

    arm_manifest = load_json(data_root / "runs" / arm["run_id"] / arm["attempt_id"] / f"{arm['run_id']}.run-manifest.json")
    roster_relpath = _roster_for(repo_root, arm_manifest)
    roster_doc = load_json(repo_root / roster_relpath)
    discovery = roster_doc.get("split_role") == "discovery"
    resampling = recipe.get("resampling") or {}
    unit = str(resampling.get("unit") or "")
    cluster_key = "sample_id" if "row" in unit else "utterance_id"
    # owner decision 172 section 3: any arm entry naming a "column" is a same-flight
    # supply-variant read, and such a recipe resamples by row (Q4 ruling) -- refused here,
    # before any score is opened, rather than left to the driver's own later check.
    if any(entry.get("column") for entry in (arm, replicate, comparator)) and cluster_key != "sample_id":
        raise Stage3ReadError(
            f"{recipe_path.name}: a column recipe (owner decision 172) resamples by row; "
            f"resampling.unit is {unit!r}, not 'row'"
        )
    analysis_root = str((recipe.get("output") or {}).get("analysis_root") or f"analysis/{read_run_id}")
    base = Path(ext_ns.output_base) if ext_ns.output_base else data_root / analysis_root
    title = str(recipe.get("title") or recipe.get("recipe_id") or read_run_id)

    passes = {
        "vs-aa": (replicate, "the in-chain A/A (gating)"),
        "vs-comparator": (comparator, "the context comparator (context only)"),
    }
    wanted = [p for p in ns.passes.split(",") if p]
    record = {"schema": SCHEMA_PACKAGE, "package": package.relative_to(repo_root).as_posix()
              if package.is_relative_to(repo_root) else str(package),
              "recipe": recipe_path.name, "recipe_sha256": digest(recipe_path),
              "read_run_id": read_run_id, "read_run_id_source": how, "roster": roster_relpath,
              "cluster_key": cluster_key, "passes": {}}
    ext = Extensions(per_scenario=True, delivery=True, frontier=True, gold_bank=ext_ns.gold_bank,
                     gold_bank_sha256=ext_ns.gold_bank_sha256, gold_bank_roster=ext_ns.gold_bank_roster,
                     strata_key=ext_ns.strata_key, strata_source=ext_ns.strata_source,
                     population_counts=ext_ns.population_counts,
                     weighting=ext_ns.weighting, roster_floored=ext_ns.roster_floored)
    for name in wanted:
        if name not in passes:
            raise Stage3ReadError(f"unknown pass {name!r}")
        left, label = passes[name]
        if not left.get("run_id"):
            record["passes"][name] = {"status": "SKIPPED", "reason": "the recipe names no such arm"}
            continue
        out = base / name
        if out.exists() and any(out.iterdir()):
            raise Stage3ReadError(f"{out} already holds files; a sealed read is never overwritten")
        out.mkdir(parents=True, exist_ok=True)
        for source in (CORE_PATH, _DRIVER_PATH):  # a record of the driver bytes beside the output
            shutil.copyfile(source, out / source.name)
        argv = [
            "--stage", "all",
            "--left-run", left["run_id"], "--left-attempt", left["attempt_id"], "--left-label", label,
            "--right-run", arm["run_id"], "--right-attempt", arm["attempt_id"],
            "--right-label", f"the arm ({arm['run_id']})",
            "--scorer-id", "slurp-slu-official-train" if discovery else "slurp-slu-official",
            "--expected-split-role", "discovery" if discovery else "dev",
            "--roster", roster_relpath, "--cluster-key", cluster_key,
            "--split-identity-hash", str(roster_doc.get("split_identity_hash")),
            "--repo-root", str(repo_root), "--data-root", str(data_root),
            "--seed", str(int(resampling.get("seed", CORE.DEFAULT_SEED))),
            "--draws", str(int(resampling.get("bootstrap_draws", CORE.DEFAULT_DRAWS))),
            "--title", f"{title} ({name})", "--analysis-root", str(out),
        ]
        if left.get("column"):
            argv += ["--left-column", str(left["column"])]
        if arm.get("column"):
            argv += ["--right-column", str(arm["column"])]
        if recipe.get("recipe_id"):
            argv += ["--recipe-id", str(recipe["recipe_id"])]
        verdict = run_pair(CORE.parse_args(argv), ext)
        record["passes"][name] = {"status": "WRITTEN", "left": left["run_id"], "right": arm["run_id"],
                                  "analysis_root": str(out), "verdict_sha256": digest(out / "verdict.json"),
                                  "extensions": (verdict or {}).get("extensions")}
    return record


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ext_ns, rest = _extension_parser().parse_known_args(argv)
    try:
        if ext_ns.package:
            record = run_package(rest, ext_ns)
            print(json.dumps(record, indent=2, sort_keys=True))
            return 0
        core_args = CORE.parse_args(rest)
        ext = Extensions(
            per_scenario=ext_ns.stage3 or ext_ns.per_scenario,
            delivery=ext_ns.stage3 or ext_ns.delivery,
            frontier=ext_ns.stage3 or ext_ns.frontier,
            gold_bank=ext_ns.gold_bank,
            gold_bank_sha256=ext_ns.gold_bank_sha256,
            gold_bank_roster=ext_ns.gold_bank_roster,
            strata_key=ext_ns.strata_key,
            strata_source=ext_ns.strata_source,
            population_counts=ext_ns.population_counts,
            weighting=ext_ns.weighting,
            roster_floored=ext_ns.roster_floored,
        )
        run_pair(core_args, ext)
    except (CORE.StopStageError, CORE.ReadDriverError, Stage3ReadError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
