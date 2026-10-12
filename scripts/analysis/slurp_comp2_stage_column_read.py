#!/usr/bin/env python3
"""COMP-2 offline stage-column read (owner decision 203): COMP-1b + the registered scope-rule deliver
stage, read as a COLUMN over a sealed arm.

Owner decision 203: COMP-2 = COMP-1b + the scope rule (+ an optional none hint), read cross-flight on
DEV. The scope rule is the registered deliver stage ``saea-deliver-scope-rule-v1``
(``rails.delivery_normalisers``, merged 6cc9a3d9; pinned table
``prepared/SAEA-SLURP-SCOPE-RULE-TABLE-V1/table-v1.json``, receipt
``docs/receipts/knowledge/slurp-scope-rule-table-v1.json``). It is deterministic and gold-free, so it is
read OFFLINE: the stage runs over each sealed arm's delivered text (the bytes the official scorer
read), the result is one complete derived COLUMN (``{sample_id, text}`` per roster row), and that
column is scored ONCE with the dataset's official scorer through
``core.scoring_batch.score_complete_derived_copy`` (an exclusive, source-bound receipt; a retry never
spends a second scoring job). The delivered columns are never re-scored: their sealed official
per-sample scores are read.

Columns and contrasts (paired row bootstrap, ``analysis.bootstrap.paired_cluster_bootstrap``, 10,000
draws, seed 20260929, unit = roster row, CI95):

* ``stage_vs_delivered`` -- the arm's stage column minus the arm's delivered column (the stage's own
  effect on the arm; intent is unchanged by construction and is checked);
* ``stage_vs_aa`` -- the arm's stage column minus the in-chain A/A's delivered column (the COMP-2
  composed contrast, intent primary and SLU-F1 beside it);
* ``replicate`` -- the A/A's stage column minus the A/A's delivered column (the same edit on the
  request-identical replicate).

SLU-F1 is the official POOLED number: micro F1 over the per-sample word + char tp / fp / fn of the
official scorer (``analysis.sealed_credit.row_states.load_scores`` convention), reproduced against the
official aggregate to 1e-6 on every column or the read refuses.

VERDICT (the Q2 ruling of ``docs/superpowers/specs/2026-09-29-e5-asr-tool-slot-value-verification-
design.md``, which applies to the scope rule): the edit PASSES when its own ``stage_vs_delivered``
SLU-F1 CI95 excludes zero AND its point is at least the same-flight SLU floor scaled to the roster's
n (``1.49 * sqrt(1080 / n)``), AND the A/A replicate shows the same sign at >= 1.0 pp. Otherwise it
FAILS, and the report names each unmet leg. The verdict is descriptive input to the coordinator; it
admits nothing.

Beside it: per-entity-class (the predicted slot type of each dropped entity, split spurious / exact /
other against gold) and per-scenario tables (natural mixture and equal-scenario), and -- with
``--none-hint`` -- the none hint's TRIGGER COVERAGE only: the none hint of decision 199 is a
Solver-side action, not an offline edit, so this read never edits a row for it; it counts the arm's
rows whose Solver exemplar supply has an entity-free share >= 0.6 and, of those, the rows on which the
arm delivered at least one entity. Gold-free.

Gold discipline: gold enters only offline, through the official scorer and the governed loader
``data.slurp.load_slurp_split`` (scenario and entities for the tables), never a test split. Nothing
but ids, counts, pp and hashes is printed or persisted: no utterance text, filler, gold value or model
output. Zero model, server, tokenizer, encoder, embedder, network and GPU contacts; one official
scorer job per stage column.

Presets (``--preset``):

* ``a2`` -- cell A2's sealed arm ``SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1`` against its in-chain
  A/A ``SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1`` on DEV-2000-ADDED (scorer ``slurp-slu-official``,
  gold ``devel``), READ id ``SAEA-SLURP-STAGE3-COMP2-STAGE-COLUMN-DEV2000-READ-V1``; REFUSES before
  any score is opened unless that READ row is root countersigned;
* ``comp1b-fold-a-rehearsal`` -- the rehearsal on COMP-1b's sealed TRAIN Fold A run against
  ``SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`` (scorer ``slurp-slu-official-train``, gold ``train``), READ
  id ``SAEA-SLURP-COMP2-STAGE-COLUMN-COMP1B-FOLD-A-REHEARSAL-V1`` (a model-free-check row registered
  before result reading).

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src python scripts/analysis/slurp_comp2_stage_column_read.py \\
        --preset comp1b-fold-a-rehearsal [--none-hint] [--data-root DIR] [--lock PATH] [--dry-run]
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

SCHEMA = "saea-slurp-comp2-stage-column-read-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
LEDGER = "docs/exposure-ledger.md"
BOOT_SEED = 20260929
BOOT_N = 10_000
BOOT_LEVEL = 0.95
#: Q2 ruling: the same-flight SLU floor, 1.49 pp at n = 1,080, scaled by sqrt(1080 / n).
FLOOR_ANCHOR = (1080, 1.49)
REPLICATE_MIN_PP = 1.0
NONE_HINT_THETA = 0.6
EX_FACET_PREFIX = "train-exemplars::facet:content:"
EX_SNAPSHOT = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
COUNTERSIGNED = re.compile(r"\broot\s+countersigned\b", re.IGNORECASE)

PRESETS: dict[str, dict[str, Any]] = {
    "a2": {
        "read_id": "SAEA-SLURP-STAGE3-COMP2-STAGE-COLUMN-DEV2000-READ-V1",
        "arm_experiment": "slurp-native-stage3-comp1b-dev2000-added-v1",
        "aa_experiment": "slurp-native-stage3-comp1-aa-dev2000-added-v1",
        "scorer_id": "slurp-slu-official",
        "gold_split": "devel",
        "rows": 1000,
        "require_countersigned": True,
    },
    "comp1b-fold-a-rehearsal": {
        "read_id": "SAEA-SLURP-COMP2-STAGE-COLUMN-COMP1B-FOLD-A-REHEARSAL-V1",
        "arm_experiment": "slurp-native-stage3-comp1b-fold-a-v1",
        "aa_experiment": "slurp-native-stage3-comp1-aa-fold-a-v1",
        "scorer_id": "slurp-slu-official-train",
        "gold_split": "train",
        "rows": 1080,
        "require_countersigned": False,
    },
}


class ColumnReadError(RuntimeError):
    """A sealed input is missing, drifted, or does not have the shape this read needs."""


# ---------------------------------------------------------------------------
# Pure arithmetic (tested on fakes)
# ---------------------------------------------------------------------------


def floor_pp(rows: int) -> float:
    anchor_n, anchor_pp = FLOOR_ANCHOR
    return anchor_pp * math.sqrt(anchor_n / rows)


def pooled_f1(totals: Sequence[float]) -> float:
    tp, fp, fn = totals
    denominator = 2 * tp + fp + fn
    return 0.0 if denominator == 0 else 2 * tp / denominator


def slu_counts(sample: Mapping[str, Any]) -> tuple[float, float, float]:
    """word + char tp / fp / fn of one official per-sample row (row_states.load_scores convention)."""

    return (
        float(sample["slu_f1_word_tp"]) + float(sample["slu_f1_char_tp"]),
        float(sample["slu_f1_word_fp"]) + float(sample["slu_f1_char_fp"]),
        float(sample["slu_f1_word_fn"]) + float(sample["slu_f1_char_fn"]),
    )


def column_from_official(per_sample: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for row in per_sample:
        out[str(row["sample_id"])] = {
            "intent": bool(float(row["scenario_action_exact"]) >= 1.0),
            "counts": slu_counts(row),
        }
    return out


def column_metrics(column: Mapping[str, Mapping[str, Any]], ids: Sequence[str]) -> dict[str, float]:
    totals = [sum(column[s]["counts"][k] for s in ids) for k in range(3)]
    return {"slu_f1_pp": 100.0 * pooled_f1(totals),
            "intent_pp": 100.0 * sum(column[s]["intent"] for s in ids) / len(ids)}


def contrast(ids: Sequence[str], left: Mapping[str, Mapping[str, Any]], right: Mapping[str, Mapping[str, Any]],
             *, bootstrap: Callable | None = None, n_replicates: int = BOOT_N, seed: int = BOOT_SEED) -> dict:
    """right minus left, paired per roster row, SLU-F1 (pooled) and intent, with CI95."""

    if bootstrap is None:
        from speech_aware_evidence_acquisition.analysis.bootstrap import paired_cluster_bootstrap as bootstrap

    def slu(xs):
        return column_metrics(right, xs)["slu_f1_pp"] - column_metrics(left, xs)["slu_f1_pp"]

    def intent(xs):
        return column_metrics(right, xs)["intent_pp"] - column_metrics(left, xs)["intent_pp"]

    out = {}
    for name, statistic in (("slu_f1", slu), ("intent", intent)):
        result = bootstrap(sample_ids=list(ids), statistic=statistic, n_replicates=n_replicates, seed=seed,
                           ci_level=BOOT_LEVEL)
        out[name] = {"point_pp": round(result.point_estimate, 4),
                     "ci95_pp": [round(result.ci_low, 4), round(result.ci_high, 4)]}
    out["left"] = {k: round(v, 4) for k, v in column_metrics(left, ids).items()}
    out["right"] = {k: round(v, 4) for k, v in column_metrics(right, ids).items()}
    out["intent_rows_changed"] = sum(left[s]["intent"] != right[s]["intent"] for s in ids)
    return out


def q2_verdict(own: Mapping[str, Any], replicate: Mapping[str, Any], rows: int) -> dict:
    """The Q2 ruling: own CI excludes zero AND point >= the scaled floor; A/A same sign >= 1.0 pp."""

    point = own["point_pp"]
    low, high = own["ci95_pp"]
    floor = floor_pp(rows)
    legs = {
        "own_ci_excludes_zero": bool(low > 0 or high < 0),
        "own_point_at_or_above_floor": bool(abs(point) >= floor and point > 0),
        "replicate_same_sign_at_least_1pp": bool(
            point != 0 and math.copysign(1, replicate["point_pp"]) == math.copysign(1, point)
            and abs(replicate["point_pp"]) >= REPLICATE_MIN_PP),
    }
    passed = all(legs.values())
    return {
        "rule": "Q2 (E5 spec, coordinator ruling): own paired row-bootstrap SLU-F1 CI95 excluding zero AND point >= "
                "1.49 * sqrt(1080 / n); the A/A replicate the same sign at >= 1.0 pp",
        "floor_pp": round(floor, 4), "rows": rows, "legs": legs,
        "verdict": "PASSES-Q2" if passed else "FAILS-Q2",
        "unmet": [name for name, ok in legs.items() if not ok],
    }


def apply_stage(texts: Mapping[str, str], stage: Callable, table, parse: Callable) -> dict[str, dict[str, Any]]:
    """Run the registered stage over each delivered text; prove the re-rendered text parses to the kept
    entities. Returns ``{sid: {text, dropped, entities_in, dropped_types}}``."""

    from speech_aware_evidence_acquisition.rails.delivery_normalisers import validate_scope_rule_receipt

    out = {}
    for sid, text in texts.items():
        normalisation = stage(text, table=table)
        receipt = validate_scope_rule_receipt(dict(normalisation.receipt))
        dropped = list(receipt["dropped_entity_indices"])
        types: list[str] = []
        if dropped:
            _s, _a, entities, parsed = parse(text)
            _s2, _a2, kept, parsed2 = parse(normalisation.text)
            expect = [(e.type, e.filler) for i, e in enumerate(entities) if i not in dropped]
            if not parsed or not parsed2 or [(e.type, e.filler) for e in kept] != expect:
                raise ColumnReadError(f"{sid}: the stage's text does not parse to the kept entities")
            types = [entities[i].type for i in dropped]
        elif normalisation.text != text:
            raise ColumnReadError(f"{sid}: the stage changed a row it dropped nothing from")
        out[sid] = {"text": normalisation.text, "dropped": dropped, "entities_in": receipt["entities_in"],
                    "dropped_types": types}
    return out


def none_hint_coverage(ranked: Mapping[str, Sequence[str]], entity_free: Mapping[str, bool],
                       delivered_entities: Mapping[str, int], theta: float = NONE_HINT_THETA) -> dict:
    """Descriptive trigger coverage of the none hint: rows whose exemplar supply's entity-free share is
    >= theta, and of those the rows where the arm delivered >= 1 entity. Gold-free; edits nothing."""

    unresolved = sorted({eid for ids in ranked.values() for eid in ids if eid not in entity_free})
    triggered = []
    for sid, ids in ranked.items():
        if not ids:
            continue
        share = sum(bool(entity_free.get(eid, False)) for eid in ids) / len(ids)
        if share >= theta:
            triggered.append(sid)
    return {
        "theta": theta,
        "rows_with_supply": sum(1 for v in ranked.values() if v),
        "rows_triggered": len(triggered),
        "rows_triggered_with_delivered_entities": sum(1 for s in triggered if delivered_entities.get(s, 0) > 0),
        "entities_delivered_on_triggered_rows": sum(delivered_entities.get(s, 0) for s in triggered),
        "unresolved_exemplar_ids": len(unresolved),
        "note": "decision 199's none hint is a Solver-side action; this read counts its trigger, it edits no row",
    }


def per_scenario(ids: Sequence[str], scenario: Mapping[str, str], base: Mapping[str, Mapping[str, Any]],
                 edited: Mapping[str, Mapping[str, Any]], rows_edited: set) -> dict:
    groups: dict[str, list[str]] = defaultdict(list)
    for sid in ids:
        groups[scenario[sid]].append(sid)
    table = {}
    for name in sorted(groups):
        xs = groups[name]
        b, e = column_metrics(base, xs), column_metrics(edited, xs)
        table[name] = {"rows": len(xs), "rows_edited": sum(1 for s in xs if s in rows_edited),
                       "delivered_slu_f1_pp": round(b["slu_f1_pp"], 4), "stage_slu_f1_pp": round(e["slu_f1_pp"], 4),
                       "delta_pp": round(e["slu_f1_pp"] - b["slu_f1_pp"], 4)}
    equal = sum(v["delta_pp"] for v in table.values()) / len(table)
    whole = column_metrics(edited, ids)["slu_f1_pp"] - column_metrics(base, ids)["slu_f1_pp"]
    return {"per_scenario": table, "natural_mixture_delta_pp": round(whole, 4),
            "equal_scenario_delta_pp": round(equal, 4), "scenarios": len(table)}


def per_entity_class(ids: Sequence[str], staged: Mapping[str, Mapping[str, Any]], pred: Mapping[str, tuple],
                     gold: Mapping[str, tuple] | None, items: Callable | None) -> dict:
    table: dict[str, Counter] = defaultdict(Counter)
    for sid in ids:
        dropped = staged[sid]["dropped"]
        if not dropped:
            continue
        spur = matched = set()
        if gold is not None and items is not None:
            its = items(gold[sid], pred[sid])
            spur = {it["pred_index"] for it in its if it["gold_index"] is None}
            matched = {it["pred_index"] for it in its if it["pred_index"] is not None}
        for index in dropped:
            slot_type = pred[sid][index].type
            table[slot_type]["dropped"] += 1
            if gold is not None:
                table[slot_type]["spurious" if index in spur else "exact" if index not in matched else "other"] += 1
    return {k: dict(sorted(v.items())) for k, v in sorted(table.items())}


def read_countersigned(ledger_text: str, run_id: str) -> bool | None:
    """True when the run id's ledger row carries a root countersignature; None when there is no row."""

    for line in ledger_text.split("\n"):
        if not line.startswith("| "):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) > 2 and parts[2] == run_id:
            return bool(COUNTERSIGNED.search(line)) and "countersignature pending" not in line.lower()
    return None


