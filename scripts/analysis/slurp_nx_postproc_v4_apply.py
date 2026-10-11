#!/usr/bin/env python3
"""NX: apply a NAMED registered delivery normaliser (v4 or v4g) to ANY sealed SLURP column (zero GPU).

The sibling of ``scripts/analysis/slurp_nx_postproc_v4_search.py``. The search driver SELECTS rules
offline; this script APPLIES a registered rule set, by its registered id, to a sealed run and reads
the paired delta against the unmodified column:

  * ``--apply v4``   -> ``saea-deliver-normalise-v4``  (the five-rule entity stage as selected on A2)
  * ``--apply v4g``  -> ``saea-deliver-normalise-v4g`` (v4 + the ee-wilson and ti-expressible guards)

Inputs. ``--pool <run id>/<attempt>`` names a sealed run under ``$SPEECHRL_DATA_DIR/runs/`` (the
aliases ``a2`` and ``fold-a`` of the search driver's POOLS also resolve). Without ``--column`` the
column is the run's DELIVERED answers (``<run>.outputs.jsonl``); the unmodified column is those
answers as sealed, proved row by row against the sealed official per-sample fields. With
``--column <arm id>`` the column is the first-visit answer of that arm of a same-flight
node-template group (item E1, receipt ``saea-supply-variant-arms-v4``) or supply group (loop item E-S2,
receipt ``saea-supply-variant-arms-v3``), read through the E2 reader's
``load_sealed_arm_texts`` over a verified bundle and then rendered through the delivered row's OWN sealed
normaliser (``stage3_rollout_score.normalise_arm_answer``: v3 cited-answer unwrap + SLURP projection v3, the
function the official column scorer calls). That NORMALISED answer is the unmodified column and the base the
registered v4/v4g normaliser is applied to; the RAW answer is never the base, because v4/v4g begin with the full
v3 chain, which legitimately rewrites labels relative to raw text. The label guard compares against the base.

Path. Every answer goes through ``DELIVERY_NORMALISERS.resolve(<id>)`` and the offline replay row
(``analysis.deliver_normaliser_replay.replay_row``), i.e. the SAME registered entry the runtime and
the bundle verifier call. This script contains no rule logic.

Scoring. The edited column is written as a derived copy under the analysis root and scored ONCE
through the registered scorer of the run (``core.base.SCORERS``); the scorer's pooled SLU-F1 must
equal the in-process arithmetic of the search driver to 1e-6, and its port/official identity check
must pass. In the ``--column`` case the unmodified column is scored the same way. Every scorer run
records the copy's sha256 and the result's sha256 in the report. The paired delta is the
whole-utterance cluster bootstrap of the search driver (10,000 draws, seed 20260915).

Refusals (all before any scoring). The test split (the scorer must be a devel/train SLURP scorer);
a run whose roster intersects TRAIN Fold B unless a registered analysis recipe
(docs/readiness/*/analysis-recipe-*.json) names the run and attempt as its sealed arm run, declares the requested
normaliser under offline_columns.columns (and the --column under applied_to) and the attempt is sealed; a ``--label`` that would reuse a search
driver report directory (``select-a2``, ``confirm-*``); an existing report (write-once unless the
bytes are identical, as for the search driver's ``confirm-fold-a``).

Text discipline: the report holds ids, counts, pp and hashes only. Derived copies carry answer text,
as the scorer needs, and live under the analysis root, never the repository.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_postproc_v4_apply.py \\
        --apply v4g --pool a2
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-NX-POSTPROC-V4-APPLY-V1"
SCHEMA = "saea-slurp-nx-postproc-v4-apply-v1"
NORMALISERS = {"v4": "saea-deliver-normalise-v4", "v4g": "saea-deliver-normalise-v4g"}
#: scorer id -> the split it reads (the test scorer is deliberately absent).
SCORER_SPLITS = {
    "slurp-slu-official": "devel",
    "slurp-slu-official-projected-v3": "devel",
    "slurp-slu-official-train": "train",
    "slurp-slu-official-projected-v3-train": "train",
}
FOLD_B_ROSTER = "docs/receipts/rosters/slurp-evo-fold-b-v2.json"
RESERVED_LABELS = ("select-a2", "confirm-fold-a")
BASE_DELIVERED = "the delivered column as sealed"
BASE_NORMALISED_COLUMN = ("the arm's first-visit answer after the delivered row's sealed normaliser "
                          "(stage3_rollout_score.normalise_arm_answer), the column as the column scorer scored it")


class ApplyError(RuntimeError):
    pass


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DRV = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py", "slurp_nx_postproc_v4_search")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_time(text: str) -> str:
    return DRV.strip_time(text)


def resolve_run(pool: str, data_root: Path) -> dict:
    """``<run id>/<attempt>`` (or a search-driver alias) -> run spec with the scorer and split."""
    if pool in DRV.POOLS:
        spec = dict(DRV.POOLS[pool])
    else:
        run_id, sep, attempt = pool.partition("/")
        if not sep or not run_id or not attempt or "/" in attempt:
            raise ApplyError("--pool is <run id>/<attempt> or one of " + ", ".join(sorted(DRV.POOLS)))
        spec = {"run_id": run_id, "attempt": attempt}
    directory = data_root / "runs" / spec["run_id"] / spec["attempt"]
    scores = directory / f"{spec['run_id']}.scores.json"
    if not scores.is_file():
        raise ApplyError(f"no sealed scores at {scores}")
    block = json.loads(scores.read_text(encoding="utf-8"))
    if "scorer" not in spec:
        known = [k for k in block if k in SCORER_SPLITS]
        unknown = [k for k in block if str(k).startswith("slurp") and k not in SCORER_SPLITS]
        if unknown:
            raise ApplyError(f"scorer {unknown[0]!r} is not a devel/train SLURP scorer (the test split is closed)")
        if len(known) != 1:
            raise ApplyError(f"expected exactly one SLURP scorer block in {scores.name}, found {known}")
        spec["scorer"] = known[0]
    if SCORER_SPLITS.get(spec["scorer"]) is None:
        raise ApplyError(f"scorer {spec['scorer']!r} is not a devel/train SLURP scorer (the test split is closed)")
    spec["split"] = SCORER_SPLITS[spec["scorer"]]
    return spec


def recipe_admission(run_id: str, attempt: str, apply_name: str, column: str | None,
                     data_root: Path, recipe_root: Path | None = None) -> dict | None:
    """The registered analysis recipe that admits a Fold B read of this run, or None.

    A recipe admits ONLY when it (a) names the run as its sealed arm run (``arms.arm``: run id and attempt),
    (b) declares the requested normaliser under ``offline_columns.columns`` with the registered normaliser id,
    (c) lists ``--column`` (when given) in ``offline_columns.applied_to``, and (d) the attempt is sealed
    (a run manifest beside the sealed scores).
    """
    root = recipe_root or REPO_ROOT
    for path in sorted((root / "docs" / "readiness").glob("*/analysis-recipe-*.json")):
        try:
            recipe = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        arm = (recipe.get("arms") or {}).get("arm") or {}
        offline = recipe.get("offline_columns") or {}
        declared = (offline.get("columns") or {}).get(apply_name) or {}
        if arm.get("run_id") != run_id or arm.get("attempt_id") != attempt:
            continue
        if declared.get("normaliser") != NORMALISERS[apply_name]:
            continue
        if column is not None and column not in (offline.get("applied_to") or []):
            continue
        manifest = data_root / "runs" / run_id / attempt / f"{run_id}.run-manifest.json"
        if not manifest.is_file():
            raise ApplyError(f"recipe {recipe.get('recipe_id')!r} names this run but the attempt is not sealed "
                             f"(no run manifest at {manifest})")
        return {"recipe_id": recipe.get("recipe_id"), "recipe": str(path.relative_to(root)),
                "recipe_sha256": sha256_file(path)}
    return None


def refuse_fold_b(ids, admission: dict | None = None) -> None:
    """Refuse a Fold B roster unless a registered recipe admitted this read (``recipe_admission``)."""
    roster = json.loads((REPO_ROOT / FOLD_B_ROSTER).read_text(encoding="utf-8"))
    fold_b = {":".join(str(item["sample_id"]).split(":")[:3]) for item in roster["items"]}
    hit = sum(1 for sid in ids if ":".join(str(sid).split(":")[:3]) in fold_b)
    if hit and admission is None:
        raise ApplyError(f"the run's roster intersects TRAIN Fold B on {hit} rows; Fold B is not read by this script")


def column_texts(data_root: Path, spec: dict, column: str | None):
    """sample_id -> unmodified column text.

    Delivered answers as sealed, or -- for ``column`` -- that arm's first-visit answer rendered through the
    delivered row's own sealed normaliser (the column scorer's ``normalise_arm_answer``): the NORMALISED column.
    """
    directory = data_root / "runs" / spec["run_id"] / spec["attempt"]
    if column is None:
        outputs = directory / f"{spec['run_id']}.outputs.jsonl"
        return {str(r["sample_id"]): r.get("text") or "" for r in DRV.iter_jsonl(outputs)}, {
            "kind": "delivered", "outputs": [str(outputs.relative_to(data_root)), sha256_file(outputs)]}
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle

    reader = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_solver_column_read.py", "slurp_nx_solver_column_read")
    manifest = directory / f"{spec['run_id']}.run-manifest.json"
    bundle = verify_bundle(manifest)
    sealed = reader.load_sealed_arm_texts(bundle.outputs_rows, bundle.trace_records)
    if column not in sealed["texts"]:
        raise ApplyError(f"arm {column!r} is not in the run's arm group {list(sealed['arm_ids'])}")
    normalised = reader.normalise_texts({column: sealed["texts"][column]}, sealed["normaliser_ids"])[column]
    return dict(normalised), {
        "kind": ("template-arm" if sealed.get("kind", "template") == "template" else "supply-arm"), "arm_id": column, "delivering_arm": sealed["delivering"],
        "arm_ids": list(sealed["arm_ids"]), "manifest_sha256": sha256_file(manifest),
        "base": BASE_NORMALISED_COLUMN, "base_rows": len(normalised)}


def score_vectors(ids, texts, gold):
    import numpy as np
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    matrix = np.zeros((len(ids), 10), dtype=np.float64)
    unparsed = 0
    for k, sid in enumerate(ids):
        scenario, action, entities, parsed = parse_slu_response(texts[sid])
        unparsed += int(not parsed)
        matrix[k] = np.array(DRV.score_vector(gold[sid], scenario, action, list(entities)))
    return matrix, unparsed


def registered_score(copy: Path, spec: dict, lock, data_root: Path, in_process: float, label: str) -> dict:
    from speech_aware_evidence_acquisition.core.base import SCORERS
    import speech_aware_evidence_acquisition.core.scorers  # noqa: F401

    started = time.time()
    result = SCORERS.resolve(spec["scorer"])(copy, lock, data_root)
    if not result["aggregate"]["identity_check"]["passed"]:
        raise ApplyError(f"{label}: the registered scorer's port/official identity check failed on the copy")
    official = 100.0 * float(result["aggregate"]["official"]["slu_f1"])
    if abs(official - in_process) > 1e-6:
        raise ApplyError(f"{label}: registered scorer {official} != in-process {in_process}")
    return {"label": label, "scorer": spec["scorer"], "copy_sha256": sha256_file(copy),
            "result_sha256": hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode("utf-8")).hexdigest(),
            "official_slu_f1_pp": round(official, 6), "in_process_slu_f1_pp": round(in_process, 6),
            "official_intent_pp": round(100.0 * float(result["aggregate"]["official"]["intent_accuracy"]), 4),
            "seconds": round(time.time() - started, 1)}


def write_jsonl(path: Path, ids, texts) -> None:
    lines = [json.dumps({"sample_id": sid, "text": texts[sid]}, ensure_ascii=False, sort_keys=True) for sid in ids]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def check_labels_untouched(base, new, base_name: str, apply_name: str) -> None:
    """The label guard: v4/v4g add entity rules only, so no row's intent score may differ from the base column."""
    changed = [k for k in range(len(base)) if base[k][9] != new[k][9]]
    if changed:
        raise ApplyError(f"the normaliser changed an intent label on {len(changed)} rows relative to the base column "
                         f"({base_name}); {apply_name} must never touch labels beyond that base")


