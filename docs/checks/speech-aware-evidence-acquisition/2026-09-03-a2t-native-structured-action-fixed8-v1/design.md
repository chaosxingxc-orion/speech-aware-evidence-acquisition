# Native structured-action fixed-eight design

Date: 2026-09-03. Status: **DESIGN ONLY; MODEL CONTACT CLOSED**.
Formal experiment id: `SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1`.
Execution profile: `bounded-discovery-probe`.

## Decision question

G8C showed that more AgentLoop steps and more evidence did not make the current action set useful.
Its post-score oracle remained 4/12 exact with slot micro-F1 0.5116. The decomposed path usually
selected the correct tool but failed to construct canonical arguments and values. Actual context
headroom remained at least 9,193 tokens, so context length was not the observed cause.

This experiment asks one narrow question before another AgentLoop or any policy fit: does an
upstream llama.cpp constrained-decoding surface, built from the complete task-wide action contract,
make exact actions reachable? The schema supplies no sample value. It only constrains the output to
registered tool names, construction-qualified legal argument-key skeletons, public types, public
constraints, and aggregate-supported compatibility forms.

## Paired two-by-two design

The no-schema cells are reused without model contact from the sealed 104-row executable-ground
qualification flight. The two new cells run on the same identity-only fixed eight.

| Cell | System knowledge | Structured action contract | Contact |
|---|---|---:|---:|
| `REGISTRY_NO_SCHEMA` | complete 152-row registry | no | sealed historical subset |
| `REGISTRY_STRICT_ACTION` | byte-identical registry message | yes | eight new calls |
| `HANDBOOK_NO_SCHEMA` | 54,881-byte executable handbook | no | sealed historical subset |
| `HANDBOOK_STRICT_ACTION` | byte-identical handbook message | yes | eight new calls |

This is an action-contract factor, not an outer-format-only factor. Applying the identical schema to
both knowledge surfaces preserves the two-by-two comparison: the schema main effect measures
structured action-contract delivery; the handbook main effect measures task semantics expressed in
the prompt; their interaction tests whether both are needed.

The historical flight used the same frozen Qwen3-Omni core, receipt-pinned llama.cpp runtime,
speech packets, temperature zero, seed 20260803, 1,024-token completion ceiling, and two
sample-affine slots. Its aggregate results are already exposed: registry was 0/104 exact with 104
parse failures; handbook was 19/104 exact, 71/104 tool correct, slot micro-F1 0.3495, and 104/104
parsed. Those aggregates motivate the mechanism but did not select any fixed-eight identity. No
fixed-eight historical output, per-sample score, reward, gold, or task text may be opened before the
two new cells seal.

## Frozen roster and knowledge

The roster is `docs/receipts/a2t/A2T-NATIVE-STRUCTURED-ACTION-FIXED8.json`, SHA-256
`b777f05e830af84209d6aa3403fe86d3835991452f983b3185214990004a4be3`. It contains one
identity-only SHA-256-ranked row per tier, eight rows and 45.096 speech seconds, split identity
`f95efe70b615d71bb082f9ef804d1fa2b6f04ce4114d5d2694151cbaf44019ba`. The roster is secondary
discovery from `A2T-GROUND-QUAL-104`, disjoint from G8/G8B/G8C and CPV2. It is not an independent
confirmation sample. Protected confirmation, test, and future turns remain closed.

The prompt handbook is the frozen values-stripped executable ground, SHA-256
`58ba08f3cebbe390156506653051d54aa37796822f49f5b851fd6eba4818fbc8`. It contains all 152
tools, 354 construction argument-pattern families, all 85 argument keys, and zero construction
utterances, invocation texts, concrete argument values, or complete registry-default literals.

