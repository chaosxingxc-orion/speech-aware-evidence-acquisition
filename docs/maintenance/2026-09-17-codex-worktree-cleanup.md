# Codex temporary worktree cleanup

Completed: 2026-09-17T07:48:42.379774+00:00.
Authorization: the owner's request to clean Codex development worktrees, consistent with
Decision 10 in [the current owner decisions](../readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md).

Removed 219 stale directories under /home/chao/saea-worktrees. Their Git administration
entries were already absent. A complete archive was created and compared byte-for-byte
against the source directories before removal. The deletion pass rechecked path containment,
absence of nested mounts, registration and process references.

## Outcome

- Removed filesystem allocation: 52,379,549,696 bytes (52.38 GB).
- Recovery archive and accompanying records: approximately 9.99 GB.
- Estimated net space reclaimed inside WSL: 42,393,350,144 bytes (42.39 GB, 39.48 GiB).
- Retained /home/chao/saea-worktrees/fable-b0r-flight and the canonical master checkout.
- Retained all Git branches; 209 name-associated Codex branch tips were rechecked unchanged.
- Added zero model contacts; stopped or restarted zero services.

The remaining worktree parent contains only fable-b0r-flight. These figures describe WSL
filesystem space; this operation did not compact the host virtual-disk file.

## Recovery and provenance

Archive:
/home/chao/saea-archives/worktree-cleanup-2026-09-17-codex-v1/orphan-worktrees.tar.gz

Archive SHA-256:
0c7c433c85514ea4b2351f18dcb5f5e88d28727a3688ccea67af96875ddcdfed

The [machine-readable receipt](2026-09-17-codex-worktree-cleanup.json) records every removed
directory, retained branch associations, source receipt hashes and the registered worktrees
after cleanup. The same backup directory contains the plan, successful archive comparison
receipt and per-directory removal journal.

Uncommitted and untracked directory contents were preserved by the complete archive.
Archived .git marker files still refer to their old, already absent administration entries;
restore into a separate recovery location and reconcile Git registration if needed.
Branch-name associations do not assert exact historical checkout HEADs. Frozen experimental
results, weights, feature caches and the current Fable worktree were outside the removal set.
