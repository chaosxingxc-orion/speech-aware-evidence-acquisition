# DESCRIPTIVE: fixed-policy prefix-slot scheduling on the same20 inputs

Root retains the existing trajectory schedule. Both role-affinity repeats reuse markedly less input and take longer in the generation phase under the unchanged speech-query-prefix-v2 layout. This bounded operational decision does not establish a formal speedup, quality harm, non-inferiority, stable system benefit or learning gain. Independent Solver, Reviewer and Planner text optimization remains available with affinity OFF.

All four members independently finalized20 rows with verified seals and exactly one successful official complete score, zero failed jobs. Root countersigned SAEA-SLURP-PREFIX-AFFINITY-N20-READ-V1 before reading any cache or quality results. There were509 model contacts across80 trajectories. The shared saved-count reader reproduces the official aggregate; this analysis made zero model, tokenizer or scorer contacts and has no optimizer export.

## Complete-system and cache observations

| Schedule | Contacts | Input reuse | Evaluated input tokens | Generation wall (s) | Campaign wall incl. sealing/scoring (s) | Official SLU-F1 (%) | Intent (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| trajectory | 128 | 83.81% | 203944 | 195.68 | 593 | 61.2783 | 70.0 |
| role | 131 | 25.84% | 949857 | 505.81 | 618 | 55.1724 | 70.0 |
| role-aa | 128 | 25.99% | 920950 | 496.49 | 603 | 58.3942 | 70.0 |
| trajectory-aa | 122 | 83.19% | 204554 | 195.50 | 303 | 56.3586 | 75.0 |

Generation time is the FlightRuntime run_phases interval. Campaign time is the preserved driver arm-start to arm-exit interval; it includes preparation, sealing and scoring and has one-second resolution. The trajectory campaign durations593s versus303s vary far more than their generation durations195.68s versus195.50s. Do not attribute that campaign-overhead difference to cache scheduling. The complete driver took2316s including resource admission and transitions.

| Role | Trajectory reuse (%) | Role affinity reuse (%) | Role A/A reuse (%) | Trajectory A/A reuse (%) |
| --- | ---: | ---: | ---: | ---: |
| perception | 63.09 | 63.09 | 63.09 | 63.09 |
| solver | 63.46 | 23.72 | 23.80 | 61.57 |
| reviewer | 96.78 | 23.53 | 23.62 | 96.84 |
| planner | 94.93 | 22.83 | 22.90 | 94.91 |

The two role schedules evaluated949857 and920950 input tokens, versus203944 and204554 under trajectory scheduling. All509 contacts have observed token and timing metadata. Reuse is measured from preserved response counters, not inferred from final cache residency. The actual served slot is unavailable in these responses; requested-slot custody is preserved. First-contact reuse is not a cold-cache measurement: no cache flush or server restart occurred.

## Quality guards and the own repeats

| Right minus left | Natural-mixture SLU delta (pp) | Paired95% CI (pp) | Intent delta (pp) | Equal-scenario SLU delta (pp) | Equal-scenario intent delta (pp) |
| --- | ---: | --- | ---: | ---: | ---: |
| trajectory__role | -6.1059 | [-22.0162, 6.8173] | +0.00 | -4.0278 | +0.0000 |
| trajectory-aa__role-aa | +2.0355 | [-4.7838, 9.2067] | -5.00 | -2.4821 | -7.6923 |
| trajectory__trajectory-aa | -4.9196 | [-18.4154, 4.0874] | +5.00 | -1.5457 | +7.6923 |
| role__role-aa | +3.2217 | [0.0000, 10.2564] | +0.00 | +0.0000 | +0.0000 |

The role-versus-trajectory SLU point estimates reverse sign between repeats. All natural-mixture contrasts include zero; own-repeat differences are substantial. These20 previously exposed optimization inputs cannot establish quality benefit/harm or a no-harm admission. Sparse one-row scenario strata can produce degenerate bootstrap intervals; their zero width is not strong evidence. Repeats are not pooled into40 independent inputs.

All four members have20/20 admitted terminal outputs, zero context-compacted rows, zero knowledge-tool calls and zero illegal Planner routes. The existing final normalizer changed2/3/2/1 rows in trajectory/role/role-aa/trajectory-aa order. One role result used its existing r-action normalization branch; retain this engineering detail without attributing task quality to it.

## Complete scenario support and descriptive values

Cells report official pooled SLU-F1 / intent percentage. Both repeats use the same20 rows. No scenario is a decision unit.

| Scenario | n | Trajectory | Role | Role A/A | Trajectory A/A |
| --- | ---: | ---: | ---: | ---: | ---: |
| audio | 3 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 |
| cooking | 2 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 |
| email | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| general | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| iot | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| lists | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 |
| music | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| news | 1 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 |
| play | 2 | 73.03 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 57.14 / 100.00 |
| qa | 2 | 62.75 / 100.00 | 58.54 / 100.00 | 58.54 / 100.00 | 58.54 / 100.00 |
| recommendation | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 |
| social | 1 | 41.79 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 41.79 / 100.00 |
| takeaway | 1 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 |

## Interpretation and next action

The source-defined ordering places variable query speech before the contact-instruction history suffix. Trajectory affinity preserves one sample's speech and supplied evidence across its roles; assigning one slot to each role switches that role across different queries and loses much of that shared prefix. The observed token counters support this explanation. Scheduling also changes concurrency and numerical batching, so this panel does not causally separate queueing from recomputation. It is not a test of relocating invariant node instructions ahead of the query.

Keep the current trajectory schedule for the learning panel. Continue independent node text and post-call optimization through the separately admitted typed-successor2 proposals. A future node-static-prefix layout must be registered as a distinct request-semantics factor and pass capacity, structural and complete-family checks; do not edit the flown workers or silently activate that layout. Do not export this scheduler panel to either optimizer branch.

The four-proposal Windows task was separately admitted/launched at11:15:35Z; its current outcomes are not part of this read. The SLURP30-minute heartbeat remains PAUSED, while independent10-second resource telemetry continues. Preserve owner227 review before8x400 and every other-carrier hold.

## Evidence

- Root qualification: ../receipts/continuation/2026-10-03-prefix-affinity-n20-family-qualified.json
- Preregistered recipe: ../readiness/2026-10-03-slurp-prefix-affinity-n20-v1/analysis-recipe-v1.json
- Hash-bound outputs and exact source addresses: ../receipts/continuation/2026-10-03-prefix-affinity-n20-scientific-read.json
