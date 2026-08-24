# Scheme scoreboard — speech-as-knowledge on a frozen local core (LIVING DOCUMENT)

Owner goal (2026-08-19, standing): find an agent-technology scheme, on the existing local
frozen model, in which speech signals are MODELED INTO knowledge and multimodal knowledge is
EFFECTIVELY CONSUMED with task-performance gains — demonstrated with CONSISTENT improvement
across small-scale explorations. This document is the running consolidation: what
consistently works, what consistently fails, and the current best-scheme statement. Updated
at every consumed read. (Registration/verdict docs remain the evidence of record.)

## Current best-scheme statement (v5, 2026-08-23 — decoder-joint speech×text-key matching is
## the strongest speech-native lever; controllers unvalidated; knowledge-plane baseline program adopted)

**v5 headline (M-line, EFFECT-C108, read 2026-08-22):** the speech-native decoder-joint path
that v4 named as "open" now has its first strong positive — carrying the original speech
packet plus maintainable TRAIN-built text keys into the frozen decoder scores **K1-M1 90/108
vs direct K0-M0 77/108 (net +13)** on a train-only discovery split; key-text shuffle collapses
to **0/108** (the keys are load-bearing) and speech-swap drops to 75/108 (speech-sensitive).
This is bounded discovery evidence, not validation. Five external controller generations
(M5-v2, M6 always-refine, M7 multistate, M8 pairwise, M9 factor-graph) were all REJECTED
against their preregistered bars on the same near-ceiling SLURP routing surface (primary
89–95/108, oracle headroom 3–8); the 2026-08-23 owner rulings redirect controller validation
to structurally-headroomed surfaces (Audio2Tool 152 tools; earnings/ConEC) and to a DEV
optimization ladder — see `2026-08-23-knowledge-plane-baseline-rulings.md`, which also
decouples the GPU 95/90 serving gate from scientific admission (it remains the
engineering-baseline acceptance criterion). The v4 statement below stands as evidence context.

## Prior best-scheme statement (v4, 2026-08-21 — register alignment measured; decoder-joint path remains open)

