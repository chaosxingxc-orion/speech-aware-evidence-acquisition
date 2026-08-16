#!/usr/bin/env python3
"""P2 R-ladder report extractor. Read-only. usage: p2_extract.py [ARM ...]"""
import json, os, re, sys, collections

DATA = "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data"
ARMS = ["SAEA-P2-r0bias", "SAEA-P2-r1verify", "SAEA-P2-r2draft",
        "SAEA-P2-r0wrong", "SAEA-P2-r1wrong"]
WATCH = ["frenz", "aldeyra", "chumbley", "reed"]
EMPTY_BY_DESIGN = {"4365024", "4365948", "4366429", "4384964"}


def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split()


def latest_attempt(arm):
    d = os.path.join(DATA, "runs", arm)
    if not os.path.isdir(d):
        return None
    a = sorted(x for x in os.listdir(d) if x.startswith("attempt-"))
    return os.path.join(d, a[-1]) if a else None


def report(arm):
    A = latest_attempt(arm)
    print("=" * 78)
    print("ARM", arm)
    if not A:
        print("  no attempt dir yet")
        return
    print("  attempt:", os.path.basename(A))
    mp = os.path.join(A, f"{arm}.run-manifest.json")
    if not os.path.exists(mp):
        n = len(os.listdir(A))
        print(f"  IN-PROGRESS (no manifest yet), files={n}")
    else:
        m = json.load(open(mp))
        c = m.get("cost", {})
        print("  status:", m.get("status"), "| failure:", m.get("failure_reason"))
        print("  created:", m.get("created_at"), "| study_commit:", (m.get("study_commit") or "")[:8])
        print("  fragments:", json.dumps(m.get("config", {}).get("fragments", {})))
        print("  COST calls=%s audio_s=%.1f gpu_s=%.1f cpu_s=%.1f prompt_tok=%s compl_tok=%s vram=%s" % (
            c.get("calls_used"), c.get("audio_seconds_used") or 0, c.get("gpu_seconds") or 0,
            c.get("cpu_seconds") or 0, c.get("prompt_tokens_total"),
            c.get("completion_tokens_total"), c.get("peak_vram_mib")))
        print("  latency_total_s=%.1f gate_setup_s=%.1f evidence_bytes supplied=%s admitted=%s" % (
            c.get("latency_seconds_total") or 0, c.get("gate_setup_seconds") or 0,
            c.get("supplied_evidence_bytes"), c.get("admitted_evidence_bytes")))
        print("  saturated=%s skipped=%s" % (c.get("saturated_slice_count"), c.get("skipped_slice_count")))

    sp = os.path.join(A, f"{arm}.scores.json")
    if os.path.exists(sp):
        s = json.load(open(sp))
        w = s.get("asr-wer", {})
        agg = w.get("aggregate", {})
        print("  MACRO WER: %.5f  (n=%s)" % (agg.get("mean_wer", float("nan")), agg.get("samples")))
        for ps in w.get("per_sample", []):
            print("    call %-9s wer=%.5f  S=%-4s D=%-4s I=%-4s hits=%s" % (
                ps.get("sample_id"), ps.get("wer", float("nan")), ps.get("substitutions"),
                ps.get("deletions"), ps.get("insertions"), ps.get("hits")))

    # ---- replay derivations ----
    tot = collections.Counter()
    rej = collections.Counter()
    echo_begin = echo_only = with_text = 0
    watch_hits = []
    copies = []
    empties = []
    for fn in sorted(os.listdir(A)):
        if ".replay-derivation." not in fn:
            continue
        sid = fn.split(".replay-derivation.")[1][:-5]
        d = json.load(open(os.path.join(A, fn)))
        note = d.get("replay_pack_terms_empty_note")
        if note or sid in EMPTY_BY_DESIGN:
            empties.append((sid, note, len(d.get("replay_windows", []))))
        for w in d.get("replay_windows", []):
            tot["windows"] += 1
            if w.get("replay_request_sha256"):
                tot["issued"] += 1
            if w.get("replay_accepted"):
                tot["accepted"] += 1
            r = w.get("replay_reject_reason")
            if r:
                rej[r] += 1
            rt = w.get("replay_replay_text")
            cands = [c.get("text", "") for c in (w.get("replay_candidates") or [])]
            if rt:
                with_text += 1
                nt = norm(rt)
                for cd in cands:
                    nc = norm(cd)
                    if nc and nt[:len(nc)] == nc:
                        echo_begin += 1
                        if nt == nc:
                            echo_only += 1
                        break
            blob = " ".join([rt or "", " ".join(cands), " ".join(w.get("replay_query_terms") or [])]).lower()
            for name in WATCH:
                if name in blob:
                    watch_hits.append((sid, name, w.get("replay_accepted"), r,
                                       (w.get("replay_pass1_text") or "")[:60],
                                       (rt or "")[:120], cands))
                    break
            if "wrong" in arm and rt and cands:
                for cd in cands:
                    nc = norm(cd)
                    if nc and len(nc) >= 1 and all(t in norm(rt) for t in nc):
                        copies.append((sid, cd, rt[:200]))
                        break
    print("  COUNTERS windows=%s issued=%s accepted=%s" % (
        tot["windows"], tot["issued"], tot["accepted"]))
    print("  REJECTS:", dict(rej) if rej else "{}")
    if with_text:
        print("  PRE-LOCALIZE ECHO on raw replay text: n_with_text=%s begins-with-ref=%s (%.1f%%) ref-only=%s (%.1f%%)" % (
            with_text, echo_begin, 100.0 * echo_begin / with_text, echo_only, 100.0 * echo_only / with_text))
    else:
        print("  PRE-LOCALIZE ECHO: no replay text yet")
    print("  EMPTY-CANDIDATE calls seen: %s" % (
        [(s, n, f"{k} windows") for s, n, k in empties] or "none"))
    if copies:
        print("  WRONG-REF COPIES (%d):" % len(copies))
        for sid, cd, rt in copies:
            print("    call %s  ref=%r" % (sid, cd))
            print("       replay=%r" % rt)
    elif "wrong" in arm:
        print("  WRONG-REF COPIES: 0")
    if watch_hits:
        print("  WATCH WINDOWS (frenz/aldeyra/chumbley/reed):")
        for sid, name, acc, r, p1, rt, cands in watch_hits:
            print("    %s [%s] accepted=%s reject=%s" % (sid, name, acc, r))
            print("       pass1=%r" % p1)
            print("       replay=%r" % rt)
            print("       cands=%s" % json.dumps(cands)[:200])


for arm in (sys.argv[1:] or ARMS):
    report(arm)
