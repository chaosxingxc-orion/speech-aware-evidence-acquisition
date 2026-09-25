# Handoff to Fable 5.1: training-free RL continuation

## Owner steering: optimize complete system trajectories

The owner clarified on 2026-09-25 that Stage-3 must optimize the complete agentic
system and its cross-node decisions. A local component improvement can disappear
after downstream review, revision or delivery. Terminal reward alone does not
make a single Solver supply knob a sufficient system optimization space.

The finite supply bandit is retained as a restricted comparator. The next research
boundary is complete trajectory collection, root-owned cross-node attribution,
then a small coordinated system action space with full terminal evaluation.
Read docs/readiness/2026-09-25-stage3-system-trajectory-optimization.md before
interpreting the older finite-policy sequence below.

Shared full-system trajectory export and sealed official TRAIN feedback join are
implemented. They preserve all roles, tools, state/transition references, fallback
and final delivery; terminal score data is separate from actor context. The
delivery-normalization diagnostic now uses the existing deterministic replay
validator. New engineering evidence is model-free, not an algorithm gain.
Current F10 remains on its frozen checkout and independent background chain.
Whole-system reader validation is now complete on real sealed PLAN and PLANR:
both 625-row trajectories exported and source-bound, followed by offline attribution.
Every delivered exact-entity count and intent indicator matched sealed official rows.
Read docs/results/2026-09-25-slurp-system-trajectory-attribution.md and
docs/receipts/continuation/2026-09-25-system-trajectory-attribution.json.

Root findings: only 32/31 rows reached a subsequent Solver; 29/481 and 26/478
initially wrong strict answers were revised. Reasoning repaired 2/7 fully wrong
answers and harmed 2/4 correct ones. All nine full repairs survived delivery.
The current bottleneck is repair reach/effectiveness and offsetting harms, not
observed erasure of successful full repairs. These are exact-task diagnostics,
not official SLU-F1 or a counterfactual review ablation.

Every first Reviewer received the same speech packet and evidence IDs as Solver.
All 657/656 Reviewer requests retained a mandatory task-contract call instruction
with zero exposed tool schemas. Fixing that interface is engineering; restoring
the old duplicated-contract tool is not automatically useful information.

Prior R-PRIM, B7a, B8b and B9a outcomes constrain the next family. In particular,
B9a acquired zero items in all 18 acquisitions. Require a whole-roster proof that
new evidence exists, survives filtering and reaches the next node before a new
full-system intervention. Do not rename and rerun those old treatments.


The full-context E36b availability replay is now complete on PLAN and PLANR.
New evidence is available on 613/625 and 614/625 rows, but this is not information
gain. Strict tool_call JSON occurs in 319/313 Reviewer states, and protocol text
can become lexical retrieval keys. Do not fly the unchanged held B9a-v2 cell.
Read docs/results/2026-09-25-slurp-system-acquisition-requery.md and the receipt
docs/receipts/continuation/2026-09-25-system-requery-replay.json. No gold, model,
tokenizer, encoder, official scorer or F10 outcomes were read for this diagnostic.

Next design: docs/readiness/2026-09-25-stage3-coordinated-system-family.md.
Optimize the complete supported-issue -> clean acquisition -> bounded repair ->
delivery path. Interface correction is a common engineering control, not an RL
gain. Map onto existing native seams, then register full-system sampling and
evaluation; do not stop at optimizing Solver supply count.

Current execution verified 2026-09-25 at 12:58 UTC (05:58 Seattle).
This is the living record. Superseded snapshots remain in Git history through
fe0d0ee2 and are not live instructions. Preserve immutable records and verdicts.

## Read this first

- F10 is RUNNING: control625 completed, finalized and passed the operational
  inspection at 12:04:44 UTC; treatment625 started automatically at 12:05:11 UTC.
  No task scores were read. Paired analysis waits for both complete arms.
  No owner decision blocks the independent chain.
- VAR-1 and VERIFY-1 are complete, without a stable supply winner or proven
  selector benefit. VAR-2 is CLOSED after its only recovery also failed.
- Finite policy integration passes 118 tests; no formal policy GPU cell has run.
  Shared complete-system export and sealed official TRAIN feedback now exist.
  Root-owned cross-node attribution and acquisition availability are complete.
   Coordinated system action registration comes next.
  Policy-decision credit, including action-not-reached rows, remains unadmitted.
- The stable full-system training-free optimization objective remains open.
- Use scripts for progress, root for interpretation. Keep one continuation
  implementation worktree and merge reviewed chunks promptly into master.

## Objective and boundaries

