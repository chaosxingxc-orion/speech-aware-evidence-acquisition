# Operations and recovery

This document describes the run actually in flight, not a generic launch recipe.
All paths below are WSL paths. Resolve current liveness again after any quota interruption
or reboot. The timestamped snapshot is evidence only for its capture time.

## Roots and fixed execution environment

| Name | Path |
| --- | --- |
| Canonical study | /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition |
| Umbrella | /mnt/d/chao_workspace/exploring-l4-intelligence |
| DATA | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data |
| Research Python | /home/chao/.venvs/speechrl/bin/python |
| Current coordination | DATA/coordination/slurp-typed-context-vs-direct-v1 |
| Dataset identity authority | Umbrella/docs/datasets.lock.json |
| SLURP feature cache | /home/chao/feat-cache/slurp-q4km-packets-04ccc72a |

Use Ubuntu-24.04 explicitly. Set PYTHONDONTWRITEBYTECODE=1 and literal PYTHONPATH to the chosen
frozen checkout's src directory. Do not reinstall editable packages or infer active code
from the shell's current directory. Preserve the separate pinned official SLURP scorer;
the shared campaign already owns the pending first full score.

Canonical branch is master. Its pre-handoff HEAD is
442d77e89f3d6d112324b3277e73fa6070d12f3c. This handoff adds documentation after that commit.
Preserve unrelated untracked _tmp_slurp_gap_extract.py, integration_native_finite.py and wsl$/.
Do not stage them. Nothing in this handoff authorizes a push.

## Source and attempt map

| Purpose | Frozen checkout under /home/chao/saea-worktrees/ | Commit | State at handoff |
| --- | --- | --- | --- |
| Current full system recovery | slurp-typed-context-full-recovery-v1 | 9bf27b28708bb93607138e7bcd1eacb66eab3f08 | RUNNING |
| Successful current-configuration proof4 | slurp-typed-context-system-recovery-v1 | 8ad1a306dd2a50f67916c93246d083c1218bbbc5 | 4 complete, finalized, no task score |
| Shared rejection repair | slurp-native-tool-rejection-recovery-v1 | d7ff1c1ad9ee9bb6dbf613cf7ef8dbc4fde4cb87 | Integrated and verified |
| Completed direct and aborted original system | slurp-direct-source-recovery-v1 | f3189ce2667a45b1c0c9633e510747ae914118bd | Preserve both |
| Earlier zero-contact direct failure | slurp-typed-context-registration-v1 | bae1e743e66c0ee8189851bb1ec35ddc37ab2c49 | Historical, not current |

Current system identities:

- Run: SAEA-SLURP-NATIVE-TYPED-ROLE-CONTEXT-TRAIN-FOLD-A-RECOVERY-V1.
- Attempt: attempt-slurp-native-typed-role-context-train-fold-a-recovery-generation-v1.
- Attempt metadata: DATA/attempts/SAEA-SLURP-NATIVE-TYPED-ROLE-CONTEXT-TRAIN-FOLD-A-RECOVERY-V1/attempt-slurp-native-typed-role-context-train-fold-a-recovery-generation-v1.json.
- Baseline, experiment and campaign stem: slurp-native-typed-role-context-train-fold-a-recovery-v1.
- Config composition hash: 4bc94ebd766c466185aab5366f764eba1c992ab809acaab23f7ebc2f59754b3f.
- Execution protocol hash: f41f0b47664d166a91899aec173cb6bcb552d121a02e845d87ab97c76ca520d8.
- Split hash: 61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6.
- Complete ordered cohort: 1,080 TRAIN Fold A recordings.
- Caps: 11,880 generation contacts; 47,520 FIT endpoint contacts; 4,320 analytical
  tool invocations; 33,930 processed speech seconds; 12 FIT-inclusive GPU hours.
  These are caps, not required activity or a progress denominator.

Registration lives in
[the system recovery directory](../../readiness/2026-09-16-slurp-typed-context-system-recovery-v1/README.md).
Use its registered system-recovery protocol, generation plan and FIT plan, not an old proof draft.

The prepared supply artifact is
DATA/prepared/SAEA-SLURP-NATIVE-TYPED-ROLE-CONTEXT-TRAIN-FOLD-A-RECOVERY-V1/phase-supply-v1.json,
SHA-256 eb474db68caacf1ab072d3e62007a74755cfd8935b37ce0df1818368ffdccf29.
Its selected-value/order output hash ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f
matches the original preparation. Never relabel that artifact for a new run.

## Live service and observation

Service session: serving-slurp-native-candidate-five-train-a-np4-v1.
Original server PID 364846; monitor PID 364981. Total context 98,304, four slots,
max output 512, temperature 0, seed 20260913. Prepared SLURP speech packets, no GPU mmproj.
The service occupies approximately 22.4 GiB. Do not change power mode; the owner settled it.

Campaign PID 425664 has process start_ticks 12073328. Verify both start_ticks and the exact
frozen checkout/campaign-plan command line; PID existence alone is insufficient.
The original root tool session is 34947. A new task may not inherit that handle.

Under current coordination:

- root-campaign-system-recovery-launch-v1.json: root launch metadata.
- root-campaign-system-recovery-terminal-v1.json: expected terminal receipt.
- observer-system-recovery-v1.json: last completed observer window, which may be older than
  the live watcher. A timeout here means observer expiry only.
