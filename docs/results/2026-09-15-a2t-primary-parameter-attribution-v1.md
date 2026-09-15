# Audio2Tool primary parameters: value grounding is the main remaining gap

Date: 2026-09-15. Root-authored post-hoc CPU analysis. The owner GPU hold,
original outcomes and prepared successor configurations remain unchanged.
No model, tokenizer, encoder, runtime analytical-tool or scorer was called.

## Findings that matter for the system

On the same 2,089 samples where both arms select the correct primary tool,
official exact improves from665 to829. The number of samples with a wrong
parameter value falls950->784, extra-key cases fall472->451, and missing-key
cases rise107->131. Errors can coexist in a sample, so do not add those sample
counts as if they were disjoint. The corresponding wrong-value key count falls
1,205->941. This supports keeping the parameter-resolution direction while
measuring its omission tradeoff; it does not isolate a component effect.

The system's remaining wrong values are concentrated in device identifiers:
583/941 wrong keys in that common cohort (61.955%), and688/1,082 in the wider
2,337-sample system-primary-correct cohort (63.586%), are deviceId.
Do not substitute a global deviceId correction rule for per-tool and per-request
grounding: this is an analysis priority, not a runtime lookup table.

The public registry supplies a nonempty deviceId default for43 tools.
A source audit finds none of those exact ID literals in the corresponding
parameter value, any of the152 parameter values, or the complete compact tool
description. This is a concrete source-to-value projection gap. The parameter
store explains the String field and supplies synthetic examples, but does not
carry these published identifier values. Some wrong outputs use a different
identifier spelling or a descriptive device name; those individual examples
remain outside Git and never become runtime corrections.

The public default is not proof of the requested device. In the common cohort,
376 of the583 deviceId reference values equal the public default and207 do not.
No wrong system deviceId prediction in that cohort equals the published default.
This is evidence that documented values deserve investigation, not permission
to fill every missing or uncertain identifier with that default. No transcript
was read in this extension, so the analysis does not establish which identifiers
were spoken, inferable from the request or underdetermined.

## Meaning of the analysis

This report targets the official **primary call** and its extracted_params.
It does not explain every multi-call parameter failure in the previous ordered
analysis. That previous study's1,250 covered/sequence-correct but repo-inexact
cases use a different full-call metric and subset.

The registered source binding is
[the primary-parameter read intent](../readiness/2026-09-15-a2t-primary-parameter-read-intent-v1.json).
Exactly4,000 discovery IDs are selected with the existing tier/id/query association
helper. The existing official primary parser and normalize_parameters are reused.
The new pure helper computes key-set and value relations; it never invokes
compute_parameter_accuracy or a scorer. For both arms and every sample,
primary parse/name facts, normalized correct/predicted/reference key counts,
parameter exactness and official exactness agree with the first saved scores.
The reference maps use the original official extracted_params, not the repo's
expanded expected-call arguments.

The helper preserves normalized-key collisions and simultaneous error classes.
No raw parameter values are written to its output. Per-sample diagnostic rows,
post-hoc example pairs and all large source bytes remain outside Git. The original
4,000-row roster, scores, primary decision and held prompts are unchanged.

## Common-cohort error types

Both arms have the correct primary tool on these2,089 samples. The cohort is
selected using observed outcomes from both arms and is descriptive; it is not a
randomized test of parameter knowledge. These diagnostic rates have no matching
published Table3 column.

| Error type | Direct samples | System samples | Direct sample rate | System sample rate | Direct keys | System keys |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Missing reference key | 107 | 131 | 5.122% | 6.271% | 135 | 142 |
| Extra predicted key | 472 | 451 | 22.595% | 21.589% | 656 | 600 |
| Wrong value on a shared key | 950 | 784 | 45.476% | 37.530% | 1205 | 941 |

Among those2,089 samples, correct reference keys rise862->1,119, predicted keys
fall2,723->2,660 and the reference denominator remains2,202. Of600 extra system
keys,144 equal a public reference-tool default under official normalization.
That diagnostic differs from the saved repo-v2 default-stripping count, which
uses a different typed parser and all-call/reference semantics. It does not
license stripping arguments from a future answer.

The common-cohort system parameter error profiles are696 wrong-value-only,
418 extra-only,52 missing-only and94 mixed cases;829 have no parameter error.
The profiles explain why a single 'repair slots' action is too coarse.

