# SLURP candidate coverage, joint resolution and useful evidence plan

Date: 2026-09-14. Root design following owner direction 026. This document
proposes successor behavior; it does not authorize enhanced model contacts.

## Released evidence and the optimization objective

The completed matched NEW500 discovery comparison increased official pooled
SLU micro F1 from 36.14371997 to 50.44788353 and intent accuracy from 73.6 to
77.6 percent. This is a complete-system exploratory result, not a component
attribution or an independently replicated superiority claim.

The system's first Perception candidate set covered gold on 424/500 records
(84.8%). The final answer was correct on 387/424 covered records (91.2736%);
one additional final answer was correct outside the initial set. There were
76 uncovered records and 37 covered but incorrectly resolved records. Correct
intent with nonexact entities occurred on 250/500 records. These are released
diagnostics, never runtime facts or construction examples.

For a strictly candidate-constrained answer, final intent accuracy equals
candidate coverage multiplied by conditional selection accuracy. Holding the
current conditional rate constant while reaching 95% coverage gives about
86.7% final intent accuracy; this is an arithmetic scenario, not a forecast.
Reaching coverage alone does not solve selection or slot extraction.

Retain a maximum of three distinct candidates for the first successor design.
Report actual widths and fixed-roster uncertainty. Treat 95% as a prospective
engineering target. Do not claim a population lower bound of 95% from a point
estimate of 95%, and do not enlarge the legal shortlist silently.

## Current implementation gaps

The incumbent Perception returns one to three intents with short distinctions.
Its evidence_refs and unresolved_fields are required to be empty. Solver
instructions require choosing an initial candidate and retaining that same
candidate set on revision. The few observed answers outside that set are
instruction deviations, not an implemented candidate-recovery mechanism.

Reviewer instructions require a task-contract tool call in each review.
All 1,010 analytical calls in the completed DEV1000 system run were contract
calls. No live speech observation was invoked. Tool use was real, but useful
acoustic information gain has not been evaluated.

The current native tool argument schema supports full-utterance ASR with a
declared distinction. It does not support arbitrary crop selection. Existing
candidate-contract lookup and prepared named-store access can support richer
semantic evidence, but a tool allowlist does not itself add a model-tool-model
round trip or permit a new role transition.

## Axis 1: cover the correct intent

Diagnose misses on TRAIN, keeping retrieval support and model shortlist
coverage separate. Test whether a useful intent facet was absent from retrieved
support, whether supplied distinctions were insufficient, or whether the model
discarded a supported alternative. Do not infer a failure stage from final
accuracy alone.

Construct a stable intent store with recall-oriented keys covering paraphrases,
speech acts, requested operations, negation and confusable neighborhoods.
Values should explain the decisive boundary and evidence to seek, rather than
repeat a topical label. Preserve the complete legal inventory in the task
contract. Avoid padding candidates or treating a short list as calibrated
confidence.

Freeze C0 at initial Perception. A bounded Planner-controlled recovery may
request an alternative speech observation or a competing-contract lookup and
refresh the shortlist from the complete legal inventory. Freeze the resulting
C1 before the final Solver decision. Report initial coverage, post-acquisition
coverage, recovered and newly lost gold candidates, and final out-of-set
answers. Never reconstruct either set from the final answer or gold.

Represent a concrete unresolved distinction in the internal state. Do not
require long free-form reasoning: an unresolved operation or uncertain spoken
phrase and its relevant candidate alternatives suffice. A candidate refresh
requires an explicit shared graph transition and its actual-request fit.

## Axis 2: resolve covered candidates jointly with slots

Keep intent and slot knowledge in separate stores, but join their consumption
through the candidate identity and source evidence.

Intent values should expose activation conditions, nearest competing intents,
decisive differences, exclusion evidence where supported, and unresolved
conditions. Slot values should explain semantic roles, extraction boundaries,
surface-form requirements, allowed representations and known confusions.
Distinguish official constraints from empirical TRAIN associations. Optional
slot absence is not a hard intent exclusion.

For example, alarm_set and alarm_query can both concern an alarm and a time.
The discriminating evidence is whether the speaker requests creation/change
or inspection of an existing alarm. A time mention alone cannot settle the
operation. Slot interpretation must then follow the selected operation and
the actual spoken expression. This illustrates knowledge structure; it is not
a newly admitted knowledge value.

Supply a compact candidate-by-evidence view: evidence supporting each
alternative, evidence contradicting it, slot interpretations it entails, and
the remaining unknown. Preserve observation provenance separately from
semantic interpretation. Solver jointly selects the intent and fills the
supported entities; a missing or ambiguous value must not be invented.

