# Held TRAIN successor: candidate refresh with on-demand evidence

Date: 2026-09-14. Root design during the unchanged TRAIN A recovery.
This is one proposed complete-system successor. It grants no model or tool contact.

## Scientific question and roles

Test whether a complete agentic system can improve candidate coverage and final SLU
quality by seeking relevant information and reconsidering its candidate set.
Do not interpret the contrast with the incumbent as a causal estimate for one component.

Perception retains one to three distinct complete legal intents and up to two bounded
unresolved distinctions. On a Planner-requested second visit, it can reconsider the
full legal inventory using source-bound observations. It does not orchestrate tools.
Solver jointly selects the most recent candidate and extracts all supported entities.
Reviewer can request a contract lookup or a second speech decoding for a concrete gap.
Planner chooses acceptance, revision within the current candidates, or candidate refresh.
Only Solver answers the task. Knowledge remains reference material, and ASR remains
fallible acoustic evidence rather than a source of final task labels.

Keep the distinction between tools: candidate-contract lookup clarifies activation and
slot semantics but supplies no new evidence that a word was spoken; Whisper supplies
an alternative transcript but no authoritative intent or slot annotation.
Optional slot absence does not exclude a candidate. A high-confidence suspicion
concerns a specific defect in the current evidence or draft, not generic low confidence.

## Prepared shared configuration

The held fragment is
configs/baseline/slurp-native-candidate-refresh-tools-train-fold-a-held-v1.json.
It retains the Fold A speech packets and dual knowledge stores.
A new shared phase-native-candidates-review-refresh-v1 program has a ceiling of 12
model contacts, leaving the incumbent program's ceiling 11 unchanged.

With one refresh and the incumbent role limits, the worst case is:
initial Perception 1, two rounds of Solver 1 + Reviewer 3 + Planner 1, and refreshed
Perception 1. The Reviewer ceiling includes model turns used to request tools and
read their results. It is a safety bound, not a target number of calls.

Only Reviewer has the three tool schemas: task contract, candidate-contract lookup
(up to 3 legal IDs), and live full-utterance speech observation.
The prompts request selective use, reuse of an already returned transcript, and a
remaining model turn for reporting findings. A prompt is not a runtime per-sample
ASR cap; the admitted ASR execution plan and dispatcher must enforce the actual bound.

The Solver consumes the latest Perception state. Candidate slot supply selects its
full bounded cards before subtracting already-visible values. Each selection remains
limited to 28 cards; cumulative history may reach 56 after a disjoint refresh.
The full request, including this history and any returned transcript, must pass the
shared actual-request fit. Preserve max512, the no-mmproj model and current serving
geometry for the proposed comparison unless a formally registered fit decision changes
the whole group before launch.

## Required admission work

Wait for the complete 1,080-record TRAIN A anchor, its automatic first official score,
and the root diagnostic decision. Keep Fold B untouched. Freeze C0 and C1 projections
from actual Perception contacts before launching the successor; do not use a union or
infer candidates from final answers.

Bind the existing TRAIN runtime view's original-audio addresses, hashes and roster
to the local pinned Whisper assets, runtime protocol and attempt outputs. A separate
model-free inventory export can aid audit but is not another runtime requirement.
Do not reuse the old DEV audio roster or pretranscribe TRAIN audio. Register real
ASR/tool contacts before use.

The held fragment opts into the shared scheduler's yield-model-slot resource policy,
with one local tool worker across the whole flight. A selected analytical tool releases
the sample's model slot before waiting for CPU capacity; the next model request
reacquires a slot and supplies its complete history. Preserve serialization within
each episode, source custody and cancellation draining. Legacy configurations keep
their original stable slot affinity. No independent model service is launched.
Bind the Whisper thread envelope and aggregate preparation allowance before admission;
one scheduler worker does not bound Torch's internal parallelism by itself.

Bind generation, actual-request fit, tool budgets, prepared receipts and one complete
official score. The max12 graph implies an upper bound of 12,960 model contacts on 1,080
rows and 51,840 fit endpoint calls for one speech packet per request. These are prospective
ceilings, not authorization, contact targets or measured costs. The CPU tool and graph
allowances must agree. No executable experiment or campaign fragment is provided here.

After complete paired TRAIN trajectories exist, compare whole-roster final quality.
Use C0/C1 coverage, recovered/lost candidates, common-covered resolution, slot quality,
rescues/harms and tool outcomes for diagnosis. Do not treat confidence gains or more
tool activity as reward. Group-relative feedback requires the actual paired sources;
compact corrective guidance is proposed and selected on TRAIN before disjoint Fold B.

## Root model-free validation

The shared scheduler, actual fake-transport native role/tool path, role configuration,
actual-request fit, dispatch, and legacy workflow suites passed 231 tests in WSL.
The on-demand tool test runs both the legacy and yielding resource policies and
verifies the same counted tool result in the next Reviewer and revised Solver
requests. Scheduling tests cover slot reuse by another sample during CPU work,
one local worker across 16 admitted episodes, cancellation before submission,
repeated cancellation during a started tool, and no work for unselected tools.

The first local test invocation accidentally imported an older installed checkout
because the shell did not preserve the intended import path; it made no external
contact. The successful invocation explicitly bound the absolute successor source
path. Retain both logs and use explicit checkout paths for all subsequent commands.
These are engineering checks, not quality evidence or an admitted GPU experiment.
