# G8 action-support reachability fixed16 preregistration

## Purpose and boundary

G8 is a 16-row action-set reachability screen. It asks whether four complete
macro-actions contain enough answer support to make later training-free control
scientifically worthwhile. It does not fit a policy, estimate a deployable
policy, authorize model contact, or admit a scale claim.

The `>0.90` objective is a post-training-free-control target. It is not an
admission criterion for the direct or AgentLoop engineering baselines.

## Prospective identity

The `A2T-G8-ACTION-SUPPORT-FIXED16` receipt selects exactly two identities per
tier from the exact 44-row `support_remainder` in the frozen G7 receipt. It
sorts each tier by
`SHA-256("speech-aware-evidence-acquisition-g8-action-support-fixed16-v1" NUL sample_id)`
and then by `sample_id`. The resulting carrier-prefixed split identity hash is
`06acbcf6b9bd3fde67c1de8da622d6d446a5ec993926be3f58c42968dddb250b`;
28 identities remain untouched.

Roster construction reads only `key`, `sample_id`, and `tier`. It does not read
task text, audio, gold, outputs, scores, rewards, test annotations, or future
turns. The generated receipt is reproducible from
`scripts/build_a2t_g8_action_support_fixed16.py` and is tested for stability,
source exhaustion, per-tier balance, and disjointness from G7.

## Frozen complete actions

`STOP_M0` reuses the sealed same-row G1 M0 frozen-core response by exact sample
identity and makes no new contact.

The other three actions share one OBS response and the same 28 family EVIDENCE
responses for each row. Those shared responses and the normalized all-tool
sheet seal before branch-specific supply is derived.

1. `EXHAUSTIVE_G7` gives the frozen core the complete G7 execution sheet and
   all normalized assessments for one final resolve.
2. `SUPPORT_ONLY_RESOLVE` mechanically retains only registered tools whose
   normalized status is exactly `support`, in frozen registry order. It removes
   every `contradict` and `uncertain` candidate. An empty result remains empty;
   there is no fallback, inference, or repair. The frozen core resolves once.
3. `DECOMPOSED_SELECT_BIND_RESOLVE` directly targets the two main G7 USE
   failures. A first speech-carrying contact receives family objectives,
   operations, and the complete normalized tool-status surface, but no
   argument schemas, and returns only an ordered list of exact registered tool
   names. A second speech-carrying contact receives only the selected tools'
   legal key skeletons and types and binds their argument objects without
   changing the selection. A third speech-carrying contact authors the final
   official response from the sealed selection and bindings. An empty
selection stays empty; no stage may add a fallback or repair an answer.

The decomposed protocol accepts at most 32 ordered selection occurrences and
4,096 UTF-8 bytes in the selection response. Repeated exact registered names
remain repeated in their original order. The binding response accepts at most
12,288 UTF-8 bytes and must contain exactly one typed argument object per
sealed occurrence with the identical name, count, and order. Invalid JSON,
unknown names, excessive fan-out, response overflow, skeleton drift, type
drift, or binding misalignment aborts and terminalizes the one-shot attempt
before its next contact. It does not trigger a retry, repair, empty-answer
substitution, branch-manifest emission, or scoring.

The selection and binding completion reserves are 4,096 and 12,288 tokens,
respectively. These conservative reserves cover their full frozen UTF-8
response envelopes even under the one-byte-per-token upper bound; early JSON
termination consumes only the tokens actually generated.

Every final response is authored by the frozen Qwen3-Omni core on the unchanged
official JSON-array surface. Filters, parsers, the future controller, and the
value verifier never obtain final-answer authority.

## Execution geometry

The maximum and frozen geometry is 34 new speech-carrying contacts per row:
one shared OBS, 28 shared family EVIDENCE contacts, one exhaustive resolve, one
support-only resolve, one decomposed tool selection, one decomposed argument
binding, and one decomposed final resolve. Across 16 rows this is 544 contacts.
`STOP_M0` adds zero contacts. There are no retries,
resends, repairs, tokenizer contacts, embeddings, or paid API calls.

Batch execution remains enabled with two sample-affine slots and at most two
concurrent model requests. Network jitter is not an experimental variable.
Before every future contact, the executor must render the actual serialized
request and account for its speech, special-token, and completion reserves.
It uses a conservative UTF-8 byte upper bound for the serialized text and a
separate 512-token special-token reserve, so this contact-free measurement
does not require a tokenizer service or underestimate text tokens.
Each request must remain within the 24,576-token operational cap of the
32,768-token slot and retain at least 8,192 tokens of headroom. A fixed estimate
from an earlier loop step cannot authorize a later request. Overflow refuses
before contact and never trims.

This document and its config are preregistration scaffolds only. A later
execution authorization must first bind exact prompts, schemas, implementation
hashes, runtime receipts, an `ExecutionPlan`, exact repeated-audio accounting,
and the exposure-ledger entry. The contact-free launcher implementation does
not itself authorize execution.

## One-shot execution activation

The zero-contact preflight passed on clean source commit
`ed22380ed511e097389876f6d8e0132fb1ba73d7`. It verified the receipt-pinned
server and model, 317 promoted packets, the exact 16-row packet join, the
frozen 104-row M0 source followed by exact 16-row identity filtering, and
OpenJiuwen `0.1.16.post2`. The largest conservative dynamic envelope is the
exhaustive resolve at 24,317 of 32,768 tokens, leaving 8,451; select leaves
10,038 and maximum bind leaves 14,038.

Attempt `attempt-20260903t015045z-g8-fixed16` is bound by the structured
ExecutionPlan SHA-256
`586370c731a49213a04f5c08faabbc2e04dee4805afdb503d97e58a546368773`
and zero-contact preflight report SHA-256
`a1c6c80b54642a1f1280f382d4e8fdb634a603bc4e9da4a1304ddbb16087bd1b`.
The exposure ledger registers exactly 544 calls, 2,728 speech-reference
seconds, and 1.0 GPU-hour before any result is read. This activates only that
one-shot attempt. It does not authorize a retry, a replacement roster, policy
fitting, scale, confirmation, or test access.

## Seal, score, and oracle

Gold remains closed until all four complete 16-row branch manifests, traces,
final responses, and costs seal. Each complete branch manifest is then scored
by exactly one unchanged official scorer process. Independent complete
manifests may be scored concurrently by an outer coordinator; a manifest may
not be sharded, and partial metrics may not be averaged. The authoritative
score command persists aggregate and per-sample results from that same single
invocation. A branch scorer is never rerun to recover row detail.

After scoring, construct a gold-informed per-row branch oracle. For each row,
prefer a branch with exact match. Break exact ties by row-level slot F1, then
tool correctness, then the frozen action order `STOP_M0`, `EXHAUSTIVE_G7`,
`SUPPORT_ONLY_RESOLVE`, `DECOMPOSED_SELECT_BIND_RESOLVE`. When no branch is exact, use
the same slot-F1, tool-correctness, and action-order tie break. Build one 16-row
oracle manifest from the chosen sealed responses and compute unchanged
official metrics once. This oracle is an action-set ceiling, not a learned or
deployable policy result.

## Decision rule

Proceed to a separately preregistered, approximately 100-row randomized and
propensity-logged Vowpal Wabbit discovery experiment only if the oracle reaches
both:

- at least 15 of 16 exact matches; and
- slot micro-F1 strictly greater than 0.90.

If either condition fails, do not fit a controller over these actions and do
not collect the approximately 100-row policy-learning surface. Improve the
knowledge or macro-action set on a new identity-only discovery roster. The
approximately 1,000-row stage, test data, confirmation, and paper-scale work
remain closed.
