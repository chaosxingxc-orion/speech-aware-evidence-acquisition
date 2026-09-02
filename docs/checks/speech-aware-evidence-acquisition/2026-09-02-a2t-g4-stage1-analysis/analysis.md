# Audio2Tool G4 Stage-1 executable-microground analysis

## Decision

Neither `E` nor `SE` passes Stage 1. Both arms score 16/16 parsed, 1/16 exact, 6/16 correct
tool, and four correct slots out of 21 expected. Their slot micro-F1 values are 0.186047 and
0.195122, respectively. Both exact contrasts against frozen `C` have one win, two losses, thirteen
ties, and net -1. The fixed remainder 24 therefore stays closed. Fresh 88, test, future turns,
scale, candidate pruning, and TFRL evaluation also stay closed.

The dominant failure is the candidate route. The complete frozen 152-card corpus contains every
gold tool and admits every gold argument-key skeleton on 16/16 rows, but each bounded route supplies
all gold tools on only 7/16 rows. `E` and `SE` miss the same nine rows. This is a legal-corpus
coverage result, not evidence that the model can reach 100% exact: the present corpus deliberately
contains no task-specific concrete values and the observed USE failures still include defaults,
canonicalization, nested schema, and value typing.

The machine-readable companion is `analysis.json` in this directory.

## Evidence and analysis boundary

The official scoring directory is
`/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-A2T-G4-STAGE1-SCORING-20260902T210300Z`.
The sealed `E` and `SE` manifest SHA-256 values are
`75550a28f3efc9b495ca60f06f88f506a0ac2c7d432cee936f07b61b008373c3` and
`69afd80f710eea8c2636e9646df5133f88c41b3ced9c7a33c10559d2e38b0032`. The official score-file
SHA-256 values are `2b31e1f8c2f20374f410cd8dcb76e3e97460d9c27cf25322570f642950ee90c2`
and `83df3fe26ef4381d98d094dc67a42db55e90cc15443934a924771aa951774af8`.

The official score files intentionally retain aggregates. After both jobs settled, this analysis
used the G3-established read-only post-score pattern: apply the frozen parser, gold loader, and
item-score functions inside offline analysis, require the reconstructed aggregates to equal the
official artifacts exactly, and retain only the selected 16 rows. It launched no official scorer
job and made zero model, network, tokenizer, retriever, or new data-split contact. It read the
already authorized outputs, agent traces, route packets, and SE state receipt. It did not read or
score remainder 24, fresh 88, test, future turns, or any TFRL evaluation surface.

## Absolute and paired results

| Arm | Parsed | Exact | Correct tool | Slot TP / expected / predicted | Slot micro-F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Frozen `C` | 16/16 | 2/16 | 11/16 | 7 / 21 / 22 | 0.325581 |
| `E` | 16/16 | 1/16 | 6/16 | 4 / 21 / 22 | 0.186047 |
| `SE` | 16/16 | 1/16 | 6/16 | 4 / 21 / 20 | 0.195122 |

| Contrast | Exact W / L / T / net | Tool W / L / T / net |
| --- | ---: | ---: |
| `E-C` | 1 / 2 / 13 / **-1** | 0 / 5 / 11 / **-5** |
| `SE-C` | 1 / 2 / 13 / **-1** | 0 / 5 / 11 / **-5** |
| `SE-E` | 0 / 0 / 16 / **0** | 0 / 0 / 16 / **0** |

`E` and `SE` reproduce the same single exact improvement over `C`, lose both of `C`'s exact rows,
and lose five of `C`'s tool-correct rows without gaining any tool-correct row. The small SE slot-F1
increase is only a denominator change: SE emits 20 slots instead of E's 22 while retaining the
same four true positives. It is not additional recovered information.

## Per-tier results

Every tier contains two rows and every arm parses both rows. Cells show exact / correct-tool count
and slot micro-F1.

