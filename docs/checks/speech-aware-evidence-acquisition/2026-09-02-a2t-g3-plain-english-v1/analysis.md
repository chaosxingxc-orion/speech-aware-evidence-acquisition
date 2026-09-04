# Audio2Tool G3 plain-English ground analysis

## Decision

G3 does not qualify the plain-English ground and does not open a larger run. The matched AgentLoop
improves parse reliability and tool selection, but it does not improve strict exact match over the
single-call M0 baseline. The matched-versus-shuffled exact effect is also below the preregistered
information-gain gate and its grouped 90% confidence interval crosses zero. The fresh 88-sample
reserve, larger discovery populations, test data, and training-free policy fitting remain closed.

The terminal offline result is
`/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-A2T-G3-PLAIN-ENGLISH-V1/flight-20260902T182038Z/result.json`,
SHA-256 `d5c6ed5393d3119516420942827cc751add03edaf9d61a88ac6baf50336c0d01`.
The terminal flight receipt SHA-256 is
`fccf51a91eed259f3bdad06f3bcbfd26f65972a356b955774485eed77053ee86`.

## Official results

| Arm | Parsed | Exact | Correct tool | Slot micro-F1 |
| --- | ---: | ---: | ---: | ---: |
| M0 single call | 35/40 | 8/40 | 21/40 | 0.333333 |
| Matched AgentLoop ground | 40/40 | 8/40 | 27/40 | 0.354839 |
| Shuffled composite, 40 rows | 39/40 | 7/40 | 24/40 | 0.250000 |

Matched minus M0 has four exact wins and four exact losses, for zero net exact gain. Tool selection
has eight wins and two losses, for a net gain of six. The grouped 90% interval for the exact effect
is `[-0.125, 0.125]`.

On the preregistered selected 16 rows, matched scores 2/16 exact and 11/16 correct tool, while
shuffled scores 1/16 exact and 8/16 correct tool. The paired exact outcome is two wins, one loss,
and thirteen ties, for a point gain of one. Its grouped 90% interval is `[-0.125, 0.25]`. This fails
both the at-least-five-exact gain requirement and the positive-lower-bound requirement.

Matched exact counts by tier are 3, 1, 0, 0, 1, 2, 1, and 0 out of five. No tier reaches the
required four exact rows. The global ground gates for exact, tool, and slot quality all fail; only
the parse gate passes.

## Mechanism diagnosis

The detailed retrieved cards contain the gold tool on 37/40 samples and 52/55 gold calls. The
complete 152-tool name index contains the gold name on every sample. Of the 32 matched rows that
are not exact, 30 already contain their gold tool in the detailed cards. Candidate existence is
therefore not the primary limitation.

The 32 failures have the following mutually exclusive primary diagnoses:

- 18 rows select the correct tool but fail exact argument realization: nine omit required defaults
  or fields, four add an incorrect field, four encode a value or type incorrectly, and one exposes
  a registry-versus-gold field-name conflict.
- Nine rows receive the gold card but USE selects the wrong tool or omits an intent.
- Four rows have materially damaged task-blind observations, concentrated in multiturn and blended
  requests.
- One row lacks the gold detailed card.

The card builder renders no source utterances and no row-level argument values. It projects
construction knowledge into generalized tool descriptions and tier-conditioned key patterns, but
runtime does not expose a trustworthy tier label. The model must therefore infer tool choice,
argument inclusion, defaults, value types, corrections, and multi-intent ordering from a broad
packet of 32 cards plus a 152-name index. The packet contains knowledge, but not a sufficiently
executable representation of that knowledge.

Five matched hard-validity repairs produce zero official-score contribution: four final texts are
unchanged and one change leaves the scored outcome unchanged. Seven repairs occur in the shuffled
arm. Automatic repair should be disabled in the successor unless a new offline analysis identifies
a deployment-visible failure class with positive utility.

## Reachability audit

A conservative offline audit separates knowledge failure from impossible rows. Across the 55 gold
calls, public registry semantics plus speech or task-blind OBS fully determine 23 calls. Another 23
require aggregate English construction rules, seven conflict with the public schema, and two have
runtime audio or observation evidence inconsistent with the expected task. At the sample level,
the strict public-registry ceiling is 16/40 exact. Legal aggregate construction rules raise the
ceiling to 33/40. Training-partition compatibility rules for recurring scorer-effective conventions
raise the legal ceiling to 37/40 without rendering an evaluation label, sample ID, source utterance,
or reference transcript. The 36/40 qualification target is therefore reachable in principle, but
not if the public schema is treated as the only executable convention.

Six samples expose public-schema conflicts. Four have recurring support in the non-evaluation
construction partition: Boolean strings for adaptive lighting, nullable valet PINs, and a
`controlPlayback` compatibility signature with `deviceId`, `Mute`, and `Unmute`. Two Tier-8 rows
remain anomalous: one expects `setHapticStrength` with `strength: "Medium"` although the public
schema and all 220 construction units use integer `level`; another expects noncanonical period and
Boolean strings. A subsequent identity audit proves that the third Tier-8 anomaly is not a carrier
binding defect. Its roster, runtime media, packet, request, waveform, and dataset-manifest hashes
all agree. The foreground asks for HRV and a hike while a competing background speaker asks for
always-on display and heart rate; both M0 and OBS lock onto the background. Retain this row as a
foreground-speech-selection hard anomaly rather than repairing or excluding it.

