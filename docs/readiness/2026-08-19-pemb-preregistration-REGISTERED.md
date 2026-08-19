# P-EMB-1/2 — embedding-tier routing probes — REGISTERED

Date: 2026-08-19. Status: **REGISTERED — flyable once the machinery lands** (GPU
time-shared: the embedding server cannot coexist with the generation server; flights take
idle windows in the M-line queue). Profile: `bounded-discovery-probe` (two runs, one
registration). Owner GO: the second-arc design order. E-0 feasibility (2026-08-19, scratch
report): pooled audio embeddings work AS-BUILT on the pinned llama.cpp via a separate
instance with `--embedding --pooling mean`; dim 2048, bit-deterministic, featcache-served
encoder pass. Binding decisions from E-0: **the pinned q4km GGUF** (the frozen-core
identity — E-0's Q8_0 was feasibility-only and is NOT the probe quant), `-ngl 999`,
`LLAMA_MEDIA_MARKER` pinned via env, **NO instruct prefix on either side** (E-0 measured
the prefix shifting the pooled vector more than swapping the audio does; bare-content
embeddings on both sides avoid the dilution asymmetry), L2-normalized outputs (cosine =
dot).

## 1. Questions

Routing-tier hypothesis (scheme scoreboard v1): can whole-utterance representation
matching recover HIGH-ORDER semantics on the frozen core — (P-EMB-1) canonical scenario
routing where free-form decode scored 6/360 exact hits, and (P-EMB-2) tool routing on the
183 samples where selection fails and no supply form can reach?

## 2. Run A — SAEA-PROBE-pemb1-78 (SLURP scenario routing)

Embed the frozen 60 devel samples' audio (bare, no prompt text) + the 18 canonical
scenario labels as text (bare label strings) = 78 embedding contacts, zero generation.
Prediction: argmax cosine(audio, label). Scoring-side gold scenarios. Comparators (CITED):
A0 free-form decode (6/360 exact scenario hits ≈ 0.10 accuracy at best), A1'r closed-set
decode routing (47/60 = 0.7833).
- **EMB-ROUTES**: accuracy ≥ 0.65 (within ~0.13 of the closed-set decode router) — the
  embedding tier is a viable router at a fraction of the decode cost.
- **EMB-WEAK**: accuracy ≤ 0.30 — bare cross-modal matching does not form a usable shared
  space on this core; the routing tier stays decode-based.
- Otherwise **INCONCLUSIVE-EMB1** (report the confusion structure).

## 3. Run B — SAEA-PROBE-pemb2-552 (A2T tool routing; the 183 headline)

Embed all 400 frozen A2T samples' audio + the 152 tool registry rows as text (row text as
shipped) = 552 contacts, zero generation. Prediction: argmax cosine. Scoring-side gold
tools. Primary axes:
- **RECOVERY on the 183 tool-wrong ids** (the population no supply form reaches):
  **EMB-OPENS-183** if top-1 tool accuracy on the 183 ≥ 0.30 (≥55 recoveries — a
  deployment-meaningful dent) with top-5 reported alongside; **EMB-CLOSED** if top-1 ≤
  0.10; else INCONCLUSIVE-EMB2.
- **NON-DEGRADATION on the 217 tool-correct ids** (reported, no clause): top-1 accuracy vs
  the decode baseline 217/400; a router would only ever be composed as a rescue/argmax-
  fallback, so degradation here is informational.

## 4. Cost (registered ceilings)

Run A: ≤90 embedding calls; ≤400 metered audio-seconds; ≤0.2 GPU-h. Run B: ≤600 embedding
calls; ≤3,000 metered audio-seconds; ≤0.5 GPU-h (includes the one-time embedding-server
load). Embedding contacts ARE frozen-core contacts (encode+pool, zero sampling) and are
ledgered as calls.

## 5. Discipline

One-shot read per run; pinned suite (`analysis/pemb_read.py`, cosine matcher + verdict
evaluators + confusion tables) built and coordinator-reviewed BEFORE the reads; exposure
rows at registration (consumed=no); embedding vectors are derived artifacts (data root,
hashed manifests, never in Git); gold labels/tools scoring-side only; the embedding server
runs the PINNED q4km + mmproj with `--embedding --pooling mean` on its own port and never
coexists with a generation flight; SLURP CC BY-NC 4.0 and Audio2Tool CC BY-NC 4.0 carried.
