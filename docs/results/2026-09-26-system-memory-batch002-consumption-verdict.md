# Memory batch002: consumed guidance, no demonstrated task improvement

## Completion and evidence

All eight selected actors finalized with exactly one official complete score
each: six original actors plus memory-s4-recovery1 and empty-s4-recovery1.
There are four distinct TRAIN inputs, four stochastic trajectories per arm and
32 complete episodes. The original failed memory-s4's eighteen generation
contacts remain excluded from complete learning trajectories and retained as
cost; original empty-s4 remains unstarted. No second recovery is permitted.

This is a construction diagnostic, not an effectiveness, equivalence or
generalization claim. No new model or official-scorer contact was made for
this read. Root personally inspected the actual Reviewer and Planner outputs.

The read was authorized before quality inspection by
`docs/receipts/continuation/2026-09-26-system-memory-batch002-read-authorization.json`,
read-registration-v4 and round-policy-v3. DATA is SPEECHRL_DATA_DIR.

| Derived artifact under DATA/coordination/slurp-system-memory-batch002-v1/read-v1 | File SHA-256 |
| --- | --- |
| batch-read.json | 5b84857927b17f444a569cc9b0528f3597567bd41f93cc07a1a386047ba60327 |
| root-inspection-v2.json | 5d4f140397340afd25fab9cc1da9ebdc358bb05131486d9ac49292d7e9ef2083 |

The shared read entry verifies the whole family before reading quality and
reuses source custody, official feedback, memory exposure and full-trajectory
attribution. Its first derivation had a gold-wrapper adapter error, corrected
with a regression test before the successful second derivation. No raw output
or score changed. Eight reader tests pass; the registered integration covers
92% of the thin entry. The inspection successor fills wire finish-reason and
model-visible prefix diagnostics; the earlier inspection is preserved.

## Complete-system outcomes

SLU-F1 below is reconstructed from the first official score's combined
word/character TP/FP/FN counts, on a 0-100 scale. Slot exactness is a separate,
stricter diagnostic. Each row has the same four input identities.

| Draw | Empty memory SLU-F1 | Provisional memory SLU-F1 | Intent correct, empty / memory | Complete task exact, empty / memory |
| --- | ---: | ---: | ---: | ---: |
| s1 | 51.3211 | 51.3211 | 3/4 / 3/4 | 0/4 / 0/4 |
| s2 | 58.2272 | 58.2272 | 4/4 / 4/4 | 0/4 / 0/4 |
| s3 | 59.7806 | 53.5261 | 4/4 / 4/4 | 1/4 / 0/4 |
| s4, fresh recovery pair | 53.7104 | 53.7104 | 4/4 / 4/4 | 0/4 / 0/4 |
| Arithmetic mean of four roster-level scores | 55.7598 | 54.1962 | 15/16 / 15/16 episodes | 1/16 / 0/16 episodes |

The mean difference is -1.5636 percentage points. It is not a causal estimate
of harmful memory: the only different paired Solver output occurs before the
memory tool is called. The two Perception histories already differ there.
Fifteen of sixteen paired Solver output strings are identical. Every Planner
chooses ACCEPT, no episode revises, and final delivery preserves the first
Solver output. There is no observed memory-mediated final-answer correction
or degradation in these complete trajectories.

Both arms have fifteen correct intents out of sixteen repeated episodes.
The joint cells (intent correct / slots exact) are:

| Arm | Both correct | Intent only correct | Slots only correct | Neither correct |
| --- | ---: | ---: | ---: | ---: |
| Empty | 1 | 14 | 0 | 1 |
| Memory | 0 | 15 | 0 | 1 |

These are repeated episodes on four inputs, not sixteen independent samples.
Do not interpret correct intent as evidence of correct slot extraction.

| Stratum | Distinct inputs | Episodes per arm | Intent correct, empty / memory | Slots exact, empty / memory | Official TP/FP/FN, empty | Official TP/FP/FN, memory |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| news | 1 | 4 | 4/4 / 4/4 | 0/4 / 0/4 | 8 / 20.794643 / 28.794643 | 8 / 20.794643 / 28.794643 |
| takeaway | 2 | 8 | 7/8 / 7/8 | 0/8 / 0/8 | 42 / 10.392308 / 16.392308 | 42 / 10.392308 / 16.392308 |
| datetime | 1 | 4 | 4/4 / 4/4 | 1/4 / 0/4 | 2 / 0 / 6 | 0 / 0 / 8 |

Natural-mixture intent accuracy is 93.75% in both arms; equal-scenario intent
accuracy is 95.8333%. Natural-mixture complete-task exactness is 6.25% versus 0%;
equal-scenario exactness is 8.3333% versus 0%. Weight each row's official counts
by the inverse of its scenario's roster size, then compute micro F1 within
each draw: the four-draw means are 47.3002 versus 44.9589. This weighted
diagnostic is not a second official scoring run and is not a mean of per-row
F1 scores. The natural-mixture means remain 55.7598 versus 54.1962 above.
These descriptive weightings do
not create more independent inputs. There are no gold-empty entity sets here,
so this batch cannot assess the empty-target false-positive problem.

## What memory actually did

