#!/usr/bin/env python3
"""AT-M3: the scope-rule deliver stage, re-derived on the R5 table, on the sealed AGREE and wave A/A arms.

Evidence-consumption module, migration step 3 (design ``docs/superpowers/specs/2026-09-29-slurp-
consumption-module-design.md`` section 4; owner decision 195 = B; coordinator ruling R5). The offline
read (``docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md``) measured the do-not-tag
scope rule at +1.04 [+0.53, +1.57] pp SLU-F1 on the AGREE arm and +0.93 [+0.46, +1.42] on the wave
A/A replicate, with pool statistics counted over the Fold-A-excluded pool that still held R01. R5
moves the table to TRAIN minus Fold A, Fold B, R01 and R01C
(``prepared/SAEA-SLURP-SCOPE-RULE-TABLE-V1``); this read re-derives the estimate on that table.

Per arm it proves, row by row, that three computations select the SAME delivered entities:

1. the offline rule of the headroom read, recomputed here from the R5 pool with that read's own
   ``scope_counts`` / ``untagged_share`` (never the table);
2. the rule looked up in the pinned table (``rails.delivery_normalisers.scope_rule_drops``);
3. the registered runtime stage ``saea-deliver-scope-rule-v1`` run over the row's own sealed
   delivered text (the text the official scorer read), whose receipt names the dropped indices.

It then scores the edit exactly (the headroom read's in-process official arithmetic over the sealed
totals, which it reproduces to 1e-6) with the programme bootstrap (seed 20260807, 10,000 draws). As
a control it also recomputes the rule on the ORIGINAL pool and asserts the published 66 drops and
+1.04 / +0.93.

Gold discipline: gold enters only offline, through the governed TRAIN loader
``data.slurp.load_slurp_split``, on the scoring side. No utterance text, phrase, gold value, filler
or model output is printed or persisted: counts, pp, ids and hashes only. Zero model, server,
tokenizer, encoder, embedder, scorer-subprocess, network and GPU contacts.

    PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/slurp_scope_rule_stage_estimate.py \\
        --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-SCOPE-RULE-STAGE-ESTIMATE-R5-V1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
SCORER = "slurp-slu-official-train"
ROWS = 1080
ORIGINAL_POOL = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
#: The published numbers of the offline read at threshold 0.8 (headroom note :94) -- the control.
PUBLISHED = {"agree": {"predictions_dropped": 66, "exact_pp": 1.04}, "wave_aa": {"exact_pp": 0.93}}


class ReadError(RuntimeError):
    pass


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pool_exemplars(gp, data_root: Path, relpath: str) -> list:
    pool = gp.load_exemplar_pool(data_root, relpath)
    return [(v["utterance"].split(), [f.split() for fl in v["fillers"].values() for f in fl])
            for _k, v in sorted(pool["values"].items())], pool


def offline_drops(hr, entities_by_sid: dict, occ, tagged) -> dict:
    """The headroom read's rule, operand for operand, at its registered thresholds."""
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import fold

    out = {}
    for sid, entities in entities_by_sid.items():
        hits = set()
        for pi, e in enumerate(entities):
            n, u = hr.untagged_share(tuple(fold(e.filler).split()), occ, tagged)
            if n >= hr.SCOPE_MIN_OCC and u is not None and u >= 0.8:
                hits.add(pi)
        if hits:
            out[sid] = hits
    return out


