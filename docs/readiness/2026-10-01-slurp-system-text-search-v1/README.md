# SLURP joint system-text optimization: implementation and preregistration

Date: 2026-10-01. Authority: the owner's approved implementation plan in the
current ChatGPT conversation, recorded as owner decision 214. This package
supersedes decision 212's finite-action F2/F3 research design for this sequence.
It reuses the prepared F1 knowledge interface and data assets. It neither releases
the old F1 cells nor changes any milestone allowance, held proposal or queue.

## Research contract

Optimize the complete combination of knowledge construction, organization,
supply and consumption. Jointly change English text and already implemented
configuration. Do not require independent component benefit or component
ablation for progression. Keep Omni weights, speech input, intent retrieval and
vote mechanism, ontology, shared executor, tool interfaces and official scoring
fixed. Retain one model-initiated lookup, at most two returned slot entries and
one extra Solver revision. Keep final answer authority with Omni. An empty tool
result and declining to call are legal. Do not optimize unused slot-key text or
introduce a new ASR, retriever, answering model or closed research line.

The initial system is the COMP-1b shared base plus the prepared targeted slot
opportunity. It is a starting configuration, not a previously established gain.
Knowledge construction instructions, explanatory value fields, bounded supply
settings and Solver/Reviewer/Planner English texts are jointly editable.
Knowledge and optimizer experience have separate storage and consumers. The
optimizer's historical evidence must never become a runtime answer database.

The algorithm is whole-system reward-guided, parameter-free black-box text-policy
iteration. Runtime state is visible context/history; runtime actions retain the
existing language and tool interfaces. Do not introduce an enumerated state table,
invent language-action probabilities, importance weights or KL, or call this
PPO, GRPO or parameter training. The old finite-action implementation remains
compatible but does not run this search.

## Three updates and the feedback-blind control

Use one pinned GPT6 proposer version throughout the comparison. A switch to Fable
5.1 or another version is a separately registered factor. Fresh isolated sessions
must share no conversation history. Freeze exact input manifests, settings,
context/output limits and actual responses. The current research conversation is
not a valid blind context. No paid API spend is authorized.

The learning branch L receives only its own complete trajectories, official
terminal counts, actual execution costs, changes, failures and cumulative history.
Its two proposals per update are a joint parent revision and a revision that may
combine historical complementary versions. The blind branch B independently
proposes from the original seed each round, without this experiment's trajectories,
scores, selection outcomes or winner history. Its evaluator may select a final
winner without feeding that selection to its proposer. Give both branches the
same proposer invocation count and token ceilings. Record missing token telemetry
as unavailable; do not claim total compute matching without complete metering.

Freeze every round before execution. Compile complete candidates. A construction
instruction change must actually produce successor knowledge and pass the shared
source/release checks. Do not evaluate an edited recipe with unchanged knowledge.
Execute each candidate through the complete shared system, including all subsequent
roles, tool branches and final delivery. Seal and score every admitted member
once before forming feedback or generating the next update. A branch may use
point estimates to choose its next parent; this is search, not scientific adoption.

Every proposal opportunity is consumed even if the output is invalid, duplicated
or unchanged. Preserve its exact bytes and diagnosis; never repair it silently or
generate a replacement. An invalid proposal is excluded before any model contact
and consumes its proposal slot. Register such exclusions and the exact admitted
family before running that family. A failure after an admitted flight starts
does not become an exclusion and does not permit partial-family feedback.

## Prospective rosters and upper bounds

The machine-readable `protocol.json` binds each source receipt, exact ordered
membership, stage and quota. Sort TRAIN by SHA256 of UTF-8 `20261001:<sample_id>`,
ascending, with sample ID as tie-breaker. Preserve the existing DEV order.