| Tier | `C` | `E` | `SE` |
| --- | ---: | ---: | ---: |
| Direct | 0 / 1; 0.000000 | 0 / 1; 0.000000 | 0 / 1; 0.000000 |
| Parametric | 0 / 2; 0.000000 | **1 / 2; 0.333333** | **1 / 2; 0.333333** |
| Multi-intent | 0 / 0; 0.400000 | 0 / 0; 1.000000 | 0 / 0; 1.000000 |
| Implicit | 0 / 2; 0.333333 | 0 / 0; 0.000000 | 0 / 0; 0.000000 |
| Needle | 0 / 1; 0.285714 | 0 / 1; 0.333333 | 0 / 1; 0.285714 |
| Correction | **1 / 2; 0.800000** | 0 / 1; 0.000000 | 0 / 1; 0.000000 |
| Multiturn | **1 / 2; 0.500000** | 0 / 1; 0.000000 | 0 / 1; 0.000000 |
| Intent blending | 0 / 1; 0.000000 | 0 / 0; 0.222222 | 0 / 0; 0.222222 |

The multi-intent slot-F1 of 1.0 is not task success: each new arm recovers the only scored slot
while emitting the wrong tool multiset on both rows. This is why the official exact and tool gates
must remain authoritative over isolated slot metrics.

## Structural validity and literal copying

Both arms parse 16/16 under the unchanged parser, including SE's one empty JSON array. `E` has
16/16 nonempty registry-valid rows and 16/16 legal-key rows. `SE` has 15/16 nonempty
registry-valid rows and 14/16 legal-key rows: one response is an empty array, and one
`setThermostatSchedule` response omits `deviceId` even though the frozen card admits only `{}` or
`{deviceId, schedule}`. Neither arm emits an out-of-registry tool name.

Both arms copy the same unmistakable artificial literal once:
`SYNTHETIC_CONTROLPLAYBACK_HOME_DEVICEID_001`. It appears in the registered
`controlPlayback_home` call on the correction row where the route also contains the gold
`controlPlayback` card. Thus the out-of-registry count is zero but the preregistered
zero-synthetic-example-copy gate still fails. A broader lexical-overlap audit finds output values
that also occur in rendered examples on five E rows and four SE rows; those overlaps are not by
themselves proof of copying because public constraint values can also be spoken. The prefixed
literal is unambiguous and sufficient to fail the gate.

## Candidate coverage and failure decomposition

`E` supplies 2-4 tool cards per row, mean 3.25. `SE` supplies 2-8, mean 4.3125. The two candidate
sets are identical on 8/16 rows and have mean set Jaccard 0.688542, but each covers every gold tool
on exactly 7/16. More cards and structured action segmentation therefore do not improve candidate
recall. The same nine route misses span direct, multi-intent, implicit, needle, multiturn, and
blended requests.

The mutually exclusive primary decomposition is identical for E and SE:

| Primary outcome | Rows | Meaning |
| --- | ---: | --- |
| Route miss | **9** | At least one gold tool card is absent; model selection cannot satisfy the registered packet constraint. |
| Model selection miss | **1** | All gold tools are supplied, but USE selects the wrong registered tool. |
| Correct-tool argument realization failure | **5** | The tool multiset is correct, but keys or values are not exact. |
| Exact | **1** | Tool and arguments are exact. |

This separation matters. Candidate recall limits nine rows before USE. Among the seven rows where
the route supplies the complete gold tool set, USE reaches only one exact result; five keep the
right tool but fail arguments, and one chooses a sibling tool and copies its synthetic device ID.
Routing is the largest failure bucket, but widening routing alone is not enough.

On the five correct-tool, nonexact rows, E has one extra-key occurrence, one missing-key
occurrence, and five wrong-value occurrences; one wrong value is also a type error. SE has one
extra key, two missing keys, and four wrong values; again, one is a type error. The recurring
classes are:

- unwanted optional/default fields, including an `enabled` field where the expected call is empty;
- missing default device identifiers;
- lexical canonicalization of URLs and device identifiers;
- Boolean versus Boolean-string compatibility;
- nested schedule shape, day-key, clock, and temperature serialization; and
- sibling compatibility-tool selection, coupled here with direct copying of an artificial value.

