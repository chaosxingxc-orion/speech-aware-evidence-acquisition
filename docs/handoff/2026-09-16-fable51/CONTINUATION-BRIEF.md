# Fable5.1 continuation brief

Read this file and LATEST.md before historical handoff snapshots. This is the owner's
requested file-based transfer of research, including expectations for future experiments.
No acceptance by Fable5.1 is assumed. Record a new TAKEOVER-FABLE51-<UTC>.md when taking
coordination, including actual Git, process, flight and ownership state.

## Settled research direction

Build a useful agentic speech system around the frozen Qwen3-Omni core, then optimize
its external decisions through genuine training-free trajectory sampling and updates.
Root-authored prompts and engineering improvements are not an RL algorithm result.

Focus SLURP first. Pursue two connected questions: increase gold-intent inclusion toward
95%, and improve final intent/slot quality once the correct hypothesis is available.
Whole-task performance decides advancement. The owner explicitly permits these directions
to advance together; 95% is a target, not a prerequisite for every system improvement.

Keep intent and slot knowledge separate. Intent values should express activation
distinctions; slot values should explain semantic roles, extraction boundaries, supported
representations and ambiguity/omission behavior. Retrieval accuracy alone is insufficient:
what the receiving role consumes is the central mechanism.

Memory should capture transferable corrections and useful rules, not relabel the raw
training set as memory. Separate observation, knowledge, hypotheses, drafts and criticism.
Reviewer/Planner may request bounded tools during execution; Solver retains answer
authority. Do not turn on-demand Whisper into a mandatory preprocessing stage.

## Results to retain

All numbers below are released exploratory findings, not untouched confirmation.

| Design | Established result | Interpretation |
| --- | --- | --- |
| Older max512 dual-store SLURP agent, NEW500 | Official SLU 36.1437 to 50.4479; +14.3042 points, CI90 [11.2445, 17.5009] | Useful system versus direct anchor. |
| Same-roster replica | 35.8906 to 50.6876; +14.7970 points, CI90 [11.5245, 18.0112] | Replicated package-level benefit; no isolated component or RL claim. |
| TRAIN A anchor, 1,080 rows | Gold inclusion 937/1,080 (86.76%); final intent correct 842; SLU 48.5336 | There is both candidate and downstream headroom. |
| Maximum-five candidates | Inclusion 951; intent 837; SLU 48.6204; SLU difference CI95 [-1.365, 1.651] | Did not advance. More inclusion did not establish whole-task gain. |
| Broad/factored knowledge | Inclusion 947; intent 841; SLU 47.6347; difference CI95 [-2.6077, 0.7821] | Did not advance. More material is not enough. |
| Anchor stage attribution | 525 correct-intent/nonexact-entity rows; 143 uncovered; 95 covered but wrong intent | Prioritize how relevant information is consumed, not candidate width alone. |

The detailed experimental report contains metric definitions, cohorts, conditions,
stratification, provenance and limitations. Do not combine these cohorts as independent
confirmation. E21 and Audio2Tool are held while SLURP stabilizes; retain their existing
results and dataset-native metrics.

## Latest failure and engineering diagnosis

The typed-role-context system's sole full recovery failed after 6,645 generation contacts.
A Reviewer request required 24,878 tokens in a 24,576-token slot and was rejected before
generation. The flight is CLOSED_SECOND_FAILURE_NO_FURTHER_RECOVERY.

There is no complete system score. The completed 1,080-row direct comparator has its
first official score, but task quality remains unread under the paired-release contract.
Do not read partial failed-system quality, rescore direct, splice completed prefixes,
activate the held matched replica, or create a third attempt with a different name.

Root's source-bound structural audit found that two Reviewer lookups returned 3 and 21
already-visible knowledge bodies. The second repeats 38,938 UTF-8 body bytes. The first
post-tool request was verified to contain both base and returned copies. The final failed
wire was not completely reconstructed, and token savings have not been measured.

