# Handoff to Fable 5.1: training-free RL continuation

## Monitor and policy implementation checkpoint, 2026-09-25 11:05 UTC

The15-minute heartbeat remains ACTIVE. The shared continuation_status.py now
accepts an explicit --telemetry path and emits a bounded, allowlisted serving
snapshot alongside queue/process status. It reads the last complete telemetry
row, tolerates an in-progress tail, and warns on stale/unhealthy/unavailable
telemetry without replaying or altering the job.21 synthetic status tests pass.
A service request counter is service-wide, never a current-flight completion count.

At11:04:40UTC the fresh-control625 process was RUNNING, with no STOP or completed
full manifest. The service was healthy, all4 slots busy and GPU utilization97%.
The first input-assembly interval was followed by active generation; do not
infer completed rows from an OPENED attempt or announce partial task outcomes.
No new owner decision is blocking the independent F10 chain.

The finite-policy pure numeric component is in implementation/review, not yet
connected to runtime and not authorized as a GPU cell. Root confirmed the
ordinary pre-Solver supply callback can carry one episode-held action without
reopening VAR-2. Required next integration is pinned snapshots, default20
pre-action preview, a source-bound decision receipt, ordinary graph validation,
real capacity registration and a complete terminal-feedback join. The design
now explicitly records balanced allocation probabilities and adaptive global
mean confounding. No training-free RL gain has been measured.

## Live execution: independent F10, 2026-09-25 10:47 UTC

F10 is now RUNNING as independent task SAEA-F10-Continuation-20260925.
This supersedes the launch-pending paragraph below. Root explicitly closed
VAR-2 after its second failure and released this independently registered
family; no third VAR-2 attempt is authorized.

- Launch10:47:15UTC; shared driver10:47:18; prelaunch passed10:47:25.
- Sequence: empty-contract smoke4, fresh default control625, empty-contract625.
  Each full arm has one complete official job. No partial outcomes are read.
- Flight commit54b6e151481129f4e1915c37f42a88ade687930b stays frozen through
  generation/scoring. Launcher commit7897d37ffa6a2200717af213cc82f0aed61e307c
  adds only explicit failed-predecessor closure dispatch; runtime is unchanged.
- Log /home/chao/batch-chain-f10.out; chain status /home/chao/f10-chain-status.jsonl;
  own stop /home/chao/f10-chain-STOP; ordinary queue/status paths are reused.
- Protocol docs/readiness/2026-09-25-slurp-stage3-f10-v1/protocol-registered-v1.json.
  Prospective analysis-specification-v1.json binds the decision rules.
  Fill analysis-binding-template-v1.json only after both full arms seal, hash
  all sources before the read, and use the shared official-feedback reader.
- Exact launch/preflight/closure hashes are in
  docs/receipts/continuation/2026-09-25-f10-launch.json.
- The approximately11-minute interruption was failure closure and independent
  handoff work, not data wait. Record it; do not claim continuous GPU utilization.
- Model servicePID714 remains resident, same no-mmproj four-slot geometry.
-15-minute heartbeat slurp is ACTIVE; scripts inspect progress, root interprets.
  Local telemetry, generation, scoring and queue control do not need network,
  Codex credits or the heartbeat. Notifications may wait for app connectivity.
- Shared analysis61 tests, launcher13 synthetic boundary tests and six relevant
  engineering gates pass. Root confirmed three clean prepared preflights.
- No new owner decision is blocking F10. Stage-3 stable optimization and the
  finite-policy learning cycle remain unproven/unexecuted; do not mark goal done.

## Current state: VAR-2 closed; independent F10 admission ready

This section supersedes every earlier execution snapshot.
The sole VAR-2 recovery ABORTED at2026-09-25 10:36:23 UTC after441 model
contacts. The cumulative exk10 supply reached40 items against declared bound38.
The original full attempt cost224 contacts and each smoke28: total721
generation contacts. Neither full attempt produced a complete manifest or
official score; no partial answers or scores were read. VAR-2 is CLOSED and
must never receive a third attempt. Preserve both failed runs and all costs.

