# Canonical family-local action ground design

## Decision

Test an exhaustive family-local canonical action ground before fitting any
training-free control policy. The study must first demonstrate that a frozen
core can place the correct calls in an available action pool. A controller
cannot learn to select an answer that no registered action can produce.

The later training-free control path reuses the pinned upstream
`vowpalwabbit==9.11.2` `cb_explore_adf` implementation. Repository code is
limited to AgentLoop state/action rendering, propensity logging, post-seal
reward joining, artifact hashing, and trace integration. Historical local
memory controllers are not part of the active path. MABWiser remains an
optional macro-router ablation, not a second production learner.

This document authorizes no model, scorer, or test contact. It defines the
mechanism to preregister on a fresh identity-only discovery roster after its
model-free checks are complete.

## Evidence behind the change

The contract-preserving AgentLoop remains the only prior mechanism with clear
answer-level information gain: matched evidence raised exact calls from
32/104 to 40/104, while shuffled evidence fell to 28/104. Later mechanisms
improved parsing or tool identification but did not produce a reliable exact
gain.

The repeated failure is now localized:

- free-form family planning and scanning omit the correct family;
- broad handbooks and the 338-branch global schema create sibling interference;
- support filtering does not supply a sufficiently complete action set;
- select-bind-resolve identifies tools but loses exact argument construction;
- schema enforcement repairs syntax but cannot add semantic information.

The new experiment removes those confounders simultaneously without reusing
evaluation examples.

## Mechanism

Use the frozen 28-family, 152-tool G5 public contract corpus together with the
43 aggregate-qualified, value-free G4 compatibility forms. Derive nothing from
the new roster. For every sample, execute all 28 families independently. Each
family contact receives:

1. the original speech carrier;
2. one bounded same-core English OBS state;
3. one example-free canonical family card;
4. one strict family-local response schema that permits `[]` and only exact
   registered tool/key-skeleton combinations from that family.

The card includes exact operation meaning, sibling contrasts, legal key sets,
public types and constraints, public default-completion semantics, correction rules,
multi-intent rules, and public canonicalization rules. It excludes source
utterances, construction examples, evaluation identities, labels, scores,
reference transcripts, and sample-specific task argument values. Public
registry defaults are retained: they may complete an explicitly requested
operation when speech omits that argument, but they never establish that the
operation itself was requested.

Family contacts do not append one another's prompts. Every contact is rendered
from the bounded OBS state plus one family card. Each factor therefore has a
fixed 28 family-contact count and no unbounded prompt-history growth, although
the number of returned proposal occurrences is dynamic. Runtime must serialize
and measure the exact request immediately before every send and refuse
overflow.

ORG parses each family response locally, preserves raw invalid bytes for that
row, validates every proposed call against its family contract, and merges
legal proposal occurrences without reading gold. This first screen stops at a
sealed proposal pool. It measures whether the knowledge ground contains usable
answer content before candidate reduction or final frozen-core USE is designed.
It is not a deployed agent action and does not authorize a control policy.

## Fixed discovery factors

Use a fixed-eight identity-only secondary discovery roster, one row per
task-complexity tier. Select it from the separately exposed GROUND-QUAL cohort,
exclude every identity used by G5 through G8C and the native structured-action
screen, and do not consume the protected confirmation reserve or proposed
unexposed population.

- `M0_DIRECT`: one frozen-core call with the frozen direct protocol.
- `SCHEMA_ONLY_FAMILY_PROPOSALS`: 28 independent family contacts with the
  strict local action schemas and only minimal family/interface identity.
- `CANONICAL_FAMILY_PROPOSALS`: the same 28 contacts and schemas plus the
  canonical cards.
- `POSTSEAL_PROPOSAL_CONTENT_CEILING`: two zero-contact, gold-informed analyses
  performed only after both runtime factors and traces are sealed. Each may
  select and order sealed proposal occurrences but must not edit tool names,
  keys, types, or values. Exact row reachability is equality to the ordered
  gold call list, including multiplicity. If duplicate occurrences can form
  the same answer, prefer family order and then response index. This is a
  knowledge-content ceiling, never a deployment policy or controller action.

The estimand is incremental canonical-card information conditional on the same
strict family-local action schema. Reusing the same speech, roster, schemas,
decoding parameters, OBS state, merge rules, and sealing procedure keeps card
content as the intended factor. This comparison does not estimate the full
effect of structured output versus native output grammar.

The runtime plan is exactly 58 model contacts per row: one M0 call, one shared
OBS call, 28 schema-only family contacts, and 28 canonical family contacts.
The fixed-eight screen therefore has 464 contacts and repeats 36.936 seconds of
roster speech 58 times. A model-free construction audit must prove that four
calls per family covers every row in the frozen construction corpus before
preregistration. The post-seal ceilings add no model contact.

## Admission rules

The bounded screen is informative only when every planned runtime row is
sealed and the official scorer processes one complete manifest per factor.
Independent complete manifests may be scored concurrently by an outer
launcher. Never shard one manifest or average shard scores. Network jitter is
not an experimental variable and must not trigger retries.

Require all of the following before designing the next disjoint discovery
screen for candidate reduction and genuine frozen-core final USE:

- 8/8 parse validity, hard validity, and legal argument-key sets;
- the canonical proposal-content ceiling contains the exact gold calls on 8/8
  rows and has slot micro-F1 above 0.90;
- the canonical ground has no exact harm relative to schema-only and supplies
  at least one exact candidate-pool save;
- canonical proposal-content exact reachability is the primary semantic
  mediator; tool accuracy and slot micro-F1 are fixed secondary diagnostics;
- the canonical factor must improve exact proposal-content reachability over
  schema-only, establishing information gain rather than format repair alone.

Passing this screen does not open VW. On a new identity-disjoint roster, first
build a bounded hierarchical candidate-reduction action set followed by a
genuine frozen-core USE decision. Its action-set oracle must support greater
than 0.90 exact reachability, and the executed AgentLoop must deliver at least
one exact save over M0 with no exact harm on that screen. Only then may an
approximately-100-row propensity-logged VW experiment open.

The executed AgentLoop baseline is not required to exceed 0.90 before policy
learning. The owner's `>0.90` performance target applies after the open-source
training-free controller. The proposal-content and later action-set ceilings
are feasibility gates, not claims that the baseline already achieves that
score. If either ceiling is below its reachability gate, expand or correct the
knowledge/action construction on a new discovery roster; do not fit VW,
access test, or scale.

## Later open-source control experiment

After proposal reachability and the complete AgentLoop action screen pass,
collect approximately 100 discovery rows with randomized registered
macro-actions and complete logged probabilities. Every macro-action controls
only evidence acquisition, organization, or supply; a non-trivial frozen-core
USE call retains final-answer authority. Use deployment-visible OBS/ORG/SUPPLY/
USE state and action-dependent cost/coverage features. Join the binary exact
reward only after manifest and trace sealing. Fit and select with the pinned
upstream `vowpalwabbit==9.11.2` `cb_explore_adf` implementation on discovery
folds, hash and freeze that artifact, and evaluate it on a disjoint validation
roster. Repository code does not implement a learner. Report exact match as
the primary reward and tool accuracy, slot F1, legality, contacts, latency,
and evidence-use deltas as separate outcomes.

Scale toward approximately 1,000 rows only after stable paired gains over both
M0 and the fixed AgentLoop baseline. Do not optimize prompts, actions,
features, rewards, thresholds, or VW configuration on test data.
