# SLURP continuation review and proposed experiment family

Date: 2026-10-01 (UTC). Author: ChatGPT root.
Status: REVIEW AND PROPOSAL, not a registration, countersignature, scientific verdict, or launch instruction.
Review base: master 000da6bee27fc0533bb07c32b528706c54863504.
Fable's scientific handoff refresh: 2026-09-30T16:13:00Z.
The October 1 operational inspection below supersedes older running statements.

## 1. Executive judgment

Keep SLURP as the only GPU research carrier. Preserve COMP-1b as the development-admitted intent improvement.
Prioritise slot quality, as decisions 209 and 211 require. The next question is whether the complete agent can
recognise a specific evidence deficit, acquire useful evidence, and convert it into a better delivered answer
without damaging correct answers. Only then is there a useful system action space to learn.

There is no established incremental SLU gain or automatic system-policy gain from the latest work.
That is not a failure of the Stage-2 system. It separates three evidence levels:

1. The four-node agent already improves substantially over the direct core on development rosters.
2. COMP-1b improves intent on Fold A and DEV; its DEV entity-F1 increment is inconclusive.
3. Automatic selection or learning beyond that fixed system remains unproven.

This review reads published, registered analysis reports. It does not re-score their artifacts or claim an
independent reproduction. The failed test-sample campaign was inspected for operational metadata only.

## 2. Operational correction: the milestone is blocked

Inspection of the current batch driver, both campaign members, attempt metadata, output line count, scheduled
tasks, process list and GPU state found:

- MILESTONE-00-PLAN produced 3,010 output records and recorded 12,343 model contacts.
- At 2026-09-30T18:02:24Z, bundle verification failed: the serialized manifest plan omitted owner_allowance.
  The generation attempt is ABORTED. A written manifest says COMPLETED, but that flag is not a successful seal.
- There is no score-jobs.jsonl for this attempt. No quality result was read.
- MILESTONE-01 has no generation attempt: the campaign stopped in its first member, not the representative
  treatment named by the outer queue.
- P-SV-4's dependent queue halted at 18:02:44Z on the same STOP; it did not launch.
- The serving stop receipt at 2026-10-01T00:51:02Z records the process already gone. Inspection found no active
  experiment/server, GPU memory 0 MiB and Windows free memory above 43 GiB.
- This failure is evidenced as a seal/serialization failure, not as a GPU out-of-memory event.

Code evidence: core/bundle/manifest.py writes a manual plan dictionary without owner_allowance;
core/bundle/verify.py reconstructs ExecutionPlan from that dictionary and validates it. The runtime's earlier
plan-building fix does carry owner_allowance, so preflight success did not cover the serialization round trip.

Recommended engineering scope is narrow: preserve optional authorization fields through the shared serializer,
prove ExecutionPlan -> manifest -> validation on synthetic final-report fixtures, and prove legacy no-allowance
requests/manifests preserve their intended semantics. Exercise the actual sealing path before another launch;
another broad infrastructure refactor is unnecessary.

The exact milestone protocol forbids retries, seal-only recovery, rescoring, projection changes, and partial
reads. The ordinary one-recovery rule does NOT grant a recovery here. First produce a model-free repair proof
and custody report. Any exceptional zero-generation reseal or replacement baseline requires an explicit new
owner ruling and a successor allowance that names the exact handling; do not assume such an exception.
Do not consume a spare treatment id as an informal replacement comparator. The unstarted treatment has not
been consumed, but cannot proceed with an invalid comparator. Preserve all originals.

Evidence: /home/chao/batch-status.jsonl, /home/chao/batch-campaign-1-comp1bts-20260930T131036Z.log,
/home/chao/queue-milestone.out, /home/chao/queue-psv4.out and the operational receipt beside this report.
The heartbeat has been updated to this state; it remains read-only.

## 3. Evidence retained from Fable

All numbers in this section are published development results, not test results.