## Full per-tier performance and conditional errors

Performance counts below cover all500 rows per tier. Paper exact is the already
pinned external Table3 primary-call reference, not the same model or a matched
population. Repo exact compares normalized call multisets, not only the primary
call or ordered full calls. No new per-tier hypothesis test is introduced.

| Tier | Official tool direct -> system | Official exact direct -> system | Repo exact direct -> system | Paper primary exact |
| --- | --- | --- | --- | ---: |
| tier1_direct | 336 -> 307 | 80 -> 49 | 98 -> 107 | 92.400% |
| tier2_parametric | 392 -> 379 | 141 -> 176 | 142 -> 165 | 15.600% |
| tier3_multi_intent | 338 -> 324 | 102 -> 137 | 13 -> 34 | 28.600% |
| tier4_implicit | 145 -> 122 | 32 -> 49 | 32 -> 48 | 11.300% |
| tier5_needle | 402 -> 372 | 109 -> 139 | 116 -> 151 | 36.000% |
| tier6_correction | 380 -> 364 | 120 -> 145 | 118 -> 145 | 24.800% |
| tier7_multiturn | 245 -> 227 | 53 -> 62 | 53 -> 60 | 16.300% |
| tier8_intent_blending | 243 -> 242 | 103 -> 145 | 12 -> 30 | 12.400% |

The next table returns to the common-primary-correct subset. Error cells are numbers of affected samples, direct -> system; the conditional denominators differ by tier.

| Tier | Common n | Missing | Extra | Wrong value |
| --- | ---: | --- | --- | --- |
| tier1_direct | 280 | 3 -> 0 | 197 -> 230 | 2 -> 3 |
| tier2_parametric | 348 | 15 -> 18 | 22 -> 7 | 197 -> 175 |
| tier3_multi_intent | 291 | 9 -> 15 | 93 -> 74 | 125 -> 94 |
| tier4_implicit | 88 | 6 -> 3 | 5 -> 4 | 56 -> 45 |
| tier5_needle | 357 | 18 -> 14 | 122 -> 108 | 138 -> 113 |
| tier6_correction | 327 | 18 -> 35 | 3 -> 4 | 212 -> 176 |
| tier7_multiturn | 191 | 15 -> 27 | 3 -> 3 | 136 -> 126 |
| tier8_intent_blending | 207 | 23 -> 19 | 27 -> 21 | 84 -> 52 |

Correction shows a clear descriptive tradeoff: wrong-value samples fall212->176,
while missing-key samples rise18->35. Multiturn similarly changes136->126 and
15->27. Tier1 differs: extras rise197->230, while official exact falls and repo
exact improves. Preserve the historical empty-reference/default distinction;
an extra parameter is not automatically unsupported by speech.

## Weighting sensitivity

Natural rates above pool the common cohort. The following equal-stratum rates
average within-tier or within-domain sample rates with equal stratum weights.
They do not use parameter-key micro weights or supply additional inference.

| Common-cohort weighting | Missing direct -> system | Extra direct -> system | Wrong value direct -> system |
| --- | --- | --- | --- |
| Equal tier | 5.600% -> 6.459% | 20.503% -> 19.665% | 47.398% -> 38.920% |
| Equal domain | 8.764% -> 4.999% | 17.175% -> 18.042% | 35.290% -> 27.087% |

Equal-domain missing-key direction differs from the natural/equal-tier direction.
Keep this sensitivity rather than claiming that omissions worsen in every domain.
The full by-domain counts and all4,000-row partitions are in the aggregate artifact.

## Parsing and representation do not explain the main result

Both parsers yield identical official-normalized primary parameter maps on all
2,089 common-primary-correct rows, and all2,337 system-primary-correct rows.
Across the whole system there are6 disagreements among3,984 comparable parses,
all outside that correct-primary subset. No missing or wrong reference key in
the system is rescued by the alternative first-call parse under official
normalization in this audit.

The existing repo numeric/boolean coercion makes5 direct common-cohort wrong
keys equivalent, but zero system wrong keys. Therefore neither this parser
diagnostic nor this coercion diagnostic explains the main residual system
value gap. These are narrow checks, not proof that all possible formatting,
representation or annotation issues are absent.

## Root recommendation: improve what a value lets the agent decide

