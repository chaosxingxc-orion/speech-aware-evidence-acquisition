# Config A″ re-lock: the feature cache earns its keep by vacating the GPU (2026-08-12)

Owner value ruling (2026-08-12): "我是希望我们的方案能够腾出hbm,如果没法空出HBM的话,我们的
缓存方案没有价值" — the cache scheme's value IS the freed HBM. This document records the
measured chain that satisfies that ruling and the resulting baseline re-lock A′ → A″.

## The chain, all measured (no step estimated)

1. **The cache is correct and total.** Media-ordinal keys are text-invariant: 806/806 hits
   across bare, matched-evidence, and mismatched-evidence prompts on the same audio; zero
   encoder calls; VALIDATE mode holds byte-identical features
   (SAEA-BENCH-featcache / -featcache-np8, 2026-08-11).
2. **A warm cache makes the encoder a no-op, so the mmproj can leave the GPU.**
   `--no-mmproj-offload` was killed in the encode-inline era (config B, −26%): CPU encode
   is 2× GPU. With every feature served from cache the encoder never runs, on either
   device. Probe A (SAEA-BENCH-hbmfree, attempt c54874): peak **18,738 MiB vs 21,700
   (−2.96 GB)**, encoder calls **0**, cache dir untouched at 806, WER **0.1397** on the
   no-tail floor, wall 16 min in-band. The mmproj (2,913.90 MiB worst case) loads to host.
