# Fable5.1 handoff: read this first

Date: 2026-09-16. Author: Codex, root research coordinator.
Owner request: transfer the research through local files, including designs, conclusions,
detailed reports, next experiments and expectations. No email is required.
This is the current consolidated entry. Older START-HERE, TO-FABLE51, operations and design
documents contain historical running-state snapshots; do not execute their obsolete next steps.

## Read only these three files initially

1. This file: objective, settled decisions, established results and immediate work.
2. [EXPERIMENT-REPORT-v2.md](EXPERIMENT-REPORT-v2.md): inherited families, complete SLURP,
   E21 and Audio2Tool results, denominators, uncertainty, negative results and source links.
3. [FUTURE-EXPERIMENT-DESIGNS-v2.md](FUTURE-EXPERIMENT-DESIGNS-v2.md): selected next experiment,
   alternatives, controls, expected signatures, failure interpretations and later RL design.

Then read [IMPLEMENTATION-HANDOVER-v2.md](IMPLEMENTATION-HANDOVER-v2.md) for accepted code and open live validation
and [RUNBOOK-SNAPSHOT-v2.md](RUNBOOK-SNAPSHOT-v2.md) before operating the environment.
[HANDOFF-MANIFEST-v2.json](HANDOFF-MANIFEST-v2.json) binds this package's file hashes.
The source index and original result reports supply full historical evidence on demand.
Do not load every status note or repeat already completed numerical audits.

## What the owner is actually trying to build

Build a useful agentic system around one frozen speech-capable core, then identify and
optimize its external decisions through actual training-free trajectory sampling and updates.
SLURP is the first development carrier. Transfer the qualified framework later; do not
simultaneously optimize SLURP, E21 and Audio2Tool or invent a summary benchmark.

Two connected questions govern SLURP:
- Increase gold-intent inclusion toward 95%; inclusion is the candidate node's criterion.
- Given plausible alternatives, improve final intent choice and slot interpretation/extraction.

95% is a priority, not a prerequisite for all system improvements. The owner explicitly
approved parallel conceptual progress on both lines. Whole-task performance determines
system progression. More knowledge or larger top-N is not automatically better.

Keep intent activation knowledge separate from slot explanatory knowledge. Valuable intent
content distinguishes neighboring activation cases. Slot values explain meaning, semantic
roles, extraction boundaries, representation and ambiguity/omission conventions.
Build generalized corrective memory from permitted errors/rules; do not rename the raw
training set as memory. Never leak evaluation labels or reference text into runtime.

Clean, normalize and bind each role's context. Observations, knowledge, candidate hypotheses,
drafts and criticism have different authority. Reviewer/Planner can investigate on demand;
the frozen Solver answers. Whisper and other local tools should be agent-selected evidence
acquisition, not mandatory preprocessing added to every task.

Researcher-written prompts, context code and rules are engineering. They can establish the
base but are not algorithmic RL. Later optimization needs explicit states/actions,
same-policy sampled trajectories, rewards, automatic updates and frozen evaluation.

## Established results worth retaining

All entries are released exploratory results on exposed cohorts, not new confirmation.

| Evidence | Finding | Consequence |
| --- | --- | --- |
| Older max512 dual-store SLURP, NEW500 | Official pooled SLU 36.1437 to 50.4479; +14.3042 pp, CI90 [11.2445, 17.5009] | A useful system base exists. |
| Same-roster replica | 35.8906 to 50.6876; +14.7970 pp, CI90 [11.5245, 18.0112] | Retain this package rather than assuming every richer system is better. |
| TRAIN A retained anchor, 1,080 rows | Inclusion 937 (86.76%); final intent 842; SLU 48.5336 | Candidate and downstream headroom both remain. |
| Maximum-five / broad-factored | Inclusion 951 / 947; neither established whole-task progression | Do not propose these tested variants as new or simply sweep N/K. |
| Anchor error partition | 143 uncovered; 95 covered/wrong intent; 525 correct intent/nonexact entities; 317 exact | Prioritize actual information consumption and slot interpretation. |
| Reviewer attribution | Five executed revisions; no full-task exact saves; one intent harm | An extra review pass or formatted critique is not evidence of benefit. |
| E21 offline repair | 99 fewer PERSON and 165 fewer total word errors; five more insertions | Keep the failed historical guard; future rules prioritize WER/PERSON with insertions analyzed separately. |
| Audio2Tool 4,000 rows | Primary-call exact +4.050 pp; primary-tool accuracy -3.600 pp | Parameter improvement can coexist with selection damage; system not adopted under its guard. |

