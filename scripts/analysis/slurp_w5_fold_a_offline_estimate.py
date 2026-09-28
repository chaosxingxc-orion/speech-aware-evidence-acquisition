#!/usr/bin/env python3
"""Offline Fold A estimate for cell W5 (knowledge-wave item W5, slot-side retrieval; owner
decision 170): what the W5 exemplar route would put in front of the Solver on the sealed AGREE
rows, which of the AGREE arm's entity error items it newly PRINTS (the gold type and value appear
in a W5 exemplar and in none of the row's M1 exemplars), what that is worth at a MEASURED
conversion rate, what it risks, and what it costs in prompt tokens per contact.

TAXONOMY. Entity error items are classified with the 2026-09-27 error-source read's own function
(``scripts/analysis/slurp_agree_arm_error_sources.py``, ``entity_items``): FORMAT, BOUNDARY, NEAR,
WRONG-VALUE, WRONG-TYPE, MISSING, SPURIOUS -- the same classes, imported unchanged.

MEASURED RATES ONLY (row 139). (a) M1's delivered-filler conversion: of the 154 B1 saves that gained
a newly correct filler, 133 have that exact filler printed in the block, and the block printed
0.5719 of the 941 Fold A gold fillers (docs/results/2026-09-19-slurp-m1-exemplar-compression-
analysis-v1.md sections 2.1 and 3.2): 133 / (0.5719 x 941) = 0.2471 per printed gold filler, a
LOWER bound (the denominator includes fillers the anchor already had right). (b) pp per repaired
item from the error-source read's isolated repairs (section 3): MISSING 9.80 / 173, WRONG-VALUE
2.12 / 41, NEAR 1.84 / 56, BOUNDARY 2.88 / 75, WRONG-TYPE 4.63 / 51. Expected pp = sum over kinds
of newly printed items x (a) x (b).

BOUNDARY. Gold is read OFFLINE from the governed TRAIN metadata (counts only); the sealed AGREE
outputs, scores and trace are read, never written; the W5 selection is the build's id file. No
utterance text, filler, gold label or model output is printed or persisted: the output carries
ids, kind names, slot TYPE names, counts and hashes. Zero model, server, tokenizer, encoder,
embedder, scorer, network and GPU contacts.

    python scripts/analysis/slurp_w5_fold_a_offline_estimate.py --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity  # noqa: E402

READ_ID = "SAEA-SLURP-W5-FOLD-A-OFFLINE-ESTIMATE-V1"
SCHEMA = "saea-slurp-w5-fold-a-offline-estimate-v1"
OUT_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
ROWS = 1080
BUILD = "prepared/SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1"
ARM = {"run_id": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
       "attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"}
M1_SNAPSHOT = {"relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json",
               "sha256": "4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9"}
W5_SNAPSHOT = {"relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json",
               "sha256": "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63"}
NEW_STORE, ROLE = "slot-exemplars", "train-exemplars"
M1_CONVERSION = {"newly_correct_fillers_printed": 133, "filler_recall_k20": 0.5719, "fold_a_gold_items": 941}
ISOLATED = {"MISSING": (9.80, 173), "WRONG-VALUE": (2.12, 41), "NEAR": (1.84, 56), "BOUNDARY": (2.88, 75),
            "WRONG-TYPE": (4.63, 51)}
M1_CHARS_PER_TOKEN = 3.634  # measured on the flown M1 exemplar block (compression analysis section 1)


def import_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ES = import_path(REPO_ROOT / "scripts/analysis/slurp_agree_arm_error_sources.py", "slurp_agree_arm_error_sources")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_values(root: Path, pin: dict) -> dict:
    snap = KnowledgeSnapshot.from_frozen_json(json.loads((root / pin["relpath"]).read_text(encoding="utf-8")))
    if snap.content_hash() != pin["sha256"]:
        raise SystemExit(f"{pin['relpath']} does not hash to its pin")
    return {v.value_id: v for v in snap.values}


def printed_pairs(content: str) -> set:
    """(type, folded value) pairs an annotated exemplar prints (held in memory only)."""
    slots = content.split(" | ")[2]
    out = set()
    if "=" not in slots:
        return out
    for part in slots.split(";"):
        if "=" in part:
            t, v = part.split("=", 1)
            out.add((t.strip(), ES.fold(v)))
    return out


def rendered_chars(store: str, value_id: str, content: str) -> int:
    return len(f"[value {store}::{value_id}] [knowledge store={store} role={ROLE}] {content}") + 1


def trace_contacts(arm_dir: Path) -> list:
    """(phase, sample, realised prompt tokens, carries the M1 exemplar block) per contact."""
    requests, rows = {}, []
    with (arm_dir / f"{ARM['run_id']}.trace.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            channel = record["channel"]
            if channel == "MODEL_REQUEST":
                payload = record["payload"]["payload"]
                evidence = payload.get("supplied_evidence") or []
                requests[record["record_id"].split("/")[0]] = (
                    payload["key_representation_id"].rsplit(":", 1)[-1], payload["sample_id"],
                    any(str(e.get("evidence_id", "")).startswith("train-exemplars::") for e in evidence))
            elif channel == "MODEL_RESPONSE":
                phase, sample, has_m1 = requests[record["record_id"].split("/")[0]]
                rows.append((phase, sample, int(record["payload"]["usage"]["prompt_tokens"]), has_m1))
    return rows


def estimate(root: Path, lock_path: Path) -> dict:
    lock = load_lock(lock_path)
    gold = ES.load_gold(lock, root)
    arm_dir = root / "runs" / ARM["run_id"] / ARM["attempt"]
    outputs = ES.load_outputs(arm_dir, ARM["run_id"])["rows"]
    selection = {}
    with (root / BUILD / "selection-v1.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                selection[row["id"]] = row
    if len(selection) != ROWS or set(selection) != set(outputs):
        raise SystemExit("the W5 selection and the AGREE outputs do not cover one 1,080-row roster")
    m1_values = snapshot_values(root, M1_SNAPSHOT)
    w5_values = snapshot_values(root, W5_SNAPSHOT)

    kinds = Counter()
    newly = Counter()
    already_m1 = Counter()
    printed_w5_any = Counter()
    newly_by_type = defaultdict(Counter)
    rows_touched = set()
    risk = Counter()
    chars_per_row = {}
    for sid, sel in selection.items():
        g = gold[sid]
        pred = outputs[sid]["entities"]
        items = ES.entity_items(g["entities"], pred)
        m1_pairs = set().union(*(printed_pairs(m1_values[v].content) for v in sel["m1_value_ids"])) if sel["m1_value_ids"] else set()
        w5_pairs = set().union(*(printed_pairs(w5_values[v].content) for v in sel["w5_value_ids"]))
        chars_per_row[sid] = sum(rendered_chars(NEW_STORE, v, w5_values[v].content) for v in sel["w5_value_ids"])
        for item in items:
            kinds[item["kind"]] += 1
            if item["gold_index"] is None:
                continue
            ge = g["entities"][item["gold_index"]]
            pair = (ge.type, ES.fold(ge.filler))
            if pair in w5_pairs:
                printed_w5_any[item["kind"]] += 1
            if pair in m1_pairs:
                already_m1[item["kind"]] += 1
            elif pair in w5_pairs:
                newly[item["kind"]] += 1
                newly_by_type[item["kind"]][ge.type] += 1
                rows_touched.add(sid)
        # risks (counts only)
        gold_intent = g["intent"]
        in_short = gold_intent in sel["shortlist"]
        risk["rows_gold_intent_outside_shortlist"] += int(not in_short)
        risk["intent_correct_rows_gold_outside_shortlist"] += int(not in_short and outputs[sid]["intent"] == gold_intent)
        w5_intents = Counter(w5_values[v].task_target for v in sel["w5_value_ids"])
        risk["rows_w5_block_without_gold_intent"] += int(w5_intents[gold_intent] == 0)
        gold_types = {e.type for e in g["entities"]}
        risk["w5_printed_pairs_of_types_absent_from_gold"] += sum(1 for t, _ in w5_pairs if t not in gold_types)
        risk["w5_printed_pairs"] += len(w5_pairs)
        risk["empty_gold_rows"] += int(not g["entities"])
        risk["empty_gold_rows_where_w5_prints_slots"] += int(not g["entities"] and bool(w5_pairs))

    rate = M1_CONVERSION["newly_correct_fillers_printed"] / (M1_CONVERSION["filler_recall_k20"] * M1_CONVERSION["fold_a_gold_items"])
    per_kind = {}
    total = 0.0
    for kind, (pp, n) in ISOLATED.items():
        value = newly[kind] * rate * pp / n
        per_kind[kind] = {"newly_printed_items": newly[kind], "pp_per_repaired_item": round(pp / n, 6),
                          "expected_pp": round(value, 4)}
        total += value
    oracle = sum(newly[k] * ISOLATED[k][0] / ISOLATED[k][1] for k in ISOLATED)

    contacts = trace_contacts(arm_dir)
    per_phase = {}
    for phase in sorted({c[0] for c in contacts}):
        sel_c = [c for c in contacts if c[0] == phase]
        carrying = [c for c in sel_c if c[3]]
        added = [chars_per_row[c[1]] / M1_CHARS_PER_TOKEN if c[3] else 0.0 for c in sel_c]
        per_phase[phase] = {
            "contacts": len(sel_c), "contacts_carrying_the_m1_block": len(carrying),
            "added_tokens_mean": round(sum(added) / len(added), 1), "added_tokens_max": round(max(added), 1),
            "realised_prompt_tokens_max": max(c[2] for c in sel_c),
            "projected_prompt_tokens_max": int(round(max(c[2] + a for c, a in zip(sel_c, added)))),
        }
    per_row_added = defaultdict(float)
    for c in contacts:
        if c[3]:
            per_row_added[c[1]] += chars_per_row[c[1]] / M1_CHARS_PER_TOKEN
    values = list(per_row_added.values())
    chars = list(chars_per_row.values())
    total_prompt = sum(c[2] for c in contacts)
    cost = {
        "chars_per_token": M1_CHARS_PER_TOKEN,
        "chars_per_token_source": "measured on the flown M1 exemplar block (docs/results/2026-09-19-slurp-m1-exemplar-compression-analysis-v1.md section 1); the block W5 adds has the same line form",
        "block_chars_per_row": {"mean": round(sum(chars) / len(chars), 1), "max": max(chars), "min": min(chars)},
        "block_tokens_per_contact": {"mean": round(sum(chars) / len(chars) / M1_CHARS_PER_TOKEN, 1),
                                     "max": round(max(chars) / M1_CHARS_PER_TOKEN, 1)},
        "per_phase": per_phase,
        "per_row": {"added_tokens_mean": round(sum(values) / ROWS, 1), "added_tokens_max": round(max(values), 1)},
        "total_added_tokens": round(sum(values)), "total_prompt_tokens_realised_agree": total_prompt,
        "added_share_of_prompt_volume": round(sum(values) / total_prompt, 4),
    }
    return {
        "schema": SCHEMA, "read_id": READ_ID,
        "taxonomy": "the error-source read's entity item classes (scripts/analysis/slurp_agree_arm_error_sources.py entity_items), imported unchanged",
        "arm": {"run_id": ARM["run_id"], "outputs_sha256": digest(arm_dir / f"{ARM['run_id']}.outputs.jsonl")},
        "inputs": {"selection_sha256": digest(root / BUILD / "selection-v1.jsonl"),
                   "build_receipt_sha256": digest(root / BUILD / "receipt.json")},
        "error_items_by_kind": dict(sorted(kinds.items())),
        "gold_pair_printed_by_w5": dict(sorted(printed_w5_any.items())),
        "gold_pair_already_printed_by_m1": dict(sorted(already_m1.items())),
        "newly_printed_by_w5_not_m1": dict(sorted(newly.items())),
        "newly_printed_by_type": {k: dict(sorted(v.items())) for k, v in sorted(newly_by_type.items())},
        "rows_touched": len(rows_touched),
        "conversion": {"m1_delivered_filler_conversion": round(rate, 4), "basis": M1_CONVERSION,
                       "isolated_repairs": {k: {"pp": v[0], "items": v[1]} for k, v in ISOLATED.items()}},
        "expected": {"per_kind": per_kind, "expected_pp": round(total, 4), "oracle_pp_if_every_newly_printed_item_converted": round(oracle, 4)},
        "risk": dict(sorted(risk.items())),
        "cost": cost,
        "boundary": "gold read offline, counts only; development numbers (owner decisions 28 and 86); no text persisted",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", default=DEFAULT_LOCK)
    args = parser.parse_args(argv)
    root = Path(args.data_root)
    report = estimate(root, Path(args.lock_path))
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (out / "estimate-v1.json").write_bytes(payload)
    print(json.dumps({"written": str(out / "estimate-v1.json"), "sha256": hashlib.sha256(payload).hexdigest(),
                      "expected": report["expected"], "newly": report["newly_printed_by_w5_not_m1"],
                      "risk": report["risk"], "cost_per_row": report["cost"]["per_row"],
                      "per_phase": report["cost"]["per_phase"], "block": report["cost"]["block_tokens_per_contact"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
