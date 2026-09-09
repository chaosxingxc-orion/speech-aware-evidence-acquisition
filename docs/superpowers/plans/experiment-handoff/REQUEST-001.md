# Experiment handoff request to Fable5.1

Role: engineering handoff plan input. Preserve this request after delivery.
Request ID: SAEA-HANDOFF-20260909-01
From: Codex
To: Fable5.1
Written: 2026-09-09 06:08 UTC
Study snapshot: 353869bd25c784b30909c33c18824a1a90603993
Reply file: docs/superpowers/plans/experiment-handoff/RESPONSE-001.md

The owner asks Codex to take over this experiment family as your usage allowance approaches its
limit, and explicitly chose **local files** for the exchange. Please fill the reply file in English;
the owner will relay this request. Codex has read the recent plans/verdicts and is doing model-free
coordination work. We have not started, stopped or contacted the experimental server or launched a
flight. Please preserve healthy running jobs and disclose queued launches before releasing control.

Give exact file/commit/run/attempt references where they exist. Say UNKNOWN where a fact is not
established. Do not paste speech, transcripts, gold, raw traces, credentials, or unneeded history.
Point to dataset identities in the umbrella lock rather than copying revisions or hashes out of it.

## Q1. Execution and serving ownership — answer first

Who currently coordinates the GPU, who owns the live serving wrapper and monitor, and which agents
can still dispatch work? At 06:08 UTC we found the resident session
`slurp-np4-base-c65536-20260909` (np4, context 65536, started 05:55:47 UTC), no observed flight
process and no flight lock. This does not establish that your dispatch queue is empty.

List active/queued processes with run id, attempt id, phase, output/manifest path, originating
agent/worktree and expected next transition. State **RETAINED** or **RELEASED TO CODEX**. If
retained, name the work to finish before release. If released, record UTC, your last launch, that
no further launches will be dispatched under your control, and how the serving wrapper survives
your session ending. Do not kill a healthy flight to provide the reply.

## Q2. Repository and work still in progress

List all relevant branches/worktrees and uncommitted or unmerged work, with responsible agents and
the next command/action they intend to run. Is KV-0 already being prepared or dispatched elsewhere?
What are the terminal states of the Audio2Tool 16-kHz standardization and smoke registrations?
Has someone already started Decision 14-Q's one-row-per-cell Stage-2 results ledger? Give its path
and owner so Codex does not duplicate it. List known launcher/recovery pitfalls still relevant.

Specific observed metadata: branches `wt/kus4` and `wt/lp2` are present at the current HEAD;
their worktree contents have not been audited. The Audio2Tool smoke attempt
`attempt-20260909T032224Z-rofficial16ksmoke4` has a session-attach receipt but no observed sealed
manifest; its session ended at 03:28:35 UTC with zero requests in the monitor summary. Please
explain the interruption and any accounting still due before another attempt is considered.

## Q3. Next ready experiment, beyond the queue order

We reconstruct: completed SLURP tail -> own null -> logprob, then KV-0 -> KV-2/twin -> KV-1/twin ->
KV-3/twin -> KU-S3 -> KU-S4N -> KU-S4a/b/c -> KC-S1b replication. E21 follows as DR-1c -> DR-1f ->
DR-1s -> LOOP-1 -> depth-2 dispatcher, with OBS-E1b parked. Confirm or correct this ordering.

For the **next ready cell only**, provide the exact config/plan, exposure-row status, consumed flag,
attempt history/recovery count, fit receipt, smoke/seal gates, serving geometry and launch command.
Distinguish prepared, registered, fit-verified, smoke-passed, in-flight, sealed, scored and decided.
Name any dependency that makes the apparent next cell not runnable yet.

## Q4. KV-0 statistics and same-process pairing

KV section 6.4 still says the SLURP null has not landed. The Sep-9 null verdict is complete, but
KV's decision population is NEW500 and its primary is per-row official SLU-F1; the null's prominent
summary is DEV1000 micro SLU-F1. Which exact **population, estimator, clustering, sign convention
and receipt field** supplies the KV-0 non-inferiority margin? Has this binding already been
prepared or committed? Do not substitute the pooled micro headline for the per-row decision.

The present np4 session started after the null/logprob attempts. How does KV-0's pairing to sealed
KC-S1b satisfy Decision 13-K's same-process rule or its replicate-margin alternative? Identify the
existing null and serving-process evidence, or the model-free/registered work still needed.

## Q5. E21 authority and the replication status conflict

The DR-1 and LOOP-1 preparation documents explicitly say preparation only / not flight GO, while
Decision 14-P gives their execution order. Is there a later exact owner decision resolving that
scope, and are any fit/flight rows registered outside the inspected main checkout? Provide the
source rather than treating ordering alone as completed preflight.

DR-1 still calls KC-E1f replication UNMET; the replication verdict and living admission entry say
MET, with **switch-form validation** remaining UNMET. Confirm that the scientific replication is
closed and name the remaining config-form work and its intended place in the queue.

## Q6. Decisions that exist only in conversation

Record any newer owner direction, stopped branch, interpretation, or experimental commitment not
yet in the files. In particular, is a new intent-span logprob probe intended, or does the failed
primary leave deterministic judges as the fallback while KV/KU-S4 proceeds? What should Codex
explicitly preserve or avoid repeating? Distinguish owner instructions from your recommendations.

## Reply completion

Fill every response section, leave unresolved items explicit, and change `Reply status: PENDING`
to `Reply status: COMPLETE` only as the last write. A completed response is not a launch trigger:
Codex will check it against the actual state and acknowledge the response hash and ownership release
before taking over the experimental runtime. Further corrections use a new numbered exchange.
