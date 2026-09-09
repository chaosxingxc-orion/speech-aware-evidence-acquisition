# Owner-directed experiment recovery

Status: **owner-directed recovery**, generation 2. Codex is the recovery coordinator
and execution owner under [OWNER-RECOVERY-001.md](OWNER-RECOVERY-001.md). The current
phase permits reconstruction and merging; `launch_allowed` remains **false**.

The owner reports that Fable5.1 has exhausted its weekly quota and cannot reply.
The owner and Codex will reconstruct the work from GitHub history and unmerged
worktrees, organize the plan, and merge completed work into the default branch,
`master`. This direction replaces waiting for a response. It is not a Fable5.1 release.

## Recovery protocol

1. Inspect the current Git references, commit history and Windows worktree inventory.
   Preserve all uncommitted changes. Distinguish completed branches from unfinished
   work and explicitly parked historical experiments.
2. Recover existing artifacts before creating replacements, particularly the Stage-2
   results ledger and prepared integration branches. Use each branch's recorded
   decisions, receipts and tests to establish what is complete.
3. Test completed changes through the shared engineering base, then merge verified
   work serially into `master`. Keep ongoing work isolated and record remaining gaps.
4. Reconcile the exposure ledger, attempt metadata and scientific verdicts separately.
   The latest metadata audit reports **no active experiment** and **seven KV arms
   finalized and scored at `2afb4b5c`**, awaiting scientific closure. Do not rerun them
   merely because an older handoff note calls KV-0 the next flight.
5. Update this state after a durable coordination decision and increment its generation.
   Re-read live metadata before a later operational step. An idle process snapshot is
   not launch permission; the existing experiment contracts and runtime locks apply.

The detailed recovered inventory and work plan are maintained in
[RECOVERY-PLAN.md](RECOVERY-PLAN.md). This README defines coordination; it does not
replace the scientific results ledger or a preregistration.

## Local state check

Run the read-only checker at the start of a continuation:

```bash
python scripts/checks/experiment_handoff_check.py
```

Use WSL2 `Ubuntu-24.04` and the `~/.venvs/speechrl` environment. The checker reports
`OWNER_DIRECTED_RECOVERY` only when generation 2 or later records Codex ownership,
an unavailable reply, `launch_allowed: false`, and an explicit matching local owner
decision restricted to reconstruction and merging. A missing, conflicting or
malformed decision reports `INVALID`. The original `WAITING_FOR_REPLY` and
`REPLY_READY` states remain supported for an ordinary exchange.

The check reads coordination files and Git metadata only. It does not read experiment
outputs, contact a model or server, acquire a runtime lock, change state, or authorize
a flight. `execution_authority` remains `NOT_EVALUATED` in every report. There is no
background poller.

## Preserved exchange

[REQUEST-001.md](REQUEST-001.md) and [RESPONSE-001.md](RESPONSE-001.md) remain unchanged
as the original exchange, including the pending reply marker. Codex does not fill in
Fable5.1's reply or mark it complete. The original
[verification receipt](../../../checks/speech-aware-evidence-acquisition/2026-09-09-fable51-codex-handoff/verification.json)
records the earlier waiting phase and is preserved unchanged. Current phase and
ownership are recorded in [state.json](state.json) and the owner decision above.

All authored documents and coordination messages remain English. Dataset identity
still comes from the umbrella lock; discovery/confirmatory isolation, one experiment
in flight, zero paid API spend and the Stage-2 research boundary are unchanged.