These are representation classes, not row-specific repair targets. No conclusion in this analysis
licenses tuning a route, prompt, default, or canonicalizer to these 16 identities.

## What structured state contributed

SE state is a deterministic re-expression of E's already sealed English observation. It preserves
surface text, adds normalized duplicates and action-segmentation fields, and introduces no new
speech, label, reference, tool, or value source. Empirically:

- candidate sets change on 8/16 rows, but full-gold candidate coverage remains the same 7/16 and
  the route-miss identities are identical;
- output bytes change on 9/16 rows, but exact and tool outcomes are tied on all 16;
- slot true positives remain four, while SE emits two fewer predicted slots;
- SE consumes 26,899 prompt tokens versus E's 19,988, an increase of 6,911 or 34.58%; and
- SE latency is 24.7691 seconds versus 21.3638, an increase of 3.4053 seconds or 15.94%.

SE therefore adds organization and formatting, not task information. Its changed formatting has
no exact or tool utility in this screen and creates the only two structural-invalid rows. Because
there is no state-only arm, this is not an interaction estimate; it is the narrower observation
that the registered SE transformation supplies no measurable correctness gain over E.

## Can the legal ground reach 90%?

At the tool-and-key-skeleton level, yes. The complete frozen corpus contains every gold tool and a
legal argument-key set for every gold call on 16/16 selected rows. A model-usable supplier that
preserves the relevant full schema bundle can therefore clear a 90% candidate-ground criterion in
principle. The current BM25 microground cannot: 7/16 coverage is 43.75%.

At exact-call level, this experiment does not establish a 90% ceiling. The full corpus intentionally
renders no evaluation values, source utterances, or concrete construction values. The five
correct-tool failures show that key-set availability is not the same as executable realization.
The earlier G3 legality audit found a training-supported compatibility-rule ceiling of 37/40, or
92.5%, across the already exposed pilot, but G4 demonstrates that the knowledge must be supplied
as usable ordered skeletons and canonicalization rules rather than merely existing somewhere in a
corpus. The warranted conclusion is therefore: the legal knowledge source is sufficient for a
credible at-least-90% hypothesis, while this router and packet representation are not.

## Smallest prospective successor

Do not repair these identities and do not open the fixed remainder 24. First run a model-free,
prospectively frozen coverage qualification for a broader supplier on a construction-validation
surface that is disjoint from every evaluation row. For each task-blind English action, supply the
complete relevant schema bundle: every registry tool supported by the deterministic action-to-tool
map, its ordered call skeletons, legal public and training-supported compatibility key sets, value
forms, defaults, and canonicalization rules. Use no concrete evaluation value and no gold-, tier-,
sample-, reward-, or prior-outcome feature. An action-to-tool coverage map is admissible only if
its derivation is runtime-legal, construction-only, pinned, and logged; otherwise use the full
public domain/category bundle and accept its larger width.

Before any model contact, require at least 90% complete tool-set recall on a held-out
construction-validation action set, 100% registry-name validity, 100% inclusion of each candidate's
legal key skeletons, zero artificial concrete literals, and prompt fit for the full unpruned bundle.
Then, and only if an eligible already-exposed non-G4 discovery cohort exists, run one identity-only,
tier-balanced 16-row prospective screen on that cohort. Exclude this selected 16, the closed
remainder 24, fresh 88, test, future turns, and TFRL evaluation space. If no eligible cohort exists,
stop after model-free qualification and request owner direction rather than borrowing a sealed
surface.

The contact gate should remain model-usable and strict: at least 15/16 parsed, at least 15/16 exact,
16/16 correct tool, slot micro-F1 at least 0.90, zero out-of-registry names, zero illegal key sets,
and zero artificial-literal copies. Candidate pruning remains downstream and closed until an
unpruned broader ground clears that gate. This is smaller and more diagnostic than another router
tweak: it first proves that the model actually receives a credible 90% ground, then tests whether
USE can realize it without consuming any protected evaluation space.
