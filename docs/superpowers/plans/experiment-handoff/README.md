# Fable5.1 to Codex experiment handoff

Role: engineering plan. Status: awaiting the incumbent coordinator's reply.
Snapshot: 2026-09-09 06:08 UTC, study commit `353869bd25c784b30909c33c18824a1a90603993`.

The owner asked Codex to take over this experiment family as Fable5.1 approaches its usage limit,
first understanding the setup, progress and pending experiments. The owner then specified **local
files**, with the owner relaying the request to Fable5.1. This authorizes this handoff work and its
coordination mechanism; it does not convert an explicitly preparation-only cell into a registered
flight. All files and agent replies in this exchange are English.

## Read and reply

1. Fable5.1 reads [REQUEST-001.md](REQUEST-001.md) and fills [RESPONSE-001.md](RESPONSE-001.md).
2. Fable5.1 leaves `Reply status: PENDING` until the reply is complete, then changes it to
   `Reply status: COMPLETE` as the **last write**. It records whether execution ownership is
   released or retained; a complete explanation alone does not release ownership.
3. Codex checks the reply, reconciles it against the current Git state, exposure ledger, attempt
   manifests, serving records and lock state, then acknowledges the exact response hash in this
   plan and in `state.json`. A response is evidence to verify, not automatic execution authority.
4. Codex updates this plan in place. Subsequent questions use `REQUEST-002.md` / `RESPONSE-002.md`;
   completed exchanges remain unchanged. A new round updates the request id and increments the
   generation in `state.json`.

The owner can relay the two file paths; copying chat history or raw experimental data is unnecessary.
There is **no installed background poller**. At the start of each continuation and before any
experiment action, the coordinator runs the read-only checker:

```bash
python scripts/checks/experiment_handoff_check.py
```

Run it from this study in WSL2 `Ubuntu-24.04` with `~/.venvs/speechrl` activated. It reports
`WAITING_FOR_REPLY`, `REPLY_READY`, or `INVALID`, the current commit and dirty-file counts. It
never starts a server, opens experimental data, changes state, acquires a lock, or authorizes a
launch. `REPLY_READY` only means a matching response was marked complete. Its schema-v1 scope
is this pending exchange; a later operational handoff must be acknowledged separately.

## One coordinator and one experiment in flight

- Codex owns these request/state/plan files and the checker. Fable5.1 owns the response file.
  Both agents leave the other's files untouched during a round.
- Execution ownership is **UNCONFIRMED**, not inferred from an idle GPU, an empty lock directory,
  a timeout, exhausted usage, or a completed response. Codex makes no experiment or serving contact
  during this initial reconciliation.
- Fable5.1 reports any running or already-dispatched jobs and any agent/worktree that can still
  launch. It either retains ownership to finish a named attempt, or records a release point and
  that no further launches are queued under its control. It must not interrupt a healthy flight
  just to answer the request.
- After a release, Codex verifies it against live metadata and records acceptance of that release,
  the serving-session custodian, the next named action, and the evidence pointers. The existing
  runtime flight lock remains mandatory; these documents are **not a replacement lock**.
- A flight agent attaches to the coordinator's resident session. Only the confirmed serving
  coordinator changes that session. A live wrapper may belong to Fable5.1's session and needs
  an explicit lifecycle handoff; ownership of a Markdown file does not keep its process alive.
- Before a launch, satisfy the experiment's own authority, exact ExecutionPlan, exposure row,
  clean-tree preflight, registered prompt-fit/tokenizer contacts, smoke gate and one-shot rules.
  Never automatically retry an attempted run or change a margin after seeing its treatment result.
- A flight launcher's `--dry-run` is not necessarily read-only: the current SLURP launcher writes
  an aborted attempt after preflight. Its wire check also writes artifacts and scores canned
  responses. Do not invoke either on a formal run id merely to inspect status.
- At every meaningful transition (registration, launch, seal, score, verdict, failure, release),
  the execution owner updates the canonical ledger/receipts first, then this plan's pointers.
  Record the run/attempt id, commit, session id, terminal state, recovery count and next action.
  Keep raw traces, speech, weights and model outputs outside Git.

## Working understanding of the experiment

