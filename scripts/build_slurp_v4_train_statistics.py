#!/usr/bin/env python3
"""Build the four pinned TRAIN-statistics tables of ``saea-deliver-normalise-v4`` (NX R0.4 / E4).

The R0.4 read (``docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md`` section 6) says
the TRAIN statistics behind v4's fx-article, fx-oclock, ti1 and ee10 steps must be frozen as pinned
tables, as the scope table is, before v4 can be registered. This builder freezes them, with the
scope table's conventions (``scripts/build_slurp_scope_rule_table.py``): write-once files under the
data root, a counts-and-hashes receipt in the repository, and an exposure-ledger row.

WHAT IT BUILDS. Under ``prepared/SAEA-SLURP-V4-TRAIN-STATISTICS-V1/``:

  article-strip-v1.json        per (slot type, determiner): [span includes it, span is preceded by it]
                               over the pool, the rule's thresholds (< 10 % of >= 10) and the derived
                               strip set (73 pairs on the R5 pool)
  oclock-v1.json               time fillers ending in "o'clock" vs followed by it, thresholds, decision
  type-by-intent-v1.json       per intent: exemplar count and per-slot-type exemplar counts (ti1, < 1 %)
  intent-entity-rate-v1.json   per intent: exemplar count and entity-carrying exemplar count (ee10, < 10 %)

The arithmetic is ``rails.delivery_normalisers.v4_pool_counts`` / ``v4_table_bytes`` -- the runtime's
own code -- and the builder proves it equals the offline search driver's ``TrainStats`` on the real
pool before writing anything. The pool is the scope table's R5 pool
(``size-pool-annotated-exemplars-minus-r01``, content pin ``6eaa03ae...``), parsed by the same
``load_exemplar_pool``; disjointness from Fold A, Fold B, R01 and R01C is re-proved here.

BOUNDARY. Model-free: zero model, server, encoder, embedder, tokenizer, ASR, scorer, network, GPU and
paid-API contact. TRAIN construction text only; no evaluated row's gold is read. The tables hold slot
TYPE names, determiner words, intent ids and counts -- never a filler, utterance or value -- and they
live under the data root anyway, by convention. The receipt carries counts and hashes only.

    python scripts/build_slurp_v4_train_statistics.py --data-root "$SPEECHRL_DATA_DIR" --dry
    python scripts/build_slurp_v4_train_statistics.py --data-root "$SPEECHRL_DATA_DIR"
    python scripts/build_slurp_v4_train_statistics.py --data-root "$SPEECHRL_DATA_DIR" --check
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails import delivery_normalisers as DN  # noqa: E402

LEDGER_ROW = "SAEA-SLURP-V4-TRAIN-STATISTICS-BUILD-V1"
BUILDER_ID = "saea-slurp-v4-train-statistics-v1"
RECEIPT_SCHEMA = "saea-slurp-v4-train-statistics-receipt-v1"
RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-v4-train-statistics-v1.json"
EXTRA_FORBIDDEN_ROSTERS = ("docs/receipts/rosters/slurp-stage3-construction-r01c.json",)
#: The R0.4 read's count of the strip set on this pool (section 6, step 2).
EXPECTED_ARTICLE_STRIP_PAIRS = 73


class BuildError(RuntimeError):
    pass


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def receipt_bytes(document: dict) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def build(root: Path) -> dict:
    w3a = import_path(REPO_ROOT / "scripts/build_slurp_intent_contrast_cards.py", "build_slurp_intent_contrast_cards")
    gp = import_path(REPO_ROOT / "scripts/analysis/slurp_gold_position_and_solver_freedom_read.py",
                     "slurp_gold_position_and_solver_freedom_read")
    drv = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py", "slurp_nx_postproc_v4_search")
    pool_relpath, pool_content_sha = w3a.POOL
    if {"relpath": pool_relpath, "content_sha256": pool_content_sha} != DN.V4_STATS_CONSTRUCTION_POOL:
        raise BuildError("the contrast-card builder's pool pin is not the v4 statistics' construction pool")
    if tuple(drv.STATS_POOL) != (pool_relpath, pool_content_sha):
        raise BuildError("the search driver's statistics pool is not the v4 statistics' construction pool")
    pinned = w3a.load_pool(root)
    rosters = {}
    for relpath in (*w3a.FORBIDDEN_ROSTERS, *EXTRA_FORBIDDEN_ROSTERS):
        roster = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
        ids = {":".join(str(item["sample_id"]).split(":")[:3]) for item in roster["items"]}
        overlap = len(pinned["utterances"] & ids)
        if overlap:
            raise BuildError(f"the construction pool intersects {relpath} on {overlap} utterances")
        rosters[relpath] = {"sha256": sha_file(REPO_ROOT / relpath), "utterances": len(ids), "overlap": 0}
    pool = gp.load_exemplar_pool(root, pool_relpath)
    if pool["content_sha256"] != pool_content_sha:
        raise BuildError("the parsed pool's snapshot_sha256 is not the pinned content hash")
    if len(pool["values"]) != len(pinned["utterances"]):
        raise BuildError("one exemplar per pool utterance expected")
    counts = DN.v4_pool_counts(pool["values"])
    blobs = DN.v4_table_bytes(counts, DN.V4_STATS_CONSTRUCTION_POOL)
    stats = DN.SlurpV4Statistics.from_table_bytes(blobs, expected_sha256=None)
    # Parity with the offline driver that selected and confirmed v4, on the real pool.
    offline = drv.TrainStats(pool["values"])
    if (stats.article_strip != frozenset(offline.article_strip) or stats.oclock_strip != offline.oclock["strip"]
            or stats.intent_n != dict(offline.intent_n)
            or stats.intent_with_entities != dict(offline.intent_with_entities)
            or stats.intent_type != {i: dict(t) for i, t in offline.intent_type.items()}):
        raise BuildError("the runtime statistics differ from the offline driver's TrainStats")
    if len(stats.article_strip) != EXPECTED_ARTICLE_STRIP_PAIRS:
        raise BuildError(f"{len(stats.article_strip)} strip pairs, not the read's {EXPECTED_ARTICLE_STRIP_PAIRS}")
    if stats.sha256 != DN.SlurpV4Statistics.from_pool_values(pool["values"]).sha256:
        raise BuildError("table round trip changes the statistics")
    return {
        "blobs": blobs, "stats": stats, "counts": counts,
        "pool": {"relpath": pool_relpath, "content_sha256": pool_content_sha, "file_sha256": pool["sha256"],
                 "utterances": len(pinned["utterances"]), "exemplars": len(pool["values"])},
        "rosters": rosters,
    }


def write_once(path: Path, data: bytes, *, dry: bool) -> str:
    digest = sha_bytes(data)
    if dry:
        return digest
    if path.exists():
        if sha_file(path) != digest:
            raise BuildError(f"refusing to overwrite {path} with different bytes")
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest


def receipt(built: dict, digests: dict) -> dict:
    stats, counts = built["stats"], built["counts"]
    observed_pairs = len(set(counts["article_included"]) | set(counts["article_excluded"]))
    return {
        "schema": RECEIPT_SCHEMA,
        "artifact_id": DN.V4_STATS_ARTIFACT_ID,
        "builder_id": BUILDER_ID,
        "exposure_ledger_row": LEDGER_ROW,
        "normaliser": {"id": DN.DELIVER_NORMALISE_V4, "version": DN.DELIVER_NORMALISE_V4_VERSION,
                       "entity_stage": list(DN.V4_STAGES)},
        "builder": {"relpath": "scripts/build_slurp_v4_train_statistics.py", "sha256": sha_file(Path(__file__))},
        "boundary": "No filler, utterance, value or card text appears in this receipt or the tables: slot type "
                    "names, determiner words, intent ids, counts and hashes only.",
        "contacts": {k: 0 for k in ("asr", "embedder", "encoder", "gpu", "model", "network", "paid_api",
                                    "scorer", "server", "tokenizer")},
        "inputs": {"construction_pool": built["pool"], "forbidden_rosters": built["rosters"]},
        "method": {
            "arithmetic": "rails.delivery_normalisers.v4_pool_counts / v4_table_bytes, proved equal to "
                          "scripts/analysis/slurp_nx_postproc_v4_search.py TrainStats on this pool",
            "fx_article": f"strip (type, w) when pool spans include w in < {DN.V4_ARTICLE_MAX_INCLUDED_SHARE} of "
                          f">= {DN.V4_ARTICLE_MIN_OPPORTUNITIES} opportunities (w precedes or opens the span)",
            "fx_oclock": f"strip a trailing o'clock from a time filler when the pool includes it in < "
                         f"{DN.V4_ARTICLE_MAX_INCLUDED_SHARE} of >= {DN.V4_OCLOCK_MIN_OPPORTUNITIES} opportunities",
            "ti1": f"drop an entity whose type occurs in < {DN.V4_TI_MIN_SHARE} of the delivered intent's pool "
                   "exemplars (intent absent from the pool: left alone)",
            "ee10": f"empty a row whose delivered intent carries entities in < {DN.V4_EE_MIN_ENTITY_RATE} of its "
                    "pool exemplars (intent absent: left alone; an empty list is never filled)",
            "roster_ruling": "R5: TRAIN minus Fold A, minus Fold B, minus R01/R01C (the scope table's pool)",
        },
        "counts": {
            "pool_exemplars": sum(stats.intent_n.values()),
            "intents": len(stats.intent_n),
            "intent_type_bindings": sum(len(t) for t in stats.intent_type.values()),
            "article_pairs_observed": observed_pairs,
            "article_strip_pairs": len(stats.article_strip),
            "oclock": {"included": counts["oclock_included"], "excluded": counts["oclock_excluded"],
                       "strip": stats.oclock_strip},
            "intents_entity_rate_below_10pct": sum(1 for i in stats.intent_n if stats.entity_rate(i) < 0.10),
        },
        "outputs": {name: {"relpath": DN.V4_TABLE_RELPATHS[name], "sha256": digests[name]} for name in DN.V4_TABLES},
        "statistics_sha256": stats.sha256,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry", action="store_true", help="build and measure, write nothing")
    mode.add_argument("--check", action="store_true", help="rebuild and compare with the written tables and pins")
    args = parser.parse_args(argv)
    root: Path = args.data_root
    if not str(root) or not root.is_dir():
        raise SystemExit("--data-root (or SPEECHRL_DATA_DIR) is required")
    built = build(root)
    digests = {name: sha_bytes(data) for name, data in built["blobs"].items()}
    if args.check:
        written = {name: (root / DN.V4_TABLE_RELPATHS[name]) for name in DN.V4_TABLES}
        same = all(p.is_file() and sha_file(p) == digests[n] for n, p in written.items())
        rec = json.loads((REPO_ROOT / RECEIPT_RELPATH).read_text(encoding="utf-8"))
        receipt_same = {n: rec["outputs"][n]["sha256"] for n in DN.V4_TABLES} == digests
        runtime_same = dict(DN.V4_TABLE_SHA256) == digests and DN.V4_STATS_SHA256 == built["stats"].sha256
        print(json.dumps({"tables_identical": same, "receipt_pins_identical": receipt_same,
                          "runtime_pins_identical": runtime_same, "sha256": digests,
                          "statistics_sha256": built["stats"].sha256}, indent=2))
        return 0 if same and receipt_same and runtime_same else 1
    for name in DN.V4_TABLES:
        write_once(root / DN.V4_TABLE_RELPATHS[name], built["blobs"][name], dry=args.dry)
    document = receipt(built, digests)
    if not args.dry:
        (REPO_ROOT / RECEIPT_RELPATH).parent.mkdir(parents=True, exist_ok=True)
        (REPO_ROOT / RECEIPT_RELPATH).write_bytes(receipt_bytes(document))
    print(json.dumps({"dry": args.dry, "outputs": document["outputs"], "counts": document["counts"],
                      "statistics_sha256": document["statistics_sha256"], "pool": built["pool"],
                      "rosters": built["rosters"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
