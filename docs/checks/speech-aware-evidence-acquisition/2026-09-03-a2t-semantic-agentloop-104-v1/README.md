# Audio2Tool semantic AgentLoop 104-row launcher skeleton

Status: `PREFLIGHT_ONLY_NO_CONTACT`.

This check directory contains a fail-closed launcher skeleton for the fresh
104-row Audio2Tool discovery roster. It does not authorize or perform model,
embedding-tool, tokenizer, network, or scorer contact. It does not read gold.
The exposure ledger is intentionally unchanged.

The frozen phase order is:

1. 104 single-call M0 requests.
2. 104 single-contact semantic OBS requests through the existing OpenJiuwen
   AgentLoop runner.
3. A separate local Qwen3-Embedding-0.6B Q8 service window: embed the 104
   transcripts and 104 retrieval queries in physical batches of 32, yielding
   seven physical requests. Rank the complete tool registry independently for
   both views, fuse the complete rankings with RRF constant 60, and retain the
   top 16 tools.
4. 104 single-contact matched USE requests with per-sample selected-tool
   decision cards and response schemas.
5. 104 single-contact same-tier, same-card-count deranged USE requests.

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
all four prediction surfaces seal.

Run the no-contact preflight from the repository root:

```text
python docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-semantic-agentloop-104-v1/launcher/launch_semantic_agentloop_104.py --preflight-only
```

The report mechanically exposes the config and protocol hashes and lists every
unresolved governed hash. A final authority-binding launcher must supply all of
those exact hashes and a validated structured `ExecutionPlan` before exposing
an execution path.
