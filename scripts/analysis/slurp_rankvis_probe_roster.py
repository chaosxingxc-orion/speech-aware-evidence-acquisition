#!/usr/bin/env python3
"""Derive the roster of cell RANKVIS (owner decision 171) from the sealed AGREE error sources.

The RANKVIS conversion probe flies the AGREE arm's own bytes with ONE change
-- ``native_episode.knowledge_value_rendering`` (retrieval-rank order, rank
visible, stores ``intent-boundaries`` and ``train-exemplars``) -- on the rows
where the AGREE arm DELIVERED the gold intent's boundary entry and still
answered a wrong intent. This script derives that row set and proves it
against the committed error-source read, fail-closed:

* **Proof A (the partition reproduces).** The error-source driver
  ``scripts/analysis/slurp_agree_arm_error_sources.py`` is imported
  BYTE-UNCHANGED and its own ``load_gold`` / ``load_arm`` / ``q2_intent`` are
  called; the primary partition must reproduce the committed table of
  ``docs/results/2026-09-27-slurp-agree-arm-error-sources.md`` section 2.1
  (UNPARSED 1, CATCH-ALL 33, RETRIEVAL 25, PERCEPTION-DROP 36, SOLVER-CHOICE
  58) and the stage partition without the catch-all split (UNPARSED 1,
  RETRIEVAL 34, PERCEPTION-DROP 49, SOLVER-CHOICE 69), or the script refuses.
  The committed ``rows.jsonl`` (the perception-suspect flag ``q2_intent``
  reads) is verified by its committed content hash first.
* **Proof B (the order the probe changes).** On how many AGREE rows the
  sealed exemplar block was rendered in lexicographic key order, and on how
  many the sealed boundary block equals the rank-ordered replay (the error
  source's own structural check), so the README's statement of today's
  order is a count, not a claim.

The roster is every AGREE row whose intent is wrong and whose gold boundary
entry sits in the delivered eight: stages CONSUMPTION-PERCEPTION-DROP and
CONSUMPTION-SOLVER-CHOICE (catch-all rows included) plus the one UNPARSED row
whose gold entry was delivered. The synthesis's 89 is its subset whose
in-chain A/A answer was also wrong; it is recorded as a pre-declared sub-read.

SELECTED USING GOLD, OFFLINE -- legitimate for a CONDITIONAL rate on a TRAIN
roster and for nothing else. Gold is read on the scoring side only (the
driver's own ``data.slurp.load_slurp_split`` on the governed TRAIN split) and
never reaches a query, key, selector, config or runtime. No utterance text,
transcript, answer, gold label or filler is printed or persisted: the output
carries ids, stage names, booleans, counts and hashes.

Zero model, server, tokenizer, encoder, embedder, scorer, network and GPU
contacts. Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>/src python \\
      scripts/analysis/slurp_rankvis_probe_roster.py --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)

DERIVATION_ID = "SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-ROSTER-V1"
SCHEMA = "saea-rankvis-conversion-roster-v1"
ERROR_SOURCES = Path("scripts/analysis/slurp_agree_arm_error_sources.py")
ERROR_SOURCES_NOTE = Path("docs/results/2026-09-27-slurp-agree-arm-error-sources.md")
ROWS_RELPATH = "analysis/SAEA-SLURP-STAGE3-AGREE-ERROR-SOURCES-V1/rows.jsonl"
#: ``content-sha256.json`` of the committed read (section 5 of the note);
#: ``rows.jsonl`` carries no ``generated_at``, so its file bytes hash to it.
ROWS_CONTENT_SHA256 = "17a0be507949a3c78765729eef7f72d630389848acbf4de24f778740b8b63508"
DEFAULT_OUT = Path("docs/readiness/2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1/roster-derivation-v1.json")
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"
CARRIER_LOCK_KEY = "slurp"

PRIMARY_EXPECTED = {
    "UNPARSED": 1, "CATCH-ALL": 33, "RETRIEVAL": 25,
    "CONSUMPTION-PERCEPTION-DROP": 36, "CONSUMPTION-SOLVER-CHOICE": 58,
}
STAGE_EXPECTED = {
    "UNPARSED": 1, "RETRIEVAL": 34,
    "CONSUMPTION-PERCEPTION-DROP": 49, "CONSUMPTION-SOLVER-CHOICE": 69,
}
ROSTER_STAGES = ("CONSUMPTION-PERCEPTION-DROP", "CONSUMPTION-SOLVER-CHOICE")
#: The synthesis's count (section 4.2): 40 newly delivered + 49 delivered in both.
SYNTHESIS_SUBSET = {"rows": 89, "aa_not_delivered": 40, "aa_delivered": 49}
#: The no-op save rate by where the left arm's gold entry sat, pooled over the
#: three request-identical null pairs (A/A, PLAN, PLANr) -- the committed note's
#: section 1.1 table: a wrong row with gold at position 1 flips to correct in
#: 12 of 31 null re-flights, at 2-8 in 20 of 226. The probe's conversions are
#: read against this expectation, never against zero.
NULL_SAVE_RATE = {"1": 12 / 31, "2-8": 20 / 226}
#: One Fold A row in pp of intent accuracy (1 / 1,080), the re-declaration unit.
PP_PER_ROW = 100.0 / 1080.0


class DeriveError(RuntimeError):
    """Refuse a derivation that cannot be proven against committed bytes."""


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_module(relpath: Path, name: str):
    path = REPO_ROOT / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DeriveError(f"cannot import {relpath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, digest_file(path)


def load_entity_rows(root: Path) -> dict:
    path = root / ROWS_RELPATH
    if digest_file(path) != ROWS_CONTENT_SHA256:
        raise DeriveError(f"{ROWS_RELPATH} does not match the committed content hash")
    rows = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                rows[row["sample_id"]] = {"perception_suspect": bool(row["perception_suspect"])}
    return {"rows": rows}


def derive(args) -> dict:
    root = Path(args.data_root)
    es, es_sha = import_module(ERROR_SOURCES, "_saea_agree_error_sources")
    lock = load_lock(Path(args.lock))
    gold = es.load_gold(lock, root)
    arms = {arm["label"]: es.load_arm(root, arm, True) for arm in es.ARMS}
    ids = sorted(arms["agree"]["scores"])
    if len(ids) != es.ROWS:
        raise DeriveError(f"AGREE roster has {len(ids)} rows, expected {es.ROWS}")
    entity = load_entity_rows(root)
    if set(entity["rows"]) != set(ids):
        raise DeriveError("rows.jsonl and the AGREE roster differ")
    q2 = es.q2_intent(arms, gold, ids, {"rows": {}}, {"values": {}}, entity)

    primary = Counter(row["primary"] for row in q2.values())
    stage = Counter(row["stage"] for row in q2.values())
    differences = []
    for label, expected, observed in (("primary", PRIMARY_EXPECTED, primary), ("stage", STAGE_EXPECTED, stage)):
        if dict(observed) != expected:
            differences.append(f"{label}: expected {expected}, observed {dict(sorted(observed.items()))}")
    if differences:
        raise DeriveError("proof A: the partition does not reproduce the committed note: " + "; ".join(differences))

    roster = sorted(
        sid for sid, row in q2.items()
        if row["stage"] in ROSTER_STAGES or (row["stage"] == "UNPARSED" and row["gold_pos"] is not None)
    )
    per_row = []
    subset = []
    aa_not_delivered = aa_delivered = 0
    for sid in roster:
        aa_facts = es.row_facts(sid, arms["aa"], gold[sid])
        aa_correct = bool(aa_facts["correct"])
        aa_gold_delivered = aa_facts["gold_pos"] is not None
        if not aa_correct:
            subset.append(sid)
            if aa_gold_delivered:
                aa_delivered += 1
            else:
                aa_not_delivered += 1
        gold_band = "1" if q2[sid]["gold_pos"] == 1 else "2-8"
        per_row.append({
            "sample_id": sid, "stage": q2[sid]["stage"], "primary": q2[sid]["primary"],
            "agree_gold_position_band": gold_band,
            "catch_all_flagged": bool(q2[sid]["catch_all"]),
            "aa_correct": aa_correct, "aa_gold_delivered": aa_gold_delivered,
            "in_synthesis_subset": not aa_correct,
        })

    # Proof B: today's order, counted on the sealed AGREE phases.
    lexicographic = sum(
        1 for sid in ids
        if list(arms["agree"]["phases"][sid]["ex_rendered"]) == sorted(arms["agree"]["phases"][sid]["ex_rendered"])
    )
    exemplar_rows = sum(1 for sid in ids if len(arms["agree"]["phases"][sid]["ex_rendered"]) >= 2)

    manifest = json.loads((REPO_ROOT / "configs" / "dataset" / f"{DATASET_FRAGMENT}.json").read_text(encoding="utf-8"))
    in_fragment = {str(item["sample_id"]) for item in manifest["items"]}
    missing = [sid for sid in roster if sid not in in_fragment]
    if missing:
        raise DeriveError(f"{len(missing)} roster id(s) are not in {DATASET_FRAGMENT}")

    id_list_sha256 = hashlib.sha256("\n".join(roster).encode("utf-8")).hexdigest()
    return {
        "schema": SCHEMA, "derivation_id": DERIVATION_ID,
        "authority": "owner decision 171 (2026-09-27)",
        "driver": {"relpath": str(ERROR_SOURCES), "sha256": es_sha, "imported_unchanged": True},
        "note": {"relpath": str(ERROR_SOURCES_NOTE), "sha256": digest_file(REPO_ROOT / ERROR_SOURCES_NOTE)},
        "inputs": {
            label: {"run_id": arm["run_id"], "attempt": arm["attempt"],
                    "phases_sha256": arm["phases_sha256"], "outputs_sha256": arm["outputs_sha256"],
                    "scores_sha256": arm["scores_sha256"]}
            for label, arm in arms.items()
        } | {"error_source_rows": {"relpath": ROWS_RELPATH, "sha256": ROWS_CONTENT_SHA256}},
        "proof_a_partition_reproduced": {
            "primary": dict(sorted(primary.items())), "stage": dict(sorted(stage.items())),
            "differences": [],
        },
        "proof_b_todays_order": {
            "agree_rows": len(ids),
            "rows_with_two_or_more_rendered_exemplars": exemplar_rows,
            "rows_whose_rendered_exemplar_keys_are_in_lexicographic_order": lexicographic,
            "boundary_block_equals_rank_ordered_replay": (
                "1080/1080 per the committed note section 0 (agree_replay_top8_equals_sealed_block); "
                "the associated-values fuser traverses the ranked facets in rank order, so the "
                "boundary block is ALREADY rank-ordered and only its rank is invisible"
            ),
        },
        "roster": {
            "definition": (
                "AGREE Fold A rows whose intent is wrong and whose gold intent-boundary entry is "
                f"among the eight delivered: stages {list(ROSTER_STAGES)} (catch-all rows "
                "included) plus the UNPARSED row(s) whose gold entry was delivered"
            ),
            "rows": len(roster),
            "by_stage": dict(sorted(Counter(r["stage"] for r in per_row).items())),
            "by_primary": dict(sorted(Counter(r["primary"] for r in per_row).items())),
            "ids": roster,
            "id_list_sha256": id_list_sha256,
            "split_identity_hash": split_identity_hash(prefixed(CARRIER_LOCK_KEY, roster)),
            "split_identity_convention": (
                "data.splits.split_identity_hash over the LF-joined sorted carrier-prefixed ids "
                "f'slurp/{sample_id}'"
            ),
            "dataset_fragment": DATASET_FRAGMENT,
            "per_row": per_row,
        },
        "synthesis_subset": {
            "definition": "roster rows whose in-chain A/A (w_agree 0.0) answer was ALSO intent-wrong",
            "rows": len(subset),
            "aa_gold_not_delivered": aa_not_delivered,
            "aa_gold_delivered": aa_delivered,
            "synthesis_expected": SYNTHESIS_SUBSET,
            "matches_synthesis": (
                len(subset) == SYNTHESIS_SUBSET["rows"]
                and aa_not_delivered == SYNTHESIS_SUBSET["aa_not_delivered"]
                and aa_delivered == SYNTHESIS_SUBSET["aa_delivered"]
            ),
            "id_list_sha256": hashlib.sha256("\n".join(subset).encode("utf-8")).hexdigest(),
        },
        "no_op_expectation": {
            "definition": (
                "expected wrong-to-correct flips on this roster under a request-identical re-flight "
                "of the AGREE bytes: sum over rows of the committed null save rate of the row's "
                "AGREE gold-position band (note section 1.1, pooled over three null pairs)"
            ),
            "null_save_rate": NULL_SAVE_RATE,
            "rows_by_band": dict(sorted(Counter(r["agree_gold_position_band"] for r in per_row).items())),
            "expected_null_conversions": sum(NULL_SAVE_RATE[r["agree_gold_position_band"]] for r in per_row),
            "expected_null_conversions_synthesis_subset": sum(
                NULL_SAVE_RATE[r["agree_gold_position_band"]] for r in per_row if r["in_synthesis_subset"]
            ),
        },
        "re_declaration_unit_pp_per_row": PP_PER_ROW,
        "gold_selection": "SELECTED USING GOLD, OFFLINE: conditional estimate only, no pooled or roster-level claim",
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                     "scorer": 0, "network": 0, "gpu": 0},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock", default="/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)
    document = derive(args)
    out = Path(args.out)
    if not out.is_absolute():
        out = REPO_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "rows": document["roster"]["rows"], "by_stage": document["roster"]["by_stage"],
        "synthesis_subset": {k: document["synthesis_subset"][k]
                             for k in ("rows", "aa_gold_not_delivered", "aa_gold_delivered", "matches_synthesis")},
        "proof_b": document["proof_b_todays_order"]["rows_whose_rendered_exemplar_keys_are_in_lexicographic_order"],
        "no_op_expectation": {k: document["no_op_expectation"][k] for k in
                              ("rows_by_band", "expected_null_conversions", "expected_null_conversions_synthesis_subset")},
        "split_identity_hash": document["roster"]["split_identity_hash"],
        "out_sha256": digest_file(out),
    }, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
