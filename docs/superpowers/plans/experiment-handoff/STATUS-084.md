# Status 084: direct arm finalized and native system generating

Snapshot: 2026-09-14T01:14:52.693123+00:00. Continue the complete owner goal; the useful system,
reliable benefit, and full TRAIN optimization/transfer requirements are not
yet complete. This interval made progress: the direct arm finished, its
complete first-score sources were verified, the native arm started, and
parallel work produced concrete successor configuration and reader corrections.

## Active immutable campaign

The sole reboot recovery stays on frozen runtime commit
6307a3ab30c93a6be35114deb5f701e6e444292f at
/home/chao/saea-worktrees/slurp-dual-store-reboot-recovery-runtime-v1.
Campaign PID 3413 / managed exec 9571. Service PID 793 / exec 25977,
session serving-slurp-dual-store-reboot-np4-v1; monitor PID 1142 / exec 18862.
The service remains decoder-only, no mmproj, c98304, four slots of 24576,
max512. Do not edit the active runtime, change geometry or start another flight.

The direct recovery is FINALIZED with all 1,000 calls and 2884.7936875 speech
seconds. Its only complete official job succeeded with per-sample output,
69.722706232 seconds scoring time, and no sharding. Root verified the bundle,
1,000 output rows, single score job and first-score source envelope. No quality
values were exposed or paired read released.

- Direct manifest SHA256:
  cd5dcf65fcdc2a61da93f0980e3a104d09cf4d521edb402ac9258e54c60d1d87.
- First complete score SHA256:
  696fc4db6a80ec08197c706386352d6d9b2c3eb945d6f757d1d030788e05aba2.
- Root direct source verification:
  DATA/coordination/slurp-direct-vs-native-dual-store-reboot-recovery-v1/
  direct-source-verification-v1.json,
  SHA256 ec65e5d8918be5926a0640ad401e7f8971f23cd04c2288bc6642efa138ecc74d.

The native recovery is OPENED at 388 launched model contacts.
These are contacts across roles, not completed utterances. Latest monitor at
2026-09-14T01:14:41.429154+00:00: GPU 71.0%, 4/4 busy.
The direct-to-native handoff included a measured idle period during sealing and
native source/request preparation; retain it in post-seal utilization accounting.
No whole-period utilization or exact idle duration has been inferred here.

## Ready post-seal analysis

Read the concrete handoff at DATA/coordination/
slurp-direct-vs-native-dual-store-reboot-recovery-v1/
analysis-binding-handoff-v1.json,
SHA256 8ba8094102153857e05e21dfd24310d3548df0de47e7b9fc312ace9ebb688fa5.
It names source verification, first-score receipt creation, actual binding
pointers and existing shared reader commands. Do not invent FlightReceipts.

The original diagnostics template used the wrong interface key:
native_system_perception_only instead of native_system_perception_source.
Root verified the CLI constant, retained the frozen original, and authored a
successor that changes only this key, with the entire value unchanged.

- Successor: docs/readiness/2026-09-14-slurp-dual-store-native-diagnostics-reader-ready.template.json;
  SHA256 c238271865c81a690e39a0d9be71bb9f470ff25425a33c6e6e2e67a195503b69.
- Correction registration:
  docs/readiness/2026-09-14-slurp-dual-store-analysis-interface-correction-v1.json;
  SHA256 d89c8f5c0c05b7311277957bed572b0fd2306fd55d2104faee5d4f2088d07f41.

This fixes the reader interface before quality exposure; metrics, estimator,
population and decision rules are unchanged. After the native arm fully seals
and completes its first official score, root verifies both sources, binds
measured hashes, records the paired read release, and runs the shared readers.
Native traces support supplied-value and lexical-consumption diagnostics.
Candidate-to-value selection audits require genuine optional FlightReceipts;
if absent, report that diagnostic unavailable rather than synthesize receipts.

## Parallel progress and next handoffs

1. The held current-dual-store live-speech successor is committed. Reviewer alone
   gains the existing full-utterance Whisper tool and existing instruction;
   Solver retains answer authority. Root kept the original native episode ID
   and moved the old config-bound preparation pin to prospective metadata.
   A future admitted configuration needs a fresh prepared wrapper, its own
   generation/fit/ASR/ledger/CPU-resource bindings and analysis registration.
   It remains non-dispatchable until the current pair names a suitable bottleneck.

2. Agent reboot_contact_audit is implementing the typed TRAIN proposal output
   seam at /home/chao/saea-worktrees/typed-training-proposal-output-v1,
   branch codex/typed-training-proposal-output-v1, based on b8a328ea.
   Root approved a zero-to-bounded-proposals response (do not force a correction),
   shared response/content registries, exact prepared-context source pin,
   per-sample option labels, bounded applicability and text, and existing
   runtime/bundle verification. Legacy v1/v2 stays unchanged. Synthetic integration
   tests are in progress; root has not reviewed or merged this implementation.
   No proposal, memory admission, candidate evaluation or GPU contact is granted.

3. Agent speech_tool_inventory_recovery identified and documented the TRAIN
   alias format gap: both A/B query sources are sealed, ordered, disjoint,
   1,080-row, 2,048-dimensional segment-vector files. The old dimension alias
   accepts flat vectors. Root has now authorized the minimal shared explicit
   segment-alias branch. It must preserve every audio/frame/segment/source field
   and numeric component, rename only the dimension, reuse the existing segment
   loader, and keep flat v1 semantics. Then prepare the two pinned CPU aliases,
   test warm reuse and zero contact, and report exact output/receipt hashes.
   Do not flatten, pool, re-encode or change an active source.
   Worktree: /home/chao/saea-worktrees/codex-native-speech-tool-inventory.
   Gap note is historical; completion will need a separate successor.

The shared output seam and alias preparation reduce future setup but are not
the complete training-free RL loop. Provisional materialization, disjoint TRAIN
candidate evaluation and real admission remain required. Root will personally
review these choices and implementations. Keep DEV errors out of correction
construction. Select the next full system from completed native task diagnostics;
transfer the shared system to Audio2Tool and E21 after the SLURP base stabilizes.