# ---------------------------------------------------------------------------
# I/O (the sealed runs, the official scorer)
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def resolve_run(repo_root: Path, experiment: str) -> tuple[str, str]:
    document = json.loads((repo_root / "configs/experiment" / f"{experiment}.json").read_text(encoding="utf-8"))
    cell = document["cells"][0]
    return cell["run_id"], cell["attempt_id"]


def load_sealed(data_root: Path, run_id: str, attempt: str, scorer_id: str, rows: int) -> dict:
    from speech_aware_evidence_acquisition.core.bundle.verify import verify_bundle

    directory = data_root / "runs" / run_id / attempt
    manifest = directory / f"{run_id}.run-manifest.json"
    if not manifest.is_file():
        raise ColumnReadError(f"{run_id}: no sealed run manifest at {manifest} (not sealed yet?)")
    bundle = verify_bundle(manifest)
    if bundle.manifest.get("status") != "COMPLETED" or bundle.attempt_state != "FINALIZED":
        raise ColumnReadError(f"{run_id}: the bundle is not a finalized complete attempt")
    texts = {}
    for row in bundle.outputs_rows:
        texts[str(row["sample_id"])] = row.get("text") or ""
    if len(texts) != rows or set(texts) != set(bundle.split_ids):
        raise ColumnReadError(f"{run_id}: not the complete {rows}-row roster")
    scores_path = directory / f"{run_id}.scores.json"
    document = json.loads(scores_path.read_text(encoding="utf-8"))
    if scorer_id not in document:
        raise ColumnReadError(f"{run_id}: no sealed {scorer_id} score")
    block = document[scorer_id]
    column = column_from_official(block["per_sample"])
    if set(column) != set(texts):
        raise ColumnReadError(f"{run_id}: the sealed scores do not cover the roster exactly")
    official = float(block["aggregate"]["official"]["slu_f1"])
    mine = column_metrics(column, sorted(column))["slu_f1_pp"] / 100.0
    if abs(official - mine) > 1e-6:
        raise ColumnReadError(f"{run_id}: pooled word+char counts do not reproduce the official SLU-F1")
    return {"run_id": run_id, "attempt": attempt, "directory": directory, "manifest": manifest, "texts": texts,
            "column": column, "outputs_sha256": bundle.manifest["outputs"]["sha256"],
            "scores": {"relpath": str(scores_path.relative_to(data_root)), "sha256": sha256_file(scores_path)},
            "official": {"slu_f1": official, "intent_accuracy": float(block["aggregate"]["official"]["intent_accuracy"])}}