Root diagnosis: the earlier increment/cumulative repair did not validate the
whole allowed revision horizon against the registered item bound. The guard
correctly refused the request. This is engineering failure, not evidence
against the supply actions. Read
docs/results/2026-09-25-slurp-var2-closed-engineering-failure.md and
docs/receipts/continuation/2026-09-25-var2-final-closure.json.

F10 is independently registered and prepared: smoke4, fresh control625, then
empty-contract625. All three offline preflights passed at54b6e151 with exact
prepared artifacts and root admission. F10 has no supply_variants and uses
the ordinary four-node path; it does not enter the failing bound check.
The official comparison is empty minus fresh control, pooled SLU-F1 CI95
lower>0 and intent one-sided95 lower>-1.44pp. This is construction screening,
not stable-gain or learned-policy evidence. All strata, empty FP and nonempty
FN/FP must be reported. The knowledge store has8,554 keys, with2,741 empty
values changed and5,813 nonempty values preserved exactly.

Root has archived the original STOP and dead owner's lease metadata at
/home/chao/var2-recovery-closed-before-f10-20260925. It checked PID27810 absent,
no flight/scorer process, four idle server slots, and held the stable kernel
guard while removing only stale metadata. ServerPID714 remains resident.
Independent continuation receipt:
$SPEECHRL_DATA_DIR/coordination/slurp-stage3-f10-v1/closed-predecessor-v1.json
SHA256 c264123858aad1bc93968c391149ccf967bb216ca47c1c46d42e1d422974e206.
This explicit root decision permits F10 after the failed predecessor; the
default unattended path still refuses a failure. F10 launch is pending the
reviewed closed-predecessor launcher profile; do not claim GPU has restarted.

VAR-1 and VERIFY-1 conclusions are unchanged: no stable supply winner above
the PLANR replicate; VERIFY benefit not proven, so no enlarged sampling.
The finite policy remains designed, not executed. Its state must be recorded
before the first Solver action, using a fixed default20 preview. The old
analysis aggregates supply across all waves, so its agreement state cannot
be assumed pre-action. Read
docs/readiness/2026-09-25-slurp-stage3-finite-policy-design-v1.md.

The generic official-count comparison reader now supports two registered
arms, preflights BOTH seals and hashes before outcomes, and distinguishes
exact-entity counts from pooled word/character counts.61 analysis tests and
six launcher boundary tests pass. No new answering LLM or scorer replay.
Use scripts for progress. Automation slurp remains ACTIVE every15minutes;
host telemetry remains every10seconds. GPU processes never depend on either
Codex heartbeat availability or local credits.

## Current execution: VAR-2 single recovery, 2026-09-25 10:12 UTC

This section supersedes earlier execution snapshots. The sole registered
recovery is RUNNING under independent task SAEA-VAR2-Recovery-20260925.
Flight checkout is pinned at 960d793880b0782acf92dfc96f7ad9608364c954.
The driver started at 10:11:07 UTC; service prelaunch passed at 10:11:15.
Smoke4 is followed by the full625 arm and then four serial derived scores.
This snapshot does not claim smoke/full completion.

- Entry: scripts/flights/batch/batch_chain_var2_recovery.sh, a thin profile of
  the existing batch_chain_var2.sh and shared batch driver.
- Log: /home/chao/batch-chain-var2-recovery.out.
- Pin: /home/chao/var2-recovery-flight-commit.txt.
- Full run: SAEA-SLURP-STAGE3-VAR2-SUPPLY-VARIANTS-R01C-RECOVERY-V1.
- Analysis: $SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-VAR2-RECOVERY-SUPPLY-READ-V1.
  Driver completion is not full chain completion; require score-summary.json.
- Original failure remains archived at
  /home/chao/var2-failed-before-recovery-20260925 and in original data-root paths.
  Owner PID22771 is absent, all4 server slots were idle, and root held the
  stable kernel guard exclusively before archiving/removing stale metadata.
  The guard inode was preserved. No server restart or failed result read.
- Clean smoke/full preflights pass. The first offline check refused incidental
  scoring bytecode; it was quarantined outside the source tree before the clean
  checks. No frozen scoring source changed and no model contact occurred.