| Item | Evidence | Consequence |
| --- | --- | --- |
| COMP-1b / A2 | DEV n=1,000: intent 76.90 -> 81.50, +4.60 pp, CI95 [2.58, 6.73]; SLU 65.40 -> 65.93, +0.53 [-1.04, 2.09] | Retain the intent improvement; do not claim an incremental entity gain |
| COMP-1 citation contract | Intent improved, but SLU fell 2.24 pp; attribution names increased emission, including +102 FP on zero-gold rows | Keep the citation contract out; provenance tracking must not force entity production |
| G5 / v2.1 | Reviewer instruction removes obsolete-tool narration; quality deltas are inside the null | Engineering/efficiency admission, not a quality improvement |
| P-SV-4 / K6p | Implied intent +1.06 pp from changed ranks and historical conversion; unflown | Finish the already authorised question after its dependency is legitimately resolved; no promotion from the estimate |
| Scope rule | DEV stage column +0.49 SLU [-0.01, 1.00] | No standalone efficacy claim; preserve its existing bounded status |
| REV-TFRL-1 | Versus A/A: intent -0.46 [-1.57, 0.65], SLU -0.55 [-1.79, 0.69] | More review activity did not establish benefit |
| Reviewer instrument | In the contrastive arm, 464 REVISE routes, positive precision 0.095, positive conversion 0.159; net intent -1 row | Improve information and action selection, not revision frequency |
| Core re-listen / verify-span | Re-listen replacement harms; Whisper verify-span fails the oracle precondition | Keep these specific routes closed |
| S2 missing-slot tool | Best budgeted ranker reaches 23-26 of 70 target values with Whisper; reference-text figures are 43-49 at top 3 | Do not buy another ASR pass before a valid end-to-end case exists |

Primary repository sources:
- docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md
- docs/results/2026-09-29-slurp-comp1-slu-harm-attribution.md
- docs/results/2026-09-30-slurp-v2-1-lock-v1.md
- docs/results/2026-09-30-slurp-sealed-credit-inner-loop-run-3.md
- docs/results/2026-09-30-slurp-reviewer-revision-decision-instrument-offline.md
- docs/results/2026-09-30-slurp-s1-slu-error-taxonomy-refresh.md
- docs/results/2026-09-30-slurp-s2a-ranker-study-offline.md

The file called v2.1 LOCK records an engineering-base version. It is not evidence that decision 209's
scientific closure criterion is satisfied. Other GPU carriers remain held under decision 211.

## 4. What I would refine in the interpretation

### 4.1 A printed value is not proof of hearing or grounding

On A2, 165 gold-side error items have their value printed by M1; 214 items have an undetermined origin.
These are useful availability diagnostics. A value in a training exemplar is not current-utterance evidence.
Calling every such failure a consumption failure is stronger than the observation supports.

Keep separate: (a) the current utterance's own note contains a span; (b) an exemplar contains the same string;
(c) a schema describes a type; (d) the model explicitly associates current evidence with that type; and
(e) the association survives revision and delivery. Track source, intent relevance, type, boundary and
ambiguity, not string occurrence alone. A missing note span also does not prove a hearing failure.

### 4.2 Oracle, transported conversion and system gain are different quantities

S1's A2 errors include MISSING 188, SPURIOUS 249, WRONG-TYPE 67 and BOUNDARY 73. Their isolated oracle gains
must not be summed as a prediction. Repairs overlap, and micro F1 is nonlinear.

The S2 ranker benchmark queries each target with its GOLD slot type. It does not measure a model's ability
to choose that type or decide to call. Its false-candidate rate averages all 55 types, not the actual
model-selected query distribution. Both matter for deployment.

Likewise, T multiplied by the historical CONV uptake 0.457 is a transported scenario estimate, not a
mathematical upper bound on a new system. It omits call selection and new false positives; the uptake
came from another intervention/population. Preserve the registered historical ruling, but do not reuse
that multiplication as a universal feasibility theorem.

The LR ranker was supervised-fitted on TRAIN. It is a diagnostic learned model, not automatically a
training-free runtime component. Runtime admission would need to reconcile it with the no-task-trained-model
boundary. This plan does not deploy it.

### 4.3 Complete-system reward is not a Solver-column score

