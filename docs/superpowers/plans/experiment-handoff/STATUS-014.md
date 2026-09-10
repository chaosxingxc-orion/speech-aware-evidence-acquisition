# Status 014: recovered GPU generation and G2 preparation

Snapshot UTC: 2026-09-10T00:34:29.467366+00:00. Process and progress snapshots are evidence of this instant, not a persistent readiness guarantee. Root verified the single model server, the fit coordinator retaining its foreground lifetime, the campaign coordinator and the 10-second monitor are alive. No second server or replay was launched. The owner-approved recovery is now performing GPU generation, after the CPU-only repair, testing, artifact preparation and request materialization stages.

## Recovered G1

The resident session is slurp-g1-max256-recovery-np4-20260909-root: decoder-only, total context 65536, four slots of 16384. All actual experiment requests use maximum output 256; the historical model fragment name is not the effective per-request output limit. Server PID 1096, monitor PID 1136, fit coordinator PID 364 and campaign PID 1568 were verified through /proc. The frozen generation checkout remains /home/chao/saea-worktrees/g1-max256-recovery-runtime at 05b0f05ea87b52314845c3466d8f5a547551356f. Do not update it during the campaign.

All three fresh full-roster capacity fits passed in this session. Each covered 1000 requests and 3001 registered tokenizer endpoints, with zero generation or encoding during fitting. Minimum remaining margins were 6122, 5927 and 5917 tokens for control, speech and twin. Admission and the three generation plans were committed before generation. OWNER-KUS3-RECOVERY-006 authorizes this one additional 1000-row matched control and the remaining a/twin; retain the old completed control as descriptive replication evidence without scoring it again.

| Arm | Attempt state | Recorded generation calls | Whole official score present |
| --- | --- | ---: | --- |
| control | FINALIZED | 1000 | true |
| speech | OPENED | 543 | false |
| twin | NOT_OPENED | 0 | false |

The attempted-call counters above come from the AttemptStore. Monitor requests_total is a sampled lower bound and must not replace them. Audio seconds are input exposure, not generation wall time. Comparative outcomes remain unread. Wait until all three new manifests seal and each completes its single whole official score, then bind the pending hashes in the registered recovery analysis config and run the shared paired analysis. Keep primary and sensitivity estimators, roster partitions and the descriptive new-minus-old control contrast fixed.

Live coordination files under DATA/coordination are ku-s3-max256-recovery-fit-batch-v1.launch.json, ku-s3-max256-recovery-fit-batch-v1.json, ku-s3-max256-recovery-campaign-v1.launch.json and ku-s3-max256-recovery-admission-v1.json. Inspect selected attempt metadata and monitor samples without exposing unclosed comparison outcomes. The fit coordinator keeps the resident service alive; a tool polling yield is not evidence that it exited. On a genuine service failure, preserve contact records, pause dispatch and reconcile before any restart. Do not automatically replay.

## G2 and later

The N and twin V2 candidate artifacts are DATA_READY. Each preserves all 1000 V1 ordered selections and the shared renderer's complete supplied bytes. The audit proves zero warm producer calls and zero runtime bootstrap recomputation. Preparation, parity and this review made no model, tokenizer, encoder, scorer or network contact. The source-bound pins and receipt are in docs/checks/speech-aware-evidence-acquisition/2026-09-10-ku-s4n-g2-preparation-v2/. G2 capacity and generation remain held pending G1 closure, their separate registrations and the matching np8 service. The inactive G2 worktree can be updated only before its next registered contact; it must not alter the active G1 runtime.

Root reviewed the historical N comparator: its geometry matches G2, but its fixed-policy prompt omits the phase-control turn shared by N and twin. Preserve the preregistered whole-configuration interpretation against history and conditional candidate-selection interpretation against twin. See docs/readiness/2026-09-10-ku-s4n-g2-comparator-interpretation.md. No extra experiment or altered threshold is authorized by this review. The current shared-executor direct baseline remains required for the full live system.

The handoff target below one minute is not yet met: full CPU request revalidation delays dispatch despite persisted supply reuse. Preserve the current comparison's frozen implementation, record the actual idle interval and improve this only at a future run boundary with source-binding and byte-parity validation. Do not add model contacts merely to keep the GPU busy.

E21 full constrained replay remains complete for 1593 windows and 44 calls with zero new generation. Current live executor proof, actual DR/LOOP capacity admission, two DR generations and four derived deliveries, LOOP/twin, and complete live system evaluation remain pending. G3 exemplar encoding remains gated on the N non-inferiority decision. The overall Stage-2 goal is active and incomplete. No owner question is pending.
