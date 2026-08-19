# Scheme scoreboard — speech-as-knowledge on a frozen local core (LIVING DOCUMENT)

Owner goal (2026-08-19, standing): find an agent-technology scheme, on the existing local
frozen model, in which speech signals are MODELED INTO knowledge and multimodal knowledge is
EFFECTIVELY CONSUMED with task-performance gains — demonstrated with CONSISTENT improvement
across small-scale explorations. This document is the running consolidation: what
consistently works, what consistently fails, and the current best-scheme statement. Updated
at every consumed read. (Registration/verdict docs remain the evidence of record.)

## Current best-scheme statement (v1, 2026-08-19)

**Two-tier architecture on the frozen core:**
- **Routing tier (high-order semantics — intent, tool, QA candidate):** whole-utterance
  representation matching or closed-set prompting. No word-level resonance channel exists
  here; risks are classic ICL biases. EVIDENCE FOR: closed-set decode routing works
  (A1'r 60/60 non-fallback, 47/60 gold agreement); label-space supply dominates gains
  (A2 +0.29 of A1's +0.46). UNDER TEST: embedding-matching routing (P-EMB-1/2, pending
  E-0 feasibility), few-shot routing gain and bias (P-FEW, machinery in build).
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
  embeddings (under test), (b) percept-aware supply filtering (designable), (c) corrective
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
| Closed-set decode routing viable | ✅ 1/1 (A1'r) | 60/60 non-fallback |
| Refusal evidence-gated (A2T) | ✅ 1/1 (V1) | 11/11 vs 2/11 — carrier-specific vs SLURP |
| Embedding routing | ⏳ P-EMB-1/2 (E-0 gating) | — |
| Few-shot routing gain/bias | ⏳ P-FEW (flying next) | — |
| Router-confidence targeting | 🔜 P-TARGET (needs P-EMB) | — |
| Corrective confusable supply | 🔜 design queue | — |

## Design queue (small probes, each ≤0.5 GPU-h, registered one at a time)

1. **P-FEW** (registered, machinery in build) — routing few-shot gain + bias.
2. **P-EMB-1** (SLURP scenario routing) + **P-EMB-2** (A2T tool routing, headline = recovery
   on the 183 supply-unreachable ids) — after E-0 feasibility.
3. **P-TARGET** — router confidence as the supply-targeting signal (merges the two open
   problems); design after P-EMB reads.
4. **P-CORR** (corrective confusable supply) — supply the CORRECT side of the core's own
   confusion pairs (percept-aware, from consumed A0 wrong-value inventory + legal roster
   intersection): the constructive twin of P-TRAP's destructive result.
5. **P-STRIP-AUG** (V4's named confound) — stripped-augmenting vs stripped-replacing on the
   97 EM-correct ids: is the regression channel registry-loss or defaults-stripping?

Consistency bar for declaring the scheme (goal condition): each load-bearing mechanism ≥2
independent probes agreeing in sign; the composed scheme (routing tier + targeted filling
tier) demonstrated end-to-end on at least two carriers with positive net signed accounts.
