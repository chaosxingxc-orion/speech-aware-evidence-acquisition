# Handoff to Fable 5.1: active Stage-3 continuation

This is the current entry point. It supersedes pending/running statements in
the [preserved earlier handoff](archive/2026-09-25-HANDOFF-TO-FABLE51-through-63b1bb66.md).
Historical research artifacts, registrations and verdicts remain authoritative
for their own flights. Do not interpret old plans as permission to restart them.

## Checkpoint and research objective

Checkpoint: 2026-09-26T00:48:16Z. The sole seal recovery is now
execution-closed without a comparative verdict. Control625 sealed and passed
structural inspection at 2026-09-25T23:15:09Z: 625 distinct rows, 3,657 model
contacts, 16,056.869125 audio seconds and one full official scoring job.
Its attempt is FINALIZED. No quality metric has been read.

Expanded smoke4 failed at 23:17:00Z when the local service closed a Reviewer
connection. Server.log records MUL_MAT failure and CUDA illegal memory access.
Expanded full625 never started. The failed smoke consumed 13 contacts and
55.45625 audio seconds; after confirming no worker/driver/server process was
live, root preserved its OPENED record and closed it ABORTED through the frozen
worker's existing attempt API. Successful control and smoke records are retained.

Windows subsequently reported bugcheck 0x116 (display-driver timeout recovery
failure), record 61904 at 23:31:19Z, and boot at 23:31:02Z. The record timestamp
does not prove the precise crash onset or the underlying kernel/driver/hardware
cause. At the checkpoint, the Windows task was Ready, no llama-server or
campaign was running, and GPU use/memory were zero. Do not use stale telemetry
as live health. No service restart, driver change or automatic second recovery.

Read the [failure receipt](../receipts/continuation/2026-09-25-candidate-seal-recovery1-runtime-failure.json).
The queue, STOP and all source artifacts remain intact. Preserve the worker at
60d5719728f7a79f374000bcbd742508785c9894 in
/home/chao/saea-worktrees/codex-stage3-continuation-20260925 for source verification.
The [launch receipt](../receipts/continuation/2026-09-25-candidate-seal-recovery1-launch.json)
records the original authority, now exhausted by this execution failure.

The old control remains ABORTED with 625 outputs, 3,723 model contacts and
zero official scores. Its worker remains at 9f6a949f. Root verified owner
death, kernel-lock availability and repeated zero busy service slots before
archiving its stale lease metadata; the kernel guard inode is retained.
The old queue, commit pointer, STOP and smoke logs are preserved separately.
The recovery retains the roster, prompts, knowledge and scientific gates.
Any further execution failure closes this flight; no second recovery.

Stage-2's frozen four-node system already has substantial complete-task benefit.
Stage-3 has **no learned-policy update with established stable benefit yet**.
The objective remains full sampling, terminal feedback, update, reexecution,
and matched replication, first on SLURP, then Audio2Tool/E21/E22. Engineering
proofs and fixed-policy improvements do not complete that objective.

The named recovery is the one permitted attempt. Existing infrastructure resume
does not apply to a harness defect; keep the aborted source immutable.

## Prior failed execution: retain for provenance

| Item | Current authority |
| --- | --- |
| Prior queue archive | DATA/coordination/slurp-stage3-candidate-seal-recovery1-v1/prior-runtime/batch-queue.json |
| Ordered work | Control smoke4 passed; control625 ABORTED at seal; expanded not started |
| Worker checkout | /home/chao/saea-worktrees/fable-batch-flight |
| Frozen worker commit | 9f6a949f445e4fb308789eb0786a1a25c3fb8f69 |
| Resident session | serving-slurp-native-candidate-five-train-a-np4-v1 |
| Geometry | Decoder-only, no-mmproj, 4 slots x 24576 tokens, total 98304, output 512 |
| Driver | Existing Windows task SAEA-Batch-Driver starts WSL Ubuntu-24.04 |
| Status / stop | /home/chao/batch-status.jsonl / /home/chao/batch-STOP |
| Data root | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data |

Retain the failed source worker checkout for provenance. Do not advance it or
replay its queue while diagnosing recovery.
Generation/scoring run independently of the assistant, network and credits.
The OS task has no network condition, execution timeout or automatic replay.
Keep the existing fifteen-minute heartbeat slurp; notify on meaningful change,
failure, completion or required action, not every unchanged snapshot.

