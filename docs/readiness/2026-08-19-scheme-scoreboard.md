# Scheme scoreboard — speech-as-knowledge on a frozen local core (LIVING DOCUMENT)

Owner goal (2026-08-19, standing): find an agent-technology scheme, on the existing local
frozen model, in which speech signals are MODELED INTO knowledge and multimodal knowledge is
EFFECTIVELY CONSUMED with task-performance gains — demonstrated with CONSISTENT improvement
across small-scale explorations. This document is the running consolidation: what
consistently works, what consistently fails, and the current best-scheme statement. Updated
at every consumed read. (Registration/verdict docs remain the evidence of record.)

## Current best-scheme statement (v2, 2026-08-20 — routing tier gains the cascade lever)

**Two-tier architecture on the frozen core:**
- **Routing tier (high-order semantics — intent, tool, QA candidate):** whole-utterance
  representation matching or closed-set prompting. No word-level resonance channel exists
  here; risks are classic ICL biases. EVIDENCE FOR: closed-set decode routing works
  (A1'r 60/60 non-fallback, 47/60 gold agreement); label-space supply dominates gains
  (A2 +0.29 of A1's +0.46). **SECOND WORKING LEVER (2026-08-20, P-EMB-3M M4): cascade
  routing** — frozen-core self-transcript → dedicated text embedder → argmax cosine,
  0.7500 on the same 60, within 2 samples of decode routing and scaling to a large label
  side without prompt growth; text-mediated, so it is not a speech-native lever. AUDIO
  embedding routing is refuted on every construction flown (chat-core 3/3, dedicated
  LCO scoped 1/1); the best audio-side number in the program is a CONTROL at 0.1333.
- **Filling tier (low-order semantics — slot/argument values):** decode-path generation
  governed by the supply law. CONSISTENT positives: elicitation-bank supply (values or
  stripped structure) converts MISSING-type failures (L3 +0.42/+0.44; L5 [8,10]/120,
  form-robust). CONSISTENT negatives: (1) word-level acoustic resonance — wrong entries
  echoing the core's own percept capture decode 29/32 (supply-side filtering duty);
  (2) in-context concrete values re-open injection (34→2→22 series); (3) blind replacing
  supply on already-correct samples regresses 36/97 — **supply targeting is the open
  problem**; (4) compositional failures (tier3+tier8) are supply-immune everywhere.
- **Speech-as-knowledge (the goal's core question):** participation of acoustics in supply
  USE is PROVEN (P-TRAP); net VALUE of audio in the supply loop over self-transcription is
  unresolved (P-KEY I=+0.046, CI crossing zero; ~89% text-side realizable at L3).
  The scheme's speech-native lever is therefore currently: (a) routing-tier audio
  embeddings — **CLOSED for now (P-EMB-3M): every flown construction is refuted, the
  dedicated arm only scope-refuted behind a build defect, and the strongest candidate
  (nemotron) never flew**; the routing tier's cascade lever that replaced it is
  text-mediated, (b) percept-aware supply filtering (designable), (c) corrective
  confusable-pair supply (design queue).

## Consistency ledger (per mechanism, across probes)

| Mechanism | Consistent? | Evidence trail |
|---|---|---|
| Label-space/structure supply helps | ✅ 4/4 (A2, B1, C1, C2) | +0.29 L3; [8,10]/120 L5 envelope |
| Wrong-content supply inert (augmenting) | ✅ 3/3 (B2, A4-reread, loss-decomp) | 1/120; drag 3/21 |
| Value-copy channel cut by stripping | ✅ 2/2 (B1, C1/C2) | 34→[2,4] |
| Augment re-opens in-context values | ✅ 1/1 (C3) | 22 induced |
| Self-percept resonance captures decode | ✅ 1/1 (P-TRAP) | 29/32 vs 0/32 |
| Blind supply regresses correct answers | ✅ 1/1 (V4) | 36/97 vs 0/97 baseline |
| Closed-set decode routing viable | ✅ 2/2 (A1'r 0.7833; P-FEW FS-NONE 0.8167 — cross-session ±2 samples) | the routing tier's ONLY working lever |
| Refusal evidence-gated (A2T) | ✅ 1/1 (V1) | 11/11 vs 2/11 — carrier-specific vs SLURP |
| Label-level supply has NO resonance channel | ✅ 2/2 (P-FEW skew capture 0/59 incremental; P-EMB no audio→label signal) | the arc's founding premise, now evidenced |
| Embedding routing — GENERATION-CORE pooled states | ❌ REFUTED 3/3 (P-EMB-1 EMB-WEAK 3/60 below chance, attractor collapse; P-EMB-2 EMB-CLOSED 2/183 at chance, 400/400 negative cosines, richer text made it WORSE; P-EMB-3L LOCAL-EXHAUSTED — all three constructions 3/60 = 0.0500, the instruct prefix narrowing the reachable label set from 5 to 2) — SCOPE widened by P-EMB-3L: this now refutes EVERY training-free construction the pinned build can express (bare/instructed × the pooling flag), not only mean pool; it never tested a DEDICATED semantically-aligned embedding model — P-EMB-3M has now done so, see the next row. BUILD DEFECT FOUND: `--pooling` is INERT on this build's audio side (L1 audio 60/60 byte-identical to consumed P-EMB-1), so last-token audio pooling was never actually tested — **and P-EMB-3M reproduced the same defect on LCO, so it is a property of the build, not of one model** | `6ebcaba`, `af99ebe`, `063c056` |
| Embedding routing — DEDICATED omni-embedding model, AUDIO side (pinned tool, charter retriever clause) | ❌ **EMB-WEAK-SCOPED 1/1 (P-EMB-3M, consumed 2026-08-20)** — LCO-Embedding-Omni-3B GGUF returned **3/60 = 0.0500**, below uniform chance, below its own shuffle expectation (3 vs 3.283), 5/18 labels reachable with 60 % of the mass on `recommendation` and `calendar` never predicted; 60/60 winning cosines positive but near-orthogonal (mean +0.0707), median top-1/top-2 margin 0.00737. **SCOPED, NOT model-level**: the pre-flight POOLING-DIFFER gate fired `POOLING-OVERRIDE-PRESENT` (two LCO boots, `--pooling mean` vs `last`, byte-identical audio vectors), reproducing the P-EMB-3L build defect on a second, entirely different model — LCO is a last-token-pooling model that this build never ran in last-token pooling. Control GLAP (audio-TYPE) reached **0.1333 with 16/18 labels and +4.750 over its own shuffle expectation** — the first audio-side arm to beat that baseline, still far under the 0.30 floor, and a control. **CONTROL-ANOMALY did NOT fire (0.1333 vs 0.7500), but against GLAP alone**: the CLSP speaking-STYLE control was DROPPED-RUNTIME-ERROR (transformers 5.12.1 vs pinned 4.57.3) and the style confound is untested. UNTESTED: nemotron escalation (the only candidate with measured audio-content retrieval, NC license + pinned transformers branch), CLSP re-entry, and any non-llama.cpp LCO stack — all environment changes | `2026-08-20-pemb3m-verdict.md` |
| Routing by CASCADE (frozen-core self-transcript → dedicated TEXT embedder) | ✅ **CASCADE-ROUTES 1/1 (P-EMB-3M M4, consumed 2026-08-20)** — T0 self-transcripts (consumed P-KEY-2 artifacts) → `qwen3-embedding-0.6b-gguf` text↔text argmax cosine = **45/60 = 0.7500**, i.e. 2 samples below A1′r (0.7833) and 4 below FS-NONE (0.8167), **+40.683 over its own shuffle expectation**, 17/18 labels reachable with no attractor (top-1 share 0.1667), errors semantically adjacent (largest cell `music→play` 2), winning cosines 60/60 positive at mean **+0.6030**. Jitter-robust: the qwen3-emb repeat pair clears the declared ≥0.9999 tolerance (0.9999006) but its **argmax is NOT stable** on a null synthetic string (margin 0.000485); under the adversarial 2δ bound at most 5 scored correct predictions could flip → **40/60 = 0.6667, still above the 0.65 floor**. **Text-mediated, so NOT speech-native**: it extends the P-KEY ~89 %-text-side pattern to representation matching and inherits every transcription error. Its leverage is a label side that scales to 152 tool rows without prompt growth | `2026-08-20-pemb3m-verdict.md` |
| Few-shot routing gain/bias | ❌ INERT-ish (P-FEW: Δ exactly 0.0000, CI [−.067,+.067]; skew costs −0.067 generic ICL noise, ZERO prior capture; equivalence not certified — band 0.05 < measured ±0.033×2 noise) | `162cca3` |
| Router-confidence targeting | 🔜 P-TARGET **descoped to the routing tier** (2026-08-20 design analysis over consumed artifacts): the A2T gate simulation is NEGATIVE — no threshold on any measured decode-path signal (chars AUC 0.765, completion-tokens AUC 0.794, args) yields a positive net over the 217; best sweep result = supply nothing (net 0); blind supply = −28, reproducing V4. The 8 conversions sit inside the regression-densest length band — length separates regressors from non-regressors but NOT converters from regressors. Only positive rule is tier1-structural (+5): post-hoc, benchmark-label, non-deployable. Routing-tier signal is real (two-arm in-session disagreement precision 0.50, lift 2.73 re-confirmed) but structurally blind to the concentrated `play` cluster (flags 1 of 6; 5 errors are prompt-unanimous) → P-TARGET-P1 = closed-set routing + logprobs (60 calls; llama-server logprob usability unverified — feasibility check first; prior 0/17 earnings negative disclosed) | design dossier 2026-08-20; pemb2 synthesis §5.3 |
| Corrective supply (percept-keyed) | 🔜 **P-CORR-F REGISTERED 2026-08-20** with a scope correction: the phonetic-confusable population is EMPTY on this carrier (0/37 pairs share a phonetic key); the real channel is TYPE-NAME collision (68/95 emitted slots use out-of-vocabulary types). Construction = gold-free L1 TYPE-LOOKUP: mean 1.02 entries/sample covers 36/89 gold slots, beating the A3 100-entry roster (29/89) at ~1% dose. Pre-declared: P-CORR-F is P-TRAP sign-flipped — recovery AND contamination both measured. Routing twin P-CORR-R (confusable-neighbourhood re-ask, disagreement-complementary: the two signals catch DISJOINT error populations) designs next | `2026-08-20-pcorrf-preregistration-REGISTERED.md` |

## Design queue (small probes, each ≤0.5 GPU-h, registered one at a time)

1. **P-FEW** (registered, machinery in build) — routing few-shot gain + bias.
2. **P-EMB-1** (SLURP scenario routing) + **P-EMB-2** (A2T tool routing, headline = recovery
   on the 183 supply-unreachable ids) — after E-0 feasibility. ✅ both consumed, both negative.
   **P-EMB-3L** (local construction sweep, owner's local-first order) — ✅ consumed 2026-08-20,
   **LOCAL-EXHAUSTED**: all three arms 3/60 = 0.0500, below chance; the local branch is closed and
   may not be re-cut. **P-EMB-3M** (dedicated omni-embedding model) was the surviving successor —
   ✅ consumed 2026-08-20, see item 3.
3. **P-EMB-3M** — ✅ consumed 2026-08-20: **EMB-WEAK-SCOPED (M1) + CASCADE-ROUTES (M4)**,
   CONTROL-ANOMALY not fired (against GLAP alone; M3 CLSP never flew). 3 of 4 arms flew.
   See both consistency-ledger embedding rows. **Successor candidate opened, NOT registered:**
   run the M4 cascade instrument on the P-EMB-2 A2T tool surface (400 samples × 152 tool
   rows, primary axis = the 183 supply-unreachable ids that P-EMB-2 measured audio-side at
   2/183 with 400/400 negative cosines). It needs its own registration, exposure row and a
   T0-transcript source check over the 400 A2T ids. Queue order below is unchanged; P-CORR-F
   machinery is now unblocked.
4. **P-CORR-F** — ✅ REGISTERED 2026-08-20 (scope-corrected to percept-keyed
   TYPE/NORMALIZATION-corrective supply; see the consistency ledger row). Machinery after
   P-EMB-3M's, now unblocked. **P-CORR-R** (routing twin) registers after P-CORR-F flies.
5. **P-TARGET-P1** — routing-tier logprob confidence only (A2T arm killed by the gate
   simulation); registers after P-CORR-R.
6. **P-STRIP-AUG** (V4's named confound) — stripped-augmenting vs stripped-replacing on the
   97 EM-correct ids: is the regression channel registry-loss or defaults-stripping?

Consistency bar for declaring the scheme (goal condition): each load-bearing mechanism ≥2
independent probes agreeing in sign; the composed scheme (routing tier + targeted filling
tier) demonstrated end-to-end on at least two carriers with positive net signed accounts.
