#!/usr/bin/env python3
"""W3 offline read: tune the per-intent exemplar cap on TRAIN Fold B, estimate both W3 changes on Fold A.

Owner decision 164, knowledge-wave item W3 (intent contrast cards + a per-intent
exemplar cap). Read id ``SAEA-SLURP-W3-CONTRAST-CAP-OFFLINE-V1``.

MODEL-FREE. Zero model, server, encoder, embedder, ASR, scorer, tokenizer,
network, GPU and paid-API contacts: every similarity is float64 arithmetic over
sha256-pinned vector files the flights already sealed; gold is read offline from
the governed ``train.jsonl`` (intent label only); the AGREE arm's sealed outputs
and phase summaries are read for its chosen intent and its delivered sets.
Nothing is printed or persisted but intent ids, counts and hashes.

WHAT IT DOES.

1. Re-derives the flown Solver exemplar ranking (the ``train-exemplars`` store,
   9,354 pool values, pure cosine between the row's pinned speech vector and the
   pinned pool text vectors, facet id ascending on ties, non-positive cosines
   never recalled -- ``rails.kb_policy.multidim_recall``'s own order) and PROVES
   it before any number is used: on Fold A the top 20 equals the AGREE arm's
   sealed Solver consumption records row for row; on Fold B the top 20's intent
   shares equal the pinned Fold B agreement table row for row.
2. FOLD B TUNING (gold offline, allowed for tuning): for every cap N the rule
   ``rails.kb_policy.select_target_capped`` -- the function the registered fuser
   calls -- is applied at total 20 and the block's plurality state is compared
   with the uncapped block's: GAIN = rows whose uncapped block has a unique
   WRONG-intent plurality that the cap removes; HARM = rows whose uncapped block
   has a unique GOLD plurality that the cap removes; PRESENCE = rows with no gold
   exemplar in the uncapped 20 that gain one. THE RULE, fixed here before the
   numbers were read: N is the smallest cap whose GAIN is at least its HARM (a cap
   must not break more right majorities than wrong ones); PRESENCE breaks no tie
   because it only grows as N falls. The admission depth m (= the recall k) is
   the smallest listed depth at which the capped block fills 20 on every Fold B
   row that the uncapped block fills.
3. FOLD A ESTIMATES (counts only, never a tuning input): on the AGREE arm's 153
   intent-wrong rows, the rows where a DELIVERED card names the chosen-vs-gold
   pair before (the authored exclusion alone) and after (plus the contrast
   lines the released cards carry); the rows where the cap brings at least one
   gold-intent exemplar into the 20; and the RISK -- the AGREE arm's 927 right
   rows whose gold plurality (unique, and absolute) the cap breaks.

    python scripts/analysis/slurp_w3_contrast_cap_offline.py --data-root "$SPEECHRL_DATA_DIR" \\
        [--out docs/readiness/<package>/offline-estimates-v1.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from speech_aware_evidence_acquisition.rails.kb_policy import select_target_capped  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_agreement,
    load_sealed_vectors,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response  # noqa: E402

READ_ID = "SAEA-SLURP-W3-CONTRAST-CAP-OFFLINE-V1"
SCHEMA = "saea-slurp-w3-contrast-cap-offline-v1"
ANALYSIS_DIR = f"analysis/{READ_ID}"
TOTAL = 20
CAPS = tuple(range(1, 21))
DEPTHS = (20, 60, 100, 200, 300, 500, 1000, 2000, 9354)

PINS = {
    "pool": ("knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json",
             "4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9", "content"),
    "pool_keys": ("vectors/slurp-kus3/facet-vectors.jsonl",
                  "5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e", "file"),
    "fold_a_queries": ("vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl",
                       "d0f06ed21c6a576d8118d5a914e34807c24a3d3523d89e7b30d90575d24104ff", "file"),
    "fold_b_queries": ("vectors/slurp-stage3-filler-fold-b-v1/query-vectors-speech-content-v1.jsonl",
                       "573a8a37a63d790d6b849c11676b9463de28c92eeb92ab3e99177181a947c67f", "file"),
    "fold_b_agreement": ("prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FILLER-FOLD-B-V1/agreement.jsonl",
                         "06990a86d20469c668ac4231990b49e5926d4771c9af8fbb13ae634b3ec21911", "file"),
    "train_gold": ("datasets/slurp/metadata/train.jsonl",
                   "4a05a3de6c7f028aff298c4a90196e6a3fecd1938d96fb1c125d6fd10d5e301e", "file"),
    "base_cards": ("knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json",
                   "5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe", "content"),
}
CONTRAST_SOURCE = "prepared/SAEA-SLURP-W3-INTENT-CONTRAST-CARDS-V1/source-v1.json"
CONTRAST_RECEIPT = "docs/receipts/knowledge/slurp-intent-contrast-cards-v1.json"
AGREE = {
    "run_id": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
    "attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1",
}
ROSTERS = {"fold_a": "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
           "fold_b": "docs/receipts/rosters/slurp-evo-fold-b-v2.json"}
FOLD_B_AGREEMENT_TARGET = "intent-boundary:"
CHARS_PER_TOKEN = 5.13


class ReadError(RuntimeError):
    pass


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pinned(root: Path, key: str) -> Path:
    relpath, expected, kind = PINS[key]
    path = root / relpath
    if kind == "file" and sha_file(path) != expected:
        raise ReadError(f"{relpath} is not the pinned sha256")
    return path


def utterance(sample_id: str) -> str:
    return str(int(sample_id.split(":")[2]))


def load_gold(root: Path) -> dict[str, str]:
    gold = {}
    with pinned(root, "train_gold").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                gold[str(row["slurp_id"])] = f"{row['scenario']}_{row['action']}"
    return gold


def load_pool(root: Path) -> dict:
    snap = KnowledgeSnapshot.from_frozen_json(json.loads(pinned(root, "pool").read_text(encoding="utf-8")))
    if snap.content_hash() != PINS["pool"][1]:
        raise ReadError("the flown exemplar pool is not the pinned content hash")
    facets = sorted(value.associated_facet_ids[0] for value in snap.values)
    by_facet = {value.associated_facet_ids[0]: (value.value_id, value.task_target) for value in snap.values}
    if any(len(value.associated_facet_ids) != 1 for value in snap.values):
        raise ReadError("a pool value is not bound to exactly one facet")
    vectors = load_sealed_vectors(pinned(root, "pool_keys"), expected_sha256=PINS["pool_keys"][1],
                                  dimensions=("content",))
    matrix = np.asarray([vectors[f]["content"] for f in facets], dtype=np.float64)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    return {"facets": facets, "by_facet": by_facet, "matrix": matrix,
            "targets_by_facet": {facet: [pair] for facet, pair in by_facet.items()},
            "value_chars": {value.value_id: len(value.content) for value in snap.values},
            "value_intent": {value_id: target for value_id, target in by_facet.values()}}


def load_queries(root: Path, key: str) -> tuple[list[str], np.ndarray]:
    vectors = load_sealed_vectors(pinned(root, key), expected_sha256=PINS[key][1], dimensions=("content",))
    ids = sorted(vectors)
    matrix = np.asarray([vectors[i]["content"] for i in ids], dtype=np.float64)
    return ids, matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def rankings(pool: dict, queries: np.ndarray, depth: int) -> list[list[tuple[str, float]]]:
    """The flown recall order: cosine descending, facet id ascending, positive cosines only."""

    scores = queries @ pool["matrix"].T
    facets = pool["facets"]
    out = []
    for row in scores:
        take = min(depth, row.shape[0])
        idx = np.argpartition(-row, take - 1)[:take] if take < row.shape[0] else np.arange(row.shape[0])
        order = sorted(idx.tolist(), key=lambda j: (-row[j], facets[j]))
        out.append([(facets[j], float(row[j])) for j in order if row[j] > 0.0])
    return out


def block(ranked, pool: dict, cap: int, depth: int) -> list[str]:
    """The registered fuser's rule over the first ``depth`` admitted facets (tau 0.0: every recalled
    facet has a positive cosine, so admission is the depth alone)."""

    selected, _ = select_target_capped(
        ranked[:depth], targets_by_facet=pool["targets_by_facet"], per_target_cap=cap, total=TOTAL
    )
    return list(selected)


def intents_of(value_ids, pool: dict) -> Counter:
    return Counter(pool["value_intent"][v] for v in value_ids)


def plurality(counts: Counter, gold: str) -> str:
    if not counts:
        return "EMPTY"
    top = max(counts.values())
    tops = [intent for intent, count in counts.items() if count == top]
    if len(tops) > 1:
        return "TIE"
    return "GOLD" if tops[0] == gold else "WRONG"


def load_agree(root: Path) -> dict:
    directory = root / "runs" / AGREE["run_id"] / AGREE["attempt"]
    phases_path = directory / f"{AGREE['run_id']}.phases.json"
    outputs_path = directory / f"{AGREE['run_id']}.outputs.jsonl"
    document = json.loads(phases_path.read_text(encoding="utf-8"))
    consumption = {}
    for result in document["phases"][0]["results"]:
        exemplars, boundary = [], []
        for record in (result.get("consumption") or {}).get("records") or ():
            item = str(record.get("supplied_item_id") or "")
            item = item.split("::", 1)[1] if "::" in item else item
            if item.startswith("value:"):
                exemplars.append(item)
            elif item.startswith("intent-boundary:"):
                boundary.append(item.split("intent-boundary:", 1)[1])
        consumption[result["sample_id"]] = {"exemplars": exemplars, "boundary": boundary}
    chosen = {}
    with outputs_path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                scenario, action, _entities, parsed = parse_slu_response(record.get("text") or "")
                chosen[record["sample_id"]] = f"{scenario}_{action}" if parsed else "<unparsed>"
    return {"consumption": consumption, "chosen": chosen,
            "phases_sha256": sha_file(phases_path), "outputs_sha256": sha_file(outputs_path)}


def authored_exclusions(root: Path) -> dict[str, set[str]]:
    snap = KnowledgeSnapshot.from_frozen_json(json.loads(pinned(root, "base_cards").read_text(encoding="utf-8")))
    if snap.content_hash() != PINS["base_cards"][1]:
        raise ReadError("intent-boundaries-v1 is not the flown content hash")
    out = {}
    for value in snap.values:
        section = value.content.split("Confusable exclusions:\n", 1)[1].split("\nUncertainty behavior:", 1)[0]
        out[value.value_id.split("intent-boundary:", 1)[1]] = {
            line.split(":", 1)[0].lstrip("- ").strip() for line in section.split("\n") if line.startswith("- ")
        }
    return out


def tune(rows, gold_of, pool: dict, depth: int) -> dict:
    table = {}
    for cap in CAPS:
        gain = harm = presence = fill = changed = absolute_broken = 0
        for sample_id, ranked in rows:
            gold = gold_of(sample_id)
            before = block(ranked, pool, TOTAL, depth)
            after = block(ranked, pool, cap, depth)
            b, a = intents_of(before, pool), intents_of(after, pool)
            fill += len(after) == TOTAL
            changed += set(before) != set(after)
            state_b, state_a = plurality(b, gold), plurality(a, gold)
            gain += state_b == "WRONG" and state_a != "WRONG"
            harm += state_b == "GOLD" and state_a != "GOLD"
            presence += b[gold] == 0 and a[gold] > 0
            absolute_broken += b[gold] > TOTAL // 2 and a[gold] <= TOTAL // 2
        table[str(cap)] = {"gain_wrong_plurality_removed": gain, "harm_gold_plurality_removed": harm,
                           "net": gain - harm, "gold_presence_gained": presence,
                           "absolute_gold_majority_broken": absolute_broken,
                           "blocks_changed": changed, "blocks_filled_to_20": fill}
    return table


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")))
    parser.add_argument("--out", type=Path, default=None, help="repository copy of the counts")
    args = parser.parse_args(argv)
    root: Path = args.data_root
    if not str(root) or not root.is_dir():
        raise SystemExit("--data-root (or SPEECHRL_DATA_DIR) is required")

    gold = load_gold(root)
    pool = load_pool(root)
    rosters = {}
    for key, relpath in ROSTERS.items():
        document = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
        rosters[key] = {"ids": sorted(str(item["sample_id"]) for item in document["items"]),
                        "split_identity_hash": document["split_identity_hash"], "sha256": sha_file(REPO_ROOT / relpath)}
    pool_utterances = {value_id.split("value:", 1)[1].lstrip("0") for value_id, _ in pool["by_facet"].values()}
    for key in rosters:
        if {utterance(s) for s in rosters[key]["ids"]} & pool_utterances:
            raise ReadError(f"{key} utterances are in the flown pool; the ranking would self-retrieve")

    max_depth = max(DEPTHS)
    ids_a, q_a = load_queries(root, "fold_a_queries")
    ids_b, q_b = load_queries(root, "fold_b_queries")
    if ids_a != rosters["fold_a"]["ids"] or ids_b != rosters["fold_b"]["ids"]:
        raise ReadError("a query file does not cover its fold's roster exactly")
    ranked_a = list(zip(ids_a, rankings(pool, q_a, max_depth), strict=True))
    ranked_b = list(zip(ids_b, rankings(pool, q_b, max_depth), strict=True))
    gold_of = lambda sample_id: gold[utterance(sample_id)]  # noqa: E731

    # ---- validation before any number ------------------------------------
    agree = load_agree(root)
    fold_a_match = sum(
        set(block(r, pool, TOTAL, TOTAL)) == set(agree["consumption"][s]["exemplars"]) for s, r in ranked_a
    )
    agreement = load_sealed_agreement(
        pinned(root, "fold_b_agreement"), expected_sha256=PINS["fold_b_agreement"][1],
        dimension="agreement:exemplar-intent",
        facet_ids=sorted({FOLD_B_AGREEMENT_TARGET + t for _v, t in pool["by_facet"].values()}),
    )
    fold_b_match = 0
    for sample_id, ranked in ranked_b:
        counts = intents_of(block(ranked, pool, TOTAL, TOTAL), pool)
        mine = {FOLD_B_AGREEMENT_TARGET + t: c / TOTAL for t, c in counts.items()}
        theirs = agreement[sample_id]
        fold_b_match += set(mine) == set(theirs) and all(abs(mine[k] - theirs[k]) < 1e-12 for k in mine)
    if fold_a_match != len(ranked_a) or fold_b_match != len(ranked_b):
        raise ReadError(f"the re-derived ranking does not reproduce the sealed blocks: A {fold_a_match}, B {fold_b_match}")

    # ---- Fold B tuning ---------------------------------------------------
    tuning = tune(ranked_b, gold_of, pool, max_depth)
    cap = next(int(n) for n in sorted(tuning, key=int) if tuning[n]["net"] >= 0)
    base_fill = sum(len(block(r, pool, TOTAL, max_depth)) == TOTAL for _s, r in ranked_b)
    depth = next(
        d for d in DEPTHS if sum(len(block(r, pool, cap, d)) == TOTAL for _s, r in ranked_b) >= base_fill
    )
    depth_table = {
        str(d): {"fold_b_filled": sum(len(block(r, pool, cap, d)) == TOTAL for _s, r in ranked_b),
                 "fold_a_filled": sum(len(block(r, pool, cap, d)) == TOTAL for _s, r in ranked_a)}
        for d in DEPTHS
    }

    # ---- Fold A estimates --------------------------------------------------
    contrast_source_path = root / CONTRAST_SOURCE
    contrast = json.loads(contrast_source_path.read_text(encoding="utf-8"))
    carried = {intent: set(card["rivals_carried"]) for intent, card in contrast["cards"].items()}
    authored = authored_exclusions(root)
    wrong = [s for s, _r in ranked_a if agree["chosen"][s] != gold_of(s)]
    right = [s for s, _r in ranked_a if agree["chosen"][s] == gold_of(s)]
    ranked_by_id = dict(ranked_a)

    def named(names: dict[str, set[str]], sample_id: str, *, delivered_only: bool) -> bool:
        g, c = gold_of(sample_id), agree["chosen"][sample_id]
        delivered = set(agree["consumption"][sample_id]["boundary"])
        by_gold = c in names.get(g, set()) and (g in delivered or not delivered_only)
        by_chosen = g in names.get(c, set()) and (c in delivered or not delivered_only)
        return by_gold or by_chosen

    after_names = {i: authored.get(i, set()) | carried.get(i, set()) for i in set(authored) | set(carried)}
    both_delivered_unnamed = [
        s for s in wrong
        if {gold_of(s), agree["chosen"][s]} <= set(agree["consumption"][s]["boundary"])
        and not named(authored, s, delivered_only=True)
    ]
    contrast_table = {
        "wrong_rows": len(wrong),
        "pair_named_on_a_delivered_card_before": sum(named(authored, s, delivered_only=True) for s in wrong),
        "pair_named_on_a_delivered_card_after": sum(named(after_names, s, delivered_only=True) for s in wrong),
        "both_cards_delivered_neither_names_the_other_before": len(both_delivered_unnamed),
        "of_which_named_after": sum(named(after_names, s, delivered_only=True) for s in both_delivered_unnamed),
        "right_rows_whose_pair_with_any_delivered_rival_is_named_after": None,
    }
    contrast_table.pop("right_rows_whose_pair_with_any_delivered_rival_is_named_after")

    def cap_effect(sample_ids):
        stats = Counter()
        for s in sample_ids:
            g = gold_of(s)
            before = intents_of(block(ranked_by_id[s], pool, TOTAL, depth), pool)
            after = intents_of(block(ranked_by_id[s], pool, cap, depth), pool)
            stats["rows"] += 1
            stats["gold_zero_before"] += before[g] == 0
            stats["gold_zero_to_present"] += before[g] == 0 and after[g] > 0
            stats["gold_count_up"] += after[g] > before[g]
            stats["gold_count_down"] += after[g] < before[g]
            stats["block_changed"] += before != after
            sb, sa = plurality(before, g), plurality(after, g)
            stats[f"plurality_{sb}_to_{sa}"] += 1
            stats["unique_gold_plurality_broken"] += sb == "GOLD" and sa != "GOLD"
            stats["wrong_plurality_removed"] += sb == "WRONG" and sa != "WRONG"
            stats["absolute_gold_majority_broken"] += before[g] > TOTAL // 2 and after[g] <= TOTAL // 2
            chosen = agree["chosen"][s]
            stats["chosen_intent_majority_before"] += bool(before) and before.most_common(1)[0][0] == chosen and chosen != g
        return dict(sorted(stats.items()))

    cap_table = {"wrong_rows": cap_effect(wrong), "right_rows": cap_effect(right)}

    # ---- request-size projection (counts only) ------------------------------
    # Per Fold A row: the exact token change of the eight delivered cards (the contrast receipt's own
    # per-card counts) and the character change of the capped exemplar block, converted at the
    # measured 5.13 characters per token (docs/results/2026-09-19-slurp-m1-exemplar-compression-analysis-v1.md).
    receipt_cards = json.loads((REPO_ROOT / CONTRAST_RECEIPT).read_text(encoding="utf-8"))["cards"]
    card_delta = {i: c["tokens_rebuilt"] - c["tokens_flown"] for i, c in receipt_cards.items()}
    nets, ex_chars, card_tokens = [], [], []
    for s, ranked in ranked_a:
        before = block(ranked, pool, TOTAL, depth)
        after = block(ranked, pool, cap, depth)
        dc = sum(pool["value_chars"][v] for v in after) - sum(pool["value_chars"][v] for v in before)
        dt = sum(card_delta[i] for i in agree["consumption"][s]["boundary"])
        ex_chars.append(dc)
        card_tokens.append(dt)
        nets.append(dt + dc / CHARS_PER_TOKEN)
    projection = {
        "chars_per_token": CHARS_PER_TOKEN,
        "cards_token_delta_per_later_contact": {"min": min(card_tokens), "max": max(card_tokens),
                                                "mean": round(sum(card_tokens) / len(card_tokens), 3)},
        "exemplar_block_char_delta": {"min": min(ex_chars), "max": max(ex_chars),
                                      "mean": round(sum(ex_chars) / len(ex_chars), 3)},
        "net_token_delta_per_solver_contact": {"min": round(min(nets), 3), "max": round(max(nets), 3),
                                               "mean": round(sum(nets) / len(nets), 3),
                                               "rows_above_zero": sum(n > 0 for n in nets)},
        "note": ("the cards reach all four roles; the exemplar block reaches the Solver and every later contact. "
                 "An estimate for the realised request, beside the pre-flight check's placeholder counts."),
    }

    result = {
        "schema": SCHEMA,
        "read_id": READ_ID,
        "owner_decision": 164,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "driver": {"relpath": "scripts/analysis/slurp_w3_contrast_cap_offline.py",
                   "sha256": sha_file(Path(__file__))},
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "asr": 0, "scorer": 0,
                     "tokenizer": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "inputs": {
            **{key: {"relpath": relpath, ("sha256" if kind == "file" else "content_sha256"): expected}
               for key, (relpath, expected, kind) in PINS.items()},
            "rosters": {k: {"relpath": ROSTERS[k], "sha256": v["sha256"], "split_identity_hash": v["split_identity_hash"]}
                        for k, v in rosters.items()},
            "agree_arm": {**AGREE, "phases_sha256": agree["phases_sha256"], "outputs_sha256": agree["outputs_sha256"]},
            "contrast_source": {"relpath": CONTRAST_SOURCE, "sha256": sha_file(contrast_source_path)},
        },
        "validation": {
            "fold_a_top20_equals_agree_solver_consumption": f"{fold_a_match} of {len(ranked_a)}",
            "fold_b_top20_intent_shares_equal_pinned_agreement_table": f"{fold_b_match} of {len(ranked_b)}",
            "fold_a_wrong_rows": len(wrong), "fold_a_right_rows": len(right),
            "selection_rule": "rails.kb_policy.select_target_capped (the registered fuser's own function)",
        },
        "fold_b_tuning": {
            "rule": ("the smallest cap N whose GAIN (unique wrong-intent pluralities the cap removes) is at least its "
                     "HARM (unique gold pluralities the cap removes), over TRAIN Fold B 1,080 with gold read offline; "
                     "fixed before the table was read"),
            "table": tuning,
            "chosen_cap": cap,
            "admission_depth_rule": ("the smallest listed depth at which the capped block fills 20 on every Fold B row the "
                                     "uncapped block fills"),
            "depth_table_at_the_chosen_cap": depth_table,
            "chosen_depth": depth,
        },
        "fold_a_estimates": {
            "note": "counts only; never a tuning input; the AGREE arm's own chosen intents and delivered sets",
            "contrast_cards": contrast_table,
            "exemplar_cap": cap_table,
            "request_size_projection": projection,
        },
    }
    out_dir = root / ANALYSIS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (out_dir / "read-v1.json").write_text(payload, encoding="utf-8")
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(json.dumps({"cap": cap, "depth": depth, "validation": result["validation"],
                      "fold_b_at_cap": tuning[str(cap)], "fold_a": result["fold_a_estimates"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