Use scripts/flights/batch/continuation_status.py with the queue, status,
data-root, stop-marker, --check-processes, driver-script, session-id and
the session's serving/SESSION/monitor.jsonl telemetry path. Reuse the actual
compact invocation recorded by the launch receipt and prior checkpoint.
Do not scan answer text, infer completed samples from service totals, or
create progress-monitor subagents.

The smoke passed structural inspection at 2026-09-25T19:30:47Z: four distinct
rows, 25 registered model contacts and no tool calls. No
official task-quality score was read or used for smoke admission.
The full control began at 19:30:57Z. All eight clean preflights passed.
Each real request still requires strict exact fit; the conservative envelope
is only a preparation estimate. No truncating context, dropping cards,
reducing output limits or changing geometry to make an arm fit.

[Registration](../readiness/2026-09-25-slurp-stage3-candidate-recovery-v1-preregistration.md)
and [launch receipt](../receipts/continuation/2026-09-25-candidate-recovery-launch.json)
are the execution authority. Exact run/attempt IDs, caps and source pins live in
the [registered package](../readiness/2026-09-25-slurp-stage3-candidate-recovery-v1/README.md).
Never invent substitute IDs or consume a new attempt without registration.

## Active recovery execution authority

Use the [fresh recovery registration](../readiness/2026-09-25-slurp-stage3-candidate-seal-recovery1-v1-preregistration.md),
[package](../readiness/2026-09-25-slurp-stage3-candidate-seal-recovery1-v1/README.md)
and launch receipt above. Runtime pointers still identify the recovery for diagnosis, not permission
to replay it. Its queue has stopped and the service is absent. Ordered work is control smoke4/control625/expanded
smoke4/expanded625, with unique step names candidate-seal-recovery1-control-v1
and candidate-seal-recovery1-expand-v1. The same resident session and geometry
remain in use. The fifteen-minute slurp monitor stays quiet on unchanged state.
The root admission cites the corrected v2 source exclusion proof.

## Current scientific question and decision rule

Both complete policies use the same Perception, twenty retrieved examples,
new common Solver/Reviewer/Planner prompts, canonical plain rendering, one
revision and full legal label inventory. The sole declared mode difference
is original-only versus append-selected-exemplars.

The expanded policy preserves original candidate order, adds example-supported
labels up to eight total, supplies their intent distinctions and at most 24
additional unique slot cards while preserving up to 28 original cards.
The source-bound proposal remains identical across downstream roles and revision.
Frequency is not confidence; proposed candidates never restrict legal answers.

Read outcomes only after both complete manifests and one official scoring job
per arm seal. Then bind manifest, phases, outputs, flight and scoring hashes.
The original primary test is expanded-control official pooled word/character
SLU-F1, natural mixture, paired utterance-cluster CI95 lower endpoint > 0.
Intent protection requires paired CI90 lower endpoint > -1.44 percentage points.
Use 10000 draws and seed 20260915; retain all rows, every scenario and the
registered equal-scenario sensitivity. See the registration for exact details.

Coverage is diagnostic. Report complete paths, repairs AND harms, whether a
repair survives delivery, empty-target FP, nonempty FP/FN, format/fallback,
input and contact costs. Actual supplied evidence does not prove semantic use.
Do not convert gold-based diagnostic groups into runtime decision states.

A pass is a construction candidate requiring matched same-roster replication.
Fixed control-then-expanded order leaves time effects. Failure closes this
tested continuation: no subgroup rescue, changed threshold, component-only
success claim or automatic rerun. An execution failure stops the queue;
at most one named, separately registered recovery may follow a four-row proof.

Source clarification: actual R01C625 overlaps **zero samples and utterances**
with all three knowledge stores. The historical 57/155 card-support overlaps
refer to the larger R01 roster, outside R01C. Use the
[source clarification](../readiness/2026-09-25-slurp-stage3-candidate-recovery-v1/source-clarification-v1.md)
and [preflight amendment](../receipts/continuation/2026-09-25-candidate-recovery-preflight-amendment.json).
R01C is repeatedly exposed construction, not independent holdout.
DEV6570 and test13078 remain closed.

## Available analysis and algorithm work

All completed work is merged into master. The implementation checkout is
/home/chao/saea-worktrees/codex-stage3-continuation-20260925; the main checkout is
/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition.
Analysis code may be newer than the frozen generation checkout. Pass the
retained clean worker as --source-repo-root to source verification; do not
move that checkout merely to run newer readers.

