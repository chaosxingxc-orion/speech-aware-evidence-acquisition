# Stage-2B candidate qualification — DRAFT for owner review

Date: 2026-08-18. Status: **DRAFT** — becomes the frozen paper candidate on owner approval;
until then no claim below is citable outside this repository. Carrier: this study
(Stage-2 endpoint = qualified paper candidates; manuscript work is Stage-3, prohibited here).

Working title: **"Signed supply: a two-channel, content-gated law of prompt-level knowledge
supply for a frozen speech-capable omni core."**

## 1. Evidence base (all consumed, one-shot, registered)

Eight consumed registered reads on two speech carriers, all under the study's fail-closed
probe discipline (pre-registration with mechanical branch rules → flight with no result
reading → coordinator-reviewed pinned read suite → single read → ledger flip):

| Read | Carrier | Verdict | Record |
|---|---|---|---|
| P-SLU | SLURP devel n=60 | UNRESOLVED (rule-gap) | `2026-08-18-pslu-verdict.md`, `d8b71a5` |
| A2T A0 | audio2tool 400 | +30.0pp real gap; 120 headroom | `2026-08-18-pa2t-a0-verdict.md`, `ec25706` |
| A2T Stage-2 | headroom 120 ×4 arms | COPY-TRAP | `2026-08-18-a2t-s2-verdict.md`, `5269eee` |
| A2T Stage-2b | headroom 120 ×2 | Q-A CONFIRMED-CUT; Q-B INCONCLUSIVE-B | `2026-08-18-a2t-s2b-verdict.md`, `c9ee811` |
| A2T Stage-2c | headroom 120 ×3 | ROBUST; CHANNEL-REOPENED | `2026-08-18-a2t-s2c-verdict.md`, `88ebaf5` |
| P-SLU s2 | SLURP n=60 ×2 | KNOWLEDGE-BEYOND-FORMAT; SELF-SCOPING-WORKS | `2026-08-18-pslu-s2-verdict.md`, `dbac0bc` |
| Loss decomposition | 3 consumed attempts | DRIFT-CONFIRMED | `2026-08-18-a2t-loss-decomp-verdict.md`, `e67e2e8` |

(The A0 read is one of the eight; exposure rows in `docs/exposure-ledger.md` carry every
flight receipt, budget, and integrity line.)

## 2. Claim–evidence matrix

**C1 — Prompt-level legal supply converts real failures on a frozen core, at two task
levels.** L5 (tool calling): on the 120 samples where the core already selects the right
tool but fails the call, the values-stripped row converts **[8, 10]/120** across three
renderings (envelope, form-ROBUST); the full row converts 16/120. L3 (slot SLU): a legal
train-mined roster lifts SLU-F1 by **+0.4220** (undirected, 100 entries) and **+0.4352**
(self-scoped, ~36 entries/call, phase-1 closed-set mapping 60/60 non-fallback) — **94.6% of
the gold-scoped ceiling gain**. Boundary: conversion is exactly **zero on all 45
compositional samples** (tier3 multi-intent + tier8 intent-blending) under every supply form
flown. *License: descriptive, discovery-split, n=120/n=60; no superiority claims.*

**C2 — The harm channel rides supplied VALUES, and any in-context values, not structure.**
Full-row supply injects supplied default values at 2:1 against its own conversions (34 vs
16; dilution keeps all 34 while losing 31% of conversions). Stripping `argument_defaults`
cuts injection **34→2 (−94.1%)** at half the conversions — benefit:harm moves 0.47:1 →
**4:1**. In the deployment augmenting position the registry body's own defaults re-open the
channel (**22 induced**, 0.32:1) even though the appended row carries no values; the
selection channel stays clean there (all 7 selection losses are parse-fails). *The cut
requires values absent from the WHOLE context — an ORG-side action, not a retrieval choice.*

**C3 — Wrong-content supply neither converts nor drags.** A highlighted wrong tool row:
conversion **1/120** (below the noise floor), induced **0**, per-axis profile identical to
zero supply; mechanically, only **3/21** of its selection losses go to the highlighted tool
(inside the 12.5% selection-noise band) — the losses are format collapse (12/21) and
near-synonym drift (5/21). *Corollary: retrieval precision demands are far lower than
assumed — a wrong retrieval is nearly free; a right one pays only in clean form.*

**C4 — The benefit is content, not shape.** A format-matched filler roster (identical
`type=value` rendering, non-ontology content) scores **−0.0385 vs zero supply**: pure shape
buys nothing. Against that control the knowledge component defends **+0.4605**. The
deranged-roster gain that broke the original branch lattice (+0.1346) is therefore carried
by its real in-domain type vocabulary, not by format — and the wrong-row/right-row augment
contrast (1/120 vs 7/120 conversions on identical construction) shows content deciding both
channels' direction.

**C5 — Deployment reading (SUPPLY/ORG/USE).** The clean supply form is "supply structure,
withhold values"; it is form-robust but unreachable by augmentation over an intact
registry — deployment needs a value-stripped context (ORG) or replacing supply. Legal
self-scoping works (closed-set label choice; oracle-selection premium closes to within the
0.03 separability bar). Silence-swap controls (0/6 persisted across both carriers) tie all
gains to the audio; under silence the core confabulates confident well-formed commands —
recorded as a safety observation.

## 3. Bounds and honesty ledger (travel WITH every claim)

1. All numbers are single-run point estimates on discovery splits (SLURP devel seed
   20260807 n=60; audio2tool frozen-400 headroom n=120); run-to-run variance is unmeasured
   except the SLURP duplicate-condition floor (±0.013 SLU-F1) and the A2T selection-noise
   band (12.5%); EM-conversion counts have no measured variance.
2. Zero-margin flags: B1's 8/120 cleared its floor with zero margin (it is the envelope
   minimum, robust upward); ROBUST's induced clauses cleared by 1–2 raw counts;
   CHANNEL-REOPENED fired at 22 vs floor 20 (the 11× step over [2,4] is
   threshold-independent).
3. Q-B Stage-2b stays INCONCLUSIVE-B by its registered letter (retention clause on a
   too-noisy axis); the content conclusion rests on Stage-2c/loss-decomp corroboration.
4. Format hygiene is form-sensitive on unregistered axes (permutation doubles parse
   failures; C1 30/30 empty/parse) — reported, not claimed.
5. tier1_direct slot-F1 columns are definitional artifacts (zero-argument golds).
6. Licenses: SLURP audio CC BY-NC 4.0; Audio2Tool CC BY-NC 4.0 — NC carried on every
   audio-derived number. No test split was touched anywhere.

## 4. What Stage-3 would need (sketch only; not authorized here)

Pre-registered confirmatory versions of C1/C2/C4 on dev-optimized → test-reported protocol
(program split philosophy); measured run-to-run variance first (cheap re-fly block);
ORG-side value-stripped registry implemented as the deployment method under test; scale
beyond n=120/60 with power set from the measured variance; the compositional-failure
boundary (C1) as an explicit negative result.

## 5. Owner decision requested

- Approve (or amend) the claim set C1–C5 and the working title → this document is
  superseded by a frozen `…-QUALIFIED.md` with hash-pinned evidence bundle;
- or name deltas (additional probes / restatements) before freezing.