Current level-2 columns and sealed-credit estimates are excellent screening instruments. They do not
necessarily execute an independent Reviewer/Planner suffix for every alternative. A new system-policy
experiment must give every alternative its own complete suffix and terminal delivery.

The run-3 compositions explicitly add estimates across arms/rosters without deduplicating affected rows.
They rank hypotheses, not establish policy value. Historical action propensities were not generally
randomised or logged, so unsupported off-policy estimates are not a substitute for new execution.

## 5. Proposed sequence: one bounded family at a time

These are questions and analysis plans. Their thresholds support a later root judgment, not an automatic
winner declaration or dispatch.

### R0. Close the milestone incident and clarify scientific closure

Deliver the model-free serializer proof, original-artifact hash inventory, two-member status receipt,
and an explicit owner recovery/closure decision. No new generation or scientific reading of the failed arm.

For pending decision 210, recommend the prior Fold A -> DEV replication plus one valid, predeclared milestone
read as the present stability criterion. Repeating the same arm on the same sample diagnoses execution
variability; it is not a fresh-data replication. Keep any final closure-roster read under its separate
allowance. Do not redefine closure after seeing a milestone result.

### R1. Finish P-SV-4 as the remaining intent item

Keep its registered configuration and order until the coordinator resolves the failed predecessor.
Read K6p, the delivering branch and the twin, with the selection-on-both-folds disclosure. Its +1.06 pp
is a nomination estimate. If later considered for inclusion, it needs the already proposed fresh-roster
form and a complete-system check. Decision 213 must not promote a Solver-only column to final-system gain.

Do not open another general intent expansion campaign.

### R2. Audit the slot action space before spending on more sampling

Reuse the existing S1, node-state and sealed-credit extractors on authorised TRAIN construction material.
Add only the missing associations, not another taxonomy or execution framework:

- available evidence versus current-utterance-supported evidence;
- first Solver answer -> review decision -> revision -> delivered result;
- exact saves, exact harms, omissions and false emissions;
- decision-time observability of each proposed trigger;
- state/action support and whether the compared episodes share input and predecessor.

The main target is a wrong or missing TYPE/BOUNDARY association despite relevant current evidence, including
the case where the same string appears under several intent/type interpretations. This must be distinguished
from genuinely missing acoustic content, which the present knowledge cannot supply.

Keep intent and slot stores separate. Intent values explain why one candidate applies. Slot values explain
type meaning, scope, span and normalisation. Candidate intents supply a SOFT union of type priors, not a hard
whitelist; preserve out-of-list correction and empty retrieval/empty entity answers.

Deliver a finite action manifest with evidence sources, eligible decision state, known harms, support,
predicted complete-system increment and uncertainty. If only generic rereading or a closed rule-card
mechanism is available, record that the action space is not yet adequate for RL.

### R3. One candidate capability question: targeted evidence verification

Proposed hypothesis: a model-requested, slot-specific evidence check can discriminate between two concrete
interpretations better than another generic review of the same answer.

This is not a re-opening of S2's Whisper missing-value route, forced citations, hard type masking, or W4's
general rule cards. It qualifies as a new action only if R2 identifies a different, useful evidence relation.
Otherwise do not register it.

Possible implementation through the existing provider and controller:

1. Reviewer marks a specific uncertainty: presence, type or span. It does not replace the answer.
2. Planner chooses whether a further check is warranted.
3. At the designated Solver visit, the frozen core may invoke a bounded evidence lookup with its own proposed
   type/ambiguity. The system offers the function; it never calls on the model's behalf.
4. The result separates current-input evidence, TRAIN analogy and schema facts, with ids and source hashes.
   It may be empty. Similarity never makes a suggested value mandatory.
5. Solver decides whether to preserve, revise or leave empty. It retains final answer authority.

If the evidence cannot be grounded without a new speech tool, stop at that dependency; do not fabricate
a transcript, alignment or confidence. The stronger-ASR question remains held.

A prospective capability design uses one preregistered TRAIN roster of at least 400 eligible, unique utterances
(the exact inventory must be verified), with four COMPLETE episode paths: current system; its request-identical
twin; evidence offer; and equal-extra-contact rereading without new evidence. The latter separates the effect of
information from more compute. Execute each path through the same runtime; no branch borrows another branch's
review or final answer. Balance path order. The no-op twin estimates this design's actual variability.

