# Audio2Tool training-free signed-supply memory v1 — preregistration

Date: 2026-09-01. Status: **REGISTERED BEFORE PER-SAMPLE STATE/RETURN REPLAY**.
Experiment: `SAEA-A2T-MF-TFRL-SIGNED-SUPPLY-MEMORY-V1`. Machine contract:
`configs/experiment/a2t-training-free-signed-supply-memory-v1.json`.

## Question and boundary

The already-consumed Audio2Tool experiments expose a signed decision surface. Supplying the
A0-selected tool's values-stripped registry row converted eight of 120 tool-correct A0 failures,
but the same supply form regressed 36 of 97 A0 exact matches. The next question is whether a
runtime-legal controller can target that evidence rather than supplying it blindly.

This is a retrospective discovery feasibility screen over 217 already-exposed, gold-selected
samples. It is not representative of the frozen 400 because the 183 A0 tool-selection failures are
outside the action's current support. Gold-defined population membership is never an input to the
controller. A pass may only authorize a separately registered prospective discovery run of about
100 samples. It cannot revise the baseline, open G2, or support a superiority, confirmatory,
generalization, Stage-3, or paper claim.

## Frozen logged actions and rewards

For every eligible sample, `STOP_DIRECT` returns the original A0 response and costs no second core
contact. `SUPPLY_STRIPPED_REGISTRY` makes one second contact with the A0-selected tool row or rows,
rendered through the already-landed `render_b1_tool_schemas` path with `argument_defaults` removed.
The supplied response is Stage-2b B1 for the 120 A0 failures and R1 for the 97 A0 exact matches.

Primary reward is official `exact_match`, recomputed from every stored response through the frozen
Audio2Tool scorer primitives. Tool accuracy, slot F1, parse success, empty-call rate, and second-
contact rate are mandatory secondaries. The two supply sources must prove the same renderer and
must prove that their per-sample supplied tool labels equal the tool names parsed from the original
A0 response. Failure of either identity check refuses the screen.

## Runtime state and forbidden information

State is extracted only from the original A0 response and the deployment registry. The coarse state
contains parse class, registry resolution class, and the relation between provided argument keys and
the selected tool's declared signature keys. The detailed state additionally contains declared
schema-arity and provided-key-count buckets. Signature parsing is deterministic and fail-closed:
an unresolvable signature enters the explicit `unresolved` class rather than being guessed.

The state may not contain gold, correctness, reference transcript, spoken query text, a supplied
response, a future turn, sample or group identity, tier, tool identity, domain, category, or
description. Unit mutation gates must show that changing rewards or gold-side expected calls cannot
change a state signature.

## Frozen reward-memory policy

Two candidates are screened: `coarse-v1` and `detailed-v1`. Both are exact-cell, non-parametric
action-return memories; no model parameter or learned classifier exists. For each held-out query
group, memory is built only from the other four folds. Supply is chosen only when the matching memory
cell has at least five samples, at least two observed `0 -> 1` exact-match saves, and zero observed
`1 -> 0` harms. Every unsupported or ambiguous state defaults to stop.

The receipt's `query_idx` is the isolation unit. All renditions sharing one query remain in one of
five deterministic balanced folds under seed 20260901. `query_idx` is used only for isolation and
bootstrap clustering, never as a state feature. The paired 90% interval uses 10,000 whole-group
bootstrap replicates with the same seed.

## Gates fixed before replay

Every fidelity and promotion condition is conjunctive. The surface must contain exactly 217 unique
eligible A0 rows, 120 B1 rows, and 97 R1 rows; group isolation, supply identity, selected-tool
identity, and gold-mutation invariance must pass. Each candidate must expose at least two live state
classes and no one class may exceed 95% of the population.

The chosen controller must make both actions; save at least four of the eight known always-supply
conversions; harm at most three samples, thereby avoiding at least 90% of the 36 known always-supply
regressions; and obtain an exact-match net gain of at least three over always stop. Its grouped 90%
interval lower bound must be strictly positive. Every fold must have nonnegative net gain and at
least three folds must have positive gain. Among candidates that pass all gates, selection maximizes
net gain, then saved answers, then minimizes second contacts, then uses lexical candidate id.

Failure writes a negative artifact and keeps every unexposed Audio2Tool population closed. Success
freezes a proposal for a new prospective approximately-100-sample discovery experiment; it does not
itself authorize a model contact.

## Spend

This screen authorizes zero frozen-core, embedding, tokenizer, HTTP, socket, audio, or GPU contact.
It reads only already-consumed artifacts and the frozen deployment registry. FINAL60, test
annotations, future turns, G2, and the unobserved Audio2Tool population remain closed.
