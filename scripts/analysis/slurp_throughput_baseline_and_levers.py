#!/usr/bin/env python3
"""SLURP throughput baseline and levers (owner decision 140, 2026-09-27).

Zero model, server, encoder and scorer contacts. Reads only: the sealed ROLL-2
trace, the resident np4 serving session's own ``server.log`` and
``monitor.jsonl`` (plus the three other 2026-09-26 sessions' monitors for the
day accounting), ``/home/chao/batch-driver.out`` (read-only), and the vocab-only
``llama-tokenize`` binary the 2026-09-26 global-state audit already used. It
never prints or persists utterance text, transcripts, gold, knowledge bodies,
model output or sample identifiers -- token counts, timings, rates, hashes and
row indices only. Output: one receipt JSON, byte-reproducible apart from
``generated_at`` (and the tokenizer-call count, which depends on the cache).

Usage (WSL, speechrl venv or system python3, stdlib only):

    PYTHONDONTWRITEBYTECODE=1 python3 scripts/analysis/slurp_throughput_baseline_and_levers.py \
        --out docs/receipts/slurp-throughput-baseline-and-levers-v1.json
"""
from __future__ import annotations
import os

import argparse
import collections
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
RUN_ID = "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1"
ATTEMPT = "attempt-slurp-native-stage3-roll-2-fold-a-v1-generation"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
DAY_SESSIONS = (
    "serving-slurp-system-batch001-np2-v1",
    "serving-slurp-system-summary001-np1-v1",
    "serving-slurp-system-memory-batch002-np2-v1",
    SESSION,
)
DRIVER_OUT = Path("/home/chao/batch-driver.out")
TOKENIZE = Path("/home/chao/llama.cpp/build/bin/llama-tokenize")
GGUF = Path("/home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf")
SCHEMA = Path("docs/receipts/knowledge/slurp-intent-slot-schema-v1.json")
PRIOR_VRAM_POINTS = [(36864, 19776), (65536, 21272), (98304, 22976)]  # 2026-09-19 receipt, nvidia-smi MiB
DAY = "2026-09-26"
ROLE_ORDER = ("perception", "solver", "reviewer", "planner")
BUSY_UTIL = 5.0

# --------------------------------------------------------------------------- helpers

def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def parse_iso(text: str) -> float:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def stats(values, digits=1):
    values = [v for v in values if v is not None]
    if not values:
        return None
    s = sorted(values)
    q = lambda p: s[min(len(s) - 1, int(p * len(s)))]
    return {
        "n": len(s), "mean": round(statistics.fmean(s), digits), "p50": round(q(0.5), digits),
        "p90": round(q(0.9), digits), "max": round(s[-1], digits), "sum": round(sum(s), digits),
    }


def store_of(evidence_id: str) -> str:
    # "<store>::<kind>:<name>" (e.g. slot-contracts::slot-contract:app_name) -> <store>
    m = re.match(r"([^:]+)::", evidence_id)
    return m.group(1) if m else "other"


# --------------------------------------------------------------------------- A. server log

TS_RE = re.compile(r"^(\d+)\.(\d\d)\.(\d{3})\.(\d{3}) ([IWE]) (.*)$")
SLOT_RE = re.compile(r"id\s+(\d+) \| task\s+(-?\d+) \| (.*)$")
PROMPT_RE = re.compile(r"prompt eval time =\s+([\d.]+) ms /\s+(\d+) tokens")
EVAL_RE = re.compile(r"\beval time =\s+([\d.]+) ms /\s+(\d+) tokens")
TOTAL_RE = re.compile(r"total time =\s+([\d.]+) ms /\s+(\d+) tokens")
RELEASE_RE = re.compile(r"stop processing: n_tokens = (\d+), truncated = (\d)")
MTMD_RE = re.compile(r"speech feature chunk, n_tokens = (\d+)")
NPAST_RE = re.compile(r"need to evaluate at least 1 token .*\(n_past = (\d+), task.n_tokens\(\) = (\d+)\)")


def parse_server_log(path: Path, segment_start_utc: float):
    """Parse the LAST server lifetime in an appended server.log into tasks."""
    starts = []
    with path.open("rb") as fh:
        for index, raw in enumerate(fh):
            if b"log_info: verbosity" in raw:
                starts.append(index)
    last = starts[-1]
    tasks: dict[tuple[int, int], dict] = {}
    idle_marks = []
    device_line = None
    with path.open("rb") as fh:
        for index, raw in enumerate(fh):
            if index < last:
                continue
            line = raw.decode("utf-8", "replace").rstrip("\n")
            m = TS_RE.match(line)
            if not m:
                continue
            t = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 1e3 + int(m.group(4)) / 1e6
            body = m.group(6)
            if device_line is None and "CUDA0" in body and "MiB free" in body:
                device_line = body.strip()
            if "all slots are idle" in body:
                idle_marks.append(t)
                continue
            sm = SLOT_RE.search(body)
            if not sm:
                continue
            slot, task, rest = int(sm.group(1)), int(sm.group(2)), sm.group(3)
            if task < 0:
                continue
            rec = tasks.setdefault((slot, task), {"slot": slot, "task": task})
            if "processing task" in rest:
                rec["t_launch"] = t
            elif (mm := MTMD_RE.search(rest)):
                rec["mtmd_tokens"] = rec.get("mtmd_tokens", 0) + int(mm.group(1))
            elif (pm := PROMPT_RE.search(rest)):
                rec["prompt_ms"], rec["prompt_n"] = float(pm.group(1)), int(pm.group(2))
            elif (em := EVAL_RE.search(rest)) and "prompt" not in rest:
                rec["eval_ms"], rec["eval_n"] = float(em.group(1)), int(em.group(2))
            elif (tm := TOTAL_RE.search(rest)):
                rec["total_ms"], rec["total_n"] = float(tm.group(1)), int(tm.group(2))
            elif (rm := RELEASE_RE.search(rest)):
                rec["t_release"], rec["n_ctx_release"], rec["truncated"] = t, int(rm.group(1)), int(rm.group(2))
            elif (nm := NPAST_RE.search(rest)):
                rec["full_hit_n_past"] = int(nm.group(1))
    out = []
    for rec in tasks.values():
        if "t_launch" not in rec or "t_release" not in rec:
            continue
        rec["t_launch_utc"] = segment_start_utc + rec["t_launch"]
        rec["t_release_utc"] = segment_start_utc + rec["t_release"]
        rec.setdefault("prompt_n", 0); rec.setdefault("prompt_ms", 0.0)
        rec.setdefault("eval_n", 0); rec.setdefault("eval_ms", 0.0)
        rec.setdefault("mtmd_tokens", 0)
        rec["full_prompt"] = rec["n_ctx_release"] - rec["eval_n"]
        rec["cached"] = rec["full_prompt"] - rec["prompt_n"]
        out.append(rec)
    out.sort(key=lambda r: (r["t_launch"], r["slot"]))
    return out, [segment_start_utc + t for t in idle_marks], device_line, len(starts)


# --------------------------------------------------------------------------- B. trace