| Stage | Roster | Complete systems | Trajectory cap |
|---|---|---|---:|
| Initial feedback | R01C625, first 400 | Seed and identical A/A | 800 |
| Update 1 | Fold A1080, first 400 | Parent, parent A/A, two candidates per branch | 3,200 |
| Update 2 | Fold A1080, positions 401-800 | Same eight member slots | 3,200 |
| Update 3 | Fold B1080, first 400 | Same eight member slots | 3,200 |
| Frozen selection | Fold B1080, positions 401-800 | At most two per branch, seed and A/A | 2,400 |
| Development regression | Existing DEV-2000-ADDED, 1,000 rows | Seed, A/A, frozen L and B winners | 4,000 |
| Total | | Excludes separately registered FIT, engineering and construction | 16,800 |

There are twelve candidate opportunities. Thirteen model contacts and one actual
knowledge invocation per system trajectory are upper limits, not expected costs.
Retries and extra contacts cannot be hidden outside the registered caps. Proposer,
construction, FIT and engineering contacts require their own registrations. No
automatic additional sampling is allowed. The 32,768 input / 4,096 output token
ceilings in the draft proposer protocol apply symmetrically and must be verified
against the selected transport before use. The exact proposer version is pending
transport pinning, not silently inferred from a marketing name.

All these rosters have historical exposure; DEV is not a fresh holdout. Preserve
utterance-level separation, including recording variants. The source audit
rechecks all three seed stores against all roster sources. Each successor must
also include the transitive sources of proposal, feedback, construction and
selection. Deleting knowledge or experience never deletes exposure ancestry.
Do not use the independent PLAN/COMP-1b milestone results, test labels, closure
rows or old failed artifacts for this search or borrow their allowance.

## Feedback, retention and analysis

Official pooled SLU-F1 is the endpoint. Keep intent correctness, reliable completion,
failure/abstention and cost separate. For each complete trajectory compute
`u = 2 TP - F_ref * (2 TP + FP + FN)`, pooling the official word and character
sufficient counts. Freeze F_ref from the initial seed's official aggregate on
the zero-to-one scale. Empty entities have zero utility when both sets are empty;
false positives on an empty reference are penalized. Failed/abstained rows stay
in the registered cohort and retain their scorer counts and dispositions.

Same-input relative returns are descriptive whole-trajectory comparisons.
Zero variance gives zero. Recompute them inside L's own view; blind outcomes
must not leak through a shared normalization. Do not claim node-level causal
credit or policy gradients. The feedback index covers successes, failures, ties
and harmed cases, with exact trace/output pins; summaries must retain source
addresses and explicit omissions. A compact projection never grants access to
unregistered sources.

Keep all history. Maintain true non-dominance on official quality, intent and
actual model/tool cost within one common cohort. A balanced candidate need not
win any single axis to remain non-dominated. Keep at most two active candidates
per branch. Never merge scores from successive, different rosters into a global
frontier. Compare historical survivors on the common selection roster.

The final primary comparison is frozen L versus frozen B; the secondary is L
versus the seed. Report quality-cost tradeoffs, confidence intervals, same-chain
A/A and natural-mixture/equal-stratum descriptive results. Apply the existing
measurement floor and intent protection at the appropriate own null. Root reads
the complete final family and decides whether the combination helped, feedback
helped, evidence is insufficient, or no effective solution was found. Three
updates are one registered learning sequence, not three independent search
replications or evidence of general recursive self-improvement.

## Engineering implementation

Reuse `TaskAdapter`, `KnowledgeProvider`, `EvidenceAgentController`, `FlightRuntime`,
OpenJiuwen, the consumption compiler, semantic knowledge materialization and
verified reward links. There is no new runtime controller or answering path.

- `SystemTextPolicyBundle`: content identity of the complete bundle, all parents,
  English construction/role texts, legal supply configuration, actual knowledge
  pins, build receipt and cumulative provenance. Canonical JSON prevents nested
  mutation. Optimizer experience does not enter compiled runtime configuration.