- root-campaign-system-recovery-v1.log: contains model material; do not tail while quality is held.

Existing telemetry is DATA/serving/<service-session>/monitor.jsonl, sampled every ten seconds.
A lightweight observer checks metadata at most once per minute and reports terminal state,
failure or 15 minutes without counter progress. Its PID/window is in LIVE-SNAPSHOT.json.
The currently assigned observer is /root/slurp_stage_attribution_sol; the Luna observer is idle.
Do not create a second watcher. Check the existing watcher before renewing an expired window.

A request count includes different endpoint activity and a model contact can belong to an
intermediate role. Neither supplies completed-row percentage or a reliable finish time.
Do not probe generation/tokenizer endpoints merely to obtain progress.

## Failure and terminal handling

1. If the exact process remains alive and counters advance, leave source/service/lease alone.
2. If a terminal receipt appears, inspect metadata first. A process exit alone is insufficient
   evidence that generation, score attachment and attempt finalization all completed.
3. If the root handle is unavailable, inspect the exact OS process and durable receipts.
   Do not restart on a missing handle or observer timeout.
4. If a reboot removed the process/service, reconcile the recorded attempt, partial exposure,
   lease and terminal evidence before doing anything else. Never erase the accounting or
   resume by splicing completed-looking prefixes.
5. A second failure of this system flight closes it. No automatic third attempt, renamed
   replacement, scorer on a partial manifest, or held-replica bypass is permitted.
6. Historical lease recovery preserved the guard inode. Never delete a live lock file or
   release another owner's credential. No new lease reconciliation is needed while this
   campaign is active.

The original system failed after 507 contacts because an invalid multi-tool batch was
rejected without all matching tool-result observations. It was not evidence of a reboot,
OOM or task-quality failure. The shared repair and proof are documented in the report.

## Direct comparator: never rerun its score

Run: SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1.
Attempt: attempt-slurp-direct-max512-train-fold-a-source-recovery-generation-v1.
All 1,080 rows and its first full score are complete; attempt FINALIZED. Quality is unread.

Artifacts are under DATA/runs/<run>/<attempt>/:

- <run>.generation-manifest.json:
  5219d078dae949fede1f8cd72832ffdbf26b9e2205fd7873e4e7bf631e56b534.
- <run>.scores.json:
  7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38.

Its generation source is f3189ce2, not the newer system/analysis source. Preserve this difference.
The system repair does not retroactively change direct provenance.

## Exact postseal analysis route

Prepared inputs and checks already exist. Do not rebuild the analysis framework.

- [Source binding instructions](../../readiness/2026-09-16-slurp-postseal-source-bindings-v1.md).
- [Frozen full-cohort estimands](../../readiness/2026-09-16-slurp-system-vs-direct-train-a-analysis-held-v1.json).
- DATA/coordination/slurp-typed-context-vs-direct-v1/postseal-preparation/ contains five held
  analysis templates with suffix system-recovery-v1.
- source-bindings-known-system-recovery-v1.json in that directory binds 42 verified files;
  SHA-256 d5d689b0ee5093a9da0d8de2b5fd71181c09b5b5103beb9e5d52bc0e2993287c.
- analysis-api-compatibility-v1.json:
  0b0974e7d0cee3249e24e06d51a0bebff3b28b9d6344c7dfd02fd4f7b1c74819.

Some held templates contain an old preparation checkout. Create fresh bound execution copies
using the supplemental known bindings; never overwrite or blindly execute an unresolved template.

Execute only after full system completion, first full score and source verification:

1. Verify both finalized complete sources, exact ordered 1,080 coverage, manifest hashes and
   first score attachments. Record root paired quality release before reading quality.
2. Bind fresh analysis copies. Use the frozen 9bf27b28 checkout for system source verification;
   keep the direct generation commit distinct.
3. Build both saved-score reward projections using rails.reward_link_io.build_reward_link_artifact.
4. Verify the native source with analysis.native_episode_source.verify_native_episode_source.
5. Explicitly invoke analysis.native_tool_exposure.analyze_verified_native_tool_exposure on
   that verified source. The source verifier does NOT call this rejection-aware audit.
   Preserve the rejected batch and exclude rejected calls from successful acquisitions.
6. Run existing native_train_stage_diagnostics, slurp_solver_stage_attribution,
   review_findings and score_compare_cli paths. Use governed exact Fold A reference bindings
   only in offline diagnostics. Export numeric/status/hash derivatives, not reference strings.
7. Report whole-cohort official pooled SLU micro F1, all 18 scenarios, equal-scenario values,
   intent/scenario/action, entity pairs, malformed/saturated/fallback cases and costs.
   Use 10,000 whole-speaker bootstrap draws, seed 20260915, max two workers;
   CI95 for primary, CI90 for diagnostics.
8. Keep direct candidate coverage undefined. Keep the primary unconditional on system gold
   inclusion. For slots, report the common-correct-intent cohort separately from own-correct
   denominators. Root interprets saves, harms and actual information acquired/consumed.
9. Write the root verdict, update the results ledger and coordination state, and choose the
   next branch in NEXT-STEPS-AND-DECISIONS.md.

Do not execute the official scorer a second time. If its first job fails, preserve that failure
and follow the existing scoring custody/recovery rules rather than claiming a completed score.
