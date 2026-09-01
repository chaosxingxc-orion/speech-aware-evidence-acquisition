# Audio2Tool training-free semantic-factor top-1 v1 — preregistration

Date: 2026-09-01. Status: **REGISTERED DESIGN; NO MODEL CONTACT AUTHORIZED YET**.
Experiment: `SAEA-A2T-TFRL-FACTOR-TOP1-104-V1`. Machine contract:
`configs/experiment/a2t-training-free-factor-top1-104-v1.json`.

## Why this mechanism is the next admissible change

The prior prospective self-consistency flight produced a live second observation but no saves from
re-observation and an unsafe evidence arm with four saves and ten harms. Its schema-risk successor
then parsed every deployment signature and produced live risk classes, but no registered cell
safely separated the same returns. Both training-free controllers stopped on all 104 samples.
Those results close more category, threshold, and schema-risk search on the existing supply action.

The next mechanism therefore changes both information acquisition and evidence generation. One
same-core contact organizes the speech into a strict English semantic-factor object. A pinned local
retriever ranks the frozen registry from those factors and selects at most one row. A later final
contact receives the original speech, the canonical factor state, and exactly that one
values-stripped row. The core never sees a supplied candidate menu. This follows the earlier
measured constraint that the core emits keyed candidates rather than safely arbitrating among them.

## Frozen AgentLoop

Every sample starts from the same speech-feature packet and frozen M0 response used by the previous
104-sample work. `ORG_FACTORS` asks the frozen core for `task_action`, `task_object`, up to four
qualifiers, up to four role/value hints, and a low/medium/high uncertainty label. A strict response
schema forbids extra fields and a tool-call list. Canonicalization rejects non-ASCII control text,
collapses whitespace, and deterministically sorts and deduplicates repeated factor entries. An
invalid or empty factor cannot acquire evidence and the scored composite returns M0.

`RETRIEVE_TOP1` is model-free Okapi BM25 with `k1=1.5` and `b=0.75`. Its documents contain only the
camel-case-split tool name, domain, category, description, and signature names. Argument defaults
and constraints do not enter ranking. Scores tie by ascending numeric `tool_id`; no positive score
means no candidate. Supply contains one canonical registry row with `argument_defaults` removed.

`USE_FACTOR_TOP1` is the only second model contact. It preserves the original speech as primary
authority and makes the canonical factor state and one traced registry value visible through the
openJiuwen workflow. Where retrieval is available, its response is the experimental task answer.
The factor response is never a task answer, unavailable diagnostic responses are excluded, and no
other answering model exists.

### Pre-contact implementation amendment

The generic openJiuwen trajectory runner requires every stopped trajectory to select a response
produced inside that trajectory; it cannot terminate by injecting an externally reused frozen M0
byte string. Therefore every discovery trajectory records the second diagnostic contact. When
factor parsing or positive-score retrieval fails, the rejected factor is replaced by a fixed
English sentinel, no registry facet or value is supplied, and the diagnostic response is excluded
from both action-return memory and the scored main composite. That row is forced to frozen M0. A
deployed controller would stop after the factor and would not spend the unavailable second contact.

This amendment occurs before any model contact, keeps the 104-contact phase-3 maximum and every
promotion gate unchanged, and makes the actual openJiuwen trace total while preserving the
registered exactly-one-row-or-no-row supply law. It introduces no new information variable.

## Training-free decision and information-gain requirements

The experimental arm acquires the counterfactual final response wherever a top-1 row is available.
After all model outputs seal, five whole-`query_idx` folds learn an exact-cell action-return memory
from the other four folds. State contains only factor validity and uncertainty, retrieval/M0
relation, top-score tie status, positive-document-count bucket, matched-token-fraction bucket, and
nonempty-field-count bucket. Tool identity, registry semantics, literal factor strings, sample or
tier identity, gold, correctness, reward, and future responses are forbidden.

A cell selects `USE_FACTOR_TOP1` only with support at least four, at least two exact-match saves, and
zero harms; otherwise it returns frozen M0. All samples pay the factor contact in the proposed
controller, while only selected samples pay the final evidence contact. No parameter is updated and
no missing counterfactual is imputed.

Promotion is conjunctive. Factor parse rate must reach 95%, a positive top-1 must exist for 90%, and
top-1 gold-tool correctness must exceed M0 tool correctness by at least three samples. The
cross-fitted policy must use both actions, use evidence on 5–52 samples, save at least three exact
matches, harm at most one, gain at least two exact matches, have a strictly positive grouped CI90
lower bound, avoid at least 80% and at least one of the always-use harms, retain at least 50% of
always-use saves, remain nonnegative on tool accuracy, slot micro-F1, and every fold, and have at
least two positive folds. Its exact gain must be no worse than always-use while using at most half
the cohort for final evidence contacts.

These gates separately require new information, agent-over-single-call benefit, and a training-free
control contribution. A live factor state alone is not enough.

## Resend control and scorer efficiency

