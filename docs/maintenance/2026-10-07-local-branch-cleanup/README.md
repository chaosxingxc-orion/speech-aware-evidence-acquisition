# Local branch integration and cleanup

The repository mainline and remote default are `master`. Preserve that name.

The inventory contains 728 original local branches. 147 divergent branch histories
were reconciled with the exact current tree retained: 146 have patch-equivalent
commits already on master, and the completion-budget branch produces an identical
three-way merged tree. This integration preserves original commits without replaying
old implementations over later fixes.

Two pending changes were merged normally: campaign CLI runtime/lock forwarding
coverage and bound abstention proposal validation. The historical CLI test double
was updated to implement the current prepared-artifact verification interface.
78 related unit tests pass.

23 non-equivalent historical branches remain preserved and unmerged. Their exact
commits, affected paths and reasons are in [audit.json](audit.json). Some contain
withdrawn experimental architectures or unregistered recovery/finite-action plans;
others overlap later implementations and require semantic reconciliation. This
cleanup does not claim that all historical code has been integrated.

Keep every checked-out branch and every frozen/detached worktree. Three WSL working
directories have existing uncommitted edits; retain them untouched. Windows reports
Linux paths as prunable, while WSL reports the Windows checkout similarly. Never
prune these cross-environment worktrees based on that flag.

The external coordination/local-branch-cleanup inventory retains all original branch
names and commit IDs, Windows and WSL worktree inventories, patch-equivalence results
and merge simulations. Final deletion receipts record only merged, unchecked-out
branch references removed with safe Git deletion. No experiment or scorer was run.

## Verified completion

Deleted680 merged inactive branch references with `git branch -d`, without force.
48 original branches remain: master,24 other checked-out branches, and23 preserved
non-equivalent historical branches. The temporary maintenance branch/worktree will
be removed after its final fast-forward integration. Every original nonmain worktree
retains its exact HEAD and branch attachment. Main is clean; engineering-base PASS
and78 related unit tests pass. No remote changes were made.