def extract_trace(path: Path):
    """One streaming pass. Per contact: numbers, hashes, class sizes and the
    byte-prefix relation to the previous contact on the same slot."""
    contacts: dict[str, dict] = {}
    prev_parts: dict[int, list] = {}           # slot -> previous contact's parts [(cls, text)]
    prev_fid: dict[int, int] = {}
    order_ok = True
    with path.open("rb") as fh:
        for raw in fh:
            head = raw[:200]
            if b'"MODEL_REQUEST"' not in head and b'"MODEL_RESPONSE"' not in head and b'"COST"' not in head and b'"USE"' not in head:
                continue
            rec = json.loads(raw)
            ch = rec["channel"]
            fid = rec["record_id"].split("/")[0]
            if not fid.startswith("flight-") or not fid[7:].isdigit():
                continue  # sample-level ORG/SUPPLY/USE records are not contacts
            c = contacts.setdefault(fid, {"fid": fid, "seq": int(fid[7:])})
            if ch == "COST":
                c["latency_s"] = rec["payload"]["latency_seconds"]
            elif ch == "MODEL_RESPONSE":
                u = rec["payload"]["usage"]
                c["prompt_tokens"], c["completion_tokens"] = u["prompt_tokens"], u["completion_tokens"]
                text = rec["payload"].get("text") or ""
                c["response_chars"] = len(text)
                c["response_compact_chars"], c["response_dup_value_chars"], c["response_json_ok"] = _compaction(text)
            elif ch == "USE":
                c["use_role"] = rec["payload"]["use_role_id"]
            elif ch == "MODEL_REQUEST":
                pl = rec["payload"]["payload"]
                slot = int(pl["decoding_params"]["id_slot"])
                hist = pl["history"]
                env = json.loads(hist[-1]["content"])
                role = env["role_id"]
                cid = env["contact_id"]                # <policy>:<role>:<index>:<sample>
                cparts = cid.split(":")
                query = env["messages"][1]["content"]
                limits = query.split("\n\nNative episode limits: ", 1)
                system_text = pl["task_instruction"]
                parts = [("system", system_text), ("packet", "PKT:" + pl["speech_feature_parts"][0]["sha256"])]
                ev_meta = []
                for item in pl["supplied_evidence"]:
                    text = f"[evidence {item['evidence_id']}] {item['content']}"
                    parts.append(("evidence:" + store_of(item["evidence_id"]), text))
                    ev_meta.append((item["evidence_id"], len(item["content"])))
                states = []
                for item in hist[:-1]:
                    text = f"[agent state {item['state_id']} kind={item['state_kind']}] {item['content']}"
                    parts.append(("state:" + item["state_kind"], text))
                    states.append((item["state_kind"], len(item["state_id"]), len(item["content"]), item["content"]))
                parts.append(("query", query))
                # byte-prefix relation to the previous contact on this slot
                # (the packet is an atomic non-text part: matched by sha, 0 chars)
                pp = prev_parts.get(slot)
                lcp_parts = 0; lcp_chars = 0; first_diff = None; same_set_chars = 0
                if pp is not None:
                    prev_shas = {sha(t) for _, t in pp}
                    same_set_chars = sum(len(t) for cls, t in parts if cls != "packet" and sha(t) in prev_shas)
                    while lcp_parts < min(len(pp), len(parts)) and pp[lcp_parts][1] == parts[lcp_parts][1]:
                        if parts[lcp_parts][0] != "packet":
                            lcp_chars += len(parts[lcp_parts][1])
                        lcp_parts += 1
                    if lcp_parts < len(parts):
                        first_diff = parts[lcp_parts][0]
                        if lcp_parts < len(pp):
                            a, b = pp[lcp_parts][1], parts[lcp_parts][1]
                            k = 0
                            for x, y in zip(a, b):
                                if x != y: break
                                k += 1
                            lcp_chars += k
                    else:
                        first_diff = "none"
                    if prev_fid.get(slot, -1) > int(fid.split("-")[1]):
                        order_ok = False
                prev_parts[slot] = parts
                prev_fid[slot] = int(fid.split("-")[1])
                total_chars = sum(len(t) for cls, t in parts if cls != "packet")
                cands = []
                for kind, _sid, _n, content in states:
                    if kind == "phase:perception":
                        try:
                            cands = [x.get("intent_id") for x in json.loads(content).get("candidates", [])]
                        except Exception:
                            cands = []
                query_body = limits[0]
                TEXTS.setdefault(sha(system_text), system_text)
                TEXTS.setdefault(sha(query_body), query_body)
                if len(limits) == 2:
                    lim_text = "\n\nNative episode limits: " + limits[1]
                    TEXTS.setdefault(sha(lim_text), lim_text)
                card_shas = []
                for cls, t in parts:
                    if cls == "evidence:slot-contracts":
                        TEXTS.setdefault(sha(t), t); card_shas.append(sha(t))
                for i, _ in ev_meta:
                    LABELS.setdefault(i, f"[evidence {i}] ")
                per_store = collections.defaultdict(int)
                for cls, t in parts:
                    if cls.startswith("evidence:"):
                        per_store[cls.split(":", 1)[1]] += len(t)
                c.update({
                    "slot": slot, "role": role,
                    "row_key": sha(":".join(cparts[3:]))[:16],
                    "system_sha": sha(system_text), "system_chars": len(system_text),
                    "n_history": len(hist) - 1,
                    "n_evidence": len(ev_meta),
                    "evidence_chars": sum(n for _, n in ev_meta),
                    "label_chars": sum(len(f"[evidence {i}] ") for i, _ in ev_meta),
                    "state_label_chars": sum(len(f"[agent state {'x'*sid} kind={kind}] ") for kind, sid, _n, _c in states),
                    "state_chars": sum(n for _k, _s, n, _c in states),
                    "query_sha": sha(query_body), "limits_sha": sha(lim_text) if len(limits) == 2 else None,
                    "total_chars": total_chars,
                    "lcp_parts": lcp_parts, "lcp_chars": lcp_chars, "first_diff": first_diff,
                    "same_set_chars": same_set_chars, "has_prev": pp is not None,
                    "candidate_intents": cands,
                    "card_shas": card_shas,
                    "card_ids": [i for i, _ in ev_meta if store_of(i) == "slot-contracts"],
                    "label_ids": [i for i, _ in ev_meta],
                    "evidence_chars_by_store": dict(per_store),
                    "ws_chars": sum(len(m.group(0)) - 1 for cls, t in parts if cls.startswith("evidence:") for m in re.finditer(r"[ \t]{2,}|\n{3,}", t)),
                    "dup_line_chars": _dup_line_chars([t for cls, t in parts if cls.startswith("evidence:")]),
                })
                c["dup_heading_chars"], c["dup_content_chars"], c["dup_distinct_lines"] = _dup_line_census(
                    [t for cls, t in parts if cls.startswith("evidence:")])
    return contacts, order_ok


TEXTS: dict[str, str] = {}    # sha -> text, for the few exact token counts (system, queries, limits, cards)
LABELS: dict[str, str] = {}   # evidence_id -> "[evidence <id>] "


def _compaction(text: str):
    """(compact-JSON chars, chars of string values repeated beyond their first
    occurrence, parsed?) for one model response; the text is not retained."""
    try:
        obj = json.loads(text)
    except Exception:
        return len(text), 0, False
    compact = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    seen = collections.Counter()

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str) and len(o) >= 8:
            seen[o] += 1
    walk(obj)
    dup = sum(len(k) * (n - 1) for k, n in seen.items() if n > 1)
    return len(compact), dup, True


