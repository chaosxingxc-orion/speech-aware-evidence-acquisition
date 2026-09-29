#!/usr/bin/env python3
"""Build the do-not-tag SCOPE-RULE table (evidence-consumption module, migration step 3).

Owner decision 195 (option B): the do-not-tag scope rule enters the composed policy as a USE-layer
deterministic node action. Design ``docs/superpowers/specs/2026-09-29-slurp-consumption-module-
design.md`` sections 2.2 (d), 2.3 and 4 (step 3); coordinator ruling R5: the table is built from
TRAIN minus Fold A, minus Fold B (rollout-exposed, decision 186) and minus R01/R01C -- exactly the
contrast-pair table's exclusions -- and registered with a receipt like
``SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V2``.

WHAT IT BUILDS. A pinned, model-free lookup table,
``prepared/SAEA-SLURP-SCOPE-RULE-TABLE-V1/table-v1.json``: for every word n-gram (n <= 8) that
occurs in at least :data:`MIN_POOL_OCCURRENCES_FLOOR` pool exemplars, the pair
``[pool occurrences, tagged occurrences]`` -- an exemplar counted once per n-gram, "tagged" when
the n-gram lies inside one of that exemplar's own annotated slot fillers. The runtime stage
``saea-deliver-scope-rule-v1`` (``rails.delivery_normalisers``) reads it: a delivered entity whose
folded phrase occurs in >= 5 pool exemplars and is untagged in >= 80 % of them is dropped.

THE RULE, REUSED VERBATIM. The counting (``ngrams``, ``scope_counts``, ``MAX_NGRAM``,
``SCOPE_MIN_OCC``) is imported from ``scripts/analysis/slurp_slu_consumption_headroom.py`` -- the
offline read that measured the rule (+1.04 [+0.53, +1.57] pp SLU-F1 on the AGREE arm) -- and the
exemplar parse (folded utterance, folded fillers) is that read's own
``load_exemplar_pool`` (``scripts/analysis/slurp_gold_position_and_solver_freedom_read.py``). The
ONE difference is the pool: the offline read counted over ``size-pool-annotated-exemplars``
(9,354 utterances, TRAIN minus Fold A, which still holds the 800 R01 utterances); this table counts
over ``size-pool-annotated-exemplars-minus-r01`` (8,554 utterances), the SAME pool, content pin and
forbidden-roster disjointness check the contrast-pair tables use, extended by the R01C roster
(a subset of R01, checked here anyway so the exclusion is proven rather than inferred).

BOUNDARY. Model-free: zero model, server, encoder, embedder, tokenizer, ASR, scorer, network, GPU
and paid-API contact. TRAIN construction text only; no evaluated row's gold is read. Writes only
under the data root (write-once) and the repository receipt, which carries counts and hashes only
-- never a phrase, an utterance or a filler.

    python scripts/build_slurp_scope_rule_table.py --data-root "$SPEECHRL_DATA_DIR" --dry
    python scripts/build_slurp_scope_rule_table.py --data-root "$SPEECHRL_DATA_DIR"
    python scripts/build_slurp_scope_rule_table.py --data-root "$SPEECHRL_DATA_DIR" --check
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

ARTIFACT_ID = "SAEA-SLURP-SCOPE-RULE-TABLE-V1"
LEDGER_ROW = "SAEA-SLURP-SCOPE-RULE-TABLE-BUILD-V1"
BUILDER_ID = "saea-slurp-scope-rule-table-v1"
TABLE_SCHEMA = "saea-slurp-scope-rule-table-v1"
RECEIPT_SCHEMA = "saea-slurp-scope-rule-table-receipt-v1"
TABLE_RELPATH = f"prepared/{ARTIFACT_ID}/table-v1.json"
RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-scope-rule-table-v1.json"
#: R5's exclusions beyond the contrast-pair tables' three rosters: R01C (a subset of R01).
EXTRA_FORBIDDEN_ROSTERS = ("docs/receipts/rosters/slurp-stage3-construction-r01c.json",)
#: The rule's registered thresholds (fixed by the offline read before its first run).
DEFAULT_UNTAGGED_SHARE = 0.8


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


HR = import_path(REPO_ROOT / "scripts/analysis/slurp_slu_consumption_headroom.py", "slurp_slu_consumption_headroom")
MIN_POOL_OCCURRENCES_FLOOR = HR.SCOPE_MIN_OCC
MAX_NGRAM = HR.MAX_NGRAM
#: The contrast-card builder: the pool pin, its loader and the forbidden rosters (R5).
W3A = import_path(REPO_ROOT / "scripts/build_slurp_intent_contrast_cards.py", "build_slurp_intent_contrast_cards")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def table_bytes(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def receipt_bytes(document: dict) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def table_rows(exemplars: list, *, floor: int = MIN_POOL_OCCURRENCES_FLOOR) -> dict[str, list[int]]:
    """``{phrase: [pool occurrences, tagged occurrences]}`` for every n-gram occurring in at least
    ``floor`` exemplars. ``exemplars``: ``[(utterance tokens, [filler token lists])]``, folded. The
    phrase key is the space-joined token tuple, so ``key.split()`` is the offline read's tuple."""

    occ, tagged = HR.scope_counts(exemplars)
    return {" ".join(phrase): [n, min(tagged.get(phrase, 0), n)] for phrase, n in occ.items() if n >= floor}