When coverage changes, compare full-roster final quality first. Conditional
selection now refers to a changed population. Include the common-covered
subset as a descriptive diagnostic and do not interpret its change alone as
a causal measure of a component.

## Roles and tools

Perception consumes frozen observation and intent knowledge and produces
candidates plus bounded unresolved distinctions. It need not orchestrate
analytical tools.

Reviewer identifies a specific possible error or evidence gap. Planner selects
ACCEPT, evidence acquisition, candidate refresh, or answer revision within a
registered bound. Trigger acquisition because a consequential distinction is
unresolved, not merely because a model reports a confidence number. Reviewer
and Planner own active acoustic acquisition initially.

Solver receives source-bound observations, competing intent boundaries and
slot contracts and owns the final answer. It can expose a specific unresolved
distinction for the next review. Direct read-only contract/knowledge/check
tools for Solver are an optional explicit successor design; do not enable
them without an actual iterative role configuration and registration.

Prioritize the following tools through shared registered interfaces:

1. Competing intent and slot-contract lookup: clarify the requested operation,
   competing interpretation and extraction rules. It retrieves knowledge, not
   new evidence that a particular word was spoken.
2. Local on-demand Whisper: supply a second decoding of the same original
   speech when a lexical ambiguity affects the decision. Preserve disagreement
   and original speech; do not replace audio with ASR as fixed preprocessing.
3. Deterministic contract and representation checks: identify illegal labels,
   types or surface-form violations where the official task supports a rule.
   A model-based semantic-support judgment is not a deterministic validator.
4. Registered source-bound crop/re-listening and forced alignment, later:
   locate a relevant span and let the frozen core inspect it. Alignment is
   conditional on its hypothesis and cannot prove that the word was spoken.
5. Pronunciation/confusability lookup for eligible entity ambiguities: return
   plausible confusions, never a factual assertion of the spoken entity.

Start with existing full-utterance observation support for short SLURP inputs.
Do not delay the first useful tool experiment for diarization or a new slicing
framework. Longer E21 turns may make those tools valuable later.

## Measure useful information, not activity

Report the explicit pre-tool gap, requested tool and arguments, actual returned
evidence, resulting candidate/answer change and final task outcome. Count
wrong-to-right rescues, right-to-wrong harms, candidate recoveries, entity
corrections, failures and no-op acquisitions.

Self-reported confidence increases, a longer rationale, or a tool call count
are not task-grounded information gain. Before/after changes in one trajectory
are descriptive; causal credit needs an appropriate registered comparison.

The shared feedback implementation currently supplies final native task
rewards, not candidate-coverage, conditional-selection or tool-credit fields.
Add stage diagnostics to offline source-bound feedback without placing gold
in runtime. Use actual complete same-sample alternative trajectories for
group-relative feedback. An intermediate-state counterfactual fork and forced
native actions are not currently implemented and must not be claimed.

Use complete final task quality to select candidates; stage metrics diagnose
and guide proposals. Do not reward coverage while allowing final SLU quality
to deteriorate, and do not reward token or tool volume.

## Execution order

1. Complete and register the unchanged 1,080-record TRAIN Fold A native anchor
   using prepared speech packets and the existing no-mmproj resident server.
   Preserve Fold B for disjoint evaluation. This supplies source trajectories;
   it does not itself demonstrate optimization.
2. Use sealed Fold A outcomes to construct coverage and resolution diagnostics.
   Propose compact knowledge-consumption and procedural-memory changes from
   TRAIN sources only. DEV errors remain analysis-only.
3. Evaluate a bounded coverage-oriented complete system successor on TRAIN A,
   including candidate refresh only if its shared transition is implemented
   and registered. Keep the direct-model/system comparison as the main study;
   do not expand into an indiscriminate knowledge/no-knowledge factorial grid.
4. Add candidate-conditioned semantic evidence and on-demand tools according
   to the diagnosed failure component. Compare complete task outcomes and
   retain a minimal matched control only when it changes the decision.
5. Evaluate selected candidates on disjoint Fold B before promoting guidance.
   Return to a registered matched direct-versus-complete-system evaluation.
   Historical exposed DEV remains discovery data.

The same framework carries later tasks, while their evidence contracts and
values differ: Audio2Tool joins activation boundaries with argument semantics;
E21 prioritizes transcript, entity and number quality rather than an invented
intent metric. No E22 carrier or new dataset is admitted by this document.
