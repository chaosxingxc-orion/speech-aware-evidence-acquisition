# Status 111: restart review, running SLURP replica and complete Audio2Tool preparation

Date: 2026-09-14. This supersedes STATUS-110 for current progress. Retain all
historical verdicts and timestamped service observations. Establish a reproducibly
beneficial agent base and observable configurable workspace before designing
training-free RL factors, trajectory sampling, rewards and updates.

## Restart review and live execution

Root inspected WSL Ubuntu-24.04 at 17:06 UTC. Resident server PID 766 and campaign
PID 2093 are alive. GPU utilization was 98 percent, with 22,976 of 24,463 MiB
occupied and 95.80 W reported. This is one measurement, not a campaign average.
The service retains prepared speech features, no mmproj, total context 98,304,
four 24,576-token slots and maximum output 512. No restart or replay was needed.

The event-only observer's 17:07:04 UTC metadata snapshot confirms the direct
replication arm is FINALIZED at 1,000 calls, with its completed manifest and bound
first full score. The native system remains OPENED at 2,655 role calls and
7,318.7646875 repeated speech-seconds. There is no terminal, seal, scoring or
failure event for that arm. Permitted metadata does not expose a completed
system-sample count. Do not translate role calls into a percentage complete.

Keep the execution checkout frozen at 1b5009d6f82655b9ffd2f6aa2ce381f330f9f5f9.
The preparation branch changes do not enter the running process. Hold both
quality results until complete pair verification and registered paired release.
Continue the admitted campaign and event-only observation; do not start a second
generation lease or Audio2Tool service while this generation is active.

## Released results and their limits

The prior SLURP package passes its exploratory advancement rule. On historically
exposed NEW500, official pooled SLU micro F1 is 36.1437 direct and 50.4479 system,
a 14.3042-point gain with speaker-cluster CI90 [11.2445, 17.5009]. Joint intent
accuracy is 73.6 versus 77.6 percent. DEV1000 micro F1 improves 35.4589 to 49.5219.
This is one package comparison; reproducibility is the running experiment.

Candidate inclusion remains 424/500 (84.8 percent) on NEW500 and 836/1000
(83.6 percent) on DEV1000. On NEW500, 37 covered cases still deliver a wrong
intent; 250 cases have a correct intent but a nonexact entity result. The package
has heterogeneous effects: the general scenario loses intent accuracy despite
its SLU gain. Preserve full scenario tables; do not infer that every component
or stratum benefits. The previous system has 1,010 task-contract tool calls,
12 revisions and no ASR or corrective-memory use. These results do not establish
a selectively acquired acoustic-evidence benefit.

The separate TRAIN-A diagnostic has 1,080 rows: 143 missing candidates, 95
covered-but-wrong intents, 525 correct-intent/nonexact-slot cases and 317 fully
correct cases. Its 86.75926-percent inclusion estimate is a different population.
The enhanced TRAIN recovery aborted after 2,417 contacts when its server
disappeared; the cause is not established. It is a closed second failure,
has no partial quality score and must not receive a third attempt.

The old 4,000-row Audio2Tool direct/stage/knowledge package is closed:
official exact match 18.90/17.95/18.60 percent and tool accuracy
62.025/60.525/58.550 percent. It did not establish system benefit.
The new four-role design has no generation or quality result yet.

E21's completed fixed repair covers 1,593 windows and 44 calls. WER improves
8.12086 to 8.07499 percent; PERSON error improves 23.14021 to 19.74631 percent,
with 165 fewer total word errors and 99 fewer PERSON errors. Five additional
insertions failed the historical guard. Preserve that decision. Future screening
prioritizes WER/PERSON under the owner's amendment and analyzes insertions
separately. No completed native Reviewer/Planner/tool-acquisition E21 result is
established. E22 and summary-based objectives remain outside the active queue.

## Completed Audio2Tool preparation

The shared candidate-to-parameter route is already integrated in master:
ordered action occurrences, legal candidates from the public 152-tool registry,
candidate-associated parameter values, and the registered four-role controller.
The source verification records 343 passing tests and 89.32-percent changed-line
coverage. No new carrier-specific executor was created.

The isolated preparation branch now contains matched direct/system configs,
four role prompts, prospective three-slot and fallback two-slot model profiles,
a campaign and a frozen saved-score analysis recipe. Both arms retain original
speech, the official task contract, the complete legal answer space, the same
frozen core and a common 2,048-token ceiling. These are prospective configurations,
not model-contact admission.

