# Audio2Tool parameter-value evidence: historical and source reconciliation

Date: 2026-09-15. Status: **CPU audit complete; no new value-view or flight admission.**

The missing identifier information reported in STATUS-135 remains a real source-projection
gap. It does **not** justify appending public defaults or constructing a device alias table
from evaluation errors. Previously completed experiments already show default-copying
failures. The current construction contract contains no device inventory or alias mapping.

Keep the prepared scope-tools pair unchanged. Treat parameter-value evidence as a later,
separately registered system extension, with source meaning and request binding established
before implementation. Root owns this decision. The owner GPU hold remains in force.

## 1. Reconcile the new gap with the consumed historical experiments

The [complete primary-parameter analysis](../results/2026-09-15-a2t-primary-parameter-attribution-v1.md)
found 583 deviceId errors among 941 residual system wrong-value keys in the 2,089 rows where
both arms choose the correct primary tool. Of those 583 references, 376 equal the public
default and 207 do not. All 43 tools with a nonempty public deviceId default lack that
literal in their parameter card, every other parameter card and the compact registry.

These are conditional, post-outcome diagnostics. The system cannot identify the 376 cases
from their evaluation references at runtime. Replacing every identifier with a default
would also affect correct predictions and non-default requests; this audit does not
estimate that intervention's gain. The value audit did not read speech/transcripts, so it
does not establish whether each identifier was spoken explicitly, referred to by an alias,
or underspecified in the available task input.

The August 18 supply experiments used the same 120 discovery rows selected because one A0
attempt chose the correct tool but failed the full call. Preserve their own scorer and
formal decisions:

| Historical arm | Supply | Exact-call conversions / 120 | Induced substitutions |
|---|---|---:|---:|
| S1' | Self-selected correct row, including defaults; replaces registry | 16 | 34 |
| S2 | Correct row plus eight distractors; replaces registry | 11 | 34 |
| B1 | Self-selected row with argument_defaults removed; replaces registry | 8 | 2 |
| C1 | Permuted stripped row; replaces registry | 10 | 4 |
| C2 | Verbalized stripped row; replaces registry | 9 | 3 |
| C3 | Stripped correct row appended to the intact registry containing defaults | 7 | 22 |

Sources: [Stage-2 verdict](2026-08-18-a2t-s2-verdict.md),
[Stage-2b verdict](2026-08-18-a2t-s2b-verdict.md), and
[Stage-2c verdict](2026-08-18-a2t-s2c-verdict.md). Their full per-tier tables remain the
authoritative historical breakdowns. This reconciliation adds no experimental verdict.

Stage-2's formal outcome was COPY-TRAP, with descriptive DOSE. B1 met CONFIRMED-CUT.
C1/C2 jointly met ROBUST, while C3 met the separate CHANNEL-REOPENED overlay. Retain the
unrelated B2 decision as INCONCLUSIVE-B with MISLEAD not met. The replacing wrong-row S4
withheld the correct tool and is not independent evidence about activation knowledge.

Two limitations change how to use this history:

- Conversion counts are sample outcomes; induced substitutions use a bare argument-key
  detector and are upper bounds. Do not subtract them or present their ratio as a net task
  benefit. They are not the current official parameter-error statistic.
- B/C arms were not replicated; no registry-only induced baseline exists. The old
  quantization, prompt, sampling, scorer, selected cohort and near-threshold counts do not
  establish a modern effect size or universal rule. In particular, historical ROBUST is a
  registered label, not a general robustness claim.

The evidence is still sufficient to reject the assumption that supplying more concrete
values is automatically helpful. Moving access behind a tool call has not yet demonstrated
protection against copying.

## 2. Distinguish source permission from scientific evidence

The [original registration](2026-08-18-pa2t-stage2-preregistration-REGISTERED.md) explicitly
treats the shipped registry as a legal task-native source. Removing argument_defaults was
an arm-specific intervention. A0, B2 and C3 retained registry defaults.

There is no repository-wide prohibition on public defaults established by these records.
The later [candidate qualification document](2026-08-18-stage2b-candidate-qualification-DRAFT.md)
is a draft freeze candidate, not an owner-approved global runtime rule. This decision
therefore does not invent a new permission requirement or rewrite the historical results.

Current [value readiness](2026-09-11-audio2tool-discriminative-value-readiness.md) still
requires pinned registry/construction sources and evaluation exclusions. A legal public
field is not necessarily an applicable answer for the current user request.

## 3. What the permitted construction source actually supports

The pinned selection covers 30,733 source samples in 16,843 tier/query units. The upstream
exposure union has 6,479 identities, which resolve to 5,274 excluded original sample IDs
covering 2,956 query groups. The remaining selection contains 1,690 query groups,
3,208 complete units and 5,955 samples:

| Tier | Permitted complete units | Permitted samples |
|---|---:|---:|
| Direct | 303 | 606 |
| Parametric | 1,243 | 2,486 |
| Multi-intent | 300 | 600 |
| Implicit | 297 | 594 |
| Needle | 304 | 608 |
| Correction | 300 | 600 |
| Multiturn | 299 | 299 |
| Intent blending | 162 | 162 |
| Total | 3,208 | 5,955 |

The existing compilation quarantined one two-sample unit: 3,207 units / 5,953 samples
remain usable at that stage. A further 13 construction-summary rows were excluded by the
compiler, leaving 3,194 safe summary rows. Do not conflate these three denominators.

