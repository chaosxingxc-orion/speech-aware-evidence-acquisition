# Audio2Tool: ordered candidate-action attribution

Date: 2026-09-15. Root-authored, post-hoc descriptive extension of the sealed
4,000-row native system comparison. This closes the earlier deferred full
reference-action analysis. It creates no new effectiveness test, adoption
decision, model contact or runtime knowledge. The owner GPU hold remains active.

## What changes our understanding

The previous 72.050% figure means the official **primary tool** appears somewhere
in the candidate union. It does not measure coverage of every requested action.
On the same 4,000 samples, all reference tool names are union-covered on 2,663
samples (66.575%); distinct candidate actions can cover every reference occurrence
on 2,624 (65.600%); an order-preserving assignment exists on 2,567 (64.175%).
Strict one-for-one correspondence holds on 2,207 (55.175%). Preserve the original
primary coverage estimate; these are different estimands.

The main current candidate bottleneck is missing tool names. Of 5,417 reference
occurrences, 3,756 have an order-compatible match. The remaining 1,661 decompose
into 1 unavailable-state occurrence, 1,543 absent from the candidate union,
51 lost to distinct-action capacity/grouping, and 66 further lost to reference
order compatibility. Thus 92.896% of this particular occurrence deficit is
absence from the union. These are descriptive compatibility categories, not
causal effect estimates or a decomposition of task errors.

The system also has substantial work after coverage: among the 2,567 samples
with an order-compatible candidate assignment, 593 system outputs have the wrong
complete tool sequence. Another 1,250 have the correct tool sequence but fail the
repository normalized call-multiset exact metric. This motivates both better
candidate construction and better evidence consumption/parameter interpretation.
It does not prove that any particular proposed tool will repair those cases.

## Source validation and limits

The extension was bound before reading reference fields:
[reference read extension](../readiness/2026-09-15-a2t-ordered-action-reference-read-extension-v1.json).
It selects exactly the frozen 4,000 discovery IDs, with tier/id/query association,
from the same eight released manifests already pinned for metadata. It reuses
the existing a2t-gold-v1 expander and output parser; their code is identical to
both original runtime commits. All primary gold names, parsed flags, ordered-name
equality and name-multiset equality agree with the persisted first scores for
both arms. No scorer was invoked.

Reference order is the repository/scorer convention: primary tool, extra
segments of expected_tool_call, then additional_tool_calls. It has not been
independently verified against spoken chronology. Strict correspondence is a
diagnostic of the intermediate representation, not an additional task metric
or a requirement to execute every candidate action.

The 4,000 samples contain 5,417 expected occurrences, including 22 samples with
repeated tool names. No expanded reference name is outside the public registry.
Ten samples have an expanded occurrence count different from the official
scorer's saved expected count; retain both rather than deduplicating or repairing
the annotations. Official primary-call exact match, repo normalized call-multiset
exact match, and repo ordered-tool accuracy remain distinct. The last measures
tool names and order, not arguments. Bare additional-call references retain the
existing annotation limitations.

One finite unavailable candidate state remains in every sample denominator.
The 31 observed zero-action states are distinct from it. Candidates are from the
verified operative Perception source of the delivered Solver; none are
reconstructed from outputs or borrowed from another state.

## Coverage and weightings

There is no corresponding published candidate-coverage column. The published
primary-call figures are retained beside the official/repo performance table
below. Whole-sample full coverage and occurrence micro coverage use different
denominators; no new confidence intervals or hypothesis tests are introduced.

| Coverage criterion | Samples / 4,000 | Natural / equal-tier | Equal-domain sensitivity |
| --- | ---: | ---: | ---: |
| All expected names appear in candidate union | 2,663 | 66.575% | 70.401% |
| Distinct-action assignment exists | 2,624 | 65.600% | 69.151% |
| Order-preserving assignment exists | 2,567 | 64.175% | 67.166% |
| Strict equal-count, equal-position compatibility | 2,207 | 55.175% | 57.656% |