| Work | Evidence and remaining limit |
| --- | --- |
| Whole-system feedback and trajectory export | Shared verified source, official terminal counts, all roles/tools/finite outcomes and source hashes; no node-level causal credit |
| Candidate recovery attribution, 2fd3b934 | Proposal custody, original/new coverage, first/last/delivered choices, retained/lost repairs; 82 related tests and 9 gates |
| Semantic summary input, 19310d6b | Exact whole episode in the upstream first trajectory field; speech/split/round grouping, lossless field deduplication; 118 tests and 9 gates |
| Objective audit, 63b1bb66 | Synthetic frozen-reward/local-F1/group-normalization counterexamples and exact fractional prototype; 42 tests and 9 gates |
| Complete episode policy selector/catalog | Executable pre-Perception choice and terminal credit; one episode-start state only learns a global fixed choice |
| Semantic feedback input preparation | Complete episode/count binding, separate summary and signed-feedback channels, explicit terminal-vector eligibility; 131 related tests and 9 gates; no model-facing update yet |
| TF-GRPO cross-round consolidation source audit | Seven synthetic exact-source cases; sparse-ID ADD can overwrite prior experience after deletion. Require stable IDs and explicit atomic operations in the future adapter; no runtime change or task claim |
| Atomic candidate consolidation | Shared ADD/UPDATE/DELETE over existing provisional experience records; immutable revision lineage and all-or-nothing failure; 143 related tests and 9 gates passed. Model-facing semantic stages and real runtime reexecution remain outstanding |
| Consolidated candidate source replay | Existing materializer, attestation and runtime reader now accept a distinct verified consolidation-chain output. 84 related tests and 9 offline gates pass; connected synthetic native execution reaches Reviewer tool and Solver revision; model-facing semantic stages and real reexecution remain outstanding |
| Complete-system summary runtime connection | Shared full-source preparation and ORG/request path, configured summary prompt and baseline; 61 related tests and 9 gates pass, with synthetic fit/send and raw artifact-output proof. No real summary generation yet; the existing arm also attaches original speech |
| Contextual complete-continuation learner | Still outstanding at the real post-Perception/pre-Solver boundary; no learned continuation-selector has run |

Test populations overlap; do not add them into one coverage claim. These are
targeted checks, not a claim that every historical repository test passes.

Read the [semantic feedback input contract](../readiness/2026-09-25-system-semantic-feedback-inputs.md),
[trajectory analysis](../readiness/2026-09-25-candidate-recovery-whole-trajectory-analysis.md),
[summary interface](../readiness/2026-09-25-complete-system-semantic-summary-input.md),
[objective audit](../readiness/2026-09-25-system-terminal-ratio-objective-audit.md),
[policy catalog](../readiness/2026-09-25-system-policy-catalog-runtime.md) and
[baseline fidelity audit](../readiness/2026-09-25-training-free-rl-baseline-fidelity.md)
for contracts and proof receipts. Read the new
[consolidated candidate contract](../readiness/2026-09-25-consolidated-candidate-materialization.md)
for the source-replay connection and its exact test boundary. Raw task answers
stay outside Git.

## Prepared-text summary continuation

CPU implementation checkpoint: 2026-09-26T01:24:30Z.
The new [prepared-text path](../readiness/2026-09-26-prepared-text-system-summary.md)
uses system-trajectory-summary-text-v1 and the distinct D2 arm
prepared-context-text. It keeps verified whole-episode ORG input, shared
controller/OpenJiuwen and exact fitting, while sending no fresh speech or task
ontology. The default runtime binding and request renderer are covered by
synthetic connected tests; 326 targeted regressions passed with one existing
skip; all nine offline gates and Ruff passed. A separate nineteen-test run
confirms legacy feedback and zero-media cost behavior. Read the final validation
receipt linked in that document for test boundaries and log hashes.

The older multimodal summary config is retained unchanged. The new input mode
does not complete the semantic comparison/update/reexecution loop or establish
an RL benefit. GPU state remains the execution-closed failure checkpoint above.
No source worker, queue, STOP, service or research result was changed.

## Whole-system summary runtime connection

