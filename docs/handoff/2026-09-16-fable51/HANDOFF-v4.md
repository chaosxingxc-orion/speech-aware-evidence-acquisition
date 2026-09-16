# Fable5.1: current research handoff v4

Author: Codex, root research coordinator. Date: 2026-09-16.
Read this file first. This v4 package is the consolidated current handoff, superseding
the operational next actions in v3 and the rendering-repair addendum. All historical files,
failed checkouts and original receipts remain intact. The transfer is by local files;
no email, external message or claimed live takeover is involved.

## Minimal reading order

1. This file: settled decisions, current state, remaining approval and immediate actions.
2. [Full experiment report](EXPERIMENT-REPORT-v4.md): designs, results, limitations and
   evidence for SLURP, E21 and Audio2Tool, including the stopped engineering flights.
3. [Next experiments and expectations](NEXT-EXPERIMENTS-v4.md): hypothesis, comparison,
   metrics, interpretation, stop rules and eventual training-free optimization.
4. Only when executing: [fresh proof proposal](../../readiness/2026-09-16-candidate-slot-rendering-fresh-proof-proposal-v1.md),
   [repair validation](../../readiness/2026-09-16-candidate-slot-rendering-repair-validation-v1.json),
   [comparator audit](COMPARATOR-AUDIT-v1.md), and the named source/configuration files.

[HANDOFF-MANIFEST-v4.json](HANDOFF-MANIFEST-v4.json) binds this package.
The historical [source index](SOURCE-INDEX.json), [operating snapshot](OPERATING-SNAPSHOT-v3.json)
and [worktree inventory](WORKTREE-INVENTORY-v3.json) are references, not current liveness
or instructions to merge every worktree. Avoid rereading every status note.

## Research objective and settled owner decisions

Build a useful agentic system around a frozen speech-capable Qwen3-Omni core. Establish
repeatable improvement over direct invocation, then optimize real external decisions through
trajectory sampling and automatic updates without training the core.

Focus development on SLURP first. Work on two connected questions: bring the correct intent
into the candidate set, with 95% as a priority; then choose the correct intent and extract its
entities. Coverage is not the only advancement criterion and 95% is not a prerequisite for
all system work. Expand to Audio2Tool and Earnings only after the base is stable.

Preserve these decisions:

- Separate intent activation/boundary knowledge from slot/parameter explanatory knowledge.
  Knowledge values must resolve distinctions, roles, spans, formats and ambiguity; a larger
  label list or more retrieved text is not an adequate objective.
- Build memory from generalizable correction rules, conditions, exceptions and measured
  outcomes. Do not relabel the training dataset as memory or put evaluation answers into it.
- Normalize and source-bind what each role sees. Speech observations, task knowledge,
  candidate hypotheses, drafts and criticism have different authority.
- Give Reviewer/Planner on-demand investigative tools. The frozen Solver retains answer
  authority; a tool transcript is evidence, not another answering LLM.
- Judge confidence means confidence that a problem or missing evidence exists. It is not a
  calibrated probability merely because the model emits a number.
- Prioritize task quality over online latency. The intended application is post-recording
  meeting work, but evaluate the datasets' native tasks; do not invent a summary benchmark.
- Establish the base before algorithmic RL. Researcher-written prompts, memory rules and
  context edits are engineering, not automatically a training-free RL contribution.
- Run all code, tests, preparation, inference and scoring in WSL Ubuntu-24.04.
  One coordinator owns one resident service and one generation flight. Reuse shared code
  and configuration; avoid private experiment runners and competing editable installs.
- GPU authorization is active at owner level. It does not reopen a failed one-shot attempt
  or waive per-flight preparation, exposure, budget and ownership checks. Do not change
  power settings; the owner already settled them.
- Root owns attribution, design and scientific acceptance. Delegate bounded implementation,
  factual extraction and event-driven observation to smaller ChatGPT models. Frequent
  unchanged progress scans are not useful.

Keep Stage-2, frozen parameters, no second answering model, no paid research API and split
isolation. Official scoring runs once on a complete manifest. NEW500/DEV1000 are exposed
development cohorts. Fold B remains unavailable for tuning or incidental inspection.

## Findings to retain

All results below are released exploratory evidence, not untouched-data confirmation.
The full report links to the complete strata and original verdicts.

