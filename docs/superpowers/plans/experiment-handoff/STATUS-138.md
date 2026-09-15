# STATUS-138: SLURP TRAIN-A is running; Audio2Tool registration is frozen

Date: 2026-09-15. The SLURP broad/factored TRAIN-A campaign is running from
frozen source 0bede772c27688c29999798e5fc945035a10b805. Its sole service is
serving-slurp-native-broad-factored-train-a-np4-v1, with geometry
4x24576, max512 and no-mmproj.

The last bounded observer milestone recorded 1,009 model calls. Process 293426
was live and the attempt was OPENED at that milestone. The call count is not a
completed-row count and does not establish campaign completion. Shared
10-second telemetry began at 17:11:58 UTC, so the earlier interval is missing.
Later snapshots recorded 91--99% GPU utilization and as many as four busy
slots. The current campaign alone owns the first full official score.
Paired quality remains unread.

The [post-seal analysis recipe](../../../readiness/2026-09-15-slurp-broad-factored-train-a-analysis-recipe-v1.json)
is copied byte-for-byte from DATA/coordination/slurp-broad-factored-v1/
postseal-analysis-recipe-v1.json with SHA-256
b2dcc443d5c349460032663ab0547658a35a5cb38c84dd2cb7db564264348e90.
It is a source-binding recipe pending a complete seal and makes no new
statistical choices.

The Audio2Tool direct/system scope-tools pair is root-reviewed, registered,
integrated and source-frozen at
219e305f306f11998e39c44b5fb055b4fcfb3179. Its source-freeze receipt at
DATA/coordination/a2t-scope-tools-registration-v1/source-freeze-v1.json has
SHA-256 5f6fe9953feaf0d7cdd3c2ffff2dc6344a693fa2d38545b3ab843d091bf39959
and covers all 5,714 tracked files. The root review has SHA-256
a4eabc45ad36288ed82fc8c80ac026aec9bdc5ac393fb41f10da2e193b48ea98;
the admission at DATA/coordination/a2t-scope-tools-registration-v1/
admission-v1.json has SHA-256
825ad8ccd90e91a448b8938e13e46e674364cbdc9d49be874762935dd66de5c6.
Its 81 focused tests and root's independent four-plan binding checks passed
without a new GPU contact. It awaits the SLURP generation boundary and its
exact np3 service, not more engineering.

The Earnings21 held registration preparation is root-reviewed and merged at
7861546dea74d9099030c0e39fae4ed59d9e88ea. Preparation source
64ff6fe6c744285b48d3a4454be2e74ff11b2431 includes the corrected README
ordering. Its root review receipt is
DATA/coordination/e21-native-window-registration-prepare-v1/root-review-v1.json
with SHA-256
3b3461b9ed41dd3b85e3b7dcaf88298c586a279113b001615662103ea909bb81.
The new configs, draft plans and held campaign grant no admission, exposure,
fit or generation authority. Retain the supported static fit over 1,593 windows
and 4,780 endpoints: the live fit counts 44 parents and is not unit-aware, so no
production change is needed.

The active order is SLURP, Audio2Tool, then Earnings21. The owner GPU resume
remains in force. The coordination checker retains launch_allowed=false because
it never grants launches; each registered execution plan remains authoritative.
Preserve all historical failed verdicts and records. Stable
benefit and trajectory-sampling optimization remain incomplete. This
documentation performed no inference, outcome read, service operation, scoring
or statistical interpretation.