The model-facing summary input now has a shared preparation/loader/baseline
path. Read the [runtime contract](../readiness/2026-09-25-system-summary-shared-runtime.md).
It re-verifies the full frozen TRAIN source, retains all role/tool/revision/
delivery content and feeds the existing ORG serializer, controller, OpenJiuwen,
actual request fitting and raw artifact output. No new research model/scorer
contact or generation-worker change occurred.

The older shared artifact arm also attaches original sample speech. Register
that exposure as a multimodal adaptation. The new prepared-text route above
removes fresh media and task knowledge; its existence does not imply that an
upstream-equivalent algorithm cycle has run.
The summary context contains no scores or reference answers, though the source
bundle verifier checks score-file integrity. This connection is not a complete
executed TF-GRPO cycle. Semantic group comparison, typed proposals, model-side
consolidation and frozen reexecution are still required.

Optimize coordinated complete policies and use terminal task return. Local
role improvements remain diagnostics until they survive full delivery and
matched replication. Resolve disjoint TRAIN memory-use scheduling before
multi-round registration; never self-apply provisional experience silently.

## Next algorithm boundary

1. Preserve the execution-closed incomplete pair and diagnose the CUDA/host
   failure. It has no comparative effectiveness verdict. Do not read isolated
   control quality or automatically replay the failed expanded attempt.
   Root personally owns any new registration and scientific interpretation.
2. Admit a small, explicit space of coordinated complete continuations from
   terminal evidence. A Solver branch score is not a system return.
3. Put each decision at a boundary where its state is actually available.
   Log state, action set, exact action probability, source identity, every
   subsequent role/tool visit and final official task feedback. Retain
   no-action, failure, abstention and unrevised episodes without invented credit.
4. Execute construction sampling, complete scoring, external value/experience
   update, frozen reexecution and matched evaluation. Compare both locked
   default and strongest eligible fixed complete policy. Replicate before
   claiming stable benefit or moving the main effort to another carrier.
5. Complete scholarly same-space baselines: MemRL remains a pinned reference
   with explicit retrieval/update/credit adaptations; TF-GRPO now has separate
   feedback fields and versioned eligibility preparation, but still needs an
   executed summary/feedback comparison, model-generated semantic operations,
   consolidation-stage execution and real execution using the updated frozen
   experience. Consolidated candidates now connect through the existing
   source-attestation/runtime path in synthetic integration tests. The deterministic atomic plan applier
   is now implemented over the existing provisional record contract. The
   summary serializer alone is not an algorithm reproduction.
   Candidate runtime still requires disjoint TRAIN construction/evaluation;
   reconcile the multi-round construction schedule before registration rather
   than silently allowing provisional self-application.

Keep the approved frozen-F0 baseline unchanged. Its utility detects improvement
over F0 but need not rank improved policies by pooled F1. The ratio-aware
prototype is classical exact-count optimization, not a learned method or new
theorem. A separate comparator requires count estimation/support, state
occupancy, intent protection, admission and real reexecution. Preserve raw
terminal counts; do not optimize a mean of standardized group advantages and
assume it equals the population task objective.

## Closed lines, source history and owner preferences

Do not restart semantic-delta, VAR-2, F10 or evidence-path arms. Read historical
[VAR-1](../results/2026-09-25-slurp-var1-complete-evidence.md),
[VERIFY-1](../results/2026-09-25-slurp-verify1-complete-evidence.md),
[F10](../results/2026-09-25-slurp-f10-complete-verdict.md),
[evidence-path](../results/2026-09-25-slurp-evidence-path-system-verdict.md) and
[candidate support](../results/2026-09-25-slurp-candidate-support-diagnostic.md)
only for their registered evidence and limitations.

The previous handoff's 914 lines are preserved byte-for-byte in the archive
linked above, SHA-256:
f9715df89823eea234a22149bf837ad89f4e30bc523b91f9a7438a736a4477f8.
It contains superseded launch instructions; this current checkpoint and each
flight's immutable registration take precedence for their respective scope.

Use WSL Ubuntu-24.04 and /home/chao/.venvs/speechrl/bin/python with explicit
source paths; do not reinstall editable packages across checkouts. English
documents and model contexts, zero paid research API, frozen core and final
Solver answer authority remain in force. Keep one model-generating flight,
one full scorer, at most 8 aggregate preparation workers during a campaign
(20 idle). Owner has confirmed the power mode is optimal; do not reopen that
investigation. Use scripts for progress, merge finished work into master
promptly, and keep this entry point short and current.