- Revision fix: two incremental graph tests failed before the correction,
  repeated-selection controls passed; 89 variant-related and35 ordinary-native/
  status/log tests pass afterward. A separate read-only code review found no
  concrete defect. Source first-visit semantics and actual PLAN request remain.
- The combined original-plus-recovery generation cap, INCLUDING both smoke
  proofs, is 10,945; actual original costs are224 full+28 smoke. A second
  failure closes VAR-2. No automatic recovery or changed readout threshold.
- F10's three HELD runtime packages are committed: fresh full625 control,
  empty-contract full625 and treatment smoke4. The8,554-example minus-R01
  store is built and verified. Next: register matched analysis, prepare supply,
  admit and launch after the current chain closes; do not change active files.
- Exact recovery launch and preflight pins:
  docs/receipts/continuation/2026-09-25-var2-recovery-launch.json.

## Active incident: 2026-09-25 10:02 UTC, root Codex

This incident supersedes the running status in the prior snapshot.
VAR-2 full generation ABORTED at 09:49:19 UTC, after 224 model contacts.
The service remains alive; the experiment driver has stopped. No sealed
manifest or scientific result exists. No partial answers or scores were read.
Root reproduced and fixed an increment-versus-cumulative supply check on the
Solver revision path. One registered recovery is being prepared; it has not
started. F10 HELD configurations are ready but not dispatched.
Read docs/readiness/2026-09-25-var2-revision-recovery-diagnosis.md and the incident
receipt. Preserve the original failed artifacts. Do not clear STOP or restart
on a timer; the root recovery launch must bind the new identities and fix.

## Live continuation update: 2026-09-25 09:46 UTC, root Codex

This section supersedes older live-status paragraphs below. Main is master.
Keep one implementation worktree plus one frozen flight checkout; merge reviewed
chunks promptly.

- VAR-1: all six arms complete; official-count feedback v2 now complete.
  See docs/results/2026-09-25-slurp-var1-complete-evidence.md and
  docs/results/2026-09-25-slurp-var1-feedback-v2.md. K10/K30 improve versus PLAN
  but not reliably versus unchanged PLANR. Coverage for K16/C5 is 80.32%;
  this is R01C, not the earlier Fold A roster. Empty-gold rows: 191/625;
  PLAN falsely emits entities on 114. No stable optimization winner.
- VERIFY-1: the only registered recovery completed 625/625 at 09:04 UTC,
  using 625 model contacts with no invalid choices or selected malformed sources.
  Chosen SLU-F1 58.5816 versus mean-single 57.8807; delta +0.7009 pp,
  CI95 [-0.2551, 1.6507]. Intent guard passes, primary benefit does not.
  See docs/results/2026-09-25-slurp-verify1-complete-evidence.md.
  Close as benefit not proven: no promotion, larger sampling, automatic rerun,
  or automatic evidence-driven Reviewer successor. Do not claim all reviewers fail.
- Preserve the original zero-contact fit refusal and both post-generation reader
  refusal logs. Identity and contact-count metadata fixes enabled analysis only;
  they changed no sealed predictions and added no model or scorer contacts.
- VAR-2: configuration, root decision, four-row/full625 prepared supply, shared
  first-visit custody/scoring and clean preflights are ready. Independent task
  SAEA-VAR2-Continuation-20260925 started at 09:33 UTC, flight commit
  80299fe72458bcb3c280eef5725d2587a037d964; the driver is RUNNING.
  Smoke4 passed at 09:36:25 UTC (4 rows, 28 contacts, zero tools); full625
  started at 09:36:35 UTC. At 09:46 UTC, the service monitor reports 4/4 slots
  busy and GPU 98%; the full attempt is OPENED. Per-contact real fit remains
  mandatory. This is not a full-arm completion claim.
  See docs/receipts/continuation/2026-09-25-var2-preflight.json.
  Only the last plan arm has downstream Reviewer/Planner behavior; local side
  branches never count as system RL returns. Fixed arm order stays a limitation.
- New derived scoring records a durable start marker before the official scorer.
  A failed/interrupted invocation cannot be automatically repeated; completed
  cached scores remain readable. Focused scoring/supply tests: 36 passed.
