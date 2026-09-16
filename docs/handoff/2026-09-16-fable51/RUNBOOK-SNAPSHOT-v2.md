# Operational handoff v2: closed campaign, resident service, prospective successor

This supersedes the old operations document's running-flight instructions.
The immutable [operating snapshot](OPERATING-SNAPSHOT-v2.json) was captured at
2026-09-16 18:48:12 UTC. Revalidate once on takeover; it is not perpetual liveness evidence.

## Paths

| Purpose | WSL path |
| --- | --- |
| Study canonical checkout | /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition |
| Umbrella | /mnt/d/chao_workspace/exploring-l4-intelligence |
| Dataset identity authority | /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json |
| DATA root | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data |
| Research Python | /home/chao/.venvs/speechrl/bin/python |
| SLURP prepared speech | /home/chao/feat-cache/slurp-q4km-packets-04ccc72a |
| Candidate-view implementation | /home/chao/saea-worktrees/candidate-bound-slot-view-v1 |
| Closed flight's frozen code | /home/chao/saea-worktrees/slurp-typed-context-full-recovery-v1 |

All execution is in Ubuntu-24.04. Set an absolute PYTHONPATH to the selected checkout's
src directory and PYTHONDONTWRITEBYTECODE=1. Do not install another editable checkout
into the shared environment. The pinned official SLURP scorer remains separate.
Canonical branch is master; preserve unrelated untracked _tmp_slurp_gap_extract.py,
integration_native_finite.py and wsl$/. No push is implied.

## Exact operating state at capture

- Decoder PID 364846, process start_ticks 9575036, alive.
- Monitor PID 364981, process start_ticks 9581534, alive; existing ten-second telemetry.
- Old campaign PID 425664 absent; its durable closure receipt is present and hash-bound.
- Session: serving-slurp-native-candidate-five-train-a-np4-v1.
- Decoder-only, --no-mmproj, context 98,304, four slots (24,576 each), Q4_K_M core,
  q8_0 key/value cache, flash attention, batch 2,048 and microbatch 512.
- Snapshot GPU utilization 0%; memory 22,976 / 24,463 MiB.
- No Fable5.1 takeover receipt was found.

No restart, stop, memory release, lease mutation or generation was performed for this
handoff. Check process identity plus durable state, not PID existence or an old JSON alone.
The snapshot does not substitute for full weight/build/cache/service identity validation
before a new admitted contact. Do not change power settings; the owner settled them.

The named service is idle, not proof that any new flight is READY. Do not load a second
server or infer permission from available memory. A successor needs its own exact
source/preparation/config/ExecutionPlan/exposure bindings and root-owned exclusive lease.

## Closed flight and unread direct source

Closed run:
SAEA-SLURP-NATIVE-TYPED-ROLE-CONTEXT-TRAIN-FOLD-A-RECOVERY-V1.

Closed attempt:
attempt-slurp-native-typed-role-context-train-fold-a-recovery-generation-v1.

Frozen commit: 9bf27b28708bb93607138e7bcd1eacb66eab3f08.
State: CLOSED_SECOND_FAILURE_NO_FURTHER_RECOVERY.
Closure: DATA/coordination/slurp-typed-context-vs-direct-v1/root-system-recovery-closure-v1.json.
The snapshot records its hash. Read [terminal details](TERMINAL-UPDATE-20260916.md).
Do not resume, change this worktree, score partial rows, splice results or activate its replica.

Direct run: SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1.
Attempt: attempt-slurp-direct-max512-train-fold-a-source-recovery-generation-v1.
State: FINALIZED, 1,080 rows and first complete official score; task quality unread.
Generation commit: f3189ce2667a45b1c0c9633e510747ae914118bd.

Under DATA/runs/<run>/<attempt>/:
- Generation manifest hash: 5219d078dae949fede1f8cd72832ffdbf26b9e2205fd7873e4e7bf631e56b534.
- First score hash: 7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38.

These identities are provided to prevent rerun/read mistakes, not to authorize quality
release. The old postseal analysis templates and matched replica are now ineligible.
Do not tail old campaign logs or inspect answer/gold text to reconstruct progress.

## First takeover actions

1. Read HANDOFF.md and the two v2 research documents.
2. Check shared coordination state and whether another coordinator is active.
3. Verify current Git branches/commits, the closed attempt and actual service/lease ownership.
   Preserve a live lock guard and another owner's credential; do not delete lock files.
4. Create TAKEOVER-FABLE51-<UTC>.md with the observed identities, ownership and selected
   next action. Only then reconcile the legacy coordination contract explicitly before updating its owner fields.
5. Review implementation acceptance and the held proof configuration. Finalize a fresh
   plan before contacting generation, tokenizer/FIT or speech tools.

Use the existing read-only coordination checker from the canonical checkout:
    /home/chao/.venvs/speechrl/bin/python -B scripts/checks/experiment_handoff_check.py

Its launch_allowed=false states that the checker does not grant a launch. Per-flight gates
remain authoritative. Do not bypass them with a private script.

The legacy checker currently pins coordinator/execution_owner to Codex in its
owner_directed_execution mode and validates the older OWNER-CONTINUATION-002 markers.
A Fable5.1 receipt must therefore be additive first. Do not merely replace those fields
or fabricate the historical unavailable reply. Reconcile a new takeover state/contract and
its checker support as an explicit ownership change; model-contact gates stay intact.

Shared entry surfaces are core.flight.cli, core.flight.lease_cli, core.flight.campaign,
core.session.worker and core.driver.cli under speech_aware_evidence_acquisition; inspect
their local help and a qualified current plan before use.
This document deliberately does not offer a runnable GPU command with incomplete bindings.

## Efficient work after takeover

Prepare the next qualified configuration/source/materials on CPU while the current flight
generates; no more than eight CPU preparation workers total during generation, 20 while idle.
One official complete scoring job can overlap the next scientifically eligible flight.
One root-owned service and one generation flight remain the rule.

Use lightweight event-driven metadata observation. Report terminal, failure or lack of
progress rather than frequent unchanged root scans. A generation-contact count is not a
completed-sample count. Tokenization/FIT is registered contact, not a progress probe.

Log all contacts and failed attempts. Keep raw/model artifacts in DATA, not Git.
Preserve frozen source until its scoring/analysis obligations close. Stop rather than
automatically replay after a service crash or capacity failure.