def _dup_line_census(texts: list[str]):
    """Lines that recur across DIFFERENT evidence items of one contact, counted
    beyond their first occurrence: (heading-like chars, content chars,
    distinct repeated lines). Heading-like = ends with ':' or <= 40 chars."""
    first_seen: dict[str, int] = {}
    heading = content = 0
    distinct = set()
    for index, text in enumerate(texts):
        for line in set(text.split("\n")):
            line = line.strip()
            if len(line) < 12:
                continue
            if line in first_seen and first_seen[line] != index:
                distinct.add(line)
                if line.endswith(":") or len(line) <= 40:
                    heading += len(line)
                else:
                    content += len(line)
            else:
                first_seen.setdefault(line, index)
    return heading, content, len(distinct)


def _dup_line_chars(texts: list[str]) -> int:
    """Characters of lines that recur across DIFFERENT evidence items of one
    contact, counted beyond their first occurrence (repeated ontology text)."""
    first_seen: dict[str, int] = {}
    dup = 0
    for index, text in enumerate(texts):
        for line in set(text.split("\n")):
            line = line.strip()
            if len(line) < 12:
                continue
            if line in first_seen and first_seen[line] != index:
                dup += len(line)
            else:
                first_seen.setdefault(line, index)
    return dup


# --------------------------------------------------------------------------- tokenizer (vocab only)

class Tokenizer:
    def __init__(self, scratch: Path, cache_path: Path, workers: int):
        self.scratch = scratch; self.cache_path = cache_path; self.workers = workers
        self.cache: dict[str, int] = {}
        if cache_path.exists():
            self.cache = {k: int(v) for k, v in json.loads(cache_path.read_text(encoding="utf-8")).items()}
        self.calls = 0

    def _count(self, key: str, text: str) -> int:
        self.scratch.mkdir(parents=True, exist_ok=True)
        path = self.scratch / (key[:24] + ".txt")
        path.write_bytes(text.encode("utf-8"))
        argv = [str(TOKENIZE), "-m", str(GGUF), "-f", str(path), "--no-bos", "--no-escape", "--show-count", "--log-disable", "--ids"]
        result = subprocess.run(argv, check=True, capture_output=True, text=True)
        path.unlink()
        self.calls += 1
        for line in result.stdout.splitlines():
            if line.startswith("Total number of tokens:"):
                return int(line.split(":")[1].strip())
        raise RuntimeError("no token count for " + key)

    def measure(self, texts: dict[str, str]) -> dict[str, int]:
        keys = sorted(k for k in texts if k not in self.cache)
        if keys:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                counts = list(pool.map(lambda k: self._count(k, texts[k]), keys))
            self.cache.update(zip(keys, counts))
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cache, indent=0, sort_keys=True), encoding="utf-8")
        return {k: self.cache[k] for k in texts}


# --------------------------------------------------------------------------- C. join

def join(contacts: dict, tasks: list, arm_start: float, arm_exit: float):
    window = [t for t in tasks if arm_start - 5 <= t["t_launch_utc"] <= arm_exit + 5]
    by_slot_tasks = collections.defaultdict(list)
    for t in window:
        by_slot_tasks[t["slot"]].append(t)
    by_slot_contacts = collections.defaultdict(list)
    for c in contacts.values():
        if "slot" in c:
            by_slot_contacts[c["slot"]].append(c)
    joined = []; skipped = 0; unmatched = 0; offsets = collections.Counter()
    for slot, cs in by_slot_contacts.items():
        cs.sort(key=lambda c: c["seq"])
        ts = by_slot_tasks[slot]
        j = 0
        for c in cs:
            found = None
            for look in range(j, min(j + 4, len(ts))):
                t = ts[look]
                if abs(t["full_prompt"] - c["prompt_tokens"]) <= 2 and abs(t["eval_n"] - c["completion_tokens"]) <= 1:
                    found = look; break
            if found is None:
                unmatched += 1; continue
            skipped += found - j
            t = ts[found]; j = found + 1
            offsets[(t["full_prompt"] - c["prompt_tokens"], t["eval_n"] - c["completion_tokens"])] += 1
            c["srv"] = t
            joined.append(c)
    return joined, window, {"unmatched_contacts": unmatched, "skipped_tasks": skipped,
                            "offset_histogram": {f"{k[0]},{k[1]}": v for k, v in sorted(offsets.items())}}


# --------------------------------------------------------------------------- D. wall-clock sweep

def sweep(window_tasks: list, t0: float, t1: float):
    """Union-of-intervals decomposition of the contact window, plus a decode
    batch-scaling table: for every (slots prefilling, slots decoding) state its
    duration and the tokens decoded in it (each request is taken to decode at
    its own constant rate eval_n / eval_ms over its decode interval)."""
    events = []  # (time, kind, delta, rate)
    for t in window_tasks:
        rel = t["t_release_utc"]; ev_s = t["eval_ms"] / 1000; pf_s = t["prompt_ms"] / 1000
        pf0, pf1 = rel - ev_s - pf_s, rel - ev_s
        rate = t["eval_n"] / ev_s if ev_s > 0 else 0.0
        events += [(max(t["t_launch_utc"], t0), "busy", 1, 0.0), (min(rel, t1), "busy", -1, 0.0),
                   (max(pf0, t0), "pf", 1, 0.0), (min(pf1, t1), "pf", -1, 0.0),
                   (max(pf1, t0), "dec", 1, rate), (min(rel, t1), "dec", -1, -rate)]
    events.sort(key=lambda e: (e[0], e[1]))
    acc = collections.Counter(); busy = pf = dec = 0; dec_rate = 0.0; last = t0
    conc_pf = collections.Counter(); conc_dec_only = collections.Counter()
    state_dur = collections.Counter(); state_tok = collections.Counter()
    for time, kind, delta, rate in events:
        dt = max(0.0, time - last)
        if pf > 0:
            acc["prefill_active"] += dt; conc_pf[pf] += dt
        elif dec > 0:
            acc["decode_only"] += dt; conc_dec_only[dec] += dt
        elif busy > 0:
            acc["slot_busy_no_compute"] += dt
        else:
            acc["all_idle"] += dt
        acc["slot_seconds_busy"] += dt * busy
        key = (min(pf, 4), min(dec, 4))
        state_dur[key] += dt; state_tok[key] += dt * dec_rate
        last = time
        if kind == "busy": busy += delta
        elif kind == "pf": pf += delta
        else: dec += delta; dec_rate += rate
    acc["all_idle"] += max(0.0, t1 - last)
    scaling = []
    for key in sorted(state_dur):
        if state_dur[key] < 30:
            continue
        agg = state_tok[key] / state_dur[key]
        scaling.append({"slots_prefilling": key[0], "slots_decoding": key[1], "seconds": round(state_dur[key], 1),
                        "decoded_tokens": round(state_tok[key]), "aggregate_decode_tok_s": round(agg, 1),
                        "per_slot_decode_tok_s": round(agg / key[1], 1) if key[1] else None})
    return ({k: round(v, 1) for k, v in acc.items()}, {str(k): round(v, 1) for k, v in sorted(conc_pf.items())},
            {str(k): round(v, 1) for k, v in sorted(conc_dec_only.items())}, scaling)


