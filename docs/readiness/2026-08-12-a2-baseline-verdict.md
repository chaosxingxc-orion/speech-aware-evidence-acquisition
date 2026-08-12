# A″ (a2) serving-baseline verdict — featcache locks by vacating the GPU (2026-08-12)

Owner value rule that decided this lock: **"我是希望我们的方案能够腾出hbm,如果没法空出HBM的话,
我们的缓存方案没有价值"** — the feature cache is not a wall-clock optimization; its purpose is to
take the mmproj's 2.9 GB off the card and spend that HBM on configurations that were previously
impossible. Both halves were measured, not estimated, per the standing "不能靠观测去进行方案决策,
要实际跑出效果来,再lock" doctrine.

## The two receipts

**Probe A — the HBM claim** (`SAEA-BENCH-hbmfree`, attempt `20260812T141853Z-c54874`,
commit `a844649`): featcache warm + `--no-mmproj-offload` on the bare-core np8 substrate.

- Peak VRAM **18,738 MiB** vs 21,70x with mmproj resident → **−2.96 GB, the mmproj left the GPU**
  (load log: mmproj worst case 2,913.90 MiB, placed on CPU).
- Encoder invoked **0 times**; cache dir untouched at 806 features (mtime still 2026-08-11) —
  warm hits carry the whole run, so the config-B-era CPU-encode penalty (−26%, 2026-08-10 bench)
  never applies. That penalty was an encode-inline-era fact; with the cache warm the CPU mmproj
  is dead weight in RAM, not a compute path.
- WER **0.1397** — exactly the notail floor. Wall 16 min — in-band with np8short 16.1 /
  featcache-np8 15.5.

**Probe B — what the freed HBM buys** (`SAEA-BENCH-hbmfree-evid`, attempt
`20260812T144825Z-fce635`, commit `5fae758`): matched-evidence (ConEC contexts) np8 at
`-c 81920`, slice-parallel notail substrate, featcache warm, mmproj off-GPU.

- **Fits**: peak **22,114 MiB**, stable for the whole run (~2.3 GB headroom). With mmproj
  resident the same shape needs ~25 GB and does not fit — this is the configuration class that
  killed config C in the 2026-08-10 bench. The freed 2.9 GB is exactly the ticket.
- **No overflow**: 102/102 slot releases report `truncated = 0`; longest request 7,601 tokens
  against the 10,240/slot budget.
- **Wall 20.1 min** end-to-end (boot 1.5 + pre-cut + requests ~14.4 + finalize). Encoder 0 calls.
- Evidence-era comparison, same fast-3 split, same matched design:
  np4-sequential-ojw era (`SAEA-E-002F-r4-matched`, 2026-08-11): **~43 min, WER 0.2513**.
  This probe: **~20.1 min (−54%), WER 0.1498 (−10 pp)**. The WER gain belongs to the
  fixedwindow+notail substrate; the wall gain belongs to np8 + slice-parallel + hbmfree.

## Slot sizing came from measured prompts, not guesses

R4 trace extraction (2026-08-12): evidence-arm prompts max **7,611 tokens** (p50 ≈ 4.8–5.0k,
p99 ≈ 7.6k); bare prompts ≈ 1.0k. With `max_tokens` 1024 the worst request needs ~8.7k, so
**10,240/slot (`-c 81920` at np8)** replaces the ConEC-worst-case 12,288 guess. If a future
ConEC campaign genuinely packs ≥9.2k-token evidence, that campaign either drops np or caps the
SUPPLY budget as an explicit experimental parameter — not a silent serving-side trim.

## What is locked (A″ = a2)

Two serving shapes, both: pinned featcache build `5d9dfcb58` (receipt
`receipts/runtime-q4km-featcache.json`), `--no-mmproj-offload`, warm cache dir
`LLAMA_MTMD_FEAT_CACHE_DIR=/home/chao/feat-cache/q4km` (config-hashed via `server_env`),
`-fa on -ngl 999 -ctk q8_0 -ctv q8_0`, `id_slot: "per-sample"` sentinel,
`prompt_order: "evidence-first-system-v2"`, temperature 0, seed 20260803, max_tokens 1024:

- **`configs/model/qwen3-omni-llamacpp-q4km-a2-bare.json`** — `-c 16384 -np 8`. Substrate
  baseline: `configs/baseline/fixed-batch-bare8.json` (fixed windows, tail 0, trim 0,
  slice-parallel ×8).
- **`configs/model/qwen3-omni-llamacpp-q4km-a2-evid.json`** — `-c 81920 -np 8`. Substrate
  baseline: `configs/baseline/fixed-batch-matched8.json` (same, + matched conec-contexts).

The canonical fragment **`qwen3-omni-llamacpp-q4km.json` is re-locked in place** to the evid
shape (`-c 81920 -np 8`, hbmfree) — every existing arms invocation consumes the fragment by
name, so in-place is what makes the re-lock take effect everywhere without churn; the unit test
`test_q4km_repo_fragment_composes_with_the_expected_runtime_selection` asserts the new shape.
(This in-place edit + test update were authored by the concurrent babysitter session right after
probe B finalized and were swept into commit `da8f9a4` together with this document — recorded
here so the mixed authorship of that commit is on the record.) A′'s bytes remain authoritative
in history per the blob rule: `git show 5fae758:configs/model/qwen3-omni-llamacpp-q4km.json`.
The a2-named files are explicit per-workload references: `-a2-evid` is byte-equivalent to the
canonical lock; `-a2-bare` (`-c 16384 -np 8`) is the tighter bare-workload variant (16 min,
18,738 MiB); probe fragments (`q4km-hbmfree-np8*.json`) stay as audit provenance.

Cold-start rule: a corpus's first-ever pass pays CPU encode (~6.8 s/60s-slice) once under
`--no-mmproj-offload`. For campaigns on new audio, either accept the one-time cost or run one
GPU-mmproj warmup arm first; the cache dir persists per model key and the 806 fast/wave features
are already warm.

## What is rejected, with its evidence

- **np16** (`SAEA-BENCH-np16short` registered at `95272dc`, never launched, zero spend —
  superseded): aggregate decode ceiling ~26–27 tok/s is flat np4→np8 and encode removal lifts
  per-slot decode only +6–7% (p50 3.27→3.47), so 16-way splitting buys ≤2–3% and lengthens
  tails. The registration stands in the ledger as an unconsumed pre-registration.
- **Wall-clock as featcache's justification**: measured gain was 4% (15.5 vs 16.1) — below any
  lock bar. The lock rests on the HBM purchase alone.

## Honest bounds

- Determinism: the slice-parallel substrate is not byte-deterministic run-to-run; measured WER
  noise floor 0.11 pp (2026-08-12 twice-run). Paired reads must keep using per-sample pairing.
- n=3 fast-split walls carry single-run noise ~±0.5 min; the −54% evidence-era claim is robust
  to that, the 4% featcache wall delta is not (and is not load-bearing).
- Science flag, not a verdict: on the new floor, matched 0.1498 vs bare 0.1397 (n=3) — the R4
  context-value question re-opens on the clean substrate (R4-A2 below).
