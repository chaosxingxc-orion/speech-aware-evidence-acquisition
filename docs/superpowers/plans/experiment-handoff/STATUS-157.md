# STATUS-157: postseal provenance complete; full system recovery remains live

Date: 2026-09-16. Supersede STATUS-156. Root owns scientific decisions.

## New completed work

Known postseal provenance is now bound in a separate metadata-only receipt. Root verified
42 file bindings, including both clean frozen source checkouts, registered plans/protocols,
model/dataset fragments, ordered roster bytes, unchanged direct artifact hashes, and all
12 existing analysis implementation pins. No task scores, answers or references were parsed.

Read docs/readiness/2026-09-16-slurp-postseal-source-bindings-v1.md.
The data receipt is coordination/slurp-typed-context-vs-direct-v1/postseal-preparation/
source-bindings-known-system-recovery-v1.json, SHA-256
d5d689b0ee5093a9da0d8de2b5fd71181c09b5b5103beb9e5d52bc0e2993287c.

The bounded compatibility audit identified a required orchestration step:
verify_native_episode_source builds generic diagnostics but does not invoke the
rejection-aware native_tool_exposure audit. Explicitly call
analyze_verified_native_tool_exposure with the verified source before reporting tool
behavior. It preserves rejected calls and excludes them from successful acquisitions.
Root checked these code paths. No runtime edits or additional tests were needed.

Compatibility receipt: postseal-preparation/analysis-api-compatibility-v1.json under the
same coordination directory, SHA-256
0b0974e7d0cee3249e24e06d51a0bebff3b28b9d6344c7dfd02fd4f7b1c74819.

## Verified execution state

At 2026-09-16T12:20:00.963757Z, campaign PID425664 had the exact expected command line,
and root exec34947 was still running. No terminal receipt existed. The latest service
sample at12:19:52Z reported GPU99%, four busy slots, memory22976MiB and a healthy server.
Do not infer completed sample count from service requests or model contacts.

The live source remains frozen9bf27b28708bb93607138e7bcd1eacb66eab3f08 at
/home/chao/saea-worktrees/slurp-typed-context-full-recovery-v1.
The direct source remains frozenf3189ce2667a45b1c0c9633e510747ae914118bd.
No service restart, geometry change, model contact, scorer call or runtime source edit
was introduced by this preparation work.

The lightweight observer's watcher PID425824 was verified live. Its tool session40733
is owned by the observer agent and is not accessible from root. The observer was instructed
to await its own existing watcher and notify meaningful transitions. Original expiry is
approximately12:56Z; expiration is not campaign failure. Root retains campaign handle34947.

## Next action

Wait on the confirmed live campaign. Do not expand preparation or introduce another
mechanism. System future artifacts and the paired root quality release remain unresolved.
After complete system sealing and its first official score, verify both complete sources,
record paired release, bind fresh analysis copies and execute the shared analysis sequence,
including the separate tool-exposure audit. Root then attributes full-task gains/losses and
decides replication or one named successor. Never rerun the already completed direct score.

The sole system recovery failure policy remains unchanged. Preserve and close on a second
failure; no automatic replay, prefix splice or third attempt. SLURP is the sole active carrier.
