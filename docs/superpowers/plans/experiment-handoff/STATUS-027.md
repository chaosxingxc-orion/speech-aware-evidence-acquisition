# Status 027: bounded Planner implemented while E21 generation continues

Date: 2026-09-11 UTC. Supersedes STATUS-026 for current implementation and
routing. Preserve the earlier snapshots and every scientific verdict.

OWNER-DATASET-TASKS-010 remains the latest scope instruction: summaries are
feasibility only and existing dataset tasks govern evaluation. E21/E22 do not
gain a summary task or evaluator through this implementation.

## GPU work

Root observed the resident service healthy at 2026-09-11T02:03:01.046761+00:00:
850 cumulative generation requests, 27 written call rows, no sealed manifest.
This is an operational snapshot, not completed-window coverage or a quality
read. Generation remains on b4d30c0f, service source remains 7a991a9c, and
serving-e21-offline-direct-repair-np4-v1 remains c36864/np4/max1024 with formal
precomputed packets and no resident mmproj.

Revalidate PID1675/session51412 (worker), PID1354 (server), PID637/session95670
(coordinator) and PID1641/session33752 (generation lease) before acting. Root
must not restart or replay because a tool observation times out.

Next scientific action is unchanged: seal and verify the direct parent, bind
all 1593 fresh windows through bind_window_predecessor.py before quality reads,
materialize the frozen KC-E1f repair configuration, fit its actual full requests
under a root prompt-fit lease, then run repair on the same resident service.
Use the existing repair handoff and corrected score-comparison preparation v2.
Whole-call PERSON and the frozen guards are authoritative; window attribution
is secondary and must reconstruct whole-call aggregates exactly.

## Shared implementation

Root implemented phase_planner in an isolated WSL worktree. A typed review
can now stop or continue a declared phase through the same shared controller
and OpenJiuwen executor. Missing configuration preserves previous behavior;
the new optional program has a distinct identity. Actual fitting follows
the derived active roster while retaining the registered budget ceiling.
The wire check distinguishes maximum and realized contacts, and shared review
records no longer duplicate across separate phase waves.

See [the bounded Planner note](../../../readiness/2026-09-11-bounded-phase-planner.md)
for configuration, evidence and limits. The main targeted suite passed 296
tests; additional controller/base/judge/fit checks passed 142 tests.
The new module measured 93 percent branch-aware coverage; source lint passed.
Tests and synthetic execution consumed zero neural contacts.

This closes the generic review-to-bounded-phase-decision implementation gap.
It does not close live E21 selection or new observation. The direct-only
window bridge still refuses this configuration, and no scientific flight was
added or changed. The next observation implementation must stay on the same
base and count selected-cut preparation, fits and all model stages.

KV, KU-S3, S4N, DR, LOOP and G6 SLURP decisions remain unchanged. G3/G4 stay
held. New E22 GPU flights stay outside the queue. The overall goal is active.