Occurrence micro coverage is 3,873/5,417 (71.497%) for union membership, 3,822/5,417 (70.556%) for distinct-action matching, 3,756/5,417 (69.337%) for order-compatible matching and 3,390/5,417 (62.581%) for equal-position matches. The additional equal-position occurrence loss is 366; this does not count all excess candidate actions.

## Complete per-tier results

Each tier has 500 rows. Performance cells show direct -> system. The paper
column is the already pinned Table 3 external primary-call reference, not a
matched comparator or an ordered-action ceiling. No per-tier superiority claim
is made from these descriptive points.

| Tier | All-name coverage | Ordered coverage | Strict coverage | Repo ordered tool | Official primary exact | Paper primary exact |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| tier1_direct | 79.800% | 79.800% | 76.000% | 67.200% -> 61.000% | 16.000% -> 9.800% | 92.400% |
| tier2_parametric | 85.600% | 85.600% | 83.400% | 78.400% -> 75.400% | 28.200% -> 35.200% | 15.600% |
| tier3_multi_intent | 54.600% | 46.800% | 46.600% | 30.200% -> 34.000% | 20.400% -> 27.400% | 28.600% |
| tier4_implicit | 34.200% | 34.200% | 24.000% | 29.000% -> 24.000% | 6.400% -> 9.800% | 11.300% |
| tier5_needle | 84.000% | 84.000% | 79.400% | 80.400% -> 74.200% | 21.800% -> 27.800% | 36.000% |
| tier6_correction | 84.600% | 84.600% | 49.600% | 73.800% -> 67.000% | 24.000% -> 29.000% | 24.800% |
| tier7_multiturn | 65.000% | 65.000% | 54.800% | 49.000% -> 44.200% | 10.600% -> 12.400% | 16.300% |
| tier8_intent_blending | 44.800% | 33.400% | 27.600% | 20.200% -> 22.800% | 20.600% -> 29.000% | 12.400% |

The single-reference group contains 3,004 samples. Repo ordered-tool accuracy
falls from 1,892/3,004 (62.983%) to 1,730/3,004 (57.590%), while repo exact improves
from 560 to 676. The 996 multi-reference samples show a different pattern: ordered
tool accuracy rises from 249/996 (25.000%) to 283/996 (28.414%), and repo exact rises
from 24/996 (2.410%) to 64/996 (6.426%). Multi-reference ordered candidate coverage
is only 399/996 (40.060%). Overall ordered-tool decline therefore must not be
described as uniform deterioration on multi-action tasks.

The correction tier has 220/500 samples with more candidate actions than reference
occurrences. All 360 samples with full ordered coverage but failed strict coverage
have excess candidate actions. Extra candidate actions are hypotheses, not
necessarily executed false positives. These counts motivate examining how the
system distinguishes provisional, superseded and final requests; the current
analysis does not read transcripts or prove why those extra actions occurred.

## Conditional outcomes and parameter gap

Partitions below use the system's own operative candidates and therefore are
post-treatment descriptive subsets, not randomized component comparisons.

| Ordered candidate coverage | n | Official primary tool direct -> system | Official primary exact direct -> system | Repo ordered tool direct -> system | Repo exact direct -> system |
| --- | ---: | --- | --- | --- | --- |
| False | 1,433 | 29.379% -> 15.980% | 6.420% -> 5.024% | 16.329% -> 2.722% | 2.652% -> 1.117% |
| True | 2,567 | 80.249% -> 82.119% | 25.243% -> 32.333% | 74.289% -> 76.899% | 21.270% -> 28.204% |

For the covered subset, system repo ordered-tool accuracy is 1,974/2,567 (76.899%)
and repo exact is 724/2,567 (28.204%). In the uncovered subset, repo ordered-tool
correct rows fall from 234 to 39 and repo exact from 38 to 16. Both arms are
evaluated on the same IDs within these tables, but difficulty and candidate
selection are not controlled. Full candidate coverage is neither final quality
nor a hard restriction: the system can answer outside its candidate state.

Across all 4,000 system outputs, 1,286 have the correct ordered tool sequence
but fail repo exact. Conversely 13 pass repo exact while having the wrong ordered
tool sequence, because the repo exact metric ignores order. Never derive the
parameter gap by blindly subtracting those aggregate metric counts.