The research object is an external training-free control system around the frozen Qwen3-Omni
core. Its current organization is **Planner -> Observer -> Solver -> Reviewer -> Planner/Commit**.
The Reviewer only scores and flags; the frozen core remains the answering Solver. OBS, ORG,
SUPPLY and USE remain separate trace axes. The implementation uses one shared `FlightRuntime`,
OpenJiuwen executor and controller, with thin carrier adapters and module switches in config.

The program studies knowledge construction, knowledge consumption and system evolution on
Earnings21+ConEC, SLURP and Audio2Tool. Evidence remains bounded Stage-2 discovery/dev work,
with zero paid API spend and no paper-scale or confirmatory expansion. Dataset identities are
resolved only through the umbrella `docs/datasets.lock.json`. Exact results and hashes remain
in their canonical verdicts and receipts; the table below is a routing summary.

| Line | Verified state at the snapshot | Immediate implication / canonical source |
|---|---|---|
| SLURP intent-conditioned slot schema KC-S1b | Admitted; same-roster replication still in the recorded queue | [KC-S1 verdict](../../../readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md) |
| SLURP silence tail | Not admitted; the later own-null read revises the explanation without admitting the tail | [Tail verdict](../../../readiness/2026-09-09-slurp-silence-tail-v1-verdict.md), [own-null verdict](../../../readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md) |
| SLURP own-null | Completed and finalized, 1,000 rows; use the carrier's measured noise with the matching estimator/population | [Own-null verdict](../../../readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md) |
| SLURP logprob judge | Whole-answer minimum primary not admitted; intent-span signal is a successor diagnostic, not an admitted switch | [Logprob verdict](../../../readiness/2026-09-09-slurp-logprob-judge-probe-v1-verdict.md) |
| SLURP KV views | Seven arms prepared; KV-0 must seal and be read before successors; no KV flight row found in this audit | [KV preregistration](../../../readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md) |
| E21 KC-E1f constrained repair | Scientific replication **MET**. Default-plan switch-form validation remains **UNMET** | [Replication verdict](../../../readiness/2026-09-08-e21-kc-e1f-replication-v1-verdict.md), [admission receipt](../../../receipts/harness-admission.json) |
| E21 OBS-E1 speaker-turn units | Rejected: overall transcription improves but PERSON errors worsen; lost surrounding context is the named mechanism | [OBS verdict](../../../readiness/2026-09-08-e21-obs-speaker-turn-units-v1-verdict.md), [harm decomposition](../../../readiness/2026-09-08-e21-obs-e1-person-harm-decomposition-v1.md) |
| E21 DR-1 / OBS-E1b / LOOP-1 | Prepared, not observed as flown. DR-1 and LOOP-1 preparation records explicitly distinguish preparation from flight GO | [DR-1](../../../readiness/2026-09-09-e21-draft-then-refresh-dr1-v1-preregistration.md), [LOOP-1](../../../readiness/2026-09-08-e21-loop-1-v1-preregistration.md) |
| E21 dispatcher | Depth 1 neutral and admitted at tested geometry; depth 2 deferred | [Dispatcher verdict](../../../readiness/2026-09-08-e21-dispatcher-admission-v1-verdict.md) |
| Audio2Tool | No admitted new content mechanism established by the audited ORG-1/KC-A1 records; some standardization registrations need terminal-state reconciliation | Request Q2; do not interpret an unconsumed registration as a runnable fresh attempt |

## Queue to reconcile with Fable5.1

The latest recorded ordering is umbrella
`wiki/experiments/speech-aware-evidence-acquisition/2026-09-07-owner-go-stage2-cells-and-foundation-fixes.md`,
Decisions 13-M and 14-P. This ordering is not a ready-to-run queue:

| Order | Work | Prerequisite still requiring attention |
|---|---|---|
| 1 | SLURP KV-0 | Resolve own-null margin for **NEW500 / per-row official SLU-F1**, current process pairing, actual exposure/fit/smoke state, and execution ownership |
| 2 | KV-2 + twin -> KV-1 + twin -> KV-3 + twin | KV-0 must establish the valid base; per-view registered fits, token-matched twins and verdict gates |
| 3 | KU-S3 -> KU-S4N -> KU-S4a/b/c -> KC-S1b replication | Correct predecessor rebinding; prepared CPU products; exact plans and one-flight discipline |
| 4 | E21 DR-1c -> DR-1f -> DR-1s -> LOOP-1 -> depth-2 dispatcher | Reconcile preparation-only language with later owner order; registered fit and per-cell flight rows; preserve controls and stop rules |
| parked | OBS-E1b; further EVO rounds; enhancement; intent-span logprob successor | Prepared/named is not admission. Do not reopen or schedule automatically |

