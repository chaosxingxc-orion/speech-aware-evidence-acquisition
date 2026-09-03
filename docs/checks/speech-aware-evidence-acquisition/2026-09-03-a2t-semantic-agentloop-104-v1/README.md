# Audio2Tool semantic AgentLoop 104-row contact-ready coordinator

Status: `CONTACT_READY_RUNTIME_FACTORY_REQUIRED_NOT_EXECUTED`.

This check directory contains a fail-closed launcher coordinator for the fresh
104-row Audio2Tool discovery roster. It does not authorize or perform model,
embedding-tool, tokenizer, network, or scorer contact. It does not read gold.
The exposure ledger is intentionally unchanged.

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
renderer and differ only in ranking source. Trace material preserves the
complete transcript, model-query, and RRF-fused rankings. It supports required
tool-ranking ceilings and does not claim unproduced skeleton/action-set ceilings.

Generation uses two slots and queue depth four. The service geometry is 65,536
total context tokens with two physical 32,768-token slots. Immediately before
each generation send, the exact assembled messages and that sample's response
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
intervals for query minus transcript, fused minus transcript, fused minus
query, fused minus M0, and fused minus shuffled. Exact and tool contrasts also
receive exact paired sign tests.

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
unresolved governed hash. `--execute` exists but fails closed unless a separately
authored, command-line-hash-pinned authority document supplies six ordered
structured discovery `ExecutionPlan` objects and a local runtime factory. The
runtime factory remains a prerequisite: it must construct and start/stop the
pinned local generation and embedding services, adapters, clients, trace sinks,
and bundle sealers. Therefore this file alone is not yet a direct service
launcher. No authority, preregistration, ledger entry, runtime receipt, model
contact, embedding contact, tokenizer contact, network contact, or scorer
contact was created during this revision.
