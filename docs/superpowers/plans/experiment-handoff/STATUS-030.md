# Status 030: matching preparation closed; E21 repair still generating

Date: 2026-09-11 UTC. Previous goal turn classification: PROGRESS. This turn completed full request-material verification, formal registrations, source freeze and final preflights while the authorized E21 repair continued. The full research goal remains active and incomplete.

## Live E21 custody

At 2026-09-11T04:16:50Z, the repair had written 22 complete call rows out of 44 and no final manifest. Worker 21509, lease holder 21472, server 1354, coordinator 637 and monitor 1389 were alive; GPU utilization was 64%, memory 19,776 MiB and power 95.14 W. Earlier zero-utilization samples were brief between-call waits; subsequent monitor samples showed healthy service, active slots and continuing task observations. No service restart occurred.

Preserve generation source /home/chao/saea-worktrees/e21-offline-repair-generation at 64440737a401b80805cfdd4f09d5a04748a3aad7. Worker tool session 99977 and lease session 22105 remain live. Root coordinator session 95670 holds the existing E21 service. Revalidate these handles; do not infer termination from a timeout or transient idle sample.

After full repair seal, verify all 1,593 windows / 44 calls, the fresh direct-parent lineage and complete manifest; close immutable external costs; then release only the root generation lease. Stop the old service through the shared serving stop entry only after that custody closure. The coordinator watches its serving wrapper and cleans up its own monitor when the wrapper exits; do not guess a stdin stop command. The new direct parent and fit evidence remain in STATUS-028.

E21 scoring is prepared but not run. Use coordination/e21-offline-score-comparison-execution-source-v1.json (SHA-256 265476f1431d5c6c4beb7e639eabcccff589a3cca91ebe9022fbac3d9601fa9a), with the fixed 64440737 source and explicit ScoringContext. Complete each whole-manifest score once, retain per-sample statistics, then run the frozen whole-call primary comparison. Do not read quality/reference material before the repair seal or a formally closed comparison hold.

## SLURP preparation is closed

The speech wire check completed successfully: 2,000 synthetic requests across the full 1,000-row roster. Receipt coordination/slurp-program-matched-speech-full-wire-v1.json has SHA-256 be85feef616b5e33fdf45e5b44253d1b926cce3779468cd3bc0a5cf0866cba5e. Both wire processes are finished; do not rerun them.

The first root raw-payload comparison remains HOLD, SHA-256 c3d1ac0ed4cb9e96cb71cdc0173f3b183be6a55d55377ed0ad5540cd595a5176. That criterion included request IDs, audit provenance and dynamic slot routing, making it stricter than the approved model-context match. The correction is an additive, named input-material review before any new model or outcome contact, not a revised quality guard.

An independent saved-trace audit passed, then root independently reread all 4,000 recorded synthetic requests, matched their raw hashes to the original wire fingerprints and recomputed the common history rendering. Results: all 1,000 first-stage prompt-material projections match; all 1,000 second-stage projections match after removing only the declared supply contrast. Treatment supplies exactly five TRAIN facts per row; null supplies zero. max_tokens=256, seed=20260803 and temperature=0 match everywhere. id_slot differs on 757 first-stage and 775 slots-stage rows, reflecting the existing dynamic slot pool. request_id is not forwarded to the server; evidence_provenance is audit metadata. Do not claim raw HTTP equality, identical scheduling or guaranteed identical responses.

Root verdict coordination/slurp-program-matched-root-wire-verdict-v1.json, SHA-256 6ddf799922869f1adcdbad502acea13287efc9fb91b909f52669b1f9cf6da927, pins both synthetic trace files and all source evidence. Independent audit SHA-256 is 79bdea4b908881e880366c0888ad8609693398a0ee8981b1f0391df8cd9c7962. The old HOLD receipt remains unchanged. STATUS-029's requirement for identical raw payload bytes is superseded by this exact prompt/sampling review; the approved prompt/program/feature matching requirement remains intact.

The new recall artifact remains SHA-256 7295b85d86f0392afbdec7a06a798d7c94a13ef0d11f73d64f812ca8701ac820, with complete output equality to its original 1,000-row source. Cell readiness changes preserve its normalized preparation-input identity. No further preparation or config adjustment is planned.

## Frozen source and registrations

Use one source for the new service and both arms:

