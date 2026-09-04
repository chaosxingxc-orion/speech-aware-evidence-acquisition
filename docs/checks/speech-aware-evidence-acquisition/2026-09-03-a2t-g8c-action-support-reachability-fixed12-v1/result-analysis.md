# G8C fixed12 result analysis

## Decision

G8C fails the preregistered action-set reachability gate. The best post-score oracle remains at
4/12 exact match and 0.5116 slot micro-F1, exactly matching the single-call branch on both answer
metrics. It improves only tool accuracy from 10/12 to 11/12. The current AgentLoop action set does
not beat a single frozen-core call and supplies no demonstrated answer-level information gain.

This result does not require an engineering baseline to exceed 0.90. The owner target above 0.90
applies after training-free RL. The oracle is only a necessary ceiling test: because the best
available action cannot improve any single-call miss, an upstream Vowpal Wabbit policy cannot
create the missing answer action. VW fitting and the approximately-100 scale remain closed until a
new action construction clears the reachability gate.

## Official results

| Branch | Exact | Tool accuracy | Slot micro-F1 | Parse failures |
|---|---:|---:|---:|---:|
| `STOP_M0` | 4/12 = 0.3333 | 10/12 = 0.8333 | 0.5116 | 0 |
| `EXHAUSTIVE_G7` | 1/12 = 0.0833 | 7/12 = 0.5833 | 0.1951 | 0 |
| `SUPPORT_ONLY_RESOLVE` | 0/12 | 0/12 | 0 | 12 |
| `DECOMPOSED_SELECT_BIND_RESOLVE` | 1/12 = 0.0833 | 9/12 = 0.7500 | 0.2632 | 1 |
| frozen four-action oracle | 4/12 = 0.3333 | 11/12 = 0.9167 | 0.5116 | 0 |

Four complete branch manifests were scored once by four outer workers. Each official scorer stayed
single-process over one whole 12-row manifest; there was no dataset sharding or averaging of
shard-level metrics. The oracle reuses only sealed branch bytes, makes zero model contacts, and was
then scored over one complete manifest. Its first process was refused by D3 before scorer or gold
access because an operator-side import created six ordinary `.pyc` files. Those exact generated
files were moved out of the frozen scoring package, and the same unchanged oracle completed one
effective official scoring invocation with bytecode writes disabled. Both the refusal and the
effective result remain retained.

## Counterfactual value of the actions

No agent branch rescues a single M0 exact-match failure.

- Exhaustive produces zero saves and harms three M0-exact rows.
- Support-only produces zero saves and harms all four M0-exact rows.
- Decomposed produces zero saves and harms three M0-exact rows.
- The oracle selects M0 for 11 rows and decomposed once only because tool accuracy breaks a tie;
  that row has no exact or slot improvement over M0.

The action policy is therefore not the limiting component yet. With no answer-superior action in
the logged set, policy optimization can at best learn to retain M0 and reproduce the same 4/12
exact result.

## OBS, ORG, SUPPLY, and USE diagnosis

- OBS marks 11/12 responses valid, but one additional valid-marked response is a refusal. About
  10/12 observations are operationally useful.
- ORG covers all 152 registered tools for every row. Of 1,824 tool assessments, 66 are support, 24
  contradict, and 1,734 uncertain. The 95.1 percent uncertainty rate shows that exhaustive
  organization does not turn registry content into discriminative executable knowledge.
- SUPPLY preserves all 66 support assessments. There is no observed ORG-to-SUPPLY loss.
- SELECT is parse-valid on 12/12 rows and chooses a non-empty set on 11.
- BIND is valid on 9/11 non-empty rows. One response omits a closing array bracket and one violates
  the unfenced-output contract.
- Final resolve exactly preserves the sealed bindings on 10/10 calls. It adds cost but no observed
  semantic repair or drift.
- Among the nine non-empty valid decomposed trajectories, tool accuracy is 9/9 but exact match is
  only 1/9. The dominant failure is canonical argument and value construction after the correct
  tool has already been identified.
- Every support-only response is syntactically valid JSON but uses an unofficial outer schema: seven
  use `tool/tool_input`, two use `id/function/type`, two use `action/parameters`, and one uses
  `action/arguments`. Its 12 parse failures primarily expose an interface-envelope failure.

## Context and batching answers