First demonstrate reproducible SLURP improvement over the locked agentic system
AND best fixed action. Then extend to Audio2Tool and Earnings. Configuration
improvement alone is not adaptive-policy benefit.

Freeze Qwen3-Omni, preserve the local API boundary, final-answer authority and
OBS/ORG/SUPPLY/USE separation. No second answering model or paid research API.
Fresh DEV6570 and test13078 stay closed. Construction and exposed regression
rosters cannot establish fresh-data generalization.

The semantic-delta application line stays closed. CELL-2's approximately +0.64 pp
was inconclusive; CELL-3's approximately -1.44 pp closed that application. Neither
result evaluates every RL method or constitutes a full iterative GEPA comparison.

Run research code, tests, preparation, generation and scoring in Ubuntu-24.04.
Use /home/chao/.venvs/speechrl/bin/python, explicit checkout PYTHONPATH,
PYTHONDONTWRITEBYTECODE=1 and python -B. No shared editable reinstall.
Repository documents and all model-facing material are English.

## Independent F10: current execution

Task SAEA-F10-Continuation-20260925 started at 10:47:15 UTC.
Sequence: treatment smoke4 -> fresh control625 -> empty-contract treatment625.
Each full arm receives one complete official score. Paired analysis waits for
BOTH sealed arms and pinned sources.

- Smoke passed 10:48:43 UTC, 16 generation contacts.
- Control started 10:48:53 UTC and exited successfully at 12:04:40 UTC.
  Operational inspection at 12:04:44 found FINALIZED, COMPLETED, 625 distinct
  outputs and one score job. Generation cost: 2,585 calls. No task metrics read.
  Five finite completions and one revision-limit disposition remain in the roster.
- Treatment started 12:05:11 UTC on the same frozen service after a passing
  prelaunch check. The compact status reports OPENED with no full manifest.
- At 12:58 UTC the service was healthy, 22,988 MiB resident, all four slots busy,
  GPU utilization 64%. This is one sample, not continuous utilization.
  The service-wide request counter is not an arm-completed-row count.
- Frozen flight: /home/chao/saea-worktrees/fable-batch-flight,
  commit 54b6e151481129f4e1915c37f42a88ade687930b through generation AND scoring.
- Launcher 7897d37ffa6a2200717af213cc82f0aed61e307c only adds explicit
  failed-predecessor closure dispatch; it does not change this flight runtime.
- Entry: scripts/flights/batch/batch_chain_f10.sh.
- Log /home/chao/batch-chain-f10.out; status /home/chao/f10-chain-status.jsonl;
  own stop /home/chao/f10-chain-STOP.
- Shared files: /home/chao/batch-queue.json, /home/chao/batch-status.jsonl,
  /home/chao/batch-STOP.
- Serving session serving-slurp-native-candidate-five-train-a-np4-v1:
  decoder-only --no-mmproj, total context 98,304, four 24,576 slots, output512.
  Do not change geometry in flight.
- Data root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data.
- Explicit release: coordination/slurp-stage3-f10-v1/closed-predecessor-v1.json,
  SHA c264123858aad1bc93968c391149ccf967bb216ca47c1c46d42e1d422974e206.
- Launch receipt: docs/receipts/continuation/2026-09-25-f10-launch.json.

F10 changes empty-entity example rendering only. All 8,554 keys remain:
5,813 nonempty values unchanged, 2,741 empty values re-rendered (32.0435%).
All R01 and other required held-out exclusions remain; zero encoding contacts.
Distinguish this from the older 31.5% pool and the 191/625 gold-empty evaluation rows.

Registration: docs/readiness/2026-09-25-slurp-stage3-f10-v1/.
The analysis binding template contains intentional null hashes; create a bound
instance only after both arms seal. Primary construction decision is treatment
minus fresh control pooled SLU-F1 CI95 lower > 0, with intent one-sided CI95
lower > -1.44 pp. Report natural/equal weighting, all strata, empty false
positives, nonempty false negatives/positives and cost. Passing produces a
construction candidate requiring replication, not a stable-gain claim.

## Independent execution and monitor

Automation slurp is ACTIVE every 15 minutes in this thread. The compact script
checks processes, STOP, queue/attempt status and telemetry. No monitoring agent.
Notify only completion, failure, actionable stall or required decision.
Current handoff facts override older automation snapshots.

Local generation, sealing, scoring, queue control and 10-second telemetry do not
depend on heartbeat, network or assistant credits. The Windows task only hosts
WSL. Verified settings: no network requirement, execution time limit, battery
stop or automatic restart. Notifications may wait for connectivity. Machine
shutdown or WSL termination still stops execution; diagnose from receipts,
never automatically replay an attempt or scorer.