- Execution entry: scripts/flights/batch/batch_chain_var2.sh through saea_task.ps1.
  It uses the existing WSL shared driver and resident no-mmproj four-slot service,
  then scores four complete first-visit columns serially. Never run generation
  from an assistant PTY. /home/chao/var2-flight-commit.txt binds this launch.
  The actual driver runs from the frozen flight checkout; pass
  --driver-script /home/chao/saea-worktrees/fable-batch-flight/scripts/flights/batch/batch_driver.sh
  to continuation_status.py. Checking the old main-path driver falsely reports
  an absent process. The heartbeat argument has been corrected.
  The driver completing is not the derived scoring completing: inspect the
  independent task/log and analysis score-summary.json before reporting closure.
- The 15-minute current-thread heartbeat slurp is ACTIVE. Script-only status
  checks, no monitoring agents; notify meaningful changes only. Its availability
  is separate from the local GPU driver and 10-second telemetry. Generation
  and scoring do not depend on network, assistant credits or this heartbeat.
- MemRL and TF-GRPO upstream implementation pins were audited. Read
  docs/readiness/2026-09-25-training-free-rl-baseline-fidelity.md.
  The first cumulative-mean finite policy is MemRL-inspired contextual bandit,
  not full MemRL reproduction. Do not feed signed/continuous reward to a
  truthiness-based success update. Same-space scholarly algorithm loops remain
  unexecuted and required by the persistent Stage-3 objective.
- F10: the existing empty-contract builder now accepts a source-bound sibling
  configuration; 26 focused/legacy tests and the engineering gate passed.
  The registered CPU build is COMPLETE: 8,554 identical retrieval facets,
  5,813 unchanged nonempty values and 2,741 re-rendered empty values.
  All required vectors are present; zero model/tool/encoder/scorer/GPU contacts.
  Receipt: docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars-empty-contract-minus-r01-v1.json.
  Snapshot content SHA-256: 2c4d44626e269df2b9cc1371623c08a317de03dd0f1183e3a0bc3b8ed1477e18. The historical 9,354 store is not eligible for R01C. See
  docs/readiness/2026-09-25-slurp-stage3-f10-knowledge-build-v1.md.
  Proposed matched control/treatment runtime remains undispatched.
- No current owner decision is required. Continue VAR-2/F10 -> qualify useful
  full-system actions -> frozen-round exploration/update -> evaluate against
  both the locked system and the strongest fixed action. Only revisit Reviewer
  or coverage with a named information deficit. Fresh DEV6570 and test13078
  remain closed. Semantic-delta application stays closed.

Owner-approved implementation of the ChatGPT continuation plan, 2026-09-25 UTC.
This is the single living handoff back to Fable. Update the current facts in place;
preserve immutable flight artifacts and historical verdicts.

## Objective and operating decisions

Seek a statistically supported, reproducible full-system gain over the locked SLURP
agent and the best fixed construction. A configuration gain is not evidence of policy
learning. Core weights remain frozen; no second answering model, paid research API,
transcript input, new DEV-remainder use, or test-split read is authorised by this phase.
Do not promise a significant result before measurement.

Continue VAR-1 -> VERIFY-1 -> VAR-2 / F10 -> evidence-qualified coverage or Reviewer
work -> complete-system validation -> bounded external action-value optimisation.
Keep the semantic-delta application line closed.

Use scripts for routine progress inspection, compact status summaries, and execution.
GPU generation, sealing, and queued scoring must run under the independent WSL background
batch driver, with no dependency on Codex availability, network, or assistant credits.
The resident local model is the only inference endpoint. Preserve failures; do not auto-replay.
Use subagents for bounded code changes or named error analysis, not recurring scans.
The root owns scientific attribution, decisions, and experimental interpretation.
Merge reviewed, completed tasks into master promptly. Use one shared continuation
worktree rather than accumulating independent branches.

## Current execution and isolation

- Frozen VAR-1 chain uses study commit 3ade29ff and the existing resident decoder-only
  service, np4 x 24576, no mmproj. Do not change its checkout, queue, or service.
