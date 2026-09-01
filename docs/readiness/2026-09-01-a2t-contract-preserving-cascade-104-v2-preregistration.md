# Audio2Tool contract-preserving cascade 104 v2 — preregistration

Date: 2026-09-01. Status: **IMPLEMENTATION FROZEN; CONTACT CLOSED UNTIL CLEAN PREFLIGHT PASSES**.
Experiment: `SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2`. Machine contract:
`configs/experiment/a2t-training-free-contract-preserving-cascade-104-v2.json`, initial SHA-256
`cf77ceee65ce0ed8c30b1ac5a469b1f6688f1eb0bca3d4340e9a784c1976039e`.

Identity-only materialization from clean study commit `ecd50b385b00bc7973acd15399d298ee0712b8c1`
froze receipt `docs/receipts/a2t/A2T-CPV2-104.json`, SHA-256
`8f47922124c61f92fee03273c1165eb1f8f97048d910ddd4a6a7243906d78783`, split identity
`a0acb1672aa1d65517f050418c530cebce9946328d030f41af958ff1a946d42c`, and run identity
`401a28684adea908c80363df0815c9ce04b0ffa46a654975b129d4b69e60f8a1`. The materializer read
no gold, query text, expected call, prior response, prior score, or test field. It selected 104
unique query blocks, 13 per tier, with zero overlap against all 104 A2T-G1-104 query blocks and
536.05 total speech-audio seconds. The receipt-binding amendment changes no experimental rule;
the current machine-contract SHA-256 is
`00f3fa9b1b3386a3a889dcbbbf79f7141a106c30ab475a5634ebda65e6d5c54e`.

## Why this is a distinct successor

The predecessor proved that same-core English transcription and BM25 routing were live but that
its USE adapter silently dropped the original Audio2Tool output sentence and exact
`[{"name": "x", "arguments": {}}]` example. Its matched, shuffled, and resend surfaces consequently
produced no valid nonempty official call. The predecessor is closed exactly as registered: no old
response will be normalized, reparsed, rescored under a new parser, or recontacted, and no old
retrieval or policy threshold will move.

This successor changes one prospective engineering variable on a different cohort. Its direct M0
arm uses the existing Audio2Tool prompt byte-for-byte. Its USE arms insert the self-transcript and
evidence before the same final output sentence and example, leaving that output contract as the
last system text. Raw model output still goes to the unchanged official parser without cleanup or
normalization. This tests whether the prior failure was a prompt-boundary defect while preserving
the original agent information path.

## Population and isolation

The population is `A2T-CPV2-104`, still secondary discovery evidence because its parent 400 was
already exposed. Selection is frozen before materialization: remove every parent item whose
`tier/query_N` block occurs in `A2T-G1-104`; then, within each of the eight tiers, sort by
`SHA-256("a2t-contract-preserving-cascade-v2" + NUL + sample_id)`, break ties by sample id, and take
13. No gold, query text, expected call, old response, old score, or test field participates. The
landed receipt carries both identity hashes, media byte hashes, durations, block ids, the parent and
exclusion hashes, and an explicit zero-overlap proof. Implementation remains closed until this
receipt binding is committed and its real-receipt regression test passes.

## AgentLoop and label-free stop sequence

The frozen core is reached only through the receipt-pinned local API-shaped service and the
`openjiuwen-workflow-v1` executor. The new same-flight M0 direct arm supplies the single-call
comparator. OBS then requests English transcription from speech alone. All 104 OBS rows seal before
the existing label-free 104-row transcript and routing gate can authorize any USE.

USE starts with only 16 contacts: one independently hash-selected sample per tier is sent once with
matched evidence and once with same-tier shuffled evidence. Before response meaning, gold, or score
is opened, the raw bytes must yield at least 15/16 strict envelopes, at least 7/8 in each arm, and at
least one valid result in every tier. A strict envelope is unfenced exact JSON containing one to
four objects, each with exactly `name` and `arguments`; every name is a member of the frozen
registry and every arguments value is an object. Failure stops before the remaining 192 USE
contacts. Passing canaries become ordinary rows of their complete surfaces; they are not repeated.

Matched USE receives original speech, its own transcript, and at most five facets, six values, and
five targets from deterministic BM25. The control keeps original speech and the recipient's own
transcript but rotates only the retrieval query within tier. Sixteen exact matched-request resends,
two independently hash-selected per tier, bound request instability. All model responses and all
four complete prediction manifests seal before gold or official scoring opens.

## Training-free contribution and promotion

Five whole-query-block folds estimate a hierarchical exact-cell signed-return memory. State is
limited to M0/route-set relation, BM25 margin, positive-facet count, transcript length, and target
diversity. Literal transcript, identity, tool, knowledge, gold, reward, response, tier, donor, and
future-turn features are forbidden. A cell needs support four, two saves, and zero harms; everything
else chooses `STOP_M0`.

Promotion is conjunctive. Retrieval must add at least three gold-tool hits over M0. Matched evidence
must add at least three exact and three tool-correct results over both the single call and the
shuffled control, with a strictly positive grouped matched-minus-shuffled CI90 lower bound. The
policy must use 5–52 final contacts, save at least four, harm at most one, gain at least three exact
matches with a strictly positive grouped CI90 lower bound, regress neither tool accuracy nor slot
micro-F1, keep every fold nonnegative with two positive folds, beat the resend floor, and exceed the
always-use exact gain by at least two while using fewer final contacts. Both actions and a live
non-dominant state are mandatory. These clauses jointly require agent-over-single-call improvement,
information delivery beyond matched-budget noise, and an incremental training-free selection
contribution beyond unconditional two-call use.