After factor outputs identify candidate availability but before any response is semantically read,
two available samples per tier are fixed by the smallest hash of `resend-v1` plus `sample_id`.
Their phase-3 requests are repeated byte-identically in separate workflows. The main and resend
responses each form a complete 104-row manifest; unchanged rows are shared and unavailable rows use
frozen M0. The two unchanged official scorer invocations run concurrently through
`scripts/evaluate_parallel.sh --workers 2`. There is no dataset sharding, shard-level metric, or
scorer modification.

### Pre-contact exact-replay and complete-manifest amendment

The replay workflow passes the original traced phase-3 payload directly to a fresh gated
`FrozenCoreAdapter`; it does not rebuild an equivalent AgentLoop call. Canonical serialized request
bytes, including request id, slot id, speech packet, decoding parameters, factor state, supplied
row, and control instruction, must hash to the original `MODEL_REQUEST` payload before dispatch.
The fresh resend attempt keeps its own trace and durable accounting while the payload itself stays
byte-identical. Selection reads only structural candidate availability and is fixed before final
response text is inspected.

The two official scorer workers finalize two distinct attempts. The main attempt carries all 208
factor and phase-3 contacts. The resend attempt carries exactly 16 replay contacts. Each attempt
materializes a complete 104-row composite through deterministic `TOOL` trace records: available
main rows cite their phase-3 response, unavailable rows cite frozen M0, selected resend rows cite
the replay response, and the other resend rows cite the hash-pinned main composite. This preserves
the existing bundle output-to-trace invariant without mislabeling a reused M0 byte string as a new
model response. The shared run-level budget remains 228 contacts and 1,340 speech-audio seconds.

Prompt fit reuses the landed session-bound Audio2Tool NP2 envelope at SHA-256
`0c77812d9439b6a7d6d3ff0227fc27924f617245d1ec9a0cbca20960f090946b`. That envelope contains the
same complete task contract, one agent-state text, five visible facets, and six visible values at
19,413 prompt tokens plus 1,024 completion tokens against 32,768 tokens per slot. This probe keeps
the same task contract and constructor but exposes one state, at most one facet, and at most one
value, so it is strictly dominated by the landed envelope. Any constructor, receipt, task-contract,
packet, or serving-geometry drift fails preflight and requires a separately registered model-free
prompt-fit measurement; this flight never opens an unregistered tokenizer contact.

### Pre-result peg-native recovery amendment

The first main attempt stopped after five metered requests. Three factor requests returned HTTP 500
and no `MODEL_RESPONSE` because the receipt-pinned server could not reconcile Qwen's peg-native chat
format with the OpenAI `response_format` JSON-schema path. One sample completed both contacts, but
its final request carried zero supplied registry values. Before reading either response text, that
sample is fixed to `STOP_M0`, excluded from retrieval and reward memory, and must never be
re-contacted. The three error requests have no returned response and may be issued once under the
repaired protocol. Exact structural identities and trace hash are frozen in `recovery-plan.json`.

Recovery runs the remaining 103 samples. It removes only server-side `response_format`, caps the
factor completion at 256 tokens, and retains the exact same strict external parser, fields,
canonicalization, tool-name rejection, BM25, one-row renderer, state, folds, thresholds, promotion
gates, and scorer. Arbitrary text, tool calls, extra fields, malformed JSON, non-ASCII text, and
tool-name leakage still become `invalid` with no retrieval. The contact therefore remains
strictly post-validated, while avoiding a server path that returned no usable factor.

The recovery spends at most 206 main contacts plus 16 resends. Including the five consumed canary
requests, cumulative use is at most 227 of 228 contacts. The 1,340-second ceiling also covers the
five consumed calls plus the registered worst-case resend durations. No scorer or gold has been
opened. Both complete 104-row composites still seal before the same two-worker official finalizer.

The result records byte, parsed-call, and exact-score divergence. The cross-fitted policy's exact
gain must exceed the absolute main-versus-resend-composite exact-count difference. This measures the
stack's current resend floor instead of assuming deterministic decoding is bit-reproducible.

## Exposure, stop rules, and scope

The population remains the fully exposed, tier-balanced `A2T-G1-104` discovery cohort. This design
opens no new sample identity. Maximum planned contact is 104 factor calls, 104 main final calls, 16
resends, and four canary allowances: 228 calls, 1,340 metered speech-audio seconds, 0.6 GPU-hours,
and zero paid API, embedding, or tokenizer contact.

No contact is authorized until implementation, tests, structured `ExecutionPlan`, exposure binding,
all source and runtime hashes, packet checks, prompt-fit checks, two complete scorer job specs, and a
clean repository state land. A failure closes this factor-to-BM25-top-1 single-row mechanism; it
cannot be followed by larger `k`, a menu, BM25 tuning, state-bin search, or gate relaxation on these
returns. A pass can only freeze a proposal for a separately preregistered fresh approximately-104
support flight from the remaining exposed discovery population. It cannot revise the baseline or
open approximately 1,000 samples, G2, unexposed data, FINAL60, test annotations, Stage-3, or
paper-scale work.