- Steps PLAN, PLANR, EX-K10, EX-K30, EX-DIV completed. PER-K16C5 smoke sealed
  at 05:43:43 UTC. At 06:00 UTC the root found the driver and server absent,
  despite an unfinished arm-start log. No final-arm attempt, fit attempt, output
  directory or flight lock exists. The campaign log is empty. Windows tasks report
  0xC000013A (control-event termination); its initiating cause is unknown.
- The local server was restarted through SAEA-Serving at 06:03:30 UTC with the
  same model and geometry. A separate one-shot continuation reuses the sealed
  smoke and starts only the unopened arm; it refuses any already opened attempt.
  Record this service-process boundary in VAR-1 interpretation. Do not claim that
  the entire family ran in one server process.
- No VAR-1 variant outcomes have been read by this continuation.
- At 06:08 UTC the resumed final arm is OPENED, driver and service processes match,
  and GPU utilization is 97%. SAEA-VAR1-Unopened-20260925 owns the WSL chain.
- The inherited own-null read failed before any number: the supposedly reusable
  paired-roster reader hardcodes split role dev and rejects TRAIN construction.
  Fixed in 254a80a3 with explicitly guarded discovery/TRAIN support and 22 passing
  tests. Preserve the old refusal log; do not alter the experiment roster.
- Implementation worktree: /home/chao/saea-worktrees/codex-stage3-continuation-20260925.
  Source fable-verify1b is preserved. Its 24 unfinished VERIFY-1 files were copied
  with source hashes in docs/receipts/continuation/2026-09-25-verify1-source-snapshot.json.

## Implemented and pending engineering

1. Completed in 04b72a71: shared official_metric_feedback helpers and tests. The
   frozen-baseline utility is u = 2TP - F0*(2TP+FP+FN), combining the official word
   and character counts. Keep intent correctness and parse status separately.
   Candidate disagreement uses structured outputs, not only row-F1. Tests cover
   empty-gold false positives, aligned complete groups, and invalid numeric inputs.
2. VERIFY-1: inherited sealed-samples binding passes 55 tests. A versioned
   balanced-block presentation rule and strict reason-length parsing have been
   implemented locally; source positions balance exactly on the full 625 roster.
   Complete config/material binding, registration, fit, and smoke before flight.
3. VAR-2: post-seal bundle validation completed in 8b6c0f03 with 138 passing tests. Only the delivering
   Solver arm has downstream Reviewer/Planner continuation; alternative scores
   are component probes, not complete-system returns.
4. Feedback-v2 analysis, aligned ROLL-AA statistics, selector read, and bounded
   value-policy implementation remain to be integrated.

## Scientific interpretation to preserve

- Locked system: Fold A SLU-F1 63.63 vs direct 33.89; DEV-added 65.40 vs direct
  38.09. These are whole-system development results, not single-component claims.
- CELL-2 gain +0.64 pp was inconclusive; CELL-3 loss -1.44 pp closed the existing
  semantic-delta application line. Do not reinterpret that as failure of every RL
  algorithm or a full reproduction of iterative GEPA.
- 191/625 construction rows have no gold entities and row-F1 cannot distinguish
  correct emptiness from false positives. Historical advantage selection excludes
  these ties. Feedback-v2 is a new derived version; old artifacts remain intact.
- ROLL-AA half-width 0.735 uses mean row-F1, whereas ~1.25 cross-flight uses pooled
  micro-F1. Do not claim 3x statistical power or a certified 0.4 pp detection limit.
- VERIFY-1: report all 625 plus 420 content-distinct and 205 identical-answer
  populations; separately flag the six rows containing malformed source samples.
  No favourable-subset-only reporting. Balanced presentation changes are frozen
  before first contact.
- F10 tests rendering, not missing examples: the pool already has 31.5% empty-entity
  values. Keep example identities and selection fixed.
- Policy features must exist before their action. Initial routing uses the existing
  exemplar/candidate agreement buckets. First study the four known supply actions.
  Search remains TRAIN construction; exposed Fold A / DEV are regression checks.

## Next execution boundary

Finish the active VAR-1 chain, seal its own null first, then its registered variant
analysis. Preserve failed read logs and write corrected analyses to a new location.
Complete VERIFY-1 code/config tests, register all contacts, mint the root receipt
under the owner's implementation approval, and use the existing scheduled batch
driver in attach-only mode. Never bypass a fit, manifest, lease, or clean-tree refusal.