def write_column(path: Path, ids: Sequence[str], staged: Mapping[str, Mapping[str, Any]]) -> str:
    text = "".join(json.dumps({"sample_id": sid, "text": staged[sid]["text"]}, ensure_ascii=False, sort_keys=True) + "\n"
                   for sid in ids)
    data = text.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    if path.exists():
        if sha256_file(path) != digest:
            raise ColumnReadError(f"{path} exists with other bytes; refusing to overwrite a rendered column")
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
    return digest


def score_column(sealed: Mapping[str, Any], column_path: Path, column_sha: str, scorer_id: str, out_dir: Path,
                 lock, data_root: Path, binding: Mapping[str, Any], *, scorer: Callable | None = None) -> dict:
    if scorer is None:
        from speech_aware_evidence_acquisition.core.scoring_batch import score_complete_derived_copy as scorer
    result = scorer(parent_manifest=sealed["manifest"], outputs_copy=column_path, expected_copy_sha256=column_sha,
                    scorer_id=scorer_id, result_path=out_dir / f"{column_path.stem}-{scorer_id}-scores.json",
                    lock=lock, data_root=data_root, column_binding=dict(binding))
    column = column_from_official(result["per_sample"])
    official = float(result["aggregate"]["official"]["slu_f1"])
    mine = column_metrics(column, sorted(column))["slu_f1_pp"] / 100.0
    if abs(official - mine) > 1e-6:
        raise ColumnReadError(f"{column_path.name}: pooled counts do not reproduce the official SLU-F1")
    return {"column": column, "official": {"slu_f1": official,
                                           "intent_accuracy": float(result["aggregate"]["official"]["intent_accuracy"])}}