- `TextPolicyUpdateProposal`: a provisional joint edit over the declared surface.
  It cannot mutate authority, model geometry, scoring, roster or arbitrary code.
- `CompleteSystemFeedback`: all-member operational preflight, all seals, shared
  reward-source verification, unique official scoring, exact roster and final
  receipts before any update. Model/tool costs come from attributed trace records.
- `SystemSearchArchive`: immutable policies, proposal allocation, exact responses,
  input manifests, import validation, same-cohort frontiers and search-only
  retention. No automatic scientific adoption.

The consumption opportunity has backward-compatible optional Solver text,
bounded value limit and source-pinned knowledge binding. Existing fragments keep
their historical behavior. The disabled compiler returns the original fragment.
The enabled compiler stages content-addressed English role texts and verifies
its result through the existing declared-module checker.

`scripts/prepare_system_text_search.py` performs only metadata preparation. It
writes source pins and the prospective protocol, materializes the seed bundle
outside Git, and creates two own HELD initial cells with the same scientific
request semantics and separate FIT and prepared-supply custody identities.
It does not prepare a serving session, dispatch, clear STOP or read task outcomes.

## Execution boundary and remaining admissions

Complete related tests and repository gates in the isolated worktree. Commit
explicit paths; let the coordinator merge serially and freeze the actual worker.
Prepare each cell's own first-phase supply; bind all source receipts. Real FIT
must include maximum legal lookup material, role handoff, revision context and
the full output reserve on four 24,576-token slots, actor max512. A separately
registered four-row engineering proof covers decline, empty return, actual lookup
and post-revision final delivery. It supplies no quality evidence or learning.

The independent background queue consumes only compiled, registered and admitted
candidates. Wait at a batch boundary for an external proposal if necessary;
existing GPU work remains independent. Keep one generating experiment and one
complete official scorer. Windows free memory must stay at least 10 GiB and above
the serving startup guard; CPU workers stay at most eight while running and twenty
while idle. Retain ten-second resource telemetry and thirty-minute script checks.
Monitoring never dispatches, retries, clears STOP or updates scientific policy.
P-SV-4, Audio2Tool, E21 and per-group held proposals retain their existing boundaries.

Deliver the policy lineage, complete trace index, official score receipts,
quality-cost comparisons, failures and an English handoff. Until actual sealed
search evidence exists, describe engineering readiness only and make no claim
that any of the three updates or the 16,800 trajectories has run.

## Implementation checkpoint: 2026-10-01

The isolated branch is `codex/system-text-policy`, based on `afce16557514f5ab188073745d6bc1baab8c15cc`.
The shared checkout, frozen milestone worker, services, queue and STOP controls
were not modified. The two initial supplies are prepared and warm-verified at
their own version-2 pins. Their selected outputs and scientific baseline fields
are identical; their own FIT identities differ. Generation and FIT plans are
draft registrations, not contact authorization.

The lifecycle CLI exports exact isolated-session input manifests, imports every
response without silently repairing invalid proposals, and compiles provisional
candidates through the existing consumption module. Earlier learning-branch
feedback, unsuccessful proposals and dispositions are indexed without omitting
negative cases. The blind exporter neither reads nor includes these records.
Every indexed source contributes to cumulative exposure even when its candidate
was not selected.

The multi-cell registration gate was also repaired: when members use different
baseline fragments, it now inspects each member's own FIT identity. Previously
such campaigns could omit FIT rows from the gate. The new initial family is
correctly refused while HELD, with draft generation/FIT rows and no coordinator
admission receipts. The remaining historical tuning/read-roster disclosure must
be completed before a launch; do not substitute `none` or call these old rosters
fresh validation.

See [the operator runbook](operator-runbook.md) and
[validation evidence](engineering-validation.json). This is an engineering
delivery awaiting serial integration and runtime admissions. No proposer,
knowledge-construction model, FIT, engineering flight or new search-generation
contact has been made, and no new system-benefit verdict exists.