def apply(args) -> tuple[dict, str]:
    from speech_aware_evidence_acquisition.analysis.deliver_normaliser_replay import replay_row
    from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.rails import delivery_normalisers  # noqa: F401

    data_root = Path(args.data_root)
    normaliser_id = NORMALISERS[args.apply]
    spec = resolve_run(args.pool, data_root)
    label = args.label or "-".join(["apply", args.apply, spec["run_id"]] + ([args.column] if args.column else []))
    if label in RESERVED_LABELS or label.startswith("confirm"):
        raise ApplyError(f"label {label!r} is reserved for the search driver's reports")
    out_dir = data_root / "analysis" / READ_ID / label
    report_path = out_dir / "report.json"
    if report_path.exists() and not args.allow_rewrite_identical:
        raise ApplyError(f"{report_path} exists: an apply read is written once")

    lock = load_lock(Path(args.lock))
    texts, column_block = column_texts(data_root, spec, args.column)
    ids = sorted(texts)
    admission = recipe_admission(spec["run_id"], spec["attempt"], args.apply, args.column, data_root)
    refuse_fold_b(ids, admission)
    gold = DRV.load_gold(lock, data_root, spec["split"])
    missing = [s for s in ids if s not in gold]
    if missing:
        raise ApplyError(f"{len(missing)} roster ids absent from the {spec['split']} gold")
    base, unparsed = score_vectors(ids, texts, gold)
    base_proof = None
    if args.column is None:
        spec_rows = dict(spec, rows=len(ids))
        delivered = DRV.load_delivered(data_root, spec_rows)
        mismatches = sum(
            1 for k, sid in enumerate(ids)
            if any(abs(a - b) > 1e-9 for a, b in zip(base[k], DRV.sealed_vector(delivered["sealed"][sid]), strict=True)))
        if mismatches:
            raise ApplyError(f"{mismatches} rows: in-process scoring does not reproduce the sealed official fields")
        if abs(DRV.pooled(base)["slu_f1_pp"] - delivered["official"]["slu_f1_pp"]) > 1e-6:
            raise ApplyError("in-process pooled SLU-F1 does not reproduce the official aggregate")
        base_proof = {"rows_reproduced_exactly": len(ids), "scores": delivered["scores"],
                      "official": {k: round(v, 4) for k, v in delivered["official"].items()}}

    normaliser = DELIVERY_NORMALISERS.resolve(normaliser_id)
    edited, changed_rows, applied_rows = {}, 0, 0
    for sid in ids:
        replayed = replay_row({"sample_id": sid, "text": texts[sid]}, normaliser=normaliser)
        edited[sid] = replayed["text"]
        changed_rows += int(replayed["changed"])
        applied_rows += int(bool(replayed["applied"]))
    new, _unparsed = score_vectors(ids, edited, gold)
    check_labels_untouched(base, new, column_block.get("base", BASE_DELIVERED), args.apply)
    cluster_of = {sid: gold[sid]["utterance_id"] for sid in ids}
    boot = DRV.Bootstrap(ids, cluster_of)
    contrast = boot.contrast(base, new)
    scen = DRV.per_scenario(ids, gold, base, new)

    out_dir.mkdir(parents=True, exist_ok=True)
    scorer_runs = []
    edited_copy = out_dir / f"{args.apply}-column-outputs.jsonl"
    write_jsonl(edited_copy, ids, edited)
    scorer_runs.append(registered_score(edited_copy, spec, lock, data_root,
                                        DRV.pooled(new)["slu_f1_pp"], f"{args.apply}-column"))
    if args.column is not None:
        base_copy = out_dir / "unmodified-column-outputs.jsonl"
        write_jsonl(base_copy, ids, texts)
        scorer_runs.append(registered_score(base_copy, spec, lock, data_root,
                                            DRV.pooled(base)["slu_f1_pp"], "unmodified-column"))

    report = {
        "apply": args.apply, "normaliser_id": normaliser_id, "normaliser_version": str(normaliser.version),
        "pool": {"run_id": spec["run_id"], "attempt": spec["attempt"], "scorer": spec["scorer"],
                 "split": spec["split"], "rows": len(ids), "clusters": boot.clusters},
        "column": column_block, "fold_b_admission": admission, "unmodified_in_process": {k: round(v, 4) for k, v in DRV.pooled(base).items()},
        "edited_in_process": {k: round(v, 4) for k, v in DRV.pooled(new).items()},
        "unmodified_column_proof": base_proof, "unparsed_rows_unmodified": unparsed,
        "rows_applied": applied_rows, "rows_edited": changed_rows, "contrast": contrast,
        "per_scenario": scen,
        "bootstrap": {"draws": DRV.BOOT_DRAWS, "seed": DRV.BOOT_SEED, "cluster": "utterance_id",
                      "clusters": boot.clusters},
        "scorer_runs": scorer_runs,
        "refusals_held": ["test split (scorer allow-list)", "Fold B roster intersection (unless a registered recipe admits the run)",
                          "reserved search-driver labels", "write-once report"],
        "read_id": READ_ID, "schema": SCHEMA, "status": "DESCRIPTIVE",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "driver_sha256": sha256_file(Path(__file__)),
        "search_driver_sha256": sha256_file(REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py"),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "network": 0,
                     "gpu": 0, "paid_api": 0, "registered_scorer_on_copy": len(scorer_runs)},
    }
    return report, label


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", required=True, choices=sorted(NORMALISERS))
    parser.add_argument("--pool", required=True, help="<run id>/<attempt>, or a search-driver alias (a2, fold-a)")
    parser.add_argument("--column", default=None, help="a template-arm id of a same-flight group (default: delivered)")
    parser.add_argument("--allow-rewrite-identical", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--data-root", default=DRV.DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=DRV.DEFAULT_LOCK)
    parser.add_argument("--label", default=None)
    args = parser.parse_args(argv)
    try:
        report, label = apply(args)
    except ApplyError as error:
        raise SystemExit(f"refused: {error}") from error
    text = json.dumps(report, indent=1, sort_keys=True, default=str) + "\n"
    out_dir = Path(args.data_root) / "analysis" / READ_ID / label
    path = out_dir / "report.json"
    if path.exists() and strip_time(path.read_text(encoding="utf-8")) != strip_time(text):
        raise SystemExit(f"refused: {path} exists with different content")
    path.write_text(text, encoding="utf-8", newline="\n")
    c = report["contrast"]
    print(json.dumps({"report": str(path), "sha256": sha256_file(path), "rows_edited": report["rows_edited"],
                      "delta_slu_pp": c["delta_slu_pp"], "ci95_slu_pp": c["ci95_slu_pp"],
                      "delta_intent_pp": c["delta_intent_pp"],
                      "scorer_runs": [{k: r[k] for k in ("label", "official_slu_f1_pp", "copy_sha256")}
                                      for r in report["scorer_runs"]]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
