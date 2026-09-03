# Audio2Tool Semantic AgentLoop 104-Row Flight — Preregistration

Status: **REGISTERED BEFORE ANY FLIGHT GENERATION, EMBEDDING, TOKENIZER, SCORER, OR GOLD CONTACT**  
Execution profile: `bounded-discovery-probe`  
Generation run: `SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1`  
Embedding-tool run: `SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1-EMBED`

## Scientific question

Test whether a frozen speech-capable core organized as an OpenJiuwen AgentLoop can outperform one
direct frozen-core call because it receives higher-value, sample-specific task information. Separate
four mechanisms rather than treating a larger prompt as an intervention:

1. Does a local frozen semantic encoder narrow 152 tools to a useful transcript-conditioned top 16?
2. Does the same frozen core add retrieval information by producing a tool-name-free desired-action
   query, while the local encoder and all downstream knowledge remain fixed?
3. Are transcript and desired-action rankings complementary under fixed RRF-60 fusion?
4. Does the recipient sample's fused evidence outperform the same amount of evidence taken from a
   different sample in the same difficulty tier?

This is an engineering-baseline discovery flight. Task performance above 0.90 is not an admission
condition. The greater-than-0.90 target applies after a later, separately registered training-free RL
stage. This flight contains no policy fitting and creates no test-set tuning authority.

## Frozen population and isolation

Use exactly the 104 discovery samples in `A2T-AGENTLOOP-FRESH-FLIGHT`: 13 samples from each of the
eight Audio2Tool tiers and 104 unique query blocks. The roster receipt SHA-256 is
`457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e`; the split identity is
`84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0`; one speech pass is
554.255707 seconds. The promoted speech-packet receipt SHA-256 is
`6f5d77438b50ebba8130122c6cc39acff18f0707836c61e72a03f6af1380c6b5`.

Gold tool calls, reference transcripts, test annotations, scorer outputs, future turns, and prior
responses for these identities remain unavailable to runtime. The runtime semantic index and 43
compatibility rules are prebuilt aggregate knowledge assets. The flight process must load their
hash-pinned, label-free runtime forms and must not reopen construction annotations or derive labels,
centroids, rules, examples, or thresholds while executing.

## Frozen arms and contact budget

Run the following six generation arms in order, with 104 complete responses per arm:

1. `direct_m0`: original speech and the complete 152-tool registry in one call.
2. `obs_semantic_retrieval`: original speech to a strict observation response containing a faithful
   English transcript and a concise tool-name-free desired-action retrieval query. This arm is
   diagnostic, not a task answer.
3. `transcript_top16_use`: original speech, the observation, and the transcript embedding's top-16
   canonical decision cards.
4. `model_query_top16_use`: the same inputs except selection uses the same-core desired-action query.
5. `rrf_fused_top16_use`: the same inputs except selection uses complete-ranking RRF-60 fusion of
   transcript and desired-action rankings.
6. `same_stratum_shuffled_fused_use`: original speech and the recipient observation, but decision
   cards come from a deranged same-tier donor. Card count and prompt class are preserved.

The generation ceiling is exactly 624 frozen-core contacts. The conservative carrier-reference
ceiling is 3,400 speech-audio seconds and the registered GPU ceiling is 4.0 hours. There is no retry,
repair, resend, fallback, response substitution, or network-jitter experiment.

The local `Qwen3-Embedding-0.6B-Q8_0` tool embeds exactly 208 English texts: one transcript and one
desired-action query for every sample. It uses last pooling, dimension 1,024, batches of at most 32,
exactly seven physical loopback requests, and no generation-server coexistence. The embedding plan
registers 208 logical model contacts separately from the seven physical HTTP requests; it is a
retriever only and has no final-answer authority. Exact request-body hashes, response-vector hashes,
logical contact identities, dimensions, and timings must be durable before a vector can affect
routing. Vector values do not enter Git or the final model context.

## Context and concurrency

The physical generation context is 65,536 tokens split across two sample-affine slots, or 32,768 per
slot. The operational maximum required window is 24,576, reserving 8,192 tokens for prompt growth and
implementation variance. At the start of each generation window, read `/props` once to bind the
live process-specific media marker and verify the 32,768-token slot; this local metadata request is
not a model generation contact. Immediately before every generation contact, render the exact current
request with `/apply-template`, tokenize every non-speech segment with `/tokenize`, and add the
measured speech-packet tokens, registered special-token reserve, and that request's completion
ceiling. Refuse a request above 24,576; do not predict later-loop length from an average or trim a
request to make it fit.

Generation uses two slots and queue depth four. This is concurrency, not prompt-level batching.
Generation contacts remain individual sample requests. Embedding alone may use physical batches of
32. Run three disjoint server windows: generation before embedding, embedding, then generation after
embedding.

## Evaluation and estimands

Seal all six complete manifests before opening response meaning, gold, or the scorer. Score the five
task-answer manifests only. Run the unchanged official single-process scorer as five whole-manifest
jobs through an outer process pool of at most four workers. Do not shard a dataset and do not average
shard metrics.

Report exact match, tool accuracy, slot micro-F1, parse rate, all eight tiers, paired saves/harms/ties,
paired sign tests for exact match and tool accuracy, and 10,000 paired bootstrap replicates with seed
20260903. Report these fixed contrasts:

- transcript top-16 USE minus direct M0;
- model-query top-16 USE minus transcript top-16 USE;
- fused top-16 USE minus each single-view USE arm;
- fused top-16 USE minus same-tier shuffled fused USE;
- fused top-16 USE minus direct M0.

After all manifests seal, compute required-tool reachability for transcript, model-query, and fused
top 16. Reachability is the retrieval upper bound: all gold-required tool labels must be inside the
candidate set. A stronger reported diagnostic may state how many of the top five are gold-required,
but redundant labels plus model selection is not an upper bound. If reachability is materially below
0.90–0.95, backtrack to knowledge construction or organization. If reachability is high but task
performance is low, first revise supplied decision content or USE control rather than widening the
candidate list blindly.

## Decision rule and next scale

Do not expand toward approximately 1,000 samples unless both the agent-over-single-call contrast and
the sample-specific-evidence contrast are positive and stable under paired uncertainty analysis, with
no material structural or tier-specific regression. A weak model-query arm with a strong transcript
arm selects the local encoder as the baseline. A positive model-query increment selects the same-core
retrieval query. A fused gain over both singles establishes complementarity. Failure of all matched
arms despite high reachability triggers a knowledge-supply and USE redesign, not an assumption that
the frozen core must be replaced.

Only after a deployment-visible AgentLoop state has measured action-dependent returns may a separate
training-free RL experiment begin. Prefer pinned upstream `vowpalwabbit==9.11.2` contextual-bandit
assets over a repository-owned learner. Preserve untouched discovery support and the test split for
that later stage.

## Artifact bindings

The exact committed config, protocol, runtime, semantic-asset, launcher, factory, ExecutionPlan, and
authority hashes are carried by the contact authority and verified by the contact-ready preflight.
The authority may be executed only from a clean committed tree. Any code, config, data, runtime,
knowledge, prompt, roster, packet, plan, or preregistration hash change requires a new authority and
fresh attempt identities before contact.
