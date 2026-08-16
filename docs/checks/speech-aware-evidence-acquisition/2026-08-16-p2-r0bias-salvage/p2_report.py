#!/usr/bin/env python3
"""PHASE-2 R-ladder report extractor. Read-only over run artifacts."""
import json, os, sys, glob, collections, re

D = "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs"
ARMS = ["SAEA-P2-r0bias", "SAEA-P2-r1verify", "SAEA-P2-r2draft",
        "SAEA-P2-r0wrong", "SAEA-P2-r1wrong"]
# Stale attempts from the ABORTED 2026-08-15T23:2x launch (0 calls / 0 audio).
STALE = {"attempt-20260815T232522Z-eb10f5", "attempt-20260815T233245Z-6a98bd"}
# Hard cutoff: tonight's relaunch began 2026-08-16T00:21:01Z. Anything older is
# not this run and must never be reported as such.
CUTOFF = "attempt-20260816T0021"
WATCH = ["frenz", "aldeyra", "chumbley", "reedy"]


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def newest_attempt(run):
    p = os.path.join(D, run)
    if not os.path.isdir(p):
        return None
    ats = sorted([a for a in os.listdir(p)
                  if a not in STALE and a >= CUTOFF], reverse=True)
    return ats[0] if ats else None


def jload(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def report_arm(run):
    a = newest_attempt(run)
    print("=" * 78)
    print(f"ARM {run}")
    if not a:
        print("  no attempt dir")
        return
    P = os.path.join(D, run, a)
    print(f"  attempt: {a}")
    man = jload(os.path.join(P, f"{run}.run-manifest.json"))
    if not man:
        print("  NO MANIFEST (in flight or aborted)")
        print("  files:", sorted(os.listdir(P)))
        return
    cost = man.get("cost", {}) or {}
    print(f"  status={man.get('status')} failure_reason={man.get('failure_reason')}")
    print(f"  study_commit={man.get('study_commit')} created_at={man.get('created_at')}")
    print(f"  config_hash={man.get('config',{}).get('config_hash')}")
    print(f"  fragments={man.get('config',{}).get('fragments')}")
    print(f"  split={man.get('split',{}).get('name')} role={man.get('split',{}).get('role')} "
          f"n={man.get('split',{}).get('count')} idhash={man.get('split',{}).get('identity_hash','')[:16]}")
    for k in ("calls_used", "audio_seconds_used", "gpu_seconds", "cpu_seconds",
              "latency_seconds_total", "peak_vram_mib", "prompt_tokens_total",
              "completion_tokens_total", "supplied_evidence_bytes",
              "admitted_evidence_bytes", "tool_calls", "gate_setup_seconds",
              "skipped_slice_count", "saturated_slice_count"):
        if k in cost:
            print(f"    {k} = {cost[k]}")

    sc = jload(os.path.join(P, f"{run}.scores.json"))
    if sc and "asr-wer" in sc:
        agg = sc["asr-wer"].get("aggregate", {})
        print(f"  WER macro(mean_wer)={agg.get('mean_wer')} samples={agg.get('samples')}")
        for s in sc["asr-wer"].get("per_sample", []):
            print(f"    per-call {s}")

    # ---- trace-derived counters ----
    T = os.path.join(P, f"{run}.trace.jsonl")
    if not os.path.exists(T):
        print("  NO TRACE")
        return
    recs = []
    with open(T, encoding="utf-8") as f:
        for line in f:
            try:
                recs.append(json.loads(line))
            except Exception:
                pass
    chans = collections.Counter(r["channel"] for r in recs)
    print(f"  trace lines={len(recs)} channels={dict(chans)}")

    rep = [r["payload"] for r in recs if r["channel"] == "REPLAY"]
    acc = [p for p in rep if p.get("replay_accepted")]
    rej = [p for p in rep if not p.get("replay_accepted")]
    print(f"  REPLAY total={len(rep)} accepted={len(acc)} rejected={len(rej)}")
    print("  rejects-by-reason:",
          dict(collections.Counter(p.get("replay_reject_reason") for p in rej)))
    print("  triggers:", dict(collections.Counter(p.get("replay_trigger") for p in rep)))
    print("  flag_source:", dict(collections.Counter(p.get("replay_flag_source") for p in rep)))
    print("  localize_source:", dict(collections.Counter(p.get("replay_localize_source") for p in rep)))

    # ---- PRE-LOCALIZE echo rates ----
    # measurement point = replay_replay_text (raw replay output, BEFORE localization
    # trims it to replay_localized_words); reference = replay_flag_matched_candidate.
    bw = ro = tot = 0
    echo_examples = []
    for p in rep:
        raw = p.get("replay_replay_text")
        ref = p.get("replay_flag_matched_candidate")
        if raw is None or not ref:
            continue
        tot += 1
        nraw, nref = norm(raw), norm(ref)
        if nraw == nref:
            ro += 1
            bw += 1
            echo_examples.append(("reference-only", p.get("replay_pass1_text"), raw, ref))
        elif nraw.startswith(nref):
            bw += 1
            echo_examples.append(("begins-with", p.get("replay_pass1_text"), raw, ref))
    if tot:
        print(f"  PRE-LOCALIZE echo (n={tot}): begins-with={bw} ({bw/tot:.1%}) "
              f"reference-only={ro} ({ro/tot:.1%})")
    else:
        print("  PRE-LOCALIZE echo: no measurable replays")
    for e in echo_examples[:8]:
        print(f"    echo[{e[0]}] pass1={e[1]!r} raw={e[2]!r} ref={e[3]!r}")

    # ---- wrong-reference copy instances (verbatim) ----
    if "wrong" in run:
        print("  WRONG-REFERENCE COPY INSTANCES (pre-localize raw contains delivered ref):")
        n = 0
        for p in rep:
            raw = p.get("replay_replay_text")
            ref = p.get("replay_flag_matched_candidate")
            if not raw or not ref:
                continue
            if norm(ref) and norm(ref) in norm(raw):
                n += 1
                print(f"    COPY#{n} sample={p.get('replay_sample_id')} "
                      f"win_iter={p.get('replay_window_iteration')} "
                      f"span=({p.get('replay_span_start_word')},{p.get('replay_span_end_word')}) "
                      f"accepted={p.get('replay_accepted')}")
                print(f"      pass1_text  = {p.get('replay_pass1_text')!r}")
                print(f"      delivered_ref = {ref!r}")
                print(f"      raw_replay  = {raw!r}")
                print(f"      localized   = {p.get('replay_localized_words')!r}")
        print(f"    total copy instances = {n} / {len(rep)} replays")

    # ---- watched terms ----
    print("  WATCHED TERM OUTCOMES (Frenz/Aldeyra/Chumbley/Reedy):")
    for w in WATCH:
        hits = [p for p in rep
                if w in norm(p.get("replay_pass1_text")) or w in norm(p.get("replay_flag_matched_candidate"))
                or w in norm(p.get("replay_replay_text")) or w in norm(" ".join(p.get("replay_localized_words") or []))]
        if not hits:
            print(f"    {w}: no replay records")
            continue
        for p in hits:
            print(f"    {w}: sample={p.get('replay_sample_id')} "
                  f"pass1={p.get('replay_pass1_text')!r} -> raw={p.get('replay_replay_text')!r} "
                  f"localized={p.get('replay_localized_words')!r} "
                  f"accepted={p.get('replay_accepted')} reject={p.get('replay_reject_reason')!r} "
                  f"cand={p.get('replay_flag_matched_candidate')!r} "
                  f"dist={p.get('replay_flag_distance')}")

    # ---- empty-candidate annotations ----
    print("  EMPTY-CANDIDATE ANNOTATIONS (replay-derivation docs):")
    empt = []
    for dp in sorted(glob.glob(os.path.join(P, f"{run}.replay-derivation.*.json"))):
        d = jload(dp) or {}
        sid = os.path.basename(dp).split(".")[-2]
        note = d.get("replay_pack_terms_empty_note")
        nterms = d.get("replay_pack_terms")
        nwin = d.get("replay_windows") or d.get("windows")
        print(f"    sample={sid} empty_note={note!r} "
              f"n_terms={len(nterms) if isinstance(nterms,list) else nterms} "
              f"n_windows={len(nwin) if isinstance(nwin,list) else nwin}")
        if note == "empty-candidates-file":
            empt.append(sid)
    print(f"    empty-candidates-file samples ({len(empt)}): {empt}")

    # ORG evidence counts per call
    org = [r["payload"] for r in recs if r["channel"] == "ORG"]
    print("  ORG evidence_count per call:",
          [o.get("org_evidence_count") for o in org])

    # ---- payload spot-checks (2 per arm) ----
    print("  PAYLOAD SPOT-CHECKS (2):")
    mreq = [r for r in recs if r["channel"] == "MODEL_REQUEST" and "payload" in r["payload"]]
    for r in mreq[:1] + mreq[len(mreq)//2:len(mreq)//2+1]:
        pl = r["payload"]["payload"]
        print(f"    record_id={r['record_id']} sha={r['payload'].get('payload_sha256','')[:16]}")
        print(f"      arm={r['payload'].get('arm')} sample={pl.get('sample_id')} "
              f"audio_s={pl.get('audio_seconds')} media={pl.get('media_relpath')}")
        print(f"      supplied_evidence={json.dumps(pl.get('supplied_evidence'))[:300]}")
        print(f"      delta_candidates={json.dumps(pl.get('delta_candidates'))[:300]}")
        print(f"      evidence_provenance={json.dumps(pl.get('evidence_provenance'))[:200]}")
        print(f"      decoding={json.dumps(pl.get('decoding_params'))}")
        print(f"      task_instruction={pl.get('task_instruction')!r}")


if __name__ == "__main__":
    which = sys.argv[1:] or ARMS
    for r in which:
        try:
            report_arm(r)
        except Exception as e:
            print(f"ARM {r} EXTRACTION ERROR: {type(e).__name__}: {e}")
