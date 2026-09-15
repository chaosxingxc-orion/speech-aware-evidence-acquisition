# Released TRAIN A entity-loss diagnosis

Date: 2026-09-14. Model-free descriptive analysis of the complete 1080-row native dual-store TRAIN A anchor. This is not a new experiment, a successor admission, a memory release or an algorithm result.

## Main finding

The saved exact-count audit found 525 correct-intent/nonexact-entity cases: 127 FN-only, 134 FP-only and 264 mixed. The current analysis now joins the already released final predictions with exactly the governed Fold A references, then reuses the shared official-distance attribution API. It verifies all six saved official word/character ingredients, all three exact entity-pair counts and every parse flag per sample. No official scorer is invoked.

The full source reproduces pooled official SLU micro F1 48.53363 percent. The equal-scenario mean of the 18 per-scenario pooled micro values is 46.83639 percent; this is a separate estimand, not the full-cohort pooled micro.

| Official FP+FN loss component | Natural-mixture loss share | Mean of within-scenario loss shares | Samples with this loss |
| --- | ---: | ---: | ---: |
| Residual unmatched reference | 31.49% | 29.05% | 312 |
| Residual unmatched prediction | 28.82% | 32.80% | 300 |
| Same-type filler distance | 35.04% | 33.85% | 246 |
| Heuristic residual type swap | 4.65% | 4.29% | 27 |

The loss-mass columns partition the official FP+FN denominator contribution. Sample counts overlap across categories and must not be summed as a sample partition. A filler disagreement can reflect hearing, span boundaries, normalization, annotation conventions or semantic interpretation; this analysis does not identify which cause applies. Residual type swaps require equal normalized fillers with different types and are only a matching heuristic. Their small share does not bound the total amount of real type confusion.

## Empty-entity behavior

The reference annotation has no entity in 414 of 1080 samples. Of those, 184 (44.44 percent) emit at least one entity, totaling 198 predicted entities. This is an annotation-relative result, not proof that every such word is meaningless or hallucinated. The remaining empty entity outputs are not automatically complete-task successes; one unparsed prediction is retained in this group.

Root subsequently checked the frozen Solver prompt and authored slot contracts. Both already require omission when no supported mention is present and prohibit inventing fillers. The context prompt already says that knowledge is not evidence an entity was spoken. The completed replica additionally shows slot-contract supply in every one of its 2,018 Reviewer requests. Adding those existing instructions or merely exposing the same cards to Reviewer is not a supported remedy. Investigate task-specific annotation boundaries, evidence conflicts and actual correction behavior. Do not use offline gold-empty membership as a runtime trigger, remove these rows or simply request more extraction.

## Priority entity types by attributed loss

| Type | Share of total loss mass |
| --- | ---: |
| date | 10.89% |
| time | 9.15% |
| place_name | 8.46% |
| business_name | 6.30% |
| media_type | 5.62% |
| person | 4.86% |
| event_name | 4.18% |
| food_type | 4.02% |
| device_type | 3.45% |
| list_name | 3.43% |
| business_type | 2.97% |
| order_type | 2.68% |

These are descriptive priorities, not measured returns from a proposed tool. Time/date conventions and value boundaries may need explanatory knowledge; speech ambiguity may justify an on-demand ASR or localized listening observation. Establish the missing information before choosing an intervention.

## Complete scenario view

Each scenario has 60 samples. Report every stratum; do not promote one favorable stratum into the primary task outcome.

| Scenario | Official pooled SLU micro F1 | Surface share | Type-swap share | Unmatched prediction share | Unmatched reference share |
| --- | ---: | ---: | ---: | ---: | ---: |
| alarm | 52.66% | 59.30% | 2.71% | 18.99% | 18.99% |
| audio | 47.75% | 31.45% | 0.00% | 57.13% | 11.43% |
| calendar | 48.38% | 36.41% | 2.23% | 18.97% | 42.40% |
| cooking | 62.47% | 38.06% | 15.48% | 36.78% | 9.68% |
| datetime | 59.52% | 69.64% | 0.00% | 6.39% | 23.97% |
| email | 36.64% | 28.36% | 15.08% | 27.65% | 28.91% |
| general | 15.45% | 8.61% | 0.00% | 73.11% | 18.28% |
| iot | 55.53% | 16.74% | 0.00% | 62.44% | 20.81% |
| lists | 43.55% | 30.57% | 3.86% | 48.21% | 17.36% |
| music | 34.53% | 16.08% | 0.00% | 59.94% | 23.98% |
| news | 44.24% | 31.00% | 10.35% | 22.42% | 36.22% |
| play | 46.82% | 40.44% | 10.36% | 27.19% | 22.01% |
| qa | 57.04% | 46.53% | 3.69% | 35.03% | 14.75% |
| recommendation | 49.75% | 19.79% | 3.41% | 18.77% | 58.03% |
| social | 34.74% | 25.66% | 5.51% | 35.79% | 33.04% |
| takeaway | 48.84% | 35.97% | 2.33% | 13.97% | 47.73% |
| transport | 51.34% | 42.67% | 2.29% | 13.76% | 41.28% |
| weather | 53.81% | 32.04% | 0.00% | 13.87% | 54.09% |

## Custody and limits

All 1080 rows and all seven unparsed final predictions are retained. The loader materializes only the requested real TRAIN recording IDs and refuses missing identities. It additionally validates selected audio headers and hashes audio bytes; there is no audio decoding, encoder, ASR, model, tokenizer or GPU observation. Fold B and current replication outcomes are not analyzed. Only numeric/categorical row diagnostics and aggregate type/scenario tables are persisted; no reference or predicted filler or sentence strings enter the derivative.

Use the existing root-quality-release-v1.json for this complete TRAIN source; its SHA-256 is 0be030c3d4d43bd27035575ff455cf30830d042b5f35d3ab6b83ff69ecc43bdf.

Recipe: docs/readiness/2026-09-14-slurp-train-a-entity-loss-attribution-v1.json, SHA-256 ba6de73b0bd232be1b3206894b28f58f4039d69b8d642ae46f7524225bcb1f94.
Artifact: DATA/analysis/SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1/entity-loss-attribution-v1.json, SHA-256 10d2cf3c33d040872464dc980b1dc3a7ef642935da761cc6be8f2d0ffa077bb6.
Completion: DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-recovery-v1/entity-loss-attribution-completion-v1.json, SHA-256 75c4315c98593817b6123810b87363f505617613e088fddb65f6bef308b8dd6a.

Shared analysis API: analysis.slurp_entity_attribution.attribute_parsed_rows. The recipe pins the governed loader, parser and attribution source; completion additionally binds the actual code commit and helper sources. This diagnostic does not reopen the twice-failed dynamic tool/refresh flight or attribute system gains to any individual component.

## Root source review update

The omission/preservation rules are present in configs/probes/slurp_native_role_solver_v2.txt and slurp_native_role_context_v3.txt, and in the released authored-slot-contracts-v1.json. The Reviewer visibility finding comes from the separately released complete replication, not from a fresh TRAIN-label read. Distinguish rule availability from successful use. The priority-type table is sorted by measured loss mass; the earlier alphabetical excerpt did not rank loss priorities. The numeric attribution artifact remains unchanged.