The minimum missing ground is now concrete: construction-specific ordered call skeletons;
conditional device defaults; entity, URL, Boolean, null, list, period, and nested-schedule
canonicalizers; a training-supported compatibility schema; explicit correction and multi-intent
ordering rules; and role-preserving multiturn observation. These are the first G4 knowledge targets.

## Context, batching, and scoring efficiency

The service exposes a nominal 65,536-token context split across two parallel slots, or 32,768 tokens
per slot. Matched prompt-token p50, p95, and maximum are 13,346, 13,799, and 14,594. With the
1,024-token completion allowance, the worst observed request uses 15,618 tokens and retains 17,150
tokens of per-slot headroom. Context length is not the G3 failure mechanism.

G3 phases use fresh requests rather than appending the full Loop transcript. A successor that adds
cumulative state must apply a runtime token budget and bounded state compaction; it must not assume
that a static step-count estimate is exact. The current two-slot server can accept concurrent
requests, but it is request parallelism, not a tensor batch. Inference batching should be enabled
only after a small byte-equivalence and stability check, while preserving one result per sample.

The three official jobs each consume one complete manifest in one unchanged single-process scorer.
Three outer workers finish the batch in 4.396 seconds; the individual job times sum to 11.488
seconds, an effective 2.61-times wall-clock speedup. No dataset shards or shard-score averages are
used. Network jitter is not an engineering-baseline variable.

## Successor hypothesis

The next bounded discovery experiment should test construction exemplars as executable ground,
not widen the card menu. Use a hash-selected, tier-balanced 16-row subset of the already exposed
discovery population, independent of G3 error outcomes. Exclude those rows, the fresh 88 reserve,
and their query-block siblings from every knowledge source.

For each request, retrieve three to five training-side construction exemplars. Each exemplar should
carry an English construction paraphrase, an ordered complete call skeleton, exact public argument
keys, serialization types, and construction-stable defaults. Supply a minimal contrast set rather
than the full 152-name index and 32 generalized cards. For multiturn speech, OBS should preserve
the already available turn and role boundaries and produce explicit current-intent, superseded-
intent, and carried-slot state without using a reference transcript. ORG selects a skeleton; USE
fills values from the original speech and bounded state. The frozen core remains the only answering
model.

The first gate is at least 15/16 exact, 16/16 correct tool, and slot-F1 at least 0.90. Failure expands
or corrects the training-side exemplar and canonicalization ground without opening more samples.
Success permits a separately frozen 40-row run; only at 36/40 exact or better may the untouched
fresh 88 confirmation be considered. Candidate pruning and training-free reward-guided selection
remain downstream of a qualified ground so their action space can later choose exemplar families,
candidate width, observation depth, and stopping without compensating for a broken knowledge base.

## Correction under a2t-scorer-v2 (2026-09-03)

Zero-contact offline re-score of the same three sealed `outputs.jsonl` files (40/40 rows each, v1
identity confirmed to 4 decimals overall for every arm) under the registered `a2t-scorer-v2`
(`analysis.a2t_v2_rescore`, `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/`).

| Arm | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|
| m0 | 0.2000 | 0.5250 | 0.2750 | 0.5000 | 0.5250 | 0.4324 | 0.3333 | 0.8750 |
| matched | 0.2000 | 0.6750 | 0.2750 | 0.6500 | 0.6750 | 0.4144 | 0.3548 | 1.0000 |
| shuffled | 0.1750 | 0.6000 | 0.1750 | 0.5750 | 0.6000 | 0.2679 | 0.2500 | 0.9750 |

Paired contrasts vs. `m0` (v1 and v2, CI90, 10,000 replicates, tier-stratified; a lighter-power
n=40 comparator than this doc's own selected-16 secondary contrast):

| arm | metric | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|
| matched | v1 exact | +0.0000 | 4 | 4 | 32 | [-0.1000, 0.1000] |
| matched | v2 exact | +0.0000 | 5 | 5 | 30 | [-0.1250, 0.1250] |
| matched | v1 tool | +0.1500 | 8 | 2 | 30 | [0.0250, 0.2750] |
| matched | v2 tool (multiset) | +0.1500 | 8 | 2 | 30 | [0.0250, 0.2750] |
| shuffled | v1 exact | -0.0250 | 5 | 6 | 29 | [-0.1250, 0.0750] |
| shuffled | v2 exact | -0.1000 | 4 | 8 | 28 | [-0.2250, 0.0250] |

Exact match ties exactly (m0=matched=8/40 under v1, 11/40 under v2) both scorings; the tool-accuracy
gain for `matched` over `m0` (+0.1500pp, CI90 excludes zero) is unchanged in direction and
significance under v2. This is a diagnostic/mechanism doc, not a promotion decision, so there is no
verdict to reopen; the reading that `matched` gains tool accuracy without a corresponding exact-match
gain (a SELECT/parameter-supply asymmetry) holds under v2 as well.