The report preserves earlier KC/KV/KU/G6/DR/LOOP outcomes and distinctions between numerical
reproduction, component replay, full live system and independent replica. Official pooled
SLU, mean sample F1, exact entities, intent accuracy and tool-call variants are not interchangeable.

## Current execution state

The typed-context system's sole full recovery failed after 6,645 generation contacts.
An actual Reviewer request required 24,878 tokens in a 24,576-token slot. The capacity guard
refused that request before generation. Its status is:
CLOSED_SECOND_FAILURE_NO_FURTHER_RECOVERY.

There is no complete system manifest or score. The direct arm completed 1,080 rows and its
first official score; its quality remains unread under the paired-release contract.
Do not score/read partial system output, read held direct quality, rescore direct, splice a
prefix, reactivate the replica or rename a third recovery.

The service was rechecked during handoff preparation: the decoder and monitor were alive,
GPU utilization was 0%, and memory use was 22,976 MiB. See the timestamped snapshot.
This is a resident idle service, not a running GPU experiment. No restart, unloading,
generation, tokenizer call, acoustic tool or official scorer was used to prepare this handoff.

## Selected successor and immediate work

Root selected candidate-bound slot views on the older useful dual-store agent.
Keep facts, prompts, candidates, selected card IDs/order, tool permissions and decoding fixed;
project each slot card's applicable semantic-role bindings at the actual consumer request.
Preserve all global rules and source custody. Include the latest legal draft intent even
outside the candidate set. Fall back to full content on missing/malformed scope.

Why this direction: many correct-intent rows still have entity errors; date guidance was
already visible in every audited omission case; shared cards carry unrelated intent bindings.
This suggests a consumption problem, without proving all errors have that cause.

A source-only exhaustive audit measured 42.5421% lower ideal slot-body bytes for ordered
candidate triples. It did not measure actual tokens, capacity or quality.
The separate reference-dedup implementation is already verified; do not bundle it with
the new slot-view experiment or reopen the closed typed-context package.

Immediate ordered work:
1. Review the accepted implementation at 7ca75217 and its exact model-free evidence in the
   implementation handover. Real-source/request tests are complete; proceed to prospective
   proof preparation after review, rather than repeating open-ended engineering checks.
2. Freeze accepted source and fresh preparation. Admit the held four-row engineering proof
   through shared execution, real-request FIT, contact registration and root-owned lease.
3. If that proof passes, present/register one complete same-roster fixed-agent versus
   slot-view comparison, plus a compatible direct anchor or a justified fresh direct arm.
4. Judge the complete result once. Replicate a qualified improvement on the same roster;
   otherwise preserve the useful older base and select one evidence-backed successor.

Expected benefit is plausible but unproven. Lower context volume alone is not progression.
Do not simultaneously add candidate refresh, new slot rules, Whisper or RL.

## Settled operating decisions and ownership

- Run all implementation, tests, preparation, inference and scoring in WSL Ubuntu-24.04.
- One coordinator owns one resident service; one generation flight. Reuse complete serving
  identity and already verified SLURP features, with decoder-only/no GPU mmproj serving.
- Use explicit frozen source paths; never let a new editable install change an active run.
- CPU prep: at most 20 workers while idle and eight total during generation. One complete
  official scoring job at a time; overlap it with qualified next generation where possible.
- Root owns attribution, design, review and acceptance. Small ChatGPT agents may read,
  implement or monitor; use event summaries instead of repeated root progress scans.
- Quality outranks online latency. Current power settings are settled; do not reopen them.
- Preserve Stage-2, frozen core, zero paid research API, gold isolation and untouched Fold B.
- GPU owner authorization is active, but each new contact still needs its qualified plan.
  This handoff grants no launch or extra scientific budget.

No new owner reply blocks reading or model-free acceptance. A new comparison/action/budget
needs a concrete prospective proposal when ready. Detailed decision triggers are in the
future-design document; do not ask the owner to redecide settled principles.

Fable5.1 has not yet acknowledged takeover. On taking coordination, create a local
TAKEOVER-FABLE51-<UTC>.md recording actual source, process, attempt, lease and next action;
then reconcile the legacy coordinator binding before updating shared state (see runbook). Do not assume a handoff document itself transfers
a live credential. Record questions and responses in local files, without sending email.

The file handoff is complete. The overall research objective remains active and incomplete.
