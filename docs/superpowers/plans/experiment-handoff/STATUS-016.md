# Status 016: decoder-only G2 campaign dispatched

Date: 2026-09-10 UTC. Supersede STATUS-015 as a coordination snapshot; preserve all historical snapshots.

## Frozen runtime and live ownership

The recovered G1 trio remains ADMITTED_COMPONENT and must not be restarted or replayed. G2 runs from /home/chao/saea-worktrees/g2-kus4n-runtime at c45941547f2a47aac70bf54c1167c066ae2a4d9a. Keep this source frozen until the full N/twin generation and their scoring complete. Canonical-only documentation updates do not change its source.

Root owns resident session slurp-g2-kus4n-aligned-np8-20260910-root, server PID 3092. The actual session receipt pins --no-mmproj, exactly one decoder GGUF, prepared speech feature root, total context 65,536, eight slots, batch 2,048 and microbatch 512. No mmproj parameters are loaded into GPU memory or this inference process. The ten-second monitor PID is 3237. Keep the fit-batch wrapper alive while this session is needed; unified execution session 45471 hosts that wrapper, process 377 (wrapper 313). Never terminate it merely because fitting finished.

The full campaign was dispatched through the shared CLI, N then twin, process 10777, unified execution session 45127. Read its metadata under analysis/SAEA-SLURP-KU-S4N-G2-CAMPAIGN-V3 and launch.json. Do not infer generation completion from process launch. Confirm progress from serving counters and sealed manifests. A model/service failure pauses dispatch; root decides recovery with all prior contacts preserved.

## Completed G2 gates

The aligned V3 baselines preserve model-facing behavior and use one official projected-v2 primary score plus the separate raw-label normalized view. The frozen null margins, metric order, speaker-cluster primary, 10,000 replicates and seed remain unchanged. Corrected the accidental projected-v3 null-key substitution before any model contact and retained earlier CPU artifacts as superseded. Accepted preparation lives under prepared/SAEA-SLURP-KU-S4N-G2-PREPARE-V3-ALIGNED. Both full arms have 1,000 ordered selections identical to V2; both smoke subsets have four original registered IDs. Warm producer and runtime bootstrap recomputation counts are zero. Root relevant tests: 40 passed; independent configuration review, engineering-base and harness-admission checks passed.

The public fit_batch module originally lacked its __main__ guard and exited without executing. No service, journal or actual contact occurred in that first launch. Shared entry repair 33a321ca is covered by a failing-before/passing-after subprocess entry test and eight passing fit-batch tests. Do not repeat the no-op launch or its output paths. The actual fit batch is recorded under analysis/SAEA-SLURP-KU-S4N-G2-FIT-V3-ENTRY.

All actual request batches materialized before service startup. Full N/twin fits each cover 1,000 requests and 3,001 registered endpoints. Minimum margins are 5,491 and 5,478 tokens in 8,192-token slots; maximum requirements including max64 reserve are 2,701 and 2,714. Both inherited four-row smoke fits cover 13 endpoints. Total fit contacts: 6,028; generation and encoding contacts: zero. Preserve these receipts, their original fit protocols and consumed exposure rows.

Both inherited real smokes completed four GPU generations each, exact original rosters, valid JSON delivery, expected request/response and ORG/SUPPLY/REVIEW counts, one aligned official score per complete manifest and FINALIZED attempts. Root read engineering metadata only; no smoke accuracy was used to tune settings. The smoke admission decision is coordination/SAEA-G2-V3-SMOKE-ADMISSION-V1.json. The G1 predecessor admission is coordination/SAEA-G2-V3-PREDECESSOR-ADMISSION-V1.json. Both full cells bind these decisions and their own prepared supply and fit receipts.

## Full comparison and next gate

N: SAEA-SLURP-KUS4N-CANDIDATES-DEV1000-V3, attempt-20260910T020504Z-938cd3. Twin: SAEA-SLURP-KUS4N-CANDIDATES-TWIN-DEV1000-V3, attempt-20260910T020504Z-a556a2. Each has exactly 1,000 target rows, cap 1,050 calls, 1.0 GPU hour and 3,000 speech seconds. Both use one resident service and max64 intent output. This does not change the separately approved KU-S3 max256 slot-output setting.

Both full arms must seal and complete their one official scoring job before any treatment result read. Fill only pending source hashes in configs/experiment/slurp-kus4n-g2-aligned-analysis-v1.json, then perform the one registered read under SAEA-SLURP-KU-S4N-G2-ALIGNED-READOUT-V1. Do not rescore historical null or comparator. Root must decide non-inferiority and efficacy separately. G3 encoding remains held until N non-inferiority passes; G4-G6 remain pending. Do not add a matched control without a named decision-relevant mismatch and its required authorization.

## Independent E21 work

The corrected exact-four synthetic integration proof is in isolated branch codex/e21-ojw-integration-proof, commit 75f536c7aad2a80644163f86889cf9df19f6ee96 atop a0465ecf and 44d8529b. Root reviewed the new integration and reran 11 passing tests covering real fitter/OJW/controller parity, provenance, verified construction subsets and preserved discovery loading. It is ACCEPTED_MODEL_FREE_INTEGRATION only; the earlier implementation chain still needs root integration review at a safe boundary. Do not merge it into active G2. No live E21 serving or efficacy claim is made.

The opt-in strict cache-hit guard is isolated in /home/chao/llama-worktrees/featcache-require-hit. Root caught and required correction of a legacy VALIDATE regression; the corrected source preserves default behavior, makes strict shape/length checks opt-in and skips pre-existing encoded batches in strict mode. The lower-cost helper is compiling an isolated binary with at most four workers and no model load. It must not modify /home/chao/llama.cpp-featcache or the G2 binary. Source-level tests and compilation do not establish live hit/miss or parity qualification. E21 GPU-mmproj V1 remains held; V2 serving model fields remain unqualified. Prefer precomputed fresh exact-window cache with CPU projector and a qualified miss-refusal boundary, or the verified per-window packet alternative. Separate offline encoder placement clarification remains pending.

All research implementation, preparation, tests, inference and scoring use WSL Ubuntu-24.04. Root owns scientific decisions and service management; helpers may follow metadata and prepare isolated changes. No paid experiment API or Stage-3 scope is admitted.

## Confirmed full-arm GPU work and efficiency limit

Full generation is now observed, not merely dispatched. At 2026-09-10T02:53:54 UTC the monitor recorded 24 total generation requests (including the eight engineering smoke requests), eight busy slots, 98% instantaneous GPU utilization and 21,264 MiB allocated. The session identity remains decoder-only with no mmproj. Do not report the instantaneous reading as a campaign mean. During earlier full-flight preflight, shared request materialization and verification held the GPU idle for several minutes. Preserve that measured gap as setup/validation overhead; optimize durable prepared-request reuse at a later runtime boundary rather than changing this active pair or adding unregistered generation.