Run scripts/flights/batch/continuation_status.py with:

- --queue /home/chao/batch-queue.json
- --status /home/chao/batch-status.jsonl
- --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
- --stop-marker /home/chao/batch-STOP
- --check-processes
- --driver-script /home/chao/saea-worktrees/fable-batch-flight/scripts/flights/batch/batch_driver.sh
- --session-id serving-slurp-native-candidate-five-train-a-np4-v1
- --telemetry /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl

The bounded telemetry reader tolerates an incomplete tail and warns about
stale/unhealthy/unavailable data without altering execution. service_requests_total
is service-wide, never arm-completed rows. Raw logs are for named incidents only,
filtered to operational metadata. Never inspect partial answers/scores.

## Completed evidence and root interpretation

Stage-2 whole-system SLU-F1: Fold A direct 33.89 -> system 63.63;
DEV-added direct 38.09 -> system 65.40. Those are different rosters from R01C below.

VAR-1 completed six 625-row arms and the registered official-feedback-v2 read:

| Arm | SLU-F1 | Intent accuracy | Candidate coverage |
| --- | ---: | ---: | ---: |
| PLAN | 58.5066 | 70.56 | 77.76 |
| PLANR | 60.3755 | 69.28 | 77.28 |
| K10 | 60.4440 | 69.76 | 76.80 |
| K30 | 60.4606 | 70.72 | 77.60 |
| EX-DIV | 58.6794 | 70.88 | 77.28 |
| K16/C5 | 58.6673 | 70.88 | 80.32 |

K10/K30 are about +1.94/+1.95 pp above PLAN, but only +0.0684/+0.0851 pp
above PLANR, with the latter intervals including zero. No stable winner.
PLANR differs from PLAN by +1.8689 pp, CI95 [0.4121, 3.3599].
That repeat shift is neither an algorithm gain nor a universal noise bound.

EX-DIV's mean supply 10.29 versus 20 confounds quantity/diversity; it harmed
performance versus PLANR. K16/C5 changes knowledge count AND candidate width.
Only 5/625 rows gained gold at positions 4/5. The 95% target remains; do not
substitute these R01C results for Fold A.

PLAN emitted entities on 114/191 gold-empty rows; K30 on 108, with 20 repairs and
14 newly harmed rows. Feedback-v2 uses official TP/FP/FN to expose empty-target
false positives hidden by old row-F1 advantage ties. Preserve original analyses.

VERIFY-1's only recovery completed 625/625, no invalid choices.
Selected SLU-F1 58.5816 vs mean-single 57.8807: +0.7009 pp,
CI95 [-0.2551, 1.6507]; medoid 57.9064. Intent +0.544 pp,
CI95 [0.032, 1.088], but the primary benefit did not pass.
Close as benefit not proven: no larger sampling or automatic Reviewer promotion.
420 distinct-answer rows do not establish reliable benefit; a gold-defined
favorable subset cannot become a runtime trigger. The 205 identical-answer rows
cannot establish correction ability.

Full reports:
- docs/results/2026-09-25-slurp-var1-complete-evidence.md
- docs/results/2026-09-25-slurp-var1-feedback-v2.md
- docs/results/2026-09-25-slurp-verify1-complete-evidence.md
- docs/results/2026-09-25-slurp-var2-closed-engineering-failure.md

## VAR-2 closure and custody

Original full attempt stopped after 224 generation contacts. Its only recovery
stopped 10:36:23 UTC after 441: cumulative exk10 supply 40 exceeded registered 38.
Two smokes cost 28 each; total generation721, fit separate. Neither full run
sealed or scored; no partial outcomes were read.

The increment/cumulative fix failed to cover the whole revision horizon.
The guard correctly refused. This is engineering failure, not evidence against
supply actions. No third attempt, renamed rescue or partial score is authorized.

Root checked the owner absent and held the stable guard while archiving STOP/
dead lease at /home/chao/var2-recovery-closed-before-f10-20260925; guard inode
preserved. F10's separate release and approximately 11-minute interruption are
recorded. Do not claim uninterrupted generation.

Historical service receipt custody was restored byte-for-byte from preserved
wrapper/startup bytes; commit 46e03f3d archives replaced receipts by raw hash.
Original manifests/current receipt unchanged. Read
docs/receipts/continuation/2026-09-25-session-receipt-custody-recovery.json.
Raw-file and canonical-JSON hashes differ; that difference alone is not corruption.

## Finite policy engineering checkpoint

Pure numeric policy, pinned artifact loaders, pre-Solver callback and ordinary
OpenJiuwen graph integration are implemented. Source is reviewed in
/home/chao/saea-worktrees/codex-stage3-continuation-20260925 and merged in bounded
chunks to master. Active flight files remain frozen.

