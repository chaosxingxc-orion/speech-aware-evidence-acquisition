# Audio2Tool training-free self-transcript cascade v1 — preregistration

Date: 2026-09-01. Status: **OBS FLOWN AND ABORTED DURING PACKAGING; BOUNDED RECOVERY REGISTERED**.
Experiment: `SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1`. Machine contract:
`configs/experiment/a2t-training-free-self-transcript-cascade-104-v1.json`, initial SHA-256
`635c90e886064f5053507a9118777c7b18880b2695ca410e108eff5f577d58aa`.

## Why this is the next admissible experiment

The locked SLURP engineering baseline already demonstrates the required scale ladder: DEV-100
established the mechanism, the new 400 rows in DEV-500 improved exact match from 52.50% to 72.25%,
and the new 500 rows in DEV-1000 improved it from 55.60% to 75.80%. The latter gain was 20.20
percentage points with a 90% interval of [17.20, 23.40]. That lock establishes a stable
openJiuwen two-contact speech agent above a one-call frozen-core baseline without test tuning.
The remaining unmet objective is a positive, prospective training-free control contribution.

Three independent observations justify a new linguistic observation instead of more threshold
mining on old returns:

1. `docs/readiness/2026-08-20-pemb3m-verdict.md` records that the frozen core's own self-transcript
   routed 45 of 60 samples, or 0.7500, through a text retrieval cascade.
2. `docs/readiness/2026-08-25-a2t-g0-report.md` records an Audio2Tool perfect-transcript
   deterministic BM25 top-5 ceiling of 317 of 400, or 0.7925, well above the A2T-G1-104 M0 tool
   accuracy of 62 of 104.
3. The completed factor-top1 experiment returned model responses for all 103 recovery samples but
   accepted zero strict factor objects. That failure closes the strict structured-observation
   interface; it does not establish that plain English speech content is unavailable.

This experiment therefore changes the observation interface once. It does not relax the failed
schema, add a second language model, read a reference transcript, or retune the existing returns.

## Frozen two-phase AgentLoop

Every sample begins with the same original speech-feature packet and hash-pinned frozen M0 output.
`OBS_SELF_TRANSCRIPT` is one same-core speech-only contact. Its English instruction requests only
the spoken English words. No registry, task-answer schema, knowledge value, M0 response, reference
transcript, label, or score is visible. A deterministic external filter accepts only one-line,
printable ASCII, English-like text with 1–160 tokens and rejects JSON, code fences, role prefixes,
tool-call structures, commentary, and refusals. A rejected string never enters another model
context and forces `STOP_M0`.

All 104 observation contacts must finish and seal before any evidence-use contact can begin. The
batch then passes a label-free liveness barrier only if at least 102 responses, 99 valid
transcripts, 94 positive BM25 routes, and 83 distinct normalized transcripts exist; no identical
transcript may occur more than five times, no JSON/tool-call leakage is allowed, and a same-tier
derangement must be possible for every routed sample. This gate uses no gold, reference transcript,
official scorer, task correctness, or response semantics beyond the frozen structural validator.
Failure terminates the experiment before the expensive USE phase.

For a live batch, `ORG_RETRIEVE` applies deterministic Okapi BM25 (`k1=1.5`, `b=0.75`) to the
frozen 12,936-facet English Audio2Tool knowledge snapshot. The query is the accepted self-transcript
only. The renderer supplies at most five positive facets, six associated values, and five distinct
task targets through the existing canonical knowledge interface. Retrieval makes no model,
embedding, tokenizer, HTTP, or socket contact.

`USE_MATCHED` sees the original speech as primary authority, the sample's own validated
self-transcript as an English AgentState, the complete frozen 152-tool task contract, and the
matched bounded evidence. It is the only new response eligible for the training-free policy.
The final answer authority remains the same frozen core or frozen M0.

## Matched-evidence information control

For every routed sample, a deterministic within-tier rotation assigns another routed sample's
self-transcript. The donor transcript drives BM25 only. `USE_SHUFFLED_EVIDENCE` still receives the
recipient's original speech and own self-transcript AgentState, but it receives an equal-budget
evidence bundle retrieved by the donor. No sample maps to itself, and each sample is used exactly
once as a donor within its tier.

This control holds the second contact, speech, AgentState, task contract, prompt shape, and evidence
budget fixed. A matched advantage therefore identifies information in the observation-to-evidence
link rather than generic second-call or evidence-volume effects. Promotion requires matched exact
match and tool accuracy each to exceed both M0 or shuffled as specified by the machine contract,
and the grouped matched-minus-shuffled exact-match 90% interval must have a strictly positive lower
bound.

## Frozen training-free reward memory

After every model output and complete prediction manifest seals, the unchanged scorer may expose
discovery rewards. Five whole-`query_idx` folds learn only from the other four folds. The default
action is `STOP_M0`. A fixed hierarchical exact-cell memory may use only:

- M0's parsed-set relation to the matched top-five target set;
- a frozen normalized BM25 top-one margin bucket;
- a frozen positive-facet-count bucket;
- transcript word-count and supplied-target-count buckets.

