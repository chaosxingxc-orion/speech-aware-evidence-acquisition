# DEV-100 literature-consistency review (reviewer perspective)

Date: 2026-08-24. Provenance: coordinator-directed web survey under the owner's
reviewer-elevation directive; companion to `2026-08-24-dev100-reviewer-audit.md`.
Iteration-tier design input; no verdict clause attaches.

## Verdict

The campaign's gain profile is **consistent with the recent literature and sits in the
upper-middle of the published envelope** — anomalous in neither direction. Closest published
comparable: **kNN-Prompt (EMNLP 2022)** — train-datastore retrieval over a frozen LM on weak
zero-shot classification baselines, 56.2 → 69.6 average (+13.4; per-task max +28.9). Our dev
result (+15 observed through +24 at the α-.45 cell, on a 48% base) is above that average and
below that maximum, at a comparable baseline. The closest SPEECH comparable, RASU
(Interspeech 2024), realized only +0.83 EM from acoustic-key retrieval against a measured
oracle-prompt headroom of +11.95 on a fine-tuned 73.3-EM baseline; our larger realized share
of the oracle headroom is principled — we retrieve on the model's own first-pass answer text
(the HyDE mechanism, ACL 2023), not on acoustic similarity, which RASU's authors themselves
name as their limitation.

## Key comparisons

1. **The 48% zero-shot floor is plausible and, if anything, high.** Same-or-near-identical
   60-way intent set: gold-text ChatGPT 0-shot 79.25 (He & Garner, Interspeech 2023);
   MASSIVE gold-text 7-13B instruct models 10.3-35.5, flan-t5-xxl 72.6, GPT-3.5 71.6
   (ILLUMINER, LREC-COLING 2024); AUDIO-input models 0.1-36.5 on Dynamic-SUPERB Phase-2's IC
   task (ICLR 2025). Our audio-native quantized 48 beats every audio-LLM row and four of
   five 7-13B text-mode models. The reviewer risk is inverted: the baseline may be called
   WEAK — the DEV-500 design therefore carries a stronger prompt-matched control.
2. **Gain magnitude obeys the literature's invariant** (gain scales inversely with baseline
   strength): strong/fine-tuned baselines yield +1..+5 (RASU +0.83, Tip-Adapter +1.7,
   flan-t5 few-shot +1.5); ~50% baselines yield +13..+35 (kNN-Prompt, ILLUMINER weak-model
   rows). Our own two settings reproduce the invariant internally: train-side base 71% →
   +13..15; dev base 48% → +15..24.
3. **Mechanism**: the confusable-neighbor damage channel and a top-k sweet spot are exactly
   what the RAG-as-noisy-ICL theory (arXiv:2506.03100, 2025) predicts; large bidirectional
   flip mass is the documented norm (Retriever Inconsistencies, ACL Findings 2024). Our
   per-sample W→C/C→W contingency accounting has NO published precedent found — it is
   reported as a contribution (with McNemar's exact test), not a replication.
4. **P-FEW = 0.0000 is NOT anomalous (coordinator correction to the survey's flag).** The
   survey noted weak-baseline literature predicts +17..+35 from plain exemplars and flagged
   our P-FEW null as a possible artifact. P-FEW, however, was flown at the STRONG-baseline
   decode-routing setting (FS-NONE 0.8167), where the same literature (ILLUMINER strong
   rows) predicts +1.5..+4.1 — and P-FEW's registered CI [−0.067, +0.067] covers that band
   entirely. No re-verification is required; the two regimes must not be conflated.

## Reviewer-standard requirements adopted for the DEV-500 confirmatory design

1. Paired uncertainty: bootstrap/CLT CIs on the PAIRED difference + McNemar's exact test;
   a-priori power framing (n=400 unexposed remainder → ~±4-5 pp SEs).
2. Determinism pinning: build commit + per-file GGUF SHA-256 + sampling config + a
   repeated-decode variance estimate at fixed configuration (round 5 supplies the first).
3. Bracketing ablations: (i) random-exemplar ICL control, (ii) random-retrieval from the
   same datastore, (iii) oracle-retrieval ceiling (the RASU GT-prompt pattern).
4. Frozen operating point, one-touch read on the UNEXPOSED DEV-500 remainder (DEV-100 is a
   nested subset — its 100 samples are excluded from the confirmatory statistic and reported
   separately), damage channel and per-class confusion reported alongside the gain.

Full citation list: He & Garner arXiv:2305.13512; ILLUMINER arXiv:2403.17536;
Dynamic-SUPERB Phase-2 arXiv:2411.05361; kNN-Prompt aclanthology 2022.emnlp-main.214; RASU
Interspeech 2024; Tip-Adapter arXiv:2207.09519; QZero arXiv:2406.15241; RAG-as-noisy-ICL
arXiv:2506.03100; Retriever Inconsistencies arXiv:2405.20680; KATE DeeLIO 2022; Luo et al.
TMLR 2024 arXiv:2401.11624; HyDE aclanthology 2023.acl-long.99; Miller arXiv:2411.00640.