## Results and conclusions

No new model-effectiveness conclusion has yet been produced by this continuation.
Record run ids, manifest and analysis hashes, complete official scores, paired
intervals, per-stratum results, failure/fallback counts, and costs here as each
experiment closes. Distinguish code completion, generation completion, and scientific
decision; none implies the others.

## Independent WSL execution contract

The host Scheduled Task owns the WSL process, independent of the interactive
assistant connection. SAEA-Serving owns llama-server; SAEA-Monitor samples locally;
a uniquely named campaign task owns the batch driver. Settings checked on
2026-09-25: RunOnlyIfNetworkAvailable=false, ExecutionTimeLimit=PT0S,
RestartCount=0. Model calls use localhost and local assets; no assistant credit,
remote API token, or online scheduler appears in the research execution path.

Run only already registered, admitted tasks. Queue transitions and sealing are
scripted; an undecided scientific branch stops at a local handoff record.
Network loss or exhausted assistant credits needs no intervention. Machine shutdown,
WSL termination, a killed task or hardware failure still stops execution; recover
from receipts after diagnosis, never automatically replay a model contact.

The one-shot script scripts/flights/batch/batch_continue_var1_unopened.sh preserves
the original queue and records its replacement hash. It does not reopen five
completed arms or repeat the completed smoke. The active frozen experiment checkout
remains at 3ade29ff. Later VERIFY-1 code is integrated only at a run boundary.

## Remaining experiments and expected decisions

1. Close VAR-1 in registered order: PLAN/PLANR own-null, then four variants.
   Preserve the failed original TRAIN-reader log and use a fresh corrected output.
   Compare complete task quality, candidate coverage, entity FP/FN, empty-entity
   mistakes, actual supply size and cost. K16/C5 is a combined action; diversity
   may also change example count. Neither supports a single-factor claim yet.
2. VERIFY-1: speech plus five sealed Solver candidates, balanced positions, all
   625 rows primary; source-index-0 fallback for malformed selector output.
   Selection benefit opens evidence-rich Reviewer work. Lack of benefit stops
   expansion of this bounded sampling route. Report metric-limited oracle
   references and operational intent guard separately.
3. VAR-2: default 20, 10, 30 and diversity supply branches share their prefix.
   Only the baseline branch continues downstream. Validate branch custody and
   full-roster real requests; a component winner still needs a full-system run.
4. F10: change empty-entity rendering only, preserving identities and count.
   Evaluate false-positive reduction beside missed entities. Keep the R01C
   exclusion in the knowledge version.
5. F4 is conditional: if wider candidates improve coverage without improving
   final answers, prioritize discriminative evidence and Reviewer selection;
   otherwise measure marginal coverage from additional neighbor intents.
6. First policy baseline: finite contextual bandit, frozen model, existing
   pre-Solver agreement bins, eligible supply actions including default. Two
   R01C full-system construction rounds: balanced exploration, then 80% current
   best / 20% uniform. Record action probabilities and terminal trajectories.
   Update cumulative external values only between rounds; state-action counts
   below 20 fall back to global action estimates. Freeze policy for evaluation.
   Use official-count utility plus a separate intent guard. Compare the locked
   system, best fixed action and learned policy; configuration search alone is
   not an RL improvement. Multistep optimization waits for useful downstream
   evidence-acquisition and revision actions.

## Resolved receipt custody issue

Service restart replaced the old resident session receipt. The root recovered its
exact bytes from the preserved wrapper identity and the append-only startup log.
The reconstructed raw SHA-256 equals the original manifest's required
8dc2bbda40f74824946701ad6b3a660bd220b7bc396e184f9f99cd0b0e812d52.
The missing startup hash came from observed log bytes at offset 135805607, length
2921; no event value was invented. Original manifest and current receipt are
unchanged. See docs/receipts/continuation/2026-09-25-session-receipt-custody-recovery.json.

