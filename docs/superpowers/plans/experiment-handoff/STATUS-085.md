# Status 085: GPU recovery progressing; TRAIN output seams integrated

Snapshot: 2026-09-14T01:43:42.173393+00:00. This interval made progress. Keep the complete owner goal active:
a useful replicated system, its training-free optimization cycle and transfer
work are not yet complete. No owner decision blocks the current flight.

## Active immutable campaign

Read STATUS-084 for source hashes and the complete paired-analysis handoff.
The sole reboot recovery remains on frozen commit
6307a3ab30c93a6be35114deb5f701e6e444292f at
/home/chao/saea-worktrees/slurp-dual-store-reboot-recovery-runtime-v1.
Campaign PID3413/exec9571, service PID793/exec25977, monitor PID1142/exec18862;
session serving-slurp-dual-store-reboot-np4-v1.
Boot ea153fa0-9cd7-4e94-9e1d-4cd18f015a37 is unchanged.
Use decoder-only, no mmproj, c98304, four slots of24576, max512.

Direct recovery is FINALIZED: 1000 generated outputs and its single complete
official score are source-verified; quality remains unread.
Native recovery is OPENED at 1205 launched
role contacts and 3271.510500 repeated speech seconds.
Contacts do not equal completed utterances. Last monitor:
2026-09-14T01:43:34.038002+00:00, GPU98.0%,
slots {'busy': 4, 'idle': 0, 'total': 4}. No failure appeared in the recent campaign tail.

Do not edit active code, start another generating flight, change the serving
geometry, re-score completed manifests or replay interrupted contacts.
After native finalization and its first complete official score, verify both
sources, bind measured hashes through analysis-binding-handoff-v1.json, record
the paired read release, and run the existing shared readers. Preserve the
registered diagnostic-template correction described in STATUS-084.

## Hardware telemetry correction

A read-only audit initially suspected a cool 232MHz low-clock condition.
Root found contrary historical evidence and required a host/WSL comparison.
Root's near-contemporaneous 2026-09-14T01:41:34Z queries read WSL232MHz but
host1387MHz; earlier paired host readings were1515-1905MHz. WSL SM telemetry
does not establish an actual low-clock stall or whether a graphics lock exists.
The documented100W host policy remains unchanged. Recent real decode timings
do not resemble the historical6000ms/token custom-build stall.
No hardware mutation or additional model contact occurred.

Root receipt: DATA/coordination/
slurp-direct-vs-native-dual-store-reboot-recovery-v1/
hardware-telemetry-cross-check-v1.json,
SHA256695280edf04bbb590e4762311eed53ddf4dd538a60a81f9c7ace370fd7e2e097.
The earlier causal inference is withdrawn. Keep this correction in later
utilization interpretation. At01:39:59Z the preceding30samples averaged93.4%
GPU utilization, with all four slots busy in20samples and server_ok throughout;
this short interval is not the whole-campaign utilization estimate.

## Integrated CPU progress

TRAIN-A/B dimension aliases are complete and root-verified warm across2160rows:
numeric components, ordering, ranges and metadata are unchanged except the
content-to-intent-boundary dimension name. No re-encoding occurred.
Read the alias completion note and train-alias-root-verification-v1.json.

Typed TRAIN proposal output is integrated as2400c88c; root133focused tests pass.
It uses a registered one-phase program, prepared ORG input, shared OpenJiuwen
executor, canonical output and v3 source binding. Zero-to-bounded provisional
proposals are allowed; actual per-sample option identities are enforced.
Read docs/readiness/2026-09-14-typed-train-proposal-output-root-review-v1.md.

Provisional materialization is integrated as5b7fdbf4; root35materializer/memory
tests pass. It reconstructs true TRAIN source authority, verifies the finalized
bundle, binds actual protocol/decision identity and preserves all proposals
without selecting or admitting them. Read
docs/readiness/2026-09-14-provisional-train-materializer-root-review-v1.md.
No real proposal or admitted memory was created.

Root reviewed the next scientific gap: the existing memory loader's structural
filtering and stable record-ID ordering are not semantic relevance or learned
utility. Freeze a compact candidate-pack or relevance policy before evaluation.
Do not blindly take the first few of thousands of single-example rules.
Keep provisional evaluation separate from admitted runtime memory.

## Current parallel task and next work

Agent reboot_contact_audit is preparing HELD native dual-store TRAIN A/B source
configurations in
/home/chao/saea-worktrees/slurp-native-dual-store-train-source-held-v1,
branch codex/slurp-native-dual-store-train-source-held-v1,
based2400c88c. It reuses the1080-row fold descriptors, EVO-FOLDS-V2 promotion
and explicit sealed-segment-vector aliases. No model/ASR/encoder/scorer/quality
access is granted; root must review configurations and real CPU receipts.
The scientific incumbent and exploration decision awaits the current system
comparison. Do not interpret HELD configurations as contact admission.

The other two agents completed the materializer and telemetry audit and are
available for bounded independent follow-ups. CPU work stays within the shared
campaign limit. The live-speech successor fromSTATUS-084 is still HELD and
requires named diagnostic motivation plus complete prospective registration.
Continue GPU monitoring and complete-source analysis before choosing the next
full system. Maintain direct-vs-agent as the main comparison; only admitted
TRAIN feedback may produce future correction rules.