Both arms perform one successful memory-tool call per episode: sixteen per
arm. Every learned-arm call selects the same second provisional record,
`9a2f7b5e6099b1bf9317b7529ab445a642a30c56cc9b39f36b0b3a3e5410b279`.
The full three-record pack was supplied to the matcher without manual pruning.
Records1 and3 were not returned in these observed decision states. Every
control call returns no records. No other analytical tool is actually called.

The selected record is subsequently exposed to Reviewer and Planner in all
sixteen learned episodes. Actual Reviewer outputs sometimes reproduce its
instruction to trust Reviewer judgment and secure Planner acceptance. Thus
there is evidence of textual uptake, not merely a successful retrieval receipt.
There is still no demonstrated useful task intervention.

Root identifies three observed system failure modes:

1. Advisory authority displaces evidence checking. Some reviews repeat the
   memory's trust/acceptance language rather than inspect missing or incorrectly
   bounded entities. Several speak as Planner before Planner has acted.
2. The tool result is misrepresented. Some learned reviews explicitly claim
   the result was empty despite the verified nonempty returned record. The
   guidance is also treated as if it were evidence confirming the current speech.
3. A missing objection is treated as positive confirmation. Controls also
   accept erroneous drafts after an empty memory result. This shared behavior
   cannot be attributed solely to learned memory or repaired only in one arm.

These observations do not license deleting or rewriting the generated record
by hand. Source validity, structural applicability, textual uptake and useful
credit assignment are distinct. The current provisional candidate remains
semantically unqualified and is not promoted as an effective policy.

## Whole-system feedback and next update

The learned arm has two utility-informative input groups and two utility ties;
three groups contain different normalized answers. One tied group still has
answer disagreement. All sixteen learned trajectories lack revision. Keep
intent and format feedback alongside entity utility; do not discard ties or
mistake within-group variation for the causal effect of memory.

Use the four learned actors in round-policy-v3 for the next batch update;
controls remain diagnostic, not learner samples. Preserve cumulative
construction provenance over batch001 and batch002's eight distinct TRAIN
inputs. The next semantic update must receive actual chronological tool
results, role decisions and final feedback. A proposed lesson must distinguish
an observation from an untested explanation, and preserve NONE when evidence
does not justify a change. Use the existing typed atomic update path, not a
root-authored replacement lesson. The next update is not yet registered.

The owner's intent/slot correction changes the analysis target: examine how
one prediction task helps or damages the other. Candidate coverage is only
a secondary diagnostic. The separate design successor is
`docs/readiness/2026-09-26-intent-slot-task-coupling-design-v2.md`.
The subsequent owner direction also admits a prospective knowledge-construction
optimization design: `docs/readiness/2026-09-26-system-knowledge-rsi-design-v1.md`.
Neither design changes these sealed actors or establishes a successful update.

B1080 matched evaluation and same-roster replication remain pending. No stable
training-free RL gain has been established by this four-input construction.

## Prefixes, capacity and operation

For each input, all eight actors share identical initial Perception task text,
history, supplied evidence, tool schemas and speech packet/features. Seeds
change only through decoding parameters across draws. Runtime request IDs,
provenance addresses and slot assignments can differ; identical seeds do not
make entire multistage trajectories identical. Later contexts retain actual
distinct histories rather than forcing false equality for cache reuse.

The 32 complete episodes use160 model generations,32 local memory dispatches,
eight official scores and no fallback. Wire finishes are128 stop and32
tool_calls; none finishes by length. Model-contact audio totals605.1125 seconds
on15.1278125 unique input seconds. Prompt-token sum is1,318,198, output-token
sum8,195 and summed request latency614.96 seconds; summed latency is not wall
time or utilization-integrated GPU time. The failed eighteen generations and
capacity checks remain additional costs in their original receipts.

| Role | Contacts | Largest prompt | Largest completion | Output limit |
| --- | ---: | ---: | ---: | ---: |
| Perception | 32 | 3660 | 142 | 512 |
| Solver | 32 | 11511 | 58 | 512 |
| Reviewer | 64 | 12730 | 307 | 1024 |
| Planner | 32 | 12685 | 2 | 512 |

Against24576 tokens per slot, even the largest prompt plus its full1024-token
output reserve leaves10822 tokens. This batch shows no output truncation or
context overflow; it does not establish the capacity of larger update contexts.

Operational correction: the server did not remain resident. Its source-bound
stop receipt records resource-guard SIGTERM at2026-09-26T12:09:34Z; all eight
actors nevertheless sealed and completed their single CPU score. The driver
finished at12:14:26Z with exit0. Live checks find no server or driver process.
The stop is `observation-too-old`, with sampled_at1790424574.4449503 greater
than completed_at1790424574.2764623. The guard explicitly rejects backward
wall-clock observations. Windows free24.96GiB and GPU free3706MiB in that
receipt do not indicate memory exhaustion. The clock discontinuity's external
cause is unestablished. Do not describe this as an OOM or retry any actor.
Before a separately registered next GPU phase, resolve clock-safe observation
duration handling without relaxing the resource floors, and launch a freshly
identified service only when that phase is ready. No service was restarted by
this analysis. Retain frozen sources and all original failure/stop receipts.