def build(args) -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.analysis.sealed_credit import row_states as RS
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items
    from speech_aware_evidence_acquisition.rails import delivery_normalisers as DN
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    HR = import_path(REPO_ROOT / "scripts/analysis/slurp_slu_consumption_headroom.py", "slurp_slu_consumption_headroom")
    TB = import_path(REPO_ROOT / "scripts/build_slurp_scope_rule_table.py", "build_slurp_scope_rule_table")
    NG = import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    ES, GP = NG.ES, NG.GP
    data_root = Path(args.data_root)

    table_path = data_root / DN.SCOPE_RULE_TABLE_RELPATH
    table = DN.ScopeRuleTable.from_bytes(table_path.read_bytes(), expected_sha256=DN.SCOPE_RULE_TABLE_SHA256)
    r5_exemplars, r5_pool = pool_exemplars(GP, data_root, TB.W3A.POOL[0])
    if r5_pool["content_sha256"] != TB.W3A.POOL[1]:
        raise ReadError("the R5 pool is not the pinned content hash")
    r5_occ, r5_tagged = HR.scope_counts(r5_exemplars)
    orig_exemplars, orig_pool = pool_exemplars(GP, data_root, ORIGINAL_POOL)
    orig_occ, orig_tagged = HR.scope_counts(orig_exemplars)

    lock = load_lock(Path(args.lock))
    records = load_slurp_split(lock, data_root, "train", workers=4)
    gold_e = {r.sample_id: tuple(ES.SlotEntity(e.type, e.filler) for e in r.entities) for r in records}

    arms = {}
    for label, spec in (("agree", NG.ARMS[0]), ("wave_aa", NG.ARMS[1])):
        directory = data_root / "runs" / spec["run_id"] / spec["attempt"]
        outputs_path = directory / f"{spec['run_id']}.outputs.jsonl"
        texts = {}
        for line in outputs_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                texts[record["sample_id"]] = record.get("text") or ""
        outputs = ES.load_outputs(directory, spec["run_id"])
        ids = sorted(outputs["rows"])
        if len(ids) != ROWS or set(ids) != set(texts):
            raise ReadError(f"{label}: not the 1,080-row Fold A roster")
        pred = {sid: outputs["rows"][sid]["entities"] for sid in ids}
        gold = {sid: gold_e[sid] for sid in ids}
        sealed = RS.load_scores(directory, spec["run_id"], SCORER)
        sealed_totals = tuple(sum(sealed["rows"][s][k] for s in ids) for k in ("tp", "fp", "fn"))
        rs = HR.Rescorer(gold, pred, ES.slu_counts, ids)
        if any(abs(a - b) > 1e-6 for a, b in zip(rs.base, sealed_totals)):
            raise ReadError(f"{label}: in-process totals do not reproduce the sealed official totals")

        # 1. offline rule on the R5 pool; 2. the pinned table; 3. the registered stage on sealed text
        offline = offline_drops(HR, pred, r5_occ, r5_tagged)
        via_table = {}
        via_stage = {}
        stage_changed_rows = 0
        for sid in ids:
            hits = set(DN.scope_rule_drops([e.filler for e in pred[sid]], table))
            if hits:
                via_table[sid] = hits
            normalisation = DN.DELIVERY_NORMALISERS.resolve(DN.DELIVER_SCOPE_RULE_V1)(texts[sid], table=table)
            DN.validate_scope_rule_receipt(dict(normalisation.receipt))
            dropped = set(normalisation.receipt["dropped_entity_indices"])
            if dropped:
                via_stage[sid] = dropped
                stage_changed_rows += int(normalisation.changed)
                _s, _a, kept, parsed = parse_slu_response(normalisation.text)
                expect = [e for i, e in enumerate(pred[sid]) if i not in dropped]
                if not parsed or [(e.type, e.filler) for e in kept] != [(e.type, e.filler) for e in expect]:
                    raise ReadError(f"{label}: the stage's delivered text does not parse to the kept entities")
        if not (offline == via_table == via_stage):
            raise ReadError(f"{label}: the offline rule, the table and the stage disagree on the row set")
        new = HR.drop_preds(offline, pred)
        spur = exact = other = 0
        for sid, hits in offline.items():
            its = entity_items(gold[sid], pred[sid])
            spur_idx = {it["pred_index"] for it in its if it["gold_index"] is None}
            matched_idx = {it["pred_index"] for it in its if it["pred_index"] is not None}
            for pi in hits:
                if pi in spur_idx:
                    spur += 1
                elif pi not in matched_idx:
                    exact += 1
                else:
                    other += 1
        boot = NG.boot_f1(ids, rs.base_rows, rs.edited_rows(new))
        # control: the rule on the ORIGINAL (Fold-A-excluded, R01-inclusive) pool
        control = offline_drops(HR, pred, orig_occ, orig_tagged)
        control_pp = round(rs.gain(HR.drop_preds(control, pred)), 4)
        arms[label] = {
            "run_id": spec["run_id"],
            "outputs": {"relpath": str(outputs_path.relative_to(data_root)), "sha256": digest(outputs_path)},
            "scores": [sealed["relpath"], sealed["sha256"]],
            "sealed_slu_f1": round(HR.pooled_f1(sealed_totals), 4),
            "rows_edited": len(offline),
            "predictions_dropped": sum(len(v) for v in offline.values()),
            "spurious_dropped": spur, "exact_dropped": exact, "other_matched_dropped": other,
            "stage_rows_changed": stage_changed_rows,
            "row_sets_identical_offline_table_stage": True,
            "exact_pp": round(rs.gain(new), 4),
            "bootstrap_pp": boot,
            "control_original_pool": {"predictions_dropped": sum(len(v) for v in control.values()),
                                      "exact_pp": control_pp},
        }
    if arms["agree"]["control_original_pool"]["predictions_dropped"] != PUBLISHED["agree"]["predictions_dropped"]:
        raise ReadError("the original-pool control does not reproduce the published 66 drops")
    for label in ("agree", "wave_aa"):
        if round(arms[label]["control_original_pool"]["exact_pp"], 2) != PUBLISHED[label]["exact_pp"]:
            raise ReadError(f"the original-pool control does not reproduce the published {label} pp")
    return {
        "read_id": READ_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stage": {"id": DN.DELIVER_SCOPE_RULE_V1, "version": DN.DELIVER_SCOPE_RULE_V1_VERSION,
                  "min_pool_occurrences": DN.SCOPE_RULE_MIN_POOL_OCCURRENCES,
                  "untagged_share": DN.SCOPE_RULE_UNTAGGED_SHARE},
        "table": {"relpath": DN.SCOPE_RULE_TABLE_RELPATH, "sha256": table.sha256, "phrases": len(table.rows)},
        "pools": {"r5": {"relpath": TB.W3A.POOL[0], "sha256": r5_pool["sha256"], "exemplars": len(r5_exemplars)},
                  "original": {"relpath": ORIGINAL_POOL, "sha256": orig_pool["sha256"],
                               "exemplars": len(orig_exemplars)}},
        "arms": arms,
        "contacts": {k: 0 for k in ("model", "server", "tokenizer", "encoder", "embedder", "scorer_subprocess",
                                    "network", "gpu")},
    }


def strip_time(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"', "", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    args = parser.parse_args(argv)
    report = build(args)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    out_dir = Path(args.data_root) / ANALYSIS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(text, encoding="utf-8", newline="\n")
    content = hashlib.sha256(strip_time(text).encode("utf-8")).hexdigest()
    print(json.dumps({"report": str(out_dir / "report.json"), "content_sha256": content,
                      "table": report["table"], "arms": report["arms"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