## Root interpretation and next actions

1. Prioritize candidate coverage while retaining the downstream optimization
   track. Missing reference names dominate the measured occurrence deficit.
   The old system already sees all 152 legal tools; this is not an inventory
   availability claim. The association does not establish that the old automatic
   activation shortlist caused the deficit.
2. Maintain separate activation and parameter knowledge. Activation values should
   explain task-relevant distinctions, with optional named comparisons where the
   model is uncertain. Parameter values should explain semantic roles, allowed
   forms, units, defaults and extraction requirements. The observed parameter gap
   is large enough to study evidence consumption independently of candidate recall.
3. Treat action identity, repetition and commitment status as part of the working
   representation. A broader candidate list cannot by itself decide which earlier
   requests remain active after correction. The excess-action result motivates a
   future registered investigation of that distinction, not a post-hoc prompt edit
   or an instruction inferred from these evaluation labels.
4. Reviewer/Planner should choose tools according to the missing evidence.
   Acoustic uncertainty may justify a targeted local ASR/relisten; semantic scope
   ambiguity may justify activation/parameter comparison; structural inconsistency
   may justify contract checks or a bounded candidate refresh. This study establishes
   gaps, not the effectiveness of those interventions. Preserve Solver answer
   authority and do not substitute fixed preprocessing for agentic tool use.
5. Preserve the already prepared scope-tools configuration, prompt bytes and gates.
   After explicit owner GPU resume, SLURP broad/factored TRAIN-A remains first,
   followed by an admitted Audio2Tool scope-tools pair and E21 transfer. Reuse this
   source-bound analysis for future complete runs. Require actual capacity and
   task evidence before declaring a stable base; algorithmic training-free trajectory
   optimization remains a later stage.

The original outcome remains PRIMARY_GAIN_TOOL_GUARD_FAILED_NOT_ADOPTED: official
exact improves 18.500% -> 22.550% while primary-tool accuracy declines
62.025% -> 58.425%. Its paired intervals and rules are unchanged. This extension
does not establish replication, causality, final superiority or training-free RL.
The original direct/system generation costs, tool-use counts, failed exposure
and OBS/ORG/SUPPLY/USE evidence remain in
[the complete result](2026-09-15-a2t-native-role-base-full4000.md).

## Reproduction and engineering evidence

Run the registered reference extension through
speech_aware_evidence_acquisition.analysis.a2t_ordered_action_cli with --config
and a fresh external --output directory in WSL. The shared entry uses pure source
projection and candidate-action alignment helpers; it has no model service or
scorer path. It refuses changed hashes, cohort differences, source association
mismatches and disagreement with saved metrics.

All 49 focused tests pass, including 1,275 exhaustive matching/oracle cases,
repeated occurrences, state unavailability, source contradictions and distinct
sample/occurrence/equal-stratum denominators. Ruff and engineering-base checks pass.
The actual 4,000-row projection validates both arms against their first saved
scores. Individual projected names and model-derived rows stay outside Git;
only aggregate reports and source bindings are committed.

External artifacts reside under
SPEECHRL_DATA_DIR/analysis/SAEA-A2T-ORDERED-ACTION-ATTRIBUTION-V1:

- report.json: SHA-256 17d0aafc9964ef69e8352ed5c735ebf53347d450b1d61d7aff91c718875029ed.
- rows.jsonl: SHA-256 ab3ecbb963a3f3c71fee38bacb724557b400268ebe32a283f8419f237eeb4106.
- diagnostics-v1.json: SHA-256 8eab41c240297076b0390422155dbd45b566b35db2d343c917351e13e5ce6743.
- reference-read-extension-v1.json: SHA-256 b98479f4bf137b653bf0f21a5bbd5f24dd5cdfad81c4250bae40e9cba9146baa.

The new analysis uses zero model, tokenizer, encoder, runtime tool-inference or scorer calls. New GPU dispatch remains held; no service restart or memory release was performed.
