# Shared implementation for the next complete-system candidate recovery

Status: ENGINEERING PARTIAL; no new model contact, admitted flight, learned
policy update or quality gain. The evidence-path comparison is closed at
cbbb1857. This implementation addresses two concrete dependencies of the
planned F4 complete-system comparison, using the existing shared base.

## Explicit common knowledge rendering

Declare knowledge_value_rendering as canonical-plain-v1 in both matched
configurations. The existing PhaseToolDispatcher continues validating
named-store source identities and enforcing tool authority, but renders the
canonical value body without its automatic store-role prefix. A tool-free
configuration already uses that canonical body and acquires no dispatcher
or tool authority. Explicit invalid values fail before the no-tools shortcut.

Omit the key to retain every historical default: named-store tools retain
their prefixes, the tool-free path remains plain, and old receipts do not
gain a new field. Declared tool receipts record the explicit rendering.
This option changes presentation, not store selection, legal tool actions,
source custody, tool result retention or final-answer authority.

The full native-graph regression uses the actual shared request builder,
OpenJiuwen execution, transport renderer and request gate with synthetic
in-process responses. Control and tool-enabled policy execute Perception,
Solver, Reviewer, Planner, revision Solver, Reviewer and Planner. All seven
requests carry identical evidence and speech packet hashes; only the declared
Reviewer exposes the target lookup schema. No tool call is fabricated.
A separate native request test executes actual synthetic lookups and confirms
fit and sent evidence agree under both legacy and explicit rendering.

## Separate source-bound candidate proposal

rails/slurp_candidate_proposal.py provides an immutable CandidateProposal.
It verifies the caller's original IDs against the existing normalized parser
over the original sealed max-three Perception artifact and its real response
hash. Original IDs and order are retained. New legal labels from selected
exemplars are ranked by support count, with lexical ties, up to the declared
total cap. Frequency is not confidence. The proposal is not an answer filter.

The public build_candidate_proposal_from_selection boundary accepts the
actual local KnowledgeSnapshot, PhaseSupply rank/fusion pair, and current
QueryState. It validates snapshot/query/rank binding, selected value/facet
membership and exact current-sample exclusion, then constructs the proposal.
The existing released-store loader and caller must still enforce the complete
TRAIN/source-roster exclusion contract; exact sample exclusion alone does not
prove utterance-level isolation.

Receipt data includes original state/response/query hashes, snapshot and
selection hashes, and the identity/content/full-value hash of every selected
example. Model text contains original and added labels and their provenance
category, without internal sample IDs, hashes, paths or raw example bodies.
The low-level pure builder is not an alternative to the bound-selection entry
at runtime. Neither constructor loads a dataset, retrieves new examples or
modifies the original Perception artifact.

## Remaining integration before GPU registration

1. In knowledge_stores.automatic_for_phase, reuse the actual local
   train-exemplars Solver selection already produced before candidate supply.
   Feed its validated rank/fusion pair into the bound proposal constructor.
   Do not reconstruct a label pool from future supplies or historical outcomes.
2. Pass the same proposal to shared candidate semantic selection. Preserve
   baseline-selected cards before appending bounded added-candidate cards;
   source-bind corresponding intent distinctions as well as slot explanations.
   Simply increasing max_candidates does not implement this policy.
3. Expose the same derived proposal through the active native context path to
   Solver, Reviewer, Planner and later revision. Preserve raw Perception.
   Record proposal/selection hashes in full-episode custody and seal verification.
   A Solver-only state_fill does not by itself prove downstream visibility.
4. Match common role text, program identity, delivery and explicit rendering
   between complete policies. Common instructions must reconcile the original
   prompt's candidate-only wording with explicit supported additions without
   silently introducing a hard answer filter.
5. Prove all-role consistency on synthetic complete trajectories, prepare the
   exact roster/config sources, and register real request fit, smoke4, full
   paired execution, budgets and terminal analysis before any model contact.

Existing roles/context policies not armed by the first F4 config need not be
expanded speculatively. Reject incompatible combinations explicitly. Static
standing fallback candidates are not an implementation of dynamic proposals;
closed fallback, semantic-delta, VAR-2 and F10 lines remain closed.

## Verification and interpretation

79 focused tests passed, including the two full native request/graph paths
and all existing target-tool tests in the focused set. All nine offline gates
have a successful final invocation. The first engineering check caught an
authoring newline syntax error in the new proposal export list; it was fixed
before contact and the affected tests/check were rerun. Logs preserve failures.

The environment has no pytest-cov plugin. The attempted coverage invocation
was rejected before tests ran. A standard-library line tracer then measured
the pure proposal module on its 14 focused tests: 207/224 executable lines,
92.41% by that tool's definition. This is not branch or repository coverage.
No dependency was installed and no editable package registration changed.

These checks prove the recorded engineering behaviors only. The proposal has
not yet been wired into a formal experiment, actual capacity is not measured,
and neither policy sampling nor real feedback update/reexecution is enabled
by this change. Terminal complete-task benefit remains the admission target.