The strict action schema is rebuilt from the already-qualified G4 semantic cards because those
cards retain explicit public types and aggregate-supported compatibility forms. It must contain all
152 registered tools, exactly 338 legal tool/skeleton branches, and 43 compatibility rules. The
schema builder must consume none of each card's synthetic examples, rendered card text, source
utterances, source values, sample identities, reference transcripts, evaluation rows, or gold. Its
model-free build produced the canonical 91,407-byte artifact at
`$SPEECHRL_DATA_DIR/knowledge/audio2tool/structured-action-schema-v1/response-format.json`, SHA-256
`8fe5db869f044b9e952765f7bee045027ad137db2cc445ff428db5303fb1a2ed`. The build receipt is
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-structured-action-schema-build-v1/build-receipt.json`,
SHA-256 `2931aba40a9a94921f670b857a052e69e1fba9820250cb1a8206b9838b35c581`. It records zero
model, tool, scorer, tokenizer, or network contact and zero evaluation or source values rendered.

## Execution and context

Run `REGISTRY_STRICT_ACTION` first and `HANDBOOK_STRICT_ACTION` second through one unchanged
service session. Use two 32,768-token sample-affine slots, concurrency two, queue depth four, and
batch size two. Expected and maximum new contact are both 16; exact delivered speech is 90.192
seconds and the registered ceiling is 91 seconds. No repair, retry, resend, output normalization,
tool execution, network-jitter test, paid API, retriever, embedding model, tokenizer endpoint, or
second answerer is permitted.

Before contact, reconstruct all 16 real envelopes and bind the system/user messages, speech packet,
source slot, decoding parameters, response schema, and rendered request hashes. The strict cell must
differ from its historical parent only by request/accounting identity and `response_format`. Measure
each actual serialized prompt immediately before sending it. Require prompt plus completion at most
24,576 tokens, leaving at least 8,192 tokens in the configured 32,768-token service slot. This
single-contact screen makes no claim about an architecture-wide maximum context. A later
OpenJiuwen loop must repeat the measurement at every step because its history grows dynamically.

Any partial failure seals available traces, aborts open attempts, stops the service, and ends without
recontacting a row. Recovery requires a prospective successor.

## Post-seal evaluation

Only after both new eight-row manifests and their traces seal may the fixed-eight historical subsets
be materialized and gold opened. Run four unchanged official single-process scorer jobs through four
outer workers, one complete manifest per process. Never shard a manifest or average shard metrics.

Report parse, exact, tool correctness, slot micro precision/recall/F1, hard validity, legal key-set
coverage, and paired exact wins/losses for each cell. Build a zero-contact four-cell oracle after all
four official scores exist.

The mechanism passes only if all clauses hold:

1. Both strict cells parse 8/8 with zero wrong outer shape and zero out-of-registry names.
2. Every strict-cell result is valid under the label-free legal key/type/constraint validator.
3. The four-cell oracle reaches 8/8 exact, 8/8 tool correct, and slot micro-F1 at least 0.90. The
   8/8 exact requirement is the small-screen evidence that a later post-policy target above 0.90 is
   not excluded by the available actions.
4. At least one new strict cell reaches at least 7/8 exact, 8/8 tool correct, and slot micro-F1 at
   least 0.90, with at least three exact saves and zero exact harms against its no-schema parent.
5. The oracle exceeds the best fixed strict cell by at most one exact row. A larger gap means the
   routing problem remains unresolved.
6. If both strict cells qualify, prefer the simpler registry cell unless the handbook cell has at
   least two paired exact wins and zero harms against it.

Fixed eight is a high-bar mechanism falsification screen, not a generalization or confidence-
interval study. A pass opens only a separately preregistered OpenJiuwen AgentLoop integration on a
different identity-frozen discovery support roster. That successor must demonstrate a paired exact
gain over single-call and trace separate OBS/ORG/SUPPLY/USE information gain. Vowpal Wabbit remains
closed until the AgentLoop passes.

If schema repairs syntax or hard validity but not the oracle/fixed-arm exact gates, record a
syntax-only result and stop. Expand task-wide canonicalization knowledge only if the post-seal error
partition shows a missing representation that cannot be expressed by the current public types,
constraints, and aggregate-supported compatibility forms. Do not tune a sample-specific prompt,
schema, threshold, or candidate list on these eight rows.

## Training-free control boundary

No RL implementation is part of this experiment. If later gates open policy fitting, the production
controller remains the pinned upstream `vowpalwabbit==9.11.2` `cb_explore_adf` implementation. Local
code is restricted to context/action rendering, propensity logging, reward joins, artifact hashing,
and OpenJiuwen integration. It must not implement a repository-owned learner, optimizer, value
update, or action-scoring algorithm. The performance target above 0.90 applies after that external
policy on held-out discovery/validation data, not to admission of the engineering baseline.
