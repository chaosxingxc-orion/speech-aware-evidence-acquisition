# First system-text update: root diagnosis and repair priorities

Scope: root requested diagnosis of the fully qualified UPDATE1 TRAIN family, all five members and all2000 rows. The exact root READ was already countersigned. This is a post hoc descriptive diagnosis, not a new score, a new hypothesis test or node-level causal attribution. No model, tokenizer or official scorer was contacted. Original traces, outputs, manifests, seals and scores remain unchanged. The combined L/B diagnostic is root-only and must not be copied into either proposer context. Milestone/test feedback was not used.

## What is established

1. The intended Reviewer-to-Planner channel was nonfunctional throughout this family. All3987 completed Reviewer replies normalized to invalid/empty criticism; all3987 were Markdown-fenced JSON. There were3990 raw Reviewer replies including3 length-truncated outputs. Strict parsing and raw model output disagreed. The registered Reviewer phase declared no structured response format. This is a concrete producer/consumer contract defect.
2. B's only valid new Solver-text candidate reduced official pooled SLU-F1 from61.1300% to58.7969%, a difference of-2.3330 percentage points with registered paired CI95[-4.5327,-0.1700]. Against its A/A the difference is-2.5144pp, CI95[-4.6749,-0.3321]. Intent protection is unproven; a negative point estimate alone does not establish an intent loss.
3. The decline has a visible over-extraction component: among171 rows with zero reference entities according to already-scored exact entity counts, false-positive entity rows increased from70(parent) and67(A/A) to83(candidate). These are annotation-defined false entities, not proof that a word was absent from the waveform.
4. The feedback-learning branch had no valid new candidate in round1. Both of its original proposal slots were invalid and remain spent. Consequently this round does not establish that feedback-driven system optimization works or fails.

The original [complete result report](2026-10-02-slurp-system-text-update1-feedback.md) retains the official pooled metrics, intent protection, reliable completion and all18 strata plus the equal-stratum view. The new diagnosis does not replace its numbers or select a favorable slice.

## The common execution defect

| Member | Completed reviews | Invalid handoffs | REVISE | ACCEPT | Rows with two Solver outputs | Rows whose two Solver outputs differ |
|---|---:|---:|---:|---:|---:|---:|
| B-candidate-2 | 796 | 796 | 796 | 0 | 398 | 57 |
| B-parent | 799 | 799 | 798 | 1 | 399 | 39 |
| B-parent-aa | 796 | 796 | 794 | 2 | 397 | 35 |
| L-parent | 797 | 797 | 796 | 1 | 398 | 44 |
| L-parent-aa | 799 | 799 | 798 | 1 | 399 | 31 |

There were3982 REVISE choices and only5 ACCEPT choices. All five members made zero native knowledge lookups. A second Solver output was produced on1991/2000 rows;206 rows changed text between Solver outputs. These are behavioral counts, not node accuracy or evidence that revisions caused the candidate loss. A valid schema is necessary for meaningful criticism transfer but does not prove that a criticism is correct, that a lookup is useful, or that the model should call on every row.

Removing only the outer fence in an offline diagnostic projection makes2628 raw replies pass the existing schema and exposes5072 finding entries. This projection is never substituted for a sealed runtime output. Another1299 replies contain invalid finding fields,28 exceed the checked-list bound,32 violate other types/bounds and3 remain truncated/non-JSON. Thus stripping fences alone would leave substantial schema failure and would silently change the historical parser. The repair constrains new producer requests while keeping the strict consumer unchanged.

Both parent and candidate share this defect. It explains why the intended structured criticism channel failed and why no functioning knowledge-consumption experiment was demonstrated. It does not, by itself, explain the candidate-minus-parent loss. The absence of tool use also does not establish a causal claim that invalid reviews are its sole cause; model willingness and task usefulness remain unmeasured.

## Differential candidate damage

The B candidate changes Solver instructions only. It adds explicit candidate comparison and an internal entity-by-entity evidence/type/boundary/omission check. Knowledge, Reviewer and Planner instructions remain the same as its parent. The measured result is an effect of this complete configuration under the defective common handoff, not proof that a particular sentence is harmful.

| Complete-row diagnostic | Candidate vs parent | Candidate vs parent A/A |
|---|---:|---:|
| Improved frozen utility |26|22|
| Worse frozen utility |46|45|
| Unchanged utility |328|333|
| Previously exact-perfect slot output becomes imperfect |27|25|
| Previously imperfect slot output becomes exact-perfect |9|7|
| Intent correct to wrong |6|7|
| Intent wrong to correct |3|2|
| Extra exact entity false positives (aggregate delta) |+9|+17|
| Word SLU true-positive delta |-7|-4|
| Word SLU false-positive delta |+14.75|+24.5833|

The utility uses the previously frozen F_ref=0.5966805915811396 and saved official terminal counts. It is not a replacement for official pooled SLU-F1. Counts retain all400 paired rows, including failure/abstention. The diagnosis reads no new reference labels and runs no unofficial rescoring of drafts.

