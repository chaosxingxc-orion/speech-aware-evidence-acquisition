# Serving-configuration verdict: mmproj stays on the GPU, `-np 4` stays (2026-08-10)

> **RE-LOCK 2026-08-11 (config A′).** After the pre-registered cacheorder
> re-verification passed all three predictions (wall −37%, 121/124 cache
> hits, WER 0.2575 inside the noise band, no systematic digit loss), the
> locked fragment gained three deltas — `id_slot: "per-sample"`,
> `prompt_order: "evidence-first-system-v2"`, `timeout_seconds: 420` — with
> server args unchanged. Evidence chain: SAEA-BENCH-idslot-q4km (diagnosis)
> → SAEA-BENCH-cacheorder-q4km attempts `dba5bf` (attribution) + `73488c`
> (re-verify) and the same-day saturation-quarantine fix. The A-vs-B/C
> verdict below is unchanged; this note is the config's continuation.

Reads the SAEA-BENCH-serving-q4km results (three completed attempts, study
commit `fb234a8`, fast-e21-sub3, identical bare-core-ojw arm) and locks the
deployment configuration for every subsequent arm. The bench was registered
2026-08-10 with a falsifiable prediction on record; this document is the
read-out, the decision, and the two findings that outrank the decision.

## The numbers

| config | model fragment | serving delta | attempt | net wall¹ | s/slice² | ×RT³ | mean WER | saturated |
|---|---|---|---|---|---|---|---|---|
| **A — LOCKED** | `qwen3-omni-llamacpp-q4km` | mmproj GPU, `-np 4 -c 49152` | `fd7ba3` | **22.8 min** | **10.8** | **5.5×** | **0.2359** | 0 |
| B — retired | `q4km-mmprojcpu` | mmproj CPU | `21a665` | 29.1 min | 14.0 | 4.3× | 0.2601 | 0 |
| C — retired | `q4km-mmprojcpu-np8` | mmproj CPU, `-np 8 -c 98304` | `230144` | 31.0 min | 14.9 | 4.0× | 0.3451 | 1 |

¹ attempt wall minus `gate_setup_seconds` (~78 s each).
² net wall / calls (A 126, B 125, C 125 — the counts themselves diverge, see
finding 2). ³ audio seconds processed per net wall second (~7,450 audio-s per
attempt).

Config A wins on every axis at once: 22% less wall than B, 27% less than C,
and the lowest WER. Peak VRAM confirms the mechanism the bench was designed
around: A 23,402 MiB, B 20,416 MiB — moving the mmproj off-GPU frees the
predicted ~2,940 MiB, and it buys nothing.

## Resolution of the pre-registered prediction

The registration said: if CPU audio-encode overlaps GPU decode, B/C match or
beat A; if llama.cpp serialises encode and decode per slot, B loses ~8%.

**There is zero overlap, and the loss is larger than predicted.** B's
per-slice delta over A is +3.2 s — almost exactly the measured +3.5 s
CPU-vs-GPU encode excess — i.e. the entire encode delta lands on the critical
path. The "~8%" figure was derived against a 64.4 s long-prompt request; on
this bare-core workload the same absolute delta is ~28% of net wall. C adds
insult: doubling slots to 8 on the vacated VRAM made it *slower* than B
(the workload is 3 samples, so slots 5–8 mostly idle while the bigger KV and
scheduling overhead are paid anyway) — and it produced the worst transcripts.

## Finding 1 (outranks the wall clock): serving configuration perturbs numerics

The pre-registered correctness expectation — identical WER across the three —
is **falsified**. Per-sample WER:

| sample | A | B | C |
|---|---|---|---|
| 4366522 | 0.1532 | 0.2262 | 0.2551 |
| 4387383 | 0.2466 | 0.2737 | 0.4316 |
| 4389907 | 0.3080 | 0.2805 | 0.3486 |

The divergence is noise-like, not uniform degradation (B *improves* 4389907),
and it is large — ±3–7 pp per sample from mmproj placement alone. Under C,
sample 4387383 additionally hit one runaway-repetition slice (699 insertions,
capped by the `max_tokens: 1024` saturation flag doing exactly its job).
Mechanism: mmproj-on-CPU computes the audio embeddings with different kernels
and accumulation order; at temperature 0 near-tie logits then take different
branches, and `-np 8` changes ubatch composition with the same effect.

Consequences, binding:

- Serving arguments are **load-bearing for comparability**, not an
  engineering convenience. They stay inside the config hash (already the
  case), and the locked A arguments may not change mid-campaign for any
  reason short of a new registered bench.
- Absolute WERs remain comparable only *within* one serving configuration.
  All existing scientific rows (SAEA-E-001, the completed E-002 nocontext
  attempt) already ran under A's arguments; they remain internally valid.

## Finding 2: the perturbation propagates into segmentation

The three attempts produced **different slice counts** (126 / 125 / 125) on
identical audio: divergent transcripts move the model-guided boundary
estimate, which moves every later slice. Serving numerics therefore compound
through the OBS loop rather than averaging out — one more reason the
configuration is frozen rather than "equivalent within noise".

## Open item: run-to-run determinism under the locked config

> **CLOSED 2026-08-11 — NON-DETERMINISTIC.** The repeat (attempt `54a5e7`,
> same config hash `dc67f633…`) diverged from `fd7ba3` on every sample:
> 114/129 slice responses differ, slice counts 126 vs 124 (boundary cascade),
> mean WER 0.2359 → 0.2680. Run-to-run noise floor: ±3.2 pp on the 3-sample
> mean, up to ±9.6 pp per sample. Mechanism and consequences:
> `docs/readiness/2026-08-11-segmentation-efficiency-frontier.md` §2 and the
> exposure-ledger read-out of the same date. The paragraph below is the
> pre-repeat state, kept as written.

A fourth attempt (`639d36`, config A again) was launched as determinism
repeat 1 — same arm, same split, same commit, twice, byte-compare — and
ABORTED before its first request: the freshly-loaded llama-server process
died between "server is listening" and the first invoke; the session layer
refused the touch fail-closed (`pid … is not a live process`), 0 calls
metered. This is an environment failure, not a config one. The question it
was to answer is still open and still matters: findings 1–2 prove
*cross-config* divergence; whether *same-config* reruns are byte-identical
(as temperature 0 + fixed seed should give on identical batching) bounds the
noise floor under every paired delta this study will read. The registered
SAEA-BENCH-serving-q4km envelope (1,500 calls / 60,000 audio-s / 10 gpu-h;
376 calls / 22,340 s consumed) still covers both repeats.

## Actions taken with this verdict

1. `configs/model/qwen3-omni-llamacpp-q4km.json` is the **locked deployment
   configuration** — unchanged, since it already encodes the winner; all
   registered plans and hashes stay valid.
2. `configs/model/q4km-mmprojcpu.json` and
   `configs/model/q4km-mmprojcpu-np8.json` are **deleted** (bytes preserved
   at `fb234a8`). A rejected-but-live config fragment is an accidental-reuse
   hazard; reintroducing either requires a new registered bench.
3. The exposure ledger's SAEA-BENCH-serving-q4km row gains a dated read-out
   note; `docs/arms/serving-bench.arms` gains the result annotation.
4. Unblocked next: register and run the SAEA-E-002F fast R4 set (their two
   2026-08-10 launch attempts were correctly gate-refused for having no
   ledger rows), then the full R4 re-run — all under locked A, ~22 min per
   fast arm at 10.8 s/slice.