Literal transcripts, tokens, tool or knowledge identities, domains, categories, sample and tier
identity, donor and fold identity, gold, score, correctness, responses, and future turns are
forbidden policy features. A detailed cell is tried before its fixed coarse parent. `USE_MATCHED`
is selected only when other-fold support is at least four, with at least two exact-match saves and
zero harms. There is no learned model, parameter update, policy-family search, missing-return
imputation, or threshold tuning.

Promotion requires both actions, 5–52 USE decisions, at least three policy saves, zero harmful
uses, at least three net exact matches, a strictly positive grouped 90% lower bound, nonnegative
tool accuracy and slot micro-F1, no negative fold and at least two positive folds. The policy must
match or exceed always-use matched exact gain while making strictly fewer final-answer contacts.
Its gain must also exceed the measured resend floor. These conjunctive requirements separately
test agent-over-one-call benefit, matched information gain, and training-free control value.

## Resend and efficient authoritative scoring

Before any USE response is semantically read, two routed samples per tier are fixed by the smallest
registered resend hash. Their exact `USE_MATCHED` request payloads are replayed through fresh gated
attempts. The resend composite replaces only those 16 responses in an otherwise complete 104-row
matched manifest. Request identity, byte divergence, parsed-call divergence, exact-count
divergence, timing, and slot identity are reported.

The official scorer remains unchanged and single-process for each complete manifest. After all
contacts and manifests seal, `scripts/evaluate_parallel.sh --workers 3` starts the matched,
shuffled-evidence, and resend complete-manifest finalizations concurrently. Each worker invokes the
authoritative scorer exactly once on all 104 rows. It never divides one manifest into shards and
never averages shard metrics. A second scoring wave verifies the fixed cross-fitted policy
composite after reward-memory composition. Batch receipts record wall time, summed per-job time,
effective speedup, scorer identity, manifest identity, and result hashes. Evaluation speed is an
engineering measurement, not a scientific promotion criterion.

### Pre-contact implementation binding: observation and derivative lifecycle

The observation-only attempt ends in the durable `ABORTED` state after its complete English
transcript artifact, trace, cost, and liveness report seal. Here `ABORTED` means "not eligible for
task-answer scoring," not a failed model execution. This terminal state prevents an observation
response from being mistaken for a task answer or left indefinitely open. A failed liveness gate
stops there without opening USE, gold, or the scorer.

Complete matched, shuffled-evidence, and resend prediction manifests may contain deterministic
reuse of frozen M0 or an already sealed composite. Their trace binds every reused row to an
absolute source artifact path and a freshly verified SHA-256; current-attempt `calls_used` remains
the measured number of new model requests and is never inflated to the 104 output-row count.

Wave 1 finalizes the three independent model-bearing attempts in three outer workers. Wave 2 is a
single `score` operation over the complete model-free policy derivative. The derivative binds the
already-finalized matched-attempt identity but does not reopen or mutate it. This is an
implementation/lifecycle clarification only: it changes no sample, prompt, route, action rule,
metric, bootstrap, promotion gate, or contact budget.

## Exposure, budgets, and terminal decisions

The cohort is the already-exposed, tier-balanced A2T-G1-104 only. This registration permits at most
104 observation contacts, 104 matched USE contacts, 104 shuffled-evidence USE contacts, 16 exact
resends, and six canary allowances: 334 calls, 2,000 metered speech-audio seconds, 1.0 planned
GPU-hour, and zero paid API, embedding, or tokenizer contact.

Implementation, red-then-green tests with at least 80% targeted branch coverage, structured
`ExecutionPlan` files, exact source/runtime/packet/protocol identities, attempt budgets, prompt-fit,
three prepared complete-manifest scoring jobs, and a clean committed tree must all land before the
first contact. Gold and scorer remain closed until every response and complete manifest seals.

A liveness failure closes the interface without USE or scoring. A scientific-gate failure closes
this matched self-transcript BM25 mechanism on this cohort and authorizes no new contact. A pass
freezes the complete mechanism and permits only a separately preregistered, block-disjoint,
approximately-104-sample prospective support proposal. Only that independent support pass may
propose an approximately-1,000-sample Stage-2 engineering validation. Neither this contract nor a
failure permits another parent row, test data, G2, FINAL60, a baseline revision, Stage-3,
paper-scale execution, or a superiority/generalization claim.

## Recovery amendment

The first flight completed all 104 observation contacts and then aborted on a launcher-only trace
manifest packaging defect before liveness authorization, USE, gold, or scoring. The label-free
read subsequently established 104/104 valid, distinct, positively routed transcripts. The fixed
source hashes, 104-call spend, no-repeat rule, trace-sealing repair, and zero-OBS recovery entry are
registered in
`docs/readiness/2026-09-01-a2t-self-transcript-cascade-104-v1-recovery-preregistration.md`.
That amendment changes no scientific axis or original 334-call ceiling. The first recovery then
sealed 104 matched and 104 shuffled contacts before a mixed-trace resend-extractor packaging abort;
no resend, gold, or scorer contact occurred. The same recovery registration now fixes those source
hashes and permits only zero-call complete derivatives plus the original 16 resends. Cumulative
use is 312 calls; only 22 calls remain under fresh attempt identities.
