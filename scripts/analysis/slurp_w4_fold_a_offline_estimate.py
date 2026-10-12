#!/usr/bin/env python3
"""Knowledge-wave item W4 (owner decision 164): the offline TRAIN Fold A estimate.

Reads, offline and model-free, the sealed AGREE arm (``SAEA-SLURP-STAGE3-AGREE-W1-
FOLD-A-V1``: its outputs, official per-sample score, phase consumption records and
trace) against governed TRAIN gold, and counts -- per W4 component, only for slot
types whose card the row was actually delivered -- the error items the W4 card
additions could touch and the items they put at risk:

* K2 -- omissions and wrong fillers whose gold value is in the W4 listed vocabulary
  (closed and semi-closed lists) or in a K3 "tagged when spoken" list;
* K3 -- over-emissions whose predicted value is in a K3 "usually left untagged" list
  (the convention would flag them); RISK: exact true positives whose value is in that
  list (recall loss) and gold-untagged spoken occurrences of a listed / tagged-when-
  spoken value in the Fold A sentences (list-induced over-emission);
* K4 -- same-type wrong fillers that are a sub- or super-span of gold differing only
  by a word a W4 span rule names, on the side the rule says.

It also measures the W4 token cost per contact and per row from the flown request
bytes (the delivered slot cards per contact times the per-card byte delta, at the
flight's own measured characters-per-token ratio) and the projected widest realised
request per phase, and derives the M4b analogue the expectation is declared from.

Every Fold A number is a DEVELOPMENT number (owner decisions 28 and 86), never a test
claim. Gold is read offline only; no utterance text, gold filler, predicted filler or
model output is printed or persisted -- cells are slot TYPE names and counts. Zero
model, server, tokenizer, encoder, embedder, scorer, network and GPU contacts.
Writes ``$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-W4-FOLD-A-OFFLINE-ESTIMATE-V1/estimate-v1.json``.
"""

from __future__ import annotations

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "4")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

