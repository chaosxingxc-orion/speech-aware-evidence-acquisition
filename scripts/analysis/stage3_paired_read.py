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
    AVAILABLE, never filled from gold. ``--strata-source scorer`` (coordinator ruling
    2026-09-30) is the channel for a roster whose gold may be read ONLY by the official scorer
    after delivery (the signed test sample: "per-intent aggregate counts only; no label beside a
    sample id"): this process never sees a per-row stratum. It runs the official-scoring step's
    ``--strata-inside-scorer`` mode (``core.scoring_strata``) in a separate process, which reads
    gold, stratifies by gold intent, runs the same within-stratum bootstraps through the same
    shared estimators (``analysis.stratified_paired``) and writes ONE aggregate receipt
    (``scorer-strata-aggregate.json``: per-stratum n and per-arm intent-correct / TP / FP / FN
    totals, the weighted deltas, CI95s, a receipt hash); this driver verifies the receipt against
    the arms, roster and population counts it read, checks the scorer's raw numbers equal its own
    contrast bit for bit, and reports the three weightings exactly as the gold-bank path would.
    The file ``per-scenario-tables.json`` is then REPLACED by the available table (schema
    ``saea-stage3-paired-read-per-scenario-v1``).
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

from speech_aware_evidence_acquisition.analysis import stratified_paired as SP  # noqa: E402

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
#: ``--strata-source`` legal values; ``scorer`` added by the coordinator ruling of 2026-09-30.
STRATA_SOURCES = ("roster-item", "gold-bank", "scorer")


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
    #: ``--strata-source scorer`` only: the umbrella lock the scorer step loads gold through
    #: (``None``: the umbrella default, exactly what ``core.driver score`` uses).
    scorer_lock_path: str | None = None

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
        "--strata-source", choices=STRATA_SOURCES, default="roster-item",
        help="where the per-row stratum comes from: the roster's own items (default; a "
             "discovery/TRAIN roster only), the offline gold bank (--gold-bank/--gold-bank-roster; "
             "a roster whose rows may legally be joined to gold), or 'scorer': the official-"
             "scoring step's --strata-inside-scorer mode stratifies by gold intent INSIDE the "
             "scorer process and returns aggregates only (a roster whose gold may be read only "
             "by the official scorer, e.g. the signed test sample; needs --population-counts)",
    )
    parser.add_argument(
        "--scorer-lock-path", default=None,
        help="--strata-source scorer: the umbrella lock the scorer step loads gold through "
             "(default: the umbrella lock core.driver score uses)",
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


# The estimators live in ONE shared module (``analysis.stratified_paired``) so the official-scoring
# step's ``--strata-inside-scorer`` mode (``core.scoring_strata``) computes the SAME numbers from
# the SAME code; the names below keep this driver's historical private API.
_intent_delta = SP.intent_delta
_slu_delta = SP.slu_delta
_grouped_by_stratum = SP.grouped_by_stratum
_post_stratified_intent_statistic = SP.post_stratified_intent_statistic
_post_stratified_intent_level = SP.post_stratified_intent_level
_post_stratified_slu_statistic = SP.post_stratified_slu_statistic
_post_stratified_slu_level = SP.post_stratified_slu_level


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


def _population_counts_path(path: str, repo_root: Path | None) -> Path:
    counts_path = Path(path)
    if repo_root is not None and not counts_path.is_absolute():
        counts_path = Path(repo_root) / counts_path
    if not counts_path.is_file():
        raise Stage3ReadError(f"--population-counts {path} is not a file")
    return counts_path


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

    counts_path = _population_counts_path(path, repo_root)
    document = load_json(counts_path)
    try:
        weights = SP.population_weights(document, strata, label=f"--population-counts {path}")
    except SP.StratifiedPairedError as error:
        raise Stage3ReadError(str(error)) from error
    return weights, {
        "relpath": path,
        "sha256": digest(counts_path),
        "strata": sorted(set(strata)),
        "dropped_strata": SP.dropped_strata(document, strata),
    }


def _post_stratified_block(
    core_args, ext: Extensions, scenarios: Sequence[str], stratum_of: Callable[[str], str],
    cluster_of: Callable[[str], str], left_rows: Mapping, right_rows: Mapping, ids: Sequence[str],
) -> dict:
    if not ext.population_counts:
        return {"status": "NOT_AVAILABLE", "reason": "no --population-counts given"}
    weights, source = _load_population_weights(
        ext.population_counts, scenarios, repo_root=core_args.repo_root
    )
    estimates = SP.post_stratified_estimates(
        left_rows, right_rows, ids, weights=weights, stratum_of=stratum_of, cluster_of=cluster_of,
        seed=core_args.seed, draws=core_args.draws,
    )
    return {
        "status": "AVAILABLE",
        "definition": SP.POST_STRATIFIED_DEFINITION,
        "weights_source": source,
        "population_weights": weights,
        **estimates,
    }


def _raw_block(contrast: dict, floored: bool) -> dict:
    natural_intent = contrast["per_row"][INTENT]
    natural_slu = contrast["pooled_micro"][SLU]
    return {
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


def _assemble_per_scenario(
    core_args, ext: Extensions, left, right, roster, contrast: dict, *, stratum_source: dict,
    table: dict, equal: dict, post_stratified: dict, strata_rows: dict, extra: dict | None = None,
) -> dict:
    """The per-scenario document, identical in shape whichever channel produced the strata."""

    scenarios = sorted(table)
    floored = _detect_roster_floored(roster.document, ext.roster_floored)
    raw = _raw_block(contrast, floored)
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
    document = {
        "schema": SCHEMA_SCENARIO,
        "status": "AVAILABLE",
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stratum_source": stratum_source,
        "left": left.spec.label,
        "right": right.spec.label,
        "sign_convention": f"delta = right({right.spec.label}) minus left({left.spec.label})",
        "cluster_key": core_args.cluster_key,
        "seed": core_args.seed,
        "draws": core_args.draws,
        "roster_floored": floored,
        "strata_rows": strata_rows,
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
    if extra:
        document.update(extra)
    return document


# --------------------------------------------------------------------------
# --strata-source scorer: aggregate-only post-stratification inside the official-scoring step
# --------------------------------------------------------------------------


#: The aggregate receipt the scorer step writes into the analysis root (and nothing else).
SCORER_STRATA_FILE = "scorer-strata-aggregate.json"
SCORER_STRATA_MODULE = "speech_aware_evidence_acquisition.core.scoring_strata"
SCORER_STRATA_SCHEMA = "saea-scorer-strata-aggregate-v1"


def run_scorer_strata(argv: Sequence[str]) -> None:
    """Run ``core.scoring_strata --strata-inside-scorer`` in its OWN process.

    Gold is opened only there -- inside the official-scoring step, after delivery (allowance:
    gold "ONLY by the official scorer, after delivery") -- never in this read process, which
    receives per-stratum AGGREGATES only. Tests substitute an in-process runner.
    """

    import os
    import subprocess

    env = dict(os.environ)
    env["PYTHONPATH"] = _SRC + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", "-m", SCORER_STRATA_MODULE, *argv],
        env=env, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        tail = (result.stderr or "").strip().splitlines()[-5:]
        raise Stage3ReadError("the scorer's --strata-inside-scorer step refused: " + " | ".join(tail))


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _scorer_per_scenario(core_args, ext: Extensions, left, right, roster, contrast: dict) -> dict:
    if not ext.population_counts:
        raise Stage3ReadError(
            "--strata-source scorer needs --population-counts: the scorer step reports the "
            "raw, post-stratified and equal-stratum weightings together"
        )
    counts_path = _population_counts_path(ext.population_counts, core_args.repo_root)
    out = core_args.analysis_root / SCORER_STRATA_FILE
    if out.exists():
        raise Stage3ReadError(f"{out} already exists; a scorer aggregate receipt is never overwritten")
    argv = [
        "--strata-inside-scorer",
        "--scorer-id", core_args.scorer_id,
        "--left-scores", str(left.scores_path),
        "--right-scores", str(right.scores_path),
        "--roster", str(roster.path),
        "--population-counts", str(counts_path),
        "--population-counts-label", ext.population_counts,
        "--cluster-key", core_args.cluster_key,
        "--seed", str(core_args.seed),
        "--draws", str(core_args.draws),
        "--output", str(out),
        "--data-root", str(core_args.data_root),
    ]
    if ext.scorer_lock_path:
        argv += ["--lock-path", ext.scorer_lock_path]
    run_scorer_strata(argv)
    if not out.is_file():
        raise Stage3ReadError("the scorer step wrote no aggregate receipt")
    receipt = load_json(out)
    problems = []
    if receipt.get("schema") != SCORER_STRATA_SCHEMA:
        problems.append("schema")
    if receipt.get("receipt_sha256") != SP.canonical_digest(receipt, exclude=("receipt_sha256",)):
        problems.append("receipt_sha256")
    inputs = receipt.get("inputs") or {}
    expected = {
        "scorer_id": core_args.scorer_id, "seed": core_args.seed, "draws": core_args.draws,
        "cluster_key": core_args.cluster_key,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            problems.append(key)
    if (inputs.get("left_scores") or {}).get("sha256") != left.scores_sha256:
        problems.append("left scores sha256")
    if (inputs.get("right_scores") or {}).get("sha256") != right.scores_sha256:
        problems.append("right scores sha256")
    if (inputs.get("roster") or {}).get("sha256") != roster.sha256:
        problems.append("roster sha256")
    if (inputs.get("population_counts") or {}).get("sha256") != digest(counts_path):
        problems.append("population counts sha256")
    weightings = receipt.get("weightings") or {}
    per_stratum = receipt.get("per_stratum") or {}
    if sum(int(row.get("n", 0)) for row in per_stratum.values()) != len(roster.ids):
        problems.append("per-stratum n does not sum to the roster")
    # The raw weighting needs no stratum: this process computed it itself (the core contrast). The
    # scorer's own raw numbers must be the SAME floats -- proof both sides paired the same rows
    # under the same draws.
    floored = _detect_roster_floored(roster.document, ext.roster_floored)
    raw = _raw_block(contrast, floored)
    for kind in ("intent", "slu_f1"):
        if not _same((weightings.get("raw") or {}).get(kind), raw[kind]):
            problems.append(f"raw {kind} differs from the read's own contrast")
    if problems:
        raise Stage3ReadError(f"the scorer aggregate receipt does not match this read: {problems}")
    table = {
        stratum: {"n": row["n"], "intent": row["intent"], "slu_f1": row["slu_f1"]}
        for stratum, row in sorted(per_stratum.items())
    }
    post = weightings["post_stratified"]
    post_stratified = {
        "status": "AVAILABLE",
        "definition": post["definition"],
        "weights_source": {
            "relpath": ext.population_counts,
            "sha256": digest(counts_path),
            "strata": sorted(table),
            "dropped_strata": list(post.get("dropped_strata") or []),
        },
        "population_weights": post["population_weights"],
        "intent": post["intent"],
        "slu_f1": post["slu_f1"],
    }
    equal = {kind: weightings["equal_stratum"][kind] for kind in ("intent", "slu_f1")}
    return _assemble_per_scenario(
        core_args, ext, left, right, roster, contrast,
        stratum_source={
            "relpath": SCORER_STRATA_FILE,
            "sha256": digest(out),
            "field": "scorer:gold intent scenario_action (aggregate-only, --strata-inside-scorer)",
        },
        table=table, equal=equal, post_stratified=post_stratified,
        strata_rows={s: table[s]["n"] for s in sorted(table)},
        extra={"scorer_strata_receipt": {"relpath": SCORER_STRATA_FILE, "sha256": digest(out),
                                         "receipt_sha256": receipt["receipt_sha256"]}},
    )


def stage_per_scenario(core_args, ext: Extensions, left, right, roster, contrast: dict) -> dict:
    if ext.strata_source == "scorer":
        return _scorer_per_scenario(core_args, ext, left, right, roster, contrast)
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

    table = SP.per_stratum_table(left_rows, right_rows, ids, stratum_of=scenario_of,
                                 cluster_of=cluster_of, seed=seed, draws=draws)
    equal = SP.equal_stratum_block(left_rows, right_rows, ids, stratum_of=scenario_of,
                                   cluster_of=cluster_of, seed=seed, draws=draws)
    post_stratified = _post_stratified_block(
        core_args, ext, sorted(table), scenario_of, cluster_of, left_rows, right_rows, ids,
    )
    return _assemble_per_scenario(
        core_args, ext, left, right, roster, contrast, stratum_source=stratum_source,
        table=table, equal=equal, post_stratified=post_stratified,
        strata_rows={s: table[s]["n"] for s in sorted(table)},
    )


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


def _answered_rows(arm, ids: Sequence[str]) -> tuple[int, list[str]]:
    """Every roster row's own ``admitted`` / ``response_text_sha256`` from the arm's OWN sealed
    ``<run>.outputs.jsonl`` -- gold-free by construction: this file is the arm's answer
    bookkeeping, never a gold field. Returns ``(answered_count, missing_ids)``."""

    path = arm.artifact("outputs.jsonl")
    if not path.exists():
        raise Stage3ReadError(f"{arm.spec.label}: no sealed outputs {path.name}")
    rows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            entry = json.loads(line)
            rows[str(entry.get("sample_id"))] = entry
    missing: list[str] = []
    answered = 0
    for sample_id in ids:
        entry = rows.get(sample_id)
        answer_hash = (entry or {}).get("response_text_sha256")
        has_answer_hash = isinstance(answer_hash, str) and len(answer_hash) == 64
        if entry is not None and entry.get("admitted") and has_answer_hash:
            answered += 1
        else:
            missing.append(sample_id)
    return answered, missing


def _prepared_boundary_check(data_root: Path, arm, boundary: dict, ids: Sequence[str]) -> dict:
    """Compare flown boundary identities with this arm's own pinned preparation, without gold."""
    preflight = ((arm.flight_receipts or {}).get("stages") or {}).get("preflight") or {}
    pins = [p for p in preflight.get("prepared_artifacts", [])
            if isinstance(p, dict) and p.get("key") == "prepared_phase_supply"]
    if len(pins) != 1:
        raise Stage3ReadError(f"{arm.spec.label}: prepared supply requires exactly one preflight pin")
    pin = pins[0]
    root = Path(data_root).resolve()
    relpath = pin.get("relpath")
    if not isinstance(relpath, str) or not relpath or Path(relpath).is_absolute():
        raise Stage3ReadError(f"{arm.spec.label}: prepared supply path must be relative")
    path = (root / relpath).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise Stage3ReadError(f"{arm.spec.label}: prepared supply is missing or outside the data root")
    sha = digest(path)
    if sha != pin.get("sha256"):
        raise Stage3ReadError(f"{arm.spec.label}: prepared supply does not hash to its preflight pin")
    try:
        phases = load_json(path)["output"]["values"]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise Stage3ReadError(f"{arm.spec.label}: prepared supply has no perception value map") from error
    if not isinstance(phases, dict) or set(phases) - {"perception"}:
        raise Stage3ReadError(f"{arm.spec.label}: prepared supply has invalid phases")
    values = phases.get("perception", {})
    if not isinstance(values, dict) or set(values) - set(ids):
        raise Stage3ReadError(f"{arm.spec.label}: prepared supply rows are outside the roster")
    equal = 0
    for sample_id in ids:
        # Runtime _load_phase_supply_seed accepts sparse maps. The runner's
        # per-sample bootstrap defaults an absent row to no values; it does
        # not infer unknown content or refill it from another preparation.
        row = values.get(sample_id, [])
        if (not isinstance(row, list) or any(not isinstance(v, str) for v in row)
                or len(row) != len(set(row))):
            raise Stage3ReadError(f"{arm.spec.label}: prepared supply has an invalid value list")
        expected = {bare(v) for v in row if bare(v).startswith(BOUNDARY_PREFIX)}
        equal += expected == set(boundary[sample_id])
    if digest(path) != sha:
        raise Stage3ReadError(f"{arm.spec.label}: prepared supply changed during the read")
    return {"prepared_relpath": relpath, "prepared_sha256": sha,
            "rows": len(ids), "rows_flown_set_equals_prepared_set": equal,
              "omitted_rows_with_empty_default": len(set(ids) - set(values)),
            "mismatched_rows": len(ids) - equal}


def _stage_delivery_final_report(base: dict, left, right, ids: Sequence[str], data_root: Path) -> dict:
    """The recipe's step 2 delivery check, GOLD-FREE: each cell's flown first-phase boundary
    selections and delivered answers, checked against its OWN sealed artefacts only (its own
    outputs, phases and wire trace against its own sealed generation-manifest cost) -- never
    against gold, and never against the other arm's gold. A ``final-report`` roster (the signed
    test sample) allows gold to be read ONLY by the official scorer, after delivery (the owner
    allowance) and never through a per-row gold bank (coordinator ruling 2026-09-30), so this
    REPLACES the gold-bank delivery/conversion extension outright for such a roster, rather than
    reporting it NOT AVAILABLE for want of a ``--gold-bank-roster`` mapping that could never be a
    legal one here.
    """

    left_boundary, left_src = _phase_boundaries(left)
    right_boundary, right_src = _phase_boundaries(right)
    if left_boundary is None or right_boundary is None:
        # Same E10e situation stage_delivery's own gold-bank path guards against: see its
        # docstring note beside _phase_boundaries.
        return {**base, "status": "NOT_AVAILABLE",
                "reason": "a seal-only arm's phases.json is a trace replay and carries no "
                          "consumption custody (core.flight.resume cannot reconstruct it "
                          "from the predecessor trace)",
                "phases": {"left": left_src, "right": right_src}}
    for label, boundary in ((left.spec.label, left_boundary), (right.spec.label, right_boundary)):
        if sorted(boundary) != sorted(ids):
            raise Stage3ReadError(f"{label}: the phase artefact's rows are not the roster")

    def _arm_block(arm, boundary: dict[str, dict]) -> dict:
        answered, missing_answer_ids = _answered_rows(arm, ids)
        selected = sum(1 for s in ids if any(v == "use" for v in boundary[s].values()))
        wire = _wire_tokens(arm)
        totals = wire["totals"]
        cost = arm.generation_manifest.get("cost") or {}
        return {
            "rows": len(ids),
            "prepared_supply": _prepared_boundary_check(data_root, arm, boundary, ids),
            "answered_rows": answered,
            "missing_answer_ids": missing_answer_ids,
            "boundary_selected_rows": selected,
            "boundary_items_per_row_histogram": {
                str(k): v for k, v in sorted(Counter(len(boundary[s]) for s in ids).items())
            },
            "contacts": {
                "sealed_calls_used": int(cost.get("calls_used") or 0),
                "wire_contacts": totals.get("contacts", 0),
                "contacts_equal_sealed_calls": totals.get("contacts", 0) == int(cost.get("calls_used", -1)),
                "prompt_tokens_total_equals_sealed_cost": (
                    totals.get("prompt_tokens", 0) == int(cost.get("prompt_tokens_total", -1))
                ),
            },
            "answers_source": {
                "relpath": f"runs/{arm.spec.run_id}/{arm.spec.attempt_id}/{arm.spec.run_id}.outputs.jsonl",
            },
        }

    left_block = _arm_block(left, left_boundary)
    right_block = _arm_block(right, right_boundary)
    problems: list[str] = []
    for label, block in ((left.spec.label, left_block), (right.spec.label, right_block)):
        if block["prepared_supply"]["mismatched_rows"]:
            problems.append(f"{label}: {block['prepared_supply']['mismatched_rows']} row(s) "
                            "differ from the arm's own prepared supply")
        if block["missing_answer_ids"]:
            problems.append(f"{label}: {len(block['missing_answer_ids'])} row(s) delivered no answer")
        if not block["contacts"]["contacts_equal_sealed_calls"]:
            problems.append(f"{label}: wire contacts do not equal the sealed generation-manifest cost")
        if not block["contacts"]["prompt_tokens_total_equals_sealed_cost"]:
            problems.append(f"{label}: wire prompt tokens do not equal the sealed generation-manifest cost")
    return {
        **base,
        "status": "AVAILABLE",
        "definition": (
            "gold-free (recipe step 2): each cell's flown first-phase boundary selections and "
            "delivered answers checked against its OWN sealed artefacts only -- boundary sets "
            "equal the arm's pinned prepared supply row by row, every row "
            "delivered an answer with its byte hash on record, and the wire contact / prompt "
            "token counts reconcile with the sealed generation-manifest cost; no gold intent, no "
            "gold bank, no cross-arm gold comparison. A mismatch is an engineering defect, "
            "reported here, and consumes the milestone (no re-fly)."
        ),
        "gold_bank_extension": {
            "status": "NOT_APPLICABLE (final-report)",
            "reason": (
                "the roster allows gold to be read only by the official scorer, after delivery "
                "(owner allowance); a per-row gold bank is not a legal channel for a final-report "
                "roster (coordinator ruling 2026-09-30), so the gold-bank delivery/conversion "
                "extension never applies here, whatever --gold-bank-roster is passed"
            ),
        },
        "detail": {"left": left_block, "right": right_block},
        "mismatches": problems,
        "phases": {"left": left_src, "right": right_src},
        "driver_sha256": digest(_DRIVER_PATH),
    }


def stage_delivery(core_args, ext: Extensions, left, right, roster) -> dict:
    ids = list(roster.ids)
    roster_id = str(roster.document.get("roster_id") or "")
    base = {"schema": SCHEMA_DELIVERY, "contacts": dict(CONTACTS_ZERO),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "left": left.spec.label, "right": right.spec.label}
    if roster.document.get("split_role") == "final-report":
        return _stage_delivery_final_report(base, left, right, ids, Path(core_args.data_root))
    bank_roster = ext.gold_bank_roster or BANK_ROSTER_OF.get(roster_id)
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


def _render_delivery_gold_free(block: dict) -> list[str]:
    detail = block["detail"]
    lines = [
        block["definition"],
        "",
        "| arm | rows | answered | missing answer | boundary selected | wire == sealed calls | tokens == sealed cost |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for label, key in ((block["left"], "left"), (block["right"], "right")):
        d = detail[key]
        c = d["contacts"]
        lines.append(
            f"| {label} | {d['rows']} | {d['answered_rows']} | {len(d['missing_answer_ids'])} | "
            f"{d['boundary_selected_rows']} | {c['contacts_equal_sealed_calls']} | "
            f"{c['prompt_tokens_total_equals_sealed_cost']} |"
        )
    lines += [
        "",
        f"Gold-bank extension: {block['gold_bank_extension']['status']}. "
        f"{block['gold_bank_extension']['reason']}",
    ]
    if block["mismatches"]:
        lines += ["", "Mismatches (engineering defects, reported, never re-flown):"]
        lines += [f"- {m}" for m in block["mismatches"]]
    return lines


def _render_delivery(block: dict) -> list[str]:
    if block.get("status") != "AVAILABLE":
        return [f"{block.get('status')}. {block.get('reason')}"]
    if "conversion" not in block:
        return _render_delivery_gold_free(block)
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
    if (root / SCORER_STRATA_FILE).is_file():  # --strata-source scorer: the aggregate receipt
        names.append(SCORER_STRATA_FILE)
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


#: The recipe's ``read_driver.scorer`` a final-report package must resolve to (condition b).
FINAL_REPORT_SCORER = "slurp-slu-official-test"


def _registered_facts(package: Path) -> tuple[Path, dict]:
    matches = sorted(package.glob("*registered-facts*.json"))
    if len(matches) != 1:
        raise Stage3ReadError(
            f"{package} carries {len(matches)} usable registered-facts documents; expected exactly one"
        )
    return matches[0], load_json(matches[0])


def _require_final_report_conditions(
    repo_root: Path, package: Path, recipe_path: Path, recipe: dict, arm: dict, replicate: dict,
    ext_ns: argparse.Namespace,
) -> str:
    """A roster whose ``split_role`` is ``final-report`` (the signed test sample) is read ONLY when
    every one of four conditions holds; this refuses BEFORE any score is opened, naming the first
    missing condition. Condition (d) -- the ledger READ row's root countersignature -- is already
    checked, unconditionally, before this function is ever reached (the refusal at the very top of
    :func:`run_package`), so it needs no repeat here. Returns the scorer id to run with (condition
    (b)'s own resolved value).
    """

    # (a) the package's OWN registered facts name every milestone read id this recipe's cells use
    # as USED under a signed owner allowance, AND that allowance's own current bytes still list
    # every one of them. Neither document is trusted alone: the registered facts could claim an id
    # the owner never signed, and the allowance's mere existence proves nothing about THIS package
    # unless the registered facts tie the two together.
    facts_path, facts = _registered_facts(package)
    allowance_block = facts.get("allowance") or {}
    allowance_relpath = allowance_block.get("path")
    used_ids = set(allowance_block.get("read_run_ids_used") or [])
    wanted = {run_id for run_id in (arm.get("run_id"), replicate.get("run_id")) if run_id}
    if not allowance_relpath or not wanted or not wanted <= used_ids:
        raise Stage3ReadError(
            f"REFUSED (final-report condition a): {facts_path.name} does not name every milestone "
            f"read id {sorted(wanted)} as used under a signed owner allowance"
        )
    allowance_path = repo_root / allowance_relpath
    if not allowance_path.is_file():
        raise Stage3ReadError(
            f"REFUSED (final-report condition a): owner allowance {allowance_relpath} is not a file"
        )
    allowance_doc = load_json(allowance_path)
    permitted = set(allowance_doc.get("read_run_ids") or []) | set(allowance_doc.get("permitted_run_ids") or [])
    missing = sorted(wanted - permitted)
    if missing:
        raise Stage3ReadError(
            f"REFUSED (final-report condition a): the owner allowance {allowance_relpath} does not "
            f"list milestone read id(s) {missing}"
        )

    # (b) the recipe's own read_driver.scorer resolves to the TEST official scorer -- the recipe,
    # not this driver, is where that decision is registered and reviewed.
    scorer_id = (recipe.get("read_driver") or {}).get("scorer")
    if scorer_id != FINAL_REPORT_SCORER:
        raise Stage3ReadError(
            f"REFUSED (final-report condition b): {recipe_path.name}'s read_driver.scorer must "
            f"resolve to {FINAL_REPORT_SCORER!r} for a final-report read (got {scorer_id!r})"
        )

    # (c) the read runs the aggregate-only in-scorer stratification (coordinator ruling
    # 2026-09-30); a per-row gold-bank stratum channel is never legal for this roster.
    if ext_ns.strata_source != "scorer":
        raise Stage3ReadError(
            "REFUSED (final-report condition c): a final-report read needs --strata-source scorer "
            f"(aggregate-only, inside the official scorer); got {ext_ns.strata_source!r}"
        )

    return scorer_id


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
    final_report = roster_doc.get("split_role") == "final-report"
    scorer_id = "slurp-slu-official-train" if discovery else "slurp-slu-official"
    if final_report:
        scorer_id = _require_final_report_conditions(
            repo_root, package, recipe_path, recipe, arm, replicate, ext_ns
        )
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
                     weighting=ext_ns.weighting, roster_floored=ext_ns.roster_floored,
                     scorer_lock_path=ext_ns.scorer_lock_path)
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
            "--scorer-id", scorer_id,
            "--expected-split-role", "discovery" if discovery else ("final-report" if final_report else "dev"),
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
            scorer_lock_path=ext_ns.scorer_lock_path,
        )
        run_pair(core_args, ext)
    except (CORE.StopStageError, CORE.ReadDriverError, Stage3ReadError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
