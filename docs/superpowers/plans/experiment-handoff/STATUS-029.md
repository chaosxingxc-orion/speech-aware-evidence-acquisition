# Status 029: owner-approved matching pair prepared while E21 repair runs

Date: 2026-09-11 UTC. Scope remains Stage-2, WSL Ubuntu-24.04, the frozen core and dataset-native tasks. The active research goal is not complete.

## Confirmed owner decision

OWNER-SLURP-MATCHED-COMPARISON-011 approves exactly one additional program-matched SLURP pair after the current E21 repair seals. Generate independent first and slots phases in each arm. Retain DEV1000, NEW500 primary, the original schema/examples, five-fact speech retrieval, registered delivery and every inherited analysis guard. The pair has 4,000 planned generation contacts, 4,200 including bounded retries, 12,004 actual-fit endpoints and a 1.0 utilization-integrated GPU-hour family cap (0.5 per arm, fit and generation costs reported together). Speech exposure is capped at 6,000 seconds per arm. If its guards fail again, stop; no further search for a passing repeat is authorized.

The historical G6 slot-positive/scenario-guard-failed decision is unchanged. The program identifier mismatch is a named nuisance, not a demonstrated cause of that failure.

## E21 generation remains active

At 2026-09-11T03:44:38Z, worker 21509, root lease 21472, server 1354, coordinator 637 and monitor 1389 were alive. GPU utilization was 65%, memory 19,776 MiB and power 92.91 W. Twelve complete call rows had been written out of the target 44 calls / 1,593 windows; no manifest existed. This is a progress snapshot, not a quality result.

Preserve frozen generation source /home/chao/saea-worktrees/e21-offline-repair-generation at 64440737a401b80805cfdd4f09d5a04748a3aad7. Worker session 99977 and lease session 22105 remain active; release the lease only after full seal verification or explicit abort reconciliation. Service serving-e21-offline-direct-repair-np4-v1 remains on its existing np4 no-mmproj geometry. Do not restart or alter it.

The direct parent is sealed, all 1,593 current-run predecessors are bound, and the repair actual fit passed all 1,593 requests / 4,780 endpoints. STATUS-028 retains the exact hashes, costs and lineage. Quality/reference reading and complete scoring still await repair seal or a formally closed comparison hold.

The scoring execution-source handoff coordination/e21-offline-score-comparison-execution-source-v1.json, SHA-256 265476f1431d5c6c4beb7e639eabcccff589a3cca91ebe9022fbac3d9601fa9a, explicitly binds the frozen 64440737 source. Root independently verified all eleven implementation files and both jobs. Run whole-call primary analysis under the frozen plan, one complete scorer at a time, with per-sample retention; do not use the superseded source path from preparation v2.

## SLURP preparation completed in this turn

- Added held control/speech baseline and experiment fragments named slurp-live-program-matched-control-v1 and slurp-live-program-matched-speech-v1. Both use phase-direct-then-slots-supplied-v1. Null supply is explicitly empty.
- Root removed copied old failure-recovery metadata and retained the inherited scientific feature identity strings. The only mechanism change against the historical null is the matched program identity; treatment retrieval/schema/decoding are preserved.
- Frozen analysis plan: docs/readiness/2026-09-11-slurp-program-matched-v1/analysis-plan.json, SHA-256 471e0d7ab6f900b5f2f31a6a7c74dd4d0d7bda22471f1db82da53141e20c5893. Root compared the old fields and confirmed all metrics, populations, seeds, estimators and guards are unchanged.
- Complete-score and paired-analysis templates are held. The scoring recipe uses explicit ScoringContext for source, DATA and umbrella lock, avoiding implicit CLI context. Its two jobs remain sequential.
- Model-free exposure row SAEA-SLURP-MF-PROGRAM-MATCHED-PREPARE-WIRE-V1 is committed.
- Existing recall bytes failed the strict new configuration binding. A first shared preparation invocation refused before production because the old optional pin was still configured. Root cleared that pin, produced a new artifact through shared prepare-phase-recall using four CPU workers, verified the complete output exactly equals the old output, then pinned the new artifact. No model, tokenizer, embedding, encoding or scoring contact occurred.
- New recall: prepared/SAEA-SLURP-LIVE-PROGRAM-MATCHED-SPEECH-PREPARE-V1/recall.json, SHA-256 7295b85d86f0392afbdec7a06a798d7c94a13ef0d11f73d64f812ca8701ac820. All 1,000 rows match the original output exactly.
- Equivalence receipt: coordination/slurp-program-matched-recall-successor-equivalence-v1.json, SHA-256 3fa4f91dcb9fd363ad3ff9f01e3af2515c751bc5ec226f00608d5002d1b81c2d. Original artifact remains unchanged.
- Full control wire check passed through shared FlightRuntime and OpenJiuwen: 1,000 direct and 1,000 slots synthetic requests, four slots, max_tokens=256 everywhere, zero supplied blocks and zero model/scorer contacts. Receipt coordination/slurp-program-matched-control-full-wire-v1.json, SHA-256 8f8a62f09f9a91bb38e1063ba1499e1314a0b55e5b68547604c0adf216299ce5; composed config a90f759c9770ba23d8ff952a2b5de83f926802a919abb8bc7afe34262f866f7d.
- Engineering-base and diff checks pass. No new execution framework or model-facing implementation was added.

## Pending work and exact continuation

1. Finish the speech arm full model-free wire check already running in exec session 80581, using integration source launched at 359069f5. Output is coordination/slurp-program-matched-speech-full-wire-v1.json and its log has the same stem. The null check session 16680 and recall preparation session 84769 completed successfully; do not rerun them.
2. Compare the two receipts by sample and phase: all first-stage raw payloads must match. With the common synthetic predecessor, second-stage model-visible material may differ only by declared supply. Receipts retain raw and common-rendered history fingerprints; if other fields differ, name and resolve them before admission. Neither synthetic request count is a neural-contact count, and this proof does not replace actual capacity fitting.
3. The speech wire receipt also captures the required full SLURP session identity through the shared runtime. Review it, the prepared binding and max256 request values. Keep all real fit/generation gates held until the remaining required evidence exists.
4. After E21 repair seal, verify all windows/calls, lineage and budget; close its immutable external cost receipt; release only its root lease. Freeze its scoring source and release the registered paired read. Score both full manifests once, then execute the frozen whole-call primary comparison and close both attempts.
5. Finalize and commit the two SLURP generation and two live-fit ExecutionPlans/exposure rows against final composed configs. Preserve the registered budgets. Readiness changes and receipt pins must not change the scientific artifact input identity. Freeze one WSL source for both arms before service switch.
6. Root switches to serving-slurp-live-program-matched-np4-v1: decoder-only, no-mmproj, total context 65,536, four slots, 16,384 per slot, max256. Use one process for null then treatment. Actual fits occur at each live phase barrier through the shared runtime; do not fit invented final predecessors or create a separate runner.
7. E21 complete CPU scoring may overlap this approved SLURP generation, within aggregate CPU limits and one full scorer. After both SLURP parents seal, derive the two registered deliveries, score each complete roster once, run the unchanged paired analysis, and retain the result even if a guard fails.

The handoff check is coordination-only and never grants launch permission. Do not interpret launch_allowed=false as a new request for owner approval: OWNER011 already authorizes this exact pair, subject to its existing executable prerequisites. No further owner decision is currently needed.