Observe first Perception plus fixed default20 local preview; choose one action
and retain it through revisions. Default routing is unchanged. Other actions
reuse the released knowledge router, not a second controller/model. Balanced
assignments follow frozen roster order independent of concurrent arrival.
Receipts separate unexposed preview, decision and actual supply.

118 focused/legacy tests passed, including actual OpenJiuwen graph with fake
transport: one seven-contact revision and two concurrent episodes.
Engineering-base, Stage-3-label and finite-completion checks passed. These are
model-free proofs, not real capacity or quality results. Historical ledger
findings remain; do not claim every check is clean.

Details:
docs/readiness/2026-09-25-finite-policy-runtime-integration.md and
docs/receipts/continuation/2026-09-25-finite-policy-runtime-integration.json.

Existing implementation to reuse next: FlightRuntime._acquisition_requery_binding
already includes E36b. With max_items_per_acquisition declared it searches the
whole released composite snapshot, excludes already-held values and applies the
registered token/IDF policy. Without that declaration it preserves the empty
legacy B9a-rec path. Inspect and test the existing E36b seam on the prepared
roster before proposing any new acquisition implementation; code availability
does not establish useful evidence or a quality result.

## Next execution and algorithm plan

The complete-system design above supersedes the older supply-only progression.

1. Seal both F10 arms, bind sources, read the registered comparison. Retain the
   old representation if unqualified; replicate a positive result before stable
   adoption. Do not change this running experiment.
2. The PLAN/PLANR complete trajectory read is done. Use the linked full-system
   attribution to prepare the next evidence acquisition/repair policy. Preserve
   terminal failures and unknown instrumentation. Do not infer causality from the
   descriptive wrong-row classes or copy them into runtime state.
3. Admit a small set of coherent system policies from named evidence deficits.
   Use matched combinations to measure interactions, rather than a large Cartesian
   product of independent component knobs. Compare every policy's full terminal
   outcome with the locked system and strongest fixed system policy.
4. Register full-horizon real request capacity, four-row engineering proof,
   configuration, complete trajectory schedules, plans and budgets. Reuse the
   independent queue and freeze runtime at the next execution boundary.
5. Complete full-system sampling -> terminal feedback -> external memory/policy
   update -> re-execution. Freeze policies within each construction round; log
   pre-action states and true selection propensities. Multi-step credit requires
   an explicit estimator, not the same terminal scalar blindly copied to all nodes.
6. Run same-space scholarly baselines: MemRL-style external utility updates and
   full Training-Free GRPO grouped trajectories, feedback, experience update and
   re-execution. Keep the finite supply contextual bandit as a restricted comparator.
   Its existing two-round balanced then 80/20 schedule is an engineering proposal,
   not the entire Stage-3 optimization space.
7. Freeze learning for authorized exposed regression, compare complete policies,
   and replicate before stable-gain claims. Other datasets follow a stable SLURP
   system; fresh DEV/test stay closed.

The existing finite-policy implementation still needs decision/terminal-source
credit and explicit action-not-reached handling before a formal admission. Do not
drop terminal rows, fabricate actions, or repurpose closed VAR-2 as a new run.

The first baseline is MemRL-inspired contextual bandit, not faithful MemRL or
multi-step RL. Read docs/readiness/2026-09-25-training-free-rl-baseline-fidelity.md.
Never pass arbitrary signed utility to MemRL's boolean success API.

Frozen F0=0.5850661976193667; feedback u=2TP-F0*(2TP+FP+FN), combining official
word/character counts. Keep intent, format and fallback separately.
Feedback has count units; official pooled F1 remains the primary metric.

Pre-action state uses fixed agreement bins. Old analysis unions evidence across
waves and is not a valid pre-action feature. With 625 rows / four actions, sparse
bins are expected; report support/fallback and exact propensities. Adaptive global
means may reflect state occupancy. Preserve the declared baseline and report the
limitation; importance weighting requires a separate registered comparator.

Aligned null CI90 half-widths: pooled SLU-F1 1.2413258895 pp, intent 1.44 pp.
Do not divide by row-mean ROLL-AA intervals to claim threefold power, or promise
625 rows can detect 0.4 pp. Stable significance remains an objective, not a result.

## Owner decisions

None blocks current authorized work. Root owns F10 interpretation and bounded
action admission under the approved plan. A new decision is needed before fresh
DEV/test access, reopening a closed family, changing data isolation/claim scope,
or materially expanding experimental scope. Ordinary implementation or an
inconclusive result does not require repetitive permission requests.