Perception receives eight activation values and may describe up to eight ordered
action occurrences with up to four alternatives each. Solver receives up to
32 candidate-associated parameter explanations. Repeated actions remain distinct;
knowledge delivery deduplicates tool cards. Solver can recover outside the
candidate set from the full registry. These are intermediate operational limits,
not a claim about dataset action maxima or a restriction on final answers.

Reviewer may request task-contract evidence when a concrete issue warrants it.
Planner may accept or request one revision; Solver alone supplies the answer.
This initial transfer has no ASR, corrective memory or candidate-refresh mechanism.
The two stores have different value semantics, but existing retrieval key text
remains mixed. Improved key construction is a later measured change.

Shared prepare-supply completed all 4,000 activation selections. Every sample has
eight selected values; the sample set equals the prepared speech-packet roster.
A second invocation reports a warm hit and preserves all artifact bytes.
There were zero model, tokenizer, encoder, ASR or scoring contacts.
Source-bound receipt:
DATA/coordination/a2t-agent-base-transfer-v1/native-role-configuration-preparation-v1.json
SHA-256 67836d65b502880fcb1957893107f9214ab58c30df4c3560e071f85265d8f4e1.
Prepared artifact SHA-256:
91847da0921f12a0a1be5cc1b4eafee091de3e1e32986a779d77d29a36026b68.

The candidate-supply volume bound and adjacent integration pass 115 tests and
the engineering-base check. A coarse bound is not an actual token-fit receipt.
Generic synthetic wire-check supports the direct arm only. Native proof must use
the real renderer/OpenJiuwen path and the registered bounded serving validation.

The genuine-receipt custody gap is now fixed in shared campaign/receipt code.
Campaigns persist actual stage and candidate-selection receipts after seal and
score completion. Atomic writes reject rollback, identity changes and mutation
of prior stages; failures preserve genuine completed stages and the primary
error. Root identified and closed a shutdown-failure omission, then verified
89 integrated tests and the engineering-base check. The prepared runtime/config
bytes remain identical to dce62993 and the artifact hash is unchanged. Historical
missing-receipt limitations and active execution source remain unchanged.

Verification: DATA/coordination/a2t-agent-base-transfer-v1/
campaign-receipt-custody-verification-v1.json, SHA-256
48d3ff64b9d4aacd1121311b72d65f1182fdace27e40c0bd8736bbafff64757e.

## Next actions and completion criteria

1. Finish the admitted SLURP replica, both first full scores and registered paired
   analysis. Apply the existing primary/stratum rule. If it disagrees with the
   first comparison, root-cause the discrepancy; do not average away instability.
2. Retain the completed preparation and receipt-persistence integration for the
   next run boundary; keep the current execution checkout unchanged.
3. Use the complete Audio2Tool preparation to finish prospective registration,
   current-configuration native serving proof and actual capacity validation.
   Settle the whole comparison's three-slot or two-slot geometry before generation.
   Dispatch it only after its SLURP scientific dependency and readiness pass.
4. Select the next SLURP capability using released TRAIN diagnostics: improve
   candidate inclusion, resolve covered ambiguities, or correct slot interpretation
   with new evidence. Develop these workstreams in parallel, but admit one measured
   capability change at a time. Preserve disjoint construction/validation splits.
5. Add local speech tools as in-episode evidence actions chosen by Reviewer/Planner.
   Trace the trigger, selected span, tool output, Solver revision and corrections
   versus regressions. Tool availability or extra calls alone is not information gain.
6. Transfer the stable base to E21 with native WER/entity scoring and genuine
   dynamic observation. Keep speaker/topic context as evidence-design hypotheses.
7. After the SLURP base and workspace qualify, define the training-free RL action
   factors, trajectory sampling, reward/advantage estimation and policy/memory
   updates. Completion of every transfer carrier is not required first.

There is no blocking owner decision. Existing directions settle GPU use,
quality priority, the candidate-inclusion target, separate knowledge stores,
on-demand tools and the base-before-RL sequence. Ask only when a concrete next
proposal changes dataset inputs, scientific comparison, closed-flight recovery
authority or task scope. The public Audio2Tool prompt/multi-action ambiguity is
documented; this matched transfer retains the existing contract in both arms.
