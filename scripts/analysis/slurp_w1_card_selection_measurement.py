#!/usr/bin/env python3
"""W1 card selection, measured offline on the sealed AGREE arm before any contact.

Owner decision 164 (2026-09-27): W1 sends the Solver only the slot-contract cards for
slot types legal under the row's candidate intents, the legality table built from the
released TRAIN exemplar store alone (``scripts/build_slurp_intent_slot_legality.py``).
This script answers the two numbers the registration needs:

1. **What W1 saves.** For every one of the 1,080 TRAIN Fold A rows of the sealed AGREE arm
   (``SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1``), the row's own sealed Perception shortlist is
   re-projected exactly as the flown route read it, the flown card selection is REPLAYED
   through the repository's own ``select_candidate_semantic_values`` over the authored index
   and must reproduce the sealed selection on every row, and then the same selection is
   taken over the NARROWED index (``rails.candidate_semantic_supply.released_candidate_index``
   with the pinned legality source). The difference is priced in exact tokens of each card's
   rendered evidence block (the local vocab-only ``llama-tokenize`` over the pinned GGUF
   vocab; one process per distinct card text), per Solver contact and per row over every
   contact after Perception that renders the block.
2. **What W1 risks.** Offline only, never printed beyond ids, counts and type names: on how
   many rows a card for a GOLD slot type was offered by the flown selection and would be
   dropped by W1 -- the harm mode "gold type not legal under any shortlisted intent" -- and
   how many of those gold items the AGREE arm delivered exactly right. The error-source
   analysis's per-row items are cross-tabulated beside it.

It also reports the pre-flight static bound (``core.flight.runtime`` candidate-route volume)
before and after, in UTF-8 bytes, and a sensitivity grid over the rule's one parameter.

ZERO model, server, encoder, embedder, scorer, network, GPU and paid-API contacts; the only
process is the vocab-only tokenizer. Gold (governed ``train.jsonl``) is read for Fold A rows
only and only into counts; no utterance text, filler or delivered answer is persisted.

    python scripts/analysis/slurp_w1_card_selection_measurement.py --data-root "$SPEECHRL_DATA_DIR" \\
        --out docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1/card-selection-measurement-v1.json
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import statistics
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails.candidate_semantic_supply import (  # noqa: E402
    load_sealed_slot_legality,
    max_candidate_selection_value_ids,
    narrow_candidate_index,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    AgentStateArtifact,
    KnowledgeSnapshot,
)
from speech_aware_evidence_acquisition.rails.knowledge_provider import (  # noqa: E402
    select_candidate_semantic_values,
)
from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (  # noqa: E402
    parse_slurp_intent_hypothesis_state,
)

SCHEMA = "saea-w1-card-selection-measurement-v1"
RUN_ID = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
ATTEMPT = "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"
ANALYSIS_DIR = "analysis/SAEA-SLURP-W1-CARD-SELECTION-MEASUREMENT-V1"
ERRSRC_ROWS = "analysis/SAEA-SLURP-STAGE3-AGREE-ERROR-SOURCES-V1/rows.jsonl"
LEGALITY = {
    "kind": "sealed-intent-slot-legality",
    "relpath": "prepared/SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1/legality.json",
    "sha256": "59b507b4e36970d4328b3442a31c790c2be48e2e47f4247bd3764bf2fddd1bad",
    "tool_contact_ledger_row": "SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1",
    "embedded_signal": "measurement only",
}
AUTHORED_RELPATH = "prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/authored-slot-contracts-v1.json"
AUTHORED_SHA256 = "34f6c3dc192eca4a30ef7208d10c1e2b797a0ae2ffe5122f16b376e10a30e4c5"
SLOT_SNAPSHOT = "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json"
SLOT_CONTENT_HASH = "d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec"
POOL_SNAPSHOT = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
TRAIN_GOLD = "datasets/slurp/metadata/train.jsonl"
TRAIN_GOLD_SHA = "4a05a3de6c7f028aff298c4a90196e6a3fecd1938d96fb1c125d6fd10d5e301e"
GGUF = "models/qwen3-omni-30b-a3b-instruct-gguf-q4km/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf"
TOKENIZE = Path("/home/chao/llama.cpp/build/bin/llama-tokenize")
STORE_ID = "slot-contracts"
PROJECTION = "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
MAX_CANDIDATES, PER_CANDIDATE, TOTAL = 3, 16, 28
ROWS = 1080


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rendered_block(value_id: str, content: str) -> str:
    """The model-facing evidence block (``core.flight.runtime`` and
    ``KnowledgeStoreBinding.model_evidence_block``)."""

    return f"[evidence {STORE_ID}::{value_id}] [knowledge store={STORE_ID} role={STORE_ID}] {content}"


class Tokenizer:
    def __init__(self, model: Path) -> None:
        self.model, self.invocations, self.cache = model, 0, {}

    def count(self, text: str) -> int:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key not in self.cache:
            with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as handle:
                handle.write(text.encode("utf-8"))
                path = handle.name
            argv = [str(TOKENIZE), "-m", str(self.model), "-f", path, "--no-bos", "--no-escape",
                    "--show-count", "--log-disable", "--ids"]
            result = subprocess.run(argv, check=True, capture_output=True, text=True)
            Path(path).unlink()
            self.invocations += 1
            counts = [int(line.split(":")[1]) for line in result.stdout.splitlines()
                      if line.startswith("Total number of tokens:")]
            if len(counts) != 1:
                raise RuntimeError("the local tokenizer produced no count")
            self.cache[key] = counts[0]
        return self.cache[key]


def authored_index(data_root: Path) -> dict[str, tuple[str, ...]]:
    path = data_root / AUTHORED_RELPATH
    if sha_file(path) != AUTHORED_SHA256:
        raise SystemExit("the authored slot-contract source is not the pinned file")
    index: dict[str, list[str]] = defaultdict(list)
    for row in json.loads(path.read_text(encoding="utf-8"))["rows"]:
        for binding in row["intent_bindings"]:
            index[binding["intent_id"]].append(f"slot-contract:{row['slot_id']}")
    return {intent: tuple(sorted(values)) for intent, values in index.items()}


def pool_support(data_root: Path) -> dict[tuple[str, str], int]:
    """(intent, slot type) -> distinct pool utterances, for the sensitivity grid only."""

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from build_slurp_intent_slot_legality import annotation_types, utterance_of  # noqa: PLC0415

    snapshot = KnowledgeSnapshot.from_frozen_json(json.loads((data_root / POOL_SNAPSHOT).read_text(encoding="utf-8")))
    support: dict[tuple[str, str], set[str]] = defaultdict(set)
    for value in snapshot.values:
        utt = utterance_of(value.source_sample_ids[0])
        for slot_type in set(annotation_types(value.content)):
            support[(value.task_target, slot_type)].add(utt)
    return {pair: len(utts) for pair, utts in support.items()}


def load_gold(data_root: Path, utterances: set[str]) -> dict[str, dict]:
    path = data_root / TRAIN_GOLD
    if sha_file(path) != TRAIN_GOLD_SHA:
        raise SystemExit("governed train.jsonl is not the pinned file")
    out = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = json.loads(line)
            if str(raw["slurp_id"]) not in utterances:
                continue
            tokens = {token["id"]: token["surface"] for token in raw["tokens"]}
            entities = []
            for entity in raw["entities"]:
                filler = " ".join(tokens[i] for i in entity["span"]).lower()
                entities.append((entity["type"], filler))
            out[str(raw["slurp_id"])] = {"intent": f"{raw['scenario']}_{raw['action']}", "entities": entities}
    return out


def distribution(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "mean": round(statistics.fmean(ordered), 3),
        "median": ordered[len(ordered) // 2],
        "p95": ordered[int(0.95 * (len(ordered) - 1))],
        "max": ordered[-1],
        "min": ordered[0],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--out", required=True, help="repository-relative package receipt path")
    args = parser.parse_args(argv)
    data_root = args.data_root
    support = pool_support(data_root)

    snapshot = KnowledgeSnapshot.from_frozen_json(json.loads((data_root / SLOT_SNAPSHOT).read_text(encoding="utf-8")))
    if snapshot.content_hash() != SLOT_CONTENT_HASH:
        raise SystemExit("slot-contracts snapshot is not the flown pin")
    blocks = {value.value_id: rendered_block(value.value_id, value.content) for value in snapshot.values}
    tokenizer = Tokenizer(data_root / GGUF)
    tokens = {value_id: tokenizer.count(text) for value_id, text in sorted(blocks.items())}
    utf8 = {value_id: len(text.encode("utf-8")) for value_id, text in blocks.items()}

    authored = authored_index(data_root)
    legal_ids = sorted({v.task_target for v in KnowledgeSnapshot.from_frozen_json(
        json.loads((data_root / POOL_SNAPSHOT).read_text(encoding="utf-8"))).values})
    legality = load_sealed_slot_legality(LEGALITY, data_root)
    narrowed = narrow_candidate_index(authored, legality, legal_candidate_ids=legal_ids)

    run_dir = data_root / "runs" / RUN_ID / ATTEMPT
    phases_path = run_dir / f"{RUN_ID}.phases.json"
    phases = json.loads(phases_path.read_text(encoding="utf-8"))
    results = phases["phases"][0]["results"]
    if len(results) != ROWS:
        raise SystemExit("the sealed arm does not carry 1,080 rows")
    errsrc_path = data_root / ERRSRC_ROWS
    errsrc = {}
    with errsrc_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            errsrc[record["sample_id"]] = record
    utterances = {result["sample_id"].split(":")[2].lstrip("0") or "0" for result in results}
    gold = load_gold(data_root, utterances)

    rows = []
    for result in results:
        sample_id = result["sample_id"]
        state = [s for s in result["agent_states"] if s["state_kind"] == "phase:perception"]
        if len(state) != 1:
            raise SystemExit(f"{sample_id}: not exactly one Perception state")
        artifact = AgentStateArtifact(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in state[0].items()})
        parsed = parse_slurp_intent_hypothesis_state(
            artifact, expected_sample_id=sample_id, legal_intent_ids=legal_ids,
            max_candidates=MAX_CANDIDATES, compact_source_phase="perception", projection_policy=PROJECTION,
        )
        candidates = tuple(item.intent_id for item in parsed.candidates)
        flown = [x.split("::", 1)[1] for x in result["final_query_state"]["retrieved_value_ids"] if x.startswith(f"{STORE_ID}::")]
        base, _ = select_candidate_semantic_values(candidates, authored, max_values_per_candidate=PER_CANDIDATE, max_total_values=TOTAL)
        w1, _ = select_candidate_semantic_values(candidates, narrowed, max_values_per_candidate=PER_CANDIDATE, max_total_values=TOTAL)
        if list(base) != flown:
            raise SystemExit(f"{sample_id}: the replayed flown selection differs from the sealed one")
        roles = [contact["plan"]["contact_id"].split(":")[1] for contact in result["contacts"]]
        g = gold[sample_id.split(":")[2].lstrip("0") or "0"]
        try:
            answer = json.loads(result["final_response_text"])
            delivered = [(e["type"], str(e.get("filler", "")).lower()) for e in answer.get("entities", [])]
        except (json.JSONDecodeError, TypeError, AttributeError):
            delivered = []
        rows.append({"sample_id": sample_id, "candidates": candidates, "base": list(base), "w1": list(w1),
                     "roles": roles, "gold": g, "delivered": delivered})

    # ---- savings ---------------------------------------------------------
    def price(selection):
        return sum(tokens[v] for v in selection), sum(utf8[v] for v in selection)

    per_solver_saved, per_row_saved, cards_base, cards_w1, tok_base, tok_w1 = [], [], [], [], [], []
    rows_changed = 0
    for row in rows:
        tb, _ = price(row["base"])
        tw, _ = price(row["w1"])
        carrying = sum(1 for role in row["roles"] if role != "perception")
        per_solver_saved.append(tb - tw)
        per_row_saved.append((tb - tw) * carrying)
        cards_base.append(len(row["base"]))
        cards_w1.append(len(row["w1"]))
        tok_base.append(tb)
        tok_w1.append(tw)
        rows_changed += set(row["w1"]) != set(row["base"])
        if not set(row["w1"]) <= set(row["base"]):
            raise SystemExit(f"{row['sample_id']}: W1 offered a card the flown selection did not")
    role_counts = Counter(role for row in rows for role in row["roles"])

    # ---- harm ------------------------------------------------------------
    harm = []
    at_risk_correct_items = 0
    gold_rows = sum(1 for row in rows if row["gold"]["entities"])
    base_cover = w1_cover = 0
    delivered_type_dropped_rows = 0
    for row in rows:
        gold_types = {t for t, _ in row["gold"]["entities"]}
        base_types = {v.split(":", 1)[1] for v in row["base"]}
        w1_types = {v.split(":", 1)[1] for v in row["w1"]}
        if gold_types:
            base_cover += gold_types <= base_types
            w1_cover += gold_types <= w1_types
        if {t for t, _ in row["delivered"]} & (base_types - w1_types):
            delivered_type_dropped_rows += 1
        lost = sorted((gold_types & base_types) - w1_types)
        if not lost:
            continue
        delivered = Counter(row["delivered"])
        items = []
        for slot_type in lost:
            for entity in row["gold"]["entities"]:
                if entity[0] != slot_type:
                    continue
                correct = delivered[entity] > 0
                if correct:
                    delivered[entity] -= 1
                    at_risk_correct_items += 1
                items.append({"slot_type": slot_type, "delivered_exactly_right_by_agree": correct})
        gold_intent = row["gold"]["intent"]
        err = errsrc.get(row["sample_id"], {})
        harm.append({
            "sample_id": row["sample_id"],
            "lost_gold_slot_types": lost,
            "gold_items_of_lost_types": items,
            "gold_intent_position_in_shortlist": (row["candidates"].index(gold_intent) + 1) if gold_intent in row["candidates"] else None,
            "shortlist_width": len(row["candidates"]),
            "lost_type_support_under_gold_intent": {t: support.get((gold_intent, t), 0) for t in lost},
            "error_source_items_of_lost_types": [
                {"kind": item.get("kind"), "sub": item.get("sub")}
                for item in err.get("entity_items", []) if item.get("type") in lost
            ],
        })

    # ---- static bound (pre-flight) --------------------------------------
    global_bound = sorted(utf8.values(), reverse=True)[:TOTAL]
    narrowed_ids = max_candidate_selection_value_ids(narrowed, weight=utf8, max_candidates=MAX_CANDIDATES, max_total_values=TOTAL)
    authored_ids = max_candidate_selection_value_ids(authored, weight=utf8, max_candidates=MAX_CANDIDATES, max_total_values=TOTAL)

    # ---- sensitivity grid (the rule's one parameter) ---------------------
    grid = []
    for min_support in (1, 2, 3, 5):
        table: dict[str, frozenset[str]] = defaultdict(frozenset)
        kept: dict[str, set[str]] = defaultdict(set)
        for (intent, slot_type), n in support.items():
            if n >= min_support and f"slot-contract:{slot_type}" in authored.get(intent, ()):
                kept[intent].add(slot_type)
        table = {intent: frozenset(types) for intent, types in kept.items()}
        index = narrow_candidate_index(authored, table, legal_candidate_ids=legal_ids)
        saved, harmed_rows, harmed_items = [], 0, 0
        for row in rows:
            sel, _ = select_candidate_semantic_values(row["candidates"], index, max_values_per_candidate=PER_CANDIDATE, max_total_values=TOTAL)
            saved.append(price(row["base"])[0] - price(sel)[0])
            lost = ({t for t, _ in row["gold"]["entities"]} & {v.split(":", 1)[1] for v in row["base"]}) - {v.split(":", 1)[1] for v in sel}
            harmed_rows += bool(lost)
            harmed_items += sum(1 for t, _ in row["gold"]["entities"] if t in lost)
        grid.append({"min_support_utterances": min_support, "pairs_kept": sum(len(v) for v in table.values()),
                     "tokens_saved_per_solver_contact_mean": round(statistics.fmean(saved), 1),
                     "rows_losing_a_gold_type_card": harmed_rows, "gold_items_of_lost_types": harmed_items})

    payload = {
        "schema": SCHEMA,
        "read_id": "SAEA-SLURP-W1-CARD-SELECTION-MEASUREMENT-V1",
        "descriptive": "model-free; development numbers on TRAIN Fold A (owner decisions 28 and 86); never a test claim",
        "inputs": {
            "sealed_arm": {"run_id": RUN_ID, "attempt_id": ATTEMPT, "phases_relpath": str(phases_path.relative_to(data_root)), "phases_sha256": sha_file(phases_path)},
            "legality": {"relpath": LEGALITY["relpath"], "sha256": LEGALITY["sha256"]},
            "authored_slot_contracts": {"relpath": AUTHORED_RELPATH, "sha256": AUTHORED_SHA256},
            "slot_contract_store": {"relpath": SLOT_SNAPSHOT, "content_hash": SLOT_CONTENT_HASH},
            "gold_offline_only": {"relpath": TRAIN_GOLD, "sha256": TRAIN_GOLD_SHA, "rows_read": len(gold)},
            "error_sources": {"relpath": ERRSRC_ROWS, "sha256": sha_file(errsrc_path)},
            "tokenizer": {"binary": str(TOKENIZE), "vocab_only_model": GGUF, "invocations": tokenizer.invocations},
        },
        "validation": {"rows": len(rows), "replayed_flown_selection_identical_in_order": len(rows),
                       "w1_selection_is_a_subset_of_the_flown_selection_on_every_row": True},
        "cards": {
            "per_row_flown": distribution(cards_base), "per_row_w1": distribution(cards_w1),
            "rows_whose_card_set_changes": rows_changed,
            "rows_with_zero_cards_w1": sum(1 for n in cards_w1 if n == 0),
            "rows_with_zero_cards_flown": sum(1 for n in cards_base if n == 0),
            "zero_card_rows_w1": sorted(row["sample_id"] for row in rows if not row["w1"]),
            "zero_card_note": "a row whose shortlisted intents carry no legal slot type receives no slot-contract card; the route records disposition no-mapping and the Solver still receives its exemplar supply (rails.knowledge_stores composes only the supplies that exist)",
            "card_tokens_per_solver_contact_flown": distribution(tok_base),
            "card_tokens_per_solver_contact_w1": distribution(tok_w1),
            "card_block_tokens": {"min": min(tokens.values()), "max": max(tokens.values()), "mean": round(statistics.fmean(tokens.values()), 1)},
        },
        "saving": {
            "tokens_per_solver_contact": distribution(per_solver_saved),
            "tokens_per_row_over_every_contact_rendering_the_block": distribution(per_row_saved),
            "tokens_per_1080_row_flight": sum(per_row_saved),
            "contacts_rendering_the_block": {role: n for role, n in sorted(role_counts.items()) if role != "perception"},
            "tolerance": "each card is priced as its own rendered block; the separator between blocks is not priced (at most one boundary token per card)",
        },
        "harm": {
            "definition": "a row loses a card for a GOLD slot type: the flown selection offered it and W1 does not, i.e. the gold type is not legal under any shortlisted intent",
            "rows_with_gold_entities": gold_rows,
            "rows_all_gold_types_carded_flown": base_cover,
            "rows_all_gold_types_carded_w1": w1_cover,
            "rows_losing_a_gold_type_card": len(harm),
            "gold_items_of_lost_types": sum(len(h["gold_items_of_lost_types"]) for h in harm),
            "of_which_delivered_exactly_right_by_agree": at_risk_correct_items,
            "rows_whose_delivered_answer_used_a_dropped_type": delivered_type_dropped_rows,
            "rows": harm,
        },
        "static_bound_utf8_bytes": {
            "flown_global_longest_28": sum(global_bound),
            "w1_heaviest_28_any_3_intents_can_reach": sum(utf8[v] for v in narrowed_ids),
            "authored_heaviest_28_any_3_intents_can_reach": sum(utf8[v] for v in authored_ids),
            "w1_cards_in_the_bound": len(narrowed_ids),
            "note": "the runtime bound for a narrowed route is rails.candidate_semantic_supply.max_candidate_selection_value_ids over the narrowed index; the check converts bytes to tokens",
        },
        "sensitivity_grid": grid,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    out = REPO_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    machine = data_root / ANALYSIS_DIR / "measurement-v1.json"
    machine.parent.mkdir(parents=True, exist_ok=True)
    machine.write_text(text, encoding="utf-8")
    print(json.dumps({"out": args.out, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                      "cards": payload["cards"]["per_row_flown"]["mean"], "cards_w1": payload["cards"]["per_row_w1"]["mean"],
                      "saving": payload["saving"]["tokens_per_solver_contact"], "per_row": payload["saving"]["tokens_per_row_over_every_contact_rendering_the_block"],
                      "harm_rows": len(harm), "harm_items": payload["harm"]["gold_items_of_lost_types"],
                      "at_risk_correct": at_risk_correct_items, "static": payload["static_bound_utf8_bytes"],
                      "grid": grid, "tokenizer_invocations": tokenizer.invocations}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
