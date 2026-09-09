# Owner-directed recovery and continuation plan

Role: engineering plan. Coordinator: Codex. Updated: 2026-09-09.
The owner directed recovery from GitHub history and unmerged worktrees after Fable5.1 exhausted
its weekly allowance. The current task is to recover and merge completed work, then continue from
the actual experiment state. The former request/reply exchange is historical; no Fable reply is required.

## Git history and merge decisions

GitHub's actual default branch is **master**, which is what the owner's "main" refers to here.
At the recovery fetch, `origin/master` was `0b7e1626` (2026-08-25), with no open pull requests.
Local master `2afb4b5c` had **980 commits not on origin**. The September work is therefore
recoverable from local Git and worktrees, not from the remote history alone. No remote ref was
changed in this recovery; local integration and publication of the large remote backlog are distinct actions.

| Work recovered | Evidence / branch tip | Integration outcome |
|---|---|---|
| Audio2Tool D1 declarations and seal/scoring consistency | `wt/a2t-d1fix`, `wt/a2t-scorer`, included in `wt/wave9` | Merged |
| Existing Stage-2 results ledger and executable consistency checker | `wt/results-ledger`, included in `wt/wave9` | Merged; refresh current statuses in place |
| LP-2 label-token confidence successor | `wt/lp2`, included in `wt/wave9` | Preparation merged; not a flight GO or admitted module |
| KU-S4 candidate narrowing and exemplar-family preparation | `wt/kus4`, included in `wt/wave9` | Preparation merged; exemplar packet promotion still outstanding |
| Review fix for the shared cleanliness check | `33e8c831` on `wt/wave9` | Merged; protects unstaged code edits, both rename endpoints and untracked protected files |
| Exact-arithmetic KU-S3 vector-norm cache and live digest update | `wt/kus3seed` at `4279a314` | Merged by `db1e86f7`; frozen historical digest unchanged |
| Worktree-aware Audio2Tool preprocessing and consumed-run refusal classification | Recovered five-file patch, `wt/a2tgq` at `73a55f63` | Merged by `d1c15c29`; receipts preserved |
| Owner-directed recovery and executable file coordination | `codex/owner-recovery` at `6771fea2` | Merged by `557e6f10`; no Fable reply or release fabricated |

Wave 9 was already a clean integration of four lines, 22 commits ahead of the starting master.
It was fast-forwarded only after the discovered cleanliness defect was fixed and tested. No
cherry-pick reconstruction or history rewrite was needed. The two additional branch merges were
conflict-free. Existing Git author configuration was retained; original authorship was not invented.

## What the completed experiments require next

The seven KV cells **already flew and were scored** under `2afb4b5c`: one finalized attempt and
one successful complete-manifest scoring job per cell, 7,000 metered contacts total. Their current
scientific status is **pending read/verdict**, not "unflown". The server stopped normally at
10:52 UTC and no experimental process or flight lock was present in the 10:55 audit.
Evidence: [runtime snapshot](../../../checks/speech-aware-evidence-acquisition/2026-09-09-owner-recovery/runtime-snapshot.json).

Do not re-fly, re-score or edit these sealed artifacts to reconstruct their history. The registered
exposure rows still say `consumed=no`; the main checkout lacks KV-0's prerequisite decision before
its successors. Locate any missing read/decision artifact first. If none exists, record the sequence
deviation explicitly. The preparation's NEW500/per-row decision and the null's pooled
DEV1000/speaker-clustered measurements must not be silently substituted for one another after
treatment results exist. Any unresolved analysis must remain descriptive until its authority is settled.

## Ordered work queue

