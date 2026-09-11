# Status 032: E21 generation sealed; CPU analysis released; GPU dispatch paused

Date: 2026-09-11 UTC. This goal turn made progress: the current E21 repair
finished, root verified its complete seal and fresh-parent lineage, closed its
external costs, released its experiment lease, and preregistered/released the
fixed CPU-only scoring and analysis. The full research goal remains incomplete.

## Complete E21 repair

The worker in tool session 99977 exited with code zero. The verified manifest is
COMPLETED and contains 44 calls, 1593 terminal windows, 1593 wire responses and
1593 charged generations. Its SHA-256 is
6086119a9a974393ba9b9ad6765041a347ddb3b3c1a153a60a5399ff2176b28d.

Common verify_bundle passes. Root additionally matched every predecessor window
ID, text hash, ordinal and audio range against the newly sealed direct-parent
snapshot. All1593 match. One window reached the output cap and none was skipped;
retain the frozen saturation/fallback behavior. The source remains clean at
/home/chao/saea-worktrees/e21-offline-repair-generation,
commit64440737a401b80805cfdd4f09d5a04748a3aad7.

Seal receipt: DATA coordination/e21-offline-kc-e1f-repair-generation-seal-v1.json,
SHA-25694abe61bd1c0ea0fbcea5b617c253e788ca8358d1557985171c9e757733edc33.

## Closed generation costs

Repair utilization-integrated GPU time is1.2582756753040685 hours, below its
registered2.0-hour ceiling. Energy is0.1986948864272039 kWh over7953.895875692368
wall seconds with full monitor coverage and zero missing seconds. The method is
the established device-wide right-endpoint integral, capped at20seconds coverage
per sample; it is not exact model-kernel time.

There are1593 calls,141345.8526875 speech seconds,3544442 prompt tokens and
439863 completion tokens. Durable attempt usage agrees with the sealed manifest.
Raw model responses and all historical parent artifacts remain unchanged.

Cost receipt: DATA coordination/e21-offline-kc-e1f-repair-generation-external-cost-v1.json,
SHA-256544e32578c81bc67116ff4e0896409b696c76a97d33a208bf4bc33799c23d58c.
It pins an immutable monitor snapshot and immutable pre-settlement attempt
snapshot. The attach receipt changed normally on worker detach; the final cost
uses its terminal contact_window, not the earlier partial live receipt or
manifest-writing timestamp. Independent CPU verification rehashed all pinned
inputs and reproduced the integral, energy and full coverage; it passed without
a discrepancy.

## Service retained; no further GPU dispatch

Root lease session22105 returned worker-lease-released and exited zero.
Worker21509 and lease holder21472 are absent. Root coordinator637, server1354 and
monitor1389 remain alive. The post-release GPU sample was0% utilization,
19776MiB resident and5.82W. Revalidate these observations before later action.

Keep serving-e21-offline-direct-repair-np4-v1 and its monitor resident under
OWNER-GPU-PAUSE-012. Do not stop/unload or change profile proactively. All new
GPU generation, encoding, actual-fit/tokenizer checks and throughput experiments
remain paused until a new explicit owner instruction. The prepared SLURP
source, plans and artifacts stay intact and unexecuted.

## CPU scoring and analysis

Before any quality-result read, root appended exposure
SAEA-E21-MF-OFFLINE-PAIR-POSTSEAL-SCORE-READ-V1 and created DATA
coordination/e21-offline-pair-postseal-score-read-release-v1.json,
SHA-25602a5aaaba4fbf017050a178f0003951996c178d2a913ae81b8164c089f09500c.

The aligned_scoring_views agent started the direct complete score as the sole
scorer (PID33717, tool session57224); repair scoring remains next in sequence.
Its log is DATA coordination/e21-offline-direct-score-v1.log. Execute both scores sequentially through core.scoring_batch with max_workers1,
include_per_sample=True, operation score and explicit frozen ScoringContext.
Use source64440737 and the unchanged analysis plan
8b92393cb37632b7fc53fbb35686d0aef63f845b199bd5de39127e5702ccd5f5.
Then bind saved reader/comparator templates to actual output hashes and perform
the frozen whole-call primary/guard comparisons and valid window attribution.
Check the agent and actual job handles; delegation alone does not prove scores
started or completed.

Root retains the scientific verdict and attempt settlement. Do not finalize
before complete scores and reviewed comparisons. Do not read a positive result
into the seal or count generic Planner tests as live selective observation.
All previous held/rejected scientific decisions remain unchanged.