Default plans and candidate freeze wait for the KV/KU-S4 families per Decision 12-I.
Decision 14-Q also calls for a study results ledger; confirm its assigned writer before creating
a competing version. This handoff plan is not that scientific results ledger.

## Live metadata snapshot and discrepancies

At approximately 06:08 UTC, an existing session `slurp-np4-base-c65536-20260909` was resident:
profile `q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64`, context 65,536,
four slots, session start 05:55:47 UTC. Read-only process metadata showed a server and monitor,
no flight/scorer/preprocessor process, an empty flight-lock directory and zero requests in the
monitor samples inspected. This is an **idle snapshot, not a release of ownership**. No server
endpoint was contacted by this handoff audit. Re-read metadata immediately before any action.

Resolve these concrete discrepancies before dependent work:

1. Umbrella `Research-Objective.md` still says `last_refresh: 2026-08-25`; its routing and the
   old scoreboard cannot establish the Sep-9 queue. Consolidate confirmed state back into the
   existing umbrella current layer after the reply, without creating a second authority.
2. DR-1's introduction and preparation ledger retain KC-E1f replication UNMET. The later
   replication verdict and living admission entry say MET; the outstanding obligation is
   **validation of the registered switch form**, a different requirement.
3. KV section 6.4 says SLURP's null has not landed. It has. Micro pooled SLU-F1 and mean per-row
   SLU-F1 are different estimators; DEV1000 and NEW500 are different populations. Bind the exact
   null used by the decision before treatment results exist. Do not copy a headline margin.
4. The current np4 resident session began after the completed SLURP null/logprob attempts.
   Decision 13-K requires same-process pairing where possible and an appropriate same-day,
   same-process replicate margin otherwise. Identify the existing evidence satisfying it.
5. The Sep-5 program's older SLURP intent comparator differs from the latest projected-v2
   comparator. The latest own-null verdict anchors the applicable numbers; do not mix score versions.
6. Audio2Tool's 16-kHz smoke has an attach-only attempt directory with no observed sealed manifest
   while its exposure row remains unconsumed. Record Fable5.1's explanation and verify accounting
   before attempting recovery. Branches `wt/kus4` and `wt/lp2` may hold parallel work; a WSL
   `prunable` label on a Windows worktree path is not proof the worktree is absent. Never prune
   those worktrees as part of this handoff.

## Completion of this handoff phase

- [x] Read current experiment designs, recent verdicts and operational metadata independently.
- [x] Identify the current queue, stale statements and unresolved readiness dependencies.
- [x] Provide a request, reply template, one-writer protocol and machine-readable exchange state.
- [x] Validate the checker and the handoff files; record a metadata-only check receipt.
- [ ] Receive Fable5.1's completed reply, including explicit execution/session ownership.
- [ ] Reconcile and acknowledge the reply; refresh canonical routing; select the next ready action.
- [ ] Take over actual experiment execution through the existing registered harness.

Files added by this handoff initially make the working tree dirty. Do not mistake that for a
pre-existing experiment modification. Commit only the verified handoff-owned paths, with unrelated
work preserved, before any clean-tree flight gate is attempted. No Git push or remote publication
is part of this handoff.

Validation: 11 synthetic checker tests passed in WSL Python 3.12.3; Ruff passed. The actual
exchange reports `WAITING_FOR_REPLY`. Engineering-base and harness-admission checks passed
(4 modules, 3 barred from default plans, 1 default plan). Every Markdown link in this directory
resolves locally and the authored documents contain no CJK text. See
[verification.json](../../../checks/speech-aware-evidence-acquisition/2026-09-09-fable51-codex-handoff/verification.json).
These are coordination/engineering checks, not new experimental measurements or permission to fly.
