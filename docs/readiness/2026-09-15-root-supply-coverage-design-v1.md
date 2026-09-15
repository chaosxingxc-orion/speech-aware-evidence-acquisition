# Root design: coverage before further candidate commitment

This is root's mechanism analysis and bounded next-work specification. It is not a generation registration, a new runtime policy, a causal verdict, or a training-free RL algorithm. Preserve the replicated native SLURP base and the running Audio2Tool comparison.

## Evidence and the named bottlenecks

The released TRAIN Fold A anchor covers 1,080 episodes. Correct intent appears in the initial candidate set in 937 episodes (86.76 percent); 842 of those 937 receive the correct final intent. There are 143 candidate misses and 95 errors despite candidate inclusion. Separately, 525 episodes have correct final intent but nonexact entities. These quantities describe different intervention points.

Actual first-Perception requests contain the own-intent boundary value in 947 episodes. The cross-table is:

| Actual own-intent value supply | Candidate includes correct intent | Candidate misses correct intent |
| --- | ---: | ---: |
| Present | 914 | 33 |
| Absent | 23 | 110 |

Thus 110 of 143 candidate misses occur without the corresponding value in the request. This is observational and confounded by sample difficulty. The 96.52 percent inclusion rate among supplied episodes is not an expected outcome for newly supplied harder episodes. An own-intent value test also does not count useful distinctions mentioned in another intent's value.

The frozen store contains 60 intents and one value per intent. Current Perception selects at most eight using speech-query/key cosine recall and the shared rank/fuse path. Therefore the knowledge exists but often does not reach this node. The first investigation concerns SUPPLY coverage, not an assumption that the knowledge database lacks those labels.

Existing value structure also leaves two concrete opportunities for later study:

- Every intent value has one explicitly authored confusable alternative. That is useful stable content, but not evidence that it explains the alternatives actually competing in a given episode.
- A slot card can contain semantic-role bindings for many intents (up to 40). Candidate-conditioned selection currently supplies the whole released card, including bindings outside the current candidate set. The model must perform the relevance filtering itself.

The second opportunity is about value consumption and relevance. It is not established as the cause of entity errors. Existing cards already contain extraction, format, missing-value and ambiguity guidance; simply adding those same reminders is not a new mechanism.

## Immediate model-free diagnostic

Use only the released TRAIN Fold A cohort, existing sealed query segments and key vectors, and the existing shared recall/rank/fuse implementations. Examine the fixed breadth grid 1, 3, 8, 12, 16, 24, 32 and 60, preserving cosine-only ranking, one value per facet, original segment handling and tie order.

Selection must be computed without reference labels. Join references only afterwards in the offline analysis process. Persist hashes, ranks, aggregate/stratum statistics and Boolean membership, never reference text or per-sample gold intent strings in runtime artifacts.

At breadth eight, reproduce the actual selected qualified-value-ID hash for every episode and the observed 947 own-card-supplied episodes. A mismatch stops the diagnostic; an approximate replay is not enough. Report support coverage, coverage among the 143 candidate misses and the 110 neither cases, knowledge bytes/characters and per-scenario results. Do not call character counts token capacity or report deterministic support coverage as generated candidate accuracy.

The diagnostic distinguishes a narrow selection cutoff from poor ranking deeper in the inventory. Root will use it to specify one prospective system configuration and its matched comparison. The audit cannot establish downstream effectiveness.

## Candidate and value design order

1. Keep the exact working base as an incumbent. Do not make candidate width, knowledge breadth, tool behavior and delivery rules change together.
2. Resolve the supply cutoff question first. If a modest, measurable increase reaches the missing values, test that configured supply change on the complete registered roster with actual-request capacity and full native task scoring. If the missing values remain deep or nonpositive in the ranking, prioritize a better discriminative key/query construction instead of flooding context.
3. Assess generated candidate inclusion separately from support coverage. The owner's 95 percent target applies to the former. More candidates alone cannot recover information the model failed to perceive or consume. Generic parsing accepts wider bounds, but the SLURP provider/projection/analysis path still has three-candidate restrictions; widening must be a coherent shared change if selected later.
4. For later value-consumption work, investigate candidate-scoped explanatory views: preserve shared extraction rules, render semantic-role bindings for the current candidates, retain immutable original cards and bind the derived view to source and configuration. Test the loss of cross-candidate cues and complete-task outcomes before adoption.
5. For later candidate resolution, supply distinctions between the actual alternatives and record the evidence for changing rank one. Current replica decisions rescue 11 rank-one errors while damaging 20 correct rank-one choices. A longer review or an extra contract lookup is not by itself information gain.
6. Reopen no closed tool/refresh flight through renaming. On-demand acoustic tools remain an important system direction, but a reopened family requires a concrete design, engineering evidence and the applicable owner decision.

## Role and optimization workspace

Perception consumes original speech and discriminative knowledge to propose hypotheses. Solver chooses the task answer and consumes candidate-specific explanatory knowledge. Reviewer identifies a specific suspected defect and missing evidence. Planner chooses an authorized continuation or stop. Final answer authority stays with Solver.

A useful future optimization workspace can expose supply selection, candidate breadth, value view, evidence-gap classification, tool choice and revision/stop decisions while retaining complete trajectories and native task rewards. This document does not implement trajectory sampling, relative advantages or policy updates. Those algorithmic steps follow a stable useful system, as directed by the owner.

## Source custody

- Released TRAIN support diagnostic: DATA/analysis/SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1/native-train-support-diagnostics-v1.json, SHA256 214b3e058782703490558c54805541d9722dbafe44f64a5bb1880b16785f9e34.
- Root read release: DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-recovery-v1/root-quality-release-v1.json, SHA256 0be030c3d4d43bd27035575ff455cf30830d042b5f35d3ab6b83ff69ecc43bdf.
- Knowledge structure: DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-recovery-v1/knowledge-value-structure-audit-v1.json. Its store-structure facts apply to the shared releases; its tool/role configuration fields must not be confused with the replicated base's active configuration.
- Factual source inventory: DATA/coordination/slurp-next-agent-base-design-v1/dual-store-source-inventory-v1.md.
- The paired SLURP replica report and frozen native base remain the task-quality evidence. Fold B is not consumed by this work.

Root owns interpretation, mechanism selection and admission. Delegated work is bounded implementation and factual extraction.