# --------------------------------------------------------------------------- E. day accounting

DRIVER_LINE = re.compile(r"^(\d\d):(\d\d):(\d\d) (\S+)(?: (.*))?$")
EXIT_LINE = re.compile(r"^driver exit (\d+) (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)$")
LOGSTAMP = re.compile(r"(\d{8}T\d{6}Z)\.log")


def parse_driver(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    anchors = {}
    for i, line in enumerate(lines):
        m = EXIT_LINE.match(line)
        if m:
            anchors[i] = parse_iso(m.group(2)); continue
        s = LOGSTAMP.search(line)
        dm = DRIVER_LINE.match(line)
        if s and dm:
            anchors[i] = datetime.strptime(s.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp()
    events = []
    anchor_idx = sorted(anchors)
    for i, line in enumerate(lines):
        m = EXIT_LINE.match(line)
        if m:
            events.append((anchors[i], "driver-exit", m.group(1))); continue
        dm = DRIVER_LINE.match(line)
        if not dm:
            continue
        prev = [a for a in anchor_idx if a <= i]
        nxt = [a for a in anchor_idx if a >= i]
        ref_i = prev[-1] if prev else nxt[0]
        ref = datetime.fromtimestamp(anchors[ref_i], timezone.utc)
        hms = timedelta(hours=int(dm.group(1)), minutes=int(dm.group(2)), seconds=int(dm.group(3)))
        cand = datetime.combine(ref.date(), datetime.min.time(), tzinfo=timezone.utc) + hms
        if prev and cand < ref - timedelta(hours=1):
            cand += timedelta(days=1)
        if not prev and cand > ref + timedelta(hours=1):
            cand -= timedelta(days=1)
        events.append((cand.timestamp(), dm.group(4), dm.group(5) or ""))
    events.sort(key=lambda e: e[0])
    return events


def driver_states(events, t0: float, t1: float):
    """Intervals (start, end, state) covering [t0, t1), from the driver's own
    event lines. 'between-drivers:stopped-waiting' = after a STOP or a killed
    driver until a human starts the next one; 'between-drivers:nothing-registered'
    = after a clean driver-done until the next driver-start."""
    spans = []
    state = "between-drivers:nothing-registered"; since = None; short = "step"
    for time, kind, detail in events:
        if since is not None and time > since:
            spans.append((since, time, state))
        since = time
        if kind == "driver-start":
            state = "driver-idle"
        elif kind == "step-start":
            m = re.search(r'"short":"([^"]+)"', detail); short = m.group(1) if m else "step"; state = "prelaunch+smoke"
        elif kind == "arm-start":
            state = "arm:" + short
        elif kind == "arm-exit":
            state = "inspect+seal"
        elif kind == "step-done":
            state = "driver-idle"
        elif kind == "STOP":
            state = "between-drivers:stopped-waiting"
        elif kind == "driver-exit":
            if state.startswith("arm:") or detail != "0":
                state = "between-drivers:stopped-waiting"
            elif not state.startswith("between-drivers"):
                state = "between-drivers:nothing-registered"
        elif kind == "driver-done":
            state = "between-drivers:nothing-registered"
    if since is not None and t1 > since:
        spans.append((since, t1, state))
    return [(max(a, t0), min(b, t1), s) for a, b, s in spans if min(b, t1) > max(a, t0)]


def day_accounting(t0: float, t1: float, driver_events, session_windows):
    minutes = int((t1 - t0) // 60)
    busy = [None] * minutes  # None = unmonitored, False idle, True busy
    for name in DAY_SESSIONS:
        mpath = DATA / "serving" / name / "monitor.jsonl"
        if not mpath.exists():
            continue
        with mpath.open("rb") as fh:
            for raw in fh:
                if b'"2026-09-2' not in raw:
                    continue
                try:
                    j = json.loads(raw)
                except Exception:
                    continue
                ts = j.get("sampled_at")
                if ts is None or not (t0 <= ts < t1):
                    continue
                k = int((ts - t0) // 60)
                u = (j.get("gpu") or {}).get("utilization_percent") or 0.0
                b = (j.get("slots") or {}).get("busy") or 0
                flag = (u >= BUSY_UTIL) or (b > 0)
                busy[k] = bool(busy[k]) or flag if busy[k] is not None else flag
    spans = driver_states(driver_events, t0, t1)
    table = collections.defaultdict(lambda: collections.Counter())
    arm_minutes = collections.Counter()
    for k in range(minutes):
        tm = t0 + k * 60 + 30
        state = next((s for a, b, s in spans if a <= tm < b), "unknown")
        cell = "unmonitored" if busy[k] is None else ("busy" if busy[k] else "idle")
        group = "in-flight" if state.startswith("arm:") else state
        table[group][cell] += 1
        if state.startswith("arm:"):
            arm_minutes[state] += 1
    # session residency
    resident = 0
    for k in range(minutes):
        tm = t0 + k * 60 + 30
        if any(a <= tm < b for a, b in session_windows):
            resident += 1
    return {k: dict(v) for k, v in sorted(table.items())}, dict(arm_minutes), resident, minutes, [(iso(a), iso(b), s) for a, b, s in spans]


# --------------------------------------------------------------------------- F. geometry

def fit_line(points):
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    slope = sum((x - mx) * (y - my) for x, y in points) / sum((x - mx) ** 2 for x in xs)
    return slope, my - slope * mx


def session_idle_memory(name: str, day_only: bool):
    p = DATA / "serving" / name / "monitor.jsonl"
    first = None; peak = 0.0; idle_vals = []
    with p.open("rb") as fh:
        for raw in fh:
            if day_only and b'"2026-09-26T1' not in raw and b'"2026-09-27T0' not in raw:
                continue
            try:
                j = json.loads(raw)
            except Exception:
                continue
            m = (j.get("gpu") or {}).get("memory_used_mib")
            if not m:
                continue
            peak = max(peak, m)
            if first is None:
                first = m
            if ((j.get("slots") or {}).get("busy") or 0) == 0:
                idle_vals.append(m)
    return {"first_after_load_mib": first, "peak_mib": peak, "idle_min_mib": min(idle_vals) if idle_vals else None,
            "idle_median_mib": statistics.median(idle_vals) if idle_vals else None}


def geometry(device_line: str | None):
    sessions = {}
    for name in DAY_SESSIONS:
        sj = json.loads((DATA / "serving" / name / "session.json").read_text(encoding="utf-8"))
        argv = (sj.get("identity") or {}).get("server_argv") or []
        c = int(argv[argv.index("-c") + 1]); np_ = int(argv[argv.index("-np") + 1])
        mem = session_idle_memory(name, name == SESSION)
        sessions[name] = {"total_context": c, "slots": np_, "slot_tokens": c // np_, **mem}
    free_at_load = None
    if device_line:
        m = re.search(r"\((\d+) MiB, (\d+) MiB free\)", device_line)
        if m:
            free_at_load = int(m.group(2)); total = int(m.group(1))
    day_points = [(v["total_context"], v["first_after_load_mib"]) for v in sessions.values() if v["first_after_load_mib"]]
    slope_day, icpt_day = fit_line(day_points) if len({p[0] for p in day_points}) > 1 else (None, None)
    slope_all, icpt_all = fit_line(day_points + PRIOR_VRAM_POINTS)
    kib_q8 = slope_all * 1024
    kib_q4 = kib_q8 * 18 / 34
    peak_np4 = sessions[SESSION]["peak_mib"]
    rows = []
    for label, slots, slot_tokens in (("np4 x 24,576 (as flown)", 4, 24576), ("np5 x 24,576", 5, 24576), ("np6 x 24,576", 6, 24576),
                                      ("np8 x 24,576", 8, 24576), ("np4 x 32,768", 4, 32768), ("np6 x 32,768", 6, 32768)):
        total_ctx = slots * slot_tokens
        for kv_label, kib in (("q8_0", kib_q8), ("q4_0 (derived)", kib_q4)):
            est = icpt_all + total_ctx * kib / 1024
            rows.append({"geometry": label, "kv_type": kv_label, "total_context": total_ctx,
                         "vram_mib_estimated": round(est), "fits_free_at_load": bool(free_at_load and est <= free_at_load),
                         "margin_mib_vs_free_at_load": round(free_at_load - est) if free_at_load else None})
    return {"device_line": device_line, "free_at_load_mib": free_at_load, "sessions": sessions,
            "fit_day_only": {"kib_per_token": round(slope_day * 1024, 2) if slope_day else None, "intercept_mib": round(icpt_day) if icpt_day else None, "points": day_points},
            "fit_all": {"kib_per_token_q8_0": round(kib_q8, 2), "intercept_mib": round(icpt_all), "points": day_points + PRIOR_VRAM_POINTS,
                        "kib_per_token_q4_0_derived": round(kib_q4, 2), "note": "q4_0 block = 18 bytes / 32 elements vs q8_0 34 bytes"},
            "np4_peak_used_mib_during_day": peak_np4, "rows": rows,
            "server_log_prints_kv_buffer_sizes": False}


# --------------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--token-cache", default="/tmp/saea-scope-audit/tokens.json")
    ap.add_argument("--scratch", default="/tmp/saea-tput")
    args = ap.parse_args(argv)

    run_dir = DATA / "runs" / RUN_ID / ATTEMPT
    sess_dir = DATA / "serving" / SESSION
    session = json.loads((sess_dir / "session.json").read_text(encoding="utf-8"))
    seg_start = parse_iso(session["started_at"])
    attach = json.loads(next(run_dir.glob("*.session-attach-receipt.json")).read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / f"{RUN_ID}.run-manifest.json").read_text(encoding="utf-8"))

    driver_events = parse_driver(DRIVER_OUT)
    arm_start = next(t for t, k, d in driver_events if k == "arm-start" and "-roll2-2026" in d)
    arm_exit = next(t for t, k, d in driver_events if k == "arm-exit" and t > arm_start)

    tasks, idle_marks, device_line, n_segments = parse_server_log(sess_dir / "server.log", seg_start)
    contacts, order_ok = extract_trace(run_dir / f"{RUN_ID}.trace.jsonl")
    joined, window_tasks, join_report = join(contacts, tasks, arm_start, arm_exit)

    # ---- tokenizer: exact counts for the constant/small classes (system,
    # node queries, limits lines, slot-contract cards) and a deterministic
    # per-store sample of evidence labels (<= 200 distinct ids per store; the
    # rest take their store's mean -- ids within a store share one shape)
    tok = Tokenizer(Path(args.scratch), Path(args.token_cache), args.workers)
    jobs = dict(TEXTS)
    by_store = collections.defaultdict(list)
    for eid in LABELS:
        by_store[store_of(eid)].append(eid)
    label_sample = {}
    for store, ids in by_store.items():
        for eid in sorted(ids, key=lambda i: sha(i))[:200]:
            label_sample[eid] = sha(LABELS[eid]); jobs[sha(LABELS[eid])] = LABELS[eid]
    counts = tok.measure(jobs)
    store_label_mean = {store: statistics.fmean(counts[label_sample[i]] for i in ids if i in label_sample) for store, ids in by_store.items()}
    def label_tokens(eid):
        return counts[label_sample[eid]] if eid in label_sample else store_label_mean[store_of(eid)]
    label_summary = {store: {"distinct_ids": len(ids), "sampled": sum(1 for i in ids if i in label_sample), "mean_tokens_per_label": round(store_label_mean[store], 2)} for store, ids in sorted(by_store.items())}

    # ---- per-contact derived numbers
    frame_tokens = 2  # special_token_reserve in the preflight breakdown
    for c in joined:
        s = c["srv"]
        c["system_tokens"] = counts[c["system_sha"]]
        c["packet_tokens"] = s["mtmd_tokens"]
        c["label_tokens"] = sum(label_tokens(i) for i in c["label_ids"])
        c["limits_tokens"] = counts[c["limits_sha"]] if c["limits_sha"] else 0
        c["query_tokens"] = counts[c["query_sha"]]
        c["card_tokens"] = sum(counts[h] for h in c["card_shas"])
        text_chars = c["total_chars"] - c["system_chars"]
        text_tokens = c["prompt_tokens"] - c["system_tokens"] - c["packet_tokens"] - frame_tokens
        c["tok_per_char"] = text_tokens / text_chars if text_chars else 0.0
        # LCP -> tokens: system exactly, packet from the log, remainder by this request's ratio
        if c["has_prev"]:
            after_sys = max(0, c["lcp_chars"] - c["system_chars"])
            same_after_sys = max(0, c["same_set_chars"] - c["system_chars"])
            pkt = c["packet_tokens"] if c["lcp_parts"] >= 2 else 0
            c["lcp_tokens_est"] = c["system_tokens"] + (pkt if c["lcp_parts"] >= 2 else 0) + after_sys * c["tok_per_char"]
            c["same_set_tokens_est"] = c["system_tokens"] + c["packet_tokens"] + same_after_sys * c["tok_per_char"]
        else:
            c["lcp_tokens_est"] = c["same_set_tokens_est"] = 0.0
        c["cached"] = s["cached"]; c["processed"] = s["prompt_n"]
        c["prefill_rate"] = s["prompt_n"] / (s["prompt_ms"] / 1000) if s["prompt_ms"] > 0 else None
        c["decode_rate"] = s["eval_n"] / (s["eval_ms"] / 1000) if s["eval_ms"] > 0 else None
        c["turnaround_s"] = None
    # slot turnaround (client-side gap between a release and the next launch on the slot)
    by_slot = collections.defaultdict(list)
    for c in joined:
        by_slot[c["slot"]].append(c)
    for cs in by_slot.values():
        cs.sort(key=lambda c: c["seq"])
        for a, b in zip(cs, cs[1:]):
            b["turnaround_s"] = b["srv"]["t_launch_utc"] - a["srv"]["t_release_utc"]

    # ---- role classes
    def role_class(c):
        if c["role"] == "solver":
            return "solver#1" if (c["has_prev"] and c["first_diff"] != "none") or not c["has_prev"] else "solver#2-5(full hit)"
        return c["role"]
    per_role = {}
    for cls in ("perception", "solver#1", "solver#2-5(full hit)", "reviewer", "planner"):
        cs = [c for c in joined if role_class(c) == cls]
        if not cs:
            continue
        per_role[cls] = {
            "contacts": len(cs),
            "prompt_tokens": stats([c["prompt_tokens"] for c in cs]),
            "completion_tokens": stats([c["completion_tokens"] for c in cs]),
            "processed_prompt_tokens": stats([c["processed"] for c in cs]),
            "cached_tokens": stats([c["cached"] for c in cs]),
            "cache_hit_share_of_prompt": round(sum(c["cached"] for c in cs) / sum(c["prompt_tokens"] for c in cs), 4),
            "prompt_ms": stats([c["srv"]["prompt_ms"] for c in cs]),
            "eval_ms": stats([c["srv"]["eval_ms"] for c in cs]),
            "client_latency_s": stats([c["latency_s"] for c in cs], 2),
            "turnaround_before_s": stats([c["turnaround_s"] for c in cs], 2),
            "prefill_rate_tok_s_per_request": stats([c["prefill_rate"] for c in cs], 0),
            "decode_rate_tok_s_per_request": stats([c["decode_rate"] for c in cs], 1),
            "prefill_share_of_server_time": round(sum(c["srv"]["prompt_ms"] for c in cs) / max(1e-9, sum(c["srv"]["prompt_ms"] + c["srv"]["eval_ms"] for c in cs)), 4),
            "first_differing_class": dict(collections.Counter(c["first_diff"] or "no-previous" for c in cs).most_common()),
            "lcp_tokens_est": stats([c["lcp_tokens_est"] for c in cs if c["has_prev"]], 0),
            "same_content_bound_tokens_est": stats([c["same_set_tokens_est"] for c in cs if c["has_prev"]], 0),
            "cache_shortfall_vs_same_content_tokens": stats([max(0.0, c["same_set_tokens_est"] - c["cached"]) for c in cs if c["has_prev"]], 0),
            "label_tokens": stats([c["label_tokens"] for c in cs]),
            "limits_tokens": stats([c["limits_tokens"] for c in cs]),
            "query_tokens_excl_limits": stats([c["query_tokens"] for c in cs]),
            "card_tokens": stats([c["card_tokens"] for c in cs]),
            "n_cards": stats([len(c["card_ids"]) for c in cs]),
            "state_label_tokens_est": stats([c["state_label_chars"] * c["tok_per_char"] for c in cs], 1),
            "whitespace_run_tokens_est": stats([c["ws_chars"] * c["tok_per_char"] for c in cs], 1),
            "duplicate_line_tokens_est": stats([c["dup_line_chars"] * c["tok_per_char"] for c in cs], 1),
            "duplicate_heading_like_tokens_est": stats([c["dup_heading_chars"] * c["tok_per_char"] for c in cs], 1),
            "duplicate_content_tokens_est": stats([c["dup_content_chars"] * c["tok_per_char"] for c in cs], 1),
            "duplicate_distinct_lines": stats([c["dup_distinct_lines"] for c in cs], 1),
            "response_json_parsed_share": round(sum(1 for c in cs if c.get("response_json_ok")) / len(cs), 4),
            "response_chars": stats([c["response_chars"] for c in cs]),
            "response_compact_share": round(sum(c["response_compact_chars"] for c in cs) / max(1, sum(c["response_chars"] for c in cs)), 4),
            "response_repeated_value_share": round(sum(c["response_dup_value_chars"] for c in cs) / max(1, sum(c["response_chars"] for c in cs)), 4),
            "decode_slot_seconds": round(sum(c["srv"]["eval_ms"] for c in cs) / 1000, 1),
            "prefill_slot_seconds": round(sum(c["srv"]["prompt_ms"] for c in cs) / 1000, 1),
            "turnaround_slot_seconds": round(sum(c["turnaround_s"] or 0 for c in cs), 1),
            "evidence_tokens_by_store_est": {k: round(statistics.fmean([c["evidence_chars_by_store"].get(k, 0) * c["tok_per_char"] for c in cs]), 1) for k in sorted({k for c in cs for k in c["evidence_chars_by_store"]})},
        }

    # ---- validation of the ratio method: full hits and system-only hits
    full_hits = [c for c in joined if "full_hit_n_past" in c["srv"]]
    validation = {
        "full_hit_contacts_server": len(full_hits),
        "full_hit_lcp_est_minus_prompt_tokens": stats([c["lcp_tokens_est"] - c["prompt_tokens"] for c in full_hits], 1),
        "system_only_hits": {
            "count": sum(1 for c in joined if c["has_prev"] and c["lcp_parts"] == 1),
            "server_cached_tokens": stats([c["cached"] for c in joined if c["has_prev"] and c["lcp_parts"] == 1], 1),
            "system_tokens": stats([c["system_tokens"] for c in joined if c["has_prev"] and c["lcp_parts"] == 1], 1),
        },
        "lcp_est_minus_server_cached_all": stats([c["lcp_tokens_est"] - c["cached"] for c in joined if c["has_prev"]], 1),
        "trace_order_per_slot_monotone": order_ok,
    }

    # ---- card selection bound (gold-free): cards whose slot type is admissible under the row's candidate intents
    schema = json.loads(SCHEMA.read_text(encoding="utf-8")) if SCHEMA.exists() else None
    intent_slots = {}
    if schema:
        for row in schema.get("intents", []):
            intent_slots[row["intent"]] = {t["entity_type"] for t in row.get("types", [])}
    card_sel = None
    if intent_slots:
        keep = []; drop = []; keep_tok = []; drop_tok = []
        for c in joined:
            if not c["card_ids"] or not c["candidate_intents"]:
                continue
            adm = set().union(*(intent_slots.get(i, set()) for i in c["candidate_intents"]))
            k = d = kt = dt = 0
            for cid, h in zip(c["card_ids"], c["card_shas"]):
                slot_type = cid.split(":")[-1]
                t = counts[h]
                if slot_type in adm: k += 1; kt += t
                else: d += 1; dt += t
            keep.append(k); drop.append(d); keep_tok.append(kt); drop_tok.append(dt)
        card_sel = {"contacts_measured": len(keep), "cards_admissible_per_contact": stats(keep), "cards_not_admissible_per_contact": stats(drop),
                    "admissible_card_tokens": stats(keep_tok), "not_admissible_card_tokens": stats(drop_tok),
                    "schema_intents": len(intent_slots), "method": "slot type admissible iff listed for any of the row's Perception candidate intents in slurp-intent-slot-schema-v1 (train-derived, gold-free at runtime)"}

    # ---- wall-clock decomposition (contact window)
    t0, t1 = attach["contact_window"]["from"], attach["contact_window"]["to"]
    acc, conc_pf, conc_dec, scaling = sweep([c["srv"] for c in joined], t0, t1)
    wall = t1 - t0
    total_processed = sum(c["processed"] for c in joined)
    total_decoded = sum(c["srv"]["eval_n"] for c in joined)
    idle_in_window = [m for m in idle_marks if t0 <= m <= t1]
    time_split = {
        "contact_window_utc": [iso(t0), iso(t1)], "wall_s": round(wall, 1), "arm_wall_s_driver": round(arm_exit - arm_start, 1),
        "states_s": acc, "states_share": {k: round(v / wall, 4) for k, v in acc.items() if k != "slot_seconds_busy"},
        "mean_busy_slots": round(acc["slot_seconds_busy"] / wall, 3),
        "prefill_concurrency_s": conc_pf, "decode_only_concurrency_s": conc_dec,
        "sum_prompt_ms_all_slots_s": round(sum(c["srv"]["prompt_ms"] for c in joined) / 1000, 1),
        "sum_eval_ms_all_slots_s": round(sum(c["srv"]["eval_ms"] for c in joined) / 1000, 1),
        "sum_client_latency_s": round(sum(c["latency_s"] for c in joined), 1),
        "processed_prompt_tokens_total": total_processed, "decoded_tokens_total": total_decoded,
        "sealed_prompt_tokens_total": sum(c["prompt_tokens"] for c in joined),
        "aggregate_prefill_tok_s_over_prefill_active": round(total_processed / acc["prefill_active"], 0),
        "aggregate_decode_tok_s_over_wall": round(total_decoded / wall, 1),
        "contacts_per_minute": round(len(joined) / wall * 60, 2),
        "contacts_per_gpu_hour_contact_window": round(len(joined) / wall * 3600, 0),
        "contacts_per_gpu_hour_arm_wall": round(len(joined) / (arm_exit - arm_start) * 3600, 0),
        "all_slots_idle_marks_in_window": len(idle_in_window),
        "slot_capacity": {
            "slot_seconds_total": round(4 * wall, 1),
            "server_compute_slot_s": round(sum(c["srv"]["prompt_ms"] + c["srv"]["eval_ms"] for c in joined) / 1000, 1),
            "in_slot_overhead_slot_s": round(acc["slot_seconds_busy"] - sum(c["srv"]["prompt_ms"] + c["srv"]["eval_ms"] for c in joined) / 1000, 1),
            "empty_slot_s": round(4 * wall - acc["slot_seconds_busy"], 1),
            "client_turnaround_slot_s": round(sum(c["turnaround_s"] or 0 for c in joined), 1),
        },
        "decode_batch_scaling": scaling,
        "manifest_latency_seconds_total": manifest["cost"]["latency_seconds_total"],
        "monitor_summary_in_attach_receipt": {k: attach["monitor_summary"].get(k) for k in ("active_seconds", "parked_seconds", "parked_fraction", "mean_utilization_percent", "mean_power_watts")},
    }

    # ---- levers -> contacts per GPU-hour. Each saving is converted in its own
    # unit: prefill tokens at the measured aggregate prefill rate while >=1 slot
    # prefills; decode tokens at the measured aggregate decode rate while the GPU
    # computes; wall seconds directly. Levers are estimated one at a time.
    n = len(joined)
    W = wall
    R_pf = total_processed / acc["prefill_active"]
    R_dec = total_decoded / (acc["prefill_active"] + acc["decode_only"])
    def lever(name, *, prefill_tokens=0.0, decode_tokens=0.0, wall_removed=0.0, **kw):
        dw = prefill_tokens / R_pf + decode_tokens / R_dec + wall_removed
        return {"lever": name, "wall_s_removed_est": round(dw, 1), "gain_pct": round(dw / max(1.0, W - dw) * 100, 1),
                "contacts_per_gpu_hour": round(n / max(1.0, W - dw) * 3600, 0), **kw}
    def processed_weighted(key, cs):
        return sum(c[key] * c["processed"] / c["prompt_tokens"] for c in cs)
    solver1 = [c for c in joined if role_class(c) == "solver#1"]
    later = [c for c in joined if c["has_prev"]]
    per_slot_mean = total_decoded / (sum(c["srv"]["eval_ms"] for c in joined) / 1000)
    r4 = next((row["per_slot_decode_tok_s"] for row in scaling if row["slots_prefilling"] == 0 and row["slots_decoding"] == 4), None)
    busy = acc["slot_seconds_busy"]
    decode_slot_s = sum(c["srv"]["eval_ms"] for c in joined) / 1000
    lev = []
    lev.append(lever("fill the slots: no empty slot-seconds (async dispatch; upper bound, per-slot service unchanged)",
                     wall_removed=W - busy / 4,
                     empty_slot_s=round(4 * W - busy, 1), mean_busy_slots=round(busy / W, 3),
                     changes_for_nodes="nothing (same bytes; batch composition changes as in every dispatcher change)",
                     needs="runtime change + own-null read of batch-composition noise"))
    r2 = next((row["aggregate_decode_tok_s"] for row in scaling if row["slots_prefilling"] == 0 and row["slots_decoding"] == 2), None)
    r4agg = next((row["aggregate_decode_tok_s"] for row in scaling if row["slots_prefilling"] == 0 and row["slots_decoding"] == 4), None)
    lev.append({"lever": "np6 x 24,576 with q4_0 KV (the only wider geometry that fits): more decode batch", "wall_s_removed_est": None, "gain_pct": None,
                "contacts_per_gpu_hour": None, "measured_decode_scaling_2_to_4_slots_tok_s": [r2, r4agg], "per_slot_decode_tok_s_at_4_no_prefill": r4,
                "changes_for_nodes": "nothing in the bytes; an unflown KV type changes the core's arithmetic", "needs": "a flown session to measure (no number claimed here) + serving-identity change -> owner ruling + no-harm read; worthless until the slots are kept full"})
    lev.append(lever("remove only the all-slots-idle time", wall_removed=acc["all_idle"], changes_for_nodes="nothing", needs="runtime change"))
    lev.append(lever("overlap the Solver#1 supply acquisition (client gap before the first Solver contact)",
                     wall_removed=sum(c["turnaround_s"] or 0 for c in solver1) / 4,
                     gap_slot_s=round(sum(c["turnaround_s"] or 0 for c in solver1), 1), gap_mean_s=round(statistics.fmean(c["turnaround_s"] or 0 for c in solver1), 2),
                     changes_for_nodes="nothing", needs="runtime change (start acquisition while Perception decodes)"))
    for cls in ("perception", "solver#1", "solver#2-5(full hit)", "reviewer", "planner"):
        cs = [c for c in joined if role_class(c) == cls]
        if not cs:
            continue
        share = 1 - sum(c["response_compact_chars"] for c in cs) / max(1, sum(c["response_chars"] for c in cs))
        lev.append(lever(f"compact JSON output ({cls}): whitespace/newlines out of the emitted JSON",
                         decode_tokens=sum(c["completion_tokens"] for c in cs) * share, whitespace_char_share=round(share, 4),
                         changes_for_nodes="same parsed answer; the core's own sampling path changes",
                         needs="form change on the output side -> no-harm cell (grammar/response_format)"))
    perc = [c for c in joined if role_class(c) == "perception"]
    share = sum(c["response_dup_value_chars"] for c in perc) / max(1, sum(c["response_chars"] for c in perc))
    lev.append(lever("Perception output: string values repeated across candidates (state once)",
                     decode_tokens=sum(c["completion_tokens"] for c in perc) * share, repeated_value_char_share=round(share, 4),
                     changes_for_nodes="Perception schema change; later nodes read the same candidates", needs="form change -> no-harm cell"))
    lev.append(lever("[evidence <id>] labels removed or shortened (prefill; only the processed share counts)",
                     prefill_tokens=processed_weighted("label_tokens", joined), tokens_on_wire_per_contact=round(sum(c["label_tokens"] for c in joined) / n, 0),
                     changes_for_nodes="removes the addressable id in front of each body (nodes cite ids in evidence_refs)", needs="form change -> no-harm cell"))
    lev.append(lever("Native episode limits line (always in the processed tail)",
                     prefill_tokens=processed_weighted("limits_tokens", joined), tokens_on_wire_per_contact=round(sum(c["limits_tokens"] for c in joined) / n, 0),
                     changes_for_nodes="removes remaining-revisions/actions the Planner reads", needs="form change -> no-harm cell"))
    if card_sel:
        saved = 0.0
        for c in solver1:
            if not c["card_ids"] or not c["candidate_intents"]:
                continue
            adm = set().union(*(intent_slots.get(i, set()) for i in c["candidate_intents"]))
            saved += sum(counts[h] for cid, h in zip(c["card_ids"], c["card_shas"]) if cid.split(":")[-1] not in adm) * c["processed"] / c["prompt_tokens"]
        lev.append(lever("slot-contract cards whose slot type no candidate intent can carry (selection, gold-free)",
                         prefill_tokens=saved, cards_per_contact_not_admissible=card_sel["cards_not_admissible_per_contact"]["mean"] if card_sel["cards_not_admissible_per_contact"] else None,
                         changes_for_nodes="removes cards about types the row's own candidates exclude; Reviewer/Planner still see every card the Solver saw",
                         needs="form change (selection) -> no-harm cell; the owner ruling on global state does not forbid it"))
    lev.append(lever("repeated heading-like lines across evidence items (<=40 chars or ending ':')",
                     prefill_tokens=sum(c["dup_heading_chars"] * c["tok_per_char"] * c["processed"] / c["prompt_tokens"] for c in joined),
                     tokens_on_wire_per_contact=round(sum(c["dup_heading_chars"] * c["tok_per_char"] for c in joined) / n, 0),
                     changes_for_nodes="card structure changes", needs="form change -> no-harm cell"))
    lev.append(lever("repeated content lines across evidence items (state once per contact)",
                     prefill_tokens=sum(c["dup_content_chars"] * c["tok_per_char"] * c["processed"] / c["prompt_tokens"] for c in joined),
                     tokens_on_wire_per_contact=round(sum(c["dup_content_chars"] * c["tok_per_char"] for c in joined) / n, 0),
                     changes_for_nodes="same facts, stated once", needs="form change -> no-harm cell"))
    lev.append(lever("prefix cache: bring every byte-identical block into the cached prefix (the brief's hypothesis)",
                     prefill_tokens=min(sum(max(0.0, c["same_set_tokens_est"] - c["cached"]) for c in later), sum(c["processed"] for c in later)),
                     measured_cache_share_of_prompt_tokens=round(1 - total_processed / sum(c["prompt_tokens"] for c in joined), 4),
                     changes_for_nodes="nothing", needs="nothing -- already realised as flown (see validation)"))
    lev.append(lever("whitespace runs inside evidence bodies",
                     prefill_tokens=sum(c["ws_chars"] * c["tok_per_char"] * c["processed"] / c["prompt_tokens"] for c in joined),
                     changes_for_nodes="nothing semantic", needs="byte-identity-of-meaning proof"))
    lev.append(lever("baseline as flown"))
    lev.sort(key=lambda r: -(r["contacts_per_gpu_hour"] or 0))
    rates = {"aggregate_prefill_tok_s_while_prefilling": round(R_pf, 0), "aggregate_decode_tok_s_while_computing": round(R_dec, 1), "mean_per_slot_decode_tok_s": round(per_slot_mean, 1)}

    # ---- day accounting
    d0 = parse_iso(DAY + "T00:00:00Z"); d1 = d0 + 86400
    session_windows = []
    for name in DAY_SESSIONS:
        sj = json.loads((DATA / "serving" / name / "session.json").read_text(encoding="utf-8"))
        start = parse_iso(sj["started_at"])
        stop_p = DATA / "serving" / name / "session-stop.json"
        stop = parse_iso(json.loads(stop_p.read_text(encoding="utf-8")).get("stopped_at")) if stop_p.exists() else d1
        session_windows.append((start, stop))
    prev_np4_stop = sess_dir / "archive-stopped-20260926T144222Z" / "session-stop.json"
    if prev_np4_stop.exists():
        j = json.loads(prev_np4_stop.read_text(encoding="utf-8"))
        session_windows.append((d0, parse_iso(j["stopped_at"])))
    day_table, arm_minutes, resident_minutes, minutes, spans = day_accounting(d0, d1, driver_events, session_windows)

    receipt = {
        "schema": "saea-slurp-throughput-baseline-and-levers-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": RUN_ID, "attempt_id": ATTEMPT, "session_id": SESSION,
        "session_started_at": session["started_at"], "server_log_segments_in_file": n_segments,
        "arm_window_driver_utc": [iso(arm_start), iso(arm_exit)],
        "server_tasks_in_arm_window": len(window_tasks), "trace_contacts": len(contacts), "joined_contacts": len(joined),
        "join_report": join_report, "validation": validation,
        "time_split": time_split, "per_role": per_role, "card_selection_bound": card_sel,
        "levers_ranked": lev, "lever_model_rates": rates,
        "geometry": geometry(device_line),
        "day_accounting": {"day_utc": DAY, "minutes": minutes, "monitored_minutes": sum(v.get("busy", 0) + v.get("idle", 0) for v in day_table.values()),
                           "busy_minutes": sum(v.get("busy", 0) for v in day_table.values()), "np4_or_other_server_resident_minutes": resident_minutes,
                           "by_driver_state": day_table, "arm_minutes": arm_minutes, "driver_spans": spans,
                           "busy_definition": f"a minute is busy when any monitor sample in it has utilization >= {BUSY_UTIL} % or a busy slot; unmonitored = no sample from any of the four sessions"},
        "tokenizer": {"binary": str(TOKENIZE), "calls_this_run": tok.calls, "distinct_texts": len(jobs), "label_summary": label_summary, "note": "vocab-only llama-tokenize, sha256-keyed count cache; no model, server, encoder or scorer contact"},
        "sources": {"trace": str(run_dir / f"{RUN_ID}.trace.jsonl"), "server_log": str(sess_dir / "server.log"), "driver_out": str(DRIVER_OUT), "manifest_cost": manifest["cost"]},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("server_tasks_in_arm_window", "trace_contacts", "joined_contacts", "join_report")}, indent=1))
    print(json.dumps(time_split, indent=1))
    for k, v in per_role.items():
        print(k, json.dumps({x: v[x] for x in ("contacts", "prompt_tokens", "processed_prompt_tokens", "cached_tokens", "cache_hit_share_of_prompt", "prompt_ms", "eval_ms", "first_differing_class", "same_content_bound_tokens_est", "lcp_tokens_est")}))
    print(json.dumps(validation, indent=1))
    print(json.dumps(receipt["levers_ranked"], indent=1))
    print(json.dumps(receipt["geometry"]["fit_all"], indent=1)); print(json.dumps(receipt["geometry"]["rows"], indent=1))
    print(json.dumps(receipt["day_accounting"]["by_driver_state"], indent=1)); print(json.dumps(arm_minutes, indent=1))
    print("tokenizer calls", tok.calls, "distinct", len(jobs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
