# Audio2Tool registry-semantic reward memory v2 — preregistration

Date: 2026-09-01. Status: **REGISTERED BEFORE DOMAIN/CATEGORY-RETURN REPLAY**.
Experiment: `SAEA-A2T-MF-TFRL-REGISTRY-SEMANTIC-MEMORY-V2`. Machine contract:
`configs/experiment/a2t-training-free-registry-semantic-memory-v2.json`.

## Why one successor is admissible

V1 established a real signed action surface and a live structural state, but not a usable policy.
Seven saves and 31 harms occupied the same coarse single-call/exact-schema cell; adding arity and
provided-key counts still left seven saves with 18 harms. Relaxing the frozen support, save, or
zero-harm memory rule would be result-facing threshold tuning and is prohibited.

The deployment registry already exposes two semantic abstractions for every selected tool row:
`domain` and `category`. V2 changes only the state representation by appending those fields. It does
not change the population, rewards, actions, supply, default, memory thresholds, folds, promotion
gates, or candidate selection. No domain/category-to-return relation has been read before this
registration.

## Frozen semantic state

`domain-category-coarse-v2` appends the sorted unique set of `(domain, category)` pairs belonging to
the A0-selected calls to the v1 coarse state. `domain-category-detailed-v2` appends the same pair set
to the v1 detailed state. Sorting and deduplication make multiple-call state independent of call
order and duplicate calls. Missing registry metadata becomes an explicit unresolved class.

Tool name, tool description, argument values, transcript, spoken query text, tier, sample/group
identity, gold, correctness, supplied response, reward, and future turns remain forbidden. The
fields used are present in the same deployment registry supplied to the frozen core and are
available before the second-contact decision.

## Unchanged policy and evaluation

The exact-cell reward memory supplies only when the matching other-fold cell has at least five
samples, at least two saves, and zero harms. Every unsupported or mixed-return cell stops. The same
`query_idx` groups, deterministic five-fold assignment, seed 20260901, and 10,000-replicate grouped
CI90 are reused. The v1 memory digest must match
`a17cef81f1746c2b15f6cf6de235e4a182e4eb57bf749d1198e67767bdf81fd6`; outcome and fold
identity drift refuses the replay.

Promotion remains conjunctive: both actions; at least four saves; at most three harms; at least 90%
avoidance of the 36 always-supply harms; at least 50% retention of the eight saves; exact-match net
gain at least three; grouped CI90 lower bound strictly positive; nonnegative gain in every fold; and
positive gain in at least three folds. State needs at least two live classes, dominant share at most
95%, and decisions different from v1's all-stop result.

## Terminal rule for this static surface

A pass only freezes a proposal for a separately registered prospective approximately-100-sample
discovery run. A failure closes further categorical or threshold search on this static 217-row
surface. The next experiment would need a genuinely new runtime observation, such as prospective
direct-response self-consistency, and a new execution plan before any model contact.

This row authorizes zero frozen-core, embedding, tokenizer, HTTP, socket, audio, or GPU contact. The
183 tool-selection failures, unexposed Audio2Tool data, G2, FINAL60, test annotations, and future
turns remain closed.