| Evidence | Established finding | Research implication |
| --- | --- | --- |
| Older max512 dual-store SLURP, NEW500 | Official pooled SLU 36.1437 -> 50.4479; +14.3042 pp, CI90 [11.2445, 17.5009] | A useful full-system baseline exists. |
| Same-roster matched replica | 35.8906 -> 50.6876; +14.7970 pp, CI90 [11.5245, 18.0112] | Preserve this package as the fallback and control. |
| TRAIN A anchor, 1,080 rows | Gold inclusion 937/1080 (86.76%); 842 correct final intents; SLU 48.5336 | Coverage and downstream resolution both have headroom. |
| Maximum-five / broad-factored K60 | Inclusion 951 / 947; SLU 48.6204 / 47.6347; neither advanced | Do not rediscover a simple N/K sweep as a new proposal. |
| Anchor disjoint errors | 143 uncovered; 95 covered/wrong intent; 525 correct intent/nonexact entities; 317 exact | Missing candidates alone do not explain most complete-task failures. |
| Reviewer attribution | Five executed revisions; zero full-task exact saves; one intent harm | Extra review needs useful evidence and better decisions, not merely valid critique. |
| E21 offline repair | 99 fewer PERSON errors, 165 fewer total word errors, five more insertions | Historical insertion guard failed; future owner preference prioritizes WER/PERSON with insertion analysis. |
| Audio2Tool full4,000 | Primary-call exact +4.050 pp; primary-tool accuracy -3.600 pp | Parameter gains can coexist with tool-selection damage; package not adopted. |

Do not interchange official pooled SLU, mean row F1, entity exactness, intent accuracy or
Audio2Tool primary-call/full-sequence metrics. Conditional cohorts diagnose failure; they
do not isolate a component's causal contribution.

Inherited closures matter: KU-S4N failed noninferiority, so the missing example-encoding
queue and a/b/c are not eligible. The final owner-authorized G6 matched pair failed.
E21 LOOP did not retain its incumbent. Do not rerun these to keep the GPU occupied.

## Current execution status: two distinct stopped experiments

| Item | State at handoff |
| --- | --- |
| Typed-context full-system flight | CLOSED_SECOND_FAILURE_NO_FURTHER_RECOVERY. Original failed at 507 contacts; sole full recovery failed at 6,645. |
| Cause of typed-context recovery stop | Actual Reviewer request 24,878 tokens exceeded a 24,576-token slot. No complete system manifest or score. |
| Its direct comparator | FINALIZED, 1,080 rows and first official score. Quality remains unread under that pair's release contract. |
| Candidate-bound slot-view proof | Independently registered engineering proof; ABORTED after four Perception contacts. No Solver generation or complete task result. |
| Cause of candidate-view proof stop | Exact source-content check rejected the legacy plain slot body because the new projector expected a named-store-prefixed body. See the source-level diagnosis. |
| Candidate proof FIT | Four actual requests passed; 16 endpoint calls; minimum margin 20,417 tokens. These were Perception requests, not evidence that the unexecuted Solver/Reviewer fit. |
| Accepted CPU repair | Integrated at 23b4ec0e; exact plain and named-store-prefixed canonical source forms are recognized and preserved. Root reproduced the failure and verified the fix. |
| Repair verification | Root: 46 unique tests passed; 14 are new rendering regressions. Delegated adjacent suite: 89 passed. Projection-module coverage: 391/449 lines, 87.08%. Test sets overlap; do not add their counts. |
| Fresh four-row proof | Configuration and model-free prepared supply are complete, but HELD pending the already asked owner admission. No new model contact has occurred. |
| Model service | Left resident; no restart/unload for this handoff. Latest snapshot checks process identity, not a new endpoint health check. |
| Fable ownership | Not yet acknowledged. No claim that writing these files has transferred a live lease. |

Do not splice partial output, score partial systems, read the held direct score, reactivate
the held replica, edit a frozen failed checkout or rename a third typed-context recovery.
Static readiness=ready in the used proof configuration is historical registration, not
permission to reuse its exhausted attempt.

The predecessor handoff incorrectly described the candidate proof as still held and gave
a draft analytical-tool cap of 16. The registered program retained three tool-visible
Reviewer iterations and two possible visits, so the cap was corrected to 24 before contact.
The registered generation/FIT caps were 44/176, not actual usage.

## Code and artifacts you will inherit

Canonical checkout:
D:\chao_workspace\exploring-l4-intelligence\studies\speech-aware-evidence-acquisition

WSL checkout:
/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition

The branch is master, not a branch named main. This package was assembled from
9c2cda822a91c5cfcde82a9de2698ad4a4d19e31; the eventual documentation commit is its successor.
Runtime repair 23b4ec0eade972f98d961442dd7856c9fa87ec2c is already integrated.
Held configuration/preparation commit d5723280d8cf5feaf7606d0b072adaf93ffba4fe is also integrated.
Use the actual local HEAD and diff at takeover; this handoff does not claim a remote push.

