# STATUS-067: A2T decided; first Whisper preparation aborted

Snapshot UTC: 2026-09-12T19:09:57.647987+00:00. The broad system objective remains active.

## Current execution

The three A2T recovery arms are FINALIZED and first-scored: 4000 direct, 8000 stage-control and 8000 knowledge generation contacts on the same 4000-row roster. Frozen analysis finished at 18:51:58 UTC. Root issued the formal decision at 18:54:16 UTC; promising_system is NOT_ADMITTED and knowledge_contribution is NOT_ESTABLISHED. Read the full metric and tier/domain tables in docs/readiness/2026-09-12-a2t-native-system-final-result-v1.md. All 234 independent reconciliation points match. No extra A2T generation or rescoring is planned.

Root stopped the Qwen service through its shared owner entry at 18:54:42 UTC for the registered Whisper preparation window. No forced stop was used. Whisper reached its first real GPU batch and aborted at 18:56:07 UTC. Eight source contacts and 24.6738125 speech seconds remain charged. No observation file or complete catalog sealed. Do not treat download/load checks as successful batch inference.

A fresh 19:03:27 UTC check found no Qwen, Whisper preparation, or official scoring process; GPU utilization and allocated memory were both zero. This is a failure-recovery wait, not GPU work in progress or an owner-imposed pause. The prior GPU-resume authorization remains in force.

## Whisper failure and bounded next repair

The retained stack reports 40 decoder-token rows against 8 audio-feature rows in batched beam search (batch 8, beam 5). The pinned implementation repeats token rows but not audio features, then later slices audio features by the beam-group stride. The narrow CPU proof against the actual upstream decoding path is complete: the original batch8/beam5 fails with the same 40-versus-8 error, while the one-line feature expansion returns eight ordered results with exact returned feature lineage and batch/serial token equality; beam1 is unchanged. This used tiny random weights and synthetic encoded features, not the checkpoint or task audio. All eight synthetic rows emitted the same tokens, so this is a structural regression proof, not broad acoustic or task validation. GPU memory, real transcript quality and long decoding remain untested. Root inspected the receipt at DATA coordination/whisper-batched-beam-defect-v1/diagnostic.json, SHA256 7dba1a640ca0be256940bb675ba9e9d82dc01e59375ce6b3458b0d7da3fc1c86. The independent authority audit is complete: the standing rule permits exactly one prospectively registered recovery of this original failed flight without a new owner preference. The prior identity-specific release does not admit the successor by itself; root must bind and admit the new source, protocol, ledger, run and attempt before contact. The unchanged recovery workload is 1000 sources and 2884.7936875 seconds; including the failed eight contacts, family exposure is 1008 contacts and 2909.4675 seconds.

Neither a deployed patch nor a new recovery attempt is complete at this snapshot. Preserve the aborted attempt, started markers, source inventory, decoding settings and charged contacts. A new source-bound recovery must be prospectively registered under the inherited one-recovery rule before any contact. Do not silently switch beam size, reduce the experiment roster, or replay the old attempt directory.

## SLURP pair readiness

The compact-frame baseline remains an exploratory working baseline with replicated NEW500 intent +4.200pp and raw official pooled micro F1 +2.991pp. This is whole-system evidence versus a one-phase direct arm; it is not isolated evidence for knowledge alone.

The next matched pair uses plan, solve and revise in both arms, full legal labels, five compact knowledge blocks and max_tokens 256. Only treatment receives the prepared full-utterance Whisper observation. Control recall and all 3000 fake-wire requests are verified. The official saved-score reader and prospective paired analysis are merged and frozen.

Treatment templates are committed on an isolated branch at 8fcb68808f34bff863faee0a46e21e5afab2a111. They now explicitly await a newly registered recovery catalog and preserve original failed preparation accounting. They are non-runnable templates; catalog binding, treatment recall, final admission and actual capacity checks are pending. They have not been merged at this snapshot.

Plan 3000 answering generations per arm with a 3150 per-arm ceiling and 9003 actual fit endpoints per arm. Restore a single root-owned decoder-only c65536/np4 service with prepared source speech features and no mmproj. Auxiliary Whisper contacts are separately recorded; a cache hit does not erase them.

