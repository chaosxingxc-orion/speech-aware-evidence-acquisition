# Audio2Tool SELECT/FILL 104-Row Flight — Recovery V5 Preregistration

Status: **REGISTERED BEFORE ANY RECOVERY-V5 MODEL, EMBEDDING, TEMPLATE, TOKENIZER, SCORER, OR GOLD CONTACT**  
Execution profile: `bounded-discovery-probe`  
Generation run: `SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5`  
Embedding-tool run: `SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5-EMBED`

## Predecessor boundary

Recovery V4 mechanically recovered the immutable V2 M0 and OBS prefix, completed exactly 104 local
transcript embeddings in four physical batches, and persisted a complete K=32 checkpoint. It then
sent 33 JOINT requests before one response failed the detailed parameter `oneOf` response schema.
OpenJiuwen propagated that response-validation exception across the whole phase. JOINT was aborted at
33 contacts and 96.654458 referenced speech-audio seconds; SELECT, REVISE, and FILL made zero
contacts. No response meaning, gold, reference transcript, scorer output, test annotation, or future
turn was opened. The V4 failure receipt SHA-256 is
`424bdc6d485710d8725e9be2a271d6933c677063da85cccd54e04ef72e25eea2`.

V5 uses fresh run, mission, and attempt identities. It does not reuse any V4 response or vector.
V4 remains immutable failure evidence. V5 mechanically rehydrates only the exact V2 M0 and OBS
prefix already bound by Recovery V4, repeats one local 104-item embedding pass in four physical
batches, and creates a new K=32 checkpoint before generation.

## Scientific repair and workflow comparison

The V4 stop exposed a measurement defect: public parameter correctness was enforced as a fatal
runtime invariant instead of being measured by the official scorer. V5 keeps the full English public
tool contracts, legal key skeletons, types, constraints, defaults, omission rules, and canonicalizers
in the supplied ground, but narrows constrained decoding to output structure:

- JOINT and REVISE must return one to seven exact `{name, arguments}` objects. `name` is restricted to
  the sample's K=32 candidates and `arguments` must be an object, but its keys and values are not
  constrained by the decoder.
- SELECT retains its argument-free ordered tool-name schema over the same K=32 candidates.
- FILL must preserve the exact SELECT occurrence count, order, multiplicity, and tool names. Each
  `arguments` value must be an object, but its keys and values are not constrained by the decoder.

The official scorer therefore observes illegal, missing, extra, mistyped, and wrong-valued parameters
as model errors. The stronger public-key-bounded schema is excluded from this primary flight because
it would remove a parameter-error class before measuring whether the specialized parameter ground
provides information gain. It remains a possible later preregistered ablation if illegal keys dominate
the sealed FILL errors.

The answer arms remain recovered speech-only `DIRECT_M0`, one-contact `JOINT_ONE_CALL`, two-contact
`JOINT_DRAFT_REVISE`, and two-workflow `SELECT_THEN_FILL`. REVISE receives the exact canonical JOINT
draft. FILL receives only the canonical SELECT occurrence state and selected-tool parameter ground;
it cannot change selected names, order, positions, or multiplicity. Split versus equal-contact joint
revision remains the primary causal comparison. Split versus one-call JOINT and direct M0 remain
secondary comparisons.

Implementation commit `65c86bb2a64672b22d44d10532e84c333ed6f3b5` carries coordinator SHA-256
`3709fb725f3f9b0976c5fbff49c3669334dc0799ab30dfb216ad9e4fd06a2239`, runtime-factory SHA-256
`16982ec54d94526d564c7a06f91d12886e45ea3c1d59e26212a545e2ca2153a3`, and protocol-config
SHA-256 `b371cb64d01b3cff82b585a29af100b27b21252cd77f8cc74751133708ad86de`.
The expanded focused suite passes 140 tests and Ruff passes. The launcher now closes opened attempts
for any escaping ordinary framework exception; interruption semantics remain outside that catch.

## Frozen population, capacity, and exposure

V5 preserves the original fresh 104-row discovery roster: 13 rows from each of eight task tiers,
549.489916 referenced speech-audio seconds per pass. The frozen Qwen3-Omni core, local Qwen3
embedding model, dense K=32 retrieval, prompts, knowledge assets, temperature-zero decoding, two
generation slots, queue depth four, and official scorer remain fixed.

V5 authorizes exactly 416 new frozen-core contacts: 104 each for JOINT, SELECT, REVISE, and FILL.
The conservative generation ceilings are 3,400 speech-audio seconds and 4.0 GPU hours. The embedding
ceilings are 104 logical text items, four physical requests, one schema-required conservative audio
second, and 0.2 GPU hours. No retry, repair, resend, response substitution, fallback, network-jitter
study, test use, training-free policy fit, approximately-1,000-row expansion, Stage-3 work, or paper
claim is authorized.

Generation uses a physical 32,768-token context per slot. Each exact request is admitted against a
24,576-token operating cap, retaining 8,192 tokens of reserve. Every physical variant in a phase must
pass live template, grammar, tokenizer, speech-token, and completion checks before that phase sends.
Prompt size is remeasured after every workflow boundary. Generation requests remain individual;
only local embeddings use batches.

## Sealing, analysis, and decision rule

Seal and verify complete JOINT and SELECT predecessor states before materializing REVISE or FILL.
Seal exactly four complete answer manifests before opening response meaning, gold, or scorer output.
Score each whole manifest once with the unchanged official single-process scorer, using at most four
outer workers. Never shard a manifest or average shard metrics.

Report exact match, tool accuracy, slot micro-F1, parse rate, all eight tiers, prompt tokens, realized
contacts, and wall time. Exclude network jitter from efficacy. Assign agentic errors in the fixed order
`SUPPLY`, `SELECT`, `FILL`, or `SUCCESS`; report selector order/multiplicity accuracy, conditional FILL
accuracy when SELECT is correct, and illegal-key frequency. For every primary and secondary paired
contrast, report saves, harms, ties, exact sign tests, and 10,000 tier-stratified bootstrap replicates
with seed 20260903.

Promote workflow separation only if its lower 90% exact-match bound is above zero against both joint
controls, its tool and slot effects are nonnegative against both, exact match improves over M0, and no
tier has more than one net exact loss. Beating only one-call JOINT is additional-inference evidence,
not decomposition evidence. Predominant SUPPLY errors return work to knowledge construction. High
reachability with weak SELECT returns work to routing supply or use. Correct SELECT with weak FILL
returns work to selected parameter supply or use.

This engineering baseline is not required to exceed 0.90. That target applies only after a separately
preregistered training-free RL stage using deployment-visible state and preferentially reusing pinned
upstream `vowpalwabbit==9.11.2` `cb_explore_adf`. V5 opens no test split, policy fit, or scale
expansion.
