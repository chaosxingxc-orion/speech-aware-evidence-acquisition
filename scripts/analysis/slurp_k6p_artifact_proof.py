#!/usr/bin/env python3
"""Prove that the K6p block recomputed FROM THE TWO PINNED ARTIFACTS (the centred key file and a
roster's centred query file) is the read's own K6p block, and reproduces the read's rank-1 lifts.

Proof id ``SAEA-SLURP-K6P-ARTIFACT-PROOF-V1``. Model-free: zero model, server, tokenizer, encoder,
embedder, GPU and network contacts. Uses ONLY the recall read's own functions
(``scripts/analysis/slurp_retrieval_key_recall.py``: ``key_construction``, ``centre_keys``,
``centre_queries``, ``unit_rows``, ``order_from_scores``, ``block_of``, ``rank_of``) and the
production loaders (``load_sealed_vectors`` / ``load_sealed_segment_vectors`` /
``load_sealed_agreement``). Per fold:

* ``direct``: the read's K6p (``w_agree`` 1, production admission: a facet is recalled only at a
  positive centred cosine) computed from the pinned sources exactly as the read computes it;
* ``artifact``: the same arithmetic over the two artifacts read back through the production loaders
  (cosine = dot of the unit rows the artifacts carry);
* ``cent_agree``: the flown centroid + agreement key (the read's baseline).

Gold enters only through the governed TRAIN loader and only to count ranks. Output: counts only
(rows, identical blocks, gold at block rank 1, gold in block), never an id, text or label.

    PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/slurp_k6p_artifact_proof.py --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for extra in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import numpy as np  # noqa: E402

import build_slurp_centred_centroid_key as keybuild  # noqa: E402
import build_slurp_centred_query_vectors as querybuild  # noqa: E402

PROOF_ID = "SAEA-SLURP-K6P-ARTIFACT-PROOF-V1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
#: The recall note's own counts (docs/results/2026-09-30-slurp-retrieval-key-recall-offline.md,
#: "K6p centred cosine + agreement (w 1), production admission" vs ``cent_agree``).
NOTE_RANK1 = {"fold-a": {"k6p": 845, "cent_agree": 823}, "fold-b": {"k6p": 815, "cent_agree": 789}}
NOTE_IN_BLOCK = {"fold-a": 1040, "fold-b": 1029}


def fold_counts(recall, kc, key_art: np.ndarray, q_ids: list, q_art: np.ndarray, q_raw: np.ndarray,
                share: np.ndarray, gold: dict) -> dict:
    """Counts of one fold under the three keys (pure: unit-tested on fakes)."""

    intents = kc["intents"]
    cc_dir = recall.centre_queries(q_raw, kc["mu_q"]) @ recall.centre_keys(kc["raw_means"], kc["mu_p"]).T
    cc_art = q_art @ key_art.T
    cos_c = q_raw @ kc["centroid"].T
    orders = {
        "direct": recall.order_from_scores(cc_dir + share, intents, cc_dir > 0.0),
        "artifact": recall.order_from_scores(cc_art + share, intents, cc_art > 0.0),
        "cent_agree": recall.order_from_scores(cos_c + share, intents, cos_c > 0.0),
    }
    blocks = {k: [recall.block_of(o) for o in v] for k, v in orders.items()}
    ranks = {k: [recall.rank_of(b, gold[s]) for b, s in zip(v, q_ids)] for k, v in blocks.items()}
    return {
        "rows": len(q_ids),
        "blocks_identical_artifact_vs_direct": sum(1 for a, d in zip(blocks["artifact"], blocks["direct"]) if a == d),
        "max_abs_cosine_diff_artifact_vs_direct": float(np.abs(cc_art - cc_dir).max()),
        "rank1": {k: sum(1 for r in v if r == 1) for k, v in ranks.items()},
        "gold_in_block": {k: sum(1 for r in v if r is not None) for k, v in ranks.items()},
        "rank1_lift_artifact_vs_cent_agree": (sum(1 for r in ranks["artifact"] if r == 1)
                                              - sum(1 for r in ranks["cent_agree"] if r == 1)),
    }


def run(args) -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.rails.phase_supply import (
        load_sealed_agreement, load_sealed_segment_vectors, load_sealed_vectors)

    repo, root = Path(args.repo_root), Path(args.data_root)
    recall, diag, cbuild = keybuild.recall_modules(repo)
    kc = recall.key_construction(root, diag, cbuild, centroid_pin=keybuild.CENTROID_PIN)
    intents = kc["intents"]
    idx = {x: i for i, x in enumerate(intents)}
    key_rel = f"prepared/{keybuild.ARTIFACT_ID}/{keybuild.KEY_NAME}"
    key_sha = keybuild.digest_file(root / key_rel)
    key_vecs = load_sealed_vectors(root / key_rel, expected_sha256=key_sha, dimensions=(recall.IB_DIM,))
    key_art = np.asarray([key_vecs[recall.IB_FACET_MARK + x][recall.IB_DIM] for x in intents], dtype=np.float64)
    records = load_slurp_split(load_lock(Path(args.lock)), root, "train", workers=4)
    gold = {r.sample_id: r.intent for r in records}
    del records
    out = {"proof_id": PROOF_ID, "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "gpu": 0, "network": 0},
           "key": {"relpath": key_rel, "sha256": key_sha}, "folds": {}, "note": {"rank1": NOTE_RANK1, "in_block": NOTE_IN_BLOCK}}
    for roster in args.rosters.split(","):
        cfg_rel = querybuild.ROSTERS[roster][0]
        spec = json.loads((repo / cfg_rel).read_text(encoding="utf-8"))["knowledge_stores"]["intent-boundaries"][
            "phase_supply"]["perception"]
        raw_q = load_sealed_segment_vectors(root / spec["query_source"]["relpath"],
                                            expected_sha256=spec["query_source"]["sha256"], dimensions=(recall.IB_DIM,))
        art_rel = f"prepared/{querybuild.ARTIFACT_ID}/{roster}/{querybuild.FILE_NAME}"
        art_sha = keybuild.digest_file(root / art_rel)
        art_q = load_sealed_segment_vectors(root / art_rel, expected_sha256=art_sha, dimensions=(recall.IB_DIM,))
        agr = load_sealed_agreement(root / spec["agreement_source"]["relpath"], expected_sha256=spec["agreement_source"]["sha256"],
                                    dimension="agreement:exemplar-intent", facet_ids=[recall.IB_FACET_MARK + x for x in intents])
        q_ids = sorted(raw_q)
        if sorted(art_q) != q_ids:
            raise SystemExit(f"{roster}: the artifact does not cover the pinned query ids exactly")
        q_raw = recall.unit_rows([raw_q[s].segments[0][recall.IB_DIM] for s in q_ids])
        q_art = np.asarray([art_q[s].segments[0][recall.IB_DIM] for s in q_ids], dtype=np.float64)
        share = np.zeros((len(q_ids), len(intents)))
        for i, s in enumerate(q_ids):
            for f, v in agr.get(s, {}).items():
                share[i, idx[f.split(recall.IB_FACET_MARK, 1)[-1]]] = v
        counts = fold_counts(recall, kc, key_art, q_ids, q_art, q_raw, share, gold)
        counts["artifact"] = {"relpath": art_rel, "sha256": art_sha}
        counts["reproduces_the_note"] = (
            counts["rank1"]["artifact"] == NOTE_RANK1[roster]["k6p"]
            and counts["rank1"]["cent_agree"] == NOTE_RANK1[roster]["cent_agree"]
            and counts["gold_in_block"]["artifact"] == NOTE_IN_BLOCK[roster]
            and counts["blocks_identical_artifact_vs_direct"] == counts["rows"]
        )
        out["folds"][roster] = counts
    out["ok"] = all(f["reproduces_the_note"] for f in out["folds"].values())
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--rosters", default="fold-a,fold-b")
    parser.add_argument("--write", action="store_true", help=f"write analysis/{PROOF_ID}/proof.json")
    args = parser.parse_args(argv)
    result = run(args)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.write:
        out = Path(args.data_root) / "analysis" / PROOF_ID / "proof.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        result["written"] = {"path": str(out), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