The bounded engineering fix is opt-in request projection: retain the canonical tool result,
preserve its selections and call identity, and reference an exact full body already visible
earlier in the same request. A visibility flag is not sufficient. Source ID, URI and content
must agree; a reference cannot point to another reference or future text. Retain genuinely
new content and observations.

Read IMPLEMENTATION-UPDATE.md for the final implementation and verification state.
This repair does not prove that every dynamic request fits or that references preserve
task performance. It does not reopen the closed experiment.

## Recommended next sequence and expectations

1. Complete source/ownership takeover. Keep the failed source frozen. Check actual service
   state once; do not blindly restart, unload or release another owner's lease.
2. Review the model-free projection proof and source identities. Define a distinct,
   prospective bounded engineering validation, with explicit source, roster, tool paths,
   real-request capacity, service, contacts and stop rules. A four-row proof establishes
   connectivity/custody/capacity for those paths only; it cannot establish task gain.
   Do not use this as a renamed third recovery.
3. Select one scientific successor with a named information-use hypothesis. My preferred
   direction is candidate-specific slot/role information, keeping store contents fixed
   initially. Preserve global rules and applicable exceptions; record exclusions.
   Expected benefit: fewer irrelevant cross-intent instructions and more actionable review.
   Risk: removing useful context increases omissions. Lower input size alone is not success.
4. Keep candidate-preserving augmentation as the other main direction. Preserve initial
   candidates, acquire a specific missing distinction, and add a bounded supplemental set
   rather than regenerate the old set away. Measure gains and losses in gold inclusion
   and final task quality. Expected inclusion improvement is plausible; final selection
   can still worsen as ambiguity grows. Freeze actual caps before contact.
5. Add one on-demand acoustic tool only for a demonstrated hearing gap and qualified shared
   route. Measure actual new evidence, destination visibility, saves and harms. Generic
   re-decoding and a tool citation are not evidence of useful information gain.
6. Replicate a qualified full system on the same roster before claiming stable benefit.
   Keep the older useful agent as a fallback and complexity reference.
7. Only then define algorithmic factors, states, finite action probabilities, grouped
   trajectory sampling, score-only rewards, update rules and frozen evaluation. Compare
   direct model, fixed agent and optimized agent; include unchanged-policy sampling to
   distinguish optimization from extra inference. Keep Fold B untouched during tuning.

These are a decision tree, not a request to launch every branch. Detailed hypotheses,
controls, failure signatures, metrics and transfer plans are in FUTURE-EXPERIMENT-DESIGNS.md.
Its opening running-state statements are historical and superseded by this brief/LATEST.md.

## Owner decisions versus ordinary execution

No owner reply is needed to read the handoff or finish model-free implementation checks.
Before new unregistered contacts, present one concrete successor with comparison, roster,
actions, service geometry and full contact limits. Do not reopen settled choices:
quality is prioritized over online latency, current power configuration is accepted,
SLURP is first, and 95% inclusion plus system optimization may proceed together.

Keep existing failure and verdict rules. Future E21 screening prioritizes overall WER and
PERSON quality; small insertion increases are analyzed separately rather than automatically
vetoing a new candidate. That prospective preference never changes old verdicts.

## Operating instructions

Run in WSL Ubuntu-24.04 with explicit code paths and frozen active checkouts. One coordinator
owns one resident model service; one generation experiment is in flight. Precompute
features for the SLURP decoder-only route. Never install competing editable checkouts into
the shared environment. CPU preparation can overlap generation within the shared worker
limit. Official scoring runs once on each complete manifest.

Delegate mechanical monitoring and bounded implementation. Personally own attribution,
scientific choices, review and final acceptance. Use event summaries rather than frequent
root polling. Preserve raw data, immutable receipts, first scores and unsuccessful attempts.

The file handoff is complete; the overall research objective is not. There is no qualified
new live campaign implied by these documents.