**Two-tier architecture on the frozen core:**
- **Routing tier (high-order semantics — intent, tool, QA candidate):** whole-utterance
  representation matching or closed-set prompting. No word-level resonance channel exists
  here; risks are classic ICL biases. EVIDENCE FOR: closed-set decode routing works
  (A1'r 60/60 non-fallback, 47/60 gold agreement); label-space supply dominates gains
  (A2 +0.29 of A1's +0.46). **SECOND WORKING LEVER (2026-08-20, P-EMB-3M M4): cascade
  routing** — frozen-core self-transcript → dedicated text embedder → argmax cosine,
  0.7500 on the same 60, within 2 samples of decode routing and scaling to a large label
  side without prompt growth; text-mediated, so it is not a speech-native lever. P-EMB-4R
  removes the former blanket audio-embedding refutation: register-aligned GLAP
  utterance-to-utterance kNN reaches 0.3167 and fires REGISTER-RESCUE, while LCO-3B/7B
  remain weak at 0.1500/0.1167 under the pooling override. The rescued signal is still far
  below direct speech classification (0.8167) and does not qualify independent pooled
  embedding/kNN as the main method.
- **Filling tier (low-order semantics — slot/argument values):** decode-path generation
  governed by the supply law. CONSISTENT positives: elicitation-bank supply (values or
  stripped structure) converts MISSING-type failures (L3 +0.42/+0.44; L5 [8,10]/120,
  form-robust). CONSISTENT negatives: (1) word-level acoustic resonance — wrong entries
  echoing the core's own percept capture decode 29/32 (supply-side filtering duty);
  (2) in-context concrete values re-open injection (34→2→22 series); (3) blind replacing
  supply on already-correct samples regresses 36/97 — **supply targeting was the open
  problem and is now ANSWERED by percept-keying (P-CORR-F): keying every emitted slot on the
  core's own output needs no confidence gate, and makes blind replacement's failure mode
  structurally unreachable (untouched samples get byte-identical prompts). The duty that
  REPLACES it is supply-side FILTERING — the core admits wrong percept-keyed entries at 85.7%,
  so supply precision is the whole safety margin**; (4) compositional failures (tier3+tier8)
  are supply-immune everywhere; (5) percept-keying reaches only 67% of samples (20/60 emit
  nothing keyable), so a keyed layer always needs a coverage layer beside it.
- **Speech-as-knowledge (the goal's core question):** participation of acoustics in supply
  USE is PROVEN (P-TRAP); net VALUE of audio in the supply loop over self-transcription is
  unresolved (P-KEY I=+0.046, CI crossing zero; ~89% text-side realizable at L3).
  The scheme's speech-native lever is therefore currently: (a) routing-tier speech
  representations — **independent pooled embedding/kNN is insufficient, not universally
  content-absent (P-EMB-4R): GLAP register alignment rescues a weak 0.3167 signal, LCO remains
  scoped and weak, and neither tests joint frozen-decoder matching**; the next method keeps
  the original speech features in every decision call and matches them jointly against
  maintainable text keys inside the frozen decoder, while the strong cascade result remains
  diagnostic-only because it is text-mediated, (b) percept-aware supply filtering — **promoted from designable to REQUIRED
  AND SPECIFIED (P-CORR-F): the core passes 85.7% of wrong percept-keyed entries through, so
  the filter must sit OUTSIDE the frozen core**, (c) corrective percept-keyed supply —
  **✅ WORKS (P-CORR-F CORRECTIVE-PERCEPT, consumed 2026-08-20): +0.0508 full-60 / +0.0753 on
  the 40 mechanism-usable, driven by a 96.7%-vs-0.0% self-vs-cross percept gate**.

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
| Register-aligned utterance-to-utterance kNN | ⚠️ **WEAK RESCUE, NOT AN EFFECTIVE METHOD (P-EMB-4R, consumed 2026-08-21)** — A-GLAP reaches **19/60 = 0.3167** and recall@5 0.5667, firing the registered REGISTER-RESCUE clause and disproving the blanket claim that every audio embedding construction is content-absent. A-LCO3/A-LCO7 remain weak at 0.1500/0.1167 and pooling-override scoped. The best speech arm remains 30 correct samples below FS-NONE (49/60). T-QW reaches **52/60 = 0.8667** with recall@5 0.9333, proving the utterance-text key space is strong after text mediation, but it is not speech-native. C-DECODE was canceled before the read and made zero contacts. The branch conclusion is limited to independent pooled embedding/cosine/kNN; joint speech-feature × text-key decoder matching remains untested. **Post-consumption design input (2026-08-23 mean-centering re-analysis, no verdict clause): the modality cone is real and large on the LCO arms (query centroid norm 0.94) — per-modality mean-centering lifts a-lco3 0.1500→0.5000 (0.5167 with hubness correction, stack-scoped), HURTS the already-aligned a-glap (0.3167→0.2333), and leaves every audio arm far below text (best 0.5167 vs t-qw 0.8333); query-side centering is deployable (leave-one-out-identical constant offset). KB-BUILD stays text-key-first; audio keys re-enter as a secondary centering-mandatory dimension with encoder choice reopened (LCO, not GLAP).** | `2026-08-21-pemb4r-verdict.md`; `2026-08-23-pemb4r-meancenter-reanalysis.md` |
| Routing by CASCADE (frozen-core self-transcript → dedicated TEXT embedder) | ✅ **CASCADE-ROUTES 1/1 (P-EMB-3M M4, consumed 2026-08-20)** — T0 self-transcripts (consumed P-KEY-2 artifacts) → `qwen3-embedding-0.6b-gguf` text↔text argmax cosine = **45/60 = 0.7500**, i.e. 2 samples below A1′r (0.7833) and 4 below FS-NONE (0.8167), **+40.683 over its own shuffle expectation**, 17/18 labels reachable with no attractor (top-1 share 0.1667), errors semantically adjacent (largest cell `music→play` 2), winning cosines 60/60 positive at mean **+0.6030**. Jitter-robust: the qwen3-emb repeat pair clears the declared ≥0.9999 tolerance (0.9999006) but its **argmax is NOT stable** on a null synthetic string (margin 0.000485); under the adversarial 2δ bound at most 5 scored correct predictions could flip → **40/60 = 0.6667, still above the 0.65 floor**. **Text-mediated, so NOT speech-native**: it extends the P-KEY ~89 %-text-side pattern to representation matching and inherits every transcription error. Its leverage is a label side that scales to 152 tool rows without prompt growth | `2026-08-20-pemb3m-verdict.md` |
| Few-shot routing gain/bias | ❌ INERT-ish (P-FEW: Δ exactly 0.0000, CI [−.067,+.067]; skew costs −0.067 generic ICL noise, ZERO prior capture; equivalence not certified — band 0.05 < measured ±0.033×2 noise) | `162cca3` |
| Router-confidence targeting | 🔜 P-TARGET **descoped to the routing tier** (2026-08-20 design analysis over consumed artifacts): the A2T gate simulation is NEGATIVE — no threshold on any measured decode-path signal (chars AUC 0.765, completion-tokens AUC 0.794, args) yields a positive net over the 217; best sweep result = supply nothing (net 0); blind supply = −28, reproducing V4. The 8 conversions sit inside the regression-densest length band — length separates regressors from non-regressors but NOT converters from regressors. Only positive rule is tier1-structural (+5): post-hoc, benchmark-label, non-deployable. Routing-tier signal is real (two-arm in-session disagreement precision 0.50, lift 2.73 re-confirmed) but structurally blind to the concentrated `play` cluster (flags 1 of 6; 5 errors are prompt-unanimous) → P-TARGET-P1 = closed-set routing + logprobs (60 calls; llama-server logprob usability unverified — feasibility check first; prior 0/17 earnings negative disclosed) | design dossier 2026-08-20; pemb2 synthesis §5.3 |
| Corrective supply (percept-keyed) | ✅ **CORRECTIVE-PERCEPT 1/1 (P-CORR-F, consumed 2026-08-20)** — the filling tier's first TARGETING-FREE positive lever with a dose-matched control. Δ₁ = SLU-F1(W1 self) − SLU-F1(W2 cross) = **+0.0508**, 90% CI **[+0.0098, +0.0968]** on the registered full 60, and **+0.0753**, CI **[+0.0179, +0.1411]** on the 40 mechanism-usable samples (20/60 fly K=0 with **byte-identical W1/W2 prompts, verified 20/20**, so the mechanism denominator is 40 not 60). Arm SLU-F1 W1 **0.6588** / W2 0.6080 / W3 0.4336 / W4 0.6366. **THE PERCEPT GATE IS BINARY AND NEAR-TOTAL**: capture of supplied corrective entries = **96.7% self-percept vs 0.0% cross-percept** at identical dose and roster base, 100% for W3, and **95.1% keyed vs 11.9% retrieval-widened inside a single W4 prompt** — P-TRAP with the sign flipped exactly as pre-declared, isolated by three independent contrasts. **But the gate does not inspect correctness**: 12 of W1's 14 non-gold entries were emitted (**85.7%**), and the marginal effect over the dose-matched control is **+7 gold slots recovered against +12 spurious values emitted** (dual measurement W1 53/12, W2 46/0, W3 27/14, W4 48/18). F1 still rises because a type repair converts a simultaneous FP+FN into a TP (slot_f1_exact +0.0824). **Supply precision is therefore the entire safety margin** — W4's widening to 41% value precision gives back 0.0222. Q-2 **DOSE-INSUFFICIENT** (Δ₂ = −0.1625 vs pinned A3 0.5961) but only through the 33% zero-supply blind spot: restricted to K>0, Δ₂ = **−0.0380**, i.e. 1.5 entries/sample buys ~94% of a 100-entry roster where it acts. The roster's value is COVERAGE, not per-sample strength → keyed layer + coverage layer, not either. Guardrails clean (parse 1.0000, copy 0.0000 all arms). Carries a disclosure: **the byte-identical-resend floor is NOT 0.0000 on this stack** — 6 of 20 identical-prompt pairs diverged at temperature 0 / `-np 4` (aggregate 0.0072) | `2026-08-20-pcorrf-verdict.md` |

| Speech-native decoder-joint matching (speech packet × TRAIN-built text keys, in-decoder) | ✅ **WORKS AS DISCOVERY EVIDENCE 2/2 (GATE18 embedded K1-M1 16/18 vs direct 15/18; EFFECT-C108 K1-M1 90/108 vs K0-M0 77/108, net +13)** — key-text shuffle collapses to 0/108, speech-swap 75/108 (below matched but above the frozen 24-gap mechanism bar, so speech sensitivity is established at the weaker tier); mmproj-free serving; every contact carries the original packet. Train-only discovery; no validation claim | `2026-08-21-speech-native-agent-loop-training-free-rl-plan.md` (EFFECT-C108 replacement read sha256 `6f7017fb…f40a`) |
| External AgentLoop controllers over the joint matcher | ❌ **REJECTED 5/5 (M5-v2, M6 always-refine −1 vs primary with 4 helpful/5 harmful, M7 multistate, M8 pairwise, M9 factor-graph)** — every generation missed its preregistered bar on a near-ceiling surface (primary 89–95/108; oracle 94–100/108; action-variable 14–31/108); episodic/OOF policies (A1b, A1d) selected retain-primary 108/108. Diagnosis (2026-08-23 rulings): saturated surface + sparse action support, partly a sample-size artifact; controller validation moves to structurally-headroomed surfaces + the T500/DEV ladders. **E108 (M11 adaptive evidence-gap, consumed 2026-08-23) confirms terminally: support gate FAILED 6/8 (action-variable 14<24, boundary acquisitions 7<18, oracle gain 2<6, reachable 96<100), controller deferred unevaluated; primary 92/108 on the fresh split with oracle 94 — the gap is 2. BUT the adaptive acquisitions that did fire were perfect: 4/4 helpful prediction changes, 0 harmful (+2/0 factor-side) — ACQUIRE-on-registered-gap is precise, merely starved on a saturated task. T500 not spent (its own clause). Successor: identical machinery on Audio2Tool** | plan doc A1–A1i; `2026-08-23-e108-verdict.md` |
| GPU serving gate (saturated median/P10 ≥95/90) | ⚠️ **UNMET after 7+ engineering cells (np32, q128, global-branch, n-gram 63% acceptance, MoE CUDA-graph, cross-slot batching, hot-prefix line)** — mean occupancy 94–96% throughout; every remedy class formally closed; **2026-08-23 owner ruling: decoupled from scientific admission; retained as the engineering-baseline acceptance criterion** (next admissible idea: tail work-stealing across slot-affine trajectories) | plan doc "GPU execution requirement" + `2026-08-23-knowledge-plane-baseline-rulings.md` §2.1 |

## Design queue — SUPERSEDED 2026-08-23

The owner's knowledge-plane baseline program (`2026-08-23-knowledge-plane-baseline-rulings.md`)
supersedes this queue: items 4–6 below (P-CORR-R, P-TARGET-P1, P-STRIP-AUG) are formally
PARKED, never having been registered; the A2T cascade successor candidate is absorbed into the
Audio2Tool surface work. The active program is: C4 contract scale fixes → C2 DEV-ladder
receipts + split gate → C1 train-scale KB-BUILD (datastore-size axis, coverage,
decontamination) → C3 first cross-task policy (multi-dim recall → rank fusion → percept-keyed
supply filter → α-blend consumption) → E108 under the decoupled gate → Audio2Tool cell →
DEV-100/500/1000 optimization → baseline freeze. The historical queue is preserved below as
the record of what was and was not registered.

## Historical design queue (small probes, each ≤0.5 GPU-h, registered one at a time)

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
   **P-EMB-4R** — ✅ consumed 2026-08-21: **REGISTER-RESCUE(a-glap) +
   KNN-BEATS-LABEL-MATCH**, with C-DECODE canceled. Register alignment exposes a weak
   speech-side signal but does not close the gap to direct speech classification; the
   independent pooled kNN branch is no longer the main successor. The open successor is
   decoder-joint speech-feature query × text-key matching under the frozen-core boundary.
4. **P-CORR-F** — ✅ **consumed 2026-08-20: CORRECTIVE-PERCEPT + DOSE-INSUFFICIENT**
   (see the consistency ledger row and `2026-08-20-pcorrf-verdict.md`). **P-CORR-R** (routing
   twin) is now unblocked and registers next, with four design constraints this read imposes:
   (i) the core cannot arbitrate among supplied candidates — at 96.7% capture with no
   correctness inspection, a confusable-neighbourhood MENU yields emissions, not a choice, so
   P-CORR-R must arbitrate outside the core or supply exactly one candidate per slot;
   (ii) percept-keying is a usable ON/OFF admission switch (96.7% keyed vs 11.9% unkeyed,
   measured inside one prompt); (iii) pair the keyed layer with a coverage layer and report its
   own K=0 population before any verdict; (iv) **P-CORR-R MUST fly an explicit
   byte-identical-resend control arm** — its disagreement signal is a difference between two
   responses, and this stack returned different responses to identical prompts on 6/20 pairs at
   temperature 0, which would masquerade as disagreement.
5. **P-TARGET-P1** — routing-tier logprob confidence only (A2T arm killed by the gate
   simulation); registers after P-CORR-R. **Note from P-CORR-F**: the filling tier's targeting
   gap that motivated part of this item is now closed by percept-keying; P-TARGET-P1 stays
   routing-tier-scoped, and the filling tier's live successor question is supply-side
   FILTERING (rejecting wrong percept-keyed entries before supply), not targeting.
6. **P-STRIP-AUG** (V4's named confound) — stripped-augmenting vs stripped-replacing on the
   97 EM-correct ids: is the regression channel registry-loss or defaults-stripping?

Consistency bar for declaring the scheme (goal condition): each load-bearing mechanism ≥2
independent probes agreeing in sign; the composed scheme (routing tier + targeted filling
tier) demonstrated end-to-end on at least two carriers with positive net signed accounts.