Addressable examples in the external paired index include three originally empty-entity rows where the candidate fills `joke_type=best`, `music_descriptor=song identifier`, or `device_type=coffee machine`. Their saved exact counts record false positives; the candidate's first and final Solver outputs already contain the fill. These examples therefore cannot be presented as proved damage introduced by the extra revision step. Other losses include a changed title/intent pairing, a date-to-time type shift, and an altered business-name span. Gains also exist: a birthday-plans span is changed from event_name to list_name, and an ordering expression is moved to order_type. Those gains are retained alongside losses, unchanged rows and damaged correct rows.

The concrete examples are diagnostic, not a rule to suppress a slot type, a runtime answer library or permission to tune on these labels. Knowledge/consumption text should learn general evidence and annotation-boundary distinctions using its own branch's permitted feedback. It must still allow legal entities outside a candidate intent's usual binding.

## Learning-loop and acceptance gaps

Three of four original proposals were invalid. One L slot failed own-app transport, B slot1 hit an overly narrow completion-status importer, and the other L slot exhausted the conservative cumulative input allowance before a third contact. They are not silently repaired or replaced. The one evaluated B candidate made no knowledge-construction change. Round2's two L proposals chose no-change from indexed summary feedback; its two B proposals edit Solver text. This is a substantially shallower search than the planned joint knowledge-construction/supply/consumption space.

The existing four-row proof checked routes, finite completion and tool plumbing but did not require valid Reviewer handoffs. The capacity proof measured request size but could not establish semantic handoff validity. A full row completing is insufficient evidence that all intended intermediate channels function. The revised engineering acceptance must separately assert raw-to-normalized validity, legal routes, explicit empty returns, post-tool final delivery and preserved Solver authority. It must not demand tool calls merely to increase a counter.

For future L updates, expose a compact, source-addressed L-only funnel: raw review, normalization status, decision, actual lookup, returned material, revision and final official counts. Preserve complete indexes and explicit omissions, including successful, failed, unchanged and damaged rows. Do not give B current trajectories, quality, winners or failure history. Root's present combined report is never a proposer file. More iterations alone cannot repair missing feedback or a broken channel.

## Implemented offline correction and authorized next step

The opt-in `saea-slot-review-handoff-v1` response format constrains the existing exact fields, four findings, at most two types/finding and eight checked entries. It keeps empty findings legal, preserves raw output custody and keeps the old strict parser. The shared consumption compiler selects a separately registered13-contact program only for the supported uncited phase shape. Old configurations remain byte-equivalent when the parameter is absent. No new controller, answering model, scoring rule or tool is introduced.

The initial focused tests reproduced the missing contract;231 relevant tests now pass. Coverage is91% for both the changed handoff and consumption modules. The integration test sends the schema through the actual OpenJiuwen runner and shared transport using a synthetic response, then verifies valid criticism in the Planner request and Solver-only final delivery. The pinned local llama.cpp Python grammar converter also compiles the schema without model contact. This is not a real Omni or C++ server-grammar proof.

Owner219 explicitly approved the [prospective correction and execution](../readiness/2026-10-02-slot-review-contract-correction-v1/proposal.json). Register and prove four engineering rows plus maximum legal request FIT, then uniformly rebind all eight existing UPDATE2 members on the same400-row list,3,200 total. Preserve every original candidate and invalid proposal allocation. Rebind full seed/bundle/config/run/attempt identities, keep cumulative ancestry in a cross-protocol transition record, and retain old workers/STOP/evidence. This is a common infrastructure correction, not a learned policy improvement. Do not pool old/new protocol scores as a common frontier.

Owner218's separate memory containment remains required: one member per process,14.5GiB startup and10GiB running floor, no automatic retry. The approved correction is not yet GPU-verified or dispatched at this report's creation.

## Iteration policy

The owner's new instruction makes three rounds the first review checkpoint, not the optimization ceiling. Add rounds one bounded registration at a time when there is a distinct evidence-backed modification and an eligible cohort under cumulative-source isolation. Give L and B the same proposal opportunities and evaluation allocations. Register the extension's total budget, cohort and stop conditions before contacting a proposer or model. The finite original Fold A/B inventories must be audited; more rounds do not create fresh data automatically.

Stop repeated same-mechanism sampling when there is no viable new modification, no eligible cohort, unresolved channel failures or repeated no-change/no-progress. Do not recycle failed slots, enlarge a confidence interval until it passes, or call extra rounds independent replications. After the extension checkpoint, freeze both branches and compare on the common registered selection and DEV lists. The claims remain separate: full-system improvement, incremental value of feedback, and costs/reliability.

## Evidence custody

The [structured diagnostic receipt](../receipts/continuation/2026-10-02-system-text-update1-root-diagnosis.json) pins every external analysis file and the original trace hashes. External root-only files include all400 paired rows for each contrast, all2000 state summaries, every raw Reviewer format record, the successful/failed/unchanged index and the named sample references. Raw data and traces are not committed. New output is descriptive analysis under the already-qualified READ, not a new scientific contact.