def ranked_exemplars(directory: Path, run_id: str) -> dict[str, list[str]]:
    """The arm's Solver exemplar ranking per row, from its sealed phases (headroom read idiom)."""

    path = directory / f"{run_id}.phases.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for phase in document["phases"]:
        for result in phase["results"]:
            sid = result["sample_id"]
            if sid in out:
                continue
            for wave in result.get("waves") or ():
                candidates = (wave.get("rank_result") or {}).get("candidates") or []
                ex = [str(c["facet_id"]).split(EX_FACET_PREFIX, 1)[-1] for c in candidates
                      if str(c["facet_id"]).startswith(EX_FACET_PREFIX)]
                if ex:
                    out[sid] = ex
                    break
    return out


def exemplar_entity_free(data_root: Path) -> dict[str, bool]:
    GP = import_path(REPO_ROOT / "scripts/analysis/slurp_gold_position_and_solver_freedom_read.py",
                     "slurp_gold_position_and_solver_freedom_read")
    pool = GP.load_exemplar_pool(data_root, EX_SNAPSHOT)
    return {key: not value["fillers"] for key, value in pool["values"].items()}


def run(args) -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items
    from speech_aware_evidence_acquisition.rails import delivery_normalisers as DN
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity, parse_slu_response

    preset = PRESETS[args.preset]
    data_root = Path(args.data_root)
    read_id = preset["read_id"]
    if preset["gold_split"] == "test" or "test" in preset["scorer_id"]:
        raise ColumnReadError("this read never touches the test split")
    if preset["require_countersigned"]:
        state = read_countersigned((REPO_ROOT / LEDGER).read_text(encoding="utf-8"), read_id)
        if state is not True:
            raise ColumnReadError(f"REFUSED: the READ row {read_id} is {'missing' if state is None else 'not root countersigned'}; "
                                  "no score is opened before the countersignature")
    arm_run, arm_attempt = resolve_run(REPO_ROOT, preset["arm_experiment"])
    aa_run, aa_attempt = resolve_run(REPO_ROOT, preset["aa_experiment"])
    rows = preset["rows"]
    arm = load_sealed(data_root, arm_run, arm_attempt, preset["scorer_id"], rows)
    aa = load_sealed(data_root, aa_run, aa_attempt, preset["scorer_id"], rows)
    if set(arm["texts"]) != set(aa["texts"]):
        raise ColumnReadError("the arm and its A/A are not the same roster")
    ids = sorted(arm["texts"])

    table_path = data_root / DN.SCOPE_RULE_TABLE_RELPATH
    table = DN.ScopeRuleTable.from_bytes(table_path.read_bytes(), expected_sha256=DN.SCOPE_RULE_TABLE_SHA256)
    stage = DN.DELIVERY_NORMALISERS.resolve(DN.DELIVER_SCOPE_RULE_V1)
    staged = {"arm": apply_stage(arm["texts"], stage, table, parse_slu_response),
              "aa": apply_stage(aa["texts"], stage, table, parse_slu_response)}
    out_dir = data_root / "analysis" / read_id
    columns = {}
    for label, sealed in (("arm", arm), ("aa", aa)):
        path = out_dir / "columns" / f"{label}-scope-rule-stage.jsonl"
        columns[label] = {"path": path, "sha256": write_column(path, ids, staged[label])}
    render = {
        "schema": SCHEMA + "-render", "read_id": read_id,
        "stage": {"id": DN.DELIVER_SCOPE_RULE_V1, "version": DN.DELIVER_SCOPE_RULE_V1_VERSION},
        "table": {"relpath": DN.SCOPE_RULE_TABLE_RELPATH, "sha256": table.sha256},
        "columns": {k: {"relpath": str(v["path"].relative_to(data_root)), "sha256": v["sha256"]} for k, v in columns.items()},
        "sources": {"arm": {"run_id": arm_run, "attempt": arm_attempt, "outputs_sha256": arm["outputs_sha256"]},
                    "aa": {"run_id": aa_run, "attempt": aa_attempt, "outputs_sha256": aa["outputs_sha256"]}},
    }
    render_path = out_dir / "render-manifest.json"
    render_text = json.dumps(render, indent=2, sort_keys=True) + "\n"
    if render_path.exists() and render_path.read_text(encoding="utf-8") != render_text:
        raise ColumnReadError("a different render manifest already exists for this read id")
    render_path.write_text(render_text, encoding="utf-8")
    if args.dry_run:
        return {"dry_run": True, "read_id": read_id, "render": render,
                "rows_edited": {k: sum(1 for s in ids if staged[k][s]["dropped"]) for k in staged}}

    lock = load_lock(Path(args.lock))
    scored = {}
    for label, sealed in (("arm", arm), ("aa", aa)):
        scored[label] = score_column(
            sealed, columns[label]["path"], columns[label]["sha256"], preset["scorer_id"], out_dir / "scores", lock,
            data_root, {"read_id": read_id, "column": f"{label}-scope-rule-stage", "stage": DN.DELIVER_SCOPE_RULE_V1,
                        "table_sha256": table.sha256, "render_manifest_sha256": sha256_file(render_path)})

    contrasts = {
        "stage_vs_delivered": contrast(ids, arm["column"], scored["arm"]["column"]),
        "stage_vs_aa": contrast(ids, aa["column"], scored["arm"]["column"]),
        "delivered_vs_aa": contrast(ids, aa["column"], arm["column"]),
        "replicate": contrast(ids, aa["column"], scored["aa"]["column"]),
    }
    verdict = q2_verdict(contrasts["stage_vs_delivered"]["slu_f1"], contrasts["replicate"]["slu_f1"], rows)

    records = load_slurp_split(lock, data_root, preset["gold_split"], workers=4)
    wanted = set(ids)
    scenario = {r.sample_id: r.scenario for r in records if r.sample_id in wanted}
    gold = {r.sample_id: tuple(SlotEntity(e.type, e.filler) for e in r.entities) for r in records if r.sample_id in wanted}
    del records
    if set(scenario) != wanted:
        raise ColumnReadError("the governed loader does not cover the roster")
    tables = {}
    for label, sealed in (("arm", arm), ("aa", aa)):
        pred = {sid: tuple(parse_slu_response(sealed["texts"][sid])[2]) for sid in ids}
        edited = {s for s in ids if staged[label][s]["dropped"]}
        tables[label] = {
            "rows_edited": len(edited),
            "entities_dropped": sum(len(staged[label][s]["dropped"]) for s in ids),
            "per_entity_class": per_entity_class(ids, staged[label], pred, gold, entity_items),
            "scenario": per_scenario(ids, scenario, sealed["column"], scored[label]["column"], edited),
        }

    none_hint = None
    if args.none_hint:
        ranked = ranked_exemplars(arm["directory"], arm_run)
        delivered = {sid: len(parse_slu_response(arm["texts"][sid])[2]) for sid in ids}
        none_hint = none_hint_coverage(ranked, exemplar_entity_free(data_root), delivered)

    report = {
        "schema": SCHEMA,
        "read_id": read_id,
        "preset": args.preset,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": rows,
        "scorer_id": preset["scorer_id"],
        "gold_split": preset["gold_split"],
        "stage": render["stage"],
        "table": render["table"],
        "render_manifest": {"relpath": str(render_path.relative_to(data_root)), "sha256": sha256_file(render_path)},
        "sources": {label: {"run_id": s["run_id"], "attempt": s["attempt"], "outputs_sha256": s["outputs_sha256"],
                            "scores": s["scores"], "official": s["official"]} for label, s in (("arm", arm), ("aa", aa))},
        "stage_columns": {label: {**render["columns"][label], "official": scored[label]["official"]} for label in scored},
        "contrasts": contrasts,
        "verdict_q2": verdict,
        "tables": tables,
        "none_hint_trigger_coverage": none_hint,
        "bootstrap": {"primitive": "analysis.bootstrap.paired_cluster_bootstrap", "unit": "roster row",
                      "seed": BOOT_SEED, "replicates": BOOT_N, "ci_level": BOOT_LEVEL},
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "network": 0, "gpu": 0,
                     "official_scorer_jobs": len(scored)},
        "boundary": "DESCRIPTIVE development read; ids, counts, pp and hashes only; admits nothing",
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    (out_dir / "report.json").write_text(text, encoding="utf-8", newline="\n")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--preset", required=True, choices=sorted(PRESETS))
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--none-hint", action="store_true", help="also report the none hint's trigger coverage (descriptive)")
    parser.add_argument("--dry-run", action="store_true", help="render and hash the stage columns; score nothing")
    args = parser.parse_args(argv)
    try:
        report = run(args)
    except ColumnReadError as error:
        print(f"REFUSED: {error}")
        return 3
    summary = {k: report[k] for k in ("read_id", "rows") if k in report}
    if report.get("dry_run"):
        summary.update({"dry_run": True, "rows_edited": report["rows_edited"], "render": report["render"]["columns"]})
    else:
        summary.update({"contrasts": {k: {m: v[m] for m in ("slu_f1", "intent", "intent_rows_changed")}
                                      for k, v in report["contrasts"].items()},
                        "verdict_q2": report["verdict_q2"],
                        "rows_edited": {k: v["rows_edited"] for k, v in report["tables"].items()},
                        "entities_dropped": {k: v["entities_dropped"] for k, v in report["tables"].items()},
                        "none_hint_trigger_coverage": report["none_hint_trigger_coverage"]})
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
