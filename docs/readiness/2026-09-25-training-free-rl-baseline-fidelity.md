# Training-free RL baseline fidelity and SLURP adaptation

Status: source-audited design, not an executed algorithm comparison.
Keep the current order: qualify actions, validate complete-system returns,
then sample, update and re-execute. Do not reopen the closed semantic-delta
application campaign through a renamed prompt experiment.

## Frozen external references

Read-only upstream code was downloaded outside the repository. Exact file
hashes are recorded in
docs/receipts/continuation/2026-09-25-training-free-upstream-source-pins.json.
No upstream code or package enters the study runtime in this step.

- MemRL: MemTensor/MemRL, commit
  c1b322ca43de36ddf64c6712f89d0095bfc35ce0 (2026-07-17).
- Training-Free GRPO: TencentCloudADP/youtu-agent, commit
  c2caa539f4c95ae1c39ed24dc8a99cb3651e1d5d (2026-03-21).
  This is the pinned implementation of the earlier method, not a claim that
  Training-Free GRPO originated in 2026.

## Findings from implementation, not just the abstract

MemRL's Q updater applies
Q <- (1-alpha) Q + alpha (reward + gamma max_next_Q).
The inspected config defaults to alpha=0.3 and gamma=0; a Q floor is optional.
It changes memory metadata and preserves the memory retrieval key.
[Source](https://github.com/MemTensor/MemRL/blob/c1b322ca43de36ddf64c6712f89d0095bfc35ce0/memrl/service/value_driven.py)

The inspected service exposes more than one retrieval path. Its local
retrieve_query ranks by a mixture of normalized similarity and Q, then uses
epsilon-greedy selection; the LifelongAgentBench runner calls that path.
Do not label every code path a faithful implementation of the paper's
two-stage retrieval description. Its batch update_values maps truthy
success values to success_reward, otherwise failure_reward, and assigns
that outcome to every retrieved memory in the trajectory.
[Service](https://github.com/MemTensor/MemRL/blob/c1b322ca43de36ddf64c6712f89d0095bfc35ce0/memrl/service/memory_service.py),
[runner](https://github.com/MemTensor/MemRL/blob/c1b322ca43de36ddf64c6712f89d0095bfc35ce0/memrl/run/llb_rl_runner.py)

Training-Free GRPO iterates rollout batches, experience updates and scheduled
evaluation. Its experience updater summarizes trajectories, derives semantic
group advantages, then consolidates experience updates. A single reflection
or a manually edited prompt does not reproduce that loop.
[Loop](https://github.com/TencentCloudADP/youtu-agent/blob/c2caa539f4c95ae1c39ed24dc8a99cb3651e1d5d/utu/practice/training_free_grpo.py),
[updater](https://github.com/TencentCloudADP/youtu-agent/blob/c2caa539f4c95ae1c39ed24dc8a99cb3651e1d5d/utu/practice/experience_updater.py)

## Consequences for this study

These are root inferences from the inspected implementations and SLURP results.

1. Do not feed a fractional SLU score or signed utility to a success-boolean
   update API: almost every nonzero number, including a negative number,
   is truthy. Preserve the declared continuous feedback and record that
   adaptation; keep intent correctness as a separate protected outcome.
2. Crediting every retrieved memory with the same terminal outcome does not
   identify which evidence helped. VAR-2 was intended to supply matched-prefix
   action evidence, but both attempts failed and the family is closed without
   that result. Its planned side branches also lacked independent downstream
   Reviewer/Planner trajectories. Only complete-system trials can supply
   the return for a deployed action-selection policy.
3. Memory values should represent supported conditional action experience
   (state, action, outcome, count, provenance), not a copy of the training
   corpus. Knowledge continues to hold released task semantics and examples.
4. Keep runtime selection independent of online external APIs. Use frozen,
   already-prepared speech representations and observed pre-action state;
   update external values only from complete construction rounds.
5. A fixed-action search can improve the system without demonstrating an RL
   benefit. Compare the frozen learned selector with both the locked default
   and the best eligible fixed action under matched evaluation conditions.

## Baseline ladder and labels

| Baseline | Updated object | Required cycle | Scientific label |
| --- | --- | --- | --- |
| Locked system | Nothing | Repeated complete evaluation | System comparator |
| Best fixed eligible action | One construction configuration | Complete fixed-action validation | Configuration-search comparator |
| First finite policy | State-action cumulative mean values | Balanced round, score, update, 80/20 round, score, freeze | Contextual bandit with complete-system return; MemRL-inspired adaptation |
| Faithful MemRL-style memory policy | Per-memory values plus pinned retrieval/credit rule | Sample, attribute, update, retrieve again, frozen evaluation | Adapted MemRL baseline, with every deviation enumerated |
| Training-Free GRPO comparator | Bounded experience/policy context | Grouped sampling, feedback, semantic update, re-execution | Adapted TF-GRPO only when the full loop is actually executed |

The approved first finite policy deliberately uses cumulative means instead of
the upstream fixed alpha. It is not full MemRL replication and cannot by itself
complete the scholarly-baseline objective. A same-space algorithm comparison
must be registered after useful actions and return semantics are established.
The closed historical delta results remain evidence about that application,
not evidence that all TF-GRPO or GEPA implementations fail.

## Feedback limitation to keep visible

The frozen-baseline utility is u=2TP-F0(2TP+FP+FN), using official combined
word/character counts. With a positive denominator, positive summed utility
implies pooled F1 above F0. It does not guarantee the same ordering between
two improved policies when their denominators differ. Therefore utility is
the optimization signal; official pooled F1, intent and error decomposition
remain the evaluation criteria. The zero-denominator convention remains
explicit. No reward formula is tuned after observing validation results.

## Still required

Qualify action availability and behavior; execute complete-system exploration
rounds with logged action probabilities and frozen policies; verify that the
state exists before the action; freeze policy and provenance; evaluate against
the strongest fixed action; replicate before claiming stable gains. Keep new
DEV and test access closed under the existing data boundary.


## Verified TF-GRPO feedback-interface adaptation requirements

On 2026-09-25, root rechecked the pinned experience_updater.py and executed
only its grouping/filter prefix, extracted through Python AST before model
setup. All six synthetic cases passed the asserted source behavior. No research
outcome, model, scorer or backend tool was contacted. See
docs/receipts/continuation/2026-09-25-tfgrpo-feedback-interface-audit.json.
These findings constrain the future SLURP bridge; they do not show an error
in the upstream binary-reward/text-task setting or an efficacy result.

The existing high-level source audit is insufficient to implement the bridge
unchanged. Four specific differences must be declared:

1. Group by the registered speech input identity, not instruction text.
   The upstream grouping at lines 82-85 uses raw_question. In the synthetic
   case, four records with distinct speech identities and identical task
   instructions collapse into one four-member group. Bind the SLURP split,
   sample ID, original speech packet and round before grouping. Repeats must
   share the original input; their internal states and actions may differ.
   Preserve the rendered task text separately from this identity. Do not
   substitute a reference transcript as a convenient grouping key.

2. Separate numeric feedback from reference-answer disclosure.
   The upstream given_ground_truth switch controls both answer insertion
   (lines 116 and 180) and reward visibility (line 168). Setting it false
   also redacts the group reward. A SLURP adaptation must retain authorized
   construction counts/utility/intent feedback for the offline updater while
   keeping reference-answer text out of model contexts and all task feedback
   out of actor contexts. Merely setting the upstream switch false is not a
   feedback-preserving bridge. Inspect the critique field as well; it must
   not become an indirect reference-answer channel.

3. Replace the binary-reward group eligibility rule explicitly.
   At lines 90-95, and again at 151-156, the upstream rule retains groups
   whose mean reward is strictly between zero and one. With binary rewards,
   this identifies groups containing successes and failures. It is not a
   general test for different outcomes: the exact prefix retained two tied
   rewards of 0.2, but dropped the distinct signed utilities [-2, 1] and
   [2, 3]. The false-ground-truth mode bypasses this filter, but also hides
   the reward as described above.

   Use the existing complete-system grouping artifact to retain every input,
   all ties, official count differences, intent differences and empty-target
   errors. If a later semantic-update registration selects informative groups,
   define eligibility prospectively from those separate feedback fields and
   report every excluded group. Do not convert signed utility to boolean or
   shift/clip it into a success score merely to satisfy this source filter.
   Empty-group and all-tie behavior must be defined before any update contact.

4. Serialize a complete system episode as one trajectory.
   Line 115 reads only json.loads(item.trajectories)[0]["trajectory"].
   An adapter that places Perception, Solver, Reviewer and Planner in separate
   top-level entries would expose only the first entry to this summary path.
   Bind one complete ordered episode, including tool results, revisions,
   finite failures and final delivery, with links to its verified sources.
   This does not imply upstream trajectories are inherently incomplete; it
   identifies an incompatible carrier mapping to avoid.
   Preserve update failures and missing summaries explicitly instead of
   silently treating successful summaries as the entire collection.

For fidelity, preserve the full upstream algorithmic stages: per-trajectory
summary, semantic group comparison, group-level experience operations, batch
consolidation, and execution using the updated frozen experience. A numeric
advantage table is not a substitute for the semantic stages. Register all
updater contacts, retry bounds and local frozen-core usage before execution;
the read-only audit adds no authority for those contacts.

Before a same-space comparison, bind the permitted role/context locations of
learned memory and the executable system actions for every algorithm. A semantic
method must not silently receive new tools, facts, routes or revision limits
unavailable to the numeric comparator. If the semantic updater is constrained
to conditional choices over the admitted complete-policy catalog, label that
restriction as an adaptation. If it can alter a wider policy surface, evaluate
and report that as a different search space rather than an algorithm-only win.

The active fixed evidence-path pair remains unchanged. Its complete terminal
evidence still determines the next system-action question. This audit neither
reopens semantic-delta nor enables a new contextual policy or semantic update.


## Implemented complete-episode summary carrier

The source-only representation gap is now implemented in the shared analysis
module. Read 2026-09-25-complete-system-semantic-summary-input.md. The pinned
upstream first-entry extraction returns the complete role/tool/delivery episode,
with exact request-field deduplication and speech/split/round grouping identity.
Reference annotations and scores remain outside summary fields.

This does not resolve the distinct feedback-visibility, signed-group eligibility,
experience-operation, consolidation, action-space or reexecution requirements.
It creates no model client and authorizes no semantic update. Current research
GPU execution remains the registered complete-system candidate-recovery pair.


## Terminal objective counterexamples and a separate candidate comparator

Read 2026-09-25-system-terminal-ratio-objective-audit.md. The synthetic audit
demonstrates that frozen-reference utility can rank two complete policies
differently from pooled F1, local-state F1 optimization can disagree with the
population objective, and averaging standardized group advantages can erase
terminal error magnitude. These are mathematical limitations, not observed
failures of a research policy or the upstream semantic updater.

An exact finite-table fractional optimizer matches exhaustive search in the
synthetic audit. It is a classical-method prototype, not an activated learner.
Any ratio-aware learning comparison must be separately registered, retain the
frozen-F0 baseline and same action space, address estimation/support and intent
protection, and execute full-system evaluation and replication.


## Implemented terminal feedback preparation

Read 2026-09-25-system-semantic-feedback-inputs.md. The shared pure join now
binds every complete episode to separate signed count/intent/format feedback.
The versioned terminal-outcome-vector disagreement rule retains all groups
and explicitly marks all-tie no-update cases. Reference-answer and arbitrary
critique text remain excluded. This does not itself execute a model-facing
comparison or fix the upstream flag/filter unchanged; the future adapted
updater must consume the separate channel under its own registration.

Summary inference, recorded summary-to-feedback joins, semantic operations,
consolidation and full-system reexecution remain outstanding. The current
registered candidate-recovery pair and historical frozen-F0 baseline are
unchanged; no runtime application or learned-policy benefit is established.

## Verified cross-round consolidation behavior

The pinned upstream plan applier was executed on seven synthetic cases, using
only the exact AST suffix at lines 304-327 after its model response is parsed.
No upstream import, research trajectory, model, network or scorer was involved.
Read docs/receipts/continuation/2026-09-25-tfgrpo-consolidation-source-audit.json.
The replay script is scripts/checks/tfgrpo_consolidation_source_audit.py; it
requires the pinned source bytes and refuses a changed source or output overwrite.

The verified cases distinguish implementation behavior from observed frequency:

- Dense IDs 0,1 followed by ADD produce 0,1,2 as intended.
- Sparse IDs 0,2 followed by ADD overwrite existing ID 2. The allocator starts
  at the number of entries rather than an unused ID. A legitimate deletion in
  one round followed by ADD in the next reproduces this loss.
- DELETE without content is skipped; DELETE with content removes the target.
  This describes the parser's current contract, not the frequency with which
  the model follows or violates its prompt.
- UPDATE of an unknown ID becomes ADD and can trigger the same collision.
  An unknown operation is silently ignored.

These are synthetic source-level counterexamples, not measured SLURP failures,
evidence against the paper, or an explanation of the closed delta results.
They do not change the running fixed-policy family or its scientific gate.

For the future adapted TF-GRPO baseline, keep summary, semantic comparison,
group operations and batch consolidation as distinct model stages. The final
plan applier must use persistent never-reused experience identities, require
an explicit operation, validate update/delete targets, and apply a validated
batch atomically to a new immutable snapshot. A deletion should not require
invented replacement content. Keep malformed operations and failed stages in
the round receipt; do not silently report only successful updates. Record
these as reliability adaptations to the pinned implementation, separately
from any proposed algorithm improvement.

Preserving an experience does not prove it helps the complete system. Candidate
snapshots still require the same permitted role/action surface, real frozen
reexecution, terminal official scoring and matched replication. The active
worker, its outcome embargo and the closed application families remain unchanged.

## Implemented atomic candidate consolidation

The pure shared adapter in rails/experience_consolidation.py applies the final
ADD/UPDATE/DELETE plan to the existing ExperienceRecord type. It is the
deterministic plan-application step, not a second memory runtime or a semantic
optimizer. The upstream summary, comparison, group-operation and model-facing
batch-consolidation stages still need registered execution.

The input contract requires a pinned base snapshot, a round ID, already
materialized provisional proposal records, and separate source hashes for
complete-system feedback, the proposal artifact and the consolidation response.
The caller must authenticate those sealed sources with existing verifiers;
integrity hashes alone cannot prove that a supplied record came from a complete
system trajectory. Reference annotations never become runtime memory.

The adapter implements these deliberate reliability adaptations:

- Let the model select explicit operations and existing proposal/record IDs.
  Allocate immutable new record identities in the adapter. Keep all issued
  identities, including deleted and superseded records, across rounds.
- Preserve unchanged records byte-for-byte. UPDATE creates a new revision
  linked to its predecessor; it cannot replace the old record in place.
- Reject unknown operations, missing targets/proposals, conflicting operations,
  duplicate active content, invalid sources and changed admission status.
  Reject the whole batch without returning any partial successor.
- Allow DELETE without content. Retain an explicit unchanged receipt for an
  empty plan and allow deletion of all candidates without inventing a fallback.
- Retain the submitted plan, source pins, proposal hashes, operation mapping and
  failure reason in a separately hashed receipt. Never count a rejected batch
  as an update. Snapshot dictionaries returned by this pure API are detached
  values; persist them with the existing preparation layer before reuse.
- Preserve provisional status. Existing admitted-memory loading still refuses
  these records. Candidate source attestation and registered, disjoint TRAIN
  evaluation remain necessary; this snapshot is not a runtime manifest.

Multi-round tests cover sparse imported IDs, deletion followed by addition,
successive revision lineage, late-operation failure, malformed plans, invalid
unused proposals, source-population isolation and existing runtime refusal.
Read docs/receipts/continuation/2026-09-25-semantic-consolidation-validation.json
for the executed tests and offline gate results.

This step does not yet connect the adapted update snapshots to the existing
candidate source-attestation materializer. Complete that binding before any
registered reexecution; do not relabel a consolidation snapshot as an original
proposal artifact. Summary inference, complete semantic update-stage receipts,
same-space admission, frozen execution and matched replication remain open.
No new model/tool contact, source-result read, scoring or running-worker change
was made for this implementation. There is no learned-policy benefit claim.

## Consolidation lineage now connects to candidate evaluation

The distinct consolidated-candidate schema now replays original typed-proposal
materializations and each sealed operation plan through the existing source
attestation and runtime reader. Read
2026-09-25-consolidated-candidate-materialization.md. This supersedes the earlier
statement that deterministic update snapshots have no candidate-attestation
connection. It does not supersede the outstanding model-facing stages,
same-space registration, real frozen execution or replication.

The current operation space selects, replaces or deletes already materialized
proposal records. It cannot invent rewritten content in a consolidation plan;
new content must first be a source-bound typed proposal. Report that restriction
when comparing to the pinned upstream free-form consolidation rather than
presenting this adapter as an unchanged TF-GRPO reproduction.
