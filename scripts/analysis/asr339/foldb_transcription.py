#!/usr/bin/env python3
"""ASR339 qualification instrument: Qwen3-ASR (0.6B / 1.7B) transcription of the TRAIN Fold B roster on CPU.

Owner rulings 339 / 342 A. Package: docs/readiness/2026-10-19-slurp-asr339-foldb-transcription-v1/. This is an
INSTRUMENT: it measures tool quality (WER, gold-span containment, missed-slot and value-error containment) so the
root can compare Qwen3-ASR with the sealed Whisper large-v3 Fold B catalog (E5-0). It never answers, never
reaches the core and is never a delivery step. Zero core contacts; one ASR call per clip per model.

Subcommands:
    transcribe --model-id M --out DIR [--rows N] [--smoke | --full] [--port P]
        Calls the already-running CPU sidecar (scripts/flights/direct/asr_sidecar.sh start M). --smoke allows at
        most 4 rows and writes only under $SPEECHRL_DATA_DIR/diagnostics/ASR339-SMOKE/. --full runs the whole
        roster and refuses unless docs/exposure-ledger.md carries the registered row (see the package README).
    score --transcripts DIR [--containment] [--out FILE]
        WER and sentence-exact rate against the TRAIN reference sentence (scoring side, in memory only);
        with --containment also the all-gold span containment and the missed-slot / value-error containment on
        the NX-T R2b Fold B delivered column (the v3.0 lock form), the same definitions as the design note.

Text discipline: no utterance, transcript, reference or gold value is printed; transcripts live only under the
data root. Printed and persisted score output is counts, rates and hashes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATASET = "configs/dataset/slurp-speech-native-evo-fold-b-1080.json"
SCHEMA_CATALOG = "saea-asr339-transcript-catalog-v1"
SCHEMA_SCORE = "saea-asr339-foldb-score-v1"
SCHEMA_ROW = "saea-asr339-transcript-row-v1"
PACKAGE_ID = "slurp-asr339-foldb-transcription-v1"
LEDGER_ROW_ID = "SAEA-SLURP-ASR339-FOLD-B-V1"
SMOKE_MAX_ROWS = 4
DECODING = {"schema": "saea-asr339-decode-v1", "temperature": 0, "max_tokens": 256, "endpoint": "/v1/chat/completions",
            "audio_part": "input_audio", "text_part": None, "device": "cpu", "session_slots": 1}
OUTPUT_PREFIX = re.compile(r"^\s*language\s+[^<]*<asr_text>", re.S)
WHISPER_COMPARATOR = {"canon_wer": 0.152, "gold_span_containment": 0.7606, "missed_slot_containment": 0.625,
                      "value_error_containment": 0.367}


class InstrumentError(RuntimeError):
    pass


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical_json(doc) -> bytes:
    return (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def parse_asr_output(content: str) -> tuple:
    """Raw model content -> (status, transcript). The Qwen3-ASR form is ``language <L><asr_text><text>``."""
    text = OUTPUT_PREFIX.sub("", content or "", count=1).strip()
    if "<asr_text>" in text:
        text = text.split("<asr_text>")[-1].strip()
    return ("ok", text) if text else ("empty", "")


def roster_items(repo: Path = REPO) -> tuple:
    doc = json.loads((Path(repo) / DATASET).read_text(encoding="utf-8"))
    return doc, list(doc["items"])


def call_sidecar(port: int, audio_bytes: bytes, timeout: float = 600.0) -> dict:
    body = {"model": "asr", "temperature": DECODING["temperature"], "max_tokens": DECODING["max_tokens"],
            "messages": [{"role": "user", "content": [
                {"type": "input_audio", "input_audio": {"data": base64.b64encode(audio_bytes).decode("ascii"),
                                                         "format": "flac"}}]}]}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def read_peak_rss_kib(pid: int) -> int | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1])
    except OSError:
        return None
    return None


def check_ledger(repo: Path) -> None:
    ledger = (Path(repo) / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    rows = [ln for ln in ledger.splitlines() if LEDGER_ROW_ID in ln]
    if len(rows) != 1:
        raise InstrumentError(f"--full refused: exposure ledger must carry {LEDGER_ROW_ID} exactly once ({len(rows)})")
    row = rows[0].lower()
    if "consumed" in row and "| no" not in row and "consumed = no" not in row:
        raise InstrumentError("--full refused: the ledger row is not unconsumed")
    if "countersign" not in row:
        raise InstrumentError("--full refused: the ledger row carries no root countersignature")


def cmd_transcribe(a) -> int:
    data = Path(os.environ["SPEECHRL_DATA_DIR"])
    out = Path(a.out)
    smoke_root = (data / "diagnostics" / "ASR339-SMOKE").resolve()
    doc, items = roster_items()
    if a.smoke == a.full:
        raise InstrumentError("choose exactly one of --smoke and --full")
    if a.smoke:
        if a.rows is None or not 1 <= a.rows <= SMOKE_MAX_ROWS:
            raise InstrumentError(f"--smoke needs --rows 1..{SMOKE_MAX_ROWS}")
        if smoke_root not in out.resolve().parents and out.resolve() != smoke_root:
            raise InstrumentError("--smoke writes only under $SPEECHRL_DATA_DIR/diagnostics/ASR339-SMOKE/")
        items = items[: a.rows]
    else:
        check_ledger(REPO)
        if a.rows is not None:
            raise InstrumentError("--full runs the whole roster; --rows is a smoke option")
    session = json.loads((Path(a.session_root) / f"asr-sidecar-{a.model_id}" / "session.json").read_text())
    if session["model_id"] != a.model_id or session["device"] != "cpu":
        raise InstrumentError("sidecar session does not match the requested model or is not CPU")
    out.mkdir(parents=True, exist_ok=True)
    rows_path = out / "transcripts.jsonl"
    if rows_path.exists():
        raise InstrumentError(f"{rows_path} exists; one-shot semantics, never overwritten")
    peak = 0
    started = time.time()
    with rows_path.open("w", encoding="utf-8") as sink:
        for item in items:
            audio = (data / item["media_relpath"]).read_bytes()
            if sha256_bytes(audio) != item["audio_sha256"]:
                raise InstrumentError(f"audio hash differs from the roster for {item['sample_id']}")
            t0 = time.time()
            try:
                reply = call_sidecar(a.port or session["port"], audio)
                content = reply["choices"][0]["message"]["content"]
                usage = reply.get("usage") or {}
                status, text = parse_asr_output(content)
            except Exception as error:  # a failed contact is a recorded fact, never a silent retry
                status, text, usage = f"error:{type(error).__name__}", "", {}
            seconds = time.time() - t0
            peak = max(peak, read_peak_rss_kib(session["pid"]) or 0)
            sink.write(json.dumps({"schema": SCHEMA_ROW, "sample_id": item["sample_id"], "status": status,
                                   "transcript": text, "audio_sha256": item["audio_sha256"],
                                   "audio_seconds": item["audio_seconds"], "asr_seconds": round(seconds, 3),
                                   "completion_tokens": usage.get("completion_tokens"),
                                   "prompt_tokens": usage.get("prompt_tokens")}, sort_keys=True) + "\n")
            sink.flush()
    catalog = {"schema": SCHEMA_CATALOG, "package": PACKAGE_ID, "model_id": a.model_id,
               "lock_entry": session["lock_entry"], "lock_revision": session["lock_revision"],
               "model_sha256": session["model"]["sha256"], "mmproj_sha256": session["mmproj"]["sha256"],
               "build_commit": session["build_commit"], "device": "cpu", "sidecar_argv": session["argv"],
               "split_identity_hash": doc["split_identity_hash"], "roster_dataset": DATASET,
               "rows": len(items), "transcripts_sha256": sha256_file(rows_path),
               "decoding": DECODING, "decoding_sha256": sha256_bytes(canonical_json(DECODING)),
               "wall_seconds": round(time.time() - started, 2),
               "server_peak_rss_kib": peak or None, "created_at": datetime.now(timezone.utc).isoformat(),
               "mode": "smoke" if a.smoke else "full"}
    (out / "catalog.json").write_bytes(canonical_json(catalog))
    print(json.dumps({k: catalog[k] for k in ("model_id", "rows", "wall_seconds", "server_peak_rss_kib", "mode")}))
    return 0


# ---------------------------------------------------------------------------------------------- scoring


def load_rows(directory: Path) -> tuple:
    catalog = json.loads((Path(directory) / "catalog.json").read_text(encoding="utf-8"))
    path = Path(directory) / "transcripts.jsonl"
    if sha256_file(path) != catalog["transcripts_sha256"]:
        raise InstrumentError("transcripts.jsonl differs from its catalog pin")
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return catalog, rows


def _imp(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def wer_summary(refs: dict, hyps: dict, canon, edit) -> dict:
    err = n = exact = 0
    for sid, hyp in hyps.items():
        ref = canon(refs[sid])
        h = canon(hyp)
        e = edit(ref, h)
        err += e
        n += len(ref)
        exact += int(e == 0)
    return {"rows": len(hyps), "ref_tokens": n, "edit_errors": err, "canon_wer": round(err / n, 4) if n else None,
            "sentence_exact_rate": round(exact / len(hyps), 4) if hyps else None}


def cmd_score(a) -> int:
    sys.path.insert(0, str(REPO / "src"))
    sys.dont_write_bytecode = True
    data = Path(os.environ["SPEECHRL_DATA_DIR"])
    lock_path = Path(os.environ.get("SAEA_ASR_LOCK", "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"))
    E5 = _imp(REPO / "scripts/analysis/e5_transcript_consistency_read.py", "e5read")
    S2 = _imp(REPO / "scripts/analysis/slurp_s2a1_recall_ceiling.py", "s2a1")
    catalog, rows = load_rows(Path(a.transcripts))
    hyps = {r["sample_id"]: (r["transcript"] if r["status"] == "ok" else "") for r in rows}
    if any(":test:" in s or ":devel:" in s for s in hyps):
        raise InstrumentError("only TRAIN rows may be scored")
    refs, _ = S2.load_reference_sentences(lock_path, data)
    report = {"schema": SCHEMA_SCORE, "package": PACKAGE_ID, "model_id": catalog["model_id"],
              "catalog_transcripts_sha256": catalog["transcripts_sha256"], "mode": catalog["mode"],
              "status_counts": dict(Counter(r["status"] for r in rows)),
              "wer": wer_summary(refs, hyps, E5.canon_tokens, E5.token_edit),
              "asr_seconds_per_clip": round(sum(r["asr_seconds"] for r in rows) / len(rows), 3),
              "audio_seconds_per_clip": round(sum(r["audio_seconds"] for r in rows) / len(rows), 3),
              "whisper_comparator": WHISPER_COMPARATOR}
    del refs
    if a.containment:
        report["containment"] = containment_block(E5, hyps, lock_path, data)
    text = canonical_json(report)
    if a.out:
        Path(a.out).write_bytes(text)
    print(json.dumps({"model_id": report["model_id"], "wer": report["wer"],
                      "asr_seconds_per_clip": report["asr_seconds_per_clip"],
                      "containment": report.get("containment")}, sort_keys=True))
    return 0


def containment_block(E5, hyps: dict, lock_path: Path, data: Path) -> dict:
    """Gold-span containment (all gold) and the missed-slot / value-error containment on the v3.0 lock's Fold B
    delivered column (NX-T R2b arm budget-3072), the design note's definitions. Aggregates only."""
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

    G = _imp(REPO / "scripts/analysis/gap_to_sota/gap_decomposition.py", "gapdec")
    lock = G.load_lock(lock_path)
    train = G.load_slurp_split(lock, data, "train", workers=4)
    gold_all = {}
    for r in train:
        G.guard(r.sample_id)
        gold_all[r.sample_id] = {"intent": f"{r.scenario}_{r.action}", "scenario": r.scenario, "utt": r.utterance_id,
                                 "ents": tuple(SlotEntity(type=e.type, filler=e.filler) for e in r.entities)}
    del train
    pop = G.load_pop("FOLDB", G.POPS["FOLDB"], gold_all)
    tx = {s: {"status": "ok", "canon": E5.canon_tokens(t)} for s, t in hyps.items()}
    all_gold = {"items": 0, "contained": 0}
    tally = Counter()
    for sid in sorted(hyps):
        row = pop["rows"][sid]
        for g in row["gold"]:
            all_gold["items"] += 1
            all_gold["contained"] += int(E5.contiguous(E5.canon_tokens(g.filler), tx[sid]["canon"]))
        for it in entity_items(row["gold"], row["pred"]):
            kind = it["kind"]
            if kind == "MISSING":
                cls = "miss"
            elif kind in ("FORMAT", "BOUNDARY", "NEAR", "WRONG-VALUE"):
                cls = "val"
            else:
                continue
            tally[f"{cls}_items"] += 1
            tally[f"{cls}_contained"] += int(E5.contiguous(E5.canon_tokens(row["gold"][it["gold_index"]].filler),
                                                          tx[sid]["canon"]))
    rate = lambda c, n: round(c / n, 4) if n else None  # noqa: E731
    return {"rows": len(hyps), "population_run": G.POPS["FOLDB"]["run"],
            "all_gold": {**all_gold, "rate": rate(all_gold["contained"], all_gold["items"])},
            "missed_slot": {"items": tally["miss_items"], "contained": tally["miss_contained"],
                            "rate": rate(tally["miss_contained"], tally["miss_items"])},
            "value_error": {"items": tally["val_items"], "contained": tally["val_contained"],
                            "rate": rate(tally["val_contained"], tally["val_items"])}}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("transcribe")
    t.add_argument("--model-id", required=True, choices=("qwen3-asr-0.6b", "qwen3-asr-1.7b"))
    t.add_argument("--out", required=True)
    t.add_argument("--rows", type=int)
    t.add_argument("--smoke", action="store_true")
    t.add_argument("--full", action="store_true")
    t.add_argument("--port", type=int)
    t.add_argument("--session-root", default=os.path.join(os.environ.get("SPEECHRL_DATA_DIR", "."), "serving"))
    s = sub.add_parser("score")
    s.add_argument("--transcripts", required=True)
    s.add_argument("--containment", action="store_true")
    s.add_argument("--out")
    a = p.parse_args(argv)
    try:
        return {"transcribe": cmd_transcribe, "score": cmd_score}[a.cmd](a)
    except InstrumentError as error:
        print(f"asr339_foldb: REFUSED: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