## Parallel engineering and system direction

The shared TRAIN trajectory-to-first-official-score reward-link draft was committed in an isolated worktree at 1d88ef1c7adabc2c801593a68b73f6d9bb05f0bc. Root restored the two files missing from that checkout exactly from the commit and ran its tests in the actual WSL research environment. Both tests fail because the fixture uses an unsupported tool_action trace channel. The fixture also substitutes verify_bundle instead of proving the requested complete bundle integration. Root has not accepted or merged it and will personally repair/review this submission; it does not block GPU recovery. Proposal projection, disjoint selection, candidate admission, frozen policy evaluation and an actual training-free update cycle remain incomplete. Seven upstream methods were statically audited; no upstream reproduction or positive optimization result is claimed.

Existing local tool readiness remains differentiated: Whisper checkpoint/runtime present but real batch failed; Silero ONNX load verified; MMS alignment weights loaded on CPU; Sortformer weights present but load/forward untested; FFmpeg/ffprobe and CMUdict available; WhisperX source only; optional pyannote weights unavailable. No new tool is task-validated by acquisition.

Historical E21 DR, LOOP and fresh repair comparisons remain closed. The fresh repair reduces PERSON errors by 99 and total word errors by 165, while adding 5 insertions; preserve the old failed guard and apply OWNER022 only to future experiments. No new E22 system evaluation has begun. KU-S4N remains held after failed noninferiority; do not perform the held exemplar encoding.

## Next ordered actions and owner decisions

1. Close the narrow Whisper repair proof and authority check, pin the corrected tool implementation, register one eligible recovery, and resume its existing 1000-source GPU preparation.
2. Seal the complete observation catalog; bind treatment recall, final configurations and full actual capacity checks.
3. Run the two matched SLURP arms in one decoder process. Overlap permitted CPU work and one complete official scorer with the next scientifically eligible generation.
4. Apply the already frozen paired native micro-F1/intent analysis. Replicate a positive mechanism on the same roster or diagnose an unresolved/negative result to a named component before another mechanism.
5. Test problem-targeted evidence against matched random selection only after evidence availability is understood. Severity or one minus judge score is not problem confidence.
6. Close TRAIN reward lineage, legal proposals, disjoint validation and version freezing in the shared framework. Optimize system actions and task-specific discriminative values; admit reusable corrections as memory only after validation. Transfer the same interfaces to Audio2Tool and E21, then an independently admitted E22 scope.

No new quality/latency, SLURP-first, GPU-resume, local-tool or Reviewer-trigger preference is required: the owner already decided those. If the frozen SLURP comparison produces opposing native task effects, present the actual tradeoff before changing retention priorities. Optional pyannote access is not on the critical path. Recovery authority is now verified under the existing one-recovery rule. The changed source and successor admission are not yet registered or launched.

## Operational provenance

Seven frozen worktrees temporarily lacked Git administrative metadata. Root verified every tracked file against its pinned commit with zero mismatch, then restored only missing administrative pointers/indexes and locked the worktrees. Source files and branch identities were unchanged; the cause remains unknown. Receipt: DATA coordination/wsl-worktree-metadata-restoration-complete-v1.json, SHA256 46a6d479cb086d0027d3e0d6a9688ecef07161e19600b3c19a983850ddb17b5f.

Keep load, useful generation, data wait, scientific decision wait and scoring tail separate. Prior high GPU utilization did not establish maximum hardware throughput; a read-only audit found a 100 W reported software power limit and low reported SM clocks under load. No platform power setting was changed.

## Status-document validation

The handoff coordination check passes with no errors and correctly grants no launch authority. The full results-ledger check stops in the unchanged existing exposure ledger: the SAEA-SLURP-SPEECH-OBSERVATION-ANALYSIS-DESIGN-V1 entry has five cells beneath a fifteen-column header. This is an inherited metadata defect, not a new experiment result. Record it as unresolved and require a valid successor ledger for the next recovery registration; do not modify frozen historical ledger snapshots. The new result report and current continuation entry retain source hashes and full strata.
