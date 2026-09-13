# STATUS-076: Live system, prepared analysis inputs and verified reuse boundaries

Snapshot time: 2026-09-13T19:22:50.911057+00:00. Supersede STATUS-075's current execution and
preparation fields. Preserve its scientific sequence, closed results and holds.
Owner direction remains OWNER-SYSTEM-VERSIONS-025.

## Current execution

The native system is OPENED with 4662 model-role contacts at this
snapshot. Server PID756 and campaign PID890 are live. These contacts are not
completed sample counts. Revalidate the processes rather than relying on this
snapshot. Managed exec handles: service45101, campaign21002, monitor86723.

Keep the active WSL worktree
/home/chao/saea-worktrees/slurp-native-slot-values-dev1000-v1 frozen at
7ec4cf340206d52a2cf44f65cdda278352c43363. Its direct and system configurations
share prepared speech, decoder-only/no-mmproj serving, context98304,
four24576-token slots and max-output256. Service identity remains
serving-slurp-direct-vs-native-np4-ctx24k-v1.

Direct completed1000 contacts, finalized and received its first official score.
System generation continues. Current task quality and trajectories remain
unread. No new experiment is admitted, and no positive native-system result or
completed training-free RL cycle is established.

## Integrated preparation

The reviewed main implementation base is
ce1820752fab692de9f3ac8f87cf63abd1920906. It includes:

- Native source projection and post-seal episode diagnostics, integrated in
  0d549ffe, with80 focused diagnostic/score-receipt checks and the
  engineering-base check passing.
- Native TRAIN response identity and revisit handling through reward links,
  integrated in d1c0c851. Synthetic finalized TRAIN sources pass through grouped
  feedback and legal proposal contexts. The137 focused checks pass. A real
  proposer/update, disjoint selection and memory admission cycle remains absent.
- Audio2Tool source reuse audit, integrated in ce182075. The actual closed
  union4000 adapter uses the frozen media roster and FIRST-user-turn Tier7
  binding, not the generic loader's final turn. All500 Tier7 paths were
  independently checked. Complete dialogue can use existing materialization
  and derived-roster interfaces; ordered tool scoring already exists in v2.
  No new runtime framework or scorer is justified by that audit.

Read the linked evidence:
[Native diagnostics](../../../readiness/2026-09-13-native-system-candidate-diagnostics.md),
[TRAIN feedback](../../../readiness/2026-09-13-native-train-feedback-bridge-result-v1.md),
[Audio2Tool reuse](../../../readiness/2026-09-13-a2t-native-role-reuse-audit-v1.md).

## Prepared analysis inputs

DATA means /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data.
The analysis directory is
analysis/SAEA-SLURP-DIRECT-VS-NATIVE-SYSTEM-PAIRED-ANALYSIS-V1.

The direct saved-score receipt remains verified at
saved-score-receipts/direct/complete-score-receipt.json, SHA256
e6bc6eb14ea16a38d75b089d452d7e6915c9282f5ca36e961adb8f1802427b8c.
Do not run its official scorer again.

Prepared inputs are in prepared-inputs-v1:
- paired-config-pending.json; SHA256
  f7ce5b5e9a8748e9edf9385838b64d807623306cdb8508ea3780468a599daf01.
- native-diagnostics-config-pending.json; SHA256
  11ae8adec7665efd4dfb7b519ce37a12ff00157d20c0f3a0b72b3dd483209509.
- preparation-receipt.json; SHA256
  7a6da4e1d147be7b3fe75b49c93f8dc0580276048c464cacdf62cdaa80263b1d.

These resolve static paths and the already verified direct pins, preserving the
frozen roster, metrics, bootstrap settings and interpretation. System manifest,
score and phase-artifact hashes remain pending. Write bound successors after
completion; do not overwrite the preparation files or run analysis now.

## GPU power observation

A read-only audit observed an RTX5090 Laptop GPU, driver592.01, an active
software power cap, current/requested limit100W, default95W and reported
maximum175W. Sampled SM frequency was232MHz. The host reported AC online,
battery100percent, battery saver off and the high-performance power scheme.
No instantaneous thermal cap was active; cumulative counters do not establish
a flight-specific thermal history.

The audit receipt is DATA coordination/slurp-direct-vs-native-system-dev1000-v1/
gpu-power-observation-20260913t190714-v1/observation.json, SHA256
797ebd1120372f7c51523891501e1deaba4e65114a77bc13488d1cb3206d7c8c.
It pins the fresh raw performance/clock/power report. GPU utilization alone is
not a claim of unrestricted throughput.

An optional owner clarification about physical power and OEM performance mode
is pending. It does not block generation. No power limit, clock, driver,
serving geometry or active runtime setting was changed by this audit.

## Next action

Let the same campaign finalize and perform its one complete system score.
Use core.scoring_receipt to package the attached first score into a fresh
saved-score-receipts/system directory without scoring again. Bind both
complete-arm receipts and manifests, the system phase artifact and the frozen
method. Record the root read release before task-quality or trajectory reads.

Run the shared score comparison and system-only candidate/episode diagnostics.
Keep NEW500 primary and every row in the comparison. Missing FlightReceipts
means the original candidate-supply audit is unavailable, not reconstructible
as a producer-authored receipt. Distinguish rank-one-to-final repairs from
direct-to-system repairs.

Choose the next system capability from those outcomes under the inherited
replication or named-component root-cause rule. Optional Reviewer-selected
Whisper is still held pending scientific selection and its own fit/generation/
ASR plans. Audio2Tool native-role execution and later E21/E22 transfer retain
task-specific input, output and metric requirements. No scientific owner
decision is currently blocking this pair. The full research goal remains active.
