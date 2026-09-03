# Audio2Tool semantic AgentLoop 104-row contact-ready coordinator

Status: `SCORED_ANALYZED_NO_SCALE`.

The one-shot flight completed all 624 generation calls and all 208 logical
embedding contacts. Final sealing failed after the first manifest was written
because the roster's colon-key integrity digest was not the canonical
carrier-prefixed split digest recomputed by `verify_bundle`. The zero-contact
recovery subsequently created six verified successor bundles without repeating
a model contact. Five complete answer manifests have now been scored and the
104-row post-seal analysis is complete.

This check directory contains the fail-closed launcher coordinator and the
zero-contact recovery for the fresh 104-row Audio2Tool discovery roster. The
separate generation and embedding-tool exposure rows were registered before
contact and are now fully consumed. Gold remained closed until all six
successor manifests verified.

The coordinator pins preprocessing report SHA-256
`32ec7ab4b93926f81a9f352e0dbcabf669f41eec23956e94f694c987d4a45950`
and speech-packet promotion receipt SHA-256
`6f5d77438b50ebba8130122c6cc39acff18f0707836c61e72a03f6af1380c6b5`.
The exact promoted packet-token distribution is min 26, median 65, p95 169,
and max 481. Dynamic request measurement uses each packet's recorded count.

The revised frozen phase order is:

1. 104 single-call M0 requests.
2. 104 single-contact semantic OBS requests through the existing OpenJiuwen
   AgentLoop runner.
3. A separate local Qwen3-Embedding-0.6B Q8 service window: embed the 104
   transcripts and 104 retrieval queries in physical batches of 32, yielding
   seven physical requests. Rank the complete tool registry independently for
   both views, fuse the complete rankings with RRF constant 60, and retain the
   top 16 tools.
4. 104 single-contact transcript-top-16 USE requests with per-sample
   selected-tool decision cards and response schemas.
5. 104 single-contact main-model-query-top-16 USE requests.
6. 104 single-contact RRF-fused-top-16 USE requests.
7. 104 single-contact same-tier, same-card-count deranged fused USE requests.

This is exactly 624 generation contacts. All matched arms use the same card
renderer and differ only in ranking source. The terminal sealing failure
occurred before the non-direct semantic sidecars were written, so the durable
traces preserve the selected per-arm evidence but not the in-memory complete
rankings. Post-seal analysis can therefore report top-16 required-tool
reachability from the selected evidence; it must mark unavailable any stronger
full-ranking, skeleton, or action-set ceiling that the durable bytes cannot
reconstruct.

Generation uses two slots and queue depth four. The service geometry is 65,536
total context tokens with two physical 32,768-token slots. Immediately before
each generation window, one local `/props` read binds that process's live media
marker and verifies its 32,768-token slot. Immediately before each generation
send, the exact assembled messages and that sample's response
format go to `/apply-template`; each non-speech prompt segment then goes to
`/tokenize`. The exact text count is added to that packet's recorded speech-token
count, a two-special-token reserve, and the request's completion ceiling. The send
is refused unless that complete required window is at most 24,576 tokens, leaving
an additional 8,192-token physical reserve. The transport wrapper has one send path and no
retry, fallback, repair, or prompt-level multi-sample batching.

Generation is split into pre-embedding and post-embedding service windows. A
state gate requires the first generation server to stop before the embedding
server starts, requires the embedding server to stop before the second
generation server starts, and requires all services to stop before sealing.
Gold and scorer access remain outside the skeleton and are allowed only after
all five scored call-output surfaces and the OBS diagnostic surface seal.
Each of those six phases must carry a distinct stopped-runtime receipt and a
complete 104-row manifest.

## Post-seal score and diagnostic contract

The five scored complete manifests are M0, transcript-top-16 USE,
main-model-query-top-16 USE, RRF-fused-top-16 USE, and same-stratum shuffled
fused USE. OBS remains a complete diagnostic manifest and is never a tool-call
score job. Submit each scored manifest as one whole-manifest official-scorer
job; outer parallelism may use at most four workers, but a manifest must never
be sharded or reconstructed from averaged shard metrics.

The no-contact reader reports per-tier official results and paired bootstrap
intervals for transcript minus M0, query minus transcript, fused minus
transcript, fused minus query, fused minus M0, and fused minus shuffled. Exact
and tool contrasts also receive exact paired sign tests.

OBS diagnostics always report transcript, main-model-query, and RRF-fused
top-16 tool-ranking reachability. Ordered-call-skeleton and
proposal-content/action-set ceilings are reported only when sealed trace
artifacts for every row and every diagnostic condition are supplied. Otherwise
they are explicitly `unavailable`; the reader never infers them from tool
rankings.

Run the no-contact preflight from the repository root:

```text
python docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-semantic-agentloop-104-v1/launcher/launch_semantic_agentloop_104.py --preflight-only
```

The report mechanically exposes the config and protocol hashes and lists every
unresolved governed hash. `--execute` fails closed unless a separately authored,
command-line-hash-pinned authority document supplies six ordered structured
discovery `ExecutionPlan` objects and selects
`launcher/local_runtime_factory.py:build_runtime`. That concrete WSL2 runtime
starts and stops two receipt-pinned generation sessions on port 8090 around one
receipt-pinned embedding session on port 8082; constructs the direct and
OpenJiuwen adapters, clients, and trace sinks; and seals six independently
verified complete manifests plus one flight receipt.

The generation and embedding-tool preregistration, exposure rows, standalone
embedding runtime receipt, frozen semantic runtime receipt, 1,095 tool-tier
centroids, and 43 aggregate compatibility rules now exist. The concrete runtime
loads only those hash-pinned label-free semantic assets; it cannot reopen the
construction rows, gold labels, source utterances, concrete argument values, or
reference transcripts. A one-facet inert external-governed snapshot satisfies
the generic AgentLoop runner contract but activates and supplies no evidence.
The model receives only the per-sample selected G5 decision cards rendered by
the semantic phase adapter.

The official outcome is recorded in `postseal-result-summary.json` and
`docs/readiness/2026-09-03-a2t-semantic-agentloop-104-v1-verdict.md`. Transcript
top-16 improved tool accuracy over direct M0 but did not establish stable exact
match superiority. Same-core query generation and RRF fusion did not improve
the transcript route. Matched evidence strongly beat the same-volume shuffled
control, while top-16 required-tool reachability remained 92/104. The current
method is therefore not promoted to approximately 1,000 samples; the next
104-row experiment redesigns knowledge supply and separates ordered tool
selection from parameter filling.
