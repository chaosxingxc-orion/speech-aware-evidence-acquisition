# A2T Post-Contact Arbitration Headroom V1 Preregistration

## Question

Before spending another model contact, determine whether the sealed contract-preserving matched
response surface contains enough paired save/harm headroom for a future training-free controller
that observes both M0 and matched responses and chooses which one becomes final.

This is a bounded model-free audit, not a policy experiment. It does not ask which runtime feature
predicts a save or harm. It asks only whether the paired return surface makes post-contact
arbitration mathematically worth investigating.

## Frozen inputs

- Run: `SAEA-A2T-MF-POSTCONTACT-HEADROOM-V1`.
- Discovery split: the already-exposed 104-row `A2T-CPV2-104` cohort, run identity
  `401a28684adea908c80363df0815c9ce04b0ffa46a654975b129d4b69e60f8a1`.
- M0 outputs SHA-256:
  `9efc91d7362e40255a25d099b3fb464b32ca87228f96c4db5c0aba0edcbdf400`.
- Matched outputs SHA-256:
  `4f41183d01a5246a76944ad48843936fb8fe08907a84f55784079feb0c1afc9b`.
- Cohort receipt SHA-256:
  `8f47922124c61f92fee03273c1165eb1f8f97048d910ddd4a6a7243906d78783`.
- Gold and registry are read only through the existing governed Audio2Tool loaders and unchanged
  item scorer. The test split, unexposed population, G2, and FINAL60 stay closed.

## Computation

For each frozen identity, score M0 and matched with the unchanged exact item scorer. Emit aggregate
counts only:

1. `save`: M0 exact-wrong and matched exact-correct;
2. `harm`: M0 exact-correct and matched exact-wrong;
3. `both_correct` and `both_wrong`;
4. raw output-text changed/unchanged;
5. parse rescue, parse loss, both parse, and neither parse;
6. M0 exact count, matched exact count, always-matched net, oracle-selector exact count, and oracle
   improvement over always matched.

The oracle selector is descriptive only: it chooses matched exactly on save rows and can never be a
runtime policy. Its improvement over always matched equals the harm count and is used only as a
headroom identity check.

## Gates and consequence

The audit is viable only if all frozen identities align, both files match their SHA-256 pins, all
104 rows score, the paired count partition sums to 104, and the arithmetic identities hold.

`postcontact_headroom_present` requires all of:

- at least four saves;
- at least two harms;
- always-matched exact net at least +2;
- oracle exact net over M0 at least +4;
- oracle improvement over always matched at least +2.

These thresholds are feasibility floors, not a controller policy. Passing authorizes only a
separately preregistered, zero-model-contact controller screen on these already-exposed outcomes.
That screen must freeze its runtime-visible state and nonparametric rule before reading conditional
reward strata. Failing closes post-contact arbitration for this surface. Neither outcome authorizes
a new speech flight, approximately-1,000 scale, baseline promotion, test access, or Stage-3 work.

## Prohibitions

- No model, retriever, embedding, tokenizer, paid API, or network contact.
- No per-sample outcome publication.
- No reward breakdown by candidate feature, tier, state, transcript property, evidence property,
  tool, argument, or query block.
- No policy fit, policy evaluation, threshold search, bin search, nearest-neighbor choice, or action
  recommendation.
- No mutation of any sealed input, manifest, score, attempt, or receipt.