| Priority | Action | Completion criterion / prerequisite |
|---|---|---|
| P0, completed | Merge finished engineering and preserve unfinished work | Selected branches integrated; focused regression and contract checks passed; unfinished work remains isolated |
| P0, completed | Recover current results routing and ownership | Existing results ledger refreshed to 53 rows, current completed/pending distinction, Codex/owner recovery generation 3; no waiting for Fable |
| P1 | Close KV operational accounting and scientific read | Register a model-free read before new result inspection; verify existing manifests/hashes and one-pass scores; locate prior decision or record deviation; preserve original thresholds and clearly label unresolved estimator/process issues |
| P2 | Complete KU-S3 preparation, execute under its registered gates, and close its verdict before KU-S4N | Reuse the sealed predecessors and vector bindings; validate the existing seed plan; keep the preregistered baseline/view comparisons and one-flight rule. Owner Decision 13-M orders KV -> KU-S3 -> KU-S4N |
| P2, CPU lane | Review and test the existing KU-S4 exemplar-packet worktree | Review/test the seven untracked files and prepare the dry-run/promotion registration now. Produce and pin the missing packets only after KU-S4N is ADMITTED or NEUTRAL, as KU-S4 preregistration section 11 step 9 requires |
| P3 | Execute KU-S4N and its twin when dependencies are ready | Exact registered plans, fit/smoke gates and predecessor decisions; then same-speaker/other-speaker/text controls only after their packet and decision gates |
| P4 | KC-S1b same-roster replication and module consolidation | Follow the recorded SLURP queue; defaults and candidate freeze still wait for KV/KU-S4 |
| P5 | E21 DR-1c -> DR-1f -> DR-1s -> LOOP-1 -> depth-2 dispatcher | Resolve preparation-only wording versus later ordering authority; fit and register each cell before contact; OBS-E1b stays prepared/unflown |
| Separate decision | LP-2 confidence successor / enhancement / further EVO rounds | Merged preparation is not execution authorization; no silent promotion of a failed primary's post-hoc diagnostic |

This is the recovery order, not a new scientific preregistration. The controlling experiment order
remains umbrella `wiki/experiments/speech-aware-evidence-acquisition/2026-09-07-owner-go-stage2-cells-and-foundation-fixes.md`,
Decisions 13-14, with the owner changes recorded in the recovery file. Maintain the same frozen
core, shared harness, information boundaries, zero paid API spend and Stage-2 stop line.

## Work preserved outside main

| Worktree / branch | State at audit | Disposition |
|---|---|---|
| `D:/chao_workspace/saea-worktrees/wt-kus4pk` | Seven untracked files: packet driver/test, dataset/experiment fragments and three receipt/roster products. Metadata union: 7,489 recordings, 440 already promoted and 7,049 cold. No completed promotion receipt or dedicated promotion exposure row | Preserve in place; next bounded implementation task. Its KU-S4 design dependency is now merged |
| `codex/stage2-speech-native-agentloop` | Older Aug-30 branch, 143 branch-only commits versus 980 main-only at the initial audit; five dirty code/test files | Preserve; do not merge wholesale into the September base. Revisit only a named missing capability |
| `staged/a2t-item-functions-cell` | Historical withdrawn cell; per-item schema contradicted the official protocol | Keep parked |
| `staged/select-fill-factorial-128` | Historical parked/unauthorized cell | Keep parked |
| `wsl-sync/master` | Historical Aug-22 divergence | Keep as provenance, not a September integration source |

All other current unmerged worktree branch tips found in the audit were ancestors of the recovered
Wave 9 tip, apart from the separately merged KU-S3 cache. A WSL "prunable" label on a Windows
worktree path is a path-format artifact, not permission to delete the worktree. No worktree was pruned.

## Validation and operating limits

Validation is recorded in the [integration receipt](../../../checks/speech-aware-evidence-acquisition/2026-09-09-owner-recovery/integration-verification.json). The merge review found and fixed a
real defect before integration; it did not treat historical green checks as sufficient. A dirty-tree
scorer refusal during concurrent editing was expected and passed when rerun on the committed tree.
One contract test initially lacked the venv's `python` on its child shell PATH and passed after
the documented environment was activated. Neither incident required weakening a check.

Scientific results remain in [the existing results ledger](../../../results/stage2-results-ledger.md)
and their cited original verdicts. This plan owns next actions and integration status only. A
successful merge or checker result does not authorize a new experimental contact. Before the next
flight, refresh actual runtime/attempt state, honor the execution plan and exposure gates, and keep
one coordinator and one experiment in flight.
