# Status 035: SLURP matched pair sealed; complete scoring and E21 analysis active

Date: 2026-09-11T12:57:24.166421+00:00. This turn made progress: completed the speech arm,
verified both raw parents and joined derivatives, released the two-arm read,
started complete SLURP scoring, and added the shared raw saved-score
settlement path needed for E21.

## GPU cohort and custody closed

The same-process SLURP comparison completed exactly 4,000 generation calls
and 12,004 actual-fit endpoints. Each arm has 1,000 direct and 1,000 slots
contacts and 1,000 final outputs. Both worker processes exited zero and both
root leases were released normally. Speech worker session 24915 and lease
session 20954 are terminal; do not restart them.

The model remains resident: serving-slurp-live-program-matched-np4-v1,
server PID 35780, root wrapper PID 35765 / session 49170, monitor PID 35824 /
session 62129. Generation/scoring source remains frozen at 21ebe2bc in
/home/chao/saea-worktrees/slurp-program-matched-generation. No encoder was
loaded and no feature was newly encoded.

| Arm | Raw manifest SHA-256 | Fit-inclusive GPU hours |
|---|---|---|
| Control | 55b063174c635a921844f8b0acc3fc1a12bf7a5c6748b4e6fd75776b9bd55797 | 0.21377297687994107 |
| Speech | 0857e6342896613bf06fa2c9ce4a55b59f41e98e86b748e64a90e41c2727da42 | 0.2364384910623232 |

Pair utilization cost is 0.4502114679422643 GPU hours against 1.0, with both
arms below their shared fit-plus-generation 0.5 caps. Pair energy is
0.04799783497199085 kWh. Each arm used 5,769.58737500002 speech seconds.
Root independently rehashed the closed snapshots and recomputed both integrals;
coverage is complete, using the registered right-endpoint/max-20-second rule.
Keep the missed handoff and initial source-packet validation times from STATUS-034.

Authoritative DATA cost receipts:
- coordination/slurp-program-matched-control-external-cost-v2.json:
  d81d0575880fbc317c2a7248bf463bd227a032bd9ee5b757bc0473376d47a0a4.
- coordination/slurp-program-matched-speech-external-cost-v1.json:
  dfe1a0395f819d815948f6e5855afeef80e06ec59f9b5584e8e08694edee3f2a.

## Released joined deliveries and complete scoring

The post-seal release was committed before either derivative was built:
DATA coordination/slurp-program-matched-postseal-read-release-v1.json,
SHA-256 017126f53c3da6914270e8aa063d8e926514e03975059120d16c85aec6ddce77;
exposure SAEA-SLURP-MF-PROGRAM-MATCHED-POSTSEAL-SCORE-READ-V1.

Both registered joined deliveries verified with 1,000 outputs each and zero
additional contacts. Their manifest hashes are:
- Control: ca5a6368a262d8b147efc7ed5f8ddd61e7ace74402cee65b131001163e145c75.
- Speech: 7692f280830fcb20bea8a1eeb57e4230aacce044af46026f24c011e63ca3b7b2.

DATA coordination/slurp-program-matched-joined-deliveries-v1.json has
SHA-256 2126602cbce9d4dcdfe5269764193303d096287cdb4bd8039c446359971f84bb.
Raw parents were not changed. The shared batch is now active under root:
session 96331, batch PID 42461, initial control scorer PID 42463.
It runs exactly two whole official jobs sequentially with include_per_sample
and explicit frozen source/data/lock context. Log:
DATA coordination/slurp-program-matched-complete-scores-v1.log.
Do not start a second scorer or repeat the batch on an observation timeout.

## E21 scoring complete; saved analysis active

Both full official scores completed once under frozen source 64440737:
- Direct result SHA-256:
  68d2792a22f0901aa7fd8261210d6dbfee5971aae6e5678aa85ded3a93e53682;
  complete receipt 2a8aa24693d3fdfcf7c0aec31a2b7a8d93fa55e5905d9e336e0da8937f337d1d.
- Repair result SHA-256:
  ae4ddb5a0a0877b290c2642b992e24dd7c7e310ecdac028b58eb4c196284f58a;
  complete receipt 1acba8ac3247e02d2ec14daf8df54ac2c1c8175b0363dd800a66c46fe8429198.

Direct and repair complete-score elapsed times were 1929.26 and 1912.13 seconds.
The single whole-call alignment scorer was computationally active; retain this
named CPU scoring tail. E21 repair session 78549 is terminal and no E21 official
scorer remains active. aligned_scoring_views is now running the frozen saved
readers and comparisons under DATA; root retains scientific decision authority.

## Shared settlement correction

The actual E21 experiment Git blobs contain no derivative declarations.
Delivery-only settlement does not apply. Commit 22af3394 adds
settle_scored_attempt and verify_scored_attempt_settlement in the existing
settlement module, sharing atomic publication, independent verification and
exact-retry finalization. It refuses parents with any recorded derivative duty.
The complete saved score is reused; raw bundles are never rescored or rewritten.

Validation: 112 relevant tests passed, shared module branch-enabled coverage
81 percent, Ruff and engineering-base check passed. The real synthetic
generation-to-saved-score-to-settlement flow is covered. See
docs/readiness/2026-09-11-raw-saved-score-settlement.md. All running experiment
and scoring checkouts were left unchanged.

## Next actions

1. Wait for root SLURP score session 96331, verify both complete receipts,
   bind the unchanged analysis template and run the saved-score comparator.
2. Review E21 whole-call primary, numeric/nonentity/insertion/WER guards,
   strata, costs and valid secondary window attribution; write the verdict.
3. Review SLURP NEW500 row-F1 primary, pooled micro, equal-scenario and
   intent/scenario/action/malformed/saturation guards; preserve the old failure.
4. Settle E21 raw attempts through the new saved-score path only after root
   review. Settle SLURP raw parents through their registered scored derivatives.
5. Update the results ledger, reproducibility instructions and full-scope audit.
   Held S4 exemplars and the unproven live E21 review/selection/new-observation
   path remain explicit. No adaptive repeat or extra GPU busywork is admitted.