def rule_hits(rows: dict[str, list[int]], *, min_occurrences: int, untagged_share: float) -> int:
    """How many table phrases the rule would drop (a count only; phrases stay in-process)."""

    hits = 0
    for n, t in rows.values():
        if n >= min_occurrences and 1.0 - t / n >= untagged_share:
            hits += 1
    return hits


def forbidden_rosters() -> tuple[str, ...]:
    return (*W3A.FORBIDDEN_ROSTERS, *EXTRA_FORBIDDEN_ROSTERS)


def build(root: Path) -> dict:
    w3a = W3A
    gp = import_path(
        REPO_ROOT / "scripts/analysis/slurp_gold_position_and_solver_freedom_read.py",
        "slurp_gold_position_and_solver_freedom_read",
    )
    pool_relpath, pool_content_sha = w3a.POOL
    pinned = w3a.load_pool(root)  # verifies the pinned content hash; the utterance set for disjointness
    per_roster = {}
    for relpath in forbidden_rosters():
        roster = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
        ids = {":".join(str(item["sample_id"]).split(":")[:3]) for item in roster["items"]}
        overlap = len(pinned["utterances"] & ids)
        if overlap:
            raise BuildError(f"the construction pool intersects {relpath} on {overlap} utterances")
        per_roster[relpath] = {"sha256": sha_file(REPO_ROOT / relpath), "utterances": len(ids), "overlap": 0}
    pool = gp.load_exemplar_pool(root, pool_relpath)
    if pool["content_sha256"] != pool_content_sha:
        raise BuildError("the parsed pool's snapshot_sha256 is not the pinned content hash")
    exemplars = [
        (value["utterance"].split(), [f.split() for fillers in value["fillers"].values() for f in fillers])
        for _key, value in sorted(pool["values"].items())
    ]
    if len(exemplars) != len(pinned["utterances"]):
        raise BuildError("one exemplar per pool utterance expected")
    rows = table_rows(exemplars)
    document = {
        "schema": TABLE_SCHEMA,
        "artifact_id": ARTIFACT_ID,
        "builder_id": BUILDER_ID,
        "construction_pool": {"relpath": pool_relpath, "content_sha256": pool_content_sha},
        "exemplars": len(exemplars),
        "max_ngram": MAX_NGRAM,
        "min_pool_occurrences_floor": MIN_POOL_OCCURRENCES_FLOOR,
        "phrase_key": "space-joined tokens of analysis.sealed_credit.entity_states.fold(text)",
        "rows": dict(sorted(rows.items())),
    }
    by_n = Counter(len(key.split()) for key in rows)
    return {
        "document": document,
        "pool": {"relpath": pool_relpath, "content_sha256": pool_content_sha, "file_sha256": pool["sha256"],
                 "utterances": len(pinned["utterances"]), "exemplars": len(exemplars)},
        "rosters": per_roster,
        "phrases_by_ngram_length": {str(n): by_n[n] for n in sorted(by_n)},
        "rule_hits": rule_hits(rows, min_occurrences=MIN_POOL_OCCURRENCES_FLOOR, untagged_share=DEFAULT_UNTAGGED_SHARE),
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


def receipt(built: dict, table_sha: str) -> dict:
    return {
        "schema": RECEIPT_SCHEMA,
        "artifact_id": ARTIFACT_ID,
        "builder_id": BUILDER_ID,
        "exposure_ledger_row": LEDGER_ROW,
        "builder": {"relpath": "scripts/build_slurp_scope_rule_table.py", "sha256": sha_file(Path(__file__))},
        "boundary": "No phrase, utterance, filler or card text appears in this receipt: counts and hashes only.",
        "contacts": {k: 0 for k in ("asr", "embedder", "encoder", "gpu", "model", "network", "paid_api",
                                    "scorer", "server", "tokenizer")},
        "inputs": {"construction_pool": built["pool"], "forbidden_rosters": built["rosters"]},
        "method": {
            "rule": "drop a delivered entity whose folded phrase occurs in >= min_pool_occurrences pool "
                    "exemplars and is untagged in >= untagged_share of them",
            "reused_from": "scripts/analysis/slurp_slu_consumption_headroom.py (ngrams, scope_counts, "
                           "SCOPE_MIN_OCC, MAX_NGRAM); exemplar parse load_exemplar_pool of "
                           "scripts/analysis/slurp_gold_position_and_solver_freedom_read.py",
            "max_ngram": MAX_NGRAM,
            "min_pool_occurrences_floor": MIN_POOL_OCCURRENCES_FLOOR,
            "registered_thresholds": {"min_pool_occurrences": MIN_POOL_OCCURRENCES_FLOOR,
                                      "untagged_share": DEFAULT_UNTAGGED_SHARE},
            "roster_ruling": "R5: TRAIN minus Fold A, minus Fold B, minus R01/R01C (the contrast-pair "
                             "tables' exclusions plus R01C)",
        },
        "counts": {
            "phrases_in_table": len(built["document"]["rows"]),
            "phrases_by_ngram_length": built["phrases_by_ngram_length"],
            "phrases_the_registered_rule_drops": built["rule_hits"],
        },
        "output": {"relpath": TABLE_RELPATH, "sha256": table_sha},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry", action="store_true", help="build and measure, write nothing")
    mode.add_argument("--check", action="store_true", help="rebuild and compare with the written table")
    args = parser.parse_args(argv)
    root: Path = args.data_root
    if not str(root) or not root.is_dir():
        raise SystemExit("--data-root (or SPEECHRL_DATA_DIR) is required")
    built = build(root)
    data = table_bytes(built["document"])
    if args.check:
        written = root / TABLE_RELPATH
        same = written.is_file() and sha_file(written) == sha_bytes(data)
        pinned = json.loads((REPO_ROOT / RECEIPT_RELPATH).read_text(encoding="utf-8"))["output"]["sha256"]
        print(json.dumps({"table_identical": same, "receipt_pin_identical": pinned == sha_bytes(data),
                          "sha256": sha_bytes(data)}, indent=2))
        return 0 if same and pinned == sha_bytes(data) else 1
    table_sha = write_once(root / TABLE_RELPATH, data, dry=args.dry)
    document = receipt(built, table_sha)
    if not args.dry:
        (REPO_ROOT / RECEIPT_RELPATH).parent.mkdir(parents=True, exist_ok=True)
        (REPO_ROOT / RECEIPT_RELPATH).write_bytes(receipt_bytes(document))
    print(json.dumps({"dry": args.dry, "output": document["output"], "counts": document["counts"],
                      "pool": built["pool"], "rosters": built["rosters"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