Root independently joined the pinned metadata inventory, selection and current 4,000-row
evaluation roster. Every selected unit is complete; the selection is exactly the set of
units outside excluded query groups. All 4,000 evaluation sample IDs are excluded, and
their query groups have zero overlap with permitted construction. This audit did not
recompute a global exposure union or read new dataset target fields.

The shared builder validates receipt bytes, all eight manifest bindings, complete unit
membership and cross-tier query-group exclusion. It trusts the upstream selection's
exposure coverage; it does not rediscover every exposure source. A future construction
change must use the then-current exclusions, rather than treating this receipt as perpetual
authorization.

The inherited renderer receipt names tool_name and arg_signature as its construction
fields. The complete compiler also reads arg_pairs to classify serialized argument values
into coarse JSON forms; those observed literals are not rendered into runtime cards. Runtime cards contain public API facts, supported key patterns and forms,
role guidance, support counts and artificial examples. The receipt records zero rendered
source argument values, evaluation values, source utterances, transcripts and sample IDs.

No current source field or projection defines a device-ID alias map. Media/sample alias
normalization only resolves derived sample identities; it says nothing about device names.
A real device catalog would require a separately identified, permitted source and a
versioned projection through the shared compiler. Do not fabricate one from repeated
evaluation answers, public default coincidences or source sample identifiers.

## 4. Root design: evidence must explain how a value applies

A knowledge-store value is an evidence object, not merely a literal to copy. For parameter
resolution it should explain the role, applicable form, source scope, constraints and how
the current request supports a particular choice. Activation knowledge continues to explain
which operation and domain apply; the stores retain their separate roles.

| Evidence kind | Current availability | Valid use | Limitation |
|---|---|---|---|
| Public signature, type and constraint | Implemented | Explain valid roles and representations | Does not identify the requested entity |
| Construction-supported native form | Implemented | Explain a supported task form and its scope | Does not provide concrete observed answer values |
| Explicit speech or permitted dialogue evidence | Existing observation pathways | Recover the requested value or correction | Observation is uncertain and must retain its source |
| Public argument default | Registry source exists; current parameter view omits it | A later proposal may expose a clearly labelled, conditional source fact | Default status alone does not bind it to the request |
| Device alias / instance catalog | Absent from the current contract | Only a future permitted catalog can support instance resolution | Never infer this catalog from evaluation error pairs |
| Synthetic example | Implemented | Demonstrate syntax or a semantic role | Its values are not evidence about the current request |

The resulting agentic behavior remains a hypothesis to test:

1. Reviewer flags a concrete inconsistency or missing evidence, such as an unresolved
   identifier, conflicting correction, or a role not supported by the current observation.
   Reviewer does not supply an authoritative final answer.
2. Planner selects a useful available action. Targeted knowledge lookup can clarify roles
   and constraints. A speech observation tool can clarify an uncertain spoken token. It
   cannot recover an unprovided device catalog by decoding the same audio again.
3. Solver combines the observation and returned source facts, retaining answer authority.
   An unresolved binding stays visible in the internal evidence state; it is not silently
   filled with a convenient default. Keep the dataset-native final output contract.
4. Trace the requested target, returned source, proposed binding and final consumption
   separately. OBS identifies the observation; ORG defines the fact's structure; SUPPLY
   records what was returned; USE records whether it changed the answer.

Reuse the existing target-knowledge/store tools and common controller/executor if this
extension is later admitted. This note introduces no new runtime fields, default-filling
rule, private agent script or second answering model.

## 5. Sequence and decision use

Keep the current queue: after explicit owner GPU resume and per-flight gates, run the
prepared SLURP broad/factored TRAIN-A work first, the admitted prepared Audio2Tool
scope-tools pair next, then E21 transfer. The Audio2Tool
[held configuration](2026-09-15-a2t-native-role-scope-tools-held-v1.md) does not change here.

A later parameter-evidence extension must name its available source and unresolved binding
question before adding code. If no permitted instance mapping exists, treat it as a missing
environment fact rather than inventing an algorithmic solution. Complete this source audit
now; do not keep recompiling the same cards while GPU execution is held.

Judge that future extension on complete direct-model versus complete-system task quality,
using the eligible full roster and dataset-native scoring. Keep candidate inclusion,
tool selection, parameter errors, insertions/omissions and default-copying diagnostics
separate. Report both natural and balanced strata. A focused tool/key/occurrence diagnostic
must distinguish copying a default into a newly wrong value from merely matching a public
default; observing a match is not a causal proof. Do not use the old selected 120-row cohort
as a new adoption gate or impose an obligatory knowledge-on/off factorial.

The stable, replicated system benefit and later trajectory-sampling training-free RL
objective remain open. This root engineering judgment is not an RL algorithm result.

## Evidence custody

The [source-bound JSON receipt](2026-09-15-a2t-parameter-value-evidence-decision-v1.json)
pins 17 repository blobs at 5f896aeb1c6b04fbdd9146d9988ece5295b2a8bc and five external metadata
artifacts. No compiler, scorer, model, tokenizer, encoder or serving endpoint was invoked
for this audit. Existing results, raw traces, preparation releases and frozen configurations
remain unchanged; no new raw target values enter Git or runtime.