_DRIVER = Path(__file__).resolve()
REPO_ROOT = _DRIVER.parents[2]
for _p in (str(REPO_ROOT / "src"), str(_DRIVER.parent), str(REPO_ROOT / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from speech_aware_evidence_acquisition.analysis.null_calibration import pooled_f1  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    _SPLIT_FILES,
    _entity_filler,
    _entity_type,
    _governed_roots,
    _tokens_by_id,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    SlotEntity,
    parse_slu_response,
)
from slurp_plan_bad_case_bank import _edit_distance, _fold_punct  # noqa: E402

READ_ID = "SAEA-SLURP-W4-FOLD-A-OFFLINE-ESTIMATE-V1"
SCHEMA = "saea-slurp-w4-fold-a-offline-estimate-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
OUT_DIR = "analysis/SAEA-SLURP-W4-FOLD-A-OFFLINE-ESTIMATE-V1"
ROWS = 1080
FOLD_A_SPLIT_IDENTITY = "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"
SCORER = "slurp-slu-official-train"
TRAIN_GOLD = ("datasets/slurp/metadata/train.jsonl",
              "4a05a3de6c7f028aff298c4a90196e6a3fecd1938d96fb1c125d6fd10d5e301e")
ARM = {"run_id": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
       "attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"}
PREP = "prepared/SAEA-SLURP-SLOT-CONVENTIONS-W4-PREPARE-V1"

#: M4b (cell B4b, slot store v2): the measured analogue. Pooled official SLU-F1 deltas
#: against the sealed dual-store anchor, first flight and request-identical replicate
#: (docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md,
#: docs/results/2026-09-19-slurp-b4b-replicate-verdict.md), and the anchor's FN items on
#: the eight revised types (gold mentions minus exact mentions, the verdict's M4b table).
M4B = {
    "first_pp": 2.5519, "replicate_pp": 1.5403,
    "gold_mentions": {"date": 138, "time": 76, "media_type": 57, "transport_type": 36,
                      "business_type": 29, "order_type": 23, "relation": 16, "event_name": 41},
    "anchor_exact": {"date": 28, "time": 8, "media_type": 8, "transport_type": 10,
                     "business_type": 2, "order_type": 1, "relation": 0, "event_name": 10},
    "anchor_spurious": {"date": 7, "time": 11, "media_type": 8, "transport_type": 2,
                        "business_type": 7, "order_type": 7, "relation": 0, "event_name": 13},
}


class EstimateError(RuntimeError):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_gold(lock: dict, root: Path) -> dict:
    path = _governed_roots(lock, root)[2] / _SPLIT_FILES["train"]
    if digest(path) != TRAIN_GOLD[1]:
        raise EstimateError("governed train metadata does not hash to its pin")
    out = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            context = f"SLURP train.jsonl line {line_no}"
            tokens = _tokens_by_id(raw.get("tokens"), context)
            entities = tuple(SlotEntity(type=_entity_type(e, context),
                                        filler=_entity_filler(tokens, e.get("span"), context))
                             for e in raw["entities"])
            spans = []
            for e in raw["entities"]:
                ids = sorted(int(i) for i in e.get("span") or ())
                if ids:
                    spans.append((min(ids), max(ids) + 1))
            order = sorted(tokens)
            words = [str(tokens[i]).lower() for i in order]
            index_of = {tid: pos for pos, tid in enumerate(order)}
            spans = [(index_of.get(a, -1), index_of.get(b - 1, -2) + 1) for a, b in spans]
            for rec in raw["recordings"]:
                sid = f"slurp:train:{raw['slurp_id']:06d}:{rec['file'][:-len('.flac')]}"
                out[sid] = {"entities": entities, "words": words, "spans": spans}
    return out


def entity_items(gold_entities, predicted_entities) -> dict:
    """The official exact matcher, then the bad-case bank's same-type / type-swap / over /
    omission attribution (as the knowledge content audit applies it)."""
    remaining = list(gold_entities)
    unmatched, exact = [], []
    for entity in predicted_entities:
        if entity in remaining:
            remaining.remove(entity)
            exact.append(entity)
        else:
            unmatched.append(entity)
    by_pred, by_gold = defaultdict(list), defaultdict(list)
    for i, e in enumerate(unmatched):
        by_pred[e.type].append((i, e))
    for i, e in enumerate(remaining):
        by_gold[e.type].append((i, e))
    used_p, used_g, same, swap = set(), set(), [], []
    for slot_type in sorted(set(by_pred) & set(by_gold)):
        options = []
        for pi, pe in by_pred[slot_type]:
            for gi, ge in by_gold[slot_type]:
                left, right = _fold_punct(pe.filler), _fold_punct(ge.filler)
                options.append((_edit_distance(left, right) / max(len(left), len(right), 1), pi, gi, pe, ge))
        for _, pi, gi, pe, ge in sorted(options, key=lambda o: o[:3]):
            if pi in used_p or gi in used_g:
                continue
            used_p.add(pi)
            used_g.add(gi)
            same.append((pe, ge))
    gold_by_filler = defaultdict(list)
    for gi, ge in enumerate(remaining):
        if gi not in used_g:
            gold_by_filler[_fold_punct(ge.filler)].append(gi)
    for pi, pe in enumerate(unmatched):
        if pi in used_p:
            continue
        hits = [g for g in gold_by_filler.get(_fold_punct(pe.filler), ()) if g not in used_g]
        if hits:
            used_p.add(pi)
            used_g.add(hits[0])
            swap.append((pe, remaining[hits[0]]))
    return {"exact": exact, "same": same, "swap": swap,
            "over": [e for i, e in enumerate(unmatched) if i not in used_p],
            "omitted": [e for i, e in enumerate(remaining) if i not in used_g]}


def load_arm(root: Path) -> dict:
    directory = root / "runs" / ARM["run_id"] / ARM["attempt"]
    block = json.loads((directory / f"{ARM['run_id']}.scores.json").read_text(encoding="utf-8"))[SCORER]
    per_sample = {str(s["sample_id"]): s for s in block["per_sample"]}
    delivered = {}
    with (directory / f"{ARM['run_id']}.outputs.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                _, _, entities, _ = parse_slu_response(record.get("text") or "")
                delivered[record["sample_id"]] = list(entities)
    if set(delivered) != set(per_sample) or len(delivered) != ROWS:
        raise EstimateError("the arm's outputs and scores do not cover one 1,080-row roster")
    if split_identity_hash(prefixed("slurp", sorted(delivered))) != FOLD_A_SPLIT_IDENTITY:
        raise EstimateError("the arm roster is not TRAIN Fold A")
    phases = json.loads((directory / f"{ARM['run_id']}.phases.json").read_text(encoding="utf-8"))
    cards = {}
    for result in phases["phases"][0]["results"]:
        got = set()
        for record in (result.get("consumption") or {}).get("records") or ():
            item = str(record.get("supplied_item_id") or "")
            if "slot-contract:" in item:
                got.add(item.split("slot-contract:", 1)[-1])
        cards[result["sample_id"]] = got
    official = block["aggregate"]["official"]
    fields = (("slot_f1_exact_tp",), ("slot_f1_exact_fp",), ("slot_f1_exact_fn",))
    return {"per_sample": per_sample, "delivered": delivered, "cards": cards,
            "span_f1": pooled_f1(per_sample, sorted(per_sample), fields),
            "official": {"slu_f1": official["slu_f1"], "intent_accuracy": official["intent_accuracy"],
                         "span_f1": official["span_f1"]},
            "directory": directory}


def contact_cost(root: Path, arm_dir: Path, added: dict) -> dict:
    """Per contact: the W4 byte delta of the slot cards actually in the request, beside the
    realised prompt tokens; characters per token measured on the flight itself."""
    trace = arm_dir / f"{ARM['run_id']}.trace.jsonl"
    requests, rows = {}, []
    with trace.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            channel = record["channel"]
            if channel == "MODEL_REQUEST":
                payload = record["payload"]["payload"]
                evidence = payload.get("supplied_evidence") or []
                slot_ids = [e["evidence_id"].split("slot-contract:", 1)[-1] for e in evidence
                            if e["evidence_id"].startswith("slot-contracts::")]
                requests[record["record_id"].split("/")[0]] = (
                    payload["key_representation_id"].rsplit(":", 1)[-1],
                    sum(added.get(t, 0) for t in slot_ids),
                    sum(len(e["content"]) for e in evidence),
                    payload["sample_id"])
            elif channel == "MODEL_RESPONSE":
                phase, delta, chars, sample = requests[record["record_id"].split("/")[0]]
                rows.append((phase, delta, chars, sample, int(record["payload"]["usage"]["prompt_tokens"])))
    solver = [r for r in rows if r[0] == "solver"]
    x = np.array([[1.0, r[2]] for r in solver])
    y = np.array([float(r[4]) for r in solver])
    coef = np.linalg.lstsq(x, y, rcond=None)[0]
    chars_per_token = 1.0 / coef[1]
    per_phase = {}
    for phase in sorted({r[0] for r in rows}):
        sel = [r for r in rows if r[0] == phase]
        deltas = [r[1] for r in sel]
        per_phase[phase] = {
            "contacts": len(sel),
            "added_bytes_mean": round(float(np.mean(deltas)), 2), "added_bytes_max": int(max(deltas)),
            "added_tokens_mean": round(float(np.mean(deltas)) / chars_per_token, 1),
            "added_tokens_max": round(max(deltas) / chars_per_token, 1),
            "realised_prompt_tokens_max": int(max(r[4] for r in sel)),
            "realised_prompt_tokens_mean": round(float(np.mean([r[4] for r in sel])), 1),
            "projected_prompt_tokens_max": int(round(max(r[4] + r[1] / chars_per_token for r in sel))),
        }
    per_row = defaultdict(int)
    for r in rows:
        per_row[r[3]] += r[1]
    values = list(per_row.values())
    return {
        "chars_per_token_measured": round(chars_per_token, 4),
        "fit_intercept_tokens": round(float(coef[0]), 2),
        "per_phase": per_phase,
        "per_row": {"added_bytes_mean": round(float(np.mean(values)), 1), "added_bytes_max": int(max(values)),
                    "added_tokens_mean": round(float(np.mean(values)) / chars_per_token, 1),
                    "added_tokens_max": round(max(values) / chars_per_token, 1),
                    "rows_touched": sum(1 for v in values if v > 0)},
        "total_prompt_tokens_realised": int(sum(r[4] for r in rows)),
        "total_added_tokens": round(sum(r[1] for r in rows) / chars_per_token, 0),
    }


def estimate(lock_path: Path, root: Path) -> dict:
    lock = load_lock(lock_path)
    conventions = json.loads((root / PREP / "conventions-v1.json").read_text(encoding="utf-8"))
    changes = json.loads((root / PREP / "CHANGES.json").read_text(encoding="utf-8"))
    revised = set(changes["changed_cards"])
    added = {c["slot_id"]: c["added_bytes"] for c in changes["cards"]}
    listed = {t: {_fold_punct(v) for v, _ in conventions["vocabulary"][t]["listed"]}
              for t in revised if conventions["vocabulary"].get(t, {}).get("class") in ("closed", "semi-closed")}
    scope = conventions["annotation_scope"]
    recurring = {t for t in revised if conventions["vocabulary"].get(t, {}).get("class") == "semi-closed"
                 or (conventions["vocabulary"].get(t, {}).get("class") == "open"
                     and conventions["vocabulary"][t]["loo_value_coverage"] >= 0.70)}
    tagged = {t: {_fold_punct(r["value"]) for r in scope.get(t, {}).get("tagged_when_spoken", [])}
              for t in recurring}
    untagged = {t: {_fold_punct(r["value"]) for r in scope.get(t, {}).get("usually_untagged", [])} for t in revised}
    span_rules = {t: conventions["span_extent"].get(t, {}).get("rules", []) for t in revised}

    gold = load_gold(lock, root)
    arm = load_arm(root)
    counts = defaultdict(Counter)
    per_type = defaultdict(Counter)
    repair_rows = defaultdict(set)
    tp = fp = fn = 0
    for sid, predicted in arm["delivered"].items():
        g = gold[sid]
        items = entity_items(g["entities"], predicted)
        tp += len(items["exact"])
        fp += len(items["same"]) + len(items["swap"]) + len(items["over"])
        fn += len(items["same"]) + len(items["swap"]) + len(items["omitted"])
        delivered_cards = arm["cards"][sid]
        on = lambda t: t in revised and t in delivered_cards  # noqa: E731
        for e in items["omitted"]:
            if not on(e.type):
                continue
            per_type[e.type]["fn_omitted_on_delivered"] += 1
            f = _fold_punct(e.filler)
            if f in listed.get(e.type, ()) or f in tagged.get(e.type, ()):
                counts["K2"]["omission_gold_value_listed"] += 1
                per_type[e.type]["K2_omission"] += 1
                repair_rows["K2"].add(sid)
        for pe, ge in items["same"]:
            if not on(ge.type):
                continue
            per_type[ge.type]["wrong_filler_on_delivered"] += 1
            gf, pf = _fold_punct(ge.filler), _fold_punct(pe.filler)
            if (gf in listed.get(ge.type, ()) or gf in tagged.get(ge.type, ())) and not (
                    pf in listed.get(ge.type, ()) or pf in tagged.get(ge.type, ())):
                counts["K2"]["wrong_gold_listed_pred_not"] += 1
                repair_rows["K2"].add(sid)
            gw, pw = gf.split(), pf.split()
            fixed = False
            for rule in span_rules.get(ge.type, ()):
                word, outside = rule["word"], rule["side"] == "outside"
                if word == "<preposition>":
                    continue
                if rule["edge"] == "lead":
                    if outside and pw[:1] == [word] and pw[1:] == gw:
                        fixed = True
                    if not outside and gw[:1] == [word] and gw[1:] == pw:
                        fixed = True
                else:
                    if outside and pw[-1:] == [word] and pw[:-1] == gw:
                        fixed = True
                    if not outside and gw[-1:] == [word] and gw[:-1] == pw:
                        fixed = True
            contain = gf != pf and (gf in pf or pf in gf)
            if contain:
                counts["K4"]["containment_wrong_filler"] += 1
            if fixed:
                counts["K4"]["span_rule_would_fix"] += 1
                per_type[ge.type]["K4_fix"] += 1
                repair_rows["K4"].add(sid)
        for e in items["over"]:
            if not on(e.type):
                continue
            per_type[e.type]["over_emission_on_delivered"] += 1
            if _fold_punct(e.filler) in untagged.get(e.type, ()):
                counts["K3"]["over_emission_value_usually_untagged"] += 1
                per_type[e.type]["K3_flag"] += 1
                repair_rows["K3"].add(sid)
        for e in items["exact"]:
            if on(e.type) and _fold_punct(e.filler) in untagged.get(e.type, ()):
                counts["risk"]["exact_tp_value_usually_untagged"] += 1
        # list-induced over-emission risk: a listed / tagged-when-spoken value SPOKEN in the
        # gold sentence but not annotated (any type) -- counted, never printed
        words = g["words"]
        covered = set()
        for a, b in g["spans"]:
            covered.update(range(a, b))
        for t in revised:
            if t not in delivered_cards:
                continue
            for value in listed.get(t, set()) | tagged.get(t, set()):
                vw = value.split()
                n = len(vw)
                for i in range(len(words) - n + 1):
                    if words[i:i + n] == vw and not any(j in covered for j in range(i, i + n)):
                        counts["risk"]["listed_value_spoken_untagged"] += 1
                        repair_rows["risk_list"].add(sid)
    # exact span-F1 ceilings (oracle): K2 omissions repaired (+tp, -fn); K2 wrong repaired
    # (+tp, -fp, -fn); K3 flagged over-emissions removed (-fp); K4 fixes (+tp, -fp, -fn)
    def f1(t, p, n):
        return 100.0 * 2 * t / (2 * t + p + n)

    base = f1(tp, fp, fn)
    k2o, k2w = counts["K2"]["omission_gold_value_listed"], counts["K2"]["wrong_gold_listed_pred_not"]
    k3, k4 = counts["K3"]["over_emission_value_usually_untagged"], counts["K4"]["span_rule_would_fix"]
    ceilings = {
        "K2": round(f1(tp + k2o + k2w, fp - k2w, fn - k2o - k2w) - base, 4),
        "K3": round(f1(tp, fp - k3, fn) - base, 4),
        "K4": round(f1(tp + k4, fp - k4, fn - k4) - base, 4),
        "all": round(f1(tp + k2o + k2w + k4, fp - k2w - k3 - k4, fn - k2o - k2w - k4) - base, 4),
    }
    if abs(base - arm["span_f1"] * (100.0 if arm["span_f1"] <= 1.0 else 1.0)) > 1e-6:
        raise EstimateError("the exact matcher does not reproduce the arm's pooled span-F1")
    targeted_fn = sum(v["fn_omitted_on_delivered"] + v["wrong_filler_on_delivered"] for v in per_type.values())
    m4b_fn = sum(M4B["gold_mentions"][t] - M4B["anchor_exact"][t] for t in M4B["gold_mentions"])
    per_item = {"first": M4B["first_pp"] / m4b_fn, "replicate": M4B["replicate_pp"] / m4b_fn,
                "mean": (M4B["first_pp"] + M4B["replicate_pp"]) / 2 / m4b_fn}
    analogue = {
        "m4b_fn_items_on_its_eight_types": m4b_fn,
        "m4b_pp_per_fn_item": {k: round(v, 6) for k, v in per_item.items()},
        "w4_fn_items_on_revised_types_with_card_delivered": targeted_fn,
        "w4_expected_pp": {k: round(v * targeted_fn, 4) for k, v in per_item.items()},
    }
    return {
        "schema": SCHEMA, "read_id": READ_ID,
        "arm": {**ARM, "official": arm["official"], "exact_tp_fp_fn": [tp, fp, fn],
                "pooled_span_f1": round(base, 4)},
        "revised_types": sorted(revised),
        "counts": {k: dict(v) for k, v in counts.items()},
        "rows_touched": {k: len(v) for k, v in repair_rows.items()},
        "per_type": {t: dict(v) for t, v in sorted(per_type.items())},
        "span_f1_oracle_ceilings_pp": ceilings,
        "m4b_analogue": analogue,
        "cost": contact_cost(root, arm["directory"], added),
        "inputs": {"conventions_sha256": digest(root / PREP / "conventions-v1.json"),
                   "changes_sha256": digest(root / PREP / "CHANGES.json")},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR", DEFAULT_DATA_ROOT))
    args = parser.parse_args(argv)
    root = Path(args.data_root)
    result = estimate(Path(args.lock), root)
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (out / "estimate-v1.json").write_bytes(raw)
    print(json.dumps({**result, "sha256": hashlib.sha256(raw).hexdigest()}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