- Worktree: /home/chao/saea-worktrees/slurp-program-matched-generation
- Commit: 21ebe2bc8f9c03469a48fe0c68e9b31f1c360dff
- Branch: codex/slurp-program-matched-generation
- Python: /home/chao/.venvs/speechrl/bin/python, literal PYTHONPATH to that source/src and PYTHONDONTWRITEBYTECODE=1

All four formal ExecutionPlans and exposure rows are committed. Plans are under docs/readiness/2026-09-11-slurp-program-matched-v1/{control,speech}-{generation,fit}-plan-v1.json. Owner011's exact one-pair limits remain 4,000 planned / 4,200 maximum generation contacts, 12,004 actual-fit endpoints and 1.0 utilization-integrated GPU hour for the family. Each arm's 0.5 GPU-hour limit includes its fit and generation intervals; the separate plan caps are not additive. Preserve 6,000 speech seconds per arm and every original analysis guard. No new repeat is authorized if this pair fails.

| Arm | Final config hash | Final protocol hash |
|---|---|---|
| Control | 0fe0bd857099c632360d0f9618beaeef6ecb298b718197d887f45ab82f994a45 | da64d7529359c6fa8a3ce9430f3250717f981b3416a74df07b8e79a47d8b8c70 |
| Speech | 899a057106f9d2a9b361ec9f9b3c318b6aee0deb0bda1d29803c87f578ba9a14 | b1988473a0a04c2af304953bbf54f8cd30cde951cfcb51f3ba1e17404a112414 |

Both final shared CLI check invocations completed successfully from the clean frozen source. Captures: coordination/slurp-program-matched-control-registered-preflight-v1.json SHA-256 6013a17a781572a32286164dccb78604591dd207ea87278bc1779b90d29c3356; speech counterpart SHA-256 fbc32b40431810007c212c3c42b7ee4e64c6b23cb46d49107c36a2b7cd6b1299. Sessions 24542 and 16466 finished with exit zero. They opened no attempt, model, tokenizer or scorer contact. The rough preflight estimate retains its legacy 32,768-token model limit; it is explicitly not capacity evidence for the actual 16,384-token serving slots. Actual per-phase endpoint fits are still required, using each arm's own freshly generated predecessor at the slots barrier.

The scientific-eligibility decision SHA-256 is 4fb2836b4e53caedbb7bd3b2100222bb928ea08cadce4ca5fbe67c0de97df1be. Both configurations pass shared declared_readiness. A separate local comparison refuses the current E21 service on sixteen full-identity fields despite both profiles having four slots; receipt coordination/slurp-program-matched-dispatch-hold-v1.json SHA-256 48e524f39682fbe13aeaaada5d3f7a8deba8e079690348f40714e08b62821588. Scientific/config readiness does not grant a service or lease and does not waive the owner-required E21 seal order.

## Exact next actions

The prepared, non-executed common-entry command handoff is coordination/slurp-program-matched-frozen-handoff-v1.json, SHA-256 b5b581d60e8ab1b26a6271565f428e456821b11b3fa3ed63aac4ec4a105ae9c8. It specifies the frozen source/environment and exact argv for the root serving wrapper, 10-second monitor, each lease and each attach-only worker. It contains no private execution implementation. No new service or lease token exists yet.

1. Keep observing the current E21 worker until its complete seal; preserve every existing source and ownership handle.
2. Verify the E21 seal and lineage, close external costs, release its lease, and stop the old resident service through the shared stop entry. Release the fixed E21 paired read/scoring under its already prepared source.
3. Root starts serving-slurp-live-program-matched-np4-v1 from the frozen source: no-mmproj, c65536/np4/16384 per slot, inherited build/weights/cache and max256. Bind its own 10-second monitor before dispatch.
4. Root leases and runs control, verifies its seal, releases only that lease, then leases and runs speech against the same process. Each worker's common live-phase barrier performs its registered actual fits before generating. Do not create standalone synthetic-predecessor fits.
5. Run complete E21 CPU scoring while SLURP generates, subject to the shared CPU budget and one complete scorer. Do not use automatic raw-parent scoring for SLURP: after both parents seal, build each registered joined delivery, run the two complete official scores sequentially with explicit context, then execute the unchanged paired analysis and close attempts/costs.
6. Preserve all old decisions and evaluate the new results honestly. The original G6 failed guard is unchanged; S4N still holds G3/G4; LOOP remains rejected against its incumbent floor; no E22/summary/training/paid-API work is admitted.

Engineering-base and diff checks passed; no new runtime framework or scientific implementation was introduced. No additional owner decision is currently needed. Do not modify the frozen SLURP source while awaiting the service boundary.
