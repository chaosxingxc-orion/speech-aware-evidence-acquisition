# P1 loop-ceiling verdict — the 2x2 decomposition (2026-08-14)

SCOPE AMENDMENT (2026-08-15, owner discussion): "ceiling" throughout means the ceiling of
STATIC-BIAS delivery (knowledge as prompt-prior). The reflection family (span audio + own
errored draft + retrieved reference, verify-with-abstention) is a different inference
operator, unmeasured here (the D vehicle failed first), and not bounded by these numbers.

Runs: SAEA-P1-relisten (B), SAEA-P1-static (C), SAEA-P1-replay (D); arm A = reused
SAEA-E-005B-zero (14.48). fast-e21-sub3, 90s era, v3 shape, locked instruction, oracle
materialization p1-oracle-v1 (14 gold-selected terms; ceiling probe, deployment-illegal by
design). Registered commit 592b24f; adversarial-review amendment wf_f412e338. Offline reads:
derived/entity-wer/SAEA-P1-*/ (adapter entity-wer-v1); macro from each attempt's scores.

## Numbers

| arm | macro WER | entity correct /1310 | entity-WER |
|---|---|---|---|
| A locked-zero (reused) | 14.48 | — | — |
| B forced re-listen, zero knowledge | 14.56 | 782 | 40.31 |
| C static oracle prompt | 14.99 | 751 | 42.67 |
| D oracle replay + exemplar bank | 23.53* | 672* | 48.70* |

*D is mechanically invalidated on 4389907 (see defect below); on the two clean samples D ~ C
(12.36 vs 12.10; 13.75 vs 12.91) with ZERO replay acceptances.

Targeted read (occurrence counts of the 14 oracle terms in final texts, B -> C):
Aldeyra 0->6, EUDARIO 0->1, McMullin 0->1, NIAID 0->2, gonna 0->2, Compumedics 0->1,
Frenz 0->2, Horne 0->1, Ching 0->1, ifeng 0->6(lower)/1(cased); missed: wanna,
Livingstone, Tribecca, eCommerce. **10/14 flip under C vs 0/14 under B, correct casing.**

## Pre-registered decompositions

- Re-listen effect B-A = +0.08pp: **nil**. Targeted re-listening alone pays nothing
  (9 windows, 6 splices accepted, aggregate unmoved).
- Static-delivery knowledge C-A = +0.51pp aggregate, -31 entity tokens: **net negative at
  the call level — but 10/14 targeted flips.** Oracle knowledge converts on target; the
  collateral tax on non-targeted entities (~-50 tokens) exceeds the targeted gain (~+20).
- Knowledge-in-replay D-B and replay-over-prompt D-C: **not evaluable as designed** — two
  mechanical failures (below) prevented replay from ever delivering a candidate.

## The two mechanical findings

1. **Flag targeting misses entities 17/17.** Every logprob-flagged span on the clean samples
   is function-word/boundary text ('with a', 'for the', 'increase by', 'final regulatory');
   zero overlap with the real entity errors the oracle candidates answer. The correction
   filter then (correctly) finds no candidate similar to the flagged words and skips every
   replay call. The loop's binding constraint is FLAG->entity targeting, not retrieval, not
   delivery.
2. **Pass-1 exemplar hijack (defect).** The fixed-legal-context-replay arm declares
   exemplar_bank in its D2-frozen field set, and the pass-1 slice-parallel path threads
   ctx.exemplar_bank into EVERY slice request (obs_loop pass-1 reuse; by design for the
   static exemplar-context arm, inherited unintentionally here). With the one non-empty
   own-history bank (4389907, ecommerce span), the core transcribed the exemplar audio
   instead of slice content: the exemplar sentence appears 17x in D's final text (0x in B,
   1x in C = the real occurrence), output 6.5k chars short, 1116 deletions, 44.49 WER.
   MM-3's flight shares this exposure surface; CHECKED same day: MM-3's outputs carry no
   repeated-exemplar signature (its mm5-selfsup-v2 labels are short common-word spans; no
   label string repeats in any output) — MM-3's WER-level reads stand, the hijack risk is
   specific to long own-call exemplar spans. Fix direction: a replay-scoped bank
   must not ride pass-1 — either a pass-1-suppressed bank resolution for obs-replay-loop or
   a separate arm whose D2 field set declares exemplar_bank for replay requests only.

## Gate decisions (as pre-registered)

- P5/P7 investment gate "D-B > 0 on the entity ledger": **FAILS as measured** (672 vs 782).
  Recorded with cause: the replay vehicle never delivered knowledge (findings 1-2), so this
  is a verdict on the vehicle, not on knowledge value (C's 10/14 flips).
- Delivery fork "D ~ C": **fires.** Per the pre-registered rule this MANDATES re-wording the
  frozen candidate hypothesis before P6: the claim becomes TARGETING / small-N supply; the
  "every static supply interface fails" clause is struck; prompt-delivery runs co-primary
  with splice-delivery in P6.

## Tax decomposition (same-day offline analysis, alignment-mask diff vs arm B)

The C-A "collateral tax" is, at this dose, an ORTHOGRAPHIC FORMAT ARTIFACT, not recognition
damage: on 4366522, 59 of C's 68 arm-only reference misses are digit-form tokens (2020, 30,
2191, ...) — C spells numbers as spoken words (digit tokens 49->3, "twenty twenty" 5->17)
while the reference uses digits; B's arm-only misses contain ZERO digit refs. The other two
calls show no net format effect. Recognition-wise C is at parity with B while flipping 10/14
targets. Retroactive check on the E-005 family (same method): the n=10 matched-locked tax
(+60 errors) has SYMMETRIC digit shares (63/237 vs 36/116) — the full-dose tax is real
recognition churn, so the tax law survives at n=10 and the format artifact dominates only at
small N. Separately, the ctxinstr instruction variant alone swings >100 digit tokens
(E-005F-nocontext-ctxinstr −162 errors vs zero): number format is a volatile,
instruction-controlled axis, and every cross-framing aggregate-WER comparison needs a
format-normalized secondary read (analysis-only; the frozen scorer stays primary).

## Redirect

The program's next measurable question is no longer "does knowledge help" (it does, 10/14 on
target) but "how to deliver it without the collateral tax": (i) entity-aware flagging
(draft-NER + rare-word + logprob fusion — the P5-lite RECOVER-style arm covers this); (ii)
slice-local / span-local candidate injection instead of whole-call static supply; (iii) the
deployment-legal candidate source (call metadata, P0.3) — "Aldeyra" is derivable from the
call's own metadata, so C's strongest flip is reproducible deployment-legally.