The current parameter value already supplies signature, type, constraints,
required/optional keys, source-scoped native forms, spoken-role-to-key guidance
and synthetic examples. Repeating those fields is unlikely to address the
identified omission in its source projection. A future source-grounded value
should distinguish:

1. **Role and requirement:** what the parameter means; when it is needed, optional,
   superseded or inapplicable. Preserve the distinction between a public API
   shape and a permitted native task form.
2. **Available value evidence:** documented identifiers, enum values, formats
   and source provenance. Label a published default/example as such; do not
   assert it is a live inventory or the selected object's true ID.
3. **Binding to this request:** the utterance/authorized context that identifies
   the object, time, zone or measurement. Keep unresolved alternatives visible
   rather than manufacturing an ID. Error pairs from this evaluation are never
   copied into memory or runtime knowledge.
4. **Revision authority:** Reviewer/Planner may inspect the relevant public
   value evidence, check a contract or request another observation; Solver
   selects the final tool and arguments. Tools add evidence rather than secretly
   replacing the answer.

This changes the tool priority. A targeted ASR/relisten remains useful when the
spoken entity or number is uncertain. It does not supply a missing application's
identifier catalog. A source-bound public-value/identifier inspection capability
is a plausible next system component; where the source lacks a real entity
mapping, report the limitation instead of inventing one. Schema validity alone
also cannot certify the correctness of an arbitrary String identifier.

The smallest next scientific question is whether exposing documented parameter
values on demand, with their source and default/example status, improves the
integrated system while preserving tool selection and avoiding unsupported
default filling. Reuse the shared target-knowledge tool/registered store seam
for any future implementation. First examine permitted construction sources,
not these evaluation aliases, for the binding rules.

Do not silently add this mechanism to the frozen scope-tools comparison.
The current prepared SLURP -> admitted Audio2Tool scope-tools pair -> E21
sequence remains held until explicit owner GPU resume. This report is an input
to a later named, registered system extension, not an additional launch plan.
Actual gains, component utility, replication and eventual algorithmic
training-free trajectory optimization remain unproven.

## Reproduction and closure

The shared entry is speech_aware_evidence_acquisition.analysis.a2t_primary_parameter_cli
with the registered --config and a fresh external --output directory, executed
in WSL with the explicit source tree. It imports the existing source verification,
cohort association, official parser and normalizer; no new experiment runner exists.

The new helper/aggregation suite passes25 tests, including empty and mixed cases,
collisions, immutability, default/coercion diagnostics and separate cohort/weighting
denominators. Including the reused source projection tests gives54 passing tests.
The pure helper has100% statement coverage. Ruff, engineering-base and whitespace
checks pass. Actual complete4000 projection succeeded once with all saved facts
matching. No historical scorer was rerun.

The supplementary default analysis counts wrong keys whose normalized reference
or prediction equals the public default, using the same already admitted sources.
The identifier-availability audit checks exact default-ID literal presence in
each own card, all cards and render_registry_compact_rows. These reproducible
source-inspection definitions do not alter the primary analysis or create a
counterfactual score. Raw example pairs remain external and analysis-only.

Artifacts under SPEECHRL_DATA_DIR/analysis/SAEA-A2T-PRIMARY-PARAMETER-ATTRIBUTION-V1:

- report.json: SHA-256 8b11e11f7a14c33fb1d69f3955c1d018d53f83fbfc116c50e0b6c0872df3a56a.
- rows.jsonl: SHA-256 76397aac58624f022066302506a959277f15b76ca4aa8b148f679bedbe932fe6.
- read-intent-v1.json: SHA-256 591b4320d14baa4843907ec16a6093612a4813b0413e20dd99688cc621e273e2.
- default-value-diagnostic-v1.json: SHA-256 df15e3748b6cfd1d2cf59da8c38144f858f980004b58e1e51ef408b35534167d.
- public-identifier-availability-v1.json: SHA-256 b24166d477f0590f8c643aa4855454daa97b66c3d825ea52ad2b94b1a70534f4.

Original verdict: PRIMARY_GAIN_TOOL_GUARD_FAILED_NOT_ADOPTED. See [the complete paired report](2026-09-15-a2t-native-role-base-full4000.md) and [ordered-action analysis](2026-09-15-a2t-ordered-action-attribution-v1.md). GPU hold remains active; no service restart or memory release occurred.