Commit 46e03f3d preserves replaced session receipts by content hash and permits
only exact-hash session-receipt archive resolution. Other artifact checks are
unchanged. Session/bundle tests: 210 passed, 6 skipped. The earlier claim that a
different canonical stop hash established preexisting corruption was rejected:
canonical JSON hashes differ from raw-file hashes. The full VERIFY-1 material
build and offline dry run now pass again, with zero model contacts.

## Current implementation evidence

VERIFY-1 sealed source binding, balanced presentation, shared actual-request fit
path, parser and analysis reader have landed on master. 206 relevant phase,
selector and status tests pass. Shared OpenJiuwen proof covers role visibility,
rail rejection, iteration bounds and tool round trips. Smoke and full-roster readiness are now ready after root admission and clean-tree
checks. Actual-request fit remains mandatory inside the scheduled worker/campaign.

## Independent successor prepared

scripts/flights/batch/batch_chain_verify1.sh waits for all six VAR-1 steps and
FINALIZED attempts, preserves its queue/status, switches the frozen flight checkout
at the boundary, then uses the existing batch driver for VERIFY-1 smoke and full
625. The explicit flight commit is /home/chao/verify1-flight-commit.txt. The running Scheduled Task
SAEA-VERIFY1-Continuation-20260925 owns this chain; no Codex heartbeat or live assistant is
in the execution path. VAR-1's registered analysis runs concurrently on CPU and
VERIFY-1's sealed-count reader runs after its completed manifest. Any driver
failure stops the chain. VAR-2/F10 and adaptive policy experiments are not queued
without their own completed scientific and engineering prerequisites.

## R01C repeat calibration read

The corrected own-null read completed under
analysis/SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1-CORRECTED-V2. PLAN SLU-F1 is
58.5066 and PLANR is 60.3755: +1.8689 pp, paired CI95 [0.4121, 3.3599].
Intent (scenario/action exact) is 70.56 vs 69.28: -1.28 pp, CI95 [-3.04, 0.48].
Frozen CI90 half-widths are 1.2413258895 pp for pooled SLU-F1 and 1.44 pp for
intent. These are operational calibration values, not practically meaningful
effect thresholds or universal sampling-noise bounds.

The nonzero repeat shift is a caution for cross-run attribution, not an algorithm
gain. Preserve original planned contrasts and add interpretation against the
replicate in the complete family read. Scenario/equal-weight tables remain pending
that read; no final family verdict has been issued. Do not transfer the pooled
half-width to mean row-F1, ROLL-AA, or the selector's own contrast variance.

## Last verified execution snapshot: 2026-09-25 06:38 UTC

- SAEA-Serving and SAEA-Monitor are running as independent host tasks.
- SAEA-VAR1-Unopened-20260925 is running the final arm; its attempt is OPENED.
  The five completed arms remain skipped. Latest observed GPU utilization: 93%.
- SAEA-VERIFY1-Continuation-20260925 is running and waiting locally for VAR-1.
  Its frozen successor commit is 14ee125cc81dfa50bd15414a097c96209fbb0d90.
- All four host tasks have RunOnlyIfNetworkAvailable=false and no execution
  time limit. The GPU path calls the local service, not a ChatGPT/OpenAI API.
- Two orchestration-only prelaunch refusals are preserved: an embedded queue
  newline syntax error, corrected before any queue mutation, and an initial
  successor-task launch before its pin file finished writing. Neither opened
  a model attempt or repeated an experiment. The pin file now exists and the
  successor is waiting normally.
- Further branch selection remains root work after sealed results. The detached
  scripts do not invent a new experiment, update a policy mid-round, or continue
  beyond a failure or unresolved scientific decision.

Routine status (no subagent): run scripts/flights/batch/continuation_status.py
with --queue /home/chao/batch-queue.json, --status /home/chao/batch-status.jsonl,
--data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data,
--stop-marker /home/chao/batch-STOP, --check-processes,
--driver-script /home/chao/saea-worktrees/fable-batch-flight/scripts/flights/batch/batch_driver.sh,
and --session-id serving-slurp-native-candidate-five-train-a-np4-v1.
The successor task log is /home/chao/batch-chain-verify1.out. Inspect facts and
errors via scripts; do not repeatedly read model output or invoke a monitoring LLM.
