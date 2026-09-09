# Owner-directed experiment recovery

Decision ID: OWNER-RECOVERY-001
Request ID: SAEA-HANDOFF-20260909-01
Owner decision: AUTHORIZE_RECOVERY
Execution owner: Codex
Scope: RECONSTRUCTION_AND_MERGE_ONLY
Launch allowed: false

Recorded: 2026-09-09. This record supersedes the requirement to wait for a Fable5.1
reply in generation 1 of the handoff state. It records a direction from the owner,
not a release from Fable5.1. No Fable5.1 response or release has been received.

## Owner instructions and provenance

The owner supplied these two follow-up messages in the current Codex conversation,
after requesting a local-file handoff. Faithful English translations, in chronological
order, supplied by the coordinating Codex task:

1. "Fable5.1 has exhausted its weekly quota and cannot reply to you. Now only you and I
   can reconstruct its work."
2. "What matters is using the GitHub commit history and unmerged worktrees to organize
   the work plan and approach, and merging some already-completed work into main."

Source: the two owner messages immediately following the file-handoff request in the
current Codex task. The original messages remain in the conversation; they are not
copied into model-facing repository documents. No wording from Fable5.1 is attributed
to this decision.

## Authorized recovery

Codex takes responsibility for reconstructing the experiment family with the owner.
Prioritize GitHub commit history, retrieved Git references, unmerged branches and local
worktrees. Identify completed work, preserve unfinished changes, recover the existing
results ledger, organize the work plan, run appropriate model-free checks, and merge
verified completed work into the repository's actual default branch, `master`.

At the reconstruction baseline, `master` is
`2afb4b5cdc33f13a73a9b5d11a246f9a6858868b`; the retrieved `origin/master` reference is
980 commits behind. This is a recorded Git snapshot, not evidence that the remote has
received the local work. Refresh Git evidence as recovery proceeds.

The latest metadata-only recovery audit reported no active experiment process and
seven KV arms already finalized and scored at the reconstruction baseline, awaiting
scientific closure. Treat those as completed contacts to reconcile, not experiments
to rerun automatically. Scientific verdicts must follow their registered rules and
sealed evidence; this coordination record supplies no new result or admission.

## Boundaries and preserved records

Keep `REQUEST-001.md`, `RESPONSE-001.md`, and the original handoff check receipts
unchanged. An unavailable reply is neither a completed reply nor an inferred release.
The owner's explicit takeover direction replaces waiting for that reply.

This phase covers reconstruction and merging. It does not authorize a new experiment,
server action, model/tool contact, re-registration, rerun, revised scientific gate, or
publication. Existing execution contracts, exposure registration, budget checks,
attempt accounting and runtime locks remain in force. The handoff checker only
validates this local record; it never grants experiment execution.

Codex owns the recovery state and records subsequent decisions explicitly. When
recovering worktrees, preserve uncommitted files and Windows worktree registrations;
a WSL `prunable` label alone is not evidence that a worktree can be removed.
