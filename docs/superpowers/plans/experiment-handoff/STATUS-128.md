# STATUS-128: Audio2Tool finalized; GPU hold active; paired analysis running

Date: 2026-09-15. The owner GPU hold is now active after the current task completed.

## Completed execution and integration

The original Audio2Tool full4000 sole recovery exited normally at 09:36:23.183569 UTC with exit code0. The attempt is FINALIZED. No successor, restart, fit or encoding was dispatched. Preserve the original resident service and its memory until an explicit owner instruction.

| Arm | Complete rows | Metered generation contacts | First complete official scoring |
| --- | ---: | ---: | --- |
| SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1 | 4,000 | 4,000 | Succeeded; reused |
| SAEA-A2T-NATIVE-ROLE-DUAL-STORE-UNION4000-RECOVERY-V1 | 4,000 | 19,475 | Succeeded; retained |

The full system trace is1,259,187,862 bytes. It was still being written at09:25:53 and09:30:01 UTC and its final mtime is09:34:25.603550 UTC. These observations identify a material artifact-persistence tail; they are not a precise GPU stop timestamp.

The reviewed shared execution-unit, feature-window, bounded speech-span, governed-context, held E21 configuration and saved-score window-analysis changes were integrated into the canonical master branch at d8f4bfa24e852d22132564b76f2f0dd8523c0dda after the flight stopped. The merged runtime/config/test tree exactly matches the reviewed source. Existing509-test and263-test receipts apply; they overlap. Preserve the two pre-existing untracked paths, integration_native_finite.py and wsl$/.

## Registered analysis and current results

Complete source bindings are recorded under SPEECHRL_DATA_DIR/analysis/SAEA-A2T-NATIVE-ROLE-BASE-ANALYSIS-V1/. The paired read release was registered at commit d1ddc9d66734fe36d974d440990e4e98a893ffb0 before quality inspection. Both bundles were verified by the shared reader. Preserve all first scores; no scorer was rerun.

The initial paired analysis refused integer query_idx values before producing statistics. Commit8ca04037a10de77f9845a9c3c9c9e0c4740f6aa8 registers a representation-only correction: decimal text IDs for the same2097 query clusters and unchanged4000 rows. The v2 config is SHA-256 2fc0f2f562fa06abb2ef6c1ba0f5ae5899df47e2e922a657f3fa47d6564d6c77; metadata is f0cc01a84506dbd6bd4be9b53388e251c4ffa108711acb46c281a70fb4cd8251. The10,000-replicate paired analysis started at09:48:16.410727 UTC (PID91662). Its current authoritative state is its process handle and paired-score-analysis-exit-v2.json, not this snapshot.

Root has read both first complete aggregate tables:

| Official metric | Direct | System | System minus direct |
| --- | ---: | ---: | ---: |
| Exact match | 18.500% | 22.550% | +4.050 percentage points |
| Tool accuracy | 62.025% | 58.425% | -3.600 percentage points |
| Macro parameter F1 | 30.149% | 34.902% | +4.753 percentage points |
| Micro parameter F1 | 24.535% | 30.278% | +5.743 percentage points |

These are complete-roster point estimates, not a stable-benefit claim. Formal paired intervals and all strata remain pending the existing CPU job. The frozen promising-system rule includes a nonnegative official tool-accuracy point difference; that requirement fails on the observed complete scores even though full-task exact match rises. Preserve this distinction in the eventual verdict and in recommendations for future system versions.

## Native trajectory custody and behavior

The first generic audit exposed a postseal reader mismatch: it compared the raw JSON Planner response to a decoded action token. The runtime receipt and source were intact. Reader repair0bcd5f7faa36b22e4e9ec7fcb894cc76545b71f3 reuses the existing strict raw-plan/control/hash/route checks.44 related tests and engineering checks pass. The corrected reader then verified every one of the4000 native episodes against the frozen834d4 runtime source.

The complete audit artifact is native-episode-audit-v2.json, SHA-256 9a970faf5d6fae9ebe3f55beb270508bd08e0140c667800df5c21231782eefdb. Its verified behavior:

- Perception4000, Solver5156, Reviewer5170, Planner5149 contacts; total19475.
- Fifteen successful analytical task-contract tool calls; no observation-tool calls.
- Planner routes:3620 ACCEPT and1529 REVISE. These are route counts, not distinct sample counts.
-372 episodes delivered the latest Solver at the revision limit.
- Eight finite length stops: one Perception, six Reviewer and one Solver. Six retained a completed Solver; two produced the registered abstention. These explain the workflow error events without making the full run incomplete.
- Supplied-value lexical overlap is available for all4000 rows and remains descriptive. Candidate-to-value coverage requires the separately bound actual selection-receipt join.

## Next authorized work

1. Complete the existing paired CPU analysis, inspect all tier/domain results, preserve the frozen primary decision and write root attribution.
2. Bind actual Audio2Tool Perception candidates and parameter-value selections to the verified native source. Use the Audio2Tool parser, not the SLURP stage-projection parser. Keep official-primary coverage separate from complete ordered-action coverage.
3. Integrate the verified postseal reader repair and complete the canonical status/results ledger update. Preserve frozen flight worktrees and historical failed analysis artifacts.
4. Retain ready SLURP and E21 configurations. Do not launch GPU generation, fit, encoding, service restart/recovery or another comparison without explicit owner resume.
5. Build algorithmic training-free RL only after a usable agent system and optimizable action space are established. Manual root engineering is not algorithmic RL innovation.

## Terminal and read receipts

Under SPEECHRL_DATA_DIR/coordination/a2t-native-role-control-recovery-v1/:

- full-campaign-exit-v1.json: normal terminal.
- root-terminal-gpu-hold-v1.json, SHA-256 6dfcd6dc7010914e7b88d1619b17b7b5ba90ddf7a4614c8e50f22d6ecdf6daae.
- observer-full-recovery-v9.json: terminal metadata only; no observer quality read.

Under the full4000 analysis directory, retain all metadata/config versions, both failed analysis/audit records, complete-source-bindings-v1.json, root-paired-aggregate-read-intent-v1.json and native-episode-audit-intent-v2.json. The latter binds the repaired reader before its complete-source verification.
