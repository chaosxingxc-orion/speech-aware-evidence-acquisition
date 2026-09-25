# Handoff to Fable 5.1: active Stage-3 continuation

This is the current entry point. It supersedes pending/running statements in
the [preserved earlier handoff](archive/2026-09-25-HANDOFF-TO-FABLE51-through-63b1bb66.md).
Historical research artifacts, registrations and verdicts remain authoritative
for their own flights. Do not interpret old plans as permission to restart them.

## Checkpoint and research objective

Checkpoint: 2026-09-25T20:31:06.131796+00:00. Script state is running, current step
candidate-recovery-control-v1, with no warning or handoff requirement.
The driver and generation worker were verified live (PIDs 84082 and 84442);
revalidate process identity before acting. Process IDs and utilization are
observations, not durable identity or completed-row counts.

Stage-2's frozen four-node system already has substantial complete-task benefit.
Stage-3 has **no learned-policy update with established stable benefit yet**.
The objective remains full sampling, terminal feedback, update, reexecution,
and matched replication, first on SLURP, then Audio2Tool/E21/E22. Engineering
proofs and fixed-policy improvements do not complete that objective.

No new owner decision is required to finish the current registered pair.

## Live execution: preserve this queue and frozen source

| Item | Current authority |
| --- | --- |
| Queue | /home/chao/batch-queue.json |
| Ordered work | Control smoke4 (passed), control625 (running), expanded smoke4, expanded625 |
| Worker checkout | /home/chao/saea-worktrees/fable-batch-flight |
| Frozen worker commit | 9f6a949f445e4fb308789eb0786a1a25c3fb8f69 |
| Resident session | serving-slurp-native-candidate-five-train-a-np4-v1 |
| Geometry | Decoder-only, no-mmproj, 4 slots x 24576 tokens, total 98304, output 512 |
| Driver | Existing Windows task SAEA-Batch-Driver starts WSL Ubuntu-24.04 |
| Status / stop | /home/chao/batch-status.jsonl / /home/chao/batch-STOP |
| Data root | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data |

Do not advance the worker checkout until BOTH complete arms finish scoring.
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
| Contextual complete-continuation learner | Still outstanding at the real post-Perception/pre-Solver boundary; no learned continuation-selector has run |

Test populations overlap; do not add them into one coverage claim. These are
targeted checks, not a claim that every historical repository test passes.

Read the [semantic feedback input contract](../readiness/2026-09-25-system-semantic-feedback-inputs.md),
[trajectory analysis](../readiness/2026-09-25-candidate-recovery-whole-trajectory-analysis.md),
[summary interface](../readiness/2026-09-25-complete-system-semantic-summary-input.md),
[objective audit](../readiness/2026-09-25-system-terminal-ratio-objective-audit.md),
[policy catalog](../readiness/2026-09-25-system-policy-catalog-runtime.md) and
[baseline fidelity audit](../readiness/2026-09-25-training-free-rl-baseline-fidelity.md)
for contracts and proof receipts. Raw task answers stay outside Git.

## Next algorithm boundary

1. Finish and interpret the current whole-system pair under its registered
   rule. Root personally owns attribution and scientific decisions.
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
   executed summary/feedback comparison, actual semantic operations,
   consolidation and execution using the updated frozen experience. The
   summary serializer alone is not an algorithm reproduction.

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