The active service is configured for 32,768 context tokens; this is the configured service limit,
not a claim about the model architecture's absolute maximum. The operational prompt-plus-completion
cap is 24,576 so at least 8,192 tokens remain reserved. G8C measured every actual request instead
of predicting Loop growth statically. The smallest observed remaining service headroom was 9,193
tokens, so sequence length is not causal in this failure.

Batch execution remains viable when it preserves sample affinity. G8C used two slots, concurrency
two, queue four, and batch two for model work. Evaluation acceleration also worked: four independent
whole-manifest scorer processes ran under four outer workers while every official scorer itself
remained unchanged and single-process.

## Next research move

Run a fresh, disjoint, small discovery screen that separates two missing mechanisms:

1. native JSON-schema or grammar-constrained output with the existing ground;
2. selected-tool canonical execution cards with current decoding;
3. canonical execution cards plus constrained output;
4. the frozen single-call baseline.

Build cards only from deployment-legal registry and pinned open-source or training assets. Include
required and optional keys, enum literals, canonical units, casing, time and device identifiers,
correction precedence, and valid `name/arguments` examples. Do not use sample labels, references,
test annotations, or observed G8C errors to create sample-specific content. The frozen core remains
the only semantic author; structured decoding may enforce only the legal output envelope. Remove
the redundant final-resolve step from this screen because it preserved valid bindings exactly.

Keep the same reachability gate: at least 11/12 exact and slot micro-F1 strictly above 0.90 on the
new small discovery roster. If the combined arm still fails, expand canonical knowledge rather
than prune candidates. Only after an action set clears the gate may a separately registered
approximately-100 experiment fit the already-pinned upstream Vowpal Wabbit policy. The post-RL
target remains above 0.90; no approximately-1,000 or larger expansion occurs until gains are stable.

## Correction under a2t-scorer-v2 (2026-09-03)

Zero-contact offline re-score of the same four sealed branch `outputs.jsonl` files (12/12 rows each,
v1 identity confirmed to 4 decimals overall for every branch) under the registered `a2t-scorer-v2`
(`analysis.a2t_v2_rescore`, `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/`).
The derived post-score oracle branch is not re-scored (it is a frozen selector over these four, not
an independent model contact).

| Branch | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|
| STOP_M0 | 0.3333 | 0.8333 | 0.5000 | 0.8333 | 0.8333 | 0.6111 | 0.5116 | 1.0000 |
| EXHAUSTIVE_G7 | 0.0833 | 0.5833 | 0.0833 | 0.5833 | 0.5833 | 0.2105 | 0.1951 | 1.0000 |
| SUPPORT_ONLY_RESOLVE | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| DECOMPOSED_SELECT_BIND_RESOLVE | 0.0833 | 0.7500 | 0.0833 | 0.7500 | 0.7500 | 0.2857 | 0.2632 | 0.9167 |

Paired contrasts vs. `STOP_M0` (v1 and v2, CI90, 10,000 replicates, tier-stratified):

| branch | metric | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|
| EXHAUSTIVE_G7 | v1 exact | -0.2500 | 0 | 3 | 9 | [-0.4167, -0.0833] |
| EXHAUSTIVE_G7 | v2 exact | -0.4167 | 0 | 5 | 7 | [-0.5833, -0.2500] |
| SUPPORT_ONLY_RESOLVE | v1 exact | -0.3333 | 0 | 4 | 8 | [-0.5000, -0.1667] |
| SUPPORT_ONLY_RESOLVE | v2 exact | -0.5000 | 0 | 6 | 6 | [-0.6667, -0.3333] |
| DECOMPOSED_SELECT_BIND_RESOLVE | v1 exact | -0.2500 | 0 | 3 | 9 | [-0.4167, -0.0833] |
| DECOMPOSED_SELECT_BIND_RESOLVE | v2 exact | -0.4167 | 0 | 5 | 7 | [-0.5833, -0.2500] |

Every branch's exact-match deficit versus `STOP_M0` stays entirely negative (CI90 excludes zero) and
widens under v2, never flips to a save — v2's registry-default/coercion credit accrues more to
`STOP_M0` (a byte composite of `A2T-G1-104`'s own M0 responses) than to any of the three treatment
branches here. Tool accuracy is unchanged for every branch (ordered equals multiset throughout; no
`TOOL_ORDER_ONLY` rows). This is a mechanism diagnostic, not a promotion decision; the doc's
reading that none of the three action variants beats `STOP_M0` holds under v2 as well.