| Source | Identity and treatment |
| --- | --- |
| Candidate-view initial implementation | 7ca75217ae52da5bd0b81fc569005d5c5fdcefa1 |
| Accepted source-representation repair | 23b4ec0eade972f98d961442dd7856c9fa87ec2c |
| Prepared repair worktree | /home/chao/saea-worktrees/candidate-slot-view-representation-repair-v1 at d5723280d8cf5feaf7606d0b072adaf93ffba4fe |
| Candidate proof frozen source | /home/chao/saea-worktrees/candidate-bound-slot-view-v1 at 3c14a0b0780967a5d224c573e8a991c0fd255607 |
| Typed-context failed source | /home/chao/saea-worktrees/slurp-typed-context-full-recovery-v1 at 9bf27b28708bb93607138e7bcd1eacb66eab3f08 |
| Useful base replica source | /home/chao/saea-worktrees/slurp-dual-store-base-replication-v1; verify against its released verdict before reuse |
| Shared execution | TaskAdapter, KnowledgeProvider, EvidenceAgentController, FlightRuntime and OpenJiuwen |
| Candidate-view code | rails/slot_binding_view.py and core/model/native_slot_binding_view.py |
| Supporting request path | core/model/transport.py, rails/phase_tools.py, rails/runner.py, core/flight/runtime.py |

The initial 248-test acceptance missed a real plain-rendering route. The accepted successor
tests the actual task-contract-only dispatcher, strict source identity, projection/fallback,
and shared raw/feature request construction. It permits exactly two canonical representations;
it does not strip arbitrary prefixes or relax source verification.

The released-source CPU check used 54 cards in both representations, 108 views: 20 projected,
86 fallback and two full/no-exclusion. This used synthetic legal candidates, so it is neither
a campaign distribution nor measured model capacity. No new live or quality result exists.

Preserve unrelated untracked _tmp_slurp_gap_extract.py, integration_native_finite.py and
wsl$/. Worktree inventory is a map, not an instruction to merge everything; ancestry alone
cannot recognize every cherry-picked equivalent. No remote push is part of this handoff.

## First actions for Fable5.1

1. Read the three main files above. Verify their hashes and current Git/state once; do not
   poll endpoints or read held scores simply to check progress.
2. Write an additive acknowledgement using [the current reply template](TAKEOVER-TEMPLATE-v2.md).
   Reconcile service and lease ownership explicitly. The legacy checker still pins Codex;
   do not fabricate an old response or merely rename the owner.
3. The CPU repair and preparation are DONE. Do not redo them or begin another broad
   hardening campaign. Review the exact validation and the pending four-row proposal.
4. Resolve the existing admission question. If it is approved, prospectively bind fresh
   ExecutionPlans, exposure, final readiness and frozen source; then acquire the exclusive
   credential and run the shared proof. If declined or unanswered, keep it held.
5. After a passing proof, propose one complete matched TRAIN A comparison of the retained
   agent versus candidate-bound views. Do not reuse a failed attempt or open held quality.
6. Decide and replicate a qualifying package before one targeted capability extension.
   Keep E21/Audio2Tool optimization held until the SLURP base question closes.

The prepared proof uses baseline/experiment/cell
slurp-candidate-slot-view-rendering-proof4-v1, with run
SAEA-SLURP-CANDIDATE-SLOT-VIEW-RENDERING-PROOF4-V1.
Its prepared source is DATA/prepared/SAEA-SLURP-CANDIDATE-SLOT-VIEW-RENDERING-PROOF4-V1/phase-supply-v1.json,
SHA-256 b3375ff4275bbf5d2fdbb0f9a4f265e72efe83db602c8e73ff7aa00992eefead.
It was revalidated warm with zero contacts. Preparation is not launch authorization.

Use WSL Ubuntu-24.04 and /home/chao/.venvs/speechrl/bin/python. Keep explicit absolute
PYTHONPATH to the selected frozen source; do not reinstall another worktree into the shared
editable environment. Large artifacts remain under
/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data.
Use umbrella docs/datasets.lock.json as the dataset/model identity authority.

## Pending owner decision and later decisions

One concrete question has already been submitted and remains unanswered: admit a fresh
four-row engineering proof after the accepted repair, with caps of 44 generation contacts,
176 FIT endpoints, 24 analytical tool invocations, 117 repeated speech seconds and one shared
FIT-inclusive GPU hour; no official scoring or full experiment. The prior proof's explicit
first-failure/no-retry rule is why this needs separate admission. Do not ask the same question
again, infer consent from time passing, or confuse general GPU authorization with that reply.

A complete scientific comparison is a later proposal. Its exact source, roster, budgets,
service identity, progression/protection criteria and failure rule must be fixed before
outcomes. The current [comparator audit](COMPARATOR-AUDIT-v1.md) found no released matched
TRAIN direct source: DEV1000 has zero row/audio overlap with TRAIN A, the original TRAIN
direct failed before contact, and the completed recovery's quality is held. If making a new
TRAIN system-versus-direct claim, propose a fresh matched direct arm and its budget.
Do not read the held score or reopen its failed pair for convenience.

The recommended scientific sequence is already in [NEXT-EXPERIMENTS-v4.md](NEXT-EXPERIMENTS-v4.md).
SLURP first, knowledge separation, quality priority, local on-demand tools and root-owned
interpretation are settled decisions; no repeated preference questions are needed.
