# Native replication stopped at the configured revision limit

Root finding recorded on September 13, 2026. This supersedes the live progress
claim in STATUS-079. It does not change any original output, score, verdict,
replication configuration or active-runtime code.

The direct replication completed 1,000 responses and its first complete official
score exists. Quality has not been read. The native replication stopped after
1,329 model contacts and 3,595.7754375 seconds of repeated speech input. Those
counts are consumed contacts, not completed answers. The campaign exited with
code 1 and NativeEpisodeError: episode revision limit is exhausted.
The system attempt is now ABORTED and is not scored as a partial population.

## Named cause and closure

reproduction.ojw.native_episode._Exhausted raises when the final Planner returns
REVISE or ACQUIRE after the one allowed revision. Only explicit ACCEPT may bind
an answer under the frozen v1 configuration. This behavior is intentional in its
existing unit test, but is unsuitable for a system required to finish the entire
roster. The Planner already receives a prompt saying that only ACCEPT is available
at the terminal step; a prompt is not an enforced stopping policy.

The shared campaign omitted attempt abort on its exception path. Root verified
that worker PID 27240 no longer existed, no TCP connection to port 8080 remained,
the generation kernel lock was free, and three consecutive monitor samples showed
zero busy slots with the same request count. Root archived the old lease,
closed the opened attempt using the existing abort API, and reconciled lease
metadata. The root service PID 756 and monitor PID 961 remain resident.
This closure added zero model/tool contacts.

Source receipts under SPEECHRL_DATA_DIR/coordination/slurp-direct-vs-native-system-dev1000-replication-v1:

- failure-quiescence-v1.json
- failure-attempt-closure-v1.json:
  SHA256 221c1d2391a4498089dcf6531872530e15b000cd9ba6c389c6a447a7f1007e77
- failure-fit-closure-v1.json: 1329 request-fit receipts and
  5316 endpoint contact rows, all retained; no allocation may be reused.
- failed-flight-lease-v1.json and campaign.log are retained outside Git.

The failed runtime stays frozen at 532d8788a3cedca45fd9b81bde81b08fad4a22ec.
The incomplete system trace remains diagnostic failure evidence. Do not manufacture
a task manifest, deliver an old Solver response retroactively, or score its partial
roster. The original complete pair remains exploratory evidence, not a successful
replication.

## Prospective root decision

Use the owner-authorized progressive-system route and register at most one recovery
with an explicit deliver-latest-solver exhaustion policy. Keep the legacy default
raise unchanged. At the registered revision limit, a REVISE or ACQUIRE result may
end with the latest eligible Solver response, unchanged, with an explicit
revision-limit disposition and planner_accepted=false. Do not write an accepted
Solver receipt for that path. Invalid Solver sources and unrelated integrity
failures remain fatal.

Test the real shared graph, source custody, final bundle conversion and diagnostic
reader with synthetic episodes before admission. Preserve every completed call and
report the terminal-stop count and quality separately while retaining all 1,000
rows in the primary comparison. The change adds no model calls within an episode.

If verified, run one complete new system setting on the existing roster against
the already completed direct replication in the same resident process. Register
fresh generation and actual-request-fit identities. The comparison is the revised
complete system versus direct answering, not an exact v1 replication. A second
failed recovery stops this flight. Intent-boundary supply remains the next separate
capability after this root-caused predecessor closes; do not combine it into the
recovery or switch the current service for encoding yet.
