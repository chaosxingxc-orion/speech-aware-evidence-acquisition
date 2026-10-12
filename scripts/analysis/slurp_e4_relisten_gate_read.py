#!/usr/bin/env python3
"""E4-1 pre-declared information-gain gate read (model-free, DESCRIPTIVE).

Companion to ``scripts/flights/e4/e4_read.sh`` (read row
``SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1``). The paired reads give
the official pooled SLU-F1 deltas; this driver evaluates the gate the
coordinator pre-declared in that row before any read
(``docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md``,
section 5 item 2):

* replace-only column: NOMINATED only if its net conversion over the 106
  hearing-visible + re-listen-addressable gold items is at least 29 %;
* drop-when-unheard column: only if it removes at least 49.5 net false
  positives, with harm counted on the 273 correct items absent from the
  Perception note.

The 106 / 179 / 273 sets were derived on the retained AGREE arm
``SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`` by the node information-gain ledger.
Gold-side items are keyed by ``(sample_id, gold_index)``, which is independent
of any arm's prediction, so the AGREE-defined 106 set is evaluated directly on
E4-1's delivered and shadow columns. Pred-side sets (SPURIOUS) are not
transferable across arms, so the drop gate is evaluated on E4-1's own
delivered column with the same definitions (a SPURIOUS item's filler, and an
EXACT item's filler, contiguous or not in the row's own Perception note), and
the AGREE-defined 273 keys are reported beside it.

It also writes the per-entity-class transition table (delivered -> shadow),
the blind-disposition / confirm-vote tallies and the relisten contact cost.

Gold enters only offline, through the governed TRAIN loader, on the scoring
side. No utterance text, transcript, gold value, filler or model output is
printed or persisted: only ids, counts, rates, slot TYPE names and hashes.
Zero model, server, tokenizer, encoder, embedder, scorer-subprocess, network
and GPU contacts.

    PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/slurp_e4_relisten_gate_read.py \\
        --data-root "$SPEECHRL_DATA_DIR" \\
        --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1"
RUN = "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1"
SEAL_ATTEMPT = "attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only"
PRED_ATTEMPT = "attempt-slurp-native-stage3-relisten-fold-a-generation-v1"
PRED_TRACE_SHA = "966613e416dd81c9cd5bbdc21b16050f394844e5b9da6522ed8451b1f1f233f6"
COLUMNS = ("relisten-replace-only", "relisten-replace-drop-unheard")
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROWS = 1080
GATE_REPLACE_NET_RATE = 0.29
GATE_DROP_NET_FP = 49.5
EXPECT_AGREE = {"hearing": 71, "relisten35": 35, "hearing_or_relisten": 106,
                "spurious": 253, "spurious_not_in_note": 179, "exact_not_in_note": 273}
GOLD_KINDS = ("EXACT", "FORMAT", "BOUNDARY", "NEAR", "WRONG-VALUE", "WRONG-TYPE", "MISSING")


class ReadError(RuntimeError):
    pass


def import_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def parse_column(path: Path, slot_entity) -> dict:
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    rows = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            _s, _a, entities, _ok = parse_slu_response(record.get("text") or "")
            rows[record["sample_id"]] = tuple(slot_entity(e.type, e.filler) for e in entities)
    return rows


def gold_states(gold: tuple, pred: tuple, entity_items) -> tuple[dict, list]:
    """(gold_index -> kind with EXACT for matched, [spurious pred indices])."""
    items = entity_items(gold, pred)
    states = {gi: "EXACT" for gi in range(len(gold))}
    spurious = []
    for it in items:
        if it["gold_index"] is None:
            spurious.append(it["pred_index"])
        else:
            states[it["gold_index"]] = it["kind"]
    matched_pred = {}
    taken = set()
    for pi, entity in enumerate(pred):
        hit = next((gi for gi, g in enumerate(gold) if gi not in taken and g == entity), None)
        if hit is not None:
            taken.add(hit)
            matched_pred[pi] = ("EXACT", hit)
    for it in items:
        if it["gold_index"] is not None and it.get("pred_index") is not None:
            matched_pred[it["pred_index"]] = (it["kind"], it["gold_index"])
    return states, spurious, matched_pred


def perception_tokens(trace_path: Path, canonical) -> dict:
    out = {}
    with trace_path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("channel") != "ORG":
                continue
            sid = record["record_id"].split("/", 1)[0]
            for state in record["payload"].get("org_agent_states") or ():
                if state.get("state_kind") != "phase:perception":
                    continue
                payload = json.loads(state.get("content") or "")
                parts = []
                for cand in payload.get("candidates") or ():
                    parts.append(str(cand.get("distinction") or ""))
                    parts.extend(str(u) for u in cand.get("unresolved_fields") or ())
                out[sid] = canonical(" ".join(parts)).split()
                break
    return out


def agree_sets(data_root: Path, gold: dict, ids: list) -> dict:
    """The AGREE-defined item keys, derived exactly as
    scripts/analysis/slurp_slu_consumption_headroom.py derives them."""
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import (
        canonical, contiguous_in, entity_items)

    NG = import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    ES, GP, W5 = NG.ES, NG.GP, NG.W5
    spec = NG.ARMS[0]
    if spec["run_id"] != "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1":
        raise ReadError("the ledger's primary arm is not the AGREE arm")
    phases = GP.load_phases(data_root, spec)
    directory = phases["directory"]
    outputs = ES.load_outputs(directory, spec["run_id"])
    scores = ES.load_scores(directory, spec["run_id"])
    nodes = NG.load_node_states(data_root, spec)
    pool = GP.load_exemplar_pool(data_root, ES.EX_SNAPSHOT)
    m1_values = W5.snapshot_values(data_root, W5.M1_SNAPSHOT)
    arm = {"label": spec["label"], "phases": phases["rows"], "outputs": outputs["rows"], "scores": scores["rows"],
           "nodes": nodes["rows"]}
    derived = NG.derive_arm(arm, gold, ids, pool, m1_values)
    NG.slot_ledger(derived["rows"], derived["items"], ids)  # assigns each item its origin, as the headroom read does
    hearing, relisten35 = set(), set()
    for li in derived["items"]:
        if li["d"] == "EXACT":
            continue
        key = (li["sample_id"], li["gold_index"])
        if li["origin"].startswith("hearing"):
            hearing.add(key)
        if li["d"] in NG.RELISTEN_KINDS and li["note"] == "CONTIGUOUS":
            relisten35.add(key)
    spurious, sp_out, exact_out = 0, 0, set()
    for sid in ids:
        g = gold[sid]["entities"]
        p = outputs["rows"][sid]["entities"]
        tokens = nodes["rows"][sid]["perception"]["tokens"] if nodes["rows"][sid]["perception"] else []
        states, spur, _m = gold_states(g, p, entity_items)
        spurious += len(spur)
        sp_out += sum(1 for pi in spur if not contiguous_in(canonical(p[pi].filler).split(), tokens))
        for gi, kind in states.items():
            if kind == "EXACT" and not contiguous_in(canonical(g[gi].filler).split(), tokens):
                exact_out.add((sid, gi))
    got = {"hearing": len(hearing), "relisten35": len(relisten35),
           "hearing_or_relisten": len(hearing | relisten35), "spurious": spurious,
           "spurious_not_in_note": sp_out, "exact_not_in_note": len(exact_out)}
    if got != EXPECT_AGREE:
        raise ReadError(f"AGREE set re-derivation differs from the published counts: {got}")
    return {"hearing_or_relisten": hearing | relisten35, "exact_not_in_note": exact_out, "counts": got,
            "slot_entity": ES.SlotEntity}


def build(args) -> dict:
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import (
        canonical, contiguous_in, entity_items)
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split

    NGmod = import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    ES = NGmod.ES
    data_root = Path(args.data_root)
    run_dir = data_root / "runs" / RUN / SEAL_ATTEMPT
    manifest = json.loads((run_dir / f"{RUN}.run-manifest.json").read_text(encoding="utf-8"))
    pred_block = manifest.get("predecessor_attempt") or {}
    if manifest.get("status") != "COMPLETED" or pred_block.get("trace_sha256") != PRED_TRACE_SHA:
        raise ReadError("the seal-only manifest is not COMPLETED or does not name the registered predecessor trace")
    pred_trace = data_root / "runs" / RUN / PRED_ATTEMPT / f"{RUN}.trace.jsonl"
    if sha256_file(pred_trace) != PRED_TRACE_SHA:
        raise ReadError("predecessor trace re-hash differs")
    colroot = run_dir / "supply-variants"
    render = json.loads((colroot / "relisten-render-manifest.json").read_text(encoding="utf-8"))

    lock = load_lock(Path(args.lock))
    records = load_slurp_split(lock, data_root, "train", workers=4)
    gold = {r.sample_id: {"intent": r.intent, "scenario": r.scenario, "action": r.action,
                          "entities": tuple(ES.SlotEntity(e.type, e.filler) for e in r.entities)} for r in records}

    delivered_rows = {}
    receipts = {}
    with (run_dir / f"{RUN}.outputs.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            receipts[row["sample_id"]] = row.get("relisten")
    delivered = parse_column(run_dir / f"{RUN}.outputs.jsonl", ES.SlotEntity)
    ids = sorted(delivered)
    if len(ids) != ROWS:
        raise ReadError("roster is not the 1,080-row Fold A roster")
    shadows = {c: parse_column(colroot / f"arm-{c}-shadow-outputs.jsonl", ES.SlotEntity) for c in COLUMNS}
    for c in COLUMNS:
        if sorted(shadows[c]) != ids:
            raise ReadError(f"{c}: roster differs")
    tokens = perception_tokens(pred_trace, canonical)
    if len(tokens) != ROWS:
        raise ReadError(f"Perception note found for {len(tokens)} of {ROWS} rows")

    agree = agree_sets(data_root, gold, ids)

    # receipt tallies
    tally = Counter()
    for sid in ids:
        rec = receipts[sid] or {}
        tally["rows_with_receipt"] += bool(rec)
        tally["triggered"] += int(rec.get("triggered_count") or 0)
        tally["contacts"] += int(rec.get("contacts_used") or 0)
        for e in rec.get("entities") or ():
            b = e.get("blind") or {}
            tally["blind:" + str(b.get("disposition"))] += 1
            cf = e.get("confirm")
            if isinstance(cf, dict):
                tally["confirm_fired"] += 1
                tally["confirm_vote:" + str(cf.get("vote"))] += 1
            tally["confirm_unheard_vote"] += bool(e.get("confirm_unheard_vote"))
            tally["accept"] += bool(e.get("accept"))
            tally["drop_rule"] += (b.get("disposition") in ("unheard", "unparsed") and bool(e.get("confirm_unheard_vote")))
            tally["accept_type:" + str(e.get("slot_type"))] += bool(e.get("accept"))

    # per-entity-class transitions and the gate
    trans = {c: Counter() for c in COLUMNS}
    spur_count = {"delivered": 0, **{c: 0 for c in COLUMNS}}
    type_trans = {c: Counter() for c in COLUMNS}
    changed_rows = {c: 0 for c in COLUMNS}
    replace_106 = Counter()
    agree273 = Counter()
    drop = Counter()
    own_sets = Counter()
    for sid in ids:
        g = gold[sid]["entities"]
        d_pred = delivered[sid]
        d_states, d_spur, d_match = gold_states(g, d_pred, entity_items)
        spur_count["delivered"] += len(d_spur)
        toks = tokens[sid]
        own_sets["spurious"] += len(d_spur)
        own_sets["spurious_not_in_note"] += sum(
            1 for pi in d_spur if not contiguous_in(canonical(d_pred[pi].filler).split(), toks))
        exact_out_row = {gi for gi, k in d_states.items()
                         if k == "EXACT" and not contiguous_in(canonical(g[gi].filler).split(), toks)}
        own_sets["exact_not_in_note"] += len(exact_out_row)
        own_sets["gold_items"] += len(g)
        own_sets["exact"] += sum(1 for k in d_states.values() if k == "EXACT")
        col_states = {}
        for c in COLUMNS:
            s_pred = shadows[c][sid]
            changed_rows[c] += s_pred != d_pred
            s_states, s_spur, _m = gold_states(g, s_pred, entity_items)
            col_states[c] = s_states
            spur_count[c] += len(s_spur)
            for gi in range(len(g)):
                a, b = d_states[gi], s_states[gi]
                trans[c][(a, b)] += 1
                if a != b:
                    type_trans[c][(g[gi].type, a, b)] += 1
        # replace-only gate over the AGREE-defined 106
        for gi in range(len(g)):
            if (sid, gi) in agree["hearing_or_relisten"]:
                a, b = d_states[gi], col_states[COLUMNS[0]][gi]
                replace_106["items"] += 1
                replace_106["delivered_exact"] += a == "EXACT"
                replace_106["delivered_error"] += a != "EXACT"
                replace_106["converted"] += a != "EXACT" and b == "EXACT"
                replace_106["broken"] += a == "EXACT" and b != "EXACT"
                replace_106["changed_state"] += a != b
            if (sid, gi) in agree["exact_not_in_note"]:
                a, b = d_states[gi], col_states[COLUMNS[1]][gi]
                agree273["items"] += 1
                agree273["delivered_exact"] += a == "EXACT"
                agree273["lost_in_drop_column"] += a == "EXACT" and b != "EXACT"
        # drop gate: the dropped indices of column (b) relative to column (a)
        rec = receipts[sid] or {}
        dropped = {int(e["index"]) for e in rec.get("entities") or ()
                   if (e.get("blind") or {}).get("disposition") in ("unheard", "unparsed")
                   and e.get("confirm_unheard_vote")}
        if len(shadows[COLUMNS[0]][sid]) - len(shadows[COLUMNS[1]][sid]) != len(dropped):
            raise ReadError(f"{sid}: column (b) does not drop exactly the receipt's drop set")
        for pi in dropped:
            drop["dropped"] += 1
            if pi in d_spur:
                drop["spurious_removed"] += 1
                in_note = contiguous_in(canonical(d_pred[pi].filler).split(), toks)
                drop["spurious_removed_not_in_note" if not in_note else "spurious_removed_in_note"] += 1
            else:
                kind, gi = d_match.get(pi, ("?", None))
                if kind == "EXACT":
                    drop["exact_lost"] += 1
                    if gi in exact_out_row:
                        drop["exact_lost_not_in_note"] += 1
                else:
                    drop["partial_lost:" + kind] += 1

    replace_rate = replace_106["converted"] - replace_106["broken"]
    replace_net_rate = replace_rate / replace_106["items"] if replace_106["items"] else 0.0
    net_fp_all = drop["spurious_removed"] - drop["exact_lost"]
    net_fp_note = drop["spurious_removed"] - drop["exact_lost_not_in_note"]

    def table(counter):
        return {f"{a}->{b}": n for (a, b), n in sorted(counter.items()) if a != b}

    cost = manifest.get("cost") or {}
    gen = json.loads((run_dir / f"{RUN}.generation-manifest.json").read_text(encoding="utf-8"))
    report = {
        "schema": "saea-slurp-e4-relisten-gate-read-v1",
        "read_id": READ_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run": RUN, "attempt": SEAL_ATTEMPT, "predecessor_trace_sha256": PRED_TRACE_SHA,
        "render_manifest_counts": {k: render.get(k) for k in (
            "rows", "triggered_count_total", "contacts_used_total", "at1_column_reproduction_checked_rows")},
        "receipt_tallies": dict(sorted(tally.items())),
        "flight_cost_generation_manifest": gen.get("cost"),
        "seal_only_manifest_cost": {k: cost.get(k) for k in ("calls_used", "audio_seconds_used")},
        "agree_sets": agree["counts"],
        "e4_own_sets": dict(own_sets),
        "changed_rows": changed_rows,
        "spurious_items": spur_count,
        "gold_state_transitions": {c: table(trans[c]) for c in COLUMNS},
        "gold_state_totals": {
            "delivered": dict(Counter(k for (k, _b), n in trans[COLUMNS[0]].items() for _ in range(n))),
            **{c: dict(Counter(b for (_a, b), n in trans[c].items() for _ in range(n))) for c in COLUMNS}},
        "type_transitions_top": {c: [[t, a, b, n] for (t, a, b), n in type_trans[c].most_common(15)]
                                 for c in COLUMNS},
        "gate_replace_only": {**dict(replace_106), "net_converted": replace_rate,
                              "net_conversion_rate": round(replace_net_rate, 4),
                              "threshold": GATE_REPLACE_NET_RATE,
                              "nominated_by_gate": replace_net_rate >= GATE_REPLACE_NET_RATE},
        "gate_drop": {**dict(drop), "agree_273": dict(agree273),
                      "net_fp_removed_harm_on_not_in_note_exact": net_fp_note,
                      "net_fp_removed_harm_on_all_exact": net_fp_all,
                      "threshold": GATE_DROP_NET_FP,
                      "nominated_by_gate": net_fp_note >= GATE_DROP_NET_FP},
    }
    return report


def render_md(r: dict) -> str:
    lines = [f"# E4-1 gate read ({r['read_id']})", "", f"Generated: {r['generated_at']}", ""]
    for key in ("render_manifest_counts", "receipt_tallies", "agree_sets", "e4_own_sets", "changed_rows",
                "spurious_items", "gold_state_totals", "gold_state_transitions", "type_transitions_top",
                "gate_replace_only", "gate_drop", "flight_cost_generation_manifest"):
        lines += [f"## {key}", "", "```json", json.dumps(r[key], indent=1, sort_keys=True, default=str), "```", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    args = parser.parse_args(argv)
    out = Path(args.data_root) / "analysis" / READ_ID / "gate"
    if out.exists() and any(out.iterdir()):
        print(f"REFUSED: {out} already holds files", file=sys.stderr)
        return 5
    try:
        report = build(args)
    except ReadError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
                                     encoding="utf-8", newline="\n")
    (out / "tables.md").write_text(render_md(report), encoding="utf-8", newline="\n")
    print(json.dumps({"gate_replace_only": report["gate_replace_only"], "gate_drop": report["gate_drop"]},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
