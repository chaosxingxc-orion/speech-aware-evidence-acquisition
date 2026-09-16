# Fable5.1: current research handoff

Author: Codex, root research coordinator. Date: 2026-09-16.
Read this file first. It supersedes the operational instructions in HANDOFF.md and the v2
package. Historical reports, source records and manifests are preserved. The owner asked
for a local-file transfer; no email or outgoing message is required.

## Minimal reading order

1. This file: objective, retained conclusions, current state, decisions and first actions.
2. [Full experiment report](EXPERIMENT-REPORT-v3.md): inherited and completed SLURP, E21 and
   Audio2Tool experiments, metrics, uncertainty, attribution and evidence links. It also
   incorporates the latest stopped proof, so no old running-state override is needed.
3. [Next experiments and expectations](NEXT-EXPERIMENTS-v3.md): the selected sequence, controls,
   outcome interpretations and eventual training-free optimization.
4. Read [the latest proof closure and exact repair target](LIVE-PROOF-CLOSURE-v1.md) before coding.
   Consult [the source/operating snapshot](OPERATING-SNAPSHOT-v3.json), [worktree inventory](WORKTREE-INVENTORY-v3.json)
   and [older operational reference](RUNBOOK-SNAPSHOT-v2.md) only as needed.

[HANDOFF-MANIFEST-v3.json](HANDOFF-MANIFEST-v3.json) binds the package and its evidence.
The original [source index](SOURCE-INDEX.json) points to historical detailed reports.
Do not load every status note, repeat completed arithmetic audits, or start from an old
running-flight instruction.

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
| New proof next action | CPU reproduction and repair of the named rendering-contract mismatch in a new worktree. No retry under the closed proof. |
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

The branch is master. The handoff began at 854e3d2b814a700784957104c8901c1cfa8c76de.
Documentation after that commit is an additive handoff, not a runtime fix.

| Source | Identity and treatment |
| --- | --- |
| Candidate-view implementation integrated in canonical | 7ca75217ae52da5bd0b81fc569005d5c5fdcefa1 |
| Candidate proof frozen source | /home/chao/saea-worktrees/candidate-bound-slot-view-v1 at 3c14a0b0780967a5d224c573e8a991c0fd255607 |
| Typed-context failed source | /home/chao/saea-worktrees/slurp-typed-context-full-recovery-v1 at 9bf27b28708bb93607138e7bcd1eacb66eab3f08 |
| Useful base replica source | /home/chao/saea-worktrees/slurp-dual-store-base-replication-v1; verify against its released verdict before reuse |
| Shared execution | TaskAdapter, KnowledgeProvider, EvidenceAgentController, FlightRuntime and OpenJiuwen |
| Candidate-view code | rails/slot_binding_view.py and core/model/native_slot_binding_view.py |
| Supporting request path | core/model/transport.py, rails/phase_tools.py, rails/runner.py, core/flight/runtime.py |

The 248-test acceptance and 83% new-module coverage remain truthful model-free evidence.
They missed a real legacy rendering route; they are not live acceptance. The exact next
regression is described in the closure document. Do not broaden this into general hardening.

Preserve unrelated untracked _tmp_slurp_gap_extract.py, integration_native_finite.py and
wsl$/. Worktree inventory is a map, not an instruction to merge everything; ancestry alone
cannot recognize every cherry-picked equivalent. No remote push is part of this handoff.

## First actions for Fable5.1

1. Read this entry and the closure. Revalidate the current state once, without reading
   held answers/scores or opening model/tokenizer endpoints for a progress check.
2. Write a local takeover acknowledgement using [the reply template](FABLE51-REPLY-TEMPLATE.md).
   Reconcile actual service/lease ownership. The legacy checker pins Codex as execution owner;
   update the takeover contract and checker explicitly, rather than fabricating the old
   unavailable reply or merely changing one owner field.
3. Create an isolated fix worktree. Reproduce the plain-versus-prefixed mismatch through the
   real shared renderer using permitted released knowledge and synthetic runtime states.
   Preserve old behavior when projection is off. Root-review the fix.
4. Prepare a concrete fresh bounded proof proposal if the repair passes. This failed proof
   stops on first failure; do not silently retry it or treat this document as a new admission.
5. After engineering closure, propose one complete matched TRAIN A comparison of the fixed
   useful agent versus candidate-bound views. Keep E21 and Audio2Tool held.
6. Decide and replicate the selected package before expanding its action workspace or
   claiming algorithmic optimization.

## Decisions still genuinely open

No answer from the owner is needed for reading, CPU diagnosis, the narrow repair or preparing
a concrete proposal. SLURP-first, knowledge separation, quality priority and on-demand tools
are settled.

Before any additional live proof/full comparison, show the exact proposed source, mechanism,
control, roster, service identity, generation/FIT/tool budgets and failure rule. Reconcile
new contact admission with the failed proof's no-retry condition. A larger full comparison
is not already authorized by this handoff. If no compatible released direct anchor exists,
explain the need and budget for a fresh one; the held direct score is not a shortcut.

The scientific recommendation is already in [NEXT-EXPERIMENTS-v3.md](NEXT-EXPERIMENTS-v3.md).
Do not ask the owner to choose among a broad menu before the named repair is concrete.
