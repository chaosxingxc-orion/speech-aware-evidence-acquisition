# Handoff to Fable 5.1: training-free RL continuation

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

## Latest custody issue

VERIFY-1 preparation currently refuses a historical ROLL-1 session-receipt hash:
the manifest names a mutable resident-session path that changed on a restart.
Do not modify sealed manifests or suppress verification. Locate exact original
bytes, preserve them by content hash, and establish a versioned relocation rule
before any VERIFY-1 contact. The active VAR-1 arm does not consume this source.
