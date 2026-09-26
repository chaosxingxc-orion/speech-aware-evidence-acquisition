# First complete-system batch: resource and learning diagnostic

## Status and scope

The first frozen-order four TRAIN inputs have four independent complete-system
replicas each. All 16 episodes sealed; each four-input manifest received one
official score, for four complete scoring jobs. There were 67 generation
contacts. Scientific reading began only after all four closures were checked.
This construction batch proves neither effectiveness nor stable learned gains.
No new DEV/test data was opened, source was rewritten or scorer replayed.

The actor worker remains at d56ad054ad06df36b2a2e508ab5e765cc2549085.
See the source hashes in the read authorization, prefix audit and resource
audit under docs/receipts/continuation/. All large/raw artifacts remain in
the data root. The shared feedback/preparation index is
coordination/slurp-system-batch001-v1/semantic/index.json,
SHA-256 89efe456f7e9a1db246076b8cf0e292b4366bf582a3c80371c954c88b965c31d.

## Distinguish update batch, trajectory sampling and live GPU occupancy

The actor batch contains four inputs, with four full trajectories per input.
Only two episodes run concurrently; each serially invokes Perception, Solver,
Reviewer and Planner, including any revision. Sixteen sampled trajectories
are not sixteen simultaneous KV contexts. Likewise, 32 logical TRAIN inputs
would not alone establish an OOM. A 32-input update can nevertheless overload
the later aggregation request, and it has not been admitted.

The observed decoder-only profile uses no mmproj, total 49152 context tokens,
two 24576-token slots and Q8_0 K/V. Resource protection closes admission below
12 GiB Windows available or2048 MiB GPU free; it stops the owned service below
10 GiB Windows or1024 MiB GPU free. The guard is sampled, not an absolute
instantaneous protection guarantee. No cause of an older Windows/CUDA fault
is inferred from this successful short batch.

| Whole actor batch measure | Observed |
| --- | ---: |
| Complete episodes / generated requests | 16 /67 |
| Maximum actual prompt tokens | 10810 |
| Maximum actual completion tokens | 274 |
| Configured output caps | 512 for 50 requests;1024 for 17 |
| Normal stop / length finishes | 67 /0 |
| Resource observations through driver completion | 889 |
| Peak GPU used | 20432 MiB |
| Minimum GPU free | 3706 MiB |
| Minimum actual Windows available | 26.321 GiB |
| Pressure latch in these observations | None |

## Prefix evidence

The same input and comparable role/visit retain identical first messages
across all four samples. Four Perception groups have fully identical messages.
Seeds are decoding parameters, not prompt text. Dynamic role histories remain
independent, preserving system exploration. 65 of 67 actual responses recorded
positive cache reuse. This is not a causal throughput comparison; cache can
also be reused within a trajectory. Do not alter prefixes within a sampling
batch; change the complete frozen policy uniformly at the next boundary.

## Semantic update capacity is the binding limit

Shared production rendering and the resident tokenizer measured all 16 complete
trajectory summary requests. Each retains its actual source; no content was
clipped. Four source fits used nine endpoints each, 36 total, no generations,
no fresh audio and no official scoring.

| Replica source | Actual input tokens for the four inputs |
| --- | --- |
| s1 | 64809,61535,63577,57386 |
| s2 | 99721,65713,58375,63730 |
| s3 | 61593,64318,64178,57559 |
| s4 | 64461,60760,63965,57919 |

Every request exceeds even physical capacity. With 2048 output,3072 operational
reserve and2 special tokens, admissible input is 19454. Decreasing the logical
update batch to one cannot resolve this representation's single-trajectory
size. The longer revision path is the worst measured case.

The first fit registration omitted a required framework snapshot custody pin
and refused before any endpoint. It was preserved as a zero-contact refusal.
The successor bound the existing TRAIN snapshot with evidence still none;
all 16 payloads materialized and passed the strict text-only validator before
contact. The shared independent fit path now also validates that arm and
uses zero speech tokens, matching live phase fitting.62 targeted tests and
nine offline checks passed; source pins, validation limits and the corrected
native-check invocation are documented. The fit success here means successful
measurement and a negative admission verdict, not permission to generate.

## Whole-system learning evidence

Three groups tie on the full official terminal outcome vector. One differs
in entity FP/FN and intent correctness; all four original groups remain in
construction lineage. One group is not enough to infer a population rate of
informative exploration or choose a winning policy.

In the informative group, all four trajectories contain Reviewer text that
claims a tool call or result, but the complete records contain zero actual
tool events. In one replica, this unsupported account prompts Planner to
request revision. Solver changes the initially correct intent to an incorrect
one. The subsequent Reviewer text prefers the earlier interpretation, but
Planner accepts and the delivered Solver answer remains incorrect.
This is a concrete cross-role failure path. It does not prove a causal effect
of Reviewer alone: roles, earlier candidates and sampling jointly vary.

The incorrect-intent replica and two correct-intent replicas have equal
entity utility 0.762633706506171. Intent remains a separate official feedback
field. An entity-only scalar therefore cannot stand for full system quality.
Do not discard that field, label a model's claimed tool output an actual tool
observation, or manually insert a rule from this audit into learned memory.

## Next registered work

1. Produce a compact, versioned complete-trajectory view. Share repeated
   contexts with explicit references and verify reconstruction against actual
   source inputs/outputs. Keep ordered observations, model responses, actual
   tool events, revisions and final delivery. Preserve original records.
2. Fit every real request again with the same adequate output allowance.
   If lossless organization is insufficient, explicitly register hierarchical
   summarization as an algorithm adaptation. No silent truncation, convenient
   subset, guessed token counts or unmeasured context enlargement.
3. Complete the real summary/comparison/proposal/consolidation sequence,
   preserving terminal entity counts, intent, format and complete provenance.
   Freeze its actual memory output before the next actor batch.
4. Use the prepared next disjoint four inputs and shared multi-cell campaign,
   overlapping one scorer with independent generation. Keep actor policy and
   prefixes fixed within each batch; update only after its complete scoring.
5. Assess learned memory through frozen full-system evaluation and matched
   controls/replication on the already planned complete roster. Do not present
   this construction diagnostic or engineering repair as an RL improvement.