Report full-roster official SLU-F1 and intent, as well as call precision, recall, acceptance, repairs and harms.
The diagnostics do not replace terminal reward, and gold-selected problem subsets cannot become runtime gates.

Decision 192 currently requires an offline >=1.5 pp prediction at a measured conversion before a slot mechanism
is registered; a different roster/design may require an even larger detectable effect. This candidate has no
measured conversion yet. Consequently it is HELD: either R2 supplies adequate evidence, or the owner must
explicitly authorise a bounded capability-measurement exception. Do not relabel it engineering to bypass the gate.
No current benefit expectation is asserted.

### R4. Learn the policy only over supported complete-system actions

Once at least one useful alternative exists, retain the admitted fixed system as anchor. Freeze knowledge
construction while learning consumption. Start with a small finite action set: default continuation and the
qualified evidence-offer policy. Every policy still lets the model decline tools.

State contains only pre-action observable variables: candidate agreement, slot-type ambiguity, evidence
availability/provenance and structured reviewer issue flags. It contains no gold-derived error class or
future answer. The sampled action is an external workflow/offer policy; its probability is logged exactly.
The model's subsequent tool-call decision is separately logged, not falsely assigned that same probability.

Record full episodes: observation -> retrieved supply -> Solver -> Reviewer/Planner -> optional tool ->
revision -> normalised delivery. Reward comes from the final official word/char entity counts. Use a
pre-frozen baseline F0 in [0,1] for construction utility:

    u_i = 2 TP_i - F0 (2 TP_i + FP_i + FN_i)

For a fixed complete roster, positive SUM(u_i) is equivalent to pooled F1 exceeding F0 when the denominator
is positive. A change in summed utility across two arbitrary policies is only a surrogate for the change in
their F1, so admission always uses official pooled F1. Empty-gold false emissions receive negative utility.
Keep intent correctness, format, tool costs, failures and fallbacks as separate fields/guards.

Within each input group, compare terminal returns (group-relative advantages) and keep failures in the group.
Update an external state/action utility table or a bounded set of evidence-use memories after a whole batch;
the core weights remain unchanged. Freeze the policy and knowledge throughout the batch.

Important batch distinction: the current rule A4 prohibits policy updates from fewer than 200 rows.
A compatible proposal uses >=200 unique construction inputs per logical update, streamed through the existing
4 live slots, with up to 4 sequential complete trajectories per input. This is NOT 200 or 800 simultaneous
GPU requests. It preserves the owner's batch-update preference without reviving the 4-input efficacy mistake.
Two update batches establish the minimal sample -> update -> execute -> update loop; their construction scores
are not evaluation evidence. This is a proposal, not an authorised new sampling budget.

Initial algorithm should be simple and inspectable: cumulative state/action utility with sparse-state shrinkage
to the global action estimate, followed by a fixed exploration rule. First batch balanced; subsequent batch
80% current preferred offer policy / 20% uniform exploration, subject to preregistration. Unsupported states
fall back to the fixed baseline. No small bucket is declared effective on its own.

A single policy decision with terminal reward is contextual bandit optimisation. Call it that. Extend to
multi-step RL only after separate retrieval, tool and revision decisions have identifiable support and
whole-trajectory returns; do not claim GRPO reproduction merely because advantages are grouped.

### R5. Test whether learning adds anything

Freeze the final policy, memory and knowledge before evaluation. Compare, in one controlled family:

- the current fixed system with its in-chain A/A;
- the best fixed action chosen on construction data;
- the learned, frozen state-dependent policy;
- a frozen-update control with the same action space and collection protocol.

Use identical inference sampling budgets and the full system. The decisive contrast is learned policy versus
best fixed action; comparing only with the old anchor can mistake an added capability for learning.
Predeclare the statistical design and all comparisons; do not select the best checkpoint on the evaluation
scores. Report final checkpoint and construction trajectory. A shuffled-state diagnostic is optional only
if it has a distinct decision use and is preregistered.