3. **The freed 2.9 GB buys the one thing VRAM was actually blocking: evidence-arm np8.**
   Decode is kernel-bound, indifferent to VRAM headroom (M1) and nearly indifferent to
   encode contention (+6–7% per-slot with encode removed) — free HBM does NOT buy decode
   speed. What it buys is slots × context. Evidence arms need big slots; with the mmproj
   resident, np8 × evidence-sized KV could not boot (config C's grave). Probe B
   (SAEA-BENCH-hbmfree-evid, attempt fce635): `-c 81920 -np 8` boots and serves at
   **22,114 MiB peak** (~2.3 GB headroom), max request 7,567 tokens vs the 10,240 slot,
   `truncated = 0` on all 102 slices, zero skips/saturations, zero encoder calls.
4. **The science workload gets the dividend.** Same matched-evidence fast-3 workload:
   **43.2 min** (np4 sequential tail-era, E-002F-r4-matched d02706) → **20 min** (probe B)
   ≈ **2.2×**. Matched WER 0.1498 vs bare floor 0.1397 (n=3 — a science hint for E-005,
   not a serving verdict).

## Slot sizing: measured ceiling replaces the worst-case guess

The A/A′ sizing (12,288/slot) came from the ConEC tokenizer worst case (~11.8k). Measured
R4 prompt distribution (three arms, ~1,220 requests each): evidence arms p50 ≈ 4.8–5.0k,
p99 ≈ 7.58–7.60k, **max 7,611**; bare p50 ≈ 1,003, max 1,042. With the 1,024-token
generation cap the ceiling is ~8.7k → **10,240/slot** with margin. A ConEC campaign that
genuinely packs ≥10k-token evidence must either drop np or set an explicit SUPPLY evidence
budget — that is an experimental knob, never a silent serving-side trim.

## The lock (config A″)

`configs/model/qwen3-omni-llamacpp-q4km.json`, all inside the config hash:

- build: receipt `receipts/runtime-q4km-featcache.json` (llama.cpp featcache patch,
  worktree commit `5d9dfcb58`, per-file GGUF SHA-256; patch archived at
  `docs/patches/2026-08-11-mtmd-feature-cache.diff`)
- `server_args`: `-c 81920 -np 8 -fa on -ngl 999 -ctk q8_0 -ctv q8_0 --no-mmproj-offload`
- `server_env`: `LLAMA_MTMD_FEAT_CACHE_DIR=/home/chao/feat-cache/q4km`
- unchanged from A′: `timeout_seconds 420`, `max_tokens 1024`, `id_slot per-sample`,
  `prompt_order evidence-first-system-v2`

One profile serves both arm families: bare arms use ~1k of a 10,240 slot (KV
over-allocation costs no measured decode speed — M1), evidence arms fit to the measured
ceiling. Substrate baselines for new work: fixed windows + `tail=0` + `trim=0` +
`obs_batch_slices 8` (`fixed-batch-bare8` / `-matched8` / `-mismatched8`).

## Fragment naming, provenance, and authorship of this re-lock

Named per-workload references exist beside the canonical lock:
`qwen3-omni-llamacpp-q4km-a2-evid.json` (byte-equivalent to the canonical shape) and
`qwen3-omni-llamacpp-q4km-a2-bare.json` (`-c 16384 -np 8` tighter bare variant — probe A's
measured shape: 16 min, 18,738 MiB). Probe fragments `q4km-hbmfree-np8*.json` are audit
provenance. A′'s bytes stay authoritative in history:
`git show 5fae758:configs/model/qwen3-omni-llamacpp-q4km.json`.

Authorship record: this re-lock was packaged by two concurrent sessions working the same
checkout after probe B finalized — the babysitter session wrote the in-place canonical
re-lock, the composition-test update, this document, and `fixed-batch-mismatched8`; the
planning session wrote the a2-named fragments, the experiment plan
(`2026-08-12-a2-experiment-plan.md`), and a parallel verdict since consolidated into this
document. Commits `da8f9a4` and `328e6f8` therefore carry mixed authorship (the planning
session's `git add -A` swept in-flight babysitter work); coherence of the merged tree was
verified twice (37/37 composition tests; full gate suite 1,223 passed / 9 skipped).
Single-writer discipline for one checkout is an open owner call.

## Determinism statement (honest, unchanged from the slice-parallel adoption)

Runs are not byte-deterministic under concurrent slots; the measured run-to-run WER noise
floor on this substrate is **0.11 pp** (vs ±3.2 pp mean / 13.6 pp per-sample on the old
protocol). Pairing discipline: contrasts run on the same config hash, same split, and are
read against the 0.11 pp floor.

## Cache lifecycle (owner policy, 2026-08-11 discussion)

Features are per-experiment materialization, not a second dataset: warm the cache before a
campaign (one cold pass; cold-miss cost 3.32 s/slice GPU or 6.79 s CPU), persist per
model-quant dir (`feat-cache/q4km`, ~1.5 MB/slice) while reused, delete freely — every
feature is reproducible from (pinned audio bytes, pinned build). The cache never holds
gold/reference material; keys bind audio bitmap hash + media ordinal only.

## Dispositions

- **np16 — REVERSED for the bare arm by measurement** (2026-08-12, SAEA-BENCH-hbmfree-np16,
  attempt 340b84): with encode fully cached, featcache+np16 ran the same 102-slice load in
  **14.0 min vs np8's 16.0 (−12.5%)**, WER 0.1393 on the floor, 0 skips / 0 saturations /
  0 timeouts, peak 19,558 MiB. The np4→np8 aggregate-flatness result does NOT extrapolate
  to np16 once the encoder leaves the device; the prediction recorded in the first version
  of this section was wrong, and the owner's push to measure was right. Bare lock updated
  in place: `-a2-bare` = `-c 32768 -np 16` (dispatch baseline `fixed-batch-bare16`).
  Evidence-arm np16 stays excluded by capacity (+4.4 GB KV vs 2.3 GB free at the legal
  10,240 slot); the np10 probe (`-c 102400 -np 10`, SAEA-BENCH-hbmfree-np10-evid,
  attempt a9e405) came back NEGATIVE: 21.0 min vs np8's 20.1 (+4.5%), WER 0.1528 in-band,
  clean run (0 quarantine, 102/102 truncated=0, peak 23,174 MiB) — the np16 flip is
  short-context-specific; long evidence contexts decode slower per token and 10-way
  splitting lengthens tails. **Evidence shape locks at np8; the config chapter is closed**
  (bare np16 / evidence np8, both by measurement; np24/np32 recorded as
  feasible-but-not-pursued — expected <1 min marginal against certain 420 s-timeout tails
  at ~1.1–1.3 tok/s per slot). The stock np16short registration (commit 95272dc) stands
  unlaunched — superseded by the featcache-form measurement.
- **Stock (unpatched) build**: retired from the baseline; receipt kept for provenance.
- **Comparability break**: A″ is a new config era. Nothing measured under A/A′ pairs with
  A″ numbers; E-002F tail-era reads (incl. R4 n=10) are provenance, and R4 re-reads on the
  clean floor are queued as E-005.

## Receipts

- Probe A: `$SPEECHRL_DATA_DIR/runs/SAEA-BENCH-hbmfree/attempt-20260812T141853Z-c54874/`
- Probe B: `$SPEECHRL_DATA_DIR/runs/SAEA-BENCH-hbmfree-evid/attempt-20260812T144825Z-fce635/`
- Ledger rows: SAEA-BENCH-hbmfree, SAEA-BENCH-hbmfree-evid (carrier-cell amendment
  recorded in-row; zero calls spent under the refused registration)
- Gate suite after re-lock: 1,223 passed, 9 skipped (2026-08-12)