A discovery pass can authorize only a separately registered, query-block-disjoint approximately-104
support proposal. That support run must freeze this discovery memory and apply it without fitting on
support rewards. Only a positive support result may propose a separately decontaminated
approximately-1,000 engineering experiment. Nothing here authorizes either run.

## Official scoring efficiency

Wave 1 contains four independent complete manifests: M0, matched, shuffled, and resend. Four outer
workers each invoke the unchanged official single-process scorer exactly once on one full 104-row
manifest. No dataset shard exists and no shard aggregate is averaged. The dependent model-free
policy is built after wave 1 and scored once in wave 2. Both waves record wall time, summed job time,
effective speedup, worker count, full-manifest identities, and result hashes. A failed job makes the
wave fail without cancelling or hiding other completed jobs.

## Budget and closed surfaces

The cumulative ceiling is 440 model contacts: 104 M0, 104 OBS, 104 matched, 104 shuffled, 16 resend,
and eight unused-unless-needed allowance contacts. Speech audio is capped at 2,700 seconds and GPU
time at 1.5 hours. Paid API, embedding, and tokenizer contacts are zero. The canaries are included
inside the matched and shuffled totals rather than added to them.

Before contact, the cohort receipt, implementation, tests with at least 80% targeted branch
coverage, structured ExecutionPlans, exposure binding, composed and protocol hashes, runtime and
packet receipts, prompt-fit proof, exact-output-contract byte test, canary gate, complete-manifest
job table, and clean tree must land. G2, unexposed Audio2Tool data, FINAL60, test annotations,
future turns, Stage-3, and paper-scale work remain closed.

## Pre-contact implementation binding

The implementation and all remaining bindings now land prospectively. The composed config
SHA-256 is `ff6f8a0065279243126635caf2b648568c2b579274a2c5a44bbdfe624946dd93`; its protocol
SHA-256 is `52d1d4e589bf6663e5724b7095cbbfce9fd1e6f9eaee9a12280e7b4f93348dba`.
The main baseline binds the exclusive preprocessing promotion receipt SHA-256
`a9ae338fbc9ba4734553b97a417403923aa6e085d3bd4446848a2abff3b65c87` and prompt-fit receipt
SHA-256 `9b6b8464926af01b33bdd6f1f5360eb6623702033e217491b26141b3f947d5df`.
The latter verifies all 104 packet/audio hashes, measures a worst speech feature length of 455
tokens, and leaves 12,240 tokens of margin in each 32,768-token serving slot without a model or
tokenizer contact.

The launcher emits a true direct M0 request without Agent state or control history, preserves the
exact final output-contract bytes in both USE arms, keeps each canary inside its original complete
attempt, and leaves gold closed until M0, matched, shuffled, and resend manifests have all sealed.
Its Wave-1 job table invokes four unchanged official single-process scorers concurrently with four
outer workers, once per complete 104-row manifest; it contains no dataset sharding or shard-score
averaging. The dependent policy remains one complete single-worker Wave-2 job. Model contact stays
closed until the committed tree is clean and the launcher's read-only preflight passes every
identity, budget, runtime, packet, prompt-fit, AgentLoop, and scorer-plan check.

The four targeted mechanism modules jointly reach 82% branch coverage in the pre-contact suite
(policy 81%, cohort construction 99%, bundle materialization 71%, and AgentLoop flight 80%).
Separate launcher assembly tests cover frozen identities, non-repeated canary combination, and the
default-score command boundary.

## Post-M0 manifest-path recovery amendment

The first flight from clean commit `d555b7bc7f68b96bf677539f88d3ae56d5cfae4c` completed all 104
direct M0 contacts and then stopped at the first bundle verification. Attempt
`attempt-20260901t223557z-cpv2m0` records 104 calls and 536.05 audio seconds and is terminally
`ABORTED`. The responses, raw trace, trace manifest, outputs, session receipt, and stop receipt all
sealed, but the launcher asked `build_manifest` to discover the raw trace in the M0 parent
directory while the direct client had written it in `transport-trace/`. The resulting manifest
correctly refused because its `raw_trace` and `trace_manifest` entries were null. OBS, matched USE,
shuffled USE, resend, gold, and the official scorer all remained unopened, and response meaning was
not read.

Before any further contact, recovery plan
`docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-contract-preserving-cascade-104-v2/m0-manifest-recovery-plan.json`,
SHA-256 `00ec5bf6781816a8349959850e17da0d13f5dd96affbef7c04a57b0654ae9737`, freezes
every source artifact hash. M0 must not be contacted again. A model-free repair may add only the two
already-sealed trace artifact metadata entries to a new manifest document while preserving the old
study commit, attempt identity, output bytes, cost, and every scientific field. The recovered
manifest must verify against the terminal `ABORTED` attempt before the launcher may open one fresh
OBS attempt and the original remaining stages. At most 328 further calls are possible, so cumulative
use remains at most 432 of the registered 440.

Wave 1 remains four concurrent outer workers over four complete 104-row manifests. Because the M0
attempt is terminal, its official operation is read-only `score`; matched, shuffled, and resend
remain `finalize`. The batch therefore uses the existing per-job-operation mode. This changes no
official scorer, prediction, metric, concurrency boundary, sample, prompt, evidence, policy, fold,
gate, or claim surface. Dataset sharding and shard-score averaging remain forbidden. Model contact
stays closed until this amendment, recovery implementation, tests, score plan, and exposure update
land on a clean commit and the recovery preflight passes.
