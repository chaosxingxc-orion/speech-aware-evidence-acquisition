# Owner direction 026: candidate coverage, conditional resolution and useful tools

Recorded on 2026-09-14. This English record translates the owner's latest
direction. Preserve all earlier completed verdicts.

## Owner direction

Split optimization into two parts. First improve how often the correct intent
appears in the candidate set; the owner considers at least 95 percent a useful
engineering target. Second determine what additional information improves
intent selection once the correct intent is present. Design Reviewer and
Solver tool capabilities around useful information gain for task correctness.

## Root interpretation and prospective measurement

Treat 95 percent as a prospective engineering target, not a retrospective
replacement for the completed system's advancement rule and not a claim that
the target has been reached. Start with the retained maximum of three distinct
candidates; report actual width and uncertainty intervals on the complete
registered roster. Do not achieve coverage by silently widening to the entire
label inventory. A width change requires its own declared system version.

Freeze C0 at first Perception output. If bounded evidence acquisition later
refreshes candidates, freeze C1 before the final Solver decision and report
both coverages. Do not reconstruct candidates from the final answer or gold.
Report final correctness given coverage and correctness outside the set
separately. When coverage changes, compare both full-roster final task quality
and downstream behavior on the common-covered subset; changing conditional
populations is not by itself evidence of changed selection skill.

Current released NEW500 evidence: C0 contains gold for 424/500 (84.8%).
Of these, 387 are finally correct (91.2736% conditional selection), while one
additional answer is correct outside C0. Final intent accuracy is 388/500
(77.6%). The 76 uncovered and 37 covered-but-wrong cases are separate gaps.
Current correct-intent/nonexact-entity outcomes number 250/500. Do not use these
DEV examples to construct memory or knowledge content.

## Knowledge construction and consumption

Maintain separate intent and slot stores. Improve high-recall intent keys
using TRAIN-derived paraphrases, speech-act/action distinctions and known
confusable neighborhoods. Inspect retrieval support coverage independently
from model candidate coverage; neither proves that values were consumed
correctly. Preserve the full legal label space.

Make intent values distinguish alternatives: activation condition, necessary
or exclusion evidence only where the task contract supports it, closest
confusions and decisive differences, and what remains unknown. Topic nouns
alone are not intent. Do not turn empirical optional-slot co-occurrence into
a hard exclusion rule.

For covered candidates, supply compact candidate-specific contrasts together
with explanatory slot contracts: semantic role, allowable representation,
extraction boundary, normalization, evidence requirement and distinctions from
nearby slots. Knowledge describes interpretation; it does not invent a spoken
value. Preserve source evidence and uncertainty separately.

## Tool design and role boundaries

Prefer tools that address an explicit missing observation, unavailable domain
distinction, or verifiable constraint. Distinguish new acoustic/textual evidence
from access to already frozen knowledge and from deterministic consistency
checks. Repeated self-review without new evidence is computation, not an
independent observation.

Candidate priorities are:
- competing-intent and slot-contract lookup through the existing shared tools,
  enriched with appropriate released values rather than a private tool runner;
- on-demand local Whisper as an alternative transcript when a decision depends
  on uncertain words, with the original speech preserved;
- source-bound crop/re-listening and alignment when a local span is actually
  required, after the shared span interface is implemented and registered;
- deterministic contract/type/value and evidence-support checks, reporting
  violations or missing proof rather than assigning the final intent;
- pronunciation/confusability lookup for ambiguous entity strings when the
  task supports it, without treating pronunciation similarity as evidence
  that a word was spoken.

The current completed system permits Reviewer task-contract calls only.
Its live-speech successor is held; the present callable live-speech interface
is full-utterance ASR and does not implement arbitrary crop requests.
Downloads, bindings, declared tool names and completed task evaluations are
different readiness states.

Root's initial recommendation preserves Reviewer/Planner responsibility for
active acoustic evidence acquisition. Solver must receive the evidence needed
for joint selection and filling and be able to express a specific unresolved
distinction. Consider direct read-only contract/knowledge/check tools for Solver
as an explicit next-version role design, not an already implemented or admitted
change. Keep final answer authority with Solver and never give tools or another
LLM that authority.

## Execution consequences

Continue model-free readiness work on the unchanged TRAIN Fold A incumbent
source. It provides an anchor for both diagnostic directions and future
same-sample alternatives. Keep Fold B untouched for disjoint evaluation.
Do not launch an enhanced mechanism based on the earlier slot-only priority.

Before an enhanced flight, freeze the candidate/conditional-selection metrics,
actual graph transitions, allowed tools, stopping behavior and complete-system
task reward. Reuse the current framework, registered tools and actual-request
fitter. Any missing tool argument or state transition must become a shared
capability, not an experiment-specific execution path.

Reward analysis must distinguish candidate recall, covered-set selection,
entity/slot quality and full final task quality. Improvements to a stage cannot
override deterioration in the full task. Real TRAIN trajectories, procedural
proposals, compact construction and disjoint candidate evaluation remain
necessary before claiming a training-free optimization cycle.