Use construction/evaluation partitions by utterance and audit overlap with every knowledge source. Both TRAIN
folds are exposed; DEV-2000-ADDED has extensive development exposure. Do not call any of them untouched.
A new qualification roster requires an explicit registered allocation; the milestone sample is never used
for policy learning or root-guided tuning.

## 6. Training-free references and limits

The official [MemRL implementation](https://github.com/MemTensor/MemRL) separates frozen reasoning from
feedback-updated episodic memory and uses two-stage retrieval. Borrow its external-utility principle;
do not claim its benchmarks or full implementation have been reproduced here.

[Training-Free GRPO / Agent Practice](https://github.com/TencentCloudADP/youtu-agent/blob/main/utu/practice/README.md)
implements grouped rollout, semantic advantage and iterative experience updates without LLM parameter
updates. It is a useful algorithm comparator after the system action space exists. Its defaults, API calls
and dataset assumptions are not an admission to this repository.

Do not reopen the closed semantic-delta line under a new name. First compare numerical action-value updates
within the finite space. A later semantic-memory method needs separate admission and the same full-system
evaluation. Root-designed context changes remain engineering/research design, not algorithmic learning gains.

## 7. GPU and engineering schedule

While R0 awaits a ruling: only the narrow repair proof, R2 preparation and existing result interpretation.
Never clear STOP or detach P-SV-4 from its dependency automatically.

At an authorised boundary, retain Fable's verified decoder-only, no-mmproj, np4 x 24,576 geometry if the exact
new requests fit with full role output reserves and the registered safety margin. Prepare speech packets first.
Logical sampling batches do not change live-slot count. Preserve static prefixes and put variable policy/evidence
tails after the shared prefix where request semantics allow it; order balancing must not be replaced by
permanently running one policy last.

Use the Windows-owned WSL driver, local scorer and local manifests; network, assistant credits and heartbeat
are never dependencies. Check host/GPU headroom before launch, keep >=10 GiB for Windows and any stricter guard,
record resource samples every 10 seconds, and do not infer health from an old session's telemetry.
One generating flight and one scorer; CPU preparation stays within the aggregate registered limits.

Reuse FlightRuntime, the controller, KnowledgeProvider, OpenJiuwen, module compiler, official scorer and
sealed-credit records. If independent complete suffixes are unsupported, either add the smallest shared
extension or use whole-arm execution with A/A; do not pretend current Solver columns already implement it.
Code lives in one isolated worktree and is merged serially by the coordinator at a safe boundary.

## 8. Decisions and expected outcomes

Needed next, after concrete evidence is ready:

1. Milestone incident disposition: a successor allowance or an explicitly authorised zero-generation sealing
   exception. No action is implied by this report. The default is preserve and stop.
2. Closure definition 210: recommend Fold A -> DEV replication plus one valid milestone, with the final
   closure read separately governed. Do not spend repeated sample reads chasing a positive result.
3. S2/212: recommend no stronger-ASR pin/pass now under the failed current contract. A changed query
   policy or evidence source is a genuinely new question, requiring a new design.
4. R3: decide on a bounded capability-measurement exception ONLY if R2 cannot meet decision 192 yet gives
   a concrete, non-circular information-gain hypothesis. Until then it remains a design.
5. P-SV-4/213: preserve the existing authorised item, and specify the future replicate form before results
   guide its choice. Other carriers remain held until SLURP scientific closure.

Expected deliverables are an honest closure of the current incident, a grounded slot-action ledger, one
capability measurement if justified, and a frozen system-policy comparison if an action space qualifies.
A null action-space or learning result is a valid outcome. No numerical gain is promised.

## 9. Document validation and integration

English-content validation, referenced-document existence, operational JSON parsing and git diff whitespace
checks passed. The existing experiment_handoff_check returned INVALID in this managed checkout because it
could not read a required handoff file or local Git metadata; no experiment-authority result was established.
Subsequent explicit WSL Git root/HEAD reads succeeded. This is a documentation-only branch, not a launch-ready
package. Let the current coordinator merge it serially; no shared active checkout or frozen flight was changed.
